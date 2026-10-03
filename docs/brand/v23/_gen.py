# 第二十三輪〈股立方〉：簡約 2.5D —— 等角投影的平塗立方，三個可見面各切兩塊面板＝六個面向。
# 客戶原話：「立方體，需要 2.5D 呈現，但不能過於 3D，且需要專業的感覺，且融合資金、產業、技術、籌碼、消息、基本等 6 面向，
#           AI 感不能太多。色系不用太花俏，單調簡單，舒服。」
#
# 跟 v18～v22 刻意相反的地方（那幾輪被嫌太花、太 AI）：
#   · 沒有漸層、發光、玻璃透明、反光條、投影、刻度環、角框、模糊濾鏡 —— 只有平塗色塊與同粗線條。
#   · 立方是正確的等角投影（30°／90°／150°），三個可見面用同一色相的不同明度區分。
#   · 面上的圖示不是用 SVG transform 貼上去的（那樣線條會被斜切得粗細不一、圓頭變橢圓），
#     而是把圖示的每一個控制點用仿射矩陣投影到面上、再用「畫面座標」的固定線寬描邊 ——
#     所以投影後的線條跟立方的輪廓線一樣粗，端點仍是正圓頭，像手繪的等角插畫。
#
# 面板分組（每一面上下／左右切兩半）：
#   頂面＝看大局：資金｜產業    左面＝看交易：技術／籌碼    右面＝看公司：基本／消息
#
# 三個方向：A 六格立方（平塗＋面上圖示）、B 單線立方（純線稿）、C 刻面立方（只有六塊明度，圖示放旁邊說明）
# 色系：墨藍（主推）、石墨灰、深青 —— 每組一個色相 × 六個明度＋白；明度用 WCAG 相對亮度反推，
#       同一面兩塊對比 1.32:1、跨面 ≥1.8:1，所以「明度相近但可分辨」是算出來的、不是目測的。
#
# 需要：pip install fonttools playwright（只有產生器要用，網站不用）
# 執行：BRAND_SCRATCH=<暫存資料夾> python docs/brand/v23/_gen.py
import math, os, json
from fontTools.ttLib import TTCollection, TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen

HERE = os.path.dirname(os.path.abspath(__file__))
SCRATCH = os.environ.get('BRAND_SCRATCH', '/tmp')
os.makedirs(SCRATCH, exist_ok=True)
S60 = math.sin(math.radians(60))
C30, S30 = math.cos(math.radians(30)), 0.5


# =====================================================================================
# 色彩：WCAG 相對亮度、對比、同色相明度階
# =====================================================================================
def hx(c): return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
def to_hex(rgb): return '#%02x%02x%02x' % tuple(max(0, min(255, round(v))) for v in rgb)
def _lin(v):
    v /= 255; return v/12.92 if v <= .04045 else ((v + .055)/1.055)**2.4
def lum(c):
    r, g, b = hx(c); return .2126*_lin(r) + .7152*_lin(g) + .0722*_lin(b)
def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True); return (la + .05)/(lb + .05)
def _oklab(c):
    r, g, b = (_lin(v) for v in hx(c))
    l = (.4122214708*r + .5363325363*g + .0514459929*b)**(1/3); m = (.2119034982*r + .6806995451*g + .1073969566*b)**(1/3)
    s = (.0883024619*r + .2817188376*g + .6299787005*b)**(1/3)
    return (.2104542553*l + .7936177850*m - .0040720468*s, 1.9779984951*l - 2.4285922050*m + .4505937099*s, .0259040371*l + .7827717662*m - .8086757660*s)


def _from_oklab(L, A, B):
    l, m, s = (L + .3963377774*A + .2158037573*B)**3, (L - .1055613458*A - .0638541728*B)**3, (L - .0894841775*A - 1.2914855480*B)**3
    rgb = (4.0767416621*l - 3.3077115913*m + .2309699292*s, -1.2684380046*l + 2.6097574011*m - .3413193965*s, -.0041960771*l - .7034186147*m + 1.7076147010*s)
    f = lambda v: 12.92*v if v <= .0031308 else 1.055*max(v, 0)**(1/2.4) - .055
    return to_hex([f(v)*255 for v in rgb])


def mix(a, b, t, bump=0.0):
    """在 OKLCH 裡內插：色相固定用暗端的色相，彩度線性內插再在中段略加一點（sin 拱形）——
    直接在 sRGB 裡內插，中間調會掉色變成灰；這樣墨藍的中間調仍看得出是藍、不是灰"""
    La, Aa, Ba = _oklab(a); Lb, Ab, Bb = _oklab(b)
    ca, cb = math.hypot(Aa, Ba), math.hypot(Ab, Bb); h = math.atan2(Bb, Ab)
    L = La + (Lb - La)*t; C = ca + (cb - ca)*t + bump*math.sin(math.pi*t)
    return _from_oklab(L, C*math.cos(h), C*math.sin(h))




def solve(c0, c1, Y, bump=0.0):
    """在 c0→c1 的 OKLCH 路徑上找相對亮度＝Y 的那一點（c0 亮、c1 暗；同色相兩端，所以中間仍是同一色相）"""
    lo, hi = 0.0, 1.0
    for _ in range(40):
        m = (lo + hi)/2
        if lum(mix(c0, c1, m, bump)) > Y: lo = m
        else: hi = m
    return mix(c0, c1, (lo + hi)/2, bump)


