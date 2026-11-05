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

