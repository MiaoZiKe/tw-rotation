"""v4 概念插圖（自繪向量）：每張是「兩個意象合一、雙關、比例錯置或負空間」的一個巧思，預設無人。
座標系 888 寬，內容落在 y=88..440 的「內容帶」；scene_svg 依插圖框高度縮放並置中。
通則：描線 --w-line、圓角端點；每張只有一個主光源（--w-lamp）；圖上的比例與數字都由程式依真實數字算出。"""
import math
SW = 3.0
K = 1.0
L = LC = LAMP = FNT = ""
def _styles(sw):
    global SW, L, LC, LAMP, FNT
    SW = sw
    b = 'stroke="var(--w-line)" stroke-width="%.2f" stroke-linecap="round" stroke-linejoin="round"' % sw
    L = 'fill="none" ' + b
    LC = 'fill="var(--w-card)" ' + b
    LAMP = 'fill="var(--w-lamp)" ' + b
    FNT = 'fill="none" ' + b + ' opacity=".5"'

def thick(st, f): return st.replace('stroke-width="%.2f"' % SW, 'stroke-width="%.2f"' % (SW * f))
def R(x, y, w, h, rx=0, st=None): return '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%s" %s/>' % (x, y, w, h, rx, st or L)
def Ln(x1, y1, x2, y2, st=None): return '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s/>' % (x1, y1, x2, y2, st or L)
def C(cx, cy, r, st=None): return '<circle cx="%.1f" cy="%.1f" r="%.1f" %s/>' % (cx, cy, r, st or L)
def P(d, st=None): return '<path d="%s" %s/>' % (d, st or L)
def poly(pts, st=None): return '<polygon points="%s" %s/>' % (' '.join('%.1f,%.1f' % q for q in pts), st or L)
def dash(st, d="10 9"): return st.replace('stroke-linecap', 'stroke-dasharray="%s" stroke-linecap' % d)
def glow(cx, cy, r, op):
    return '<g data-g="1" style="filter:blur(24px)"><circle cx="%d" cy="%d" r="%d" fill="url(#gl)" opacity="%s"/></g>' % (cx, cy, r, op)
def steam(x, y, h=40):
    return P('M%s %s q 7 -%s 0 -%s q -7 -%s 0 -%s' % (x, y, h / 4, h / 2, h / 4, h / 2), L.replace('fill="none"', 'fill="none" opacity=".6"'))
def T(x, y, s, anchor="middle"):
    """圖內文字：有效字級 28px（依縮放補償），顏色走次文字色。"""
    return '<text x="%.1f" y="%.1f" text-anchor="%s" font-size="%.1f" fill="var(--w-sub)" stroke="none" style="letter-spacing:.05em">%s</text>' % (x, y, anchor, 28.0 / K, s)

def bowl_top(x, y, r=15, warm=False):
    return C(x, y, r, LAMP if warm else LC) + C(x, y, r * .62, L)
def chair_top(cx, cy, ang):
    return '<g transform="rotate(%.1f %.1f %.1f)">%s</g>' % (ang, cx, cy, R(cx - 20, cy - 12, 40, 24, 7, LC))

# ---------- 催婚篇 ----------
def q_points():
    """問號的碗：弧 7 顆＋莖 2 顆，縮放 .88（以 (444,240) 為中心）；回傳碗位置與「點」的位置。"""
    pts = []
    for a in (180, 215, 250, 285, 320, 355, 30):
        pts.append((444 + 60 * math.cos(math.radians(a)), 208 + 60 * math.sin(math.radians(a))))
    pts += [(470, 264), (452, 292)]
    s = .88
    pts = [(444 + (x - 444) * s, 246 + (y - 240) * s) for x, y in pts]
    return pts, (444, 246 + (336 - 240) * s)

def sc_qtable(dawn):
    """封面：圓桌從上往下看，碗排成一個問號；問號的「點」是一碗亮著的熱湯。"""
    cx, cy = 444, 274
    o = glow(cx, cy + 56, 150, "var(--w-glow)")
    for k in range(6):
        a = math.radians(30 + 60 * k)
        o += chair_top(cx + 156 * math.cos(a), cy + 156 * math.sin(a), 30 + 60 * k + 90)
    o += C(cx, cy, 130, LC) + C(cx, cy, 118, FNT)
    pts, dot = q_points()
    for (x, y) in pts: o += bowl_top(x, y, 15)
    o += bowl_top(dot[0], dot[1], 15, True) + glow(int(dot[0]), int(dot[1]), 46, ".6")
    o += Ln(dot[0] + 24, dot[1] - 8, dot[0] + 30, dot[1] + 18) + Ln(dot[0] + 31, dot[1] - 8, dot[0] + 37, dot[1] + 18)
    return o

