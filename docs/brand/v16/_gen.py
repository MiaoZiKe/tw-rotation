# 第十六輪〈股立方〉：立方體＝鏡框本身。等角立方的六角外輪廓就是放大鏡的粗框，框內是冰藍玻璃立方；
# 把手從右下邊中點垂直伸出，整顆（立方＋框＋把手）繞中心轉 −15°，把手軸線從 60° 變 45°，正對畫布右下角。
# Andy 第十六輪：「立方體就是鏡框本身，右下角的框去除，讓中間的圖在填滿一點，並且把把手延伸右下角空位，
#                 所以整個六角形會因為把手而一點偏轉」
# 這一輪只交滿版圖示：icon_full_light.svg／.png（1024×1024）。
# 執行：python docs/brand/v16/_gen.py
import math, os, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location('v15', os.path.join(HERE, '..', 'v15', '_gen.py'))
v15 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(v15)   # v15 → v14 → v13，產生段落都包在 main()，不會重寫檔案
Cube, pts, shrink, hexagon, glyph = v15.Cube, v15.pts, v15.shrink, v15.hexagon, v15.glyph
FRONT, BACK = v15.FRONT, v15.BACK   # 上＝基本、左＝技術、右＝產業；背面：左上＝籌碼、右上＝資金、底＝事件（配色同 v15 的 GLY）

# ---------- 規格（512 畫布；PNG 輸出 1024 = 2 倍）----------
W = 512
LX, LY = 252, 246          # 六角（立方）中心：參考圖的立方幾乎置中，只往左上偏一點讓把手有位置
R = 175                    # 立方外接半徑＝鏡框中心線；寬 2R·cos30° = 303 ≈ 畫布 59%（參考圖量到立方佔寬 55～60%、高 67%）
FRAME = 24                 # 鏡框線寬（延用 v15 樣式）
R_IN = R - FRAME/2
ROT = -15                  # 整顆繞中心旋轉（SVG 角度，負＝逆時針）
BASE_ANG = 60              # 未旋轉時把手垂直於右下邊的方向
RING_IN, TICK_L, TICK_S = 196, 16, 9    # 刻度環緊貼立方外圍：內緣 196（鏡框外緣頂點 187）；外徑 424 ≈ 畫布 83%（參考圖量到 81%）
BR, BR_L, BR_W = 34, 62, 20             # 角框靠近四角：中心線距邊 34（外緣距邊 24）、臂長、線寬 20
# 把手照參考圖：短而粗的胡桃木柄＋根部一圈銀色金屬環＋圓頭（參考圖量到：木柄長約畫布 26%、直徑約 10%、軸線 45°）
HW = 25                    # 握把半徑（直徑 50 ≈ 畫布 10%）
COLLAR0, COLLAR1 = 3, 26   # 金屬環：從鏡框中心線往外 3～26（鏡框外緣在 +12 → 壓進 9）
WOOD1 = 150                # 木柄圓頭最外點距根部（金屬環＋木柄 ≈ 147 ≈ 畫布 29%；木頭本身 124 ≈ 24%）

S3 = math.cos(math.radians(30))
P = dict(bg0='#ffffff', bg1='#eaf3fa', bracket='#1d3557', tick='#2c4b6c',
         frame='#24557b', frame_hi='#6fb3e2', hi='#ffffff',
         top='#eef9fe', left='#cdeaf9', right='#b4dcf3', base='#dcf0fa', face_op=.6, base_op=.95,
         hidden_op=.8, back_op=.5)


def rot(p, deg=ROT, c=(LX, LY)):
    a = math.radians(deg); x, y = p[0] - c[0], p[1] - c[1]
    return (c[0] + x*math.cos(a) - y*math.sin(a), c[1] + x*math.sin(a) + y*math.cos(a))


