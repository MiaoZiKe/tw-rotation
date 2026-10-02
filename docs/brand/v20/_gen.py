# 第二十輪〈股立方〉：標誌只留立方；依立方設計「股立方」字標（A 三面色／B 等角立體字／C 方框字）與橫、直式組合。白底。
# Andy 第二十輪：「若是只留下立方體，幫我依據立方體設計"股立方"風格」
# 立方、面上的細節圖示、貼面規則與五種風格配色都直接用第十九輪（v19.cube／v19.THEMES）。
# 所有文字都轉成向量路徑（fontTools 讀容器裡的 WenQuanYi Zen Hei／DejaVu Sans Bold 字形外框），
# 所以 SVG 拿到沒裝這些字型的電腦上也長得一樣；B 立體字的厚度是用字形外框的每一條邊拉出側面四邊形畫的。
# 需要：pip install fonttools（只有產生器要用，網站不用）
# 執行：BRAND_SCRATCH=<暫存資料夾> python docs/brand/v20/_gen.py
import math, os, importlib.util
from fontTools.ttLib import TTCollection, TTFont
from fontTools.pens.basePen import BasePen

HERE = os.path.dirname(os.path.abspath(__file__))
SCRATCH = os.environ.get('BRAND_SCRATCH', '/tmp')
_spec = importlib.util.spec_from_file_location('v19', os.path.join(HERE, '..', 'v19', '_gen.py'))
v19 = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(v19)
THEMES, ORDER = v19.THEMES, v19.ORDER
S3 = math.cos(math.radians(30))

# ---------- 字形 → 多邊形 ----------
ZH = TTCollection('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc').fonts[0]
EN = TTFont('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')


class FlatPen(BasePen):
    """把字形外框（TrueType 二次曲線）攤平成折線；每個輪廓一串點（字型座標，y 朝上）"""
    def __init__(self, gs, steps=8):
        super().__init__(gs); self.cs = []; self.cur = None; self.steps = steps
    def _moveTo(self, p): self.cur = [p]; self.cs.append(self.cur)
    def _lineTo(self, p): self.cur.append(p)
    def _qCurveToOne(self, p1, p2):
        p0 = self.cur[-1]
        for i in range(1, self.steps + 1):
            t = i/self.steps
            self.cur.append(((1-t)**2*p0[0] + 2*(1-t)*t*p1[0] + t*t*p2[0], (1-t)**2*p0[1] + 2*(1-t)*t*p1[1] + t*t*p2[1]))
    def _curveToOne(self, p1, p2, p3):
        p0 = self.cur[-1]
        for i in range(1, self.steps + 1):
            t = i/self.steps; a, b, c, d = (1-t)**3, 3*(1-t)**2*t, 3*(1-t)*t*t, t**3
            self.cur.append((a*p0[0] + b*p1[0] + c*p2[0] + d*p3[0], a*p0[1] + b*p1[1] + c*p2[1] + d*p3[1]))
    def _closePath(self): pass
    def _endPath(self): pass


def shape(text, font, size, spacing=0.0):
    """回傳 (輪廓列表〔畫面座標，y 朝下，原點＝第一個字的基線左端〕, 總寬)"""
    cmap, gs, hm = font.getBestCmap(), font.getGlyphSet(), font['hmtx']
    s = size/font['head'].unitsPerEm
    out, x = [], 0.0
    for i, ch in enumerate(text):
        g = cmap.get(ord(ch))
        if g is None: continue
        pen = FlatPen(gs); gs[g].draw(pen)
        for c in pen.cs:
            if len(c) > 2: out.append([(x + px*s, -py*s) for px, py in c])
        x += hm[g][0]*s + (spacing if i < len(text) - 1 else 0)
    return out, x


def d_of(contours, ox=0.0, oy=0.0):
    return ''.join('M' + 'L'.join(f'{x + ox:.2f} {y + oy:.2f}' for x, y in c) + 'Z' for c in contours)


def text_path(text, font, size, x, y, fill, spacing=0.0, anchor='start', bold=0.0, extra=''):
    cs, w = shape(text, font, size, spacing)
    ox = x - (w/2 if anchor == 'middle' else w if anchor == 'end' else 0)
    st = f' stroke="{fill}" stroke-width="{bold:.2f}" stroke-linejoin="round"' if bold else ''
    return f'<path d="{d_of(cs, ox, y)}" fill="{fill}"{st}{extra}/>', w


# ---------- 字標 ----------
NAME, EN_TXT = '股立方', 'STOCK · CUBE'
TAG = '六面透視　資金・籌碼・產業・技術・事件・基本'


