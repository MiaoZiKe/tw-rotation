"""手機版 v3 原型的本機伺服器（docs/mobile_v3_spec.md §6）。

用法（在 repo 根目錄）：
    python docs/mobile_v3_proto/serve.py            # 開在 http://127.0.0.1:8796/proto/index.html
然後用手機寬（390／360）打開；驗收腳本在 docs/mobile_v3_proto/shot.py。

做的事只有兩件：
  1. 從 site/index.html 抽出 <style>…</style> 寫成 proto/site.css（原型拿站上的 token 與剖析圖樣式當底，
     不另抄一份會過期的 CSS —— 所以 site.css 不進版控）
  2. 起一個伺服器，根目錄底下同時看得到 proto/ 與 site/（原型用 ../site/data/*.json 的真資料、
     ../site/diagrams.js ＋ dg/*.js ＋ three3d.js 的真圖）

⚠ site/data/ 是工作流產出、不進版控；本機要先有一份（python -m pipeline.build_payload），不然原型畫不出東西。
"""
from __future__ import annotations

import os
import re
import sys
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PORT = int(os.environ.get("TW_PROTO_PORT", "8796"))


def build() -> Path:
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    m = re.search(r"<style>(.*?)</style>", html, re.S)
    if not m:
        sys.exit("site/index.html 裡找不到 <style>")
    (HERE / "site.css").write_text(m.group(1), encoding="utf-8")
    top = Path(tempfile.mkdtemp(prefix="twproto-"))
    (top / "proto").symlink_to(HERE)
    (top / "site").symlink_to(ROOT / "site")
    return top


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):  # noqa: D102
        pass


def serve(block: bool = True) -> ThreadingHTTPServer:
    top = build()
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), partial(_Quiet, directory=str(top)))
    if block:
        print(f"http://127.0.0.1:{PORT}/proto/index.html")
        srv.serve_forever()
    else:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


if __name__ == "__main__":
    serve()
