"""把資料湖算成前端要的 JSON。

前端只負責畫圖，所有運算都在這裡做完 —— 這樣手機開也是秒開，
而且圖表跟數字永遠一致（不會前端算一套、後端算一套）。
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import config, delivery_log, indicators
from .compute import analysis, flow, fundamental, mtf, rrg, scoring, season, stockpage, technical, themes
from .groups import loader
# TechNews 的分類在讀取端重跑（見下面 news_df 那一段的註解），所以要 import 抓取層的分類器
from .sources import news as news_src
from .sources import logos as logos_src
from .util import store
from .util.roc import is_common_stock, is_tradable_security, limit_down_price, limit_up_price, norm_industry

log = logging.getLogger(__name__)


class _Lap:
    """每個階段花幾秒，直接印進 Actions 的 log。

    為什麼要這個：2026-09-18 為了找部署為什麼要 14 分鐘，先是**猜**上傳那步慢（錯的，它只花 5 秒），
    然後拿大型股取樣去推估全市場（也是錯的，全市場七成是小型股，便宜得多）。
    兩次都白花時間。有了這幾行，下次打開 Actions 的 log 就直接看得到答案，不用再猜。
    """

    def __init__(self):
        self.t0 = self.last = time.time()
        self.rows: list[tuple[str, float]] = []

    def __call__(self, name: str) -> None:
        now = time.time()
        self.rows.append((name, now - self.last))
        log.info("⏱ %-22s %6.1fs（累計 %6.1fs）", name, now - self.last, now - self.t0)
        self.last = now

    def report(self) -> None:
        total = time.time() - self.t0
        log.info("⏱ ===== build() 合計 %.1fs =====", total)
        for name, sec in sorted(self.rows, key=lambda r: -r[1])[:8]:
            log.info("⏱   %-22s %6.1fs（%4.1f%%）", name, sec, sec / max(total, 1e-9) * 100)

# 個股頁分層（決策見 DECISIONS #52）：每一檔上市櫃股票都要有頁面，差別只在資料多寡。
MIN_PAGE_BARS = 60        # 有這麼多日線才算得出指標、SMC 與評分
CAND_PER_FACET = 300      # candidates.json 每個面向各留這麼多檔（取聯集）
FULL_PAGE_BARS = 1500     # 有分 K 的那一批給 6 年日線（週／月線在前端合成）
SLIM_PAGE_BARS = 1250     # 其餘有歷史的股票也要 5 年（Andy 2026-09-18：「日 K 這種需要有至少 5 年」）
                          # 以前是 1000（約 4 年），只有前 400 檔達標，其餘不符規格
# 「日線給 6 年（FULL_PAGE_BARS）」那一批有幾檔：族群成分股一定有，其餘照成交值往下補到這個數。
# ★ 2026-09-30：這個數字**不再決定誰有分 K** —— 60 分 K 擴到全市場（pipeline/intraday60.py），
#   有沒有 1H／4H 只看資料湖裡有沒有這一檔的 60 分 K（meta.m60）。這裡只剩「日線給多長」的用途，
#   刻意不跟著擴大：全市場都給 6 年日線，個股頁每檔多 250 根，網站多約 20MB，換不到什麼。
INTRADAY_LIMIT = 400
# 60 分 K 給前端幾根（約 520 個交易日 ≈ 兩年，DECISIONS #156「60 分給滿 730 天」）。多週期分析也用同一段。
M60_PAGE_BARS = 2600
# 60 分 K 只讀資料湖最近幾個月分割（每月一個）：2,600 根 ≈ 25 個月，多讀兩個月當緩衝。
# 全表是三年多、全市場好幾百萬列，全讀只是浪費記憶體。
M60_READ_MONTHS = 27
# 事件側欄保留幾天（日期下拉選單就是拿這一段的日期去產生的）
NEWS_KEEP_DAYS = 7


def _f(v):
    """數字欄位轉 float；NaN／None 一律變 None（JSON 不吃 NaN）。"""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else round(f, 4)


def _minute_money_by_day(lake) -> dict:
    """資料湖 index_intraday 裡 FinMind 真實 1 分 K 的每日成交金額加總（元）：{(symbol, 'YYYY-MM-DD'): 元}。
    只用 src=finmind（整天 270 根、累計差分，加總＝官方當日成交金額）；mis 可能缺頭缺尾，不拿來補日線。"""
    try:
        if lake is None or lake.empty or "src" not in lake.columns:
            return {}
        fm = lake[(lake["src"].astype(str) == "finmind") & (lake["interval"].astype(str) == "1m")]
        if fm.empty:
            return {}
        day = fm["ts"].astype(str).str[:10]
        tot = pd.to_numeric(fm["volume"], errors="coerce").fillna(0).groupby([fm["symbol"].astype(str), day]).sum()
        return {k: float(v) * 1000.0 for k, v in tot.items() if v > 0}   # 湖存千元 → 元
    except Exception as exc:  # noqa: BLE001 —— 補不了就照實給 0
        log.warning("分鐘成交金額加總失敗：%s", exc)
        return {}


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


RRG_LITE_KEYS = ("date", "rrg", "sankey")


def rrg_lite(flow_v3: dict) -> dict:
    """flow_v3 裡總覽首屏用得到的三欄（date／rrg／sankey），原封不動拷貝。

    2026-10-04 首頁瘦身：flow_v3 約 1MB，九成是資金流向頁才用的 inst_daily／share_daily／periods。
    總覽的資金輪盤、摘要卡（含盤中續算的 live_state／live_params）只讀這三欄，所以另存一份小檔。
    **不重算、不刪欄位**：同一次計算的同一個物件，口徑跟 flow_v3 一模一樣（有 pytest 釘著）。"""
    return {k: flow_v3.get(k) for k in RRG_LITE_KEYS if k in flow_v3}


def _write(name: str, payload) -> None:
    path = config.SITE_DATA / f"{name}.json"
    path.write_text(json.dumps(_clean(payload), ensure_ascii=False), encoding="utf-8")
    log.info("寫出 %s（%.1f KB）", path.name, path.stat().st_size / 1024)


def export_logos() -> dict:
    """把資料湖的公司 Logo 複製到 site/data/logos/，並寫 site/data/logos.json（{代號: 相對路徑}）。

    - 只列「真的有圖」的代號：狀態 ok、檔案存在、不是預設圖（見 sources/logos.usable_codes）。
      前端查不到代號就退回字母頭像，所以這裡**寧缺勿濫**。
    - 只讀資料湖、不抓網路（DECISIONS #155：build_payload 對湖裡的東西只准讀）。
    - 每次先把舊的 site/data/logos/ 整個清掉再複製：本機 site/data 不會被清空，
      Pages 快取命中時也會沿用舊目錄 —— 不清的話，被判成預設圖或整批關掉的 Logo 會一直掛在網站上。
    - `config.LOGOS_ENABLED` 關掉 → 輸出空的 `{}`、不複製任何圖（整批關閉的開關，見 docs/logo_sources.md）。
    - 本機一張 Logo 都沒有時輸出 `{}`，不報錯。
    """
    out_dir = config.SITE_DATA / "logos"
    shutil.rmtree(out_dir, ignore_errors=True)
    mapping: dict[str, str] = {}
    if config.LOGOS_ENABLED:
        try:
            usable = logos_src.usable_codes(logos_src.read_index())
        except Exception as exc:  # noqa: BLE001 —— Logo 是裝飾，壞了不能拖垮整份 payload
            log.warning("Logo 索引讀取失敗，這次不輸出 Logo：%s", exc)
            usable = {}
        if usable:
            out_dir.mkdir(parents=True, exist_ok=True)
        for code, fname in sorted(usable.items()):
            try:
                shutil.copyfile(logos_src.logo_dir() / fname, out_dir / fname)
            except OSError as exc:
                log.warning("Logo %s 複製失敗：%s", code, exc)
                continue
            mapping[code] = f"data/logos/{fname}"
    else:
        log.info("LOGOS_ENABLED 關閉：logos.json 輸出空物件，前端全部退回字母頭像")
    _write("logos", mapping)
    return mapping


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
    lap = _Lap()
    price = store.read("price_daily")
    if price.empty:
        log.warning("資料湖還沒有行情資料，只產出空的 meta")
        _write("meta", {"status": "empty", "generated_at":
                        datetime.now(timezone.utc).isoformat()})
        export_logos()
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

    # ★ 2026-09-25 R5（除權息沒還原）：資料湖保留真實成交價（只增不改），還原全部在這裡做。
    #   price        原始價（去掉收盤 0 的列）→ 報價顯示、漲跌、資金流向（它們用官方「漲跌」，本來就對參考價）
    #   price_adj    總報酬還原 → K 線、均線、技術判讀、站上均線比例、個股月季節性
    #   price_share  只還原股數 → 族群季節性（基準也是同一份價格的等權報酬，不改變既有口徑）
    #   shares       股數事件表 → EPS／BPS／股本／現金股利換算到今天的股本（本益比、殖利率）
    price = fundamental.clean_price(price)
    div_events = store.read("dividend_events")
    div_results = store.read("dividend_results")
    actions = fundamental.corporate_actions(price, div_results, div_events)
    actions = actions[actions["date"].astype(str) <= latest] if not actions.empty else actions
    shares = fundamental.share_table(actions)
    price_adj = fundamental.adjust_prices(price, actions, mode="total")
    price_share = fundamental.adjust_prices(price, actions, mode="share")
    if not actions.empty:
        log.info("股本事件：%d 筆（官方 %d、推估 %d）", len(actions),
                 int((actions["source"] == "dividend_results").sum()),
                 int((actions["source"] != "dividend_results").sum()))

    lap("讀資料湖")

    # ---------------------------------------------------------- M1 資金面
    group_hist = flow.group_daily(price, company, inst, margin)
    today = (group_hist[group_hist["date"] == latest]
             if not group_hist.empty else pd.DataFrame())

    _write("groups_today", today.to_dict("records"))
    _write("rotation", flow.rotation_radar(group_hist).head(25).to_dict("records"))
    # 120 → 400 天（Andy 2026-09-18：均線要能到 240 日，只留 120 天算不出來）。
    # 每一列現在還帶著當天的前 10 大族群（點某一天時旁邊直接列得出來）。
    _write("concentration", flow.concentration(group_hist).tail(400).to_dict("records"))
    # 站上均線的歷史（圖16）：七條均線 × 逐日比例，獨立檔，只有那一頁會載
    try:
        _write("ma_breadth", flow.ma_breadth_history(price_adj, loader.membership(), 250))
    except Exception as exc:  # noqa: BLE001
        log.warning("站上均線歷史產出失敗：%s", exc)
        _write("ma_breadth", {"dates": [], "mas": [], "series": {}})
    # 集中度圖點到某一天 → 那天前 10 大族群各自的前 5 檔（第三層，獨立檔案不進 flow_v3）
    try:
        _write("concentration_members",
               flow.concentration_members(group_hist, price, loader.membership(), 400))
    except Exception as exc:  # noqa: BLE001
        log.warning("集中度成分股產出失敗：%s", exc)
        _write("concentration_members", {})
    _write("relative_strength",
           flow.relative_strength(group_hist, market).to_dict("records"))
    # 三種法人各出一份（Andy 2026-09-15：「還要加上外資買超，以及綜合」）。
    # min_days=2 是給前端篩的空間 —— 他要能自己選「連續幾天以上」。
    streaks = {}
    for who in ("trust", "foreign", "total"):
        df_s = flow.trust_streak(inst, min_days=2, who=who)
        streaks[who] = [] if df_s.empty else _clean(df_s.head(60).to_dict("records"))
        # 2026-09-24：連續賣超另存一份（`<法人>_sell`），總覽的四象限要買賣兩半。
        # 鍵名刻意不跟買超混在同一個清單：舊前端只讀 `trust`／`foreign`／`total`，看不到賣超也不會讀錯。
        df_x = flow.trust_streak(inst, min_days=2, who=who, side="sell")
        streaks[who + "_sell"] = [] if df_x.empty else _clean(df_x.head(60).to_dict("records"))
    _write("trust_streak", streaks.get("trust", []))      # 舊鍵留著，換版時不會開天窗
    _write("inst_streak", streaks)

    lap("M1 資金面")

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

    lap("市場體溫")

    # ---------------------------------------------------------- M4 季節性
    _write("seasonality", seasonality(price_share, company).to_dict("records"))
    intl_all = store.read("intl_daily")
    try:
        _write("seasonality_v3", season.build(price_share, intl_all))
    except Exception as exc:  # noqa: BLE001
        log.warning("季節性 v3 產出失敗：%s", exc)
        _write("seasonality_v3", {"periods": {}, "groups": [], "note": str(exc)})

    lap("M4 季節性")

    # ---------------------------------------------------------- M2 基本面
    day_px = price[price["date"] == latest][["code", "close"]]
    ttm_df = fundamental.ttm(financial, shares, latest)
    bal = fundamental.latest_balance(balance, shares, latest)
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

    lap("M2 基本面")

    # ---------------------------------------------------------- 個股技術面 + 個股頁
    news_all = store.read("news")
    sh_all = store.read("shareholding_weekly")
    deep = {
        "revenue": revenue, "financial": financial, "margin": margin, "shareholding": sh_all,
        "dividend_events": div_events,
        "dividend_results": div_results,
        "company": company,
        # ★ 2026-09-19：重大訊息（公司自己公告的）。跟 news（媒體寫的）分開放，
        #   因為 M4 事件面要否決一筆進場，靠的是公告不是報導。
        "material_news": store.read("material_news"),
        # ★ 2026-09-27：籌碼分頁的「當沖」「借券賣」（config.TABLES 的 daytrade_daily／sbl_daily，回補計畫補）
        "daytrade": store.read("daytrade_daily"),
        "sbl": store.read("sbl_daily"),
        # ★ 2026-09-27：董監事持股（每月，sources/mops.insider_holdings）
        "insider": store.read("insider_holding"),
    }
    cand_rows, breadth = candidates(price, valuation, company, inst, latest,
                                    names=names, markets=markets, fund=fund_rows,
                                    news_df=news_all, broker=bv if not bv.empty else None,
                                    shareholding=sh_all, deep=deep,
                                    price_adj=price_adj, shares=shares, actions=actions)
    _write("candidates", shortlist(cand_rows))
    gdetail = group_detail(price, company, inst, latest, cand_rows, names, markets)
    _write("groups_detail", gdetail)
    heat.update({"breadth": breadth})
    _write("market_heat", heat)

    lap("個股頁（全市場）")

    # ---------------------------------------------------------- 大盤三張圖的歷史日 K
    # Andy 2026-09-15：「櫃買 台指期怎麼可能沒有日線數據」。
    # Yahoo 的 ^TWOII 壞掉、台指期沒有代號，所以改由 FinMind 存進資料湖再從這裡吐給前端。
    # 前端的週／月／季是拿日線再合成的，所以這裡只給日線。
    # ★ 2026-09-28：加權、櫃買的「量」一律用**成交金額（元）**（Trading_money → turnover），台指期照舊口數。
    #   為什麼：分 K 的量唯一真實的來源（證交所 mis 分時的 s、FinMind 每 5 秒成交統計）給的都是成交金額，
    #   以前日線用張數、分 K 用金額卻都印成「張」，同一張圖 4 小時（一天一根）跟日 K 差了一個單位。
    #   金額也是台股看大盤量的慣用說法（「成交量 7,366 億」），證交所自己的走勢圖量柱也是金額。
    #   日線成交金額是 0 的日子（加權 2026-02 那 12 天等）若湖裡有那天的真實 1 分 K（FinMind），用分鐘加總補回 ——
    #   那是真實值的加總，不是估算；沒有就照實給 0，前端不畫那根量柱。
    idx = store.read("index_ohlc")
    lake_intra = store.read("index_intraday")
    minute_money = _minute_money_by_day(lake_intra)
    out_idx: dict = {}
    if not idx.empty:
        idx = idx.dropna(subset=["date", "symbol", "close"]).sort_values("date")
        for sym, g in idx.groupby("symbol"):
            g = g.drop_duplicates("date", keep="last").tail(1300)
            money = str(sym) in ("TSE", "OTC") and "turnover" in g.columns
            rows = []
            for r in g.itertuples(index=False):
                v = _f(r.turnover) if money else _f(r.volume)
                if money and not (v and v > 0):
                    v = minute_money.get((str(sym), str(r.date)[:10])) or v
                rows.append([str(r.date), _f(r.open), _f(r.high), _f(r.low), _f(r.close), v])
            out_idx[str(sym)] = _clean(rows)
    _write("index_ohlc", out_idx)

    # 大盤三張圖的 1H／4H（2026-09-25）：資料湖 index_intraday 依台股時段合成，前端只讀、不再即時抓 Yahoo。
    try:
        from .compute import intraday_bars
        _write("index_intraday", intraday_bars.build(lake_intra))
    except Exception as exc:  # noqa: BLE001 —— 這張壞掉不能拖垮整個 build，前端會走退回鏈
        log.warning("index_intraday 合成失敗：%s", exc)
        _write("index_intraday", {})

    # 開頁種子（2026-10-04）：最近一個完整交易日的分時＋昨收，幾 KB，前端第一幀用（大檔背景補）。
    try:
        from .compute import lastday
        _write("index_lastday", lastday.build(lake_intra, out_idx))
    except Exception as exc:  # noqa: BLE001
        log.warning("index_lastday 產出失敗：%s", exc)
        _write("index_lastday", {})

    lap("大盤歷史日K")

    # ---------------------------------------------------------- v3：資金流向 / 題材 / 產業地圖
    try:
        r3 = rrg.rrg(group_hist, price)
        f3 = {
            "date": latest,
            "rrg": r3,
            "sankey": rrg.sankey(today, gdetail),
            "share": rrg.share_series(group_hist),
            # 族群 × 法人的逐日序列：30 → 120 天（Andy 2026-09-18 圖八要「截止日」回放，
            # 只有 30 天的話回放兩下就沒資料了）
            "inst_daily": flow.inst_daily_series(group_hist, 120),
            # 族群成交值佔比的逐日序列（60 天），給圖四資金流向排行的 1–30 天拉 Bar 用。
            # 給 60 天是因為拉到 30 天時比較基準要再往前 30 天（「最近 30 天 vs 前 30 天」）。
            "share_daily": flow.share_daily(group_hist, 60),
            **flow.period_flows(group_hist),
        }
        _write("flow_v3", f3)
        # 總覽輪盤＋摘要卡只用 date／rrg／sankey：另存小檔（約 100KB vs 1MB），前端讀不到才退回 flow_v3。
        _write("rrg_lite", rrg_lite(f3))
        # 資金去向的逐日版（圖六的拉Bar＋播放）。
        # ★ 刻意拆成獨立檔：flow_v3 已經是全站最大的一份，再加 60 天 × 12 族群 × 3 檔，
        #   連只想看總覽的人都得先下載它。這一份只有資金流向頁會去載。
        # ★ 2026-09-20 多傳一個 company：法定產業別的收容桶（ind_*）不在 membership 裡，
        #   不補的話四層樹上「其他產業別」整條底下一檔代表股都沒有（理由見 rrg.sankey_daily）。
        _write("sankey_daily", rrg.sankey_daily(group_hist, price, loader.membership(), 60,
                                                company=company))
        # 個股層級的 RRG（Andy 2026-09-21「點擊族群後可以顯示對應個股，也可以點擊，並顯示在圖上」）。
        # ★ 一樣刻意拆成獨立檔，而且**不進 flow_v3**：那一份是首屏就要載的，
        #   把 36 族群 × 10 檔 × 31 天塞進去，連只想看總覽的人都得先下載它。
        #   前端只有在使用者真的下鑽某個族群時才去 fetch 這一份（lazy load）。
        _write("rrg_members", rrg.member_rrg(price, gdetail, (r3 or {}).get("points") or []))
    except Exception as exc:  # noqa: BLE001
        log.warning("資金流向 v3 產出失敗：%s", exc)
        _write("sankey_daily", {"dates": [], "groups": [], "leaves": {}})
        _write("rrg_members", {})
        _write("rrg_lite", {"date": latest, "rrg": {"points": []}, "sankey": {"nodes": [], "links": []}})
        _write("flow_v3", {"date": latest, "rrg": {"points": []}, "sankey": {"nodes": [], "links": []},
                           "share": {"dates": [], "series": []},
                           "inst_daily": {"dates": [], "groups": []},
                           "share_daily": {"dates": [], "groups": []},
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

    lap("資金流向/題材/產業地圖")

    # ---------------------------------------------------------- 新聞
    # 事件側欄要能「選日期看那天發生什麼」，所以留整整一週而不是每類各 40 則
    # （Andy 2026-09-15：「事件需要同步更新今天發生的，但保留前一個禮拜資訊」）。
    # published_at 兩種格式混在一起（鉅亨是 ISO、RSS 是 RFC 2822），
    # 直接拿字串排序會變成照星期幾的英文字母排 —— 一律先 parse 成時間再排。
    news_df = store.read("news")
    if not news_df.empty:
        if "category" not in news_df.columns:
            news_df["category"] = "台股"
        # ★ 2026-09-21（Andy：「科技新聞請確實篩選跟科技有關的，我發現很多無關的，例如醫療科技等等」）
        #   TechNews 的 RSS 以前被無條件標成「科技」，於是天文／醫療／健康／3C 開箱全進了科技格。
        #   `news.classify_technews()` 現在會重新分類，哪一格都不屬於的標成「其他」。
        #   這裡要把「其他」濾掉 —— 側欄的篩選晶片（#evFilters）只有
        #   台股／科技／總經／券商四顆，「其他」沒有自己的晶片，
        #   **卻還是會出現在「全部」清單裡**，等於篩了跟沒篩一樣。
        #   ★ 濾在這裡而不是在 news.py：資料湖只增不改、原始分類要留著，
        #     哪天判準改了可以重跑；被濾掉的是「這一版判斷不該顯示的」，不是「不存在的」。
        #
        #   ★★ 而且分類是**在這裡重跑一次**，不是只信資料湖裡存的那個值。
        #   原因：TechNews 的 RSS 一次只給最新 20 則，已經躺在湖裡的幾百則舊記錄
        #   永遠不會被重抓，`category` 會一直是舊的「科技」——
        #   使用者重新整理還是看到 CAR-T 掛在科技格，看起來像「修了沒用」。
        #   在讀取端重跑有兩個好處，都比「寫回資料湖」乾淨：
        #     ① 資料湖維持只增不改（CLAUDE.md 的紅線），原始分類完整保留；
        #     ② 判準之後再調，下一次部署就自動套用到全部歷史，不用再補一次資料。
        if "source" in news_df.columns:
            _tn = news_df["source"] == "technews"
            if _tn.any():
                _new = [news_src.classify_technews(t, k) or "其他"
                        for t, k in zip(news_df.loc[_tn, "title"].fillna(""),
                                        news_df.loc[_tn, "keywords"].fillna(""))]
                news_df.loc[_tn, "category"] = _new
                log.info("TechNews 重新分類 %d 則：%s", int(_tn.sum()),
                         pd.Series(_new).value_counts().to_dict())
        news_df = news_df[news_df["category"] != "其他"]
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
        rec = recent[cols].to_dict("records")
        _write("news", rec)
        # 2026-10-04：事件欄的開頁小檔 —— 總件數＋最新 30 則（同一份排序、同樣欄位）。完整版前端背景補。
        _write("news_head", {"total": len(rec), "items": rec[:30]})
    else:
        _write("news", [])
        _write("news_head", {"total": 0, "items": []})

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

    lap("新聞/國際/產業關聯")

    # ---------------------------------------------------------- meta
    # ★ 2026-09-25（R6 審查追補）：**不再產出 tasks.json**。
    #   任務板的內容是內部作業文字（金鑰放哪、token 怎麼換、Actions 怎麼跑），
    #   前端 09-24 已經把 `#tasks` 導到交付清單、不再載入它 —— 但檔案照樣被部署，
    #   `…/data/tasks.json` 直接打得開，等於把內部流程公開在 public 網站上。
    #   交付清單（delivery.json）完全不依賴它（來源是 docs/delivery_log.md），所以整份拿掉，不留欄位。
    #   上一輪殘留的舊檔也要刪掉：本機 site/data 不會被清空，Pages 快取命中時也會沿用舊目錄，
    #   不主動刪的話「管線不寫了」不等於「網站上沒有了」。
    (config.SITE_DATA / "tasks.json").unlink(missing_ok=True)
    # 交付清單（Andy 2026-09-23：「要用什麼方式可以讓你一次就知道我問的問題不會被遺忘，
    # 且如實完成」）。原話逐字放到網站上，他自己就驗得了 —— 不必相信我在對話裡列的清單。
    _write("delivery", delivery_log.build(config.ROOT))
    export_logos()
    _write("meta", meta_payload(latest, history_days))
    lap("meta")
    lap.report()


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


def _m60_lake() -> dict[str, pd.DataFrame]:
    """資料湖的個股 60 分 K，每檔最後 M60_PAGE_BARS 根：{代號: DataFrame(ts, code, open, high, low, close, volume)}。

    只讀最近 M60_READ_MONTHS 個月分割（DECISIONS #155：build_payload 對湖只准讀、不准抓）。失敗回空。"""
    try:
        d = config.DATA / "intraday_60m"
        parts = sorted(p.parent.name.split("=", 1)[1] for p in d.glob("year=*/part.parquet"))
        parts = [int(x) for x in parts[-M60_READ_MONTHS:] if x.isdigit()]
        m60 = store.read("intraday_60m", years=parts) if parts else pd.DataFrame()
    except Exception as exc:  # noqa: BLE001
        log.warning("60 分 K 讀取失敗：%s", exc)
        return {}
    if m60.empty or not {"ts", "code"} <= set(m60.columns):
        return {}
    m60 = (m60.assign(code=m60["code"].astype(str), ts=m60["ts"].astype(str))
              .sort_values(["code", "ts"], kind="stable"))
    out = {c: g.tail(M60_PAGE_BARS).reset_index(drop=True) for c, g in m60.groupby("code", sort=False)}
    log.info("60 分 K：從資料湖讀到 %d 列 / %d 檔（最近 %d 個月分割，每檔最多給 %d 根）",
             len(m60), len(out), len(parts), M60_PAGE_BARS)
    return out


