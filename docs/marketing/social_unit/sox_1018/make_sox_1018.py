"""IG 輪播「費半最近為什麼震盪走弱？」第 1、2 頁（1080x1350）— 第 2 版（繪本手繪質感）。
重跑：python3 docs/marketing/social_unit/sox_1018/make_sox_1018.py
文案只用 docs/marketing/social_unit/post_sox_1018.md；比比用 docs/anim/bibi_library 的透明 key.png（只做輕微旋轉／壓扁／局部合成，不重畫）。
字型：jf-openhuninn 粉圓 2.1（OFL，justfont）。字型檔不進 repo，缺檔時自動從
raw.githubusercontent.com/justfont/open-huninn-font 下載到 ~/.cache/sox1018/。
所有道具皆以 PIL 程序化繪製（4 倍超取樣、手繪抖動輪廓、內陰影、投影），最後加紙張顆粒與暖色暈邊。
同時輸出 overlap_report.json（逐元素外框相交檢查）。"""
import json, math, os, random, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

ROOT = Path('/home/user/tw-rotation')
OUT = ROOT / 'docs/marketing/social_unit/sox_1018'
LIB = ROOT / 'docs/anim/bibi_library'
FONTP = Path.home() / '.cache/sox1018/jf-openhuninn-2.1.ttf'
FONT_URL = 'https://raw.githubusercontent.com/justfont/open-huninn-font/master/font/jf-openhuninn-2.1.ttf'
if not FONTP.exists():
    FONTP.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(FONT_URL, FONTP)
FONT = str(FONTP)
W, H, SS = 1080, 1350, 4

CREAM = (255, 248, 238); INK = (66, 38, 26); CORAL = (240, 97, 90)
SUBINK = (112, 82, 64); BLUE_BG = (212, 232, 251); BLUE = (62, 140, 220)
PINK = (249, 207, 207); MINT = (205, 235, 216); YEL = (255, 214, 102)
WHITE = (255, 255, 255)
WARM = (122, 78, 52)          # 暖棕描邊（比填色深一階）


def S(v):
    return int(round(v * SS))


def darker(c, k=0.72):
    return tuple(int(v * k) for v in c)


def lighter(c, k=0.35):
    return tuple(int(v + (255 - v) * k) for v in c)


_fc = {}


def F(sz):
    k = int(sz * SS)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(FONT, k)
    return _fc[k]


