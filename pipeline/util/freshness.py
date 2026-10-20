"""資料新鮮度把關（2026-10-20，Andy：「我看見那數據沒更新，確保數據每天都有更新」）。

為什麼要有這支：10-19 的個股三大法人只進了 148～249 檔（正常 1,900 檔以上），
管線每一步都「成功」、last_run.json 的 errors 是空的、Actions 是綠的，
結果頁面默默退回 10-16 的資料，沒有任何人發現。「抓到一點點」被當成成功。

判準（全部以價量表 price_daily 的最新日為「最新交易日」，不用執行當下的日期）：
  · missing：這張表一列都沒有（例如 inst_market_daily 一直沒進湖）；
  · behind ：表的最新日 < 最新交易日；
  · thin   ：最新交易日那天的筆數 < 近 10 個交易日（不含最新日）中位數的 80%。
台北時間當天 19:00 前、最新交易日就是今天時，法人／融資券本來就還沒出，標 pending 而不是 warn
（15:30 那輪若亮警告，每天下午都會被誤會成壞掉）。
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import pandas as pd

from .. import config
from . import store

log = logging.getLogger(__name__)

#: 要把關的表 → 給人看的中文名（不列內部代號，見 app.js 2026-09-28 的註解）
WATCH = {
    "inst_daily": "個股三大法人",
    "inst_market_daily": "全市場三大法人金額",
    "margin_total": "整體融資融券",
    "fut_inst": "期貨三大法人",
    "fut_oi": "期貨全市場未平倉",
}
MIN_RATIO = 0.8          # 最新日筆數至少要有近期中位數的幾成
HISTORY_DAYS = 10        # 中位數看幾個交易日
EVENING_HOUR = 19        # 台北幾點之後，當天的晚出來源才算「該到了」
TAIPEI = timezone(timedelta(hours=8))


def evaluate(counts: dict[str, pd.Series], trade_date: str | None, *, pending: bool = False,
             ratio: float = MIN_RATIO) -> dict:
    """純函式，方便用假資料測。counts[表] ＝ 以日期字串為索引、筆數為值的 Series。"""
    tables, warn = {}, []
    for t, label in WATCH.items():
        s = counts.get(t)
        s = s.sort_index() if s is not None else pd.Series(dtype="int64")
        latest = str(s.index.max()) if len(s) else None
        n = int(s.get(trade_date, 0)) if trade_date else 0
        prev = s[[d for d in s.index if trade_date and str(d) < trade_date]].tail(HISTORY_DAYS)
        med = float(prev.median()) if len(prev) else 0.0
        reason = None
        if latest is None:
            reason = "missing"
        elif trade_date and latest < trade_date:
            reason = "behind"
        elif med > 0 and n < ratio * med:
            reason = "thin"
        status = "ok" if reason is None else ("pending" if pending else "warn")
        tables[t] = {"label": label, "latest": latest, "rows": n, "median": round(med, 1),
                     "status": status, "reason": reason}
        if status == "warn":
            warn.append(t)
    return {"trade_date": trade_date, "tables": tables, "warn": warn,
            "warn_labels": [WATCH[t] for t in warn]}


def _counts(table: str) -> pd.Series:
    try:
        df = store.read(table)
    except Exception as exc:  # noqa: BLE001
        log.warning("新鮮度檢查讀 %s 失敗：%s", table, exc)
        return pd.Series(dtype="int64")
    if df.empty or "date" not in df.columns:
        return pd.Series(dtype="int64")
    return df["date"].astype(str).str.slice(0, 10).value_counts().sort_index()


def check(now: datetime | None = None) -> dict:
    """讀資料湖算新鮮度。任何失敗回空 dict（把關不能反過來弄壞管線）。"""
    try:
        px = store.read("price_daily", years=[(now or datetime.now(TAIPEI)).year])
        if px.empty:
            px = store.read("price_daily")
        trade_date = str(px["date"].astype(str).max())[:10] if not px.empty else None
        tp = (now or datetime.now(TAIPEI)).astimezone(TAIPEI)
        pending = bool(trade_date == tp.date().isoformat() and tp.hour < EVENING_HOUR)
        return evaluate({t: _counts(t) for t in WATCH}, trade_date, pending=pending)
    except Exception as exc:  # noqa: BLE001
        log.warning("資料新鮮度檢查失敗（不影響管線）：%s", exc)
        return {}
