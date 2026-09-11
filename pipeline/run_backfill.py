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
from datetime import date, datetime, timedelta, timezone

import pandas as pd

from . import config
from .groups import loader
from .sources import finmind
from .util import http, roc, store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("backfill")

PROGRESS = config.STATE / "backfill_progress.json"

# 各資料集鍵（--datasets 用的名字）；summary 與 main() 的合計都照這張表
DATA_KEYS = ("price", "inst", "per", "revenue", "financial", "balance",
             "dividend", "divresult", "margin", "holding")

# ETF / 指數型商品沒有財報、月營收、本益比、股利公告可抓（ETF 其實有配息，先不抓），
# 逐檔去問只是在燒額度；融資券與股權分散 ETF 有，要抓
FINANCIAL_KEYS = {"per", "revenue", "financial", "balance", "dividend", "divresult"}

# 排程用的預設回補計畫：依序執行，某一步額度用盡就停下，下一小時從那一步接續。
# scope=universe → target_codes(limit)；scope=groups → 只補 groups.yaml 的成分股。
PLAN_DEFAULT = [
    {"datasets": "revenue+financial+balance", "start": "2016-01-01", "scope": "universe"},
    {"datasets": "dividend+divresult",        "start": "2016-01-01", "scope": "universe"},
    {"datasets": "margin+holding",            "start": "2021-01-01", "scope": "universe"},
    {"datasets": "price",                     "start": "2000-01-01", "scope": "groups"},
]
PLANS = {"default": PLAN_DEFAULT}
TAIPEI = timezone(timedelta(hours=8))


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


_cov_cache: dict[str, pd.DataFrame] = {}


def already_covered(table: str, code: str, start: str, respect_time: bool = True) -> bool:
    """該檔在這張表裡是否已經補到指定起始日之前。

    整張表只讀一次（price_daily 有六十幾萬列，逐檔重讀會讓一輪回補多花好幾分鐘）；
    這一輪新補進去的股票會被 progress 檔記住，不靠這個快取判斷。

    respect_time=False 時一律回 False（只看 progress 檔的 done_key）——
    每月重抓股利公告的步驟用：dividend_events 沒有時間欄位，否則「有資料就算補過」
    會讓月更新永遠被跳掉。"""
    if not respect_time:
        return False
    if table not in _cov_cache:
        _cov_cache[table] = store.read(table)
    df = _cov_cache[table]
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


def done_key_of(key: str, code: str, start: str, tag: str | None = None) -> str:
    """progress 檔裡的完成鍵。

    起始日等於 config.BACKFILL_START 時維持舊格式 "price:2330"（相容既有進度檔），
    其他起始日帶上日期 "price@2000-01-01:2330"；月更新步驟改帶 tag "dividend@m2026-09:2330"，
    每個月的鍵都不同，所以每月會重抓一次。"""
    if tag:
        return f"{key}@{tag}:{code}"
    if start == config.BACKFILL_START:
        return f"{key}:{code}"
    return f"{key}@{start}:{code}"


def datasets_key_of(datasets: str, start: str, tag: str | None = None) -> str:
    """prog["complete"] 的鍵；規則與 done_key_of 一致（舊格式 "revenue" 不變）。"""
    base = "+".join(sorted(datasets.replace("+", ",").split(",")))
    if tag:
        return f"{base}@{tag}"
    if start == config.BACKFILL_START:
        return base
    return f"{base}@{start}"


