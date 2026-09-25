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


# 同一個「盤」有好幾種顆粒時挑哪一種：數字越小越優先。
# 1m ＝ 證交所 mis 分時（2026-09-26 起每天盤後自己存）：真實逐分鐘量、跟今天走勢圖同一個來源，一律優先；
# 15m／60m ＝ Yahoo（加權才有，指數量是 0）。認不得的 interval 排最後。
INTERVAL_RANK = {"1m": 0, "15m": 1, "60m": 2}


def bucket(bars: pd.DataFrame, secs: int) -> list[list]:
    """照固定的牆鐘格子（例：900 秒＝15 分）聚合，時間戳是格子的開始。`bars` 欄位同 synth()，已排序。

    1 分 K → 15 分 K 用這個（前端 toBars 的 floor(分鐘 / 15) 同一個切法）；1H／4H 仍走 session_key。
    """
    out: list[list] = []
    cur = None
    key = None
    for r in bars.itertuples(index=False):
        k = (int(r.t) // secs) * secs
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


def _day_str(day_key: int) -> str:
    """trade_day_of() 的格子（牆鐘秒數）→ 'YYYY-MM-DD'。"""
    return (pd.Timestamp("1970-01-01") + pd.Timedelta(seconds=int(day_key))).strftime("%Y-%m-%d")


def build(lake: pd.DataFrame, tail: int = 2600) -> dict:
    """資料湖 `index_intraday` → {symbol: {"H1": [...], "H4": [...], "M15": [...], "src": {...}}}。

    每一個「盤」只挑一種顆粒：有 1 分（mis）用 1 分，否則 15 分，否則 60 分（INTERVAL_RANK）。
    ★ 2026-09-26：三個指數同一套邏輯 —— 加權的 Yahoo 歷史保留，同一天兩個來源都有時以 mis 為準
      （真實量、跟今天走勢圖同口徑）；櫃買、台指期從第一個存到的交易日開始累積。
    `src` 額外給 first／last（有分 K 的第一天、最後一天）與 mis_first／mis_days（mis 1 分 K 從哪天起、幾天），
    前端用它寫「櫃買分 K 自 YYYY-MM-DD 起累積（N 天）」—— 天數讀資料，不寫死。
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
    df["iv"] = df["interval"].astype(str) if "interval" in df.columns else "60m"
    df["rank"] = df["iv"].map(INTERVAL_RANK).fillna(9).astype(int)
    cols = ["t", "open", "high", "low", "close", "volume"]
    for sym, g in df.groupby("symbol"):
        best = g.groupby("day")["rank"].transform("min")
        use = g[g["rank"] == best].sort_values(["t", "rank"], kind="stable").drop_duplicates("t", keep="first")
        h1 = synth(use[cols], "H1")[-tail:]
        h4 = synth(use[cols], "H4")[-tail:]
        # 原始 15 分 K 也吐給前端（2026-09-25，Andy：「已經有 15 分 K，1H & 4H 理論上可以透過 15 分 K 計算」）。
        # 前端選「15 分／30 分」時看得到多日，1H／4H 跟它是同一份資料切出來的。
        # 15m 那幾盤照原樣；1m（mis）那幾盤聚合成 15 分；只有 60 分的日子沒有 15 分（顆粒不夠，不假造）。
        parts = []
        r15 = use[use["iv"] == "15m"]
        if not r15.empty:
            parts += [[int(r.t), float(r.open), float(r.high), float(r.low), float(r.close),
                       float(r.volume) if pd.notna(r.volume) else 0.0] for r in r15[cols].itertuples(index=False)]
        r1 = use[use["iv"] == "1m"]
        if not r1.empty:
            parts += bucket(r1[cols], 900)
        m15 = sorted(parts, key=lambda b: b[0])
        mis_days = sorted(set(r1["day"]))
        all_days = sorted(set(use["day"]))
        out[str(sym)] = {"H1": h1, "H4": h4, "M15": m15[-tail:],
                         "src": {"rows": int(len(use)),
                                 "days15": len({trade_day_of(b[0]) for b in m15}),
                                 "days": len(all_days),
                                 "first": _day_str(all_days[0]) if all_days else None,
                                 "last": _day_str(all_days[-1]) if all_days else None,
                                 "mis_first": _day_str(mis_days[0]) if mis_days else None,
                                 "mis_days": len(mis_days)}}
    return out


def ticks_to_60m(ticks: pd.DataFrame) -> pd.DataFrame:
    """期貨逐筆（FinMind TaiwanFuturesTick）→ 近月 60 分 K，分日盤 FUT／夜盤 FUT_N。

    逐筆欄位：date（"YYYY-MM-DD HH:MM:SS"，台北時間）, contract_date, price, volume。
    近月＝那一個盤裡成交量最大的單一月份（帶 `/` 的是價差單，丟掉）—— 跟日 K 的 `_near_month` 同一口徑。
    """
    if ticks is None or ticks.empty or "date" not in ticks.columns or "price" not in ticks.columns:
        return pd.DataFrame()
    d = ticks.copy()
    d["ts"] = d["date"]
    for c in ("open", "high", "low", "close"):
        d[c] = d["price"]
    return kbar_to_60m(d, futures=True)


def kbar_to_60m(kbar: pd.DataFrame, symbol: str | None = None, futures: bool = False) -> pd.DataFrame:
    """1 分 K（或逐筆，已轉成 ts/open/high/low/close/volume）→ 60 分 K，照 session_key 切。

    為什麼存 60 分而不是 1 分（2026-09-25）：`build()` 的合成只需要整點以下的顆粒，
    60 分由 1 分聚合時高低點是真的盤中極值；存 60 分每天每個指數只有 5 列，資料湖不會被 1 分 K 撐大。
    futures=True：分日盤 FUT／夜盤 FUT_N，每個盤挑成交量最大的單一月份當近月（價差單帶 `/`，丟掉）。
    否則整份都標成 `symbol`（例：OTC）。指數量固定 0 也照存。
    """
    if kbar is None or kbar.empty or "ts" not in kbar.columns:
        return pd.DataFrame()
    d = kbar.copy()
    if futures:
        d = d[~d.get("contract_date", pd.Series("", index=d.index)).astype(str).str.contains("/", na=False)]
    for c in ("open", "high", "low", "close"):
        d[c] = pd.to_numeric(d.get(c), errors="coerce")
    d["volume"] = pd.to_numeric(d.get("volume"), errors="coerce").fillna(0)
    d = d[d["close"] > 0]
    if d.empty:
        return pd.DataFrame()
    d["open"] = d["open"].fillna(d["close"])
    d["high"] = d["high"].fillna(d["close"])
    d["low"] = d["low"].fillna(d["close"])
    d["t"] = wall_seconds(d["ts"])
    d = d.dropna(subset=["t"])
    d["t"] = d["t"].astype("int64")
    d["day"] = d["t"].map(trade_day_of)
    minute = (d["t"] % 86400) // 60
    d["night"] = (minute >= NIGHT_START) | (minute < NIGHT_END)
    rows = []
    for (day, night), g in d.groupby(["day", "night"]):
        if futures:
            cd = g.get("contract_date", pd.Series("", index=g.index)).astype(str)
            near = g.groupby(cd)["volume"].sum().idxmax()
            g = g[cd == near]
            sym = "FUT_N" if night else "FUT"
        else:
            sym = symbol
        g = g.sort_values("t", kind="stable")
        for b in synth(g[["t", "open", "high", "low", "close", "volume"]], "H1"):
            ts = (pd.Timestamp("1970-01-01") + pd.Timedelta(seconds=b[0])).tz_localize(TZ)
            rows.append({"ts": ts.isoformat(), "symbol": sym,
                         "interval": "60m", "open": b[1], "high": b[2], "low": b[3],
                         "close": b[4], "volume": b[5]})
    return pd.DataFrame(rows)
