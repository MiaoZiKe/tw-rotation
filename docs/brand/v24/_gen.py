# 第二十四輪〈股立方〉：三圖立方 —— 立方不再切六塊，而是由「三張面圖」拼成（頂面一張、左面一張、右面一張，三塊之間留同寬白縫）。
# 客戶原話：「幫我試試改成這立方體是用三個圖片組合成的」
#
# 六個面向沒有丟：每一張面圖把那一面原本的兩個面向融成一個圖案 ——
#   頂面（看大局）＝資金＋產業：一個來源點分流成三條線，三條線就是晶片左邊的針腳 →「錢往哪個產業流」
#   左面（看交易）＝技術＋籌碼：三根 K 棒立在一疊籌碼上 →「誰在什麼時候進場」
#   右面（看公司）＝基本＋消息：一張報紙，版面裡是營收長條圖 →「這家公司值不值、有沒有雜音」
#
# 三個方向：
#   D 三面三圖・色塊：三塊面用三個明度平塗，面上是合成圖案（淺面深線、深面淺線）
#   E 三面三圖・線稿：只有線條；每一面是一個獨立的圓角菱形框＋單線圖案，三框之間留縫，不畫完整立方輪廓
#   F 三面三圖・圖形即面：面不畫底色，由圖案的實心形狀（同一明度）把菱形撐滿，三個圖騰拼成立方
#
# 投影、色票、字標、渲染都直接用 v23（等角面座標 O＋sP＋tQ；圖示的控制點投影到面上，再用畫面座標的固定線寬描邊）。
# 圖案是 48 格線、線寬 3.5（＝v23 的 24 格 1.75 放大兩倍，縮到 24px 時線寬一樣是 1.75）。
# 執行：BRAND_SCRATCH=<暫存資料夾> python docs/brand/v24/_gen.py
import math, os, json, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
SCRATCH = os.environ.get('BRAND_SCRATCH', '/tmp')
os.makedirs(SCRATCH, exist_ok=True)
_spec = importlib.util.spec_from_file_location('v23', os.path.join(HERE, '..', 'v23', '_gen.py'))
v23 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(v23)
Path, rrect, circle, line, Cube, poly = v23.Path, v23.rrect, v23.circle, v23.line, v23.Cube, v23.poly
PALETTES, contrast, svg, wordmark, render = v23.PALETTES, v23.contrast, v23.svg, v23.wordmark, v23.render
S60, C30 = v23.S60, v23.C30

G = 48          # 圖案格線
SW = 3.5        # 線寬（48 格）


def save(name, text):
    with open(os.path.join(HERE, name), 'w') as f: f.write(text)


# =====================================================================================
# 三張合成面圖 —— 線條版（D／E 用，也是 App 內導覽圖示的平面版）
# 元素：(Path, 填色？, 描邊？)
# =====================================================================================
def combo_top():   # 資金＋產業：左邊三個資金來源點，三條線匯流進晶片、直接變成晶片左邊的針腳（錢流進產業）
    # 第一版是「一個來源點分三條線」：在 48 格裡只有 14 格的水平距離，線寬 3.5 的三條線在起點黏成一片葉子，32px 以下讀成一支箭；
    # 改成三個來源點（上、中、下）往晶片收攏，三條線從頭到尾都分得開。
    o = []
    for y0, y1 in ((10, 18), (24, 24), (38, 30)):
        o.append((circle(5, y0, 3), True, False))
        o.append((Path().M(8, y0).C(16, y0, 15, y1, 24, y1) if y0 != y1 else line((8, 24), (24, 24)), False, True))
    o.append((rrect(24, 14, 20, 20, 3.5), False, True))
    o.append((rrect(30, 20, 8, 8, 1.5), False, True))
    pins = Path()
    for t in (30, 38): pins.M(t, 14).V(9).M(t, 34).V(39)
    for t in (20, 28): pins.M(44, t).H(46.5)
    o.append((pins, False, True))
    return o


