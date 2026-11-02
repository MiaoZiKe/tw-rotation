from lib import *

DESIGNS = []
def design(id, name, idea, fonts, box=(290, 290), icon_bg=None):
    def deco(fn):
        DESIGNS.append(dict(id=id, name=name, idea=idea, fonts=fonts, mk=fn, box=box, icon_bg=icon_bg)); return fn
    return deco

def chev(tip, d, col, sw, L=18, sp=13):
    m = math.hypot(*d); d = (d[0] / m, d[1] / m); n = (-d[1], d[0])
    w1 = (tip[0] - L * d[0] + sp * n[0], tip[1] - L * d[1] + sp * n[1])
    w2 = (tip[0] - L * d[0] - sp * n[0], tip[1] - L * d[1] - sp * n[1])
    return S(f'M{n2(w1[0])},{n2(w1[1])} L{n2(tip[0])},{n2(tip[1])} L{n2(w2[0])},{n2(w2[1])}', col, sw)

def grad(id, x1, x2, c1, c2):
    return (f'<defs><linearGradient id="{id}" gradientUnits="userSpaceOnUse" x1="{x1}" y1="0" x2="{x2}" y2="0">'
            f'<stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient></defs>')

def li_parts(P, ac, ox=0):
    fg = S('M9,9 V91 H57 Q75,91 75,73 V43', P['fg'], 18)
    a = S('M34,91 H57 Q75,91 75,73 V43', ac, 18) + C(75, 13, 13, ac)
    return fg, a

# ---------------------------------------------------------------- I01 兩段連筆（H04 精修）
@design('I01', '兩段連筆（精修）', 'H04 原案精修：L 腳接進 i、G 尾接進 U 杯底，橘色連筆；頭像改成「Li」——L 的橘色長腳托住 i，不再是怪怪的 Lj。', '自繪幾何筆畫', (270, 270))
def i01(P, mode):
    k = mk(18); fg, a = li_parts(P, P['ac'])
    g, _ = k.G(106, P['fg']); u, _ = k.U(228, P['fg'])
    word = fg + a + g + u + S('M156,91 H269', P['ac'], 18)
    ico = (S('M10,10 V90 H50', P['fg'], 20) + S('M50,90 H122', P['ac'], 20) + S('M92,46 V90', P['fg'], 20) + C(92, 14, 14, P['ac']))
    return word, ico

# ---------------------------------------------------------------- I02 共用地板（單色）
@design('I02', '共用地板・單色', '四個字母站在同一條地板上：L 的腳一路延伸、穿過 I、G 的底、接進 U 的杯底，整個字標只有墨藍一色＋橘色 i 點；頭像是 G 拖出一條帶終點圓點的尾巴。', '自繪幾何筆畫', (290, 250))
def i02(P, mode):
    k = mk(18); fg = P['fg']
    s = S('M9,91 H299', fg, 18)
    s += k.L(0, fg)[0] + k.I(88, fg, dot=P['ac'])[0] + k.G(136, fg)[0] + k.U(258, fg)[0]
    g, _ = k.G(0, fg)
    ico = g + S('M50,91 H138', P['ac'], 18) + C(146, 91, 13, P['ac'])
    return s, ico

