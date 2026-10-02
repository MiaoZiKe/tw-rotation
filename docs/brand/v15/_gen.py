# 第十五輪〈股立方〉：平面的六角放大鏡（2D）＋ 鏡片裡一顆等角玻璃立方（2.5D）
# Andy 第十五輪：「把手需要相交且垂直六角形左上及右下平行處／看起來會像是 2D 的六角放大鏡，看裡面 2.5D 的立方體／
#                 籌碼改成原來那樣，走勢圖與資金流互換，並且每個面圖示需要一點配色／周圍框需要距離再寬點，先給出滿版圖示即可」
# 這一輪只交滿版圖示（icon_full_light.svg／.png）與圓角 App 版（icon_light.svg）；深色、小尺寸、標準字下一輪再做。
# 執行：python docs/brand/v15/_gen.py
import math, os, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location('v14', os.path.join(HERE, '..', 'v14', '_gen.py'))
v14 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(v14)   # v14 會再 import v13；兩邊的產生段落都包在 main()，不會重寫檔案
v13 = v14.v13
Cube, pts, shrink = v14.Cube, v14.pts, v14.shrink

# ---------- 規格（512 畫布；PNG 輸出 1024 = 2 倍）----------
W = 512
LX, LY = 226, 220          # 鏡片中心（整體往左上挪，讓 60° 的把手放得下）
R = 118                    # 鏡片六角形外接半徑（鏡框中心線）
FRAME = 24                 # 鏡框線寬
R_IN = R - FRAME/2         # 鏡框內緣的外接半徑 = 106
CUBE_S = round(R_IN*.70)   # 立方外接半徑 ≈ 鏡片內徑 70% = 74
RING_IN, TICK_L, TICK_S = 150, 18, 10   # 刻度環內緣半徑、長刻度、短刻度
BR = 42                    # 角框中心線距畫布邊（線寬 20 → 外緣距邊 32）
BR_L, BR_W = 70, 20        # 角框每支臂長、線寬（線寬維持 v14 的 20）
HANDLE_ANG = 60            # 把手方向：垂直於右下邊（30° 頂點 → 90° 頂點）

P = dict(name='light', bg0='#ffffff', bg1='#eaf3fa',
         bracket='#1d3557', tick='#2c4b6c',
         frame='#24557b', frame_hi='#6fb3e2', lens='#e2f3fc',
         outline='#2b6ea3', hi='#ffffff',
         top='#eef9fe', left='#cdeaf9', right='#b4dcf3', base='#dcf0fa', face_op=.6, base_op=.95,
         hidden_op=.8, back_op=.62, glyph='#12345a')

# 面上圖示的配色（同一組也套在 v13 的徽章上）。技術面照台股慣例紅漲綠跌；基本面不用紅綠。
GLY = dict(acc='#1474d3', fill='none', ink='#12345a', rise='#d93a4f', fall='#14936a',
           flowline='#1474d3', n1='#f08a4b', n2='#22a6a0', n3='#7b6cf0',
           trend='#1474d3', area='#5cb6f0', area_op=.32, hot='#f08a4b',
           chip='#e7b04a', chipacc='#e0526a', core='#22a6a0')

# 走勢圖與資金流互換：頂面＝基本面（走勢圖），資金面（分流圖）移到右上背面
FRONT = {'top': v13.fund, 'left': v13.candle, 'right': v13.chain}
BACK = {'bl': v13.chips, 'br': v13.flow, 'bottom': v13.event}


def hexagon(cx, cy, r):
    """平面正六角形，尖頂朝上：頂點角度 -90°、-30°、30°、90°、150°、210°（SVG y 朝下）"""
    return [(cx + r*math.cos(math.radians(a)), cy + r*math.sin(math.radians(a))) for a in (-90, -30, 30, 90, 150, 210)]


def glyph(fn, sw):
    return (f'<g fill="none" stroke="{GLY["ink"]}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round">'
            + ''.join(fn(GLY)) + '</g>')


