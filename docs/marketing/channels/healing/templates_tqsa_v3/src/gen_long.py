#!/usr/bin/env python3
"""首篇「長版」2 頁（Andy 2026-11-06：版本 A 長文做 1～2 頁）。沿用 gen.py 的 CSS／色票機制、illus.py 的細線工具，
LOGO 沿用 gen_first.py 的圖片字標做法。三色系：奶油晨光、晝版、黑白混搭（第 1 頁黑底＝礙、第 2 頁白底＝晴）。
用法：python3 gen_long.py && node render_long.js && python3 contrast_long.py && python3 sheets_long.py"""
import json, os, sys, re, html
B = os.path.dirname(os.path.abspath(__file__))
src = open(B + "/gen.py", encoding="utf-8").read().rsplit("\nmain()", 1)[0]
exec(compile(src, "gen.py", "exec"))
import illus as I
from illus import *
LDIR = os.path.abspath(os.path.join(B, "..", "..", "logo_tqsa4_晴時多雲", "02_三道光"))
PAL.clear(); PAL.update({
 "晝版": {"bg": "#F6F1E8", "bg2": "#FBF8F1", "dark": "#E4DCCD", "face": "#EEE7DA", "face3": "#FBF8F1", "line": "#6E6A66", "lamp": "#D9822B", "text": "#2F2D2B", "sub": "#5C5753", "hint": "#9C530C", "cloudtxt": "#5F5B57", "glow": ".42", "glow2": ".6", "grain": ".08"},
 "奶油晨光": {"bg": "#FFF6E5", "bg2": "#FFFBF2", "dark": "#EFE1C6", "face": "#FAEFD8", "face3": "#FFFBF2", "line": "#7A746E", "lamp": "#D9822B", "text": "#3A3A3A", "sub": "#5C5753", "hint": "#9C530C", "cloudtxt": "#5F5B57", "glow": ".42", "glow2": ".6", "grain": ".07"},
 # 黑白混搭：只用黑白灰。第 1 頁黑底（礙），第 2 頁白底（晴）。光點：黑底＝淺灰＋白光暈；白底＝中灰（不做全黑實心太陽）
 "黑白_1": {"bg": "#0E0E0E", "bg2": "#1B1B1B", "dark": "#070707", "face": "#1D1D1D", "face3": "#2D2D2D", "line": "#E4E4E4", "lamp": "#E8E8E8", "text": "#F5F5F5", "sub": "#BDBDBD", "hint": "#FFFFFF", "cloudtxt": "#E4E4E4", "glow": ".5", "glow2": ".75", "grain": ".05"},
 "黑白_2": {"bg": "#FFFFFF", "bg2": "#FFFFFF", "dark": "#E4E4E4", "face": "#F1F1F1", "face3": "#FFFFFF", "line": "#111111", "lamp": "#8A8A8A", "text": "#111111", "sub": "#3A3A3A", "hint": "#4A4A4A", "cloudtxt": "#111111", "glow": ".22", "glow2": ".34", "grain": ".03"},
})
LOGO_FILE = {"晝版": "字標_透明_晝版.png", "奶油晨光": "字標_透明_奶油晨光.png", "黑白_1": B + "/logo_mono_白.png", "黑白_2": B + "/logo_mono_黑.png"}
def logo_img(theme):
    f = LOGO_FILE[theme]; f = f if os.path.isabs(f) else os.path.join(LDIR, f)
    return '<img src="file://%s" style="height:72px;display:block">' % f

