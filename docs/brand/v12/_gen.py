# 第十二輪〈股立方〉：照 Andy 給的參考圖 —— 霧面幻彩玻璃立方（輪廓即六角鏡片）＋ 暖色 HUD ＋ 黃銅木柄放大鏡
import math, os, sys, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('v11', os.path.join(HERE, '..', 'v11', '_gen.py'))
v11 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v11)   # 重用投影、面座標、指標圖（v11 檔案會原樣重產）
Cam, FACES, VERTS, face_frame, mapper, glyph, pts, poly = v11.Cam, v11.FACES, v11.VERTS, v11.face_frame, v11.mapper, v11.glyph, v11.pts, v11.poly

NAVY = dict(bg0='#26375c', bg1='#141f38', hud='#f2b48c', ink='#f6efe6', sub='#c9b9a8', tile='#1a2744', stroke='#3a4d78')
CREAM = dict(bg0='#fffaf2', bg1='#f6ead8', hud='#c9875a', ink='#5a3a22', sub='#8a6a52', tile='#fff8ee', stroke='#ead9c2')
GLY = dict(line='#4552a6', rise='#e0526a', fall='#23a37a', acc='#f08a4b')
# 每一面的幻彩漸層（粉→薰衣草→天藍）
GRAD = {
    '資金面': ('#ffe3f1', '#e2daff', '#cfeeff'),
    '技術面': ('#ffc4dc', '#dcc6ff', '#b9d4ff'),
    '產業面': ('#b8ddff', '#d6c8ff', '#ffcde4'),
}

def defs(uid, P):
    g = [f'<radialGradient id="bg{uid}" cx="50%" cy="38%" r="80%"><stop offset="0" stop-color="{P["bg0"]}"/><stop offset="1" stop-color="{P["bg1"]}"/></radialGradient>',
         f'<radialGradient id="halo{uid}"><stop offset="0" stop-color="#ffb8d9" stop-opacity=".55"/><stop offset=".55" stop-color="#b9c4ff" stop-opacity=".22"/><stop offset="1" stop-color="#b9c4ff" stop-opacity="0"/></radialGradient>',
         f'<filter id="fr{uid}" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="2.4"/></filter>',
         f'<filter id="gw{uid}" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>',
         f'<linearGradient id="wood{uid}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#a8704a"/><stop offset=".45" stop-color="#7a4a2c"/><stop offset="1" stop-color="#4f2d18"/></linearGradient>',
         f'<linearGradient id="brass{uid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f6d3a6"/><stop offset=".5" stop-color="#c98f5c"/><stop offset="1" stop-color="#8c5a33"/></linearGradient>',
         f'<radialGradient id="lensg{uid}" cx="35%" cy="30%" r="80%"><stop offset="0" stop-color="#ffffff" stop-opacity=".55"/><stop offset=".5" stop-color="#ffffff" stop-opacity=".08"/><stop offset="1" stop-color="#cfe0ff" stop-opacity=".18"/></radialGradient>']
    for name, (a, b, c) in GRAD.items():
        g.append(f'<linearGradient id="f{uid}{name}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{a}"/><stop offset=".55" stop-color="{b}"/><stop offset="1" stop-color="{c}"/></linearGradient>')
    return ''.join(g)