def _num(v, nd: int = 2):
    """價格四捨五入到 nd 位、整數去掉 .0（Yahoo 的價格偶爾帶 float32 尾巴，52.29999923706055 這種）。NaN → None。"""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(f):
        return None
    f = round(f, nd)
    return int(f) if f == int(f) else f


def _m60_payload(code: str, bars: pd.DataFrame, as_of: str) -> dict:
    """個股 60 分 K 的精簡格式（site/data/m60/<代號>.json；前端 industry.js 的 expandM60 還原）。

    {"v":1, "code", "as_of", "tz":"+08:00", "n", "days": [["YYYY-MM-DD", [[HHMM, 開, 高, 低, 收, 量], ...]], ...]}
    為什麼不用個股頁原本的 [ISO 時間字串, 開, 高, 低, 收, 量]：一根 K 棒光時間就佔 27 個字元，
    日期每天重複五次；改成「日期一次＋HHMM 整數」、價格去掉 float 尾巴，每檔大約省一半，
    全市場約 2,000 檔省下一兩百 MB（GitHub Pages 整站上限 1GB）。時間一律台北時間（+08:00）。"""
    days: list = []
    cur = None
    for ts, o, h, lo, c, v in bars[["ts", "open", "high", "low", "close", "volume"]].itertuples(index=False, name=None):
        ts = str(ts)
        d_, hm = ts[:10], int(ts[11:13] + ts[14:16])
        if d_ != cur:
            days.append([d_, []])
            cur = d_
        days[-1][1].append([hm, _num(o), _num(h), _num(lo), _num(c), _num(v, 0)])
    return {"v": 1, "code": code, "as_of": as_of, "tz": "+08:00", "n": int(len(bars)), "days": days}


