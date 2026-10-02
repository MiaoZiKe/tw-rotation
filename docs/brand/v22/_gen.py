# 第二十二輪〈股立方〉：白底＋六個色系，各做「柔光」「左上打光」兩版，並加強玻璃透視感。
# Andy 第二十二輪：「底色是白色的，給我其他色系」＋「並且具備多點玻璃透視感」
# 造型沿用 v21：只留立方（無把手）、刻度圓環、四個圓角角框、珍珠霧面玻璃、面上細節圖示與貼面規則（v17）、紅漲綠跌。
# 透視感的做法：
#   1. 前三面填色不透明度降到 0.45～0.6（墨黑版 0.72），背面三張圖示與看不見的三條稜明顯透出（背面稜輕微模糊＝隔著玻璃）。
#   2. 外緣是較亮的玻璃厚邊（外側細暗線＋厚緣＋內側亮線），頂點有高光點。
#   3. 每一面一道斜向反光條（裁在面內）；打光版的反光條較亮、方向跟光源一致（左上）。
#   4. 立方後面加一條細的「透視圈」（圓框系統的一部分，半徑介於立方內切與外接之間）：它在六個頂點附近穿到立方後面，
#      隔著玻璃看得到但被淡化，在邊的中點附近露在立方外面 —— 證明立方是透明的（刻度環本身在立方外圈，不會被擋到）。
#   5. 打光版的投影不是全黑：中性灰半透明＋中心一團該色系的淡色（光穿過有色玻璃）。
#   6. 正面圖示加一圈細描邊（淺色面用白、墨黑版用深色），透明之後對比不變差。
# 執行：BRAND_SCRATCH=<暫存資料夾> python docs/brand/v22/_gen.py
import math, os, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
SCRATCH = os.environ.get('BRAND_SCRATCH', '/tmp')
_spec = importlib.util.spec_from_file_location('v21', os.path.join(HERE, '..', 'v21', '_gen.py'))
v21 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(v21)
v19, v17, v18 = v21.v19, v21.v17, v21.v18
Cube, pts, shrink = v17.Cube, v17.pts, v17.shrink
W, CX, CY, R, RIM, RING_R = v21.W, v21.CX, v21.CY, v21.R, v21.RIM, v21.RING_R
BR, BR_L, BR_RAD = v21.BR, v21.BR_L, v21.BR_RAD
SEE_R = 165                # 透視圈半徑：立方外緣在邊中點離中心 ≈ 153、頂點 ≈ 175 → 這條圈在六個頂點附近（±8°）穿到立方的玻璃厚邊後面


def hx(c): return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
def mix(a, b, t):
    A, B = hx(a), hx(b); return '#%02x%02x%02x' % tuple(round(A[i] + (B[i] - A[i])*t) for i in range(3))


def lum(c):
    def ch(v):
        v /= 255; return v/12.92 if v <= .03928 else ((v + .055)/1.055)**2.4
    r, g, b = hx(c); return .2126*ch(r) + .7152*ch(g) + .0722*ch(b)
def contrast(a, b='#ffffff'):
    la, lb = sorted((lum(a), lum(b)), reverse=True); return (la + .05)/(lb + .05)


