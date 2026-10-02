# 第十四輪〈股立方〉：照 Andy 給的圖二風格 —— 白底、冰藍透明玻璃立方、深藍線條圖示、深藍刻度環、粗角框、木柄放大鏡
# 立方用「等角正交投影」（不是透視）：每一面都是平行四邊形，24×24 的線條圖示可以用一個 SVG matrix() 精準貼上去。
# 面上的圖示直接 import 第十三輪的線條圖示函式（同一套造型，改一邊兩邊一起變）。
# 執行：python docs/brand/v14/_gen.py   → 產出本資料夾的 SVG、badge/、_sheet.html、股立方_圖二風格.png
import math, os, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location('v13', os.path.join(HERE, '..', 'v13', '_gen.py'))
v13 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(v13)   # v13 的產生段落包在 main()，import 不會重寫它的檔案

# ---------- 色票（量自圖二：白底 #fefefe、字 #0d2644、面上線條 #092f52、立方輪廓 #24557b、刻度 #2c4b6c、
#            細線 #4a637f、玻璃 #d8f0fa／#dceff8／#c9edff、金屬環 #1474d3、木頭亮面 #f3bb7e、木頭暗邊 #bb8258）----------
LIGHT = dict(
    name='light', bg0='#ffffff', bg1='#eef5fb', tile_stroke='#d5e3ef',
    ink='#0f2a4a', sub='#4a637f', rule='#8aa0b6',
    glyph='#12345a', acc='#1474d3', rise='#d93a4f', fall='#14936a',
    outline='#24557b', tick='#2c4b6c', bracket='#1d3557',
    top='#e8f7fd', left='#d7eefa', right='#c6e8fa', base='#dff2fb', face_op=.55, base_op=.92,
    hi='#ffffff', hidden_op=.75, back_op=.28)
DARK = dict(
    name='dark', bg0='#1c3358', bg1='#0b1629', tile_stroke='#2c4670',
    ink='#eef6ff', sub='#9fb6cf', rule='#5d7898',
    glyph='#e6f4ff', acc='#5cc0ff', rise='#ff5f73', fall='#2fcf92',
    outline='#6cc0f2', tick='#8fb3d9', bracket='#d6ecff',
    top='#a9e2fb', left='#7cc6ef', right='#5aaee0', base='#6fbde8', face_op=.2, base_op=.16,
    hi='#e4f6ff', hidden_op=.45, back_op=.3)

# 面上的圖示：前三面（上＝資金分流、左＝技術 K 棒、右＝產業晶片），後三面隔著玻璃（籌碼、事件、基本）
FRONT = {'top': v13.flow, 'left': v13.candle, 'right': v13.chain}
BACK = {'bl': v13.chips, 'br': v13.fund, 'bottom': v13.event}

S3 = math.cos(math.radians(30))


class Cube:
    """等角正交投影的立方：中心 C、頂點距 s。六角輪廓頂點 T, UR, LR, B, LL, UL（尖頂朝上）。"""
    def __init__(self, cx, cy, s):
        self.C = (cx, cy); self.s = s
        o = lambda dx, dy: (cx + dx*s, cy + dy*s)
        self.T, self.UR, self.LR = o(0, -1), o(S3, -.5), o(S3, .5)
        self.B, self.LL, self.UL = o(0, 1), o(-S3, .5), o(-S3, -.5)
        self.hex = [self.T, self.UR, self.LR, self.B, self.LL, self.UL]
        C = self.C
        # 每一面：(原點, 圖示 x 軸終點, 圖示 y 軸終點) —— 行列式都 > 0，所以圖示不會被鏡像
        self.face = {
            'top':    (self.UL, self.T, C),        # 上面：x 往右上、y 往右下
            'left':   (self.UL, C, self.LL),       # 左面：x 往右下、y 垂直往下
            'right':  (C, self.UR, self.B),        # 右面：x 往右上、y 垂直往下
            'bl':     (self.UL, self.T, self.LL),  # 後左面（隔著玻璃）：x 往右上、y 垂直
            'br':     (self.T, self.UR, C),        # 後右面：x 往右下、y 垂直
            'bottom': (self.LL, C, self.B),        # 底面：同上面的方向
        }

    def quad(self, k):
        O, X, Y = self.face[k]
        D = (X[0] + Y[0] - O[0], X[1] + Y[1] - O[1])
        return [O, X, D, Y]

    def matrix(self, k, pad=.17):
        """把 24×24 圖示貼進面 k（四周留 pad 比例的邊）"""
        O, X, Y = self.face[k]
        xv = (X[0] - O[0], X[1] - O[1]); yv = (Y[0] - O[0], Y[1] - O[1])
        f = (1 - 2*pad) / 24
        e = O[0] + pad*(xv[0] + yv[0]); g = O[1] + pad*(xv[1] + yv[1])
        return f'matrix({xv[0]*f:.4f} {xv[1]*f:.4f} {yv[0]*f:.4f} {yv[1]*f:.4f} {e:.2f} {g:.2f})'


