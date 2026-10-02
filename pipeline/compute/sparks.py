"""迷你走勢圖（site/data/sparks.json）：搜尋下拉、自選頁每一列、手機加入清單抽屜共用。

Andy 2026-09-28：「搜尋欄位的對應股票旁需要出現小小的分時走勢圖，只要走勢圖就好不用數據因為只是參考」。
Andy 2026-10-02：「這搜尋以及自選內上的走勢小圖有點不精確，幫我精確點，並需要有外框或其他繪製輔助走勢圖」
  → v2（DECISIONS #290）。v1 的三個不精確：
    ① 分時一天只有 6 點（開盤＋5 根 60 分 K 收盤），畫出來只剩幾個轉折；
    ② 小圖畫「最近一天」、自選展開大圖畫「最近 5 個交易日」—— 期間不同，形狀當然對不起來；
    ③ 每一檔都把自己的最低～最高撐滿整格（只存 64 階形狀、不存價位），0.3% 的波動看起來跟漲停一樣，
       也畫不出昨收／起點線、算不出漲跌幅。

v2 的口徑 —— **跟自選展開大圖（site/app.js 的 trendSeries）逐點相同，改一邊一定要改另一邊**：
  ① 分時（種類 i）：資料湖 `intraday_60m` 的「最近 5 個交易日」，每一天＝09:00 開盤價＋每根 60 分 K 收盤
     （10:00、11:00、12:00、13:00、13:30），一天 6 點、5 天 30 點。
     · 條件：60 分 K 的最後一天必須等於這一檔日線的最後一天（落後就不當分時，免得把前天當成最新）。
     · 最新一天的最後一點換成日線正式收盤（60 分 K 不含收盤集合競價）。
     · 不拿每根 K 棒的最高／最低去「猜」盤中順序補點 —— 那是編出來的路徑，不是資料。
  ② 沒有分時的股票（不在分 K 名單、或 60 分 K 落後）：最近 60 個交易日的日收盤（還原價，跟 K 線同一套）。
  基準（虛線）＝**昨收**：日線倒數第二天的收盤（還原價；最新一天遇到除權息時，它就等於參考價）。只有一天資料就用第一點。
  方向（紅漲綠跌）＝最後一點對昨收 —— 跟列上的「漲跌幅」同一件事、同一個顏色。
  為什麼不用「窗口前一天收盤」當基準：那樣小圖畫的是 5 日／60 日漲跌，緊鄰的漲跌幅欄是當日漲跌，
  常常一紅一綠並排（實測 2330 09-24：5 日 +2.06% 紅、當日 -1.00% 綠），看起來像資料打架。
  期間漲跌（訖／起）照樣寫在提示框裡。

一檔一個陣列（JSON 裡用陣列不用物件，省掉每檔重複的鍵名；全市場約 2,300 檔）：
  [形狀字串, 最低, 最高, 基準, 第一點, 最後一點, 起日, 訖日, 基準日, 每天點數]
  形狀字串＝種類（i／d）＋方向（+／-／=）＋每點一個字元（最低～最高壓成 64 階）。
  最低／最高／第一點／最後一點／基準是**真實價位**：前端用它把 64 階還原成價格、決定 Y 軸範圍
  （包含基準線、留白、最小振幅），提示框的起訖價與漲跌幅也直接讀這幾個數字，不從 64 階反推。
  日期一律 'MM/DD'（只拿來顯示）；每天點數是 i 種類才有的字串（例：'66666'），前端拿來畫日分隔線。

資料來源只讀資料湖，不打任何外部端點（CLAUDE.md「build_payload 對湖裡的東西只准讀」），也不增加任何抓取頻率。
"""
from __future__ import annotations

import pandas as pd

ABC = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"   # 64 階，JSON 裡不必跳脫
LEVELS = len(ABC)
DAILY_N = 60          # 沒有分時的股票：最近 60 個交易日收盤（跟自選展開大圖的退路同一個數字）
INTRA_DAYS = 5        # 分時：最近 5 個交易日（跟自選展開大圖同一個數字）


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


def _r(x: float) -> float | int:
    """價位寫進 JSON：最多 2 位小數、整數就不帶 .0（跟 m60 檔同一套省字元的做法）。"""
    f = round(float(x), 2)
    return int(f) if f == int(f) else f


