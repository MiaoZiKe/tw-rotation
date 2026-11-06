# 「談晴說礙」LOGO 第三輪：簡約（2026-11-06 Andy：「LOGO 太糟糕 需要簡約風格」）
# 規則：符號只用 1～3 個幾何元素、同一線寬；晴＝晴光橘（q 圖層）、礙＝雲灰（a 圖層）；字不放進圖形。
# 重跑：rm -f fit.json; python3 gen_tq3.py && node render.js && python3 fit_tq3.py && python3 gen_tq3.py && node render.js && python3 post_tq3.py
import os, json
from PIL import ImageFont
H = os.path.dirname(os.path.abspath(__file__)); os.chdir(H)
CHK = '/tmp/claude-0/-home-user-tw-rotation/ce50d787-1067-5482-ab44-99dc39a48890/scratchpad/tqsa3'; os.makedirs(CHK, exist_ok=True)
FIT = json.load(open('fit.json')) if os.path.exists('fit.json') else {}
NAME = '談晴說礙'; SUB = '礙還在，晴也在。'
FD = os.path.expanduser('~/.fonts/')
FONT = {'serif': ('Noto Serif CJK TC', FD+'NotoSerifCJKtc-Regular.otf'), 'sans': ('Noto Sans CJK TC', FD+'NotoSansCJKtc-Regular.otf')}
# 統一色票（與模板設計師共用）。晝版「晴」文字色另外加深到對比 4.5:1，符號仍用 #D9822B（見 README）
TONES = {
 '夜版': dict(bg='#2B2A2E', ink='#F3EEE6', sub='#B8B1A7', a='#CFC9C0', q='#F2B35E'),
 '晝版': dict(bg='#F6F1E8', ink='#2F2D2B', sub='#6E6A66', a='#6E6A66', q='#D9822B'),
 '單色黑': dict(bg='#FFFFFF', ink='#111111', sub='#111111', a='#111111', q='#111111', mono=1),
 '單色白': dict(bg='#111111', ink='#FFFFFF', sub='#FFFFFF', a='#FFFFFF', q='#FFFFFF', mono=1),
}
def rgb(h): return [int(h[i:i+2], 16) for i in (1, 3, 5)]
def blend(a, b, t): return '#' + ''.join(f'{round(x+(y-x)*t):02X}' for x, y in zip(rgb(a), rgb(b)))
def lum(h):
    f = lambda c: c/12.92 if c <= .03928 else ((c+.055)/1.055)**2.4
    r, g, b = [f(v/255) for v in rgb(h)]; return .2126*r+.7152*g+.0722*b
def ratio(a, b):
    x, y = sorted((lum(a), lum(b)), reverse=True); return (x+.05)/(y+.05)
def fix(c, bg, toward, tgt=4.5):   # 把文字色往 toward 推到對比 ≥ tgt
    for i in range(51):
        k = blend(c, toward, i/50)
        if ratio(k, bg) >= tgt: return k
    return toward
# 晝版符號「晴」#D9822B 對 #F6F1E8 只有 2.6:1，低於圖形對比 3:1 → 微調加深到 3:1（README 有寫）
TONES['晝版']['q0'] = TONES['晝版']['q']; TONES['晝版']['q'] = fix(TONES['晝版']['q'], TONES['晝版']['bg'], TONES['晝版']['ink'], 3.0)
def tq_text(P): return P['q'] if ratio(P['q'], P['bg']) >= 4.5 else fix(P['q'], P['bg'], P['ink'])
def ta_text(P): return P['a'] if ratio(P['a'], P['bg']) >= 4.5 else fix(P['a'], P['bg'], P['ink'])
SW = 24   # 全部符號統一線寬（±200 座標系）
def st(c): return f'fill="none" stroke="{c}" stroke-width="{SW}" stroke-linecap="round" stroke-linejoin="round"'
def fl(c): return f'fill="{c}"'
# ---- 符號：回傳 (晴圖層, 礙圖層) 的 SVG 片段；座標 ±200，原點在中心
def s1(q, a):   # 日出被橫線擋住
    return (f'<path d="M -110 10 A 110 110 0 0 1 110 10" {st(q)}/>',
            f'<path d="M -170 62 H 170 M -90 114 H 90" {st(a)}/>')
