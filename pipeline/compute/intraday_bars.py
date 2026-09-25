"""大盤三張圖的 1 小時／4 小時：把資料湖 `index_intraday` 的分 K 依台股交易時段合成。

為什麼放伺服器端（2026-09-25，Andy：「幫我處理週期問題」）
--------------------------------------------------------------
以前 `site/market3.js` 在瀏覽器端經 Worker `/y` 抓 Yahoo 15 分 K 再合成，
線上抓不到時三張卡片全部退回日 K、寫「15 分 K 抓不到，已改用『日』」。
分 K 是「明天還會用到」的資料，照 DECISIONS #155 應該進資料湖、增量更新，前端只讀。

切法跟前端 `sessKey()` 一字不差（兩邊口徑必須一致，改一邊記得改另一邊）：
  · 日盤 1H：09:00 起每小時；08:45～09:00（期貨）併進 09 那根，13:00 之後併進 13 那根。
  · 日盤 4H：一個交易日一根（09:00 開始）。
  · 夜盤 1H：15:00 起每小時，跨午夜照接，05:00 收。
  · 夜盤 4H：一晚一根，歸在**開盤那天**的 15:00（凌晨那段屬於前一天開的那一盤）。
時間戳一律是「台北牆鐘秒數」（UTC 秒數＋8 小時），跟前端其他週期同一個口徑。
"""
from __future__ import annotations

import pandas as pd

TZ = "Asia/Taipei"
NIGHT_START = 15 * 60          # 15:00
NIGHT_END = 5 * 60 + 1         # 05:00（含 05:00 那一分鐘）


def wall_seconds(ts: pd.Series) -> pd.Series:
    """ISO 時間字串 → 台北牆鐘秒數（整數）。naive 時間視為台北時間。"""
    t = pd.to_datetime(ts.astype(str), errors="coerce", utc=False, format="mixed")
    out = []
    for v in t:
        if v is pd.NaT or pd.isna(v):
            out.append(None)
            continue
        v = v.tz_localize(TZ) if v.tzinfo is None else v.tz_convert(TZ)
        naive = v.tz_localize(None)
        out.append(int((naive - pd.Timestamp("1970-01-01")).total_seconds()))
    return pd.Series(out, index=ts.index, dtype="Int64")


