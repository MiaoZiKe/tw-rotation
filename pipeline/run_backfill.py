"""歷史回補。

這是整個專案最有時效性的一件事：開放資料只有當日快照，每晚一天開始存檔，
就永久少一天歷史。FinMind 免費層是目前唯一能一次補回十年的免費途徑。

設計成可以重複執行：
- 已經補過的股票會被跳過（依資料湖裡既有的最早日期判斷）
- 額度用盡就停下並寫進度檔，下一輪從沒補到的地方接續
- 中途被 CI timeout 砍掉，已寫入的部分不會丟失
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import datetime, timezone

import pandas as pd

from . import config
from .groups import loader
from .sources import finmind
from .util import http, store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("backfill")

PROGRESS = config.STATE / "backfill_progress.json"


def _progress() -> dict:
    if PROGRESS.exists():
        try:
            return json.loads(PROGRESS.read_text())
        except ValueError:
            pass
    return {"done": {}, "updated_at": None}


def _save_progress(p: dict) -> None:
    p["updated_at"] = datetime.now(timezone.utc).isoformat()
    PROGRESS.write_text(json.dumps(p, ensure_ascii=False, indent=2))


def target_codes(limit: int | None) -> list[str]:
    """回補優先順序：先是 groups.yaml 裡的族群成分股（這些一定要有歷史），
    再依近期成交值補其他流動性好的標的。"""
    picks: list[str] = []

    m = loader.membership()
    if not m.empty:
        picks.extend(dict.fromkeys(m["code"].tolist()))

    price = store.read("price_daily")
    if not price.empty:
        latest = price["date"].max()
        recent = price[price["date"] == latest]
        by_turnover = (recent.groupby("code")["turnover"].sum()
                             .sort_values(ascending=False).index.tolist())
        for c in by_turnover:
            if c not in picks:
                picks.append(c)
    else:
        # 資料湖全空（第一次跑）就用 FinMind 的股票總覽當來源
        info = finmind.stock_info()
        if not info.empty:
            for c in info["code"]:
                if c not in picks:
                    picks.append(c)

    return picks[:limit] if limit else picks


def already_covered(table: str, code: str, start: str) -> bool:
    """該檔在這張表裡是否已經補到指定起始日之前。"""
    df = store.read(table)
    if df.empty or "code" not in df.columns:
        return False
    sub = df[df["code"] == code]
    if sub.empty:
        return False
    # 各表的時間欄位不同：日表 date、月表 ym、季表 period_end
    col = next((c for c in ("date", "ym", "period_end") if c in sub.columns), None)
    if col is None:
        return True          # 沒有時間維度的表，有資料就算補過
    earliest = str(sub[col].min())
    return earliest <= start[:len(earliest)]


def run(datasets: str, limit: int | None, start: str) -> dict:
    wanted = set(datasets.replace("+", ",").split(","))
    codes = target_codes(limit)
    log.info("回補目標：%d 檔，資料集 %s，起始 %s", len(codes), sorted(wanted), start)

    prog = _progress()
    summary = {"price": 0, "inst": 0, "per": 0, "revenue": 0,
               "financial": 0, "balance": 0, "skipped": 0, "exhausted": False}

    jobs = [
        ("price", "price_daily", lambda c: finmind.price_history(c, start, wait=False)),
        ("inst", "inst_daily", lambda c: finmind.institutional(c, start, wait=False)),
        ("per", "valuation_daily", lambda c: finmind.per_history(c, start, wait=False)),
        ("revenue", "revenue_monthly", lambda c: finmind.month_revenue(c, start, wait=False)),
        ("financial", "financial_q", lambda c: finmind.financial_statements(c, start, wait=False)),
        ("balance", "balance_q", lambda c: finmind.balance_sheet(c, start, wait=False)),
    ]

    for i, code in enumerate(codes, 1):
        if http.finmind_budget_left() <= 1:
            log.warning("FinMind 額度用盡，本輪停在第 %d/%d 檔（%s）", i, len(codes), code)
            summary["exhausted"] = True
            break

        for key, table, fetch in jobs:
            if key not in wanted:
                continue
            done_key = f"{key}:{code}"
            if prog["done"].get(done_key) or already_covered(table, code, start):
                summary["skipped"] += 1
                continue
            if http.finmind_budget_left() <= 1:
                summary["exhausted"] = True
                break

            try:
                df = fetch(code)
            except Exception as exc:  # noqa: BLE001
                log.warning("%s %s 抓取失敗：%s", key, code, exc)
                continue

            if df is None or df.empty:
                continue
            n = store.append(table, df)
            summary[key] += n
            prog["done"][done_key] = True

        if i % 25 == 0:
            _save_progress(prog)
            log.info("進度 %d/%d（額度剩 %d）：價量 %d 列、法人 %d 列",
                     i, len(codes), http.finmind_budget_left(),
                     summary["price"], summary["inst"])
            time.sleep(0.2)

        if summary["exhausted"]:
            break

    _save_progress(prog)
    log.info("回補結束：%s", summary)
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="FinMind 歷史回補")
    ap.add_argument("--limit", default="400",
                    help="本輪最多處理幾檔；留空或 0 表示不限")
    ap.add_argument("--datasets", default="price+inst",
                    help="price / inst / per / revenue / financial / balance，可用 + 串接")
    ap.add_argument("--start", default=config.BACKFILL_START)
    args = ap.parse_args()

    if not config.FINMIND_TOKEN:
        log.warning("未設定 FINMIND_TOKEN，額度只有 300/hr，回補會很慢")

    limit_raw = (args.limit or "").strip()
    limit = int(limit_raw) if limit_raw.isdigit() and int(limit_raw) > 0 else None

    summary = run(args.datasets, limit, args.start)
    total = sum(summary[k] for k in ("price", "inst", "per", "revenue", "financial", "balance"))
    log.info("本輪共寫入 %d 列", total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