def extrude(contours, depth_vec, front, top, side, edge, bold, edge_w=1.4):
    """厚度：外框每一條「朝向拉伸方向」（看得見的那一側）的邊，沿 depth_vec 拉出一個四邊形；
    水平面（法向量偏上下）用 top 色、垂直面（偏左右）用 side 色；由遠到近畫，最後蓋上正面。
    TrueType 外框在 y 朝下的畫面座標裡，填色在行進方向的左邊，所以往外的法向量是 (-dy, dx)。"""
    dx_, dy_ = depth_vec
    quads = []
    for c in contours:
        n = len(c)
        for i in range(n):
            (x0, y0), (x1, y1) = c[i], c[(i + 1) % n]
            ex, ey = x1 - x0, y1 - y0
            L = math.hypot(ex, ey)
            if L < 1e-6: continue
            nx, ny = -ey/L, ex/L                       # 往外的法向量
            if nx*dx_ + ny*dy_ <= 0: continue           # 背對拉伸方向的邊看不到
            col = top if abs(ny) >= abs(nx) else side    # 法向量偏上下＝水平面（top 色）、偏左右＝垂直面（side 色）
            q = [(x0, y0), (x1, y1), (x1 + dx_, y1 + dy_), (x0 + dx_, y0 + dy_)]
            quads.append((((x0 + x1)/2*dx_ + (y0 + y1)/2*dy_), q, col))
    quads.sort(key=lambda t: -t[0])                     # 沿拉伸方向越遠的先畫
    # 第一層：整塊（背面＋所有側面＋正面）用深色畫得比較粗 → 只在最外圈留下一條收邊細線（不會在字的裡面多出一圈圈的輪廓）
    W0 = bold + edge_w*2
    quad_pts = lambda q: " ".join(f"{x:.2f},{y:.2f}" for x, y in q)
    o = [f'<g fill="{edge}" stroke="{edge}" stroke-width="{W0:.2f}" stroke-linejoin="round">'
         f'<path d="{d_of(contours, dx_, dy_)}"/>' + ''.join(f'<polygon points="{quad_pts(q)}"/>' for _, q, _ in quads) + f'<path d="{d_of(contours)}"/></g>']
    # 第二層：真正的顏色
    o.append(f'<path d="{d_of(contours, dx_, dy_)}" fill="{side}" stroke="{side}" stroke-width="{bold:.2f}" stroke-linejoin="round"/>')
    for _, q, col in quads:
        o.append(f'<polygon points="{quad_pts(q)}" fill="{col}" stroke="{col}" stroke-width="{bold:.2f}" stroke-linejoin="round"/>')
    o.append(f'<path d="{d_of(contours)}" fill="{front}" stroke="{front}" stroke-width="{bold:.2f}" stroke-linejoin="round"/>')
    return ''.join(o)


def word_A(T, size=150, spacing=26):
    """A「三面色」：平面、正面朝前的字（最好讀），往右下拉一小段厚度，像從正上方偏一點看一塊方塊字：
    正面＝立方的深色外輪廓色、朝下的面＝立方左面色、朝右的面＝立方右面色（三個面三種明暗），外面一圈深色細線收邊。"""
    cs, w = shape(NAME, ZH, size, spacing)
    d = size*.085
    g = extrude(cs, (d, d), T['rim_dark'], T['left'], T['right'], T['rim_dark'], bold=size*.035, edge_w=.9)
    return g, w, size


def word_B(T, size=150, spacing=34, depth=.17):
    """B「等角立體字」：字立在立方「右面」那個平面上（x 軸 30° 往右上、y 垂直），厚度往左上（等角的另一條水平軸）拉出；
    跟立方同一個投影角度。正面深色、頂面亮、側面中間調。"""
    cs, w = shape(NAME, ZH, size, spacing)
    D = size*depth
    body = extrude(cs, (-D, -D), T['rim_dark'], T['top'], T['left'], T['rim_dark'], bold=size*.03)
    # 字形座標（x 往右、y 往下）→ 右面平面：x' = cos30·x、y' = y − 0.5x；厚度 (−D,−D) 會變成 (−cos30·D, −0.5D)… 即等角的左上水平軸
    return f'<g transform="matrix({S3:.5f} -0.5 0 1 0 0)">{body}</g>', w, size


