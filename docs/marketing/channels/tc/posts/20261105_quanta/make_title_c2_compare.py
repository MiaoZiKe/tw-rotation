"""第四輪（正圓、膠囊 12 點鐘、副標在右）比較總覽：上排廣達修改前後；中排 389px 縮圖（廣達＋四字兩種排法）；下排全部試套。"""
import sys, base64, json
from pathlib import Path
from playwright.sync_api import sync_playwright
import title_styles as T
O = Path(sys.argv[1]).resolve()
b = lambda p: "data:image/png;base64," + base64.b64encode(Path(p).read_bytes()).decode()
img = lambda f, w: f'<img src="{b(O/(f+".png"))}" width="{w}" height="{round(w*1350/1080)}">'
fs = lambda k: json.load(open(O / f"overlap_{k}.json"))["font"]
top = f'<div><div class="lb">廣達 修改前（c1）</div>{img("title_c1_prev", 480)}</div><div><div class="lb">廣達 修改後（c2）</div>{img("title_c2", 480)}</div>'
mid_items = [("title_c2", "廣達", None), ("try_c2_tokyo_a", "東京威力 (a) 一行", "try_c2_tokyo_a"), ("try_c2_tokyo_b", "東京威力 (b) 2×2", "try_c2_tokyo_b"), ("try_c2_four_a", "鴻海精密 (a) 一行", "try_c2_four_a"), ("try_c2_four_b", "鴻海精密 (b) 2×2", "try_c2_four_b")]
mid = "".join(f'<div><div class="lb sm">{n}　字級 {fs(k) if k else fs("title_c2")}px</div>{img(f, 389)}</div>' for f, n, k in mid_items)
tr = [("try_c2_hon", "鴻海"), ("try_c2_tsmc", "台積電"), ("try_c2_tokyo_a", "東京威力(a)"), ("try_c2_tokyo_b", "東京威力(b)"), ("try_c2_four_a", "鴻海精密(a)"), ("try_c2_four_b", "鴻海精密(b)"), ("try_c2_asml", "ASML")]
bot = "".join(f'<div><div class="lb sm2">{n}　{fs(f)}px</div>{img(f, 290)}</div>' for f, n in tr)
html = (f'<!doctype html><meta charset="utf-8"><style>{T.font_css()}*{{margin:0;box-sizing:border-box}}body{{width:2300px;background:#E9EDF3;font-family:TCS,sans-serif;padding:36px 40px}}.g{{display:flex;gap:28px;margin-bottom:30px;align-items:flex-start}}'
        f'.lb{{font-size:28px;font-weight:700;color:#6B7689;margin-bottom:8px}}.sm{{font-size:23px}}.sm2{{font-size:21px}}img{{display:block}}.cap{{font-size:24px;color:#3C4659;margin:0 0 10px}}</style>'
        f'<div class="g">{top}</div><div class="cap">↓ 389 px 寬實際縮圖</div><div class="g">{mid}</div><div class="cap">↓ 試套公司名（標題旁為公司名字級）</div><div class="g">{bot}</div>')
f = O / "_cmp.html"; f.write_text(html, encoding="utf8")
with sync_playwright() as p:
    br = p.chromium.launch(executable_path="/opt/pw-browsers/chromium"); pg = br.new_page(viewport={"width": 2380, "height": 800})
    pg.goto(f"file://{f}", wait_until="networkidle"); pg.wait_for_timeout(600); pg.screenshot(path=str(O / "title_c2_compare.png"), full_page=True); br.close()
f.unlink()
