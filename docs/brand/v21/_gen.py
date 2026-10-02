# 第二十一輪〈股立方〉：深色專業版。深海軍藍底＋珍珠霧面立方＋參考圖那種暖桃色刻度圓環與四個圓角角框（柔和外發光）。
# 兩張：icon_dark_pro（柔光，沒有明顯方向）、icon_dark_lit（主光從左上 10～11 點鐘方向打來，有明暗分面、地面投影、受光高光）。
# Andy 第二十一輪：「需要再改成深色專業感覺，並且需要有像這張圖的圓框，再多一個不同角度打光出現陰影的效果」
# 只留立方（延續第二十輪「只留立方」，不加放大鏡把手）。細節圖示與貼面規則沿用第十七輪（經由 v19）。
# 執行：BRAND_SCRATCH=<暫存資料夾> python docs/brand/v21/_gen.py
import math, os, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
SCRATCH = os.environ.get('BRAND_SCRATCH', '/tmp')
_spec = importlib.util.spec_from_file_location('v19', os.path.join(HERE, '..', 'v19', '_gen.py'))
v19 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(v19)
v17, v18 = v19.v17, v19.v18
Cube, pts, shrink = v17.Cube, v17.pts, v17.shrink
S3 = math.cos(math.radians(30))

# ---------- 規格（512 畫布；PNG 1024）。比例量自參考圖 3.png（307×305）----------
W = 512
CX, CY = 256, 250          # 參考圖的立方與圓環幾乎置中
R = 168                    # 立方外接半徑：含外緣寬 2R·cos30°+RIM ≈ 304 ≈ 畫布 59%（參考圖約 55～60%）
RIM = 13
RING_R = 212               # 刻度外緣半徑：直徑 424 ≈ 83%（參考圖約 81%）
BR, BR_L, BR_W, BR_RAD = 60, 54, 15, 18   # 角框：外緣距邊 ≈ 52（參考圖約 11%）、臂長、線寬、轉角半徑

# ---------- 色票 ----------
BG0, BG1 = '#2e3b58', '#1b2540'                 # 背景：中心 → 暗角（參考圖量到中心 #26405b、角落 #1b2f48，這裡偏海軍藍）
PEACH, PEACH_CORE, PEACH_DARK = '#f2b48c', '#ffe1c8', '#c9825a'   # 刻度與角框（參考圖角框平均 #f6d9b5、外圈 #f2b48c）
PEARL = dict(top='#fbf6f3', left='#eee6f1', right='#dfe3f2', base0='#fffaf6', base1='#e2e0f1',
             rim='#fff6f0', rim_soft='#b9bbd8', hi='#ffffff',
             sheen=('#ffd9e6', '#e6dcff', '#d2e6ff'))  # 珍珠光澤：極淡粉 → 薰衣草 → 淡藍
GLY = dict(ink='#1d2f52', acc='#2c5d9e', fill='none', rise='#d33a4a', fall='#1a8a5c', flowline='#2c5d9e',
           n1='#c0782f', n2='#2a8f88', n3='#6a5acd', trend='#2c5d9e', area='#2c5d9e', hot='#d9864f',
           chip='#d9a84e', chipacc='#c0392b', core='#2a8f88')
# 左上打光版：三面依光線重新分配明暗（頂最亮、左次亮、右最暗）
LIT = dict(top='#fffbf6', left='#e2d9ea', right='#a6acc9', base0='#fffaf5', base1='#b8b9d4')


def defs(u, lit):
    P = dict(PEARL, **(LIT if lit else {}))
    a, b, c = P['sheen']
    d = [f'<radialGradient id="{u}bg" cx="48%" cy="44%" r="72%"><stop offset="0" stop-color="{BG0}"/><stop offset="1" stop-color="{BG1}"/></radialGradient>',
         f'<linearGradient id="{u}glass" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{P["base0"]}"/><stop offset="1" stop-color="{P["base1"]}"/></linearGradient>',
         f'<linearGradient id="{u}sheen" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{a}"/><stop offset=".5" stop-color="{b}"/><stop offset="1" stop-color="{c}"/></linearGradient>',
         f'<filter id="{u}glow" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="3.2"/></filter>',
         f'<filter id="{u}soft" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="10"/></filter>',
         f'<filter id="{u}b6" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="6"/></filter>',
         f'<filter id="{u}b2" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="2"/></filter>']
    if lit:
        # 刻度環與角框的受光：左上亮、右下暗（細微）
        d.append(f'<linearGradient id="{u}peach" x1="40" y1="40" x2="472" y2="472" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#ffc9a4"/><stop offset=".55" stop-color="{PEACH}"/><stop offset="1" stop-color="#d48d63"/></linearGradient>')
        # 地面長投影：靠近立方最深、往右下漸淡
        d.append(f'<linearGradient id="{u}cast" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#000208" stop-opacity=".92"/><stop offset=".5" stop-color="#000208" stop-opacity=".5"/><stop offset="1" stop-color="#000208" stop-opacity="0"/></linearGradient>')
        d.append(f'<radialGradient id="{u}trans" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#ffffff" stop-opacity=".55"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient>')
    return '<defs>' + ''.join(d) + '</defs>', P


