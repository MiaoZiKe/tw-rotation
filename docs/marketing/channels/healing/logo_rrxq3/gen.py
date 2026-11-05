# 「日日小晴」LOGO 第三輪 12 款（2026-11-05）：全新方向、明亮悠閒色調、全自繪向量，不用 AI 圖／比比／吉祥物／品牌商標
# 字型只用 ~/.fonts 的 Noto Sans/Serif CJK TC 與霞鶩文楷（OFL）
# 重跑：python3 gen.py && node render.js && python3 compose.py
import json, math, os, random
from PIL import ImageFont
H = os.path.dirname(os.path.abspath(__file__)); os.chdir(H)
CHK = '/tmp/claude-0/-home-user-tw-rotation/ce50d787-1067-5482-ab44-99dc39a48890/scratchpad/rrxq3_chk'
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

# ===== 第三輪 12 款符號（座標約 ±270，之後由 fit.json 自動縮放）=====
# 第三輪主軸：Andy 11-05「這名稱不是貓咪」→ 從名稱本身「日日（每一天）＋小晴（一小段晴）」出發，不用動物，12 種畫法彼此差很多
def shade(h, f):
    """f>0 往白、f<0 往黑混。"""
    h = h.lstrip('#'); c = [int(h[i:i+2], 16) for i in (0, 2, 4)]
    c = [round(x+(255-x)*f) if f > 0 else round(x*(1+f)) for x in c]
    return '#%02X%02X%02X' % tuple(c)
def _lum(h):
    h = h.lstrip('#'); c = [int(h[i:i+2], 16)/255 for i in (0, 2, 4)]
    c = [x/12.92 if x <= .03928 else ((x+.055)/1.055)**2.4 for x in c]; return .2126*c[0]+.7152*c[1]+.0722*c[2]
def _cr(a, b):
    x, y = sorted([_lum(a), _lum(b)], reverse=True); return (x+.05)/(y+.05)
def SF(P): return P['bg'] if P.get('mono') else P['S']   # 太陽實心色（單色版用底色＋描邊）

# ===== 1 三圈漸亮（極簡幾何）：虛線圈→實線圈→填滿的太陽，一天比一天亮 =====
def s1(P):
    ink = P['ink']; mono = P.get('mono')
    c1 = f'<circle cx="0" cy="73" r="40" fill="none" stroke="{ink}" stroke-width="14" stroke-dasharray="3 19" stroke-linecap="round"/>'
    c2 = f'<circle cx="157" cy="38" r="72" fill="none" stroke="{ink}" stroke-width="20"/>'
    c3 = f'<circle cx="379" cy="8" r="112" fill="{lightfill(P) if mono else P["S"]}" stroke="{ink if mono else "none"}" stroke-width="14"/>'
    base = line(-47, 170, 491, 170, 14, ink)
    return '<g transform="translate(-222 -35)">' + L('a', c1 + c2) + L('b', c3) + L('c', base) + '</g>'

# ===== 2 撕頁日曆（日曆撕頁）：一頁一頁撕下來的日子，今天這頁畫著小太陽 =====
def s2(P):
    ink = P['ink']; mono = P.get('mono'); w = 12
    st = ''
    for off, fill in ((28, P['M'] if not mono else P['bg']), (14, P['soft'])):
        st += f'<rect x="{-170+off}" y="{-200+off}" width="340" height="380" rx="18" fill="{fill}" stroke="{ink}" stroke-width="{w}" stroke-linejoin="round"/>'
    pts = ''.join(f' L {-170+i*34} {-200 if i % 2 == 0 else -182}' for i in range(0, 11))
    page = f'<path d="M -170 -200{pts} L 170 -200 L 170 110 L 100 180 L -170 180 Z" fill="{P["soft"] if not mono else P["bg"]}" stroke="{ink}" stroke-width="{w}" stroke-linejoin="round"/>'
    page += f'<path d="M 170 110 L 100 180 L 100 110 Z" fill="{P["M"] if not mono else P["bg"]}" stroke="{ink}" stroke-width="{w}" stroke-linejoin="round"/>'
    page += f'<circle cx="0" cy="-30" r="78" fill="{lightfill(P)}" stroke="{ink}" stroke-width="12"/>' + rays(0, -30, 104, 130, 8, 14, ink)
    page += line(-110, 150, 30, 150, 12, ink)
    return L('a', st) + L('b', page)

