"""談晴說礙 v3 插圖（自繪向量，座標 888×764）。
承接 gen2000 v4／v5 的「細線＋單一暖光」語言：線寬降到 3px（v5 為 5.5px）、輔助線 1.2～1.8px 半透明，
面色只做三階輕填（凹 --w-dark／主 --w-face／凸 --w-face3），暖光只有一個光點（--w-lamp，含雙層光暈）。
雲＝礙（雲灰細線、多層），光＝晴（唯一暖色）。所有顏色走 CSS 變數，夜版／晝版換變數即可。"""
import math, random

SW = 3.0                         # 主線寬（v5 是 5.5）
LN = "var(--w-line)"
_uid = [0]

def at(fill="none", w=SW, stroke=LN, op=None, dash=None, extra=""):
    s = 'fill="%s" stroke="%s" stroke-width="%s" stroke-linecap="round" stroke-linejoin="round"' % (fill, stroke, w)
    if op is not None: s += ' opacity="%s"' % op
    if dash: s += ' stroke-dasharray="%s"' % dash
    return s + " " + extra

F1 = at("var(--w-face)"); F3 = at("var(--w-face3)"); DK = at("var(--w-dark)"); LP = at("var(--w-lamp)", SW, "var(--w-lamp)")
LPo = at("var(--w-lamp)")                # 暖光面但線用雲灰
NO = at("none")
THIN = at("none", 1.8, op=.55); HAIR = at("none", 1.2, op=.4); MID = at("none", 2.2, op=.7)

def R(x, y, w, h, rx=0, st=F1): return '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%s" %s/>' % (x, y, w, h, rx, st)
def Ln(x1, y1, x2, y2, st=NO): return '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s/>' % (x1, y1, x2, y2, st)
def C(cx, cy, r, st=F1): return '<circle cx="%.1f" cy="%.1f" r="%.1f" %s/>' % (cx, cy, r, st)
def E(cx, cy, rx, ry, st=F1): return '<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" %s/>' % (cx, cy, rx, ry, st)
def P(d, st=NO): return '<path d="%s" %s/>' % (d, st)
def poly(pts, st=F1): return '<polygon points="%s" %s/>' % (' '.join('%.1f,%.1f' % q for q in pts), st)
def G(inner, extra=""): return '<g %s>%s</g>' % (extra, inner)

def clip_rect(x, y, w, h, inner):
    _uid[0] += 1; i = "k%d" % _uid[0]
    return '<clipPath id="%s"><rect x="%.1f" y="%.1f" width="%.1f" height="%.1f"/></clipPath><g clip-path="url(#%s)">%s</g>' % (i, x, y, w, h, i, inner)

def hatch(x, y, w, h, gap=11, st=None):
    """斜線陰影（45°），裁在矩形內。"""
    st = st or at("none", 1.2, op=.32)
    ls = ''.join(Ln(x + o, y, x + o - h, y + h, st) for o in range(0, int(w + h), gap))
    return clip_rect(x, y, w, h, ls)

def glow(cx, cy, r, strength=1.0):
    """雙層光暈：外層寬而淡、內層緊而亮（data-g 供檢查用）。"""
    return ('<g data-g="1" style="filter:blur(38px)"><circle cx="%d" cy="%d" r="%d" fill="url(#gl)" style="opacity:calc(var(--w-glow) * %.2f)"/></g>'
            '<g data-g="1" style="filter:blur(16px)"><circle cx="%d" cy="%d" r="%d" fill="url(#gl)" style="opacity:calc(var(--w-glow2) * %.2f)"/></g>'
            % (cx, cy, r, strength, cx, cy, r * .42, strength))

def halo_rings(cx, cy, r, n=2):
    """光點外的細圈（一圈實、一圈虛），不是第二個光點。"""
    o = C(cx, cy, r + 14, at("none", 1.6, "var(--w-lamp)", op=.8))
    if n > 1: o += C(cx, cy, r + 30, at("none", 1.3, "var(--w-lamp)", op=.5, dash="3 9"))
    return o

def rays(cx, cy, r1, r2, a0, a1, n, st=None):
    st = st or at("none", 1.3, "var(--w-lamp)", op=.45)
    o = ''
    for i in range(n):
        a = math.radians(a0 + (a1 - a0) * i / max(1, n - 1))
        o += Ln(cx + r1 * math.cos(a), cy + r1 * math.sin(a), cx + r2 * math.cos(a), cy + r2 * math.sin(a), st)
    return o

