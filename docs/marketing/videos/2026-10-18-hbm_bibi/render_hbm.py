"""短影音「AI 晶片為什麼需要 HBM？」渲染器（直式 1080×1920、30fps、cairo＋PIL 逐格算圖＋ffmpeg，不掉格）。

Andy 2026-10-18 規則（docs/marketing/videos/video_rules_1018.md）：
  · 比比是小助手、不說話、不出對話泡泡；畫面占比小（左下角約 180px 寬），內容優先。
  · 圖表 2.5D（等角／斜視角、有厚度、上亮側暗的光影、柔和陰影與光暈），用 cairo 畫（有反鋸齒、漸層）。
  · 自製圖表不加外框，直接畫在深色背景上（參考範例片 reference_cowos_short/analysis.md）。
  · 一段一張圖、圖跟著配音逐步長出來；一句一張字幕卡；上方進度條；頁腳固定「非投資建議＋數字說明」。
  · 配音 MeloTTS（voice_melo/S01.wav…），時間軸由配音長度決定；MeloTTS 沒有逐字時間，
    句內的字幕切換與「講到某個詞時圖長出來」用字數比例推算（標點算停頓）。

版面（由上到下，彼此不相交；每幀登記外框做兩兩重疊檢查，layout_rules.md）：
  品牌膠囊／頁碼 60–118 ｜ 進度條 140–150 ｜ 大字 172–262 ｜ 副標 282–326
  圖解區 372–1410（不加框）｜ 比比（左，x 20–310）＋字幕卡（右，x 330–1040）1440–1700 ｜ 頁腳 1716–1790

用法（repo 根目錄）：
    python docs/marketing/videos/2026-10-18-hbm_bibi/render_hbm.py               # 出片＋overlap_report.md＋srt
    python docs/marketing/videos/2026-10-18-hbm_bibi/render_hbm.py --frames 3,12.5  # 只輸出這幾秒的單格
    python docs/marketing/videos/2026-10-18-hbm_bibi/render_hbm.py --cover          # 封面
環境變數 HBM_SCR：中間產物（抽格、配樂、混音）所在的 scratchpad；HBM_FONT_DIR：字型資料夾。
"""
from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import os
import re
import subprocess
import sys
import wave
from functools import lru_cache
from pathlib import Path

import cairo
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
LIB = REPO / "docs" / "anim" / "bibi_library"
SCR = Path(os.environ.get("HBM_SCR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/hbm"))
FD = Path(os.environ.get("HBM_FONT_DIR", "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/font"))
F_ROUND = str(FD / "jf-openhuninn-2.1.ttf")        # 粉圓（OFL）
F_BOLD = str(FD / "NotoSansTC-Bold.ttf")
F_BLACK = str(FD / "NotoSansTC-Black.ttf")
F_MED = str(FD / "NotoSansTC-Medium.ttf")
VDIR = Path(os.environ.get("HBM_VDIR", str(HERE / "voice_melo")))
SCRIPT = HERE / "melo_script.json"
OUT_BASE = "hbm_bibi_9x16"

W, H, FPS = 1080, 1920, 30

# 配色（深色底，參考範例片：深藍黑＋青綠＋橘＋紫）
BG_TOP = (9, 16, 26)
BG_BOT = (6, 11, 18)
TXT = (240, 244, 248)
MUTED = (150, 166, 186)
DIM = (110, 124, 142)
TEAL = (38, 205, 186)
ORANGE = (255, 146, 64)
PURPLE = (132, 98, 246)
BLUE = (64, 140, 255)
RED = (255, 92, 92)
GOLD = (246, 196, 72)
SLATE = (92, 108, 132)
CHIP = (44, 52, 66)
GREEN = (52, 199, 120)

G = (40, 372, 1040, 1410)          # 圖解區
CARD = (330, 1462, 1040, 1676)     # 字幕卡
BIBI_SIZE = 300
BIBI_FOOT = (152, 1690)
FOOT_Y = 1716
PAD = 6


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


def back_out(x, s=1.7):
    x = clamp(x) - 1
    return x * x * ((s + 1) * x + s) + 1


def lerp(a, b, t):
    return a + (b - a) * t


def ap(t, t0, dur=0.45):
    """t0 起 dur 秒內 0→1（ease_out）。"""
    return ease_out((t - t0) / dur)


def tsize(f, s):
    b = f.getbbox(s)
    return b[2] - b[0], b[3] - b[1], b


def light(c, k):
    return tuple(min(255, int(v + (255 - v) * k)) for v in c)


def dark(c, k):
    return tuple(max(0, int(v * (1 - k))) for v in c)


# ───────────────────────── 外框登記（重疊檢查） ─────────────────────────
class Reg:
    def __init__(self):
        self.items = []
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
            self.text_issues.append(f"{name} 出框 {tuple(int(v) for v in tbox)} ⊄ {tuple(int(v) for v in cbox)}")

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
        return out


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
    """句內停頓（< -35 dB 連續 ≥ 0.08 秒），回傳 [(起, 訖)]（秒，相對音檔開頭）。"""
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
            if j - i >= 8 and i * 0.01 > on + 0.05 and j * 0.01 < off - 0.05:
                out.append((i * 0.01, j * 0.01))
            i = j
        else:
            i += 1
    return out


class Line:
    """一句配音。MeloTTS 沒有逐字時間：先用字數比例（標點算停頓）估每個字的時間，
    再把音檔裡偵測到的句內停頓對到最近的標點，當成校正點（分段線性內插）。"""

    def __init__(self, lid, text):
        self.id = lid
        self.text = text
        p = VDIR / f"{lid}.wav"
        self.sr, self.audio, self.on, self.off = wav_info(p)
        self.speech = self.off - self.on
        self.start = 0.0
        cw = [char_w(c) for c in text]
        tot = sum(cw)
        acc, self.cum = 0.0, []
        for c in cw:
            self.cum.append(acc / tot)
            acc += c
        self.cum.append(1.0)
        knots = [(0.0, 0.0)]
        punct = [k for k, ch in enumerate(text[:-1]) if ch in "，。！？：；、"]
        last = -1
        for (g0, g1) in pauses(self.audio, self.sr, self.on, self.off):
            mid = (g0 + g1) / 2 - self.on
            best = None
            for k in punct:
                if k <= last:
                    continue
                est = self.cum[k] * self.speech
                d = abs(est - mid)
                if best is None or d < best[0]:
                    best = (d, k)
            if best and best[0] < 1.3:
                k = best[1]
                if self.cum[k] > knots[-1][0] and g0 - self.on > knots[-1][1]:
                    knots += [(self.cum[k], g0 - self.on), (self.cum[k + 1], g1 - self.on)]
                    last = k
        knots.append((1.0, self.speech))
        self.kf = np.array([x[0] for x in knots])
        self.kt = np.array([x[1] for x in knots])

    @property
    def end(self):
        return self.start + self.speech

    def frac_t(self, k):
        return self.start + float(np.interp(self.cum[min(k, len(self.cum) - 1)], self.kf, self.kt))

    def at(self, anchor, nth=0):
        if not anchor:
            return self.start
        k = -1
        for _ in range(nth + 1):
            k = self.text.find(anchor, k + 1)
        if k < 0:
            raise KeyError(f"{self.id} 找不到錨點「{anchor}」")
        return self.frac_t(k)


DISP = [("一千零二十四位元", " 1024 位元"), ("兩千零四十八位元", " 2048 位元"), ("二零一三年", " 2013 年"),
        ("二零二四年", " 2024 年"), ("二零二五年", " 2025 年"), ("每秒一百二十八 GB", "每秒 128 GB"),
        ("每秒一點二 TB", "每秒 1.2 TB"), ("九倍", " 9 倍"), ("搜尋哩股哩股", "搜尋「哩股哩股」")]


def chunks_of(ln):
    """字幕：依標點切；太短（< 5 字）的往後併（不往前黏），每張 ≤ 22 字。"""
    parts = [(m.group(0), m.start()) for m in re.finditer(r"[^，。！？：；]+[，。！？：；]?", ln.text)]
    merged, carry = [], None
    for s, k in parts:
        if carry:
            if len(carry[0]) + len(s) <= 24:
                s, k = carry[0] + s, carry[1]
            else:
                merged.append(carry)
            carry = None
        core = s.strip("，。！？：； ")
        if len(core) < 5 and s[-1:] in "；。！？" and merged and len(merged[-1][0]) + len(s) <= 24:
            merged[-1] = (merged[-1][0] + s, merged[-1][1])      # 句尾的短句併回前一張
            continue
        if len(core) < 5 and len(s) < 22 and (s, k) != parts[-1]:
            carry = (s, k)
            continue
        merged.append((s, k))
    if carry:
        if merged:
            merged[-1] = (merged[-1][0] + carry[0], merged[-1][1])
        else:
            merged.append(carry)
    out = []
    for i, (s, k) in enumerate(merged):
        t0 = ln.frac_t(k)
        t1 = ln.frac_t(merged[i + 1][1]) if i + 1 < len(merged) else ln.end
        d = s.strip()
        if not d.endswith(("？", "！")):
            d = d.rstrip("，。、：；")
        for a, b in DISP:
            d = d.replace(a, b)
        d = re.sub(r" {2,}", " ", d).strip()
        out.append((d, t0, t1))
    return out


SCENES = [
    # (句子, 大字, 大字重點色字, 副標, 頁腳第二行)
    ("S01", "AI 晶片的瓶頸在哪？", "瓶頸", "運算單元 vs 記憶體頻寬", "示意圖，非實際比例"),
    ("S02", "HBM 是什麼？", "HBM", "High Bandwidth Memory・高頻寬記憶體", "示意圖：堆疊結構簡化，非實際比例"),
    ("S03", "記憶體牆", "記憶體牆", "頻寬跟不上，GPU 只能閒置等待", "示意圖：資料流與閒置為概念說明"),
    ("S04", "HBM vs GDDR／DDR", "HBM", "用超寬介面換取頻寬", "介面寬度：JEDEC 標準；其餘為相對比較"),
    ("S05", "HBM 規格演進", "規格演進", "單疊（stack）頻寬", "資料：JEDEC 標準、記憶體廠新聞稿；HBM4 為標準值"),
    ("S06", "應用場景", "應用", "AI 加速器・資料中心・HPC", "示意圖"),
    ("S07", "HBM 供應鏈分工", "供應鏈", "堆疊 → 基底晶片 → 先進封裝 → 測試", "依公開報導整理環節分工；列名不代表推薦"),
    ("S08", "HBM 的四項挑戰", "挑戰", "良率・成本・產能・散熱", "示意圖；不放良率、價格等數字"),
    ("S09", "重點總結", "總結", "以垂直堆疊與超寬介面換取頻寬", "示意圖"),
    ("S10", "下一集預告", "預告", "2.5D 先進封裝如何整合 HBM 與 GPU", "資料來源與查證說明見貼文"),
]
FOOT1 = "非投資建議｜數字為公開規格或推估"
DISCLAIMER = "本內容為公開資料整理，不構成任何投資建議；投資有風險，請自行判斷。"
T0, GAP = 0.6, 0.55
END_HOLD = 3.8

ACTS = {
    "S01": [("", "face_think_v2"), ("記憶體頻寬", "point_r_v2"), ("HBM", "face_thinking_bulb")],
    "S02": [("", "face_nod_v2"), ("垂直堆疊", "magnifier"), ("GPU", "point_ur_v2")],
    "S03": [("", "face_think_v2"), ("閒置", "face_sweat")],
    "S04": [("", "point_r_v2"), ("代價", "face_sweat")],
    "S05": [("", "point_ur_v2"), ("九倍", "wow"), ("HBM4", "surprise_jump")],
    "S06": [("", "face_nod_v2"), ("這些場景", "face_thumbs")],
    "S07": [("", "point_r_v2"), ("最後", "face_thinking_bulb"), ("封測廠", "face_nod_v2")],
    "S08": [("", "face_sweat"), ("高密度", "face_shock")],
    "S09": [("", "face_thinking_bulb"), ("關鍵元件", "face_thumbs")],
    "S10": [("", "invite_nod"), ("搜尋", "point_r_v2")],
}
ALT = {"wave": "face_nod_v2", "face_shock": "face_nod_v2", "face_nod_v2": "point_r_v2", "magnifier": "face_nod_v2",
       "point_ur_v2": "face_nod_v2", "face_think_v2": "face_nod_v2", "face_sweat": "face_nod_v2",
       "point_r_v2": "face_nod_v2", "wow": "face_nod_v2", "surprise_jump": "face_nod_v2", "face_thumbs": "face_nod_v2",
       "face_thinking_bulb": "face_nod_v2", "invite_nod": "face_nod_v2", "face_bow": "wave"}