# ===== 3 霓虹晴（霓虹燈）：暗板上的光管，圓是太陽、「晴」是字 =====
def s3(P):
    mono = P.get('mono'); tube = P['bg'] if mono else P['S']; gcol = P['bg'] if mono else '#FFF0D2'
    gx, gy = gp('晴', 'sans', 280, 0, 8)
    disc = f'<circle cx="0" cy="0" r="268" fill="{P["ink"] if mono else P["D"]}"/>'
    ring = f'<circle cx="0" cy="0" r="236" fill="none" stroke="{tube}" stroke-width="14"/>'
    gl = f'<text x="{gx:.1f}" y="{gy:.1f}" font-family="{FONTS["sans"][0]}" font-weight="700" font-size="280" fill="{gcol}" fill-opacity="{1 if mono else .22}" stroke="{gcol}" stroke-width="7" stroke-linejoin="round">晴</text>'
    glow = ''
    if not mono:
        glow = ('<filter id="glow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="11"/></filter>'
                f'<g filter="url(#glow)" opacity=".85"><circle cx="0" cy="0" r="236" fill="none" stroke="{tube}" stroke-width="20"/>'
                f'<text x="{gx:.1f}" y="{gy:.1f}" font-family="{FONTS["sans"][0]}" font-weight="700" font-size="280" fill="none" stroke="{P["S"]}" stroke-width="14">晴</text></g>')
    return L('a', disc) + L('d', glow) + L('b', ring) + L('c', gl)

# ===== 4 繡線太陽（刺繡布章）：緞面繡的太陽，邊緣一圈鎖邊 =====
def s4(P):
    ink = P['ink']; mono = P.get('mono'); bc = ink if mono else P['T']; sc = ink if mono else shade(P['S'], -.3)
    pat = (f'<pattern id="sat" width="11" height="11" patternUnits="userSpaceOnUse" patternTransform="rotate(35)"><rect width="11" height="11" fill="{P["bg"] if mono else P["S"]}"/>'
           f'<line x1="0" y1="0" x2="0" y2="11" stroke="{ink if mono else shade(P["S"], -.18)}" stroke-width="{4 if mono else 3}"/></pattern>')
    base = f'<rect x="-213" y="-213" width="426" height="426" rx="86" fill="{P["bg"] if mono else P["M"]}" stroke="{ink}" stroke-width="{8 if mono else 0}"/>'
    base += f'<rect x="-198" y="-198" width="396" height="396" rx="74" fill="none" stroke="{bc}" stroke-width="28" stroke-dasharray="6 3.5"/>'
    run = f'<rect x="-166" y="-166" width="332" height="332" rx="48" fill="none" stroke="{bc}" stroke-width="6" stroke-dasharray="16 12" stroke-linecap="round"/>'
    sun = f'<circle cx="0" cy="0" r="82" fill="url(#sat)"/><circle cx="0" cy="0" r="90" fill="none" stroke="{sc}" stroke-width="12" stroke-dasharray="5 4"/>'
    for k in range(8):
        a = math.radians(k*45-90)
        sun += line(112*math.cos(a), 112*math.sin(a), 138*math.cos(a), 138*math.sin(a), 16, sc)
    return pat + L('a', base) + L('c', run) + L('b', sun)

