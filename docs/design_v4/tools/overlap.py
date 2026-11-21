"""設計 v4：三頁 × 四寬度 × 三主題的文字重疊與水平溢出掃描。

重疊判準直接借 scripts/_preview.py 的 OVERLAP_JS（同一套規則，不另寫一套）；
溢出＝documentElement.scrollWidth − clientWidth > 1（整頁出現水平捲軸）。
_preview.py 本身只跑 1500 與 390 兩個寬度，這支補 1440／1100／800／390 與三主題。

用法：flock /tmp/claude-0/browser.lock python docs/design_v4/tools/overlap.py
"""
from __future__ import annotations

import json
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from _preview import OVERLAP_JS, CONSENT_PRESET  # noqa: E402

PAGES = ["overview", "flow", "stock/2330"]
WIDTHS = [1440, 1100, 800, 390]
THEMES = [("casual", "light"), ("hud", "dark"), ("pro", "light"), ("casual", "dark"), ("hud", "light"), ("pro", "dark")]


class Q(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def main() -> int:
    from playwright.sync_api import sync_playwright
    import os
    # TW_OVERLAP_SITE：指向改前的網站快照，量「這個重疊是不是本來就有」（改前沒有 v4，風格設定會被忽略）
    site = os.environ.get("TW_OVERLAP_SITE") or str(ROOT / "site")
    srv = ThreadingHTTPServer(("127.0.0.1", 8795), partial(Q, directory=site))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    bad = []
    rows = []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        for t4, mode in THEMES:
            widths = WIDTHS if (t4, mode) in THEMES[:3] else [1440]
            for w in widths:
                ctx = b.new_context(viewport={"width": w, "height": 844 if w <= 480 else 900},
                                    is_mobile=w <= 480, has_touch=w <= 480)
                ctx.add_init_script(CONSENT_PRESET)
                ctx.add_init_script(f"try{{localStorage.setItem('tw.theme4','{t4}');localStorage.setItem('tw.theme','{mode}');}}catch(e){{}}")
                pg = ctx.new_page()
                errs = []
                pg.on("pageerror", lambda e: errs.append(str(e)))
                for route in PAGES:
                    pg.goto(f"http://127.0.0.1:8795/index.html#{route}", wait_until="networkidle")
                    pg.wait_for_timeout(3000)
                    ov = pg.evaluate(OVERLAP_JS)
                    sx = pg.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                    ledes = pg.evaluate("[...document.querySelectorAll('.t4-lede')].map(p => p.textContent)")
                    rows.append({"theme": f"{t4}-{mode}", "w": w, "route": route, "overlaps": len(ov), "overflowX": sx,
                                 "ledes": ledes, "errs": errs[:]})
                    if ov or sx > 1 or errs:
                        bad.append((f"{t4}-{mode}", w, route, ov[:3], sx, errs[:2]))
                    print(f"{t4}-{mode} {w} {route}: 重疊 {len(ov)}、水平溢出 {sx}px、結論 {len(ledes)} 句、錯誤 {len(errs)}", flush=True)
                    errs.clear()
                ctx.close()
        b.close()
    srv.shutdown()
    out = ROOT / "docs" / "design_v4" / "data" / ("overlap-before.json" if os.environ.get("TW_OVERLAP_SITE") else "overlap.json")
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n有問題的組合：{len(bad)}")
    for x in bad:
        print("  ", json.dumps(x, ensure_ascii=False)[:400])
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
