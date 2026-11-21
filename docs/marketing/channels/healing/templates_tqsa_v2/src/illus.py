# -*- coding: utf-8 -*-
"""談晴說礙 v2 自繪向量插圖（沿用日日小晴 templates_rrxq 的素材，雲改灰＝礙、太陽＝晴；線條加填色，明亮悠閒）。每個場景回傳 (svg 字串, 寬, 高)。顏色全部走 palette dict。"""
import math

def mix(a, b, t):
    a = a.lstrip('#'); b = b.lstrip('#')
    ca = [int(a[i:i+2], 16) for i in (0, 2, 4)]; cb = [int(b[i:i+2], 16) for i in (0, 2, 4)]
    return '#%02X%02X%02X' % tuple(round(x + (y - x) * t) for x, y in zip(ca, cb))

W = 888
LEAF = '#A9CC93'; LEAFD = '#7FAE6C'; GREEN_ON = '#86D6A4'; WHITE = '#FFFFFF'

class S:
    """一個場景的畫布：收集 svg 片段；p 是色盤。"""
    def __init__(self, p, w, h, uid):
        self.p, self.w, self.h, self.uid, self.o = p, w, h, uid, []
        self.ink = p['ink']
    def add(self, s): self.o.append(s)
    def st(self, fill, sw=5, extra=''):
        return 'fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round" stroke-linecap="round" %s' % (fill, self.ink, sw, extra)
    def nost(self, fill, extra=''): return 'fill="%s" stroke="none" %s' % (fill, extra)
    def circ(self, cx, cy, r, fill, sw=5, extra=''): self.add('<circle cx="%.1f" cy="%.1f" r="%.1f" %s/>' % (cx, cy, r, self.st(fill, sw, extra)))
    def rect(self, x, y, w, h, rx, fill, sw=5, extra=''): self.add('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%s" %s/>' % (x, y, w, h, rx, self.st(fill, sw, extra)))
    def path(self, d, fill, sw=5, extra=''): self.add('<path d="%s" %s/>' % (d, self.st(fill, sw, extra)))
    def poly(self, pts, fill, sw=5, extra=''): self.add('<polygon points="%s" %s/>' % (' '.join('%.1f,%.1f' % q for q in pts), self.st(fill, sw, extra)))
    def line(self, x1, y1, x2, y2, sw=5, extra=''): self.add('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%s" stroke-linecap="round" %s/>' % (x1, y1, x2, y2, self.ink, sw, extra))
    def ell(self, cx, cy, rx, ry, fill, sw=5, extra=''): self.add('<ellipse cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" %s/>' % (cx, cy, rx, ry, self.st(fill, sw, extra)))
    def union(self, shapes, fill, sw=5):
        """多個圓／矩形合成一個外輪廓（先畫粗線再蓋填色，內部不留線）。shapes: ('c',cx,cy,r) 或 ('r',x,y,w,h,rx)"""
        def one(s, attr):
            if s[0] == 'c': return '<circle cx="%.1f" cy="%.1f" r="%.1f" %s/>' % (s[1], s[2], s[3], attr)
            return '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%.1f" %s/>' % (s[1], s[2], s[3], s[4], s[5], attr)
        a1 = 'fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"' % (self.ink, self.ink, sw * 2)
        a2 = 'fill="%s" stroke="none"' % fill
        self.add('<g>' + ''.join(one(s, a1) for s in shapes) + ''.join(one(s, a2) for s in shapes) + '</g>')
    def cloud(self, x, y, s=1.0, fill=None):
        fill = fill or self.p['cl']
        sh = [('c', x, y - 10 * s, 40 * s), ('c', x - 46 * s, y + 4 * s, 30 * s), ('c', x + 48 * s, y + 2 * s, 34 * s), ('r', x - 78 * s, y + 4 * s, 160 * s, 32 * s, 16 * s)]
        self.union(sh, fill)
    def sun(self, cx, cy, r, rays=True, fill=None, n=12, a0=0, a1=360, gap=14, ln=26):
        fill = fill or self.p['acc2']
        if rays:
            for i in range(n):
                a = math.radians(a0 + (a1 - a0) * i / (n if a1 - a0 == 360 else n - 1))
                self.line(cx + (r + gap) * math.cos(a), cy + (r + gap) * math.sin(a), cx + (r + gap + ln) * math.cos(a), cy + (r + gap + ln) * math.sin(a), 5)
        self.circ(cx, cy, r, fill)
    def grad(self, gid, top, bot):
        self.add('<defs><linearGradient id="%s_%s" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient></defs>' % (gid, self.uid, top, bot))
        return 'url(#%s_%s)' % (gid, self.uid)
    def begin(self, fill, r=40):
        self.add('<defs><clipPath id="cp_%s"><rect width="%d" height="%d" rx="%d"/></clipPath></defs><g clip-path="url(#cp_%s)">' % (self.uid, self.w, self.h, r, self.uid))
        self.add('<rect width="%d" height="%d" fill="%s"/>' % (self.w, self.h, fill))
    def end(self, r=40):
        self.add('</g><rect x="2.5" y="2.5" width="%d" height="%d" rx="%d" fill="none" stroke="%s" stroke-width="5"/>' % (self.w - 5, self.h - 5, r, self.ink))
    def svg(self):
        return '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">%s</svg>' % (self.w, self.h, self.w, self.h, ''.join(self.o))