# ---------- 六個色系 ----------
# face：三面色與玻璃底；sheen：珍珠光澤；rim：玻璃厚緣；edge：外側細暗線（在白底上讓立方浮出來）；hi：內側亮線與 Y 稜；
# acc：刻度與角框（白底上用實色）；acc_core：亮芯；acc_lit：打光版的漸層（亮→主→暗）；metal：柔光版也用金屬漸層；
# tint：打光版投影中心的色調；halo：正面圖示的細描邊；gly：圖示配色
T = {
    'peach': dict(name='珍珠暖桃', top='#fbf6f3', left='#eee6f1', right='#dfe3f2', base0='#fffaf6', base1='#e2e0f1',
                  sheen=('#ffd9e6', '#e6dcff', '#d2e6ff'), rim='#fff6f0', edge='#8e89ad', hi='#ffffff',
                  acc='#c8784a', acc_core='#f6c9a8', acc_lit=('#e09466', '#c8784a', '#a35a33'), metal=False, bw=15,
                  tint='#e7b9a0', halo='#ffffff', face_op=.45, base_op=.26, back_op=1,
                  gly=dict(ink='#1d2f52', acc='#2c5d9e', fill='none', rise='#d33a4a', fall='#1a8a5c', flowline='#2c5d9e',
                           n1='#c0782f', n2='#2a8f88', n3='#6a5acd', trend='#2c5d9e', area='#2c5d9e', hot='#d9864f',
                           chip='#d9a84e', chipacc='#c0392b', core='#2a8f88')),
    'navy': dict(name='海軍藍青銅', top='#fbf6ea', left='#efe3cc', right='#e0cdaa', base0='#fdf9f0', base1='#e3d2b2',
                 sheen=('#fff1d6', '#f5e6c8', '#e9e2d0'), rim='#f6eedd', edge='#1d2f52', hi='#ffffff',
                 acc='#a8743f', acc_core='#ead0a4', acc_lit=('#cfa06a', '#a8743f', '#7a5530'), metal=True, bw=15,
                 tint='#d8bf8e', halo='#ffffff', face_op=.45, base_op=.26, back_op=1,
                 gly=dict(ink='#1d2f52', acc='#2c5d9e', fill='none', rise='#d33a4a', fall='#1a8a5c', flowline='#2c5d9e',
                          n1='#c0782f', n2='#2a8f88', n3='#6a5acd', trend='#2c5d9e', area='#2c5d9e', hot='#c0782f',
                          chip='#d9a84e', chipacc='#c0392b', core='#2a8f88')),
    'neon': dict(name='霓虹紫電藍', top='#c9e4ff', left='#b7a2f5', right='#9785ea', base0='#d6ecff', base1='#9b84ee',
                 sheen=('#ffd6f5', '#d7c9ff', '#bfe3ff'), rim='#e8e0ff', edge='#5b3fc4', hi='#ffffff',
                 acc='#7c4dff', acc_core='#d2c0ff', acc_lit=('#a184ff', '#7c4dff', '#5530cc'), metal=False, bw=15,
                 tint='#a98cff', halo='#ffffff', face_op=.45, base_op=.26, back_op=1,
                 gly=dict(ink='#24124f', acc='#2f7cf6', fill='none', rise='#e5384f', fall='#0f9d68', flowline='#2f7cf6',
                          n1='#e84bb5', n2='#14b8a6', n3='#f59e0b', trend='#2f7cf6', area='#2f7cf6', hot='#e84bb5',
                          chip='#f5b83d', chipacc='#e5384f', core='#22c3d6')),
    'coral': dict(name='珊瑚綠松石', top='#c6f1f5', left='#8fd3dc', right='#68b9c4', base0='#d6f6f9', base1='#5fb0bb',
                  sheen=('#e9fffb', '#c8f3f1', '#bde8ff'), rim='#e6fbfc', edge='#1f7480', hi='#ffffff',
                  acc='#f0604f', acc_core='#ffc4bc', acc_lit=('#ff8577', '#f0604f', '#c9443a'), metal=False, bw=15,
                  tint='#7fd1db', halo='#ffffff', face_op=.45, base_op=.26, back_op=1,
                  gly=dict(ink='#123540', acc='#0f6f8f', fill='none', rise='#e0414f', fall='#12805a', flowline='#0f6f8f',
                           n1='#ff6f61', n2='#ffb347', n3='#7b6cf0', trend='#0f6f8f', area='#0f6f8f', hot='#ff6f61',
                           chip='#ffc857', chipacc='#e0414f', core='#ff8a7a')),
    'ice': dict(name='冰藍', top='#eef9ff', left='#d6effc', right='#bce1f5', base0='#f5fcff', base1='#c3e4f6',
                sheen=('#ffffff', '#e2f6ff', '#cbeaff'), rim='#f2fbff', edge='#1d8fbf', hi='#ffffff',
                acc='#1798cc', acc_core='#bfeafa', acc_lit=('#45b5e2', '#1798cc', '#0d6f99'), metal=False, bw=8,
                tint='#9fdcf3', halo='#ffffff', face_op=.45, base_op=.26, back_op=1,
                gly=dict(ink='#0b4f6c', acc='#0a8fc2', fill='none', rise='#e5384f', fall='#0f9d68', flowline='#0a8fc2',
                         n1='#ff7a59', n2='#00b894', n3='#6c5ce7', trend='#0a8fc2', area='#0a8fc2', hot='#ff7a59',
                         chip='#9adcf0', chipacc='#ff7a59', core='#5fd0f0')),
    'noir': dict(name='墨黑香檳金', top='#44444b', left='#2e2e34', right='#202026', base0='#4a4a52', base1='#18181c',
                 sheen=('#6a5a3e', '#3e3e4a', '#2f3644'), rim='#2b2b31', edge='#b89a5e', hi='#ead8aa',
                 acc='#a5834a', acc_core='#f1dfb3', acc_lit=('#c9a96a', '#a5834a', '#7d5f2e'), metal=True, bw=15,
                 tint='#8f7a52', halo='#141418', face_op=.46, base_op=.34, back_op=1, dark=True,
                 gly=dict(ink='#ecd9a6', acc='#ffffff', fill='none', rise='#ff5f6d', fall='#3ddc97', flowline='#f3e3bc',
                          n1='#ffffff', n2='#e8c47a', n3='#b9a6ff', trend='#f3e3bc', area='#f3e3bc', hot='#ffffff',
                          chip='#d9b56a', chipacc='#ff5f6d', core='#3a3a42')),
}
KEYS = ('peach', 'navy', 'neon', 'coral', 'ice', 'noir')


