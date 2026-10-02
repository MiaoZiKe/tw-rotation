# 第十九輪〈股立方〉：白底，五種風格（科技／專業／HUD 透明／休閒／黑白），同一個造型。
# Andy 第十九輪：「這風格把手好醜，風格符合點立方體，並且位置調整，符合現實中正確位置，幫我在做一個白底，
#                 並且需要 科技 專業 HUD透明 休閒 並且黑白頁面的風格」
# 改動重點：
#   1. 把手不用木頭，改成跟立方同一套材質（同色系霧面玻璃柄＋同樣的外緣亮線與深一階細輪廓、圓角端頭），
#      根部用跟立方外框同材質的環扣接上。
#   2. 位置照真實放大鏡：把手沿鏡片半徑方向伸出 —— 從右下邊（30° 頂點 → 90° 頂點）中點、沿 60° 往外，
#      軸線延長會通過六角形中心，也垂直於那條邊；立方端正不轉。
#   3. 全部白底。面的配置、細節圖示、貼面規則沿用第十七輪（頂＝產業、左＝技術、右＝基本；背面：左上＝籌碼、右上＝事件、底＝資金）。
# 執行：BRAND_SCRATCH=<暫存資料夾> python docs/brand/v19/_gen.py
import math, os, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location('v18', os.path.join(HERE, '..', 'v18', '_gen.py'))
v18 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(v18)   # v18 → v17 → … 都只載入函式
v17 = v18.v17
Cube, pts, shrink = v17.Cube, v17.pts, v17.shrink
S3 = math.cos(math.radians(30))
SCRATCH = os.environ.get('BRAND_SCRATCH', '/tmp')

# ---------- 共同規格（512 畫布；PNG 1024 = 2 倍）----------
W = 512
CX, CY = 248, 232          # 立方（鏡片）中心：往左上，讓 60° 的把手放得下
R = 160                    # 立方外接半徑（含外緣寬 2R·cos30°+RIM ≈ 291 ≈ 畫布 57%）
RIM = 13                   # 立方玻璃外緣厚度
RING_R = 202               # 刻度外緣半徑
HANDLE_ANG = 60            # 從中心往外的半徑方向，同時垂直於右下邊
HW = 22                    # 握把半徑（直徑 44 ≈ 畫布 8.6%）
COL0, COL1 = -7, 23        # 環扣（局部座標：0＝右下邊中點、x 沿把手往外）
H_END = 124                # 握把末端（圓頭最外點）距右下邊中點：≈ 畫布 24%
BR, BR_L, BR_W, BR_RAD = 40, 62, 16, 20   # 角框

