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

FOOTNOTE = "畫面數據為過往歷史資料，僅供功能展示，不具投資參考價值"
GLOW = (255, 196, 40)


# ───────────────────────── 版面 ─────────────────────────
class Layout:
    def __init__(self, fmt):
        self.fmt = fmt
        if fmt == "web":
            self.W, self.H = 1920, 1080
            self.box = (24, 24, 1480, 925)          # 展示框（桌機 16:10 → 1480×925，不放大 2160 寬素材）
            self.side_x = 1528                      # 右側窄欄：段落膠囊、大字、比比
            self.pill_xy = (1528, 40)
            self.head_xy = (1528, 112)
            self.head_w = 368
            self.head_px = 64
            self.host = (1712, 860)                 # 比比腳底
            self.host_size = 330
            self.sub_xy = (40, 966)                 # 字幕：展示框下方一行
            self.sub_px = 42
            self.sub_chars = 30
            self.foot_y = 1040
            self.data_xy = (24 + 1480 - 16, 24 + 925 - 14)
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
    d.polygon([(x - 26, 18), (x - 2, 4), (x - 8, 36)], fill=INK + (255,))
    for i, ln in enumerate(lines[:2]):
        d.text((x, i * L.sub_px * 1.32), ln, font=f, fill=INK, stroke_width=5, stroke_fill=CREAM)
    if a < 1:
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a)))
    cv.paste(lay, (0, y), lay)


def footnote(cv, L):
    f = font(F_MED, 24 if L.fmt == "web" else 26)
    tw = text_w(f, FOOTNOTE)
    d = ImageDraw.Draw(cv)
    if L.fmt == "web":
        x = L.W / 2 - tw / 2
    else:
        x = L.W / 2 - tw / 2
    d.text((x, L.foot_y), FOOTNOTE, font=f, fill=(96, 96, 96))


def data_tag(cv, L, date):
    f = font(F_MED, 24)
    s = f"網站實際畫面・資料日 {date}"
    tw = text_w(f, s)
    x1, y1 = L.data_xy
    x0, y0 = x1 - tw - 28, y1 - 40
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
        cv = background(L.fmt).copy()
        for ly in self.layers:
            ly.draw(cv, t, self)
        if self.kind == "feature":
            if self.date:
                data_tag(cv, L, self.date)
            if self.pill_text:
                pill(cv, self.pill_text, *L.pill_xy)
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
    # 3) 資金輪動：虛線描邊框住輪盤
    f3 = FocusBox((410, 250, 1370, 1200), t_draw=0.9, d_draw=0.8, t_zoom=1.9, d_zoom=0.9, style="dashed")
    S.append(Shot3(3.4, [Rec3("S04_desktop", [(0, 2.0), (3.4, 5.4)], focus=f3)], pill_text="資金輪動", head="族群輪到哪裡", hl="輪到哪裡",
                   sub="領先、轉弱、落後、改善四個象限，族群位置一眼看",
                   host=Host([(0, 3.4, "face_think", None, None, "loop")]), cues=[(0.9, "draw"), (1.9, "zoom")]))
    S.append(end_card(2.6))
    S.append(disclaimer_card(2.4, prev=S[-1]))
    return S, L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", default="")
    ap.add_argument("--fmt", choices=["web", "mobile"], default="web")
    ap.add_argument("--audio", default="")
    ap.add_argument("--cues", default="")
    ap.add_argument("--stills", default="")
    ap.add_argument("--still-dir", default=".")
    a = ap.parse_args()
    S, L = sample_shots(a.fmt)
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
                    s.render(T - t0, L).save(p); print(p)
                    break
        return
    render_shots(S, L, a.sample, a.audio or None)
    print("輸出", a.sample)


if __name__ == "__main__":
    main()
