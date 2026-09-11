"""把資料湖算成前端要的 JSON。

前端只負責畫圖，所有運算都在這裡做完 —— 這樣手機開也是秒開，
而且圖表跟數字永遠一致（不會前端算一套、後端算一套）。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import config, indicators
from .compute import flow, fundamental
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
    _write("market_heat", heat)

    # ---------------------------------------------------------- M4 季節性
    _write("seasonality", seasonality(price, company).to_dict("records"))

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
            fund_rows.append({
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
            })
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
    if not bv.empty:
        cutoff = (pd.Timestamp(latest) - pd.Timedelta(days=60)).date().isoformat()
        bv = bv[bv["date"].astype(str) >= cutoff].sort_values("date", ascending=False)
        bv["name"] = bv["code"].map(names)
        _write("broker_views", bv.to_dict("records"))
    else:
        _write("broker_views", [])

    # ---------------------------------------------------------- 個股技術面
    _write("candidates", candidates(price, valuation, company, inst, latest,
                                    names=names, markets=markets, fund=fund_rows))

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
               latest: str, limit: int = 120, *, names: dict | None = None,
               markets: dict | None = None, fund: list[dict] | None = None) -> list[dict]:
    """當日候選股：技術分 + 同業本益比分位 + 籌碼，合成綜合分。"""
    if price.empty:
        return []

    m = loader.membership()
    day = price[price["date"] == latest]
    # 只算有題材族群、且當日成交值前段的標的，避免無謂的運算
    codes = (day.merge(m[["code"]].drop_duplicates(), on="code", how="inner")
                .nlargest(limit, "turnover")["code"].tolist())
    if not codes:
        codes = day.nlargest(limit, "turnover")["code"].tolist()

    hist = price[price["code"].isin(codes)].sort_values(["code", "date"])
    val_today = (valuation[valuation["date"] == latest]
                 if not valuation.empty else pd.DataFrame())

    # 同業本益比分位需要族群內的 PE 分布
    pe_by_group = {}
    if not val_today.empty:
        joined = val_today.merge(m[["code", "group_id"]], on="code", how="inner")
        for gid, g in joined.groupby("group_id"):
            pes = pd.to_numeric(g["pe"], errors="coerce")
            pes = pes[(pes > 0) & (pes < 200)]
            if len(pes) >= 3:
                pe_by_group[gid] = pes

    inst_today = (inst[inst["date"] == latest]
                  if not inst.empty else pd.DataFrame())
    names = names or {}
    markets = markets or {}
    fund_idx = {f["code"]: f for f in (fund or [])}

    rows = []
    for code, g in hist.groupby("code"):
        if len(g) < 60:      # 資料太短算不出有意義的技術指標
            continue
        try:
            ind = indicators.compute_all(g[["date", "open", "high", "low", "close"]])
        except Exception:  # noqa: BLE001
            continue
        last = ind.iloc[-1]
        tech = indicators.technical_score(last)

        groups = m[m["code"] == code]
        gid = groups["group_id"].iloc[0] if not groups.empty else None
        gname = groups["group_name"].iloc[0] if not groups.empty else "—"

        pe = pct = None
        if not val_today.empty:
            v = val_today[val_today["code"] == code]
            if not v.empty:
                pe = _clean(v["pe"].iloc[0])
                if pe and gid in pe_by_group and pe > 0:
                    pct = float((pe_by_group[gid] < pe).mean() * 100)

        trust_net = None
        if not inst_today.empty:
            i = inst_today[inst_today["code"] == code]
            if not i.empty:
                trust_net = _clean(i["trust"].iloc[0])

        fx = fund_idx.get(code, {})
        rows.append({
            "code": code,
            # 簡稱一律從 company_info 拿；回補的歷史列沒有名稱欄位
            "name": names.get(code) or (g["name"].dropna().iloc[-1] if "name" in g.columns and g["name"].notna().any() else code),
            "market": markets.get(code),
            "group": gname,
            "group_id": gid,
            "close": _clean(last.get("close")),
            "tech_score": round(tech, 1),
            "ma_align": int(last.get("ma_align") or 0),
            "rsi": _clean(last.get("rsi14")),
            "k": _clean(last.get("k")),
            "d": _clean(last.get("d")),
            "osc": _clean(last.get("osc")),
            "trend": int(last.get("trend") or 0),
            "bos": bool(last.get("bos")),
            "choch": bool(last.get("choch")),
            "fvg_bull": bool(last.get("fvg_bull")),
            "sweep_low": bool(last.get("sweep_low")),
            "bias20": _clean(last.get("bias20")),
            # 估值改用自算的（TTM），證交所快照只當備援
            "pe": fx.get("pe") if fx.get("pe") is not None else pe,
            "pe_percentile": fx.get("percentile") if fx.get("percentile") is not None else (_clean(pct) if pct is not None else None),
            "metric": fx.get("metric"),
            "metric_value": fx.get("metric_value"),
            "group_n": fx.get("group_n"),
            "rev_yoy": fx.get("rev_yoy"),
            "rev_streak": fx.get("rev_streak"),
            "momentum_score": fx.get("momentum_score"),
            "trust_net": trust_net,
            "turnover": _clean(g["turnover"].iloc[-1]),
        })

    rows.sort(key=lambda r: r["tech_score"], reverse=True)
    return rows


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    build()
