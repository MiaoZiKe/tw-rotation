"""第 3 版合成核心：版面、錄影層（遮蓋＋推近）、發光框焦點、比比操作員、鏡頭、片尾卡與警語卡。

沿用 render_1010.py（素材讀取、比比精靈圖）與 render_v3.py（文字浮層、發光框畫法）；
這支新增：手機版小卡→推近大卡、乾淨遮蓋（不是馬賽克）、網站自己的客服比比淡化、
比比操作員（跳過去踩、悬停、打字、拖曳推 3D、魔法棒畫框）、鏡頭之間的淡入。
"""
from __future__ import annotations

import math
import re
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_1010 as B  # noqa: E402
import render_v3 as R  # noqa: E402
from render_1010 import (CREAM, DEEP, INK, LEMON, SKY, WHITE, F_BOLD, F_MED, FPS, anim_frame, back_out, clamp,  # noqa: E402
                         ease_io, ease_out, font, lerp, logo_sized, piecewise, put_sprite, reader, rounded_mask,
                         text_w, wrap_lines)

THEME = R.THEME
RAW3 = B.SCR / "video1010" / "raw_v3"
FADE_IN = 0.22
FOOT_DATE = "2026-10-08"


# ───────────────────────── 版面 ─────────────────────────
class Lay:
    def __init__(self, fmt):
        self.fmt = fmt
        self.full_bleed = fmt == "web"
        if fmt == "web":
            self.W, self.H = 1920, 1080
            self.box = (0, 0, 1920, 1080)
            self.head_px, self.head_w = 44, 760
            self.host_size = 230
            self.sub_px, self.sub_chars = 32, 44
            self.foot_y = 1050
            self.set_side("L")
        else:
            self.W, self.H = 1080, 1920
            self.box = (40, 420, 960, 960)               # 推近後的大卡（x, y, w, h）
            self.small = (50, 420, 503, 1090)            # 第一拍：手機畫面完整
            self.head_px, self.head_w = 56, 1000
            self.pill_xy, self.pill_right = (40, 214), False
            self.head_xy = (40, 284)
            self.host_size = 320
            self.sub_px, self.sub_chars = 44, 14
            self.foot_y = 1515
            self.side = "L"
            self.sub_xy, self.sub_align = (0, 0), "L"

    def set_side(self, side, top=True):
        """CEO 10-11：浮層一律放網站空白／次要區（頁首中間空白條、底部細條），比比站右下角空白處；不再依焦點換邊。"""
        self.side = "L"
        self.pill_xy, self.pill_right = (590, 9), False
        self.head_xy = (0, 9)
        self.sub_xy, self.sub_align = (60, 992), "L"
        self.host_xy = (1850, 1068)

    @property
    def host(self):
        return self.host_xy if self.fmt == "web" else (770, 1290)


# ───────────────────────── 錄影層 ─────────────────────────
def fit_aspect(win, ar, sw, sh, min_w=0.0):
    x0, y0, x1, y1 = win
    w, h = x1 - x0, y1 - y0
    if w / h < ar:
        w = h * ar
    else:
        h = w / ar
    w = max(w, min_w)
    h = w / ar
    if w > sw:
        w, h = sw, sw / ar
    if h > sh:
        h, w = sh, sh * ar
    cx = clamp((x0 + x1) / 2, w / 2, sw - w / 2)
    cy = clamp((y0 + y1) / 2, h / 2, sh - h / 2)
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def hide_mascot(img):
    """網站右下角自己的客服比比：柔和遮罩淡化（避免跟主持比比同框兩隻）。"""
    if img.width < img.height:
        cx, cy, r = 1012, img.height - 114, 125
    else:
        cx, cy, r = 3090, 1688, 110
    ring = np.array(img.crop((cx - r, cy - r - 24, cx + r, cy - r)))
    col = tuple(int(v) for v in np.median(ring.reshape(-1, 3), axis=0))
    img.paste(Image.new("RGB", (2 * r, 2 * r), col), (cx - r, cy - r), B._soft_disc(r))


def scrub_rect(img, box, sample):
    """乾淨遮蓋：用旁邊底色的實心色塊（不是馬賽克）。"""
    x0, y0, x1, y1 = [int(v) for v in box]
    col = img.getpixel((int(sample[0]), int(sample[1])))
    img.paste(Image.new("RGB", (x1 - x0, y1 - y0), col), (x0, y0))


