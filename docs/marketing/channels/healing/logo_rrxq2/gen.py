# 「日日小晴」LOGO 第二輪 12 款（2026-11-05）：全新方向、明亮悠閒色調、全自繪向量，不用 AI 圖／比比／吉祥物／品牌商標
# 字型只用 ~/.fonts 的 Noto Sans/Serif CJK TC 與霞鶩文楷（OFL）
# 重跑：python3 gen.py && node render.js && python3 compose.py
import json, math, os, random
from PIL import ImageFont
H = os.path.dirname(os.path.abspath(__file__)); os.chdir(H)
CHK = '/tmp/claude-0/-home-user-tw-rotation/ce50d787-1067-5482-ab44-99dc39a48890/scratchpad/rrxq2_chk'
os.makedirs(CHK, exist_ok=True)
FD = os.path.expanduser('~/.fonts/')
FONTS = {  # 鍵：(CSS 家族, 字重, PIL 檔)
 'sans': ("'Noto Sans CJK TC',sans-serif", 700, FD+'NotoSansCJKtc-Bold.otf'),
 'serif': ("'Noto Serif CJK TC',serif", 700, FD+'NotoSerifCJKtc-Bold.otf'),
 'kai': ("'LXGW WenKai TC',serif", 400, FD+'LXGWWenKaiTC-Regular.ttf'),
}
# 色調：bg 底、S 太陽色、M 主色（大面積）、soft 淺色、ink 字與線
TONES = {
 '奶油晨光': dict(bg='#FFF6E5', S='#F2A65A', M='#F7D9A6', soft='#FFE9C7', ink='#3A3A3A', G='#7FA06A', C='#CDB9A0', T='#C98B5E'),
 '晴空淡藍': dict(bg='#EAF4FB', S='#F6C85F', M='#6FB1E0', soft='#CFE6F6', ink='#1F3C54', G='#5E9E7A', C='#8DB6D8', T='#C98B5E'),
 '抹茶午後': dict(bg='#EEF2E6', S='#F6C85F', M='#8DAA7B', soft='#D6E2CA', ink='#2F3F29', G='#5F8450', C='#A9B79A', T='#C98B5E'),
 '深色模式': dict(bg='#1E1A16', S='#F2A65A', M='#7A5A38', soft='#2E261E', ink='#FFF6E5', G='#8DB07A', C='#6B5C4C', T='#B9805A'),
 '單色黑': dict(bg='#FFFFFF', S='#111111', M='#FFFFFF', soft='#FFFFFF', ink='#111111', G='#111111', C='#111111', T='#111111', mono=1),
 '單色白': dict(bg='#111111', S='#FFFFFF', M='#111111', soft='#111111', ink='#FFFFFF', G='#FFFFFF', C='#FFFFFF', T='#FFFFFF', mono=1),
}
FIT = json.load(open('fit.json')) if os.path.exists('fit.json') else {}
SUB = '每天，一小段晴'
NAME = '日日小晴'

def stroke(P, w, force=False):
    return f'stroke="{P["ink"]}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"' if (force or P.get('mono')) else ''
def line(x1, y1, x2, y2, w, col):
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col}" stroke-width="{w}" stroke-linecap="round"/>'
def rays(cx, cy, r1, r2, n, w, col, a0=0, a1=360):
    s = ''
    for k in range(n):
        a = math.radians(a0 + (a1-a0)*k/(n if a1-a0 == 360 else max(n-1, 1)))
        s += line(cx+r1*math.cos(a), cy+r1*math.sin(a), cx+r2*math.cos(a), cy+r2*math.sin(a), w, col)
    return s
def cloud_parts(cx, by, s):
    return (f'<rect x="{cx-110*s:.1f}" y="{by-50*s:.1f}" width="{220*s:.1f}" height="{50*s:.1f}" rx="{25*s:.1f}"/>'
            f'<circle cx="{cx-45*s:.1f}" cy="{by-52*s:.1f}" r="{45*s:.1f}"/><circle cx="{cx+22*s:.1f}" cy="{by-72*s:.1f}" r="{66*s:.1f}"/>'
            f'<circle cx="{cx+85*s:.1f}" cy="{by-38*s:.1f}" r="{34*s:.1f}"/>')