# ---------------------------------------------------------------- I03 股價線貫穿
@design('I03', '股價線貫穿', '字標底下一條折線貫穿四字（起點墨點、終點上衝箭頭），像一根股價線；頭像是整條資金線＋起點終點兩顆點。', '自繪幾何筆畫', (300, 220))
def i03(P, mode):
    k = mk(14); s = ''; x = 0
    for f, kw, gap in [(k.L, {}, 22), (k.I, dict(dot=P['ac']), 22), (k.G, {}, 22), (k.U, {}, 0)]:
        a, w = f(x, P['fg'], **kw); s += a; x += w + gap
    pts = [(0, 146), (32, 132), (60, 146), (100, 124), (134, 138), (176, 122), (212, 134), (256, 124), (296, 134), (330, 122), (360, 74)]
    line = 'M' + ' L'.join(f'{a},{b}' for a, b in pts)
    s += S(line, P['ac'], 9) + C(0, 146, 8, P['fg']) + chev(pts[-1], (30, -48), P['ac'], 9, 16, 11)
    pts2 = [(0, 120), (28, 94), (52, 112), (88, 70), (112, 86), (150, 38), (176, 52), (214, 4)]
    ico = S('M' + ' L'.join(f'{a},{b}' for a, b in pts2), P['ac'], 16) + C(0, 120, 15, P['fg']) + C(214, 4, 17, P['ac'])
    return s, ico

# ---------------------------------------------------------------- I04 階梯收盤線
@design('I04', '階梯收盤線', '底下的資金線是 K 線收盤價連成的階梯，一階一階往上，每階一顆收盤點，尾端箭頭；頭像是三階樓梯＋箭頭。', '自繪幾何筆畫', (270, 250))
def i04(P, mode):
    k = mk(16); s = ''; x = 0
    for f, kw, gap in [(k.L, {}, 22), (k.I, dict(dot=P['ac']), 22), (k.G, {}, 22), (k.U, {}, 0)]:
        a, w = f(x, P['fg'], **kw); s += a; x += w + gap
    s += S('M0,170 H88 V154 H176 V138 H264 V122 H340', P['ac'], 9)
    for px, py in [(0, 170), (88, 154), (176, 138), (264, 122)]: s += C(px, py, 8, P['fg'])
    s += chev((352, 122), (1, 0), P['ac'], 9, 16, 11)
    ico = S('M0,120 H46 V84 H92 V48 H138 V12 H168', P['ac'], 18) + C(0, 120, 15, P['fg']) + C(46, 84, 12, P['fg']) + C(92, 48, 12, P['fg']) + C(138, 12, 12, P['fg'])
    ico += chev((176, 12), (1, 0), P['ac'], 18, 24, 18)
    return s, ico

# ---------------------------------------------------------------- I05 U 尾巴衝出
@design('I05', 'U 尾巴衝出箭頭', 'G 的尾巴流進 U 杯底，再沿 U 右臂一路往上衝破字高、變成箭頭：資金流入、拉升；頭像是 U 杯＋流入線＋衝出箭頭。', '自繪幾何筆畫', (290, 290))
def i05(P, mode):
    k = mk(18)
    s = k.L(0, P['fg'])[0] + k.I(88, P['fg'], dot=P['ac'])[0] + k.G(136, P['fg'])[0] + k.U(258, P['fg'])[0]
    s += S('M186,91 H299 A32,32 0 0 0 331,59 V-22', P['ac'], 18) + chev((331, -36), (0, -1), P['ac'], 18, 20, 16) + C(186, 91, 9, P['ac'])
    ico = k.U(0, P['fg'])[0] + S('M-46,91 H41 A32,32 0 0 0 73,59 V-22', P['ac'], 18) + chev((73, -36), (0, -1), P['ac'], 18, 20, 16) + C(-46, 91, 12, P['ac'])
    return s, ico

