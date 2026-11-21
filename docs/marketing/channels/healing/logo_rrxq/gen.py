# 「日日小晴」LOGO 12 款（2026-11-04）：明亮悠閒色調、全自繪向量，不用 AI 圖／比比／吉祥物／品牌商標
# 字型只用 ~/.fonts 的 Noto Sans/Serif CJK TC 與霞鶩文楷（OFL）
# 重跑：python3 gen.py && node render.js && python3 compose.py
import json, math, os, random
from PIL import ImageFont
H = os.path.dirname(os.path.abspath(__file__)); os.chdir(H)
CHK = '/tmp/claude-0/-home-user-tw-rotation/ce50d787-1067-5482-ab44-99dc39a48890/scratchpad/rrxq_chk'
os.makedirs(CHK, exist_ok=True)
FD = os.path.expanduser('~/.fonts/')
FONTS = {  # 鍵：(CSS 家族, 字重, PIL 檔)
 'sans': ("'Noto Sans CJK TC',sans-serif", 700, FD+'NotoSansCJKtc-Bold.otf'),
 'serif': ("'Noto Serif CJK TC',serif", 700, FD+'NotoSerifCJKtc-Bold.otf'),
 'kai': ("'LXGW WenKai TC',serif", 400, FD+'LXGWWenKaiTC-Regular.ttf'),
}
# 色調：bg 底、S 太陽色、M 主色（大面積）、soft 淺色、ink 字與線
TONES = {
 '奶油晨光': dict(bg='#FFF6E5', S='#F2A65A', M='#F7D9A6', soft='#FFE9C7', ink='#3A3A3A'),
 '晴空淡藍': dict(bg='#EAF4FB', S='#F6C85F', M='#6FB1E0', soft='#CFE6F6', ink='#1F3C54'),
 '抹茶午後': dict(bg='#EEF2E6', S='#F6C85F', M='#8DAA7B', soft='#D6E2CA', ink='#2F3F29'),
 '蜜桃傍晚': dict(bg='#FCEDE6', S='#F7C873', M='#F0A58A', soft='#F8D3C4', ink='#5A4636'),
 '單色黑': dict(bg='#FFFFFF', S='#111111', M='#FFFFFF', soft='#FFFFFF', ink='#111111', mono=1),
 '單色白': dict(bg='#111111', S='#FFFFFF', M='#111111', soft='#111111', ink='#FFFFFF', mono=1),
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

# ===== 1 窗中日（字體設計）=====
def s1(P):
    ink = P['ink']; mono = P.get('mono')
    s = f'<rect x="-170" y="-250" width="340" height="230" fill="{P["soft"]}"/><rect x="-170" y="20" width="340" height="230" fill="{P["soft"]}"/>'
    sun = f'<circle cx="40" cy="-135" r="60" fill="{P["S"]}" {stroke(P, 16, True)}/>' + rays(40, -135, 84, 100, 9, 12, ink, 185, 355)
    s += sun
    s += f'<polygon points="-70,22 50,22 150,248 30,248" fill="{lightfill(P)}" opacity="{1 if mono else .7}"/>'
    s += f'<rect x="-190" y="-270" width="380" height="540" rx="34" fill="none" stroke="{ink}" stroke-width="40"/>' + line(-190, 0, 190, 0, 40, ink)
    return L('a', s)
# ===== 2 雲縫太陽（剪紙疊層）=====
def s2(P):
    m = P.get('mono'); ink = P['ink']; f = '' if m else 'filter="url(#sh)"'
    ow = 12 if m else 0
    s = '<clipPath id="c2"><rect x="-280" y="-280" width="560" height="560" rx="72"/></clipPath>'
    s += f'<rect x="-280" y="-280" width="560" height="560" rx="72" fill="{P["soft"]}" {stroke(P, 14)} {f}/>'
    s += f'<g clip-path="url(#c2)"><circle cx="75" cy="-70" r="135" fill="{P["S"]}" {stroke(P, 12)}/>'
    s += f'<g {f}>{cloud(-70, 215, 2.0, P["M"], ink, ow)}</g>'
    s += f'<g {f}>{cloud(95, 330, 2.3, P["bg"], ink, ow)}</g></g>'
    return L('a', s)
# ===== 3 日日週曆格（幾何網格）=====
def s3(P):
    ink = P['ink']; cs, g = 124, 22; s = ''
    pos = [(-273+(i % 4)*(cs+g), -131+(i//4)*(cs+g)) for i in range(7)]
    for i, (x, y) in enumerate(pos[:6]):
        s += f'<rect x="{x}" y="{y}" width="{cs}" height="{cs}" rx="22" fill="{P["soft"]}" stroke="{ink}" stroke-width="12"/>'
        s += cloud(x+cs/2-4, y+cs/2+22, .36, P['M'], ink, 5 if P.get('mono') else 0)
    x, y = pos[6]; cx, cy = x+cs/2, y+cs/2
    s += f'<rect x="{x-6}" y="{y-6}" width="{cs+12}" height="{cs+12}" rx="26" fill="{P["S"]}" stroke="{ink}" stroke-width="18"/>'
    dc = P['bg']
    s += f'<circle cx="{cx}" cy="{cy}" r="32" fill="{dc}" stroke="{ink}" stroke-width="12"/>' + line(cx-32, cy, cx+32, cy, 12, ink)
    s += rays(cx, cy, 44, 54, 8, 9, dc if P.get('mono') else ink)
    return L('a', s)
# ===== 4 晴字日字旁變太陽（字體設計・宋體）=====
def s4(P, dx=0):
    ink = P['ink']
    gx, gy = gp('青', 'serif', 380, 105, 20)
    q = TX('青', 'serif', 380, gx, gy, ink)
    sx, sy = -178, 20
    sun = f'<circle cx="{sx}" cy="{sy}" r="62" fill="{P["S"]}" {stroke(P, 18, True)}/>' + line(sx-62, sy, sx+62, sy, 16, ink)
    sun += rays(sx, sy, 88, 112, 8, 14, ink)
    return L('a', sun) + L('b', q)
# ===== 5 雲影切出晴天（留白藏圖）=====
def s5(P):
    m = P.get('mono'); ground = P['ink'] if m else P['M']; hole = P['bg'] if m else P['S']
    cx, cy = 20, -40
    mk = '<mask id="mk5"><rect x="-300" y="-300" width="600" height="600" fill="#fff"/>'
    mk += f'<circle cx="{cx}" cy="{cy}" r="112" fill="#000"/>'
    for k in range(8):
        a = math.radians(k*45-90+22.5*0); x1, y1 = cx+148*math.cos(a), cy+148*math.sin(a); x2, y2 = cx+212*math.cos(a), cy+212*math.sin(a)
        mk += f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#000" stroke-width="34" stroke-linecap="round"/>'
    mk += f'<g fill="#fff">{cloud_parts(-20, 300, 1.85)}</g></mask>'
    s = mk + f'<rect x="-270" y="-270" width="540" height="540" rx="86" fill="{hole}"/>'
    s += f'<rect x="-270" y="-270" width="540" height="540" rx="86" fill="{ground}" mask="url(#mk5)"/>'
    return L('a', s)
# ===== 6 晾衣夾夾著一小塊陽光（插畫感）=====
def s6(P):
    ink = P['ink']; sw = 14
    s = f'<g transform="rotate(-9)">'
    s += f'<rect x="-150" y="-20" width="300" height="290" rx="18" fill="{lightfill(P) if P.get("mono") else P["S"]}" stroke="{ink}" stroke-width="{sw}"/>'
    if not P.get('mono'):
        for k, o in enumerate((-80, 0, 80)):
            s += line(-90+o, 150, -30+o, 215, 11, P['bg'])
    for x in (-58, 10):
        s += f'<rect x="{x}" y="-270" width="48" height="340" rx="18" fill="{P["M"]}" stroke="{ink}" stroke-width="{sw}"/>'
    s += f'<circle cx="0" cy="-40" r="30" fill="{P["soft"]}" stroke="{ink}" stroke-width="{sw}"/><circle cx="0" cy="-40" r="8" fill="{ink}"/>'
    s += '</g>'
    return L('a', s)
# ===== 7 熱飲杯口升太陽（單線一筆畫）=====
def s7(P):
    ink = P['ink']; w = 28; cx, cy = -10, 10
    sun = f'<path d="M {cx-125} {cy} A 125 125 0 0 1 {cx+125} {cy} Z" fill="{P["S"]}" stroke="{ink}" stroke-width="{w}" stroke-linejoin="round"/>'
    sun += ''.join(line(cx+158*math.cos(math.radians(a)), cy+158*math.sin(math.radians(a)), cx+212*math.cos(math.radians(a)), cy+212*math.sin(math.radians(a)), w-4, ink) for a in (-165, -128, -90, -52, -15))
    mug = f'<path d="M -190 {cy} L -170 215 Q -165 262 -120 262 L 100 262 Q 145 262 150 215 L 170 {cy} Z" fill="{P["soft"]}" stroke="{ink}" stroke-width="{w}" stroke-linejoin="round"/>'
    mug += f'<path d="M 162 80 C 290 60 290 205 150 198" fill="none" stroke="{ink}" stroke-width="{w}" stroke-linecap="round"/>'
    return L('a', f'<g transform="translate(-38 -32)">{sun}{mug}</g>')
# ===== 8 收傘指向晴空（極簡符號）=====
def s8(P):
    ink = P['ink']
    u = f'<path d="M 0 -250 C 34 -190 56 -80 56 22 Q 28 56 0 30 Q -28 56 -56 22 C -56 -80 -34 -190 0 -250 Z" fill="{P["M"]}" stroke="{ink}" stroke-width="16" stroke-linejoin="round"/>'
    u += f'<path d="M 0 -245 L 0 30 M 0 -245 Q 30 -100 28 40 M 0 -245 Q -30 -100 -28 40" fill="none" stroke="{ink}" stroke-width="9" stroke-linecap="round"/>'
    u += f'<rect x="-54" y="-70" width="108" height="30" rx="8" fill="{P["S"]}" stroke="{ink}" stroke-width="10"/>'
    u += f'<path d="M 0 30 L 0 215 Q 0 262 -40 262 Q -78 262 -78 222" fill="none" stroke="{ink}" stroke-width="24" stroke-linecap="round"/>'
    um = f'<g transform="translate(-62 42) rotate(25) scale(.9)">{u}</g>'
    sx, sy = 182, -182
    sun = f'<circle cx="{sx}" cy="{sy}" r="58" fill="{P["S"]}" {stroke(P, 16, True)}/>' + rays(sx, sy, 84, 108, 8, 13, ink)
    return L('a', um) + L('b', sun)
# ===== 9 日日小晴印（印章）=====
def s9(P):
    m = P.get('mono'); body = P['ink'] if m else P['S']; tc = P['bg'] if m else P['ink']
    s = f'<g filter="url(#rough)"><rect x="-270" y="-270" width="540" height="540" rx="26" fill="{body}"/>'
    s += f'<rect x="-238" y="-238" width="476" height="476" rx="12" fill="none" stroke="{tc}" stroke-width="12"/></g>'
    t = ''
    for ch, (cx, cy) in {'小': (-118, -118), '日': (118, -118), '晴': (-118, 118), '日 ': (118, 118)}.items():
        t += glyph(ch.strip(), 'kai', 196, cx, cy, tc, bold=7)
    return L('a', s) + L('b', t)
# ===== 10 日光徽章 =====
def s10(P):
    ink = P['ink']; R = 290
    s = f'<circle r="{R}" fill="{P["soft"]}" stroke="{ink}" stroke-width="16"/>'
    s += f'<circle r="188" fill="{P["bg"] if not P.get("mono") else P["bg"]}" stroke="{ink}" stroke-width="12"/>'
    ring = '<path id="pt" d="M -214 0 A 214 214 0 0 1 214 0" fill="none"/><path id="pb" d="M -258 0 A 258 258 0 0 0 258 0" fill="none"/>'
    fam, w, _ = FONTS['sans']
    t = f'<text font-family="{fam}" font-weight="{w}" font-size="62" letter-spacing="14" fill="{ink}" text-anchor="middle"><textPath href="#pt" startOffset="50%">{NAME}</textPath></text>'
    t += f'<text font-family="{fam}" font-weight="{w}" font-size="40" letter-spacing="8" fill="{ink}" text-anchor="middle"><textPath href="#pb" startOffset="50%">{SUB}</textPath></text>'
    dots = f'<circle cx="-241" cy="0" r="12" fill="{P["S"] if not P.get("mono") else ink}" stroke="{ink}" stroke-width="5"/><circle cx="241" cy="0" r="12" fill="{P["S"] if not P.get("mono") else ink}" stroke="{ink}" stroke-width="5"/>'
    inner = f'<clipPath id="c10"><circle r="176"/></clipPath><g clip-path="url(#c10)">'
    inner += f'<path d="M -100 30 A 100 100 0 0 1 100 30 Z" fill="{P["S"]}" stroke="{ink}" stroke-width="14" stroke-linejoin="round"/>'
    inner += rays(0, 30, 122, 150, 5, 12, ink, 205, 335)
    inner += f'<rect x="-190" y="30" width="380" height="170" fill="{P["M"] if not P.get("mono") else P["bg"]}"/>' + line(-190, 30, 190, 30, 14, ink)
    inner += cloud(-112, 24, .5, P['bg'], ink, 7)
    inner += '</g>'
    return L('a', s + ring + dots + inner) + L('b', t)
# ===== 11 手寫（楷體＋手繪太陽）=====
def s11(P):
    ink = P['ink']
    t = glyph('晴', 'kai', 330, -30, 55, ink, bold=9)
    sx, sy = 160, -180
    sun = f'<path d="{wob(sx, sy, 50, 3, .05)}" fill="{P["S"]}" stroke="{ink}" stroke-width="12" stroke-linejoin="round"/>'
    sun += f'<path d="{wob(sx, sy, 58, 8, .05, a0=40, a1=300)}" fill="none" stroke="{ink}" stroke-width="7" stroke-linecap="round" opacity=".6"/>'
    for k in range(7):
        a = math.radians(-100+k*28 - 5); sun += line(sx+78*math.cos(a), sy+78*math.sin(a), sx+104*math.cos(a), sy+104*math.sin(a), 11, ink)
    wave = 'M -180 245 q 30 -26 60 0 t 60 0 t 60 0 t 60 0 t 60 0'
    w = f'<path d="{wave}" fill="none" stroke="{P["S"] if not P.get("mono") else ink}" stroke-width="22" stroke-linecap="round"/>'
    return L('b', t) + L('a', sun) + L('c', w)
# ===== 12 窗光落地板（平塗光影）=====
def s12(P):
    m = P.get('mono'); ink = P['ink']; ground = P['bg'] if m else P['M']; light = ink if m else P['S']
    s = f'<clipPath id="c12"><rect x="-270" y="-270" width="540" height="540" rx="60"/></clipPath><rect x="-270" y="-270" width="540" height="540" rx="60" fill="{ground}" {stroke(P, 18)}/><g clip-path="url(#c12)">'
    s += f'<polygon points="-110,-290 70,-290 200,-30 20,-30" fill="{light}"/><polygon points="10,10 190,10 320,270 140,270" fill="{light}"/>'
    lf = P['bg'] if not m else ink
    leaf = ''; lc = P['bg'] if m else ink
    leaf += f'<path d="M 110 290 C 100 220 120 160 150 100" fill="none" stroke="{lc}" stroke-width="16" stroke-linecap="round" opacity="{1 if m else .6}"/>'
    for (x, y, a) in ((150, 215, -25), (190, 170, -50), (112, 175, 205), (160, 115, -80)):
        leaf += f'<ellipse cx="{x}" cy="{y}" rx="66" ry="26" transform="rotate({a} {x} {y})" fill="{lc}" opacity="{1 if m else .6}"/>'
    s += leaf + '</g>'
    return L('a', s)

STYLES = [
 # 序號、資料夾名、名稱、風格、含義、符號函式、字標字型、字距、符號縮放、44px 自評、頭像縮放
 (1, '01_窗中日', '窗中日', '字體設計', '「日」字是一扇窗，上格是太陽，一道光斜斜落進下格。', s1, 'sans', 14, 1.12, '強：窗框＋太陽粗線條，44px 仍清楚。'),
 (2, '02_雲縫太陽', '雲縫太陽', '剪紙疊層', '雲的縫隙裡露出一小角太陽，今天不用很大，一角就夠。', s2, 'sans', 14, 1.1, '強：卡片＋橘黃弧形，一眼是太陽。'),
 (3, '03_週曆格', '一週七格', '幾何網格', '一週七格，前六格是雲，第七天「日」亮成晴，日日都有機會。', s3, 'sans', 12, 1.1, '中：6 朵小雲糊成點，亮格仍明顯。'),
 (4, '04_晴字日旁', '日旁變太陽', '字體設計・宋體', '「晴」字的日字旁變成一顆小太陽，字裡就有晴。', s4, 'serif', 12, 1.12, '強：青字清楚，太陽辨識度高。'),
 (5, '05_雲影切晴', '雲影切晴', '留白藏圖', '雲的影子留下的空白，剛好切成一個晴天的形狀。', s5, 'serif', 14, 1.1, '強：大色塊＋空白太陽。'),
 (6, '06_晾衣夾', '晾衣夾陽光', '插畫感', '晾衣夾夾住一小塊陽光，把今天的好天氣收進生活裡。', s6, 'kai', 12, 1.08, '中：夾子與黃布小但輪廓明確。'),
 (7, '07_杯口日出', '杯口日出', '單線一筆畫', '一杯熱飲的杯口升起一顆太陽，日子辛苦，但有一口暖。', s7, 'kai', 12, 1.08, '強：粗線杯子＋半圓太陽。'),
 (8, '08_收傘', '收傘放晴', '極簡符號', '雨傘收起來，傘尖指向放晴的天空，雨停了。', s8, 'sans', 14, 1.12, '中：傘細長，44px 靠傘身色塊與太陽辨認。'),
 (9, '09_日日小晴印', '日日小晴印', '印章', '一方小印落款「日日小晴」，每天蓋一個今天的章。', s9, 'serif', 14, 1.08, '中：印面小字糊成紋理，色塊與方印可辨。'),
 (10, '10_日光徽章', '日光徽章', '徽章', '圓徽上半是頻道名、下半是副標，中間是剛升起的太陽。', s10, 'sans', 14, 1.1, '弱：環字讀不出，剩圓徽＋半日。'),
 (11, '11_手寫晴', '手寫晴', '手寫', '手寫的「晴」旁邊畫了一顆隨手塗的小太陽，像日記一角。', s11, 'kai', 14, 1.1, '強：大字「晴」＋黃波浪線。'),
 (12, '12_窗光落地', '窗光落地', '平塗光影', '窗光落在地板上，兩塊光裡有一株小植物的影子。', s12, 'sans', 14, 1.1, '中：兩塊斜光明確，植物影在 44px 糊掉。'),
]

def avatar_svg(P, sym, k, bg=True):
    b = f'<rect width="1080" height="1080" fill="{P["bg"]}"/>' if bg else ''
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1080" viewBox="0 0 1080 1080"><defs>{defs(P)}</defs>{b}<g transform="translate(540 540) scale({k})">{sym}</g></svg>'
def text_w(s, kind, fs, ls):
    f = ImageFont.truetype(FONTS[kind][2], fs); return f.getlength(s) + ls*(len(s)-1)
WH = 420
def wm_svg(P, n, sym, kind, ls, k, sub, bg=True):
    """橫式字標；回傳 svg 字串與寬度。n=4／11 為特殊字標。"""
    ink = P['ink']; bgr = f'<rect width="{{W}}" height="{WH}" fill="{P["bg"]}"/>' if bg else ''
    fs = 150 if not sub else 134
    ty = 210 if not sub else 170
    symsz = 372
    tw = text_w(NAME, kind, fs, ls); x0 = 60 + symsz + 54; W = int(x0 + tw + 70)
    body = ''
    if n == 4:  # 「日日小」＋日旁變太陽的「晴」
        tw3 = text_w('日日小', kind, fs, ls); gh = fs*.98
        x0 = 70; W = int(x0 + tw3 + ls + 125 + 115 + 70)
        body += L('txt', TX('日日小', kind, fs, x0, 0, ink, ls=ls).replace('y="0.0"', f'y="{ty+.36*fs:.1f}"'))
        body += L('sym', f'<g transform="translate({x0+tw3+ls+125} {ty}) scale({fs/380*.98})">{s4(P)}</g>')
    elif n == 11:
        fsz = 150 if not sub else 134
        sunk = f'<g transform="translate(0 0)">'
        x0 = 70
        wsun = wob(0, 0, 44, 3, .05)
        sun = f'<path d="{wsun}" fill="{P["S"]}" stroke="{ink}" stroke-width="10" stroke-linejoin="round"/>' + ''.join(
            line(70*math.cos(math.radians(a)), 70*math.sin(math.radians(a)), 94*math.cos(math.radians(a)), 94*math.sin(math.radians(a)), 10, ink) for a in range(-100, 260, 40))
        body += L('sym', f'<g transform="translate({x0+100} {ty})">{sun}</g>')
        tx0 = x0 + 230; tw = text_w(NAME, kind, fsz, ls); W = int(tx0 + tw + 70)
        body += L('txt', TX(NAME, kind, fsz, tx0, ty+.36*fsz, ink, ls=ls, bold=3))
        wave = f'M {tx0} {ty+.36*fsz+52} q 28 -16 56 0 t 56 0 t 56 0 t 56 0 t 56 0'
        body += L('sym2', f'<path d="{wave}" fill="none" stroke="{P["S"] if not P.get("mono") else ink}" stroke-width="12" stroke-linecap="round"/>')
        if sub: pass
    else:
        body += L('sym', f'<g transform="translate({60+symsz/2} 210) scale({k})">{sym}</g>')
        body += L('txt', TX(NAME, kind, fs, x0, ty+.36*fs, ink, ls=ls, bold=3 if kind == 'kai' else 0))
    if sub:
        body += L('sub', TX(SUB, 'sans', 44, (x0 if n not in (4, 11) else (70 if n == 4 else 70+230)), 345, ink, ls=7, bold=0).replace('font-weight="700"', 'font-weight="700"'))
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
                if tag == '奶油晨光':
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