# ===== 5 剪紙日花（剪紙）：一張紙剪出放射的太陽花 =====
def s5(P):
    mono = P.get('mono'); col = P['ink'] if mono else P['S']
    bumps = ''.join(f'<circle cx="{232*math.cos(math.radians(k*22.5)):.1f}" cy="{232*math.sin(math.radians(k*22.5)):.1f}" r="26"/>' for k in range(16))
    tear = ''.join(f'<path d="M 0 -190 C 26 -168 30 -140 0 -118 C -30 -140 -26 -168 0 -190 Z" transform="rotate({k*45})"/>' for k in range(8))
    dots = ''.join(f'<circle cx="{190*math.cos(math.radians(k*45+22.5)):.1f}" cy="{190*math.sin(math.radians(k*45+22.5)):.1f}" r="15"/>' for k in range(8))
    mk = (f'<mask id="mk5" maskUnits="userSpaceOnUse" x="-300" y="-300" width="600" height="600"><rect x="-300" y="-300" width="600" height="600" fill="#fff"/>'
          f'<g fill="#000">{tear}{dots}</g><circle cx="0" cy="0" r="86" fill="none" stroke="#000" stroke-width="22"/></mask>')
    body = f'<g fill="{col}" mask="url(#mk5)"><circle cx="0" cy="0" r="232"/>{bumps}</g>'
    return mk + L('a', body)

# ===== 6 黏土太陽（黏土立體）：捏出來的圓胖太陽加一朵小雲 =====
def s6(P):
    ink = P['ink']; mono = P.get('mono'); S = P['S']
    g = (f'<radialGradient id="cg" cx=".35" cy=".3" r=".85"><stop offset="0" stop-color="{shade(S, .5)}"/><stop offset=".55" stop-color="{S}"/><stop offset="1" stop-color="{shade(S, -.22)}"/></radialGradient>'
         f'<radialGradient id="cg2" cx=".35" cy=".3" r=".9"><stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="{P["C"] if P["bg"] != "#1E1A16" else "#8A7A68"}"/></radialGradient>'
         '<filter id="bl" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="6"/></filter>')
    rays_ = ''
    for k in range(10):
        a = math.radians(k*36-90); x1, y1, x2, y2 = 228*math.cos(a), 228*math.sin(a), 254*math.cos(a), 254*math.sin(a)
        if mono: rays_ += line(x1, y1, x2, y2, 40, ink)
        else: rays_ += line(x1, y1, x2, y2, 42, shade(S, .08)) + line(x1+(x2-x1)*.1-5, y1+(y2-y1)*.1-7, x1+(x2-x1)*.7-5, y1+(y2-y1)*.7-7, 9, shade(S, .55))
    if mono:
        sun = f'<circle cx="0" cy="0" r="176" fill="url(#hatch)" stroke="{ink}" stroke-width="16"/>'
        cloud_ = cloud(70, 262, .95, P['bg'], ink, 10)
    else:
        sun = (f'<g filter="url(#sh)"><circle cx="0" cy="0" r="176" fill="url(#cg)"/></g>'
               '<ellipse cx="-72" cy="-100" rx="56" ry="30" transform="rotate(-35 -72 -100)" fill="#FFFFFF" opacity=".5" filter="url(#bl)"/>')
        cloud_ = f'<g filter="url(#sh)"><g fill="url(#cg2)">{cloud_parts(70, 262, .95)}</g></g>'
    return g + L('a', rays_) + L('b', sun) + L('c', cloud_)

