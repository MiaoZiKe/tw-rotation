"""文字轉向量路徑（字型輪廓原樣取出，不加粗、不變形；只做位移／縮放／旋轉）。"""
import os, math
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen
FD = os.path.join(os.path.dirname(__file__), '..', 'fonts')
FONTS = {
 'huninn': ['huninn-chinese-traditional-400-normal.woff', 'huninn-112-400-normal.woff'],
 'wk': ['lxgw-wenkai-tc-112-700-normal.woff', 'lxgw-wenkai-tc-120-700-normal.woff'],
 'serif': ['noto-serif-tc-chinese-traditional-900-normal.woff'],
 'sans': ['noto-sans-tc-chinese-traditional-900-normal.woff2'],
 'sans7': ['noto-sans-tc-chinese-traditional-700-normal.woff2'],
 'fr': ['fraunces-latin-900-normal.woff'],
 'fr7': ['fraunces-latin-700-normal.woff'],
 'inter': ['Inter-ExtraBold.otf'],
}
_c = {}
def _fonts(k):
    if k not in _c:
        _c[k] = [TTFont(os.path.join(FD, f)) for f in FONTS[k]]
    return _c[k]
def _find(k, ch):
    for f in _fonts(k):
        cm = f.getBestCmap()
        if ord(ch) in cm:
            return f, cm[ord(ch)]
    raise KeyError((k, ch))
def glyph(k, ch, size, x=0, y=0, rot=0):
    """回傳 (path d, advance, bounds(以 x,y 為原點、含縮放))"""
    f, gn = _find(k, ch)
    upm = f['head'].unitsPerEm; s = size / upm
    gs = f.getGlyphSet(); adv = f['hmtx'][gn][0] * s
    sp = SVGPathPen(gs, ntos=lambda v: ('%.2f' % v).rstrip('0').rstrip('.'))
    cr = math.cos(math.radians(rot)); sr = math.sin(math.radians(rot))
    # 本地座標 (翻 y) 再旋轉再平移
    t = (s*cr, -s*sr, s*sr*-1*-1*0 + s*sr, 0, 0, 0)  # placeholder, replaced below
    a, b, c, d = s*cr, s*sr, s*sr, -s*cr   # x' = a*gx + c*gy' ... 見下
    # 旋轉 rot（順時針為正，SVG 座標）：[x',y'] = R*[s*gx, -s*gy]
    a, b = s*cr, s*sr            # gx 影響
    c, d = s*sr, -s*cr           # gy 影響 (已含翻轉)
    tp = TransformPen(sp, (a, b, c, d, x, y))
    gs[gn].draw(tp)
    bp = BoundsPen(gs); gs[gn].draw(bp)
    bd = bp.bounds
    return sp.getCommands(), adv, (None if bd is None else (bd[0]*s, -bd[3]*s, bd[2]*s, -bd[1]*s))
def text(k, s, size, x, y, anchor='start', ls=0, rot=0, items=False):
    """水平排字；回傳 (d 串接, 總寬)。items=True 回傳每字 (ch, x0, adv, bounds)"""
    adv = []
    for ch in s:
        _, a, bd = glyph(k, ch, size)
        adv.append((ch, a, bd))
    W = sum(a for _, a, _ in adv) + ls*(len(s)-1)
    x0 = x - (W/2 if anchor == 'middle' else (W if anchor == 'end' else 0))
    ds = []; cx = x0; its = []
    for ch, a, bd in adv:
        d, _, _ = glyph(k, ch, size, cx, y)
        ds.append(d); its.append((ch, cx, a, bd)); cx += a + ls
    return (its if items else (' '.join(ds), W))
def arc_text(k, s, size, cx, cy, r, mid_deg, bottom=False, ls=0):
    """沿圓弧排字。上弧：字頭朝外；下弧：字頭朝圓心、左→右可讀。r 為基線半徑。"""
    its = text(k, s, size, 0, 0, items=True, ls=ls)
    W = its[-1][1] + its[-1][2]
    span = W / r
    ds = []
    for ch, x0, a, bd in its:
        ac = -span/2 + (x0 + a/2) / r      # 弧度，相對中軸
        # 字元以自己中心為準，基線置於原點
        if not bottom:
            ang = math.radians(mid_deg) + ac
            px, py = cx + r*math.sin(ang), cy - r*math.cos(ang)
            rot = math.degrees(ang)
        else:
            ang = math.radians(mid_deg) + ac
            px, py = cx + r*math.sin(ang), cy + r*math.cos(ang)
            rot = -math.degrees(ang)
        d, _, _ = glyph(k, ch, size, 0, 0, rot=rot)
        # 平移：把字元中心(a/2,0)擺到 (px,py)：先算旋轉後中心偏移
        cr, sr = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        ox, oy = (a/2)*cr, (a/2)*sr
        d, _, _ = glyph(k, ch, size, px-ox, py-oy, rot=rot)
        ds.append(d)
    return ' '.join(ds)
