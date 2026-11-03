# 第二輪（依審查 review.md）：2 整合／錯高、7 粗勾、8 改 2x2；封面標誌左緣對齊 64px、高 44px
import json, os, urllib.parse, subprocess
import build
from build import S
OUT=build.OUT+'/round2'; os.makedirs(OUT+'/html',exist_ok=True)
FONT="'Noto Sans CJK TC','Noto Sans TC','WenQuanYi Zen Hei',sans-serif"
def chk(x,y,s,w,c): return f'<path d="M{x} {y+0.1*s}L{x+0.3*s} {y+0.4*s}L{x+0.85*s} {y-0.35*s}" stroke="{c}" stroke-width="{w}" {S}/>'
def crs(x,y,s,w,c): return f'<path d="M{x-s/2} {y-s/2}L{x+s/2} {y+s/2}M{x+s/2} {y-s/2}L{x-s/2} {y+s/2}" stroke="{c}" stroke-width="{w}" {S}/>'
def r2a(p):  # 整合：一個外框、左綠右琥珀，符號粗大
    return ((f'<defs><clipPath id="c"><rect x="84" y="146" width="344" height="220" rx="48"/></clipPath></defs><g clip-path="url(#c)">'
      f'<rect x="84" y="146" width="172" height="220" fill="{p["g"]}"/><rect x="256" y="146" width="172" height="220" fill="{p["a"]}"/></g>'
      + chk(138,262,110,36,p['bg']) + crs(342,256,84,36,p['bg'])), (84,146,344,220))
def r2b(p):  # 錯高：叉塊較低半格，兩塊間縫小
    return ((f'<rect x="84" y="120" width="166" height="190" rx="36" fill="{p["g"]}"/><rect x="262" y="202" width="166" height="190" rx="36" fill="{p["a"]}"/>'
      + chk(130,222,100,36,p['bg']) + crs(345,297,80,36,p['bg'])), (84,120,344,272))
def r2c(p):  # 斜角：兩塊對角錯開，不並排成單選鈕
    return ((f'<rect x="84" y="108" width="190" height="190" rx="40" fill="{p["g"]}"/><rect x="238" y="214" width="190" height="190" rx="40" fill="{p["a"]}" stroke="{p["bg"]}" stroke-width="14"/>'
      + chk(128,208,110,38,p['bg']) + crs(333,309,86,38,p['bg'])), (84,108,344,296))
def r2_7(p):
    return ((f'<circle cx="224" cy="224" r="112" stroke="{p["fg"]}" stroke-width="36" fill="none"/>'
      f'<path d="M308 308L402 402" stroke="{p["a"]}" stroke-width="44" {S}/>'
      f'<path d="M162 228L206 272L286 172" stroke="{p["g"]}" stroke-width="44" {S}/>'), (96,96,316,316))
def grid(p,cells):
    s='';
    for (i,j),k in cells.items():
        x=112+i*158; y=112+j*158
        if k=='g': s+=f'<rect x="{x}" y="{y}" width="130" height="130" rx="28" fill="{p["g"]}"/>'
        elif k=='a': s+=f'<rect x="{x}" y="{y}" width="130" height="130" rx="28" fill="{p["a"]}"/>'
        else: s+=f'<rect x="{x+8}" y="{y+8}" width="114" height="114" rx="22" stroke="{p["dim"] if p is build.DARK else p["dim"]}" stroke-width="16" fill="none"/>'
    return s,(112,112,288,288)
def r2_8a(p): return grid(p,{(0,0):'g',(1,0):'g',(0,1):'e',(1,1):'a'})
def r2_8b(p): return grid(p,{(0,0):'g',(1,0):'g',(0,1):'g',(1,1):'a'})
L=[('r2a','整合雙色塊','一個外框、左綠右琥珀：成功與翻車同屬一份紀錄，勾叉都加粗放大。',r2a),
   ('r2b','錯高雙塊','勾塊在上、叉塊低半格：像天平兩端，成功與翻車並列、不像單選鈕。',r2b),
   ('r2c','斜角雙塊','綠勾塊與琥珀叉塊沿對角錯開：一路做下去，成功與翻車交替出現。',r2c),
   ('r27','放大驗證（粗勾）','放大鏡裡一個粗綠勾：可驗證，你能自己再做一次。',r2_7),
   ('r28a','2×2 實驗（二綠一空一琥珀）','四格＝四次實測：綠成功、空框沒做出來、琥珀翻車。',r2_8a),
   ('r28b','2×2 實驗（三綠一琥珀）','四次實測三次成功、一次翻車：連翻車那格都放進版面。',r2_8b)]