def run(datasets: str, limit: int | None, start: str, *,
        codes: list[str] | None = None, datasets_key: str | None = None,
        tag: str | None = None, respect_time: bool = True) -> dict:
    """跑一輪回補。

    codes：覆寫目標清單（計畫步驟用，例如只補族群成分股）；預設 target_codes(limit)。
    datasets_key：prog["complete"] 用的鍵；預設依 datasets / start / tag 產生。
    tag / respect_time：月更新步驟用，見 done_key_of 與 already_covered。"""
    wanted = set(datasets.replace("+", ",").split(","))
    unknown = wanted - set(DATA_KEYS)
    if unknown:
        log.warning("不認識的資料集，略過：%s", sorted(unknown))
    codes = list(codes) if codes is not None else target_codes(limit)
    log.info("回補目標：%d 檔，資料集 %s，起始 %s%s", len(codes), sorted(wanted), start,
             f"，標記 {tag}" if tag else "")

    prog = _progress()
    prog.setdefault("done", {})
    prog.setdefault("complete", {})
    datasets_key = datasets_key or datasets_key_of(datasets, start, tag)
    summary = {k: 0 for k in DATA_KEYS}
    summary.update({"skipped": 0, "failed": 0, "no_data": 0, "exhausted": False})

    jobs = [
        ("price", "price_daily", lambda c: finmind.price_history(c, start, wait=False)),
        ("inst", "inst_daily", lambda c: finmind.institutional(c, start, wait=False)),
        ("per", "valuation_daily", lambda c: finmind.per_history(c, start, wait=False)),
        ("revenue", "revenue_monthly", lambda c: finmind.month_revenue(c, start, wait=False)),
        ("financial", "financial_q", lambda c: finmind.financial_statements(c, start, wait=False)),
        ("balance", "balance_q", lambda c: finmind.balance_sheet(c, start, wait=False)),
        ("dividend", "dividend_events", lambda c: finmind.dividend_events(c, start, wait=False)),
        ("divresult", "dividend_results", lambda c: finmind.dividend_results(c, start, wait=False)),
        ("margin", "margin_daily", lambda c: finmind.margin_history(c, start, wait=False)),
        ("holding", "shareholding_weekly", lambda c: finmind.holding_history(c, start, wait=False)),
    ]

    for i, code in enumerate(codes, 1):
        if http.finmind_budget_left() <= 1:
            log.warning("FinMind 額度用盡，本輪停在第 %d/%d 檔（%s）", i, len(codes), code)
            summary["exhausted"] = True
            break

        for key, table, fetch in jobs:
            if key not in wanted:
                continue
            done_key = done_key_of(key, code, start, tag)
            if prog["done"].get(done_key) or already_covered(table, code, start, respect_time):
                summary["skipped"] += 1
                continue
            if key in FINANCIAL_KEYS and roc.is_etf(code):
                prog["done"][done_key] = True
                summary["skipped"] += 1
                continue
            if http.finmind_budget_left() <= 1:
                summary["exhausted"] = True
                break

            try:
                df = fetch(code)
            except Exception as exc:  # noqa: BLE001
                log.warning("%s %s 抓取失敗：%s", key, code, exc)
                summary["failed"] += 1
                continue

            if http.finmind_budget_left() <= 1:
                # 這一筆是撞到伺服器端限流才空的，不能當作「沒資料」
                summary["exhausted"] = True
                break

            if df is None or df.empty:
                # 額度還在卻拿不到東西 → 這檔真的沒有這種資料（新掛牌、KY 股缺財報…），
                # 記成做過，下一輪不要再問；要重抓就刪 progress 檔裡的鍵
                summary["no_data"] += 1
                prog["done"][done_key] = True
                continue
            n = store.append(table, df)
            summary[key] += n
            prog["done"][done_key] = True

        if i % 25 == 0:
            _save_progress(prog)
            log.info("進度 %d/%d（額度剩 %d）：已寫入 %s",
                     i, len(codes), http.finmind_budget_left(),
                     {k: summary[k] for k in DATA_KEYS if k in wanted})
            time.sleep(0.2)

        if summary["exhausted"]:
            break

    # 整輪走完、沒被限流、也沒有抓取失敗 → 這組資料集對目前的目標清單已補齊。
    # 排程觸發的工作流會看這個旗標決定要不要直接跳過（省 Actions 分鐘與額度）。
    # 手動觸發永遠會重跑一輪，所以 groups.yaml 新增成分股後按一次即可。
    finished_all = not summary["exhausted"] and summary["failed"] == 0
    prog["complete"][datasets_key] = {
        "done": finished_all,
        "at": datetime.now(timezone.utc).isoformat(),
        "codes": len(codes),
    }
    _save_progress(prog)
    log.info("回補結束：%s", summary)
    return summary


# ------------------------------------------------------------------ 回補計畫

def monthly_step(today: date | None = None) -> dict:
    """每月重抓一次族群成分股的股利公告（今年以來）。

    tag 帶年月，所以每個月的 done_key 都是新的；一個月約 260 次請求。"""
    today = today or datetime.now(TAIPEI).date()
    return {"datasets": "dividend+divresult", "start": f"{today.year}-01-01",
            "scope": "groups", "tag": f"m{today:%Y-%m}"}


