"""本機預覽驗證：起一個 http server，用 stub 版 ECharts 載入頁面，
檢查有沒有 JS 例外、資料有沒有正確渲染，並截圖。

之所以用 stub：這個開發環境的 egress 政策擋掉了 cdnjs，拿不到真的 ECharts。
但 stub 仍然會忠實執行我們自己寫的每一段圖表設定程式碼 —— 真正容易寫錯的
是那些 formatter 與資料對應，而不是 ECharts 本身。
"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
PORT = 8765

STUB = """
window.__calls = []; window.__errs = [];
window.echarts = {
  init: function(el){
    return {
      setOption: function(o){
        // 真的把每個 formatter 跑一遍，這是最容易寫錯的地方
        try {
          (o.series || []).forEach(function(s){
            (s.data || []).slice(0, 5).forEach(function(d, i){
              if (o.tooltip && typeof o.tooltip.formatter === 'function') {
                var v = (d && d.value !== undefined) ? d.value : d;
                o.tooltip.formatter({name: (d && d.name) || 'x', value: v,
                                     data: d, dataIndex: i, seriesName: s.name});
              }
              if (s.label && typeof s.label.formatter === 'function') {
                s.label.formatter({value: (d && d.value !== undefined) ? d.value : d,
                                   data: d, dataIndex: i});
              }
            });
          });
        } catch (e) { window.__errs.push('formatter: ' + e.message); }
        window.__calls.push({id: el.id, series: (o.series || []).length});
        el.setAttribute('data-charted', '1');
      },
      resize: function(){}, on: function(){}
    };
  }
};
"""


def serve():
    handler = partial(SimpleHTTPRequestHandler, directory=str(SITE))
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main() -> int:
    from playwright.sync_api import sync_playwright

    srv = serve()
    time.sleep(0.5)
    out = ROOT / "docs" / "preview.png"
    out.parent.mkdir(exist_ok=True)

    problems: list[str] = []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        pg = b.new_page(viewport={"width": 1440, "height": 2400})
        pg.on("pageerror", lambda e: problems.append(f"pageerror: {e}"))
        pg.on("console", lambda m: problems.append(f"console.{m.type}: {m.text}")
              if m.type == "error" else None)
        # 攔掉 cdnjs 的 ECharts，換成 stub
        pg.route("**/echarts*.js", lambda route: route.fulfill(
            status=200, content_type="application/javascript", body=STUB))
        pg.route("**/fonts.googleapis.com/**", lambda route: route.abort())

        pg.goto(f"http://127.0.0.1:{PORT}/index.html", wait_until="networkidle")
        pg.wait_for_timeout(1200)

        state = pg.evaluate("""() => ({
          errs: window.__errs || [],
          charted: document.querySelectorAll('[data-charted]').length,
          heatTiles: document.querySelectorAll('#heat > div').length,
          candRows: document.querySelectorAll('#candBody tr').length,
          newsItems: document.querySelectorAll('.newsitem').length,
          banner: document.getElementById('banner').className,
          bannerText: document.getElementById('banner').textContent.slice(0, 120),
          dataDate: document.getElementById('dataDate').textContent,
          firstRow: Array.from(document.querySelectorAll('#candBody tr:first-child td'))
                         .map(td => td.textContent.trim()),
        })""")
        pg.screenshot(path=str(out), full_page=True)
        b.close()
    srv.shutdown()

    print(json.dumps(state, ensure_ascii=False, indent=2))
    if state["errs"]:
        problems.extend(state["errs"])
    if problems:
        print("\n=== 問題 ===")
        for p_ in problems:
            print(" -", p_)
        return 1
    print(f"\n頁面正常，截圖：{out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