def s2(q, a):   # 圓圈裡一個光點
    return (f'<circle cx="0" cy="0" r="40" {fl(q)}/>', f'<circle cx="0" cy="0" r="150" {st(a)}/>')
def s3(q, a):   # 對話框裡一個光點
    return (f'<circle cx="0" cy="-20" r="34" {fl(q)}/>',
            f'<path d="M -100 -120 H 100 A 70 70 0 0 1 170 -50 V 20 A 70 70 0 0 1 100 90 H -20 L -105 160 L -95 90 H -100 A 70 70 0 0 1 -170 20 V -50 A 70 70 0 0 1 -100 -120 Z" {st(a)}/>')
def s4(q, a):   # 雲弧下面有一點光
    return (f'<circle cx="0" cy="62" r="40" {fl(q)}/>', f'<path d="M -150 14 A 48 48 0 0 1 -82 -44 A 72 72 0 0 1 60 -40 A 48 48 0 0 1 150 14" {st(a)}/>')
def s5(q, a):   # 「日」字抽象：方框、橫線、中間的點
    return (f'<circle cx="0" cy="0" r="30" {fl(q)}/>',
            f'<rect x="-120" y="-165" width="240" height="330" rx="40" {st(a)}/><path d="M -120 0 H -80 M 80 0 H 120" {st(a)}/>')
def s6(q, a):   # 圓被一道雲浪切過
    import math
    r = 125; P = lambda d: (r*math.cos(math.radians(d)), r*math.sin(math.radians(d)))
    (x1, y1), (x2, y2), (x3, y3), (x4, y4) = P(208), P(332), P(28), P(152)
    return (f'<path d="M {x1:.1f} {y1:.1f} A {r} {r} 0 0 1 {x2:.1f} {y2:.1f}" {st(q)}/><path d="M {x3:.1f} {y3:.1f} A {r} {r} 0 0 1 {x4:.1f} {y4:.1f}" {st(q)}/>',
            f'<path d="M -185 0 C -145 -34 -105 34 -65 0 S 15 -34 55 0 S 135 34 185 0" {st(a)}/>')
def s7(q, a):   # 晴時多雲：太陽露出上緣、雲在前
    import math
    P = lambda d: (80+110*math.cos(math.radians(d)), -50+110*math.sin(math.radians(d)))
    (x1, y1), (x2, y2) = P(195), P(395)
    return (f'<path d="M {x1:.1f} {y1:.1f} A 110 110 0 0 1 {x2:.1f} {y2:.1f}" {st(q)}/>',
            f'<path d="M -120 120 H 110 A 40 40 0 0 0 110 40 A 67.5 67.5 0 0 0 -25 35 A 55 55 0 0 0 -120 120 Z" {st(a)}/>')
def s8(q, a):   # 沒封口的圓，缺口裡有光
    import math
    r = 145; t = math.radians(34); x = r*math.cos(t); y = r*math.sin(t)
    return (f'<circle cx="95" cy="0" r="34" {fl(q)}/>', f'<path d="M {x:.1f} {-y:.1f} A {r} {r} 0 1 0 {x:.1f} {y:.1f}" {st(a)}/>')
def s9(q, a):   # 三個點：說不出口的兩個、最後亮起的一個
    return (f'<circle cx="120" cy="0" r="48" {fl(q)}/>', f'<circle cx="-120" cy="0" r="34" {fl(a)}/><circle cx="-10" cy="0" r="34" {fl(a)}/>')