def cloud(cx, by, s, fill, ink=None, ow=0, extra=''):
    o = ''
    if ink and ow: o = f'<g fill="{ink}" stroke="{ink}" stroke-width="{2*ow}" stroke-linejoin="round" {extra}>{cloud_parts(cx, by, s)}</g>'
    return o + f'<g fill="{fill}" {extra}>{cloud_parts(cx, by, s)}</g>'
def gp(ch, kind, fs, cx, cy):
    f = ImageFont.truetype(FONTS[kind][2], fs); l, t, r, b = f.getbbox(ch, anchor='ls'); return cx-(l+r)/2, cy-(t+b)/2
def TX(s, kind, fs, x, y, col, anchor='start', ls=0, extra='', bold=0):
    fam, w, _ = FONTS[kind]
    st = f'stroke="{col}" stroke-width="{bold}" stroke-linejoin="round"' if bold else ''
    return f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-weight="{w}" font-size="{fs}" letter-spacing="{ls}" text-anchor="{anchor}" fill="{col}" {st} {extra}>{s}</text>'
def glyph(ch, kind, fs, cx, cy, col, bold=0):
    x, y = gp(ch, kind, fs, cx, cy); return TX(ch, kind, fs, x, y, col, bold=bold)
def L(name, inner): return f'<g data-layer="{name}">{inner}</g>'
def lightfill(P): return 'url(#hatch)' if P.get('mono') else P['S']
def wob(cx, cy, R, seed, amp=.03, n=90, a0=0, a1=360):
    rnd = random.Random(seed); p = [rnd.uniform(0, 6.28) for _ in range(3)]; pts = []
    for k in range(n+1):
        a = math.radians(a0+(a1-a0)*k/n); r = R*(1+amp*math.sin(2*a+p[0])+amp*.6*math.sin(3*a+p[1])+amp*.4*math.sin(5*a+p[2]))
        pts.append((cx+r*math.cos(a), cy+r*math.sin(a)))
    return 'M'+' L'.join(f'{x:.1f} {y:.1f}' for x, y in pts)

SHADOW = '<filter id="sh" x="-25%" y="-25%" width="150%" height="150%"><feDropShadow dx="0" dy="10" stdDeviation="9" flood-color="#5A4636" flood-opacity=".28"/></filter>'
def defs(P):
    return (f'<pattern id="hatch" width="18" height="18" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="18" height="18" fill="{P["bg"]}"/>'
            f'<line x1="0" y1="0" x2="0" y2="18" stroke="{P["ink"]}" stroke-width="6"/></pattern>{SHADOW}'
            '<filter id="rough" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency=".05" numOctaves="2" seed="4"/><feDisplacementMap in="SourceGraphic" scale="9"/></filter>')

# ===== 第二輪 12 款符號（座標約 ±270，之後由 fit.json 自動縮放）=====
def BEAM(P): return P['bg'] if P.get('mono') else P['S']
def dstroke(d, P, w_out, w_in, inner=None, extra=''):
    """雙層描線：外層深色、內層亮色，像一道有輪廓的光。"""
    inner = inner or BEAM(P)
    return (f'<path d="{d}" fill="none" stroke="{P["ink"]}" stroke-width="{w_out}" stroke-linecap="round" stroke-linejoin="round" {extra}/>'
            f'<path d="{d}" fill="none" stroke="{inner}" stroke-width="{w_in}" stroke-linecap="round" stroke-linejoin="round" {extra}/>')

# ===== 1 小字三光（字體設計）：太陽圓裡的「小」，三筆像三道往下灑的光 =====
def s1(P):
    ink = P['ink']; cy = 0; R = 178
    sun = f'<circle cx="0" cy="{cy}" r="{R}" fill="{P["bg"] if P.get("mono") else P["S"]}" stroke="{ink}" stroke-width="22"/>'
    sun += rays(0, cy, R+44, R+84, 12, 18, ink)
    # 「小」：中間一豎帶鉤，左右兩筆斜落，筆畫由上往下漸寬，像光束
    g = f'<path d="M 0 -112 L 0 92 C 0 126 -18 140 -54 130" fill="none" stroke="{ink}" stroke-width="50" stroke-linecap="round" stroke-linejoin="round"/>'
    for sgn in (-1, 1):
        g += f'<path d="M {sgn*100} -26 L {sgn*138} 40" fill="none" stroke="{ink}" stroke-width="46" stroke-linecap="round"/>'
    return L('a', sun) + L('b', f'<g transform="translate(0 6) scale(.85)">{g}</g>')
