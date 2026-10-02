# 第十八輪〈股立方〉：照 Andy 給的三色系參考圖 —— 同一個造型做三種色系
#   科技色系：霓虹紫與電藍／專業色系：優雅海軍藍與青銅／休閒色系：充滿活力珊瑚與綠松石
# 造型：圓潤霧面玻璃立方（端正等角，佔畫面大部分）＋外圈細刻度＋三個角框（右下留給把手）
#       ＋短粗木柄放大鏡把手（接在立方右下頂點附近，往右下 45°，端面看得到年輪）。
# 面上的圖示沿用第十七輪的細節版函式與貼面規則（Cube.matrix，沿該面兩組邊貼）：
#   頂＝產業（晶片）、左＝技術（K 棒，紅漲綠跌）、右＝基本（走勢圖）；背面：左上＝籌碼、右上＝事件、底＝資金（分流圖）
# 執行：python docs/brand/v18/_gen.py → icon_tech／icon_pro／icon_casual 的 .svg＋1024 .png，以及 三色系.png
import math, os, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location('v17', os.path.join(HERE, '..', 'v17', '_gen.py'))
v17 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(v17)   # v17 → v16 → v15 → v14 → v13，都只載入函式
Cube, pts, shrink = v17.Cube, v17.pts, v17.shrink
S3 = math.cos(math.radians(30))
SCRATCH = os.environ.get('BRAND_SCRATCH', '/tmp')   # 總覽頁的暫存 HTML 放這裡（設計美編用 scratchpad）

# ---------- 共同規格（512 畫布；PNG 1024 = 2 倍）----------
W = 512
CX, CY = 248, 246          # 立方中心（參考圖幾乎置中，略往左上給把手位置）
R = 170                    # 立方外接半徑：含外緣寬 2R·cos30°+RIM = 309 ≈ 畫布 60%（參考圖量到 61%）、高 355 ≈ 69%（參考圖 70%）；頂點與刻度內端留 14
RIM = 15                   # 玻璃外緣厚度（圓潤的厚玻璃邊）
RING_R = 214               # 刻度外緣半徑（參考圖刻度環直徑約 84%）
BR, BR_L, BR_W, BR_RAD = 40, 66, 18, 22   # 角框：中心線距邊、臂長、線寬、轉角半徑
HANDLE_ANG = 45
HW = 24                    # 握把半徑（直徑 48 ≈ 畫布 9.4%）
ATTACH = .26               # 把手接點：右下邊上從 LR 頂點往 B 走 26%（緊貼右下頂點）
FER0, FER1 = -6, 20        # 金屬環（局部座標，x 沿把手軸線）
WOOD_END = 118             # 木柄端面中心（＋端面半深 ≈ 圓頭最外點；總長約畫布 25%）