def sc_scale(dawn):
    """長輩問的（一碗熱湯，輕）對上被問的人算的（一疊帳單加圈起來的房租日，重）：天平往帳單那邊沉。"""
    px, py, ang, half = 444, 176, 7.0, 214
    a = math.radians(ang)
    lx, ly = px - half * math.cos(a), py - half * math.sin(a)
    rx, ry = px + half * math.cos(a), py + half * math.sin(a)
    o = glow(int(lx), int(ly) + 100, 110, "var(--w-glow)")
    o += Ln(px, py, px, 424) + R(384, 424, 120, 12, 4, LC)
    o += Ln(lx, ly, rx, ry, thick(L, 1.8)) + C(px, py, 11, LC)
    for (x, y, pw) in ((lx, ly, 84), (rx, ry, 150)):
        o += Ln(x, y, x - pw / 2, y + 96) + Ln(x, y, x + pw / 2, y + 96) + R(x - pw / 2 - 6, y + 96, pw + 12, 8, 3, LC)
    bx, by = lx, ly + 96
    o += P('M%.1f %.1f q 30 44 60 0 Z' % (bx - 30, by - 36), LAMP) + steam(bx - 8, by - 42, 30) + steam(bx + 10, by - 40, 24)
    cxr, cyr = rx, ry + 96
    for i in range(4):
        o += R(cxr - 52 + i * 3, cyr - 20 - i * 18, 104, 18, 2, LC)
    top = cyr - 20 - 4 * 18
    o += R(cxr - 40, top - 72, 80, 70, 3, LC) + Ln(cxr - 30, top - 50, cxr + 30, top - 50, FNT) + Ln(cxr - 20, top - 78, cxr - 20, top - 66) + Ln(cxr + 20, top - 78, cxr + 20, top - 66) + C(cxr + 6, top - 30, 11, L)
    return o

def chair_side(x, base, s, lit=False):
    """側視的椅子：椅背、椅面、四腳；高度 200×s。"""
    H = 200 * s
    o = Ln(x - 38 * s, base - 100 * s, x - 38 * s, base) + Ln(x + 38 * s, base - 100 * s, x + 38 * s, base)
    o += Ln(x - 38 * s, base - 100 * s, x - 46 * s, base - H) + R(x - 56 * s, base - H - 2 * s, 20 * s, 12 * s, 4 * s, LC)
    o += Ln(x - 42 * s, base - 150 * s, x - 36 * s, base - 150 * s) + Ln(x - 40 * s, base - 125 * s, x - 36 * s, base - 125 * s)
    o += R(x - 44 * s, base - 112 * s, 92 * s, 14 * s, 5 * s, LAMP if lit else LC)
    return o

def sc_chairs(dawn):
    """0.695：大人椅高 200，兒童椅只有 200×0.695＝139（比例照數字），空著，坐墊亮著一點燈。"""
    base = 428
    o = glow(700, base - 70, 120, "var(--w-glow)") + Ln(40, base, 848, base)
    for x in (170, 330, 490): o += chair_side(x, base, 1.0)
    o += chair_side(690, base, .695, True)
    top = base - 200
    o += Ln(120, top, 780, top, dash(FNT)) + Ln(760, top + 4, 760, base - 139 - 4, dash(FNT, "5 6"))
    return o

def sc_steamq(dawn):
    """話題先停在這裡：筷子擱在碗上，碗上的熱氣原本要捲成問號，越往上越淡、停在半空。"""
    o = glow(444, 360, 140, "var(--w-glow)") + Ln(40, 424, 848, 424)
    o += R(160, 398, 568, 14, 4, LC) + Ln(200, 412, 200, 424) + Ln(688, 412, 688, 424)
    q = 'M410 196 C410 146 478 146 478 192 C478 226 444 228 444 262'
    o += P(q, dash(thick(L, 1.5), "16 12").replace('fill="none"', 'fill="none" opacity=".85"'))
    o += '<circle cx="444" cy="290" r="7" fill="var(--w-line)" opacity=".7"/>'
    o += P('M384 336 q 60 90 120 0 Z', LC) + P('M384 336 Q 444 346 504 336', LAMP.replace('fill="var(--w-lamp)"', 'fill="var(--w-lamp)" opacity=".85"'))
    o += Ln(402, 300, 520, 346) + Ln(414, 296, 532, 342)
    o += P('M580 398 q 0 -30 24 -30 q 24 0 24 30 Z', LC) + Ln(572, 398, 636, 398)
    return o

