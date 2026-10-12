"""第 4 版自繪鏡頭（storyboard_v4_*.md 第 0、5-3、14、15 節）：痛點開場三格、LOGO、比比自我介紹、3D 四宮格、片尾、警語。
開場不放任何網站或別家 App 畫面（只畫空白小視窗、方塊、月曆格）。每個元素都登記外框（v3_check），互不重疊。
手機：所有文字放在 Reels 安全區內（不進底部 320px、右側 140px）。
"""
from __future__ import annotations

import math

from PIL import Image, ImageDraw

import render_1010 as B
import render_v3 as R
import v3_check as C
from render_1010 import LEMON, WHITE, anim_frame, back_out, clamp, ease_io, ease_out, font, logo_sized, put_sprite, reader, rounded_mask, text_w
from v3_cards import bubble_box, center_head, sprite_union_rect, disclaimer_fn as _disc_v3
from v3_core import ROLE, card_host

THEME = R.THEME
SKY = (120, 190, 240)
PINK = (245, 160, 170)
MINT = (140, 210, 180)
INK = (60, 70, 90)


MCX = 540            # 手機卡片水平中心（畫面正中；內容寬 ≤800 → x 140～940，不進右側 140px 的 Reels 介面區）
MHEAD_Y = 250        # 手機卡片大字的 y（卡片內容整體在 y 250～1580，上下對稱）


def _push(fn, amt=0.03):
    """整張卡片慢推（3 秒內放大 3%）：動畫收尾後畫面也持續微動，不會被判成停格（freezedetect n=0.003 d=0.5）。"""
    def w(cv, t, shot):
        fn(cv, t, shot)
        k = 1 + amt * clamp(t / max(0.5, shot.dur), 0, 1)
        W, H = cv.size
        im = cv.resize((int(W * k) + 1, int(H * k) + 1), Image.BILINEAR)
        ox, oy = (im.width - W) // 2, (im.height - H) // 2
        cv.paste(im.crop((ox, oy, ox + W, oy + H)), (0, 0))
    return w


def _host(cv, L, nm, text, t, mode=None):
    """卡片鏡頭的比比＋泡泡。網頁用一般主持位；手機改放底部安全區上緣（比比在左、泡泡在右，整組水平置中）。"""
    if L.fmt == "web":
        return card_host(cv, L, nm, text, t, mode)
    old = (L.host_x, L.host_foot, L.host_w, L.host_h, L.host_size)
    L.host_x, L.host_foot, L.host_w, L.host_h, L.host_size = 320, 1570, 360, 340, 440
    try:
        card_host(cv, L, nm, text, t, mode)
    finally:
        L.host_x, L.host_foot, L.host_w, L.host_h, L.host_size = old


def _zone(L):
    """內容區（避開標題、比比帶與手機 Reels 介面區）。"""
    if L.fmt == "web":
        return (360, 172, 1680, 812)
    return (140, 460, 940, 1190)


# ---------------------------------------------------------------------------------------------
# 痛點開場三張卡（Andy 10-12：太潦草 → 補強）。全部用 PIL 畫，假資料、不標任何真實公司或 App。
# ---------------------------------------------------------------------------------------------
import random

RED = (226, 96, 100)
GRN = (72, 176, 126)
DSKY = (84, 150, 222)
PURP = (186, 168, 232)
GRAY = (196, 204, 218)
GRID = (226, 232, 242)
SS = 2    # 內容層超取樣倍率（圖形邊緣才不會鋸齒）


def _fr(sz):
    return font(B.F_ROUND, int(sz))


def _fs(sz):
    return font(B.F_ROUND, int(sz * SS))


def _ln(d, pts, col, w=2):
    d.line([(x * SS, y * SS) for x, y in pts], fill=col, width=max(1, int(w * SS)), joint="curve")


def _rr(d, r, rad, fill=None, outline=None, w=1):
    d.rounded_rectangle([r[0] * SS, r[1] * SS, r[2] * SS, r[3] * SS], rad * SS, fill=fill, outline=outline, width=int(w * SS))


def _tx(d, x, y, s, f, col, anchor="la"):
    d.text((x * SS, y * SS), s, font=f, fill=col, anchor=anchor)


# ---- 視窗內容（每個都不一樣；w、h 是內容區邏輯像素，d 是 SS 倍層）----------------------------------
def _c_candle(d, w, h, t):
    rnd = random.Random(11)
    n = 15
    p, cs = 50.0, []
    for _ in range(n):
        o = p
        p += rnd.uniform(-5, 6.5)
        cs.append((o, p, max(o, p) + rnd.uniform(1, 4), min(o, p) - rnd.uniform(1, 4)))
    o, c, hi, lo = cs[-1]                                   # 最後一根微微跳動（動畫收尾後仍有微動）
    c += 2.5 * math.sin(t * 5)
    cs[-1] = (o, c, max(hi, c), min(lo, c))
    lo_all = min(x[3] for x in cs) - 2
    hi_all = max(x[2] for x in cs) + 2
    Y = lambda v: h - 6 - (v - lo_all) / (hi_all - lo_all) * (h - 14)
    for i in range(1, 4):
        _ln(d, [(4, h * i / 4), (w - 4, h * i / 4)], GRID, 1)
    cw = (w - 12) / n
    for i, (o, c, hi, lo) in enumerate(cs):
        col = RED if c >= o else GRN
        x = 6 + cw * (i + 0.5)
        _ln(d, [(x, Y(hi)), (x, Y(lo))], col, 2)
        _rr(d, (x - cw * 0.3, Y(max(o, c)), x + cw * 0.3, Y(min(o, c)) + 1), 1.5, fill=col)
    cl = [x[1] for x in cs]
    for per, col in ((3, (240, 170, 60)), (6, DSKY)):
        pts = []
        for i in range(per - 1, n):
            pts.append((6 + cw * (i + 0.5), Y(sum(cl[i - per + 1:i + 1]) / per)))
        _ln(d, pts, col, 3)


