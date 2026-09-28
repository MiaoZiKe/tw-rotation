"""設計 v4 第二批 2B：產業頁／個股頁的量測（整頁＋逐張圖），改前改後用同一支。

整頁指標跟 measure.py 同一套量法（直接 import 它的 JS 與面積、空白帶函式）：
  plot1   第一屏繪圖區 ÷ 可視面積（%）
  plotP   整頁繪圖區 ÷ 整頁面積（%）
  docH    頁高
  blank   空白帶（整列沒東西、連續 ≥24px）÷ 頁高（%）
  head    卡片頂 → 卡片裡第一張圖（中位數 px）
  gapV    卡片之間垂直間距（中位數 px）

個股頁的分頁（營收、獲利、除權息、法人、資券、大戶／散戶）在 K 線卡**下面**，第一屏看不到；
所以另外量「分頁區」（#stockTab）：
  tabTop  分頁區頂端在頁面的 y（K 線卡＋分頁列的總高）
  tabPlot 分頁區裡繪圖區 ÷ 分頁區面積（%）
  tabHead 分頁區裡第一張卡的頂 → 第一張圖的繪圖區頂（標題列＋篩選列＋圖例的總負擔 px）

逐張圖（ECharts）：
  gridTop   繪圖區頂端離圖表容器頂幾 px（圖例畫在容器裡就會把它撐大）
  legendIn  ECharts 圖例是不是畫在容器裡（true＝還在圖裡；改後應該是 false，圖例改成容器外的 HTML）
  legendHit 圖例外框跟繪圖區有沒有重疊（壓到資料）
  axisMin   軸字最小字級（getOption 讀 axisLabel.fontSize；沒寫＝ECharts 預設 12）
  vGrid     直向格線還開著的軸數（x 是類別／時間軸、y 是數值軸時，x 軸的 splitLine）
  plotPct   繪圖區 ÷ 容器面積（%）
Lightweight Charts（K 線）：
  lwcFont   軸字字級（chart.options().layout.fontSize）
  paneLbl   副圖標籤（.pane-labels div）字級、跟該副圖繪圖區頂端的重疊高度 px（>0＝標籤壓在資料區上）

用法（一律包 flock）：
    flock /tmp/claude-0/browser.lock python3 docs/design_v4/tools/stock_measure.py --site site --out x.json \
        [--widths 1440,1100,800,390] [--theme4 hud] [--mode dark] [--views stock,industry] [--shots 資料夾]
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import threading
import time
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import measure as M  # noqa: E402

# (名稱, 路由, 要點的分頁鈕)
VIEWS = [
    ("stock-overview", "stock/2330", "overview"),
    ("stock-revenue", "stock/2330", "revenue"),
    ("stock-profit", "stock/2330", "profit"),
    ("stock-dividend", "stock/2330", "dividend"),
    ("stock-inst", "stock/2330", "inst"),
    ("stock-margin", "stock/2330", "margin"),
    ("stock-holders", "stock/2330", "holders"),
    ("industry", "industry", None),
    ("chain-semi", "industry/semiconductor", None),
    ("chain-elec", "industry/electronics", None),
]

JS2 = r"""
() => {
  const sy = scrollY;
  const R = (el) => { if (!el) return null; const r = el.getBoundingClientRect();
    return { x: Math.round(r.left), y: Math.round(r.top + sy), w: Math.round(r.width), h: Math.round(r.height) }; };
  const vis = el => { if (!el) return false; const s = getComputedStyle(el); if (s.display==='none'||s.visibility==='hidden') return false;
    const r = el.getBoundingClientRect(); return r.width>4 && r.height>4; };
  const inView = el => { let p = el; while (p && p!==document.body) { const s = getComputedStyle(p);
      if (s.display==='none' || s.visibility==='hidden') return false; p = p.parentElement; } return true; };
  const out = { charts: {}, lwc: null };
  const view = document.querySelector('.view.on') || document.querySelector('main');
  for (const el of [...view.querySelectorAll('[_echarts_instance_]')]) {
    if (!vis(el) || !inView(el)) continue;
    const c = echarts.getInstanceByDom(el); if (!c) continue;
    const id = el.id || (el.parentElement && el.parentElement.id) || '?';
    const o = c.getOption(), m = c.getModel();
    const W = el.clientWidth, H = el.clientHeight;
    const grids = [];
    try { m.eachComponent('grid', g => { const r = g.coordinateSystem && g.coordinateSystem.getRect(); if (r) grids.push(r); }); } catch (e) {}
    let gridTop = grids.length ? Math.round(Math.min(...grids.map(g => g.y))) : null;
    const plotA = grids.reduce((s, g) => s + g.width * g.height, 0);
    let legendIn = false, legendHit = false, legendBox = null;
    try { m.eachComponent('legend', lm => { if (lm.get('show') === false) return; const d = lm.getData ? lm.getData() : [];
        if (!d || !d.length) return; const v = c.getViewOfComponentModel(lm); if (!v || !v.group) return;
        const b = v.group.getBoundingRect(); const t = v.group.transform || [1,0,0,1,0,0];
        const bx = b.x + t[4], by = b.y + t[5];
        if (b.width < 2) return; legendIn = true; legendBox = { x: Math.round(bx), y: Math.round(by), w: Math.round(b.width), h: Math.round(b.height) };
        for (const g of grids) if (bx < g.x + g.width && bx + b.width > g.x && by < g.y + g.height && by + b.height > g.y) legendHit = true; }); } catch (e) {}
    const fs = []; let vGrid = 0;
    for (const k of ['xAxis', 'yAxis']) for (const a of (o[k] || [])) {
      if (!a || a.show === false) continue; const al = a.axisLabel || {}; if (al.show !== false) fs.push(al.fontSize == null ? 12 : al.fontSize); }
    try { m.eachComponent('xAxis', ax => { const sl = ax.get('splitLine'); const t = ax.get('type');
        if (ax.get('show') !== false && sl && sl.show && (t === 'category' || t === 'time')) vGrid++; }); } catch (e) {}
    out.charts[id] = { w: W, h: H, gridTop, plotPct: W*H ? +(plotA / (W*H) * 100).toFixed(1) : null,
      legendIn, legendHit, legendBox, axisMin: fs.length ? Math.min(...fs) : null, vGrid };
  }
  const k = window.KChart && KChart.last;
  const lw = document.querySelector('#lwc');
  if (k && lw && vis(lw)) {
    let font = null; try { font = k.chart.options().layout.fontSize; } catch (e) {}
    let vert = null; try { vert = k.chart.options().grid.vertLines.visible; } catch (e) {}
    const panes = []; try { let top = 0; for (const p of k.chart.panes()) { let mt = null;
        try { const s = (p.getSeries ? p.getSeries() : [])[0]; mt = s.priceScale().options().scaleMargins.top; } catch (e) {}
        panes.push({ top, h: p.getHeight(), dataTop: mt == null ? null : Math.round(mt * p.getHeight()) }); top += p.getHeight() + 1; } } catch (e) {}
    const lr = lw.getBoundingClientRect();
    const lbls = [...lw.querySelectorAll('.pane-labels div')].filter(vis).map(d => { const b = d.getBoundingClientRect();
      return { t: d.textContent.trim().slice(0, 16), fs: parseFloat(getComputedStyle(d).fontSize), y: Math.round(b.top - lr.top), h: Math.round(b.height) }; });
    out.lwc = { font, vertLines: vert, panes, labels: lbls, h: Math.round(lr.height) };
  }
  const tab = document.getElementById('stockTab');
  if (tab && vis(tab)) {
    out.tab = R(tab);
    const tabs = document.getElementById('stockTabs'); out.tabs = R(tabs);
    const card = tab.querySelector('.card');
    out.tabCard = R(card);
  }
  const chart = document.getElementById('skChartCard'); out.skChartCard = R(chart);
  return out;
}
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--shots", default="")
    ap.add_argument("--views", default="")
    ap.add_argument("--widths", default="1440,1100,800,390")
    ap.add_argument("--theme4", default="hud")
    ap.add_argument("--mode", default="dark")
    ap.add_argument("--port", type=int, default=8793)
    ap.add_argument("--wait", type=int, default=3200)
    args = ap.parse_args()

    from PIL import Image
    from playwright.sync_api import sync_playwright

    site = Path(args.site).resolve()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), partial(M._Q, directory=str(site)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{args.port}/index.html"
    shots = Path(args.shots) if args.shots else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    want = [v for v in args.views.split(",") if v]
    views = [v for v in VIEWS if not want or any(v[0].startswith(w) for w in want)]
    res = []
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
            for w in [int(x) for x in args.widths.split(",")]:
                h = 844 if w <= 480 else 900
                for name, route, tab in views:
                    ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=1,
                                        is_mobile=w <= 480, has_touch=w <= 480)
                    ctx.add_init_script(M.CONSENT)
                    ls = {"tw.theme": args.mode, "tw.theme4": args.theme4}
                    for k, v in ls.items():
                        ctx.add_init_script(f"try{{localStorage.setItem({k!r},{v!r});}}catch(e){{}}")
                    pg = ctx.new_page()
                    t0 = time.time()
                    pg.goto(f"{base}#{route}", wait_until="networkidle")
                    pg.wait_for_timeout(args.wait)
                    if tab:
                        # 手機（≤640）個股頁是券商式分段（#mbTabs），分頁鈕不一定看得到 —— 用 JS 點
                        ok = pg.evaluate("""(t) => { const b = document.querySelector('#stockTabs button[data-t="'+t+'"]');
                            if (!b) return false; b.click(); return true; }""", tab)
                        pg.wait_for_timeout(1600)
                        if not ok:
                            ctx.close()
                            continue
                        pg.evaluate("window.scrollTo(0,0)")
                        pg.wait_for_timeout(300)
                    m = pg.evaluate(M.JS)
                    d = pg.evaluate(JS2)
                    vw, vh = m["vw"], m["vh"]
                    plot1 = M.area_union(m["rects"], (0, 0, vw, vh)) / (vw * vh) * 100
                    plotP = M.area_union(m["rects"]) / (vw * m["docH"]) * 100
                    png = pg.screenshot(full_page=True)
                    img = Image.open(io.BytesIO(png))
                    band, empty, worst = M.blank_metrics(img, m["mainX"], m["mainX"] + m["mainW"],
                                                         max(m["topH"], m["viewTop"]), min(img.height, m["viewBot"]))
                    row = {"view": name, "route": route, "tab": tab, "w": w, "h": h,
                           "plot1": round(plot1, 1), "plotP": round(plotP, 1), "docH": m["docH"],
                           "gapV": M.med(m["gapsV"]), "gapH": M.med(m["gapsH"]), "head": M.med(m["heads"]),
                           "blank": round(band, 1), "empty": round(empty, 1), "worst": worst,
                           "charts": d["charts"], "lwc": d["lwc"]}
                    t = d.get("tab")
                    if t:
                        tr = (t["x"], t["y"], t["x"] + t["w"], t["y"] + t["h"])
                        row["tabTop"] = t["y"]
                        row["tabPlot"] = round(M.area_union(m["rects"], tr) / max(1, t["w"] * t["h"]) * 100, 1)
                        c = d.get("tabCard")
                        if c:
                            inc = [r for r in m["rects"] if r["x"] >= c["x"] - 2 and r["x"] + r["w"] <= c["x"] + c["w"] + 2
                                   and r["y"] >= c["y"] - 2 and r["y"] < c["y"] + c["h"]]
                            row["tabHead"] = round(min(r["y"] for r in inc) - c["y"]) if inc else None
                            row["tabCardH"] = c["h"]
                    row["secs"] = round(time.time() - t0, 1)
                    res.append(row)
                    print(json.dumps({k: row.get(k) for k in ("view", "w", "plot1", "plotP", "docH", "blank", "head",
                                                              "tabTop", "tabPlot", "tabHead")}, ensure_ascii=False), flush=True)
                    if shots:
                        img.convert("RGB").save(shots / f"{name}-{w}.jpg", quality=70)
                    ctx.close()
            b.close()
    finally:
        srv.shutdown()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