def defs(u):
    d = [f'<linearGradient id="{u}bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{P["bg0"]}"/><stop offset="1" stop-color="{P["bg1"]}"/></linearGradient>',
         f'<linearGradient id="{u}glass" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{P["top"]}"/><stop offset=".55" stop-color="{P["base"]}"/><stop offset="1" stop-color="{P["right"]}"/></linearGradient>',
         f'<linearGradient id="{u}wood" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8c5735"/><stop offset=".22" stop-color="#c08a5a"/>'
         f'<stop offset=".45" stop-color="#d4a06c"/><stop offset=".7" stop-color="#bb8859"/><stop offset="1" stop-color="#7d4a2b"/></linearGradient>',
         f'<radialGradient id="{u}cap" cx="40%" cy="38%" r="70%"><stop offset="0" stop-color="#f7c88f"/><stop offset=".7" stop-color="#e0a468"/><stop offset="1" stop-color="#c08452"/></radialGradient>',
         f'<linearGradient id="{u}metal" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9aa3ad"/><stop offset=".3" stop-color="#e9edf1"/>'
         f'<stop offset=".5" stop-color="#ffffff"/><stop offset=".75" stop-color="#c3cad3"/><stop offset="1" stop-color="#7f8994"/></linearGradient>',
         f'<clipPath id="{u}clip"><polygon points="{pts(hexagon(LX, LY, R_IN))}"/></clipPath>']
    return '<defs>' + ''.join(d) + '</defs>'


def handle_axis():
    return BASE_ANG + ROT    # 45°


def ring():
    """刻度環（不跟著轉，60 格對齊畫布）；把手經過的角度留白"""
    ha = handle_axis(); half = math.degrees(math.atan2(HW + 8, RING_IN)) + 2
    thin, thick = [], []
    r0 = RING_IN + TICK_L
    for i in range(60):
        a = 6*i
        if abs(((a - ha) + 180) % 360 - 180) <= half: continue
        t = math.radians(a); L = TICK_L if i % 5 == 0 else TICK_S
        d = f'M{LX + r0*math.cos(t):.1f} {LY + r0*math.sin(t):.1f}L{LX + (r0 - L)*math.cos(t):.1f} {LY + (r0 - L)*math.sin(t):.1f}'
        (thick if i % 5 == 0 else thin).append(d)
    return (f'<path d="{"".join(thin)}" stroke="{P["tick"]}" stroke-width="3.4" stroke-linecap="round" opacity=".8"/>'
            f'<path d="{"".join(thick)}" stroke="{P["tick"]}" stroke-width="7" stroke-linecap="round"/>')


def brackets():
    """只留左上、右上、左下三個角框；右下角讓給把手"""
    x0 = y0 = BR; x1 = y1 = W - BR; L = BR_L
    d = f'M{x0} {y0 + L}V{y0}H{x0 + L}M{x1 - L} {y0}H{x1}V{y0 + L}M{x0} {y1 - L}V{y1}H{x0 + L}'
    return f'<path d="{d}" fill="none" stroke="{P["bracket"]}" stroke-width="{BR_W}" stroke-linecap="round" stroke-linejoin="round"/>'


def place(cb, k, front):
    """立方放大到 R=175 後，v14 的預設比例讓頂面走勢圖的縱軸太粗、背面淡圖太搶眼，這裡收小一點"""
    if k in ('top', 'bottom'):
        return cb.matrix_flat(k, .52 if front else .38)
    return cb.matrix(k, .13 if front else .31)


