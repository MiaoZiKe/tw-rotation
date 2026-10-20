"""全市場三大法人買賣超日序列（「三大法人買賣超日報」的資料）。

口徑（Andy 2026-10-20：會拿別站的證交所公告值比對，所以以官方值為主）：
  · 官方值：資料湖 inst_market_daily（FinMind TaiwanStockTotalInstitutionalInvestors，上市，單位元），
    淨買賣超 ＝ buy − sell，換成億元。外資含外資自營商、自營商含自行買賣與避險。
  · 官方值還沒進湖的日子才用估算補：inst_daily（個股別，股）× 當日收盤價，**只加總上市（TWSE）個股**
    （官方值只有上市，上櫃混進來會對不上），每列標 est=True，前端畫面標「估算」。
    估算只補涵蓋 ≥ 60% 的完整日（法人表上市上櫃分開落地，半套的日子不補）。
  · 加權指數收盤取自 index_ohlc（symbol=TSE）。
  · 只給最近 MAX_DAYS 個交易日（5 年），前端期間鈕自己切。
"""
from __future__ import annotations

import pandas as pd

MAX_DAYS = 1300
YI = 1e8


def _official(mkt: pd.DataFrame) -> pd.DataFrame:
    if mkt is None or mkt.empty:
        return pd.DataFrame(columns=["date", "f", "t", "d", "tot"])
    m = mkt.drop_duplicates("date", keep="last").copy()
    out = pd.DataFrame({"date": m["date"].astype(str)})
    for k, n in (("f", "foreign"), ("t", "trust"), ("d", "dealer"), ("tot", "total")):
        out[k] = (m[n + "_buy"] - m[n + "_sell"]) / YI
    return out.dropna(subset=["f", "t", "d"])


def _estimate(inst: pd.DataFrame, price: pd.DataFrame, skip: set, dates: list) -> pd.DataFrame:
    """官方值缺的完整日，用股數×收盤估算（只算上市）。"""
    if inst is None or inst.empty or price is None or price.empty or not dates:
        return pd.DataFrame(columns=["date", "f", "t", "d", "tot"])
    cnt = inst.groupby("date").size()
    full = set(cnt[cnt >= cnt.tail(250).max() * 0.6].index.astype(str))
    want = [d for d in dates if d in full and d not in skip]
    if not want:
        return pd.DataFrame(columns=["date", "f", "t", "d", "tot"])
    i = inst[inst["date"].astype(str).isin(want)].drop_duplicates(["date", "code"], keep="last")
    p = price[price["date"].astype(str).isin(want)].drop_duplicates(["date", "code"], keep="last")
    if "market" in p.columns:
        p = p[p["market"].astype(str).str.upper() == "TWSE"]
    j = i.merge(p[["date", "code", "close"]], on=["date", "code"], how="inner")
    j = j[j["close"] > 0]
    for c in ("foreign_total", "trust", "dealer"):
        j[c] = pd.to_numeric(j[c], errors="coerce").fillna(0.0) * j["close"] / YI
    g = j.groupby(j["date"].astype(str))[["foreign_total", "trust", "dealer"]].sum().reset_index()
    g.columns = ["date", "f", "t", "d"]
    g["tot"] = g["f"] + g["t"] + g["d"]
    return g


def series(mkt: pd.DataFrame, inst: pd.DataFrame, price: pd.DataFrame, ohlc: pd.DataFrame) -> dict:
    """回傳 {unit, rows:[{d,f,t,dl,tot,tw,est}], official_from, n_est}；rows 由舊到新。"""
    off = _official(mkt)
    tw = pd.DataFrame(columns=["date", "tw"])
    if ohlc is not None and not ohlc.empty:
        o = ohlc[ohlc["symbol"] == "TSE"].drop_duplicates("date", keep="last")
        tw = pd.DataFrame({"date": o["date"].astype(str), "tw": o["close"]})
    days = sorted(set(tw["date"]) if not tw.empty else set())
    days = days[-MAX_DAYS:]
    est = _estimate(inst, price, set(off["date"]), days)
    off["est"] = False
    est["est"] = True
    allr = pd.concat([off, est], ignore_index=True).drop_duplicates("date", keep="first")
    if days:
        allr = allr[allr["date"].isin(days)]     # 以加權交易日為準（排除補班日之類資料雜訊）
    allr = allr.merge(tw, on="date", how="left").sort_values("date").tail(MAX_DAYS)
    rows = [{"d": r.date, "f": round(r.f, 2), "t": round(r.t, 2), "dl": round(r.d, 2), "tot": round(r.tot, 2),
             "tw": None if pd.isna(r.tw) else round(float(r.tw), 2), "est": bool(r.est)} for r in allr.itertuples()]
    return {"unit": "億元", "n_est": int(allr["est"].sum()), "rows": rows,
            "official_from": next((r["d"] for r in rows if not r["est"]), None)}
