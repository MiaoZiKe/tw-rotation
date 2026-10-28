"""Instagram 排程發文：讀 social/ig/queue/*.md，把「已核准、時間到」的貼文用官方 Instagram API（Instagram 登入版）發出。

用法：
  python scripts/ig_post.py --check              只檢查格式、字數、圖片檔，不連外
  python scripts/ig_post.py                      發出所有「approved 且 publish_at 已到」的貼文
  python scripts/ig_post.py --file <檔名> [--now]  只處理一個檔案（仍須 status: approved；--now 忽略時間）
  python scripts/ig_post.py --convert a.png b.png  把 PNG 轉成 IG 能收的 JPEG（放同資料夾，需 Pillow）

安全規則（與 Threads 發文一致）：
  · 只有 status: approved 的檔案會被發；draft／posted／error 一律不碰。
  · 金鑰只讀環境變數 IG_ACCESS_TOKEN，不印出、不寫進任何檔案。
  · 失敗不重發：標 status: error 並寫原因，工作流程失敗，GitHub 會通知。

IG 官方限制（檢查時會擋）：
  · 一定要有圖：單張 1 張、輪播 2～10 張。
  · 圖片必須是 JPEG（.jpg／.jpeg）；PNG 請先用 --convert 轉檔。
  · 圖片必須在「公開網址」：本程式用 repo 公開網址 raw.githubusercontent.com/<repo>/main/<路徑>，
    所以圖要先 push 到 main，才能排程發出。repo 是公開的，別放機密或個資。
  · 說明文字 ≤ 2200 字、#標籤 ≤ 30 個。

檔案格式：
  ---
  status: draft | approved | posted | error
  publish_at: 2026-10-26T20:30+08:00
  title: 給人看的標題
  images: social/ig/images/a.jpg, social/ig/images/b.jpg
  ---
  說明文字（整段原樣當作 caption）
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
QUEUE = ROOT / "social" / "ig" / "queue"
API = "https://graph.instagram.com"
RAW = "https://raw.githubusercontent.com/MiaoZiKe/tw-rotation/main/"
TAIPEI = timezone(timedelta(hours=8))
STATUSES = {"draft", "approved", "posted", "error"}
MAX_CAPTION = 2200
MAX_TAGS = 30


class PostError(Exception):
    pass


def parse(text: str) -> tuple[dict, str]:
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
    return meta, m.group(2).strip()


def images_of(meta: dict) -> list[str]:
    return [s.strip() for s in meta.get("images", "").split(",") if s.strip()]


def when(meta: dict) -> datetime:
    d = datetime.fromisoformat(meta["publish_at"])
    return d if d.tzinfo else d.replace(tzinfo=TAIPEI)


def validate(meta: dict, caption: str, root: Path | None = None, check_files: bool = True) -> list[str]:
    root = root or ROOT
    errs: list[str] = []
    if meta.get("status", "") not in STATUSES:
        errs.append(f"status 必須是 {sorted(STATUSES)} 之一，目前是 {meta.get('status')!r}")
    if not meta.get("publish_at"):
        errs.append("缺少 publish_at")
    else:
        try:
            when(meta)
        except ValueError:
            errs.append(f"publish_at 格式錯誤（要像 2026-10-26T20:30+08:00）：{meta['publish_at']!r}")
    imgs = images_of(meta)
    if not imgs:
        errs.append("IG 一定要有圖：請在 images 填圖片路徑（輪播用逗號分隔）")
    if len(imgs) > 10:
        errs.append(f"輪播最多 10 張，目前 {len(imgs)} 張")
    for p in imgs:
        if not p.lower().endswith((".jpg", ".jpeg")):
            errs.append(f"{p} 不是 JPEG（IG 官方只收 JPEG；PNG 請用 --convert 轉檔）")
        elif check_files and not (root / p).is_file():
            errs.append(f"找不到圖片檔 {p}")
    if not caption:
        errs.append("說明文字是空的")
    if len(caption) > MAX_CAPTION:
        errs.append(f"說明文字 {len(caption)} 字，超過 {MAX_CAPTION}")
    if len(re.findall(r"#\S+", caption)) > MAX_TAGS:
        errs.append(f"#標籤超過 {MAX_TAGS} 個")
    if "{連結}" in caption:
        errs.append("說明文字還有未填的 {連結} 佔位符")
    return errs


def is_due(meta: dict, now: datetime) -> bool:
    return meta.get("status") == "approved" and when(meta) <= now


# ---------- Instagram API ----------

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
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise PostError(f"HTTP {e.code} {path}：{e.read().decode('utf-8', 'replace')[:300]}") from None
    except urllib.error.URLError as e:
        raise PostError(f"連線失敗 {path}：{e.reason}") from None


def public_url(rel: str) -> str:
    return RAW + urllib.parse.quote(rel.replace("\\", "/"))


def check_public(url: str) -> None:
    """圖片要先在 main 上公開，否則 IG 抓不到。"""
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=30) as r:
            if r.status != 200:
                raise PostError(f"圖片網址不是 200：{url}")
    except urllib.error.HTTPError as e:
        raise PostError(f"圖片還沒公開（HTTP {e.code}）：{url}；請先把圖片 push 到 main") from None
    except urllib.error.URLError as e:
        raise PostError(f"圖片網址連不上：{url}（{e.reason}）") from None


def wait_ready(cid: str, token: str, tries: int = 12) -> None:
    for _ in range(tries):
        st = _call("GET", f"/{cid}", token, {"fields": "status_code"}).get("status_code", "")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise PostError(f"容器處理失敗（{st}）：{cid}")
        time.sleep(5)
    raise PostError(f"容器 60 秒內沒處理完：{cid}")


def publish(imgs: list[str], caption: str, token: str) -> dict:
    uid = _call("GET", "/me", token, {"fields": "user_id,username"}).get("user_id")
    if not uid:
        raise PostError("查不到 IG user_id（權杖權限或帳號類型有問題）")
    urls = [public_url(p) for p in imgs]
    for u in urls:
        check_public(u)
    if len(urls) == 1:
        c = _call("POST", f"/{uid}/media", token, {"image_url": urls[0], "caption": caption})["id"]
    else:
        kids = []
        for u in urls:
            k = _call("POST", f"/{uid}/media", token, {"image_url": u, "is_carousel_item": "true"})["id"]
            wait_ready(k, token)
            kids.append(k)
        c = _call("POST", f"/{uid}/media", token,
                  {"media_type": "CAROUSEL", "children": ",".join(kids), "caption": caption})["id"]
    wait_ready(c, token)
    mid = _call("POST", f"/{uid}/media_publish", token, {"creation_id": c})["id"]
    link = ""
    try:
        link = _call("GET", f"/{mid}", token, {"fields": "permalink"}).get("permalink", "")
    except PostError:
        pass
    return {"id": mid, "permalink": link}


# ---------- 檔案寫回 ----------

def rewrite_meta(path: Path, updates: dict) -> None:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"\A(---\s*\n)(.*?)(\n---\s*\n?)(.*)\Z", text, re.S)
    lines = m.group(2).splitlines()
    done = set()
    for i, line in enumerate(lines):
        k = line.partition(":")[0].strip()
        if k in updates:
            lines[i] = f"{k}: {updates[k]}"
            done.add(k)
    for k, v in updates.items():
        if k not in done:
            lines.append(f"{k}: {v}")
    path.write_text(m.group(1) + "\n".join(lines) + m.group(3) + m.group(4), encoding="utf-8")


def process(path: Path, now: datetime, token: str | None, force_now: bool = False) -> str:
    meta, caption = parse(path.read_text(encoding="utf-8"))
    errs = validate(meta, caption)
    if errs:
        raise PostError("；".join(errs))
    if meta["status"] != "approved":
        return "略過（status 不是 approved）"
    if not force_now and not is_due(meta, now):
        return f"略過（還沒到 {meta['publish_at']}）"
    if not token:
        raise PostError("沒有 IG_ACCESS_TOKEN（請在 GitHub Secrets 設定）")
    r = publish(images_of(meta), caption, token)
    rewrite_meta(path, {
        "status": "posted",
        "posted_at": now.astimezone(TAIPEI).strftime("%Y-%m-%dT%H:%M+08:00"),
        "urls": r["permalink"] or "(無)",
    })
    return "已發出"


def convert(files: list[str]) -> int:
    try:
        from PIL import Image
    except ImportError:
        print("需要 Pillow：pip install pillow", file=sys.stderr)
        return 2
    for f in files:
        p = Path(f)
        out = p.with_suffix(".jpg")
        Image.open(p).convert("RGB").save(out, "JPEG", quality=92)
        print(f"{p} → {out}")
    return 0


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
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--file", default="")
    ap.add_argument("--now", action="store_true")
    ap.add_argument("--wait-max", type=float, default=0.0,
                    help="publish_at 還沒到但 N 分鐘內會到的，在 job 內等到點再發（上限 20 分；超過交給下一輪）")
    ap.add_argument("--queue", default=str(QUEUE))
    ap.add_argument("--convert", nargs="+")
    a = ap.parse_args(argv)
    if a.convert:
        return convert(a.convert)
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
    token = os.environ.get("IG_ACCESS_TOKEN", "").strip() or None
    bad = 0
    for f in files:
        try:
            meta, caption = parse(f.read_text(encoding="utf-8"))
            errs = validate(meta, caption)
            if a.check:
                if errs:
                    bad += 1
                    print(f"✗ {f.name}：{'；'.join(errs)}")
                else:
                    print(f"✓ {f.name}（{meta['status']}，{len(images_of(meta))} 張圖）")
                continue
            if errs:
                if meta.get("status") == "approved":
                    raise PostError("；".join(errs))
                continue
            print(f"{f.name}：{process(f, now, token, a.now)}")
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
