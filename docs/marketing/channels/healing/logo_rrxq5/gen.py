# 「日日小晴」LOGO 第五輪 12 款（2026-11-05）：全新方向、明亮悠閒色調、全自繪向量，不用 AI 圖／比比／吉祥物／品牌商標
# 字型只用 ~/.fonts 的 Noto Sans/Serif CJK TC 與霞鶩文楷（OFL）
# 重跑：python3 gen.py && node render.js && python3 compose.py
import json, math, os, random
from PIL import ImageFont
H = os.path.dirname(os.path.abspath(__file__)); os.chdir(H)
CHK = '/tmp/claude-0/-home-user-tw-rotation/ce50d787-1067-5482-ab44-99dc39a48890/scratchpad/rrxq5_chk'
os.makedirs(CHK, exist_ok=True)
FD = os.path.expanduser('~/.fonts/')
FONTS = {  # 鍵：(CSS 家族, 字重, PIL 檔)
 'sans': ("'Noto Sans CJK TC',sans-serif", 700, FD+'NotoSansCJKtc-Bold.otf'),
 'serif': ("'Noto Serif CJK TC',serif", 700, FD+'NotoSerifCJKtc-Bold.otf'),
 'kai': ("'LXGW WenKai TC',serif", 400, FD+'LXGWWenKaiTC-Regular.ttf'),
}
# 色調：bg 底、S 太陽色、M 主色（大面積）、soft 淺色、ink 字與線
TONES = {
 '奶油晨光': dict(bg='#FFF6E5', S='#F2A65A', M='#F7D9A6', soft='#FFE9C7', ink='#3A3A3A', G='#7FA06A', C='#CDB9A0', T='#C98B5E', B='#6FA8C6', D='#2B2320'),
 '晴空淡藍': dict(bg='#EAF4FB', S='#F6C85F', M='#6FB1E0', soft='#CFE6F6', ink='#1F3C54', G='#5E9E7A', C='#8DB6D8', T='#C98B5E', B='#2F6FA3', D='#2B2320'),
 '抹茶午後': dict(bg='#EEF2E6', S='#F6C85F', M='#8DAA7B', soft='#D6E2CA', ink='#2F3F29', G='#5F8450', C='#A9B79A', T='#C98B5E', B='#4E8FB0', D='#2B2320'),
 '深色模式': dict(bg='#1E1A16', S='#F2A65A', M='#7A5A38', soft='#2E261E', ink='#FFF6E5', G='#8DB07A', C='#6B5C4C', T='#B9805A', B='#6FB1E0', D='#38302A'),
 '單色黑': dict(bg='#FFFFFF', S='#111111', M='#FFFFFF', soft='#FFFFFF', ink='#111111', G='#111111', C='#111111', T='#111111', mono=1, B='#111111', D='#111111'),
 '單色白': dict(bg='#111111', S='#FFFFFF', M='#111111', soft='#111111', ink='#FFFFFF', G='#FFFFFF', C='#FFFFFF', T='#FFFFFF', mono=1, B='#FFFFFF', D='#FFFFFF'),
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

# ===== 第五輪 12 款符號（座標約 ±270，之後由 fit.json 自動縮放）=====
# 第五輪主軸：Andy 11-05「再多點素材，我覺得可以更好」→ 主元素＋2～4 個配角＋質感細節；每款附「簡化小圖版」（simple=True）供 110／44px 頭像
def shade(h, f):
    h = h.lstrip('#'); c = [int(h[i:i+2], 16) for i in (0, 2, 4)]
    c = [round(x+(255-x)*f) if f > 0 else round(x*(1+f)) for x in c]
    return '#%02X%02X%02X' % tuple(c)
def _lum(h):
    h = h.lstrip('#'); c = [int(h[i:i+2], 16)/255 for i in (0, 2, 4)]
    c = [x/12.92 if x <= .03928 else ((x+.055)/1.055)**2.4 for x in c]; return .2126*c[0]+.7152*c[1]+.0722*c[2]
def _cr(a, b):
    x, y = sorted([_lum(a), _lum(b)], reverse=True); return (x+.05)/(y+.05)
def DK(P): return P['bg'] == '#1E1A16'
def A(P, fill, accent=False, w=10):
    """填色屬性：單色版改成「底色＋描邊」，accent 用斜線網。"""
    if P.get('mono'):
        f = 'url(#hatch)' if accent else P['bg']
        return f'fill="{f}" stroke="{P["ink"]}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"'
    return f'fill="{fill}"'
def spark(cx, cy, r, col, rot=0):
    d = f'M {cx} {cy-r} Q {cx} {cy} {cx+r} {cy} Q {cx} {cy} {cx} {cy+r} Q {cx} {cy} {cx-r} {cy} Q {cx} {cy} {cx} {cy-r} Z'
    return f'<path d="{d}" fill="{col}" stroke="{col}" stroke-width="3" stroke-linejoin="round" transform="rotate({rot} {cx} {cy})"/>'
def leaf(x, y, ln, w, ang, fill, extra=''):
    return (f'<path d="M 0 0 C {w} {-ln*.3:.1f}, {w*.6:.1f} {-ln*.8:.1f}, 0 {-ln} C {-w*.6:.1f} {-ln*.8:.1f}, {-w} {-ln*.3:.1f}, 0 0 Z" '
            f'transform="translate({x} {y}) rotate({ang})" {fill} {extra}/>')
def tip(x, y, ln, ang):
    a = math.radians(ang); return x+ln*math.sin(a), y-ln*math.cos(a)
def ring_pts(R, n, off=0): return [(R*math.cos(math.radians(off+360*k/n)), R*math.sin(math.radians(off+360*k/n))) for k in range(n)]
def check_col(P, bgc): return P['ink'] if _cr(P['ink'], bgc) >= _cr(P['bg'], bgc) else P['bg']
CARD = lambda P: P['bg'] if P.get('mono') else (P['D'] if DK(P) else '#FFFFFF')


# ===== 第五輪通用小工具 =====
def lerp_hex(a, b, t):
    a = a.lstrip('#'); b = b.lstrip('#')
    ca = [int(a[i:i+2], 16) for i in (0, 2, 4)]; cb = [int(b[i:i+2], 16) for i in (0, 2, 4)]
    return '#%02X%02X%02X' % tuple(round(x+(y-x)*t) for x, y in zip(ca, cb))
def star5(cx, cy, r, col, rot=-90):
    pts = []
    for k in range(10):
        rr_ = r if k % 2 == 0 else r*.45; a = math.radians(rot+36*k); pts.append(f'{cx+rr_*math.cos(a):.1f},{cy+rr_*math.sin(a):.1f}')
    return f'<polygon points="{" ".join(pts)}" fill="{col}" stroke="{col}" stroke-width="3" stroke-linejoin="round"/>'
def grain_defs():
    return ('<filter id="gr" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="7"/>'
            '<feColorMatrix values="0 0 0 0 .35  0 0 0 0 .25  0 0 0 0 .15  0 0 0 .7 -.22"/></filter>')
def union(P, shapes, fill, w=10, accent=False):
    """多片重疊的形狀先描一圈外框再填色，外框只留聯集輪廓（單色版靠它）。"""
    if P.get('mono'):
        f = 'url(#hatch)' if accent else P['bg']
        return (f'<g fill="{P["ink"]}" stroke="{P["ink"]}" stroke-width="{2*w}" stroke-linejoin="round">{shapes}</g>'
                f'<g fill="{f}">{shapes}</g>')
    return f'<g fill="{fill}">{shapes}</g>'
def sun_rays(cx, cy, r1, r2, n, w, col, alt=None, rot=-90):
    s = ''
    for k in range(n):
        a = math.radians(rot+k*360/n); rr2 = r2 if (alt is None or k % 2 == 0) else alt
        s += line(cx+r1*math.cos(a), cy+r1*math.sin(a), cx+rr2*math.cos(a), cy+rr2*math.sin(a), w, col)
    return s
def SUNG(P, id_, lighten=.45):
    S = P['S']
    return (f'<radialGradient id="{id_}" cx=".38" cy=".32" r=".85"><stop offset="0" stop-color="{shade(S, lighten)}"/>'
            f'<stop offset=".55" stop-color="{S}"/><stop offset="1" stop-color="{shade(S, -.18)}"/></radialGradient>')
def sunfill(P, id_):
    return 'url(#hatch)' if P.get('mono') else f'url(#{id_})'

def SF(P, id_, w=10):
    return A(P, 'x', True, w) if P.get('mono') else f'fill="url(#{id_})"'
def MST(P, w=5):
    return f'stroke="{P["ink"]}" stroke-width="{w}"' if P.get('mono') else ''

# ===== 1 雙日·一大一小（平塗＋紙感）：一顆大太陽（今天）、一顆小太陽（明天）並排，小雲、閃光、紙面顆粒 =====
def s1(P, simple=False):
    ink = P['ink']; mono = P.get('mono'); S = P['S']; wh = '#FFFFFF' if not DK(P) else '#E8DCC8'
    defs_ = SUNG(P, 'g1') + SUNG(P, 'g1b', .7) + grain_defs() + '<clipPath id="c1"><circle cx="0" cy="0" r="300"/></clipPath>'
    if mono: halo = f'<circle cx="0" cy="0" r="300" fill="none" stroke="{ink}" stroke-width="8" stroke-dasharray="3 16" stroke-linecap="round"/>'
    else: halo = f'<circle cx="0" cy="0" r="300" fill="{P["soft"]}"/>'
    out = defs_ + L('h', halo)
    if not mono and not simple:
        out += L('n', '<g clip-path="url(#c1)"><rect x="-310" y="-310" width="620" height="620" filter="url(#gr)" opacity=".55"/></g>')
    bx, by_, br = -80, 44, 122; sx, sy, sr = 162, -132, 44
    rc = ink if mono else shade(S, -.02)
    big = sun_rays(bx, by_, br+22, br+54 if not simple else br+46, 12, 22 if not simple else 28, rc, alt=br+38 if not simple else None)
    big += f'<circle cx="{bx}" cy="{by_}" r="{br}" {SF(P, "g1", 12)}/>'
    sm = sun_rays(sx, sy, sr+16, sr+38, 8, 12 if not simple else 14, rc)
    sm += f'<circle cx="{sx}" cy="{sy}" r="{sr}" {SF(P, "g1b", 10)}/>'
    out += L('a', big) + L('b', sm)
    if not simple:
        out += L('c', cloud(150, 195, .36, wh if not mono else P['bg'], ink if mono else None, 6))
        out += L('d', spark(-196, -142, 16, S if not mono else ink) + spark(228, 40, 11, S if not mono else ink))
    return out

# ===== 2 習字格·日日（練習簿）：兩格習字格，左格寫一個「日」，右格同位置畫一顆小太陽 =====
def s2(P, simple=False):
    ink = P['ink']; mono = P.get('mono'); S = P['S']
    rc = ink if mono else ('#E58C7C' if DK(P) else '#C9594A'); card = CARD(P)
    paper = (f'<g filter="url(#sh)"><rect x="-250" y="-215" width="500" height="430" rx="26" fill="{card}"/></g>' if not mono
             else f'<rect x="-250" y="-215" width="500" height="430" rx="26" fill="{card}" stroke="{ink}" stroke-width="10"/>')
    out = L('a', paper)
    cells = ''; fills = ''; guides = ''
    for cx in (-115, 115):
        fills += f'<rect x="{cx-100}" y="-120" width="200" height="200" fill="{P["soft"] if not mono else P["bg"]}"/>'
        cells += f'<rect x="{cx-100}" y="-120" width="200" height="200" fill="none" stroke="{rc}" stroke-width="7"/>'
        if not simple:
            for (x1, y1, x2, y2) in ((cx-100, -120, cx+100, 80), (cx+100, -120, cx-100, 80), (cx, -120, cx, 80), (cx-100, -20, cx+100, -20)):
                guides += f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{rc}" stroke-width="3" stroke-dasharray="10 9" stroke-opacity="{1 if mono else .6}"/>'
    out += L('f', fills) + L('k', cells + guides)
    out += L('g', glyph('日', 'kai', 176, -115, -20, ink, bold=3))
    sun = sun_rays(115, -20, 62, 84, 8, 13, S if not mono else ink, rot=-90) + f'<circle cx="115" cy="-20" r="44" {A(P, S, True, 10)}/>'
    out += L('s', sun)
    if not simple:
        tp = shade(S, .5) if not mono else P['bg']
        out += L('w', f'<g transform="rotate(-4 0 -215)"><rect x="-84" y="-246" width="168" height="56" fill="{tp}" fill-opacity="{1 if mono else .88}" {MST(P, 6)}/>'
                      + ''.join(f'<line x1="{x}" y1="-246" x2="{x-16}" y2="-190" stroke="{ink if mono else shade(S, -.1)}" stroke-width="4" stroke-opacity=".35"/>' for x in range(-52, 90, 34)) + '</g>')
        out += L('t', TX('每天一格', 'kai', 42, 0, 158, ink, anchor='middle', ls=8, bold=1))
        out += L('x', star5(172, 142, 26, S if not mono else ink))
    return out

# ===== 3 日出雙峰·條紋（復古條紋）：同一條地平線上兩個日出（一大一小），日身被條紋切開，下方水面映出光條 =====
def s3(P, simple=False):
    ink = P['ink']; mono = P.get('mono'); S = P['S']; y0 = 50
    defs_ = '<clipPath id="c3"><circle cx="0" cy="0" r="250"/></clipPath>'
    gaps = ''.join(f'<rect x="-300" y="{y0-yy}" width="600" height="{hh}" fill="#000"/>' for yy, hh in ((14, 6), (32, 8), (54, 10)))
    defs_ += f'<mask id="m3" maskUnits="userSpaceOnUse" x="-300" y="-300" width="600" height="600"><rect x="-300" y="-300" width="600" height="600" fill="#fff"/>{gaps}</mask>'
    disc = f'<circle cx="0" cy="0" r="250" fill="{P["soft"] if not mono else P["bg"]}" stroke="{ink if mono else "none"}" stroke-width="10"/>'
    ground = f'<g clip-path="url(#c3)"><rect x="-260" y="{y0}" width="520" height="220" {A(P, P["M"], True, 8)}/></g>'
    out = defs_ + L('a', disc + ground)
    sunL = f'<path d="M -210 {y0} A 112 112 0 0 1 14 {y0} Z" {A(P, S, True, 10)}/>'
    sunR = f'<path d="M 50 {y0} A 68 68 0 0 1 186 {y0} Z" {A(P, shade(S, .3) if not mono else S, True, 10)}/>'
    msk = 'mask="url(#m3)"' if not simple else ''
    out += L('b', f'<g {msk}>{sunL}</g>') + L('c', f'<g {msk}>{sunR}</g>')
    if not simple:
        st = ''.join(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h/2}" fill="{"#FFFFFF" if not mono else P["bg"]}" {MST(P, 5)}/>' for x, y, w, h in ((-60, -150, 150, 16), (30, -112, 110, 14), (-196, -90, 84, 13)))
        out += L('d', st)
        rf = ''
        for (cx_, ws), yy, hh, op in (((-98, (210, 140, 80)), None, None, None), ((118, (130, 80, 36)), None, None, None)):
            for ww, y_, h_, o in zip(ws, (y0+24, y0+48, y0+70), (12, 10, 8), (.9, .65, .4)):
                rf += f'<rect x="{cx_-ww/2}" y="{y_}" width="{ww}" height="{h_}" rx="{h_/2}" fill="{S if not mono else ink}" fill-opacity="{1 if mono else o}"/>'
        out += L('e', rf)
        out += L('x', spark(176, -128, 15, S if not mono else ink))
    return out

# ===== 4 網點日子（半色調）：一天一顆圓點，由小漸大，最後一顆是帶網點光芒的太陽 =====
def s4(P, simple=False):
    ink = P['ink']; mono = P.get('mono'); S = P['S']
    defs_ = SUNG(P, 'g4')
    scx, scy, rs = 118, -104, 62; ringr = 100; ringo = ringr+7
    rads = [6, 9, 13, 17, 22, 28, 35] if not simple else [9, 13, 18, 24, 31, 39]
    p0 = (-232, 176); dx, dy = scx-p0[0], scy-p0[1]; D = math.hypot(dx, dy); ux, uy = dx/D, dy/D
    need_sum = 2*sum(rads)-rads[0]-rads[-1]
    gap = (D-(ringo+16+rads[-1])-need_sum)/(len(rads)-1)
    gap = max(gap, 12)
    nx, ny = uy, -ux    # 弧形往左上鼓
    if ny > 0: nx, ny = -nx, -ny
    dots = ''; pos = []; dcur = 0.0
    for i, r_ in enumerate(rads):
        if i > 0: dcur += rads[i-1]+r_+gap
        s_ = dcur/D; bow = 30*math.sin(math.pi*min(s_, 1))
        x = p0[0]+ux*dcur+nx*bow; y = p0[1]+uy*dcur+ny*bow
        col = lerp_hex(P['C'], S, i/(len(rads)-1)) if not mono else ink
        t_ = i/(len(rads)-1)
        dots += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r_}" {A(P, col, i >= len(rads)//2, 6)}/>'
        if not mono and not simple and r_ >= 13: dots += f'<circle cx="{x-r_*.3:.1f}" cy="{y-r_*.32:.1f}" r="{r_*.24:.1f}" fill="#FFFFFF" fill-opacity=".6"/>'
    out = defs_ + L('a', dots)
    ring = ''.join(f'<circle cx="{scx+ringr*math.cos(math.radians(k*22.5)):.1f}" cy="{scy+ringr*math.sin(math.radians(k*22.5)):.1f}" r="{7 if k % 2 == 0 else 5}" fill="{S if not mono else ink}" fill-opacity="{1 if (k % 2 == 0 or mono) else .6}"/>' for k in range(16))
    sunb = ring + f'<circle cx="{scx}" cy="{scy}" r="{rs}" {SF(P, "g4", 10)}/>'
    out += L('b', sunb)
    if not simple:
        ht = ''
        for gx in range(-60, 260, 30):
            for gy in range(50, 260, 30):
                d_ = math.hypot(gx-235, gy-235); r_ = 9*(1-d_/300)
                if r_ >= 2.2 and math.hypot(gx, gy) <= 252: ht += f'<circle cx="{gx}" cy="{gy}" r="{r_:.1f}" fill="{ink if mono else P["C"]}" fill-opacity="{1 if mono else .85}"/>'
        out += L('h', ht)
        out += L('d', spark(-200, -170, 16, S if not mono else ink) + spark(236, -200 if False else -10, 10, S if not mono else ink))
    return out