def leaf(s, x, y, ang, L=70, Wd=26, fill=LEAF):
    """一片葉子：以 (x,y) 為葉柄，朝 ang 度伸出。"""
    a = math.radians(ang); ex, ey = x + L * math.cos(a), y + L * math.sin(a)
    nx, ny = -math.sin(a) * Wd, math.cos(a) * Wd; mx, my = x + L * .5 * math.cos(a), y + L * .5 * math.sin(a)
    s.path('M%.1f %.1f Q%.1f %.1f %.1f %.1f Q%.1f %.1f %.1f %.1f Z' % (x, y, mx + nx, my + ny, ex, ey, mx - nx, my - ny, x, y), fill, 4)

def house(s, x, y, w, h, wall, roof, lit=True):
    s.rect(x, y - h, w, h, 4, wall, 4)
    s.poly([(x - 6, y - h), (x + w / 2, y - h - h * .55), (x + w + 6, y - h)], roof, 4)
    s.rect(x + w * .3, y - h * .62, w * .4, h * .42, 3, s.p['acc2'] if lit else wall, 3)

# ---------- 場景 A：晚霞／硬幣太陽（封面）----------
def sc_sunset(p, uid='a'):
    s = S(p, W, 752, uid)
    top = mix(p['bg'], p['acc2'], .45); bot = mix(p['bg'], p['acc'], .6)
    s.begin(s.grad('sky', top, bot))
    cx, cy = 444, 430
    s.sun(cx, cy, 132, n=11, a0=196, a1=344, gap=20, ln=34)
    s.add('<circle cx="%d" cy="%d" r="98" fill="none" stroke="%s" stroke-width="3.5" stroke-dasharray="3 12" stroke-linecap="round" opacity=".55"/>' % (cx, cy, s.ink))
    s.cloud(160, 196, 1.2); s.cloud(716, 130, 0.95); s.cloud(700, 300, 0.7)
    s.union([('r', 90, 478, 230, 36, 18)], p['cl']); s.union([('r', 570, 408, 250, 36, 18)], p['cl'])
    far = mix(p['acc'], p['bg'], .45)
    s.path('M0 560 Q180 500 340 548 T620 540 T888 520 V752 H0 Z', far, 5)
    for hx, hy, hw, hh in ((70, 548, 54, 40), (150, 536, 46, 34), (668, 536, 56, 42), (748, 530, 48, 36)):
        house(s, hx, hy, hw, hh, WHITE, p['acc'])
    s.path('M0 630 Q220 575 470 620 T888 600 V752 H0 Z', p['acc'], 5)
    s.rect(300, 655, 300, 22, 11, mix(p['bg'], WHITE, .6), 4)   # 回家的小路
    s.line(238, 640, 238, 590, 6); s.circ(238, 566, 36, LEAF, 5); s.circ(206, 586, 26, LEAF, 5)
    for bx, by in ((560, 214), (610, 190), (590, 250)):
        s.add('<path d="M%d %d q14 -16 28 0 q14 -16 28 0" fill="none" stroke="%s" stroke-width="4.5" stroke-linecap="round"/>' % (bx, by, s.ink))
    s.end(); return s.svg(), W, 752

