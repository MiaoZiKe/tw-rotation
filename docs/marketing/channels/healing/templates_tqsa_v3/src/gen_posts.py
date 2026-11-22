#!/usr/bin/env python3
"""談晴說礙 說明型貼文（3 張：封面＋2 內頁，晝版，1080×1350）。沿用首篇短版版型（gen_short.py）：
LOGO 左上、右下頁碼小太陽＋淡橘實心點 40%＋箭頭（最後一頁無箭頭）、圖上一行出處（data-o="src"）。
封面字 ≤20、內頁字 ≤50；不用「我／我們」；圖上不放叫人做事的話。
用法：python3 gen_posts.py <佇列資料夾名> [...] && node render_posts.js <同上> && python3 contrast_posts.py <同上>
輸出：docs/marketing/channels/healing/queue/<名>/1～3.png；HTML 在 src/html/posts/<名>/。"""
import json, os, sys, html
B = os.path.dirname(os.path.abspath(__file__))
_src = open(B + "/gen_short.py", encoding="utf-8").read().split("\nmf = []")[0]
exec(compile(_src, "gen_short.py", "exec"))
QUEUE = os.path.abspath(os.path.join(B, "..", "..", "queue"))
SVGTXT = "font-family:'Noto Sans CJK TC',sans-serif;letter-spacing:.02em"
def scene_x(svg, H, top, VH=None):
    VH = VH or H
    I._uid[0] = 0
    defs = '<radialGradient id="gl"><stop offset="0" stop-color="var(--w-lamp)" stop-opacity="1"/><stop offset="1" stop-color="var(--w-lamp)" stop-opacity="0"/></radialGradient>'
    return ('<div data-o="illus" class="illus" style="top:%dpx;width:888px;height:%dpx"><svg width="888" height="%d" viewBox="0 0 888 %d" preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg"><defs>%s</defs><g id="ink">%s</g></svg></div>' % (top, H, H, VH, defs, svg))


# ───────── 插圖（2026-11-10 Andy：依每篇內容量身畫、有數據就畫圖表、素材不跨篇重複；用過的登記在 ../../素材登記.md）─────────
def T(x, y, t, fs=30, w=400, col="var(--w-sub)", anchor="middle"):
    return '<text x="%.1f" y="%.1f" text-anchor="%s" style="%s;font-size:%dpx;font-weight:%d;color:%s" fill="currentColor">%s</text>' % (x, y, anchor, SVGTXT, fs, w, col, html.escape(t))
HL = at("var(--w-lamp)", 2.2, "var(--w-lamp)", op=.9)          # 重點長條（晴光橘）

def sc_hbars(items, vmax, H, ticks=None, tickfmt="%g", hi=(), ref=None, reflab="", lw=230, bh=None):
    """橫條圖（等比例，0 起算）：items=[(標籤, 數值, 數值文字)]；hi＝要用晴光橘的列；ref＝直向虛線參考值。"""
    n = len(items); x0 = lw; x1 = 740; top = 70 if ref is not None else 20; bot = H - (70 if ticks else 20)
    rowh = (bot - top) / n; bh = bh or min(76, rowh * .52)
    sx = lambda v: x0 + (x1 - x0) * v / vmax
    o = ""
    if ticks:
        for t in ticks:
            o += Ln(sx(t), top - 10, sx(t), bot, at("none", 1.2, op=.25, dash="3 7")) + T(sx(t), bot + 46, tickfmt(t) if callable(tickfmt) else tickfmt % t, 30)
    for i, (lab, v, vt) in enumerate(items):
        cy = top + rowh * (i + .5)
        o += T(x0 - 22, cy + 11, lab, 32, 400, "var(--w-text)", "end")
        o += R(x0, cy - bh / 2, sx(v) - x0, bh, 6, HL if i in hi else F3)
        lx = sx(v) + 16
        if ref is not None and sx(v) < sx(ref) + 8 and lx + 24 * len(vt) > sx(ref) - 8: lx = sx(ref) + 16   # 標籤會被參考線穿過 → 移到線右邊
        o += T(lx, cy + 13, vt, 38, 700, "var(--w-text)", "start")
    o += Ln(x0, top - 16, x0, bot, at("none", SW))
    if ref is not None:
        o += Ln(sx(ref), top - 8, sx(ref), bot, at("none", 2.6, "var(--w-lamp)", dash="12 10")) + T(sx(ref), top - 24, reflab, 30, 700, "var(--w-text)")
    return o

def sc_vbars(items, vmax, H, ref=None, reflab="", hi=()):
    """直條圖（等比例）：items=[(標籤, 數值, 數值文字, 只知上限?)]；只知上限的畫成虛線框（例：官方只說「低於 3%」）。"""
    base = H - 70; k = (base - 80) / vmax; n = len(items); w = 132; gap = (760 - n * w) / (n - 1)
    o = Ln(40, base, 860, base, at("none", SW))
    for i, (lab, v, vt, cap) in enumerate(items):
        x = 80 + i * (w + gap); h = v * k
        st = at("none", 2.2, dash="8 7") if cap else (HL if i in hi else F3)
        o += R(x, base - h, w, h, 4, st) + T(x + w / 2, (base - h / 2 + 14) if cap else (base - h - 18), vt, 38, 700, "var(--w-text)") + T(x + w / 2, base + 46, lab, 30)
    if ref is not None:
        ry = base - ref * k
        o += Ln(40, ry, 860, ry, at("none", 2.4, "var(--w-lamp)", dash="12 10"))
        o += Ln(560, 40, 620, 40, at("none", 2.4, "var(--w-lamp)", dash="12 10")) + T(636, 51, reflab, 30, 700, "var(--w-text)", "start")   # 圖例放右上，不壓長條標籤
    return o

def sc_ratio_cards(H=760):
    """11/11 封面：兩張對比數字卡。每張卡上一個大數字＋ 10×10 點陣（每 100 位勞動力，四捨五入：整體約 3 位、15–24 歲約 12 位）。
    失業率分母是勞動力（有工作＋正在找工作），不是全部人口，所以寫「每 100 位勞動力」。"""
    o = ""
    for j, (lab, num, n, hi) in enumerate((("整體", "3.36%", 3, False), ("15–24 歲", "11.59%", 12, True))):
        x = 24 + j * 432; y = 20; w = 408; h = 640
        o += R(x, y, w, h, 22, F1 if not hi else at("var(--w-face)", SW, "var(--w-lamp)"))
        o += T(x + w / 2, y + 66, lab, 34, 400, "var(--w-text)") + T(x + w / 2, y + 156, num, 72, 700, "var(--w-text)")
        gx, gy, cs = x + 64, y + 210, 30
        for i in range(100):
            r, c = divmod(i, 10)
            o += C(gx + c * cs + 11, gy + r * cs + 11, 10, HL if i < n else at("none", 1.6, op=.45))
        o += T(x + w / 2, y + h - 34, "約 %d 位失業" % n, 30, 700 if hi else 400, "var(--w-text)")
    o += T(444, H - 30, "每張點陣＝100 位勞動力，約數四捨五入", 30)
    return o

def sc_door(H=560):
    """11/11 第 3 頁：門半開、地上一道光，門把掛著一張空白識別證（第一份工作的第一天）。"""
    fl = H - 60
    o = Ln(30, fl, 858, fl, at("none", SW)) + hatch(44, fl + 2, 800, 18, 11, at("none", 1.1, op=.25))
    o += R(250, 40, 330, fl - 40, 4, F1)                                            # 門框
    o += poly([(266, 56), (564, 56), (564, fl), (266, fl)], at("var(--w-lamp)", 0, op=.16))   # 門後的光
    o += poly([(564, 56), (448, 96), (448, fl - 30), (564, fl)], F3)                 # 半開的門板
    o += Ln(458, 140, 548, 110, at("none", 1.3, op=.4)) + Ln(458, 300, 548, 290, at("none", 1.3, op=.4))
    o += C(470, (fl + 56) / 2, 9, DK)
    o += poly([(266, fl), (448, fl), (700, fl + 50 - 6), (110, fl + 50 - 6)], at("var(--w-lamp)", 0, op=.22))   # 地上的光
    by = (fl + 56) / 2
    o += P('M470 %.1f L440 %.1f L500 %.1f Z' % (by, by + 70, by + 70), at("none", 2))  # 掛繩
    o += R(420, by + 70, 100, 130, 10, F1) + R(436, by + 86, 68, 50, 6, at("none", 1.6, op=.6)) + Ln(436, by + 156, 504, by + 156, at("none", 1.4, op=.5)) + Ln(436, by + 176, 484, by + 176, at("none", 1.4, op=.5))
    o += R(640, fl - 50, 110, 50, 6, F3) + R(650, fl - 66, 90, 18, 4, F1)            # 門邊一雙新鞋盒
    return o

def sc_coins(H=760):
    """11/12 封面：10 疊硬幣由低到高；橘色虛線＝平均。右邊 3 疊把平均拉上去，左邊 7 疊在線下（示意 69.74%，高度非金額比例）。"""
    base, ch = H - 100, 30
    stacks = [3, 4, 4, 5, 5, 6, 6, 9, 12, 16]; avg = sum(stacks) / len(stacks)
    o = ""
    for i, n in enumerate(stacks):
        x = 52 + i * 80; w = 62
        for k in range(n):
            y = base - (k + 1) * ch
            o += R(x, y, w, ch - 3, 10, F3 if k % 2 else F1) + Ln(x + 12, y + (ch - 3) / 2, x + w - 12, y + (ch - 3) / 2, at("none", 1.2, op=.35))
    ay = base - avg * ch
    o += Ln(36, ay, 852, ay, at("none", 3, "var(--w-lamp)", dash="14 10")) + T(52, ay - 18, "平均 47,884 元", 34, 700, "var(--w-text)", "start")
    o += Ln(30, base, 858, base, at("none", SW)) + hatch(44, base + 2, 800, 14, 11, at("none", 1.1, op=.25))
    o += T(52 + 3 * 80 + 31, base + 52, "7 成在平均線以下", 30)
    return o