def defs(u):
    d = [f'<linearGradient id="{u}bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{P["bg0"]}"/><stop offset="1" stop-color="{P["bg1"]}"/></linearGradient>',
         f'<linearGradient id="{u}glass" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{P["top"]}"/><stop offset=".55" stop-color="{P["base"]}"/><stop offset="1" stop-color="{P["right"]}"/></linearGradient>',
         f'<linearGradient id="{u}wood" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#b47a4c"/><stop offset=".22" stop-color="#e2a96c"/>'
         f'<stop offset=".45" stop-color="#f6c48a"/><stop offset=".62" stop-color="#facd91"/><stop offset=".85" stop-color="#d39a5e"/><stop offset="1" stop-color="#9c6a40"/></linearGradient>',
         f'<radialGradient id="{u}cap" cx="40%" cy="38%" r="70%"><stop offset="0" stop-color="#f7c88f"/><stop offset=".7" stop-color="#e0a468"/><stop offset="1" stop-color="#c08452"/></radialGradient>',
         f'<linearGradient id="{u}metal" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0d4f99"/><stop offset=".3" stop-color="#3d9bf0"/>'
         f'<stop offset=".5" stop-color="#bfe3ff"/><stop offset=".7" stop-color="#1474d3"/><stop offset="1" stop-color="#0a3d78"/></linearGradient>',
         f'<clipPath id="{u}lensclip"><polygon points="{pts(hexagon(LX, LY, R_IN))}"/></clipPath>']
    return '<defs>' + ''.join(d) + '</defs>'


def ring():
    """外圈刻度：60 格，每 5 格一根粗長刻度；把手經過的 48°～72° 留白"""
    thin, thick = [], []
    for i in range(60):
        a = 6*i
        if 48 <= a <= 72: continue
        t = math.radians(a)
        L = TICK_L if i % 5 == 0 else TICK_S
        r0 = RING_IN + TICK_L                     # 長短刻度外緣對齊
        d = f'M{LX + r0*math.cos(t):.1f} {LY + r0*math.sin(t):.1f}L{LX + (r0 - L)*math.cos(t):.1f} {LY + (r0 - L)*math.sin(t):.1f}'
        (thick if i % 5 == 0 else thin).append(d)
    return (f'<path d="{"".join(thin)}" stroke="{P["tick"]}" stroke-width="3.4" stroke-linecap="round" opacity=".8"/>'
            f'<path d="{"".join(thick)}" stroke="{P["tick"]}" stroke-width="7" stroke-linecap="round"/>')


def brackets():
    x0 = y0 = BR; x1 = y1 = W - BR; L = BR_L
    d = (f'M{x0} {y0 + L}V{y0}H{x0 + L}' f'M{x1 - L} {y0}H{x1}V{y0 + L}'
         f'M{x0} {y1 - L}V{y1}H{x0 + L}' f'M{x1} {y1 - L}V{y1}H{x1 - L}')
    return f'<path d="{d}" fill="none" stroke="{P["bracket"]}" stroke-width="{BR_W}" stroke-linecap="round" stroke-linejoin="round"/>'


def lens_back(u):
    """鏡片：淡冰藍的平面玻璃（立方畫在它上面）"""
    return f'<polygon points="{pts(hexagon(LX, LY, R))}" fill="{P["lens"]}"/>'


def lens_front(u):
    """鏡片前景：平面斜向反光帶（裁在鏡片內）＋鏡框（深藍粗框＋金屬亮線＋內緣白線）"""
    # 反光帶沿 -30°（左下→右上）方向斜切過鏡片左上角，兩條：一寬一細
    def band(off, w):
        dx, dy = math.cos(math.radians(-30)), math.sin(math.radians(-30))   # 帶子走向
        nx, ny = -dy, dx                                                      # 法向（往右下）
        c0 = (LX - nx*off, LY - ny*off)
        L = 2*R
        p = [(c0[0] - dx*L, c0[1] - dy*L), (c0[0] + dx*L, c0[1] + dy*L)]
        return [(p[0][0], p[0][1]), (p[1][0], p[1][1]), (p[1][0] + nx*w, p[1][1] + ny*w), (p[0][0] + nx*w, p[0][1] + ny*w)]
    glare = (f'<g clip-path="url(#{u}lensclip)"><polygon points="{pts(band(R_IN*.86, 22))}" fill="#ffffff" opacity=".55"/>'
             f'<polygon points="{pts(band(R_IN*.58, 8))}" fill="#ffffff" opacity=".45"/></g>')
    hx = hexagon(LX, LY, R)
    return (glare +
            f'<polygon points="{pts(hx)}" fill="none" stroke="{P["frame"]}" stroke-width="{FRAME}" stroke-linejoin="round"/>'
            f'<polygon points="{pts(hexagon(LX, LY, R + FRAME*.22))}" fill="none" stroke="{P["frame_hi"]}" stroke-width="3" stroke-opacity=".75" stroke-linejoin="round"/>'
            f'<polygon points="{pts(hexagon(LX, LY, R_IN - 2.5))}" fill="none" stroke="#ffffff" stroke-width="2.5" stroke-opacity=".9" stroke-linejoin="round"/>')


