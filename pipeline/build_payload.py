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
from .compute import flow, fundamental, mtf, rrg, scoring, season, stockpage, technical, themes
from .groups import loader
from .util import store
from .util.roc import is_tradable_security, norm_industry

log = logging.getLogger(__name__)

# 個股頁分層（決策見 DECISIONS #52）：每一檔上市櫃股票都要有頁面，差別只在資料多寡。
MIN_PAGE_BARS = 60        # 有這麼多日線才算得出指標、SMC 與評分
CAND_PER_FACET = 300      # candidates.json 每個面向各留這麼多檔（取聯集）
FULL_PAGE_BARS = 1500     # 有分 K 的那一批給 6 年日線（週／月線在前端合成）
SLIM_PAGE_BARS = 1250     # 其餘有歷史的股票也要 5 年（Andy 2026-09-18：「日 K 這種需要有至少 5 年」）
                          # 以前是 1000（約 4 年），只有前 400 檔達標，其餘不符規格
# 分 K（Yahoo）給幾檔。族群成分股一定有，其餘照成交值往下補到這個數。
# 從 150 拉到 400：Andy 回報「1 日以下的週期打開是空的」，大多是他看的股票不在前 150 名。
# yfinance 每批 40 檔、批間停 1 秒，兩個 interval 共約 20 批，多出來的時間在盤後管線可以接受。
INTRADAY_LIMIT = 400
# 事件側欄保留幾天（日期下拉選單就是拿這一段的日期去產生的）
NEWS_KEEP_DAYS = 7


def _f(v):
    """數字欄位轉 float；NaN／None 一律變 None（JSON 不吃 NaN）。"""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else round(f, 4)


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