# ===== 7 霧玻璃日（玻璃漸層）：太陽隔著一片霧玻璃，模糊也暖 =====
def s7(P):
    ink = P['ink']; mono = P.get('mono'); S = P['S']; B2 = P['B'] if not mono else ink
    gd = (f'<linearGradient id="o1" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{shade(S, .35)}"/><stop offset="1" stop-color="{shade(S, -.1)}"/></linearGradient>'
          f'<linearGradient id="o2" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{shade(B2, .45)}"/><stop offset="1" stop-color="{B2}"/></linearGradient>'
          '<filter id="bl2" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="16"/></filter>'
          '<clipPath id="clg"><rect x="-150" y="-135" width="360" height="330" rx="80"/></clipPath>')
    if mono:
        orbs = f'<circle cx="-60" cy="-70" r="150" fill="url(#hatch)" stroke="{ink}" stroke-width="14"/><circle cx="85" cy="95" r="125" fill="none" stroke="{ink}" stroke-width="16"/>'
        glass = f'<rect x="-150" y="-135" width="360" height="330" rx="80" fill="{P["bg"]}" fill-opacity=".88" stroke="{ink}" stroke-width="14"/>'
    else:
        o = '<circle cx="-60" cy="-70" r="150" fill="url(#o1)"/><circle cx="85" cy="95" r="125" fill="url(#o2)"/>'
        orbs = o
        glass = (f'<g clip-path="url(#clg)"><g filter="url(#bl2)">{o}</g><rect x="-150" y="-135" width="360" height="330" fill="#FFFFFF" fill-opacity=".34"/></g>'
                 f'<rect x="-150" y="-135" width="360" height="330" rx="80" fill="none" stroke="{ink}" stroke-opacity=".4" stroke-width="5"/>'
                 '<rect x="-143" y="-128" width="346" height="316" rx="73" fill="none" stroke="#FFFFFF" stroke-opacity=".85" stroke-width="5"/>')
    return gd + L('a', orbs) + L('b', glass)

# ===== 8 一筆圓相（書法筆觸）：一筆畫圓，留個口，圈裡一點就是「日」 =====
def s8(P):
    ink = P['ink']; mono = P.get('mono')
    a0, sw = -35, 320; outer = []; inner = []; N = 120
    for i in range(N+1):
        t = i/N; a = math.radians(a0+sw*t); R = 170+9*math.sin(2*math.pi*t*1.3+.5)
        wd = 64*(1-.8*t**1.7) if t > .06 else 40+24*(t/.06)
        outer.append((R+wd/2)*math.cos(a)); outer.append((R+wd/2)*math.sin(a)); inner.append((R-wd/2)*math.cos(a)); inner.append((R-wd/2)*math.sin(a))
    po = [(outer[k], outer[k+1]) for k in range(0, len(outer), 2)]; pi_ = [(inner[k], inner[k+1]) for k in range(0, len(inner), 2)][::-1]
    d = 'M ' + ' L '.join(f'{x:.1f} {y:.1f}' for x, y in po+pi_) + ' Z'
    rnd = random.Random(3); arcs = ''
    for dr in (-24, -12, 0, 12, 24):
        t0 = rnd.uniform(.5, .62); t1 = rnd.uniform(.82, .97)
        pts = ' L '.join(f'{(170+dr)*math.cos(math.radians(a0+sw*(t0+(t1-t0)*q/20))):.1f} {(170+dr)*math.sin(math.radians(a0+sw*(t0+(t1-t0)*q/20))):.1f}' for q in range(21))
        arcs += f'<path d="M {pts}" fill="none" stroke="#000" stroke-width="4" stroke-linecap="round"/>'
    mk = f'<mask id="mk8" maskUnits="userSpaceOnUse" x="-300" y="-300" width="600" height="600"><rect x="-300" y="-300" width="600" height="600" fill="#fff"/>{arcs}</mask>'
    brush = f'<g filter="url(#rough)"><path d="{d}" fill="{ink}" mask="url(#mk8)"/></g>'
    dot = f'<circle cx="0" cy="2" r="58" fill="{lightfill(P)}" stroke="{ink if mono else "none"}" stroke-width="12"/>'
    return mk + L('a', brush) + L('b', dot)

