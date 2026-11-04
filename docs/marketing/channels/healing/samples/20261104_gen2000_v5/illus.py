"""v5 概念插圖（自繪向量）：座標 888×772，原生尺寸（不縮放），線寬 5.5。
面（填色）三階：--w-dark（凹處／底板）、--w-face（主面）、--w-face3（凸起／亮面）；暖黃光源 --w-lamp 每張一處。
圖上的比例與數字一律由程式依真實數字算出。"""
import math
SW = 5.5
LN = "var(--w-line)"
def at(fill, sw=SW, stroke=LN, extra=""):
    return 'fill="%s" stroke="%s" stroke-width="%s" stroke-linecap="round" stroke-linejoin="round" %s' % (fill, stroke, sw, extra)
F1 = at("var(--w-face)"); F3 = at("var(--w-face3)"); DK = at("var(--w-dark)"); LP = at("var(--w-lamp)")
NO = at("none"); FT = at("none", 3.5, extra='opacity=".6"'); NS = at("var(--w-dark)", 0)
def R(x, y, w, h, rx=0, st=F1): return '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%s" %s/>' % (x, y, w, h, rx, st)
def Ln(x1, y1, x2, y2, st=NO): return '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" %s/>' % (x1, y1, x2, y2, st)
def C(cx, cy, r, st=F1): return '<circle cx="%.1f" cy="%.1f" r="%.1f" %s/>' % (cx, cy, r, st)
def P(d, st=NO): return '<path d="%s" %s/>' % (d, st)
def poly(pts, st=F1): return '<polygon points="%s" %s/>' % (' '.join('%.1f,%.1f' % q for q in pts), st)
def dash(st, d="14 12"): return st.replace('stroke-linecap', 'stroke-dasharray="%s" stroke-linecap' % d)
def glow(cx, cy, r, op="var(--w-glow)"):
    return '<g data-g="1" style="filter:blur(30px)"><circle cx="%d" cy="%d" r="%d" fill="url(#gl)" opacity="%s"/></g>' % (cx, cy, r, op)
def T(x, y, s, anchor="middle", size=32, fill="var(--w-sub)"):
    return '<text x="%.1f" y="%.1f" text-anchor="%s" font-size="%d" fill="%s" stroke="none" style="letter-spacing:.05em">%s</text>' % (x, y, anchor, size, fill, s)
def steam(x, y, h=70):
    return P('M%s %s q 14 -%s 0 -%s q -14 -%s 0 -%s' % (x, y, h / 4, h / 2, h / 4, h / 2), at("none", 5, extra='opacity=".8"'))

def chair_top(cx, cy, ang):
    return '<g transform="rotate(%.1f %.1f %.1f)">%s</g>' % (ang, cx, cy, R(cx - 46, cy - 27, 92, 54, 15, F3))
def bowl_top(x, y, r, warm=False):
    return C(x, y, r, LP if warm else F3) + C(x, y, r * .6, at("none", 3.5))
def table(cx, cy, R_=262):
    o = ''
    for k in range(6):
        a = math.radians(30 + 60 * k)
        o += chair_top(cx + 322 * math.cos(a), cy + 322 * math.sin(a), 30 + 60 * k + 90)
    return o + C(cx, cy, R_, F1) + C(cx, cy, R_ - 24, at("none", 3.5, extra='opacity=".5"'))

def sc_qtable():
    cx, cy = 444, 386
    pts = []
    for a in (180, 215, 250, 285, 320, 355, 30):
        pts.append((444 + 60 * math.cos(math.radians(a)), 208 + 60 * math.sin(math.radians(a))))
    pts += [(470, 264), (452, 292)]
    f = lambda x, y: (cx + (444 + (x - 444) * .88 - 444) * 1.9, cy + 30 + (246 + (y - 240) * .88 - 274) * 1.9)
    o = glow(cx, 520, 230, "var(--w-glow)") + table(cx, cy)
    for (x, y) in pts: o += bowl_top(*f(x, y), 29)
    dx, dy = cx, cy + 30 + (246 + 96 * .88 - 274) * 1.9
    o += bowl_top(dx, dy, 29, True) + glow(int(dx), int(dy), 90, ".95")
    o += Ln(dx + 52, dy - 18, dx + 62, dy + 30, at("none", 7)) + Ln(dx + 68, dy - 18, dx + 78, dy + 30, at("none", 7))
    return o

