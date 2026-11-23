"""頻道②「科技透明圈」同步發 Facebook 粉專 Reels（2026-11-23）。

開關：social/tc/fb.json（預設 {"enabled": false}；只有 enabled 是 true 才會連 Facebook）。
權杖：GitHub Secrets TECH_FB_PAGE_TOKEN（粉專「科技透明圈」長效粉專權杖）、TECH_FB_PAGE_ID，
      工作流帶成環境變數 TC_FB_PAGE_TOKEN／TC_FB_PAGE_ID。權杖一個字都不印（log 一律經 redact）。

用法：
  python scripts/tc_fb.py --check          只讀檢查：GET /{page-id}?fields=id,name、/me、/debug_token；不發文
  （發文由 scripts/tc_post.py 呼叫 sync()：IG、Threads 發完之後才發 FB；FB 失敗只記錄，不擋 IG／Threads）
  python scripts/tc_post.py --fb-only <資料夾> [--dry-run]   把一支已發影片補發到 FB（手動測試用，不看開關）

FB Reels 三段式上傳（Meta 官方文件「Reels Publishing API」）：
  1. POST /{page-id}/video_reels  upload_phase=start                       → video_id、upload_url
  2. POST https://rupload.facebook.com/video-upload/{版本}/{video_id}
       標頭 Authorization: OAuth <粉專權杖>、offset: 0、file_size: <位元組>，本體＝影片檔
  3. POST /{page-id}/video_reels  upload_phase=finish、video_id、video_state=PUBLISHED、description
  之後 GET /{video_id}?fields=status 查到 video_status ready／publishing_phase complete；ERROR 就報錯。
官方影片規格（發前用 ffprobe 檢查，不合就不上傳）：mp4／mov、長寬比 9:16、至少 540×960（建議 1080×1920）、
  影格率 24～60 fps、長度 3～90 秒。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "social" / "tc" / "fb.json"
GRAPH_VER = "v25.0"
GRAPH = f"https://graph.facebook.com/{GRAPH_VER}"
RUPLOAD = f"https://rupload.facebook.com/video-upload/{GRAPH_VER}"
TAIPEI = timezone(timedelta(hours=8))
POLL_SEC = 10
MAX_WAIT_SEC = 300
SPEC = {"min_w": 540, "min_h": 960, "fps": (24.0, 60.0), "dur": (3.0, 90.0), "ratio": 9 / 16, "ratio_tol": 0.02}
SLEEP = time.sleep

_SECRETS: list[str] = []


class FBError(Exception):
    pass


def mask(v: str) -> None:
    if v and v not in _SECRETS:
        _SECRETS.append(v)
        if os.environ.get("GITHUB_ACTIONS"):
            print("::add-mask::" + v, flush=True)


def redact(s) -> str:
    s = str(s)
    for t in _SECRETS:
        s = s.replace(t, "***")
    return s


def log(*a) -> None:
    print(redact(" ".join(str(x) for x in a)), flush=True)


def load_config(path: Path | None = None) -> dict:
    """讀不到或格式壞 → 視為關閉（寧可不發）。"""
    path = path or CONFIG
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    return {"enabled": isinstance(d, dict) and d.get("enabled") is True}


def creds(env: dict) -> tuple[str, str]:
    tok = (env.get("TC_FB_PAGE_TOKEN") or "").strip()
    pid = (env.get("TC_FB_PAGE_ID") or "").strip()
    mask(tok)
    return tok, pid


# ---------- HTTP（單一出口，測試 mock 這裡） ----------

def http(method: str, url: str, token: str, params: dict | None = None, headers: dict | None = None,
         body: bytes | None = None) -> dict:
    """權杖一律放 Authorization 標頭，不進網址，錯誤訊息也不會帶到。"""
    h = {"Authorization": f"OAuth {token}"}
    h.update(headers or {})
    q = urllib.parse.urlencode(params or {})
    if method == "GET":
        req = urllib.request.Request(url + (f"?{q}" if q else ""), headers=h)
    elif body is not None:
        req = urllib.request.Request(url + (f"?{q}" if q else ""), data=body, headers=h, method=method)
    else:
        req = urllib.request.Request(url, data=q.encode(), headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raise FBError(redact(f"HTTP {e.code} {url.split('?')[0]}：{e.read().decode('utf-8', 'replace')[:300]}")) from None
    except urllib.error.URLError as e:
        raise FBError(redact(f"連線失敗 {url.split('?')[0]}：{e.reason}")) from None


# ---------- 只讀檢查 ----------

def check(env: dict) -> int:
    tok, pid = creds(env)
    if not tok or not pid:
        log(f"✗ 缺少 Secret：{'TECH_FB_PAGE_TOKEN ' if not tok else ''}{'TECH_FB_PAGE_ID' if not pid else ''}".strip())
        return 1
    ok = True
    try:
        d = http("GET", f"{GRAPH}/{pid}", tok, {"fields": "id,name"})
        log(f"✓ 粉專：{d.get('name', '')}（ID {d.get('id', '')}）")
        if str(d.get("id", "")) != pid:
            log("✗ 回傳的粉專 ID 跟 TECH_FB_PAGE_ID 不一樣")
            ok = False
    except FBError as e:
        log(f"✗ 查粉專失敗：{e}")
        ok = False
    try:
        me = http("GET", f"{GRAPH}/me", tok, {"fields": "id,name"})
        same = str(me.get("id", "")) == pid
        log(f"{'✓' if same else '✗'} /me：{me.get('name', '')}（ID {me.get('id', '')}）"
            + ("＝這把權杖就是這個粉專的粉專權杖" if same else "，跟粉專 ID 不同，可能不是粉專權杖"))
        ok = ok and same
    except FBError as e:
        log(f"✗ /me 失敗：{e}")
        ok = False
    try:
        dt = http("GET", f"{GRAPH}/debug_token", tok, {"input_token": tok}).get("data") or {}
        exp = dt.get("expires_at")
        exp_s = "永不" if exp in (0, None) else datetime.fromtimestamp(int(exp), TAIPEI).strftime("%Y-%m-%d %H:%M")
        log(f"{'✓' if dt.get('type') == 'PAGE' and dt.get('is_valid') else '✗'} debug_token：類型 {dt.get('type', '?')}、"
            f"有效 {dt.get('is_valid')}、粉專 {dt.get('profile_id', '')}、到期 {exp_s}、"
            f"權限 {','.join(dt.get('scopes') or [])}")
        if dt.get("type") != "PAGE" or not dt.get("is_valid"):
            ok = False
        need = {"publish_video", "pages_manage_posts", "pages_read_engagement", "pages_show_list"}
        miss = need - set(dt.get("scopes") or [])
        if dt.get("scopes") is not None and miss:
            log(f"⚠ 缺少權限：{','.join(sorted(miss))}")
    except FBError as e:
        log(f"⚠ debug_token 查不到（不影響判斷，以 /me 為準）：{e}")
    log("結果：" + ("成功" if ok else "失敗"))
    return 0 if ok else 1


# ---------- 規格檢查 ----------

def probe(path: Path) -> dict | None:
    """ffprobe 讀寬、高、影格率、長度；沒有 ffprobe 回 None（只警告不擋）。"""
    if not shutil.which("ffprobe"):
        return None
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(path)],
                       capture_output=True, text=True, timeout=60)
    d = json.loads(r.stdout or "{}")
    s = (d.get("streams") or [{}])[0]
    num, _, den = str(s.get("r_frame_rate", "0/1")).partition("/")
    return {"w": int(s.get("width") or 0), "h": int(s.get("height") or 0),
            "fps": float(num or 0) / float(den or 1), "dur": float((d.get("format") or {}).get("duration") or 0)}


def spec_errors(info: dict | None) -> list[str]:
    if info is None:
        return []
    e = []
    if info["w"] < SPEC["min_w"] or info["h"] < SPEC["min_h"]:
        e.append(f"解析度 {info['w']}×{info['h']} 小於 540×960")
    if info["h"] and abs(info["w"] / info["h"] - SPEC["ratio"]) > SPEC["ratio_tol"]:
        e.append(f"長寬比 {info['w']}:{info['h']} 不是 9:16")
    if not SPEC["fps"][0] <= info["fps"] <= SPEC["fps"][1]:
        e.append(f"影格率 {info['fps']:.2f} 不在 24～60")
    if not SPEC["dur"][0] <= info["dur"] <= SPEC["dur"][1]:
        e.append(f"長度 {info['dur']:.1f} 秒不在 3～90 秒")
    return e


# ---------- 發 Reels ----------

def post_reel(page_id: str, token: str, video: Path, description: str) -> dict:
    data = video.read_bytes()
    st = http("POST", f"{GRAPH}/{page_id}/video_reels", token, {"upload_phase": "start"})
    vid = str(st.get("video_id") or "")
    if not vid:
        raise FBError(f"start 沒拿到 video_id：{str(st)[:200]}")
    up_url = st.get("upload_url") or f"{RUPLOAD}/{vid}"
    up = http("POST", up_url, token, headers={"offset": "0", "file_size": str(len(data)),
                                              "Content-Type": "application/octet-stream"}, body=data)
    if up.get("success") is not True:
        raise FBError(f"上傳沒有回 success：{str(up)[:200]}")
    fin = http("POST", f"{GRAPH}/{page_id}/video_reels", token,
               {"upload_phase": "finish", "video_id": vid, "video_state": "PUBLISHED", "description": description})
    if fin.get("success") is not True:
        raise FBError(f"finish 沒有回 success：{str(fin)[:200]}")
    # finish 成功＝已送出發布；之後只查狀態，逾時不重發（避免重複貼文）
    state = "處理中"
    for _ in range(MAX_WAIT_SEC // POLL_SEC):
        s = (http("GET", f"{GRAPH}/{vid}", token, {"fields": "status"}).get("status") or {})
        vs = s.get("video_status", "")
        pub = (s.get("publishing_phase") or {}).get("status", "")
        if vs == "error" or pub == "error" or (s.get("processing_phase") or {}).get("status") == "error":
            raise FBError(f"FB 影片處理失敗：{str(s)[:200]}")
        if pub == "complete" or vs in ("ready", "published"):
            state = "已發布"
            break
        SLEEP(POLL_SEC)
    link = ""
    try:
        link = http("GET", f"{GRAPH}/{vid}", token, {"fields": "permalink_url"}).get("permalink_url", "")
    except FBError:
        pass
    if link.startswith("/"):
        link = "https://www.facebook.com" + link
    return {"id": vid, "permalink": link or f"https://www.facebook.com/reel/{vid}", "state": state}


def sync(p: dict, env: dict, now: datetime, dry_run: bool = False, force: bool = False,
         cfg: dict | None = None) -> dict:
    """IG／Threads 發完後呼叫。回傳要寫進 post.md 的欄位（可能是空的）；任何錯誤都吞掉、寫進 fb_error，不往外丟。

    force＝True：手動補發（--fb-only），不看 fb.json 開關。
    """
    cfg = cfg if cfg is not None else load_config()
    if not force and not cfg["enabled"]:
        return {}
    pid_ = p.get("id", "")
    if p.get("media") != "video":
        log(f"{pid_}：FB 只發 Reels，這篇不是影片，略過")
        return {}
    if p["meta"].get("ids_fb"):
        log(f"{pid_}：FB 已發過（{p['meta'].get('urls_fb', '')}），不重發")
        return {}
    tok, page = creds(env)
    if not tok or not page:
        msg = "沒有 TECH_FB_PAGE_TOKEN／TECH_FB_PAGE_ID"
        log(f"::warning::{pid_}：FB {msg}，略過")
        return {"fb_error": msg}
    try:
        video = p["dir"] / p.get("video", "")
        if not p.get("video") or not video.is_file():
            raise FBError(f"找不到影片檔 {p.get('video', '')}")
        bad = spec_errors(probe(video))
        if bad:
            raise FBError("影片不合 FB Reels 規格：" + "；".join(bad))
        if not p.get("caption"):
            raise FBError("ig.txt 是空的")
        if dry_run:
            log(f"[dry-run] {pid_}：會發 FB Reels 到粉專 {page}（{video.name}，{video.stat().st_size // 1024} KB）；沒有真的發")
            return {}
        r = post_reel(page, tok, video, p["caption"])
        log(f"{pid_}：FB Reels {r['state']} {r['permalink']}")
        return {"ids_fb": r["id"], "urls_fb": r["permalink"], "fb_posted_at": now.astimezone(TAIPEI).strftime(
            "%Y-%m-%dT%H:%M+08:00"), "fb_error": ""}
    except Exception as e:  # noqa: BLE001  FB 失敗絕不擋 IG／Threads
        msg = redact(str(e))[:200].replace("\n", " ")
        log(f"::warning::{pid_}：FB Reels 發文失敗（不影響 IG／Threads）：{msg}")
        return {"fb_error": msg}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="頻道② 科技透明圈 FB 粉專")
    ap.add_argument("--check", action="store_true", help="只讀檢查權杖與粉專，不發文")
    a = ap.parse_args(argv)
    if a.check:
        return check(dict(os.environ))
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