# ===== 2 昌日倒影（色塊疊影）：兩個「日」疊成「昌」，上面是太陽，下面是水面上的倒影 =====
def s2(P):
    ink = P['ink']
    def ri(y0):
        d = f'M -72 {y0} H 72 V {y0+180} H -72 Z M -72 {y0+90} H 72'
        return f'<rect x="-72" y="{y0}" width="144" height="180" fill="{BEAM(P)}"/>' + dstroke(d, P, 46, 18, inner=BEAM(P))
    top = ri(-216) + rays(0, -126, 128, 166, 7, 15, ink, 195, 345)
    refl = (f'<mask id="mk2"><rect x="-300" y="0" width="600" height="300" fill="#fff"/>'
            + ''.join(f'<path d="M -300 {y} q 30 -12 60 0 t 60 0 t 60 0 t 60 0 t 60 0 t 60 0 t 60 0 t 60 0 t 60 0 t 60 0" fill="none" stroke="#000" stroke-width="{w}"/>' for y, w in ((78, 8), (126, 12), (174, 16), (222, 20)))
            + f'</mask><g mask="url(#mk2)" opacity="{1 if P.get("mono") else .55}">{ri(52)}</g>')
    water = f'<path d="M -230 14 q 28 -14 56 0 t 56 0 t 56 0 t 56 0 t 56 0 t 56 0 t 56 0 t 56 0" fill="none" stroke="{ink}" stroke-width="13" stroke-linecap="round"/>'
    return L('a', top) + L('b', refl) + L('c', water)
# ===== 3 蛋黃太陽吐司（貼紙）：早餐桌上的蛋黃，就是今天的一小段晴 =====
def s3(P):
    ink = P['ink']; mono = P.get('mono')
    parts = ('<rect x="-190" y="-150" width="380" height="400" rx="70"/><circle cx="-118" cy="-150" r="86"/><circle cx="118" cy="-150" r="86"/>'
             '<rect x="-190" y="-170" width="380" height="120"/>')
    def shape(fill, sw=0, sc=None, extra=''):
        sc = sc or ink
        return f'<g fill="{fill}" stroke="{sc if sw else "none"}" stroke-width="{2*sw}" stroke-linejoin="round" {extra}>{parts}</g>'
    s = ''
    if not mono:
        s += f'<g filter="url(#sh)">{shape("#FFFFFF", 40, "#FFFFFF")}</g>'
    s += shape(ink, 13)
    s += shape(P['M'] if not mono else P['bg'])
    # 吐司內框（軟麵包心）
    s += f'<g transform="translate(0 20) scale(.8)" fill="{P["soft"]}" opacity="{1 if mono else .85}">{parts}</g>'
    if mono:
        s += f'<g transform="translate(0 20) scale(.8)" fill="none" stroke="{ink}" stroke-width="7" stroke-linejoin="round">{parts}</g>'
    egg = wob(-10, 38, 128, 5, .085, n=110)
    s += f'<path d="{egg}" fill="{P["bg"] if mono else "#FFFFFF"}" stroke="{ink}" stroke-width="11" stroke-linejoin="round"/>'
    s += f'<circle cx="-4" cy="34" r="56" fill="{lightfill(P)}" stroke="{ink}" stroke-width="10"/>'
    s += f'<path d="M -28 20 q 8 -14 24 -16" fill="none" stroke="{"#FFFFFF" if not mono else P["bg"]}" stroke-width="9" stroke-linecap="round" opacity=".85"/>'
    return L('a', s)

