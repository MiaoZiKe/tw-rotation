"""總覽大盤三張圖的「開頁種子」：最近一個**完整**交易日的分時＋昨收（2026-10-04）。

為什麼有這支（Andy 2026-10-04 21:19 週日截圖：三張圖都卡在「載入中…」）
---------------------------------------------------------------------------
非交易時段前端要先下載 index_intraday.json（約 944KB）＋ index_ohlc.json（約 334KB）
才畫得出第一張走勢圖；Worker 又慢的時候三張圖長時間空白。這裡把「畫第一幀需要的東西」
預先切成一份幾 KB 的 index_lastday.json，大檔改成背景補。

口徑（不准放寬）
----------------
· 「完整」＝那一天的 1 分 K 至少涵蓋時段的六成、且碰到開盤後 30 分與收盤前 15 分 —— 跟前端 fullDay() 同一把尺。
  資料湖偶爾某個來源只存到某天頭幾根，那種天往前退。
· 昨收＝**所選那一天的前一個交易日**的日 K 收盤（index_ohlc 裡 date < 那天的最後一根）。
  絕不拿「最新一根日 K」的前一根當昨收 —— 那會把 10-01 的走勢配上 10-02 的昨收。
· 同一分鐘有多個來源（finmind／mis）時保留最後寫進湖的那筆。
· 只做日盤三個代號（TSE／OTC／FUT）。夜盤（FUT_N）的參考價是日盤結算價，湖裡沒有那個欄位，
  寧可不給種子也不給一個口徑可疑的昨收。
"""
from __future__ import annotations

import pandas as pd

# 交易時段（台北分鐘），跟 site/market3.js 的 SESSION 一字不差
SESSION = {"TSE": (9 * 60, 13 * 60 + 30), "OTC": (9 * 60, 13 * 60 + 30), "FUT": (8 * 60 + 45, 13 * 60 + 45)}


def _day_min(ts: pd.Series) -> tuple[pd.Series, pd.Series]:
    t = pd.to_datetime(ts.astype(str), errors="coerce", format="mixed", utc=True).dt.tz_convert("Asia/Taipei")
    return t.dt.strftime("%Y-%m-%d"), t.dt.hour * 60 + t.dt.minute


def full_enough(mins: list[int], sym: str) -> bool:
    s0, s1 = SESSION[sym]
    if not mins:
        return False
    return len(mins) >= (s1 - s0) * 0.6 and min(mins) <= s0 + 30 and max(mins) >= s1 - 15


def build(lake: pd.DataFrame, ohlc: dict) -> dict:
    """lake：資料湖 index_intraday 原表；ohlc：寫給前端的 index_ohlc（{sym: [[date,o,h,l,c,v],…]}）。"""
    out: dict = {}
    if lake is None or lake.empty:
        return out
    df = lake[lake["interval"].astype(str) == "1m"].copy() if "interval" in lake.columns else lake.copy()
    df = df.dropna(subset=["ts", "close"])
    if df.empty:
        return out
    df["day"], df["min"] = _day_min(df["ts"])
    df = df.dropna(subset=["day", "min"])
    for sym, (s0, s1) in SESSION.items():
        g = df[(df["symbol"].astype(str) == sym) & (df["min"] >= s0) & (df["min"] <= s1)]
        if g.empty:
            continue
        g = g.drop_duplicates(["day", "min"], keep="last").sort_values(["day", "min"])
        daily = [r for r in (ohlc or {}).get(sym, []) if r and r[4] is not None]
        for day in sorted(g["day"].unique(), reverse=True):
            d = g[g["day"] == day]
            mins = [int(m) for m in d["min"]]
            if not full_enough(mins, sym):
                continue
            prevs = [r for r in daily if str(r[0])[:10] < day]
            if not prevs:
                break                      # 沒有前一個交易日的收盤 → 不給（不准拿別天湊）
            prev = float(prevs[-1][4])
            last = float(d["close"].iloc[-1])
            # 只給 [分鐘, 收盤]：種子只畫走勢線與數字列，不畫量（各來源分 K 的量口徑不一，見 build_payload 的 turnover 註解）
            pts = [[int(m), round(float(c), 2)] for m, c in zip(d["min"], d["close"])]
            bar = next((r for r in reversed(daily) if str(r[0])[:10] == day), None)
            # 收盤以當天日 K 為準：13:30 收盤集合競價常在 13:31～13:33 才寫進分 K，落在時段外。
            # 線的最後一點補在收盤那一分鐘（s1），值＝當天日 K 收盤 —— 那是真實的收盤價，不是估的。
            if bar and bar[4] is not None:
                last = float(bar[4])
                if pts[-1][0] < s1:
                    pts.append([s1, round(last, 2)])
            out[sym] = {
                "date": day.replace("-", ""),
                "prev": prev, "prev_date": str(prevs[-1][0])[:10],
                "open": float(d["open"].iloc[0]), "high": float(d["high"].max()), "low": float(d["low"].min()),
                "last": last, "chg": round(last - prev, 2), "pct": round((last / prev - 1) * 100, 2),
                "points": pts,
                "bar": bar, "lastbar": daily[-1] if daily else None,
            }
            break
    return out
