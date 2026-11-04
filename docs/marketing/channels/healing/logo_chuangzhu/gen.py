# 「燭窗」LOGO 12 款產生器（2026-11-04）
# 全部自繪向量；文字一律轉成字形路徑（字型只用 ~/.fonts 的 OFL 字型），SVG 不依賴系統字型。
# 窗＝觀察的視角，燭＝窗裡那一點光。燭火一律畫成生活裡的暖光（燈火、窗內透出的光），不畫白燭、香爐。
import json, math, os
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen

H = os.path.dirname(os.path.abspath(__file__)); os.chdir(H)
NAME = '燭窗'; SUB = '2000 後的夜間觀察'
FONTS = {'serif': 'NotoSerifCJKtc-Bold.otf', 'sans': 'NotoSansCJKtc-Bold.otf', 'sansR': 'NotoSansCJKtc-Regular.otf',
         'serifR': 'NotoSerifCJKtc-Regular.otf', 'kai': 'LXGWWenKaiTC-Regular.ttf'}
_F = {}
def font(k):
    if k not in _F:
        f = TTFont(os.path.expanduser('~/.fonts/' + FONTS[k])); _F[k] = (f, f.getGlyphSet(), f.getBestCmap(), f['head'].unitsPerEm)
    return _F[k]
def glyph(k, ch, size, x, y):
    f, gs, cm, upm = font(k); g = gs[cm[ord(ch)]]; s = size / upm
    pen = SVGPathPen(gs); g.draw(TransformPen(pen, (s, 0, 0, -s, x, y)))
    bp = BoundsPen(gs); g.draw(TransformPen(bp, (s, 0, 0, -s, x, y)))
    return pen.getCommands(), bp.bounds, g.width * s
def text(k, s, size, x, y, ls=0):
    """回傳 (path d, bbox, 總寬)；bbox=(x0,y0,x1,y1)"""
    ds = []; bb = None; cx = x
    for ch in s:
        d, b, adv = glyph(k, ch, size, cx, y); ds.append(d)
        if b: bb = b if bb is None else (min(bb[0], b[0]), min(bb[1], b[1]), max(bb[2], b[2]), max(bb[3], b[3]))
        cx += adv + ls
    return ' '.join(ds), bb, cx - ls - x

TONES = {
    '霧紫灰': dict(bg='#4A4454', ink='#F3EEF6', mid='#A99FB8', warm='#F2D88E'),
    '深夜藍': dict(bg='#1F2A3A', ink='#F1EBDD', mid='#6F819A', warm='#F2D88E'),
    '灰綠': dict(bg='#3E4A44', ink='#EFEBDD', mid='#9BAE9F', warm='#E3C98A'),
    '米白紙': dict(bg='#F1ECE3', ink='#26232B', mid='#8F887C', warm='#E58A2E'),
    '單色黑': dict(bg='#FFFFFF', ink='#000000', mid='#000000', warm='#000000', mono=True),
    '單色白': dict(bg='#000000', ink='#FFFFFF', mid='#FFFFFF', warm='#FFFFFF', mono=True),
}

def flame(cx, top, h, w):
    y = top
    return (f'M{cx},{y} C{cx+.15*w},{y+.30*h} {cx+.5*w},{y+.50*h} {cx+.5*w},{y+.72*h} '
            f'C{cx+.5*w},{y+.92*h} {cx+.25*w},{y+h} {cx},{y+h} C{cx-.25*w},{y+h} {cx-.5*w},{y+.92*h} {cx-.5*w},{y+.72*h} '
            f'C{cx-.5*w},{y+.50*h} {cx-.15*w},{y+.30*h} {cx},{y} Z')
def ogee(l, r, bot, top, shoulder):
    """火苗形拱（燈火／拱窗同形）：左右 l、r，底 bot，尖 top，肩高 shoulder"""
    c = (l + r) / 2
    return (f'M{l},{bot} L{l},{shoulder} C{l},{shoulder-14} {c-13},{top+22} {c},{top} '
            f'C{c+13},{top+22} {r},{shoulder-14} {r},{shoulder} L{r},{bot} Z')