LINES: dict[str, Line] = {}
SCENE_T: list[tuple] = []
SUBS: list[tuple] = []
ACT_TL: list[tuple] = []
TOTAL = 0.0
END_T = 0.0


def build_timeline():
    global TOTAL, END_T
    spec = json.loads(SCRIPT.read_text(encoding="utf-8"))
    texts = {x["id"]: x["text"] for x in spec["lines"]}
    t = T0
    for i, sc in enumerate(SCENES):
        ln = Line(sc[0], texts[sc[0]])
        LINES[sc[0]] = ln
        if i:
            t += GAP
        ln.start = t
        t = ln.end
    END_T = LINES["S10"].end + 0.45
    TOTAL = round((END_T + END_HOLD) * FPS) / FPS
    for i, sc in enumerate(SCENES):
        s0 = 0.0 if i == 0 else LINES[sc[0]].start - 0.3
        s1 = LINES[SCENES[i + 1][0]].start - 0.3 if i + 1 < len(SCENES) else TOTAL
        SCENE_T.append((sc, s0, s1))
        for c in chunks_of(LINES[sc[0]]):
            SUBS.append((c[0], c[1], c[2], sc[0]))
    raw = []
    for sc in SCENES:
        ln = LINES[sc[0]]
        for anchor, name in ACTS[sc[0]]:
            raw.append((0.0 if (sc[0] == "S01" and not anchor) else ln.at(anchor), name))
    raw.append((END_T, "face_bow"))
    raw.sort()
    segs = []
    for i, (st, name) in enumerate(raw):
        en = raw[i + 1][0] if i + 1 < len(raw) else TOTAL
        segs.append((st, en, name))
    for (a, b, n) in segs:
        s0 = a
        while b - a > 3.0:
            m = a + min(2.6, (b - a) / 2)
            ACT_TL.append((a, m, n, s0))
            a, n, s0 = m, ALT.get(n, "face_nod_v2"), m
        ACT_TL.append((a, b, n, s0))


def bibi_at(t):
    for a, b, n, s0 in ACT_TL:
        if a <= t < b:
            return n, t - s0
    a, b, n, s0 = ACT_TL[-1]
    return n, t - s0


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
        fr.append(im.convert("RGBA").resize((BIBI_SIZE, BIBI_SIZE), Image.LANCZOS))
    return fr


@lru_cache(maxsize=None)
def bibi_bbox(name, i):
    a = np.array(bibi_frames(name)[i])[..., 3]
    ys, xs = np.nonzero(a > 24)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def draw_bibi(cv, reg, name, t):
    fr = bibi_frames(name)
    n = len(fr)
    L = lib_lengths().get(name, (n, 1.0))[1]
    i = int((t % L) / L * n) % n
    s = BIBI_SIZE / 512
    ox, oy = int(round(BIBI_FOOT[0] - 248 * s)), int(round(BIBI_FOOT[1] - 482 * s))
    cv.alpha_composite(fr[i], (ox, oy))
    b = bibi_bbox(name, i)
    reg.add("比比", (ox + b[0], oy + b[1], ox + b[2], oy + b[3]))


# ───────────────────────── 2.5D 繪圖（cairo） ─────────────────────────
class Proj:
    """iso：等角（x 往右下、y 往左下）；obl：斜視（x 往右、y 往右上縱深、z 往上）。"""

    def __init__(self, kind, ox, oy, s=1.0):
        self.kind, self.ox, self.oy, self.s = kind, ox, oy, s

    def __call__(self, x, y, z=0.0):
        s = self.s
        if self.kind == "iso":
            return self.ox + (x - y) * 0.866 * s, self.oy + (x + y) * 0.5 * s - z * s
        return self.ox + (x + y * 0.55) * s, self.oy + (-z - y * 0.42) * s


class Ctx:
    """包住 cairo context：記錄圖解實際畫到的範圍（重疊檢查用），並提供 2.5D 元件。"""

    def __init__(self, c, dy=0.0):
        self.c = c
        self.ext = None
        self.dy = dy          # 整張圖解的緩慢上下漂浮（避免停格），cairo 端用 translate 套用

    def track(self, pts, raw=False):
        xs = [p[0] for p in pts]
        ys = [p[1] + (0 if raw else self.dy) for p in pts]
        b = (min(xs), min(ys), max(xs), max(ys))
        e = self.ext
        self.ext = b if e is None else (min(e[0], b[0]), min(e[1], b[1]), max(e[2], b[2]), max(e[3], b[3]))

    def poly(self, pts, rgba=None, src=None, stroke=None, lw=1.5, track=True):
        c = self.c
        c.new_path()
        c.move_to(*pts[0])
        for p in pts[1:]:
            c.line_to(*p)
        c.close_path()
        if src is not None:
            c.set_source(src)
            c.fill_preserve()
        elif rgba is not None:
            c.set_source_rgba(*rgba)
            c.fill_preserve()
        if stroke is not None:
            c.set_source_rgba(*stroke)
            c.set_line_width(lw)
            c.stroke()
        c.new_path()
        if track:
            self.track(pts)

    def line(self, pts, rgba, lw=2.0, dash=None, cap=cairo.LINE_CAP_ROUND, track=True):
        c = self.c
        c.new_path()
        c.move_to(*pts[0])
        for p in pts[1:]:
            c.line_to(*p)
        c.set_source_rgba(*rgba)
        c.set_line_width(lw)
        c.set_line_cap(cap)
        c.set_line_join(cairo.LINE_JOIN_ROUND)
        if dash:
            c.set_dash(dash)
        c.stroke()
        c.set_dash([])
        if track:
            self.track(pts)

    def glow(self, x, y, r, col, a):
        if a <= 0:
            return
        g = cairo.RadialGradient(x, y, 0, x, y, r)
        g.add_color_stop_rgba(0, *rgb(col), a)
        g.add_color_stop_rgba(0.45, *rgb(col), a * 0.35)
        g.add_color_stop_rgba(1, *rgb(col), 0)
        self.c.set_source(g)
        self.c.arc(x, y, r, 0, 2 * math.pi)
        self.c.fill()

    def lin(self, p0, p1, stops):
        g = cairo.LinearGradient(p0[0], p0[1], p1[0], p1[1])
        for k, col, a in stops:
            g.add_color_stop_rgba(k, *rgb(col), a)
        return g

    def shadow(self, pr, x, y, w, d, z=0.0, a=0.45, spread=26, n=6):
        for k in range(n, 0, -1):
            e = spread * k / n
            pts = [pr(x - e, y - e, z), pr(x + w + e, y - e, z), pr(x + w + e, y + d + e, z), pr(x - e, y + d + e, z)]
            self.poly(pts, (0, 0, 0, a / n * 0.9), track=False)

    def box(self, pr, x, y, z, w, d, h, col, a=1.0, edge=0.38, top_col=None, sheen=True):
        if a <= 0:
            return
        T = [pr(x, y, z + h), pr(x + w, y, z + h), pr(x + w, y + d, z + h), pr(x, y + d, z + h)]
        R = [pr(x + w, y, z), pr(x + w, y + d, z), pr(x + w, y + d, z + h), pr(x + w, y, z + h)]
        if pr.kind == "iso":
            F = [pr(x, y + d, z), pr(x + w, y + d, z), pr(x + w, y + d, z + h), pr(x, y + d, z + h)]
        else:
            F = [pr(x, y, z), pr(x + w, y, z), pr(x + w, y, z + h), pr(x, y, z + h)]
        tc = top_col or light(col, 0.30)
        # 正面：上亮下暗的漸層
        fg = self.lin(F[3], F[0], [(0, light(col, 0.06), a), (1, dark(col, 0.22), a)])
        self.poly(F, src=fg)
        rg = self.lin(R[3], R[0], [(0, dark(col, 0.30), a), (1, dark(col, 0.48), a)])
        self.poly(R, src=rg)
        if sheen:
            tg = self.lin(T[0], T[2], [(0, light(tc, 0.18), a), (0.55, tc, a), (1, dark(tc, 0.08), a)])
            self.poly(T, src=tg)
        else:
            self.poly(T, (*rgb(tc), a))
        if edge > 0:
            self.line([T[3], T[0], T[1]] if pr.kind == "iso" else [T[0], T[1], T[2]], (1, 1, 1, edge * a), 1.6, track=False)
            self.line([F[2], F[3]] if pr.kind == "iso" else [T[0], F[3]] , (1, 1, 1, edge * 0.6 * a), 1.2, track=False)
            self.line([T[1], T[2], T[3], T[0]] if pr.kind == "iso" else [T[1], R[0]], (1, 1, 1, edge * 0.5 * a), 1.1, track=False)
        return T, F, R

    def cyl(self, pr, cx, cy, z, r, h, col, a=1.0, top_col=None):
        """等角圓柱（硬幣、晶圓）。"""
        if a <= 0:
            return
        c = self.c
        px, py = pr(cx, cy, z)
        _, pyt = pr(cx, cy, z + h)
        s = pr.s
        R, ry = r * 1.2247 * s, r * 0.7071 * s
        self.track([(px - R, pyt - ry), (px + R, py + ry)])
        # 側面
        c.save()
        c.new_path()
        c.move_to(px - R, pyt)
        c.line_to(px - R, py)
        c.save(); c.translate(px, py); c.scale(1, ry / R); c.arc_negative(0, 0, R, math.pi, 0); c.restore()
        c.line_to(px + R, pyt)
        c.close_path()
        g = cairo.LinearGradient(px - R, 0, px + R, 0)
        g.add_color_stop_rgba(0, *rgb(dark(col, 0.05)), a)
        g.add_color_stop_rgba(0.5, *rgb(dark(col, 0.25)), a)
        g.add_color_stop_rgba(1, *rgb(dark(col, 0.5)), a)
        c.set_source(g)
        c.fill()
        # 頂面
        c.new_path()
        c.save(); c.translate(px, pyt); c.scale(1, ry / R); c.arc(0, 0, R, 0, 2 * math.pi); c.restore()
        tc = top_col or light(col, 0.3)
        g = cairo.LinearGradient(px - R, pyt - ry, px + R, pyt + ry)
        g.add_color_stop_rgba(0, *rgb(light(tc, 0.25)), a)
        g.add_color_stop_rgba(1, *rgb(tc), a)
        c.set_source(g)
        c.fill_preserve()
        c.set_source_rgba(1, 1, 1, 0.35 * a)
        c.set_line_width(1.4)
        c.stroke()
        c.restore()
        return px, pyt, R, ry

    def top_text(self, pr, x, y, z, w, d, s, size, col, a=1.0, family="Inter", weight=cairo.FONT_WEIGHT_BOLD):
        """英文字貼在等角盒子的頂面上（字跟著頂面傾斜，2.5D）。"""
        if a <= 0:
            return
        c = self.c
        c.save()
        o = pr(x, y, z)
        ex = pr(x + 1, y, z)
        ey = pr(x, y + 1, z)
        # 頂面座標系：u 沿 x 軸、v 沿 y 軸
        c.transform(cairo.Matrix(ex[0] - o[0], ex[1] - o[1], ey[0] - o[0], ey[1] - o[1], o[0], o[1]))
        c.select_font_face(family, cairo.FONT_SLANT_NORMAL, weight)
        c.set_font_size(size)
        xb, yb, tw, th, _, _ = c.text_extents(s)
        # 字沿 u（x 軸）方向寫；置中在頂面
        c.move_to(w / 2 - tw / 2 - xb, d / 2 + th / 2)
        c.set_source_rgba(*rgb(col), a)
        c.show_text(s)
        c.restore()


def rgb(c):
    return c[0] / 255, c[1] / 255, c[2] / 255


def rgba(c, a):
    return c[0] / 255, c[1] / 255, c[2] / 255, a


