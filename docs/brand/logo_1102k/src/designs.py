from lib import *

PALS = {
 'candy': dict(bg='#FFF7E8', fg='#1F2A44', c1='#E8590C', c2='#2B6BF3', c3='#0A8CA3', up='#E8590C', dn='#0A8CA3', mute='#E2D6BF', name='陽光糖果'),
 'gold':  dict(bg='#0F1B33', fg='#F4EFE3', c1='#D9A441', c2='#5B7FC4', c3='#8FA3C8', up='#E5534B', dn='#3DB88A', mute='#24365C', name='墨藍＋金'),
 'rk':    dict(bg='#FFFFFF', fg='#111111', c1='#D62839', c2='#8C8C8C', c3='#C9C6BF', up='#D62839', dn='#111111', mute='#E4E2DC', name='白黑＋台股紅'),
 'teal':  dict(bg='#0B2545', fg='#E8F1F5', c1='#2EC4B6', c2='#5FA8D3', c3='#1E4D8F', up='#FF6B6B', dn='#2EC4B6', mute='#163A66', name='深藍＋青'),
}
DESIGNS = []
def design(id, name, idea, pal, box=330):
    def deco(fn):
        DESIGNS.append(dict(id=id, name=name, idea=idea, pal=pal, mk=fn, box=box)); return fn
    return deco

def T(inner, x=0, y=0, s=1): return f'<g transform="translate({n2(x)},{n2(y)}) scale({s})">{inner}</g>'
def PS(d, c, sw, extra=''): return f'<path d="{d}" fill="none" stroke="{c}" stroke-width="{n2(sw)}" {extra}/>'
def TRI(x, y, w, h, c, up=True, extra=''):
    pts = f'{x},{y+h} {x+w},{y+h} {x+w/2},{y}' if up else f'{x},{y} {x+w},{y} {x+w/2},{y+h}'
    return f'<polygon points="{pts}" fill="{c}" {extra}/>'
def hair(x1, y1, x2, y2, c, w=1.4, o=1): return f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{c}" stroke-width="{w}" opacity="{o}"/>'

# ---------- 平口幾何字母（高 100，填色，無圓頭）----------
def Lf(c, t=22): return R(0, 0, t, 100, c) + R(0, 100 - t, 62, t, c), 62
def If(c, t=22): return R(0, 0, t, 100, c), t
def Gf(c, t=22, a=42, bar=True):
    r = 50 - t / 2; ex = 50 + r * math.cos(rad(a)); ey = 50 - r * math.sin(rad(a))
    s = PS(f'M{n2(ex)},{n2(ey)} A{n2(r)},{n2(r)} 0 1 0 {n2(50+r)},50', c, t)
    if bar: s += R(52, 50, 48, t * .86, c)
    return s, 100
def Uf(c, t=22, W=76):
    r = (W - t) / 2; cy = 100 - r - t / 2
    return PS(f'M{n2(t/2)},0 V{n2(cy)} A{n2(r)},{n2(r)} 0 0 0 {n2(W-t/2)},{n2(cy)} V0', c, t), W
LET = dict(L=Lf, I=If, G=Gf, U=Uf)
def row(cols, gap=26, t=22, x0=0):
    s = ''; x = x0; xs = []
    for ch, c in zip('LIGU', cols):
        a, w = LET[ch](c, t); s += T(a, x); xs.append((x, w)); x += w + gap
    return s, xs, x - gap

