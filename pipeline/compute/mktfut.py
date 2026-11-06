"""市場明細三張卡的 payload（site/data/market_fut.json，2026-10-20）：融資餘額／外資台指期口數／小台散戶多空比。

只讀資料湖（margin_total、margin_daily、price_daily、company_info、fut_inst、fut_oi），不抓網路。
口徑（前端「?」照抄）
  · 融資餘額（億元）：FinMind 整體市場融資融券的 MarginPurchaseMoney（仟元）÷10 萬；融券餘額／融資張數同一個資料集（上市）。
  · 大盤融資維持率（估算，2026-10-20 Andy 範本）＝ Σ(上市個股融資餘額張數×1000×當日收盤價) ÷ 融資總餘額(元) × 100。
    非證交所法定整戶擔保維持率（那要每戶的借款與擔保品）；只是整體市場的現值／借款比。
  · 台指期（TX）三大法人：多方／空方／淨 ＝ 未平倉口數（所有月份合計），淨＝多−空。
  · 散戶多空比（大台 TX／小台 MTX／微台 TMF，三商品各算各的）＝ (全市場未平倉−法人多方 − (全市場未平倉−法人空方)) ÷ 全市場未平倉 × 100%，
    全市場未平倉＝一般交易時段各單一到期月份 open_interest 加總（排除價差單）。
"""
from __future__ import annotations

import pandas as pd

DAYS = 120
MARGIN_DAYS = 1300      # 信用交易頁週期鈕最長到 5 年／全部
WHO = ("foreign", "trust", "dealer")


def _f(v):
    return None if v is None or pd.isna(v) else float(v)


def _caps(m: pd.DataFrame, px: pd.DataFrame) -> tuple[dict, set]:
    """Σ(個股融資餘額張數×1000×當日收盤價)，一天一個值（元）；回 ({date: 市值}, 部分估算日集合)。

    m：date／code／margin_balance（張），已篩成同一個市場；px：date／code／close。
    當天個股融資只到一部分（FinMind 逐檔回補還沒跟上）時，缺的檔用「前一次有資料的餘額」順延再乘當日收盤價：
    融資餘額一天的變動遠小於持股數，實測 2026-10-16 隨機拿掉一半檔數用順延補，誤差 0.35pp（183.73 vs 183.38）；
    檔數不到中位數一半的日子仍不收（回傳裡沒有那天），免得畫出假的暴跌；不到中位數 95% 的日子標「部分估算」。
    沒有收盤價的檔（停牌）那天不計入分子 —— 跟上市版本同一口徑。"""
    if m is None or m.empty:
        return {}, set()
    bal = m.pivot_table(index="date", columns="code", values="margin_balance", aggfunc="last").sort_index()
    n_have = bal.notna().sum(axis=1)
    full = n_have.median() if len(bal) else 0
    bal = bal.ffill()
    pxp = px.pivot_table(index="date", columns="code", values="close", aggfunc="last").reindex(index=bal.index, columns=bal.columns)
    capser = (bal * 1000 * pxp).sum(axis=1, min_count=1)
    keep = n_have >= 0.5 * full
    return capser[keep].dropna().to_dict(), set(n_have[keep & (n_have < 0.95 * full)].index)


def _idx_map(idx: pd.DataFrame | None, symbol: str) -> dict:
    """index_ohlc 某一個指數（TSE 加權／OTC 櫃買）的 {date: 收盤}。"""
    if idx is None or idx.empty or "symbol" not in idx.columns:
        return {}
    t = idx[idx["symbol"] == symbol]
    return dict(zip(t["date"].astype(str), pd.to_numeric(t["close"], errors="coerce")))


