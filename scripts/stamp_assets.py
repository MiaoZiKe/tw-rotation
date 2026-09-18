"""部署前把 `site/index.html` 的自家 JS／CSS 加上版本戳，讓瀏覽器一定拿到新版。

為什麼需要這個（2026-09-14 實際踩到）
------------------------------------
`index.html` 裡是 `<script src="app.js"></script>`，沒有版本號。
GitHub Pages 會給這些檔案快取標頭，所以**部署完之後重新整理看到的還是舊的 JS**。
那天的實測：

    瀏覽器實際載到的 app.js   124,428 bytes  ← 舊版
    伺服器上的新版 app.js     125,114 bytes

畫面於是「看起來沒更新」，只有按 Ctrl+F5 才會換過來。
Andy 的原話是「這連結我沒看到最新資訊」—— 東西其實早就部署好了。

做法：部署前把 src/href 改成 `app.js?v=<戳記>`。檔名一變，瀏覽器就一定重抓。

**vendor/ 不加戳記**：那些是 ECharts、Lightweight Charts、three.js，
一個好幾百 KB 又幾乎不會變，每次部署都讓人重抓是白白浪費頻寬。

用法：
    python scripts/stamp_assets.py            # 用 GITHUB_SHA，沒有就用時間
    python scripts/stamp_assets.py --stamp x  # 指定戳記（測試用）
"""
from __future__ import annotations

import argparse
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "site" / "index.html"

# 只戳自家的檔。vendor/ 的第三方函式庫不動（大、且幾乎不變）。
PATTERN = re.compile(
    r'(?P<attr>\b(?:src|href)=")(?P<file>(?!https?:|//|vendor/)[^"?#]+\.(?:js|css))'
    r'(?P<query>\?[^"]*)?(?P<tail>")'
)

# 給人看的版號（Andy 2026-09-16：「每次說有更新，但打開來跟原本一樣，網頁需要新增版號」）。
# 上面那個 ?v= 是給瀏覽器看的（不讓它用舊快取），人看不到；這個 meta 是給人看的。
BUILD_META = re.compile(r'(<meta\s+name="tw:build"\s+content=")(?P<val>[^"]*)(")')


def stamp_value() -> str:
    """GitHub Actions 上用 commit SHA 前 8 碼；本機就用 UTC 時間。"""
    sha = os.environ.get("GITHUB_SHA", "")
    if sha:
        return sha[:8]
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def build_label(now: datetime | None = None, sha: str | None = None) -> str:
    """給人看的版號：`<commit 前 7 碼>|<MM-DD HH:MM 台北>`。

    前 7 碼跟 GitHub 網頁上顯示的 commit 短碼一樣，可以直接對照。
    本機沒有 GITHUB_SHA 就寫 `local`（看到 local 就代表這不是部署出來的版本）。
    時間一定會往前走，所以就算 SHA 沒變（同一個 commit 重跑一次部署），也看得出來換過版。
    """
    now = now or datetime.now(timezone.utc)
    tpe = now.astimezone(timezone(timedelta(hours=8)))
    sha = sha if sha is not None else os.environ.get("GITHUB_SHA", "")
    return f"{sha[:7] if sha else 'local'}|{tpe:%m-%d %H:%M}"


def stamp_html(html: str, stamp: str, now: datetime | None = None,
               sha: str | None = None) -> tuple[str, int]:
    """回傳 (加好戳記的 HTML, 改了幾個)。重複執行是安全的 —— 舊戳記會被換掉。"""
    n = 0

    def sub(m: re.Match) -> str:
        nonlocal n
        n += 1
        return f'{m.group("attr")}{m.group("file")}?v={stamp}{m.group("tail")}'

    out = PATTERN.sub(sub, html)
    label = build_label(now, sha)
    out, k = BUILD_META.subn(lambda m: m.group(1) + label + m.group(3), out)
    if not k:
        print('[WARN] 找不到 <meta name="tw:build">，頁面上不會顯示版號')
    return out, n


def main() -> int:
    ap = argparse.ArgumentParser(description="部署前給 site/index.html 的自家資源加版本戳")
    ap.add_argument("--stamp", default=None)
    ap.add_argument("--sha", default=None, help="給人看的版號用哪個 commit（預設讀 GITHUB_SHA）")
    ap.add_argument("--file", default=str(INDEX))
    args = ap.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"[FAIL] 找不到 {path}")
        return 1
    stamp = args.stamp or stamp_value()
    out, n = stamp_html(path.read_text(encoding="utf-8"), stamp, sha=args.sha)
    path.write_text(out, encoding="utf-8")
    print(f"已加上版本戳 v={stamp}，共 {n} 個資源（vendor/ 不動）")
    print(f"頁面上顯示的版號：{build_label(sha=args.sha)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