# ===== 4 貓咪打盹（剪影）：一隻貓蜷在一小塊陽光裡 =====
def s4(P):
    ink = P['ink']
    patch = f'<polygon points="-170,128 290,128 224,268 -246,268" fill="{lightfill(P)}"/>'
    cat = (f'<g fill="{ink}" stroke="{ink}" stroke-width="18" stroke-linejoin="round">'
           '<ellipse cx="0" cy="124" rx="178" ry="98"/><ellipse cx="-4" cy="-18" rx="98" ry="86"/>'
           '<polygon points="-92,-62 -84,-168 -18,-92"/><polygon points="80,-62 72,-168 6,-92"/></g>')
    tail = f'<path d="M 176 168 C 262 170 286 84 238 38" fill="none" stroke="{ink}" stroke-width="44" stroke-linecap="round"/>'
    eyes = (f'<path d="M -66 -14 q 22 22 44 0 M 14 -14 q 22 22 44 0" fill="none" stroke="{P["bg"]}" stroke-width="9" stroke-linecap="round"/>'
            f'<path d="M -16 22 q 14 12 28 0" fill="none" stroke="{P["bg"]}" stroke-width="8" stroke-linecap="round"/>')
    return L('b', patch) + L('a', cat + tail + eyes)

# ===== 5 車窗流光（單線）：捷運車廂，窗外有一道陽光流過 =====
def s5(P):
    ink = P['ink']; w = 22
    body = f'<rect x="-190" y="-150" width="410" height="270" rx="84" fill="{P["soft"]}" stroke="{ink}" stroke-width="{w}"/>'
    for x in (-140, -36):
        body += f'<rect x="{x}" y="-104" width="84" height="104" rx="30" fill="{P["bg"]}" stroke="{ink}" stroke-width="16"/>'
    body += f'<rect x="68" y="-104" width="100" height="104" rx="32" fill="{lightfill(P)}" stroke="{ink}" stroke-width="16"/>'
    body += line(-190, 50, 220, 50, 12, ink)
    body += line(-232, 188, 254, 188, 18, ink)
    streak = ''.join(line(x1, y, -250, y, 18, P['ink'] if P.get('mono') else P['S']) for x1, y in ((-304, -92), (-330, -40), (-290, 12)))
    return L('a', body) + L('b', streak)
# ===== 6 書頁折角透光（線稿）：折起來的書角下面，透出一小顆太陽 =====
def s6(P):
    ink = P['ink']; w = 15
    sun = f'<circle cx="128" cy="-218" r="64" fill="{lightfill(P)}" stroke="{ink}" stroke-width="13"/>' + rays(128, -218, 92, 124, 6, 13, ink, -172, -8)
    page = f'<path d="M -170 -250 L 50 -250 L 170 -130 L 170 250 L -170 250 Z" fill="{P["soft"]}" stroke="{ink}" stroke-width="{w}" stroke-linejoin="round"/>'
    page += f'<path d="M 50 -250 L 50 -130 L 170 -130 Z" fill="{P["M"] if not P.get("mono") else P["bg"]}" stroke="{ink}" stroke-width="{w}" stroke-linejoin="round"/>'
    for y, x2 in ((-50, 100), (10, 100), (70, 100), (130, 20)):
        page += line(-110, y, x2, y, 12, ink)
    return f'<g transform="rotate(-5)">' + L('b', sun) + L('a', page) + '</g>'
# ===== 7 雲帶缺口（色塊拼貼）：長長的雲帶中間缺了一段，露出一小塊晴 =====
def s7(P):
    ink = P['ink']; mono = P.get('mono'); c = P['C']
    def bar(x1, x2, y, bx):
        return (f'<rect x="{x1}" y="{y}" width="{x2-x1}" height="76" rx="38" fill="{c}"/>'
                f'<circle cx="{bx}" cy="{y+22}" r="46" fill="{c}"/>')
    bars = bar(-250, 110, -200, -60) + bar(-280, -130, -40, -200) + bar(130, 280, -40, 205) + bar(-100, 270, 120, 150)
    sun = f'<circle cx="0" cy="0" r="80" fill="{P["bg"] if mono else P["S"]}" stroke="{ink if mono else "none"}" stroke-width="12"/>'
    return L('a', bars) + L('b', sun)
