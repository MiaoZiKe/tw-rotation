import sys, glob, itertools
sys.path.insert(0,'/home/user/tw-rotation/docs/brand/logo_1102c/src')
from marks_c import VARS, render
from playwright.sync_api import sync_playwright
OUT='/home/user/tw-rotation/docs/brand/logo_1102c'; FD='/home/user/tw-rotation/docs/brand/logo_1102b/fonts'
CORAL='#FF5B4A';YEL='#FFC83D';INK='#1F2A44';CREAM='#FFF7E8';BLUE='#2B6BF3'
PAL={'brand':(CORAL,{'main':'#fff','acc':YEL}),'cream':(CREAM,{'main':INK,'acc':CORAL})}
FIT={'A0':60,'B1':60,'B2':60,'B3':58,'C1':62,'C2':62,'C3':60,'D1':64,'D2':56}
cnt=itertools.count()
def mk(v): return {k:f for k,_,f in VARS}[v]
def tile(v,w,size,idn=''):
    bg,p=PAL[w]; return f'<svg {idn} xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 100 100"><rect width="100" height="100" rx="22.5" fill="{bg}"/>{render(mk(v)(p),FIT[v])}</svg>'
def circle(v,w,size,idn=''):
    bg,p=PAL[w]; i=next(cnt)
    return (f'<svg {idn} xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 100 100"><clipPath id="c{i}"><circle cx="50" cy="50" r="50"/></clipPath>'
            f'<g clip-path="url(#c{i})"><rect width="100" height="100" fill="{bg}"/>{render(mk(v)(p),FIT[v]*0.9)}</g></svg>')
CSS=f'''@font-face{{font-family:"NSTC";font-weight:500;src:url("file://{FD}/noto-sans-tc-chinese-traditional-500-normal.woff2")}}
@font-face{{font-family:"NSTC";font-weight:700;src:url("file://{FD}/noto-sans-tc-chinese-traditional-700-normal.woff2")}}
body{{margin:0;font-family:"Inter","NSTC",sans-serif;color:{INK}}} .cjk{{font-family:"Inter","NSTC";font-weight:700}} .lat{{font-family:"Inter Display","Inter";font-weight:600}}'''
def horizontal(v,h=64,idn=''):
    return f'''<div {idn} style="display:inline-flex;align-items:center;gap:{h*0.26:.0f}px;padding:{h*0.3:.0f}px {h*0.4:.0f}px;background:#fff">{tile(v,'brand',h)}<div style="line-height:1"><div class="cjk" style="font-size:{h*0.5:.0f}px;letter-spacing:.06em">哩股哩股</div><div class="lat" style="font-size:{h*0.15:.1f}px;letter-spacing:.42em;color:#6b7080;margin-top:{h*0.12:.0f}px;padding-left:.2em">LIGULIGU</div></div></div>'''
def threads(v):
    return f'''<div style="box-sizing:border-box;width:100%;background:#fff;border:1px solid #e6e6e6;border-radius:14px;padding:16px;color:{INK}">
<div style="display:flex;justify-content:space-between;align-items:flex-start"><div><div class="cjk" style="font-size:20px">哩股哩股</div><div style="font-size:14px;color:#8d9198;margin-top:3px">liguligu0818</div></div>{circle(v,'brand',72)}</div>
<div style="font-size:14px;line-height:1.55;margin-top:8px;font-family:'Inter','NSTC';font-weight:500">每天盤後 3 分鐘，看懂錢往哪個族群跑<br>ETF 存股・資金輪動</div>
<div style="margin-top:10px;border:1px solid #e6e6e6;border-radius:9px;text-align:center;padding:6px 0;font-size:14px;font-weight:700;font-family:'Inter','NSTC'">追蹤</div></div>'''
IDEA={'A0':'基準：L 腳上揚成楔形，黃點是 i 的點／資金落點。Andy 已預留。','B1':'L 的腳換成被抽離的圓餅四分之一：豎筆＋黃色圓餅塊，一眼是「輪動」。','B2':'維持原 Li，黃點換成一小塊圓餅：最小改動、保留原本辨識度。','B3':'圓餅被切掉一角形成 L，缺掉的那塊飛出去（黃）：圓餅與 L 合為一體。',
 'C1':'L 的腳上揚成最高的 K 棒，棒頂影線＝i 的點：Li 與 K 線同一個符號。','C2':'豎筆旁接兩根漸高的圓角 K 棒，最高黃棒帶影線：由 L 長出上升的行情。','C3':'黃點接上影線，變成立在楔形上的 K 棒頂端：改動最小的 K 棒版。',
 'D1':'名稱重複的節奏：兩顆 Li 逐步上升，各自一顆點（Li Li）。','D2':'兩個 L 旋轉 180° 互扣成風車，縫隙一致：LIGU LIGU 的對稱＋輪動。'}
