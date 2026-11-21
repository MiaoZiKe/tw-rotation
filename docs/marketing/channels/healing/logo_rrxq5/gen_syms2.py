
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