# ───────────────────────── 文字標籤（PIL，畫在 cairo 圖上面） ─────────────────────────
class Labels:
    def __init__(self):
        self.items = []

    def add(self, s, x, y, f, col, a=1.0, anchor="la", bg=None, pad=(18, 10), r=16):
        if a > 0.01:
            self.items.append((s, x, y, f, col, a, anchor, bg, pad, r))

    def box_of(self, it):
        s, x, y, f, col, a, anchor, bg, pad, r = it
        tw, th, bb = tsize(f, s)
        if anchor[0] == "m":
            x -= tw / 2
        elif anchor[0] == "r":
            x -= tw
        if anchor[1] == "m":
            y -= th / 2
        elif anchor[1] == "b":
            y -= th
        return x, y, tw, th, bb

    def draw(self, ov, reg, ctx, cname="圖解字"):
        d = ImageDraw.Draw(ov, "RGBA")
        drawn = []
        for it in self.items:
            s, _x, _y, f, col, a, anchor, bg, pad, r = it
            x, y, tw, th, bb = self.box_of(it)
            y += ctx.dy
            box = (x, y, x + tw, y + th)
            if bg is not None:
                px, py = pad
                bc = bg if len(bg) == 4 else bg + (235,)
                d.rounded_rectangle([x - px, y - py, x + tw + px, y + th + py], r, fill=bc[:3] + (int(bc[3] * a),))
                box = (x - px, y - py, x + tw + px, y + th + py)
            d.text((x - bb[0], y - bb[1]), s, font=f, fill=tuple(col[:3]) + (int(255 * a),))
            ctx.track([(box[0], box[1]), (box[2], box[3])], raw=True)
            reg.text_in(cname, box, G)
            for s2, b2 in drawn:
                if min(box[2], b2[2]) - max(box[0], b2[0]) > -4 and min(box[3], b2[3]) - max(box[1], b2[1]) > -4:
                    reg.text_issues.append(f"圖解字互撞「{s}」×「{s2}」")
            drawn.append((s, box))


# ───────────────────────── 共用圖元 ─────────────────────────
LAYER_COLS = [(150, 112, 250), (118, 92, 236), (96, 128, 246), (78, 150, 240), (60, 176, 222), (48, 196, 200),
              (58, 206, 170), (90, 210, 140), (150, 205, 110), (210, 190, 90), (240, 160, 80), (250, 128, 96)]


def hbm_stack(g, pr, x, y, z, w, d, layers=8, lh=10, gap=2, a=1.0, base=True, exploded=0.0, drop=None, tsv=0.0, t=0.0):
    """HBM 堆疊：底層控制晶片＋DRAM 多層。exploded＝層間額外間距；drop(k)→第 k 層的出場 0～1。回傳頂面 z。"""
    zz = z
    if base:
        g.box(pr, x, y, zz, w, d, lh + 2, (34, 70, 82), a, top_col=(56, 110, 120))
        zz += lh + 2 + gap
    for k in range(layers):
        u = 1.0 if drop is None else drop(k)
        if u <= 0:
            zz += lh + gap + exploded
            continue
        off = (1 - u) * 40
        col = LAYER_COLS[k % len(LAYER_COLS)]
        g.box(pr, x, y, zz + off, w, d, lh, col, a * u)
        zz += lh + gap + exploded
    if tsv > 0:
        # 矽穿孔：在正面與側面畫出發亮的垂直通道，從底層一路打通到頂
        top = zz - gap - exploded
        for k in range(4):
            fx = x + w * (0.18 + 0.21 * k)
            p0, p1 = pr(fx, y + d, z), pr(fx, y + d, z + (top - z) * tsv)
            g.line([p0, p1], (*rgb(GOLD), 0.95 * a), 3.2, track=False)
            g.glow(p1[0], p1[1], 14, GOLD, 0.8 * a * (0.6 + 0.4 * math.sin(t * 8 + k)))
            fy = y + d * (0.2 + 0.2 * k)
            q0, q1 = pr(x + w, fy, z), pr(x + w, fy, z + (top - z) * tsv)
            g.line([q0, q1], (*rgb(GOLD), 0.75 * a), 2.6, track=False)
    return zz


def gpu_die(g, pr, x, y, z, w, d, h, a=1.0, glow=0.0, label="GPU", size=40, t=0.0):
    g.box(pr, x, y, z, w, d, h, CHIP, a, top_col=(64, 74, 92))
    # 晶片頂面的細格線
    for k in range(1, 6):
        g.line([pr(x + w * k / 6, y + 6, z + h), pr(x + w * k / 6, y + d - 6, z + h)], (1, 1, 1, 0.06 * a), 1, track=False)
        g.line([pr(x + 6, y + d * k / 6, z + h), pr(x + w - 6, y + d * k / 6, z + h)], (1, 1, 1, 0.06 * a), 1, track=False)
    if glow > 0:
        cx, cy = pr(x + w / 2, y + d / 2, z + h)
        g.glow(cx, cy, max(w, d) * 0.9 * pr.s, TEAL, 0.35 * glow * a * (0.8 + 0.2 * math.sin(t * 6)))
    g.top_text(pr, x, y, z + h, w, d, label, size, (230, 238, 246), a)


def package(g, pr, t, a=1.0, hbm_a=1.0, hbm_lift=0.0, flow=0.0, drop=None, sub_col=(30, 92, 70)):
    """CoWoS 樣式封裝：基板＋中介層＋GPU＋四疊 HBM（S01、S10 共用）。"""
    g.shadow(pr, 0, 0, 420, 420, a=0.55 * a)
    g.box(pr, 0, 0, 0, 420, 420, 24, sub_col, a, top_col=light(sub_col, 0.18))
    # 基板上的走線
    for k in range(1, 9):
        g.line([pr(14, 14 + k * 44, 24), pr(40, 14 + k * 44, 24)], (*rgb(GOLD), 0.5 * a), 2, track=False)
    g.box(pr, 40, 40, 24, 340, 340, 14, (70, 96, 120), a, top_col=(104, 130, 156))
    gpu_die(g, pr, 140, 110, 38, 140, 200, 26, a, glow=flow, size=34, t=t)
    spots = [(55, 105), (55, 245), (305, 105), (305, 245)]
    for (sx, sy) in sorted(spots, key=lambda p: p[0] + p[1]):
        za = 38 + hbm_lift
        ha = a * hbm_a
        if ha > 0:
            hbm_stack(g, pr, sx, sy, za, 60, 70, layers=8, lh=8, gap=2, a=ha, drop=drop)
    if flow > 0 and hbm_a > 0.2:
        for (sx, sy) in spots:
            left = sx < 140
            for k in range(3):
                u = (t * 1.6 + k / 3 + sy * 0.003) % 1.0
                x0 = sx + 60 if left else sx
                x1 = 140 if left else 280
                px = lerp(x0, x1, u)
                p = pr(px, sy + 35, 40)
                g.glow(p[0], p[1], 16, TEAL, 0.9 * flow * hbm_a * a)


def arrow(g, p0, p1, col, a=1.0, lw=6, head=18):
    g.line([p0, p1], (*rgb(col), a), lw)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    pts = [p1, (p1[0] - head * math.cos(ang - 0.45), p1[1] - head * math.sin(ang - 0.45)),
           (p1[0] - head * math.cos(ang + 0.45), p1[1] - head * math.sin(ang + 0.45))]
    g.poly(pts, (*rgb(col), a))


def leader(g, p_from, p_to, a, col=MUTED):
    g.line([p_from, p_to], (*rgb(col), 0.75 * a), 2, track=False)
    g.c.arc(p_from[0], p_from[1], 4.5, 0, 2 * math.pi)
    g.c.set_source_rgba(*rgb(col), 0.95 * a)
    g.c.fill()


# ───────────────────────── 場景 ─────────────────────────
def sc_s01(g, L, t, A):
    ln = LINES["S01"]
    t_cu = ln.at("運算單元")
    t_bw = ln.at("記憶體頻寬")
    t_hbm = ln.at("HBM")
    pr = Proj("iso", 540, 520 + (1 - ap(t, 0.0, 0.6)) * 30, 0.88)
    ha = ap(t, t_hbm - 0.1, 0.4)
    drop = lambda k: ap(t, t_hbm - 0.1 + k * 0.06, 0.3)  # noqa: E731
    package(g, pr, t, A * ap(t, -0.25, 0.5), hbm_a=ha, flow=ap(t, t_hbm + 0.5, 0.5), drop=drop)
    if ha > 0:
        lp = pr(85, 175, 150)
        L.add("HBM", lp[0] - 60, lp[1] - 20, font(F_BLACK, 40), (196, 176, 255), A * ha, "rm")
        leader(g, (lp[0] - 50, lp[1] - 20), pr(55, 140, 110), A * ha)
    # 下方：2.5D 長條對比（運算能力 vs 記憶體頻寬）
    bp = Proj("obl", 0, 1320, 1.0)
    fa = A * ap(t, t_cu - 0.4)
    if fa > 0:
        g.shadow(bp, 200, -10, 640, 90, a=0.4 * fa, spread=14)
        g.box(bp, 200, -10, -14, 640, 90, 14, (34, 46, 62), fa, edge=0.25)
        h1 = 330 * ease_out((t - t_cu + 0.2) / 0.8)
        g.box(bp, 300, 10, 0, 130, 60, max(3, h1), BLUE, fa)
        L.add("運算能力", bp(365, 0)[0], 1334, font(F_BOLD, 32), TXT, fa, "ma")
        if h1 > 200:
            q = bp(365, 10, h1)
            L.add("一直提升", q[0] + 10, q[1] - 26, font(F_BOLD, 30), (150, 200, 255), fa, "mb")
    ba = A * ap(t, t_bw - 0.2)
    if ba > 0:
        grow = ease_io((t - t_hbm - 0.2) / 0.9)
        h2 = lerp(90, 300, grow) * ease_out((t - t_bw + 0.2) / 0.5)
        col = tuple(int(lerp(RED[i], TEAL[i], grow)) for i in range(3))
        g.box(bp, 610, 10, 0, 130, 60, max(3, h2), col, ba)
        L.add("記憶體頻寬", bp(675, 0)[0], 1334, font(F_BOLD, 32), TXT, ba, "ma")
        q = bp(675, 10, h2)
        if grow < 0.5:
            g.glow(q[0], q[1] + 20, 90, RED, 0.5 * ba * (0.7 + 0.3 * math.sin(t * 7)))
            L.add("瓶頸", q[0] + 10, q[1] - 30, font(F_BLACK, 40), WHITE_RED, ba * (1 - grow * 2), "mb", bg=(130, 30, 40, 230), r=18)
        else:
            L.add("HBM 補上頻寬", q[0] + 10, q[1] - 26, font(F_BOLD, 30), TEAL, ba * (grow - 0.5) * 2, "mb")


WHITE_RED = (255, 236, 236)