def glass_cube(cam, uid, w=4, glyphs=True, faces_out=None):
    vis = {}
    for (ax, sg) in FACES:
        n = [0,0,0]; n[ax] = sg; vis[(ax, sg)] = cam.front(tuple(n), tuple(n))
    back, front = [], []
    for (ax, sg), name in FACES.items():
        n, e1, e2 = face_frame(cam, ax, sg); m = mapper(cam, n, e1, e2)
        if faces_out is not None: faces_out[name] = (m(0, 0), vis[(ax, sg)])
        quad = pts(m, [(-1,-1),(1,-1),(1,1),(-1,1)])
        if vis[(ax, sg)]:
            front.append(f'<polygon points="{quad}" fill="url(#f{uid}{name})" fill-opacity=".86"/>')
            front.append(f'<polygon points="{pts(m,[(-.84,-.84),(.84,-.84),(.84,.84),(-.84,.84)])}" fill="#ffffff" fill-opacity=".16" stroke="#ffffff" stroke-opacity=".75" stroke-width="{w*.45:.1f}" stroke-linejoin="round"/>')
            if glyphs: front.append(f'<g>{glyph(name, m, GLY, w*1.25)}</g>')
        else:
            back.append(f'<polygon points="{quad}" fill="#e9e4ff" fill-opacity=".35"/>')
            if glyphs: back.append(f'<g opacity=".55">{glyph(name, m, GLY, w*1.1)}</g>')
    edges_b, edges_f = [], []
    for v in VERTS:
        for i in range(3):
            if v[i] != -1: continue
            u = list(v); u[i] = 1; u = tuple(u)
            j, k = [a for a in range(3) if a != i]
            a, b = cam.P(v), cam.P(u)
            d = f'M{a[0]:.1f} {a[1]:.1f}L{b[0]:.1f} {b[1]:.1f}'
            (edges_b if not vis[(j, v[j])] and not vis[(k, v[k])] else edges_f).append(d)
    B = (f'<g filter="url(#fr{uid})">{"".join(back)}<path d="{"".join(edges_b)}" stroke="#ffffff" stroke-width="{w*.8:.1f}" stroke-opacity=".9" stroke-linecap="round"/></g>')
    F = ''.join(front) + f'<path d="{"".join(edges_f)}" stroke="#ffffff" stroke-width="{w*1.1:.1f}" stroke-opacity=".95" stroke-linecap="round" stroke-linejoin="round"/>'
    return B, F

def hull(pts_):
    p = sorted(set((round(x, 2), round(y, 2)) for x, y in pts_))
    def cross(o, a, b): return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
    lo, up = [], []
    for q in p:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], q) <= 0: lo.pop()
        lo.append(q)
    for q in reversed(p):
        while len(up) >= 2 and cross(up[-2], up[-1], q) <= 0: up.pop()
        up.append(q)
    return lo[:-1] + up[:-1]

def hud(P, cx, cy, r, x0, y0, x1, y1):
    o = []
    for i in range(60):
        a = math.radians(6*i)
        if 20 <= 6*i <= 70: continue
        L = 16 if i % 5 == 0 else 8
        o.append(f'M{cx+r*math.cos(a):.1f} {cy+r*math.sin(a):.1f}L{cx+(r-L)*math.cos(a):.1f} {cy+(r-L)*math.sin(a):.1f}')
    t = f'<path d="{"".join(o)}" stroke="{P["hud"]}" stroke-width="3" stroke-linecap="round" opacity=".55"/>'
    L = 40
    br = (f'M{x0} {y0+L}V{y0+12}Q{x0} {y0} {x0+12} {y0}H{x0+L} M{x1-L} {y0}H{x1-12}Q{x1} {y0} {x1} {y0+12}V{y0+L} '
          f'M{x1} {y1-L}V{y1-12}Q{x1} {y1} {x1-12} {y1}H{x1-L} M{x0+L} {y1}H{x0+12}Q{x0} {y1} {x0} {y1-12}V{y1-L}')
    return t + f'<path d="{br}" stroke="{P["hud"]}" stroke-width="7" fill="none" stroke-linecap="round" opacity=".9"/>'

