"""短影音「CoWoS 為什麼缺貨？」比比主持版渲染器（直式 1080×1920、30fps、PIL 逐格算圖＋ffmpeg，不掉格）。

沿用 2026-10-17-k_cpo/render_cpo.py 的架構（逐格算圖、比比素材從 docs/anim/bibi_library/ 取、每幀登記外框
做重疊檢查、自製配樂），這一版的差別：
  · 比比是主持人（身體約 300px 寬，畫面下方左側），配音逐句播放，說話時用 talk_*，講到數字用 point_ur／wow，
    開場 intro、片尾 face_bow；每段動作不超過 3 秒就換。
  · 台詞泡泡＝字幕：跟配音逐字時間軸對時（edge-tts 的 WordBoundary），一次一小句。
  · 時間軸由配音長度決定（voice/<聲音>/Lxx.json），不是寫死秒數。

版面（四條帶，彼此不相交；layout_rules.md）：
  上 110–300：段落膠囊（左）、角標（右）、大字
  中 340–1236：內容框（開場大字／示意圖／重點卡＋直條圖／甜甜圈／供應鏈分段／網站實際畫面）
  下 1243–1700：比比（左，腳底 x200,y1700）＋台詞泡泡（右，尾巴只指向比比）
  底 1740–1830：小字（來源／示意說明／網站實際畫面・資料日）

用法（repo 根目錄）：
    python docs/marketing/videos/2026-10-18-cowos_bibi/render_cowos.py              # 出片＋overlap_report.md＋srt＋封面
    python docs/marketing/videos/2026-10-18-cowos_bibi/render_cowos.py --frames 3,12.5   # 只輸出這幾秒的單格
環境變數 COWOS_SCR：中間產物（網站錄影、抽格、配樂）所在的 scratchpad；COWOS_VOICE：用哪個聲音（預設 hsiaoyu_cute）。
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

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
LIB = REPO / "docs" / "anim" / "bibi_library"
SCR = Path(os.environ.get("COWOS_SCR", "/tmp/claude-0/-home-user-tw-rotation/09911d5e-cbec-5eb0-a188-19f18707f268/scratchpad/video_cowos"))
FD = Path(os.environ.get("COWOS_FONT_DIR", "/tmp/claude-0/-home-user-tw-rotation/09911d5e-cbec-5eb0-a188-19f18707f268/scratchpad/video_cpo/font"))
F_ROUND = str(FD / "h/package/400Regular/Huninn_400Regular.ttf")       # 粉圓（Huninn，OFL）
F_BOLD = str(FD / "n/package/700Bold/NotoSansTC_700Bold.ttf")
F_BLACK = str(FD / "n/package/900Black/NotoSansTC_900Black.ttf")
F_MED = str(FD / "n/package/500Medium/NotoSansTC_500Medium.ttf")
LOGO = REPO / "site" / "brand" / "src" / "logo_1009.jpg"
VOICE = os.environ.get("COWOS_VOICE", "hsiaoyu_cute")
VDIR = HERE / "voice" / VOICE
OUT_BASE = "cowos_bibi_9x16"

W, H, FPS = 1080, 1920, 30

SKY = (42, 166, 245)
DEEP = (27, 111, 224)
LEMON = (255, 212, 59)
CREAM = (255, 249, 239)
INK = (26, 26, 26)
GREY = (96, 104, 116)
WHITE = (255, 255, 255)
CORAL = (232, 93, 74)
# 圖表配色跟網站一致（site/theme4.css「科技 HUD・淺」：--cat-1 青藍、--cat-2 紫、--cat-other 灰）
CAT1 = (10, 106, 134)
CAT2 = (81, 69, 200)
CAT_OTHER = (200, 208, 216)
AMBER = (143, 86, 0)

CONTENT = (40, 340, 1040, 1236)
BIBI_FOOT = (200, 1700)
BIBI_SIZE = 560
BUBBLE_Y = (1330, 1676)
FOOT_Y = 1742
PAD = 6


# ───────────────────────── 小工具 ─────────────────────────
@lru_cache(maxsize=96)
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


def paste_alpha(cv, im, xy, a):
    if a <= 0:
        return
    if a < 1:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    cv.alpha_composite(im, (int(round(xy[0])), int(round(xy[1]))))


def mix(c, a):
    """顏色 c 以透明度 a 疊在白底上（畫在不透明卡片內的淡入用）。"""
    return tuple(int(lerp(255, v, a)) for v in c)


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


# ───────────────────────── 配音時間軸 ─────────────────────────
LINE_IDS = [f"L{i:02d}" for i in range(1, 16)]
SCENES = [
    # (id, 句子, 膠囊, 大字, 黃底字, 角標, 底部小字)
    ("hook", ["L01", "L02"], "比比知識", "CoWoS 一分鐘看懂", "CoWoS", None,
     ["資料來源：台積電法說會、法人與研調報告（見貼文）"]),
    ("what", ["L03", "L04", "L05"], "重點 1／5", "什麼是 CoWoS？", "CoWoS", "示意圖",
     ["示意圖：簡化結構，非實際比例"]),
    ("why", ["L06", "L07"], "重點 2／5", "為什麼會缺？", "缺", "示意圖",
     ["示意圖：顆數只是示意，不是實際數字"]),
    ("cap", ["L08", "L09", "L10"], "重點 3／5", "產能擴多快？", "擴多快", None,
     ["法說會：台積電 2024-10-17；月產能為法人估計", "大摩、TrendForce、優分析（2026 年報導）"]),
    ("who", ["L11"], "重點 4／5", "產能給誰？", "給誰", None,
     ["大摩估計（2026 年產能分配），非公司公布"]),
    ("chain", ["L12", "L13"], "重點 5／5", "台灣供應鏈分幾段？", "分幾段", None,
     ["依公開報導整理環節分工，不列個別公司"]),
    ("site", ["L14"], "哩股哩股網站", "想看更多？", "更多", "網站實際畫面", None),
    ("end", ["L15"], None, None, None, None, None),
]
GAP_LINE, GAP_SCENE, T0 = 0.18, 0.45, 0.40
END_HOLD = 3.3          # 片尾免責至少停 3 秒（endcard 從 L15 前 0.3 秒開始）

# 每句的比比動作：(錨點字串, 素材)。錨點字串第一個字被唸到時換動作；"" ＝句子開始。
ACTS = {
    "L01": [("", "intro"), ("AI", "talk_excited")],
    "L02": [("", "talk_explain"), ("封裝", "point_ur")],
    "L03": [("", "talk_happy"), ("先進封裝", "point_ur")],
    "L04": [("", "talk_explain"), ("HBM", "point_ur"), ("矽中介層", "talk_happy"), ("基板", "point_ur")],
    "L05": [("", "talk_excited"), ("省電", "face_thinking_bulb")],
    "L06": [("", "talk_explain"), ("越放越多", "face_shock")],
    "L07": [("", "magnifier"), ("需求", "face_sweat")],
    "L08": [("", "talk_explain"), ("翻倍", "wow"), ("供不應求", "talk_happy")],
    "L09": [("", "talk_explain"), ("7", "point_ur"), ("12", "wow")],
    "L10": [("", "talk_excited"), ("18", "point_ur")],
    "L11": [("", "face_think"), ("大摩", "talk_explain"), ("六成", "point_ur")],
    "L12": [("", "talk_happy")],
    "L13": [("", "talk_explain"), ("封測廠", "point_ur"), ("設備", "face_nod")],
    "L14": [("", "talk_happy"), ("CoWoS", "point_ur"), ("看看", "face_wink")],
    "L15": [("", "face_bow")],
}
# 同一動作超過 3 秒就換成另一個（每 3 秒至少換一次表情或動作）
ALT = {"talk_explain": "talk_happy", "talk_happy": "talk_excited", "talk_excited": "talk_explain",
       "point_ur": "talk_explain", "face_bow": "wave", "wave": "face_bow", "face_nod": "talk_happy",
       "face_wink": "talk_happy", "wow": "talk_excited", "face_think": "talk_explain",
       "magnifier": "talk_explain", "face_sweat": "talk_explain", "face_shock": "talk_explain",
       "face_thinking_bulb": "talk_happy", "intro": "talk_happy"}
LIB_ONCE = {"intro"}          # 只播一次（不循環）的素材


class Line:
    def __init__(self, lid):
        d = json.loads((VDIR / f"{lid}.json").read_text(encoding="utf-8"))
        self.id = lid
        self.text = d["text"]
        self.words = [w for w in d["words"] if w["type"] == "WordBoundary"]
        self.w0 = self.words[0]["start"]
        self.speech = self.words[-1]["start"] + self.words[-1]["dur"] - self.w0
        self.start = 0.0            # 影片時間（第一個字開始唸）
        self.char_t = self._char_times()

    def _char_times(self):
        """每個字元被唸到的時間（相對句子開始）。標點跟著前一個字。"""
        txt = self.text
        times = [None] * len(txt)
        pos = 0
        for w in self.words:
            k = txt.find(w["text"], pos)
            if k < 0:
                k = txt.lower().find(w["text"].lower(), pos)
            if k < 0:
                continue
            n = len(w["text"])
            for j in range(n):
                times[k + j] = w["start"] - self.w0 + w["dur"] * j / max(1, n)
            pos = k + n
        last = 0.0
        for i, v in enumerate(times):
            if v is None:
                times[i] = last
            else:
                last = v
        return times

    @property
    def end(self):
        return self.start + self.speech

    def at(self, anchor):
        if not anchor:
            return self.start
        k = self.text.find(anchor)
        return self.start + (self.char_t[k] if k >= 0 else 0.0)

    def chunks(self):
        """字幕小句：以標點切，太短的併到下一句，每句 ≤ 18 字。回傳 [(顯示文字, 起, 訖)]。"""
        parts = re.findall(r"[^，。！？：]+[，。！？：]?", self.text)
        merged = []
        for p in parts:
            if merged and (len(merged[-1].strip("，。、：")) < 6) and len(merged[-1]) + len(p) <= 18:
                merged[-1] += p
            else:
                merged.append(p)
        starts, pos = set(), 0
        for w in self.words:            # 詞界（字元位置）
            k = self.text.find(w["text"], pos)
            if k >= 0:
                starts.add(k)
                pos = k + len(w["text"])
        out, pos = [], 0
        for p in merged:
            k = self.text.find(p, pos)
            pos = k + len(p)
            out.append([p, self.start + self.char_t[k], None, k])
        for i in range(len(out)):
            out[i][2] = out[i + 1][1] if i + 1 < len(out) else self.end + 0.1
            raw = out[i][0]
            lead = len(raw) - len(raw.lstrip())
            s = raw.strip()
            s = s.rstrip("，、：。") if not s.endswith(("？", "！")) else s
            k0 = out[i][3] + lead
            BREAKS[s] = {j - k0 for j in starts if 0 < j - k0 < len(s)}
            out[i][0] = s
        return [tuple(x[:3]) for x in out]


LINES: dict[str, Line] = {}
SCENE_T: list[tuple] = []        # (scene, 起, 訖)
TOTAL = 0.0
ACT_TL: list[tuple] = []         # (起, 訖, 素材, 素材自己的起點)
SUBS: list[tuple] = []           # (文字, 起, 訖, scene id)


def build_timeline():
    global TOTAL
    t = T0
    for si, sc in enumerate(SCENES):
        for k, lid in enumerate(sc[1]):
            ln = Line(lid)
            LINES[lid] = ln
            if k:
                t += GAP_LINE
            ln.start = t
            t = ln.end
        t += GAP_SCENE
    # 段落起訖：內容提早 0.35 秒進場；段尾＝下一段起點
    starts = []
    for i, sc in enumerate(SCENES):
        if i == 0:
            starts.append(0.0)
            continue
        prev_end = LINES[SCENES[i - 1][1][-1]].end
        starts.append(max(prev_end + 0.2, LINES[sc[1][0]].start - 0.35))   # 上一句講完才換段
    last = LINES["L15"]
    TOTAL = round((last.start - 0.3 + END_HOLD + 0.1) * FPS) / FPS
    TOTAL = max(TOTAL, last.end + 1.0)
    for i, sc in enumerate(SCENES):
        e = starts[i + 1] if i + 1 < len(SCENES) else TOTAL
        SCENE_T.append((sc, starts[i], e))
    # 比比動作時間軸
    raw = []
    for lid in LINE_IDS:
        ln = LINES[lid]
        for anchor, name in ACTS[lid]:
            st = 0.15 if (lid == "L01" and not anchor) else ln.at(anchor)
            raw.append((st, name))
    raw.sort()
    segs = []
    for i, (st, name) in enumerate(raw):
        en = raw[i + 1][0] if i + 1 < len(raw) else TOTAL
        if name == "intro":
            en = min(en, st + 2.07)
            if i + 1 < len(raw) and raw[i + 1][0] > en:
                segs.append((st, en, name, st))
                segs.append((en, raw[i + 1][0], "talk_happy", en))
                continue
        segs.append((st, en, name, st))
    # 開頭 0～0.15 秒：intro 第一格
    segs.insert(0, (0.0, segs[0][0], segs[0][2], 0.0))
    # 超過 3 秒的段落切開交替
    for (a, b, n, s0) in segs:
        while b - a > 3.0:
            m = a + min(2.6, (b - a) / 2)
            ACT_TL.append((a, m, n, s0))
            a, n = m, ALT.get(n, "talk_happy")
            s0 = a
        ACT_TL.append((a, b, n, s0))
    for sc in SCENES:
        for lid in sc[1]:
            for c in LINES[lid].chunks():
                SUBS.append((c[0], c[1], c[2], sc[0]))


def bibi_at(t):
    for a, b, n, s0 in ACT_TL:
        if a <= t < b:
            return n, t - s0
    a, b, n, s0 = ACT_TL[-1]
    return n, t - s0


def acts_between(t0, t1):
    return sorted({n for (a, b, n, _s) in ACT_TL if a < t1 and b > t0})


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
    n = len(bibi_frames(name))
    L = lib_lengths().get(name, (n, 1.0))[1]
    if name in LIB_ONCE:
        return min(n - 1, int(max(0.0, t) / L * n))
    return int((t % L) / L * n) % n


def draw_bibi(cv, reg, name, t, size=BIBI_SIZE, foot=BIBI_FOOT):
    i = frame_idx(name, t)
    sp = bibi_scaled(name, i, size)
    ox, oy = bibi_origin(size, foot)
    cv.alpha_composite(sp, (ox, oy))
    b = bibi_bbox(name, i, size)
    reg.add("比比", (ox + b[0], oy + b[1], ox + b[2], oy + b[3]))


def bibi_right(names):
    bs = [bibi_union(n, BIBI_SIZE) for n in names]
    b = (min(x[0] for x in bs), min(x[1] for x in bs), max(x[2] for x in bs), max(x[3] for x in bs))
    ox, oy = bibi_origin(BIBI_SIZE)
    return ox + b[2], oy + b[1], oy + b[3]


# ───────────────────────── 元件 ─────────────────────────
def pill(cv, reg, text, x, y, a, bg=SKY, fg=WHITE, px=34, name="段落膠囊", right=False):
    if a <= 0:
        return
    f = font(F_ROUND, px)
    tw, th, bb = tsize(f, text)
    w, h = tw + 44, px + 26
    if right:
        x = x - w
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    im.paste(bg + (255,), (0, 0), rmask(w, h, h // 2))
    ImageDraw.Draw(im).text((22 - bb[0], (h - th) / 2 - bb[1]), text, font=f, fill=fg)
    s = 0.85 + 0.15 * back_out(a)
    im2 = im.resize((max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS) if s != 1 else im
    x2, y2 = x + (w - im2.width) / 2, y + (h - im2.height) / 2
    paste_alpha(cv, im2, (x2, y2), a)
    reg.add(name, (x2, y2, x2 + im2.width, y2 + im2.height))
    reg.text_in(name, (x + 22, y + (h - th) / 2, x + 22 + tw, y + (h - th) / 2 + th), (x, y, x + w, y + h))


def headline(cv, reg, text, y, a, px=76, color=INK, hl=None):
    if a <= 0:
        return
    f = font(F_ROUND, px)
    tw, th, bb = tsize(f, text)
    x = (W - tw) / 2
    dy = (1 - ease_out(a)) * 24
    im = Image.new("RGBA", (W, th + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if hl and hl in text:
        i = text.index(hl)
        pre = tsize(f, text[:i])[0] if i else 0
        hw = tsize(f, hl)[0]
        d.rounded_rectangle([x + pre - 6, th * 0.62 + 10, x + pre + hw + 6, th + 18], 10, fill=LEMON + (255,))
    d.text((x - bb[0], 10 - bb[1]), text, font=f, fill=color)
    paste_alpha(cv, im, (0, y + dy - 10), a)
    reg.add("大字", (x - 6, y + dy, x + tw + 6, y + dy + th + 10))
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
        ImageDraw.Draw(im).text((-bb[0], 6 - bb[1]), ln, font=f, fill=GREY)
        paste_alpha(cv, im, (x, y), a)
        reg.text_in("底部小字", (x, y, x + tw, y + 40), (0, 0, W, H), inset=30)
        x0s.append(x)
        x1s.append(x + tw)
        y += 42
    reg.add("底部小字", (min(x0s), FOOT_Y, max(x1s), y))


BREAKS: dict[str, set] = {}      # 字幕文字 → 可以換行的位置（配音逐字時間軸的詞界，不會把「什麼」拆開）


def wrap(f, text, maxw):
    ok = BREAKS.get(text)
    if tsize(f, text)[0] <= maxw:
        return [text]
    n = len(text)
    best = None
    # 先試兩行、不夠再試三行；只在詞界斷，越平均越好
    cands = sorted(ok) if ok else list(range(1, n))
    for k in cands:
        if not (0 < k < n) or text[k] in "，。！？：、）」得的了":
            continue
        a_, b_ = text[:k].rstrip(" ，、"), text[k:].lstrip()
        if tsize(f, a_)[0] <= maxw and tsize(f, b_)[0] <= maxw:
            sc = abs(tsize(f, a_)[0] - tsize(f, b_)[0])
            if best is None or sc < best[0]:
                best = (sc, [a_, b_])
    if best:
        return best[1]
    for i in cands:
        for j in cands:
            if not (0 < i < j < n):
                continue
            parts = [text[:i].rstrip(), text[i:j].strip(), text[j:].lstrip()]
            if all(tsize(f, x)[0] <= maxw for x in parts):
                ws = [tsize(f, x)[0] for x in parts]
                sc = max(ws) - min(ws)
                if best is None or sc < best[0]:
                    best = (sc, parts)
    if best:
        return best[1]
    lines, cur = [], ""
    for ch in text:
        if tsize(f, cur + ch)[0] > maxw and cur:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    return lines + ([cur] if cur else [])


def bubble(cv, reg, text, a, names, ta=1.0, px=50, all_texts=()):
    """台詞泡泡：本體＋尾巴同一個遮罩（單一封閉路徑、同一條描邊），尾巴尖端離比比外框 13px、只指向比比。
    泡泡位置與大小整段固定（只有文字換），ta＝文字的淡入。"""
    if a <= 0:
        return
    br, by0, by1 = bibi_right(names)
    tip_x = br + 13
    tail = 50
    bx0 = tip_x + tail
    bx1 = 1040
    padx, pady = 36, 28
    f = font(F_ROUND, px)
    lh = int(px * 1.34)
    lines = wrap(f, text, bx1 - bx0 - padx * 2 - 8) if text else []
    th = lh * len(lines) - (lh - px) if lines else 0
    # 泡泡高度：整段固定，取這一段所有字幕裡最多的行數（不會句句變大小）
    nmax = max([len(wrap(f, x, bx1 - bx0 - padx * 2 - 8)) for x in all_texts] + [len(lines), 1])
    bh = lh * nmax - (lh - px) + pady * 2 + 24
    cyb = 1545
    ty0, ty1 = cyb - bh / 2, cyb + bh / 2
    tip_y = clamp((ty0 + ty1) / 2 + 40, by0 + 80, by1 - 50)
    ox, oy = tip_x - 8, ty0 - 8
    mw, mh = int(bx1 - ox + 10), int(bh + 18)
    m = Image.new("L", (mw, mh), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([bx0 - ox, ty0 - oy, bx1 - ox, ty1 - oy], 36, fill=255)
    root_y = clamp(tip_y, ty0 + 50, ty1 - 50)
    d.polygon([(bx0 - ox + 26, root_y - oy - 30), (tip_x - ox, tip_y - oy), (bx0 - ox + 26, root_y - oy + 24)], fill=255)
    outline = m.filter(ImageFilter.MaxFilter(7))
    im = Image.new("RGBA", (mw, mh), (0, 0, 0, 0))
    im.paste(DEEP + (255,), (0, 0), outline)
    im.paste(WHITE + (255,), (0, 0), m)
    s = 0.9 + 0.1 * back_out(a)
    if s != 1:
        im = im.resize((max(1, int(mw * s)), max(1, int(mh * s))), Image.LANCZOS)
    px0 = tip_x + (ox - tip_x) * s
    py0 = tip_y + (oy - tip_y) * s
    paste_alpha(cv, im, (px0, py0), a)
    tx = lambda x: tip_x + (x - tip_x) * s  # noqa: E731
    ty = lambda y: tip_y + (y - tip_y) * s  # noqa: E731
    reg.add("泡泡", (tx(bx0) - 3, ty(ty0) - 3, tx(bx1) + 3, ty(ty1) + 3), group="泡泡")
    reg.add("泡泡尾巴", (tx(tip_x), ty(root_y - 30) - 3, tx(bx0 + 26), ty(root_y + 24) + 3), group="泡泡")
    if lines and ta > 0 and s > 0.999:
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dd = ImageDraw.Draw(lay)
        y = (ty0 + ty1) / 2 - th / 2
        tws = [tsize(f, ln)[0] for ln in lines]
        for ln, w_ in zip(lines, tws):
            bb = f.getbbox(ln)
            x = (bx0 + bx1 - w_) / 2
            dd.text((x - bb[0], y - bb[1] + (px - (bb[3] - bb[1])) / 2), ln, font=f, fill=INK)
            y += lh
        paste_alpha(cv, lay, (0, 0), a * ta)
        tw = max(tws)
        tb = ((bx0 + bx1 - tw) / 2, (ty0 + ty1) / 2 - th / 2, (bx0 + bx1 + tw) / 2, (ty0 + ty1) / 2 + th / 2)
        reg.text_in("泡泡文字", tb, (bx0, ty0, bx1, ty1), inset=14)
        if tb[0] - (bx0 + 26) < 10:
            reg.text_issues.append("泡泡尾巴離文字<10px")
    if tip_x - br < 12 or tip_x - br > 14:
        reg.text_issues.append(f"尾巴尖端離比比 {tip_x - br}px（應 12～14）")


def panel(w, h, bg=(250, 252, 255), edge=(190, 204, 222)):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([2, 2, w - 3, h - 3], 30, fill=bg + (255,), outline=edge + (255,), width=4)
    return im, d


def text_at(d, reg, cname, xy, s, f, fill, origin, cbox_local, anchor="la"):
    tw, th, bb = tsize(f, s)
    x, y = xy
    if anchor == "ma":
        x = x - tw / 2
    elif anchor == "ra":
        x = x - tw
    d.text((x - bb[0], y - bb[1]), s, font=f, fill=fill)
    ox, oy = origin
    c0, c1, c2, c3 = cbox_local
    reg.text_in(cname, (ox + x, oy + y, ox + x + tw, oy + y + th), (ox + c0, oy + c1, ox + c2, oy + c3), inset=0)
    return tw, th


def chip_tag(d, reg, xy, s, f, fg, bg, org, cb, anchor="la"):
    tw, th, bb = tsize(f, s)
    x, y = xy
    if anchor == "ra":
        x -= tw + 32
    elif anchor == "ma":
        x -= (tw + 32) / 2
    d.rounded_rectangle([x, y, x + tw + 32, y + th + 22], 18, fill=bg)
    text_at(d, reg, "標籤字", (x + 16, y + 11), s, f, fg, org, cb)
    return x, y, x + tw + 32, y + th + 22


# ───────────────────────── 場景：開場 ─────────────────────────
def sc_hook(cv, reg, tl, t):
    x0, y0, x1, y1 = CONTENT
    L2 = LINES["L02"]
    items = [("AI 晶片", font(F_BLACK, 170), DEEP, 390, 0.1),
             ("為什麼一直缺貨？", font(F_ROUND, 92), CORAL, 610, 0.45)]
    for k, (s, f, col, y, d0) in enumerate(items):
        ta = clamp((tl - d0) / 0.3)
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
    # L01：AI 晶片示意圖示＋「缺貨」章（L02 的卡片出來前收掉，兩者不同時出現）
    ca = clamp((t - (L2.start - 0.05)) / 0.3)
    ga = clamp((tl - 0.7) / 0.3) * (1.0 if ca <= 0 else 0.0)
    if ga > 0:
        gw, gh = 560, 340
        im = Image.new("RGBA", (gw, gh), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        cx0, cy0, cx1, cy1 = 150, 40, 410, 300
        for k in range(7):                      # 接腳
            yy = cy0 + 30 + k * 34
            d.rounded_rectangle([cx0 - 40, yy, cx0 + 4, yy + 14], 5, fill=(150, 160, 172))
            d.rounded_rectangle([cx1 - 4, yy, cx1 + 40, yy + 14], 5, fill=(150, 160, 172))
        d.rounded_rectangle([cx0, cy0, cx1, cy1], 28, fill=(36, 52, 71), outline=(20, 30, 44), width=4)
        d.rounded_rectangle([cx0 + 30, cy0 + 30, cx1 - 30, cy1 - 30], 18, outline=(90, 120, 150), width=4)
        fa = font(F_BLACK, 96)
        tw, th, bb = tsize(fa, "AI")
        d.text(((cx0 + cx1) / 2 - tw / 2 - bb[0], (cy0 + cy1) / 2 - th / 2 - bb[1]), "AI", font=fa, fill=WHITE)
        sa = clamp((t - LINES["L01"].at("缺貨") + 0.05) / 0.25)
        if sa > 0:                              # 缺貨章（旋轉蓋下）
            st = Image.new("RGBA", (230, 120), (0, 0, 0, 0))
            sd = ImageDraw.Draw(st)
            sd.rounded_rectangle([4, 4, 226, 116], 20, outline=CORAL, width=10)
            fs_ = font(F_BLACK, 70)
            tw2, th2, bb2 = tsize(fs_, "缺貨")
            sd.text((115 - tw2 / 2 - bb2[0], 60 - th2 / 2 - bb2[1]), "缺貨", font=fs_, fill=CORAL)
            sc_ = 1.6 - 0.6 * ease_out(sa)
            st = st.rotate(-14, expand=True, resample=Image.BICUBIC)
            st = st.resize((int(st.width * sc_), int(st.height * sc_)), Image.LANCZOS)
            a_ = st.getchannel("A").point(lambda v: int(v * sa))
            st.putalpha(a_)
            im.alpha_composite(st, (int(gw - 40 - st.width / 2 - 100), int(gh - 20 - st.height / 2 - 60)))
        gx, gy = (W - gw) / 2, 790
        paste_alpha(cv, im, (gx, gy), ga)
        reg.add("開場圖示", (gx, gy, gx + gw, gy + gh))
    if ca > 0:
        cw, ch = 900, 320
        im, d = panel(cw, ch, bg=(255, 250, 232), edge=(232, 190, 60))
        org = ((W - cw) / 2, 800)
        cb = (14, 14, cw - 14, ch - 14)
        f1, f2 = font(F_ROUND, 52), font(F_BLACK, 120)
        text_at(d, reg, "開場卡字", (cw / 2, 46), "卡住的常常不是晶片", f1, GREY, org, cb, anchor="ma")
        fa = clamp((t - L2.at("封裝") + 0.1) / 0.3)
        if fa > 0:
            s = "是「封裝」"
            tw2, th2, _ = tsize(f2, s)
            hx = cw / 2 - tw2 / 2
            d.rounded_rectangle([hx - 8, 140 + th2 * 0.62, hx + tw2 + 8, 140 + th2 + 18], 12, fill=mix(LEMON, fa))
            text_at(d, reg, "開場卡字", (cw / 2, 140), s, f2, mix(DEEP, fa), org, cb, anchor="ma")
        sc = 0.9 + 0.1 * back_out(ca)
        im2 = im.resize((int(cw * sc), int(ch * sc)), Image.LANCZOS)
        px, py = org[0] + (cw - im2.width) / 2, org[1] + (ch - im2.height) / 2
        paste_alpha(cv, im2, (px, py), ca)
        reg.add("開場卡", (px, py, px + im2.width, py + im2.height))


# ───────────────────────── 場景：什麼是 CoWoS（剖面示意） ─────────────────────────
def sc_what(cv, reg, tl, t):
    x0, y0, x1, y1 = CONTENT
    w, h = x1 - x0, y1 - y0
    im, d = panel(w, h)
    org = (x0, y0)
    cb = (14, 14, w - 14, h - 14)
    L3, L4, L5 = LINES["L03"], LINES["L04"], LINES["L05"]
    f_t, f_s, f_l, f_c = font(F_BLACK, 50), font(F_BOLD, 30), font(F_BOLD, 34), font(F_BOLD, 36)
    text_at(d, reg, "示意圖字", (w / 2, 44), "CoWoS", f_t, DEEP, org, cb, anchor="ma")
    text_at(d, reg, "示意圖字", (w / 2, 112), "Chip on Wafer on Substrate", f_s, GREY, org, cb, anchor="ma")
    a_gpu = clamp((t - L4.start + 0.1) / 0.35)
    a_hbm = clamp((t - L4.at("HBM") + 0.05) / 0.35)
    a_int = clamp((t - L4.at("矽中介層") + 0.05) / 0.35)
    a_sub = clamp((t - L4.at("基板") + 0.05) / 0.35)
    a_l5 = clamp((t - L5.start + 0.05) / 0.35)
    # L03：圖還沒開始畫之前，先放「台積電的先進封裝」大字（GPU 掉下來時淡出，兩者不同時出現）
    a_l3 = clamp((t - L3.start + 0.1) / 0.3) * (1 - clamp((t - L4.start + 0.3) / 0.25))
    if a_l3 > 0:
        text_at(d, reg, "示意圖字", (w / 2, 330), "台積電的", font(F_ROUND, 60), mix(GREY, a_l3), org, cb, anchor="ma")
        text_at(d, reg, "示意圖字", (w / 2, 420), "先進封裝技術", font(F_BLACK, 96), mix(DEEP, a_l3), org, cb, anchor="ma")
        text_at(d, reg, "示意圖字", (w / 2, 580), "（2.5D 封裝）", font(F_ROUND, 48), mix(GREY, a_l3), org, cb, anchor="ma")
    # 幾何（面板座標）
    base_y = 600       # 中介層頂
    sub = (90, base_y + 70, w - 90, base_y + 150)
    inter = (150, base_y, w - 150, base_y + 60)
    gpu = (w / 2 - 150, base_y - 250, w / 2 + 150, base_y - 8)
    hbms = [(195, base_y - 220, 315, base_y - 8), (w - 315, base_y - 220, w - 195, base_y - 8)]
    if a_sub > 0:
        dy = (1 - ease_out(a_sub)) * 60
        d.rounded_rectangle([sub[0], sub[1] + dy, sub[2], sub[3] + dy], 14, fill=mix((222, 196, 150), a_sub), outline=mix((170, 130, 70), a_sub), width=4)
        for k in range(9):    # 錫球
            cx = sub[0] + 60 + k * (sub[2] - sub[0] - 120) / 8
            d.ellipse([cx - 12, sub[3] + dy + 2, cx + 12, sub[3] + dy + 26], fill=mix((180, 180, 186), a_sub))
        text_at(d, reg, "示意圖字", (w / 2, sub[1] + dy + 20), "基板 Substrate", f_l, mix((110, 70, 20), a_sub), org, cb, anchor="ma")
    if a_int > 0:
        dy = (1 - ease_out(a_int)) * 40
        d.rounded_rectangle([inter[0], inter[1] + dy, inter[2], inter[3] + dy], 10, fill=mix((120, 200, 210), a_int), outline=mix(CAT1, a_int), width=4)
        for k in list(range(4)) + list(range(10, 14)):   # 矽穿孔（中間留給標籤）
            cx = inter[0] + 30 + k * (inter[2] - inter[0] - 60) / 13
            d.line([(cx, inter[1] + dy + 6), (cx, inter[3] + dy - 6)], fill=mix((40, 120, 140), a_int), width=3)
    if a_gpu > 0:
        dy = -(1 - ease_out(a_gpu)) * 50
        d.rounded_rectangle([gpu[0], gpu[1] + dy, gpu[2], gpu[3] + dy], 16, fill=mix((36, 52, 71), a_gpu), outline=mix((20, 30, 44), a_gpu), width=3)
        text_at(d, reg, "示意圖字", ((gpu[0] + gpu[2]) / 2, gpu[1] + dy + 70), "GPU", font(F_BLACK, 56), mix(WHITE, a_gpu) if a_gpu > 0.5 else mix((36, 52, 71), a_gpu), org, cb, anchor="ma")
        text_at(d, reg, "示意圖字", ((gpu[0] + gpu[2]) / 2, gpu[1] + dy + 150), "運算晶片", f_s, mix((200, 210, 225), a_gpu) if a_gpu > 0.5 else mix((36, 52, 71), a_gpu), org, cb, anchor="ma")
    if a_hbm > 0:
        dy = -(1 - ease_out(a_hbm)) * 50
        for hb in hbms:
            n = 6
            hh = (hb[3] - hb[1]) / n
            for k in range(n):
                yy = hb[1] + dy + k * hh
                d.rounded_rectangle([hb[0], yy + 2, hb[2], yy + hh - 2], 6, fill=mix(CAT2 if k % 2 else (124, 108, 232), a_hbm))
        text_at(d, reg, "示意圖字", ((hbms[0][0] + hbms[0][2]) / 2, hbms[0][1] - 52), "HBM", f_c, mix(CAT2, a_hbm), org, cb, anchor="ma")
        text_at(d, reg, "示意圖字", ((hbms[1][0] + hbms[1][2]) / 2, hbms[1][1] - 52), "HBM", f_c, mix(CAT2, a_hbm), org, cb, anchor="ma")
    if a_int > 0:
        lab = "矽中介層 Interposer"
        # 標籤畫在中介層裡面
        text_at(d, reg, "示意圖字", (w / 2, inter[1] + 13 + (1 - ease_out(a_int)) * 40), lab, f_s, mix((10, 60, 75), a_int), org, cb, anchor="ma")
    # L05：距離短 → 更快、更省電
    if a_l5 > 0:
        for hb, sgn in ((hbms[0], 1), (hbms[1], -1)):
            xa = hb[2] + 8 if sgn > 0 else hb[0] - 8
            xb = gpu[0] - 8 if sgn > 0 else gpu[2] + 8
            yy = base_y - 120
            col = mix(CORAL, a_l5)
            d.line([(xa, yy), (xb, yy)], fill=col, width=7)
            for xe, dirn in ((xa, -sgn), (xb, sgn)):
                d.polygon([(xe, yy), (xe - dirn * 18, yy - 13), (xe - dirn * 18, yy + 13)], fill=col)
        chip_tag(d, reg, (w / 2 - 20, 820), "距離短 → 跑得快", font(F_BOLD, 34), WHITE, mix(CAT1, a_l5), org, cb, anchor="ra")
        chip_tag(d, reg, (w / 2 + 20, 820), "也更省電", font(F_BOLD, 34), WHITE, mix((46, 160, 96), a_l5), org, cb)
    paste_alpha(cv, im, org, clamp(tl / 0.3))
    reg.add("示意圖", (x0, y0, x1, y1))


# ───────────────────────── 場景：為什麼會缺（晶圓示意） ─────────────────────────
def wafer(d, cx, cy, r, die_w, die_h, col, a, gap=6):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=mix((214, 222, 232), a), outline=mix((120, 130, 145), a), width=4)
    n = 0
    nx = int(2 * r / (die_w + gap)) + 2
    ny = int(2 * r / (die_h + gap)) + 2
    for i in range(-nx // 2, nx // 2 + 1):
        for j in range(-ny // 2, ny // 2 + 1):
            x0 = cx + i * (die_w + gap) - die_w / 2
            y0 = cy + j * (die_h + gap) - die_h / 2
            corners = [(x0, y0), (x0 + die_w, y0), (x0, y0 + die_h), (x0 + die_w, y0 + die_h)]
            if all((px - cx) ** 2 + (py - cy) ** 2 <= (r - 8) ** 2 for px, py in corners):
                d.rounded_rectangle([x0, y0, x0 + die_w, y0 + die_h], 4, fill=mix(col, a))
                n += 1
    return n


def sc_why(cv, reg, tl, t):
    x0, y0, x1, y1 = CONTENT
    w, h = x1 - x0, y1 - y0
    im, d = panel(w, h)
    org = (x0, y0)
    cb = (14, 14, w - 14, h - 14)
    L6, L7 = LINES["L06"], LINES["L07"]
    f1, f2 = font(F_ROUND, 40), font(F_BOLD, 32)
    a1 = clamp((tl - 0.1) / 0.3)
    a2 = clamp((t - L6.at("越做越大") + 0.05) / 0.35)
    a3 = clamp((t - L7.at("需求") + 0.05) / 0.35)
    r = 200
    text_at(d, reg, "示意圖字", (250, 40), "以前：晶片小", f1, mix(INK, a1), org, cb, anchor="ma")
    wafer(d, 250, 330, r, 46, 46, CAT1, a1)
    text_at(d, reg, "示意圖字", (250, 556), "一片封得多", f2, mix(CAT1, a1), org, cb, anchor="ma")
    if a2 > 0:
        # 箭頭
        d.polygon([(470, 310), (520, 330), (470, 350)], fill=mix(GREY, a2))
        d.line([(440, 330), (480, 330)], fill=mix(GREY, a2), width=8)
        text_at(d, reg, "示意圖字", (750, 40), "現在：晶片大＋HBM 多", f1, mix(INK, a2), org, cb, anchor="ma")
        wafer(d, 750, 330, r, 112, 88, CORAL, a2, gap=10)
        text_at(d, reg, "示意圖字", (750, 556), "一片封得少", f2, mix(CORAL, a2), org, cb, anchor="ma")
    if a3 > 0:
        # 需求往上衝：上升折線
        bx0, by0, bx1, by1 = 90, 640, w - 90, 860
        d.rounded_rectangle([bx0 - 30, by0 - 20, bx1 + 30, by1 + 20], 22, fill=mix((255, 244, 240), a3), outline=mix(CORAL, a3), width=4)
        pts = [(bx0 + 20, by1 - 20), (bx0 + 220, by1 - 50), (bx0 + 420, by1 - 100), (bx0 + 560, by1 - 150)]
        u = ease_out(a3)
        d.line(pts[:2] + [(lerp(pts[1][0], pts[3][0], u), lerp(pts[1][1], pts[3][1], u))], fill=mix(CORAL, a3), width=10, joint="curve")
        tip = (lerp(pts[1][0], pts[3][0], u), lerp(pts[1][1], pts[3][1], u))
        d.polygon([(tip[0] + 6, tip[1] - 6), (tip[0] - 26, tip[1] - 2), (tip[0] - 6, tip[1] + 24)], fill=mix(CORAL, a3))
        text_at(d, reg, "示意圖字", (bx0 + 610, by0 + 40), "需求", font(F_BLACK, 56), mix(CORAL, a3), org, cb)
        text_at(d, reg, "示意圖字", (bx0 + 610, by0 + 122), "一直往上衝", f1, mix(INK, a3), org, cb)
    paste_alpha(cv, im, org, clamp(tl / 0.3))
    reg.add("示意圖", (x0, y0, x1, y1))


# ───────────────────────── 場景：產能擴多快（重點卡＋C 款直條） ─────────────────────────
BARS = [("2025 年底", 7.0, None, "約 7 萬"), ("2026 年底", 12.5, (12.0, 13.0), "約 12～13 萬"), ("2027 年底", 18.0, None, "約 18 萬")]


def sc_cap(cv, reg, tl, t):
    x0, y0, x1, y1 = CONTENT
    L8, L9, L10 = LINES["L08"], LINES["L09"], LINES["L10"]
    # 重點卡（公司說法）
    ca = clamp((t - L8.start + 0.1) / 0.3)
    cw, ch = x1 - x0, 270
    if ca > 0:
        im, d = panel(cw, ch, bg=WHITE, edge=SKY)
        org = (x0, y0)
        cb = (14, 14, cw - 14, ch - 14)
        f0, f1, f2 = font(F_BOLD, 30), font(F_BLACK, 50), font(F_ROUND, 42)
        text_at(d, reg, "卡片字", (40, 30), "台積電法說會（2024-10-17）", f0, GREY, org, cb)
        chip_tag(d, reg, (cw - 40, 24), "公司說法", font(F_BOLD, 28), (150, 90, 0), (255, 236, 200), org, cb, anchor="ra")
        text_at(d, reg, "卡片字", (40, 92), "2024、2025 年產能都翻倍", f1, DEEP, org, cb)
        xa = clamp((t - L8.at("翻倍") + 0.05) / 0.3)
        if xa > 0:
            chip_tag(d, reg, (cw - 40, 182), "×2　×2", font(F_BLACK, 40), WHITE, mix(CORAL, xa), org, cb, anchor="ra")
        fa = clamp((t - L8.at("供不應求") + 0.05) / 0.3)
        text_at(d, reg, "卡片字", (40, 182), "還是供不應求", f2, mix(CORAL, fa), org, cb)
        sc = 0.92 + 0.08 * back_out(ca)
        im2 = im.resize((int(cw * sc), int(ch * sc)), Image.LANCZOS)
        px, py = x0 + (cw - im2.width) / 2, y0 + (ch - im2.height) / 2
        paste_alpha(cv, im2, (px, py), ca)
        reg.add("重點卡", (px, py, px + im2.width, py + im2.height))
    # C 款直條（法人估計）
    ga = clamp((t - L8.start - 0.2) / 0.35)      # 圖表框跟著重點卡一起先出來（直條等講到才長出來），不留大片空白
    if ga <= 0:
        return
    gy0 = y0 + ch + 26
    gw, gh = x1 - x0, y1 - gy0
    im, d = panel(gw, gh, bg=WHITE)
    org = (x0, gy0)
    cb = (14, 14, gw - 14, gh - 14)
    text_at(d, reg, "圖表字", (36, 28), "CoWoS 月產能（萬片／月）", font(F_BOLD, 34), INK, org, cb)
    chip_tag(d, reg, (gw - 36, 22), "法人估計", font(F_BOLD, 28), (150, 90, 0), (255, 236, 200), org, cb, anchor="ra")
    py0, py1 = 120, gh - 86        # 繪圖區
    vmax = 20.0
    for v in (5, 10, 15, 20):      # 極淡水平格線
        yy = py1 - (py1 - py0) * v / vmax
        d.line([(60, yy), (gw - 40, yy)], fill=(236, 240, 244), width=2)
    d.line([(60, py1), (gw - 40, py1)], fill=(190, 198, 206), width=3)
    appear = [L9.at("2025"), L9.at("2026"), L10.start]
    slot = (gw - 100) / 3
    bw = min(48 * 2.6, slot * 0.5)
    for k, ((lab, v, rng, txt), ta0) in enumerate(zip(BARS, appear)):
        u = ease_out((t - ta0 + 0.05) / 0.6)
        cx = 60 + slot * (k + 0.5)
        if k:                      # 每根之間極淡垂直分隔線
            d.line([(60 + slot * k, py0), (60 + slot * k, py1)], fill=(240, 243, 246), width=2)
        text_at(d, reg, "圖表字", (cx, py1 + 18), lab, font(F_BOLD, 32), GREY, org, cb, anchor="ma")
        if u <= 0:
            continue
        top = py1 - (py1 - py0) * v / vmax * u
        bar = Image.new("RGBA", (int(bw), int(max(2, py1 - top))), (0, 0, 0, 0))
        g = np.linspace(1.0, 0.55, bar.height)[:, None]       # 上深下淺漸層
        arr = np.zeros((bar.height, bar.width, 4), np.uint8)
        arr[..., 0], arr[..., 1], arr[..., 2] = CAT1
        arr[..., 3] = (255 * g).astype(np.uint8).repeat(bar.width, 1)
        bar = Image.fromarray(arr, "RGBA")
        mk = Image.new("L", bar.size, 0)
        ImageDraw.Draw(mk).rounded_rectangle([0, 0, bar.width - 1, bar.height + 6], 6, fill=255)
        bar.putalpha(Image.fromarray(np.minimum(np.array(bar.getchannel("A")), np.array(mk))))
        im.alpha_composite(bar, (int(cx - bw / 2), int(top)))
        if k == 2:                 # 預估：斜線
            for yy in range(int(top) - 60, int(py1), 22):
                d.line([(cx - bw / 2, yy + 40), (cx + bw / 2, yy)], fill=(255, 255, 255, 120), width=4)
            d.rectangle([cx - bw / 2, top, cx + bw / 2, py1], outline=None)
        if rng and u > 0.95:       # 12～13 的區間
            ya, yb = py1 - (py1 - py0) * rng[0] / vmax, py1 - (py1 - py0) * rng[1] / vmax
            d.line([(cx + bw / 2 + 14, ya), (cx + bw / 2 + 14, yb)], fill=INK, width=4)
            d.line([(cx + bw / 2 + 6, ya), (cx + bw / 2 + 22, ya)], fill=INK, width=4)
            d.line([(cx + bw / 2 + 6, yb), (cx + bw / 2 + 22, yb)], fill=INK, width=4)
        la = clamp((t - ta0 - 0.35) / 0.3)
        if la > 0:
            f = font(F_BLACK, 44)
            text_at(d, reg, "圖表字", (cx, top - 62), txt, f, mix(CAT1 if k < 2 else CORAL, la), org, cb, anchor="ma")
    paste_alpha(cv, im, org, ga)
    reg.add("直條圖", (x0, gy0, x1, y1))


# ───────────────────────── 場景：產能給誰（A 款甜甜圈） ─────────────────────────
def sc_who(cv, reg, tl, t):
    x0, y0, x1, y1 = CONTENT
    w, h = x1 - x0, y1 - y0
    im, d = panel(w, h, bg=WHITE)
    org = (x0, y0)
    cb = (14, 14, w - 14, h - 14)
    L11 = LINES["L11"]
    text_at(d, reg, "圖表字", (40, 34), "2026 年 CoWoS 產能分配", font(F_BOLD, 36), INK, org, cb)
    chip_tag(d, reg, (w - 40, 28), "大摩估計", font(F_BOLD, 28), (150, 90, 0), (255, 236, 200), org, cb, anchor="ra")
    cx, cy, R = w / 2, 430, 280
    r_in = R * 68 / 92
    u = ease_io((t - L11.at("大摩") + 0.1) / 1.2)
    big = 0.60 * u
    # 底軌
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(240, 243, 246))
    if big > 0:
        d.pieslice([cx - R, cy - R, cx + R, cy + R], -90, -90 + 360 * big - 1, fill=CAT1)
    if u >= 1:
        d.pieslice([cx - R, cy - R, cx + R, cy + R], -90 + 360 * 0.60 + 1, 270 - 1, fill=CAT_OTHER)
    d.ellipse([cx - r_in, cy - r_in, cx + r_in, cy + r_in], fill=WHITE)
    ca = clamp((t - L11.at("六成") + 0.05) / 0.3)
    if ca > 0:
        text_at(d, reg, "圖表字", (cx, cy - 40), "約六成", font(F_BLACK, 76), mix(CAT1, ca), org, (cx - r_in, cy - r_in, cx + r_in, cy + r_in), anchor="ma")
        text_at(d, reg, "圖表字", (cx, cy + 56), "最大 GPU 客戶", font(F_BOLD, 32), mix(GREY, ca), org, (cx - r_in, cy - r_in, cx + r_in, cy + r_in), anchor="ma")
    # 圖例（下方）
    la = clamp((t - L11.at("六成") - 0.2) / 0.3)
    if la > 0:
        ly = 770
        for k, (col, name, pct) in enumerate([(CAT1, "最大 GPU 客戶", "約 60%"), (CAT_OTHER, "其他客戶", "約 40%")]):
            yy = ly + k * 54
            d.rounded_rectangle([200, yy + 6, 232, yy + 38], 6, fill=mix(col, la))
            text_at(d, reg, "圖表字", (252, yy), name, font(F_BOLD, 34), mix(INK, la), org, cb)
            text_at(d, reg, "圖表字", (w - 200, yy), pct, font(F_BOLD, 34), mix(INK, la), org, cb, anchor="ra")
    paste_alpha(cv, im, org, clamp(tl / 0.3))
    reg.add("甜甜圈", (x0, y0, x1, y1))


# ───────────────────────── 場景：台灣供應鏈分段 ─────────────────────────
CHAIN = [("前段", "晶圓廠", "晶片接上中介層（CoW）", CAT1, "晶圓廠"),
         ("後段", "封測廠分擔", "接上基板（oS）、部分製程", CAT2, "封測廠"),
         ("支援", "設備・測試環節", "一起撐起產能", AMBER, "設備")]


def sc_chain(cv, reg, tl, t):
    x0, y0, x1, y1 = CONTENT
    w, h = x1 - x0, y1 - y0
    im, d = panel(w, h)
    org = (x0, y0)
    cb = (14, 14, w - 14, h - 14)
    L12, L13 = LINES["L12"], LINES["L13"]
    bh, gap = 220, 70
    top = 60
    for k, (tag, title, sub, col, anchor) in enumerate(CHAIN):
        a = clamp((t - L13.at(anchor) + 0.1) / 0.3) if k else clamp((t - L12.start + 0.05) / 0.3)
        by = top + k * (bh + gap)
        if a <= 0:
            continue
        d.rounded_rectangle([60, by, w - 60, by + bh], 26, fill=mix((246, 248, 252), a), outline=mix(col, a), width=5)
        x_t = 90
        bx = chip_tag(d, reg, (x_t, by + 32), tag, font(F_BOLD, 34), WHITE, mix(col, a), org, cb)
        text_at(d, reg, "分段字", (bx[2] + 26, by + 30), title, font(F_BLACK, 52), mix(INK, a), org, cb)
        text_at(d, reg, "分段字", (x_t, by + 130), sub, font(F_ROUND, 40), mix(GREY, a), org, cb)
        if k < 2:
            ay = by + bh + 8
            d.polygon([(w / 2 - 26, ay + 12), (w / 2 + 26, ay + 12), (w / 2, ay + gap - 18)], fill=mix((170, 180, 192), a))
    paste_alpha(cv, im, org, clamp(tl / 0.3))
    reg.add("供應鏈圖", (x0, y0, x1, y1))


# ───────────────────────── 場景：網站實際畫面 ─────────────────────────
class Clip:
    def __init__(self, path, crop_y=0):
        self.frames = sorted(Path(path).glob("*.png"))
        self.crop_y = crop_y

    def get(self, t):
        if not self.frames:
            return None
        return self.frames[min(len(self.frames) - 1, max(0, int(t * FPS)))]


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
    ImageDraw.Draw(out).rounded_rectangle([0, 0, w - 1, h - 1], 28, outline=(180, 196, 214), width=4)
    return out


CLIPS = {}


def sc_site(cv, reg, tl, t):
    p = CLIPS["theme"].get(max(0.0, tl - 0.15))
    if p is None:
        return
    paste_alpha(cv, site_frame(str(p), CLIPS["theme"].crop_y), CONTENT[:2], clamp(tl / 0.3))
    reg.add("網站畫面", CONTENT)


# ───────────────────────── 片尾 ─────────────────────────
@lru_cache(maxsize=1)
def logo(px):
    im = Image.open(LOGO).convert("RGBA").resize((px, px), Image.LANCZOS)
    im.putalpha(rmask(px, px, int(px * 0.22)))
    return im


DISCLAIMER = ["本內容為公開資料整理，不構成任何投資建議", "投資有風險，請自行判斷"]


def sc_end(cv, reg, tl, t):
    la = clamp(tl / 0.35)
    lg = logo(320)
    sc = 0.8 + 0.2 * back_out(la)
    l2 = lg.resize((int(320 * sc), int(320 * sc)), Image.LANCZOS)
    x, y = (W - l2.width) / 2, 360 + (320 - l2.height) / 2
    paste_alpha(cv, l2, (x, y), la)
    reg.add("標誌", (x, y, x + l2.width, y + l2.height))
    f1, f2 = font(F_ROUND, 56), font(F_ROUND, 40)
    for k, (s, f, col, yy) in enumerate([("搜尋「哩股哩股」", f1, DEEP, 730), ("題材熱力圖・CoWoS／先進封裝", f2, INK, 818)]):
        ta = clamp((tl - 0.3 - 0.2 * k) / 0.3)
        if ta <= 0:
            continue
        tw, th, bb = tsize(f, s)
        im = Image.new("RGBA", (tw + 8, th + 16), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((4 - bb[0], 8 - bb[1]), s, font=f, fill=col)
        xx = (W - tw) / 2
        paste_alpha(cv, im, (xx - 4, yy - 8), ta)
        reg.add(f"片尾字{k + 1}", (xx, yy, xx + tw, yy + th))
        reg.text_in(f"片尾字{k + 1}", (xx, yy, xx + tw, yy + th), (0, 0, W, H), inset=30)
    da = clamp((tl - 0.2) / 0.3)
    if da > 0:
        f3 = font(F_BOLD, 36)
        tws = [tsize(f3, s)[0] for s in DISCLAIMER]
        lh = 54
        bw, bh = max(tws) + 64, lh * len(DISCLAIMER) + 36
        bx, by = (W - bw) / 2, 940
        im = Image.new("RGBA", (int(bw), int(bh)), (0, 0, 0, 0))
        im.paste((255, 255, 255, 255), (0, 0), rmask(bw, bh, 22))
        dd = ImageDraw.Draw(im)
        dd.rounded_rectangle([0, 0, bw - 1, bh - 1], 22, outline=(200, 206, 214), width=3)
        for k, s in enumerate(DISCLAIMER):
            bb = f3.getbbox(s)
            dd.text(((bw - tws[k]) / 2 - bb[0], 22 + k * lh - bb[1]), s, font=f3, fill=INK)
            reg.text_in("免責聲明", (bx + (bw - tws[k]) / 2, by + 22 + k * lh, bx + (bw + tws[k]) / 2, by + 22 + k * lh + 38), (bx, by, bx + bw, by + bh), inset=10)
        paste_alpha(cv, im, (bx, by), da)
        reg.add("免責聲明", (bx, by, bx + bw, by + bh))


SCENE_FN = {"hook": sc_hook, "what": sc_what, "why": sc_why, "cap": sc_cap, "who": sc_who,
            "chain": sc_chain, "site": sc_site, "end": sc_end}
FOOT_SITE = None


def render(t):
    cv = Image.new("RGBA", (W, H), CREAM + (255,))
    d = ImageDraw.Draw(cv)
    off = (t * 24) % 60
    for y in range(-60, H + 60, 60):
        d.line([(0, y - off), (W, y - off)], fill=(242, 232, 213), width=3)
    for x in range(-60, W + 60, 60):
        d.line([(x + off, 0), (x + off, H)], fill=(242, 232, 213), width=3)
    reg = Reg()
    cur = None
    for (sc, s0, s1) in SCENE_T:
        if not (s0 <= t < s1):
            continue
        cur = (sc, s0, s1)
        sid, lids, pl, hd, hl, tag, fn = sc
        tl = t - s0 + (0.6 if s0 == 0.0 else 0.15)
        if pl:
            pill(cv, reg, pl, 40, 110, clamp(tl / 0.3))
        if tag:
            pill(cv, reg, tag, 1040, 110, clamp((tl - 0.2) / 0.3), bg=(255, 236, 200), fg=(150, 90, 0), px=30, name="角標", right=True)
        if hd:
            headline(cv, reg, hd, 196, clamp((tl - 0.1) / 0.35), hl=hl)
        fa = clamp((tl - 0.2) / 0.3) if sid != "hook" else clamp((t - 2.25) / 0.3)   # 開場 intro 彈跳會低到小字帶，等 intro 播完
        footnote(cv, reg, fn if fn else (FOOT_SITE if sid == "site" else None), fa)
        SCENE_FN[sid](cv, reg, tl, t)
    nm, bt = bibi_at(t)
    draw_bibi(cv, reg, nm, bt)
    if cur:
        sc, s0, s1 = cur
        lids = sc[1]
        b0 = LINES[lids[0]].start - 0.12
        b1 = min(s1 - 0.04, LINES[lids[-1]].end + 0.5) if sc[0] != "end" else s1
        if b0 <= t < b1:
            a = min(clamp((t - b0) / 0.18), clamp((b1 - t) / 0.12))
            names = acts_between(b0, b1)
            txt, ta = "", 0.0
            for (s, c0, c1, sid) in SUBS:
                if sid == sc[0] and c0 - 0.02 <= t < c1:
                    txt, ta = s, clamp((t - c0 + 0.02) / 0.1)
            if not txt:       # 句子之間的空檔：留著上一句（不閃空泡泡）
                prev = [x for x in SUBS if x[3] == sc[0] and x[1] <= t]
                if prev:
                    txt, ta = prev[-1][0], 1.0
            bubble(cv, reg, txt, a, names, ta, all_texts=[x[0] for x in SUBS if x[3] == sc[0]])
    return cv.convert("RGB"), reg


# ───────────────────────── 字幕、封面、配音混音 ─────────────────────────
def ts(x):
    ms = int(round(x * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_srt(path):
    out = []
    for i, (s, a, b, _sid) in enumerate(SUBS, 1):
        out += [str(i), f"{ts(a)} --> {ts(min(b, TOTAL))}", s, ""]
    e0 = SCENE_T[-1][1] + 0.5
    out += [str(len(SUBS) + 1), f"{ts(e0)} --> {ts(TOTAL)}", "，".join(DISCLAIMER), ""]
    Path(path).write_text("\n".join(out), encoding="utf-8")


def make_cover(path):
    cv = Image.new("RGBA", (W, H), CREAM + (255,))
    d = ImageDraw.Draw(cv)
    for y in range(0, H, 60):
        d.line([(0, y), (W, y)], fill=(246, 238, 222), width=2)
    for x in range(0, W, 60):
        d.line([(x, 0), (x, H)], fill=(246, 238, 222), width=2)
    reg = Reg()
    pill(cv, reg, "比比知識", 40, 200, 1.0, px=40)
    items = [("CoWoS", font(F_BLACK, 230), DEEP, 330), ("為什麼缺貨？", font(F_ROUND, 130), INK, 640),
             ("先進封裝・5 個重點", font(F_ROUND, 64), CORAL, 860)]
    for k, (s_, f, col, y) in enumerate(items):
        tw, th, bb = tsize(f, s_)
        x = (W - tw) / 2
        if k == 2:
            d.rounded_rectangle([x - 30, y - 22, x + tw + 30, y + th + 26], 40, fill=(255, 236, 200))
        d.text((x - bb[0], y - bb[1]), s_, font=f, fill=col)
        ex = 30 if k == 2 else 0
        reg.add(f"封面字{k + 1}", (x - ex, y - (22 if k == 2 else 0), x + tw + ex, y + th + (26 if k == 2 else 0)))
        reg.text_in(f"封面字{k + 1}", (x, y, x + tw, y + th), (0, 0, W, H), inset=30)
    size = 900
    i = len(bibi_frames("talk_excited")) // 2
    sp = bibi_scaled("talk_excited", i, size)
    ox, oy = int(W / 2 - 248 * size / 512), int(1610 - 482 * size / 512)
    cv.alpha_composite(sp, (ox, oy))
    b = bibi_bbox("talk_excited", i, size)
    reg.add("比比", (ox + b[0], oy + b[1], ox + b[2], oy + b[3]))
    cv.convert("RGB").save(path)
    return reg


def read_wav(p):
    with wave.open(str(p)) as w:
        sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
        a = np.frombuffer(w.readframes(n), np.int16).astype(np.float32) / 32768
    return sr, a.reshape(-1, ch)


def mix_audio(out_wav):
    SR = 44100
    n = int(TOTAL * SR) + SR
    voice = np.zeros(n, np.float32)
    speak = np.zeros(n, np.float32)
    for lid, ln in LINES.items():
        tmp = SCR / f"v_{VOICE}_{lid}.wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(VDIR / f"{lid}.mp3"), "-ac", "1", "-ar", str(SR), str(tmp)], check=True)
        _, a = read_wav(tmp)
        a = a[:, 0]
        s = int((ln.start - ln.w0) * SR)
        if s < 0:
            a, s = a[-s:], 0
        e = min(n, s + len(a))
        voice[s:e] += a[:e - s]
        speak[int(ln.start * SR):int(ln.end * SR)] = 1.0
    pk = np.max(np.abs(voice)) + 1e-9
    voice *= 0.89 / pk
    bgm_p = SCR / "bgm.wav"
    subprocess.run([sys.executable, str(HERE / "make_bgm_cowos.py"), str(bgm_p), f"{TOTAL + 0.5:.2f}"], check=True)
    _, b = read_wav(bgm_p)
    b = b[:n] if len(b) >= n else np.vstack([b, np.zeros((n - len(b), 2), np.float32)])
    # 人聲下壓：講話時配樂 0.10，沒講話 0.26，用 0.25 秒平滑
    k = int(0.25 * SR)
    env = np.convolve(speak, np.ones(k) / k, mode="same")
    g = 0.26 - 0.16 * np.clip(env * 1.5, 0, 1)
    outp = b * g[:, None] + voice[:, None]
    outp = outp[:int(TOTAL * SR)]
    outp = np.clip(outp, -0.99, 0.99)
    with wave.open(str(out_wav), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((outp * 32767).astype(np.int16).tobytes())


def keyframe_sheet(paths, out):
    ims = [Image.open(p).resize((270, 480), Image.LANCZOS) for p in paths]
    sheet = Image.new("RGB", (4 * 270 + 5 * 10, 3 * 480 + 4 * 10 + 3 * 34), (30, 30, 30))
    d = ImageDraw.Draw(sheet)
    f = font(F_BOLD, 24)
    for k, (im, p) in enumerate(zip(ims, paths)):
        x, y = 10 + (k % 4) * 280, 10 + (k // 4) * (480 + 44)
        sheet.paste(im, (x, y + 34))
        d.text((x, y), Path(p).stem.replace("s_", "") + " 秒", font=f, fill=(255, 255, 255))
    sheet.save(out)


def main():
    global FOOT_SITE
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / f"{OUT_BASE}.mp4"))
    ap.add_argument("--frames", default="")
    ap.add_argument("--cover", action="store_true")
    a = ap.parse_args()
    build_timeline()
    meta_p = SCR / "raw" / "meta.json"
    meta = json.loads(meta_p.read_text()) if meta_p.exists() else {}
    FOOT_SITE = [f"網站實際畫面・資料日 {meta.get('data_date', '')}"]
    CLIPS["theme"] = Clip(SCR / "raw" / "theme", meta.get("crop", {}).get("theme", 0))
    print(f"片長 {TOTAL:.2f} 秒；聲音 {VOICE}", file=sys.stderr)
    for (sc, s0, s1) in SCENE_T:
        print(f"  {sc[0]:6s} {s0:6.2f}–{s1:6.2f}", file=sys.stderr)
    if a.cover:
        reg = make_cover(HERE / "cowos_bibi_cover.png")
        print("封面 重疊", reg.overlaps(), "字出框", reg.text_issues)
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
    for i in range(n):
        t = i / FPS
        im, reg = render(t)
        ff.stdin.write(im.tobytes())
        for (x, y, area) in reg.overlaps():
            rows.append(f"| {t:6.2f} | {x} | {y} | {area} |")
        for s in reg.text_issues:
            issues.append(f"| {t:6.2f} | {s} |")
        if i % 15 == 0:
            im.save(samp / f"s_{t:05.1f}.png")
        if i % 150 == 0:
            print(f"{t:5.1f}s", file=sys.stderr)
    ff.stdin.close()
    ff.wait()
    rep = ["# 重疊檢查報告（render_cowos.py 每一幀自動產生）", "",
           f"- 聲音：{VOICE}；片長 {TOTAL:.2f} 秒；總幀數：{n}（30fps）；每個外框外擴 {PAD}px 後兩兩比對（同一個泡泡的本體／尾巴算同一組）。",
           "- 登記的元素：段落膠囊、角標、大字、開場大字、開場卡、示意圖、重點卡、直條圖、甜甜圈、供應鏈圖、網站畫面、標誌、片尾字、免責聲明、底部小字、比比（每一幀實際外框）、泡泡＋尾巴。",
           f"- 重疊：**{len(rows)} 筆**", f"- 字出框／泡泡尾巴規則：**{len(issues)} 筆**", ""]
    if rows:
        rep += ["| 秒 | 元素 A | 元素 B | 相交面積 |", "|---|---|---|---|"] + rows[:400]
    if issues:
        rep += ["", "| 秒 | 問題 |", "|---|---|"] + issues[:400]
    (HERE / "overlap_report.md").write_text("\n".join(rep) + "\n", encoding="utf-8")
    print("重疊", len(rows), "字出框", len(issues), "幀", n)
    wav = SCR / "mix.wav"
    mix_audio(wav)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), "-i", str(wav), "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "160k", "-shortest", "-movflags", "+faststart", a.out], check=True)
    write_srt(HERE / f"{OUT_BASE}.srt")
    (SCR / "timeline.json").write_text(json.dumps({"total": TOTAL, "acts": ACT_TL, "subs": SUBS,
                                                   "scenes": [(s[0][0], s[1], s[2]) for s in SCENE_T]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
