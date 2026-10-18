"""IG 輪播「費半為什麼一直跌？」第 1、2 頁（1080x1350）。
重跑：python3 docs/marketing/social_unit/sox_1018/make_sox_1018.py
文案只用 docs/marketing/social_unit/post_sox_1018.md；比比用 docs/anim/bibi_library 的透明 key.png。
同時輸出 overlap_report.json（逐元素外框相交檢查）。"""
import json, math, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path('/home/user/tw-rotation')
OUT = ROOT / 'docs/marketing/social_unit/sox_1018'
LIB = ROOT / 'docs/anim/bibi_library'
FONT = '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'
W, H, SS = 1080, 1350, 2          # 2 倍超取樣

CREAM = (255, 248, 238); INK = (58, 35, 24); CORAL = (240, 97, 90)
SUBINK = (110, 84, 68); BLUE_BG = (216, 235, 251); BLUE = (62, 140, 220)
PINK = (249, 207, 207); MINT = (205, 235, 216); YEL = (255, 214, 102)
WHITE = (255, 255, 255); LINE = (58, 35, 24)


def F(sz):
    return ImageFont.truetype(FONT, int(sz * SS))


class Page:
    def __init__(self, name):
        self.name = name
        self.im = Image.new('RGB', (W * SS, H * SS), CREAM)
        self.d = ImageDraw.Draw(self.im)
        self.els = []   # (id, (x0,y0,x1,y1)) 1x 座標

    def reg(self, eid, box):
        self.els.append((eid, tuple(int(round(v)) for v in box)))

    def text(self, eid, xy, s, sz, fill=INK, bold=True, anchor='la', reg=True):
        sw = (max(1, int(sz / 50 * SS)) if sz < 80 else int(sz / 38 * SS)) if bold else 0
        x, y = xy
        self.d.text((x * SS, y * SS), s, font=F(sz), fill=fill, anchor=anchor,
                    stroke_width=sw, stroke_fill=fill)
        b = self.d.textbbox((x * SS, y * SS), s, font=F(sz), anchor=anchor, stroke_width=sw)
        box = [v / SS for v in b]
        if reg:
            self.reg(eid, box)
        return box

    def multitext(self, eid, xy, parts, sz, bold=True):
        """parts=[(字串,顏色)...] 同一行多色。回傳外框。"""
        x, y = xy
        x0 = x
        for s, c in parts:
            b = self.text(eid + '_t', (x, y), s, sz, c, bold, reg=False)
            x = b[2] if False else x + self.d.textlength(s, font=F(sz)) / SS
        box = (x0, y, x, y + sz * 1.15)
        self.reg(eid, box)
        return box

    def rrect(self, eid, box, r, fill=None, outline=None, width=0, reg=True):
        x0, y0, x1, y1 = box
        self.d.rounded_rectangle([x0 * SS, y0 * SS, x1 * SS, y1 * SS], r * SS,
                                 fill=fill, outline=outline, width=int(width * SS))
        if reg:
            self.reg(eid, box)

    def circle(self, eid, cx, cy, r, fill, outline=None, width=0, reg=True):
        self.d.ellipse([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS],
                       fill=fill, outline=outline, width=int(width * SS))
        if reg:
            self.reg(eid, (cx - r, cy - r, cx + r, cy + r))

    def dash(self, eid, p0, p1, color, w=9):
        self.d.line([p0[0] * SS, p0[1] * SS, p1[0] * SS, p1[1] * SS], fill=color, width=w * SS)
        for p in (p0, p1):
            self.circle('', p[0], p[1], w / 2, color, reg=False)
        self.reg(eid, (min(p0[0], p1[0]) - w / 2, min(p0[1], p1[1]) - w / 2,
                       max(p0[0], p1[0]) + w / 2, max(p0[1], p1[1]) + w / 2))

    def bibi(self, eid, name, left, bottom, scale):
        im = Image.open(LIB / name / 'key.png').convert('RGBA')
        bb = im.getchannel('A').point(lambda a: 255 if a > 20 else 0).getbbox()
        im = im.crop(bb)
        w, h = int(im.width * scale * SS), int(im.height * scale * SS)
        im = im.resize((w, h), Image.LANCZOS)
        x, y = int(left * SS), int(bottom * SS) - h
        # 地面陰影（含入比比外框）
        sh = Image.new('RGBA', self.im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).ellipse([x + w * 0.08, y + h - 22 * SS, x + w * 0.92, y + h + 14 * SS],
                                   fill=(190, 150, 120, 70))
        self.im.paste(sh, (0, 0), sh)
        self.im.paste(im, (x, y), im)
        self.d = ImageDraw.Draw(self.im)
        self.reg(eid, (x / SS, y / SS, (x + w) / SS, (y + h) / SS + 14))
        return (x / SS, y / SS, (x + w) / SS, (y + h) / SS)

    def header(self, num, badge=True):
        self.text('brand', (54, 46), '哩股哩股', 36, INK)
        if badge:
            self.rrect('page_badge', (860, 38, 1026, 100), 31, fill=CREAM, outline=INK, width=4)
            self.d.text((943 * SS, 69 * SS), num, font=F(38), fill=INK, anchor='mm',
                        stroke_width=SS, stroke_fill=INK)
        else:
            self.text('page_no', (1026, 50), num, 36, INK, anchor='ra')

    def save(self):
        out = self.im.resize((W, H), Image.LANCZOS)
        out.save(OUT / self.name, optimize=True)


