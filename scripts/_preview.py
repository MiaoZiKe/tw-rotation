"""本機預覽驗證 v3：起 http server，用真的 ECharts + Lightweight Charts 走過每個分頁與個股頁，
抓 JS 錯誤、偵測文字框重疊、截圖到 docs/。

用法：python scripts/_preview.py [--code 2330]
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
PORT = 8766

OVERLAP_JS = r"""
() => {
  // 找出可見的文字葉節點，兩兩比對外框；忽略祖先/後代與 canvas
  const els = Array.from(document.querySelectorAll('main *')).filter(e => {
    if (!(e instanceof HTMLElement)) return false;
    if (['SCRIPT','STYLE','CANVAS','SVG','INPUT','BUTTON'].includes(e.tagName)) return false;
    const hasText = Array.from(e.childNodes).some(n => n.nodeType === 3 && n.textContent.trim().length > 1);
    if (!hasText) return false;
    const r = e.getBoundingClientRect(); const cs = getComputedStyle(e);
    return r.width > 6 && r.height > 6 && cs.visibility !== 'hidden' && cs.display !== 'none' && r.bottom > 0 && r.top < document.documentElement.scrollHeight;
  });
  // 在可捲動容器裡、已經捲出可視範圍的元素不算重疊（它其實被容器裁掉了）
  const clipped = (e) => {
    for (let p = e.parentElement; p; p = p.parentElement) {
      const cs = getComputedStyle(p);
      if (!/auto|scroll|hidden/.test(cs.overflowY + cs.overflowX)) continue;
      const pr = p.getBoundingClientRect(), er = e.getBoundingClientRect();
      if (er.bottom < pr.top - 1 || er.top > pr.bottom + 1 || er.right < pr.left - 1 || er.left > pr.right + 1) return true;
    }
    return false;
  };
  const rects = els.filter(e => !clipped(e)).map(e => ({ e, r: e.getBoundingClientRect() }));
  const bad = [];
  for (let i = 0; i < rects.length; i++) for (let j = i + 1; j < rects.length; j++) {
    const a = rects[i], b = rects[j];
    if (a.e.contains(b.e) || b.e.contains(a.e)) continue;
    const x = Math.max(0, Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left));
    const y = Math.max(0, Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top));
    const inter = x * y; const small = Math.min(a.r.width * a.r.height, b.r.width * b.r.height);
    if (inter > 0.3 * small && inter > 40) bad.push([a.e.textContent.trim().slice(0, 30), b.e.textContent.trim().slice(0, 30)]);
  }
  return bad.slice(0, 12);
}
"""


def serve():
    handler = partial(SimpleHTTPRequestHandler, directory=str(SITE))
    handler.log_message = lambda *a, **k: None
    SimpleHTTPRequestHandler.log_message = lambda *a, **k: None
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--code", default=None); args = ap.parse_args()
    from playwright.sync_api import sync_playwright
    srv = serve(); time.sleep(0.4)
    out = ROOT / "docs"; out.mkdir(exist_ok=True)
    problems: list[str] = []; state = {}

    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        pg = b.new_page(viewport={"width": 1500, "height": 1000})
        pg.on("pageerror", lambda e: problems.append(f"pageerror: {e}"))
        pg.on("console", lambda m: problems.append(f"console.error: {m.text}") if m.type == "error" and "ERR_FAILED" not in m.text and "fonts.googleapis" not in m.text else None)
        pg.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        base = f"http://127.0.0.1:{PORT}/index.html"

        def visit(hash_, name, wait=1500):
            pg.goto(f"{base}#{hash_}", wait_until="networkidle"); pg.wait_for_timeout(wait)
            info = pg.evaluate("""() => ({ canvases: document.querySelectorAll('main canvas').length, empties: Array.from(document.querySelectorAll('main .view.on .empty')).map(e => e.textContent.trim().slice(0, 40)), text: document.querySelector('main .view.on').innerText.length })""")
            info["overlaps"] = pg.evaluate(OVERLAP_JS)
            state[name] = info
            pg.screenshot(path=str(out / f"v3_{name}.png"), full_page=True)
            return info

        visit("overview", "overview")
        state["overview"]["cands"] = pg.evaluate("document.querySelectorAll('#candBody tr').length")
        state["overview"]["hero"] = pg.evaluate("document.getElementById('hero').innerText.slice(0,80)")
        visit("flow", "flow")
        visit("industry", "industry_map")
        visit("industry/ai_server", "industry_chain")
        state["industry_chain"]["members"] = pg.evaluate("document.querySelectorAll('#memberTable tbody tr').length")
        state["industry_chain"]["diagram"] = pg.evaluate("!!document.querySelector('#prodDiagram svg') && document.querySelectorAll('#chainMap .co').length")
        visit("industry/group/ind_ETF", "industry_etf")
        state["industry_etf"]["members"] = pg.evaluate("document.querySelectorAll('#memberTable tbody tr').length")
        visit("themes", "themes")
        # 每個題材都要有產品圖，而且圖上每個零件都要點得到個股（Andy 2026-09-12 的要求）
        tids = pg.evaluate("(window.ThemeDiagrams ? Object.keys(window.ThemeDiagrams) : [])")
        tstat = {}
        for tid in tids:
            pg.goto(f"{base}#themes/{tid}", wait_until="networkidle"); pg.wait_for_timeout(900)
            tstat[tid] = pg.evaluate("""() => {
              const r = document.querySelector('#themeDiagram svg'); if (!r) return { svg: false };
              const ns = Array.from(r.querySelectorAll('[data-part]'));
              const ids = [...new Set(ns.map(n => n.dataset.part).filter(Boolean))];
              const noCode = ids.filter(id => !ns.some(n => n.dataset.part === id && n.dataset.codes));
              const rows = ns.filter(n => n.classList.contains('lrow')).length;
              return { svg: true, parts: ids.length, rows, noCode, vb: r.getAttribute('viewBox') };
            }""")
            if tstat[tid].get("noCode"):
                problems.append(f"題材 {tid} 有零件點不到個股：{tstat[tid]['noCode']}")
            if not tstat[tid].get("svg"):
                problems.append(f"題材 {tid} 沒有產品圖")
            ov2 = pg.evaluate(OVERLAP_JS)
            if ov2:
                problems.append(f"題材 {tid} 文字重疊：{ov2[:3]}")
        # 點第一個零件，確認會列出個股
        if tids:
            pg.goto(f"{base}#themes/{tids[0]}", wait_until="networkidle"); pg.wait_for_timeout(900)
            pg.evaluate("document.querySelector('#themeDiagram [data-part][data-codes]').dispatchEvent(new MouseEvent('click', {bubbles:true}))")
            pg.wait_for_timeout(300)
            tstat["_click"] = pg.evaluate("({ links: document.querySelectorAll('#themeParts a.lk').length, sel: document.querySelectorAll('#themeDiagram .p3.sel').length })")
            if not tstat["_click"]["links"]:
                problems.append("點題材產品圖的零件沒有列出個股")
            pg.screenshot(path=str(out / "v3_theme_diagram.png"), full_page=True)
        state["theme_diagrams"] = tstat
        visit("season", "season")

        code = args.code or pg.evaluate("(document.querySelector('#candBody tr')||{}).dataset ? document.querySelector('#candBody tr').dataset.code : '2330'") or "2330"
        pg.goto(f"{base}#stock/{code}", wait_until="networkidle"); pg.wait_for_timeout(2200)
        st = pg.evaluate("""() => ({ title: (document.querySelector('#stockPage h2')||{}).innerText, lwc: !!document.querySelector('#lwc canvas'), lwcCanvases: document.querySelectorAll('#lwc canvas').length,
            chips: document.querySelectorAll('#indChips .chip').length, legend: (document.getElementById('legendOv')||{}).innerText, mtf: (document.getElementById('mtfCard')||{}).innerText.slice(0,120), chainCos: document.querySelectorAll('#chainMap .co').length, sel: document.querySelectorAll('#chainMap .co.sel').length })""")
        st["overlaps"] = pg.evaluate(OVERLAP_JS); state["stock"] = st
        pg.screenshot(path=str(out / "v3_stock.png"), full_page=True)
        # 切分頁與週期
        for tab in ("revenue", "profit", "dividend", "chips", "basics", "news"):
            pg.evaluate(f"document.querySelector('#stockTabs button[data-t=\"{tab}\"]').click()"); pg.wait_for_timeout(500)
            state["tab_" + tab] = pg.evaluate("({ canvases: document.querySelectorAll('#stockTab canvas').length, text: document.getElementById('stockTab').innerText.length, empties: Array.from(document.querySelectorAll('#stockTab .empty')).map(e => e.textContent.trim().slice(0,30)) })")
            pg.screenshot(path=str(out / f"v3_tab_{tab}.png"), full_page=False)
        for tf in ("1w", "1M", "60m"):
            pg.evaluate(f"document.querySelector('#tfSeg button[data-tf=\"{tf}\"]').click()"); pg.wait_for_timeout(500)
            state["tf_" + tf] = pg.evaluate("({ canvases: document.querySelectorAll('#lwc canvas').length, empty: !!document.querySelector('#chartHost .empty'), legend: (document.getElementById('legendOv')||{}).innerText })")
        pg.evaluate("document.querySelector('#tfSeg button[data-tf=\"1d\"]').click()"); pg.wait_for_timeout(300)
        pg.evaluate("document.getElementById('mtfBtn').click()"); pg.wait_for_timeout(1200)
        state["mtf_grid"] = pg.evaluate("({ cells: document.querySelectorAll('.mtf-cell').length, canvases: document.querySelectorAll('#mtfGrid canvas').length })")
        pg.screenshot(path=str(out / "v3_mtf.png"), full_page=False)
        # 指標參數
        pg.evaluate("document.getElementById('mtfBtn').click()"); pg.wait_for_timeout(600)
        pg.evaluate("document.querySelector('#indChips .chip[data-k=rsi]').click()"); pg.wait_for_timeout(400)
        state["rsi_on"] = pg.evaluate("({ chipOn: document.querySelector('#indChips .chip[data-k=rsi]').classList.contains('on'), legend: (document.getElementById('legendOv')||{}).innerText.includes('RSI') })")

        # 手機
        m = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        m.on("pageerror", lambda e: problems.append(f"mobile pageerror: {e}"))
        m.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        m.goto(f"{base}#overview", wait_until="networkidle"); m.wait_for_timeout(1200)
        state["mobile"] = m.evaluate("({ sideways: document.documentElement.scrollWidth > 391, cards: document.querySelectorAll('#candCards .scard').length })")
        m.screenshot(path=str(out / "v3_mobile.png"), full_page=False)
        m.goto(f"{base}#stock/{code}", wait_until="networkidle"); m.wait_for_timeout(1800)
        state["mobile_stock"] = m.evaluate("({ sideways: document.documentElement.scrollWidth > 391, lwc: !!document.querySelector('#lwc canvas') })")
        m.screenshot(path=str(out / "v3_mobile_stock.png"), full_page=False)
        b.close()
    srv.shutdown()

    print(json.dumps(state, ensure_ascii=False, indent=1))
    ov = {k: v["overlaps"] for k, v in state.items() if isinstance(v, dict) and v.get("overlaps")}
    if ov:
        print("\n=== 文字重疊 ===")
        for k, v in ov.items():
            print(" ", k, v)
    if problems:
        print("\n=== 問題 ===")
        for x in problems:
            print(" -", x)
        return 1
    print("\n所有分頁與個股頁正常，截圖在 docs/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