def lit_faces(t):
    """左上打光：頂面提亮、左面維持、右面（背光）壓暗"""
    if t.get('dark'):
        return dict(top=mix(t['top'], '#ffffff', .14), left=t['left'], right=mix(t['right'], '#000000', .35))
    return dict(top=mix(t['top'], '#ffffff', .45), left=mix(t['left'], '#000000', .03), right=mix(t['right'], '#000000', .2))


def defs(u, t, lit):
    a, b, c = t['sheen']
    L0, L1, L2 = t['acc_lit']
    d = [f'<radialGradient id="{u}bg" cx="50%" cy="46%" r="72%"><stop offset="0" stop-color="#ffffff"/><stop offset=".6" stop-color="#fcfdfe"/><stop offset="1" stop-color="#f4f6f9"/></radialGradient>',
         f'<linearGradient id="{u}glass" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t["base0"]}"/><stop offset="1" stop-color="{t["base1"]}"/></linearGradient>',
         f'<linearGradient id="{u}sheen" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{a}"/><stop offset=".5" stop-color="{b}"/><stop offset="1" stop-color="{c}"/></linearGradient>',
         f'<filter id="{u}glow" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="2.6"/></filter>',
         f'<filter id="{u}soft" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="10"/></filter>',
         f'<filter id="{u}b6" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="6"/></filter>',
         f'<filter id="{u}b2" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="2"/></filter>',
         f'<filter id="{u}b1" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation=".8"/></filter>',   # 隔著玻璃的輕微模糊
         # 正面圖示的細描邊：把圖示的 alpha 往外長一點、填 halo 色，墊在圖示底下
         f'<filter id="{u}halo" x="-5%" y="-5%" width="110%" height="110%"><feMorphology in="SourceAlpha" operator="dilate" radius=".24" result="d"/>'
         f'<feFlood flood-color="{t["halo"]}" flood-opacity=".9"/><feComposite in2="d" operator="in" result="h"/><feMerge><feMergeNode in="h"/><feMergeNode in="SourceGraphic"/></feMerge></filter>']
    # 圓框與角框的漆色：打光版一律左上亮、右下暗；柔光版金屬系（海軍藍青銅、墨黑香檳金）用金屬漸層，其他用實色
    if lit:
        d.append(f'<linearGradient id="{u}acc" x1="40" y1="40" x2="472" y2="472" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="{L0}"/><stop offset=".55" stop-color="{L1}"/><stop offset="1" stop-color="{L2}"/></linearGradient>')
    elif t['metal']:
        d.append(f'<linearGradient id="{u}acc" x1="40" y1="40" x2="472" y2="472" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="{L0}"/><stop offset=".3" stop-color="{L1}"/>'
                 f'<stop offset=".5" stop-color="{L0}"/><stop offset=".75" stop-color="{L1}"/><stop offset="1" stop-color="{L2}"/></linearGradient>')
    if lit:
        d.append(f'<linearGradient id="{u}cast" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2a303e" stop-opacity=".42"/><stop offset=".55" stop-color="#2a303e" stop-opacity=".2"/><stop offset="1" stop-color="#2a303e" stop-opacity="0"/></linearGradient>')
    return '<defs>' + ''.join(d) + '</defs>'


