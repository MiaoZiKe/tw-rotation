"""期中選舉行情短片：共用工具（畫布、外框登記、配音時間軸、字幕）。
直式 1080×1920、30fps；cairo 畫圖形、PIL 畫字，逐格算圖。
檢查（每一幀）：
  重疊：所有登記外框（外擴 PAD）兩兩不相交；折線點不得落在文字框內。
  遮擋：每個文字的字形像素（alpha>=0.95）在最終畫面上必須還是原色，被別的東西蓋到就算一筆。
  模糊：每個文字框的拉普拉斯變異量（正規化）必須高於門檻；全片不使用任何模糊濾鏡。
"""
from __future__ import annotations

import json
import math
import os
import re
import wave
from functools import lru_cache
from pathlib import Path

import cairo
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
LIB = REPO / "docs" / "anim" / "bibi_library"
SCR = Path(os.environ.get("MT_SCR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/midterm"))
FD = Path(os.environ.get("MT_FONT_DIR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/font"))
F_BLACK = str(FD / "NotoSansTC-Black.ttf")
F_BOLD = str(FD / "NotoSansTC-Bold.ttf")
F_MED = str(FD / "NotoSansTC-Medium.ttf")
VDIR = HERE / "voice_melo"
SCRIPT = HERE / "melo_script.json"
CHART = HERE / "chart_data"

W, H, FPS = 1080, 1920, 30

BG = (12, 18, 28)
TXT = (240, 244, 248)
MUTED = (150, 166, 186)
DIM = (176, 190, 208)
TEAL = (38, 205, 186)
ORANGE = (255, 160, 64)
UP = (255, 84, 84)        # 紅漲
DOWN = (52, 200, 120)     # 綠跌
CARD = (24, 34, 50)
CARD_EDGE = (10, 15, 24)
GRID = (34, 46, 64)

SAFE_X0, SAFE_X1 = 48, 900      # 文字安全區（右側留給平台按鈕）
PAD = 4


# ───────────────────────── 小工具 ─────────────────────────
@lru_cache(maxsize=128)
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


def lerp(a, b, t):
    return a + (b - a) * t


def ap(t, t0, dur=0.4):
    return ease_out((t - t0) / dur)


def light(c, k):
    return tuple(min(255, int(v + (255 - v) * k)) for v in c)


def dark(c, k):
    return tuple(max(0, int(v * (1 - k))) for v in c)


def rgb(c):
    return (c[0] / 255, c[1] / 255, c[2] / 255)


def tsize(f, s):
    b = f.getbbox(s)
    return b[2] - b[0], b[3] - b[1], b


# ───────────────────────── 外框登記 ─────────────────────────
class Reg:
    def __init__(self):
        self.items = []        # (name, group, box)
        self.polys = []        # (name, [(x,y)...])
        self.issues = []       # 出框、字太小等
        self.texts = []        # 遮擋／模糊檢查用 (name, x0, y0, alpha_mask, color)

    def add(self, name, box, group=None):
        x0, y0, x1, y1 = box
        if x1 - x0 < 1 or y1 - y0 < 1:
            return
        self.items.append((name, group or name, (x0, y0, x1, y1)))

    def poly(self, name, pts, group=None):
        self.polys.append((name, group or name, pts))

    def inside(self, name, box, cbox, inset=0):
        x0, y0, x1, y1 = box
        c0, c1, c2, c3 = cbox
        if x0 < c0 + inset - 0.5 or y0 < c1 + inset - 0.5 or x1 > c2 - inset + 0.5 or y1 > c3 - inset + 0.5:
            self.issues.append(f"{name} 出框 {tuple(int(v) for v in box)} ⊄ {tuple(int(v) for v in cbox)}")

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
                ix = min(ax1, bx1) + PAD - (max(ax0, bx0) - PAD)
                iy = min(ay1, by1) + PAD - (max(ay0, by0) - PAD)
                if ix > 0 and iy > 0:
                    out.append((a[0], b[0], int(ix * iy)))
        # 折線（取樣點）不得落在其他群組的外框內
        for pn, pg, pts in self.polys:
            for (n, g, (x0, y0, x1, y1)) in it:
                if g == pg:
                    continue
                for (px, py) in pts:
                    if x0 - PAD <= px <= x1 + PAD and y0 - PAD <= py <= y1 + PAD:
                        out.append((pn, n, 1))
                        break
        return out