def cloud(cx, base, w, h, seed=1, fill="var(--w-face)", op=1.0, detail=True, free=False):
    """多層雲：圓疊成輪廓（外線＋內填）、平底；內有 2～3 條弧形細紋、底部斜線陰影、底下兩條拖尾。"""
    rnd = random.Random(seed)
    n = max(3, round(w / (h * .62)))
    x0, x1 = cx - w / 2, cx + w / 2
    assert free or (x0 >= 12 and x1 <= 876), ('雲超出插圖框', cx, w)
    cs = []
    for i in range(n):
        t = (i + .5) / n
        r = h * (.30 + .26 * math.sin(math.pi * t)) * (.92 + .16 * rnd.random())
        x = x0 + h * .28 + (w - h * .56) * t
        cs.append((x, base - r * .72, r))
    _uid[0] += 1; ck = "c%d" % _uid[0]
    body = ''.join('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s"/>' % (x, y, r + SW * .55, LN) for x, y, r in cs)
    body += ''.join('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s"/>' % (x, y, r, fill) for x, y, r in cs)
    if detail:
        for k, (x, y, r) in enumerate(cs):
            if k % 2 == 0 or r > h * .5:
                a0, a1 = math.radians(205), math.radians(285)
                rr = r * .7
                body += '<path d="M%.1f %.1f A%.1f %.1f 0 0 1 %.1f %.1f" %s/>' % (x + rr * math.cos(a0), y + rr * math.sin(a0), rr, rr, x + rr * math.cos(a1), y + rr * math.sin(a1), at("none", 1.5, op=.5))
        body += Ln(x0 + w * .12, base - 12, x0 + w * .62, base - 12, at("none", 1.3, op=.4))
        body += hatch(x0 + w * .16, base - h * .26, w * .68, h * .26, 9, at("none", 1.1, op=.28))
    clipped = clip_rect(x0 - 10, base - h * 2, w + 20, h * 2, body)
    o = '<g opacity="%s">%s%s' % (op, clipped, Ln(x0 + h * .06, base, x1 - h * .06, base, at("none", SW)))
    if detail:
        o += Ln(x0 + w * .2, base + 13, x0 + w * .5, base + 13, at("none", 1.4, op=.45)) + Ln(x0 + w * .55, base + 24, x0 + w * .82, base + 24, at("none", 1.2, op=.35))
    return o + '</g>'

def wisp(x, y, w, op=.5, amp=9):
    return P('M%.1f %.1f q %.1f %.1f %.1f 0 t %.1f 0' % (x, y, w / 4, -amp, w / 2, w / 2), at("none", 1.5, op=op))

def steam(x, y, h=70, op=.7):
    return P('M%s %s q 12 -%s 0 -%s q -12 -%s 0 -%s' % (x, y, h / 4, h / 2, h / 4, h / 2), at("none", 2.4, op=op))

def bowl_top(x, y, r, warm=False):
    o = C(x, y, r, LP if warm else F3) if warm else C(x, y, r, F3)
    o += C(x, y, r * .66, at("none", 1.8, op=.7)) + C(x, y, r * .3, at("none", 1.3, op=.45))
    a0, a1 = math.radians(200), math.radians(260)
    rr = r * .82
    o += P('M%.1f %.1f A%.1f %.1f 0 0 1 %.1f %.1f' % (x + rr * math.cos(a0), y + rr * math.sin(a0), rr, rr, x + rr * math.cos(a1), y + rr * math.sin(a1)), at("none", 1.6, op=.6))
    return o

def chair_top(cx, cy, ang):
    inner = R(cx - 46, cy - 27, 92, 54, 15, F3) + R(cx - 36, cy - 18, 72, 36, 10, at("none", 1.4, op=.5)) + Ln(cx - 14, cy, cx + 14, cy, at("none", 1.4, op=.4))
    return '<g transform="rotate(%.1f %.1f %.1f)">%s</g>' % (ang, cx, cy, inner)