def combo_left():  # 技術＋籌碼：三根 K 棒（空心＝漲、實心＝跌，往右上）立在一疊籌碼（側面看的三片）上
    o = []
    for x, wt, wb, bt, bb, solid in ((14, 9, 22.5, 12.5, 19.5, False), (24, 5, 21, 8, 15, True), (34, 2.5, 17, 5, 12, False)):
        o.append((line((x, wt), (x, bt)), False, True))
        o.append((line((x, bb), (x, wb)), False, True))
        o.append((rrect(x - 3.5, bt, 7, bb - bt, 1.25), solid, True))
    # 籌碼改用「側面看的一疊」：一個圓角長方形＋兩條分隔線＝三片。
    # （v23 那種橢圓疊片本身已經是立體圖，再投影到斜的左面會變成一顆壓扁的圓盤，讀不出是籌碼）
    o.append((rrect(7, 29, 34, 16, 3), False, True))
    o.append((line((7, 34.33), (41, 34.33)), False, True))
    o.append((line((7, 39.67), (41, 39.67)), False, True))
    return o


def combo_right():  # 基本＋消息：報紙（正面一頁＋左邊摺頁），頁內一條標題線＋三根往上的營收長條＋基線
    page = Path().M(11, 42).H(38).arc(38, 38, 4, 4, 90, 0).V(10).arc(38, 10, 4, 4, 0, -90).H(18).arc(18, 10, 4, 4, 270, 180)
    page.V(39).arc(11, 39, 3, 3, 0, 90).arc(11, 39, 3, 3, 90, 180).V(17).H(14)
    o = [(page, False, True), (line((20, 12.5), (36, 12.5)), False, True), (line((20, 37), (36, 37)), False, True)]
    for x, top in ((21.5, 27.5), (28, 23), (34.5, 18.5)):
        o.append((rrect(x - .75, top, 1.5, 32.5 - top, .75), True, True))
    return o


# =====================================================================================
# 三張合成面圖 —— 刻版（F 用）：整塊面就是圖案 —— 面被「切縫」切成幾塊實心形狀，切縫的寬度＝三塊面之間的白縫，
# 所以面與面之間的縫、面裡面的縫是同一套系統。切縫有兩種：
#   ('cut', Path)  線狀切縫（線寬＝縫寬、圓頭）。端點落在 0 或 48 的切縫會把面整個切斷；
#                  圓頭半徑＝縫寬／2，剛好停在原本的面邊界，不會切到隔壁那一面。
#   ('hole', Path) 整塊挖空（空心 K 棒、營收長條）
# ⚠ 第一版照字面「面不畫底色、只用圖案的實心形狀」做（見 mark_F_字面試作_ink.png）：圖案撐不滿菱形，
#   三個面的外形散掉、立方讀不出來，所以改成「面被圖案切開」—— 面仍然是由圖案的形狀組成，但外形保住。
# =====================================================================================
def totem_top():   # 資金＋產業：左邊三道從邊緣收攏的匯流切縫（錢）流進晶片；晶片外框＋中心方塊挖空＋上下右走線切到邊
    o = [('cut', Path().M(0, 8).C(10, 8, 11, 18, 20, 18)), ('cut', Path().M(0, 40).C(10, 40, 11, 30, 20, 30)), ('cut', line((0, 24), (20, 24))),
         ('cut', rrect(20, 13, 22, 22, 3)), ('hole', rrect(27.5, 20.5, 7, 7, 1.2))]
    for x in (25.5, 36.5): o += [('cut', line((x, 13), (x, 0))), ('cut', line((x, 35), (x, 48)))]
    for y in (19, 29): o.append(('cut', line((42, y), (48, y))))
    return o


def totem_left():  # 技術＋籌碼：下面三條橫切縫切出三片籌碼（側面看的一疊）；上面三根 K 棒 —— 漲＝挖空、跌＝切出輪廓留下實心
    o = [('cut', line((0, y), (48, y))) for y in (28, 34.67, 41.33)]
    for x, wt, wb, bt, bb, hollow in ((13, 9, 24.5, 13, 21, True), (24, 4, 22.5, 7.5, 17, False), (35, 0, 16.5, 3.5, 12, True)):
        if wt < bt: o.append(('cut', line((x, wt), (x, bt))))
        o.append(('cut', line((x, bb), (x, wb))))
        o.append(('hole' if hollow else 'cut', rrect(x - 4, bt, 8, bb - bt, 1.2)))
    return o