def s10(q, a):  # 兩個圓：一個空心（礙）、一個實心發亮（晴），像兩個人對談
    return (f'<circle cx="112" cy="0" r="62" {fl(q)}/>', f'<circle cx="-82" cy="0" r="100" {st(a)}/>')
SYMS = {
 1: ('01_日出擋線', '日出擋線', '半圓日出被兩道橫線擋在下面。', '半圓日出（橘）', '兩道橫線（雲灰）', s1),
 2: ('02_圓中一點', '圓中一點', '一個細線圓，圓心一點光。', '圓心的光點（橘）', '外圈的圓（雲灰），把光圍在裡面', s2),
 3: ('03_對話框光點', '對話框光點', '對話框的輪廓，框裡只亮一個點。', '框裡的光點（橘）', '對話框輪廓（雲灰），談不出口的話', s3),
 4: ('04_雲下有光', '雲下有光', '一道雲的輪廓，雲下面亮著一個點。', '雲下的光點（橘）', '上方的雲弧（雲灰）', s4),
 5: ('05_日字框', '日字框', '「日」字抽象成方框、橫線，中間一個點。', '中間的點（橘），是「日」的光', '方框與橫線（雲灰），把日框住', s5),
 6: ('06_雲浪切圓', '雲浪切圓', '圓被一道雲浪切過，圓弧在浪的兩側留出空隙。', '被切開的圓（橘）', '穿過的雲浪（雲灰）', s6),
 7: ('07_晴時多雲', '晴時多雲', '太陽被雲擋住一半，只露出上緣的弧。', '露出的太陽弧（橘）', '前面的雲輪廓（雲灰）', s7),
 8: ('08_缺口圓', '缺口圓', '沒封口的圓，缺口裡有一點光。', '缺口裡的光點（橘）', '沒封口的圓（雲灰），礙還在', s8),
 9: ('09_三點', '三點', '三個點：兩個灰點，最後一個亮起來。', '最後亮起的點（橘）', '前面兩個沒說出口的點（雲灰）', s9),
 10: ('10_雙圓對談', '雙圓對談', '一個空心圓、一個實心圓並排，像兩個人在對談。', '實心發亮的圓（橘）', '空心的圓（雲灰）', s10),
}
def sym_layers(n, P): return SYMS[n][5](P['q'], P['a'])
def L(layer, inner): return f'<g data-layer="{layer}">{inner}</g>'
def avatar_svg(n, P, bg=True, k=1.0, off=(0, 0)):
    q, a = sym_layers(n, P)
    r = f'<rect width="1080" height="1080" fill="{P["bg"]}"/>' if bg else ''
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1080" viewBox="0 0 1080 1080">{r}<g transform="translate({540-off[0]*k} {540-off[1]*k}) scale({k})">{L("a", a)}{L("q", q)}</g></svg>'
def tw(txt, font, fs, ls):
    f = ImageFont.truetype(FONT[font][1], fs); return sum(f.getlength(c) for c in txt) + ls*(len(txt)-1)
