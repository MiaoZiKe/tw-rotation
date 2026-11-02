import sys, os, itertools, glob
sys.path.insert(0,'/home/user/tw-rotation/docs/brand/logo_1102b/src')
import marks
from marks import MARKS, render
from playwright.sync_api import sync_playwright
OUT='/home/user/tw-rotation/docs/brand/logo_1102b'
CORAL='#FF5B4A';YEL='#FFC83D';MINT='#19C6A7';SKY='#3FA9FF';CREAM='#FFF6E6';INK='#232733';WHITE='#FFFFFF';PALE='#BFE3FF'
marks.WEIGHT=500
CANDS=[
 dict(id='a_li',k='A',name='Li 上揚',idea='「哩」的拼音 Li：L 的腳往右上揚成楔形（上升），上方一顆圓點是 i 的點、也是資金落點。',
      brand=(CORAL,{'main':WHITE,'accent':YEL}),cream=(CREAM,{'main':INK,'accent':CORAL}),fit=60,cfit=56),
 dict(id='b_pie',k='B',name='輪動圓餅',idea='圓餅四等分，右上一塊被抽離——資金從各族群輪到下一個族群；四色明亮、紅色那塊就是「現在錢在哪」。',
      brand=(SKY,{'c1':WHITE,'c2':YEL,'c3':PALE,'accent':CORAL}),cream=(CREAM,{'c1':SKY,'c2':YEL,'c3':MINT,'accent':CORAL}),fit=62,cfit=56),
 dict(id='c_kbar',k='C',name='K 棒上升',idea='三根圓角 K 棒由矮到高，最高的紅棒（台灣紅漲）帶上影線；全部用同一組棒寬與間距建構，是最直白的「看盤」符號。',
      brand=(YEL,{'c1':WHITE,'c2':INK,'accent':CORAL}),cream=(CREAM,{'c1':MINT,'c2':SKY,'accent':CORAL}),fit=66,cfit=58),
 dict(id='d_li_type',k='D',name='「哩」字標',idea='專業企業感的穩重款：Noto Sans TC Medium 的「哩」原字（不加粗、不變形），只把口字旁染成珊瑚紅作為唯一記憶點。',
      brand=(INK,{'main':WHITE,'accent':CORAL}),cream=(CREAM,{'main':INK,'accent':CORAL}),fit=64,cfit=56),
]
_c=itertools.count()
def tile(c,which,size,fit=None):
    bg,p=c[which]; fit=fit or c['fit']
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 100 100"><rect width="100" height="100" rx="22.5" fill="{bg}"/>{render(MARKS[c["k"]](p),fit)}</svg>'
def circle(c,which,size):
    bg,p=c[which]; i=next(_c)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 100 100"><clipPath id="cc{i}"><circle cx="50" cy="50" r="50"/></clipPath>'
            f'<g clip-path="url(#cc{i})"><rect width="100" height="100" fill="{bg}"/>{render(MARKS[c["k"]](p),c["cfit"])}</g></svg>')
FONTCSS=f'''
@font-face{{font-family:"NSTC";font-weight:500;src:url("file://{OUT}/fonts/noto-sans-tc-chinese-traditional-500-normal.woff2")}}
@font-face{{font-family:"NSTC";font-weight:700;src:url("file://{OUT}/fonts/noto-sans-tc-chinese-traditional-700-normal.woff2")}}
@font-face{{font-family:"NSTC";font-weight:900;src:url("file://{OUT}/fonts/noto-sans-tc-chinese-traditional-900-normal.woff2")}}
body{{margin:0;font-family:"Inter","NSTC",sans-serif;color:{INK}}}
.cjk{{font-family:"Inter","NSTC";font-weight:700}} .lat{{font-family:"Inter Display","Inter";font-weight:600}}
'''
def horizontal(c,h=96,bg=WHITE):
    ic=tile(c,'brand',h)
    return f'''<div style="display:inline-flex;align-items:center;gap:{h*0.26:.0f}px;padding:{h*0.3:.0f}px {h*0.4:.0f}px;background:{bg}">
 {ic}<div style="line-height:1"><div class="cjk" style="font-size:{h*0.5:.0f}px;letter-spacing:.06em">哩股哩股</div>
 <div class="lat" style="font-size:{h*0.15:.1f}px;letter-spacing:.42em;color:#6b7080;margin-top:{h*0.12:.0f}px;padding-left:.2em">LIGULIGU</div></div></div>'''
def threads(c,dark=False):
    bgc,fg,sub,line=('#101010','#F3F5F7','#8d9198','#2a2a2a') if dark else ('#fff',INK,'#8d9198','#e6e6e6')
    return f'''<div style="width:392px;background:{bgc};border:1px solid {line};border-radius:14px;padding:18px 18px 16px;color:{fg}">
 <div style="display:flex;justify-content:space-between;align-items:flex-start">
  <div><div style="font-size:21px;font-weight:700;font-family:NSTC,Inter">哩股哩股</div><div style="font-size:14px;color:{sub};margin-top:3px;font-family:Inter">liguligu0818</div></div>
  {circle(c,'brand',76)}</div>
 <div style="font-size:14px;line-height:1.55;margin-top:10px;font-family:NSTC,Inter;font-weight:500">每天盤後 3 分鐘，看懂錢往哪個族群跑<br>ETF 存股・資金輪動</div>
 <div style="margin-top:12px;border:1px solid {line};border-radius:9px;text-align:center;padding:7px 0;font-size:14px;font-weight:700;font-family:NSTC,Inter">追蹤</div></div>'''