def table(cx, cy, R_=262):
    o = ''
    for k in range(6):
        a = math.radians(30 + 60 * k)
        o += chair_top(cx + 322 * math.cos(a), cy + 322 * math.sin(a), 30 + 60 * k + 90)
    o += C(cx, cy, R_ + 12, at("none", 1.4, op=.35)) + C(cx, cy, R_, F1) + C(cx, cy, R_ - 24, at("none", 1.8, op=.5))
    for rr, a0, a1 in ((R_ - 62, 190, 330), (R_ - 98, 20, 150), (R_ - 132, 220, 300), (R_ - 44, 60, 120)):    # 桌面木紋
        p0, p1 = math.radians(a0), math.radians(a1)
        o += P('M%.1f %.1f A%d %d 0 0 1 %.1f %.1f' % (cx + rr * math.cos(p0), cy + rr * math.sin(p0), rr, rr, cx + rr * math.cos(p1), cy + rr * math.sin(p1)), at("none", 1.3, op=.28))
    return o

# ───────────────────────── 長輩的期待：4 張（v5 構圖，細線＋細節）─────────────────────────
def sc_qtable():
    cx, cy = 444, 386
    pts = []
    for a in (180, 215, 250, 285, 320, 355, 30):
        pts.append((444 + 60 * math.cos(math.radians(a)), 208 + 60 * math.sin(math.radians(a))))
    pts += [(470, 264), (452, 292)]
    f = lambda x, y: (cx + (444 + (x - 444) * .88 - 444) * 1.9, cy + 30 + (246 + (y - 240) * .88 - 274) * 1.9)
    o = glow(cx, 520, 185) + table(cx, cy)
    for (x, y) in pts: o += bowl_top(*f(x, y), 29)
    dx, dy = cx, cy + 30 + (246 + 96 * .88 - 274) * 1.9
    o += R(dx - 62, dy - 44, 124, 88, 22, at("none", 1.5, op=.5, dash="5 7"))      # 墊在熱湯下的杯墊（虛線）
    o += bowl_top(dx, dy, 29, True) + halo_rings(dx, dy, 29)
    o += Ln(dx + 54, dy - 20, dx + 64, dy + 30, at("none", 3.4)) + Ln(dx + 70, dy - 20, dx + 80, dy + 30, at("none", 3.4))
    o += Ln(dx + 52, dy + 38, dx + 94, dy + 34, at("none", 1.4, op=.5))
    return o

def sc_ring():
    cx, cy = 444, 386
    o = glow(cx, cy, 250) + table(cx, cy)
    for k in range(12):                                                         # 燈到碗之間的細光線
        a = math.radians(30 * k + 15)
        o += Ln(cx + 74 * math.cos(a), cy + 74 * math.sin(a), cx + 112 * math.cos(a), cy + 112 * math.sin(a), at("none", 1.3, "var(--w-lamp)", op=.5))
    o += C(cx, cy, 118, at("none", 1.4, op=.35, dash="4 9"))
    for k in range(6):
        a = math.radians(60 * k)
        o += bowl_top(cx + 168 * math.cos(a), cy + 168 * math.sin(a), 42)
    return o + C(cx, cy, 58, LP) + halo_rings(cx, cy, 58, 1) + C(cx, cy, 24, at("none", 2, op=.7, stroke="var(--w-dark)"))