def _rows(mt: pd.DataFrame, caps: dict, partial_days: set, tx: dict) -> list[dict]:
    """整體融資表（margin_total／margin_total_otc，同一組欄位）＋分子市值 → 前端一天一列。

    ratio ＝ 市值 ÷ 融資金額(元) × 100；分子或分母任一缺、或分母為 0 → None（不補、不外推）。
    margin_money 實際單位是「元」（資料湖 2026-10-19 上市 = 640,618,432,000 ＝ 6,406 億）；
    舊版當成仟元（÷1e5、×1000）→ 融資金額差 1000 倍、維持率貼在 0%。"""
    rows = []
    for r in mt.tail(MARGIN_DAYS + 1).itertuples():
        money = getattr(r, "margin_money", None)
        money = None if money is None or pd.isna(money) else float(money)
        cap = caps.get(r.date)
        ratio = (cap / money * 100) if cap is not None and money else None
        lp, sp = getattr(r, "margin_lots_prev", None), getattr(r, "short_lots_prev", None)
        ml, sl = getattr(r, "margin_lots", None), getattr(r, "short_lots", None)
        rows.append({"d": r.date, "ratio": _f(ratio), "margin_lots": _f(ml),
                     "margin_chg": _f(ml - lp) if ml is not None and lp is not None and not pd.isna(ml) and not pd.isna(lp) else None,
                     "margin_yi": _f(money / 1e8) if money is not None else None, "cap_yi": _f(cap / 1e8) if cap is not None else None,
                     "short_lots": _f(sl), "partial": r.date in partial_days,
                     "short_chg": _f(sl - sp) if sl is not None and sp is not None and not pd.isna(sl) and not pd.isna(sp) else None,
                     "taiex": _f(tx.get(r.date))})
    return rows[-MARGIN_DAYS:]


def otc_rows(mt_otc: pd.DataFrame | None, md: pd.DataFrame | None, company: pd.DataFrame | None,
             price: pd.DataFrame | None, idx: pd.DataFrame | None = None) -> list[dict]:
    """上櫃融資維持率（估算），口徑跟上市完全相同，只是換成上櫃：
    Σ(上櫃個股融資餘額張數×1000×當日收盤價) ÷ 上櫃整體融資金額(元，櫃買 OpenAPI 信用交易彙總) × 100。
    分子的個股融資來自 margin_daily（market＝TPEX，FinMind 逐檔續補），缺檔順延與「不到中位數一半不收」同 _caps。
    指數欄（taiex）放櫃買指數（index_ohlc symbol＝OTC），讓上櫃的維持率對照上櫃大盤。
    分母只有從 margin_total_otc 開始累積的日子才有，所以列數＝那張表的天數（沒有回補歷史）。"""
    if mt_otc is None or mt_otc.empty:
        return []
    mt_otc = mt_otc.sort_values("date").drop_duplicates("date", keep="last")
    first = mt_otc["date"].tail(MARGIN_DAYS + 1).iloc[0]
    caps, partial = {}, set()
    if md is not None and not md.empty and company is not None and not company.empty and price is not None and not price.empty:
        codes = set(company[company["market"] == "TPEX"]["code"].astype(str))
        # 往前多留 30 天，讓第一天的缺檔也能順延（分母第一天之前的個股餘額只當順延來源，不輸出）
        lo = (pd.Timestamp(first) - pd.Timedelta(days=30)).strftime("%Y-%m-%d")
        m = md[(md["date"].astype(str) >= lo) & md["code"].astype(str).isin(codes)][["date", "code", "margin_balance"]]
        px = price[(price["date"].astype(str) >= lo) & price["code"].astype(str).isin(codes)][["date", "code", "close"]]
        caps, partial = _caps(m, px)
    return _rows(mt_otc, caps, partial, _idx_map(idx, "OTC"))


def combine_rows(tw: list[dict], otc: list[dict], idx: pd.DataFrame | None = None) -> list[dict]:
    """上市＋上櫃合計：只收兩邊都有融資金額的日子（只有一邊的日子不收，免得合計值跳一階）。

    ratio ＝ (上市市值＋上櫃市值) ÷ (上市融資金額＋上櫃融資金額) × 100 —— 是加總後再除，**不是**兩個比率平均；
    兩邊市值任一缺 → ratio None（不拿一邊的比率代表合計）。指數放加權指數。"""
    o = {r["d"]: r for r in otc if r.get("margin_yi") is not None}
    tx = _idx_map(idx, "TSE")

    def add(a, b):
        return None if a is None or b is None else a + b
    rows = []
    for a in tw:
        b = o.get(a["d"])
        if b is None or a.get("margin_yi") is None:
            continue
        cap, yi = add(a.get("cap_yi"), b.get("cap_yi")), a["margin_yi"] + b["margin_yi"]
        rows.append({"d": a["d"], "ratio": _f(cap / yi * 100) if cap is not None and yi else None,
                     "margin_lots": add(a.get("margin_lots"), b.get("margin_lots")), "margin_chg": add(a.get("margin_chg"), b.get("margin_chg")),
                     "margin_yi": yi, "cap_yi": cap, "short_lots": add(a.get("short_lots"), b.get("short_lots")),
                     "short_chg": add(a.get("short_chg"), b.get("short_chg")),
                     "partial": bool(a.get("partial") or b.get("partial")), "taiex": _f(tx.get(a["d"])) if tx else a.get("taiex")})
    return rows


