"""ASML 財報前 IG 輪播 10 張（1080×1350）。
用法：python render_post.py  → final/slide_01..10.png、contact_sheet.png、check/layout.json
所有字取自 content.json（標題、泡泡、事實）；版面元素全部登記外框給 validate_output.py 檢查重疊。
"""
import json, os, re, sys, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, HERE + "tech")
import illus as I

FONT_DIR = "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/font/"
F_ROUND = FONT_DIR + "jf-openhuninn-2.1.ttf"
F_BLACK = FONT_DIR + "NotoSansTC-Black.ttf"
LOGO = "/home/user/tw-rotation/site/brand/src/logo_1009.jpg"
CT = json.load(open(HERE + "content.json"))
SL = {s["n"]: s for s in CT["slides"]}
FA = CT["facts"]

W, H, S = 1080, 1350, 2
def hx(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
CREAM, YEL, PEACH, CORAL = hx("FFF8EF"), hx("FFE5A3"), hx("F6B299"), hx("EC886A")
COCOA, INK, BLUE, AQUA, MINT = hx("53362F"), hx("251713"), hx("7DADDE"), hx("8EDBD4"), hx("BDE4BE")
WHITE, VIO, LILAC = (255, 255, 255), hx("9C86E0"), hx("EEE8FC")
PALE = {"yel": hx("FFF1CC"), "peach": hx("FDE3D8"), "aqua": hx("DDF5F2"), "blue": hx("E3EEF9"), "mint": hx("E6F4E6"), "lilac": LILAC}
KIND_COL = {"已確認事實": (MINT, hx("4E8B57")), "公司預估": (YEL, hx("A47512")), "市場看法": (PEACH, hx("B2523A")),
            "示意圖": (hx("CFE2F5"), hx("3F6FA3")), "原理說明": (LILAC, hx("6A55B0")), "公司規劃": (YEL, hx("A47512"))}
_fc = {}
def font(sz, path=F_ROUND):
    k = (sz, path)
    if k not in _fc: _fc[k] = ImageFont.truetype(path, int(sz * S))
    return _fc[k]


class Slide:
    def __init__(s, n):
        s.n = n; s.els = []; s.texts = []
        s.im = Image.new("RGBA", (W * S, H * S), CREAM + (255,)); s.d = ImageDraw.Draw(s.im)
        s.paper()

    # ── 登記
    def reg(s, name, box, parent=None, kind="leaf", **kw):
        s.els.append(dict(name=name, box=[round(v, 1) for v in box], parent=parent, kind=kind, **kw)); return box

    # ── 背景：研究筆記方格＋左側裝訂線（不登記）
    def paper(s):
        d = s.d; g = hx("F3E6D3")
        for x in range(36, W, 36):
            for y in range(36, H, 36):
                d.ellipse([(x - 1.6) * S, (y - 1.6) * S, (x + 1.6) * S, (y + 1.6) * S], fill=g)
        for y in range(200, 1280, 72):
            d.ellipse([12 * S, y * S, 24 * S, (y + 12) * S], fill=hx("F1DCC6"))

    # ── 基本形
    def rr(s, box, r=30, fill=WHITE, out=INK, w=4):
        s.d.rounded_rectangle([v * S for v in box], radius=r * S, fill=fill, outline=out, width=int(w * S) if out else 0)

    def shadow_box(s, box, r=30, off=8, op=40):
        m = Image.new("L", s.im.size, 0); md = ImageDraw.Draw(m)
        md.rounded_rectangle([(box[0]) * S, (box[1] + off) * S, (box[2]) * S, (box[3] + off) * S], radius=r * S, fill=op)
        m = m.filter(ImageFilter.GaussianBlur(10 * S))
        s.im.paste(Image.new("RGBA", s.im.size, COCOA + (255,)), (0, 0), m); s.d = ImageDraw.Draw(s.im)

    def card(s, name, box, fill=WHITE, out=INK, r=30, w=4, parent=None, shadow=True):
        if shadow: s.shadow_box(box, r)
        s.rr(box, r, fill, out, w); return s.reg(name, box, parent, "card")

    # ── 文字
    def lines(s, text, sz, maxw, fp=F_ROUND):
        f = font(sz, fp); out = []; NOSTART = "，。、；：！？）」』…,.;:!?)%～"
        for para in text.split("\n"):
            toks = re.findall(r"[A-Za-z0-9%/\.\-]+|.", para)
            cur = ""; ls = []
            for tk in toks:
                if cur and f.getlength(cur + tk) / S > maxw and tk[0] not in NOSTART:
                    ls.append(cur); cur = tk.lstrip()
                else: cur += tk
            ls.append(cur); out += ls
        return out

    def text(s, name, x, y, w, text, sz, color=INK, align="left", parent=None, gap=1.3, bold=1.0, fp=F_ROUND, role="body", marker=None):
        f = font(sz, fp); ls = s.lines(text, sz, w, fp); yy = y; bx0 = bx1 = None
        for ln in ls:
            lw = f.getlength(ln) / S
            xx = x if align == "left" else (x + (w - lw) / 2 if align == "center" else x + w - lw)
            if marker:
                s.d.rounded_rectangle([(xx - 6) * S, (yy + sz * 0.52) * S, (xx + lw + 6) * S, (yy + sz * 1.08) * S], radius=8 * S, fill=marker)
            s.d.text((xx * S, yy * S), ln, font=f, fill=color, stroke_width=int(bold * S * 0.5), stroke_fill=color)
            bx0 = xx if bx0 is None else min(bx0, xx); bx1 = xx + lw if bx1 is None else max(bx1, xx + lw)
            yy += sz * gap
        top = y + f.getbbox(ls[0])[1] / S
        box = (bx0, top, bx1, y + (len(ls) - 1) * sz * gap + f.getbbox(ls[-1])[3] / S)
        s.texts.append(dict(name=name, text="".join(ls), size=sz, role=role))
        return s.reg(name, box, parent, "text", size=sz)

    def text_h(s, text, sz, w, gap=1.3, fp=F_ROUND):
        n = len(s.lines(text, sz, w, fp)); return (n - 1) * sz * gap + sz * 1.05

    # ── 小標籤（事實類型）
    def tag(s, name, x, y, kind, label=None, parent=None, sz=24, right=False):
        label = label or kind
        fill, col = KIND_COL[kind.split("｜")[0] if kind in KIND_COL else "示意圖"]
        tw = font(sz).getlength(label) / S; bw = tw + 32; bh = sz + 18
        if right: x = x - bw
        box = (x, y, x + bw, y + bh)
        s.rr(box, bh / 2, fill, col, 3); s.reg(name, box, parent, "card")
        s.text(name + "_字", x + 16, y + (bh - sz) / 2 - sz * 0.1, tw + 2, label, sz, col, parent=name, bold=0.6, role="tag")
        return box

    def pill(s, name, box, fill, out, label, sz, color=INK, parent=None, bold=1.0):
        s.rr(box, (box[3] - box[1]) / 2, fill, out, 4); s.reg(name, box, parent, "card")
        tw = font(sz).getlength(label) / S
        s.text(name + "_字", box[0] + (box[2] - box[0] - tw) / 2, box[1] + (box[3] - box[1] - sz) / 2 - sz * 0.1, tw + 2, label, sz, color, parent=name, bold=bold, role="pill")
        return box

    def badge(s, name, cx, cy, r, label, fill=CORAL, parent=None, sz=None):
        s.d.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], fill=fill, outline=INK, width=int(3.5 * S))
        sz = sz or int(r * 1.15); f = font(sz, F_BLACK); tw = f.getlength(label) / S
        bb = f.getbbox(label)
        s.d.text(((cx - tw / 2) * S, cy * S - (bb[1] + bb[3]) / 2), label, font=f, fill=WHITE)
        s.texts.append(dict(name=name, text=label, size=sz, role="badge"))
        return s.reg(name, (cx - r, cy - r, cx + r, cy + r), parent, "badge")

    # ── SVG 插畫
    def svg(s, name, res, x, y, w=None, h=None, parent=None, shadow=True, kind="illus"):
        svg, vw, vh = res
        if w and not h: h = vh * w / vw
        if h and not w: w = vw * h / vh
        im = I.render(svg, w * S, h * S)
        if shadow:
            a = im.split()[3].filter(ImageFilter.GaussianBlur(7 * S)).point(lambda v: int(v * 0.22))
            sh = Image.new("RGBA", im.size, COCOA + (0,)); sh.putalpha(a)
            s.im.alpha_composite(sh, (int(x * S), int((y + 6) * S)))
        s.im.alpha_composite(im, (int(x * S), int(y * S))); s.d = ImageDraw.Draw(s.im)
        bb = im.getbbox()
        box = (x + bb[0] / S, y + bb[1] / S, x + bb[2] / S, y + bb[3] / S)
        return s.reg(name, box, parent, kind)

    # ── 比比
    def bibi(s, key, x=None, y=None, h=None, w=None, cx=None, right_edge=None, bottom_edge=None):
        im = Image.open(HERE + f"assets/bibi_{key}.png").convert("RGBA")
        if h: w = im.width * h / im.height
        else: h = im.height * w / im.width
        im = im.resize((int(w * S), int(h * S)), Image.LANCZOS)
        if cx is not None: x = cx - w / 2
        if right_edge is not None: x = right_edge - w
        if bottom_edge is not None: y = bottom_edge - h
        s.im.alpha_composite(im, (int(round(x * S)), int(round(y * S)))); s.d = ImageDraw.Draw(s.im)
        return s.reg("比比", (x, y, x + w, y + h), None, "bibi", key=key)

    def ground(s, cx, y, rx, op=50):
        m = Image.new("L", s.im.size, 0); md = ImageDraw.Draw(m)
        md.ellipse([(cx - rx) * S, (y - 12) * S, (cx + rx) * S, (y + 12) * S], fill=op)
        m = m.filter(ImageFilter.GaussianBlur(5 * S))
        s.im.paste(Image.new("RGBA", s.im.size, COCOA + (255,)), (0, 0), m); s.d = ImageDraw.Draw(s.im)
        return (cx - rx, y - 12, cx + rx, y + 12)

    def bubble(s, name, box, tail, text, sz=34, parent=None):
        """tail=(side, base, tipx, tipy)；單一封閉外框。"""
        x0, y0, x1, y1 = box; side, bp, tx, ty = tail; hw = 20
        if side == "down": pts = [(bp - hw, y1 - 6), (tx, ty), (bp + hw, y1 - 6)]
        elif side == "up": pts = [(bp - hw, y0 + 6), (tx, ty), (bp + hw, y0 + 6)]
        elif side == "left": pts = [(x0 + 6, bp - hw), (tx, ty), (x0 + 6, bp + hw)]
        else: pts = [(x1 - 6, bp - hw), (tx, ty), (x1 - 6, bp + hw)]
        m = Image.new("L", s.im.size, 0); md = ImageDraw.Draw(m)
        md.rounded_rectangle([v * S for v in box], radius=30 * S, fill=255); md.polygon([(a * S, b * S) for a, b in pts], fill=255)
        ol = m.filter(ImageFilter.MaxFilter(2 * 4 * S + 1))
        sh = ol.filter(ImageFilter.GaussianBlur(8 * S)).point(lambda v: int(v * 0.18))
        s.im.paste(Image.new("RGBA", m.size, COCOA + (255,)), (0, 8 * S), sh)
        s.im.paste(Image.new("RGBA", m.size, INK + (255,)), (0, 0), ol)
        s.im.paste(Image.new("RGBA", m.size, WHITE + (255,)), (0, 0), m); s.d = ImageDraw.Draw(s.im)
        ub = (min(x0, *[p[0] for p in pts]), min(y0, *[p[1] for p in pts]), max(x1, *[p[0] for p in pts]), max(y1, *[p[1] for p in pts]))
        s.reg(name, ub, parent, "bubble", tip=[tx, ty])
        pad = 24; th = s.text_h(text, sz, x1 - x0 - 2 * pad)
        s.text(name + "_字", x0 + pad, y0 + (y1 - y0 - th) / 2, x1 - x0 - 2 * pad, text, sz, INK, "center", parent=name, bold=0.9, role="bubble")
        return ub

    def bsize(s, text, sz, maxw, pad=24):
        ls = s.lines(text, sz, maxw - 2 * pad); w = max(font(sz).getlength(l) / S for l in ls) + 2 * pad + 6
        return w, (len(ls) - 1) * sz * 1.3 + sz * 1.05 + 2 * pad

    def arrow(s, name, x, y, length, ang=0, color=CORAL, thick=12, parent=None):
        res = I.arrow_svg(length, "#%02X%02X%02X" % color, thick)
        im = I.render(res[0], res[1] * S, res[2] * S).rotate(-ang, expand=True, resample=Image.BICUBIC)
        s.im.alpha_composite(im, (int(x * S), int(y * S))); s.d = ImageDraw.Draw(s.im)
        bb = im.getbbox(); box = (x + bb[0] / S, y + bb[1] / S, x + bb[2] / S, y + bb[3] / S)
        return s.reg(name, box, parent, "arrow")

    # ── 固定頁首／頁尾
    def header(s, title=None, tsz=62):
        lg = Image.open(LOGO).convert("RGBA")
        bb = (86, 86, 1168, 1168); lg = lg.crop(bb).resize((84 * S, 84 * S), Image.LANCZOS)
        m = Image.new("L", lg.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, lg.width - 1, lg.height - 1], radius=20 * S, fill=255)
        s.d.rounded_rectangle([38 * S, 34 * S, 126 * S, 122 * S], radius=22 * S, fill=WHITE, outline=INK, width=3 * S)
        s.im.paste(lg, (40 * S, 36 * S), m); s.d = ImageDraw.Draw(s.im)
        s.reg("LOGO", (38, 34, 126, 122), None, "logo")
        s.text("品牌字", 142, 46, 300, "哩股哩股", 36, COCOA, bold=1.6, role="brand")
        s.text("欄名", 142, 92, 300, "科技小教室", 24, hx("9A7B6E"), bold=0.4, role="brand")
        s.pill("頁碼", (900, 50, 1040, 104), WHITE, INK, f"{s.n:02d} / 10", 30, bold=0.8)
        if title:
            s.text("標題", 48, 146, 984, title, tsz, INK, bold=2.2, role="title")

    def footer(s, src, swipe=True, right_limit=1032):
        s.text("出處", 48, 1290, (right_limit - 48) - (200 if swipe else 0), "資料：" + src, 24, hx("8A6C60"), bold=0.3, role="foot")
        if swipe:
            s.text("往右滑", right_limit - 150, 1288, 150, "往右滑 ›", 28, CORAL, "right", bold=1.0, role="foot")

    def save(s):
        im = s.im.resize((W, H), Image.LANCZOS).convert("RGB")
        im.save(HERE + f"final/slide_{s.n:02d}.png"); return im


