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

# ---------------------------------------------------------------- 資料集封印
# 2026-09-19 的事故：revenue / financial / balance 連續好幾輪整組回空，
# 判定「資料集不開放」的邏輯只活在那一輪的記憶體裡、沒有寫進進度檔，
# 於是**每一輪都重問全部 506 檔**、每一輪都把額度燒光，
# 計畫永遠停在第 1 步，後面幾千檔個股的價量與法人永遠輪不到。
#
# 修法是「封印 ＋ 定期探測」：判定不開放就寫進進度檔並記時間戳，
# 之後每天最多重問一次，而且重問只拿少量樣本去探，探到通了才恢復全量。
# 刻意不做成「永遠不再問」—— 資料集有可能之後就開放了（或只是上游暫時壞掉），
# 那樣會永遠補不到。
UNAVAILABLE_RETRY_HOURS = 24   # 封印後至少隔這麼久才准再探一次
PROBE_CODES = 5                # 解封探測一輪最多問幾檔（夠過「3 檔以上」的判定門檻）
EMPTY_STREAK_LIMIT = 20        # 同一個資料集在一輪內連續回空幾檔就先收手

# 健檢用的標的：台積電最近幾天的日線 —— FinMind 免費層一定有的東西。
# 連它都拿不到就不是「某個資料集不開放」，是整把 token／帳號的問題。
CANARY_CODE = "2330"
CANARY_DAYS = 10


def _progress() -> dict:
    if PROGRESS.exists():
        try:
            return json.loads(PROGRESS.read_text())
        except ValueError:
            pass
    return {"done": {}, "updated_at": None}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(value) -> datetime | None:
    try:
        ts = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


def dataset_mode(prog: dict, key: str, now: datetime | None = None) -> str:
    """這一輪要怎麼對待這個資料集。

    full   —— 正常全量跑（沒有被封印，或剛剛探測成功）
    probe  —— 封印超過 UNAVAILABLE_RETRY_HOURS，這一輪只拿 PROBE_CODES 檔去探
    sealed —— 還在封印期內，這一輪一次請求都不發（額度留給補得動的步驟）
    """
    rec = (prog.get("unavailable") or {}).get(key)
    if not isinstance(rec, dict):
        return "full"
    ts = _parse_ts(rec.get("last_probe") or rec.get("since"))
    if ts is None:
        return "probe"
    hours = ((now or _now()) - ts).total_seconds() / 3600
    return "probe" if hours >= UNAVAILABLE_RETRY_HOURS else "sealed"


def seal_dataset(prog: dict, key: str, reason: str = "") -> bool:
    """把資料集記成「不開放」。回傳 True 代表這是第一次判定（先前沒有紀錄）。"""
    book = prog.setdefault("unavailable", {})
    rec = book.get(key)
    first = not isinstance(rec, dict)
    now = _now().isoformat()
    if first:
        rec = {"since": now, "probes": 0}
    rec["last_probe"] = now
    rec["probes"] = int(rec.get("probes") or 0) + 1
    if reason:
        rec["last_reason"] = reason[:200]
    book[key] = rec
    return first