def sc_s02(g, L, t, A):
    ln = LINES["S02"]
    pr = Proj("iso", 560, 862, 1.1)
    t_layers = min(ln.at("多層"), ln.start + 0.6)
    t_stack = ln.at("垂直堆疊")
    t_tsv = ln.at("透過矽穿孔")
    t_base = ln.at("底部")
    t_int = ln.at("整疊")
    t_gpu = ln.at("與 GPU")
    t_25d = ln.at("2.5D")
    a_sub = A * ap(t, t_int - 0.1)
    a_int = A * ap(t, t_int + 0.15)
    a_base = A * ap(t, t_base - 0.05)
    a_gpu = A * ap(t, t_gpu - 0.15)
    expl = lerp(26, 0, ease_io((t - t_stack) / 0.7))
    if a_sub > 0:
        g.shadow(pr, -70, -70, 520, 290, a=0.5 * a_sub)
        g.box(pr, -70, -70, 0, 520, 290, 22, (30, 92, 70), a_sub, top_col=(46, 120, 92))
    if a_int > 0:
        g.box(pr, -40, -40, 22, 460, 230, 16, (70, 96, 120), a_int, top_col=(104, 130, 156))
    z0 = 38
    if a_base > 0:
        g.box(pr, 0, 0, z0 + (1 - a_base / max(A, 1e-6)) * 30, 150, 150, 16, (34, 70, 82), a_base, top_col=(56, 110, 120))
    tsv = ease_io((t - t_tsv) / 0.8)
    stack_a = A * ap(t, t_layers - 0.4, 0.3)
    top = hbm_stack(g, pr, 0, 0, z0 + 18, 150, 150, layers=8, lh=14, gap=3, a=stack_a, base=False, exploded=expl,
                    drop=lambda k: ap(t, t_layers - 0.35 + k * 0.09, 0.3), tsv=tsv, t=t)
    if a_gpu > 0:
        gpu_die(g, pr, 210, 0, 38 + (1 - ap(t, t_gpu - 0.15)) * 50, 180, 150, 40, a_gpu, glow=0.6, size=46, t=t)
        p1, p2 = pr(150, 75, 90), pr(210, 75, 90)
        u = (t * 1.5) % 1
        g.glow(lerp(p1[0], p2[0], u), lerp(p1[1], p2[1], u), 16, TEAL, a_gpu)
    # 標籤（左側固定一欄，引線指到堆疊）
    f = font(F_BOLD, 34)
    fs = font(F_MED, 26)
    la = stack_a
    XR = 318
    if la > 0:
        p = pr(0, 150, z0 + 18 + (top - z0 - 18) * 0.8)
        L.add("DRAM 晶粒", XR, 520, f, (200, 186, 255), la, "ra")
        L.add("多層垂直堆疊", XR, 566, fs, MUTED, la, "ra")
        leader(g, (p[0] - 4, p[1]), (XR + 8, 540), la)
    ta = A * ap(t, t_tsv)
    if ta > 0:
        p = pr(21 + 150 * 0.18, 150, z0 + 18 + (top - z0 - 18) * 0.45)
        L.add("TSV 矽穿孔", XR, 660, f, GOLD, ta, "ra")
        L.add("上下互連", XR, 706, fs, MUTED, ta, "ra")
        leader(g, (p[0], p[1]), (XR + 8, 680), ta)
    if a_base > 0:
        p = pr(0, 150, z0 + 8)
        L.add("基底晶片", XR, 810, f, (120, 214, 220), a_base, "ra")
        leader(g, (p[0] - 2, p[1]), (XR + 8, 830), a_base)
    if a_int > 0:
        p = pr(-40, 150, 30)
        L.add("中介層", XR, 950, f, (170, 196, 222), a_int, "ra")
        leader(g, (p[0] + 2, p[1]), (XR + 8, 970), a_int)
    if a_sub > 0:
        p = pr(160, 220, 6)
        L.add("封裝基板", p[0] - 30, 1290, f, (130, 214, 170), a_sub, "ra")
        leader(g, (p[0], p[1]), (p[0] - 22, 1306), a_sub)
    if a_gpu > 0:
        L.add("與 GPU 並排", 1000, 600, f, TEAL, a_gpu, "ra", bg=(16, 56, 54, 220), pad=(18, 10), r=18)
        a25 = A * ap(t, t_25d - 0.1)
        if a25 > 0:
            L.add("＝ 2.5D 封裝", 1000, 1270, font(F_BLACK, 44), GOLD, a25, "ra", bg=(60, 48, 16, 225), pad=(22, 12), r=20)
        p = pr(380, 20, 80)
        leader(g, (p[0], p[1]), (930, 640), a_gpu, col=TEAL)


def sc_s03(g, L, t, A):
    ln = LINES["S03"]
    pr = Proj("obl", 60, 880, 1.07)
    t_fast = ln.at("運算速度")
    t_slow = ln.at("如果")
    t_wait = ln.at("GPU 就")
    t_neck = ln.at("這就是")
    a0 = A * ap(t, ln.start - 0.2)
    # 記憶體（左）
    g.shadow(pr, 0, 0, 150, 130, a=0.5 * a0)
    hbm_stack(g, pr, 0, 0, 0, 150, 130, layers=9, lh=13, gap=3, a=a0)
    q = pr(75, 0, 0)
    L.add("記憶體", q[0], q[1] + 24, font(F_BOLD, 36), (200, 186, 255), a0, "ma")
    # GPU（右）：正面寫字
    gl = ap(t, t_fast) * (1 - 0.7 * ap(t, t_wait))
    g.shadow(pr, 620, 0, 220, 160, a=0.5 * a0)
    if gl > 0:
        cx, cy = pr(730, 80, 110)
        g.glow(cx, cy, 200, TEAL, 0.5 * gl * a0 * (0.8 + 0.2 * math.sin(t * 7)))
    g.box(pr, 620, 0, 0, 220, 160, 120, CHIP, a0, top_col=(64, 74, 92))
    for k in range(1, 6):
        g.line([pr(620 + 220 * k / 6, 8, 120), pr(620 + 220 * k / 6, 152, 120)], (1, 1, 1, 0.07 * a0), 1, track=False)
    cx, cy = pr(730, 0, 60)
    L.add("GPU", cx, cy, font(F_BLACK, 60), TXT, a0, "mm")
    if gl > 0.05:
        L.add("運算速度提升", cx, cy - 210, font(F_BOLD, 34), TEAL, A * gl, "mm")
    # 傳輸通道：寬 → 中間變窄（瓶頸）
    neck = ease_io((t - t_slow) / 0.8)
    x0, x1 = 150, 620
    mid0, mid1 = 320, 450
    dw = lerp(80, 18, neck)
    yc, z, hw = 65, 26, 40
    c_pipe = (52, 74, 100)
    def ring(zz):
        return [pr(x0, yc - hw, zz), pr(mid0, yc - hw, zz), pr(mid0 + 30, yc - dw / 2, zz), pr(mid1 - 30, yc - dw / 2, zz),
                pr(mid1, yc - hw, zz), pr(x1, yc - hw, zz)]
    pa = A * ap(t, ln.start)
    front = ring(z) + ring(z - 16)[::-1]
    g.poly(front, (*rgb(dark(c_pipe, 0.35)), pa))
    back = [pr(x1, yc + hw, z), pr(mid1, yc + hw, z), pr(mid1 - 30, yc + dw / 2, z), pr(mid0 + 30, yc + dw / 2, z),
            pr(mid0, yc + hw, z), pr(x0, yc + hw, z)]
    top = ring(z) + back
    g.poly(top, src=g.lin(top[0], top[5], [(0, light(c_pipe, 0.25), pa), (1, c_pipe, pa)]), stroke=(1, 1, 1, 0.25 * pa), lw=1.4)
    if neck > 0.3:
        nc = pr((mid0 + mid1) / 2, yc, z)
        g.glow(nc[0], nc[1], 100, RED, 0.55 * A * ap(t, t_slow + 0.3) * (0.75 + 0.25 * math.sin(t * 8)))
    # 記憶體牆：通道兩側長出磚牆，只留中間一道窄縫
    wall = ease_out((t - t_neck + 0.4) / 0.9)
    if wall > 0:
        wa_ = A * min(1.0, wall * 1.5)
        wx = (mid0 + mid1) / 2 - 22
        for side in (0, 1):
            for row in range(5):
                hh = 26
                if row * hh > 130 * wall:
                    break
                for colm in range(3):
                    y0_ = (yc + dw / 2 + 4 + colm * 22 + (row % 2) * 8) if side else (yc - dw / 2 - 26 - colm * 22 - (row % 2) * 8)
                    g.box(pr, wx, y0_, z + row * hh, 44, 20, hh - 3, (150, 70, 60), wa_, edge=0.25)
    # 資料方塊：前段順暢；變窄後在瓶頸前排隊、只有少數通過
    n = 16
    cubes = []
    for k in range(n):
        ph = (t * 0.5 + k / n) % 1.0
        xx = lerp(x0 + 6, x1 - 30, ph)
        yy = yc + ((k * 37) % 56) - 28
        if neck > 0:
            if k % 4 != 0:
                qx = mid0 + 4 - (k % 6) * 26
                xx = lerp(xx, min(xx, qx), neck)
            if mid0 < xx < mid1:
                yy = lerp(yy, yc + (yy - yc) * 0.2, neck)
        cubes.append((yy, xx, k))
    cubes = [c_ for c_ in cubes]
    for yy, xx, k in sorted(cubes, key=lambda c_: -c_[0]):
        g.box(pr, xx, yy - 9, z, 22, 18, 20, ORANGE if k % 3 else GOLD, pa * 0.95, edge=0.3)
    q = pr(300, 0, 0)
    L.add("參數・中間資料", q[0] + 50, q[1] + 24, font(F_BOLD, 34), ORANGE, pa, "ma")
    # GPU 忙碌程度（2.5D 長條）：全速 → 閒置等待
    ua = A * ap(t, t_fast - 0.1)
    if ua > 0:
        bp = Proj("obl", 560, 1110, 1.0)
        g.box(bp, 0, 0, 0, 380, 30, 36, (36, 46, 60), ua, edge=0.2)
        fill = lerp(0.96, 0.2, ease_io((t - t_slow - 0.2) / 1.0))
        col = TEAL if fill > 0.6 else (GOLD if fill > 0.4 else RED)
        g.box(bp, 2, 2, 0, 380 * fill - 4, 26, 36.5, col, ua * 0.9, edge=0.2)
        L.add("GPU 忙碌程度", 560, 1136, font(F_BOLD, 30), MUTED, ua, "la")
        st = "全速運算" if fill > 0.6 else "閒置等待…"
        L.add(st, 940, 1136, font(F_BOLD, 30), col, ua, "ra")
    wa = A * ap(t, ln.at("記憶體牆") - 0.15, 0.35)
    if wa > 0:
        s_ = 0.85 + 0.15 * back_out(clamp((t - t_neck + 0.15) / 0.4))
        L.add("記憶體牆（Memory Wall）", 540, 1300, font(F_BLACK, int(52 * s_)), (255, 238, 238), wa, "mm", bg=(150, 34, 44, 235), pad=(28, 16), r=24)


def bus(g, pr, x, y, length, depth, bits, col, a, t, step):
    """2.5D 介面通道：一條有厚度的平板，上面每條細線代表 step 位元，資料點沿通道流動。"""
    g.box(pr, x, y, 0, length, depth, 16, col, a, edge=0.3)
    n = max(1, int(bits / step))
    for k in range(n + 1):
        yy = y + depth * k / n
        if 0 < k < n:
            g.line([pr(x + 6, yy, 16), pr(x + length - 6, yy, 16)], (1, 1, 1, 0.22 * a), 1.2, track=False)
    for k in range(n):
        yy = y + depth * (k + 0.5) / n
        ph = (t * 0.7 + k * 0.137) % 1
        p = pr(x + 10 + ph * (length - 20), yy, 17)
        g.glow(p[0], p[1], 9, (255, 255, 255), 0.7 * a)


def sc_s04(g, L, t, A):
    ln = LINES["S04"]
    t_if = ln.at("一千零二十四")
    # 上半：介面寬度（位元數換算成通道寬度，同一比例）
    ia = A * ap(t, ln.start - 0.1)
    pr = Proj("obl", 300, 0, 1.0)
    rows_if = [("DDR5 模組", "64 位元", 64, SLATE, ia, 560),
               ("HBM（每疊）", "1024 位元", 1024, PURPLE, A * ap(t, t_if - 0.2), 700)]
    for name, bits_s, bits, col, a, ybase in rows_if:
        if a <= 0:
            continue
        p_ = Proj("obl", 300, ybase, 1.0)
        depth = bits / 1024 * 150
        g.shadow(p_, 0, 0, 640, max(depth, 8), a=0.4 * a, spread=12)
        bus(g, p_, 0, 0, 640, max(depth, 8), bits, col, a, t, 64)
        L.add(name, 270, ybase - 30, font(F_BOLD, 32), TXT, a, "rb")
        L.add(bits_s, 270, ybase - 22, font(F_BLACK, 36), GOLD if bits > 64 else MUTED, a, "ra")
    wa = A * ap(t, t_if + 0.6)
    if wa > 0:
        L.add("通道寬 16 倍", 1000, 470, font(F_BOLD, 32), GOLD, wa, "ra", bg=(60, 48, 16, 225), pad=(18, 10), r=18)
    # 下半：相對比較
    rows = [("頻寬", "高", True, "較低", False, ln.at("大幅")),
            ("每位元傳輸功耗", "較低", True, "較高", False, ln.at("每位元")),
            ("成本", "較高", False, "較低", True, ln.at("代價")),
            ("容量擴充", "受限堆疊層數", False, "插槽可擴充", True, ln.at("容量"))]
    cols = [(330, 330, PURPLE), (690, 330, SLATE)]
    ha = A * ap(t, ln.at("大幅") - 0.3)
    if ha > 0:
        for (x, w, col), s_ in zip(cols, ["HBM", "GDDR／DDR"]):
            p_ = Proj("obl", x, 860, 1.0)
            g.box(p_, 0, 0, 0, w - 30, 24, 50, col, ha)
            L.add(s_, x + (w - 30) / 2, 835, font(F_BLACK, 32), TXT, ha, "mm")
    fr = font(F_BOLD, 32)
    for k, (name, hv, hg, dv, dg, ta) in enumerate(rows):
        ra = A * ap(t, ta - 0.15, 0.4)
        if ra <= 0:
            continue
        y = 975 + k * 112
        dy = (1 - ra / max(A, 1e-6)) * 24
        L.add(name, 60, y - 30 + dy, fr, MUTED, ra, "lm")
        for (x, w, col), v, good in ((cols[0], hv, hg), (cols[1], dv, dg)):
            p_ = Proj("obl", x, y + dy, 1.0)
            tc = (24, 92, 84) if good else (110, 58, 30)
            g.box(p_, 0, 0, 0, w - 30, 22, 62, tc, ra, edge=0.3)
            L.add(v, x + (w - 30) / 2 + 10, y + dy - 31, fr, TEAL if good else ORANGE, ra, "mm")
            mp_ = Proj("obl", x + 12, y + dy - 20, 1.0)
            g.box(mp_, 0, 0, 0, 12, 8, 22, TEAL if good else ORANGE, ra, edge=0.2)