def sc_scale():
    px, py, half, ang = 444, 170, 285, math.radians(6)
    lx, ly = px - half * math.cos(ang), py - half * math.sin(ang)
    rx, ry = px + half * math.cos(ang), py + half * math.sin(ang)
    o = glow(int(lx), int(ly) + 190, 170)
    o += cloud(190, 98, 250, 78, 7, "var(--w-dark)", .8) + cloud(150, 722, 220, 60, 11, "var(--w-dark)", .8) + cloud(760, 724, 230, 62, 12, "var(--w-dark)", .8)     # 遠處的雲（礙）
    # 底座：三階＋地面陰影
    o += hatch(330, 718, 230, 26, 10)
    o += poly([(300, 716), (588, 716), (556, 690), (332, 690)], F1) + poly([(340, 690), (548, 690), (524, 668), (364, 668)], F3)
    o += Ln(300, 724, 588, 724, THIN)
    # 立柱：兩條縱向細紋、柱頭
    o += R(426, py, 36, 520, 6, F1) + Ln(437, py + 20, 437, 660, HAIR) + Ln(452, py + 20, 452, 660, HAIR)
    o += R(414, 640, 60, 28, 6, F3) + R(418, py + 22, 52, 14, 5, F3)
    nx, ny = -math.sin(ang) * 13, math.cos(ang) * 13
    o += poly([(lx - nx, ly - ny), (rx - nx, ry - ny), (rx + nx, ry + ny), (lx + nx, ly + ny)], F3)
    for k in range(1, 12):                                                      # 橫桿刻度
        t = k / 12
        x = lx + (rx - lx) * t; y = ly + (ry - ly) * t
        o += Ln(x, y - 5, x, y + 5, at("none", 1.3, op=.5))
    o += C(px, py, 28, F3) + C(px, py, 11, at("none", 1.8, op=.7))
    for (x, y, pw) in ((lx, ly, 200), (rx, ry, 260)):
        o += C(x, y, 8, F1)
        o += Ln(x, y, x - pw / 2 + 10, y + 190) + Ln(x, y, x + pw / 2 - 10, y + 190) + Ln(x, y, x, y + 190, at("none", 1.3, op=.35, dash="4 8"))
        o += R(x - pw / 2, y + 190, pw, 14, 6, F3) + Ln(x - pw / 2 + 12, y + 208, x + pw / 2 - 12, y + 208, at("none", 1.3, op=.4))
    py_l = ly + 190
    o += P('M%.1f %.1f H%.1f C%.1f %.1f %.1f %.1f %.1f %.1f C%.1f %.1f %.1f %.1f %.1f %.1f Z' % (lx - 72, py_l - 66, lx + 72, lx + 72, py_l - 10, lx + 40, py_l, lx, py_l, lx - 40, py_l, lx - 72, py_l - 10, lx - 72, py_l - 66), F3)
    o += P('M%.1f %.1f C%.1f %.1f %.1f %.1f %.1f %.1f' % (lx - 66, py_l - 40, lx - 40, py_l - 32, lx + 40, py_l - 32, lx + 66, py_l - 40), at("none", 1.4, op=.5))   # 碗身花邊
    o += E(lx, py_l - 66, 72, 14, LP) + steam(lx - 20, py_l - 86) + steam(lx + 22, py_l - 84, 56)
    cyr = ry + 190
    for i in range(5):                                                          # 一疊帳單：每張有兩條字線
        yy = cyr - 30 * (i + 1); xx = rx - 100 + (i % 2) * 6
        o += R(xx, yy, 200, 30, 4, F3 if i % 2 else F1) + Ln(xx + 16, yy + 15, xx + 96, yy + 15, at("none", 1.5, op=.5)) + Ln(xx + 120, yy + 15, xx + 184, yy + 15, at("none", 1.5, op=.35))
    top = cyr - 150
    cal_y = top - 172
    o += R(rx - 84, cal_y, 168, 160, 8, F3) + R(rx - 84, cal_y, 168, 36, 8, DK)
    for xx in (rx - 50, rx + 50): o += Ln(xx, cal_y - 8, xx, cal_y + 12, at("none", 3))
    for k in range(4):
        for j in range(3): o += C(rx - 54 + k * 36, cal_y + 70 + j * 30, 3.6, at("var(--w-line)", 0, op=.6))
    o += C(rx - 18, cal_y + 100, 20, at("none", 3, stroke="var(--w-lamp)"))
    return o

def sc_steamq():
    o = glow(444, 520, 190)
    o += cloud(150, 104, 230, 72, 3, "var(--w-dark)", .75) + cloud(760, 150, 220, 70, 5, "var(--w-dark)", .75)
    o += hatch(60, 694, 770, 30, 11) + R(70, 654, 748, 38, 12, F1)
    for yy, x0, x1 in ((668, 110, 420), (680, 480, 780), (666, 560, 760)): o += Ln(x0, yy, x1, yy, at("none", 1.3, op=.3))   # 桌面木紋
    o += R(390, 636, 108, 20, 6, F1) + E(444, 646, 70, 9, at("none", 1.4, op=.4))
    o += P('M250 520 H638 C634 604 566 640 444 640 C322 640 254 604 250 520 Z', F3)
    o += P('M262 560 C330 580 560 580 626 560', at("none", 1.4, op=.5)) + P('M276 590 C340 608 548 608 612 590', at("none", 1.2, op=.4))
    o += E(444, 520, 194, 24, LP)
    o += Ln(236, 470, 660, 548, at("none", 5)) + Ln(250, 442, 676, 520, at("none", 5))
    m = lambda x, y: "%.1f %.1f" % (444 + (x - 444) * 2.6, 440 + (y - 290) * 2.6)
    q = "M%s C%s %s %s C%s %s %s" % (m(410, 196), m(410, 146), m(478, 146), m(478, 192), m(478, 226), m(444, 228), m(444, 262))
    o += P(q, at("none", 4, stroke="url(#fade)", dash="14 12"))
    o += P(q, at("none", 1.6, stroke="url(#fade)", op=.55, extra='transform="translate(-14 6)"'))
    o += C(444, 440, 7, at("var(--w-line)", 0, op=.85))
    return o