# ---------------------------------------------------------------- I06 粗體＋底下曲線
@design('I06', '粗體＋資金曲線', 'Poppins ExtraBold 大寫，底下一條橘色資金曲線從 L 下方出發、微微下沉再上揚收成箭頭；頭像是粗體 G ＋同一條曲線。', 'Poppins ExtraBold（OFL）', (280, 280))
def i06(P, mode):
    g, W = run('poppins', 'LIGU', 100, 0.03); s = ''
    for ch, d, x, adv, b in g: s += Pth(d, P['fg'], f'transform="translate({n2(x)},0)"')
    W2 = W - (g[-1][3] - g[-1][4][2]); x0 = g[0][4][0]
    ex, ey = W2 + 14, -14
    s += S(f'M{n2(x0)},30 C{n2(x0+W2*.3)},52 {n2(x0+W2*.7)},52 {n2(ex)},{ey}', P['ac'], 10) + C(x0, 30, 8, P['ac']) + chev((ex + 4, ey - 8), (0.55, -0.83), P['ac'], 10, 16, 12)
    d, adv, b = glyph('poppins', 'G', 100)
    ico = Pth(d, P['fg']) + S(f'M{n2(b[0])},30 C{n2(b[0]+30)},52 {n2(b[2]-40)},52 {n2(b[2]+10)},-12', P['ac'], 10) + C(b[0], 30, 8, P['ac']) + chev((b[2] + 14, -20), (0.55, -0.83), P['ac'], 10, 16, 12)
    return s, ico

# ---------------------------------------------------------------- I07 圓潤小寫連筆
@design('I07', '圓潤小寫 ligu 連筆', 'Nunito Black 小寫 ligu，底下一條藍色笑弧從 l 連到 u 尾端上揚（親切＋資金上揚）；橘色大圓點是 i 的點；頭像是 li 加同一條弧。', 'Nunito Black（OFL）', (280, 280))
def i07(P, mode):
    s = ''; x = 0; pos = []
    for ch in 'ligu':
        d, adv, b = glyph('nunito', 'ı' if ch == 'i' else ch, 100)
        s += Pth(d, P['fg'], f'transform="translate({n2(x)},0)"')
        if ch == 'i':
            rr = (b[2] - b[0]) * 0.82; s += C(x + (b[0] + b[2]) / 2, b[1] - rr * 1.15, rr, P['ac'])
        pos.append((x, b, adv)); x += adv + 3
    xe = pos[-1][0] + pos[-1][1][2]; x0 = pos[0][0] + pos[0][1][0]
    s += S(f'M{n2(x0)},46 C{n2(x0+70)},74 {n2(xe-60)},74 {n2(xe+12)},-6', P['ac2'], 10) + C(x0, 46, 8, P['ac2']) + chev((xe + 16, -14), (0.45, -0.9), P['ac2'], 10, 16, 12)
    s2 = ''; x = 0; pp = []
    for ch in 'li':
        d, adv, b = glyph('nunito', 'ı' if ch == 'i' else ch, 100)
        s2 += Pth(d, P['fg'], f'transform="translate({n2(x)},0)"')
        if ch == 'i':
            rr = (b[2] - b[0]) * 0.82; s2 += C(x + (b[0] + b[2]) / 2, b[1] - rr * 1.15, rr, P['ac'])
        pp.append((x, b)); x += adv + 3
    xe2 = pp[-1][0] + pp[-1][1][2]; xs = pp[0][0] + pp[0][1][0]
    s2 += S(f'M{n2(xs)},40 C{n2(xs+20)},60 {n2(xe2-10)},60 {n2(xe2+16)},-8', P['ac2'], 10) + C(xs, 40, 8, P['ac2']) + chev((xe2 + 20, -16), (0.45, -0.9), P['ac2'], 10, 16, 12)
    return s, s2

# ---------------------------------------------------------------- I08 細線＋藍→橘漸層穿越線
@design('I08', '細線大寫＋漸層穿越線', '細線大寫 LIGU，一條藍→橘漸層資金線斜斜穿過整個字（穿過 G 的位置就是橫槓），錢從藍流到橘；頭像是細線 G 被同一條漸層線穿過。', '自繪幾何筆畫', (280, 280))
def i08(P, mode):
    k = mk(10); gid = 'gr8'; fg = P['fg']
    s = grad(gid, -30, 390, P['ac2'], P['ac']) + S('M-30,74 L384,26', f'url(#{gid})', 10)
    s += chev((392, 25), (414, -48), P['ac'], 10, 18, 13)
    x = 0
    for f, kw, gap in [(k.L, {}, 24), (k.I, dict(dot=P['ac']), 24), (k.G, {}, 24), (k.U, {}, 0)]:
        a, w = f(x, fg, **kw); s += a; x += w + gap
    g, _ = k.G(0, fg)
    ico = grad('gr8b', -24, 130, P['ac2'], P['ac']) + g + S('M-24,80 L124,20', 'url(#gr8b)', 10) + chev((132, 17), (148, -60), P['ac'], 10, 18, 13)
    return s, ico

