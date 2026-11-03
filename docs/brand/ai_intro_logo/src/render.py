import json, os
import build
OUT=build.OUT; meta=json.load(open(f'{OUT}/src/meta.json'))
FONT="'Noto Sans CJK TC','Noto Sans TC','WenQuanYi Zen Hei',sans-serif"
def uri(fn,p,bg=True):
    return 'data:image/svg+xml;utf8,'+__import__('urllib.parse').parse.quote(build.svg(fn,p,bg=bg))
fns={k:fn for k,n,m,fn in build.LOGOS}
def cell(x):
    fn=fns[x['k']]
    return f'''<div class="c"><div class="row"><img src="{uri(fn,build.DARK)}" width=300 height=300 style="border-radius:44px"><img src="{uri(fn,build.LIGHT)}" width=300 height=300 style="border-radius:44px;border:1px solid #cfd8e3"></div>
<div class="row2"><img class="ci" src="{uri(fn,build.DARK)}"><img class="ci" src="{uri(fn,build.LIGHT)}"><img class="ci s" src="{uri(fn,build.DARK)}"><span class="px">110px／40px 實際像素</span></div>
<div class="n">{x['k'][1]}　{x['n']}</div><div class="m">{x['m']}</div></div>'''
html=f'''<html><body style="margin:0;background:#E9EEF4;font-family:{FONT}"><style>
.g{{display:grid;grid-template-columns:repeat(4,660px);gap:28px;padding:40px}}.c{{background:#fff;border-radius:24px;padding:24px;height:660px;box-sizing:border-box}}
.row{{display:flex;gap:24px}}.row2{{display:flex;gap:16px;align-items:center;margin:20px 0 14px}}.ci{{width:110px;height:110px;border-radius:50%}}.ci.s{{width:40px;height:40px}}
.px{{font-size:18px;color:#5b6b7e}}.n{{font-size:34px;font-weight:800;color:#0F1722}}.m{{font-size:24px;color:#34465c;line-height:1.5;margin-top:6px}}
h1{{margin:40px 40px 0;font-size:44px;color:#0F1722}}</style><h1>頻道③ AI 介紹頻道 LOGO：八個方向（深底與淺底、IG 圓形大頭貼實際像素）</h1><div class="g">{''.join(cell(x) for x in meta)}</div></body></html>'''
cover=lambda x,name:f'''<html><body style="margin:0"><style>
*{{box-sizing:border-box}}.p{{position:relative;width:1080px;height:1350px;background:#0F1722;color:#F3F7FB;font-family:{FONT};overflow:hidden}}
.e{{position:absolute}}</style><div class="p">
<img data-el="logo" class="e" style="left:64px;top:54px;width:88px;height:88px" src="{uri(fns[x['k']],build.DARK,bg=False).replace('viewBox%3D%22','viewBox%3D%2280%2080%20352%20352%22%20data-x%3D%22')}">
<div data-el="series" class="e" style="left:180px;top:76px;font-size:30px;color:#6FD8A0;line-height:44px;white-space:nowrap">AI 實測 第 07 期</div>
<div data-el="date" class="e" style="right:64px;top:76px;font-size:28px;color:#B4C2D3;line-height:44px">2026/11/03</div>
<div data-el="title" class="e" style="left:64px;top:190px;width:952px;font-size:132px;font-weight:900;line-height:1.12">我用 <span style="color:#6FD8A0">AI</span><br>一天寫完<br>一個月的報表</div>
<div data-el="sub" class="e" style="left:64px;top:674px;font-size:44px;color:#B4C2D3;line-height:60px;white-space:nowrap">實測 3 款工具，第 2 款最意外</div>
<div data-el="pills" class="e" style="left:64px;top:766px;font-size:32px;line-height:64px;white-space:nowrap;display:flex;gap:16px">
{''.join(f'<span style="border:2px solid #2A3A52;background:#182334;border-radius:32px;padding:0 24px">{t}</span>' for t in ['省 6 小時','免費可用','附測試條件'])}</div>
<div data-el="card" class="e" style="left:64px;top:898px;width:952px;height:300px;background:#182334;border:3px solid #2A3A52;border-radius:28px"></div>
<div data-el="foot" class="e" style="left:64px;top:1230px;width:952px;border-top:2px solid #2A3A52;padding-top:12px;font-size:28px;color:#B4C2D3;display:flex;justify-content:space-between"><span><b style="color:#F3F7FB">無業配</b>｜截圖已遮個資</span><span>圖文含 AI 協助</span></div>
</div></body></html>'''

H=f'{OUT}/src/html'; os.makedirs(H,exist_ok=True); jobs=[]
for x in meta:
    for v,pal in (('dark',build.DARK),('light',build.LIGHT)):
        open(f'{H}/{x["k"]}_{v}.html','w').write(f'<body style="margin:0"><img src="{uri(fns[x["k"]],pal)}" width=1024 height=1024>')
        jobs.append(dict(html=f'{x["k"]}_{v}.html',out=f'{x["dir"]}/icon_{v}_1024.png',w=1024,h=1024))
    open(f'{H}/{x["k"]}_c110.html','w').write(f'<body style="margin:0;background:transparent"><img src="{uri(fns[x["k"]],build.DARK)}" style="width:110px;height:110px;border-radius:50%">')
    jobs.append(dict(html=f'{x["k"]}_c110.html',out=f'{x["dir"]}/circle110_dark.png',w=110,h=110,transparent=1))
    open(f'{H}/{x["k"]}_cover.html','w').write(cover(x,x['n']))
    jobs.append(dict(html=f'{x["k"]}_cover.html',out=f'{x["dir"]}/cover_A.png',w=1080,h=1350,check=1))
open(f'{H}/overview.html','w').write(html)
jobs.append(dict(html='overview.html',out=f'{OUT}/overview.png',w=2800,h=1500,full=1))
json.dump(jobs,open(f'{H}/jobs.json','w'))
