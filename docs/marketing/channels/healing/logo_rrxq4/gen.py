# 「日日小晴」LOGO 第四輪 12 款（2026-11-05）：全新方向、明亮悠閒色調、全自繪向量，不用 AI 圖／比比／吉祥物／品牌商標
# 字型只用 ~/.fonts 的 Noto Sans/Serif CJK TC 與霞鶩文楷（OFL）
# 重跑：python3 gen.py && node render.js && python3 compose.py
import json, math, os, random
from PIL import ImageFont
H = os.path.dirname(os.path.abspath(__file__)); os.chdir(H)
CHK = '/tmp/claude-0/-home-user-tw-rotation/ce50d787-1067-5482-ab44-99dc39a48890/scratchpad/rrxq4_chk'
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

# ===== 第四輪 12 款符號（座標約 ±270，之後由 fit.json 自動縮放）=====
# 第四輪主軸：Andy 11-05「再多點素材，我覺得可以更好」→ 主元素＋2～4 個配角＋質感細節；每款附「簡化小圖版」（simple=True）供 110／44px 頭像
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

# ===== 1 一筆圓相·暈彩（書法＋淡彩）：一筆圓相，後面暈開三色淡彩，圈裡一點太陽，右下蓋一枚「晴」小印 =====
def s1(P, simple=False):
    ink = P['ink']; mono = P.get('mono'); S = P['S']
    defs_ = '<filter id="hb" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="24"/></filter>'
    halo = ''
    if not mono:
        halo = (f'<g filter="url(#hb)" opacity=".8"><circle cx="-34" cy="-30" r="132" fill="{S}" fill-opacity=".62"/><circle cx="50" cy="42" r="120" fill="{P["B"]}" fill-opacity=".2"/>'
                f'<circle cx="-62" cy="58" r="88" fill="{P["G"]}" fill-opacity=".16"/></g>')
    a0, sw = -35, 320; outer = []; inner = []; N = 120
    for i in range(N+1):
        t = i/N; a = math.radians(a0+sw*t); R = 170+9*math.sin(2*math.pi*t*1.3+.5)
        wd = 64*(1-.8*t**1.7) if t > .06 else 40+24*(t/.06)
        outer.append(((R+wd/2)*math.cos(a), (R+wd/2)*math.sin(a))); inner.append(((R-wd/2)*math.cos(a), (R-wd/2)*math.sin(a)))
    d = 'M ' + ' L '.join(f'{x:.1f} {y:.1f}' for x, y in outer+inner[::-1]) + ' Z'
    rnd = random.Random(3); arcs = ''
    for dr in (-24, -12, 0, 12, 24):
        t0 = rnd.uniform(.5, .62); t1 = rnd.uniform(.82, .97)
        pts = ' L '.join(f'{(170+dr)*math.cos(math.radians(a0+sw*(t0+(t1-t0)*q/20))):.1f} {(170+dr)*math.sin(math.radians(a0+sw*(t0+(t1-t0)*q/20))):.1f}' for q in range(21))
        arcs += f'<path d="M {pts}" fill="none" stroke="#000" stroke-width="4" stroke-linecap="round"/>'
    defs_ += f'<mask id="mk1" maskUnits="userSpaceOnUse" x="-300" y="-300" width="600" height="600"><rect x="-300" y="-300" width="600" height="600" fill="#fff"/>{arcs}</mask>'
    brush = f'<g filter="url(#rough)"><path d="{d}" fill="{ink}" mask="url(#mk1)"/></g>'
    dot = f'<circle cx="-24" cy="-20" r="44" fill="{lightfill(P)}" stroke="{ink if mono else "none"}" stroke-width="12"/>'
    sealc = ink if mono else ('#E8694A' if DK(P) else '#D9573A'); charc = P['bg'] if mono else '#FFF6E5'
    seal = f'<rect x="38" y="36" width="46" height="46" rx="8" fill="{sealc}" transform="rotate(-6 61 59)"/>'
    schar = TX('晴', 'sans', 30, 61, 71, charc, anchor='middle', extra='transform="rotate(-6 61 59)"')
    out = defs_ + L('h', halo) + L('a', brush) + L('b', dot) + L('c', seal) + L('e', schar)
    if not simple:
        out += L('d', spark(97, -139, 20, S if not mono else ink) + spark(-190, 150, 14, S if not mono else ink) + spark(-200, -118, 10, P['B'] if not mono else ink))
    return out