def candidates(price: pd.DataFrame, valuation: pd.DataFrame,
               company: pd.DataFrame, inst: pd.DataFrame,
               latest: str, limit: int = INTRADAY_LIMIT, *, names: dict | None = None,
               markets: dict | None = None, fund: list[dict] | None = None,
               news_df: pd.DataFrame | None = None, broker: pd.DataFrame | None = None,
               shareholding: pd.DataFrame | None = None,
               deep: dict | None = None, price_adj: pd.DataFrame | None = None,
               shares: dict | None = None,
               actions: pd.DataFrame | None = None) -> tuple[list[dict], dict]:
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
        _indmap = loader.ind_names()      # 迴圈外拿一次；ind_name() 每呼叫一次會重讀 YAML
        for c_, ind_ in zip(company["code"], company["industry"]):
            if c_ in group_of:
                continue
            ind_ = norm_industry(ind_)
            # group_id 維持 `ind_<產業別原名>`（前端的 L.groupByName 與熱力圖下鑽吃它），
            # 只有顯示名改成 tide 的「〇〇・其他」
            _nm = _indmap.get(ind_, ind_)
            group_of[c_] = {"group_id": "ind_" + ind_, "group_name": _nm, "groups": [_nm]}

    day = price[price["date"] == latest]
    # 日線給 6 年的那一批：族群成分股全部給，再用成交值補到 limit（指數列如 TAIEX 與權證不算個股）。
    # ★ 2026-09-30 以前這一批同時決定「誰有分 K」；現在分 K 全市場都有（看 m60_state），這裡只管日線長度。
    member_codes = set(m["code"])
    by_turnover = [c for c in day.sort_values("turnover", ascending=False)["code"].tolist()
                   if is_tradable_security(c)]
    long_codes = [c for c in by_turnover if c in member_codes]
    for c in by_turnover:
        if len(long_codes) >= limit:
            break
        if c not in long_codes:
            long_codes.append(c)
    long_set = set(long_codes)
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

    # K 線／指標／判讀一律吃還原價（price_adj）；本益比歷史與填息天數要原始價（raw_by）。
    # 最新一天還原因子恆為 1，所以 last["close"]、漲跌幅、報價顯示都還是真實價格。
    if price_adj is None:
        price_adj = price
    hist = price_adj[price_adj["code"].isin(codes)].sort_values(["code", "date"])
    raw_by = {c: g_ for c, g_ in price[price["code"].isin(codes)].groupby("code")}
    act_by = ({c: g_ for c, g_ in actions.groupby("code")}
              if actions is not None and not actions.empty else {})
    new_listing = _new_listings(price, latest, company)
    val_today = valuation[valuation["date"] == latest] if not valuation.empty else pd.DataFrame()
    inst_hist = inst[inst["code"].isin(codes)] if not inst.empty else pd.DataFrame()
    inst_today = inst_hist[inst_hist["date"] == latest] if not inst_hist.empty else pd.DataFrame()
    mops_by_code: dict[str, list] = {}
    _mops = (deep or {}).get("material_news")
    if _mops is not None and not _mops.empty:
        _m = _mops.sort_values(["date", "time"], ascending=False)
        for _, n in _m.iterrows():
            c = str(n.get("code") or "")
            if c and len(mops_by_code.setdefault(c, [])) < 6:
                mops_by_code[c].append({
                    "date": n.get("date"), "time": n.get("time"),
                    "subject": n.get("subject"), "clause": n.get("clause"),
                    "occurred": n.get("occurred"), "detail": n.get("detail"),
                })
    news_by_code: dict[str, list] = {}
    if news_df is not None and not news_df.empty:
        # ★ 2026-09-27（Andy：「新聞列表時間要顯示到時分」）：published_at 是 RFC 2822 字串
        #   （"Fri, 11 Sep 2026 00:48:58 +0800"）。以前直接拿字串排序 ＝ 照星期幾的字母排（Fri < Mon < Thu…），
        #   「最新 8 則」其實不是最新的。改成解析成台北時間再排，順手給前端 time（HH:MM）。
        _nd = news_df.copy()
        _ts = pd.to_datetime(_nd["published_at"], errors="coerce", utc=True, format="mixed") \
            if "published_at" in _nd.columns else pd.Series(pd.NaT, index=_nd.index)
        _nd["_ts"] = _ts.dt.tz_convert("Asia/Taipei")
        _nd = _nd.sort_values(["_ts", "date"], ascending=False, na_position="last")
        for _, n in _nd.iterrows():
            t = n.get("_ts")
            for c in str(n.get("codes") or "").split(","):
                if c and len(news_by_code.setdefault(c, [])) < 8:
                    news_by_code[c].append({"date": t.strftime("%Y-%m-%d") if pd.notna(t) else n.get("date"),
                                            "time": t.strftime("%H:%M") if pd.notna(t) else None,
                                            "title": n.get("title"),
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
    # ③ 歷史無限回溯用的分頁檔（個股頁那 1,250～1,500 根再往前的部分）
    hist_dir = config.SITE_DATA / "hist"
    hist_dir.mkdir(parents=True, exist_ok=True)
    hist_stat = {"codes": 0, "files": 0, "bars": 0}
    hist_pages: dict[str, int] = {}        # 代號 → 這一檔有幾段（給前端的目錄檔）

    # ★ 分 K 一律**只讀資料湖、不打 Yahoo**（DECISIONS #155 / #156）。
    #
    #   以前這裡是 yahoo.intraday(..., "730d") + yahoo.intraday(..., "60d")，
    #   每一次部署都從零重抓 400 檔 —— 昨天抓過的今天再抓一次，改一行 CSS 也照抓。
    #   實測部署 14 分鐘裡有 13 分 43 秒卡在這兩行（Actions run #16／#17 的逐步秒數）。
    #   現在 60 分 K 由 run_daily 盤後增量寫進資料湖，這裡只要讀。
    #   15 分 K 不再預先產出：Andy 2026-09-18「1 5 15 分 K 都限制當天即可」，
    #   改由前端開個股時即時抓（livek.js 的 1 分 K 已經是這條路）。
    # ★ 2026-09-30 全市場：不再只讀前 400 檔；而且 60 分 K **不再塞進個股頁**，改寫成每檔一個
    #   `m60/<代號>.json`（精簡格式，見 _m60_payload），前端開個股頁時才載入。
    #   塞在個股頁裡的話，全市場約 2,000 檔 × 每檔約 180KB，網站會多三百多 MB（GitHub Pages 上限 1GB），
    #   而且只看日線的人也要多下載一份用不到的分 K。
    #   SKIP_INTRADAY 只跳過「多週期分析的 1H／4H」（最貴的那段計算），分 K 檔照寫 —— 讀湖＋寫檔很便宜，
    #   本機驗收（SKIP_INTRADAY=1 重算 payload）才驗得到 1H／4H。
    m15 = pd.DataFrame()
    m60_by = _m60_lake()
    try:
        from . import intraday60
        _prog = intraday60.read_progress()
        _names = set(intraday60.universe()[0]) or None     # 湖裡沒有價量時不判「不在名單」
        m60_state = {c: intraday60.state_of(c, len(m60_by.get(c, ())), _prog, _names)
                     for c in set(bar_count.index) | set(m60_by)}
    except Exception as exc:  # noqa: BLE001 —— 狀態只影響個股頁那一句說明，壞了當成「還在回補」
        log.warning("60 分 K 狀態判斷失敗：%s", exc)
        m60_state = {c: ("ok" if len(g) >= 5 else "pending") for c, g in m60_by.items()}
    m60_dir = config.SITE_DATA / "m60"
    shutil.rmtree(m60_dir, ignore_errors=True)   # 不清的話，下市或被判無資料的舊檔會一直掛在網站上
    m60_dir.mkdir(parents=True, exist_ok=True)
    m60_stat = {"files": 0, "bytes": 0}

    def _write_m60(code_: str) -> None:
        if m60_state.get(code_) != "ok":
            return
        path_ = m60_dir / f"{code_}.json"
        path_.write_text(json.dumps(_m60_payload(code_, m60_by[code_], latest), ensure_ascii=False,
                                    separators=(",", ":")), encoding="utf-8")
        m60_stat["files"] += 1
        m60_stat["bytes"] += path_.stat().st_size

    skip_mtf60 = bool(os.environ.get("SKIP_INTRADAY"))
    m15_by = {c: g for c, g in m15.groupby("code")} if not m15.empty else {}

    # ★ 迴圈裡不准再對整張資料湖做 `df[df["code"] == code]`。
    #   2026-09-18 實測：個股頁那一圈跑 2,334 檔，光是這種全表掃描就吃掉一百多秒
    #   （`monthly_seasonality` 一檔 20.8ms＝全市場 48.6 秒，因為 price 有 127 萬列）。
    #   先 groupby 建一次索引（總共約 0.5 秒），迴圈裡就是 dict 查表。
    #   安全性：stockpage 那幾支內部都是 `df[df["code"] == code]`，
    #   餵已經篩過的切片進去等於那一行變成 no-op，結果完全一樣（tests/test_perf_golden.py 釘住）。
    def _by_code(df):
        if df is None or not isinstance(df, pd.DataFrame) or df.empty or "code" not in df.columns:
            return {}
        return {c: g for c, g in df.groupby("code")}

    EMPTY = pd.DataFrame()
    rev_by = _by_code(deep.get("revenue"))
    fin_by = _by_code(deep.get("financial"))
    mgn_by = _by_code(deep.get("margin"))
    shw_by = _by_code(deep.get("shareholding"))
    ins_by = _by_code(deep.get("insider"))
    dve_by = _by_code(deep.get("dividend_events"))
    dvr_by = _by_code(deep.get("dividend_results"))
    com_by = _by_code(deep.get("company"))
    dtr_by = _by_code(deep.get("daytrade"))
    div_cover = dividend_cover_years()
    sbl_by = _by_code(deep.get("sbl"))
    # 資券三個來源全市場最新到哪天（#304）：頁面據此寫「資料源更新到 MM-DD」，不讓空格被當成 0
    mg_asof = stockpage.margin_asof(deep.get("margin"), deep.get("daytrade"), deep.get("sbl"))
    insth_by = _by_code(inst_hist)
    instd_by = _by_code(inst_today)
    valt_by = _by_code(val_today)

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
        # with_checks：多帶 A／B 條件逐條的成立與數字，給個股頁「AI 分析」卡講觀望的原因
        #（判定結果不變；checks 只進 analysis，不重複寫進 page["verdict"]）
        verdict = technical.evaluate(ind, avg_turnover=avg_turnover, with_checks=True)

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
        v = valt_by.get(code)
        if v is not None and not v.empty:
            pe = _clean(v["pe"].iloc[0])
        trust_net = foreign_net = None
        i = instd_by.get(code)
        if i is not None and not i.empty:
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
        _ih = insth_by.get(code)
        inst_code = _ih.sort_values("date").tail(60) if _ih is not None and not _ih.empty else None
        row.update(_clean(scoring.evaluate(
            last=last, ind=ind, verdict=verdict, base_tech=tech,
            inst=inst_code, holders=sh_by_code.get(code),
            broker=broker_by_code.get(code), fx=fx, avg_turnover=avg_turnover)))
        rows.append(row)

        # ---------------- 個股頁
        tail = ind.tail(250)
        long = ind.tail(FULL_PAGE_BARS if code in long_set else SLIM_PAGE_BARS)   # 前端自己合成週 K / 月 K
        st60 = m60_state.get(code, "pending")
        # 多週期分析的 1H／4H 跟前端畫的是同一段（最後 M60_PAGE_BARS 根）
        bars60 = m60_by.get(code, pd.DataFrame()) if st60 == "ok" and not skip_mtf60 else pd.DataFrame()
        bars15 = m15_by.get(code, pd.DataFrame())
        try:
            # daily_ind：日線指標主迴圈上面剛算完，不要讓 mtf 再算一次
            # （mtf 內部每個週期各呼叫一次 compute_all，日線那次完全重複）
            mtf_res = mtf.build(g[cols], bars60 if not bars60.empty else None,
                                bars15 if not bars15.empty else None, daily_ind=ind)
        except Exception as exc:  # noqa: BLE001
            log.debug("%s 多週期分析失敗：%s", code, exc)
            mtf_res = {"tf": {}, "summary": {}}

        def _bars(df_, tcol):
            """K 棒轉成 [時間, 開, 高, 低, 收, 量] 的陣列。

            ★ 不要用 `iterrows()`。2026-09-18 實測：1,500 根日 K 用 iterrows 要 56.8ms，
            改成 `to_numpy().tolist()` 只要 1.6ms —— **35 倍**。
            全市場 2,334 檔換算下來是 133 秒變 4 秒，是這次部署提速最便宜的一塊。
            （iterrows 每一列都要建一個 Series 物件，1,500 根就是 1,500 個。）"""
            if df_ is None or df_.empty:
                return []
            cols_ = [tcol, "open", "high", "low", "close"] + (["volume"] if "volume" in df_ else [])
            rows_ = df_[cols_].to_numpy(dtype=object).tolist()
            for r_ in rows_:
                r_[0] = str(r_[0])
                if len(r_) == 5:
                    r_.append(None)          # 沒有成交量的也要補一格，前端照索引取值
            return _clean(rows_)

        page = {
            # tier：full＝有 60 分 K（1H／4H 看得到）；daily＝只有日線以上。
            # m60：ok／none（確認無資料，冷門股）／pending（還在回補）—— 前端靠它決定要不要載 m60 檔、
            #      沒有時講哪一句話（不要空白）。m60_n：分 K 檔裡有幾根。
            "meta": dict({k: row[k] for k in ("code", "name", "market", "group", "group_id", "groups")},
                         tier="full" if st60 == "ok" else "daily", m60=st60,
                         m60_n=min(len(m60_by.get(code, ())), M60_PAGE_BARS) if st60 == "ok" else 0),
            "as_of": latest,
            "version": 3,
            "daily": _bars(long, "date"),
            # 60 分 K 不在這裡了：每檔獨立一個 m60/<代號>.json（見上面 _write_m60），前端開頁時才載入。
            # 240 分由前端從 60 分合成、15 分開個股時即時抓，都不預先產出（DECISIONS #156）。
            "intraday": {},
            "mtf": _clean(mtf_res),
            # ★ 一律餵「這一檔的切片」，不要餵整張資料湖（見上面 _by_code 的註解）。
            #   g 就是這一檔的完整日線歷史，pe_history / dividends / month_season 要的就是它。
            "revenue": _clean(stockpage.revenue_series(rev_by.get(code, EMPTY), code)),
            "profit": _clean(stockpage.profit_series(fin_by.get(code, EMPTY), code, asof=latest)),
            "pe_history": _clean(stockpage.pe_history(raw_by.get(code, g), fin_by.get(code, EMPTY), code,
                                                      shares=shares, adj_price=g)),
            "dividends": _clean(stockpage.dividends(dve_by.get(code, EMPTY), dvr_by.get(code, EMPTY),
                                                    raw_by.get(code, g), code, float(last["close"]),
                                                    shares=shares, asof=latest, cover_from=div_cover.get(code))),
            # 還原說明：K 線是還原價；這裡列出每一個還原事件（日期、價格因子、配股率、來源），
            # 前端要標示「還原」或對帳時用。source 不是 dividend_results 的是推估值。
            "price_adjust": _adjust_meta(act_by.get(code)),
            "margin": _clean(stockpage.margin_series(mgn_by.get(code, EMPTY), code,
                                                     daytrade=dtr_by.get(code), sbl=sbl_by.get(code),
                                                     price=raw_by.get(code, g))),
            "margin_columns": stockpage.MARGIN_COLUMNS,
            "margin_asof": mg_asof,
            # ★ 2026-09-27「指標」分頁：事實條件標籤（stockpage.stock_tags，不做推介）
            "tags": _clean(stockpage.stock_tags(rev_by.get(code), fin_by.get(code), code)),
            "holders": _clean(stockpage.holder_series(shw_by.get(code, EMPTY), code)),
            "insider": _clean(stockpage.insider_series(ins_by.get(code), shw_by.get(code), code)),
            "inst_v3": _clean(stockpage.inst_series(insth_by.get(code), code)),
            # ★ 2026-09-27「主力」替代口徑（券商分點不爬，CLAUDE.md 第 7 條）：法人合計＋5／20 日集中度
            "main_proxy": _clean(stockpage.main_proxy_series(insth_by.get(code), raw_by.get(code, g), code)),
            "basics": _clean(stockpage.basics(com_by.get(code, EMPTY), code)),
            # C5：1–12 月平均漲幅（最多 15 年）。給逐年的原始數字，前端自己切 1/3/5/自填年數。
            "month_season": _clean(stockpage.monthly_seasonality(g, code, 15)),
            "marks": {
                "bos": _clean(tail[tail["bos"].fillna(False)]["date"].tolist()),
                "choch": _clean([[r_["date"], int(r_["trend"])] for _, r_ in
                                 tail[tail["choch"].fillna(False)].iterrows()]),
                "sweep_low": _clean(tail[tail["sweep_low"].fillna(False)]["date"].tolist()),
                "sweep_high": _clean(tail[tail["sweep_high"].fillna(False)]["date"].tolist()),
                "limit_up": _clean(tail[tail["limit_up"].fillna(False)]["date"].tolist()),
            },
            "verdict": _clean({k_: v_ for k_, v_ in verdict.items() if k_ != "checks"}),
            "summary": row,
            "fundamental": fx or None,
            # inst_code 上面已經切好了（同一份、同樣的排序與 tail(60)），不要再掃一次全表
            "inst": _clean(inst_code[["date", "foreign_total", "trust", "dealer"]].to_dict("records"))
                    if inst_code is not None and not inst_code.empty else [],
            "shareholding": _clean(sh_by_code.get(code, [])),
            "news": news_by_code.get(code, []),
            "material_news": mops_by_code.get(code, []),
            "broker_views": broker_by_code.get(code, [])[:6],
        }
        # 「AI 分析」卡（規則式自動判讀，不是語言模型）：四個面向都用上面剛組好的同一份資料，
        # 不再讀湖、不再抓任何東西。失敗就不給這一欄，前端會顯示「資料不足」而不是整頁壞掉。
        try:
            _vol20 = pd.to_numeric(g["volume"].tail(20), errors="coerce").mean() if "volume" in g else None
            page["analysis"] = _clean(analysis.build(
                verdict=verdict, mtf_res=page["mtf"], inst_v3=page["inst_v3"], margin=page["margin"],
                holders=page["holders"], fundamental=page["fundamental"], revenue=page["revenue"],
                profit=page["profit"], news=page["news"], material_news=page["material_news"],
                as_of=latest, code=code, name=row["name"], avg_vol20=_vol20))
        except Exception as exc:  # noqa: BLE001
            log.debug("%s AI 分析失敗：%s", code, exc)
        # 整頁過一次 _clean：任何漏網的 NaN 都會讓瀏覽器 JSON.parse 直接失敗
        (stock_dir / f"{code}.json").write_text(json.dumps(_clean(page), ensure_ascii=False),
                                                encoding="utf-8")
        _write_m60(code)

        # ---------------- ③ 更舊的日 K（往左拖到頭才載入）
        #
        #   只寫「個股頁那一段之前」的部分 —— 頁面裡已經有的那 1,250～1,500 根不重複寫一次。
        #   ★ 這裡只**讀**已經在記憶體裡的 `ind`，不會再去抓任何東西（CLAUDE.md：
        #     會重複用到的資料一律走資料湖，不准每次部署重抓）。
        #   部署成本：全市場只有 345 檔的歷史超過個股頁那一段，總共約 70 萬根、
        #   切成約 960 個檔案、未壓縮約 32MB；寫檔本身是純 I/O，實測遠小於算指標那一段。
        older = ind.iloc[: max(0, len(ind) - len(long))]
        if len(older):
            chunks = stockpage.history_chunks(_bars(older, "date"))
            if chunks:
                d = hist_dir / code
                d.mkdir(parents=True, exist_ok=True)
                for ch in chunks:
                    (d / f"p{ch['page']}.json").write_text(
                        json.dumps(dict(ch, code=code, tf="1d"), ensure_ascii=False), encoding="utf-8")
                hist_pages[code] = len(chunks)
                hist_stat["codes"] += 1
                hist_stat["files"] += len(chunks)
                hist_stat["bars"] += sum(len(c["bars"]) for c in chunks)

    # 目錄檔：哪幾檔有更舊的歷史、各有幾段。前端第一次要回補時先讀它 ——
    # 沒有這一份的話，對「沒有更舊歷史」的股票（全市場 2,341 檔裡有 1,996 檔）
    # 每拖一次就打一次 404，console 會噴錯（`_preview.py` 的 console.error 關卡會直接抓到）。
    (hist_dir / "index.json").write_text(
        json.dumps({"chunk": stockpage.HIST_CHUNK, "codes": hist_pages}, ensure_ascii=False),
        encoding="utf-8")
    log.info("歷史回溯分頁：%d 檔 / %d 個檔案 / %d 根日 K",
             hist_stat["codes"], hist_stat["files"], hist_stat["bars"])

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
    thin_px = (price_adj[price_adj["code"].isin(thin_codes)].sort_values(["code", "date"])
               if thin_codes else pd.DataFrame())
    thin_by = {c: g for c, g in thin_px.groupby("code")} if not thin_px.empty else {}
    # 當沖比率的分母要原始成交股數（還原價的量不變，但這裡刻意用原始表，口徑跟完整頁同一份）
    thin_raw = ({c: g for c, g in price[price["code"].isin(thin_codes)].groupby("code")} if thin_codes else {})
    for code in thin_codes:
        g = thin_by.get(code)
        close = _cell(day_one, code, "close")
        gi = group_of.get(code, {})
        st60 = m60_state.get(code, "pending")
        meta = {"code": code, "name": names.get(code) or code, "market": markets.get(code),
                "group": gi.get("group_name") or "—", "group_id": gi.get("group_id"),
                "groups": gi.get("groups", []), "tier": "thin", "m60": st60,
                "m60_n": min(len(m60_by.get(code, ())), M60_PAGE_BARS) if st60 == "ok" else 0}
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
            "marks": {}, "verdict": {"verdict": "資料準備中", "grade": None, "reasons": []},
            "summary": {**{k: meta[k] for k in ("code", "name", "market", "group", "group_id", "groups")},
                        "close": close, "chg_pct": _chg(code, close),
                        "turnover": _cell(day_one, code, "turnover"),
                        "pe": _cell(val_one, code, "pe"),
                        "trust_net": _cell(inst_one, code, "trust"),
                        "foreign_net": _cell(inst_one, code, "foreign_total"),
                        "tech_score": None, "verdict": "資料準備中", "grade": None},
            "basics": _clean(stockpage.basics(deep.get("company"), code)),
            "month_season": _clean(stockpage.monthly_seasonality(g if g is not None else EMPTY, code, 15)),
            "revenue": _clean(stockpage.revenue_series(deep.get("revenue"), code)) if code in has["revenue"] else {},
            "profit": _clean(stockpage.profit_series(fin_by.get(code, EMPTY), code, asof=latest)) if code in has["financial"] else {},
            "pe_history": [],
            "dividends": _clean(stockpage.dividends(deep.get("dividend_events"), deep.get("dividend_results"),
                                                    thin_raw.get(code), code, float(close) if close else None,
                                                    shares=shares, asof=latest, cover_from=div_cover.get(code)))
                         if code in has["dividend_events"] or code in has["dividend_results"] else {},
            "margin": _clean(stockpage.margin_series(mgn_by.get(code, EMPTY), code, daytrade=dtr_by.get(code),
                                                     sbl=sbl_by.get(code), price=thin_raw.get(code))),
            "margin_columns": stockpage.MARGIN_COLUMNS,
            "margin_asof": mg_asof,
            "tags": _clean(stockpage.stock_tags(rev_by.get(code), fin_by.get(code), code)),
            "holders": _clean(stockpage.holder_series(shw_by.get(code, EMPTY), code)),
            "insider": _clean(stockpage.insider_series(ins_by.get(code), shw_by.get(code), code)),
            "inst_v3": {}, "inst": [], "shareholding": _clean(sh_by_code.get(code, [])),
            "fundamental": fund_idx.get(code),
            "news": news_by_code.get(code, []), "broker_views": broker_by_code.get(code, [])[:6],
            # ★ 2026-09-19：簡版頁**更需要**重大訊息。這些是冷門股，媒體不會報，
            #   但減資、變更面額、解散、訴訟這些公司自己一定會公告 ——
            #   probe fixture 的第一筆就是冷門股「沛爾生醫」的面額變更。
            #   而且它不依賴價量歷史，所以簡版頁照樣有東西可看，
            #   正好對上「不可以出現沒有資訊的頁面」那條要求。
            "material_news": mops_by_code.get(code, []),
            "note": f"歷史價量資料準備中（目前只有 {len(bars)} 個交易日），技術面與多週期判讀等資料足夠後才會出現。",   # 2026-09-28 讀者語言：不寫「回補」
        }
        (stock_dir / f"{code}.json").write_text(json.dumps(_clean(page), ensure_ascii=False), encoding="utf-8")
        _write_m60(code)       # 日線還不夠 60 根的新股，分 K 可能已經有了（Yahoo 從掛牌第一天就有）

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
            "tier": ("full" if m60_state.get(code) == "ok" else "daily") if r else "thin",
        })
    # ★ 2026-09-26 漲跌家數分上市／上櫃／全部：級距由管線決定（flow.updown_bin，唯一權威），
    # 每列帶 `ud`，前端分組直接讀它；updown.json 是三組家數（all／twse／tpex／other）＋加總檢查。
    # ★ 2026-10-05：每列再帶 `lim`（1 漲停／-1 跌停／沒有就不寫），前端市場明細的漲停分頁與即時模式對照用。
    lim_today = limit_flags(day, new_listing)
    for it in index:
        it["ud"] = flow.updown_bin(it["chg_pct"], LIMIT_PCT)
        if lim_today.get(it["code"]):
            it["lim"] = lim_today[it["code"]]
    _write("stocks", index)
    ud = flow.updown_distribution(index, LIMIT_PCT)
    if not ud["check"]["ok"]:
        # 不可能發生（all 是三組逐列加出來的），真的發生代表程式被改壞 —— 寫 log，不擋整個 payload
        log.warning("漲跌家數分佈加總不一致：%s", ud["check"]["diff"])
    _write("updown", ud)
    # ★ 2026-09-28 搜尋下拉的迷你走勢圖（Andy：「搜尋欄位的對應股票旁需要出現小小的分時走勢圖」）。
    #   範圍＝上面那份全市場索引（搜尋得到的每一檔），來源與口徑見 compute/sparks.py 檔頭。壞掉不擋整個 payload。
    try:
        _write("sparks", _sparks_payload(price_adj, index_codes, latest))
    except Exception as exc:  # noqa: BLE001
        log.warning("sparks 產出失敗：%s", exc)
    _st = pd.Series({c: m60_state.get(c, "pending") for c in index_codes}, dtype=object)
    log.info("個股頁：完整 %d 檔、簡版 %d 檔；60 分 K 有 %d 檔（確認無資料 %d、還在回補 %d），"
             "分 K 檔 %d 個、共 %.1f MB",
             len(rows), len(thin_codes), int((_st == "ok").sum()), int((_st == "none").sum()),
             int((_st == "pending").sum()), m60_stat["files"], m60_stat["bytes"] / 1e6)

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
    breadth["movers"] = movers(day, group_of, names, _new_high, new_listing=new_listing)
    log.info("個股頁：%d 檔，A 級 %d、B 級 %d", len(rows), breadth["grade_a"], breadth["grade_b"])
    return rows, breadth