# ───────────────────────── 首篇三張（新畫）─────────────────────────
def sc_gap():
    """雲層裂開一道縫，一點光透出來；縫下是被光輕輕碰到的小鎮屋頂線。"""
    sx, sy = 452, 330
    shaft = poly([(sx - 26, sy + 20), (sx + 26, sy + 20), (sx + 190, 740), (sx - 190, 740)], at("var(--w-lamp)", 0, op=.07))
    o = glow(sx, sy + 10, 250) + shaft + rays(sx, sy, 60, 430, 62, 118, 11)
    o += C(sx, sy, 40, LP) + halo_rings(sx, sy, 40)
    o += cloud(130, 300, 230, 92, 21, "var(--w-dark)", .8) + cloud(750, 268, 240, 104, 23, "var(--w-dark)", .8)       # 遠雲
    o += cloud(248, 424, 440, 196, 3) + cloud(676, 408, 400, 184, 5)              # 上層雲，中間留縫
    o += cloud(190, 586, 340, 132, 9) + cloud(670, 596, 380, 146, 13)             # 下層雲，縫更寬
    for yy, x0, x1, op in ((640, 40, 330, .45), (654, 500, 850, .4), (670, 120, 420, .3), (684, 520, 800, .3)): o += Ln(x0, yy, x1, yy, at("none", 1.4, op=op, dash="22 10"))
    # 小鎮：屋頂線、窗格（不亮燈）、小樹
    o += hatch(60, 726, 770, 24, 12, at("none", 1.1, op=.25)) + Ln(30, 726, 858, 726, at("none", SW))
    xs = (300, 366, 436, 500, 560)
    for i, x in enumerate(xs):
        h = (40, 56, 34, 62, 44)[i]; w = (50, 56, 46, 52, 44)[i]
        o += R(x, 726 - h, w, h, 3, F1) + poly([(x - 6, 726 - h), (x + w / 2, 726 - h - 22), (x + w + 6, 726 - h)], F3)
        o += R(x + 8, 726 - h + 10, 12, 12, 2, at("none", 1.4, op=.5)) + R(x + w - 20, 726 - h + 10, 12, 12, 2, at("none", 1.4, op=.5))
    o += P('M120 726 q 10 -40 22 0', F3) + Ln(131, 726, 131, 700, at("none", 2)) + C(131, 690, 18, F3)
    o += P('M660 726 q 10 -34 20 0', F3) + Ln(670, 726, 670, 704, at("none", 2)) + C(670, 695, 15, F3)
    return o

