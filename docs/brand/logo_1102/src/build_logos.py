# -*- coding: utf-8 -*-
# 產生 6 個 LOGO 方向的 SVG（中文字轉成路徑，SVG 不依賴字型）
import math, os
from fontTools.ttLib import TTCollection
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen

OUT = '/home/user/tw-rotation/docs/brand/logo_1102'
font = TTCollection('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc').fonts[0]
gs = font.getGlyphSet(); cmap = font.getBestCmap()

def gpath(ch, cx, cy, size):
    g = gs[cmap[ord(ch)]]
    bp = BoundsPen(gs); g.draw(bp)
    x0, y0, x1, y1 = bp.bounds
    s = size / max(x1 - x0, y1 - y0)
    tx = cx - (x0 + x1) / 2 * s
    ty = cy + (y0 + y1) / 2 * s
    pen = SVGPathPen(gs, ntos=lambda v: f"{v:.1f}")
    g.draw(TransformPen(pen, (s, 0, 0, -s, tx, ty)))
    return pen.getCommands(), s

def glyph_el(ch, cx, cy, size, fill, bold):
    d, s = gpath(ch, cx, cy, size)
    return f'<path d="{d}" fill="{fill}" stroke="{fill}" stroke-width="{bold:.1f}" stroke-linejoin="round"/>'

TH = {
 'dark':  dict(bg='#14213D', fg='#FFF8EA', red='#FF5257', blue='#6C9BFF', pink='#F4A582', ink='#14213D'),
 'light': dict(bg='#F7F3EA', fg='#14213D', red='#E5383B', blue='#2E5BDB', pink='#F4A582', ink='#14213D'),
}
def wrap(body, bg, label):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512" role="img" aria-label="{label}">\n'
            f'<rect width="512" height="512" fill="{bg}"/>\n{body}\n</svg>\n')

# ① 純字標「哩」＋ 一道上漲短斜線
def d1(t):
    b = glyph_el('哩', 256, 218, 262, t['fg'], 8)
    b += f'<path d="M176 424 L230 396 L262 412 L336 366" fill="none" stroke="{t["red"]}" stroke-width="22" stroke-linecap="round" stroke-linejoin="round"/>'
    return wrap(b, t['bg'], '哩股哩股 LOGO 方向一：哩字標')

# ② 輪動環：三段箭頭圈（三個族群輪流領漲），紅色那段向上
def d2(t):
    cx = cy = 256; r = 150; sw = 40; L = 58; aw = 88
    def pt(a): a = math.radians(a); return cx + r*math.sin(a), cy - r*math.cos(a)
    segs = [(248, 350, t['red']), (12, 114, t['fg']), (130, 232, t['blue'])]
    b = ''
    for s, e, col in segs:
        e2 = e - math.degrees(L / r)
        x0, y0 = pt(s); x1, y1 = pt(e2)
        b += f'<path d="M{x0:.1f} {y0:.1f} A{r} {r} 0 0 1 {x1:.1f} {y1:.1f}" fill="none" stroke="{col}" stroke-width="{sw}" stroke-linecap="butt"/>'
        a = math.radians(e2)
        tx, ty = math.cos(a), math.sin(a)       # 切線
        nx, ny = math.sin(a), -math.cos(a)      # 法線
        bx, by = x1, y1
        p1 = (bx + nx*aw/2, by + ny*aw/2); p2 = (bx - nx*aw/2, by - ny*aw/2)
        tip = (bx + tx*L, by + ty*L)
        b += f'<path d="M{p1[0]:.1f} {p1[1]:.1f} L{tip[0]:.1f} {tip[1]:.1f} L{p2[0]:.1f} {p2[1]:.1f} Z" fill="{col}" stroke="{col}" stroke-width="6" stroke-linejoin="round"/>'
    b += f'<circle cx="256" cy="256" r="34" fill="{t["red"]}"/>'
    return wrap(b, t['bg'], '哩股哩股 LOGO 方向二：輪動環')

# ③ 「哩」字＋上漲折線（組合標）
def d3(t):
    b = glyph_el('哩', 256, 172, 216, t['fg'], 7)
    pts = [(118, 420), (190, 384), (234, 406), (322, 350)]
    poly = ' '.join(f'{x},{y}' for x, y in pts)
    b += f'<polyline points="{poly}" fill="none" stroke="{t["red"]}" stroke-width="26" stroke-linecap="round" stroke-linejoin="round"/>'
    b += f'<path d="M312 322 L392 318 L360 388 Z" fill="{t["red"]}" stroke="{t["red"]}" stroke-width="8" stroke-linejoin="round"/>'
    return wrap(b, t['bg'], '哩股哩股 LOGO 方向三：哩字加上漲線')

