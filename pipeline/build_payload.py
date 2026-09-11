"""把資料湖算成前端要的 JSON。

前端只負責畫圖，所有運算都在這裡做完 —— 這樣手機開也是秒開，
而且圖表跟數字永遠一致（不會前端算一套、後端算一套）。
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import config, indicators
from .compute import flow, fundamental, mtf, rrg, season, stockpage, technical, themes
from .groups import loader
from .util import store
from .util.roc import is_tradable_security

log = logging.getLogger(__name__)


def _clean(obj):
    """NaN / numpy 型別轉成 JSON 吃得下的形式。"""
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        return None if (pd.isna(obj) or np.isinf(obj)) else round(float(obj), 4)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if obj is pd.NaT or (isinstance(obj, float) and pd.isna(obj)):
        return None
    return obj


def _write(name: str, payload) -> None:
    path = config.SITE_DATA / f"{name}.json"
    path.write_text(json.dumps(_clean(payload), ensure_ascii=False), encoding="utf-8")
    log.info("寫出 %s（%.1f KB）", path.name, path.stat().st_size / 1024)


def build() -> None:
    price = store.read("price_daily")
    if price.empty:
        log.warning("資料湖還沒有行情資料，只產出空的 meta")
        _write("meta", {"status": "empty", "generated_at":
                        datetime.now(timezone.utc).isoformat()})
        return

    company = store.read("company_info")
    inst = store.read("inst_daily")
    margin = store.read("margin_daily")
    market = store.read("market_daily")
    valuation = store.read("valuation_daily")
    financial = store.read("financial_q")
    balance = store.read("balance_q")
    revenue = store.read("revenue_monthly")

    # 簡稱對照：company_info 是唯一可靠來源（回補的歷史列沒有名稱）
    names = {}
    if not company.empty and "name" in company.columns:
        names = (company.dropna(subset=["name"]).drop_duplicates("code", keep="last")
                        .set_index("code")["name"].to_dict())
    markets = {}
    if not company.empty and "market" in company.columns:
        markets = (company.dropna(subset=["market"]).drop_duplicates("code", keep="last")
                          .set_index("code")["market"].to_dict())

    latest = str(price["date"].max())
    history_days = int(price["date"].nunique())

    # ---------------------------------------------------------- M1 資金面
    group_hist = flow.group_daily(price, company, inst, margin)
    today = (group_hist[group_hist["date"] == latest]
             if not group_hist.empty else pd.DataFrame())

    _write("groups_today", today.to_dict("records"))
    _write("rotation", flow.rotation_radar(group_hist).head(25).to_dict("records"))
    _write("concentration", flow.concentration(group_hist).tail(120).to_dict("records"))
    _write("relative_strength",
           flow.relative_strength(group_hist, market).to_dict("records"))
    _write("trust_streak", flow.trust_streak(inst).head(30).to_dict("records"))

    # ---------------------------------------------------------- 市場體溫
    heat = {"date": latest}
    if not market.empty:
        mk = market.sort_values("date")
        heat["taiex"] = _clean(mk["taiex"].iloc[-1])
        heat["change"] = _clean(mk["change"].iloc[-1])
        heat["turnover"] = _clean(mk["turnover"].iloc[-1])
        tv = pd.to_numeric(mk["turnover"], errors="coerce")
        if len(tv.dropna()) >= 20:
            heat["turnover_ma20"] = _clean(tv.tail(20).mean())
        series = mk[["date", "taiex"]].dropna()
        # FMTQIK 只回當月至今，所以剛上線時走勢圖只有幾個點。
        # 用 yfinance 的 ^TWII 把更早的歷史補上，之後再逐日累積自己的。
        if len(series) < 60:
            intl = store.read("intl_daily")
            if not intl.empty:
                twii = intl[intl["symbol"] == "^TWII"][["date", "close"]]
                twii = twii.rename(columns={"close": "taiex"}).dropna()
                if not twii.empty:
                    have = set(series["date"].astype(str))
                    extra = twii[~twii["date"].astype(str).isin(have)]
                    series = (pd.concat([extra, series], ignore_index=True)
                                .sort_values("date"))
                    heat["taiex_series_source"] = "FMTQIK + ^TWII"
        heat["taiex_series"] = _clean(
            series.tail(120)[["date", "taiex"]].to_dict("records"))

    day = price[price["date"] == latest].copy()
    # 家數只算普通股與 ETF —— 把權證算進去會變成五千多家，那不是台股的實際家數
    day = day[day["code"].map(is_tradable_security)]
    day["prev"] = day["close"] - day["change"].fillna(0)
    day["chg_pct"] = np.where(day["prev"] > 0, day["change"] / day["prev"] * 100, np.nan)
    heat["advancers"] = int((day["chg_pct"] > 0).sum())
    heat["decliners"] = int((day["chg_pct"] < 0).sum())
    heat["unchanged"] = int((day["chg_pct"] == 0).sum())
    if not today.empty:
        heat["top5_share"] = _clean(today.nlargest(5, "turnover")["turnover_share"].sum())

    # ---------------------------------------------------------- M4 季節性
    _write("seasonality", seasonality(price, company).to_dict("records"))
    intl_all = store.read("intl_daily")
    try:
        _write("seasonality_v3", season.build(price, intl_all))
    except Exception as exc:  # noqa: BLE001
        log.warning("季節性 v3 產出失敗：%s", exc)
        _write("seasonality_v3", {"periods": {}, "groups": [], "note": str(exc)})

    # ---------------------------------------------------------- M2 基本面
    day_px = price[price["date"] == latest][["code", "close"]]
    ttm_df = fundamental.ttm(financial)
    bal = fundamental.latest_balance(balance)
    val = fundamental.valuation(day_px, ttm_df, bal)
    gval = fundamental.group_valuation(val, company)
    rev = fundamental.revenue_momentum(revenue)

    fund_rows = []
    if not val.empty:
        gv_first = (gval.sort_values("thin_sample").drop_duplicates("code", keep="first")
                        .set_index("code") if not gval.empty else pd.DataFrame())
        rev_idx = rev.set_index("code") if not rev.empty else pd.DataFrame()
        for _, r in val.iterrows():
            c = r["code"]
            g = gv_first.loc[c] if (len(gv_first) and c in gv_first.index) else None
            rv = rev_idx.loc[c] if (len(rev_idx) and c in rev_idx.index) else None
            fund_rows.append(_clean({
                "code": c, "name": names.get(c), "market": markets.get(c),
                "close": _clean(r["close"]),
                "ttm_eps": _clean(r.get("ttm_eps")), "ttm_complete": bool(r.get("ttm_complete")),
                "latest_period": r.get("latest_period"),
                "pe": _clean(r.get("pe")), "pb": _clean(r.get("pb")), "ps": _clean(r.get("ps")),
                "roe": _clean(r.get("roe")), "gross_margin": _clean(r.get("gross_margin")),
                "market_cap": _clean(r.get("market_cap")), "is_loss": bool(r.get("is_loss")),
                "group_id": (g["group_id"] if g is not None else None),
                "group_name": (g["group_name"] if g is not None else None),
                "metric": (g["metric"] if g is not None else None),
                "metric_value": _clean(g["metric_value"]) if g is not None else None,
                "group_median": _clean(g["group_median"]) if g is not None else None,
                "group_n": int(g["group_n"]) if g is not None else None,
                "percentile": _clean(g["percentile"]) if g is not None else None,
                "vs_median": _clean(g["vs_median"]) if g is not None else None,
                "thin_sample": bool(g["thin_sample"]) if g is not None else None,
                "fallback": (g.get("fallback") if g is not None else None),
                "rev_ym": (rv["ym"] if rv is not None else None),
                "rev_yoy": _clean(rv["yoy_adj"]) if rv is not None else None,
                "rev_yoy_note": (rv["yoy_note"] if rv is not None else None),
                "rev_mom": _clean(rv["mom"]) if rv is not None else None,
                "rev_mom_vs_typical": _clean(rv["mom_vs_typical"]) if rv is not None else None,
                "rev_yoy_3m": _clean(rv["yoy_3m"]) if rv is not None else None,
                "rev_ytd_yoy": _clean(rv["ytd_yoy"]) if rv is not None else None,
                "rev_streak": int(rv["growth_streak"]) if rv is not None else None,
                "rev_record_high": bool(rv["is_record_high"]) if rv is not None else None,
                "rev_flag_spike": bool(rv["flag_spike"]) if rv is not None else None,
                "momentum_score": _clean(fundamental.momentum_score(rv)) if rv is not None else None,
            }))
    _write("fundamental", fund_rows)

    # 族群估值摘要（每族群一列：口徑、中位數、樣本數、虧損比例）
    if not gval.empty:
        gsum = (gval.groupby(["group_id", "group_name", "metric"], dropna=False)
                    .agg(group_median=("group_median", "first"), group_n=("group_n", "first"),
                         loss_ratio=("group_loss_ratio", "first"))
                    .reset_index())
        _write("group_valuation", gsum.to_dict("records"))
    else:
        _write("group_valuation", [])

    # 券商目標價引述（近 60 天）
    bv = store.read("broker_views")
    if bv.empty:
        bv = pd.DataFrame()
    if not bv.empty:
        cutoff = (pd.Timestamp(latest) - pd.Timedelta(days=60)).date().isoformat()
        bv = bv[bv["date"].astype(str) >= cutoff].sort_values("date", ascending=False)
        bv["name"] = bv["code"].map(names)
        _write("broker_views", bv.to_dict("records"))
    else:
        _write("broker_views", [])

    # ---------------------------------------------------------- 個股技術面 + 個股頁
    news_all = store.read("news")
    sh_all = store.read("shareholding_weekly")
    deep = {
        "revenue": revenue, "financial": financial, "margin": margin, "shareholding": sh_all,
        "dividend_events": store.read("dividend_events"),
        "dividend_results": store.read("dividend_results"),
        "company": company,
    }
    cand_rows, breadth = candidates(price, valuation, company, inst, latest,
                                    names=names, markets=markets, fund=fund_rows,
                                    news_df=news_all, broker=bv if not bv.empty else None,
                                    shareholding=sh_all, deep=deep)
    _write("candidates", cand_rows)
    gdetail = group_detail(price, company, inst, latest, cand_rows, names)
    _write("groups_detail", gdetail)
    heat.update({"breadth": breadth})
    _write("market_heat", heat)

    # ---------------------------------------------------------- v3：資金流向 / 題材 / 產業地圖
    try:
        _write("flow_v3", {
            "date": latest,
            "rrg": rrg.rrg(group_hist, price),
            "sankey": rrg.sankey(today, gdetail),
            "share": rrg.share_series(group_hist),
        })
    except Exception as exc:  # noqa: BLE001
        log.warning("資金流向 v3 產出失敗：%s", exc)
        _write("flow_v3", {"date": latest, "rrg": {"points": []}, "sankey": {"nodes": [], "links": []},
                           "share": {"dates": [], "series": []}})
    try:
        _write("themes", themes.build(price, inst, news_all, names, latest))
    except Exception as exc:  # noqa: BLE001
        log.warning("題材熱力產出失敗：%s", exc)
        _write("themes", {"date": latest, "themes": [], "series": {}})
    try:
        _write("industry_map", industry_map(today, gdetail, fund_rows, gval, latest))
    except Exception as exc:  # noqa: BLE001
        log.warning("產業地圖產出失敗：%s", exc)
        _write("industry_map", {"date": latest, "chains": [], "industries": [], "segments_pe": {}})

    # ---------------------------------------------------------- 新聞
    news_df = store.read("news")
    if not news_df.empty:
        if "category" not in news_df.columns:
            news_df["category"] = "台股"
        news_df = news_df.sort_values("published_at", ascending=False)
        recent = pd.concat([g.head(40) for _, g in news_df.groupby("category")],
                           ignore_index=True)
        _write("news", recent.to_dict("records"))
    else:
        _write("news", [])

    # ---------------------------------------------------------- 國際
    intl = store.read("intl_daily")
    if not intl.empty:
        recent = intl[intl["date"] >= (pd.Timestamp(latest) -
                                       pd.Timedelta(days=180)).date().isoformat()]
        _write("intl", recent.to_dict("records"))
    else:
        _write("intl", [])

    # ---------------------------------------------------------- 產業關聯圖
    try:
        _write("supply_chain", loader.supply_chain())
    except Exception as exc:  # noqa: BLE001
        log.warning("產業關聯圖產出失敗：%s", exc)
        _write("supply_chain", {})

    # ---------------------------------------------------------- meta
    last_run = {}
    lr = config.STATE / "last_run.json"
    if lr.exists():
        try:
            last_run = json.loads(lr.read_text())
        except ValueError:
            pass

    _write("meta", {
        "status": "ok",
        "data_date": latest,
        "history_days": history_days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "groups_health": loader.health(),
        "table_summary": store.table_summary().to_dict("records"),
        "last_run_errors": last_run.get("errors", []),
    })


def seasonality(price: pd.DataFrame, company: pd.DataFrame) -> pd.DataFrame:
    """族群 × 月份的歷史平均報酬、勝率、樣本數。

    刻意三個數字一起輸出 —— 只給平均報酬會讓人把 3 個樣本的巧合當成規律。
    """
    if price.empty:
        return pd.DataFrame()

    df = price.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "close"])
    m = loader.membership()
    df = df.merge(m[["code", "group_id", "group_name"]], on="code", how="inner")
    if df.empty:
        return pd.DataFrame()

    df["ym"] = df["date"].dt.to_period("M")
    monthly = (df.sort_values("date")
                 .groupby(["group_id", "group_name", "ym"])
                 .agg(first=("close", "first"), last=("close", "last"))
                 .reset_index())
    monthly["ret"] = (monthly["last"] / monthly["first"] - 1) * 100
    monthly["month"] = monthly["ym"].dt.month

    out = (monthly.groupby(["group_id", "group_name", "month"])
                  .agg(avg_return=("ret", "mean"),
                       median_return=("ret", "median"),
                       win_rate=("ret", lambda s: float((s > 0).mean() * 100)),
                       samples=("ret", "size"))
                  .reset_index())
    # 樣本數太少的直接不給結論，避免誤導
    out.loc[out["samples"] < 3, ["avg_return", "median_return", "win_rate"]] = np.nan
    return out


def candidates(price: pd.DataFrame, valuation: pd.DataFrame,
               company: pd.DataFrame, inst: pd.DataFrame,
               latest: str, limit: int = 150, *, names: dict | None = None,
               markets: dict | None = None, fund: list[dict] | None = None,
               news_df: pd.DataFrame | None = None, broker: pd.DataFrame | None = None,
               shareholding: pd.DataFrame | None = None,
               deep: dict | None = None) -> tuple[list[dict], dict]:
    """當日候選股 + 每檔的個股頁 JSON。

    回傳 (候選清單, 市場寬度統計)。個股頁直接寫到 site/data/stock/<code>.json。
    v3：個股頁多了分 K（Yahoo）、多週期 SMC、營收/獲利/除權息/資券/大戶散戶/基本資料。
    """
    if price.empty:
        return [], {}
    deep = deep or {}

    names = names or {}
    markets = markets or {}
    fund_idx = {f["code"]: f for f in (fund or [])}
    m = loader.membership()
    group_of = (m.groupby("code")
                 .agg(group_id=("group_id", "first"), group_name=("group_name", "first"),
                      groups=("group_name", lambda x: list(dict.fromkeys(x))))
                 .to_dict("index"))

    day = price[price["date"] == latest]
    # 族群成分股全部算，再用成交值補到 limit（指數列如 TAIEX 與權證不算個股）
    member_codes = set(m["code"])
    by_turnover = [c for c in day.sort_values("turnover", ascending=False)["code"].tolist()
                   if is_tradable_security(c)]
    codes = [c for c in by_turnover if c in member_codes]
    for c in by_turnover:
        if len(codes) >= limit:
            break
        if c not in codes:
            codes.append(c)

    hist = price[price["code"].isin(codes)].sort_values(["code", "date"])
    val_today = valuation[valuation["date"] == latest] if not valuation.empty else pd.DataFrame()
    inst_hist = inst[inst["code"].isin(codes)] if not inst.empty else pd.DataFrame()
    inst_today = inst_hist[inst_hist["date"] == latest] if not inst_hist.empty else pd.DataFrame()
    news_by_code: dict[str, list] = {}
    if news_df is not None and not news_df.empty:
        for _, n in news_df.sort_values("published_at", ascending=False).iterrows():
            for c in str(n.get("codes") or "").split(","):
                if c and c in codes and len(news_by_code.setdefault(c, [])) < 8:
                    news_by_code[c].append({"date": n.get("date"), "title": n.get("title"),
                                            "url": n.get("url"), "source": n.get("source"),
                                            "category": n.get("category")})
    broker_by_code: dict[str, list] = {}
    if broker is not None and not broker.empty:
        for _, b in broker.sort_values("date", ascending=False).iterrows():
            broker_by_code.setdefault(b["code"], []).append({
                "date": b.get("date"), "broker": b.get("broker"), "target_price": _clean(b.get("target_price")),
                "action": b.get("action"), "rating": b.get("rating"), "url": b.get("url")})
    sh_by_code: dict[str, list] = {}
    if shareholding is not None and not shareholding.empty:
        big = shareholding[shareholding["level"].isin([13, 14, 15])]
        g = big.groupby(["code", "date"])["pct"].sum().reset_index()
        for c, gg in g.groupby("code"):
            sh_by_code[c] = gg.sort_values("date").tail(26)[["date", "pct"]].to_dict("records")

    stock_dir = config.SITE_DATA / "stock"
    stock_dir.mkdir(parents=True, exist_ok=True)

    # 分 K（Yahoo）：只在正式管線抓，測試與本機預覽用 SKIP_INTRADAY=1 跳過
    m60 = m15 = pd.DataFrame()
    if not os.environ.get("SKIP_INTRADAY"):
        try:
            from .sources import yahoo
            m60 = yahoo.intraday(codes, markets, "60m", "730d")
            m15 = yahoo.intraday(codes, markets, "15m", "60d")
            log.info("分 K：60 分 %d 列、15 分 %d 列", len(m60), len(m15))
        except Exception as exc:  # noqa: BLE001
            log.warning("分 K 抓取失敗：%s", exc)
    m60_by = {c: g for c, g in m60.groupby("code")} if not m60.empty else {}
    m15_by = {c: g for c, g in m15.groupby("code")} if not m15.empty else {}

    rows = []
    breadth = {"n": 0, "above_ma20": 0, "above_ma60": 0, "new_high_60": 0, "grade_a": 0, "grade_b": 0}
    for code, g in hist.groupby("code"):
        if len(g) < 60:
            continue
        cols = ["date", "open", "high", "low", "close"] + (["volume"] if "volume" in g else [])
        try:
            ind = indicators.compute_all(g[cols])
        except Exception:  # noqa: BLE001
            continue
        last = ind.iloc[-1]
        tech = indicators.technical_score(last)
        avg_turnover = float(pd.to_numeric(g["turnover"].tail(20), errors="coerce").mean())
        verdict = technical.evaluate(ind, avg_turnover=avg_turnover)

        breadth["n"] += 1
        if pd.notna(last.get("ma20")) and last["close"] > last["ma20"]:
            breadth["above_ma20"] += 1
        if pd.notna(last.get("ma60")) and last["close"] > last["ma60"]:
            breadth["above_ma60"] += 1
        if last["close"] >= ind["high"].tail(60).max():
            breadth["new_high_60"] += 1
        if verdict["grade"] == "A":
            breadth["grade_a"] += 1
        elif verdict["grade"] == "B":
            breadth["grade_b"] += 1

        gi = group_of.get(code, {})
        gname = gi.get("group_name") or "—"
        fx = fund_idx.get(code, {})
        pe = pct = None
        if not val_today.empty:
            v = val_today[val_today["code"] == code]
            if not v.empty:
                pe = _clean(v["pe"].iloc[0])
        trust_net = foreign_net = None
        if not inst_today.empty:
            i = inst_today[inst_today["code"] == code]
            if not i.empty:
                trust_net = _clean(i["trust"].iloc[0]); foreign_net = _clean(i["foreign_total"].iloc[0])
        name = names.get(code) or (g["name"].dropna().iloc[-1] if "name" in g and g["name"].notna().any() else code)
        prev = ind["close"].iloc[-2] if len(ind) > 1 else last["close"]
        chg_pct = float((last["close"] / prev - 1) * 100) if prev else None

        row = {
            "code": code, "name": name, "market": markets.get(code),
            "group": gname, "group_id": gi.get("group_id"), "groups": gi.get("groups", []),
            "close": _clean(last["close"]), "chg_pct": _clean(chg_pct),
            "tech_score": round(tech, 1), "verdict": verdict["verdict"], "grade": verdict["grade"],
            "ma_align": int(last.get("ma_align") or 0),
            "rsi": _clean(last.get("rsi14")), "k": _clean(last.get("k")), "d": _clean(last.get("d")),
            "osc": _clean(last.get("osc")), "trend": int(last.get("trend") or 0),
            "bos": bool(last.get("bos")), "choch": bool(last.get("choch")),
            "fvg_bull": bool(last.get("fvg_bull")), "sweep_low": bool(last.get("sweep_low")),
            "bias20": _clean(last.get("bias20")), "vol_ratio": _clean(last.get("vol_ratio")),
            "pe": fx.get("pe") if fx.get("pe") is not None else pe,
            "pe_percentile": fx.get("percentile"), "metric": fx.get("metric"),
            "metric_value": fx.get("metric_value"), "group_n": fx.get("group_n"),
            "rev_yoy": fx.get("rev_yoy"), "rev_streak": fx.get("rev_streak"),
            "momentum_score": fx.get("momentum_score"),
            "trust_net": trust_net, "foreign_net": foreign_net,
            "turnover": _clean(g["turnover"].iloc[-1]), "avg_turnover": _clean(avg_turnover),
            "stop": verdict["stop"], "tp1": verdict["tp1"], "rr": verdict["rr"],
        }
        rows.append(row)

        # ---------------- 個股頁
        tail = ind.tail(250)
        long = ind.tail(1500)      # 6 年日 K，前端自己合成週 K / 月 K
        bars60 = m60_by.get(code, pd.DataFrame())
        bars15 = m15_by.get(code, pd.DataFrame())
        try:
            mtf_res = mtf.build(g[cols], bars60 if not bars60.empty else None,
                                bars15 if not bars15.empty else None)
        except Exception as exc:  # noqa: BLE001
            log.debug("%s 多週期分析失敗：%s", code, exc)
            mtf_res = {"tf": {}, "summary": {}}
        bars240 = mtf.resample_intraday(bars60, "240min") if not bars60.empty else pd.DataFrame()

        def _bars(df_, tcol):
            if df_ is None or df_.empty:
                return []
            return _clean([[str(r_[tcol]), r_["open"], r_["high"], r_["low"], r_["close"],
                            (r_["volume"] if "volume" in df_ else None)] for _, r_ in df_.iterrows()])

        page = {
            "meta": {k: row[k] for k in ("code", "name", "market", "group", "group_id", "groups")},
            "as_of": latest,
            "version": 3,
            "ohlcv": _clean([[r_["date"], r_["open"], r_["high"], r_["low"], r_["close"],
                              (r_["volume"] if "volume" in tail else None)]
                             for _, r_ in tail.iterrows()]),
            "daily": _bars(long, "date"),
            "intraday": {"60m": _bars(bars60.tail(1800), "ts"), "240m": _bars(bars240.tail(800), "ts"),
                         "15m": _bars(bars15.tail(1100), "ts")},
            "mtf": _clean(mtf_res),
            "revenue": _clean(stockpage.revenue_series(deep.get("revenue"), code)),
            "profit": _clean(stockpage.profit_series(deep.get("financial"), code)),
            "pe_history": _clean(stockpage.pe_history(price, deep.get("financial"), code)),
            "dividends": _clean(stockpage.dividends(deep.get("dividend_events"), deep.get("dividend_results"),
                                                    price, code, float(last["close"]))),
            "margin": _clean(stockpage.margin_series(deep.get("margin"), code)),
            "holders": _clean(stockpage.holder_series(deep.get("shareholding"), code)),
            "inst_v3": _clean(stockpage.inst_series(inst_hist if not inst_hist.empty else None, code)),
            "basics": _clean(stockpage.basics(deep.get("company"), code)),
            "series": {k: _clean(tail[k].tolist()) for k in
                       ("ma5", "ma20", "ma60", "ma120", "k", "d", "dif", "macd", "osc",
                        "rsi14", "vol_ma20", "atr14") if k in tail},
            "marks": {
                "bos": _clean(tail[tail["bos"].fillna(False)]["date"].tolist()),
                "choch": _clean([[r_["date"], int(r_["trend"])] for _, r_ in
                                 tail[tail["choch"].fillna(False)].iterrows()]),
                "sweep_low": _clean(tail[tail["sweep_low"].fillna(False)]["date"].tolist()),
                "sweep_high": _clean(tail[tail["sweep_high"].fillna(False)]["date"].tolist()),
                "limit_up": _clean(tail[tail["limit_up"].fillna(False)]["date"].tolist()),
            },
            "verdict": _clean(verdict),
            "summary": row,
            "fundamental": fx or None,
            "inst": _clean(inst_hist[inst_hist["code"] == code].sort_values("date").tail(60)
                           [["date", "foreign_total", "trust", "dealer"]].to_dict("records"))
                    if not inst_hist.empty else [],
            "shareholding": _clean(sh_by_code.get(code, [])),
            "news": news_by_code.get(code, []),
            "broker_views": broker_by_code.get(code, [])[:6],
        }
        # 整頁過一次 _clean：任何漏網的 NaN 都會讓瀏覽器 JSON.parse 直接失敗
        (stock_dir / f"{code}.json").write_text(json.dumps(_clean(page), ensure_ascii=False),
                                                encoding="utf-8")

    rows.sort(key=lambda r: (r["grade"] or "Z", -r["tech_score"]))
    if breadth["n"]:
        breadth["pct_above_ma20"] = round(breadth["above_ma20"] / breadth["n"] * 100, 1)
        breadth["pct_above_ma60"] = round(breadth["above_ma60"] / breadth["n"] * 100, 1)
    log.info("個股頁：%d 檔，A 級 %d、B 級 %d", len(rows), breadth["grade_a"], breadth["grade_b"])
    return rows, breadth


def group_detail(price: pd.DataFrame, company: pd.DataFrame, inst: pd.DataFrame,
                 latest: str, cand_rows: list[dict], names: dict) -> dict:
    """每個族群的成分股明細，給熱力圖下鑽與法人下鑽用。

    v3 修正：熱力圖上的「ETF」「其他電子」這類板塊是法定產業別的 fallback 族群（ind_*），
    以前這裡只展開 groups.yaml 的族群，點下去就是空的。現在用 flow._attach_groups 同一套
    邏輯把 fallback 族群一起展開。
    """
    day_px = price[price["date"] == latest]
    m = flow._attach_groups(day_px, company)
    if m.empty:
        m = loader.membership()
    m = m[["code", "group_id", "group_name"]].drop_duplicates()
    day = day_px.set_index("code")
    inst_today = inst[inst["date"] == latest].set_index("code") if not inst.empty else pd.DataFrame()
    cand_idx = {r["code"]: r for r in cand_rows}
    out = {}
    for gid, g in m.groupby("group_id"):
        members = []
        for c in g["code"]:
            if c not in day.index:
                continue
            r = day.loc[c]
            if isinstance(r, pd.DataFrame):
                r = r.iloc[0]
            prev = r["close"] - (r["change"] if pd.notna(r["change"]) else 0)
            cr = cand_idx.get(c, {})
            it = inst_today.loc[c] if (len(inst_today) and c in inst_today.index) else None
            if isinstance(it, pd.DataFrame):
                it = it.iloc[0]
            members.append({
                "code": c, "name": names.get(c) or r.get("name") or c,
                "close": _clean(r["close"]),
                "chg_pct": _clean((r["change"] / prev * 100) if prev else None),
                "turnover": _clean(r["turnover"]),
                "foreign": _clean(it["foreign_total"]) if it is not None else None,
                "trust": _clean(it["trust"]) if it is not None else None,
                "dealer": _clean(it["dealer"]) if it is not None else None,
                "tech_score": cr.get("tech_score"), "grade": cr.get("grade"),
                "verdict": cr.get("verdict"), "pe_percentile": cr.get("pe_percentile"),
                "rev_yoy": cr.get("rev_yoy"), "has_page": c in cand_idx,
            })
        members.sort(key=lambda x: -(x["turnover"] or 0))
        out[gid] = {"group_name": g["group_name"].iloc[0], "members": members}
    return out


def industry_map(today: pd.DataFrame, gdetail: dict, fund_rows: list[dict],
                 gval: pd.DataFrame, latest: str) -> dict:
    """產業地圖（v3 合併頁的總覽）：產業鏈 → 族群 → 成分股，附本益比中位數與資金流向。"""
    chains = loader.chains()
    fund_idx = {f["code"]: f for f in (fund_rows or [])}
    gv = {}
    if gval is not None and not gval.empty:
        for _, r in gval.drop_duplicates("group_id").iterrows():
            gv[r["group_id"]] = {"metric": r.get("metric"), "median": _clean(r.get("group_median")),
                                 "n": int(r["group_n"]) if pd.notna(r.get("group_n")) else None}
    t = today.set_index("group_id") if today is not None and not today.empty else pd.DataFrame()

    def _group(gid: str, name: str, chain: str | None) -> dict:
        d = gdetail.get(gid, {})
        members = []
        for mmb in d.get("members", []):
            fx = fund_idx.get(mmb["code"], {})
            members.append({**mmb, "pe": fx.get("pe"), "pe_percentile": fx.get("percentile"),
                            "market_cap": fx.get("market_cap"), "momentum": fx.get("momentum_score")})
        tv = t.loc[gid] if len(t) and gid in t.index else None
        if isinstance(tv, pd.DataFrame):
            tv = tv.iloc[0]
        return {
            "id": gid, "name": name, "chain": chain, "n": len(members),
            "turnover": _clean(tv["turnover"]) if tv is not None else None,
            "turnover_share": _clean(tv["turnover_share"]) if tv is not None else None,
            "chg_pct": _clean(tv["chg_pct"]) if tv is not None and "chg_pct" in tv else None,
            "foreign": _clean(tv["foreign_total"]) if tv is not None and "foreign_total" in tv else None,
            "trust": _clean(tv["trust"]) if tv is not None and "trust" in tv else None,
            "valuation": gv.get(gid),
            "members": members,
        }

    cfg_groups = loader.load().get("groups") or {}
    out_chains = []
    for cid, c in chains.items():
        groups = [_group(gid, cfg_groups.get(gid, {}).get("name", gid), cid) for gid in c.get("order", [])
                  if gid in cfg_groups]
        out_chains.append({"id": cid, "name": c.get("name", cid), "groups": groups,
                           "turnover": sum((g["turnover"] or 0) for g in groups)})
    # 沒排進 chains.order 的族群
    placed = {gid for c in chains.values() for gid in c.get("order", [])}
    orphan = [_group(gid, g.get("name", gid), g.get("chain")) for gid, g in cfg_groups.items() if gid not in placed]
    if orphan:
        out_chains.append({"id": "_other", "name": "其他族群", "groups": orphan,
                           "turnover": sum((g["turnover"] or 0) for g in orphan)})
    industries = [_group(gid, d.get("group_name", gid), "industry") for gid, d in gdetail.items()
                  if gid.startswith("ind_")]
    industries.sort(key=lambda g: -(g["turnover"] or 0))

    # 供應鏈環節本益比（supply_chain.yaml 的公司 → fundamental）
    seg_pe = {}
    try:
        sc = loader.supply_chain()
        by_seg: dict[str, list] = {}
        for comp in sc.get("companies", []):
            code = comp.get("tw_code")
            if code:
                by_seg.setdefault(comp.get("segment"), []).append(code)
        for seg, codes in by_seg.items():
            pes = [fund_idx[c]["pe"] for c in codes if c in fund_idx and fund_idx[c].get("pe")]
            pes = [p for p in pes if 3 <= p <= 200]
            seg_pe[seg] = {"n": len(pes), "median": (round(float(np.median(pes)), 1) if pes else None),
                           "codes": codes}
    except Exception as exc:  # noqa: BLE001
        log.debug("環節本益比失敗：%s", exc)

    return {"date": latest, "chains": out_chains, "industries": industries, "segments_pe": seg_pe}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s | %(message)s",
                        datefmt="%H:%M:%S")
    build()
