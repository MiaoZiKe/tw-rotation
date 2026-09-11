"""本機預覽驗證 v2：起 http server、stub ECharts、走過每個分頁與個股頁，抓 JS 錯誤並截圖。

用 stub 的原因：開發環境的 egress 擋掉 cdnjs。stub 仍會執行我們自己寫的
每一個 formatter / label / click handler —— 真正容易寫錯的就是那些。
"""
from __future__ import annotations

import json
import sys
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
PORT = 8765

STUB = r"""
window.__calls = []; window.__errs = []; window.__handlers = {};
function runFormatters(o, id){
  try {
    const ser = o.series || [];
    ser.forEach(function(s){
      const data = s.data || [];
      data.slice(0, 6).forEach(function(d, i){
        const v = (d && d.value !== undefined) ? d.value : d;
        const p = {name: (d && d.name) || 'x', value: v, data: d, dataIndex: i, seriesName: s.name, seriesType: s.type, dataType: 'node'};
        if (o.tooltip && typeof o.tooltip.formatter === 'function') {
          // K 線 tooltip 是 axis trigger，會收到陣列
          o.tooltip.formatter(o.tooltip.trigger === 'axis' ? [p] : p);
        }
        if (s.label && typeof s.label.formatter === 'function') s.label.formatter(p);
        if (typeof s.symbolSize === 'function') s.symbolSize(Array.isArray(v) ? v : [v]);
        if (s.itemStyle && typeof s.itemStyle.color === 'function') s.itemStyle.color(p);
      });
      if (s.links) s.links.slice(0,3).forEach(function(l){ if (o.tooltip && typeof o.tooltip.formatter==='function') o.tooltip.formatter({dataType:'edge', data:l}); });
      if (s.markPoint && s.markPoint.tooltip && typeof s.markPoint.tooltip.formatter==='function' && s.markPoint.data && s.markPoint.data[0]) s.markPoint.tooltip.formatter({data: s.markPoint.data[0]});
    });
    (o.yAxis ? [].concat(o.yAxis) : []).forEach(function(a){ if (a.axisLabel && typeof a.axisLabel.formatter==='function') a.axisLabel.formatter(3); });
  } catch (e) { window.__errs.push(id + ' formatter: ' + e.message); }
}
window.echarts = {
  init: function(el){
    const h = {};
    return {
      setOption: function(o){ runFormatters(o, el.id); window.__calls.push({id: el.id, series: (o.series||[]).length}); el.setAttribute('data-charted','1'); },
      resize: function(){}, on: function(ev, fn){ h[ev]=fn; window.__handlers[el.id]=h; }, off: function(){},
      dispose: function(){}
    };
  }
};
"""