# ================= K01 K 線圖網格 2×2＋均線切過（糖果）
@design('K01', 'K 線網格＋均線切過', 'LIGU 各佔 K 線圖網格的一格，指數刻度在左緣；一條橘色均線從左下穿過四個字母的前面，切過 L、I、G、U（均線＋網格＋刻度＋高亮區塊）。', 'candy', 350)
def k01(P):
    fg, bg = P['fg'], P['bg']
    def grid(w, h):
        s = ''
        for x in range(0, w + 1, 30):
            mj = x % 120 == 0; s += hair(x, 0, x, h, fg, 2.4 if mj else 1.2, .5 if mj else .2)
        for y in range(0, h + 1, 30):
            mj = y % 120 == 0; s += hair(0, y, w, y, fg, 2.4 if mj else 1.2, .5 if mj else .2)
            s += hair(-(22 if mj else 12), y, 0, y, fg, 2.6)
        return s
    def put(ch, col, cx, cy):
        a, w = LET[ch](col, 30); sc = .8
        return T(a, cx + (120 - w * sc) / 2, cy + (120 - 80) / 2, sc)
    def ma(d, ex, ey):
        return PS(d, bg, 14, 'stroke-linecap="round"') + PS(d, P['c1'], 6, 'stroke-linecap="round"') + C(ex, ey, 13, bg) + C(ex, ey, 8, P['c1'])
    av = R(120, 0, 120, 120, P['c1'], 0, 'opacity=".15"') + R(0, 120, 120, 120, P['c2'], 0, 'opacity=".15"') + grid(240, 240)
    for ch, cx, cy, col in [('L', 0, 0, fg), ('I', 120, 0, fg), ('G', 0, 120, fg), ('U', 120, 120, fg)]: av += put(ch, col, cx, cy)
    av += ma('M-22,206 C 40,216 76,150 126,134 S 196,88 240,34', 240, 34)
    wd = R(120, 0, 120, 120, P['c1'], 0, 'opacity=".15"') + R(240, 0, 120, 120, P['c2'], 0, 'opacity=".15"') + grid(480, 120)
    for i, ch in enumerate('LIGU'): wd += put(ch, fg, i * 120, 0)
    wd += ma('M-22,104 C 40,112 90,72 160,78 S 280,58 340,50 S 450,24 480,22', 480, 22)
    return wd, av

# ================= K02 重疊透明色塊（墨藍＋金）
@design('K02', '重疊透明色塊', '四個字母做成大幅半透明色塊、彼此重疊（螢幕混色），I 是一根穿過全幅的 K 棒（實體＋影線），疊合處浮出新的明暗塊面（K 棒＋色塊疊層）。', 'gold', 330)
def k02(P):
    fg, c1, c2, c3, up = P['fg'], P['c1'], P['c2'], P['c3'], P['up']
    bl = 'style="mix-blend-mode:screen"'
    def lay(a, o): return f'<g opacity="{o}" {bl}>{a}</g>'
    L1, _ = Lf(c1, 30); G1, _ = Gf('#4F78D4', 30); U1, _ = Uf(c3, 30)
    av = lay(T(L1, 6, 6, 1.5), .95) + lay(T(G1, 4, 104, 1.3), .9) + lay(T(U1, 112, 112, 1.3), .85)
    av += R(112, 26, 34, 96, up, 0, 'opacity=".95"') + R(127, 0, 4, 236, fg, 0, 'opacity=".95"')
    s = ''
    for ch, col, x, t, o in [('L', c1, 0, 30, .95), ('G', '#4F78D4', 112, 30, .9), ('U', c3, 236, 30, .85)]:
        a, w = LET[ch](col, t); s += lay(T(a, x, 0), o)
    s += R(66, 12, 32, 76, up, 0, 'opacity=".95"') + R(80, -14, 4, 128, fg, 0, 'opacity=".95"')
    return s, av