# 漲停幅度：台股是 ±10%，但成交價要照檔位跳，實際常落在 9.7~10.0 之間，
# 用 9.5 當門檻比硬比 10% 準（硬比會漏掉一堆真的漲停）。
LIMIT_PCT = 9.5
MOVER_TOP = 60
# ★ 2026-10-05：上面 LIMIT_PCT 只剩「漲跌分佈分級」在用（flow.updown_bin 的最兩端那格）；
#   漲停／跌停**名單與家數**改用 limit_flags（價格＝漲停價），見下面。
LIMIT_ABS_MAX = 10.0 + 1e-6      # 有漲跌幅限制的普通股，漲跌幅不可能超過 10%


def limit_flags(day: pd.DataFrame, new_listing: set[str] | None = None) -> dict[str, int]:
    """每一檔今天是否鎖在漲停（1）／跌停（-1）。只回有命中的。

    判定＝收盤價（盤中則為現價）**等於**漲停價／跌停價，漲停價＝昨收×1.1 依升降單位向下取整
    （roc.limit_up_price），昨收＝close − change（官方漲跌，除權息日也對得上參考價）。
    只認普通股（roc.is_common_stock）、排除上市未滿 5 個交易日的新股（沒有漲跌幅限制）。
    前端即時模式用同一套規則（app.js 的 twLimit），兩邊口徑一致。"""
    out: dict[str, int] = {}
    if day is None or day.empty:
        return out
    skip = new_listing or set()
    close = pd.to_numeric(day["close"], errors="coerce")
    change = pd.to_numeric(day.get("change"), errors="coerce")
    for code, c, ch in zip(day["code"].astype(str), close, change):
        if code in skip or not is_common_stock(code) or pd.isna(c) or pd.isna(ch):
            continue
        prev = float(c) - float(ch)
        if prev <= 0 or ch == 0:
            continue
        if ch > 0 and abs(float(c) - limit_up_price(prev)) < 1e-6:
            out[code] = 1
        elif ch < 0 and abs(float(c) - limit_down_price(prev)) < 1e-6:
            out[code] = -1
    return out