# ---------------------------------------------------------------- I09 台股紅・波動後上揚
@design('I09', '台股紅・波動後上揚', '資金線用台股紅：G 的尾巴先上下震盪、再爬進 U 杯底，波動後上揚；頭像是 L 的腳變成震盪後衝高的紅線。', '自繪幾何筆畫', (280, 280))
def i09(P, mode):
    k = mk(18); rd = P['rd']
    fg, a = li_parts(P, rd)
    g, _ = k.G(106, P['fg']); u, _ = k.U(228, P['fg'])
    s = fg + a + g + u
    s += S('M156,91 L176,108 L196,92 L216,110 L240,96 L269,91', rd, 14, 'stroke-linejoin="round"')
    ico = S('M9,9 V91 H30', P['fg'], 20) + S('M30,91 L56,108 L78,90 L102,106 L132,58', rd, 18) + chev((142, 42), (10, -16), rd, 18, 22, 17)
    return s, ico

# ---------------------------------------------------------------- I10 中文字標＋LIGU 一線穿
@design('I10', '哩股哩股＋LIGU 一線穿', '粗黑體「哩股哩股」，每個字下方站一個 L／I／G／U，四個字母站在同一條橘線上（起點圓點、終點箭頭）；頭像是「哩」加一道上揚橘弧。', 'Noto Sans TC Black（OFL）', (300, 300))
def i10(P, mode):
    t, tw = run('sans', '哩股哩股', 120, 0.05)
    s = ''.join(Pth(d, P['fg'], f'transform="translate({n2(x)},0)"') for ch, d, x, adv, b in t)
    sc = 0.42; k = mk(18); ly = 46 + sc * 91
    cxs = [x + adv / 2 for ch, d, x, adv, b in t]
    s += S(f'M{n2(cxs[0]-70)},{n2(ly)} H{n2(cxs[3]+66)}', P['ac'], 18 * sc * 1.15) + C(cxs[0] - 70, ly, 7, P['ac'])
    s += chev((cxs[3] + 78, ly), (1, 0), P['ac'], 18 * sc * 1.15, 14, 10)
    for i, (f, kw) in enumerate([(k.L, {}), (k.I, dict(dot=P['ac'])), (k.G, {}), (k.U, {})]):
        a, w = f(0, P['fg'], **kw); s += Gp(a, cxs[i] - w * sc / 2, 46, sc)
    d, adv, b = glyph('sans', '哩', 300)
    ico = Pth(d, P['fg']) + S(f'M{n2(b[0])},{n2(b[3]+34)} Q{n2((b[0]+b[2])/2)},{n2(b[3]+70)} {n2(b[2]+10)},{n2(b[3]-6)}', P['ac'], 20) + C(b[0], b[3] + 34, 14, P['ac']) + chev((b[2] + 18, b[3] - 20), (0.5, -0.85), P['ac'], 20, 28, 20)
    return s, ico