THEMES = {
    'tech': dict(name='科技', top='#c9e4ff', left='#b7a2f5', right='#9785ea', base0='#d6ecff', base1='#9b84ee', face_op=.8,
                 rim='#d9ccff', rim_dark='#5b3fc4', hi='#ffffff', accent='#8b5cf6', accent_hi='#c9a8ff', accent_dark='#5b3fc4',
                 halo=True, metal=None, shadow='#5b3fc4',
                 gly=dict(ink='#24124f', acc='#2f7cf6', fill='none', rise='#e5384f', fall='#0f9d68', flowline='#2f7cf6',
                          n1='#e84bb5', n2='#14b8a6', n3='#f59e0b', trend='#2f7cf6', area='#2f7cf6', hot='#e84bb5',
                          chip='#f5b83d', chipacc='#e5384f', core='#22c3d6'), back_op=.38),
    'pro': dict(name='專業', top='#fbf6ea', left='#efe3cc', right='#e0cdaa', base0='#fdf9f0', base1='#e3d2b2', face_op=.9,
                rim='#f4ead6', rim_dark='#1d2f52', hi='#ffffff', accent='#a8743f', accent_hi='#e3bd84', accent_dark='#7a5530',
                halo=False, metal=('#f3dcb0', '#c8995c', '#8c6034'), shadow='#1d2f52',
                gly=dict(ink='#1d2f52', acc='#2c5d9e', fill='none', rise='#d33a4a', fall='#1a8a5c', flowline='#2c5d9e',
                         n1='#c0782f', n2='#2a8f88', n3='#6a5acd', trend='#2c5d9e', area='#2c5d9e', hot='#c0782f',
                         chip='#d9a84e', chipacc='#c0392b', core='#2a8f88'), back_op=.36),
    'hud': dict(name='HUD 透明', top='#e8f7ff', left='#e2f4fd', right='#d9f0fb', base0='#f2fbff', base1='#dff3fc', face_op=.35,
                rim='#00a6d6', rim_dark='#00a6d6', hi='#ffffff', accent='#00a6d6', accent_hi='#7fdcf5', accent_dark='#007ea6',
                halo=False, metal=None, shadow=None, hud=True,
                gly=dict(ink='#0086b3', acc='#00a6d6', fill='none', rise='#e5384f', fall='#0f9d68', flowline='#00a6d6',
                         n1='#ff7a59', n2='#00b894', n3='#6c5ce7', trend='#00a6d6', area='#00a6d6', hot='#ff7a59',
                         chip='#9adcf0', chipacc='#ff7a59', core='#7fdcf5'), back_op=.45),
    'casual': dict(name='休閒', top='#c6f1f5', left='#8fd3dc', right='#68b9c4', base0='#d6f6f9', base1='#5fb0bb', face_op=.85,
                   rim='#dcf8fa', rim_dark='#1f7480', hi='#ffffff', accent='#ff6f61', accent_hi='#ffc1bb', accent_dark='#d9483b',
                   halo=True, metal=None, shadow='#1f7480',
                   gly=dict(ink='#123540', acc='#0f6f8f', fill='none', rise='#e0414f', fall='#12805a', flowline='#0f6f8f',
                            n1='#ff6f61', n2='#ffb347', n3='#7b6cf0', trend='#0f6f8f', area='#0f6f8f', hot='#ff6f61',
                            chip='#ffc857', chipacc='#e0414f', core='#ff8a7a'), back_op=.4),
    # 黑白：一個彩色都不准有。K 棒的漲跌改用「空心＝漲、實心＝跌」（rise 與 fall 同為黑，細節版 candle_d 本來就是漲空心、跌實心）
    'mono': dict(name='黑白', top='#f5f5f5', left='#e4e4e4', right='#d0d0d0', base0='#f7f7f7', base1='#cfcfcf', face_op=.92,
                 rim='#ffffff', rim_dark='#111111', hi='#ffffff', accent='#222222', accent_hi='#888888', accent_dark='#000000',
                 halo=False, metal=None, shadow='#000000',
                 gly=dict(ink='#111111', acc='#444444', fill='none', rise='#111111', fall='#111111', flowline='#333333',
                          n1='#111111', n2='#555555', n3='#888888', trend='#222222', area='#444444', hot='#111111',
                          chip='#bdbdbd', chipacc='#111111', core='#9a9a9a'), back_op=.32),
}
ORDER = ('tech', 'pro', 'hud', 'casual', 'mono')


def defs(u, T):
    d = [f'<linearGradient id="{u}glass" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{T["base0"]}"/><stop offset="1" stop-color="{T["base1"]}"/></linearGradient>',
         # 把手的玻璃：截面方向漸層（同一組玻璃色），中間一道亮
         f'<linearGradient id="{u}hg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{T["base1"]}"/><stop offset=".38" stop-color="{T["base0"]}"/>'
         f'<stop offset=".55" stop-color="{T["top"]}"/><stop offset="1" stop-color="{T["right"]}"/></linearGradient>',
         f'<linearGradient id="{u}cg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{T["rim_dark"]}"/><stop offset=".35" stop-color="{T["rim"]}"/>'
         f'<stop offset=".55" stop-color="#ffffff"/><stop offset="1" stop-color="{T["rim_dark"]}"/></linearGradient>',
         f'<filter id="{u}halo" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="3"/></filter>',
         f'<filter id="{u}soft" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="9"/></filter>',
         f'<filter id="{u}blur2" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="2"/></filter>']
    if T['metal']:
        a, b, c = T['metal']
        d.append(f'<linearGradient id="{u}brm" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{a}"/><stop offset=".5" stop-color="{b}"/><stop offset="1" stop-color="{c}"/></linearGradient>')
    return '<defs>' + ''.join(d) + '</defs>'