class Rec4:
    """錄影層。win0＝起始視窗；focus＝發光框焦點；mode='card'（手機：小卡→推近放大）或 'big'。"""

    def __init__(self, clip, srcmap, focus=None, win0=None, mode="card", mascot=True, scrub=()):
        self.clip, self.srcmap, self.focus, self.win0 = clip, srcmap, focus, win0
        self.mode, self.mascot, self.scrub = mode, mascot, list(scrub)
        self.win = self.rect = None

    def zoom_u(self, t):
        return self.focus.zoom_u(t) if self.focus else 0.0

    def draw(self, cv, t, shot):
        L = shot.L
        st = piecewise(self.srcmap, t)
        src = reader(self.clip).get(st)
        copied = False
        for sc in self.scrub:
            if sc[4] <= st <= sc[5]:
                if not copied:
                    src = src.copy(); copied = True
                scrub_rect(src, sc[:4], sc[6])
        if self.mascot:
            if not copied:
                src = src.copy()
            hide_mascot(src)
        sw, sh = src.size
        u = self.zoom_u(t)
        if L.fmt == "mobile" and self.mode == "card":
            k = min(L.small[2] / sw, L.small[3] / sh)
            small = (L.small[0], L.small[1], sw * k, sh * k)
            rect = tuple(lerp(a, b, u) for a, b in zip(small, L.box))
            w_full = (0, 0, sw, sh)
        else:
            rect = L.box
            w_full = self.win0 or (0, 0, sw, sh)
            if L.fmt == "mobile":
                w_full = fit_aspect(w_full, L.box[2] / L.box[3], sw, sh)
        rx, ry, rw, rh = rect
        if self.focus and u > 0:
            x0, y0, x1, y1 = self.focus.rect
            mx, my = (x1 - x0) * 0.06, (y1 - y0) * 0.06
            tgt = fit_aspect((x0 - mx, y0 - my, x1 + mx, y1 + my), L.box[2] / L.box[3], sw, sh, L.box[2] * self.focus.max_up_inv)
        else:
            tgt = w_full
        cx = lerp((w_full[0] + w_full[2]) / 2, (tgt[0] + tgt[2]) / 2, u)
        cy = lerp((w_full[1] + w_full[3]) / 2, (tgt[1] + tgt[3]) / 2, u)
        ww = lerp(w_full[2] - w_full[0], tgt[2] - tgt[0], u)
        wh = ww * rh / rw
        if wh > sh:
            wh, ww = sh, sh * rw / rh
        cx = clamp(cx, ww / 2, sw - ww / 2)
        cy = clamp(cy, wh / 2, sh - wh / 2)
        self.win = (cx - ww / 2, cy - wh / 2, cx + ww / 2, cy + wh / 2)
        self.rect = (rx, ry, rw, rh)
        ix, iy, iw, ih = [int(round(v)) for v in self.rect]
        im = src.resize((iw, ih), Image.LANCZOS, box=self.win)
        tile = im.convert("RGBA")
        if not (L.full_bleed and (iw, ih) == (L.W, L.H)):
            tile.putalpha(rounded_mask(iw, ih, 28))
            ImageDraw.Draw(tile).rounded_rectangle([1, 1, iw - 2, ih - 2], 28, outline=(DEEP if THEME["name"] == "cute" else R.NAVY) + (255,),
                                                   width=3 if THEME["name"] == "cute" else 2)
        cv.paste(tile, (ix, iy), tile)
        if self.focus:
            self.focus.draw(cv, t, self)

    def map(self, sx, sy):
        x0, y0, x1, y1 = self.win
        rx, ry, rw, rh = self.rect
        return rx + (sx - x0) / (x1 - x0) * rw, ry + (sy - y0) / (y1 - y0) * rh


