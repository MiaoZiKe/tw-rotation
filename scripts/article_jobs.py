"""精選文章／短影片「產出佇列」同步（2026-10-16，工作流 .github/workflows/article-jobs.yml 呼叫）。

Andy 10-16：「claude 指負責產出文章，內容……點選清單內主題，點選後我可以再次點選產生精選文章，或是短影片」。
管理區按鈕把請求排進會員 Worker（workers/account-api/articles.js 的 article_jobs 表）；這支用 ARTICLE_BOT_KEY（工作流由 CLOUDFLARE_API_TOKEN 推導）：
  · 預設（同步）：讀未完成的（queued／working）→ 寫 data/_state/article_jobs.json（Claude 排程從這裡讀）；
    同時把「index.json 已經有同一個 topic 的文章」那幾筆 article 請求自動標 done（result＝文章 id）。
  · --mark ID STATUS [--result X]：Claude 開工／完成時標狀態（working／done／failed）。
環境變數 ACCOUNT_API_URL、ARTICLE_BOT_KEY（或 BACKUP_TOKEN）沒設 → 印一行提示、正常結束（不讓排程變紅）。
寫進 repo 的欄位只有：編號、主題 id、種類、標題、備註、狀態、時間 —— 不含會員 uid／email（repo 是 public）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "_state" / "article_jobs.json"
INDEX = ROOT / "site" / "articles" / "index.json"
TAIPEI = timezone(timedelta(hours=8))
KEEP = ("id", "topic_id", "kind", "title", "note", "status", "created", "updated", "result")


def call(base: str, token: str, body: dict) -> dict:
    req = urllib.request.Request(base.rstrip("/") + "/v1/articles/jobs/bot", data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + token, "content-type": "text/plain"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


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
    jobs = call(base, token, {"op": "open"}).get("jobs") or []
    pub = published_topics()
    for j in list(jobs):
        if j.get("kind") == "article" and j.get("topic_id") in pub:
            r = call(base, token, {"op": "mark", "id": j["id"], "status": "done", "result": pub[j["topic_id"]]})
            print(f"#{j['id']} {j.get('title')} → 已上架 {pub[j['topic_id']]}（{r.get('error') or 'ok'}）")
            if not r.get("error"):
                jobs.remove(j)
    changed = write_if_changed(snapshot(jobs))
    print(f"未完成 {len(jobs)} 筆；{'已更新' if changed else '沒有變動'} {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