def sc_ring(dawn):
    """未來：那個問號收成一圈，六碗匀稱地圍著桌中央一盞小燈。"""
    cx, cy = 444, 274
    o = glow(cx, cy, 170, "var(--w-glow)")
    for k in range(6):
        a = math.radians(30 + 60 * k)
        o += chair_top(cx + 156 * math.cos(a), cy + 156 * math.sin(a), 30 + 60 * k + 90)
    o += C(cx, cy, 130, LC) + C(cx, cy, 118, FNT)
    for k in range(6):
        a = math.radians(60 * k)
        x, y = cx + 84 * math.cos(a), cy + 84 * math.sin(a)
        o += bowl_top(x, y, 17)
    o += C(cx, cy, 26, LAMP) + C(cx, cy, 11, L)
    return o

# ---------- 經濟成長篇 ----------
def tree(x):
    o = ''
    cs = [(x, 186, 54), (x - 50, 214, 42), (x + 50, 214, 42), (x - 28, 152, 38), (x + 30, 154, 38)]
    for cx, cy, r in cs: o += '<circle cx="%d" cy="%d" r="%.1f" fill="var(--w-line)"/>' % (cx, cy, r + SW)
    for cx, cy, r in cs: o += '<circle cx="%d" cy="%d" r="%d" fill="var(--w-card)"/>' % (cx, cy, r)
    return o + Ln(x - 14, 250, x - 14, 372) + Ln(x + 14, 250, x + 14, 372)

def sc_treepot(dawn, reach=False):
    """新聞說經濟成長了：一棵一直長的大樹，旁邊一盆小苗；根沒有伸到那盆（hope 版：根往小盆多伸了一段）。"""
    g = 372
    o = glow(660, 300, 110, "var(--w-glow)")
    o += tree(280) + Ln(40, g, 848, g)
    for d in ('M266 372 C250 396 230 410 196 416', 'M294 372 C310 398 340 410 372 408', 'M282 372 L282 424 M282 396 C270 410 262 420 250 432'): o += P(d)
    if reach:
        o += P('M372 408 C420 410 470 404 520 396', dash(L)) + P('M520 396 C560 392 590 384 608 376', dash(L, "4 8"))
    else:
        o += P('M372 408 C400 410 430 410 452 406', dash(L))
    o += P('M606 372 L614 330 L690 330 L698 372 Z', LC) + R(602, 322, 100, 12, 4, LC)
    o += Ln(652, 322, 652, 288) + P('M652 308 q -26 -4 -32 -26 q 26 -2 32 26', L) + P('M652 296 q 24 -6 30 -28 q -26 0 -30 28', LAMP) + glow(676, 280, 40, ".6")
    if reach: o += P('M652 316 q 22 -2 28 -18 q -22 0 -28 18', L)
    return o

def sc_means(dawn):
    """平均被一根特別高的柱子拉高：九根柱，平均線在中位數柱（亮的那根）之上；比例＝中位數 38,406 ÷ 平均 47,884。"""
    base, M = 404, 110
    rel = [.40, .52, .62, .72, 38406 / 47884, .90, 1.05, 1.35, 0]
    rel[-1] = 9 - sum(rel[:-1])
    o = glow(380, base - 40, 110, "var(--w-glow)") + Ln(70, base, 820, base)
    w, gap, x0 = 56, 22, 100
    for i, r in enumerate(rel):
        x = x0 + i * (w + gap); h = r * M
        o += R(x, base - h, w, h, 3, LAMP if i == 4 else LC)
    o += Ln(80, base - M, 810, base - M, dash(thick(L, 1.2), "14 10"))
    o += T(84, base - M - 12, "平均", "start") + T(x0 + 4 * (w + gap) + w / 2, base + 34, "中位數")
    return o

def sc_jars(dawn):
    """6.17 倍：兩個一樣大的罐子，錢的高度 100％ 對 16.2％（39.7÷244.9），比例由程式算。"""
    base, inner = 392, 200
    ratio = 39.7 / 244.9
    o = glow(640, base - 40, 110, "var(--w-glow)") + Ln(60, base + 8, 830, base + 8)
    for cx, frac, lit in ((250, 1.0, False), (640, ratio, True)):
        o += R(cx - 76, base - inner - 18, 152, inner + 22, 14, LC) + R(cx - 60, base - inner - 36, 120, 18, 5, LC)
        h = inner * frac
        o += '<rect x="%d" y="%.1f" width="136" height="%.1f" rx="6" fill="%s" opacity="%s"/>' % (cx - 68, base - h, h, "var(--w-lamp)" if lit else "var(--w-line)", ".7" if lit else ".35")
        y = base
        while y - 8.1 >= base - h - .01:
            y -= 8.1; o += Ln(cx - 68, y, cx + 68, y, 'fill="none" stroke="var(--w-card)" stroke-width="1.6" opacity=".7"')
    o += T(250, base + 46, "最高 20%") + T(640, base + 46, "最低 20%")
    return o

