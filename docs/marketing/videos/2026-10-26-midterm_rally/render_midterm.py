"""〈台股自高點回落 7.6%，11 月期中選舉行情還在嗎？〉敘事短片渲染器（1080×1920、30fps）。

用法（repo 根目錄）：
    python docs/marketing/videos/2026-10-26-midterm_rally/render_midterm.py --frames 1.0,12.5   # 單格
    python docs/marketing/videos/2026-10-26-midterm_rally/render_midterm.py --sheet 0,70         # 每 0.5 秒存抽格
    python docs/marketing/videos/2026-10-26-midterm_rally/render_midterm.py                       # 出片（無聲）＋檢查報告
    python docs/marketing/videos/2026-10-26-midterm_rally/render_midterm.py --cover               # 封面

版面（由上到下；任兩個元素的外框不相交）：
  大字 170–290 ｜ 副標 300–350 ｜ 數字列 378–545 ｜ 圖 565–1122 ｜ 圖註 1130–1226 ｜ 字幕條 1236–1346 ｜ 頁腳 1366–1432 ｜ 比比 1440 以下
文字安全區：x 48–900（右側留給平台按鈕）、y 150–1440。
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import multiprocessing as mp
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mt_core import *   # noqa: F401,F403
import mt_core as mc

# ───────────────────────── 資料 ─────────────────────────
def read_csv(name):
    with open(CHART / name, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


TAIEX = [(r["date"], float(r["close"])) for r in read_csv("taiex_0901_1022_close.csv")]
CLOSE = [c for _, c in TAIEX]
DATES = [d for d, _ in TAIEX]
NPT = len(CLOSE)
PEAK = int(np.argmax(CLOSE))
assert DATES[PEAK] == "2026-10-06" and abs(CLOSE[PEAK] - 49822.55) < 0.01
assert abs(CLOSE[-1] - 46041.43) < 0.01
DROPS = [(r["date"], float(r["pts"]), float(r["pct"])) for r in read_csv("taiex_top10_daily_point_drops.csv")]
WORLD = {r["index"]: float(r["pct_change"]) for r in read_csv("index_since_1006_peak.csv")}
assert abs(WORLD["台灣加權指數"] + 7.59) < 1e-9 and abs(WORLD["費城半導體"] + 18.45) < 1e-9

FOOT1 = "非投資建議｜僅為歷史統計，不代表未來"
FOOT2 = "資料日：台股 2026-10-22、美股 2026-10-23 收盤"
DISCLAIMER = "本內容為公開資料整理，不構成任何投資建議；投資有風險，請自行判斷。"
BIBI_SIZE = 440
BIBI_CX, BIBI_FOOT = 235, 1890

# 字幕（一次一行、≤13 字）：(配音裡的起點片段, 顯示文字, 關鍵字)
CHUNKS = {
    "S01": [("台股兩週", "台股兩週回落7.6%", ["7.6%"]), ("選舉行情還在嗎", "選舉行情還在嗎？", ["選舉行情"])],
    "S02": [("先校正", "先校正：這不是歷史新紀錄", ["新紀錄"])],
    "S03": [("十月六日", "10/06 加權創高", ["創高"]), ("二十二日", "10/22 回落7.6%", ["7.6%"])],
    "S04": [("單日最大", "單日最大跌點，", ["最大跌點"]), ("仍是七月", "仍是7月17日", ["7月17日"])],
    "S05": [("美股方面", "美股方面，費半自10/06", ["費半"]), ("回落", "回落約18.5%", ["18.5%"])],
    "S06": [("歷史怎麼說", "歷史怎麼說？", []), ("標普五百", "標普500，選後12個月", ["12個月"])],
    "S07": [("一九五零年", "1950 年以來，", []), ("十九次", "19次樣本都是正報酬", ["正報酬"])],
    "S08": [("選舉年", "選舉年第四季，", ["第四季"]), ("平均漲", "平均漲6.6%，84%收高", ["6.6%", "84%"])],
    "S09": [("但選前", "但選前常先跌，", ["先跌"]), ("平均最大", "平均最大回檔17.5%", ["17.5%"])],
    "S10": [("樣本僅", "樣本僅19次，", ["19次"]), ("起算年份", "起算年份也影響結論", ["起算年份"])],
    "S11": [("二零一八", "2018 年，選後仍跌到12月底", ["2018 年"])],
    "S12": [("台股沒有", "台股沒有可信的", ["台股"]), ("選後統計", "選後統計，不硬湊", ["不硬湊"])],
    "S13": [("這次變數", "這次變數不同。", ["變數"]), ("九月美國", "9月美國通膨3.7%", ["3.7%"])],
    "S14": [("高於預期", "高於預期，升息機率約5成", ["升息機率"])],
    "S15": [("AI", "AI 融資成本，也是壓力", ["AI 融資成本"])],
    "S16": [("觀察三件事", "觀察三件事。", ["三件事"]), ("一，", "一，聯準會與通膨", ["聯準會"])],
    "S17": [("二，", "二，費半與", ["費半"]), ("AI", "AI 融資是否止穩", ["AI 融資"])],
    "S18": [("三，", "三，開票後波動率是否降溫", ["波動率"])],
    "S19": [("歷史偏強", "歷史偏強，但不保證這次一樣", ["不保證"])],
    "S20": [("想看資料", "想看資料整理，", ["資料整理"]), ("搜尋哩股", "搜尋「哩股哩股」", ["哩股哩股"])],
    "S21": [("本內容", "本內容為公開資料整理", [])],
    "S22": [("不構成", "不構成任何投資建議", [])],
    "S23": [("投資有風險", "投資有風險，請自行判斷", ["投資有風險"])],
}

# 比比動作：(句, 錨點, 素材)
ACTS = {
    "S01": [("", "clock")], "S02": [("", "tilt")], "S03": [("", "magnifier"), ("二十二日", "point_dr_v2")],
    "S04": [("", "point_ur_v2"), ("七月", "face_shock")], "S05": [("", "globe")],
    "S06": [("", "calendar")], "S07": [("", "face_nod_v2")], "S08": [("", "wow")],
    "S09": [("", "face_sweat")], "S10": [("", "face_think_v2")], "S11": [("", "sulk_curl")], "S12": [("", "face_think_v2")],
    "S13": [("", "news")], "S14": [("", "face_sweat")], "S15": [("", "face_shock")],
    "S16": [("", "point_r_v2")], "S17": [("", "point_r_v2")], "S18": [("", "hourglass")],
    "S19": [("", "face_think_v2")], "S20": [("", "invite_nod")], "S21": [("", "face_bow")],
}
ALT = "face_nod_v2"

SCENE_DEF = [
    ("A1", ["S01"]), ("A2", ["S02"]), ("A3", ["S03"]), ("B", ["S04"]), ("C", ["S05"]), ("D", ["S06", "S07"]), ("E", ["S08"]),
    ("F", ["S09"]), ("L", ["S10", "S11"]), ("G", ["S12"]), ("H", ["S13", "S14", "S15"]), ("I", ["S16", "S17", "S18"]),
    ("J", ["S19"]), ("K", ["S20", "S21", "S22", "S23"]),
]
GAP_BEFORE = {"S02": 0.30, "S03": 0.40, "S04": 0.30, "S05": 0.30, "S06": 0.32, "S07": 0.10, "S08": 0.40,
              "S09": 0.28, "S10": 0.32, "S11": 0.14, "S12": 0.40, "S13": 0.45, "S14": 0.10, "S15": 0.28, "S16": 0.40, "S17": 0.14,
              "S18": 0.14, "S19": 0.50, "S20": 0.45, "S21": 0.45, "S22": 0.12, "S23": 0.12}
T0 = 0.20
END_HOLD = 0.9

LINES: dict[str, Line] = {}
SCENES: list[tuple] = []     # (id, [line ids], s0, s1)
SUBS: list[tuple] = []       # (text, hl, t0, t1, lid, spoken_start_idx, expected_pause_time or None)
ACT_TL: list[tuple] = []
END_T = 0.0
TOTAL = 0.0


def build_timeline():
    global END_T, TOTAL
    spec = json.loads(SCRIPT.read_text(encoding="utf-8"))
    texts = {x["id"]: x["text"] for x in spec["lines"]}
    t = T0
    order = [lid for _, ids in SCENE_DEF for lid in ids]
    for lid in order:
        ln = Line(lid, texts[lid])
        t += GAP_BEFORE.get(lid, 0.0)
        ln.start = t
        LINES[lid] = ln
        t = ln.end
    END_T = t
    TOTAL = round((END_T + END_HOLD) * FPS) / FPS
    for i, (sid, ids) in enumerate(SCENE_DEF):
        s0 = 0.0 if i == 0 else LINES[ids[0]].start - 0.22
        s1 = (LINES[SCENE_DEF[i + 1][1][0]].start - 0.22) if i + 1 < len(SCENE_DEF) else TOTAL
        SCENES.append((sid, ids, s0, s1))
    # 字幕時間
    raw = []
    for lid in order:
        ln = LINES[lid]
        for (frag, disp, hl) in CHUNKS[lid]:
            k = ln.text.find(frag)
            assert k >= 0, (lid, frag)
            tt = ln.frac_t(k)
            shift = 0.0
            if k > 0 and not any(pm[0] == k - 1 for pm in ln.pause_marks):
                tt, shift = ln.snap(tt)
            raw.append([disp, hl, tt, None, lid, k, shift])
    for i, r in enumerate(raw):
        nxt = raw[i + 1][2] if i + 1 < len(raw) else TOTAL
        ln_end = LINES[r[4]].end + 0.45
        r[3] = min(nxt, max(ln_end, r[2] + 1.0)) if i + 1 < len(raw) else TOTAL
        if r[3] > nxt:
            r[3] = nxt
        SUBS.append(tuple(r))
    # 比比
    pts = []
    for lid in order:
        if lid not in ACTS:
            continue
        for (anchor, name) in ACTS[lid]:
            pts.append((LINES[lid].at(anchor) if anchor else LINES[lid].start - 0.1, name))
    pts[0] = (0.0, pts[0][1])
    pts.append((END_T + 0.1, "wave"))
    pts.sort()
    for i, (st, name) in enumerate(pts):
        en = pts[i + 1][0] if i + 1 < len(pts) else TOTAL
        a, n, s0 = st, name, st
        while en - a > 3.2:
            m = a + 2.8
            ACT_TL.append((a, m, n, s0))
            a, n, s0 = m, ALT, m
        ACT_TL.append((a, en, n, s0))


def cur(t, seq):
    """seq: [(t0, val)...] 依時間排序，回傳 t 時刻最新的 (t0, val)；尚未開始回 None。"""
    out = None
    for it in seq:
        if t >= it[0]:
            out = it
    return out


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


def bibi_at(t):
    for a, b, n, s0 in ACT_TL:
        if a <= t < b:
            return n, t - s0
    a, b, n, s0 = ACT_TL[-1]
    return n, t - s0


def draw_bibi(t, cx=BIBI_CX, foot=BIBI_FOOT, name=None, bt=None):
    nm, tt = bibi_at(t) if name is None else (name, bt)
    fr = bibi_frames(nm)
    n = len(fr)
    L = lib_lengths().get(nm, (n, 1.0))[1]
    i = int((tt % L) / L * n) % n
    s = BIBI_SIZE / 512
    ox, oy = int(round(cx - 248 * s)), int(round(foot - 482 * s))

    def fn(cv, reg):
        cv.alpha_composite(fr[i], (ox, oy))
        b = bibi_bbox(nm, i)
        reg.add("比比", (ox + b[0], oy + b[1], ox + b[2], oy + b[3]))
        reg.inside("比比", (ox + b[0], oy + b[1], ox + b[2], oy + b[3]), (0, 1440, W, H))
    return fn


# ───────────────────────── 版面零件 ─────────────────────────
def title(cv, text, hl, p, sub=None, subp=None):
    if p <= 0:
        return
    size = 104
    while size > 60:
        f = font(F_BLACK, size)
        if f.getlength(text) <= SAFE_X1 - 60:
            break
        size -= 4
    f = font(F_BLACK, size)
    x, y = 60, 172
    if hl and hl in text:
        i = text.index(hl)
        pre, post = text[:i], text[i + len(hl):]
        xx = x
        clip = x + f.getlength(text) * ease_out(p) + 2
        for part, col, nm in ((pre, TXT, "大字a"), (hl, ORANGE, "大字b"), (post, TXT, "大字c")):
            if part:
                cv.text(nm, part, xx, y, f, col, p, grp="大字", ref=text, clip_x=clip)
                xx += f.getlength(part)
    else:
        cv.text("大字", text, x, y, f, TXT, p)
    if sub:
        cv.text("副標", sub, 60, 304, font(F_BOLD, 40), TEAL, p if subp is None else subp)


def strip(cv, label, p_label, number, col, p_num, size=104, extra=None):
    """數字列：label 36px；number 大字；extra=[(text, color, size, dx, dy, p)] 接在數字右側。"""
    if label and p_label > 0:
        cv.text("數字列標", label, 60, 384, font(F_BOLD, 34), MUTED, p_label)
    nx = 60
    if number and p_num > 0:
        f = font(F_BLACK, size)
        cv.text("數字", number, nx, 432, f, col, p_num)
        nx += f.getlength(number)
    if extra:
        for k, (s, c, sz, dx, dy, pp) in enumerate(extra):
            if pp > 0:
                cv.text(f"數字附{k}", s, nx + dx, 432 + dy, font(F_BLACK, sz), c, pp)
    return nx


def caption(cv, lines, p=1.0):
    """圖註：每行手動斷好（≤ 約 30 字、寬 ≤ 840px），最多 3 行。"""
    f = font(F_MED, 28)
    y = 1128
    if len(lines) > 3:
        cv.reg.issues.append(f"圖註 {len(lines)} 行 > 3")
    for k, s_ in enumerate(lines):
        cv.text(f"圖註{k}", s_, 60, y, f, DIM, p, grp="圖註")
        y += 32


def footer(cv):
    f = font(F_MED, 28)
    cv.text("頁腳1", FOOT1, 60, 1368, f, DIM, grp="頁腳")
    cv.text("頁腳2", FOOT2, 60, 1402, f, MUTED, grp="頁腳")


SUB_BAR = (48, 1236, 900, 1346)


def subtitle(cv, t):
    x0, y0, x1, y1 = SUB_BAR
    if t < SUBS[0][2] - 0.04:
        return
    cv.rrect(x0, y0 + 8, x1 - x0, y1 - y0, 22, CARD_EDGE)
    cv.rrect(x0, y0, x1 - x0, y1 - y0, 22, (20, 30, 46))
    cv.rrect(x0, y0, 10, y1 - y0, 5, ORANGE)
    cv.reg.add("字幕條", (x0, y0, x1, y1 + 8))
    cur_ = None
    for r in SUBS:
        if r[2] - 0.04 <= t < r[3]:
            cur_ = r
    if not cur_:
        return
    disp, hl = cur_[0], cur_[1]
    p = 1.0
    maxw = x1 - x0 - 70
    for px in (68, 64, 60, 56):
        f = font(F_BLACK, px)
        if f.getlength(disp.rstrip("，。；")) <= maxw:
            break
    s = disp.rstrip("，。；")
    # 關鍵字分段上色
    segs = [(s, TXT)]
    for h in hl:
        new = []
        for (seg, col) in segs:
            if col == TXT and h in seg:
                a, b = seg.split(h, 1)
                new += [(a, TXT), (h, ORANGE), (b, TXT)]
            else:
                new.append((seg, col))
        segs = new
    segs = [(a, c) for a, c in segs if a]
    total = sum(f.getlength(a) for a, _ in segs)
    x = x0 + 36 + (maxw - total) / 2
    ty = y0 + (y1 - y0 - px) / 2 - 2
    clip = x + total * ease_out(p) + 2
    for k, (a, c) in enumerate(segs):
        cv.text(f"字幕{k}", a, x, ty, f, c, 1.0, grp="字幕條", slide=0, ref=s)
        x += f.getlength(a)
    # 字幕字要在條內
    cv.reg.inside("字幕字", (x0 + 36 + (maxw - total) / 2, ty, x0 + 36 + (maxw - total) / 2 + total, ty + px), (x0 + 12, y0, x1, y1), inset=8)


# ───────────────────────── 折線圖（加權指數） ─────────────────────────
PX0, PX1, PY0, PY1 = 172, 830, 430, 1060


def catmull(pts, n=10):
    out = []
    P = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            u = k / n
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * u + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * u * u
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * u ** 3) for j in (0, 1)))
    out.append(pts[-1])
    return out


def taiex_chart(cv, view, reach, p_axis=1.0, show_axis=True):
    """view=(i0,i1,ymin,ymax)；reach=已畫到的索引（可小數）。回傳映射函式與折線點。"""
    i0, i1, y0, y1 = view

    def mx(i):
        return PX0 + (i - i0) / (i1 - i0) * (PX1 - PX0)

    def my(v):
        return PY0 + (y1 - v) / (y1 - y0) * (PY1 - PY0)

    c = cv.c
    c.save()
    c.rectangle(PX0 - 6, PY0 - 4, PX1 - PX0 + 12, PY1 - PY0 + 8)
    c.clip()
    # 水平格線
    step = 1000 if (y1 - y0) < 6200 else 2000
    v = math.ceil(y0 / step) * step
    ticks = []
    while v <= y1:
        ticks.append(v)
        cv.line([(PX0 - 6, my(v)), (PX1 + 6, my(v))], GRID, 2)
        v += step
    # 折線
    pts = []
    n_full = int(reach)
    for i in range(n_full + 1):
        pts.append((mx(i), my(CLOSE[i])))
    if reach - n_full > 1e-6 and n_full + 1 < NPT:
        f = reach - n_full
        pts.append((mx(n_full + f), my(CLOSE[n_full] + (CLOSE[n_full + 1] - CLOSE[n_full]) * f)))
    pk_i = min(PEAK, len(pts) - 1)
    # 面積（低透明度純色）
    if len(pts) > 1:
        base = PY1 + 2
        cv.poly_fill(pts + [(pts[-1][0], base), (pts[0][0], base)], (80, 120, 180), 0.10)
        up_pts = pts[:pk_i + 1]
        dn_pts = pts[pk_i:] if len(pts) > pk_i + 1 else []
        if len(up_pts) > 1:
            cv.line(up_pts, UP, 7)
        if len(dn_pts) > 1:
            cv.line(dn_pts, DOWN, 7)
    c.restore()
    # 取樣點（遮擋檢查用）：沿折線每 ~6px 一點
    dense = []
    for a, b in zip(pts[:-1], pts[1:]):
        L = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 6))
        for k in range(L + 1):
            u = k / L
            q = (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)
            if PX0 - 1 <= q[0] <= PX1 + 1:
                dense.append(q)
    cv.reg.poly("折線", dense, "圖")
    # 座標軸文字
    if show_axis:
        for v in ticks:
            cv.text(f"y軸{int(v)}", f"{int(v):,}", PX0 - 16, my(v) - 12, font(F_MED, 28), MUTED, anchor="r", grp=f"y軸{int(v)}")
        want = ["09-01", "09-15", "10-01", "10-15"] if i1 - i0 > 20 else ["10-01", "10-08", "10-15", "10-22"]
        for k, d in enumerate(DATES):
            if d[5:] in want and i0 - 0.01 <= k <= i1 + 0.01:
                lab = d[5:].replace("-", "/").lstrip("0")
                lab = lab.replace("/0", "/") if lab[0] != "1" else lab.replace("/0", "/")
                cv.text(f"x軸{d}", lab, mx(k), PY1 + 16, font(F_MED, 28), MUTED, anchor="c", grp=f"x軸{d}", safe=False)
    return mx, my, pts


# ───────────────────────── 場景（v2：圖放大、下半部有比比＋重點面板） ─────────────────────────
PANEL = (480, 1490, 420, 350)


def panel(cv, label, number, col, p, note=None, size=100, name="面板"):
    """下半部重點面板（比比旁）：標籤＋大數字（寬度自動縮到放得下）＋說明。整段文字一次出現（無逐字）。"""
    if p <= 0:
        return
    x, y, w, h = PANEL
    cv.card(name, x, y, w, h, depth=14, edge=ORANGE, grp=name)
    cv.text(name + "標", label, x + 34, y + 28, font(F_BOLD, 32), MUTED, p, grp=name, reg=False)
    sz = size
    while sz > 48 and font(F_BLACK, sz).getlength(number) > w - 68:
        sz -= 4
    f = font(F_BLACK, sz)
    cv.text(name + "數", number, x + 34, y + 84, f, col, p, grp=name, reg=False)
    cv.reg.inside(name + "數", (x + 34, y + 84, x + 34 + f.getlength(number), y + 84 + sz), (x, y, x + w, y + h), inset=14)
    yy = y + 84 + int(sz * 1.25) + 8
    for k, s in enumerate(note or []):
        nsz = 30
        while nsz > 28 and font(F_MED, nsz).getlength(s) > w - 68:
            nsz -= 1
        nf = font(F_MED, nsz)
        cv.text(f"{name}註{k}", s, x + 34, yy + k * 42, nf, TXT, p, grp=name, reg=False)
        cv.reg.inside(f"{name}註{k}", (x + 34, yy + k * 42, x + 34 + nf.getlength(s), yy + k * 42 + 30), (x, y, x + w, y + h), inset=14)


def sc_taiex(cv, t, S, mode):
    L1, L3 = S["S01"], S["S03"]
    if mode == 1:
        reach_full = False
        tA, tB = L1.at("回落") - 0.15, L1.at("七點六") + 0.1
        if t < tA:
            reach = lerp(0.45 * (NPT - 1), PEAK, ease_io(t / max(0.3, tA)))
        else:
            reach = lerp(PEAK, NPT - 1, ease_io((t - tA) / max(0.3, tB - tA)))
        reach = min(reach, NPT - 1)
        view = (0, NPT - 1, 45000, 51500)
        z = 0.0
    else:
        reach = NPT - 1
        tz = L3.at("十月六日") - 0.15
        z = ease_io((t - tz) / 0.9)
        view = (lerp(0, DATES.index("2026-10-01"), z), NPT - 1, 45000, 51500)
    moving = 0 < z < 1
    mx, my, pts = taiex_chart(cv, view, reach, show_axis=not moving)
    pk = (mx(PEAK), my(CLOSE[PEAK]))
    en = (mx(NPT - 1), my(CLOSE[-1]))
    if reach >= PEAK - 1e-6:
        cv.circle(pk[0], pk[1], 13, BG, stroke=TXT, lw=5)
        cv.reg.add("高點點", (pk[0] - 15, pk[1] - 15, pk[0] + 15, pk[1] + 15), "圖")
    if reach >= NPT - 1 - 1e-6:
        cv.circle(en[0], en[1], 13, DOWN, stroke=TXT, lw=4)
        cv.reg.add("終點點", (en[0] - 15, en[1] - 15, en[0] + 15, en[1] + 15), "圖")
    if mode == 1:
        title(cv, "還有選舉行情嗎？", "選舉行情", 1.0, "台灣加權指數・近兩個月收盤")
        if t < L1.at("回落") - 0.05:
            panel(cv, "10/06 收盤・歷史新高", "49,822.55", TXT, 1.0, ["資料至 2026-10-22"])
        else:
            panel(cv, "10/22 收盤", "46,041.43", TXT, 1.0, ["較 10/06 高點 −7.6%"])
    else:
        title(cv, "創高後回落", "回落", 1.0, "10/06 歷史新高 → 10/22 收盤")
        if not moving:
            if t >= L3.at("十月六日"):
                cv.text("高點標1", "10/06 創高", pk[0], pk[1] - 104, font(F_BOLD, 32), ORANGE, anchor="c", grp="高點標", safe=False)
                cv.text("高點標2", "49,822.55", pk[0], pk[1] - 66, font(F_BLACK, 38), TXT, anchor="c", grp="高點標", safe=False)
                cv.line([(pk[0] + 14, pk[1]), (PX1 + 10, pk[1])], MUTED, 2, dash=[8, 8])
            if t >= L3.at("二十二日"):
                cv.text("終點標", "10/22 收 46,041.43", en[0] + 10, en[1] + 26, font(F_BOLD, 32), TXT, anchor="r", grp="終點標", safe=False)
            if t >= L3.at("七點六"):
                bx = PX1 + 24
                cv.line([(bx, pk[1]), (bx, en[1])], DOWN, 6)
                cv.line([(bx - 12, en[1] - 16), (bx, en[1]), (bx + 12, en[1] - 16)], DOWN, 6)
                cv.line([(bx - 20, en[1]), (en[0] + 14, en[1])], MUTED, 2, dash=[8, 8])
        panel(cv, "10/06 → 10/22", "−7.59%", DOWN, ap(t, L3.start - 0.2, 0.1), ["49,822.55 → 46,041.43"])
    caption(cv, ["資料區間：2026-09-01 至 10-22，加權指數日收盤。", "來源：證交所 OpenAPI；10/06 為 2000 年以來最高收盤。"])


def sc_split(cv, t, S):
    L = S["S02"]
    title(cv, "先校正", None, 1.0, "題目「持續下跌、創歷史紀錄」不成立")
    cv.text("分割標", "下跌創歷史新紀錄？", 60, 430, font(F_BOLD, 34), MUTED)
    if t >= L.at("不是") - 0.1:
        cv.text("否", "否", 60, 490, font(F_BLACK, 300), ORANGE)
        cv.text("不成立", "數據不支持", 60, 830, font(F_BOLD, 48), TXT)
    base, sc_ = 1020, 0.17
    cv.line([(500, base), (890, base)], MUTED, 3)
    items = [(520, "2026-07-17", 2953.71, "史上最大", DOWN), (730, "2026-10-15", 1655.96, "本次", dark(DOWN, 0.35))]
    for i, (x, d, v, tag, col) in enumerate(items):
        gr = ap(t, L.start - 0.1 + i * 0.35, 0.6)
        h = v * sc_ * gr
        if h > 1:
            cv.bar25(f"分割條{i}", x, base - h, 130, h, col, d=22, grp=f"分割條{i}")
        if gr >= 1:
            cv.text(f"分割值{i}", f"−{v:,.2f}", x + 75, base - h - 24 - 56, font(F_BLACK, 34), TXT, anchor="c", grp=f"分割值{i}")
            cv.text(f"分割日{i}", d[5:].replace("-", "/"), x + 65, base + 12, font(F_BOLD, 30), TXT, anchor="c", grp=f"分割日{i}", safe=False)
            cv.text(f"分割註{i}", tag, x + 65, base + 50, font(F_MED, 28), MUTED, anchor="c", grp=f"分割註{i}", safe=False)
    panel(cv, "最大單日跌點", "7/17", DOWN, ap(t, L.start - 0.2, 0.1), ["−2,953.71 點", "−6.47%・至今仍是紀錄"])
    caption(cv, ["資料區間：2021-06-07 至 2026-10-22，加權指數日收盤。", "來源：證交所 OpenAPI；7/17、10/15 另見媒體報導。"])


def sc_drops(cv, t, S):
    L = S["S04"]
    t_a = L.at("七月")
    title(cv, "單日最大跌點", "最大跌點", 1.0, "加權指數・單日跌點前十")
    x0, scale = 270, 380 / 2953.71
    dim = ease_io((t - t_a) / 0.5)
    for i, (d, pts_, pct) in enumerate(DROPS):
        y = 410 + i * 66
        gr = ap(t, L.start - 0.2 + i * 0.06, 0.5)
        hl = i in (0, 5)
        col = DOWN if hl else tuple(int(lerp(DOWN[k], dark(DOWN, 0.55)[k], dim)) for k in range(3))
        if gr > 0.02:
            cv.text(f"日期{i}", d, 60, y + 6, font(F_MED, 30), TXT if hl else tuple(int(lerp(DIM[k], MUTED[k], dim)) for k in range(3)),
                    grp=f"日期{i}", safe=False)
        w = abs(pts_) * scale * gr
        if gr > 0.02:
            cv.hbar25(f"條{i}", x0, y, w, 44, col, d=14, grp=f"條{i}")
            if gr >= 1:
                fv = font(F_BLACK if hl else F_BOLD, 30)
                s_ = f"−{abs(pts_):,.2f}"
                cv.text(f"值{i}", s_, x0 + w + 26, y + 6, fv, TXT if hl else MUTED, grp=f"值{i}")
                if i == 5:
                    vx = x0 + w + 26 + fv.getlength(s_) + 24
                    fc = font(F_BOLD, 28)
                    cw_ = fc.getlength("本次 10/15") + 36
                    cv.rrect(vx, y + 2, cw_, 40, 20, ORANGE)
                    cv.reg.add("本次標", (vx, y + 2, vx + cw_, y + 42), "本次標")
                    cv.text("本次字", "本次 10/15", vx + 18, y + 7, fc, (30, 20, 8), grp="本次標", safe=False, reg=False)
    panel(cv, "07/17・−6.47%", "−2,953.71 點", DOWN, ap(t, L.start - 0.2, 0.1), ["史上最大單日跌點", "10/15 −1,655.96 點排第 6"])
    caption(cv, ["資料區間：2021-06-07 至 2026-10-22，加權指數日收盤。", "來源：證交所 OpenAPI；7/17、10/15 另見媒體報導。"])


def sc_world(cv, t, S):
    L = S["S05"]
    title(cv, "自 10/06 的漲跌", "漲跌", 1.0, "台股與美股四大指數")
    order = [("費城半導體", WORLD["費城半導體"]), ("台灣加權", WORLD["台灣加權指數"]), ("那斯達克", WORLD["那斯達克綜合"]),
             ("S&P 500", WORLD["S&P 500"]), ("道瓊工業", WORLD["道瓊工業"])]
    zx, sc_ = 660, 410 / 18.45
    hi = ease_io((t - L.at("費半")) / 0.5)
    for i, (nm, v) in enumerate(order):
        y = 430 + i * 128
        gr = ap(t, L.start - 0.18 + i * 0.1, 0.5)
        base = UP if v > 0 else DOWN
        col = base if i == 0 else tuple(int(lerp(base[k], dark(base, 0.50)[k], hi)) for k in range(3))
        if gr > 0.02:
            cv.text(f"名{i}", nm, 60, y + 14, font(F_BOLD, 34), TXT if i == 0 else tuple(int(lerp(TXT[k], MUTED[k], hi)) for k in range(3)), grp=f"名{i}")
        w = abs(v) * sc_ * gr
        if gr > 0.02:
            if v < 0:
                cv.hbar25(f"世界條{i}", zx - w, y, w, 72, col, d=16, grp=f"世界條{i}")
            else:
                cv.hbar25(f"世界條{i}", zx, y, max(w, 2), 72, col, d=16, grp=f"世界條{i}")
        if gr >= 1:
            lx = zx + 36 if v < 0 else zx + abs(v) * sc_ + 44
            s = f"−{abs(v):.2f}%" if v < 0 else f"+{v:.2f}%"
            cv.text(f"世界值{i}", s, lx, y + 14, font(F_BLACK, 38), TXT if i == 0 else MUTED, grp=f"世界值{i}")
    cv.line([(zx, 410), (zx, 1090)], MUTED, 2)
    panel(cv, "費半・自 10/06 收盤", "−18.45%", DOWN, ap(t, L.start - 0.2, 0.1), ["台股 −7.59%｜那指 −5.96%", "標普 −2.5%｜道瓊 +1.35%"])
    caption(cv, ["基期 2026-10-06 收盤；台股至 10-22、美股至 10-23。", "道瓊 10-06 並非其高點。來源：證交所 OpenAPI、Yahoo Finance。"])


STATS = [("Capital Group", "1950–2022・19 次", 15.4), ("BNY／Carson", "1950–2022・19 次", 16.6), ("LPL Research", "1954–2022・18 次", 18.2)]


def sc_stats(cv, t, S):
    L6, L7 = S["S06"], S["S07"]
    if t < L7.start - 0.1:
        title(cv, "歷史怎麼說？", "歷史", 1.0, "美國期中選舉日：2026-11-03")
    else:
        title(cv, "選後 12 個月", "12 個月", 1.0, "標普 500 平均報酬（各家彙總值）")
    t_bars = L6.start - 0.3
    base_y, bw, sc_ = 1030, 160, 30.0
    centers = [190, 470, 750]
    cv.line([(60, base_y), (895, base_y)], MUTED, 3)
    for i, (nm, sm, v) in enumerate(STATS):
        gr = ap(t, t_bars + 0.1 + i * 0.18, 0.7)
        h = v * sc_ * gr
        x = centers[i] - bw / 2
        if h > 1:
            cv.bar25(f"選後條{i}", x, base_y - h, bw, h, UP, d=24, grp=f"選後條{i}")
        if gr >= 1:
            cv.text(f"選後值{i}", f"{v:.1f}%", centers[i] + 8, base_y - h - 24 - 56, font(F_BLACK, 46), TXT, anchor="c", grp=f"選後值{i}")
        if gr > 0.3:
            cv.text(f"商名{i}", nm, centers[i], base_y + 12, font(F_BOLD, 28), TXT, anchor="c", grp=f"商名{i}", safe=False)
            cv.text(f"樣本{i}", sm, centers[i], base_y + 48, font(F_MED, 28), MUTED, anchor="c", grp=f"樣本{i}", safe=False)
    note = ["各家彙總值，非逐年"] + (["樣本內皆為正報酬（19 次）"] if t >= L7.at("正報酬") - 0.1 else [])
    panel(cv, "標普 500・選後 12 個月", "約 15%～18%", UP, ap(t, L6.start - 0.2, 0.1), note)
    caption(cv, ["標普 500，1950–2022（各家起算點略有不同），彙總值、非逐年。", "來源：Capital Group、BNY、LPL（二手轉述，未核原文）。"])


def sc_q4(cv, t, S):
    L = S["S08"]
    title(cv, "選舉年第四季", "第四季", 1.0, "標普 500・1950 年以來")
    cards = [(60, "平均漲幅", "+6.6%"), (490, "收高機率", "84%")]
    for k, (x, lab, num) in enumerate(cards):
        ap_ = ap(t, L.start - 0.22 + k * 0.12, 0.4)
        if ap_ <= 0:
            continue
        yy = 400 - (1 - ap_) * 24
        cv.card(f"卡{k}", x, yy, 410, 690, depth=16, edge=UP, grp=f"卡{k}")
        cv.text(f"卡標{k}", lab, x + 36, yy + 34, font(F_BOLD, 40), MUTED, ap_, grp=f"卡{k}", reg=False)
        f = font(F_BLACK, 112)
        cv.text(f"卡數{k}", num, x + 36, yy + 100, f, UP, ap_, grp=f"卡{k}", reg=False)
        cv.reg.inside(f"卡數{k}", (x + 36, yy + 100, x + 36 + f.getlength(num), yy + 210), (x, yy, x + 410, yy + 690), inset=16)
        if k == 0:
            ax, bot = x + 205, yy + 640
            gp = ease_out((t - (L.start + 0.1)) / 0.8)
            if gp > 0:
                hgt = 380 * gp
                cv.poly_fill([(ax - 52, bot), (ax - 52, bot - hgt * 0.55), (ax - 110, bot - hgt * 0.55), (ax, bot - hgt),
                              (ax + 110, bot - hgt * 0.55), (ax + 52, bot - hgt * 0.55), (ax + 52, bot)], UP)
        else:
            gx, gy = x + 38, yy + 250
            n_show = int(100 * clamp((t - (L.start + 0.2)) / 1.0))
            for j in range(100):
                r_, c_ = j // 10, j % 10
                if j < n_show:
                    cv.circle(gx + c_ * 34 + 17, gy + r_ * 41 + 18, 12, UP if j < 84 else (60, 72, 90))
    panel(cv, "期中選舉年第四季", "84% 收高", UP, ap(t, L.start - 0.2, 0.1), ["平均漲幅 +6.6%", "標普 500，1950 年以來"])
    caption(cv, ["標普 500，1950 年以來期中選舉年第四季；右圖每格＝1%。", "來源：Truist（Lerner）；他家口徑 4.6%～7.8% 不一。"])


def sc_dip(cv, t, S):
    L = S["S09"]
    title(cv, "選前常先跌", "先跌", 1.0, "期中選舉年：年內先回檔、選後回升")
    way = [(110, 470), (230, 410), (330, 490), (430, 720), (520, 880), (600, 720), (700, 600), (800, 500)]
    path = catmull(way, 12)
    xe = 560
    n = len(path)
    gr = ease_io((t - (L.start - 0.2)) / (L.at("平均最大") - L.start + 0.5))
    k = max(2, int(n * clamp(gr)))
    seg = path[:k]
    pk_k = min(range(n), key=lambda j: path[j][1])
    tr_k = max(range(n), key=lambda j: path[j][1])
    cv.line([(100, 1040), (870, 1040)], MUTED, 3)
    cv.line([(xe, 420), (xe, 900)], MUTED, 2, dash=[8, 8])
    up1 = seg[:min(k, pk_k + 1)]
    dn = seg[pk_k:min(k, tr_k + 1)] if k > pk_k else []
    up2 = seg[tr_k:] if k > tr_k else []
    if len(up1) > 1:
        cv.line(up1, UP, 8)
    if len(dn) > 1:
        cv.line(dn, DOWN, 8)
    if len(up2) > 1:
        cv.line(up2, UP, 8)
    dense = []
    for a, b in zip(seg[:-1], seg[1:]):
        dense += [a, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)]
    cv.reg.poly("示意折線", dense, "圖")
    if k > pk_k:
        cv.circle(path[pk_k][0], path[pk_k][1], 11, BG, stroke=TXT, lw=4)
    if k > tr_k:
        cv.circle(path[tr_k][0], path[tr_k][1], 11, DOWN, stroke=TXT, lw=4)
    if t >= L.at("平均最大") and k > tr_k:
        bx = 150
        y0_, y1_ = path[pk_k][1], path[tr_k][1]
        cv.line([(bx, y0_), (bx, y1_)], ORANGE, 6)
        cv.line([(bx, y0_), (path[pk_k][0] - 16, y0_)], MUTED, 2, dash=[8, 8])
        cv.line([(bx, y1_), (path[tr_k][0] - 16, y1_)], MUTED, 2, dash=[8, 8])
        cv.line([(bx - 12, y1_ - 16), (bx, y1_), (bx + 12, y1_ - 16)], ORANGE, 6)
        cv.text("回檔標", "平均最大回檔 −17.5%", 300, 960, font(F_BLACK, 46), ORANGE, grp="回檔標", safe=False)
    cv.text("示意標", "示意圖・非實際走勢", 620, 372, font(F_MED, 28), MUTED, grp="示意標", safe=False)
    for lab, xx in (("選前", 250), ("選舉日 11/03", xe), ("選後", 790)):
        cv.text(f"軸{lab}", lab, xx, 1058, font(F_MED, 28), MUTED, anchor="c", grp=f"軸{lab}", safe=False)
    panel(cv, "期中選舉年平均最大回檔", "−17.5%", DOWN, ap(t, L.start - 0.2, 0.1), ["示意圖，非逐年數字", "選舉日 2026-11-03"])
    caption(cv, ["示意圖，不含逐年數字；美國期中選舉日 2026-11-03。", "平均峰谷回檔約 17.5%（Carson，Motley Fool 轉述）。"])


def sc_limits(cv, t, S):
    L10, L11 = S["S10"], S["S11"]
    title(cv, "統計的限制", "限制", 1.0, "規律不等於保證")
    a1 = ap(t, L10.start - 0.22, 0.4)
    if a1 > 0:
        yy = 410 - (1 - a1) * 22
        cv.card("限制1", 60, yy, 840, 320, depth=16, edge=TEAL)
        cv.text("限制1標", "樣本僅 19 次", 100, yy + 30, font(F_BLACK, 72), TEAL, a1, grp="限制1", reg=False)
        cv.text("限制1字", "起算年份不同，平均也不同：", 100, yy + 142, font(F_MED, 36), TXT, a1, grp="限制1", reg=False)
        cv.text("限制1數", "15.4%～18.2%", 100, yy + 200, font(F_BLACK, 76), UP, a1, grp="限制1", reg=False)
    a2 = ap(t, L11.start - 0.22, 0.4)
    if a2 > 0:
        yy = 780 - (1 - a2) * 22
        cv.card("限制2", 60, yy, 840, 310, depth=16, edge=ORANGE)
        cv.text("限制2標", "2018 年：選後仍續跌", 100, yy + 30, font(F_BLACK, 62), ORANGE, a2, grp="限制2", reg=False)
        cv.text("限制2字", "11/06 選舉後，跌到 12 月底", 100, yy + 132, font(F_MED, 36), TXT, a2, grp="限制2", reg=False)
        f = font(F_BOLD, 38)
        s_ = "9/20 高點→12/24 低點 約 −19.4%"
        cv.text("限制2數", s_, 100, yy + 214, f, DOWN, a2, grp="限制2", reg=False)
        cv.reg.inside("限制2數", (100, yy + 214, 100 + f.getlength(s_), yy + 262), (60, yy, 900, yy + 310), inset=14)
    panel(cv, "統計的限制", "19 次樣本", TEAL if t < L11.start else ORANGE, ap(t, L10.start - 0.2, 0.1),
          ["起算年份影響結論", "2018 選後仍跌到 12 月底"])
    caption(cv, ["樣本期間見前圖圖註。2018 年：標普 500，", "Advisor Perspectives；各文低點日 12/24～12/26 略不同。"])


def sc_tw(cv, t, S):
    L = S["S12"]
    title(cv, "台股呢？", None, 1.0, "美國期中選舉後的台股表現")
    ap_ = ap(t, L.start - 0.22, 0.4)
    yy = 410 - (1 - ap_) * 22
    if ap_ > 0:
        cv.card("台股卡", 60, yy, 840, 330, depth=16, edge=ORANGE)
        f = font(F_BLACK, 104)
        cv.text("台股卡字", "查無可信統計", 100, yy + 90, f, ORANGE, ap_, grp="台股卡", reg=False)
        cv.text("台股卡標", "台股在美國期中選舉後的表現", 100, yy + 34, font(F_BOLD, 36), MUTED, ap_, grp="台股卡", reg=False)
        cv.reg.inside("台股卡字", (100, yy + 90, 100 + f.getlength("查無可信統計"), yy + 210), (60, yy, 900, yy + 330), inset=20)
    if t >= L.at("選後"):
        cv.text("六次標", "資料湖 2000 年起，僅有 6 次樣本：", 60, 830, font(F_BOLD, 38), TXT, grp="六次標")
    yrs = [2002, 2006, 2010, 2014, 2018, 2022]
    for i, yv in enumerate(yrs):
        if t < L.at("選後") + 0.2 + i * 0.13:
            continue
        x = 110 + i * 135
        cv.circle(x, 950, 30, BG, stroke=MUTED, lw=6)
        cv.reg.add(f"點{i}", (x - 32, 918, x + 32, 982), f"點{i}")
        cv.text(f"年{i}", str(yv), x, 1004, font(F_MED, 32), MUTED, anchor="c", grp=f"年{i}", safe=False)
    if t >= L.at("不硬湊") - 0.1:
        cv.text("不硬湊", "樣本太少，不硬湊", 60, 1054, font(F_BOLD, 40), ORANGE, grp="不硬湊")
    panel(cv, "台股在美國期中選舉後", "查無統計", ORANGE, ap(t, L.start - 0.2, 0.1), ["中英文各 3 組關鍵字", "未見可信統計，不硬湊"])
    caption(cv, ["查證：中英文各 3 組關鍵字，未見可信的台股統計。", "自家資料 2000 年起僅 6 次樣本，不足以作統計。"])


def sc_vars(cv, t, S):
    L13, L14, L15 = S["S13"], S["S14"], S["S15"]
    title(cv, "這次變數不同", "變數", 1.0, "左右對照：通膨與升息｜AI 融資")
    a1 = ap(t, L13.start - 0.22, 0.4)
    yy = 400 - (1 - a1) * 22
    if a1 > 0:
        cv.card("變數卡1", 60, yy, 410, 700, depth=16, edge=ORANGE)
        cv.text("變數1標", "① 通膨與升息", 90, yy + 28, font(F_BLACK, 40), TEAL, a1, grp="變數卡1", reg=False)
        cv.text("CPI標", "美國 9 月 CPI 年增", 90, yy + 100, font(F_MED, 32), MUTED, a1, grp="變數卡1", reg=False)
        if t >= L13.at("九月") - 0.1:
            cv.text("CPI數", "3.7%", 90, yy + 148, font(F_BLACK, 136), ORANGE, a1, grp="變數卡1", reg=False)
        if t >= L14.start:
            cv.text("CPI預期", "預期 3.6%", 90, yy + 320, font(F_BOLD, 38), MUTED, a1, grp="變數卡1", reg=False)
        if t >= L14.at("升息") - 0.1:
            cv.text("FOMC標", "10/28 FOMC", 90, yy + 440, font(F_BOLD, 34), TXT, a1, grp="變數卡1", reg=False)
            cv.text("FOMC標2", "升息機率約 5 成", 90, yy + 486, font(F_BOLD, 34), ORANGE, a1, grp="變數卡1", reg=False)
            bw = 330 * ease_out((t - L14.at("升息")) / 0.8)
            cv.rect(90, yy + 560, 330, 26, (44, 58, 80))
            cv.rect(90, yy + 560, bw * 0.5, 26, ORANGE)
            cv.rect(90 + 165 - 2, yy + 548, 5, 50, TXT)
    lit = t >= L15.start - 0.1
    a2 = ap(t, L13.start - 0.22, 0.4)
    yy2 = 400 - (1 - a2) * 22
    if a2 > 0:
        cv.card("變數卡2", 490, yy2, 410, 700, depth=16, edge=ORANGE if lit else (70, 86, 110), col=CARD if lit else (18, 26, 40))
        cv.text("變數2標", "② AI 融資成本", 520, yy2 + 28, font(F_BLACK, 40), TEAL if lit else (90, 106, 130), a2, grp="變數卡2", reg=False)
        if lit:
            cv.text("變數2a", "資料中心融資疑慮", 520, yy2 + 110, font(F_BOLD, 34), TXT, a2, grp="變數卡2", reg=False)
            cv.text("變數2b", "中國記憶體廠", 520, yy2 + 186, font(F_BOLD, 34), TXT, a2, grp="變數卡2", reg=False)
            cv.text("變數2c", "擴產傳聞", 520, yy2 + 232, font(F_BOLD, 34), TXT, a2, grp="變數卡2", reg=False)
            cv.text("費半標", "費半自 10/06", 520, yy2 + 400, font(F_MED, 32), MUTED, a2, grp="變數卡2", reg=False)
            cv.text("費半數", "−18.45%", 520, yy2 + 450, font(F_BLACK, 70), DOWN, a2, grp="變數卡2", reg=False)
            cv.reg.inside("費半數", (520, yy2 + 450, 520 + font(F_BLACK, 70).getlength("−18.45%"), yy2 + 540), (490, yy2, 900, yy2 + 700), inset=14)
        else:
            cv.text("變數2待", "待下一個變數", 520, yy2 + 110, font(F_MED, 32), (90, 106, 130), a2, grp="變數卡2", reg=False)
    if t < L15.start - 0.1:
        panel(cv, "壓力 ①", "CPI 3.7%", ORANGE, ap(t, L13.start - 0.2, 0.1), ["高於預期 3.6%", "10/28 FOMC 升息機率約 5 成"])
    else:
        panel(cv, "壓力 ②", "AI 融資", ORANGE, 1.0, ["資料中心融資疑慮", "中國記憶體廠擴產傳聞"])
    caption(cv, ["CPI 於 2026-10-14 公布；升息機率為 CME FedWatch，", "各來源約 47%～52%、每日變動。AI 融資為媒體報導（10/13）。"])


def sc_watch(cv, t, S):
    L16, L17, L18 = S["S16"], S["S17"], S["S18"]
    title(cv, "觀察三件事", "三件事", 1.0, "不預測，只看這三個訊號")
    items = [("聯準會與通膨", "10/28 FOMC・美國 CPI", L16.at("一，")),
             ("費半與 AI 融資消息", "費城半導體指數是否止穩", L17.start),
             ("開票後波動率", "VIX・選舉日 2026-11-03", L18.start)]
    active = 0
    for i, it in enumerate(items):
        if t >= it[2] - 0.1:
            active = i
    for i, (ti, su, t_in) in enumerate(items):
        a = ap(t, t_in - 0.1 if i else L16.start - 0.22, 0.4)
        if a <= 0:
            continue
        yy = 410 + i * 240 - (1 - a) * 10
        on = (i == active)
        cv.card(f"觀察{i}", 60, yy, 840, 200, depth=14, col=(30, 44, 64) if on else CARD, edge=ORANGE if on else (70, 86, 110), grp=f"觀察{i}")
        cv.circle(132, yy + 110, 42, ORANGE if on else (70, 86, 110))
        cv.text(f"觀察號{i}", str(i + 1), 132, yy + 82, font(F_BLACK, 54), (24, 14, 4) if on else TXT, a, anchor="c", grp=f"觀察{i}", reg=False)
        cv.text(f"觀察標{i}", ti, 200, yy + 40, font(F_BLACK, 54), TXT if on else MUTED, a, grp=f"觀察{i}", reg=False)
        cv.text(f"觀察副{i}", su, 200, yy + 128, font(F_MED, 36), TEAL if on else MUTED, a, grp=f"觀察{i}", reg=False)
        cv.reg.inside(f"觀察標{i}", (200, yy + 40, 200 + font(F_BLACK, 54).getlength(ti), yy + 96), (60, yy, 900, yy + 220), inset=14)
    ti, su, _ = items[active]
    panel(cv, f"觀察 {active + 1}／3", ["聯準會", "費半", "波動率"][active], ORANGE, ap(t, L16.start - 0.2, 0.1), [su])
    caption(cv, ["FOMC＝美國聯準會利率會議；VIX＝芝加哥選擇權交易所", "波動率指數。以上為觀察面向，不構成進出場建議。"])


def sc_concl(cv, t, S):
    L = S["S19"]
    title(cv, "歷史偏強，不保證", "不保證", 1.0, "規律與例外並陳")
    a1 = ap(t, L.start - 0.22, 0.4)
    if a1 > 0:
        cv.rect(0, 410, W, 300, (16, 52, 52))
        cv.reg.add("帶1", (0, 410, W, 710), "帶1")
        cv.text("結論1標", "歷史偏強", 60, 440, font(F_BLACK, 86), TEAL, a1, grp="帶1", reg=False)
        cv.text("結論1字", "標普 500 選後 12 個月，樣本內皆為正報酬", 60, 580, font(F_MED, 36), TXT, a1, grp="帶1", reg=False)
        cv.text("結論1字2", "各家平均約 15%～18%（19 次）", 60, 634, font(F_MED, 36), TXT, a1, grp="帶1", reg=False)
    a2 = ap(t, L.at("但不保證") - 0.1, 0.4)
    if a2 > 0:
        cv.rect(0, 740, W, 380, (60, 38, 14))
        cv.reg.add("帶2", (0, 740, W, 1120), "帶2")
        cv.text("結論2標", "但不保證這次一樣", 60, 764, font(F_BLACK, 78), ORANGE, a2, grp="帶2", reg=False)
        for j, s in enumerate(["通膨 3.7%，升息機率約 5 成", "AI 融資與費半仍待止穩", "選後走勢仍有不確定性"]):
            if t >= L.at("這次") + j * 0.18:
                cv.text(f"結論2條{j}", s, 60, 880 + j * 74, font(F_MED, 44), TXT, 1.0, grp="帶2", reg=False)
    panel(cv, "結論", "偏強≠保證", ORANGE, ap(t, L.start - 0.2, 0.1), ["歷史統計不代表未來", "請自行判斷"])
    caption(cv, ["彙總統計不代表未來；各家樣本期間與口徑不同，", "詳見前面各圖圖註。"])


def sc_end(cv, t, S):
    L20, L21, L22, L23 = S["S20"], S["S21"], S["S22"], S["S23"]
    title(cv, "想看資料整理", "資料整理", 1.0, "每天盤後自動整理公開資料")
    a = ap(t, L20.start - 0.22, 0.4)
    if a > 0:
        yy = 400 - (1 - a) * 20
        cv.card("搜尋框", 60, yy, 840, 190, depth=16, col=(240, 244, 248))
        cv.circle(144, yy + 92, 34, None, stroke=(40, 52, 70), lw=10)
        cv.line([(168, yy + 118), (202, yy + 152)], (40, 52, 70), 11)
        f = font(F_BLACK, 104)
        cv.text("搜尋字", "哩股哩股", 250, yy + 40, f, (22, 30, 44), a, grp="搜尋框", reg=False)
        cv.reg.inside("搜尋字", (250, yy + 40, 250 + f.getlength("哩股哩股"), yy + 150), (60, yy, 900, yy + 190), inset=14)
    feats = [("資金流向", "錢往哪個族群跑"), ("產業地圖", "產業鏈與族群"), ("題材熱度", "熱門題材排行"), ("季節性", "歷史季節統計")]
    for j, (nm, ds) in enumerate(feats):
        cp_ = ap(t, L20.start + 0.35 + j * 0.2, 0.4)
        if cp_ <= 0:
            continue
        x = 60 + (j % 2) * 430
        y = 640 + (j // 2) * 244 - (1 - cp_) * 10
        cv.card(f"功能{j}", x, y, 410, 200, depth=14, edge=TEAL, grp=f"功能{j}")
        cv.text(f"功能名{j}", nm, x + 36, y + 36, font(F_BLACK, 52), TEAL, cp_, grp=f"功能{j}", reg=False)
        cv.text(f"功能述{j}", ds, x + 36, y + 124, font(F_MED, 34), TXT, cp_, grp=f"功能{j}", reg=False)
    b = ap(t, L21.start - 0.2, 0.4)
    px, py, pw, ph = PANEL
    cv.card("免責卡", px, py, pw, ph, depth=14, edge=ORANGE)
    cv.text("免責標", "免責聲明", px + 34, py + 26, font(F_BOLD, 34), ORANGE, 1.0, grp="免責卡", reg=False)
    f = font(F_BOLD, 29)
    for j, (lid, s) in enumerate([("S21", "本內容為公開資料整理，"), ("S22", "不構成任何投資建議；"), ("S23", "投資有風險，請自行判斷。")]):
        if t >= S[lid].start - 0.05:
            cv.text(f"免責{j}", s, px + 34, py + 96 + j * 72, f, TXT, 1.0, grp="免責卡", reg=False)
            cv.reg.inside(f"免責{j}", (px + 34, py + 96 + j * 72, px + 34 + f.getlength(s), py + 96 + j * 72 + 40), (px, py, px + pw, py + ph), inset=14)
    caption(cv, ["站內頁面：資金流向、產業地圖、題材熱度、季節性。", "資料為公開資料整理，更新至 2026-10-22／10-23 收盤。"])


SCENE_FN = {"A1": lambda cv, t, S: sc_taiex(cv, t, S, 1), "A2": sc_split, "A3": lambda cv, t, S: sc_taiex(cv, t, S, 3),
            "B": sc_drops, "C": sc_world, "D": sc_stats, "E": sc_q4, "F": sc_dip, "L": sc_limits, "G": sc_tw,
            "H": sc_vars, "I": sc_watch, "J": sc_concl, "K": sc_end}


# ───────────────────────── 單格 ─────────────────────────
def render(t):
    cv = Canvas()
    cur_sc = None
    for sc in SCENES:
        if sc[2] <= t < sc[3]:
            cur_sc = sc
    if cur_sc is None:
        cur_sc = SCENES[-1]
    sid, ids, s0, s1 = cur_sc
    S = LINES
    SCENE_FN[sid](cv, t, S)
    subtitle(cv, t)
    footer(cv)
    cv.finish(draw_bibi(t))
    return cv


# ───────────────────────── 封面 ─────────────────────────
def make_cover(path):
    cv = Canvas()
    view = (0, NPT - 1, 45000, 51500)
    # 封面用更大的圖：把繪圖區暫時放大
    global PX0, PX1, PY0, PY1
    save = (PX0, PX1, PY0, PY1)
    PX0, PX1, PY0, PY1 = 190, 800, 900, 1300
    mx, my, pts = taiex_chart(cv, view, NPT - 1)
    pk = (mx(PEAK), my(CLOSE[PEAK]))
    en = (mx(NPT - 1), my(CLOSE[-1]))
    cv.circle(pk[0], pk[1], 13, BG, stroke=TXT, lw=5)
    cv.circle(en[0], en[1], 13, DOWN, stroke=TXT, lw=4)
    cv.reg.add("高點點", (pk[0] - 15, pk[1] - 15, pk[0] + 15, pk[1] + 15), "圖")
    cv.reg.add("終點點", (en[0] - 15, en[1] - 15, en[0] + 15, en[1] + 15), "圖")
    cv.text("封面高點", "10/06 創高 49,822.55", pk[0], pk[1] - 60, font(F_BOLD, 32), ORANGE, anchor="c", grp="封面高點", safe=False)
    cv.text("封面終點", "−7.59%", 880, en[1] + 24, font(F_BLACK, 44), DOWN, anchor="r", grp="封面終點", safe=False)
    PX0, PX1, PY0, PY1 = save
    items = [("台股自高點", font(F_BLACK, 112), TXT, 190), ("回落 7.6%", font(F_BLACK, 168), DOWN, 330),
             ("期中選舉行情", font(F_BLACK, 112), TXT, 560), ("還在嗎？", font(F_BLACK, 168), ORANGE, 700)]
    for k, (s, f, col, y) in enumerate(items):
        cv.text(f"封面字{k}", s, 60, y, f, col)
    cv.text("封面副標", "歷史統計怎麼說・這次的變數", 60, 1000 - 40 - 0, font(F_BOLD, 40), TEAL, grp="封面副標") if False else None
    cv.text("封面角註", "資料至 2026-10-22・非投資建議", 60, 1396, font(F_MED, 28), DIM, grp="封面角註")
    cv.finish(draw_bibi(0, name="face_think_v2", bt=1.0, cx=720, foot=1880))
    cv.final.convert("RGB").save(path)
    return cv.reg


# ───────────────────────── SRT ─────────────────────────
def write_srt(path):
    out = []
    for i, (disp, hl, a, b, lid, k, _sh) in enumerate(SUBS, 1):
        out += [str(i), f"{ts(a)} --> {ts(b)}", disp.rstrip("，。；") if not disp.endswith(("？", "！")) else disp, ""]
    Path(path).write_text("\n".join(out), encoding="utf-8")


def write_sync_report(path):
    """字幕同步：每張字幕的起點是怎麼定的。
    句首＝音檔實際起音（能量 > -38 dB）；標點後＝偵測到的句內停頓結束點；句中無標點＝估計值吸到 ±0.12 秒內最近的音節縫隙（記下位移）。
    MeloTTS 沒有逐字時間，無法用強制對齊量真實誤差；這裡列的是各種定法的不確定度上限。"""
    rows, worst = [], 0.0
    for (disp, hl, a, b, lid, k, shift) in SUBS:
        ln = LINES[lid]
        if k == 0:
            kind, unc = "句首（起音）", 0.01
        elif any(pm[0] == k - 1 for pm in ln.pause_marks):
            kind, unc = "標點後（偵測停頓結束）", 0.02
        else:
            kind, unc = f"句中吸附（位移 {shift:+.3f}s）", 0.12
        worst = max(worst, unc)
        rows.append(f"| {a:6.2f} | {b:6.2f} | {lid} | {disp} | {kind} | ≤{unc:.2f} |")
    n_pause = sum(1 for r in rows if "標點後" in r)
    n_snap = sum(1 for r in rows if "吸附" in r)
    out = ["# 字幕同步報告", "", f"- 字幕 {len(SUBS)} 張；句首 {len(SUBS) - n_pause - n_snap}、標點後 {n_pause}、句中吸附 {n_snap}。",
           f"- 同步誤差上限（各定法的不確定度最大值）：**{worst:.2f} 秒**（標準：≤0.15 秒）。",
           "- 說明：MeloTTS 沒有逐字時間，無法用強制對齊量真實誤差；句首與標點後兩類是以音檔能量偵測到的實際起音／停頓結束點，句中吸附類以 ±0.12 秒視窗內的能量谷底為準。", "",
           "| 起 | 訖 | 句 | 字幕 | 起點怎麼定 | 不確定度（秒） |", "|---|---|---|---|---|---|"] + rows
    Path(path).write_text("\n".join(out) + "\n", encoding="utf-8")


# ───────────────────────── 主程式 ─────────────────────────
def _work(i):
    t = i / FPS
    cv = render(t)
    ovl = cv.reg.overlaps()
    occ, blur, det = cv.checks()
    buf = cv.final.convert("RGB").tobytes()
    return i, buf, ovl, list(cv.reg.issues), occ, blur, det


def main():
    ap_ = argparse.ArgumentParser()
    ap_.add_argument("--out", default=str(SCR / "silent.mp4"))
    ap_.add_argument("--frames", default="")
    ap_.add_argument("--sheet", default="")
    ap_.add_argument("--cover", action="store_true")
    ap_.add_argument("--workers", type=int, default=4)
    a = ap_.parse_args()
    SCR.mkdir(parents=True, exist_ok=True)
    build_timeline()
    print(f"片長 {TOTAL:.2f} 秒；結尾 {END_T:.2f}", file=sys.stderr)
    write_sync_report(HERE / "sync_report.md")
    for sid, ids, s0, s1 in SCENES:
        print(f"  {sid} {s0:6.2f}–{s1:6.2f} {ids}", file=sys.stderr)
    if a.cover:
        reg = make_cover(HERE / "midterm_rally_cover.png")
        print("封面 重疊", reg.overlaps(), "出框", reg.issues)
        return
    if a.frames:
        for s in a.frames.split(","):
            cv = render(float(s))
            p = SCR / f"f_{float(s):06.2f}.png"
            cv.final.convert("RGB").save(p)
            occ, blur, det = cv.checks()
            print(p, bibi_at(float(s))[0], "重疊", cv.reg.overlaps(), "出框", cv.reg.issues, "遮擋", occ, "模糊", blur, det[:4])
        return
    n = int(round(TOTAL * FPS))
    tmp = Path(a.out)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "17", "-preset", "medium",
                           "-pix_fmt", "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    rows, issues, occs, blurs = [], [], [], []
    samp = SCR / "samples"
    samp.mkdir(exist_ok=True)
    for old in samp.glob("*.png"):
        old.unlink()
    with mp.get_context("fork").Pool(a.workers) as pool:
        for i, buf, ovl, iss, occ, blur, det in pool.imap(_work, range(n), chunksize=4):
            t = i / FPS
            ff.stdin.write(buf)
            for (x, y, area) in ovl:
                rows.append(f"| {t:6.2f} | {x} | {y} | {area} |")
            for s in iss:
                issues.append(f"| {t:6.2f} | {s} |")
            if occ:
                occs.append(f"| {t:6.2f} | " + "；".join(d for d in det if d.startswith("遮擋"))[:200] + " |")
            if blur:
                blurs.append(f"| {t:6.2f} | " + "；".join(d for d in det if d.startswith("模糊"))[:200] + " |")
            if i % 15 == 0:
                Image.frombytes("RGB", (W, H), buf).save(samp / f"s_{t:05.1f}.png")
            if i % 300 == 0:
                print(f"{t:5.1f}s", file=sys.stderr, flush=True)
    ff.stdin.close()
    ff.wait()
    rep = ["# 檢查報告（render_midterm.py 每一幀自動產生）", "",
           f"- 片長 {TOTAL:.2f} 秒；總幀數 {n}（30fps）。",
           f"- 重疊檢查：程式 {n} 幀 {len(rows)} 筆（每個外框外擴 {PAD}px 後兩兩比對；折線取樣點不得落在其他元素外框內）",
           f"- 出框／安全區／字級：{len(issues)} 筆",
           f"- 遮擋檢查：程式 {n} 幀 {len(occs)} 筆（每個文字的字形像素在最終畫面上必須仍為原色）",
           f"- 模糊檢查：程式 {n} 幀 {len(blurs)} 筆（文字框內與「文字遮罩重算的預期畫面」不符的像素比例 > {mc.BLUR_MAX} 算模糊／疊影；全片未使用任何模糊濾鏡）", ""]
    for title_, rr, head in (("重疊明細", rows, "| 秒 | 元素 A | 元素 B | 相交面積 |\n|---|---|---|---|"),
                             ("出框明細", issues, "| 秒 | 問題 |\n|---|---|"),
                             ("遮擋明細", occs, "| 秒 | 明細 |\n|---|---|"),
                             ("模糊明細", blurs, "| 秒 | 明細 |\n|---|---|")):
        if rr:
            rep += [f"## {title_}", head] + rr[:300] + [""]
    (HERE / "overlap_report.md").write_text("\n".join(rep) + "\n", encoding="utf-8")
    write_srt(HERE / "midterm_rally_9x16.srt")
    (SCR / "timeline.json").write_text(json.dumps({
        "total": TOTAL, "end_t": END_T, "scenes": [(s[0], s[1], s[2], s[3]) for s in SCENES],
        "lines": {k: [v.start, v.end, v.on] for k, v in LINES.items()},
        "subs": [(s[0], s[2], s[3], s[4]) for s in SUBS]}, ensure_ascii=False, indent=1))
    print(f"重疊 {len(rows)} 出框 {len(issues)} 遮擋 {len(occs)} 模糊 {len(blurs)} 幀 {n}")


if __name__ == "__main__":
    main()
