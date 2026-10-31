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


ETF_CAL_LABEL = "ETF 配息行事曆"
ETF_CAL_GUARD_DAY = 15      # 每月 15 日起還是 0 筆才算異常：月初投信還沒公告本月除息是正常的


def etf_cal_guard(ex_dates, today: str) -> dict | None:
    """ETF 配息行事曆保底（Andy 2026-11-01：行事曆整月空白沒人發現）。

    當月（以台北「今天」為準）已公告除息 0 筆、但去年同月有除息，而且已過當月 ETF_CAL_GUARD_DAY 日 → 回告警 dict。
    純函式，方便用假資料測。"""
    ex = [str(x)[:10] for x in ex_dates if x is not None and str(x)[:4].isdigit()]
    ym = today[:7]
    last = f"{int(ym[:4]) - 1}{ym[4:]}"
    cur_n = sum(1 for x in ex if x[:7] == ym)
    prev_n = sum(1 for x in ex if x[:7] == last)
    if cur_n == 0 and prev_n > 0 and int(today[8:10]) >= ETF_CAL_GUARD_DAY:
        return {"label": ETF_CAL_LABEL, "month": ym, "rows": 0, "last_year_rows": prev_n, "status": "warn",
                "reason": "empty_month"}
    return None


FIN_CAL_LABEL = "財經日曆"
FIN_CAL_SRC_STALE_DAYS = 8       # FRED 日程／重大訊息超過幾天沒抓到新的就亮燈（排程是每個交易日，8 天涵蓋長假）
FIN_CAL_GROUP = {"rep": "公司財報", "conf": "公司法說", "fed": "FED 消息"}


def fin_cal_guard(coverage: dict, today: str, *, last_year: dict | None = None,
                  fred_fetched: str | None = None, mops_last: str | None = None) -> list[dict]:
    """財經日曆保底（Andy 2026-11-01：「財經日曆也一樣每週更新」；下個月整月空白要被發現，不准默默空白）。純函式。

    coverage＝earnings.coverage() 的輸出 {月: {分類: {announced, est}}}；last_year＝{分類: 去年同月已公告筆數}（資料湖還沒滿一年就傳 None）。
    告警條件（任何一條成立就回一筆 dict）：
      · 下個月某分類 已公告＋預估 都是 0 筆，而且去年同月有（法說）或這一類本來每月都有（財報有營收期限、FED 有 CPI／非農）；
      · FRED 日程或重大訊息超過 FIN_CAL_SRC_STALE_DAYS 天沒抓到新的（抓取失敗要亮燈）。"""
    out = []
    ym = today[:7]
    nxt = sorted(coverage)[-1] if coverage else None
    always = {"rep", "fed"}
    if nxt and nxt > ym:
        for g, n in coverage[nxt].items():
            tot = n["announced"] + n["est"]
            if tot == 0 and (g in always or (last_year or {}).get(g, 0) > 0):
                out.append({"label": f"{FIN_CAL_LABEL}・{FIN_CAL_GROUP.get(g, g)}", "month": nxt, "rows": 0,
                            "last_year_rows": (last_year or {}).get(g), "status": "warn", "reason": "empty_next_month"})
    t = pd.Timestamp(today)
    for name, last in (("FRED 日程", fred_fetched), ("重大訊息", mops_last)):
        if last is None or (t - pd.Timestamp(last[:10])).days > FIN_CAL_SRC_STALE_DAYS:
            out.append({"label": f"{FIN_CAL_LABEL}・{name}", "last": last, "status": "warn", "reason": "source_stale"})
    return out


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
        res = evaluate({t: _counts(t) for t in WATCH}, trade_date, pending=pending)
        try:
            ev = store.read("etf_dividend_events")
            g = etf_cal_guard(ev["ex_date"].dropna().tolist() if not ev.empty else [], tp.date().isoformat())
            if g:
                res["tables"]["etf_dividend_events"] = g
                res["warn"].append("etf_dividend_events")
                res["warn_labels"].append(ETF_CAL_LABEL)
        except Exception as exc:  # noqa: BLE001
            log.warning("ETF 行事曆保底檢查失敗（不影響管線）：%s", exc)
        try:
            from ..compute import earnings as _E
            mn, cal = store.read("material_news"), store.read("macro_calendar")
            today = tp.date().isoformat()
            start, end = today, (pd.Timestamp(today) + pd.Timedelta(days=75)).strftime("%Y-%m-%d")
            evs = _E.macro_events(_E.load_macro_yaml(), cal, start, end) + _E.market_events(start, end)   # 營收／財報法定期限一定有，財報分類才不會因來源沒預告就誤報
            if not mn.empty:
                evs += [e for e in _E.mops_events(mn, set(), conf_all=True) if start <= e["d"] <= end]
            cov = _E.coverage(evs, today)
            nxt = sorted(cov)[-1]
            ly = f"{int(nxt[:4]) - 1}{nxt[4:]}"
            ly_ok = (not mn.empty) and str(mn["date"].min())[:7] <= ly     # 資料湖要真的涵蓋到去年同月才拿來比
            ly_n = None
            if ly_ok:
                ly_n = {"conf": sum(1 for e in _E.mops_events(mn, set(), conf_all=True) if e["d"][:7] == ly and e["k"] in ("conf", "invite"))}
            gs = fin_cal_guard(cov, today, last_year=ly_n,
                               fred_fetched=str(cal["fetched"].max()) if not cal.empty and "fetched" in cal.columns else None,
                               mops_last=str(mn["date"].max())[:10] if not mn.empty else None)
            for i, w in enumerate(gs):
                res["tables"][f"fin_calendar_{i}"] = w
                res["warn"].append(f"fin_calendar_{i}")
                res["warn_labels"].append(w["label"])
        except Exception as exc:  # noqa: BLE001
            log.warning("財經日曆保底檢查失敗（不影響管線）：%s", exc)
        return res
    except Exception as exc:  # noqa: BLE001
        log.warning("資料新鮮度檢查失敗（不影響管線）：%s", exc)
        return {}