def peach(u, lit):
    return f'url(#{u}peach)' if lit else PEACH


def ring(u, lit):
    thin, thick, quad = [], [], []
    for i in range(72):
        a = 5*i; t = math.radians(a)
        if a % 90 == 0: L, bk = 18, quad
        elif a % 30 == 0: L, bk = 11, thick
        else: L, bk = 7, thin
        bk.append(f'M{CX + RING_R*math.cos(t):.1f} {CY + RING_R*math.sin(t):.1f}L{CX + (RING_R - L)*math.cos(t):.1f} {CY + (RING_R - L)*math.sin(t):.1f}')
    p = peach(u, lit)
    return (f'<path d="{"".join(quad + thick)}" stroke="{PEACH}" stroke-width="9" stroke-linecap="round" opacity=".35" filter="url(#{u}glow)"/>'
            f'<path d="{"".join(thin)}" stroke="{p}" stroke-width="2.4" stroke-linecap="round" opacity=".75"/>'
            f'<path d="{"".join(thick)}" stroke="{p}" stroke-width="3.6" stroke-linecap="round"/>'
            f'<path d="{"".join(quad)}" stroke="{p}" stroke-width="5.4" stroke-linecap="round"/>'
            f'<path d="{"".join(quad)}" stroke="{PEACH_CORE}" stroke-width="1.8" stroke-linecap="round" opacity=".85"/>')


def brackets(u, lit):
    x0 = y0 = BR; x1 = y1 = W - BR; L = BR_L; r = BR_RAD
    segs = [f'M{x0} {y0 + L}V{y0 + r}Q{x0} {y0} {x0 + r} {y0}H{x0 + L}', f'M{x1 - L} {y0}H{x1 - r}Q{x1} {y0} {x1} {y0 + r}V{y0 + L}',
            f'M{x0} {y1 - L}V{y1 - r}Q{x0} {y1} {x0 + r} {y1}H{x0 + L}', f'M{x1} {y1 - L}V{y1 - r}Q{x1} {y1} {x1 - r} {y1}H{x1 - L}']
    p = peach(u, lit)
    o = [f'<path d="{s}" fill="none" stroke="{PEACH}" stroke-width="{BR_W + 9}" stroke-linecap="round" opacity=".38" filter="url(#{u}glow)"/>' for s in segs]   # 收斂的外發光
    o += [f'<path d="{s}" fill="none" stroke="{p}" stroke-width="{BR_W}" stroke-linecap="round" stroke-linejoin="round"/>' for s in segs]
    o += [f'<path d="{s}" fill="none" stroke="{PEACH_CORE}" stroke-width="{BR_W*.3:.1f}" stroke-linecap="round" stroke-linejoin="round" opacity=".8"/>' for s in segs]   # 亮芯
    return ''.join(o)


def ground_shadow(u, cb, lit):
    """柔光：正下方一團柔和的影子。左上打光：地面上的接觸陰影＋往右下延伸的長投影（光在左上 → 影子在右下）。
    立方的底面（地面上的菱形）＝ 隱藏的後下頂點（投影在 C）＋ LL、B、LR；長投影＝底面菱形沿光線方向在地面上平移後取凸包。"""
    C = cb.C
    foot = [C, cb.LR, cb.B, cb.LL]
    if not lit:
        return f'<ellipse cx="{CX}" cy="{cb.B[1] + 6:.1f}" rx="{R*.82:.1f}" ry="{R*.13:.1f}" fill="#04070d" opacity=".55" filter="url(#{u}soft)"/>'
    v = (R*1.2, R*.5)                   # 地面上的投影方向：往右下（光從左上偏高處打來，所以影子不會拉太長）
    moved = [(x + v[0], y + v[1]) for x, y in foot]
    P_ = foot + moved
    P_ = sorted(set((round(x, 2), round(y, 2)) for x, y in P_))
    def cross(o, a, b): return (a[0]-o[0])*(b[1]-o[1]) - (a[1]-o[1])*(b[0]-o[0])
    lo, up = [], []
    for q in P_:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], q) <= 0: lo.pop()
        lo.append(q)
    for q in reversed(P_):
        while len(up) >= 2 and cross(up[-2], up[-1], q) <= 0: up.pop()
        up.append(q)
    h = lo[:-1] + up[:-1]     # 凸包
    # 地面受光區：光從左上打到桌面，立方左下方的地面略亮，影子才看得出來（深底上純黑影子會被吃掉）
    pool = f'<ellipse cx="{CX - 40:.1f}" cy="{cb.B[1] - 10:.1f}" rx="{R*1.55:.1f}" ry="{R*.5:.1f}" fill="#4a5b82" opacity=".55" filter="url(#{u}soft)"/>'
    return (pool + f'<polygon points="{pts(h)}" fill="url(#{u}cast)" filter="url(#{u}b6)"/>'
            # 接觸陰影：貼著底下兩條稜（LL→B→LR）最深的一條
            f'<path d="M{cb.LL[0]:.1f} {cb.LL[1] + 4:.1f}L{cb.B[0]:.1f} {cb.B[1] + 4:.1f}L{cb.LR[0]:.1f} {cb.LR[1] + 4:.1f}" fill="none" stroke="#02040a" stroke-width="16" stroke-linejoin="round" opacity=".7" filter="url(#{u}b6)"/>')