# ---------------- 12 款圖形（100×100，安全圓半徑 40，中心 50,50）----------------
CHK = {}   # 款 → 程式檢查項目（名稱, 是否通過）
def seg_hits_rect(p, q, rc, mg=0):
    x0, y0, x1, y1 = rc[0]-mg, rc[1]-mg, rc[2]+mg, rc[3]+mg
    for i in range(41):
        t = i/40; x = p[0]+(q[0]-p[0])*t; y = p[1]+(q[1]-p[1])*t
        if x0 <= x <= x1 and y0 <= y <= y1: return True
    return False
def rect_hit(a, b, mg=0): return not (a[2]+mg <= b[0] or b[2]+mg <= a[0] or a[3]+mg <= b[1] or b[3]+mg <= a[1])

def ic1(P):
    I, M, W, B = P['ink'], P['mid'], P['warm'], P['bg']
    pane = '' if P.get('mono') else f'<rect x="26" y="24" width="22" height="24" fill="{M}" opacity=".28"/><rect x="52" y="24" width="22" height="24" fill="{M}" opacity=".28"/><rect x="26" y="52" width="22" height="24" fill="{M}" opacity=".28"/><rect x="52" y="52" width="22" height="24" fill="{W}" opacity=".22"/>'
    return (f'{pane}<path d="{flame(63, 56, 18, 11)}" fill="{W}"/>'
            f'<rect x="24" y="22" width="52" height="56" rx="5" fill="none" stroke="{I}" stroke-width="4.6"/>'
            f'<path d="M50 22V78M24 50H76" stroke="{I}" stroke-width="4" fill="none"/>')
def ic2(P):
    I, W, B = P['ink'], P['warm'], P['bg']
    return (f'<path d="{flame(50, 14, 66, 50)}" fill="{W}" stroke="{I}" stroke-width="4.2" stroke-linejoin="round"/>'
            f'<path d="M22 50H78M22 60H78M22 70H78" stroke="{B}" stroke-width="3"/>'
            f'<path d="M34 85H66" stroke="{I}" stroke-width="3.8" stroke-linecap="round"/>')
def ic3(P):
    I, W, B = P['ink'], P['warm'], P['bg']
    return (f'<rect x="24" y="24" width="52" height="52" rx="4" fill="none" stroke="{I}" stroke-width="4.6"/>'
            f'<path d="{flame(50, 29, 42, 34)}" fill="{W}"/>'
            f'<path d="M50 36V70M34 55H66" stroke="{B}" stroke-width="3"/>')
def ic4_parts(P, S, x, y):
    """燭字：火字旁換成窗外的雨（三道斜線），右半「蜀」的虫字口裡亮一點光。回傳 (svg, 各部件 bbox, 整體 bbox)"""
    I, M, W, B = P['ink'], P['mid'], P['warm'], P['bg']
    gx = x + S*0.36
    d, bb, adv = glyph('serif', '蜀', S, gx, y)
    h = bb[3]-bb[1]
    rain = ''; rb = []
    for fx, y0, ln in [(0.07, 0.22, 0.34), (0.19, 0.10, 0.46), (0.31, 0.30, 0.38)]:
        x0 = x + S*fx; ya = bb[1] + h*y0; yb = ya + h*ln
        x1 = x0 - S*0.07
        rain += f'<path d="M{x0:.2f},{ya:.2f} L{x1:.2f},{yb:.2f}" stroke="{M}" stroke-width="{S*0.07:.2f}" stroke-linecap="round" fill="none"/>'
        rb.append((x1 - S*0.035, ya - S*0.035, x0 + S*0.035, yb + S*0.035))
    hx = bb[0] + (bb[2]-bb[0])*0.56; hy = bb[1] + h*0.605
    dot = f'<circle cx="{hx:.2f}" cy="{hy:.2f}" r="{S*0.05:.2f}" fill="{W}"/>'
    svg = f'<path d="{d}" fill="{I}"/>{rain}{dot}'
    rbb = (min(r[0] for r in rb), min(r[1] for r in rb), max(r[2] for r in rb), max(r[3] for r in rb))
    box = dict(glyph=bb, rain=rbb)
    whole = (rbb[0], bb[1], bb[2], bb[3])
    return svg, box, whole
