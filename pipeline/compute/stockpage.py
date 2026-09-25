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
DIV_YEAR_DAYS = 320            # 殖利率：最後一次除息往回幾天內算「同一個配息年度」


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

def pe_daily(price: pd.DataFrame, fin: pd.DataFrame, code: str,
             shares: dict | None = None, quarters: int | None = None) -> pd.DataFrame:
    """逐日本益比：[date, close, ttm_eps, pe, period, from]。price 必須是**原始**（未還原）收盤。

    公式：PE_d ＝ 原始收盤_d ÷ TTM_d，
          TTM_d ＝ Σ(近四季 eps_q ÷ eps_divisor(..., d))  —— 每季 EPS 換算到 d 當天的股本。
    所以除權當天收盤掉到 1/2.98、TTM 也同步除以 2.98，本益比連續（R5：6669 從 20 掉到 6.7 就是少了這步）。
    - 只用公布日（缺值用法定期限）之後的價格，不偷看未來季報。
    - 四季不連續或任一季缺 EPS → 那一段不給；TTM ≤ 0 → pe 為 NaN（不給負數）。
    - quarters：只算最後幾季（個股頁只要 5 年，全算會多花好幾倍時間）。
    效能：TTM 只會在「新季報」或「股數事件」那天變，所以區段再依事件日切開、每一小段向量化，
    不逐日呼叫查表（逐日版本全市場要多 10 分鐘以上）。
    """
    from .fundamental import eps_divisor, eps_basis_info
    cols = ["date", "close", "ttm_eps", "pe", "period", "from"]
    if fin is None or fin.empty or price is None or price.empty:
        return pd.DataFrame(columns=cols)
    g = fin[fin["code"] == code].copy()
    if g.empty:
        return pd.DataFrame(columns=cols)
    for c in ("year", "quarter"):
        g[c] = pd.to_numeric(g[c], errors="coerce")
    g = g.dropna(subset=["year", "quarter"])
    g["year"] = g["year"].astype(int); g["quarter"] = g["quarter"].astype(int)
    g["qidx"] = g["year"] * 4 + g["quarter"]
    g = g.sort_values("qidx").drop_duplicates("qidx", keep="last").reset_index(drop=True)
    g["eps"] = pd.to_numeric(g["eps"], errors="coerce")
    info = eps_basis_info(g)                    # 在完整序列上算（隱含股數要上一季）
    pend = [x[0] for x in info]; avail = [x[1] for x in info]; impl = [x[2] for x in info]
    px = price[price["code"] == code][["date", "close"]]
    dates = px["date"].astype(str).to_numpy()
    closes = pd.to_numeric(px["close"], errors="coerce").to_numpy(dtype=float)
    ok = np.isfinite(closes) & (closes > 0)
    dates, closes = dates[ok], closes[ok]
    order = np.argsort(dates, kind="stable")
    dates, closes = dates[order], closes[order]
    if len(dates) == 0:
        return pd.DataFrame(columns=cols)
    ent = (shares or {}).get(str(code))
    ev_dates = ent[0] if ent is not None else []
    qidx = g["qidx"].to_numpy(); eps = g["eps"].to_numpy(dtype=float)
    first_i = 3 if quarters is None else max(3, len(g) - int(quarters))
    parts = []
    for i in range(first_i, len(g)):
        if qidx[i] - qidx[i - 3] != 3 or np.isnan(eps[i - 3: i + 1]).any():
            continue
        start = avail[i]
        end = avail[i + 1] if i + 1 < len(g) else "9999-12-31"
        lo, hi = np.searchsorted(dates, start, "left"), np.searchsorted(dates, end, "left")
        if hi <= lo:
            continue
        sd, sc = dates[lo:hi], closes[lo:hi]
        # 區段內的股數事件日把這段再切開；每一小段 TTM 是常數
        cuts = [0] + [int(np.searchsorted(sd, e, "left")) for e in ev_dates if sd[0] < e <= sd[-1]] + [len(sd)]
        t = np.empty(len(sd))
        for a_, b_ in zip(cuts[:-1], cuts[1:]):
            if b_ <= a_:
                continue
            d0 = sd[a_]
            t[a_:b_] = sum(eps[k] / (eps_divisor(shares, code, pend[k], avail[k], d0, impl[k]) if ent is not None else 1.0)
                           for k in range(i - 3, i + 1))
        with np.errstate(divide="ignore", invalid="ignore"):
            pe = np.where(t > 0, sc / t, np.nan)
        parts.append(pd.DataFrame({"date": sd, "close": sc, "ttm_eps": t, "pe": pe,
                                   "period": f"{g.at[i, 'year']}Q{g.at[i, 'quarter']}", "from": sd[0]}))
    if not parts:
        return pd.DataFrame(columns=cols)
    return pd.concat(parts, ignore_index=True)[cols]