def last_complete_date(price: pd.DataFrame, *, primary: str = "TWSE",
                       ratio: float = 0.6, lookback: int = 10) -> str:
    """回傳「主市場（上市）資料到齊」的最後一個交易日（字串）。

    - 有 market 欄位且含上市列：只看上市列，取近 lookback 個交易日中最多檔數的 ratio 倍為門檻，
      最後一個達門檻的日期就是它。櫃買抓失敗不會拖住更新（櫃買是可失敗來源）。
    - 沒有 market 欄位（測試資料）：用全部列數做同樣的判斷。
    - 只有一天資料：直接回傳那一天。
    """
    if price.empty:
        return ""
    px = price
    if "market" in px.columns and (px["market"] == primary).any():
        px = px[px["market"] == primary]
    counts = px.groupby(px["date"].astype(str))["code"].nunique().sort_index()
    if len(counts) < 2:
        return str(counts.index.max())
    ref = counts.tail(lookback).max()
    ok = counts[counts >= ratio * ref]
    return str(ok.index.max()) if not ok.empty else str(counts.index.max())


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

    # 最新交易日不能直接用 max(date)：證交所 OpenAPI 與櫃買更新時間不同，跑管線時常只有
    # 其中一邊有最新一天。之前就因為只有櫃買到了 09-11，整個上市股票被算漏
    # （個股頁 404、族群統計只剩上櫃）。改用「上市資料到齊的最後一天」，並把各日表裁到同一天。
    latest = last_complete_date(price)
    price = price[price["date"].astype(str) <= latest]
    inst, margin, market, valuation = (t[t["date"].astype(str) <= latest] if not t.empty and "date" in t else t
                                       for t in (inst, margin, market, valuation))
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
    # 三種法人各出一份（Andy 2026-09-15：「還要加上外資買超，以及綜合」）。
    # min_days=2 是給前端篩的空間 —— 他要能自己選「連續幾天以上」。
    streaks = {}
    for who in ("trust", "foreign", "total"):
        df_s = flow.trust_streak(inst, min_days=2, who=who)
        streaks[who] = [] if df_s.empty else _clean(df_s.head(60).to_dict("records"))
    _write("trust_streak", streaks.get("trust", []))      # 舊鍵留著，換版時不會開天窗
    _write("inst_streak", streaks)

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
    _write("candidates", shortlist(cand_rows))
    gdetail = group_detail(price, company, inst, latest, cand_rows, names, markets)
    _write("groups_detail", gdetail)
    heat.update({"breadth": breadth})
    _write("market_heat", heat)

    # ---------------------------------------------------------- 大盤三張圖的歷史日 K
    # Andy 2026-09-15：「櫃買 台指期怎麼可能沒有日線數據」。
    # Yahoo 的 ^TWOII 壞掉、台指期沒有代號，所以改由 FinMind 存進資料湖再從這裡吐給前端。
    # 前端的週／月／季是拿日線再合成的，所以這裡只給日線。
    idx = store.read("index_ohlc")
    out_idx: dict = {}
    if not idx.empty:
        idx = idx.dropna(subset=["date", "symbol", "close"]).sort_values("date")
        for sym, g in idx.groupby("symbol"):
            g = g.drop_duplicates("date", keep="last").tail(1300)
            out_idx[str(sym)] = _clean([
                [str(r.date), _f(r.open), _f(r.high), _f(r.low), _f(r.close), _f(r.volume)]
                for r in g.itertuples(index=False)
            ])
    _write("index_ohlc", out_idx)

    # ---------------------------------------------------------- v3：資金流向 / 題材 / 產業地圖
    try:
        _write("flow_v3", {
            "date": latest,
            "rrg": rrg.rrg(group_hist, price),
            "sankey": rrg.sankey(today, gdetail),
            "share": rrg.share_series(group_hist),
            **flow.period_flows(group_hist),
        })
    except Exception as exc:  # noqa: BLE001
        log.warning("資金流向 v3 產出失敗：%s", exc)
        _write("flow_v3", {"date": latest, "rrg": {"points": []}, "sankey": {"nodes": [], "links": []},
                           "share": {"dates": [], "series": []},
                           "periods": [], "bump": {"weeks": [], "series": []},
                           "bumps": {"week": {"weeks": [], "series": []}, "month": {"weeks": [], "series": []}}})
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
    # 事件側欄要能「選日期看那天發生什麼」，所以留整整一週而不是每類各 40 則
    # （Andy 2026-09-15：「事件需要同步更新今天發生的，但保留前一個禮拜資訊」）。
    # published_at 兩種格式混在一起（鉅亨是 ISO、RSS 是 RFC 2822），
    # 直接拿字串排序會變成照星期幾的英文字母排 —— 一律先 parse 成時間再排。
    news_df = store.read("news")
    if not news_df.empty:
        if "category" not in news_df.columns:
            news_df["category"] = "台股"
        ts = pd.to_datetime(news_df.get("published_at"), errors="coerce", utc=True, format="mixed")
        fallback = pd.to_datetime(news_df.get("date"), errors="coerce", utc=True)
        news_df = news_df.assign(_ts=ts.fillna(fallback))
        news_df = news_df.sort_values("_ts", ascending=False, na_position="last")
        newest = news_df["_ts"].max()
        keep = pd.Series(True, index=news_df.index)
        if pd.notna(newest):
            # 以「最新一則」往回推七天，而不是用執行當下的時間：
            # 抓不到新聞的那幾輪才不會把側欄清空
            keep = news_df["_ts"] >= (newest - pd.Timedelta(days=NEWS_KEEP_DAYS))
        week = news_df[keep]
        # 週內筆數過少（例如剛回補完、或某一類本來就冷門）時，每類至少補到 40 則
        floor = pd.concat([g.head(40) for _, g in news_df.groupby("category")], ignore_index=False)
        recent = (pd.concat([week, floor])
                  .drop_duplicates("news_id")
                  .sort_values("_ts", ascending=False, na_position="last")
                  .drop(columns=["_ts"]))
        # 一週的量是原本每類 40 則的四倍多，而 news.json 每頁都會載入 ——
        # 把前端用不到的欄位（summary 每則最多 600 字、keywords）砍掉，體積才不會跟著翻倍
        cols = [c for c in ("news_id", "category", "date", "published_at",
                            "title", "url", "codes", "source") if c in recent.columns]
        _write("news", recent[cols].to_dict("records"))
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
    _write("meta", meta_payload(latest, history_days))


def _provisional_share(date: str | None) -> dict:
    """這一天有多少比例的價量列是 mis 補的暫定值。

    回 `{"is_provisional": bool, "rows": n, "share": 0~1}`。
    沒有 `px_source` 欄位（舊資料）就一律當成官方值。
    """
    empty = {"is_provisional": False, "rows": 0, "share": 0.0}
    if not date:
        return empty
    try:
        px = store.read("price_daily")
    except Exception:  # noqa: BLE001
        return empty
    if px.empty or "px_source" not in px.columns:
        return empty
    day = px[px["date"].astype(str) == str(date)]
    if day.empty:
        return empty
    n = int((day["px_source"] == "mis").sum())
    share = n / len(day)
    return {"is_provisional": share > 0.5, "rows": n, "share": round(share, 3)}


