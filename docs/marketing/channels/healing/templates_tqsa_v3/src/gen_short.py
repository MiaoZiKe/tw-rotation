#!/usr/bin/env python3
"""首篇短版 3 張（依 research_字數版面色系.md：大標 72～88px、內文 40～44px、行距 1.5、每行 ≤20 字、
封面插圖 55～65%、內頁 40～50%、頁尾 ≥30px；文字不用「我／我們」）。沿用 gen_long.py 的色票、LOGO、插圖工具。
色系：晝版、奶油晨光。用法：python3 gen_short.py && node render_short.js && python3 contrast_short.py && python3 sheets_short.py"""
import json, os, re, html
B = os.path.dirname(os.path.abspath(__file__))
_src = open(B + "/gen_long.py", encoding="utf-8").read().split("# ───────── 頁面")[0]
exec(compile(_src, "gen_long.py", "exec"))
for k in ("黑白_1", "黑白_2"): PAL.pop(k, None)

def box(x, y, w, h):
    o = R(x, y, w, h, 3, F1) + R(x, y, w, 14, 3, F3)
    o += Ln(x + w / 2 - 16, y, x + w / 2 - 16, y + h, at("none", 1.8, op=.6)) + Ln(x + w / 2 + 16, y, x + w / 2 + 16, y + h, at("none", 1.8, op=.6))
    o += R(x + w - 54, y + h - 34, 38, 22, 2, at("none", 1.4, op=.55)) + Ln(x + w - 48, y + h - 24, x + w - 24, y + h - 24, at("none", 1.2, op=.45))
    return o + Ln(x + 12, y + h - 14, x + 52, y + h - 14, at("none", 1.2, op=.4))

def sc_room_tall():
    """礙：小租屋房間（直式放大版，888×560）。"""
    fl = 506
    o = glow(790, 330, 170)
    o += R(290, 28, 270, 304, 6, DK) + R(300, 38, 250, 284, 3, at("none", 1.6, op=.55))
    inner = R(302, 40, 246, 280, 2, at("var(--w-face)", 0)) + cloud(380, 120, 130, 52, 61, "var(--w-face3)", free=True) + wisp(420, 66, 100, .4) + wisp(330, 100, 80, .3)
    inner += towers(302, 320, [(6, 34, 130), (46, 28, 196), (78, 40, 150), (124, 30, 236), (158, 36, 140), (198, 32, 176)], .9)
    inner += Ln(500, 46, 540, 92, at("none", 1.4, op=.18))
    o += clip_rect(302, 40, 246, 280, inner) + R(302, 40, 246, 280, 2, at("none", SW)) + Ln(425, 40, 425, 320, at("none", 2, op=.7)) + Ln(302, 190, 548, 190, at("none", 2, op=.7))
    o += R(270, 332, 310, 18, 4, F3) + hatch(284, 352, 280, 16, 10, at("none", 1.1, op=.25))
    for (x, y, w, h) in ((16, fl - 104, 232, 104), (38, fl - 104 - 92, 188, 92), (58, fl - 104 - 92 - 80, 148, 80), (76, fl - 104 - 92 - 80 - 62, 112, 62)): o += box(x, y, w, h)
    o += Ln(14, fl, 874, fl, at("none", SW)) + hatch(30, fl + 2, 820, 22, 11, at("none", 1.1, op=.25))
    cx, cy = 624, 64
    o += R(cx, cy, 140, 150, 6, F3) + R(cx, cy, 140, 32, 6, DK) + Ln(cx + 28, cy - 6, cx + 28, cy + 10, at("none", 3)) + Ln(cx + 112, cy - 6, cx + 112, cy + 10, at("none", 3))
    for r in range(4):
        for c in range(5): o += '<circle cx="%.1f" cy="%.1f" r="3" fill="var(--w-line)" opacity=".55"/>' % (cx + 22 + c * 24, cy + 60 + r * 26)
    o += C(cx + 22 + 3 * 24, cy + 60 + 2 * 26, 14, at("none", 2.8, "var(--w-line)"))
    dt = 396
    o += R(590, dt, 284, 16, 3, F1) + Ln(604, dt + 16, 604, fl, at("none", SW)) + Ln(860, dt + 16, 860, fl, at("none", SW))
    o += R(618, dt + 26, 228, 64, 4, F1) + Ln(700, dt + 58, 764, dt + 58, at("none", 3)) + C(732, dt + 58, 4, at("var(--w-line)", 0))
    for i in range(5):
        o += R(612 + (i % 2) * 6, dt - 14 * (i + 1), 112, 14, 2, F3 if i % 2 else F1) + Ln(624 + (i % 2) * 6, dt - 14 * (i + 1) + 7, 686 + (i % 2) * 6, dt - 14 * (i + 1) + 7, at("none", 1.3, op=.5))
    o += R(736, dt - 24, 48, 24, 2, F1) + Ln(742, dt - 12, 778, dt - 12, at("none", 1.2, op=.45))
    o += E(830, dt - 2, 28, 5, F3) + Ln(830, dt - 6, 830, dt - 100, at("none", 3.4)) + P('M830 %d q -24 -4 -40 -24' % (dt - 100), at("none", 3.4))
    o += P('M768 %d Q 800 %d 842 %d Z' % (dt - 124, dt - 180, dt - 124), LP) + Ln(768, dt - 124, 842, dt - 124, at("none", SW)) + halo_rings(804, dt - 150, 14, 1)
    o += poly([(770, dt - 122), (842, dt - 122), (780, dt - 2), (868, dt - 2)], at("var(--w-lamp)", 0, op=.07))
    return o