def ic4(P):
    svg, box, bb = ic4_parts(P, 50, 14, 20 + 50*0.88)
    gx = (bb[0]+bb[2])/2; gy = (bb[1]+bb[3])/2
    CHK[4] = [('雨線外框與「蜀」字外框不相交', not rect_hit(box['rain'], box['glyph'], 1))]
    return f'<g transform="translate({50-gx+14-14:.2f},{50-gy:.2f})">{svg}</g>'
def ic5(P):
    I, M, W, B = P['ink'], P['mid'], P['warm'], P['bg']
    win = (31, 46, 69, 80)
    rain = ''; n = 0; bad = 0
    ys = [14, 20, 26, 32]
    for r, y0 in enumerate(range(13, 78, 12)):
        for x0 in range(14 + (r % 2)*5, 90, 10):
            p = (x0, y0); q = (x0-3.6, y0+9)
            if math.hypot(p[0]-50, p[1]-50) > 38 or math.hypot(q[0]-50, q[1]-50) > 38: continue
            if seg_hits_rect(p, q, win, 5): continue
            rain += f'<path d="M{p[0]},{p[1]} L{q[0]},{q[1]}" stroke="{M}" stroke-width="2.6" stroke-linecap="round"/>'; n += 1
    CHK[5] = [(f'雨線 {n} 條皆距窗框 ≥5', True)]
    return (rain + f'<rect x="31" y="46" width="38" height="34" rx="2" fill="{W}" stroke="{I}" stroke-width="4.2"/>'
            f'<path d="M50 46V80M31 63H69" stroke="{B}" stroke-width="3"/>')
def ic6(P):
    I, M, W, B = P['ink'], P['mid'], P['warm'], P['bg']
    def fig(cx, lean):
        return (f'<circle cx="{cx+lean}" cy="40" r="6" fill="{I}"/>'
                f'<path d="M{cx-9},74 C{cx-9},56 {cx-5},50 {cx+lean},50 C{cx+9+lean},50 {cx+9},56 {cx+9},74 Z" fill="{I}"/>')
    CHK[6] = [('左人影(21–39) / 燈(43–57) / 右人影(61–79) 外框互不相交', not rect_hit((21, 34, 39, 74), (43, 43, 57, 74), 3) and not rect_hit((43, 43, 57, 74), (61, 34, 79, 74), 3))]
    return (fig(30, 3) + fig(70, -3) +
            f'<path d="{flame(50, 44, 16, 9)}" fill="{W}"/>'
            f'<path d="M45 64C45 59 55 59 55 64Z" fill="{I}"/>'
            f'<path d="M44 66H56M46 66V74M54 66V74" stroke="{I}" stroke-width="3" stroke-linecap="round"/>'
            f'<path d="M20 76H80" stroke="{M}" stroke-width="3" stroke-linecap="round"/>')
def ic7(P):
    I, W, B = P['ink'], P['warm'], P['bg']
    a, ba, _ = glyph('serif', '燭', 25, 0, 0); b, bb, _ = glyph('serif', '窗', 25, 0, 0)
    ga, gb = glyph('serif', '燭', 25, 34.5, 45)[0], glyph('serif', '窗', 25, 34.5, 74)[0]
    return (f'<defs><filter id="rough" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency="0.7" numOctaves="2" seed="4"/><feDisplacementMap in="SourceGraphic" scale="1.3"/></filter></defs>'
            f'<g filter="url(#rough)"><rect x="29" y="17" width="37" height="62" rx="2.5" fill="{I}"/>'
            f'<path d="{ga}" fill="{B}"/><path d="{gb}" fill="{B}"/></g>'
            f'<circle cx="66" cy="79" r="4.6" fill="{W}" stroke="{B}" stroke-width="1.6"/>')