def cube_glass(cb, u, yw=7, sw=1.5):
    """框內的冰藍玻璃立方（未旋轉座標；外面整組再轉 −15°）"""
    C = cb.C
    o = [f'<polygon points="{pts(cb.hex)}" fill="url(#{u}glass)" fill-opacity="{P["base_op"]}"/>']
    for k, fn in BACK.items():
        o.append(f'<g opacity="{P["back_op"]}" transform="{place(cb, k, False)}">{glyph(fn, sw)}</g>')
    o.append(f'<path d="M{C[0]:.1f} {C[1]:.1f}L{cb.T[0]:.1f} {cb.T[1]:.1f}M{C[0]:.1f} {C[1]:.1f}L{cb.LL[0]:.1f} {cb.LL[1]:.1f}M{C[0]:.1f} {C[1]:.1f}L{cb.LR[0]:.1f} {cb.LR[1]:.1f}" '
             f'stroke="{P["hi"]}" stroke-width="{yw*.45:.1f}" stroke-opacity="{P["hidden_op"]}" stroke-linecap="round"/>')
    for k in ('top', 'left', 'right'):
        q = cb.quad(k)
        o.append(f'<polygon points="{pts(q)}" fill="{P[k]}" fill-opacity="{P["face_op"]}"/>')
        cen = (sum(x for x, _ in q)/4, sum(y for _, y in q)/4)
        o.append(f'<polygon points="{pts(shrink(q, cen, .86))}" fill="none" stroke="{P["hi"]}" stroke-opacity=".7" stroke-width="{yw*.3:.1f}" stroke-linejoin="round"/>')
    # 平面斜向反光帶：只在鏡框內緣左上角那一小塊，很淡，避開面上圖示
    def band(off, w):
        dx, dy = math.cos(math.radians(-30)), math.sin(math.radians(-30)); nx, ny = -dy, dx
        c0 = (LX - nx*off, LY - ny*off); L = 2*R
        return [(c0[0] - dx*L, c0[1] - dy*L), (c0[0] + dx*L, c0[1] + dy*L), (c0[0] + dx*L + nx*w, c0[1] + dy*L + ny*w), (c0[0] - dx*L + nx*w, c0[1] - dy*L + ny*w)]
    o.append(f'<g clip-path="url(#{u}clip)"><polygon points="{pts(band(R_IN*.9, 16))}" fill="#ffffff" opacity=".4"/>'
             f'<polygon points="{pts(band(R_IN*.74, 6))}" fill="#ffffff" opacity=".3"/></g>')
    for k, fn in FRONT.items():
        o.append(f'<g transform="{place(cb, k, True)}">{glyph(fn, sw)}</g>')
    o.append(f'<path d="M{C[0]:.1f} {C[1]:.1f}L{cb.UL[0]:.1f} {cb.UL[1]:.1f}M{C[0]:.1f} {C[1]:.1f}L{cb.UR[0]:.1f} {cb.UR[1]:.1f}M{C[0]:.1f} {C[1]:.1f}L{cb.B[0]:.1f} {cb.B[1]:.1f}" '
             f'stroke="{P["hi"]}" stroke-width="{yw:.1f}" stroke-opacity=".95" stroke-linecap="round"/>')
    return ''.join(o)


def frame():
    """鏡框＝立方的六角外輪廓（v15 樣式：深藍粗框＋外側金屬亮線＋內緣白線）"""
    return (f'<polygon points="{pts(hexagon(LX, LY, R))}" fill="none" stroke="{P["frame"]}" stroke-width="{FRAME}" stroke-linejoin="round"/>'
            f'<polygon points="{pts(hexagon(LX, LY, R + FRAME*.22))}" fill="none" stroke="{P["frame_hi"]}" stroke-width="3" stroke-opacity=".75" stroke-linejoin="round"/>'
            f'<polygon points="{pts(hexagon(LX, LY, R_IN - 2.5))}" fill="none" stroke="#ffffff" stroke-width="2.5" stroke-opacity=".9" stroke-linejoin="round"/>')


def handle_root():
    """未旋轉座標的把手根部：右下邊（30° 頂點 → 90° 頂點）中點"""
    h = hexagon(LX, LY, R)
    return ((h[2][0] + h[3][0])/2, (h[2][1] + h[3][1])/2)


