"""大戶／散戶買賣（推估）：用 mis 連續快照的增量，把成交量分成「大單／小單」×「外盤（主動買）／內盤（主動賣）」。

Andy 2026-11-07：「個股可以看到 大戶 散戶 當前買賣狀況，即時的資訊 以及 日K級別資訊 這功能記得也要顯在權限內 但暫不開放」。
查證與口徑全文：docs/bigsmall_sources.md。這支是純函式（不打網路），盤中收集器（sources/bigsmall_collect.py）
與前端即時面板（site/bigsmall.js 的 step()）用**同一套規則**，tests/test_bigsmall.py 用同一組向量對兩邊。

為什麼是「推估」：免費合規來源都沒有逐筆成交（FinMind TaiwanStockPriceTick 要贊助等級，2026-11-07 probe/bigsmall 實測回
「Your level is register」）。mis（白名單 #108）每次快照只給「最近一筆成交」的張數 tv 與價 z、累計量 v、五檔。
兩次快照之間如果成交了好幾筆，我們只看得到最後一筆 —— 其餘的量（「沒看到的量」）用當天已看到的單筆大小分布按比例分攤。

規則（每檔、每次快照 i 對上一次 i−1）：
  1. dv ＝ v_i − v_{i−1}（張）。dv ≤ 0 → 只更新五檔，不計量。第一次快照只當基準（之前的量記成「開始收集前」）。
  2. 價 p ＝ z → trade.z → 上一次的 p（z 是 '-' 時，mis 把最近一筆放在 trade 子物件）。
  3. 方向（內外盤，Lee–Ready 精神）：p ≥ 上一次的最佳賣價 → 外盤（+1，主動買）；p ≤ 上一次的最佳買價 → 內盤（−1，主動賣）；
     落在買賣價中間 → 跟上一筆價比（漲＝+1、跌＝−1），平盤沿用上一次的方向；都沒有 → 0（不分方向）。
  4. 集合競價（09:00:00 開盤那一筆、13:30:00 收盤那一筆）一律記「集合競價」，不分方向、不分大小 —— 那是一次撮合大家的單，
     不是誰主動追價。
  5. 這次看得到的那一筆：tv 張（0 < tv ≤ dv 才算數），金額 tv×1000×p ≥ 大單門檻 → 大單，否則小單。
  6. 沒看到的量 r ＝ dv − tv：按「當天到目前為止看到的大單量 ÷ 看到的總量」分攤成大單／小單；
     當天還沒看到任何一筆時，把 r 當成一筆看（r×1000×p 比門檻）—— 這是一般 Level-1 快照軟體的做法，會高估大單，所以只用在開頭。
  7. 方向 0 的量進「不分方向」，不進買或賣。

大單門檻（元）＝ max(100 萬元, 4 × 該檔近 20 個交易日「平均每筆成交金額」)：
  固定 100 萬元會讓台積電（一張就超過 100 萬）每一筆都是大單；用自己的平均單筆金額當尺度，大小單在每一檔的意義才接近。
  平均每筆成交金額＝證交所日成交資訊的成交金額 ÷ 成交筆數（price_daily turnover ÷ transactions）。
"""
from __future__ import annotations

from dataclasses import dataclass, field

BIG_FLOOR = 1_000_000          # 大單門檻下限（元）
AVG_MULT = 4                   # 門檻 ＝ 平均每筆成交金額 × 這個倍數（至少 BIG_FLOOR）
AUCTION_OPEN, AUCTION_CLOSE = "09:00:00", "13:30:00"
SERIES_STEP_MIN = 5            # 日內走勢一格 5 分鐘（跟 tape 同一個尺度）


def threshold(avg_trade_amount: float | None) -> float:
    try:
        a = float(avg_trade_amount or 0)
    except (TypeError, ValueError):
        a = 0.0
    return max(float(BIG_FLOOR), AVG_MULT * a) if a == a else float(BIG_FLOOR)