# ───────── 插圖（viewBox 888×H）─────────
def towers(x0, base, specs, op=1.0):
    o = ''
    for i, (dx, w, h) in enumerate(specs):
        x = x0 + dx
        o += R(x, base - h, w, h, 1, at("var(--w-face3)", 2.2, op=op))
        for r in range(int((h - 16) // 18)):
            for c in range(int((w - 8) // 14)):
                if (r * 3 + c * 5 + i) % 4: continue
                o += '<rect x="%.1f" y="%.1f" width="6" height="8" fill="var(--w-line)" opacity=".35"/>' % (x + 6 + c * 14, base - h + 10 + r * 18)
        if i % 2 == 0: o += Ln(x + w / 2, base - h, x + w / 2, base - h - 12, at("none", 2, op=.7))
    return o

def sc_room():
    """礙：小租屋房間——疊起的搬家紙箱、桌上一疊帳單、圈著繳租日的月曆、窗外遠方高樓；一盞小檯燈是唯一暖光。H=340"""
    fl = 316
    o = glow(790, 190, 150)
    # 窗與窗外遠方高樓、淡淡的雲
    o += R(300, 18, 250, 214, 6, DK) + R(310, 28, 230, 194, 3, at("none", 1.6, op=.55))
    inner = R(312, 30, 226, 190, 2, at("var(--w-face)", 0)) + cloud(380, 120, 120, 48, 61, "var(--w-face3)", free=True) + wisp(430, 64, 90, .4)
    inner += towers(318, 220, [(0, 30, 70), (38, 24, 110), (70, 36, 90), (116, 26, 130), (150, 34, 80), (190, 28, 100)], .9)
    inner += Ln(436, 30, 436, 220, at("none", 1.4, op=.0)) + Ln(500, 36, 534, 70, at("none", 1.4, op=.18))
    o += clip_rect(312, 30, 226, 190, inner) + R(312, 30, 226, 190, 2, at("none", SW)) + Ln(425, 30, 425, 220, at("none", 2, op=.7))
    o += R(290, 232, 270, 16, 4, F3) + hatch(300, 250, 250, 14, 10, at("none", 1.1, op=.25))
    # 搬家紙箱三疊（租屋一換再換）
    for (x, y, w, h, k) in ((24, fl - 84, 190, 84, 0), (44, fl - 84 - 74, 150, 74, 1), (60, fl - 84 - 74 - 64, 118, 64, 2)):
        o += R(x, y, w, h, 3, F1) + R(x, y, w, 14, 3, F3)
        o += Ln(x + w / 2 - 16, y, x + w / 2 - 16, y + h, at("none", 1.8, op=.6)) + Ln(x + w / 2 + 16, y, x + w / 2 + 16, y + h, at("none", 1.8, op=.6))
        o += R(x + w - 54, y + h - 34, 38, 22, 2, at("none", 1.4, op=.55)) + Ln(x + w - 48, y + h - 24, x + w - 24, y + h - 24, at("none", 1.2, op=.45))
        o += Ln(x + 12, y + h - 14, x + 52, y + h - 14, at("none", 1.2, op=.4))
    o += P('M96 %d q 20 -16 40 0' % (fl - 84 - 74 - 64 - 2), at("none", 1.5, op=.5))      # 最上箱的提手洞
    # 地板
    o += Ln(14, fl, 874, fl, at("none", SW)) + hatch(30, fl + 2, 820, 18, 11, at("none", 1.1, op=.25))
    # 月曆（圈著繳租日）掛在牆上，不用繩子：貼牆
    cx, cy = 626, 36
    o += R(cx, cy, 120, 124, 6, F3) + R(cx, cy, 120, 28, 6, DK) + Ln(cx + 24, cy - 6, cx + 24, cy + 8, at("none", 3)) + Ln(cx + 96, cy - 6, cx + 96, cy + 8, at("none", 3))
    for r in range(4):
        for c in range(5): o += '<circle cx="%.1f" cy="%.1f" r="2.6" fill="var(--w-line)" opacity=".55"/>' % (cx + 18 + c * 21, cy + 50 + r * 22)
    o += C(cx + 18 + 3 * 21, cy + 50 + 2 * 22, 12, at("none", 2.6, "var(--w-line)"))
    # 書桌：桌面、兩腳、陰影
    o += R(600, 262, 270, 14, 3, F1) + Ln(612, 276, 612, fl, at("none", SW)) + Ln(858, 276, 858, fl, at("none", SW)) + R(612, 282, 246, 10, 0, at("none", 1.4, op=.4))
    # 一疊帳單
    for i in range(4):
        o += R(630 + (i % 2) * 5, 262 - 12 * (i + 1), 96, 12, 2, F3 if i % 2 else F1) + Ln(640 + (i % 2) * 5, 262 - 12 * (i + 1) + 6, 690 + (i % 2) * 5, 262 - 12 * (i + 1) + 6, at("none", 1.3, op=.5))
    o += R(738, 242, 44, 20, 2, F1) + Ln(744, 252, 774, 252, at("none", 1.2, op=.45))
    # 小檯燈（唯一暖光）
    o += E(826, 260, 26, 5, F3) + Ln(826, 255, 826, 205, at("none", 3.4)) + P('M826 205 q -22 -4 -36 -22', at("none", 3.4))
    o += P('M770 182 Q 800 130 838 182 Z', LP) + Ln(770, 182, 838, 182, at("none", SW)) + halo_rings(802, 160, 12, 1)
    o += poly([(772, 184), (838, 184), (780, 262), (860, 262)], at("var(--w-lamp)", 0, op=.07))
    return o

def sc_dusk():
    """晴：窗前書桌——窗外一段夕陽（暖光）、手機上的對話泡泡、小存錢罐、一碗冒熱氣的晚餐、窗台一株小芽。H=480"""
    o = glow(444, 190, 190)
    # 窗
    o += R(170, 14, 548, 306, 8, DK) + R(184, 28, 520, 278, 4, at("none", 1.8, op=.6))
    panes = [(192, 36, 250, 120), (446, 36, 250, 120), (192, 160, 250, 130), (446, 160, 250, 130)]
    sunx, suny = 444, 262
    for i, (x, y, w, h) in enumerate(panes):
        inner = R(x, y, w, h, 2, at("var(--w-face)", 0))
        if i == 0: inner += cloud(x + 120, y + 96, 170, 70, 71, "var(--w-face3)", free=True) + wisp(x + 20, y + 30, 100, .4)
        if i == 1: inner += cloud(x + 130, y + 80, 160, 64, 73, "var(--w-face3)", free=True) + wisp(x + 130, y + 26, 100, .4)
        inner += Ln(x + w - 60, y + 6, x + w - 18, y + 46, at("none", 1.3, op=.16))
        if i >= 2:
            sp = [(4, 34, 60), (42, 26, 98), (74, 38, 72), (118, 28, 110), (150, 36, 66), (190, 28, 88)] if i == 2 else [(20, 34, 76), (58, 28, 64), (90, 38, 104), (134, 28, 70), (166, 36, 96), (206, 30, 60)]
            inner += towers(x, 290, sp, .85)
        o += clip_rect(x, y, w, h, inner) + R(x, y, w, h, 2, at("none", SW))
    # 夕陽（半圓落在遠樓之間，窗框之上）：用窗內裁切
    sun = clip_rect(192, 160, 504, 130, C(sunx, 296, 62, LP) + C(sunx, 296, 82, at("none", 1.6, "var(--w-lamp)", op=.7)) + C(sunx, 296, 104, at("none", 1.3, "var(--w-lamp)", op=.45, dash="3 9")) + rays(sunx, 296, 112, 220, 205, 335, 15, at("none", 1.2, "var(--w-lamp)", op=.4)))
    o += sun + R(192, 160, 504, 130, 2, at("none", SW)) + Ln(444, 36, 444, 290, at("none", 2, op=.6)) + Ln(192, 156, 696, 156, at("none", 2, op=.6))
    # 窗台與小芽
    o += R(150, 308, 588, 18, 4, F3) + hatch(166, 328, 556, 14, 10, at("none", 1.1, op=.25))
    o += P('M236 308 H276 L270 276 H242 Z', F1) + Ln(240, 288, 272, 288, at("none", 1.3, op=.5)) + Ln(256, 276, 256, 246, at("none", 2.6))
    o += P('M256 252 q -30 -4 -34 -34 q 30 0 34 34 Z', F3) + P('M256 262 q 28 -6 32 -34 q -28 2 -32 34 Z', F3)
    # 桌面
    dy = 410
    o += Ln(30, dy, 858, dy, at("none", SW)) + R(30, dy, 828, 20, 0, F1) + Ln(30, dy + 20, 858, dy + 20, THIN) + hatch(60, dy + 22, 770, 40, 12, at("none", 1.1, op=.24))
    # 手機（靠著一本小書，螢幕上一個對話泡泡）
    o += '<g transform="rotate(-7 128 %d)">' % dy + R(90, dy - 150, 76, 150, 10, F3) + R(98, dy - 140, 60, 126, 4, DK) \
        + R(104, dy - 122, 38, 22, 8, at("var(--w-face3)", 1.8)) + P('M110 %d l -4 8 l 12 -4' % (dy - 100), at("var(--w-face3)", 1.8)) \
        + R(116, dy - 84, 36, 18, 8, at("none", 1.6, op=.7)) + Ln(124, dy - 75, 144, dy - 75, at("none", 1.2, op=.5)) + Ln(110, dy - 112, 134, dy - 112, at("none", 1.2, op=.5)) + '</g>'
    # 存錢罐
    px = 296
    o += E(px, dy - 34, 62, 40, F3) + C(px + 56, dy - 40, 24, F3) + R(px + 62, dy - 38, 20, 16, 6, F1) + P('M%d %d q -8 -12 2 -16 q 10 4 6 16 Z' % (px + 44, dy - 62), F1) \
        + Ln(px - 22, dy - 72, px + 18, dy - 72, at("none", 3.4)) + P('M%d %d q -22 -4 -18 -24 q 8 10 4 8' % (px - 60, dy - 40), at("none", 2.4)) \
        + R(px - 34, dy - 4, 22, 14, 3, F1) + R(px + 14, dy - 4, 22, 14, 3, F1) + C(px + 56, dy - 46, 2.6, at("var(--w-line)", 0)) + P('M%d %d q 40 12 80 0' % (px - 40, dy - 20), at("none", 1.3, op=.4))
    # 一碗冒熱氣的晚餐
    bx = 600
    o += P('M%d %d H%d C%d %d %d %d %d %d C%d %d %d %d %d %d Z' % (bx - 76, dy - 56, bx + 76, bx + 72, dy - 8, bx + 40, dy - 2, bx, dy - 2, bx - 40, dy - 2, bx - 72, dy - 8, bx - 76, dy - 56), F3) \
        + E(bx, dy - 56, 76, 12, DK) + P('M%d %d q 76 12 152 0' % (bx - 76, dy - 34), at("none", 1.3, op=.45)) + R(bx - 26, dy - 4, 52, 6, 2, F1) \
        + C(bx - 24, dy - 60, 6, at("var(--w-face3)", 1.2)) + C(bx + 10, dy - 58, 6, at("var(--w-face3)", 1.2)) + C(bx + 38, dy - 61, 5, at("var(--w-face3)", 1.2)) \
        + steam(bx - 30, dy - 70, 54, .6) + steam(bx + 6, dy - 72, 44, .5) + steam(bx + 40, dy - 70, 50, .55)
    o += Ln(bx + 96, dy - 52, bx + 150, dy - 14, at("none", 3.2)) + Ln(bx + 110, dy - 56, bx + 162, dy - 18, at("none", 3.2))
    return o
LONG_SC = {"room": (sc_room, 340, 340), "dusk": (sc_dusk, 480, 480)}
def scene_long(name, top):
    fn, H, VH = LONG_SC[name]; I._uid[0] = 0
    defs = ('<radialGradient id="gl"><stop offset="0" stop-color="var(--w-lamp)" stop-opacity="1"/><stop offset="1" stop-color="var(--w-lamp)" stop-opacity="0"/></radialGradient>')
    return ('<div data-o="illus" class="illus" style="top:%dpx;width:888px;height:%dpx"><svg width="888" height="%d" viewBox="0 0 888 %d" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg"><defs>%s</defs><g id="ink">%s</g></svg></div>' % (top, H, H, VH, defs, fn()))

# ───────── 頁面 ─────────
def para(lines, key=None):
    return "<br>".join(html.escape(l) for l in lines)
P1 = ["我們是一個觀察者。", "看這一代年輕人怎麼生活：", "薪水追不上房價，租屋一換再換；", "長輩問什麼時候結婚、生小孩，我們還在算下個月的房租；", "大家都說台灣在成長，但多數人的日子，好像沒有跟著變輕。"]
P1b = ["這些是「礙」。我們不美化，也不抱怨，只是把它說清楚。", "說清楚了，才知道不是自己不夠努力。"]
P2 = ["下班路上的一段夕陽、朋友傳來的一句「我懂」、", "存款終於多了一點點、今天的晚餐剛好很好吃。", "日子很硬，這一代還是很會在縫裡找光。"]
P2b = ["這裡每天說一點礙，也談一點晴。"]
P2_hint = "你今天的一小段晴是什麼？"
BODY = "font-size:32px;line-height:46px;color:var(--w-sub);white-space:pre-wrap;overflow-wrap:anywhere;line-break:strict"
def long_page(n, theme):
    p = PAL[theme]; W, H = 1080, 1350
    o = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><style>:root{--W:%dpx;--H:%dpx;%s}%s .hintuse{font-weight:700}</style></head><body>' % (W, H, css_vars(p), CSS), GRAIN % (W, H, W, H)]
    o.append('<div data-o="lab" class="abs lab" style="left:96px;top:96px">觀察者手記</div><div data-o="pg" class="abs lab" style="right:96px;top:96px">%d／2</div>' % n)
    o.append('<div data-o="logo" class="abs" style="right:96px;top:1196px;line-height:72px">%s</div>' % logo_img(theme))
    if n == 1:
        o.append(scene_long("room", 176))
        o.append('<div data-o="main" class="m" style="top:566px;font-size:64px;line-height:80px">談晴，也說礙</div>')
        o.append('<div data-o="small" class="s" style="top:690px">說這一代的難，也說還在的光。</div>')
        o.append('<div class="abs" style="left:96px;top:772px;width:888px;display:flex;flex-direction:column;gap:40px"><div data-o="body1" style="%s">%s</div><div data-o="body2" style="%s">%s</div></div>' % (BODY, para(P1), BODY, para(P1b)))
        o.append('<div data-o="foot" class="abs lab" style="left:96px;top:1222px">往右滑 →</div>')
    else:
        o.append(scene_long("dusk", 176))
        o.append('<div data-o="main" class="m" style="top:700px;font-size:64px;line-height:80px">但我們也看見「晴」</div>')
        o.append('<div class="abs" style="left:96px;top:822px;width:888px;display:flex;flex-direction:column;gap:40px"><div data-o="body1" style="%s">%s</div><div data-o="body2" style="%s">%s<br><span class="hintuse">%s</span></div></div>' % (BODY, para(P2), BODY, para(P2b), P2_hint))
        o.append('<div data-o="foot" class="abs lab cta" style="left:96px;top:1222px">傳給一個也在撐的朋友 →</div>')
    return "".join(o) + "</body></html>"
# body2 的 top：body1 之下留 40px（空一行），行數依字寬量；由 render 前先用 PIL 估，再由 render 檢查驗證
from PIL import ImageFont as _IF
_SANS = _IF.truetype("/root/.fonts/NotoSansCJKtc-Regular.otf", 100)
def nlines(lines, size=32, spacing=.04, W=888):
    t = 0
    for l in lines:
        w = _SANS.getlength(l) * size / 100 + len(l) * spacing * size
        t += 1 if w <= W else 2
    return t
def body2_top(n):
    return (732 + 46 * nlines(P1) if n == 1 else 822 + 46 * nlines(P2)) + 40
mf = []
os.makedirs(B + "/tmp", exist_ok=True)
for out, themes in (("奶油晨光", ("奶油晨光", "奶油晨光")), ("晝版", ("晝版", "晝版")), ("黑白混搭", ("黑白_1", "黑白_2"))):
    for n in (1, 2):
        th = themes[n - 1]; h = long_page(n, th)
        hd = os.path.join(B, "html", out, "長版"); os.makedirs(hd, exist_ok=True); hp = os.path.join(hd, f"{n}.html"); open(hp, "w", encoding="utf-8").write(h)
        od = os.path.join(OUT, "首篇_長版2頁", out); os.makedirs(od, exist_ok=True)
        mf.append(dict(html=os.path.relpath(hp, B), png=os.path.relpath(os.path.join(od, f"{n}.png"), B), W=1080, H=1350, key=f"首篇_長版2頁/{out}/{n}", safe=None))
json.dump(mf, open(B + "/manifest_long.json", "w"), ensure_ascii=False, indent=1); print("頁數", len(mf))
