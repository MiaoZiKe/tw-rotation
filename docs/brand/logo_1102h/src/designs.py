from lib import *

DN = {('A', 'light'): '#0A8CA3', ('A', 'dark'): '#3CC8DC', ('B', 'light'): '#0E8F7E', ('B', 'dark'): '#35D0B5'}
DESIGNS = []
def design(id, name, idea, fonts, icon_modes=('light', 'dark'), box=(290, 290)):
    def deco(fn):
        DESIGNS.append(dict(id=id, name=name, idea=idea, fonts=fonts, mk=fn, icon_modes=icon_modes, box=box)); return fn
    return deco

# ---------------------------------------------------------------- H01 幾何字標
@design('H01', '幾何字標', 'L I G U 同一套圓頭幾何筆畫重新構成；i 的點做成橘色「資金落點」，圖示 G 的橫槓一路延伸到中心落點。',
        '無（自繪幾何筆畫）', ('light', 'dark'), (270, 270))
def h01(P, pk, mode):
    k = mk(18); x = 0; s = ''
    a, w = k.L(x, P['fg']); s += a; x += w + 22
    a, w = k.I(x, P['fg'], dot=P['ac']); s += a; x += w + 22
    a, w = k.G(x, P['fg']); s += a; x += w + 22
    a, w = k.U(x, P['fg']); s += a; x += w
    word = (s, (0, 0, x, 100))
    g, _ = k.G(0, P['fg'])
    ico = (g + C(50, 50, 15, P['ac']), (0, 0, 100, 100))
    return word, ico

# ---------------------------------------------------------------- H02 輪動 G
def rot_g(x0, P, sw=18, col=None, ang=58, barcol=None):
    r = 50 - sw / 2; cx = x0 + 50; cy = 50; col = col or P['ac']
    ex = cx + r * math.cos(rad(ang)); ey = cy - r * math.sin(rad(ang))
    tx, ty = math.cos(rad(-ang) + math.pi / 2), math.sin(rad(-ang) + math.pi / 2)  # 順時針切線
    tx, ty = -math.sin(rad(-ang)), math.cos(rad(-ang))
    nx, ny = -ty, tx
    b1 = (ex - 2 * tx + 21 * nx, ey - 2 * ty + 21 * ny); b2 = (ex - 2 * tx - 21 * nx, ey - 2 * ty - 21 * ny)
    tip = (ex + 25 * tx, ey + 25 * ty)
    d = f'M{n2(cx+3)},{n2(cy)} H{n2(cx+r)} A{n2(r)},{n2(r)} 0 1 1 {n2(ex)},{n2(ey)}'
    head = Pth(f'M{n2(b1[0])},{n2(b1[1])} L{n2(tip[0])},{n2(tip[1])} L{n2(b2[0])},{n2(b2[1])} Z', col,
               f'stroke="{col}" stroke-width="5" stroke-linejoin="round"')
    return S(d, col, sw) + head

@design('H02', '輪動圓 G', 'G 的缺口＋箭頭＝資金順時針輪動，箭頭追著橫槓跑；其餘字母保持乾淨。',
        '無（自繪幾何筆畫）', ('dark', 'light'), (300, 300))
def h02(P, pk, mode):
    k = mk(18); x = 0; s = ''
    a, w = k.L(x, P['fg']); s += a; x += w + 22
    a, w = k.I(x, P['fg']); s += a; x += w + 22
    s += rot_g(x, P); x += 100 + 22
    a, w = k.U(x, P['fg']); s += a; x += w
    return (s, (0, 0, x, 100)), (rot_g(0, P), (0, 0, 100, 100))

# ---------------------------------------------------------------- H03 U 杯子
def cup(x0, P, coin=True):
    k = mk(18); xl = x0 + 9; ra = 32; cy = 59; ic = xl + 32
    liq = (f'M{n2(xl+9)},46 Q{n2(xl+20.5)},38 {n2(ic)},46 T{n2(xl+55)},46 V{cy} '
           f'A23,23 0 0 1 {n2(xl+9)},{cy} Z')
    s = Pth(liq, P['ac'])
    u, w = k.U(x0, P['fg']); s += u
    if coin: s += C(ic, 21, 9.5, P['ac'])
    return s, w

@design('H03', '杯子 U', 'U 是裝資金的杯子，橘色資金水位＋落下的一枚硬幣；L 的腳往右上揚起，一進一出。',
        '無（自繪幾何筆畫）', ('light', 'dark'), (250, 290))