# ---------- 場景 B：中位數／小盆栽排排站（數據頁）----------
POT_X0, POT_STEP, POT_N, POT_MED = 36, 76, 11, 5
def sc_pots(p, uid='b'):
    h = 400; s = S(p, W, h, uid); s.begin(mix(p['bg'], p['acc2'], .28))
    gy = 338
    for i in range(POT_N):
        x = POT_X0 + i * POT_STEP + 28; ph = 36 + i * 15; med = (i == POT_MED)
        s.line(x, gy - 50, x, gy - 50 - ph, 5)
        top = gy - 50 - ph
        leaf(s, x, top + 34, -150, 38 + i, 14); leaf(s, x, top + 34, -30, 38 + i, 14)
        leaf(s, x, top + 10, -125, 30, 11, LEAFD); leaf(s, x, top + 10, -55, 30, 11, LEAFD)
        s.poly([(x - 30, gy - 52), (x + 30, gy - 52), (x + 23, gy), (x - 23, gy)], p['acc2'] if med else p['acc'], 5)
        if med: s.sun(x, top - 82, 30, n=10, gap=10, ln=18)
    s.cloud(130, 92, .8)
    s.line(10, gy, W - 10, gy, 5)
    s.end(); return s.svg(), W, h

def pot_center_x(): return 96 + POT_X0 + POT_MED * POT_STEP + 28

# ---------- 場景 C：窗台上曬太陽的小植物（一句話頁）----------
def sc_window(p, uid='c', observer=False):
    s = S(p, W, 752, uid); wall = mix(p['bg'], p['acc'], .22); s.begin(wall)
    s.rect(150, 56, 588, 440, 22, mix(WHITE, p['acc'], .30), 5)          # 窗
    s.sun(640, 190, 54, n=9, a0=150, a1=250, gap=12, ln=22)
    s.cloud(572, 226, .85); s.cloud(300, 120, .75)
    s.poly([(588, 200), (700, 200), (560, 496), (356, 496)], p['acc2'], 0, 'opacity=".38"')   # 光束
    s.line(444, 56, 444, 496, 5); s.line(150, 276, 738, 276, 5)
    s.rect(110, 496, 668, 38, 12, WHITE, 5)                              # 窗台
    s.ell(360, 500, 120, 14, p['acc2'], 0, 'opacity=".75"')
    # 主角：小綠
    px = 360
    s.poly([(px - 62, 400), (px + 62, 400), (px + 48, 496), (px - 48, 496)], p['acc'], 5)
    s.rect(px - 70, 386, 140, 26, 10, mix(p['acc'], WHITE, .25), 5)
    s.line(px, 386, px, 250, 6)
    for a, L, yy in ((-160, 78, 330), (-20, 78, 330), (-140, 70, 290), (-40, 70, 290), (-120, 58, 262), (-60, 58, 262)):
        leaf(s, px, yy, a, L, 24, LEAF)
    leaf(s, px, 262, -90, 62, 20, LEAFD)
    for sx, sy in ((px - 6, 168), (px + 46, 196), (px - 84, 214)):
        s.line(sx - 12, sy, sx + 12, sy, 4); s.line(sx, sy - 12, sx, sy + 12, 4)   # 新葉的小星光
    # 小多肉
    qx = 560
    s.poly([(qx - 40, 438), (qx + 40, 438), (qx + 32, 496), (qx - 32, 496)], p['acc2'], 5)
    for a in (-150, -110, -70, -30): leaf(s, qx, 438, a, 52, 17, LEAFD)
    if observer:   # 觀察者：窗台上一本攤開的記事本（記錄），本子上畫著一顆小太陽
        s.rect(166, 396, 104, 100, 8, WHITE, 5)
        s.line(218, 396, 218, 496, 3.5)
        for k in range(2): s.line(176, 444 + k * 24, 208, 444 + k * 24, 3.5)
        for k in range(3): s.line(228, 420 + k * 24, 260, 420 + k * 24, 3.5)
        s.circ(192, 420, 9, p['acc2'], 3.5)
    else:
        s.rect(214, 340, 22, 156, 5, WHITE, 4)
        for k in range(5): s.line(214, 360 + k * 28, 214 + (14 if k % 2 == 0 else 9), 360 + k * 28, 3.5)
    # 地板上的窗格光
    s.rect(0, 620, W, 132, 0, mix(p['bg'], p['acc2'], .35), 0)
    s.line(0, 620, W, 620, 4)
    for k in range(2):
        for j in range(2):
            x0 = 250 + k * 190 + j * 60; y0 = 650 + j * 50
            s.poly([(x0, y0), (x0 + 170, y0), (x0 + 140, y0 + 42), (x0 - 30, y0 + 42)], p['acc2'], 0, 'opacity=".7"')
    s.end(); return s.svg(), W, 752

