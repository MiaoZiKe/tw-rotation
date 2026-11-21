"""設計 v4 第二批 2A：資金流向頁的**逐元件**量測（補 measure.py 量不到的地方）。

measure.py 量的是整頁（第一屏繪圖區 %、空白帶、頁高），改前改後都用它；這支只量資金流向頁四張卡的細節：
  rot     資金輪動卡：卡高、輪盤容器寬高、盤半徑 R、盤直徑佔容器寬 %、排行圖容器寬高與繪圖區（grid）寬高、兩欄或單欄
  sankey  資金去向：畫布寬高、**右側空帶寬**（FlowTopo.probe 讀每個節點標籤的實際位置）：
            bandIdle＝畫布右緣 − 根／產業鏈／族群標籤最右緣（沒滑過時右邊整條空多寬）
            bandLeaf＝畫布右緣 − 代表股標籤最右緣（滑過顯示代表股時，右邊還剩多寬用不到）
  legend  族群 × 法人、資金集中度：ECharts 圖例是不是畫在圖表容器裡（inBox）、繪圖區頂端離容器頂幾 px（gridTop）
  axis    四張 ECharts 圖的軸字最小字級（getOption 讀 axisLabel.fontSize，沒寫＝ECharts 預設 12）
  docH    頁高

資金去向（拓撲光纖版）是原生 canvas，measure.py 的「繪圖區」只認 ECharts／Lightweight Charts／SVG，**不算它** ——
所以它的空帶只能用這支量（measure.py 的 worst 也會框到它，但那是最大空矩形，不是空帶寬）。

用法（一律包 flock）：
    flock /tmp/claude-0/browser.lock python3 docs/design_v4/tools/flow_measure.py --site site --out x.json \
        [--widths 1440,1280,1100,1000,901,800] [--theme4 hud] [--mode dark]
"""
from __future__ import annotations

import argparse
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CONSENT = ("try{if(!localStorage.getItem('tw.consent'))localStorage.setItem('tw.consent',"
           "JSON.stringify({v:'*',at:'test'}));"
           "if(!localStorage.getItem('tw.tour'))localStorage.setItem('tw.tour','*');}catch(e){}")