def sc_window():
    """窗前書桌：筆記本、一盞小燈。窗外是雲（礙）、窗內的燈是光（晴）。"""
    o = glow(560, 500, 180)
    # 窗
    o += R(156, 34, 576, 404, 8, DK) + R(170, 48, 548, 376, 4, at("none", 1.8, op=.6))
    panes = [(178, 56, 258, 172), (452, 56, 258, 172), (178, 242, 258, 172), (452, 242, 258, 172)]
    for i, (x, y, w, h) in enumerate(panes):
        inner = R(x, y, w, h, 2, at("var(--w-face)", 0))
        if i == 0: inner += cloud(x + 130, y + 120, 190, 78, 31, "var(--w-face3)", free=True) + wisp(x + 20, y + 40, 110, .4)
        if i == 1: inner += cloud(x + 100, y + 98, 170, 70, 33, "var(--w-face3)", free=True) + cloud(x + 214, y + 146, 120, 52, 35, "var(--w-face3)", free=True) + wisp(x + 120, y + 36, 110, .4)
        if i in (2, 3):
            inner += P('M%d %d q 60 -30 120 -6 t 140 -10' % (x, y + h - 48), at("none", 1.6, op=.5)) + P('M%d %d q 70 -20 130 -2 t 130 -12' % (x, y + h - 22), at("none", 1.4, op=.35))
            inner += wisp(x + 30, y + 40, 100, .35) + (cloud(x + 170, y + 78, 130, 52, 37, "var(--w-face3)", free=True) if i == 3 else '')
        inner += Ln(x + w - 70, y + 6, x + w - 24, y + 52, at("none", 1.4, op=.18)) + Ln(x + w - 52, y + 6, x + w - 6, y + 52, at("none", 1.4, op=.18))   # 玻璃反光
        o += clip_rect(x, y, w, h, inner) + R(x, y, w, h, 2, at("none", SW))
    o += Ln(444, 48, 444, 424, at("none", 1.4, op=.5))
    # 窗台
    o += R(130, 438, 628, 22, 5, F3) + Ln(146, 449, 742, 449, at("none", 1.3, op=.35)) + hatch(150, 462, 590, 22, 11)
    # 桌面
    o += Ln(30, 640, 858, 640, at("none", SW)) + R(30, 640, 828, 26, 0, F1) + Ln(30, 666, 858, 666, THIN) + hatch(60, 668, 768, 36, 12, at("none", 1.1, op=.24))
    # 筆記本（攤開）
    o += poly([(178, 646), (184, 548), (338, 562), (494, 548), (500, 646), (338, 652)], DK)
    o += poly([(188, 638), (192, 556), (336, 570), (336, 644)], F3) + poly([(340, 570), (484, 556), (488, 638), (340, 644)], F3)
    for k in range(5):
        y0 = 586 + k * 11
        o += Ln(358, y0 - k * .2 + 4, 466 - (k % 2) * 30, y0 - 11 - k * .2 + 2, at("none", 1.4, op=.5 - k * .02))
    o += P('M206 600 q 12 -14 26 -4 q 14 -16 30 0 q 18 -4 16 12 H206 Z', at("none", 1.5, op=.6)) + Ln(210, 622, 306, 628, at("none", 1.3, op=.35))   # 左頁小雲塗鴉
    o += Ln(338, 570, 338, 644, at("none", 2)) + Ln(332, 572, 332, 642, at("none", 1.2, op=.35))
    # 疊書
    o += R(70, 604, 96, 18, 3, F1) + R(76, 622, 90, 18, 3, F3) + Ln(86, 613, 130, 613, HAIR) + Ln(94, 631, 140, 631, HAIR)
    # 小燈：底座、燈桿、燈罩（唯一暖色）、光錐
    o += poly([(560, 520), (650, 520), (440, 640), (700, 640)], at("var(--w-lamp)", 0, op=.07))
    o += E(660, 636, 58, 9, F3) + Ln(660, 628, 660, 500, at("none", 4)) + P('M660 500 q -36 -6 -62 -34', at("none", 4))
    o += P('M544 498 Q 598 410 656 498 Z', LP) + Ln(544, 498, 656, 498, at("none", SW)) + halo_rings(600, 470, 14, 1)
    o += P('M566 484 q 30 -50 60 -10', at("none", 1.4, "var(--w-dark)", op=.45))
    # 杯子
    o += P('M736 598 H790 C788 628 774 640 763 640 C752 640 738 628 736 598 Z', F3) + P('M790 606 c 18 -2 18 22 -4 22', at("none", 3)) + steam(754, 586, 50, .55) + steam(770, 584, 38, .45)
    return o