def svg(fn,p,bg=True,vb=None):
    inner,bb=fn(p); v=vb or '0 0 512 512'
    r=f'<rect x="-999" y="-999" width="3000" height="3000" fill="{p["bg"]}"/>' if bg else ''
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{v}" width="512" height="512">{r}{inner}</svg>'
uri=lambda s:'data:image/svg+xml;utf8,'+urllib.parse.quote(s)
H=OUT+'/html'; jobs=[]; cells=''
for k,n,m,fn in L:
    d=f'{OUT}/{k}_{n}'; os.makedirs(d,exist_ok=True)
    for v,p in (('dark',build.DARK),('light',build.LIGHT)):
        s=svg(fn,p); open(f'{d}/icon_{v}.svg','w').write(s)
        open(f'{H}/{k}_{v}.html','w').write(f'<body style="margin:0"><img src="{uri(s)}" width=1024 height=1024>')
        jobs.append(dict(html=f'{k}_{v}.html',out=f'{d}/icon_{v}_1024.png',w=1024,h=1024))
    # 封面：標誌緊貼符號外框，左緣 64、高 44
    bb=fn(build.DARK)[1]; lw=round(44*bb[2]/bb[3]); lg=svg(fn,build.DARK,bg=False,vb=f'{bb[0]} {bb[1]} {bb[2]} {bb[3]}')
    sx=64+lw+24
    cov=f'''<html><body style="margin:0"><style>*{{box-sizing:border-box}}.p{{position:relative;width:1080px;height:1350px;background:#0F1722;color:#F3F7FB;font-family:{FONT};overflow:hidden}}.e{{position:absolute}}</style><div class="p">
<img data-el="logo" class="e" style="left:64px;top:76px;width:{lw}px;height:44px" src="{uri(lg)}">
<div data-el="series" class="e" style="left:{sx}px;top:76px;font-size:30px;color:#6FD8A0;line-height:44px;white-space:nowrap">AI 實測 第 07 期</div>
<div data-el="date" class="e" style="right:64px;top:76px;font-size:28px;color:#B4C2D3;line-height:44px">2026/11/03</div>
<div data-el="title" class="e" style="left:64px;top:190px;width:952px;font-size:132px;font-weight:900;line-height:1.12">我用 <span style="color:#6FD8A0">AI</span><br>一天寫完<br>一個月的報表</div>
<div data-el="sub" class="e" style="left:64px;top:674px;font-size:44px;color:#B4C2D3;line-height:60px;white-space:nowrap">實測 3 款工具，第 2 款最意外</div>
<div data-el="pills" class="e" style="left:64px;top:766px;font-size:32px;line-height:64px;white-space:nowrap;display:flex;gap:16px">{''.join(f'<span style="border:2px solid #2A3A52;background:#182334;border-radius:32px;padding:0 24px">{t}</span>' for t in ['省 6 小時','免費可用','附測試條件'])}</div>
<div data-el="card" class="e" style="left:64px;top:898px;width:952px;height:300px;background:#182334;border:3px solid #2A3A52;border-radius:28px"></div>
<div data-el="foot" class="e" style="left:64px;top:1230px;width:952px;border-top:2px solid #2A3A52;padding-top:12px;font-size:28px;color:#B4C2D3;display:flex;justify-content:space-between"><span><b style="color:#F3F7FB">無業配</b>｜截圖已遮個資</span><span>圖文含 AI 協助</span></div></div></body></html>'''
    open(f'{H}/{k}_cover.html','w').write(cov); jobs.append(dict(html=f'{k}_cover.html',out=f'{d}/cover_A.png',w=1080,h=1350,check=1))
    D,Li=uri(svg(fn,build.DARK)),uri(svg(fn,build.LIGHT))
    cells+=f'''<div class="c"><div class="row"><img src="{D}" width=260 height=260 style="border-radius:40px"><img src="{Li}" width=260 height=260 style="border-radius:40px;border:1px solid #cfd8e3"></div>
<div class="row2"><img class="ci" src="{D}"><img class="ci" src="{Li}"><img class="ci s" src="{D}"><img class="ci s" src="{Li}"><span class="px">110px／40px 實際像素</span></div>
<div class="n">{k[1:]}　{n}</div><div class="m">{m}</div></div>'''
page=f'''<html><body style="margin:0;background:#E9EEF4;font-family:{FONT}"><style>.g{{display:grid;grid-template-columns:repeat(3,640px);gap:28px;padding:40px}}.c{{background:#fff;border-radius:24px;padding:24px;height:640px;box-sizing:border-box}}
.row{{display:flex;gap:24px}}.row2{{display:flex;gap:16px;align-items:center;margin:20px 0 14px}}.ci{{width:110px;height:110px;border-radius:50%}}.ci.s{{width:40px;height:40px}}.px{{font-size:18px;color:#5b6b7e}}.n{{font-size:32px;font-weight:800;color:#0F1722}}.m{{font-size:24px;color:#34465c;line-height:1.5;margin-top:6px}}h1{{margin:40px 40px 0;font-size:42px;color:#0F1722}}</style>
<h1>頻道③ LOGO 第二輪（依審查修正）：深淺底、IG 圓形 110／40px 實際像素</h1><div class="g">{cells}</div></body></html>'''
open(H+'/overview_round2.html','w').write(page); jobs.append(dict(html='overview_round2.html',out=build.OUT+'/overview_round2.png',w=2100,h=1500,full=1))
json.dump(jobs,open(H+'/jobs.json','w'))