# ===== 2 黏土小日子（黏土立體）：圓胖太陽、小雲、一株小芽、小草，腳下一圈柔影 =====
def s2(P, simple=False):
    ink = P['ink']; mono = P.get('mono'); S = P['S']; Gc = P['G']
    cl2 = '#8A7A68' if DK(P) else P['C']
    defs_ = (f'<radialGradient id="cg" cx=".35" cy=".3" r=".85"><stop offset="0" stop-color="{shade(S, .5)}"/><stop offset=".55" stop-color="{S}"/><stop offset="1" stop-color="{shade(S, -.22)}"/></radialGradient>'
             f'<radialGradient id="cg2" cx=".35" cy=".3" r=".9"><stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="{cl2}"/></radialGradient>'
             f'<linearGradient id="cg3" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{shade(Gc, .38)}"/><stop offset="1" stop-color="{shade(Gc, -.18)}"/></linearGradient>'
             '<filter id="bl" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="6"/></filter>')
    sy = -50; rays_ = ''
    for k in range(10):
        a = math.radians(k*36-90); x1, y1, x2, y2 = 160*math.cos(a), sy+160*math.sin(a), 198*math.cos(a), sy+198*math.sin(a)
        if mono: rays_ += line(x1, y1, x2, y2, 38, ink)
        else: rays_ += line(x1, y1, x2, y2, 38, shade(S, .08)) + line(x1+(x2-x1)*.1-4, y1+(y2-y1)*.1-6, x1+(x2-x1)*.7-4, y1+(y2-y1)*.7-6, 8, shade(S, .55))
    if mono: sun = f'<circle cx="0" cy="{sy}" r="136" fill="url(#hatch)" stroke="{ink}" stroke-width="14"/>'
    else:
        sun = f'<g filter="url(#sh)"><circle cx="0" cy="{sy}" r="136" fill="url(#cg)"/></g><ellipse cx="-58" cy="{sy-82}" rx="46" ry="24" transform="rotate(-35 -58 {sy-82})" fill="#FFFFFF" opacity=".5" filter="url(#bl)"/>'
        if not simple:   # 指紋壓痕
            for (dx, dy, rx_) in ((50, -20, 9), (72, 20, 7), (-60, 30, 8), (10, 62, 7), (-20, -40, 6)):
                sun += f'<ellipse cx="{dx}" cy="{sy+dy}" rx="{rx_}" ry="{rx_*.55:.1f}" fill="{shade(S, -.3)}" opacity=".28" transform="rotate(-20 {dx} {sy+dy})"/>'
    cloud_ = (f'<g fill="none" stroke="{ink}" stroke-width="8"/>' if False else '')
    cloud_ = cloud(168, 140, .5, P['bg'], ink, 9) if mono else f'<g filter="url(#sh)"><g fill="url(#cg2)">{cloud_parts(168, 140, .5)}</g></g>'
    out = defs_ + L('g', '' if mono else '<ellipse cx="0" cy="232" rx="215" ry="22" fill="#5A4636" opacity=".17" filter="url(#bl)"/>' if True else '')
    out += L('a', rays_) + L('b', sun) + L('c', cloud_)
    if not simple:
        gA = A(P, 'url(#cg3)', True, 8)
        stem = f'<path d="M -200 232 Q -203 205 -198 180" fill="none" stroke="{ink if mono else shade(Gc, -.2)}" stroke-width="9" stroke-linecap="round"/>'
        sp = stem + leaf(-198, 184, 50, 26, -38, gA) + leaf(-198, 184, 46, 24, 36, gA)
        gr = ''.join(leaf(140+dx, 230, ln, 11, ang, gA) for dx, ln, ang in ((-18, 40, -26), (0, 48, 0), (18, 38, 26)))
        out += L('d', sp) + L('e', gr)
    return out

# ===== 3 搪瓷晴招牌·雙框（復古招牌）：放射光芒、雙層邊框、鉚釘、一排小圓點、下方一條小字帶 =====
def s3(P, simple=False):
    ink = P['ink']; mono = P.get('mono'); bg = P['bg']; wd = ''
    cy = 0 if simple else -22; n = 12 if simple else 24
    for k in range(n):
        a0 = math.radians(k*360/n-90); a1 = math.radians((k+1)*360/n-90)
        f = (P['S'] if k % 2 == 0 else P['soft']) if not mono else ('url(#hatch)' if k % 2 == 0 else bg)
        wd += f'<path d="M 0 {cy} L {420*math.cos(a0):.1f} {cy+420*math.sin(a0):.1f} L {420*math.cos(a1):.1f} {cy+420*math.sin(a1):.1f} Z" fill="{f}"/>'
    defs_ = '<clipPath id="cl3"><rect x="-190" y="-190" width="380" height="380" rx="30"/></clipPath>'
    plate = f'<rect x="-240" y="-240" width="480" height="480" rx="62" fill="{ink}"/>'
    if not simple: plate += f'<rect x="-226" y="-226" width="452" height="452" rx="50" fill="none" stroke="{bg}" stroke-width="4"/>'
    out = defs_ + L('a', plate) + L('w', f'<g clip-path="url(#cl3)">{wd}</g>')
    if not simple:
        dots = ''
        for t in range(-162, 163, 36):
            for (x, y) in ((t, -208), (t, 208), (-208, t), (208, t)): dots += f'<circle cx="{x}" cy="{y}" r="8" fill="{bg}"/>'
        riv = ''.join(f'<circle cx="{sx*208}" cy="{sy*208}" r="14" fill="{bg}"/><circle cx="{sx*208-3}" cy="{sy*208-3}" r="5" fill="{ink}" fill-opacity=".35"/>' for sx in (-1, 1) for sy in (-1, 1))
        out += L('f', dots + riv)
    r = 128 if simple else 112
    out += L('b', f'<circle cx="0" cy="{cy}" r="{r}" fill="{bg}" stroke="{ink}" stroke-width="10"/>')
    gs = 170 if simple else 150; x, y = gp('晴', 'serif', gs, 0, cy+2)
    out += L('c', TX('晴', 'serif', gs, x, y, ink, bold=2))
    if not simple:
        bf = ink if mono else ink
        out += L('d', f'<rect x="-150" y="112" width="300" height="58" rx="16" fill="{bf}" stroke="{bg}" stroke-width="4"/>')
        tcol = bg
        out += L('e', TX('每天，一小段晴', 'sans', 32, 0, 152, tcol, anchor='middle', ls=4))
    return out