def handle(u):
    """參考圖風格的短粗木柄（局部座標：x 沿把手軸線往外，0＝鏡框中心線上的右下邊中點）"""
    m = handle_root()
    x0, x1 = COLLAR1 - 2, WOOD1                 # 木頭起點、圓頭最外點
    rx = HW*.8                                  # 圓頭的半橢圓深度
    xe = x1 - rx
    wood = f'M{x0} {-HW}H{xe}A{rx} {HW} 0 0 1 {xe} {HW}H{x0}Z'
    groove = xe - HW*.35                        # 靠近端頭的一圈溝（參考圖有）
    grain = (f'M{x0 + 4} {-HW*.55:.1f}C{x0 + 30} {-HW*.85:.1f} {x0 + 52} {-HW*.2:.1f} {x0 + 80} {-HW*.5:.1f}S{xe - 6} {-HW*.75:.1f} {xe + 10} {-HW*.35:.1f}'
             f'M{x0 + 6} {HW*.35:.1f}C{x0 + 28} {HW*.1:.1f} {x0 + 46} {HW*.7:.1f} {x0 + 74} {HW*.45:.1f}S{xe - 10} {HW*.2:.1f} {xe + 8} {HW*.55:.1f}'
             f'M{x0 + 14} {-HW*.05:.1f}C{x0 + 36} {-HW*.3:.1f} {x0 + 58} {HW*.15:.1f} {x0 + 88} {-HW*.02:.1f}')
    knot = f'<ellipse cx="{x0 + 52}" cy="{HW*.12:.1f}" rx="13" ry="{HW*.32:.1f}" fill="none"/><ellipse cx="{x0 + 52}" cy="{HW*.12:.1f}" rx="6" ry="{HW*.14:.1f}" fill="none"/>'
    return (f'<g transform="translate({m[0]:.2f} {m[1]:.2f}) rotate({BASE_ANG})">'
            f'<clipPath id="{u}woodclip"><path d="{wood}"/></clipPath>'
            f'<path d="{wood}" fill="url(#{u}wood)"/>'
            f'<g clip-path="url(#{u}woodclip)" stroke="#7a4626" stroke-width="2.4" stroke-linecap="round" fill="none" opacity=".75">'
            f'<path d="{grain}"/>{knot}'
            f'<path d="M{xe - 2} {-HW*.75:.1f}A{rx*.55:.1f} {HW*.6:.1f} 0 0 1 {xe - 2} {HW*.75:.1f}"/>'          # 圓頭上的年輪
            f'</g>'
            f'<path d="M{x0 + 6} {-HW*.5:.1f}H{groove - 8}" stroke="#ffe9c9" stroke-width="5" stroke-linecap="round" opacity=".35"/>'   # 高光
            f'<path d="M{groove} {-HW}A{HW*.32:.1f} {HW} 0 0 1 {groove} {HW}" fill="none" stroke="#4a2a16" stroke-width="3.2"/>'          # 端頭的溝
            f'<path d="{wood}" fill="none" stroke="#4a2a16" stroke-width="3.6" stroke-linejoin="round"/>'                                   # 深咖啡外框
            f'<rect x="{COLLAR0}" y="{-HW*.86:.1f}" width="{COLLAR1 - COLLAR0}" height="{HW*1.72:.1f}" rx="7" fill="url(#{u}metal)" stroke="#4a2a16" stroke-width="3.2"/>'  # 銀色金屬環
            f'</g>')


def icon(u='f'):
    cb = Cube(LX, LY, R)
    # 由下往上：背景 → 刻度環 → 角框 → 〔整組轉 −15°：把手（根部被鏡框蓋住）→ 玻璃立方 → 鏡框〕
    lens = handle(u) + cube_glass(cb, u) + frame()
    return '\n'.join([f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {W}" width="{W}" height="{W}">', defs(u),
                      f'<rect width="{W}" height="{W}" fill="url(#{u}bg)"/>', ring(), brackets(),
                      f'<g transform="rotate({ROT} {LX} {LY})">{lens}</g>', '</svg>'])