def pts(ps): return ' '.join(f'{x:.1f},{y:.1f}' for x, y in ps)
def shrink(ps, c, k): return [(c[0] + (x - c[0])*k, c[1] + (y - c[1])*k) for x, y in ps]


def glyph(fn, P, sw=1.7):
    pal = dict(acc=P['acc'], fill='none', rise=P['rise'], fall=P['fall'], ink=P['glyph'])
    return (f'<g fill="none" stroke="{P["glyph"]}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round">'
            + ''.join(fn(pal)) + '</g>')


def defs(u, P):
    d = [f'<linearGradient id="{u}tile" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{P["bg0"]}"/><stop offset="1" stop-color="{P["bg1"]}"/></linearGradient>',
         f'<linearGradient id="{u}glass" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{P["top"]}"/><stop offset=".55" stop-color="{P["base"]}"/><stop offset="1" stop-color="{P["right"]}"/></linearGradient>',
         # 木柄：截面方向的漸層（暗邊 → 亮面 → 高光 → 暗邊），量自圖二握把的橫切面
         f'<linearGradient id="{u}wood" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#b47a4c"/><stop offset=".22" stop-color="#e2a96c"/>'
         f'<stop offset=".45" stop-color="#f6c48a"/><stop offset=".62" stop-color="#facd91"/><stop offset=".85" stop-color="#d39a5e"/><stop offset="1" stop-color="#9c6a40"/></linearGradient>',
         f'<radialGradient id="{u}cap" cx="40%" cy="38%" r="70%"><stop offset="0" stop-color="#f7c88f"/><stop offset=".7" stop-color="#e0a468"/><stop offset="1" stop-color="#c08452"/></radialGradient>',
         f'<linearGradient id="{u}metal" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0d4f99"/><stop offset=".3" stop-color="#3d9bf0"/>'
         f'<stop offset=".5" stop-color="#bfe3ff"/><stop offset=".7" stop-color="#1474d3"/><stop offset="1" stop-color="#0a3d78"/></linearGradient>',
         f'<filter id="{u}soft" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="9"/></filter>',
         f'<filter id="{u}blur1" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="1.2"/></filter>']
    return '<defs>' + ''.join(d) + '</defs>'


def ring(P, cx, cy, r, skip=(25, 62)):
    """外圈刻度：60 格，每 5 格一根粗長刻度；握把經過的那一段留白（跟圖二一樣讓握把蓋在刻度上會太亂）"""
    thin, thick = [], []
    for i in range(60):
        a = 6*i
        if skip[0] <= a <= skip[1]: continue
        t = math.radians(a)
        L = 24 if i % 5 == 0 else 12
        d = f'M{cx + r*math.cos(t):.1f} {cy + r*math.sin(t):.1f}L{cx + (r - L)*math.cos(t):.1f} {cy + (r - L)*math.sin(t):.1f}'
        (thick if i % 5 == 0 else thin).append(d)
    return (f'<path d="{"".join(thin)}" stroke="{P["tick"]}" stroke-width="3.6" stroke-linecap="round" opacity=".8"/>'
            f'<path d="{"".join(thick)}" stroke="{P["tick"]}" stroke-width="7.5" stroke-linecap="round"/>')


def brackets(P, x0, y0, x1, y1, L, w, corners=('tl', 'tr', 'bl')):
    """四角角框（粗線＋圓角端點）。右下角預設讓給放大鏡握把，跟圖二一樣。"""
    seg = {'tl': f'M{x0} {y0 + L}V{y0}H{x0 + L}', 'tr': f'M{x1 - L} {y0}H{x1}V{y0 + L}',
           'bl': f'M{x0} {y1 - L}V{y1}H{x0 + L}', 'br': f'M{x1} {y1 - L}V{y1}H{x1 - L}'}
    return f'<path d="{"".join(seg[c] for c in corners)}" fill="none" stroke="{P["bracket"]}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'