class Focus4(R.FocusBox):
    """發光框焦點：完整畫面 → 比比魔法棒畫框 → 推近。frame=False 只推近不畫框；zoom=False 只畫框不推近。"""

    def __init__(self, rect, t_draw=1.2, d_draw=0.5, t_zoom=None, d_zoom=0.8, style="square", tag=None, max_up=1.0,
                 frame=True, zoom=True, dim=0.14):
        t_zoom = t_draw + d_draw + 0.2 if t_zoom is None else t_zoom
        super().__init__(rect, t_draw, d_draw, t_zoom, d_zoom, style, tag, max_up, dim)
        self.frame, self.zoom = frame, zoom

    def zoom_u(self, t):
        return super().zoom_u(t) if self.zoom else 0.0

    def draw(self, cv, t, rec):
        if self.frame:
            super().draw(cv, t, rec)


# ───────────────────────── shots.md 解析 ─────────────────────────
@lru_cache(maxsize=1)
def parse_events():
    """{clip: [{t, kind(tap|hover|drag_start|drag_end), x, y}]}（影片像素）。"""
    md = (RAW3 / "shots.md").read_text()
    out = {}
    for blk in md.split("\n## ")[1:]:
        lines = blk.split("\n")
        name = lines[0].strip()
        ev = []
        for ln in lines[1:]:
            m = re.search(r"([\d.]+)s (踩下|拖曳開始|拖曳放開|游標移到) \((-?[\d.]+),(-?[\d.]+)\)css → 影片\((-?\d+),(-?\d+)\)px", ln)
            if m:
                kind = {"踩下": "tap", "拖曳開始": "drag_start", "拖曳放開": "drag_end", "游標移到": "hover"}[m.group(2)]
                ev.append({"t": float(m.group(1)), "kind": kind, "x": int(m.group(5)), "y": int(m.group(6))})
        out[name] = ev
    return out


def events_for(clip):
    ev = parse_events()
    return ev.get(clip, [])


def inv_srcmap(srcmap, st, tol=1e-6):
    best = None
    for (t0, s0), (t1, s1) in zip(srcmap, srcmap[1:]):
        if s1 - s0 > tol and (t1 - t0) > 1e-3 and s0 - tol <= st <= s1 + tol:
            best = t0 + (st - s0) / (s1 - s0) * (t1 - t0)
            break
    return best


