"""每週自動產出 IG 短影片（Reels）。2026-11-09 Andy 同意：IG 停自動純圖文，改每週 2 支 15～30 秒短影片。

流程：選題 → 逐幀算圖（Pillow）→ ffmpeg 編碼 → 逐幀重疊檢查（overlap_report.md）→ 寫 IG 佇列檔。
真正發出由 scripts/ig_post.py（佇列檔有 `video:` 欄就走 REELS 上傳）負責，這支不連 Meta。

選題順序（沒有任何一步會讓整段不做）：
  1. 近 14 天 Threads 觀看數最高的貼文（social/threads/insights/metrics.csv）→ 比對題庫關鍵字，
     命中且近 28 天沒做過 → 用該題；
  2. 否則題庫裡「最久沒用過」的一題（輪替）。
題庫：docs/marketing/social_unit/reels_bank.json（每題都是規則型知識，不預測、不點名個股、不給時機）。
為什麼不直接把熱點文自動拆成字卡：自由文字拆句會產生預測／點名個股的風險，合規閘過不了就會整段不做，
所以改成「熱點文決定題目、內容用查證過的題庫」。

用法：
  python scripts/ig_reels_weekly.py --out <資料夾>             產影片＋重疊報告＋佇列檔，更新 state.json
  python scripts/ig_reels_weekly.py --out <資料夾> --sample     只產影片與報告（不寫佇列、不改 state）
  python scripts/ig_reels_weekly.py --topic cost ...           指定題庫 id
  python scripts/ig_reels_weekly.py --list                     列題庫

版型：色票照 docs/marketing/social_unit/post_layout_b_pro.md（深藍 #14213D、暖白 #FBFAF6、銅紅 #A8482A、紅漲 #C0392B、綠跌 #1F7A57）。
社群貼文與短影片一律不放吉祥物比比（CLAUDE.md 11-02）。
重疊檢查規則：docs/marketing/video_1010/layout_rules.md（每幀登記每個元素外框、外擴 6px 兩兩比對，有一筆就不出片）。
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
BANK = ROOT / "docs" / "marketing" / "social_unit" / "reels_bank.json"
STATE = ROOT / "social" / "ig" / "reels" / "state.json"
METRICS = ROOT / "social" / "threads" / "insights" / "metrics.csv"
QUEUE = ROOT / "social" / "ig" / "queue"
TAIPEI = timezone(timedelta(hours=8))

W, H, FPS = 1080, 1920, 30
PAD = 6                      # 規則：外框外擴 6px 再比對
SAFE_X = (40, 1040)          # 文字不得超出左右 40px
SAFE_Y = (230, 1520)         # Reels 上下 UI 會蓋住的區域之外

INK = (20, 33, 61)           # 深藍 #14213D
PAPER = (251, 250, 246)      # 暖白 #FBFAF6
COPPER = (168, 72, 42)       # 銅紅 #A8482A
UP = (192, 57, 43)           # 紅漲 #C0392B
DOWN = (31, 122, 87)         # 綠跌 #1F7A57
GRAY = (74, 84, 104)         # 灰字 #4A5468
SOFT = (243, 225, 216)       # 淺銅底 #F3E1D8
LINE = (227, 221, 207)       # 分隔線 #E3DDCF
BRIGHT = (224, 137, 95)      # 深色底上用的亮銅（銅紅在深藍上對比不夠）

FONT_CANDIDATES = [  # (路徑, ttc 索引, 本身是否粗體)
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 3, True),
    ("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc", 3, True),
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 3, False),
    ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 0, False),
    ("/usr/share/fonts/wqy-zenhei/wqy-zenhei.ttc", 0, False),
]

# 合規：不預測、不點名個股、不給時機、不放網址
BANNED = ["進場", "出場", "目標價", "推薦", "看好", "看多", "看空", "會漲", "會跌", "必漲", "必跌",
          "穩賺", "保證", "明牌", "布局", "佈局", "加碼", "停損點", "http", "www.", ".com", "代號"]
ADVICE = re.compile(r"(建議|可以|應該|該|請|快|先|趁|逢低|逢高)(買進|賣出|買|賣)")
STOCK_CODE = re.compile(r"(?<![\d.,])[1-9]\d{3}(?![\d%年元.,點億月日號萬])")


# ---------- 字型與文字 ----------
_font_cache: dict = {}


def font(size: int):
    if size in _font_cache:
        return _font_cache[size]
    for p, idx, bold in FONT_CANDIDATES:
        if Path(p).exists():
            try:
                f = ImageFont.truetype(p, size, index=idx)
                _font_cache[size] = (f, 0 if bold else max(1, size // 38))
                return _font_cache[size]
            except OSError:
                continue
    raise SystemExit("找不到中文字型（請安裝 fonts-noto-cjk）")


def units(s: str) -> float:
    return sum(0.5 if ord(c) < 256 else 1.0 for c in s)


def wrap(s: str, limit: float = 12.0) -> list[str]:
    """依「字數單位」換行（半形算 0.5）；盡量在標點與空白處斷。"""
    out, cur = [], ""
    for ch in s:
        if units(cur + ch) > limit and cur:
            cut = max(cur.rfind(c) for c in "，、 ：（") if any(c in cur for c in "，、 ：（") else -1
            if cut >= max(4, len(cur) // 2):
                out.append(cur[:cut + 1].strip())
                cur = cur[cut + 1:]
            else:
                out.append(cur)
                cur = ""
        cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def lerp(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(round(a + (b - a) * t)) for a, b in zip(c1, c2))


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


# ---------- 畫面 ----------
class Canvas:
    """一幀：背景（慢速明暗波，避免畫面停格）＋ 元素登記（供逐幀重疊檢查）。"""

    def __init__(self, base, wave_amp, t):
        y = np.arange(H)
        wave = wave_amp * np.sin(2 * math.pi * (y / 760.0 - t * 0.7))
        rows = np.clip(np.array(base)[None, :] + wave[:, None], 0, 255).astype(np.uint8)
        arr = np.repeat(rows[:, None, :], W, axis=1)
        self.img = Image.fromarray(arr)
        self.d = ImageDraw.Draw(self.img)
        self.base = base
        self.elems: list[tuple[str, tuple[int, int, int, int]]] = []

    def text(self, name, xy, s, size, fill, anchor="la", alpha=1.0):
        f, sw = font(size)
        fill = lerp(self.base, fill, alpha)
        box = self.d.textbbox(xy, s, font=f, anchor=anchor, stroke_width=sw)
        self.d.text(xy, s, font=f, fill=fill, anchor=anchor, stroke_width=sw, stroke_fill=fill)
        self.elems.append((name, tuple(int(v) for v in box)))
        return box

    def pill(self, name, xy, s, size, fg, bg, alpha=1.0, anchor="l", padx=34, pady=16):
        """圓角膠囊（膠囊＋裡面的字算同一個元素）。xy＝(左或中心 x, 上緣 y)。"""
        f, sw = font(size)
        tb = self.d.textbbox((0, 0), s, font=f, stroke_width=sw)
        tw, th = tb[2] - tb[0], tb[3] - tb[1]
        w, h = tw + 2 * padx, th + 2 * pady
        x0 = xy[0] if anchor == "l" else xy[0] - w // 2
        y0 = xy[1]
        bgc = lerp(self.base, bg, alpha)
        fgc = lerp(bgc, fg, alpha)
        self.d.rounded_rectangle((x0, y0, x0 + w, y0 + h), radius=h // 2, fill=bgc)
        self.d.text((x0 + padx - tb[0], y0 + pady - tb[1]), s, font=f, fill=fgc, stroke_width=sw, stroke_fill=fgc)
        self.elems.append((name, (x0, y0, x0 + w, y0 + h)))
        return (x0, y0, x0 + w, y0 + h)

    def card(self, name, rect, label, s, size, bg, fg, alpha=1.0):
        x0, y0, x1, y1 = rect
        bgc = lerp(self.base, bg, alpha)
        fgc = lerp(bgc, fg, alpha)
        self.d.rounded_rectangle(rect, radius=36, fill=bgc)
        f, sw = font(size)
        lf, lsw = font(size + 20)
        self.d.text((x0 + 44, (y0 + y1) // 2), label, font=lf, fill=lerp(bgc, BRIGHT if bg == INK else COPPER, alpha),
                    anchor="lm", stroke_width=lsw, stroke_fill=lerp(bgc, BRIGHT if bg == INK else COPPER, alpha))
        tb = self.d.textbbox((x0 + 130, (y0 + y1) // 2), s, font=f, anchor="lm", stroke_width=sw)
        if tb[2] > x1 - 20:
            raise SystemExit(f"卡片文字放不下：{s!r}")
        self.d.text((x0 + 130, (y0 + y1) // 2), s, font=f, fill=fgc, anchor="lm", stroke_width=sw, stroke_fill=fgc)
        self.elems.append((name, tuple(rect)))

    def rect(self, name, rect, fill, alpha=1.0):
        self.d.rectangle(rect, fill=lerp(self.base, fill, alpha))
        self.elems.append((name, tuple(rect)))


# ---------- 場景 ----------
FOOT = "內容僅供教育參考，非投資建議"


def chrome(c: Canvas, dark: bool, tag: str, prog: float, t_all: float):
    fg = PAPER if dark else INK
    c.text("品牌", (80, 250), "哩股哩股", 40, BRIGHT if dark else COPPER)
    c.text("分類", (1000, 250), tag, 36, fg, anchor="ra", alpha=0.8)
    # 進度條（整條算一個元素）
    track = (80, 1410, 1000, 1422)
    c.d.rectangle(track, fill=lerp(c.base, fg, 0.18))
    c.d.rectangle((80, 1410, 80 + int(920 * prog), 1422), fill=BRIGHT if dark else COPPER)
    c.elems.append(("進度條", track))
    c.text("免責", (540, 1460), FOOT, 30, fg, anchor="ma", alpha=0.65)


def stagger(t, start, step, i):
    """第 i 個元素的進場進度 0→1（每個 0.5 秒滑入）。"""
    return ease((t - start - i * step) / 0.5)


def _tok(ch):
    return ch.isascii() and (ch.isalnum() or ch in ".,%+-×")


def wrap_px(s, size, maxw):
    """依像素寬換行；不把「12.19%」「39,702」這類數字從中間拆開，優先在空白與標點後斷行。"""
    f, sw = font(size)
    out, cur = [], ""
    for ch in s:
        if cur and f.getlength(cur + ch) + 2 * sw > maxw:
            k = len(cur)
            if _tok(ch):                      # 新字會接在數字／英文後面 → 往回找可斷處
                k = next((i for i in range(len(cur) - 1, 0, -1) if not (_tok(cur[i - 1]) and _tok(cur[i]))), len(cur))
            out.append(cur[:k].rstrip())
            cur = cur[k:].lstrip()
        cur += ch
    if cur:
        out.append(cur)
    return out


def fit_block(s, maxw, maxh, hi, lo, lh=1.3):
    """找最大字級，使換行後的文字塊放得進 maxw×maxh。"""
    for size in range(hi, lo - 1, -4):
        lines = wrap_px(s, size, maxw)
        if len(lines) * size * lh <= maxh:
            return size, lines
    return lo, wrap_px(s, lo, maxw)


def textcard(c, name, rect, s, hi, lo, fg, bg, alpha=1.0, lh=1.3, align="l"):
    """圓角色塊＋置中文字，算同一個元素；字級自動放到最大。"""
    x0, y0, x1, y1 = rect
    size, lines = fit_block(s, x1 - x0 - 80, y1 - y0 - 50, hi, lo, lh)
    bgc = lerp(c.base, bg, alpha)
    fgc = lerp(bgc, fg, alpha)
    c.d.rounded_rectangle(rect, radius=40, fill=bgc)
    f, sw = font(size)
    total = len(lines) * size * lh
    y = (y0 + y1) / 2 - total / 2 + size * lh / 2
    for ln in lines:
        x = x0 + 44 if align == "l" else (x0 + x1) // 2
        c.d.text((x, y), ln, font=f, fill=fgc, anchor="lm" if align == "l" else "mm", stroke_width=sw, stroke_fill=fgc)
        y += size * lh
    c.elems.append((name, tuple(rect)))


def draw_lines(c, name, lines, x, y, size, fill, t, start, step=0.22, anchor="la", lh=1.3, first=0):
    for i, ln in enumerate(lines):
        p = stagger(t, start, step, i + first)
        if p > 0:
            c.text(f"{name}{i + 1}", (x, y + int((1 - p) * 40)), ln, size, fill, anchor=anchor, alpha=p)
        y += int(size * lh)
    return y


def fit_size(lines, lo, hi, maxw=900):
    for s in range(hi, lo - 1, -4):
        f, sw = font(s)
        if max(f.getlength(l) + 2 * sw for l in lines) <= maxw:
            return s
    return lo


def scene_hook(c, sp, t):
    c.pill("類別", (540, 560), sp["tag"], 44, PAPER, COPPER, alpha=stagger(t, 0.0, 0, 0), anchor="c")
    size = fit_size(sp["hook"], 90, 180, 980)
    y = draw_lines(c, "鉤子", sp["hook"], 540, 700, size, PAPER, t, 0.15, 0.25, anchor="ma", lh=1.28)
    sub = stagger(t, 0.8, 0, 0)
    if sub > 0:
        c.text("副標", (540, y + 60 + int((1 - sub) * 30)), sp["sub"], 58, (255, 214, 186), anchor="ma", alpha=sub)


def scene_point(c, sp, t, idx, total, head, detail, plain):
    c.pill("步驟", (80, 340), f"{idx} / {total}", 40, PAPER, COPPER, alpha=stagger(t, 0.0, 0, 0))
    p1, p2, p3 = stagger(t, 0.1, 0, 0), stagger(t, 0.7, 0, 0), stagger(t, 1.4, 0, 0)
    if p1 > 0:
        textcard(c, "重點", (80, 430, 1000, 770), head, 104, 64, INK, SOFT, p1)
    bottom = 1010 if plain else 1370
    if p2 > 0:
        textcard(c, "說明", (80, 810, 1000, bottom), detail, 76, 48, PAPER, INK, p2, lh=1.4)
    if plain and p3 > 0:
        textcard(c, "白話", (80, 1050, 1000, 1370), plain, 68, 44, PAPER, COPPER, p3, lh=1.35)


def fmt(v, dec):
    return f"{v:,.{dec}f}"


def scene_number(c, sp, t, n):
    color = {"up": UP, "green": DOWN, "ink": INK}[n["color"]]
    c.pill("類別", (80, 340), n.get("pill", "關鍵數字"), 40, PAPER, COPPER, alpha=stagger(t, 0.0, 0, 0))
    lsz = next((z for z in range(68, 43, -2) if len(wrap_px(n["label"], z, 920)) == 1), 44)
    ll = wrap_px(n["label"], lsz, 920)
    draw_lines(c, "標籤", ll, 80, 420, lsz, INK, t, 0.1, 0.2, lh=1.35)
    ytop = 420 + int(len(ll) * lsz * 1.35) + 10
    dec = n.get("dec", len(str(n["value"]).split(".")[1]) if "." in str(n["value"]) else 0)
    prog = ease((t - 0.5) / 1.8)
    full = fmt(n["value"], dec) + n["suffix"]
    size = fit_size([full], 120, 250, 920)
    if prog > 0:
        c.text("大數字", (80, ytop), fmt(n["value"] * prog, dec) + n["suffix"], size, color)
    ybig = ytop + int(size * 1.3)
    p = stagger(t, 2.2, 0, 0)
    bar = n.get("bar")
    ph = 230 if bar else 330
    if n.get("plain") and p > 0:
        textcard(c, "白話", (80, ybig + 20, 1000, ybig + 20 + ph), n["plain"], 72, 44, PAPER, COPPER, p, lh=1.3)
    yb = ybig + 20 + ph + 36
    if bar:
        tot = sum(v for _, v, _ in bar)
        pb = ease((t - 2.6) / 1.2)
        x = 80
        for i, (lab, v, col) in enumerate(bar):
            wseg = int(920 * v / tot)
            seg = (x, yb, x + wseg - (14 if i < len(bar) - 1 else 0), yb + 72)
            if pb > 0:
                r = (seg[0], seg[1], seg[0] + max(2, int((seg[2] - seg[0]) * pb)), seg[3])
                c.d.rectangle(r, fill={"up": UP, "green": DOWN, "ink": INK, "copper": COPPER}[col])
                c.elems.append((f"長條{i + 1}", r))
                c.text(f"長條標{i + 1}", (seg[0] + (seg[2] - seg[0]) // 2, yb + 84), lab, 32, GRAY, anchor="ma", alpha=pb)
            x += wseg
        yd = yb + 84 + 56
    else:
        yd = yb
    if n.get("detail") and stagger(t, 3.0, 0, 0) > 0:
        draw_lines(c, "算式", wrap_px(n["detail"], 38, 920), 80, yd, 38, GRAY, t, 3.0, 0.2, lh=1.7)


def scene_question(c, sp, t):
    q = sp["question"]
    c.pill("類別", (540, 440), "二選一", 40, PAPER, COPPER, alpha=stagger(t, 0.0, 0, 0), anchor="c")
    ql = [x for part in q["q"] for x in wrap(part, 11)]
    size = fit_size(ql, 72, 100)
    y = draw_lines(c, "問題", ql, 540, 560, size, PAPER, t, 0.1, 0.25, anchor="ma", lh=1.3)
    for i, (lab, key) in enumerate((("A", "a"), ("B", "b"))):
        p = stagger(t, 1.0, 0.35, i)
        if p > 0:
            top = y + 50 + i * 210 + int((1 - p) * 40)
            c.card(f"選項{lab}", (80, top, 1000, top + 170), lab, q[key], 60, PAPER, INK, alpha=p)
    p = stagger(t, 2.2, 0, 0)
    if p > 0:
        c.text("邀請", (540, y + 50 + 2 * 210 + 10), "留言告訴我 A 或 B", 46, BRIGHT, anchor="ma", alpha=p)


def build_scenes(sp):
    scenes = [("hook", 3.6, None)]
    if sp.get("numbers"):                       # 週報：三個數字
        for n in sp["numbers"]:
            scenes.append(("number", 5.2, n))
    else:
        pts = sp["points"]
        if sp.get("number"):
            pts = pts[:2]
        for i, pt in enumerate(pts):
            scenes.append(("point", 4.4, (i + 1, len(pts), pt[0], pt[1], pt[2] if len(pt) > 2 else "")))
        if sp.get("number"):
            scenes.append(("number", 5.6, sp["number"]))
    scenes.append(("question", 4.6, None))
    return scenes


def render_frame(sp, scenes, f_idx, total_dur):
    t_all = f_idx / FPS
    acc = 0.0
    for kind, dur, arg in scenes:
        if t_all < acc + dur or (kind, dur, arg) == scenes[-1]:
            break
        acc += dur
    t = t_all - acc
    dark = kind in ("hook", "question")
    c = Canvas(INK if dark else PAPER, 11 if dark else -7, t_all)
    chrome(c, dark, sp["tag"] if kind != "hook" else "台股小知識", min(1.0, t_all / total_dur), t_all)
    if kind == "hook":
        scene_hook(c, sp, t)
    elif kind == "point":
        scene_point(c, sp, t, *arg)
    elif kind == "number":
        scene_number(c, sp, t, arg)
    else:
        scene_question(c, sp, t)
    return c, kind


# ---------- 重疊檢查 ----------
def inflate(b, p=PAD):
    return (b[0] - p, b[1] - p, b[2] + p, b[3] + p)


def overlap_area(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return w * h if w > 0 and h > 0 else 0


def check_frame(elems):
    """回傳 [(類型, 元素甲, 元素乙, 面積)]。進度條與免責是固定元素，也一起比。"""
    bad = []
    for i in range(len(elems)):
        n1, b1 = elems[i]
        if b1[0] < SAFE_X[0] or b1[2] > SAFE_X[1] or b1[3] > SAFE_Y[1] or (b1[1] < SAFE_Y[0]):
            bad.append(("出安全框", n1, "", 0))
        for j in range(i + 1, len(elems)):
            n2, b2 = elems[j]
            a = overlap_area(inflate(b1), inflate(b2))
            if a > 0:
                bad.append(("重疊", n1, n2, a))
    return bad


# ---------- 選題與合規 ----------
def lint_topic(sp) -> list[str]:
    errs = []
    texts = list(sp["hook"]) + [sp["sub"], sp["caption"]] + [x for p in sp.get("points", []) for x in p]
    texts += list(sp["question"]["q"]) + [sp["question"]["a"], sp["question"]["b"]]
    for n in ([sp["number"]] if sp.get("number") else []) + list(sp.get("numbers", [])):
        texts += [n["label"], n.get("detail", ""), n.get("plain", "")]
    for s in texts:
        for w in BANNED:
            if w in s:
                errs.append(f"含禁用詞「{w}」：{s}")
        if ADVICE.search(s):
            errs.append(f"疑似買賣建議：{s}")
        if STOCK_CODE.search(s):
            errs.append(f"疑似個股代號：{s}")
    for ln in list(sp["hook"]) + list(sp["question"]["q"]) + [p[0] for p in sp.get("points", [])]:
        for seg in wrap(ln, 12):
            if units(seg) > 12:
                errs.append(f"單行超過 12 字：{seg}")
    cap = sp["caption"] + " " + " ".join(sp["tags"])
    if len(cap) > 100:
        errs.append(f"文案 {len(cap)} 字，超過 100")
    if not 3 <= len(sp["tags"]) <= 5:
        errs.append("hashtag 要 3～5 個")
    return errs


def weekly_numbers(data_dir: Path | None = None):
    """週報三個數字（只陳述事實）：加權指數週漲跌點數、外資本週買賣超、本週成交值最大族群。
    讀資料湖：market_daily（加權指數、成交值）、inst_market_first（三大法人買賣超）、price_daily＋groups.yaml（族群成交值）。
    資料不足回 None（呼叫端改用題庫，不整段不做）。"""
    import glob

    import pandas as pd
    import yaml
    dd = Path(data_dir) if data_dir else ROOT / "data"

    def rd(name, cols=None, last=1):
        fs = sorted(glob.glob(str(dd / name / "**" / "*.parquet"), recursive=True))[-last:]
        if not fs:
            raise ValueError(f"沒有 {name}")
        return pd.concat([pd.read_parquet(f, columns=cols) for f in fs])
    try:
        m = rd("market_daily", last=2).drop_duplicates("date", keep="last").sort_values("date")
        m["d"] = pd.to_datetime(m["date"])
        last = m["d"].iloc[-1]
        wk = m[(m["d"].dt.isocalendar().week == last.isocalendar().week) & (m["d"].dt.year == last.year)]
        prev = m[m["d"] < wk["d"].iloc[0]]
        if len(wk) < 2 or prev.empty:
            return None
        dates = [d.strftime("%Y-%m-%d") for d in wk["d"]]
        span = f"{wk['d'].iloc[0].month}/{wk['d'].iloc[0].day}～{last.month}/{last.day}"
        close, pclose = float(wk["taiex"].iloc[-1]), float(prev["taiex"].iloc[-1])
        pts = close - pclose
        inst = rd("inst_market_first").drop_duplicates("date", keep="last")
        inst = inst[inst["date"].isin(dates)]
        if len(inst) < len(dates) - 1:
            return None
        fnet = float((inst["foreign_buy"] - inst["foreign_sell"]).sum()) / 1e8
        px = rd("price_daily", ["date", "code", "turnover"])
        px = px[px["date"].isin(dates)]
        by_code = px.groupby("code")["turnover"].sum()
        groups = yaml.safe_load((ROOT / "pipeline" / "groups" / "groups.yaml").read_text(encoding="utf-8"))["groups"]
        best = max(((g["name"], float(by_code.reindex([str(c) for c in g.get("codes", [])]).sum())) for g in groups.values()),
                   key=lambda x: x[1])
        mkt = float(wk["turnover"].sum())
    except (ValueError, KeyError, OSError, IndexError) as e:
        print(f"::warning::週報資料讀取失敗：{e!r}", flush=True)
        return None
    up = pts >= 0
    num = [
        {"pill": "數字 1／3", "label": f"加權指數本週{'上漲' if up else '下跌'}", "value": round(abs(pts)), "suffix": " 點",
         "color": "up" if up else "green",
         "plain": f"收盤 {close:,.0f} 點，{pts / pclose * 100:+.2f}%",
         "detail": f"統計 {span}，對比上週最後一個交易日收盤 {pclose:,.0f} 點"},
        {"pill": "數字 2／3", "label": f"外資本週{'買超' if fnet >= 0 else '賣超'}", "value": round(abs(fnet)), "suffix": " 億元",
         "color": "up" if fnet >= 0 else "green",
         "plain": f"外資本週合計{'買超' if fnet >= 0 else '賣超'}約 {abs(fnet):,.0f} 億元（上市市場）",
         "detail": f"統計 {span}，資料來源：三大法人買賣金額統計"},
        {"pill": "數字 3／3", "label": f"本週成交值最大族群：{best[0]}", "value": round(best[1] / 1e8), "suffix": " 億元",
         "color": "ink",
         "plain": f"約占全市場本週成交值的 {best[1] / mkt * 100:.0f}%",
         "detail": f"統計 {span}，族群成分股成交值加總（成分股可能與其他族群重疊）"},
    ]
    cap = (f"本週台股 3 個數字：加權指數{'上漲' if up else '下跌'} {abs(pts):,.0f} 點、外資{'買超' if fnet >= 0 else '賣超'} "
           f"{abs(fnet):,.0f} 億元、成交值最大族群是{best[0]}。")
    return {"id": "weekly3", "tag": "本週數字", "hook": ["本週台股", "3 個數字"], "sub": "週漲跌・外資・成交值",
            "numbers": num, "keywords": [],
            "question": {"q": ["這 3 個數字", "你最在意哪個？"], "a": "外資買賣超", "b": "族群成交值"},
            "caption": cap, "tags": ["#台股", "#本週回顧", "#哩股哩股"], "points": []}


def load_bank():
    return json.loads(BANK.read_text(encoding="utf-8"))["topics"]


def load_state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"used": []}


def hot_posts(days=14, now=None):
    """metrics.csv 每則貼文取最後一筆，近 days 天、依觀看數由高到低。"""
    try:
        rows = list(csv.DictReader(METRICS.open(encoding="utf-8")))
    except OSError:
        return []
    now = now or datetime.now(timezone.utc)
    latest = {}
    for r in rows:
        latest[r["post_id"]] = r
    out = []
    for r in latest.values():
        try:
            ts = datetime.strptime(r["posted_at"], "%Y-%m-%dT%H:%M:%S%z")
            v = int(float(r["views"] or 0))
        except (ValueError, KeyError):
            continue
        if now - ts <= timedelta(days=days):
            out.append((v, r["text_head"]))
    return sorted(out, reverse=True)


def pick_topic(bank, state, want=None, today=None):
    today = today or datetime.now(TAIPEI).date()
    if want:
        for t in bank:
            if t["id"] == want:
                return t, "指定"
        raise SystemExit(f"題庫沒有 id={want}")
    last = {}
    for u in state.get("used", []):
        last[u["id"]] = u["date"]
    recent = {i for i, d in last.items() if (today - datetime.fromisoformat(d).date()).days < 28}
    for v, head in hot_posts():
        for t in bank:
            if t["id"] not in recent and any(k in head for k in t["keywords"]):
                return t, f"Threads 熱點文（觀看 {v}）：{head[:30]}"
    ranked = sorted(bank, key=lambda t: last.get(t["id"], "0000-00-00"))
    return ranked[0], "題庫輪替（最久沒用過）"


# ---------- 渲染 ----------
def render(sp, out_mp4: Path, report: Path, limit_frames=None):
    scenes = build_scenes(sp)
    total = sum(d for _, d, _ in scenes)
    n = int(round(total * FPS))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
           "-c:a", "aac", "-b:a", "96k", str(out_mp4)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    hits, per_scene = [], {}
    for i in range(n):
        c, kind = render_frame(sp, scenes, i, total)
        bad = check_frame(c.elems)
        per_scene[kind] = per_scene.get(kind, 0) + 1
        for b in bad:
            hits.append((i, kind, *b))
        p.stdin.write(c.img.tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise SystemExit("ffmpeg 編碼失敗")
    lines = [f"# overlap_report（{sp['id']}）", "",
             f"- 影片：{out_mp4.name}，{W}×{H}，{n} 幀（{total:.1f} 秒，{FPS} fps）",
             f"- 程式檢查：{n} 幀，{len(hits)} 筆（元素外框外擴 {PAD}px 兩兩比對＋安全框）",
             f"- 各場景幀數：{per_scene}", ""]
    if hits:
        lines.append("| 幀 | 秒 | 場景 | 類型 | 元素甲 | 元素乙 | 面積 |\n|---|---|---|---|---|---|---|")
        for h in hits[:200]:
            lines.append(f"| {h[0]} | {h[0] / FPS:.2f} | {h[1]} | {h[2]} | {h[3]} | {h[4]} | {h[5]} |")
    else:
        lines.append("結果：0 筆重疊。")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return n, len(hits), total


def freeze_check(mp4: Path) -> int:
    """ffmpeg freezedetect（規則 9：n=0.003 d=0.5）；回傳停格段數。"""
    r = subprocess.run(["ffmpeg", "-i", str(mp4), "-vf", "freezedetect=n=0.003:d=0.5", "-an", "-f", "null", "-"],
                       capture_output=True, text=True)
    return r.stderr.count("freeze_start")


def write_queue(sp, mp4_rel: str, approved: bool):
    now = datetime.now(TAIPEI)
    name = f"{now.strftime('%Y-%m-%d')}_reel-{sp['id']}.md"
    cap = sp["caption"] + "\n\n" + " ".join(sp["tags"])
    body = (f"---\nstatus: {'approved' if approved else 'draft'}\npublish_at: {now.strftime('%Y-%m-%dT%H:%M+08:00')}\n"
            f"title: IG 短影片 {sp['id']}\nvideo: {mp4_rel}\n---\n{cap}\n")
    QUEUE.mkdir(parents=True, exist_ok=True)
    (QUEUE / name).write_text(body, encoding="utf-8")
    return name


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    ap.add_argument("--topic", default="")
    ap.add_argument("--sample", action="store_true", help="只產影片與報告，不寫佇列、不改 state")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--kind", choices=["auto", "bank", "weekly"], default="auto",
                    help="auto＝週四做『本週台股 3 個數字』，其他天用題庫；weekly 讀不到資料會改用題庫")
    ap.add_argument("--data", default="", help="資料湖資料夾（預設 repo 的 data/）")
    ap.add_argument("--approved", choices=["auto", "yes", "no"], default="auto",
                    help="auto＝看 post_quota.json 的 ig.reels_need_review；yes／no 強制")
    a = ap.parse_args(argv)
    bank = load_bank()
    if a.list:
        for t in bank:
            print(t["id"], "|", "".join(t["hook"]), "|", lint_topic(t) or "合規OK")
        return 0
    sys.path.insert(0, str(ROOT / "scripts"))
    import post_quota
    q = post_quota.load()
    if not a.sample and not post_quota.reels_enabled(q):
        print(f"{post_quota.SKIP_MSG}（post_quota.json ig.reels_weekly=false）")
        return 0
    sp, why = None, ""
    kind = a.kind if a.kind != "auto" else ("weekly" if (datetime.now(TAIPEI).weekday() == 3 and not a.topic) else "bank")
    if kind == "weekly":
        sp = weekly_numbers(a.data or None)
        why = "週報：本週 3 個數字（資料湖）"
        if sp is None:
            print("::warning::週報資料不足，改用題庫", flush=True)
    if sp is None:
        sp, why = pick_topic(bank, load_state(), a.topic or None)
    print(f"選題：{sp['id']}（{why}）")
    errs = lint_topic(sp)
    if errs:
        print("題庫合規檢查未過：", *errs, sep="\n  ", file=sys.stderr)
        # 保底：換下一個合規的題，不讓整段不做
        ok = [t for t in bank if not lint_topic(t) and t["id"] != sp["id"]]
        if not ok:
            return 2
        sp = ok[0]
        print(f"改用：{sp['id']}")
    out = Path(a.out or ".")
    out.mkdir(parents=True, exist_ok=True)
    day = datetime.now(TAIPEI).strftime("%Y-%m-%d")
    mp4 = out / f"{day}_reel-{sp['id']}.mp4"
    n, bad, dur = render(sp, mp4, out / "overlap_report.md")
    frz = freeze_check(mp4)
    print(f"重疊檢查：程式 {n} 幀 {bad} 筆；停格 {frz} 段；長度 {dur:.1f} 秒")
    if bad or frz:
        print("不出片：重疊或停格未通過", file=sys.stderr)
        return 3
    if a.sample:
        return 0
    need_review = post_quota.reels_need_review(q)
    approved = {"yes": True, "no": False}.get(a.approved, not need_review)
    qname = write_queue(sp, mp4.relative_to(ROOT).as_posix() if mp4.is_relative_to(ROOT) else mp4.as_posix(), approved)
    st = load_state()
    st["used"] = (st.get("used", []) + [{"id": sp["id"], "date": day}])[-60:]
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"佇列檔：{qname}（status: {'approved' if approved else 'draft，待 CEO 看樣片'}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