def sc_ring():
    cx, cy = 444, 386
    o = glow(cx, cy, 250, "var(--w-glow)") + table(cx, cy)
    for k in range(6):
        a = math.radians(60 * k)
        o += bowl_top(cx + 160 * math.cos(a), cy + 160 * math.sin(a), 40)
    return o + C(cx, cy, 58, LP) + C(cx, cy, 24, at("none", 4))

def sc_scale():
    px, py, half, ang = 444, 170, 285, math.radians(6)
    lx, ly = px - half * math.cos(ang), py - half * math.sin(ang)
    rx, ry = px + half * math.cos(ang), py + half * math.sin(ang)
    o = glow(int(lx), int(ly) + 200, 160)
    o += R(426, py, 36, 540, 6, F1) + poly([(320, 712), (568, 712), (524, 668), (364, 668)], F1)
    nx, ny = -math.sin(ang) * 13, math.cos(ang) * 13
    o += poly([(lx - nx, ly - ny), (rx - nx, ry - ny), (rx + nx, ry + ny), (lx + nx, ly + ny)], F3) + C(px, py, 28, F3)
    for (x, y, pw) in ((lx, ly, 200), (rx, ry, 260)):
        o += Ln(x, y, x - pw / 2 + 10, y + 190) + Ln(x, y, x + pw / 2 - 10, y + 190) + R(x - pw / 2, y + 190, pw, 16, 6, F3)
    py_l = ly + 190
    o += P('M%.1f %.1f H%.1f C%.1f %.1f %.1f %.1f %.1f %.1f C%.1f %.1f %.1f %.1f %.1f %.1f Z' % (lx - 72, py_l - 66, lx + 72, lx + 72, py_l - 10, lx + 40, py_l, lx, py_l, lx - 40, py_l, lx - 72, py_l - 10, lx - 72, py_l - 66), F3)
    o += '<ellipse cx="%.1f" cy="%.1f" rx="72" ry="14" %s/>' % (lx, py_l - 66, LP) + steam(lx - 20, py_l - 86) + steam(lx + 22, py_l - 84, 56)
    cyr = ry + 190
    for i in range(5): o += R(rx - 100 + (i % 2) * 6, cyr - 30 * (i + 1), 200, 30, 4, F3 if i % 2 else F1)
    top = cyr - 150
    cal_y = top - 172
    o += R(rx - 84, cal_y, 168, 160, 8, F3) + R(rx - 84, cal_y, 168, 36, 8, DK)
    for k in range(4):
        for j in range(3): o += C(rx - 54 + k * 36, cal_y + 70 + j * 30, 5, at("var(--w-dark)", 0))
    o += C(rx - 18, cal_y + 100, 22, at("none", 6, stroke="var(--w-hint)"))
    return o

def sc_steamq():
    o = glow(444, 540, 230) + R(70, 654, 748, 40, 12, F1)
    o += R(390, 636, 108, 22, 6, F1)
    o += P('M250 520 H638 C634 604 566 640 444 640 C322 640 254 604 250 520 Z', F3)
    o += '<ellipse cx="444" cy="520" rx="194" ry="24" %s/>' % LP
    o += Ln(236, 470, 660, 548, at("none", 10)) + Ln(250, 442, 676, 520, at("none", 10))
    m = lambda x, y: "%.1f %.1f" % (444 + (x - 444) * 2.6, 440 + (y - 290) * 2.6)
    q = "M%s C%s %s %s C%s %s %s" % (m(410, 196), m(410, 146), m(478, 146), m(478, 192), m(478, 226), m(444, 228), m(444, 262))
    o += P(q, at("none", 9, stroke="url(#fade)", extra='stroke-dasharray="26 18"'))
    o += C(444, 440, 12, at("var(--w-line)", 0, extra='opacity=".85"'))
    return o