# ===== 9 雙色絹印（Risograph）：橘色太陽疊藍色雲，故意錯位的疊印 =====
def s9(P):
    ink = P['ink']; mono = P.get('mono'); B2 = P['B']
    pat = (f'<pattern id="dt" width="17" height="17" patternUnits="userSpaceOnUse"><circle cx="8.5" cy="8.5" r="4.6" fill="{B2}" fill-opacity="{1 if mono else .8}"/></pattern>'
           '<linearGradient id="fd" x1="1" y1="0" x2="0" y2="1"><stop offset=".25" stop-color="#000"/><stop offset=".75" stop-color="#fff"/></linearGradient>'
           '<mask id="mfd" maskUnits="userSpaceOnUse" x="-300" y="-300" width="600" height="600"><rect x="-300" y="-300" width="600" height="600" fill="url(#fd)"/></mask>')
    field = f'<circle cx="0" cy="0" r="238" fill="url(#dt)" mask="url(#mfd)"/>'
    if mono:
        sun = f'<circle cx="-45" cy="-40" r="150" fill="url(#hatch)" stroke="{ink}" stroke-width="14"/>'
        cl = f'<g fill="{ink}" transform="translate(6 -5)">{cloud_parts(70, 190, 1.15)}</g>'
    else:
        bm = 'opacity:.88' if P['bg'] == '#1E1A16' else 'mix-blend-mode:multiply'   # 深色底乘不出來，改半透明疊印
        sun = f'<circle cx="-45" cy="-40" r="150" fill="{P["S"]}"/>'
        cl = f'<g fill="{B2}" transform="translate(6 -5)" style="{bm}">{cloud_parts(70, 190, 1.15)}</g>'
    return pat + L('a', field) + L('b', sun) + L('c', cl)

# ===== 10 搪瓷晴招牌（復古招牌）：老街的搪瓷招牌，光芒放射，中間一個「晴」 =====
def s10(P):
    ink = P['ink']; mono = P.get('mono'); wd = ''
    for k in range(24):
        a0 = math.radians(k*15-90); a1 = math.radians(k*15+15-90)
        f = (P['S'] if k % 2 == 0 else P['soft']) if not mono else ('url(#hatch)' if k % 2 == 0 else P['bg'])
        wd += f'<path d="M 0 0 L {420*math.cos(a0):.1f} {420*math.sin(a0):.1f} L {420*math.cos(a1):.1f} {420*math.sin(a1):.1f} Z" fill="{f}"/>'
    plate = (f'<clipPath id="cl10"><rect x="-200" y="-200" width="400" height="400" rx="34"/></clipPath>'
             f'<rect x="-230" y="-230" width="460" height="460" rx="58" fill="{ink}"/>'
             f'<rect x="-208" y="-208" width="416" height="416" rx="42" fill="none" stroke="{P["bg"]}" stroke-width="5"/>'
             f'<g clip-path="url(#cl10)">{wd}</g>' + ''.join(f'<circle cx="{sx*205}" cy="{sy*205}" r="9" fill="{P["bg"]}"/>' for sx in (-1, 1) for sy in (-1, 1)))
    disc = f'<circle cx="0" cy="0" r="142" fill="{P["bg"]}" stroke="{ink}" stroke-width="12"/>'
    return L('a', plate) + L('b', disc) + L('c', glyph('晴', 'serif', 190, 0, 2, ink, bold=2))

# ===== 11 日日方塊（等距立體）：一大一小兩塊方塊，頂面各有太陽 =====
def s11(P):
    ink = P['ink']; mono = P.get('mono')
    top = P['bg'] if mono else P['soft']; lf = 'url(#hatch)' if mono else P['M']; rt = ink if mono else shade(P['M'], -.2)
    def cube(ox, oy, s):
        c = .866*s; f = f'stroke="{ink}" stroke-width="11" stroke-linejoin="round"'
        Lb, Rb, Bt, Lt, Rt, Tt = (ox-c, oy-.5*s), (ox+c, oy-.5*s), (ox, oy-s), (ox-c, oy-1.5*s), (ox+c, oy-1.5*s), (ox, oy-2*s)
        P_ = lambda *pts: ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts)
        o = f'<polygon points="{P_((ox, oy), Lb, Lt, Bt)}" fill="{lf}" {f}/><polygon points="{P_((ox, oy), Rb, Rt, Bt)}" fill="{rt}" {f}/>'
        o += f'<polygon points="{P_(Bt, Lt, Tt, Rt)}" fill="{top}" {f}/>'
        o += f'<ellipse cx="{ox:.1f}" cy="{oy-1.5*s:.1f}" rx="{.49*s:.1f}" ry="{.283*s:.1f}" fill="{lightfill(P)}" stroke="{ink}" stroke-width="9"/>'
        return o
    return L('a', cube(-96, 160, 150)) + L('b', cube(144, 160, 95))