# ===== 5 日日地平線（字體設計）：兩個「日」字格底邊連成一條長長的地平線，兩日之間升起一顆小太陽 =====
def s5(P, simple=False):
    ink = P['ink']; mono = P.get('mono'); S = P['S']; sw = 30 if not simple else 36
    wh = '#FFFFFF' if not DK(P) else '#E8DCC8'
    f1 = P['soft'] if not mono else P['bg']; f2 = shade(S, .62) if not mono else 'url(#hatch)'
    if DK(P): f1, f2 = '#3A2E22', shade(S, -.35)
    g = ''
    for cx, fl in ((-140, f1), (140, f2)):
        g += f'<rect x="{cx-65}" y="-125" width="130" height="210" rx="18" fill="{fl}" stroke="{ink}" stroke-width="{sw}" stroke-linejoin="round"/>'
        g += line(cx-65, -20, cx+65, -20, sw-4, ink)
    g += line(-262, 85, 262, 85, sw, ink)
    out = L('a', g)
    # 三道短光：只留 -120、-90、-60 度
    rr_ = ''
    for a in (-120, -90, -60):
        aa = math.radians(a); rr_ += line(60*math.cos(aa), 58+60*math.sin(aa), 84*math.cos(aa), 58+84*math.sin(aa), 12, S if not mono else ink)
    out += L('c', f'<path d="M -44 58 A 44 44 0 0 1 44 58 Z" {A(P, S, True, 10)}/>' + rr_)
    if not simple:
        rf = ''
        for ww, yy, hh, o in ((380, 128, 14, .9), (270, 158, 12, .6), (150, 186, 10, .4)):
            rf += f'<rect x="{-ww/2}" y="{yy}" width="{ww}" height="{hh}" rx="{hh/2}" fill="{S if not mono else ink}" fill-opacity="{1 if mono else o}"/>'
        out += L('r', rf)
        out += L('d', cloud(150, -168, .3, wh if not mono else P['bg'], ink if mono else None, 5))
        out += L('e', spark(-186, -200, 15, S if not mono else ink))
    return out

