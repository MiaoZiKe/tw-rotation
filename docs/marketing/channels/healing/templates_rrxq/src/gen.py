#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日日小晴 模板產生器：7 種模板 × 4 色調 → html/（再由 render.js 轉 PNG）。
用法：python3 gen.py && node render.js && python3 contrast.py && python3 sheets.py"""
import os, json, html, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import illus as I
from illus import mix
BASE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(BASE, "..")
esc = html.escape

PALS = {
 "cream":  dict(name="奶油晨光", bg="#FFF6E5", acc="#F2A65A", acc2="#F8D58A", ink="#3A3A3A", sub="#5A5249", deep="#A55608"),
 "sky":    dict(name="晴空淡藍", bg="#EAF4FB", acc="#6FB1E0", acc2="#F6C85F", ink="#2E3A46", sub="#4A5865", deep="#1B6396"),
 "matcha": dict(name="抹茶午後", bg="#EEF2E6", acc="#8DAA7B", acc2="#F1DB8C", ink="#34402F", sub="#505B49", deep="#456A33"),
 "peach":  dict(name="蜜桃傍晚", bg="#FCEDE6", acc="#F0A58A", acc2="#F9D58B", ink="#5A4636", sub="#6B5848", deep="#A4452A"),
}
FONT = "'Noto Sans CJK TC',sans-serif"

def css(p, w, h):
    return """*{margin:0;padding:0;box-sizing:border-box}
