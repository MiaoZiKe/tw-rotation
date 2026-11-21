"""全市場三大法人買賣超日序列（「三大法人買賣超日報」的資料）。

口徑（Andy 2026-10-20：會拿別站的證交所公告值比對，所以以官方值為主）：
  · 官方值：資料湖 inst_market_daily（FinMind TaiwanStockTotalInstitutionalInvestors，上市，單位元），
    淨買賣超 ＝ buy − sell，換成億元。外資含外資自營商、自營商含自行買賣與避險。
  · 官方值還沒進湖的日子才用估算補：inst_daily（個股別，股）× 當日收盤價，**只加總上市（TWSE）個股**
    （官方值只有上市，上櫃混進來會對不上），每列標 est=True，前端畫面標「估算」。
    估算只補涵蓋 ≥ 60%（分母＝當天有收盤價的上市個股）的日子，半套的日子不補。
  · ★ 首次公布版優先（2026-10-25，10/21 外資 +9.60 億 vs 本站 +22.39 億的根因）：
    證交所 15:00 公布「三大法人買賣金額統計表」，新聞（時報、鉅亨、中央社）引用的就是這一版；
    FinMind 同一個資料集晚間會換成另一版（實測 10/21：外資買進 3,353→3,471 億、賣出 3,344→3,448 億，
    買賣兩邊一起變大、自營商買進完全不變 —— 研判是 15:00 之後才成交的盤後交易被補進去，中信心，未見官方說明）。
    inst_market_daily 是後到覆蓋，存到的是晚間版；首次抓到的那版另存 inst_market_first（先到的贏）。
    有首次公布版的日子用它（＝新聞口徑），晚間版若不同就放在 rev 欄位、不丟掉；沒有首次版的日子（表建立前的歷史）用晚間版。
  · 加權指數收盤取自 index_ohlc（symbol=TSE）。
  · 只給最近 MAX_DAYS 個交易日（5 年），前端期間鈕自己切。
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

MAX_DAYS = 1300
YI = 1e8
COVER = 0.6      # 估算涵蓋門檻：有法人資料的上市個股 ≥ 當天上市個股的 60%


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
    # 涵蓋率＝當天有法人資料的上市個股數 ÷ 當天有收盤價的上市個股數（≥ 60% 才補）。
    # 舊做法拿「近 250 天最多那天」當分母，上市上櫃混算，最新日只要法人表晚出就一直退回舊日。
    pp = price
    if "market" in pp.columns:
        pp = pp[pp["market"].astype(str).str.upper() == "TWSE"]
    denom = pp.drop_duplicates(["date", "code"]).groupby(pp["date"].astype(str)).size()
    ii = inst.merge(pp[["date", "code"]].drop_duplicates(), on=["date", "code"], how="inner")
    cnt = ii.drop_duplicates(["date", "code"]).groupby(ii["date"].astype(str)).size()
    full = {d for d, n in cnt.items() if denom.get(d, 0) and n / denom[d] >= COVER}
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


SEED = Path(__file__).resolve().parent.parent / "seeds" / "inst_market_first_seed.csv"


def with_seed(first: pd.DataFrame | None, seed_path: Path | None = None) -> pd.DataFrame:
    """湖裡的首次公布版 ∪ 種子檔（git 歷史還原的首次版）。同一天湖裡有就用湖裡的。

    build_payload 直接讀種子 → 部署當下就生效，不必等下一個交易日的每日管線把種子寫進湖。
    """
    parts = [x for x in (first,) if x is not None and not x.empty]
    try:
        seed = pd.read_csv(seed_path or SEED, dtype={"date": str})
        if not seed.empty:
            parts.append(seed)
    except Exception:  # noqa: BLE001 —— 種子讀不到就只用湖裡的
        pass
    if not parts:
        return pd.DataFrame()
    out = pd.concat(parts, ignore_index=True)
    out["date"] = out["date"].astype(str)
    return out.drop_duplicates("date", keep="first").reset_index(drop=True)


REV_EPS = 0.005  # 億元；首次版與晚間版差不到這個數（四捨五入到 0.01 後看不出來）就不附 rev


def _prefer_first(off: pd.DataFrame, first: pd.DataFrame) -> pd.DataFrame:
    """同一天兩版都有 → 數字用首次公布版，晚間版放 rev_*；只有其中一版 → 用那一版。"""
    if first is None or first.empty:
        return off.assign(first=False)
    fo = _official(first)
    if fo.empty:
        return off.assign(first=False)
    m = fo.merge(off, on="date", how="outer", suffixes=("", "_rev"))
    for k in ("f", "t", "d", "tot"):
        m[k] = m[k].where(m[k].notna(), m[k + "_rev"])
    m["first"] = m["date"].isin(set(fo["date"]))
    return m


def series(mkt: pd.DataFrame, inst: pd.DataFrame, price: pd.DataFrame, ohlc: pd.DataFrame,
           first: pd.DataFrame | None = None) -> dict:
    """回傳 {unit, basis, rows:[{d,f,t,dl,tot,tw,est[,first][,rev]}], official_from, n_est, n_rev}；rows 由舊到新。

    first：inst_market_first（首次公布版，欄位同 inst_market_daily）。給了就以它為準，見模組說明。
    rev：{f,t,dl,tot}＝同一天晚間修訂版（只有和首次版差 ≥ 0.005 億時才附）。
    """
    off = _prefer_first(_official(mkt), first)
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
    rows = []
    for r in allr.to_dict("records"):
        row = {"d": r["date"], "f": round(r["f"], 2), "t": round(r["t"], 2), "dl": round(r["d"], 2), "tot": round(r["tot"], 2),
               "tw": None if pd.isna(r["tw"]) else round(float(r["tw"]), 2), "est": bool(r["est"])}
        fst = r.get("first")
        if isinstance(fst, (bool, np.bool_)) and bool(fst):
            row["first"] = True
            rv = {"f": r.get("f_rev"), "t": r.get("t_rev"), "dl": r.get("d_rev"), "tot": r.get("tot_rev")}
            if all(v is not None and not pd.isna(v) for v in rv.values()) and any(
                    abs(rv[k] - row[k]) >= REV_EPS for k in rv):
                row["rev"] = {k: round(float(v), 2) for k, v in rv.items()}
        rows.append(row)
    return {"unit": "億元", "n_est": int(allr["est"].sum()), "rows": rows,
            "n_rev": sum(1 for r in rows if "rev" in r),
            "basis": "上市；證交所 15:00 首次公布值（與新聞同）；外資含外資自營商、自營商含自行買賣與避險；"
                     "晚間修訂值放 rev；est＝官方值未到、以個股股數×收盤估算",
            "official_from": next((r["d"] for r in rows if not r["est"]), None)}