def pe_history(price: pd.DataFrame, fin: pd.DataFrame, code: str, years: int = 5,
               shares: dict | None = None, adj_price: pd.DataFrame | None = None) -> list:
    """每季一個點：季報可用日之後的第一個收盤 / 當時近四季 EPS，外加該季區間的最高與最低本益比。

    price 是**原始**收盤（本益比用的是當天真的價格 ÷ 當天股本下的 EPS，見 pe_daily）。
    ttm_eps 欄位要給前端「本益比河流圖」拿去跟**還原 K 線**相除，所以換算到還原價的基準：
      ttm_eps_輸出 ＝ 區段最後一天的 收盤_還原 ÷ PE
    這樣河流圖的 收盤_還原 ÷ ttm_eps 在區段最後一天會精確等於真的本益比；
    區段內若有除息，前面幾天的偏差不超過那次的現金殖利率（除權的股數部分則完全抵銷）。
    沒給 adj_price 時 ttm_eps 就是當天股本下的 TTM（舊行為）。虧損（TTM ≤ 0）的季度給 None。
    """
    d = pe_daily(price, fin, code, shares, quarters=years * 4 + 1)
    if d.empty:
        return []
    adj_map = None
    if adj_price is not None and not adj_price.empty:
        a = adj_price[adj_price["code"] == code]
        adj_map = pd.Series(pd.to_numeric(a["close"], errors="coerce").to_numpy(),
                            index=a["date"].astype(str).to_numpy())
        adj_map = adj_map[~adj_map.index.duplicated(keep="last")]
    rows = []
    per = d["period"].to_numpy()
    brk = np.flatnonzero(per[1:] != per[:-1]) + 1
    for a_, b_ in zip(np.r_[0, brk], np.r_[brk, len(d)]):
        seg = d.iloc[a_:b_]
        last = seg.iloc[-1]
        ttm_raw = float(last["ttm_eps"])
        if ttm_raw <= 0:
            rows.append({"period": last["period"], "ttm_eps": round(ttm_raw, 2),
                         "pe": None, "pe_high": None, "pe_low": None, "from": seg["from"].iloc[0]})
            continue
        ttm_out = ttm_raw
        if adj_map is not None:
            ac = adj_map.get(last["date"])
            if ac is not None and pd.notna(ac) and ac > 0 and pd.notna(last["pe"]) and last["pe"] > 0:
                ttm_out = float(ac) / float(last["pe"])
        pes = seg["pe"].dropna()
        rows.append({"period": last["period"], "ttm_eps": round(ttm_out, 2),
                     "pe": _r(seg["pe"].iloc[0], 1),
                     "pe_high": _r(pes.max(), 1) if len(pes) else None,
                     "pe_low": _r(pes.min(), 1) if len(pes) else None,
                     "from": seg["from"].iloc[0]})
    return rows[-years * 4:]


# ------------------------------------------------------------------ 除權息

