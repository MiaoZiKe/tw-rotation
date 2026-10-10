"""哩股哩股功能宣傳影片（2026-10-10，比比全片主持版）逐格合成。

做法（沿用 1009 那支「逐格算圖＋ffmpeg、不掉格」的精神，改成純 Python）：
- 素材：網站真實錄影（scratchpad/video1010/raw/*.mp4，30fps，資料日 2026-10-08）＋比比 12 格透明 PNG 序列（scratchpad/bibi/*）
  ＋LOGO（site/brand/src/logo_1009.jpg）＋字型（jf open 粉圓、Noto Sans TC，皆 SIL OFL）。
- 每一鏡是一個 Shot：錄影卡（在「來源座標」先做模糊，再裁切縮放 → 模糊會自動跟著推近／平移）＋大字＋字幕＋角標＋比比動作。
- 比比「踩」：腳落下那一格（tap 第 9 格）對準錄影裡的點擊時間；位置用當格的裁切換算，所以鏡頭在動時腳也黏在按鈕上。
- 每鏡各自算圖成一段無損近似的 mp4（4 個行程平行），最後串接＋配樂。

用法：
  python docs/marketing/video_1010/render_1010.py --cut main  --out <mp4>      # 主版
  python docs/marketing/video_1010/render_1010.py --cut short --out <mp4>      # 15 秒短版（＋警語）
  python docs/marketing/video_1010/render_1010.py --cut main --stills 12.3,40.1 --still-dir <dir>   # 只抽格
  python docs/marketing/video_1010/render_1010.py --cover <png>                                     # 封面
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SCR = Path(os.environ.get("V1010_SCRATCH", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad"))
RAW = SCR / "video1010" / "raw"
BIBI = SCR / "bibi"
FONT_DIR = SCR / "font"
F_ROUND = os.environ.get("BIBI_SIGN_FONT") or str(FONT_DIR / "jf-openhuninn-2.1.ttf")
F_BOLD = str(FONT_DIR / "NotoSansTC-Bold.ttf")
F_MED = str(FONT_DIR / "NotoSansTC-Medium.ttf")
F_BLACK = str(FONT_DIR / "NotoSansTC-Black.ttf")
LOGO = REPO / "site" / "brand" / "src" / "logo_1009.jpg"
LAPTOP = REPO / "docs" / "anim" / "laptop" / "animation.gif"

W, H, FPS = 1080, 1920, 30
DATA_DATE = "2026-10-08"

SKY = (42, 166, 245)
DEEP = (27, 111, 224)
LEMON = (255, 212, 59)
CREAM = (255, 249, 239)
INK = (26, 26, 26)
BLUSH = (246, 165, 160)
WHITE = (255, 255, 255)

CARD = (60, 470, 960, 930)          # x, y, w, h（畫面卡）
HOST = (190, 1418)                  # 比比主持位：腳底（x 中心, 地面 y）
HOST_SIZE = 380                     # 比比精靈圖方框邊長（角色本體約佔一半）
SUB_Y = 1428                        # 字幕第一行頂端

DISCLAIMER = [
    "哩股哩股為公開市場資料之整理與視覺化工具，並非證券投資顧問事業。",
    "影片內容僅供功能說明，不構成任何投資建議或買賣依據；投資有風險，過去表現不代表未來，請自行審慎判斷。",
]
SPONSOR_NOTE = "本影片由哩股哩股自行製作刊登，無第三方付費合作。"


# ───────────────────────── 小工具 ─────────────────────────
def clamp(x, a, b):
    return a if x < a else b if x > b else x


def ease_out(x):
    x = clamp(x, 0.0, 1.0)
    return 1 - (1 - x) ** 3


def ease_io(x):
    x = clamp(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def back_out(x, s=1.7):
    x = clamp(x, 0.0, 1.0) - 1
    return 1 + x * x * ((s + 1) * x + s)


def lerp(a, b, t):
    return a + (b - a) * t


def piecewise(keys, t, ease=None):
    """keys: [(t, v...)]，線性（或 ease）內插。v 可以是 tuple。"""
    if t <= keys[0][0]:
        return keys[0][1:] if len(keys[0]) > 2 else keys[0][1]
    for (t0, *v0), (t1, *v1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            u = (t - t0) / (t1 - t0) if t1 > t0 else 1.0
            if ease:
                u = ease(u)
            r = tuple(lerp(a, b, u) for a, b in zip(v0, v1))
            return r if len(r) > 1 else r[0]
    last = keys[-1]
    return last[1:] if len(last) > 2 else last[1]


@lru_cache(maxsize=64)
def font(path, size):
    return ImageFont.truetype(path, size)


def text_w(f, s):
    return f.getlength(s)


def rounded_mask(w, h, r):
    return _rounded_mask(int(w), int(h), int(r))


@lru_cache(maxsize=64)
def _rounded_mask(w, h, r):
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=255)
    return m


def wrap_lines(s, max_chars=16):
    """字幕斷行：≤16 字一行，最多兩行，優先在標點後斷。"""
    if len(s) <= max_chars:
        return [s]
    best, best_score = None, 1e9
    for i in range(max(1, len(s) - max_chars), min(len(s), max_chars) + 1):
        a, b = s[:i], s[i:]
        if len(a) > max_chars or len(b) > max_chars:
            continue
        score = abs(len(a) - len(b))
        if a[-1] in "，、；：！？）": score -= 6
        if b[:1] in "，、；：！？）。": score += 20
        if b[:1] == "（": score -= 4
        if score < best_score:
            best, best_score = (a, b), score
    if best is None:
        return [s[:max_chars], s[max_chars:]]
    return list(best)


# ───────────────────────── 背景 ─────────────────────────
@lru_cache(maxsize=1)
def background():
    bg = Image.new("RGB", (W, H), CREAM)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    a = int(255 * 0.10)
    for x in range(0, W, 60):
        d.line([(x, 0), (x, H)], fill=SKY + (a,), width=2)
    for y in range(0, H, 60):
        d.line([(0, y), (W, y)], fill=SKY + (a,), width=2)
    bg.paste(ov, (0, 0), ov)
    return bg


@lru_cache(maxsize=1)
def logo_img():
    im = Image.open(LOGO).convert("RGB")
    s = im.size[0]
    m = rounded_mask(s, s, int(s * 0.2))
    out = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    out.paste(im, (0, 0), m)
    # 去掉圓角外殘留白邊：往內縮 1%
    return out


@lru_cache(maxsize=32)
def logo_sized(px):
    return logo_img().resize((px, px), Image.LANCZOS)


# ───────────────────────── 錄影來源 ─────────────────────────
class SourceReader:
    """依序往前讀的 ffmpeg 解碼器（不跳回頭；要回頭就重開）。"""

    def __init__(self, clip):
        self.clip = clip
        self.path = RAW / f"{clip}.mp4"
        info = json.loads(subprocess.check_output([
            "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,nb_frames",
            "-of", "json", str(self.path)]))["streams"][0]
        self.w, self.h = info["width"], info["height"]
        self.nframes = int(info.get("nb_frames") or 0)
        self.proc = None
        self.idx = -1
        self.cur = None
        self.start_idx = 0

    def _open(self, idx):
        if self.proc:
            self.proc.kill()
        self.start_idx = idx
        self.proc = subprocess.Popen([
            "ffmpeg", "-v", "error", "-ss", f"{idx / FPS:.4f}", "-i", str(self.path),
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=10 ** 8)
        self.idx = idx - 1
        self.cur = None

    def get(self, t):
        idx = int(round(t * FPS))
        if self.nframes:
            idx = clamp(idx, 0, self.nframes - 1)
        if self.proc is None or idx < self.idx or idx - self.idx > 90:
            self._open(idx)
        n = self.w * self.h * 3
        while self.idx < idx:
            buf = self.proc.stdout.read(n)
            if len(buf) < n:
                break
            self.cur = buf
            self.idx += 1
        if self.cur is None:
            self._open(max(0, idx - 1))
            return self.get(t)
        return Image.frombuffer("RGB", (self.w, self.h), self.cur, "raw", "RGB", 0, 1)

    def close(self):
        if self.proc:
            self.proc.kill()
            self.proc = None


_READERS: dict = {}


def reader(clip):
    if clip not in _READERS:
        _READERS[clip] = SourceReader(clip)
    return _READERS[clip]


def sresize(src, size, box):
    """裁切縮放；box 超出來源就平移回來，比來源大就縮成來源大小（維持比例由呼叫者負責）。"""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    if w > src.width:
        s = src.width / w; w, h = w * s, h * s
    if h > src.height:
        s = src.height / h; w, h = w * s, h * s
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    x0 = clamp(cx - w / 2, 0, src.width - w); y0 = clamp(cy - h / 2, 0, src.height - h)
    return src.resize(size, Image.BICUBIC, box=(x0, y0, x0 + w, y0 + h))


def frosted(img, box, r=24, white=0.45):
    """毛玻璃膠囊：高斯模糊（來源像素半徑 r）＋白 45%，圓角。"""
    x0, y0, x1, y1 = [int(v) for v in box]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(img.width, x1), min(img.height, y1)
    if x1 - x0 < 4 or y1 - y0 < 4:
        return
    reg = img.crop((x0, y0, x1, y1))
    k = 4
    small = reg.resize((max(1, reg.width // k), max(1, reg.height // k)), Image.BILINEAR)
    small = small.filter(ImageFilter.GaussianBlur(r / k))
    reg2 = small.resize(reg.size, Image.BILINEAR)
    reg2 = Image.blend(reg2, Image.new("RGB", reg.size, (246, 249, 252)), white)
    m = rounded_mask(reg.width, reg.height, min(18, reg.height // 2))
    img.paste(reg2, (x0, y0), m)


# ───────────────────────── 錄影卡（一層） ─────────────────────────
class Rec:
    """一張錄影卡。

    srcmap: [(本鏡秒, 來源秒)] 分段線性
    win:    [(本鏡秒, 中心x, 中心y, 寬)]（來源像素），高度依卡片比例；ease 內插
    blur:   [(x0,y0,x1,y1, 來源秒起, 來源秒迄)]
    """

    def __init__(self, clip, srcmap, win, blur=(), rect=CARD, radius=36, border=True, enter=None, exit=None,
                 blur_r=24, tint=None, fade_in=0.0, blur_white=0.45):
        self.clip, self.srcmap, self.win, self.blur = clip, srcmap, win, list(blur)
        self.rect = rect
        self.radius, self.border = radius, border
        self.enter, self.exit = enter, exit
        self.blur_r = blur_r
        self.blur_white = blur_white
        self.tint = tint
        self.fade_in = fade_in
        self.box = None
        self.out_rect = rect

    def src_t(self, t):
        return piecewise(self.srcmap, t)

    def window(self, t):
        cx, cy, w = piecewise(self.win, t, ease_io)
        rw, rh = self.rect[2], self.rect[3]
        h = w * rh / rw
        return cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2

    def frame_image(self, t):
        st = self.src_t(t)
        src = reader(self.clip).get(st).copy()
        for b in self.blur:
            x0, y0, x1, y1, s0, s1 = (list(b) + [-1e9, 1e9])[:6]
            if s0 <= st <= s1:
                frosted(src, (x0, y0, x1, y1), self.blur_r, self.blur_white)
        x0, y0, x1, y1 = self.window(t)
        # 視窗比來源大 → 等比縮回來源大小
        k = min(1.0, src.width / (x1 - x0), src.height / (y1 - y0))
        if k < 1:
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            hw, hh = (x1 - x0) * k / 2, (y1 - y0) * k / 2
            x0, x1, y0, y1 = cx - hw, cx + hw, cy - hh, cy + hh
        # 視窗超出來源 → 平移回來（保持大小）
        if x0 < 0: x1 -= x0; x0 = 0
        if y0 < 0: y1 -= y0; y0 = 0
        if x1 > src.width: x0 -= x1 - src.width; x1 = src.width
        if y1 > src.height: y0 -= y1 - src.height; y1 = src.height
        self.box = (x0, y0, x1, y1)
        rw, rh = self.rect[2], self.rect[3]
        im = src.resize((rw, rh), Image.BICUBIC, box=(x0, y0, x1, y1))
        if self.tint:
            im = Image.blend(im, Image.new("RGB", im.size, self.tint[0]), self.tint[1])
        return im

    def map(self, sx, sy):
        x0, y0, x1, y1 = self.box
        rx, ry, rw, rh = self.out_rect
        return rx + (sx - x0) / (x1 - x0) * rw, ry + (sy - y0) / (y1 - y0) * rh

    def draw(self, canvas, t, shot):
        im = self.frame_image(t)
        rx, ry, rw, rh = self.rect
        scale, dx, dy, alpha = 1.0, 0.0, 0.0, 1.0
        if self.enter:
            kind, d = self.enter[0], self.enter[1]
            u = ease_out(t / d) if d > 0 else 1
            if kind == "slide_r": dx = (1 - u) * (W - rx + 40)
            elif kind == "slide_l": dx = -(1 - u) * (rx + rw + 40)
            elif kind == "slide_up": dy = (1 - u) * 500; alpha = u
            elif kind == "zoom": scale = lerp(self.enter[2] if len(self.enter) > 2 else 0.82, 1.0, u); alpha = min(1, u * 1.6)
            elif kind == "fade": alpha = u
            elif kind == "wipe_down":
                pass
        if self.exit:
            kind, d = self.exit[0], self.exit[1]
            u = ease_io((t - (shot.dur - d)) / d) if d > 0 else 0
            if u > 0:
                if kind == "zoom_to":
                    # 往點擊處穿越：以 (fx,fy) 為中心放大
                    fx, fy = self.exit[2]
                    scale *= lerp(1.0, 2.2, u)
                    alpha *= 1 - u * 0.9
                    self._zoom_focus = (fx, fy)
                elif kind == "slide_l": dx -= u * (rx + rw + 60)
                elif kind == "slide_r": dx += u * (W - rx + 60)
                elif kind == "fade": alpha *= 1 - u
        tile = im.convert("RGBA")
        mask = rounded_mask(rw, rh, self.radius).copy()
        if self.enter and self.enter[0] == "wipe_down":
            u = ease_out(t / self.enter[1])
            cut = int(rh * u)
            md = ImageDraw.Draw(mask)
            md.rectangle([0, cut, rw, rh], fill=0)
        tile.putalpha(mask)
        if self.border:
            bd = Image.new("RGBA", (rw, rh), (0, 0, 0, 0))
            ImageDraw.Draw(bd).rounded_rectangle([1, 1, rw - 2, rh - 2], self.radius, outline=DEEP + (255,), width=3)
            if self.enter and self.enter[0] == "wipe_down":
                bd.putalpha(Image.fromarray(np.minimum(np.array(bd.getchannel("A")), np.array(mask))))
            tile.alpha_composite(bd)
        if self.fade_in > 0:
            alpha *= clamp(t / self.fade_in, 0, 1)
        ox, oy = rx + dx, ry + dy
        if scale != 1.0:
            nw, nh = int(rw * scale), int(rh * scale)
            tile = tile.resize((nw, nh), Image.BILINEAR)
            if self.exit and self.exit[0] == "zoom_to" and getattr(self, "_zoom_focus", None):
                fx, fy = self._zoom_focus
                ox = fx - (fx - rx) * scale
                oy = fy - (fy - ry) * scale
            else:
                ox = rx + rw / 2 - nw / 2 + dx
                oy = ry + rh / 2 - nh / 2 + dy
            self.out_rect = (ox, oy, nw, nh)
        else:
            self.out_rect = (ox, oy, rw, rh)
        if alpha < 1:
            a = tile.getchannel("A").point(lambda v: int(v * alpha))
            tile.putalpha(a)
        # 卡片陰影（淡）
        if alpha > 0.5 and scale == 1.0:
            sh = _shadow(rw, rh, self.radius)
            canvas.paste(sh, (int(ox) - 20, int(oy) - 8), sh)
        canvas.paste(tile, (int(round(ox)), int(round(oy))), tile)


@lru_cache(maxsize=16)
def _shadow(w, h, r):
    pad = 40
    m = Image.new("L", (w + pad, h + pad), 0)
    ImageDraw.Draw(m).rounded_rectangle([20, 22, w + 20, h + 22], r, fill=60)
    m = m.filter(ImageFilter.GaussianBlur(12))
    im = Image.new("RGBA", m.size, (27, 60, 110, 0))
    im.putalpha(m)
    return im


class Still:
    """靜態圖層（自己畫的卡片、LOGO 等）：fn(canvas, t, shot)。"""

    def __init__(self, fn):
        self.fn = fn
        self.rect = CARD

    def draw(self, canvas, t, shot):
        self.fn(canvas, t, shot)


# ───────────────────────── 比比 ─────────────────────────
@lru_cache(maxsize=1)
def bibi_index():
    idx = {}
    for f in ["index.json", "index_b.json", "index_c.json", "index_d.json"]:
        p = BIBI / f
        if p.exists():
            d = json.loads(p.read_text())
            idx.update(d)
    return idx


@lru_cache(maxsize=4096)
def sprite(name, i, size, flip=False):
    info = bibi_index()[name]
    im = Image.open(info["frames"][i]).convert("RGBA")
    if name == "calc":
        im = blank_calc_screen(im)
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    size = int(size)
    return im.resize((size, size), Image.LANCZOS)


def blank_calc_screen(im):
    a = np.array(im).astype(int)
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    scr = (al > 200) & (g >= r + 7) & (g - b >= 22) & (g > 200)
    ys, xs = np.nonzero(scr[300:, 200:])
    if len(xs) < 50:
        return im
    x0, x1 = xs.min() + 200, xs.max() + 200
    y0, y1 = ys.min() + 300, ys.max() + 300
    col = tuple(int(v) for v in np.median(a[300:, 200:][scr[300:, 200:]][:, :3], axis=0))
    out = im.copy()
    ImageDraw.Draw(out).rectangle([x0 + 3, y0 + 3, x1 - 3, y1 - 3], fill=col + (255,))
    return out


def anim_frame(name, t, mode="loop"):
    durs = bibi_index()[name]["durations_ms"]
    total = sum(durs) / 1000
    if mode == "loop":
        t = t % total
    elif mode in ("once", "hold"):
        if t >= total:
            return len(durs) - 1 if mode == "hold" else 0
    acc = 0
    for i, d in enumerate(durs):
        acc += d / 1000
        if t < acc:
            return i
    return len(durs) - 1


def anim_len(name):
    return sum(bibi_index()[name]["durations_ms"]) / 1000


def put_sprite(canvas, name, i, foot, size, flip=False):
    size = int(round(size / 4) * 4)
    sp = sprite(name, i, size, flip)
    s = size / 512
    x = foot[0] - 248 * s
    y = foot[1] - 482 * s
    canvas.paste(sp, (int(round(x)), int(round(y))), sp)


TIP_OFF = (474.7 - 248, 232.1 - 482)       # 指示棒尖端相對腳底（512 座標）
TAP_CONTACT = 0.62                         # tap 第 9 格（腳碰到按鈕）開始時間
TAP_QUICK_START = 0.41                     # 快速版從第 6 格開始


class Bibi:
    """比比的時間軸。acts：dict(t0,t1,kind,...)；沒有 act 的時間用 default 動畫站主持位。"""

    def __init__(self, acts=(), default="talk_happy", visible=True):
        self.acts = sorted(acts, key=lambda a: a["t0"])
        self.default = default
        self.visible = visible
        self.last = (HOST, HOST_SIZE)
        self.act_start = {}

    def resolve_target(self, tgt, shot):
        if tgt is None:
            return HOST
        if len(tgt) == 3:          # ("src", 層 index, (sx, sy))
            _, li, (sx, sy) = tgt
            return shot.layers[li].map(sx, sy)
        return tgt

    def draw(self, canvas, t, shot):
        if not self.visible:
            return
        act = None
        for a in self.acts:
            if a["t0"] <= t < a["t1"]:
                act = a
        if act is None:
            name = self.default
            foot, size = HOST, HOST_SIZE
            if shot.bibi_hidden_default:
                return
            prev = max([a["t1"] for a in self.acts if a["t1"] <= t] or [-1])
            start = self._blend_from(("default", prev), t, foot, size)
            foot, size = start
            put_sprite(canvas, name, anim_frame(name, t), foot, size)
            self.last = (foot, size)
            return
        k = act["kind"]
        lt = t - act["t0"]
        if k == "anim":
            name = act["name"]
            foot = self.resolve_target(act.get("foot"), shot)
            size = act.get("size", HOST_SIZE)
            if "move" in act:       # [(本 act 秒, x, y, size)]
                x, y, size = piecewise(act["move"], lt, ease_io)
                foot = (x, y)
            foot, size = self._blend_from(id(act), t, foot, size, act.get("blend", 0.22))
            fi = anim_frame(name, lt * act.get("speed", 1.0), act.get("mode", "loop"))
            put_sprite(canvas, name, fi, foot, size, act.get("flip", False))
            self.last = (foot, size)
        elif k == "pointer":
            name = act.get("name", "pointer_r")
            tip = self.resolve_target(act["tip"], shot)
            size = act.get("size", 340)
            s = size / 512
            off = TIP_OFF if name == "pointer_r" else (21.3 - 248, 232.1 - 482)
            foot = (tip[0] - off[0] * s, tip[1] - off[1] * s)
            foot, size = self._blend_from(id(act), t, foot, size, 0.25)
            put_sprite(canvas, name, anim_frame(name, lt), foot, size)
            self.last = (foot, size)
        elif k == "tap":
            self._draw_tap(canvas, t, act, shot)
        elif k == "peek":
            name = act.get("name", "peek_l")
            size = act.get("size", 360)
            s = size / 512
            if name == "peek_l":
                foot = (248 * s + act.get("x", 0), act["y"])
            else:
                foot = (act.get("x", W) - (512 - 248) * s, act["y"])
            put_sprite(canvas, name, anim_frame(name, lt, act.get("mode", "hold")), foot, size)
            self.last = (HOST, HOST_SIZE)

    def _blend_from(self, key, t, foot, size, dur=0.22):
        if key not in self.act_start:
            self.act_start[key] = (t, self.last)
        t0, (pf, ps) = self.act_start[key]
        u = (t - t0) / dur if dur > 0 else 1
        if u >= 1:
            return foot, size
        u = ease_io(u)
        arc = -60 * math.sin(math.pi * u) if math.hypot(foot[0] - pf[0], foot[1] - pf[1]) > 40 else 0
        return (lerp(pf[0], foot[0], u), lerp(pf[1], foot[1], u) + arc), lerp(ps, size, u)

    def _draw_tap(self, canvas, t, act, shot):
        tc = act["contact"]
        quick = act.get("quick", False)
        tgt = self.resolve_target(act["target"], shot)
        tsize = act.get("size", 280)
        home = act.get("home", HOST)
        hsize = act.get("home_size", HOST_SIZE)
        if "start_from" not in act:
            act["start_from"] = self.last
        sf, ss = act["start_from"]
        lead = TAP_CONTACT - (TAP_QUICK_START if quick else 0)
        ta = t - (tc - lead)                      # 從 tap 開始的秒數
        tap_t = ta + (TAP_QUICK_START if quick else 0)   # tap 動畫內部時間
        if tap_t < TAP_CONTACT:
            fi = anim_frame("tap", tap_t, "hold")
            air0 = 0.29 if not quick else TAP_QUICK_START
            if tap_t < air0:
                foot, size = sf, ss
            else:
                u = ease_io((tap_t - air0) / (TAP_CONTACT - air0))
                foot = (lerp(sf[0], tgt[0], u), lerp(sf[1], tgt[1], u) - 170 * math.sin(math.pi * u))
                size = lerp(ss, tsize, u)
            put_sprite(canvas, "tap", fi, foot, size)
            self.last = (foot, size)
            return
        hold = act.get("hold", 0.38)
        if tap_t < TAP_CONTACT + hold:
            fi = anim_frame("tap", tap_t, "hold")
            put_sprite(canvas, "tap", fi, tgt, tsize)
            self.last = (tgt, tsize)
            return
        if act.get("stay"):
            put_sprite(canvas, "tap", 11, tgt, tsize)
            self.last = (tgt, tsize)
            return
        # 跳回主持位
        bt = tap_t - TAP_CONTACT - hold
        back = act.get("back", 0.36)
        u = ease_io(bt / back)
        foot = (lerp(tgt[0], home[0], u), lerp(tgt[1], home[1], u) - 150 * math.sin(math.pi * u))
        size = lerp(tsize, hsize, u)
        name = "hop_l" if home[0] < tgt[0] else "hop_r"
        fi = 2 + int(clamp(u, 0, 0.999) * 4)
        if u >= 1:
            name, fi = act.get("after", self.default), anim_frame(act.get("after", self.default), bt - back)
        put_sprite(canvas, name, fi, foot, size)
        self.last = (foot, size)


def tap_span(contact, quick=False, hold=0.38, back=0.36):
    lead = TAP_CONTACT - (TAP_QUICK_START if quick else 0)
    return contact - lead, contact + hold + back


# ───────────────────────── 文字元件 ─────────────────────────
@lru_cache(maxsize=256)
def headline_layout(text, hl):
    f = None
    for px in range(96, 60, -4):
        f = font(F_ROUND, px)
        if text_w(f, text) <= 900:
            break
    x = 60
    chars = []
    for ch in text:
        w = text_w(f, ch)
        chars.append((ch, x, w))
        x += w
    hl_range = None
    if hl and hl in text:
        i = text.index(hl)
        hl_range = (chars[i][1], chars[i + len(hl) - 1][1] + chars[i + len(hl) - 1][2])
    return f, chars, hl_range


def draw_headline(canvas, text, t, hl=None, y=318, animate=True, color=INK, x0=None):
    if not text:
        return
    f, chars, hl_range = headline_layout(text, hl)
    total_w = chars[-1][1] + chars[-1][2] - 60
    shift = 0 if x0 in (None, "center") else x0 - 60
    if x0 == "center":
        shift = (W - total_w) / 2 - 60
    d = ImageDraw.Draw(canvas)
    if hl_range:
        u = ease_out((t - 0.3) / 0.25) if animate else 1
        if u > 0:
            a, b = hl_range
            d.rounded_rectangle([a + shift - 4, y + f.size * 0.78, a + shift + (b - a + 8) * u, y + f.size * 1.08], 10, fill=LEMON)
    for i, (ch, x, w) in enumerate(chars):
        u = ease_out((t - 0.04 * i) / 0.18) if animate else 1
        if u <= 0:
            continue
        dy = (1 - u) * 22
        if u < 1:
            layer = Image.new("RGBA", (int(w) + 20, f.size + 40), (0, 0, 0, 0))
            ImageDraw.Draw(layer).text((6, 10), ch, font=f, fill=color + (int(255 * u),))
            canvas.paste(layer, (int(x + shift) - 6, int(y + dy) - 10), layer)
        else:
            d.text((x + shift, y), ch, font=f, fill=color)


def pill(canvas, text, x, y, bg=SKY, fg=WHITE, stroke=True, px=34, right=False, scale=1.0, alpha=1.0):
    f = font(F_ROUND, px)
    tw = text_w(f, text)
    pw, ph = tw + 44, px + 30
    if right:
        x = x - pw
    layer = Image.new("RGBA", (int(pw) + 8, int(ph) + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle([2, 2, pw + 2, ph + 2], ph / 2, fill=bg + (255,), outline=INK + (255,), width=3)
    if stroke:
        d.text((24, 14), text, font=f, fill=fg, stroke_width=3, stroke_fill=INK)
    else:
        d.text((24, 14), text, font=f, fill=fg)
    if scale != 1.0:
        nw, nh = max(1, int(layer.width * scale)), max(1, int(layer.height * scale))
        cx, cy = x + layer.width / 2, y + layer.height / 2
        layer = layer.resize((nw, nh), Image.BILINEAR)
        x, y = cx - nw / 2, cy - nh / 2
    if alpha < 1:
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
    canvas.paste(layer, (int(x), int(y)), layer)
    return pw


def data_pill(canvas, rect):
    f = font(F_MED, 24)
    s = f"網站實際畫面・資料日 {DATA_DATE}"
    tw = text_w(f, s)
    rx, ry, rw, rh = rect
    x1 = min(rx + rw - 18, 950)
    x0 = x1 - tw - 28
    y1 = ry + rh - 16
    y0 = y1 - 40
    layer = Image.new("RGBA", (int(x1 - x0) + 4, 44), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle([0, 0, x1 - x0, 40], 20, fill=(255, 255, 255, 225), outline=DEEP + (200,), width=2)
    d.text((14, 5), s, font=f, fill=INK)
    canvas.paste(layer, (int(x0), int(y0)), layer)


def subtitle(canvas, text, t, y=SUB_Y):
    if not text:
        return
    f = font(F_BOLD, 48)
    lines = wrap_lines(text)
    a = clamp(t / 0.12, 0, 1)
    layer = Image.new("RGBA", (W, 150), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x = 96
    # 小尾巴（指向左上的比比）
    d.polygon([(70, 22), (98, 6), (88, 40)], fill=INK + (255,))
    for i, ln in enumerate(lines):
        d.text((x, 0 + i * 64), ln, font=f, fill=INK, stroke_width=5, stroke_fill=CREAM)
    if a < 1:
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * a)))
    canvas.paste(layer, (0, y), layer)


def bubble(canvas, text, box, tail=None, t=1.0, px=44, max_chars=9):
    """對話泡泡（白底墨黑框，粉圓）。box=(x0,y0,x1,y1)；tail=(x,y) 尖端。"""
    u = back_out(t / 0.25)
    if u <= 0.01:
        return
    x0, y0, x1, y1 = box
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    if tail:
        cx = clamp(tail[0], x0 + 40, x1 - 40)
        base_y = y1 if tail[1] > y1 else y0
        d.polygon([(cx - 26, base_y - (3 if base_y == y1 else -3)), (cx + 26, base_y - (3 if base_y == y1 else -3)), tail],
                  fill=WHITE + (255,), outline=INK + (255,))
        d.line([(cx - 26, base_y), tail, (cx + 26, base_y)], fill=INK, width=4)
    d.rounded_rectangle([x0, y0, x1, y1], 34, fill=WHITE + (255,), outline=INK + (255,), width=4)
    if tail:
        cx = clamp(tail[0], x0 + 40, x1 - 40)
        base_y = y1 if tail[1] > y1 else y0
        d.polygon([(cx - 23, base_y), (cx + 23, base_y), (lerp(cx, tail[0], 0.85), lerp(base_y, tail[1], 0.85))], fill=WHITE + (255,))
    f = font(F_ROUND, px)
    lines = wrap_lines(text, max_chars)
    lh = px * 1.3
    ty = (y0 + y1) / 2 - lh * len(lines) / 2 + 2
    for i, ln in enumerate(lines):
        tw = text_w(f, ln)
        d.text(((x0 + x1) / 2 - tw / 2, ty + i * lh), ln, font=f, fill=INK)
    if u != 1:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        sc = max(0.05, u)
        layer = layer.resize((int(W * sc), int(H * sc)), Image.BILINEAR)
        canvas.paste(layer, (int(cx - cx * sc), int(cy - cy * sc)), layer)
    else:
        canvas.paste(layer, (0, 0), layer)


def spot_overlay(canvas, rect, center, radius, a):
    """聚光燈：畫面卡外圍壓暗 30%，一次打上去就停。"""
    if a <= 0:
        return
    rx, ry, rw, rh = [int(v) for v in rect]
    m = Image.new("L", (rw, rh), int(255 * 0.32 * a))
    d = ImageDraw.Draw(m)
    cx, cy = center[0] - rx, center[1] - ry
    d.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=0)
    m = m.filter(ImageFilter.GaussianBlur(14))
    m = Image.fromarray(np.minimum(np.array(m), np.array(rounded_mask(rw, rh, 36))))
    dark = Image.new("RGBA", (rw, rh), (10, 20, 40, 255))
    dark.putalpha(m)
    canvas.paste(dark, (rx, ry), dark)
    ring = Image.new("RGBA", (rw, rh), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse([cx - radius, cy - radius, cx + radius, cy + radius], outline=LEMON + (int(230 * a),), width=6)
    canvas.paste(ring, (rx, ry), ring)


# ───────────────────────── Shot ─────────────────────────
class Shot:
    def __init__(self, sid, dur, layers=(), headline="", hl=None, sub="", pill_text=None, badge=None, bibi=None,
                 data=True, bubble_spec=None, spots=(), extra=None, post=None, cues=(), bibi_hidden_default=False,
                 headline_y=318, headline_center=False, headline_anim=True, pill_anim=False):
        self.sid, self.dur = sid, dur
        self.layers = list(layers)
        self.headline, self.hl, self.sub = headline, hl, sub
        self.pill_text, self.badge = pill_text, badge
        self.bibi = bibi or Bibi()
        self.data = data
        self.bubble_spec = bubble_spec
        self.spots = list(spots)
        self.extra = extra
        self.post = post
        self.cues = list(cues)
        self.bibi_hidden_default = bibi_hidden_default
        self.headline_y = headline_y
        self.headline_center = headline_center
        self.headline_anim = headline_anim
        self.pill_anim = pill_anim

    def render(self, t):
        cv = background().copy()
        if self.pill_text:
            u = back_out(t / 0.3) if self.pill_anim else 1
            pill(cv, self.pill_text, 60 - (1 - clamp(u, 0, 1)) * 300, 226)
        if self.badge:
            u = clamp(t / 0.25, 0, 1)
            pill(cv, self.badge, 960, 226, bg=LEMON, fg=INK, stroke=False, right=True, scale=lerp(0.6, 1, back_out(u)), alpha=u)
        draw_headline(cv, self.headline, t if self.headline_anim else 9, self.hl, y=self.headline_y,
                      x0="center" if self.headline_center else None)
        for L in self.layers:
            L.draw(cv, t, self)
        for sp in self.spots:   # dict(t0, t1, layer, src(sx,sy) or out, r)
            if sp["t0"] <= t < sp["t1"]:
                L = self.layers[sp.get("layer", 0)]
                c = L.map(*sp["src"]) if "src" in sp else sp["out"]
                a = clamp((t - sp["t0"]) / 0.2, 0, 1) * clamp((sp["t1"] - t) / 0.15, 0, 1)
                spot_overlay(cv, L.out_rect if "src" in sp else sp.get("rect", CARD), c, sp["r"], a)
        if self.data and self.layers and isinstance(self.layers[0], Rec):
            data_pill(cv, self.layers[0].rect)
        if self.extra:
            self.extra(cv, t, self)
        self.bibi.draw(cv, t, self)
        if self.post:
            self.post(cv, t, self)
        if self.bubble_spec:
            b = self.bubble_spec
            if b.get("t0", 0) <= t < b.get("t1", 99):
                bubble(cv, b["text"], b["box"], b.get("tail"), t - b.get("t0", 0), b.get("px", 44), b.get("max_chars", 9))
        else:
            subtitle(cv, self.sub, t)
        return cv


# ───────────────────────── 自繪元件 ─────────────────────────
def curtain(canvas, open_u, box=(0, 470, W, 1400)):
    """紅布幕（跟 bibi_reveal 同色系），open_u 0=全關 1=全開。"""
    x0, y0, x1, y1 = box
    wcov = (x1 - x0) / 2 * (1 - open_u) + 40 * open_u
    red, dark, gold = (226, 74, 66), (178, 44, 40), (246, 196, 66)
    d = ImageDraw.Draw(canvas)
    for side in (0, 1):
        if side == 0:
            a, b = x0, x0 + wcov
        else:
            a, b = x1 - wcov, x1
        d.rectangle([a, y0, b, y1], fill=red)
        n = max(2, int((b - a) / 60))
        for k in range(n + 1):
            fx = a + (b - a) * k / n
            d.line([(fx, y0 + 20), (fx, y1)], fill=dark, width=6)
        d.line([(a, y0), (a, y1)], fill=INK, width=4) if side == 1 else d.line([(b, y0), (b, y1)], fill=INK, width=4)
    d.rectangle([x0, y0 - 10, x1, y0 + 40], fill=red, outline=INK, width=4)
    for k in range(0, x1 - x0, 60):
        d.ellipse([x0 + k + 10, y0 + 22, x0 + k + 50, y0 + 58], fill=dark)
    d.rectangle([x0, y0 - 24, x1, y0 - 8], fill=gold, outline=INK, width=3)


_LAPTOP_FRAMES = None


def laptop_frame(t, size):
    global _LAPTOP_FRAMES
    if _LAPTOP_FRAMES is None:
        im = Image.open(LAPTOP)
        fr = []
        for i in range(im.n_frames):
            im.seek(i)
            fr.append(im.convert("RGBA"))
        _LAPTOP_FRAMES = fr
    i = int(t / 0.35) % len(_LAPTOP_FRAMES)
    return _LAPTOP_FRAMES[i].resize((size, size), Image.LANCZOS)


# ───────────────────────── 模糊清單（來源座標） ─────────────────────────
B_S03 = [(505, 2020, 665, 2105, -1, 2.4)]                      # 公司財報分頁 10/28 格內個股代號
B_S08D = [(410, 346, 732, 1082), (1762, 252, 2088, 1092), (400, 1060, 2110, 1350)]   # 3D 零件標籤公司膠囊、下方說明卡
B_S06D_CHAIN = [(400, 355, 2100, 470, 5.8, 99)]               # 產業鏈頁說明文字內的個股代號
B_S09D = [(400, 180, 2160, 1350)]                             # 關聯圖節點（公司名＋代號）整片
B_S10 = [(182, 1072, 832, 1222)]                              # ETF 行事曆格內代號
B_S11 = [(18, 1072, 1152, 1872)]                              # ETF 總覽清單（名稱、代號、數字）
B_S12 = [(146, 790, 1000, 1722, -1, 6.95), (36, 560, 178, 1380, 6.0, 99)]   # 下拉清單名稱代號、Y 軸 %
B_S13_M = [(436, 700, 694, 792, -1, 14.6), (874, 700, 1134, 792, -1, 14.6), (0, 846, 1170, 1044, -1, 14.6),
           (30, 1326, 1150, 1556, -1, 14.6), (660, 1850, 940, 1920, -1, 14.6), (110, 2046, 370, 2122, -1, 14.6),
           (410, 2070, 760, 2270, -1, 14.6), (670, 2400, 940, 2480, -1, 14.6),
           (0, 560, 1170, 640, -1, 14.6), (0, 570, 1170, 640, -1, 14.6)]    # 月配試算：投入金額、目標、明細、甜甜圈標籤與中心
B_S13_C = [(10, 660, 1160, 740, 14.6, 99), (20, 1010, 1160, 1215, 14.6, 99), (30, 1285, 160, 1960, 14.6, 99),
           (950, 1320, 1170, 1810, 14.6, 99), (0, 1960, 1170, 2532, 14.6, 99)]   # 複利：條件列、圖例名稱、Y 軸、末端％
B_S16 = [(36, 1990, 1134, 2215, 1.55, 99)]                    # 客服常見問題「該買哪一檔」「AI 分析」兩題
B_S05_TIP = [(520, 540, 1170, 980, 0.9, 1.75)]                # 滑過時的成交值提示框


def src_tap(layer, sx, sy):
    return ("src", layer, (sx, sy))


# ───────────────────────── 主版 40 鏡 ─────────────────────────
def shots_main():
    S = []
    WIN_M = 1170          # 手機滿寬

    # 01 鉤子：3D 自轉
    S.append(Shot("01", 1.5,
                  [Rec("S08f_mobile", [(0, 1.0), (1.5, 3.0)], [(0, 585, 760, WIN_M / 1.18), (1.5, 585, 740, WIN_M)])],
                  headline="AI 伺服器怎麼拆？", hl="怎麼拆", sub="",
                  bibi=Bibi([dict(t0=0.8, t1=9, kind="peek", name="peek_l", size=460, y=1420, x=0)]),
                  bibi_hidden_default=True, cues=[(0, "pop"), (0.8, "boop")]))

    # 02 三格拉進來
    def tiles02(cv, t, shot):
        specs = [("S04_mobile", 3.0, (585, 1080, 760)), ("S06_mobile", 0.3, (585, 1000, 760)), ("S13_mobile", 12.9, (585, 2110, 900))]
        for k, (clip, s0, (cx, cy, w)) in enumerate(specs):
            u = ease_out((t - 0.125 * k) / 0.3)
            if u <= 0:
                continue
            tw, th = 300, 760
            x = 60 + k * 330 + (1 - u) * 900
            y = 520
            out = 1 - ease_io((t - 1.25) / 0.25)
            src = reader(clip).get(s0 + t).copy()
            if clip == "S13_mobile":
                for b in B_S13_M:
                    frosted(src, b[:4], 24)
            hh = w * th / tw
            im = sresize(src, (tw, th), (cx - w / 2, cy - hh / 2, cx + w / 2, cy + hh / 2)).convert("RGBA")
            m = rounded_mask(tw, th, 30)
            im.putalpha(m)
            ImageDraw.Draw(im).rounded_rectangle([1, 1, tw - 2, th - 2], 30, outline=DEEP, width=3)
            if out < 1:
                sc = max(0.05, out)
                im = im.resize((max(1, int(tw * sc)), max(1, int(th * sc))), Image.BILINEAR)
                x = lerp(540 - tw * sc / 2, x + tw / 2 - tw * sc / 2, out)
                y = lerp(900 - th * sc / 2, y + th / 2 - th * sc / 2, out)
            cv.paste(im, (int(x), int(y)), im)
        if t < 1.25:
            data_pill(cv, (60, 520, 960, 760))
    S.append(Shot("02", 1.5, [Still(tiles02)], headline="一個網站串著看", hl="串著看",
                  sub="錢往哪跑、哪裡熱、配息怎麼排，我都整理好了", data=False,
                  bibi=Bibi([dict(t0=0, t1=1.5, kind="anim", name="slide_l", size=380,
                                  move=[(0, 1200, 1418, 380), (1.5, -200, 1418, 380)], blend=0)]),
                  cues=[(0.0, "blip"), (0.125, "blip"), (0.25, "blip"), (1.25, "whoosh")]))

    # 03 布幕拉開 LOGO
    def logo03(cv, t, shot):
        u = ease_out((t - 0.15) / 0.5)
        sc = 0.6 + 0.45 * back_out((t - 0.15) / 0.45, 2.2) if t > 0.15 else 0.6
        sc = sc if t < 0.6 else lerp(1.05, 1.0, ease_io((t - 0.6) / 0.3))
        px = int(560 * sc)
        lg = logo_sized(px)
        cv.paste(lg, (540 - px // 2, 935 - px // 2), lg)
        curtain(cv, ease_io(t / 0.55), (60, 520, 1020, 1350))
    S.append(Shot("03", 1.5, [Still(logo03)], headline="哩股哩股", hl="哩股哩股", headline_center=True,
                  sub="把公開資料，整理成看得懂的圖", data=False,
                  bibi=Bibi([dict(t0=0, t1=0.5, kind="anim", name="reveal", size=HOST_SIZE, mode="hold", speed=2.2, foot=HOST, blend=0.3),
                             dict(t0=0.5, t1=1.5, kind="anim", name="face_proud", size=HOST_SIZE, foot=HOST)]),
                  cues=[(0.0, "swish"), (0.45, "ding")]))

    # 04 認識比比（自介名牌）
    def logo_top(cv, t, shot):
        u = ease_io(t / 0.3) if shot.sid == "04" else 1
        px = int(lerp(560, 190, u))
        cy = lerp(935, 575, u)
        lg = logo_sized(px)
        cv.paste(lg, (540 - px // 2, int(cy - px / 2)), lg)
    S.append(Shot("04", 2.0, [Still(logo_top)], headline="認識比比", hl="比比", headline_center=True, data=False,
                  bibi=Bibi([dict(t0=0, t1=2.0, kind="anim", name="intro", size=700, mode="hold", foot=(540, 1470), blend=0)]),
                  bubble_spec=dict(text="我是比比，看不懂就問我！", box=(150, 690, 930, 830), tail=(700, 900), t0=0.5, max_chars=12),
                  bibi_hidden_default=True, cues=[(0.35, "boop"), (0.8, "chirp")]))

    # 05 跟我來 → 跳到主持位
    S.append(Shot("05", 1.5, [Still(logo_top)], headline="5 大功能逛一圈", hl="5 大功能", headline_center=True, data=False,
                  bibi=Bibi([dict(t0=0, t1=0.95, kind="anim", name="talk_excited", size=700, foot=(540, 1470), blend=0),
                             dict(t0=0.95, t1=1.5, kind="anim", name="hop_l", size=HOST_SIZE, speed=1.4,
                                  move=[(0, 540, 1470, 700), (0.55, HOST[0], HOST[1], HOST_SIZE)], blend=0)]),
                  bubble_spec=dict(text="5 個功能，跟我來！", box=(200, 700, 880, 830), tail=(600, 900), t0=0.0, t1=0.95, max_chars=12),
                  bibi_hidden_default=True, cues=[(0.95, "boop")]))

    # 06 ① 總覽：比比拿手機 → 手機放大成畫面卡
    rec06 = Rec("S01_mobile", [(0, 0.0), (2.0, 0.85)], [(0, 585, 1180, WIN_M)])
    def phone06(cv, t, shot):
        if t >= 1.2:
            rec06.draw(cv, t, shot)
            data_pill(cv, CARD)
            return
        idx = bibi_index()["phone"]
        fi = anim_frame("phone", t)
        size, foot = 820, (540, 1330)
        s = size / 512
        corners = idx["interaction"][fi]["screen_corners"]
        q = [(foot[0] + (cx - 248) * s, foot[1] + (cy - 482) * s) for cx, cy in corners]
        u = ease_io((t - 0.8) / 0.4)
        src = reader("S01_mobile").get(t * 0.4)
        box = (30, 1150, 1140, 1770)            # 加權指數那一塊（橫向，貼手機螢幕）
        if u <= 0:
            put_sprite(cv, "phone", fi, foot, size)
        else:
            rx, ry, rw, rh = CARD
            target = [(rx, ry), (rx + rw, ry), (rx + rw, ry + rh), (rx, ry + rh)]
            q = [(lerp(a[0], b[0], u), lerp(a[1], b[1], u)) for a, b in zip(q, target)]
            bw = lerp(box[2] - box[0], WIN_M, u)
            bh = lerp(box[3] - box[1], WIN_M * rh / rw, u)
            bc = (lerp((box[0] + box[2]) / 2, 585, u), lerp((box[1] + box[3]) / 2, 1180, u))
            box = (bc[0] - bw / 2, bc[1] - bh / 2, bc[0] + bw / 2, bc[1] + bh / 2)
        minx, miny = min(p[0] for p in q), min(p[1] for p in q)
        maxx, maxy = max(p[0] for p in q), max(p[1] for p in q)
        ow, oh = int(maxx - minx) + 2, int(maxy - miny) + 2
        crop = src.crop(tuple(int(v) for v in box))
        qq = [(p[0] - minx, p[1] - miny) for p in q]
        coeffs = _persp_coeffs(qq, [(0, 0), (crop.width, 0), (crop.width, crop.height), (0, crop.height)])
        warped = crop.transform((ow, oh), Image.PERSPECTIVE, coeffs, Image.BICUBIC)
        m = Image.new("L", (ow, oh), 0)
        ImageDraw.Draw(m).polygon(qq, fill=255)
        if u > 0.3:
            m = Image.fromarray(np.minimum(np.array(m), np.array(_round_quad_mask(ow, oh, qq, int(36 * u)))))
        cv.paste(warped, (int(minx), int(miny)), m)
    S.append(Shot("06", 2.0, [Still(phone06)], headline="① 每天先看這頁", hl="先看這頁", pill_text="① 總覽", pill_anim=True,
                  sub="大盤、漲跌家數、資金熱度，這頁一次看完", data=False,
                  bibi_hidden_default=True,
                  bibi=Bibi([dict(t0=0.8, t1=1.3, kind="anim", name="hop_l", size=HOST_SIZE, move=[(0, 540, 1330, 820), (0.5, HOST[0], HOST[1], HOST_SIZE)], blend=0),
                             dict(t0=1.3, t1=2.0, kind="anim", name="face_nod", size=HOST_SIZE, foot=HOST)]),
                  cues=[(0.8, "whoosh")]))

    # 07 往下捲＋指示棒指主圖
    r07 = Rec("S01_mobile", [(0, 0.9), (1.5, 2.6)], [(0, 585, 1250, WIN_M / 1.25), (1.5, 585, 1420, WIN_M / 1.4)])
    S.append(Shot("07", 1.5, [r07], headline="不用開好幾個 App", hl="好幾個", pill_text="① 總覽",
                  sub="以前要切好幾個 App，現在看這頁就好",
                  bibi=Bibi([dict(t0=0, t1=1.5, kind="pointer", tip=(470, 1180), size=360)])))

    # 08 不用熬夜：laptop 小卡 vs 畫面
    r08 = Rec("S01_mobile", [(0, 2.6), (1.5, 2.9)], [(0, 585, 1180, 760)], rect=(420, 470, 600, 930))
    def lap08(cv, t, shot):
        u = ease_out(t / 0.25)
        im = laptop_frame(t, 320)
        dim = Image.new("RGBA", im.size, (40, 50, 110, 70))
        im = Image.alpha_composite(im, dim)
        m = rounded_mask(320, 320, 30)
        im.putalpha(Image.fromarray(np.minimum(np.array(im.getchannel("A")), np.array(m))))
        cv.paste(im, (60 - int((1 - u) * 400), 600), im)
        f = font(F_ROUND, 34)
        ImageDraw.Draw(cv).text((80 - int((1 - u) * 400), 940), "熬夜翻資料…", font=f, fill=INK)
    S.append(Shot("08", 1.5, [r08, Still(lap08)], headline="不用熬夜看盤", hl="熬夜", pill_text="① 總覽",
                  sub="下班看一頁就好，不用熬夜翻資料",
                  bibi=Bibi([dict(t0=0, t1=0.7, kind="anim", name="face_sleepy", size=HOST_SIZE, foot=HOST),
                             dict(t0=0.7, t1=1.2, kind="anim", name="face_wink", size=HOST_SIZE, foot=HOST),
                             dict(t0=1.2, t1=1.5, kind="anim", name="slide_r", size=HOST_SIZE,
                                  move=[(0, HOST[0], HOST[1], HOST_SIZE), (0.3, 1250, HOST[1], HOST_SIZE)], blend=0)]),
                  cues=[(1.2, "whoosh")]))

    # 09 ② 財經日曆：踩 FED 消息分頁
    r09 = Rec("S03_mobile", [(0, 1.08), (0.62, 1.70), (2.0, 3.2)], [(0, 585, 930, WIN_M / 1.05), (2.0, 585, 960, WIN_M / 1.12)],
              blur=B_S03, enter=("slide_r", 0.25))
    S.append(Shot("09", 2.0, [r09], headline="② 財報法說 FED", hl="FED", pill_text="② 財經日曆", pill_anim=True,
                  sub="財報、法說、FED 的日子，我排在同一張月曆",
                  bibi=Bibi([dict(t0=-0.1, t1=0.0, kind="anim", name="hop_l", size=HOST_SIZE, move=[(0, 1250, 1418, 380), (0.3, HOST[0], HOST[1], HOST_SIZE)]),
                             dict(t0=tap_span(0.62)[0], t1=tap_span(0.62)[1], kind="tap", contact=0.62, target=src_tap(0, 661, 605)),
                             dict(t0=tap_span(0.62)[1], t1=2.0, kind="anim", name="calendar", size=HOST_SIZE, foot=HOST)],
                            default="talk_explain"),
                  cues=[(0, "whoosh"), (0.62, "tap")]))

    # 10 點第一則 FED 事件 → 說明
    r10 = Rec("S03_mobile", [(0, 4.48), (0.62, 5.10), (1.1, 6.2), (2.0, 8.7)],
              [(0, 585, 1150, WIN_M), (0.75, 585, 1150, WIN_M), (1.25, 585, 700, WIN_M / 1.5), (2.0, 585, 680, WIN_M / 1.5)])
    S.append(Shot("10", 2.0, [r10], headline="點一下就懂", hl="點一下", pill_text="② 財經日曆",
                  sub="點一下，數據說明和下次公布日都在這",
                  bibi=Bibi([dict(t0=tap_span(0.62)[0], t1=tap_span(0.62)[1], kind="tap", contact=0.62, target=src_tap(0, 894, 1093)),
                             dict(t0=tap_span(0.62)[1], t1=2.0, kind="anim", name="face_nod", size=HOST_SIZE, foot=HOST)]),
                  cues=[(0.62, "tap")]))

    # 11 點第二則 FED 事件
    r11 = Rec("S03_mobile", [(0, 13.78), (0.62, 14.40), (1.5, 17.3)],
              [(0, 585, 1150, WIN_M), (0.75, 585, 1150, WIN_M), (1.2, 585, 700, WIN_M / 1.4), (1.5, 585, 690, WIN_M / 1.45)])
    S.append(Shot("11", 1.5, [r11], headline="重要日子不漏看", hl="不漏看", pill_text="② 財經日曆",
                  sub="重要日子不用到處查，我幫你排好",
                  bibi=Bibi([dict(t0=tap_span(0.62)[0], t1=tap_span(0.62, back=0.3)[1], kind="tap", contact=0.62, back=0.3, target=src_tap(0, 585, 1336)),
                             dict(t0=1.3, t1=1.5, kind="anim", name="hop_l", size=HOST_SIZE, move=[(0, HOST[0], HOST[1], HOST_SIZE), (0.2, -220, HOST[1], HOST_SIZE)], blend=0)],
                            default="news"),
                  cues=[(0.62, "tap"), (1.3, "boop")]))

    # 12 ③ 資金輪動（靜止）
    r12 = Rec("S04_mobile", [(0, 0.0), (2.0, 0.9)], [(0, 585, 1060, WIN_M)], enter=("slide_l", 0.25))
    S.append(Shot("12", 2.0, [r12], headline="③ 錢往哪裡跑", hl="錢", pill_text="③ 資金", pill_anim=True,
                  sub="錢都跑去哪了？我們來看資金輪動",
                  bibi=Bibi([dict(t0=0, t1=0.4, kind="anim", name="hop_r", size=HOST_SIZE, move=[(0, -220, HOST[1], HOST_SIZE), (0.4, HOST[0], HOST[1], HOST_SIZE)], blend=0),
                             dict(t0=0.4, t1=1.1, kind="anim", name="talk_explain", size=HOST_SIZE, foot=HOST),
                             dict(t0=1.1, t1=2.0, kind="anim", name="face_think", size=HOST_SIZE, foot=HOST)]),
                  cues=[(0, "whoosh")]))

    # 13 踩 ▶ 播放
    r13 = Rec("S04_mobile", [(0, 0.98), (0.62, 1.60), (2.5, 7.6)], [(0, 585, 760, WIN_M), (0.85, 585, 760, WIN_M), (1.35, 585, 1080, 900)])
    S.append(Shot("13", 2.5, [r13], headline="按播放看它轉", hl="播放", pill_text="③ 資金",
                  sub="我踩一下播放，族群怎麼輪一路播給你看",
                  bibi=Bibi([dict(t0=tap_span(0.62)[0], t1=tap_span(0.62)[1], kind="tap", contact=0.62, target=src_tap(0, 1086, 270)),
                             dict(t0=tap_span(0.62)[1], t1=1.6, kind="anim", name="face_shock", size=HOST_SIZE, foot=HOST),
                             dict(t0=1.6, t1=2.5, kind="anim", name="coins", size=HOST_SIZE, foot=HOST)]),
                  cues=[(0.62, "tap"), (0.7, "rise")]))

    # 14 分流樹（靜止）＋聚光燈
    r14 = Rec("S05_mobile", [(0, 0.0), (2.0, 0.8)], [(0, 585, 820, WIN_M), (2.0, 585, 1000, WIN_M)])
    S.append(Shot("14", 2.0, [r14], headline="大盤的錢分去哪", hl="分去哪", pill_text="③ 資金",
                  sub="從大盤分到產業，再分到每個族群",
                  spots=[dict(t0=0.55, t1=2.0, src=(420, 780), r=250)],
                  bibi=Bibi([dict(t0=0, t1=2.0, kind="anim", name="spotlight", size=HOST_SIZE, foot=HOST, mode="hold")], default="face_think")))

    # 15 分流樹踩 ▶
    r15 = Rec("S05_mobile", [(0, 0.98), (0.62, 1.60), (2.5, 8.2)], [(0, 585, 760, WIN_M), (0.85, 585, 760, WIN_M), (1.4, 560, 860, 900)],
              blur=B_S05_TIP)
    S.append(Shot("15", 2.5, [r15], headline="每天分流一路播", hl="一路播", pill_text="③ 資金",
                  sub="原來錢在這裡轉！每天都能回看",
                  bibi=Bibi([dict(t0=tap_span(0.62)[0], t1=tap_span(0.62)[1], kind="tap", contact=0.62, target=src_tap(0, 1086, 270)),
                             dict(t0=tap_span(0.62)[1], t1=2.1, kind="anim", name="face_laugh", size=HOST_SIZE, foot=HOST),
                             dict(t0=2.1, t1=2.5, kind="anim", name="hop_r", size=HOST_SIZE, move=[(0, HOST[0], HOST[1], HOST_SIZE), (0.4, 1250, HOST[1], HOST_SIZE)], blend=0)]),
                  cues=[(0.62, "tap"), (0.7, "rise"), (2.1, "boop")]))

    # 16 ④ 熱力圖
    r16 = Rec("S06_mobile", [(0, 0.0), (2.0, 2.0)], [(0, 585, 1010, WIN_M), (0.5, 585, 1010, WIN_M), (2.0, 585, 980, WIN_M / 1.05)],
              enter=("slide_up", 0.25))
    S.append(Shot("16", 2.0, [r16], headline="④ 哪裡熱一眼看", hl="一眼看", pill_text="④ 產業", pill_anim=True,
                  sub="方塊越大，成交值越大；紅漲綠跌",
                  bibi=Bibi([dict(t0=0, t1=0.4, kind="anim", name="hop_r", size=HOST_SIZE, move=[(0, -220, HOST[1], HOST_SIZE), (0.4, HOST[0], HOST[1], HOST_SIZE)], blend=0),
                             dict(t0=0.4, t1=2.0, kind="anim", name="magnifier", size=HOST_SIZE, foot=HOST)]),
                  cues=[(0, "thud")]))

    # 17 踩方塊 → 進產業鏈（桌機：點方塊跳產業鏈頁）
    r17a = Rec("S06_desktop", [(0, 4.98), (0.62, 5.60), (0.9, 5.75)], [(0, 960, 722, 1160)], exit=("zoom_to", 0.25, None))
    r17b = Rec("S06_desktop", [(0, 6.3), (0.6, 7.4)], [(0, 1000, 720, 1300), (0.6, 960, 700, 1220)], blur=B_S06D_CHAIN, enter=("zoom", 0.25, 0.7))

    class Switch:
        def __init__(self, a, b, tcut):
            self.a, self.b, self.tcut = a, b, tcut
            self.rect = a.rect

        @property
        def out_rect(self):
            return self.a.out_rect

        def map(self, sx, sy):
            return self.a.map(sx, sy)

        def draw(self, cv, t, shot):
            if t < self.tcut:
                    self.a.draw(cv, t, _Dur(shot, self.tcut))
            else:
                self.b.draw(cv, t - self.tcut, shot)
                data_pill(cv, CARD)

    class _Dur:
        def __init__(self, shot, dur):
            self.dur = dur
            self.__dict__.update({k: v for k, v in shot.__dict__.items() if k != "dur"})

    sw17 = Switch(r17a, r17b, 0.9)
    r17a.exit = ("zoom_to", 0.25, (60 + (580 - 380) / 1160 * 960, 470 + (360 - 160) / 1124 * 930))
    S.append(Shot("17", 1.5, [sw17], headline="點進產業鏈", hl="產業鏈", pill_text="④ 產業",
                  sub="熱的那一塊，踩下去就進產業鏈", data=True,
                  bibi=Bibi([dict(t0=tap_span(0.62)[0], t1=0.9, kind="tap", contact=0.62, stay=True, target=src_tap(0, 580, 360)),
                             dict(t0=0.9, t1=1.5, kind="anim", name="face_star", size=HOST_SIZE, foot=HOST, blend=0.2)]),
                  cues=[(0.62, "tap"), (0.7, "whoosh")]))

    # 18 2D 剖析圖＋指示棒
    r18 = Rec("S07_mobile", [(0, 0.0), (2.0, 1.3)], [(0, 640, 880, 1100), (2.0, 640, 880, 1100 / 1.3)])
    S.append(Shot("18", 2.0, [r18], headline="2D 看上下游", hl="上下游", pill_text="④ 產業",
                  sub="2D 先看零件怎麼排、每段在做什麼",
                  bibi=Bibi([dict(t0=0, t1=2.0, kind="pointer", tip=src_tap(0, 520, 760), size=360)])))

    # 19 踩「3D」鈕 → 戴眼鏡
    r19 = Rec("S08a_mobile", [(0, 1.0), (0.62, 1.62), (1.5, 2.9)], [(0, 470, 560, 820), (0.75, 470, 560, 820), (1.4, 585, 740, WIN_M)])
    S.append(Shot("19", 1.5, [r19], headline="切到 3D！", hl="3D", pill_text="④ 產業",
                  sub="戴上眼鏡，切到 3D！",
                  bibi=Bibi([dict(t0=tap_span(0.62)[0], t1=tap_span(0.62)[1], kind="tap", contact=0.62, target=src_tap(0, 288, 280)),
                             dict(t0=tap_span(0.62)[1], t1=1.5, kind="anim", name="3dglasses", size=HOST_SIZE, foot=HOST, mode="once")]),
                  cues=[(0.62, "tap"), (0.9, "pop")]))

    # 20 3D 自動轉（主力段開始）
    r20 = Rec("S08f_mobile", [(0, 0.4), (3.0, 4.6)], [(0, 585, 740, WIN_M), (3.0, 585, 730, WIN_M / 1.08)])
    S.append(Shot("20", 3.0, [r20], headline="整台拆開看", hl="拆開看", pill_text="④ 產業",
                  sub="哇！零件一層一層拆開了",
                  bibi=Bibi([dict(t0=0, t1=1.0, kind="anim", name="3dglasses", size=HOST_SIZE, foot=HOST, mode="hold", speed=1.0),
                             dict(t0=1.0, t1=3.0, kind="anim", name="face_star", size=HOST_SIZE, foot=HOST)]),
                  cues=[(0, "chorus")]))

    # 21 拖曳旋轉
    r21 = Rec("S08b_mobile", [(0, 0.7), (2.5, 3.3)], [(0, 585, 740, WIN_M)])
    S.append(Shot("21", 2.5, [r21], headline="拖一下就轉", hl="拖一下", pill_text="④ 產業",
                  sub="拖曳就能轉，換個角度看看",
                  bibi=Bibi([dict(t0=0.3, t1=1.2, kind="anim", name="hop_r", size=HOST_SIZE, move=[(0, HOST[0], HOST[1], HOST_SIZE), (0.9, HOST[0] + 60, HOST[1], HOST_SIZE)], blend=0),
                             dict(t0=1.2, t1=2.5, kind="anim", name="face_wink", size=HOST_SIZE, foot=(HOST[0] + 60, HOST[1]))]),
                  cues=[(0.3, "swish")]))

    # 22 拉近
    r22 = Rec("S08c_mobile", [(0, 0.7), (2.0, 3.2)], [(0, 585, 700, WIN_M), (2.0, 600, 640, WIN_M / 1.25)])
    S.append(Shot("22", 2.0, [r22], headline="拉近看細節", hl="細節", pill_text="④ 產業",
                  sub="拉近看，每一層的名字都標好了",
                  bibi=Bibi([dict(t0=0, t1=0.5, kind="anim", name="face_shock", size=HOST_SIZE, foot=HOST),
                             dict(t0=0.5, t1=1.3, kind="anim", name="magnifier", size=HOST_SIZE, foot=HOST),
                             dict(t0=1.3, t1=2.0, kind="anim", name="face_love", size=HOST_SIZE, foot=HOST)])))

    # 23 踩零件標籤 → 說明卡標題（桌機；公司膠囊與說明卡模糊）
    r23 = Rec("S08d_desktop", [(0, 2.43), (0.62, 3.05), (2.5, 5.2)],
              [(0, 980, 690, 1160), (0.8, 980, 690, 1160), (1.7, 900, 600, 1050)], blur=B_S08D)
    S.append(Shot("23", 2.5, [r23], headline="點零件看環節", hl="環節", pill_text="④ 產業",
                  sub="我踩一下零件，卡片告訴你是哪個環節",
                  bibi=Bibi([dict(t0=tap_span(0.62)[0], t1=tap_span(0.62)[1], kind="tap", contact=0.62, target=src_tap(0, 560, 300)),
                             dict(t0=tap_span(0.62)[1], t1=2.5, kind="anim", name="face_proud", size=HOST_SIZE, foot=HOST)]),
                  cues=[(0.62, "tap")]))

    # 24 不只 AI 伺服器：三格（AI 伺服器側面、HBM、液冷）
    def tiles24(cv, t, shot):
        specs = [("S08e_desktop", 3.0, (1225, 690, 520)), ("S08g_mobile", 3.6, (585, 700, 560)), ("S08h_mobile", 3.6, (585, 700, 600))]
        tw, th = 300, 900
        for k, (clip, s0, (cx, cy, w)) in enumerate(specs):
            u = ease_out((t - 0.12 * k) / 0.3)
            if u <= 0:
                continue
            x, y = 60 + k * 330, 485
            src = reader(clip).get(s0 + t * 0.8)
            hh = w * th / tw
            im = sresize(src, (tw, th), (cx - w / 2, cy - hh / 2, cx + w / 2, cy + hh / 2)).convert("RGBA")
            m = rounded_mask(tw, th, 30).copy()
            ImageDraw.Draw(m).rectangle([0, int(th * u), tw, th], fill=0)
            im.putalpha(m)
            bd = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
            ImageDraw.Draw(bd).rounded_rectangle([1, 1, tw - 2, th - 2], 30, outline=DEEP, width=3)
            bd.putalpha(Image.fromarray(np.minimum(np.array(bd.getchannel("A")), np.array(m))))
            im.alpha_composite(bd)
            # 聚光燈：依序打亮（其他兩格壓暗）
            cur = int(clamp((t - 0.5) / 0.5, 0, 2.999)) if t >= 0.5 else -1
            if cur >= 0 and cur != k:
                dk = Image.new("RGBA", (tw, th), (10, 20, 40, int(255 * 0.32)))
                dk.putalpha(Image.fromarray(np.minimum(np.array(dk.getchannel("A")), np.array(m))))
                im.alpha_composite(dk)
            cv.paste(im, (x, y), im)
            lab = ["AI 伺服器", "HBM", "液冷散熱"][k]
            f = font(F_ROUND, 34)
            if u >= 1:
                pill(cv, lab, x + tw / 2 - (text_w(f, lab) + 44) / 2, y + 16, bg=WHITE, fg=INK, stroke=False, px=30)
            if cur == k:
                ImageDraw.Draw(cv).rounded_rectangle([x - 4, y - 4, x + tw + 4, y + th + 4], 32, outline=LEMON, width=8)
        data_pill(cv, (60, 485, 960, 900))
    S.append(Shot("24", 2.0, [Still(tiles24)], headline="不只 AI 伺服器", hl="不只", pill_text="④ 產業", data=False,
                  sub="半導體、HBM、液冷…19 種產品都能轉",
                  bibi=Bibi([dict(t0=0, t1=2.0, kind="anim", name="spotlight", size=HOST_SIZE, foot=HOST, mode="loop")], default="face_star"),
                  cues=[(0.5, "blip"), (1.0, "blip"), (1.5, "blip")]))

    # 25 關聯圖（遠景＋整片模糊）
    r25 = Rec("S09_desktop", [(0, 0.6), (2.5, 3.6)], [(0, 1250, 700, 1380), (2.5, 1400, 690, 1380)], blur=B_S09D, blur_r=7, blur_white=0.15,
              enter=("wipe_down", 0.3))
    S.append(Shot("25", 2.5, [r25], headline="上下游一張連", hl="一張連", pill_text="④ 產業",
                  sub="連線是供貨關係，滑過去上下游就亮",
                  bibi=Bibi([dict(t0=0, t1=1.0, kind="anim", name="face_think", size=HOST_SIZE, foot=HOST),
                             dict(t0=1.0, t1=2.5, kind="pointer", tip=(560, 960), size=360)], default="face_nod"),
                  cues=[(0, "swish")]))

    # 26 手機關聯圖（環節群組層，無公司）推近
    r26 = Rec("S09_mobile", [(0, 0.5), (2.0, 2.5)], [(0, 585, 700, WIN_M), (1.6, 640, 640, WIN_M / 1.3)])
    def curtain26(cv, t, shot):
        u = ease_io((t - 1.6) / 0.4)
        if u > 0:
            curtain(cv, 1 - u, (60, 470, 1020, 1400))
    S.append(Shot("26", 2.0, [r26], headline="產業關係串起來", hl="串起來", pill_text="④ 產業",
                  sub="原來是這樣接的！一張就看懂", post=curtain26,
                  bibi=Bibi([dict(t0=0, t1=1.0, kind="anim", name="hop_r", size=HOST_SIZE, foot=HOST),
                             dict(t0=1.0, t1=2.0, kind="anim", name="face_love", size=HOST_SIZE, foot=HOST)]),
                  cues=[(1.6, "swish"), (1.9, "chord")]))

    # 27 ETF 轉場字卡（布幕拉開）
    r27 = Rec("S10_mobile", [(0, 1.0), (1.5, 1.6)], [(0, 585, 1080, WIN_M)], blur=B_S10)

    def card27(cv, t, shot):
        r27.draw(cv, t, shot)
        data_pill(cv, CARD)
        curtain(cv, ease_io(t / 0.45), (60, 470, 1020, 1400))
    S.append(Shot("27", 1.5, [Still(card27)], headline="存 ETF 的人看這頁", hl="ETF", pill_text="⑤ ETF", pill_anim=True, data=False,
                  headline_y=318, sub="存 ETF 的人，這幾頁整理給你",
                  bibi=Bibi([dict(t0=0, t1=1.5, kind="anim", name="piggy", size=520, foot=(770, 1300), blend=0.0)]),
                  cues=[(0, "swish"), (0.6, "ding")]))

    # 28 ⑤ ETF 行事曆：踩有事件的那天
    r28 = Rec("S10_mobile", [(0, 1.83), (0.62, 2.45), (2.0, 3.9)], [(0, 585, 1080, WIN_M), (0.8, 585, 1080, WIN_M), (1.5, 585, 1120, 900)],
              blur=B_S10, enter=("fade", 0.15))
    S.append(Shot("28", 2.0, [r28], headline="⑤ 除息一張月曆", hl="月曆", pill_text="⑤ ETF",
                  sub="哪天除息，月曆上一眼就看到",
                  bibi=Bibi([dict(t0=tap_span(0.62)[0], t1=tap_span(0.62)[1], kind="tap", contact=0.62, target=src_tap(0, 583, 1102)),
                             dict(t0=tap_span(0.62)[1], t1=2.0, kind="anim", name="calendar", size=HOST_SIZE, foot=HOST)]),
                  cues=[(0.62, "tap")]))

    # 29 ETF 總覽：分類一個個切（清單模糊）
    r29 = Rec("S11_mobile", [(0, 1.0), (1.5, 6.7)], [(0, 585, 780, WIN_M)], blur=B_S11)
    S.append(Shot("29", 1.5, [r29], headline="分類幫你分好", hl="分好", pill_text="⑤ ETF",
                  sub="配息型、市值型、主題型、債券型",
                  bibi=Bibi([dict(t0=0, t1=1.5, kind="pointer", tip=src_tap(0, 420, 440), size=360)]),
                  cues=[(0.2, "blip"), (0.55, "blip"), (0.9, "blip"), (1.25, "blip")]))

    # 30 報酬比較：勾三檔
    r30 = Rec("S12_mobile", [(0, 2.6), (0.4, 3.0), (1.0, 4.5), (1.6, 6.0), (2.5, 8.4)], [(0, 585, 960, WIN_M), (1.75, 585, 960, WIN_M), (2.3, 585, 880, WIN_M / 1.15)],
              blur=B_S12)
    taps30 = []
    for c, sy in [(0.4, 845), (1.0, 967), (1.6, 1088)]:
        a0, a1 = tap_span(c, quick=True, hold=0.3, back=0.36)
        last = c > 1.5
        taps30.append(dict(t0=a0, t1=a1 if last else c + 0.39, kind="tap", contact=c, quick=True, hold=0.3, back=0.36,
                           stay=not last, size=230, target=src_tap(0, 98, sy)))
    S.append(Shot("30", 2.5, [r30], headline="含息不含息分開比", hl="分開比", pill_text="⑤ ETF",
                  sub="幾檔一起比，含息不含息分開算（過去不代表未來）",
                  bibi=Bibi(taps30, default="face_think"),
                  cues=[(0.4, "tap"), (1.0, "tap"), (1.6, "tap"), (1.95, "rise")]))

    # 31 月配試算：換組合
    B31 = [(0, 980, 1170, 1060, -1, 1.0), (0, 1170, 1170, 1440, -1, 1.0), (0, 1600, 190, 2532, -1, 1.0)] + \
          [tuple(list(b[:4]) + [11.0, 14.6]) for b in B_S13_M]
    r31 = Rec("S13_mobile", [(0, 0.0), (1.0, 0.6), (1.0001, 11.52), (1.6, 12.12), (2.5, 13.5)],
              [(0, 585, 1970, WIN_M), (1.0, 585, 1990, WIN_M / 1.04), (1.0001, 585, 1066, WIN_M), (1.75, 585, 1066, WIN_M), (2.5, 585, 1700, WIN_M)],
              blur=B31)
    S.append(Shot("31", 2.5, [r31], headline="看每月配息落在哪", hl="落在哪", pill_text="⑤ ETF",
                  sub="自己搭組合，看哪幾個月有配息（依歷史配息試算，不代表未來）",
                  bibi=Bibi([dict(t0=0, t1=tap_span(1.6)[0], kind="anim", name="calc", size=HOST_SIZE, foot=HOST),
                             dict(t0=tap_span(1.6)[0], t1=tap_span(1.6)[1], kind="tap", contact=1.6, target=src_tap(0, 810, 745)),
                             dict(t0=tap_span(1.6)[1], t1=2.5, kind="anim", name="face_nod", size=HOST_SIZE, foot=HOST)]),
                  cues=[(1.0, "swish"), (1.6, "tap")]))

    # 32 複利試算表
    r32 = Rec("S13_mobile", [(0, 13.95), (0.62, 14.57), (2.0, 18.2)], [(0, 585, 716, WIN_M), (0.8, 585, 716, WIN_M), (1.6, 585, 1420, WIN_M)],
              blur=B_S13_M + B_S13_C)
    S.append(Shot("32", 2.0, [r32], headline="配息再投入怎麼走", hl="再投入", pill_text="⑤ ETF",
                  sub="再投入和只領現金，兩條線並排看（過去不代表未來）",
                  bibi=Bibi([dict(t0=tap_span(0.62)[0], t1=tap_span(0.62)[1], kind="tap", contact=0.62, target=src_tap(0, 976, 279)),
                             dict(t0=tap_span(0.62)[1], t1=2.0, kind="anim", name="growth", size=HOST_SIZE, foot=HOST)]),
                  cues=[(0.62, "tap"), (0.8, "rise")]))

    # 33 甜甜圈本體＋喝珍奶
    r33 = Rec("S13_mobile", [(0, 12.9), (1.5, 13.2)], [(0, 585, 1960, WIN_M), (1.5, 585, 1990, WIN_M / 1.05)], blur=B_S13_M)
    S.append(Shot("33", 1.5, [r33], headline="不用自己拉表格", hl="不用", pill_text="⑤ ETF",
                  sub="這些試算，網站都先幫你算好",
                  bibi=Bibi([dict(t0=0, t1=1.2, kind="anim", name="boba", size=HOST_SIZE, foot=HOST),
                             dict(t0=1.2, t1=1.5, kind="anim", name="hop_r", size=280, move=[(0, HOST[0], HOST[1], HOST_SIZE), (0.3, 230, 880, 280)], blend=0)]),
                  cues=[(1.2, "boop")]))

    # 34 四步串著看（動態圖形）
    mini = [("S03_mobile", 3.4, (585, 1250, 1170), "看消息"), ("S04_mobile", 4.0, (585, 1080, 1100), "錢往哪跑"),
            ("S08f_mobile", 1.5, (585, 740, 1170), "誰在做"), ("S10_mobile", 3.6, (585, 1150, 1170), "自己怎麼排")]
    pos = [(80, 520), (560, 520), (560, 960), (80, 960)]
    MW, MH = 440, 380
    _mini_cache = {}

    def mini_img(k):
        if k not in _mini_cache:
            clip, st, (cx, cy, w), lab = mini[k]
            src = reader(clip).get(st).copy()
            if clip == "S10_mobile":
                for b in B_S10:
                    frosted(src, b[:4], 24)
            if clip == "S03_mobile":
                for b in B_S03:
                    frosted(src, b[:4], 24)
            hh = w * MH / MW
            im = sresize(src, (MW, MH), (cx - w / 2, cy - hh / 2, cx + w / 2, cy + hh / 2)).convert("RGBA")
            im.putalpha(rounded_mask(MW, MH, 28))
            ImageDraw.Draw(im).rounded_rectangle([1, 1, MW - 2, MH - 2], 28, outline=DEEP, width=3)
            _mini_cache[k] = im
        return _mini_cache[k]

    def flow34(cv, t, shot):
        d = ImageDraw.Draw(cv)
        for k in range(4):
            u = ease_out((t - 0.08 * k) / 0.25)
            if u <= 0:
                continue
            land = 0.5 * k
            bump = 1 + 0.06 * math.sin(math.pi * clamp((t - land - 0.1) / 0.25, 0, 1)) if t > land else 1
            im = mini_img(k)
            if bump != 1 or u < 1:
                sc = bump * lerp(0.7, 1, u)
                im = im.resize((int(MW * sc), int(MH * sc)), Image.BILINEAR)
            x, y = pos[k]
            cv.paste(im, (int(x + MW / 2 - im.width / 2), int(y + MH / 2 - im.height / 2)), im)
            f = font(F_ROUND, 34)
            lab = f"{k + 1} {mini[k][3]}"
            pill(cv, lab, x + 14, y + MH - 70, bg=WHITE, fg=INK, stroke=False, px=30)
        # 虛線箭頭：每 0.5 秒畫一段
        segs = [((520, 710), (560, 710)), ((780, 900), (780, 960)), ((560, 1150), (520, 1150))]
        for i, (a, b) in enumerate(segs):
            u = clamp((t - 0.5 * (i + 1) + 0.3) / 0.3, 0, 1)
            if u <= 0:
                continue
            ex, ey = lerp(a[0], b[0], u), lerp(a[1], b[1], u)
            d.line([a, (ex, ey)], fill=SKY, width=10)
            if u >= 1:
                ang = math.atan2(b[1] - a[1], b[0] - a[0])
                tip = (b[0] + 12 * math.cos(ang), b[1] + 12 * math.sin(ang))
                l = (tip[0] - 30 * math.cos(ang - 0.5), tip[1] - 30 * math.sin(ang - 0.5))
                r = (tip[0] - 30 * math.cos(ang + 0.5), tip[1] - 30 * math.sin(ang + 0.5))
                d.polygon([tip, l, r], fill=SKY, outline=INK)
    hops34 = []
    feet = [(300, 880), (780, 880), (780, 1320), (300, 1320)]
    for k in range(4):
        t0 = 0.5 * k - 0.35 if k else 0
        src_foot = feet[k - 1] if k else (230, 880)
        hops34.append(dict(t0=max(0, t0), t1=0.5 * k + 0.15 if k < 3 else 2.5, kind="anim", name="hop_r" if k in (1,) else "hop_l" if k == 3 else "hop_r",
                           size=260, move=[(0, src_foot[0], src_foot[1], 260), (0.35 if k else 0.01, feet[k][0], feet[k][1], 260)], blend=0))
    S.append(Shot("34", 2.5, [Still(flow34)], headline="四步串著看", hl="串著看", data=False,
                  sub="先看消息，再看錢往哪跑、是誰在做、自己怎麼排",
                  bibi=Bibi(hops34, default="face_laugh"),
                  cues=[(0.0, "blip"), (0.5, "blip"), (1.0, "blip"), (1.5, "blip")]))

    # 35 導覽：踩導覽鈕、再踩「本頁導覽」
    r35 = Rec("S15_mobile", [(0, 0.98), (0.62, 1.60), (1.62, 3.90), (2.0, 4.7)],
              [(0, 585, 640, WIN_M), (1.75, 585, 640, WIN_M), (2.0, 585, 1700, 1000)])
    S.append(Shot("35", 2.0, [r35], headline="看不懂？問比比", hl="問比比", pill_text="導覽", pill_anim=True,
                  sub="每一頁都有導覽，我一步一步帶你看",
                  bibi=Bibi([dict(t0=tap_span(0.62)[0], t1=1.0, kind="tap", contact=0.62, stay=True, size=240, target=src_tap(0, 936, 76)),
                             dict(t0=1.0, t1=tap_span(1.62)[1], kind="tap", contact=1.62, size=240, target=src_tap(0, 640, 232)),
                             ], default="face_nod"),
                  cues=[(0.62, "tap"), (1.62, "tap")]))

    # 36 客服面板（比比・問題小助手）
    r36 = Rec("S16_mobile", [(0, 1.0), (0.6, 1.6), (1.2, 2.6), (2.0, 4.6)],
              [(0, 585, 1966, WIN_M), (0.7, 585, 1966, WIN_M), (1.2, 585, 930, WIN_M)], blur=B_S16)
    S.append(Shot("36", 2.0, [r36], headline="右下角就是我", hl="就是我", pill_text="客服",
                  sub="右下角點我，常見問題馬上看",
                  bibi=Bibi([dict(t0=0, t1=0.6, kind="pointer", tip=src_tap(0, 1000, 2380), size=340),
                             dict(t0=1.2, t1=2.0, kind="peek", name="peek_l", size=360, y=1330, x=0)], default="face_wink"),
                  cues=[(0.6, "tap")]))

    # 37 功能總覽卡（10-11 Andy：不分會員層級，只說每日次數有限）
    rows37 = ["資金輪動・分流樹播放", "熱力圖點擊跳產業鏈", "3D 剖析圖", "ETF 報酬比較", "自訂配息試算", "複利試算表"]

    def plus37(cv, t, shot):
        x0, y0, x1, y1 = 60, 490, 700, 1380
        lay = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        d.rounded_rectangle([0, 0, x1 - x0 - 1, y1 - y0 - 1], 36, fill=WHITE + (245,), outline=DEEP, width=3)
        for i in range(1, 6):
            yy = 40 + i * 140
            d.line([(30, yy - 22), (x1 - x0 - 30, yy - 22)], fill=(220, 228, 238), width=2)
        cv.paste(lay, (x0, y0), lay)
        f = font(F_BOLD, 42)
        dd = ImageDraw.Draw(cv)
        for i, name in enumerate(rows37):
            land = 0.12 + i * 0.25
            u = clamp((t - land) / 0.22, 0, 1)
            if u <= 0:
                continue
            yy = y0 + 40 + i * 140 + 28
            dx = (1 - back_out(u)) * 160
            # 勾勾徽章
            cx, cy = x0 + 62 - dx, yy + 26
            dd.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], fill=LEMON, outline=INK, width=3)
            dd.line([(cx - 12, cy), (cx - 3, cy + 10), (cx + 13, cy - 10)], fill=INK, width=6)
            lay2 = Image.new("RGBA", (560, 70), (0, 0, 0, 0))
            ImageDraw.Draw(lay2).text((0, 0), name, font=f, fill=INK + (int(255 * u),))
            cv.paste(lay2, (int(x0 + 110 - dx), int(yy)), lay2)
    S.append(Shot("37", 2.0, [Still(plus37)], headline="這些功能都能用", hl="都能用", data=False,
                  sub="功能都開放體驗，每日使用次數有限，依網站公告",
                  bibi=Bibi([dict(t0=0, t1=1.37, kind="anim", name="face_wink", size=440, foot=(860, 1360)),
                             dict(t0=1.37, t1=2.0, kind="anim", name="celebrate", size=440, foot=(860, 1360), mode="hold")], default="celebrate"),
                  cues=[(0.12 + 0.25 * i, "blip") for i in range(6)]))

    # 38 願望清單 ＋ 許願牌
    r38 = Rec("S16_mobile", [(0, 8.5), (2.0, 10.7)], [(0, 585, 1150, WIN_M), (2.0, 585, 1230, WIN_M / 1.12)], blur=B_S16,
              rect=(60, 470, 960, 640))
    S.append(Shot("38", 2.0, [r38], headline="歡迎許願", hl="許願", headline_center=True,
                  bibi=Bibi([dict(t0=0, t1=2.0, kind="anim", name="sign_text", size=540, foot=(700, 1480))]),
                  bubble_spec=dict(text="功能持續新增，想要什麼跟我說！", box=(60, 1150, 450, 1370), tail=(470, 1300), t0=0.2, max_chars=8, px=42),
                  bibi_hidden_default=True, cues=[(0.3, "ding")]))

    # 39 片尾：LOGO＋搜尋 哩股哩股＋免費註冊（不放網址、信箱）
    def end39(cv, t, shot):
        sc = lerp(1.0, 1.03, ease_io(t / 3.0))
        px = int(440 * sc)
        lg = logo_sized(px)
        cv.paste(lg, (540 - px // 2, 800 - px // 2), lg)
        u = ease_out((t - 0.3) / 0.3)
        if u > 0:
            pill(cv, "搜尋 哩股哩股", 90, 1095, bg=WHITE, fg=INK, stroke=False, px=44, alpha=u)
            pill(cv, "免費註冊", 560, 1095, bg=LEMON, fg=INK, stroke=False, px=44, alpha=u)
    S.append(Shot("39", 3.0, [Still(end39)], headline="哩股哩股", hl="哩股哩股", headline_center=True, data=False,
                  bibi=Bibi([dict(t0=0, t1=3.0, kind="anim", name="wave", size=440, foot=(800, 1470))]),
                  bubble_spec=dict(text="我們網站見，掰掰～", box=(90, 1250, 560, 1380), tail=(640, 1330), t0=0.3, max_chars=10),
                  bibi_hidden_default=True, cues=[(0, "chord_end")]))

    # 40 法遵警語（≥5 秒；警語不壓動畫）
    S.append(disclaimer_shot("40", 5.5))
    return S


def disclaimer_shot(sid, dur):
    def disc(cv, t, shot):
        a = clamp(t / 0.2, 0, 1)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        lg = logo_sized(150)
        lay.paste(lg, (540 - 75, 250), lg)
        d = ImageDraw.Draw(lay)
        fs = font(F_MED, 30)
        tw = text_w(fs, SPONSOR_NOTE)
        d.text((540 - tw / 2, 440), SPONSOR_NOTE, font=fs, fill=(70, 70, 70))
        d.rounded_rectangle([60, 520, 1020, 1330], 36, fill=WHITE, outline=DEEP, width=3)
        f = font(F_MED, 48)
        y = 580
        for para in DISCLAIMER:
            line = ""
            for ch in para:
                if text_w(f, line + ch) > 860 and line:
                    d.text((110, y), line, font=f, fill=INK)
                    y += 70
                    line = ""
                line += ch
            if line:
                d.text((110, y), line, font=f, fill=INK)
                y += 70
            y += 30
        if a < 1:
            lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a)))
        cv.paste(lay, (0, 0), lay)
    return Shot(sid, dur, [Still(disc)], headline="", data=False, bibi=Bibi(visible=False), cues=[(0, "fade")])


def _persp_coeffs(src_pts, dst_pts):
    """PIL PERSPECTIVE：給輸出四點 → 來源四點，回 8 係數。"""
    A, B = [], []
    for (x, y), (u, v) in zip(src_pts, dst_pts):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    return np.linalg.solve(np.array(A, float), np.array(B, float)).tolist()


def _round_quad_mask(w, h, q, r):
    m = Image.new("L", (w, h), 0)
    xs = [p[0] for p in q]; ys = [p[1] for p in q]
    ImageDraw.Draw(m).rounded_rectangle([min(xs), min(ys), max(xs), max(ys)], max(1, r), fill=255)
    return m


# ───────────────────────── 15 秒短版 ─────────────────────────
def shots_short():
    M = {s.sid: s for s in shots_main()}
    S = []
    WIN_M = 1170
    S.append(Shot("s1", 1.5,
                  [Rec("S08f_mobile", [(0, 1.0), (1.5, 3.0)], [(0, 585, 760, WIN_M / 1.18), (1.5, 585, 740, WIN_M)])],
                  headline="AI 伺服器怎麼拆？", hl="怎麼拆", sub="我是比比，帶你拆開看！",
                  bibi=Bibi([dict(t0=0, t1=0.6, kind="peek", name="peek_l", size=460, y=1420, x=0),
                             dict(t0=0.6, t1=1.5, kind="anim", name="talk_excited", size=HOST_SIZE, foot=HOST)]),
                  cues=[(0, "pop")]))
    r = Rec("S08d_desktop", [(0, 2.43), (0.62, 3.05), (2.0, 4.6)], [(0, 980, 690, 1160), (0.8, 980, 690, 1160), (1.6, 900, 600, 1050)], blur=B_S08D)
    S.append(Shot("s2", 2.0, [r], headline="點零件看環節", hl="環節", pill_text="④ 產業",
                  sub="踩一下零件，馬上知道是哪個環節",
                  bibi=Bibi([dict(t0=tap_span(0.62)[0], t1=tap_span(0.62)[1], kind="tap", contact=0.62, target=src_tap(0, 560, 300)),
                             dict(t0=tap_span(0.62)[1], t1=2.0, kind="anim", name="face_proud", size=HOST_SIZE, foot=HOST)]),
                  cues=[(0.62, "tap")]))
    r = Rec("S04_mobile", [(0, 0.98), (0.62, 1.60), (2.0, 6.0)], [(0, 585, 760, WIN_M), (0.85, 585, 760, WIN_M), (1.35, 585, 1080, 900)])
    S.append(Shot("s3", 2.0, [r], headline="按播放看它轉", hl="播放", pill_text="③ 資金",
                  sub="錢往哪個族群跑，一路播給你看",
                  bibi=Bibi([dict(t0=tap_span(0.62)[0], t1=tap_span(0.62)[1], kind="tap", contact=0.62, target=src_tap(0, 1086, 270)),
                             dict(t0=tap_span(0.62)[1], t1=1.5, kind="anim", name="face_shock", size=HOST_SIZE, foot=HOST),
                             dict(t0=1.5, t1=2.0, kind="anim", name="coins", size=HOST_SIZE, foot=HOST)]),
                  cues=[(0.62, "tap"), (0.7, "rise")]))
    s17 = M["17"]
    S.append(Shot("s4", 1.5, s17.layers, headline="點進產業鏈", hl="產業鏈", pill_text="④ 產業",
                  sub="熱的那一塊，點進去看產業鏈", bibi=s17.bibi, cues=s17.cues))
    r = Rec("S13_mobile", [(0, 0.0), (2.0, 0.65)], [(0, 585, 1970, WIN_M), (2.0, 585, 1990, WIN_M / 1.06)],
            blur=[(0, 980, 1170, 1060), (0, 1170, 1170, 1440), (0, 1600, 190, 2532)])
    S.append(Shot("s5", 2.0, [r], headline="看每月配息落在哪", hl="落在哪", pill_text="⑤ ETF",
                  sub="依歷史配息試算，不代表未來",
                  bibi=Bibi([dict(t0=0, t1=2.0, kind="anim", name="calc", size=HOST_SIZE, foot=HOST)])))
    s04 = M["04"]
    S.append(Shot("s6", 2.0, s04.layers, headline="認識比比", hl="比比", headline_center=True, data=False,
                  bibi=Bibi([dict(t0=0, t1=2.0, kind="anim", name="intro", size=700, mode="hold", foot=(540, 1470), blend=0)]),
                  bubble_spec=dict(text="看不懂就問我！", box=(240, 700, 840, 830), tail=(700, 900), t0=0.5, max_chars=12),
                  bibi_hidden_default=True, cues=s04.cues))
    s37 = M["37"]
    S.append(Shot("s7", 2.0, s37.layers, headline="這些功能都能用", hl="都能用", data=False,
                  sub="功能都開放體驗，每日使用次數有限，依網站公告", bibi=s37.bibi, cues=s37.cues))
    s39 = M["39"]
    S.append(Shot("s8", 2.0, s39.layers, headline="哩股哩股", hl="哩股哩股", headline_center=True, data=False,
                  bibi=Bibi([dict(t0=0, t1=2.0, kind="anim", name="wave", size=440, foot=(800, 1470))]),
                  bubble_spec=dict(text="搜尋「哩股哩股」，網站見！", box=(70, 1240, 580, 1390), tail=(640, 1330), t0=0.2, max_chars=9, px=40),
                  bibi_hidden_default=True, cues=[(0, "chord_end")]))
    S.append(disclaimer_shot("s9", 3.5))
    return S


# ───────────────────────── 輸出 ─────────────────────────
def shot_list(cut):
    return shots_main() if cut == "main" else shots_short()


def timeline(cut):
    t = 0.0
    out = []
    for s in shot_list(cut):
        out.append((s.sid, t, s.dur))
        t += s.dur
    return out


def render_shot(args):
    cut, i, seg_path = args
    shots = shot_list(cut)
    s = shots[i]
    n = int(round(s.dur * FPS))
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", "-pix_fmt", "yuv420p", str(seg_path)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for k in range(n):
        im = s.render(k / FPS)
        p.stdin.write(im.tobytes())
    p.stdin.close()
    p.wait()
    for r in list(_READERS.values()):
        r.close()
    _READERS.clear()
    return s.sid


def cues_json(cut):
    out = []
    t = 0.0
    for s in shot_list(cut):
        for ct, kind in s.cues:
            out.append([round(t + ct, 3), kind])
        t += s.dur
    return {"total": round(t, 3), "cues": out, "shots": [[sid, round(t0, 3), d] for sid, t0, d in timeline(cut)]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cut", choices=["main", "short"], default="main")
    ap.add_argument("--out", default="")
    ap.add_argument("--audio", default="")
    ap.add_argument("--work", default=str(SCR / "v10" / "work"))
    ap.add_argument("--stills", default="")
    ap.add_argument("--still-dir", default=str(SCR / "v10" / "stills"))
    ap.add_argument("--only", default="", help="只重算這幾鏡（逗號分隔 sid）")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--cues", default="")
    ap.add_argument("--cover", default="")
    a = ap.parse_args()

    if a.cues:
        Path(a.cues).write_text(json.dumps(cues_json(a.cut), ensure_ascii=False, indent=1))
        print("cues →", a.cues)
        return

    if a.cover:
        make_cover(a.cover)
        return

    shots = shot_list(a.cut)
    tl = timeline(a.cut)
    if a.stills:
        od = Path(a.still_dir); od.mkdir(parents=True, exist_ok=True)
        for ts in a.stills.split(","):
            T = float(ts)
            for (sid, t0, d), s in zip(tl, shots):
                if t0 <= T < t0 + d:
                    # 依序算到該格（讓比比的平滑轉場狀態正確）
                    k_end = int(round((T - t0) * FPS))
                    im = None
                    for k in range(0, k_end + 1):
                        if k == k_end or k % 3 == 0:
                            im = s.render(k / FPS)
                    im.save(od / f"{a.cut}_{T:06.2f}_{sid}.png")
                    print("抽格", od / f"{a.cut}_{T:06.2f}_{sid}.png")
                    break
        return

    work = Path(a.work) / a.cut
    work.mkdir(parents=True, exist_ok=True)
    only = set(a.only.split(",")) if a.only else None
    jobs = [(a.cut, i, work / f"seg_{s.sid}.mp4") for i, s in enumerate(shots) if (only is None or s.sid in only)]
    from multiprocessing import Pool
    # 長的鏡先跑，平行度較好
    jobs.sort(key=lambda j: -shots[j[1]].dur)
    with Pool(a.jobs) as pool:
        for sid in pool.imap_unordered(render_shot, jobs):
            print("完成鏡", sid, flush=True)
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{work / ('seg_' + s.sid + '.mp4')}'\n" for s in shots))
    if a.out:
        cmd = ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst)]
        if a.audio:
            cmd += ["-i", a.audio]
        cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", "19", "-pix_fmt", "yuv420p", "-r", str(FPS),
                "-profile:v", "high", "-movflags", "+faststart"]
        if a.audio:
            cmd += ["-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-shortest"]
        cmd += [a.out]
        subprocess.check_call(cmd)
        print("輸出", a.out)


def make_cover(path):
    """封面：3D 剖析（桌機第二角度，零件為主）＋比比星星眼＋一句鉤子。"""
    s = [x for x in shots_main() if x.sid == "20"][0]
    cv = background().copy()
    rc = Rec("S08e_desktop", [(0, 4.0)], [(0, 1225, 680, 900)], blur=B_S08D)
    rc.draw(cv, 0, s)
    data_pill(cv, CARD)
    f = font(F_ROUND, 104)
    d = ImageDraw.Draw(cv)
    lines = ["AI 伺服器", "拆開看！"]
    y = 214
    for i, ln in enumerate(lines):
        tw = text_w(f, ln)
        if i == 1:
            d.rounded_rectangle([540 - tw / 2 - 8, y + 86, 540 + tw / 2 + 8, y + 116], 12, fill=LEMON)
        d.text((540 - tw / 2, y), ln, font=f, fill=INK)
        y += 124
    put_sprite(cv, "face_star", 2, (250, 1500), 560)
    pill(cv, "比比帶你逛 5 個功能", 470, 1430, bg=SKY, fg=WHITE, px=40)
    pill(cv, "哩股哩股", 560, 1530, bg=LEMON, fg=INK, stroke=False, px=40)
    cv.save(path)
    print("封面", path)


if __name__ == "__main__":
    main()
