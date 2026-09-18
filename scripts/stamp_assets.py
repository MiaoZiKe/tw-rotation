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
TPE = timezone(timedelta(hours=8))
INDEX = ROOT / "site" / "index.html"

# 只戳自家的檔。vendor/ 的第三方函式庫不動（大、且幾乎不變）。
PATTERN = re.compile(
    r'(?P<attr>\b(?:src|href)=")(?P<file>(?!https?:|//|vendor/)[^"?#]+\.(?:js|css))'
    r'(?P<query>\?[^"]*)?(?P<tail>")'
)

# 給人看的版號（Andy 2026-09-16：「每次說有更新，但打開來跟原本一樣，網頁需要新增版號」）。
# 上面那個 ?v= 是給瀏覽器看的（不讓它用舊快取），人看不到；這個 meta 是給人看的。
BUILD_META = re.compile(r'(<meta\s+name="tw:build"\s+content=")(?P<val>[^"]*)(")')
# commit 短碼從版號裡拿掉之後，另外放一個 meta 給徽章的連結與 tooltip 用
SHA_META = re.compile(r'(<meta\s+name="tw:commit"\s+content=")(?P<val>[^"]*)(")')


def stamp_value() -> str:
    """GitHub Actions 上用 commit SHA 前 8 碼；本機就用 UTC 時間。"""
    sha = os.environ.get("GITHUB_SHA", "")
    if sha:
        return sha[:8]
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def builds_today(now: datetime, root: Path = ROOT) -> int:
    """今天（台北）是第幾次改動：數 HEAD 上「今天」的 commit 數。

    用 git 而不是自己存一個計數器，是因為部署跑在乾淨的 checkout 上，
    沒有地方存狀態；而 commit 紀錄本來就在，數它最準也最不會走鐘。
    數不出來（沒有 git、淺 clone）就回 0，呼叫端會退回只寫日期。
    """
    import subprocess
    tpe = now.astimezone(TPE)
    since = tpe.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    try:
        out = subprocess.run(["git", "-C", str(root), "rev-list", "--count",
                              f"--since={since}", "HEAD"],
                             capture_output=True, text=True, timeout=20)
        return int((out.stdout or "0").strip() or 0) if out.returncode == 0 else 0
    except Exception:  # noqa: BLE001 —— 版號不該讓部署死掉
        return 0


def build_label(now: datetime | None = None, sha: str | None = None,
                seq: int | None = None) -> str:
    """給人看的版號：`<西元-月-日 第 N 版>|<HH:MM 台北>`。

    Andy 2026-09-18：「版號用西元＋日期，以及第幾次改動命名」。
    之前是 commit 前 7 碼 —— 對得上 GitHub，但人看不出「這是今天第幾版」，
    也看不出兩個版本誰新誰舊（sha 是亂碼，沒有順序）。
    現在是 `2026-09-18 第 3 版`：一眼知道是哪一天、當天第幾次改動、誰比較新。
    commit 短碼沒有丟掉 —— 它移到徽章的 title 與連結上，要對照 GitHub 時還在。

    本機沒有 GITHUB_SHA 就在後面標 `local`（看到就代表這不是部署出來的版本）。
    時間一定會往前走，所以同一個 commit 重跑一次部署也看得出來換過版。
    """
    now = now or datetime.now(timezone.utc)
    tpe = now.astimezone(TPE)
    sha = sha if sha is not None else os.environ.get("GITHUB_SHA", "")
    n = builds_today(now) if seq is None else seq
    ver = f"{tpe:%Y-%m-%d}" + (f" 第 {n} 版" if n > 0 else "")
    if not sha:
        ver += "（local）"
    return f"{ver}|{tpe:%H:%M}"


def stamp_html(html: str, stamp: str, now: datetime | None = None,
               sha: str | None = None, seq: int | None = None) -> tuple[str, int]:
    """回傳 (加好戳記的 HTML, 改了幾個)。重複執行是安全的 —— 舊戳記會被換掉。"""
    n = 0

    def sub(m: re.Match) -> str:
        nonlocal n
        n += 1
        return f'{m.group("attr")}{m.group("file")}?v={stamp}{m.group("tail")}'

    out = PATTERN.sub(sub, html)
    label = build_label(now, sha, seq)
    out, k = BUILD_META.subn(lambda m: m.group(1) + label + m.group(3), out)
    if not k:
        print('[WARN] 找不到 <meta name="tw:build">，頁面上不會顯示版號')
    csha = (sha if sha is not None else os.environ.get("GITHUB_SHA", ""))[:7]
    out = SHA_META.sub(lambda m: m.group(1) + csha + m.group(3), out)
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
