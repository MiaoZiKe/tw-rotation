import os, glob, sys
sys.path.insert(0, os.path.dirname(__file__))
from build import NAMES
from playwright.sync_api import sync_playwright
OUT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
IDEA={
'11':'L 與 G 兩條圓角線條上下交織（G 在下方壓過 L、L 在上方壓過 G），像資金與標的互相咬合。',
'12':'對稱八角雙金線框＋扇形光芒＋四層階梯塔（同時是上升的長條），深藍底配細金線。',
'13':'5×5 點陣：圓點由小到大排成 L，腳尾接橘色漸大的點與落點圓環，像 LED 看板的上升走勢。',
'14':'四塊水彩暈染（黃、橘、藍、紫）與墨點飛濺，上面疊一個乾淨的墨藍「哩」，字標維持俐落。',
'15':'紅底燈箱招牌：黃色粗體「哩股」＋墨藍描邊與偏移陰影，外圈一圈跑馬燈泡，下方小橫牌 LIGU。',
'16':'千禧鉻金屬：有地平線反光的鉻質 L ＋上揚箭頭，紫藍底配四角閃光。',
'17':'粗黑框、硬陰影、高彩：三根上升長條＋圓形箭頭貼紙，黃底。字標放在粗框牌上。',
'18':'「哩」字向右下擠出厚度（橘色側面漸深），奶黃字面，藍底，立體但不變形字型。',
'19':'橘色星球與兩條傾斜軌道，藍、青、黃、紫四顆衛星繞行，像資金在族群間輪動。',
'20':'海棠花磚意象：四大瓣橘＋四小瓣青、四角同心圓花，奶油磚面配青底，橫式帶紅磚疊砌淡紋。',
}
FONT=f"""@font-face{{font-family:T;font-weight:900;src:url('file://{OUT}/fonts/noto-sans-tc-chinese-traditional-900-normal.woff2')}}
@font-face{{font-family:T;font-weight:700;src:url('file://{OUT}/fonts/noto-sans-tc-chinese-traditional-700-normal.woff2')}}
@font-face{{font-family:T;font-weight:500;src:url('file://{OUT}/fonts/noto-sans-tc-chinese-traditional-500-normal.woff2')}}
*{{box-sizing:border-box}}body{{margin:0;font-family:T,Inter,sans-serif;color:#1F2A44;background:#fff}}"""
def img(f,w=None,h=None,extra=''):
    return f'<img src="file://{OUT}/{f}" {"width=%d"%w if w else ""} {"height=%d"%h if h else ""} style="display:block;{extra}">'
rows=''
for n,nm in NAMES.items():
    d='G'+n
    rows+=f'''<div class="r"><div class="lab"><b>{d}　{nm}</b><span>{IDEA[n]}</span></div>
    <div class="c">{img(d+"_icon512.png",128)}</div><div class="c">{img(d+"_ig110.png")}</div><div class="c">{img(d+"_ig40.png")}</div>
    <div class="hz">{img(d+"_horizontal.png",330,110,"border-radius:8px;border:1px solid #e3e3e3")}</div></div>'''
html=f'''<html><style>{FONT}
.h{{padding:26px 34px 8px}} h1{{margin:0;font-size:30px;font-weight:900}} .h p{{margin:6px 0 0;color:#666;font-size:14px}}
.th{{display:flex;padding:14px 34px 6px;border-bottom:2px solid #1F2A44;font-size:13px;font-weight:700;color:#555}}
.th div,.r div{{flex:none}} .lab{{width:380px;padding-right:24px}} .c{{width:150px;display:flex;align-items:center;justify-content:center}} .hz{{width:350px;padding-left:10px}}
.r{{display:flex;padding:14px 34px;border-bottom:1px solid #e6e6e6;align-items:center;min-height:164px}}
.lab b{{display:block;font-size:20px;font-weight:900}} .lab span{{display:block;font-size:14px;margin-top:6px;line-height:1.55;color:#333}}
</style><body><div class="h"><h1>哩股哩股 LOGO 第七輪：10 種新風格（G11～G20，每種 1 套主配色）</h1><p>每列由左至右：方形圖示（縮到 128px 顯示）、IG 圓形 110px、IG 圓形 40px、橫式 LOGO（縮圖）。110／40 皆為實際像素、白底、未放大。</p></div>
<div class="th"><div class="lab">風格與理念</div><div class="c">方形</div><div class="c">IG 110</div><div class="c">IG 40</div><div class="hz">橫式</div></div>{rows}</body></html>'''
open('/tmp/claude-0/w/ov.html','w').write(html)
with sync_playwright() as pw:
    b=pw.chromium.launch(executable_path=glob.glob("/opt/pw-browsers/chromium_headless_shell-1243/*/chrome-headless-shell")[0],args=['--allow-file-access-from-files'])
    pg=b.new_page(viewport={'width':1400,'height':800}); pg.goto('file:///tmp/claude-0/w/ov.html'); pg.wait_for_timeout(800)
    pg.screenshot(path=os.path.join(OUT,'overview.png'),full_page=True); b.close()
