"""Threads 貼文洞察追蹤：定時把自己最近的貼文與回覆的瀏覽、讚、回覆、轉發、引用、分享記下來。

每跑一次，對每一則貼文新增一列（時間戳＋當下累計數），append-only，存在
social/threads/insights/metrics.csv。之後可以畫出「發文後每小時累積多少」的曲線，
用來判斷是時段、內容還是別的原因。

金鑰只讀環境變數 THREADS_ACCESS_TOKEN（GitHub Secret），不寫進任何檔案或 log。
洞察需要 token 有 threads_manage_insights 權限；沒有就只記公開欄位並在輸出提醒。

用法：
  python scripts/threads_insights.py                # 抓最近 25 則貼文＋25 則回覆
  python scripts/threads_insights.py --limit 50
  python scripts/threads_insights.py --report       # 不連外，只讀 CSV 印摘要
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "social" / "threads" / "insights" / "metrics.csv"
API = "https://graph.threads.net/v1.0"
TAIPEI = timezone(timedelta(hours=8))
METRICS = ["views", "likes", "replies", "reposts", "quotes", "shares"]
COLS = ["fetched_at", "post_id", "kind", "posted_at", "permalink", "text_head"] + METRICS


def _get(path: str, token: str, params: dict | None = None) -> dict:
    q = dict(params or {})
    q["access_token"] = token
    url = f"{API}/{path}?{urllib.parse.urlencode(q)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        body = body.replace(token, "***")
        raise RuntimeError(f"HTTP {e.code} {path}: {body[:300]}") from None


def list_posts(token: str, edge: str, limit: int) -> list[dict]:
    d = _get(f"me/{edge}", token, {"fields": "id,text,permalink,timestamp,media_type", "limit": limit})
    return d.get("data", [])


def insights(token: str, post_id: str) -> dict:
    d = _get(f"{post_id}/insights", token, {"metric": ",".join(METRICS)})
    out = {}
    for m in d.get("data", []):
        vals = m.get("values") or []
        out[m["name"]] = vals[0]["value"] if vals else (m.get("total_value") or {}).get("value", 0)
    return out


def collect(token: str, limit: int) -> tuple[list[dict], list[str]]:
    now = datetime.now(TAIPEI).isoformat(timespec="minutes")
    rows, warns = [], []
    for edge, kind in (("threads", "post"), ("replies", "reply")):
        try:
            posts = list_posts(token, edge, limit)
        except RuntimeError as e:
            warns.append(f"讀 {edge} 失敗：{e}")
            continue
        for p in posts:
            row = {"fetched_at": now, "post_id": p["id"], "kind": kind,
                   "posted_at": p.get("timestamp", ""), "permalink": p.get("permalink", ""),
                   "text_head": (p.get("text") or "").replace("\n", " ")[:40]}
            try:
                row.update(insights(token, p["id"]))
            except RuntimeError as e:
                warns.append(f"{p['id']} 洞察失敗（多半是缺 threads_manage_insights 權限）：{str(e)[:120]}")
            rows.append(row)
    return rows, warns


def append(rows: list[dict]) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    new = not OUT.exists()
    with OUT.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerows(rows)


def report() -> str:
    if not OUT.exists():
        return "還沒有資料。"
    with OUT.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    last = {}
    first = {}
    for r in rows:
        first.setdefault(r["post_id"], r)
        last[r["post_id"]] = r
    lines = []
    for pid, r in sorted(last.items(), key=lambda kv: kv[1]["posted_at"], reverse=True)[:15]:
        lines.append(f"{r['posted_at'][:16]} {r['kind']:5} 瀏覽{r.get('views','')} 讚{r.get('likes','')} "
                     f"回覆{r.get('replies','')} 轉發{r.get('reposts','')} 引用{r.get('quotes','')} "
                     f"｜{r['text_head']}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.report:
        print(report())
        return 0
    token = os.environ.get("THREADS_ACCESS_TOKEN", "")
    if not token:
        print("沒有 THREADS_ACCESS_TOKEN，無法抓洞察", file=sys.stderr)
        return 1
    rows, warns = collect(token, a.limit)
    if rows:
        append(rows)
    print(f"記錄 {len(rows)} 則")
    for w in warns[:5]:
        print("⚠", w)
    if len(warns) > 5:
        print(f"⚠ 另有 {len(warns) - 5} 則警告")
    return 0 if rows else 1


if __name__ == "__main__":
    sys.exit(main())