def _md(d: str) -> str:
    return f"{d[5:7]}/{d[8:10]}" if d and len(d) >= 10 else ""


def intraday_points(bars: pd.DataFrame) -> list[float]:
    """同一天的 60 分 K（依時間排好）→ 開盤價＋每根收盤。"""
    b = bars.sort_values("ts")
    pts = [float(b["open"].iloc[0])] + [float(x) for x in b["close"]]
    return [p for p in pts if p == p and p > 0]


def _pack(kind: str, pts: list[float], base: float | None, d0: str, d1: str, bd: str, per_day: str = "") -> list:
    b = base if base is not None and base == base and base > 0 else pts[0]
    return [kind + _dir(pts[-1], b) + encode(pts), _r(min(pts)), _r(max(pts)), _r(b), _r(pts[0]), _r(pts[-1]),
            _md(d0), _md(d1), _md(bd), per_day]


def build(price: pd.DataFrame, m60: pd.DataFrame, latest: str, codes: list[str] | None = None) -> dict:
    """price：日線（date, code, close；用還原價）；m60：資料湖 intraday_60m 最近一兩個月；
    latest：日線最新交易日；codes：要產出的股票（通常＝stocks.json 的全市場索引）。"""
    out: dict[str, list] = {}
    stat = {"intraday": 0, "daily": 0, "none": 0}
    want = set(codes) if codes is not None else None

    px = price[["date", "code", "close"]].copy()
    px["date"] = px["date"].astype(str)
    px = px[(px["date"] <= latest) & (px["close"] > 0)]
    if want is not None:
        px = px[px["code"].isin(want)]
    # 每檔只要最近 61 天（60 天的線；多拿一天備用）
    px = px.sort_values(["code", "date"]).groupby("code", sort=False).tail(DAILY_N + 1)
    daily_by = {c: g for c, g in px.groupby("code", sort=False)}

    intra_by: dict[str, pd.DataFrame] = {}
    if m60 is not None and not m60.empty:
        m = m60.copy()
        m["ts"] = m["ts"].astype(str)
        m["d"] = m["ts"].str.slice(0, 10)
        m = m[m["d"] <= latest]
        if want is not None:
            m = m[m["code"].astype(str).isin(want)]
        intra_by = {str(c): g for c, g in m.groupby("code", sort=False)}

    for code in (codes if codes is not None else sorted(daily_by)):
        g = daily_by.get(code)
        closes = [float(x) for x in g["close"]] if g is not None else []
        dates = list(g["date"]) if g is not None else []
        ib = intra_by.get(code)
        # ① 分時：60 分 K 的最後一天必須就是這一檔日線的最後一天（停牌的股票兩邊都停在同一天，也算數）
        #    —— 跟前端 trendSeries 同一個條件（前端只拿得到這一檔自己的日線）
        if ib is not None and len(ib) and dates and ib["d"].max() == dates[-1]:
            ib = ib.sort_values("ts")
            days = sorted(ib["d"].unique())
            win = days[-INTRA_DAYS:]
            pts: list[float] = []
            per: list[str] = []
            for d in win:
                p = intraday_points(ib[ib["d"] == d])
                pts += p
                per.append(str(min(len(p), 9)))
            # 最後一點換成日線的正式收盤：60 分 K 最後一根的收盤不含 13:25～13:30 的收盤集合競價
            # （實測 2330 2026-09-24：60 分 K 2,480、正式收盤 2,475），不換的話小圖終點跟列上的現價差一截。
            # 只換最新那一天：還原價在最新一天一定等於原始價，更早的日子遇到除權息會差一個還原係數。
            if pts:
                pts[-1] = closes[-1]
            if len(pts) >= 2:
                base, bd = (closes[-2], dates[-2]) if len(closes) >= 2 else (None, "")
                out[code] = _pack("i", pts, base, win[0], win[-1], bd, "".join(per))
                stat["intraday"] += 1
                continue
        # ② 退路：最近 60 個交易日收盤
        if len(closes) >= 2:
            tail, td = closes[-DAILY_N:], dates[-DAILY_N:]
            out[code] = _pack("d", tail, closes[-2], td[0], td[-1], dates[-2])
            stat["daily"] += 1
        else:
            stat["none"] += 1
    return {"v": 2, "asof": latest, "abc": ABC, "n": DAILY_N, "days": INTRA_DAYS, "stat": stat, "s": out}