def unseal_dataset(prog: dict, key: str) -> None:
    """探測拿到資料了 —— 解除封印，下一輪恢復全量。"""
    book = prog.get("unavailable") or {}
    if key in book:
        book.pop(key, None)
        log.info("%s 又拿得到資料了 —— 解除封印，恢復全量回補", key)


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

    # key -> 這一輪回空的 done_key 清單；key -> 這一輪至少拿到過一次資料
    pending_no_data: dict[str, list[str]] = {}
    got_data: set[str] = set()

    # 被封印的資料集這一輪怎麼處理（見 dataset_mode 的說明）
    modes = {k: dataset_mode(prog, k) for k in wanted}
    asked: dict[str, int] = {k: 0 for k in wanted}
    empty_streak: dict[str, int] = {k: 0 for k in wanted}
    halted: set[str] = set()          # 這一輪已經收手的資料集（連續回空太多）
    for k, mode in sorted(modes.items()):
        if mode == "sealed":
            rec = (prog.get("unavailable") or {}).get(k, {})
            log.info("%s 先前判定為不開放（%s 起，已探 %s 次），封印中，這一輪不花額度",
                     k, str(rec.get("since"))[:19], rec.get("probes"))
        elif mode == "probe":
            log.info("%s 封印超過 %d 小時 —— 這一輪拿 %d 檔去探，探到就恢復全量",
                     k, UNAVAILABLE_RETRY_HOURS, PROBE_CODES)

    for i, code in enumerate(codes, 1):
        if http.finmind_budget_left() <= 1:
            log.warning("FinMind 額度用盡，本輪停在第 %d/%d 檔（%s）", i, len(codes), code)
            summary["exhausted"] = True
            break

        for key, table, fetch in jobs:
            if key not in wanted:
                continue
            if modes[key] == "sealed" or key in halted:
                continue
            if modes[key] == "probe" and asked[key] >= PROBE_CODES:
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

            asked[key] += 1
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
                # 額度還在卻拿不到東西 → **通常**是這檔真的沒有這種資料
                #（新掛牌、KY 股缺財報…），記成做過，下一輪不要再問。
                # ★ 但「整組資料集每一檔都回空」是完全不同的一件事：那代表這個資料集
                #   在免費層根本沒開，不是這 N 檔沒有資料。2026-09-12 那輪就是這樣 ——
                #   holding（集保股權分散）500 檔全回空、500 個 done 鍵全被寫死，
                #   於是「大戶 4 週變化」在全站永遠顯示「—」，而且再也不會有人去重抓。
                #   所以先記在暫存區，等整輪跑完再決定要不要真的寫進 progress（見下方）。
                summary["no_data"] += 1
                pending_no_data.setdefault(key, []).append(done_key)
                empty_streak[key] += 1
                # ★ 第一次遇到「整個資料集掛掉」也不該把額度燒完：連續 N 檔回空、
                #   而且這一輪一次都沒成功過 → 先收手，剩下的額度留給補得動的步驟。
                #   2026-09-19 少了這道閘，光是必定失敗的請求就吃掉 506 次額度。
                if empty_streak[key] >= EMPTY_STREAK_LIMIT and key not in got_data:
                    halted.add(key)
                    log.warning("%s 連續 %d 檔回空且一次都沒成功 —— 本輪先停問這個資料集，"
                                "把額度留給其他步驟", key, empty_streak[key])
                continue
            n = store.append(table, df)
            summary[key] += n
            got_data.add(key)
            empty_streak[key] = 0
            if modes[key] != "full":
                # 探測成功：解除封印，這一輪剩下的檔照全量跑
                unseal_dataset(prog, key)
                modes[key] = "full"
            prog["done"][done_key] = True

        if i % 25 == 0:
            _save_progress(prog)
            log.info("進度 %d/%d（額度剩 %d）：已寫入 %s",
                     i, len(codes), http.finmind_budget_left(),
                     {k: summary[k] for k in DATA_KEYS if k in wanted})
            time.sleep(0.2)

        if summary["exhausted"]:
            break

    # ★ 結算「回空」的那些鍵：某個 key 這一輪只要成功拿到過一次資料，
    #   其餘回空的就是真的沒資料，照舊記 done；一次都沒拿到（而且問了 3 檔以上）的，
    #   判定是這個資料集本身不開放，**不寫 done**，下一輪重問。
    #   門檻訂 3 是為了不要因為一輪只跑到兩檔就誤判。
    newly_unavailable: list[str] = []
    for key, keys in pending_no_data.items():
        if key in got_data or len(keys) < 3:
            for dk in keys:
                prog["done"][dk] = True
        else:
            err = http.finmind_last_error() or {}
            reason = f"HTTP {err.get('status')}：{err.get('msg')}" if err else "整組回空"
            first = seal_dataset(prog, key, reason)
            log.warning("%s 這一輪 %d 檔全部回空 —— 判定為該資料集不開放（而不是這些股票沒資料），"
                        "不寫入 done；已寫進進度檔封印，%d 小時後只拿 %d 檔重探。上游回應：%s",
                        key, len(keys), UNAVAILABLE_RETRY_HOURS, PROBE_CODES, reason)
            summary["unavailable"] = sorted(set(summary.get("unavailable", [])) | {key})
            if first:
                newly_unavailable.append(key)
    if newly_unavailable:
        summary["newly_unavailable"] = sorted(newly_unavailable)
    sealed_now = sorted(k for k in wanted if k in (prog.get("unavailable") or {}))
    if sealed_now:
        summary["sealed"] = sealed_now

    # 這一組資料集什麼情況下才算「補齊」（排程的 guard 看這個旗標決定要不要整輪跳過）：
    #   1) 沒有撞到 FinMind 限流（exhausted=False）——還沒問完，當然不算完成
    #   2) 沒有抓取例外（failed=0）
    #   3) 沒有**這一輪第一次**被判定為不開放的資料集 —— 那個狀態還不確定
    #      （可能只是上游暫時壞掉），留一輪讓下一次重問，不要太早宣告完成
    # ★ 已經封印過的資料集**不算**未完成。這一條是 2026-09-19 事故的正解：
    #   原本寫成「只要有 unavailable 就永遠不算完成」，結果一個確定不開放的資料集
    #   把整個計畫鎖死在第 1 步，後面幾千檔個股的價量與法人永遠輪不到。
    #   不開放的資料集不會因為我們一直等就開放；它該被封印＋每天探一次，
    #   而不是拿整個計畫去陪葬。
    finished_all = (not summary["exhausted"] and summary["failed"] == 0
                    and not newly_unavailable)
    summary["finished"] = finished_all
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


