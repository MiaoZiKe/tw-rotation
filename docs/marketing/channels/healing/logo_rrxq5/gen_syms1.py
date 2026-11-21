
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