LX, LY = 318, 270
def icon(P, uid, size='L'):
    """size: L＝大圖（含指標圖、HUD）；M＝48px（拿掉指標圖）；S＝16px（只留六角＋Y 線）"""
    cx, cy = 236, 232
    cam = Cam(math.radians(45), math.radians(30), D=9).fit(cx, cy, 158 if size != 'S' else 205)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><defs>{defs(uid, P)}<clipPath id="lc{uid}"><circle cx="{LX}" cy="{LY}" r="62"/></clipPath></defs>',
         f'<rect x="4" y="4" width="504" height="504" rx="116" fill="url(#bg{uid})" stroke="{P["stroke"]}" stroke-width="6"/>']
    sil = poly(hull([cam.P(v) for v in VERTS]))
    edge = '' if P is NAVY else f'<polygon points="{sil}" fill="none" stroke="{P["hud"]}" stroke-width="{ {"L": 4, "M": 12, "S": 22}[size] }" stroke-linejoin="round"/>'
    if size == 'S':
        B, F = glass_cube(cam, uid, w=14, glyphs=False)
        o += [F, edge, f'<circle cx="{cam.P((1,1,1))[0]:.1f}" cy="{cam.P((1,1,1))[1]:.1f}" r="26" fill="#f08a4b"/>', '</svg>']
        return '\n'.join(o)
    if size == 'L': o.append(hud(P, cx, cy, 214, 66, 66, 446, 446))
    o.append(f'<circle cx="{cx}" cy="{cy}" r="190" fill="url(#halo{uid})"/>')
    w = 4 if size == 'L' else 9
    B, F = glass_cube(cam, uid, w=w, glyphs=(size == 'L'))
    o += [B, F, edge]
    # 放大鏡：鏡片裡是同一顆立方放大 1.5 倍（透視的意思）
    if size == 'L':
        o.append(f'<g clip-path="url(#lc{uid})"><rect x="{LX-68}" y="{LY-68}" width="135" height="135" fill="{P["bg1"]}"/>'
                 f'<g transform="translate({LX} {LY}) scale(1.6) translate({-LX} {-LY})">{B}{F}</g></g>')
    o.append(f'<circle cx="{LX}" cy="{LY}" r="62" fill="url(#lensg{uid})"/>')
    o.append(f'<path d="M{LX-38} {LY-28} A48 48 0 0 1 {LX-6} {LY-50}" stroke="#ffffff" stroke-width="7" stroke-linecap="round" fill="none" opacity=".8"/>')
    o.append(f'<circle cx="{LX}" cy="{LY}" r="62" fill="none" stroke="url(#brass{uid})" stroke-width="{14 if size=="L" else 20}"/>')
    o.append(f'<path d="M{LX+46} {LY+46} L{LX+128} {LY+128}" stroke="url(#wood{uid})" stroke-width="{34 if size=="L" else 44}" stroke-linecap="round"/>')
    o.append(f'<path d="M{LX+42} {LY+42} L{LX+54} {LY+54}" stroke="url(#brass{uid})" stroke-width="{38 if size=="L" else 48}"/>')
    o.append('</svg>')
    return '\n'.join(o)

def save(name, s):
    open(os.path.join(HERE, name), 'w').write(s)

save('icon_navy.svg', icon(NAVY, 'n'))
save('icon_cream.svg', icon(CREAM, 'c'))
save('icon48_navy.svg', icon(NAVY, 'nm', 'M')); save('icon48_cream.svg', icon(CREAM, 'cm', 'M'))
save('icon16_navy.svg', icon(NAVY, 'ns', 'S')); save('icon16_cream.svg', icon(CREAM, 'cs', 'S'))

# ---------- 標準字 ----------
def inner(f):
    t = open(os.path.join(HERE, f)).read()
    return t.split('>', 1)[1].rsplit('</svg>', 1)[0]
NAME, EN, TAG = '股立方', 'STOCK·CUBE', '透過一面鏡，看穿六個面'
SIX = '資金・籌碼・產業・技術・事件・基本'
def lockup(P, ic):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 320"><defs><linearGradient id="lb" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{P['bg0']}"/><stop offset="1" stop-color="{P['bg1']}"/></linearGradient></defs>
<rect width="1100" height="320" rx="24" fill="url(#lb)"/>
<svg x="36" y="36" width="248" height="248" viewBox="0 0 512 512">{inner(ic)}</svg>
<text x="326" y="162" font-family="WenQuanYi Zen Hei" font-size="124" font-weight="600" letter-spacing="22" fill="{P['ink']}">{NAME}</text>
<text x="332" y="212" font-family="DejaVu Sans Mono" font-size="27" letter-spacing="11" fill="{P['hud']}">{EN}</text>
<path d="M332 236 H1056" stroke="{P['hud']}" stroke-opacity=".4" stroke-width="2"/>
<text x="332" y="280" font-family="WenQuanYi Zen Hei" font-size="27" letter-spacing="4" fill="{P['sub']}">{TAG}</text></svg>'''
def stacked(P, ic):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 640"><defs><linearGradient id="lb" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{P['bg0']}"/><stop offset="1" stop-color="{P['bg1']}"/></linearGradient></defs>
<rect width="600" height="640" rx="28" fill="url(#lb)"/>
<svg x="160" y="40" width="280" height="280" viewBox="0 0 512 512">{inner(ic)}</svg>
<text x="300" y="450" text-anchor="middle" font-family="WenQuanYi Zen Hei" font-size="104" font-weight="600" letter-spacing="18" fill="{P['ink']}">{NAME}</text>
<text x="300" y="502" text-anchor="middle" font-family="DejaVu Sans Mono" font-size="24" letter-spacing="10" fill="{P['hud']}">{EN}</text>
<text x="300" y="566" text-anchor="middle" font-family="WenQuanYi Zen Hei" font-size="25" letter-spacing="4" fill="{P['sub']}">{TAG}</text></svg>'''
save('lockup_navy.svg', lockup(NAVY, 'icon_navy.svg')); save('lockup_cream.svg', lockup(CREAM, 'icon_cream.svg'))
save('stacked_navy.svg', stacked(NAVY, 'icon_navy.svg')); save('stacked_cream.svg', stacked(CREAM, 'icon_cream.svg'))

