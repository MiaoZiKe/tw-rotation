"""每日三關稽核：有沒有執行 ／ 內容對不對 ／ 有沒有發布上去。

Andy 2026-11-09 原話：「目的是避免沒有發文 以及沒更新數據」。

2026-11-09 事故：盤前消息 08:22 已寫好、09:19 備援站已部署，主站（Cloudflare）卻停在 11-06，
因為 pages.yml 從 11-07 起沒再跑。沒有任何一個地方會紅燈，Andy 自己發現才補。
所以這支稽核的每一項都要回答三個問題，而且三個答案分開記：

  關卡一「有沒有執行」：對應的 workflow 有沒有跑、結論是不是 success。
  關卡二「內容對不對」：產出檔的日期＝今天／最近交易日、筆數 > 0、沒有 nan、資料日沒退回。
  關卡三「有沒有發布上去」：貼文有發布網址；網站兩個站（GitHub Pages＋Cloudflare 主站）都包含該 commit。

三種「不是失敗」的狀態要跟失敗分開（CLAUDE.md 紅線）：
  · skip     ：今天不該做（非交易日）→ 不檢查
  · disabled ：功能沒開（post_quota 沒開、沒設定）→ 未啟用，不是失敗
  · pending  ：還沒到截止時間 → 還沒到，不是失敗
  · fail     ：已過截止、任一關卡不過 → 真的沒完成
  · ok       ：三關都過

自動補救（保底，不准只回報）：每項每天最多補救一次，補救只是「派出 workflow」，
下一輪稽核會再驗證。發文類只補救「保留開著」的時段，被降量關掉的時段不補發。

用法：
  python scripts/daily_audit.py                 # 檢查並寫 data/_state/daily_audit.json（不補救）
  python scripts/daily_audit.py --remediate     # 同上，且對失敗項做一次性補救
  python scripts/daily_audit.py --now 2026-11-09T18:40:00+08:00   # 測試／重現用
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# 直接 `python scripts/daily_audit.py` 時 sys.path 只有 scripts/，要把 repo 根目錄加進來才 import 得到 pipeline
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
REPO = "MiaoZiKe/tw-rotation"
TPE = timezone(timedelta(hours=8))
HOLIDAYS_FILE = ROOT / "pipeline" / "calendar" / "tw_holidays.yaml"
AUDIT_FILE = ROOT / "data" / "_state" / "daily_audit.json"
METATOKEN_FILE = ROOT / "data" / "_state" / "meta_token.json"
LAST_RUN_FILE = ROOT / "data" / "_state" / "last_run.json"
SOURCE_HEALTH_FILE = ROOT / "data" / "_state" / "source_health.json"
QUOTA_FILE = ROOT / "docs" / "marketing" / "social_unit" / "post_quota.json"
HEALING_DIR = ROOT / "docs" / "marketing" / "channels" / "healing"
HEALING_QUOTA_FILE = HEALING_DIR / "post_quota.json"      # 頻道④自己的開關（不是頻道①的 post_quota）
HEALING_QUEUE_DIR = HEALING_DIR / "queue"
HEALING_POSTED_FILE = HEALING_DIR / "state" / "posted.json"  # 格式：{資料夾: {平台: {...}}}，deleted 代表已刪
TC_QUEUE_DIR = ROOT / "social" / "tc" / "queue"
TC_POSTED_FILE = ROOT / "state" / "tc" / "posted.json"    # tc_post.yml 直接 commit 到 main 的 state/tc/
ISSUE_TITLE = "⚠️ 每日稽核：有項目沒完成"

PRICE_CLOSE = time(15, 30)       # 台股收盤後，價量才會有當天
PRICE_DEADLINE = time(16, 15)    # 價量截止（Andy 11-09：16:15 前價量要進湖）
INST_DEADLINE = time(17, 15)     # 三大法人截止（inst 輪 16:15～17:15 搶當天法人）
DATA_DEADLINE = time(18, 40)     # 融資券／來源健康／畫面資料日的截止（18:30 那輪落地後留 10 分鐘）
# ETF（Andy 2026-11-09：「ETF 資訊也是否都有更新到」）。截止 21:40：full 輪 21:30 落地之後才算數。
# 成分股（投信 PCF）的基準日＝當天（2026-10-08 實測：晚上公告、基準日仍是當天），所以應有日＝價量應有日，不另加一天。
ETF_DEADLINE = time(21, 40)
ETF_HOLD_SRC = "etf_pcf.holdings"       # source_health 的鍵（run_daily 的 step 名稱）
ETF_NOTICE_SRC = "etf.exright_notice"
ETF_MONTH_TOLERANCE = 1                 # 月資料最多落後幾個月（公會月底後一兩週才齊，所以不要求當月）
TC_GRACE = timedelta(minutes=30)  # 排定時間過 30 分鐘還沒發，才算沒發
SOURCE_FAIL_RED = 2              # 來源連續失敗 2 天以上才算壞（1 天可能是 GitHub 排程延遲）
META_DAYS_RED = 7                # Meta 權杖剩 7 天以下就要續期
REMEDY_MAX_PER_DAY = 3           # 每項每天最多自動派幾次（含被佇列取代後的重派）
REMEDY_LOST_MIN = 10             # 派出後超過這分鐘還找不到對應的 run，視為派丟了
# 兩個站的線上資料檔（畫面實際讀的那一份；關卡三「畫面資料日期」用）
SITE_FILES = {"liguligu": "https://liguligu-puipui.com/data/",
              "gh_pages": "https://miaozike.github.io/tw-rotation/data/"}
GATE_NAMES = {"run": "執行", "content": "內容", "publish": "發布", "price": "價量", "inst": "三大法人",
              "margin": "融資券", "health": "來源與錯誤", "screen": "畫面資料日",
              "etf_hold": "ETF 成分股", "etf_notice": "ETF 除權息預告", "etf_month": "ETF 月資料",
              "etf_screen": "ETF 畫面日"}


# ---------------------------------------------------------------- 日曆
def load_holidays(path: Path = HOLIDAYS_FILE) -> set[str]:
    """休市日只取 days: 區塊裡 "YYYY-MM-DD": 那種行；註解與週末不在這裡。"""
    if not path.exists():
        return set()
    return set(re.findall(r'^\s+"(\d{4}-\d{2}-\d{2})":', path.read_text(encoding="utf-8"), re.M))


def is_trading_day(d: date, holidays: set[str]) -> bool:
    return d.weekday() < 5 and d.isoformat() not in holidays


def prev_trading_day(d: date, holidays: set[str]) -> date:
    x = d - timedelta(days=1)
    while not is_trading_day(x, holidays):
        x -= timedelta(days=1)
    return x


def expected_price_date(now: datetime, holidays: set[str]) -> date:
    """這一刻「應該已經有」的價量日：交易日 15:30 之後是今天，其餘是前一個交易日。
    用台北時間，不用執行環境的 UTC；也不用 GitHub 排程的時間（排程會延遲）。"""
    d = now.astimezone(TPE).date()
    if is_trading_day(d, holidays) and now.astimezone(TPE).time() >= PRICE_CLOSE:
        return d
    return prev_trading_day(d, holidays)


def at_tpe(d: date, hhmm: time) -> datetime:
    return datetime.combine(d, hhmm, tzinfo=TPE)


# ---------------------------------------------------------------- 小工具
def gate(ok: bool | None, why: str, evidence: list[str] | None = None, busy: bool = False,
         hard: bool = False) -> dict:
    """ok=None 代表「查不到」，當作不過（不准把查不到當成綠燈）。
    busy=True 代表「正在進行中」（例如 pages.yml 部署中），這種不過是還沒到，不是壞掉。
    hard=True 代表「不等截止，不過就紅」（price／full 輪已經失敗且之後沒有成功的一輪）。"""
    return {"ok": bool(ok), "why": why, "evidence": evidence or [], "busy": busy, "hard": hard}


def runs_since(runs: list[dict], since: datetime) -> list[dict]:
    out = []
    for r in runs or []:
        try:
            created = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        if created >= since:
            out.append(r)
    return out


def run_gate(runs: list[dict], since: datetime, label: str) -> dict:
    """關卡一：窗口內有沒有 success 的 run。有 in_progress 不算失敗，由呼叫端判成 pending。"""
    hits = runs_since(runs, since)
    ok_runs = [r for r in hits if r.get("conclusion") == "success"]
    if ok_runs:
        return gate(True, f"{label} 今天有成功執行 {len(ok_runs)} 次",
                    [r.get("html_url", "") for r in ok_runs[:3]])
    if any(r.get("status") in ("queued", "in_progress") for r in hits):
        return gate(False, f"{label} 正在執行中（還沒跑完）", [])
    bad = [r.get("html_url", "") for r in hits[:3]]
    return gate(False, f"{label} 窗口內沒有成功的執行（找到 {len(hits)} 次）", bad)


def is_round(r: dict, holidays: set[str]) -> bool:
    """這一則 daily.yml 執行是不是「價量／全量」輪（price／full）。
    · run-name 帶 phase 字樣（手動派的）：看標題。
    · 排程沒有 phase 字樣：看「跑指標庫測試」那一步有沒有被跳過。法人輪（inst）的 cron 會把它跳過
      （daily.yml 的 if 條件就是這樣寫的），跳過＝法人輪，不算價量輪。
    · 排程的新聞輪在週末也會跑，不算價量輪：排程只看交易日。"""
    title = str(r.get("display_title") or r.get("name") or "")
    if "(inst)" in title or "(news)" in title:
        return False
    if "(price)" in title or "(full)" in title:
        return True
    steps = r.get("_steps")
    if steps is not None and any(s.get("name") == "跑指標庫測試" and s.get("conclusion") == "skipped"
                                 for s in steps):
        return False
    if r.get("event", "schedule") == "schedule":
        created = _parse_ts(r.get("created_at"))
        if created is None or not is_trading_day(created.astimezone(TPE).date(), holidays):
            return False
    return True


def round_gate(runs, since: datetime, label: str, holidays: set[str]) -> dict:
    """關卡一（每日資料專用）：窗口內的 price／full 輪。
    · 有執行中的 → 還沒跑完（busy，不紅）。
    · 最近一次失敗之後沒有成功的一輪 → 紅（hard，不等截止）；附失敗網址與失敗步驟名稱。
    · 成功在最近一次失敗之後 → 綠（失敗後重跑成功就算數）。
    · 都沒有 → 不過；截止前是還沒到，截止後才是沒跑。"""
    if runs is None:
        return gate(None, f"查不到 {label} 執行紀錄")
    hits = [r for r in runs_since(runs, since) if is_round(r, holidays)]

    def ts(r: dict) -> datetime:
        return _parse_ts(r.get("created_at")) or since

    running = [r for r in hits if r.get("status") in ("queued", "in_progress")]
    if running:
        return gate(False, f"{label} price／full 輪正在執行中（還沒跑完）",
                    [r.get("html_url", "") for r in running[:2]], busy=True)
    succ = [r for r in hits if r.get("conclusion") == "success"]
    fails = [r for r in hits if r.get("conclusion") in ("failure", "timed_out")]
    last_fail = max(fails, key=ts) if fails else None
    last_succ = max(succ, key=ts) if succ else None
    if last_succ and (last_fail is None or ts(last_succ) > ts(last_fail)):
        return gate(True, f"{label} 今天有成功的 price／full 輪 {len(succ)} 次", [last_succ.get("html_url", "")])
    if last_fail:
        bad_steps = [s.get("name", "") for s in (last_fail.get("_steps") or []) if s.get("conclusion") == "failure"]
        return gate(False, f"{label} price／full 輪失敗（失敗步驟：{'、'.join(bad_steps) or '未知，看網址'}），"
                           f"之後沒有成功的一輪",
                    [last_fail.get("html_url", "")], hard=True)
    return gate(False, f"{label} 今天還沒有成功的 price／full 輪")


def screen_gate(screen: dict | None, exp_s: str) -> dict:
    """關卡三補充（畫面）：兩個站各自的「總覽」（meta.json 的 data_date／inst_date）與
    「三大法人頁」（inst_market.json 的 latest）都要等於應有日。讀不到就是不過，不准當綠。
    兩站各自的日期都寫進說明，Andy 一眼看得出是哪一站落後。"""
    if not screen:
        return gate(None, "查不到兩站線上資料檔")
    parts, ok = [], True
    for key, label in (("liguligu", "主站"), ("gh_pages", "備援")):
        s = screen.get(key) or {}
        if s.get("error") or s.get("data_date") is None:
            ok = False
            parts.append(f"{label}讀不到（{s.get('error') or '沒有 data_date'}）")
            continue
        dd, idt, im = s.get("data_date"), s.get("inst_date"), s.get("inst_market_latest")
        ok = ok and dd == exp_s and idt == exp_s and im == exp_s
        parts.append(f"{label}：總覽 {dd}／法人 {idt}／三大法人頁 {im}")
    return gate(ok, "；".join(parts) + f"（應有 {exp_s}）")


def etf_holdings_gate(lake_date: str | None, health: dict | None, exp_s: str) -> dict:
    """ETF 成分股（投信 PCF）：湖裡最新基準日要 ≥ 應有日，而且 source_health 的最後成功日也要 ≥ 應有日。
    兩個都要看：湖裡有、但來源紀錄停在前一天，代表最後一次抓取失敗（11-06 那次就是這樣：湖停在 11-05）。"""
    if lake_date is None or health is None:
        return gate(None, "查不到 ETF 成分股（資料湖或 source_health）")
    h = health.get(ETF_HOLD_SRC) or {}
    last_ok = h.get("last_ok_date")
    ok = lake_date >= exp_s and last_ok is not None and last_ok >= exp_s
    return gate(ok, f"ETF 成分股湖內最新 {lake_date}、來源最後成功 {last_ok or '無'}、"
                    f"連續失敗 {int(h.get('consecutive_fail') or 0)} 天（應有 {exp_s}）",
                [SOURCE_HEALTH_FILE.name])


def etf_notice_gate(health: dict | None, exp_s: str) -> dict:
    """ETF 除權息預告：不看湖（湖裡的日期是除息日，不是抓到的日期），只看 source_health 的最後成功日。
    端點回應但當天沒有 ETF 列是正常的，那種情況 raw_ok 仍為 true，last_ok_date 照樣會前進。"""
    if health is None:
        return gate(None, "查不到 source_health")
    h = health.get(ETF_NOTICE_SRC) or {}
    last_ok = h.get("last_ok_date")
    ok = last_ok is not None and last_ok >= exp_s
    return gate(ok, f"ETF 除權息預告來源最後成功 {last_ok or '無'}、連續失敗 {int(h.get('consecutive_fail') or 0)} 天"
                    f"（應有 {exp_s}）", [SOURCE_HEALTH_FILE.name])


def _month_index(ym: str) -> int:
    y, m = int(ym[:4]), int(ym[5:7])
    return y * 12 + m - 1


def etf_monthly_gate(lake_month_end: str | None, exp_s: str) -> dict:
    """公會每月前十大（月資料）：應有最新完整月＝應有日的上一個月；最新月落後不超過 ETF_MONTH_TOLERANCE 個月才算過。
    月資料不做每日紅燈：當月還沒齊、上個月也還沒齊，都還在容忍範圍內。"""
    if lake_month_end is None:
        return gate(None, "查不到 ETF 月資料（etf_holdings_monthly）")
    exp = date.fromisoformat(exp_s)
    last_full = _month_index(f"{exp.year:04d}-{exp.month:02d}") - 1
    lag = last_full - _month_index(lake_month_end)
    ok = lag <= ETF_MONTH_TOLERANCE
    return gate(ok, f"ETF 月資料最新 {lake_month_end[:7]}，落後 {max(lag, 0)} 個月（容許 {ETF_MONTH_TOLERANCE}）")


def etf_screen_gate(screen: dict | None, exp_s: str) -> dict:
    """ETF 畫面日：兩個站各自的 etf.json（價量日）與 etf_holdings.json（成分股基準日）都要 ＝ 應有日。
    讀不到就是不過（不准當綠），兩站各自的日期都寫進說明。"""
    if not screen:
        return gate(None, "查不到兩站線上 ETF 檔")
    parts, ok = [], True
    for key, label in (("liguligu", "主站"), ("gh_pages", "備援")):
        s = screen.get(key) or {}
        if s.get("etf_error") or s.get("etf_asof") is None or s.get("etf_hold_asof") is None:
            ok = False
            parts.append(f"{label}讀不到 ETF 檔（{s.get('etf_error') or '沒有 asof'}）")
            continue
        a, h = s["etf_asof"], s["etf_hold_asof"]
        ok = ok and a == exp_s and h == exp_s
        parts.append(f"{label}：ETF 頁 {a}／成分股 {h}")
    return gate(ok, "；".join(parts) + f"（應有 {exp_s}）")


def bad_text(s: str) -> bool:
    return (not s) or s.strip().lower() in {"nan", "none", "null"}


# ---------------------------------------------------------------- 事實蒐集（唯一有 I/O 的地方）
def http_json(url: str, timeout: int = 20):
    """線上資料檔（加時間戳防快取）。失敗丟例外，由呼叫端記成「讀不到」，不准當綠。"""
    sep = "&" if "?" in url else "?"
    req = urllib.request.Request(f"{url}{sep}t={int(datetime.now(TPE).timestamp())}",
                                 headers={"Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 - 固定網址
        return json.loads(r.read().decode("utf-8"))


def collect_screen(http) -> dict:
    """畫面實際讀的資料日：總覽讀 meta.json（data_date、inst_date），三大法人頁讀 inst_market.json（latest）。
    ETF 頁讀 etf.json（頂層 asof＝價量日），成分股分頁讀 etf_holdings.json（頂層 asof＝基準日）。
    ETF 的讀取與上面分開 try：ETF 檔讀不到不能把總覽／法人的判定也連帶弄成「讀不到」。"""
    out: dict = {}
    for key, base in SITE_FILES.items():
        s: dict = {"data_date": None, "inst_date": None, "inst_market_latest": None, "error": None,
                   "etf_asof": None, "etf_hold_asof": None, "etf_error": None}
        try:
            meta = http(base + "meta.json") or {}
            s["data_date"] = meta.get("data_date")
            s["inst_date"] = meta.get("inst_date")
            s["inst_market_latest"] = (http(base + "inst_market.json") or {}).get("latest")
        except Exception as e:  # noqa: BLE001 - 讀不到就記下來，關卡判不過
            s["error"] = str(e)[:200]
        try:
            s["etf_asof"] = (http(base + "etf.json") or {}).get("asof")
            s["etf_hold_asof"] = (http(base + "etf_holdings.json") or {}).get("asof")
        except Exception as e:  # noqa: BLE001
            s["etf_error"] = str(e)[:200]
        out[key] = s
    return out


def collect_facts(now: datetime, holidays: set[str], gh, http=None) -> dict:
    """gh(path) → 解析後的 JSON；gh_raw(path) → 純文字。失敗由呼叫端決定要不要紅。"""
    http = http or http_json
    today = now.astimezone(TPE).date()
    expected = expected_price_date(now, holidays)
    f: dict = {
        "now": now.astimezone(TPE).isoformat(timespec="seconds"),
        "today": today.isoformat(),
        "expected_price": expected.isoformat(),
        "holidays": holidays,
    }
    # 工作流執行紀錄
    f["runs"] = {}
    for wf in ("daily.yml", "social-live.yml", "article-jobs.yml", "tc_post.yml",
               "healing_post.yml", "pages.yml", "meta_token_refresh.yml"):
        try:
            f["runs"][wf] = gh(f"repos/{REPO}/actions/workflows/{wf}/runs?per_page=50").get("workflow_runs", [])
        except Exception as e:  # noqa: BLE001 - 查不到就記下來，由關卡判 None
            f["runs"][wf] = None
            f.setdefault("errors", []).append(f"查 {wf} 失敗：{e}")

    # 今天 15:00 後的 daily.yml 每一則，要看步驟（區分 price／full 與法人輪；失敗要附失敗步驟名稱）。
    # 只抓窗口內的，省 API。
    since_round = at_tpe(expected, time(15, 0))
    for r in f["runs"].get("daily.yml") or []:
        created = _parse_ts(r.get("created_at"))
        if created is None or created < since_round:
            continue
        try:
            jobs = gh(f"repos/{REPO}/actions/runs/{r['id']}/jobs").get("jobs", [])
            r["_steps"] = [s for j in jobs for s in j.get("steps", [])]
        except Exception as e:  # noqa: BLE001 - 查不到步驟就記下來，失敗名稱會寫「未知」
            r["_steps"] = None
            f.setdefault("errors", []).append(f"查 daily.yml run {r.get('id')} 的步驟失敗：{e}")

    # 本機（CI 裡是 checkout 出來的 main）
    f["premarket"] = _read_json(ROOT / "site" / "articles" / "premarket.json")
    f["postmarket"] = _read_json(ROOT / "site" / "articles" / "postmarket.json")
    f["last_run"] = _read_json(LAST_RUN_FILE)
    f["source_health"] = _read_json(SOURCE_HEALTH_FILE)
    f["meta"] = _read_json(METATOKEN_FILE)
    f["quota"] = _read_json(QUOTA_FILE)
    f["healing_posted"] = _read_json(HEALING_POSTED_FILE)
    f["healing_quota"] = _read_json(HEALING_QUOTA_FILE)
    f["healing_queue"] = _read_healing_queue()
    f["tc_queue"] = _read_tc_queue()
    f["tc_posted"] = _read_json(TC_POSTED_FILE)  # 找不到＝None＝查不到，不是空紀錄

    # 資料湖最新日（pipeline 只在 CI／本機有 pandas 時讀；讀不到就是 None＝查不到）
    f["lake"] = {}
    try:  # 讀不到就是 None，關卡會判「查不到」而不是綠
        from pipeline.util import store
        for t in ("price_daily", "inst_daily", "inst_market_daily", "margin_total",
                  "etf_holdings", "etf_holdings_monthly"):
            f["lake"][t] = store.latest_date(t)
    except Exception as e:  # noqa: BLE001
        f.setdefault("errors", []).append(f"讀資料湖失敗：{e}")

    # 社群發布紀錄（在 social-snaps 分支）
    f["snaps_posted"] = _gh_json_or_none(gh, "state/posted.json")

    # 網站部署：GitHub Pages ＋ Cloudflare 主站
    f["site"] = collect_site(gh)
    # 畫面資料日（關卡三）：兩個站各自讀到的日期，直接從線上資料檔看
    f["screen"] = collect_screen(http)
    return f


def _read_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _read_healing_queue() -> list[dict]:
    out = []
    for p in sorted(HEALING_QUEUE_DIR.glob("*/meta.json")) if HEALING_QUEUE_DIR.exists() else []:
        m = _read_json(p) or {}
        out.append({"slug": p.parent.name, "status": m.get("status", ""),
                    "platforms": list(m.get("platforms") or []), "publish_at": m.get("publish_at")})
    return out


def _read_tc_queue() -> list[dict]:
    out = []
    for p in sorted(TC_QUEUE_DIR.glob("*/post.md")) if TC_QUEUE_DIR.exists() else []:
        text = p.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---", text, re.S)
        meta = {}
        for line in (m.group(1).splitlines() if m else []):
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        out.append({"slug": p.parent.name, "status": meta.get("status", ""),
                    "scheduled_at": meta.get("scheduled_at", ""), "file": str(p.relative_to(ROOT))})
    return out


def _gh_json_or_none(gh, path: str):
    """social-snaps 分支上的 JSON。找不到＝None（查不到），不是空的。"""
    try:
        raw = gh(f"repos/{REPO}/contents/{path}?ref=social-snaps", raw=True)
        return json.loads(raw)
    except Exception:  # noqa: BLE001
        return None


def collect_site(gh) -> dict:
    """網站兩個站各自部署到哪個 commit。
    · 必須包含的 commit ＝ main 上最新一次「資料更新」或「網站／管線改動」的 commit（取較新者）。
    · GitHub Pages：environment=github-pages 最近一筆 success 的 deployment 的 sha。
    · Cloudflare 主站：pages.yml 在 main 上最近一筆 success、且「雙部署到 Cloudflare Pages（主站）」那步 success 的 run。"""
    out: dict = {"required": None, "gh_pages": None, "cf": None, "pending": False, "errors": []}
    try:
        a = gh(f"repos/{REPO}/commits?path=data/_state/last_run.json&per_page=1")
        b = gh(f"repos/{REPO}/commits?path=site/articles/premarket.json&per_page=1")
        cands = [c for c in (a + b) if c]
        cands.sort(key=lambda c: c["commit"]["committer"]["date"], reverse=True)
        out["required"] = cands[0]["sha"] if cands else None
    except Exception as e:  # noqa: BLE001
        out["errors"].append(f"查 main 最新資料 commit 失敗：{e}")
    try:
        deps = gh(f"repos/{REPO}/deployments?environment=github-pages&per_page=5")
        for d in deps:
            st = gh(f"repos/{REPO}/deployments/{d['id']}/statuses?per_page=1")
            if st and st[0].get("state") == "success":
                out["gh_pages"] = d["sha"]
                break
    except Exception as e:  # noqa: BLE001
        out["errors"].append(f"查 GitHub Pages 部署失敗：{e}")
    try:
        runs = gh(f"repos/{REPO}/actions/workflows/pages.yml/runs?branch=main&per_page=8").get("workflow_runs", [])
        live = [r for r in runs if r.get("status") in ("queued", "in_progress")]
        if live:
            out["pending"] = True
            out["pending_since"] = min(r["created_at"] for r in live)
        for r in runs:
            if r.get("conclusion") != "success":
                continue
            jobs = gh(f"repos/{REPO}/actions/runs/{r['id']}/jobs").get("jobs", [])
            steps = [s for j in jobs for s in j.get("steps", [])]
            cf_ok = any(s.get("name", "").startswith("雙部署到 Cloudflare Pages（主站）")
                        and s.get("conclusion") == "success" for s in steps)
            if cf_ok:
                out["cf"] = r["head_sha"]
                break
    except Exception as e:  # noqa: BLE001
        out["errors"].append(f"查 pages.yml／Cloudflare 失敗：{e}")
    return out


def site_gate(site: dict, compare_fn, now: datetime) -> dict:
    """關卡三（網站）：兩個站都要包含必須的 commit；主站不可比備援站舊。compare_fn(base, head) → status。
    部署中：一小時內是還沒到（busy）；超過一小時還沒跑完，才當失敗（卡住）。"""
    req = site.get("required")
    if site.get("pending"):
        started = _parse_ts(site.get("pending_since"))
        if started and now - started > timedelta(hours=1):
            return gate(False, "pages.yml 已經在部署中超過一小時，疑似卡住")
        return gate(False, "pages.yml 正在部署中（還沒跑完）", busy=True)
    if not req:
        return gate(None, "查不到 main 上最新資料 commit")
    res = {}
    for key, label in (("gh_pages", "GitHub Pages（備援）"), ("cf", "Cloudflare 主站")):
        sha = site.get(key)
        if not sha:
            res[key] = (False, f"{label} 查不到成功的部署")
            continue
        st = compare_fn(req, sha)  # identical／ahead＝部署的版本包含 req
        res[key] = (st in ("identical", "ahead"), f"{label} 部署到 {sha[:7]}，" +
                    ("已包含最新資料" if st in ("identical", "ahead") else "還沒包含最新資料"))
    ok = all(v[0] for v in res.values())
    why = "；".join(v[1] for v in res.values())
    if ok and site.get("gh_pages") and site.get("cf"):
        # compare(cf, gh)＝gh 比 cf 新 → 主站落後於備援
        st = compare_fn(site["cf"], site["gh_pages"])
        if st == "ahead":
            ok, why = False, why + "；主站比備援站舊"
    return gate(ok, why, [site.get("gh_pages") or "", site.get("cf") or ""])


# ---------------------------------------------------------------- 三關（純函式，可測）
def _parse_ts(stamp):
    try:
        return datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except ValueError:
        return None


def _within(stamp: str | None, now: datetime, span: timedelta) -> bool:
    try:
        t = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except ValueError:
        return False
    return now - span <= t <= now + timedelta(minutes=5)


def due(now: datetime, when: datetime) -> bool:
    return now.astimezone(TPE) >= when


def evaluate(f: dict, holidays: set[str], site_result: dict, now: datetime) -> list[dict]:
    """依事實算出每一項三關。site_result＝site_gate() 的結果（網站關卡共用）。"""
    today = date.fromisoformat(f["today"])
    expected = date.fromisoformat(f["expected_price"])
    trading_today = is_trading_day(today, holidays)
    quota = f.get("quota") or {}
    live = quota.get("live") or {}
    today_start = at_tpe(today, time(0, 0))
    items: list[dict] = []

    def finish(id_, name, applies, deadline: datetime | None, gates: dict, disabled: str | None = None,
               remedy=None):
        """deadline＝None 代表隨時都要過（沒有截止時間）；過了截止時間仍不過才是 fail。"""
        if not applies:
            items.append({"id": id_, "name": name, "status": "skip", "gates": {}, "why": "今天不該做（非交易日）"})
            return
        if disabled:
            items.append({"id": id_, "name": name, "status": "disabled", "gates": {}, "why": disabled})
            return
        # 每個 gate 用自己的截止（沒帶就用 item 的）。hard＝不等截止，不過就紅。
        # busy＝進行中（例如部署中）＝還沒到；但同時有 hard 失敗，仍然紅。
        over, busy_any, hard_bad, pend = [], False, False, False
        for k, g in gates.items():
            if g["ok"]:
                continue
            if g.get("busy"):
                busy_any = True
                continue
            dl = g.get("deadline") or deadline
            if g.get("hard"):
                hard_bad = True
                over.append(k)
            elif dl is None or due(now, dl):
                over.append(k)
            else:
                pend = True
        if hard_bad or (over and not busy_any):
            status = "fail"
        elif over or pend or busy_any:
            status = "pending"
        else:
            status = "ok"
        items.append({"id": id_, "name": name, "status": status, "gates": gates,
                      "deadline": deadline.isoformat() if deadline else None,
                      "remedy": remedy if status == "fail" else None})

    # 盤前消息：交易日 08:40 前要有今天的盤前
    pm = f.get("premarket") or {}
    pm_day = (pm.get("days") or [{}])[0]
    pm_items = pm_day.get("items") or []
    pm_content = gate(pm_day.get("date") == f["today"] and len(pm_items) > 0 and
                      not any(bad_text(i.get("title", "")) or bad_text(i.get("url", "")) for i in pm_items),
                      f"盤前消息日期 {pm_day.get('date')}、{len(pm_items)} 則",
                      [pm.get("updated", "")])
    finish("premarket", "盤前消息（交易日 08:40 前）", trading_today, at_tpe(today, time(8, 40)), {
        "run": run_gate(f["runs"].get("social-live.yml") or [], today_start, "social-live"),
        "content": pm_content,
        "publish": site_result["site"],
    }, remedy={"action": "dispatch", "workflow": "social-live.yml",
               "inputs": {"kind": "premarket", "dry_run": "false", "force": "false"}})

    # 盤後消息：交易日 21:40 前要有今天的盤後（daily.yml 裡的 postmarket_news 產出）
    po = f.get("postmarket") or {}
    po_day = (po.get("days") or [{}])[0]
    po_items = po_day.get("items") or []
    po_content = gate(po_day.get("date") == f["today"] and len(po_items) > 0,
                      f"盤後消息日期 {po_day.get('date')}、{len(po_items)} 則", [po.get("updated", "")])
    finish("postmarket", "盤後消息（交易日 21:40 前）", trading_today, at_tpe(today, time(21, 40)), {
        "run": run_gate(f["runs"].get("daily.yml") or [], at_tpe(today, time(15, 0)), "daily.yml"),
        "content": po_content,
        "publish": site_result["site"],
    }, remedy={"action": "dispatch", "workflow": "daily.yml", "inputs": {"phase": "full"}})

    # 每日資料更新：分段截止（Andy 11-09：16:15 要有價量、17:15 要有法人，畫面也要跟上）。
    # 價量 16:15、法人 17:15、融資券／來源健康／畫面資料日 18:40；截止前不過＝還沒到，不紅。
    # price／full 輪失敗是例外：不等截止，之後沒有成功的一輪就紅（11-09 那天 15:38 起連續失敗，
    # Andy 16:53 才自己發現）。截止錨在「應有日」而不是今天，所以週末查週五的資料也是同一套規則。
    lake = f.get("lake") or {}
    last = f.get("last_run") or {}
    sh = f.get("source_health") or {}
    bad_src = sorted(k for k, v in sh.items() if isinstance(v, dict) and (v.get("consecutive_fail") or 0) >= SOURCE_FAIL_RED)
    exp_s = expected.isoformat()

    def by(g: dict, hh: time) -> dict:
        g["deadline"] = at_tpe(expected, hh)
        return g

    price_g = by(gate(lake.get("price_daily") == exp_s, f"價量 {lake.get('price_daily')}（應有 {exp_s}）"),
                 PRICE_DEADLINE)
    inst_g = by(gate((lake.get("inst_daily") or "") >= exp_s, f"三大法人 {lake.get('inst_daily')}（應有 {exp_s}）"),
                INST_DEADLINE)
    margin_g = by(gate((lake.get("margin_total") or "") >= exp_s,
                       f"融資券 {lake.get('margin_total')}（應有 {exp_s}）"), DATA_DEADLINE)
    health_g = by(gate(not (last.get("errors") or []) and not bad_src,
                       f"last_run 錯誤 {len(last.get('errors') or [])} 筆；連續失敗來源 {bad_src or '無'}",
                       [LAST_RUN_FILE.name, SOURCE_HEALTH_FILE.name]), DATA_DEADLINE)
    screen_g = by(screen_gate(f.get("screen"), exp_s), DATA_DEADLINE)
    run_g = by(round_gate(f["runs"].get("daily.yml"), at_tpe(expected, time(15, 0)), "daily.yml", holidays),
               PRICE_DEADLINE)
    # 網站那一項的「內容」沿用同一套（價量／法人／融資券／來源健康）
    data_content = gate(all(g["ok"] for g in (price_g, inst_g, margin_g, health_g)),
                        "價量／法人／融資券／來源健康（同每日資料關卡）")
    # ETF 四關（各自 21:40 截止；未到截止＝還沒到，不紅）。成分股與除權息預告是 full 輪的產出，
    # 所以補救也是派 daily.yml phase=full（同一個補救，不另開）。
    etf_hold_g = by(etf_holdings_gate(lake.get("etf_holdings"), f.get("source_health"), exp_s), ETF_DEADLINE)
    etf_notice_g = by(etf_notice_gate(f.get("source_health"), exp_s), ETF_DEADLINE)
    etf_month_g = by(etf_monthly_gate(lake.get("etf_holdings_monthly"), exp_s), ETF_DEADLINE)
    etf_screen_g = by(etf_screen_gate(f.get("screen"), exp_s), ETF_DEADLINE)
    finish("data", "每日資料更新（價量／法人／融資券／ETF）", True, at_tpe(expected, DATA_DEADLINE), {
        "run": run_g, "price": price_g, "inst": inst_g, "margin": margin_g,
        "health": health_g, "screen": screen_g,
        "etf_hold": etf_hold_g, "etf_notice": etf_notice_g, "etf_month": etf_month_g,
        "etf_screen": etf_screen_g,
        "publish": site_result["site"],
    }, remedy={"action": "dispatch", "workflow": "daily.yml", "inputs": {"phase": "full"}})

    # 頻道①盤後主貼文（只在 post_quota 的 close 開著時檢查）
    close_on = bool((live.get("close") or {}).get("threads") or (live.get("close") or {}).get("ig_story"))
    posted = f.get("snaps_posted")
    key = f"close-{f['today']}"
    entry = (posted or {}).get(key) if isinstance(posted, dict) else None
    links = []
    if entry:
        if isinstance(entry.get("threads"), dict):
            links.append(entry["threads"].get("link", ""))
        for s in entry.get("story") or []:
            links.append(s.get("link", ""))
    links = [x for x in links if x]
    finish("close_post", "頻道①盤後主貼文（交易日 18:20 前）", trading_today, at_tpe(today, time(18, 20)), {
        "run": run_gate(f["runs"].get("social-live.yml") or [], at_tpe(today, time(15, 0)), "social-live"),
        "content": gate(entry is not None, f"posted.json 有 {key}" if entry else f"posted.json 沒有 {key}"),
        "publish": gate(bool(links), "有發布網址" if links else "沒有發布網址（查不到或沒發出）", links[:3]),
    } if posted is not None else {
        "run": run_gate(f["runs"].get("social-live.yml") or [], at_tpe(today, time(15, 0)), "social-live"),
        "content": gate(None, "查不到 social-snaps state/posted.json"),
        "publish": gate(None, "查不到發布紀錄"),
    }, disabled=None if close_on else "未啟用（post_quota.json 的 close 沒開，不是失敗）",
        remedy={"action": "dispatch", "workflow": "social-live.yml",
                "inputs": {"kind": "close", "dry_run": "false", "force": "false"}})

    # 頻道④談晴說礙：healing 自己的開關（live 必須是 true，否則整個停發＝未啟用）。
    # 今天該發的 ＝ 佇列裡 status: approved，且 publish_at（null＝當天 20:27 的時段）已到。
    # 發布紀錄 ＝ healing/state/posted.json 的 {資料夾: {平台: {...}}}，每個平台都要有紀錄且沒被刪。
    heal_on = (f.get("healing_quota") or {}).get("live") is True
    hp = f.get("healing_posted")
    heal_due = []
    for q in f.get("healing_queue") or []:
        if q["status"] != "approved":
            continue
        due_at = _parse_ts(q.get("publish_at")) or at_tpe(today, time(20, 27))
        if now >= due_at:
            heal_due.append(q)

    def _posted_ok(slug: str, plat: str) -> bool:
        rec = ((hp or {}).get(slug) or {}).get(plat) if isinstance(hp, dict) else None
        return bool(rec) and not rec.get("deleted")

    if not heal_due:
        heal_gates = {"run": gate(True, "沒有已到時間的核准稿，不需要發"), "content": gate(True, "無"),
                      "publish": gate(True, "無")}
    elif hp is None:
        heal_gates = {"run": run_gate(f["runs"].get("healing_post.yml") or [], today_start, "healing_post"),
                      "content": gate(None, "查不到 healing/state/posted.json"),
                      "publish": gate(None, "查不到發布紀錄")}
    else:
        unposted = [f"{q['slug']}（缺 {'、'.join(p for p in q['platforms'] if not _posted_ok(q['slug'], p))}）"
                    for q in heal_due if any(not _posted_ok(q["slug"], p) for p in q["platforms"])]
        links = []
        for q in heal_due:
            for p in q["platforms"]:
                rec = ((hp or {}).get(q["slug"]) or {}).get(p) or {}
                if rec.get("link"):
                    links.append(rec["link"])
        heal_gates = {
            "run": run_gate(f["runs"].get("healing_post.yml") or [], today_start, "healing_post"),
            "content": gate(all(q["platforms"] for q in heal_due),
                            "已到時間的核准稿：" + "、".join(q["slug"] for q in heal_due), [str(HEALING_QUEUE_DIR.name)]),
            "publish": gate(not unposted, "未發布：" + "、".join(unposted) if unposted else "各平台都有發布紀錄",
                            links[:3]),
        }
    finish("healing", "頻道④談晴說礙（核准稿到時間就要發）", True, at_tpe(today, time(21, 40)), heal_gates,
           disabled=None if heal_on else "未啟用（healing/post_quota.json 的 live 不是 true，整個停發，不是失敗）",
           remedy={"action": "dispatch", "workflow": "healing_post.yml",
                   "inputs": {"mode": "post", "dry_run": "false"}})

    # 頻道②科技透明圈：approved 且排定時間已過 30 分鐘，就必須是 posted
    tc_on = bool((quota.get("tc") or {}).get("enabled"))
    due_tc, pending_tc = [], []
    for p in f.get("tc_queue") or []:
        if p["status"] != "approved":
            continue
        try:
            sched = datetime.fromisoformat(p["scheduled_at"])
        except ValueError:
            due_tc.append(p["slug"] + "（scheduled_at 格式錯）")
            continue
        (due_tc if now >= sched + TC_GRACE else pending_tc).append(p["slug"])
    tc_posted_ids = f.get("tc_posted") if f.get("tc_posted") is not None else {}
    tc_content_bad = due_tc
    if not due_tc and not pending_tc:
        tc_gates = {"run": gate(True, "沒有核准待發的稿，不需要發"), "content": gate(True, "無"),
                    "publish": gate(True, "無")}
    else:
        tc_gates = {
            "run": run_gate(f["runs"].get("tc_post.yml") or [], today_start, "tc_post") if due_tc else gate(True, "排定時間未到"),
            "content": gate(not tc_content_bad, "已排定時間的核准稿：" + ("、".join(due_tc) or "無"),
                            [p["file"] for p in f.get("tc_queue") or []][:3]),
            "publish": gate(not due_tc or all(s in json.dumps(tc_posted_ids, ensure_ascii=False) for s in due_tc),
                            "發布紀錄" + ("齊全" if not due_tc else "有缺")),
        }
    # 頻道②是「排定時間到了就發」，不分交易日，所以每天都檢查
    finish("tc", "頻道②科技透明圈（排定時間到了就要發）", True, None, tc_gates,
           disabled=None if tc_on else "未啟用（post_quota.json 的 tc.enabled 不是 true）",
           remedy=None)

    # Meta 權杖：剩 7 天以下或驗證失敗就要續期
    m = f.get("meta") or {}
    plats = m.get("platforms") or {}
    worst = []
    for name, p in plats.items():
        dl = p.get("days_left")
        if not p.get("ok") or dl is None or dl < META_DAYS_RED:
            worst.append(f"{name} 剩 {dl} 天／ok={p.get('ok')}")
    finish("meta", "Meta 權杖（剩餘天數）", True, None, {
        # 權杖檔的 updated_at 最近兩天內有寫過，代表續期流程有在跑（meta_token_refresh 不是每天跑）
        "run": gate(_within(m.get("updated_at"), now, timedelta(days=2)),
                    f"權杖檔更新於 {m.get('updated_at')}", [str(METATOKEN_FILE.name)]),
        "content": gate(bool(plats) and not worst, "權杖正常" if not worst else "；".join(worst),
                        [str(METATOKEN_FILE.name)]),
        "publish": gate(True, "不適用（權杖不發布）"),
    }, remedy={"action": "dispatch", "workflow": "meta_token_refresh.yml", "inputs": {}})

    # 網站部署：必須包含最新資料，兩個站都要
    finish("website", "網站部署（GitHub Pages＋Cloudflare 主站）", True, None, {
        "run": run_gate(f["runs"].get("pages.yml") or [], now - timedelta(days=2), "pages.yml"),
        "content": data_content,
        "publish": site_result["site"],
    }, remedy={"action": "dispatch", "workflow": "pages.yml", "inputs": {}})
    return items


def summarize(items: list[dict]) -> dict:
    out = {"fail": 0, "pending": 0, "ok": 0, "skip": 0, "disabled": 0}
    for it in items:
        out[it["status"]] = out.get(it["status"], 0) + 1
    return out


# ---------------------------------------------------------------- 補救（每項每天一次）
def remedy_allowed(state: dict, item_id: str, today: str) -> bool:
    """今天這一項還能不能再派（每項每天最多 REMEDY_MAX_PER_DAY 次；跨日自動歸零）。"""
    r = (state.get("remedies") or {}).get(item_id)
    if not r or r.get("date") != today:
        return True
    return int(r.get("count", 0)) < REMEDY_MAX_PER_DAY


def _track_attempt(att: dict, runs, now: datetime) -> str:
    """看上一次派出的 run 現在到哪了，順便把 run id／狀態記進 attempt。
    回傳：unknown（查不到，不准重派）／running（還在跑）／waiting（還沒出現，等下一輪）／
    done（已跑完，依結論判斷）／lost（超過時限還找不到，當作派丟了）。
    dispatch 的 CLI 不回 run id，所以用「建立時間 ≥ 派出時間 − 60 秒」來對。"""
    if runs is None or runs.get(att.get("workflow")) is None:
        return "unknown"
    t0 = _parse_ts(att.get("at"))
    if t0 is None:
        return "unknown"
    cands = sorted(runs_since(runs[att["workflow"]], t0 - timedelta(seconds=60)),
                   key=lambda r: r.get("created_at", ""))
    if not cands:
        return "waiting" if now - t0 < timedelta(minutes=REMEDY_LOST_MIN) else "lost"
    r = cands[0]
    att.update(run_id=r.get("id"), run_status=r.get("status"), run_conclusion=r.get("conclusion"))
    return "running" if r.get("status") in ("queued", "in_progress") else "done"


DAILY_DEFER_START = time(15, 0)   # 交易日 15:00～17:30 不從稽核派 daily.yml：這段是 price／inst 輪的時段，full 一跑最久 90 分鐘會把 price 壓住
DAILY_DEFER_END = time(17, 30)


def daily_remedy_deferred(rm: dict, runs, now: datetime, holidays: set[str] | None = None) -> str | None:
    """2026-11-11：稽核補救派 daily.yml 時讓路。回傳理由（要讓）或 None。
    ① daily.yml 已有排隊／執行中的 run → 不疊（pending 只留一個，新來的會把別人頂掉）。
    ② 交易日 15:00～17:30 → 不派（11-11 15:12 派的 full 跑了 90 分鐘，壓住 15:38 的 price）。17:30 之後的稽核檢查點（18:40）再補。"""
    if rm.get("workflow") != "daily.yml":
        return None
    live = [r for r in ((runs or {}).get("daily.yml") or []) if r.get("status") in ("queued", "in_progress", "pending", "waiting")]
    if live:
        return f"daily.yml 已有 {len(live)} 個排隊／執行中的 run，不疊上去"
    t = now.astimezone(TPE)
    if is_trading_day(t.date(), holidays if holidays is not None else set()) and DAILY_DEFER_START <= t.time() < DAILY_DEFER_END:
        return "交易日 15:00～17:30 是 price／inst 輪的時段，full 補救延到 17:30 之後"
    return None


def run_remedies(items, state, today, dispatch, runs=None, now: datetime | None = None, holidays: set[str] | None = None) -> None:
    """dispatch(workflow, inputs) → (ok, msg)。只派出，不假裝已修好；下一輪稽核會再驗。
    同一時間只准一個補救在跑：上一次派出的 run 還在執行，就不重派。被佇列取代（cancelled）、
    失敗、或派丟了，就重派；但每項每天最多 REMEDY_MAX_PER_DAY 次，超過就等人工。
    每次派出與追蹤結果都記在 state["remedies"][項目]["attempts"]，寫進 data/_state/daily_audit.json。"""
    now = now or datetime.now(TPE)
    state.setdefault("remedies", {})
    for it in items:
        if it["status"] != "fail" or not it.get("remedy"):
            continue
        rec = state["remedies"].get(it["id"])
        if not rec or rec.get("date") != today:
            rec = {"date": today, "count": 0, "attempts": []}
            state["remedies"][it["id"]] = rec
        atts = rec["attempts"]
        last = atts[-1] if atts else None
        if last and last.get("ok"):
            st = _track_attempt(last, runs, now)
            if st == "running":
                it["remedy_note"] = f"補救執行中（派出於 {last.get('at')}，run {last.get('run_id')}），不重派"
                continue
            if st == "waiting":
                it["remedy_note"] = "上次派出的 run 還沒出現，等下一輪再看"
                continue
            if st == "unknown":
                it["remedy_note"] = "查不到上次補救的執行狀態，不重派（避免重複派）"
                continue
            # done／lost：沒有在跑 → 往下走上限判斷（被取代、失敗、派丟都在這裡重派）
        if not remedy_allowed(state, it["id"], today):
            it["remedy_note"] = f"今天已自動補救 {REMEDY_MAX_PER_DAY} 次，不再自動派（等人工看）"
            continue
        rm = it["remedy"]
        why = daily_remedy_deferred(rm, runs, now, holidays)
        if why:
            it["remedy_note"] = "本輪不派：" + why
            continue
        ok, msg = dispatch(rm["workflow"], rm.get("inputs") or {})
        rec["count"] = int(rec.get("count", 0)) + 1
        atts.append({"at": now.isoformat(timespec="seconds"), "workflow": rm["workflow"],
                     "inputs": rm.get("inputs") or {}, "ok": bool(ok), "msg": msg[:300],
                     "run_id": None, "run_status": None, "run_conclusion": None})
        del atts[:-5]
        it["remedy_note"] = (f"已派出 {rm['workflow']}（今天第 {rec['count']} 次）") if ok \
            else ("派出失敗：" + msg[:200])


def dispatch_fn(workflow: str, inputs: dict) -> tuple[bool, str]:
    cmd = ["gh", "workflow", "run", workflow, "-R", REPO, "--ref", "main"]
    for k, v in inputs.items():
        cmd += ["-F", f"{k}={v}"]  # -F 會把 "false" 轉成真布林；-f 會傳字串，GitHub 布林輸入會拒絕
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0, (r.stderr or r.stdout).strip()


# ---------------------------------------------------------------- gh 包裝
def make_gh():
    def gh(path: str, raw: bool = False):
        args = ["gh", "api"]
        if raw:
            args += ["-H", "Accept: application/vnd.github.raw"]
        r = subprocess.run(args + [path], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError((r.stderr or r.stdout).strip()[:300])
        return r.stdout if raw else json.loads(r.stdout)
    return gh


def compare_fn_factory(gh):
    def compare(base: str, head: str) -> str:
        try:
            return gh(f"repos/{REPO}/compare/{base}...{head}").get("status", "unknown")
        except Exception:  # noqa: BLE001
            return "unknown"
    return compare


def load_state() -> dict:
    try:
        return json.loads(AUDIT_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--now", help="測試用：ISO 時間（含時區）")
    ap.add_argument("--remediate", action="store_true", help="對失敗項做一次性補救")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)

    now = datetime.fromisoformat(a.now) if a.now else datetime.now(TPE)
    holidays = load_holidays()
    gh = make_gh()
    facts = collect_facts(now, holidays, gh)
    site_res = {"site": site_gate(facts["site"], compare_fn_factory(gh), now)}
    items = evaluate(facts, holidays, site_res, now)

    state = load_state()
    today = facts["today"]
    if a.remediate:
        run_remedies(items, state, today, dispatch_fn, runs=facts["runs"], now=now, holidays=holidays)
    # 補救紀錄只留今天與昨天，避免檔案無限長
    state["remedies"] = {k: v for k, v in (state.get("remedies") or {}).items()
                         if v.get("date") in {today, (date.fromisoformat(today) - timedelta(days=1)).isoformat()}}

    summary = summarize(items)
    report = {
        "checked_at": facts["now"],
        "today": today,
        "expected_price_date": facts["expected_price"],
        "is_trading_day": is_trading_day(date.fromisoformat(today), holidays),
        "summary": summary,
        "items": items,
        "errors": facts.get("errors", []),
        "remedies": state.get("remedies", {}),
    }
    if not a.no_write:
        AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
        AUDIT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(render_text(report))
    return 1 if summary["fail"] else 0


def render_text(rep: dict) -> str:
    mark = {"ok": "✅", "fail": "❌", "pending": "🔄", "skip": "⏭", "disabled": "⏸"}
    lines = [f"每日稽核 {rep['checked_at']}（價量應有日 {rep['expected_price_date']}）", ""]
    for it in rep["items"]:
        lines.append(f"{mark.get(it['status'], '?')} {it['name']}：{it['status']}")
        for k, g in (it.get("gates") or {}).items():
            tag = "過" if g["ok"] else ("進行中" if g.get("busy") else "不過")
            lines.append(f"    {GATE_NAMES.get(k, k)}: {tag}｜{g['why']}")
        if it.get("why"):
            lines.append(f"    {it['why']}")
        if it.get("remedy_note"):
            lines.append(f"    補救：{it['remedy_note']}")
    lines.append("")
    lines.append(f"合計：{rep['summary']}")
    for e in rep.get("errors") or []:
        lines.append(f"⚠️ 查詢錯誤：{e}")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