# ===== 8 向光小苗（水彩感，向量模擬）：盆栽把葉子伸向一小塊光 =====
def s8(P):
    ink = P['ink']; mono = P.get('mono'); g = P['G']
    wc = '<filter id="wc" x="-15%" y="-15%" width="130%" height="130%"><feTurbulence type="fractalNoise" baseFrequency=".03" numOctaves="3" seed="7" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="16"/></filter>'
    def leaf(x, y, ln, ang, wd):
        a = math.radians(ang); ex, ey = x+ln*math.cos(a), y+ln*math.sin(a); nx, ny = -math.sin(a)*wd, math.cos(a)*wd
        mx, my = (x+ex)/2, (y+ey)/2
        d = f'M {x:.1f} {y:.1f} Q {mx+nx:.1f} {my+ny:.1f} {ex:.1f} {ey:.1f} Q {mx-nx:.1f} {my-ny:.1f} {x:.1f} {y:.1f} Z'
        if mono: return f'<path d="{d}" fill="{P["bg"]}" stroke="{ink}" stroke-width="9" stroke-linejoin="round"/>'
        return f'<path d="{d}" fill="{g}" fill-opacity=".66" stroke="{g}" stroke-opacity=".95" stroke-width="6" stroke-linejoin="round"/>'
    stem = 'M 0 190 C -6 110 0 30 40 -40 C 66 -86 96 -120 126 -150'
    plant = f'<path d="{stem}" fill="none" stroke="{ink if mono else g}" stroke-width="{14 if mono else 22}" stroke-linecap="round" opacity="{1 if mono else .9}"/>'
    plant += leaf(-2, 130, 178, -22, 70) + leaf(2, 66, 170, -58, 64) + leaf(20, 0, 160, -30, 60) + leaf(44, -48, 140, -68, 52) + leaf(92, -102, 112, -40, 42)
    if not mono:
        sun = f'<circle cx="214" cy="-186" r="96" fill="{P["S"]}" opacity=".28"/><circle cx="214" cy="-186" r="64" fill="{P["S"]}" opacity=".9"/><circle cx="222" cy="-178" r="50" fill="{P["S"]}" opacity=".55"/>'
    else:
        sun = f'<circle cx="214" cy="-186" r="64" fill="url(#hatch)" stroke="{ink}" stroke-width="9"/>'
    pc = ink if mono else P['T']
    pot = f'<path d="M -108 182 L 108 182 L 84 268 L -84 268 Z" fill="{pc}" stroke="{pc}" stroke-width="10" stroke-linejoin="round"/>'
    pot += f'<rect x="-126" y="164" width="252" height="38" rx="12" fill="{pc}"/>'
    body = f'<g {"" if mono else "filter=\"url(#wc)\""}>{plant}{sun}</g>'
    return wc + L('a', body) + L('b', pot)
# ===== 9 手帳鉛筆塗鴉（手帳塗鴉）：手帳紙上，用鉛筆隨手畫一圈太陽 =====
def s9(P):
    ink = P['ink']; mono = P.get('mono'); rnd = random.Random(11)
    paper = f'<g transform="rotate(-4)"><rect x="-250" y="-250" width="500" height="520" rx="22" fill="{P["soft"]}" stroke="{ink}" stroke-width="12"/>'
    for ix in range(-4, 5):
        for iy in range(-4, 5):
            paper += f'<circle cx="{ix*52}" cy="{iy*52+10}" r="3.4" fill="{ink}" opacity="{1 if mono else .35}"/>'
    paper += '</g>'
    cx, cy = -6, 24
    d = f'<path d="{wob(cx+12, cy+10, 98, 21, .05)}" fill="{lightfill(P)}" opacity="{1 if mono else .92}"/>'
    d += f'<path d="{wob(cx, cy, 108, 3, .05, a0=-10, a1=345)}" fill="none" stroke="{ink}" stroke-width="10" stroke-linecap="round"/>'
    d += f'<path d="{wob(cx, cy, 118, 9, .05, a0=40, a1=380)}" fill="none" stroke="{ink}" stroke-width="7" stroke-linecap="round" opacity="{1 if mono else .65}"/>'
    for k in range(10):
        a = math.radians(-90+k*36+rnd.uniform(-6, 6)); r1 = 142+rnd.uniform(-4, 6); r2 = r1+rnd.uniform(28, 52)
        d += line(cx+r1*math.cos(a), cy+r1*math.sin(a), cx+r2*math.cos(a), cy+r2*math.sin(a), 10, ink)
    tape = f'<g transform="translate(40 -262) rotate(8)"><rect x="-86" y="-30" width="172" height="62" fill="{lightfill(P)}" opacity="{1 if mono else .88}"/>'
    if not mono:
        for k in range(-4, 5): tape += line(k*20-14, -30, k*20+14, 32, 6, P['bg'])
    tape += f'<rect x="-86" y="-30" width="172" height="62" fill="none" stroke="{ink}" stroke-width="6" stroke-dasharray="2 12" stroke-linecap="round"/></g>'
    return L('a', paper) + L('b', d) + L('c', tape)

