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

def head(theme="晝版"):
    p = PAL[theme]; W, H = 1080, 1350
    return ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><style>:root{--W:%dpx;--H:%dpx;%s}%s .hintuse{font-weight:700}</style></head><body>' % (W, H, css_vars(p), CSS), GRAIN % (W, H, W, H),
            '<div data-o="logo" class="abs" style="left:96px;top:84px;line-height:0"><img src="file://%s" style="height:64px;display:block"></div>' % LOGO_TIGHT]

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
