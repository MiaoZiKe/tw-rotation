# 第十七輪〈股立方〉：立方轉正；六角外框改成跟內部 Y 稜同一套白色筆觸；刻度圈＝放大鏡的鏡片圈，
# 外緣一條連續圓當鏡框，把手是同色的實心圓角粗線，從圓的 45° 處往右下伸；立方滿版塞進圈內。
# Andy 第十七輪：「幫我把立方體轉回來好了，另外放大鏡邊框跟立方體內部線條風格一樣，且把手風格跟圓圈線條一樣
#                 並且位置不變但銜接到圓圈邊緣上，因為目前的圓圈會影響把手大小，所以可以適當把圓圈調小一點，
#                 但立方體大小需要滿版在圓圈內」
# 只交滿版圖示：icon_full_light.svg／.png（1024×1024）。執行：python docs/brand/v17/_gen.py
import math, os, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location('v16', os.path.join(HERE, '..', 'v16', '_gen.py'))
v16 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(v16)   # v16 → v15 → v14 → v13，都只載入函式
Cube, pts, shrink, hexagon, glyph, place = v16.Cube, v16.pts, v16.shrink, v16.hexagon, v16.glyph, v16.place
FRONT, BACK = v16.FRONT, v16.BACK   # 上＝基本、左＝技術、右＝產業；背面：左上＝籌碼、右上＝資金、底＝事件（配色同 v15）

# ---------- 規格（512 畫布；PNG 輸出 1024 = 2 倍）----------
W = 512
LX, LY = 238, 234          # 圓心＝立方中心：比 v16（252,246）往左上挪，讓 45° 把手放得下
RC = 192                   # 鏡片圈（連續圓）中心線半徑；v16 刻度環外緣是 212，這裡縮小
RING_W = 7                 # 圓圈線寬＝粗刻度的線寬
TICK_L, TICK_S = 11, 6     # 刻度在圈內側：長刻度 11、短刻度 6（比 v16 的 16／9 短，免得撞立方頂點）
TICK_OUT = RC - RING_W/2   # 刻度從圓圈內緣往內畫
GAP = 8                    # 立方外輪廓（含白線半寬）到長刻度內端的留白
OUT_W = 10                 # 六角外輪廓白線寬（Y 稜是 7，外輪廓略粗）
EDGE = 1.6                 # 白線兩側的淡藍細描邊寬（每側）
R = TICK_OUT - TICK_L - GAP - OUT_W/2 - EDGE   # 立方外接半徑：頂點幾乎貼到長刻度內端
HANDLE_ANG = 45
HANDLE_W = 46              # 把手粗（畫布 9%）
HANDLE_END = 300           # 把手末端圓心距圓心（再加半徑 23 是最外點）
BR, BR_L, BR_W = 34, 62, 20   # 角框延用 v16：中心線距邊 34、臂長 62、線寬 20；右下角讓給把手

INK = '#2c4b6c'            # 刻度、圓圈、把手同一個深藍
EDGE_C = '#8fc0e2'         # 白線的淡藍細描邊（跟右側面的陰影 #b4dcf3 同色系、深一階，讓白線在淺底上浮出來）
P = dict(bg0='#ffffff', bg1='#eaf3fa', bracket='#1d3557', hi='#ffffff', lens='#eef7fd',
         top='#eef9fe', left='#cdeaf9', right='#b4dcf3', base='#dcf0fa', face_op=.6, base_op=.95,
         hidden_op=.8, back_op=.5)


def defs(u):
    d = [f'<linearGradient id="{u}bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{P["bg0"]}"/><stop offset="1" stop-color="{P["bg1"]}"/></linearGradient>',
         f'<linearGradient id="{u}glass" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{P["top"]}"/><stop offset=".55" stop-color="{P["base"]}"/><stop offset="1" stop-color="{P["right"]}"/></linearGradient>',
         f'<clipPath id="{u}clip"><polygon points="{pts(hexagon(LX, LY, R))}"/></clipPath>',
         # 只保留圓圈中心線以外的區域：把手的根部在這裡被切齊，接縫剛好被圓圈的線蓋住
         f'<clipPath id="{u}outside"><path clip-rule="evenodd" d="M0 0H{W}V{W}H0Z'
         f'M{LX + RC} {LY}A{RC} {RC} 0 1 0 {LX - RC} {LY}A{RC} {RC} 0 1 0 {LX + RC} {LY}Z"/></clipPath>']
    return '<defs>' + ''.join(d) + '</defs>'


def white_line(d, w, closed=False):
    """立方的稜線筆觸：先一條淡藍細描邊（兩側各 EDGE），再一條白線。內部 Y 稜與六角外輪廓都用這一支，所以是同一套線條"""
    j = 'stroke-linejoin="round"' + ('' if closed else ' stroke-linecap="round"')
    tag = 'polygon points' if closed else 'path d'
    return (f'<{tag}="{d}" fill="none" stroke="{EDGE_C}" stroke-width="{w + 2*EDGE:.1f}" {j}/>'
            f'<{tag}="{d}" fill="none" stroke="{P["hi"]}" stroke-width="{w}" {j}/>')