# ===== 10 郵票（復古郵票）：一枚蓋著「每天寄來一小段晴」的郵票 =====
def s10(P):
    ink = P['ink']; mono = P.get('mono')
    body_fill = ink if mono else P['S']
    holes = ''.join(f'<circle cx="{x}" cy="{y}" r="14" fill="#000"/>' for x in range(-160, 161, 40) for y in (-250, 250))
    holes += ''.join(f'<circle cx="{x}" cy="{y}" r="14" fill="#000"/>' for y in range(-200, 201, 40) for x in (-200, 200))
    mk = f'<mask id="mk10"><rect x="-300" y="-300" width="600" height="600" fill="#fff"/>{holes}</mask>'
    s = mk + f'<g transform="rotate(-5)"><rect x="-200" y="-250" width="400" height="500" fill="{body_fill}" mask="url(#mk10)"/>'
    s += f'<rect x="-164" y="-214" width="328" height="428" fill="{P["bg"] if mono else P["soft"]}"/>'
    s += f'<rect x="-164" y="-214" width="328" height="428" fill="none" stroke="{ink}" stroke-width="9"/>'
    s += f'<clipPath id="c10"><rect x="-164" y="-214" width="328" height="428"/></clipPath><g clip-path="url(#c10)">'
    s += f'<circle cx="0" cy="-40" r="92" fill="{lightfill(P)}" stroke="{ink}" stroke-width="12"/>'
    s += rays(0, -40, 118, 146, 7, 12, ink, 195, 345)
    for y in (96, 138, 180):
        s += f'<path d="M -190 {y} q 26 -16 52 0 t 52 0 t 52 0 t 52 0 t 52 0 t 52 0 t 52 0" fill="none" stroke="{ink}" stroke-width="13" stroke-linecap="round"/>'
    s += '</g></g>'
    return L('a', s)

# ===== 11 像素日出（像素）：像素遊戲的一格畫面，太陽升起、小芽長出 =====
def s11(P):
    ink = P['ink']; mono = P.get('mono'); u = 30; N = 17; ox = -N*u/2
    grid = {}
    cx, cy = 7, 6
    for y in range(N):
        for x in range(N):
            dd = math.hypot(x-cx, y-cy)
            if dd <= 3.4: grid[(x, y)] = 'Y'
            elif dd <= 4.6: grid[(x, y)] = 'O'
    for p in ((7, 0), (7, 1), (2, 1), (3, 2), (12, 1), (11, 2), (0, 6), (1, 6), (13, 6), (14, 6)): grid[p] = 'O'
    for x in range(N):
        for y in range(12, N):
            if y == 12: grid[(x, y)] = 'O'
            else: grid[(x, y)] = 'h' if not mono else ('O' if (x+y) % 2 == 0 else '.')
    for p in ((14, 11), (14, 10)): grid[p] = 'L'
    for p in ((13, 10), (12, 9), (15, 10), (16, 9)): grid[p] = 'L'
    col = {'Y': P['bg'] if mono else P['S'], 'O': ink, 'h': P['M'], 'L': ink if mono else P['G']}
    s = f'<g shape-rendering="crispEdges">'
    for (x, y), t in grid.items():
        if t in col: s += f'<rect x="{ox+x*u:.0f}" y="{ox+y*u:.0f}" width="{u}" height="{u}" fill="{col[t]}"/>'
    s += '</g>'
    if mono:  # 單色：太陽實心，與像素山丘分開看
        pass
    return L('a', s)

# ===== 12 一格電（介面圖示）：電量只剩一小格，但那一格是晴的 =====
def s12(P):
    ink = P['ink']; mono = P.get('mono')
    s = f'<rect x="-250" y="-70" width="430" height="180" rx="42" fill="{P["soft"]}" stroke="{ink}" stroke-width="24"/>'
    s += f'<rect x="196" y="-26" width="46" height="92" rx="16" fill="{ink}"/>'
    xs = [-216+i*94 for i in range(4)]
    s += f'<rect x="{xs[0]}" y="-40" width="80" height="120" rx="20" fill="{lightfill(P)}" stroke="{ink}" stroke-width="{10 if mono else 0}"/>'
    for x in xs[1:]:
        s += f'<rect x="{x}" y="-40" width="80" height="120" rx="20" fill="none" stroke="{ink}" stroke-width="8" stroke-dasharray="3 15" stroke-linecap="round" opacity="{1 if mono else .55}"/>'
    sunr = rays(-176, -108, 62, 118, 5, 16, ink, -150, -30)
    return L('a', s) + L('b', sunr)