def card(c):
    return f'''<section style="box-sizing:border-box;width:456px;background:#fff;border-radius:18px;padding:22px 22px 24px;box-shadow:0 1px 3px rgba(0,0,0,.08)">
 <div style="display:flex;align-items:baseline;gap:10px"><b style="font-size:22px;font-family:NSTC,Inter">{c['id'][0].upper()}　{c['name']}</b></div>
 <p style="font-size:13.5px;line-height:1.6;color:#555b6b;margin:6px 0 16px;min-height:66px">{c['idea']}</p>
 <div style="display:flex;gap:14px;align-items:flex-end">{tile(c,'brand',150)}{tile(c,'cream',150)}
  <div style="display:flex;flex-direction:column;gap:8px;align-items:flex-start"><div style="display:flex;gap:10px;align-items:flex-end">{circle(c,'brand',110)}{circle(c,'brand',40)}</div>
  <div style="font-size:12px;color:#888">IG 圓形 110／40px</div></div></div>
 <div style="margin-top:16px;border:1px solid #eee;border-radius:12px;overflow:hidden">{horizontal(c,76)}</div>
 <div style="margin-top:14px">{threads(c)}</div>
 <div style="margin-top:12px">{threads(c,True)}</div>
</section>'''

def overview():
    strip=''
    for c in CANDS:
        strip+=f'<div style="display:flex;gap:10px;align-items:center;padding:14px;background:#EEF0F4;border-radius:12px">{circle(c,"brand",110)}{circle(c,"brand",40)}{circle(c,"cream",110)}{circle(c,"cream",40)}</div>'
    # 手機桌面模擬（60px 圖示）
    gray=['#C9CED8','#B8BFCC','#D6DAE2','#AEB6C4','#C2C8D4']
    def home(c):
        cells=''
        g=itertools.cycle(gray)
        items=[None,None,'me',None]
        for it in items: cells+=f'<div style="width:60px;height:60px;border-radius:14px;background:{next(g)}"></div>' if it is None else f'<div style="text-align:center">{tile(c,"brand",60)}<div class="cjk" style="font-size:11px;margin-top:4px;color:#fff">哩股哩股</div></div>'
        return f'<div style="display:flex;gap:16px;align-items:flex-start;padding:16px;background:linear-gradient(135deg,#7aa6d6,#c7b3e3);border-radius:16px">{cells}</div>'
    homes=''.join(home(c) for c in CANDS)
    return f'''<html><head><meta charset="utf-8"><style>{FONTCSS}</style></head><body style="background:#E8EBF1;padding:32px 36px;width:2000px;box-sizing:border-box">
 <h1 style="margin:0;font-size:30px;font-family:NSTC,Inter">哩股哩股 LOGO 第二輪：四個方向（2026-11-02 美編）</h1>
 <p style="margin:6px 0 22px;font-size:14px;color:#555b6b">不用吉祥物。符號為座標格＋一致圓角的向量（非 AI 描圖，原因見 ai_review.md）；字用真字型：Noto Sans TC（SIL OFL，可商用）＋Inter Display。A／B／C 走明亮親切，D 是穩重企業款。</p>
 <div style="display:flex;gap:22px;align-items:flex-start">{''.join(card(c) for c in CANDS)}</div>
 <div style="margin-top:22px;background:#fff;border-radius:18px;padding:20px 22px">
  <b style="font-size:20px;font-family:NSTC,Inter">四款並排：品牌色底／奶油底，110px 與 40px（實際像素，不放大）</b>
  <div style="display:flex;gap:22px;margin-top:14px">{strip}</div>
  <b style="font-size:20px;font-family:NSTC,Inter;display:block;margin-top:20px">手機桌面圖示 60px（旁邊是灰色雜牌圖示做對照）</b>
  <div style="display:flex;gap:22px;margin-top:14px">{homes}</div></div></body></html>'''

def page_png(html,path,w,h,omit=False,dsf=1):
    pg.set_viewport_size({'width':w,'height':h})
    pg.set_content(html); pg.wait_for_timeout(300)
    pg.screenshot(path=path,omit_background=omit,full_page=True)
exe=glob.glob("/opt/pw-browsers/chromium_headless_shell-1243/*/chrome-headless-shell")[0]
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=exe); pg=b.new_page(viewport={'width':2000,'height':900})
    for c in CANDS:
        for w in ('brand','cream'):
            open(f"{OUT}/{c['id']}_icon_{w}.svg",'w').write(tile(c,w,1024))
            page_png(f'<style>body{{margin:0;background:transparent}}</style>{tile(c,w,1024)}',f"{OUT}/{c['id']}_icon_{w}.png",1024,1024,omit=True)
            for s in (110,40,400):
                page_png(f'<style>body{{margin:0;background:transparent}}svg{{display:block}}</style>{circle(c,w,s)}',f"{OUT}/{c['id']}_ig_{w}_{s}.png",s,s,omit=True)
        pg.set_viewport_size({'width':1000,'height':400}); pg.set_content(f'<html><head><meta charset="utf-8"><style>{FONTCSS}</style></head><body>{horizontal(c,120)}</body></html>'); pg.wait_for_timeout(300)
        pg.locator('body > div').screenshot(path=f"{OUT}/{c['id']}_horizontal.png")
    page_png(overview(),f"{OUT}/overview.png",2000,1000)
    b.close()