def overlap_check(page):
    hits = []
    E = page.els
    for i in range(len(E)):
        a_id, a = E[i]
        if a[0] < 24 or a[1] < 24 or a[2] > W - 24 or a[3] > H - 24:
            hits.append(f'{a_id} 超出安全邊界 {a}')
        for j in range(i + 1, len(E)):
            b_id, b = E[j]
            if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                hits.append(f'{a_id} {a} x {b_id} {b}')
    return {'page': page.name, 'elements': len(E), 'overlaps': hits, 'boxes': E}


def bubble(p, eid, box, s, sz, tail_to, tail_from_x):
    x0, y0, x1, y1 = box
    p.rrect(eid, (x0, y0, x1, y1 + 0), 36, fill=WHITE, outline=INK, width=4, reg=False)
    # 尾巴（泡泡自己的一部分）
    tx, ty = tail_to
    poly = [(tail_from_x - 26, y1 - 3), (tail_from_x + 26, y1 - 3), (tx, ty)]
    p.d.polygon([(a * SS, b * SS) for a, b in poly], fill=WHITE)
    p.d.line([(poly[0][0] * SS, poly[0][1] * SS), (tx * SS, ty * SS), (poly[1][0] * SS, poly[1][1] * SS)],
             fill=INK, width=4 * SS)
    p.d.line([(poly[0][0] + 3) * SS, (y1 - 1) * SS, (poly[1][0] - 3) * SS, (y1 - 1) * SS], fill=WHITE, width=7 * SS) if False else None
    p.d.line([((poly[0][0] + 4) * SS), (y1 - 2) * SS, (poly[1][0] - 4) * SS, (y1 - 2) * SS], fill=WHITE, width=6 * SS)
    p.reg(eid, (x0, y0, x1, ty))
    p.d.text(((x0 + x1) / 2 * SS, (y0 + y1) / 2 * SS), s, font=F(sz), fill=INK, anchor='mm',
             stroke_width=SS, stroke_fill=INK)
    # 文字外框（需落在泡泡內）
    tb = p.d.textbbox(((x0 + x1) / 2 * SS, (y0 + y1) / 2 * SS), s, font=F(sz), anchor='mm', stroke_width=SS)
    p.text_in = getattr(p, 'text_in', []) + [(eid + '_text', [v / SS for v in tb], (x0, y0, x1, y1))]


def sparkle_dashes(p, eid, cx, cy, ang0, color, n=3, r0=0, ln=34, gap=22):
    n0 = len(p.els)
    for k in range(n):
        a = math.radians(ang0 + k * 28)
        p.dash(f'{eid}{k}', (cx + math.cos(a) * (r0), cy + math.sin(a) * r0),
               (cx + math.cos(a) * (r0 + ln), cy + math.sin(a) * (r0 + ln)), color, 8)
    g = p.els[n0:]; del p.els[n0:]
    p.reg(eid, (min(b[0] for _, b in g), min(b[1] for _, b in g), max(b[2] for _, b in g), max(b[3] for _, b in g)))