def brackets(u, T, corners):
    x0 = y0 = BR; x1 = y1 = W - BR; L = BR_L; r = BR_RAD
    seg = {'tl': f'M{x0} {y0 + L}V{y0 + r}Q{x0} {y0} {x0 + r} {y0}H{x0 + L}',
           'tr': f'M{x1 - L} {y0}H{x1 - r}Q{x1} {y0} {x1} {y0 + r}V{y0 + L}',
           'bl': f'M{x0} {y1 - L}V{y1 - r}Q{x0} {y1} {x0 + r} {y1}H{x0 + L}',
           'br': f'M{x1} {y1 - L}V{y1 - r}Q{x1} {y1} {x1 - r} {y1}H{x1 - L}'}
    o = []
    for c in corners:
        s = seg[c]
        if T.get('hud'):   # HUD：細線角框＋端點小方塊
            o.append(f'<path d="{s}" fill="none" stroke="{T["accent"]}" stroke-width="4" stroke-linecap="square"/>')
            continue
        if T['halo']:      # 白底上的發光收斂成「淡光暈」：一條模糊的淺色粗線墊在底下
            o.append(f'<path d="{s}" fill="none" stroke="{T["accent_hi"]}" stroke-width="{BR_W + 8}" stroke-linecap="round" opacity=".55" filter="url(#{u}halo)"/>')
        paint = f'url(#{u}brm)' if T['metal'] else T['accent']
        o.append(f'<path d="{s}" fill="none" stroke="{T["accent_dark"]}" stroke-width="{BR_W + 3}" stroke-linecap="round" stroke-linejoin="round"/>')   # 描邊
        o.append(f'<path d="{s}" fill="none" stroke="{paint}" stroke-width="{BR_W}" stroke-linecap="round" stroke-linejoin="round"/>')
        o.append(f'<path d="{s}" fill="none" stroke="#ffffff" stroke-width="2.2" stroke-linecap="round" opacity=".55" transform="translate(-2.4 -2.4)"/>')
    return ''.join(o)