# ===== 4 繡布章·彩線（刺繡布章）：圓布章、鎖邊四色線、跑針圈、緞面繡太陽＋小雲＋小草＋十字繡 =====
def s4(P, simple=False):
    ink = P['ink']; mono = P.get('mono'); S = P['S']
    th = [ink]*4 if mono else [S, P['T'], P['G'], P['B']]
    sc = ink if mono else shade(S, -.3)
    defs_ = (f'<pattern id="sat" width="11" height="11" patternUnits="userSpaceOnUse" patternTransform="rotate(35)"><rect width="11" height="11" fill="{P["bg"] if mono else S}"/>'
             f'<line x1="0" y1="0" x2="0" y2="11" stroke="{ink if mono else shade(S, -.18)}" stroke-width="{4 if mono else 3}"/></pattern>'
             f'<pattern id="sat2" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(-30)"><rect width="9" height="9" fill="{P["bg"] if mono else ("#FFFFFF" if not DK(P) else "#CFC2AE")}"/>'
             f'<line x1="0" y1="0" x2="0" y2="9" stroke="{ink if mono else P["B"]}" stroke-width="{3 if mono else 2}" stroke-opacity="{1 if mono else .55}"/></pattern>')
    base = f'<circle cx="0" cy="0" r="244" fill="{P["bg"] if mono else P["M"]}" stroke="{ink}" stroke-width="{8 if mono else 0}"/>'
    N = 40 if simple else 56; st = ''
    for k in range(N):
        a = math.radians(k*360/N); st += line(212*math.cos(a), 212*math.sin(a), 240*math.cos(a), 240*math.sin(a), 8 if simple else 7, th[k % 4])
    base += st + f'<circle cx="0" cy="0" r="212" fill="none" stroke="{th[0]}" stroke-width="5"/>'
    out = defs_ + L('a', base)
    sy = -48 if not simple else -10; rr = 84 if not simple else 100
    sun = f'<circle cx="0" cy="{sy}" r="{rr}" fill="url(#sat)"/><circle cx="0" cy="{sy}" r="{rr+8}" fill="none" stroke="{sc}" stroke-width="10" stroke-dasharray="5 4"/>'
    for k in range(10):
        a = math.radians(k*36-90); r1, r2 = rr+22, rr+46
        sun += line(r1*math.cos(a), sy+r1*math.sin(a), r2*math.cos(a), sy+r2*math.sin(a), 15, sc if k % 2 == 0 else (ink if mono else shade(S, .15)))
    out += L('b', sun)
    if not simple:
        out += L('r', f'<circle cx="0" cy="0" r="203" fill="none" stroke="{ink}" stroke-opacity="{1 if mono else .55}" stroke-width="5" stroke-dasharray="14 12" stroke-linecap="round"/>')
        out += L('c', cloud(-84, 130, .38, 'url(#sat2)', P['B'] if not mono else ink, 5))
        gr = ''.join(line(98+dx*0, 140, 98+dx, 140-h, 9, th[2] if not mono else ink) for dx, h in ((-22, 38), (-8, 52), (8, 52), (22, 38)))
        gr = ''.join(line(98, 140, 98+dx, 140-h, 9, th[2]) for dx, h in ((-24, 40), (-9, 54), (9, 54), (24, 40)))
        out += L('d', gr)
        xs = ''
        for (x, y) in ((-122, -122), (126, -118)):
            xs += line(x-7, y-7, x+7, y+7, 5, th[1]) + line(x-7, y+7, x+7, y-7, 5, th[1])
        xs += f'<circle cx="-160" cy="-50" r="6" fill="{th[0]}"/><circle cx="162" cy="-48" r="6" fill="{th[3]}"/>'
        out += L('e', xs)
    return out

# ===== 5 霓虹晴·小夜燈（霓虹燈）：燈泡圈＋霓虹環＋「晴」字管＋三顆閃光，暗板上的光 =====
def s5(P, simple=False):
    mono = P.get('mono'); tube = P['bg'] if mono else P['S']; gcol = P['bg'] if mono else '#FFF0D2'
    fs = 235 if simple else 200; gx, gy = gp('晴', 'sans', fs, 0, 6)
    FAM = FONTS['sans'][0]
    out = '<filter id="glow" x="-30%" y="-30%" width="160%" height="160%"><filter/></filter>'.replace('<filter/>', '<feGaussianBlur stdDeviation="11"/>')
    out += L('a', f'<circle cx="0" cy="0" r="270" fill="{P["ink"] if mono else P["D"]}"/>')
    out += L('b', f'<circle cx="0" cy="0" r="215" fill="none" stroke="{tube}" stroke-width="13"/>')
    out += L('c', f'<text x="{gx:.1f}" y="{gy:.1f}" font-family="{FAM}" font-weight="700" font-size="{fs}" fill="{gcol}" fill-opacity="{1 if mono else .22}" stroke="{gcol}" stroke-width="7" stroke-linejoin="round">晴</text>')
    if not mono:
        out += L('d', f'<g filter="url(#glow)" opacity=".85"><circle cx="0" cy="0" r="215" fill="none" stroke="{tube}" stroke-width="20"/>'
                      f'<text x="{gx:.1f}" y="{gy:.1f}" font-family="{FAM}" font-weight="700" font-size="{fs}" fill="none" stroke="{P["S"]}" stroke-width="14">晴</text></g>')
    if not simple:
        bl = ''.join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="8" fill="{tube if i % 2 == 0 else (gcol if not mono else tube)}" fill-opacity="{1 if i % 2 == 0 else .75}"/>' for i, (x, y) in enumerate(ring_pts(244, 24, -90)))
        out += L('e', bl)
        out += L('f', spark(-122, -122, 17, tube) + spark(124, 122, 13, tube) + spark(128, -116, 9, gcol))
    return out