def _num(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if x == x else None


def _first(s):
    if not s:
        return None
    return _num(str(s).split("_")[0])


@dataclass
class Acc:
    """一檔一天的累計。量的單位是張，金額是元。"""
    thr: float = float(BIG_FLOOR)
    v0: float | None = None          # 開始收集時的累計量（之前的量沒看到，記成 pre）
    v: float | None = None
    p: float | None = None
    ask: float | None = None
    bid: float | None = None
    dir: int = 0
    big_buy: float = 0.0
    big_sell: float = 0.0
    small_buy: float = 0.0
    small_sell: float = 0.0
    big_buy_amt: float = 0.0
    big_sell_amt: float = 0.0
    small_buy_amt: float = 0.0
    small_sell_amt: float = 0.0
    neutral: float = 0.0             # 不分方向（含集合競價）
    auction: float = 0.0             # 其中集合競價
    seen: float = 0.0                # 真的看到單筆大小的量（tv 加總）
    seen_big: float = 0.0
    polls: int = 0
    first_t: str = ""
    last_t: str = ""
    series: list = field(default_factory=list)   # [[HH:MM, 大單淨額(張), 小單淨額(張)]] 每 5 分鐘一格（該格最後一次快照的累計值）

    # ------------------------------------------------------------ 主要規則
    def step(self, m: dict) -> None:
        """吃一次 mis 的一列（msgArray 的一個元素，原樣）。"""
        v = _num(m.get("v"))
        t = str(m.get("t") or (m.get("trade") or {}).get("t") or "")
        ask, bid = _first(m.get("a")), _first(m.get("b"))
        self.polls += 1
        if v is None:
            return
        p = _num(m.get("z"))
        if p is None:
            p = _num((m.get("trade") or {}).get("z"))
        if p is None:
            p = self.p
        if self.v is None:                                   # 第一次＝基準
            self.v0 = self.v = v
            self.p, self.ask, self.bid = p, ask or self.ask, bid or self.bid
            self.first_t = self.last_t = t
            return
        dv = v - self.v
        if dv <= 0 or p is None:
            self.ask, self.bid = ask or self.ask, bid or self.bid
            self.last_t = t or self.last_t
            return
        tv = _num(m.get("tv"))
        if tv is None:
            tv = _num((m.get("trade") or {}).get("v"))
        if tv is None or tv <= 0 or tv > dv:
            tv = 0.0
        if t in (AUCTION_OPEN, AUCTION_CLOSE):
            self.neutral += dv
            self.auction += dv
        else:
            d = 0
            if self.ask is not None and p >= self.ask:
                d = 1
            elif self.bid is not None and p <= self.bid:
                d = -1
            elif self.p is not None and p > self.p:
                d = 1
            elif self.p is not None and p < self.p:
                d = -1
            else:
                d = self.dir
            big = 0.0
            if tv > 0:
                if tv * 1000 * p >= self.thr:
                    big += tv
                    self.seen_big += tv
                self.seen += tv
            r = dv - tv
            if r > 0:
                if self.seen > 0:
                    big += r * (self.seen_big / self.seen)
                elif r * 1000 * p >= self.thr:
                    big += r
            small = dv - big
            if d > 0:
                self.big_buy += big; self.small_buy += small
                self.big_buy_amt += big * 1000 * p; self.small_buy_amt += small * 1000 * p
            elif d < 0:
                self.big_sell += big; self.small_sell += small
                self.big_sell_amt += big * 1000 * p; self.small_sell_amt += small * 1000 * p
            else:
                self.neutral += dv
            if d:
                self.dir = d
        self.v, self.p = v, p
        self.ask, self.bid = ask or self.ask, bid or self.bid
        self.last_t = t or self.last_t
        self._mark(t)

    def _mark(self, t: str) -> None:
        if len(t) < 5:
            return
        h, mi = int(t[:2]), int(t[3:5])
        slot = h * 60 + mi - (h * 60 + mi) % SERIES_STEP_MIN
        hm = f"{slot // 60:02d}:{slot % 60:02d}"
        pt = [hm, round(self.big_buy - self.big_sell, 1), round(self.small_buy - self.small_sell, 1)]
        if self.series and self.series[-1][0] == hm:
            self.series[-1] = pt
        else:
            self.series.append(pt)

    # ------------------------------------------------------------ 輸出
    def row(self, date: str, code: str) -> dict:
        obs = (self.v - self.v0) if (self.v is not None and self.v0 is not None) else 0.0
        return {
            "date": date, "code": code,
            "big_buy": round(self.big_buy, 1), "big_sell": round(self.big_sell, 1),
            "small_buy": round(self.small_buy, 1), "small_sell": round(self.small_sell, 1),
            "big_net_amt": round(self.big_buy_amt - self.big_sell_amt),
            "small_net_amt": round(self.small_buy_amt - self.small_sell_amt),
            "neutral": round(self.neutral, 1), "auction": round(self.auction, 1),
            "observed": round(obs, 1), "pre": round(self.v0 or 0.0, 1),
            "sampled": round(self.seen, 1),
            "coverage": round(self.seen / obs, 4) if obs > 0 else None,
            "threshold": round(self.thr), "polls": self.polls,
            "first_t": self.first_t, "last_t": self.last_t,
            "close": self.p, "src": "mis-snap",
        }


COLUMNS = ["date", "code", "big_buy", "big_sell", "small_buy", "small_sell", "big_net_amt", "small_net_amt",
           "neutral", "auction", "observed", "pre", "sampled", "coverage", "threshold", "polls", "first_t", "last_t",
           "close", "src"]


def avg_trade_amount(price_daily, days: int = 20) -> dict:
    """每檔近 N 個交易日的平均每筆成交金額（元）＝ Σ成交金額 ÷ Σ成交筆數。缺欄位或筆數 0 的略過。"""
    out: dict[str, float] = {}
    if price_daily is None or price_daily.empty or not {"turnover", "transactions"} <= set(price_daily.columns):
        return out
    df = price_daily[["date", "code", "turnover", "transactions"]].dropna()
    if df.empty:
        return out
    ds = sorted(df["date"].astype(str).unique())[-days:]
    df = df[df["date"].astype(str).isin(ds)]
    g = df.groupby(df["code"].astype(str)).sum(numeric_only=True)
    for code, r in g.iterrows():
        if r["transactions"] > 0 and r["turnover"] > 0:
            out[str(code)] = float(r["turnover"]) / float(r["transactions"])
    return out


def stock_payload(rows, kline=None, holders=None) -> dict:
    """一檔的前端 JSON：每日大單／小單淨額（張、元）＋涵蓋率＋口徑；kline 給股價日 K 對照（[date, o, h, l, c]）。"""
    days = []
    for r in rows:
        days.append([str(r["date"])[:10],
                     round(float(r["big_buy"]) - float(r["big_sell"]), 1),
                     round(float(r["small_buy"]) - float(r["small_sell"]), 1),
                     int(r["big_net_amt"] or 0), int(r["small_net_amt"] or 0),
                     r.get("coverage"), float(r.get("pre") or 0), float(r.get("observed") or 0),
                     int(r.get("threshold") or BIG_FLOOR)])
    return {
        "cols": ["date", "big_net", "small_net", "big_net_amt", "small_net_amt", "coverage", "pre", "observed", "threshold"],
        "days": days, "k": kline or [], "holders": holders or [],
        "method": {"floor": BIG_FLOOR, "mult": AVG_MULT, "src": "mis 快照推估（docs/bigsmall_sources.md）"},
    }


def export(site_data, price_daily, lake_rows) -> dict:
    """寫 site/data/bigsmall/：每檔一支 <code>.json（有收集到的才寫）＋ _thr.json（全部代號的今日大單門檻，給即時面板用）。

    lake_rows：資料湖 bigsmall_daily 全表（空也要寫 _thr.json，即時面板才有門檻）。回傳摘要（寫進 log）。
    前端只在功能鍵 stock.bigsmall 開著時才去抓這些檔（site/bigsmall.js），所以不加大個股 JSON。
    """
    import json

    import pandas as pd

    out = site_data / "bigsmall"
    out.mkdir(parents=True, exist_ok=True)
    avg = avg_trade_amount(price_daily)
    thr = {c: round(threshold(a)) for c, a in avg.items()}
    (out / "_thr.json").write_text(json.dumps({"floor": BIG_FLOOR, "mult": AVG_MULT, "thr": thr}, ensure_ascii=False), encoding="utf-8")
    n = 0
    first = last = None
    if lake_rows is not None and not lake_rows.empty:
        df = lake_rows.copy()
        df["date"] = df["date"].astype(str).str[:10]
        df = df.sort_values(["code", "date"])
        first, last = df["date"].min(), df["date"].max()
        for code, g in df.groupby(df["code"].astype(str)):
            rows = g.where(pd.notna(g), None).to_dict("records")
            pl = stock_payload(rows[-250:])
            pl["thr"] = thr.get(code, BIG_FLOOR)
            (out / f"{code}.json").write_text(json.dumps(pl, ensure_ascii=False), encoding="utf-8")
            n += 1
    return {"codes": n, "first": first, "last": last, "thr": len(thr)}
