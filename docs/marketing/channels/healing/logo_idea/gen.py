# 「我們這一代」創意概念 LOGO 10 款（全部自繪向量，不用 AI 圖、不用比比、不走吉祥物）
# 用法：python3 gen.py → node render.js → python3 compose.py
import json, os
from PIL import ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
NAME = '我們這一代'
FD = os.path.expanduser('~/.fonts/')
SB = (FD+'NotoSansCJKtc-Bold.otf', "'Noto Sans CJK TC',sans-serif", 700)
PAL = {
 '霧紫灰': dict(bg='#4A4454', ink='#F3EFF5', line='#ABA0B5', lamp='#F2D88E', mono=False),
 '單色白': dict(bg='#000000', ink='#FFFFFF', line='#FFFFFF', lamp='#FFFFFF', mono=True),
 '單色黑': dict(bg='#FFFFFF', ink='#000000', line='#000000', lamp='#000000', mono=True),
}
def tw(s, fs, ls):
    return ImageFont.truetype(SB[0], 200).getlength(s) * fs / 200 + ls * fs * len(s)
def T(i, x, y, s, fs, fill, anchor='middle', ls=0.0):
    if anchor == 'middle': x += ls * fs / 2
    return (f'<text id="{i}" x="{x:.1f}" y="{y:.1f}" font-family="{SB[1]}" font-weight="700" font-size="{fs}" '
            f'letter-spacing="{ls*fs:.1f}" text-anchor="{anchor}" fill="{fill}">{s}</text>')
def Ls(c, sw, col=None):
    return f'fill="none" stroke="{col or c["line"]}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"'
def wrap(w, h, c, body, transparent=False):
    bg = '' if transparent else f'<rect width="{w}" height="{h}" fill="{c["bg"]}"/>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{bg}{body}</svg>'

# ---- 符號：回傳 (svg, 半寬, 半高)；全部以原點為中心。單色版 lamp==ink，所以「燈」一律用實心面，與線條區別 ----
def dim(c): return '' if c['mono'] else ' opacity=".55"'
def Fl(c): return f'fill="{c["lamp"]}"'
def s1(c):   # 一扇窗同時是一隻眼睛：杏眼輪廓裡的瞳孔是四格窗，只有一格亮
    L = Ls(c, 8); W = Ls(c, 6)
    return (f'<path d="M-100 0 Q0 -112 100 0 Q0 112 -100 0 Z" {L}/>'
            f'<rect x="-32" y="-32" width="64" height="64" rx="8" {W}/><path d="M0 -32 V32 M-32 0 H32" {Ls(c,5)}/>'
            f'<rect x="5" y="-27" width="22" height="22" rx="3" {Fl(c)}/>'), 104, 60
def s2(c):   # 放大鏡裡一整面公寓牆，只有一扇窗亮著
    L = Ls(c, 8); o = f'<g transform="translate(-7 -7)"><circle cx="-14" cy="-14" r="62" {L}/><path d="M31 31 L82 82" {Ls(c,13)}/>'
    for r in range(3):
        for k in range(3):
            x = -14 + (k-1)*28; y = -14 + (r-1)*28
            if (r, k) == (0, 2): o += f'<rect x="{x-9}" y="{y-9}" width="18" height="18" rx="3" {Fl(c)}/>'
            else: o += f'<rect x="{x-9}" y="{y-9}" width="18" height="18" rx="3" {Ls(c,5)}{dim(c)}/>'
    return o + '</g>', 86, 86
def s3(c):   # 沙漏的兩個玻璃球，是一間倒過來的房子和一間正的房子；沙正往下掉
    L = Ls(c, 8)
    o = (f'<path d="M-50 -84 V-46 L-6 -4 M50 -84 V-46 L6 -4" {L}/><path d="M-6 4 L-50 46 V84 M6 4 L50 46 V84" {L}/>'
         f'<path d="M-64 -84 H64 M-64 84 H64" {Ls(c,10)}/>'
         f'<path d="M0 -2 V44" {Ls(c,5,c["lamp"])}/><path d="M-26 78 L0 46 L26 78 Z" {Fl(c)} stroke="{c["lamp"]}" stroke-width="4" stroke-linejoin="round"/>')
    return o, 68, 90
def s4(c):   # 鑰匙的齒，就是一條往上爬的房價線
    L = Ls(c, 8)
    return (f'<g transform="translate(-6 -12)"><circle cx="-62" cy="0" r="26" {L}/><path d="M-36 0 H92" {L}/>'
            f'<path d="M-4 0 V52 L18 34 L36 44 L56 20 L74 28 L92 4" {Ls(c,7)}/><circle cx="92" cy="4" r="11" {Fl(c)}/></g>'), 100, 42