# ===== 6 絹印·三色（Risograph）：橘太陽、藍雲、綠葉三版疊印，網點、顆粒、套準十字 =====
def s6(P, simple=False):
    ink = P['ink']; mono = P.get('mono'); B2 = P['B']; Gc = P['G']; S = P['S']
    defs_ = (f'<pattern id="dt" width="17" height="17" patternUnits="userSpaceOnUse"><circle cx="8.5" cy="8.5" r="4.6" fill="{B2}" fill-opacity="{1 if mono else .8}"/></pattern>'
             '<linearGradient id="fd" x1="1" y1="0" x2="0" y2="1"><stop offset=".25" stop-color="#000"/><stop offset=".75" stop-color="#fff"/></linearGradient>'
             '<mask id="mfd" maskUnits="userSpaceOnUse" x="-300" y="-300" width="600" height="600"><rect x="-300" y="-300" width="600" height="600" fill="url(#fd)"/></mask>'
             '<filter id="spk" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="1" seed="2" result="n"/>'
             '<feColorMatrix in="n" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -9 5.5" result="m"/><feComposite in="SourceGraphic" in2="m" operator="in"/></filter>')
    bm = 'opacity:.88' if DK(P) else 'mix-blend-mode:multiply'
    out = defs_
    if not simple: out += L('a', f'<circle cx="0" cy="0" r="238" fill="url(#dt)" mask="url(#mfd)"/>')
    if mono:
        sun = f'<circle cx="-35" cy="-45" r="140" fill="url(#hatch)" stroke="{ink}" stroke-width="14"/>'
        cl = f'<g fill="{ink}" transform="translate(40 -5)">{cloud_parts(70, 190, 1.05)}</g>'
    else:
        flt = '' if simple else 'filter="url(#spk)"'
        sun = f'<g {flt}><circle cx="-35" cy="-45" r="140" fill="{S}"/></g>'
        if not simple: sun += f'<circle cx="-27" cy="-38" r="140" fill="none" stroke="{P["T"]}" stroke-opacity=".7" stroke-width="5"/>'   # 錯位的粉橘描邊
        cl = f'<g {flt} fill="{B2}" transform="translate(40 -5)" style="{bm}">{cloud_parts(70, 190, 1.05)}</g>'
    out += L('b', sun) + L('c', cl)
    if not simple:
        gA = f'fill="{Gc if not mono else ink}"' + ('' if mono else f' style="{bm}"')
        lv = leaf(-170, 218, 96, 40, -30, gA) + leaf(-170, 218, 84, 36, 28, gA) + f'<path d="M -170 220 L -170 196" stroke="{Gc if not mono else ink}" stroke-width="8" stroke-linecap="round"/>'
        out += L('d', lv)
        rc = ink if mono else P['T']
        reg = ''.join(f'<circle cx="{x}" cy="{y}" r="13" fill="none" stroke="{rc}" stroke-width="4"/>' + line(x-22, y, x+22, y, 4, rc) + line(x, y-22, x, y+22, 4, rc) for (x, y) in ((-196, -176), (206, -150)))
        out += L('e', reg)
    return out

# ===== 7 圓形徽章（徽章）：郵票鋸齒邊、深色緞帶環、底部弧形「日日小晴」、三顆小星，中間太陽與小山 =====
def s7(P, simple=False):
    ink = P['ink']; mono = P.get('mono'); S = P['S']; Gc = P['G']
    band_r, band_w = (236, 40) if simple else (228, 60)
    defs_ = f'<clipPath id="cl7"><circle cx="0" cy="0" r="{band_r-band_w/2+2}"/></clipPath>'
    R0 = band_r+band_w/2+2
    bumps = ''.join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="12" {A(P, S, True, 8)}/>' for x, y in ring_pts(R0+4, 30))
    base = bumps + f'<circle cx="0" cy="0" r="{R0+4}" {A(P, S, True, 8)}/>'
    base += f'<circle cx="0" cy="0" r="{band_r}" fill="none" stroke="{ink}" stroke-width="{band_w}"/>'
    out = defs_ + L('a', base)
    ir = band_r-band_w/2
    sun_y = -8; sr = 66
    inner = f'<circle cx="0" cy="0" r="{ir}" {A(P, P["soft"])} />' + (f'<circle cx="0" cy="0" r="{ir}" fill="none" stroke="{S}" stroke-width="5"/>' if not mono else '')
    sc = f'<g clip-path="url(#cl7)">'
    for k in range(9):
        a = math.radians(180+k*22.5)
        sc += line((sr+16)*math.cos(a), sun_y+(sr+16)*math.sin(a), (sr+42)*math.cos(a), sun_y+(sr+42)*math.sin(a), 12, P['S'] if not mono else ink)
    sc += f'<circle cx="0" cy="{sun_y}" r="{sr}" {A(P, S, True, 10)}/>'
    h1 = f'M -220 52 Q -110 -8 0 40 T 220 30 L 220 220 L -220 220 Z'; h2 = f'M -220 112 Q -90 62 40 108 T 220 96 L 220 220 L -220 220 Z'
    sc += f'<path d="{h1}" {A(P, shade(Gc, .3), False, 8)}/><path d="{h2}" {A(P, Gc, True, 8)}/>'
    if not simple:
        for (x, y, c) in ((-100, 140, '#FFFFFF'), (60, 150, S), (130, 128, '#FFFFFF')): sc += f'<circle cx="{x}" cy="{y}" r="9" fill="{ink if mono else c}"/>'
    out += L('b', inner + sc + '</g>')
    if not simple:
        R = 244; x1, y1, x2, y2 = -R*math.cos(math.radians(32)), R*math.sin(math.radians(32)), R*math.cos(math.radians(32)), R*math.sin(math.radians(32))
        out_defs = f'<path id="arc7" d="M {x1:.1f} {y1:.1f} A {R} {R} 0 0 0 {x2:.1f} {y2:.1f}" fill="none"/>'
        txt = f'<text font-family="{FONTS["sans"][0]}" font-weight="700" font-size="46" letter-spacing="14" fill="{P["bg"]}"><textPath href="#arc7" startOffset="50%" text-anchor="middle">日日小晴</textPath></text>'
        out = out_defs + out + L('c', txt)
        st = ''.join(spark(228*math.cos(math.radians(a)), 228*math.sin(math.radians(a)), r_, S if not mono else P['bg']) for a, r_ in ((-90, 15), (-62, 11), (-118, 11)))
        out += L('d', st)
    return out