def h03(P, pk, mode):
    k = mk(18); x = 0; s = ''
    s += S('M9,9 V91 H46', P['fg'], 18) + S('M46,91 Q80,91 92,56', P['ac'], 18)
    x = 103 + 22
    a, w = k.I(x, P['fg'], dot=P['ac']); s += a; x += w + 22
    a, w = k.G(x, P['fg']); s += a; x += w + 22
    a, w = cup(x, P); s += a; x += w
    c, w = cup(0, P)
    return (s, (0, 0, x, 100)), (c, (0, 0, w, 100))

# ---------------------------------------------------------------- H04 連筆
@design('H04', '連筆資金線', 'L 的腳接進 I 的豎線、G 的尾巴接進 U 的杯底，橘色連筆＝一條連續流動的資金線；圖示取 L→i 連筆。',
        '無（自繪幾何筆畫）', ('dark', 'light'), (270, 290))
def h04(P, pk, mode):
    k = mk(18); fg, ac = P['fg'], P['ac']
    li_fg = S('M9,9 V91 H57 Q75,91 75,73 V43', fg, 18)
    li_ac = S('M34,91 H57 Q75,91 75,73 V43', ac, 18) + C(75, 13, 13, ac)
    s = li_fg + li_ac
    g, _ = k.G(106, fg); s += g
    u, _ = k.U(228, fg); s += u
    s += S('M156,91 H269', ac, 18)
    return (s, (0, 0, 310, 100)), (li_fg + li_ac, (0, 0, 84, 100))

# ---------------------------------------------------------------- H05 粗字換色
@design('H05', '粗體大寫＋G 換色', 'Poppins ExtraBold 大寫 LIGU，只把 G 換成橘（紅）色，極簡專業、一眼記得住「G」。',
        'Poppins ExtraBold（OFL）', ('light', 'dark'), (300, 300))
def h05(P, pk, mode):
    g, W = run('poppins', 'LIGU', 100, 0.03); s = ''
    for ch, d, x, adv, b in g:
        s += Pth(d, P['ac'] if ch == 'G' else P['fg'], f'transform="translate({n2(x)},0)"')
    y0 = min(b[1] for *_, b in g); y1 = max(b[3] for *_, b in g)
    d, adv, b = glyph('poppins', 'G', 100)
    ico = Pth(d, P['ac'])
    return (s, (g[0][4][0], y0, W - (g[-1][3] - g[-1][4][2]), y1)), (ico, b)

# ---------------------------------------------------------------- H06 圓潤小寫
@design('H06', '圓潤小寫 ligu', 'Nunito Black 圓體小寫，四個字母四種糖果色、微微彈跳；i 的點是橘色大圓點。圖示取 gu。',
        'Nunito Black（OFL）', ('light', 'dark'), (300, 300))
def h06(P, pk, mode):
    cols = [P['ac'], P['ac2'], P['ac3'], DN[(pk, mode)]]
    rots = [-5, 4, -4, 5]; dys = [0, -4, 3, -3]
    size = 100; s = ''; x = 0; pos = []
    for i, ch in enumerate('ligu'):
        gch = 'ı' if ch == 'i' else ch
        d, adv, b = glyph('nunito', gch, size)
        ox = (b[0] + b[2]) / 2; oy = (b[1] + b[3]) / 2
        inner = Pth(d, cols[i])
        if ch == 'i':
            rr = (b[2] - b[0]) * 0.82
            inner += C(ox, b[1] - rr * 1.15, rr, P['ac'])
        s += f'<g transform="translate({n2(x)},{dys[i]}) rotate({rots[i]},{n2(ox)},{n2(oy)})">{inner}</g>'
        pos.append((x, ch, d, adv, b)); x += adv + 3
    top = min(p[4][1] for p in pos); bot = max(p[4][3] for p in pos)
    ib = pos[1][4]; top = min(top, ib[1] - (ib[2] - ib[0]) * 0.82 * 2.3)
    word = (s, (pos[0][4][0] - 6, top - 8, x + 4, bot + 10))
    # 圖示 gu
    ic = ''
    x2 = 0
    for i, ch in enumerate('gu'):
        d, adv, b = glyph('nunito', ch, 100)
        ox = (b[0] + b[2]) / 2; oy = (b[1] + b[3]) / 2
        ic += f'<g transform="translate({n2(x2)},{[-2,3][i]}) rotate({[-5,5][i]},{n2(ox)},{n2(oy)})">{Pth(d, [P["ac3"], P["ac"]][i])}</g>'
        x2 += adv + 2
    return word, (ic, (6, -62, x2 + 2, 52))

