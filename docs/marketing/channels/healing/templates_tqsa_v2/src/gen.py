#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""談晴說礙 v2 模板產生器（沿用日日小晴 templates_rrxq 的版型與插圖，換成談晴說礙品牌／雲＝礙、太陽＝晴）。
產出：首篇 3 張版、首篇 5 張版、Threads 單張、7 種模板 × 4 色調 → html/ 與 manifest.json，再由 render.js 轉 PNG。
重跑：cd src && python3 gen.py && node render.js && python3 contrast.py && python3 sheets.py"""
import os, json, html, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import illus as I
from illus import mix
from PIL import Image
BASE = os.path.dirname(os.path.abspath(__file__)); esc = html.escape
FONT = "'Noto Sans CJK TC',sans-serif"
LOGO = json.load(open(os.path.join(BASE, 'logo.json'), encoding='utf-8'))

def lin(c):
    c /= 255; return c / 12.92 if c <= .03928 else ((c + .055) / 1.055) ** 2.4
def lum(h): h = h.lstrip('#'); r, g, b = [int(h[i:i+2], 16) for i in (0, 2, 4)]; return .2126 * lin(r) + .7152 * lin(g) + .0722 * lin(b)
def cr(a, b): x, y = max(lum(a), lum(b)), min(lum(a), lum(b)); return (x + .05) / (y + .05)
def deepen(base, ink, bg, need=4.8):
    t = 0.0
    while cr(mix(base, ink, t), bg) < need and t < 1: t += .02
    return mix(base, ink, t)

RAW = {
 "cream":  dict(name="奶油晨光", bg="#FFF6E5", acc="#F2A65A", acc2="#F8D58A", ink="#3A3A3A", sub="#5A5249", deep="#A55608"),
 "sky":    dict(name="晴空淡藍", bg="#EAF4FB", acc="#6FB1E0", acc2="#F6C85F", ink="#2E3A46", sub="#4A5865", deep="#1B6396"),
 "matcha": dict(name="抹茶午後", bg="#EEF2E6", acc="#8DAA7B", acc2="#F1DB8C", ink="#34402F", sub="#505B49", deep="#456A33"),
 "peach":  dict(name="蜜桃傍晚", bg="#FCEDE6", acc="#F0A58A", acc2="#F9D58B", ink="#5A4636", sub="#6B5848", deep="#A4452A"),
}
PALS = {}
for k, p in RAW.items():
    q = dict(p)
    q['cl'] = mix('#DCE0E8', p['bg'], .25)                       # 雲灰填色（礙）
    q['sunT'] = deepen('#F29A2E', p['ink'], p['bg'])              # 「晴」字：加深太陽橘
    q['clT'] = deepen('#9AA3B0', p['ink'], p['bg'])               # 「礙」字：加深雲灰
    PALS[k] = q

_sym = {}
def logo_html(p, tone_key):
    """左上 LOGO：回傳 (html, 寬)。換 LOGO 只改 logo.json。"""
    src = os.path.normpath(os.path.join(BASE, LOGO['src'].replace('{tone}', p['name'])))
    if not os.path.exists(src): src = os.path.normpath(os.path.join(BASE, LOGO['src'].replace('{tone}', LOGO['fallback_tone'])))   # 蜜桃傍晚 LOGO 沒有該色調圖檔，借奶油晨光
    im = Image.open(src).convert('RGBA'); h = LOGO['height']
    if LOGO['mode'] == 'image':
        bb = im.getchannel('A').getbbox(); im = im.crop(bb)
    else:
        im = im.crop((0, 0, LOGO['crop_x'], im.height)); bb = im.getchannel('A').getbbox(); im = im.crop(bb)
    w = round(im.width * h / im.height)
    out = os.path.join(BASE, 'logo_%s.png' % tone_key); im.save(out)
    return '<img data-o="logo" src="logo_%s.png" class="abs" style="left:96px;top:%dpx;height:%dpx;width:%dpx">' % (tone_key, 0, h, w), w

def css(p, w, h):
    return """*{margin:0;padding:0;box-sizing:border-box}