DIV_DEEP_START = "2009-01-01"      # run_backfill.PLAN_DEFAULT 的股利深度回補起點（2026-09-27）


def _sparks_payload(price: pd.DataFrame, codes: list[str], latest: str) -> dict:
    """sparks.json：只讀資料湖 intraday_60m 最近兩個月分割（按月分割，讀兩個檔就夠找到最新交易日）。

    ⚠ 不看 SKIP_INTRADAY：那個開關是為了省掉整張 60 分 K（兩年、上百萬列）的讀取與個股頁分 K 的計算，
      這裡只讀最後兩個分割（約 3 萬列、1 秒內），本機預覽也要看得到分時小圖。"""
    from .compute import sparks
    d = config.DATA / "intraday_60m"
    parts = sorted(p.name.split("=", 1)[1] for p in d.glob("year=*")) if d.exists() else []
    m60 = pd.DataFrame()
    if parts:
        m60 = store.read("intraday_60m", years=[int(x) for x in parts[-2:] if x.isdigit()])
    out = sparks.build(price, m60, latest, codes)
    log.info("sparks：分時 %d 檔、日收盤代替 %d 檔、沒有資料 %d 檔",
             out["stat"]["intraday"], out["stat"]["daily"], out["stat"]["none"])
    return out


def dividend_cover_years() -> dict[str, int]:
    """每一檔的股利資料「補到哪一年」：2009 那一步回補過的（進度檔有 divresult@2009-01-01:<代號>）給 2009，
    其他用 stockpage.DIV_COVER_YEAR（2016）。年度股利圖只畫這一年之後 —— 沒補過的年份是「不知道」，不是「沒配」。"""
    try:
        prog = json.loads((config.STATE / "backfill_progress.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    pre = f"divresult@{DIV_DEEP_START}:"
    y = int(DIV_DEEP_START[:4])
    return {k[len(pre):]: y for k, v in (prog.get("done") or {}).items() if v and k.startswith(pre)}


def _adjust_meta(acts: pd.DataFrame | None) -> dict:
    """個股頁的還原說明：K 線是否為還原價、每一個還原事件。"""
    ev = []
    if acts is not None and not acts.empty:
        for r in acts.sort_values("date").itertuples(index=False):
            ev.append([str(r.date), round(float(r.price_factor), 6), round(float(r.share_ratio), 6), r.source])
    return {"method": "還原權值（官方參考價 ÷ 前收盤，往回連乘）", "daily_adjusted": True, "events": ev}


def _new_listings(price: pd.DataFrame, latest: str, company: pd.DataFrame | None) -> set[str]:
    """最新一天仍在上市（櫃）前 5 個交易日內的股票（無漲跌幅限制，不能算進漲跌停）。

    有 listed_date：數「上市日 ≤ 交易日 ≤ latest」的全市場交易日數 ≤ 5。
    沒有 listed_date：數這一檔在資料湖裡的有效 K 棒數 ≤ 5（寧可少算一檔漲停，也不要把新股算進去）。
    """
    if price is None or price.empty:
        return set()
    days = sorted(price["date"].astype(str).unique())
    listed = {}
    if company is not None and not company.empty and "listed_date" in company.columns:
        listed = (company.dropna(subset=["listed_date"]).drop_duplicates("code", keep="last")
                         .set_index("code")["listed_date"].astype(str).to_dict())
    import bisect
    n_all = bisect.bisect_right(days, str(latest))
    bars = price[price["date"].astype(str) <= str(latest)].groupby("code").size()
    today = set(price[price["date"].astype(str) == str(latest)]["code"])
    out = set()
    for code in today:
        ld = listed.get(code)
        if ld and ld[:4].isdigit():
            n = n_all - bisect.bisect_left(days, ld[:10])
        else:
            n = int(bars.get(code, 0))
        if n <= fundamental.NEW_LISTING_DAYS:
            out.add(code)
    return out


def movers(day: pd.DataFrame, group_of: dict, names: dict, new_high: list[str],
           new_listing: set[str] | None = None) -> dict:
    """今天漲的、跌的、漲停的、跌停的、創新高的分別是哪幾檔。

    總覽上方那排數字（漲/跌家數、站上均線…）要點得開才有用 ——
    只看到「567 / 1545」沒辦法做任何事，看到是哪些股票才能往下查。

    ★ 2026-09-25 R5：上市前 5 個交易日沒有漲跌幅限制（7856 首日 +110%），
      那不是「漲停」。new_listing 裡的股票不進漲停／跌停清單與家數（仍算漲跌家數）。
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
    # ★ 2026-10-05 漲跌停改成「收盤價＝漲停價／跌停價」（limit_flags），不再用 ±9.5% 門檻；只認普通股、排除新股。
    lim = limit_flags(d, new_listing)
    lu = up[up["code"].map(lim).eq(1)]
    ld = down[down["code"].map(lim).eq(-1)]
    # 漲幅／跌幅前段：只排普通股、而且 |漲跌幅| ≤ 10%（超過 10% 的一定不是有漲跌幅限制的個股：
    #   槓桿 ETF、新上市前五天……）。Andy：「高過 10% 就不顯示，因為通常不是個股」。
    #   漲跌「家數」（counts.up/down）照舊含 ETF，不改大盤寬度的口徑。
    ok_rank = d["code"].map(is_common_stock) & (d["chg_pct"].abs() <= LIMIT_ABS_MAX)
    up_rank = up[ok_rank.reindex(up.index)]
    down_rank = down[ok_rank.reindex(down.index)]
    nh = d[d["code"].isin(new_high)].sort_values("turnover", ascending=False)
    return {
        "counts": {"up": int(len(up)), "down": int(len(down)), "flat": int(len(flat)),
                   "limit_up": int(len(lu)), "limit_down": int(len(ld)), "new_high": int(len(new_high))},
        "limit_up": _rows(lu), "limit_down": _rows(ld),
        "up": _rows(up_rank), "down": _rows(down_rank),
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