def tree_crown(x, y, k=1.0):
    cs = [(x, y, 105), (x - 92, y + 70, 80), (x + 92, y + 70, 80), (x - 60, y - 70, 72), (x + 68, y - 67, 72)]
    o = ''
    for cx, cy, r in cs: o += '<circle cx="%d" cy="%d" r="%.1f" fill="%s"/>' % (cx, cy, r * k + SW, LN)
    for cx, cy, r in cs: o += '<circle cx="%d" cy="%d" r="%.1f" fill="var(--w-face3)"/>' % (cx, cy, r * k)
    return o

def sc_treepot(reach=False):
    g = 470
    o = glow(722, 360, 150) + R(40, g, 808, 270, 0, NS) + R(612, g, 210, 120, 28, F1)
    o += R(222, 360, 58, 112, 6, F1) + tree_crown(251, 235)
    o += Ln(40, g, 848, g, at("none", SW))
    for d in ('M236 470 C220 540 180 590 100 620', 'M250 470 L250 660 M250 560 C230 610 200 640 150 700', 'M266 470 C300 540 380 580 470 590'):
        o += P(d, at("none", 6.5))
    o += P('M470 590 C500 594 520 596 540 596', dash(at("none", 6.5)))
    if reach: o += P('M540 596 C570 596 590 586 604 574', dash(at("none", 6.5), "3 12"))
    o += Ln(722, g, 722, 330) + P('M722 400 q -64 -10 -82 -64 q 64 -2 82 64 Z', F3) + P('M722 370 q 76 -14 92 -88 q -84 2 -92 88 Z', LP)
    if reach: o += P('M722 430 q 58 -2 72 -44 q -58 0 -72 44 Z', F3)
    return o

def sc_tree():
    g = 640
    o = glow(250, 230, 220) + R(40, g, 808, 90, 0, NS) + Ln(40, g, 848, g)
    o += R(214, 420, 72, 222, 8, F1) + tree_crown(250, 250, 1.25)
    for i in range(6):
        y = g - i * 100
        o += Ln(600, y, 700 if i % 2 == 0 else 664, y, at("none", 5))
    o += Ln(600, g, 600, 140, at("none", 5)) + Ln(588, 140, 740, 140, at("var(--w-lamp)", 7, stroke="var(--w-lamp)"))
    return o

def sc_means():
    base, M = 690, 210
    rel = [.40, .52, .62, .72, 38406 / 47884, .90, 1.05, 1.35, 0]
    rel[-1] = 9 - sum(rel[:-1])
    o = glow(380, 560, 160) + Ln(30, base, 858, base)
    w, gap, x0 = 70, 24, 33
    for i, r in enumerate(rel):
        x = x0 + i * (w + gap); h = r * M
        o += R(x, base - h, w, h, 5, LP if i == 4 else (F3 if i == 8 else F1))
    o += Ln(20, base - M, 868, base - M, dash(at("none", 4.5, stroke="var(--w-sub)"), "18 12"))
    o += T(30, base - M - 14, "平均", "start") + T(x0 + 4 * (w + gap) + w / 2, base + 44, "中位數")
    return o

def sc_slips():
    o = glow(640, 400, 200)
    w, h, gap, x0, y0 = 560, 54, 16, 140, 50
    for i in range(9):
        y = y0 + i * (h + gap); sx = 120 if i == 4 else 0
        o += R(x0 + sx, y, w, h, 8, LP if i == 4 else F1)
        o += Ln(x0 + sx + 24, y + h / 2, x0 + sx + 24 + 140, y + h / 2, at("none", 5, stroke="var(--w-dark)" if i == 4 else LN)) + Ln(x0 + sx + w - 120, y + h / 2, x0 + sx + w - 24, y + h / 2, at("none", 5, stroke="var(--w-dark)" if i == 4 else LN, extra='opacity=".7"'))
    my = y0 + 4 * (h + gap) + h / 2
    return o + poly([(60, my - 26), (112, my), (60, my + 26)], F3)