# ---------- 六個面（攤平） ----------
SIXF = [('資金面', '錢往哪裡跑', '資金流向・資金輪盤・雷達・熱力圖', ('#ffe3f1', '#e2daff', '#cfeeff')),
        ('產業面', '上下游誰最強', '2D／3D 產業地圖・產業鏈關聯', ('#b8ddff', '#d6c8ff', '#ffcde4')),
        ('技術面', '什麼時候進場', 'K 線・多週期 SMC・技術評分', ('#ffc4dc', '#dcc6ff', '#b9d4ff')),
        ('籌碼面', '誰在買、誰在賣', '法人買賣超・集保大戶', ('#d9f0ff', '#e4dcff', '#ffe0ee')),
        ('基本面', '現在貴不貴', '營收・獲利・本益比河流・週期統計', ('#ffe9d6', '#f3dcff', '#d6e6ff')),
        ('事件面', '有沒有理由不進場', '今日事件・新聞・總經', ('#e6dcff', '#ffd6e8', '#d2ecff'))]
def six(P):
    W, cw = 1500, 230
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} 470"><defs>']
    for i, (_, _, _, (a, b, c)) in enumerate(SIXF):
        o.append(f'<linearGradient id="t{i}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{a}"/><stop offset=".55" stop-color="{b}"/><stop offset="1" stop-color="{c}"/></linearGradient>')
    o.append(f'</defs><rect width="{W}" height="470" rx="24" fill="{P["bg1"]}"/>')
    for i, (name, q, feats, _) in enumerate(SIXF):
        x = 30 + i*(cw+18); cx, cy, hs = x+cw/2, 150, 92
        o.append(f'<rect x="{cx-hs}" y="{cy-hs}" width="{2*hs}" height="{2*hs}" rx="22" fill="url(#t{i})" stroke="#ffffff" stroke-width="5"/>')
        o.append(f'<rect x="{cx-hs+14}" y="{cy-hs+14}" width="{2*hs-28}" height="{2*hs-28}" rx="14" fill="#ffffff" fill-opacity=".18" stroke="#ffffff" stroke-opacity=".7" stroke-width="2"/>')
        m = lambda u, v, cx=cx, cy=cy: (cx + u*hs, cy - v*hs)
        o.append(glyph(name, m, GLY, 7))
        o.append(f'<text x="{cx}" y="290" text-anchor="middle" font-family="DejaVu Sans Mono" font-size="20" fill="{P["hud"]}">0{i+1}</text>')
        o.append(f'<text x="{cx}" y="334" text-anchor="middle" font-family="WenQuanYi Zen Hei" font-size="34" font-weight="600" fill="{P["ink"]}">{name}</text>')
        o.append(f'<text x="{cx}" y="374" text-anchor="middle" font-family="WenQuanYi Zen Hei" font-size="21" fill="{P["hud"]}">{q}</text>')
        parts = feats.split('・'); half = (len(parts)+1)//2
        for j, line in enumerate(('・'.join(parts[:half]), '・'.join(parts[half:]))):
            o.append(f'<text x="{cx}" y="{410+j*28}" text-anchor="middle" font-family="WenQuanYi Zen Hei" font-size="18" fill="{P["sub"]}">{line}</text>')
    o.append('</svg>')
    return '\n'.join(o)
save('six_navy.svg', six(NAVY)); save('six_cream.svg', six(CREAM))