def plan_steps(name: str, today: date | None = None) -> list[dict]:
    if name not in PLANS:
        raise KeyError(f"沒有這個回補計畫：{name}（可用：{sorted(PLANS)}）")
    return [dict(s) for s in PLANS[name]] + [monthly_step(today)]


def _codes_for_scope(scope: str, limit: int | None) -> list[str]:
    if scope == "groups":
        m = loader.membership()
        if m.empty:
            log.warning("groups.yaml 沒有任何成分股，這一步沒有目標")
            return []
        return list(dict.fromkeys(m["code"].tolist()))
    return target_codes(limit)


def plan_is_done(prog: dict, name: str = "default", today: date | None = None) -> bool:
    """進度檔裡的計畫是否已補齊且仍在同一個月（月更新步驟的 tag 換了就算未完成）。"""
    flag = (prog.get("complete") or {}).get(f"plan:{name}")
    if not isinstance(flag, dict) or not flag.get("done"):
        return False
    return flag.get("month") == monthly_step(today)["tag"][1:]


def run_plan(name: str, limit: int | None, today: date | None = None) -> dict:
    """依序執行計畫的每一步；某一步額度用盡就停下，後面的步驟下一小時再來。

    每一步都會寫自己的 prog["complete"][datasets_key]；全部 done 才把
    prog["complete"]["plan:<name>"] 標成 done，並記下月更新的年月。"""
    steps = plan_steps(name, today)
    month = monthly_step(today)["tag"][1:]
    results: dict[str, bool] = {}
    stopped_at: str | None = None
    totals = {k: 0 for k in DATA_KEYS}

    for n, step in enumerate(steps, 1):
        tag = step.get("tag")
        key = datasets_key_of(step["datasets"], step["start"], tag)
        log.info("計畫 %s 第 %d/%d 步：%s（起始 %s，範圍 %s）",
                 name, n, len(steps), key, step["start"], step.get("scope", "universe"))
        codes = _codes_for_scope(step.get("scope", "universe"), limit)
        summary = run(step["datasets"], limit, step["start"], codes=codes,
                      datasets_key=key, tag=tag, respect_time=not tag)
        for k in DATA_KEYS:
            totals[k] += summary.get(k, 0)
        done = not summary["exhausted"] and summary["failed"] == 0
        results[key] = done
        if summary["exhausted"]:
            stopped_at = key
            log.warning("計畫 %s 在第 %d 步（%s）額度用盡，其餘步驟下一輪接續", name, n, key)
            break

    all_done = len(results) == len(steps) and all(results.values())
    prog = _progress()
    prog.setdefault("complete", {})
    prog["complete"][f"plan:{name}"] = {
        "done": all_done,
        "at": datetime.now(timezone.utc).isoformat(),
        "month": month,
        "steps": results,
        "stopped_at": stopped_at,
    }
    _save_progress(prog)
    log.info("計畫 %s 結束：done=%s，各步 %s，寫入 %s", name, all_done, results,
             {k: v for k, v in totals.items() if v})
    return {"done": all_done, "steps": results, "stopped_at": stopped_at,
            "exhausted": stopped_at is not None, **totals}


def main() -> int:
    ap = argparse.ArgumentParser(description="FinMind 歷史回補")
    ap.add_argument("--limit", default="400",
                    help="本輪最多處理幾檔；留空或 0 表示不限")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--datasets", default=None,
                      help="price / inst / per / revenue / financial / balance / "
                           "dividend / divresult / margin / holding，可用 + 串接（預設 price+inst）")
    mode.add_argument("--plan", default=None, choices=sorted(PLANS),
                      help="改跑預設回補計畫（依序多步驟，忽略 --start；與 --datasets 二擇一）")
    ap.add_argument("--start", default=config.BACKFILL_START)
    args = ap.parse_args()

    if not config.FINMIND_TOKEN:
        log.warning("未設定 FINMIND_TOKEN，額度只有 300/hr，回補會很慢")

    limit_raw = (args.limit or "").strip()
    limit = int(limit_raw) if limit_raw.isdigit() and int(limit_raw) > 0 else None

    if args.plan:
        summary = run_plan(args.plan, limit)
    else:
        summary = run(args.datasets or "price+inst", limit, args.start)
    total = sum(summary[k] for k in DATA_KEYS)
    log.info("本輪共寫入 %d 列", total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
