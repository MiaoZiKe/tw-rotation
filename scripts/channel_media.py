"""頻道影片（Reels）的公開網址：放 GitHub Release 資產，不進 main（2026-11-15）。

Andy 原話（2026-11-15）：「我決定每天兩隻 Reels」。頻道③ CaffAIne 一天兩支影片，每支 10～30MB；
如果照頻道④的做法把 mp4 commit 進 main（佇列一份＋site/media 一份），一個月就多 1～2GB，每次 clone、
每個工作流 checkout 都要背著它。所以 channels.json 寫 "video_host": "release" 的頻道改成：

  影片本體 → 推到 media/<頻道>/<資料夾> 分支（只含 video.mp4、cover.jpg，跟 main 沒有共同歷史），
             或直接放在佇列資料夾（相容；會讓 repo 變肥，不建議）
  工作流   → sync：把影片上傳成 Release「channel-media」的資產（<頻道>__<資料夾>.mp4），網址寫進 state/media.json
             發文：healing_post.video_sources 第一條就用這個網址（IG Reels video_url、Threads VIDEO video_url）
             clean：兩個平台都發完 N 天後刪掉 Release 資產與 media 分支（分支刪掉後 GitHub 會回收那些物件）

用法：
  python scripts/channel_media.py stage --channel caffaine --folder 20261116_x --video 片.mp4 [--cover 封面.jpg]
      作者用：在本機把影片推到 media/caffaine/20261116_x 分支（不動工作目錄、不 force），
      並在佇列資料夾的 meta.json 寫 "video_src": "media/caffaine/20261116_x"（meta.json 要自己 commit 到 main）。
  python scripts/channel_media.py sync --channel caffaine          # 工作流：上傳還沒上傳／內容變了的影片
  python scripts/channel_media.py testclip --channel caffaine      # 工作流：ffmpeg 產 3 秒測試片 → @reels-test
  python scripts/channel_media.py clean --channel caffaine [--keep-days 3]

GitHub 權杖只從環境變數 GH_TOKEN／GITHUB_TOKEN 讀（工作流的 github.token），不寫進任何檔。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import healing_post as HP  # noqa: E402

TAG = "channel-media"
API = "https://api.github.com"
UPLOADS = "https://uploads.github.com"
TEST_NAME = "@reels-test"
TAIPEI = timezone(timedelta(hours=8))


def repo() -> str:
    return os.environ.get("GITHUB_REPOSITORY") or "MiaoZiKe/tw-rotation"


def asset_name(ch: str, folder: str, kind: str = "video") -> str:
    base = f"{ch}__{folder.lstrip('@')}"
    return base + (".mp4" if kind == "video" else "__cover.jpg")


def download_url(name: str) -> str:
    return f"https://github.com/{repo()}/releases/download/{TAG}/{quote(name)}"


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ---------- GitHub API（可在測試換掉）----------
class GH:
    def __init__(self, token: str):
        import requests
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                               "X-GitHub-Api-Version": "2022-11-28"})
        HP.mask(token)

    def _ok(self, r, what):
        if r.status_code >= 300:
            raise RuntimeError(f"GitHub {what} 失敗：HTTP {r.status_code} {r.text[:200]}")
        return r.json() if r.content else {}

    def release(self) -> dict:
        r = self.s.get(f"{API}/repos/{repo()}/releases/tags/{TAG}", timeout=30)
        if r.status_code == 404:
            r = self.s.post(f"{API}/repos/{repo()}/releases", timeout=30, json={
                "tag_name": TAG, "target_commitish": "main", "name": "社群影片暫存（自動發文用）",
                "body": "頻道自動發文的影片暫存區（scripts/channel_media.py）。發完幾天會自動刪掉，不是正式版本。",
                "prerelease": True, "make_latest": "false"})
            return self._ok(r, "建立 Release")
        return self._ok(r, "讀 Release")

    def assets(self, rel: dict) -> dict:
        out, page = {}, 1
        while True:
            r = self.s.get(f"{API}/repos/{repo()}/releases/{rel['id']}/assets", params={"per_page": 100, "page": page},
                           timeout=30)
            xs = self._ok(r, "列資產")
            out.update({a["name"]: a for a in xs})
            if len(xs) < 100:
                return out
            page += 1

    def delete_asset(self, aid) -> None:
        r = self.s.delete(f"{API}/repos/{repo()}/releases/assets/{aid}", timeout=30)
        if r.status_code not in (204, 404):
            self._ok(r, "刪資產")

    def upload(self, rel: dict, name: str, data: bytes, ctype: str) -> dict:
        r = self.s.post(f"{UPLOADS}/repos/{repo()}/releases/{rel['id']}/assets", params={"name": name},
                        headers={"Content-Type": ctype}, data=data, timeout=600)
        return self._ok(r, f"上傳 {name}")

    def delete_branch(self, branch: str) -> bool:
        r = self.s.delete(f"{API}/repos/{repo()}/git/refs/heads/{quote(branch)}", timeout=30)
        if r.status_code in (204, 422, 404):
            return r.status_code == 204
        self._ok(r, f"刪分支 {branch}")
        return False


def gh_from_env() -> GH:
    t = (os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or "").strip()
    if not t:
        raise SystemExit("沒有 GH_TOKEN／GITHUB_TOKEN（工作流要帶 github.token）")
    return GH(t)


# ---------- 影片來源 ----------
def branch_file(branch: str, fname: str, cwd: Path = HP.ROOT) -> bytes | None:
    """從 media 分支拿檔案（只抓那個分支的最新一個 commit）；沒有回 None。"""
    f = subprocess.run(["git", "fetch", "-q", "--depth", "1", "origin", f"refs/heads/{branch}"], cwd=cwd,
                       capture_output=True)
    if f.returncode != 0:
        return None
    r = subprocess.run(["git", "show", f"FETCH_HEAD:{fname}"], cwd=cwd, capture_output=True)
    return r.stdout if r.returncode == 0 and r.stdout else None


def source(d: Path, meta: dict, fname: str, fetch=branch_file) -> tuple[bytes | None, str]:
    """（內容, 來源說明）：佇列資料夾裡有就用；否則 meta.video_src 指的 media 分支。"""
    if (d / fname).is_file():
        return (d / fname).read_bytes(), "queue"
    br = str(meta.get("video_src") or "")
    if br.startswith("media/"):
        b = fetch(br, fname)
        if b:
            return b, br
    return None, ""


def load_media(state: Path) -> dict:
    m = HP.load_json(state / "media.json", {})
    return m if isinstance(m, dict) else {}


def save_media(state: Path, m: dict) -> None:
    p, txt = state / "media.json", json.dumps(m, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    if (p.is_file() and p.read_text(encoding="utf-8") == txt) or (not p.is_file() and not m):
        return               # 沒變（或一直是空的）就不寫，免得每輪多一個 commit
    state.mkdir(parents=True, exist_ok=True)
    p.write_text(txt, encoding="utf-8")


def _put(gh, rel, have: dict, name: str, data: bytes, ctype: str) -> str:
    old = have.get(name)
    if old:
        gh.delete_asset(old["id"])
    gh.upload(rel, name, data, ctype)
    return download_url(name)


def sync(code: str, gh=None, fetch=branch_file, now: datetime | None = None) -> list[str]:
    """佇列裡 format=video、還沒發完的影片 → 上傳到 Release（內容雜湊一樣就跳過）。回傳做了什麼。"""
    ch = HP.channel(code)
    q, st = ch["queue"], ch["state"]
    now = now or datetime.now(TAIPEI)
    media, posted = load_media(st), HP.load_json(st / "posted.json", {})
    log, rel, have = [], None, None
    for d in sorted(x for x in q.iterdir() if x.is_dir()) if q.is_dir() else []:
        meta = HP.load_json(d / "meta.json", {})
        if not isinstance(meta, dict) or meta.get("format") != "video" or meta.get("status") not in ("draft", "approved"):
            continue
        plats = meta.get("platforms") or list(HP.PLATFORMS)
        if all(p in (posted.get(d.name) or {}) for p in plats):
            continue
        vid, via = source(d, meta, HP.VIDEO_FILE, fetch)
        if not vid:
            log.append(f"{d.name}：找不到影片（佇列沒有 video.mp4，meta.video_src={meta.get('video_src')!r} 也抓不到）")
            continue
        if len(vid) > HP.RELEASE_MAX_BYTES:
            log.append(f"{d.name}：影片 {len(vid) / 1048576:.1f}MB 超過 {HP.RELEASE_MAX_BYTES // 1048576}MB，沒上傳")
            continue
        cov, _ = source(d, meta, HP.COVER_FILE, fetch)
        e = media.get(d.name) or {}
        if e.get("sha256") == sha256(vid) and (not cov or e.get("cover_sha256") == sha256(cov)):
            log.append(f"{d.name}：Release 上已經是同一支，跳過")
            continue
        try:          # 一支上傳失敗不擋其他支；發文那步還有佇列裡的 raw 網址可以保底（影片有放在佇列時）
            if gh is None:
                gh = gh_from_env()
            if rel is None:
                rel = gh.release()
                have = gh.assets(rel)
            e = {"video": _put(gh, rel, have, asset_name(code, d.name), vid, "video/mp4"), "sha256": sha256(vid),
                 "bytes": len(vid), "src": via, "at": now.isoformat(timespec="seconds")}
            if cov:
                e["cover"] = _put(gh, rel, have, asset_name(code, d.name, "cover"), cov, "image/jpeg")
                e["cover_sha256"] = sha256(cov)
        except Exception as ex:  # noqa: BLE001
            print(f"::warning::{d.name} 上傳 Release 失敗：{str(ex)[:200]}")
            log.append(f"{d.name}：上傳 Release 失敗：{str(ex)[:200]}")
            continue
        media[d.name] = e
        log.append(f"{d.name}：已上傳 {len(vid) / 1048576:.1f}MB（來源 {via}）→ {e['video']}")
    save_media(st, media)
    return log


def make_clip(out_dir: Path) -> tuple[bytes, bytes]:
    """ffmpeg 產 3 秒 1080×1920 30fps H.264＋AAC（靜音）測試片與一張封面 JPEG。只給驗證模式用，不會發布。"""
    v, c = out_dir / "t.mp4", out_dir / "t.jpg"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    "testsrc2=size=1080x1920:rate=30:duration=3", "-f", "lavfi", "-i",
                    "anullsrc=channel_layout=stereo:sample_rate=48000", "-t", "3", "-shortest",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high", "-c:a", "aac", "-b:a", "128k",
                    "-movflags", "+faststart", str(v)], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(v), "-frames:v", "1", "-q:v", "3", str(c)],
                   check=True)
    return v.read_bytes(), c.read_bytes()


def testclip(code: str, gh=None, maker=make_clip, now: datetime | None = None) -> str:
    ch = HP.channel(code)
    st = ch["state"]
    now = now or datetime.now(TAIPEI)
    with tempfile.TemporaryDirectory() as td:
        vid, cov = maker(Path(td))
    gh = gh or gh_from_env()
    rel = gh.release()
    have = gh.assets(rel)
    media = load_media(st)
    media[TEST_NAME] = {"video": _put(gh, rel, have, asset_name(code, TEST_NAME), vid, "video/mp4"),
                        "cover": _put(gh, rel, have, asset_name(code, TEST_NAME, "cover"), cov, "image/jpeg"),
                        "sha256": sha256(vid), "bytes": len(vid), "src": "ffmpeg", "at": now.isoformat(timespec="seconds")}
    save_media(st, media)
    return media[TEST_NAME]["video"]


def clean(code: str, keep_days: int = 3, gh=None, now: datetime | None = None) -> list[str]:
    """兩個平台都發完、最後一個平台發出超過 keep_days 天 → 刪 Release 資產與 media 分支；測試片 1 天後刪。"""
    ch = HP.channel(code)
    q, st = ch["queue"], ch["state"]
    now = now or datetime.now(TAIPEI)
    media, posted = load_media(st), HP.load_json(st / "posted.json", {})
    log, drop = [], []
    for name, e in media.items():
        if name.startswith("@"):
            at = datetime.fromisoformat(e.get("at", "2000-01-01T00:00:00+08:00"))
            if now - at > timedelta(days=1):
                drop.append(name)
            continue
        meta = HP.load_json(q / name / "meta.json", {})
        plats = (meta.get("platforms") if isinstance(meta, dict) else None) or list(HP.PLATFORMS)
        done = posted.get(name) or {}
        if not isinstance(meta, dict) or not meta:          # 佇列資料夾已經不在 → 也清掉
            drop.append(name)
            continue
        if not all(p in done for p in plats):
            continue
        last = max(datetime.fromisoformat(done[p]["at"]) for p in plats)
        if now - last > timedelta(days=keep_days):
            drop.append(name)
    if not drop:
        return ["沒有要清的影片"]
    gh = gh or gh_from_env()
    rel = gh.release()
    have = gh.assets(rel)
    for name in drop:
        for kind in ("video", "cover"):
            a = have.get(asset_name(code, name, kind))
            if a:
                gh.delete_asset(a["id"])
        br = f"media/{code}/{name}"
        gone = gh.delete_branch(br) if not name.startswith("@") else False
        media.pop(name, None)
        log.append(f"{name}：已刪 Release 資產" + ("、分支 " + br if gone else ""))
    save_media(st, media)
    return log


# ---------- 作者用：把影片推到 media 分支 ----------
def git(*args, cwd: Path = HP.ROOT, input_: bytes | None = None, env=None) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, input=input_, capture_output=True, env=env)
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} 失敗：{r.stderr.decode(errors='replace')[:300]}")
    return r.stdout.decode().strip()


def stage(code: str, folder: str, video: Path, cover: Path | None = None, push: bool = True,
          cwd: Path = HP.ROOT) -> str:
    """不動工作目錄：用 git 底層指令做一個只有 video.mp4（＋cover.jpg）的 commit，推到 media/<頻道>/<資料夾>。
    分支已經存在 → 新 commit 接在它後面（一般 push，不 force）。回傳分支名。"""
    ch = HP.channel(code)
    if not video.is_file():
        raise SystemExit(f"找不到影片 {video}")
    if video.stat().st_size > HP.RELEASE_MAX_BYTES:
        raise SystemExit(f"影片 {video.stat().st_size / 1048576:.1f}MB 超過 {HP.RELEASE_MAX_BYTES // 1048576}MB，請先壓縮")
    br = f"media/{code}/{folder}"
    rows = [f"100644 blob {git('hash-object', '-w', str(video.resolve()), cwd=cwd)}\t{HP.VIDEO_FILE}"]
    if cover:
        rows.append(f"100644 blob {git('hash-object', '-w', str(cover.resolve()), cwd=cwd)}\t{HP.COVER_FILE}")
    tree = git("mktree", cwd=cwd, input_=("\n".join(sorted(rows, key=lambda x: x.split("\t")[1])) + "\n").encode())
    parent = []
    rem = subprocess.run(["git", "ls-remote", "origin", f"refs/heads/{br}"], cwd=cwd, capture_output=True, text=True)
    if push and rem.stdout.strip():
        sha = rem.stdout.split()[0]
        git("fetch", "-q", "--depth", "1", "origin", f"refs/heads/{br}", cwd=cwd)
        parent = ["-p", sha]
    commit = git("commit-tree", tree, *parent, "-m", f"{code}：{folder} 影片（自動發文用，發完會刪這個分支）", cwd=cwd)
    if push:
        git("push", "origin", f"{commit}:refs/heads/{br}", cwd=cwd)
    meta_p = ch["queue"] / folder / "meta.json"
    if meta_p.is_file():
        m = json.loads(meta_p.read_text(encoding="utf-8"))
        m.update(format="video", video_src=br)
        meta_p.write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return br


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="頻道影片放 GitHub Release（不進 main）")
    ap.add_argument("cmd", choices=["stage", "sync", "testclip", "clean"])
    ap.add_argument("--channel", required=True)
    ap.add_argument("--folder", default="")
    ap.add_argument("--video", default="")
    ap.add_argument("--cover", default="")
    ap.add_argument("--keep-days", type=int, default=3)
    a = ap.parse_args(argv)
    ch = HP.channel(a.channel)
    if ch.get("video_host") != "release":
        print(f"{a.channel} 沒有設 video_host=release，什麼都不做")
        return 0
    if a.cmd == "stage":
        if not a.folder or not a.video:
            ap.error("stage 要給 --folder 與 --video")
        br = stage(a.channel, a.folder, Path(a.video), Path(a.cover) if a.cover else None)
        print(f"已推到分支 {br}；佇列資料夾的 meta.json 已寫 video_src（記得把 meta.json、caption.txt commit 到 main）")
        return 0
    if a.cmd == "sync":
        out = sync(a.channel)
    elif a.cmd == "testclip":
        out = ["測試片：" + testclip(a.channel)]
    else:
        out = clean(a.channel, a.keep_days)
    for x in out:
        print(x)
    summ = os.environ.get("GITHUB_STEP_SUMMARY")
    if summ:
        with open(summ, "a", encoding="utf-8") as f:
            f.write(f"### {ch.get('name', a.channel)} 影片 Release（{a.cmd}）\n\n" + "\n".join(f"- {x}" for x in out) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