def s5(c):   # 電池的形狀是一間房子，只充到 3%
    L = Ls(c, 8)
    return (f'<g transform="translate(0 5)"><path d="M-54 -10 L0 -62 L54 -10 V74 H-54 Z" {L}/><rect x="-22" y="-84" width="44" height="14" rx="4" fill="{c['line']}"/>'
            f'<path d="M-36 6 H36 M-36 26 H36 M-36 46 H36" {Ls(c,4)} stroke-dasharray="10 9"{dim(c)}/>'
            f'<rect x="-40" y="58" width="80" height="10" rx="4" {Fl(c)}/></g>'), 58, 84
def s6(c):   # 一盞燈泡裡，住著一間小套房
    L = Ls(c, 8)
    return (f'<g transform="translate(0 -2)"><path d="M-24 42 A62 62 0 1 1 24 42 V58 H-24 Z" {L}/><path d="M-18 70 H18 M-10 82 H10" {Ls(c,7)}/>'
            f'<path d="M-30 -14 L0 -44 L30 -14 V24 H-30 Z" {Ls(c,7)}/><rect x="-9" y="-9" width="18" height="18" rx="3" {Fl(c)}/></g>'), 66, 84
def s7(c):   # 一整面大樓的窗，亮的、實心的拼成「人」字，頂端那一格是暖黃
    o = ''; P = 32; S = 24
    ren = {(0,2),(1,1),(1,3),(2,1),(2,3),(3,0),(3,4),(4,0),(4,4)}
    for r in range(5):
        for k in range(5):
            x = (k-2)*P-S/2; y = (r-2)*P-S/2
            if (r, k) == (0, 2): o += f'<rect x="{x}" y="{y}" width="{S}" height="{S}" rx="4" {Fl(c)}/>'
            elif (r, k) in ren: o += f'<rect x="{x}" y="{y}" width="{S}" height="{S}" rx="4" fill="{c["line"]}"/>'
            else: o += f'<rect x="{x+2}" y="{y+2}" width="{S-4}" height="{S-4}" rx="3" {Ls(c,4)}{dim(c)}/>'
    return o, 78, 78
def s8(c):   # 燈泡是實心的，人形（抽象幾何、站著）是從燈裡挖出來的負空間；中間那個頭是亮的
    cx = lambda x, top: (f'<circle cx="{x}" cy="{top}" r="9" fill="#000"/><path d="M{x-10} 34 V{top+22} A10 10 0 0 1 {x+10} {top+22} V34 Z" fill="#000"/>')
    mk = ('<mask id="mk"><rect x="-100" y="-100" width="200" height="200" fill="#fff"/>' + cx(-27, -8) + cx(0, -22) + cx(27, -8) + '</mask>')
    return (f'<defs>{mk}</defs><g mask="url(#mk)"><circle cx="0" cy="-14" r="70" fill="{c["line"]}"/><rect x="-26" y="40" width="52" height="30" rx="7" fill="{c["line"]}"/></g>'
            f'<rect x="-18" y="74" width="36" height="12" rx="5" fill="{c["line"]}"/><circle cx="0" cy="-22" r="9" {Fl(c)}/>'), 70, 86
def s9(c):   # 窗格的直框，長成一支向上的箭頭
    L = Ls(c, 8)
    return (f'<g transform="translate(0 -6)"><rect x="-62" y="-70" width="124" height="140" rx="18" {L}/><path d="M-74 84 H74" {Ls(c,7)}/>'
            f'<path d="M-62 22 H62" {Ls(c,6)}/><path d="M0 70 V-40" {Ls(c,6)}/><path d="M-28 -16 L0 -44 L28 -16" {Ls(c,10,c["lamp"])}/></g>'), 76, 88
def s10(c):  # 月曆的最後一格，透出一點光
    o = f'<g transform="translate(0 -8)"><rect x="-70" y="-66" width="140" height="148" rx="14" {Ls(c,7)}/><path d="M-70 -34 H70" {Ls(c,6)}/>'
    n = 0
    for r in range(5):
        for k in range(7):
            n += 1
            if n > 30: break
            x = -54 + k*18; y = -12 + r*18
            if n == 30: o += f'<rect x="{x-8}" y="{y-8}" width="16" height="16" rx="3" {Fl(c)}/><path d="M{x+14} {y} H{x+30} M{x+12} {y-9} L{x+26} {y-18} M{x+12} {y+9} L{x+26} {y+18}" {Ls(c,5,c["lamp"])}/>'
            else: o += f'<rect x="{x-5}" y="{y-5}" width="10" height="10" rx="2" {Ls(c,3.5)}{dim(c)}/>'
    return o + '</g>', 72, 78