def glass_cube(cb, P, u, glyphs=True, ow=7.0, yw=7.0, sw=1.7):
    C = cb.C; s = cb.s
    o = []
    # 地上的影子（只有亮版）
    if P['name'] == 'light':
        o.append(f'<ellipse cx="{C[0] + s*.12:.1f}" cy="{C[1] + s*1.08:.1f}" rx="{s*.8:.1f}" ry="{s*.12:.1f}" fill="#1d3557" opacity=".12" filter="url(#{u}soft)"/>')
    # 1) 玻璃本體
    o.append(f'<polygon points="{pts(cb.hex)}" fill="url(#{u}glass)" fill-opacity="{P["base_op"]}"/>')
    # 2) 後三面的圖示（隔著玻璃，淡）＋看不見的三條稜（白色細線）
    if glyphs:
        for k, fn in BACK.items():
            o.append(f'<g opacity="{P["back_op"]}" transform="{cb.matrix(k)}">{glyph(fn, P, sw)}</g>')
    o.append(f'<path d="M{C[0]:.1f} {C[1]:.1f}L{cb.T[0]:.1f} {cb.T[1]:.1f}M{C[0]:.1f} {C[1]:.1f}L{cb.LL[0]:.1f} {cb.LL[1]:.1f}M{C[0]:.1f} {C[1]:.1f}L{cb.LR[0]:.1f} {cb.LR[1]:.1f}" '
             f'stroke="{P["hi"]}" stroke-width="{yw*.45:.1f}" stroke-opacity="{P["hidden_op"]}" stroke-linecap="round"/>')
    # 3) 前三面：各自一層玻璃色＋內側白色細框（玻璃厚度的高光）
    for k in ('top', 'left', 'right'):
        q = cb.quad(k)
        o.append(f'<polygon points="{pts(q)}" fill="{P[k]}" fill-opacity="{P["face_op"]}"/>')
        cen = (sum(x for x, _ in q)/4, sum(y for _, y in q)/4)
        o.append(f'<polygon points="{pts(shrink(q, cen, .88))}" fill="none" stroke="{P["hi"]}" stroke-opacity=".7" stroke-width="{yw*.3:.1f}" stroke-linejoin="round"/>')
    # 左上的玻璃反光帶
    a, b = cb.UL, cb.T
    o.append(f'<polygon points="{pts([(a[0] + s*.12, a[1] + s*.14), (b[0] - s*.1, b[1] + s*.2), (b[0] - s*.26, b[1] + s*.36), (a[0] + s*.12, a[1] + s*.42)])}" fill="{P["hi"]}" opacity=".28"/>')
    if glyphs:
        for k, fn in FRONT.items():
            o.append(f'<g transform="{cb.matrix(k)}">{glyph(fn, P, sw)}</g>')
    # 4) 前面的 Y 稜（白色亮線）＋外輪廓（藍色粗圓角線）＋輪廓內側一圈白
    o.append(f'<path d="M{C[0]:.1f} {C[1]:.1f}L{cb.UL[0]:.1f} {cb.UL[1]:.1f}M{C[0]:.1f} {C[1]:.1f}L{cb.UR[0]:.1f} {cb.UR[1]:.1f}M{C[0]:.1f} {C[1]:.1f}L{cb.B[0]:.1f} {cb.B[1]:.1f}" '
             f'stroke="{P["hi"]}" stroke-width="{yw:.1f}" stroke-opacity=".95" stroke-linecap="round"/>')
    o.append(f'<polygon points="{pts(shrink(cb.hex, C, 1 - (ow*1.25)/s))}" fill="none" stroke="{P["hi"]}" stroke-opacity=".9" stroke-width="{ow*.45:.1f}" stroke-linejoin="round"/>')
    o.append(f'<polygon points="{pts(cb.hex)}" fill="none" stroke="{P["outline"]}" stroke-width="{ow:.1f}" stroke-linejoin="round"/>')
    return ''.join(o)


