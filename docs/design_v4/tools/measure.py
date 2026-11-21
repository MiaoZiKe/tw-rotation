"""設計 v4 的版面量測工具：改前、改後用**同一支、同一套量法**。

為什麼有這支（Andy 2026-09-27）
--------------------------------
> 「我發現目前最大的痛點是無法充分利用版面空間，有些間隔太大導致圖被壓縮」

「變寬敞了」不是數字。這支把每一頁在 1440／1100／800／390 的空間用法量成數字：

  plot1   第一屏：圖表**繪圖區**面積 ÷ 可視面積（%）
          繪圖區＝ECharts 直角座標的 grid 矩形（不含軸字、圖例）、極座標取外接正方形、
          桑基／樹圖取 series 版面框；Lightweight Charts 取主圖窗格的 canvas（不含價格軸與時間軸）；
          大張 SVG 剖析圖取整張。只算可見的部分（跟視窗求交集）。
  plotP   整頁：繪圖區總面積 ÷ 整頁面積（寬 × 捲動高度）（%）
  mainW   內容區實際寬度（扣掉右側「今日事件」欄之後）
  gapH/gapV  卡片之間的水平／垂直間距（中位數，px）
  pad     卡片內距（computed style，眾數）
  head    卡片頂 → 卡片裡第一張圖頂端（標題列＋篩選列的總負擔，中位數 px）
  blank   空白帶：內容區裡「整列都沒有東西」且連續 ≥ 24px 的橫帶，總高 ÷ 整頁高（%）
  empty   空白格：內容區切成 16×16 方格，格內像素全部一樣（沒畫任何東西）的比例（%）
  worst   最大的一塊全空矩形（方格單位換回 px）—— 用來挑「這一頁最浪費的地方」截圖

用法（容器同時只能開一支瀏覽器，一律包 flock）：
    flock /tmp/claude-0/browser.lock python docs/design_v4/tools/measure.py \
        --site <網站資料夾> --out <結果.json> [--shots <截圖資料夾>] [--theme4 hud] [--mode dark]
"""
from __future__ import annotations

import argparse
import io
import json
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PAGES = [
    ("overview", "總覽"),
    ("flow", "資金流向"),
    ("industry", "產業地圖"),
    ("industry/semiconductor", "單一產業鏈（半導體）"),
    ("stock/2330", "個股（2330）"),
    ("heatmap", "熱力圖"),
    ("heatmap/theme", "題材"),
    ("market", "市場明細"),
    ("season", "週期統計"),
]
WIDTHS = [1440, 1100, 800, 390]

CONSENT = ("try{if(!localStorage.getItem('tw.consent'))localStorage.setItem('tw.consent',"
           "JSON.stringify({v:'*',at:'test'}));"
           "if(!localStorage.getItem('tw.tour'))localStorage.setItem('tw.tour','*');}catch(e){}")