STYLES = [
 dict(n=1, name='窗是眼', sym=s1, exp='一扇窗同時是一隻眼睛：觀察家看見的，是每一戶只亮一格的窗。', how='兩個意象合一（窗＝眼）'),
 dict(n=2, name='放大鏡公寓', sym=s2, exp='放大鏡一照，一整面公寓牆，只有一扇窗亮著。', how='比例錯置＋小反差（放大鏡裡是整棟樓）'),
 dict(n=3, name='沙漏房子', sym=s3, exp='沙漏的兩個玻璃球是一正一倒的房子，時間往下掉，房子還是遠的。', how='雙關（沙漏＝等一間房）'),
 dict(n=4, name='鑰匙房價線', sym=s4, exp='鑰匙的齒是一條往上爬的房價線，終點那一點是暖黃。', how='兩個意象合一（鑰匙齒＝折線圖）'),
 dict(n=5, name='房子電池', sym=s5, exp='電池的形狀是一間房子，只充到了 3%。', how='兩個意象合一＋小反差（屋頂接電池頭）'),
 dict(n=6, name='燈泡套房', sym=s6, exp='一盞燈泡裡，住著一間亮著窗的小套房。', how='比例錯置（燈泡裡裝一個家）'),
 dict(n=7, name='窗拼人字', sym=s7, exp='整棟樓的窗，實心的那些拼成一個「人」字，頂端一格亮著。', how='負空間／像素拼字（窗＝人）'),
 dict(n=8, name='燈裡的人', sym=s8, exp='燈是實心的，三個站著的幾何人形是從燈裡挖出來的光，中間那顆頭亮著。', how='負空間（人形＝燈的缺口）'),
 dict(n=9, name='窗格向上', sym=s9, exp='窗格的直框長成一支向上的箭頭，箭尖是暖黃。', how='兩個意象合一（窗格＝箭頭）'),
 dict(n=10, name='月曆末格', sym=s10, exp='月曆最後一格，透出一點光。', how='小反差（整頁灰色格子裡，唯一發光的一天）'),
]
def folder(st): return f"{st['n']:02d}_{st['name']}"
IDS = ['sym', 'nm']
PAIRS = {}

def avatar(st, c):
    s, hw, hh = st['sym'](c); import math
    sc = min(4.6, 400 / math.hypot(hw, hh))
    return wrap(1080, 1080, c, f'<g id="sym" transform="translate(540 540) scale({sc:.3f})">{s}</g>'), sc
def wordmark(st, c, transparent=False, H=400):
    s, hw, hh = st['sym'](c); ss = min(120 / hh, 175 / hw); fs = 120; ls = 0.1; pad = 70; cy = H / 2; base = cy + fs * 0.36
    gap = 0.5 * fs; sx = pad + hw * ss; tx = pad + 2 * hw * ss + gap; tl = tw(NAME, fs, ls) - ls * fs
    W = round(tx + tl + pad)
    body = f'<g id="sym" transform="translate({sx:.1f} {cy}) scale({ss:.3f})">{s}</g>' + T('nm', tx, base, NAME, fs, c['ink'], 'start', ls)
    return W, H, wrap(W, H, c, body, transparent)

jobs = []
for st in STYLES:
    fo = folder(st); os.makedirs(fo, exist_ok=True)
    for tag, c in PAL.items():
        av, sc = avatar(st, c); p = f'{fo}/頭像_1080_{tag}'
        open(p + '.svg', 'w', encoding='utf-8').write(av)
        jobs.append(dict(svg=p + '.svg', png=p + '.png', w=1080, h=1080, kind='avatar', n=st['n'], tag=tag, pairs=PAIRS.get(st['n'], []), ids=IDS, sc=sc))
        W, H, sv = wordmark(st, c); p = f'{fo}/字標_{tag}'
        open(p + '.svg', 'w', encoding='utf-8').write(sv)
        jobs.append(dict(svg=p + '.svg', png=p + '.png', w=W, h=H, kind='wm', n=st['n'], tag=tag, ids=['sym', 'nm']))
    W, H, sv = wordmark(st, PAL['霧紫灰'], True); p = f'{fo}/字標_透明_霧紫灰'
    open(p + '.svg', 'w', encoding='utf-8').write(sv)
    jobs.append(dict(svg=p + '.svg', png=p + '.png', w=W, h=H, kind='cover', n=st['n'], tag='透明', transparent=True, ids=[]))
json.dump(dict(jobs=jobs, styles=[{k: v for k, v in s.items() if k != 'sym'} for s in STYLES], pal=PAL), open('jobs.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(jobs), 'jobs')