INDEX_START = "2000-01-01"


def backfill_indices(prog: dict, start: str = INDEX_START) -> bool:
    """把加權指數、櫃買指數、台指期的日 K 一次補到 2000 年。

    為什麼要另外寫一支，而不是塞進 PLAN_DEFAULT（2026-09-19）
    --------------------------------------------------------
    計畫的每一步都是「逐檔跑 codes」，但指數不是個股 —— 三個 symbol 一共只要 3 次請求。

    為什麼非補不可（Andy 2026-09-15：「櫃買 台指期怎麼可能沒有日線數據」）
    ------------------------------------------------------------------
    `run_daily` 抓指數時寫死 `since = now - 40 天`，而回補計畫裡**沒有這張表** ——
    所以資料湖永遠只有 40 天：實測 32 個交易日 → 週 K 7 根、**月 K 2 根、季 K 1 根**。
    `market3.js` 卻給了日／週／月／季四顆按鈕，使用者按「季 K」看到一根棒子。
    這不是「還沒補完」，是**設計上永遠不會變多**，所以當時回報「已修好」是不對的。

    順帶解掉季節性的基準問題：`seasonality_v3.json` 的 note 寫著「指數只有 12 個月，不夠比」，
    所謂「超額報酬」其實退回成全市場等權平均、不是大盤。指數有歷史之後才比得了。

    補過就不再補（進度檔記 `complete["index_ohlc"]`），每日管線照樣用 40 天的增量。
    """
    flag = (prog.get("complete") or {}).get("index_ohlc")
    if isinstance(flag, dict) and flag.get("done") and flag.get("start") == start:
        log.info("指數歷史已補過（%s 起），跳過", start)
        return True
    if http.finmind_budget_left() <= 3:
        log.warning("額度不足 3 次，指數歷史這一輪先不補")
        return False

    total = 0
    # 每個來源要求哪些 symbol 都齊了才算數：index_ohlc 是一支函式抓兩個指數，
    # 只回到加權、櫃買失敗時它仍然是「非空」的 —— 那樣標成 done 會讓櫃買永遠只有 40 天。
    for label, fn, need in (("指數", finmind.index_ohlc, {"TSE", "OTC"}),
                            ("台指期", finmind.futures_ohlc, {"FUT"})):
        try:
            df = fn(start, wait=False)
        except Exception as exc:  # noqa: BLE001
            log.warning("%s 歷史抓取失敗：%s", label, exc)
            return False
        if df is None or df.empty:
            err = http.finmind_last_error() or {}
            log.warning("%s 歷史回空 —— 不標 done，下一輪重試（上游最近一次錯誤：%s）",
                        label, f"HTTP {err.get('status')} {err.get('msg')}" if err else "無")
            return False
        missing = need - set(df.get("symbol", pd.Series(dtype=str)).astype(str))
        if missing:
            log.warning("%s 歷史只拿到部分代號，缺 %s —— 先寫進湖裡但不標 done，下一輪重試",
                        label, sorted(missing))
            store.append("index_ohlc", df)
            return False
        total += store.append("index_ohlc", df)

    prog.setdefault("complete", {})["index_ohlc"] = {
        "done": True, "start": start,
        "at": datetime.now(timezone.utc).isoformat(), "rows": total,
    }
    _save_progress(prog)
    log.info("指數歷史補完：寫入 %d 列（%s 起）", total, start)
    return True