STYLES = [
 # 序號、資料夾名、名稱、風格、含義、符號函式、字標字型、字距、符號縮放、44px 自評
 (1, '01_小字三光', '小字三光', '字體設計', '「小」字的三筆是從太陽灑下的三道光：日子再小，也有光落下來。', s1, 'sans', 14, 1.1, ''),
 (2, '02_昌日倒影', '昌日倒影', '色塊疊影', '兩個「日」疊成「昌」：上面是今天的太陽，下面是水面上的倒影，日日都留得住。', s2, 'serif', 14, 1.1, ''),
 (3, '03_蛋黃吐司', '蛋黃吐司', '貼紙', '一片吐司上的蛋黃就是太陽：早餐桌上，吃得到的小確定。', s3, 'kai', 12, 1.1, ''),
 (4, '04_貓睡陽光', '貓睡陽光', '剪影', '一隻貓蜷在地板的一小塊陽光裡打盹，不趕時間，剛剛好。', s4, 'sans', 14, 1.1, ''),
 (5, '05_車窗流光', '車窗流光', '單線', '通勤的捷運車廂，窗外有一道陽光流過，擠的日子裡也有一下子亮。', s5, 'sans', 14, 1.1, ''),
 (6, '06_書頁透光', '書頁透光', '線稿', '書頁折起來的角落，透出一顆小太陽：翻開一頁，就有光。', s6, 'serif', 14, 1.1, ''),
 (7, '07_雲帶缺口', '雲帶缺口', '色塊拼貼', '一條很長的雲帶，中間缺了一小段，剛好露出晴空。', s7, 'sans', 14, 1.1, ''),
 (8, '08_向光小苗', '向光小苗', '水彩感', '盆栽把葉子伸向一小塊光，慢慢長，也算數。', s8, 'kai', 12, 1.1, ''),
 (9, '09_手帳塗鴉', '手帳塗鴉', '手帳塗鴉', '手帳上用鉛筆隨手畫的一圈太陽，貼著紙膠帶，像今天的小記號。', s9, 'kai', 12, 1.1, ''),
 (10, '10_晴天郵票', '晴天郵票', '復古郵票', '一枚小小的郵票，每天寄來一小段晴。', s10, 'serif', 14, 1.1, ''),
 (11, '11_像素日出', '像素日出', '像素', '像素遊戲的一格畫面：太陽升起來，旁邊長出一株小芽，今天也推進一格。', s11, 'sans', 14, 1.1, ''),
 (12, '12_一格電', '一格電', '介面圖示', '電量只剩一小格，但那一格是亮的：撐得過今天就好。', s12, 'sans', 14, 1.1, ''),
]
def avatar_svg(P, sym, k, bg=True):
    b = f'<rect width="1080" height="1080" fill="{P["bg"]}"/>' if bg else ''
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1080" viewBox="0 0 1080 1080"><defs>{defs(P)}</defs>{b}<g transform="translate(540 540) scale({k})">{sym}</g></svg>'
def text_w(s, kind, fs, ls):
    f = ImageFont.truetype(FONTS[kind][2], fs); return f.getlength(s) + ls*(len(s)-1)
WH = 420
def wm_svg(P, n, sym, kind, ls, k, sub, bg=True):
    """橫式字標（圖示＋文字）；回傳 svg 字串與寬度。"""
    ink = P['ink']; bgr = f'<rect width="{{W}}" height="{WH}" fill="{P["bg"]}"/>' if bg else ''
    fs = 150 if not sub else 134
    ty = 210 if not sub else 170
    symsz = 372
    tw = text_w(NAME, kind, fs, ls); x0 = 60 + symsz + 54; W = int(x0 + tw + 70)
    body = L('sym', f'<g transform="translate({60+symsz/2} 210) scale({k})">{sym}</g>')
    body += L('txt', TX(NAME, kind, fs, x0, ty+.36*fs, ink, ls=ls, bold=3 if kind == 'kai' else 0))
    if sub:
        body += L('sub', TX(SUB, 'sans', 44, x0, 345, ink, ls=7))
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{WH}" viewBox="0 0 {W} {WH}"><defs>{defs(P)}</defs>{bgr.replace("{W}", str(W))}{body}</svg>', W