def totem_right():  # 基本＋消息：整面是一張報紙 —— 左下 L 形切縫切出摺頁；標題、副標兩道切縫；三根營收長條挖空、坐在基線切縫上
    o = [('cut', line((9, 48), (9, 12), (0, 12))),
         ('cut', line((15, 7.5), (41, 7.5))), ('cut', line((15, 14), (29, 14))), ('cut', line((15, 42), (41, 42)))]
    for x, top in ((15.5, 31), (24.5, 25), (33.5, 19)):
        o.append(('hole', rrect(x, top, 6.5, 38.5 - top, 1.2)))
    return o


# 小尺寸版（App 圖示 32～48px 用）：每一面只留最主要的切縫 —— 頂面＝晶片外框＋中心；左面＝三片籌碼；右面＝摺頁＋三根長條。
# 完整版的細縫在 48px 以下不到 1px，會糊成雜紋（實測見 v24_small_x6.png），所以小尺寸不是「縮小」，是「少畫」。
def totem_top_s():   return [('cut', rrect(14, 10, 28, 28, 4)), ('hole', rrect(23, 19, 10, 10, 2))]
def totem_left_s():  return [('cut', line((0, y), (48, y))) for y in (18, 33)]
def totem_right_s():
    o = [('cut', line((12, 48), (12, 14), (0, 14)))]
    for x, top in ((18, 30), (27.5, 22), (37, 14)): o.append(('hole', rrect(x, top, 6.5, 41 - top, 1.5)))
    return o


SMALL = {'top': totem_top_s, 'left': totem_left_s, 'right': totem_right_s}


COMBOS = [
    ('top',   '頂面', '資金＋產業', '錢往哪個產業流',       combo_top,   totem_top),
    ('left',  '左面', '技術＋籌碼', '誰在什麼時候進場',     combo_left,  totem_left),
    ('right', '右面', '基本＋消息', '這家公司值不值、有沒有雜音', combo_right, totem_right),
]
FN = {c[0]: c for c in COMBOS}


def lines_body(elems, color, T=lambda p: p, sw=SW):
    o = []
    for p, fill, stroke in elems:
        a = f'd="{p.d(T)}" fill="{color if fill else "none"}"'
        if stroke: a += f' stroke="{color}" stroke-width="{sw:.3f}" stroke-linecap="round" stroke-linejoin="round"'
        o.append(f'<path {a}/>')
    return ''.join(o)


CUT = 2.5     # 刻版切縫寬（48 格）；投影到立方上時改用畫面座標的縫寬（＝面與面之間的白縫）


def cuts_body(elems, color, T=lambda p: p, w=CUT):
    o = []
    for kind, p in elems:
        if kind == 'hole': o.append(f'<path d="{p.d(T)}" fill="{color}"/>')
        else: o.append(f'<path d="{p.d(T)}" fill="none" stroke="{color}" stroke-width="{w:.3f}" stroke-linecap="round" stroke-linejoin="round"/>')
    return ''.join(o)


def solid_flat(face, uid, color='currentColor'):
    """平面實心版：48 格圓角方塊被切縫切開（用 mask，不是濾鏡）；線色＝currentColor"""
    cuts = cuts_body(FN[face][5](), '#000')
    return (f'<mask id="m-{uid}" maskUnits="userSpaceOnUse" x="0" y="0" width="48" height="48">'
            f'<rect width="48" height="48" fill="#fff"/>{cuts}</mask>'
            f'<rect x="1" y="1" width="46" height="46" rx="4" fill="{color}" mask="url(#m-{uid})"/>')


# =====================================================================================
# 立方（三塊面＝三張圖）
# =====================================================================================
GAP = .035          # 三塊面之間的白縫（以邊長 a 為單位）
RAD = .014          # 面的圓角
ICON = .66          # 合成圖案佔面的比例（D／E）
STROKE = SW/G*ICON  # 投影後線寬（以 a 為單位）：圖案 3.5／48 格 × 圖案框 ⇒ 跟圖案本身同比例
FACE_TONE = (1, 2, 4)   # D／F 三塊面用 v23 明度階的第幾階：頂 L1、左 L2、右 L4（相鄰兩面對比都 ≈2:1，最淺面對白底 1.5:1）
FULL = (0, 1, 0, 1)