# ===== 8 窗景圓框（窗景）：圓窗外是晴空、太陽、白雲、遠山，窗台上一盆小植物和一杯熱茶 =====
def s8(P, simple=False):
    ink = P['ink']; mono = P.get('mono'); S = P['S']; Gc = P['G']; T = P['T']
    cy, Ro, Ri = -14, 215, 182
    wood = T if not mono else P['bg']
    defs_ = (f'<clipPath id="cl8"><circle cx="0" cy="{cy}" r="{Ri}"/></clipPath>'
             f'<linearGradient id="sk8" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{P["soft"]}"/><stop offset="1" stop-color="{shade(P["soft"], .6)}"/></linearGradient>')
    fr = f'<circle cx="0" cy="{cy}" r="{Ro-20}" fill="none" stroke="{wood if not mono else ink}" stroke-width="40"/>' + (f'<circle cx="0" cy="{cy}" r="{Ro}" fill="none" stroke="{ink}" stroke-width="8"/><circle cx="0" cy="{cy}" r="{Ri}" fill="none" stroke="{ink}" stroke-width="8"/>' if mono else f'<circle cx="0" cy="{cy}" r="{Ro-2}" fill="none" stroke="{shade(T, -.2)}" stroke-width="5"/>')
    bar = line(0, cy-Ri, 0, cy+Ri, 14, wood if not mono else ink) + line(-Ri, cy, Ri, cy, 14, wood if not mono else ink)
    sc = f'<g clip-path="url(#cl8)"><rect x="-200" y="{cy-200}" width="400" height="400" fill="{P["bg"] if mono else "url(#sk8)"}"/>'
    sc += f'<circle cx="104" cy="{cy-96}" r="{58 if not simple else 64}" {A(P, S, True, 8)}/>'
    if not mono: sc += f'<circle cx="104" cy="{cy-96}" r="80" fill="{S}" fill-opacity=".22"/>'
    sc += cloud(-92, cy-52, .34, '#FFFFFF' if not DK(P) else '#E8DCC8', ink if mono else None, 6)
    sc += f'<path d="M -200 {cy+62} Q -110 {cy+8} -20 {cy+58} T 200 {cy+44} L 200 {cy+200} L -200 {cy+200} Z" {A(P, shade(Gc, .35), False, 8)}/>'
    sc += f'<path d="M -200 {cy+110} Q -90 {cy+62} 30 {cy+108} T 200 {cy+96} L 200 {cy+200} L -200 {cy+200} Z" {A(P, Gc, True, 8)}/></g>'
    out = defs_ + L('g', sc) + L('f', fr + bar)
    sill_y = 178
    out += L('s', f'<rect x="-196" y="{sill_y}" width="392" height="32" rx="10" {A(P, shade(T, -.12) if not mono else P["bg"], False, 8)}/>')
    gA = A(P, Gc, True, 7); pot = f'<path d="M -146 128 L -74 128 L -84 {sill_y} L -136 {sill_y} Z" {A(P, T, False, 8)}/><rect x="-154" y="116" width="88" height="16" rx="6" {A(P, shade(T, -.12) if not mono else P["bg"], False, 8)}/>'
    pl = leaf(-110, 118, 70, 32, -38, gA) + leaf(-110, 118, 90, 34, 2, gA) + leaf(-110, 118, 66, 30, 40, gA)
    out += L('p', pl + pot)
    cup = f'<ellipse cx="108" cy="{sill_y-4}" rx="58" ry="9" {A(P, "#FFFFFF" if not DK(P) else "#CFC2AE", False, 7)}/>'
    cup += f'<path d="M 72 122 L 144 122 Q 142 {sill_y-10} 108 {sill_y-10} Q 74 {sill_y-10} 72 122 Z" {A(P, "#FFFFFF" if not DK(P) else "#E8DCC8", False, 8)}/>'
    cup += f'<path d="M 144 134 Q 172 134 168 156 Q 164 170 138 166" fill="none" stroke="{ink if mono else ("#FFFFFF" if not DK(P) else "#E8DCC8")}" stroke-width="{8 if mono else 9}" stroke-linecap="round"/>'
    if not mono: cup += f'<ellipse cx="108" cy="122" rx="36" ry="6" fill="{shade(T, -.1)}" opacity=".75"/>'
    out += L('c', cup)
    if not simple:
        stm = ''.join(f'<path d="M {x} 100 q -12 -16 0 -30 q 12 -16 0 -30" fill="none" stroke="{ink}" stroke-opacity="{1 if mono else .45}" stroke-width="6" stroke-linecap="round"/>' for x in (92, 124))
        out += L('t', stm)
    return f'<g transform="translate(0 14)">{out}</g>'

