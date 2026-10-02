"""分支預覽：把每個 `preview/*` 分支的 site/ 放到部署產物的 `site/preview/<名稱>/`（DECISIONS #301）。

Andy 2026-10-03：「直接開分支給我一版可操作的，以後都這樣，避免覆蓋到原版本」。

部署（.github/workflows/pages.yml）永遠在 main 上跑：正式站照舊從 main 的 site/ 產出，
這支再把每個 `preview/*` 分支的 site/（**不含 data/**）疊到 `site/preview/<名稱>/`，並：
  ① 在預覽版 index.html 的 <head> 最前面插入 TW_PREVIEW 設定 ＋ preview_boot.js
     （localStorage 加前綴、資料改讀正式站 ../../data/、會員寫入擋下、橫幅；細節見那支的檔頭）
  ② 沿用正式站部署產物的 account_config.js（會員 API 網址是 Secret，在 main 那步就填好了）
  ③ 給預覽版的自家 JS/CSS 加版本戳（同 stamp_assets.py），commit 短碼用預覽分支的
每次部署都是整包重建，所以**分支刪掉之後下一次部署那份預覽就自動消失**，不需要另外清。

用法（工作流裡）：
    python scripts/preview_inject.py                 # 自動找 origin 上所有 preview/* 分支
    python scripts/preview_inject.py --local <名稱> <目錄>   # 本機測試：把某個目錄當成一份預覽
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tarfile
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
BOOT = Path(__file__).resolve().parent / "preview_boot.js"
PROD_URL = "https://miaozike.github.io/tw-rotation/"
PREFIX = "preview/"

sys.path.insert(0, str(ROOT / "scripts"))
import stamp_assets  # noqa: E402


def safe_name(branch: str) -> str:
    """`preview/layout-v2` → `layout-v2`；巢狀斜線換成 -，其他怪字元也換成 -（網址只留一層）。"""
    n = branch[len(PREFIX):] if branch.startswith(PREFIX) else branch
    n = re.sub(r"[^A-Za-z0-9._-]+", "-", n.replace("/", "-")).strip("-.")
    return n or "preview"


def inject_html(html: str, cfg: dict) -> str:
    """把設定與開機腳本插在 <meta charset> 之後（沒有就插在 <head> 之後）。重複執行不會插兩次。"""
    if 'id="twPreviewCfg"' in html:
        html = re.sub(r'<script id="twPreviewCfg">.*?</script>\s*<script src="preview_boot\.js[^"]*"></script>\n?',
                      "", html, flags=re.S)
    tag = ('<script id="twPreviewCfg">window.TW_PREVIEW = ' + json.dumps(cfg, ensure_ascii=False) + ';</script>'
           '<script src="preview_boot.js"></script>\n')
    m = re.search(r"<meta\s+charset=[^>]*>\s*", html, flags=re.I) or re.search(r"<head[^>]*>\s*", html, flags=re.I)
    if not m:
        return tag + html
    return html[:m.end()] + tag + html[m.end():]


def install(name: str, src_site: Path, sha: str, branch: str, site: Path = SITE) -> Path:
    """把 src_site（某分支的 site/）裝成 site/preview/<name>/。回傳目的地。"""
    dst = site / "preview" / name
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src_site, dst, ignore=shutil.ignore_patterns("data", "preview"))
    shutil.copy2(BOOT, dst / "preview_boot.js")
    acc = site / "account_config.js"
    if acc.exists():
        shutil.copy2(acc, dst / "account_config.js")
    idx = dst / "index.html"
    if idx.exists():
        cfg = {"name": name, "branch": branch, "sha": sha[:7], "dataRoot": "../../data/", "prod": PROD_URL}
        html = inject_html(idx.read_text(encoding="utf-8"), cfg)
        html, _ = stamp_assets.stamp_html(html, (sha[:8] or "preview"), sha=sha)
        idx.write_text(html, encoding="utf-8")
    return dst


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True, capture_output=True, text=True).stdout


def remote_previews() -> list[tuple[str, str]]:
    """origin 上所有 preview/* 分支：[(分支名, sha)]。"""
    out = git("ls-remote", "--heads", "origin", "refs/heads/preview/*")
    res = []
    for line in out.splitlines():
        sha, _, ref = line.partition("\t")
        if ref.startswith("refs/heads/" + PREFIX):
            res.append((ref[len("refs/heads/"):], sha))
    return res


def extract_site(branch: str, sha: str, tmp: Path) -> Path | None:
    """淺抓那個分支，把它的 site/ 解到 tmp。分支沒有 site/ 就回 None。"""
    git("fetch", "--depth", "1", "--no-tags", "origin", f"+refs/heads/{branch}:refs/twpreview/{sha}")
    try:
        data = subprocess.run(["git", "-C", str(ROOT), "archive", "--format=tar", sha, "site"],
                              check=True, capture_output=True).stdout
    except subprocess.CalledProcessError:
        return None
    with tarfile.open(fileobj=io.BytesIO(data)) as tf:
        tf.extractall(tmp, filter="data")
    return tmp / "site" if (tmp / "site").is_dir() else None


def main() -> int:
    ap = argparse.ArgumentParser(description="把 preview/* 分支裝進部署產物的 site/preview/<名稱>/")
    ap.add_argument("--local", nargs=2, metavar=("NAME", "SITE_DIR"), help="本機測試：把某個目錄裝成一份預覽")
    args = ap.parse_args()

    prev_root = SITE / "preview"
    if prev_root.exists():
        shutil.rmtree(prev_root)   # 整包重建：刪掉的分支不會殘留

    if args.local:
        name, src = args.local
        dst = install(safe_name(name), Path(src), "local000", name)
        print(f"本機預覽：{dst}")
        return 0

    branches = remote_previews()
    if not branches:
        print("沒有 preview/* 分支，不產出預覽")
        return 0
    seen: set[str] = set()
    import tempfile
    for branch, sha in branches:
        name = safe_name(branch)
        if name in seen:
            print(f"::warning::{branch} 的名稱 {name} 跟別的分支撞了，略過")
            continue
        seen.add(name)
        with tempfile.TemporaryDirectory() as td:
            src = extract_site(branch, sha, Path(td))
            if not src:
                print(f"::warning::{branch} 沒有 site/，略過")
                continue
            dst = install(name, src, sha, branch)
        size = sum(f.stat().st_size for f in dst.rglob("*") if f.is_file())
        print(f"預覽 {branch} @ {sha[:7]} → preview/{name}/（{size / 1e6:.1f} MB，不含資料）"
              f"  {PROD_URL}preview/{name}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
