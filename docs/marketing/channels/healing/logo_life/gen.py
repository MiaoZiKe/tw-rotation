# 「我們這一代」生活體驗 LOGO 10 款（全部自繪向量，不用 AI 圖、不用比比、不走吉祥物）
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

# ---- 符號：回傳 (svg, 半寬, 半高)。要檢查不重疊的元素加 id p1..p4 ----
def s1(c):   # 電量 3%：直立電池，只剩最底一小格是暖黃
    L = Ls(c, 8)
    return (f'<rect x="-50" y="-70" width="100" height="156" rx="16" {L}/><rect x="-18" y="-90" width="36" height="14" rx="5" {L}/>'
            f'<rect x="-34" y="58" width="68" height="16" rx="5" fill="{c["lamp"]}"/>'), 54, 96
def s2(c):   # 租屋鑰匙圈＋門牌號
    L = Ls(c, 7)
    return (f'<g transform="translate(0 12)"><circle cx="0" cy="-62" r="24" {L}/><path d="M0 -38 V-18" {L}/>'
            f'<rect x="-44" y="-28" width="88" height="96" rx="16" {L}/><circle id="p1" cx="0" cy="-10" r="8" fill="{c["lamp"]}"/>'
            + T('p2', 0, 48, '302', 36, c['ink']) + '</g>'), 48, 80
def s3(c):   # 末班車廂：一根立柱＋一排座椅，只有最後一格亮
    L = Ls(c, 8); o = f'<path d="M-68 -80 V76" {Ls(c,9)}/><path d="M-84 -80 H-52" {L}/><path d="M-90 78 H90" {L}/>'
    for k, x in enumerate((-48, -6, 36)):
        fill = f'fill="{c["lamp"]}" stroke="{c["lamp"]}" stroke-width="8" stroke-linejoin="round"' if k == 2 else L
        o += f'<rect x="{x}" y="-30" width="34" height="40" rx="9" {fill}/>'
    o += f'<rect x="-48" y="24" width="118" height="24" rx="8" {L}/>'
    return o, 92, 86
def s4(c):   # 微波便當／泡麵：碗＋三縷蒸氣，中間一縷是暖黃
    L = Ls(c, 8); st = lambda x, col: f'<path d="M{x} -10 q-14 -16 0 -32 t0 -32" {Ls(c,8,col)}/>'
    return (f'<g transform="translate(0 -6)"><path d="M-80 8 H80" {L}/><path d="M-68 8 C-68 62 -36 84 0 84 C36 84 68 62 68 8" {L}/>'
            f'<path d="M-26 92 H26" {L}/>' + st(-34, c['line']) + st(0, c['lamp']) + st(34, c['line']) + '</g>'), 82, 86
def s5(c):   # 存款簿：一條細進度條，只填了一小段
    L = Ls(c, 7)
    return (f'<rect x="-74" y="-70" width="148" height="140" rx="16" {L}/><path d="M-52 -70 V70" {Ls(c,5)}/>'
            f'<path d="M-30 -36 H20" {L}/><rect x="-30" y="-6" width="90" height="18" rx="9" {Ls(c,6)}/>'
            f'<rect x="-25" y="-1" width="16" height="8" rx="4" fill="{c["lamp"]}"/><path d="M-30 38 H4 M16 38 H44" {Ls(c,6)}/>'), 76, 72
def s6(c):   # 過年飯桌：對話泡泡「什麼時候…？」，最後一點是暖黃
    L = Ls(c, 8)
    d = 'M-60 -62 H60 A24 24 0 0 1 84 -38 V22 A24 24 0 0 1 60 46 H-8 L-46 80 L-40 46 H-60 A24 24 0 0 1 -84 22 V-38 A24 24 0 0 1 -60 -62 Z'
    return (f'<g transform="translate(0 -9)"><path d="{d}" {L}/>' + T('p1', 0, -12, '什麼時候', 34, c['ink'])
            + f'<circle cx="-56" cy="22" r="5.5" fill="{c["line"]}"/><circle cx="-40" cy="22" r="5.5" fill="{c["line"]}"/><circle id="p2" cx="-24" cy="22" r="5.5" fill="{c["lamp"]}"/>'
            + T('p3', 14, 34, '？', 34, c['ink'], 'start') + '</g>'), 88, 76
def s7(c):   # 室內衣架上的帽 T：帽口那一點是暖黃
    L = Ls(c, 8)
    body = ('M-28 -52 L-74 -34 L-82 28 L-62 32 L-56 -2 L-56 64 L56 64 L56 -2 L62 32 L82 28 L74 -34 L28 -52')
    return (f'<g transform="translate(0 18.5) scale(.88)"><path d="{body}" {L}/><path d="M-28 -52 C-36 -96 36 -96 28 -52" {L}/>'
            f'<path d="M-28 -52 Q0 -34 28 -52" {L}/><circle cx="0" cy="-66" r="7" fill="{c["lamp"]}"/>'
            f'<path d="M-34 28 H34 L40 54 H-40 Z" {L}/><path d="M0 -86 V-94 C0 -108 20 -106 18 -94" {L}/></g>'), 74, 76