def paint(u, t, lit):
    return f'url(#{u}acc)' if (lit or t['metal']) else t['acc']


def ring(u, t, lit):
    thin, thick, quad = [], [], []
    for i in range(72):
        a = 5*i; tt = math.radians(a)
        if a % 90 == 0: L, bk = 18, quad
        elif a % 30 == 0: L, bk = 11, thick
        else: L, bk = 7, thin
        bk.append(f'M{CX + RING_R*math.cos(tt):.1f} {CY + RING_R*math.sin(tt):.1f}L{CX + (RING_R - L)*math.cos(tt):.1f} {CY + (RING_R - L)*math.sin(tt):.1f}')
    p = paint(u, t, lit); thin_w = 1.8 if t['bw'] < 10 else 2.4
    return (f'<path d="{"".join(quad + thick)}" stroke="{t["acc"]}" stroke-width="8" stroke-linecap="round" opacity=".14" filter="url(#{u}glow)"/>'   # 很淡的同色光暈
            f'<path d="{"".join(thin)}" stroke="{p}" stroke-width="{thin_w}" stroke-linecap="round" opacity=".85"/>'
            f'<path d="{"".join(thick)}" stroke="{p}" stroke-width="{thin_w*1.5:.1f}" stroke-linecap="round"/>'
            f'<path d="{"".join(quad)}" stroke="{p}" stroke-width="{thin_w*2.3:.1f}" stroke-linecap="round"/>')


def see_ring(u, t, lit):
    """透視圈：細的連續圓，半徑 160；在立方頂點附近會被立方擋在後面（隔著玻璃淡淡看得到）"""
    return f'<circle cx="{CX}" cy="{CY}" r="{SEE_R}" fill="none" stroke="{paint(u, t, lit)}" stroke-width="2.4" stroke-dasharray="1 0" opacity=".9"/>'


def brackets(u, t, lit):
    x0 = y0 = BR; x1 = y1 = W - BR; L = BR_L; r = BR_RAD; w = t['bw']
    segs = [f'M{x0} {y0 + L}V{y0 + r}Q{x0} {y0} {x0 + r} {y0}H{x0 + L}', f'M{x1 - L} {y0}H{x1 - r}Q{x1} {y0} {x1} {y0 + r}V{y0 + L}',
            f'M{x0} {y1 - L}V{y1 - r}Q{x0} {y1} {x0 + r} {y1}H{x0 + L}', f'M{x1} {y1 - L}V{y1 - r}Q{x1} {y1} {x1 - r} {y1}H{x1 - L}']
    p = paint(u, t, lit)
    o = [f'<path d="{s}" fill="none" stroke="{t["acc"]}" stroke-width="{w + 8}" stroke-linecap="round" opacity=".14" filter="url(#{u}glow)"/>' for s in segs]
    o += [f'<path d="{s}" fill="none" stroke="{p}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>' for s in segs]
    if w >= 10:
        o += [f'<path d="{s}" fill="none" stroke="{t["acc_core"]}" stroke-width="{w*.26:.1f}" stroke-linecap="round" stroke-linejoin="round" opacity=".75"/>' for s in segs]
    return ''.join(o)