body{width:%dpx;height:%dpx;position:relative;overflow:hidden;background:%s;color:%s;font-family:%s;letter-spacing:.04em}
.abs{position:absolute;white-space:nowrap}
.lab{font-size:32px;line-height:44px;color:%s}
.wm{font-size:44px;line-height:56px;font-weight:900;color:%s;letter-spacing:.08em}.wm .q{color:%s}.wm .a{color:%s}
.main{font-weight:700;color:%s;white-space:nowrap}
.sm{color:%s;white-space:nowrap}
.deep{color:%s}
.pill{background:%s;border-radius:30px;padding:6px 24px;font-size:32px;line-height:44px;font-weight:700;color:%s}
.si{font-size:32px;line-height:1.5;color:%s;white-space:pre-wrap}
.help{font-size:34px;line-height:1.55;color:%s;white-space:pre-wrap}
""" % (w, h, p['bg'], p['ink'], FONT, p['sub'], p['ink'], p['sunT'], p['clT'], p['ink'], p['sub'], p['deep'], mix(p['bg'], p['acc2'], .3), p['deep'], p['sub'], p['ink'])

def head(p, tk, n=None, total=None, badge=None, top=84):
    lg, lw = logo_html(p, tk); lg = lg.replace('top:0px', 'top:%dpx' % top)
    o = [lg]
    if LOGO['mode'] != 'image':
        o.append('<div data-o="wm" class="abs wm" style="left:%dpx;top:%dpx">談<span class="q">晴</span>說<span class="a">礙</span></div>' % (96 + lw + 18, top + (LOGO['height'] - 56) // 2))
    if badge: o.append('<div data-o="badge" class="abs pill" style="right:96px;top:%dpx">%s</div>' % (top + 12, esc(badge)))
    elif total: o.append('<div data-o="pg" class="abs lab" style="right:96px;top:%dpx">%d／%d</div>' % (top + 14, n, total))
    return ''.join(o)

def split(s, size, maxw=888):
    if len(s) * size * 1.04 <= maxw and len(s) <= 13: return [s]
    cut = [i + 1 for i, c in enumerate(s) if c in "，、：" and 0 < i < len(s) - 1]
    i = min(cut, key=lambda c: abs(c - len(s) / 2)) if cut else len(s) // 2
    return [s[:i], s[i:]]

def text_block(main, small, size, top, ssize=34, gap=14, lh=1.5):
    ml = split(main, size); o = []
    for k, l in enumerate(ml):
        o.append('<div data-o="main%d" class="abs main" style="left:96px;top:%dpx;font-size:%dpx;line-height:%dpx">%s</div>' % (k, top + k * round(size * lh), size, round(size * lh), esc(l)))
    y = top + len(ml) * round(size * lh) + gap
    if small: o.append('<div data-o="small" class="abs sm" style="left:96px;top:%dpx;font-size:%dpx;line-height:%dpx">%s</div>' % (y, ssize, round(ssize * 1.45), esc(small)))
    return ''.join(o)

def illus_box(svg, w, h, top, left=96): return '<div data-o="illus" class="abs" style="left:%dpx;top:%dpx;width:%dpx;height:%dpx">%s</div>' % (left, top, w, h, svg)
def foot(txt, y=1236): return '<div data-o="foot" class="abs lab" style="left:96px;top:%dpx">%s</div>' % (y, esc(txt))
def doc(p, w, h, body): return '<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><style>%s</style></head><body>%s</body></html>' % (css(p, w, h), body)

def tracker(p, y=1238, today=2):
    o = '<svg data-o="trk" class="abs" style="left:96px;top:%dpx" width="%d" height="38" viewBox="0 0 %d 38">' % (y, 7 * 46, 7 * 46)
    for i in range(7):
        cx = 19 + i * 46
        if i == today:
            for k in range(8):
                a = k * math.pi / 4; o += '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="3" stroke-linecap="round"/>' % (cx + 14 * math.cos(a), 19 + 14 * math.sin(a), cx + 18 * math.cos(a), 19 + 18 * math.sin(a), p['ink'])
            o += '<circle cx="%d" cy="19" r="10" fill="%s" stroke="%s" stroke-width="3.5"/>' % (cx, p['acc2'], p['ink'])
        else: o += '<circle cx="%d" cy="19" r="9" fill="none" stroke="%s" stroke-width="3.5"/>' % (cx, p['sub'])
    return o + '</svg>'

# ---------- 首篇（IG 輪播）----------
SC = {'cover': I.sc_cover, 'obs': lambda p: I.sc_window(p, observer=True), 'clouds': I.sc_clouds, 'gap': I.sc_gaptown, 'talk': I.sc_talk}
POST3 = [('cover', '談晴，也說礙', '說這一代的難，也說還在的光。', 80, '往右滑 →'),
         ('obs', '我們是觀察者', '記錄這一代的難，也記錄難裡的晴。', 80, '往右滑 →'),
         ('talk', '每天說一點礙，也談一點晴', '傳給一個也在撐的朋友。', 68, '今天的晴，留一個字給我們 →')]
POST5 = [('cover', '談晴，也說礙', '說這一代的難，也說還在的光。', 80, '往右滑 →'),
         ('obs', '我們是觀察者', '記錄這一代年輕人，怎麼過日子。', 80, '往右滑 →'),
         ('clouds', '有些難，說清楚了', '才知道，不是只有你不夠努力。', 80, '往右滑 →'),
         ('gap', '但我們也看見晴', '再硬的日子，這一代還是很會在縫裡找光。', 80, '往右滑 →'),
         ('talk', '每天說一點礙，也談一點晴', '傳給一個也在撐的朋友。', 68, '今天的晴，留一個字給我們 →')]
def post_slide(p, tk, spec, n, total):
    sc, tt, sb, size, ft = spec; svg, sw, sh = SC[sc](p)
    top = 950 if size > 68 else 972
    b = head(p, tk, n, total) + illus_box(svg, sw, sh, 168) + text_block(tt, sb, size, top - (0 if size > 68 else 0)) + foot(ft)
    return 1080, 1350, doc(p, 1080, 1350, b)

# ---------- 七種模板 ----------
def t_cover(p, tk):
    svg, sw, sh = I.sc_cover(p)
    return 1080, 1350, doc(p, 1080, 1350, head(p, tk, 1, 6) + illus_box(svg, sw, sh, 168) + text_block("雲很厚，但今天還是有一小段晴", "先說說礙，再找找晴", 64, 950) + foot("往右滑 →"))
def t_data(p, tk):
    svg, sw, sh = I.sc_pots(p); cx = I.pot_center_x()
    b = head(p, tk, 2, 6)
    b += '<div data-o="kick" class="abs main" style="left:96px;top:188px;font-size:50px;line-height:66px">2025 年經常性薪資中位數</div>'
    b += '<div data-o="num" class="abs main deep" style="left:96px;top:262px;font-size:200px;line-height:290px;letter-spacing:.01em">38,406<span style="font-size:76px;letter-spacing:.04em;color:%s;margin-left:14px">元</span></div>' % p['ink']
    b += illus_box(svg, sw, sh, 570)
    b += '<div data-o="medlab" class="abs lab" style="left:%dpx;top:982px;transform:translateX(-50%%);font-weight:700;color:%s">中位數</div>' % (cx, p['deep'])
    b += '<div data-o="small" class="abs sm" style="left:96px;top:1090px;font-size:36px;line-height:52px">出處：主計總處 2025 年，媒體轉述</div>'
    b += foot("示意圖，非實際分布・公開數據整理，非投資建議")
    return 1080, 1350, doc(p, 1080, 1350, b)
def t_line(p, tk):
    svg, sw, sh = I.sc_window(p)
    return 1080, 1350, doc(p, 1080, 1350, head(p, tk, 3, 6) + illus_box(svg, sw, sh, 168) + text_block("窗外有雲，窗邊那盆小綠還是長高了", "礙在外面，晴在窗邊", 64, 950) + foot("存起來，累的時候看"))
def t_daily(p, tk):
    svg, sw, sh = I.sc_lights(p)
    b = head(p, tk, badge="今日的晴 No.07") + illus_box(svg, sw, sh, 168) + text_block("下班路上，綠燈剛好一路亮到家", "沒什麼大事，剛剛好就很好", 64, 950)
    b += tracker(p) + '<div data-o="foot" class="abs lab" style="right:96px;top:1236px">週三的晴</div>'
    return 1080, 1350, doc(p, 1080, 1350, b)
def t_sources(p, tk):
    svg, sw, sh = I.sc_gap(p); k = .72; gw, gh = int(sw * k), int(sh * k)
    b = head(p, tk, 6, 6) .replace('data-o="pg"', 'data-o="pg"')
    b += '<div data-o="sh" class="abs main" style="left:96px;top:236px;font-size:56px;line-height:76px">出處與求助資源</div>'
    b += '<div data-o="si0" class="abs si" style="left:96px;top:350px">出處：行政院主計總處\n2025 年薪資統計，媒體轉述</div>'
    b += '<div data-o="si1" class="abs si" style="left:96px;top:478px">數據為公開資料整理，非投資建議。</div>'
    b += '<div data-o="rule" class="abs" style="left:96px;top:580px;width:888px;height:4px;background:%s;border-radius:2px"></div>' % mix(p['bg'], p['acc'], .7)
    b += '<div data-o="help0" class="abs help" style="left:96px;top:616px">如果你最近很辛苦，不用一個人撐：</div>'
    b += '<div data-o="help1" class="abs help main" style="left:96px;top:684px;font-size:44px;line-height:64px;color:%s">安心專線 1925（24 小時、免付費）</div>' % p['deep']
    b += '<div data-o="help2" class="abs help" style="left:96px;top:776px">生命線 1995　張老師 1980（非 24 小時）</div>'
    b += '<div data-o="help3" class="abs help" style="left:96px;top:844px">有立即危險請撥 119 或 110。</div>'
    b += '<div data-o="note" class="abs si" style="left:96px;top:956px">這裡是陪伴型內容分享，不是心理諮商，\n也不能取代專業協助。</div>'
    b += '<div data-o="gap" class="abs" style="right:96px;top:206px;width:%dpx;height:%dpx">%s</div>' % (gw, gh, svg.replace('width="%d" height="%d"' % (sw, sh), 'width="%d" height="%d"' % (gw, gh), 1))
    b += foot("談晴說礙・今天也辛苦了", 1240)
    return 1080, 1350, doc(p, 1080, 1350, b)
def t_threads(p, tk, main="一碗熱湯，晴就在雲邊", small="喝完，再慢慢出發", ft="每天說一點礙，也談一點晴"):
    svg, sw, sh = I.sc_bowl(p)
    b = head(p, tk) + text_block(main, small, 68, 196, 36, 16) + illus_box(svg, sw, sh, 392) + foot(ft, 1244)
    return 1080, 1350, doc(p, 1080, 1350, b)
def t_reels(p, tk):
    svg, sw, sh = I.sc_picnic(p)
    b = head(p, tk, top=270) + illus_box(svg, sw, sh, 372) + text_block("雲在，晴也在，一起坐一下", "不用很多，一小段就夠了", 84, 1262, 40, 20)
    return 1080, 1920, doc(p, 1080, 1920, b)

TPL = [("1_cover", t_cover), ("2_data", t_data), ("3_line", t_line), ("4_daily", t_daily), ("5_sources", t_sources), ("6_threads", t_threads), ("7_reels", t_reels)]

def main():
    mf = {}; d = os.path.join(BASE, 'html'); os.makedirs(d, exist_ok=True)
    def put(key, w, h, s):
        fp = os.path.join(d, key + '.html'); os.makedirs(os.path.dirname(fp), exist_ok=True)
        rel = os.path.relpath(BASE, os.path.dirname(fp))
        open(fp, 'w', encoding='utf-8').write(s.replace('src="logo_', 'src="%s/logo_' % rel)); mf[key] = [w, h]
    for pk, p in PALS.items():
        for i, sp in enumerate(POST3, 1): put('首篇_3張/%s_%d' % (pk, i), *post_slide(p, pk, sp, i, 3))
        for i, sp in enumerate(POST5, 1): put('首篇_5張/%s_%d' % (pk, i), *post_slide(p, pk, sp, i, 5))
        put('首篇_threads/%s' % pk, 1080, 1350, t_threads(p, pk, "談晴，也說礙", "說這一代的難，也說還在的光。", "每天說一點礙，也談一點晴")[2])
        for tid, fn in TPL:
            w, h, s = fn(p, pk); put('模板/%s/%s_%s' % (tid, tid, pk), w, h, s)
    json.dump(mf, open(os.path.join(BASE, 'manifest.json'), 'w'), ensure_ascii=False)
    json.dump(PALS, open(os.path.join(BASE, 'palettes.json'), 'w'), ensure_ascii=False, indent=1)
    print('html', len(mf))
main()