def fact(k): return FA[k]["text"]


# ═══════════════════════════════ 各頁
def s01():
    c = Slide(1); c.header(); t = SL[1]
    c.pill("欄位標", (48, 150, 400, 204), YEL, INK, "財報前・半導體小知識", 28, bold=0.8)
    c.text("標題1", 48, 226, 984, "ASML 為何是", 100, INK, bold=2.6, role="title")
    c.text("標題2", 48, 352, 984, "景氣前哨？", 100, INK, bold=2.6, role="title", marker=YEL)
    c.text("副標", 50, 484, 700, t["sub"], 40, COCOA, bold=1.0, role="sub")
    c.svg("曝光機插畫", I.euv_machine(), 24, 590, w=780)
    c.tag("示意標", 48, 1132, "示意圖", "示意圖，非實際構造")
    bw, bh = c.bsize(t["bubble"], 34, 236)
    bx0 = 1044 - bw
    c.bubble("泡泡", (bx0, 566, 1044, 566 + bh), ("down", bx0 + bw / 2, bx0 + bw / 2 + 10, 566 + bh + 34), t["bubble"], 34)
    b = c.bibi("s01", cx=922, y=740, h=210)
    # 速度線＋地面影子（騰空）
    for i, dx in enumerate((-60, 0, 60)):
        c.d.line([((922 + dx) * S, 972 * S), ((922 + dx * 0.8) * S, 1004 * S)], fill=hx("D8C3AE"), width=6 * S)
    c.reg("速度線", (858, 968, 986, 1008), None, "fx")
    c.reg("影子", c.ground(922, 1086, 96))
    c.card("事件條", (48, 1190, 1032, 1266), PALE["yel"], INK, r=24)
    c.text("事件條字", 72, 1206, 936, "2026/10/14　ASML 公布第 3 季財報（預定）", 36, INK, "center", parent="事件條", bold=1.2)
    c.footer("TechNews 2026-10-13", swipe=False)
    c.text("往右滑", 882, 1288, 150, "往右滑 ›", 28, CORAL, "right", bold=1.0, role="foot")
    return c


