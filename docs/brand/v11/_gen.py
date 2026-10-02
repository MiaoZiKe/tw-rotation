# 第十一輪：六角鏡片 × 台股立方（HUD／透視）
import math, os
OUT = os.path.dirname(os.path.abspath(__file__))

def rot(p, yaw, pitch):
    x, y, z = p
    c, s = math.cos(yaw), math.sin(yaw)
    x1, z1 = x*c + z*s, -x*s + z*c
    c2, s2 = math.cos(pitch), math.sin(pitch)
    return (x1, y*c2 - z1*s2, y*s2 + z1*c2)

class Cam:
    def __init__(s, yaw, pitch, D=None):
        s.yaw, s.pitch, s.D = yaw, pitch, D
        s.cx = s.cy = 0; s.k = 1
    def raw(s, p):
        x, y, z = rot(p, s.yaw, s.pitch)
        f = s.D/(s.D - z) if s.D else 1
        return x*f, -y*f
    def fit(s, cx, cy, R):
        pts = [s.raw(v) for v in VERTS]
        r = max(math.hypot(x, y) for x, y in pts)
        mx = (max(p[0] for p in pts)+min(p[0] for p in pts))/2
        my = (max(p[1] for p in pts)+min(p[1] for p in pts))/2
        s.k = R/r; s.cx = cx - mx*s.k; s.cy = cy - my*s.k
        return s
    def P(s, p):
        x, y = s.raw(p); return (s.cx + x*s.k, s.cy + y*s.k)
    def front(s, n, c):
        nr = rot(n, s.yaw, s.pitch)
        if not s.D: return nr[2] > 0
        cr = rot(c, s.yaw, s.pitch)
        return nr[0]*(-cr[0]) + nr[1]*(-cr[1]) + nr[2]*(s.D-cr[2]) > 0