def ic8(P):
    I, W = P['ink'], P['warm']
    a = glyph('kai', '燭', 32, 34, 49)[0]; b = glyph('kai', '窗', 32, 34, 82)[0]
    return (f'<defs><filter id="brush" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="9"/><feDisplacementMap in="SourceGraphic" scale="1.1"/></filter></defs>'
            f'<g filter="url(#brush)"><path d="{a}" fill="{I}"/><path d="{b}" fill="{I}"/></g>'
            f'<circle cx="74" cy="76" r="3.4" fill="{W}"/>')
def ic9(P):
    I, W = P['ink'], P['warm']
    d = ('M26 80V46A24 24 0 0 1 74 46V80H37V50A13 13 0 0 1 63 50V68H50')
    return (f'<path d="{d}" fill="none" stroke="{I}" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="{flame(50, 43, 20, 12)}" fill="{W}"/>')
def ic10(P):
    I, W, B = P['ink'], P['warm'], P['bg']
    cuts = ''.join(f'<path d="M{x},{y-6.5}L{x+4.2},{y}L{x},{y+6.5}L{x-4.2},{y}Z" fill="{B}"/>' for x, y in [(50, 31), (50, 69), (31, 50), (69, 50)])
    cuts += ''.join(f'<circle cx="{x}" cy="{y}" r="3.4" fill="{B}"/>' for x, y in [(33, 33), (67, 33), (33, 67), (67, 67)])
    scal = ''.join(f'<circle cx="{x}" cy="{y}" r="2.1" fill="{B}"/>' for x, y in [(41, 25.5), (59, 25.5), (41, 74.5), (59, 74.5), (25.5, 41), (25.5, 59), (74.5, 41), (74.5, 59)])
    return (f'<rect x="24" y="24" width="52" height="52" rx="3" fill="{I}"/>{cuts}{scal}'
            f'<circle cx="50" cy="50" r="12.6" fill="{B}"/><path d="{flame(50, 41, 18, 11)}" fill="{W}"/>')
def ic11(P):
    I, M, W, B = P['ink'], P['mid'], P['warm'], P['bg']
    poem = '何當共剪西窗燭卻話巴山夜雨時'; slots = 16; ring = ''
    order = list(poem[:7]) + ['·'] + list(poem[7:]) + ['·']
    for i, ch in enumerate(order):
        ang = i*360/slots + 360/slots/2
        if ch == '·':
            ring += f'<g transform="translate(50,50) rotate({ang}) translate(0,-31.5)"><circle r="1" fill="{W}"/></g>'
        else:
            d, bb, adv = glyph('sansR', ch, 8.2, -4.1, 0)
            ring += f'<g transform="translate(50,50) rotate({ang}) translate(0,-27.8)"><path d="{d}" fill="{I}"/></g>'
    return (f'<circle cx="50" cy="50" r="38.4" fill="none" stroke="{I}" stroke-width="2.4"/><circle cx="50" cy="50" r="25.2" fill="none" stroke="{M}" stroke-width="1.6"/>{ring}'
            f'<path d="M41 64V46A9 9 0 0 1 59 46V64Z" fill="none" stroke="{I}" stroke-width="2.6" stroke-linejoin="round"/>'
            f'<path d="{flame(50, 46, 13, 8)}" fill="{W}"/><path d="M39.5 66.5H60.5" stroke="{I}" stroke-width="2.6" stroke-linecap="round"/>')
def ic12(P):
    I, M, W, B = P['ink'], P['mid'], P['warm'], P['bg']
    return (f'<path d="{flame(50, 16, 36, 22)}" fill="{W}"/>'
            f'<path d="M22 56H78" stroke="{I}" stroke-width="3.4" stroke-linecap="round"/>'
            f'<g transform="translate(0,56) scale(1,-0.7) translate(0,-56)"><path d="{flame(50, 16, 36, 22)}" fill="none" stroke="{M}" stroke-width="3" stroke-linejoin="round"/></g>'
            f'<path d="M50 62V80M41 70H59" stroke="{M}" stroke-width="2.6"/>')