# ---------- 場景 D：綠燈一路亮到家（今日小晴）----------
def sc_lights(p, uid='d'):
    s = S(p, W, 752, uid); vx, vy = 444, 330
    s.begin(s.grad('sky', mix(p['bg'], p['acc2'], .5), mix(p['bg'], p['acc'], .5)))
    s.sun(vx, vy - 6, 78, n=9, a0=200, a1=340, gap=14, ln=26)
    s.cloud(170, 130, 1.0); s.cloud(740, 190, .8)
    s.rect(0, vy, W, 752 - vy, 0, mix(LEAF, p['bg'], .35), 0); s.line(0, vy, W, vy, 4)
    house(s, vx - 36, vy, 72, 52, WHITE, p['acc'])
    ex = lambda y: (y - vy) / (720 - vy) * 325
    s.poly([(vx - 2, vy), (vx + 2, vy), (vx + ex(752), 752), (vx - ex(752), 752)], mix(p['bg'], p['ink'], .16), 0)
    s.line(vx - 2, vy, vx - ex(752), 752, 5); s.line(vx + 2, vy, vx + ex(752), 752, 5)
    for k in range(7):
        t0 = (vy + 40 + k * 55); 
    for k, y in enumerate((372, 408, 462, 534, 624, 735)):
        wdt = ex(y) * .09 + 2; hgt = 20 + (y - vy) * .12
        s.add('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="%s" stroke="none"/>' % (vx - wdt, y, vx + wdt, y, vx + wdt * 1.4, y + hgt, vx - wdt * 1.4, y + hgt, p['acc2']))
    for k in range(4, -1, -1):
        sc = .72 ** k; base = vy + (720 - vy) * sc; sw = max(3, 5 * sc)
        for side in (-1, 1):
            x = vx + side * 345 * sc; top = base - 400 * sc
            s.add('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%.1f" stroke-linecap="round"/>' % (x, base, x, top, s.ink, 14 * sc + 3))
            s.add('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%.1f" stroke-linecap="round"/>' % (x, base, x, top, p['acc'], 14 * sc))
            hw, hh = 58 * sc, 142 * sc
            s.add('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%.1f" fill="%s" stroke="%s" stroke-width="%.1f"/>' % (x - hw / 2, top - hh * .5, hw, hh, 12 * sc, WHITE, s.ink, sw))
            for j, col in enumerate((mix(p['bg'], p['ink'], .12), mix(p['bg'], p['ink'], .12), GREEN_ON)):
                cyy = top - hh * .5 + hh * (.2 + .3 * j); r = 16 * sc
                if j == 2: s.add('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" opacity=".45"/>' % (x, cyy, r * 1.9, GREEN_ON))
                s.add('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="%s" stroke-width="%.1f"/>' % (x, cyy, r, col, s.ink, max(2.5, 4 * sc)))
    s.end(); return s.svg(), W, 752