VERTS = [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
AX = [(1,0,0),(0,1,0),(0,0,1)]
def add(a,b,k=1): return tuple(a[i]+b[i]*k for i in range(3))
def neg(a): return tuple(-x for x in a)

# 六個面（軸, 正負）→ 指標面
FACES = {
    (1, 1): '資金面', (0, -1): '技術面', (2, 1): '產業面',
    (1, -1): '基本面', (0, 1): '籌碼面', (2, -1): '事件面',
}
EN = {'資金面':'FLOW','技術面':'TECH','產業面':'CHAIN','基本面':'FUND','籌碼面':'CHIPS','事件面':'EVENT'}

def face_frame(cam, ax, sg):
    n = [0,0,0]; n[ax] = sg; n = tuple(n)
    others = [i for i in range(3) if i != ax]
    ta, tb = AX[others[0]], AX[others[1]]
    C = n
    def scr(v):
        a = cam.P(C); b = cam.P(add(C, v, .5)); return (b[0]-a[0], b[1]-a[1])
    # e2 = 螢幕上最朝上的切向量；e1 = 另一個、朝右
    cands = [ta, neg(ta), tb, neg(tb)]
    e2 = min(cands, key=lambda v: scr(v)[1])
    e1 = tb if e2 in (ta, neg(ta)) else ta
    if scr(e1)[0] < 0: e1 = neg(e1)
    return n, e1, e2

def mapper(cam, n, e1, e2):
    return lambda u, v: cam.P(add(add(n, e1, u), e2, v))

def pts(m, uv): return ' '.join(f'{x:.1f},{y:.1f}' for x, y in (m(u, v) for u, v in uv))
def circ(m, u0, v0, r, k=18): return [(u0+r*math.cos(2*math.pi*i/k), v0+r*math.sin(2*math.pi*i/k)) for i in range(k)]
def arc(u0, v0, r, a0, a1, k=14): return [(u0+r*math.cos(math.radians(a0+(a1-a0)*i/k)), v0+r*math.sin(math.radians(a0+(a1-a0)*i/k))) for i in range(k+1)]

def glyph(name, m, P, w):
    L, R, G, A = P['line'], P['rise'], P['fall'], P['acc']
    sw = f'stroke-width="{w:.1f}" stroke-linecap="round" stroke-linejoin="round" fill="none"'
    o = []
    if name == '資金面':   # 輪動：兩段旋轉箭頭
        for a0, a1 in ((200, 330), (20, 150)):
            a = arc(0, 0, .5, a0, a1)
            o.append(f'<polyline points="{pts(m,a)}" stroke="{L}" {sw}/>')
            tip = a[-1]; ang = math.radians(a1)
            t = (-math.sin(ang), math.cos(ang))  # 切線（逆時針方向）
            nn = (math.cos(ang), math.sin(ang))
            head = [(tip[0]+t[0]*.2, tip[1]+t[1]*.2), (tip[0]+nn[0]*.14, tip[1]+nn[1]*.14), (tip[0]-nn[0]*.14, tip[1]-nn[1]*.14)]
            o.append(f'<polygon points="{pts(m,head)}" fill="{L}"/>')
        o.append(f'<polygon points="{pts(m,circ(m,0,0,.1,12))}" fill="{A}"/>')
    elif name == '技術面':  # K 棒（紅漲綠跌）
        for u, lo, hi, b0, b1, col in ((-.42,-.5,.1,-.38,-.02,R), (0,-.32,.36,-.2,.2,G), (.42,-.18,.62,-.05,.5,R)):
            o.append(f'<polyline points="{pts(m,[(u,lo),(u,hi)])}" stroke="{col}" {sw}/>')
            o.append(f'<polygon points="{pts(m,[(u-.12,b0),(u+.12,b0),(u+.12,b1),(u-.12,b1)])}" fill="{col}"/>')
    elif name == '產業面':  # 產業鏈網路
        N = [(-.56, .32), (-.56, -.32), (.56, .4), (.56, -.4), (0, 0)]
        for a, b in ((0,4),(1,4),(4,2),(4,3)):
            o.append(f'<polyline points="{pts(m,[N[a],N[b]])}" stroke="{L}" {sw} opacity=".85"/>')
        for i, (u, v) in enumerate(N):
            o.append(f'<polygon points="{pts(m,circ(m,u,v,.17 if i==4 else .12))}" fill="{A if i==4 else L}"/>')
    elif name == '籌碼面':  # 法人買賣超（正負柱）
        for u, h in ((-.48,.42),(-.16,-.28),(.16,.6),(.48,.3)):
            col = R if h > 0 else G
            o.append(f'<polygon points="{pts(m,[(u-.1,0),(u+.1,0),(u+.1,h),(u-.1,h)])}" fill="{col}"/>')
        o.append(f'<polyline points="{pts(m,[(-.66,0),(.66,0)])}" stroke="{L}" {sw}/>')
    elif name == '基本面':  # 營收趨勢
        line = [(-.6,-.42),(-.22,-.12),(.08,-.24),(.56,.42)]
        o.append(f'<polygon points="{pts(m,line+[(.56,-.56),(-.6,-.56)])}" fill="{L}" opacity=".22"/>')
        o.append(f'<polyline points="{pts(m,line)}" stroke="{L}" {sw}/>')
        for u, v in line: o.append(f'<polygon points="{pts(m,circ(m,u,v,.07,10))}" fill="{L}"/>')
    elif name == '事件面':  # 事件脈衝
        p = [(-.66,0),(-.28,0),(-.15,.5),(0,-.48),(.14,.2),(.26,0),(.66,0)]
        o.append(f'<polyline points="{pts(m,p)}" stroke="{L}" {sw}/>')
        o.append(f'<polygon points="{pts(m,circ(m,.5,.3,.09,10))}" fill="{A}"/>')
    return '\n'.join(o)

def cube(cam, P, w=8, glyphs=True, back_glyphs=True, faces_out=None, glyph_w=None):
    """回傳 (後層, 前層) SVG；faces_out 收集每面螢幕中心供圖說用"""
    back, frontl = [], []
    vis = {}
    for (ax, sg), name in FACES.items():
        n = [0,0,0]; n[ax] = sg; n = tuple(n)
        vis[(ax, sg)] = cam.front(n, n)
    for (ax, sg), name in FACES.items():
        n, e1, e2 = face_frame(cam, ax, sg)
        m = mapper(cam, n, e1, e2)
        quad = pts(m, [(-1,-1),(1,-1),(1,1),(-1,1)])
        f = vis[(ax, sg)]
        tint = P['face'].get(name, P['line'])
        if faces_out is not None: faces_out[name] = (m(0,0), f)
        if f:
            frontl.append(f'<polygon points="{quad}" fill="{tint}" fill-opacity="{P["fo"]}"/>')
            if glyphs: frontl.append(f'<g opacity="{P["go"]}">{glyph(name, m, P, glyph_w or w*.9)}</g>')
        else:
            back.append(f'<polygon points="{quad}" fill="{tint}" fill-opacity="{P["bo"]}"/>')
            if glyphs and back_glyphs: back.append(f'<g opacity="{P["bgo"]}">{glyph(name, m, P, (glyph_w or w*.9)*.8)}</g>')
    # 稜線
    for v in VERTS:
        for i in range(3):
            if v[i] != -1: continue
            u = list(v); u[i] = 1; u = tuple(u)
            j, k = [a for a in range(3) if a != i]
            fa = vis[(j, v[j])]; fb = vis[(k, v[k])]
            a, b = cam.P(v), cam.P(u)
            d = f'M{a[0]:.1f} {a[1]:.1f} L{b[0]:.1f} {b[1]:.1f}'
            if not fa and not fb:
                back.append(f'<path d="{d}" stroke="{P["edge"]}" stroke-width="{w*.55:.1f}" stroke-dasharray="{w*1.1:.1f} {w*1.1:.1f}" stroke-linecap="round" opacity=".7"/>')
            else:
                frontl.append(f'<path d="{d}" stroke="{P["edge"]}" stroke-width="{w:.1f}" stroke-linecap="round"/>')
    return '\n'.join(back), '\n'.join(frontl)

def hexpts(cx, cy, r, rot0=-90):
    return [(cx + r*math.cos(math.radians(rot0 + 60*i)), cy + r*math.sin(math.radians(rot0 + 60*i))) for i in range(6)]
def poly(p): return ' '.join(f'{x:.1f},{y:.1f}' for x, y in p)

HUD = dict(bg0='#0d1b30', bg1='#060b14', line='#57e3ff', edge='#8ff0ff', acc='#ffb44d', rise='#ff5b6e', fall='#2fd59b',
           face={'資金面':'#57e3ff','技術面':'#3a8dff','產業面':'#2fc6e0','基本面':'#57e3ff','籌碼面':'#57e3ff','事件面':'#57e3ff'},
           fo=.16, bo=.05, go=1, bgo=.38, rim='#57e3ff', hud='#57e3ff', ink='#e8f6ff', sub='#7fa6c4', tile='#0a1424')
LIGHT = dict(bg0='#ffffff', bg1='#f2f5fa', line='#2f63e0', edge='#1b2433', acc='#f08a3c', rise='#e5384f', fall='#16a46c',
           face={'資金面':'#2f63e0','技術面':'#1b2433','產業面':'#2f63e0','基本面':'#2f63e0','籌碼面':'#2f63e0','事件面':'#2f63e0'},
           fo=.09, bo=.03, go=1, bgo=.32, rim='#1b2433', hud='#2f63e0', ink='#1b2433', sub='#5b6779', tile='#ffffff')

GLOW = '''<filter id="gl" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="{s}" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'''

def ticks(cx, cy, r, P, n=72, long_every=6, w=2, l1=8, l2=16, a_skip=None):
    o = []
    for i in range(n):
        a = 360*i/n
        if a_skip and a_skip[0] <= a <= a_skip[1]: continue
        L = l2 if i % long_every == 0 else l1
        x1 = cx + r*math.cos(math.radians(a)); y1 = cy + r*math.sin(math.radians(a))
        x2 = cx + (r-L)*math.cos(math.radians(a)); y2 = cy + (r-L)*math.sin(math.radians(a))
        o.append(f'M{x1:.1f} {y1:.1f}L{x2:.1f} {y2:.1f}')
    return f'<path d="{"".join(o)}" stroke="{P["hud"]}" stroke-width="{w}" opacity=".55"/>'

def brackets(x0, y0, x1, y1, L, P, w=4):
    d = (f'M{x0} {y0+L}V{y0}H{x0+L} M{x1-L} {y0}H{x1}V{y0+L} M{x1} {y1-L}V{y1}H{x1-L} M{x0+L} {y1}H{x0}V{y1-L}')
    return f'<path d="{d}" stroke="{P["hud"]}" stroke-width="{w}" fill="none" opacity=".8"/>'

def handle(P, x0=338, y0=338, x1=432, y1=432, w=34, hud=True):
    o = [f'<path d="M{x0} {y0} L{x1} {y1}" stroke="{P["rim"]}" stroke-width="{w}" stroke-linecap="round"/>']
    if hud:   # 握把刻紋
        for t in (.45, .6, .75):
            x = x0 + (x1-x0)*t; y = y0 + (y1-y0)*t; h = w*.32
            o.append(f'<path d="M{x-h:.1f} {y+h:.1f} L{x+h:.1f} {y-h:.1f}" stroke="{P["tile"]}" stroke-width="4" stroke-linecap="round"/>')
    return '\n'.join(o)

# ---------- A：等角 HUD（六角＝立方體輪廓） ----------
def iconA(P, small=False, dark=True):
    cx, cy, R = 232, 232, 132
    cam = Cam(math.radians(45), math.atan(1/math.sqrt(2))).fit(cx, cy, R)
    w = 12 if small else 6
    back, front = cube(cam, P, w=w, glyphs=not small, glyph_w=7)
    hexo = poly(hexpts(cx, cy, R))
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><defs><radialGradient id="bg" cx="45%" cy="40%" r="75%"><stop offset="0" stop-color="{P["bg0"]}"/><stop offset="1" stop-color="{P["bg1"]}"/></radialGradient>{GLOW.format(s=4 if dark else 0.01)}</defs>',
         f'<rect x="4" y="4" width="504" height="504" rx="116" fill="url(#bg)" stroke="{P["hud"] if dark else "#e3e8f0"}" stroke-opacity="{.35 if dark else 1}" stroke-width="6"/>']
    if not small:
        o.append(ticks(cx, cy, R+44, P, a_skip=(28, 62)))
        o.append(f'<circle cx="{cx}" cy="{cy}" r="{R+52}" fill="none" stroke="{P["hud"]}" stroke-width="2" stroke-dasharray="4 10" opacity=".45"/>')
    o.append(f'<g filter="url(#gl)">{back}\n{front}</g>' if dark else f'<g>{back}\n{front}</g>')
    o.append(f'<polygon points="{hexo}" fill="none" stroke="{P["rim"]}" stroke-width="{24 if small else 16}" stroke-linejoin="round"' + (' filter="url(#gl)"' if dark else '') + '/>')
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{18 if small else 11}" fill="{P["acc"]}"/>')
    o.append(handle(P, 336, 336, 430, 430, 40 if small else 34, hud=not small))
    o.append('</svg>')
    return '\n'.join(o)