def margin_block(mt: pd.DataFrame, md: pd.DataFrame, company: pd.DataFrame, price: pd.DataFrame,
                 idx: pd.DataFrame | None = None, members: pd.DataFrame | None = None) -> dict:
    """上市大盤融資維持率（估算）＋融資／融券餘額＋加權指數＋個股融資增減排行＋個股融券增減排行（short_rank，同一天）。

    維持率 ＝ Σ(各上市股融資餘額張數×1000×當日收盤價) ÷ 融資總餘額(元，整體市場 MarginPurchaseMoney，單位元) × 100。
    分子是「融資買進股票的現值」、分母是「借款餘額」，所以是整體市場的估算，**不是**證交所法定的整戶擔保維持率。
    """
    out = {"rows": [], "asof": None, "rank": None, "short_rank": None}
    if mt is None or mt.empty:
        return out
    mt = mt.sort_values("date").drop_duplicates("date", keep="last")
    first = mt["date"].tail(MARGIN_DAYS + 1).iloc[0]
    caps, rank, srank, partial_days = {}, None, None, set()
    if md is not None and not md.empty and company is not None and not company.empty and price is not None and not price.empty:
        tw = company[company["market"] == "TWSE"].drop_duplicates("code", keep="last")
        codes = set(tw["code"].astype(str))
        scol = [c for c in ("short_balance", "short_change") if c in md.columns]
        m = md[(md["date"].astype(str) >= first) & md["code"].astype(str).isin(codes)][["date", "code", "margin_balance", "margin_change"] + scol].copy()
        px = price[price["date"].astype(str) >= first][["date", "code", "close"]]
        m = m.merge(px, on=["date", "code"], how="left")
        caps, partial_days = _caps(m[["date", "code", "margin_balance"]], px)
        m["cap"] = m["margin_balance"] * 1000 * m["close"]
        if caps:
            d = max(caps)
            names = tw.set_index("code")["name"].to_dict()
            x = m[m["date"] == d].dropna(subset=["margin_change"])
            gmap = {}
            if members is not None and not members.empty:
                for r in members.itertuples():
                    gmap.setdefault(str(r.code), []).append(r.group_name)
            x = x[x["margin_change"] != 0]
            x = pd.concat([x.nlargest(400, "margin_change"), x.nsmallest(400, "margin_change")]).drop_duplicates("code")
            rank = {"d": d, "rows": [{"code": str(r.code), "name": names.get(r.code), "chg": float(r.margin_change),
                                      "g": gmap.get(str(r.code), [])} for r in x.itertuples()]}
            # 融券增減排行（2026-10-26 Andy：「需要新增一個融券的」）：同一天、同一批上市個股，short_change 單位張（前端 ÷1000 顯示千張）
            if "short_change" in m.columns:
                y = m[m["date"] == d].dropna(subset=["short_change"])
                y = y[y["short_change"] != 0]
                y = pd.concat([y.nlargest(400, "short_change"), y.nsmallest(400, "short_change")]).drop_duplicates("code")
                srank = {"d": d, "rows": [{"code": str(r.code), "name": names.get(r.code), "chg": float(r.short_change),
                                           "bal": _f(getattr(r, "short_balance", None)), "g": gmap.get(str(r.code), [])}
                                          for r in y.itertuples()]}
    rows = _rows(mt, caps, partial_days, _idx_map(idx, "TSE"))
    out["rows"] = rows[-MARGIN_DAYS:]
    out["asof"] = rows[-1]["d"]
    out["rank"] = rank
    out["short_rank"] = srank
    return out


def _taiex(idx):
    if idx is None or idx.empty:
        return {}
    t = idx[idx["symbol"] == "TSE"]
    return dict(zip(t["date"].astype(str), pd.to_numeric(t["close"], errors="coerce")))