# ---------------------------------------------------------------- I11 粉圓中文＋LIGU─LIGU 連鎖
@design('I11', '粉圓中文＋LIGU 連鎖', '粉圓體「哩股哩股」，下方 LIGU LIGU 兩組用同一條橘線連成鎖鏈（G→U→下一組 L→i…→箭頭）；頭像是橘底奶油「哩」＋下方連線與終點。', 'Huninn 粉圓（OFL）、自繪筆畫', (300, 300), icon_bg='ac')
def i11(P, mode):
    t, tw = run('huninn', '哩股哩股', 96, 0.08)
    s = ''.join(Pth(d, P['ac'] if ch == '股' else P['fg'], f'transform="translate({n2(x)},0)"') for ch, d, x, adv, b in t)
    sc = 0.5; off = 34; k = mk(18); gw = 310 * sc; gap = tw - 2 * gw
    inner = ''
    for gi in range(2):
        ox = gi * (gw + gap)
        fg, a = li_parts(P, P['ac']); g, _ = k.G(106, P['fg']); u, _ = k.U(228, P['fg'])
        inner += f'<g transform="translate({n2(ox)},{off}) scale({sc})">{fg}{g}{u}{S("M156,91 H269", P["ac"], 18)}{a}</g>'
    yl = off + 91 * sc
    xu = 269 * sc; x2 = gw + gap + 9 * sc
    inner += S(f'M{n2(xu)},{n2(yl)} H{n2(x2)}', P['ac'], 9)
    xe = gw + gap + 269 * sc
    inner += S(f'M{n2(xe)},{n2(yl)} H{n2(xe+36)}', P['ac'], 9) + chev((xe + 44, yl), (1, 0), P['ac'], 9, 12, 9)
    s += inner
    d, adv, b = glyph('huninn', '哩', 260)
    ico = Pth(d, P['bg']) + S(f'M{n2(b[0])},{n2(b[3]+30)} H{n2(b[2]-14)}', P['bg'], 18) + C(b[2] + 4, b[3] + 30, 15, P['bg'])
    return s, ico

# ---------------------------------------------------------------- I12 輪動軌道
@design('I12', '輪動軌道圈', 'LIGU 被一圈橘色軌道繞住，軌道繞行、尾端箭頭追著起點（資金輪動＝輪迴）；頭像是 G 外面一圈傾斜軌道。', '自繪幾何筆畫', (290, 290))
def i12(P, mode):
    k = mk(18)
    s = k.L(0, P['fg'])[0] + k.I(88, P['fg'], dot=P['ac'])[0] + k.G(136, P['fg'])[0] + k.U(258, P['fg'])[0]
    cx, cy, rx, ry = 170, 50, 236, 86
    a0, a1 = rad(14), rad(318)
    sx, sy = cx + rx * math.cos(a0), cy + ry * math.sin(a0); ex, ey = cx + rx * math.cos(a1), cy + ry * math.sin(a1)
    orb = S(f'M{n2(sx)},{n2(sy)} A{rx},{ry} 0 1 1 {n2(ex)},{n2(ey)}', P['ac'], 8)
    tx, ty = -rx * math.sin(a1), ry * math.cos(a1)
    orb += chev((ex + tx * 0.05, ey + ty * 0.05), (tx, ty), P['ac'], 8, 20, 14)
    g, _ = k.G(0, P['fg']); gcx, gcy = 50, 50; rx2, ry2 = 98, 34
    b0, b1 = rad(10), rad(305)
    sx, sy = rx2 * math.cos(b0), ry2 * math.sin(b0); ex, ey = rx2 * math.cos(b1), ry2 * math.sin(b1)
    tx, ty = -rx2 * math.sin(b1), ry2 * math.cos(b1)
    def rot(x, y, a=-24): c, s_ = math.cos(rad(a)), math.sin(rad(a)); return x * c - y * s_, x * s_ + y * c
    p0 = rot(sx, sy); p1 = rot(ex, ey); td = rot(tx, ty)
    orb2 = f'<g transform="translate(50,50)">' + S(f'M{n2(p0[0])},{n2(p0[1])} A{rx2},{ry2} -24 1 1 {n2(p1[0])},{n2(p1[1])}', P['ac'], 10) + chev(p1, td, P['ac'], 10, 16, 12) + '</g>'
    return orb + s, orb2 + g