RW = 1.32   # 同一面兩塊面板的對比（「相近但可分辨」；規格下限 1.3）


def ramp(l0, l5, bump=0.0):
    """六個明度：L0,L1＝頂面、L2,L3＝左面、L4,L5＝右面。同面相鄰 RW、跨面 RB，RW³·RB²＝L0 對 L5 的總對比"""
    Y0, Y5 = lum(l0), lum(l5)
    R = (Y0 + .05)/(Y5 + .05)
    rb = math.sqrt(R/RW**3)
    ys, y = [Y0], Y0
    for r in (RW, rb, RW, rb):
        y = (y + .05)/r - .05; ys.append(y)
    return [l0] + [solve(l0, l5, v, bump) for v in ys[1:]] + [l5]


# 每組：ink＝最深色（線、字、深底 App 圖示的底）、light＝深面板上的線色、l0／l5＝面板明度兩端
PALETTES = {
    'ink':      dict(name='墨藍', ink='#1f2d3d', light='#f5f7f9', l0='#e9eef3', l5='#2b3a4b', mute='#6b7a8a', bump=.012),
    'graphite': dict(name='石墨灰', ink='#2a2927', light='#f6f5f3', l0='#ecebe8', l5='#3a3835', mute='#7a7671', bump=.0),   # 石墨灰不加彩度拱形，免得中間調偏米色
    'teal':     dict(name='深青', ink='#1d3b3a', light='#f3f7f6', l0='#e5eeed', l5='#2b4a48', mute='#62807d', bump=.010),
}
for _p in PALETTES.values():
    _p['tones'] = ramp(_p['l0'], _p['l5'], _p['bump'])
    # 深底版（App 圖示深色款）：最暗那塊面板若照用 l5，跟深底只差 1.2:1、右面會消失 → 另算一組，最暗面板對深底 ≥1.6:1
    y5 = (lum(_p['ink']) + .05)*1.6 - .05
    _p['dark_tones'] = ramp(_p['l0'], solve(_p['l0'], _p['l5'], y5, _p['bump']), _p['bump'])


# =====================================================================================
# 向量路徑：只用 M／L／C／Z，所以任何仿射投影都是精確的（投影控制點即可）
# =====================================================================================
class Path:
    def __init__(self): self.seg = []; self.cur = (0, 0)
    def M(self, x, y): self.seg.append(('M', [(x, y)])); self.cur = (x, y); return self
    def L(self, x, y): self.seg.append(('L', [(x, y)])); self.cur = (x, y); return self
    def H(self, x): return self.L(x, self.cur[1])
    def V(self, y): return self.L(self.cur[0], y)
    def C(self, x1, y1, x2, y2, x, y): self.seg.append(('C', [(x1, y1), (x2, y2), (x, y)])); self.cur = (x, y); return self
    def Z(self): self.seg.append(('Z', [])); return self

    def arc(self, cx, cy, rx, ry, a0, a1):
        """從目前點（應在 a0 角上）沿橢圓畫到 a1（度；畫面座標 y 朝下，90°＝正下方）。每段 ≤90° 用一條三次貝茲近似"""
        n = max(1, math.ceil(abs(a1 - a0)/90 - 1e-9)); da = (a1 - a0)/n
        k = 4/3*math.tan(math.radians(da)/4)
        for i in range(n):
            t0, t1 = math.radians(a0 + da*i), math.radians(a0 + da*(i + 1))
            p0 = (cx + rx*math.cos(t0), cy + ry*math.sin(t0)); p3 = (cx + rx*math.cos(t1), cy + ry*math.sin(t1))
            p1 = (p0[0] - k*rx*math.sin(t0), p0[1] + k*ry*math.cos(t0))
            p2 = (p3[0] + k*rx*math.sin(t1), p3[1] - k*ry*math.cos(t1))
            self.C(*p1, *p2, *p3)
        return self

    def d(self, T=lambda p: p, nd=2):
        o = []
        for c, ps in self.seg:
            o.append(c + ' '.join(f'{T(p)[0]:.{nd}f} {T(p)[1]:.{nd}f}' for p in ps))
        return ''.join(o)


def rrect(x, y, w, h, r):
    p = Path().M(x + r, y).H(x + w - r).arc(x + w - r, y + r, r, r, -90, 0).V(y + h - r).arc(x + w - r, y + h - r, r, r, 0, 90)
    return p.H(x + r).arc(x + r, y + h - r, r, r, 90, 180).V(y + r).arc(x + r, y + r, r, r, 180, 270).Z()


def circle(cx, cy, r):
    return Path().M(cx + r, cy).arc(cx, cy, r, r, 0, 360).Z()


def line(*pts):
    p = Path().M(*pts[0])
    for q in pts[1:]: p.L(*q)
    return p


# =====================================================================================
# 六個面向的單線圖示（24×24 格線、線寬 1.75、圓頭圓角；只有「實心」與「線」兩種元素）
# 每個元素：(Path, 填色？, 描邊？)。填色一律用前景色；不需要「底色填滿」—— 疊放的地方都設計成不互相穿線。
# =====================================================================================
SW = 1.75


