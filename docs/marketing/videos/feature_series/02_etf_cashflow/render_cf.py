"""功能介紹影片 01：ETF —— 成片合成（網頁 1920×1080／手機 1080×1920，30fps）。

素材：capture_etf.py 錄的網站實際畫面（亮色主題、逐格算圖，游標與點擊漣漪在錄影當下畫進畫面）。
版面（沿用第 6 版宣傳片）：奶油格紙底、左上藍色膠囊＋標題（黃色螢光底線）、右上「網站實際畫面・資料日」與歷史資料提醒；
網站畫面框只放「這一句在介紹的那一塊」（鏡頭＝錄影時每一格量到的元素外框，補成畫面框比例後裁切放大，平滑跟隨）；
比比主持、台詞用對話泡泡（一泡一句、≤22 字），泡泡尾巴指向比比；不配人聲，配輕快底樂＋點擊音效。

每一幀登記所有元素外框，兩兩比對（外擴 6px）→ overlap_report.md；另外檢查：泡泡字出框、點擊落在鏡頭內、
鏡頭有沒有把介紹的區塊裁掉、來源畫面（畫面框內）連續不動的最長秒數；成片再跑 ffmpeg freezedetect。

用法：python render_etf.py --dev d|m [--frames 1.0,5.5]（只出單格）[--cover]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
import wave
from functools import lru_cache
from pathlib import Path

import cairo
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
LIB = REPO / "docs" / "anim" / "bibi_library"
SCR = Path(os.environ.get("FEAT_SCR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/feat02"))
FAST = True   # 第 2 支起一律快節奏
SPEED = 1.5   # 成片整支 1.5 倍速（Andy 10-19：「控制 1min 內，可以載 x1.5 倍」）
RAW = SCR / "raw"
FD = Path(os.environ.get("HBM_FONT_DIR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/font"))
F_BOLD = str(FD / "NotoSansTC-Bold.ttf")
F_BLACK = str(FD / "NotoSansTC-Black.ttf")
F_MED = str(FD / "NotoSansTC-Medium.ttf")
FPS = 30
PAD = 6
XF = 12            # 鏡頭之間交叉淡化 0.4 秒
END_DUR = 5.0      # 片尾卡原片 5 秒（1.5 倍後 3.3 秒 ≥ 3 秒）

ORDER = ["open", "guide", "inc", "cx", "end"]
SEC = {   # 膠囊、標題、標題重點字
    "open": ("ETF 現金流", "月配、複利，先試算", "先試算"),
    "guide": ("引導", "從首頁找到現金流試算", "現金流試算"),
    "inc": ("功能 1", "月配試算表", "月配試算表"),
    "cx": ("功能 2", "複利試算表", "複利試算表"),
    "end": ("ETF 現金流", "現金流規劃一頁試算", "一頁試算"),
}
NAV = [("inc", "月配試算表"), ("cx", "複利試算表")]
DISC = "本內容為公開資料整理，不構成任何投資建議；投資有風險，請自行判斷。"

BG = (253, 247, 236)
GRID = (238, 228, 212)
INK = (40, 33, 28)
MUTED = (110, 98, 88)
BLUE = (37, 131, 230)
BLUE_D = (22, 92, 170)
YEL = (255, 214, 64)
CORAL = (240, 112, 92)
WHITE = (255, 255, 255)


def font(p, s):
    return _font(p, int(s))


@lru_cache(maxsize=None)
def _font(p, s):
    return ImageFont.truetype(p, s)


def tsize(f, s):
    bb = f.getbbox(s)
    return bb[2] - bb[0], bb[3] - bb[1], bb


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return 0.5 - 0.5 * math.cos(math.pi * x)


def back_out(x, s=1.6):
    x = clamp(x) - 1
    return x * x * ((s + 1) * x + s) + 1


# ───────────────────────── 版面 ─────────────────────────
class L:
    pass


def layout(dev):
    o = L()
    o.dev = dev
    if dev == "d":
        o.W, o.H = 1920, 1080
        o.panel = (26, 94, 1676, 904)
        o.bibi_size = 236
        o.bibi_foot = (1800, 1070)
        o.nav = (1696, 94, 1900, 0)
        o.bub_zone = (26, 918, None, 1068)     # 泡泡在畫面框下方，右邊接尾巴指向比比
        o.bub_font = 46
        o.flip_point = True
    else:
        o.W, o.H = 1080, 1920
        o.panel = (40, 420, 1040, 1898)
        o.bibi_size = 240
        o.bibi_foot = (150, 388)
        o.nav = None
        o.bub_zone = (None, 176, 1046, 398)    # 泡泡在比比右邊，尾巴往左
        o.bub_font = 44
        o.flip_point = False
    x0, y0, x1, y1 = o.panel
    o.pw, o.ph = x1 - x0, y1 - y0
    o.asp = o.pw / o.ph
    return o


def grid_bg(o):
    im = Image.new("RGB", (o.W, o.H), BG)
    d = ImageDraw.Draw(im)
    for x in range(0, o.W, 60):
        d.line([(x, 0), (x, o.H)], fill=GRID, width=1)
    for y in range(0, o.H, 60):
        d.line([(0, y), (o.W, y)], fill=GRID, width=1)
    return im


class Reg:
    def __init__(self):
        self.items = []
        self.issues = []

    def add(self, name, box, group=None):
        x0, y0, x1, y1 = box
        if x1 - x0 >= 1 and y1 - y0 >= 1:
            self.items.append((name, group or name, (x0, y0, x1, y1)))

    def text_in(self, name, t, c, inset=0):
        if t[0] < c[0] + inset - .5 or t[1] < c[1] + inset - .5 or t[2] > c[2] - inset + .5 or t[3] > c[3] - inset + .5:
            self.issues.append(f"{name} 出框")

    def overlaps(self):
        out = []
        it = self.items
        for i in range(len(it)):
            for j in range(i + 1, len(it)):
                a, b = it[i], it[j]
                if a[1] == b[1]:
                    continue
                ix = min(a[2][2], b[2][2]) + PAD - (max(a[2][0], b[2][0]) - PAD)
                iy = min(a[2][3], b[2][3]) + PAD - (max(a[2][1], b[2][1]) - PAD)
                if ix > 0 and iy > 0:
                    out.append((a[0], b[0], int(ix * iy)))
        return out


def header(o, im, reg, sid, data_date):
    """上方：藍色膠囊＋標題（黃色螢光底線）＋右上資料說明。回傳登記項目。"""
    d = ImageDraw.Draw(im, "RGBA")
    pill, title, hl = SEC[sid]
    if o.dev == "d":
        fp, ft, fs = font(F_BOLD, 26), font(F_BLACK, 44), font(F_MED, 21)
        px, py, ph = 40, 20, 50
        ty = 18
        tx_gap = 22
    else:
        fp, ft, fs = font(F_BOLD, 30), font(F_BLACK, 56), font(F_MED, 25)
        px, py, ph = 40, 30, 60
        ty = 22
        tx_gap = 24
    tw, th, bb = tsize(fp, pill)
    pw = tw + 44
    d.rounded_rectangle([px, py, px + pw, py + ph], ph // 2, fill=BLUE + (255,), outline=(20, 40, 70, 255), width=3)
    d.text((px + 22 - bb[0], py + (ph - th) / 2 - bb[1]), pill, font=fp, fill=WHITE)
    reg.add("膠囊", (px, py, px + pw, py + ph))
    x = px + pw + tx_gap
    tw2, th2, bb2 = tsize(ft, title)
    yb = py + ph / 2 - th2 / 2
    if hl in title:
        i = title.index(hl)
        hx = x + ft.getlength(title[:i])
        hw = ft.getlength(hl)
        d.rounded_rectangle([hx - 4, yb + th2 * 0.55, hx + hw + 4, yb + th2 + 6], 6, fill=YEL + (230,))
    d.text((x - bb2[0], yb - bb2[1]), title, font=ft, fill=INK)
    reg.add("標題", (x - 4, yb, x + tw2 + 4, yb + th2 + 6))
    # Andy 10-19：「後續影片都不要出現這種備註」→ 第 2 支起不放右上角的資料日／歷史資料角標（法遵由片尾免責卡承擔）

def nav(o, im, reg, sid):
    if not o.nav:
        return
    d = ImageDraw.Draw(im, "RGBA")
    x0, y0, x1, _ = o.nav
    f = font(F_BOLD, 24)
    fn = font(F_BLACK, 22)
    cur = [k for k, _ in NAV].index(sid) if sid in [k for k, _ in NAV] else (-1 if sid in ("open", "guide") else 99)
    y = y0 + 4
    for i, (k, t) in enumerate(NAV):
        on, done = i == cur, i < cur
        fill = BLUE + (255,) if on else (255, 255, 255, 235)
        d.rounded_rectangle([x0, y, x1, y + 62], 18, fill=fill, outline=(BLUE_D if on else (205, 190, 170)) + (255,), width=2)
        cx, cy = x0 + 28, y + 31
        d.ellipse([cx - 15, cy - 15, cx + 15, cy + 15], fill=(WHITE if on else (BLUE if done else (226, 214, 196))) + (255,))
        s = "✓" if done else str(i + 1)
        if done:
            d.line([(cx - 7, cy), (cx - 2, cy + 6), (cx + 8, cy - 6)], fill=WHITE, width=4)
        else:
            w_, h_, b_ = tsize(fn, s)
            d.text((cx - w_ / 2 - b_[0], cy - h_ / 2 - b_[1]), s, font=fn, fill=(BLUE_D if on else MUTED))
        w_, h_, b_ = tsize(f, t)
        tx = x0 + 52
        d.text((tx - b_[0], cy - h_ / 2 - b_[1]), t, font=f, fill=(WHITE if on else INK))
        reg.text_in("導覽字", (tx, cy - h_ / 2, tx + w_, cy + h_ / 2), (x0, y, x1, y + 62), 4)
        y += 74
    reg.add("功能導覽", (x0, y0, x1, y - 12))


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
def bibi_frames(name, size, flip):
    im = Image.open(LIB / name / "anim.webp")
    out = []
    for i in range(im.n_frames):
        im.seek(i)
        f = im.convert("RGBA").resize((size, size), Image.LANCZOS)
        if flip:
            f = f.transpose(Image.FLIP_LEFT_RIGHT)
        a = np.array(f)
        ys, xs = np.nonzero(a[..., 3] > 24)
        out.append((a, (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)))
    return out


SUBST = {"coins": "face_thinking_bulb"}   # 品牌規範：不用金錢圖示（金幣）


def act_name(o, name):
    name = SUBST.get(name, name)
    if o.dev == "m" and name.startswith("point_"):
        return "point_dr_v2"
    return name


def bibi_frame(o, name, t):
    name = act_name(o, name)
    flip = o.flip_point and name.startswith("point_")
    fr = bibi_frames(name, o.bibi_size, flip)
    n = len(fr)
    Ln = lib_lengths().get(name, (n, 1.2))[1]
    i = int((t % Ln) / Ln * n) % n
    s = o.bibi_size / 512
    fx = 248 * s
    if flip:
        fx = o.bibi_size - fx
    ox, oy = int(round(o.bibi_foot[0] - fx)), int(round(o.bibi_foot[1] - 482 * s))
    a, b = fr[i]
    return a, ox, oy, (ox + b[0], oy + b[1], ox + b[2], oy + b[3])


def bibi_extent(o, names):
    """所有會用到的動作、所有格的比比外框聯集（泡泡依這個放，保證尾巴不碰到比比）。"""
    x0 = y0 = 1e9
    x1 = y1 = -1e9
    for n in names:
        nn = act_name(o, n)
        flip = o.flip_point and nn.startswith("point_")
        for k in range(len(bibi_frames(nn, o.bibi_size, flip))):
            _a, ox, oy, b = bibi_frame(o, n, k / len(bibi_frames(nn, o.bibi_size, flip)) * lib_lengths().get(nn, (1, 1.2))[1] + 1e-4)
            x0, y0, x1, y1 = min(x0, b[0]), min(y0, b[1]), max(x1, b[2]), max(y1, b[3])
    return x0, y0, x1, y1


def blend(dst, src_rgba, ox, oy, alpha=1.0):
    h, w = src_rgba.shape[:2]
    H, W = dst.shape[:2]
    x0, y0 = max(0, ox), max(0, oy)
    x1, y1 = min(W, ox + w), min(H, oy + h)
    if x1 <= x0 or y1 <= y0:
        return
    s = src_rgba[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
    a = s[..., 3:4].astype(np.float32) / 255 * alpha
    dd = dst[y0:y1, x0:x1].astype(np.float32)
    dst[y0:y1, x0:x1] = (dd * (1 - a) + s[..., :3].astype(np.float32) * a).astype(np.uint8)


# ───────────────────────── 泡泡（單一封閉路徑：圓角框＋尾巴） ─────────────────────────
def wrap(f, text, maxw):
    if f.getlength(text) <= maxw:
        return [text]
    best = None
    for k in range(3, len(text) - 2):
        a_, b_ = text[:k].rstrip(), text[k:].lstrip()
        if b_[:1] in "，。、；：」）％%" or (a_[-1:].isascii() and a_[-1:].isalnum() and b_[:1].isascii() and b_[:1].isalnum()):
            continue
        if a_[-1:] in "「（":
            continue
        wa, wb = f.getlength(a_), f.getlength(b_)
        if wa <= maxw and wb <= maxw:
            sc = abs(wa - wb) - (60 if a_[-1:] in "，、：" else 0)
            if best is None or sc < best[0]:
                best = (sc, [a_, b_])
    return best[1] if best else None


@lru_cache(maxsize=64)
def bubble_img(dev, text, tip_x, tip_y, side, zone):
    """回傳（RGBA 陣列、左上角、泡泡框外框、尾巴外框、文字外框、問題）。zone＝可放的範圍。"""
    o = layout(dev)
    fz = o.bub_font
    zx0, zy0, zx1, zy1 = zone
    maxw = (zx1 - zx0) - 80
    for s in (fz, fz - 4, fz - 8):
        f = font(F_BOLD, s)
        lines = wrap(f, text, maxw)
        if lines:
            break
    lh = int(s * 1.38)
    tw = max(f.getlength(x) for x in lines)
    th = lh * len(lines) - (lh - s)
    bw, bh = tw + 80, max(th + 56, 96)
    tail = max(30, bh * 0.25)
    if side == "right":      # 泡泡在左、尾巴往右指向比比
        bx1 = tip_x - tail
        bx0 = max(zx0, bx1 - bw)
        by0 = zy0 + ((zy1 - zy0) - bh) / 2
    else:                    # 泡泡在右、尾巴往左
        bx0 = tip_x + tail
        bx1 = min(zx1, bx0 + bw)
        by0 = zy0 + ((zy1 - zy0) - bh) / 2
    by1 = by0 + bh
    W, H = int(zx1 - zx0 + 200), int(zy1 - zy0 + 120)
    offx, offy = zx0 - 100, zy0 - 60
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    c.translate(-offx, -offy)
    r = 30
    ty = min(max(tip_y, by0 + r + 22), by1 - r - 22)
    root0, root1 = ty - bh * 0.16, ty + bh * 0.16
    c.new_path()
    c.move_to(bx0 + r, by0)
    c.line_to(bx1 - r, by0)
    c.arc(bx1 - r, by0 + r, r, -math.pi / 2, 0)
    if side == "right":
        c.line_to(bx1, root0)
        c.curve_to(bx1 + tail * 0.35, root0 + 4, tip_x - 6, tip_y - 6, tip_x, tip_y)
        c.curve_to(bx1 + tail * 0.45, root1 - 2, bx1 + 6, root1, bx1, root1)
    c.line_to(bx1, by1 - r)
    c.arc(bx1 - r, by1 - r, r, 0, math.pi / 2)
    c.line_to(bx0 + r, by1)
    c.arc(bx0 + r, by1 - r, r, math.pi / 2, math.pi)
    if side == "left":
        c.line_to(bx0, root1)
        c.curve_to(bx0 - tail * 0.35, root1 - 4, tip_x + 6, tip_y + 6, tip_x, tip_y)
        c.curve_to(bx0 - tail * 0.45, root0 + 2, bx0 - 6, root0, bx0, root0)
    c.line_to(bx0, by0 + r)
    c.arc(bx0 + r, by0 + r, r, math.pi, 1.5 * math.pi)
    c.close_path()
    # 陰影
    c.save()
    c.translate(0, 6)
    c.set_source_rgba(0.25, 0.18, 0.12, 0.16)
    c.fill_preserve()
    c.restore()
    c.new_path()
    c.move_to(bx0 + r, by0)
    # 重畫同一條路徑（cairo 的 fill_preserve 在 translate 後已改路徑，這裡直接再走一次）
    c.line_to(bx1 - r, by0)
    c.arc(bx1 - r, by0 + r, r, -math.pi / 2, 0)
    if side == "right":
        c.line_to(bx1, root0)
        c.curve_to(bx1 + tail * 0.35, root0 + 4, tip_x - 6, tip_y - 6, tip_x, tip_y)
        c.curve_to(bx1 + tail * 0.45, root1 - 2, bx1 + 6, root1, bx1, root1)
    c.line_to(bx1, by1 - r)
    c.arc(bx1 - r, by1 - r, r, 0, math.pi / 2)
    c.line_to(bx0 + r, by1)
    c.arc(bx0 + r, by1 - r, r, math.pi / 2, math.pi)
    if side == "left":
        c.line_to(bx0, root1)
        c.curve_to(bx0 - tail * 0.35, root1 - 4, tip_x + 6, tip_y + 6, tip_x, tip_y)
        c.curve_to(bx0 - tail * 0.45, root0 + 2, bx0 - 6, root0, bx0, root0)
    c.line_to(bx0, by0 + r)
    c.arc(bx0 + r, by0 + r, r, math.pi, 1.5 * math.pi)
    c.close_path()
    c.set_source_rgb(1, 1, 1)
    c.fill_preserve()
    c.set_line_width(4)
    c.set_line_join(cairo.LINE_JOIN_ROUND)
    c.set_source_rgb(*(v / 255 for v in INK))
    c.stroke()
    surf.flush()
    arr = np.ndarray((H, surf.get_stride() // 4, 4), np.uint8, surf.get_data())[:, :W].copy()
    rgba = arr[..., [2, 1, 0, 3]].copy()
    al = rgba[..., 3:4].astype(np.float32) / 255
    rgba[..., :3] = np.clip(rgba[..., :3].astype(np.float32) / np.maximum(al, 1e-3), 0, 255).astype(np.uint8)
    im = Image.fromarray(rgba, "RGBA")
    d = ImageDraw.Draw(im)
    issues = []
    ty0 = by0 + (bh - th) / 2
    tboxes = []
    for k, s_ in enumerate(lines):
        w_ = f.getlength(s_)
        x = bx0 + (bw - w_) / 2 if len(lines) > 1 else bx0 + 40
        bb = f.getbbox(s_)
        y = ty0 + k * lh
        d.text((x - offx, y - offy - bb[1] + (s - (bb[3] - bb[1])) / 2), s_, font=f, fill=INK + (255,))
        tboxes.append((x, y, x + w_, y + s))
    tb = (min(b[0] for b in tboxes), min(b[1] for b in tboxes), max(b[2] for b in tboxes), max(b[3] for b in tboxes))
    if tb[0] < bx0 + 20 or tb[2] > bx1 - 20 or tb[1] < by0 + 12 or tb[3] > by1 - 12:
        issues.append("泡泡字出框")
    if bx0 < zx0 - .5 or bx1 > zx1 + .5:
        issues.append("泡泡超出可放範圍")
    tail_box = (bx1, root0 - 6, tip_x, root1 + 6) if side == "right" else (tip_x, root0 - 6, bx0, root1 + 6)
    # 尾巴與文字的距離 ≥ 10px
    if side == "right" and tb[2] + 10 > bx1:
        issues.append("尾巴離文字<10px")
    if side == "left" and tb[0] - 10 < bx0:
        issues.append("尾巴離文字<10px")
    return np.array(im), (int(offx), int(offy)), (bx0, by0, bx1, by1), tail_box, tb, tuple(issues), len(lines)


# ───────────────────────── 鏡頭 ─────────────────────────
def fit_cam(o, r, W0, H0, minw, content, xlim=None, ytop=0):
    x, y, w, h = r
    if o.dev == "d" and w >= W0 - 2 and h >= H0 - 2:
        x, y, w, h = content
    cx, cy = x + w / 2, y + h / 2
    tw, th = w, h
    w = max(w, minw)
    if w / max(h, 1) < o.asp:
        w = h * o.asp
    else:
        h = w / o.asp
    if w > W0:
        w, h = W0, W0 / o.asp
    if h > H0:
        h, w = H0, H0 * o.asp
    lo, hi = (0, W0) if not xlim else (max(0, xlim[0]), min(W0, xlim[1]))
    if w > hi - lo:
        w = hi - lo
        h = w / o.asp
    x = clamp(cx - w / 2, lo, hi - w)
    if h > H0 - ytop:
        h = H0 - ytop
        w = h * o.asp
        x = clamp(cx - w / 2, lo, hi - w)
    y = clamp(cy - h / 2, ytop, H0 - h)
    if r[2] >= W0 - 2 and r[3] >= H0 - 2:      # 整個視窗（捲動、抽屜）：對齊上緣
        y = ytop
    cut = (tw > w + 2) or (th > h + 2)
    return np.array([x, y, w, h], np.float64), cut


def tri(x):
    """三角波 -1～1，週期 1。"""
    x = x % 1.0
    return 4 * x - 1 if x < 0.5 else 3 - 4 * x


def drift_xy(t, o=None):
    lo = drift_xy.o
    px = 4.5 / (lo.pw * 0.01)          # 每秒要走的「振幅倍數」：4.5 畫面像素 ÷ 振幅
    py = 4.5 / (lo.ph * 0.01)
    return tri(t * px / 4 + 0.25), tri(t * py / 4 + 0.6)


def cam_track(o, meta, sid=""):
    W0, H0 = meta["size"]
    dsf = meta["dsf"]
    minw = o.pw if o.dev == "d" else o.pw   # 裁切寬度不小於畫面框寬：只縮小不放大（不糊）
    cx_ = meta.get("content_x") or [0, W0]
    xlim = [cx_[0] - 14 * dsf, cx_[1] + 14 * dsf] if o.dev == "d" else None
    content = [xlim[0], 52 * dsf, xlim[1] - xlim[0], 848 * dsf] if xlim else [0, 0, W0, H0]
    out, cuts, focus = [], [], []
    cur = None
    fcur = None
    last_id = None
    ytop = 0 if sid == "guide" else 56 * dsf   # 引導段要看得到頂欄的選單鈕
    cams_in = list(meta["cams"])
    first = next((i for i, c in enumerate(cams_in[:6]) if c[0] != 0), None)
    if first:   # 開錄第一格還沒設定鏡頭（cam_id 0）：沿用緊接著設定的鏡頭，不閃一格整頁
        cams_in[:first] = [cams_in[first]] * first
    for k, c in enumerate(cams_in):
        cid, r = c[0], c[1:]
        full = r[2] >= W0 - 2 and r[3] >= H0 - 2
        fbs = meta.get("fabs") or []
        fb = fbs[k] if k < len(fbs) else None
        if full and fb:   # 整頁鏡頭：構圖只取客服鈕以上（鏡頭避開客服鈕，不藏它）
            hh = max(200.0, fb[1] - 8 - ytop)
            lft, rgt = (xlim[0], xlim[1]) if xlim else (0, W0)
            ww = min(rgt - lft, hh * o.asp)
            hh = ww / o.asp
            r = [(lft + rgt) / 2 - ww / 2, ytop, ww, hh]
        tgt, cut = fit_cam(o, r, W0, H0, minw, content, xlim, ytop)
        if cut and not full:
            cuts.append(k)
        fr = np.array(r, np.float64) if not full else None
        if cur is None:
            cur = tgt.copy()
        else:
            a = 0.16 if cid == last_id else 0.12
            cur = cur + (tgt - cur) * a
        if fr is None:
            fcur = None
        elif fcur is None or cid != last_id and fcur is None:
            fcur = fr.copy()
        else:
            fcur = fcur + (fr - fcur) * 0.2
        last_id = cid
        out.append(cur.copy())
        focus.append(None if fcur is None else fcur.copy())
    return out, cuts, focus


# ───────────────────────── 時間軸 ─────────────────────────
def build(o, meta_all, order=None, with_end=True):
    shots = []
    t = 0.0
    for sid in (order or ORDER):
        m = meta_all.get(sid)
        if not m or not m.get("ok"):
            if os.environ.get("FEAT_PARTIAL"):
                continue
            raise SystemExit(f"缺鏡頭 {sid}")
        n = int(round(m["dur"] * FPS))
        start = t if not shots else t - XF / FPS
        shots.append(dict(sid=sid, meta=m, n=n, start=start, path=RAW / f"{o.dev}_{sid}.mp4"))
        t = start + n / FPS
    end_start = t - XF / FPS if with_end else t + 999
    total = end_start + END_DUR if with_end else t
    bubbles = []
    for s in shots:
        says = s["meta"]["says"]
        shot_end = s["start"] + s["n"] / FPS
        for i, b in enumerate(says):
            t0 = s["start"] + b["t"] + (0.25 if s["sid"] != "open" and i == 0 else 0.0)
            t1 = (s["start"] + says[i + 1]["t"]) if i + 1 < len(says) else shot_end - XF / FPS
            bubbles.append(dict(t0=t0, t1=t1 - 0.06, text=b["text"], act=b["act"], sid=s["sid"]))
    if with_end:
        bubbles.append(dict(t0=end_start + 0.2, t1=total, text="謝謝收看，我們下次見", act="face_bow", sid="__end"))
    return shots, bubbles, end_start, total


ALT = {"talk_explain_v2": "face_nod_v2", "face_nod_v2": "talk_explain_v2", "face_bow": "wave"}


def act_at(bubbles, t):
    cur = None
    for b in bubbles:
        if b["t0"] <= t:
            cur = b
    if cur is None:
        return "wave", t
    dt = t - cur["t0"]
    if dt > 2.4 and cur["act"] != "face_bow":
        k = int((dt - 2.4) // 2.2)
        name = ALT.get(cur["act"], "talk_explain_v2") if k % 2 == 0 else "talk_explain_v2"
        return name, (dt - 2.4) % 2.2
    return cur["act"], dt


def bubble_at(bubbles, t):
    for b in bubbles:
        if b["t0"] <= t < b["t1"]:
            a_in = clamp((t - b["t0"]) / 0.2)
            a_out = clamp((b["t1"] - t) / 0.12)
            return b, a_in, a_out
    return None, 0, 0


# ───────────────────────── 片尾卡 ─────────────────────────
def end_card(o, base, reg, a):
    im = Image.fromarray(base)
    d = ImageDraw.Draw(im, "RGBA")
    x0, y0, x1, y1 = o.panel
    d.rounded_rectangle([x0, y0, x1, y1], 26, fill=(255, 252, 245, int(255 * a)), outline=BLUE + (int(255 * a),), width=3)
    big = font(F_BLACK, 92 if o.dev == "d" else 84)
    s1 = "搜尋「哩股哩股」"
    w_, h_, b_ = tsize(big, s1)
    cx = (x0 + x1) / 2
    cy = y0 + (y1 - y0) * (0.30 if o.dev == "d" else 0.30)
    bx0, by0, bx1, by1 = cx - w_ / 2 - 54, cy - h_ / 2 - 36, cx + w_ / 2 + 54, cy + h_ / 2 + 36
    d.rounded_rectangle([bx0, by0 + 10, bx1, by1 + 10], 46, fill=(180, 70, 55, int(255 * a)))
    d.rounded_rectangle([bx0, by0, bx1, by1], 46, fill=CORAL + (int(255 * a),))
    d.text((cx - w_ / 2 - b_[0], cy - h_ / 2 - b_[1]), s1, font=big, fill=WHITE + (int(255 * a),))
    reg.add("搜尋鈕", (bx0, by0, bx1, by1 + 10))
    f2 = font(F_BOLD, 40 if o.dev == "d" else 40)
    s2 = "月配試算表・複利試算表"
    s2b = ""
    yy = by1 + 60
    for s in [s2]:
        w_, h_, b_ = tsize(f2, s)
        d.text((cx - w_ / 2 - b_[0], yy - b_[1]), s, font=f2, fill=INK + (int(255 * a),))
        reg.add("片尾說明", (cx - w_ / 2, yy, cx + w_ / 2, yy + h_), "片尾說明")
        yy += h_ + 22
    f3 = font(F_BOLD, 34 if o.dev == "d" else 36)
    if o.dev == "d":
        dl = [DISC]
    else:
        dl = ["本內容為公開資料整理，", "不構成任何投資建議；", "投資有風險，請自行判斷。"]
    lh = 54
    hh = lh * len(dl) - (lh - 34) + 60
    dy0 = y1 - 110 - hh if o.dev == "d" else yy + 110
    dw = max(f3.getlength(s) for s in dl) + 80
    d.rounded_rectangle([cx - dw / 2, dy0, cx + dw / 2, dy0 + hh], 22, fill=(255, 255, 255, int(255 * a)), outline=(200, 185, 165, int(255 * a)), width=2)
    yy = dy0 + 30
    for s in dl:
        w_, h_, b_ = tsize(f3, s)
        d.text((cx - w_ / 2 - b_[0], yy - b_[1]), s, font=f3, fill=INK + (int(255 * a),))
        reg.text_in("免責字", (cx - w_ / 2, yy, cx + w_ / 2, yy + h_), (cx - dw / 2, dy0, cx + dw / 2, dy0 + hh), 12)
        yy += lh
    return np.array(im)


# ───────────────────────── 主流程 ─────────────────────────
class Reader:
    def __init__(self, path):
        self.cap = cv2.VideoCapture(str(path))
        self.k = -1
        self.last = None

    def get(self, k):
        while self.k < k:
            ok, fr = self.cap.read()
            self.k += 1
            if ok:
                self.last = fr
        return self.last


def render(dev, only=None, seg=None):
    o = layout(dev)
    drift_xy.o = o
    mf = RAW / f"{dev}_meta.json"
    meta_all = json.loads(mf.read_text(encoding="utf-8")) if mf.exists() else {}
    for sid in ORDER:      # 每鏡一檔（capture_etf.py 新版），覆蓋合併檔裡的舊紀錄
        f = RAW / f"{dev}_{sid}.json"
        if f.exists():
            meta_all[sid] = json.loads(f.read_text(encoding="utf-8"))
    data_date = next(iter(meta_all.values())).get("data_date")
    etf_asof = json.loads((REPO / "site" / "data" / "etf.json").read_text(encoding="utf-8")).get("asof")
    data_date = etf_asof or data_date
    if seg:
        shots, bubbles, end_start, total = build(o, meta_all, [seg], with_end=(seg == "end"))
    else:
        shots, bubbles, end_start, total = build(o, meta_all)
    acts = {b["act"] for b in bubbles} | {ALT.get(b["act"], "talk_explain_v2") for b in bubbles} | {"talk_explain_v2", "wave", "face_nod_v2"}
    ext = bibi_extent(o, sorted(acts))
    if dev == "d":
        tip = (ext[0] - 13, (ext[1] + ext[3]) / 2 + 6)
        zone = (o.bub_zone[0], o.bub_zone[1], int(tip[0]) - 10, o.bub_zone[3])
        side = "right"
    else:
        tip = (ext[2] + 13, (ext[1] + ext[3]) / 2)
        zone = (int(tip[0]) + 10, o.bub_zone[1], o.bub_zone[2], o.bub_zone[3])
        side = "left"
    tip = (int(round(tip[0])), int(round(tip[1])))
    bg = np.array(grid_bg(o))
    # 每鏡的靜態底（背景＋上方＋導覽＋畫面框外框）
    statics = {}
    for s in shots + [dict(sid="end")]:
        im = Image.fromarray(bg.copy())
        reg = Reg()
        header(o, im, reg, s["sid"], data_date)
        nav(o, im, reg, s["sid"])
        d = ImageDraw.Draw(im)
        x0, y0, x1, y1 = o.panel
        d.rounded_rectangle([x0 - 3, y0 - 3, x1 + 3, y1 + 3], 22, fill=BLUE)
        statics[s["sid"]] = (np.array(im), reg.items, reg.issues)
    mask = Image.new("L", (o.pw, o.ph), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, o.pw - 1, o.ph - 1], 20, fill=255)
    mask = (np.array(mask).astype(np.float32) / 255)[..., None]
    cams = {s["sid"]: cam_track(o, s["meta"], s["sid"]) for s in shots}
    N = int(round(total * FPS))
    frames = [int(round(float(x) * FPS)) for x in only.split(",")] if only else range(N)
    out_mp4 = SCR / (f"feat02_{dev}_silent.mp4" if not seg else f"seg/feat02_{'web' if dev == 'd' else 'mobile'}_{ORDER.index(seg) + 1:02d}_{seg}.mp4")
    out_mp4.parent.mkdir(exist_ok=True)
    ff = None
    if not only:
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{o.W}x{o.H}",
                               "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18" if not seg else "30", "-preset", "medium", "-pix_fmt", "yuv420p",
                               str(out_mp4)], stdin=subprocess.PIPE)
    readers = {}
    rows, issues, click_rows, still = [], [], [], []
    prev_panel = None
    run = 0
    max_run = (0, 0.0)
    samp = SCR / (f"samples_{dev}" if not seg else f"seg/samples_{dev}_{seg}")
    samp.mkdir(parents=True, exist_ok=True)
    if not only:
        for old in samp.glob("*.png"):
            old.unlink()
    x0, y0, x1, y1 = o.panel

    raw_view = {}

    def panel_of(s, k):
        if s["sid"] not in readers:
            readers[s["sid"]] = Reader(s["path"])
        fr = readers[s["sid"]].get(min(k, s["n"] - 1))
        kk = min(k, len(cams[s["sid"]][0]) - 1)
        cx, cy, cw, ch = cams[s["sid"]][0][kk]
        # 停格檢查用「沒加呼吸縮放」的原始鏡頭畫面
        raw_view["v"] = cv2.resize(fr[int(round(cy)):int(round(cy + ch)), int(round(cx)):int(round(cx + cw))], (o.pw // 4, o.ph // 4), interpolation=cv2.INTER_AREA).astype(np.int16)
        # 鏡頭慢移（同 v3_core._drift 的用意）：裁切框固定內縮 2%，在留出的邊內以每秒約 4.5 畫面像素等速來回平移
        # （水平、垂直週期錯開，轉折點不重疊），網站本身沒有動作時畫面也不會完全靜止；停格檢查用的是沒平移的原始鏡頭畫面。
        tt = s["start"] + k / FPS
        dx, dy = drift_xy(tt)
        mx, my = cw * 0.01, ch * 0.01
        cx, cy, cw, ch = cx + mx + dx * mx, cy + my + dy * my, cw * 0.98, ch * 0.98
        crop = fr[int(round(cy)):int(round(cy + ch)), int(round(cx)):int(round(cx + cw))]
        img = cv2.resize(crop, (o.pw, o.ph), interpolation=cv2.INTER_AREA if cw > o.pw else cv2.INTER_CUBIC)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        f = cams[s["sid"]][2][kk]
        fbs = s["meta"].get("fabs") or []
        fb = fbs[kk] if kk < len(fbs) else None
        raw_view["fab_hit"] = 0
        if fb and f is not None:   # 網站右下角客服鈕（錄影內建）不可壓到這一句在介紹的區塊（layout_rules 第 8 條）
            ix = min(fb[0] + fb[2], f[0] + f[2]) - max(fb[0], f[0])
            iy = min(fb[1] + fb[3], f[1] + f[3]) - max(fb[1], f[1])
            if ix > 0 and iy > 0:
                raw_view["fab_hit"] = int(ix * iy)
        if f is not None:      # 介紹中的區塊以外淡化（奶油色 55%），區塊外圍一圈藍框
            sx, sy = o.pw / cw, o.ph / ch
            fx0, fy0 = int(round((f[0] - cx) * sx)), int(round((f[1] - cy) * sy))
            fx1, fy1 = int(round((f[0] + f[2] - cx) * sx)), int(round((f[1] + f[3] - cy) * sy))
            fx0, fy0, fx1, fy1 = max(0, fx0), max(0, fy0), min(o.pw, fx1), min(o.ph, fy1)
            if (fx1 - fx0) * (fy1 - fy0) < 0.93 * o.pw * o.ph:
                dim = img.astype(np.float32) * 0.45 + np.array([255, 249, 239], np.float32) * 0.55
                dim[fy0:fy1, fx0:fx1] = img[fy0:fy1, fx0:fx1]
                img = dim.astype(np.uint8)
                cv2.rectangle(img, (fx0 + 1, fy0 + 1), (fx1 - 2, fy1 - 2), (37, 131, 230), 3, cv2.LINE_AA)
        return img

    for i in frames:
        t = i / FPS
        reg = Reg()
        if t >= end_start + XF / FPS:
            sid = "end"
        else:
            sid = [s for s in shots if s["start"] <= t + 1e-6][-1]["sid"]
        base, items, iss = statics[sid]
        canvas = base.copy()
        for it in items:
            reg.items.append(it)
        issues += [f"| {t:6.2f} | {x} |" for x in iss]
        # 畫面框內容
        active = [s for s in shots if s["start"] <= t + 1e-6 < s["start"] + s["n"] / FPS]
        panel = None
        if active:
            s = active[-1]
            k = int(round((t - s["start"]) * FPS))
            panel = panel_of(s, k).astype(np.float32)
            if len(active) > 1:
                s0 = active[0]
                k0 = int(round((t - s0["start"]) * FPS))
                a = clamp((t - s["start"]) / (XF / FPS))
                panel = panel_of(s0, k0).astype(np.float32) * (1 - a) + panel * a
            reg.add("網站畫面框", (x0 - 3, y0 - 3, x1 + 3, y1 + 3))
        if t >= end_start and sid != "end":
            pass
        if panel is not None:
            region = canvas[y0:y1, x0:x1].astype(np.float32)
            canvas[y0:y1, x0:x1] = (panel * mask + region * (1 - mask)).astype(np.uint8)
        if t >= end_start:
            a = clamp((t - end_start) / (XF / FPS))
            if a > 0:
                ec = end_card(o, canvas, Reg(), 1.0)
                ddx, ddy = drift_xy(t)
                ix0, iy0, ix1, iy1 = x0 + 14, y0 + 14, x1 - 14, y1 - 14
                ec[iy0:iy1, ix0:ix1] = np.roll(ec[iy0:iy1, ix0:ix1], (int(round(ddy * o.ph * 0.01)), int(round(ddx * o.pw * 0.01))), axis=(0, 1))
                canvas = (canvas.astype(np.float32) * (1 - a) + ec.astype(np.float32) * a).astype(np.uint8)
                if a >= 1:
                    end_card(o, canvas, reg, 1.0)
        # 泡泡
        b, a_in, a_out = bubble_at(bubbles, t)
        if b is not None:
            arr, (ox, oy), bbox, tbox, txt, biss, nl = bubble_img(dev, b["text"], tip[0], tip[1], side, zone)
            al = min(a_in, a_out)
            sc = 0.86 + 0.14 * back_out(a_in)
            if sc < 0.999:
                h, w = arr.shape[:2]
                px, py = tip[0] - ox, tip[1] - oy          # 以尾巴尖端為中心放大
                im2 = Image.fromarray(arr).resize((max(1, int(w * sc)), max(1, int(h * sc))), Image.LANCZOS)
                blend(canvas, np.array(im2), int(round(tip[0] - px * sc)), int(round(tip[1] - py * sc)), al)
            else:
                blend(canvas, arr, ox, oy, al)
            reg.add("泡泡", (min(bbox[0], tbox[0]), bbox[1], max(bbox[2], tbox[2]), bbox[3] + 6), "泡泡")
            reg.add("泡泡尾巴", tbox, "泡泡")
            for x in biss:
                issues.append(f"| {t:6.2f} | {x}：{b['text']} |")
            if len(b["text"].replace(' ', '')) > 22:
                issues.append(f"| {t:6.2f} | 泡泡超過 22 字：{b['text']} |")
        # 比比
        nm, bt = act_at(bubbles, t)
        arr, ox, oy, bbx = bibi_frame(o, nm, bt)
        blend(canvas, arr, ox, oy)
        reg.add("比比", bbx)
        if b is not None:
            dtip = (bbx[0] - tip[0]) if side == "right" else (tip[0] - bbx[2])
            if dtip < 12 - 0.5:
                issues.append(f"| {t:6.2f} | 尾巴尖端離比比 {dtip:.0f}px（<12） |")
        for (p, q, ar) in reg.overlaps():
            rows.append(f"| {t:6.2f} | {p} | {q} | {ar} |")
        for x in reg.issues:
            issues.append(f"| {t:6.2f} | {x} |")
        # 來源畫面是否在動（畫面框內）
        if panel is not None:
            if raw_view.get("fab_hit"):
                issues.append(f"| {t:6.2f} | 客服鈕壓到介紹區塊 {raw_view['fab_hit']}px² |")
            pv = raw_view["v"]   # 跟這段停住的第一幀比（同 freezedetect 做法）
            if prev_panel is not None and np.abs(pv - prev_panel).max() < 6:
                run += 1
                if run > max_run[0]:
                    max_run = (run, t)
            else:
                run = 0
                prev_panel = pv
            if prev_panel is None:
                prev_panel = pv
        if only:
            p = SCR / f"f_{dev}_{t:06.2f}.png"
            Image.fromarray(canvas).save(p)
            print(p, nm, b["text"] if b else "", reg.overlaps(), reg.issues)
            continue
        ff.stdin.write(canvas.tobytes())
        if i % 15 == 0:
            Image.fromarray(canvas).save(samp / f"s_{t:06.1f}.png")
        if i % 300 == 0:
            print(f"{t:6.1f}s / {total:.1f}", file=sys.stderr)
    if only:
        return
    ff.stdin.close()
    ff.wait()
    # 點擊檢查
    for s in shots:
        cams_s = cams[s["sid"]][0]
        for c in s["meta"]["clicks"]:
            if c["kind"] != "click":
                kind = "拖曳起點"
            else:
                kind = "點擊"
            k = min(int(round(c["t"] * FPS)), len(cams_s) - 1)
            cx, cy, cw, ch = cams_s[k]
            px, py = c["center"]
            ox_ = x0 + (px - cx) / cw * o.pw
            oy_ = y0 + (py - cy) / ch * o.ph
            inside = x0 + 4 <= ox_ <= x1 - 4 and y0 + 4 <= oy_ <= y1 - 4
            rc = c.get("rect_center")
            err = math.hypot(px - rc[0], py - rc[1]) if rc else None
            blank = (c.get("selector") or "").startswith("#mSheetBack")
            click_rows.append((s["sid"], round(float(s["start"] + c["t"]), 2), kind, c.get("label") or c.get("text"), None if err is None else round(float(err), 2), bool(inside), bool(blank), (int(round(ox_)), int(round(oy_)))))
    cut_rows = [(s["sid"], len(cams[s["sid"]][1])) for s in shots]
    meta_out = dict(dev=dev, total=total, end_start=end_start, frames=N, overlaps=len(rows), issues=len(issues),
                    still_max_s=round(float(max_run[0]) / FPS, 2), still_at=round(float(max_run[1]), 2), cut_frames=cut_rows,
                    clicks=click_rows, bubbles=[(round(b["t0"], 2), round(b["t1"], 2), b["text"], b["sid"]) for b in bubbles],
                    shots=[(s["sid"], round(s["start"], 2), round(s["n"] / FPS, 2)) for s in shots], data_date=data_date)
    if seg:
        (SCR / f"seg/render_{dev}_{seg}.json").write_text(json.dumps(meta_out, ensure_ascii=False, indent=1), encoding="utf-8")
        (SCR / f"seg/overlap_rows_{dev}_{seg}.md").write_text("\n".join(rows[:300] + ["", "問題："] + issues[:300]), encoding="utf-8")
        sp = out_mp4.with_name(out_mp4.stem + "_x1.5.mp4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out_mp4), "-filter:v", f"setpts=PTS/{SPEED}", "-r", str(FPS),
                        "-c:v", "libx264", "-crf", "28", "-pix_fmt", "yuv420p", str(sp)], check=True)
        real = [c for c in click_rows if c[2] == "點擊" and not c[6]]
        print(f"段落 {seg}（1.5 倍速預覽 {sp}）：{out_mp4}｜{N} 幀｜重疊 {len(rows)} 筆｜其他問題 {len(issues)} 筆｜點擊 {len(real)} 次，中心誤差最大 "
              f"{max([c[4] for c in real if c[4] is not None] or [0]):.1f}px，畫面框外 {len([c for c in click_rows if not c[5]])} 次｜畫面框內最長不動 {max_run[0] / FPS:.2f} 秒")
        return
    (SCR / f"render_{dev}.json").write_text(json.dumps(meta_out, ensure_ascii=False, indent=1), encoding="utf-8")
    (SCR / f"overlap_rows_{dev}.md").write_text("\n".join(rows[:500] + ["", "問題："] + issues[:500]), encoding="utf-8")
    print("重疊", len(rows), "問題", len(issues), "幀", N, "畫面框最長不動", max_run[0] / FPS, "秒 @", max_run[1])
    # 配樂＋點擊音效
    cues = {"cues": [[r[1] / SPEED, "tap"] for r in click_rows if r[2] == "點擊"] + [[(end_start + 0.3) / SPEED, "ding"]]}
    cj = SCR / f"cues_{dev}.json"
    cj.write_text(json.dumps(cues), encoding="utf-8")
    wav = SCR / f"bgm_{dev}.wav"
    subprocess.run([sys.executable, str(REPO / "docs/marketing/video_1010/make_music_v3.py"), "--length", f"{total / SPEED + 0.3:.2f}",
                    "--style", "cute", "--out", str(wav), "--cues", str(cj)], check=True)
    name = "feat02_etf_cashflow_web.mp4" if dev == "d" else "feat02_etf_cashflow_mobile.mp4"
    final = HERE / name
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out_mp4), "-i", str(wav), "-filter:v", f"setpts=PTS/{SPEED}", "-r", str(FPS),
                    "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                    "-shortest", "-movflags", "+faststart", str(final)], check=True)
    print("成片", final)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", default="d", choices=["d", "m"])
    ap.add_argument("--frames", default="")
    ap.add_argument("--seg", default="")
    g = ap.parse_args()
    render(g.dev, g.frames or None, g.seg or None)


if __name__ == "__main__":
    main()