def s02():
    c = Slide(2); c.header(SL[2]["title"])
    clip = c.svg("剪報", I.news_clip(), 70, 236, w=940)
    c.text("剪報來源", 120, 290, 700, "TechNews 科技新報｜2026-10-13", 28, hx("8A6C60"), parent="剪報", bold=0.4)
    c.text("剪報標題", 120, 342, 820, "先台積電一步公布業績，\nASML 第三季有望獲利年增翻倍", 44, INK, parent="剪報", bold=1.8, gap=1.32)
    c.text("剪報摘要", 120, 486, 700, "ASML 預計 10 月 14 日公布第 3 季財報", 32, COCOA, parent="剪報", bold=0.6)
    c.tag("剪報標", 120, 556, "已確認事实".replace("实", "實"), "新聞標題原文", parent="剪報")
    # 時間軸
    y = 760
    c.d.rounded_rectangle([90 * S, (y - 5) * S, 990 * S, (y + 5) * S], radius=5 * S, fill=hx("E3CDB6"))
    c.reg("時間軸線", (90, y - 5, 990, y + 5), None, "line")
    nodes = [(150, "7/15", "第 2 季財報\n已公布", MINT), (400, "10/13", "新聞：\n財報前預期", PEACH),
             (650, "10/14", "第 3 季財報\n（預定）", CORAL), (900, "之後", "台積電\n公布業績", BLUE)]
    for i, (x, d, lab, col) in enumerate(nodes):
        r = 34 if i == 2 else 22
        c.badge(f"節點{i}", x, y, r, "", fill=col, parent="時間軸線")
        c.text(f"節點日{i}", x - 110, y - 90, 220, d, 40 if i == 2 else 34, INK if i == 2 else COCOA, "center", bold=1.6)
        c.text(f"節點字{i}", x - 115, y + 50, 230, lab, 30, INK, "center", bold=0.7)
    c.tag("順序標", 940, 900, "已確認事實", "順序依新聞標題", right=True)
    b = c.bibi("s02", x=56, y=966, h=290)
    bw, bh = c.bsize(SL[2]["bubble"], 34, 640)
    c.bubble("泡泡", (300, 1140, 300 + bw, 1140 + bh), ("left", 1140 + bh / 2, 252, 1176), SL[2]["bubble"], 34)
    c.card("白話卡", (290, 966, 1032, 1110), PALE["peach"], INK, r=26)
    c.text("白話卡字", 316, 984, 690, "白話：ASML 賣晶片「曝光機」，它的訂單常被拿來觀察半導體景氣。", 30, INK, parent="白話卡", bold=0.6)
    c.tag("白話標", 1012, 1060, "市場看法", right=True, parent="白話卡")
    c.footer("TechNews 2026-10-13、2026-07-15")
    return c