def cube(u, P, lit):
    cb = Cube(CX, CY, R); C = cb.C
    v18.set_glyph_palette(dict(gly=GLY))
    o = [f'<polygon points="{pts(cb.hex)}" fill="url(#{u}glass)" stroke="url(#{u}glass)" stroke-width="{RIM}" stroke-linejoin="round"/>']
    for k, fn in v17.BACK.items():
        o.append(f'<g opacity=".34" transform="{v17.place(cb, k, False)}">{v17.glyph(fn, u + k)}</g>')
    o.append(f'<path d="M{C[0]} {C[1]}L{cb.T[0]:.1f} {cb.T[1]:.1f}M{C[0]} {C[1]}L{cb.LL[0]:.1f} {cb.LL[1]:.1f}M{C[0]} {C[1]}L{cb.LR[0]:.1f} {cb.LR[1]:.1f}" '
             f'stroke="#ffffff" stroke-width="2.2" stroke-opacity=".55" stroke-linecap="round"/>')
    for k in ('top', 'left', 'right'):
        q = cb.quad(k)
        o.append(f'<polygon points="{pts(q)}" fill="{P[k]}" fill-opacity=".9"/>')
        o.append(f'<polygon points="{pts(q)}" fill="url(#{u}sheen)" opacity="{.22 if not lit else .16}"/>')   # 珍珠光澤
        cen = (sum(x for x, _ in q)/4, sum(y for _, y in q)/4)
        o.append(f'<polygon points="{pts(shrink(q, cen, .9))}" fill="none" stroke="#ffffff" stroke-opacity=".7" stroke-width="2" stroke-linejoin="round"/>')
    if lit:   # 光穿過玻璃：右面靠下、左面靠下各一團很淡的亮區（光從左上進、往右下出）
        o.append(f'<ellipse cx="{(C[0] + cb.LR[0])/2 - 8:.1f}" cy="{(C[1] + cb.B[1])/2 + 22:.1f}" rx="{R*.28:.1f}" ry="{R*.2:.1f}" fill="url(#{u}trans)" opacity=".8"/>')
        o.append(f'<ellipse cx="{(cb.LL[0] + C[0])/2 + 6:.1f}" cy="{(C[1] + cb.B[1])/2 + 18:.1f}" rx="{R*.22:.1f}" ry="{R*.16:.1f}" fill="url(#{u}trans)" opacity=".45"/>')
    for k, fn in v17.FRONT.items():
        o.append(f'<g transform="{v17.place(cb, k, True)}">{v17.glyph(fn, u + k)}</g>')
    y = f'M{C[0]} {C[1]}L{cb.UL[0]:.1f} {cb.UL[1]:.1f}M{C[0]} {C[1]}L{cb.UR[0]:.1f} {cb.UR[1]:.1f}M{C[0]} {C[1]}L{cb.B[0]:.1f} {cb.B[1]:.1f}'
    o.append(f'<path d="{y}" stroke="#ffffff" stroke-width="10" stroke-opacity=".3" stroke-linecap="round" filter="url(#{u}b2)"/>')
    o.append(f'<path d="{y}" stroke="#ffffff" stroke-width="4" stroke-opacity=".95" stroke-linecap="round"/>')
    # 外緣：柔和的淡薰衣草細邊（深底上不要硬黑邊）→ 象牙白厚緣 → 內側亮線
    o.append(f'<polygon points="{pts(cb.hex)}" fill="none" stroke="{P["rim_soft"]}" stroke-width="{RIM + 3}" stroke-linejoin="round"/>')
    o.append(f'<polygon points="{pts(cb.hex)}" fill="none" stroke="{P["rim"]}" stroke-width="{RIM}" stroke-linejoin="round" opacity=".92"/>')
    o.append(f'<polygon points="{pts(shrink(cb.hex, C, 1 - (RIM*.5 + 2)/R))}" fill="none" stroke="#ffffff" stroke-width="2.4" stroke-linejoin="round" opacity=".9"/>')
    if lit:
        # 受光稜（左上兩條外緣＋Y 往左上那條）加高光；背光稜（右下兩條外緣）壓暗
        hl = f'M{cb.LL[0]:.1f} {cb.LL[1]:.1f}L{cb.UL[0]:.1f} {cb.UL[1]:.1f}L{cb.T[0]:.1f} {cb.T[1]:.1f}M{C[0]} {C[1]}L{cb.UL[0]:.1f} {cb.UL[1]:.1f}'
        o.append(f'<path d="{hl}" fill="none" stroke="#ffffff" stroke-width="12" stroke-linecap="round" stroke-linejoin="round" opacity=".45" filter="url(#{u}b2)"/>')
        o.append(f'<path d="{hl}" fill="none" stroke="#ffffff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>')
        dk = f'M{cb.UR[0]:.1f} {cb.UR[1]:.1f}L{cb.LR[0]:.1f} {cb.LR[1]:.1f}L{cb.B[0]:.1f} {cb.B[1]:.1f}'
        o.append(f'<path d="{dk}" fill="none" stroke="#5d6386" stroke-width="{RIM*.6:.1f}" stroke-linecap="round" stroke-linejoin="round" opacity=".55"/>')
        # 頂點上的一顆高光點（左上頂點最亮）
        o.append(f'<circle cx="{cb.UL[0] + 3:.1f}" cy="{cb.UL[1]:.1f}" r="7" fill="#ffffff" opacity=".85" filter="url(#{u}b2)"/>')
    return ''.join(o), cb