# ===== 6 日晷（黃銅）：黃銅刻度盤、指針的影子只有短短一小段，盤面上一顆小太陽 =====
def s6(P, simple=False):
    ink = P['ink']; mono = P.get('mono'); S = P['S']
    br = shade(S, -.25) if not mono else ink
    defs_ = (f'<linearGradient id="br6" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F3D58E"/><stop offset=".5" stop-color="#D5A24E"/><stop offset="1" stop-color="#B98534"/></linearGradient>')
    plate = P['soft'] if not mono else P['bg']
    if DK(P): plate = '#3A2E22'
    if mono: a = f'<circle cx="0" cy="0" r="250" fill="{P["bg"]}" stroke="{ink}" stroke-width="12"/><circle cx="0" cy="0" r="212" fill="{plate}" stroke="{ink}" stroke-width="6"/>'
    else: a = f'<g filter="url(#sh)"><circle cx="0" cy="0" r="250" fill="url(#br6)"/></g><circle cx="0" cy="0" r="214" fill="{plate}"/><circle cx="0" cy="0" r="214" fill="none" stroke="{shade(S, -.3)}" stroke-width="4"/>'
    out = defs_ + L('a', a)
    tk = ''
    for k in range(24):
        a_ = math.radians(k*15-90); big = k % 6 == 0
        r1 = 168 if (big or simple) else 182; r2 = 204
        if simple and not big and k % 3: continue
        tk += line(r1*math.cos(a_), r1*math.sin(a_), r2*math.cos(a_), r2*math.sin(a_), 12 if big else 7, br if not simple else (br))
    out += L('k', tk)
    th = math.radians(40); wl = 150
    p1 = (wl*math.cos(th-.14), wl*math.sin(th-.14)); p2 = (wl*math.cos(th+.14), wl*math.sin(th+.14))
    wedge = f'<path d="M 0 0 L {p1[0]:.1f} {p1[1]:.1f} A {wl} {wl} 0 0 1 {p2[0]:.1f} {p2[1]:.1f} Z" fill="{"url(#hatch)" if mono else ink}" fill-opacity="{1 if mono else .22}" stroke="{ink if mono else "none"}" stroke-width="5"/>'
    out += L('w', wedge)
    ph = th+math.pi; gx = math.cos(ph); gy = math.sin(ph); px, py = -gy, gx
    tipL = 34 if not simple else 40
    gn = f'<path d="M {px*13:.1f} {py*13:.1f} L {-px*13:.1f} {-py*13:.1f} L {gx*tipL:.1f} {gy*tipL:.1f} Z" fill="{ink if mono else shade(S, -.45)}" stroke="{ink if mono else shade(S, -.45)}" stroke-width="4" stroke-linejoin="round"/>'
    out += L('g', gn)
    scx, scy = gx*104, gy*104; sr = 26 if not simple else 32
    sn = sun_rays(scx, scy, sr+10, sr+26, 8, 8 if not simple else 10, S if not mono else ink) + f'<circle cx="{scx:.1f}" cy="{scy:.1f}" r="{sr}" {A(P, S, True, 8)}/>'
    out += L('s', sn)
    if not simple:
        rv = ''.join(f'<circle cx="{232*math.cos(math.radians(a)):.1f}" cy="{232*math.sin(math.radians(a)):.1f}" r="8" fill="{shade(S, -.35) if not mono else ink}"/><circle cx="{232*math.cos(math.radians(a))-2:.1f}" cy="{232*math.sin(math.radians(a))-2:.1f}" r="3" fill="#FFFFFF" fill-opacity=".6"/>' for a in (45, 135, 225, 315))
        out += L('v', rv)
    return out