def ic_capital():   # 資金：左邊一個來源點，分流成三條線到右邊三個族群（桑基的最簡形）
    o = [(circle(4.5, 12, 2.25), True, False)]
    o.append((Path().M(4.5, 12).C(11, 12, 11.5, 5.75, 17.5, 5.75), False, True))
    o.append((line((4.5, 12), (17.5, 12)), False, True))
    o.append((Path().M(4.5, 12).C(11, 12, 11.5, 18.25, 17.5, 18.25), False, True))
    for y in (5.75, 12, 18.25): o.append((circle(19.5, y, 2), True, False))
    return o


def ic_industry():  # 產業：晶片 —— 方框、每邊兩根針腳、內方塊（兩根針腳對齊內方塊的兩條邊）
    o = [(rrect(6.5, 6.5, 11, 11, 2), False, True), (rrect(9.75, 9.75, 4.5, 4.5, 1), False, True)]
    pins = Path()
    for t in (10, 14):
        pins.M(t, 6.5).V(3.5).M(t, 17.5).V(20.5).M(6.5, t).H(3.5).M(17.5, t).H(20.5)
    o.append((pins, False, True))
    return o


def ic_technical():  # 技術：三根 K 棒，空心＝漲、實心＝跌（品牌是單色系，不用紅綠）；整體往右上
    o = []
    for x, wt, wb, bt, bb, solid in ((5.5, 10.5, 20.5, 13, 18, False), (12, 7, 16.5, 9, 13.5, True), (18.5, 3.5, 13.5, 5.5, 11, False)):
        o.append((line((x, wt), (x, bt)), False, True))
        o.append((line((x, bb), (x, wb)), False, True))
        o.append((rrect(x - 2.25, bt, 4.5, bb - bt, .75), solid, True))   # 實體寬 4.5：空心那兩根扣掉線寬後裡面還留 2.75
    return o


def ic_chips():     # 籌碼：三片疊起來的扁圓柱（只畫看得到的線：最上面一片的整圈＋每片的側邊與下緣弧線）
    o = []
    for y in (14, 10, 6):
        o.append((Path().M(5, y).V(y + 4).arc(12, y + 4, 7, 2.5, 180, 0).V(y), False, True))
    o.append((Path().M(19, 6).arc(12, 6, 7, 2.5, 0, 360).Z(), False, True))
    return o


def ic_news():      # 消息：報紙 —— 正面一頁＋左邊露出的摺頁，頁內一條標題線、一塊圖片、三行短字
    page = Path().M(5.5, 19.5).H(18).arc(18, 17.5, 2, 2, 90, 0).V(6.5).arc(18, 6.5, 2, 2, 0, -90).H(9).arc(9, 6.5, 2, 2, 270, 180)
    page.V(18).arc(5.5, 18, 1.5, 1.5, 0, 90).arc(5.5, 18, 1.5, 1.5, 90, 180).V(10).H(7)
    o = [(page, False, True), (line((10, 8), (17, 8)), False, True), (rrect(10, 11, 3.25, 5, .5), True, True)]
    for y in (11.25, 13.5, 15.75): o.append((line((15.75, y), (17, y)), False, True))
    return o


def ic_fundamental():  # 基本：L 形座標軸＋三根往上的長條（營收／獲利 —— 跟技術面的 K 棒區隔：沒有影線、坐在軸上）
    o = [(line((4, 3.5), (4, 20), (20.5, 20)), False, True)]
    for x, top in ((8.25, 13.5), (12.5, 10), (16.75, 6.5)):
        o.append((rrect(x - .625, top, 1.25, 16.75 - top, .5), True, True))
    return o


# key, 中文名, 一句話, 圖示, 所在面, 面板範圍 (s0,s1,t0,t1), 明度序號
FACETS = [
    ('capital',     '資金', '錢往哪裡跑',     ic_capital,     'top',   (0, 1, 0, .5), 0),
    ('industry',    '產業', '上下游誰最強',   ic_industry,    'top',   (0, 1, .5, 1), 1),
    ('technical',   '技術', '什麼時候進場',   ic_technical,   'left',  (0, 1, 0, .5), 2),
    ('chips',       '籌碼', '誰在買誰在賣',   ic_chips,       'left',  (0, 1, .5, 1), 3),
    ('fundamental', '基本', '現在貴不貴',     ic_fundamental, 'right', (0, 1, 0, .5), 4),
    ('news',        '消息', '有沒有理由不進場', ic_news,       'right', (0, 1, .5, 1), 5),
]
GROUP = {'top': '頂面・看大局', 'left': '左面・看交易', 'right': '右面・看公司'}


def icon_body(key, color='currentColor', T=lambda p: p, sw=SW, nd=2):
    fn = {f[0]: f[3] for f in FACETS}[key]
    o = []
    for p, fill, stroke in fn():
        a = f'd="{p.d(T, nd)}" fill="{color if fill else "none"}"'
        if stroke: a += f' stroke="{color}" stroke-width="{sw:.3f}" stroke-linecap="round" stroke-linejoin="round"'
        o.append(f'<path {a}/>')
    return ''.join(o)