def glass_cube(cb, u, ow=4.2, yw=3.6, sw=1.85):
    """鏡片裡的等角冰藍玻璃立方：玻璃質感與面上圖示貼法照 v14，面的分配與配色是第十五輪的"""
    C = cb.C
    o = [f'<polygon points="{pts(cb.hex)}" fill="url(#{u}glass)" fill-opacity="{P["base_op"]}"/>']
    for k, fn in BACK.items():   # 後三面：隔著玻璃，降不透明度
        o.append(f'<g opacity="{P["back_op"]}" transform="{cb.place(k, .27)}">{glyph(fn, sw)}</g>')
    o.append(f'<path d="M{C[0]:.1f} {C[1]:.1f}L{cb.T[0]:.1f} {cb.T[1]:.1f}M{C[0]:.1f} {C[1]:.1f}L{cb.LL[0]:.1f} {cb.LL[1]:.1f}M{C[0]:.1f} {C[1]:.1f}L{cb.LR[0]:.1f} {cb.LR[1]:.1f}" '
             f'stroke="{P["hi"]}" stroke-width="{yw*.5:.1f}" stroke-opacity="{P["hidden_op"]}" stroke-linecap="round"/>')
    for k in ('top', 'left', 'right'):
        q = cb.quad(k)
        o.append(f'<polygon points="{pts(q)}" fill="{P[k]}" fill-opacity="{P["face_op"]}"/>')
        cen = (sum(x for x, _ in q)/4, sum(y for _, y in q)/4)
        o.append(f'<polygon points="{pts(shrink(q, cen, .88))}" fill="none" stroke="{P["hi"]}" stroke-opacity=".75" stroke-width="{yw*.4:.1f}" stroke-linejoin="round"/>')
    for k, fn in FRONT.items():
        o.append(f'<g transform="{cb.place(k, .11)}">{glyph(fn, sw)}</g>')
    o.append(f'<path d="M{C[0]:.1f} {C[1]:.1f}L{cb.UL[0]:.1f} {cb.UL[1]:.1f}M{C[0]:.1f} {C[1]:.1f}L{cb.UR[0]:.1f} {cb.UR[1]:.1f}M{C[0]:.1f} {C[1]:.1f}L{cb.B[0]:.1f} {cb.B[1]:.1f}" '
             f'stroke="{P["hi"]}" stroke-width="{yw:.1f}" stroke-opacity=".95" stroke-linecap="round"/>')
    o.append(f'<polygon points="{pts(cb.hex)}" fill="none" stroke="{P["outline"]}" stroke-width="{ow:.1f}" stroke-linejoin="round"/>')
    return ''.join(o)


def handle_geom():
    """把手幾何：根部在右下邊的中點（鏡框中心線上），沿 60°（垂直於右下邊）往外"""
    v30, v90 = hexagon(LX, LY, R)[2], hexagon(LX, LY, R)[3]
    mid = ((v30[0] + v90[0])/2, (v30[1] + v90[1])/2)
    edge = (v90[0] - v30[0], v90[1] - v30[1])
    axis = (math.cos(math.radians(HANDLE_ANG)), math.sin(math.radians(HANDLE_ANG)))
    return mid, edge, axis


HW = 22                        # 握把半徑
COLLAR0, COLLAR1 = 4, 36       # 金屬環：從鏡框中心線往外 4 起（鏡框外緣在 +12，所以壓進鏡框 8）到 36
WOOD1 = 150                    # 木柄末端（端面中心）距根部


def handle(u):
    mid, _, _ = handle_geom()
    return (f'<g transform="translate({mid[0]:.2f} {mid[1]:.2f}) rotate({HANDLE_ANG})">'
            f'<rect x="{COLLAR1 - 3}" y="{-HW}" width="{WOOD1 - COLLAR1 + 3}" height="{2*HW}" rx="4" fill="url(#{u}wood)"/>'                    # 木柄
            f'<path d="M{COLLAR1 + 3} {-HW*.42:.1f}H{WOOD1 - 10}" stroke="#fff3df" stroke-width="4" stroke-linecap="round" opacity=".55"/>'       # 木頭高光
            f'<ellipse cx="{WOOD1}" cy="0" rx="{HW*.5:.1f}" ry="{HW}" fill="url(#{u}cap)" stroke="#8a5a34" stroke-width="2"/>'                   # 圓頭端面（跟著軸線轉）
            f'<rect x="{COLLAR0}" y="{-HW*.8:.1f}" width="{COLLAR1 - COLLAR0}" height="{HW*1.6:.1f}" rx="5" fill="url(#{u}metal)" stroke="#0a3566" stroke-width="2"/>'  # 金屬環
            f'<path d="M{COLLAR1} {-HW:.1f}V{HW:.1f}" stroke="#5a3218" stroke-width="4"/>'                                                        # 環與木頭交界
            f'</g>')