# ===== 7 日輪·年輪（木質切片）：每一圈是一天，疊成年輪，圓心是剛長出來的一小點晴 =====
def s7(P, simple=False):
    ink = P['ink']; mono = P.get('mono'); S = P['S']; T = P['T']
    wood = shade(T, .5) if not DK(P) else P['M']
    bark = shade(T, -.35) if not DK(P) else shade(P['M'], -.4)
    rl = ink if mono else shade(T, -.18) if not DK(P) else shade(P['M'], .35)
    defs_ = f'<radialGradient id="gl7" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="{S}" stop-opacity=".55"/><stop offset="1" stop-color="{S}" stop-opacity="0"/></radialGradient>'
    body = wob(0, 0, 226, 11, .025)
    a = f'<g filter="url(#sh)"><path d="{body} Z" fill="{wood if not mono else P["bg"]}" stroke="{bark if not mono else ink}" stroke-width="{18 if not mono else 12}" stroke-linejoin="round"/></g>' if not mono else f'<path d="{body} Z" fill="{P["bg"]}" stroke="{ink}" stroke-width="12" stroke-linejoin="round"/>'
    out = defs_ + L('a', a)
    radii = [78, 106, 134, 162, 190] if not simple else [112, 164]
    rg = ''.join(f'<path d="{wob(0, 0, r_, 21+i, .02)} Z" fill="none" stroke="{rl}" stroke-width="{6 if i % 2 == 0 else 4}" stroke-opacity="{1 if mono else .85}" stroke-linejoin="round"/>' for i, r_ in enumerate(radii))
    out += L('r', rg)
    sr = 36 if not simple else 54
    if not mono: out += L('g', f'<circle cx="0" cy="0" r="{sr+34}" fill="url(#gl7)"/>')
    sn = sun_rays(0, 0, sr+9, sr+24, 8, 9 if not simple else 12, S if not mono else ink) + f'<circle cx="0" cy="0" r="{sr}" {A(P, S, True, 8)}/>'
    out += L('s', sn)
    if not simple:
        def crack(ang, r1, r2, seed):
            rnd = random.Random(seed); pts = []
            for q in range(7):
                rr_ = r1+(r2-r1)*q/6; aa = math.radians(ang+(rnd.uniform(-5, 5) if 0 < q < 6 else 0))
                pts.append(f'{rr_*math.cos(aa):.1f} {rr_*math.sin(aa):.1f}')
            return f'<path d="M {" L ".join(pts)}" fill="none" stroke="{ink if mono else bark}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>'
        out += L('c', crack(28, 226, 150, 3) + crack(205, 226, 160, 5))
        dash = ''.join(f'<path d="M {208*math.cos(math.radians(a0)):.1f} {208*math.sin(math.radians(a0)):.1f} A 208 208 0 0 1 {208*math.cos(math.radians(a0+9)):.1f} {208*math.sin(math.radians(a0+9)):.1f}" fill="none" stroke="{ink if mono else bark}" stroke-opacity=".5" stroke-width="4" stroke-linecap="round"/>' for a0 in range(-170, 180, 38) if not (15 < a0 < 40 or 195-360 < a0 < 215-360))
        out += L('t', dash)
    return out