# =====================================================================================
# 等角立方
#   每一面寫成 O + s·P + t·Q（s,t∈[0,1]）；P、Q 是畫面上的兩條邊向量（長度都＝a，夾角 60° 或 120°）。
#   頂面：O＝左頂點，P＝右上 -30°（→頂點 T），Q＝右下 30°（→中心）
#   左面：O＝左上頂點，P＝右下 30°（→中心），Q＝正下方
#   右面：O＝中心，P＝右上 -30°（→右上頂點），Q＝正下方
#   圖示的 x 軸對到 P、y 軸對到 Q，所以圖示裡的水平／垂直線一定平行於面的邊。
# =====================================================================================
class Cube:
    def __init__(self, cx, cy, a):
        self.cx, self.cy, self.a = cx, cy, a
        ex, ey = (C30*a, S30*a), (-C30*a, S30*a)
        self.T = (cx, cy - a); self.C = (cx, cy)
        self.UL = (cx - C30*a, cy - a/2); self.UR = (cx + C30*a, cy - a/2)
        self.LL = (cx - C30*a, cy + a/2); self.LR = (cx + C30*a, cy + a/2); self.B = (cx, cy + a)
        # 頂面改成 O＝左頂點、P＝右上（→頂點 T）、Q＝右下（→中心）：圖示的「往右」＝往右上，資金分流看起來是往右上走（往上流），不是往前倒
        self.face = {'top': (self.UL, (C30*a, -S30*a), ex), 'left': (self.UL, ex, (0, a)), 'right': (self.C, (C30*a, -S30*a), (0, a))}

    def at(self, face, s, t):
        O, P, Q = self.face[face]; return (O[0] + s*P[0] + t*Q[0], O[1] + s*P[1] + t*Q[1])

    def panel(self, face, box, inset):
        """面板四角；inset 是畫面上的垂直內縮距離（px）。等角的每一面都是 60° 菱形，所以面座標內縮 δ ⇒ 畫面垂直距離 δ·a·sin60"""
        s0, s1, t0, t1 = box; d = inset/(self.a*S60)
        s0, s1, t0, t1 = s0 + d, s1 - d, t0 + d, t1 - d
        return [self.at(face, s0, t0), self.at(face, s1, t0), self.at(face, s1, t1), self.at(face, s0, t1)]

    def icon_T(self, face, box, size):
        """回傳把 24 格線圖示投影到面板中央的函式（size＝圖示 24 格在面上的邊長，以 a 為單位）"""
        s0, s1, t0, t1 = box; sc, tc = (s0 + s1)/2, (t0 + t1)/2; k = size/24
        return lambda p: self.at(face, sc + (p[0] - 12)*k, tc + (p[1] - 12)*k)


def poly(pts, fill, extra=''):
    return f'<polygon points="{" ".join(f"{x:.2f},{y:.2f}" for x, y in pts)}" fill="{fill}"{extra}/>'


def rpanel(cube, face, box, gap, r, fill):
    """圓角面板：多縮 r，再用同色、線寬 2r、圓角接頭的描邊撐回來 ⇒ 四個角是半徑 r 的正圓角（畫面座標）"""
    pts = cube.panel(face, box, gap/2 + r)
    return poly(pts, fill, f' stroke="{fill}" stroke-width="{2*r:.2f}" stroke-linejoin="round"' if r > 0 else '')


# 比例（全部以邊長 a 為單位，任何尺寸都同一套）
GAP, RAD, ICON = .03, .012, .40
STROKE = 1.75*ICON/24   # 面板縫、面板圓角、圖示框、線寬（＝圖示 1.75／24 格 × 圖示框）


def cube_A(cube, P, tones=None, bg='#ffffff'):
    tones = tones or P['tones']; a = cube.a; o = []
    for key, _, _, _, face, box, ti in FACETS:
        fill = tones[ti]
        o.append(rpanel(cube, face, box, GAP*a, RAD*a, fill))
        fg = P['ink'] if contrast(P['ink'], fill) >= contrast(P['light'], fill) else P['light']
        o.append(icon_body(key, fg, cube.icon_T(face, box, ICON), STROKE*a))
    return ''.join(o)


def cube_C(cube, P, tones=None):
    tones = tones or P['tones']; a = cube.a
    return ''.join(rpanel(cube, face, box, GAP*a, RAD*a, tones[ti]) for key, _, _, _, face, box, ti in FACETS)


def cube_B(cube, P, top_tint=True):
    a = cube.a; w = STROKE*a; ink = P['ink']; c = cube
    o = []
    if top_tint: o.append(poly([c.T, c.UR, c.C, c.UL], P['tones'][0]))   # 只有頂面留極淡的底色（＝L0），其他不填
    st = f' fill="none" stroke="{ink}" stroke-width="{w:.2f}" stroke-linecap="round" stroke-linejoin="round"'
    hexa = [c.T, c.UR, c.LR, c.B, c.LL, c.UL]
    o.append(f'<polygon points="{" ".join(f"{x:.2f},{y:.2f}" for x, y in hexa)}"{st}/>')
    inner = Path().M(*c.UL).L(*c.C).L(*c.UR).M(*c.C).L(*c.B)
    # 面板分隔線：頂面 s=0.5、左右兩面 t=0.5 —— 跟稜線同粗，兩端各留一個線寬的空隙，看得出是「面上的分隔」不是稜
    e = w*1.6/(a*S60)
    seams = Path().M(*c.at('top', e, .5)).L(*c.at('top', 1 - e, .5))
    seams.M(*c.at('left', e, .5)).L(*c.at('left', 1 - e, .5)).M(*c.at('right', e, .5)).L(*c.at('right', 1 - e, .5))
    o.append(f'<path d="{inner.d()}{seams.d()}"{st}/>')
    for key, _, _, _, face, box, ti in FACETS:
        o.append(icon_body(key, ink, cube.icon_T(face, box, ICON), w))
    return ''.join(o)