def icon(u, full=True):
    """full=True：滿版（背景鋪滿正方形）；False：圓角 App 圖示（內容縮 0.9 免得角框被圓角切到）"""
    cb = Cube(LX, LY, CUBE_S)
    body = (ring() + brackets() + lens_back(u) + glass_cube(cb, u) + handle(u) + lens_front(u))
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {W}" width="{W}" height="{W}">', defs(u)]
    if full:
        o.append(f'<rect width="{W}" height="{W}" fill="url(#{u}bg)"/>')
        o.append(body)
    else:
        o.append(f'<rect x="4" y="4" width="{W - 8}" height="{W - 8}" rx="112" fill="url(#{u}bg)" stroke="#d5e3ef" stroke-width="4"/>')
        o.append(f'<g transform="translate({W/2} {W/2}) scale(.9) translate({-W/2} {-W/2})">{body}</g>')
    o.append('</svg>')
    return '\n'.join(o)


def check():
    """自我檢查：把手軸線與右下邊的內積、立方與鏡框的距離、把手與右下角框的距離"""
    mid, edge, axis = handle_geom()
    el = math.hypot(*edge)
    dot = (axis[0]*edge[0] + axis[1]*edge[1]) / el
    end = (mid[0] + axis[0]*(WOOD1 + HW*.5), mid[1] + axis[1]*(WOOD1 + HW*.5))
    print(f'右下邊單位向量 ({edge[0]/el:.3f}, {edge[1]/el:.3f})，把手軸線 ({axis[0]:.3f}, {axis[1]:.3f})，內積 {dot:.2e}')
    print(f'把手根部（右下邊中點）{mid[0]:.1f},{mid[1]:.1f}；金屬環從鏡框中心線往外 {COLLAR0}～{COLLAR1}，鏡框外緣在 +{FRAME/2:.0f} → 壓進鏡框 {FRAME/2 - COLLAR0:.0f}')
    print(f'立方外接半徑 {CUBE_S}／鏡片內緣外接半徑 {R_IN:.0f} = {CUBE_S/R_IN:.2f}；立方頂點離鏡框內緣 {R_IN - CUBE_S - 2.1:.1f}（扣立方輪廓半線寬）')
    print(f'鏡框外緣頂點半徑 {R + FRAME/2:.0f}，刻度環內緣 {RING_IN} → 留白 {RING_IN - R - FRAME/2:.0f}（邊中點處 {RING_IN - (R + FRAME/2)*S3:.0f}）')
    print(f'刻度環外緣 {RING_IN + TICK_L}：上 {LY - RING_IN - TICK_L - 3.5:.0f}、左 {LX - RING_IN - TICK_L - 3.5:.0f}（畫布座標）；角框外緣距邊 {BR - BR_W/2:.0f}')
    print(f'把手端面中心 {end[0]:.1f},{end[1]:.1f}；右下角框內緣 x≥{W - BR - BR_L - BR_W/2:.0f} 且 y≥{W - BR - BR_W/2:.0f}')


S3 = math.cos(math.radians(30))


def render_png():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('沒有 Playwright，略過 PNG'); return
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        pg = b.new_page(viewport={'width': 1024, 'height': 1024})
        for name in ('icon_full_light', 'icon_light'):
            pg.goto('file://' + os.path.join(HERE, name + '.svg')); pg.wait_for_timeout(300)
            # SVG 直接開會以 512 顯示；用 zoom 放大到 1024 再截
            pg.evaluate("document.documentElement.setAttribute('width','1024');document.documentElement.setAttribute('height','1024')")
            pg.wait_for_timeout(100)
            pg.screenshot(path=os.path.join(HERE, name + '.png'), clip={'x': 0, 'y': 0, 'width': 1024, 'height': 1024},
                          omit_background=(name == 'icon_light'))
        b.close()


def main():
    open(os.path.join(HERE, 'icon_full_light.svg'), 'w').write(icon('f', full=True))
    open(os.path.join(HERE, 'icon_light.svg'), 'w').write(icon('r', full=False))
    check()
    render_png()


if __name__ == '__main__':
    main()