def word_C(T, size=118, gap=26):
    """C「方框字」：每個字放進一個圓角正方框（像立方的一個面），三個框依序用立方的頂／左／右面色，深色外輪廓＋內側白色亮線"""
    box = size*1.42; r = box*.2
    o = []
    for i, (ch, k) in enumerate(zip(NAME, ('top', 'left', 'right'))):
        x = i*(box + gap)
        o.append(f'<rect x="{x - 3}" y="{-box - 3 + size*.1:.1f}" width="{box + 6:.1f}" height="{box + 6:.1f}" rx="{r + 3:.1f}" fill="{T["rim_dark"]}"/>')
        o.append(f'<rect x="{x}" y="{-box + size*.1:.1f}" width="{box:.1f}" height="{box:.1f}" rx="{r:.1f}" fill="{T[k]}"/>')
        o.append(f'<rect x="{x + 6}" y="{-box + size*.1 + 6:.1f}" width="{box - 12:.1f}" height="{box - 12:.1f}" rx="{r - 5:.1f}" fill="none" stroke="#ffffff" stroke-width="3" opacity=".85"/>')
        cs, cw = shape(ch, ZH, size)
        o.append(f'<path d="{d_of(cs, x + box/2 - cw/2, -box/2 + size*.1 + size*.36)}" fill="{T["rim_dark"]}" stroke="{T["rim_dark"]}" stroke-width="{size*.035:.1f}" stroke-linejoin="round"/>')
    return ''.join(o), 3*box + 2*gap, box


# ---------- 立方標誌 ----------
def mark_inner(key, u, cx, cy, scale):
    """把 v19 的立方（中心 248,232、R 160）搬到 (cx,cy) 並縮放；id 加前綴 u"""
    T = THEMES[key]
    c, _ = v19.cube(u, T)
    return v19.defs(u, T) + f'<g transform="translate({cx} {cy}) scale({scale}) translate({-v19.CX} {-v19.CY})">{c}</g>'


def svg(w, h, body, bg='#ffffff'):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}"><rect width="{w}" height="{h}" fill="{bg}"/>{body}</svg>'


def mark(key):
    # 立方含外緣高約 2R+RIM = 333、落影再往下 ~20；放大 1.2 倍 → 約 400／512，四周留 ~50
    return svg(512, 512, mark_inner(key, 'm' + key[:2], 256, 248, 1.2))


def wordmark(kind, key='pro'):
    T = THEMES[key]
    if kind == 'A':
        g, w, s = word_A(T); W_, H_ = int(w + 140), 300
        body = f'<g transform="translate({(W_ - w)/2 - 5:.1f} 197)">{g}</g>'
    elif kind == 'B':
        g, w, s = word_B(T)
        cs, _ = shape(NAME, ZH, s, 34); D = s*.17
        pts_ = [(x + dx, y + dy) for c in cs for x, y in c for dx, dy in ((0, 0), (-D, -D))]
        tp = [(S3*x, y - .5*x) for x, y in pts_]
        x0, x1 = min(p[0] for p in tp), max(p[0] for p in tp); y0, y1 = min(p[1] for p in tp), max(p[1] for p in tp)
        W_, H_ = int(x1 - x0 + 160), int(y1 - y0 + 140)
        body = f'<g transform="translate({80 - x0:.1f} {70 - y0:.1f})">{g}</g>'
    else:
        g, w, box = word_C(T); W_, H_ = int(w + 120), int(box + 120)
        body = f'<g transform="translate(60 {60 + box - 118*.1:.1f})">{g}</g>'
    return svg(W_, H_, body), (W_, H_)


def sub_lines(T, x, y, width, anchor='start', en_size=34, tag_size=25):
    ink = T['rim_dark']; sub = T['accent_dark']
    o = []
    en, ew = text_path(EN_TXT, EN, en_size, x if anchor == 'start' else x, y, ink, spacing=en_size*.42, anchor=anchor)
    o.append(en)
    ry = y + en_size*.62
    x0 = x if anchor == 'start' else x - width/2
    o.append(f'<path d="M{x0:.1f} {ry:.1f}H{x0 + width:.1f}" stroke="{sub}" stroke-width="2" opacity=".55"/>')
    tg, tw = text_path(TAG, ZH, tag_size, x, ry + tag_size*1.55, ink, spacing=tag_size*.12, anchor=anchor, bold=tag_size*.03)
    o.append(tg)
    return ''.join(o), max(ew, tw)


def lockup_h(key):
    T = THEMES[key]; u = 'h' + key[:2]
    W_, H_ = 1360, 520
    g, w, s = word_A(T, size=170, spacing=30)
    x = 520
    body = mark_inner(key, u, 255, 258, 1.08)
    body += f'<g transform="translate({x} 250)">{g}</g>'
    sl, sw = sub_lines(T, x - 4, 336, 770, en_size=36, tag_size=30)
    body += sl
    return svg(W_, H_, body), (W_, H_)