def meta_payload(latest: str, history_days: int) -> dict:
    """網站頂端那條「資料狀態」要用的所有欄位。

    抽成獨立函式是為了讓它可以被測試直接呼叫 —— 這條資訊是 Andy 判斷
    「今天能不能照著這個畫面下單」的依據，不能只靠跑完整條管線才驗得到。

    price_ahead_of_payload：資料湖裡最新的價格日期比前端採用的 data_date 還新，
    代表那天的上市資料沒到齊（2026-09-11 就是這樣：上櫃 982 檔、上市 0 檔），
    畫面只好停在前一天 —— 這件事以前完全看不出來。
    """
    last_run: dict = {}
    lr = config.STATE / "last_run.json"
    if lr.exists():
        try:
            last_run = json.loads(lr.read_text())
        except ValueError:
            pass

    tbl = store.table_summary().to_dict("records")
    px_latest = next((t.get("latest") for t in tbl if t.get("table") == "price_daily"), None)
    # 三大法人比價量晚一輪落地（價量 15:30、法人 18:30）。
    # 前端要分得出「法人還沒出」與「法人掛了」，不然每個交易日下午的法人圖看起來都像壞掉。
    inst_latest = next((t.get("latest") for t in tbl if t.get("table") == "inst_daily"), None)

    # 畫面上這一天的價量是不是 mis 補的暫定值（openapi 還沒給官方資料）。
    # 開高低收是準的，但成交量是盤中口徑、不含盤後定價交易，逐檔少 0.5%～15%
    # （sources/mis.py 有實測數字），所以跟成交值有關的東西要標示出來。
    provisional = _provisional_share(latest)

    return {
        "status": "ok",
        "data_date": latest,
        "price_latest": px_latest,
        "inst_date": inst_latest,
        "provisional": provisional,
        "price_ahead_of_payload": bool(px_latest and latest and str(px_latest) > str(latest)),
        "history_days": history_days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "last_run_at": last_run.get("finished_at") or last_run.get("started_at"),
        "last_run_trade_date": last_run.get("trade_date"),
        # price＝盤後第一輪，只抓價量（法人、融資券、財報那時還沒出），
        # 前端要講清楚，不然會被誤會成「那些來源掛了」
        "last_run_phase": last_run.get("phase", "full"),
        "groups_health": loader.health(),
        "table_summary": tbl,
        "last_run_errors": last_run.get("errors", []),
        "last_run_empty": last_run.get("empty", []),
    }


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
               latest: str, limit: int = INTRADAY_LIMIT, *, names: dict | None = None,
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
    # 沒有題材族群的股票用法定產業別歸戶（ind_*，與 flow._attach_groups 同一套命名），
    # 這樣全市場每一檔都連得到一個族群頁
    if company is not None and not company.empty and "industry" in company.columns:
        for c_, ind_ in zip(company["code"], company["industry"]):
            if c_ in group_of:
                continue
            ind_ = norm_industry(ind_)
            group_of[c_] = {"group_id": "ind_" + ind_, "group_name": ind_, "groups": [ind_]}

    day = price[price["date"] == latest]
    # 分 K 逐檔跟 Yahoo 要，成本高：族群成分股全部給，再用成交值補到 limit。
    # 其餘股票只有日線以上（指數列如 TAIEX 與權證不算個股）。
    member_codes = set(m["code"])
    by_turnover = [c for c in day.sort_values("turnover", ascending=False)["code"].tolist()
                   if is_tradable_security(c)]
    intraday_codes = [c for c in by_turnover if c in member_codes]
    for c in by_turnover:
        if len(intraday_codes) >= limit:
            break
        if c not in intraday_codes:
            intraday_codes.append(c)
    intraday_set = set(intraday_codes)
    # 個股頁做「全部」股票：有足夠日線的算完整指標與評分，其餘在最後補簡版頁。
    # 名單取自整個資料湖而不是只有今天 —— 今天停牌或沒成交（例如 6806）也要有頁面，
    # 不然搜尋得到卻點不進去，就是 Andy 回報的「不在範圍內就不顯示」。
    bar_count = price.groupby("code").size()
    codes = [c for c in by_turnover if int(bar_count.get(c, 0)) >= MIN_PAGE_BARS]
    seen = set(codes)
    for c in sorted(bar_count.index):
        if c in seen or not is_tradable_security(c) or int(bar_count[c]) < MIN_PAGE_BARS:
            continue
        codes.append(c); seen.add(c)

    hist = price[price["code"].isin(codes)].sort_values(["code", "date"])
    val_today = valuation[valuation["date"] == latest] if not valuation.empty else pd.DataFrame()
    inst_hist = inst[inst["code"].isin(codes)] if not inst.empty else pd.DataFrame()
    inst_today = inst_hist[inst_hist["date"] == latest] if not inst_hist.empty else pd.DataFrame()
    news_by_code: dict[str, list] = {}
    if news_df is not None and not news_df.empty:
        for _, n in news_df.sort_values("published_at", ascending=False).iterrows():
            for c in str(n.get("codes") or "").split(","):
                if c and len(news_by_code.setdefault(c, [])) < 8:
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

    # ★ 分 K 一律**只讀資料湖、不打 Yahoo**（DECISIONS #155 / #156）。
    #
    #   以前這裡是 yahoo.intraday(..., "730d") + yahoo.intraday(..., "60d")，
    #   每一次部署都從零重抓 400 檔 —— 昨天抓過的今天再抓一次，改一行 CSS 也照抓。
    #   實測部署 14 分鐘裡有 13 分 43 秒卡在這兩行（Actions run #16／#17 的逐步秒數）。
    #   現在 60 分 K 由 run_daily 盤後增量寫進資料湖，這裡只要讀。
    #   15 分 K 不再預先產出：Andy 2026-09-18「1 5 15 分 K 都限制當天即可」，
    #   改由前端開個股時即時抓（livek.js 的 1 分 K 已經是這條路）。
    m60 = m15 = pd.DataFrame()
    if not os.environ.get("SKIP_INTRADAY"):
        try:
            m60 = store.read("intraday_60m")
            if not m60.empty:
                m60 = m60[m60["code"].astype(str).isin(set(intraday_codes))]
            log.info("分 K：從資料湖讀到 60 分 %d 列 / %d 檔",
                     len(m60), 0 if m60.empty else m60["code"].nunique())
        except Exception as exc:  # noqa: BLE001
            log.warning("分 K 抓取失敗：%s", exc)
    m60_by = {c: g for c, g in m60.groupby("code")} if not m60.empty else {}
    m15_by = {c: g for c, g in m15.groupby("code")} if not m15.empty else {}

    rows = []
    breadth = {"n": 0, "above_ma20": 0, "above_ma60": 0, "new_high_60": 0, "grade_a": 0, "grade_b": 0}
    _ma_by_group: dict[str, dict] = {}
    _new_high: list[str] = []
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
        # 每個統計都順手記下「是哪幾檔」，總覽上方的數字才點得開（Andy：漲跌停要能對應哪些股票）
        _gi = group_of.get(code, {})
        _gid = _gi.get("group_id") or "—"
        _bucket = _ma_by_group.setdefault(_gid, {"group_id": _gid, "group_name": _gi.get("group_name") or "—",
                                                 "n": 0, "above20": 0, "above60": 0})
        _bucket["n"] += 1
        if pd.notna(last.get("ma20")) and last["close"] > last["ma20"]:
            breadth["above_ma20"] += 1
            _bucket["above20"] += 1
        if pd.notna(last.get("ma60")) and last["close"] > last["ma60"]:
            breadth["above_ma60"] += 1
            _bucket["above60"] += 1
        if last["close"] >= ind["high"].tail(60).max():
            breadth["new_high_60"] += 1
            _new_high.append(code)
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
        # 四個面向的分數與「為何選它」—— 綜合／籌碼／技術／基本面各自可排序、可篩選
        inst_code = (inst_hist[inst_hist["code"] == code].sort_values("date").tail(60)
                     if not inst_hist.empty else None)
        row.update(_clean(scoring.evaluate(
            last=last, ind=ind, verdict=verdict, base_tech=tech,
            inst=inst_code, holders=sh_by_code.get(code),
            broker=broker_by_code.get(code), fx=fx, avg_turnover=avg_turnover)))
        rows.append(row)

        # ---------------- 個股頁
        tail = ind.tail(250)
        full = code in intraday_set
        long = ind.tail(FULL_PAGE_BARS if full else SLIM_PAGE_BARS)   # 前端自己合成週 K / 月 K
        bars60 = m60_by.get(code, pd.DataFrame())
        bars15 = m15_by.get(code, pd.DataFrame())
        try:
            mtf_res = mtf.build(g[cols], bars60 if not bars60.empty else None,
                                bars15 if not bars15.empty else None)
        except Exception as exc:  # noqa: BLE001
            log.debug("%s 多週期分析失敗：%s", code, exc)
            mtf_res = {"tf": {}, "summary": {}}

        def _bars(df_, tcol):
            if df_ is None or df_.empty:
                return []
            return _clean([[str(r_[tcol]), r_["open"], r_["high"], r_["low"], r_["close"],
                            (r_["volume"] if "volume" in df_ else None)] for _, r_ in df_.iterrows()])

        page = {
            "meta": dict({k: row[k] for k in ("code", "name", "market", "group", "group_id", "groups")},
                         tier="full" if full else "daily"),
            "as_of": latest,
            "version": 3,
            "daily": _bars(long, "date"),
            # 60 分給滿 730 天（每天約 5 根 → 約 2,500 根）。
            # 240 分改由前端從 60 分合成、15 分開個股時即時抓，都不再預先產出
            # —— 這兩塊本來佔了每個個股頁 1,900 根 K 棒（DECISIONS #156）。
            "intraday": {"60m": _bars(bars60.tail(2600), "ts")},
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

    # ---------------- 其餘股票：簡版個股頁（歷史還沒回補完，但一樣要點得進去）
    written = {r["code"] for r in rows}
    dates = sorted(price["date"].astype(str).unique())
    prev_date = dates[-2] if len(dates) > 1 else latest
    prev_close = (price[price["date"].astype(str) == prev_date]
                  .drop_duplicates("code").set_index("code")["close"])
    day_one = day.drop_duplicates("code").set_index("code")
    val_one = val_today.drop_duplicates("code").set_index("code") if not val_today.empty else pd.DataFrame()
    inst_one = inst_today.drop_duplicates("code").set_index("code") if not inst_today.empty else pd.DataFrame()

    def _cell(idx: pd.DataFrame, code: str, col: str):
        if idx is None or idx.empty or code not in idx.index or col not in idx.columns:
            return None
        return _clean(idx.at[code, col])

    def _chg(code: str, close):
        p0 = prev_close.get(code)
        if close is None or p0 is None or pd.isna(p0) or not p0:
            return None
        return _clean(float(close) / float(p0) * 100 - 100)

    has = {}
    for k in ("revenue", "financial", "margin", "shareholding", "dividend_events", "dividend_results"):
        d_ = deep.get(k)
        has[k] = set(d_["code"]) if isinstance(d_, pd.DataFrame) and not d_.empty and "code" in d_ else set()

    # 簡版頁同樣走整個資料湖：今天沒成交也要有頁
    thin_codes = [c for c in by_turnover if c not in written]
    seen_thin = set(thin_codes) | written
    for c in sorted(bar_count.index):
        if c not in seen_thin and is_tradable_security(c):
            thin_codes.append(c); seen_thin.add(c)
    thin_px = (price[price["code"].isin(thin_codes)].sort_values(["code", "date"])
               if thin_codes else pd.DataFrame())
    thin_by = {c: g for c, g in thin_px.groupby("code")} if not thin_px.empty else {}
    for code in thin_codes:
        g = thin_by.get(code)
        close = _cell(day_one, code, "close")
        gi = group_of.get(code, {})
        meta = {"code": code, "name": names.get(code) or code, "market": markets.get(code),
                "group": gi.get("group_name") or "—", "group_id": gi.get("group_id"),
                "groups": gi.get("groups", []), "tier": "thin"}
        bars = []
        if g is not None and not g.empty:
            cols_ = [c_ for c_ in ("date", "open", "high", "low", "close", "volume") if c_ in g]
            bars = _clean([[r_[c_] for c_ in cols_] + ([None] if "volume" not in cols_ else [])
                           for _, r_ in g.iterrows()])
        if close is None and bars:      # 今天停牌／沒成交：退回最後一根日線的收盤
            close = bars[-1][4]
        page = {
            "meta": meta, "as_of": latest, "version": 3,
            "daily": bars, "intraday": {}, "mtf": {"tf": {}, "summary": {}},
            "marks": {}, "verdict": {"verdict": "資料回補中", "grade": None, "reasons": []},
            "summary": {**{k: meta[k] for k in ("code", "name", "market", "group", "group_id", "groups")},
                        "close": close, "chg_pct": _chg(code, close),
                        "turnover": _cell(day_one, code, "turnover"),
                        "pe": _cell(val_one, code, "pe"),
                        "trust_net": _cell(inst_one, code, "trust"),
                        "foreign_net": _cell(inst_one, code, "foreign_total"),
                        "tech_score": None, "verdict": "資料回補中", "grade": None},
            "basics": _clean(stockpage.basics(deep.get("company"), code)),
            "revenue": _clean(stockpage.revenue_series(deep.get("revenue"), code)) if code in has["revenue"] else {},
            "profit": _clean(stockpage.profit_series(deep.get("financial"), code)) if code in has["financial"] else {},
            "pe_history": [],
            "dividends": _clean(stockpage.dividends(deep.get("dividend_events"), deep.get("dividend_results"),
                                                    price, code, float(close) if close else None))
                         if code in has["dividend_events"] or code in has["dividend_results"] else {},
            "margin": _clean(stockpage.margin_series(deep.get("margin"), code)) if code in has["margin"] else [],
            "holders": _clean(stockpage.holder_series(deep.get("shareholding"), code)) if code in has["shareholding"] else [],
            "inst_v3": {}, "inst": [], "shareholding": _clean(sh_by_code.get(code, [])),
            "fundamental": fund_idx.get(code),
            "news": news_by_code.get(code, []), "broker_views": broker_by_code.get(code, [])[:6],
            "note": f"歷史價量還在回補（目前只有 {len(bars)} 個交易日），技術面與多週期判讀等資料補齊後才會出現。",
        }
        (stock_dir / f"{code}.json").write_text(json.dumps(_clean(page), ensure_ascii=False), encoding="utf-8")

    # ---------------- 全市場索引：搜尋與各頁連結都靠這份（每一檔都有頁）
    row_idx = {r["code"]: r for r in rows}
    index_codes = list(by_turnover)
    seen_idx = set(index_codes)
    for c in sorted(bar_count.index):   # 今天沒成交的也要在索引裡，搜尋才找得到
        if c not in seen_idx and is_tradable_security(c):
            index_codes.append(c); seen_idx.add(c)
    index = []
    for code in index_codes:
        r = row_idx.get(code)
        gi = group_of.get(code, {})
        close = r["close"] if r else _cell(day_one, code, "close")
        index.append({
            "code": code, "name": names.get(code) or (r["name"] if r else code),
            "market": markets.get(code), "group": gi.get("group_name"), "group_id": gi.get("group_id"),
            "close": close, "chg_pct": r["chg_pct"] if r else _chg(code, close),
            "turnover": r["turnover"] if r else _cell(day_one, code, "turnover"),
            "pe": r["pe"] if r else _cell(val_one, code, "pe"),
            "grade": r["grade"] if r else None,
            "tier": ("full" if code in intraday_set else "daily") if r else "thin",
        })
    _write("stocks", index)
    log.info("個股頁：完整 %d 檔（分 K %d 檔）、簡版 %d 檔",
             len(rows), len(intraday_set & written), len(thin_codes))

    rows.sort(key=lambda r: (r["grade"] or "Z", -(r.get("score_all") or r["tech_score"])))
    if breadth["n"]:
        breadth["pct_above_ma20"] = round(breadth["above_ma20"] / breadth["n"] * 100, 1)
        breadth["pct_above_ma60"] = round(breadth["above_ma60"] / breadth["n"] * 100, 1)
    # 站上均線的比例要能拆到族群，不然「56% 站上 MA20」這個數字看完不知道要幹嘛
    bg = [b for b in _ma_by_group.values() if b["n"] >= 3]
    for b in bg:
        b["pct20"] = round(b["above20"] / b["n"] * 100, 1)
        b["pct60"] = round(b["above60"] / b["n"] * 100, 1)
    breadth["by_group"] = sorted(bg, key=lambda b: (-b["pct20"], -b["n"]))
    breadth["movers"] = movers(day, group_of, names, _new_high)
    log.info("個股頁：%d 檔，A 級 %d、B 級 %d", len(rows), breadth["grade_a"], breadth["grade_b"])
    return rows, breadth


# 漲停幅度：台股是 ±10%，但成交價要照檔位跳，實際常落在 9.7~10.0 之間，
# 用 9.5 當門檻比硬比 10% 準（硬比會漏掉一堆真的漲停）。
LIMIT_PCT = 9.5
MOVER_TOP = 60


def movers(day: pd.DataFrame, group_of: dict, names: dict, new_high: list[str]) -> dict:
    """今天漲的、跌的、漲停的、跌停的、創新高的分別是哪幾檔。

    總覽上方那排數字（漲/跌家數、站上均線…）要點得開才有用 ——
    只看到「567 / 1545」沒辦法做任何事，看到是哪些股票才能往下查。
    """
    if day is None or day.empty:
        return {}
    d = day.copy()
    d["close"] = pd.to_numeric(d["close"], errors="coerce")
    d["change"] = pd.to_numeric(d.get("change"), errors="coerce")
    d["turnover"] = pd.to_numeric(d["turnover"], errors="coerce").fillna(0)
    prev = d["close"] - d["change"].fillna(0)
    d["chg_pct"] = np.where(prev > 0, d["change"] / prev * 100, np.nan)
    d = d[d["code"].map(is_tradable_security) & d["chg_pct"].notna()]

    def _rows(sub: pd.DataFrame, n: int = MOVER_TOP) -> list[dict]:
        out = []
        for _, r in sub.head(n).iterrows():
            gi = group_of.get(r["code"], {})
            out.append({"code": r["code"], "name": names.get(r["code"], r["code"]),
                        "close": round(float(r["close"]), 2), "chg_pct": round(float(r["chg_pct"]), 2),
                        "turnover": float(r["turnover"]),
                        "group_id": gi.get("group_id"), "group_name": gi.get("group_name")})
        return out

    up = d[d["chg_pct"] > 0].sort_values("chg_pct", ascending=False)
    down = d[d["chg_pct"] < 0].sort_values("chg_pct")
    flat = d[d["chg_pct"] == 0]
    lu = up[up["chg_pct"] >= LIMIT_PCT]
    ld = down[down["chg_pct"] <= -LIMIT_PCT]
    nh = d[d["code"].isin(new_high)].sort_values("turnover", ascending=False)
    return {
        "counts": {"up": int(len(up)), "down": int(len(down)), "flat": int(len(flat)),
                   "limit_up": int(len(lu)), "limit_down": int(len(ld)), "new_high": int(len(new_high))},
        "limit_up": _rows(lu), "limit_down": _rows(ld),
        "up": _rows(up), "down": _rows(down),
        "turnover": _rows(d.sort_values("turnover", ascending=False)),
        "new_high": _rows(nh),
    }


def shortlist(rows: list[dict], per_facet: int = CAND_PER_FACET) -> list[dict]:
    """candidates.json 只放前端排得上號的那些，而不是全市場。

    回補跑完後有評分的股票會到兩千檔以上，整包丟給瀏覽器就是好幾 MB。
    但也不能只照綜合分砍 —— 籌碼特別強、綜合普通的那種正是 Andy 要能篩出來的。
    所以四個面向各取前 N 名再取聯集，A/B 級一律保留。
    """
    keep: dict[str, dict] = {}
    for r in rows:
        if r.get("grade") in ("A", "B"):
            keep[r["code"]] = r
    for key in ("score_all", "score_chip", "score_tech", "score_fund"):
        ranked = sorted((r for r in rows if r.get(key) is not None),
                        key=lambda r: -r[key])[:per_facet]
        for r in ranked:
            keep[r["code"]] = r
    out = list(keep.values())
    out.sort(key=lambda r: (r["grade"] or "Z", -(r.get("score_all") or 0)))
    return out


def group_detail(price: pd.DataFrame, company: pd.DataFrame, inst: pd.DataFrame,
                 latest: str, cand_rows: list[dict], names: dict,
                 markets: dict | None = None) -> dict:
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
                # 市場別要寫進來，前端「上市／上櫃」切換才過濾得掉（Andy 2026-09-12 回報）
                "market": (markets or {}).get(c) or (r.get("market") if isinstance(r.get("market"), str) else None),
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