# ---------------------------------------------------------------- H07 2×2 疊字
def block(P):
    k = mk(20); tiles = [('L', P['ac']), ('I', P['ac2']), ('G', P['ac3']), ('U', DN[P['_k']])]
    s = ''
    for i, (ch, col) in enumerate(tiles):
        tx = (i % 2) * 108; ty = (i // 2) * 108
        s += R(tx, ty, 100, 100, col, 26)
        lc = on(P, col); sc = 0.52
        if ch == 'L': a, w = k.L(0, lc)
        elif ch == 'I': a, w = k.I(0, lc, dot=lc)
        elif ch == 'G': a, w = k.G(0, lc)
        else: a, w = k.U(0, lc)
        if ch == 'I': w = 2 * 0.72 * 20
        s += Gp(a, tx + 50 - w * sc / 2, ty + 50 - 50 * sc, sc)
    return s
@design('H07', '2×2 疊字方塊', 'LI／GU 疊成四色方塊，可單獨當方形圖示；橫式是方塊＋「哩股哩股」＋LIGU LIGU。',
        '自繪幾何筆畫＋Noto Sans TC Black、Poppins ExtraBold（OFL）', ('dark', 'light'), (300, 300))
def h07(P, pk, mode):
    P = dict(P); P['_k'] = (pk, mode)
    b = block(P)
    t, tw = run('sans', '哩股哩股', 84, 0.06)
    ty0 = min(bb[1] for *_, bb in t)
    ts = ''
    for ch, d, x, adv, bb in t: ts += Pth(d, P['fg'], f'transform="translate({n2(x)},0)"')
    t2, tw2 = run('poppins', 'LIGU LIGU', 33, 0.28)
    ts2 = ''.join(Pth(d, P['ac'], f'transform="translate({n2(x)},0)"') for ch, d, x, adv, bb in t2)
    tx = 208 + 44
    top = 30; base1 = top - ty0
    base2 = base1 + 20 + 25
    s = b + f'<g transform="translate({tx},{n2(base1)})">{ts}</g><g transform="translate({tx+2},{n2(base2+ 4)})">{ts2}</g>'
    word = (s, (0, 0, tx + max(tw, tw2), 208))
    return word, (b, (0, 0, 208, 208))

# ---------------------------------------------------------------- H08 LIGU LIGU
def ligu_row(k, col, dys=(0, 0, 0, 0), gap=18, x=0):
    s = ''
    for i, (f, kw) in enumerate([(k.L, {}), (k.I, dict(dot=col)), (k.G, {}), (k.U, {})]):
        a, w = f(0, col, **kw)
        s += f'<g transform="translate({n2(x)},{n2(dys[i])})">{a}</g>'; x += w + gap
    return s, x - gap

@design('H08', 'LIGU LIGU 錯位上升', '名稱重複兩次：第一組貼地，第二組換橘色並逐字抬高，像一根一根墊高的 K 棒；圖示是階梯式的雙 L。',
        '無（自繪幾何筆畫）', ('light', 'dark'), (290, 290))
def h08(P, pk, mode):
    k = mk(14)
    s1, w1 = ligu_row(k, P['fg'])
    dys = [-10 - 9 * i for i in range(4)]
    s2, w2 = ligu_row(k, P['ac'], dys)
    s = s1 + f'<g transform="translate({n2(w1+56)},0)">{s2}</g>'
    k2 = mk(26)
    a, _ = k2.L(0, P['fg']); b, _ = k2.L(0, P['ac'])
    ico = a + f'<g transform="translate(50,-50)">{b}</g>'
    return (s, (0, -37, w1 + 56 + w2, 100)), (ico, (0, -50, 116, 100))

# ---------------------------------------------------------------- H09 K 棒字形
def candle(x, w, wy0, wy1, by0, by1, col):
    return R(x + w / 2 - 2, wy0, 4, wy1 - wy0, col) + R(x, by0, w, by1 - by0, col, 4.5)

def trend_g(x0, P, sw=18):
    r = 50 - sw / 2; cx = x0 + 50; cy = 50
    a0 = 82
    ex, ey = cx + r * math.cos(rad(a0)), cy - r * math.sin(rad(a0))
    ring = S(f'M{n2(ex)},{n2(ey)} A{n2(r)},{n2(r)} 0 1 0 {n2(cx+r)},{n2(cy)} H{n2(cx+r-22)}', P['fg'], sw)
    d = (0.72, -0.69); n = (0.69, 0.72)
    x1, y1 = cx - 12, cy + 16; x2, y2 = cx + 22, cy - 18
    tip = (x2 + 8, y2 - 8)
    w1 = (tip[0] - 17 * d[0] + 12 * n[0], tip[1] - 17 * d[1] + 12 * n[1])
    w2 = (tip[0] - 17 * d[0] - 12 * n[0], tip[1] - 17 * d[1] - 12 * n[1])
    arrow = S(f'M{n2(x1)},{n2(y1)} L{n2(x2)},{n2(y2)}', P['ac'], 14) + \
        S(f'M{n2(w1[0])},{n2(w1[1])} L{n2(tip[0])},{n2(tip[1])} L{n2(w2[0])},{n2(w2[1])}', P['ac'], 14)
    return ring + arrow

@design('H09', 'K 棒字形', 'I 是一根紅 K 棒、U 是由五根 K 棒排成的凹谷（綠跌紅漲、谷底金），G 的橫槓換成穿出缺口的趨勢箭頭。',
        '無（自繪幾何＋K 棒）', ('dark', 'light'), (300, 300))
def h09(P, pk, mode):
    k = mk(18); up = P['ac']; dn = DN[(pk, mode)]; mid = P['ac2']
    s = ''
    a, w = k.L(0, P['fg']); s += a
    s += candle(88, 28, 0, 100, 28, 76, up)
    s += trend_g(138, P)
    ux = 268; w15 = 17
    specs = [(0, 66, 6, 56, dn), (42, 92, 50, 80, dn), (66, 100, 74, 92, mid), (42, 92, 50, 80, up), (0, 66, 6, 56, up)]
    for i, (wy0, wy1, by0, by1, c) in enumerate(specs):
        s += candle(ux + i * 25, w15, wy0, wy1, by0, by1, c)
    word = (s, (0, 0, ux + 4 * 25 + 17, 100))
    ico = trend_g(0, P)
    return word, (ico, (0, -4, 112, 100))

# ---------------------------------------------------------------- H10 襯線雜誌
@design('H10', '襯線雜誌風', 'Fraunces 高對比襯線 LIGU，右上角一輪小太陽（圓＋軌道環）當記號，下方細線夾「哩股哩股」。',
        'Fraunces Bold、Noto Serif TC Black（OFL）', ('dark', 'light'), (270, 270))
def h10(P, pk, mode):
    g, W = run('fraunces', 'LIGU', 200, 0.07)
    s = ''
    for ch, d, x, adv, b in g: s += Pth(d, P['fg'], f'transform="translate({n2(x)},0)"')
    top = min(b[1] for *_, b in g)
    wend = W - (g[-1][3] - g[-1][4][2])
    sx = wend + 36; sy = top + 20
    s += C(sx, sy, 15, P['ac']) + f'<circle cx="{n2(sx)}" cy="{n2(sy)}" r="28" fill="none" stroke="{P["ac"]}" stroke-width="3"/>'
    t, tw = run('serif', '哩股哩股', 40, 0.4)
    tyc = 62
    ty0 = min(b[1] for *_, b in t); ty1 = max(b[3] for *_, b in t)
    base = tyc - (ty0 + ty1) / 2
    right = sx + 28
    s += ''.join(Pth(d, P['fg'], f'transform="translate({n2((right-tw)/2+x)},{n2(base)})"') for ch, d, x, adv, b in t)
    ly = tyc
    s += f'<path d="M0,{ly} H{n2((right-tw)/2-24)} M{n2((right+tw)/2+24)},{ly} H{n2(right)}" stroke="{P["fg"]}" stroke-width="3" opacity=".55"/>'
    word = (s, (0, top, right, tyc + 24))
    d, adv, b = glyph('fraunces', 'G', 300)
    ico = Pth(d, P['fg']) + C(b[2] - 8, b[1] + 8, 22, P['ac'])
    return word, (ico, (b[0], b[1] - 14, b[2] + 14, b[3]))