def hull(P_):
    P_ = sorted(set((round(x, 2), round(y, 2)) for x, y in P_))
    def cross(o, a, b): return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
    lo, up = [], []
    for q in P_:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], q) <= 0: lo.pop()
        lo.append(q)
    for q in reversed(P_):
        while len(up) >= 2 and cross(up[-2], up[-1], q) <= 0: up.pop()
        up.append(q)
    return lo[:-1] + up[:-1]


def ground_shadow(u, cb, t, lit):
    C = cb.C
    if not lit:
        return f'<ellipse cx="{CX}" cy="{cb.B[1] + 8:.1f}" rx="{R*.8:.1f}" ry="{R*.12:.1f}" fill="#3a4152" opacity=".26" filter="url(#{u}soft)"/>'
    foot = [C, cb.LR, cb.B, cb.LL]
    v = (R*1.2, R*.5)
    h = hull(foot + [(x + v[0], y + v[1]) for x, y in foot])
    hc = (sum(x for x, _ in h)/len(h) + 10, sum(y for _, y in h)/len(h) + 4)
    return (f'<polygon points="{pts(h)}" fill="url(#{u}cast)" filter="url(#{u}b6)"/>'
            # 光穿過有色玻璃：投影中間一團該色系的淡色（影子中心略淡、帶色調）
            f'<polygon points="{pts(shrink(h, hc, .5))}" fill="{t["tint"]}" opacity=".38" filter="url(#{u}soft)"/>'
            f'<path d="M{cb.LL[0]:.1f} {cb.LL[1] + 4:.1f}L{cb.B[0]:.1f} {cb.B[1] + 4:.1f}L{cb.LR[0]:.1f} {cb.LR[1] + 4:.1f}" fill="none" stroke="#1c2130" stroke-width="12" stroke-linejoin="round" opacity=".35" filter="url(#{u}b6)"/>')


def reflection(cb, k, lit, dark):
    """每一面一道斜向反光條：在面的 24 格座標裡畫（從面的左上角往右下斜），由貼面矩陣變形，所以一定裁在面內"""
    m = cb.matrix(k, 0)
    op1, op2 = (.42, .3) if lit else (.26, .18)
    if dark: op1, op2 = op1*.5, op2*.5
    return (f'<g transform="{m}"><polygon points="0,4 4,0 9.5,0 0,9.5" fill="#ffffff" opacity="{op1}"/>'
            f'<polygon points="0,11.5 11.5,0 13,0 0,13" fill="#ffffff" opacity="{op2}"/></g>')