def sc_dusk_tall(E_=80):
    """晴：窗前書桌夕陽（放高版，888×560）。"""
    e = E_
    o = glow(444, 190 + e // 2, 190)
    o += R(170, 14, 548, 306 + e, 8, DK) + R(184, 28, 520, 278 + e, 4, at("none", 1.8, op=.6))
    panes = [(192, 36, 250, 120 + e), (446, 36, 250, 120 + e), (192, 160 + e, 250, 130), (446, 160 + e, 250, 130)]
    for i, (x, y, w, h) in enumerate(panes):
        inner = R(x, y, w, h, 2, at("var(--w-face)", 0))
        if i == 0: inner += cloud(x + 120, y + 96, 170, 70, 71, "var(--w-face3)", free=True) + wisp(x + 20, y + 30, 100, .4) + wisp(x + 110, y + 150, 110, .3)
        if i == 1: inner += cloud(x + 130, y + 80, 160, 64, 73, "var(--w-face3)", free=True) + wisp(x + 130, y + 26, 100, .4) + cloud(x + 70, y + 150, 100, 40, 75, "var(--w-face3)", free=True)
        inner += Ln(x + w - 60, y + 6, x + w - 18, y + 46, at("none", 1.3, op=.16))
        if i >= 2:
            sp = [(4, 34, 60), (42, 26, 98), (74, 38, 72), (118, 28, 110), (150, 36, 66), (190, 28, 88)] if i == 2 else [(20, 34, 76), (58, 28, 64), (90, 38, 104), (134, 28, 70), (166, 36, 96), (206, 30, 60)]
            inner += towers(x, 290 + e, sp, .85)
        o += clip_rect(x, y, w, h, inner) + R(x, y, w, h, 2, at("none", SW))
    sy = 296 + e
    o += clip_rect(192, 160 + e, 504, 130, C(444, sy, 62, LP) + C(444, sy, 82, at("none", 1.6, "var(--w-lamp)", op=.7)) + C(444, sy, 104, at("none", 1.3, "var(--w-lamp)", op=.45, dash="3 9")) + rays(444, sy, 112, 220, 205, 335, 15, at("none", 1.2, "var(--w-lamp)", op=.4)))
    o += R(192, 160 + e, 504, 130, 2, at("none", SW)) + Ln(444, 36, 444, 290 + e, at("none", 2, op=.6)) + Ln(192, 156 + e, 696, 156 + e, at("none", 2, op=.6))
    o += R(150, 308 + e, 588, 18, 4, F3) + hatch(166, 328 + e, 556, 14, 10, at("none", 1.1, op=.25))
    o += '<g transform="translate(0 %d)">' % e + P('M236 308 H276 L270 276 H242 Z', F1) + Ln(240, 288, 272, 288, at("none", 1.3, op=.5)) + Ln(256, 276, 256, 246, at("none", 2.6)) + P('M256 252 q -30 -4 -34 -34 q 30 0 34 34 Z', F3) + P('M256 262 q 28 -6 32 -34 q -28 2 -32 34 Z', F3) + '</g>'
    dy = 410 + e
    o += Ln(30, dy, 858, dy, at("none", SW)) + R(30, dy, 828, 20, 0, F1) + Ln(30, dy + 20, 858, dy + 20, THIN) + hatch(60, dy + 22, 770, 28, 12, at("none", 1.1, op=.24))
    o += '<g transform="rotate(-7 128 %d)">' % dy + R(90, dy - 150, 76, 150, 10, F3) + R(98, dy - 140, 60, 126, 4, DK) + R(104, dy - 122, 38, 22, 8, at("var(--w-face3)", 1.8)) + P('M110 %d l -4 8 l 12 -4' % (dy - 100), at("var(--w-face3)", 1.8)) + R(116, dy - 84, 36, 18, 8, at("none", 1.6, op=.7)) + Ln(124, dy - 75, 144, dy - 75, at("none", 1.2, op=.5)) + Ln(110, dy - 112, 134, dy - 112, at("none", 1.2, op=.5)) + '</g>'
    px = 296
    o += E(px, dy - 34, 62, 40, F3) + C(px + 56, dy - 40, 24, F3) + R(px + 62, dy - 38, 20, 16, 6, F1) + P('M%d %d q -8 -12 2 -16 q 10 4 6 16 Z' % (px + 44, dy - 62), F1) + Ln(px - 22, dy - 72, px + 18, dy - 72, at("none", 3.4)) + P('M%d %d q -22 -4 -18 -24 q 8 10 4 8' % (px - 60, dy - 40), at("none", 2.4)) + R(px - 34, dy - 4, 22, 14, 3, F1) + R(px + 14, dy - 4, 22, 14, 3, F1) + C(px + 56, dy - 46, 2.6, at("var(--w-line)", 0)) + P('M%d %d q 40 12 80 0' % (px - 40, dy - 20), at("none", 1.3, op=.4))
    bx = 600
    o += P('M%d %d H%d C%d %d %d %d %d %d C%d %d %d %d %d %d Z' % (bx - 76, dy - 56, bx + 76, bx + 72, dy - 8, bx + 40, dy - 2, bx, dy - 2, bx - 40, dy - 2, bx - 72, dy - 8, bx - 76, dy - 56), F3) + E(bx, dy - 56, 76, 12, DK) + P('M%d %d q 76 12 152 0' % (bx - 76, dy - 34), at("none", 1.3, op=.45)) + R(bx - 26, dy - 4, 52, 6, 2, F1) + C(bx - 24, dy - 60, 6, at("var(--w-face3)", 1.2)) + C(bx + 10, dy - 58, 6, at("var(--w-face3)", 1.2)) + C(bx + 38, dy - 61, 5, at("var(--w-face3)", 1.2)) + steam(bx - 30, dy - 70, 54, .6) + steam(bx + 6, dy - 72, 44, .5) + steam(bx + 40, dy - 70, 50, .55)
    return o + Ln(bx + 96, dy - 52, bx + 150, dy - 14, at("none", 3.2)) + Ln(bx + 110, dy - 56, bx + 162, dy - 18, at("none", 3.2))

SH_SC = {"gap": (sc_gap, 740, 764), "room": (sc_room_tall, 540, 560), "dusk": (lambda: sc_dusk_tall(20), 500, 500)}
def scene_s(name, top):
    fn, H, VH = SH_SC[name]; I._uid[0] = 0
    defs = '<radialGradient id="gl"><stop offset="0" stop-color="var(--w-lamp)" stop-opacity="1"/><stop offset="1" stop-color="var(--w-lamp)" stop-opacity="0"/></radialGradient>'
    return ('<div data-o="illus" class="illus" style="top:%dpx;width:888px;height:%dpx"><svg width="888" height="%d" viewBox="0 0 888 %d" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg"><defs>%s</defs><g id="ink">%s</g></svg></div>' % (top, H, H, VH, defs, fn()))

BODY = "font-size:40px;line-height:60px;color:var(--w-text);white-space:pre-wrap;overflow-wrap:anywhere;line-break:strict"
def lines(ls): return "<br>".join(html.escape(l) for l in ls)
def short_page(n, theme):
    p = PAL[theme]; W, H = 1080, 1350
    o = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><style>:root{--W:%dpx;--H:%dpx;%s}%s .hintuse{font-weight:700}</style></head><body>' % (W, H, css_vars(p), CSS), GRAIN % (W, H, W, H)]
    o.append('<div data-o="lab" class="abs lab" style="left:96px;top:96px">觀察者手記</div><div data-o="pg" class="abs lab" style="right:96px;top:96px">%d／3</div>' % n)
    o.append('<div data-o="logo" class="abs" style="right:96px;top:1196px;line-height:72px">%s</div>' % logo_img(theme))
    M = 'class="m" style="top:%dpx;font-size:%dpx;line-height:%dpx"'
    if n == 1:
        o.append(scene_s("gap", 176))
        o.append('<div data-o="main" ' + M % (960, 80, 100) + '>談晴，也說礙</div>')
        o.append('<div data-o="small" class="s" style="top:1100px;font-size:40px;line-height:56px">說這一代的難，也說還在的光。</div>')
        o.append('<div data-o="foot" class="abs lab" style="left:96px;top:1222px">往右滑 →</div>')
    elif n == 2:
        o.append(scene_s("room", 176))
        o.append('<div data-o="main" ' + M % (756, 72, 88) + '>這一代的「礙」</div>')
        o.append('<div data-o="body1" class="abs" style="left:96px;top:884px;width:888px;%s">%s</div>' % (BODY, lines(["薪水追不上房價，", "租屋一換再換。", "被問何時結婚，心裡在算房租。", "經濟在成長，日子卻沒變輕。"])))
    else:
        o.append(scene_s("dusk", 176))
        o.append('<div data-o="main" ' + M % (724, 72, 88) + '>也有「晴」</div>')
        o.append('<div class="abs" style="left:96px;top:852px;width:888px;display:flex;flex-direction:column;align-items:flex-start;gap:32px"><div data-o="body1" style="%s">%s</div><div data-o="body2" style="%s;font-weight:700;color:var(--w-hint)">今天的一小段晴是什麼？</div></div>' % (BODY, lines(["下班路上的一段夕陽，", "朋友傳來一句「辛苦了」。", "日子很硬，光還在縫裡。", "一起觀察，一起往晴的那邊走。"]), BODY))
        o.append('<div data-o="foot" class="abs lab cta" style="left:96px;top:1222px">傳給一個也在撐的朋友 →</div>')
    return "".join(o) + "</body></html>"

mf = []
os.makedirs(B + "/tmp", exist_ok=True)
for th in ("晝版", "奶油晨光"):
    for n in (1, 2, 3):
        hd = os.path.join(B, "html", th, "短版"); os.makedirs(hd, exist_ok=True); hp = os.path.join(hd, f"{n}.html"); open(hp, "w", encoding="utf-8").write(short_page(n, th))
        od = os.path.join(OUT, "首篇_短版3張", th); os.makedirs(od, exist_ok=True)
        mf.append(dict(html=os.path.relpath(hp, B), png=os.path.relpath(os.path.join(od, f"{n}.png"), B), W=1080, H=1350, key=f"首篇_短版3張/{th}/{n}", safe=None))
json.dump(mf, open(B + "/manifest_short.json", "w"), ensure_ascii=False, indent=1); print("頁數", len(mf))