class Canvas:
    """cairo 圖形先畫，文字（PIL）排在圖形之後、比比之前；文字可用左到右的「擦開」進場，不使用透明度淡入。"""

    def __init__(self):
        self.surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
        self.c = cairo.Context(self.surf)
        self.c.set_source_rgb(*rgb(BG))
        self.c.paint()
        self.reg = Reg()
        self.ops = []          # 文字操作

    # ---- 圖形 ----
    def rrect(self, x, y, w, h, r, col, a=1.0):
        c = self.c
        r = min(r, w / 2, h / 2)
        c.new_sub_path()
        c.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        c.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        c.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        c.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
        c.close_path()
        c.set_source_rgba(*rgb(col), a)
        c.fill()

    def rect(self, x, y, w, h, col, a=1.0):
        self.c.set_source_rgba(*rgb(col), a)
        self.c.rectangle(x, y, w, h)
        self.c.fill()

    def line(self, pts, col, lw, a=1.0, dash=None, cap=cairo.LINE_CAP_ROUND):
        c = self.c
        c.set_source_rgba(*rgb(col), a)
        c.set_line_width(lw)
        c.set_line_cap(cap)
        c.set_line_join(cairo.LINE_JOIN_ROUND)
        c.set_dash(dash or [])
        c.move_to(*pts[0])
        for p in pts[1:]:
            c.line_to(*p)
        c.stroke()
        c.set_dash([])

    def poly_fill(self, pts, col, a=1.0):
        c = self.c
        c.set_source_rgba(*rgb(col), a)
        c.move_to(*pts[0])
        for p in pts[1:]:
            c.line_to(*p)
        c.close_path()
        c.fill()

    def circle(self, x, y, r, col, a=1.0, stroke=None, lw=4):
        c = self.c
        c.new_sub_path()
        c.arc(x, y, r, 0, 2 * math.pi)
        if col is not None:
            c.set_source_rgba(*rgb(col), a)
            c.fill_preserve() if stroke else c.fill()
        if stroke:
            c.set_source_rgba(*rgb(stroke), 1)
            c.set_line_width(lw)
            c.stroke()
        c.new_path()

    def card(self, name, x, y, w, h, depth=12, col=CARD, edge=None, grp=None, r=26):
        """2.5D 卡：底下一條較暗的厚度＋上緣亮邊。登記整張卡（含厚度）。"""
        self.rrect(x, y + depth, w, h, r, CARD_EDGE)
        self.rrect(x, y, w, h, r, col)
        if edge:
            self.rrect(x, y, 8, h, 4, edge)
        self.reg.add(name, (x, y, x + w, y + h + depth), grp or name)

    def bar25(self, name, x, y, w, h, col, d=18, grp=None, a=1.0):
        """2.5D 直條：正面＋右側面（較暗）＋頂面（較亮）。(x,y) 是正面左上角；登記含側面與頂面。"""
        if h < 1:
            return
        dx, dy = d, -d * 0.6
        self.rect(x, y, w, h, col, a)
        self.poly_fill([(x + w, y), (x + w + dx, y + dy), (x + w + dx, y + h + dy), (x + w, y + h)], dark(col, 0.38), a)
        self.poly_fill([(x, y), (x + dx, y + dy), (x + w + dx, y + dy), (x + w, y)], light(col, 0.32), a)
        self.reg.add(name, (x, y + dy, x + w + dx, y + h), grp or name)

    def hbar25(self, name, x, y, w, h, col, d=12, grp=None):
        """2.5D 橫條：正面＋頂面＋右端面。(x,y) 是正面左上角。"""
        if w < 1:
            return
        dx, dy = d * 0.7, -d * 0.7
        self.rect(x, y, w, h, col)
        self.poly_fill([(x, y), (x + dx, y + dy), (x + w + dx, y + dy), (x + w, y)], light(col, 0.30))
        self.poly_fill([(x + w, y), (x + w + dx, y + dy), (x + w + dx, y + h + dy), (x + w, y + h)], dark(col, 0.40))
        self.reg.add(name, (x, y + dy, x + w + dx, y + h), grp or name)

    # ---- 文字 ----
    def text(self, name, s, x, y, f, col, p=1.0, grp=None, anchor="l", reg=True, safe=True, slide=14, ref=None, clip_x=None):
        """預設：ink 外框左上角 = (x,y)（anchor r：x 為右緣；c：x 為中心）。
        ref 給定時為「同一行多段」模式：x 是第一個字的原點、y 是 ref 字串 ink 上緣，各段共用基線。
        p<1 時由左到右擦開並由下往上滑入（不使用透明度淡入）。"""
        bb = f.getbbox(s)
        adv = f.getlength(s)
        iw, ih = bb[2] - bb[0], bb[3] - bb[1]
        if ref is not None:
            ox, oy = x, y - f.getbbox(ref)[1]
            ink_x0 = ox + bb[0]
        else:
            if anchor == "r":
                x = x - iw
            elif anchor == "c":
                x = x - iw / 2
            ox, oy = x - bb[0], y - bb[1]
            ink_x0 = x
        if p <= 0:
            return (ink_x0, y, ink_x0, y + ih)
        sl = (1 - ease_out(p)) * slide if p < 1 else 0.0
        vis = iw
        if False:
            # 只露出完整的字（不切半個字）
            best = 0
            for i in range(1, len(s) + 1):
                a_ = f.getlength(s[:i]) - bb[0]
                if a_ <= vis:
                    best = int(math.ceil(a_))
                else:
                    break
            vis = best
            if vis <= 0:
                return (ink_x0, y, ink_x0, y + ih)
        self.ops.append([name, s, ox, oy + sl, f, col, vis, bb, vis >= iw and p >= 1])
        ink_y0 = oy + sl + bb[1]
        box = (ink_x0, ink_y0, ink_x0 + vis, ink_y0 + ih)
        if reg:
            self.reg.add(name, box, grp or name)
            if safe:
                self.reg.inside(name, box, (0, 0, SAFE_X1 + 20, H), inset=0)
                if ink_x0 < SAFE_X0 - 1:
                    self.reg.issues.append(f"{name} 超出左安全邊 x={ink_x0:.0f}")
            if f.size < 28 and p >= 1:
                self.reg.issues.append(f"{name} 字級 {f.size} < 28")
        return (ink_x0, ink_y0, ink_x0 + iw, ink_y0 + ih)

    def finish(self, bibi_fn=None):
        self.surf.flush()
        arr = np.ndarray((H, self.surf.get_stride() // 4, 4), np.uint8, self.surf.get_data())[:, :W]
        cv = Image.fromarray(np.ascontiguousarray(arr[..., [2, 1, 0]]), "RGB").convert("RGBA")
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        recs = []
        for (name, s, ox, oy, f, col, vis, bb, full) in self.ops:
            tw_, th_ = int(bb[2]) + 9, int(bb[3]) + 9
            tmp = Image.new("RGBA", (tw_, th_), (0, 0, 0, 0))
            ImageDraw.Draw(tmp).text((4, 4), s, font=f, fill=tuple(col) + (255,))
            if not full:
                tmp = tmp.crop((0, 0, min(tw_, 4 + int(bb[0]) + vis + 1), th_))
            ix, iy = int(round(ox)) - 4, int(round(oy)) - 4
            if ix < 0 or iy < 0:
                self.reg.issues.append(f"{name} 畫在畫面外 ({ix},{iy})")
                continue
            ov.alpha_composite(tmp, (ix, iy))
            if full:
                recs.append((name, ix, iy, np.array(tmp)[..., 3], col))
        cv.alpha_composite(ov)
        if bibi_fn:
            bibi_fn(cv, self.reg)
        self.final = cv
        self.recs = recs
        return cv

    def checks(self):
        """回傳 (遮擋筆數, 模糊筆數, 明細)。"""
        arr = np.array(self.final.convert("RGB")).astype(np.int16)
        occ, blur, det = 0, 0, []
        gray = (arr[..., 0] * 0.299 + arr[..., 1] * 0.587 + arr[..., 2] * 0.114)
        for (name, ix, iy, am, col) in self.recs:
            h, w = am.shape
            reg_ = arr[iy:iy + h, ix:ix + w]
            if reg_.shape[:2] != am.shape:
                continue
            m = am >= 242
            if m.sum() == 0:
                continue
            diff = np.abs(reg_ - np.array(col, np.int16)).max(axis=2)
            bad = int(((diff > 24) & m).sum())
            if bad > 0:
                occ += 1
                det.append(f"遮擋 {name} {bad}px")
            # 模糊／疊影：用文字自己的遮罩重算「應有的畫面」（背景取框內無字處的中位數），
            # 與實際畫面逐像素比較；文字邊緣若被模糊、疊影、縮放內插，差異像素比例會升高。
            from scipy.ndimage import binary_dilation
            a = am.astype(np.float32)[..., None] / 255.0
            m0 = am > 0
            near = binary_dilation(m0, iterations=2)
            far = binary_dilation(m0, iterations=6) & ~binary_dilation(m0, iterations=4)
            if far.sum() < 10 or float(reg_[far].std(axis=0).max()) > 12:
                continue            # 周圍背景不單純（貼著別的東西）就不在這裡判斷
            bgc = np.median(reg_[far], axis=0)
            expected = bgc * (1 - a) + np.array(col, np.float32) * a
            d2 = np.abs(reg_.astype(np.float32) - expected).max(axis=2)
            frac = float((d2[near] > 40).mean())
            score = frac
            if score > BLUR_MAX:
                blur += 1
                det.append(f"模糊 {name} 差異像素 {frac:.4f}")
        return occ, blur, det


BLUR_MAX = 0.012   # 文字框內與預期不符的像素比例上限


# ───────────────────────── 配音時間軸 ─────────────────────────
def char_w(ch):
    if ch in "。！？：；":
        return 1.4
    if ch in "，、":
        return 0.9
    if ch == " ":
        return 0.08
    if ch.isascii() and ch.isalpha():
        return 0.55
    if ch.isdigit():
        return 0.7
    return 1.0


def wav_info(p):
    with wave.open(str(p)) as w:
        sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
        a = np.frombuffer(w.readframes(n), np.int16).astype(np.float32) / 32768
    a = a.reshape(-1, ch).mean(axis=1)
    hop = int(sr * 0.01)
    k = len(a) // hop
    rms = np.sqrt((a[:k * hop].reshape(k, hop) ** 2).mean(axis=1) + 1e-12)
    db = 20 * np.log10(rms / (rms.max() + 1e-12))
    on = np.nonzero(db > -38)[0]
    return sr, a, (on[0] * 0.01 if len(on) else 0.0), ((on[-1] + 1) * 0.01 if len(on) else len(a) / sr)


def pauses(a, sr, on, off):
    hop = int(sr * 0.01)
    k = len(a) // hop
    rms = np.sqrt((a[:k * hop].reshape(k, hop) ** 2).mean(axis=1) + 1e-12)
    sil = 20 * np.log10(rms / (rms.max() + 1e-12)) < -35
    out, i = [], 0
    while i < k:
        if sil[i]:
            j = i
            while j < k and sil[j]:
                j += 1
            if j - i >= 6 and i * 0.01 > on + 0.05 and j * 0.01 < off - 0.05:
                out.append((i * 0.01, j * 0.01))
            i = j
        else:
            i += 1
    return out


class Line:
    """一句配音。MeloTTS 沒有逐字時間：用字數比例（標點算停頓）估每字時間，
    再把音檔偵測到的句內停頓對到最近的標點當校正點（分段線性內插）。"""

    def __init__(self, lid, text):
        self.id = lid
        self.text = text
        self.sr, self.audio, self.on, self.off = wav_info(VDIR / f"{lid}.wav")
        self.speech = self.off - self.on
        self.start = 0.0
        hop = int(self.sr * 0.01)
        kk = len(self.audio) // hop
        self.env = np.sqrt((self.audio[:kk * hop].reshape(kk, hop) ** 2).mean(axis=1) + 1e-12)
        cw = [char_w(c) for c in text]
        tot = sum(cw)
        acc, self.cum = 0.0, []
        for c in cw:
            self.cum.append(acc / tot)
            acc += c
        self.cum.append(1.0)
        knots = [(0.0, 0.0)]
        self.pause_marks = []      # (標點索引, 偵測到的停頓結束時間 相對起點)
        punct = [k for k, ch in enumerate(text[:-1]) if ch in "，。！？：；、"]
        last = -1
        for (g0, g1) in pauses(self.audio, self.sr, self.on, self.off):
            mid = (g0 + g1) / 2 - self.on
            best = None
            for k in punct:
                if k <= last:
                    continue
                d = abs(self.cum[k] * self.speech - mid)
                if best is None or d < best[0]:
                    best = (d, k)
            if best and best[0] < 1.3:
                k = best[1]
                if self.cum[k] > knots[-1][0] and g0 - self.on > knots[-1][1]:
                    knots += [(self.cum[k], g0 - self.on), (self.cum[k + 1], g1 - self.on)]
                    self.pause_marks.append((k, g1 - self.on))
                    last = k
        knots.append((1.0, self.speech))
        self.kf = np.array([x[0] for x in knots])
        self.kt = np.array([x[1] for x in knots])

    @property
    def end(self):
        return self.start + self.speech

    def frac_t(self, k):
        return self.start + float(np.interp(self.cum[min(k, len(self.cum) - 1)], self.kf, self.kt))

    def snap(self, t_abs, win=0.12):
        """把估計時間吸到前後 win 秒內能量最低（音節縫隙）的位置；回傳 (新時間, 位移)。"""
        c = int(round((t_abs - self.start + self.on) / 0.01))
        a, b = max(0, c - int(win / 0.01)), min(len(self.env), c + int(win / 0.01) + 1)
        if b - a < 3:
            return t_abs, 0.0
        k = a + int(np.argmin(self.env[a:b]))
        new = self.start + k * 0.01 - self.on
        return new, new - t_abs

    def at(self, anchor, nth=0):
        if not anchor:
            return self.start
        k = -1
        for _ in range(nth + 1):
            k = self.text.find(anchor, k + 1)
        if k < 0:
            raise KeyError(f"{self.id} 找不到錨點「{anchor}」")
        return self.frac_t(k)


def ts(x):
    ms = int(round(x * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
