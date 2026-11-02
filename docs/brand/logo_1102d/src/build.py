import sys,os,glob
sys.path.insert(0,'/home/user/tw-rotation/docs/brand/logo_1102d/src')
import gen
from gen import *
from playwright.sync_api import sync_playwright
EXE=glob.glob("/opt/pw-browsers/chromium_headless_shell-1243/*/chrome-headless-shell")[0]
FONTCSS=f'''@font-face{{font-family:"NSTC";font-weight:500;src:url("file://{FONTS}/noto-sans-tc-chinese-traditional-500-normal.woff2")}}
@font-face{{font-family:"NSTC";font-weight:700;src:url("file://{FONTS}/noto-sans-tc-chinese-traditional-700-normal.woff2")}}
@font-face{{font-family:"NSTC";font-weight:900;src:url("file://{FONTS}/noto-sans-tc-chinese-traditional-900-normal.woff2")}}
body{{margin:0;font-family:"Inter","NSTC",sans-serif;color:#1F2A44;background:transparent}}'''
REC={'c1':'p1','c2':'p3','c3':'p4','c4':'p2','c5':'p1','c6':'p3'}
S=OUT+'/svg/'
TMP=OUT+'/src/_tmp.html'
def sq(c,p,m,sz): return f'<img src="file://{S}{c}_{p}_{m}.svg" width="{sz}" height="{sz}" style="display:block">'
def ig(c,p,m,sz): return f'<div style="width:{sz}px;height:{sz}px;border-radius:50%;overflow:hidden">{sq(c,p,m,sz)}</div>'
def horizontal(c,p,h=96):
    L=PALETTES[p]['light']; n,_,_=CONCEPTS[c]
    return f'''<div style="display:inline-flex;align-items:center;gap:{h*.3:.0f}px;padding:{h*.34:.0f}px {h*.46:.0f}px;background:#fff;border:1px solid #E7EAF1;border-radius:20px">
 {sq(c,p,'brand',h)}<div style="line-height:1"><div style="font-family:NSTC;font-weight:900;font-size:{h*.5:.0f}px;letter-spacing:.04em;color:{L['f']}">哩股<span style="color:{L['a']}">哩股</span></div>
 <div style="font-family:'Inter Display',Inter;font-weight:800;font-size:{h*.17:.1f}px;letter-spacing:.34em;margin-top:{h*.14:.0f}px;color:{L['f']};opacity:.85">LIGU <span style="color:{L['a']}">LIGU</span></div></div></div>'''
def profile(c,p):
    return f'''<div style="box-sizing:border-box;width:400px;background:#fff;border:1px solid #E6E6E6;border-radius:14px;padding:18px">
 <div style="display:flex;justify-content:space-between"><div><div style="font-size:21px;font-weight:700;font-family:NSTC">哩股哩股</div><div style="font-size:14px;color:#8d9198;margin-top:3px">liguligu0818</div></div>{ig(c,p,'brand',76)}</div>
 <div style="font-size:14px;line-height:1.55;margin-top:10px;font-family:NSTC;font-weight:500">每天盤後 3 分鐘，看懂錢往哪個族群跑<br>ETF 存股・資金輪動</div>
 <div style="margin-top:12px;border:1px solid #E6E6E6;border-radius:9px;text-align:center;padding:7px 0;font-size:14px;font-weight:700;font-family:NSTC">追蹤</div></div>'''
def page(body,bg='transparent'): return f'<html><head><style>{FONTCSS}</style></head><body style="background:{bg}"><div id="x" style="display:inline-block">{body}</div></body></html>'
def build():
    gen_all()
    with sync_playwright() as pw:
        b=pw.chromium.launch(executable_path=EXE); pg=b.new_page(viewport={'width':900,'height':900})
        def shot(body,path,bg='transparent'):
            open(TMP,'w').write(page(body,bg)); pg.goto('file://'+TMP); pg.wait_for_timeout(150)
            pg.locator('#x').screenshot(path=path,omit_background=True)
        for c in CONCEPTS:
            for p in PALETTES:
                for m in ('brand','light'):
                    base=f'{OUT}/{c}_{p}_{m}'
                    shot(sq(c,p,m,512),base+'_icon512.png')
                    shot(ig(c,p,m,110),base+'_ig110.png'); shot(ig(c,p,m,40),base+'_ig40.png')
            shot(horizontal(c,REC[c]),f'{OUT}/{c}_horizontal.png','#F3F5FA')
            shot(profile(c,REC[c]),f'{OUT}/{c}_profile.png','#F3F5FA')
        b.close()