# ===== 8 色票扇（印刷色票）：七片色票攤成一把扇，每片一天，由陰天灰一路變亮，最後一片是晴 =====
def s8(P, simple=False):
    ink = P['ink']; mono = P.get('mono'); S = P['S']
    px, py = 0, 178; r0, r1 = 30, 334; half = 7
    defs_ = ''
    chips = ''; lastchip = ''; holes = ''; gloss = ''
    cols = []
    for i in range(7):
        t = i/6
        c = lerp_hex(P['C'], shade(S, .55), t/.55) if t < .55 else lerp_hex(shade(S, .55), S, (t-.55)/.45)
        cols.append(c)
    def pt(r_, th): a = math.radians(th); return px+r_*math.sin(a), py-r_*math.cos(a)
    for i in range(7):
        th = -54+i*18; a1 = pt(r0, th-half); a2 = pt(r1, th-half); a3 = pt(r1, th+half); a4 = pt(r0, th+half)
        d = f'M {a1[0]:.1f} {a1[1]:.1f} L {a2[0]:.1f} {a2[1]:.1f} A {r1} {r1} 0 0 1 {a3[0]:.1f} {a3[1]:.1f} L {a4[0]:.1f} {a4[1]:.1f} A {r0} {r0} 0 0 0 {a1[0]:.1f} {a1[1]:.1f} Z'
        fill = A(P, cols[i], i % 2 == 1 or i == 6, 7)
        el = f'<path d="{d}" {fill}/>'
        if i == 6: lastchip += el
        else: chips += el
        if not mono and not simple:
            g1 = pt(r0+30, th-half+1.6); g2 = pt(r1-8, th-half+1.6)
            gloss += f'<line x1="{g1[0]:.1f}" y1="{g1[1]:.1f}" x2="{g2[0]:.1f}" y2="{g2[1]:.1f}" stroke="#FFFFFF" stroke-opacity=".42" stroke-width="5" stroke-linecap="round"/>'
        if i < 6 and not simple:
            hx, hy = pt(298, th); holes += f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="14" fill="{P["bg"]}" stroke="{ink}" stroke-width="{5 if mono else 3}" stroke-opacity="{1 if mono else .45}"/>'
    sh = '' if mono else 'filter="url(#sh)"'
    out = defs_ + L('a', f'<g {sh}>{chips}</g>') + L('z', lastchip)
    if gloss: out += L('l', gloss)
    out += L('h', holes)
    sx_, sy_ = pt(290, -54+6*18)
    if mono: sg = f'<circle cx="{sx_:.1f}" cy="{sy_:.1f}" r="25" fill="{P["bg"]}" stroke="{ink}" stroke-width="5"/><circle cx="{sx_:.1f}" cy="{sy_:.1f}" r="11" fill="{ink}"/>'
    else: sg = sun_rays(sx_, sy_, 17, 23, 8, 5, '#FFF6E5') + f'<circle cx="{sx_:.1f}" cy="{sy_:.1f}" r="13" fill="#FFF6E5"/>'
    out += L('s', sg)
    out += L('p', f'<circle cx="{px}" cy="{py}" r="34" fill="{ink if mono else shade(P["T"], -.1)}" stroke="{P["bg"] if mono else "none"}" stroke-width="4"/><circle cx="{px-8}" cy="{py-8}" r="9" fill="#FFFFFF" fill-opacity="{0 if mono else .45}"/>')
    if not simple:
        out += L('d', spark(-228, -128, 15, S if not mono else ink) + spark(236, -104, 11, S if not mono else ink))
    return out

# ===== 9 日日春（膠彩花）：花名就叫「日日春」——天天開花。一朵盛開（花心是一顆小太陽）、一朵含苞，下面兩對葉 =====
def s9(P, simple=False):
    ink = P['ink']; mono = P.get('mono'); S = P['S']; Gc = P['G']
    PK = '#F2A9A3' if not DK(P) else '#E9A59F'; PK2 = '#D9726C' if not DK(P) else '#C9726D'
    cx, cy = -52, -30
    halo = f'<circle cx="0" cy="0" r="262" fill="{P["soft"]}"/>' if not mono else f'<circle cx="0" cy="0" r="262" fill="none" stroke="{ink}" stroke-width="8" stroke-dasharray="3 16" stroke-linecap="round"/>'
    out = L('h', halo)
    stem_c = ink if mono else shade(Gc, -.2)
    stems = (f'<path d="M 10 258 C 10 190 -40 120 {cx} {cy}" fill="none" stroke="{stem_c}" stroke-width="12" stroke-linecap="round"/>'
             f'<path d="M 4 222 C 40 155 120 40 150 -78" fill="none" stroke="{stem_c}" stroke-width="10" stroke-linecap="round"/>')
    out += L('s', stems)
    gA = A(P, Gc, True, 7)
    lv = leaf(8, 222, 78, 32, -64, gA) + leaf(8, 222, 78, 32, 64, gA)
    if not simple: lv += leaf(60, 160, 70, 28, 52, gA)
    out += L('l', lv)
    pet = ''
    for k in range(5):
        a = -82+72*k; ar = math.radians(a); ex, ey = cx+76*math.cos(ar), cy+76*math.sin(ar)
        pet += f'<ellipse cx="{ex:.1f}" cy="{ey:.1f}" rx="60" ry="76" transform="rotate({a+90} {ex:.1f} {ey:.1f})"/>'
    out += L('p', union(P, pet, PK, 10))
    if not mono and not simple:
        vein = ''.join(f'<line x1="{cx+50*math.cos(math.radians(-82+72*k)):.1f}" y1="{cy+50*math.sin(math.radians(-82+72*k)):.1f}" x2="{cx+112*math.cos(math.radians(-82+72*k)):.1f}" y2="{cy+112*math.sin(math.radians(-82+72*k)):.1f}" stroke="{PK2}" stroke-opacity=".5" stroke-width="4" stroke-linecap="round"/>' for k in range(5))
        out += L('v', vein)
    eye = f'<circle cx="{cx}" cy="{cy}" r="46" fill="{PK2 if not mono else P["bg"]}" {MST(P, 8)}/>' + f'<circle cx="{cx}" cy="{cy}" r="32" {A(P, S, True, 8)}/>'
    if not mono and not simple: eye += f'<circle cx="{cx-9}" cy="{cy-10}" r="8" fill="#FFFFFF" fill-opacity=".6"/>'
    out += L('e', eye)
    bx, by_ = 150, -118
    bud = (f'<ellipse cx="{bx}" cy="{by_}" rx="30" ry="46" transform="rotate(24 {bx} {by_})" {A(P, PK, False, 8)}/>'
           f'<path d="M {bx-14} {by_+36} Q {bx+8} {by_-4} {bx+10} {by_-44}" fill="none" stroke="{PK2 if not mono else ink}" stroke-width="5" stroke-linecap="round" transform="rotate(24 {bx} {by_})"/>')
    out += L('b', bud)
    if not simple: out += L('d', spark(-196, -176, 16, S if not mono else ink) + spark(214, 30, 11, S if not mono else ink))
    return out

