"""定稿（d6_best）比較：廣達主圖＋鴻海／台積電／東京威力（2×2）／ASML 試套，各附 389px 縮圖。用法：python make_title_final_compare.py <含 1_cover.png 與 try_final_*.png 的資料夾>"""
import sys, base64, json
from pathlib import Path
from playwright.sync_api import sync_playwright
import title_styles as T
O = Path(sys.argv[1]).resolve()
b = lambda p: "data:image/png;base64," + base64.b64encode(Path(p).read_bytes()).decode()
img = lambda f, w: f'<img src="{b(O/(f+".png"))}" width="{w}" height="{round(w*1350/1080)}">'
J = lambda k: json.load(open(O / f"overlap_{k}.json"))
items = [("1_cover", "廣達（一行）"), ("try_final_hon", "鴻海（一行）"), ("try_final_tsmc", "台積電（一行）"), ("try_final_tokyo", "東京威力（2×2）"), ("try_final_asml", "ASML（英文一行）")]
row1 = "".join(f'<div><div class="lb">{n}　公司名字級 {J(k)["font"]}px</div>{img(k, 400)}</div>' for k, n in items)
row2 = "".join(f'<div><div class="lb sm">389 px 寬</div>{img(k, 389)}</div>' for k, n in items[:1] + items[3:4])
html = (f'<!doctype html><meta charset="utf-8"><style>{T.font_css()}*{{margin:0;box-sizing:border-box}}body{{width:2140px;background:#E9EDF3;font-family:TCS,sans-serif;padding:36px 40px}}.g{{display:flex;gap:24px;margin-bottom:30px;align-items:flex-start}}.lb{{font-size:26px;font-weight:700;color:#6B7689;margin-bottom:8px}}.sm{{font-size:22px}}img{{display:block}}.cap{{font-size:24px;color:#3C4659;margin:0 0 10px}}</style>'
        f'<div class="g">{row1}</div><div class="cap">↓ 389 px 寬實際縮圖（廣達、東京威力）</div><div class="g">{row2}</div>')
f = O / "_cmp.html"; f.write_text(html, encoding="utf8")
with sync_playwright() as p:
    br = p.chromium.launch(executable_path="/opt/pw-browsers/chromium"); pg = br.new_page(viewport={"width": 2220, "height": 800})
    pg.goto(f"file://{f}", wait_until="networkidle"); pg.wait_for_timeout(600); pg.screenshot(path=str(O / "final_compare.png"), full_page=True); br.close()
f.unlink()
