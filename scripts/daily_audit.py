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
HEALING_POSTED_FILE = ROOT / "docs" / "marketing" / "channels" / "healing" / "state" / "posted.json"
TC_QUEUE_DIR = ROOT / "social" / "tc" / "queue"
ISSUE_TITLE = "⚠️ 每日稽核：有項目沒完成"

PRICE_CLOSE = time(15, 30)       # 台股收盤後，價量才會有當天
DATA_DEADLINE = time(18, 40)     # 法人／融資券最晚 18:30 那輪落地
TC_GRACE = timedelta(minutes=30)  # 排定時間過 30 分鐘還沒發，才算沒發
SOURCE_FAIL_RED = 2              # 來源連續失敗 2 天以上才算壞（1 天可能是 GitHub 排程延遲）
META_DAYS_RED = 7                # Meta 權杖剩 7 天以下就要續期


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
def gate(ok: bool | None, why: str, evidence: list[str] | None = None) -> dict:
    """ok=None 代表「查不到」，當作不過（不准把查不到當成綠燈）。"""
    return {"ok": bool(ok), "why": why, "evidence": evidence or []}


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


def bad_text(s: str) -> bool:
    return (not s) or s.strip().lower() in {"nan", "none", "null"}


# ---------------------------------------------------------------- 事實蒐集（唯一有 I/O 的地方）
def collect_facts(now: datetime, holidays: set[str], gh) -> dict:
    """gh(path) → 解析後的 JSON；gh_raw(path) → 純文字。失敗由呼叫端決定要不要紅。"""
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

    # 本機（CI 裡是 checkout 出來的 main）
    f["premarket"] = _read_json(ROOT / "site" / "articles" / "premarket.json")
    f["postmarket"] = _read_json(ROOT / "site" / "articles" / "postmarket.json")
    f["last_run"] = _read_json(LAST_RUN_FILE)
    f["source_health"] = _read_json(SOURCE_HEALTH_FILE)
    f["meta"] = _read_json(METATOKEN_FILE)
    f["quota"] = _read_json(QUOTA_FILE)
    f["healing_posted"] = _read_json(HEALING_POSTED_FILE)
    f["tc_queue"] = _read_tc_queue()

    # 資料湖最新日（pipeline 只在 CI／本機有 pandas 時讀；讀不到就是 None＝查不到）
    f["lake"] = {}
    try:  # 讀不到就是 None，關卡會判「查不到」而不是綠
        from pipeline.util import store
        for t in ("price_daily", "inst_daily", "inst_market_daily", "margin_total"):
            f["lake"][t] = store.latest_date(t)
    except Exception as e:  # noqa: BLE001
        f.setdefault("errors", []).append(f"讀資料湖失敗：{e}")

    # 社群發布紀錄（在 social-snaps 分支）
    f["snaps_posted"] = _gh_json_or_none(gh, "state/posted.json")
    f["tc_posted"] = _gh_json_or_none(gh, "state/tc/posted.json")

    # 網站部署：GitHub Pages ＋ Cloudflare 主站
    f["site"] = collect_site(gh)
    return f


def _read_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


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
        if any(r.get("status") in ("queued", "in_progress") for r in runs):
            out["pending"] = True
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


def site_gate(site: dict, compare_fn) -> dict:
    """關卡三（網站）：兩個站都要包含必須的 commit；主站不可比備援站舊。compare_fn(base, head) → status。"""
    req = site.get("required")
    if site.get("pending"):
        return gate(False, "pages.yml 正在部署中（還沒跑完）")
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
        all_ok = all(g["ok"] for g in gates.values())
        past = deadline is None or due(now, deadline)
        if all_ok:
            status = "ok"
        elif not past:
            status = "pending"
        else:
            status = "fail"
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

    # 每日資料更新：應有的價量日、法人、融資券，不退回、沒有來源連續壞
    lake = f.get("lake") or {}
    last = f.get("last_run") or {}
    sh = f.get("source_health") or {}
    bad_src = sorted(k for k, v in sh.items() if isinstance(v, dict) and (v.get("consecutive_fail") or 0) >= SOURCE_FAIL_RED)
    exp_s = expected.isoformat()
    data_due = at_tpe(expected, DATA_DEADLINE) if expected == today else None
    data_content = gate(
        lake.get("price_daily") == exp_s and (lake.get("inst_daily") or "") >= exp_s and
        (lake.get("margin_total") or "") >= exp_s and not (last.get("errors") or []) and not bad_src,
        f"價量 {lake.get('price_daily')}／法人 {lake.get('inst_daily')}／融資券 {lake.get('margin_total')}"
        f"（應有 {exp_s}）；last_run 錯誤 {len(last.get('errors') or [])} 筆；連續失敗來源 {bad_src or '無'}",
        [str(LAST_RUN_FILE.name), str(SOURCE_HEALTH_FILE.name)])
    finish("data", "每日資料更新（價量／法人／融資券）", True, data_due, {
        "run": run_gate(f["runs"].get("daily.yml") or [], at_tpe(expected, time(15, 0)), "daily.yml"),
        "content": data_content,
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

    # 頻道④談晴說礙：quota 的 healing.live 為真才算；沒設就是未啟用
    heal_on = bool((quota.get("healing") or {}).get("live"))
    hp = f.get("healing_posted")
    today_heal = [] if not isinstance(hp, dict) else [k for k, v in hp.items() if f["today"] in json.dumps({k: v}, ensure_ascii=False)]
    finish("healing", "頻道④談晴說礙（每天 1 則）", True, at_tpe(today, time(21, 40)), {
        "run": run_gate(f["runs"].get("healing_post.yml") or [], today_start, "healing_post"),
        "content": gate(bool(today_heal), "healing 發布紀錄有今天" if today_heal else "healing 發布紀錄沒有今天"),
        "publish": gate(bool(today_heal), "有發布紀錄即視為已發布"),
    }, disabled=None if heal_on else "未啟用（post_quota.json 沒有 healing.live＝true，不是失敗）")

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
    tc_posted_ids = f.get("tc_posted") or {}
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
    r = (state.get("remedies") or {}).get(item_id)
    return not (r and r.get("date") == today)


def run_remedies(items, state, today, dispatch) -> None:
    """dispatch(workflow, inputs) → (ok, msg)。只派出，不假裝已修好；下一輪稽核會再驗。"""
    state.setdefault("remedies", {})
    for it in items:
        if it["status"] != "fail" or not it.get("remedy"):
            continue
        if not remedy_allowed(state, it["id"], today):
            it["remedy_note"] = "今天已補救過一次，不再自動補（等人工看）"
            continue
        rm = it["remedy"]
        ok, msg = dispatch(rm["workflow"], rm.get("inputs") or {})
        state["remedies"][it["id"]] = {"date": today, "workflow": rm["workflow"],
                                       "inputs": rm.get("inputs") or {}, "ok": ok, "msg": msg[:300]}
        it["remedy_note"] = ("已派出 " + rm["workflow"]) if ok else ("派出失敗：" + msg[:200])


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
    site_res = {"site": site_gate(facts["site"], compare_fn_factory(gh))}
    items = evaluate(facts, holidays, site_res, now)

    state = load_state()
    today = facts["today"]
    if a.remediate:
        run_remedies(items, state, today, dispatch_fn)
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
        for k in ("run", "content", "publish"):
            g = (it.get("gates") or {}).get(k)
            if g:
                lines.append(f"    {k}: {'過' if g['ok'] else '不過'}｜{g['why']}")
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