DESIGNS = [
 dict(n=1, name='窗格亮一格', style='幾何窗格', ic=ic1, tf='sans', mean='四格窗是觀察的視角，其中一格亮著燭火：窗裡那一點光。', human='窗格＋亮格', hand='幾何：四格窗，一格暖光'),
 dict(n=2, k=0.96, name='火苗即拱窗', style='極簡線條', ic=ic2, tf='sans', mean='燭火的外形加上三道窗櫺，火苗同時是一扇窗：光就是看出去的視角。', hand='極簡線條：火苗形的窗＋三道橫櫺＋窗台'),
 dict(n=3, name='窗櫺切火苗', style='負空間', ic=ic3, tf='sans', mean='十字窗櫺把一朵火苗切成四格：看這一代的方式，本身就是光。', hand='負空間：窗櫺是切出來的留白'),
 dict(n=4, name='燭字拆雨', style='字體設計', ic=ic4, tf='serif', mean='「燭」的火字旁換成窗外的雨，蜀裡亮一點光：雨在外頭，光在窗裡。', hand='字體設計：宋體「燭」拆掉火旁'),
 dict(n=5, name='夜雨窗光', style='夜雨插畫', ic=ic5, tf='kai', mean='窗外斜斜的雨，窗內一點暖光：站在窗邊觀察的人。', hand='線稿插畫：雨線＋暖窗'),
 dict(n=6, k=0.9, name='對坐小燈', style='人影剪影', ic=ic6, tf='serif', mean='兩個抽象人影圍著一盞小燈對坐，從窗邊一起談這一代。', hand='剪影：兩人＋小桌上的燈火'),
 dict(n=7, name='觀察家的印', style='篆刻印章', ic=ic7, tf='serif', mean='白文印「燭窗」，缺角處一點暖光：觀察家的落款。', hand='白文印（宋體仿篆）＋毛邊'),
 dict(n=8, name='直書一點光', style='書法直排', ic=ic8, tf='kai', mean='直書「燭窗」，字旁一點光像落款：慢慢說這一代的事。', hand='直排楷書＋筆邊毛糙'),
 dict(n=9, k=0.96, name='一筆收光', style='一筆畫', ic=ic9, tf='sansR', mean='一筆畫出窗，一圈圈收向中心：把累收進去，只留最後那點光。', hand='一筆連續線（拱形漸縮）'),
 dict(n=10, name='燭光窗花', style='剪紙窗花', ic=ic10, tf='serif', mean='窗花剪出一圈孔，中心孔透出燭光：從紙窗看出去的觀察。', hand='剪紙：四向對稱窗花'),
 dict(n=11, name='夜雨徽章', style='復古徽章', ic=ic11, tf='serif', mean='外環刻〈夜雨寄北〉兩句，中心拱窗裡一點光：窗邊笑談往事。', hand='圓形徽章＋環字'),
 dict(n=12, name='倒影成窗', style='倒影符號', ic=ic12, tf='sans', mean='燭火倒映在玻璃上，倒影成了一扇窗：光與視角是同一件事。', hand='符號：火苗與倒影窗'),
]
# 第 9 款再加中心火苗（螺旋端點），其餘不動
def ic9b(P):
    base = ic9(P)
    return base.replace('r="0"', 'r="0"') + f'<path d="{flame(50, 52, 9, 6)}" fill="{P["warm"]}" opacity="0"/>'

def wrap_icon(d, P, tx=0, ty=0, s=1):
    return f'<g transform="translate({tx},{ty}) scale({s})">{d["ic"](P)}</g>'

def icon_k(d, P):
    k = d.get('k', 1)
    return d['ic'](P) if k == 1 else f'<g transform="translate({50-50*k:.2f},{50-50*k:.2f}) scale({k})">{d["ic"](P)}</g>'
def avatar_svg(d, P):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="1080" height="1080">'
            f'<rect width="100" height="100" fill="{P["bg"]}"/>{icon_k(d, P)}</svg>')