# ================= K03 瑞士：紅 G 圓＋▲＋刻度尺（白黑紅）
@design('K03', '瑞士格線：紅 G＋▲＋刻度尺', '黑字 L、I、U 配一個正紅粗圓 G；U 的內凹空間（負空間）裡長出一個紅色 ▲（漲），字下方是指數刻度尺，頭像是 2×2 瑞士格，G 格滿版紅、U 格黑底浮出 ▲（▲▼＋刻度＋圓）。', 'rk', 320)
def k03(P):
    fg, bg, red = P['fg'], P['bg'], P['c1']
    t = 24; s = ''; x = 0
    a, w = Lf(fg, t); s += T(a, x); x += w + 30
    a, w = If(fg, t); s += T(a, x); x += w + 30
    a, w = Gf(red, t, 40); s += T(a, x); x += w + 30
    a, w = Uf(fg, t, 78); s += T(a, x); ux = x; s += TRI(ux + 27, 36, 24, 34, red); x += w
    ry = 124
    for i in range(0, int(x) + 1, 6):
        s += hair(i, ry, i, ry + (13 if i % 30 == 0 else 6), fg, 1.8)
    s += hair(0, ry, x, ry, fg, 2) + TRI(x - 9, ry + 18, 18, 14, fg, False)
    # 頭像 2×2
    av = R(0, 0, 240, 240, bg) + R(120, 120, 120, 120, fg) + R(0, 120, 120, 120, red)
    sc = .64
    def cellp(a, w, cx, cy): return T(a, cx + (120 - w * sc) / 2, cy + (120 - 64) / 2, sc)
    a, w = Lf(fg, t); av += cellp(a, w, 0, 0)
    a, w = If(fg, t); av += cellp(a, w, 120, 0)
    a, w = Gf(bg, t, 40); av += cellp(a, w, 0, 120)
    a, w = Uf(bg, t, 78); av += cellp(a, w, 120, 120)
    ux0 = 120 + (120 - 78 * sc) / 2; av += TRI(ux0 + 27 * sc, 120 + 28 + 36 * sc, 24 * sc, 34 * sc, red)
    av += hair(120, 0, 120, 240, fg, 2.2) + hair(0, 120, 240, 120, fg, 2.2) + PS('M1,1 H239 V239 H1 Z', fg, 2.4)
    for i in range(0, 241, 12): av += hair(i, 240, i, 240 - (10 if i % 60 == 0 else 5), bg, 1.6) if False else ''
    return s, av

# ================= K04 走勢線穿進穿出（深藍＋青）
def weave(P, items, path, tail=None):
    """items: [(builder_result_svg, front?)]；先畫後層字母→走勢線(含底色描邊)→前層字母"""
    bg, c1 = P['bg'], P['c1']
    back = ''.join(a for a, f in items if not f); front = ''.join(a for a, f in items if f)
    line = PS(path, bg, 20, 'stroke-linejoin="round" stroke-linecap="round"') + PS(path, c1, 9, 'stroke-linejoin="round" stroke-linecap="round"')
    return back + line + (tail or '') + front

@design('K04', '走勢線前後穿插', '一條青色走勢折線從左下出發，在 L 與 G 的「前面」切過、鑽到 I 與 U 的「後面」，有真正的前後疊層（字母被線切出缺口），尾端變成資金流向箭頭（走勢線＋箭頭）。', 'teal', 350)
def k04(P):
    fg, c1, bg = P['fg'], P['c1'], P['bg']; t = 24
    xs = {}; x = 0; blds = {}
    for ch in 'LIGU':
        a, w = LET[ch](fg, t if ch != 'U' else t); blds[ch] = (a, x, w); x += w + 24
    path = 'M-28,112 L26,90 L60,100 L98,46 L140,76 L196,30 L262,56 L332,6'
    tail = f'<polygon points="322,-10 352,-2 336,22" fill="{c1}"/>'
    items = [(T(blds[ch][0], blds[ch][1]), ch in 'IU') for ch in 'LIGU']
    word = weave(P, items, path, tail)
    # 頭像 2×2
    sc = .98; cells = {'L': (6, 6), 'I': (138, 6), 'G': (6, 128), 'U': (130, 128)}
    its = []
    for ch in 'LIGU':
        a, w = LET[ch](fg, t); cx, cy = cells[ch]; its.append((T(a, cx + (100 - w * sc) / 2 + 4, cy + 4, sc), ch in 'IU'))
    path2 = 'M-20,222 L40,178 L86,198 L134,112 L176,136 L240,44'
    tail2 = f'<polygon points="226,36 258,32 246,64" fill="{c1}"/>'
    av = weave(P, its, path2, tail2)
    return word, av

# ================= K05 圓餅 G＋K 棒 I＋量柱 L＋凹谷 U（墨藍＋金）
def pie_g(P, t=24):
    cx = cy = 50; ro, ri = 50, 50 - t
    def sec(a0, a1, col, off=0):
        am = rad((a0 + a1) / 2); ox, oy = off * math.cos(am), off * math.sin(am)
        p = lambda r, a: (cx + ox + r * math.cos(rad(a)), cy + oy + r * math.sin(rad(a)))
        x0, y0 = p(ro, a0); x1, y1 = p(ro, a1); x2, y2 = p(ri, a1); x3, y3 = p(ri, a0)
        lg = 1 if a1 - a0 > 180 else 0
        return Pth(f'M{n2(x0)},{n2(y0)} A{ro},{ro} 0 {lg} 1 {n2(x1)},{n2(y1)} L{n2(x2)},{n2(y2)} A{ri},{ri} 0 {lg} 0 {n2(x3)},{n2(y3)} Z', col)
    s = sec(-4, 104, P['c1'], 7) + sec(108, 208, P['fg']) + sec(212, 312, P['c2'])
    s += R(52, 48, 40, 11, P['c1'])
    return s, 100