def s03():
    c = Slide(3); c.header(SL[3]["title"])
    card = c.card("檔案卡", (48, 236, 1032, 690), WHITE, INK, r=32)
    c.d.rounded_rectangle([48 * S, 236 * S, 1032 * S, 300 * S], radius=32 * S, fill=PALE["aqua"], outline=INK, width=4 * S)
    c.d.rectangle([52 * S, 270 * S, 1028 * S, 298 * S], fill=PALE["aqua"])
    c.d.line([48 * S, 300 * S, 1032 * S, 300 * S], fill=INK, width=4 * S)
    c.text("卡標", 80, 248, 600, "公司檔案　COMPANY FILE", 30, hx("2F7F78"), parent="檔案卡", bold=1.0)
    c.svg("夾子", I.paperclip(), 940, 214, w=44, parent="檔案卡", shadow=False)
    c.svg("機台小圖", I.euv_machine(), 66, 360, w=360, parent="檔案卡")
    rows = [("名字", "ASML 艾司摩爾"), ("成立", "1984 年"), ("總部", "荷蘭維爾德霍芬"), ("專長", "曝光機（微影設備）")]
    for i, (k, v) in enumerate(rows):
        yy = 330 + i * 76
        c.pill(f"欄{i}", (440, yy, 548, yy + 50), PALE["yel"], INK, k, 28, parent="檔案卡", bold=0.8)
        c.text(f"值{i}", 568, yy + 4, 440, v, 36, INK, parent="檔案卡", bold=1.4)
    c.tag("卡事實", 1008, 636, "已確認事實", right=True, parent="檔案卡")
    # 賣給誰
    c.text("小標", 48, 724, 600, "曝光機賣給誰？", 40, INK, bold=1.8, marker=YEL)
    items = [(I.machine_icon(), "ASML\n曝光機"), (I.fab_icon(), "晶圓廠"), (I.chip_icon(), "晶片"), (I.server_icon(), "AI 伺服器\n手機")]
    xs = [48, 306, 564, 822]
    for i, ((res), lab) in enumerate(items):
        w = 190 if i != 3 else 160
        c.svg(f"鏈圖{i}", res, xs[i] + (210 - w) / 2, 778, w=w)
        c.text(f"鏈字{i}", xs[i], 976, 210, lab, 30, INK, "center", bold=0.8)
        if i < 3: c.arrow(f"鏈箭{i}", xs[i] + 214, 848, 50)
    c.text("客戶", 48, 1064, 984, "主要客戶：台積電、三星、英特爾（多家媒體報導）", 30, COCOA, bold=0.6)
    b = c.bibi("s03", x=48, y=1104, h=160)
    bw, bh = c.bsize(SL[3]["bubble"], 32, 420)
    c.bubble("泡泡", (250, 1112, 250 + bw, 1112 + bh), ("left", 1112 + bh / 2, 222, 1170), SL[3]["bubble"], 32)
    c.card("便條", (706, 1100, 1032, 1266), PALE["yel"], INK, r=20)
    c.text("便條字", 726, 1114, 290, "EUV 曝光機目前只有 ASML 能量產", 28, INK, parent="便條", bold=0.8)
    c.tag("便條標", 1016, 1222, "市場看法", "市場普遍看法", right=True, parent="便條", sz=22)
    c.footer("TechNews 2026-09-11；TechNews、hwbusters、自由時報等")
    return c


