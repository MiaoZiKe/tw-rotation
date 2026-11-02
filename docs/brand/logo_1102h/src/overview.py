import sys, os, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import OUT, FD
import designs
from playwright.sync_api import sync_playwright

css = f"""
@font-face{{font-family:T;font-weight:900;src:url('file://{FD}/noto-sans-tc-chinese-traditional-900-normal.woff2')}}
@font-face{{font-family:T;font-weight:700;src:url('file://{FD}/noto-sans-tc-chinese-traditional-700-normal.woff2')}}
body{{margin:0;background:#fff;font-family:T,sans-serif;color:#1F2A44;width:2420px}}
h1{{font-size:30px;margin:0;padding:26px 34px 4px;font-weight:900}}
.sub{{padding:0 34px 14px;font-size:15px;color:#555}}
.hd,.row{{display:flex;align-items:center;padding:0 34px}}
.hd{{font-size:13px;font-weight:700;color:#444;border-bottom:2px solid #1F2A44;padding-bottom:6px}}
.row{{border-bottom:1px solid #e3e3e3;height:178px}}
.c{{flex:none;text-align:center}}
.lab{{width:300px;text-align:left}}
.lab b{{font-size:21px;font-weight:900}} .lab span{{display:block;font-size:13px;color:#555;margin-top:4px;line-height:1.45;width:270px}}
.w{{width:352px}} .w img{{width:336px;height:112px;border:1px solid #e6e6e6;display:block;margin:auto}}
.ic{{width:140px}} .ic img{{width:124px;height:124px}}
.i110{{width:130px}} .i40{{width:64px}}
.sp{{width:20px}}
"""
def row(D):
    i = D['id']
    h = f'<div class="c lab"><b>{i}　{D["name"]}</b><span>{D["idea"]}</span></div>'
    for pk in 'AB':
        for m in ('light', 'dark'):
            h += f'<div class="c w"><img src="file://{OUT}/{i}_{pk}_{m}.png"></div>'
    h += '<div class="sp"></div>'
    for pk in 'AB': h += f'<div class="c ic"><img src="file://{OUT}/{i}_{pk}_icon512.png"></div>'
    for pk in 'AB': h += f'<div class="c i110"><img src="file://{OUT}/{i}_{pk}_ig110.png" width="110" height="110"></div>'
    for pk in 'AB': h += f'<div class="c i40"><img src="file://{OUT}/{i}_{pk}_ig40.png" width="40" height="40"></div>'
    return f'<div class="row">{h}</div>'

html = f"""<html><head><meta charset="utf-8"><style>{css}</style></head><body>
<h1>哩股哩股 LIGU LOGO 第八輪：完整 L-I-G-U 字標 10 種</h1>
<div class="sub">配色 A＝陽光糖果（#FFF7E8／#1F2A44／橘／藍／紫／青）；配色 B＝墨夜金紅（深墨藍＋漲紅＋金＋跌綠，財經專業向）。每種：橫式 A 淺／A 深／B 淺／B 深、方形圖示 A／B、IG 圓形 110px、40px（皆實際像素，未放大）。</div>
<div class="hd"><div class="c lab">風格與理念</div><div class="c w">橫式 A 淺底</div><div class="c w">橫式 A 深底</div><div class="c w">橫式 B 淺底</div><div class="c w">橫式 B 深底</div><div class="sp"></div>
<div class="c ic">方形 A</div><div class="c ic">方形 B</div><div class="c i110">IG 110 A</div><div class="c i110">IG 110 B</div><div class="c i40">40 A</div><div class="c i40">40 B</div></div>
{''.join(row(D) for D in designs.DESIGNS)}
</body></html>"""
open(os.path.join(os.path.dirname(__file__), '_ov.html'), 'w').write(html)
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=glob.glob("/opt/pw-browsers/chromium_headless_shell-*/*/chrome-headless-shell")[0], args=['--allow-file-access-from-files'])
    pg = b.new_page(viewport={'width': 2420, 'height': 900})
    pg.goto('file://' + os.path.join(os.path.dirname(__file__), '_ov.html')); pg.wait_for_timeout(600)
    pg.screenshot(path=os.path.join(OUT, 'overview.png'), full_page=True)
    # 大圖：每種一格，橫式 A淺/B深 大張
    cells = ''
    for D in designs.DESIGNS:
        cells += f'<div class="cell"><div class="t">{D["id"]}　{D["name"]}</div><img src="file://{OUT}/{D["id"]}_A_light.png"><img src="file://{OUT}/{D["id"]}_B_dark.png"></div>'
    h2 = f"""<html><head><meta charset="utf-8"><style>{css}
    body{{width:1900px}} .g{{display:grid;grid-template-columns:1fr 1fr;gap:6px 24px;padding:10px 34px 30px}}
    .cell{{display:flex;flex-wrap:wrap;gap:0}} .cell .t{{width:100%;font-weight:900;font-size:19px;padding:10px 0 4px}}
    .cell img{{width:442px;height:147px;border:1px solid #e6e6e6}}</style></head><body><h1>LIGU 字標大圖（A 淺底／B 深底）</h1><div class="g">{cells}</div></body></html>"""
    open(os.path.join(os.path.dirname(__file__), '_ov2.html'), 'w').write(h2)
    pg.set_viewport_size({'width': 1900, 'height': 900})
    pg.goto('file://' + os.path.join(os.path.dirname(__file__), '_ov2.html')); pg.wait_for_timeout(600)
    pg.screenshot(path=os.path.join(OUT, 'overview_wordmarks.png'), full_page=True)
    b.close()