BARS5 = [("HBM1", "2013", "4 層", 128, "128 GB/s"), ("HBM2", "2016", "4 層", 256, "256 GB/s"),
         ("HBM3", "2022", "8 層", 819, "819 GB/s"), ("HBM3E", "2024", "8～12 層", 1229, "約 1.2 TB/s"),
         ("HBM4", "2026", "12 層", 2048, "約 2 TB/s（標準）")]


def sc_s05(g, L, t, A):
    ln = LINES["S05"]
    pr = Proj("obl", 82, 1205, 1.0)
    fa = A * ap(t, ln.start - 0.2)
    slot = 172
    g.shadow(pr, -10, -10, slot * 5 + 10, 110, a=0.4 * fa, spread=16)
    g.box(pr, -10, -10, -16, slot * 5 + 10, 110, 16, (34, 46, 62), fa, edge=0.25)
    t_e = ln.at("HBM3E")
    appear = [ln.at("二零一三"), t_e - 0.9, t_e - 0.55, t_e - 0.15, ln.at("HBM4")]
    scale = 560 / 2048
    tops = []
    for k, (nm, yr, lay, v, lab) in enumerate(BARS5):
        u = ease_out((t - appear[k]) / 0.7)
        x = k * slot + 22
        L.add(nm, pr(x + 46, 0)[0], 1222, font(F_BLACK, 32), TXT if k < 4 else (190, 200, 214), fa, "ma")
        L.add(yr + (" 量產" if k == 4 else ""), pr(x + 46, 0)[0], 1266, font(F_BOLD, 26), MUTED, fa, "ma")
        L.add(lay, pr(x + 46, 0)[0], 1302, font(F_MED, 24), DIM, fa, "ma")
        if u <= 0:
            tops.append(None)
            continue
        h = max(4, v * scale * u)
        col = [(96, 112, 220), (110, 100, 236), (132, 98, 246), (170, 96, 240), (40, 200, 186)][k]
        if k == 4:
            g.box(pr, x, 10, 0, 92, 70, h, col, fa * 0.5, edge=0.6)
            T = [pr(x, 10, h), pr(x + 92, 10, h), pr(x + 92, 80, h), pr(x, 80, h)]
            g.line([pr(x, 10, 0), pr(x, 10, h), pr(x + 92, 10, h), pr(x + 92, 10, 0)], (*rgb(TEAL), fa), 2.5, dash=[10, 7])
        else:
            g.box(pr, x, 10, 0, 92, 70, h, col, fa)
        tp = pr(x + 46, 10, h)
        tops.append(tp)
        if u > 0.6:
            va = fa * ap(t, appear[k] + 0.4, 0.3)
            L.add(lab, tp[0] + 10, tp[1] - 52, font(F_BLACK if k in (0, 3) else F_BOLD, 30), GOLD if k in (0, 3) else TXT, va, "mb")
    # 十倍括號箭頭：HBM1 → HBM3E
    xa = A * ap(t, ln.at("大約") - 0.2, 0.5)
    if xa > 0 and tops[0] is not None and tops[3] is not None:
        p0 = (tops[0][0] + 10, tops[0][1] - 110)
        p1 = (tops[3][0] - 40, tops[3][1] - 20)
        cp = (p0[0] + 40, p1[1] - 40)
        u = ease_io(xa / max(A, 1e-6))
        pts = []
        for i in range(25):
            s_ = i / 24 * u
            pts.append(((1 - s_) ** 2 * p0[0] + 2 * (1 - s_) * s_ * cp[0] + s_ ** 2 * p1[0],
                        (1 - s_) ** 2 * p0[1] + 2 * (1 - s_) * s_ * cp[1] + s_ ** 2 * p1[1]))
        g.line(pts, (*rgb(GOLD), xa), 6)
        if u > 0.95:
            arrow(g, pts[-3], pts[-1], GOLD, xa, lw=6, head=22)
        L.add("約第一代的 9 倍以上", 120, 560, font(F_BLACK, 46), GOLD, xa, "la", bg=(60, 48, 16, 225), pad=(22, 14), r=20)
    na = A * ap(t, ln.at("介面") - 0.1)
    if na > 0:
        L.add("HBM4：介面加寬到 2048 位元", 1000, 470, font(F_BOLD, 34), TEAL, na, "ra", bg=(16, 56, 54, 230), pad=(20, 12), r=18)


def server_rack(g, pr, x, y, a, t, n=6):
    g.box(pr, x, y, 0, 80, 110, 210, (40, 50, 66), a, top_col=(70, 82, 100))
    for k in range(n):
        z = 22 + k * 31
        p0, p1 = pr(x + 8, y + 110, z), pr(x + 72, y + 110, z)
        g.line([p0, p1], (*rgb(TEAL if (k + int(t * 3)) % 3 else ORANGE), 0.9 * a), 3.5, track=False)
        q0, q1 = pr(x + 8, y + 110, z + 12), pr(x + 72, y + 110, z + 12)
        g.line([q0, q1], (1, 1, 1, 0.12 * a), 1.5, track=False)


def tile_floor(g, pr, a, col):
    g.shadow(pr, 0, 0, 200, 200, a=0.45 * a, spread=18)
    g.box(pr, 0, 0, -14, 200, 200, 14, col, a, edge=0.25)


def sc_s06(g, L, t, A):
    ln = LINES["S06"]
    items = [("AI 加速器", ln.at("AI 加速器"), 205), ("雲端資料中心", ln.at("雲端資料中心"), 540), ("高效能運算", ln.at("高效能運算"), 875)]
    hub_t = ln.at("這些場景")
    for k, (name, ta, cx) in enumerate(items):
        a = A * ap(t, ta - 0.2, 0.45)
        if a <= 0:
            continue
        bob = math.sin(t * 2.2 + k) * 4
        pr = Proj("iso", cx, 700 + (1 - a / max(A, 1e-6)) * 40 + bob, 0.78)
        tile_floor(g, pr, a, (30, 48, 70))
        if k == 0:
            server_rack(g, pr, 60, 45, a, t)
        elif k == 1:
            for i in range(3):
                for j in range(2):
                    xx, yy = 10 + i * 62, 20 + j * 92
                    g.box(pr, xx, yy, 0, 44, 70, 120, (40, 50, 66), a, top_col=(70, 82, 100))
                    for m in range(3):
                        p0, p1 = pr(xx + 4, yy + 70, 20 + m * 34), pr(xx + 40, yy + 70, 20 + m * 34)
                        g.line([p0, p1], (*rgb(BLUE if (m + i + int(t * 2)) % 2 else TEAL), 0.9 * a), 3, track=False)
        else:
            g.box(pr, 30, 30, 0, 140, 140, 16, (70, 96, 120), a)
            g.box(pr, 55, 55, 16, 90, 90, 18, CHIP, a, top_col=(64, 74, 92))
            for m in range(7):
                g.box(pr, 56 + m * 13, 56, 34, 6, 88, 44, (150, 160, 175), a, edge=0.25)
            c = pr(100, 100, 80)
            g.glow(c[0], c[1], 90, ORANGE, 0.3 * a * (0.7 + 0.3 * math.sin(t * 5)))
        lp = pr(200, 200, -14)
        L.add(name, cx, 900, font(F_BLACK, 42), TXT, a, "ma")
    ha = A * ap(t, hub_t - 0.25, 0.5)
    if ha > 0:
        pr = Proj("iso", 540, 1150, 0.9)
        g.shadow(pr, 0, 0, 90, 90, a=0.5 * ha)
        hbm_stack(g, pr, 0, 0, 0, 90, 90, layers=8, lh=9, gap=2, a=ha)
        c = pr(45, 45, 100)
        g.glow(c[0], c[1], 110, PURPLE, 0.45 * ha)
        for k, (_n, _t, cx) in enumerate(items):
            p0 = (540 + (cx - 540) * 0.25, 1080)
            p1 = (cx, 970)
            g.line([p0, p1], (*rgb(PURPLE), 0.8 * ha), 4, dash=[12, 8])
        L.add("頻寬需求遠高於一般運算", 540, 1300, font(F_BLACK, 44), (205, 190, 255), ha, "mm")


def sc_s07(g, L, t, A):
    ln = LINES["S07"]
    steps = [
        ("記憶體廠：堆疊與出廠測試", "DRAM 晶粒垂直堆疊後先測試", "例：SK 海力士、三星、美光", ln.at("記憶體廠")),
        ("基底晶片：改用邏輯製程", "HBM4 起部分交由晶圓代工", "依廠商不同，自製或委外", ln.at("從 HBM4")),
        ("先進封裝：與 GPU 整合", "HBM 與 GPU 放上同一片中介層", "例：台積電 CoWoS", ln.at("最後")),
        ("封測廠：最終測試", "確認整顆模組功能正常", "例：日月光、Amkor 等", ln.at("由封測廠")),
    ]
    for k, (title, desc, ex, ta) in enumerate(steps):
        a = A * ap(t, ta - 0.25, 0.45)
        if a <= 0:
            continue
        y = 500 + k * 240
        dx = (1 - a / max(A, 1e-6)) * -40
        pr = Proj("iso", 200 + dx, y - 10, 0.8)
        g.shadow(pr, 0, 0, 150, 150, a=0.45 * a, spread=16)
        g.box(pr, 0, 0, -12, 150, 150, 12, (30, 48, 70), a, edge=0.25)
        if k == 0:
            hbm_stack(g, pr, 35, 35, 0, 80, 80, layers=8, lh=9, gap=2, a=a, base=False)
        elif k == 1:
            px, pyt, R, ry = g.cyl(pr, 75, 75, 0, 66, 6, (170, 180, 196), a, top_col=(196, 206, 222))
            c = g.c
            c.save()
            c.new_path(); c.save(); c.translate(px, pyt); c.scale(1, ry / R); c.arc(0, 0, R - 4, 0, 2 * math.pi); c.restore()
            c.clip()
            for i in range(-8, 9):
                q0, q1 = pr(75 + i * 9, 0, 6), pr(75 + i * 9, 150, 6)
                g.line([q0, q1], (0.35, 0.45, 0.6, 0.35 * a), 1, track=False)
                q0, q1 = pr(0, 75 + i * 9, 6), pr(150, 75 + i * 9, 6)
                g.line([q0, q1], (0.35, 0.45, 0.6, 0.35 * a), 1, track=False)
            c.restore()
            g.box(pr, 95, 40, 6, 40, 40, 10, (34, 70, 82), a, top_col=(56, 110, 120))
        elif k == 2:
            g.box(pr, 10, 10, 0, 130, 130, 10, (70, 96, 120), a, top_col=(104, 130, 156))
            g.box(pr, 50, 25, 10, 50, 100, 16, CHIP, a, top_col=(64, 74, 92))
            for sx in (16, 106):
                hbm_stack(g, pr, sx, 30, 10, 26, 40, layers=6, lh=6, gap=1, a=a, base=False)
                hbm_stack(g, pr, sx, 80, 10, 26, 40, layers=6, lh=6, gap=1, a=a, base=False)
        else:
            g.box(pr, 35, 35, 0, 80, 80, 14, CHIP, a, top_col=(64, 74, 92))
            c = pr(75, 75, 60)
            g.glow(c[0], c[1], 70, GREEN, 0.4 * a)
            g.line([(c[0] - 26, c[1] + 2), (c[0] - 6, c[1] + 22), (c[0] + 30, c[1] - 22)], (*rgb(GREEN), a), 10)
        if k < 3:
            na = A * ap(t, steps[k + 1][3] - 0.3)
            if na > 0:
                arrow(g, (200, y + 160), (200, y + 200), MUTED, na, lw=4, head=14)
        L.add(f"{k + 1}", 70, y - 50, font(F_BLACK, 34), TXT, a, "mm", bg=(*ORANGE, 255), pad=(14, 6), r=18)
        L.add(title, 390, y - 62, font(F_BLACK, 40), TXT, a, "la")
        L.add(desc, 390, y - 6, font(F_MED, 30), MUTED, a, "la")
        L.add(ex, 390, y + 40, font(F_MED, 26), DIM, a, "la")


