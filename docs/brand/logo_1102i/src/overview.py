import sys, os, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import OUT, FD
import designs
from playwright.sync_api import sync_playwright
HD = os.path.dirname(os.path.abspath(__file__))
css = f"""
@font-face{{font-family:T;font-weight:900;src:url('file://{FD}/noto-sans-tc-chinese-traditional-900-normal.woff2')}}
@font-face{{font-family:T;font-weight:700;src:url('file://{FD}/noto-sans-tc-chinese-traditional-700-normal.woff2')}}
body{{margin:0;background:#fff;font-family:T,sans-serif;color:#1F2A44;width:2300px}}
h1{{font-size:30px;margin:0;padding:26px 34px 4px;font-weight:900}} .sub{{padding:0 34px 14px;font-size:15px;color:#555}}
.hd,.row{{display:flex;align-items:center;padding:0 34px}}
.hd{{font-size:13px;font-weight:700;color:#444;border-bottom:2px solid #1F2A44;padding-bottom:6px}}
.row{{border-bottom:1px solid #e3e3e3;height:164px}} .c{{flex:none;text-align:center}}
.lab{{width:330px;text-align:left}} .lab b{{font-size:21px;font-weight:900}} .lab span{{display:block;font-size:13px;color:#555;margin-top:4px;line-height:1.45;width:300px}}
.w{{width:372px}} .w img{{width:360px;height:120px;border:1px solid #e6e6e6;display:block;margin:auto}}
.ic{{width:140px}} .ic img{{width:124px;height:124px}} .i110{{width:128px}} .i40{{width:62px}} .sp{{width:16px}}
"""
def row(D):
    i = D['id']
    h = f'<div class="c lab"><b>{i}　{D["name"]}</b><span>{D["idea"]}</span></div>'
    for m in ('light', 'dark'): h += f'<div class="c w"><img src="file://{OUT}/{i}_{m}.png"></div>'
    h += '<div class="sp"></div>'
    for m in ('light', 'dark'): h += f'<div class="c ic"><img src="file://{OUT}/{i}_icon512_{m}.png"></div>'
    for m in ('light', 'dark'): h += f'<div class="c i110"><img src="file://{OUT}/{i}_ig110_{m}.png" width="110" height="110"></div>'
    for m in ('light', 'dark'): h += f'<div class="c i40"><img src="file://{OUT}/{i}_ig40_{m}.png" width="40" height="40"></div>'
    return f'<div class="row">{h}</div>'
html = f"""<html><head><meta charset="utf-8"><style>{css}</style></head><body>
<h1>哩股哩股 LIGU 連筆資金線 12 種變化（I01～I12）</h1>
<div class="sub">以 H04 連筆資金線為核心；配色＝陽光糖果（底 #FFF7E8／墨藍 #1F2A44／橘／藍／紫／青；I09 資金線用台股紅）。每款：橫式淺／深、方形圖示淺／深、IG 圓形 110px、40px（皆實際像素，未放大）。</div>
<div class="hd"><div class="c lab">款式與理念</div><div class="c w">橫式 淺底</div><div class="c w">橫式 深底</div><div class="sp"></div><div class="c ic">方形 淺</div><div class="c ic">方形 深</div><div class="c i110">IG 110 淺</div><div class="c i110">IG 110 深</div><div class="c i40">40 淺</div><div class="c i40">40 深</div></div>
{''.join(row(D) for D in designs.DESIGNS)}</body></html>"""
cells = ''.join(f'<div class="cell"><div class="t">{D["id"]}　{D["name"]}</div><img src="file://{OUT}/{D["id"]}_light.png"><img src="file://{OUT}/{D["id"]}_dark.png"></div>' for D in designs.DESIGNS)
h2 = f"""<html><head><meta charset="utf-8"><style>{css}
body{{width:1900px}} .g{{display:grid;grid-template-columns:1fr 1fr;gap:6px 24px;padding:10px 34px 30px}}
.cell{{display:flex;flex-wrap:wrap}} .cell .t{{width:100%;font-weight:900;font-size:19px;padding:10px 0 4px}} .cell img{{width:442px;height:147px;border:1px solid #e6e6e6}}</style></head><body><h1>連筆資金線 12 種字標大圖（淺底／深底）</h1><div class="g">{cells}</div></body></html>"""
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=glob.glob("/opt/pw-browsers/chromium_headless_shell-*/*/chrome-headless-shell")[0], args=['--allow-file-access-from-files'])
    pg = b.new_page(viewport={'width': 2300, 'height': 900})
    for name, h, wd in [('overview', html, 2300), ('overview_wordmarks', h2, 1900)]:
        p = os.path.join(HD, '_t.html'); open(p, 'w').write(h)
        pg.set_viewport_size({'width': wd, 'height': 900}); pg.goto('file://' + p); pg.wait_for_timeout(600)
        pg.screenshot(path=os.path.join(OUT, name + '.png'), full_page=True)
    b.close()
os.remove(os.path.join(HD, '_t.html'))
