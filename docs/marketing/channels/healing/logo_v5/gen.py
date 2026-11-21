# 「我們這一代」LOGO v5：12 款全新（字體設計、剪紙、單線、疊字樓、幾何、書封、手繪、徽章、圖表、像素、年輪、便利貼）
# 全部自繪向量，不用 AI 圖、比比、吉祥物；字型只用 ~/.fonts 的 Noto Sans/Serif CJK TC 與霞鶩文楷（OFL）
# 重跑：python3 gen.py && node render.js && python3 compose.py
import json, math, os, random
from PIL import Image, ImageDraw, ImageFont
H = os.path.dirname(os.path.abspath(__file__)); os.chdir(H)
SANS = "'Noto Sans CJK TC',sans-serif"; SERIF = "'Noto Serif CJK TC',serif"; KAI = "'LXGW WenKai TC',serif"
TONES = {  # 色調：底、主字、線、暖光（acc）、深底（deep）
 '霧紫灰': dict(bg='#4A4454', ink='#F3EFF5', line='#ABA0B5', acc='#F2D88E', deep='#3A3544'),
 '深夜藍': dict(bg='#1F2A3A', ink='#F1EBDD', line='#8FA3BC', acc='#F0C987', deep='#161E2B'),
 '水泥暖灰': dict(bg='#56524D', ink='#F3EEE6', line='#BDB5A9', acc='#F3A93C', deep='#43403B'),
 '灰綠': dict(bg='#3E4A44', ink='#EFEBDD', line='#A6B8AC', acc='#E3C98A', deep='#2F3934'),
 '米白紙': dict(bg='#F1ECE3', ink='#26221F', line='#6B645C', acc='#C8372D', deep='#E2DACB'),
 '黑底朱': dict(bg='#1B1A19', ink='#EDE6D8', line='#8E877C', acc='#E0452B', deep='#100F0F'),
 '單色黑': dict(bg='#FFFFFF', ink='#111111', line='#111111', acc='#111111', deep='#FFFFFF', mono=1),
 '單色白': dict(bg='#111111', ink='#FFFFFF', line='#FFFFFF', acc='#FFFFFF', deep='#111111', mono=1),
}
def T(x, y, s, fs, fam, col, w=700, ls=0, anchor='middle', id=None, extra=''):
    i = f' id="{id}" data-fs="{fs}"' if id else ''
    return f'<text{i} x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-weight="{w}" font-size="{fs}" letter-spacing="{ls}" text-anchor="{anchor}" fill="{col}" {extra}>{s}</text>'
def pth(d, w, col, extra='', fill='none'):
    return f'<path d="{d}" fill="{fill}" stroke="{col}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round" {extra}/>'
def ring(R, seed, amp=.025, n=160, a0=0, a1=360, ph=0):
    rnd = random.Random(seed); p = [rnd.uniform(0, 6.28) for _ in range(3)]
    pts = []
    for k in range(n+1):
        a = math.radians(a0 + (a1-a0)*k/n); r = R*(1 + amp*math.sin(2*a+p[0]) + amp*.6*math.sin(3*a+p[1]) + amp*.4*math.sin(5*a+p[2]+ph))
        pts.append((r*math.cos(a), r*math.sin(a)))
    return 'M' + ' L'.join(f'{x:.1f} {y:.1f}' for x, y in pts)