def face_T(cube, face, size):
    """48 格圖案 → 面中央、佔 size 的正方形（面座標）"""
    k = size/G
    return lambda p: cube.at(face, .5 + (p[0] - G/2)*k, .5 + (p[1] - G/2)*k)


def face_fill_T(cube, face, inset):
    """48 格圖騰 → 撐滿整個面（扣掉 inset px 的垂直內縮）"""
    e = inset/(cube.a*S60)
    return lambda p: cube.at(face, e + p[0]/G*(1 - 2*e), e + p[1]/G*(1 - 2*e))


def tones3(P, dark=False):
    t = P['dark_tones'] if dark else P['tones']
    return [t[i] for i in ((0, 2, 4) if dark else FACE_TONE)]


def line_color(P, bg):
    return P['ink'] if contrast(P['ink'], bg) >= contrast(P['light'], bg) else P['light']


def cube_D(cube, P, dark=False):
    a = cube.a; o = []
    for (face, *_), tone in zip(COMBOS, tones3(P, dark)):
        o.append(v23.rpanel(cube, face, FULL, GAP*a, RAD*a, tone))
        o.append(lines_body(FN[face][4](), line_color(P, tone), face_T(cube, face, ICON), STROKE*a))
    return ''.join(o)


def cube_E(cube, P, color=None):
    """每一面：一個圓角菱形框（線）＋單線圖案；三框之間的縫＝GAP×1.6（比 D 寬一點，線稿才看得出是三張分開的圖）"""
    a = cube.a; w = STROKE*a; ink = color or P['ink']; o = []
    for face, *_ in COMBOS:
        pts = cube.panel(face, FULL, GAP*1.6*a/2 + w/2)
        o.append(poly(pts, 'none', f' stroke="{ink}" stroke-width="{w:.2f}" stroke-linejoin="round"'))
        o.append(lines_body(FN[face][4](), ink, face_T(cube, face, ICON*.92), w))
    return ''.join(o)


def cube_F(cube, P, dark=False, bg='#ffffff', small=False):
    """三塊實心面（同 D 的三個明度），再用底色畫切縫（縫寬＝面與面之間的白縫，face_fill_T 讓 0／48 落在面邊界上）。
    small＝小尺寸版：切縫少、縫寬 ×2.4（32px 時約 0.9px）"""
    a = cube.a; bg = P['ink'] if dark else bg; o = []
    g = GAP*a*(2.4 if small else 1)
    for (face, *_), tone in zip(COMBOS, tones3(P, dark)):
        o.append(v23.rpanel(cube, face, FULL, g, RAD*a, tone))
        o.append(cuts_body((SMALL[face] if small else FN[face][5])(), bg, face_fill_T(cube, face, 0), g))
    return ''.join(o)


CASES = {'D': cube_D, 'E': cube_E, 'F': cube_F}
REC = 'F'
MARK, A_MARK = 1024, 330


def mark_svg(case, pal):
    P = PALETTES[pal]; cube = Cube(MARK/2, MARK/2, A_MARK)
    return svg(MARK, MARK, CASES[case](cube, P), '#ffffff', f'股立方 三圖立方 {case}・{P["name"]}')


def app_icon(case, pal, dark=False, small=False):
    P = PALETTES[pal]; S = 1024
    bg = P['ink'] if dark else '#ffffff'
    cube = Cube(S/2, S/2, 340 if small else 320)
    if case == 'E': inner = cube_E(cube, P, P['light'] if dark else None)
    elif case == 'F': inner = cube_F(cube, P, dark=dark, small=small)
    else: inner = CASES[case](cube, P, dark=dark)
    body = f'<rect width="{S}" height="{S}" rx="{S*.225:.0f}" fill="{bg}"/>' + inner
    return svg(S, S, body, None, f'股立方 App 圖示 {case}（{"深底" if dark else "淺底"}）')


def app_icon_16(pal, dark=False):
    """16px 簡化：三面三明度、不留縫、不放圖案；直稜與中線落在整數像素（x＝3、8、13）"""
    P = PALETTES[pal]; bg = P['ink'] if dark else '#ffffff'
    top, left, right = tones3(P, dark)
    a = 5/C30; c = Cube(8, 8, a)
    body = (f'<rect width="16" height="16" rx="3.6" fill="{bg}"/>'
            + poly([c.T, c.UR, c.C, c.UL], top) + poly([c.UL, c.C, c.B, c.LL], left) + poly([c.C, c.UR, c.LR, c.B], right))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16" shape-rendering="crispEdges">'
            f'<title>股立方 App 圖示 16px 簡化版</title>{body}</svg>\n')