def card(v,name):
    return f'''<section style="box-sizing:border-box;width:640px;background:#fff;border-radius:18px;padding:20px 22px 22px;box-shadow:0 1px 3px rgba(0,0,0,.08)">
<b style="font-size:21px">{name}</b><p style="font-size:13.5px;line-height:1.55;color:#555b6b;margin:5px 0 14px;min-height:42px">{IDEA[v]}</p>
<div style="display:flex;gap:12px;align-items:flex-end">{tile(v,'brand',120)}{tile(v,'cream',120)}{circle(v,'brand',110)}{circle(v,'brand',40)}{circle(v,'cream',40)}</div>
<div style="font-size:12px;color:#888;margin:6px 0 12px">品牌色底／奶油底　IG 圓形 110px、40px（品牌色、奶油）實際像素</div>
<div style="border:1px solid #eee;border-radius:12px;overflow:hidden;display:inline-block">{horizontal(v,64)}</div>
<div style="margin-top:12px;max-width:420px">{threads(v)}</div></section>'''
def page():
    cards=''.join(f'<div>{card(v,n)}</div>' for v,n,_ in VARS)
    strip=''.join(f'<div style="display:flex;gap:8px;align-items:center;padding:10px;background:#EEF0F4;border-radius:12px"><span class="lat" style="font-size:12px;width:22px">{v}</span>{circle(v,"brand",110)}{circle(v,"brand",40)}</div>' for v,_,_ in VARS)
    return f'''<html><head><meta charset="utf-8"><style>{CSS}</style></head><body style="background:#E8EBF1;padding:30px 36px;width:2080px;box-sizing:border-box">
<h1 style="margin:0;font-size:30px">哩股哩股 LOGO 第三輪：A 基準＋A+B／A+C／雙 L 共 9 款（2026-11-02 美編）</h1>
<p style="margin:6px 0 20px;font-size:14px;color:#555b6b">沿用 A 的珊瑚紅＋黃點；奶油底版用「陽光糖果」底 #FFF7E8、墨藍 #1F2A44。符號為座標格＋統一圓角的向量；字用 Noto Sans TC（SIL OFL）＋Inter Display。</p>
<div style="display:grid;grid-template-columns:repeat(3,640px);gap:22px">{cards}</div>
<div style="margin-top:22px;background:#fff;border-radius:18px;padding:18px 22px"><b style="font-size:20px">九款 110px／40px 並排（實際像素，不放大）</b>
<div style="display:grid;grid-template-columns:repeat(5,auto);gap:12px;margin-top:12px;justify-content:start">{strip}</div></div></body></html>'''
exe=glob.glob("/opt/pw-browsers/chromium_headless_shell-1243/*/chrome-headless-shell")[0]
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=exe); pg=b.new_page(viewport={'width':2080,'height':900})
    pg.set_content(page()); pg.wait_for_timeout(1500)
    pg.screenshot(path=f'{OUT}/overview.png',full_page=True)
    for v,n,_ in VARS:
        for w in ('brand','cream'):
            open(f'{OUT}/{v}_icon_{w}.svg','w').write(tile(v,w,1024))
    # 每款單獨檔：用獨立頁面（小）
    pg2=b.new_page(viewport={'width':1100,'height':400})
    for v,n,_ in VARS:
        for w in ('brand','cream'):
            pg2.set_viewport_size({'width':1024,'height':1024}); pg2.set_content(f'<style>body{{margin:0}}svg{{display:block}}</style>{tile(v,w,1024)}')
            pg2.screenshot(path=f'{OUT}/{v}_icon_{w}.png',omit_background=True)
            for s in (110,40):
                pg2.set_viewport_size({'width':s,'height':s}); pg2.set_content(f'<style>body{{margin:0}}svg{{display:block}}</style>{circle(v,w,s)}')
                pg2.screenshot(path=f'{OUT}/{v}_ig_{w}_{s}.png',omit_background=True)
        pg2.set_viewport_size({'width':900,'height':300}); pg2.set_content(f'<html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{horizontal(v,120)}</body></html>'); pg2.wait_for_timeout(300)
        pg2.locator('body > div').screenshot(path=f'{OUT}/{v}_horizontal.png')
    b.close()