FUT_TICK_DAYS = 60     # 台指期逐筆往回補幾個交易日（一天 1 次額度；60 天 ≈ 1H 300 根）


def backfill_index_intraday(prog: dict, days: int = FUT_TICK_DAYS) -> bool:
    """大盤三張圖 1H／4H 的一次性回補（2026-09-25）。

    ① 加權／櫃買：Yahoo 60 分補滿 730 天、15 分補滿 60 天（不吃 FinMind 額度）。
       每日管線湖空時也會自己補滿，這裡是讓回補那輪就先長出來。
    ② 台指期：FinMind TaiwanFuturesTick 逐日抓最近 `days` 個交易日（交易日取自 index_ohlc 的 FUT，
       不用執行當天推算），聚合成 60 分入湖。一天 1 次額度，額度剩 ≤ 5 就停，下一輪接續；
       已在湖裡的日子跳過，所以中斷重跑不會重花額度。
    全部補完記 `complete["index_intraday"]`。資料集沒權限（回空且有錯誤訊息）就記 `unavailable` 不再重試。
    """
    from .compute.intraday_bars import ticks_to_60m
    from .sources import yahoo

    from .compute.intraday_bars import kbar_to_60m

    flag = (prog.get("complete") or {}).get("index_intraday") or {}
    if flag.get("kbar_v") != 1:
        # 2026-09-25 加了 FinMind 分 K 路線（櫃買 TaiwanStockKBar、台指期 TaiwanFuturesKBar）：
        # 舊進度可能因為「逐筆不可用」就記成 done，這裡重開一次讓分 K 那兩條有機會補；Yahoo 那段不重跑。
        flag.pop("done", None)
        flag.pop("fut_unavailable", None)
        flag["kbar_v"] = 1
    if flag.get("done"):
        return True
    have = store.read("index_intraday")
    if not flag.get("yahoo"):
        n = 0
        for iv in ("60m", "15m"):
            n += store.append("index_intraday", yahoo.index_intraday_since(have, iv))
        log.info("指數分 K（Yahoo）回補寫入 %d 列", n)
        flag["yahoo"] = n > 0 or not have.empty
        have = store.read("index_intraday")

    if not flag.get("fut_unavailable"):
        dates = store.read("index_ohlc")
        dates = (sorted(dates.loc[dates["symbol"].astype(str) == "FUT", "date"].astype(str).unique())
                 if not dates.empty else [])[-days:]
        got = set()
        if not have.empty:
            fut = have[have["symbol"].astype(str) == "FUT"]
            got = set(fut["ts"].astype(str).str.slice(0, 10))
        todo = [d for d in dates if d not in got]
        for d in reversed(todo):          # 新的先補：最近的 1H 最有用
            if http.finmind_budget_left() <= 5:
                log.warning("額度剩不多，台指期逐筆回補停在 %s，下一輪接續", d)
                break
            bars = pd.DataFrame()
            if not flag.get("tick_unavailable"):
                bars = ticks_to_60m(finmind.futures_ticks(d))
                if bars.empty and _dataset_denied("TaiwanFuturesTick"):
                    flag["tick_unavailable"] = _err_text()
            if bars.empty:
                # 逐筆沒權限就試期貨分 K（2026-09 FinMind 新增的 TaiwanFuturesKBar）
                bars = kbar_to_60m(finmind.futures_kbar(d), futures=True)
                if bars.empty and _dataset_denied("TaiwanFuturesKBar"):
                    log.warning("台指期逐筆與分 K 都不可用（%s），記下來不再重試", _err_text())
                    flag["fut_unavailable"] = _err_text()
                    break
            if bars.empty:
                continue
            store.append("index_intraday", bars)
            todo = [x for x in todo if x != d]
        flag["fut_left"] = len(todo)
        fut_ok = not todo or bool(flag.get("fut_unavailable"))
    else:
        fut_ok = True

    otc_ok = _backfill_otc_kbar(flag, have, days)
    flag["done"] = bool(flag.get("yahoo")) and fut_ok and otc_ok
    flag["at"] = datetime.now(timezone.utc).isoformat()
    prog.setdefault("complete", {})["index_intraday"] = flag
    _save_progress(prog)
    return flag["done"]