# ---------- 場景 E：熱湯蒸氣長成小雲（Threads）----------
def sc_bowl(p, uid='e'):
    h = 830; s = S(p, W, h, uid); s.begin(mix(p['bg'], p['acc'], .22))
    for sx in (350, 430, 510):
        s.add('<path d="M%d 560 q-26 -34 0 -68 q26 -34 0 -68 q-26 -34 0 -68" fill="none" stroke="%s" stroke-width="6" stroke-linecap="round"/>' % (sx, s.ink))
    s.circ(600, 300, 74, p['acc2'], 5)
    for i in range(10):
        ang = -180 + i * 20
        if -175 <= ang <= 5:
            a = math.radians(ang)
            s.line(600 + 92 * math.cos(a), 300 + 92 * math.sin(a), 600 + 122 * math.cos(a), 300 + 122 * math.sin(a), 5)
    s.cloud(430, 330, 1.8)
    s.rect(0, 640, W, 190, 0, mix(p['bg'], p['acc'], .35), 0); s.line(0, 640, W, 640, 5)
    s.path('M180 560 H700 C700 690 600 760 440 760 C280 760 180 690 180 560 Z', p['acc'], 5)
    s.ell(440, 560, 260, 40, p['acc2'], 5)
    for cx_, cy_ in ((360, 556), (470, 566), (540, 552), (410, 572)): s.circ(cx_, cy_, 9, LEAF, 3.5)
    s.rect(330, 764, 220, 22, 11, mix(p['acc'], p['ink'], .2), 5)
    s.line(740, 600, 818, 520, 7); s.ell(832, 508, 22, 15, p['acc2'], 4, 'transform="rotate(-48 832 508)"')
    s.end(); return s.svg(), W, h

# ---------- 場景 G：雲縫裡的一小角太陽（出處頁小裝飾）----------
def sc_gap(p, uid='g', w=300, h=230):
    s = S(p, w, h, uid); s.begin(mix(p['bg'], p['acc'], .3), 34)
    s.sun(150, 150, 54, n=7, a0=210, a1=330, gap=12, ln=22)
    s.union([('c', 70, 120, 56), ('c', 24, 150, 40), ('r', 0, 130, 120, 60, 30)], p['cl'])
    s.union([('c', 238, 112, 52), ('c', 282, 146, 38), ('r', 170, 128, 130, 62, 31)], p['cl'])
    s.end(34); return s.svg(), w, h


def dk(p, t=.16): return mix(p['cl'], p['ink'], t)   # 較深的雲灰（雲的後層）

def hills(s, p, y0=560, houses=True, lit=True, tree=True):
    far = mix(p['acc'], p['bg'], .45)
    s.path('M0 %d Q180 %d 340 %d T620 %d T888 %d V752 H0 Z' % (y0, y0 - 60, y0 - 12, y0 - 20, y0 - 40), far, 5)
    if houses:
        for hx, hy, hw, hh in ((70, y0 - 12, 54, 40), (150, y0 - 24, 46, 34), (668, y0 - 24, 56, 42), (748, y0 - 30, 48, 36)):
            house(s, hx, hy, hw, hh, WHITE, p['acc'], lit)
    s.path('M0 %d Q220 %d 470 %d T888 %d V752 H0 Z' % (y0 + 70, y0 + 15, y0 + 60, y0 + 40), p['acc'], 5)
    if tree:
        s.line(238, y0 + 80, 238, y0 + 30, 6); s.circ(238, y0 + 6, 36, LEAF, 5); s.circ(206, y0 + 26, 26, LEAF, 5)

