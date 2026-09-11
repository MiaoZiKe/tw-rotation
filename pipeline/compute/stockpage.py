"""個股頁深度資料（v3）：營收、獲利、除權息、資券、大戶散戶、法人、基本資料、本益比歷史。

全部是「把資料湖整理成前端可直接畫的序列」，不做任何預測。
每個函式都容忍該表為空 —— 回補還沒跑到的股票就是會缺，缺就回空清單，前端顯示「尚無資料」。

金融專家的口徑：
- 累計 EPS 用「同一年內各季相加」，跨年歸零；財報是單季值（FinMind 與證交所 t187ap14 都是）。
- 本益比歷史 = 每季財報「可用日」之後的收盤 / 當時可得的近四季 EPS，不偷看未來季報。
- 「大戶」＝集保 1,000 張以上（level 15）；「中實戶」＝400–1,000 張（level 12–14）；
  「散戶」＝10 張以下（level 1–3）。這三個口徑跟坊間籌碼軟體一致。
- 填息天數 = 除息日起，第一個收盤價 ≥ 除息前一日收盤價的交易日數；超過 250 天視為未填息。
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

BIG_LEVEL = 15                 # ≥ 1,000 張
MID_LEVELS = (12, 13, 14)      # 400–1,000 張
RETAIL_LEVELS = (1, 2, 3)      # ≤ 10 張
TOTAL_LEVEL = 17


def _f(x):
    try:
        v = float(x)
        return v if np.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def _r(x, nd=2):
    v = _f(x)
    return round(v, nd) if v is not None else None


# ------------------------------------------------------------------ 營收

def revenue_series(rev: pd.DataFrame, code: str, months: int = 72) -> dict:
    """月營收序列：每月營收、YoY、MoM、累計營收、累計 YoY；另附年度合計方便畫「年度走勢」。"""
    if rev is None or rev.empty:
        return {"monthly": [], "yearly": []}
    g = rev[rev["code"] == code][["ym", "revenue"]].copy()
    if g.empty:
        return {"monthly": [], "yearly": []}
    g["revenue"] = pd.to_numeric(g["revenue"], errors="coerce")
    g = g.dropna(subset=["revenue"]).drop_duplicates("ym", keep="last").sort_values("ym")
    g["year"] = g["ym"].str[:4].astype(int)
    g["month"] = g["ym"].str[5:7].astype(int)
    # 用 (year, month) 對齊去年同月，而不是 shift(12)：缺月時 shift 會對錯
    prev = g.set_index(["year", "month"])["revenue"]
    g["yoy"] = [
        (r / prev.get((y - 1, m)) * 100 - 100) if prev.get((y - 1, m)) else None
        for r, y, m in zip(g["revenue"], g["year"], g["month"])
    ]
    g["mom"] = g["revenue"].pct_change() * 100
    g["cum"] = g.groupby("year")["revenue"].cumsum()
    cum_prev = g.set_index(["year", "month"])["cum"]
    g["cum_yoy"] = [
        (c / cum_prev.get((y - 1, m)) * 100 - 100) if cum_prev.get((y - 1, m)) else None
        for c, y, m in zip(g["cum"], g["year"], g["month"])
    ]
    tail = g.tail(months)
    monthly = [[r.ym, _r(r.revenue, 0), _r(r.yoy, 1), _r(r.mom, 1), _r(r.cum, 0), _r(r.cum_yoy, 1)]
               for r in tail.itertuples()]
    yearly = []
    for y, gg in g.groupby("year"):
        yearly.append({"year": int(y), "months": int(len(gg)),
                       "revenue": _r(gg["revenue"].sum(), 0),
                       "by_month": {int(m): _r(v, 0) for m, v in zip(gg["month"], gg["revenue"])}})
    return {"monthly": monthly, "yearly": yearly[-7:],
            "columns": ["ym", "revenue", "yoy", "mom", "cum", "cum_yoy"]}


# ------------------------------------------------------------------ 獲利

def profit_series(fin: pd.DataFrame, code: str, quarters: int = 24) -> dict:
    """季損益：營收、毛利率、營益率、淨利率、EPS、年度累計 EPS、EPS YoY。"""
    if fin is None or fin.empty:
        return {"quarters": []}
    g = fin[fin["code"] == code].copy()
    if g.empty:
        return {"quarters": []}
    for c in ("year", "quarter"):
        g[c] = pd.to_numeric(g[c], errors="coerce")
    g = g.dropna(subset=["year", "quarter"])
    g["year"] = g["year"].astype(int); g["quarter"] = g["quarter"].astype(int)
    g = g.sort_values(["year", "quarter"]).drop_duplicates(["year", "quarter"], keep="last")
    for c in ("revenue", "gross_profit", "operating_income", "net_income", "eps"):
        g[c] = pd.to_numeric(g.get(c), errors="coerce")
    rv = g["revenue"].replace(0, np.nan)
    g["gm"] = g["gross_profit"] / rv * 100
    g["om"] = g["operating_income"] / rv * 100
    g["nm"] = g["net_income"] / rv * 100
    g["eps_cum"] = g.groupby("year")["eps"].cumsum()
    prev = g.set_index(["year", "quarter"])["eps"]
    g["eps_yoy"] = [
        (e - prev.get((y - 1, q))) if (prev.get((y - 1, q)) is not None and pd.notna(prev.get((y - 1, q)))) else None
        for e, y, q in zip(g["eps"], g["year"], g["quarter"])
    ]
    tail = g.tail(quarters)
    rows = [[f"{r.year}Q{r.quarter}", _r(r.revenue, 0), _r(r.gm, 1), _r(r.om, 1), _r(r.nm, 1),
             _r(r.eps, 2), _r(r.eps_cum, 2), _r(r.eps_yoy, 2), _r(r.net_income, 0)]
            for r in tail.itertuples()]
    return {"quarters": rows,
            "columns": ["period", "revenue", "gross_margin", "op_margin", "net_margin",
                        "eps", "eps_cum", "eps_yoy_diff", "net_income"]}


# ------------------------------------------------------------------ 本益比歷史

def pe_history(price: pd.DataFrame, fin: pd.DataFrame, code: str, years: int = 5) -> list:
    """每季一個點：季報可用日之後的第一個收盤 / 當時近四季 EPS。

    也順便給該季區間的最高與最低本益比（用區間內每日收盤 / 同一個 TTM EPS），
    前端畫本益比河流圖用。虧損（TTM ≤ 0）的季度給 None。
    """
    if fin is None or fin.empty or price is None or price.empty:
        return []
    g = fin[fin["code"] == code].copy()
    if g.empty:
        return []
    for c in ("year", "quarter"):
        g[c] = pd.to_numeric(g[c], errors="coerce")
    g = g.dropna(subset=["year", "quarter"])
    g["year"] = g["year"].astype(int); g["quarter"] = g["quarter"].astype(int)
    g["qidx"] = g["year"] * 4 + g["quarter"]
    g = g.sort_values("qidx").drop_duplicates("qidx", keep="last")
    g["eps"] = pd.to_numeric(g["eps"], errors="coerce")
    px = price[price["code"] == code][["date", "close"]].copy()
    px["date"] = px["date"].astype(str)
    px = px.sort_values("date")
    if px.empty:
        return []
    rows = []
    hist = g.tail(years * 4 + 4).reset_index(drop=True)
    for i in range(len(hist)):
        win = hist.iloc[max(0, i - 3): i + 1]
        if len(win) < 4 or (win["qidx"].max() - win["qidx"].min()) != 3 or win["eps"].isna().any():
            continue
        ttm = float(win["eps"].sum())
        r = hist.iloc[i]
        start = str(r.get("announce_date") or "")
        nxt = hist.iloc[i + 1] if i + 1 < len(hist) else None
        end = str(nxt.get("announce_date")) if nxt is not None else "9999-12-31"
        seg = px[(px["date"] >= start) & (px["date"] < end)]
        if seg.empty:
            continue
        if ttm <= 0:
            rows.append({"period": f"{r.year}Q{r.quarter}", "ttm_eps": round(ttm, 2),
                         "pe": None, "pe_high": None, "pe_low": None, "from": seg["date"].iloc[0]})
            continue
        closes = pd.to_numeric(seg["close"], errors="coerce").dropna()
        rows.append({"period": f"{r.year}Q{r.quarter}", "ttm_eps": round(ttm, 2),
                     "pe": _r(closes.iloc[0] / ttm, 1),
                     "pe_high": _r(closes.max() / ttm, 1), "pe_low": _r(closes.min() / ttm, 1),
                     "from": seg["date"].iloc[0]})
    return rows[-years * 4:]


# ------------------------------------------------------------------ 除權息

def dividends(events: pd.DataFrame, results: pd.DataFrame, price: pd.DataFrame,
              code: str, close: float | None) -> dict:
    """股利公告 + 除權息結果（含填息天數）+ 近四次現金股利合計的殖利率。"""
    out = {"events": [], "results": [], "cash_ttm": None, "yield_ttm": None}
    if events is not None and not events.empty:
        e = events[events["code"] == code].copy()
        if not e.empty:
            e = e.sort_values(["fiscal_year", "period"], ascending=[False, False]) \
                if "fiscal_year" in e.columns else e
            out["events"] = [{
                "period": r.get("period"), "kind": r.get("kind"), "amount": _r(r.get("amount"), 4),
                "announce_date": r.get("announce_date"), "ex_date": r.get("ex_date"),
                "payment_date": r.get("payment_date"),
                "fiscal_year": int(r["fiscal_year"]) if pd.notna(r.get("fiscal_year")) else None,
            } for _, r in e.head(24).iterrows()]
            cash = e[e["kind"] == "cash"].copy()
            cash["ex_date"] = cash["ex_date"].astype(str)
            cash = cash[cash["ex_date"].str.match(r"^\d{4}-\d{2}-\d{2}$", na=False)].sort_values("ex_date")
            if not cash.empty:
                cutoff = (pd.Timestamp(cash["ex_date"].iloc[-1]) - pd.Timedelta(days=365)).date().isoformat()
                ttm_cash = float(pd.to_numeric(cash[cash["ex_date"] > cutoff]["amount"], errors="coerce").sum())
                out["cash_ttm"] = round(ttm_cash, 4)
                if close:
                    out["yield_ttm"] = round(ttm_cash / close * 100, 2)
    if results is not None and not results.empty:
        rs = results[results["code"] == code].copy()
        if not rs.empty:
            px = price[price["code"] == code][["date", "close"]].copy() if price is not None else pd.DataFrame()
            if not px.empty:
                px["date"] = px["date"].astype(str)
                px = px.sort_values("date")
            rows = []
            for _, r in rs.sort_values("date", ascending=False).head(12).iterrows():
                d = str(r.get("date"))
                before = _f(r.get("before_price"))
                fill_days = None
                if not px.empty and before:
                    after = px[px["date"] >= d]
                    closes = pd.to_numeric(after["close"], errors="coerce")
                    hit = np.where(closes.values >= before)[0]
                    if len(hit):
                        fill_days = int(hit[0]) + 1
                    elif len(after) >= 250:
                        fill_days = -1        # 一年內沒填
                rows.append({"date": d, "kind": r.get("kind"), "dividend": _r(r.get("dividend"), 4),
                             "before_price": before, "reference_price": _f(r.get("reference_price")),
                             "fill_days": fill_days})
            out["results"] = rows
    return out


# ------------------------------------------------------------------ 資券

def margin_series(margin: pd.DataFrame, code: str, days: int = 250) -> list:
    if margin is None or margin.empty:
        return []
    g = margin[margin["code"] == code].copy()
    if g.empty:
        return []
    g = g.drop_duplicates("date", keep="last").sort_values("date").tail(days)
    return [[str(r.date), _r(r.margin_balance, 0), _r(r.short_balance, 0),
             _r(getattr(r, "margin_change", None), 0), _r(getattr(r, "short_change", None), 0)]
            for r in g.itertuples()]


# ------------------------------------------------------------------ 大戶散戶

def holder_series(sh: pd.DataFrame, code: str, weeks: int = 104) -> list:
    """[date, 千張大戶%, 400-1000張%, 10張以下散戶%, 總股東人數]"""
    if sh is None or sh.empty:
        return []
    g = sh[sh["code"] == code]
    if g.empty:
        return []
    rows = []
    for d, gg in g.groupby("date"):
        lv = gg.set_index("level")
        pct = pd.to_numeric(lv["pct"], errors="coerce")
        big = pct.get(BIG_LEVEL)
        mid = pct.reindex(list(MID_LEVELS)).sum(min_count=1)
        retail = pct.reindex(list(RETAIL_LEVELS)).sum(min_count=1)
        total = lv["holders"].get(TOTAL_LEVEL) if "holders" in lv else None
        rows.append([str(d), _r(big, 2), _r(mid, 2), _r(retail, 2),
                     int(total) if total is not None and pd.notna(total) else None])
    rows.sort(key=lambda x: x[0])
    return rows[-weeks:]


# ------------------------------------------------------------------ 法人

def inst_series(inst: pd.DataFrame, code: str, days: int = 120) -> dict:
    if inst is None or inst.empty:
        return {"daily": [], "sum20": None, "sum60": None}
    g = inst[inst["code"] == code].drop_duplicates("date", keep="last").sort_values("date")
    if g.empty:
        return {"daily": [], "sum20": None, "sum60": None}
    for c in ("foreign_total", "trust", "dealer"):
        g[c] = pd.to_numeric(g[c], errors="coerce")
    tail = g.tail(days).copy()
    tail["cum"] = (tail["foreign_total"].fillna(0) + tail["trust"].fillna(0) + tail["dealer"].fillna(0)).cumsum()
    daily = [[str(r.date), _r(r.foreign_total, 0), _r(r.trust, 0), _r(r.dealer, 0), _r(r.cum, 0)]
             for r in tail.itertuples()]
    tot = g["foreign_total"].fillna(0) + g["trust"].fillna(0) + g["dealer"].fillna(0)
    return {"daily": daily, "sum20": _r(tot.tail(20).sum(), 0), "sum60": _r(tot.tail(60).sum(), 0),
            "foreign20": _r(g["foreign_total"].tail(20).sum(), 0),
            "trust20": _r(g["trust"].tail(20).sum(), 0)}


# ------------------------------------------------------------------ 基本資料

def basics(company: pd.DataFrame, code: str) -> dict:
    if company is None or company.empty:
        return {}
    g = company[company["code"] == code]
    if g.empty:
        return {}
    r = g.iloc[-1]
    cap = _f(r.get("capital"))
    return {
        "name": r.get("name"), "full_name": r.get("full_name"), "market": r.get("market"),
        "industry": r.get("industry"), "industry_finmind": r.get("industry_finmind"),
        "listed_date": r.get("listed_date"),
        "capital": cap, "capital_billion": round(cap / 1e8, 2) if cap else None,
        "chairman": r.get("chairman"), "website": r.get("website"),
    }