# ===== 10 琺瑯圓徽·每天（金邊徽章）：金邊琺瑯圓徽，上緣一圈「每天，一小段晴」，圓心一顆小太陽，一圈小圓點 =====
def s10(P, simple=False):
    ink = P['ink']; mono = P.get('mono'); S = P['S']
    defs_ = ('<linearGradient id="gd" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F7DB95"/><stop offset=".5" stop-color="#D9A648"/><stop offset="1" stop-color="#F0C971"/></linearGradient>' + SUNG(P, 'g10'))
    face_c = CARD(P)
    if mono: rim = f'<circle cx="0" cy="0" r="250" fill="{P["bg"]}" stroke="{ink}" stroke-width="12"/><circle cx="0" cy="0" r="226" fill="none" stroke="{ink}" stroke-width="4"/>'
    else: rim = f'<g filter="url(#sh)"><circle cx="0" cy="0" r="250" fill="url(#gd)"/></g><circle cx="0" cy="0" r="226" fill="none" stroke="{shade(S, -.3)}" stroke-width="3" stroke-opacity=".6"/>'
    out = defs_ + L('a', rim)
    out += L('f', f'<circle cx="0" cy="0" r="214" fill="{face_c}" {("stroke=%s stroke-width=6" % (chr(34)+ink+chr(34))) if mono else ""}/>')
    if not mono and not simple:
        out += L('q', f'<path d="M {240*math.cos(math.radians(200)):.1f} {240*math.sin(math.radians(200)):.1f} A 240 240 0 0 1 {240*math.cos(math.radians(262)):.1f} {240*math.sin(math.radians(262)):.1f}" fill="none" stroke="#FFFFFF" stroke-opacity=".55" stroke-width="8" stroke-linecap="round"/>')
    sr = 54 if not simple else 100
    if not simple:
        defs2 = '<path id="arcT" d="M -156 0 A 156 156 0 0 1 156 0" fill="none"/><path id="arcB" d="M -190 0 A 190 190 0 0 0 190 0" fill="none"/>'
        out = defs2 + out
        fam = FONTS['sans'][0]
        out += L('t', f'<text font-family="{fam}" font-weight="700" font-size="38" letter-spacing="6" fill="{ink}"><textPath href="#arcT" startOffset="50%" text-anchor="middle">每天，一小段晴</textPath></text>')
        out += L('u', f'<text font-family="{fam}" font-weight="700" font-size="38" letter-spacing="14" fill="{ink}"><textPath href="#arcB" startOffset="50%" text-anchor="middle">日日小晴</textPath></text>')
        dots = ''.join(f'<circle cx="{124*math.cos(math.radians(k*22.5)):.1f}" cy="{124*math.sin(math.radians(k*22.5)):.1f}" r="{7 if k % 2 == 0 else 5}" fill="{(S if k % 2 == 0 else P["T"]) if not mono else ink}"/>' for k in range(16))
        out += L('d', dots)
        out += L('x', spark(-173, 0, 13, S if not mono else ink) + spark(173, 0, 13, S if not mono else ink))
    sn = sun_rays(0, 0, sr+14, sr+36 if not simple else sr+30, 12, 11 if not simple else 16, S if not mono else ink) + f'<circle cx="0" cy="0" r="{sr}" {SF(P, "g10", 10)}/>'
    out += L('s', sn)
    return out

# ===== 11 底片三日（底片）：三格底片＝前天、昨天、今天；天氣一格比一格亮，最後一格是小小的晴 =====
def s11(P, simple=False):
    ink = P['ink']; mono = P.get('mono'); S = P['S']
    film = ink if mono else ('#4A3F36' if DK(P) else '#2F2824')
    sky = P['soft'] if not mono else P['bg']; cl_ = P['C'] if not mono else P['bg']
    fw, fh, y1 = 142, 120, -76
    xs = [-235+i*164 for i in range(3)]
    defs_ = ''.join(f'<clipPath id="fc{i}"><rect x="{x}" y="{y1}" width="{fw}" height="{fh}" rx="10"/></clipPath>' for i, x in enumerate(xs))
    out = defs_ + '<g transform="rotate(-6)">'
    out += L('a', f'<rect x="-255" y="-128" width="510" height="226" rx="18" fill="{film}"/>')
    if not simple:
        holes = ''.join(f'<rect x="{-243+i*36}" y="{yy}" width="24" height="17" rx="5" fill="{P["bg"]}"/>' for i in range(14) for yy in (-111, 63))
        out += L('h', holes)
    fr = ''
    # 前天：雲滿滿的
    fr += f'<g clip-path="url(#fc0)"><rect x="{xs[0]}" y="{y1}" width="{fw}" height="{fh}" fill="{sky}"/>' + cloud(xs[0]+68, y1+100, .52, cl_, ink if mono else None, 5) + '</g>'
    # 昨天：太陽探出雲縫
    fr += f'<g clip-path="url(#fc1)"><rect x="{xs[1]}" y="{y1}" width="{fw}" height="{fh}" fill="{sky}"/><circle cx="{xs[1]+88}" cy="{y1+44}" r="30" {A(P, S, True, 6)}/>' + cloud(xs[1]+58, y1+112, .46, cl_, ink if mono else None, 5) + '</g>'
    # 今天：小小的晴
    sx_, sy_ = xs[2]+66, y1+54
    fr += (f'<g clip-path="url(#fc2)"><rect x="{xs[2]}" y="{y1}" width="{fw}" height="{fh}" fill="{sky}"/>' + sun_rays(sx_, sy_, 38, 54, 8, 8, S if not mono else ink)
           + f'<circle cx="{sx_}" cy="{sy_}" r="27" {A(P, S, True, 6)}/>' + cloud(xs[2]+112, y1+112, .2, cl_, ink if mono else None, 4) + '</g>')
    out += L('f', fr)
    if not simple:
        out += L('x', f'<rect x="{xs[2]-8}" y="{y1-8}" width="{fw+16}" height="{fh+16}" rx="14" fill="none" stroke="{S if not mono else P["bg"]}" stroke-width="5"/>')
        lab = ''.join(TX(t, 'sans', 34, x+fw/2, 160, ink, anchor='middle', ls=4, bold=0) for t, x in zip(('前天', '昨天', '今天'), xs))
        out += L('t', lab)
    else:
        out += L('x', f'<rect x="{xs[2]-8}" y="{y1-8}" width="{fw+16}" height="{fh+16}" rx="14" fill="none" stroke="{S if not mono else P["bg"]}" stroke-width="7"/>')
    return out + '</g>'