# ---------- 談晴說礙 封面：大雲（礙）擋住半邊，太陽（晴）從雲後把光灑出來（由日日小晴「晚霞硬幣太陽」改） ----------
def sc_cover(p, uid='h'):
    s = S(p, W, 752, uid)
    s.begin(s.grad('sky', mix(p['bg'], p['acc2'], .45), mix(p['bg'], p['acc'], .6)))
    cx, cy = 520, 372
    s.sun(cx, cy, 132, n=12, a0=196, a1=344, gap=20, ln=34)
    s.add('<circle cx="%d" cy="%d" r="98" fill="none" stroke="%s" stroke-width="3.5" stroke-dasharray="3 12" stroke-linecap="round" opacity=".55"/>' % (cx, cy, s.ink))
    s.cloud(250, 400, 1.9, dk(p, .1)); s.cloud(330, 318, 1.25)      # 左前方的大雲：擋住太陽左下
    s.cloud(770, 150, 1.0); s.cloud(150, 150, .8)
    hills(s, p, 580)
    for bx, by in ((440, 96), (490, 72), (470, 132)):
        s.add('<path d="M%d %d q14 -16 28 0 q14 -16 28 0" fill="none" stroke="%s" stroke-width="4.5" stroke-linecap="round"/>' % (bx, by, s.ink))
    s.end(); return s.svg(), W, 752

# ---------- 5 張版第 3 張：有些難——厚厚的雲層，山腳下的家還亮著燈 ----------
def sc_clouds(p, uid='i'):
    s = S(p, W, 752, uid)
    s.begin(s.grad('sky', mix(p['bg'], p['ink'], .20), mix(p['bg'], p['ink'], .04)))
    for x, y, k in ((140, 150, 1.7), (720, 130, 1.8), (440, 70, 1.4)): s.cloud(x, y, k, dk(p, .22))
    for x, y, k in ((300, 250, 2.0), (640, 290, 2.1), (90, 330, 1.5), (840, 360, 1.3)): s.cloud(x, y, k, dk(p, .08))
    s.cloud(440, 400, 1.7)
    s.poly([(420, 470), (480, 470), (600, 700), (400, 700)], p['acc2'], 0, 'opacity=".55"')   # 雲縫漏下的一縷光（在山丘後面）
    hills(s, p, 600, True, True)
    s.end(); return s.svg(), W, 752

# ---------- 5 張版第 4 張：但我們也看見晴——雲裂開一道縫，太陽把光灑在小鎮上 ----------
def sc_gaptown(p, uid='j'):
    s = S(p, W, 752, uid)
    s.begin(s.grad('sky', mix(p['bg'], p['acc2'], .55), mix(p['bg'], p['acc'], .5)))
    cx, cy = 444, 250
    s.poly([(cx - 60, cy + 40), (cx + 60, cy + 40), (cx + 250, 640), (cx - 250, 640)], p['acc2'], 0, 'opacity=".38"')   # 光束
    s.sun(cx, cy, 104, n=13, a0=196, a1=344, gap=18, ln=32)
    s.add('<circle cx="%d" cy="%d" r="76" fill="none" stroke="%s" stroke-width="3.5" stroke-dasharray="3 12" stroke-linecap="round" opacity=".55"/>' % (cx, cy, s.ink))
    s.cloud(150, 290, 2.1, dk(p, .1)); s.cloud(750, 300, 2.1, dk(p, .1))
    s.cloud(190, 130, 1.2); s.cloud(740, 120, 1.0)
    hills(s, p, 560)
    s.end(); return s.svg(), W, 752