def wordmark(d, P, sub, transparent=False):
    """回傳 (svg, W, H, boxes dict)；boxes 皆為字標座標系"""
    I, M, W_, B = P['ink'], P['mid'], P['warm'], P['bg']
    n = d['n']; boxes = {}; body = ''
    subd = None
    if sub:
        sd, sbb, sw = text('sansR', SUB, 26, 0, 0, 4)
    # 標題：自訂或預設
    if n == 7:   # 橫式白文印
        I_, W2 = I, W_
        ga, ba, _ = glyph('serif', '燭', 80, 36, 114); gb, bb2, _ = glyph('serif', '窗', 80, 122, 114)
        title = (f'<defs><filter id="rough" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency="0.5" numOctaves="2" seed="4"/><feDisplacementMap in="SourceGraphic" scale="2"/></filter></defs>'
                 f'<g filter="url(#rough)"><rect x="24" y="30" width="196" height="108" rx="6" fill="{I}"/><path d="{ga}" fill="{B}"/><path d="{gb}" fill="{B}"/></g>'
                 f'<circle cx="220" cy="138" r="13" fill="{W2}" stroke="{B}" stroke-width="4"/>')
        boxes['title'] = (24, 30, 233, 151); tr = 233; tb = (30, 151)
    elif n == 8:
        a, ba, adv = text('kai', NAME, 104, 28, 120, 6)
        title = (f'<defs><filter id="brush" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="9"/><feDisplacementMap in="SourceGraphic" scale="2"/></filter></defs>'
                 f'<g filter="url(#brush)"><path d="{a}" fill="{I}"/></g><circle cx="{28+adv+22:.1f}" cy="116" r="7" fill="{W_}"/>')
        boxes['title'] = (ba[0], ba[1], 28+adv+29, max(ba[3], 123)); tr = 28+adv+29; tb = (ba[1], ba[3])
    elif n == 99:
        S = 104; ox = 24; by = 128
        svg4, box, bb = ic4_parts(P, S, ox, by)
        d2, b2, adv2 = glyph('serif', '窗', S, bb[2] + 8, by)
        title = svg4 + f'<path d="{d2}" fill="{I}"/>'
        boxes['title'] = (bb[0], bb[1], b2[2], bb[3]); tr = b2[2]; tb = (bb[1], bb[3])
        boxes['雨線'] = box['rain']; boxes['蜀'] = box['glyph']; boxes['窗'] = b2
    else:
        sc = 1.8
        title_d, tbb, tw = text(d['tf'], NAME, 100, 232, 0, 12)
        title = f'<g transform="translate(18,20) scale({sc})">{icon_k(d, P)}</g>' if n != 4 else ''
        boxes['icon'] = (18, 20, 18+100*sc, 20+100*sc)
        tr = None; tb = None
    # 預設款：文字
    if n not in (7, 8):
        TX = 120 if n == 4 else 232
        tdd, tbb, tw = text(d['tf'], NAME, 100, TX, 0, 12)
        th = tbb[3]-tbb[1]
        if sub: tot = th + 24 + (sbb[3]-sbb[1]); top = (220-tot)/2
        else: top = (220-th)/2
        ty = top - tbb[1]
        tdd, tbb, tw = text(d['tf'], NAME, 100, TX, ty, 12)
        title += f'<path d="{tdd}" fill="{I}"/>'
        if n == 4:   # 雨落在字的左邊（取代火字旁的位置），窗字中心亮一點光
            h_ = tbb[3]-tbb[1]; rb = []
            for fx, y0, ln in [(34, .16, .50), (54, .04, .62), (74, .24, .52)]:
                ya = tbb[1]+h_*y0; yb = ya+h_*ln; title += f'<path d="M{fx+9},{ya:.1f} L{fx-3},{yb:.1f}" stroke="{M if not P.get("mono") else I}" stroke-width="7" stroke-linecap="round"/>'; rb.append((fx-7, ya-4, fx+13, yb+4))
            boxes['icon'] = (min(r[0] for r in rb), min(r[1] for r in rb), max(r[2] for r in rb), max(r[3] for r in rb))
            _, wb, _ = glyph('serif', '窗', 100, TX + 100 + 12, ty)
            title += f'<circle cx="{(wb[0]+wb[2])/2:.1f}" cy="{wb[1]+(wb[3]-wb[1])*.70:.1f}" r="5" fill="{W_}"/>'
        boxes['title'] = tbb; tr = tbb[2]; tb = (tbb[1], tbb[3])
        if sub:
            sy = tbb[3] + 24 - sbb[1]
            sdd, sbb2, sw = text('sansR', SUB, 26, 232, sy, 4)
            body_sub = f'<path d="{sdd}" fill="{M if not P.get("mono") else I}"/>'
            title += body_sub; boxes['sub'] = sbb2
            tr = max(tr, sbb2[2])
        W = int(math.ceil(tr + 30)); H = 220
    else:
        # 自訂款：副標置於標題下方
        top_t, bot_t = tb
        H = 220
        if n == 7:
            # 垂直置中
            off = (H - (bot_t - top_t) - ( (24 + (sbb[3]-sbb[1])) if sub else 0)) / 2 - top_t
        else:
            off = (H - (bot_t - top_t) - ( (24 + (sbb[3]-sbb[1])) if sub else 0)) / 2 - top_t
        title = f'<g transform="translate(0,{off:.2f})">{title}</g>'
        for k in list(boxes): boxes[k] = (boxes[k][0], boxes[k][1]+off, boxes[k][2], boxes[k][3]+off)
        if sub:
            sy = bot_t + off + 24 - sbb[1]
            sdd, sbb2, sw = text('sansR', SUB, 26, boxes['title'][0] if n != 7 else 30, sy, 4)
            title += f'<path d="{sdd}" fill="{M if not P.get("mono") else I}"/>'
            boxes['sub'] = sbb2; tr = max(tr, sbb2[2])
        W = int(math.ceil(tr + 28))
    bgr = '' if transparent else f'<rect width="{W}" height="{H}" fill="{B}"/>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">{bgr}{title}</svg>', W, H, boxes