def _dataset_denied(dataset: str) -> bool:
    """上一次 FinMind 請求是不是「這個資料集沒權限／不存在」（402/429 是額度，不算）。"""
    err = http.finmind_last_error() or {}
    return err.get("dataset") == dataset and err.get("status") not in (None, 402, 429)


def _err_text() -> str:
    err = http.finmind_last_error() or {}
    return f"{err.get('dataset')} {err.get('status')} {err.get('msg')}"[:200]


def _backfill_otc_kbar(flag: dict, have: pd.DataFrame, days: int) -> bool:
    """櫃買 60 分 K：Yahoo 沒有，改逐日抓 FinMind TaiwanStockKBar 聚合（2026-09-25）。回傳這段算不算完成。

    交易日取自 index_ohlc 的 OTC（回應裡的日期，不用執行當天推算）；湖裡已有的日子跳過；
    額度剩 ≤ 5 就停；所有候選代號都回「沒權限」就記 `otc_unavailable`，之後不再重試。
    """
    from .compute.intraday_bars import kbar_to_60m

    if flag.get("otc_unavailable"):
        return True
    dates = store.read("index_ohlc")
    dates = (sorted(dates.loc[dates["symbol"].astype(str) == "OTC", "date"].astype(str).unique())
             if not dates.empty else [])[-days:]
    got = set()
    if have is not None and not have.empty:
        otc = have[have["symbol"].astype(str) == "OTC"]
        got = set(otc["ts"].astype(str).str.slice(0, 10))
    todo = [d for d in dates if d not in got]
    ids = list(finmind.OTC_KBAR_IDS)
    empties = 0
    for d in reversed(todo):
        if http.finmind_budget_left() <= 5:
            log.warning("額度剩不多，櫃買分 K 回補停在 %s，下一輪接續", d)
            break
        bars = pd.DataFrame()
        denied = 0
        for data_id in ids:
            bars = kbar_to_60m(finmind.index_kbar(d, data_id), symbol="OTC")
            if not bars.empty:
                ids = [data_id]          # 找到能用的代號就只用它，後面的日子不再浪費額度
                break
            denied += _dataset_denied("TaiwanStockKBar")
        if bars.empty:
            if denied == len(ids):
                log.warning("櫃買分 K 不可用（%s），記下來不再重試", _err_text())
                flag["otc_unavailable"] = _err_text()
                return True
            empties += 1
            if empties >= 3 and not got and len(ids) > 1:
                # 代號不對時 FinMind 可能回 200 空陣列、沒有錯誤碼 —— 不設這道閘就會每小時燒一輪額度
                log.warning("櫃買分 K 連續 %d 個交易日所有代號都回空，視為不可用", empties)
                flag["otc_unavailable"] = f"連續 {empties} 個交易日回空（{_err_text()}）"
                return True
            continue
        store.append("index_intraday", bars)
        todo = [x for x in todo if x != d]
    flag["otc_left"] = len(todo)
    return not todo