# ---------- 談與說：左邊灰雲對話框（說礙）、右邊太陽對話框（談晴），中間一株小苗 ----------
def sc_talk(p, uid='k'):
    s = S(p, W, 752, uid)
    s.begin(s.grad('sky', mix(p['bg'], p['acc2'], .4), mix(p['bg'], p['acc'], .45)))
    s.path('M0 640 Q220 590 470 635 T888 610 V752 H0 Z', mix(LEAF, p['bg'], .35), 5)
    # 雲對話框（礙）
    s.poly([(190, 360), (150, 470), (270, 385)], p['cl'], 5)
    s.union([('c', 270, 215, 84), ('c', 170, 255, 62), ('c', 372, 252, 70), ('r', 100, 250, 340, 110, 55)], p['cl'])
    for dx in (-52, 0, 52): s.circ(270 + dx, 300, 13, p['ink'], 3.5)
    # 太陽對話框（晴）
    for i in range(14):
        a = math.radians(360 * i / 14); s.line(650 + 142 * math.cos(a), 300 + 142 * math.sin(a), 650 + 174 * math.cos(a), 300 + 174 * math.sin(a), 5)
    s.circ(650, 300, 120, p['acc2'], 5)
    s.line(650, 360, 650, 300, 6)    # 對話框裡的小苗：回答長出來
    leaf(s, 650, 318, -150, 56, 20); leaf(s, 650, 318, -30, 56, 20); leaf(s, 650, 300, -90, 50, 17, LEAFD)
    # 中間地面小苗
    s.line(444, 640, 444, 580, 6); leaf(s, 444, 600, -150, 46, 17); leaf(s, 444, 600, -30, 46, 17)
    s.end(); return s.svg(), W, 752

# ---------- Reels 封面：草地野餐墊，一朵雲抱枕、一顆太陽抱枕（取代日日小晴的晾衣繩，避開繩索意象） ----------
def sc_picnic(p, uid='l'):
    h = 860; s = S(p, W, h, uid)
    s.begin(s.grad('sky', mix(p['bg'], p['acc2'], .5), mix(p['bg'], p['acc'], .35)))
    s.poly([(0, 0), (330, 0), (110, h), (0, h)], p['acc2'], 0, 'opacity=".25"')
    s.sun(660, 190, 70, n=11, a0=190, a1=350, gap=14, ln=26)
    s.cloud(190, 150, 1.2, dk(p, .08)); s.cloud(560, 330, .9); s.cloud(830, 330, .7)
    s.path('M0 470 Q220 410 470 460 T888 430 V%d H0 Z' % h, mix(p['acc'], p['bg'], .45), 5)
    s.rect(0, 540, W, h - 540, 0, mix(LEAF, p['bg'], .3), 0); s.line(0, 540, W, 540, 5)
    # 野餐墊（梯形＋格紋）
    s.poly([(150, 600), (738, 600), (840, 800), (48, 800)], mix(p['acc2'], WHITE, .35), 5)
    for k in range(1, 6):
        t = k / 6; x0 = 150 + (48 - 150) * 0 + k * 98; s.line(150 + k * 98, 600, 48 + k * 132, 800, 3.5, 'opacity=".5"')
    for yy in (650, 700, 750):
        t = (yy - 600) / 200; s.line(150 - 102 * t, yy, 738 + 102 * t, yy, 3.5, 'opacity=".5"')
    s.cloud(300, 705, 1.0)                                       # 雲抱枕
    s.circ(560, 690, 52, p['acc2'], 5)                           # 太陽抱枕
    for i in range(10):
        a = math.radians(360 * i / 10); s.line(560 + 64 * math.cos(a), 690 + 64 * math.sin(a), 560 + 82 * math.cos(a), 690 + 82 * math.sin(a), 4.5)
    for fx, fy in ((60, 560), (840, 566), (790, 840)):
        s.line(fx, fy, fx, fy - 40, 4); s.circ(fx, fy - 50, 11, p['acc2'], 4)
    s.end(); return s.svg(), W, h