def _c_area(d, w, h, t):
    rnd = random.Random(5)
    n = 36
    v, ys = 40.0, []
    for i in range(n):
        v += rnd.uniform(-4, 5.5)
        ys.append(v)
    ys[-1] += 2 * math.sin(t * 4)
    lo, hi = min(ys) - 4, max(ys) + 4
    X = lambda i: 6 + (w - 12) * i / (n - 1)
    Y = lambda q: h - 8 - (q - lo) / (hi - lo) * (h - 20)
    for i in range(1, 4):
        _ln(d, [(4, h * i / 4), (w - 4, h * i / 4)], GRID, 1)
    pts = [(X(i), Y(ys[i])) for i in range(n)]
    d.polygon([(x * SS, y * SS) for x, y in pts] + [(X(n - 1) * SS, (h - 4) * SS), (X(0) * SS, (h - 4) * SS)], fill=(206, 229, 249))
    _ln(d, pts, DSKY, 3.5)
    ex, ey = pts[-1]
    d.ellipse([(ex - 6) * SS, (ey - 6) * SS, (ex + 6) * SS, (ey + 6) * SS], fill=WHITE, outline=DSKY, width=3 * SS)


def _c_donut(d, w, h, t):
    cols = [SKY, PINK, MINT, LEMON, PURP]
    vals = [34, 24, 18, 14, 10]
    r = min(h / 2 - 6, w * 0.36)
    cx, cy = 6 + r + 4, h / 2
    a0 = -90 + t * 24
    for v, c in zip(vals, cols):
        a1 = a0 + v * 3.6
        d.pieslice([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS], a0, a1, fill=c, outline=WHITE, width=3 * SS)
        a0 = a1
    ri = r * 0.52
    d.ellipse([(cx - ri) * SS, (cy - ri) * SS, (cx + ri) * SS, (cy + ri) * SS], fill=WHITE)
    _tx(d, cx, cy, "100%", _fs(max(16, r * 0.3)), INK, "mm")
    lx = cx + r + 22
    for i, (v, c) in enumerate(zip(vals, cols)):
        yy = 16 + i * (h - 32) / 4.0
        _rr(d, (lx, yy - 8, lx + 16, yy + 8), 4, fill=c)
        bw = (w - lx - 8 - 30) * v / 34
        _rr(d, (lx + 24, yy - 5, lx + 24 + max(10, bw), yy + 5), 5, fill=(214, 222, 236))


def _c_table(d, w, h, t):
    f = _fs(20 if h > 190 else 18)
    rows = [("營收", "86.2", "+12%"), ("毛利率", "41.3", "+2.1"), ("EPS", "3.28", "+0.4"), ("淨利", "22.5", "+9%"), ("現金", "64.0", "-3%")]
    rh = h / 6.0
    cx = [8, w * 0.42, w * 0.74]
    _rr(d, (2, 0, w - 2, rh - 2), 6, fill=(226, 236, 248))
    for x, s in zip(cx, ("項目", "本期", "年增")):
        _tx(d, x, rh / 2 - 1, s, f, DSKY, "lm")
    for i, row in enumerate(rows):
        y = rh * (i + 1)
        if i % 2 == 1:
            _rr(d, (2, y, w - 2, y + rh - 2), 6, fill=(244, 247, 252))
        for j, s in enumerate(row):
            col = INK if j < 2 else (RED if not s.startswith("-") else GRN)
            _tx(d, cx[j], y + rh / 2 - 1, s, f, col, "lm")


def _c_rank(d, w, h, t):
    f = _fs(20)
    cols = [SKY, PINK, MINT, LEMON, PURP]
    lens = [1.0, 0.82, 0.66, 0.5, 0.36]
    rh = h / 5.0
    for i in range(5):
        y = rh * i + rh / 2
        d.ellipse([4 * SS, (y - 12) * SS, 28 * SS, (y + 12) * SS], fill=(236, 240, 248), outline=GRAY, width=2 * SS)
        _tx(d, 16, y, str(i + 1), f, INK, "mm")
        L = (w - 44) * lens[i] * (0.97 + 0.03 * math.sin(t * 3 + i))
        _rr(d, (38, y - rh * 0.3, 38 + L, y + rh * 0.3), 7, fill=cols[i])


def _c_heat(d, w, h, t):
    f = _fs(20)
    cols, rows = 4, 3
    cw, ch = (w - 6) / cols, (h - 4) / rows
    rnd = random.Random(23)
    for r in range(rows):
        for c in range(cols):
            v = rnd.uniform(-3.5, 3.5) + 0.35 * math.sin(t * 2.5 + r * 2 + c)
            k = min(1.0, abs(v) / 3.5)
            base = RED if v >= 0 else GRN
            col = tuple(int(255 - (255 - b) * (0.25 + 0.75 * k)) for b in base)
            x0, y0 = 3 + c * cw, 2 + r * ch
            _rr(d, (x0 + 2, y0 + 2, x0 + cw - 2, y0 + ch - 2), 8, fill=col)
            _tx(d, x0 + cw / 2, y0 + ch / 2, f"{v:+.1f}", f, WHITE if k > 0.55 else INK, "mm")


_WIN = [("K 線", _c_candle), ("走勢", _c_area), ("持股比重", _c_donut), ("財報", _c_table), ("排行", _c_rank), ("熱力圖", _c_heat)]