def svg(w, h, body, bg='#ffffff', title=''):
    t = f'<title>{title}</title>' if title else ''
    b = f'<rect width="{w}" height="{h}" fill="{bg}"/>' if bg else ''
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">{t}{b}{body}</svg>\n'


def save(name, text):
    with open(os.path.join(HERE, name), 'w') as f: f.write(text)


# =====================================================================================
# 字標：字形轉向量路徑（fontTools；精確的二次曲線，不是折線）
# =====================================================================================
ZH = TTCollection('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc').fonts[0]
EN = TTFont('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')


def glyph_run(text, font, size, x, y, tracking=0.0, space=None):
    """回傳 (路徑 d, 字墨外框 (xmin,ymin,xmax,ymax), 前進寬)；y＝基線"""
    gs, cmap, hm = font.getGlyphSet(), font.getBestCmap(), font['hmtx']
    s = size/font['head'].unitsPerEm
    pen = SVGPathPen(gs, ntos=lambda v: f'{v:.2f}'); bp = BoundsPen(gs)
    cx = x
    for i, ch in enumerate(text):
        g = cmap[ord(ch)]
        tr = (s, 0, 0, -s, cx, y)
        gs[g].draw(TransformPen(pen, tr)); gs[g].draw(TransformPen(bp, tr))
        adv = hm[g][0]*s if (ch != ' ' or space is None) else space*size
        cx += adv + (tracking if i < len(text) - 1 else 0)
    return pen.getCommands(), bp.bounds, cx - x


def fit_text(text, font, size, tracking=0.0, space=None):
    _, b, adv = glyph_run(text, font, size, 0, 0, tracking, space); return b, adv


def wordmark(P, x, y, zh_size, align='start'):
    """股立方（字墨高度≈zh_size×0.9）＋ STOCK CUBE（寬字距，總寬＝中文字墨寬）。回傳 (svg 片段, 外框)
    x,y＝中文字墨的左上角（align='middle' 時 x 是中線）。中文用同色細描邊把字重加到穩重（不是描邊特效：線色＝字色）。"""
    tr_zh = zh_size*.12
    b, _ = fit_text('股立方', ZH, zh_size, tr_zh)
    zw, zh = b[2] - b[0], b[3] - b[1]
    x0 = x - zw/2 if align == 'middle' else x
    d_zh, bz, _ = glyph_run('股立方', ZH, zh_size, x0 - b[0], y - b[1], tr_zh)
    en_size = zh_size*.2
    # 字間撐到跟中文同寬；空白字本身寬度設 0，字詞間距＝兩個字距（不然 STOCK 跟 CUBE 中間會空出三個字距、像斷掉）
    eb, _ = fit_text('STOCK CUBE', EN, en_size, 0, 0)
    n = len('STOCK CUBE') - 1
    track = (zw - (eb[2] - eb[0]))/n
    eb2, _ = fit_text('STOCK CUBE', EN, en_size, track, 0)
    ey = y + zh + zh_size*.24
    d_en, be, _ = glyph_run('STOCK CUBE', EN, en_size, x0 - eb2[0], ey - eb2[1], track, 0)
    bold = zh_size*.028
    s = (f'<path d="{d_zh}" fill="{P["ink"]}" stroke="{P["ink"]}" stroke-width="{bold:.2f}" stroke-linejoin="round"/>'
         f'<path d="{d_en}" fill="{P["mute"]}"/>')
    return s, (min(bz[0], be[0]) - bold/2, bz[1] - bold/2, max(bz[2], be[2]) + bold/2, be[3])


# =====================================================================================
# 產出
# =====================================================================================
REC = 'C'          # 推薦案
MARK = 1024
A_MARK = 330       # 標誌畫布 1024 時的立方邊長（立方高 2a＝660，寬 1.732a＝572）


def mark_svg(case, pal, bg='#ffffff'):
    P = PALETTES[pal]; cube = Cube(MARK/2, MARK/2, A_MARK)
    body = {'A': lambda: cube_A(cube, P), 'B': lambda: cube_B(cube, P), 'C': lambda: cube_C(cube, P)}[case]()
    return svg(MARK, MARK, body, bg, f'股立方 標誌 {case}・{P["name"]}')


def app_icon(pal, dark=False):
    """App 圖示（1024 圓角方形，圓角 22.5%）。淺底＝白；深底＝主色最深色＋深底專用明度階（最暗面板對底 ≥1.6:1）"""
    P = PALETTES[pal]; S = 1024
    bg = P['ink'] if dark else '#ffffff'
    tones = P['dark_tones'] if dark else P['tones']
    cube = Cube(S/2, S/2, 320)   # 立方高 640／1024＝62.5%：32px 時立方還有 20px 高
    a = cube.a
    body = (f'<rect width="{S}" height="{S}" rx="{S*.225:.0f}" fill="{bg}"/>'
            + ''.join(rpanel(cube, face, box, GAP*a, RAD*a, tones[ti]) for _, _, _, _, face, box, ti in FACETS))
    return svg(S, S, body, None, f'股立方 App 圖示（{"深底" if dark else "淺底"}）')