def sc_s08(g, L, t, A):
    ln = LINES["S08"]
    cards = [("良率控制", "堆疊層數越多越困難", ln.at("堆疊層數") - 0.2, (290, 680)),
             ("成本", "晶圓用量大", ln.at("晶圓用量"), (790, 680)),
             ("產能", "擴產需時，供給偏緊", ln.at("產能擴充"), (290, 1170)),
             ("散熱", "高密度堆疊，設計更關鍵", ln.at("高密度"), (790, 1170))]
    for k, (title, desc, ta, (cx, cy)) in enumerate(cards):
        a = A * ap(t, ta - 0.25, 0.45)
        if a <= 0:
            continue
        pr = Proj("iso", cx, cy - 210 + (1 - a / max(A, 1e-6)) * 30, 0.75)
        g.shadow(pr, 0, 0, 200, 200, a=0.45 * a, spread=18)
        g.box(pr, 0, 0, -14, 200, 200, 14, (30, 48, 70), a, edge=0.25)
        if k == 0:
            wob = math.sin(t * 5) * 2.5
            hbm_stack(g, pr, 60 + wob, 60, 0, 80, 80, layers=12, lh=9, gap=2, a=a, base=True)
            p = pr(140, 100, 70)
            g.glow(p[0], p[1], 50, RED, 0.6 * a * (0.6 + 0.4 * math.sin(t * 6)))
        elif k == 1:
            for i, (ox, oy, n) in enumerate([(50, 60, 5), (110, 60, 7), (80, 120, 3)]):
                for m in range(n):
                    g.cyl(pr, ox, oy, m * 9, 26, 8, GOLD, a, top_col=(255, 220, 120))
        elif k == 2:
            g.box(pr, 30, 40, 0, 140, 120, 70, (70, 84, 104), a, top_col=(96, 110, 130))
            for m in range(3):
                g.box(pr, 30 + m * 47, 40, 70, 47, 120, 18, (90, 104, 124), a)
            g.box(pr, 140, 50, 70, 20, 20, 60, (110, 120, 136), a)
            p = pr(155, 60, 135 + (t * 40) % 40)
            g.glow(p[0], p[1], 26, (200, 210, 220), 0.4 * a)
            # 滿載燈號
            for m in range(4):
                p0 = pr(30 + 20 + m * 28, 160, 30)
                g.c.arc(p0[0], p0[1], 7, 0, 2 * math.pi)
                g.c.set_source_rgba(*rgb(RED if m == 3 else ORANGE), a)
                g.c.fill()
        else:
            g.box(pr, 50, 50, 0, 100, 100, 18, CHIP, a, top_col=(64, 74, 92))
            p = pr(100, 100, 30)
            g.glow(p[0], p[1], 120, (255, 90, 40), 0.55 * a * (0.75 + 0.25 * math.sin(t * 4)))
            for m in range(3):
                pts = []
                for i in range(9):
                    yy = p[1] - 20 - i * 11
                    pts.append((p[0] - 40 + m * 40 + math.sin(i * 0.9 + t * 6 + m) * 9, yy))
                g.line(pts, (1, 0.6, 0.35, 0.85 * a), 4)
        L.add(title, cx, cy + 50, font(F_BLACK, 44), ORANGE if k else RED, a, "ma")
        L.add(desc, cx, cy + 112, font(F_MED, 30), MUTED, a, "ma")


def sc_s09(g, L, t, A):
    ln = LINES["S09"]
    a1 = A * ap(t, ln.at("HBM") - 0.3)
    if a1 > 0:
        pr = Proj("obl", 110, 640, 1.0)
        g.shadow(pr, 0, 0, 800, 50, a=0.45 * a1, spread=16)
        g.box(pr, 0, 0, 0, 800, 50, 150, (66, 52, 150), a1)
        L.add("HBM ＝ 垂直堆疊 ＋ 超寬介面", 510, 520, font(F_BOLD, 44), (215, 205, 255), a1, "mm")
        L.add("AI 系統效能的關鍵元件", 510, 592, font(F_BLACK, 60), TXT, A * ap(t, ln.at("關鍵元件") - 0.6), "mm")
    a2 = A * ap(t, ln.at("超寬介面") - 0.3)
    if a2 > 0:
        pr = Proj("obl", 70, 1170, 1.0)
        lanes = lerp(2, 6, ease_io((t - ln.at("換取頻寬")) / 0.8))
        width = 40 * lanes
        g.shadow(pr, 0, 0, 160, 160, a=0.5 * a2)
        hbm_stack(g, pr, 0, 0, 0, 160, 160, layers=8, lh=12, gap=3, a=a2)
        g.box(pr, 160, 80 - width / 2, 0, 470, width, 10, (44, 56, 74), a2, edge=0.25)
        for m in range(1, int(lanes)):
            yy = 80 - width / 2 + m * width / lanes
            g.line([pr(170, yy, 10), pr(620, yy, 10)], (1, 1, 1, 0.35 * a2), 2, dash=[18, 14], track=False)
        nl = int(lanes + 0.5)
        for m in range(nl):
            for j in range(3):
                ph = (t * 0.9 + j / 3 + m * 0.17) % 1
                yy = 80 - width / 2 + (m + 0.5) * width / max(lanes, 1) - 8
                g.box(pr, 175 + ph * 420, yy, 10, 26, 16, 14, ORANGE if (m + j) % 2 else GOLD, a2 * min(1, ph * 6, (1 - ph) * 6), edge=0.3)
        g.shadow(pr, 630, 0, 210, 160, a=0.5 * a2)
        g.box(pr, 630, 0, 0, 210, 160, 60, CHIP, a2, top_col=(64, 74, 92))
        c = pr(735, 80, 60)
        g.glow(c[0], c[1], 150, TEAL, 0.4 * a2 * lanes / 6)
        cx, cy = pr(735, 0, 30)
        L.add("GPU", cx, cy, font(F_BLACK, 46), TXT, a2, "mm")
        L.add("介面越寬 ＝ 車道越多", 120, 790, font(F_BLACK, 50), GOLD, a2, "la")
        da = A * ap(t, ln.at("決定") - 0.1)
        L.add("頻寬決定 AI 系統效能上限", 120, 870, font(F_BOLD, 40), TXT, da, "la")


def sc_s10(g, L, t, A):
    ln = LINES["S10"]
    a = A * ap(t, ln.start - 0.2, 0.6)
    pr = Proj("iso", 540, 520 + math.sin(t * 1.6) * 6, 0.82)
    package(g, pr, t, a, flow=1.0)
    sw = ((t * 0.5) % 1.0)
    p = pr(lerp(-40, 460, sw), 210, 70)
    g.glow(p[0], p[1], 70, (255, 255, 255), 0.18 * a)
    L.add("下一集", 540, 990, font(F_BOLD, 36), (255, 222, 196), a, "mm", bg=(*ORANGE, 220), pad=(22, 10), r=24)
    L.add("CoWoS 先進封裝", 540, 1080, font(F_BLACK, 70), TXT, a, "mm")
    ca = A * ap(t, ln.at("搜尋") - 0.2, 0.45)
    if ca > 0:
        bp = Proj("obl", 220, 1290, 1.0)
        s = 0.9 + 0.1 * back_out(clamp((t - ln.at("搜尋") + 0.2) / 0.45))
        g.shadow(bp, 0, 0, 620, 30, a=0.5 * ca, spread=14)
        g.box(bp, 0, 0, 0, 620, 30, 96, (220, 112, 40), ca)
        L.add("搜尋「哩股哩股」", 220 + 310, 1290 - 48, font(F_BLACK, int(54 * s)), (255, 255, 255), ca, "mm")


SCENE_FN = {"S01": sc_s01, "S02": sc_s02, "S03": sc_s03, "S04": sc_s04, "S05": sc_s05,
            "S06": sc_s06, "S07": sc_s07, "S08": sc_s08, "S09": sc_s09, "S10": sc_s10}


# ───────────────────────── 每格 ─────────────────────────
def background(c, t):
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, *rgb(BG_TOP))
    g.add_color_stop_rgb(1, *rgb(BG_BOT))
    c.set_source(g)
    c.paint()
    off = (t * 10) % 60
    c.set_line_width(1)
    c.set_source_rgba(0.55, 0.7, 0.9, 0.05)
    for y in range(-60, H + 60, 60):
        c.move_to(0, y + off)
        c.line_to(W, y + off)
    for x in range(0, W + 60, 60):
        c.move_to(x, 0)
        c.line_to(x, H)
    c.stroke()
    # 兩團環境光持續繞圈移動（每秒約 150～200px），讓整個畫面一直有細微變化，不會被判成停格
    gx, gy = 860 + math.sin(t * 0.8) * 200, 1450 + math.cos(t * 0.8) * 230
    r = cairo.RadialGradient(gx, gy, 0, gx, gy, 720)
    r.add_color_stop_rgba(0, 1.0, 0.55, 0.2, 0.20)
    r.add_color_stop_rgba(1, 1.0, 0.55, 0.2, 0)
    c.set_source(r)
    c.paint()
    gx, gy = 220 + math.cos(t * 0.7) * 200, 520 + math.sin(t * 0.7) * 220
    r = cairo.RadialGradient(gx, gy, 0, gx, gy, 680)
    r.add_color_stop_rgba(0, 0.15, 0.8, 0.75, 0.14)
    r.add_color_stop_rgba(1, 0.15, 0.8, 0.75, 0)
    c.set_source(r)
    c.paint()


# 字幕換行：自動找的斷點會把詞拆開（例：「一般」「台積電」），這幾句人工指定斷在詞界
MANUAL_BREAK = {
    "是把多層 DRAM 晶粒垂直堆疊": "是把多層 DRAM 晶粒",
    "底部是一顆負責控制的基底晶片": "底部是一顆",
    "HBM 用 1024 位元的超寬介面大幅提高頻寬": "HBM 用 1024 位元的超寬介面",
    "無法像 DDR 一樣用插槽擴充": "無法像 DDR 一樣",
    "HBM 目前集中在 AI 加速器、雲端資料中心與高效能運算": "HBM 目前集中在 AI 加速器、",
    "總結來說，HBM 以垂直堆疊與超寬介面換取頻寬": "總結來說，HBM 以",
    "是決定 AI 系統效能上限的關鍵元件": "是決定 AI 系統",
    "下一集，我們解析台積電的 CoWoS 先進封裝": "下一集，我們解析",
    "參數與中間資料必須在 GPU 與記憶體之間反覆搬移": "參數與中間資料必須在",
    "記憶體廠負責 DRAM 晶粒的堆疊與出廠測試": "記憶體廠負責 DRAM",
    "最後再透過台積電 CoWoS 等先進封裝與 GPU 整合": "最後再透過台積電 CoWoS",
    "高密度堆疊也讓散熱設計更加關鍵": "高密度堆疊也讓",
}