def falling_chart(p, box):
    x0, y0, x1, y1 = box
    p.rrect('chart_card', box, 34, fill=WHITE, outline=INK, width=5)
    # 視窗三顆點
    for k, c in enumerate([(240, 120, 110), YEL, (130, 200, 150)]):
        p.circle('', x0 + 40 + k * 34, y0 + 36, 10, c, reg=False)
    p.d.text(((x1 - 36) * SS, (y0 + 36) * SS), '費半', font=F(30), fill=SUBINK, anchor='rm',
             stroke_width=1, stroke_fill=SUBINK)
    # 淡格線
    gx0, gy0, gx1, gy1 = x0 + 36, y0 + 84, x1 - 36, y1 - 40
    for k in range(4):
        y = gy0 + (gy1 - gy0) * k / 3
        p.d.line([gx0 * SS, y * SS, gx1 * SS, y * SS], fill=(236, 226, 214), width=3 * SS)
    # 先漲後跌的折線（手繪感：固定亂數抖動）
    random.seed(7)
    pts = [(0, .62), (.10, .50), (.18, .56), (.30, .30), (.40, .18), (.48, .12),
           (.56, .30), (.64, .26), (.74, .52), (.82, .48), (.92, .80), (1, .86)]
    xy = [(gx0 + (gx1 - gx0) * a + random.uniform(-3, 3), gy0 + (gy1 - gy0) * b + random.uniform(-3, 3)) for a, b in pts]
    # 下跌段著色區
    seg = xy[5:]
    area = seg + [(seg[-1][0], gy1), (seg[0][0], gy1)]
    p.d.polygon([(a * SS, b * SS) for a, b in area], fill=(253, 228, 226))
    p.d.line([(a * SS, b * SS) for a, b in xy[:6]], fill=BLUE, width=7 * SS, joint='curve')
    p.d.line([(a * SS, b * SS) for a, b in seg], fill=CORAL, width=8 * SS, joint='curve')
    for a, b in xy[:5:2] + seg[::2]:
        pass
    for a, b in xy:
        p.circle('', a, b, 7, WHITE, outline=(CORAL if (a, b) in seg else BLUE), width=3, reg=False)
    # 往下箭頭
    ex, ey = xy[-1]
    p.d.polygon([((ex - 20) * SS, (ey - 62) * SS), ((ex + 8) * SS, (ey - 62) * SS), ((ex + 8) * SS, (ey - 100) * SS)], fill=None) if False else None
    return


def cover():
    p = Page('p01_cover.png')
    p.header('01/10')
    # 大字（兩行，第二行重點字珊瑚色）
    p.text('title1', (540, 128), '費半為什麼', 158, INK, anchor='ma')
    p.text('title2', (540, 312), '一直跌？', 158, CORAL, anchor='ma')
    sparkle_dashes(p, 'deco_r', 905, 455, -70, YEL, n=2, r0=0, ln=36)
    sparkle_dashes(p, 'deco_l', 130, 440, 200, (120, 190, 240), n=2, r0=0, ln=36)
    # 副標與圈字膠囊
    p.text('subtitle', (540, 500), '先看 3 個常見原因', 52, INK, anchor='ma')
    cap = (250, 585, 830, 675)
    p.rrect('capsule', cap, 45, fill=BLUE_BG)
    p.d.text((540 * SS, 630 * SS), '資金・估值・消息', font=F(46), fill=INK, anchor='mm',
             stroke_width=SS, stroke_fill=INK)
    tb = p.d.textbbox((540 * SS, 630 * SS), '資金・估值・消息', font=F(46), anchor='mm', stroke_width=SS)
    p.text_in = [('capsule_text', [v / SS for v in tb], cap)]
    # 插圖區：泡泡、比比、下跌圖卡
    bubble(p, 'bubble', (52, 682, 560, 772), '先別慌，一起拆開看！', 40, (230, 798), 200)
    bb = p.bibi('bibi', 'wow', 52, 1196, 1.12)
    falling_chart(p, (452, 820, 1030, 1140))
    p.rrect('swipe_pill', (700, 1180, 1030, 1252), 36, fill=BLUE_BG)
    p.d.text((865 * SS, 1216 * SS), '向右滑 →', font=F(40), fill=INK, anchor='mm', stroke_width=SS, stroke_fill=INK)
    tb = p.d.textbbox((865 * SS, 1216 * SS), '向右滑 →', font=F(40), anchor='mm', stroke_width=SS)
    p.text_in.append(('swipe_text', [v / SS for v in tb], (700, 1180, 1030, 1252)))
    p.text('footnote', (540, 1284), '整理公開資訊，非投顧，非預測', 28, SUBINK, bold=False, anchor='ma')
    p.save()
    return p


