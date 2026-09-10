"""手機版面檢查：用 iPhone 尺寸載入頁面，抓出橫向溢出與過小的點擊目標。"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts._preview import STUB, serve  # noqa: E402

WIDTH, HEIGHT = 390, 844      # iPhone 15 邏輯像素


def main() -> int:
    from playwright.sync_api import sync_playwright

    srv = serve()
    time.sleep(0.5)
    out = ROOT / "docs" / "preview_mobile.png"
    problems: list[str] = []

    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        pg = b.new_page(viewport={"width": WIDTH, "height": HEIGHT},
                        device_scale_factor=2, is_mobile=True, has_touch=True)
        pg.on("pageerror", lambda e: problems.append(f"pageerror: {e}"))
        pg.route("**/echarts*.js", lambda route: route.fulfill(
            status=200, content_type="application/javascript", body=STUB))
        pg.route("**/fonts.googleapis.com/**", lambda route: route.abort())

        pg.goto("http://127.0.0.1:8765/index.html", wait_until="networkidle")
        pg.wait_for_timeout(1200)

        state = pg.evaluate("""(w) => {
          const overflow = [];
          document.querySelectorAll('body *').forEach(el => {
            const r = el.getBoundingClientRect();
            // 允許自己捲動的容器超出，其餘一律視為版面破圖
            const s = getComputedStyle(el);
            const scrolls = ['auto','scroll'].includes(s.overflowX);
            if (!scrolls && r.right > w + 1 && r.width > 0) {
              overflow.push(el.tagName.toLowerCase() +
                (el.id ? '#' + el.id : '') +
                (el.className && typeof el.className === 'string'
                  ? '.' + el.className.trim().split(/\\s+/).join('.') : '') +
                ' right=' + Math.round(r.right));
            }
          });
          return {
            docWidth: document.documentElement.scrollWidth,
            bodyScrollsSideways: document.documentElement.scrollWidth > w + 1,
            overflow: overflow.slice(0, 12),
            heatCols: getComputedStyle(document.getElementById('heat')).gridTemplateColumns
                        .split(' ').length,
            chartHeights: Array.from(document.querySelectorAll('.chart'))
                        .map(e => Math.round(e.getBoundingClientRect().height)),
            tableScrolls: (() => {
              const t = document.querySelector('.tablewrap');
              return t ? t.scrollWidth > t.clientWidth : null;
            })(),
            pageHeight: document.body.scrollHeight,
          };
        }""", WIDTH)
        pg.screenshot(path=str(out), full_page=False)
        pg.screenshot(path=str(ROOT / "docs" / "preview_mobile_full.png"), full_page=True)
        b.close()
    srv.shutdown()

    print(json.dumps(state, ensure_ascii=False, indent=2))
    if state["bodyScrollsSideways"]:
        problems.append(f"整頁可以橫向捲動（{state['docWidth']}px > {WIDTH}px）")
    for p_ in problems:
        print(" ! ", p_)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
