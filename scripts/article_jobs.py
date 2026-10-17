"""精選文章／短影片「產出佇列」同步（2026-10-16，工作流 .github/workflows/article-jobs.yml 呼叫）。

Andy 10-16：「claude 指負責產出文章，內容……點選清單內主題，點選後我可以再次點選產生精選文章，或是短影片」。
管理區按鈕把請求排進會員 Worker（workers/account-api/articles.js 的 article_jobs 表）；這支用 ARTICLE_BOT_KEY（工作流由 CLOUDFLARE_API_TOKEN 推導）：
  · 預設（同步）：讀未完成的（queued／working）→ 寫 data/_state/article_jobs.json（Claude 排程從這裡讀）；
    同時把「index.json 已經有同一個 topic 的文章」那幾筆 article 請求自動標 done（result＝文章 id）。
  · --mark ID STATUS [--result X]：Claude 開工／完成時標狀態（working／done／failed）。
  · 產文章頻率設定（第 2 版規則清單）：同步成 data/_state/article_schedule.json，並把「這一小時／前一小時」到點的規則排進佇列
    （topic_id＝sch-<日期>-<時>-r<規則>-<類別>-<第幾篇>，Worker 對同一個 id 不重排）。放在這裡做是因為 Claude 的 session 拿不到機器鑰匙。
環境變數 ACCOUNT_API_URL、ARTICLE_BOT_KEY（或 BACKUP_TOKEN）沒設 → 印一行提示、正常結束（不讓排程變紅）。
寫進 repo 的欄位只有：編號、主題 id、種類、標題、備註、狀態、時間 —— 不含會員 uid／email（repo 是 public）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "_state" / "article_jobs.json"
SCHED_OUT = ROOT / "data" / "_state" / "article_schedule.json"
INDEX = ROOT / "site" / "articles" / "index.json"
TAIPEI = timezone(timedelta(hours=8))
KEEP = ("id", "topic_id", "kind", "title", "note", "status", "created", "updated", "result")


def call(base: str, token: str, body: dict) -> dict:
    # Cloudflare 會擋 Python 預設的 User-Agent（Python-urllib → 403），帶一個自己的
    # token 空字串＝不帶 Authorization：Claude 雲端環境的「網路密鑰」由出口代理自動補上（10-17，見 production_guide.md「發佈」）
    hdr = {"content-type": "text/plain", "User-Agent": "tw-rotation-article-jobs/1.0"}
    if token:
        hdr["Authorization"] = "Bearer " + token
    req = urllib.request.Request(base.rstrip("/") + "/v1/articles/jobs/bot", data=json.dumps(body).encode(), headers=hdr, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read()[:300].decode("utf-8", "replace")
        print(f"HTTP {e.code}：{raw}")
        try:
            return {"error": json.loads(raw).get("error") or f"http_{e.code}", "_s": e.code}
        except ValueError:
            return {"error": f"http_{e.code}", "_s": e.code}


def published_topics(index_path: Path = INDEX) -> dict[str, str]:
    """index.json 裡帶 topic 欄位的文章：{topic_id: 文章 id}（同一個 topic 有多篇取最新日期那篇）。"""
    try:
        arts = json.loads(index_path.read_text(encoding="utf-8")).get("articles") or []
    except (OSError, ValueError):
        return {}
    out: dict[str, tuple[str, str]] = {}
    for a in arts:
        t, i, d = a.get("topic"), a.get("id"), str(a.get("date") or "")
        if t and i and (a.get("status") in (None, "published")) and (t not in out or d > out[t][1]):
            out[t] = (i, d)
    return {k: v[0] for k, v in out.items()}


def snapshot(jobs: list[dict], now: datetime | None = None) -> dict:
    now = now or datetime.now(TAIPEI)
    return {"updated": now.strftime("%Y-%m-%d %H:%M"),
            "jobs": [{k: j.get(k) for k in KEEP} for j in jobs if j.get("status") in ("queued", "working")]}


def write_if_changed(data: dict, path: Path = OUT) -> bool:
    """只有工作內容變了才寫（updated 時間不算），免得每小時一個空 commit。"""
    try:
        old = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        old = None
    if old is not None and old.get("jobs") == data["jobs"]:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return True


SCH_CATS = ("news", "intro", "know")


def upgrade_schedule(sch: dict) -> dict:
    """第 1 版（slots／cats）→ 第 2 版（rules）。Worker 新版本來就會轉；這裡再轉一次，是因為 Worker 還沒重新部署的那段時間
    機器路由回的仍是舊格式，而 Claude 排程只認第 2 版（docs/articles/production_guide.md）。規則與 Worker 的 upgradeSchedule 相同：
    同一組時段的星期併成一條、09:50→9 這樣取整點、篇數全 0 就沒有規則＝關閉。"""
    if sch.get("ver") == 2:
        return sch
    raw = sch.get("cats") or {}
    cats = {k: raw.get(k) if isinstance(raw.get(k), int) and 0 <= raw.get(k) <= 3 else 0 for k in SCH_CATS}
    groups: dict[tuple, list[int]] = {}
    for d, ts in sorted((sch.get("slots") or {}).items()):
        if str(d) not in "1234567" or len(str(d)) != 1:
            continue
        hs = sorted({int(str(t)[:2]) for t in (ts or []) if str(t)[:2].isdigit() and 0 <= int(str(t)[:2]) <= 23})
        if hs:
            groups.setdefault(tuple(hs), []).append(int(d))
    rules = [{"days": ds, "hours": list(hs), "cats": dict(cats)} for hs, ds in sorted(groups.items(), key=lambda x: x[1][0])] if any(cats.values()) else []
    return {"ver": 2, "enabled": bool(sch.get("enabled")) and bool(rules), "rules": rules, "updated": sch.get("updated")}


def write_schedule_if_changed(sch, path=None) -> bool:
    """頻率設定 → data/_state/article_schedule.json（第 2 版：ver／enabled／rules／updated；沒有 uid、email —— repo 是 public）。
    內容沒變就不寫（updated 不算），免得每小時一個空 commit。還沒存過設定＝不建檔。"""
    path = path or SCHED_OUT
    if not sch:
        return False
    sch = upgrade_schedule(sch)
    rules = []
    for r in sch.get("rules") or []:
        o = {("dates" if "dates" in r else "days"): list(r.get("dates") if "dates" in r else r.get("days") or []),
             "hours": list(r.get("hours") or []), "cats": {k: int((r.get("cats") or {}).get(k) or 0) for k in SCH_CATS}}
        rules.append(o)
    data = {"ver": 2, "enabled": bool(sch.get("enabled")), "rules": rules}
    try:
        old = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        old = None
    if old is not None and {k: old.get(k) for k in data} == data:
        return False
    ts = sch.get("updated")
    data["updated"] = datetime.fromtimestamp(ts / 1000, TAIPEI).strftime("%Y-%m-%d %H:%M") if isinstance(ts, (int, float)) else None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return True


TOPICS = ROOT / "site" / "articles" / "topics.json"
CAT_NAME = {"news": "比比快訊", "intro": "比比產業鏈", "know": "比比知識"}
LOOKBACK_H = 2   # 這一個小時＋前一個小時：GitHub 排程常晚十幾分鐘、偶爾整輪跳過，多看一小時補得回來；再往前就不補（避免剛加的規則把今天早就過去的整點一次補排）


def due_slots(sch: dict, now: datetime, lookback: int = LOOKBACK_H):
    """頻率設定第 2 版：列出「最近 lookback 個整點裡對得上的 (台北日期, 小時, 第幾條規則, 規則)」。
    對得上＝規則的 dates 含那天、或 days 含那天星期（1＝週一），而且 hours 含那個小時。沒開或不是第 2 版 → 空。"""
    if not sch or sch.get("ver") != 2 or sch.get("enabled") is not True:
        return []
    now = now.astimezone(TAIPEI)
    out = []
    for back in range(lookback - 1, -1, -1):
        t = now - timedelta(hours=back)
        day, wd, hr = t.strftime("%Y-%m-%d"), t.isoweekday(), t.hour
        for i, r in enumerate(sch.get("rules") or [], start=1):
            hit_day = day in (r.get("dates") or []) if "dates" in r else wd in (r.get("days") or [])
            if hit_day and hr in (r.get("hours") or []):
                out.append((day, hr, i, r))
    return out


def plan_schedule_jobs(sch: dict, now: datetime, topics: list[dict], used: set[str]) -> list[dict]:
    """到點的規則 → 要排進佇列的請求清單（還沒送出）。
    · topic_id＝sch-<YYYYMMDD>-<HH>-r<規則>-<類別>-<第幾篇>：Worker 對同一個 id 不論狀態都不重排，所以同一小時跑幾次都只排一次。
    · 從 topics.json 挑該類別「還沒上架、也還沒在佇列（used）」分數最高的主題當建議；挑完的加進 used，同一輪不會兩篇挑到同一題。
      挑不到（候選用完）就排「Claude 自選主題」，標題寫明，production_guide 說 Claude 要自己查證挑題，不是硬湊。"""
    jobs = []
    for day, hr, ri, r in due_slots(sch, now):
        for cat in SCH_CATS:
            for k in range(1, int((r.get("cats") or {}).get(cat) or 0) + 1):
                tid = f"sch-{day.replace('-', '')}-{hr:02d}-r{ri}-{cat}-{k}"
                cand = sorted((t for t in topics if t.get("cat") == cat and t.get("id") and t["id"] not in used),
                              key=lambda t: (-(t.get("score") or 0), t["id"]))
                when = f"台北 {day} {hr:02d}:00"
                if cand:
                    t = cand[0]
                    used.add(t["id"])
                    jobs.append({"topic_id": tid, "kind": "article", "title": str(t.get("title") or t["id"])[:120],
                                 "note": f"排程自動排入（規則 {ri}，{when}）；建議主題 {t['id']}"})
                else:
                    jobs.append({"topic_id": tid, "kind": "article", "title": f"排程：{CAT_NAME[cat]}（候選主題已用完，Claude 自選）",
                                 "note": f"排程自動排入（規則 {ri}，{when}）；建議主題 無"})
    return jobs


def used_topics(jobs: list[dict], index_path: Path = INDEX) -> set[str]:
    """已經用掉的 topics.json 主題：已上架文章的 topic／from_topic、以及佇列裡的 topic_id 與「建議主題 X」。"""
    used = set(published_topics(index_path))
    try:
        for a in json.loads(index_path.read_text(encoding="utf-8")).get("articles") or []:
            if a.get("from_topic"):
                used.add(a["from_topic"])
    except (OSError, ValueError):
        pass
    for j in jobs:
        used.add(str(j.get("topic_id") or ""))
        note = str(j.get("note") or "")
        if "建議主題 " in note:
            used.add(note.split("建議主題 ", 1)[1].split()[0])
    return used


def load_topics(path: Path = TOPICS) -> list[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("topics") or []
    except (OSError, ValueError):
        return []


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mark", nargs=2, metavar=("ID", "STATUS"))
    ap.add_argument("--result", default="")
    a = ap.parse_args(argv)
    base = os.environ.get("ACCOUNT_API_URL", "").strip()
    token = (os.environ.get("ARTICLE_BOT_KEY") or os.environ.get("BACKUP_TOKEN") or "").strip()
    if not base or len(token) < 16:
        print("沒有設定 ACCOUNT_API_URL／機器鑰匙，跳過")
        return 0
    if a.mark:
        r = call(base, token, {"op": "mark", "id": int(a.mark[0]), "status": a.mark[1], "result": a.result})
        print(json.dumps(r, ensure_ascii=False))
        if r.get("error"):
            return 1
    got = call(base, token, {"op": "open"})
    if got.get("error"):
        print(f"讀佇列失敗：{got['error']}")
        return 1
    jobs = got.get("jobs") or []
    pub = published_topics()
    for j in list(jobs):
        if j.get("kind") == "article" and j.get("topic_id") in pub:
            r = call(base, token, {"op": "mark", "id": j["id"], "status": "done", "result": pub[j["topic_id"]]})
            print(f"#{j['id']} {j.get('title')} → 已上架 {pub[j['topic_id']]}（{r.get('error') or 'ok'}）")
            if not r.get("error"):
                jobs.remove(j)
    changed = write_if_changed(snapshot(jobs))
    print(f"未完成 {len(jobs)} 筆；{'已更新' if changed else '沒有變動'} {OUT.relative_to(ROOT)}")
    # 2026-10-16 產文章頻率設定：同步最新一份給 Claude 排程讀（舊版 Worker 還沒部署這個 op 時回 bad_op，只印提示、不讓整支變紅）
    sc = call(base, token, {"op": "schedule"})
    if sc.get("error"):
        print(f"頻率設定略過：{sc['error']}")
    else:
        ch = write_schedule_if_changed(sc.get("schedule"))
        state = "未設定" if not sc.get("schedule") else ("啟用" if sc["schedule"].get("enabled") else "關閉")
        print(f"頻率設定：{state}；{'已更新' if ch else '沒有變動'} {SCHED_OUT.relative_to(ROOT)}")
        # 第 2 版：到點的規則在這裡排進佇列（Claude 的 session 沒有機器鑰匙，排不了；它只負責處理佇列）
        if sc.get("schedule"):
            plan = plan_schedule_jobs(upgrade_schedule(sc["schedule"]), datetime.now(TAIPEI), load_topics(), used_topics(jobs))
            added = 0
            for j in plan:
                r = call(base, token, {"op": "add", **j})
                if r.get("error"):
                    print(f"排程排隊失敗 {j['topic_id']}：{r['error']}")
                elif not r.get("dup"):
                    added += 1
                    jobs.append(r.get("job") or j)
                    print(f"排程排入 {j['topic_id']}：{j['title']}")
            if added:
                write_if_changed(snapshot(jobs))
                print(f"排程新排 {added} 筆；已更新 {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