# 在頁面裡跑的量測：回傳圖表繪圖區、卡片幾何
JS = r"""
() => {
  const vw = innerWidth, vh = innerHeight;
  const docH = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight);
  const vis = el => { const s = getComputedStyle(el); if (s.display==='none'||s.visibility==='hidden') return false;
    const r = el.getBoundingClientRect(); return r.width>4 && r.height>4; };
  const inView = el => { let p = el; while (p && p!==document.body) { const s = getComputedStyle(p);
      if (s.display==='none' || s.visibility==='hidden') return false; p = p.parentElement; } return true; };
  const view = document.querySelector('.view.on') || document.querySelector('main');
  const rects = [];        // 繪圖區（頁面座標）
  const sy = scrollY;
  const push = (x,y,w,h,kind,id) => { if (w>8 && h>8) rects.push({x, y:y+sy, w, h, kind, id}); };
  // ECharts
  const ecs = [...document.querySelectorAll('[_echarts_instance_]')].filter(el => vis(el) && inView(el));
  for (const el of ecs) {
    const inst = window.echarts && echarts.getInstanceByDom(el); if (!inst) continue;
    const r = el.getBoundingClientRect(); const id = el.id || (el.parentElement && el.parentElement.id) || '';
    let done = false;
    try {
      const m = inst.getModel();
      const grids = m.getComponent('grid') ? m.findComponents({mainType:'grid'}) : [];
      for (const g of grids) { const cs = g.coordinateSystem; if (!cs) continue; const gr = cs.getRect();
        push(r.left+gr.x, r.top+gr.y, gr.width, gr.height, 'ec-grid', id); done = true; }
      const pol = m.findComponents({mainType:'polar'});
      for (const p of pol) { const cs = p.coordinateSystem; if (!cs) continue; const rr = cs.getRadiusAxis().getExtent()[1];
        push(r.left+cs.cx-rr, r.top+cs.cy-rr, 2*rr, 2*rr, 'ec-polar', id); done = true; }
      if (!done) m.eachSeries(s => { const li = s.layoutInfo; if (li && li.width) {
        push(r.left+li.x, r.top+li.y, li.width, li.height, 'ec-'+s.subType, id); done = true; } });
    } catch (e) {}
    if (!done) push(r.left, r.top, r.width, r.height, 'ec-box', id);
  }
  // Lightweight Charts：主圖窗格（寬度超過整張一半的 canvas，排除價格軸／時間軸）
  for (const t of document.querySelectorAll('.tv-lightweight-charts')) {
    if (!vis(t) || !inView(t)) continue;
    const tr = t.getBoundingClientRect();
    const tds = [...t.querySelectorAll('td')].filter(td => { const b = td.getBoundingClientRect();
      return b.width > tr.width*0.5 && b.height > 30; });
    const seen = new Set();
    for (const td of tds) { const b = td.getBoundingClientRect(); const k = Math.round(b.top)+':'+Math.round(b.left);
      if (seen.has(k)) continue; seen.add(k); push(b.left, b.top, b.width, b.height, 'lwc', t.parentElement && t.parentElement.id || ''); }
  }
  // 大張 SVG（剖析圖、產業關聯圖）；排除 ECharts 內部與小圖示
  for (const s of document.querySelectorAll('main svg')) {
    if (s.closest('[_echarts_instance_]') || s.closest('.tv-lightweight-charts')) continue;
    if (s.parentElement && s.parentElement.closest('svg')) continue;
    if (!vis(s) || !inView(s)) continue;
    const b = s.getBoundingClientRect(); if (b.width*b.height < 40000) continue;
    push(b.left, b.top, b.width, b.height, 'svg', s.id || s.getAttribute('class') || '');
  }
  // 卡片幾何
  const main = document.querySelector('main'); const mr = main.getBoundingClientRect();
  const cards = [...(view||main).querySelectorAll('.card')].filter(c => vis(c) && inView(c) && !c.parentElement.closest('.card'));
  const cb = cards.map(c => { const b = c.getBoundingClientRect(); return {x:b.left, y:b.top+sy, w:b.width, h:b.height, el:c}; });
  const gapsH = [], gapsV = [];
  for (const a of cb) for (const b of cb) { if (a===b) continue;
    const ov = Math.min(a.y+a.h, b.y+b.h) - Math.max(a.y, b.y);
    if (ov > 40 && b.x >= a.x + a.w - 1) { const g = b.x - (a.x+a.w); if (g >= 0 && g < 80) gapsH.push(Math.round(g)); }
    const ovx = Math.min(a.x+a.w, b.x+b.w) - Math.max(a.x, b.x);
    if (ovx > 40 && b.y >= a.y + a.h - 1) { const g = b.y - (a.y+a.h); if (g >= 0 && g < 80) gapsV.push(Math.round(g)); } }
  // 只留每張卡最近的那個鄰居
  const pads = cards.map(c => { const s = getComputedStyle(c); return s.paddingTop+'/'+s.paddingLeft; });
  const heads = [];
  for (const c of cb) { const b = rects.filter(r => r.x >= c.x-2 && r.x+r.w <= c.x+c.w+2 && r.y >= c.y-2 && r.y < c.y+c.h);
    if (!b.length) continue; const top = Math.min(...b.map(r => r.y)); heads.push(Math.round(top - c.y)); }
  const side = document.querySelector('aside'); let sideW = 0;
  if (side && vis(side) && getComputedStyle(side).position !== 'fixed') sideW = Math.round(side.getBoundingClientRect().width);
  const top = document.querySelector('.topbar'); const topH = top ? Math.round(top.getBoundingClientRect().height) : 0;
  const vr = (view||main).getBoundingClientRect();
  return {vw, vh, docH, rects, viewTop: Math.round(vr.top+sy), viewBot: Math.round(vr.bottom+sy), mainX: Math.round(mr.left), mainW: Math.round(mr.width), sideW, topH,
          gapsH, gapsV, pads, heads, ncards: cards.length};
}
"""


