"""部署前把「要發佈出去的」自家 JS／CSS／HTML 壓縮並拿掉所有註解（2026-10-06 資安）。

為什麼
------
Andy 2026-10-06：「我發現點選 F12 會有我下過的 Prompt，這會透漏我如何建立這網頁的資訊，幫我修正」。
site/*.js 原本原封不動發佈，註解裡有大量開發過程與內部口徑，F12 → Sources 一打開就看得到。

做法
----
- **只改部署產物**：工作流在 checkout 出來的 site/ 上跑這支，repo 裡的原始碼保留註解（開發要用）。
- JS／CSS 用 esbuild（pages.yml 以 `npm i -g esbuild@<鎖定版本>` 安裝）`--minify --legal-comments=none`。
  非模組的傳統 <script>：esbuild 不改頂層名稱（跨檔共用的全域函式照舊可用），只縮區域變數與空白。
- HTML：拿掉 `<!-- -->` 註解，並把內嵌 <style>／<script> 也交給 esbuild 壓縮。
  不動標籤之間的空白（<pre>、行內文字的間距會受影響，風險大於收益）。
- vendor/（第三方，已是官方發佈版）與 data/（工作流產出的 JSON）不動。
- 刪掉所有 *.map（source map 一律不准發佈），並移除 `sourceMappingURL` 註記。
- 任何一支壓縮失敗 → 整步失敗（exit 1），不要發佈「一半壓了一半沒壓」的站。

用法：
    python scripts/minify_site.py [site 目錄]       # 預設 <repo>/site
    ESBUILD=/path/to/esbuild python scripts/minify_site.py
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {"vendor", "data"}

INLINE = re.compile(r'(<(script|style)\b(?P<attrs>[^>]*)>)(?P<body>.*?)(</\2\s*>)', re.S | re.I)
HTML_COMMENT = re.compile(r'<!--(?!\[if).*?-->', re.S)
# esbuild 只拿得掉「程式的」註解；寫在樣板字串裡的 CSS 註解（`<style>` 樣板、textContent=`...`）
# 與 HTML 註解（innerHTML 樣板）它不敢動。壓縮後真正的註解已全清，所以剩下的 /* */ 與 <!-- -->
# 一定在字串裡 —— 範圍不准跨過反引號與 ${（不會吃到樣板外的程式碼），長度上限 4000 字。
# 2026-10-06 實測：77 檔、這兩種共清掉約 390 處，事後再掃 `/*`、`<!--` 為 0。
STR_CSS_COMMENT = re.compile(r'/\*(?:(?!\*/)[^`$]){0,4000}?\*/')
STR_HTML_COMMENT = re.compile(r'<!--(?:(?!-->)[^`]){0,4000}?-->')
# site/modules.js 的積木清單裡每塊有 `note`（為什麼這樣放，內部決策文字），執行期不讀它，只有 _uitest 讀 repo 原檔。
MODULE_NOTE = re.compile(r'"note"\s*:\s*"(?:[^"\\]|\\.)*"\s*,?')
SRCMAP = re.compile(r'/[/*]#\s*sourceMappingURL=[^\n*]*(\*/)?')


def esbuild_bin() -> str:
    b = os.environ.get("ESBUILD") or shutil.which("esbuild")
    if not b:
        sys.exit("找不到 esbuild：請先 npm i -g esbuild@0.28.2 或設定 ESBUILD")
    return b


def esb(code: str, loader: str, binp: str) -> str:
    r = subprocess.run([binp, f"--loader={loader}", "--minify", "--legal-comments=none", "--charset=utf8"],
                       input=code.encode("utf-8"), capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode("utf-8", "replace")[:2000])
    return r.stdout.decode("utf-8").rstrip("\n")


def minify_html(text: str, binp: str) -> str:
    # 先處理內嵌 script/style（內文裡可能有長得像 <!-- 的字串，先保護起來）
    blocks: list[str] = []

    def keep(m: re.Match) -> str:
        attrs = m.group("attrs") or ""
        body = m.group("body")
        tag = m.group(2).lower()
        if body.strip() and "src=" not in attrs:
            t = re.search(r'type\s*=\s*"([^"]*)"', attrs)
            typ = (t.group(1).lower() if t else "")
            if tag == "style":
                body = esb(body, "css", binp)
            elif typ in ("", "text/javascript", "application/javascript", "module"):
                body = esb(body, "js", binp)
        blocks.append(m.group(1) + body + m.group(5))
        return f"\x00{len(blocks) - 1}\x00"

    text = INLINE.sub(keep, text)
    text = HTML_COMMENT.sub("", text)
    text = re.sub(r'\x00(\d+)\x00', lambda m: blocks[int(m.group(1))], text)
    return text


def main(site: Path) -> int:
    binp = esbuild_bin()
    n = before = after = 0
    for p in sorted(site.rglob("*")):
        if not p.is_file() or SKIP_DIRS & set(p.relative_to(site).parts[:-1]):
            continue
        if p.suffix == ".map":
            p.unlink()
            print(f"刪除 source map：{p.relative_to(site)}")
            continue
        if p.suffix not in (".js", ".css", ".html"):
            continue
        src = p.read_text(encoding="utf-8")
        if p.name == "modules.js":
            src = MODULE_NOTE.sub("", src)
        try:
            if p.suffix == ".html":
                out = minify_html(src, binp)
            else:
                out = esb(src, p.suffix[1:], binp)
                if p.suffix == ".js":
                    out = STR_CSS_COMMENT.sub("", STR_HTML_COMMENT.sub("", out))
        except RuntimeError as e:
            print(f"::error::壓縮失敗 {p.relative_to(site)}：{e}")
            return 1
        out = SRCMAP.sub("", out)
        p.write_text(out + "\n", encoding="utf-8")
        n += 1
        before += len(src.encode("utf-8"))
        after += len(out.encode("utf-8"))
    print(f"壓縮 {n} 檔：{before/1024:.0f} KB → {after/1024:.0f} KB（不含 vendor/、data/）")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "site"))