# ===== 12 老花磚（復古花磚）：四片一樣的花磚拼成地板，四個四分之一太陽在接縫中央拼出一整顆小太陽 =====
def s12(P, simple=False):
    ink = P['ink']; mono = P.get('mono'); S = P['S']
    defs_ = grain_defs() + '<clipPath id="c12"><rect x="-222" y="-222" width="444" height="444" rx="24"/></clipPath>'
    grout = P['C'] if not mono else ink
    out = defs_ + L('g', f'<rect x="-222" y="-222" width="444" height="444" rx="26" fill="{grout}"/>')
    tiles = ''
    tcol = [P['M'], P['soft'], P['soft'], P['M']]
    orn = ''
    fl_col = [P['T'], P['B'], P['G'], P['T']]
    k = 0
    for sy in (-1, 1):
        for sx in (-1, 1):
            x0, y0 = (4 if sx > 0 else -218), (4 if sy > 0 else -218)
            fill = A(P, tcol[k], (k in (0, 3)), 0) if not mono else ('fill="url(#hatch)"' if k in (0, 3) else f'fill="{P["bg"]}"')
            tiles += f'<rect x="{x0}" y="{y0}" width="214" height="214" rx="16" {fill}/>'
            for rr_, ww in ((100, 6), (114, 4)):
                a0, a1 = math.radians(14), math.radians(76)
                p0 = (sx*rr_*math.cos(a0), sy*rr_*math.sin(a0)); p1 = (sx*rr_*math.cos(a1), sy*rr_*math.sin(a1))
                sweep = 1 if sx*sy > 0 else 0
                orn += f'<path d="M {p0[0]:.1f} {p0[1]:.1f} A {rr_} {rr_} 0 0 {sweep} {p1[0]:.1f} {p1[1]:.1f}" fill="none" stroke="{ink if mono else fl_col[k]}" stroke-width="{ww}" stroke-linecap="round"/>'
            fx, fy = sx*111, sy*111
            if not simple:
                orn += ''.join(f'<circle cx="{fx+14*dx}" cy="{fy+14*dy}" r="14" fill="{ink if mono else fl_col[k]}" fill-opacity="{1 if mono else .9}"/>' for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)))
                orn += f'<circle cx="{fx}" cy="{fy}" r="8" fill="{P["bg"] if mono else S}"/>'
                dx_, dy_ = sx*190, sy*190
                orn += f'<rect x="{dx_-9}" y="{dy_-9}" width="18" height="18" transform="rotate(45 {dx_} {dy_})" fill="{ink if mono else fl_col[k]}" fill-opacity=".85"/>'
            else:
                orn += f'<circle cx="{fx}" cy="{fy}" r="26" fill="{ink if mono else fl_col[k]}"/>'
            k += 1
    out += L('a', tiles)
    if not mono and not simple: out += L('n', '<g clip-path="url(#c12)"><rect x="-222" y="-222" width="444" height="444" filter="url(#gr)" opacity=".5"/></g>')
    out += L('o', orn)
    sr = 56 if not simple else 70
    sn = sun_rays(0, 0, sr+9, sr+22, 12, 10 if not simple else 14, S if not mono else ink) + f'<circle cx="0" cy="0" r="{sr}" {A(P, S, True, 9)}/>'
    out += L('s', sn)
    return out

STYLES = [
 # 序號、資料夾名、名稱、風格、含義、符號函式、字標字型、字距、符號縮放、44px 自評(待填)、配角、質感、簡化版拿掉什麼、日日→、小晴→
 (1, '01_雙日一大一小', '雙日·一大一小', '平塗＋紙感', '兩顆太陽並排：大的是今天、小的是明天，小太陽旁還有一朵小雲：日子一天接一天，晴也不用很大。', s1, 'sans', 14, 1.1, '', '小雲、兩顆閃光、淡色底圓', '漸層太陽、紙面顆粒', '小雲、閃光、紙面顆粒、光芒交錯長短', '兩顆太陽並排（今天＋明天）', '右邊那顆小太陽＋旁邊的小雲，小小的剛剛好'),
 (2, '02_習字格日日', '習字格·日日', '練習簿／紙膠帶', '兩格習字格：左格寫下一個「日」，右格同位置畫上一顆小太陽：今天寫一格，明天畫一格。', s2, 'kai', 12, 1.1, '', '米字虛線、紙膠帶、「每天一格」小字、星星貼紙', '紙張陰影、紙膠帶斜紋', '紙膠帶、虛線、小字、星星', '兩個格子：左格「日」字、右格太陽，一天一格', '右格裡小小的一顆太陽，還貼了一顆小星星'),
 (3, '03_日出雙峰條紋', '日出雙峰·條紋', '70 年代復古條紋', '同一條地平線上升起兩個日出（一大一小），日身被條紋切開、水面映出光條：日出接日出。', s3, 'serif', 14, 1.1, '', '條紋雲、水面光條、閃光', '日身條紋、光條漸淡', '條紋雲、光條、閃光、日身條紋', '同一條地平線上兩個日出（日出到日出）', '右邊較小的日出與淡雲，只升起半個，是小小的晴'),
 (4, '04_網點日子', '網點日子', '半色調網點', '一天一顆圓點，由灰到暖、由小漸大，排到最後一顆是帶網點光芒的太陽：日子累積起來就是晴。', s4, 'sans', 14, 1.1, '', '七顆圓點、光芒網點圈、角落漸淡網點、閃光', '圓點高光、網點漸淡', '圓點高光、角落網點、閃光', '一排圓點，每顆是一天，一顆接一顆', '最後一顆太陽不大，用網點圈出一小段光'),
 (5, '05_日日地平線', '日日地平線', '字體設計（日字格）', '兩個「日」字格底邊連成一條長長的地平線，兩日之間升起一顆小太陽：日日相連，中間就是晴。', s5, 'serif', 14, 1.1, '', '光條倒影、小雲、閃光、兩格亮度不同', '字格填色、光條倒影', '光條倒影、小雲、閃光', '兩個「日」字相連，底邊就是同一條地平線', '兩日之間升起的半顆小太陽'),
 (6, '06_日晷', '日晷', '黃銅刻度盤', '黃銅日晷：一圈 24 格刻度，指針的影子只有短短一小段，盤面上亮著一顆小太陽。', s6, 'serif', 14, 1.1, '', '24 格刻度、鉚釘、短影子、指針', '黃銅漸層、鉚釘高光', '鉚釘、細刻度', '日晷的刻度一天走一圈，日復一日', '盤面上的小太陽與短短一小段影子'),
 (7, '07_日輪年輪', '日輪·年輪', '木質切片', '一圈年輪等於一天，圈圈疊起來；最中心是一點亮亮的小太陽，旁邊有兩道樹皮裂紋。', s7, 'kai', 12, 1.1, '', '年輪×5、樹皮邊、裂紋、圓心光暈', '木紋圈、裂紋、樹皮短弧', '樹皮短弧、裂紋、部分年輪', '一圈一圈的年輪，每圈是一天', '圓心那一小點太陽'),
 (8, '08_色票扇', '色票扇', '印刷色票', '七片色票攤成一把扇，每片一天，由陰天灰一路變亮；最後一片的尖端是一顆小太陽。', s8, 'sans', 14, 1.1, '', '七片色票、打孔、軸釘、閃光', '色票高光邊、打孔', '打孔、高光、閃光', '七片色票＝七天，逐日變亮', '最亮那片尖端的小太陽'),
 (9, '09_日日春', '日日春', '膠彩花卉', '「日日春」是真的花名、天天開花：一朵盛開、一朵含苞，盛開那朵的花心是一顆小太陽。', s9, 'kai', 12, 1.1, '', '含苞的第二朵、莖與三片葉、花瓣紋、閃光', '花瓣紋、高光、閃光', '花瓣紋、一片葉、閃光', '花名就叫日日春，今天開一朵、明天含一朵', '花心那顆小太陽'),
 (10, '10_琺瑯圓徽每天', '琺瑯圓徽·每天', '金邊琺瑯徽章', '金邊圓徽，上緣一圈「每天，一小段晴」，下緣「日日小晴」，一圈 16 個小圓點像一個個日子，圓心是小太陽。', s10, 'sans', 14, 1.1, '', '環字、圓點圈、閃光、金邊高光', '環字、圓點圈、金邊高光', '兩圈環字、圓點圈、閃光', '外圈「每天」與一圈圓點（一點一天）', '圓心的小太陽與「一小段晴」'),
 (11, '11_底片三日', '底片三日', '底片格', '三格底片是前天、昨天、今天：天氣一格比一格亮，最後一格是小小的晴。', s11, 'sans', 14, 1.1, '', '底片孔、三格標籤、今天高亮框', '底片孔、標籤', '底片孔、標籤', '三格底片＝三天，一格一天', '第三格「今天」裡小小的太陽'),
 (12, '12_老花磚', '老花磚', '復古花磚', '四片一樣的花磚拼成地板，花紋在接縫中央圍出一顆小太陽：同樣的日子重複鋪下去，就拼出晴。', s12, 'serif', 14, 1.1, '', '四片花磚、弧線紋、四瓣花、菱形點、磚面顆粒', '花瓣、菱形點、顆粒', '花瓣、菱形點、顆粒', '同一片花磚重複四次，日復一日', '接縫中央那顆小太陽'),
]
def avatar_svg(P, sym, k, bg=True):
    b = f'<rect width="1080" height="1080" fill="{P["bg"]}"/>' if bg else ''
    return f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1080" height="1080" viewBox="0 0 1080 1080"><defs>{defs(P)}</defs>{b}<g transform="translate(540 540) scale({k})">{sym}</g></svg>'