def magnifier(cb, P, u, k=1.0, ang=42):
    """放大鏡：整顆六角玻璃就是鏡片；金屬環接在右下那條邊靠 LR 頂點的位置，木柄往右下延伸、圓頭"""
    LR, B = cb.LR, cb.B
    px, py = LR[0] + (B[0] - LR[0])*.24, LR[1] + (B[1] - LR[1])*.24   # 邊上的接點
    hw = 21*k                                                         # 握把半徑
    return (f'<g transform="translate({px:.1f} {py:.1f}) rotate({ang})">'
            f'<rect x="{-4*k:.1f}" y="{-hw*.78:.1f}" width="{30*k:.1f}" height="{hw*1.56:.1f}" rx="{5*k:.1f}" fill="url(#{u}metal)"/>'      # 金屬環
            f'<rect x="{-4*k:.1f}" y="{-hw*.78:.1f}" width="{30*k:.1f}" height="{hw*1.56:.1f}" rx="{5*k:.1f}" fill="none" stroke="#0a3566" stroke-width="{2*k:.1f}"/>'
            f'<rect x="{24*k:.1f}" y="{-hw:.1f}" width="{98*k:.1f}" height="{2*hw:.1f}" rx="{4*k:.1f}" fill="url(#{u}wood)"/>'             # 木柄
            f'<path d="M{25*k:.1f} {-hw:.1f}V{hw:.1f}" stroke="#5a3218" stroke-width="{4*k:.1f}"/>'                                             # 環與木頭交界的暗線
            f'<ellipse cx="{122*k:.1f}" cy="0" rx="{hw*.5:.1f}" ry="{hw:.1f}" fill="url(#{u}cap)" stroke="#8a5a34" stroke-width="{2*k:.1f}"/>'  # 圓頭端面
            f'<path d="M{34*k:.1f} {-hw*.42:.1f}H{112*k:.1f}" stroke="#fff3df" stroke-width="{4*k:.1f}" stroke-linecap="round" opacity=".55"/>'  # 木頭高光
            f'</g>')


def icon(P, u, size='L', tile=True):
    """size：L＝完整版（面上圖示、刻度環、角框、放大鏡）；M＝48px（拿掉面上圖示與刻度環）；S＝16px（只留立方輪廓＋Y 線）"""
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">', defs(u, P)]
    if tile:
        o.append(f'<rect x="4" y="4" width="504" height="504" rx="112" fill="url(#{u}tile)" stroke="{P["tile_stroke"]}" stroke-width="4"/>')
    if size == 'S':
        cb = Cube(256, 256, 214)
        o.append(f'<polygon points="{pts(cb.hex)}" fill="url(#{u}glass)" fill-opacity="{1 if P["name"] == "light" else .35}"/>')
        C = cb.C
        o.append(f'<path d="M{C[0]} {C[1]}L{cb.UL[0]:.1f} {cb.UL[1]:.1f}M{C[0]} {C[1]}L{cb.UR[0]:.1f} {cb.UR[1]:.1f}M{C[0]} {C[1]}L{cb.B[0]:.1f} {cb.B[1]:.1f}" '
                 f'stroke="{P["outline"]}" stroke-width="30" stroke-linecap="round"/>')
        o.append(f'<polygon points="{pts(cb.hex)}" fill="none" stroke="{P["outline"]}" stroke-width="40" stroke-linejoin="round"/>')
        o.append('</svg>')
        return '\n'.join(o)
    if size == 'L':
        cx, cy, s = 240, 236, 128
        o.append(ring(P, cx, cy, 190))
        o.append(brackets(P, 64, 60, 416, 412, 58, 20))
        cb = Cube(cx, cy, s)
        o.append(glass_cube(cb, P, u, glyphs=True, ow=7, yw=6, sw=1.7))
        o.append(magnifier(cb, P, u, k=1.0))
    else:   # 48px
        cx, cy, s = 232, 226, 150
        o.append(brackets(P, 52, 48, 412, 408, 66, 34))
        cb = Cube(cx, cy, s)
        o.append(glass_cube(cb, P, u, glyphs=False, ow=16, yw=14))
        o.append(magnifier(cb, P, u, k=1.32))
    o.append('</svg>')
    return '\n'.join(o)


def save(name, s):
    open(os.path.join(HERE, name), 'w').write(s)