def ring(u, T, skip):
    thin, thick, quad = [], [], []
    for i in range(72):
        a = 5*i
        if skip[0] <= a <= skip[1]: continue
        t = math.radians(a)
        if a % 90 == 0: L, b = 16, quad
        elif a % 30 == 0: L, b = 12, thick
        else: L, b = 7, thin
        b.append(f'M{CX + RING_R*math.cos(t):.1f} {CY + RING_R*math.sin(t):.1f}L{CX + (RING_R - L)*math.cos(t):.1f} {CY + (RING_R - L)*math.sin(t):.1f}')
    hud = T.get('hud')
    o = [f'<path d="{"".join(thin)}" stroke="{T["accent"]}" stroke-width="{1.6 if hud else 2.4}" stroke-linecap="round" opacity=".75"/>',
         f'<path d="{"".join(thick)}" stroke="{T["accent"]}" stroke-width="{2.4 if hud else 4.6}" stroke-linecap="round"/>',
         f'<path d="{"".join(quad)}" stroke="{T["accent_dark"] if not hud else T["accent"]}" stroke-width="{2.6 if hud else 5.6}" stroke-linecap="round"/>']
    if T['halo']:
        o.insert(0, f'<path d="{"".join(quad + thick)}" stroke="{T["accent_hi"]}" stroke-width="10" stroke-linecap="round" opacity=".5" filter="url(#{u}halo)"/>')
    if hud:   # HUD：外圈一條細圓、四個方位的準星與刻度數字
        o.append(f'<circle cx="{CX}" cy="{CY}" r="{RING_R + 5}" fill="none" stroke="{T["accent"]}" stroke-width="1" opacity=".55" stroke-dasharray="2 4"/>')
        for a, lab in ((0, '090'), (90, '180'), (180, '270'), (270, '000')):
            t = math.radians(a); x, y = CX + (RING_R + 13)*math.cos(t), CY + (RING_R + 13)*math.sin(t)
            o.append(f'<path d="M{x - 4:.1f} {y:.1f}H{x + 4:.1f}M{x:.1f} {y - 4:.1f}V{y + 4:.1f}" stroke="{T["accent"]}" stroke-width="1.4"/>')
            tx, ty = CX + (RING_R - 26)*math.cos(t), CY + (RING_R - 26)*math.sin(t) + 3
            if a in (0, 180):
                ty = CY - 8
            o.append(f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="middle" font-family="DejaVu Sans Mono" font-size="8.5" fill="{T["accent_dark"]}">{lab}</text>')
    return ''.join(o)


def cube(u, T):
    cb = Cube(CX, CY, R); C = cb.C
    v18.set_glyph_palette(T)
    hud = T.get('hud')
    o = []
    if T['shadow']:
        o.append(f'<polygon points="{pts([(x + 4, y + 14) for x, y in cb.hex])}" fill="{T["shadow"]}" opacity=".16" filter="url(#{u}soft)"/>')
    o.append(f'<polygon points="{pts(cb.hex)}" fill="url(#{u}glass)" fill-opacity="{.25 if hud else 1}" stroke="url(#{u}glass)" stroke-opacity="{0 if hud else 1}" stroke-width="{RIM}" stroke-linejoin="round"/>')
    for k, fn in v17.BACK.items():
        o.append(f'<g opacity="{T["back_op"]}" transform="{v17.place(cb, k, False)}">{v17.glyph(fn, u + k)}</g>')
    hidden = f'M{C[0]} {C[1]}L{cb.T[0]:.1f} {cb.T[1]:.1f}M{C[0]} {C[1]}L{cb.LL[0]:.1f} {cb.LL[1]:.1f}M{C[0]} {C[1]}L{cb.LR[0]:.1f} {cb.LR[1]:.1f}'
    if hud:   # HUD：看不見的三條稜用虛線
        o.append(f'<path d="{hidden}" stroke="{T["rim"]}" stroke-width="2" stroke-dasharray="6 5" stroke-linecap="round" opacity=".8"/>')
    else:
        o.append(f'<path d="{hidden}" stroke="{T["hi"]}" stroke-width="2.4" stroke-opacity=".6" stroke-linecap="round"/>')
    for k in ('top', 'left', 'right'):
        q = cb.quad(k)
        o.append(f'<polygon points="{pts(q)}" fill="{T[k]}" fill-opacity="{T["face_op"]}"/>')
        if not hud:
            cen = (sum(x for x, _ in q)/4, sum(y for _, y in q)/4)
            o.append(f'<polygon points="{pts(shrink(q, cen, .9))}" fill="none" stroke="{T["hi"]}" stroke-opacity=".6" stroke-width="2" stroke-linejoin="round"/>')
    if not hud:
        tq = cb.quad('top'); tc = (sum(x for x, _ in tq)/4, sum(y for _, y in tq)/4)
        o.append(f'<polygon points="{pts(shrink([tq[0], tq[1], ((tq[1][0] + tq[2][0])/2, (tq[1][1] + tq[2][1])/2), ((tq[0][0] + tq[3][0])/2, (tq[0][1] + tq[3][1])/2)], tc, .9))}" fill="#ffffff" opacity=".22"/>')
    for k, fn in v17.FRONT.items():
        o.append(f'<g transform="{v17.place(cb, k, True)}">{v17.glyph(fn, u + k)}</g>')
    y = f'M{C[0]} {C[1]}L{cb.UL[0]:.1f} {cb.UL[1]:.1f}M{C[0]} {C[1]}L{cb.UR[0]:.1f} {cb.UR[1]:.1f}M{C[0]} {C[1]}L{cb.B[0]:.1f} {cb.B[1]:.1f}'
    if hud:
        o.append(f'<path d="{y}" stroke="{T["rim"]}" stroke-width="2.6" stroke-linecap="round"/>')
        o.append(f'<polygon points="{pts(cb.hex)}" fill="none" stroke="{T["rim"]}" stroke-width="3" stroke-linejoin="round"/>')
        o += [f'<circle cx="{x:.1f}" cy="{yy:.1f}" r="3.2" fill="#ffffff" stroke="{T["rim"]}" stroke-width="1.6"/>' for x, yy in cb.hex + [C]]   # 頂點標記
    else:
        o.append(f'<path d="{y}" stroke="{T["rim_dark"]}" stroke-width="6.4" stroke-opacity=".3" stroke-linecap="round"/>')
        o.append(f'<path d="{y}" stroke="{T["hi"]}" stroke-width="4.2" stroke-opacity=".95" stroke-linecap="round"/>')
        o += rim_layers(f'<polygon points="{pts(cb.hex)}"', T, closed=True, shrink_inner=pts(shrink(cb.hex, C, 1 - (RIM*.5 + 2)/R)))
    return ''.join(o), cb


def rim_layers(tag, T, closed=True, shrink_inner=None):
    """立方與把手共用的外緣做法：深一階的細輪廓 → 緣本體 → 內側亮線（同一套材質語言）"""
    o = [f'{tag} fill="none" stroke="{T["rim_dark"]}" stroke-width="{RIM + 3.4}" stroke-linejoin="round"/>',
         f'{tag} fill="none" stroke="{T["rim"]}" stroke-width="{RIM}" stroke-linejoin="round"/>']
    if shrink_inner:
        o.append(f'<polygon points="{shrink_inner}" fill="none" stroke="{T["hi"]}" stroke-width="2.4" stroke-linejoin="round" opacity=".9"/>')
    return o


def handle(u, T, cb):
    """玻璃柄：跟立方同色系的漸層填色＋同樣的「深一階細輪廓＋內側亮線」，圓角端頭；根部用外框同材質的環扣壓進外框"""
    h = cb.hex
    mx, my = (h[2][0] + h[3][0])/2, (h[2][1] + h[3][1])/2      # 右下邊（LR → B）中點
    x0, x1 = COL1 - 3, H_END                                     # 柄身起點、圓頭最外點
    body = f'M{x0} {-HW}H{x1 - HW}A{HW} {HW} 0 0 1 {x1 - HW} {HW}H{x0}Z'
    inner = f'M{x0 + 3} {-HW + 4}H{x1 - HW}A{HW - 4} {HW - 4} 0 0 1 {x1 - HW} {HW - 4}H{x0 + 3}'
    hud = T.get('hud')
    o = [f'<g transform="translate({mx:.2f} {my:.2f}) rotate({HANDLE_ANG})">']
    if hud:
        o += [f'<path d="{body}" fill="{T["rim"]}" fill-opacity=".07" stroke="{T["rim"]}" stroke-width="3" stroke-linejoin="round"/>',
              f'<path d="M{x0 + 6} 0H{x1 - 8}" stroke="{T["rim"]}" stroke-width="1.4" stroke-dasharray="5 4"/>',
              f'<path d="M{x1 - 26} {-HW}V{HW}" stroke="{T["rim"]}" stroke-width="1.4" opacity=".7"/>',
              f'<rect x="{COL0}" y="{-HW*1.12:.1f}" width="{COL1 - COL0}" height="{HW*2.24:.1f}" rx="4" fill="#ffffff" stroke="{T["rim"]}" stroke-width="3"/>',
              f'<path d="M{COL0 + 8} {-HW*1.12:.1f}V{HW*1.12:.1f}" stroke="{T["rim"]}" stroke-width="1.4"/>']
    else:
        if T['shadow']:
            o.append(f'<path d="{body}" fill="{T["shadow"]}" opacity=".16" filter="url(#{u}soft)" transform="translate(5 6)"/>')
        o += [f'<path d="{body}" fill="url(#{u}hg)"/>',
              f'<path d="M{x0 + 8} {-HW*.42:.1f}H{x1 - HW - 4}" stroke="#ffffff" stroke-width="5" stroke-linecap="round" opacity=".55"/>',   # 玻璃柄的高光
              f'<path d="{inner}" fill="none" stroke="{T["hi"]}" stroke-width="2.2" stroke-linejoin="round" opacity=".85"/>',                  # 內側亮線（同立方）
              f'<path d="{body}" fill="none" stroke="{T["rim_dark"]}" stroke-width="3.4" stroke-linejoin="round"/>',                           # 深一階細輪廓（同立方）
              # 環扣：外框同材質（rim 色＋深輪廓＋白色高光），比柄寬一點，壓在外框上
              f'<rect x="{COL0}" y="{-HW*1.15:.1f}" width="{COL1 - COL0}" height="{HW*2.3:.1f}" rx="7" fill="url(#{u}cg)" stroke="{T["rim_dark"]}" stroke-width="3.4"/>',
              f'<rect x="{COL0 + 4}" y="{-HW*1.15 + 4:.1f}" width="{COL1 - COL0 - 8}" height="{HW*2.3 - 8:.1f}" rx="4" fill="none" stroke="{T["hi"]}" stroke-width="2" opacity=".8"/>']
    o.append('</g>')
    return ''.join(o), (mx, my)


def icon(key, br_corner):
    T = THEMES[key]; u = key[:2]
    cube_svg, cb = cube(u, T)
    h, root = handle(u, T, cb)
    half = math.degrees(math.atan2(HW*1.2 + 6, RING_R - 8))
    corners = ('tl', 'tr', 'bl') + (('br',) if br_corner else ())
    svg = '\n'.join([f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {W}" width="{W}" height="{W}">', defs(u, T),
                     f'<rect width="{W}" height="{W}" fill="#ffffff"/>', ring(u, T, (HANDLE_ANG - half, HANDLE_ANG + half)), brackets(u, T, corners),
                     h, cube_svg, '</svg>'])   # 把手先畫，立方的外框蓋在環扣上半段 → 看起來是壓進外框接起來
    return svg, cb, root


def check(cb, root):
    h = cb.hex
    edge = (h[3][0] - h[2][0], h[3][1] - h[2][1]); el = math.hypot(*edge)
    ax = (math.cos(math.radians(HANDLE_ANG)), math.sin(math.radians(HANDLE_ANG)))
    to_c = (CX - root[0], CY - root[1]); tl = math.hypot(*to_c)
    cross = (ax[0]*to_c[1] - ax[1]*to_c[0]) / tl
    tip = (root[0] + ax[0]*H_END, root[1] + ax[1]*H_END)
    sides = [(tip[0] - ax[0]*HW + s*(-ax[1])*HW, tip[1] - ax[1]*HW + s*ax[0]*HW) for s in (-1, 1)]
    print(f'  右下邊中點 {root[0]:.1f},{root[1]:.1f}；把手軸線 {HANDLE_ANG}°；軸線與「中點→中心」的外積 {cross:.1e}（0＝延長線通過中心）；與右下邊內積 {(ax[0]*edge[0] + ax[1]*edge[1])/el:.1e}')
    print(f'  把手：粗 {2*HW}（{2*HW/W:.1%}）、從邊中點到圓頭最外 {H_END}（{H_END/W:.1%}）；環扣從 {COL0} 到 {COL1}（外框半厚 {RIM/2 + 1.7:.1f} → 壓進外框）')
    print(f'  圓頭最外點（1024）{tip[0]*2:.0f},{tip[1]*2:.0f}；圓頭側緣最遠（1024）' + '、'.join(f'{x*2:.0f},{y*2:.0f}' for x, y in sides))
    print(f'  刻度外緣距畫布：上 {CY - RING_R}、左 {CX - RING_R}、右 {W - CX - RING_R}、下 {W - CY - RING_R}')


def render(names):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        pg = b.new_page(viewport={'width': 1024, 'height': 1024})
        for n in names:
            pg.goto('file://' + os.path.join(HERE, n + '.svg')); pg.wait_for_timeout(300)
            pg.evaluate("document.documentElement.setAttribute('width','1024');document.documentElement.setAttribute('height','1024')")
            pg.wait_for_timeout(100)
            pg.screenshot(path=os.path.join(HERE, n + '.png'), clip={'x': 0, 'y': 0, 'width': 1024, 'height': 1024})
        cols = ''.join(f'<div class="c"><img src="file://{HERE}/icon_{k}.svg"><p>{THEMES[k]["name"]}</p></div>' for k in ORDER)
        html = (f'<!doctype html><html><head><meta charset="utf-8"><style>body{{margin:0;width:2000px;display:flex;background:#ffffff;font-family:"WenQuanYi Zen Hei",sans-serif}}'
                f'.c{{width:400px;display:flex;flex-direction:column;align-items:center;padding:0 0 30px;border-right:1px solid #e6e6e6}}.c:last-child{{border-right:0}}.c img{{width:400px;height:400px}}'
                f'.c p{{margin:6px 0 0;color:#111111;font-size:34px;font-weight:700;letter-spacing:.08em}}</style></head><body>{cols}</body></html>')
        tmp = os.path.join(SCRATCH, '_v19_sheet.html'); open(tmp, 'w').write(html)
        pg.set_viewport_size({'width': 2000, 'height': 800})
        pg.goto('file://' + tmp); pg.wait_for_timeout(600)
        hh = int(pg.evaluate("Math.ceil(Math.max(...[...document.querySelectorAll('.c')].map(e => e.getBoundingClientRect().bottom)))"))
        pg.screenshot(path=os.path.join(HERE, '五風格.png'), clip={'x': 0, 'y': 0, 'width': 2000, 'height': hh})
        b.close()


BR_CORNER = True   # 右下角框：把手沿 60° 往下伸，右下角框的橫臂跟圓頭還有距離 → 保留四個角（見 check 的數字）


def main():
    names = []
    for k in ORDER:
        svg, cb, root = icon(k, BR_CORNER)
        open(os.path.join(HERE, f'icon_{k}.svg'), 'w').write(svg)
        print(THEMES[k]['name']); check(cb, root)
        names.append(f'icon_{k}')
    print(f'  右下角框橫臂左端（含圓角端點）x={W - BR - BR_L - BR_W/2:.0f}、y={W - BR:.0f}±{BR_W/2:.0f}')
    render(names)


if __name__ == '__main__':
    main()