def gen_all():
    os.makedirs(S,exist_ok=True)
    for c in CONCEPTS:
        for p in PALETTES:
            for m in ('brand','light'): open(f'{S}{c}_{p}_{m}.svg','w').write(make(c,p,m))
def overview():
    cols=''.join(f'<div style="width:420px;font-weight:700;font-size:16px">{k.upper()}　{v["name"]}<div style="font-weight:500;font-size:12px;color:#6b7080;margin-top:3px">底 {v["brand"]["bg"][0]}→{v["brand"]["bg"][1]}　主 {v["brand"]["f"]}　輔 {v["brand"]["a"]}／{v["brand"]["b"]}</div></div>' for k,v in PALETTES.items())
    rows=''
    for c,(n,_,idea) in CONCEPTS.items():
        cells=''
        for p in PALETTES:
            cells+=f'<div style="width:420px;display:flex;gap:10px;align-items:flex-end">{sq(c,p,"brand",96)}{sq(c,p,"light",96)}{ig(c,p,"brand",110)}<div style="display:flex;flex-direction:column;gap:8px">{ig(c,p,"brand",40)}{ig(c,p,"light",40)}</div></div>'
        rows+=f'<div style="display:flex;gap:16px;align-items:center;padding:14px 0;border-top:1px solid #E3E7F0"><div style="width:190px"><b style="font-size:18px;font-family:NSTC">{c.upper()}　{n}</b><div style="font-size:12px;color:#6b7080;line-height:1.5;margin-top:4px;font-family:NSTC">{idea}</div></div>{cells}</div>'
    return f'<div style="width:1940px;padding:26px 30px;background:#fff;box-sizing:border-box;font-family:NSTC,Inter"><div style="font-size:26px;font-weight:900;margin-bottom:4px">哩股哩股 LOGO 第四輪：6 個新概念 × 4 套配色（24 組）</div><div style="font-size:13px;color:#6b7080;margin-bottom:14px">每組由左至右：品牌色底圖示、淺底圖示、IG 圓形 110px、IG 40px（品牌底／淺底）。110／40 皆為實際像素，未放大。</div><div style="display:flex;gap:16px;margin-bottom:8px"><div style="width:190px"></div>{cols}</div>{rows}</div>'
def detail():
    cards=''
    for c,(n,_,idea) in CONCEPTS.items():
        cards+=f'<section style="width:600px;background:#fff;border-radius:18px;padding:22px;box-sizing:border-box"><b style="font-size:21px;font-family:NSTC">{c.upper()}　{n}（推薦 {REC[c].upper()} {PALETTES[REC[c]]["name"]}）</b><p style="font-size:13px;color:#555b6b;line-height:1.6;margin:6px 0 14px;font-family:NSTC;min-height:42px">{idea}</p><div style="margin-bottom:14px">{horizontal(c,REC[c],84)}</div>{profile(c,REC[c])}</section>'
    return f'<div style="width:1900px;padding:28px;background:#E9EDF5;box-sizing:border-box;font-family:NSTC,Inter"><div style="font-size:26px;font-weight:900;margin-bottom:16px">哩股哩股 LOGO 第四輪：橫式字標＋Threads 個人頁（各概念推薦配色）</div><div style="display:grid;grid-template-columns:repeat(3,600px);gap:20px">{cards}</div></div>'
if __name__=='__main__':
    what=sys.argv[1]
    if what=='all': build()
    gen_all()
    with sync_playwright() as pw:
        b=pw.chromium.launch(executable_path=EXE); pg=b.new_page(viewport={'width':1940,'height':900})
        for nm,fn in (('overview',overview),('overview_detail',detail)):
            open(TMP,'w').write(page(fn(),'#fff')); pg.goto('file://'+TMP); pg.wait_for_timeout(500)
            pg.locator('#x').screenshot(path=f'{OUT}/{nm}.png')
        b.close()