def s04():
    c = Slide(4); c.header(SL[4]["title"], tsz=58)
    def step(i, x, y, res, lab, w=200, hl=False):
        c.svg(f"步驟圖{i}", res, x, y - 40, w=w)
        c.badge(f"步驟號{i}", x + 16, y - 20, 24, str(i), fill=CORAL if hl else BLUE)
        c.text(f"步驟字{i}", x - 10, y - 40 + w * 200 / 240 + 8, w + 20, lab, 32, INK, "center", bold=1.0)
    step(1, 60, 290, I.wafer_icon(0), "晶圓")
    step(2, 330, 290, I.wafer_icon(1), "塗上光阻")
    c.arrow("箭12", 270, 368, 56)
    c.arrow("箭23", 540, 368, 56)
    # 主角：曝光
    hero = c.card("曝光主卡", (612, 228, 1032, 760), PALE["lilac"], INK, r=32)
    c.text("主卡標", 636, 246, 380, "③ 曝光：就是這一步！", 34, hx("5A3FA8"), "center", parent="曝光主卡", bold=1.4)
    c.svg("光罩", I.reticle_icon(), 712, 306, w=220, parent="曝光主卡")
    c.text("光罩字", 636, 468, 380, "光罩＝電路圖底片", 28, INK, "center", parent="曝光主卡", bold=0.6)
    c.svg("曝光晶圓", I.wafer_icon(1, lit=True), 702, 510, w=240, parent="曝光主卡")
    c.text("曝光字", 636, 718, 380, "電路圖被投影到晶圓上", 28, INK, "center", parent="曝光主卡", bold=0.6)
    c.arrow("箭34", 800, 780, 56, ang=90)
    step(4, 780, 880, I.wafer_icon(1, pattern=True), "顯影、蝕刻", w=190)
    c.arrow("箭45", 680, 940, 56, ang=180)
    step(5, 450, 880, I.wafer_icon(3, pattern=True), "一層層重複", w=190)
    b = c.bibi("s04", x=48, y=760, h=210)
    bw, bh = c.bsize(SL[4]["bubble"], 34, 520)
    c.bubble("泡泡", (48, 590, 48 + bw, 590 + bh), ("down", 170, 180, 590 + bh + 40), SL[4]["bubble"], 34)
    c.card("說明卡", (48, 1110, 1032, 1266), WHITE, INK, r=24)
    c.text("說明字", 72, 1134, 760, "曝光機像超精密的投影機：把光罩上的電路圖，投射到塗了光阻的晶圓上。", 30, INK, parent="說明卡", bold=0.6)
    c.tag("說明標", 1012, 1214, "示意圖", "示意流程（簡化）", right=True, parent="說明卡", sz=22)
    c.footer("ASML 官網〈lithography principles〉；halbleiter.org")
    return c


def s05():
    c = Slide(5); c.header(SL[5]["title"])
    X0, Y0, WW = 48, 232, 984
    cross = c.svg("剖面", I.euv_cross(), X0, Y0, w=WW)
    sc = WW / 1000
    for n, (bx, by) in I.CROSS_BADGES.items():
        c.badge(f"剖面號{n}", X0 + bx * sc, Y0 + by * sc, 21, str(n), fill=CORAL, parent="剖面")
    c.tag("示意標", 76, 252, "示意圖", "示意圖，非實際構造", parent="剖面")
    c.pill("真空標", (X0 + 240 * sc, Y0 + 150 * sc, X0 + 400 * sc, Y0 + 150 * sc + 46), WHITE, hx("3F6FA3"), "全程真空", 26, color=hx("3F6FA3"), parent="剖面", bold=0.8)
    c.pill("放大標", (X0 + 470 * sc, Y0 + 548 * sc, X0 + 650 * sc, Y0 + 548 * sc + 44), PALE["yel"], INK, "多層膜放大", 24, parent="剖面", bold=0.8)
    leg = ["錫滴：小錫珠一顆顆落下", "雷射：精準打中錫滴", "電漿：發出 13.5 奈米 EUV 光", "收集鏡：把光聚起來",
           "反射鏡：空氣、玻璃會吸光，全程真空、只用鏡子", "光罩：反射式，帶著電路圖", "晶圓：電路圖被印上去"]
    for i, t in enumerate(leg):
        yy = 878 + i * 54
        c.badge(f"圖例號{i}", 300, yy + 18, 19, str(i + 1), fill=CORAL)
        k, v = t.split("：")
        c.text(f"圖例{i}", 332, yy, 720, f"{k}：{v}", 30 if i != 4 else 28, INK, bold=0.7 if i != 2 else 1.3,
               marker=YEL if i == 2 else None)
    bw, bh = c.bsize(SL[5]["bubble"], 34, 220)
    c.bubble("泡泡", (40, 880, 40 + bw, 880 + bh), ("down", 120, 130, 880 + bh + 30), SL[5]["bubble"], 34)
    b = c.bibi("s05", x=44, y=1040, h=220)
    c.footer("ASML 官網〈light and lasers〉；techovedas；halbleiter.org")
    return c