def sc_slips(dawn):
    """找中位數：九張薪資單排成一列，被抽出來亮著的是正中間（第 5 張）。"""
    base = 392
    o = glow(444, base - 90, 120, "var(--w-glow)") + Ln(60, base, 828, base)
    w, gap, x0 = 66, 20, 84
    for i in range(9):
        x = x0 + i * (w + gap); up = 44 if i == 4 else 0
        o += R(x, base - 150 - up, w, 150, 4, LAMP if i == 4 else LC)
        for j in range(4):
            o += Ln(x + 12, base - 128 - up + j * 20, x + w - 12 - (j % 2) * 14, base - 128 - up + j * 20, FNT)
    mx = x0 + 4 * (w + gap) + w / 2
    o += P('M%.1f %.1f l 14 -22 l 14 22 Z' % (mx - 14, base + 36), L)
    return o

# ---------- 微光篇 ----------
def sc_mailboxes(dawn):
    """封面：一整面信箱，只有一格有信；那格的門開了一道縫，信封透出暖光。"""
    o = R(60, 108, 768, 320, 10, LC)
    cw, ch, gap, x0, y0 = 134, 88, 12, 76, 124
    for r in range(3):
        for c in range(5):
            x, y = x0 + c * (cw + gap), y0 + r * (ch + gap)
            if (r, c) == (1, 2): continue
            o += R(x, y, cw, ch, 6, LC) + Ln(x + 30, y + 30, x + cw - 30, y + 30) + C(x + cw / 2, y + 62, 5, L)
    x, y = x0 + 2 * (cw + gap), y0 + 1 * (ch + gap)
    o += glow(int(x + cw / 2), int(y + ch / 2), 90, ".7")
    o += R(x, y, cw, ch, 6, LAMP) + R(x + 22, y + 22, 90, 50, 4, LC) + P('M%.1f %.1f l 45 28 l 45 -28' % (x + 22, y + 22), L)
    o += poly([(x, y), (x - 26, y + 10), (x - 26, y + ch - 6), (x, y + ch)], LC)
    return o

def sc_windows(dawn):
    """一面公寓牆，102 格＝申請 102 萬戶（一格約 1 萬戶），亮著的 87 格是核准。"""
    cols, rows = 17, 6
    cw, ch, gx, gy = 38, 30, 10, 10
    x0, y0 = (888 - (cols * cw + (cols - 1) * gx)) / 2, 124
    dark = {(i * 37) % 102 for i in range(15)}
    ww = cols * cw + (cols - 1) * gx
    o = R(x0 - 16, y0 - 16, ww + 32, rows * ch + (rows - 1) * gy + 32, 6, LC) + glow(444, y0 + 110, 200, "var(--w-glow)")
    for i in range(102):
        r, c = divmod(i, cols); x, y = x0 + c * (cw + gx), y0 + r * (ch + gy)
        if i in dark: o += R(x, y, cw, ch, 3, L)
        else: o += '<rect x="%.1f" y="%.1f" width="%d" height="%d" rx="3" fill="var(--w-lamp)" opacity=".38"/>' % (x, y, cw, ch)
    yb = y0 + rows * ch + (rows - 1) * gy + 64
    o += T(x0 - 8, yb, "一格約 1 萬戶", "start") + T(x0 + ww + 8, yb, "亮格＝核准", "end")
    return o

def sc_patch(dawn):
    """補貼＝補丁：一張被房租壓得滿滿的帳單，右下角縫了一塊暖色的補丁（只分擔了一小塊）。"""
    x, y, w, h = 230, 108, 400, 300
    o = glow(560, 330, 130, "var(--w-glow)")
    o += P('M%d %d L%d %d L%d %d L%d %d L%d %d Z' % (x, y, x + w - 44, y, x + w, y + 44, x + w, y + h, x, y + h), LC) + P('M%d %d L%d %d L%d %d' % (x + w - 44, y, x + w - 44, y + 44, x + w, y + 44), L)
    o += T(x + 34, y + 54, "房租", "start")
    for j in range(5):
        o += Ln(x + 34, y + 96 + j * 30, x + w - 120, y + 96 + j * 30, FNT) + Ln(x + w - 90, y + 96 + j * 30, x + w - 34, y + 96 + j * 30, FNT)
    px, py, s = x + w - 170, y + h - 140, 124
    o += '<rect x="%d" y="%d" width="%d" height="%d" rx="6" fill="var(--w-lamp)" opacity=".75"/>' % (px, py, s, s)
    o += R(px + 9, py + 9, s - 18, s - 18, 3, dash(thick(L, 1.2), "7 6"))
    return o