def settle_dates(dates: list[str]) -> list[str]:
    """期貨結算日＝每月第三個星期三；那天沒開盤就順延到之後第一個有資料的交易日。"""
    import datetime as dt
    ds = sorted(dates)
    if not ds:
        return []
    have = set(ds)
    out = []
    y, m = int(ds[0][:4]), int(ds[0][5:7])
    ey, em = int(ds[-1][:4]), int(ds[-1][5:7])
    while (y, m) <= (ey, em):
        d = dt.date(y, m, 1)
        d += dt.timedelta(days=(2 - d.weekday()) % 7 + 14)
        x = d
        for _ in range(7):
            if x.isoformat() in have:
                out.append(x.isoformat())
                break
            x += dt.timedelta(days=1)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def fut_oi_json(fi: pd.DataFrame, idx=None, source="") -> dict:
    """site/data/fut_oi.json：台指期（TX）三大法人多／空／淨未平倉口數，日期舊到新（order=asc）。"""
    out = {"asof": None, "source": source, "order": "asc", "dates": [], "taiex": []}
    for w in WHO:
        out[w] = {"long": [], "short": [], "net": []}
    if fi is None or fi.empty:
        return out
    d = fi[fi["futures_id"] == "TX"]
    piv = {w: d[d["who"] == w].drop_duplicates("date", keep="last").set_index("date") for w in WHO}
    dates = sorted(set.intersection(*[set(p.index) for p in piv.values()])) if all(len(p) for p in piv.values()) else []
    tx = _taiex(idx)
    out["dates"] = dates
    out["taiex"] = [_f(tx.get(x)) for x in dates]
    for w in WHO:
        lo, sh = piv[w]["long_oi"], piv[w]["short_oi"]
        out[w]["long"] = [_f(lo[x]) for x in dates]
        out[w]["short"] = [_f(sh[x]) for x in dates]
        out[w]["net"] = [_f(lo[x] - sh[x]) for x in dates]
    out["asof"] = dates[-1] if dates else None
    return out


RETAIL_PRODUCTS = ("TX", "MTX", "TMF")   # 大台、小台、微台


def _retail_one(fi: pd.DataFrame, oi: pd.DataFrame, fid: str, tx) -> dict:
    out = {"dates": [], "taiex": [], "total_oi": [], "retail_long": [], "retail_short": [], "retail_net": [],
           "ratio_pct": [], "settle_dates": []}
    if fi is None or fi.empty or oi is None or oi.empty:
        return out
    d = fi[fi["futures_id"] == fid]
    tot = oi[oi["futures_id"] == fid].drop_duplicates("date", keep="last").set_index("date")["oi"]
    byw = {w: d[d["who"] == w].drop_duplicates("date", keep="last").set_index("date") for w in WHO}
    if not len(tot) or not all(len(p) for p in byw.values()):
        return out
    dates = sorted(set(tot.index).intersection(*[set(p.index) for p in byw.values()]))
    for x in dates:
        t = float(tot[x])
        if not t:
            continue
        il = sum(float(byw[w].loc[x, "long_oi"]) for w in WHO)
        is_ = sum(float(byw[w].loc[x, "short_oi"]) for w in WHO)
        rl, rs = t - il, t - is_
        out["dates"].append(x); out["taiex"].append(_f(tx.get(x))); out["total_oi"].append(t)
        out["retail_long"].append(rl); out["retail_short"].append(rs); out["retail_net"].append(rl - rs)
        out["ratio_pct"].append((rl - rs) / t * 100)
    out["settle_dates"] = settle_dates(out["dates"])
    return out


def retail_ratio_json(fi: pd.DataFrame, oi: pd.DataFrame, idx=None, source="") -> dict:
    """site/data/retail_ratio.json（2026-10-20 新合約）：{asof, source, order, products:{TX,MTX,TMF:{dates,taiex,...}}}。
    散戶多單＝全市場未平倉(所有到期月份合計)−三大法人多方未平倉；散戶空單同理；
    多空比＝(散戶多−散戶空)÷全市場未平倉×100。三商品各自獨立算；asof＝三商品最新日的最大值。"""
    tx = _taiex(idx)
    prods = {f: _retail_one(fi, oi, f, tx) for f in RETAIL_PRODUCTS}
    last = [p["dates"][-1] for p in prods.values() if p["dates"]]
    return {"asof": max(last) if last else None, "source": source, "order": "asc", "products": prods}


def build(mt, md, company, price, idx=None, members=None, mt_otc=None) -> dict:
    """market_fut.json。margin.rows＝上市（舊鍵，舊前端照讀）；margin.mkts＝{twse, tpex, all} 三組同格式的列，
    前端「上市／上櫃／合計」分段開關切換用；margin.idx_name 給圖例。"""
    mb = margin_block(mt, md, company, price, idx, members)
    otc = otc_rows(mt_otc, md, company, price, idx)
    mb["mkts"] = {"twse": mb["rows"], "tpex": otc, "all": combine_rows(mb["rows"], otc, idx)}
    mb["idx_name"] = {"twse": "加權指數", "tpex": "櫃買指數", "all": "加權指數"}
    mb["otc_from"] = otc[0]["d"] if otc else None
    return {"margin": mb}