def med(a):
    a = sorted(a)
    return a[len(a) // 2] if a else None


def mode(a):
    if not a:
        return None
    d = {}
    for x in a:
        d[x] = d.get(x, 0) + 1
    return max(d.items(), key=lambda kv: kv[1])[0]


def area_union(rects, clip=None):
    """矩形聯集面積（用 4px 網格柵格化，避免重疊重算）"""
    if not rects:
        return 0
    import numpy as np
    x0 = int(min(r["x"] for r in rects)); y0 = int(min(r["y"] for r in rects))
    x1 = int(max(r["x"] + r["w"] for r in rects)) + 1; y1 = int(max(r["y"] + r["h"] for r in rects)) + 1
    if clip:
        x0, y0 = max(x0, clip[0]), max(y0, clip[1]); x1, y1 = min(x1, clip[2]), min(y1, clip[3])
    if x1 <= x0 or y1 <= y0:
        return 0
    s = 4
    g = np.zeros(((y1 - y0) // s + 1, (x1 - x0) // s + 1), dtype=bool)
    for r in rects:
        a = max(int(r["x"]), x0); b = max(int(r["y"]), y0)
        c = min(int(r["x"] + r["w"]), x1); d = min(int(r["y"] + r["h"]), y1)
        if c > a and d > b:
            g[(b - y0) // s:(d - y0) // s, (a - x0) // s:(c - x0) // s] = True
    return int(g.sum()) * s * s


def blank_metrics(img, x0, x1, top, bot):
    """空白帶、空白格、最大全空矩形。img 是整頁截圖（PIL）；只看內容區 x0..x1、目前這一頁（.view.on）的上下緣之間
    —— 頁尾（免責聲明）與 main 的底部留白不算，那不是版面設計能省的地方。"""
    import numpy as np
    a = np.asarray(img.convert("RGB")).astype(np.int16)
    a = a[top:bot, x0:x1]
    H, W = a.shape[:2]
    if H < 16 or W < 16:
        return 0, 0, None
    # 1) 空白帶：整列 max-min ≤ 6（每個色版）
    rng = a.max(axis=1) - a.min(axis=1)       # H×3
    flat = (rng <= 6).all(axis=1)
    band = 0; run = 0
    for f in flat:
        if f:
            run += 1
        else:
            if run >= 24:
                band += run
            run = 0
    if run >= 24:
        band += run
    # 2) 空白格：16×16 方格內全部同色
    B = 16
    h2, w2 = H // B, W // B
    t = a[:h2 * B, :w2 * B].reshape(h2, B, w2, B, 3)
    cr = t.max(axis=(1, 3)) - t.min(axis=(1, 3))
    emp = (cr <= 6).all(axis=2)
    empty_pct = float(emp.mean() * 100)
    # 3) 最大全空矩形（直方圖法）
    best = (0, 0, 0, 0, 0)
    hist = [0] * w2
    for i in range(h2):
        row = emp[i]
        for j in range(w2):
            hist[j] = hist[j] + 1 if row[j] else 0
        st = []
        for j in range(w2 + 1):
            hh = hist[j] if j < w2 else 0
            start = j
            while st and st[-1][1] >= hh:
                s0, sh = st.pop()
                ar = sh * (j - s0)
                if ar > best[0]:
                    best = (ar, s0, i - sh + 1, j - s0, sh)
                start = s0
            st.append((start, hh))
    _, bx, by, bw, bh = best
    worst = {"x": x0 + bx * B, "y": top + by * B, "w": bw * B, "h": bh * B} if bw else None
    return band / H * 100, empty_pct, worst


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--shots", default="")
    ap.add_argument("--pages", default=",".join(p for p, _ in PAGES))
    ap.add_argument("--widths", default=",".join(str(w) for w in WIDTHS))
    ap.add_argument("--theme4", default="")
    ap.add_argument("--mode", default="dark")
    ap.add_argument("--port", type=int, default=8791)
    ap.add_argument("--wait", type=int, default=3500)
    args = ap.parse_args()

    from PIL import Image, ImageDraw
    from playwright.sync_api import sync_playwright

    site = Path(args.site).resolve()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), partial(_Q, directory=str(site)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{args.port}/index.html"
    shots = Path(args.shots) if args.shots else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    res = []
    names = dict(PAGES)
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
            for w in [int(x) for x in args.widths.split(",")]:
                h = 844 if w <= 480 else 900
                for route in args.pages.split(","):
                    ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=1,
                                        is_mobile=w <= 480, has_touch=w <= 480)
                    ctx.add_init_script(CONSENT)
                    ls = {"tw.theme": args.mode}
                    if args.theme4:
                        ls["tw.theme4"] = args.theme4
                    for k, v in ls.items():
                        ctx.add_init_script(f"try{{localStorage.setItem({k!r},{v!r});}}catch(e){{}}")
                    pg = ctx.new_page()
                    t0 = time.time()
                    pg.goto(f"{base}#{route}", wait_until="networkidle")
                    pg.wait_for_timeout(args.wait)
                    m = pg.evaluate(JS)
                    vw, vh = m["vw"], m["vh"]
                    plot1 = area_union(m["rects"], (0, 0, vw, vh)) / (vw * vh) * 100
                    plotP = area_union(m["rects"]) / (vw * m["docH"]) * 100
                    png = pg.screenshot(full_page=True)
                    img = Image.open(io.BytesIO(png))
                    band, empty, worst = blank_metrics(img, m["mainX"], m["mainX"] + m["mainW"],
                                                       max(m["topH"], m["viewTop"]), min(img.height, m["viewBot"]))
                    row = {
                        "route": route, "name": names.get(route, route), "w": w, "h": h,
                        "plot1": round(plot1, 1), "plotP": round(plotP, 1),
                        "mainW": m["mainW"], "sideW": m["sideW"], "docH": m["docH"],
                        "gapH": med(m["gapsH"]), "gapV": med(m["gapsV"]), "pad": mode(m["pads"]),
                        "head": med(m["heads"]), "ncards": m["ncards"], "ncharts": len(m["rects"]),
                        "blank": round(band, 1), "empty": round(empty, 1), "worst": worst,
                        "secs": round(time.time() - t0, 1),
                    }
                    res.append(row)
                    print(json.dumps({k: row[k] for k in ("route", "w", "plot1", "plotP", "mainW", "gapH", "gapV",
                                                          "pad", "head", "blank", "empty")}, ensure_ascii=False),
                          flush=True)
                    if shots:
                        tag = route.replace("/", "_")
                        img.convert("RGB").save(shots / f"{tag}-{w}-full.jpg", quality=72)
                        if worst:
                            # 最浪費的一塊：外擴 60px 裁下來、畫紅框
                            x, y, ww, hh = worst["x"], worst["y"], worst["w"], worst["h"]
                            cx0, cy0 = max(0, x - 60), max(0, y - 60)
                            cx1, cy1 = min(img.width, x + ww + 60), min(img.height, y + hh + 60)
                            crop = img.convert("RGB").crop((cx0, cy0, cx1, cy1))
                            d = ImageDraw.Draw(crop)
                            d.rectangle((x - cx0, y - cy0, x - cx0 + ww, y - cy0 + hh), outline=(255, 40, 40), width=3)
                            crop.save(shots / f"{tag}-{w}-worst.jpg", quality=80)
                    ctx.close()
            b.close()
    finally:
        srv.shutdown()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


class _Q(SimpleHTTPRequestHandler):
    def log_message(self, *a):  # noqa: D102
        pass


if __name__ == "__main__":
    raise SystemExit(main())