def serve():
    handler = partial(SimpleHTTPRequestHandler, directory=str(SITE))
    handler.log_message = lambda *a, **k: None
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main() -> int:
    from playwright.sync_api import sync_playwright
    srv = serve(); time.sleep(0.4)
    out = ROOT / "docs"; out.mkdir(exist_ok=True)
    problems: list[str] = []

    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        pg = b.new_page(viewport={"width": 1440, "height": 1000})
        pg.on("pageerror", lambda e: problems.append(f"pageerror: {e}"))
        pg.on("console", lambda m: problems.append(f"console.error: {m.text}") if m.type == "error" and "ERR_FAILED" not in m.text else None)
        pg.route("**/echarts*.js", lambda r: r.fulfill(status=200, content_type="application/javascript", body=STUB))
        pg.route("**/fonts.googleapis.com/**", lambda r: r.abort())

        pg.goto(f"http://127.0.0.1:{PORT}/index.html#overview", wait_until="networkidle")
        pg.wait_for_timeout(900)
        state = {}
        state["overview"] = pg.evaluate("""() => ({
          heat: document.querySelectorAll('#heat > div').length,
          charted: document.querySelectorAll('[data-charted]').length,
          cands: document.querySelectorAll('#candBody tr').length,
          firstRow: Array.from(document.querySelectorAll('#candBody tr:first-child td')).map(t => t.textContent.trim()).slice(0,5),
          evCount: document.getElementById('evCount').textContent,
          evItems: document.querySelectorAll('.ev').length,
          banner: document.getElementById('banner').textContent.slice(0,60),
        })""")
        pg.screenshot(path=str(out / "v2_overview.png"), full_page=True)

        # 熱力圖點擊 → 下鑽（直接呼叫 handler）
        pg.evaluate("""() => { const h = window.__handlers['treemap']; if (h && h.click) h.click({data: {gid: 'foundry', name: '晶圓代工'}}); }""")
        pg.wait_for_timeout(300)
        state["drill"] = pg.evaluate("""() => ({on: document.getElementById('drill').classList.contains('on'), rows: document.querySelectorAll('#drill tbody tr').length,
          title: (document.querySelector('#drill h3')||{}).textContent})""")
        # 切上櫃篩選
        pg.evaluate("""() => { const b = document.querySelector('#drill .seg[data-f=market] button[data-v=TPEX]'); if (b) b.click(); }""")
        pg.wait_for_timeout(200)
        state["drill_tpex_rows"] = pg.evaluate("document.querySelectorAll('#drill tbody tr').length")
        pg.screenshot(path=str(out / "v2_drill.png"), full_page=False)

        for view in ("flow", "chain", "season"):
            pg.goto(f"http://127.0.0.1:{PORT}/index.html#{view}", wait_until="networkidle"); pg.wait_for_timeout(700)
            state[view] = pg.evaluate("""(v) => ({
              visible: document.getElementById('v-'+v).classList.contains('on'),
              charted: Array.from(document.querySelectorAll('#v-'+v+' [data-charted]')).map(e => e.id),
              text: document.getElementById('v-'+v).innerText.length })""", view)
            pg.screenshot(path=str(out / f"v2_{view}.png"), full_page=True)

        # 個股頁
        code = pg.evaluate("(document.querySelector('#candBody tr')||{}).dataset ? document.querySelector('#candBody tr').dataset.code : null") or "2330"
        pg.goto(f"http://127.0.0.1:{PORT}/index.html#stock/{code}", wait_until="networkidle"); pg.wait_for_timeout(900)
        state["stock"] = pg.evaluate("""() => ({
          title: (document.querySelector('#stockPage h2')||{}).textContent,
          verdict: (document.querySelector('#stockPage .verdict h3')||{}).textContent,
          reasons: document.querySelectorAll('#stockPage .verdict li').length,
          kline: !!document.querySelector('#kline[data-charted]'),
          inst: !!document.querySelector('#instChart[data-charted]') || document.querySelector('#instChart .empty') !== null,
          kv: document.querySelectorAll('#stockPage .kv dt').length,
          lights: document.querySelectorAll('#stockPage .light').length })""")
        pg.screenshot(path=str(out / "v2_stock.png"), full_page=True)

        # 手機
        m = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        m.on("pageerror", lambda e: problems.append(f"mobile pageerror: {e}"))
        m.route("**/echarts*.js", lambda r: r.fulfill(status=200, content_type="application/javascript", body=STUB))
        m.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        m.goto(f"http://127.0.0.1:{PORT}/index.html#overview", wait_until="networkidle"); m.wait_for_timeout(800)
        state["mobile"] = m.evaluate("""() => ({
          sideways: document.documentElement.scrollWidth > 391,
          cards: document.querySelectorAll('#candCards .card').length,
          tableHidden: getComputedStyle(document.querySelector('#v-overview .tw')).display === 'none',
          asideOff: getComputedStyle(document.getElementById('side')).transform !== 'none' })""")
        m.screenshot(path=str(out / "v2_mobile.png"), full_page=False)
        m.evaluate("document.getElementById('evToggle').click()"); m.wait_for_timeout(300)
        m.screenshot(path=str(out / "v2_mobile_events.png"), full_page=False)
        m.goto(f"http://127.0.0.1:{PORT}/index.html#chain", wait_until="networkidle"); m.wait_for_timeout(500)
        state["mobile_chain"] = m.evaluate("""() => ({listShown: getComputedStyle(document.getElementById('chainList')).display !== 'none', segs: document.querySelectorAll('#chainList details').length})""")
        state["js_errs"] = pg.evaluate("window.__errs") + m.evaluate("window.__errs")
        b.close()
    srv.shutdown()

    print(json.dumps(state, ensure_ascii=False, indent=1))
    problems += state.get("js_errs", [])
    if problems:
        print("\n=== 問題 ===")
        for x in problems:
            print(" -", x)
        return 1
    print("\n所有分頁與個股頁正常，截圖在 docs/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
