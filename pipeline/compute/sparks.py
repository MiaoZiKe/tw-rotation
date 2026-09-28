"""搜尋下拉的迷你走勢圖（site/data/sparks.json）。

Andy 2026-09-28：「搜尋欄位的對應股票旁需要出現小小的分時走勢圖，只要走勢圖就好不用數據因為只是參考」。

一檔一個字串，前端畫成 48×16 的小折線，不帶任何數字、不畫軸。所以這份檔案只存「形狀＋漲跌方向」：
  - 價格先壓成 0～63 的 64 階（一個字元一個點），形狀夠用、檔案小；
  - 開頭兩個字元：種類（i＝最近一個交易日的分時、d＝最近 20 個交易日的日收盤）＋方向（+ 漲、- 跌、= 平）。

資料來源（只讀資料湖，不打任何外部端點 —— CLAUDE.md「build_payload 對湖裡的東西只准讀」）：
  ① 分時：資料湖 `intraday_60m` 裡「最近一個交易日」那一天的 60 分 K。
     ⚠ 資料湖裡個股最細只有 60 分 K（1／5／15 分依 DECISIONS #156 只在前端當天即時抓、不進湖），
     所以一天最多 6 個點：09:00 開盤價＋每根 60 分 K 的收盤（10:00、11:00、12:00、13:00、13:30）。
     不拿每根 K 棒的最高／最低去「猜」盤中順序補點 —— 那是編出來的路徑，不是資料。
     那一天必須等於日線的最新交易日；60 分 K 落後（還沒寫進湖）就不當分時用，改走 ②，
     免得搜尋下拉把前天的分時當成今天。
  ② 沒有分時的股票（不在分 K 名單、或 60 分 K 落後）：最近 20 個交易日的日收盤（還原價，跟 K 線同一套），
     方向＝最後一天對 20 天前那一天（這條線畫的就是這 20 天，顏色要跟線的走向同一件事）。
  分時的方向＝最後一點對「前一個交易日收盤」（也就是當天漲跌，跟下拉右邊的漲跌幅同一件事）。
"""
from __future__ import annotations

import pandas as pd

ABC = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"   # 64 階，JSON 裡不必跳脫
LEVELS = len(ABC)
DAILY_N = 20


def encode(points: list[float]) -> str:
    """價格序列 → 64 階字串（最低＝'0'、最高＝'_'；整條一樣高就全部放中間）。"""
    lo, hi = min(points), max(points)
    if hi - lo < 1e-9:
        return ABC[LEVELS // 2] * len(points)
    return "".join(ABC[int(round((p - lo) / (hi - lo) * (LEVELS - 1)))] for p in points)


def _dir(last: float, base: float | None) -> str:
    if base is None or base != base:        # NaN
        return "="
    if last > base + 1e-9:
        return "+"
    if last < base - 1e-9:
        return "-"
    return "="


def intraday_points(bars: pd.DataFrame) -> list[float]:
    """同一天的 60 分 K（依時間排好）→ 開盤價＋每根收盤。"""
    b = bars.sort_values("ts")
    pts = [float(b["open"].iloc[0])] + [float(x) for x in b["close"]]
    return [p for p in pts if p == p and p > 0]


def build(price: pd.DataFrame, m60: pd.DataFrame, latest: str, codes: list[str] | None = None) -> dict:
    """price：日線（date, code, close；用還原價）；m60：資料湖 intraday_60m 最近一兩個月；
    latest：日線最新交易日；codes：要產出的股票（通常＝stocks.json 的全市場索引）。"""
    out: dict[str, str] = {}
    stat = {"intraday": 0, "daily": 0, "none": 0}
    want = set(codes) if codes is not None else None

    px = price[["date", "code", "close"]].copy()
    px["date"] = px["date"].astype(str)
    px = px[(px["date"] <= latest) & (px["close"] > 0)]
    if want is not None:
        px = px[px["code"].isin(want)]
    # 每檔只要最近 21 天（20 天的線＋分時要的前一日收盤）
    px = px.sort_values(["code", "date"]).groupby("code", sort=False).tail(DAILY_N + 1)
    daily_by = {c: g for c, g in px.groupby("code", sort=False)}

    intra_by: dict[str, pd.DataFrame] = {}
    if m60 is not None and not m60.empty:
        m = m60.copy()
        m["ts"] = m["ts"].astype(str)
        m = m[m["ts"].str.slice(0, 10) == latest]          # 只認「就是最新交易日」那一天
        if want is not None:
            m = m[m["code"].astype(str).isin(want)]
        intra_by = {str(c): g for c, g in m.groupby("code", sort=False)}

    for code in (codes if codes is not None else sorted(daily_by)):
        g = daily_by.get(code)
        closes = [float(x) for x in g["close"]] if g is not None else []
        dates = list(g["date"]) if g is not None else []
        ib = intra_by.get(code)
        if ib is not None and len(ib) >= 1:
            pts = intraday_points(ib)
            if len(pts) >= 2:
                # 前一個交易日收盤：日線裡 latest 之前的最後一天
                prev = next((closes[i] for i in range(len(dates) - 1, -1, -1) if dates[i] < latest), None)
                out[code] = "i" + _dir(pts[-1], prev) + encode(pts)
                stat["intraday"] += 1
                continue
        tail = closes[-DAILY_N:]
        if len(tail) >= 2:
            out[code] = "d" + _dir(tail[-1], tail[0]) + encode(tail)
            stat["daily"] += 1
        else:
            stat["none"] += 1
    return {"v": 1, "asof": latest, "abc": ABC, "n": DAILY_N, "stat": stat, "s": out}
