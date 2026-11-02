import sys, os, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import OUT, FD
import designs as DS
from playwright.sync_api import sync_playwright
css=f"""@font-face{{font-family:T;font-weight:900;src:url('file://{FD}/noto-sans-tc-chinese-traditional-900-normal.woff2')}}
body{{margin:0;background:#fff;font-family:T,sans-serif;color:#1F2A44;width:1700px}}
h1{{font-size:30px;margin:0;padding:24px 32px 4px;font-weight:900}} .sub{{padding:0 32px 12px;font-size:15px;color:#555}}
.hd,.row{{display:flex;align-items:center;padding:0 32px}} .hd{{font-size:14px;font-weight:900;border-bottom:2px solid #1F2A44;padding-bottom:6px}}
.row{{border-bottom:1px solid #e3e3e3;height:166px}} .c{{flex:none;text-align:center}}
.lab{{width:640px;text-align:left}} .lab b{{font-size:22px;font-weight:900}}
.lab .th{{display:block;font-size:15px;font-weight:900;color:#E8590C;margin-top:3px}}
.lab span.i{{display:block;font-size:13px;color:#555;margin-top:4px;line-height:1.5;width:600px}}
.sq{{width:160px}} .sq img{{width:130px;height:130px}} .i110{{width:140px}} .i40{{width:80px}} .w{{width:420px}} .w img{{width:400px;height:133px;border:1px solid #e6e6e6}}
"""
rows=''
for D in DS.D:
    i=D['id']
    rows+=f'<div class="row"><div class="c lab"><b>{i}　{D["name"]}</b><span class="th">對應主題：{D["theme"]}</span><span class="i">{D["idea"]}</span></div>'
    rows+=f'<div class="c sq"><img src="file://{OUT}/{i}_icon512.png"></div><div class="c i110"><img src="file://{OUT}/{i}_ig110.png" width="110" height="110"></div><div class="c i40"><img src="file://{OUT}/{i}_ig40.png" width="40" height="40"></div><div class="c w"><img src="file://{OUT}/{i}_horizontal.png"></div></div>'
html=f"""<html><head><meta charset="utf-8"><style>{css}</style></head><body><h1>哩股哩股 LIGU LOGO 第十輪：12 個貼主題的概念（J01–J12）</h1>
<div class="sub">全部對應產品主題：族群資金輪動、ETF 存股、台股 K 線、產業鏈族群、盤後 3 分鐘看懂。配色＝陽光糖果（底 #FFF7E8／墨藍 #1F2A44／橘／藍／紫／青；紅綠只用於漲跌）。方形、IG 110px、40px 皆實際像素。</div>
<div class="hd"><div class="c lab">概念與對應主題</div><div class="c sq">方形圖示</div><div class="c i110">IG 110px</div><div class="c i40">40px</div><div class="c w">橫式 LOGO</div></div>{rows}</body></html>"""
open(os.path.join(os.path.dirname(__file__),'_ov.html'),'w').write(html)
with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path=glob.glob("/opt/pw-browsers/chromium_headless_shell-*/*/chrome-headless-shell")[0],args=['--allow-file-access-from-files'])
    pg=b.new_page(viewport={'width':1700,'height':900}); pg.goto('file://'+os.path.join(os.path.dirname(__file__),'_ov.html')); pg.wait_for_timeout(600)
    pg.screenshot(path=os.path.join(OUT,'overview.png'),full_page=True); b.close()