# ---------- B：透視 HUD（鏡片裡浮一顆玻璃立方） ----------
def iconB(P, small=False, dark=True, faces_out=None, size=512):
    cx, cy, R = 232, 232, 140
    cam = Cam(math.radians(34), math.radians(24), D=5.2).fit(cx, cy+4, R*.75)
    w = 11 if small else 5.5
    back, front = cube(cam, P, w=w, glyphs=not small, glyph_w=6, faces_out=faces_out)
    hexo = poly(hexpts(cx, cy, R))
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><defs><radialGradient id="bg" cx="45%" cy="40%" r="75%"><stop offset="0" stop-color="{P["bg0"]}"/><stop offset="1" stop-color="{P["bg1"]}"/></radialGradient>'
         f'<linearGradient id="lens" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{P["hud"]}" stop-opacity="{.16 if dark else .08}"/><stop offset=".6" stop-color="{P["hud"]}" stop-opacity="0"/></linearGradient>'
         f'<clipPath id="lc"><polygon points="{hexo}"/></clipPath>{GLOW.format(s=4 if dark else 0.01)}</defs>',
         f'<rect x="4" y="4" width="504" height="504" rx="116" fill="url(#bg)" stroke="{P["hud"] if dark else "#e3e8f0"}" stroke-opacity="{.35 if dark else 1}" stroke-width="6"/>']
    if not small:
        # 鏡片內的掃描格線
        g = []
        for i in range(-6, 7):
            g.append(f'M{cx-160} {cy+i*24}H{cx+160}')
            g.append(f'M{cx+i*24} {cy-160}V{cy+160}')
        o.append(f'<g clip-path="url(#lc)"><rect x="0" y="0" width="512" height="512" fill="url(#lens)"/><path d="{"".join(g)}" stroke="{P["hud"]}" stroke-width="1" opacity="{.14 if dark else .10}"/>'
                 f'<rect x="{cx-160}" y="{cy-58}" width="320" height="3" fill="{P["hud"]}" opacity=".35"/></g>')
        o.append(ticks(cx, cy, R+40, P, a_skip=(28, 62)))
        o.append(brackets(cx-R-30, cy-R-30, cx+R+30, cy+R+30, 30, P))
    o.append(f'<g filter="url(#gl)">{back}\n{front}</g>' if dark else f'<g>{back}\n{front}</g>')
    o.append(f'<polygon points="{hexo}" fill="none" stroke="{P["rim"]}" stroke-width="{24 if small else 14}" stroke-linejoin="round"' + (' filter="url(#gl)"' if dark else '') + '/>')
    if not small:   # 鏡片頂點的小刻度
        for x, y in hexpts(cx, cy, R):
            o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{P["acc"]}"/>')
    o.append(handle(P, 340, 340, 432, 432, 40 if small else 34, hud=not small))
    o.append('</svg>')
    return '\n'.join(o)