def icon(lit):
    u = 'l' if lit else 'p'
    d, P = defs(u, lit)
    cube_svg, cb = cube(u, P, lit)
    return '\n'.join([f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {W}" width="{W}" height="{W}">', d,
                      f'<rect width="{W}" height="{W}" fill="url(#{u}bg)"/>', ground_shadow(u, cb, lit), ring(u, lit), brackets(u, lit),
                      cube_svg, '</svg>'])


def render():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        pg = b.new_page(viewport={'width': 1024, 'height': 1024})
        for n in ('icon_dark_pro', 'icon_dark_lit'):
            pg.goto('file://' + os.path.join(HERE, n + '.svg')); pg.wait_for_timeout(300)
            pg.evaluate("document.documentElement.setAttribute('width','1024');document.documentElement.setAttribute('height','1024')")
            pg.wait_for_timeout(100)
            pg.screenshot(path=os.path.join(HERE, n + '.png'), clip={'x': 0, 'y': 0, 'width': 1024, 'height': 1024})
        cols = ''.join(f'<div class="c"><img src="file://{HERE}/{n}.svg"><p>{t}</p></div>' for n, t in (('icon_dark_pro', '柔光'), ('icon_dark_lit', '左上打光')))
        html = (f'<!doctype html><html><head><meta charset="utf-8"><style>body{{margin:0;width:1640px;background:#141c30;font-family:"WenQuanYi Zen Hei",sans-serif}}'
                f'main{{display:flex;gap:40px;padding:40px}}.c{{display:flex;flex-direction:column;align-items:center}}.c img{{width:760px;height:760px;border-radius:24px}}'
                f'.c p{{margin:18px 0 0;color:{PEACH};font-size:38px;font-weight:700;letter-spacing:.12em}}</style></head><body><main>{cols}</main></body></html>')
        tmp = os.path.join(SCRATCH, '_v21_sheet.html'); open(tmp, 'w').write(html)
        pg.set_viewport_size({'width': 1640, 'height': 900})
        pg.goto('file://' + tmp); pg.wait_for_timeout(600)
        hh = int(pg.evaluate("Math.ceil(document.querySelector('main').getBoundingClientRect().bottom)"))
        pg.screenshot(path=os.path.join(HERE, '深色專業_兩版.png'), clip={'x': 0, 'y': 0, 'width': 1640, 'height': hh}, full_page=True)
        b.close()


def main():
    open(os.path.join(HERE, 'icon_dark_pro.svg'), 'w').write(icon(False))
    open(os.path.join(HERE, 'icon_dark_lit.svg'), 'w').write(icon(True))
    render()


if __name__ == '__main__':
    main()