if __name__ == '__main__':
    jobs = []; meta = []; boxes_all = {}
    for d in DESIGNS:
        fo = f'{d["n"]:02d}_{d["name"]}'; os.makedirs(fo, exist_ok=True)
        meta.append(dict(n=d['n'], name=d['name'], dir=fo, style=d['style'], mean=d['mean']))
        for tn, P in TONES.items():
            s = avatar_svg(d, P); p = f'{fo}/頭像_1080_{tn}'
            open(p + '.svg', 'w', encoding='utf-8').write(s); jobs.append(dict(svg=p+'.svg', png=p+'.png', w=1080, h=1080, kind='avatar', n=d['n'], tag=tn))
            for sub, lab in ((False, '字標'), (True, '字標_副標')):
                s, W, Hh, bx = wordmark(d, P, sub); p = f'{fo}/{lab}_{tn}'
                open(p + '.svg', 'w', encoding='utf-8').write(s)
                jobs.append(dict(svg=p+'.svg', png=p+'.png', w=W, h=Hh, kind='wm', n=d['n'], tag=tn, sub=sub, W=W, H=Hh))
                boxes_all[p] = bx
        for sub, lab in ((False, '字標_透明'), (True, '字標_副標_透明')):
            s, W, Hh, bx = wordmark(d, TONES['霧紫灰'], sub, True); p = f'{fo}/{lab}_霧紫灰'
            open(p + '.svg', 'w', encoding='utf-8').write(s); jobs.append(dict(svg=p+'.svg', png=p+'.png', w=W, h=Hh, transparent=True, kind='wmT', n=d['n'], tag='霧紫灰', sub=sub))
    json.dump(dict(jobs=jobs, meta=meta, tones=TONES, boxes=boxes_all, chk={str(k): v for k, v in CHK.items()}), open('jobs.json', 'w', encoding='utf-8'), ensure_ascii=False)
    print(len(jobs), 'jobs')