def sc_payslip(H=560):
    """11/12 第 3 頁：一張薪資單。上兩列（本薪、固定津貼）框進「經常性薪資」，下兩列（加班費、獎金）在框外、虛線。"""
    x, y, w = 200, 30, 488
    o = R(x, y, w, H - 70, 8, F1) + R(x, y, w, 56, 8, F3) + Ln(x + 24, y + 28, x + 200, y + 28, at("none", 1.6, op=.5))
    rows = [("本薪", False), ("固定津貼", False), ("加班費", True), ("獎金", True)]
    for i, (lab, dash) in enumerate(rows):
        ry = y + 100 + i * 96
        if dash: o += R(x + 28, ry, w - 56, 64, 6, at("none", 1.8, dash="7 7", op=.7)) + T(x + 52, ry + 43, lab, 30, 400, "var(--w-sub)", "start")
        else: o += R(x + 28, ry, w - 56, 64, 6, F3) + T(x + 52, ry + 43, lab, 32, 400, "var(--w-text)", "start")
        o += Ln(x + w - 170, ry + 32, x + w - 52, ry + 32, at("none", 1.6, op=.45))
    o += R(x + 12, y + 86, w - 24, 2 * 96 + 0, 10, at("none", 3, "var(--w-lamp)"))
    o += T(x + w + 20, y + 86 + 96 + 12, "經常性", 32, 700, "var(--w-text)", "start") + T(x + w + 20, y + 86 + 96 + 52, "薪資", 32, 700, "var(--w-text)", "start")
    return o