# ④ 比比頭・單色幾何（一筆畫級）
def d4(t, dark):
    head = t['fg'] if dark else '#FFF8EA'
    ink = t['bg'] if dark else '#14213D'
    st = '' if dark else f' stroke="{ink}" stroke-width="16" stroke-linejoin="round"'
    b = ''
    # 耳朵（先畫、被頭蓋住一半）
    for ex in (128, 384):
        b += f'<circle cx="{ex}" cy="176" r="48" fill="{head}"{st}/>'
    b += f'<ellipse cx="256" cy="288" rx="172" ry="146" fill="{head}"{st}/>'
    if not dark:   # 描邊版：把耳朵與頭交界的描邊蓋掉，變成一個輪廓
        for ex in (150, 362):
            pass
    for ex in (128, 384):
        b += f'<circle cx="{ex}" cy="178" r="21" fill="{t["pink"]}"/>'
    for ex in (196, 316):
        b += f'<circle cx="{ex}" cy="270" r="17" fill="{ink}"/>'
    for ex in (150, 362):
        b += f'<circle cx="{ex}" cy="318" r="26" fill="{t["red"] if dark else t["pink"]}" opacity="0.9"/>'
    b += f'<path d="M226 316 q15 24 30 0 q15 24 30 0" fill="none" stroke="{ink}" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>'
    return wrap(b, t['bg'], '哩股哩股 LOGO 方向四：比比單色幾何頭')

# ⑤ 圓章（紅印章、哩股直排）
def d5(t):
    red = '#D6382F'
    b = f'<circle cx="256" cy="256" r="206" fill="{red}"/>'
    b += f'<circle cx="256" cy="256" r="184" fill="none" stroke="#FFF1DC" stroke-width="7"/>'
    b += glyph_el('哩', 256, 172, 138, '#FFF1DC', 4)
    b += glyph_el('股', 256, 342, 138, '#FFF1DC', 4)
    return wrap(b, t['bg'], '哩股哩股 LOGO 方向五：圓章')

# ⑥ 比比彩色可愛版＋紅 K 棒呆毛
def d6(t, dark):
    bg = '#FFC93C' if not dark else '#14213D'
    head = '#FFF8EA'; ink = '#3B2A20'; pink = '#F4A582'; ear = '#E88C6C'
    b = ''
    for ex in (138, 374):
        b += f'<circle cx="{ex}" cy="196" r="44" fill="{head}"/><circle cx="{ex}" cy="198" r="22" fill="{ear}"/>'
    cx, cy, R = 256, 306, 140
    b += f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="{head}"/>'
    n = 22
    for i in range(n):
        a = 2*math.pi*i/n
        b += f'<circle cx="{cx+(R-2)*math.cos(a):.1f}" cy="{cy+(R-2)*math.sin(a):.1f}" r="24" fill="{head}"/>'
    # 紅 K 棒呆毛（影線＋實體）
    red = '#E5383B' if not dark else '#FF5257'
    b += f'<rect x="251" y="50" width="10" height="112" rx="5" fill="{red}"/>'
    b += f'<rect x="232" y="78" width="48" height="62" rx="8" fill="{red}"/>'
    for ex in (206, 306):
        b += f'<ellipse cx="{ex}" cy="304" rx="15" ry="20" fill="{ink}"/><circle cx="{ex+5}" cy="297" r="6" fill="#fff"/>'
    for ex in (166, 346):
        b += f'<ellipse cx="{ex}" cy="344" rx="26" ry="19" fill="{pink}"/>'
    b += f'<path d="M234 338 q11 18 22 0 q11 18 22 0" fill="none" stroke="{ink}" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>'
    return wrap(b, bg, '哩股哩股 LOGO 方向六：比比彩色頭加紅K棒')

D = {
 'd1_wordmark': ('純字標「哩」', d1),
 'd2_rotation': ('輪動環', d2),
 'd3_li_rising': ('哩＋上漲線', d3),
 'd4_bibi_mono': ('比比單色幾何頭', None),
 'd5_seal': ('圓章', d5),
 'd6_bibi_color': ('比比彩色＋紅K棒', None),
}
for key, (name, fn) in D.items():
    for mode in ('dark', 'light'):
        t = TH[mode]
        if key == 'd4_bibi_mono': svg = d4(t, mode == 'dark')
        elif key == 'd6_bibi_color': svg = d6(t, mode == 'dark')
        else: svg = fn(t)
        open(f'{OUT}/{key}_{mode}.svg', 'w', encoding='utf-8').write(svg)
print('ok')