def lockup_h(case, pal='ink'):
    P = PALETTES[pal]
    H = 420; a = H/2; pad = 90
    cube = Cube(pad + C30*a, pad + a, a)
    zh_size = 170
    _, bb = wordmark(P, 0, 0, zh_size)
    tx = pad + 2*C30*a + 96; ty = pad + a - (bb[3] - bb[1])/2
    wm, bb = wordmark(P, tx, ty, zh_size)
    Wd, Hd = math.ceil(bb[2] + pad), math.ceil(H + 2*pad)
    save('lockup_h.svg', svg(Wd, Hd, CASES[case](cube, P) + wm, '#ffffff', '股立方 標準字組合（橫式・三圖立方）'))
    return Wd, Hd


def combo_files():
    """平面版（不投影、48 格）：線條版 combo_<面>.svg、實心版 combo_<面>_實心.svg、sprite combos.svg"""
    sym = []
    for face, zh, pair, q, fl, fs in COMBOS:
        lb = lines_body(fl(), 'currentColor'); sb = solid_flat(face, face); sbs = solid_flat(face, face + '-s')
        save(f'combo_{zh}.svg', f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="48" height="48"><title>{zh}・{pair}：{q}</title>{lb}</svg>\n')
        save(f'combo_{zh}_實心.svg', f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" width="48" height="48"><title>{zh}・{pair}：{q}（實心）</title>{sb}</svg>\n')
        sym.append(f'<symbol id="combo-{face}" viewBox="0 0 48 48"><title>{zh}・{pair}</title>{lb}</symbol>')
        sym.append(f'<symbol id="combo-{face}-solid" viewBox="0 0 48 48"><title>{zh}・{pair}（實心）</title>{sbs}</symbol>')
    save('combos.svg', '<svg xmlns="http://www.w3.org/2000/svg" style="display:none">\n<!-- 用法：<svg width="48" height="48" style="color:#1f2d3d"><use href="combos.svg#combo-top"/></svg>；顏色跟著 currentColor -->\n'
         + '\n'.join(sym) + '\n</svg>\n')


CSS = v23.CSS


def combo_sheet():
    cells = ''
    for face, zh, pair, q, _, _ in COMBOS:
        ln = open(os.path.join(HERE, f'combo_{zh}.svg')).read(); so = open(os.path.join(HERE, f'combo_{zh}_實心.svg')).read()
        cells += (f'<div class="f"><div class="pair"><span class="ic">{ln}</span><span class="ic">{so}</span></div>'
                  f'<div class="nm">{zh}｜{pair}</div><div class="q">{q}</div>'
                  f'<div class="sm">' + ''.join(f'<span style="width:{s}px;height:{s}px">{ln}</span>' for s in (48, 32, 24))
                  + ''.join(f'<span style="width:{s}px;height:{s}px">{so}</span>' for s in (32, 24)) + '</div></div>')
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}
body{{padding:48px 56px;width:1200px}}
.row{{display:grid;grid-template-columns:repeat(3,1fr);margin-top:28px}}
.f{{display:flex;flex-direction:column;align-items:center;gap:8px;padding:8px 0;border-left:1px solid #eef1f4}} .f:first-child{{border-left:0}}
.pair{{display:flex;gap:28px}} .ic{{width:96px;height:96px;color:#1f2d3d;display:inline-flex}} .ic svg,.sm svg{{width:100%;height:100%}}
.nm{{font-size:20px;font-weight:600;margin-top:10px;letter-spacing:.08em}} .q{{font-size:14px;color:#4a5868}}
.sm{{display:flex;gap:16px;align-items:center;margin-top:12px;color:#1f2d3d}} .sm span{{display:inline-flex}}
</style></head><body><h1>股立方｜三張面圖</h1><div class="en" style="margin-top:8px">THREE FACES · 48 GRID · STROKE 3.5</div>
<div class="row">{cells}</div>
<p class="cap" style="margin-top:28px">每一面把兩個面向融成一張圖。左為線條版（App 內導覽圖示用），右為實心版（立方 F 案的圖騰）。下排為實際像素：線條版 48／32／24px、實心版 32／24px。顏色跟著 currentColor。</p>
</body></html>"""


def overview(wh):
    P = PALETTES['ink']
    def img(n, w): return f'<img src="file://{HERE}/{n}" style="width:{w}px;height:auto;display:block">'
    notes = {'D': ('三面三圖・色塊', '三塊面三個明度平塗，面上是合成圖案 —— 最好讀、最像 App'),
             'E': ('三面三圖・線稿', '三個圓角菱形框各放一張單線圖，不畫立方輪廓 —— 三張圖自己拼出立方'),
             'F': ('三面三圖・圖形即面', '整塊面被圖案切開，面就是圖案的實心形狀 —— 最有標誌感')}
    r1 = ''.join(f'<div class="card">{img(f"mark_{c}_ink.svg", 300)}<h2>{c}　{notes[c][0]}{"　<b class=rec>推薦</b>" if c == REC else ""}</h2>'
                 f'<div class="cap">{notes[c][1]}</div></div>' for c in 'DEF')
    r2 = ''
    for k, p in PALETTES.items():
        t3 = tones3(p)
        sw = ''.join(f'<div class="sw"><i style="background:{t}"></i><span class="mono">{t} {n}</span></div>' for t, n in zip(t3, ('頂', '左', '右')))
        sw += f'<div class="sw"><i style="background:{p["ink"]}"></i><span class="mono">{p["ink"]} 字</span></div>'
        r2 += f'<div class="card">{img(f"mark_{REC}_{k}.svg", 260)}<h2>{p["name"]}{"　<b class=rec>主推</b>" if k == "ink" else ""}</h2><div class="sws">{sw}</div></div>'
    r3 = ''
    for face, zh, pair, q, _, _ in COMBOS:
        r3 += (f'<div class="fc"><div class="pair"><span class="fi">{open(os.path.join(HERE, f"combo_{zh}.svg")).read()}</span>'
               f'<span class="fi">{open(os.path.join(HERE, f"combo_{zh}_實心.svg")).read()}</span></div>'
               f'<div class="nm">{zh}＝{pair}</div><div class="cap">{q}</div></div>')
    def sizes(dark):
        k = 'dark' if dark else 'light'
        o = f'<div class="sz">{img(f"app_icon_{k}.svg", 180)}<span class="mono">180</span></div>'
        o += ''.join(f'<div class="sz">{img(f"app_icon_{k}.svg", s)}<span class="mono">{s} 完整</span></div>' for s in (48, 32))
        o += ''.join(f'<div class="sz">{img(f"app_icon_small_{k}.svg", s)}<span class="mono">{s} 小尺寸版</span></div>' for s in (48, 32))
        return o + f'<div class="sz">{img(f"app_icon_16_{k}.svg", 16)}<span class="mono">16 簡化</span></div>'
    r4 = (f'<div class="apps"><div class="appcol"><div class="big">{img("app_icon_light.svg", 200)}<span class="mono">1024（縮圖）</span></div><div class="szs">{sizes(False)}</div></div>'
          f'<div class="appcol"><div class="big">{img("app_icon_dark.svg", 200)}<span class="mono">1024（縮圖）</span></div><div class="szs">{sizes(True)}</div></div></div>'
          f'<div class="locks"><div>{img("lockup_h.svg", 600)}</div></div>')
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}
body{{width:1600px;padding:64px 80px}}
.grid3{{display:grid;grid-template-columns:repeat(3,1fr);gap:40px;margin-top:20px}}
.card{{display:flex;flex-direction:column;align-items:flex-start;gap:8px}}
.rec{{font-size:12px;font-weight:400;color:#fff;background:#1f2d3d;padding:2px 8px;border-radius:4px;letter-spacing:.1em;vertical-align:3px}}
.sws{{display:grid;grid-template-columns:repeat(2,auto);gap:6px 20px}} .sw{{display:flex;align-items:center;gap:8px}} .sw i{{width:18px;height:18px;border-radius:4px;display:inline-block;box-shadow:inset 0 0 0 1px rgba(0,0,0,.06)}}
.facets{{display:grid;grid-template-columns:repeat(3,1fr);margin-top:24px}}
.fc{{display:flex;flex-direction:column;align-items:center;gap:8px;border-left:1px solid #eef1f4}} .fc:first-child{{border-left:0}}
.pair{{display:flex;gap:24px}} .fi{{width:72px;height:72px;color:#1f2d3d;display:inline-flex}} .fi svg{{width:100%;height:100%}} .nm{{font-size:18px;font-weight:600;letter-spacing:.08em;margin-top:6px}}
.row4{{display:flex;gap:56px;margin-top:24px;align-items:flex-start}}
.apps{{display:flex;flex-direction:column;gap:20px}} .appcol{{display:flex;gap:28px;align-items:flex-end;background:#f3f5f7;border-radius:16px;padding:20px 24px}}
.big,.sz{{display:flex;flex-direction:column;align-items:center;gap:6px;white-space:nowrap}} .szs{{display:flex;gap:22px;align-items:flex-end}}
.locks div{{border:1px solid #eef1f4;border-radius:12px}}
</style></head><body>
<h1>股立方｜三圖立方</h1><div class="en" style="margin-top:8px">STOCK CUBE · THREE PICTURES · ONE CUBE</div>
<p class="lead">立方由三張面圖拼成：頂面「錢往哪個產業流」（資金＋產業）、左面「誰在什麼時候進場」（技術＋籌碼）、右面「這家公司值不值、有沒有雜音」（基本＋消息）。三塊之間留同寬白縫；一個色相、平塗、無漸層與投影。</p>
<div class="sec"><h2>一　三個方向（墨藍示範）</h2><div class="grid3">{r1}</div></div>
<div class="sec"><h2>二　推薦案 {REC} × 三種色系</h2><div class="grid3">{r2}</div></div>
<div class="sec"><h2>三　三張合成面圖（平面版：線條／實心）</h2><div class="facets">{r3}</div></div>
<div class="sec"><h2>四　App 圖示與標準字</h2><div class="row4">{r4}</div></div>
</body></html>"""


def main():
    jobs = []
    def mk(name, text, w=MARK, h=MARK):
        save(name + '.svg', text); jobs.append((os.path.join(HERE, name + '.svg'), os.path.join(HERE, name + '.png'), w, h, False))
    for c in 'DEF': mk(f'mark_{c}_ink', mark_svg(c, 'ink'))
    for k in ('graphite', 'teal'): mk(f'mark_{REC}_{k}', mark_svg(REC, k))
    combo_files()
    mk('app_icon_light', app_icon(REC, 'ink'))
    mk('app_icon_dark', app_icon(REC, 'ink', True))
    save('app_icon_small_light.svg', app_icon(REC, 'ink', small=True)); save('app_icon_small_dark.svg', app_icon(REC, 'ink', True, small=True))
    save('app_icon_16_light.svg', app_icon_16('ink')); save('app_icon_16_dark.svg', app_icon_16('ink', True))
    wh = lockup_h(REC)
    jobs.append((os.path.join(HERE, 'lockup_h.svg'), os.path.join(HERE, 'lockup_h.png'), wh[0], wh[1], False))
    cs = os.path.join(SCRATCH, 'v24_combos.html'); open(cs, 'w').write(combo_sheet())
    jobs.append((cs, os.path.join(HERE, '三張面圖.png'), 1312, 400, True))
    ov = os.path.join(SCRATCH, 'v24_overview.html'); open(ov, 'w').write(overview(wh))
    jobs.append((ov, os.path.join(HERE, '股立方_三圖立方.png'), 1600, 1000, True))
    for n in ('app_icon_light', 'app_icon_dark', 'app_icon_16_light', 'app_icon_16_dark', 'app_icon_small_light', 'app_icon_small_dark'):
        for s in ((16, 32) if '16' in n else (48, 32) if 'small' in n else (180, 48, 32, 16)):
            h = os.path.join(SCRATCH, f'v24_{n}_{s}.html')
            open(h, 'w').write(f'<html><body style="margin:0"><img src="file://{HERE}/{n}.svg" width="{s}" height="{s}" style="display:block"></body></html>')
            jobs.append((h, os.path.join(SCRATCH, f'v24_{n}_{s}.png'), s, s, False))
    render(jobs)
    print('ok', len(jobs), 'png')


if __name__ == '__main__':
    main()