# ===== 12 日日小晴格（字標排版）：四個字四格，只有「晴」那格點亮 =====
def s12(P):
    ink = P['ink']; mono = P.get('mono'); S = P['S']; til = ''; gl = ''
    pos = [(-118, -118, '日'), (118, -118, '日'), (-118, 118, '小'), (118, 118, '晴')]
    for cx, cy, ch in pos:
        hot = ch == '晴'; fill = S if hot else (P['bg'] if mono else P['soft'])
        til += f'<rect x="{cx-107}" y="{cy-107}" width="214" height="214" rx="46" fill="{fill}" stroke="{ink}" stroke-width="12"/>'
        col = ink if not hot else (ink if _cr(ink, S) >= _cr(P['bg'], S) else P['bg'])
        gl += glyph(ch, 'sans', 150, cx, cy, col)
    return L('a', til) + L('b', gl)

STYLES = [
 # 序號、資料夾名、名稱、風格、含義、符號函式、字標字型、字距、符號縮放、44px 自評
 (1, '01_三圈漸亮', '三圈漸亮', '極簡幾何', '前兩天是空心的圈，今天填成太陽：日日一點一點變亮。', s1, 'sans', 14, 1.1, ''),
 (2, '02_撕頁日曆', '撕頁日曆', '日曆撕頁', '日子就是一頁一頁撕下來的，今天這一頁畫著一顆小太陽。', s2, 'sans', 14, 1.1, ''),
 (3, '03_霓虹晴', '霓虹晴', '霓虹燈', '下班走回巷口，亮著一個「晴」字的小招牌，等你的那盞燈。', s3, 'sans', 14, 1.1, ''),
 (4, '04_繡線太陽', '繡線太陽', '刺繡布章', '一針一線繡出的小太陽，慢慢來，每天繡一點也算數。', s4, 'kai', 12, 1.1, ''),
 (5, '05_剪紙日花', '剪紙日花', '剪紙', '一張紙剪出放射的太陽花，貼在家門口的小喜氣，小小一張也亮。', s5, 'serif', 14, 1.1, ''),
 (6, '06_黏土太陽', '黏土太陽', '黏土立體', '捏出來的圓胖太陽加一朵小雲，圓滾滾、軟軟的，一點都不尖。', s6, 'sans', 14, 1.1, ''),
 (7, '07_霧玻璃日', '霧玻璃日', '玻璃漸層', '太陽隔著一片霧玻璃：看不太清楚也沒關係，光還是透得進來。', s7, 'sans', 14, 1.1, ''),
 (8, '08_一筆圓相', '一筆圓相', '書法筆觸', '一筆畫圓、留個口，圈裡一點就是「日」：每天畫一個，不必畫滿。', s8, 'kai', 12, 1.1, ''),
 (9, '09_雙色絹印', '雙色絹印', '絹印（Risograph）', '橘色的太陽疊上藍色的雲，故意錯位的疊印：雲和晴本來就一起來。', s9, 'sans', 14, 1.1, ''),
 (10, '10_搪瓷晴招牌', '搪瓷晴招牌', '復古招牌', '老街上的搪瓷招牌，光芒向外放射，正中間一個「晴」字。', s10, 'serif', 14, 1.1, ''),
 (11, '11_日日方塊', '日日方塊', '等距立體', '一大一小兩塊方塊並排，頂面各有一顆太陽：大日子小日子，日日有光。', s11, 'sans', 14, 1.1, ''),
 (12, '12_日日小晴格', '日日小晴格', '字標排版', '四個字排成四格，只有「晴」那格點亮成橘色：整個名字就是 LOGO。', s12, 'sans', 14, 1.1, ''),
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
        far1 = FIT.get(str(n), 300); ka = min(420/far1, 1.6); kw = {1: .68}.get(n, min(172/far1, 1.2))  # 款1 是寬扁圖形，字標用寬度配合
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