def svg(w, h, bg, inner, defs=''):
    b = f'<rect width="{w}" height="{h}" fill="{bg}"/>' if bg else ''
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><defs>{defs}</defs>{b}{inner}</svg>'
def pix(ch, g, fs, thr=110, bold=True):
    f = ImageFont.truetype(os.path.expanduser('~/.fonts/NotoSansCJKtc-%s.otf' % ('Bold' if bold else 'Regular')), fs)
    im = Image.new('L', (g, g), 0); d = ImageDraw.Draw(im); bb = d.textbbox((0, 0), ch, font=f)
    d.text(((g-(bb[2]-bb[0]))//2-bb[0], (g-(bb[3]-bb[1]))//2-bb[1]), ch, font=f, fill=255)
    a = im.load(); return [(x, y) for y in range(g) for x in range(g) if a[x, y] > thr]

# ===== 1 代·薪資線（字體設計）=====
def g_dai(P, w=58):
    c = P['ink']
    s = pth('M-175 -330 C-215 -250 -270 -180 -335 -120', w, c) + pth('M-240 -215 L-240 345', w, c)
    s += pth('M-90 -70 H300', w, c) + pth('M165 -300 L250 -240', w, c)
    s += pth('M0 -320 C30 -120 90 140 200 300 C235 348 295 330 332 232', w, c)
    s += f'<circle cx="362" cy="165" r="{w*.62:.0f}" fill="{P["acc"]}"/>'
    return s
def sym1(P): return f'<g transform="scale(.9)">{g_dai(P)}</g>'
def wm1(P, tr=False):
    k = .175; W = 80 + 4*130 + 170 + 60; x0 = 80 + 4*130 + 16
    s = T(80, 200+.38*120, '我們這一', 120, SANS, P['ink'], 700, 10, 'start', 'w_txt')
    s += f'<g id="w_sym" transform="translate({x0+60} 200) scale({k})"><g transform="translate(0 0)">{g_dai(P, 58)}</g></g>'.replace('<g transform="translate(0 0)">', '<g>')
    return W, 400, s, [('dis', 'w_txt', 'w_sym')]
# ===== 2 門半開（剪紙疊層）=====
def sym2(P):
    m = P.get('mono'); f = '' if m else 'filter="url(#sh)"'
    op = P['bg'] if m else P['deep']
    s = f'<rect x="-240" y="-340" width="480" height="680" rx="10" fill="{P["line"]}" {f}/>'
    s += f'<rect x="-190" y="-290" width="380" height="580" fill="{op}"/>'
    if not m: s += f'<polygon points="-110,300 180,300 220,356 -140,356" fill="{P["acc"]}" opacity=".45"/>'
    s += f'<polygon points="-70,-250 120,-250 120,250 -70,250" fill="{P["acc"]}"/>'
    s += f'<polygon points="-190,-290 -70,-250 -70,250 -190,290" fill="{P["ink"]}" {f}/>'
    s += f'<polygon points="190,-290 120,-262 120,262 190,290" fill="{P["ink"]}" {f}/>'
    s += f'<circle cx="-92" cy="12" r="11" fill="{op if m else P["line"]}"/>'
    return s
SH = '<filter id="sh" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="9" stdDeviation="8" flood-color="#000" flood-opacity=".38"/></filter>'
def wm2(P, tr=False):
    s = f'<g id="w_sym" transform="translate(190 200) scale(.44)">{sym2(P)}</g>'
    s += T(360, 200+.38*120, '我們這一代', 120, SANS, P['ink'], 700, 12, 'start', 'w_txt')
    return 1080, 400, s, [('dis', 'w_sym', 'w_txt')]
# ===== 3 一筆畫窗（單線）=====
def sym3(P):
    h, pitch, sw = 75, 206, 24; c = P['line']; d = f'M-341 -206 H-281'
    cols = [-pitch, 0, pitch]; rows = [-pitch, 0, pitch]
    for ri, cy in enumerate(rows):
        seq = cols if ri % 2 == 0 else cols[::-1]
        for cx in seq:
            if ri % 2 == 0:
                d += f' L{cx-h} {cy-h} L{cx+h} {cy-h} L{cx+h} {cy+h} L{cx-h} {cy+h} L{cx-h} {cy} L{cx+h} {cy}'
            else:
                d += f' L{cx+h} {cy-h} L{cx-h} {cy-h} L{cx-h} {cy+h} L{cx+h} {cy+h} L{cx+h} {cy} L{cx-h} {cy}'
            if cx != seq[-1]: d += f' L{cx+(206-2*h)*(1 if ri%2==0 else -1)+ (h if ri%2==0 else -h)} {cy}'
        if ri < 2:
            ex = 281 if ri % 2 == 0 else -281; bx = 336 if ri % 2 == 0 else -336
            # 行尾：從出口往外拐，再回到下一列同側視窗的入口
            d += f' L{bx} {cy} L{bx} {rows[ri+1]} L{ex} {rows[ri+1]}'
    # 轉列後下一列從入口側開始：上面寫法已把游標移到入口，需要避免重複 L 到起點（視覺上同點）
    s = f'<rect x="{pitch-h}" y="{pitch-h}" width="{2*h}" height="{2*h}" fill="{P["acc"]}"/>'
    s += pth(d, sw, c)
    return s
def wm3(P, tr=False):
    ws, gap, x0, cy = 170, 60, 100, 200; n = 5; s = ''; chk = []
    for i, ch in enumerate('我們這一代'):
        x = x0 + i*(ws+gap); lit = i == 4
        if i: s += f'<line x1="{x-gap}" y1="{cy}" x2="{x}" y2="{cy}" stroke="{P["line"]}" stroke-width="10" stroke-linecap="round"/>'
        s += f'<rect id="w_win{i}" x="{x}" y="{cy-ws/2}" width="{ws}" height="{ws}" rx="6" fill="{P["acc"] if lit else P["bg"]}" stroke="{P["line"]}" stroke-width="10"/>'
        s += T(x+ws/2, cy+.38*104, ch, 104, SANS, P['bg'] if lit else P['ink'], 700, 0, 'middle', f'w_t{i}')
        chk.append(('in', f'w_t{i}', f'w_win{i}'))
    return x0*2 + n*ws + (n-1)*gap, 400, s, chk
# ===== 4 疊字樓（印刷疊字）=====
def sym4(P):
    fw, fh = 215, 335; s = f'<rect id="a_b" x="-{fw}" y="-{fh}" width="{2*fw}" height="{2*fh}" fill="none" stroke="{P["line"]}" stroke-width="18" stroke-linejoin="round"/>'
    fl = 2*fh/3; chk = []
    s += f'<rect x="-{fw-9}" y="{-fl/2+(-fl)+0:.0f}" width="{2*fw-18}" height="{fl-0:.0f}" fill="none"/>'
    s += f'<rect x="-{fw-9}" y="{-fl/2:.0f}" width="{2*fw-18}" height="{fl:.0f}" fill="{P["acc"]}"/>'
    s += f'<line x1="-{fw}" y1="{-fl/2:.0f}" x2="{fw}" y2="{-fl/2:.0f}" stroke="{P["line"]}" stroke-width="12"/><line x1="-{fw}" y1="{fl/2:.0f}" x2="{fw}" y2="{fl/2:.0f}" stroke="{P["line"]}" stroke-width="12"/>'
    for i, ch in enumerate('這一代'):
        cy = (i-1)*fl; s += T(0, cy+.38*160, ch, 160, SANS, P['bg'] if i == 1 else P['ink'], 700, 0, 'middle', f'a_t{i}')
    return s
def wm4(P, tr=False):
    s = T(90, 200+.38*140, '我們', 140, SANS, P['ink'], 700, 14, 'start', 'w_txt')
    bx, by, bw, bh = 450, 52, 260, 296; fl = bh/3
    s += f'<rect id="w_b" x="{bx}" y="{by}" width="{bw}" height="{bh}" fill="none" stroke="{P["line"]}" stroke-width="10" stroke-linejoin="round"/>'
    s += f'<rect x="{bx+5}" y="{by+fl:.1f}" width="{bw-10}" height="{fl:.1f}" fill="{P["acc"]}"/>'
    for k in (1, 2): s += f'<line x1="{bx}" y1="{by+k*fl:.1f}" x2="{bx+bw}" y2="{by+k*fl:.1f}" stroke="{P["line"]}" stroke-width="8"/>'
    chk = [('dis', 'w_txt', 'w_b')]
    for i, ch in enumerate('這一代'):
        s += T(bx+bw/2, by+(i+.5)*fl+.38*78, ch, 78, SANS, P['bg'] if i == 1 else P['ink'], 700, 0, 'middle', f'w_t{i}'); chk.append(('in', f'w_t{i}', 'w_b'))
    return bx+bw+90, 400, s, chk
# ===== 5 日出十分之一（幾何海報）=====
def sym5(P):
    sh = -120; c = P['line']; s = ''; hy = 40+sh; R = 255
    cy = hy - 42 + R   # 圓只露出頂端 42px（約直徑的十分之一）
    s += f'<clipPath id="cp5"><rect x="-400" y="-400" width="800" height="{hy+400}"/></clipPath>'
    s += f'<circle cx="0" cy="{cy}" r="{R}" fill="{P["acc"]}" clip-path="url(#cp5)"/>'
    for a in range(20, 161, 20):
        r0, r1 = 185, 245; ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        s += pth(f'M{r0*ca:.1f} {hy-20-r0*sa:.1f} L{r1*ca:.1f} {hy-20-r1*sa:.1f}', 22, P['acc'])
    for k, wd in enumerate((640, 500, 360, 220, 100)):
        s += f'<rect x="{-wd/2}" y="{hy+k*52}" width="{wd}" height="30" rx="4" fill="{c}"/>'
    return s
def wm5(P, tr=False):
    tx, W = 100, 856; s = T(tx, 160+.38*120, '我們這一代', 120, SANS, P['ink'], 700, 14, 'start', 'w_txt')
    hy = 285; R = 121.7
    s += f'<clipPath id="cp5w"><rect x="0" y="0" width="{W}" height="{hy}"/></clipPath><circle id="w_sun" cx="678" cy="{255+R:.1f}" r="{R}" fill="{P["acc"]}" clip-path="url(#cp5w)"/>'
    s += f'<rect x="{tx}" y="{hy}" width="656" height="10" fill="{P["line"]}"/>'
    for k, (y, a, b) in enumerate(((309, 160, 640), (324, 300, 520))): s += f'<rect x="{tx+a-100}" y="{y}" width="{b-a}" height="6" fill="{P["line"]}" opacity=".55"/>'
    return W, 380, s, [('dis', 'w_txt', 'w_sun')]
# ===== 6 書封直排（書封）=====
def seal(P, cx, cy, sz, fs, tag):
    m = P.get('mono')
    if m: return f'<rect x="{cx-sz/2}" y="{cy-sz/2}" width="{sz}" height="{sz}" fill="{P["bg"]}"/>' + T(cx, cy+.38*fs, '觀', fs, SERIF, P['ink'], 700, 0, 'middle', tag)
    return f'<rect x="{cx-sz/2}" y="{cy-sz/2}" width="{sz}" height="{sz}" rx="6" fill="{P["acc"]}"/>' + T(cx, cy+.38*fs, '觀', fs, SERIF, P['bg'], 700, 0, 'middle', tag)
def sym6(P):
    s = f'<rect id="a_cv" x="-260" y="-320" width="520" height="640" rx="6" fill="{P["ink"]}"/>'
    s += f'<rect x="-236" y="-296" width="472" height="592" fill="none" stroke="{P["bg"]}" stroke-width="4" opacity=".75"/>'
    chk = []
    for i, ch in enumerate('我們這一代'):
        s += T(105, -222+i*108+.38*98, ch, 98, SERIF, P['bg'], 700, 0, 'middle', f'a_t{i}')
    s += f'<line x1="10" y1="-262" x2="10" y2="262" stroke="{P["bg"]}" stroke-width="3" opacity=".6"/>'
    s += seal(P, -120, 178, 112, 78, 'a_seal')
    return s
def wm6(P, tr=False):
    x0 = 110; fs = 130; s = ''
    s += T(x0, 200+.38*fs, '我們這一代', fs, SERIF, P['ink'], 700, 18, 'start', 'w_txt')
    s += f'<rect x="{x0}" y="92" width="885" height="5" fill="{P["line"]}"/><rect x="{x0}" y="106" width="885" height="2" fill="{P["line"]}"/><rect x="{x0}" y="292" width="885" height="2" fill="{P["line"]}"/><rect x="{x0}" y="303" width="885" height="5" fill="{P["line"]}"/>'
    s += seal(P, 945, 200, 100, 64, 'w_seal')
    return 1105, 400, s, [('dis', 'w_txt', 'w_seal')]
# ===== 7 重疊圈（手繪）=====
def sym7(P):
    m = P.get('mono'); s = ''; R = 225; dx = 115
    L = ring(R, 3); Rr = ring(R, 8)
    s += f'<clipPath id="cp7"><path d="{L}" transform="translate({-dx} 0)"/></clipPath>'
    if m:
        s += '<g clip-path="url(#cp7)"><g transform="translate(%d 0)">' % dx
        s += f'<circle r="{R}" fill="{P["bg"]}"/>' + ''.join(f'<line x1="-300" y1="{y}" x2="300" y2="{y}" stroke="{P["ink"]}" stroke-width="9" transform="rotate(-35)"/>' for y in range(-300, 301, 30)) + '</g></g>'
    else:
        s += f'<g clip-path="url(#cp7)"><path d="{Rr}" transform="translate({dx} 0)" fill="{P["acc"]}"/></g>'
    for cx, seed in ((-dx, 3), (dx, 8)):
        for k, sd in enumerate((seed, seed+20)):
            s += pth(ring(R, sd, .022, 160, 0, 372 if k else 360), 15, P['line'], f'transform="translate({cx} {2*k})"')
    return s
def wm7(P, tr=False):
    s = f'<g transform="translate(240 200) scale(.46)">{sym7(P)}</g><rect id="w_sym" x="{240-340*.46}" y="{200-240*.46}" width="{680*.46}" height="{480*.46}" fill="none"/>'
    s += T(440, 200+.38*120, '我們這一代', 120, SANS, P['ink'], 700, 12, 'start', 'w_txt')
    return 1170, 400, s, [('dis', 'w_sym', 'w_txt')]
# ===== 8 徽章 00（復古徽章）=====
def sym8(P):
    rb = 345; s = pth('M-0 405 A405 405 0 1 1 0 -405 A405 405 0 1 1 0 405', 15, P['line'], '', 'none')
    s += pth('M0 318 A318 318 0 1 1 0 -318 A318 318 0 1 1 0 318', 6, P['line'])
    s += f'<path id="rp" d="M0 {rb} A{rb} {rb} 0 1 1 0 {-rb} A{rb} {rb} 0 1 1 0 {rb}" fill="none"/>'
    s += f'<text font-family="{SANS}" font-weight="700" font-size="56" fill="{P["ink"]}" text-anchor="middle"><textPath href="#rp" startOffset="50%" textLength="2060" lengthAdjust="spacing">我們這一代 ・ 二〇〇〇後出生 ・ 一位觀察家的紀錄 ・</textPath></text>'
    for cx in (-112, 112): s += f'<circle cx="{cx}" cy="0" r="92" fill="none" stroke="{P["ink"]}" stroke-width="30"/>'
    s += f'<circle cx="112" cy="0" r="40" fill="{P["acc"]}"/>'
    return s
def sym8s(P):   # 字標用的簡化徽章（無環字）
    s = pth('M0 405 A405 405 0 1 1 0 -405 A405 405 0 1 1 0 405', 26, P['line']) + pth('M0 318 A318 318 0 1 1 0 -318 A318 318 0 1 1 0 318', 12, P['line'])
    for cx in (-112, 112): s += f'<circle cx="{cx}" cy="0" r="92" fill="none" stroke="{P["ink"]}" stroke-width="34"/>'
    return s + f'<circle cx="112" cy="0" r="42" fill="{P["acc"]}"/>'
def wm8(P, tr=False):
    s = f'<g id="w_sym" transform="translate(240 200) scale(.38)">{sym8s(P)}</g>'
    s += T(455, 200+.38*120, "我們這一代", 120, SERIF, P['ink'], 700, 12, 'start', 'w_txt')
    return 1135, 400, s, [('dis', 'w_sym', 'w_txt')]
# ===== 9 剪刀差（編輯圖表線）=====
def sym9(P):
    hs = 'M-330 150 C-120 140 110 20 330 -220'; sal = 'M-330 150 L330 118'
    s = f'<clipPath id="cp9"><path d="{hs} L330 118 Z"/></clipPath><g clip-path="url(#cp9)">'
    s += ''.join(f'<line x1="-400" y1="{y}" x2="400" y2="{y}" stroke="{P["line"]}" stroke-width="8" opacity="{1 if P.get("mono") else .75}" transform="rotate(-35)"/>' for y in range(-500, 501, 30)) + '</g>'
    s += pth(sal, 30, P['line']) + pth(hs, 30, P['ink'])
    s += f'<circle cx="330" cy="118" r="40" fill="{P["acc"]}"/>'
    return s
def wm9(P, tr=False):
    s = f'<g transform="translate(215 200) scale(.46)">{sym9(P)}</g><rect id="w_sym" x="{215-345*.46}" y="{200-235*.46}" width="{690*.46}" height="{410*.46}" fill="none"/>'
    s += T(430, 200+.38*120, '我們這一代', 120, SANS, P['ink'], 700, 12, 'start', 'w_txt')
    return 1160, 400, s, [('dis', 'w_sym', 'w_txt')]
# ===== 10 像素字 =====
def pixrects(cells, u, ox, oy, acc_cells, P, gap=.1):
    s = ''
    for x, y in cells:
        c = P['acc'] if (x, y) in acc_cells else P['ink']
        s += f'<rect x="{ox+x*u+u*gap/2:.1f}" y="{oy+y*u+u*gap/2:.1f}" width="{u*(1-gap):.1f}" height="{u*(1-gap):.1f}" rx="{u*.12:.1f}" fill="{c}"/>'
    return s
def tail(cells, g):
    xs = [x for x, y in cells if y > g*.55]; mx = max(xs); return {(x, y) for x, y in cells if x >= mx-2 and y > g*.45 and y < g*.92}
def sym10(P):
    g = 32; cells = pix('代', g, 31, 100); u = 17; acc = tail(cells, g)
    return pixrects(cells, u, -g*u/2, -g*u/2, acc, P)
def wm10(P, tr=False):
    g, u, gp = 24, 6, 20; s = ''
    for i, ch in enumerate('我們這一代'):
        cells = pix(ch, g, 24, 105); acc = tail(cells, g) if ch == '代' else set()
        s += pixrects(cells, u, 100+i*(g*u+gp), 200-g*u/2, acc, P)
    return 200 + 5*g*u + 4*gp, 400, s, []
# ===== 11 年輪 =====
def sym11(P):
    s = ''
    for i, R in enumerate((50, 115, 180, 245, 310, 372)):
        s += pth(ring(R, 40+i, .03 if i else .02, 200), 26 if i < 5 else 26, P['line'])
    s += pth(ring(372, 45, .03, 200, 200, 300), 38, P['acc'])
    return s + f'<circle r="20" fill="{P["ink"]}"/>'
def wm11(P, tr=False):
    s = f'<g id="w_sym" transform="translate(215 200) scale(.44)">{sym11(P)}</g>'
    s += T(440, 200+.38*120, '我們這一代', 120, SANS, P['ink'], 700, 12, 'start', 'w_txt')
    return 1170, 400, s, [('dis', 'w_sym', 'w_txt')]
# ===== 12 便利貼 =====
def note(P, sz, txt, fs, tid, rot=-5, shadow=True):
    m = P.get('mono'); h = sz/2; s = f'<g transform="rotate({rot})">'
    if shadow and not m: s += f'<rect x="{-h+sz*.03}" y="{-h+sz*.04}" width="{sz}" height="{sz}" fill="#000" opacity=".28"/>'
    s += f'<rect id="{tid}n" x="{-h}" y="{-h}" width="{sz}" height="{sz}" fill="{P["acc"]}"/>'
    if not m: s += f'<polygon points="{h-sz*.14},{h} {h},{h-sz*.14} {h},{h}" fill="#000" opacity=".2"/>'
    s += T(0, .33*fs, txt, fs, KAI, P['bg'], 400, 0, 'middle', tid)
    s += f'<rect x="{-sz*.16}" y="{-h-sz*.055}" width="{sz*.32}" height="{sz*.1}" fill="{P["line"]}" opacity=".78" transform="rotate(3)"/>'
    return s + '</g>'
def sym12(P): return note(P, 540, '我也是', 150, 'a_t')
def wm12(P, tr=False):
    s = f'<g transform="translate(200 200)">{note(P, 230, "我也是", 62, "w_nt")}</g>'
    s += T(400, 200+.33*124, '我們這一代', 124, KAI, P['ink'], 400, 12, 'start', 'w_txt')
    return 1140, 400, s, [('dis', 'w_nt', 'w_txt')]

D = [
 (1, '代·薪資線', '字體設計', sym1, wm1, '「代」的斜鉤是一條往下沉的薪資線，尾端翹起、迸出一點光', [], [('dis', 'w_txt', 'w_sym')]),
 (2, '門半開', '剪紙疊層', sym2, wm2, '「們」的門半開，縫裡漏出暖光：同代人的日子還有出口', [], []),
 (3, '一線串起的窗', '單線一筆畫', sym3, wm3, '一條線串起許多扇窗＝許多人過著相似的日子，最後一扇亮了', [], []),
 (4, '這一代·大樓', '印刷疊字', sym4, wm4, '「這」「一」「代」三字疊成一棟樓，只有一層亮著', [], []),
 (5, '十分之一的日出', '幾何海報', sym5, wm5, '日出被地平線壓住，只露出十分之一，但已經是天亮', [], []),
 (6, '觀察筆記書封', '書封直排', sym6, wm6, '像一本觀察筆記的書封，朱印「觀」是觀察家的落款', [], []),
 (7, '我與你的重疊', '手繪重疊圈', sym7, wm7, '兩個手畫的圈，重疊那一小塊亮起：同代人才懂的同感', [], []),
 (8, '00 徽章', '復古徽章', sym8, wm8, '兩個零是 2000 後的記號，右邊那個零裡亮著一點光', [], []),
 (9, '剪刀差', '編輯圖表線', sym9, wm9, '房價線往上衝、薪水線幾乎平，夾出的斜線區就是處境，線尾一點光', [], []),
 (10, '點陣的代', '像素點陣字', sym10, wm10, '2000 後的第一批字是點陣字：每一格都小，連起來才成為我們，鉤尾一格亮', [], []),
 (11, '最新一圈', '木刻年輪', sym11, wm11, '年輪一圈就是一代，我們是最外那圈剛長出來的，一角亮著', [], []),
 (12, '我也是', '手寫便利貼', sym12, wm12, '同代人互相留下的那句「我也是」，貼在冷牆上，一張暖黃', [], []),
]
jobs = []; meta = []
for n, nm, sty, fs_, fw_, mean, _a, _w in D:
    fo = f'{n:02d}_{nm}'; os.makedirs(fo, exist_ok=True)
    meta.append(dict(n=n, name=nm, style=sty, meaning=mean, dir=fo))
    for tn, P in TONES.items():
        defs = SH
        a = svg(1080, 1080, P['bg'], f'<g transform="translate(540 540)">{fs_(P)}</g>', defs)
        open(f'{fo}/頭像_1080_{tn}.svg', 'w', encoding='utf-8').write(a)
        jobs.append(dict(n=n, kind='avatar', tag=tn, svg=f'{fo}/頭像_1080_{tn}.svg', png=f'{fo}/頭像_1080_{tn}.png', w=1080, h=1080, ids=['a_b', 'a_t0', 'a_t1', 'a_t2', 'a_t', 'a_seal', 'a_cv']))
        W, Hh, inner, chk = fw_(P)
        w = svg(W, Hh, P['bg'], inner, defs); open(f'{fo}/字標_{tn}.svg', 'w', encoding='utf-8').write(w)
        ids = sorted({i for c in chk for i in c[1:]})
        jobs.append(dict(n=n, kind='wm', tag=tn, svg=f'{fo}/字標_{tn}.svg', png=f'{fo}/字標_{tn}.png', w=W, h=Hh, ids=ids, chk=chk))
        if tn == '霧紫灰':
            open(f'{fo}/字標_透明_{tn}.svg', 'w', encoding='utf-8').write(svg(W, Hh, None, inner, defs))
            jobs.append(dict(n=n, kind='wmT', tag=tn, svg=f'{fo}/字標_透明_{tn}.svg', png=f'{fo}/字標_透明_{tn}.png', w=W, h=Hh, ids=[], transparent=True))
json.dump(dict(jobs=jobs, meta=meta, tones=TONES), open('jobs.json', 'w', encoding='utf-8'), ensure_ascii=False)
print('jobs', len(jobs))