def cube(cb, u, yw=7, sw=1.5):
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
    # 很淡的平面反光帶，只在左上角
    def band(off, w):
        dx, dy = math.cos(math.radians(-30)), math.sin(math.radians(-30)); nx, ny = -dy, dx
        c0 = (LX - nx*off, LY - ny*off); L = 2*R
        return [(c0[0] - dx*L, c0[1] - dy*L), (c0[0] + dx*L, c0[1] + dy*L), (c0[0] + dx*L + nx*w, c0[1] + dy*L + ny*w), (c0[0] - dx*L + nx*w, c0[1] - dy*L + ny*w)]
    o.append(f'<g clip-path="url(#{u}clip)"><polygon points="{pts(band(R*.84, 14))}" fill="#ffffff" opacity=".4"/>'
             f'<polygon points="{pts(band(R*.68, 5))}" fill="#ffffff" opacity=".3"/></g>')
    for k, fn in FRONT.items():
        o.append(f'<g transform="{place(cb, k, True)}">{glyph(fn, sw)}</g>')
    # 內部 Y 稜與六角外輪廓：同一支 white_line
    y = (f'M{C[0]:.1f} {C[1]:.1f}L{cb.UL[0]:.1f} {cb.UL[1]:.1f}M{C[0]:.1f} {C[1]:.1f}L{cb.UR[0]:.1f} {cb.UR[1]:.1f}'
         f'M{C[0]:.1f} {C[1]:.1f}L{cb.B[0]:.1f} {cb.B[1]:.1f}')
    o.append(white_line(y, yw))
    o.append(white_line(pts(cb.hex), OUT_W, closed=True))
    return ''.join(o)


def lens_ring(u):
    """鏡片圈：淡冰藍鏡片＋外緣一條連續圓＋圈內側的刻度（都用 INK）"""
    thin, thick = [], []
    for i in range(60):
        t = math.radians(6*i); L = TICK_L if i % 5 == 0 else TICK_S
        d = f'M{LX + TICK_OUT*math.cos(t):.1f} {LY + TICK_OUT*math.sin(t):.1f}L{LX + (TICK_OUT - L)*math.cos(t):.1f} {LY + (TICK_OUT - L)*math.sin(t):.1f}'
        (thick if i % 5 == 0 else thin).append(d)
    return (f'<circle cx="{LX}" cy="{LY}" r="{RC}" fill="{P["lens"]}"/>'
            f'<path d="{"".join(thin)}" stroke="{INK}" stroke-width="3.2" stroke-linecap="round" opacity=".8"/>'
            f'<path d="{"".join(thick)}" stroke="{INK}" stroke-width="{RING_W}" stroke-linecap="round"/>'
            f'<circle cx="{LX}" cy="{LY}" r="{RC}" fill="none" stroke="{INK}" stroke-width="{RING_W}"/>')


def handle(u):
    """把手：跟圓圈同色的實心圓角粗線，從圓心沿 45° 畫到末端，再用 clip 切掉圓圈以內的部分 → 根部正好接在圓圈中心線上"""
    a = math.radians(HANDLE_ANG)
    ex, ey = LX + HANDLE_END*math.cos(a), LY + HANDLE_END*math.sin(a)
    return (f'<g clip-path="url(#{u}outside)"><path d="M{LX} {LY}L{ex:.1f} {ey:.1f}" stroke="{INK}" stroke-width="{HANDLE_W}" stroke-linecap="round"/></g>')


def brackets():
    x0 = y0 = BR; x1 = y1 = W - BR; L = BR_L
    d = f'M{x0} {y0 + L}V{y0}H{x0 + L}M{x1 - L} {y0}H{x1}V{y0 + L}M{x0} {y1 - L}V{y1}H{x0 + L}'
    return f'<path d="{d}" fill="none" stroke="{P["bracket"]}" stroke-width="{BR_W}" stroke-linecap="round" stroke-linejoin="round"/>'


def icon(u='f'):
    cb = Cube(LX, LY, R)
    return '\n'.join([f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {W}" width="{W}" height="{W}">', defs(u),
                      f'<rect width="{W}" height="{W}" fill="url(#{u}bg)"/>', brackets(), handle(u), lens_ring(u), cube(cb, u), '</svg>'])


def check():
    a = math.radians(HANDLE_ANG)
    far = HANDLE_END + HANDLE_W/2
    print(f'立方外接半徑 R={R:.1f}；外輪廓白線外緣（含淡藍描邊）{R + OUT_W/2 + EDGE:.1f}，長刻度內端 {TICK_OUT - TICK_L:.1f} → 留白 {TICK_OUT - TICK_L - R - OUT_W/2 - EDGE:.1f}')
    print(f'圓圈中心線 {RC}、外緣 {RC + RING_W/2}；刻度 {TICK_OUT}→{TICK_OUT - TICK_L}（長）／{TICK_OUT - TICK_S}（短）')
    print(f'把手：粗 {HANDLE_W}（{HANDLE_W/W:.1%}）、圓圈外長 {far - RC:.0f}（{(far - RC)/W:.1%}），最外點（1024）{2*(LX + far*math.cos(a)):.0f},{2*(LY + far*math.sin(a)):.0f}')
    print(f'圓圈外緣距畫布：上 {LY - RC - RING_W/2:.1f}、左 {LX - RC - RING_W/2:.1f}、右 {W - LX - RC - RING_W/2:.1f}、下 {W - LY - RC - RING_W/2:.1f}')
    for nm, (bx, by) in (('左上橫臂端', (BR + BR_L, BR)), ('左上直臂端', (BR, BR + BR_L)), ('右上橫臂端', (W - BR - BR_L, BR)),
                         ('右上直臂端', (W - BR, BR + BR_L)), ('左下橫臂端', (BR + BR_L, W - BR)), ('左下直臂端', (BR, W - BR - BR_L))):
        print(f'  {nm} 距圓圈外緣 {math.hypot(bx - LX, by - LY) - RC - RING_W/2 - BR_W/2:.1f}')


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