def wrap2(f, text, maxw):
    if tsize(f, text)[0] <= maxw:
        return [text]
    if text in MANUAL_BREAK:
        a_ = MANUAL_BREAK[text]
        b_ = text[len(a_):].strip()
        if tsize(f, a_.strip())[0] <= maxw and tsize(f, b_)[0] <= maxw:
            return [a_.strip(), b_]
        return None
    best = None
    for k in range(2, len(text) - 1):
        a_, b_ = text[:k], text[k:]
        if b_[0] in "，。！？、；：」）" or (a_[-1].isascii() and a_[-1].isalnum() and b_[0].isascii() and b_[0].isalnum()):
            continue
        if a_[-1] in "「（":
            continue
        a_, b_ = a_.rstrip(), b_.lstrip()
        wa, wb = tsize(f, a_)[0], tsize(f, b_)[0]
        if wa <= maxw and wb <= maxw:
            sc = abs(wa - wb) - (40 if a_[-1] in "，、" else 0)
            if best is None or sc < best[0]:
                best = (sc, [a_, b_])
    return best[1] if best else None


def sub_card(ov, reg, text, a, ta):
    if a <= 0:
        return
    x0, y0, x1, y1 = CARD
    d = ImageDraw.Draw(ov, "RGBA")
    # 2.5D 卡：底下一條較暗的厚度
    d.rounded_rectangle([x0, y0 + 10, x1, y1 + 10 - 10], 26, fill=(4, 8, 14, int(200 * a)))
    d.rounded_rectangle([x0, y0, x1, y1 - 10], 26, fill=(22, 34, 50, int(240 * a)))
    d.rounded_rectangle([x0, y0, x0 + 12, y1 - 10], 6, fill=ORANGE + (int(255 * a),))
    reg.add("字幕卡", (x0, y0, x1, y1))
    if not text or ta <= 0:
        return
    maxw = x1 - x0 - 44 - 34
    lines = None
    for px in (52, 46, 42):
        f = font(F_BLACK, px)
        lines = wrap2(f, text, maxw)
        if lines:
            break
    if not lines:              # 兩行放不下：42px 逐字換三行
        lines, cur = [], ""
        for ch in text:
            if tsize(f, cur + ch)[0] > maxw and cur:
                lines.append(cur)
                cur = ch
            else:
                cur += ch
        lines.append(cur)
    lh = int(px * 1.32)
    th = lh * len(lines) - (lh - px)
    y = (y0 + y1 - 10) / 2 - th / 2
    for s in lines:
        tw, tht, bb = tsize(f, s)
        x = x0 + 44
        d.text((x - bb[0], y - bb[1] + (px - tht) / 2), s, font=f, fill=TXT + (int(255 * a * ta),))
        reg.text_in("字幕字", (x, y, x + tw, y + px), (x0 + 12, y0, x1, y1 - 10), inset=8)
        y += lh


def disclaimer_card(ov, reg, a):
    x0, y0, x1, y1 = CARD
    d = ImageDraw.Draw(ov, "RGBA")
    f = font(F_BOLD, 38)
    lines = ["本內容為公開資料整理，", "不構成任何投資建議；", "投資有風險，請自行判斷。"]
    lh = 54
    th = lh * 3 - (lh - 38)
    y = (y0 + y1 - 10) / 2 - th / 2
    for s in lines:
        tw, tht, bb = tsize(f, s)
        x = x0 + 44
        d.text((x - bb[0], y - bb[1]), s, font=f, fill=TXT + (int(255 * a),))
        reg.text_in("免責字", (x, y, x + tw, y + tht), (x0 + 12, y0, x1, y1 - 10), inset=8)
        y += lh


def top_bar(ov, reg, idx, prog):
    d = ImageDraw.Draw(ov, "RGBA")
    f = font(F_BOLD, 30)
    s = "哩股哩股・比比知識"
    tw, th, bb = tsize(f, s)
    w, h = tw + 76, 56
    d.rounded_rectangle([40, 62, 40 + w, 62 + h], h // 2, fill=(18, 28, 42, 255), outline=TEAL + (200,), width=2)
    d.ellipse([60, 62 + h / 2 - 8, 76, 62 + h / 2 + 8], fill=ORANGE + (255,))
    d.text((90 - bb[0], 62 + (h - th) / 2 - bb[1]), s, font=f, fill=TXT + (255,))
    reg.add("品牌膠囊", (40, 62, 40 + w, 62 + h))
    reg.text_in("品牌膠囊字", (90, 62 + (h - th) / 2, 90 + tw, 62 + (h + th) / 2), (40, 62, 40 + w, 62 + h))
    if idx is not None:
        s2 = f"{idx + 1}／10"
        f2 = font(F_BOLD, 32)
        tw2, th2, bb2 = tsize(f2, s2)
        d.text((1040 - tw2 - bb2[0], 62 + (h - th2) / 2 - bb2[1]), s2, font=f2, fill=MUTED + (255,))
        reg.add("頁碼", (1040 - tw2, 62 + (h - th2) / 2, 1040, 62 + (h + th2) / 2))
    # 進度條：十格
    x0, x1, y0, y1 = 40, 1040, 140, 150
    gap = 8
    sw = (x1 - x0 - gap * 9) / 10
    for k in range(10):
        sx = x0 + k * (sw + gap)
        d.rounded_rectangle([sx, y0, sx + sw, y1], 5, fill=(40, 54, 72, 255))
        fill = clamp(prog - k)
        if fill > 0:
            col = tuple(int(lerp(TEAL[i], ORANGE[i], k / 9)) for i in range(3))
            d.rounded_rectangle([sx, y0, sx + max(10, sw * fill), y1], 5, fill=col + (255,))
    reg.add("進度條", (x0, y0, x1, y1))


def headline(ov, reg, text, hl, sub, a):
    if a <= 0:
        return
    d = ImageDraw.Draw(ov, "RGBA")
    f = font(F_BLACK, 74)
    tw, th, bb = tsize(f, text)
    x = (W - tw) / 2
    y = 176 + (1 - ease_out(a)) * 18
    if hl and hl in text:
        i = text.index(hl)
        pre = text[:i]
        d.text((x - bb[0], y - bb[1]), pre, font=f, fill=TXT + (int(255 * a),))
        xx = x + (f.getlength(pre) if pre else 0)
        d.text((xx - bb[0], y - bb[1]), hl, font=f, fill=ORANGE + (int(255 * a),))
        xx += f.getlength(hl)
        d.text((xx - bb[0], y - bb[1]), text[i + len(hl):], font=f, fill=TXT + (int(255 * a),))
    else:
        d.text((x - bb[0], y - bb[1]), text, font=f, fill=TXT + (int(255 * a),))
    reg.add("大字", (x, y, x + tw, y + th))
    reg.text_in("大字", (x, y, x + tw, y + th), (0, 0, W, H), inset=36)
    if sub:
        f2 = font(F_BOLD, 38)
        tw2, th2, bb2 = tsize(f2, sub)
        x2 = (W - tw2) / 2
        y2 = 286 + (1 - ease_out(a)) * 18
        d.text((x2 - bb2[0], y2 - bb2[1]), sub, font=f2, fill=TEAL + (int(255 * a),))
        reg.add("副標", (x2, y2, x2 + tw2, y2 + th2))
        reg.text_in("副標", (x2, y2, x2 + tw2, y2 + th2), (0, 0, W, H), inset=36)


def footer(ov, reg, line2, a2):
    d = ImageDraw.Draw(ov, "RGBA")
    f = font(F_MED, 26)
    ys = FOOT_Y
    boxes = []
    for s, al in ((FOOT1, 1.0), (line2, a2)):
        if not s or al <= 0:
            ys += 38
            continue
        tw, th, bb = tsize(f, s)
        x = (W - tw) / 2
        d.text((x - bb[0], ys - bb[1]), s, font=f, fill=DIM + (int(255 * al),))
        boxes.append((x, ys, x + tw, ys + th))
        reg.text_in("頁腳", (x, ys, x + tw, ys + th), (0, 0, W, H), inset=30)
        ys += 38
    if boxes:
        reg.add("頁腳", (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)))


