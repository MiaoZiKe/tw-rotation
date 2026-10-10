"""哩股哩股宣傳片第 3 版渲染器（網頁版 1920×1080 橫式／手機版 1080×1920 直式）。

沿用 render_1010.py 的素材讀取、比比精靈圖與緩動函式；這支只放 v3 新增的東西：
- Layout：兩種輸出格式的版面（展示框吃滿版面、字卡與比比放在窄邊）
- Rec3：錄影卡。完整入框 → 推近時視窗寬度不小於展示框寬度（素材不放大超過原解析度）
- FocusBox：「發光框焦點」—— 完整畫面停住 → 方框沿邊描出＋輕微外光（不閃、不脈動）→ 推近放大框內
  三種樣式：square（方框）、round_tag（圓角框＋角標）、dashed（虛線描邊）
- 全片取消模糊（Andy 10-11：全部資訊公開）；每段畫面下方固定小字（歷史資料提醒）；不提次數與會員層級
- 片尾卡、警語卡內容置中重新設計；警語卡從上一鏡交叉溶接，不留空白格

用法（樣片）：python render_v3.py --sample <out.mp4> --fmt web|mobile [--audio wav]
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_1010 as B  # noqa: E402
from render_1010 import (CREAM, DEEP, INK, LEMON, SKY, WHITE, F_BOLD, F_MED, F_ROUND, FPS, anim_frame, back_out,  # noqa: E402
                         clamp, ease_io, ease_out, font, hide_site_mascot, lerp, logo_sized, piecewise, put_sprite,
                         reader, rounded_mask, text_w, wrap_lines)

# 第 3 版素材在 raw_v3/；同名找不到時才退回舊的 raw/
_SR = B.SourceReader


class _SR3(_SR):
    def __init__(self, clip):
        v3 = B.SCR / "video1010" / "raw_v3" / f"{clip}.mp4"
        if v3.exists():
            old = B.RAW
            B.RAW = v3.parent
            try:
                super().__init__(clip)
            finally:
                B.RAW = old
        else:
            super().__init__(clip)


B.SourceReader = _SR3

FOOTNOTE = "畫面數據為過往歷史資料，僅供功能展示，不具投資參考價值"
GLOW = (255, 196, 40)


# ───────────────────────── 版面 ─────────────────────────
class Layout:
    def __init__(self, fmt):
        self.fmt = fmt
        self.full_bleed = fmt == "web"
        if fmt == "web":
            # 10-11 Andy「網頁版就直接整個滿版」：錄影鋪滿 1920×1080，文字改半透明圓角浮層
            self.W, self.H = 1920, 1080
            self.box = (0, 0, 1920, 1080)
            self.head_px = 68
            self.head_w = 720
            self.host_size = 270
            self.sub_px = 40
            self.sub_chars = 30
            self.foot_y = 1046
            self.side = "L"              # 浮層放哪一側（依焦點自動換邊）
            self.set_side("L")
        else:
            self.W, self.H = 1080, 1920
            self.box = (24, 384, 1032, 1000)
            self.pill_xy = (40, 214)
            self.head_xy = (40, 284)
            self.head_w = 1000
            self.head_px = 84
            self.host = (150, 1520)
            self.host_size = 300
            self.sub_xy = (290, 1428)
            self.sub_px = 44
            self.sub_chars = 14
            self.foot_y = 1556
            self.data_xy = (24 + 1032 - 16, 384 + 1000 - 14)


def _set_side(self, side):
    """浮層與比比放在焦點的另一側。"""
    self.side = side
    if side == "L":
        self.pill_xy = (44, 30); self.pill_right = False; self.head_xy = (52, 112)
        self.sub_xy = (78, 958); self.sub_align = "L"
        self.host = (1800, 1010); self.data_xy = (1904, 52)
    else:
        self.pill_xy = (1876, 30); self.pill_right = True; self.head_xy = (1920 - 52 - 720, 112)
        self.sub_xy = (1842, 958); self.sub_align = "R"
        self.host = (130, 1010); self.data_xy = (420, 52)


Layout.set_side = _set_side


def float_panel(cv, box, alpha=214, r=26):
    x0, y0, x1, y1 = [int(v) for v in box]
    lay = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
    ImageDraw.Draw(lay).rounded_rectangle([0, 0, x1 - x0 - 1, y1 - y0 - 1], r, fill=(255, 252, 244, alpha), outline=DEEP + (120,), width=2)
    cv.paste(lay, (x0, y0), lay)


@lru_cache(maxsize=2)
def background(fmt):
    L = Layout(fmt)
    bg = Image.new("RGB", (L.W, L.H), CREAM)
    ov = Image.new("RGBA", (L.W, L.H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for x in range(0, L.W, 60):
        d.line([(x, 0), (x, L.H)], fill=SKY + (24,), width=2)
    for y in range(0, L.H, 60):
        d.line([(0, y), (L.W, y)], fill=SKY + (24,), width=2)
    bg.paste(ov, (0, 0), ov)
    return bg


# ───────────────────────── 文字 ─────────────────────────
def pill(cv, text, x, y, bg=SKY, fg=WHITE, px=32, stroke=True, right=False, center=False, alpha=1.0):
    f = font(F_ROUND, px)
    tw = text_w(f, text)
    pw, ph = tw + 44, px + 28
    if right:
        x -= pw
    if center:
        x -= pw / 2
    lay = Image.new("RGBA", (int(pw) + 8, int(ph) + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([2, 2, pw + 2, ph + 2], ph / 2, fill=bg + (255,), outline=INK + (255,), width=3)
    d.text((24, 13), text, font=f, fill=fg, stroke_width=3 if stroke else 0, stroke_fill=INK)
    if alpha < 1:
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * alpha)))
    cv.paste(lay, (int(x), int(y)), lay)
    return pw


def headline(cv, L, text, t, hl=None):
    """大字：一字一字彈上來；關鍵詞底下檸檬黃螢光筆。web 版在右側窄欄自動換行。"""
    if not text:
        return
    px = L.head_px
    f = font(F_ROUND, px)
    if text_w(f, text) <= L.head_w:
        lines = [text]
    else:
        # 兩行、盡量平均；不把螢光筆關鍵詞拆開
        best = None
        for i in range(1, len(text)):
            if hl and hl in text and text.index(hl) < i < text.index(hl) + len(hl):
                continue
            a_, b_ = text[:i], text[i:]
            sc = abs(len(a_) - len(b_)) + (0 if a_[-1] in "，、？！" else 0.5)
            if best is None or sc < best[0]:
                best = (sc, [a_, b_])
        lines = best[1]
        while max(text_w(f, ln) for ln in lines) > L.head_w and px > 40:
            px -= 4
            f = font(F_ROUND, px)
    x0, y0 = L.head_xy
    if getattr(L, "full_bleed", False):
        wmax = max(text_w(f, ln) for ln in lines)
        if L.side == "R":
            x0 = L.W - 52 - wmax
        a_ = clamp(t / 0.2, 0, 1)
        if a_ > 0:
            float_panel(cv, (x0 - 26, y0 - 10, x0 + wmax + 26, y0 + len(lines) * px * 1.22 + 18), int(214 * a_))
    d = ImageDraw.Draw(cv)
    k = 0
    hl_span = (text.index(hl), text.index(hl) + len(hl)) if hl and hl in text else None
    for li, ln in enumerate(lines):
        y = y0 + li * px * 1.22
        x = x0
        for ch in ln:
            w = text_w(f, ch)
            if hl_span and hl_span[0] <= k < hl_span[1]:
                u = ease_out((t - 0.35 - 0.04 * (k - hl_span[0])) / 0.2)
                if u > 0:
                    d.rounded_rectangle([x - 2, y + px * 0.78, x + w * u + 2, y + px * 1.08], 8, fill=LEMON)
            u = ease_out((t - 0.04 * k) / 0.22)
            if u > 0:
                lay = Image.new("RGBA", (int(w) + 16, px + 40), (0, 0, 0, 0))
                ImageDraw.Draw(lay).text((6, 10), ch, font=f, fill=INK + (int(255 * u),))
                cv.paste(lay, (int(x) - 6, int(y + (1 - u) * 20) - 10), lay)
            x += w
            k += 1


def subtitle(cv, L, text, t):
    if not text:
        return
    f = font(F_BOLD, L.sub_px)
    lines = wrap_lines(text, L.sub_chars) if len(text) > L.sub_chars else [text]
    a = clamp(t / 0.2, 0, 1)
    lay = Image.new("RGBA", (L.W, L.sub_px * 3 + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x, y = L.sub_xy
    if getattr(L, "full_bleed", False):
        lines = lines[:1] if len(text) <= 34 else lines[:2]
        if len(lines) == 1:
            pass
        wmax = max(text_w(f, ln) for ln in lines)
        if L.sub_align == "R":
            x = x - wmax
        nl = len(lines)
        y = y - (nl - 1) * L.sub_px * 1.32
        d.rounded_rectangle([x - 36, 0, x + wmax + 24, nl * L.sub_px * 1.32 + 22], 24, fill=(255, 252, 244, 222), outline=DEEP + (120,), width=2)
        for i, ln in enumerate(lines):
            d.text((x, 8 + i * L.sub_px * 1.32), ln, font=f, fill=INK)
    else:
        d.polygon([(x - 26, 18), (x - 2, 4), (x - 8, 36)], fill=INK + (255,))
        for i, ln in enumerate(lines[:2]):
            d.text((x, i * L.sub_px * 1.32), ln, font=f, fill=INK, stroke_width=5, stroke_fill=CREAM)
    if a < 1:
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a)))
    cv.paste(lay, (0, int(y)), lay)


def footnote(cv, L):
    f = font(F_MED, 24 if L.fmt == "web" else 26)
    tw = text_w(f, FOOTNOTE)
    d = ImageDraw.Draw(cv)
    x = L.W / 2 - tw / 2
    if getattr(L, "full_bleed", False):
        float_panel(cv, (x - 16, L.foot_y - 6, x + tw + 16, L.foot_y + 30), 200, 16)
    d.text((x, L.foot_y), FOOTNOTE, font=f, fill=(80, 80, 80))


def data_tag(cv, L, date):
    f = font(F_MED, 24)
    s = f"網站實際畫面・資料日 {date}"
    tw = text_w(f, s)
    x1, y1 = L.data_xy
    x0, y0 = x1 - tw - 28, y1 - 40
    if getattr(L, "full_bleed", False) and L.side == "R":
        x0, y0 = 16, y1 - 40
    lay = Image.new("RGBA", (int(tw) + 32, 44), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([0, 0, tw + 28, 40], 20, fill=(255, 255, 255, 228), outline=DEEP + (200,), width=2)
    d.text((14, 5), s, font=f, fill=INK)
    cv.paste(lay, (int(x0), int(y0)), lay)


# ───────────────────────── 錄影卡＋發光框焦點 ─────────────────────────
class Rec3:
    """錄影卡：src_t(t) 對應來源秒；視窗由 FocusBox 決定（沒有 focus 就是完整入框）。"""

    def __init__(self, clip, srcmap, focus=None, full=None, hide_mascot=True):
        self.clip = clip
        self.srcmap = srcmap
        self.focus = focus
        self.full = full                 # 完整畫面的視窗（預設整張來源）
        self.hide_mascot = hide_mascot
        self.win = None
        self.rect = None

    def _fit(self, L, sw, sh):
        bx, by, bw, bh = L.box
        k = min(bw / sw, bh / sh)
        w, h = sw * k, sh * k
        return (bx + (bw - w) / 2, by + (bh - h) / 2, w, h)

    def window(self, t, src_w, src_h, L):
        fx0, fy0, fx1, fy1 = self.full or (0, 0, src_w, src_h)
        if not self.focus:
            return (fx0, fy0, fx1, fy1)
        u = self.focus.zoom_u(t)
        # 目標視窗：焦點框外留 6% 邊，維持輸出框比例；寬度不小於輸出寬（不放大超過原解析度）
        x0, y0, x1, y1 = self.focus.rect
        rw, rh = self.rect[2], self.rect[3]
        mx, my = (x1 - x0) * 0.06, (y1 - y0) * 0.06
        x0, y0, x1, y1 = x0 - mx, y0 - my, x1 + mx, y1 + my
        ar = rw / rh
        w, h = x1 - x0, y1 - y0
        if w / h < ar:
            w = h * ar
        else:
            h = w / ar
        min_w = rw * self.focus.max_up_inv
        if w < min_w:
            w, h = min_w, min_w / ar
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        cx = clamp(cx, fx0 + w / 2, fx1 - w / 2) if w < fx1 - fx0 else (fx0 + fx1) / 2
        cy = clamp(cy, fy0 + h / 2, fy1 - h / 2) if h < fy1 - fy0 else (fy0 + fy1) / 2
        tgt = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
        full = (fx0, fy0, fx1, fy1)
        # 完整畫面的比例 ≠ 輸出框比例時，推近過程同時把輸出框長到滿框
        return tuple(lerp(a, b, u) for a, b in zip(full, tgt))

    def map(self, sx, sy):
        x0, y0, x1, y1 = self.win
        rx, ry, rw, rh = self.rect
        return rx + (sx - x0) / (x1 - x0) * rw, ry + (sy - y0) / (y1 - y0) * rh

    def draw(self, cv, t, shot):
        L = shot.L
        st = piecewise(self.srcmap, t)
        src = reader(self.clip).get(st)
        if self.hide_mascot:
            src = src.copy(); hide_site_mascot(src)
        fx0, fy0, fx1, fy1 = self.full or (0, 0, src.width, src.height)
        full_rect = self._fit(L, fx1 - fx0, fy1 - fy0)
        u = self.focus.zoom_u(t) if self.focus else 0
        box_rect = L.box
        self.rect = tuple(lerp(a, b, u) for a, b in zip(full_rect, box_rect)) if self.focus else full_rect
        self.win = self.window(t, src.width, src.height, L)
        rx, ry, rw, rh = [int(round(v)) for v in self.rect]
        im = src.resize((rw, rh), Image.LANCZOS if rw <= (self.win[2] - self.win[0]) else Image.BICUBIC, box=self.win)
        tile = im.convert("RGBA")
        if not getattr(L, "full_bleed", False) or (rw, rh) != (L.W, L.H):
            tile.putalpha(rounded_mask(rw, rh, 28))
            ImageDraw.Draw(tile).rounded_rectangle([1, 1, rw - 2, rh - 2], 28, outline=DEEP + (255,), width=3)
        cv.paste(tile, (rx, ry), tile)
        if self.focus:
            self.focus.draw(cv, t, self)


class FocusBox:
    """發光框焦點。

    t_draw：開始描框（之前是完整畫面停住）；描框 d_draw 秒；t_zoom 開始推近，d_zoom 秒推完。
    style：square / round_tag / dashed；tag：round_tag 的角標文字。
    max_up：最多放大到原解析度的幾倍（1.0 = 不超過原解析度）。
    """

    def __init__(self, rect, t_draw=1.2, d_draw=0.7, t_zoom=2.2, d_zoom=1.0, style="square", tag=None, max_up=1.0,
                 dim=0.16):
        self.rect = rect
        self.t_draw, self.d_draw, self.t_zoom, self.d_zoom = t_draw, d_draw, t_zoom, d_zoom
        self.style, self.tag = style, tag
        self.max_up_inv = 1 / max_up
        self.dim = dim

    def zoom_u(self, t):
        return ease_io((t - self.t_zoom) / self.d_zoom)

    def draw(self, cv, t, rec):
        if t < self.t_draw:
            return
        u = clamp((t - self.t_draw) / self.d_draw, 0, 1)
        x0, y0 = rec.map(self.rect[0], self.rect[1])
        x1, y1 = rec.map(self.rect[2], self.rect[3])
        rx, ry, rw, rh = rec.rect
        x0, y0, x1, y1 = max(x0, rx + 6), max(y0, ry + 6), min(x1, rx + rw - 6), min(y1, ry + rh - 6)
        zu = self.zoom_u(t)
        # 框外輕微壓暗（描框時淡入、推近時淡出），一次到位，不閃
        a_dim = self.dim * ease_io(u) * (1 - zu)
        if a_dim > 0.005:
            m = Image.new("L", (int(rw), int(rh)), int(255 * a_dim))
            ImageDraw.Draw(m).rounded_rectangle([x0 - rx, y0 - ry, x1 - rx, y1 - ry], 18, fill=0)
            m = Image.fromarray(np.minimum(np.array(m), np.array(rounded_mask(int(rw), int(rh), 28))))
            dk = Image.new("RGBA", (int(rw), int(rh)), (20, 30, 50, 255))
            dk.putalpha(m)
            cv.paste(dk, (int(rx), int(ry)), dk)
        r = 6 if self.style == "square" else 22
        path = _rect_path(x0, y0, x1, y1, r)
        lay = Image.new("RGBA", cv.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        pts = _partial(path, ease_io(u))
        col = GLOW if self.style != "dashed" else SKY
        if len(pts) > 1:
            if self.style == "dashed":
                _dashed(d, pts, col + (255,), 7, 22, 12)
            else:
                d.line(pts, fill=col + (255,), width=7, joint="curve")
        # 輕微外光：描完之後淡入，固定不變（不脈動）
        g = ease_io((t - self.t_draw - self.d_draw * 0.7) / 0.35)
        if g > 0 and self.style != "dashed":
            glow = Image.new("RGBA", cv.size, (0, 0, 0, 0))
            ImageDraw.Draw(glow).rounded_rectangle([x0, y0, x1, y1], r, outline=col + (int(150 * g),), width=18)
            glow = glow.filter(ImageFilter.GaussianBlur(10))
            cv.paste(glow, (0, 0), glow)
        cv.paste(lay, (0, 0), lay)
        if self.style == "round_tag" and self.tag:
            tu = back_out((t - self.t_draw - self.d_draw) / 0.3)
            if tu > 0:
                f = font(F_ROUND, 30)
                pw = text_w(f, self.tag) + 36
                tx, ty = x0 + 14, y0 - 24
                tag = Image.new("RGBA", (int(pw) + 6, 54), (0, 0, 0, 0))
                td = ImageDraw.Draw(tag)
                td.rounded_rectangle([2, 2, pw, 50], 24, fill=GLOW + (255,), outline=INK + (255,), width=3)
                td.text((18, 8), self.tag, font=f, fill=INK)
                if tu < 1:
                    tag = tag.resize((max(1, int(tag.width * tu)), max(1, int(tag.height * tu))), Image.BILINEAR)
                cv.paste(tag, (int(tx), int(ty)), tag)


def _rect_path(x0, y0, x1, y1, r, n=8):
    """從左上角順時針的圓角矩形路徑點。"""
    pts = []
    corners = [(x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)]
    pts.append((x0 + r, y0))
    for cx, cy, a0 in corners:
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    pts.append((x0 + r, y0))
    return pts


def _partial(pts, u):
    seg = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])]
    goal = sum(seg) * u
    out, acc = [pts[0]], 0
    for (a, b), ln in zip(zip(pts, pts[1:]), seg):
        if acc + ln <= goal:
            out.append(b); acc += ln
        else:
            r = (goal - acc) / ln if ln else 0
            out.append((lerp(a[0], b[0], r), lerp(a[1], b[1], r)))
            break
    return out


def _dashed(d, pts, fill, width, dash, gap):
    carry, on = 0.0, True
    for a, b in zip(pts, pts[1:]):
        ln = math.hypot(b[0] - a[0], b[1] - a[1])
        pos = 0.0
        while pos < ln:
            step = min((dash if on else gap) - carry, ln - pos)
            p0 = (lerp(a[0], b[0], pos / ln), lerp(a[1], b[1], pos / ln))
            p1 = (lerp(a[0], b[0], (pos + step) / ln), lerp(a[1], b[1], (pos + step) / ln))
            if on:
                d.line([p0, p1], fill=fill, width=width)
            pos += step
            carry += step
            if carry >= (dash if on else gap) - 1e-6:
                carry, on = 0.0, not on


# ───────────────────────── 比比 ─────────────────────────
class Host:
    """簡化版主持：acts=[(t0, t1, 動畫名, 腳底(None=主持位), 大小(None=預設), 模式)]。"""

    def __init__(self, acts):
        self.acts = acts

    def draw(self, cv, t, shot):
        L = shot.L
        for t0, t1, name, foot, size, mode in self.acts:
            if t0 <= t < t1:
                put_sprite(cv, name, anim_frame(name, t - t0, mode), foot or L.host, size or L.host_size)
                return


# ───────────────────────── 比比操作（Andy 10-11：錄影裡每個點擊都由比比執行） ─────────────────────────
import re as _re

RAW_V3 = B.SCR / "video1010" / "raw_v3"


def parse_shots(md=None):
    """讀 raw_v3/shots.md → {clip: [{"t", "kind": tap|drag_start|drag_end, "x", "y"}...]}（影片像素）。"""
    md = Path(md or RAW_V3 / "shots.md")
    out, cur = {}, None
    for ln in md.read_text().splitlines():
        m = _re.match(r"^## (\S+)", ln)
        if m:
            cur = m.group(1); out[cur] = []; continue
        m = _re.search(r"([\d.]+)s (踩下|拖曳開始|拖曳放開) \([\d.]+,[\d.]+\)css → 影片\((\d+),(\d+)\)px", ln)
        if m and cur:
            kind = {"踩下": "tap", "拖曳開始": "drag_start", "拖曳放開": "drag_end"}[m.group(2)]
            out[cur].append({"t": float(m.group(1)), "kind": kind, "x": int(m.group(3)), "y": int(m.group(4))})
    return out


def _inv_srcmap(srcmap, st):
    """來源秒 → 本鏡秒（srcmap 單調遞增）。不在本鏡範圍回 None。"""
    for (t0, s0), (t1, s1) in zip(srcmap, srcmap[1:]):
        if s0 <= st <= s1 and s1 > s0:
            return t0 + (st - s0) / (s1 - s0) * (t1 - t0)
    return None


def ripple(cv, xy, age, small=False):
    """點擊漣漪：一圈擴散一次就淡掉（不重複、不閃）。"""
    if age < 0 or age > 0.55:
        return
    u = ease_out(age / 0.55)
    r = (26 if small else 46) + (34 if small else 70) * u
    a = int(220 * (1 - u))
    lay = Image.new("RGBA", (int(r * 2 + 12), int(r * 2 + 12)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    c = r + 6
    d.ellipse([c - r, c - r, c + r, c + r], outline=SKY + (a,), width=6 if not small else 4, fill=SKY + (a // 5,))
    cv.paste(lay, (int(xy[0] - c), int(xy[1] - c)), lay)


class Operator:
    """比比操作員：依 shots.md 的點擊／拖曳，比比跳過去踩下（bibi_tap）、或跟著拖曳方向推；點擊太密（<0.8 秒）就停在附近只出小漣漪。

    rec：要操作的錄影層（Rec3）；idle：沒在操作時的主持動畫；extra：額外主持動作 [(t0,t1,name,foot,size,mode)]
    magic：發光框出現前比比「畫框」（有 bibi_magic_frame 素材才用，否則用指示棒）。
    """

    TAP_CONTACT = 0.62     # tap 第 9 格（腳碰到按鈕）
    LEAD = 0.62

    def __init__(self, rec, events, idle="talk_happy", extra=(), tap_size=None, magic=True):
        self.rec, self.idle, self.extra, self.magic = rec, idle, list(extra), magic
        self.tap_size = tap_size
        self.taps, self.drags = [], []
        evs = sorted(events, key=lambda e: e["t"])
        last_full = -9
        for e in evs:
            lt = _inv_srcmap(rec.srcmap, e["t"])
            if lt is None:
                continue
            if e["kind"] == "tap":
                dense = lt - last_full < 0.8
                self.taps.append({"t": lt, "x": e["x"], "y": e["y"], "dense": dense})
                if not dense:
                    last_full = lt
            elif e["kind"] == "drag_start":
                self.drags.append({"t0": lt, "x0": e["x"], "y0": e["y"]})
            elif e["kind"] == "drag_end" and self.drags and "t1" not in self.drags[-1]:
                self.drags[-1].update({"t1": lt, "x1": e["x"], "y1": e["y"]})
        self.drags = [d for d in self.drags if "t1" in d]

    def _home(self, L):
        return L.host, L.host_size

    def draw(self, cv, t, shot):
        L = shot.L
        home, hs = self._home(L)
        ts = self.tap_size or int(hs * 0.8)
        for tp in self.taps:                         # 漣漪（踩下那一格起）
            if self.rec.win:
                ripple(cv, self.rec.map(tp["x"], tp["y"]), t - tp["t"], tp["dense"])
        for t0, t1, name, foot, size, mode in self.extra:
            if t0 <= t < t1:
                put_sprite(cv, name, anim_frame(name, t - t0, mode), foot or home, size or hs)
                return
        # 拖曳：比比站在游標後方，跟著方向推
        for d in self.drags:
            if d["t0"] - 0.35 <= t <= d["t1"] + 0.2:
                u = clamp((t - d["t0"]) / max(0.01, d["t1"] - d["t0"]), 0, 1)
                sx, sy = lerp(d["x0"], d["x1"], ease_io(u)), lerp(d["y0"], d["y1"], ease_io(u))
                px, py = self.rec.map(sx, sy)
                dx = 1 if d["x1"] >= d["x0"] else -1
                foot = (px - dx * ts * 0.28, py + ts * 0.32)
                ent = clamp((t - d["t0"] + 0.35) / 0.35, 0, 1)
                foot = (lerp(home[0], foot[0], ease_io(ent)), lerp(home[1], foot[1], ease_io(ent)) - 120 * math.sin(math.pi * ent) * (ent < 1))
                name = "hop_r" if dx > 0 else "hop_l"
                put_sprite(cv, name, anim_frame(name, t), foot, ts)
                return
        # 踩按鈕
        full = [tp for tp in self.taps if not tp["dense"]]
        for i, tp in enumerate(full):
            c = tp["t"]
            nxt = full[i + 1]["t"] if i + 1 < len(full) else 1e9
            prev_pos = self._pos(full[i - 1], L, ts) if i > 0 and c - full[i - 1]["t"] < 2.0 else (home, hs)
            if c - self.LEAD <= t < c:
                tap_t = t - (c - self.LEAD)
                tgt = self.rec.map(tp["x"], tp["y"])
                air0 = 0.29
                if tap_t < air0:
                    foot, size = prev_pos
                else:
                    uu = ease_io((tap_t - air0) / (self.TAP_CONTACT - air0))
                    foot = (lerp(prev_pos[0][0], tgt[0], uu), lerp(prev_pos[0][1], tgt[1], uu) - 150 * math.sin(math.pi * uu))
                    size = lerp(prev_pos[1], ts, uu)
                put_sprite(cv, "tap", anim_frame("tap", tap_t, "hold"), foot, size)
                return
            stay_until = min(nxt - self.LEAD, c + 0.9) if nxt - c < 2.0 else c + 0.45
            if c <= t < stay_until:
                fi = anim_frame("tap", self.TAP_CONTACT + (t - c), "hold")
                put_sprite(cv, "tap", fi, self.rec.map(tp["x"], tp["y"]), ts)
                return
            if nxt - c >= 2.0 and stay_until <= t < stay_until + 0.4:
                uu = ease_io((t - stay_until) / 0.4)
                a = self.rec.map(tp["x"], tp["y"])
                foot = (lerp(a[0], home[0], uu), lerp(a[1], home[1], uu) - 130 * math.sin(math.pi * uu))
                put_sprite(cv, "hop_l" if home[0] < a[0] else "hop_r", 2 + int(uu * 3.99), foot, lerp(ts, hs, uu))
                return
        # 發光框前「畫框」
        f = getattr(self.rec, "focus", None)
        if f and self.magic and f.t_draw - 0.3 <= t < f.t_draw + f.d_draw:
            name = "magic_frame" if "magic_frame" in B.bibi_index() else "pointer_l" if L.fmt == "web" else "pointer_r"
            put_sprite(cv, name, anim_frame(name, t - f.t_draw + 0.3, "hold"), home, hs)
            return
        put_sprite(cv, self.idle, anim_frame(self.idle, t), home, hs)

    def _pos(self, tp, L, ts):
        return self.rec.map(tp["x"], tp["y"]), ts


# ───────────────────────── 鏡頭 ─────────────────────────
class Shot3:
    def __init__(self, dur, layers=(), pill_text=None, head="", hl=None, sub="", host=None, date="2026-10-08",
                 foot=True, cues=(), kind="feature"):
        self.dur, self.layers = dur, list(layers)
        self.pill_text, self.head, self.hl, self.sub = pill_text, head, hl, sub
        self.host, self.date, self.foot = host, date, foot
        self.cues = list(cues)
        self.kind = kind
        self.L = None

    def render(self, t, L):
        self.L = L
        if getattr(L, "full_bleed", False):
            side = "L"
            for ly in self.layers:
                f = getattr(ly, "focus", None)
                if f:
                    cxn = (f.rect[0] + f.rect[2]) / 2 / reader(ly.clip).w
                    side = "R" if cxn < 0.5 else "L"
            L.set_side(getattr(self, "side", None) or side)
        cv = background(L.fmt).copy()
        for ly in self.layers:
            ly.draw(cv, t, self)
        if self.kind == "feature":
            if self.date:
                data_tag(cv, L, self.date)
            if self.pill_text:
                pill(cv, self.pill_text, *L.pill_xy, right=getattr(L, "pill_right", False))
            headline(cv, L, self.head, t, self.hl)
            subtitle(cv, L, self.sub, t)
        if self.foot:
            footnote(cv, L)
        if self.host:
            self.host.draw(cv, t, self)
        return cv


class Fn:
    def __init__(self, fn):
        self.fn = fn

    def draw(self, cv, t, shot):
        self.fn(cv, t, shot)


def bubble3(cv, text, box, tail, t, px=40):
    u = clamp(back_out(t / 0.25), 0, 1.1)
    if u <= 0.02:
        return
    x0, y0, x1, y1 = box
    w, h = int(x1 - x0) + 80, int(y1 - y0) + 80
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    ox, oy = x0 - 40, y0 - 40
    tl = (tail[0] - ox, tail[1] - oy)
    bx, by = 40, 40
    bw, bh = x1 - x0, y1 - y0
    d.polygon([(bx + 10, by + bh * 0.45), (bx + 10, by + bh * 0.85), tl], fill=WHITE, outline=INK, width=4)
    d.rounded_rectangle([bx, by, bx + bw, by + bh], 30, fill=WHITE, outline=INK, width=4)
    d.polygon([(bx + 13, by + bh * 0.48), (bx + 13, by + bh * 0.82), (tl[0] + 6, tl[1] - 3)], fill=WHITE)
    f = font(F_ROUND, px)
    tw = text_w(f, text)
    d.text((bx + bw / 2 - tw / 2, by + bh / 2 - px * 0.62), text, font=f, fill=INK)
    if u != 1:
        lay = lay.resize((max(1, int(w * u)), max(1, int(h * u))), Image.BILINEAR)
    cv.paste(lay, (int(ox), int(oy + h * (1 - u) / 2)), lay)


# ───────────────────────── 片尾卡、警語卡 ─────────────────────────
def end_card(dur=3.0, bubble_text="我們網站見，掰掰～"):
    def fn(cv, t, shot):
        L = shot.L
        W, H = L.W, L.H
        web = L.fmt == "web"
        logo_px = 300 if web else 440
        cy_logo = 250 if web else 640
        u = back_out(t / 0.45)
        px = max(8, int(logo_px * (0.85 + 0.15 * clamp(u, 0, 1.2))))
        lg = logo_sized(px)
        cv.paste(lg, (W // 2 - px // 2, cy_logo - px // 2), lg)
        f = font(F_ROUND, 96 if web else 120)
        title = "哩股哩股"
        tw = text_w(f, title)
        ty = cy_logo + logo_px / 2 + (30 if web else 40)
        a = ease_out((t - 0.2) / 0.3)
        d = ImageDraw.Draw(cv)
        if a > 0:
            d.rounded_rectangle([W / 2 - tw / 2 - 6, ty + f.size * 0.8, W / 2 - tw / 2 + (tw + 12) * a, ty + f.size * 1.1], 12, fill=LEMON)
            d.text((W / 2 - tw / 2, ty), title, font=f, fill=INK)
        b = ease_out((t - 0.45) / 0.3)
        if b > 0:
            py = ty + f.size * 1.45
            px1 = 44 if web else 50
            f2 = font(F_ROUND, px1)
            w1 = text_w(f2, "搜尋 哩股哩股") + 44
            w2 = text_w(f2, "免費註冊") + 44
            gap = 36
            x = W / 2 - (w1 + gap + w2) / 2
            pill(cv, "搜尋 哩股哩股", x, py, bg=WHITE, fg=INK, px=px1, stroke=False, alpha=b)
            pill(cv, "免費註冊", x + w1 + gap, py, bg=LEMON, fg=INK, px=px1, stroke=False, alpha=b)
        # 比比揮手：置中在下方，泡泡在右
        foot = (W / 2, (1000 if web else 1560))
        size = 330 if web else 460
        put_sprite(cv, "wave", anim_frame("wave", t), foot, size)
        if t > 0.6:
            bx0 = W / 2 + size * 0.30
            by0 = foot[1] - size * 0.70
            bubble3(cv, bubble_text, (bx0, by0, bx0 + (420 if web else 380), by0 + 100), (W / 2 + size * 0.2, foot[1] - size * 0.35), t - 0.6, 38)

    return Shot3(dur, [Fn(fn)], kind="card", foot=False, cues=[(0, "chord_end")])


def disclaimer_card(dur, prev=None, prev_L=None):
    cache = {}

    def fn(cv, t, shot):
        L = shot.L
        W, H = L.W, L.H
        web = L.fmt == "web"
        a = ease_io(t / 0.35)
        if prev is not None and a < 1:
            if "img" not in cache:
                cache["img"] = prev.render(prev.dur - 1 / FPS, L)
            cv.paste(Image.blend(cache["img"], background(L.fmt), a), (0, 0))
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        lg_px = 140 if web else 170
        top = 110 if web else 300
        lg = logo_sized(lg_px)
        lay.paste(lg, (W // 2 - lg_px // 2, top), lg)
        fs = font(F_MED, 28 if web else 30)
        tw = text_w(fs, B.SPONSOR_NOTE)
        d.text((W / 2 - tw / 2, top + lg_px + 28), B.SPONSOR_NOTE, font=fs, fill=(80, 80, 80))
        pw = 1400 if web else 960
        f = font(F_MED, 46 if web else 48)
        lines = []
        for para in B.DISCLAIMER:
            cur = ""
            for ch in para:
                if text_w(f, cur + ch) > pw - 120 and cur:
                    lines.append(cur); cur = ""
                cur += ch
            lines.append(cur)
            lines.append("")
        lines = lines[:-1]
        lh = f.size * 1.5
        ph = len(lines) * lh + 110
        py0 = top + lg_px + 100
        d.rounded_rectangle([W / 2 - pw / 2, py0, W / 2 + pw / 2, py0 + ph], 36, fill=WHITE, outline=DEEP, width=3)
        y = py0 + 55
        for ln in lines:
            if ln:
                w = text_w(f, ln)
                d.text((W / 2 - w / 2, y), ln, font=f, fill=INK)
            y += lh if ln else lh * 0.45
        if a < 1:
            lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a)))
        cv.paste(lay, (0, 0), lay)

    return Shot3(dur, [Fn(fn)], kind="card", foot=False)


# ───────────────────────── 輸出 ─────────────────────────
def render_shots(shots, L, out, audio=None, crf=18):
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{L.W}x{L.H}", "-r", str(FPS), "-i", "-"]
    if audio:
        cmd += ["-i", audio]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    if audio:
        cmd += ["-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += [out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for s in shots:
        for k in range(int(round(s.dur * FPS))):
            p.stdin.write(s.render(k / FPS, L).tobytes())
    p.stdin.close()
    p.wait()


def cues_of(shots):
    t, out = 0.0, []
    for s in shots:
        for ct, kind in s.cues:
            out.append([round(t + ct, 3), kind])
        t += s.dur
    return {"total": round(t, 3), "cues": out}


def sample_shots(fmt):
    """約 13 秒樣片：三種發光框（方框／圓角框＋角標／虛線）＋置中片尾卡＋置中警語卡。"""
    L = Layout(fmt)
    S = []
    # 1) 熱力圖：完整畫面 → 方框描出半導體區 → 推近
    f1 = FocusBox((386, 180, 1536, 796), t_draw=0.9, d_draw=0.7, t_zoom=1.9, d_zoom=0.9, style="square")
    S.append(Shot3(3.4, [Rec3("S06_desktop", [(0, 0.5), (3.4, 3.9)], focus=f1)], pill_text="熱力圖", head="哪裡熱一眼看", hl="一眼看",
                   sub="方塊越大成交值越大，紅漲綠跌，先看整張再看重點",
                   host=Host([(0, 3.4, "magnifier", None, None, "loop")]), cues=[(0.9, "draw"), (1.9, "zoom")]))
    # 2) 資金分流樹：圓角框＋角標框住右側「流入最多」排名
    f2 = FocusBox((1598, 160, 2122, 836), t_draw=0.9, d_draw=0.7, t_zoom=1.9, d_zoom=0.9, style="round_tag", tag="流入最多")
    S.append(Shot3(3.4, [Rec3("S05_desktop", [(0, 3.0), (3.4, 3.6)], focus=f2)], pill_text="資金流向", head="錢流去哪看排名", hl="排名",
                   sub="哪個族群資金流入最多、流出最多，排名一次看",
                   host=Host([(0, 3.4, "pointer_l", None, None, "loop")]), cues=[(0.9, "draw"), (1.9, "zoom")]))
    # 3) 資金輪動：比比先踩 ▶ 播放（對準錄影點擊座標），再用虛線描邊框住輪盤
    ev = parse_shots(B.RAW / "shots.md").get("S04_desktop", [])
    f3 = FocusBox((410, 250, 1370, 1200), t_draw=1.3, d_draw=0.8, t_zoom=2.3, d_zoom=0.9, style="dashed")
    r3 = Rec3("S04_desktop", [(0, 1.0), (3.4, 4.4)], focus=f3)
    S.append(Shot3(3.4, [r3], pill_text="資金輪動", head="族群輪到哪裡", hl="輪到哪裡",
                   sub="領先、轉弱、落後、改善四個象限，族群位置一眼看",
                   host=Operator(r3, ev, idle="face_think"), cues=[(0.6, "tap"), (1.3, "draw"), (2.3, "zoom")]))
    S.append(end_card(2.6))
    S.append(disclaimer_card(2.4, prev=S[-1]))
    return S, L


def sample_mobile_op():
    """手機版：比比依 raw_v3 shots.md 踩總覽的分頁鈕（驗證 Operator 對位）。"""
    L = Layout("mobile")
    ev = parse_shots(B.RAW / "shots.md").get("S03_mobile", [])
    r = Rec3("S03_mobile", [(0, 1.0), (6.5, 7.5)])
    return [Shot3(6.5, [r], pill_text="財經日曆", head="FED 消息一張排好", hl="一張", sub="點一下事件，數據說明和下次公布日都在這",
                  host=Operator(r, ev, idle="talk_happy"))], L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", default="")
    ap.add_argument("--fmt", choices=["web", "mobile", "mobile_op"], default="web")
    ap.add_argument("--audio", default="")
    ap.add_argument("--cues", default="")
    ap.add_argument("--stills", default="")
    ap.add_argument("--still-dir", default=".")
    a = ap.parse_args()
    S, L = sample_mobile_op() if a.fmt == "mobile_op" else sample_shots(a.fmt)
    if a.cues:
        Path(a.cues).write_text(json.dumps(cues_of(S)))
        return
    if a.stills:
        tl, t = [], 0
        for s in S:
            tl.append((t, s)); t += s.dur
        for T in [float(x) for x in a.stills.split(",")]:
            for t0, s in tl:
                if t0 <= T < t0 + s.dur:
                    p = Path(a.still_dir) / f"v3_{a.fmt}_{T:05.2f}.png"
                    for k in range(0, int((T - t0) * FPS), 5):
                        s.render(k / FPS, L)
                    s.render(T - t0, L).save(p); print(p)
                    break
        return
    render_shots(S, L, a.sample, a.audio or None)
    print("輸出", a.sample)


if __name__ == "__main__":
    main()
