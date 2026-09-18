"""每日盤後管線。

執行順序刻意固定：先抓不用額度的證交所來源（拿到當日交易日期），
再用那個日期補上沒有日期欄位的融資券，最後才動用 FinMind 的有限額度。

任何一段失敗都只記錄並繼續 —— 一個來源掛掉不該讓整天的資料都沒存到。
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import datetime, timedelta, timezone

import pandas as pd

from . import config
from .compute import flow
from .groups import loader
from .sources import finmind, macro, mis, news, tdcc, tpex, twse
from .util import http, store
from .util.roc import is_tradable_security

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("run_daily")

# empty：抓得到端點但回 0 筆的步驟。以前這種只寫 log，errors 一直是空的，
# 網站上完全看不出來哪個來源掛了（twse.dividend / tdcc.shareholding / macro.fred
# 就這樣靜默失敗很久）。現在分開記，前端可以把它攤在頁面頂端。
RESULT: dict = {"steps": {}, "errors": [], "empty": []}


def step(name: str, fn, *args, **kwargs):
    """跑一個抓取步驟，把結果與錯誤都記進 RESULT，絕不讓例外往上炸。"""
    t0 = time.time()
    try:
        df = fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 — 這裡就是要吃掉所有例外
        log.exception("%s 失敗", name)
        RESULT["errors"].append(f"{name}: {exc}")
        RESULT["steps"][name] = {"ok": False, "rows": 0, "error": str(exc)}
        return pd.DataFrame()

    rows = 0 if df is None or df.empty else len(df)
    RESULT["steps"][name] = {"ok": rows > 0, "rows": rows,
                             "seconds": round(time.time() - t0, 1)}
    if rows == 0:
        log.warning("%s 沒有取得資料", name)
        RESULT["empty"].append(name)          # ← 不再只寫 log
    return df if df is not None else pd.DataFrame()


def save(table: str, df: pd.DataFrame) -> int:
    if df is None or df.empty:
        return 0
    try:
        n = store.append(table, df)
        RESULT["steps"].setdefault(table, {})["stored"] = n
        return n
    except Exception as exc:  # noqa: BLE001
        log.exception("寫入 %s 失敗", table)
        RESULT["errors"].append(f"store:{table}: {exc}")
        return 0


def only_new_keys(table: str, df: pd.DataFrame) -> pd.DataFrame:
    """只留下資料湖裡還沒有這組 key 的列（store.append 是後到覆蓋，這裡反過來讓先到的贏）。"""
    if df is None or df.empty:
        return pd.DataFrame()
    keys = config.TABLES[table]
    try:
        old = store.read(table)
    except Exception:  # noqa: BLE001
        old = pd.DataFrame()
    if old.empty or any(k not in old.columns for k in keys):
        return df
    have = set(map(tuple, old[keys].astype(str).itertuples(index=False, name=None)))
    mask = [tuple(map(str, t)) not in have for t in df[keys].itertuples(index=False, name=None)]
    kept = df[mask].reset_index(drop=True)
    log.info("%s：%d 列公告中 %d 列是新的", table, len(df), len(kept))
    return kept


def universe(limit: int) -> list[str]:
    """依近期成交值排序取前 N 檔，作為 FinMind 逐檔抓取的優先順序。"""
    price = store.read("price_daily")
    if price.empty:
        return []
    latest = price["date"].max()
    recent = price[price["date"] >= _shift_days(latest, 20)]
    if recent.empty:
        recent = price[price["date"] == latest]
    rank = (recent.groupby("code")["turnover"].sum()
                  .sort_values(ascending=False))
    return rank.head(limit).index.tolist()


def _shift_days(iso: str, days: int) -> str:
    try:
        d = datetime.fromisoformat(iso).date()
    except ValueError:
        return iso
    return (d - pd.Timedelta(days=days)).isoformat()


def fetch_institutional(codes: list[str], trade_date: str) -> pd.DataFrame:
    """逐檔補三大法人。額度不夠時就抓到哪算到哪，剩下的明天再補。"""
    if not codes:
        return pd.DataFrame()

    existing = store.read("inst_daily")
    have = set()
    if not existing.empty:
        have = set(existing.loc[existing["date"] == trade_date, "code"])

    todo = [c for c in codes if c not in have]
    budget = http.finmind_budget_left()
    if budget <= 0:
        log.warning("FinMind 額度已用盡，本輪不補法人資料")
        return pd.DataFrame()

    todo = todo[:budget]
    log.info("補三大法人：%d 檔（額度剩 %d）", len(todo), budget)

    frames = []
    start = _shift_days(trade_date, 10)
    for i, code in enumerate(todo, 1):
        df = finmind.institutional(code, start, trade_date, wait=False)
        if not df.empty:
            frames.append(df)
        if i % 50 == 0:
            log.info("  已處理 %d/%d", i, len(todo))
    RESULT["steps"]["institutional_codes"] = {"requested": len(todo),
                                              "returned": len(frames)}
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def refresh_financials(codes: list[str]) -> pd.DataFrame:
    """用剩餘額度補最新的季財報與資產負債表。每檔 2 次請求。"""
    if not codes:
        return pd.DataFrame()
    budget = http.finmind_budget_left()
    todo = codes[: max(0, min(len(codes), budget // 2))]
    if not todo:
        log.info("額度不足，本輪不補財報")
        return pd.DataFrame()
    start = _shift_days(datetime.now(timezone.utc).date().isoformat(), 400)
    fs, bs = [], []
    for code in todo:
        f = finmind.financial_statements(code, start, wait=False)
        if not f.empty:
            fs.append(f)
        b = finmind.balance_sheet(code, start, wait=False)
        if not b.empty:
            bs.append(b)
    if bs:
        save("balance_q", pd.concat(bs, ignore_index=True))
    return pd.concat(fs, ignore_index=True) if fs else pd.DataFrame()


def universe_pairs() -> list[tuple[str, str | None]]:
    """全市場的 (代號, 市場別)。以 `company_info` 為準（它是上市＋上櫃合起來的那份）。"""
    info = store.read("company_info")
    if info.empty or "code" not in info.columns:
        return []
    info = info.dropna(subset=["code"]).drop_duplicates("code", keep="last")
    mk = info["market"] if "market" in info.columns else pd.Series([None] * len(info))
    pairs = [(str(c), (str(m) if pd.notna(m) else None))
             for c, m in zip(info["code"], mk) if is_tradable_security(str(c))]
    return pairs


def twse_rows_on(date: str) -> int:
    """資料湖裡那一天有幾檔**上市**。

    判斷「今天的上市補過了沒」要看這個，不是看「資料湖最新日期」—— 理由見下面。
    只讀那一年的分割檔：整張 price_daily 是好幾年的歷史，為了數一天的檔數把它全讀進來太浪費。
    """
    try:
        px = store.read("price_daily", years=[int(str(date)[:4])])
    except (TypeError, ValueError):
        px = store.read("price_daily")
    if px.empty or "date" not in px.columns:
        return 0
    same_day = px["date"].astype(str) == str(date)
    if "market" not in px.columns:
        return int(same_day.sum())
    return int((same_day & (px["market"].astype(str).str.upper() == "TWSE")).sum())


# 上市約 1,300 檔。低於這個數就當作「那天的上市還沒到齊」，要用 mis 補。
# 800 是對著 build_payload.last_complete_date 的門檻挑的（0.6 × 約 1,324 ≈ 794），
# 兩邊講的「到齊」要是同一個標準，不然會出現「補了還是不算到齊」的夾縫。
MIS_FILL_MIN_TWSE = 800

# 台股 13:30 收盤。留五分鐘給最後的撮合與 mis 更新。
TPE_CLOSE_HHMM = (13, 35)


def _tpe_now() -> datetime:
    """台北當下時間（測試會換掉這個函式）。"""
    return datetime.now(timezone(timedelta(hours=8)))


def session_closed(mis_date: str) -> bool:
    """`mis_date` 那一場已經收盤了沒。

    只有「mis 說的日期就是台北的今天」才需要問這件事；比今天早的日期，那一場當然收了。
    ★ 這裡用的是執行當下的**時鐘**，不是拿它當交易日 —— 交易日一律取自 API 回應。
      會加這道是因為：盤中把 mis 的即時價寫成當天的日 K，那一天就被中午的價格佔住了
      （後面幾輪看到「上市已經有 1,300 檔」就不會再補），整天的收盤價都是錯的。
      正常排程（台北 15:30）本來就在收盤後，這道只擋「盤中手動觸發 --phase price」。
    """
    now = _tpe_now()
    if str(mis_date) != now.strftime("%Y-%m-%d"):
        return True
    return (now.hour, now.minute) >= TPE_CLOSE_HHMM


def fill_today_from_mis(openapi_date: str | None) -> pd.DataFrame:
    """openapi 還沒給今天的上市價量時，用 mis 的即時報價把那一天補起來。

    ★ 判斷依據是「那一天**上市**有幾檔」，不是「資料湖最新日期」。
      用最新日期會踩到這個坑：上櫃（TPEX）有自己的來源、常常先寫進去，
      資料湖的最新日期就變成今天了 —— 程式以為「今天已經有了、不用補」，
      可是缺的其實是上市那一半，於是上市永遠補不進來、網站每天慢一天。
      2026-09-15 實測就是這樣：上櫃 1,006 檔、上市 0 檔，
      mis.date_check 判成 will_fill=false，前端的完整度關卡不讓日期前進，
      整天停在 09-14（Andy：「我沒看到最新的」）。

    先只問一檔拿 mis 手上的交易日，確定真的需要補才去抓全市場 ——
    沒必要為了拿一份重複的資料去打人家的端點。
    """
    mis_date = mis.latest_date()
    if not mis_date:
        log.warning("mis 拿不到交易日，本輪不補")
        return pd.DataFrame()

    have_twse = twse_rows_on(mis_date)
    # 報價比 openapi 給的還舊（假日、或 mis 那邊還沒換日），補了也只是重複
    stale = bool(openapi_date and str(mis_date) < str(openapi_date))
    closed = session_closed(mis_date)
    will_fill = closed and (not stale) and have_twse < MIS_FILL_MIN_TWSE
    RESULT["steps"]["mis.date_check"] = {
        "mis_date": mis_date, "openapi_date": openapi_date,
        "lake_latest": store.latest_date("price_daily"),
        "twse_rows_on_mis_date": have_twse,
        "min_needed": MIS_FILL_MIN_TWSE,
        "session_closed": closed,
        "will_fill": will_fill,
    }
    if not will_fill:
        why = ("那一場還沒收盤" if not closed else
               "報價比 openapi 還舊" if stale else f"上市已有 {have_twse} 檔")
        log.info("mis 的 %s 不用補：%s", mis_date, why)
        return pd.DataFrame()

    pairs = universe_pairs()
    if not pairs:
        log.warning("company_info 還沒有內容，不知道要補哪些代號")
        return pd.DataFrame()
    log.info("openapi 停在 %s、%s 的上市只有 %d 檔 —— 用 mis 補 %d 檔",
             openapi_date or "（沒有）", mis_date, have_twse, len(pairs))
    return mis.price_snapshot(pairs)


# 分 K 逐檔跟 Yahoo 要，成本高，所以只做「成交值前段」這一批。
# 跟 build_payload.INTRADAY_LIMIT 是同一個口徑，改一邊要改另一邊。
INTRADAY_LIMIT = 400


def intraday_universe(limit: int = INTRADAY_LIMIT) -> tuple[list[str], dict[str, str]]:
    """要抓 60 分 K 的代號，以及它們的市場別（Yahoo 要靠它決定 .TW / .TWO）。

    挑法：拿資料湖最新那一天，照成交值由大到小取前 `limit` 檔。
    """
    px = store.read("price_daily", years=[datetime.now(timezone.utc).year])
    if px.empty or "date" not in px.columns:
        return [], {}
    latest = str(px["date"].astype(str).max())
    day = px[px["date"].astype(str) == latest]
    if "turnover" in day.columns:
        day = day.sort_values("turnover", ascending=False)
    codes, markets = [], {}
    for _, r in day.iterrows():
        c = str(r["code"])
        if not is_tradable_security(c) or c in markets:
            continue
        markets[c] = str(r.get("market") or "")
        codes.append(c)
        if len(codes) >= limit:
            break
    return codes, markets


def collect_intraday_60m() -> pd.DataFrame:
    """把 60 分 K 的**增量**抓回來（只抓資料湖最後一根之後的那一段）。

    ★ 這一步存在的理由（DECISIONS #155）：分 K 以前完全不進資料湖，
      `build_payload` 每次部署都從零重抓 400 檔 ×（60 分 730 天 ＋ 15 分 60 天），
      實測部署 14 分鐘裡有 13 分 43 秒卡在那裡 —— 昨天抓過的今天再抓一次。
      現在改成「盤後抓當天新增的那幾根、寫進資料湖」，部署只要讀。
    """
    from .sources import yahoo

    codes, markets = intraday_universe()
    if not codes:
        log.warning("還沒有價量資料，不知道要抓哪些代號的分 K")
        return pd.DataFrame()

    have = store.read("intraday_60m")
    since = str(have["ts"].astype(str).max()) if not have.empty and "ts" in have.columns else None
    RESULT["steps"]["intraday.since"] = {"since": since, "codes": len(codes),
                                         "lake_rows": 0 if have.empty else len(have)}
    return yahoo.intraday_since(codes, markets, since, "60m")


def main() -> int:
    ap = argparse.ArgumentParser(description="台股資金輪動儀表板 — 每日盤後管線")
    ap.add_argument("--skip-finmind", action="store_true",
                    help="不動用 FinMind 額度（回補當天用）")
    ap.add_argument("--universe", type=int, default=config.UNIVERSE_SIZE)
    ap.add_argument("--phase", choices=["price", "full", "news"], default="full",
                    help="price＝只抓當天價量（台北 15:30 那輪，其他來源那時還沒出）；"
                         "full＝完整管線（傍晚之後那兩輪）；"
                         "news＝只抓新聞與國際盤（週末用，價量那時本來就不會變）")
    args = ap.parse_args()
    light = args.phase == "price"
    news_only = args.phase == "news"
    RESULT["phase"] = args.phase

    started = datetime.now(timezone.utc)
    log.info("=== 每日管線開始（phase=%s）===", args.phase)

    # 一次性清理：早期版本沒有濾掉權證，上萬檔非股票標的被寫進了 price_daily，
    # 會讓「上漲/下跌家數」變成五千多家。清過就留記號，之後不再重跑。
    marker = config.STATE / "purged_warrants.flag"
    if not marker.exists():
        n = store.purge("price_daily", is_tradable_security)
        marker.write_text(f"removed={n}\nat={started.isoformat()}\n")
        RESULT["steps"]["purge_non_equity"] = {"ok": True, "removed": n}
        log.info("一次性清理完成，移除 %d 列非股票標的", n)

    # -------------------------------------------------- 證交所（不耗額度）
    # phase=news（週末那兩輪）整段跳過：週末價量不會變，打了也只是拿到週五的。
    # Andy 2026-09-14：「週六日有新增也必須更新上去」—— 指的是新聞與國際盤，不是價量。
    price = pd.DataFrame() if news_only else step("twse.price_daily", twse.price_daily)
    trade_date = str(price["date"].iloc[0]) if not price.empty else None
    if trade_date:
        log.info("本輪交易日：%s", trade_date)
    else:
        log.error("拿不到交易日期，融資券與法人資料本輪跳過")

    if not news_only:
        save("price_daily", price)
        save("valuation_daily", step("twse.valuation", twse.valuation_daily))
        save("index_daily", step("twse.index", twse.index_daily))
        save("market_daily", step("twse.market", twse.market_daily))

        # ---------------------------------------------- 上櫃（可失敗）
        otc = step("tpex.price_daily", tpex.price_daily)
        save("price_daily", otc)

    # -------------------------------------------------- 當天補齊（mis，不耗額度）
    # openapi 的日收落後一個交易日（2026-09-14 實測：收盤後一小時它還是 09-11），
    # 所以 openapi 沒給今天的時候，用 mis 把今天補上去。開高低收是準的，
    # 量與值是盤中口徑的暫定值（見 sources/mis.py），隔天會被 openapi 覆蓋。
    filled = pd.DataFrame() if news_only else step("mis.price_snapshot",
                                                   fill_today_from_mis, trade_date)
    save("price_daily", filled)
    if not filled.empty:
        d = str(filled["date"].iloc[0])
        RESULT["provisional_date"] = d
        log.info("已用 mis 補上 %s 的 %d 檔（暫定值）", d, len(filled))
        # 個股補了今天，大盤那格也要跟著補 —— 不然橫幅寫「資料更新到今天」、
        # 加權指數卻還是昨天收的數字（2026-09-14 實測：橫幅 09-14、指數 46,184.85＝09-11 收）。
        save("market_daily", step("mis.market_snapshot", mis.market_snapshot))

    # -------------------------------------------------- 60 分 K（增量，進資料湖）
    # 只在有抓價量的輪次做；news 那幾輪（盤中、週末）不必碰。
    if not news_only:
        save("intraday_60m", step("yahoo.intraday_60m", collect_intraday_60m))

    # 以下這些來源要傍晚才落地。台北 15:30 那輪（--phase price）刻意不抓，
    # 否則會把「還沒出」記成「沒回資料」，網站頂端每天下午都變成黃燈。
    if light:
        # 新聞例外：它整天都在更新，而且是免費 RSS／JSON，不吃任何額度。
        # 15:30 那輪不抓的話，事件側欄要等到 18:30 才會出現當天的新聞
        # （Andy 2026-09-15：「事件需要同步更新今天發生的」）。
        log.info("phase=price：抓價量與新聞，法人／融資券／財報等傍晚那輪再補")
        news_df = step("news.collect", news.collect)
        save("news", news_df)
        save("broker_views", step("news.broker_views", news.extract_broker_views, news_df))
    elif news_only:
        # 週末：價量不會變，但新聞、國際盤（美股週五夜盤、歐股）、總經會變。
        # 只抓這三樣，不動 FinMind 額度、不去打那些週末本來就不更新的端點
        # （打了只會拿到週五的資料，還會被 empty 記成「沒回資料」）。
        log.info("phase=news：週末只更新新聞與國際盤")
        news_df = step("news.collect", news.collect)
        save("news", news_df)
        save("broker_views", step("news.broker_views", news.extract_broker_views, news_df))
        save("intl_daily", step("macro.intl", macro.intl_daily))
        save("macro", step("macro.fred", macro.macro_all))
    else:
        if trade_date:
            save("margin_daily", step("twse.margin", twse.margin_daily, trade_date))
        company = step("twse.company_info", twse.company_info)
        save("company_info", company)
        # FinMind 總覽補上櫃 / 興櫃 / 簡稱（證交所那支只有上市）。
        # 用 append + 去重，FinMind 的列會補上證交所沒有的代號；已有的保留證交所版本的產業別
        info = step("finmind.stock_info", finmind.stock_info)
        if not info.empty:
            have = set(company["code"]) if not company.empty else set()
            extra = info[~info["code"].isin(have)].copy()
            if not extra.empty:
                extra["industry"] = extra["industry_finmind"]
                save("company_info", extra[["code", "name", "market", "industry"]])
            RESULT["steps"]["finmind.stock_info"]["added"] = int(len(extra))
        save("revenue_monthly", step("twse.revenue", twse.revenue_monthly))
        save("financial_q", step("twse.financial", twse.financial_q))
        save("dividend", step("twse.dividend", twse.dividend))
        # 證交所的公告沒有除息日；只補資料湖裡還沒有的 (code, period, kind)，
        # 已由 FinMind 回補（含除息日、發放日）的列不要被蓋掉
        save("dividend_events", only_new_keys("dividend_events",
                                              step("twse.dividend_events", twse.dividend_events)))

        # ---------------------------------------------- 集保（每週）
        save("shareholding_weekly", step("tdcc.shareholding", tdcc.shareholding_weekly))

        # ---------------------------------------------- 新聞與國際
        news_df = step("news.collect", news.collect)
        save("news", news_df)
        save("broker_views", step("news.broker_views", news.extract_broker_views, news_df))
        save("intl_daily", step("macro.intl", macro.intl_daily))
        save("macro", step("macro.fred", macro.macro_all))

    # -------------------------------------------------- FinMind（耗額度，放最後）
    # 大盤／櫃買／台指期的日 K（Andy 2026-09-15：「櫃買 台指期怎麼可能沒有日線數據」）。
    # Yahoo 的櫃買代號壞掉、台指期沒有代號，改走 FinMind；三支加起來只吃 3 次額度。
    if not news_only and not args.skip_finmind:
        since = (pd.Timestamp.now("UTC") - pd.Timedelta(days=40)).strftime("%Y-%m-%d")
        save("index_ohlc", step("finmind.index_ohlc", finmind.index_ohlc, since))
        save("index_ohlc", step("finmind.futures_ohlc", finmind.futures_ohlc, since))

    if not light and not news_only and not args.skip_finmind and trade_date:
        codes = universe(args.universe)
        save("inst_daily", step("finmind.institutional",
                                fetch_institutional, codes, trade_date))
        # 財報一季才變一次，每天用剩餘額度補一小批就夠（財報季會自然滾完）
        save("financial_q", step("finmind.financial_refresh",
                                 refresh_financials, codes[:60]))
    else:
        log.info("跳過 FinMind 步驟")

    # -------------------------------------------------- 執行紀錄（先寫一份）
    def _write_state(final: bool) -> None:
        """把這一輪的結果寫進 last_run.json。

        要分兩次寫，是因為 build_payload 會讀這個檔來產 meta.json（網站頂端的資料狀態）。
        以前只在最後寫一次，build 讀到的永遠是「上一輪」的錯誤清單，狀態整整慢一輪。
        """
        now = datetime.now(timezone.utc)
        RESULT.update({
            "started_at": started.isoformat(),
            "finished_at": now.isoformat(),
            "duration_seconds": round((now - started).total_seconds(), 1),
            "trade_date": trade_date,
            "complete": final,
        })
        if final:                       # 這幾項要掃整個資料湖，只在最後算一次
            RESULT.update({
                "finmind_budget_left": http.finmind_budget_left(),
                "tables": store.table_summary().to_dict("records"),
                "groups_health": loader.health(),
            })
        (config.STATE / "last_run.json").write_text(
            json.dumps(RESULT, ensure_ascii=False, indent=2))

    _write_state(final=False)

    # -------------------------------------------------- 產出前端資料
    try:
        from .build_payload import build
        build()
        RESULT["steps"]["build_payload"] = {"ok": True}
    except Exception as exc:  # noqa: BLE001
        log.exception("產生前端資料失敗")
        RESULT["errors"].append(f"build_payload: {exc}")
        RESULT["steps"]["build_payload"] = {"ok": False, "error": str(exc)}

    _write_state(final=True)

    ok = sum(1 for s in RESULT["steps"].values() if s.get("ok"))
    log.info("=== 完成：%d 個步驟成功，%d 個錯誤，耗時 %.0fs ===",
             ok, len(RESULT["errors"]), RESULT["duration_seconds"])

    # 交易日拿不到行情才算真正失敗；其他來源缺漏不阻斷排程
    return 0 if trade_date else 1


if __name__ == "__main__":
    raise SystemExit(main())