def cube(u, t, lit):
    cb = Cube(CX, CY, R); C = cb.C
    v18.set_glyph_palette(dict(gly=t['gly']))
    F = dict(t, **(lit_faces(t) if lit else {}))
    dark = t.get('dark')
    hi = t['hi']
    o = [f'<polygon points="{pts(cb.hex)}" fill="url(#{u}glass)" fill-opacity="{t["base_op"]}"/>']
    # 背面：圖示＋三條看不見的稜，隔著玻璃（輕微模糊）
    back = ''.join(f'<g opacity="{t["back_op"]}" transform="{v17.place(cb, k, False)}">{v17.glyph(fn, u + k)}</g>' for k, fn in v17.BACK.items())
    back += (f'<path d="M{C[0]} {C[1]}L{cb.T[0]:.1f} {cb.T[1]:.1f}M{C[0]} {C[1]}L{cb.LL[0]:.1f} {cb.LL[1]:.1f}M{C[0]} {C[1]}L{cb.LR[0]:.1f} {cb.LR[1]:.1f}" '
             f'stroke="{t["edge"] if not dark else hi}" stroke-width="2.6" stroke-opacity=".55" stroke-linecap="round" stroke-dasharray="1 0"/>')
    o.append(f'<g filter="url(#{u}b1)">{back}</g>')
    for k in ('top', 'left', 'right'):
        q = cb.quad(k)
        o.append(f'<polygon points="{pts(q)}" fill="{F[k]}" fill-opacity="{t["face_op"]}"/>')
        o.append(f'<polygon points="{pts(q)}" fill="url(#{u}sheen)" opacity="{.2 if not lit else .14}"/>')
        o.append(reflection(cb, k, lit, dark))
        cen = (sum(x for x, _ in q)/4, sum(y for _, y in q)/4)
        o.append(f'<polygon points="{pts(shrink(q, cen, .9))}" fill="none" stroke="{hi}" stroke-opacity=".7" stroke-width="2" stroke-linejoin="round"/>')
    for k, fn in v17.FRONT.items():
        o.append(f'<g transform="{v17.place(cb, k, True)}" filter="url(#{u}halo)">{v17.glyph(fn, u + k)}</g>')
    y = f'M{C[0]} {C[1]}L{cb.UL[0]:.1f} {cb.UL[1]:.1f}M{C[0]} {C[1]}L{cb.UR[0]:.1f} {cb.UR[1]:.1f}M{C[0]} {C[1]}L{cb.B[0]:.1f} {cb.B[1]:.1f}'
    o.append(f'<path d="{y}" stroke="{hi}" stroke-width="10" stroke-opacity=".28" stroke-linecap="round" filter="url(#{u}b2)"/>')
    o.append(f'<path d="{y}" stroke="{hi}" stroke-width="4" stroke-opacity=".95" stroke-linecap="round"/>')
    # 玻璃厚邊：外側細暗線（白底上讓立方浮出來）→ 厚緣（半透明，透得到後面）→ 內側亮線
    # 外側細暗線只畫在厚緣的外圈（不是整條粗線墊底），厚緣本身才是半透明的
    o.append(f'<polygon points="{pts(shrink(cb.hex, C, 1 + (RIM*.5 + .6)/R))}" fill="none" stroke="{t["edge"]}" stroke-width="2.6" stroke-linejoin="round"/>')
    o.append(f'<polygon points="{pts(cb.hex)}" fill="none" stroke="{t["rim"]}" stroke-width="{RIM}" stroke-linejoin="round" opacity="{.55 if dark else .4}"/>')   # 厚緣半透明：後面的透視圈透得出來
    o.append(f'<polygon points="{pts(shrink(cb.hex, C, 1 - (RIM*.5 + 2)/R))}" fill="none" stroke="{hi}" stroke-width="2.4" stroke-linejoin="round" opacity=".95"/>')
    # 頂點高光點（柔光：上方三個；打光：左上兩個最亮）
    spots = [(cb.T, .8), (cb.UL, .8), (cb.UR, .6), (C, .7)] if not lit else [(cb.UL, 1), (cb.T, .85), (C, .6)]
    o += [f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="5.5" fill="{hi}" opacity="{a}" filter="url(#{u}b2)"/>' for p, a in spots]
    if lit:
        hl = f'M{cb.LL[0]:.1f} {cb.LL[1]:.1f}L{cb.UL[0]:.1f} {cb.UL[1]:.1f}L{cb.T[0]:.1f} {cb.T[1]:.1f}M{C[0]} {C[1]}L{cb.UL[0]:.1f} {cb.UL[1]:.1f}'
        o.append(f'<path d="{hl}" fill="none" stroke="{hi}" stroke-width="11" stroke-linecap="round" stroke-linejoin="round" opacity=".4" filter="url(#{u}b2)"/>')
        o.append(f'<path d="{hl}" fill="none" stroke="{hi}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>')
        dk = f'M{cb.UR[0]:.1f} {cb.UR[1]:.1f}L{cb.LR[0]:.1f} {cb.LR[1]:.1f}L{cb.B[0]:.1f} {cb.B[1]:.1f}'
        o.append(f'<path d="{dk}" fill="none" stroke="{mix(t["edge"], "#000000", .3)}" stroke-width="{RIM*.55:.1f}" stroke-linecap="round" stroke-linejoin="round" opacity=".45"/>')
    return ''.join(o), cb


def icon(key, lit, hide=None):
    """hide：'back'／'front'／'see' 時拿掉那一層（只給驗收量測用）"""
    t = T[key]; u = key[:2] + ('l' if lit else 's')
    saved = (v17.BACK, v17.FRONT)
    if hide == 'back': v17.BACK = {}
    if hide == 'front': v17.FRONT = {}
    cube_svg, cb = cube(u, t, lit)
    v17.BACK, v17.FRONT = saved
    return '\n'.join([f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {W}" width="{W}" height="{W}">', defs(u, t, lit),
                      f'<rect width="{W}" height="{W}" fill="url(#{u}bg)"/>', ground_shadow(u, cb, t, lit), ring(u, t, lit), brackets(u, t, lit),
                      '' if hide == 'see' else see_ring(u, t, lit), cube_svg, '</svg>'])


def render(names):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        pg = b.new_page(viewport={'width': 1024, 'height': 1024})
        for n in names:
            pg.goto('file://' + os.path.join(HERE, n + '.svg')); pg.wait_for_timeout(250)
            pg.evaluate("document.documentElement.setAttribute('width','1024');document.documentElement.setAttribute('height','1024')")
            pg.wait_for_timeout(80)
            pg.screenshot(path=os.path.join(HERE, n + '.png'), clip={'x': 0, 'y': 0, 'width': 1024, 'height': 1024})
        cell = lambda k, v: f'<div class="c"><img src="file://{HERE}/icon_{k}_{v}.svg"><p>{T[k]["name"]}</p></div>'
        rows = ''.join(f'<div class="lab">{lab}</div><div class="row">' + ''.join(cell(k, v) for k in KEYS) + '</div>' for v, lab in (('soft', '柔光'), ('lit', '左上打光')))
        html = (f'<!doctype html><html><head><meta charset="utf-8"><style>body{{margin:0;width:2280px;background:#ffffff;font-family:"WenQuanYi Zen Hei",sans-serif;color:#1d2f52}}'
                f'main{{padding:30px 40px 40px}}.lab{{font-size:30px;font-weight:700;letter-spacing:.12em;margin:10px 0 10px;color:#7a5530}}'
                f'.row{{display:flex;gap:20px}}.c{{width:350px;display:flex;flex-direction:column;align-items:center;border:1px solid #e8eaef;border-radius:18px;padding:0 0 12px}}'
                f'.c img{{width:350px;height:350px;border-radius:18px}}.c p{{margin:4px 0 0;font-size:26px;font-weight:700;letter-spacing:.08em}}</style></head><body><main>{rows}</main></body></html>')
        tmp = os.path.join(SCRATCH, '_v22_sheet.html'); open(tmp, 'w').write(html)
        pg.set_viewport_size({'width': 2280, 'height': 1000})
        pg.goto('file://' + tmp); pg.wait_for_timeout(900)
        hh = int(pg.evaluate("Math.ceil(document.querySelector('main').getBoundingClientRect().bottom)"))
        pg.screenshot(path=os.path.join(HERE, '白底六色系.png'), clip={'x': 0, 'y': 0, 'width': 2280, 'height': hh}, full_page=True)
        b.close()


def main():
    names = []
    for k in KEYS:
        for v in ('soft', 'lit'):
            open(os.path.join(HERE, f'icon_{k}_{v}.svg'), 'w').write(icon(k, v == 'lit'))
            names.append(f'icon_{k}_{v}')
    for k in KEYS:
        t = T[k]
        print(f'{t["name"]}：角框／刻度 {t["acc"]} 對白底 {contrast(t["acc"]):.2f}:1；立方外側細線 {t["edge"]} 對白底 {contrast(t["edge"]):.2f}:1')
    render(names)


if __name__ == '__main__':
    main()