def sc_bento(H=760):
    """11/13 封面：俯視便當（飯、主菜、三格配菜）＋一張吊牌「外食 +3.01%」。"""
    x, y, w, h = 56, 120, 520, 400
    o = R(x - 16, y - 16, w + 32, h + 32, 30, F3) + R(x, y, w, h, 20, F1)
    o += R(x + 24, y + 24, 270, h - 48, 14, F3)                                      # 飯
    for i in range(18): o += E(x + 60 + (i % 6) * 40, y + 70 + (i // 6) * 110 + (i % 2) * 18, 9, 5, at("none", 1.3, op=.45))
    o += R(x + 318, y + 24, 178, 170, 14, F3) + E(x + 407, y + 109, 62, 44, at("var(--w-face)", 2.2)) + P('M%d %d q 30 -18 60 0' % (x + 377, y + 105), at("none", 1.6, op=.6))   # 主菜
    for j in range(2): o += R(x + 318 + j * 92, y + 214, 86, 162, 12, F3) + C(x + 361 + j * 92, y + 295, 22, at("none", 1.8, op=.6))
    o += Ln(x + 560, y + 40, x + 700, y - 20, at("none", 2)) + C(x + 560, y + 40, 6, DK)
    o += P('M%d %d l 30 -26 h 190 v 104 h -190 Z' % (x + 600, y - 4), F1) + C(x + 640, y - 4 - 0, 7, DK)
    o += T(x + 735, y + 10, "外食", 32, 400, "var(--w-text)") + T(x + 735, y + 56, "+3.01%", 36, 700, "var(--w-text)")
    for k in range(3): o += steam(x + 120 + k * 60, y - 24, 60, .55)
    o += Ln(30, y + h + 90, 858, y + h + 90, at("none", SW)) + hatch(44, y + h + 92, 800, 14, 11, at("none", 1.1, op=.25))
    o += Ln(x + 40, y + h + 60, x + 360, y + h + 40, at("none", 4)) + Ln(x + 40, y + h + 76, x + 360, y + h + 56, at("none", 4))   # 筷子
    return o

def sc_months(H=520):
    """11/13 第 3 頁：2026 年 3～12 月月曆格。5～10 月 CPI 年增率高於 2%（晴光橘）；3、4 月 2% 以下（1.2%、1.74%，已查證）；11、12 月尚未公布（虛線）。1、2 月沒查到逐月數字，不畫。"""
    o = ""; cw, chh, gx = 132, 120, 30; x0 = (888 - (5 * cw + 4 * gx)) / 2; y0 = 30
    for i, m in enumerate(range(3, 13)):
        r, c = divmod(i, 5); x = x0 + c * (cw + gx); y = y0 + r * (chh + 70)
        st = HL if 5 <= m <= 10 else (at("none", 2, dash="7 7", op=.6) if m >= 11 else F3)
        o += R(x, y, cw, chh, 12, st) + Ln(x + 28, y - 8, x + 28, y + 14, at("none", 3)) + Ln(x + cw - 28, y - 8, x + cw - 28, y + 14, at("none", 3))
        o += T(x + cw / 2, y + chh / 2 + 14, "%d 月" % m, 34, 700, "var(--w-text)")
    yb = y0 + 2 * (chh + 70) - 20
    for j, (st, lab) in enumerate(((HL, "高於 2%"), (F3, "2% 以下"), (at("none", 2, dash="7 7", op=.6), "尚未公布"))):
        lx = x0 + j * 270
        o += R(lx, yb, 34, 34, 6, st) + T(lx + 50, yb + 28, lab, 30, 400, "var(--w-sub)", "start")
    return o

def envelope(x, y, w, h, st):
    return R(x, y, w, h, 3, st) + P('M%.1f %.1f L%.1f %.1f L%.1f %.1f' % (x + 3, y + 3, x + w / 2, y + h * .58, x + w - 3, y + 3), at("none", 1.6, op=.6))

def sc_envelopes(H=760):
    """11/14 封面：100 封履歷信封排 10×10；48 封是晴光色虛線（想投沒投出去），示意 48.3%。"""
    x0, y0, cw, chh, ew, eh = 74, 70, 76, 54, 58, 38; o = ""
    for i in range(100):
        r, c = divmod(i, 10); x = x0 + c * cw; y = y0 + r * chh
        o += envelope(x, y, ew, eh, at("var(--w-face)", 2, "var(--w-lamp)", dash="5 5") if i < 48 else F3)
    yb = y0 + 10 * chh + 24
    o += Ln(30, yb, 858, yb, at("none", SW)) + hatch(44, yb + 2, 800, 14, 11, at("none", 1.1, op=.25))
    o += envelope(300, yb + 46, 46, 30, at("var(--w-face)", 2, "var(--w-lamp)", dash="5 5")) + T(362, yb + 72, "48.3% 曾不敢投", 30, 400, "var(--w-sub)", "start")
    return o

def sc_plane(H=520):
    """11/14 第 3 頁：左邊一支手機滑著一格格社群動態；右邊一架紙飛機（履歷）沿虛線飛出去。"""
    o = R(80, 40, 230, 430, 30, DK) + R(96, 70, 198, 370, 12, F1)
    for i in range(4):
        y = 86 + i * 88
        o += R(110, y, 170, 74, 8, F3) + C(134, y + 22, 12, at("none", 1.6, op=.6)) + Ln(156, y + 22, 262, y + 22, at("none", 1.4, op=.45)) + Ln(124, y + 52, 250, y + 52, at("none", 1.4, op=.35))
    o += P('M330 330 C 430 300 470 180 560 200 S 700 150 760 90', at("none", 2.4, "var(--w-lamp)", dash="10 10"))
    px, py = 760, 90
    o += poly([(px - 110, py + 40), (px + 40, py - 30), (px - 40, py + 70)], F1) + poly([(px - 40, py + 70), (px + 40, py - 30), (px - 30, py + 110)], F3) + Ln(px - 40, py + 70, px - 30, py + 110, at("none", 2))
    o += Ln(30, H - 30, 858, H - 30, at("none", SW)) + hatch(44, H - 28, 800, 14, 11, at("none", 1.1, op=.25))
    return o

def sc_timeline(H=760):
    """11/15 封面：時間軸 現在→3 年；2.56 年處插一面晴光色小旗；下面一疊日曆。"""
    ay = 470; x0, x1 = 90, 810; yr = (x1 - x0) / 3
    o = Ln(x0, ay, x1 + 30, ay, at("none", SW)) + P('M%d %d l -14 -10 M%d %d l -14 10' % (x1 + 30, ay, x1 + 30, ay), at("none", SW))
    for i, lab in enumerate(["現在", "1 年", "2 年", "3 年"]):
        x = x0 + i * yr; o += Ln(x, ay - 14, x, ay + 14, at("none", SW)) + T(x, ay + 58, lab, 30)
    for j in range(1, 36):
        if j % 12: o += Ln(x0 + j * yr / 12, ay - 6, x0 + j * yr / 12, ay + 6, at("none", 1.2, op=.4))
    sx = x0 + 2.56 * yr
    o += Ln(x0, ay - 6, sx, ay - 6, at("none", 6, "var(--w-lamp)", op=.75)) + Ln(sx, ay, sx, ay - 190, at("none", 3))
    o += P('M%.1f %d h 120 l -26 34 l 26 34 h -120 Z' % (sx, ay - 190), HL) + T(sx, ay - 222, "2.56 年", 44, 700, "var(--w-text)")
    cy0 = ay + 100
    for i in range(3):
        x = 330 + i * 12; y = cy0 + i * 10
        o += R(x, y, 200, 118, 8, F3 if i < 2 else F1) + R(x, y, 200, 30, 8, DK)
    for r in range(3):
        for c in range(6): o += C(384 + c * 26, cy0 + 78 + r * 24, 3.4, at("var(--w-line)", 0, op=.55))
    o += Ln(30, cy0 + 152, 858, cy0 + 152, at("none", SW)) + hatch(44, cy0 + 154, 800, 14, 11, at("none", 1.1, op=.25))
    return o

def sc_rings(items, H=520):
    """11/15 第 3 頁：三個等比例圓環（受訪者勾選比例）。"""
    import math as _m
    o = ""; r = 110
    for i, (lab, v, vt) in enumerate(items):
        cx = 150 + i * 294; cy = 200
        o += C(cx, cy, r, at("none", 26, "var(--w-face)"))
        a = 2 * _m.pi * v / 100; ex, ey = cx + r * _m.sin(a), cy - r * _m.cos(a)
        o += P('M%.1f %.1f A%d %d 0 %d 1 %.1f %.1f' % (cx, cy - r, r, r, 1 if v > 50 else 0, ex, ey), at("none", 26, "var(--w-lamp)", extra='stroke-linecap="butt"'))
        o += C(cx, cy, r + 13, at("none", 1.4, op=.5)) + C(cx, cy, r - 13, at("none", 1.4, op=.5))
        o += T(cx, cy + 14, vt, 40, 700, "var(--w-text)") + T(cx, cy + r + 76, lab, 32, 400, "var(--w-text)")
    return o

def ringpair(cx, cy, r, st1, st2):
    return C(cx - r * .45, cy, r, st1) + C(cx + r * .45, cy, r, st2)

def sc_ringpairs(H=760):
    """11/16 封面：10 組對戒（兩個相扣的圓）排兩列；後 3 組是虛線（示意 2016→2025 結婚登記少 29.4%，近 3 成）。"""
    o = ""; rr = 46
    for i in range(10):
        r, c = divmod(i, 5); cx = 124 + c * 160; cy = 170 + r * 230
        if i < 7: o += ringpair(cx, cy, rr, at("none", 7, "var(--w-lamp)"), at("none", 7))
        else: o += ringpair(cx, cy, rr, at("none", 3, dash="8 8", op=.55), at("none", 3, dash="8 8", op=.55))
    yb = 560
    o += Ln(30, yb, 858, yb, at("none", SW)) + hatch(44, yb + 2, 800, 14, 11, at("none", 1.1, op=.25))
    o += ringpair(140, yb + 92, 22, at("none", 4, "var(--w-lamp)"), at("none", 4)) + T(190, yb + 104, "2025 年仍在", 30, 400, "var(--w-sub)", "start")
    o += ringpair(480, yb + 92, 22, at("none", 2.4, dash="6 6", op=.55), at("none", 2.4, dash="6 6", op=.55)) + T(530, yb + 104, "比 2016 年少的", 30, 400, "var(--w-sub)", "start")
    return o

def sc_cradle(H=560):
    """11/16 第 3 頁：一張空搖籃，旁邊數字吊牌「總生育率 0.695」（數字卡）。"""
    fl = H - 60; o = Ln(30, fl, 858, fl, at("none", SW)) + hatch(44, fl + 2, 800, 18, 11, at("none", 1.1, op=.25))
    o += P('M120 %d Q 300 %d 480 %d' % (fl - 6, fl + 30, fl - 6), at("none", 4))                  # 搖籃底座弧
    o += P('M150 %d L150 %d Q300 %d 450 %d L450 %d Z' % (fl - 240, fl - 70, fl - 20, fl - 70, fl - 240), F1)   # 籃身
    for k in range(6): o += Ln(180 + k * 48, fl - 228, 180 + k * 48, fl - 70 + (12 if 1 < k < 4 else 0), at("none", 1.6, op=.45))
    o += Ln(140, fl - 240, 460, fl - 240, at("none", 5))
    o += P('M300 %d L300 %d' % (fl - 240, fl - 380), at("none", 3)) + P('M300 %d q 70 -10 90 50' % (fl - 380), at("none", 3)) + C(390, fl - 320, 10, DK)   # 吊架
    x, y = 560, 120
    o += R(x, y, 270, 220, 20, at("var(--w-face3)", SW, "var(--w-lamp)")) + T(x + 135, y + 70, "總生育率", 32, 400, "var(--w-text)") + T(x + 135, y + 160, "0.695", 72, 700, "var(--w-text)")
    o += T(x + 135, y + 270, "2025 年", 30)
    return o

def sc_slope(H=760):
    """11/17 封面：斜率圖。左「2026/7 以前 1.775%」→ 右「2026/8 起 0.775%」，等比例（0～2%）。下面一頂學士帽。"""
    y0, y1 = 80, 440; v2y = lambda v: y1 - (y1 - y0) * v / 2.0; xl, xr = 200, 690
    o = Ln(xl, y0 - 20, xl, y1, at("none", 1.6, op=.4)) + Ln(xr, y0 - 20, xr, y1, at("none", 1.6, op=.4)) + Ln(xl - 40, y1, xr + 40, y1, at("none", SW))
    a, b = v2y(1.775), v2y(0.775)
    o += Ln(xl, a, xr, b, at("none", 6, "var(--w-lamp)")) + C(xl, a, 16, at("var(--w-face3)", 4)) + C(xr, b, 16, at("var(--w-lamp)", 0, "var(--w-lamp)"))
    o += T(xl - 30, a + 14, "1.775%", 40, 700, "var(--w-text)", "end") + T(xr + 30, b + 14, "0.775%", 44, 700, "var(--w-text)", "start")
    o += T(xl, y1 + 50, "2026/7 以前", 30) + T(xr, y1 + 50, "2026/8 起", 30)
    cx, cy = 444, 640
    o += poly([(cx - 150, cy - 30), (cx, cy - 90), (cx + 150, cy - 30), (cx, cy + 30)], DK) + P('M%d %d v 46 q 90 40 180 0 v -46' % (cx - 90, cy - 4), F1)
    o += Ln(cx + 120, cy - 40, cx + 120, cy + 40, at("none", 3)) + C(cx + 120, cy + 48, 10, LP)
    return o

def sc_gantt(H=520):
    """11/17 第 2 頁：還款時間軸（甘特條）。舊制：畢業→寬限 1 年→開始還款；新制：寬限 2 年（期間免還本息）。等比例：1 年＝220px。"""
    x0 = 210; yr = 220; o = ""
    for j, (lab, g, hi) in enumerate((("舊制", 1, False), ("新制", 2, True))):
        y = 70 + j * 170
        o += T(x0 - 26, y + 50, lab, 34, 700 if hi else 400, "var(--w-text)", "end")
        o += R(x0, y, g * yr, 72, 10, HL if hi else F3) + T(x0 + g * yr / 2, y + 48, "寬限 %d 年" % g, 32, 700, "var(--w-text)")
        o += R(x0 + g * yr, y, 660 - g * yr - 10, 72, 10, at("none", 2, dash="8 8", op=.6)) + T(x0 + g * yr + 24, y + 48, "開始還款", 30, 400, "var(--w-sub)", "start")
    o += Ln(x0, 40, x0, 340, at("none", SW)) + T(x0, 390, "畢業", 30)
    for k in (1, 2):
        o += Ln(x0 + k * yr, 330, x0 + k * yr, 350, at("none", 2)) + T(x0 + k * yr, 390, "%d 年" % k, 30)
    o += T(444, 470, "寬限期間免還本息（在職專班不適用）", 30)
    return o

def sc_stack(H=560):
    """11/17 第 3 頁：組成（堆疊長條）。基準 1.775% ＝ 學生負擔 0.775% ＋ 政府補貼 1 個百分點；等比例（1% ＝ 360px）。"""
    x0, y, h, k = 120, 120, 110, 360
    a, b = 0.775 * k, 1.0 * k
    o = R(x0, y, a, h, 8, HL) + R(x0 + a, y, b, h, 8, at("var(--w-face3)", SW, dash="10 8"))
    o += T(x0 + a / 2, y + 68, "學生 0.775%", 34, 700, "var(--w-text)") + T(x0 + a + b / 2, y + 68, "政府補貼 1%", 34, 400, "var(--w-text)")
    o += P('M%d %d v -26 h %d v 26' % (x0, y - 20, a + b), at("none", 2)) + T(x0 + (a + b) / 2, y - 60, "基準 1.775%", 32, 700, "var(--w-text)")
    o += R(200, 330, 488, 150, 16, F1) + Ln(232, 380, 520, 380, at("none", 2, op=.5)) + Ln(232, 430, 460, 430, at("none", 2, op=.5)) + C(620, 405, 34, at("none", 3, "var(--w-lamp)")) + T(620, 417, "%", 34, 700, "var(--w-text)")
    return o


# ───────── 11/18～11/22 輪播保底（2026-11-15：影片量產等 TTS 旁白＋Andy 確認樣片，期間每天 20:27 輪播不空窗）─────────
def sc_clock(H=760):
    """11/18 封面：牆上時鐘（指針停在打工下班的 10 點）＋一張吊牌「時薪 205 元」；下方一條地平線。"""
    cx, cy, r = 300, 330, 220
    o = C(cx, cy, r + 18, F3) + C(cx, cy, r, F1)
    import math as _m
    for k in range(12):
        a = _m.pi / 6 * k; x1, y1 = cx + (r - 18) * _m.sin(a), cy - (r - 18) * _m.cos(a); x2, y2 = cx + (r - (44 if k % 3 == 0 else 32)) * _m.sin(a), cy - (r - (44 if k % 3 == 0 else 32)) * _m.cos(a)
        o += Ln(x1, y1, x2, y2, at("none", 4 if k % 3 == 0 else 2))
    o += Ln(cx, cy, cx - 110, cy - 64, at("none", 9, extra='stroke-linecap="round"')) + Ln(cx, cy, cx, cy - 170, at("none", 5, "var(--w-lamp)", extra='stroke-linecap="round"')) + C(cx, cy, 12, DK)
    o += Ln(cx + r - 10, cy - 40, 640, 210, at("none", 2)) + C(cx + r - 10, cy - 40, 6, DK)
    o += P('M600 190 l 30 -26 h 210 v 132 h -210 Z', at("var(--w-face3)", SW, "var(--w-lamp)")) + C(640, 190 - 0, 7, DK)
    o += T(735, 186, "時薪", 34, 400, "var(--w-text)") + T(735, 240, "205 元", 44, 700, "var(--w-text)")
    o += T(735, 380, "2027/1/1 起", 30)
    o += Ln(30, 640, 858, 640, at("none", SW)) + hatch(44, 642, 800, 14, 11, at("none", 1.1, op=.25))
    return o

def sc_split(H=560):
    """11/18 第 3 頁：受惠人數 261.16 萬，一條等比例分段長條（本國 219.72 萬＋移工 41.44 萬）；下方 10 個人形示意（約 8.4：1.6）。"""
    x0, y, h, tot = 70, 60, 110, 261.16; k = 748 / tot
    a, b = 219.72 * k, 41.44 * k
    o = R(x0, y, a, h, 8, HL) + R(x0 + a, y, b, h, 8, at("var(--w-face3)", SW, dash="10 8"))
    o += T(x0 + a / 2, y + 70, "本國 219.72 萬", 36, 700, "var(--w-text)") + T(x0 + a + b / 2, y - 22, "移工 41.44 萬", 30, 400, "var(--w-text)")
    for i in range(10):
        px = 120 + i * 72; py = 330; st = HL if i < 8 else (at("var(--w-face3)", 2, dash="6 6") if i > 8 else at("var(--w-lamp)", 2, op=.45))
        o += C(px, py, 20, st) + P('M%d %d q 30 -60 60 0 v 64 h -60 Z' % (px - 30, py + 86), st)
    o += T(444, 548, "每個人形＝約 26 萬人（示意，約數）", 30)
    return o

def sc_stairs(H=760):
    """11/19 封面：五級階梯，最低一級晴光橘（未滿 25 歲），上面放一張小薪資袋。階高為示意，不是金額比例。"""
    o = ""; x0, base, sw, sh = 70, 600, 150, 92
    for i in range(5):
        x = x0 + i * sw; top = base - (i + 1) * sh
        o += R(x, top, sw, (i + 1) * sh, 4, HL if i == 0 else F3)
    o += Ln(30, base, 858, base, at("none", SW)) + hatch(44, base + 2, 800, 14, 11, at("none", 1.1, op=.25))
    ex, ey = x0 + 22, base - sh - 92
    o += R(ex, ey, 106, 74, 8, F1) + P('M%d %d l 53 34 l 53 -34' % (ex, ey), at("none", 2)) 
    o += T(x0 + sw / 2, base + 56, "未滿 25 歲", 30, 700, "var(--w-text)") + T(x0 + 4 * sw + sw / 2, base + 56, "50–64 歲", 30)
    o += T(x0 + 4 * sw + sw / 2, base - 5 * sh - 26, "階高為示意", 30)
    return o

def sc_lollipop(items, vmax, H=520):
    """11/19 第 3 頁：棒棒糖圖（年增率，0 起算、等比例）。items=[(標籤, 值, 文字, 重點?)]"""
    x0, x1 = 260, 760; sx = lambda v: x0 + (x1 - x0) * v / vmax; o = ""
    for t in (0, 1, 2, 3, 4):
        if t <= vmax: o += Ln(sx(t), 40, sx(t), 330, at("none", 1.2, op=.25, dash="3 7")) + T(sx(t), 380, "%d%%" % t, 30)
    for i, (lab, v, vt, hi) in enumerate(items):
        y = 110 + i * 150
        o += T(x0 - 24, y + 12, lab, 34, 400, "var(--w-text)", "end") + Ln(x0, y, sx(v), y, at("none", 6, "var(--w-lamp)" if hi else "var(--w-line)"))
        o += C(sx(v), y, 26, HL if hi else F3) + T(sx(v) + 44, y + 14, vt, 40, 700, "var(--w-text)", "start")
    o += Ln(x0, 30, x0, 340, at("none", SW)) + T(444, 470, "2026 年 1–7 月，比去年同期", 30)
    return o

def sc_donut(H=760):
    """11/20 封面：一個月收入的圓（等比例），41.46% 晴光橘弧＝房貸月付；圓心放一棟小房子。"""
    import math as _m
    cx, cy, r, v = 444, 380, 230, 41.46
    o = C(cx, cy, r, at("none", 70, "var(--w-face3)"))
    a = 2 * _m.pi * v / 100; ex, ey = cx + r * _m.sin(a), cy - r * _m.cos(a)
    o += P('M%.1f %.1f A%d %d 0 0 1 %.1f %.1f' % (cx, cy - r, r, r, ex, ey), at("none", 70, "var(--w-lamp)", extra='stroke-linecap="butt"'))
    o += C(cx, cy, r + 37, at("none", 1.6, op=.5)) + C(cx, cy, r - 37, at("none", 1.6, op=.5))
    o += poly([(cx - 90, cy - 6), (cx, cy - 86), (cx + 90, cy - 6)], DK) + R(cx - 70, cy - 8, 140, 110, 4, F1) + R(cx - 20, cy + 40, 40, 62, 3, F3)
    o += T(cx, cy + r + 100, "一個月可支配所得", 30) + T(cx + 130, 70, "房貸月付 41.46%", 34, 700, "var(--w-text)", "start")
    return o

def sc_band(H=520):
    """11/20 第 2 頁：內政部房貸負擔率分級帶（0～60%，等比例），標出全國 41.46%。"""
    x0, x1, y, h = 60, 828, 200, 90; sx = lambda v: x0 + (x1 - x0) * v / 60
    bands = [(0, 30, "可合理負擔", F3), (30, 40, "略低", F1), (40, 50, "偏低", at("var(--w-lamp)", SW, op=.45)), (50, 60, "過低", DK)]
    o = ""
    for a, b, lab, st in bands:
        o += R(sx(a), y, sx(b) - sx(a), h, 0, st) + T((sx(a) + sx(b)) / 2, y + h + 50, lab, 30, 400, "var(--w-text)")
    for t in (0, 30, 40, 50, 60):
        o += T(sx(t), y + h + 100, "%d%%" % t + ("+" if t == 60 else ""), 30)
    mx = sx(41.46)
    o += Ln(mx, y - 70, mx, y + h + 10, at("none", 5, "var(--w-lamp)")) + poly([(mx - 16, y - 92), (mx + 16, y - 92), (mx, y - 66)], HL)
    o += T(mx, y - 108, "全國 41.46%", 38, 700, "var(--w-text)")
    o += T(444, 480, "負擔率＝月付房貸 ÷ 月可支配所得（中位數家戶）", 30)
    return o

def sc_key(H=560):
    """11/20 第 3 頁：一把鑰匙掛在掛勾上，鑰匙圈吊牌空白；旁邊一個門牌。"""
    o = Ln(30, 90, 858, 90, at("none", SW)) + R(200, 70, 60, 40, 6, DK) + P('M230 110 v 40 q 0 30 -30 30', at("none", 5))
    o += C(200, 230, 54, at("none", 7)) + C(200, 230, 24, at("var(--w-bg)", 3))
    o += R(248, 220, 280, 22, 6, F3) + R(440, 242, 26, 40, 3, F3) + R(486, 242, 22, 28, 3, F3)
    o += P('M150 200 L110 300 h 80 Z', at("var(--w-face3)", 2.4, "var(--w-lamp)"))
    o += R(600, 160, 220, 150, 14, F1) + R(620, 180, 180, 110, 8, at("none", 2, op=.5)) + C(710, 330, 6, DK)
    o += Ln(30, H - 60, 858, H - 60, at("none", SW)) + hatch(44, H - 58, 800, 14, 11, at("none", 1.1, op=.25))
    return o

def sc_hourglass(H=760):
    """11/21 封面：沙漏，上半沙少、下半沙多；旁邊年份尺 2026 → 2031（精算報告推估：若不撥補，2031 年基金餘額轉負）。"""
    cx = 300
    o = R(cx - 170, 40, 340, 30, 8, DK) + R(cx - 170, 620, 340, 30, 8, DK)
    o += P('M%d 70 C %d 260 %d 300 %d 345 C %d 390 %d 430 %d 620 L %d 620 C %d 430 %d 390 %d 345 C %d 300 %d 260 %d 70 Z' % (cx - 140, cx - 140, cx - 20, cx - 20, cx - 20, cx - 140, cx - 140, cx + 140, cx + 140, cx + 20, cx + 20, cx + 20, cx + 140, cx + 140), F1)
    o += P('M%d 250 C %d 300 %d 320 %d 345 C %d 320 %d 300 %d 250 Z' % (cx - 90, cx - 60, cx - 20, cx, cx + 20, cx + 60, cx + 90), HL)
    o += P('M%d 620 C %d 520 %d 500 %d 490 C %d 500 %d 520 %d 620 Z' % (cx - 138, cx - 120, cx - 40, cx, cx + 40, cx + 120, cx + 138), at("var(--w-lamp)", SW, op=.55))
    o += Ln(cx, 345, cx, 490, at("none", 2, "var(--w-lamp)", dash="4 6"))
    ax = 640
    o += Ln(ax, 100, ax, 600, at("none", SW))
    for i, yr in enumerate(range(2026, 2032)):
        y = 100 + i * 100; hi = yr == 2031
        o += Ln(ax - 14, y, ax + 14, y, at("none", 3)) + T(ax + 34, y + 12, str(yr), 34 if hi else 30, 700 if hi else 400, "var(--w-text)", "start")
    o += C(ax, 600, 14, HL)
    return o

def sc_slope2(H=520):
    """11/21 第 3 頁：斜率圖，未提存精算負債 10.29 兆 → 13.23 兆（0～15 兆等比例）；左上一個存錢筒。"""
    y0, y1 = 60, 400; v2y = lambda v: y1 - (y1 - y0) * v / 15; xl, xr = 330, 640
    o = Ln(xl, y0 - 10, xl, y1, at("none", 1.6, op=.4)) + Ln(xr, y0 - 10, xr, y1, at("none", 1.6, op=.4)) + Ln(xl - 40, y1, xr + 40, y1, at("none", SW))
    a, b = v2y(10.29), v2y(13.23)
    o += Ln(xl, a, xr, b, at("none", 6, "var(--w-lamp)")) + C(xl, a, 16, at("var(--w-face3)", 4)) + C(xr, b, 16, at("var(--w-lamp)", 0, "var(--w-lamp)"))
    o += T(xl - 30, a + 14, "10.29 兆", 38, 700, "var(--w-text)", "end") + T(xr + 30, b + 14, "13.23 兆", 40, 700, "var(--w-text)", "start")
    o += T(xl, y1 + 50, "前一份精算", 30) + T(xr, y1 + 50, "2024 精算", 30)
    o += E(110, 330, 70, 52, F3) + R(96, 272, 30, 8, 3, DK) + C(70, 322, 5, DK) + R(60, 370, 18, 24, 3, F1) + R(140, 370, 18, 24, 3, F1)
    return o

def sc_cups(H=760):
    """11/22 封面：桌上兩杯咖啡、兩張小生日卡（33、31，示意男女平均初婚年齡）。"""
    ty = 520
    o = Ln(30, ty, 858, ty, at("none", SW)) + hatch(44, ty + 2, 800, 14, 11, at("none", 1.1, op=.25))
    for j, (x, age, hi) in enumerate(((220, "31.4", False), (560, "33.4", True))):
        o += P('M%d %d h 150 l -14 160 h -122 Z' % (x - 75, ty - 200), F1 if not hi else at("var(--w-face3)", SW, "var(--w-lamp)"))
        o += P('M%d %d q 46 0 46 44 q 0 44 -46 44' % (x + 72, ty - 170), at("none", SW))
        o += E(x, ty - 200, 75, 14, F3) + R(x - 86, ty - 40, 172, 40, 10, F3)
        for k in range(2): o += steam(x - 20 + k * 40, ty - 230, 60, .55)
        cx = x - 70; cy = 120
        o += R(cx, cy, 140, 110, 10, HL if hi else F3) + T(cx + 70, cy + 72, age, 44, 700, "var(--w-text)")
        o += Ln(cx + 70, cy + 110, x, ty - 260, at("none", 1.6, dash="5 6", op=.5))
    o += T(220, ty + 70, "女性", 30) + T(560, ty + 70, "男性", 30)
    return o

def sc_agesteps(H=560):
    """11/22 第 3 頁：時間軸 25 → 35 歲，一條虛線小路；在 31.4、33.4 歲各插一面旗（等比例）。"""
    x0, x1, ay = 80, 808, 300; sx = lambda v: x0 + (x1 - x0) * (v - 25) / 10
    o = Ln(x0, ay, x1 + 20, ay, at("none", SW))
    for v in range(25, 36):
        o += Ln(sx(v), ay - (14 if v % 5 == 0 else 8), sx(v), ay + (14 if v % 5 == 0 else 8), at("none", 3 if v % 5 == 0 else 1.6))
        if v % 5 == 0: o += T(sx(v), ay + 56, "%d 歲" % v, 30)
    for v, lab, hi in ((31.4, "女 31.4", False), (33.4, "男 33.4", True)):
        x = sx(v); o += Ln(x, ay, x, ay - 170, at("none", 3)) + P('M%.1f %d h 110 l -22 30 l 22 30 h -110 Z' % (x, ay - 170), HL if hi else F3) + T(x + 55, ay - 190, lab, 30, 700, "var(--w-text)")
    o += P('M%d %d C 300 420 500 380 %d 420' % (x0, ay + 120, x1), at("none", 2, "var(--w-lamp)", dash="10 10"))
    return o


import math as _mm
def sc_overtime(H=760):
    """11/23 封面：三個圓環＝兩個整 8 小時＋0.2 小時的扇形（16.2 小時換算，自行計算）。"""
    cy, r = 300, 100; xs = [130, 444, 758]; o = ""
    for i, cx in enumerate(xs):
        o += C(cx, cy, r + 14, F3)
        if i < 2:
            o += C(cx, cy, r, at("var(--w-lamp)", 2.2, "var(--w-lamp)", op=.55)) + T(cx, cy + 16, "8", 64, 700, "var(--w-text)") + T(cx, cy + 190, "8 小時", 32, 400, "var(--w-text)")
        else:
            a = _mm.radians(.2 / 8 * 360); x2, y2 = cx + r * _mm.sin(a), cy - r * _mm.cos(a)
            o += C(cx, cy, r, F1) + P("M%.1f %.1f L%.1f %.1f A%d %d 0 0 1 %.1f %.1f Z" % (cx, cy, cx, cy - r, r, r, x2, y2), at("var(--w-lamp)", 2, "var(--w-lamp)")) + T(cx, cy + 190, "0.2 小時", 32, 400, "var(--w-text)")
    o += T(287, cy + 14, "＋", 44, 700, "var(--w-text)") + T(601, cy + 14, "＋", 44, 700, "var(--w-text)")
    o += Ln(60, 600, 828, 600, at("none", SW)) + T(444, 670, "16.2 小時 ≈ 2 個 8 小時工作天", 34, 700, "var(--w-text)") + T(444, 716, "換算為自行計算", 30)
    return o

def sc_lamp(H=560):
    """11/23 第 3 頁：夜裡的窗（月亮）與桌燈、桌面上一杯咖啡。"""
    o = R(470, 40, 340, 300, 14, F3) + Ln(640, 40, 640, 340, at("none", 2.4)) + Ln(470, 190, 810, 190, at("none", 2.4))
    o += C(560, 120, 34, F1) + C(574, 112, 30, F3) + R(700, 240, 60, 100, 4, at("var(--w-face)", 2, op=.6))
    fl = 440
    o += Ln(30, fl, 858, fl, at("none", SW)) + hatch(44, fl + 2, 800, 18, 11, at("none", 1.1, op=.25))
    o += R(120, fl - 22, 170, 22, 6, DK) + Ln(205, fl - 22, 150, fl - 190, at("none", 7, extra='stroke-linecap="round"')) + Ln(150, fl - 190, 280, fl - 250, at("none", 7, extra='stroke-linecap="round"'))
    o += P("M250 %d L330 %d L350 %d L275 %d Z" % (fl - 262, fl - 232, fl - 200, fl - 188), at("var(--w-lamp)", SW, "var(--w-lamp)", op=.9))
    o += poly([(275, fl - 188), (350, fl - 200), (440, fl - 22), (230, fl - 22)], at("var(--w-lamp)", 0, "var(--w-lamp)", op=.12))
    o += R(560, fl - 70, 66, 70, 8, F1) + P("M626 %d q 36 0 36 22 q 0 22 -36 22" % (fl - 56), at("none", 4)) + steam(593, fl - 80, 50, .6)
    return o

def sc_rentsplit(H=760):
    """11/24 封面：一條月薪橫條（36,312）與它的 41%（北市獨立套房 15,000），下面一條全國租金中位數 8,600（等比例）。"""
    x0, W_ = 44, 800; w1 = W_ * 15000 / 36312; w2 = W_ * 8600 / 36312
    o = T(444, 110, "25–29 歲月薪中位數 36,312 元", 36, 700, "var(--w-text)")
    o += R(x0, 160, W_, 110, 10, F1) + R(x0, 160, w1, 110, 10, HL) + T(x0 + w1 / 2, 230, "15,000", 44, 700, "var(--w-text)")
    o += Ln(x0, 300, x0 + w1, 300, at("none", 3)) + T(x0, 350, "北市獨立套房 ≈ 41%", 32, 400, "var(--w-text)", "start")
    o += R(x0, 440, W_, 110, 10, F1) + R(x0, 440, w2, 110, 10, F3) + T(x0 + w2 / 2, 510, "8,600", 44, 700, "var(--w-text)")
    o += Ln(x0, 580, x0 + w2, 580, at("none", 3)) + T(x0, 630, "全國租金中位數 ≈ 24%", 32, 400, "var(--w-text)", "start")   # 兩個標籤都靠橫條起點對齊（審查 11-20）
    o += T(444, 720, "橫條等比例，自行計算占比", 30)
    return o

def sc_lease(H=560):
    """11/24 第 3 頁：一張租約（橫線＋印章）與一串鑰匙。"""
    o = R(120, 40, 340, 440, 10, F1) + R(150, 80, 150, 22, 4, DK)
    for k in range(7): o += Ln(150, 150 + k * 40, 430, 150 + k * 40, at("none", 2, op=.45))
    o += C(370, 420, 36, at("none", 4, "var(--w-lamp)")) + T(370, 432, "租", 34, 700, "var(--w-text)")
    o += C(640, 190, 52, F3) + C(640, 190, 22, at("var(--w-face)", 2.4)) + R(626, 242, 28, 190, 6, F3) + R(654, 340, 44, 14, 3, F3) + R(654, 384, 34, 14, 3, F3)
    o += Ln(30, 500, 858, 500, at("none", SW))
    return o

def sc_diverge(H=760):
    """11/25 封面：同一條基線，往上＝全體平均儲蓄 289,970 元，往下＝最低兩成家庭 −17,703 元（1 像素＝1,000 元，等比例）。"""
    by = 470; h1 = 289.97; h2 = 17.703
    o = Ln(40, by, 848, by, at("none", SW))
    o += R(160, by - h1, 190, h1, 8, HL) + T(255, by - h1 - 24, "+289,970", 44, 700, "var(--w-text)")
    o += R(540, by, 190, h2, 4, F3) + T(635, by - 24, "−17,703", 44, 700, "var(--w-text)")
    o += T(255, by + 70, "全體平均", 34, 400, "var(--w-text)") + T(635, by + 70, "最低 20%", 34, 400, "var(--w-text)")
    o += T(444, by + 150, "每戶一年的儲蓄（元），等比例", 30)
    o += T(444, 80, "同一年，同一個統計", 32, 400, "var(--w-text)")
    return o

def sc_leak(H=560):
    """11/25 第 3 頁：一個水桶，水位很低，桶底的洞滴出水滴。"""
    fl = 470
    o = Ln(30, fl, 858, fl, at("none", SW)) + hatch(44, fl + 2, 800, 18, 11, at("none", 1.1, op=.25))
    o += P("M250 120 L640 120 L590 %d L300 %d Z" % (fl - 40, fl - 40), F1)
    o += P("M286 %d L604 %d L590 %d L300 %d Z" % (fl - 130, fl - 130, fl - 40, fl - 40), at("var(--w-lamp)", 0, "var(--w-lamp)", op=.5))
    o += Ln(250, 120, 640, 120, at("none", 6)) + C(445, fl - 44, 12, DK)
    for k, y in enumerate((fl - 20, fl + 4)): o += P("M445 %d q 10 16 0 26 q -10 -10 0 -26 Z" % y, at("var(--w-lamp)", 2, "var(--w-lamp)", op=.8))
    return o

def sc_blocks(H=760):
    """11/26 封面：兩排各 10 格（1 格≈1.35 萬人）：2024 年 10 格全滿；2025 年 8 格滿、2 格虛線空（107,812／134,856＝約 80%）。"""
    o = T(444, 90, "2024 年新生兒 134,856 人", 36, 700, "var(--w-text)")
    for i in range(10): o += R(28 + i * 84, 130, 76, 76, 14, F3)
    o += T(444, 330, "2025 年新生兒 107,812 人", 36, 700, "var(--w-text)")
    for i in range(10):
        if i < 8: o += R(28 + i * 84, 370, 76, 76, 14, HL)
        else: o += R(28 + i * 84, 370, 76, 76, 14, at("none", 3, "var(--w-lamp)", dash="6 8"))
    o += Ln(28 + 8 * 84, 480, 28 + 10 * 84 - 8, 480, at("none", 3)) + T(28 + 9 * 84 - 4, 540, "少了 2 成", 38, 700, "var(--w-text)")
    o += T(444, 660, "1 格約 1.35 萬人，等比例示意", 30)
    return o

def sc_mobile(H=560):
    """11/26 第 3 頁：嬰兒床上方的掛飾（三條線，兩個掛飾、一個空鉤）。"""
    o = Ln(180, 70, 700, 70, at("none", 7, extra='stroke-linecap="round"')) + Ln(440, 40, 440, 70, at("none", 4))
    for x, kind in ((250, "s"), (440, "m"), (630, "e")):
        o += Ln(x, 70, x, 230, at("none", 2.4, op=.6))
        if kind == "s": o += poly([(x, 230), (x + 26, 275), (x + 76, 280), (x + 38, 312), (x + 50, 362), (x, 336), (x - 50, 362), (x - 38, 312), (x - 76, 280), (x - 26, 275)], F3)
        elif kind == "m": o += C(x, 290, 62, F3) + C(x + 24, 274, 54, F1)
        else: o += C(x, 245, 12, at("none", 3, "var(--w-lamp)", dash="4 5"))
    fl = 500
    o += Ln(30, fl, 858, fl, at("none", SW)) + hatch(44, fl + 2, 800, 14, 11, at("none", 1.1, op=.25))
    return o


def sc_resign(H=760):
    """11/29 封面：辦公桌上一只寫著「離職信」的信封，旁邊螢幕與一杯冷掉的咖啡；牆上時鐘。"""
    o = C(150, 120, 74, F1) + Ln(150, 120, 150, 70, at("none", 5, extra='stroke-linecap="round"')) + Ln(150, 120, 196, 140, at("none", 4, "var(--w-lamp)", extra='stroke-linecap="round"'))
    fl = 560
    o += R(520, fl - 300, 300, 210, 14, DK) + R(540, fl - 280, 260, 160, 8, F3) + R(650, fl - 90, 40, 90, 4, DK)
    o += Ln(30, fl, 858, fl, at("none", SW)) + hatch(44, fl + 2, 800, 14, 11, at("none", 1.1, op=.25))
    x, y, w, h = 90, fl - 190, 360, 170
    o += R(x, y, w, h, 12, F1) + P("M%d %d L%d %d L%d %d" % (x, y, x + w / 2, y + 96, x + w, y), at("none", 3))
    o += T(x + w / 2, y + h - 22, "離職信", 38, 700, "var(--w-text)")
    o += P("M%d %d q 30 -22 60 0 t 60 0 t 60 0" % (x + 60, y + 60), at("none", 4, "var(--w-lamp)", extra='stroke-linecap="round"'))
    o += R(470, fl - 60, 56, 60, 8, F3) + P("M526 %d q 30 0 30 18 q 0 18 -30 18" % (fl - 50), at("none", 4))
    o += T(444, 680, "每天都想離職：30.8%（受訪者）", 34, 700, "var(--w-text)")
    return o

def sc_chair(H=560):
    """11/29 第 3 頁：沒人坐的辦公椅、旁邊落地燈（下班後的空位）。"""
    fl = 470
    o = Ln(30, fl, 858, fl, at("none", SW)) + hatch(44, fl + 2, 800, 18, 11, at("none", 1.1, op=.25))
    o += R(260, fl - 330, 180, 170, 30, F3) + R(250, fl - 170, 200, 40, 14, F1) + Ln(350, fl - 130, 350, fl - 40, at("none", 7))
    for dx in (-80, 0, 80): o += Ln(350, fl - 40, 350 + dx, fl - 10, at("none", 5)) + C(350 + dx, fl - 6, 10, DK)
    o += Ln(680, fl, 680, fl - 380, at("none", 6)) + Ln(640, fl - 380, 720, fl - 380, at("none", 6))
    o += P("M650 %d l -40 150 h 140 l -40 -150 Z" % (fl - 370), at("var(--w-face3)", SW))
    o += R(280, fl - 214, 140, 70, 8, F1) + P("M280 %d L350 %d L420 %d" % (fl - 214, fl - 176, fl - 214), at("none", 2.4)) + T(350, fl - 240, "離職信", 30, 700, "var(--w-text)")
    return o

def sc_classroom(H=760):
    """11/30 封面：教室兩排十張課桌，只有五張坐了人（114 學年→130 學年約 51%，等比例示意）；黑板寫「一年級」。"""
    o = R(244, 20, 400, 100, 10, at("#5E7A62", SW)) + T(444, 86, "一年級", 40, 700, "#FFFFFF")
    for i in range(10):
        r, c = divmod(i, 5); cx = 124 + c * 160; cy = 260 + r * 230
        o += R(cx - 58, cy, 116, 28, 6, F3) + Ln(cx - 46, cy + 28, cx - 46, cy + 80, at("none", 3)) + Ln(cx + 46, cy + 28, cx + 46, cy + 80, at("none", 3))
        if i < 5: o += C(cx, cy - 46, 24, at("var(--w-face)", SW)) + P("M%d %d q 30 -46 60 0 Z" % (cx - 30, cy), HL)
        else: o += R(cx - 26, cy - 72, 52, 66, 12, at("none", 3, dash="7 7", op=.6))
    o += T(444, 720, "10 張剩 5 張：8.8 ÷ 17.4 ≈ 51%（示意）", 34, 700, "var(--w-text)")
    return o

def sc_bags(H=560):
    """11/30 第 3 頁：教室後面一排書包掛鉤，掛了書包的只有一半，其餘只剩空鉤。"""
    y0 = 150; o = R(40, y0, 808, 24, 8, F3)
    for i in range(8):
        x = 90 + i * 100; o += Ln(x, y0 + 24, x, y0 + 60, at("none", 4)) + C(x, y0 + 64, 6, DK)
        if i % 2 == 0: o += R(x - 40, y0 + 70, 80, 110, 16, HL if i == 0 else F1) + P("M%d %d q 40 -34 80 0" % (x - 40, y0 + 70), at("none", 3)) + R(x - 24, y0 + 126, 48, 36, 8, F3) + Ln(x - 28, y0 + 80, x - 28, y0 + 176, at("none", 2.4, op=.6)) + Ln(x + 28, y0 + 80, x + 28, y0 + 176, at("none", 2.4, op=.6))
        else: o += T(x, y0 + 124, "空", 36, 700, "var(--w-text)")
    fl = 520
    o += Ln(30, fl, 858, fl, at("none", SW)) + hatch(44, fl + 2, 800, 18, 11, at("none", 1.1, op=.25))
    return o

def head(theme="晝版"):
    p = PAL[theme]; W, H = 1080, 1350
    return ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><style>:root{--W:%dpx;--H:%dpx;%s}%s .hintuse{font-weight:700}</style></head><body>' % (W, H, css_vars(p), CSS), GRAIN % (W, H, W, H),
            '<div data-o="logo" class="abs" style="left:96px;top:56px;line-height:0"><img src="file://%s" style="height:64px;display:block"></div>' % LOGO_TIGHT]

def src_line(t):
    return '<div data-o="src" class="abs" style="left:96px;top:1252px;font-size:30px;line-height:40px;color:var(--w-sub);white-space:nowrap">%s</div>' % html.escape(t)

def page(post, n):
    pg = post["pages"][n - 1]; o = head()
    o.append('<div data-o="pager" class="abs" style="right:96px;top:1250px;height:44px;display:flex;align-items:center;gap:14px">%s</div>' % pager("S", n, 3))
    o.append(src_line(post["src"]))
    sc = pg["scene"](); svg, H = sc[0], sc[1]
    o.append(scene_x(svg, H, 180, sc[2] if len(sc) > 2 else None))
    y = 180 + H + 52
    M = 'class="m" style="top:%dpx;font-size:%dpx;line-height:%dpx"'
    if n == 1:
        o.append('<div data-o="main" ' + M % (y, 80, 100) + '>%s</div>' % lines(pg["title"]))
    else:
        o.append('<div data-o="main" ' + M % (y, 72, 88) + '>%s</div>' % html.escape(pg["title"]))
        q = ('<div data-o="body2" style="%s;font-weight:700;color:var(--w-hint)">%s</div>' % (BODY, html.escape(pg["ask"]))) if pg.get("ask") else ""
        o.append('<div class="abs" style="left:96px;top:%dpx;width:888px;display:flex;flex-direction:column;align-items:flex-start;gap:32px"><div data-o="body1" style="%s">%s</div>%s</div>' % (y + 88 + 40, BODY, lines(pg["body"]), q))
    return "".join(o) + "</body></html>"

# ───────── 各篇內容（頁序：封面＝發生什麼 → 第 2 頁＝資料從哪來＋統計圖表 → 第 3 頁＝解讀與晴＋提問）─────────
POSTS = {
 "20261111_unemployment": {
  "src": "資料：主計總處2026/9人力資源調查（10/23）",
  "pages": [
   {"title": ["失業率26年同月最低", "15-24歲仍逾11%"],
    "scene": lambda: (sc_ratio_cards(), 760)},
   {"title": "資料從哪來", "body": ["主計總處人力資源調查，", "2026 年 9 月，10/23 公布；", "統計從 15 歲算起，", "15–24 歲含 15–19 歲與在學生。"],
    "scene": lambda: (sc_vbars([("15–24歲", 11.59, "11.59%", False), ("25–29歲", 5.69, "5.69%", False), ("30–34歲", 3.40, "3.40%", False), ("35–64歲", 3.0, "<3%", True)], 12, 520, ref=3.36, reflab="整體 3.36%", hi=(0,)), 520)},
   {"title": "數字背後", "body": ["官方說明：多數是初次找工作，", "還在適應職場；", "整體失業率是 26 年同月最低。"], "ask": "第一份工作，找了多久？",
    "scene": lambda: (sc_door(), 560)},
  ]},
 "20261112_salary": {
  "src": "資料：主計總處2025、2026上半年薪資統計",
  "pages": [
   {"title": ["近7成員工，", "領不到平均月薪"], "scene": lambda: (sc_coins(), 760)},
   {"title": "資料從哪來", "body": ["主計總處薪資統計，2026/2 公布；", "2025 年經常性薪資，", "平均 47,884 元、中位數 38,406 元。"],
    "scene": lambda: (sc_hbars([("平均", 47884, "47,884 元"), ("中位數", 38406, "38,406 元")], 60000, 480, ticks=[0, 20000, 40000, 60000], tickfmt=lambda t: "0" if not t else "%d 萬" % (t // 10000), hi=(0,), lw=170, bh=96), 480)},
   {"title": "數字背後", "body": ["2026 上半年升到 70.03%；", "統計含部分工時與移工，", "經常性薪資不含加班與獎金。"], "ask": "平均數離日常多遠？",
    "scene": lambda: (sc_payslip(), 560)},
  ]},
 "20261113_cpi": {
  "src": "資料：主計總處2026/10 CPI（11/5公布）",
  "pages": [
   {"title": ["外食年漲3%，", "物價連6月破2%"], "scene": lambda: (sc_bento(), 760)},
   {"title": "資料從哪來", "body": ["主計總處消費者物價指數，", "2026 年 10 月，11/5 公布；", "10 月 CPI 年增 2.33%。"],
    "scene": lambda: (sc_hbars([("外食費", 3.01, "3.01%"), ("CPI 整體", 2.33, "2.33%"), ("房租", 1.70, "1.70%")], 3.6, 520, ticks=[0, 1, 2, 3], tickfmt="%d%%", hi=(0,), ref=2.0, reflab="2%"), 520)},
   {"title": "數字背後", "body": ["5 到 10 月，CPI 每月都高於 2%；", "房租漲得比整體慢，", "壓力在天天要吃的外食。"], "ask": "一個便當，現在多少錢？",
    "scene": lambda: (sc_months(), 520)},
  ]},
 "20261114_resume": {
  "src": "資料：104《滑世代焦慮》民調2026/6・1,114份",
  "pages": [
   {"title": ["48%求職青年，", "因「不夠好」不敢投履歷"], "scene": lambda: (sc_envelopes(), 760)},
   {"title": "資料從哪來", "body": ["104 人力銀行網路民調，", "18–30 歲求職會員 1,114 份，", "2026 年 4 月填答。"],
    "scene": lambda: (sc_hbars([("自評高壓", 54.4, "54.4%"), ("不敢投履歷", 48.3, "48.3%"), ("比較而自卑", 38.5, "38.5%")], 100, 480, ticks=[0, 25, 50, 75, 100], tickfmt="%d%%", hi=(1,)), 480)},
   {"title": "數字背後", "body": ["每天滑社群越久，越容易這樣想；", "樣本是求職會員，非全體青年。"], "ask": "安心專線 1925（24 小時、免付費）",
    "scene": lambda: (sc_plane(), 520)},
  ]},
 "20261115_ai": {
  "src": "資料：北市勞動局×1111調查2026/8・1,213份",
  "pages": [
   {"title": ["受訪上班族自估：", "2.56年內工作被AI改變"], "scene": lambda: (sc_timeline(), 760)},
   {"title": "資料從哪來", "body": ["北市勞動局×1111 求職會員調查，", "2026 年 6–7 月填答，1,213 份；", "圖為受訪者認為最易被取代的工作。"],
    "scene": lambda: (sc_hbars([("普通翻譯", 53.3, "53.3%"), ("行政文書", 42.5, "42.5%"), ("美編設計", 39.1, "39.1%"), ("行銷文案", 32.4, "32.4%"), ("基礎程式", 28.3, "28.3%")], 70, 520, ticks=[0, 20, 40, 60], tickfmt="%d%%", hi=(0,)), 520)},
   {"title": "數字背後", "body": ["受訪者認為最難取代的能力，", "多半落在「人」身上；", "這是自估，不是預測。"], "ask": "工作裡，哪一塊最難取代？",
    "scene": lambda: (sc_rings([("人際溝通", 55.6, "55.6%"), ("情緒判斷", 44.3, "44.3%"), ("現場應變", 41.4, "41.4%")]), 520)},
  ]},
 "20261116_marriage": {
  "src": "資料：內政部戶政司結婚登記2016、2025年",
  "pages": [
   {"title": ["10年來，", "結婚登記少了近3成"], "scene": lambda: (sc_ringpairs(), 760)},
   {"title": "資料從哪來", "body": ["內政部戶政司結婚登記，", "2016 年 147,861 對，", "2025 年 104,376 對，少 29.4%。"],
    "scene": lambda: (sc_vbars([("2016 年", 147861, "147,861", False), ("2025 年", 104376, "104,376", False)], 160000, 520, hi=(1,)), 520)},
   {"title": "數字背後", "body": ["同年總生育率 0.695；", "國發會推估 2026 年新生兒", "約 9.4 萬人。"], "ask": "成家這件事，離日常多遠？",
    "scene": lambda: (sc_cradle(), 560)},
  ]},
 "20261117_studentloan": {
  "src": "資料：教育部國教署、臺灣銀行115學年度公告",
  "pages": [
   {"title": ["115學年起學貸利率", "0.775%、寬限期2年"], "scene": lambda: (sc_slope(), 760)},
   {"title": "資料從哪來", "body": ["教育部國教署、臺灣銀行公告，", "2026/8/1 起新申貸適用；", "寬限期由 1 年延為 2 年。"],
    "scene": lambda: (sc_gantt(), 520)},
   {"title": "數字背後", "body": ["其中 1 個百分點由政府補貼，", "利率會機動調整；", "舊貸戶適用與否，以公告為準。"], "ask": "第一份薪水先還哪筆？",
    "scene": lambda: (sc_stack(), 560)},
  ]},
 "20261118_minwage": {
  "src": "資料：勞動部最低工資審議會2026/9/24",
  "pages": [
   {"title": ["2027年最低工資", "月薪30,900元"], "scene": lambda: (sc_clock(), 760)},
   {"title": "資料從哪來", "body": ["勞動部最低工資審議會，", "2026/9/24 決議，2027/1/1 起；", "時薪 196 元調到 205 元。"],
    "scene": lambda: (sc_vbars([("2024 年", 27470, "27,470", False), ("2025 年", 28590, "28,590", False), ("2026 年", 29500, "29,500", False), ("2027 年", 30900, "30,900", False)], 32000, 520, hi=(3,)), 520)},
   {"title": "數字背後", "body": ["預估受惠約 261 萬人，", "本國勞工約 220 萬人；", "以行政院核定公告為準。"], "ask": "第一份薪水，比最低工資多多少？",
    "scene": lambda: (sc_split(), 560)},
  ]},
 "20261119_young": {
  "src": "資料：主計總處薪資統計2026年1–7月",
  "pages": [
   {"title": ["未滿25歲，", "月薪中位數29,825元"], "scene": lambda: (sc_stairs(), 760)},
   {"title": "資料從哪來", "body": ["主計總處薪資統計，", "2026 年 1–7 月經常性薪資中位數；", "40–49 歲報導未列出，圖中略過。"],
    "scene": lambda: (sc_hbars([("未滿 25 歲", 29825, "29,825"), ("25–29 歲", 36312, "36,312"), ("30–39 歲", 40171, "40,171"), ("50–64 歲", 44019, "44,019")], 50000, 520, ticks=[0, 20000, 40000], tickfmt=lambda t: "0" if not t else "%d 萬" % (t // 10000), hi=(0,), lw=210), 520)},
   {"title": "數字背後", "body": ["中位數＝排隊站在正中間的人；", "經常性薪資不含加班與獎金。"], "ask": "第一份薪水，落在哪一級？",
    "scene": lambda: (sc_lollipop([("未滿 25 歲", 2.44, "+2.44%", True), ("25–29 歲", 3.18, "+3.18%", False)], 4), 520)},
  ]},
 "20261120_mortgage": {
  "src": "資料：內政部房價負擔能力指標2026Q1",
  "pages": [
   {"title": ["買房月付，", "占收入41.46%"], "scene": lambda: (sc_donut(), 760)},
   {"title": "資料從哪來", "body": ["內政部房價負擔能力指標，", "2026 年第 1 季全國房貸負擔率；", "30% 以下才算可合理負擔。"],
    "scene": lambda: (sc_band(), 520)},
   {"title": "數字背後", "body": ["算法：中位數所得家庭，", "貸七成、20 年本息均攤；", "是全體家戶，非只算首購族。"], "ask": "第一把鑰匙，要等幾年？",
    "scene": lambda: (sc_key(), 560)},
  ]},
 "20261121_laborins": {
  "src": "資料：勞動部勞保普通事故精算報告2024",
  "pages": [
   {"title": ["勞保精算：", "若不撥補，2031年轉負"], "scene": lambda: (sc_hourglass(), 760)},
   {"title": "資料從哪來", "body": ["勞保普通事故精算報告，", "基準日 2023/12/31；", "現行費率 11%，平衡費率 31.42%。"],
    "scene": lambda: (sc_hbars([("現行費率", 11, "11%"), ("平衡費率", 31.42, "31.42%")], 40, 480, ticks=[0, 10, 20, 30, 40], tickfmt="%d%%", hi=(1,), lw=190, bh=96), 480)},
   {"title": "數字背後", "body": ["2031 是推估，不是破產日；", "政府連年撥補，年限已延後 3 年。"], "ask": "退休，離現在多遠？",
    "scene": lambda: (sc_slope2(), 520)},
  ]},
 "20261122_firstmarriage": {
  "src": "資料：內政部《2025人口統計年刊》2026/8",
  "pages": [
   {"title": ["平均初婚年齡：", "男33.4歲、女31.4歲"], "scene": lambda: (sc_cups(), 760)},
   {"title": "資料從哪來", "body": ["內政部《2025 人口統計年刊》，", "2026 年 8 月出版；", "2025 年第一次結婚的平均年齡。"],
    "scene": lambda: (sc_hbars([("男性", 33.4, "33.4 歲"), ("女性", 31.4, "31.4 歲")], 40, 480, ticks=[0, 10, 20, 30, 40], tickfmt="%d", hi=(0,), ref=30, reflab="30 歲", lw=150, bh=96), 480)},
   {"title": "數字背後", "body": ["只算當年第一次結婚的人，", "沒結婚的人不在平均裡；", "同年結婚登記 104,376 對。"], "ask": "幾歲成家，誰的時間表？",
    "scene": lambda: (sc_agesteps(), 560)},
  ]},
 "20261123_overtime": {
  "src": "資料：勞動部114年勞工生活及就業狀況調查",
  "pages": [
   {"title": ["有加班的人，", "平均每月多做16.2小時"], "scene": lambda: (sc_overtime(), 760)},
   {"title": "資料從哪來", "body": ["勞動部勞工生活及就業狀況調查，", "2025 年 5 月，樣本 4,029 份；", "近一年 36.3% 曾延長工時。"],
    "scene": lambda: (sc_vbars([("2024 推算", 14.7, "14.7 小時", False), ("2025 年", 16.2, "16.2 小時", False)], 20, 520, hi=(1,)), 520)},
   {"title": "數字背後", "body": ["是有加班者的平均，", "不是全體勞工的平均；", "比上一年多 1.5 小時。"], "ask": "上個月，多做了幾小時？",
    "scene": lambda: (sc_lamp(), 560)},
  ]},
 "20261124_rent": {
  "src": "資料：主計總處薪資統計、內政部租金統計2026",
  "pages": [
   {"title": ["25–29歲月薪36,312，", "北市套房租金占4成"], "scene": lambda: (sc_rentsplit(), 760)},
   {"title": "資料從哪來", "body": ["月薪：主計總處，2026 年 1–7 月；", "租金：內政部，2026 年上半年；", "皆為中位數。"],
    "scene": lambda: (sc_hbars([("25–29歲月薪", 36312, "36,312"), ("北市獨立套房", 15000, "15,000"), ("全國租金", 8600, "8,600")], 40000, 520, ticks=[0, 20000, 40000], tickfmt=lambda t: "0" if not t else "%d 萬" % (t // 10000), hi=(1,), lw=250), 520)},
   {"title": "數字背後", "body": ["15,000÷36,312 約 41%（自算）；", "月薪是全國、不含獎金；", "租金樣本為補貼租約。"], "ask": "租完，還剩多少？",
    "scene": lambda: (sc_lease(), 560)},
  ]},
 "20261125_savings": {
  "src": "資料：主計總處114年家庭收支調查（2026/8）",
  "pages": [
   {"title": ["最低兩成家庭，", "連19年入不敷出"], "scene": lambda: (sc_diverge(), 760)},
   {"title": "資料從哪來", "body": ["主計總處家庭收支調查，", "2025 年資料，2026 年 8 月公布；", "每戶可支配所得。"],
    "scene": lambda: (sc_hbars([("最高 20%", 244.9, "244.9 萬"), ("最低 20%", 39.7, "39.7 萬")], 300, 480, ticks=[0, 100, 200, 300], tickfmt="%d 萬", hi=(1,), lw=190, bh=96), 480)},
   {"title": "數字背後", "body": ["差距 6.17 倍，14 年來新高；", "負儲蓄＝花得比所得多；", "全體儲蓄率是 23.96%。"], "ask": "平均數裡，有誰沒被算到？",
    "scene": lambda: (sc_leak(), 560)},
  ]},
 "20261126_births": {
  "src": "資料：內政部戶口統計2025年（2026/1/9）",
  "pages": [
   {"title": ["2025年新生兒10.8萬，", "一年少了2成"], "scene": lambda: (sc_blocks(), 760)},
   {"title": "資料從哪來", "body": ["內政部戶口統計，2026/1/9 公布；", "2025 年新生兒 107,812 人，", "比 2024 年少 27,044 人。"],
    "scene": lambda: (sc_vbars([("2024 年", 134856, "134,856", False), ("2025 年", 107812, "107,812", False)], 160000, 520, hi=(1,)), 520)},
   {"title": "數字背後", "body": ["粗出生率：千分之 5.76 降到 4.62；", "連續第 10 年下降。"], "ask": "身邊，上次辦滿月是何時？",
    "scene": lambda: (sc_mobile(), 560)},
  ]},
 "20261129_quit": {
  "src": "資料：1111〈2026青年轉職調查〉（民調）",
  "pages": [
   {"title": ["1111調查：3成青年", "上班族天天想離職"], "scene": lambda: (sc_resign(), 760)},
   {"title": "資料從哪來", "body": ["1111 人力銀行網路問卷（民調）；", "18～35 歲求職會員 1,011 人；", "有轉職打算 60.4%。"],
    "scene": lambda: (sc_hbars([("薪水太低", 35.5, "35.5%"), ("工作太累", 23.9, "23.9%"), ("主管問題", 20.9, "20.9%")], 40, 520, ticks=[0, 20, 40], tickfmt="%d%%", hi=(0,), lw=220), 520)},
   {"title": "數字背後", "body": ["立意抽樣，不是全國統計；", "慰留平均要加薪 7,413 元；", "跳槽期待加 10,398 元。"], "ask": "讓人想走的，是什麼？",
    "scene": lambda: (sc_chair(), 560)},
  ]},
 "20261130_grade1": {
  "src": "資料：教育部學生數預測報告（115～130學年）",
  "pages": [
   {"title": ["15年後的小一新生，", "預測少近一半"], "scene": lambda: (sc_classroom(), 760)},
   {"title": "資料從哪來", "body": ["教育部統計處學生數預測報告，", "以 104～114 學年實際人數推估；", "115 學年起為預測值。"],
    "scene": lambda: (sc_vbars([("114 學年", 17.4, "17.4萬", False), ("115 學年", 16.5, "16.5萬", False), ("116 學年", 15.7, "15.7萬", False), ("117 學年", 14.4, "14.4萬", False)], 20, 520, hi=(3,)), 520)},
   {"title": "數字背後", "body": ["130 學年約 8.8 萬，少近 5 成；", "平均每年少約 5,400 人；", "是預測，不是實際報到數。"], "ask": "母校現在一個年級幾班？",
    "scene": lambda: (sc_bags(), 560)},
  ]},
}

def count(post):
    import re
    out = []
    for i, pg in enumerate(post["pages"]):
        t = "".join(pg["title"]) if isinstance(pg["title"], list) else pg["title"]
        t += "".join(pg.get("body", [])) + pg.get("ask", "")
        t = re.sub(r"\s", "", t)   # 全形字算 1、半形英數符號算 0.5（中文排版慣例）
        out.append(sum(.5 if ord(ch) < 128 else 1 for ch in t))
    return out

if __name__ == "__main__":
    names = sys.argv[1:] or list(POSTS)
    mf = []
    for name in names:
        post = POSTS[name]; c = count(post)
        print(name, "字數（封面≤20、內頁≤50）", c)
        assert c[0] <= 20 and all(x <= 50 for x in c[1:]), "字數超標"
        hd = os.path.join(B, "html", "posts", name); os.makedirs(hd, exist_ok=True)
        od = os.path.join(QUEUE, name); os.makedirs(od, exist_ok=True)
        for n in (1, 2, 3):
            hp = os.path.join(hd, f"{n}.html"); open(hp, "w", encoding="utf-8").write(page(post, n))
            mf.append(dict(html=os.path.relpath(hp, B), png=os.path.relpath(os.path.join(od, f"{n}.png"), B), W=1080, H=1350, key=f"{name}/{n}", post=name, safe=None))
    json.dump(mf, open(B + "/manifest_posts.json", "w"), ensure_ascii=False, indent=1); print("頁數", len(mf))
