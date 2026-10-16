"""產生 site/index.html 裡「手機分功能 CSS」那一段 <link>（site/m4/*.css，依檔名排序）。

2026-10-16 拆檔防合併衝突：多個 agent 同時往 mobile4.css 尾巴加段落，合併 main 一天衝突三次。
新的手機樣式一律寫成 site/m4/<yyyymmdd>-<名稱>.css，再跑這支把它登記進 index.html。

  python scripts/m4_css_links.py          # 重寫 index.html 那一段（合併撞到這一段時也是跑這行解決）
  python scripts/m4_css_links.py --check  # 只檢查：檔案跟 <link> 對不上就回 1（precheck 用）

載入位置：mobile4.css 正後方、fit.css 前面 —— 跟這些規則還寫在 mobile4.css 尾巴時的層疊順序一樣。
檔名排序＝層疊順序（Python sorted，逐字元比）：同一天要排先後就加兩位數序號，例如 20261016-01-xxx.css。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "site" / "index.html"
M4 = ROOT / "site" / "m4"
BEGIN = "<!-- m4:css 開始（scripts/m4_css_links.py 依 site/m4/*.css 檔名排序產生，不要手改；合併撞到這段就重跑那支） -->"
END = "<!-- m4:css 結束 -->"
BLOCK = re.compile(r"<!-- m4:css 開始[^\n]*-->\n(?:.*\n)*?<!-- m4:css 結束 -->\n")
ANCHOR = '<link rel="stylesheet" href="mobile4.css">\n'


def want() -> str:
    files = sorted(p.name for p in M4.glob("*.css")) if M4.is_dir() else []
    return BEGIN + "\n" + "".join(f'<link rel="stylesheet" href="m4/{f}">\n' for f in files) + END + "\n"


def render(html: str) -> str:
    if BLOCK.search(html):
        return BLOCK.sub(lambda m: want(), html, count=1)
    if html.count(ANCHOR) != 1:
        raise SystemExit("[m4_css_links] index.html 找不到唯一一行 mobile4.css 的 <link>")
    return html.replace(ANCHOR, ANCHOR + want(), 1)


def main() -> int:
    html = INDEX.read_text(encoding="utf-8")
    if "<<<<<<<" in html or ">>>>>>>" in html:
        # 合併撞到這一段：把衝突標記之間的 m4 連結全部丟掉，重新產生（只處理衝突完全落在這一段裡的情況）
        html = re.sub(r"<<<<<<< [^\n]*\n((?:<link rel=\"stylesheet\" href=\"m4/[^\"]+\">\n)*)=======\n"
                      r"((?:<link rel=\"stylesheet\" href=\"m4/[^\"]+\">\n)*)>>>>>>> [^\n]*\n", "", html)
    new = render(html)
    if "--check" in sys.argv:
        if new != INDEX.read_text(encoding="utf-8"):
            print("❌ site/index.html 的 m4 CSS 連結跟 site/m4/*.css 對不上 → 跑 python scripts/m4_css_links.py")
            return 1
        print("✅ m4 CSS 連結跟 site/m4/*.css 一致")
        return 0
    INDEX.write_text(new, encoding="utf-8")
    print("已更新 site/index.html 的 m4 CSS 連結：", ", ".join(sorted(p.name for p in M4.glob("*.css"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