# ---------------------------------------------------------------- 手繪輪廓
def rr_pts(box, r, step=5):
    x0, y0, x1, y1 = box
    r = min(r, (x1 - x0) / 2, (y1 - y0) / 2)
    pts = []

    def arc(cx, cy, a0, a1):
        n = max(5, int(r * abs(math.radians(a1 - a0)) / step))
        for i in range(n + 1):
            a = math.radians(a0 + (a1 - a0) * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    arc(x1 - r, y0 + r, -90, 0); arc(x1 - r, y1 - r, 0, 90)
    arc(x0 + r, y1 - r, 90, 180); arc(x0 + r, y0 + r, 180, 270)
    return pts


def resample(pts, step=5, closed=True):
    P = list(pts) + ([pts[0]] if closed else [])
    out = []
    for (ax, ay), (bx, by) in zip(P[:-1], P[1:]):
        L = math.hypot(bx - ax, by - ay)
        n = max(1, int(L / step))
        for i in range(n):
            out.append((ax + (bx - ax) * i / n, ay + (by - ay) * i / n))
    if not closed:
        out.append(P[-1])
    return out


def wobble(pts, amp, seed, wl=90, closed=True):
    rnd = random.Random(seed)
    ph = [rnd.uniform(0, 6.28) for _ in range(3)]
    n = len(pts); s = 0; out = []
    for i, (x, y) in enumerate(pts):
        px, py = pts[i - 1] if (closed or i > 0) else pts[i]
        nx, ny = pts[(i + 1) % n] if (closed or i < n - 1) else pts[i]
        tx, ty = nx - px, ny - py
        L = math.hypot(tx, ty) or 1
        if i:
            s += math.hypot(x - pts[i - 1][0], y - pts[i - 1][1])
        d = amp * (0.55 * math.sin(2 * math.pi * s / wl + ph[0]) +
                   0.3 * math.sin(2 * math.pi * s / (wl * 0.41) + ph[1]) +
                   0.15 * math.sin(2 * math.pi * s / (wl * 0.17) + ph[2]))
        out.append((x + ty / L * d, y - tx / L * d))
    return out


def chaikin(pts, it=2, closed=False):
    for _ in range(it):
        q = [pts[0]] if not closed else []
        P = pts + ([pts[0]] if closed else [])
        for a, b in zip(P[:-1], P[1:]):
            q.append((a[0] * .75 + b[0] * .25, a[1] * .75 + b[1] * .25))
            q.append((a[0] * .25 + b[0] * .75, a[1] * .25 + b[1] * .75))
        if not closed:
            q.append(pts[-1])
        pts = q
    return pts


def grad_img(size, c0, c1, horizontal=False):
    w, h = size
    t = np.linspace(0, 1, w if horizontal else h)[None, :, None] if horizontal else np.linspace(0, 1, h)[:, None, None]
    a = np.array(c0, float)[None, None, :] * (1 - t) + np.array(c1, float)[None, None, :] * t
    a = np.broadcast_to(a, (h, w, 3))
    return Image.fromarray(a.astype(np.uint8), 'RGB')


class Canvas:
    """1x 座標；內部 SS 倍。bg=None 代表透明 RGBA（用來畫要旋轉的道具）。"""

    def __init__(self, w, h, bg=None):
        self.w, self.h = w, h
        self.rgba = bg is None
        self.im = Image.new('RGBA', (S(w), S(h)), (0, 0, 0, 0)) if self.rgba else Image.new('RGB', (S(w), S(h)), bg)
        self.els = []

    def reg(self, eid, box):
        self.els.append((eid, tuple(int(round(v)) for v in box)))

    def put(self, src, mask, ox, oy):
        if self.rgba:
            src = src.convert('RGBA')
        self.im.paste(src, (ox, oy), mask)

    # ---- 通用塊面：漸層填色＋內陰影＋雙層鉛筆輪廓＋暈染＋投影
    def shape(self, pts, fill=(255, 255, 255), fill2=None, line=WARM, lw=3.5, shadow=True,
              inner=0.28, seed=1, halo=True, shadow_off=(5, 9), shadow_a=80):
        fill2 = fill2 or darker(fill, 0.93)
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        pad = 34
        ox, oy = S(min(xs) - pad), S(min(ys) - pad)
        w, h = S(max(xs) + pad) - ox, S(max(ys) + pad) - oy
        pp = [(S(x) - ox, S(y) - oy) for x, y in pts]
        mask = Image.new('L', (w, h), 0)
        ImageDraw.Draw(mask).polygon(pp, fill=255)
        if shadow:
            sh = ImageChops.offset(mask, S(shadow_off[0]), S(shadow_off[1])).filter(ImageFilter.GaussianBlur(S(6)))
            sh = sh.point(lambda v: int(v * shadow_a / 255))
            self.put(Image.new('RGB', (w, h), (150, 104, 74)), sh, ox, oy)
        bx0, by0 = int(min(p[0] for p in pp)), int(min(p[1] for p in pp))
        bx1, by1 = int(max(p[0] for p in pp)), int(max(p[1] for p in pp))
        g = Image.new('RGB', (w, h), fill)
        g.paste(grad_img((bx1 - bx0, by1 - by0), fill, fill2), (bx0, by0))
        self.put(g, mask, ox, oy)
        if inner:
            m2 = ImageChops.offset(mask, -S(7), -S(9)).filter(ImageFilter.GaussianBlur(S(6)))
            ia = ImageChops.multiply(mask, ImageChops.invert(m2)).point(lambda v: int(v * inner))
            self.put(Image.new('RGB', (w, h), darker(fill2, 0.62)), ia, ox, oy)
            # 左上淡高光
            m3 = ImageChops.offset(mask, S(5), S(6)).filter(ImageFilter.GaussianBlur(S(5)))
            ha = ImageChops.multiply(mask, ImageChops.invert(m3)).point(lambda v: int(v * 0.5))
            self.put(Image.new('RGB', (w, h), lighter(fill, 0.8)), ha, ox, oy)
        if line is not None:
            for k, (a, jx, jy) in enumerate(((1.0, 0, 0), (0.45, 1.3, -1.0))):
                pl = pp if k == 0 else [(x * SS + S(jx), y * SS + S(jy)) for x, y in wobble(
                    [(x / SS, y / SS) for x, y in pp[::2]], 1.6, seed + 7, 70)]
                lm = Image.new('L', (w, h), 0)
                d = ImageDraw.Draw(lm)
                P = pl + [pl[0]]
                d.line(P, fill=255, width=S(lw * (1 if k == 0 else 0.55)), joint='curve')
                if halo and k == 0:
                    hm = lm.filter(ImageFilter.GaussianBlur(S(1.6))).point(lambda v: int(v * 0.35))
                    self.put(Image.new('RGB', (w, h), lighter(line, 0.25)), hm, ox, oy)
                self.put(Image.new('RGB', (w, h), line), lm.point(lambda v: int(v * a)), ox, oy)

    def rrect(self, box, r, seed=1, amp=1.6, **kw):
        pts = wobble(resample(rr_pts(box, r), 5), amp, seed, 100)
        self.shape(pts, **kw)

    def ellipse(self, cx, cy, rx, ry, seed=1, amp=1.4, **kw):
        n = 80
        pts = [(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]
        self.shape(wobble(pts, amp, seed, 60), **kw)

    def poly(self, pts, seed=1, amp=1.2, rnd_r=0, **kw):
        pts = resample(pts, 5)
        self.shape(wobble(pts, amp, seed, 80), **kw)

    def stroke(self, pts, color, w, seed=1, amp=1.2, smooth=2, halo=True):
        P = chaikin(list(pts), smooth)
        P = wobble(resample(P, 4, closed=False), amp, seed, 60, closed=False)
        xs = [p[0] for p in P]; ys = [p[1] for p in P]
        pad = w + 8
        ox, oy = S(min(xs) - pad), S(min(ys) - pad)
        wd, ht = S(max(xs) + pad) - ox, S(max(ys) + pad) - oy
        m = Image.new('L', (wd, ht), 0)
        d = ImageDraw.Draw(m)
        pp = [(S(x) - ox, S(y) - oy) for x, y in P]
        d.line(pp, fill=255, width=S(w), joint='curve')
        for p in (pp[0], pp[-1]):
            d.ellipse([p[0] - S(w / 2), p[1] - S(w / 2), p[0] + S(w / 2), p[1] + S(w / 2)], fill=255)
        if halo:
            hm = m.filter(ImageFilter.GaussianBlur(S(1.8))).point(lambda v: int(v * 0.3))
            self.put(Image.new('RGB', (wd, ht), lighter(color, 0.3)), hm, ox, oy)
        self.put(Image.new('RGB', (wd, ht), color), m, ox, oy)

    def dot(self, cx, cy, r, fill, line=None, lw=2.5, seed=1):
        self.ellipse(cx, cy, r, r, seed=seed, amp=0.6, fill=fill, line=line, lw=lw, shadow=False, inner=0.15)

    # ---- 文字（粉圓體＋描邊加粗）
    def text(self, xy, s, size, fill=INK, anchor='la', bold=True, spacing=0):
        x, y = xy
        sw = max(1, int(size * 0.024 * SS)) if bold else 0
        d = ImageDraw.Draw(self.im)
        d.text((x * SS, y * SS), s, font=F(size), fill=fill, anchor=anchor, stroke_width=sw, stroke_fill=fill)
        b = d.textbbox((x * SS, y * SS), s, font=F(size), anchor=anchor, stroke_width=sw)
        return [v / SS for v in b]

    def paste_obj(self, obj, cx, cy, angle=0, scale=1.0):
        im = obj.im
        if scale != 1.0:
            im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
        if angle:
            im = im.rotate(angle, resample=Image.BICUBIC, expand=True)
        x, y = S(cx) - im.width // 2, S(cy) - im.height // 2
        self.im.paste(im, (x, y), im.getchannel('A'))
        return (x / SS, y / SS, (x + im.width) / SS, (y + im.height) / SS)


# ---------------------------------------------------------------- 標題手寫字
def dilate(mask, r):
    return mask.filter(ImageFilter.GaussianBlur(max(0.1, r / 1.17))).point(lambda v: 255 if v > 30 else 0)


def rnd_mask(mask, sg):
    return mask.filter(ImageFilter.GaussianBlur(sg)).point(lambda v: 255 if v > 118 else 0)


def hand_text(cv, eid, parts, size, x, y, anchor='l', seed=3, ow=2.4, track=0, rot=2.0, jit=0.035):
    """逐字：加粗→圓角化（模糊閾值）→深色描邊→奶白外描邊→投影；每字 ±rot 度、基線起伏。"""
    rnd = random.Random(seed)
    chars = [(c, col) for s, col in parts for c in s]
    f = F(size)
    adv = [f.getlength(c) / SS + track for c, _ in chars]
    total = sum(adv) - track
    x0 = x if anchor == 'l' else x - total / 2
    boxes = []
    for (c, col), a in zip(chars, adv):
        if c == ' ':
            x0 += a; continue
        pad = S(size * 0.35)
        w, h = S(a) + 2 * pad, S(size * 1.25) + 2 * pad
        m = Image.new('L', (w, h), 0)
        ImageDraw.Draw(m).text((pad, pad), c, font=f, fill=255, anchor='la', stroke_width=max(1, int(size * 0.013 * SS)), stroke_fill=255)
        m = rnd_mask(m, S(size * 0.008))
        m_ol = dilate(m, S(ow))
        m_out = dilate(m, S(ow + 4.5))
        ang = rnd.uniform(-rot, rot)
        sc = 1 + rnd.uniform(-jit, jit)
        base = rnd.uniform(-size * 0.03, size * 0.03)
        outs = []
        for mm in (m, m_ol, m_out):
            mm = mm.rotate(ang, resample=Image.BICUBIC, expand=True)
            outs.append(mm)
        mf, mo, mu = outs
        px = S(x0) - pad - (mf.width - w) // 2
        py = S(y + base) - pad - (mf.height - h) // 2
        shd = ImageChops.offset(mu, S(3), S(6)).filter(ImageFilter.GaussianBlur(S(2.5))).point(lambda v: int(v * 0.4))
        cv.put(Image.new('RGB', mf.size, (170, 120, 85)), shd, px, py)
        cv.put(Image.new('RGB', mf.size, (255, 252, 244)), mu, px, py)
        ocol = INK if col == INK else darker(col, 0.55)
        cv.put(Image.new('RGB', mf.size, ocol), mo, px, py)
        fillimg = grad_img(mf.size, lighter(col, 0.10), col)
        cv.put(fillimg, mf, px, py)
        bb = mo.getbbox()
        boxes.append(((px + bb[0]) / SS, (py + bb[1]) / SS, (px + bb[2]) / SS, (py + bb[3]) / SS))
        x0 += a
    box = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
    cv.reg(eid, box)
    return box


# ---------------------------------------------------------------- 比比（素材處理）
def bibi_layer(name, scale, rot=0.0, sx=1.0, sy=1.0, mirror=False, clear=None, marks=()):
    """回傳 (RGBA 圖層[SS 倍], 含邊界, marks 的圖層座標[SS 倍])。素材不重畫，只輕微旋轉／壓扁。"""
    im = Image.open(LIB / name / 'key.png').convert('RGBA')
    a = np.array(im)
    if clear:
        clear(a)
    # 暖色柔化：近黑描邊混入 30% 暖棕（保留原線稿）
    rgb = a[..., :3].astype(float)
    lum = rgb.mean(axis=2)
    k = np.clip((90 - lum) / 90, 0, 1)[..., None] * 0.30
    rgb = rgb * (1 - k) + np.array([84, 50, 34])[None, None, :] * k
    a[..., :3] = rgb.astype(np.uint8)
    im = Image.fromarray(a, 'RGBA')
    bb = im.getchannel('A').point(lambda v: 255 if v > 20 else 0).getbbox()
    pts = [(mx - bb[0], my - bb[1]) for mx, my in marks]
    im = im.crop(bb)
    if mirror:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
        pts = [(im.width - px, py) for px, py in pts]
    w, h = int(im.width * scale * sx * SS), int(im.height * scale * sy * SS)
    im = im.resize((w, h), Image.LANCZOS)
    pts = [(px * scale * sx * SS, py * scale * sy * SS) for px, py in pts]
    p = int(0.35 * max(w, h))
    big = Image.new('RGBA', (w + 2 * p, h + 2 * p), (0, 0, 0, 0))
    big.paste(im, (p, p))
    pts = [(px + p, py + p) for px, py in pts]
    if rot:
        c = (p + w / 2, p + h)
        big = big.rotate(rot, resample=Image.BICUBIC, center=c)
        th = math.radians(rot)
        q = []
        for px, py in pts:
            dx, dy = px - c[0], py - c[1]
            q.append((c[0] + dx * math.cos(th) + dy * math.sin(th), c[1] - dx * math.sin(th) + dy * math.cos(th)))
        pts = q
    # 邊緣柔化（alpha 輕微模糊）
    al = big.getchannel('A').filter(ImageFilter.GaussianBlur(S(0.35)))
    big.putalpha(al)
    return big, (p, p, p + w, p + h), pts


def place_bibi(cv, eid, layer, left, bottom, extra=(0, 0, 0, 14), shadow=True):
    big, (bx0, by0, bx1, by1), pts = layer
    x = S(left) - bx0
    y = S(bottom) - by1
    if shadow:
        w = (bx1 - bx0)
        sh = Image.new('L', (cv.im.width, S(60)), 0)
        ImageDraw.Draw(sh).ellipse([S(left) + w * 0.06, S(14), S(left) + w * 0.94, S(44)], fill=255)
        sh = sh.filter(ImageFilter.GaussianBlur(S(7))).point(lambda v: int(v * 0.42))
        cv.put(Image.new('RGB', sh.size, (160, 112, 80)), sh, 0, S(bottom) - S(30))
    cv.im.paste(big, (x, y), big.getchannel('A'))
    box = (left + extra[0], (bottom - (by1 - by0) / SS) + extra[1], left + (bx1 - bx0) / SS + extra[2], bottom + extra[3])
    cv.reg(eid, box)
    return [((x + px) / SS, (y + py) / SS) for px, py in pts], big, (x, y)


def hand_patch(cv, big, origin, pt, r):
    """把比比的手（含周圍一小圈）重新蓋在道具上面，製造「手抓著道具」的遮擋關係。"""
    x, y = origin
    cx, cy = S(pt[0]) - x, S(pt[1]) - y
    rr = S(r)
    box = (cx - rr, cy - rr, cx + rr, cy + rr)
    crop = big.crop(box)
    m = Image.new('L', crop.size, 0)
    ImageDraw.Draw(m).ellipse([S(1.5), S(1.5), crop.width - S(1.5), crop.height - S(1.5)], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(S(r * 0.18)))
    mn = np.asarray(crop.convert('RGB')).min(axis=2).astype(np.float32)
    skin = Image.fromarray(np.clip((250 - mn - 25) / 45, 0, 1).__mul__(255).astype(np.uint8))   # 只留手（非白毛）
    al = ImageChops.multiply(ImageChops.multiply(crop.getchannel('A'), m), skin)
    cv.im.paste(crop.convert('RGB'), (x + box[0], y + box[1]), al)


# ---------------------------------------------------------------- 道具
def new_obj(w, h):
    return Canvas(w, h, None)


def obj_notebook(w=104, h=134):
    o = new_obj(w + 40, h + 40)
    ox, oy = 20, 20
    o.rrect((ox, oy + 8, ox + w, oy + h), 12, seed=3, fill=(196, 232, 206), fill2=(160, 214, 178), line=(78, 128, 98), lw=3.2)
    for k in range(5):
        o.stroke([(ox + 20, oy + 40 + k * 17), (ox + w - 16, oy + 40 + k * 17 + (k % 2) * 1.5)], (112, 164, 132), 3, seed=k, amp=.6, smooth=0)
    for k in range(5):  # 線圈
        cx = ox + 14 + k * (w - 28) / 4
        o.ellipse(cx, oy + 9, 6, 9, seed=k, amp=.4, fill=(236, 240, 238), line=(80, 90, 90), lw=2.4, shadow=False, inner=0.1)
    return o


def obj_calendar(w=116, h=150):
    o = new_obj(w + 40, h + 40)
    ox, oy = 20, 20
    o.rrect((ox, oy + 10, ox + w, oy + h), 14, seed=5, fill=(255, 253, 248), fill2=(246, 236, 222), line=WARM, lw=3.4)
    o.rrect((ox, oy + 10, ox + w, oy + 52), 14, seed=6, amp=1, fill=(244, 126, 112), fill2=(226, 98, 88), line=(150, 62, 52), lw=3.2, shadow=False, inner=0.2)
    for cx in (ox + 32, ox + w - 32):
        o.rrect((cx - 5, oy, cx + 5, oy + 24), 5, seed=int(cx), amp=.3, fill=(250, 240, 224), fill2=(214, 196, 170), line=(110, 80, 60), lw=2.4, shadow=False, inner=0.2)
    cols = [(255, 190, 120), (130, 190, 240), (240, 140, 150), (150, 205, 165)]
    for r_ in range(4):
        for c_ in range(5):
            cx, cy = ox + 18 + c_ * 20, oy + 74 + r_ * 17
            if r_ == 2 and c_ == 3:
                o.ellipse(cx, cy, 10, 8, seed=9, amp=.6, fill=(255, 253, 248), line=(226, 70, 62), lw=3, shadow=False, inner=0)
            else:
                o.dot(cx, cy, 3.2, cols[(r_ + c_) % 4], seed=r_ * 5 + c_)
    return o


def obj_chip(w=92, h=92):
    o = new_obj(w + 50, h + 50)
    ox, oy = 25, 25
    for k in range(5):
        px = ox + 14 + k * (w - 28) / 4
        for yy in (oy - 12, oy + h - 2):
            o.rrect((px - 4, yy, px + 4, yy + 14), 3, seed=k + int(yy), amp=.2, fill=(244, 206, 110), fill2=(222, 170, 70), line=(150, 108, 40), lw=2, shadow=False, inner=0.1)
        py = oy + 14 + k * (h - 28) / 4
        for xx in (ox - 12, ox + w - 2):
            o.rrect((xx, py - 4, xx + 14, py + 4), 3, seed=k + int(xx), amp=.2, fill=(244, 206, 110), fill2=(222, 170, 70), line=(150, 108, 40), lw=2, shadow=False, inner=0.1)
    o.rrect((ox, oy, ox + w, oy + h), 14, seed=11, fill=(94, 138, 214), fill2=(56, 94, 176), line=(36, 56, 110), lw=3.6)
    o.rrect((ox + 22, oy + 22, ox + w - 22, oy + h - 22), 8, seed=12, amp=.8, fill=(120, 164, 236), fill2=(82, 124, 206), line=(40, 62, 120), lw=2.6, shadow=False, inner=0.2)
    o.dot(ox + 14, oy + 14, 4, (250, 232, 150), seed=3)
    return o


def obj_coin(r=30):
    o = new_obj(2 * r + 30, 2 * r + 30)
    c = r + 15
    o.ellipse(c, c, r, r, seed=2, amp=.9, fill=(255, 224, 120), fill2=(244, 184, 60), line=(156, 106, 30), lw=3.2)
    o.ellipse(c, c, r * .68, r * .68, seed=4, amp=.5, fill=(255, 232, 150), fill2=(246, 196, 80), line=(190, 140, 50), lw=2.2, shadow=False, inner=0.1)
    o.stroke([(c - 5, c - 8), (c - 5, c + 8)], (170, 120, 40), 3.2, amp=.2, smooth=0)
    o.stroke([(c + 5, c - 8), (c + 5, c + 8)], (170, 120, 40), 3.2, amp=.2, smooth=0)
    return o


def obj_arrow_badge(r=30):
    o = new_obj(2 * r + 30, 2 * r + 30)
    c = r + 15
    o.ellipse(c, c, r, r, seed=8, amp=.9, fill=(250, 150, 140), fill2=(236, 100, 92), line=(150, 56, 48), lw=3.2)
    o.poly([(c - 12, c - 14), (c + 12, c - 14), (c + 12, c + 2), (c + 20, c + 2), (c, c + 22), (c - 20, c + 2), (c - 12, c + 2)],
           seed=3, amp=.3, fill=WHITE, fill2=(255, 236, 232), line=(150, 56, 48), lw=2.4, shadow=False, inner=0.1)
    return o


def obj_plant(w=130, h=210):
    o = new_obj(w + 50, h + 50)
    ox, oy = 25, 25
    leaves = [(0.50, 0.28, 0.0, 36, 74), (0.22, 0.50, -58, 30, 60), (0.78, 0.50, 58, 30, 60),
              (0.34, 0.32, -30, 26, 58), (0.66, 0.30, 30, 26, 56)]
    for i, (fx, fy, ang, rw, rh) in enumerate(leaves):
        cx, cy = ox + w * fx, oy + h * fy + 40
        lo = new_obj(2 * rw + 40, 2 * rh + 40)
        lo.ellipse(rw + 20, rh + 20, rw * .55, rh, seed=i, amp=1.0, fill=(138, 200, 128), fill2=(88, 156, 92), line=(48, 100, 62), lw=3)
        lo.stroke([(rw + 20, rh * 2 + 8), (rw + 20, 28)], (70, 126, 78), 2.4, seed=i, amp=.5, smooth=1)
        r_ = lo.im.rotate(ang, resample=Image.BICUBIC, expand=True)
        px = S(cx) - r_.width // 2
        py = S(cy - rh * 0.55) - r_.height // 2
        o.im.paste(r_, (px, py), r_.getchannel('A'))
    o.poly([(ox + 18, oy + h - 78), (ox + w - 18, oy + h - 78), (ox + w - 34, oy + h), (ox + 34, oy + h)], seed=21, amp=.8,
           fill=(236, 150, 108), fill2=(200, 108, 74), line=(130, 70, 44), lw=3.4)
    o.rrect((ox + 10, oy + h - 92, ox + w - 10, oy + h - 66), 9, seed=22, amp=.6, fill=(244, 166, 122), fill2=(214, 124, 88), line=(130, 70, 44), lw=3.2, shadow=False, inner=0.2)
    return o


def obj_pencil(L=120):
    o = new_obj(L + 40, 50)
    cy = 25
    o.poly([(15, cy - 9), (L - 10, cy - 9), (L + 10, cy), (L - 10, cy + 9), (15, cy + 9)], seed=3, amp=.3,
           fill=(250, 200, 90), fill2=(232, 164, 50), line=(140, 96, 34), lw=2.8, shadow=False, inner=0.2)
    o.poly([(L - 10, cy - 9), (L + 10, cy), (L - 10, cy + 9)], seed=4, amp=.2, fill=(246, 222, 190), line=(140, 96, 34), lw=2.4, shadow=False, inner=0)
    o.poly([(L + 4, cy - 3), (L + 10, cy), (L + 4, cy + 3)], seed=5, amp=.1, fill=(66, 44, 34), line=None, shadow=False, inner=0)
    o.rrect((8, cy - 9, 28, cy + 9), 5, seed=6, amp=.3, fill=(244, 150, 150), fill2=(224, 110, 110), line=(140, 60, 60), lw=2.4, shadow=False, inner=0.1)
    return o


def obj_sparkle(r=14, color=YEL):
    o = new_obj(2 * r + 20, 2 * r + 20)
    c = r + 10
    o.poly([(c, c - r), (c + r * .28, c - r * .28), (c + r, c), (c + r * .28, c + r * .28), (c, c + r), (c - r * .28, c + r * .28),
            (c - r, c), (c - r * .28, c - r * .28)], seed=4, amp=.4, fill=color, fill2=darker(color, .93), line=darker(color, .6), lw=2, shadow=False, inner=0.1)
    return o


def draw_desk(cv, y0):
    """木桌面：漸層＋木紋＋上緣高光。是背景，不登記為元素。"""
    w, h = cv.w, cv.h - y0
    g = grad_img((S(w), S(h)), (240, 206, 160), (222, 178, 128))
    mask = Image.new('L', g.size, 255)
    cv.im.paste(g, (0, S(y0)), mask)
    rnd = random.Random(5)
    d = ImageDraw.Draw(cv.im)
    for k in range(26):
        yy = y0 + 18 + k * (h - 20) / 26 + rnd.uniform(-3, 3)
        x = rnd.uniform(-40, 400)
        while x < w:
            L = rnd.uniform(120, 360)
            pts = [(x + i * 12, yy + math.sin((x + i * 12) / 70 + k) * 2.2) for i in range(int(L / 12))]
            if len(pts) > 1:
                col = (214 - rnd.randint(0, 14), 168 - rnd.randint(0, 14), 120 - rnd.randint(0, 12))
                d.line([(a * SS, b * SS) for a, b in pts], fill=col, width=S(rnd.uniform(1.5, 3)), joint='curve')
            x += L + rnd.uniform(30, 120)
    # 上緣暖棕線（稍抖）＋高光
    top = wobble(resample([(-10, y0), (w + 10, y0)], 6, closed=False), 1.6, 9, 120, closed=False)
    d.line([(a * SS, b * SS) for a, b in top], fill=(158, 108, 72), width=S(4), joint='curve')
    hl = [(a, b + 5) for a, b in top]
    d.line([(a * SS, b * SS) for a, b in hl], fill=(252, 226, 186), width=S(4), joint='curve')


def washes(cv, specs):
    """水彩暈染底：大塊淡彩圓＋模糊。"""
    for cx, cy, r, col, a in specs:
        m = Image.new('L', cv.im.size, 0)
        ImageDraw.Draw(m).ellipse([S(cx - r), S(cy - r), S(cx + r), S(cy + r)], fill=int(255 * a))
        m = m.filter(ImageFilter.GaussianBlur(S(r * 0.35)))
        cv.im.paste(Image.new('RGB', cv.im.size, col), (0, 0), m)


def confetti(cv, eid_prefix, specs, reg=True):
    """彩色圓點／十字裝飾。specs=(x,y,r,color)。"""
    for i, (x, y, r, col) in enumerate(specs):
        cv.dot(x, y, r, col, line=darker(col, 0.7), lw=1.8, seed=i + 40)
        if reg:
            cv.reg(f'{eid_prefix}{i}', (x - r - 1, y - r - 1, x + r + 1, y + r + 1))


# ---------------------------------------------------------------- 全頁質感
def finish(cv, name, seed=1):
    im = cv.im.resize((W, H), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32)
    rng = np.random.default_rng(seed)
    # 顆粒
    fine = rng.normal(0, 4.2, (H, W)).astype(np.float32)
    coarse = np.asarray(Image.fromarray((rng.normal(0, 1, (H // 3, W // 3)) * 40 + 128).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(1.1))).astype(np.float32) - 128
    blot = np.asarray(Image.fromarray((rng.normal(0, 1, (H // 90, W // 90)) * 40 + 128).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(25))).astype(np.float32) - 128
    n = fine + coarse * 0.10 + blot * 0.05
    a = a + n[..., None]
    # 暖色暈邊
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    v = np.clip((r - 0.62) / 0.6, 0, 1) ** 1.6
    a = a * (1 - 0.035 * v[..., None])
    a[..., 2] -= 5 * v
    out = Image.fromarray(a.clip(0, 255).astype(np.uint8))
    # 輕微柔化：原圖與 0.55px 模糊 3:1 混合，去掉數位銳邊（色鉛筆／水彩暈感）
    soft = out.filter(ImageFilter.GaussianBlur(0.55))
    out = Image.blend(out, soft, 0.4)
    out.save(OUT / name, optimize=True)


def bg_canvas():
    cv = Canvas(W, H, CREAM)
    g = grad_img(cv.im.size, (255, 250, 242), (255, 244, 230))
    cv.im.paste(g, (0, 0))
    return cv


# ---------------------------------------------------------------- 共用元件
def header(cv, num, badge=True):
    cv.reg('brand', cv.text((54, 40), '哩股哩股', 36, INK))
    if badge:
        pts = wobble(resample(rr_pts((860, 38, 1026, 100), 31), 5), 1.0, 31, 90)
        cv.shape(pts, fill=(255, 250, 242), fill2=(255, 244, 230), line=INK, lw=4, shadow=False, inner=0.1)
        cv.reg('page_badge', (860, 38, 1026, 100))
        b = cv.text((943, 70), num, 38, INK, anchor='mm')
        cv.text_in.append(('page_badge_text', b, (860, 38, 1026, 100)))
    else:
        cv.reg('page_no', cv.text((1026, 44), num, 36, INK, anchor='ra'))


def pill(cv, eid, box, text, size, fill, line, fill2=None):
    cv.rrect(box, (box[3] - box[1]) / 2, seed=hash(eid) % 97, amp=1.4, fill=fill, fill2=fill2 or darker(fill, .95), line=line, lw=3, shadow=False, inner=0.15)
    cv.reg(eid, box)
    b = cv.text(((box[0] + box[2]) / 2, (box[1] + box[3]) / 2 + 1), text, size, INK, anchor='mm')
    cv.text_in.append((eid + '_text', b, box))


def bubble(cv, eid, box, s, size, tail_to, tail_x):
    x0, y0, x1, y1 = box
    pts = resample(rr_pts(box, 38), 5)
    # 找下緣由右往左通過 tail_x 的位置插入尾巴
    ins = None
    for i, (px, py) in enumerate(pts):
        if abs(py - y1) < 0.5 and px <= tail_x + 28:
            ins = i; break
    tail = [(tail_x + 28, y1), tail_to, (tail_x - 28, y1)]
    pts = pts[:ins] + tail + [p for p in pts[ins:] if not (abs(p[1] - y1) < .5 and tail_x - 28 <= p[0] <= tail_x + 28)]
    pts = wobble(resample(pts, 5), 1.4, 71, 100)
    cv.shape(pts, fill=WHITE, fill2=(255, 250, 244), line=INK, lw=3.8, shadow=True, inner=0.12, shadow_a=60)
    cv.reg(eid, (x0, y0, x1, tail_to[1]))
    b = cv.text(((x0 + x1) / 2, (y0 + y1) / 2 + 1), s, size, INK, anchor='mm')
    cv.text_in.append((eid + '_text', b, (x0, y0, x1, y1)))


def dashes(cv, eid, cx, cy, ang0, color, n=2, ln=36):
    segs = []
    for k in range(n):
        a = math.radians(ang0 + k * 28)
        p0 = (cx, cy); p1 = (cx + math.cos(a) * ln, cy + math.sin(a) * ln)
        cv.stroke([p0, p1], color, 8, seed=k + 3, amp=.5, smooth=0)
        segs += [p0, p1]
    cv.reg(eid, (min(p[0] for p in segs) - 5, min(p[1] for p in segs) - 5, max(p[0] for p in segs) + 5, max(p[1] for p in segs) + 5))


def fall_chart(cv, box, inner_pad=18, flow=False):
    """在 box 內畫：淡格線＋先漲後跌折線（藍→珊瑚）＋下跌段著色。"""
    x0, y0, x1, y1 = box
    gx0, gy0, gx1, gy1 = x0 + inner_pad, y0 + inner_pad, x1 - inner_pad, y1 - inner_pad
    for k in range(4):
        y = gy0 + (gy1 - gy0) * k / 3
        cv.stroke([(gx0, y), (gx1, y)], (232, 222, 210), 2, amp=.4, smooth=0, halo=False)
    pts = [(0, .62), (.10, .50), (.18, .56), (.30, .30), (.40, .18), (.48, .12), (.56, .30), (.64, .26), (.74, .52), (.82, .48), (.92, .80), (1, .86)]
    rnd = random.Random(7)
    xy = [(gx0 + (gx1 - gx0) * a + rnd.uniform(-2, 2), gy0 + (gy1 - gy0) * b + rnd.uniform(-2, 2)) for a, b in pts]
    seg = xy[5:]
    area = seg + [(seg[-1][0], gy1), (seg[0][0], gy1)]
    cv.poly(area, seed=3, amp=.6, fill=(253, 228, 226), fill2=(250, 208, 204), line=None, shadow=False, inner=0)
    cv.stroke(xy[:6], BLUE, 6.5, seed=2, amp=.8, smooth=1)
    cv.stroke(seg, CORAL, 7, seed=3, amp=.8, smooth=1)
    for i, (a, b) in enumerate(xy):
        cv.dot(a, b, 6, WHITE, line=(CORAL if i >= 5 else BLUE), lw=2.6, seed=i)


# ---------------------------------------------------------------- 第 1 頁
def cover():
    cv = bg_canvas(); cv.text_in = []
    washes(cv, [(120, 80, 260, (253, 226, 206), .55), (980, 330, 230, (214, 232, 250), .5),
                (140, 700, 210, (255, 236, 196), .4), (900, 1000, 260, (250, 222, 214), .30)])
    header(cv, '01/10')
    hand_text(cv, 'title1', [('費半最近為什麼', INK)], 126, 540, 124, anchor='c', seed=11)
    hand_text(cv, 'title2', [('震盪走弱？', CORAL)], 154, 540, 296, anchor='c', seed=12)
    dashes(cv, 'deco_r', 905, 458, -70, YEL)
    dashes(cv, 'deco_l', 130, 440, 200, (120, 190, 240))
    cv.reg('subtitle', cv.text((540, 472), '先看 3 個常見原因', 52, INK, anchor='ma'))
    pill(cv, 'capsule', (250, 552, 830, 636), '資金・估值・消息', 46, BLUE_BG, (120, 168, 220))
    bubble(cv, 'bubble', (52, 662, 566, 748), '先別慌，一起拆開看！', 40, (190, 792), 190)
    draw_desk(cv, 1140)
    # 道具：筆電（內含下跌折線與小流程圖）
    lx0, lx1, ly0, ly1 = 498, 912, 838, 1078
    cv.rrect((lx0, ly0, lx1, ly1), 22, seed=41, fill=(112, 110, 128), fill2=(78, 76, 92), line=(44, 38, 52), lw=4)
    cv.rrect((lx0 + 16, ly0 + 16, lx1 - 16, ly1 - 16), 10, seed=42, amp=.8, fill=(252, 253, 255), fill2=(228, 240, 252), line=(60, 56, 72), lw=2.4, shadow=False, inner=0.2)
    fall_chart(cv, (lx0 + 30, ly0 + 30, lx0 + 250, ly1 - 30), 8)
    # 小流程圖（方塊＋連線）
    fx = lx0 + 272
    for (bx, by, col) in ((fx + 50, ly0 + 40, BLUE_BG), (fx, ly0 + 108, MINT), (fx + 96, ly0 + 108, (255, 232, 170))):
        pass
    cv.stroke([(fx + 68, ly0 + 80), (fx + 68, ly0 + 100)], (120, 120, 150), 3, amp=.3, smooth=0, halo=False)
    cv.stroke([(fx + 19, ly0 + 100), (fx + 99, ly0 + 100)], (120, 120, 150), 3, amp=.3, smooth=0, halo=False)
    for (bx, by, col) in ((fx + 30, ly0 + 44, BLUE_BG), (fx - 8, ly0 + 108, MINT), (fx + 72, ly0 + 108, (255, 232, 170))):
        cv.rrect((bx, by, bx + 76 if by < ly0 + 100 else bx + 54, by + 36), 8, seed=int(bx), amp=.6, fill=col, fill2=darker(col, .93), line=(110, 130, 170), lw=2.4, shadow=False, inner=0.15)
    cv.stroke([(fx - 8 + 27, ly0 + 144), (fx - 8 + 27, ly0 + 160)], (140, 150, 180), 3, amp=.2, smooth=0, halo=False)
    cv.stroke([(fx + 72 + 27, ly0 + 144), (fx + 72 + 27, ly0 + 160)], (140, 150, 180), 3, amp=.2, smooth=0, halo=False)
    # 鍵盤底座
    base = [(lx0 - 36, ly1 + 6), (lx1 + 36, ly1 + 6), (lx1 + 22, ly1 + 44), (lx0 - 22, ly1 + 44)]
    cv.poly(base, seed=43, amp=.8, fill=(214, 212, 224), fill2=(176, 172, 190), line=(64, 58, 78), lw=3.6)
    for r_ in range(2):
        for c_ in range(17):
            kx = lx0 + 4 + c_ * 22.5
            cv.rrect((kx, ly1 + 16 + r_ * 13, kx + 18, ly1 + 26 + r_ * 13), 3, seed=c_ + r_ * 20, amp=.2, fill=(236, 234, 242), fill2=(204, 200, 216), line=None, shadow=False, inner=0.1)
    cv.reg('laptop', (lx0 - 36, ly0 - 2, lx1 + 36, ly1 + 46))
    # 桌曆、晶片
    cal = obj_calendar()
    cv.paste_obj(cal, 1000, 1010, 5)
    # 縮小 reg 到可見範圍
    cv.reg('calendar', (950, 930, 1052, 1090))
    chip = obj_chip()
    cv.paste_obj(chip, 610, 1204, -8)
    cv.reg('chip', (562, 1156, 660, 1252))
    # 比比（驚嘆＋手拿記事本）
    layer = bibi_layer('wow', 1.2, rot=-2.5, sx=1.03, sy=0.98, marks=((170, 373),))
    # 先放記事本再放比比，再蓋手
    left, bottom = 80, 1204
    pts, big, org = place_bibi(cv, 'bibi', layer, left, bottom, extra=(-22, 0, 0, 14))
    hand = pts[0]
    nb = obj_notebook()
    nbox = cv.paste_obj(nb, hand[0] - 34, hand[1] + 4, 10)
    hand_patch(cv, big, org, hand, 26)
    # 記事本是比比拿著的一部分：併入比比外框
    b = [e for e in cv.els if e[0] == 'bibi'][0][1]
    cv.els = [e for e in cv.els if e[0] != 'bibi']
    cv.reg('bibi', (min(b[0], nbox[0] + 14), b[1], b[2], b[3]))
    pill(cv, 'swipe_pill', (700, 1176, 1030, 1248), '向右滑 →', 40, BLUE_BG, (120, 168, 220))
    cv.reg('footnote', cv.text((540, 1280), '整理公開資訊，非投顧，非預測', 28, (86, 60, 44), bold=False, anchor='ma'))
    for (cx_, cy_, r_, c_, a_) in ((986, 800, 15, YEL, 8), (930, 780, 11, (150, 200, 240), -6)):
        cv.reg(f'spark{cx_}', cv.paste_obj(obj_sparkle(r_, c_), cx_, cy_, a_))
        cv.els[-1] = (f'spark{cx_}', (cx_ - r_ - 2, cy_ - r_ - 2, cx_ + r_ + 2, cy_ + r_ + 2))
    cv.reg('icon_coin', cv.paste_obj(obj_coin(26), 1000, 880, 8))
    cv.els[-1] = ('icon_coin', (972, 852, 1030, 908))
    confetti(cv, 'conf', [(86, 176, 6, (255, 190, 150)), (990, 232, 7, (150, 200, 240)), (60, 560, 6, (170, 220, 190)), (1010, 640, 6, (255, 200, 120)), (1034, 730, 5, (240, 150, 160)), (470, 1176, 5, (150, 200, 240))])
    finish(cv, 'p01_cover.png', 1)
    return cv


# ---------------------------------------------------------------- 第 2 頁
def clear_point_r(a):
    a[:, 447:, 3] = 0
    a[:358, 423:447, 3] = 0
    a[403:, 423:447, 3] = 0


def reasons():
    cv = bg_canvas(); cv.text_in = []
    washes(cv, [(940, 150, 230, (214, 232, 250), .5), (80, 1000, 230, (255, 232, 196), .45), (960, 980, 230, (250, 224, 216), .35)])
    header(cv, '02/10', badge=False)
    hand_text(cv, 'title', [('先看 3 個', INK), ('常見原因', CORAL)], 106, 54, 112, anchor='l', seed=21, ow=1.9)
    rows = [
        ('1', PINK, '漲多了，先獲利了結', '6 月創高後，部分資金落袋、轉向其他標的。'),
        ('2', BLUE_BG, '估值與 AI 支出被重新檢視', '市場擔心投資金額大，獲利跟不跟得上。'),
        ('3', MINT, '槓桿與擁擠部位去化', '太多人站同一邊，一鬆動就加速。'),
    ]
    y = 286
    for n, col, head, desc in rows:
        cx, cy = 54 + 46, y + 54
        cv.ellipse(cx, cy, 46, 46, seed=int(n), amp=1.2, fill=col, fill2=darker(col, .93), line=darker(col, .5), lw=3.4, shadow=True, shadow_a=50, inner=0.2)
        cv.reg(f'num{n}', (cx - 46, cy - 46, cx + 46, cy + 46))
        b = cv.text((cx, cy - 1), n, 54, INK, anchor='mm')
        cv.text_in.append((f'num{n}_text', b, (cx - 46, cy - 46, cx + 46, cy + 46)))
        cv.reg(f'head{n}', cv.text((176, y + 2), head, 50, INK))
        cv.reg(f'desc{n}', cv.text((178, y + 68), desc, 34, SUBINK, bold=False))
        y += 170
    draw_desk(cv, 1116)
    # 看板（平板）：三色分區＋下跌折線；斜靠背架
    tx0, ty0, tx1, ty1 = 470, 812, 886, 1090
    cv.poly([(tx0 + 120, ty1 - 10), (tx1 - 120, ty1 - 10), (tx1 - 150, ty1 + 22), (tx0 + 150, ty1 + 22)], seed=3, amp=.4, fill=(96, 94, 112), fill2=(70, 68, 86), line=(44, 38, 52), lw=3, shadow=False)
    cv.rrect((tx0, ty0, tx1, ty1), 26, seed=51, fill=(112, 110, 128), fill2=(78, 76, 92), line=(44, 38, 52), lw=4.2)
    sx0, sy0, sx1, sy1 = tx0 + 20, ty0 + 20, tx1 - 20, ty1 - 20
    zw = (sx1 - sx0) / 3
    zcols = [(253, 226, 224), (222, 238, 252), (222, 244, 230)]
    cv.rrect((sx0, sy0, sx1, sy1), 12, seed=52, amp=.8, fill=(252, 253, 255), fill2=(240, 246, 252), line=(60, 56, 72), lw=2.4, shadow=False, inner=0.15)
    for i, zc in enumerate(zcols):
        cv.rrect((sx0 + 8 + i * zw, sy0 + 8, sx0 + (i + 1) * zw - 6, sy1 - 8), 10, seed=60 + i, amp=.8, fill=zc, fill2=darker(zc, .96), line=darker(zc, .8), lw=2, shadow=False, inner=0.12)
    fall_chart(cv, (sx0 + 12, sy0 + 12, sx1 - 12, sy1 - 12), 24)
    cv.reg('board', (tx0, ty0, tx1, ty1 + 24))
    plant = obj_plant()
    cv.reg('plant', cv.paste_obj(plant, 984, 968, 0))
    cv.els[-1] = ('plant', (922, 864, 1048, 1094))
    # 比比：指向看板（point_r 去掉箭頭，自己畫指示棒）
    layer = bibi_layer('point_r', 1.12, rot=-1.5, sx=1.02, sy=0.98, clear=clear_point_r, marks=((420, 380),))
    left, bottom = 44, 1160
    pts, big, org = place_bibi(cv, 'bibi', layer, left, bottom, extra=(0, 0, 0, 14))
    hand = pts[0]
    tip = (448, 880)
    cv.stroke([(hand[0] - 6, hand[1] + 40), tip], (130, 84, 52), 11, seed=5, amp=.5, smooth=0)
    cv.stroke([(hand[0] - 6, hand[1] + 40), tip], (214, 164, 112), 6, seed=5, amp=.5, smooth=0, halo=False)
    cv.dot(tip[0], tip[1], 8, (240, 98, 86), line=(150, 50, 44), lw=2.4)
    hand_patch(cv, big, org, hand, 25)
    b = [e for e in cv.els if e[0] == 'bibi'][0][1]
    cv.els = [e for e in cv.els if e[0] != 'bibi']
    cv.reg('bibi', (b[0], min(b[1], tip[1] - 10), max(b[2], tip[0] + 6), b[3]))
    # 小圖示
    coin = obj_coin(28)
    cv.reg('icon_coin', cv.paste_obj(coin, 78, 826, -8))
    cv.els[-1] = ('icon_coin', (48, 796, 108, 856))
    arr = obj_arrow_badge(28)
    cv.reg('icon_down', cv.paste_obj(arr, 160, 828, 6))
    cv.els[-1] = ('icon_down', (130, 798, 190, 858))
    sp = obj_sparkle(16)
    cv.reg('icon_sp', cv.paste_obj(sp, 262, 820, 0))
    cv.els[-1] = ('icon_sp', (244, 802, 280, 838))
    # 記事本＋鉛筆（桌面）
    nb = new_obj(240, 100)
    nb.rrect((14, 10, 220, 82), 12, seed=33, fill=(255, 250, 238), fill2=(244, 232, 210), line=WARM, lw=3.2)
    nb.stroke([(117, 14), (117, 80)], (214, 190, 160), 2.6, amp=.4, smooth=0, halo=False)
    for k in range(3):
        nb.stroke([(30, 32 + k * 14), (104, 32 + k * 14)], (170, 196, 224), 2.4, seed=k, amp=.4, smooth=0, halo=False)
        nb.stroke([(132, 32 + k * 14), (204, 32 + k * 14)], (170, 196, 224), 2.4, seed=k + 5, amp=.4, smooth=0, halo=False)
    cv.paste_obj(nb, 172, 1226, -3)
    cv.reg('notebook', (52, 1192, 296, 1262))
    pc = obj_pencil(110)
    cv.paste_obj(pc, 372, 1226, -14)
    cv.reg('pencil', (312, 1196, 436, 1258))
    # 提示膠囊
    pb = (480, 1136, 1034, 1242)
    cv.rrect(pb, 50, seed=77, amp=1.4, fill=BLUE_BG, fill2=(196, 222, 248), line=(120, 168, 220), lw=3, shadow=True, shadow_a=50, inner=0.15)
    cv.reg('hint_pill', pb)
    cv.ellipse(530, 1189, 28, 28, seed=5, amp=.6, fill=BLUE, fill2=(48, 112, 196), line=(34, 76, 140), lw=2.6, shadow=False, inner=0.2)
    ib = cv.text((530, 1190), '!', 40, WHITE, anchor='mm')
    cv.text_in.append(('hint_icon', (502, 1161, 558, 1217), pb))
    b1 = cv.text((574, 1152), '據公開媒體整理，原因不只', 31, INK)
    b2 = cv.text((574, 1194), '一個，也不會一次講完。', 31, INK)
    cv.text_in += [('hint_l1', b1, pb), ('hint_l2', b2, pb)]
    cv.reg('footnote', cv.text((540, 1274), '資料整理自公開報導，非預測，非投資建議', 28, (86, 60, 44), bold=False, anchor='ma'))
    confetti(cv, 'conf', [(1000, 300 + 0, 6, (255, 190, 150)), (1020, 520, 7, (150, 200, 240)), (372, 836, 6, (170, 220, 190)), (990, 760, 5, (255, 200, 120))], reg=False)
    finish(cv, 'p02_reasons.png', 2)
    return cv


def overlap_check(cv, name):
    hits = []
    E = cv.els
    for i in range(len(E)):
        a_id, a = E[i]
        if a[0] < 24 or a[1] < 24 or a[2] > W - 24 or a[3] > H - 24:
            hits.append(f'{a_id} 超出安全邊界 {a}')
        for j in range(i + 1, len(E)):
            b_id, b = E[j]
            if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                hits.append(f'{a_id} {a} x {b_id} {b}')
    for eid, tb, cont in cv.text_in:
        if not (tb[0] >= cont[0] and tb[1] >= cont[1] and tb[2] <= cont[2] and tb[3] <= cont[3]):
            hits.append(f'{eid} 超出容器 {tb} / {cont}')
    return {'page': name, 'elements': len(E), 'overlaps': hits, 'boxes': E}


if __name__ == '__main__':
    rep = []
    for fn, name in ((cover, 'p01_cover.png'), (reasons, 'p02_reasons.png')):
        cv = fn()
        r = overlap_check(cv, name)
        rep.append(r)
        print(name, '元素', r['elements'], '重疊/越界', len(r['overlaps']))
        for h in r['overlaps']:
            print('  ', h)
    (OUT / 'overlap_report.json').write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding='utf-8')