def sc_mailboxes():
    o = R(30, 46, 828, 680, 18, DK)
    cw, ch, gap, x0, y0 = 142, 146, 14, 64, 70
    for r in range(4):
        for c in range(5):
            x, y = x0 + c * (cw + gap), y0 + r * (ch + gap)
            if (r, c) == (1, 2): continue
            o += R(x, y, cw, ch, 10, F1) + Ln(x + 34, y + 40, x + cw - 34, y + 40, at("none", 7)) + C(x + cw / 2, y + 96, 7, F3)
    x, y = x0 + 2 * (cw + gap), y0 + 1 * (ch + gap)
    o += glow(int(x + cw / 2), int(y + ch / 2), 150, ".95")
    o += R(x, y, cw, ch, 10, LP) + R(x + 24, y + 30, 100, 70, 6, F3) + P('M%.1f %.1f l 50 34 l 50 -34' % (x + 24, y + 30), at("none", 4.5))
    o += poly([(x, y), (x - 38, y + 16), (x - 38, y + ch - 10), (x, y + ch)], F3)
    return o

def sc_windows():
    cols, cw, ch, gx, gy = 12, 56, 54, 12, 12
    x0, y0 = 42, 74
    dark = {(i * 37) % 102 for i in range(15)}
    o = R(20, 50, 848, 9 * ch + 8 * gy + 52, 14, DK) + glow(444, 330, 260)
    for i in range(102):
        r, c = divmod(i, cols); x, y = x0 + c * (cw + gx), y0 + r * (ch + gy)
        if i in dark: o += R(x, y, cw, ch, 6, at("none", 4))
        else: o += R(x, y, cw, ch, 6, at("var(--w-lamp)", 0, extra='opacity=".55"'))
    yb = 74 + 9 * ch + 8 * gy + 82
    return o + T(34, yb, "一格約 1 萬戶", "start") + T(854, yb, "空框＝未列入核准數", "end")

def sc_patch():
    x, y, w, h = 190, 84, 508, 604
    o = glow(560, 540, 230)
    o += P('M%d %d L%d %d L%d %d L%d %d L%d %d Z' % (x, y, x + w - 64, y, x + w, y + 64, x + w, y + h, x, y + h), at("var(--w-paper)")) + P('M%d %d L%d %d L%d %d' % (x + w - 64, y, x + w - 64, y + 64, x + w, y + 64), F1)
    o += T(x + 44, y + 84, "房租", "start", 44, "var(--w-dark)")
    for j in range(5):
        o += Ln(x + 44, y + 140 + j * 52, x + w - 180, y + 140 + j * 52, at("none", 6, stroke="var(--w-dark)")) + Ln(x + w - 140, y + 140 + j * 52, x + w - 44, y + 140 + j * 52, at("none", 6, stroke="var(--w-dark)", extra='opacity=".7"'))
    px, py, s = x + w - 270, y + h - 280, 232
    o += R(px, py, s, s, 12, at("var(--w-lamp)", SW))
    return o + R(px + 16, py + 16, s - 32, s - 32, 6, dash(at("none", 3.5, stroke="var(--w-dark)"), "10 9"))