def reasons():
    p = Page('p02_reasons.png')
    p.header('02/10', badge=False)
    p.multitext('title', (54, 128), [('先看 3 個', INK), ('常見原因', CORAL)], 112)
    sparkle_dashes(p, 'deco_r', 960, 120, -60, YEL, n=2, ln=34) if False else None
    rows = [
        ('1', PINK, '漲多了，先獲利了結', '6 月創高後，部分資金落袋、轉向其他標的。'),
        ('2', BLUE_BG, '估值與 AI 支出被重新檢視', '市場擔心投資金額大，獲利跟不跟得上。'),
        ('3', MINT, '槓桿與擁擠部位去化', '太多人站同一邊，一鬆動就加速。'),
    ]
    p.text_in = []
    y = 296
    for i, (n, col, head, desc) in enumerate(rows):
        cx, cy = 54 + 46, y + 56
        p.circle(f'num{n}', cx, cy, 46, col, outline=INK, width=3)
        p.d.text((cx * SS, (cy - 1) * SS), n, font=F(54), fill=INK, anchor='mm', stroke_width=SS, stroke_fill=INK)
        tb = p.d.textbbox((cx * SS, (cy - 1) * SS), n, font=F(54), anchor='mm', stroke_width=SS)
        p.text_in.append((f'num{n}_text', [v / SS for v in tb], (cx - 46, cy - 46, cx + 46, cy + 46)))
        p.text(f'head{n}', (176, y + 4), head, 50, INK)
        p.text(f'desc{n}', (178, y + 70), desc, 34, SUBINK, bold=False)
        y += 180
    # 比比（思考）＋提示膠囊
    p.bibi('bibi', 'face_think', 50, 1190, 1.32)
    pill = (470, 930, 1030, 1078)
    p.rrect('hint_pill', pill, 44, fill=BLUE_BG)
    p.circle('hint_icon', 528, 1004, 28, BLUE, reg=False)
    p.d.text((528 * SS, 1004 * SS), '!', font=F(40), fill=WHITE, anchor='mm', stroke_width=SS, stroke_fill=WHITE)
    b1 = p.text('hint_l1', (574, 950), '據公開媒體整理，原因不只', 31, INK, reg=False)
    b2 = p.text('hint_l2', (574, 996), '一個，也不會一次講完。', 31, INK, reg=False)
    p.text_in += [('hint_l1', b1, pill), ('hint_l2', b2, pill), ('hint_icon', (500, 976, 556, 1032), pill)]
    p.text('footnote', (540, 1270), '資料整理自公開報導，非預測，非投資建議', 28, SUBINK, bold=False, anchor='ma')
    p.save()
    return p


if __name__ == '__main__':
    rep = []
    for pg in (cover(), reasons()):
        r = overlap_check(pg)
        # 文字需落在所屬容器內（容器內元素不算重疊）
        for eid, tb, cont in getattr(pg, 'text_in', []):
            if not (tb[0] >= cont[0] and tb[1] >= cont[1] and tb[2] <= cont[2] and tb[3] <= cont[3]):
                r['overlaps'].append(f'{eid} 超出容器 {tb} / {cont}')
        rep.append(r)
        print(pg.name, '元素', r['elements'], '重疊/越界', len(r['overlaps']))
        for h in r['overlaps']:
            print('  ', h)
    (OUT / 'overlap_report.json').write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding='utf-8')