def s06():
    c = Slide(6); c.header(SL[6]["title"])
    c.card("光尺卡", (48, 232, 1032, 756), WHITE, INK, r=32)
    c.text("光尺標", 76, 252, 700, "用「光的尺」來比：波長越短，畫得越細", 32, INK, parent="光尺卡", bold=1.2)
    rows = [("DUV 深紫外光", "248／193 奈米", 200, BLUE), ("EUV 極紫外光", "13.5 奈米", 14, VIO), ("High-NA EUV", "13.5 奈米・收光角度更大", 14, CORAL)]
    for i, (nm, sp, per, col) in enumerate(rows):
        y = 306 + i * 128
        c.rr((70, y, 1010, y + 116), 24, PALE["blue"] if i == 0 else (LILAC if i == 1 else PALE["peach"]), None, 0)
        c.reg(f"列底{i}", (70, y, 1010, y + 116), "光尺卡", "card")
        c.text(f"列名{i}", 92, y + 16, 300, nm, 32, INK, parent=f"列底{i}", bold=1.6)
        c.text(f"列值{i}", 92, y + 66, 340, sp, 28 if i < 2 else 24, COCOA, parent=f"列底{i}", bold=0.6)
        c.svg(f"波{i}", I.wave(per, 540, 28 if i < 2 else 34, "#%02X%02X%02X" % col), 448, y + 18, w=540, parent=f"列底{i}", shadow=False)
    c.text("光尺註", 76, 702, 900, "EUV 波長比 DUV 短十四倍以上（ASML 官網）", 28, COCOA, parent="光尺卡", bold=0.5)
    # 單價
    c.text("價標", 48, 792, 600, "一台多少錢？（約）", 38, INK, bold=1.8, marker=YEL)
    bars = [("EUV（低 NA）", 1.8, "約 1.8 億美元", VIO), ("High-NA EUV", 3.8, "約 3.8 億美元\n（約 3.5 億歐元）", CORAL)]
    for i, (nm, v, lab, col) in enumerate(bars):
        y = 862 + i * 84
        c.text(f"價名{i}", 48, y + 6, 230, nm, 30, INK, bold=1.0)
        L = 120 * v
        c.rr((270, y, 270 + L, y + 56), 18, col, INK, 4); c.reg(f"價條{i}", (270, y, 270 + L, y + 56), None, "bar")
        c.text(f"價字{i}", 270 + L + 16, y + (10 if i == 0 else -6), 1032 - (270 + L + 16), lab, 28 if i == 0 else 27, INK, bold=0.8, gap=1.2)
    c.tag("價標籤", 1032, 1028, "市場看法", "各來源略有差異", right=True)
    b = c.bibi("s06", x=48, y=1062, h=200)
    c.svg("放大鏡", I.magnifier_prop(), 280, 1088, w=120)
    bw, bh = c.bsize(SL[6]["bubble"], 34, 560)
    c.bubble("泡泡", (444, 1110, 444 + bw, 1110 + bh), ("left", 1110 + bh / 2, 412, 1150), SL[6]["bubble"], 34)
    c.footer("ASML 官網；Yole Group 等（單價為約略值）")
    return c


def s07():
    c = Slide(7); c.header(SL[7]["title"])
    c.svg("瞭望塔", I.tower_icon(), 60, 250, w=260)
    c.pill("塔名", (56, 610, 330, 664), PALE["peach"], INK, "前哨站＝設備商", 28, bold=1.0)
    steps = [(I.server_icon(), "需求升溫", "例如 AI 晶片需求變多"), (I.fab_icon(), "晶圓廠規劃擴產", "要蓋新產線"),
             (I.machine_icon(), "先向設備商下單", "設備商的訂單、財報先看到"), (I.chip_icon(), "設備裝好、產能開出", "晶片之後才出貨")]
    for i, (res, h1, h2) in enumerate(steps):
        y = 236 + i * 196
        hl = (i == 2)
        c.card(f"步{i}", (380, y, 1032, y + 172), PALE["yel"] if hl else WHITE, INK, r=26)
        c.badge(f"步號{i}", 380, y + 24, 22, str(i + 1), fill=CORAL if hl else BLUE)
        c.svg(f"步圖{i}", res, 412, y + 22, h=128, parent=f"步{i}")
        c.text(f"步題{i}", 580, y + 34, 430, h1, 34, INK, parent=f"步{i}", bold=1.5)
        c.text(f"步文{i}", 580, y + 92, 430, h2, 28, COCOA, parent=f"步{i}", bold=0.5)
    c.text("先", 300, 700, 60, "先", 34, CORAL, "center", bold=1.6)
    c.arrow("時間箭", 304, 750, 200, ang=90, color=hx("E3B49E"), thick=10)
    c.text("後", 300, 960, 60, "後", 34, CORAL, "center", bold=1.6)
    c.tag("示意標", 1032, 1028, "示意圖", "因果示意，非必然", right=True)
    b = c.bibi("s07", x=48, y=760, h=180)
    bw, bh = c.bsize(SL[7]["bubble"], 34, 440)
    c.bubble("泡泡", (48, 990, 48 + bw, 990 + bh), ("up", 150, 160, 958), SL[7]["bubble"], 34)
    c.card("結論卡", (48, 1124, 1032, 1266), PALE["aqua"], INK, r=24)
    c.text("結論字", 72, 1142, 780, "所以市場常把 ASML 的訂單，當作半導體景氣的「溫度計」。", 30, INK, parent="結論卡", bold=0.8)
    c.tag("結論標", 1012, 1214, "市場看法", right=True, parent="結論卡", sz=22)
    c.footer("產業常識整理（定性說明，非預測）")
    return c