# ===== 9 小物圍日（生活小物）：圓托盤上，植物、書、咖啡杯、光斑圍著中間的太陽 =====
def s9(P, simple=False):
    ink = P['ink']; mono = P.get('mono'); S = P['S']; Gc = P['G']; T = P['T']; B2 = P['B']
    wh = '#FFFFFF' if not DK(P) else '#E8DCC8'
    tray = f'<circle cx="0" cy="0" r="262" {A(P, P["soft"], False, 10)}/>'
    if not mono:
        tray = f'<g filter="url(#sh)"><circle cx="0" cy="0" r="262" fill="{shade(T, .2) if not DK(P) else P["D"]}"/></g><circle cx="0" cy="0" r="246" fill="{P["soft"]}"/>'
        if not simple: tray += f'<circle cx="0" cy="0" r="236" fill="none" stroke="{T}" stroke-opacity=".25" stroke-width="3"/><circle cx="0" cy="0" r="222" fill="none" stroke="{T}" stroke-opacity=".18" stroke-width="3"/>'
    out = L('a', tray)
    sun = ''.join(line(100*math.cos(math.radians(a)), 100*math.sin(math.radians(a)), 128*math.cos(math.radians(a)), 128*math.sin(math.radians(a)), 14, S if not mono else ink) for a in (45, 135, 225, 315))
    sun += f'<circle cx="0" cy="0" r="76" {A(P, S, True, 10)}/>'
    out += L('b', sun)
    gA = A(P, Gc, True, 7)
    pl = leaf(0, -168, 62, 28, -36, gA) + leaf(0, -168, 76, 30, 2, gA) + leaf(0, -168, 58, 26, 38, gA)
    pl += f'<path d="M -34 -170 L 34 -170 L 25 -122 L -25 -122 Z" {A(P, T, False, 8)}/><rect x="-42" y="-182" width="84" height="16" rx="6" {A(P, shade(T, -.12) if not mono else P["bg"], False, 8)}/>'
    out += L('c', pl)
    cx, cy0 = -176, 0
    cup = f'<ellipse cx="{cx}" cy="48" rx="56" ry="9" {A(P, wh, False, 7)}/><path d="M {cx-38} -10 L {cx+38} -10 Q {cx+36} 46 {cx} 46 Q {cx-36} 46 {cx-38} -10 Z" {A(P, wh, False, 8)}/>'
    cup += f'<path d="M {cx-38} 4 Q {cx-62} 4 {cx-58} 24 Q {cx-54} 38 {cx-34} 34" fill="none" stroke="{ink if mono else wh}" stroke-width="{8 if mono else 9}" stroke-linecap="round"/>'
    if not mono: cup += f'<ellipse cx="{cx}" cy="-10" rx="38" ry="6" fill="{shade(T, -.35)}"/>'
    if not simple: cup += ''.join(f'<path d="M {cx+dx} -24 q -10 -14 0 -26 q 10 -14 0 -26" fill="none" stroke="{ink}" stroke-opacity="{1 if mono else .45}" stroke-width="5" stroke-linecap="round"/>' for dx in (-12, 12))
    out += L('d', cup)
    bk = f'<rect x="120" y="14" width="112" height="30" rx="6" {A(P, B2, True, 8)}/><rect x="132" y="-16" width="96" height="30" rx="6" {A(P, T, False, 8)}/>'
    if not mono: bk += f'<rect x="126" y="22" width="100" height="6" fill="#FFFFFF" fill-opacity=".7"/><rect x="138" y="-8" width="84" height="6" fill="#FFFFFF" fill-opacity=".5"/>'
    out += L('e', bk)
    ls = ''.join(f'<circle cx="{x}" cy="{y}" r="{r_}" fill="{S if not mono else ink}" fill-opacity="{o}"/>' for x, y, r_, o in ((-24, 186, 22, 1), (22, 200, 14, .8), (52, 176, 9, .6)))
    out += L('f', ls)
    return out

# ===== 10 旅行貼紙（復古貼紙）：白邊貼紙，海平面升起的太陽、三層海浪、小雲，下方「晴天到此一遊」標籤 =====
def s10(P, simple=False):
    ink = P['ink']; mono = P.get('mono'); S = P['S']; B2 = P['B']; rot = -6
    wh = P['bg'] if mono else '#FFFFFF'
    defs_ = '<clipPath id="cl10"><circle cx="0" cy="0" r="226"/></clipPath>'
    body = f'<g filter="url(#sh)"><circle cx="0" cy="0" r="238" fill="{wh}" {("stroke=%s stroke-width=%s" % (chr(34)+ink+chr(34), chr(34)+"8"+chr(34))) if mono else ""}/></g>'
    body += f'<circle cx="0" cy="0" r="224" {A(P, P["soft"], False, 8)}/>'
    if not mono and not simple: body += f'<circle cx="0" cy="0" r="210" fill="none" stroke="{wh}" stroke-opacity=".9" stroke-width="4" stroke-dasharray="12 9"/>'
    sy = 12; sun = '<g clip-path="url(#cl10)">'
    for k in range(11):
        a = math.radians(190+k*16)
        sun += line(112*math.cos(a), sy+112*math.sin(a), 142*math.cos(a), sy+142*math.sin(a), 13, S if not mono else ink)
    sun += f'<circle cx="0" cy="{sy}" r="90" {A(P, S, True, 10)}/></g>'
    sea = '<g clip-path="url(#cl10)">'
    for k, col in enumerate((shade(B2, .45), shade(B2, .15), B2)):
        y = 50+k*48; d = f'M -240 {y} '
        for i in range(-4, 5): d += f'q 30 -22 60 0 '
        d = f'M -240 {y} ' + ' '.join(['q 30 -20 60 0']*8) + ' L 240 260 L -240 260 Z'
        sea += f'<path d="{d}" {A(P, col, k % 2 == 0, 8)}/>'
    sea += '</g>'
    out = defs_ + f'<g transform="rotate({rot})">' + L('a', body) + L('b', sun) + L('c', sea)
    out += L('d', cloud(-62, -160, .26, '#FFFFFF' if not DK(P) else '#E8DCC8', ink if mono else None, 6))
    if not simple:
        out += L('e', f'<rect x="-128" y="108" width="256" height="58" rx="14" fill="{wh if mono else "#FFFFFF" if not DK(P) else P["D"]}" stroke="{ink}" stroke-width="5"/>')
        out += L('f', TX('晴天到此一遊', 'sans', 31, 0, 148, ink, anchor='middle', ls=5))
        out += L('g', spark(138, -92, 14, S if not mono else ink) + spark(130, -146, 10, S if not mono else ink))
    return out + '</g>'