def render(t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    background(c, t)
    reg = Reg()
    labels = Labels()
    g = Ctx(c, dy=math.sin(t * 1.7) * 6)
    cur = None
    for (sc, s0, s1) in SCENE_T:
        if s0 <= t < s1:
            cur = (sc, s0, s1)
    sc, s0, s1 = cur
    sid = sc[0]
    fin = 1.0 if s0 == 0 else clamp((t - s0) / 0.35)
    fout = clamp((s1 - t) / 0.3) if sid != "S10" else 1.0
    A = min(fin, fout)
    c.save()
    c.rectangle(G[0] - 30, G[1], G[2] - G[0] + 60, G[3] - G[1])
    c.clip()
    c.translate(0, g.dy)
    SCENE_FN[sid](g, labels, t, A)
    c.restore()
    if g.ext is not None:
        e = g.ext
        if e[0] < G[0] - 30 - 0.5 or e[1] < G[1] - 0.5 or e[2] > G[2] + 30 + 0.5 or e[3] > G[3] + 0.5:
            reg.text_issues.append(f"圖解超出圖解區 {tuple(int(v) for v in e)}")
    surf.flush()
    arr = np.ndarray((H, surf.get_stride() // 4, 4), np.uint8, surf.get_data())[:, :W]
    cv = Image.fromarray(np.ascontiguousarray(arr[..., [2, 1, 0]]), "RGB").convert("RGBA")
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    labels.draw(ov, reg, g)
    if g.ext is not None:
        e = g.ext
        reg.add("圖解", (max(e[0], 0), e[1], min(e[2], W), e[3]))
    idx = [x[0][0] for x in SCENE_T].index(sid)
    ln = LINES[sid]
    prog = idx + clamp((t - s0) / max(0.1, s1 - s0))
    top_bar(ov, reg, idx, prog)
    headline(ov, reg, sc[1], sc[2], sc[3], A)
    footer(ov, reg, sc[4], A)
    # 字幕卡：第一句開始前 0.15 秒出現，之後一直在（只換字）
    ca = clamp((t - (LINES["S01"].start - 0.3)) / 0.25)
    if t >= END_T:
        sub_card(ov, reg, "", ca, 0)
        disclaimer_card(ov, reg, clamp((t - END_T) / 0.3))
    else:
        txt, ta = "", 0.0
        for (s, a0, a1, sid2) in SUBS:
            if a0 - 0.05 <= t:
                txt, ta = s, clamp((t - a0 + 0.05) / 0.12)
        if t > ln.end and sid != "S10":
            ta *= clamp((s1 - 0.05 - t) / 0.2)
        sub_card(ov, reg, txt, ca, ta)
    cv.alpha_composite(ov)
    nm, bt = bibi_at(t)
    draw_bibi(cv, reg, nm, bt)
    return cv.convert("RGB"), reg


# ───────────────────────── 封面 ─────────────────────────
def make_cover(path):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(surf)
    background(c, 0.0)
    g = Ctx(c)
    pr = Proj("iso", 540, 980, 1.05)
    package(g, pr, 0.4, 1.0, flow=1.0)
    surf.flush()
    arr = np.ndarray((H, surf.get_stride() // 4, 4), np.uint8, surf.get_data())[:, :W]
    cv = Image.fromarray(np.ascontiguousarray(arr[..., [2, 1, 0]]), "RGB").convert("RGBA")
    reg = Reg()
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    top_bar(ov, reg, None, 0)
    d = ImageDraw.Draw(ov, "RGBA")
    items = [("AI 晶片", font(F_BLACK, 150), TXT, 230), ("為什麼需要", font(F_BLACK, 110), TXT, 420),
             ("HBM？", font(F_BLACK, 220), ORANGE, 570)]
    for k, (s, f, col, y) in enumerate(items):
        tw, th, bb = tsize(f, s)
        x = (W - tw) / 2
        d.text((x - bb[0], y - bb[1]), s, font=f, fill=col + (255,))
        reg.add(f"封面字{k + 1}", (x, y, x + tw, y + th))
        reg.text_in(f"封面字{k + 1}", (x, y, x + tw, y + th), (0, 0, W, H), inset=36)
    f = font(F_BOLD, 52)
    s = "高頻寬記憶體・一分鐘看懂"
    tw, th, bb = tsize(f, s)
    x, y = (W - tw) / 2, 1500
    d.rounded_rectangle([x - 34, y - 20, x + tw + 34, y + th + 24], 36, fill=(22, 34, 50, 240))
    d.text((x - bb[0], y - bb[1]), s, font=f, fill=TEAL + (255,))
    reg.add("封面副標", (x - 34, y - 20, x + tw + 34, y + th + 24))
    reg.add("封面圖", g.ext)
    cv.alpha_composite(ov)
    fr = bibi_frames("face_thumbs")
    im = fr[len(fr) // 2]
    ox, oy = 700, 1560
    cv.alpha_composite(im, (ox, oy))
    b = bibi_bbox("face_thumbs", len(fr) // 2)
    reg.add("比比", (ox + b[0], oy + b[1], ox + b[2], oy + b[3]))
    cv.convert("RGB").save(path)
    return reg


# ───────────────────────── 混音、字幕檔 ─────────────────────────
def mix_audio(out_wav):
    SR = 44100
    n = int(TOTAL * SR) + SR
    voice = np.zeros(n, np.float32)
    speak = np.zeros(n, np.float32)
    for lid, ln in LINES.items():
        a = ln.audio
        if ln.sr != SR:
            idx = np.arange(0, len(a) * SR / ln.sr) * ln.sr / SR
            a = np.interp(idx, np.arange(len(a)), a).astype(np.float32)
        s = int((ln.start - ln.on) * SR)
        if s < 0:
            a, s = a[-s:], 0
        e = min(n, s + len(a))
        voice[s:e] += a[:e - s]
        speak[int(ln.start * SR):int(ln.end * SR)] = 1.0
    voice *= 0.89 / (np.max(np.abs(voice)) + 1e-9)
    bgm_p = SCR / "bgm.wav"
    subprocess.run([sys.executable, str(REPO / "docs/marketing/videos/2026-10-18-cowos_bibi/make_bgm_cowos.py"), str(bgm_p), f"{TOTAL + 0.5:.2f}"], check=True)
    with wave.open(str(bgm_p)) as w:
        b = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32).reshape(-1, 2) / 32768
    b = b[:n] if len(b) >= n else np.vstack([b, np.zeros((n - len(b), 2), np.float32)])
    k = int(0.25 * SR)
    env = np.convolve(speak, np.ones(k) / k, mode="same")
    gain = 0.20 - 0.135 * np.clip(env * 1.5, 0, 1)        # 很輕的底樂：講話時 0.065、沒講話 0.20
    outp = b * gain[:, None] + voice[:, None]
    outp = np.clip(outp[:int(TOTAL * SR)], -0.99, 0.99)
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((outp * 32767).astype(np.int16).tobytes())


def ts(x):
    ms = int(round(x * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_srt(path):
    out = []
    for i, (s, a, b, _sid) in enumerate(SUBS, 1):
        out += [str(i), f"{ts(a)} --> {ts(b)}", s, ""]
    out += [str(len(SUBS) + 1), f"{ts(END_T)} --> {ts(TOTAL)}", DISCLAIMER, ""]
    Path(path).write_text("\n".join(out), encoding="utf-8")


GRAPHIC_DESC = {
    "S01": "等角 2.5D 封裝（基板＋中介層＋GPU）；講到「運算單元」藍色長條長高；講到「記憶體頻寬」紅色短條＋「瓶頸」標籤；講到 HBM 時四疊 HBM 一層層落到 GPU 旁，頻寬條轉青綠長高「HBM 補上頻寬」",
    "S02": "等角大圖：DRAM 晶粒一層層出現（先分開）→「垂直堆疊」壓實 →「矽穿孔」金色 TSV 通道由下往上亮 →「底部」基底晶片 →「整疊」中介層＋封裝基板 →「與 GPU」GPU 落下＋資料光點 →「2.5D」金色標籤；左側一欄引線標註",
    "S03": "斜視 2.5D：左記憶體堆疊、右 GPU，中間通道上資料方塊流動；「運算速度」GPU 發光；「如果」通道中段變窄、資料在窄口前排隊；GPU 忙碌程度條由全速掉到閒置；「這就是」通道兩側長出磚牆；「記憶體牆（Memory Wall）」紅色標籤",
    "S04": "上半：2.5D 介面通道，寬度依位元數同比例（DDR5 模組 64 位元 vs HBM 每疊 1024 位元，細線＝每 64 位元，光點流動）＋「通道寬 16 倍」；下半：四列 2.5D 比較方塊（頻寬、每位元傳輸功耗、成本、容量擴充），青＝優點、橘＝代價",
    "S05": "斜視 2.5D 直條：HBM1 128 GB/s（2013、4 層）→ HBM2 256 → HBM3 819（2022、8 層）→ HBM3E 約 1.2 TB/s（2024、8～12 層）→ HBM4 約 2 TB/s（標準，2026 量產、12 層，虛線半透明）；金色弧線「約第一代的 9 倍以上」；「HBM4：介面加寬到 2048 位元」標籤",
    "S06": "三個等角場景依序浮出：AI 加速器（機櫃）、雲端資料中心（機櫃群）、高效能運算（晶片＋散熱鰭片）；「這些場景」中央 HBM 堆疊＋虛線連到三者，「頻寬需求遠高於一般運算」",
    "S07": "四步驟等角小圖由上而下：① DRAM 堆疊（記憶體廠：堆疊與出廠測試）② 晶圓＋基底晶片（HBM4 起部分交由晶圓代工）③ 中介層上 GPU＋HBM（先進封裝）④ 晶片＋綠色勾（封測廠最終測試）；公司名只在灰色小字「例：」",
    "S08": "2×2 等角卡：良率控制（12 層堆疊微晃＋紅光）、成本（金幣堆）、產能（廠房＋滿載燈號）、散熱（晶片紅光＋熱浪）",
    "S09": "紫色 2.5D 厚板「HBM ＝ 垂直堆疊 ＋ 超寬介面／AI 系統效能的關鍵元件」；下方 HBM→GPU 道路由 2 線道加寬到 6 線道、資料方塊流動，「介面越寬 ＝ 車道越多」「頻寬決定 AI 系統效能上限」",
    "S10": "CoWoS 樣式封裝等角圖緩慢漂浮＋光澤掃過；「下一集」標籤＋「CoWoS 先進封裝」；「搜尋」時 2.5D 橘色按鈕「搜尋「哩股哩股」」；配音結束後字幕卡換成免責聲明停 3.8 秒",
}


def write_storyboard(path):
    out = ["# 分鏡表：AI 晶片的瓶頸在哪？HBM（直式 1080×1920、30fps）", "",
           f"- 片長 {TOTAL:.2f} 秒；時間軸由 MeloTTS 配音長度決定（`render_hbm.py` 自動產生本表）。",
           "- 版面固定：上方品牌膠囊＋頁碼＋十格進度條；大字＋副標；圖解區直接畫在深色底（不加框）；左下比比（不說話、不出泡泡）＋右下字幕卡；頁腳「非投資建議｜數字為公開規格或推估」＋各段資料說明。", ""]
    for (sc, s0, s1) in SCENE_T:
        sid = sc[0]
        ln = LINES[sid]
        acts = [f"{a:.1f}s {n}" for (a, b, n, _s) in ACT_TL if a < s1 and b > s0]
        subs = [x[0] for x in SUBS if x[3] == sid]
        out += [f"## {sid}　{s0:.2f}–{s1:.2f} 秒（配音 {ln.start:.2f}–{ln.end:.2f}）", "",
                f"- 大字：{sc[1]}（橘字：{sc[2]}）／副標：{sc[3]}",
                f"- 圖：{GRAPHIC_DESC[sid]}",
                f"- 比比：{'、'.join(acts)}",
                f"- 配音：{ln.text}",
                f"- 字幕卡：{' ／ '.join(subs)}",
                f"- 頁腳第二行：{sc[4]}", ""]
    out += [f"## 片尾　{END_T:.2f}–{TOTAL:.2f} 秒", "", f"- 字幕卡換成免責：{DISCLAIMER}（停 {TOTAL - END_T:.1f} 秒）；比比 face_bow → wave。", ""]
    Path(path).write_text("\n".join(out), encoding="utf-8")


# ───────────────────────── 主程式 ─────────────────────────
def _work(i):
    t = i / FPS
    im, reg = render(t)
    return i, im.tobytes(), reg.overlaps(), reg.text_issues


def main():
    ap_ = argparse.ArgumentParser()
    ap_.add_argument("--out", default=str(HERE / f"{OUT_BASE}.mp4"))
    ap_.add_argument("--frames", default="")
    ap_.add_argument("--cover", action="store_true")
    ap_.add_argument("--workers", type=int, default=4)
    a = ap_.parse_args()
    SCR.mkdir(parents=True, exist_ok=True)
    build_timeline()
    print(f"片長 {TOTAL:.2f} 秒", file=sys.stderr)
    for (sc, s0, s1) in SCENE_T:
        ln = LINES[sc[0]]
        print(f"  {sc[0]} {s0:6.2f}–{s1:6.2f}  配音 {ln.start:6.2f}–{ln.end:6.2f}", file=sys.stderr)
    if a.cover:
        reg = make_cover(HERE / "hbm_bibi_cover.png")
        print("封面 重疊", reg.overlaps(), "出框", reg.text_issues)
        return
    if a.frames:
        for s in a.frames.split(","):
            im, reg = render(float(s))
            p = SCR / f"f_{float(s):06.2f}.png"
            im.save(p)
            print(p, bibi_at(float(s))[0], reg.overlaps(), reg.text_issues)
        return
    n = int(round(TOTAL * FPS))
    tmp = SCR / "silent.mp4"
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
                           "-pix_fmt", "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    rows, issues = [], []
    samp = SCR / "samples"
    samp.mkdir(exist_ok=True)
    for old in samp.glob("*.png"):
        old.unlink()
    with mp.get_context("fork").Pool(a.workers) as pool:
        for i, buf, ovl, iss in pool.imap(_work, range(n), chunksize=4):
            t = i / FPS
            ff.stdin.write(buf)
            for (x, y, area) in ovl:
                rows.append(f"| {t:6.2f} | {x} | {y} | {area} |")
            for s in iss:
                issues.append(f"| {t:6.2f} | {s} |")
            if i % 15 == 0:  # 每 0.5 秒存一張抽格（人工檢查用）
                Image.frombytes("RGB", (W, H), buf).save(samp / f"s_{t:05.1f}.png")
            if i % 300 == 0:
                print(f"{t:5.1f}s", file=sys.stderr)
    ff.stdin.close()
    ff.wait()
    rep = ["# 重疊檢查報告（render_hbm.py 每一幀自動產生）", "",
           f"- 片長 {TOTAL:.2f} 秒；總幀數 {n}（30fps）；每個外框外擴 {PAD}px 後兩兩比對。",
           "- 登記的元素：品牌膠囊、頁碼、進度條、大字、副標、圖解（cairo 實際畫到的範圍＋所有圖解文字）、字幕卡、比比（每一幀實際不透明外框）、頁腳。",
           "- 另外檢查：圖解文字不出圖解區、字幕字不出字幕卡、大字／副標／頁腳不出畫面安全邊、圖解不超出圖解區。",
           f"- 重疊：**{len(rows)} 筆**", f"- 出框：**{len(issues)} 筆**", ""]
    if rows:
        rep += ["| 秒 | 元素 A | 元素 B | 相交面積 |", "|---|---|---|---|"] + rows[:400]
    if issues:
        rep += ["", "| 秒 | 問題 |", "|---|---|"] + issues[:400]
    (HERE / "overlap_report.md").write_text("\n".join(rep) + "\n", encoding="utf-8")
    print("重疊", len(rows), "出框", len(issues), "幀", n)
    wav = SCR / "mix.wav"
    mix_audio(wav)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), "-i", str(wav), "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "160k", "-shortest", "-movflags", "+faststart", a.out], check=True)
    write_srt(HERE / f"{OUT_BASE}.srt")
    write_storyboard(HERE / "storyboard.md")
    (SCR / "timeline.json").write_text(json.dumps({"total": TOTAL, "end_t": END_T, "acts": ACT_TL, "subs": SUBS,
                                                   "scenes": [(s[0][0], s[1], s[2]) for s in SCENE_T],
                                                   "lines": {k: [v.start, v.end] for k, v in LINES.items()}},
                                                  ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