def chart_svg():
    vw, vh = 900, 470
    X0, Y0, H0 = 110, 400, 330   # 基線 y=400；130 → 高 330
    def yv(v): return Y0 - H0 * v / 130
    b = ""
    for v in (0, 25, 50, 75, 100, 125):
        b += f'<path d="M{X0},{yv(v):.1f} H860" stroke="#EADCC8" stroke-width="2" stroke-dasharray="{"" if v == 0 else "8 8"}"/>'
    bars = [(200, 75, "url(#gBlue)"), (430, 93, "url(#gAqua)")]
    for x, v, f in bars:
        b += f'<rect x="{x}" y="{yv(v):.1f}" width="130" height="{Y0 - yv(v) + 14:.1f}" rx="16" fill="{f}" stroke="{I.INK}" stroke-width="5"/>'
        b += f'<rect x="{x + 16}" y="{yv(v) + 14:.1f}" width="16" height="{(Y0 - yv(v)) * 0.6:.1f}" rx="8" fill="#FFFFFF" opacity="0.6"/>'
    x = 660
    b += f'<rect x="{x}" y="{yv(120):.1f}" width="130" height="{yv(110) - yv(120):.1f}" fill="url(#pHatch)" stroke="{I.INK}" stroke-width="4" stroke-dasharray="10 7"/>'
    b += f'<rect x="{x}" y="{yv(110):.1f}" width="130" height="{Y0 - yv(110) + 14:.1f}" rx="16" fill="url(#gYel)" stroke="{I.INK}" stroke-width="5" stroke-dasharray="14 8"/>'
    b += f'<rect x="{X0 - 10}" y="{Y0}" width="770" height="20" fill="#FFFFFF"/>'
    b += f'<path d="M{X0},{Y0} H860" stroke="{I.INK}" stroke-width="5" stroke-linecap="round"/>'
    return I._wrap(vw, vh, b), vw, vh


def s08():
    c = Slide(8); c.header(SL[8]["title"])
    c.card("圖卡", (48, 232, 1032, 846), WHITE, INK, r=32)
    c.text("圖標", 76, 252, 640, "每季淨銷售額（億歐元）", 32, INK, parent="圖卡", bold=1.3)
    c.tag("預估標", 1004, 254, "公司預估", "黃色＝公司預估區間", right=True, parent="圖卡")
    X, Y, WW = 80, 300, 900
    c.svg("長條圖", chart_svg(), X, Y, w=WW, parent="圖卡", shadow=False)
    sc = WW / 900
    def yv(v): return Y + (400 - 330 * v / 130) * sc
    for v in (0, 50, 100):
        c.text(f"軸{v}", X + 20 * sc, yv(v) - 18, 70, str(v), 24, hx("9A7B6E"), "right", parent="長條圖", bold=0.2, role="axis")
    labs = [(200, 75, "約 75", "2025 第 3 季", "實際"), (430, 93, "約 93", "2026 第 2 季", "實際"), (660, 120, "110～120", "2026 第 3 季", "公司預估")]
    for i, (bx, v, vl, xl, k) in enumerate(labs):
        cx = X + (bx + 65) * sc
        c.text(f"值{i}", cx - 110, yv(v) - 58, 220, vl, 38 if i < 2 else 36, INK, "center", parent="長條圖", bold=1.8)
        c.text(f"季{i}", cx - 110, Y + 430 * sc - 14, 220, xl, 28, INK, "center", parent="圖卡", bold=0.8)
        c.text(f"類{i}", cx - 110, Y + 430 * sc + 26, 220, k, 24, CORAL if i == 2 else hx("4E8B57"), "center", parent="圖卡", bold=0.8)
    c.text("圖註", 76, 790, 930, "預估區間不是實際結果；實際數字以 10/14 公布為準", 26, CORAL, "center", parent="圖卡", bold=0.8)
    # 下方兩格
    c.card("毛利卡", (48, 874, 520, 1112), PALE["yel"], INK, r=26)
    c.text("毛利標", 70, 890, 430, "第 3 季毛利率預估", 30, INK, "center", parent="毛利卡", bold=1.3)
    c.svg("儀表", I.gauge(55, 57), 140, 942, w=200, parent="毛利卡", shadow=False)
    c.text("毛利值", 336, 990, 180, "55%～57%", 34, CORAL, "left", parent="毛利卡", bold=1.8)
    c.text("毛利副", 336, 1040, 180, "公司預估", 24, hx("A47512"), parent="毛利卡", bold=0.6)
    c.card("觀察卡", (548, 874, 1032, 1112), PALE["aqua"], INK, r=26)
    c.text("觀察標", 570, 890, 440, "也可以對照", 30, INK, "center", parent="觀察卡", bold=1.3)
    c.text("觀察1", 574, 946, 440, "去年同期訂單 54 億歐元\n（其中 EUV 36 億）", 28, INK, parent="觀察卡", bold=0.6)
    c.text("觀察2", 574, 1034, 440, "全年預估 430～450 億歐元", 28, INK, parent="觀察卡", bold=0.6)
    b = c.bibi("s08", right_edge=1032, y=1128, h=150)
    bw, bh = c.bsize(SL[8]["bubble"], 34, 640)
    c.bubble("泡泡", (b[0] - 40 - bw, 1150, b[0] - 40, 1150 + bh), ("right", 1150 + bh / 2, b[0] - 8, 1196), SL[8]["bubble"], 34)
    c.footer("TechNews 2025-10-15、2026-07-15")
    return c