body{width:%dpx;height:%dpx;position:relative;overflow:hidden;background:%s;color:%s;font-family:%s;letter-spacing:.04em}
.abs{position:absolute;white-space:nowrap}
.lab{font-size:32px;line-height:44px;color:%s}
.wm{font-size:40px;line-height:52px;font-weight:700;color:%s}.wm b{color:%s}
.main{font-weight:700;color:%s;white-space:nowrap}
.sm{color:%s;white-space:nowrap}
.deep{color:%s}
.pill{background:%s;border-radius:30px;padding:6px 24px;font-size:32px;line-height:44px;font-weight:700;color:%s}
.si{font-size:32px;line-height:1.5;color:%s;white-space:pre-wrap}
.help{font-size:34px;line-height:1.55;color:%s;white-space:pre-wrap}
""" % (w, h, p['bg'], p['ink'], FONT, p['sub'], p['ink'], p['deep'], p['ink'], p['sub'], p['deep'], mix(p['bg'], p['acc2'], .3), p['deep'], p['sub'], p['ink'])

def split(s, size, maxw=888):
    if len(s) * size * 1.04 <= maxw and len(s) <= 12: return [s]
    cut = [i + 1 for i, c in enumerate(s) if c in "，、：" and 0 < i < len(s) - 1]
    i = min(cut, key=lambda c: abs(c - len(s) / 2)) if cut else len(s) // 2
    return [s[:i], s[i:]]

def head(p, w, h, n=None, total=None, badge=None, wm_top=96):
    o = ['<div data-o="wm" class="abs wm" style="left:96px;top:%dpx">日日小<b>晴</b></div>' % wm_top]
    if badge: o.append('<div data-o="badge" class="abs pill" style="right:96px;top:%dpx">%s</div>' % (wm_top - 2, esc(badge)))
    elif total: o.append('<div data-o="pg" class="abs lab" style="right:96px;top:%dpx">%d／%d</div>' % (wm_top + 4, n, total))
    return ''.join(o)

def text_block(main, small, size, top, ssize=34, gap=14, lh=1.5):
    ml = split(main, size); o = []
    for k, l in enumerate(ml):
        o.append('<div data-o="main%d" class="abs main" style="left:96px;top:%dpx;font-size:%dpx;line-height:%dpx">%s</div>' % (k, top + k * round(size * lh), size, round(size * lh), esc(l)))
    y = top + len(ml) * round(size * lh) + gap
    if small: o.append('<div data-o="small" class="abs sm" style="left:96px;top:%dpx;font-size:%dpx;line-height:%dpx">%s</div>' % (y, ssize, round(ssize * 1.45), esc(small)))
    return ''.join(o)

def illus_box(svg, w, h, top, left=96):
    return '<div data-o="illus" class="abs" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx">%s</div>' % (left, top, w, h, svg)

def foot(txt, y=1236): return '<div data-o="foot" class="abs lab" style="left:96px;top:%dpx">%s</div>' % (y, esc(txt))

def tracker(p, y=1238, today=2):
    o = '<svg data-o="trk" class="abs" style="left:96px;top:%dpx" width="%d" height="38" viewBox="0 0 %d 38">' % (y, 7 * 46, 7 * 46)
    for i in range(7):
        cx = 19 + i * 46
        if i == today:
            for k in range(8):
                a = k * 3.14159 / 4; o += '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="3" stroke-linecap="round"/>' % (cx + 14 * __import__('math').cos(a), 19 + 14 * __import__('math').sin(a), cx + 18 * __import__('math').cos(a), 19 + 18 * __import__('math').sin(a), p['ink'])
            o += '<circle cx="%d" cy="19" r="10" fill="%s" stroke="%s" stroke-width="3.5"/>' % (cx, p['acc2'], p['ink'])
        else:
            o += '<circle cx="%d" cy="19" r="9" fill="none" stroke="%s" stroke-width="3.5"/>' % (cx, p['sub'])
    return o + '</svg>'

def doc(p, w, h, body): return '<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><style>%s</style></head><body>%s</body></html>' % (css(p, w, h), body)

# ---------------- 七種模板 ----------------
def t_cover(p):
    svg, sw, sh = I.sc_sunset(p)
    return 1080, 1350, doc(p, 1080, 1350, head(p, 1080, 1350, 1, 6) + illus_box(svg, sw, sh, 168) + text_block("薪水沒漲，但今天的晚霞很好看", "抬頭看一眼，就是今天的小獎勵", 64, 950) + foot("往右滑 →"))

def t_data(p):
    svg, sw, sh = I.sc_pots(p); cx = I.pot_center_x()
    b = head(p, 1080, 1350, 2, 6)
    b += '<div data-o="kick" class="abs main" style="left:96px;top:176px;font-size:50px;line-height:66px">2025 年經常性薪資中位數</div>'
    b += '<div data-o="num" class="abs main deep" style="left:96px;top:252px;font-size:200px;line-height:290px;letter-spacing:.01em">38,406<span style="font-size:76px;letter-spacing:.04em;color:%s;margin-left:14px">元</span></div>' % p['ink']
    b += illus_box(svg, sw, sh, 560)
    b += '<div data-o="medlab" class="abs lab" style="left:%dpx;top:972px;transform:translateX(-50%%);font-weight:700;color:%s">中位數</div>' % (cx, p['deep'])
    b += '<div data-o="small" class="abs sm" style="left:96px;top:1080px;font-size:36px;line-height:52px">出處：主計總處 2025 年，媒體轉述</div>'
    b += foot("示意圖，非實際分布・公開數據整理，非投資建議")
    return 1080, 1350, doc(p, 1080, 1350, b)

def t_line(p):
    svg, sw, sh = I.sc_window(p)
    return 1080, 1350, doc(p, 1080, 1350, head(p, 1080, 1350, 3, 6) + illus_box(svg, sw, sh, 168) + text_block("窗邊那盆小綠，今天也長高了一點", "慢慢來，陽光都看得見", 64, 950) + foot("存起來，累的時候看"))

def t_daily(p):
    svg, sw, sh = I.sc_lights(p)
    b = head(p, 1080, 1350, badge="今日小晴 No.07") + illus_box(svg, sw, sh, 168) + text_block("下班路上，綠燈剛好一路亮到家", "沒什麼大事，剛剛好就很好", 64, 950)
    b += tracker(p) + '<div data-o="foot" class="abs lab" style="right:96px;top:1236px">週三的小晴</div>'
    return 1080, 1350, doc(p, 1080, 1350, b)

def t_sources(p):
    svg, sw, sh = I.sc_gap(p)
    b = head(p, 1080, 1350, 6, 6)
    b += '<div data-o="sh" class="abs main" style="left:96px;top:184px;font-size:56px;line-height:76px">出處與求助資源</div>'
    b += '<div data-o="gap" class="abs" style="right:96px;top:166px;width:%dpx;height:%dpx">%s</div>' % (int(sw * .72), int(sh * .72), svg.replace('width="%d" height="%d"' % (sw, sh), 'width="%d" height="%d"' % (int(sw * .72), int(sh * .72)), 1))
    b += '<div data-o="si0" class="abs si" style="left:96px;top:330px">出處：行政院主計總處\n2025 年薪資統計，媒體轉述</div>'
    b += '<div data-o="si1" class="abs si" style="left:96px;top:458px">數據為公開資料整理，非投資建議。</div>'
    b += '<div data-o="rule" class="abs" style="left:96px;top:560px;width:888px;height:4px;background:%s;border-radius:2px"></div>' % mix(p['bg'], p['acc'], .7)
    b += '<div data-o="help0" class="abs help" style="left:96px;top:600px">如果你最近很辛苦，不用一個人撐：</div>'
    b += '<div data-o="help1" class="abs help main" style="left:96px;top:668px;font-size:44px;line-height:64px;color:%s">安心專線 1925（24 小時、免付費）</div>' % p['deep']
    b += '<div data-o="help2" class="abs help" style="left:96px;top:760px">生命線 1995　張老師 1980（非 24 小時）</div>'
    b += '<div data-o="help3" class="abs help" style="left:96px;top:828px">有立即危險請撥 119 或 110。</div>'
    b += '<div data-o="note" class="abs si" style="left:96px;top:940px">這裡是陪伴型內容分享，不是心理諮商，\n也不能取代專業協助。</div>'
    b += foot("今天也辛苦了")
    return 1080, 1350, doc(p, 1080, 1350, b)

def t_threads(p):
    svg, sw, sh = I.sc_bowl(p)
    b = head(p, 1080, 1350) + text_block("一碗熱湯，就是今天的小晴", "喝完，再慢慢出發", 68, 176, 36, 16)
    b += illus_box(svg, sw, sh, 372) + foot("每天有一小段晴就好", 1240)
    return 1080, 1350, doc(p, 1080, 1350, b)

def t_reels(p):
    svg, sw, sh = I.sc_line(p)
    b = head(p, 1080, 1920, wm_top=270) + illus_box(svg, sw, sh, 336)
    b += text_block("今天，留一小段晴給自己", "不用很多，一小段就夠了", 84, 1236, 40, 20)
    return 1080, 1920, doc(p, 1080, 1920, b)

TPL = [("1_cover", "IG 輪播封面", t_cover), ("2_data", "一個數字的數據頁", t_data), ("3_line", "一句話頁", t_line),
       ("4_daily", "今日小晴系列頁", t_daily), ("5_sources", "出處與求助資源頁", t_sources), ("6_threads", "Threads 配圖", t_threads), ("7_reels", "Reels 封面", t_reels)]

def main():
    mf = {}
    for tid, tname, fn in TPL:
        for pk, p in PALS.items():
            w, h, s = fn(p); d = os.path.join(BASE, "html"); os.makedirs(d, exist_ok=True)
            open(os.path.join(d, "%s_%s.html" % (tid, pk)), "w", encoding="utf-8").write(s); mf["%s_%s" % (tid, pk)] = [w, h]
    json.dump(mf, open(os.path.join(BASE, "manifest.json"), "w"))
    json.dump({k: v for k, v in PALS.items()}, open(os.path.join(BASE, "palettes.json"), "w"), ensure_ascii=False)
    print("html", len(mf))
main()