THEMES = {
    'tech': dict(
        name='科技色系：霓虹紫與電藍',
        bg0='#262d3a', bg1='#1b1f26',
        top='#a9d8fb', left='#a68aee', right='#7e6fd8', base0='#b6e3ff', base1='#8a6fe6', face_op=.78,
        rim='#c9b8ff', rim_dark='#5b46b8', hi='#f2f6ff', cube_glow='#9d7bff',
        accent='#c77dff', accent_hi='#f0cfff', glow=True, bracket_metal=None,
        wood=('#0f3d40', '#1f6f70', '#5ab0b1', '#2d8c8c', '#0b2f31'), grain='#0b2a2c', endc=('#6cc3c2', '#2a8686'),
        fer=('#0f3a42', '#2b7d86', '#9fe9ec', '#1e5059'),
        gly=dict(ink='#f6f2ff', acc='#5ff3ff', fill='none', rise='#ff4d6d', fall='#2fe39a', flowline='#5ff3ff',
                 n1='#ff5ccf', n2='#7dffb0', n3='#ffd166', trend='#5ff3ff', area='#5ff3ff', hot='#ff5ccf',
                 chip='#ffd166', chipacc='#ff4d6d', core='#3dd6e0'),
        back_op=.42),
    'pro': dict(
        name='專業色系：優雅海軍藍與青銅',
        bg0='#1c3462', bg1='#13254a',
        top='#f8f2e4', left='#e9dcc6', right='#d6c4a6', base0='#fbf6ea', base1='#d9c8aa', face_op=.88,
        rim='#f1e6d0', rim_dark='#a88b5e', hi='#ffffff', cube_glow=None,
        accent='#b98252', accent_hi='#e7c08a', glow=False, bracket_metal=('#f6e3bb', '#d2a96b', '#8c6034'),
        wood=('#3e2314', '#6b3f26', '#986240', '#7d4a2b', '#2e180c'), grain='#2b160b', endc=('#b07a4e', '#6b3f26'),
        fer=('#5a3b22', '#a97a4f', '#f0d3a2', '#7a5530'),
        gly=dict(ink='#1d2f52', acc='#2c5d9e', fill='none', rise='#d33a4a', fall='#1a8a5c', flowline='#2c5d9e',
                 n1='#c0782f', n2='#2a8f88', n3='#6a5acd', trend='#2c5d9e', area='#2c5d9e', hot='#c0782f',
                 chip='#d9a84e', chipacc='#c0392b', core='#2a8f88'),
        back_op=.4),
    'casual': dict(
        name='休閒色系：充滿活力珊瑚與綠松石',
        bg0='#6b7483', bg1='#5a6270',
        top='#b4ecf2', left='#7cc7d2', right='#5aa9b5', base0='#c8f4f8', base1='#4f9ea9', face_op=.8,
        rim='#d3f6f9', rim_dark='#2e7d88', hi='#ffffff', cube_glow=None,
        accent='#ff7b72', accent_hi='#ffd0cc', glow=True, bracket_metal=None,
        wood=('#a8743f', '#d8a675', '#f0cb9c', '#c38d58', '#8a5a30'), grain='#8f5c33', endc=('#f6d9b2', '#d3a26c'),
        fer=('#8d857a', '#cfc7bc', '#fbf7f0', '#a59d92'),
        gly=dict(ink='#123540', acc='#0f6f8f', fill='none', rise='#e0414f', fall='#12805a', flowline='#0f6f8f',
                 n1='#ff6f61', n2='#ffb347', n3='#7b6cf0', trend='#0f6f8f', area='#0f6f8f', hot='#ff6f61',
                 chip='#ffc857', chipacc='#e0414f', core='#ff8a7a'),
        back_op=.42),
}


def defs(u, T):
    d = [f'<radialGradient id="{u}bg" cx="45%" cy="42%" r="75%"><stop offset="0" stop-color="{T["bg0"]}"/><stop offset="1" stop-color="{T["bg1"]}"/></radialGradient>',
         f'<linearGradient id="{u}glass" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{T["base0"]}"/><stop offset="1" stop-color="{T["base1"]}"/></linearGradient>',
         f'<filter id="{u}glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3.2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>',
         f'<filter id="{u}soft" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="10"/></filter>',
         f'<filter id="{u}blur2" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="2"/></filter>']
    w0, w1, w2, w3, _ = T['wood']
    d.append(f'<linearGradient id="{u}wood" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{w0}"/><stop offset=".25" stop-color="{w1}"/>'
             f'<stop offset=".45" stop-color="{w2}"/><stop offset=".72" stop-color="{w3}"/><stop offset="1" stop-color="{w0}"/></linearGradient>')
    e0, e1 = T['endc']
    d.append(f'<radialGradient id="{u}end" cx="45%" cy="45%" r="60%"><stop offset="0" stop-color="{e0}"/><stop offset="1" stop-color="{e1}"/></radialGradient>')
    f0, f1, f2, f3 = T['fer']
    d.append(f'<linearGradient id="{u}fer" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{f0}"/><stop offset=".3" stop-color="{f1}"/>'
             f'<stop offset=".5" stop-color="{f2}"/><stop offset=".75" stop-color="{f3}"/><stop offset="1" stop-color="{f0}"/></linearGradient>')
    if T['bracket_metal']:
        a, b, c = T['bracket_metal']
        d.append(f'<linearGradient id="{u}brm" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{a}"/><stop offset=".5" stop-color="{b}"/><stop offset="1" stop-color="{c}"/></linearGradient>')
    return '<defs>' + ''.join(d) + '</defs>'


