# 頻道③ AI 介紹頻道 LOGO：座標格向量，無字型、無 AI 生圖。用法：python build.py
import math, json, os
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
DARK = dict(bg='#0F1722', fg='#F3F7FB', dim='#2A3A52', g='#6FD8A0', a='#FFC857')
LIGHT = dict(bg='#F3F6F9', fg='#0F1722', dim='#C9D3E0', g='#1E9E6A', a='#E39A00')
def pol(cx, cy, r, deg):
    t = math.radians(deg); return cx + r*math.cos(t), cy - r*math.sin(t)
def arc(cx, cy, r, d0, d1):
    x0, y0 = pol(cx, cy, r, d0); x1, y1 = pol(cx, cy, r, d1)
    return f'M{x0:.1f} {y0:.1f}A{r} {r} 0 0 1 {x1:.1f} {y1:.1f}'
S = 'stroke-linecap="round" stroke-linejoin="round" fill="none"'
def l1(p):  # 終端機游標
    return (f'<path d="M150 186L240 256L150 326" stroke="{p["g"]}" stroke-width="40" {S}/>'
            f'<rect x="272" y="300" width="112" height="40" rx="10" fill="{p["a"]}"/>')
def l2(p):  # 勾與叉
    return (f'<rect x="96" y="176" width="150" height="160" rx="30" fill="{p["g"]}"/>'
            f'<rect x="266" y="176" width="150" height="160" rx="30" fill="{p["a"]}"/>'
            f'<path d="M137 258L168 289L206 224" stroke="{p["bg"]}" stroke-width="22" {S}/>'
            f'<path d="M322 232L360 280M360 232L322 280" stroke="{p["bg"]}" stroke-width="22" {S}/>')
def l3(p):  # 實測刻度
    cx, cy, r = 256, 330, 140
    s = f'<path d="{arc(cx,cy,r,180,0)}" stroke="{p["dim"]}" stroke-width="36" {S}/>'
    s += f'<path d="{arc(cx,cy,r,180,70)}" stroke="{p["g"]}" stroke-width="36" {S}/>'
    for d in range(160, 20, -35):
        x0,y0 = pol(cx,cy,r-34,d); x1,y1 = pol(cx,cy,r-58,d)
        s += f'<path d="M{x0:.1f} {y0:.1f}L{x1:.1f} {y1:.1f}" stroke="{p["fg"]}" stroke-width="12" {S}/>'
    nx, ny = pol(cx,cy,r-30,70)
    s += f'<path d="M{cx} {cy}L{nx:.1f} {ny:.1f}" stroke="{p["a"]}" stroke-width="20" {S}/><circle cx="{cx}" cy="{cy}" r="22" fill="{p["a"]}"/>'
    return s
def l4(p):  # 疊層證據
    return (f'<rect x="168" y="112" width="210" height="150" rx="26" stroke="{p["dim"]}" stroke-width="22" fill="none"/>'
            f'<rect x="132" y="164" width="210" height="150" rx="26" stroke="{p["fg"]}" stroke-width="22" fill="{p["bg"]}" opacity="1"/>'
            f'<rect x="96" y="216" width="210" height="150" rx="26" stroke="{p["g"]}" stroke-width="22" fill="{p["bg"]}"/>'
            f'<circle cx="146" cy="266" r="14" fill="{p["a"]}"/><path d="M180 266H262M146 318H262" stroke="{p["g"]}" stroke-width="18" {S}/>')
def l5(p):  # 日誌行
    rows = [(204,p['g']),(262,p['g']),(0,0),(330,p['g'])]
    ys = [140,206,272,338]; ws = [200,250,140,220]; cols=[p['g'],p['g'],p['a'],p['g']]
    s = ''
    for y,w,c in zip(ys,ws,cols):
        s += f'<circle cx="112" cy="{y+17}" r="12" fill="{p["dim"] if c!=p["a"] else p["a"]}"/><rect x="148" y="{y}" width="{w}" height="34" rx="17" fill="{c}"/>'
    return s
def l6(p):  # 前後對照柱
    return (f'<rect x="120" y="262" width="110" height="130" rx="22" fill="{p["dim"]}"/>'
            f'<rect x="282" y="120" width="110" height="272" rx="22" fill="{p["g"]}"/>'
            f'<path d="M96 424H416" stroke="{p["a"]}" stroke-width="16" {S}/>')
def l7(p):  # 放大驗證
    return (f'<circle cx="228" cy="228" r="110" stroke="{p["fg"]}" stroke-width="34" fill="none"/>'
            f'<path d="M306 306L398 398" stroke="{p["a"]}" stroke-width="40" {S}/>'
            f'<path d="M180 232L216 268L280 190" stroke="{p["g"]}" stroke-width="30" {S}/>')
def l8(p):  # 實驗矩陣
    s=''; lit={(0,0),(1,0),(2,1),(0,2),(1,1)}
    for i in range(3):
        for j in range(3):
            x=116+i*100; y=116+j*100
            if (i,j)==(2,2): s+=f'<rect x="{x}" y="{y}" width="80" height="80" rx="16" fill="{p["a"]}"/>'
            elif (i,j) in lit: s+=f'<rect x="{x}" y="{y}" width="80" height="80" rx="16" fill="{p["g"]}"/>'
            else: s+=f'<rect x="{x+6}" y="{y+6}" width="68" height="68" rx="13" stroke="{p["dim"]}" stroke-width="12" fill="none"/>'
    return s
LOGOS = [
 ('a1','終端游標','綠色「>」加琥珀色游標方塊：每個做法都是我親手在終端機跑過的，不是轉述。',l1),
 ('a2','勾與叉並陳','綠勾與琥珀叉兩塊同大：成功與翻車同樣大方攤開，這就是「透明」。',l2),
 ('a3','實測刻度','半圓量表加指針：用數字量過才下結論，不憑感覺。',l3),
 ('a4','疊層證據','三層視窗疊起，最前面一層帶琥珀紀錄點：每個結論背後都有一疊截圖可查。',l4),
 ('a5','日誌行','綠色行列中夾一行琥珀：上班日記，翻車那行也照實記下。',l5),
 ('a6','前後對照柱','矮灰柱對高綠柱立在同一條基準線：有沒有用，用前後對比說話。',l6),
 ('a7','放大驗證','放大鏡裡一個綠勾：「可驗證」，每一步你都能自己再做一次。',l7),
 ('a8','實驗矩陣','3×3 格子，綠＝成功、空框＝沒做出來、右下琥珀＝翻車：一格一次實測。',l8),
]
def svg(fn,p,size=512,bg=True):
    r = f'<rect width="512" height="512" fill="{p["bg"]}"/>' if bg else ''
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="{size}" height="{size}">{r}{fn(p)}</svg>'
if __name__=='__main__':
    meta=[]
    for k,n,m,fn in LOGOS:
        d=f'{OUT}/{k}_{n}'; os.makedirs(d,exist_ok=True)
        open(f'{d}/icon_dark.svg','w').write(svg(fn,DARK)); open(f'{d}/icon_light.svg','w').write(svg(fn,LIGHT))
        open(f'{d}/mark_transparent.svg','w').write(svg(fn,DARK,bg=False))
        meta.append(dict(k=k,n=n,m=m,dir=d))
    json.dump(meta,open(f'{OUT}/src/meta.json','w'),ensure_ascii=False)