def save(name, svg):
    with open(os.path.join(OUT, name), 'w') as f: f.write(svg)

variants = {
    'A_iso_hud_dark.svg': iconA(HUD), 'A_iso_light.svg': iconA(LIGHT, dark=False),
    'A_small_dark.svg': iconA(HUD, small=True), 'A_small_light.svg': iconA(LIGHT, small=True, dark=False),
    'B_persp_hud_dark.svg': iconB(HUD), 'B_persp_light.svg': iconB(LIGHT, dark=False),
    'B_small_dark.svg': iconB(HUD, small=True), 'B_small_light.svg': iconB(LIGHT, small=True, dark=False),
}
for k, v in variants.items(): save(k, v)

# 圖說用的大圖：每一面的螢幕中心

# ---------- 標準字組合（橫式） ----------
def lockup(icon_svg, P, dark):
    inner = icon_svg.split('>', 1)[1].rsplit('</svg>', 1)[0]
    bg = '#070d18' if dark else '#ffffff'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 360"><rect width="1200" height="360" fill="{bg}"/>
<svg x="40" y="40" width="280" height="280" viewBox="0 0 512 512">{inner}</svg>
<text x="370" y="178" font-family="WenQuanYi Zen Hei" font-size="118" font-weight="600" letter-spacing="14" fill="{P['ink']}">台股立方</text>
<text x="374" y="234" font-family="DejaVu Sans Mono" font-size="30" letter-spacing="10" fill="{P['hud']}">TW·STOCK·CUBE</text>
<path d="M374 262 H1120" stroke="{P['hud']}" stroke-opacity=".35" stroke-width="2"/>
<text x="374" y="300" font-family="WenQuanYi Zen Hei" font-size="27" letter-spacing="5" fill="{P['sub']}">六面透視　資金・籌碼・產業・技術・事件・基本</text>
</svg>'''

save('lockup_A_dark.svg', lockup(iconA(HUD), HUD, True))
save('lockup_A_light.svg', lockup(iconA(LIGHT, dark=False), LIGHT, False))
save('lockup_B_dark.svg', lockup(iconB(HUD), HUD, True))
save('lockup_B_light.svg', lockup(iconB(LIGHT, dark=False), LIGHT, False))
for k, v in variants.items(): pass
variants = {
    'A_iso_hud_dark.svg': iconA(HUD), 'A_iso_light.svg': iconA(LIGHT, dark=False),
    'A_small_dark.svg': iconA(HUD, small=True), 'A_small_light.svg': iconA(LIGHT, small=True, dark=False),
    'B_persp_hud_dark.svg': iconB(HUD), 'B_persp_light.svg': iconB(LIGHT, dark=False),
    'B_small_dark.svg': iconB(HUD, small=True), 'B_small_light.svg': iconB(LIGHT, small=True, dark=False),
}
for k, v in variants.items(): save(k, v)

# ---------- 六面對照圖（HUD 圖說） ----------
INFO = {
    '資金面': ('01', '錢往哪裡跑', ['資金流向排行', '資金輪盤（輪動四象限）', '雷達・熱力圖'], '#flow  #heatmap'),
    '產業面': ('02', '上下游誰最強', ['2D／3D 產業地圖', '產業鏈關聯圖', '剖析圖'], '#industry'),
    '籌碼面': ('03', '誰在買、誰在賣', ['法人買賣超', '集保大戶增減'], '#stock 籌碼'),
    '技術面': ('04', '什麼時候進場', ['K 線・分 K', '多週期 SMC', '技術評分'], '#stock'),
    '事件面': ('05', '有沒有理由不進場', ['今日事件', '新聞・除權息', '總經指標'], '#overview'),
    '基本面': ('06', '現在貴不貴', ['月營收・獲利', '本益比河流', '週期統計（歷史）'], '#season'),
}
def legend(P, dark):
    W, H = 1800, 1100
    cx, cy, R = 900, 560, 300
    cam = Cam(math.radians(34), math.radians(24), D=5.2).fit(cx, cy+6, R*.75)
    FO = {}
    back, front = cube(cam, P, w=9, glyph_w=10, faces_out=FO)
    hexo = poly(hexpts(cx, cy, R))
    bg = (f'<radialGradient id="bg" cx="50%" cy="50%" r="70%"><stop offset="0" stop-color="{P["bg0"]}"/><stop offset="1" stop-color="{P["bg1"]}"/></radialGradient>')
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}"><defs>{bg}{GLOW.format(s=6 if dark else .01)}<clipPath id="lc"><polygon points="{hexo}"/></clipPath></defs>',
         f'<rect width="{W}" height="{H}" fill="url(#bg)"/>']
    g = ''.join(f'M0 {y}H{W}' for y in range(0, H, 50)) + ''.join(f'M{x} 0V{H}' for x in range(0, W, 50))
    o.append(f'<path d="{g}" stroke="{P["hud"]}" stroke-width="1" opacity="{.05 if dark else .06}"/>')
    o.append(f'<text x="70" y="96" font-family="WenQuanYi Zen Hei" font-size="46" font-weight="600" letter-spacing="8" fill="{P["ink"]}">台股立方｜六個面，各看一件事</text>')
    o.append(f'<text x="72" y="140" font-family="DejaVu Sans Mono" font-size="22" letter-spacing="6" fill="{P["hud"]}">TW·STOCK·CUBE  //  6-FACE SCAN  //  FRONT = 實線　THROUGH = 透視（虛線）</text>')
    o.append(ticks(cx, cy, R+60, P, n=120, long_every=10, w=2, l1=10, l2=22))
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{R+72}" fill="none" stroke="{P["hud"]}" stroke-dasharray="3 12" stroke-width="2" opacity=".45"/>')
    o.append(f'<g filter="url(#gl)">{back}\n{front}</g>')
    o.append(f'<polygon points="{hexo}" fill="none" stroke="{P["rim"]}" stroke-width="16" stroke-linejoin="round" filter="url(#gl)"/>')
    for x, y in hexpts(cx, cy, R): o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="8" fill="{P["acc"]}"/>')
    # 標籤位置：左三、右三
    slots = {'資金面': ('R', 250), '產業面': ('R', 560), '籌碼面': ('R', 870),
             '技術面': ('L', 250), '事件面': ('L', 560), '基本面': ('L', 870)}
    for name, (side, ly) in slots.items():
        (fx, fy), isfront = FO[name]
        no, q, feats, route = INFO[name]
        bx = 1330 if side == 'R' else 70
        ax = bx - 20 if side == 'R' else bx + 420
        col = P['hud'] if isfront else P['sub']
        dash = '' if isfront else ' stroke-dasharray="8 8"'
        o.append(f'<polyline points="{fx:.0f},{fy:.0f} {(fx+ax)/2:.0f},{ly:.0f} {ax},{ly}" fill="none" stroke="{col}" stroke-width="2.5"{dash} opacity=".9"/>')
        o.append(f'<circle cx="{fx:.0f}" cy="{fy:.0f}" r="9" fill="none" stroke="{P["acc"]}" stroke-width="3"/><circle cx="{fx:.0f}" cy="{fy:.0f}" r="3.5" fill="{P["acc"]}"/>')
        # 標籤框
        bw, bh = 400, 220
        y0 = ly - 70
        o.append(f'<rect x="{bx}" y="{y0}" width="{bw}" height="{bh}" rx="10" fill="{P["tile"]}" fill-opacity="{.72 if dark else .9}" stroke="{col}" stroke-opacity=".6" stroke-width="2"{dash}/>')
        o.append(brackets(bx-6, y0-6, bx+bw+6, y0+bh+6, 18, P, w=3))
        o.append(f'<text x="{bx+24}" y="{y0+46}" font-family="DejaVu Sans Mono" font-size="22" fill="{P["acc"]}">{no}</text>')
        o.append(f'<text x="{bx+70}" y="{y0+48}" font-family="WenQuanYi Zen Hei" font-size="34" font-weight="600" fill="{P["ink"]}">{name}</text>')
        o.append(f'<text x="{bx+bw-22}" y="{y0+46}" text-anchor="end" font-family="DejaVu Sans Mono" font-size="20" letter-spacing="3" fill="{col}">{EN[name]}{"" if isfront else "·透視"}</text>')
        o.append(f'<text x="{bx+24}" y="{y0+90}" font-family="WenQuanYi Zen Hei" font-size="24" fill="{P["hud"]}">回答：{q}</text>')
        for i, ft in enumerate(feats):
            o.append(f'<text x="{bx+24}" y="{y0+128+i*30}" font-family="WenQuanYi Zen Hei" font-size="22" fill="{P["sub"]}">▸ {ft}</text>')
        o.append(f'<text x="{bx+bw-22}" y="{y0+bh-18}" text-anchor="end" font-family="DejaVu Sans Mono" font-size="18" fill="{P["sub"]}">{route}</text>')
    o.append(f'<text x="{W/2}" y="{H-40}" text-anchor="middle" font-family="WenQuanYi Zen Hei" font-size="22" fill="{P["sub"]}">前三面（實線）是主力：資金・產業・技術；後三面（虛線）透過玻璃看得到：籌碼・事件・基本 —— 判斷順序：資金＋基本定方向 → 技術抓時機 → 事件否決</text>')
    o.append('</svg>')
    return '\n'.join(o)
save('六面對照_dark.svg', legend(HUD, True))
save('六面對照_light.svg', legend(LIGHT, False))
