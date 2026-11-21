"""短影片 k_cpo「CPO 共同封裝光學是什麼？」渲染器（直式 1080×1920、30fps、PIL 逐格算圖＋ffmpeg，不掉格）。

沿用 video_1010 的做法（逐格算圖、比比素材從 docs/anim/bibi_library/ 取、每幀登記外框做重疊檢查、
配樂用 video_1010/make_music_v3.py 從零合成），但版面是這支短片自己的四條帶，彼此不相交：
  上：段落膠囊＋大字（y 140–330）
  中：內容框（y 380–1330；示意圖／重點卡／時間軸／網站實際畫面）
  下：比比（左）＋台詞泡泡（右，尾巴只指向比比）（y 1370–1680）
  底：小字（來源／網站實際畫面・資料日）（y 1700–1780）

用法（repo 根目錄）：
    python docs/marketing/videos/2026-10-17-k_cpo/render_cpo.py            # 出片＋overlap_report.md＋字幕＋封面
    python docs/marketing/videos/2026-10-17-k_cpo/render_cpo.py --frames 12.0,30.5   # 只輸出這幾秒的單格 PNG
環境變數 CPO_SCR：中間產物（網站錄影、逐格抽圖、配樂）所在的 scratchpad 目錄；CPO_FONT_DIR：字型。
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
LIB = REPO / "docs" / "anim" / "bibi_library"
SCR = Path(os.environ.get("CPO_SCR", "/tmp/claude-0/-home-user-tw-rotation/09911d5e-cbec-5eb0-a188-19f18707f268/scratchpad/video_cpo"))
FD = Path(os.environ.get("CPO_FONT_DIR", str(SCR / "font")))
F_ROUND = str(FD / "h/package/400Regular/Huninn_400Regular.ttf")       # 粉圓（Huninn，OFL）
F_BOLD = str(FD / "n/package/700Bold/NotoSansTC_700Bold.ttf")
F_BLACK = str(FD / "n/package/900Black/NotoSansTC_900Black.ttf")
F_MED = str(FD / "n/package/500Medium/NotoSansTC_500Medium.ttf")
LOGO = REPO / "site" / "brand" / "src" / "logo_1009.jpg"

W, H, FPS = 1080, 1920, 30
TOTAL = 45.0
DATA_DATE = os.environ.get("CPO_DATA_DATE", "")

SKY = (42, 166, 245)
DEEP = (27, 111, 224)
LEMON = (255, 212, 59)
CREAM = (255, 249, 239)
INK = (26, 26, 26)
GREY = (96, 104, 116)
WHITE = (255, 255, 255)
CORAL = (232, 93, 74)
GREEN = (46, 160, 96)

CONTENT = (40, 380, 1040, 1330)         # 內容框
BIBI_FOOT = (185, 1655)                  # 比比腳底
BIBI_SIZE = 340
BUBBLE_Y = (1385, 1640)                  # 泡泡上下界
FOOT_Y = 1712                            # 小字第一行頂端
PAD = 6                                  # 重疊檢查：每個外框外擴 6px（layout_rules.md A）


# ───────────────────────── 小工具 ─────────────────────────
@lru_cache(maxsize=64)
def font(path, size):
    return ImageFont.truetype(path, size)


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_io(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def back_out(x, s=1.6):
    x = clamp(x)
    x -= 1
    return x * x * ((s + 1) * x + s) + 1


def lerp(a, b, t):
    return a + (b - a) * t


def tsize(f, s):
    b = f.getbbox(s)
    return b[2] - b[0], b[3] - b[1], b


def rmask(w, h, r):
    m = Image.new("L", (max(1, int(w)), max(1, int(h))), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, int(w) - 1, int(h) - 1], r, fill=255)
    return m


def fade(t, t0, t1, fi=0.25, fo=0.22):
    """t0 進場、t1 退場；回傳 0～1。退場在 t1 之前做完（下一段才進場，不重疊）。"""
    if t < t0 or t >= t1:
        return 0.0
    return min(clamp((t - t0) / fi), clamp((t1 - t) / fo))


# ───────────────────────── 外框登記（重疊檢查） ─────────────────────────
class Reg:
    def __init__(self):
        self.items = []     # (名稱, 群組, box)
        self.text_issues = []

    def add(self, name, box, group=None):
        x0, y0, x1, y1 = box
        if x1 - x0 < 1 or y1 - y0 < 1:
            return
        self.items.append((name, group or name, (x0, y0, x1, y1)))

    def text_in(self, name, tbox, cbox, inset=0):
        x0, y0, x1, y1 = tbox
        c0, c1, c2, c3 = cbox
        if x0 < c0 + inset - 0.5 or y0 < c1 + inset - 0.5 or x1 > c2 - inset + 0.5 or y1 > c3 - inset + 0.5:
            self.text_issues.append(f"{name} 字出框 {tuple(int(v) for v in tbox)} ⊄ {tuple(int(v) for v in cbox)}")
        if x0 < 0 or y0 < 0 or x1 > W or y1 > H:
            self.text_issues.append(f"{name} 超出畫面 {tuple(int(v) for v in tbox)}")

    def overlaps(self):
        out = []
        it = self.items
        for i in range(len(it)):
            for j in range(i + 1, len(it)):
                a, b = it[i], it[j]
                if a[1] == b[1]:
                    continue
                ax0, ay0, ax1, ay1 = a[2]
                bx0, by0, bx1, by1 = b[2]
                ix = min(ax1 + PAD, bx1 + PAD) - max(ax0 - PAD, bx0 - PAD)
                iy = min(ay1 + PAD, by1 + PAD) - max(ay0 - PAD, by0 - PAD)
                if ix > 0 and iy > 0:
                    out.append((a[0], b[0], int(ix * iy)))
        return out


# ───────────────────────── 比比 ─────────────────────────
@lru_cache(maxsize=1)
def lib_lengths():
    d = {}
    for line in (LIB / "index.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*`([a-z0-9_]+)`\s*\|.*\|\s*(\d+)\s*\|\s*([0-9.]+)\s*秒", line)
        if m:
            d[m.group(1)] = (int(m.group(2)), float(m.group(3)))
    return d


@lru_cache(maxsize=None)
def bibi_frames(name):
    im = Image.open(LIB / name / "anim.webp")
    fr = []
    for i in range(im.n_frames):
        im.seek(i)
        fr.append(im.convert("RGBA").copy())
    return fr


@lru_cache(maxsize=None)
def bibi_scaled(name, i, size):
    return bibi_frames(name)[i].resize((size, size), Image.LANCZOS)


@lru_cache(maxsize=None)
def bibi_bbox(name, i, size):
    a = np.array(bibi_scaled(name, i, size))[..., 3]
    ys, xs = np.nonzero(a > 24)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


@lru_cache(maxsize=None)
def bibi_union(name, size):
    bs = [bibi_bbox(name, i, size) for i in range(len(bibi_frames(name)))]
    return min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs)


def bibi_origin(size, foot=BIBI_FOOT):
    s = size / 512
    return int(round(foot[0] - 248 * s)), int(round(foot[1] - 482 * s))


def frame_idx(name, t):
    n, L = lib_lengths().get(name, (len(bibi_frames(name)), 1.0))
    n = len(bibi_frames(name))
    return int((t % L) / L * n) % n


def draw_bibi(cv, reg, name, t, scale=1.0, alpha=1.0):
    size = int(round(BIBI_SIZE * scale / 4) * 4)
    i = frame_idx(name, t)
    sp = bibi_scaled(name, i, size)
    if alpha < 1:
        sp = sp.copy()
        sp.putalpha(sp.getchannel("A").point(lambda v: int(v * alpha)))
    ox, oy = bibi_origin(size)
    cv.alpha_composite(sp, (ox, oy))
    b = bibi_bbox(name, i, size)
    reg.add("比比", (ox + b[0], oy + b[1], ox + b[2], oy + b[3]))


def bibi_right(names):
    """泡泡顯示期間會出現的所有比比動作的外框聯集（尾巴尖端以它為準，換動作也不會碰到）。"""
    bs = [bibi_union(n, BIBI_SIZE) for n in (names if isinstance(names, (list, tuple)) else [names])]
    b = (min(x[0] for x in bs), min(x[1] for x in bs), max(x[2] for x in bs), max(x[3] for x in bs))
    ox, oy = bibi_origin(BIBI_SIZE)
    return ox + b[2], oy + b[1], oy + b[3]


# ───────────────────────── 元件 ─────────────────────────
def paste_alpha(cv, im, xy, a):
    if a <= 0:
        return
    if a < 1:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    cv.alpha_composite(im, (int(xy[0]), int(xy[1])))


def pill(cv, reg, text, x, y, a, bg=SKY, fg=WHITE, px=34, name="段落膠囊", right=False):
    if a <= 0:
        return
    f = font(F_ROUND, px)
    tw, th, bb = tsize(f, text)
    w, h = tw + 44, px + 26
    if right:
        x = x - w
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    m = rmask(w, h, h // 2)
    im.paste(bg + (255,), (0, 0), m)
    d = ImageDraw.Draw(im)
    d.text((22 - bb[0], (h - th) / 2 - bb[1]), text, font=f, fill=fg)
    s = 0.85 + 0.15 * back_out(a)
    if s != 1:
        im2 = im.resize((max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS)
        x2, y2 = x + (w - im2.width) / 2, y + (h - im2.height) / 2
    else:
        im2, x2, y2 = im, x, y
    paste_alpha(cv, im2, (x2, y2), a)
    reg.add(name, (x2, y2, x2 + im2.width, y2 + im2.height))
    reg.text_in(name, (x + 22, y + (h - th) / 2, x + 22 + tw, y + (h - th) / 2 + th), (x, y, x + w, y + h))


def headline(cv, reg, text, y, a, px=78, color=INK, hl=None):
    """大字（單行置中）；hl＝要上黃色底線的子字串。"""
    if a <= 0:
        return
    f = font(F_ROUND, px)
    tw, th, bb = tsize(f, text)
    x = (W - tw) / 2
    dy = (1 - ease_out(a)) * 26
    im = Image.new("RGBA", (W, th + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if hl and hl in text:
        i = text.index(hl)
        pre = tsize(f, text[:i])[0] if i else 0
        hw = tsize(f, hl)[0]
        d.rounded_rectangle([x + pre - 6, th * 0.62 + 10, x + pre + hw + 6, th + 18], 10, fill=LEMON + (255,))
    d.text((x - bb[0], 10 - bb[1]), text, font=f, fill=color)
    paste_alpha(cv, im, (0, y + dy - 10), a)
    box = (x - 6, y + dy, x + tw + 6, y + dy + th + 10)
    reg.add("大字", box)
    reg.text_in("大字", (x, y, x + tw, y + th), (0, 0, W, H), inset=24)


def footnote(cv, reg, lines, a):
    if a <= 0 or not lines:
        return
    f = font(F_MED, 28)
    y = FOOT_Y
    x0s, x1s = [], []
    for ln in lines:
        tw, th, bb = tsize(f, ln)
        x = (W - tw) / 2
        im = Image.new("RGBA", (tw + 4, 40), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((-bb[0], 2 - bb[1] + 4), ln, font=f, fill=GREY)
        paste_alpha(cv, im, (x, y), a)
        reg.text_in("底部小字", (x, y, x + tw, y + 40), (0, 0, W, H), inset=30)
        x0s.append(x); x1s.append(x + tw)
        y += 42
    reg.add("底部小字", (min(x0s), FOOT_Y, max(x1s), y))


def bubble(cv, reg, text, a, bibi_name, px=44):
    """台詞泡泡：本體＋尾巴是同一個遮罩（單一封閉路徑、同一條描邊），尾巴尖端離比比外框 13px、只指向比比。"""
    if a <= 0:
        return
    f = font(F_ROUND, px)
    lines = text.split("\n")
    lh = int(px * 1.36)
    tws = [tsize(f, ln)[0] for ln in lines]
    tw = max(tws)
    th = lh * len(lines) - (lh - px)
    br, by0, by1 = bibi_right(bibi_name)
    tip_x = br + 13
    tail = 52
    bx0 = tip_x + tail
    padx, pady = 36, 30
    bw = max(tw + padx * 2, 360)
    bx1 = min(1040, bx0 + bw)
    bx0 = bx1 - bw if bx1 - bw > bx0 else bx0
    bh = th + pady * 2
    cy = (BUBBLE_Y[0] + BUBBLE_Y[1]) / 2
    ty0, ty1 = cy - bh / 2, cy + bh / 2
    tip_y = clamp(cy + 30, by0 + 60, by1 - 40)
    # 遮罩
    ox, oy = tip_x - 8, ty0 - 8
    mw, mh = int(bx1 - ox + 10), int(bh + 18)
    m = Image.new("L", (mw, mh), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([bx0 - ox, ty0 - oy, bx1 - ox, ty1 - oy], 34, fill=255)
    root_y = clamp(tip_y, ty0 + 40, ty1 - 40)
    d.polygon([(bx0 - ox + 26, root_y - oy - 30), (tip_x - ox, tip_y - oy), (bx0 - ox + 26, root_y - oy + 24)], fill=255)
    outline = m.filter(ImageFilter.MaxFilter(7))
    im = Image.new("RGBA", (mw, mh), (0, 0, 0, 0))
    im.paste(DEEP + (255,), (0, 0), outline)
    im.paste(WHITE + (255,), (0, 0), m)
    dd = ImageDraw.Draw(im)
    y = ty0 - oy + pady
    for ln, w_ in zip(lines, tws):
        bb = f.getbbox(ln)
        dd.text((bx0 - ox + (bx1 - bx0 - w_) / 2 - bb[0], y - bb[1] + (px - (bb[3] - bb[1])) / 2), ln, font=f, fill=INK)
        y += lh
    s = 0.9 + 0.1 * back_out(a)
    if s != 1:
        im2 = im.resize((max(1, int(mw * s)), max(1, int(mh * s))), Image.LANCZOS)
        # 以尾巴尖端為錨點縮放（尖端不會靠近比比）
        ax, ay = tip_x, tip_y
        px0 = ax + (ox - ax) * s
        py0 = ay + (oy - ay) * s
    else:
        im2, px0, py0 = im, ox, oy
    paste_alpha(cv, im2, (px0, py0), a)
    k = s
    tx0 = lambda x: ax + (x - ax) * k if s != 1 else x  # noqa: E731
    ty_ = lambda y_: ay + (y_ - ay) * k if s != 1 else y_  # noqa: E731
    ax, ay = tip_x, tip_y
    reg.add("泡泡", (tx0(bx0) - 3, ty_(ty0) - 3, tx0(bx1) + 3, ty_(ty1) + 3), group="泡泡")
    reg.add("泡泡尾巴", (tx0(tip_x), ty_(root_y - 30) - 3, tx0(bx0 + 26), ty_(root_y + 24) + 3), group="泡泡")
    tb = ((bx0 + bx1 - tw) / 2, ty0 + pady, (bx0 + bx1 + tw) / 2, ty0 + pady + th)
    reg.text_in("泡泡文字", tb, (bx0, ty0, bx1, ty1), inset=12)
    # 尾巴根部離文字 ≥10px
    if tb[0] - (bx0 + 26) < 10:
        reg.text_issues.append("泡泡尾巴離文字<10px")
    if tip_x - br < 12 or tip_x - br > 14:
        reg.text_issues.append(f"尾巴尖端離比比 {tip_x - br}px（應 12～14）")


def card(cv, reg, name, box, a, draw_fn, bg=WHITE, edge=SKY):
    if a <= 0:
        return
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([2, 2, w - 3, h - 3], 28, fill=bg + (255,), outline=edge + (255,), width=5)
    draw_fn(ImageDraw.Draw(im), w, h, reg, (x0, y0))
    s = 0.92 + 0.08 * back_out(a)
    im2 = im.resize((int(w * s), int(h * s)), Image.LANCZOS) if s != 1 else im
    x2, y2 = x0 + (w - im2.width) / 2, y0 + (h - im2.height) / 2
    paste_alpha(cv, im2, (x2, y2), a)
    reg.add(name, (x2, y2, x2 + im2.width, y2 + im2.height))


def text_at(d, reg, cname, xy, s, f, fill, origin, cbox_local, anchor="la"):
    """在卡片／圖內畫字並檢查不出框。xy 是卡片內座標。"""
    tw, th, bb = tsize(f, s)
    x, y = xy
    if anchor == "ma":
        x = x - tw / 2
    d.text((x - bb[0], y - bb[1]), s, font=f, fill=fill)
    ox, oy = origin
    c0, c1, c2, c3 = cbox_local
    reg.text_in(cname, (ox + x, oy + y, ox + x + tw, oy + y + th), (ox + c0, oy + c1, ox + c2, oy + c3), inset=0)
    return tw, th


# ───────────────────────── 示意圖：前面板光模組 → CPO ─────────────────────────
def diagram(cv, reg, tl, a):
    """tl＝本段開始後的秒數。0–4.4 以前；4.4–6.0 變形；6.0 起 CPO。"""
    if a <= 0:
        return
    x0, y0, x1, y1 = CONTENT
    w, h = x1 - x0, y1 - y0
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([2, 2, w - 3, h - 3], 30, fill=(250, 252, 255, 255), outline=(190, 204, 222, 255), width=4)
    u = ease_io((tl - 4.4) / 1.6)            # 0＝以前、1＝CPO
    org = (x0, y0)
    cb = (0, 0, w, h)
    f_lab = font(F_BOLD, 34)
    f_s = font(F_BOLD, 30)
    f_t = font(F_ROUND, 44)
    # 標題列
    ta = 1 - clamp((tl - 4.0) / 0.4)
    tb_ = clamp((tl - 4.5) / 0.4)
    if ta > 0:
        col = tuple(int(lerp(250, c, ta)) for c in (110, 120, 135))
        text_at(d, reg, "示意圖標題", (w / 2, 40), "以前：前面板插光模組", f_t, col, org, cb, anchor="ma")
    if tb_ > 0:
        col = tuple(int(lerp(250, c, tb_)) for c in DEEP)
        text_at(d, reg, "示意圖標題", (w / 2, 40), "CPO：光引擎搬到晶片旁", f_t, col, org, cb, anchor="ma")
    # 主機板
    d.rounded_rectangle([50, 130, 950, 770], 22, fill=(226, 242, 230), outline=(150, 196, 160), width=4)
    text_at(d, reg, "示意圖文字", (78, 716), "交換器主機板", f_s, (70, 120, 85), org, cb)
    # 前面板
    d.rounded_rectangle([880, 150, 940, 750], 10, fill=(196, 204, 214), outline=(140, 150, 160), width=3)
    # 封裝基板（CPO 才出現）
    sub = (220, 268, 580, 632)
    if u > 0:
        sa = int(255 * u)
        lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ld = ImageDraw.Draw(lay)
        ld.rounded_rectangle(sub, 18, fill=(250, 226, 170, sa), outline=(214, 164, 70, sa), width=4)
        im.alpha_composite(lay)
    # 晶片
    cx0, cy0, cx1, cy1 = 260, 360, 450, 540
    # 四顆光模組／光引擎：以前插在前面板（x 760–870），CPO 貼在晶片上下右三邊（同一塊基板）
    old = [(760, 190 + k * 140, 870, 250 + k * 140) for k in range(4)]
    new = [(305, 290, 405, 345), (472, 375, 552, 435), (472, 465, 552, 525), (305, 555, 405, 610)]
    port_old = [220 + k * 140 for k in range(4)]
    port_new = [317, 405, 495, 582]
    mods = [tuple(lerp(o[i], n_[i], u) for i in range(4)) for o, n_ in zip(old, new)]
    ports = [lerp(po, pn, u) for po, pn in zip(port_old, port_new)]

    def edge_pt(r, tx, ty):
        """從矩形 r 中心往 (tx,ty) 的射線與邊框交點。"""
        cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
        dx, dy = tx - cx, ty - cy
        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            return cx, cy
        hw, hh = (r[2] - r[0]) / 2, (r[3] - r[1]) / 2
        k_ = min(hw / abs(dx) if dx else 1e9, hh / abs(dy) if dy else 1e9)
        return cx + dx * k_, cy + dy * k_
    chip = (cx0, cy0, cx1, cy1)
    # 銅線（電訊號）：晶片 → 模組；以前很長、CPO 很短
    for k, mb in enumerate(mods):
        mcx, mcy = (mb[0] + mb[2]) / 2, (mb[1] + mb[3]) / 2
        p0 = edge_pt(chip, mcx, mcy)
        p1 = edge_pt(mb, (cx0 + cx1) / 2, (cy0 + cy1) / 2)
        d.line([p0, p1], fill=(230, 126, 34), width=8)
    # 光纖：模組右緣 → 前面板 → 機器外
    for k, (mb, py) in enumerate(zip(mods, ports)):
        my = (mb[1] + mb[3]) / 2
        d.line([(mb[2], my), (880, py)], fill=(255, 190, 30), width=7)
        d.line([(940, py), (w - 14, py + (k - 1.5) * 10)], fill=(255, 190, 30), width=7)
    # 訊號脈衝：銅線上橘色、光纖上白黃色，持續往外流動
    for k, (mb, py) in enumerate(zip(mods, ports)):
        mcx, mcy = (mb[0] + mb[2]) / 2, (mb[1] + mb[3]) / 2
        p0 = edge_pt(chip, mcx, mcy)
        p1 = edge_pt(mb, (cx0 + cx1) / 2, (cy0 + cy1) / 2)
        segs = [(p0, p1, (255, 120, 0), 1.2), ((mb[2], mcy), (880, py), (255, 255, 200), 0.9), ((940, py), (w - 14, py + (k - 1.5) * 10), (255, 255, 200), 0.9)]
        for (q0, q1, col, sp) in segs:
            L = math.hypot(q1[0] - q0[0], q1[1] - q0[1])
            if L < 12:
                continue
            nd = 3 if L > 200 else 1
            for j in range(nd):
                f_ = ((tl * sp * 180 / L) + j / nd + k * 0.17) % 1.0
                xx, yy = lerp(q0[0], q1[0], f_), lerp(q0[1], q1[1], f_)
                d.ellipse([xx - 9, yy - 9, xx + 9, yy + 9], fill=col, outline=(150, 90, 0), width=2)
    d.rounded_rectangle([cx0, cy0, cx1, cy1], 16, fill=(36, 52, 71), outline=(20, 30, 44), width=3)
    f_c = font(F_BOLD, 32)
    text_at(d, reg, "示意圖文字", ((cx0 + cx1) / 2, 410), "交換器", f_c, WHITE, org, (cx0, cy0, cx1, cy1), anchor="ma")
    text_at(d, reg, "示意圖文字", ((cx0 + cx1) / 2, 452), "晶片", f_c, WHITE, org, (cx0, cy0, cx1, cy1), anchor="ma")
    for mb in mods:
        col = tuple(int(lerp(a_, b_, u)) for a_, b_ in zip((66, 140, 255), (124, 58, 237)))
        d.rounded_rectangle([int(v) for v in mb], 10, fill=col, outline=(30, 40, 90), width=3)
    # 標籤（變形時淡出淡入；彼此與圖形不重疊）
    if ta > 0 and u < 0.05:
        c_ = tuple(int(lerp(250, c, ta)) for c in (40, 70, 160))
        text_at(d, reg, "示意圖文字", (650, 140), "光模組", f_lab, c_, org, cb)
        text_at(d, reg, "示意圖文字", (500, 630), "電訊號走長路", f_lab, tuple(int(lerp(250, c, ta)) for c in (200, 100, 20)), org, cb)
    lb = clamp((tl - 6.0) / 0.4)        # 變形（4.4–6.0）結束後才出現標籤，不壓到移動中的光引擎
    if lb > 0:
        c1 = tuple(int(lerp(250, c, lb)) for c in (110, 50, 210))
        c2 = tuple(int(lerp(250, c, lb)) for c in (170, 110, 20))
        text_at(d, reg, "示意圖文字", (230, 190), "光引擎（電轉光）", f_lab, c1, org, cb)
        text_at(d, reg, "示意圖文字", (230, 648), "同一塊封裝基板", f_lab, c2, org, cb)
        text_at(d, reg, "示意圖文字", (690, 340), "光纖", f_lab, tuple(int(lerp(250, c, lb)) for c in (180, 120, 0)), org, cb)
    # 圖例（底部）
    ly = 820
    d.line([(70, ly + 20), (130, ly + 20)], fill=(230, 126, 34), width=8)
    text_at(d, reg, "示意圖文字", (145, ly), "電訊號（銅線）", f_s, (120, 90, 50), org, cb)
    d.line([(470, ly + 20), (530, ly + 20)], fill=(255, 190, 30), width=7)
    text_at(d, reg, "示意圖文字", (545, ly), "光訊號（光纖）", f_s, (120, 90, 50), org, cb)
    paste_alpha(cv, im, org, a)
    reg.add("示意圖", (x0, y0, x1, y1))


# ───────────────────────── 重點卡（為什麼要） ─────────────────────────
def card_claim(who, big, src, col):
    def fn(d, w, h, reg, org):
        f1, f2, f3 = font(F_BOLD, 36), font(F_BLACK, 66), font(F_BOLD, 28)
        cb = (14, 14, w - 14, h - 14)
        text_at(d, reg, "卡片文字", (40, 30), who, f1, GREY, org, cb)
        # 廠商說法章（右上）
        tg = "廠商說法"
        tw, th, bb = tsize(f3, tg)
        d.rounded_rectangle([w - 40 - tw - 32, 28, w - 40, 28 + th + 22], 18, fill=(255, 236, 200))
        text_at(d, reg, "卡片文字", (w - 40 - tw - 16, 28 + 11), tg, f3, (170, 100, 0), org, cb)
        text_at(d, reg, "卡片文字", (40, 92), big, f2, col, org, cb)
        text_at(d, reg, "卡片文字", (40, 196), src, f3, GREY, org, cb)
    return fn


def card_cost(d, w, h, reg, org):
    f1, f2, f3 = font(F_BOLD, 36), font(F_BLACK, 58), font(F_BOLD, 30)
    cb = (14, 14, w - 14, h - 14)
    text_at(d, reg, "卡片文字", (40, 30), "代價", f1, CORAL, org, cb)
    text_at(d, reg, "卡片文字", (40, 92), "光引擎壞了不能抽換", f2, INK, org, cb)
    text_at(d, reg, "卡片文字", (40, 190), "以前的光模組可以直接拔下來換新", f3, GREY, org, cb)


# ───────────────────────── 時間軸 ─────────────────────────
TL_NODES = [
    ("2025 年 10 月", "Broadcom 出貨", "102.4T CPO 交換器", "Broadcom 新聞稿 2025-10-08"),
    ("2026 年 7 月", "集邦：NVIDIA", "CPO 小量出貨", "集邦科技 2026-07-27"),
    ("2027～2028 年", "集邦預估", "進入放量階段", "研調預估，不是確定的事"),
]


def timeline(cv, reg, tl, a):
    x0, y0, x1, y1 = CONTENT
    if a <= 0:
        return
    # 軸線（純裝飾，和節點卡一起當作「時間軸」底圖的一部分，不和其他外層元素相交）
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    prog = ease_io(tl / 5.6)
    ly0, ly1 = y0 + 60, y1 - 60
    d.line([(110, ly0), (110, lerp(ly0, ly1, prog))], fill=SKY + (255,), width=10)
    paste_alpha(cv, lay, (0, 0), a)
    nh = 270
    gap = (y1 - y0 - 3 * nh) / 2
    for k, (when, l1, l2, src) in enumerate(TL_NODES):
        ta = clamp((tl - 0.1 - 1.8 * k) / 0.3) * a
        if ta <= 0:
            continue
        ny0 = int(y0 + k * (nh + gap))
        # 節點圓點
        dot = Image.new("RGBA", (60, 60), (0, 0, 0, 0))
        ImageDraw.Draw(dot).ellipse([4, 4, 56, 56], fill=WHITE, outline=DEEP, width=10)
        paste_alpha(cv, dot, (80, ny0 + nh / 2 - 30), ta)
        reg.add("時間軸圓點", (84, ny0 + nh / 2 - 26, 136, ny0 + nh / 2 + 26), group="時間軸線")

        def fn(dd, w, h, reg_, org, when=when, l1=l1, l2=l2, src=src, k=k):
            cb = (14, 14, w - 14, h - 14)
            f0, f1, f3 = font(F_BLACK, 40), font(F_ROUND, 48), font(F_BOLD, 26)
            tw, th, bb = tsize(f0, when)
            dd.rounded_rectangle([34, 26, 34 + tw + 36, 26 + th + 24], 20, fill=(DEEP if k < 2 else (124, 58, 237)))
            text_at(dd, reg_, "時間軸文字", (52, 38), when, f0, WHITE, org, cb)
            text_at(dd, reg_, "時間軸文字", (40, 112), l1 + " " + l2 if tsize(f1, l1 + " " + l2)[0] < w - 90 else l1, f1, INK, org, cb)
            if tsize(f1, l1 + " " + l2)[0] >= w - 90:
                text_at(dd, reg_, "時間軸文字", (40, 112 + 60), l2, f1, INK, org, cb)
            text_at(dd, reg_, "時間軸文字", (w - 40 - tsize(f3, src)[0], h - 52), src, f3, GREY, org, cb)
        card(cv, reg, f"時間軸節點{k + 1}", (160, ny0, x1, ny0 + nh), ta, fn)
    reg.add("時間軸線", (100, ly0, 140, ly1), group="時間軸線")


# ───────────────────────── 網站實際畫面 ─────────────────────────
class Clip:
    def __init__(self, path, crop_y=0):
        self.path = path
        self.crop_y = crop_y
        self.frames = sorted(Path(path).glob("*.png"))

    def get(self, t):
        if not self.frames:
            return None
        i = min(len(self.frames) - 1, max(0, int(t * FPS)))
        return self.frames[i]


@lru_cache(maxsize=8)
def site_frame(p, crop_y):
    im = Image.open(p).convert("RGB")
    x0, y0, x1, y1 = CONTENT
    w, h = x1 - x0, y1 - y0
    s = w / im.width
    ch = int(h / s)
    im = im.crop((0, crop_y, im.width, crop_y + ch)).resize((w, h), Image.LANCZOS)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(im, (0, 0), rmask(w, h, 28))
    # 細框
    ImageDraw.Draw(out).rounded_rectangle([0, 0, w - 1, h - 1], 28, outline=(180, 196, 214), width=4)
    return out


def site(cv, reg, clip, tl, a):
    if a <= 0:
        return
    p = clip.get(tl)
    if p is None:
        return
    im = site_frame(str(p), clip.crop_y)
    paste_alpha(cv, im, CONTENT[:2], a)
    reg.add("網站畫面", CONTENT)


# ───────────────────────── 開場大字、片尾 ─────────────────────────
def hook(cv, reg, tl, a):
    if a <= 0:
        return
    f1, f2, f3 = font(F_BLACK, 250), font(F_ROUND, 92), font(F_ROUND, 80)
    items = [("CPO", f1, DEEP, 470), ("共同封裝光學", f2, INK, 800), ("是什麼？", f3, CORAL, 960)]
    for k, (s, f, col, y) in enumerate(items):
        ta = clamp((tl - 0.15 - 0.35 * k) / 0.3) * a
        if ta <= 0:
            continue
        tw, th, bb = tsize(f, s)
        im = Image.new("RGBA", (tw + 40, th + 40), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((20 - bb[0], 20 - bb[1]), s, font=f, fill=col)
        sc = 0.7 + 0.3 * back_out(ta)
        im2 = im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS)
        x, yy = (W - im2.width) / 2, y + (im.height - im2.height) / 2
        paste_alpha(cv, im2, (x, yy), ta)
        reg.add(f"開場大字{k + 1}", (x + 20 * sc, yy + 20 * sc, x + im2.width - 20 * sc, yy + im2.height - 20 * sc))
        reg.text_in(f"開場大字{k + 1}", (x, yy, x + im2.width, yy + im2.height), (0, 0, W, H), inset=10)


@lru_cache(maxsize=1)
def logo(px):
    im = Image.open(LOGO).convert("RGBA").resize((px, px), Image.LANCZOS)
    im.putalpha(rmask(px, px, int(px * 0.22)))
    return im


def endcard(cv, reg, tl, a):
    if a <= 0:
        return
    la = clamp(tl / 0.35) * a
    lg = logo(380)
    sc = 0.8 + 0.2 * back_out(la)
    l2 = lg.resize((int(380 * sc), int(380 * sc)), Image.LANCZOS)
    x, y = (W - l2.width) / 2, 420 + (380 - l2.height) / 2
    paste_alpha(cv, l2, (x, y), la)
    reg.add("標誌", (x, y, x + l2.width, y + l2.height))
    f1, f2 = font(F_ROUND, 56), font(F_ROUND, 42)
    for k, (s, f, col, yy) in enumerate([("搜尋「哩股哩股」", f1, DEEP, 860), ("精選文章・矽光子題材頁", f2, INK, 950)]):
        ta = clamp((tl - 0.3 - 0.2 * k) / 0.3) * a
        if ta <= 0:
            continue
        tw, th, bb = tsize(f, s)
        im = Image.new("RGBA", (tw + 8, th + 16), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((4 - bb[0], 8 - bb[1]), s, font=f, fill=col)
        xx = (W - tw) / 2
        paste_alpha(cv, im, (xx - 4, yy - 8), ta)
        reg.add(f"片尾字{k + 1}", (xx, yy, xx + tw, yy + th))
        reg.text_in(f"片尾字{k + 1}", (xx, yy, xx + tw, yy + th), (0, 0, W, H), inset=30)
    # 免責（片尾全程 ≥3 秒）
    da = clamp((tl - 0.2) / 0.3) * a
    if da > 0:
        f3 = font(F_BOLD, 36)
        s = "本內容為公開資料整理，不構成投資建議"
        tw, th, bb = tsize(f3, s)
        bw, bh = tw + 64, th + 44
        bx, by = (W - bw) / 2, 1110
        im = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        im.paste((255, 255, 255, 255), (0, 0), rmask(bw, bh, 22))
        dd = ImageDraw.Draw(im)
        dd.rounded_rectangle([0, 0, bw - 1, bh - 1], 22, outline=(200, 206, 214), width=3)
        dd.text((32 - bb[0], 22 - bb[1]), s, font=f3, fill=INK)
        paste_alpha(cv, im, (bx, by), da)
        reg.add("免責聲明", (bx, by, bx + bw, by + bh))
        reg.text_in("免責聲明", (bx + 32, by + 22, bx + 32 + tw, by + 22 + th), (bx, by, bx + bw, by + bh), inset=10)


# ───────────────────────── 時間軸（分鏡） ─────────────────────────
SEGS = [
    # (起, 訖, 膠囊, 大字, 黃底字, 角標, 底部小字)
    (0.0, 4.0, "比比知識", "3 個重點講清楚", "3 個重點", None, ["資料來源：NVIDIA、Broadcom 新聞稿；集邦科技"]),
    (4.0, 14.0, "重點 1／3", "它是什麼？", "是什麼", "示意圖", ["示意圖：簡化結構，非實際比例"]),
    (14.0, 24.5, "重點 2／3", "為什麼要這樣做？", "為什麼", None, ["廠商說法：NVIDIA 新聞稿 2025-03-18", "Broadcom 新聞稿 2025-10-08"]),
    (24.5, 32.0, "重點 3／3", "時程到哪了？", "時程", None, ["資料來源：Broadcom 新聞稿 2025-10-08", "集邦科技 2026-07-27"]),
    (32.0, 40.5, "哩股哩股網站", "想看更多？", "更多", "網站實際畫面", None),   # 小字在 main() 補資料日
    (40.5, 45.0, None, None, None, None, None),
]

LINES = [
    (0.0, 4.0, "嗨，我是比比！\nCPO 到底是什麼？", "talk_excited"),
    (4.2, 8.6, "以前光模組插在前面板\n電訊號要先走一段長路", "talk_explain"),
    (8.8, 14.0, "CPO 把電轉光的光引擎\n搬到交換器晶片旁\n放在同一塊封裝基板上", "pointer_r"),
    (14.2, 20.6, "電訊號的路變短，比較省電\n但這些數字是廠商說的", "talk_explain"),
    (20.8, 24.5, "代價：光引擎壞了\n不能像光模組直接抽換", "face_sweat"),
    (24.7, 28.4, "2025 年 10 月\n已有 CPO 交換器出貨", "calendar"),
    (28.6, 32.0, "集邦預估\n2027～2028 年放量", "calendar"),
    (32.2, 36.8, "矽光子族群的資金熱度\n看網站「矽光子」題材頁", "point_ur"),
    (37.0, 40.5, "更多產業小知識\n在「精選文章」", "face_thinking_bulb"),
    (40.7, 45.0, "謝謝收看！\n下次見～", "face_bow"),
]

BIBI_ACTS = [(0.0, 1.6, "wave"), (1.6, 4.0, "talk_excited"), (4.0, 8.7, "talk_explain"), (8.7, 14.0, "pointer_r"),
             (14.0, 17.4, "wow"), (17.4, 20.7, "talk_explain"), (20.7, 24.5, "face_sweat"), (24.5, 32.0, "calendar"),
             (32.0, 37.0, "point_ur"), (37.0, 40.5, "face_thinking_bulb"), (40.5, 45.0, "face_bow")]


def bibi_at(t):
    for a, b, n in BIBI_ACTS:
        if a <= t < b:
            return n, t - a
    return "face_bow", t - 40.5


CLIPS = {}


def render(t):
    cv = Image.new("RGBA", (W, H), CREAM + (255,))
    # 背景：淡格線（慢慢往上飄，讓靜止段落也有一點動態）
    d = ImageDraw.Draw(cv)
    off = (t * 24) % 60
    for y in range(-60, H + 60, 60):
        d.line([(0, y - off), (W, y - off)], fill=(242, 232, 213), width=3)
    for x in range(-60, W + 60, 60):
        d.line([(x + off, 0), (x + off, H)], fill=(242, 232, 213), width=3)
    reg = Reg()
    for (s0, s1, pl, hd, hl, tag, fn) in SEGS:
        if not (s0 <= t < s1):
            continue
        a = fade(t, s0, s1)
        tl = t - s0
        if s0 == 0.0:                         # 第一格就要有完整畫面（不是空白底），開場不做淡入
            a = 1.0
            tl = t + 0.6
        else:                                 # 段落交接用硬切＋新元素彈入（第一格就已半顯示），不留空白格
            a = 1.0
            tl = t - s0 + 0.15
        if pl:
            pill(cv, reg, pl, 40, 150, clamp(tl / 0.3) * a)
        if tag:
            pill(cv, reg, tag, 1040, 150, clamp((tl - 0.2) / 0.3) * a, bg=(255, 236, 200), fg=(150, 90, 0), px=30, name="角標", right=True)
        if hd:
            headline(cv, reg, hd, 236, clamp((tl - 0.1) / 0.35) * a, hl=hl)
        footnote(cv, reg, fn if fn else (FOOT_SITE if s0 == 32.0 else None), clamp((tl - 0.2) / 0.3) * a)
        if s0 == 0.0:
            hook(cv, reg, tl, a)
        elif s0 == 4.0:
            diagram(cv, reg, tl, a)
        elif s0 == 14.0:
            ca = [clamp((tl - 0.1) / 0.25) * a, clamp((tl - 3.4) / 0.3) * a, clamp((tl - 6.9) / 0.3) * a]
            x0, y0, x1, y1 = CONTENT
            ch, gp = 290, (y1 - y0 - 3 * 290) / 2
            card(cv, reg, "重點卡1", (x0, y0, x1, y0 + ch), ca[0], card_claim("NVIDIA 稱", "省電 3.5 倍", "NVIDIA 新聞稿 2025-03-18", DEEP))
            card(cv, reg, "重點卡2", (x0, int(y0 + ch + gp), x1, int(y0 + 2 * ch + gp)), ca[1],
                 card_claim("Broadcom 稱", "光互連功耗少約 70%", "Broadcom 新聞稿 2025-10-08", DEEP))
            card(cv, reg, "重點卡3", (x0, int(y1 - ch), x1, y1), ca[2], card_cost, bg=(255, 244, 240), edge=CORAL)
        elif s0 == 24.5:
            timeline(cv, reg, tl, a)
        elif s0 == 32.0:
            if tl < 5.15:                     # 兩段網站錄影硬切（不留空框）
                site(cv, reg, CLIPS["theme"], tl - 0.15, clamp(tl / 0.3))
            else:
                site(cv, reg, CLIPS["articles"], tl - 5.15, 1.0)
        elif s0 == 40.5:
            endcard(cv, reg, tl, a)
    # 比比（片頭 0.0–0.4 彈進來）
    nm, bt = bibi_at(t)
    draw_bibi(cv, reg, nm, bt)
    for (l0, l1, txt, bn) in LINES:
        if l0 <= t < l1:
            names = [n for (a0, a1, n) in BIBI_ACTS if a0 < l1 and a1 > l0]
            bubble(cv, reg, txt, fade(t, l0, l1, 0.22, 0.18), names)
    return cv.convert("RGB"), reg


FOOT_SITE = None


def write_srt(path):
    def ts(x):
        ms = int(round(x * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    out = []
    for i, (a, b, txt, _) in enumerate(LINES, 1):
        out += [str(i), f"{ts(a)} --> {ts(b)}", txt, ""]
    out += [str(len(LINES) + 1), f"{ts(40.7)} --> {ts(45.0)}", "本內容為公開資料整理，不構成投資建議", ""]
    Path(path).write_text("\n".join(out), encoding="utf-8")


def make_cover(path):
    """封面（1080×1920）：膠囊、大字、副標、比比；同樣登記外框做重疊檢查。"""
    cv = Image.new("RGBA", (W, H), CREAM + (255,))
    d = ImageDraw.Draw(cv)
    for y in range(0, H, 60):
        d.line([(0, y), (W, y)], fill=(246, 238, 222), width=2)
    for x in range(0, W, 60):
        d.line([(x, 0), (x, H)], fill=(246, 238, 222), width=2)
    reg = Reg()
    pill(cv, reg, "比比知識", 40, 200, 1.0, px=40)
    items = [("CPO", font(F_BLACK, 300), DEEP, 340), ("是什麼？", font(F_ROUND, 150), INK, 640),
             ("共同封裝光學・3 個重點", font(F_ROUND, 64), CORAL, 870)]
    for k, (s_, f, col, y) in enumerate(items):
        tw, th, bb = tsize(f, s_)
        x = (W - tw) / 2
        if k == 2:
            d.rounded_rectangle([x - 30, y - 22, x + tw + 30, y + th + 26], 40, fill=(255, 236, 200))
        d.text((x - bb[0], y - bb[1]), s_, font=f, fill=col)
        reg.add(f"封面字{k + 1}", (x - (30 if k == 2 else 0), y - (22 if k == 2 else 0), x + tw + (30 if k == 2 else 0), y + th + (26 if k == 2 else 0)))
        reg.text_in(f"封面字{k + 1}", (x, y, x + tw, y + th), (0, 0, W, H), inset=30)
    size = 640
    i = len(bibi_frames("talk_excited")) // 2
    sp = bibi_scaled("talk_excited", i, size)
    ox, oy = int(W / 2 - 248 * size / 512), int(1560 - 482 * size / 512)
    cv.alpha_composite(sp, (ox, oy))
    b = bibi_bbox("talk_excited", i, size)
    reg.add("比比", (ox + b[0], oy + b[1], ox + b[2], oy + b[3]))
    cv.convert("RGB").save(path)
    return reg


def main():
    global FOOT_SITE
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "k_cpo_9x16.mp4"))
    ap.add_argument("--frames", default="")
    ap.add_argument("--audio", default=str(SCR / "bgm.wav"))
    ap.add_argument("--cover", action="store_true")
    a = ap.parse_args()
    meta = json.loads((SCR / "raw" / "meta.json").read_text()) if (SCR / "raw" / "meta.json").exists() else {}
    dd = DATA_DATE or meta.get("data_date", "")
    FOOT_SITE = [f"網站實際畫面・資料日 {dd}"]
    CLIPS["theme"] = Clip(SCR / "raw" / "theme", meta.get("crop", {}).get("theme", 0))
    CLIPS["articles"] = Clip(SCR / "raw" / "articles", meta.get("crop", {}).get("articles", 0))
    if a.cover:
        reg = make_cover(HERE / "k_cpo_cover.png")
        print("封面 重疊", reg.overlaps(), "字出框", reg.text_issues)
        return
    if a.frames:
        for s in a.frames.split(","):
            im, reg = render(float(s))
            p = SCR / f"f_{float(s):06.2f}.png"
            im.save(p)
            print(p, reg.overlaps(), reg.text_issues)
        return
    n = int(round(TOTAL * FPS))
    tmp = SCR / "silent.mp4"
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "17", "-preset", "medium",
                           "-pix_fmt", "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    rows, issues, nframes = [], [], 0
    samp = SCR / "samples"
    samp.mkdir(exist_ok=True)
    for i in range(n):
        t = i / FPS
        im, reg = render(t)
        ff.stdin.write(im.tobytes())
        nframes += 1
        for (x, y, area) in reg.overlaps():
            rows.append(f"| {t:6.2f} | {x} | {y} | {area} |")
        for s in reg.text_issues:
            issues.append(f"| {t:6.2f} | {s} |")
        if i % 15 == 0:                      # 每 0.5 秒存一格全解析度，給人工檢查
            im.save(samp / f"s_{t:05.1f}.png")
        if i % 60 == 0:
            print(f"{t:5.1f}s", file=sys.stderr)
    ff.stdin.close()
    ff.wait()
    rep = ["# 重疊檢查報告（render_cpo.py 每一幀自動產生）", "",
           f"- 總幀數：{nframes}（{TOTAL} 秒 × {FPS}fps）；每個外框外擴 {PAD}px 後兩兩比對（同一個泡泡的本體／尾巴算同一組）。",
           f"- 重疊：**{len(rows)} 筆**", f"- 字出框／泡泡尾巴規則：**{len(issues)} 筆**", ""]
    if rows:
        rep += ["| 秒 | 元素 A | 元素 B | 相交面積 |", "|---|---|---|---|"] + rows[:400]
    if issues:
        rep += ["", "| 秒 | 問題 |", "|---|---|"] + issues[:400]
    (HERE / "overlap_report.md").write_text("\n".join(rep) + "\n", encoding="utf-8")
    print("重疊", len(rows), "字出框", len(issues), "幀", nframes)
    if Path(a.audio).exists():
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), "-i", a.audio, "-c:v", "copy", "-c:a", "aac",
                        "-b:a", "160k", "-shortest", "-movflags", "+faststart", a.out], check=True)
    else:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), "-c:v", "copy", "-movflags", "+faststart", a.out], check=True)
    write_srt(HERE / "k_cpo_9x16.srt")


if __name__ == "__main__":
    main()
