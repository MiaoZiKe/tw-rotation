"""第三輪（橢圓／正圓）比較總覽：上排 e1、c1、封閉版；中排 389px 縮圖；下排試套（鴻海／台積電／鴻海精密 × 橢圓／正圓）。"""
import sys, base64
from pathlib import Path
from playwright.sync_api import sync_playwright
import title_styles as T
O = Path(sys.argv[1]).resolve()
b = lambda p: "data:image/png;base64," + base64.b64encode(Path(p).read_bytes()).decode()
img = lambda f, w: f'<img src="{b(O/f)}" width="{w}" height="{round(w*1350/1080)}">'
TOP = [("title_e1", "橢圓版 e1（缺口）"), ("title_c1", "正圓版 c1（缺口）"), ("title_e1_closed", "橢圓封閉版"), ("title_c1_closed", "正圓封閉版")]
TRY = [("hon", "鴻海"), ("tsmc", "台積電"), ("four", "鴻海精密（4 字）")]
r1 = "".join(f'<div><div class="lb">{n}</div>{img(f+".png", 400)}</div>' for f, n in TOP)
r2 = "".join(f'<div>{img(f+".png", 389)}</div>' for f, _ in TOP[:2])
r3 = "".join(f'<div><div class="lb sm">橢圓套「{n}」</div>{img(f"try_e_{k}.png", 300)}</div><div><div class="lb sm">正圓套「{n}」</div>{img(f"try_c_{k}.png", 300)}</div>' for k, n in TRY)
html = (f'<!doctype html><meta charset="utf-8"><style>{T.font_css()}*{{margin:0;box-sizing:border-box}}body{{width:2020px;background:#E9EDF3;font-family:TCS,sans-serif;padding:36px 40px}}.g{{display:flex;gap:28px;margin-bottom:30px;align-items:flex-start}}'
        f'.lb{{font-size:26px;font-weight:700;color:#6B7689;margin-bottom:8px}}.sm{{font-size:22px}}img{{display:block}}.cap{{font-size:24px;color:#3C4659;margin:0 0 10px}}</style>'
        f'<div class="g">{r1}</div><div class="cap">↓ 0.36 倍實際縮圖（389 px 寬）：橢圓版、正圓版</div><div class="g">{r2}</div><div class="cap">↓ 試套公司名</div><div class="g">{r3}</div>')
f = O / "_cmp.html"; f.write_text(html, encoding="utf8")
with sync_playwright() as p:
    br = p.chromium.launch(executable_path="/opt/pw-browsers/chromium"); pg = br.new_page(viewport={"width": 2100, "height": 800})
    pg.goto(f"file://{f}", wait_until="networkidle"); pg.wait_for_timeout(600); pg.screenshot(path=str(O / "title_ec_compare.png"), full_page=True); br.close()
f.unlink()