def session_key(t: int, tf: str) -> int:
    """一根 K 棒（台北牆鐘秒數）屬於哪一格 1H／4H（回傳那一格的開始時間）。"""
    day, minute = divmod(int(t), 86400)
    minute //= 60
    night = minute >= NIGHT_START or minute < NIGHT_END
    if night:
        if tf == "H4":
            return ((day - 1) if minute < NIGHT_END else day) * 86400 + 15 * 3600
        return (int(t) // 3600) * 3600
    if tf == "H4":
        return day * 86400 + 9 * 3600
    h = min(13, max(9, minute // 60))
    return day * 86400 + h * 3600


def trade_day_of(t: int) -> int:
    """這根屬於哪一個「盤」（日盤＝當天、夜盤＝開盤那天），用 H4 的格子當代表。"""
    return session_key(t, "H4")


def synth(bars: pd.DataFrame, tf: str) -> list[list]:
    """`bars` 欄位：t（牆鐘秒數）, open, high, low, close, volume，已排序。回傳 [[t,o,h,l,c,v], …]。"""
    out: list[list] = []
    cur = None
    key = None
    for r in bars.itertuples(index=False):
        k = session_key(r.t, tf)
        v = float(r.volume) if pd.notna(r.volume) else 0.0
        if k != key:
            if cur:
                out.append(cur)
            key = k
            cur = [k, float(r.open), float(r.high), float(r.low), float(r.close), v]
        else:
            cur[2] = max(cur[2], float(r.high))
            cur[3] = min(cur[3], float(r.low))
            cur[4] = float(r.close)
            cur[5] += v
    if cur:
        out.append(cur)
    return out


def build(lake: pd.DataFrame, tail: int = 2600) -> dict:
    """資料湖 `index_intraday` → {symbol: {"H1": [...], "H4": [...], "src": {...}}}。

    同一個「盤」同時有 15 分與 60 分時，用 15 分（顆粒細，高低點準）；
    只有 60 分的那些日子（15 分只保留約 60 天）就用 60 分 —— 60 分 K 本來就對齊整點，合成結果一樣。
    """
    out: dict = {}
    if lake is None or lake.empty:
        return out
    df = lake.dropna(subset=["ts", "symbol", "close"]).copy()
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = pd.to_numeric(df.get(c), errors="coerce")
    df["open"] = df["open"].fillna(df["close"])
    df["high"] = df["high"].fillna(df["close"])
    df["low"] = df["low"].fillna(df["close"])
    df["t"] = wall_seconds(df["ts"])
    df = df.dropna(subset=["t"])
    df["t"] = df["t"].astype("int64")
    df["day"] = df["t"].map(trade_day_of)
    for sym, g in df.groupby("symbol"):
        iv = g["interval"].astype(str) if "interval" in g.columns else pd.Series("60m", index=g.index)
        days15 = set(g.loc[iv == "15m", "day"])
        use = g[(iv == "15m") | ~g["day"].isin(days15)]
        use = use.sort_values(["t", "interval"] if "interval" in use.columns else ["t"])
        use = use.drop_duplicates("t", keep="first")
        h1 = synth(use, "H1")[-tail:]
        h4 = synth(use, "H4")[-tail:]
        out[str(sym)] = {"H1": h1, "H4": h4,
                         "src": {"rows": int(len(use)), "days15": len(days15),
                                 "days": int(use["day"].nunique())}}
    return out


def ticks_to_60m(ticks: pd.DataFrame) -> pd.DataFrame:
    """期貨逐筆（FinMind TaiwanFuturesTick）→ 近月 60 分 K，分日盤 FUT／夜盤 FUT_N。

    逐筆欄位：date（"YYYY-MM-DD HH:MM:SS"，台北時間）, contract_date, price, volume。
    近月＝那一個盤裡成交量最大的單一月份（帶 `/` 的是價差單，丟掉）—— 跟日 K 的 `_near_month` 同一口徑。
    """
    if ticks is None or ticks.empty or "date" not in ticks.columns:
        return pd.DataFrame()
    d = ticks.copy()
    d = d[~d.get("contract_date", pd.Series("", index=d.index)).astype(str).str.contains("/", na=False)]
    d["price"] = pd.to_numeric(d.get("price"), errors="coerce")
    d["volume"] = pd.to_numeric(d.get("volume"), errors="coerce").fillna(0)
    d = d[d["price"] > 0]
    if d.empty:
        return pd.DataFrame()
    d["t"] = wall_seconds(d["date"])
    d = d.dropna(subset=["t"])
    d["t"] = d["t"].astype("int64")
    d["day"] = d["t"].map(trade_day_of)
    minute = (d["t"] % 86400) // 60
    d["night"] = (minute >= NIGHT_START) | (minute < NIGHT_END)
    rows = []
    for (day, night), g in d.groupby(["day", "night"]):
        near = g.groupby(g["contract_date"].astype(str))["volume"].sum().idxmax()
        g = g[g["contract_date"].astype(str) == near].sort_values("t", kind="stable")
        g = g.assign(open=g["price"], high=g["price"], low=g["price"], close=g["price"])
        for b in synth(g[["t", "open", "high", "low", "close", "volume"]], "H1"):
            ts = (pd.Timestamp("1970-01-01") + pd.Timedelta(seconds=b[0])).tz_localize(TZ)
            rows.append({"ts": ts.isoformat(), "symbol": "FUT_N" if night else "FUT",
                         "interval": "60m", "open": b[1], "high": b[2], "low": b[3],
                         "close": b[4], "volume": b[5]})
    return pd.DataFrame(rows)
