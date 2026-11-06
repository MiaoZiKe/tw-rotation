"""第六輪比較總覽：上排 LOGO 對照＋D1/D2/D3；中排 389px 縮圖；下排以推薦款 D1 試套台積電、東京威力（兩行）。"""
import sys, base64, json
from pathlib import Path
from playwright.sync_api import sync_playwright
import title_styles as T
O = Path(sys.argv[1]).resolve(); svg = Path(sys.argv[2]).read_text(encoding="utf8")
b = lambda p: "data:image/png;base64," + base64.b64encode(Path(p).read_bytes()).decode()
img = lambda f, w: f'<img src="{b(O/(f+".png"))}" width="{w}" height="{round(w*1350/1080)}">'
logo = "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
J = lambda k: json.load(open(O / f"overlap_{k}.json"))
ink = lambda k: (J(k)["boxes"]["shuo"][3] - J(k)["boxes"]["shuo"][1]) * 389 / 1080
top = (f'<div><div class="lb">LOGO 對照</div><img src="{logo}" width="380" height="380"></div>'
       f'<div><div class="lb">D1　膠囊高＝線粗 60</div>{img("title_d1", 460)}<div class="rs">膠囊 160×60、字 44px；縮圖字高約 {ink("title_d1"):.0f}px。推薦。</div></div>'
       f'<div><div class="lb">D2　橘圓 R1（直徑 108）</div>{img("title_d2", 460)}<div class="rs">「透明說」品字形 40px；縮圖三字整塊高約 {ink("title_d2"):.0f}px，單字約 14px。</div></div>'
       f'<div><div class="lb">D3　橘圓點 R2（直徑＝線粗 60）</div>{img("title_d3", 460)}<div class="rs">字 44px 在點右側；縮圖字高約 {ink("title_d3"):.0f}px。最像 LOGO。</div></div>')
mid = "".join(f'<div>{img(f, 389)}</div>' for f in ("title_d1", "title_d2", "title_d3"))
bot = "".join(f'<div><div class="lb sm">{n}</div>{img(f, 389)}</div>' for f, n in (("try_d1_tsmc", f"D1 套「台積電」字級 {J('try_d1_tsmc')['font']}px"), ("try_d1_tokyo", f"D1 套「東京威力」兩行 字級 {J('try_d1_tokyo')['font']}px")))
html = (f'<!doctype html><meta charset="utf-8"><style>{T.font_css()}*{{margin:0;box-sizing:border-box}}body{{width:2060px;background:#E9EDF3;font-family:TCS,sans-serif;padding:36px 40px}}.g{{display:flex;gap:28px;margin-bottom:30px;align-items:flex-start}}'
        f'.lb{{font-size:28px;font-weight:700;color:#6B7689;margin-bottom:8px}}.sm{{font-size:23px}}.rs{{font-size:22px;line-height:32px;color:#3C4659;margin-top:10px;width:460px}}img{{display:block}}.cap{{font-size:24px;color:#3C4659;margin:0 0 10px}}</style>'
        f'<div class="g">{top}</div><div class="cap">↓ 389 px 寬實際縮圖</div><div class="g">{mid}</div><div class="cap">↓ 用推薦款 D1 試套</div><div class="g">{bot}</div>')
f = O / "_cmp.html"; f.write_text(html, encoding="utf8")
with sync_playwright() as p:
    br = p.chromium.launch(executable_path="/opt/pw-browsers/chromium"); pg = br.new_page(viewport={"width": 2140, "height": 800})
    pg.goto(f"file://{f}", wait_until="networkidle"); pg.wait_for_timeout(600); pg.screenshot(path=str(O / "title_d_compare.png"), full_page=True); br.close()
f.unlink()