def brackets(u, T):
    """三個角框（左上、右上、左下），圓角粗線；科技／休閒帶發光，專業用青銅金屬漸層（每個角各自一支 path，漸層各自套）"""
    x0 = y0 = BR; x1 = y1 = W - BR; L = BR_L; r = BR_RAD
    segs = [f'M{x0} {y0 + L}V{y0 + r}Q{x0} {y0} {x0 + r} {y0}H{x0 + L}',
            f'M{x1 - L} {y0}H{x1 - r}Q{x1} {y0} {x1} {y0 + r}V{y0 + L}',
            f'M{x0} {y1 - L}V{y1 - r}Q{x0} {y1} {x0 + r} {y1}H{x0 + L}']
    paint = f'url(#{u}brm)' if T['bracket_metal'] else T['accent']
    filt = f' filter="url(#{u}glow)"' if T['glow'] else ''
    o = [f'<path d="{s}" fill="none" stroke="{paint}" stroke-width="{BR_W}" stroke-linecap="round" stroke-linejoin="round"{filt}/>' for s in segs]
    if T['glow']:   # 發光的芯：中間一條較亮的細線，讓霓虹感清楚而不是糊成一團
        o += [f'<path d="{s}" fill="none" stroke="{T["accent_hi"]}" stroke-width="{BR_W*.32:.1f}" stroke-linecap="round" stroke-linejoin="round" opacity=".85"/>' for s in segs]
    else:
        o += [f'<path d="{s}" fill="none" stroke="#fff6e4" stroke-width="2.2" stroke-linecap="round" opacity=".55" transform="translate(-2.5 -2.5)"/>' for s in segs]
    return ''.join(o)


def ring(u, T):
    """外圈細短刻度；每 30° 一根較亮的長刻度（四個正方位再長一點）；把手經過的角度不畫"""
    thin, thick, quad = [], [], []
    for i in range(72):
        a = 5*i
        if 30 <= a <= 60: continue
        t = math.radians(a)
        if a % 90 == 0: L, bucket = 18, quad
        elif a % 30 == 0: L, bucket = 13, thick
        else: L, bucket = 8, thin
        bucket.append(f'M{CX + RING_R*math.cos(t):.1f} {CY + RING_R*math.sin(t):.1f}L{CX + (RING_R - L)*math.cos(t):.1f} {CY + (RING_R - L)*math.sin(t):.1f}')
    filt = f' filter="url(#{u}glow)"' if T['glow'] else ''
    return (f'<path d="{"".join(thin)}" stroke="{T["accent"]}" stroke-width="2.6" stroke-linecap="round" opacity=".7"/>'
            f'<path d="{"".join(thick)}" stroke="{T["accent"]}" stroke-width="5" stroke-linecap="round"{filt}/>'
            f'<path d="{"".join(quad)}" stroke="{T["accent"]}" stroke-width="6" stroke-linecap="round"{filt}/>'
            f'<path d="{"".join(quad + thick)}" stroke="{T["accent_hi"]}" stroke-width="2" stroke-linecap="round" opacity=".8"/>')


def set_glyph_palette(T):
    """第十七輪的細節版函式讀 v17 模組裡的 GLY／NAVY；這裡換成該色系的配色再呼叫（紅漲綠跌三種都保留）"""
    v17.GLY = T['gly']; v17.NAVY = T['gly']['ink']


