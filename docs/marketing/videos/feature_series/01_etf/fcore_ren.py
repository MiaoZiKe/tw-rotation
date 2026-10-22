"""功能介紹影片 01～03（Andy 10-21 重作）共用的成片合成（由 04 的 render_ind.py 複製改寫；單一連續錄影＋片尾卡，網頁 1920×1080／手機 1080×1920，30fps）。

素材：capture_ind.py 錄的網站實際畫面（亮色主題、逐格算圖，游標與點擊漣漪在錄影當下畫進畫面）。
版面（沿用第 6 版宣傳片）：奶油格紙底、左上藍色膠囊＋標題（黃色螢光底線）、右上「網站實際畫面・資料日」與歷史資料提醒；
網站畫面框只放「這一句在介紹的那一塊」（鏡頭＝錄影時每一格量到的元素外框，補成畫面框比例後裁切放大，平滑跟隨）；
比比主持、台詞用對話泡泡（一泡一句、≤14 字），泡泡尾巴指向比比；不配人聲，配輕快底樂＋點擊音效。

每一幀登記所有元素外框，兩兩比對（外擴 6px）→ overlap_report.md；另外檢查：泡泡字出框、點擊落在鏡頭內、
鏡頭有沒有把介紹的區塊裁掉、來源畫面（畫面框內）連續不動的最長秒數；成片再跑 ffmpeg freezedetect。

用法：python render_ind.py --dev d|m [--frames 1.0,5.5]（只出單格）[--seg open]（單段＋1.5 倍速預覽）
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
SCR = Path(os.environ.get("FEAT_SCR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/redo/x"))
FAST = True
SPEED = float(os.environ.get("FEAT_SPEED", "1.6"))   # 成片 ≤30 秒（含片尾）：1.6～1.75 倍速；每泡成片上至少停 0.9 秒
BUBBLE_MIN = 0.9
RAW = Path(os.environ.get("FEAT_RAW", str(SCR / "raw")))
NAME = "feat0x"   # 成片檔名前綴（各支 configure 覆蓋）
END_LINES_D = ["配息行事曆・類型總覽・分類卡・報酬比較"]
END_LINES_M = ["配息行事曆・類型總覽", "分類卡・報酬比較"]
END_CTA = "搜尋「哩股哩股」"
DATA_ASOF = None   # 各支提供「資料日」函式
FD = Path(os.environ.get("HBM_FONT_DIR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/font"))
F_BOLD = str(FD / "NotoSansTC-Bold.ttf")
F_BLACK = str(FD / "NotoSansTC-Black.ttf")
F_MED = str(FD / "NotoSansTC-Medium.ttf")
FPS = 30
PAD = 6
XF = 6             # 轉場交疊 0.2 秒（10-21 稽核：最多 0.2 秒）
END_DUR = 3.2      # 片尾卡原片 3.2 秒（成片約 2.0 秒；10-21 指示：片尾卡成片停 1.5～2 秒）

ORDER = ["main"]
FIXED_BOX = None   # 網頁版固定取景（10-22）：dict(bw=css 寬, y0=css 上緣, card_x=功能卡左緣 css)；取景框尺寸整支不變，只在側欄／功能卡兩個位置之間平移，空白處用底色補
SEC = {   # 膠囊、標題、標題重點字
    "open": ("產業地圖", "產品從上游到下游", "上游到下游"),
    "guide": ("引導", "從首頁找到產業地圖", "產業地圖"),
    "chain": ("功能 1", "選產業鏈＋產品剖析圖", "產品剖析圖"),
    "rel": ("功能 2", "2D 供應鏈關聯圖", "關聯圖"),
    "3d": ("功能 3", "3D 立體剖析圖", "立體剖析圖"),
    "end": ("產業地圖", "上下游、台廠位置一次看", "一次看"),
}
NAV = [("chain", "產業鏈"), ("rel", "2D 關聯圖"), ("3d", "3D 剖析圖")]
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
        o.panel = (26, 88, 1676, 940)
        o.bibi_size = 224
        o.bibi_foot = (1814, 1072)
        o.nav = (1696, 88, 1900, 0)
        o.bub_zone = (26, 950, None, 1070)     # 泡泡在畫面框下方，右邊接尾巴指向比比
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

def nav(o, im, reg, sid, cur=None):
    if not o.nav:
        return
    d = ImageDraw.Draw(im, "RGBA")
    x0, y0, x1, _ = o.nav
    f = font(F_BOLD, 24)
    fn = font(F_BLACK, 22)
    if cur is None:
        cur = 99 if sid == "end" else -1
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


# ───────────────────────── 鏡頭（v2） ─────────────────────────
# 取景：錄影時每一格量到「介紹區塊」focus（元素本身的完整外框，不以視窗裁切）與取景框 cam。
# 合成時鏡頭一律把 focus 整塊放進「最壞情況的實際裁切範圍」（鏡頭慢移＝裁切框內縮 2%、在內縮範圍內來回 → 四邊各留 2%）。
# 手機版允許取景框比錄影畫面寬一點（≤8%）：超出的部分補網頁底色（整塊區塊完整入鏡，不是靠留白算沒切到 —— 檢查是拿區塊本身的外框比實際裁切）。
DRIFT = 0.0        # 10-21 改版：取景框邊緣貼在空白處，不再內縮慢移（慢移會讓框緣切到字）
OUT_X = 0.08       # 手機取景最多比錄影畫面寬 8%


def inner(c):
    """最壞情況的實際裁切範圍（x, y, w, h）：四邊各內縮 2%。"""
    x, y, w, h = c
    return (x + DRIFT * w, y + DRIFT * h, (1 - 2 * DRIFT) * w, (1 - 2 * DRIFT) * h)


def contains(c, f, tol=0.5):
    """裁切框 c（x,y,w,h，四邊已內縮）是否整個包住 f（x,y,w,h）。"""
    return f[0] >= c[0] - tol and f[1] >= c[1] - tol and f[0] + f[2] <= c[0] + c[2] + tol and f[1] + f[3] <= c[1] + c[3] + tol


def fit2(o, cam, f, W0, H0, minw, allow_out, ytop, xlim):
    x, y, w, h = cam
    cx, cy = x + w / 2, y + h / 2
    if f is not None:
        w = max(w, f[2] / (1 - 2 * DRIFT) + 8)
        h = max(h, f[3] / (1 - 2 * DRIFT) + 8)
    w = max(w, minw)
    if w / max(h, 1) < o.asp:
        w = h * o.asp
    else:
        h = w / o.asp
    lo, hi = (0, W0) if not xlim else (max(0, xlim[0]), min(W0, xlim[1]))
    lim_w = (hi - lo) * (1 + OUT_X if allow_out else 1)
    lim_h = (H0 - ytop) * (1 + OUT_X if allow_out else 1)
    if w > lim_w:
        w, h = lim_w, lim_w / o.asp
    if h > lim_h:
        h, w = lim_h, lim_h * o.asp
    x, y = cx - w / 2, cy - h / 2
    if f is not None:   # 平移到介紹區塊整塊落在四邊內縮 2% 之內
        x = max(min(x, f[0] - DRIFT * w - 3), f[0] + f[2] - (1 - DRIFT) * w + 3)
        y = max(min(y, f[1] - DRIFT * h - 3), f[1] + f[3] - (1 - DRIFT) * h + 3)

    def clamp_axis(v, size, a0, a1, out):
        if size <= a1 - a0:
            v2 = clamp(v, a0, a1 - size)
            return v2
        return clamp(v, a1 - size, a0) if out else a0
    x_in = clamp_axis(x, w, lo, hi, allow_out)
    y_in = clamp_axis(y, h, ytop, H0, allow_out)
    if allow_out and f is not None:   # 盡量留在錄影畫面內；區塊需要時才超出（補底色），上緣不超過頂欄
        ok_in = contains(inner((x_in, y_in, w, h)), f, 1)
        if not ok_in:
            ox = W0 * OUT_X / 2
            x_in = clamp(x, lo - ox, hi + ox - w) if w < hi - lo + 2 * ox else (lo + hi) / 2 - w / 2
            y_in = clamp(y, ytop, H0 + H0 * OUT_X / 2 - h) if h < H0 - ytop + H0 * OUT_X / 2 else ytop
    return np.array([x_in, y_in, w, h], np.float64)


def tri(x):
    """三角波 -1～1，週期 1。"""
    x = x % 1.0
    return 4 * x - 1 if x < 0.5 else 3 - 4 * x


def drift_xy(t, o=None):
    lo = drift_xy.o
    px = 4.5 / (lo.pw * 0.01)          # 每秒要走的「振幅倍數」：4.5 畫面像素 ÷ 振幅
    py = 4.5 / (lo.ph * 0.01)
    return tri(t * px / 4 + 0.25), tri(t * py / 4 + 0.6)


def crop_of(c, t):
    """實際裁切框：取景框內縮 2%，在內縮範圍內等速來回（鏡頭慢移）。"""
    cx, cy, cw, ch = c
    dx, dy = drift_xy(t)
    mx, my = cw * DRIFT / 2, ch * DRIFT / 2
    return (cx + mx + dx * mx, cy + my + dy * my, cw * (1 - DRIFT), ch * (1 - DRIFT))


def avoid_fab(o, tgt, fb, r, ytop):
    x, y, w, h = tgt
    fx0, fy0, fx1, fy1 = fb[0] - 6, fb[1] - 6, fb[0] + fb[2] + 6, fb[1] + fb[3] + 6
    if x + w <= fx0 or x >= fx1 or y + h <= fy0 or y >= fy1:
        return tgt
    cands = []
    # ① 往上移；② 往左移；③ 以右下角收縮（右緣或下緣退到客服鈕外）
    if fy0 - h >= ytop:
        cands.append(np.array([x, fy0 - h, w, h]))
    if fx0 - w >= -o.out_px:
        cands.append(np.array([fx0 - w, y, w, h]))
    hh = fy0 - y
    if hh > 200:
        cands.append(np.array([x, y, hh * o.asp, hh]))
    ww = fx0 - x
    if ww > 200:
        cands.append(np.array([x, y, ww, ww / o.asp]))
    if not cands:
        return tgt
    if r is not None:   # 候選框平移到把介紹區塊整塊放進四邊內縮 2% 之內（平移後仍不碰客服鈕才算）
        more = []
        for c in cands:
            cx_, cy_, cw_, ch_ = c
            nx = max(min(cx_, r[0] - DRIFT * cw_ - 3), r[0] + r[2] - (1 - DRIFT) * cw_ + 3)
            ny = max(min(cy_, r[1] - DRIFT * ch_ - 3), r[1] + r[3] - (1 - DRIFT) * ch_ + 3)
            c2 = np.array([nx, max(ny, ytop), cw_, ch_])
            if c2[0] + cw_ <= fx0 or c2[0] >= fx1 or c2[1] + ch_ <= fy0 or c2[1] >= fy1:
                more.append(c2)
        cands = cands + more
    if r is not None:   # 先挑「介紹區塊仍整塊在內」的候選
        ok = [c for c in cands if contains(inner(c), r, 1)]
        if ok:
            return min(ok, key=lambda c: abs(c[2] - w) + abs(c[1] - y) + abs(c[0] - x))

    def cover(c):   # 這一句介紹的區塊有多少還在鏡頭裡（越多越好）
        if r is None:
            return -abs(c[2] - w)
        ix = max(0.0, min(c[0] + c[2], r[0] + r[2]) - max(c[0], r[0]))
        iy = max(0.0, min(c[1] + c[3], r[1] + r[3]) - max(c[1], r[1]))
        return ix * iy - 0.001 * abs(c[2] - w) * h
    return max(cands, key=cover)


def cam_track(o, meta, sid=""):
    """回傳每一格：取景框、目標取景框、介紹區塊、是否推移中、該拍標記。"""
    W0, H0 = meta["size"]
    dsf = meta["dsf"]
    cx_ = meta.get("content_x") or [0, W0]
    xlim = [cx_[0] - 30 * dsf, cx_[1] + 30 * dsf] if o.dev == "d" else None
    allow_out = True   # 桌機也允許取景框少量超出錄影畫面（貼視窗邊的區塊：側欄選單、超出右緣幾 px 的下拉面板），超出部分補邊緣底色
    o.out_px = W0 * OUT_X / 2 if allow_out else 0
    ytop = (41 if o.dev == "d" else 56) * dsf   # 介紹區塊的取景一律在頂欄以下（不切到頂欄的按鈕）
    ytop_full = 0 if sid == "guide" else ytop   # 引導段的整頁鏡頭要看得到頂欄的選單鈕
    out, tgts, focus, transit, beats = [], [], [], [], []
    cur = None
    fcur = None
    last_id = None
    settled = True
    snaps = 0
    cams_in = list(meta["cams"])
    first = next((i for i, c in enumerate(cams_in[:6]) if c[0] != 0), None)
    if first:   # 開錄第一格還沒設定鏡頭（cam_id 0）：沿用緊接著設定的鏡頭，不閃一格整頁
        cams_in[:first] = [cams_in[first]] * first
    fbs = meta.get("fabs") or []
    for k, c in enumerate(cams_in):
        cid, r = c[0], c[1:5]
        minw_c = c[5] if len(c) > 5 else 0
        f = np.array(c[6], np.float64) if len(c) > 6 and c[6] else None
        zoom = bool(c[7]) if len(c) > 7 else False
        full = f is None
        fb = fbs[k] if k < len(fbs) else None
        minw = max(o.pw * 0.5, minw_c) if minw_c else o.pw
        if full:
            lft, rgt = (xlim[0], xlim[1]) if xlim else (0, W0)
            hh = (fb[1] - 8 - ytop_full) if fb else (H0 - ytop_full)
            ww = min(rgt - lft, max(200.0, hh) * o.asp)
            tgt = np.array([(lft + rgt) / 2 - ww / 2, ytop_full, ww, ww / o.asp])
        else:
            xl = xlim if (xlim and f[0] >= xlim[0] - 4 * dsf) else None   # 介紹區塊在內容區左側（側欄選單）→ 不限內容區
            tgt = fit2(o, r, f, W0, H0, minw, allow_out, ytop, xl)
        if fb:   # 鏡頭一律避開網站客服鈕（不藏它，只是不入鏡）
            tgt = avoid_fab(o, tgt, fb, f, ytop_full if full else ytop)
        if cur is None:
            cur = tgt.copy()
        else:
            a = 0.16 if cid == last_id else 0.12
            cur = cur + (tgt - cur) * a
            if fb:
                cur = avoid_fab(o, cur, fb, f, ytop)
        new_beat = cid != last_id
        if new_beat:
            settled = False
        if not settled and np.abs(cur - tgt).max() < 0.012 * tgt[2]:
            settled = True
        if settled and f is not None and not contains(inner(cur), f, 1):
            cur = tgt.copy()   # 同一拍內區塊變大（展開、彈出）：鏡頭立刻拉到能整塊放下，不讓它被裁
            snaps += 1
        if f is None:
            fcur = None
        elif fcur is None:
            fcur = f.copy()
        else:
            fcur = fcur + (f - fcur) * 0.2
        last_id = cid
        out.append(cur.copy())
        tgts.append(tgt.copy())
        focus.append((None if f is None else f.copy(), None if fcur is None else fcur.copy()))
        transit.append(not settled)
        beats.append((cid, zoom))
    return dict(cams=out, tgts=tgts, focus=focus, transit=transit, beats=beats, snaps=snaps)



# ───────────────────────── 10-21 取景改版：框緣貼空白（自由比例、逐格量像素）─────────────────────────
INK_T = 175         # 灰階 < 175 視為「有字／有線」（卡片外框、底色、陰影都比這亮）


def _ink_integral(fr, cur_row, dsf):
    g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
    ink = (g < INK_T).astype(np.uint8)
    if cur_row and not cur_row[2]:   # 游標與點擊漣漪那一小塊不算
        r = int(34 * dsf)
        x, y = int(cur_row[0]), int(cur_row[1])
        ink[max(0, y - r):y + r, max(0, x - r):x + r] = 0
    return cv2.integral(ink)


def _cnt(I, x0, y0, x1, y1):
    H, W = I.shape[0] - 1, I.shape[1] - 1
    x0, x1 = max(0, min(W, x0)), max(0, min(W, x1))
    y0, y1 = max(0, min(H, y0)), max(0, min(H, y1))
    if x1 <= x0 or y1 <= y0:
        return 0
    return int(I[y1, x1] - I[y0, x1] - I[y1, x0] + I[y0, x0])


def _scan(cands, fn):
    best = None
    for p in cands:
        c = fn(p)
        if c == 0:
            return p, 0
        if best is None or c < best[1]:
            best = (p, c)
    return (best[0], best[1]) if best else (None, 1)


def _order(p0, lo, hi, S, sign, grow, inner_lim=None):
    """候選位置依「離 p0 的距離」由近到遠（同距離先往外）；往內不得超過 inner_lim（避免切進被介紹區塊）。"""
    out = []
    for i in range(0, S + 1):
        for sg in (1, -1):
            q = p0 + sg * i * sign if grow else p0 + sg * i
            if not (lo <= q <= hi) or q in out:
                continue
            if grow and sg == -1 and (inner_lim is None or (q - inner_lim) * sign < 0):
                continue   # 往內且切進被介紹區塊
            out.append(q)
    return out


def snap_rect(I, d, bounds, bw, Sx, Sy, grow, fbox=None, blocks=None, tol=8, bwy=None):
    """把 d（x0,y0,x1,y1）的四條邊各自挪到最近的「整條邊都沒有字、也不切過任何卡片」的位置（grow＝先往外、不行才往內但不切進 fbox）。
    帶寬 bw 以邊線為中心對稱（兩側都留空白）。回傳（矩形, 還切到字的邊數）。"""
    x0, y0, x1, y1 = [int(round(v)) for v in d]
    lx, ly, hx, hy = bounds
    c1 = c2 = c3 = c4 = 0
    m = 2 * bw
    h2 = bw // 2
    h2y = (bwy if bwy is not None else bw) // 2
    blocks = blocks or []
    tall = 400 * (tol / 4.0)   # tol = 4 css（px）→ 換算成 400 css
    fx0, fy0, fx1, fy1 = (None,) * 4 if fbox is None else (fbox[0], fbox[1], fbox[0] + fbox[2], fbox[1] + fbox[3])   # 被介紹區塊（已含 pad）不得被切進去

    def vx(p):   # 垂直邊 x=p（高度範圍 y0..y1）有沒有切過卡片
        return not any(by + tol < y1 and by + bh - tol > y0 and bx + tol < p < bx + bw_ - tol for bx, by, bw_, bh in blocks)

    def hy_(p):  # 水平邊 y=p
        return not any(bx + tol < x1 and bx + bw_ - tol > x0 and by + tol < p < by + bh - tol and bh <= tall for bx, by, bw_, bh in blocks)   # 很高的清單卡（>400 css）允許在列與列之間的空白處上下截斷

    def pick(c, ok):
        f_ = [q for q in c if ok(q)]
        return f_ or c

    for _ in range(3):
        n, c1 = _scan(pick(_order(y0, ly, y1 - 3 * bw, Sy, -1, grow, fy0), hy_), lambda y: _cnt(I, x0, y - h2y, x1, y + h2y))
        y0 = y0 if n is None else n
        n, c2 = _scan(pick(_order(y1, y0 + 3 * bw, hy, Sy, +1, grow, fy1), hy_), lambda y: _cnt(I, x0, y - h2y, x1, y + h2y))
        y1 = y1 if n is None else n
        n, c3 = _scan(pick(_order(x0, lx, x1 - 3 * bw, Sx, -1, grow, fx0), vx), lambda x: _cnt(I, x - h2, y0, x + h2, y1))
        x0 = x0 if n is None else n
        n, c4 = _scan(pick(_order(x1, x0 + 3 * bw, hx, Sx, +1, grow, fx1), vx), lambda x: _cnt(I, x - h2, y0, x + h2, y1))
        x1 = x1 if n is None else n
    return (x0, y0, x1, y1), int(c1 > 0) + int(c2 > 0) + int(c3 > 0) + int(c4 > 0)


def avoid_fab2(I, rect, fb, f, bw):
    """鏡頭不要把客服鈕框進來：先把下緣收到客服鈕上方的空白處，不行再收右緣。回傳（矩形, 是否仍入鏡）。"""
    x0, y0, x1, y1 = rect
    fx0, fy0, fx1, fy1 = fb[0] - 6, fb[1] - 6, fb[0] + fb[2] + 6, fb[1] + fb[3] + 6
    if x1 <= fx0 or x0 >= fx1 or y1 <= fy0 or y0 >= fy1:
        return rect, 0
    fb_, fr_ = (f[1] + f[3]) if f is not None else y0 + 100, (f[0] + f[2]) if f is not None else x0 + 100
    cand_y = [y for y in range(int(fy0), int(max(y0 + 100, fb_)) - 1, -1) if y > y0 + 100]
    n, c = _scan(cand_y, lambda y: _cnt(I, x0, y - bw, x1, y))
    if n is not None and c == 0 and n >= fb_:
        return (x0, y0, x1, n), 0
    cand_x = [x for x in range(int(fx0), int(max(x0 + 100, fr_)) - 1, -1) if x > x0 + 100]
    n, c = _scan(cand_x, lambda x: _cnt(I, x - bw, y0, x, y1))
    if n is not None and c == 0 and n >= fr_:
        return (x0, y0, n, y1), 0
    return rect, 1


def cam_track2(o, meta, path, sid=""):
    """逐格讀錄影畫面，取景框＝被介紹區塊向外擴到最近的空白處（框緣不切字），比例自由；畫面框依比例縮放置中。"""
    W0, H0 = meta["size"]
    dsf = meta["dsf"]
    web = o.dev == "d"
    ytop = int((41 if web else 56) * dsf)
    bw = int(round(5 * dsf))              # 找空白邊用的帶寬（以邊線為中心，兩側各留約 2.5 css 空白）
    bwc = 2                               # 檢查用：最外 2 個像素有字／線＝切到
    mw_css, mh_css = (520, 160) if web else (390, 380)
    Sx, Sy = int(520 * dsf), int(300 * dsf)
    cams_in = list(meta["cams"])
    first = next((i for i, c in enumerate(cams_in[:6]) if c[0] != 0), None)
    if first:
        cams_in[:first] = [cams_in[first]] * first
    fbs = meta.get("fabs") or []
    curs = meta.get("cur") or []
    btbl, bidx = meta.get("blocks_tbl") or [], meta.get("blocks_idx") or []

    def blks_at(k, f_):
        if k >= len(bidx) or bidx[k] < 0:
            return []
        pad_ = 4 * dsf
        res = []
        for b in btbl[bidx[k]]:
            if f_ is not None:
                if b[0] <= f_[0] + pad_ and b[1] <= f_[1] + pad_ and b[0] + b[2] >= f_[0] + f_[2] - pad_ and b[1] + b[3] >= f_[1] + f_[3] - pad_:
                    continue   # 被介紹區塊整個在這個容器裡：容器不算被切
                if b[2] >= 1000 * dsf:   # 很寬的大卡（放不下整張還維持字夠大）：被介紹區塊有相當部分落在裡面就放行
                    ix = max(0.0, min(b[0] + b[2], f_[0] + f_[2]) - max(b[0], f_[0]))
                    iy = max(0.0, min(b[1] + b[3], f_[1] + f_[3]) - max(b[1], f_[1]))
                    if ix * iy >= 0.4 * f_[2] * f_[3]:
                        continue
            res.append(b)
        return res

    # ── 第 1 趟：逐格算「目標取景框」（貼空白處）；第 2 趟：平滑跟隨＋逐格量邊緣有沒有切到字
    rd = Reader(path)
    T1 = []
    for k, c in enumerate(cams_in):
        fr = rd.get(k)
        I = _ink_integral(fr, curs[k] if k < len(curs) else None, dsf)
        cid, r = c[0], c[1:5]
        minw_c = c[5] if len(c) > 5 else 0
        f = np.array(c[6], np.float64) if len(c) > 6 and c[6] else None
        zoom = bool(c[7]) if len(c) > 7 else False
        exact = int(c[8]) if len(c) > 8 else 0
        if f is not None:   # 被介紹元素超出錄影視窗的部分（橫向捲動的分頁列）本來就看不到，不算要框的範圍
            fx0_, fy0_ = max(0.0, f[0]), max(float(ytop), f[1]) if f[1] + f[3] > ytop + 40 else max(0.0, f[1])   # 頂欄以上不入鏡（取景一律在頂欄以下）
            f = np.array([fx0_, fy0_, min(W0, f[0] + f[2]) - fx0_, min(H0, f[1] + f[3]) - fy0_], np.float64)
        fb = fbs[k] if k < len(fbs) else None
        fl = 0
        fh = 0
        hold = False
        if f is None and k > 0 and not exact:   # 網頁捲動／面板開關的過場（沒有被介紹元素）：鏡頭原地不動，不縮小成整頁（Andy：不要一直縮放）
            hold = True
            tgt = None
        else:
            if exact:
                ef = f if f is not None else np.array(r, np.float64)
                m = int(2.0 * dsf)
                if web:
                    rect = (int(round(ef[0] + 2 * m)), int(round(ef[1] + m)), int(round(ef[0] + ef[2])), int(round(ef[1] + ef[3] - 2 * m)))
                elif exact == 2 or ef[0] < 8 * dsf:   # 手機側邊選單抽屜（貼左緣）：右緣是遮罩的分界，往內縮 8 css
                    rect = (0, int(round(ef[1] + m)), int(round(ef[0] + ef[2] - 8 * dsf)), int(round(ef[1] + ef[3] - 2 * m)))
                else:   # 手機：抽屜外緣往外放一點（抽屜內文字貼邊），左右各 10 css
                    rect = (int(max(0, round(ef[0] - 4 * dsf))), int(round(ef[1] + m)), int(min(W0, round(ef[0] + ef[2] - 2 * dsf))), int(round(ef[1] + ef[3] - 2 * m)))
                n_, _c = _scan([rect[1] - i for i in range(0, int(30 * dsf)) if rect[1] - i >= ytop] + [rect[1] + i for i in range(1, int(22 * dsf))], lambda y: _cnt(I, rect[0], y, rect[2], y + bw))   # 上緣往外找空白（按鈕列旁的膠囊比按鈕高）
                if n_ is not None and _c == 0:
                    rect = (rect[0], n_, rect[2], rect[3])
                if fb:   # 客服鈕蓋在面板上時，把下緣收到客服鈕上方
                    rect, fh = avoid_fab2(I, rect, fb, None, bw)
                f = np.array([rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1]], np.float64)
            elif f is None:
                dd = [0, ytop, W0, H0]
                if fb and fb[1] > H0 * 0.5:
                    dd[3] = int(fb[1] - 6)
                rect, fl = snap_rect(I, dd, (0, ytop, W0, H0), bw, int(120 * dsf), int(120 * dsf), False, None, None, int(4 * dsf), int(3 * dsf))
                if fb:
                    rect, fh = avoid_fab2(I, rect, fb, None, bw)
            else:
                x0_, y0_ = min(r[0], f[0]), min(r[1], f[1])
                x1_, y1_ = max(r[0] + r[2], f[0] + f[2]), max(r[1] + r[3], f[1] + f[3])
                mw = minw_c if minw_c else mw_css * dsf
                mh = mh_css * dsf
                if x1_ - x0_ < mw:
                    cx_ = (x0_ + x1_) / 2
                    x0_, x1_ = cx_ - mw / 2, cx_ + mw / 2
                if y1_ - y0_ < mh:
                    cy_ = (y0_ + y1_) / 2
                    y0_, y1_ = cy_ - mh / 2, cy_ + mh / 2
                if x0_ < 0:
                    x1_ -= x0_
                    x0_ = 0
                if x1_ > W0:
                    x0_ -= x1_ - W0
                    x1_ = W0
                x0_ = max(0, x0_)
                if y0_ < ytop:
                    y1_ += ytop - y0_
                    y0_ = ytop
                if y1_ > H0:
                    y0_ = max(ytop, y0_ - (y1_ - H0))
                    y1_ = H0
                rect, fl = snap_rect(I, (x0_, y0_, x1_, y1_), (0, ytop, W0, H0), bw, Sx, Sy, True, f, blks_at(k, f), int(4 * dsf), int(3 * dsf))
                if fb:
                    rect, fh = avoid_fab2(I, rect, fb, f, bw)
            tgt = np.array([rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1]], np.float64)
        T1.append(dict(cid=cid, f=f, zoom=zoom, exact=exact, hold=hold, tgt=tgt, fh=fh, fl=fl))
    # 每一拍開頭 18 格內，目標框若比 18 格後的目標大很多（頁面還在動畫、版面尚未定位），改用穩定後的目標，避免一閃縮小再放大
    i = 0
    while i < len(T1):
        j = i
        while j + 1 < len(T1) and T1[j + 1]["cid"] == T1[i]["cid"]:
            j += 1
        if not T1[i]["exact"]:
            ref = next((T1[q]["tgt"] for q in range(min(i + 18, j), i - 1, -1) if T1[q]["tgt"] is not None), None)
            if ref is not None:
                for q in range(i, min(i + 18, j + 1)):
                    t_ = T1[q]["tgt"]
                    if t_ is not None and t_[2] * t_[3] > 1.3 * ref[2] * ref[3]:
                        T1[q]["tgt"] = ref.copy()
        i = j + 1
    rd = Reader(path)
    out, tgts, focus, transit, beats, viol, fabhit, fails_l = [], [], [], [], [], [], [], []
    cur = None
    last_id = None
    for k, t1 in enumerate(T1):
        cid, f, zoom, exact = t1["cid"], t1["f"], t1["zoom"], t1["exact"]
        if t1["hold"]:
            fb_ = fbs[k] if k < len(fbs) else None
            if fb_ and cur is not None:   # 捲動過場中客服鈕重新出現：取景下緣收到客服鈕上方
                if not (cur[0] + cur[2] <= fb_[0] - 6 or cur[0] >= fb_[0] + fb_[2] + 6 or cur[1] + cur[3] <= fb_[1] - 6 or cur[1] >= fb_[1] + fb_[3] + 6) and fb_[1] - 6 - cur[1] > 200:
                    cur = np.array([cur[0], cur[1], cur[2], fb_[1] - 6 - cur[1]])
            out.append(cur.copy())
            tgts.append(tgts[-1].copy())
            focus.append((None, None))
            transit.append(True)
            beats.append((cid, zoom))
            viol.append(0)
            fabhit.append(0)
            fails_l.append(0)
            last_id = cid
            continue
        tgt = t1["tgt"]
        new_beat = cid != last_id
        if cur is None or exact:
            cur = tgt.copy()
        else:
            cur = cur + (tgt - cur) * (0.22 if not new_beat else 0.16)
            if np.abs(cur - tgt).max() < max(3.0, 0.004 * tgt[2]):
                cur = tgt.copy()
        if f is not None and not contains(tuple(cur), f, 1):
            cur = tgt.copy()   # 區塊變大（展開、彈出）：鏡頭立刻拉到能整塊放下
        moving = bool(np.abs(cur - tgt).max() > 0.5)
        v = 0
        if not moving:
            fr = rd.get(k)
            I = _ink_integral(fr, curs[k] if k < len(curs) else None, dsf)
            x, y, w, h = [int(round(q)) for q in cur]
            v = int(_cnt(I, x, y, x + w, y + bwc) > 0)
            if y + h < H0 - 2:   # 取景框邊緣就是錄影視窗邊緣的那一邊，網頁本身就是在那裡被截掉（例如橫向捲動的分頁列），不算取景框切的
                v += int(_cnt(I, x, y + h - bwc, x + w, y + h) > 0)
            if x > 2:
                v += int(_cnt(I, x, y, x + bwc, y + h) > 0)
            if x + w < W0 - 2:
                v += int(_cnt(I, x + w - bwc, y, x + w, y + h) > 0)
        last_id = cid
        out.append(cur.copy())
        tgts.append(tgt.copy())
        focus.append((None if f is None else f.copy(), None if f is None else f.copy()))
        transit.append(moving)
        beats.append((cid, zoom))
        viol.append(v)
        fabhit.append(t1["fh"])
        fails_l.append(t1["fl"])
    return dict(cams=out, tgts=tgts, focus=focus, transit=transit, beats=beats, snaps=0, viol=viol, fabhit=fabhit, fails=fails_l)



def cam_track3(o, meta, path, sid=""):
    """固定尺寸取景（網頁 10-22）：取景框大小＝FIXED_BOX 定死（放大倍率整支不變）；只有位置（側欄／功能卡）、
    下緣與右緣依「最近的空白處」收短（剩下的用底色補）。回傳格式同 cam_track2，另附 'fill'。"""
    W0, H0 = meta["size"]
    dsf = meta["dsf"]
    FB = FIXED_BOX
    BWp = int(round(FB["bw"] * dsf))
    BHp = int(round(BWp / o.asp))
    y_base = int(round(FB["y0"] * dsf))
    x_card = int(round(FB["card_x"] * dsf))
    bw = 2   # 邊緣帶寬 1 css：只要求框緣上一條線沒有字
    bwc = 2
    cams_in = list(meta["cams"])
    first = next((i for i, c in enumerate(cams_in[:6]) if c[0] != 0), None)
    if first:
        cams_in[:first] = [cams_in[first]] * first
    fbs = meta.get("fabs") or []
    curs = meta.get("cur") or []
    rd = Reader(path)
    T1 = []
    mode = "side"
    for k, c in enumerate(cams_in):
        fr = rd.get(k)
        I = _ink_integral(fr, curs[k] if k < len(curs) else None, dsf)
        cid, r = c[0], c[1:5]
        f = np.array(c[6], np.float64) if len(c) > 6 and c[6] else None
        if f is not None:
            f = np.array([max(0.0, f[0]), max(float(y_base), f[1]), min(W0, f[0] + f[2]) - max(0.0, f[0]), min(H0, f[1] + f[3]) - max(float(y_base), f[1])], np.float64)
            mode = "card" if f[0] > (FB["card_x"] - 8) * dsf else "side"
        hold = f is None and k > 0
        tgt = None
        fl = 0
        if not hold:
            x0 = 0 if mode == "side" else x_card
            # 上緣：y_base 往上下找整條空白（f 的上緣以上）
            ftop = f[1] - 1 * dsf if f is not None else H0
            fleft = f[0] - 3 * dsf if f is not None else W0
            xe = min(W0, x0 + BWp)
            cand_y = [y_base + i for i in range(0, int(40 * dsf)) if y_base + i <= ftop] + [y_base - i for i in range(1, int(14 * dsf))]
            ny, cy_ = _scan(cand_y, lambda y: _cnt(I, x0, y, xe, y + 2))
            y0 = ny if ny is not None else y_base
            if cy_:
                fl += 1
            x0b = x0
            if mode == "card":
                cand_x = [x_card + i for i in range(0, int(12 * dsf)) if x_card + i <= fleft] + [x_card - i for i in range(1, int(8 * dsf))]
                nx, cx_ = _scan(cand_x, lambda x: _cnt(I, x, y0, x + 2, y0 + BHp))
                x0b = nx if nx is not None else x_card
                if cx_:
                    fl += 1
            x1 = min(W0, x0b + BWp)
            y1 = min(H0, y0 + BHp)
            fbot = (f[1] + f[3] + 1 * dsf) if f is not None else y0 + 60 * dsf
            fright = (f[0] + f[2] + 1 * dsf) if f is not None else x0b + 60 * dsf
            cand_b = [y1 - i for i in range(0, int(190 * dsf)) if y1 - i >= fbot]
            bwb = 1
            nb, cb = _scan(cand_b, lambda y: _cnt(I, x0b, y - 2, x1, y))
            if nb is not None:
                y1 = nb
            if cb:
                fl += 1
            cand_r = [x1 - i for i in range(0, int((800 if mode == 'side' else 260) * dsf)) if x1 - i >= fright]
            nr, cr = _scan(cand_r, lambda x: _cnt(I, x - 2, y0, x, y1))
            if nr is not None:
                x1 = nr
            if cr:
                fl += 1
            fb = fbs[k] if k < len(fbs) else None
            fh = 0
            if fb and not (x1 <= fb[0] - 6 or x0b >= fb[0] + fb[2] + 6 or y1 <= fb[1] - 6 or y0 >= fb[1] + fb[3] + 6):
                fh = 1
            tgt = np.array([x0b, y0, x1 - x0b, y1 - y0], np.float64)
        T1.append(dict(cid=cid, f=f, hold=hold, tgt=tgt, fl=fl, fh=(fh if not hold else 0), zoom=bool(c[7]) if len(c) > 7 else False))
    # 每一拍開頭 45 格（圖表動畫、版面尚未定位）改用「45 格之後」的目標，避免取景下緣在動畫期間跟著抖
    i = 0
    while i < len(T1):
        j = i
        while j + 1 < len(T1) and T1[j + 1]["cid"] == T1[i]["cid"] and not T1[j + 1]["hold"]:
            j += 1
        lab_i = next((m_[2] for m_ in reversed([m_ for m_ in meta["marks"] if m_[1] == "cam"]) if m_[0] <= i / FPS + 1e-6), "")
        if not T1[i]["hold"] and j > i and "圓餅" in lab_i:
            ref = T1[min(i + 45, j)]["tgt"]
            for q in range(i, min(i + 45, j + 1)):
                if T1[q]["tgt"] is not None and ref is not None:
                    T1[q]["tgt"] = ref.copy()
        i = j + 1
    out, tgts, focus, transit, beats, viol, fabhit, fails_l = [], [], [], [], [], [], [], []
    cur = None
    last_id = None
    rd = Reader(path)
    for k, t1 in enumerate(T1):
        cid, f = t1["cid"], t1["f"]
        if t1["hold"] and cur is not None:
            out.append(cur.copy())
            tgts.append(tgts[-1].copy())
            focus.append((None, None))
            transit.append(True)
            beats.append((cid, t1["zoom"]))
            viol.append(0)
            fabhit.append(0)
            fails_l.append(0)
            last_id = cid
            continue
        tgt = t1["tgt"]
        if cur is None:
            cur = tgt.copy()
        else:
            cur = cur + (tgt - cur) * (0.2 if cid == last_id else 0.12)
            if np.abs(cur - tgt).max() < 3.0:
                cur = tgt.copy()
        if f is not None and not contains(tuple(cur), f, 1) and np.abs(cur - tgt).max() < 0.2 * BWp:
            pass
        moving = bool(np.abs(cur - tgt).max() > 0.5)
        v = 0
        if not moving:
            fr = rd.get(k)
            I = _ink_integral(fr, curs[k] if k < len(curs) else None, dsf)
            x, y, w, h = [int(round(q)) for q in cur]
            v = int(_cnt(I, x, y, x + w, y + bwc) > 0)
            if y + h < H0 - 2:
                v += int(_cnt(I, x, y + h - bwc, x + w, y + h) > 0)
            if x > 2:
                v += int(_cnt(I, x, y, x + bwc, y + h) > 0)
            if x + w < W0 - 2:
                v += int(_cnt(I, x + w - bwc, y, x + w, y + h) > 0)
        last_id = cid
        out.append(cur.copy())
        tgts.append(tgt.copy())
        focus.append((None if f is None else f.copy(), None if f is None else f.copy()))
        transit.append(moving)
        beats.append((cid, t1["zoom"]))
        viol.append(v)
        fabhit.append(t1["fh"])
        fails_l.append(t1["fl"])
    return dict(cams=out, tgts=tgts, focus=focus, transit=transit, beats=beats, snaps=0, viol=viol, fabhit=fabhit, fails=fails_l, fixed=True)


def disp_rect(o, crop):
    """畫面框：依取景框比例縮放、置中於畫面框區域。回傳（x, y, w, h, 縮放倍率）。"""
    cx, cy, cw, ch = crop
    sc = min(o.pw / cw, o.ph / ch, 3.0 / disp_rect.dsf)   # 放大倍率上限：每 css px 最多放成 3 px
    dw, dh = int(round(cw * sc)), int(round(ch * sc))
    return o.panel[0] + (o.pw - dw) // 2, (o.panel[1] + (o.ph - dh) // 2) if o.dev == "d" else o.panel[1], dw, dh, sc   # 手機版靠上對齊（緊接比比與泡泡下方）


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
            t0 = s["start"] + b["t"] + (0.25 if s is not shots[0] and i == 0 else 0.0)
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
    s1 = END_CTA
    w_, h_, b_ = tsize(big, s1)
    cx = (x0 + x1) / 2
    cy = y0 + (y1 - y0) * (0.30 if o.dev == "d" else 0.30)
    bx0, by0, bx1, by1 = cx - w_ / 2 - 54, cy - h_ / 2 - 36, cx + w_ / 2 + 54, cy + h_ / 2 + 36
    d.rounded_rectangle([bx0, by0 + 10, bx1, by1 + 10], 46, fill=(180, 70, 55, int(255 * a)))
    d.rounded_rectangle([bx0, by0, bx1, by1], 46, fill=CORAL + (int(255 * a),))
    d.text((cx - w_ / 2 - b_[0], cy - h_ / 2 - b_[1]), s1, font=big, fill=WHITE + (int(255 * a),))
    reg.add("搜尋鈕", (bx0, by0, bx1, by1 + 10))
    f2 = font(F_BOLD, 40 if o.dev == "d" else 40)
    yy = by1 + 60
    for s in (END_LINES_D if o.dev == "d" else END_LINES_M):
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
    if DATA_ASOF:
        data_date = DATA_ASOF() or data_date
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
    nav_keys = [k for k, _ in NAV]

    def static_for(sid, cur):
        key = (sid, cur)
        if key not in statics:
            im = Image.fromarray(bg.copy())
            reg_ = Reg()
            header(o, im, reg_, sid, data_date)
            nav(o, im, reg_, sid, cur)
            statics[key] = (np.array(im), reg_.items, reg_.issues)
        return statics[key]

    def step_at(t):
        cur = -1
        for s_ in shots:
            for m in s_["meta"]["marks"]:
                if m[1] == "step" and s_["start"] + m[0] <= t + 1e-6 and m[2] in nav_keys:
                    cur = nav_keys.index(m[2])
        return cur
    _masks = {}

    def mask_for(w_, h_):
        if (w_, h_) not in _masks:
            m_ = Image.new("L", (w_, h_), 0)
            ImageDraw.Draw(m_).rounded_rectangle([0, 0, w_ - 1, h_ - 1], 20, fill=255)
            _masks[(w_, h_)] = (np.array(m_).astype(np.float32) / 255)[..., None]
        return _masks[(w_, h_)]
    disp_rect.dsf = shots[0]["meta"]["dsf"]
    _ct = cam_track3 if (FIXED_BOX and dev == "d") else cam_track2
    cams = {s["sid"]: _ct(o, s["meta"], s["path"], s["sid"]) for s in shots}
    N = int(round(total * FPS))
    frames = [int(round(float(x) * FPS)) for x in only.split(",")] if only else range(N)
    out_mp4 = SCR / (f"{NAME}_{dev}_silent.mp4" if not seg else f"seg/{NAME}_{dev}_{seg}.mp4")
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    ff = None
    if not only:
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{o.W}x{o.H}",
                               "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18" if not seg else "30", "-preset", "medium", "-pix_fmt", "yuv420p",
                               str(out_mp4)], stdin=subprocess.PIPE)
    readers = {}
    rows, issues, click_rows, still = [], [], [], []
    bub_final = []
    for bb_ in bubbles:   # 每泡成片上至少停 0.9 秒（原片 ≥ 0.9×倍速）；片尾免責卡另計
        bub_final.append(round((bb_["t1"] - bb_["t0"]) / SPEED, 2))
        if (bb_["t1"] - bb_["t0"]) / SPEED < BUBBLE_MIN - 1e-3 and not only and bb_["sid"] != "__end":
            issues.append(f"| {bb_['t0']:6.2f} | 泡泡成片停留 {(bb_['t1'] - bb_['t0']) / SPEED:.2f} 秒（<{BUBBLE_MIN}）：{bb_['text']} |")
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

    chk = {sid: dict(cut=[], edge=[], transit=0, fill={}, ppc={}, ppc_cid={}, occ=[], cur=[]) for sid in ORDER}
    EDGE_SIDS = {"m": ("rel", "end"), "d": ()}[dev]

    def crop_px(fr, x, y, w, h):
        """裁切（可超出錄影畫面：超出的部分補網頁底色＝畫面最左一欄的中位色）。"""
        Hs, Ws = fr.shape[:2]
        x0, y0 = int(round(x)), int(round(y))
        x1, y1 = int(round(x + w)), int(round(y + h))
        if x0 >= 0 and y0 >= 0 and x1 <= Ws and y1 <= Hs:
            return fr[y0:y1, x0:x1]
        strip = fr[Hs // 4:Hs * 3 // 4, Ws - 3:Ws] if x1 > Ws else fr[Hs // 4:Hs * 3 // 4, 0:3]
        bgc = np.median(strip.reshape(-1, 3), axis=0).astype(np.uint8)
        outp = np.empty((y1 - y0, x1 - x0, 3), np.uint8)
        outp[:] = bgc
        sx0, sy0, sx1, sy1 = max(0, x0), max(0, y0), min(Ws, x1), min(Hs, y1)
        if sx1 > sx0 and sy1 > sy0:
            outp[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = fr[sy0:sy1, sx0:sx1]
        return outp

    def panel_of(s, k, check=True):
        sid = s["sid"]
        if sid not in readers:
            readers[sid] = Reader(s["path"])
        fr = readers[sid].get(min(k, s["n"] - 1))
        T = cams[sid]
        kk = min(k, len(T["cams"]) - 1)
        c0 = T["cams"][kk]
        # 停格檢查用「沒加慢移」的原始鏡頭畫面
        raw_view["v"] = cv2.resize(crop_px(fr, *c0), (o.pw // 4, o.ph // 4), interpolation=cv2.INTER_AREA).astype(np.int16)
        tt = s["start"] + k / FPS
        cx, cy, cw, ch = [float(q) for q in c0]
        crop = crop_px(fr, cx, cy, cw, ch)
        if T.get("fixed"):
            scf = o.pw / (FIXED_BOX["bw"] * s["meta"]["dsf"])
            wi, hi = min(o.pw, int(round(cw * scf))), min(o.ph, int(round(ch * scf)))
            small = cv2.resize(crop, (wi, hi), interpolation=cv2.INTER_AREA if scf < 1 else cv2.INTER_CUBIC)
            img = np.empty((o.ph, o.pw, 3), np.uint8)
            img[:] = np.median(small[-3:, :, :].reshape(-1, 3), axis=0).astype(np.uint8)
            if wi < o.pw:
                img[:hi, wi:] = np.median(small[:, -3:, :].reshape(-1, 3), axis=0).astype(np.uint8)
            img[:hi, :wi] = small
            drect = (o.panel[0], o.panel[1], o.pw, o.ph, scf)
        else:
            drect = disp_rect(o, (cx, cy, cw, ch))
            img = cv2.resize(crop, (drect[2], drect[3]), interpolation=cv2.INTER_AREA if cw > drect[2] else cv2.INTER_CUBIC)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        f_raw, f = T["focus"][kk]
        cid, zoom = T["beats"][kk]
        if check and k < s["n"]:
            C_ = chk[sid]
            if T["transit"][kk]:
                C_["transit"] += 1
            elif f_raw is not None:
                if not contains((cx, cy, cw, ch), f_raw, 0.5):
                    C_["cut"].append(round(tt, 2))
                if sid in EDGE_SIDS:
                    eds = (s["meta"].get("edges") or [])
                    for e in (eds[kk] if kk < len(eds) else []):
                        ix = min(e[0] + e[2], cx + cw) - max(e[0], cx)
                        iy = min(e[1] + e[3], cy + ch) - max(e[1], cy)
                        if ix > 0.5 and iy > 0.5 and not contains((cx, cy, cw, ch), e, 0.5):
                            C_["edge"].append(round(tt, 2))
                            break
                lab = next((m[2] for m in reversed([m for m in s["meta"]["marks"] if m[1] == "cam"]) if m[0] <= k / FPS + 1e-6), "")
                if zoom:
                    C_["fill"][lab] = min(C_["fill"].get(lab, 9), f_raw[2] / cw)
                C_["ppc"][lab] = min(C_["ppc"].get(lab, 99), drect[4] * s["meta"]["dsf"])
                C_["ppc_cid"][cid] = min(C_["ppc_cid"].get(cid, 99), drect[4] * s["meta"]["dsf"])
            if T["transit"][kk]:
                C_["moving"] = C_.get("moving", 0) + 1
            elif T["viol"][kk]:
                C_["edge"].append(round(tt, 2))
            occ_m = s["meta"].get("occ") or []
            if kk < len(occ_m) and occ_m[kk]:
                C_["occ"].append((round(tt, 2), "；".join(occ_m[kk])))
            if kk in s["meta"].setdefault("_curset", {int(round(r_[0] * FPS)) for r_ in (s["meta"].get("cursor_rows") or [])}):
                C_["cur"].append(round(tt, 2))
        fbs = s["meta"].get("fabs") or []
        fb = fbs[kk] if kk < len(fbs) else None
        raw_view["fab_hit"] = 0
        if fb:   # 網站右下角客服鈕有入鏡就記一筆（鏡頭應該避開它）
            vx = min(fb[0] + fb[2], cx + cw) - max(fb[0], cx)
            vy = min(fb[1] + fb[3], cy + ch) - max(fb[1], cy)
            if vx > 0 and vy > 0:
                raw_view["fab_hit"] = int(vx * vy)
        # 10-21（Andy：不准遮擋）：取消框外淡化霧罩與藍色外框，框內任何內容都不被蓋住、不被淡掉
        return img, drect

    for i in frames:
        t = i / FPS
        reg = Reg()
        if t >= end_start + XF / FPS:
            sid = "end"
        else:
            sid = [s for s in shots if s["start"] <= t + 1e-6][-1]["sid"]
        base, items, iss = static_for(sid if sid != "end" else "end", 99 if sid == "end" else step_at(t))
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
            panel, drect = panel_of(s, k)
            panel = panel.astype(np.float32)
            reg.add("網站畫面框", (drect[0] - 3, drect[1] - 3, drect[0] + drect[2] + 3, drect[1] + drect[3] + 3))
        if t >= end_start and sid != "end":
            pass
        if panel is not None:
            dx_, dy_, dw_, dh_, _sc = drect
            pim = Image.fromarray(canvas)
            ImageDraw.Draw(pim).rounded_rectangle([dx_ - 3, dy_ - 3, dx_ + dw_ + 3, dy_ + dh_ + 3], 22, fill=BLUE)
            canvas = np.array(pim)
            mk = mask_for(dw_, dh_)
            region = canvas[dy_:dy_ + dh_, dx_:dx_ + dw_].astype(np.float32)
            canvas[dy_:dy_ + dh_, dx_:dx_ + dw_] = (panel * mk + region * (1 - mk)).astype(np.uint8)
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
            if len(b["text"].replace(' ', '')) > 14:
                issues.append(f"| {t:6.2f} | 泡泡超過 14 字：{b['text']} |")
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
                issues.append(f"| {t:6.2f} | 客服鈕入鏡 {raw_view['fab_hit']}px² |")
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
        cams_s = cams[s["sid"]]["cams"]
        for c in s["meta"]["clicks"]:
            if c["kind"] != "click":
                kind = "拖曳起點"
            else:
                kind = "點擊"
            k = min(int(round(c["t"] * FPS)), len(cams_s) - 1)
            cx, cy, cw, ch = [float(q) for q in cams_s[k]]
            if cams[s["sid"]].get("fixed"):
                scr = o.pw / (FIXED_BOX["bw"] * s["meta"]["dsf"])
                dxr, dyr = o.panel[0], o.panel[1]
                dwr, dhr = int(cw * scr), int(ch * scr)
            else:
                dxr, dyr, dwr, dhr, scr = disp_rect(o, (cx, cy, cw, ch))
            px, py = c["center"]
            ox_ = dxr + (px - cx) * scr
            oy_ = dyr + (py - cy) * scr
            inside = dxr + 4 <= ox_ <= dxr + dwr - 4 and dyr + 4 <= oy_ <= dyr + dhr - 4
            rc = c.get("rect_center")
            err = math.hypot(px - rc[0], py - rc[1]) if rc else None
            blank = (c.get("selector") or "").startswith("#mSheetBack") or bool(c.get("blank"))
            click_rows.append((s["sid"], round(float(s["start"] + c["t"]), 2), kind, c.get("label") or c.get("text"), None if err is None else round(float(err), 2), bool(inside), bool(blank), (int(round(ox_)), int(round(oy_)))))
    cut_rows = [(s["sid"], len(chk[s["sid"]]["cut"])) for s in shots]
    edge_rows = [(s["sid"], len(chk[s["sid"]]["edge"])) for s in shots]
    transit_rows = [(s["sid"], chk[s["sid"]]["transit"]) for s in shots]
    ppc_rows = [(s["sid"], {k: round(v, 2) for k, v in chk[s["sid"]]["ppc"].items()}) for s in shots]
    # 遮擋：網頁上被別的東西蓋住（提示框、下拉清單、面板、頂欄、客服鈕）＋游標落在被介紹元素上（點擊窗口以外）＋客服鈕入鏡＋渲染器浮層壓到畫面框
    occ_site = sorted({t_ for s in shots for t_, _ in chk[s["sid"]]["occ"]})
    occ_cur = sorted({t_ for s in shots for t_ in chk[s["sid"]]["cur"]})
    occ_ren = [r for r in rows if "網站畫面框" in r]
    fab_in = [x for x in issues if "客服鈕入鏡" in x]
    occ_detail = {s["sid"]: chk[s["sid"]]["occ"][:30] for s in shots}
    # 主要文字成片字高：每一拍（cam_id）的字級第 15 百分位 × 最小倍率
    font_rows = []
    for s in shots:
        for cid, v in (s["meta"].get("fonts") or {}).items():
            ppc = chk[s["sid"]]["ppc_cid"].get(int(cid))
            if ppc:
                font_rows.append((s["sid"], int(cid), v[0], round(v[1], 1), round(ppc, 2), round(v[1] * ppc, 1)))
    small_text = [r for r in font_rows if r[5] < 20]
    print("裁切", cut_rows, "框邊切卡", edge_rows, "推移", transit_rows)
    print("遮擋：網頁", len(occ_site), "幀｜游標", len(occ_cur), "幀｜渲染浮層", len(occ_ren), "筆｜客服鈕入鏡", len(fab_in), "幀")
    print("字高<20px 的鏡頭：", small_text)
    meta_out = dict(dev=dev, total=total, end_start=end_start, frames=N, overlaps=len(rows), issues=len(issues),
                    still_max_s=round(float(max_run[0]) / FPS, 2), still_at=round(float(max_run[1]), 2), cut_frames=cut_rows, edge_frames=edge_rows, transit_frames=transit_rows, ppc=ppc_rows,
                    cut_detail={k: v['cut'][:20] for k, v in chk.items()}, edge_cut={k: v['edge'][:40] for k, v in chk.items()}, moving_frames={k: v.get('moving', 0) for k, v in chk.items()}, fab_hit={sid_: int(sum(cams[sid_]['fabhit'])) for sid_ in cams}, snap_fail={sid_: int(sum(1 for q in cams[sid_]['fails'] if q)) for sid_ in cams}, occ_site=occ_site[:60], occ_cursor=occ_cur[:60], occ_render=len(occ_ren), fab_in=len(fab_in), occ_detail=occ_detail,
                    font_rows=font_rows, small_text=small_text, bubble_final=bub_final, speed=SPEED, final_len=round(total / SPEED, 2),
                    clicks=click_rows, bubbles=[(round(b["t0"], 2), round(b["t1"], 2), b["text"], b["act"], b["sid"]) for b in bubbles],
                    shots=[(s["sid"], round(s["start"], 2), round(s["n"] / FPS, 2)) for s in shots], data_date=data_date,
                    says_raw=[(s["sid"], s["meta"]["says"]) for s in shots], steps=[(s["sid"], [m for m in s["meta"]["marks"] if m[1] in ("step", "cam")]) for s in shots])
    (SCR / f"render_{dev}.json").write_text(json.dumps(meta_out, ensure_ascii=False, indent=1), encoding="utf-8")
    (SCR / f"overlap_rows_{dev}.md").write_text("\n".join(rows[:500] + ["", "問題："] + issues[:500]), encoding="utf-8")
    print("重疊", len(rows), "問題", len(issues), "幀", N, "畫面框最長不動", max_run[0] / FPS, "秒 @", max_run[1], "｜成片長", round(total / SPEED, 2), "秒")
    # 配樂＋點擊音效
    cues = {"cues": [[r[1] / SPEED, "tap"] for r in click_rows if r[2] == "點擊"] + [[(end_start + 0.3) / SPEED, "ding"]]}
    cj = SCR / f"cues_{dev}.json"
    cj.write_text(json.dumps(cues), encoding="utf-8")
    wav = SCR / f"bgm_{dev}.wav"
    subprocess.run([sys.executable, str(REPO / "docs/marketing/video_1010/make_music_v3.py"), "--length", f"{total / SPEED + 0.3:.2f}",
                    "--style", "cute", "--out", str(wav), "--cues", str(cj)], check=True)
    final = SCR / f"{NAME}_{'web' if dev == 'd' else 'mobile'}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out_mp4), "-i", str(wav), "-filter:v", f"setpts=PTS/{SPEED}", "-r", str(FPS),
                    "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                    "-shortest", "-movflags", "+faststart", str(final)], check=True)
    print("成片", final)


def configure(**kw):
    """各支設定：SCR、RAW、NAME、SEC、NAV、END_LINES_D、END_LINES_M、ORDER…（直接覆蓋本模組全域）。"""
    g = globals()
    for k, v in kw.items():
        g[k] = v
    g["RAW"] = Path(kw["RAW"]) if "RAW" in kw else Path(g["SCR"]) / "raw"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", default="d", choices=["d", "m"])
    ap.add_argument("--frames", default="")
    ap.add_argument("--seg", default="")
    g = ap.parse_args()
    render(g.dev, g.frames or None, g.seg or None)


if __name__ == "__main__":
    main()