# ===== 11 日日勾勾（日曆）：日曆卡，已完成的日子打勾，今天畫一顆大太陽，右下再一個手寫勾 =====
def s11(P, simple=False):
    ink = P['ink']; mono = P.get('mono'); S = P['S']; Gc = P['G']; card = CARD(P)
    defs_ = '<clipPath id="cl11"><rect x="-190" y="-225" width="380" height="440" rx="38"/></clipPath>'
    cd = f'<g filter="url(#sh)"><rect x="-190" y="-225" width="380" height="440" rx="38" fill="{card}"/></g><rect x="-190" y="-225" width="380" height="440" rx="38" fill="none" stroke="{ink}" stroke-width="{10 if mono else 6}" stroke-opacity="{1 if mono else .55}"/>'
    out = defs_ + L('a', cd)
    hf = ink if mono else S
    out += L('h', f'<g clip-path="url(#cl11)"><rect x="-190" y="-225" width="380" height="88" fill="{hf}"/></g>')
    if not simple:
        tc = P['bg'] if mono else check_col(P, S)
        out += L('p', ''.join(f'<circle cx="{x}" cy="-181" r="10" fill="{card if not mono else P["bg"]}" stroke="{ink}" stroke-opacity=".5" stroke-width="4"/>' for x in (-148, 148)))
        out += L('t', TX('今天，晴', 'sans', 44, 0, -166, tc, anchor='middle', ls=6))
        bx = ''
        for i, x in enumerate((-136, -68, 0, 68, 136)):
            if i < 4:
                bx += f'<rect x="{x-26}" y="-116" width="52" height="52" rx="12" fill="none" stroke="{ink}" stroke-opacity="{1 if mono else .5}" stroke-width="5"/>'
                bx += f'<path d="M {x-13} -90 Q {x-6} -80 {x-2} -72 Q {x+6} -96 {x+14} -106" fill="none" stroke="{ink if mono else Gc}" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>'
            else:
                bx += f'<rect x="{x-26}" y="-116" width="52" height="52" rx="12" fill="none" stroke="{ink if mono else S}" stroke-width="5" stroke-dasharray="8 7"/>'
        out += L('x', bx)
    sx, sy = -30, 80; rr = 70
    sun = ''.join(line((rr+14)*math.cos(math.radians(a))+sx, (rr+14)*math.sin(math.radians(a))+sy, (rr+38)*math.cos(math.radians(a))+sx, (rr+38)*math.sin(math.radians(a))+sy, 14, S if not mono else ink) for a in range(0, 360, 45))
    sun += f'<circle cx="{sx}" cy="{sy}" r="{rr}" {A(P, S, True, 10)}/>'
    out += L('b', sun)
    ck = f'<path d="M 112 150 Q 122 162 130 176 Q 146 142 164 122" fill="none" stroke="{ink if mono else Gc}" stroke-width="15" stroke-linecap="round" stroke-linejoin="round"/>'
    out += L('c', ck)
    return out

# ===== 12 剪紙層疊（剪紙）：四層彩紙疊起來——天空、太陽（兩色）、白雲、兩層山丘和小紙花 =====
def s12(P, simple=False):
    ink = P['ink']; mono = P.get('mono'); S = P['S']; Gc = P['G']
    sky = shade(P['B'], .28) if not mono else P['bg']
    defs_ = ('<filter id="ps" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="6" stdDeviation="4" flood-color="#5A4636" flood-opacity=".32"/></filter>'
             '<clipPath id="cl12"><circle cx="0" cy="0" r="240"/></clipPath>')
    F = '' if (mono or simple) else 'filter="url(#ps)"'
    pts = [(R*math.cos(t), R*math.sin(t)) for t in [math.radians(i*2) for i in range(180)] for R in [242+6*math.cos(16*t)]]
    sky_d = 'M ' + ' L '.join(f'{x:.1f} {y:.1f}' for x, y in pts) + ' Z'
    out = defs_ + L('a', f'<g {F}><path d="{sky_d}" {A(P, sky, False, 10)}/></g>')
    sy = -58
    bumps = ''.join(f'<circle cx="{x:.1f}" cy="{sy+y:.1f}" r="20"/>' for x, y in ring_pts(132, 16))
    sun = f'<g {F}><g {A(P, S, True, 10)}>{bumps}<circle cx="0" cy="{sy}" r="132"/></g></g>'
    sun += f'<circle cx="0" cy="{sy}" r="90" {A(P, shade(S, .5) if not mono else P["bg"], False, 8)}/>'
    if not simple and not mono:
        sun += ''.join(f'<circle cx="{x:.1f}" cy="{sy+y:.1f}" r="7" fill="{S}"/>' for x, y in ring_pts(112, 12, 15)) 
    out += L('b', sun)
    wh = '#FFFFFF' if not DK(P) else '#E8DCC8'
    cl = f'<g {F}>{cloud(-62, 38, .7, wh if not mono else P["bg"], ink if mono else None, 8)}</g><g {F}>{cloud(172, -118, .32, wh if not mono else P["bg"], ink if mono else None, 6)}</g>'
    out += L('c', cl)
    h1 = 'M -250 96 Q -130 24 -20 92 T 250 74 L 250 260 L -250 260 Z'; h2 = 'M -250 170 Q -110 112 50 166 T 250 150 L 250 260 L -250 260 Z'
    hills = f'<g clip-path="url(#cl12)"><g {F}><path d="{h1}" {A(P, shade(Gc, .35), False, 9)}/></g><g {F}><path d="{h2}" {A(P, Gc, True, 9)}/></g></g>'
    out += L('d', hills)
    if not simple:
        fl = ''
        for (x, y) in ((-128, 134), (6, 150), (124, 122)):
            fl += line(x, y, x, y+34, 6, ink if mono else shade(Gc, -.25))
            fl += f'<circle cx="{x}" cy="{y}" r="17" {A(P, wh, False, 7)}/><circle cx="{x}" cy="{y}" r="7" fill="{ink if mono else S}"/>'
        out += L('e', fl)
    return out

