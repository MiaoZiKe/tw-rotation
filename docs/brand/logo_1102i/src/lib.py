"""LIGU 字標共用：配色、字型輪廓取出（不描邊、不變形）、幾何筆畫字母。"""
import os, math
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, '..'))
FD = os.path.join(OUT, 'fonts')

# ---------- 配色 ----------
PAL = {
 'A': {  # 陽光糖果（品牌色）
  'light': dict(bg='#FFF7E8', fg='#1F2A44', ac='#E8590C', ac2='#2B6BF3', ac3='#7B4FE0', ac4='#0A8CA3', rd='#D8343F'),
  'dark':  dict(bg='#1F2A44', fg='#FFF7E8', ac='#FF8A3D', ac2='#6C9BFF', ac3='#B197FF', ac4='#3CC8DC', rd='#FF6070'),
 },
 'B': {  # 墨夜金紅：深墨藍＋漲紅＋金＋跌綠（我認為最適合財經／台股）
  'light': dict(bg='#F6F3EC', fg='#0E1A36', ac='#D7263D', ac2='#E39B00', ac3='#0E8F7E', ac4='#3B63E0'),
  'dark':  dict(bg='#0E1A36', fg='#F6F3EC', ac='#FF5468', ac2='#FFC247', ac3='#35D0B5', ac4='#7FA2FF'),
 },
}
PAL_NAME = {'A': '陽光糖果', 'B': '墨夜金紅'}

def _lum(h):
    h = h.lstrip('#'); r, g, b = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    f = lambda c: c / 12.92 if c <= .03928 else ((c + .055) / 1.055) ** 2.4
    return .2126 * f(r) + .7152 * f(g) + .0722 * f(b)
def contrast(a, b):
    la, lb = _lum(a), _lum(b)
    if la < lb: la, lb = lb, la
    return (la + .05) / (lb + .05)
def on(P, col):
    """在 col 色塊上，字用 bg 或 fg 中對比較高的一個"""
    return P['bg'] if contrast(P['bg'], col) >= contrast(P['fg'], col) else P['fg']

# ---------- 字型輪廓 ----------
FONTS = {
 'poppins': 'poppins-latin-800-normal.woff',
 'nunito': 'nunito-latin-900-normal.woff',
 'fredoka': 'fredoka-latin-700-normal.woff',
 'montserrat': 'montserrat-latin-800-normal.woff',
 'outfit': 'outfit-latin-700-normal.woff',
 'fraunces': 'fraunces-latin-700-normal.woff',
 'fraunces9': 'fraunces-latin-900-normal.woff',
 'huninn': 'huninn-chinese-traditional-400-normal.woff',
 'sans': 'noto-sans-tc-chinese-traditional-900-normal.woff2',
 }
_c = {}
def _font(k):
    if k not in _c: _c[k] = TTFont(os.path.join(FD, FONTS[k]))
    return _c[k]
def n2(v): return ('%.2f' % v).rstrip('0').rstrip('.')

def glyph(k, ch, size):
    """基線原點、y 向下。回傳 (d, advance, (x0,y0,x1,y1))；僅縮放與翻 y，輪廓不動。"""
    f = _font(k); cm = f.getBestCmap(); gn = cm[ord(ch)]
    s = size / f['head'].unitsPerEm; gs = f.getGlyphSet()
    sp = SVGPathPen(gs, ntos=n2); gs[gn].draw(TransformPen(sp, (s, 0, 0, -s, 0, 0)))
    bp = BoundsPen(gs); gs[gn].draw(TransformPen(bp, (s, 0, 0, -s, 0, 0)))
    return sp.getCommands(), f['hmtx'][gn][0] * s, (bp.bounds or (0, 0, 0, 0))

def run(k, text, size, track=0.0):
    """一串字：回傳 list[(ch,d,x,adv,bounds)] 與總寬（含字距 track*size）。"""
    out = []; x = 0
    for ch in text:
        d, adv, b = glyph(k, ch, size)
        out.append((ch, d, x, adv, b)); x += adv + track * size
    return out, x - track * size

# ---------- 小工具 ----------
def rad(a): return math.radians(a)
def S(d, c, sw, extra=''):
    return f'<path d="{d}" fill="none" stroke="{c}" stroke-width="{n2(sw)}" stroke-linecap="round" stroke-linejoin="round" {extra}/>'
def C(x, y, r, f, extra=''): return f'<circle cx="{n2(x)}" cy="{n2(y)}" r="{n2(r)}" fill="{f}" {extra}/>'
def R(x, y, w, h, f, r=0, extra=''): return f'<rect x="{n2(x)}" y="{n2(y)}" width="{n2(w)}" height="{n2(h)}" rx="{n2(r)}" fill="{f}" {extra}/>'
def Pth(d, f, extra=''): return f'<path d="{d}" fill="{f}" {extra}/>'
def Gp(inner, tx=0, ty=0, s=1, rot=0, ox=0, oy=0):
    return f'<g transform="translate({n2(tx)},{n2(ty)}) rotate({n2(rot)},{n2(ox)},{n2(oy)}) scale({n2(s)})">{inner}</g>'

# ---------- 幾何筆畫字母（高 100，圓頭圓角，統一筆寬）----------
def mk(sw=18):
    T = sw / 2; B = 100 - sw / 2; r = 50 - sw / 2
    dr = 0.72 * sw  # i 點半徑
    class K: pass
    k = K(); k.sw = sw; k.T = T; k.B = B; k.r = r
    def L(x0, c, foot=None):
        x = x0 + T; ln = (66 - sw) if foot is None else foot
        return S(f'M{n2(x)},{n2(T)} V{n2(B)} H{n2(x+ln)}', c, sw), 66 if foot is None else foot + sw
    def I(x0, c, dot=None, full=False):
        w = max(sw, 2 * dr) if dot else sw; x = x0 + w / 2
        top = T if (full or not dot) else 2 * dr + 0.45 * sw + T
        s = S(f'M{n2(x)},{n2(top)} V{n2(B)}', c, sw)
        if dot: s += C(x, dr, dr, dot)
        return s, w
    def G(x0, c, bar=True, a=40):
        cx = x0 + 50; cy = 50
        ex = cx + r * math.cos(rad(a)); ey = cy - r * math.sin(rad(a))
        d = f'M{n2(ex)},{n2(ey)} A{n2(r)},{n2(r)} 0 1 0 {n2(cx+r)},{n2(cy)}'
        if bar: d += f' H{n2(cx+5)}'
        return S(d, c, sw), 100
    def U(x0, c, wc=64):
        xl = x0 + T; xr = xl + wc; ra = wc / 2; cy = B - ra
        return S(f'M{n2(xl)},{n2(T)} V{n2(cy)} A{n2(ra)},{n2(ra)} 0 0 0 {n2(xr)},{n2(cy)} V{n2(T)}', c, sw), wc + sw
    k.L, k.I, k.G, k.U = L, I, G, U
    return k

def fit(inner, bounds, W, H, maxw, maxh, dy=0):
    x0, y0, x1, y1 = bounds; cw, ch = x1 - x0, y1 - y0
    s = min(maxw / cw, maxh / ch)
    tx = (W - cw * s) / 2 - x0 * s; ty = (H - ch * s) / 2 - y0 * s + dy
    return f'<g transform="translate({n2(tx)},{n2(ty)}) scale({s:.4f})">{inner}</g>'