JS = r"""
() => {
  const R = (el) => { if (!el) return null; const r = el.getBoundingClientRect();
    return { x: Math.round(r.left), y: Math.round(r.top + scrollY), w: Math.round(r.width), h: Math.round(r.height) }; };
  const out = { docH: Math.max(document.documentElement.scrollHeight, document.body.scrollHeight) };
  const card = document.getElementById('flowRotCard');
  out.rotCard = R(card);
  const clk = document.getElementById('rotClock');
  out.clock = R(clk);
  try { const c = echarts.getInstanceByDom(clk); const cs = c.getModel().getComponent('polar').coordinateSystem;
    out.R = Math.round(cs.getRadiusAxis().getExtent()[1]); out.discPct = +(2 * out.R / clk.clientWidth * 100).toFixed(1); } catch (e) {}
  const rf = document.getElementById('rankFlow');
  out.rank = R(rf);
  try { const c = echarts.getInstanceByDom(rf); const g = c.getModel().getComponent('grid').coordinateSystem.getRect();
    out.rankGrid = { w: Math.round(g.width), h: Math.round(g.height) }; } catch (e) {}
  const l = document.querySelector('#flowRotCard .rotleft'), r = document.querySelector('#flowRotCard .rotright');
  out.twoCol = !!(l && r && Math.abs(l.getBoundingClientRect().top - r.getBoundingClientRect().top) < 40
    && r.getBoundingClientRect().left > l.getBoundingClientRect().left + 40);
  out.clockTop = clk ? Math.round(clk.getBoundingClientRect().top - card.getBoundingClientRect().top) : null;
  out.sankey = R(document.getElementById('sankey'));
  try { const t = window.FlowTopo && FlowTopo.probe(document.getElementById('sankey'));
    const v = t.nodes.filter(n => n.lv < 3 && n.lab), l3 = t.nodes.filter(n => n.lv === 3 && n.lab);
    out.sankeyBand = { W: Math.round(t.W), idle: Math.round(t.W - Math.max(...v.map(n => n.lab.x + n.lab.w))),
      leaf: l3.length ? Math.round(t.W - Math.max(...l3.map(n => n.lab.x + n.lab.w))) : null,
      barH: Math.round(t.total - t.H) }; } catch (e) { out.sankeyBand = null; }
  out.sankeyCard = R(document.getElementById('flowSankeyCard'));
  const leg = {};
  for (const id of ['instGroups', 'conc', 'rankFlow', 'rotClock']) {
    const el = document.getElementById(id); const c = el && echarts.getInstanceByDom(el); if (!c) continue;
    const o = c.getOption(); const m = c.getModel();
    let gridTop = null;
    try { gridTop = Math.round(m.getComponent('grid').coordinateSystem.getRect().y); } catch (e) {}
    const lg = (o.legend || [])[0];
    let inBox = false;
    try { const lm = m.getComponent('legend'); inBox = !!(lm && lm.get('show') !== false && (lg.data || []).length); } catch (e) {}
    const fs = [];
    for (const k of ['xAxis', 'yAxis', 'angleAxis', 'radiusAxis']) for (const a of (o[k] || [])) {
      if (!a || a.show === false) continue; const al = a.axisLabel || {}; if (al.show === false) continue;
      fs.push(al.fontSize == null ? 12 : al.fontSize); }
    leg[id] = { gridTop, legendInChart: inBox, axisMinFs: fs.length ? Math.min(...fs) : null };
  }
  out.charts = leg;
  // 族群 × 法人的 HTML 圖例（改後）：在不在繪圖區外
  const hl = document.getElementById('instLegend');
  out.instHtmlLegend = hl ? R(hl) : null;
  return out;
}
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--widths", default="1440,1280,1100,1000,901,800")
    ap.add_argument("--theme4", default="hud")
    ap.add_argument("--mode", default="dark")
    ap.add_argument("--port", type=int, default=8794)
    ap.add_argument("--wait", type=int, default=3500)
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    site = Path(args.site).resolve()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), partial(_Q, directory=str(site)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{args.port}/index.html"
    res = []
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
            for w in [int(x) for x in args.widths.split(",")]:
                ctx = b.new_context(viewport={"width": w, "height": 900}, device_scale_factor=1)
                ctx.add_init_script(CONSENT)
                # 動態關掉：粒子不會剛好飛過右側空帶、讓截圖量出來的空帶忽大忽小
                ls = {"tw.theme": args.mode, "tw.theme4": args.theme4, "tw.flowtopo.motion": "0"}
                for k, v in ls.items():
                    ctx.add_init_script(f"try{{localStorage.setItem({k!r},{v!r});}}catch(e){{}}")
                pg = ctx.new_page()
                pg.goto(f"{base}#flow", wait_until="networkidle")
                pg.wait_for_timeout(args.wait)
                # 資金去向的畫布在首屏下方時是「捲進畫面或閒下來才畫」：先捲過去讓它畫完，再捲回頂端量
                pg.evaluate("() => { const e = document.getElementById('sankey'); if (e) e.scrollIntoView(); }")
                pg.wait_for_timeout(900)
                pg.evaluate("() => window.scrollTo(0, 0)")
                pg.wait_for_timeout(300)
                m = pg.evaluate(JS)
                m["w"] = w
                res.append(m)
                print(json.dumps({k: m.get(k) for k in ("w", "docH", "twoCol", "R", "discPct", "clock", "clockTop", "rank", "rankGrid",
                                                         "sankeyBand")}, ensure_ascii=False), flush=True)
                ctx.close()
            b.close()
    finally:
        srv.shutdown()
    Path(args.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


class _Q(SimpleHTTPRequestHandler):
    def log_message(self, *a):  # noqa: D102
        pass


if __name__ == "__main__":
    raise SystemExit(main())