def dividends(events: pd.DataFrame, results: pd.DataFrame, price: pd.DataFrame,
              code: str, close: float | None, shares: dict | None = None,
              asof: str | None = None) -> dict:
    """股利公告 + 除權息結果（含填息天數）+ 近一年現金股利合計的殖利率。

    price 必須是**原始**收盤（填息是拿除權息前的真實收盤比）。
    - 殖利率 ＝ 最近一個配息年度的現金股利（換算到今天的股數）÷ 收盤；
      配息年度＝最後一次除息往回 DIV_YEAR_DAYS（320）天內的各次除息。
      每筆現金 ÷ share_growth([除息日, asof])：6669 6/22 配 144.39 元，9/2 每股變 2.98 股，
      換算後每股 48.4 元 → 殖利率約 3.4%（R5 回報沒換算時是 10.33%）。
    - 除權息紀錄的「股利」只放股利：現金＋股票股利（元），取自 dividend_events 同一除權息日；
      以前放的是 dividend_results 的「前收盤 − 參考價」價差（6669 寫成 5,185）。
      對不到公告時：純除息用價差（除息價差就是現金股利），含權的留空（不猜）。
    """
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
            if asof:
                cash = cash[cash["ex_date"] <= str(asof)]      # 還沒除息的不算進「近一年已配」
            if not cash.empty:
                # 「最近一個配息年度」＝最後一次除息往回 320 天內（不是 365 天）：
                # 年配息股每年除息日會前後漂移幾天，用 365 天會把去年那一筆也算進來
                # （6669：2025-06-24 與 2026-06-22 只差 363 天，殖利率被多算一整年）。
                # 季配息四次橫跨約 9 個月（≈275 天）、半年配兩次約 6 個月，都在 320 天內。
                cutoff = (pd.Timestamp(cash["ex_date"].iloc[-1]) - pd.Timedelta(days=DIV_YEAR_DAYS)).date().isoformat()
                recent = cash[cash["ex_date"] > cutoff]
                amt = pd.to_numeric(recent["amount"], errors="coerce")
                if shares:
                    from .fundamental import share_growth
                    amt = amt / np.asarray([share_growth(shares, code, d, asof, include_after=True)
                                            for d in recent["ex_date"]], dtype=float)
                ttm_cash = float(amt.sum())
                out["cash_ttm"] = round(ttm_cash, 4)
                if close:
                    out["yield_ttm"] = round(ttm_cash / close * 100, 2)
    if results is not None and not results.empty:
        rs = results[results["code"] == code].copy()
        paid: dict[str, dict[str, float]] = {}
        if events is not None and not events.empty and "ex_date" in events.columns:
            ee = events[events["code"] == code]
            for k, d, amt in zip(ee["kind"], ee["ex_date"].astype(str), pd.to_numeric(ee["amount"], errors="coerce")):
                if pd.notna(amt):
                    paid.setdefault(d, {}).setdefault(k, 0.0)
                    paid[d][k] += float(amt)
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
                pd_ = paid.get(d)
                if pd_:
                    cash_d, stock_d = pd_.get("cash"), pd_.get("stock")
                    div = (cash_d or 0.0) + (stock_d or 0.0)
                elif "權" not in str(r.get("kind") or ""):
                    cash_d, stock_d, div = _f(r.get("dividend")), None, _f(r.get("dividend"))
                else:
                    cash_d = stock_d = div = None
                gap = (before - _f(r.get("reference_price"))) if before and _f(r.get("reference_price")) else None
                rows.append({"date": d, "kind": r.get("kind"), "dividend": _r(div, 4),
                             "cash_dividend": _r(cash_d, 4), "stock_dividend": _r(stock_d, 4),
                             "price_gap": _r(gap, 2),
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
        lv = gg.drop_duplicates("level", keep="last").set_index("level")
        pct = pd.to_numeric(lv["pct"], errors="coerce")
        # ★ 2026-09-26（Andy：「大戶／散戶持股資訊為何這麼少」）：集保原檔的 pct 只到小數兩位，
        #   400–1000 張三級加起來常常連續幾週都是同一個數（2330：09-04 與 09-11 都是 2.75%），
        #   前端怎麼放大 Y 軸都只看到一條水平線。原檔同時給了每級的**股數**與合計股數，
        #   用股數自己除回來可以多拿一位有效數字（2.766% → 2.764%，真的有在變）。
        #   沒有股數（舊資料、測試資料）才退回原檔的 pct，口徑不變、只是精度變高。
        sh = pd.to_numeric(lv["shares"], errors="coerce") if "shares" in lv else None
        tot_sh = sh.get(TOTAL_LEVEL) if sh is not None else None
        if tot_sh is not None and pd.notna(tot_sh) and tot_sh > 0:
            pct = pct.where(sh.isna(), sh / tot_sh * 100)
        nd = 3
        big = pct.get(BIG_LEVEL)
        mid = pct.reindex(list(MID_LEVELS)).sum(min_count=1)
        retail = pct.reindex(list(RETAIL_LEVELS)).sum(min_count=1)
        total = lv["holders"].get(TOTAL_LEVEL) if "holders" in lv else None
        rows.append([str(d), _r(big, nd), _r(mid, nd), _r(retail, nd),
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

def monthly_seasonality(price: pd.DataFrame, code: str, years: int = 15) -> dict:
    """個股的 1–12 月平均漲幅（C5，Andy 2026-09-18 拍板要做）。

    原話：「統計過往 15 年 1-12 月的平均漲幅，並且可以切時間週期 1、3、5 年（可自行填寫）」。
    沒有 15 年的就**從它有資料的那一年開始算**，並且把實際年數講出來 ——
    上市三年的公司硬湊 15 年只會變成假數字。

    回傳每一年每一個月的報酬（`by_year`），前端就能自己切 1／3／5／自填年數，
    不用為了換一個年數回頭問後端。月報酬＝該月最後一個交易日收盤 / 前一月最後一個交易日收盤 − 1。

    ★ 只用**已經收完的月份**：當月還沒走完，把它算進「平均漲幅」會讓最近一個月
      永遠是半個月的數字，平均被拉歪。
    """
    empty = {"years": 0, "from": None, "to": None, "by_year": {}, "months": []}
    if price is None or price.empty or "code" not in price.columns:
        return empty
    g = price[price["code"].astype(str) == str(code)]
    if g.empty or "date" not in g.columns or "close" not in g.columns:
        return empty
    g = g.dropna(subset=["close"]).copy()
    g["date"] = g["date"].astype(str)
    g = g.sort_values("date")
    g["ym"] = g["date"].str.slice(0, 7)
    # 每個月的最後一個交易日收盤
    last = g.groupby("ym")["close"].last().astype(float)
    if len(last) < 2:
        return empty
    # 當月還沒收完就丟掉（見上面的理由）
    newest_day = g["date"].iloc[-1]
    if newest_day[:7] == last.index[-1]:
        import datetime as _d
        y, m = int(newest_day[:4]), int(newest_day[5:7])
        nxt = _d.date(y + (m == 12), 1 if m == 12 else m + 1, 1)
        if (nxt - _d.date(y, m, int(newest_day[8:10]))).days > 1:
            last = last.iloc[:-1]
    if len(last) < 2:
        return empty
    ret = (last / last.shift(1) - 1) * 100
    ret = ret.iloc[1:]
    by_year: dict[str, dict[str, float]] = {}
    for ym, v in ret.items():
        if pd.isna(v):
            continue
        by_year.setdefault(ym[:4], {})[str(int(ym[5:7]))] = round(float(v), 2)
    ys = sorted(by_year)[-int(years):]
    by_year = {y: by_year[y] for y in ys}
    return {"years": len(ys), "from": ys[0] if ys else None, "to": ys[-1] if ys else None,
            "by_year": by_year, "months": list(range(1, 13))}


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


# ------------------------------------------------------------------ 歷史無限回溯（③）

HIST_CHUNK = 1000        # 一段幾根日 K


def history_chunks(bars: list, chunk: int = HIST_CHUNK) -> list[dict]:
    """把「個股頁那一段之前」的更舊日 K 切成一段一段，最新的那一段排 p0。

    為什麼要切段：個股頁本來就給 1,250～1,500 根（5～6 年），再往前資料湖最多還有
    5,100 根（2000-01-04 起）。一次全部塞給瀏覽器＝一檔多下載 200KB 而且九成用不到；
    切成一段一段，使用者往左拖一次才要一段（約 40KB）。

    為什麼每一段自己帶 `prev` 而不是另外做一份目錄檔：
    前端要的判斷只有一個 ——「還有沒有更舊的」。`prev` 是 None 就代表這是資料湖裡
    最早的一段，前端看到就收手，不會繼續往下打請求（也就不會出現「拖到底還一直轉」）。
    多一份目錄檔等於多一次來回，而且多一個會對不起來的地方。

    bars 由舊到新，形狀是 [日期, 開, 高, 低, 收, 量]。
    """
    if not bars:
        return []
    segs: list[list] = []
    i = len(bars)
    while i > 0:
        j = max(0, i - chunk)
        segs.append(bars[j:i])
        i = j
    out = []
    for n, seg in enumerate(segs):
        out.append({
            "page": n,
            "prev": None if n == len(segs) - 1 else f"p{n + 1}",
            "from": str(seg[0][0]),
            "to": str(seg[-1][0]),
            "bars": seg,
        })
    return out