def cube(u, T):
    cb = Cube(CX, CY, R)
    C = cb.C
    set_glyph_palette(T)
    o = []
    if T['cube_glow']:
        o.append(f'<polygon points="{pts(cb.hex)}" fill="{T["cube_glow"]}" opacity=".45" filter="url(#{u}soft)"/>')
    else:
        o.append(f'<polygon points="{pts([(x + 6, y + 12) for x, y in cb.hex])}" fill="#000000" opacity=".28" filter="url(#{u}soft)"/>')   # 落影
    o.append(f'<polygon points="{pts(cb.hex)}" fill="url(#{u}glass)" stroke="url(#{u}glass)" stroke-width="{RIM}" stroke-linejoin="round"/>')
    for k, fn in v17.BACK.items():
        o.append(f'<g opacity="{T["back_op"]}" transform="{v17.place(cb, k, False)}">{v17.glyph(fn, u + k)}</g>')
    o.append(f'<path d="M{C[0]} {C[1]}L{cb.T[0]:.1f} {cb.T[1]:.1f}M{C[0]} {C[1]}L{cb.LL[0]:.1f} {cb.LL[1]:.1f}M{C[0]} {C[1]}L{cb.LR[0]:.1f} {cb.LR[1]:.1f}" '
             f'stroke="{T["hi"]}" stroke-width="2.4" stroke-opacity=".55" stroke-linecap="round"/>')
    for k in ('top', 'left', 'right'):
        q = cb.quad(k)
        o.append(f'<polygon points="{pts(q)}" fill="{T[k]}" fill-opacity="{T["face_op"]}" stroke="{T[k]}" stroke-opacity="{T["face_op"]}" stroke-width="{RIM*.6:.1f}" stroke-linejoin="round"/>')
        cen = (sum(x for x, _ in q)/4, sum(y for _, y in q)/4)
        o.append(f'<polygon points="{pts(shrink(q, cen, .9))}" fill="none" stroke="{T["hi"]}" stroke-opacity=".55" stroke-width="2.2" stroke-linejoin="round"/>')   # 內緣亮邊
    # 頂面光澤
    tq = cb.quad('top'); tc = (sum(x for x, _ in tq)/4, sum(y for _, y in tq)/4)
    o.append(f'<polygon points="{pts(shrink([tq[0], tq[1], ((tq[1][0] + tq[2][0])/2, (tq[1][1] + tq[2][1])/2), ((tq[0][0] + tq[3][0])/2, (tq[0][1] + tq[3][1])/2)], tc, .9))}" fill="#ffffff" opacity=".16"/>')
    for k, fn in v17.FRONT.items():
        o.append(f'<g transform="{v17.place(cb, k, True)}">{v17.glyph(fn, u + k)}</g>')
    # 前面 Y 稜：柔和的寬光暈＋亮線（圓潤玻璃稜）
    y = f'M{C[0]} {C[1]}L{cb.UL[0]:.1f} {cb.UL[1]:.1f}M{C[0]} {C[1]}L{cb.UR[0]:.1f} {cb.UR[1]:.1f}M{C[0]} {C[1]}L{cb.B[0]:.1f} {cb.B[1]:.1f}'
    o.append(f'<path d="{y}" stroke="{T["hi"]}" stroke-width="11" stroke-opacity=".28" stroke-linecap="round" filter="url(#{u}blur2)"/>')
    o.append(f'<path d="{y}" stroke="{T["hi"]}" stroke-width="4.2" stroke-opacity=".92" stroke-linecap="round"/>')
    # 厚玻璃外緣：外側深一階的細輪廓、緣本體、內側亮線
    o.append(f'<polygon points="{pts(cb.hex)}" fill="none" stroke="{T["rim_dark"]}" stroke-width="{RIM + 4}" stroke-linejoin="round" opacity=".55"/>')
    o.append(f'<polygon points="{pts(cb.hex)}" fill="none" stroke="{T["rim"]}" stroke-width="{RIM}" stroke-linejoin="round" opacity=".9"/>')
    o.append(f'<polygon points="{pts(shrink(cb.hex, C, 1 - (RIM*.5 + 2)/R))}" fill="none" stroke="{T["hi"]}" stroke-width="2.6" stroke-linejoin="round" opacity=".85"/>')
    o.append(f'<polygon points="{pts(shrink(cb.hex, C, 1 + (RIM*.15)/R))}" fill="none" stroke="#ffffff" stroke-width="1.6" stroke-linejoin="round" opacity=".45"/>')
    return ''.join(o), cb