def _window_img(k, w, h, t):
    title, fn = _WIN[k]
    lay = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    ld.rounded_rectangle([0, 0, w - 1, h - 1], 18, fill=WHITE, outline=(120, 140, 170), width=3)
    ld.rounded_rectangle([0, 0, w - 1, 38], 18, fill=(225, 232, 242))
    ld.rectangle([2, 24, w - 3, 38], fill=(225, 232, 242))
    for j in range(3):
        ld.ellipse([16 + j * 24, 12, 30 + j * 24, 26], fill=[(240, 120, 120), (240, 200, 90), (120, 200, 130)][j])
    ld.text((92, 19), title, font=_fr(22), fill=INK, anchor="lm")
    cw, ch = int(w - 40), int(h - 38 - 26)
    c = Image.new("RGBA", (cw * SS, ch * SS), (0, 0, 0, 0))
    fn(ImageDraw.Draw(c), cw, ch, t)
    c = c.resize((cw, ch), Image.LANCZOS)
    lay.alpha_composite(c, (20, 38 + 12))
    return lay


# ---- 雪花產業鏈 ------------------------------------------------------------------------------
def _ico(d, kind, x, y, s, col):
    """簡筆小圖示：d 是 SS 倍層，(x,y) 是圖示左上角、s 是邊長（邏輯像素）。"""
    S = SS
    X = lambda v: (x + v * s) * S
    Y = lambda v: (y + v * s) * S
    lw = max(2, int(s * 0.09 * S))
    if kind == "chip":
        d.rounded_rectangle([X(.22), Y(.22), X(.78), Y(.78)], 3 * S, fill=col)
        for i in range(3):
            v = .34 + .16 * i
            d.line([X(v), Y(.08), X(v), Y(.22)], fill=col, width=lw)
            d.line([X(v), Y(.78), X(v), Y(.92)], fill=col, width=lw)
            d.line([X(.08), Y(v), X(.22), Y(v)], fill=col, width=lw)
            d.line([X(.78), Y(v), X(.92), Y(v)], fill=col, width=lw)
        d.rectangle([X(.4), Y(.4), X(.6), Y(.6)], fill=WHITE)
    elif kind == "gear":
        c = (X(.5), Y(.5))
        for i in range(8):
            a = i * math.pi / 4
            d.line([c[0] + math.cos(a) * s * .26 * S, c[1] + math.sin(a) * s * .26 * S, c[0] + math.cos(a) * s * .44 * S, c[1] + math.sin(a) * s * .44 * S], fill=col, width=int(s * .2 * S))
        d.ellipse([X(.2), Y(.2), X(.8), Y(.8)], fill=col)
        d.ellipse([X(.4), Y(.4), X(.6), Y(.6)], fill=WHITE)
    elif kind == "pcb":
        d.rounded_rectangle([X(.06), Y(.16), X(.94), Y(.84)], 3 * S, fill=col)
        for pts in (((.2, .35), (.45, .35), (.45, .6), (.72, .6)), ((.2, .7), (.34, .7)), ((.58, .3), (.8, .3), (.8, .45))):
            d.line([(X(a), Y(b)) for a, b in pts], fill=WHITE, width=max(1, lw // 2 + 1))
        for a, b in ((.2, .35), (.72, .6), (.8, .45)):
            d.ellipse([X(a) - 3 * S, Y(b) - 3 * S, X(a) + 3 * S, Y(b) + 3 * S], fill=WHITE)
    elif kind == "fins":
        d.rectangle([X(.1), Y(.74), X(.9), Y(.92)], fill=col)
        for i in range(5):
            v = .14 + .18 * i
            d.rounded_rectangle([X(v), Y(.1), X(v + .1), Y(.78)], 2 * S, fill=col)
    elif kind == "bolt":
        d.polygon([(X(.58), Y(.04)), (X(.2), Y(.56)), (X(.46), Y(.56)), (X(.36), Y(.96)), (X(.8), Y(.38)), (X(.54), Y(.38))], fill=col)
    elif kind == "wave":
        pts = [(X(.04 + .92 * i / 40), Y(.5 - .32 * math.sin(i / 40 * 2 * math.pi * 1.5))) for i in range(41)]
        d.line(pts, fill=col, width=int(s * .12 * S), joint="curve")
    elif kind == "rack":
        for i in range(3):
            yy = .1 + .3 * i
            d.rounded_rectangle([X(.14), Y(yy), X(.86), Y(yy + .24)], 2 * S, fill=col)
            d.ellipse([X(.24), Y(yy + .08), X(.24) + 4 * S, Y(yy + .08) + 4 * S], fill=WHITE)
            d.line([X(.5), Y(yy + .12), X(.78), Y(yy + .12)], fill=WHITE, width=max(1, lw // 2))
    elif kind == "ram":
        d.rounded_rectangle([X(.04), Y(.26), X(.96), Y(.7), ], 2 * S, fill=col)
        for i in range(4):
            d.rectangle([X(.14 + .2 * i), Y(.36), X(.26 + .2 * i), Y(.54)], fill=WHITE)
        for i in range(8):
            d.rectangle([X(.08 + .11 * i), Y(.7), X(.12 + .11 * i), Y(.84)], fill=col)
    elif kind == "tool":
        d.line([X(.2), Y(.8), X(.62), Y(.38)], fill=col, width=int(s * .16 * S))
        d.ellipse([X(.5), Y(.06), X(.92), Y(.48)], fill=col)
        d.polygon([(X(.76), Y(.2)), (X(.92), Y(.06)), (X(.94), Y(.26))], fill=WHITE)
    elif kind == "flask":
        d.polygon([(X(.4), Y(.08)), (X(.6), Y(.08)), (X(.6), Y(.4)), (X(.9), Y(.86)), (X(.1), Y(.86)), (X(.4), Y(.4))], fill=col)
        d.rectangle([X(.34), Y(.04), X(.66), Y(.12)], fill=col)
        d.polygon([(X(.26), Y(.66)), (X(.74), Y(.66)), (X(.84), Y(.82)), (X(.16), Y(.82))], fill=WHITE)
    elif kind == "person":
        d.ellipse([X(.34), Y(.08), X(.66), Y(.4)], fill=col)
        d.pieslice([X(.16), Y(.46), X(.84), Y(1.14)], 180, 360, fill=col)
    elif kind == "cloud":
        d.ellipse([X(.1), Y(.4), X(.46), Y(.78)], fill=col)
        d.ellipse([X(.3), Y(.16), X(.74), Y(.66)], fill=col)
        d.ellipse([X(.56), Y(.36), X(.92), Y(.78)], fill=col)
        d.rectangle([X(.28), Y(.5), X(.74), Y(.78)], fill=col)
    elif kind == "tag":
        d.polygon([(X(.08), Y(.46)), (X(.5), Y(.06)), (X(.94), Y(.06)), (X(.94), Y(.5)), (X(.52), Y(.92))], fill=col)
        d.ellipse([X(.68), Y(.18), X(.82), Y(.32)], fill=WHITE)
    elif kind == "wafer":
        d.ellipse([X(.08), Y(.08), X(.92), Y(.92)], fill=col)
        d.rectangle([X(.45), Y(.08), X(.55), Y(.92)], fill=WHITE)
        d.rectangle([X(.08), Y(.45), X(.92), Y(.55)], fill=WHITE)
    elif kind == "pkg":
        d.rounded_rectangle([X(.14), Y(.14), X(.86), Y(.86)], 3 * S, fill=col)
        d.rounded_rectangle([X(.3), Y(.3), X(.7), Y(.7)], 2 * S, fill=WHITE)
        for i in range(4):
            v = .24 + .17 * i
            d.ellipse([X(v) - 2 * S, Y(.8) - 2 * S, X(v) + 2 * S, Y(.8) + 2 * S], fill=col)
    elif kind == "hub":
        for a in range(6):
            ang = a * math.pi / 3
            d.line([X(.5), Y(.5), X(.5 + .4 * math.cos(ang)), Y(.5 + .4 * math.sin(ang))], fill=col, width=lw)
            d.ellipse([X(.5 + .4 * math.cos(ang)) - 4 * S, Y(.5 + .4 * math.sin(ang)) - 4 * S, X(.5 + .4 * math.cos(ang)) + 4 * S, Y(.5 + .4 * math.sin(ang)) + 4 * S], fill=col)
        d.ellipse([X(.32), Y(.32), X(.68), Y(.68)], fill=col)


# 節點定義：(標籤, 圖示)；L1 每臂一個，L2 每臂兩個，L3（只在網頁左右兩臂）一個
_ARMS_W = [  # (角度, L1, [L2 兩個], L3 或 None)
    (60, ("上游", "hub"), [("IC 設計", "chip"), ("記憶體", "ram")], None),
    (0, ("中游", "wafer"), [("晶圓代工", "wafer"), ("封測", "pkg")], ("載板", "pcb")),
    (300, ("下游", "rack"), [("伺服器", "rack"), ("光通訊", "wave")], None),
    (240, ("客戶", "person"), [("雲端大廠", "cloud"), ("品牌商", "tag")], None),
    (180, ("零組件", "pcb"), [("PCB", "pcb"), ("散熱", "fins")], ("電源", "bolt")),
    (120, ("製造", "gear"), [("設備", "tool"), ("材料", "flask")], None),
]
_ARMS_M = [
    (90, ("上游", "hub"), [("IC 設計", "chip"), ("記憶體", "ram")], None),
    (30, ("中游", "wafer"), [("晶圓代工", "wafer")], None),
    (-30, ("下游", "rack"), [("伺服器", "rack")], None),
    (-90, ("客戶", "person"), [("雲端大廠", "cloud"), ("品牌商", "tag")], None),
    (-150, ("零組件", "pcb"), [("散熱", "fins")], None),
    (150, ("製造", "gear"), [("設備", "tool")], None),
]
_SNOW_COLS = [SKY, PINK, MINT, LEMON, PURP, (250, 196, 150)]
_SNOW = {}
_SNOW_P = {"w": dict(sx=1.4, sy=0.85, r1=200, r2=330, r3=400, fk=18), "m": dict(sx=1.0, sy=1.0, r1=150, r2=320, r3=0, fk=20)}


def _node_size(label, web, lvl):
    fs = {0: 54 if web else 46, 1: 38 if web else 30, 2: 30 if web else 24, 3: 30 if web else 24}[lvl]
    f = _fr(fs)
    ic = 0 if lvl == 0 else int(fs * 1.05)
    w = text_w(f, label) + 2 * (16 if web else 12) + (ic + 8 if ic else 0)
    return f, fs, ic, int(w), int(fs + (26 if web else 18))


def _snow_nodes(web):
    """回傳節點清單：每個 dict(id, parent, lvl, label, kind, cx, cy, w, h, color, order)；座標以中心點為原點的偏移（呼吸時整體放大）。"""
    key = "w" if web else "m"
    if key in _SNOW:
        return _SNOW[key]
    arms = _ARMS_W if web else _ARMS_M
    P = dict(_SNOW_P["w"] if web else _SNOW_P["m"])
    pol = lambda ang, r: (r * P["sx"] * math.cos(math.radians(ang)), -r * P["sy"] * math.sin(math.radians(ang)))
    N = []

    def add(parent, lvl, label, kind, pos, color, order):
        f, fs, ic, w, h = _node_size(label, web, lvl)
        N.append(dict(id=len(N), parent=parent, lvl=lvl, label=label, kind=kind, cx=pos[0], cy=pos[1], w=w, h=h, f=f, fs=fs, ic=ic, color=color, order=order))
        return len(N) - 1
    add(-1, 0, "產業", None, (0, 0), (255, 224, 120), 0)
    for ai, (ang, l1, l2s, l3) in enumerate(arms):
        col = _SNOW_COLS[ai]
        p1 = add(0, 1, l1[0], l1[1], pol(ang, P["r1"]), col, ai)
        for j, (lab, kd) in enumerate(l2s):
            sgn = 0 if len(l2s) == 1 else (-1 if j == 0 else 1)
            rr = P["r2"]
            add(p1, 2, lab, kd, pol(ang + sgn * P["fk"], rr), col, ai * 2 + j)
        if l3:
            add(p1, 3, l3[0], l3[1], pol(ang, P["r3"]), col, ai)
    _SNOW[key] = N
    return N


_SPR = {}


def _node_sprite(n, web):
    k = (n["label"], web)
    if k in _SPR:
        return _SPR[k]
    w, h, S = n["w"], n["h"], SS
    lay = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([1, 1, w * S - 2, h * S - 2], (14 if n["lvl"] else 22) * S, fill=n["color"], outline=(110, 120, 140), width=3 * S)
    x = 16 if web else 12
    if n["lvl"] == 0:
        tw = text_w(n["f"], n["label"])
        d.text((w * S / 2, h * S / 2), n["label"], font=ImageFont_scaled(n["f"], S), fill=INK, anchor="mm")
    else:
        ic = n["ic"]
        _ico(d, n["kind"], x, (h - ic) / 2, ic, (70, 82, 108))
        d.text(((x + ic + 8) * S, h * S / 2 - 1 * S), n["label"], font=ImageFont_scaled(n["f"], S), fill=INK, anchor="lm")
    im = lay.resize((w, h), Image.LANCZOS)
    _SPR[k] = im
    return im


def ImageFont_scaled(f, S):
    return font(f.path, int(f.size * S))


def _snow_draw(cv, L, t, web):
    zx0, zy0, zx1, zy1 = _zone(L)
    cx, cy = (zx0 + zx1) / 2, (zy0 + zy1) / 2 + (0 if web else 8)
    N = _snow_nodes(web)
    br = 1.0 + 0.035 * ease_io(clamp((t - 1.0) / 0.5, 0, 1)) * (0.5 + 0.5 * math.sin((t - 1.0) * 2.6))   # 長好之後輕輕呼吸（只放大不縮小，節點間距只增不減）
    d = ImageDraw.Draw(cv)
    pos = [(cx + n["cx"] * br, cy + n["cy"] * br) for n in N]
    # 連線先畫（生長動畫：從父節點往子節點延伸）
    for n in N[1:]:
        t0 = 0.08 + 0.3 * (n["lvl"] - 1) + 0.04 * n["order"] * (0.7 if n["lvl"] > 1 else 1)
        u = ease_out((t - t0) / 0.3)
        if u <= 0:
            continue
        a, b = pos[n["parent"]], pos[n["id"]]
        e = (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)
        d.line([a, e], fill=(150, 162, 188), width=5 if n["lvl"] == 1 else 4)
    for n in N:
        t0 = 0.0 if n["lvl"] == 0 else 0.08 + 0.3 * (n["lvl"] - 1) + 0.04 * n["order"] * (0.7 if n["lvl"] > 1 else 1) + 0.18
        u = back_out((t - t0) / 0.28)
        if u <= 0.02:
            continue
        sp = _node_sprite(n, web)
        s = clamp(u, 0.2, 1.08)
        if abs(s - 1) > 0.005:
            sp = sp.resize((max(2, int(n["w"] * s)), max(2, int(n["h"] * s))), Image.BILINEAR)
        x, y = pos[n["id"]]
        cv.paste(sp, (int(x - sp.width / 2), int(y - sp.height / 2)), sp)
        C.reg(f"node{n['id']}", (x - n["w"] / 2, y - n["h"] / 2, x + n["w"] / 2, y + n["h"] / 2))


# ---- 月曆 ------------------------------------------------------------------------------------
def _coin(d, cx, cy, r, ch="配"):
    S = SS
    d.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], fill=(255, 205, 70), outline=(214, 150, 30), width=int(max(2, r * .12) * S))
    d.ellipse([(cx - r * .72) * S, (cy - r * .72) * S, (cx + r * .72) * S, (cy + r * .72) * S], outline=(240, 170, 40), width=int(max(1, r * .07) * S))
    d.text((cx * S, (cy + 1) * S), ch, font=font(B.F_ROUND, int(r * 1.05 * S)), fill=(150, 90, 10), anchor="mm")


MONTH_STEP = 0.1      # 每個月亮起的間隔（秒）。12 個月 × 0.1 = 1.2 秒；前 1.5 秒內全亮


def _calendar(cv, L, t, web):
    zx0, zy0, zx1, zy1 = _zone(L)
    cols, rows = (4, 3) if web else (3, 4)
    gap = 18
    cw = (zx1 - zx0 - gap * (cols - 1)) / cols
    ch = (zy1 - zy0 - gap * (rows - 1)) / rows
    fm = _fr(76 if web else 58)
    fq = _fr(70 if web else 54)
    d = ImageDraw.Draw(cv)
    for k in range(12):
        c, r_ = k % cols, k // cols
        x0, y0 = zx0 + c * (cw + gap), zy0 + r_ * (ch + gap)
        u = ease_out((t - 0.02 * k) / 0.25)
        if u <= 0:
            continue
        cell = (x0, y0, x0 + cw, y0 + ch)
        tl = 0.2 + MONTH_STEP * k                              # 這個月亮起的時間
        lit = t >= tl
        w, h = int(cw), int(ch)
        S = SS
        lay = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
        ld = ImageDraw.Draw(lay)
        fill = (255, 243, 200) if lit else WHITE
        edge = (236, 176, 60) if lit else (140, 160, 190)
        ld.rounded_rectangle([2 * S, 2 * S, (w - 2) * S, (h - 2) * S], 18 * S, fill=fill, outline=edge, width=4 * S)
        ld.rounded_rectangle([2 * S, 2 * S, (w - 2) * S, 30 * S], 18 * S, fill=(252, 196, 200) if not lit else (255, 214, 120))
        ld.rectangle([4 * S, 18 * S, (w - 4) * S, 30 * S], fill=(252, 196, 200) if not lit else (255, 214, 120))
        for j in range(2):                                    # 月曆吊環
            xx = w * (0.3 + 0.4 * j)
            ld.rounded_rectangle([(xx - 4) * S, -2 * S, (xx + 4) * S, 14 * S], 4 * S, fill=(150, 160, 185))
        ld.text((w * 0.07 * S, (h * 0.58) * S), f"{k + 1}月", font=ImageFont_scaled(fm, S), fill=(70, 62, 40) if lit else (90, 100, 120), anchor="lm")
        ccx, ccy, rr = w * 0.80, h * 0.62, min(w * 0.13, h * 0.2)
        if lit:
            dt = t - tl
            fall = ease_out(dt / 0.22)
            bounce = 0 if dt > 0.4 else -10 * math.sin(clamp((dt - 0.22) / 0.18, 0, 1) * math.pi)
            yy = ccy - (1 - fall) * (h * 0.62) + bounce
            # 金幣只在格子內掉落（用格子大小的圖層裁掉，不會跑到別格）
            _coin(ld, ccx, yy, rr)
            if dt < 0.5:                                       # 落地小火花
                for q in range(4):
                    ang = q * math.pi / 2 + .5
                    rd = rr * (1.2 + 1.2 * dt / 0.5)
                    ld.ellipse([(ccx + rd * math.cos(ang) - 3) * S, (ccy + rd * math.sin(ang) * .6 - 3) * S, (ccx + rd * math.cos(ang) + 3) * S, (ccy + rd * math.sin(ang) * .6 + 3) * S], fill=(255, 200, 60))
        else:
            if int(t * 5 + k) % 3 != 0:                       # 問號閃爍
                ld.text((ccx * S, ccy * S), "?", font=ImageFont_scaled(fq, S), fill=(224, 100, 120), anchor="mm")
        im = lay.resize((w, h), Image.LANCZOS)
        if u < 1:
            im = im.resize((max(2, int(w * u)), max(2, int(h * u))), Image.BILINEAR)
        cv.paste(im, (int(x0 + (w - im.width) / 2), int(y0 + (h - im.height) / 2)), im)
        C.reg(f"cal{k}", cell)


def opening_fn(kind):
    """0-1～0-3 痛點開場：kind 1＝六個內容不同的小視窗（K 線、走勢、圓餅、財報、排行、熱力圖）飛入疊滿；
    kind 2＝雪花狀（放射）產業鏈，節點寫族群名稱＋小圖示，往外分層長出；kind 3＝12 個月月曆逐月亮起、金幣掉入。"""
    cfg = {1: ("看盤資訊太多？", "太多", "alarm", "開好幾個 App，好累…"),
           2: ("產業怎麼看懂？", "看懂", "magnifier", "上下游一堆名字看不懂"),
           3: ("ETF 怎麼配現金流？", "現金流", "piggy", "每個月想領息怎麼排？")}[kind]

    def fn(cv, t, shot):
        L = shot.L
        web = L.fmt == "web"
        center_head(cv, L, cfg[0], t, cfg[1], y=26 if web else MHEAD_Y, px=None if web else 72)
        zx0, zy0, zx1, zy1 = _zone(L)
        if kind == 1:
            cols, rows = (3, 2) if web else (2, 3)
            gap = 22
            w = (zx1 - zx0 - gap * (cols - 1)) / cols
            h = (zy1 - zy0 - gap * (rows - 1)) / rows
            for k in range(6):
                c, r_ = k % cols, k // cols
                x0, y0 = zx0 + c * (w + gap), zy0 + r_ * (h + gap)
                u = ease_out((t - 0.07 * k) / 0.45)
                if u <= 0:
                    continue
                tl = max(0.0, t - 0.07 * k)
                im = _window_img(k, int(w), int(h), tl + k)
                if cols == 3 and c == 1:                       # 網頁中間欄：彈出放大
                    s = clamp(back_out((t - 0.07 * k) / 0.4), 0.2, 1.06)
                    im = im.resize((int(w * s), int(h * s)), Image.BILINEAR)
                    px_, py_ = x0 + (w - im.width) / 2, y0 + (h - im.height) / 2
                    full = s >= 0.995 and s <= 1.005 or u >= 1
                else:                                           # 左欄從左、右欄從右飛入
                    off = (-(w + 240) if c == 0 else (w + 240)) * (1 - u)
                    px_, py_ = x0 + off, y0
                    full = u >= 1
                cv.paste(im, (int(px_), int(py_)), im)
                if u >= 1:
                    C.reg(f"win{k}", (x0, y0, x0 + w, y0 + h))
        elif kind == 2:
            _snow_draw(cv, L, t, web)
        else:
            _calendar(cv, L, t, web)
        _host(cv, L, cfg[2], cfg[3], t)
    return _push(fn)



def logo_fn():
    """0-4：LOGO 60%→105%→100%，比比用頭頂開布幕。"""
    def fn(cv, t, shot):
        L = shot.L
        web = L.fmt == "web"
        cx, cy, lg_px = (960, 380, 380) if web else (MCX, 700, 420)
        if t < 0.35:
            s = 0.6 + (1.05 - 0.6) * ease_out(t / 0.35)
        else:
            s = 1.05 - 0.05 * ease_io((t - 0.35) / 0.25)
        px = max(8, int(lg_px * s))
        lg = logo_sized(px)
        cv.paste(lg, (int(cx - px / 2), int(cy - px / 2)), lg)
        C.reg("logo", (cx - lg_px * 0.53, cy - lg_px * 0.53, cx + lg_px * 0.53, cy + lg_px * 0.53))
        f = font(THEME["title_font"], 110 if web else 112)
        tw = text_w(f, "哩股哩股")
        ty = cy + lg_px * 0.55 + 20
        a = ease_out((t - 0.3) / 0.3)
        d = ImageDraw.Draw(cv)
        if a > 0:
            d.rounded_rectangle([cx - tw / 2 - 8, ty + f.size * 0.8, cx - tw / 2 + (tw + 16) * a, ty + f.size * 1.1], 12, fill=LEMON)
            d.text((cx - tw / 2, ty), "哩股哩股", font=f, fill=THEME["ink"])
        C.reg("title", (cx - tw / 2 - 8, ty, cx + tw / 2 + 8, ty + f.size * 1.15))
        _host(cv, L, "reveal", "這些我都整理好了！", t)
    return _push(fn)


def _body_rect(name, idx, foot, size):
    """比比本體的外框（不含頭上的名牌）：名牌與身體之間有一排全透明列，取那排以下。"""
    import numpy as np
    info = B.bibi_index()[name]
    al = np.array(Image.open(info["frames"][idx]).convert("RGBA"))[..., 3] > 40
    rows = al.sum(1)
    ys = np.where(rows > 0)[0]
    top = int(ys[0])
    gaps = [y for y in range(int(ys[0]), int(ys[-1])) if rows[y] == 0]
    if gaps:
        top = next(y for y in range(gaps[-1], int(ys[-1]) + 1) if rows[y] > 0)
    xs = np.where(al[top:].sum(0) > 0)[0]
    sz = int(round(size / 4) * 4)
    s = sz / 512
    return (foot[0] + (int(xs[0]) - 248) * s, foot[1] + (top - 482) * s, foot[0] + (int(xs[-1]) - 248) * s, foot[1] + (int(ys[-1]) - 482) * s)


def intro4_fn():
    """0-5：比比自我介紹（名牌是素材內建）；泡泡在比比旁邊、尾巴指向比比身體（不指名牌），不壓名牌。
    素材 intro 第 8～11 格（0.6～1.2 秒）右前掌舉起揮動，違反四腳原則，改用第 12 格（掌放下）頂替。"""
    def fn(cv, t, shot):
        L = shot.L
        web = L.fmt == "web"
        center_head(cv, L, "認識比比", t, "比比", y=26 if web else MHEAD_Y, px=None if web else 72)
        fi = anim_frame("intro", t, "hold")
        if 7 <= fi <= 10:
            fi = 11
        nfr = len(B.bibi_index()["intro"]["frames"])
        if web:
            size, foot = 640, (760, 1040)
        else:
            size = 700
            ur0 = sprite_union_rect("intro", range(nfr), (0, 1280), size)
            gw = (ur0[2] - ur0[0]) + 13 + 34 + 330
            foot = (MCX - gw / 2 - ur0[0], 1280)
        ROLE[0] = "bibi"
        put_sprite(cv, "intro", fi, foot, size)
        if t >= 0.6:
            ur = sprite_union_rect("intro", range(nfr), foot, size)
            lines = ["我是比比，", "帶你逛一圈！"]
            if web:
                bw, bh = 420, 2 * 52 + 40
                tip = (ur[2] + 13, (ur[1] + ur[3]) / 2 - 60)
                x0 = tip[0] + 34
                rect = (x0, tip[1] - bh / 2, x0 + bw, tip[1] + bh / 2)
                bubble_box(cv, lines, rect, tip, t, 42, t0=0.6)
            else:
                br = _body_rect("intro", 15, foot, size)
                bw, bh = 330, 2 * 52 + 40
                tip = (max(ur[2], br[2]) + 13, (br[1] + br[3]) / 2)
                x0 = tip[0] + 34
                rect = (x0, tip[1] - bh / 2, x0 + bw, tip[1] + bh / 2)
                bubble_box(cv, lines, rect, tip, t, 42, t0=0.6)
    return _push(fn)


def grid4_fn(srcs_w, srcs_m):
    """5-3：3D 四宮格（每格只裁 3D 畫布，素材從分鏡指定的來源秒往後播）；比比在四宮格外側，不壓任何一格畫布。"""
    def fn(cv, t, shot):
        L = shot.L
        web = L.fmt == "web"
        srcs = srcs_w if web else srcs_m
        if web:
            cw, ch, gap, lab = 646, 347, 12, 46
            x0 = 380
            y0 = 66
        else:
            # 每格＝整張 3D 畫布（1142×1076 → 寬高比 1.06），左右編號圓點與整個模型都入格；四格整組水平置中、垂直置中於安全區
            gap, lab = 12, 46
            cw = 394
            ch = 371
            x0 = MCX - (2 * cw + gap) // 2
            y0 = 290
        for k, (clip, name, win, st0) in enumerate(srcs):
            col, row = k % 2, k // 2
            cx = x0 + col * (cw + gap)
            cy = y0 + row * (ch + lab + gap)
            src = reader(clip).get(st0 + t)
            ww, wh = win[2] - win[0], win[3] - win[1]
            ar = cw / ch
            if ww / wh > ar:
                nh = ww / ar
                win2 = (win[0], (win[1] + win[3]) / 2 - nh / 2, win[2], (win[1] + win[3]) / 2 + nh / 2)
            else:
                nw = wh * ar
                win2 = ((win[0] + win[2]) / 2 - nw / 2, win[1], (win[0] + win[2]) / 2 + nw / 2, win[3])
            u = ease_out(t / 0.35)
            im = src.resize((cw, ch), Image.LANCZOS, box=win2).convert("RGBA")
            im.putalpha(rounded_mask(cw, ch, 14))
            ImageDraw.Draw(im).rounded_rectangle([1, 1, cw - 2, ch - 2], 14, outline=R.DEEP + (255,), width=2)
            ox = (cx + cw / 2 - (x0 + cw + gap / 2)) * (1 - u) * -0.0
            cv.paste(im, (int(cx + ox), cy + lab), im)
            C.reg("site", (cx, cy + lab, cx + cw, cy + lab + ch), role="site")
            f = font(THEME["pill_font"], 24)
            lw = text_w(f, name) + 32
            lay = Image.new("RGBA", (int(lw) + 4, 30), (0, 0, 0, 0))
            ld = ImageDraw.Draw(lay)
            ld.rounded_rectangle([0, 0, lw, 28], THEME["pill_radius"] or 14, fill=THEME["pill_bg"] + (255,))
            ld.text((16, 1), name, font=f, fill=THEME["pill_fg"])
            cv.paste(lay, (cx, cy + 2), lay)
            C.reg("label:" + name, (cx, cy + 2, cx + lw, cy + 30))
        from v3_core import footnote4
        pw = R.pill(cv, "產業地圖", L.pill_xy[0], L.pill_xy[1], px=L.pill_px)
        L.head_xy = (L.pill_xy[0] + pw + (36 if web else 30), L.head_y)
        R.headline(cv, L, "還有更多 3D", t, "更多")
        _host(cv, L, "face_surprise_happy", "封裝、HBM、液冷都能轉", t)
        footnote4(cv, L)
    return _push(fn, 0.02)


def end4_fn():
    """14-1 片尾：LOGO → 兩行大字 → 膠囊「搜尋 哩股哩股」；不放網址、信箱。"""
    def fn(cv, t, shot):
        L = shot.L
        web = L.fmt == "web"
        W = L.W
        cx = W / 2 if web else MCX
        lg_px = 260 if web else 380
        cy = 200 if web else 560
        s = 1.0 + 0.03 * ease_io(t / 3.0)
        px = int(lg_px * s)
        lg = logo_sized(px)
        cv.paste(lg, (int(cx - px / 2), int(cy - px / 2)), lg)
        C.reg("logo", (cx - lg_px * 0.52, cy - lg_px * 0.52, cx + lg_px * 0.52, cy + lg_px * 0.52))
        f = font(THEME["head_font"], 76 if web else 80)
        y = cy + lg_px * 0.55 + 30
        for i, ln in enumerate(["產業看得懂", "現金流排得出來"]):
            a = ease_out((t - 0.2 - 0.2 * i) / 0.3)
            tw = text_w(f, ln)
            if a > 0:
                R.float_panel(cv, (cx - tw / 2 - 24, y, cx + tw / 2 + 24, y + f.size * 1.3 + 6), int(235 * a), 18)
                ImageDraw.Draw(cv).text((cx - tw / 2, y + 2), ln, font=f, fill=THEME["ink"])
            C.reg(f"echo{i}", (cx - tw / 2 - 24, y, cx + tw / 2 + 24, y + f.size * 1.3 + 6))
            y += f.size * 1.3 + 22
        b = ease_out((t - 0.7) / 0.3)
        pxp = 40 if web else 46
        f2 = font(THEME["pill_font"], pxp)
        w1 = text_w(f2, "搜尋 哩股哩股") + 44
        if b > 0:
            R.pill(cv, "搜尋 哩股哩股", cx - w1 / 2, y + 10, bg=WHITE, fg=THEME["ink"], px=pxp, stroke=False, alpha=b)
        _host(cv, L, "celebrate", "我們網站見！", t)
    return _push(fn)


def disclaimer4_fn():
    """15-1 警語：網頁、手機都改成「整塊內容垂直置中」；手機面板寬 800（x 140～940，水平置中且不進右側 Reels 介面區），原文一字不改。"""
    def fn(cv, t, shot):
        L = shot.L
        web = L.fmt == "web"
        W, H = L.W, L.H
        cx = W / 2 if web else MCX
        a = ease_io(t / 0.3)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        lg_px = 130 if web else 150
        fs = font(B.F_MED, 28 if web else 26)
        note = B.SPONSOR_NOTE
        maxw = 1500 if web else 800
        nl = [note] if text_w(fs, note) <= maxw else [note[:len(note) // 2 + 1], note[len(note) // 2 + 1:]]
        pw = 1400 if web else 800
        f = font(B.F_MED, 44 if web else 42)
        lines = []
        for para in B.DISCLAIMER:
            cur = ""
            for ch in para:
                if text_w(f, cur + ch) > pw - 100 and cur:
                    lines.append(cur)
                    cur = ""
                cur += ch
            lines.append(cur)
            lines.append("")
        lines = lines[:-1]
        lh = f.size * 1.5
        ph = len(lines) * lh + 90
        nh = 36 * len(nl)
        total = lg_px + 24 + nh + 40 + ph
        zone_h = H if web else 1600          # 手機底部 320px 是 Reels 介面區，垂直置中算到 y=1600
        top = max(24, (zone_h - total) / 2)
        lg = logo_sized(lg_px)
        lay.paste(lg, (int(cx - lg_px / 2), int(top)), lg)
        C.reg("logo", (cx - lg_px / 2, top, cx + lg_px / 2, top + lg_px))
        ny = top + lg_px + 24
        for i, ln in enumerate(nl):
            tw = text_w(fs, ln)
            d.text((cx - tw / 2, ny + i * 36), ln, font=fs, fill=(80, 80, 80))
        C.reg("note", (cx - maxw / 2, ny, cx + maxw / 2, ny + nh))
        py0 = ny + nh + 40
        d.rounded_rectangle([cx - pw / 2, py0, cx + pw / 2, py0 + ph], 30, fill=WHITE, outline=R.DEEP, width=3)
        C.reg("panel", (cx - pw / 2, py0, cx + pw / 2, py0 + ph))
        y = py0 + 45
        for ln in lines:
            if ln:
                d.text((cx - text_w(f, ln) / 2, y), ln, font=f, fill=(26, 26, 26))
            y += lh if ln else lh * 0.45
        if a < 1:
            lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a)))
        cv.paste(lay, (0, 0), lay)
    return _push(fn, 0.02)
