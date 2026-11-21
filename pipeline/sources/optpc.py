"""臺指選擇權（TXO）每日買賣權比（P/C ratio）歷史回補。

來源：FinMind `TaiwanOptionDaily`（逐契約每日行情：履約價、買賣權、成交量、未平倉量、交易時段），data_id＝TXO。
做法：每個交易日把所有 TXO 契約（一般交易時段 position）的買權／賣權成交量與未平倉量加總，算
  pc_vol = 賣權成交量 / 買權成交量、pc_oi = 賣權未平倉量 / 買權未平倉量（期交所『買賣權比』的定義）。
寫進新表 `opt_pc`（key＝date），一律走 store.append()（只增不改）。

⚠ 容器連不到 FinMind，**欄位名是依 FinMind 文件與社群範例寫的，尚未在 Actions 實測**；
所以解析一律「認不得欄位就回空並記 log（含回應前 200 字）」，不猜、不寫壞資料進只增不改的湖。
回補是按月游標（進度存在 backfill_progress.json 的 complete.opt_pc），每輪最多補幾個月，避免一次吃光額度。
官方對照：期交所選擇權每日行情簡表（https://www.taifex.com.tw/cht/3/optDailyMarketSummary，2001-12 起，單日查詢）。
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

import pandas as pd

log = logging.getLogger(__name__)

CP = {"call": "call", "put": "put", "c": "call", "p": "put", "買權": "call", "賣權": "put"}
FLOOR = "2008-01-01"
MONTHS_PER_RUN = 3


def _head(rows) -> str:
    return str(rows[:1])[:200] if rows else "[]"


def parse_option_daily(rows: list[dict] | None) -> pd.DataFrame:
    """逐契約 -> 每日 (date, put_vol, call_vol, pc_vol, put_oi, call_oi, pc_oi)。"""
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    need = {"date", "call_put", "volume", "open_interest"}
    if not need <= set(df.columns):
        log.warning("opt_pc 欄位認不得（缺 %s）：%s", sorted(need - set(df.columns)), _head(rows))
        return pd.DataFrame()
    if "trading_session" in df.columns:
        sess = df["trading_session"].astype(str).str.lower()
        keep = sess.isin(["position", "一般", "regular", "0"]) | ~sess.isin(["after_market", "盤後", "1"])
        df = df[keep]
    df["cp"] = df["call_put"].astype(str).str.strip().str.lower().map(CP)
    df = df.dropna(subset=["cp"])
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0)
    df["open_interest"] = pd.to_numeric(df["open_interest"], errors="coerce").fillna(0)
    df["date"] = df["date"].astype(str).str[:10]
    g = df.groupby(["date", "cp"])[["volume", "open_interest"]].sum().unstack("cp")
    out = pd.DataFrame({
        "date": g.index,
        "put_vol": g[("volume", "put")].to_numpy() if ("volume", "put") in g else 0.0,
        "call_vol": g[("volume", "call")].to_numpy() if ("volume", "call") in g else 0.0,
        "put_oi": g[("open_interest", "put")].to_numpy() if ("open_interest", "put") in g else 0.0,
        "call_oi": g[("open_interest", "call")].to_numpy() if ("open_interest", "call") in g else 0.0,
    })
    out["pc_vol"] = out["put_vol"] / out["call_vol"].where(out["call_vol"] > 0)
    out["pc_oi"] = out["put_oi"] / out["call_oi"].where(out["call_oi"] > 0)
    return out.reset_index(drop=True)


def month_range(first: date, last: date):
    y, m = first.year, first.month
    while (y, m) <= (last.year, last.month):
        a = date(y, m, 1)
        ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
        b = date(ny, nm, 1)
        yield a, b
        y, m = ny, nm


def backfill_opt_pc(prog: dict, save_progress, today: date | None = None, months: int = MONTHS_PER_RUN, fetch=None) -> int:
    """每輪補 months 個月；游標在 prog['complete']['opt_pc']['next']（YYYY-MM-01）。回傳新增列數。"""
    from .. import config
    from ..util import http, store
    if "opt_pc" not in config.TABLES:
        return 0
    today = today or date.today()
    flag = (prog.setdefault("complete", {})).setdefault("opt_pc", {})
    nxt = date.fromisoformat(flag.get("next") or FLOOR)
    if nxt > today:
        return 0
    fetch = fetch or (lambda a, b: http.finmind_get("TaiwanOptionDaily", data_id="TXO", start_date=a, end_date=b))
    added = 0; empties = 0
    for k, (a, b) in enumerate(month_range(nxt, today)):
        if k >= months:
            break
        rows = fetch(a.isoformat(), (b - timedelta(days=1)).isoformat())
        df = parse_option_daily(rows)
        if df.empty:
            empties += 1
            log.info("opt_pc %s 沒有資料（連續空 %d 個月）", a, empties)
            if empties >= 2:                         # 連兩個月都空：多半是資料集不開放，先停，下一輪再試，不要把游標推過去
                break
        else:
            added += store.append("opt_pc", df)
            empties = 0
        flag["next"] = b.isoformat() if not df.empty or empties < 2 else a.isoformat()
        flag["at"] = str(today)
        flag["done"] = date.fromisoformat(flag["next"]) > today   # 補到本月之後才算完成（排程守門看這個）
        save_progress(prog)
    return added