def handle(u, T, cb):
    """短粗木柄：根部一小段鏡框圈＋金屬環，木柄有木紋與一圈溝，端面是看得到年輪的橢圓"""
    LR, B = cb.LR, cb.B
    px, py = LR[0] + (B[0] - LR[0])*ATTACH, LR[1] + (B[1] - LR[1])*ATTACH
    x0, x1 = FER1 - 2, WOOD_END
    ery = HW; erx = HW*.42                        # 端面橢圓（沿軸線方向被壓扁）
    body = f'M{x0} {-HW}H{x1}V{HW}H{x0}Z'
    grain = (f'M{x0 + 3} {-HW*.55:.1f}C{x0 + 26} {-HW*.9:.1f} {x0 + 46} {-HW*.2:.1f} {x0 + 70} {-HW*.55:.1f}S{x1 - 8} {-HW*.7:.1f} {x1 + 2} {-HW*.4:.1f}'
             f'M{x0 + 5} {HW*.38:.1f}C{x0 + 24} {HW*.12:.1f} {x0 + 44} {HW*.72:.1f} {x0 + 66} {HW*.42:.1f}S{x1 - 10} {HW*.2:.1f} {x1 + 2} {HW*.6:.1f}'
             f'M{x0 + 12} {-HW*.08:.1f}C{x0 + 34} {-HW*.32:.1f} {x0 + 54} {HW*.18:.1f} {x1 - 6} {-HW*.05:.1f}')
    knot = f'<ellipse cx="{x0 + 46}" cy="{HW*.18:.1f}" rx="11" ry="{HW*.3:.1f}"/><ellipse cx="{x0 + 46}" cy="{HW*.18:.1f}" rx="5" ry="{HW*.13:.1f}"/>'
    groove = x1 - 15
    rings = ''.join(f'<ellipse cx="{x1 + erx*.1:.1f}" cy="0" rx="{erx*f:.1f}" ry="{ery*f:.1f}"/>' for f in (.78, .56, .34))
    _, _, _, _, gdark = T['wood']
    return (f'<g transform="translate({px:.2f} {py:.2f}) rotate({HANDLE_ANG})">'
            f'<clipPath id="{u}wc"><path d="{body}"/></clipPath>'
            f'<path d="{body}" fill="url(#{u}wood)"/>'
            f'<g clip-path="url(#{u}wc)" fill="none" stroke="{T["grain"]}" stroke-width="2.2" stroke-linecap="round" opacity=".7"><path d="{grain}"/>{knot}</g>'
            f'<path d="M{x0 + 6} {-HW*.48:.1f}H{groove - 8}" stroke="#ffffff" stroke-width="4" stroke-linecap="round" opacity=".22"/>'
            f'<path d="M{groove} {-HW}A{HW*.36:.1f} {HW} 0 0 1 {groove} {HW}" fill="none" stroke="{gdark}" stroke-width="3"/>'
            f'<path d="{body}" fill="none" stroke="{gdark}" stroke-width="2.6"/>'
            # 端面（圓頭的平切面）：淺色木頭＋三圈年輪＋中心點
            f'<ellipse cx="{x1}" cy="0" rx="{erx:.1f}" ry="{ery}" fill="url(#{u}end)" stroke="{gdark}" stroke-width="2.6"/>'
            f'<g fill="none" stroke="{T["grain"]}" stroke-width="1.5" opacity=".75">{rings}</g>'
            f'<circle cx="{x1 + erx*.12:.1f}" cy="0" r="1.6" fill="{T["grain"]}"/>'
            # 根部：一小段鏡框圈（短的厚圈）＋金屬環
            f'<ellipse cx="{FER0 + 3}" cy="0" rx="7" ry="{HW*1.05:.1f}" fill="url(#{u}fer)" stroke="{T["fer"][0]}" stroke-width="2"/>'
            f'<rect x="{FER0 + 3}" y="{-HW*.82:.1f}" width="{FER1 - FER0 - 3}" height="{HW*1.64:.1f}" rx="5" fill="url(#{u}fer)" stroke="{T["fer"][0]}" stroke-width="2"/>'
            f'<path d="M{FER0 + 11} {-HW*.82:.1f}V{HW*.82:.1f}M{FER1 - 5} {-HW*.82:.1f}V{HW*.82:.1f}" stroke="{T["fer"][0]}" stroke-width="1.6" opacity=".7"/>'
            f'</g>'), (px, py)


def icon(key):
    T = THEMES[key]; u = key[0]
    cube_svg, cb = cube(u, T)
    h, root = handle(u, T, cb)
    svg = '\n'.join([f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {W}" width="{W}" height="{W}">', defs(u, T),
                     f'<rect width="{W}" height="{W}" fill="url(#{u}bg)"/>', ring(u, T), brackets(u, T), cube_svg, h, '</svg>'])
    return svg, cb, root