# ---------- 直式標準字 ----------
NAME, EN = '股立方', 'STOCK · CUBE'
TAG = '六面透視　資金・籌碼・產業・技術・事件・基本'

def lockup(P, u):
    ic = icon(P, u, 'L', tile=False)
    inner = ic.split('>', 1)[1].rsplit('</svg>', 1)[0]      # 直接內嵌（用 <img> 開的 SVG 不能再引用外部檔）
    W, H = 760, 940
    bg = (f'<rect width="{W}" height="{H}" rx="32" fill="{P["bg0"]}"/>' if P['name'] == 'light' else
          f'<defs><linearGradient id="{u}lbg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{P["bg0"]}"/><stop offset="1" stop-color="{P["bg1"]}"/></linearGradient></defs>'
          f'<rect width="{W}" height="{H}" rx="32" fill="url(#{u}lbg)"/>')
    # letter-spacing 會在最後一個字後面也加一段，所以置中時 x 往右補半個字距
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">{bg}
<svg x="120" y="16" width="520" height="520" viewBox="0 0 512 512">{inner}</svg>
<text x="{W/2 + 12}" y="700" text-anchor="middle" font-family="WenQuanYi Zen Hei" font-size="150" font-weight="700" letter-spacing="24" fill="{P["ink"]}" stroke="{P["ink"]}" stroke-width="3.5" stroke-linejoin="round">{NAME}</text>
<text x="{W/2 + 9}" y="776" text-anchor="middle" font-family="DejaVu Sans" font-size="38" letter-spacing="18" fill="{P["ink"]}">{EN}</text>
<path d="M60 818H{W - 60}" stroke="{P["rule"]}" stroke-width="2"/>
<text x="{W/2 + 2}" y="874" text-anchor="middle" font-family="WenQuanYi Zen Hei" font-size="27" font-weight="600" letter-spacing="4" fill="{P["ink"]}">{TAG}</text></svg>'''


# ---------- 六面＋大盤徽章（第十四輪配色：冰藍玻璃底、深藍線） ----------
BADGES = [('flow', '資金面', '分流圖'), ('chips', '籌碼面', '賭桌籌碼'), ('chain', '產業面', '晶片'),
          ('tech', '技術面', 'K 棒'), ('event', '事件面', '脈衝＋警示'), ('fund', '基本面', '走勢圖'), ('market', '大盤儀表', '外圈刻度')]

def badge(key):
    fn = {k: f for k, _, _, f, _ in v13.ICONS}[key]
    pal = dict(acc='#1474d3', fill='#ffffff', rise='#d93a4f', fall='#14936a', ink='#12345a', area='#12345a')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" width="96" height="96">'
            f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#eef9fe"/><stop offset=".55" stop-color="#d8f0fa"/><stop offset="1" stop-color="#c2e6f9"/></linearGradient></defs>'
            f'<rect x="3" y="3" width="90" height="90" rx="22" fill="url(#g)" stroke="#24557b" stroke-width="3.5"/>'
            f'<rect x="9.5" y="9.5" width="77" height="77" rx="16" fill="none" stroke="#ffffff" stroke-opacity=".9" stroke-width="2"/>'
            f'<g transform="translate(19.2 19.2) scale(2.4)" fill="none" stroke="#12345a" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
            + ''.join(fn(pal)) + '</g></svg>\n')


def sheet():
    sm = lambda v: ''.join(f'<div class="sz"><img src="{f}" width="{s}" height="{s}"><span>{s}px</span></div>'
                           for f, s in ((f'icon48{v}.svg', 48), (f'icon48{v}.svg', 24), (f'icon16{v}.svg', 16)))
    bd = ''.join(f'<div class="b"><img src="badge/{k}.svg" width="104" height="104"><b>{n}</b><i>{d}</i></div>' for k, n, d in BADGES)
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>
body{{margin:0;background:#f3f7fb;color:#0f2a4a;font-family:"WenQuanYi Zen Hei",sans-serif;padding:44px;width:1512px}}
h1{{margin:0;font-size:34px;font-weight:700;letter-spacing:.12em}} .en{{font-family:"DejaVu Sans";letter-spacing:.32em;font-size:14px;color:#24557b;margin:10px 0 14px}}
p{{margin:0 0 24px;font-size:16px;line-height:1.8;color:#3c5672}}
.row{{display:flex;gap:24px;margin-bottom:24px}}
.card{{border-radius:24px;padding:24px;display:flex;gap:26px;align-items:center;flex:1}}
.lt{{background:#ffffff;border:1px solid #d5e3ef}} .dk{{background:#0b1629;border:1px solid #2c4670;color:#d6ecff}}
.big{{width:400px;height:400px}}
.smalls{{display:flex;flex-direction:column;gap:18px}} .sz{{display:flex;align-items:center;gap:12px;font-family:"DejaVu Sans Mono";font-size:13px}}
.lock{{flex:1;border-radius:24px;overflow:hidden;display:flex;justify-content:center;background:#e6eef6;padding:20px}} .lock img{{width:600px}}
h2{{font-size:20px;letter-spacing:.1em;margin:8px 0 14px;color:#24557b}}
.bads{{display:flex;gap:18px;background:#ffffff;border:1px solid #d5e3ef;border-radius:24px;padding:24px 20px;justify-content:space-between}}
.b{{display:flex;flex-direction:column;align-items:center;gap:6px;width:180px}} .b b{{font-size:22px}} .b i{{font-style:normal;font-size:15px;color:#4a637f}}
.b:last-child{{opacity:.9}}
.foot{{margin-top:22px;font-size:15px;color:#3c5672;line-height:1.8}} code{{font-family:"DejaVu Sans Mono";color:#1474d3}}
</style></head><body>
<h1>股立方｜圖二風格</h1><div class="en">STOCK · CUBE // ICE GLASS CUBE × WOOD LENS // ISOMETRIC</div>
<p>照 Andy 給的圖二：冰藍透明玻璃立方（等角正交投影）、深藍線條、深藍刻度環、粗角框（512 畫布上線寬 20）、藍色金屬環＋木柄放大鏡。<br>
前三面：<b>上＝資金（分流圖）</b>、<b>左＝技術（K 棒，紅漲綠跌）</b>、<b>右＝產業（晶片）</b>；後三面隔著玻璃淡淡看得到：籌碼（左上）、基本（右上）、事件（下）。</p>
<div class="row"><div class="card lt"><img class="big" src="icon_light.svg"><div class="smalls">{sm('')}</div></div>
<div class="card dk"><img class="big" src="icon_dark.svg"><div class="smalls">{sm('_dark')}</div></div></div>
<h2>直式標準字</h2>
<div class="row"><div class="lock"><img src="lockup_light.svg"></div><div class="lock" style="background:#050c18"><img src="lockup_dark.svg"></div></div>
<h2>六面＋大盤圖示（第十三輪線條圖示，套第十四輪配色）</h2>
<div class="bads">{bd}</div>
<p class="foot">48／24px 用 <code>icon48*.svg</code>（拿掉面上圖示與刻度環，只留玻璃立方＋放大鏡＋角框）；16px 用 <code>icon16*.svg</code>（只留立方輪廓＋Y 線）。<br>
名稱用「股立方」（圖二的「台股立方」只當風格參考）。字型：中文 WenQuanYi Zen Hei、英文 DejaVu Sans。</p>
</body></html>'''


def render_png():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('沒有 Playwright，略過 PNG'); return
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        pg = b.new_page(viewport={'width': 1600, 'height': 900})
        pg.goto('file://' + os.path.join(HERE, '_sheet.html')); pg.wait_for_timeout(500)
        pg.screenshot(path=os.path.join(HERE, '股立方_圖二風格.png'), full_page=True); b.close()


def main():
    os.makedirs(os.path.join(HERE, 'badge'), exist_ok=True)
    save('icon_light.svg', icon(LIGHT, 'l'))
    save('icon_dark.svg', icon(DARK, 'd'))
    save('icon48.svg', icon(LIGHT, 'lm', 'M')); save('icon48_dark.svg', icon(DARK, 'dm', 'M'))
    save('icon16.svg', icon(LIGHT, 'ls', 'S')); save('icon16_dark.svg', icon(DARK, 'ds', 'S'))
    save('lockup_light.svg', lockup(LIGHT, 'kl'))
    save('lockup_dark.svg', lockup(DARK, 'kd'))
    for k, _, _ in BADGES:
        save(os.path.join('badge', f'{k}.svg'), badge(k))
    save('_sheet.html', sheet())
    render_png()


if __name__ == '__main__':
    main()