def wm_svg(n, P, sub, bg=True, font='serif', dotted=True, fit=None):
    fam = FONT[font][0]
    cx, cy, far = fit
    ks = 150/far; symcx = 60+150; H = 420
    q, a = sym_layers(n, P)
    sym = f'<g transform="translate({symcx} 210) scale({ks}) translate({-cx} {-cy})">{L("a", a)}{L("q", q)}</g>'
    x0 = 420; fs = 140 if sub else 150; ls = 30
    ny = (170 if sub else 210) + .38*fs
    cols = [P['ink'], tq_text(P) if dotted else P['ink'], P['ink'], ta_text(P) if dotted else P['ink']]
    f = ImageFont.truetype(FONT[font][1], fs); x = x0; txt = ''
    for i, ch in enumerate(NAME):
        txt += f'<text x="{x:.1f}" y="{ny:.1f}" font-family="{fam}" font-size="{fs}" fill="{cols[i]}">{ch}</text>'; x += f.getlength(ch) + ls
    W = int(x - ls + 70)
    body = L('sym', sym) + L('txt', txt)
    if sub:
        sf = 40; sls = 10; fs2 = ImageFont.truetype(FONT['sans'][1], sf); xx = x0; s = ''
        for ch in SUB:
            s += f'<text x="{xx:.1f}" y="322" font-family="Noto Sans CJK TC" font-size="{sf}" fill="{P["sub"]}">{ch}</text>'; xx += fs2.getlength(ch) + sls
        body += L('sub', s)
        W = max(W, int(xx - sls + 70))
    bgr = f'<rect width="{W}" height="{H}" fill="{P["bg"]}"/>' if bg else ''
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{bgr}{body}</svg>', W, H
DEFAULT = dict(font='serif', dotted=True)
VARIANTS = {'襯線_晴礙點色': ('serif', True), '襯線_全單色': ('serif', False), '黑體_晴礙點色': ('sans', True), '黑體_全單色': ('sans', False)}
if __name__ == '__main__':
    jobs = []
    def add(**k): jobs.append(k)
    for n, (fo, nm, mean, qd, ad, fn) in SYMS.items():
        os.makedirs(fo, exist_ok=True)
        fit = FIT.get(str(n), [0, 0, 220]); cx, cy, far = fit; ka = 330/far
        for tag, P in TONES.items():
            p = f'{fo}/頭像_1080方_{tag}'; open(p+'.svg', 'w').write(avatar_svg(n, P, True, ka, (cx, cy))); add(svg=p+'.svg', png=p+'.png', w=1080, h=1080, kind='avatar', n=n, tag=tag)
            for sub, suf in ((False, '字標'), (True, '字標含副標')):
                for bg in (True, False):
                    sv, W, Hh = wm_svg(n, P, sub, bg, fit=fit, **DEFAULT); p = f'{fo}/{suf}_{"" if bg else "透明_"}{tag}'
                    open(p+'.svg', 'w').write(sv); add(svg=p+'.svg', png=p+'.png', w=W, h=Hh, kind='wm', n=n, tag=tag, transparent=not bg)
        N = TONES['夜版']
        for vn, (font, dotted) in VARIANTS.items():
            sv, W, Hh = wm_svg(n, N, True, True, font, dotted, fit); p = f'{fo}/字標變體_夜版_{vn}'
            open(p+'.svg', 'w').write(sv); add(svg=p+'.svg', png=p+'.png', w=W, h=Hh, kind='var', n=n, tag=vn)
        # 檢查用（透明、分層）
        open(f'{CHK}/{n}fit.svg', 'w').write(avatar_svg(n, N, False, 1.0)); add(svg=f'{CHK}/{n}fit.svg', png=f'{CHK}/{n}fit.png', w=1080, h=1080, transparent=True, kind='fit', n=n)
        open(f'{CHK}/{n}av.svg', 'w').write(avatar_svg(n, N, False, ka, (cx, cy)))
        for lay in ('a', 'q'): add(svg=f'{CHK}/{n}av.svg', png=f'{CHK}/{n}av_{lay}.png', w=1080, h=1080, transparent=True, show=[lay], kind='chk', n=n)
        for font in ('serif', 'sans'):
            sv, W, Hh = wm_svg(n, N, True, False, font, True, fit); open(f'{CHK}/{n}wm_{font}.svg', 'w').write(sv)
            for lay in ('sym', 'txt', 'sub'):
                add(svg=f'{CHK}/{n}wm_{font}.svg', png=f'{CHK}/{n}wm_{font}_{lay}.png', w=W, h=Hh, transparent=True, show=([lay, 'a', 'q'] if lay == 'sym' else [lay]), kind='chk', n=n)
    json.dump(dict(jobs=jobs), open('jobs.json', 'w'), ensure_ascii=False); print(len(jobs))