def ripple(cv, xy, age, small=False):
    if age < 0 or age > 0.55:
        return
    u = ease_out(age / 0.55)
    r = (26 if small else 46) + (34 if small else 70) * u
    a = int(220 * (1 - u))
    col = SKY if THEME["name"] == "cute" else (66, 140, 255)
    lay = Image.new("RGBA", (int(r * 2 + 12), int(r * 2 + 12)), (0, 0, 0, 0))
    c = r + 6
    ImageDraw.Draw(lay).ellipse([c - r, c - r, c + r, c + r], outline=col + (a,), width=4 if small else 6, fill=col + (a // 5,))
    cv.paste(lay, (int(xy[0] - c), int(xy[1] - c)), lay)


# ───────────────────────── 比比操作員 ─────────────────────────
@lru_cache(maxsize=256)
def magic_sprite(i, size):
    info = B.bibi_index()["magic_frame"]
    im = Image.open(info["frames"][i]).convert("RGBA")
    a = np.array(im)
    a[:222, :, 3] = 0                        # 去掉內建的方框與星點，框由我們畫在錄影上
    im = Image.fromarray(a)
    return im.resize((size, size), Image.LANCZOS)


def put_magic(cv, i, foot, size):
    size = int(round(size / 4) * 4)
    sp = magic_sprite(i, size)
    s = size / 512
    cv.paste(sp, (int(round(foot[0] - 248 * s)), int(round(foot[1] - 482 * s))), sp)


def sparkle_trail(cv, p0, p1, u):
    """魔法棒星光從手飛到框的左上角。"""
    if u <= 0 or u >= 1.1:
        return
    d = ImageDraw.Draw(cv)
    col = THEME["glow"]
    for k in range(7):
        v = clamp(u - k * 0.07, 0, 1)
        if v <= 0:
            continue
        x, y = lerp(p0[0], p1[0], ease_io(v)), lerp(p0[1], p1[1], ease_io(v)) - 40 * math.sin(math.pi * v)
        r = max(2, 9 - k)
        d.polygon([(x, y - r * 1.8), (x + r * 0.6, y - r * 0.6), (x + r * 1.8, y), (x + r * 0.6, y + r * 0.6), (x, y + r * 1.8),
                   (x - r * 0.6, y + r * 0.6), (x - r * 1.8, y), (x - r * 0.6, y - r * 0.6)], fill=col + (255,))


class Op:
    """比比操作員。events＝shots.md 事件（影片像素）；taps／drags 依 srcmap 換成本鏡秒數。

    idle：[(t0, 動畫名)]；extra：[(t0, t1, 動畫名, 腳底(None=主持位), 大小(None=預設), 模式)]；
    types：[(t0, t1, (sx, sy))] 打字區間（站在旁邊跳、輸入框每 0.3 秒一個小漣漪）。
    """

    TAP_CONTACT = 0.62
    LEAD = 0.62

    def __init__(self, rec, idle="talk_happy", extra=(), types=(), events=None, use_events=True, magic=True, soft_hover=False,
                 tap_scale=0.8):
        self.rec, self.extra, self.types, self.magic = rec, list(extra), list(types), magic
        self.idle = [(0, idle)] if isinstance(idle, str) else list(idle)
        self.tap_scale = tap_scale
        self.taps, self.drags = [], []
        self.soft_hover = soft_hover
        evs = sorted(events if events is not None else (events_for(rec.clip) if use_events else []), key=lambda e: e["t"])
        end_src = max(sm[1] for sm in rec.srcmap)
        last_xy, last_t = None, -9
        for e in evs:
            if e["kind"] == "hover" and not soft_hover:
                continue
            lt = inv_srcmap(rec.srcmap, e["t"])
            if e["kind"] == "drag_end" and lt is None and e["t"] > end_src:
                lt = rec.srcmap[-1][0]
            if lt is None:
                continue
            if e["kind"] in ("tap", "hover"):
                if lt < self.LEAD - 0.05:
                    continue
                near = last_xy and abs(e["x"] - last_xy[0]) < 70 and abs(e["y"] - last_xy[1]) < 70 and lt - last_t < 3.5
                if near:
                    if self.taps and self.taps[-1]["hover"] and e["kind"] == "tap" and lt - last_t < 1.6:
                        self.taps[-1].update({"t": lt, "hover": False})
                        last_t = lt
                    continue
                dense = (lt - last_t) < 0.8
                self.taps.append({"t": lt, "x": e["x"], "y": e["y"], "dense": dense, "hover": e["kind"] == "hover"})
                last_xy, last_t = (e["x"], e["y"]), lt
            elif e["kind"] == "drag_start":
                self.drags.append({"s0": e["t"], "t0": lt, "x0": e["x"], "y0": e["y"]})
            elif e["kind"] == "drag_end" and self.drags and "t1" not in self.drags[-1]:
                self.drags[-1].update({"s1": e["t"], "t1": lt, "x1": e["x"], "y1": e["y"]})
        self.drags = [d for d in self.drags if "t1" in d and d["t1"] > d["t0"]]

    # 主持位（網頁：焦點對角；手機：右欄，推近後縮到卡片左下）
    def home(self, shot, t):
        L = shot.L
        hs = L.host_size * THEME["host_scale"]
        if L.fmt == "web":
            return L.host, hs
        u = self.rec.zoom_u(t)
        bx, by, bw, bh = L.box
        h1 = (bx + 120, by + bh - 6)
        return (lerp(L.host[0], h1[0], u), lerp(L.host[1], h1[1], u)), lerp(hs, hs * 0.72, u)

    def idle_name(self, t):
        name = self.idle[0][1]
        for t0, n in self.idle:
            if t >= t0:
                name = n
        return name

    def draw(self, cv, t, shot):
        L = shot.L
        home, hs = self.home(shot, t)
        ts = int(hs * self.tap_scale)
        rec = self.rec
        # 漣漪
        for tp in self.taps:
            if rec.win and not tp["hover"]:
                ripple(cv, rec.map(tp["x"], tp["y"]), t - tp["t"], tp["dense"])
        for t0, t1, sx_sy in self.types:
            if t0 <= t < t1 and rec.win:
                k = int((t - t0) / 0.3)
                ripple(cv, rec.map(*sx_sy), (t - t0) - k * 0.3, True)
        for t0, t1, name, foot, size, mode in self.extra:
            if t0 <= t < t1:
                f = foot(rec) if callable(foot) else foot
                put_sprite(cv, name, anim_frame(name, t - t0, mode), f or home, size or hs)
                return
        for t0, t1, sxy in self.types:
            if t0 - 0.3 <= t < t1 + 0.2 and rec.win:
                a = rec.map(*sxy)
                f = (a[0] + hs * 0.9, a[1] + hs * 0.55)
                u = ease_io((t - (t0 - 0.3)) / 0.3)
                f = (lerp(home[0], f[0], u), lerp(home[1], f[1], u) - 80 * math.sin(math.pi * u) * (u < 1))
                name = "hop_l"
                put_sprite(cv, name, anim_frame(name, t), f, int(hs * 0.7))
                return
        # 拖曳：比比站在游標後方、往拖曳方向推
        for d in self.drags:
            if d["t0"] - 0.1 <= t <= d["t1"] + 0.1:
                dx = 1 if d["x1"] >= d["x0"] else -1
                name = "hop_r" if dx > 0 else "hop_l"
                put_sprite(cv, name, anim_frame(name, t - d["t0"]), home, hs)
                return
            if False and d["t0"] - 0.4 <= t <= d["t1"] + 0.25 and rec.win:
                st_now = piecewise(rec.srcmap, t)
                u = clamp((st_now - d["s0"]) / max(0.01, d["s1"] - d["s0"]), 0, 1)
                sx, sy = lerp(d["x0"], d["x1"], ease_io(u)), lerp(d["y0"], d["y1"], ease_io(u))
                px, py = rec.map(sx, sy)
                dx = 1 if d["x1"] >= d["x0"] else -1
                tgt = (px - dx * ts * 0.35, py + ts * 0.3)
                ent = clamp((t - d["t0"] + 0.4) / 0.4, 0, 1)
                if t > d["t1"]:
                    ent = 1 - clamp((t - d["t1"]) / 0.25, 0, 1)
                f = (lerp(home[0], tgt[0], ease_io(ent)), lerp(home[1], tgt[1], ease_io(ent)) - 110 * THEME["bounce"] * math.sin(math.pi * ent) * (ent < 1))
                name = "hop_r" if dx > 0 else "hop_l"
                put_sprite(cv, name, anim_frame(name, t), f, int(lerp(hs, ts, ease_io(ent))))
                return
        # 踩按鈕
        taps = [tp for tp in self.taps if not tp["dense"]]
        for i, tp in enumerate(taps):
            c = tp["t"]
            nxt = taps[i + 1]["t"] if i + 1 < len(taps) else 1e9
            if i > 0 and c - taps[i - 1]["t"] < 2.2:
                prev = (rec.map(taps[i - 1]["x"], taps[i - 1]["y"]), ts)
            else:
                prev = (home, hs)
            tgt = rec.map(tp["x"], tp["y"])
            tgt = (clamp(tgt[0], 40, L.W - 40), clamp(tgt[1], 60, L.H - 20))
            if c - self.LEAD <= t < c:
                tt = t - (c - self.LEAD)
                air0 = 0.29
                if tt < air0:
                    foot, size = prev
                else:
                    u = ease_io((tt - air0) / (self.TAP_CONTACT - air0))
                    foot = (lerp(prev[0][0], tgt[0], u), lerp(prev[0][1], tgt[1], u) - 150 * THEME["bounce"] * math.sin(math.pi * u))
                    size = lerp(prev[1], ts, u)
                put_sprite(cv, "tap", anim_frame("tap", tt, "hold"), foot, size)
                return
            stay = min(nxt - self.LEAD, c + 0.9) if nxt - c < 2.2 else c + 0.45
            if c <= t < stay:
                put_sprite(cv, "tap", anim_frame("tap", self.TAP_CONTACT + (t - c), "hold"), tgt, ts)
                return
            if nxt - c >= 2.2 and stay <= t < stay + 0.4:
                u = ease_io((t - stay) / 0.4)
                foot = (lerp(tgt[0], home[0], u), lerp(tgt[1], home[1], u) - 130 * THEME["bounce"] * math.sin(math.pi * u))
                put_sprite(cv, "hop_l" if home[0] < tgt[0] else "hop_r", 2 + int(u * 3.99), foot, lerp(ts, hs, u))
                return
        # 魔法棒畫框
        f = getattr(rec, "focus", None)
        if f and f.frame and self.magic and f.t_draw - 0.35 <= t < f.t_draw + f.d_draw + 0.15 and rec.win:
            i = int(clamp((t - (f.t_draw - 0.35)) / 0.95 * 12, 0, 11))
            put_magic(cv, i, home, hs)
            x0, y0 = rec.map(f.rect[0], f.rect[1])
            s = hs / 512
            hand = (home[0] + (372 - 248) * s, home[1] + (318 - 482) * s)
            sparkle_trail(cv, hand, (clamp(x0, 20, L.W - 20), clamp(y0, 20, L.H - 20)), (t - (f.t_draw - 0.25)) / 0.3)
            return
        name = self.idle_name(t)
        put_sprite(cv, name, anim_frame(name, t), home, hs)


# ───────────────────────── 鏡頭 ─────────────────────────
class Shot4:
    def __init__(self, sid, dur, layers=(), pill=None, head="", hl=None, sub="", op=None, cues=(), kind="feature", foot=True,
                 side=None, custom=None, bubble_cn=None):
        self.sid, self.dur = sid, dur
        self.layers = list(layers)
        self.pill, self.head, self.hl, self.sub = pill, head, hl, sub
        self.op, self.cues, self.kind, self.foot, self.side, self.custom = op, list(cues), kind, foot, side, custom
        self.L = None
        self.prev = None
        self._pl = None

    @property
    def rec(self):
        for ly in self.layers:
            if isinstance(ly, Rec4):
                return ly
        return None

    def auto_cues(self):
        c = list(self.cues)
        r = self.rec
        if self.op:
            for tp in self.op.taps:
                if not tp["hover"] and not tp["dense"]:
                    c.append((tp["t"], "tap"))
            for d in self.op.drags[:1]:
                c.append((max(0, d["t0"] - 0.2), "swish"))
        if r and r.focus:
            if r.focus.frame:
                c.append((r.focus.t_draw, "draw"))
            if r.focus.zoom:
                c.append((r.focus.t_zoom, "zoom"))
        return sorted(c)

    def render(self, t, L, _fade=True):
        self.L = L
        if L.full_bleed:
            side, top = self.side, True
            r = self.rec
            if r and r.focus:
                fx = (r.focus.rect[0] + r.focus.rect[2]) / 2 / 3200
                fy = (r.focus.rect[1] + r.focus.rect[3]) / 2 / 1800
                top = fy > 0.40
                if side is None:
                    side = "R" if fx < 0.5 else "L"
            L.set_side(side or "L", top)
        cv = R.background(L.fmt).copy()
        for ly in self.layers:
            ly.draw(cv, t, self)
        if self.custom:
            self.custom(cv, t, self)
        if self.kind == "feature":
            if self.pill:
                pw = R.pill(cv, self.pill, *L.pill_xy, right=getattr(L, "pill_right", False))
                if L.full_bleed:
                    L.head_xy = (L.pill_xy[0] + pw + 22, 9)
            elif L.full_bleed:
                L.head_xy = (590, 9)
            R.headline(cv, L, self.head, t, self.hl)
            if L.fmt == "web":
                R.subtitle(cv, L, self.sub, t)
            if self.foot:
                footnote4(cv, L)
        if self.op:
            self.op.draw(cv, t, self)
        if self.kind == "feature" and L.fmt == "mobile":
            bubble_mobile(cv, L, self, self.sub, t)
        if _fade and self.prev is not None and t < FADE_IN:
            if self._pl is None:
                self._pl = self.prev.render(self.prev.dur - 1 / FPS, L, _fade=False).copy()
            cv = Image.blend(self._pl, cv, ease_io(t / FADE_IN))
        return cv


def footnote4(cv, L):
    f = font(F_MED, 22 if L.fmt == "web" else 26)
    FN = R.FOOTNOTE
    d = ImageDraw.Draw(cv)
    if L.fmt == "web":
        text = f"網站實際畫面・資料日 {FOOT_DATE}｜{FN}"
        tw = text_w(f, text)
        x = L.W / 2 - tw / 2
        R.float_panel(cv, (x - 14, L.foot_y - 4, x + tw + 14, L.foot_y + 28), 150, 12)
        d.text((x, L.foot_y), text, font=f, fill=(80, 80, 80))
    else:
        for i, text in enumerate([f"網站實際畫面・資料日 {FOOT_DATE}", FN]):
            tw = text_w(f, text)
            d.text((L.W / 2 - tw / 2, L.foot_y + i * 34), text, font=f, fill=(90, 90, 90))


def bubble_mobile(cv, L, shot, text, t):
    """手機版比比台詞泡泡：推近前在右欄、推近後在卡片下方。"""
    if not text:
        return
    r = shot.rec
    u = r.zoom_u(t) if r else 1.0
    a = clamp(t / 0.25, 0, 1)
    px = 40
    f = font(B.F_ROUND, px)
    if u < 0.5:
        box = (590, 600, 1040, 900)
        lines = wrap_lines(text, 9)[:3]
        hp, hs = shot.op.home(shot, t) if shot.op else (L.host, 300)
        _bubble_col(cv, lines, box, (hp[0] + 10, hp[1] - hs * 0.52), a * (1 - u * 2), f)
    else:
        bx, by, bw, bh = L.box
        box = (40, by + bh + 14, 1040, by + bh + 14 + 104)
        lines = wrap_lines(text, 22)[:2]
        hp, hs = shot.op.home(shot, t) if shot.op else (L.host, 300)
        _bubble_band(cv, lines, box, (hp[0] + 40, by + bh - 6), a * (u * 2 - 1), f)


def _bubble_col(cv, lines, box, tail, a, f):
    if a <= 0.02:
        return
    x0, y0, x1, y1 = box
    h = len(lines) * 62 + 44
    y1 = tail[1] - 46
    y0 = y1 - h
    lay = Image.new("RGBA", cv.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    cx = clamp(tail[0], x0 + 40, x1 - 40)
    d.polygon([(cx - 24, y1 - 3), (cx + 24, y1 - 3), tail], fill=WHITE + (255,), outline=R.THEME["ink"] + (255,))
    d.rounded_rectangle([x0, y0, x1, y1], R.THEME["panel_r"] + 8, fill=WHITE + (255,), outline=R.THEME["ink"] + (255,), width=4)
    d.polygon([(cx - 21, y1 - 2), (cx + 21, y1 - 2), (lerp(cx, tail[0], 0.85), lerp(y1, tail[1], 0.85))], fill=WHITE + (255,))
    for i, ln in enumerate(lines):
        tw = text_w(f, ln)
        d.text(((x0 + x1) / 2 - tw / 2, y0 + 20 + i * 62), ln, font=f, fill=R.THEME["ink"])
    lay.putalpha(lay.getchannel("A").point(lambda v: int(v * clamp(a, 0, 1))))
    cv.paste(lay, (0, 0), lay)


def _bubble_band(cv, lines, box, tail, a, f):
    if a <= 0.02:
        return
    x0, y0, x1, y1 = box
    lay = Image.new("RGBA", cv.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.polygon([(tail[0] - 24, y0 + 3), (tail[0] + 24, y0 + 3), (tail[0] - 6, y0 - 22)], fill=WHITE + (255,), outline=R.THEME["ink"] + (255,))
    d.rounded_rectangle([x0, y0, x1, y1], R.THEME["panel_r"] + 8, fill=WHITE + (255,), outline=R.THEME["ink"] + (255,), width=4)
    d.polygon([(tail[0] - 21, y0 + 2), (tail[0] + 21, y0 + 2), (tail[0] - 6, y0 - 18)], fill=WHITE + (255,))
    for i, ln in enumerate(lines):
        tw = text_w(f, ln)
        yy = y0 + (y1 - y0) / 2 - (len(lines) * 56) / 2 + i * 56 - 4
        d.text(((x0 + x1) / 2 - tw / 2, yy), ln, font=f, fill=R.THEME["ink"])
    lay.putalpha(lay.getchannel("A").point(lambda v: int(v * clamp(a, 0, 1))))
    cv.paste(lay, (0, 0), lay)


class Fn:
    def __init__(self, fn):
        self.fn = fn

    def draw(self, cv, t, shot):
        self.fn(cv, t, shot)