STYLES = [
 # 序號、資料夾名、名稱、風格、含義、符號函式、字標字型、字距、符號縮放、44px 自評、升級自、配角、質感、簡化版拿掉什麼
 (1, '01_一筆圓相暈彩', '一筆圓相·暈彩', '書法筆觸＋淡彩（升級自第三輪 08）', '一筆畫圓、留個口，後面暈開今天的淡彩，圈裡一點太陽，右下蓋一枚「晴」小印：今天畫完了。', s1, 'kai', 12, 1.1, '', '三色淡彩光暈、「晴」字小印、三顆閃光', '乾筆飛白、水彩暈開、印章微斜', '拿掉閃光'),
 (2, '02_黏土小日子', '黏土小日子', '黏土立體（升級自第三輪 06）', '捏出來的圓胖太陽、小雲、一株小芽和一撮小草，腳下一圈柔軟的影子：平凡的一天，什麼都剛剛好。', s2, 'sans', 14, 1.1, '', '小雲、小芽（兩片葉）、小草、地面柔影', '漸層高光、指紋壓痕、柔影', '拿掉小芽、小草、指紋壓痕'),
 (3, '03_搪瓷晴招牌雙框', '搪瓷晴招牌·雙框', '復古招牌（升級自第三輪 10）', '老街的搪瓷招牌加了雙層邊框、鉚釘和一條小字帶：放射的光芒中間一個「晴」，底下寫著「每天，一小段晴」。', s3, 'serif', 14, 1.1, '', '雙層邊框＋一圈小圓點、四角鉚釘、小字帶「每天，一小段晴」', '放射光芒、鉚釘高光', '拿掉邊框圈點、鉚釘、小字帶，光芒減半，晴字放大'),
 (4, '04_繡布章彩線', '繡布章·彩線', '刺繡布章（升級自第三輪 04）', '圓布章用四色線鎖邊、跑針繞一圈，中間繡太陽，旁邊還繡了小雲、小草：一針一線，慢慢繡出一天。', s4, 'kai', 12, 1.1, '', '四色鎖邊線、跑針圈、小雲、小草、十字繡與線結', '緞面繡斜紋、鎖邊針腳、跑針虛線', '拿掉跑針圈、小雲、小草、十字繡，太陽放大'),
 (5, '05_霓虹晴小夜燈', '霓虹晴·小夜燈', '霓虹燈（升級自第三輪 03）', '戲院門口那種燈泡圈圍著一個亮著的「晴」，旁邊閃兩三下：下班路上，巷口還有一盞燈等你。', s5, 'sans', 14, 1.1, '', '一圈小燈泡、三顆霓虹閃光', '外發光、燈管描邊、燈泡明暗交錯', '拿掉燈泡圈與閃光，「晴」字放大'),
 (6, '06_絹印三色', '絹印·三色', '絹印 Risograph（升級自第三輪 09）', '橘太陽、藍雲、綠葉三版故意錯位疊印，帶著網點和油墨顆粒：手作的、有一點不整齊的好天氣。', s6, 'sans', 14, 1.1, '', '綠葉、網點底紋、套準十字', '油墨顆粒、錯位描邊、乘算疊色', '拿掉網點、綠葉、套準十字、顆粒'),
 (7, '07_圓形徽章', '圓形徽章', '徽章／郵票鋸齒邊（新構圖）', '鋸齒邊的圓徽章：中間太陽照著小山丘，深色緞帶環上寫著「日日小晴」，頂端三顆小星。', s7, 'serif', 14, 1.1, '', '鋸齒外緣、深色緞帶環、底部弧形字「日日小晴」、三顆小星、小山丘與小花', '鋸齒邊、緞帶環、弧形字', '拿掉弧形字、小星、小花，緞帶環變細'),
 (8, '08_窗景圓框', '窗景圓框', '窗景插畫（新構圖）', '圓窗外是晴天的太陽、白雲和遠山，窗台上一盆小植物、一杯冒煙的熱茶：在家裡也看得到一小段晴。', s8, 'serif', 14, 1.1, '', '晴空太陽、白雲、遠山兩層、窗台、盆栽、熱茶與蒸氣', '木窗框、天空漸層、茶杯與盆栽', '拿掉蒸氣，太陽放大'),
 (9, '09_小物圍日', '小物圍日', '生活小物組合（新構圖）', '圓托盤上，植物、書、咖啡杯和光斑圍著中間一顆太陽：生活裡的小東西，湊在一起就是一小段晴。', s9, 'sans', 14, 1.1, '', '盆栽、咖啡杯（蒸氣）、書堆、光斑、圓托盤木紋', '托盤木紋、托盤陰影、杯口咖啡色', '拿掉蒸氣、托盤木紋圈'),
 (10, '10_旅行貼紙', '旅行貼紙', '復古旅行貼紙（新構圖）', '一張貼在行李上的圓貼紙：太陽從海平面升起，三層海浪，底下寫著「晴天到此一遊」。', s10, 'sans', 14, 1.1, '', '海平面升起的太陽、三層海浪、小雲、「晴天到此一遊」標籤、兩顆閃光', '白色切割邊＋陰影、虛線縫線、貼紙微斜', '拿掉標籤與字、閃光、縫線'),
 (11, '11_日日勾勾', '日日勾勾', '日曆＋手寫勾勾（新構圖）', '日曆上前幾天都打了勾，今天這格畫一顆大太陽，右下再補一個手寫的勾：又完成了一天。', s11, 'sans', 14, 1.1, '', '橘色頁首「今天，晴」、五格打勾欄、大太陽、手寫大勾勾、裝訂孔', '卡片陰影、手寫勾勾的筆畫起伏', '拿掉標題字、裝訂孔、打勾欄'),
 (12, '12_剪紙層疊', '剪紙層疊', '多層剪紙（新構圖）', '四層彩紙疊出一小段晴：天空、鋸齒邊的太陽、白雲、兩層山丘，前面還插著三朵紙花。', s12, 'serif', 14, 1.1, '', '兩層山丘、白雲×2、太陽兩層紙、三朵紙花', '層層投影、波浪紙邊、太陽鋸齒邊與小孔', '拿掉紙花、太陽小孔與投影'),
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
    for (n, fo, nm, sty, mean, fn, kind, ls, k, self44, added, tex, simp) in STYLES:
        os.makedirs(fo, exist_ok=True)
        meta.append(dict(n=n, dir=fo, name=nm, style=sty, mean=mean, kind=kind, self44=self44, added=added, texture=tex, simple=simp))
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
