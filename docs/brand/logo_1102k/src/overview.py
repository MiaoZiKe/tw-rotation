import sys, os, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import OUT, FD
import designs
from playwright.sync_api import sync_playwright
HD = os.path.dirname(os.path.abspath(__file__))
css = f"""
@font-face{{font-family:T;font-weight:900;src:url('file://{FD}/noto-sans-tc-chinese-traditional-900-normal.woff2')}}
body{{margin:0;background:#fff;font-family:T,sans-serif;color:#1F2A44;width:1700px}}
h1{{font-size:30px;margin:0;padding:26px 34px 4px;font-weight:900}} .sub{{padding:0 34px 14px;font-size:15px;color:#555}}
.row{{display:flex;align-items:center;padding:0 34px;border-bottom:1px solid #e3e3e3;height:250px}} .c{{flex:none;text-align:center}}
.lab{{width:360px;text-align:left}} .lab b{{font-size:21px;font-weight:900}} .lab em{{font-style:normal;font-size:12px;color:#888;margin-left:8px}} .lab span{{display:block;font-size:13px;color:#555;margin-top:5px;line-height:1.5;width:330px}}
.big img{{width:220px;height:220px}} .big{{width:250px}} .i110{{width:140px}} .i40{{width:70px}} .w{{width:480px}} .w img{{width:460px;height:153px;border:1px solid #e6e6e6}}
.g{{display:grid;grid-template-columns:repeat(5,1fr);gap:16px;padding:10px 34px 30px}} .cell{{text-align:center;font-weight:900;font-size:17px}} .cell img{{width:300px;height:300px}}
"""
def row(D):
    i = D['id']; P = designs.PALS[D['pal']]
    return (f'<div class="row"><div class="c lab"><b>{i}　{D["name"]}</b><em>{P["name"]}</em><span>{D["idea"]}</span></div>'
            f'<div class="c big"><img src="file://{OUT}/{i}_icon512.png"></div>'
            f'<div class="c i110"><img src="file://{OUT}/{i}_ig110.png" width="110" height="110"></div>'
            f'<div class="c i40"><img src="file://{OUT}/{i}_ig40.png" width="40" height="40"></div>'
            f'<div class="c w"><img src="file://{OUT}/{i}_word.png"></div></div>')
html = f"""<html><head><meta charset="utf-8"><style>{css}</style></head><body>
<h1>哩股哩股 LIGU 字母×股票元素交織 10 款（K01～K10）</h1>
<div class="sub">每款：方形頭像大圖、IG 圓形 110px、40px（實際像素）、橫式字標。配色：陽光糖果／墨藍＋金／白黑＋台股紅／深藍＋青；紅綠只代表漲跌。</div>
{''.join(row(D) for D in designs.DESIGNS)}</body></html>"""
cells = ''.join(f'<div class="cell"><img src="file://{OUT}/{D["id"]}_icon512.png"><div>{D["id"]}　{D["name"]}</div></div>' for D in designs.DESIGNS)
h2 = f"""<html><head><meta charset="utf-8"><style>{css} body{{width:1700px}}</style></head><body><h1>LIGU 頭像 10 款並排</h1><div class="g">{cells}</div></body></html>"""
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=glob.glob("/opt/pw-browsers/chromium_headless_shell-*/*/chrome-headless-shell")[0], args=['--allow-file-access-from-files'])
    pg = b.new_page(viewport={'width': 1700, 'height': 900})
    for name, h in [('overview', html), ('overview_avatars', h2)]:
        p = os.path.join(HD, '_t.html'); open(p, 'w').write(h)
        pg.goto('file://' + p); pg.wait_for_timeout(600)
        pg.screenshot(path=os.path.join(OUT, name + '.png'), full_page=True)
    b.close()
os.remove(os.path.join(HD, '_t.html'))