def check():
    h = [rot(p) for p in hexagon(LX, LY, R)]
    edge = (h[3][0] - h[2][0], h[3][1] - h[2][1]); el = math.hypot(*edge)
    ax = (math.cos(math.radians(handle_axis())), math.sin(math.radians(handle_axis())))
    m = rot(handle_root())
    cap = (m[0] + ax[0]*(WOOD1 - HW*.8), m[1] + ax[1]*(WOOD1 - HW*.8))
    far = [(m[0] + ax[0]*WOOD1, m[1] + ax[1]*WOOD1), (cap[0] - ax[1]*HW, cap[1] + ax[0]*HW), (cap[0] + ax[1]*HW, cap[1] - ax[0]*HW)]
    hx_out = [rot(p) for p in hexagon(LX, LY, R + FRAME/2)]
    print(f'旋轉後右下邊單位向量 ({edge[0]/el:.3f}, {edge[1]/el:.3f})，把手軸線 {handle_axis()}° ({ax[0]:.3f}, {ax[1]:.3f})，內積 {(ax[0]*edge[0] + ax[1]*edge[1])/el:.1e}')
    print(f'把手根部 {m[0]:.1f},{m[1]:.1f}；金屬環從鏡框中心線往外 {COLLAR0}～{COLLAR1}，鏡框外緣 +{FRAME/2} → 壓進 {FRAME/2 - COLLAR0:.1f}')
    print(f'圓頭中心 {cap[0]:.1f},{cap[1]:.1f}（1024：{cap[0]*2:.0f},{cap[1]*2:.0f}）；端面最外點（1024）：' + '、'.join(f'{x*2:.0f},{y*2:.0f}' for x, y in far))
    print(f'鏡框外緣頂點（含旋轉）x {min(p[0] for p in hx_out):.0f}～{max(p[0] for p in hx_out):.0f}、y {min(p[1] for p in hx_out):.0f}～{max(p[1] for p in hx_out):.0f}')
    print(f'刻度環 {RING_IN}～{RING_IN + TICK_L}，與鏡框外緣頂點留白 {RING_IN - R - FRAME/2:.1f}；刻度環外緣：上 {LY - RING_IN - TICK_L - 3.5:.0f}、左 {LX - RING_IN - TICK_L - 3.5:.0f}、右 {W - LX - RING_IN - TICK_L - 3.5:.0f}、下 {W - LY - RING_IN - TICK_L - 3.5:.0f}')
    for nm, (bx, by) in (('左上角框臂端', (BR + BR_L, BR)), ('左上角框臂端(直)', (BR, BR + BR_L)), ('右上角框臂端', (W - BR - BR_L, BR)), ('右上角框臂端(直)', (W - BR, BR + BR_L)), ('左下角框臂端', (BR + BR_L, W - BR)), ('左下角框臂端(直)', (BR, W - BR - BR_L))):
        print(f'  {nm} 距刻度環外緣 {math.hypot(bx - LX, by - LY) - RING_IN - TICK_L - BR_W/2 - 3.5:.0f}')


def render_png():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('沒有 Playwright，略過 PNG'); return
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        pg = b.new_page(viewport={'width': 1024, 'height': 1024})
        pg.goto('file://' + os.path.join(HERE, 'icon_full_light.svg')); pg.wait_for_timeout(300)
        pg.evaluate("document.documentElement.setAttribute('width','1024');document.documentElement.setAttribute('height','1024')")
        pg.wait_for_timeout(100)
        pg.screenshot(path=os.path.join(HERE, 'icon_full_light.png'), clip={'x': 0, 'y': 0, 'width': 1024, 'height': 1024})
        b.close()


def main():
    open(os.path.join(HERE, 'icon_full_light.svg'), 'w').write(icon())
    check()
    render_png()


if __name__ == '__main__':
    main()