def app_icon_16(pal, dark=False):
    """16px 簡化版：不切面板、只剩三個面三個明度；直接在 16 格上畫，左右兩條直稜與中線都落在整數像素上（x＝3、8、13）"""
    P = PALETTES[pal]
    bg = P['ink'] if dark else '#ffffff'
    t = P['dark_tones'] if dark else P['tones']
    top, left, right = (t[0], t[2], t[4]) if dark else (t[1], t[3], t[5])
    a = 5/C30; c = Cube(8, 8, a)
    body = (f'<rect width="16" height="16" rx="3.6" fill="{bg}"/>'
            + poly([c.T, c.UR, c.C, c.UL], top) + poly([c.UL, c.C, c.B, c.LL], left) + poly([c.C, c.UR, c.LR, c.B], right))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16" shape-rendering="crispEdges">'
            f'<title>股立方 App 圖示 16px 簡化版</title>{body}</svg>\n')


def lockups(pal='ink'):
    P = PALETTES[pal]
    # 橫式：標誌左、字標右，字標的整塊（中文＋英文）與立方垂直置中
    H = 420; a = H/2; pad = 90
    cube = Cube(pad + C30*a, pad + a, a)
    zh_size = 170
    wm, bb = wordmark(P, 0, 0, zh_size)
    block_h = bb[3] - bb[1]
    tx = pad + 2*C30*a + 96
    ty = pad + a - block_h/2
    wm, bb = wordmark(P, tx, ty, zh_size)
    Wd = math.ceil(bb[2] + pad); Hd = math.ceil(H + 2*pad)
    save('lockup_h.svg', svg(Wd, Hd, cube_C(cube, P) + wm, '#ffffff', '股立方 標準字組合（橫式）'))
    # 直式：立方在上、字標置中在下
    a2 = 230; W2 = 900
    cube2 = Cube(W2/2, 110 + a2, a2)
    wm2, bb2 = wordmark(P, W2/2, 110 + 2*a2 + 64, 150, 'middle')
    H2 = math.ceil(bb2[3] + 110)
    save('lockup_v.svg', svg(W2, H2, cube_C(cube2, P) + wm2, '#ffffff', '股立方 標準字組合（直式）'))
    return (Wd, Hd), (W2, H2)


def facet_files():
    sym = []
    for key, zh, q, _, _, _, _ in FACETS:
        body = icon_body(key)
        save(f'facet_{zh}.svg', f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24"><title>{zh}：{q}</title>{body}</svg>\n')
        sym.append(f'<symbol id="facet-{key}" viewBox="0 0 24 24"><title>{zh}：{q}</title>{body}</symbol>')
    save('facets.svg', '<svg xmlns="http://www.w3.org/2000/svg" style="display:none">\n<!-- 用法：<svg width="24" height="24" style="color:#1f2d3d"><use href="facets.svg#facet-capital"/></svg>；線色跟著 currentColor -->\n'
         + '\n'.join(sym) + '\n</svg>\n')


# ---------- 說明頁與總覽（HTML → Playwright 截圖） ----------
CSS = """
*{box-sizing:border-box} body{margin:0;background:#fff;color:#1f2d3d;font-family:"WenQuanYi Zen Hei",sans-serif}
.en{font-family:"DejaVu Sans",sans-serif;letter-spacing:.32em;font-size:12px;color:#6b7a8a}
h1{font-size:30px;font-weight:600;margin:0;letter-spacing:.06em} h2{font-size:18px;font-weight:600;margin:0 0 4px;letter-spacing:.04em}
.lead{font-size:14px;line-height:1.75;color:#4a5868;margin:10px 0 0;max-width:1180px}
.sec{border-top:1px solid #e6eaee;padding:36px 0 40px} .sec:first-of-type{border-top:0}
.cap{font-size:13px;color:#6b7a8a;line-height:1.7}
.mono{font-family:"DejaVu Sans Mono",monospace;font-size:12px;color:#4a5868}
"""


def facet_sheet():
    """六面向圖示說明：圖示（48）＋名稱＋一句話；下面一列看 32／24 實際像素"""
    cells = ''
    for key, zh, q, _, face, _, ti in FACETS:
        ic = open(os.path.join(HERE, f'facet_{zh}.svg')).read()
        cells += (f'<div class="f"><div class="ic">{ic}</div><div class="nm">{zh}</div><div class="q">{q}</div>'
                  f'<div class="g">{GROUP[face]}</div>'
                  f'<div class="sm">' + ''.join(f'<span style="width:{s}px;height:{s}px">{ic}</span>' for s in (32, 24)) + '</div></div>')
    html = f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}