def sc_mailbox1():
    o = glow(600, 400, 200)
    o += R(70, 230, 300, 420, 10, F3) + Ln(104, 282, 336, 282, at("none", 8, stroke="var(--w-dark)"))
    for j in range(5): o += Ln(104, 340 + j * 50, 336 - (j % 2) * 50, 340 + j * 50, at("none", 6, stroke="var(--w-dark)", extra='opacity=".7"'))
    o += R(104, 580, 70, 40, 6, at("none", 4, stroke="var(--w-dark)"))
    o += Ln(30, 690, 858, 690, at("none", SW)) + R(588, 520, 36, 170, 6, F1) + R(540, 676, 132, 14, 5, F1)
    o += poly([(440, 330), (480, 244), (730, 244), (770, 330)], F3)
    o += R(498, 276, 214, 140, 8, F3) + P('M498 276 l 107 78 l 107 -78', at("none", 5))
    o += R(440, 370, 330, 160, 24, F1) + R(456, 372, 298, 22, 8, LP)
    return o

def sc_teacup():
    o = glow(444, 470, 260) + R(70, 640, 748, 40, 12, F1)
    o += P('M270 400 H618 C614 540 560 620 444 620 C330 620 274 540 270 400 Z', F3) + '<ellipse cx="444" cy="400" rx="174" ry="26" %s/>' % LP
    o += P('M618 440 C700 430 710 540 600 548', at("none", 20)) + R(396, 614, 96, 30, 6, F1)
    return o + steam(400, 350, 130) + steam(450, 340, 100) + steam(500, 350, 120)

def sc_price():
    g = 690
    o = glow(110, 560, 190) + Ln(30, g, 858, g)
    xs = [470 + i * 52 for i in range(8)]
    hs = [100, 150, 195, 250, 330, 420, 520, 640]
    pts = []
    for x, h in zip(xs, hs):
        o += R(x - 22, g - h, 44, h, 0, F1)
        for yy in range(int(g - h + 20), g - 10, 34):
            if (x + yy) % 3 == 0: o += '<rect x="%d" y="%d" width="12" height="14" fill="var(--w-lamp)" opacity=".55"/>' % (x - 6, yy)
        pts.append((x, g - h))
    o += P('M' + ' L'.join('%d %d' % q for q in pts), dash(at("none", 6, stroke="var(--w-lamp)"), "16 12"))
    for q in pts: o += C(q[0], q[1], 9, F3)
    o += R(140, 470, 290, 220, 10, F3) + Ln(174, 506, 174, 658, at("none", 4.5, stroke="var(--w-dark)")) + Ln(174, 658, 400, 658, at("none", 4.5, stroke="var(--w-dark)")) + Ln(174, 610, 400, 598, at("none", 7, stroke="var(--w-dark)"))
    o += R(62, 650, 46, 40, 4, F1) + P('M62 650 L46 560 L124 560 L108 650 Z', LP) + Ln(85, 560, 85, 530, at("none", 5))
    return o

SCENES = {"qtable": sc_qtable, "scale": sc_scale, "steamq": sc_steamq, "ring": sc_ring, "treepot": sc_treepot,
          "treepot2": lambda: sc_treepot(True), "tree": sc_tree, "means": sc_means, "slips": sc_slips,
          "mailboxes": sc_mailboxes, "windows": sc_windows, "patch": sc_patch, "mailbox1": sc_mailbox1, "teacup": sc_teacup, "price": sc_price}
IH = 764
def scene_svg(name):
    defs = ('<radialGradient id="gl"><stop offset="0" stop-color="var(--w-lamp)" stop-opacity="1"/><stop offset="1" stop-color="var(--w-lamp)" stop-opacity="0"/></radialGradient>'
            '<linearGradient id="fade" gradientUnits="userSpaceOnUse" x1="0" y1="60" x2="0" y2="450"><stop offset="0" stop-color="var(--w-line)" stop-opacity=".12"/><stop offset="1" stop-color="var(--w-line)" stop-opacity="1"/></linearGradient>')
    return ('<div data-o="illus" class="illus" style="top:176px;width:888px;height:%dpx"><svg width="888" height="%d" viewBox="0 0 888 %d" xmlns="http://www.w3.org/2000/svg"><defs>%s</defs>%s</svg></div>'
            % (IH, IH, IH, defs, SCENES[name]()))