def check(cb, root):
    a = math.radians(HANDLE_ANG)
    tip = (root[0] + (WOOD_END + HW*.42)*math.cos(a), root[1] + (WOOD_END + HW*.42)*math.sin(a))
    side = [(tip[0] - HW*math.sin(a) - HW*.42*math.cos(a), tip[1] + HW*math.cos(a)), (tip[0] + HW*math.sin(a), tip[1] - HW*math.cos(a))]
    print(f'  立方寬 {2*R*S3 + RIM:.0f}（{(2*R*S3 + RIM)/W:.0%}）、高 {2*R + RIM:.0f}（{(2*R + RIM)/W:.0%}）；把手接點 {root[0]:.1f},{root[1]:.1f}（右下頂點 LR {cb.LR[0]:.1f},{cb.LR[1]:.1f}）')
    print(f'  把手：軸線 {HANDLE_ANG}°、粗 {2*HW}（{2*HW/W:.1%}）、從接點到端面最外 {WOOD_END + HW*.42 - FER0:.0f}（{(WOOD_END + HW*.42 - FER0)/W:.1%}）；端面最外點（1024）{tip[0]*2:.0f},{tip[1]*2:.0f}，側緣 ' + '、'.join(f'{x*2:.0f},{y*2:.0f}' for x, y in side))
    print(f'  刻度外緣：上 {CY - RING_R:.0f}、左 {CX - RING_R:.0f}、右 {W - CX - RING_R:.0f}、下 {W - CY - RING_R:.0f}；立方外緣頂點半徑 {R + RIM/2 + 2:.0f} ↔ 刻度內端（最長 18）{RING_R - 18}')


def render(names):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('沒有 Playwright，略過 PNG'); return
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        pg = b.new_page(viewport={'width': 1024, 'height': 1024})
        for n in names:
            pg.goto('file://' + os.path.join(HERE, n + '.svg')); pg.wait_for_timeout(300)
            pg.evaluate("document.documentElement.setAttribute('width','1024');document.documentElement.setAttribute('height','1024')")
            pg.wait_for_timeout(100)
            pg.screenshot(path=os.path.join(HERE, n + '.png'), clip={'x': 0, 'y': 0, 'width': 1024, 'height': 1024})
        # 三色系總覽：三張並排，下面寫色系名稱（每欄底色照各色系）
        cols = ''.join(f'<div class="c" style="background:{THEMES[k]["bg1"]}"><img src="file://{HERE}/icon_{k}.svg"><p>{THEMES[k]["name"].replace("：", "：<br>")}</p></div>' for k in ('tech', 'pro', 'casual'))
        html = (f'<!doctype html><html><head><meta charset="utf-8"><style>body{{margin:0;width:1800px;display:flex;font-family:"WenQuanYi Zen Hei",sans-serif}}'
                f'.c{{width:600px;display:flex;flex-direction:column;align-items:center;padding:0 0 40px}}.c img{{width:600px;height:600px}}'
                f'.c p{{margin:18px 0 0;color:#ffffff;font-size:40px;font-weight:700;-webkit-text-stroke:1px #ffffff;line-height:1.35;text-align:center;letter-spacing:.06em}}</style></head><body>{cols}</body></html>')
        tmp = os.path.join(SCRATCH, '_v18_sheet.html')   # 中間檔不留在 repo
        open(tmp, 'w').write(html)
        pg.set_viewport_size({'width': 1800, 'height': 1000})
        pg.goto('file://' + tmp); pg.wait_for_timeout(600)
        h = int(pg.evaluate("Math.ceil(Math.max(...[...document.querySelectorAll('.c')].map(e => e.getBoundingClientRect().bottom)))"))
        pg.screenshot(path=os.path.join(HERE, '三色系.png'), clip={'x': 0, 'y': 0, 'width': 1800, 'height': h})
        b.close()


def main():
    names = []
    for k in ('tech', 'pro', 'casual'):
        svg, cb, root = icon(k)
        open(os.path.join(HERE, f'icon_{k}.svg'), 'w').write(svg)
        print(THEMES[k]['name']); check(cb, root)
        names.append(f'icon_{k}')
    render(names)


if __name__ == '__main__':
    main()