def sc_mailbox1(dawn):
    """先存著就好：左邊一張官方公告，右邊一只信箱，箱蓋掀開、裡面亮著，一封信在裡面。"""
    o = glow(560, 280, 150, "var(--w-glow)")
    o += R(90, 150, 190, 230, 6, LC) + R(112, 176, 146, 170, 3, LC) + Ln(128, 206, 242, 206) + Ln(128, 230, 220, 230, FNT) + Ln(128, 252, 232, 252, FNT) + Ln(128, 274, 206, 274, FNT)
    o += R(160, 164, 36, 16, 2, FNT)
    o += Ln(60, 424, 828, 424) + Ln(560, 376, 560, 424) + R(520, 420, 80, 8, 3, LC)
    o += R(440, 236, 240, 140, 12, LC) + R(458, 250, 204, 36, 4, LAMP)
    o += P('M440 236 L470 190 L650 190 L680 236', LC)
    o += R(498, 252, 100, 60, 4, LC) + P('M498 252 l 50 34 l 50 -34', L)
    return o

def sc_price(dawn):
    """房價：遠處的樓頂連起來，剛好是一條往上爬的房價折線；近處小燈下的存款簿，是一條幾乎平的線。"""
    o = glow(130, 380, 140, "var(--w-glow)") + Ln(40, 428, 848, 428)
    xs = [420 + i * 52 for i in range(8)]
    hs = [40, 58, 72, 96, 130, 168, 214, 262]
    pts = []
    for x, h in zip(xs, hs):
        o += R(x - 22, 428 - h, 44, h, 0, LC)
        for yy in range(int(428 - h + 14), 418, 22):
            if (x + yy) % 3 == 0: o += '<rect x="%d" y="%d" width="8" height="10" fill="var(--w-lamp)" opacity=".18"/>' % (x - 4, yy)
        pts.append((x, 428 - h))
    o += P('M' + ' L'.join('%d %d' % q for q in pts), dash(thick(L, 1.3), "12 8"))
    for q in pts: o += C(q[0], q[1], 6, LC)
    o += R(150, 296, 210, 132, 6, LC) + Ln(172, 316, 172, 408, FNT) + Ln(172, 408, 340, 408, FNT) + Ln(172, 392, 340, 386, thick(L, 1.3))
    o += R(70, 392, 34, 36, 3, LC) + P('M70 392 L58 372 L116 372 L104 392 Z', LAMP) + glow(87, 380, 50, ".6")
    return o

SCENES = {"qtable": sc_qtable, "scale": sc_scale, "chairs": sc_chairs, "steamq": sc_steamq, "ring": sc_ring, "treepot": sc_treepot,
          "treepot2": lambda d: sc_treepot(d, True), "means": sc_means, "jars": sc_jars, "slips": sc_slips,
          "mailboxes": sc_mailboxes, "windows": sc_windows, "patch": sc_patch, "mailbox1": sc_mailbox1, "price": sc_price}

ZMAX = {"qtable": 1.3, "ring": 1.2, "chairs": 1.2, "steamq": 1.2, "scale": 1.3, "jars": 1.2, "patch": 1.3, "mailbox1": 1.0}
def scene_svg(name, ih, dawn=False):
    global K
    k = min(ZMAX.get(name, 1.0), ih / 360.0); K = k
    _styles(3.0 / k)
    tx = (888 - 888 * k) / 2; ty = (ih - 8) - 440 * k
    inner = SCENES[name](dawn)
    defs = ('<radialGradient id="gl"><stop offset="0" stop-color="var(--w-lamp)" stop-opacity="1"/><stop offset="1" stop-color="var(--w-lamp)" stop-opacity="0"/></radialGradient>')
    return ('<div data-o="illus" class="illus" style="top:176px;width:888px;height:%dpx"><svg width="888" height="%d" viewBox="0 0 888 %d" '
            'xmlns="http://www.w3.org/2000/svg"><defs>%s</defs><g transform="translate(%.2f %.2f) scale(%.4f)">%s</g></svg></div>' % (ih, ih, ih, defs, tx, ty, k, inner))