def sc_sunrise():
    """遠方雲後的日出；前景兩杯熱茶並肩（不畫人、不畫高處）。"""
    hy = 440; sx = 444
    o = glow(sx, hy - 20, 280)
    for i, rr in enumerate((108, 138, 172, 210)):                              # 日出的同心細圈（只畫地平線上的半圈）
        o += clip_rect(30, 100, 828, hy - 100, C(sx, hy, rr, at("none", 1.4, "var(--w-lamp)", op=.5 - i * .1, dash="3 10" if i % 2 else None)))
    o += rays(sx, hy, 96, 330, 195, 345, 21, at("none", 1.2, "var(--w-lamp)", op=.35))
    o += clip_rect(30, 100, 828, hy - 100, C(sx, hy, 78, LP)) + clip_rect(30, 100, 828, hy - 100, C(sx, hy, 92, at("none", 1.6, "var(--w-lamp)", op=.85)))
    # 雲層：左低右高，中間讓出日出
    o += cloud(444, 214, 260, 84, 41, "var(--w-dark)", .75) + cloud(175, 350, 320, 118, 43) + cloud(700, 330, 330, 124, 45)
    o += wisp(40, 150, 160, .4) + wisp(690, 134, 160, .4) + wisp(300, 120, 120, .3)
    # 遠山（細線填面）與地平線
    o += P('M30 %d L120 %d Q 170 %d 230 %d L330 %d Z' % (hy, hy - 28, hy - 58, hy - 22, hy), F1) + P('M570 %d L650 %d Q 720 %d 790 %d L858 %d Z' % (hy, hy - 24, hy - 62, hy - 26, hy), F1)
    o += Ln(30, hy, 858, hy, at("none", SW))
    # 水面／田野：反光的虛線漸短
    for i in range(8):
        w = 150 - i * 15; y = hy + 24 + i * 20
        o += Ln(sx - w / 2, y, sx + w / 2, y, at("none", 2, "var(--w-lamp)", op=.6 - i * .06, dash="16 8"))
    for yy, x0, x1 in ((hy + 40, 60, 260), (hy + 70, 600, 820), (hy + 100, 90, 300), (hy + 130, 580, 790)): o += Ln(x0, yy, x1, yy, at("none", 1.3, op=.3, dash="26 12"))
    # 桌面與兩杯茶（並肩，把手向外）
    o += hatch(100, 686, 690, 30, 12, at("none", 1.1, op=.25)) + Ln(60, 674, 828, 674, at("none", SW)) + R(60, 674, 768, 12, 0, F1)
    for cx_, side in ((386, -1), (502, 1)):
        o += E(cx_, 672, 62, 8, F1) + P('M%d 600 H%d C%d 646 %d 668 %d 668 C%d 668 %d 646 %d 600 Z' % (cx_ - 46, cx_ + 46, cx_ + 44, cx_ + 24, cx_, cx_ - 24, cx_ - 44, cx_ - 46), F3)
        o += E(cx_, 600, 46, 8, at("var(--w-dark)", 2.2)) + P('M%d 614 q 46 8 92 0' % (cx_ - 46), at("none", 1.3, op=.45))
        hx = cx_ + side * 46
        o += P('M%d 616 c %d -4 %d 30 %d 24' % (hx, side * 28, side * 28, -side * 4), at("none", 3.4))
        o += steam(cx_ - 12, 580, 64, .6) + steam(cx_ + 14, 576, 54, .5)
    return o

SCENES = {"qtable": sc_qtable, "scale": sc_scale, "steamq": sc_steamq, "ring": sc_ring, "gap": sc_gap, "window": sc_window, "sunrise": sc_sunrise}
SW_W, SW_H = 888, 764

def scene_svg(name, box_h=720, top=168, scale_fit=True, anchor="xMidYMid"):
    _uid[0] = 0
    defs = ('<radialGradient id="gl"><stop offset="0" stop-color="var(--w-lamp)" stop-opacity="1"/><stop offset="1" stop-color="var(--w-lamp)" stop-opacity="0"/></radialGradient>'
            '<linearGradient id="fade" gradientUnits="userSpaceOnUse" x1="0" y1="60" x2="0" y2="450"><stop offset="0" stop-color="var(--w-line)" stop-opacity=".12"/><stop offset="1" stop-color="var(--w-line)" stop-opacity="1"/></linearGradient>')
    body = SCENES[name]()
    return ('<div data-o="illus" class="illus" style="top:%dpx;width:888px;height:%dpx"><svg width="888" height="%d" viewBox="0 0 888 764" preserveAspectRatio="%s meet" xmlns="http://www.w3.org/2000/svg"><defs>%s</defs>'
            '<g id="ink">%s</g></svg></div>' % (top, box_h, box_h, anchor, defs, body))