def s8(c):   # 小套房俯視平面圖：一張床、一盞檯燈
    L = Ls(c, 8)
    return (f'<path d="M30 70 H-84 V-70 H84 V70 H66" {L}/><path d="M30 70 V38 A32 32 0 0 1 62 70" {Ls(c,5)}/>'
            f'<rect x="-66" y="-54" width="72" height="84" rx="8" {Ls(c,6)}/><rect x="-58" y="-46" width="30" height="20" rx="6" {Ls(c,5)}/>'
            f'<rect x="22" y="-54" width="30" height="30" rx="6" {Ls(c,5)}/><circle cx="37" cy="-39" r="8" fill="{c["lamp"]}"/>'), 90, 74
def s9(c):   # 一排信箱，只有一格有信
    L = Ls(c, 6); o = ''
    for r, y in enumerate((-58, 4)):
        for k in range(4):
            x = -84 + k * 44; o += f'<rect x="{x}" y="{y}" width="36" height="54" rx="6" {L}/><path d="M{x+8} {y+24} H{x+28}" {Ls(c,5)}/><circle cx="{x+18}" cy="{y+42}" r="3.5" fill="{c["line"]}"/>'
            if (r, k) == (1, 2): o += f'<rect x="{x+6}" y="{y+6}" width="24" height="18" rx="3" fill="{c["lamp"]}"/>'
    return o, 88, 62
def s10(c):  # 計算機螢幕 0.695（小數點是暖黃）
    L = Ls(c, 7); o = f'<rect x="-60" y="-88" width="120" height="176" rx="18" {L}/><rect x="-46" y="-72" width="92" height="46" rx="8" {Ls(c,5)}/>'
    o += T('p1', 40, -38, '695', 26, c['ink'], 'end') + f'<circle id="p2" cx="-13" cy="-38" r="4.5" fill="{c["lamp"]}"/>' + T('p3', -22, -38, '0', 26, c['ink'], 'end')
    for r in range(3):
        for k in range(3): o += f'<rect x="{-45+k*34}" y="{-8+r*30}" width="24" height="18" rx="5" {Ls(c,5)}/>'
    return o, 62, 90

STYLES = [
 dict(n=1, name='電量3%', sym=s1, exp='手機永遠剩 3% 還在趕路、不敢離開插座的那個人。'),
 dict(n=2, name='租屋鑰匙', sym=s2, exp='鑰匙圈上掛的永遠是別人家的門牌：租了又搬、搬了又租。'),
 dict(n=3, name='末班座椅', sym=s3, exp='末班車廂一整排空座位、一根立柱，回家的路上只剩自己。'),
 dict(n=4, name='熱便當蒸氣', sym=s4, exp='一個人加班後微波的便當、泡麵，蒸氣是今天唯一的暖。'),
 dict(n=5, name='存款進度條', sym=s5, exp='存款簿上那條頭期款進度條，努力很久只填了一小段。'),
 dict(n=6, name='什麼時候', sym=s6, exp='過年飯桌上那句「什麼時候…？」，全家人都在等你回答。'),
 dict(n=7, name='室內帽T', sym=s7, exp='小套房沒陽台，帽 T 只能掛在室內衣架上慢慢晾乾。'),
 dict(n=8, name='小套房平面', sym=s8, exp='整個家只有一張床加一盞檯燈的小套房，一坪都不浪費。'),
 dict(n=9, name='一格有信', sym=s9, exp='一整排信箱只有一格有信，同棟的每個我們都過一樣的日子。'),
 dict(n=10, name='計算機0.695', sym=s10, exp='台灣生育率 0.695：用計算機按出來的，是這一代的現實。'),
]
def folder(st): return f"{st['n']:02d}_{st['name']}"
IDS = ['sym', 'nm', 'p1', 'p2', 'p3']
PAIRS = {2: [['p1', 'p2']], 6: [['p1', 'p3'], ['p1', 'p2'], ['p2', 'p3']], 10: [['p1', 'p2'], ['p2', 'p3'], ['p1', 'p3']]}

def avatar(st, c):
    s, hw, hh = st['sym'](c); import math
    sc = min(3.4, 400 / math.hypot(hw, hh))
    return wrap(1080, 1080, c, f'<g id="sym" transform="translate(540 540) scale({sc:.3f})">{s}</g>'), sc
def wordmark(st, c, transparent=False, H=400):
    s, hw, hh = st['sym'](c); ss = 120 / hh; fs = 120; ls = 0.1; pad = 70; cy = H / 2; base = cy + fs * 0.36
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