body{{padding:48px 56px;width:1200px}}
.row{{display:grid;grid-template-columns:repeat(6,1fr);gap:0;margin-top:28px}}
.f{{display:flex;flex-direction:column;align-items:center;gap:6px;padding:8px 0;border-left:1px solid #eef1f4}} .f:first-child{{border-left:0}}
.ic{{width:56px;height:56px;color:#1f2d3d}} .ic svg,.sm svg{{width:100%;height:100%}}
.nm{{font-size:22px;font-weight:600;margin-top:10px;letter-spacing:.1em}} .q{{font-size:14px;color:#4a5868}} .g{{font-size:12px;color:#8a97a5}}
.sm{{display:flex;gap:16px;align-items:center;margin-top:12px;color:#1f2d3d}} .sm span{{display:inline-flex}}
</style></head><body><h1>股立方｜六個面向</h1><div class="en" style="margin-top:8px">SIX FACETS · 24 GRID · STROKE 1.75</div>
<div class="row">{cells}</div>
<p class="cap" style="margin-top:28px">24×24 格線、線寬 1.75、圓頭圓角；只有「線」與「實心」兩種元素。下排為 32px 與 24px 實際像素。線色跟著 currentColor，放進網站自動跟深淺主題變色。</p>
</body></html>"""
    return html


def overview(sizes_h, sizes_v):
    P = PALETTES['ink']
    def img(n, w, extra=''): return f'<img src="file://{HERE}/{n}" style="width:{w}px;height:auto;display:block{extra}">'
    # 第一排：三案
    notes = {'A': ('六格立方', '平塗色塊，六塊面板各放一個圖示 —— 六個面向直接寫在立方上'),
             'B': ('單線立方', '純線稿，一種墨色、同一粗細 —— 最像手繪、最不像算圖'),
             'C': ('刻面立方', '只有六塊明度，不放圖示 —— 純幾何，小尺寸最穩')}
    legend = ''.join(f'<div class="lg"><i style="background:{P["tones"][ti]}"></i><span class="li">{icon_body(key, P["ink"])}</span>{zh}</div>'
                     for key, zh, _, _, _, _, ti in FACETS)
    legend = legend.replace('<path', '<path').replace('<span class="li">', '<span class="li"><svg viewBox="0 0 24 24">').replace('</span>', '</svg></span>')
    r1 = ''.join(f'<div class="card">{img(f"mark_{c}_ink.svg", 300)}<h2>{c}　{notes[c][0]}{"　<b class=rec>推薦</b>" if c == REC else ""}</h2>'
                 f'<div class="cap">{notes[c][1]}</div>{"<div class=legend>" + legend + "</div>" if c == "C" else ""}</div>' for c in 'ABC')
    # 第二排：推薦案 × 三色系
    r2 = ''
    for k, p in PALETTES.items():
        sw = ''.join(f'<div class="sw"><i style="background:{t}"></i><span class="mono">{t}</span></div>' for t in p['tones'])
        sw += f'<div class="sw"><i style="background:{p["ink"]}"></i><span class="mono">{p["ink"]} 字</span></div>'
        r2 += f'<div class="card">{img(f"mark_{REC}_{k}.svg", 260)}<h2>{p["name"]}{"　<b class=rec>主推</b>" if k == "ink" else ""}</h2><div class="sws">{sw}</div></div>'
    # 第三排：六面向
    r3 = ''.join(f'<div class="fc"><span class="fi">{open(os.path.join(HERE, f"facet_{zh}.svg")).read()}</span><div class="nm">{zh}</div><div class="cap">{q}</div></div>'
                 for key, zh, q, _, _, _, _ in FACETS)
    # 第四排：App 圖示各尺寸＋標準字
    def sizes(dark):
        n = 'app_icon_dark.svg' if dark else 'app_icon_light.svg'
        n16 = 'app_icon_16_dark.svg' if dark else 'app_icon_16_light.svg'
        o = ''.join(f'<div class="sz">{img(n, s)}<span class="mono">{s}</span></div>' for s in (180, 48, 32, 16))
        o += f'<div class="sz">{img(n16, 16)}<span class="mono">16 簡化</span></div>'
        return o
    r4 = (f'<div class="apps"><div class="appcol"><div class="big">{img("app_icon_light.svg", 200)}<span class="mono">1024（縮圖）</span></div><div class="szs">{sizes(False)}</div></div>'
          f'<div class="appcol"><div class="big">{img("app_icon_dark.svg", 200)}<span class="mono">1024（縮圖）</span></div><div class="szs">{sizes(True)}</div></div></div>'
          f'<div class="locks"><div>{img("lockup_h.svg", 560)}</div><div>{img("lockup_v.svg", 230)}</div></div>')
    html = f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}
body{{width:1600px;padding:64px 80px}}
.grid3{{display:grid;grid-template-columns:repeat(3,1fr);gap:40px;margin-top:20px}}
.card{{display:flex;flex-direction:column;align-items:flex-start;gap:8px}}
.rec{{font-size:12px;font-weight:400;color:#fff;background:#1f2d3d;padding:2px 8px;border-radius:4px;letter-spacing:.1em;vertical-align:3px}}
.legend{{display:grid;grid-template-columns:repeat(3,auto);gap:8px 18px;margin-top:6px}}
.lg{{display:flex;align-items:center;gap:6px;font-size:13px}} .lg i{{width:14px;height:14px;border-radius:3px;display:inline-block}}
.li{{width:20px;height:20px;display:inline-flex}} .li svg{{width:100%;height:100%}}
.sws{{display:grid;grid-template-columns:repeat(2,auto);gap:6px 20px}} .sw{{display:flex;align-items:center;gap:8px}} .sw i{{width:18px;height:18px;border-radius:4px;display:inline-block;box-shadow:inset 0 0 0 1px rgba(0,0,0,.06)}}
.facets{{display:grid;grid-template-columns:repeat(6,1fr);margin-top:24px}}
.fc{{display:flex;flex-direction:column;align-items:center;gap:6px;border-left:1px solid #eef1f4}} .fc:first-child{{border-left:0}}
.fi{{width:48px;height:48px;color:#1f2d3d}} .fi svg{{width:100%;height:100%}} .nm{{font-size:18px;font-weight:600;letter-spacing:.1em;margin-top:6px}}
.row4{{display:flex;gap:56px;margin-top:24px;align-items:flex-start}}
.apps{{display:flex;flex-direction:column;gap:20px}} .appcol{{display:flex;gap:28px;align-items:flex-end;background:#f3f5f7;border-radius:16px;padding:20px 24px}}
.big,.sz{{display:flex;flex-direction:column;align-items:center;gap:6px}} .szs{{display:flex;gap:22px;align-items:flex-end}}
.locks{{display:flex;flex-direction:column;gap:20px;align-items:flex-start}} .locks div{{border:1px solid #eef1f4;border-radius:12px}}
</style></head><body>
<h1>股立方｜簡約 2.5D</h1><div class="en" style="margin-top:8px">STOCK CUBE · ISOMETRIC · FLAT · ONE HUE</div>
<p class="lead">等角投影的平塗立方。看得到的三個面各切兩塊面板，一共六塊，對應六個面向：頂面看大局（資金｜產業）、左面看交易（技術／籌碼）、右面看公司（基本／消息）。只用一個色相的六個明度，不用漸層、發光、透明與投影。</p>
<div class="sec"><h2>一　三個方向（墨藍示範）</h2><div class="grid3">{r1}</div></div>
<div class="sec"><h2>二　推薦案 {REC} × 三種色系</h2><div class="grid3">{r2}</div></div>
<div class="sec"><h2>三　六個面向圖示</h2><div class="facets">{r3}</div></div>
<div class="sec"><h2>四　App 圖示與標準字</h2><div class="row4">{r4}</div></div>
</body></html>"""
    return html


def render(jobs):
    """jobs：[(html 或 svg 檔路徑, 輸出 png, 寬, 高, 是否整頁)]"""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        for src, out, w, h, full in jobs:
            pg = b.new_page(viewport={'width': w, 'height': h})
            pg.goto('file://' + src); pg.wait_for_timeout(250)
            pg.screenshot(path=out, full_page=full); pg.close()
        b.close()


def main():
    jobs = []
    def mk(name, text, w=MARK, h=MARK):
        save(name + '.svg', text); jobs.append((os.path.join(HERE, name + '.svg'), os.path.join(HERE, name + '.png'), w, h, False))
    for c in 'ABC': mk(f'mark_{c}_ink', mark_svg(c, 'ink'))
    for k in ('graphite', 'teal'): mk(f'mark_{REC}_{k}', mark_svg(REC, k))
    # 另附 A 案三色系（A 是「把六面向寫在立方上」的說明版，介紹頁可能用得到）
    for k in ('graphite', 'teal'): mk(f'mark_A_{k}', mark_svg('A', k))
    facet_files()
    mk('app_icon_light', app_icon('ink'))
    mk('app_icon_dark', app_icon('ink', True))
    save('app_icon_16_light.svg', app_icon_16('ink')); save('app_icon_16_dark.svg', app_icon_16('ink', True))
    (wh, hh), (wv, hv) = lockups('ink')
    jobs.append((os.path.join(HERE, 'lockup_h.svg'), os.path.join(HERE, 'lockup_h.png'), wh, hh, False))
    jobs.append((os.path.join(HERE, 'lockup_v.svg'), os.path.join(HERE, 'lockup_v.png'), wv, hv, False))
    fs = os.path.join(SCRATCH, 'v23_facets.html'); open(fs, 'w').write(facet_sheet())
    jobs.append((fs, os.path.join(HERE, '六面向圖示.png'), 1312, 400, True))
    ov = os.path.join(SCRATCH, 'v23_overview.html'); open(ov, 'w').write(overview((wh, hh), (wv, hv)))
    jobs.append((ov, os.path.join(HERE, '股立方_簡約2.5D.png'), 1600, 1000, True))
    # App 圖示各尺寸（給驗收看實際像素）
    for n in ('app_icon_light', 'app_icon_dark'):
        for s in (180, 48, 32, 16):
            h = os.path.join(SCRATCH, f'{n}_{s}.html')
            open(h, 'w').write(f'<html><body style="margin:0"><img src="file://{HERE}/{n}.svg" width="{s}" height="{s}" style="display:block"></body></html>')
            jobs.append((h, os.path.join(SCRATCH, f'{n}_{s}.png'), s, s, False))
    render(jobs)
    # 色票表（給回報與驗收）
    rep = {k: dict(name=p['name'], ink=p['ink'], light=p['light'], tones=p['tones'], dark_tones=p['dark_tones']) for k, p in PALETTES.items()}
    open(os.path.join(SCRATCH, 'v23_palettes.json'), 'w').write(json.dumps(rep, ensure_ascii=False, indent=1))
    print('ok', len(jobs), 'png')


if __name__ == '__main__':
    main()
