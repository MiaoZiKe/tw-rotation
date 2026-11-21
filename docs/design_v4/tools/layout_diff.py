"""設計 v4 第二批 2C：改前／改後「版面副作用」比對（同一份資料、同一個瀏覽器、兩份網站並排）。

間距改動本來就會讓東西位移，所以「像素有差」不是問題；要抓的是**預期之外**的變化：
  wrap     文字換行數變了（例如按鈕列多一個 8px 間距 → 最後一顆掉到第二行）
  trunc    多出來的「被截斷」文字（overflow 隱藏＋內容比框寬，例如 ellipsis 多吃掉幾個字）
  overflow 多出來的橫向捲軸（文件寬 > 視窗寬）
  pix      第一屏像素差異比例（%）＋差異圖；**390 寬應該是 0**（手機一屏版刻意不動）

用法：
    flock /tmp/claude-0/browser.lock python docs/design_v4/tools/layout_diff.py \
        --a <改前 site> --b <改後 site> --out <資料夾> [--pages overview,flow] [--widths 1440,800,390]
"""
from __future__ import annotations

import argparse
import io
import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PAGES = ["overview", "flow", "industry", "industry/semiconductor", "stock/2330", "heatmap/theme", "season", "market"]
CONSENT = ("try{if(!localStorage.getItem('tw.consent'))localStorage.setItem('tw.consent',"
           "JSON.stringify({v:'*',at:'test'}));"
           "if(!localStorage.getItem('tw.tour'))localStorage.setItem('tw.tour','*');}catch(e){}")

JS = r"""
() => {
  const out = []; const vw = innerWidth;
  const path = el => { const a = []; while (el && el !== document.body) { let i = 1, s = el;
      while ((s = s.previousElementSibling)) i++; a.push(el.tagName.toLowerCase() + ':' + i); el = el.parentElement; } return a.reverse().join('>'); };
  const vis = el => { const r = el.getBoundingClientRect(); if (r.width < 1 || r.height < 1) return false;
    let p = el; while (p && p !== document.documentElement) { const s = getComputedStyle(p);
      if (s.display === 'none' || s.visibility === 'hidden' || +s.opacity === 0) return false; p = p.parentElement; } return true; };
  const all = document.querySelectorAll('.topbar *, main *');
  for (const el of all) {
    if (el.closest('svg') || el.closest('[_echarts_instance_]') || el.closest('.tv-lightweight-charts') || el.closest('canvas')) continue;
    let txt = ''; for (const n of el.childNodes) if (n.nodeType === 3) txt += n.textContent;
    txt = txt.replace(/\s+/g, ' ').trim(); if (!txt) continue;
    if (!vis(el)) continue;
    const rg = document.createRange(); const tops = new Set();
    for (const n of el.childNodes) if (n.nodeType === 3 && n.textContent.trim()) { rg.selectNodeContents(n);
      for (const r of rg.getClientRects()) if (r.width > 0.5) tops.add(Math.round(r.top / 3)); }
    const s = getComputedStyle(el);
    const trunc = (s.overflow !== 'visible' || s.overflowX !== 'visible' || s.textOverflow === 'ellipsis') && el.scrollWidth > el.clientWidth + 1;
    out.push({k: path(el), t: txt.slice(0, 40), lines: tops.size, trunc, w: Math.round(el.getBoundingClientRect().width)});
  }
  return {els: out, docW: document.documentElement.scrollWidth, vw, docH: document.documentElement.scrollHeight};
}
"""


class _Q(SimpleHTTPRequestHandler):
    def log_message(self, *a):  # noqa: D102
        pass


def serve(d, port):
    srv = ThreadingHTTPServer(("127.0.0.1", port), partial(_Q, directory=str(Path(d).resolve())))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def grab(b, base, route, w, theme4, mode, wait):
    h = 844 if w <= 480 else 900
    ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=1, is_mobile=w <= 480, has_touch=w <= 480,
                        reduced_motion="reduce")
    ctx.add_init_script(CONSENT)
    for k, v in {"tw.theme": mode, "tw.theme4": theme4}.items():
        ctx.add_init_script(f"try{{localStorage.setItem({k!r},{v!r});}}catch(e){{}}")
    pg = ctx.new_page()
    pg.goto(f"{base}#{route}", wait_until="networkidle")
    pg.wait_for_timeout(wait)
    m = pg.evaluate(JS)
    png = pg.screenshot()
    ctx.close()
    return m, png


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pages", default=",".join(PAGES))
    ap.add_argument("--widths", default="1440,800,390")
    ap.add_argument("--theme4", default="hud")
    ap.add_argument("--mode", default="dark")
    ap.add_argument("--wait", type=int, default=3000)
    a = ap.parse_args()
    import numpy as np
    from PIL import Image
    from playwright.sync_api import sync_playwright
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    sa, sb = serve(a.a, 8793), serve(a.b, 8794)
    res = []
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
            for w in [int(x) for x in a.widths.split(",")]:
                for route in a.pages.split(","):
                    ma, pa = grab(b, "http://127.0.0.1:8793/index.html", route, w, a.theme4, a.mode, a.wait)
                    mb, pb = grab(b, "http://127.0.0.1:8794/index.html", route, w, a.theme4, a.mode, a.wait)
                    A = {e["k"]: e for e in ma["els"]}
                    wrap, trunc = [], []
                    for e in mb["els"]:
                        o = A.get(e["k"])
                        if not o or o["t"] != e["t"]:
                            continue
                        if o["lines"] != e["lines"]:
                            wrap.append({"t": e["t"], "a": o["lines"], "b": e["lines"], "wa": o["w"], "wb": e["w"], "k": e["k"][-80:]})
                        if e["trunc"] and not o["trunc"]:
                            trunc.append({"t": e["t"], "w": e["w"], "k": e["k"][-80:]})
                    ia = np.asarray(Image.open(io.BytesIO(pa)).convert("RGB")).astype(np.int16)
                    ib = np.asarray(Image.open(io.BytesIO(pb)).convert("RGB")).astype(np.int16)
                    hh = min(ia.shape[0], ib.shape[0])
                    d = (np.abs(ia[:hh] - ib[:hh]).max(axis=2) > 24)
                    pix = float(d.mean() * 100)
                    tag = route.replace("/", "_") + f"-{w}"
                    if pix > 0:
                        vis = (ib[:hh] * 0.35).astype(np.uint8)
                        vis[d] = [255, 60, 60]
                        Image.fromarray(vis).save(out / f"{tag}-diff.png")
                    Image.open(io.BytesIO(pa)).convert("RGB").save(out / f"{tag}-a.jpg", quality=80)
                    Image.open(io.BytesIO(pb)).convert("RGB").save(out / f"{tag}-b.jpg", quality=80)
                    row = {"route": route, "w": w, "pix": round(pix, 2), "wrap": wrap, "trunc": trunc,
                           "docWa": ma["docW"], "docWb": mb["docW"], "docHa": ma["docH"], "docHb": mb["docH"],
                           "nA": len(ma["els"]), "nB": len(mb["els"])}
                    res.append(row)
                    print(f"{route:24s} {w:5d} 像素差 {pix:6.2f}%  換行變 {len(wrap):3d}  新截斷 {len(trunc):3d}  "
                          f"文件寬 {ma['docW']}→{mb['docW']}  頁高 {ma['docH']}→{mb['docH']}", flush=True)
            b.close()
    finally:
        sa.shutdown()
        sb.shutdown()
    (out / "diff.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
