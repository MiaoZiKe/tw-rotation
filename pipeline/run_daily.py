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
from .sources import finmind, macro, news, tdcc, tpex, twse
from .util import http, store
from .util.roc import is_tradable_security

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("run_daily")

RESULT: dict = {"steps": {}, "errors": []}


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


def main() -> int:
    ap = argparse.ArgumentParser(description="台股資金輪動儀表板 — 每日盤後管線")
    ap.add_argument("--skip-finmind", action="store_true",
                    help="不動用 FinMind 額度（回補當天用）")
    ap.add_argument("--universe", type=int, default=config.UNIVERSE_SIZE)
    args = ap.parse_args()

    started = datetime.now(timezone.utc)
    log.info("=== 每日管線開始 ===")

    # 一次性清理：早期版本沒有濾掉權證，上萬檔非股票標的被寫進了 price_daily，
    # 會讓「上漲/下跌家數」變成五千多家。清過就留記號，之後不再重跑。
    marker = config.STATE / "purged_warrants.flag"
    if not marker.exists():
        n = store.purge("price_daily", is_tradable_security)
        marker.write_text(f"removed={n}\nat={started.isoformat()}\n")
        RESULT["steps"]["purge_non_equity"] = {"ok": True, "removed": n}
        log.info("一次性清理完成，移除 %d 列非股票標的", n)

    # -------------------------------------------------- 證交所（不耗額度）
    price = step("twse.price_daily", twse.price_daily)
    trade_date = str(price["date"].iloc[0]) if not price.empty else None
    if trade_date:
        log.info("本輪交易日：%s", trade_date)
    else:
        log.error("拿不到交易日期，融資券與法人資料本輪跳過")

    save("price_daily", price)
    save("valuation_daily", step("twse.valuation", twse.valuation_daily))
    if trade_date:
        save("margin_daily", step("twse.margin", twse.margin_daily, trade_date))
    save("index_daily", step("twse.index", twse.index_daily))
    save("market_daily", step("twse.market", twse.market_daily))
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

    # -------------------------------------------------- 上櫃（可失敗）
    otc = step("tpex.price_daily", tpex.price_daily)
    save("price_daily", otc)

    # -------------------------------------------------- 集保（每週）
    sh = step("tdcc.shareholding", tdcc.shareholding_weekly)
    save("shareholding_weekly", sh)

    # -------------------------------------------------- 新聞與國際
    news_df = step("news.collect", news.collect)
    save("news", news_df)
    save("broker_views", step("news.broker_views", news.extract_broker_views, news_df))
    save("intl_daily", step("macro.intl", macro.intl_daily))
    save("macro", step("macro.fred", macro.macro_all))

    # -------------------------------------------------- FinMind（耗額度，放最後）
    if not args.skip_finmind and trade_date:
        codes = universe(args.universe)
        save("inst_daily", step("finmind.institutional",
                                fetch_institutional, codes, trade_date))
        # 財報一季才變一次，每天用剩餘額度補一小批就夠（財報季會自然滾完）
        save("financial_q", step("finmind.financial_refresh",
                                 refresh_financials, codes[:60]))
    else:
        log.info("跳過 FinMind 步驟")

    # -------------------------------------------------- 產出前端資料
    try:
        from .build_payload import build
        build()
        RESULT["steps"]["build_payload"] = {"ok": True}
    except Exception as exc:  # noqa: BLE001
        log.exception("產生前端資料失敗")
        RESULT["errors"].append(f"build_payload: {exc}")
        RESULT["steps"]["build_payload"] = {"ok": False, "error": str(exc)}

    # -------------------------------------------------- 執行紀錄
    finished = datetime.now(timezone.utc)
    RESULT.update({
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "duration_seconds": round((finished - started).total_seconds(), 1),
        "trade_date": trade_date,
        "finmind_budget_left": http.finmind_budget_left(),
        "tables": store.table_summary().to_dict("records"),
        "groups_health": loader.health(),
    })
    (config.STATE / "last_run.json").write_text(
        json.dumps(RESULT, ensure_ascii=False, indent=2))

    ok = sum(1 for s in RESULT["steps"].values() if s.get("ok"))
    log.info("=== 完成：%d 個步驟成功，%d 個錯誤，耗時 %.0fs ===",
             ok, len(RESULT["errors"]), RESULT["duration_seconds"])

    # 交易日拿不到行情才算真正失敗；其他來源缺漏不阻斷排程
    return 0 if trade_date else 1


if __name__ == "__main__":
    raise SystemExit(main())