def lockup_v(key):
    T = THEMES[key]; u = 'v' + key[:2]
    W_, H_ = 900, 980
    g, w, s = word_A(T, size=170, spacing=34)
    body = mark_inner(key, u, 450, 296, 1.15)
    body += f'<g transform="translate({450 - w/2 + 10:.1f} 750)">{g}</g>'
    sl, sw = sub_lines(T, 450, 844, 790, anchor='middle', en_size=38, tag_size=30)
    body += sl
    return svg(W_, H_, body), (W_, H_)


# ---------- 輸出 ----------
def render(jobs, sheet):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
        pg = b.new_page()
        for name, (w, h), scale in jobs:
            pg.set_viewport_size({'width': int(w*scale), 'height': int(h*scale)})
            pg.goto('file://' + os.path.join(HERE, name + '.svg')); pg.wait_for_timeout(200)
            pg.evaluate(f"document.documentElement.setAttribute('width','{int(w*scale)}');document.documentElement.setAttribute('height','{int(h*scale)}')")
            pg.wait_for_timeout(80)
            pg.screenshot(path=os.path.join(HERE, name + '.png'), clip={'x': 0, 'y': 0, 'width': int(w*scale), 'height': int(h*scale)})
        tmp = os.path.join(SCRATCH, '_v20_sheet.html'); open(tmp, 'w').write(sheet)
        pg.set_viewport_size({'width': 2400, 'height': 900})
        pg.goto('file://' + tmp); pg.wait_for_timeout(800)
        hh = int(pg.evaluate("Math.ceil(document.querySelector('main').getBoundingClientRect().bottom)"))
        pg.screenshot(path=os.path.join(HERE, '股立方_立方字標.png'), clip={'x': 0, 'y': 0, 'width': 2400, 'height': hh}, full_page=True)
        b.close()


def main():
    jobs = []
    def save(name, s, size, scale):
        open(os.path.join(HERE, name + '.svg'), 'w').write(s); jobs.append((name, size, scale))
    for k in ORDER:
        save(f'mark_{k}', mark(k), (512, 512), 2)
    for kind in 'ABC':
        s, size = wordmark(kind); save(f'wordmark_{kind}_pro', s, size, 1)
    for k in ORDER:
        s, size = lockup_h(k); save(f'lockup_h_{k}', s, size, 1)
    s, size = lockup_v('pro'); save('lockup_v_pro', s, size, 1)
    f = lambda n: f'file://{HERE}/{n}.svg'
    names = {k: THEMES[k]['name'] for k in ORDER}
    sheet = (f'<!doctype html><html><head><meta charset="utf-8"><style>body{{margin:0;background:#ffffff;font-family:"WenQuanYi Zen Hei",sans-serif;color:#1d2f52}}'
             f'main{{width:2400px;padding:40px 40px 50px;box-sizing:border-box}}h1{{font-size:44px;margin:0 0 6px;letter-spacing:.1em}}.en{{font-family:"DejaVu Sans";letter-spacing:.35em;font-size:16px;color:#7a5530;margin-bottom:26px}}'
             f'h2{{font-size:26px;margin:30px 0 14px;color:#7a5530;letter-spacing:.08em}}.row{{display:flex;gap:20px;align-items:flex-end}}.it{{flex:1;display:flex;flex-direction:column;align-items:center;border:1px solid #e6e2da;border-radius:18px;padding:14px 10px}}'
             f'.it img{{max-width:100%}}.it p{{margin:10px 0 0;font-size:24px;font-weight:700}}</style></head><body><main>'
             f'<h1>股立方｜只留立方＋依立方設計的字標</h1><div class="en">STOCK · CUBE // CUBE MARK + WORDMARK // 5 STYLES ON WHITE</div>'
             f'<h2>立方標誌（五種風格）</h2><div class="row">' + ''.join(f'<div class="it"><img src="{f("mark_" + k)}" width="400"><p>{names[k]}</p></div>' for k in ORDER) + '</div>'
             f'<h2>字標三案（專業配色示範）</h2><div class="row">'
             + ''.join(f'<div class="it"><img src="{f("wordmark_" + c + "_pro")}" style="height:230px"><p>{t}</p></div>' for c, t in (('A', 'A　三面色'), ('B', 'B　等角立體字'), ('C', 'C　方框字'))) + '</div>'
             f'<h2>橫式組合（字標 A，五種風格）＋直式（專業）</h2><div style="display:grid;grid-template-columns:repeat(3,1fr);gap:20px">' + ''.join(f'<div class="it"><img src="{f("lockup_h_" + k)}"><p>{names[k]}</p></div>' for k in ORDER)
             + f'<div class="it"><img src="{f("lockup_v_pro")}" style="height:420px"><p>直式（專業）</p></div></div></main></body></html>')
    render(jobs, sheet)


if __name__ == '__main__':
    main()