def valley(P, w=13, g=8):
    spec = [(0, 64, 4, 52, 'dn'), (36, 88, 46, 78, 'dn'), (62, 100, 74, 92, 'c1'), (36, 88, 46, 78, 'up'), (0, 64, 4, 52, 'up')]
    s = ''
    for i, (w0, w1, b0, b1, ck) in enumerate(spec):
        x = i * (w + g); col = P[ck]
        s += R(x + w / 2 - 1.5, w0, 3, w1 - w0, col) + R(x, b0, w, b1 - b0, col)
    return s, 4 * (w + g) + w
@design('K05', '圓餅 G＋K 棒 I＋量柱 L＋凹谷 U', 'G 切成三塊圓餅、其中一塊被推出（輪動熱點）；I 是一根紅 K 棒；L 的橫筆換成由低到高的四根成交量柱；U 由五根 K 棒排成凹谷（圓餅＋K 棒＋量柱）。', 'gold', 350)
def k05(P):
    def Lv():
        s = R(0, 0, 20, 100, P['fg'])
        for i, h in enumerate([14, 24, 36, 52]): s += R(30 + i * 17, 100 - h, 12, h, P['c1'], 0, f'opacity="{.55+i*.15:.2f}"')
        return s, 96
    def Ic(): return R(15, 0, 3, 100, P['fg']) + R(4, 22, 26, 54, P['up']), 34
    parts = [Lv(), Ic(), pie_g(P), valley(P)]
    s = ''; x = 0; xs = []
    for a, w in parts: s += T(a, x); xs.append(x); x += w + 34
    av = ''
    for i, (a, w) in enumerate(parts):
        cx = (i % 2) * 125; cy = (i // 2) * 125; av += T(a, cx + (110 - w * .98) / 2, cy + 2, .98)
    return s, av

# ================= K06 負空間 ▲▼（白黑紅 反白）
@design('K06', '負空間 ▲▼ 黑塊反白', '黑色滿版塊面上，LIGU 以反白鏤空；U 的內凹空間浮出紅色 ▲（漲）、G 的缺口裡嵌著一個 ▼（跌），塊面底緣是由低到高的鏤空成交量柱（▲▼＋量柱＋負空間）。', 'rk', 330)
def k06(P):
    fg, bg, red, dn = P['fg'], P['bg'], P['c1'], P['c2']
    t = 22
    def letters(x0, sc):
        s = ''; x = x0; res = {}
        for ch in 'LIGU':
            a, w = LET[ch](bg, t) if ch != 'U' else Uf(bg, t, 78); s += T(a, x, 0, sc); res[ch] = (x, w); x += (w + 28) * sc
        return s, res, x - 28 * sc
    s, res, xe = letters(30, 1)
    W = xe + 30; H = 190
    inner = R(0, 0, W, H, fg)
    inner += T(s, 0, 28)
    ux = res['U'][0]; gx = res['G'][0]
    inner += TRI(ux + 27, 28 + 38, 24, 32, red) + TRI(gx + 70, 28 + 18, 16, 14, bg, False) + TRI(gx + 72, 28 + 20, 12, 10, P['c2'], False)
    for i, h in enumerate([5, 8, 6, 12, 10, 16, 14, 20, 18, 24, 22, 28]):
        bw = (W - 60) / 12
        inner += R(30 + i * bw + 2, H - 14 - h, bw - 4, h, bg)
    # 頭像
    sc = .7; cell = 120
    av = R(0, 0, 240, 240, fg)
    pos = {'L': (0, 0), 'I': (120, 0), 'G': (0, 120), 'U': (120, 120)}
    for ch, (cx, cy) in pos.items():
        a, w = LET[ch](bg, t) if ch != 'U' else Uf(bg, t, 78)
        px = cx + (120 - w * sc) / 2; py = cy + 12
        av += T(a, px, py, sc)
        if ch == 'U': av += TRI(px + 27 * sc, py + 38 * sc, 24 * sc, 32 * sc, red)
        if ch == 'G': av += TRI(px + 70 * sc, py + 20 * sc, 12, 10, P['c2'], False)
    for i, h in enumerate([4, 7, 6, 10, 9, 14, 13, 18]):
        av += R(18 + i * 27.5, 232 - h, 20, h, bg)
    return inner, av

# ================= K07 輪動羅盤／跳躍弧（糖果）
@design('K07', '輪動羅盤', '四個字母站在圓環的上／右／下／左，環被切成四段弧、每段帶箭頭，藍橘交替追著下一個字母跑（資金輪動）；圓心一根小 K 棒；橫式是四條跳躍弧在字母之間一格一格跳（輪動弧＋資金箭頭＋K 棒）。', 'candy', 350)
def k07(P):
    fg, c1, c2 = P['fg'], P['c1'], P['c2']; t = 24
    cx = cy = 120; R0 = 88
    av = ''
    cols = [c2, c1, c2, c1]
    for i in range(4):
        a0 = -90 + i * 90 + 25; a1 = a0 + 40
        p = lambda a: (cx + R0 * math.cos(rad(a)), cy + R0 * math.sin(rad(a)))
        x0, y0 = p(a0); x1, y1 = p(a1)
        av += PS(f'M{n2(x0)},{n2(y0)} A{R0},{R0} 0 0 1 {n2(x1)},{n2(y1)}', cols[i], 15)
        tx, ty = -math.sin(rad(a1)), math.cos(rad(a1)); nx, ny = -ty, tx
        tip = (x1 + tx * 22, y1 + ty * 22)
        av += f'<polygon points="{n2(x1+nx*14)},{n2(y1+ny*14)} {n2(tip[0])},{n2(tip[1])} {n2(x1-nx*14)},{n2(y1-ny*14)}" fill="{cols[i]}"/>'
    sc = .62
    for ch, ang in zip('LIGU', [-90, 0, 90, 180]):
        a, w = LET[ch](fg, t) if ch != 'U' else Uf(fg, t, 78)
        px = cx + R0 * math.cos(rad(ang)) - w * sc / 2; py = cy + R0 * math.sin(rad(ang)) - 31
        av += R(px - 8, py - 6, w * sc + 16, 74, P['bg']) + T(a, px, py, sc)
    av += R(117, 92, 6, 56, fg) + R(107, 104, 26, 32, P['up'])
    # 橫式
    s = ''; x = 0; cs = []
    for ch in 'LIGU':
        a, w = LET[ch](fg, t) if ch != 'U' else Uf(fg, t, 78); s += T(a, x, 0); cs.append(x + w / 2); x += w + 40
    for i in range(3):
        x0, x1 = cs[i], cs[i + 1]; col = [c2, c1, c2][i]
        s += PS(f'M{n2(x0)},-12 Q{n2((x0+x1)/2)},-70 {n2(x1)},-26', col, 8)
        s += f'<polygon points="{n2(x1-11)},-36 {n2(x1+11)},-36 {n2(x1)},-14" fill="{col}"/>'
    return s, av

# ================= K08 K 棒字體（白黑紅）
BARS = {  # 每欄：[(y0,y1),...]，三欄
 'L': [[(0, 100)], [(80, 100)], [(80, 100)]],
 'I': [[], [(0, 100)], []],
 'G': [[(0, 100)], [(0, 20), (80, 100), (46, 60)], [(46, 100)]],
 'U': [[(0, 100)], [(80, 100)], [(0, 100)]],
}
def barletter(P, ch, red_last=True):
    cw, gap = 20, 4; s = ''; fg, red = P['fg'], P['c1']
    for ci, segs in enumerate(BARS[ch]):
        x = ci * (cw + gap)
        for (y0, y1) in segs:
            col = red if (ch == 'U' and ci == 2) or (ch == 'I' and ci == 1) else fg
            s += R(x, y0, cw, y1 - y0, col)
        if segs:
            top = min(a for a, b in segs); bot = max(b for a, b in segs)
            col = red if (ch == 'I' and ci == 1) else fg
            s += R(x + cw / 2 - 1.2, top - 11, 2.4, 11, col) if ch in 'IGU' and top == 0 else ''
    return s, 3 * cw + 2 * gap
@design('K08', 'K 棒字體', '每個字母由三欄浮動的 K 棒／成交量柱拼成（L 是一根高柱加兩根矮柱、I 是一根紅 K 棒、G 與 U 由高低柱組成），柱子帶影線，背後有指數格線穿過（K 棒＋量柱＋格線＋刻度）。', 'rk', 340)
def k08(P):
    fg = P['fg']; s = ''; x = 0; xs = []
    for ch in 'LIGU':
        a, w = barletter(P, ch); s += T(a, x); xs.append(x); x += w + 30
    W = x - 30
    grid = ''.join(hair(-18, y, W + 10, y, fg, 1.2, .35) for y in (0, 50, 100)) + ''.join(hair(-18 - 0, y, -6, y, fg, 2) for y in (0, 25, 50, 75, 100))
    word = grid + s
    av = ''
    for i, ch in enumerate('LIGU'):
        a, w = barletter(P, ch); cx = (i % 2) * 125 + 8; cy = (i // 2) * 125 + 8
        av += T(a, cx + (110 - w * .95) / 2 - 5, cy + 6, .95)
    av = ''.join(hair(0, y, 240, y, fg, 1.2, .3) for y in (0, 120, 240)) + ''.join(hair(x_, 0, x_, 240, fg, 1.2, .3) for x_ in (0, 120, 240)) + av
    return word, av

# ================= K09 量柱穿過字母、交疊反色（墨藍＋金）
@design('K09', '量柱穿字・交疊反色', '四根由低到高的成交量柱（帶影線，像 K 棒）從字母中間穿過，柱子與字母重疊的地方字母自動反色，筆畫在柱內外交替出現（量柱＋K 棒影線＋交疊反色）。', 'gold', 350)
def k09(P):
    fg, bg, c1 = P['fg'], P['bg'], P['c1']; t = 24
    def build(cells):
        """cells: [(ch, x, barx, barw, bartop)]"""
        s = ''
        for ch, x, bx, bw, bt in cells:
            a, w = LET[ch](fg, t if ch != 'U' else t) if ch != 'U' else Uf(fg, t, 78)
            ai, _ = LET[ch](bg, t) if ch != 'U' else Uf(bg, t, 78)
            cid = f'k9{ch}{int(x)}'
            s += f'<clipPath id="{cid}"><rect x="{n2(bx-x)}" y="{n2(bt)}" width="{n2(bw)}" height="{n2(100-bt+0)}"/></clipPath>'
            s += R(bx, bt, bw, 100 - bt + 0, c1) + R(bx + bw / 2 - 1.5, bt - 16, 3, 16, c1)
            s += T(a, x, 0) + f'<g transform="translate({n2(x)},0)"><g clip-path="url(#{cid})">{ai}</g></g>'
        return s
    cells = [('L', 0, 32, 30, 56), ('I', 92, 100, 28, 38), ('G', 148, 204, 34, 28), ('U', 276, 306, 34, 6)]
    word = build(cells)
    av = ''
    cl = {'L': (0, 0, 34, 40, 50), 'I': (1, 0, 8, 26, 34), 'G': (0, 1, 56, 44, 28), 'U': (1, 1, 44, 36, 6)}
    sc = .8
    for ch, (ci, ri, off, bw, bt) in cl.items():
        cx = ci * 125 + 10; cy = ri * 125 + 22
        a, w = LET[ch](fg, t) if ch != 'U' else Uf(fg, t, 78)
        ai, _ = LET[ch](bg, t) if ch != 'U' else Uf(bg, t, 78)
        px = cx + (110 - w * sc) / 2
        bx = px + off * sc; cid = f'k9a{ch}'
        av += f'<clipPath id="{cid}"><rect x="{off}" y="{n2(bt)}" width="{n2(bw)}" height="{n2(100-bt)}"/></clipPath>'
        av += R(bx, cy + bt * sc, bw * sc, (100 - bt) * sc, c1) + R(bx + bw * sc / 2 - 1.2, cy + bt * sc - 12, 2.4, 12, c1)
        av += T(a, px, cy, sc) + f'<g transform="translate({n2(px)},{n2(cy)}) scale({sc})"><g clip-path="url(#{cid})">{ai}</g></g>'
    return word, av

# ================= K10 圓餅四象限＋輪動環（深藍＋青）
@design('K10', '圓餅四象限＋輪動環', '一個圓餅切成四個象限，各象限一個字母（L／I／G／U），其中一塊被推出（熱點），外圍一圈帶箭頭的輪動弧追著跑（圓餅＋輪動圓弧＋資金箭頭）；橫式是圓餅徽記接字標與上揚刻度線。', 'teal', 340)
def k10(P):
    fg, bg, c1, c2, c3, up = P['fg'], P['bg'], P['c1'], P['c2'], P['c3'], P['up']; t = 24
    def emblem(cx, cy, r, gap=4, pull=9, ring=True):
        s = ''
        cols = [(c3, fg), (c1, bg), (fg, bg), (c2, bg)]  # UL UR LL LR（fill, letter）
        angs = [(180, 270), (270, 360), (90, 180), (0, 90)]
        chs = 'LIUG'; chs = ['L', 'I', 'G', 'U']
        offs = [0, pull, 0, 0]
        for i in range(4):
            a0, a1 = angs[i]; am = rad((a0 + a1) / 2)
            ox = (gap + offs[i]) * math.cos(am); oy = (gap + offs[i]) * math.sin(am)
            p = lambda rr, a: (cx + ox + rr * math.cos(rad(a)), cy + oy + rr * math.sin(rad(a)))
            x0, y0 = p(r, a0); x1, y1 = p(r, a1); xi0, yi0 = p(r * .17, a0); xi1, yi1 = p(r * .17, a1)
            s += Pth(f'M{n2(xi0)},{n2(yi0)} L{n2(x0)},{n2(y0)} A{r},{r} 0 0 1 {n2(x1)},{n2(y1)} L{n2(xi1)},{n2(yi1)} A{n2(r*.17)},{n2(r*.17)} 0 0 0 {n2(xi0)},{n2(yi0)} Z', cols[i][0])
            ch = chs[i]; a, w = LET[ch](cols[i][1], t) if ch != 'U' else Uf(cols[i][1], t, 78)
            sc = r * .0046
            lx = cx + ox + 0.52 * r * math.cos(am) - w * sc / 2; ly = cy + oy + 0.52 * r * math.sin(am) - 50 * sc
            s += T(a, lx, ly, sc)
        if ring:
            rr = r + 20; a0, a1 = 112, 392 - 14
            x0, y0 = cx + rr * math.cos(rad(a0)), cy + rr * math.sin(rad(a0)); x1, y1 = cx + rr * math.cos(rad(a1)), cy + rr * math.sin(rad(a1))
            s += PS(f'M{n2(x0)},{n2(y0)} A{rr},{rr} 0 1 1 {n2(x1)},{n2(y1)}', up, 7)
            tx, ty = -math.sin(rad(a1)), math.cos(rad(a1)); nx, ny = -ty, tx
            s += f'<polygon points="{n2(x1+nx*13)},{n2(y1+ny*13)} {n2(x1+tx*24)},{n2(y1+ty*24)} {n2(x1-nx*13)},{n2(y1-ny*13)}" fill="{up}"/>'
        return s
    av = emblem(124, 124, 98, 4, 11)
    em = emblem(72, 72, 62, 3, 7)
    s = ''; x = 190; xs = []
    for ch in 'LIGU':
        a, w = LET[ch](fg, t) if ch != 'U' else Uf(fg, t, 78); s += T(a, x, 22); x += w + 26
    xe = x - 26
    ly = 148
    s += hair(190, ly, xe, ly, fg, 2) + ''.join(hair(190 + i, ly, 190 + i, ly - (12 if i % 30 == 0 else 6), fg, 1.6) for i in range(0, int(xe - 190) + 1, 6))
    s += TRI(xe - 6, ly - 28, 22, 20, up)
    return em + s, av