def text_w(s, kind, fs, ls):
    f = ImageFont.truetype(FONTS[kind][2], fs); return f.getlength(s) + ls*(len(s)-1)
WH = 420
def wm_svg(P, n, sym, kind, ls, k, sub, bg=True):
    ink = P['ink']; bgr = f'<rect width="{{W}}" height="{WH}" fill="{P["bg"]}"/>' if bg else ''
    fs = 150 if not sub else 134
    ty = 210 if not sub else 170
    symsz = 372
    tw = text_w(NAME, kind, fs, ls); x0 = 60 + symsz + 54; W = int(x0 + tw + 70)
    body = L('sym', f'<g transform="translate({60+symsz/2} 210) scale({k})">{sym}</g>')
    body += L('txt', TX(NAME, kind, fs, x0, ty+.36*fs, ink, ls=ls, bold=3 if kind == 'kai' else 0))
    if sub:
        body += L('sub', TX(SUB, 'sans', 44, x0, 345, ink, ls=7))
    return f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{WH}" viewBox="0 0 {W} {WH}"><defs>{defs(P)}</defs>{bgr.replace("{W}", str(W))}{body}</svg>', W

if __name__ == '__main__':
    import re
    jobs = []; meta = []
    for (n, fo, nm, sty, mean, fn, kind, ls, k, self44, added, tex, simp, rr, xq) in STYLES:
        os.makedirs(fo, exist_ok=True)
        meta.append(dict(n=n, dir=fo, name=nm, style=sty, mean=mean, kind=kind, self44=self44, added=added, texture=tex, simple=simp, rr=rr, xq=xq))
        far1 = FIT.get(str(n), 300); ka = min(420/far1, 1.6); kw = min(172/far1, 1.2)
        meta[-1].update(far1=far1, ka=ka, kw=kw)
        for tag, P in TONES.items():
            sym = fn(P); sv = avatar_svg(P, sym, ka); p = f'{fo}/頭像_1080方_{tag}'; open(p+'.svg', 'w').write(sv)
            jobs.append(dict(n=n, kind='avatar', tag=tag, svg=p+'.svg', png=p+'.png', w=1080, h=1080))
            sv = avatar_svg(P, fn(P, True), ka); p = f'{fo}/頭像_簡化小圖版1080方_{tag}'; open(p+'.svg', 'w').write(sv)
            jobs.append(dict(n=n, kind='avatar_s', tag=tag, svg=p+'.svg', png=p+'.png', w=1080, h=1080))
            for sub, suf in ((False, '字標'), (True, '字標含副標')):
                sv, W = wm_svg(P, n, sym, kind, ls, kw, sub); p = f'{fo}/{suf}_{tag}'; open(p+'.svg', 'w').write(sv)
                jobs.append(dict(n=n, kind='wmsub' if sub else 'wm', tag=tag, svg=p+'.svg', png=p+'.png', w=W, h=WH))
                if not TONES[tag].get('mono'):
                    sv, W = wm_svg(P, n, sym, kind, ls, kw, sub, bg=False); p = f'{fo}/{suf}_透明_{tag}'; open(p+'.svg', 'w').write(sv)
                    jobs.append(dict(n=n, kind='wmT', tag=tag, svg=p+'.svg', png=p+'.png', w=W, h=WH, transparent=True))
        P = TONES['奶油晨光']; sym = fn(P)
        open(f'{CHK}/av{n}.svg', 'w').write(avatar_svg(P, sym, ka, bg=False)); open(f'{CHK}/av{n}_1.svg', 'w').write(avatar_svg(P, sym, 1.0, bg=False))
        open(f'{CHK}/avs{n}.svg', 'w').write(avatar_svg(P, fn(P, True), ka, bg=False))
        jobs.append(dict(n=n, kind='chk_av', svg=f'{CHK}/av{n}.svg', png=f'{CHK}/av{n}_all.png', w=1080, h=1080, transparent=True))
        jobs.append(dict(n=n, kind='chk_av1', svg=f'{CHK}/av{n}_1.svg', png=f'{CHK}/av{n}_1.png', w=1080, h=1080, transparent=True))
        jobs.append(dict(n=n, kind='chk_avs', svg=f'{CHK}/avs{n}.svg', png=f'{CHK}/avs{n}_all.png', w=1080, h=1080, transparent=True))
        for lay in sorted(set(re.findall(r'data-layer="(\w+)"', sym))):
            jobs.append(dict(n=n, kind='chk_layer', layer=lay, svg=f'{CHK}/av{n}.svg', png=f'{CHK}/av{n}_{lay}.png', w=1080, h=1080, transparent=True, show=[lay]))
        for sub in (False, True):
            sv, W = wm_svg(P, n, sym, kind, ls, kw, sub, bg=False); open(f'{CHK}/wm{n}{"s" if sub else ""}.svg', 'w').write(sv)
            for lay in ('sym', 'txt', 'sub'):
                if f'data-layer="{lay}"' in sv:
                    jobs.append(dict(n=n, kind='chk_wm', sub=sub, layer=lay, svg=f'{CHK}/wm{n}{"s" if sub else ""}.svg', png=f'{CHK}/wm{n}{"s" if sub else ""}_{lay}.png', w=W, h=WH, transparent=True, show=[lay]))
            jobs.append(dict(n=n, kind='chk_wm', sub=sub, layer='all', svg=f'{CHK}/wm{n}{"s" if sub else ""}.svg', png=f'{CHK}/wm{n}{"s" if sub else ""}_all.png', w=W, h=WH, transparent=True))
    json.dump(dict(jobs=jobs, meta=meta, tones=TONES), open('jobs.json', 'w'), ensure_ascii=False)
    print(len(jobs), 'jobs')
