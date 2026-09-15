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
from datetime import datetime, timezone

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


def fill_today_from_mis(openapi_date: str | None) -> pd.DataFrame:
    """openapi 還沒給今天的話，用 mis 把今天補起來。

    先只問一檔拿 mis 手上的交易日，確定真的比較新才去抓全市場 ——
    一天 24 個請求不算多，但沒必要為了拿一份重複的資料去打人家的端點。
    """
    mis_date = mis.latest_date()
    if not mis_date:
        log.warning("mis 拿不到交易日，本輪不補")
        return pd.DataFrame()

    have = store.latest_date("price_daily")
    newest_known = max([d for d in (openapi_date, have) if d], default=None)
    RESULT["steps"]["mis.date_check"] = {
        "mis_date": mis_date, "openapi_date": openapi_date,
        "lake_latest": have, "will_fill": bool(not newest_known or mis_date > newest_known),
    }
    if newest_known and mis_date <= newest_known:
        log.info("mis 的 %s 沒有比已知的 %s 新，不用補", mis_date, newest_known)
        return pd.DataFrame()

    pairs = universe_pairs()
    if not pairs:
        log.warning("company_info 還沒有內容，不知道要補哪些代號")
        return pd.DataFrame()
    log.info("openapi 還停在 %s，mis 已經有 %s —— 補 %d 檔",
             openapi_date or "（沒有）", mis_date, len(pairs))
    return mis.price_snapshot(pairs)


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

    # 以下這些來源要傍晚才落地。台北 15:30 那輪（--phase price）刻意不抓，
    # 否則會把「還沒出」記成「沒回資料」，網站頂端每天下午都變成黃燈。
    if light:
        log.info("phase=price：只抓價量，法人／融資券／財報／新聞等傍晚那輪再補")
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