def s09():
    c = Slide(9); c.header(SL[9]["title"])
    slabs = [("gPeach", "設備：ASML 曝光機", "EUV 等先進設備"), ("gAqua", "晶圓代工：台積電等", "ASML EUV 主要客戶之一"),
             ("gYel", "晶片 → 終端產品", "AI 伺服器、手機…")]
    for i, (fid, t1, t2) in enumerate(slabs):
        y = 236 + i * 236
        box = c.svg(f"層{i}", I.iso_slab(fid, 540), 40, y, w=640)
        fx0, fy0 = 40 + 20 * 640 / 660, y + 70 * 640 / 660
        c.text(f"層題{i}", fx0 + 24, fy0 + 6, 500, t1, 34, INK, parent=f"層{i}", bold=1.6)
        c.text(f"層文{i}", fx0 + 24, fy0 + 52, 500, t2, 26, COCOA, parent=f"層{i}", bold=0.5)
        if i < 2: c.arrow(f"層箭{i}", 260, y + 172, 54, ang=90)
    c.pill("台灣標", (470, 470, 690, 520), CORAL, INK, "台灣在這層", 28, color=WHITE, bold=1.2)
    c.tag("層事實", 40, 950, "已確認事實", "客戶：多家媒體報導")
    # 產能
    c.card("產能卡", (712, 236, 1032, 960), WHITE, INK, r=28)
    c.text("產能標", 730, 254, 284, "ASML 低 NA EUV\n產能規劃", 30, INK, "center", parent="產能卡", bold=1.4)
    base = 840
    c.rr((760, base - 300, 860, base), 16, LILAC, INK, 4); c.reg("產能柱1", (760, base - 300, 860, base), "產能卡", "bar")
    c.rr((890, base - 390, 990, base), 16, CORAL, INK, 4); c.reg("產能柱2", (890, base - 390, 990, base), "產能卡", "bar")
    c.text("柱值1", 740, base - 350, 140, "約 65 台", 28, INK, "center", parent="產能卡", bold=1.2)
    c.text("柱值2", 870, base - 440, 140, "+約 30%", 30, CORAL, "center", parent="產能卡", bold=1.6)
    c.text("柱年1", 740, base + 14, 140, "2026", 28, INK, "center", parent="產能卡", bold=0.8)
    c.text("柱年2", 870, base + 14, 140, "2027 規劃", 26, INK, "center", parent="產能卡", bold=0.8)
    c.tag("產能標籤", 1016, 900, "公司規劃", "媒體引述管理層", right=True, parent="產能卡", sz=22)
    b = c.bibi("s09", x=48, y=1010, h=150)
    bw, bh = c.bsize(SL[9]["bubble"], 34, 640)
    c.bubble("泡泡", (330, 1008, 330 + bw, 1008 + bh), ("left", 1008 + bh / 2, 300, 1080), SL[9]["bubble"], 34)
    c.card("觀察卡", (48, 1176, 1032, 1266), PALE["peach"], INK, r=22)
    c.text("觀察字", 70, 1194, 760, "觀察重點：EUV 出貨步調，和先進製程擴產有關", 28, INK, parent="觀察卡", bold=0.7)
    c.tag("觀察標", 1012, 1198, "市場看法", right=True, parent="觀察卡", sz=22)
    c.footer("技術媒體引述 ASML 管理層；TechNews 等")
    return c


def s10():
    c = Slide(10); c.header(SL[10]["title"])
    c.card("筆記卡", (48, 232, 1032, 790), WHITE, INK, r=32)
    pts = [("ASML 做 EUV 曝光機", "先進晶片製造的關鍵設備", PALE["aqua"]),
           ("設備訂單先動", "所以財報常被當景氣前哨（市場看法）", PALE["yel"]),
           ("10/14 財報看什麼", "營收是否落在公司預估 110～120 億歐元", PALE["peach"])]
    for i, (h1, h2, col) in enumerate(pts):
        y = 258 + i * 174
        c.rr((72, y, 1008, y + 156), 24, col, None, 0); c.reg(f"重點底{i}", (72, y, 1008, y + 156), "筆記卡", "card")
        c.badge(f"重點號{i}", 130, y + 78, 38, str(i + 1), fill=CORAL, parent=f"重點底{i}")
        c.text(f"重點題{i}", 196, y + 22, 790, h1, 40, INK, parent=f"重點底{i}", bold=1.8)
        c.text(f"重點文{i}", 196, y + 88, 790, h2, 30, COCOA, parent=f"重點底{i}", bold=0.6)
    b = c.bibi("s10", x=780, y=812, h=226)
    bw, bh = c.bsize(SL[10]["bubble"], 34, 680)
    c.bubble("泡泡", (48, 830, 48 + bw, 830 + bh), ("right", 830 + bh / 2, 770, 900), SL[10]["bubble"], 34)
    c.pill("CTA", (48, 950, 720, 1036), CORAL, INK, "搜尋「哩股哩股」", 44, color=WHITE, bold=2.0)
    c.card("免責卡", (48, 1072, 1032, 1196), PALE["blue"], INK, r=22)
    c.text("免責字", 72, 1090, 936, CT["disclaimer"], 30, INK, parent="免責卡", bold=0.6)
    c.text("出處", 48, 1222, 984, "資料：TechNews、ASML 官網、Yole Group 等；完整出處見文案", 24, hx("8A6C60"), bold=0.3, role="foot")
    return c


ALL = [s01, s02, s03, s04, s05, s06, s07, s08, s09, s10]

if __name__ == "__main__":
    os.makedirs(HERE + "final", exist_ok=True); os.makedirs(HERE + "check", exist_ok=True)
    only = [int(a) for a in sys.argv[1:]]
    layout = {}
    if os.path.exists(HERE + "check/layout.json"): layout = json.load(open(HERE + "check/layout.json"))
    for i, fn in enumerate(ALL, 1):
        if only and i not in only: continue
        c = fn(); c.save()
        layout[str(i)] = dict(els=c.els, texts=c.texts)
        print("ok", i, len(c.els))
    json.dump(layout, open(HERE + "check/layout.json", "w"), ensure_ascii=False, indent=0)
    # 總覽
    ims = [Image.open(HERE + f"final/slide_{i:02d}.png") for i in range(1, 11)]
    T = 360; th = int(T * H / W)
    sheet = Image.new("RGB", (T * 5 + 60, th * 2 + 45), hx("EADCC8"))
    for i, im in enumerate(ims):
        sheet.paste(im.resize((T, th), Image.LANCZOS), (10 + (i % 5) * (T + 10), 15 + (i // 5) * (th + 15)))
    sheet.save(HERE + "final/contact_sheet.png")