def finmind_reachable(prog: dict) -> bool:
    """花 1 次額度確認「整把 token 還通不通」。

    為什麼要這一步（2026-09-19 的事故）
    ----------------------------------
    那天 revenue / financial / balance 連續好幾輪每一檔都回 400，
    日誌裡只寫「回 400，不重試」，所以沒有人分得出是
    ①「這三個資料集不開放」還是 ②「整把 token 失效／帳號等級被改」——
    而這兩種的修法完全不同（前者封印那三個資料集，後者要換金鑰）。
    於是每一輪都把 506 次額度燒在必定失敗的請求上，計畫永遠停在第 1 步。

    做法：先問一個最基本、免費層一定拿得到的東西（台積電最近 10 天的日線）。
    - 拿得到 → 是個別資料集的問題，照常跑，由封印機制處理。
    - 拿不到 → 不是資料集的問題，整輪直接停，把上游回應的原文寫進進度檔，
      讓下一個人（或 Andy）一眼看出要不要去 GitHub Secrets 換 token。
    """
    if http.finmind_budget_left() <= 1:
        return True          # 額度本來就沒了，健檢沒有意義，交給原本的限流流程
    since = (datetime.now(TAIPEI).date() - timedelta(days=CANARY_DAYS)).isoformat()
    try:
        df = finmind.price_history(CANARY_CODE, since, wait=False)
    except Exception as exc:  # noqa: BLE001
        df = None
        log.warning("FinMind 健檢拋出例外：%s", exc)
    ok = df is not None and not df.empty
    err = http.finmind_last_error() or {}
    prog["finmind_health"] = {
        "ok": ok,
        "at": _now().isoformat(),
        "probe": f"TaiwanStockPrice/{CANARY_CODE} since {since}",
        "detail": "" if ok else f"HTTP {err.get('status')}：{err.get('msg')}",
    }
    if not ok:
        log.error("FinMind 健檢失敗 —— 連 %s 最近 %d 天的日線都拿不到。"
                  "這不是某個資料集不開放，是整把 token／帳號的問題，本輪不再發任何請求。"
                  "上游回應：%s", CANARY_CODE, CANARY_DAYS,
                  prog["finmind_health"]["detail"] or "（沒有留下錯誤內容）")
        log.error("要處理的話：到 FinMind 網站重新產一把 token，"
                  "更新 GitHub Secrets 的 FINMIND_TOKEN，再手動觸發一次「歷史回補」。")
    _save_progress(prog)
    return ok


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
    prog0 = _progress()

    # ★ 第一件事是健檢：整把 token 不通的話，後面每一個請求都是白燒額度。
    #   2026-09-19 就是少了這一步，三輪各燒掉 506 次額度、一列都沒寫進來。
    if not finmind_reachable(prog0):
        return {"done": False, "steps": {}, "stopped_at": None, "exhausted": False,
                "finmind_down": True, **{k: 0 for k in DATA_KEYS}}

    # 指數歷史只要 3 次請求，放最前面：它一補完，總覽的月 K／季 K 與季節性的
    # 大盤基準就都有東西了，不必等後面幾千檔個股跑完。
    idx_ok = backfill_indices(prog0)
    # 大盤 1H／4H 的分 K（Yahoo 不吃額度；台指期逐筆一天 1 次）。失敗不擋後面的個股回補。
    try:
        backfill_index_intraday(_progress())
    except Exception as exc:  # noqa: BLE001
        log.warning("指數分 K 回補失敗（不影響其他步驟）：%s", exc)
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
        # 用 run() 算好的同一個判準，不要在這裡再寫一次（兩邊不一致過一次就夠了）
        results[key] = bool(summary.get("finished"))
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
    return {"done": all_done and idx_ok, "steps": {**results, "index_ohlc": idx_ok},
            "stopped_at": stopped_at,
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
        # 手動指定資料集也要先健檢：token 掛掉的話，逐檔跑只是在燒額度
        prog = _progress()
        if not finmind_reachable(prog):
            log.error("FinMind 不通，本輪不跑（原因見上一行與 backfill_progress.json 的 finmind_health）")
            return 0
        summary = run(args.datasets or "price+inst", limit, args.start)
    total = sum(summary[k] for k in DATA_KEYS)
    log.info("本輪共寫入 %d 列", total)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