if __name__ == '__main__':
    jobs = []; meta = []
    for (n, fo, nm, sty, mean, fn, kind, ls, k, self44) in STYLES:
        os.makedirs(fo, exist_ok=True)
        meta.append(dict(n=n, dir=fo, name=nm, style=sty, mean=mean, kind=kind, self44=self44))
        far1 = FIT.get(str(n), 300); ka = min(420/far1, 1.6); kw = min(172/far1, 1.2)
        meta[-1].update(far1=far1, ka=ka, kw=kw)
        for tag, P in TONES.items():
            sym = fn(P)
            sv = avatar_svg(P, sym, ka); p = f'{fo}/頭像_1080方_{tag}'; open(p+'.svg', 'w').write(sv)
            jobs.append(dict(n=n, kind='avatar', tag=tag, svg=p+'.svg', png=p+'.png', w=1080, h=1080))
            for sub, suf in ((False, '字標'), (True, '字標含副標')):
                sv, W = wm_svg(P, n, sym, kind, ls, kw, sub); p = f'{fo}/{suf}_{tag}'; open(p+'.svg', 'w').write(sv)
                jobs.append(dict(n=n, kind='wmsub' if sub else 'wm', tag=tag, svg=p+'.svg', png=p+'.png', w=W, h=WH))
                if not TONES[tag].get('mono'):
                    sv, W = wm_svg(P, n, sym, kind, ls, kw, sub, bg=False); p = f'{fo}/{suf}_透明_{tag}'; open(p+'.svg', 'w').write(sv)
                    jobs.append(dict(n=n, kind='wmT', tag=tag, svg=p+'.svg', png=p+'.png', w=W, h=WH, transparent=True))
        # 檢查用（暫存區）：無底圖層
        P = TONES['奶油晨光']; sym = fn(P)
        open(f'{CHK}/av{n}.svg', 'w').write(avatar_svg(P, sym, ka, bg=False)); open(f'{CHK}/av{n}_1.svg', 'w').write(avatar_svg(P, sym, 1.0, bg=False))
        jobs.append(dict(n=n, kind='chk_av', svg=f'{CHK}/av{n}.svg', png=f'{CHK}/av{n}_all.png', w=1080, h=1080, transparent=True))
        jobs.append(dict(n=n, kind='chk_av1', svg=f'{CHK}/av{n}_1.svg', png=f'{CHK}/av{n}_1.png', w=1080, h=1080, transparent=True))
        for lay in ('a', 'b', 'c'):
            if f'data-layer="{lay}"' in sym:
                jobs.append(dict(n=n, kind='chk_layer', layer=lay, svg=f'{CHK}/av{n}.svg', png=f'{CHK}/av{n}_{lay}.png', w=1080, h=1080, transparent=True, show=[lay]))
        for sub in (False, True):
            sv, W = wm_svg(P, n, sym, kind, ls, kw, sub, bg=False); open(f'{CHK}/wm{n}{"s" if sub else ""}.svg', 'w').write(sv)
            for lay in ('sym', 'sym2', 'txt', 'sub'):
                if f'data-layer="{lay}"' in sv:
                    jobs.append(dict(n=n, kind='chk_wm', sub=sub, layer=lay, svg=f'{CHK}/wm{n}{"s" if sub else ""}.svg', png=f'{CHK}/wm{n}{"s" if sub else ""}_{lay}.png', w=W, h=WH, transparent=True, show=[lay]))
            jobs.append(dict(n=n, kind='chk_wm', sub=sub, layer='all', svg=f'{CHK}/wm{n}{"s" if sub else ""}.svg', png=f'{CHK}/wm{n}{"s" if sub else ""}_all.png', w=W, h=WH, transparent=True))
    json.dump(dict(jobs=jobs, meta=meta, tones=TONES), open('jobs.json', 'w'), ensure_ascii=False)
    print(len(jobs), 'jobs')
