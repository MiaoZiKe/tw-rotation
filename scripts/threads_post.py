"""Threads 排程發文：讀 social/threads/queue/*.md，把「已核准、時間到」的貼文用官方 Threads API 發出。

用法：
  python scripts/threads_post.py --check            只檢查格式與字數，不連外（本機、pytest 用）
  python scripts/threads_post.py                    發出所有「approved 且 publish_at 已到」的貼文
  python scripts/threads_post.py --file <檔名>      只處理指定的一個檔案（仍須 status: approved）
  python scripts/threads_post.py --file <檔名> --now  忽略 publish_at，立刻發（仍須 status: approved）

安全規則（Andy 要求：核准才發、金鑰只放 GitHub Secrets）：
  · 只有 status: approved 的檔案會被發；draft／posted／error 一律不碰。
  · 金鑰從環境變數 THREADS_ACCESS_TOKEN 讀，絕不印出、絕不寫進檔案或 log。
  · 失敗不重試發文（避免重複發）：標 status: error 並寫原因，工作流程以失敗結束，GitHub 會通知。
  · 串文（一則接一則）：檔案內用單獨一行 `-----` 分隔，第 2 則起以前一則為回覆對象。
  · 每則 ≤ 500 字（Threads 單則上限）。

檔案格式：
  ---
  status: draft | approved | posted | error
  publish_at: 2026-10-26T20:30+08:00
  title: 給人看的標題
  ---
  第一則內容
  -----
  第二則內容
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "social" / "threads" / "queue"
API = "https://graph.threads.net/v1.0"
TAIPEI = timezone(timedelta(hours=8))
MAX_LEN = 500
STATUSES = {"draft", "approved", "posted", "error"}
SEP = re.compile(r"^-{5,}\s*$", re.M)


class PostError(Exception):
    pass


def _is_emoji(c: str) -> bool:
    o = ord(c)
    return o >= 0x1F000 or 0x2190 <= o <= 0x2BFF or o in (0xFE0F, 0x200D, 0x20E3)


def _tlen(s: str) -> int:
    """Threads 官方文件：表情符號以 UTF-8 位元組數計入 500 上限（一個 emoji 常占 3～4）。
    這裡對 emoji 一律用 UTF-8 位元組數，其他字元算 1，寧可高估也不要發不出去。"""
    return sum(len(c.encode("utf-8")) if _is_emoji(c) else 1 for c in s)


def parse(text: str) -> tuple[dict, list[str]]:
    """回傳 (front matter dict, 貼文清單)。格式不對丟 PostError。"""
    m = re.match(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", text, re.S)
    if not m:
        raise PostError("缺少檔頭（開頭要有 --- … ---）")
    meta: dict = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        k, sep, v = line.partition(":")
        if not sep:
            raise PostError(f"檔頭格式錯誤：{line!r}")
        meta[k.strip()] = v.strip()
    posts = [p.strip() for p in SEP.split(m.group(2)) if p.strip()]
    return meta, posts


def validate(meta: dict, posts: list[str]) -> list[str]:
    """回傳問題清單（空＝通過）。"""
    errs: list[str] = []
    st = meta.get("status", "")
    if st not in STATUSES:
        errs.append(f"status 必須是 {sorted(STATUSES)} 之一，目前是 {st!r}")
    if not meta.get("publish_at"):
        errs.append("缺少 publish_at")
    else:
        try:
            when(meta)
        except ValueError:
            errs.append(f"publish_at 格式錯誤（要像 2026-10-26T20:30+08:00）：{meta['publish_at']!r}")
    if not posts:
        errs.append("沒有任何貼文內容")
    for i, p in enumerate(posts, 1):
        if _tlen(p) > MAX_LEN:
            errs.append(f"第 {i} 則 {_tlen(p)} 字，超過 {MAX_LEN} 字")
    if "{連結}" in "".join(posts) or "{link}" in "".join(posts).lower():
        errs.append("內容還有未填的 {連結} 佔位符")
    return errs


def when(meta: dict) -> datetime:
    s = meta["publish_at"]
    d = datetime.fromisoformat(s)
    return d if d.tzinfo else d.replace(tzinfo=TAIPEI)


def is_due(meta: dict, now: datetime) -> bool:
    return meta.get("status") == "approved" and when(meta) <= now


# ---------- Threads API ----------

def _call(method: str, path: str, token: str, params: dict | None = None) -> dict:
    params = dict(params or {})
    params["access_token"] = token
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}{path}"
    if method == "GET":
        req = urllib.request.Request(f"{url}?{data.decode()}")
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        # 錯誤內文不含權杖（權杖在請求裡，不在回應裡）；仍只截前 300 字
        raise PostError(f"HTTP {e.code} {path}：{body[:300]}") from None
    except urllib.error.URLError as e:
        raise PostError(f"連線失敗 {path}：{e.reason}") from None


def publish_chain(posts: list[str], token: str) -> list[dict]:
    me = _call("GET", "/me", token, {"fields": "id,username"})
    uid = me["id"]
    out: list[dict] = []
    reply_to = None
    for i, text in enumerate(posts, 1):
        params = {"media_type": "TEXT", "text": text}
        if reply_to:
            params["reply_to_id"] = reply_to
        c = _call("POST", f"/{uid}/threads", token, params)
        cid = c["id"]
        time.sleep(8)  # 讓容器建好；官方建議等候，文字貼文通常很快
        p = None
        for wait in (0, 10, 20, 30):  # 容器尚未就緒時重試「發布」；發布前重試不會重複發
            time.sleep(wait)
            try:
                p = _call("POST", f"/{uid}/threads_publish", token, {"creation_id": cid})
                break
            except PostError as e:
                if wait == 30 or "HTTP 4" not in str(e) or "190" in str(e):
                    raise
        mid = p["id"]
        link = ""
        try:
            link = _call("GET", f"/{mid}", token, {"fields": "permalink"}).get("permalink", "")
        except PostError:
            pass
        out.append({"id": mid, "permalink": link})
        reply_to = mid
        if i < len(posts):
            time.sleep(3)
    return out


# ---------- 檔案寫回 ----------

def rewrite_meta(path: Path, updates: dict) -> None:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"\A(---\s*\n)(.*?)(\n---\s*\n?)(.*)\Z", text, re.S)
    lines = m.group(2).splitlines()
    done = set()
    for idx, line in enumerate(lines):
        k = line.partition(":")[0].strip()
        if k in updates:
            lines[idx] = f"{k}: {updates[k]}"
            done.add(k)
    for k, v in updates.items():
        if k not in done:
            lines.append(f"{k}: {v}")
    path.write_text(m.group(1) + "\n".join(lines) + m.group(3) + m.group(4), encoding="utf-8")


def process(path: Path, now: datetime, token: str | None, force_now: bool = False) -> str:
    meta, posts = parse(path.read_text(encoding="utf-8"))
    errs = validate(meta, posts)
    if errs:
        raise PostError("；".join(errs))
    if meta["status"] != "approved":
        return "略過（status 不是 approved）"
    if not force_now and not is_due(meta, now):
        return f"略過（還沒到 {meta['publish_at']}）"
    if not token:
        raise PostError("沒有 THREADS_ACCESS_TOKEN（請在 GitHub Secrets 設定）")
    res = publish_chain(posts, token)
    rewrite_meta(path, {
        "status": "posted",
        "posted_at": now.astimezone(TAIPEI).strftime("%Y-%m-%dT%H:%M+08:00"),
        "urls": " ".join(r["permalink"] for r in res if r["permalink"]) or "(無)",
    })
    return f"已發出 {len(res)} 則"


def wait_for_due(files: list, wait_max_min: float) -> None:
    """備援觸發用：早到的 job 在 wait_max_min 分鐘內等到 publish_at 再發，超過的留給下一輪。"""
    deadline = time.time() + wait_max_min * 60
    upcoming = []
    for f in files:
        try:
            meta, _ = parse(f.read_text(encoding="utf-8"))
            if meta.get("status") == "approved":
                upcoming.append((when(meta), f))
        except Exception:
            continue
    upcoming.sort(key=lambda x: x[0])
    for t, f in upcoming:
        delta = (t - datetime.now(TAIPEI)).total_seconds()
        if delta <= 0:
            continue
        if time.time() + delta > deadline:
            print(f"{f.name}：{t.isoformat()} 超過等待上限，交給下一輪")
            break
        print(f"{f.name}：等 {int(delta)} 秒到 {t.isoformat()}", flush=True)
        time.sleep(delta + 2)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只檢查格式，不連外")
    ap.add_argument("--file", default="", help="只處理這個檔名（queue 內）")
    ap.add_argument("--now", action="store_true", help="忽略 publish_at，立刻發")
    ap.add_argument("--wait-max", type=float, default=0.0,
                    help="publish_at 還沒到但 N 分鐘內會到的，在 job 內等到點再發（上限 20 分；超過交給下一輪）")
    ap.add_argument("--queue", default=str(QUEUE))
    a = ap.parse_args(argv)
    q = Path(a.queue)
    files = sorted(q.glob("*.md"))
    if a.file:
        files = [f for f in files if f.name == a.file or f.stem == a.file]
        if not files:
            print(f"找不到檔案：{a.file}", file=sys.stderr)
            return 2
    if a.wait_max > 0 and not a.check and not a.now:
        wait_for_due(files, min(a.wait_max, 20.0))
    now = datetime.now(TAIPEI)
    token = os.environ.get("THREADS_ACCESS_TOKEN", "").strip() or None
    bad = 0
    for f in files:
        try:
            meta, posts = parse(f.read_text(encoding="utf-8"))
            errs = validate(meta, posts)
            if a.check:
                if errs:
                    bad += 1
                    print(f"✗ {f.name}：{'；'.join(errs)}")
                else:
                    print(f"✓ {f.name}（{meta['status']}，{len(posts)} 則）")
                continue
            if errs:
                if meta.get("status") == "approved":
                    raise PostError("；".join(errs))
                continue
            msg = process(f, now, token, a.now)
            print(f"{f.name}：{msg}")
        except PostError as e:
            bad += 1
            print(f"✗ {f.name}：{e}", file=sys.stderr)
            if not a.check:
                try:
                    rewrite_meta(f, {"status": "error", "error": str(e)[:200].replace("\n", " ")})
                except Exception:
                    pass
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
