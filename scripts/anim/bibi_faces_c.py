"""動畫設計單位：吉祥物「比比」C 批「表情包＋說話」（3 種說話、10 種表情、自我介紹），512×512、透明。

為什麼有這支
------------
Andy 2026-10-10：「幫我在影片中新增多點 GIF 圖，表情越豐富越好，情境越多越好，可以多點物件，
動作可以跟影片有更多互動，讓觀眾有是比比在介紹的感覺」。A 批在 `bibi_actions.py`、B 批在 `bibi_scenes_b.py`；
這支只 import 它們的函式，**不改那幾支**（另一位設計師同時在做 D 批）。

做法（docs/anim/prompt_kit/01_總控Prompt.md：raster_first）
----------------------------------------------------------
1. 身體一律是原圖 `site/brand/src/support_anim_1009.gif` 第 0 張的像素，沿用 `pose_tween.warp_body` 網格變形
   （擠壓／拉長／歪頭／頭頂毛慣性）。角色本體不重畫。
2. 五官改在「原圖座標」上做，再跟身體一起變形 → 五官跟著臉走，不會像貼片浮在上面：
   - 先把原本的眼睛／嘴巴「用周圍毛色補掉」：只挑非毛色、非腮紅的像素當遮罩，往外擴 3px 吃掉白邊，
     由遮罩邊緣往內一圈一圈取鄰近已知像素平均（洋蔥式擴散補色），腮紅不會被蓋掉。
   - 再用 SVG 三次 Bézier＋手繪筆刷畫新眼睛／嘴巴／眉毛／加深腮紅（4 倍繪製再 LANCZOS），
     筆刷粗細＝原圖描邊，嘴巴「原樣」那格直接沿用原圖像素。
3. 臉以外的物件（愛心、星星、汗滴、Zzz、點點點、鼻涕泡、名牌、炸毛）在場景座標畫，錨點用原圖座標正向映射，
   身體動它們跟著動。炸毛＝沿身體輪廓往外長的尖毛，畫在身體後面。
4. Andy 退件教訓：不從身體伸出長手臂；需要手的地方只放小肉掌（揮手、托下巴、抓頭）。
5. 場景座標跟 A／B 批相同：身體縮 0.75、中心 x=248、腳底 y=482。

用法
----
    BIBI_SIGN_FONT=<jf-openhuninn-2.1.ttf> python scripts/anim/bibi_faces_c.py \
        --out <scratchpad>/bibi --repo-out docs/anim [--only talk_happy,face_love]
輸出：<out>/<名>/frames/frame_01.png…、<out>/<名>/anim.gif、<repo-out>/bibi_<名>/sheet_12.png、anim.webp、
storyboard.md；<out>/index_c.json。
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import bibi_actions as BA  # noqa: E402  （import 時已把 pose_tween.SS 設成 4）
import pose_tween  # noqa: E402

from bibi_actions import (INK, FUR, SPARK, SIZE, SS, OUT_W, f, P, add, dirv, bez, brush,  # noqa: E402
                          sparkle, motion_lines, arcs, paw_svg, base_geom, fwd, raster, text_layer, sheet12,
                          exmark, ease)
from bibi_scenes_b import smooth_closed, rrect_pts, jitter, shape  # noqa: E402

# ---- 原圖第 0 張量到的五官（原圖座標，512 原圖）
EYE_L, EYE_R = (192.5, 262.5), (310.0, 260.5)
CHEEK_L, CHEEK_R = (151, 289), (350, 284)
MOUTH_C = (250, 289)
SW = 7.6                     # 原圖描邊粗細（原圖座標）

MOUTH_IN = "#8C3426"
TONGUE = "#F08C70"
TONGUE_DK = "#D9674C"
HEART, HEART_DK = "#F45D7A", "#D63E5E"
STAR, STAR_DK = "#FFD23F", "#F2A81D"
SWEAT, SWEAT_LT = "#A8DCF7", "#E6F6FF"
BLUSH2 = "#F7876F"
PLATE_PINK = "#F7B4C2"


# ================================================================== 原圖去掉五官（只做一次）
_CLEAN = {}


def _fill_onion(arr, mask, iters=400):
    """洋蔥式補色：遮罩邊緣往內，每一圈取 8 鄰域已知像素平均；最後在遮罩內輕微平滑。"""
    arr = arr.astype(np.float32).copy()
    known = ~mask
    H, W = mask.shape
    for _ in range(iters):
        if known.all():
            break
        acc = np.zeros_like(arr[..., :3]); cnt = np.zeros((H, W), np.float32)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                k = np.roll(np.roll(known, dy, 0), dx, 1)
                v = np.roll(np.roll(arr[..., :3], dy, 0), dx, 1)
                acc += v * k[..., None]; cnt += k
        grow = (~known) & (cnt >= 2)
        if not grow.any():
            grow = (~known) & (cnt >= 1)
        arr[grow, :3] = acc[grow] / cnt[grow][:, None]
        known = known | grow
    for _ in range(6):   # 遮罩內平滑一點，不留擴散的條紋
        sm = sum(np.roll(np.roll(arr[..., :3], dy, 0), dx, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1)) / 9
        arr[mask, :3] = sm[mask]
    return arr


def _dilate(m, r):
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r:
                out |= np.roll(np.roll(m, dy, 0), dx, 1)
    return out


def clean_body(poses, eyes=True, mouth=True):
    key = (eyes, mouth)
    if key in _CLEAN:
        return _CLEAN[key]
    body = poses[0]["body"]
    arr = np.asarray(body).astype(np.float32)
    rgb = arr[..., :3]
    H, W = rgb.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    # 臉部毛色＝眼睛與嘴巴之間那塊乾淨毛的中位數；跟它差太多（含描邊外那圈白邊）就算五官要補
    face = ((xx - 250) ** 2 + (yy - 225) ** 2 < 18 ** 2)
    ref = np.median(rgb[face], 0)
    fur = np.abs(rgb - ref).max(2) < 9
    pink = (rgb[..., 0] > 215) & (rgb[..., 1] > 130) & (rgb[..., 1] < 212) & (rgb[..., 0] - rgb[..., 2] > 55)
    near = np.zeros((H, W), bool)
    for c in (CHEEK_L, CHEEK_R):
        near |= (xx - c[0]) ** 2 + (yy - c[1]) ** 2 <= 31 ** 2
    pink &= near                                                        # 只有腮紅圓裡面的粉色才保留
    region = np.zeros((H, W), bool)
    if eyes:
        for e in (EYE_L, EYE_R):
            region |= (xx - e[0]) ** 2 + (yy - e[1]) ** 2 <= 21 ** 2
    feat_eye = region & ~fur & ~pink
    mreg = np.zeros((H, W), bool)
    if mouth:
        mreg = ((xx - 250) / 41.0) ** 2 + ((yy - 291) / 36.0) ** 2 <= 1
    feat_m = mreg & ~fur
    mask = _dilate(feat_eye, 3) & region & ~pink | _dilate(feat_m, 3) & mreg
    out = _fill_onion(arr, mask)
    out[..., 3] = arr[..., 3]
    im = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")
    _CLEAN[key] = im
    return im


# ================================================================== 五官（原圖座標）
def heart_d(c, s, deg=0.0):
    cx, cy = c
    pts = [(0, 0.9), (-0.2, 0.7), (-1.0, 0.25), (-1.0, -0.3), (-1.0, -0.85), (-0.35, -1.0), (0, -0.5),
           (0.35, -1.0), (1.0, -0.85), (1.0, -0.3), (1.0, 0.25), (0.2, 0.7), (0, 0.9)]
    r = math.radians(deg); co, si = math.cos(r), math.sin(r)
    T = [(cx + (x * co - y * si) * s, cy + (x * si + y * co) * s) for x, y in pts]
    return (f"M {P(T[0])} C {P(T[1])} {P(T[2])} {P(T[3])} C {P(T[4])} {P(T[5])} {P(T[6])} "
            f"C {P(T[7])} {P(T[8])} {P(T[9])} C {P(T[10])} {P(T[11])} {P(T[12])} Z")


def heart_svg(c, s, deg=0.0, lw=None, op=1.0):
    d = heart_d(c, s, deg)
    lw = lw if lw is not None else max(2.6, s * 0.32)
    hl = (c[0] - s * 0.45, c[1] - s * 0.35)
    body = (f'<path d="{d}" fill="{HEART}"/>'
            f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{f(lw)}" stroke-linejoin="round"/>'
            f'<ellipse cx="{f(hl[0])}" cy="{f(hl[1])}" rx="{f(s*0.2)}" ry="{f(s*0.13)}" fill="#FFFFFF" opacity="0.85" '
            f'transform="rotate(-35,{f(hl[0])},{f(hl[1])})"/>')
    return body if op >= 1 else f'<g opacity="{op:.2f}">{body}</g>'


def star_d(c, R, deg=0.0, inner=0.5):
    pts = []
    for i in range(10):
        a = math.radians(deg - 90 + i * 36)
        r = R if i % 2 == 0 else R * inner
        pts.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a)))
    # 每個尖角用二次 Bézier 稍微收圓，不是生硬多邊形
    d = f"M {P(pts[0])} "
    for i in range(1, 11):
        p = pts[i % 10]
        q = pts[i - 1]
        m = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
        d += f"Q {P(m)} {P(p)} " if i % 2 == 0 else f"L {P(p)} "
    return d + "Z"


def star_svg(c, R, deg=0.0, lw=None, op=1.0):
    d = star_d(c, R, deg)
    lw = lw if lw is not None else max(2.4, R * 0.2)
    s = (f'<path d="{d}" fill="{STAR}"/>'
         f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{f(lw)}" stroke-linejoin="round"/>'
         f'<circle cx="{f(c[0]-R*0.18)}" cy="{f(c[1]-R*0.2)}" r="{f(R*0.14)}" fill="#FFFFFF" opacity="0.9"/>')
    return s if op >= 1 else f'<g opacity="{op:.2f}">{s}</g>'


def eye_svg(e, kind, look=(0.0, 0.0), s=1.0, side=1, deg=0.0):
    """kind：dot／shine（亮晶晶）／happy（∩）／blink（‿）／half（半閉）／line（睡）／gt（> 或 <）／
    heart／star／wide（白眼圈小瞳孔）。e＝原圖座標眼睛中心，side＝-1 左眼／+1 右眼。"""
    x, y = e[0] + look[0], e[1] + look[1]
    if kind == "dot":
        return f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="{f(12.5*s)}" ry="{f(13.5*s)}" fill="{INK}"/>'
    if kind == "shine":
        return (f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="{f(13.5*s)}" ry="{f(14.5*s)}" fill="{INK}"/>'
                f'<circle cx="{f(x+4.2*s)}" cy="{f(y-5.2*s)}" r="{f(4.8*s)}" fill="#FFFFFF"/>'
                f'<circle cx="{f(x-4.6*s)}" cy="{f(y+5.0*s)}" r="{f(2.3*s)}" fill="#FFFFFF"/>')
    if kind == "happy":
        return brush(bez((x - 13, y + 5), (x - 7, y - 9), (x + 7, y - 9), (x + 13, y + 5), 14), SW, SW)
    if kind == "blink":
        return brush(bez((x - 13, y - 1), (x - 6, y + 7), (x + 6, y + 7), (x + 13, y - 1), 14), SW, SW)
    if kind == "line":
        return brush(bez((x - 13, y + 3), (x - 5, y + 6.5), (x + 5, y + 6.5), (x + 13, y + 3), 12), SW * 0.9, SW * 0.9)
    if kind == "half":
        cid = f"hc{int(x*10)}{int(y*10)}{int(s*100)}"
        return (f'<clipPath id="{cid}"><rect x="{f(x-20)}" y="{f(y-1)}" width="40" height="30"/></clipPath>'
                f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="{f(12.5*s)}" ry="{f(13.5*s)}" fill="{INK}" clip-path="url(#{cid})"/>'
                + brush(bez((x - 15, y + 1), (x - 6, y - 2.5), (x + 6, y - 2.5), (x + 15, y + 1), 12), SW * 0.95, SW * 0.95))
    if kind == "gt":   # 左眼 >、右眼 <（瞇眼大笑）
        k = -side
        pts = [(x - 11 * k, y - 11), (x + 9 * k, y), (x - 11 * k, y + 11)]
        return brush(bez(pts[0], (x - 2 * k, y - 6), (x + 6 * k, y - 2), pts[1], 8) +
                     bez(pts[1], (x + 6 * k, y + 2), (x - 2 * k, y + 6), pts[2], 8)[1:], SW, SW)
    if kind == "heart":
        return heart_svg((x, y + 1), 19.0 * s, deg, lw=5.0)
    if kind == "star":
        return star_svg((x, y), 19 * s, deg, lw=4.4)
    if kind == "wide":
        return (f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="{f(16*s)}" ry="{f(17.5*s)}" fill="#FFFFFF" stroke="{INK}" '
                f'stroke-width="{f(SW*0.8)}"/>'
                f'<circle cx="{f(x+look[0]*0.0)}" cy="{f(y)}" r="{f(5.2*s)}" fill="{INK}"/>')
    raise ValueError(kind)


L_DIP, R_DIP, PEAK = (236, 280), (264, 280), (250, 270)
W_TOP = (bez((221, 268), (222, 276), (229, 280), L_DIP, 10) + bez(L_DIP, (243, 280), (249, 276), PEAK, 10)[1:] +
         bez(PEAK, (251, 276), (257, 280), R_DIP, 10)[1:] + bez(R_DIP, (271, 280), (278, 276), (279, 268), 10)[1:])


def mouth_svg(kind, k=1.0):
    """嘴巴（原圖座標）。w＝閉嘴 ω；open_s／open_m／open_l＝ω 下面張開（舌頭）；laugh＝大 D 嘴；
    o／O＝圓嘴；wavy＝尷尬波浪；tongue＝吐舌；tiny＝睡覺小 o。"""
    w = brush(W_TOP, SW, SW)
    if kind == "w":
        return w
    if kind in ("open_s", "open_m", "open_l"):
        dep = {"open_s": 16, "open_m": 34, "open_l": 46}[kind] * k
        bx = {"open_s": 2, "open_m": 5, "open_l": 10}[kind]
        y0 = L_DIP[1]
        u = (f"M {P(L_DIP)} C {P((L_DIP[0]-bx, y0+dep*1.33))} {P((R_DIP[0]+bx, y0+dep*1.33))} {P(R_DIP)}")
        d = u + f" C 257,280 251,276 {P(PEAK)} C 249,276 243,280 {P(L_DIP)} Z"
        cid = f"m{kind}{int(dep*10)}"
        tongue = (f'<clipPath id="{cid}"><path d="{d}"/></clipPath>'
                  f'<ellipse cx="250" cy="{f(y0+dep*0.92)}" rx="{f(10+bx)}" ry="{f(dep*0.42)}" fill="{TONGUE}" '
                  f'clip-path="url(#{cid})"/>')
        return (f'<path d="{d}" fill="{MOUTH_IN}"/>' + tongue +
                f'<path d="{u}" fill="none" stroke="{INK}" stroke-width="{f(SW)}" stroke-linecap="round"/>' + w)
    if kind == "laugh":
        d = ("M 219,268 C 232,276 268,276 281,268 C 286,330 214,330 219,268 Z")
        return (f'<path d="{d}" fill="{MOUTH_IN}"/>'
                f'<clipPath id="ml"><path d="{d}"/></clipPath>'
                f'<ellipse cx="250" cy="312" rx="21" ry="12" fill="{TONGUE}" clip-path="url(#ml)"/>'
                f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{f(SW)}" stroke-linejoin="round"/>')
    if kind in ("o", "O", "tiny"):
        rx, ry, cy = {"o": (8, 9.5, 286), "O": (12.5, 16, 292), "tiny": (5.5, 4.5, 284)}[kind]
        return (f'<ellipse cx="250" cy="{cy}" rx="{rx}" ry="{ry}" fill="{MOUTH_IN}" stroke="{INK}" '
                f'stroke-width="{f(SW*0.85)}"/>')
    if kind == "wavy":
        pts = [(226 + i * 2, 284 + 4.5 * math.sin(i * 2 * math.pi / 8)) for i in range(25)]
        return brush(pts, SW * 0.9, SW * 0.9)
    if kind == "tongue":
        d = "M 240,279 C 236,310 264,312 260,279 Z"
        return (f'<path d="{d}" fill="{TONGUE}"/>'
                f'<path d="M 250,286 L 250,298" stroke="{TONGUE_DK}" stroke-width="2.6" stroke-linecap="round"/>'
                f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{f(SW*0.85)}" stroke-linejoin="round"/>' + w)
    raise ValueError(kind)


def brows_svg(kind, k=1.0):
    """眉毛（原圖座標）：raise＝左眉挑高右眉平（認真講）；up＝兩眉上揚（興奮）；worry＝八字眉（尷尬）。"""
    out = ""
    for e, side in ((EYE_L, -1), (EYE_R, 1)):
        x, y = e[0], e[1] - 30
        if kind == "raise":
            lift = (8 if side < 0 else 0) * k
            p0, p3 = (x - 12, y + 3 - lift * 0.4), (x + 12, y + 3 - lift * 0.4)
            m = -lift - 5
            out += brush(bez(p0, (x - 5, y + m), (x + 5, y + m), p3, 10), 6.0, 5.0)
        elif kind == "up":
            out += brush(bez((x - 11, y), (x - 4, y - 8 * k), (x + 4, y - 8 * k), (x + 11, y), 10), 5.6, 5.0)
        elif kind == "worry":   # 內側高、外側低
            a = (x - side * 12, y + 1); b = (x + side * 10, y - 6 * k)
            out += brush(bez(b, (x + side * 3, y - 6 * k), (x - side * 4, y - 2), a, 10), 5.6, 5.0)
    return out


def blush_svg(kind):
    """加深腮紅；lines＝腮紅上三道斜線（害羞／尷尬）。"""
    out = ""
    for c in (CHEEK_L, CHEEK_R):
        out += f'<ellipse cx="{c[0]}" cy="{c[1]+2}" rx="29" ry="22" fill="{BLUSH2}" opacity="0.45"/>'
        if kind == "lines":
            for j in (-1, 0, 1):
                x = c[0] + j * 11
                out += brush([(x + 4, c[1] - 8), (x - 4, c[1] + 8)], 3.6, 3.0)
    return out


_POSE = {}


def face_pose(poses, eyes="orig", mouth="orig", look=(0.0, 0.0), es=(1.0, 1.0), brows=None, blush=None,
              edeg=(0.0, 0.0), mk=1.0, extra=""):
    """回傳「換了五官」的原圖第 0 張 pose（給 warp_body 用）。eyes 可以是字串或 (左, 右)。"""
    if isinstance(eyes, str):
        eyes = (eyes, eyes)
    key = (eyes, mouth, tuple(round(v, 2) for v in look), tuple(round(v, 3) for v in es), brows, blush,
           tuple(round(v, 1) for v in edeg), round(mk, 3), extra)
    if key in _POSE:
        return _POSE[key]
    if eyes == ("orig", "orig") and mouth == "orig" and not (brows or blush or extra):
        _POSE[key] = poses[0]
        return poses[0]
    body = clean_body(poses, eyes=eyes != ("orig", "orig"), mouth=mouth != "orig")
    svg = ""
    if blush:
        svg += blush_svg(blush)
    if brows:
        svg += brows_svg(brows)
    if eyes != ("orig", "orig"):
        for e, kd, side, s, dg in ((EYE_L, eyes[0], -1, es[0], edeg[0]), (EYE_R, eyes[1], 1, es[1], edeg[1])):
            svg += eye_svg(e, kd, look, s, side, dg)
    if mouth != "orig":
        svg += mouth_svg(mouth, mk)
    svg += extra
    ov = raster(svg).resize((SIZE, SIZE), Image.LANCZOS)
    a = body.getchannel("A")
    nb = Image.alpha_composite(body, ov)
    nb.putalpha(a)
    out = dict(poses[0]); out["body"] = nb
    _POSE[key] = out
    return out


# ================================================================== 臉以外的物件（場景座標）
def drop_svg(c, s, deg=0.0):
    cx, cy = c
    d = (f"M {P((cx, cy-1.5*s))} C {P((cx+0.3*s, cy-0.85*s))} {P((cx+s, cy-0.15*s))} {P((cx+s, cy+0.35*s))} "
         f"C {P((cx+s, cy+0.98*s))} {P((cx-s, cy+0.98*s))} {P((cx-s, cy+0.35*s))} "
         f"C {P((cx-s, cy-0.15*s))} {P((cx-0.3*s, cy-0.85*s))} {P((cx, cy-1.5*s))} Z")
    g = (f'<path d="{d}" fill="{SWEAT}"/>'
         f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{f(max(2.4, s*0.3))}" stroke-linejoin="round"/>'
         f'<ellipse cx="{f(cx-0.38*s)}" cy="{f(cy+0.28*s)}" rx="{f(0.2*s)}" ry="{f(0.34*s)}" fill="{SWEAT_LT}"/>')
    return f'<g transform="rotate({deg:.1f},{f(cx)},{f(cy)})">{g}</g>' if deg else g


def dots_svg(c, n, bounce=0.0, r=6.2):
    out = ""
    for j in range(n):
        dy = -bounce * math.sin(math.pi * (j / 2.0)) if bounce else 0
        out += f'<circle cx="{f(c[0]+j*20)}" cy="{f(c[1]+dy)}" r="{f(r)}" fill="{INK}"/>'
    return out


def bubble_svg(c, r):
    return (f'<circle cx="{f(c[0])}" cy="{f(c[1])}" r="{f(r)}" fill="#D7EEFB" opacity="0.75"/>'
            f'<circle cx="{f(c[0])}" cy="{f(c[1])}" r="{f(r)}" fill="none" stroke="{INK}" stroke-width="3.6"/>'
            f'<path d="M {P((c[0]-r*0.55, c[1]-r*0.15))} Q {P((c[0]-r*0.5, c[1]-r*0.55))} {P((c[0]-r*0.12, c[1]-r*0.6))}" '
            f'stroke="#FFFFFF" stroke-width="{f(max(2.2, r*0.16))}" fill="none" stroke-linecap="round"/>')


def burst_svg(body_big, g, poses, k):
    """炸毛：沿目前身體輪廓往外長一圈尖毛（腳那一側不長），畫在身體後面。"""
    a = np.asarray(body_big.getchannel("A").resize((SIZE, SIZE), Image.BILINEAR))
    c = fwd(poses, g, 254, 320)
    pts = []
    N = 52
    for i in range(N):
        ang = 2 * math.pi * i / N
        dx, dy = math.cos(ang), math.sin(ang)
        r = 10
        while r < 260:
            x, y = int(c[0] + dx * r), int(c[1] + dy * r)
            if not (0 <= x < SIZE and 0 <= y < SIZE) or a[y, x] < 100:
                break
            r += 1
        low = dy > 0.45
        rr = r * (0.94 if (i % 2 or low) else 1 + 0.13 * k * (1 + 0.25 * math.sin(i * 1.7)))
        pts.append((c[0] + dx * rr, c[1] + dy * rr))
    # 一撮一撮的毛：谷點 → 二次 Bézier 彎到尖端 → 再彎回下一個谷點（尖端都往順時針微微倒，像手繪炸毛）
    d = f"M {P(pts[1])} "
    for i in range(1, N + 1, 2):
        v0, tip, v1 = pts[i % N], pts[(i + 1) % N], pts[(i + 2) % N]
        t = (v1[0] - v0[0], v1[1] - v0[1]); L = math.hypot(*t) + 1e-6; t = (t[0] / L, t[1] / L)
        m0 = ((v0[0] + tip[0]) / 2 + t[0] * 4, (v0[1] + tip[1]) / 2 + t[1] * 4)
        m1 = ((tip[0] + v1[0]) / 2 + t[0] * 5, (tip[1] + v1[1]) / 2 + t[1] * 5)
        d += f"Q {P(m0)} {P(tip)} Q {P(m1)} {P(v1)} "
    d += "Z"
    return (f'<path d="{d}" fill="{FUR}"/>'
            f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{f(OUT_W)}" stroke-linejoin="round"/>')


def plate_svg(c, sc, deg):
    """名牌：白色圓角牌＋粉紅頂條＋兩個小吊環（懸空），sc＝彈出縮放。"""
    w, h = 268 * sc, 116 * sc
    cx, cy = c
    d = smooth_closed(jitter(rrect_pts(cx, cy, w, h, 26 * sc, 3, 4), 0.5 * sc, 21))
    band = smooth_closed(rrect_pts(cx, cy - h / 2 + 12 * sc, w - 22 * sc, 9 * sc, 4.5 * sc, 2, 2))
    shadow = smooth_closed(rrect_pts(cx + 3 * sc, cy + 7 * sc, w, h, 26 * sc, 3, 4))
    s = (f'<path d="{shadow}" fill="{PLATE_PINK}" opacity="0.9"/>'
         + shape(d, "#FFFFFF", lw=OUT_W * min(1, sc))
         + f'<path d="{band}" fill="{PLATE_PINK}" opacity="0.85"/>')
    # 左右兩顆小愛心點綴
    s += heart_svg((cx - w / 2 + 26 * sc, cy + h / 2 - 24 * sc), 7 * sc, -12, lw=2.4 * sc)
    s += heart_svg((cx + w / 2 - 26 * sc, cy + h / 2 - 24 * sc), 7 * sc, 12, lw=2.4 * sc)
    return f'<g transform="rotate({deg:.2f},{f(cx)},{f(cy)})">{s}</g>'


# ================================================================== 合成
def render(poses, fr, font):
    pose = fr.get("pose") or poses[0]
    body = pose_tween.warp_body(pose, fr["g"], SIZE).convert("RGBA")
    canvas = Image.new("RGBA", body.size, (0, 0, 0, 0))
    back = fr.get("back", "")
    if fr.get("burst"):
        back = burst_svg(body, fr["g"], poses, fr["burst"]) + back
    if back:
        canvas = Image.alpha_composite(canvas, raster(back))
    canvas = Image.alpha_composite(canvas, body)
    if fr.get("front"):
        canvas = Image.alpha_composite(canvas, raster(fr["front"]))
    for t in fr.get("texts", []):
        txt, c, deg, px = t[:4]
        col = t[4] if len(t) > 4 else (42, 22, 16, 255)
        canvas = Image.alpha_composite(canvas, text_layer(txt, c, deg, px, font, color=col))
    return canvas.resize((SIZE, SIZE), Image.LANCZOS)


def FR(poses, label, gk, face, front="", **kw):
    g = base_geom(poses, 0, **gk)
    fr = {"g": g, "label": label, "pose": face_pose(poses, **face), "front": front, "texts": []}
    fr.update(kw)
    return fr


def F(poses, g, x, y):
    return fwd(poses, g, x, y)


# ================================================================== 1. 說話 ×3
MOUTH_SEQ = ["w", "open_m", "open_s", "open_l", "open_s", "w", "open_m", "open_l", "open_s", "open_m", "w", "open_s"]
OPEN_AMT = {"w": 0.0, "open_s": 0.4, "open_m": 0.7, "open_l": 1.0, "o": 0.5}


def talk_geom(i, amp=1.0, hop=0.0):
    o = OPEN_AMT[MOUTH_SEQ[i]]
    ph = 2 * math.pi * i / 12
    return dict(h=1 + 0.022 * amp * (o - 0.45), w=1 - 0.012 * amp * (o - 0.45), lag=0.03 * amp * (o - 0.4),
                rot=1.6 * amp * math.sin(ph), bottom=-hop * max(0.0, math.sin(2 * ph)) if hop else 0)


def sound_marks(poses, g, i, n=2):
    """嘴邊的小聲音線（講話時偶爾冒出）。"""
    c = F(poses, g, 445, 236)
    return motion_lines(c, 25, spread=30, r0=8, length=15 + 3 * (i % 2), n=n, w=5.0)


def talk_happy(poses):
    frames = []
    for i, m in enumerate(MOUTH_SEQ):
        eyes = "dot"
        if i in (3, 7):
            eyes = "happy"     # 講到開心處眼睛笑瞇
        if i == 9:
            eyes = "blink"
        gk = talk_geom(i, 1.0)
        g = base_geom(poses, 0, **gk)
        front = ""
        if OPEN_AMT[m] >= 0.7:
            front += sound_marks(poses, g, i)
        if i in (3, 4, 7, 8):
            k = 1.0 if i in (3, 7) else 0.6
            front += sparkle(F(poses, g, 70, 196), 15 * k) + sparkle(F(poses, g, 445, 175), 12 * k)
        lab = {3: "開心大聲（瞇眼）", 7: "開心大聲（瞇眼）", 9: "眨眼"}.get(i, f"講話：{ {'w':'閉','open_s':'小開','open_m':'中開','open_l':'大開'}[m] }嘴")
        frames.append(FR(poses, lab, gk, dict(eyes=eyes, mouth=m, blush="soft" if i in (3, 7) else None), front))
    return frames


def talk_explain(poses):
    frames = []
    seq = ["w", "open_s", "open_m", "open_s", "w", "o", "open_s", "open_m", "w", "open_s", "open_m", "open_s"]
    for i, m in enumerate(seq):
        MOUTH_SEQ_LOCAL = OPEN_AMT[m]
        ph = 2 * math.pi * i / 12
        gk = dict(h=1 + 0.016 * (MOUTH_SEQ_LOCAL - 0.4), lag=0.02 * (MOUTH_SEQ_LOCAL - 0.4) - 0.02,
                  rot=-2.2 + 1.2 * math.sin(ph))          # 認真講：頭微歪
        g = base_geom(poses, 0, **gk)
        eyes = "blink" if i == 5 else "dot"
        look = (3.0, -1.0) if i < 6 else (-2.0, -1.0)
        # 小肉掌在臉旁打拍子（不伸手臂，只露肉掌，貼在身體右側）
        py = 352 - 16 * max(0, math.sin(2 * ph + 0.5))
        pc = F(poses, g, 398, py)
        front = paw_svg(pc, 75 - body_rot(g), r=15, squash=0.9, seed=i + 900, open_side=290)
        if i in (2, 7, 10):
            front += motion_lines(add(pc, (0, -6)), 70, spread=34, r0=16, length=9, n=2, w=3.8)
        lab = "認真講：" + {"w": "閉嘴", "open_s": "小開", "open_m": "中開", "o": "「喔」＋眨眼"}[m]
        frames.append(FR(poses, lab, gk, dict(eyes=eyes, mouth=m, look=look, brows="raise"), front))
    return frames


def body_rot(g):
    return g.get("rot", 0.0)


def talk_excited(poses):
    frames = []
    for i, m in enumerate(MOUTH_SEQ):
        ph = 2 * math.pi * i / 12
        gk = talk_geom(i, 1.8, hop=7.0)
        g = base_geom(poses, 0, **gk)
        eyes = "shine" if i != 6 else "happy"
        es = 1.06 + 0.06 * math.sin(2 * ph)
        front = ""
        # 身邊一圈小星星輪流冒（相位循環）
        for j, (sx, sy, r0) in enumerate(((58, 200, 13), (452, 168, 15), (470, 300, 10), (40, 320, 9))):
            t = (i / 12 + j * 0.25) % 1
            sz = r0 * (0.3 + 0.7 * math.sin(math.pi * t))
            front += star_svg(F(poses, g, sx, sy - 18 * t), sz, deg=40 * t + j * 20, lw=max(2.0, sz * 0.22))
        if OPEN_AMT[m] >= 0.7:
            front += sound_marks(poses, g, i, 3)
        lab = "興奮講：" + {"w": "閉嘴", "open_s": "小開", "open_m": "中開", "open_l": "大開"}[m] + ("（笑瞇）" if i == 6 else "")
        frames.append(FR(poses, lab, gk, dict(eyes=eyes, mouth=m, es=(es, es), brows="up", blush="soft"), front))
    return frames


# ================================================================== 2. 表情 ×10
def env(i, a, b):
    """第 a～b 格之間是表情的「滿」段，前後各一格過渡：回傳 0..1。"""
    if i < a - 1 or i > b + 1:
        return 0.0
    if a <= i <= b:
        return 1.0
    return 0.5


def face_love(poses):
    plan = [
        ("待機", dict(), dict(), 0),
        ("看到喜歡的（眼睛縮一下）", dict(h=0.97, w=1.02), dict(eyes="dot", mouth="w", es=(0.8, 0.8)), 0),
        ("愛心眼彈出！", dict(h=1.04, w=0.97, lag=-0.04), dict(eyes="heart", mouth="open_m", es=(1.25, 1.25), blush="lines"), 1),
        ("愛心眼跳動（大）", dict(h=1.01, rot=-2.5), dict(eyes="heart", mouth="w", es=(1.05, 1.05), blush="lines"), 2),
        ("愛心眼跳動（小）", dict(h=1.0, rot=-3.5), dict(eyes="heart", mouth="w", es=(0.92, 0.92), blush="lines"), 3),
        ("左右陶醉晃", dict(h=1.01, rot=0.5), dict(eyes="heart", mouth="open_s", es=(1.1, 1.1), blush="lines"), 4),
        ("陶醉晃（右）", dict(h=1.0, rot=3.5), dict(eyes="heart", mouth="w", es=(0.95, 0.95), blush="lines"), 5),
        ("陶醉晃（回）", dict(h=1.01, rot=1.5), dict(eyes="heart", mouth="open_s", es=(1.12, 1.12), blush="lines"), 6),
        ("愛心飄高", dict(h=1.0, rot=-1.0), dict(eyes="heart", mouth="w", es=(0.97, 0.97), blush="lines"), 7),
        ("愛心眼縮小", dict(h=0.99), dict(eyes="heart", mouth="w", es=(0.72, 0.72), blush="soft"), 8),
        ("眼睛回來、還在笑", dict(h=0.985, w=1.01), dict(eyes="happy", mouth="w", blush="soft"), 0),
        ("回待機", dict(h=0.995), dict(), 0),
    ]
    frames = []
    for i, (lab, gk, face, t) in enumerate(plan):
        g = base_geom(poses, 0, **gk)
        front = ""
        if t:
            for j, (sx, phase, s0) in enumerate(((120, 0.0, 22), (370, 0.33, 18), (250, 0.66, 15))):
                tt = ((t - 1) / 8 + phase) % 1
                if t == 1 and j:
                    continue
                c = F(poses, g, sx + 28 * math.sin(2 * math.pi * tt + j), 150 - 150 * tt)
                op = 1.0 if tt < 0.7 else (1 - tt) / 0.3
                front += heart_svg(c, s0 * (0.6 + 0.6 * math.sin(math.pi * min(1, tt * 1.4))), deg=18 * math.sin(6 * tt + j), op=op)
        frames.append(FR(poses, lab, gk, face, front))
    return frames


def face_laugh(poses):
    frames = []
    seq = [
        ("待機", dict(), dict(), 0),
        ("噗（憋笑）", dict(h=0.98, w=1.01), dict(eyes="happy", mouth="w"), 0),
        ("哈！大笑", dict(h=1.05, w=0.97, lag=-0.05, bottom=-4), dict(eyes="gt", mouth="laugh", blush="soft"), 1),
        ("抖（下）", dict(h=0.95, w=1.04, lag=0.03), dict(eyes="gt", mouth="laugh", blush="soft"), 2),
        ("抖（上）", dict(h=1.04, w=0.97, bottom=-5, rot=-2), dict(eyes="gt", mouth="laugh", blush="soft"), 1),
        ("抖（下）", dict(h=0.95, w=1.04, rot=1), dict(eyes="gt", mouth="open_l", blush="soft"), 2),
        ("抖（上）", dict(h=1.04, w=0.97, bottom=-5, rot=2), dict(eyes="gt", mouth="laugh", blush="soft"), 1),
        ("笑到彎腰", dict(h=0.93, w=1.05, lag=0.05, rot=-1), dict(eyes="gt", mouth="laugh", blush="soft"), 2),
        ("笑出眼淚", dict(h=1.03, w=0.98, bottom=-3), dict(eyes="gt", mouth="laugh", blush="soft"), 3),
        ("喘口氣", dict(h=0.98, w=1.01), dict(eyes="happy", mouth="open_m", blush="soft"), 3),
        ("餘笑", dict(h=1.0), dict(eyes="happy", mouth="w"), 0),
        ("回待機", dict(h=0.995, w=1.004), dict(), 0),
    ]
    for i, (lab, gk, face, st) in enumerate(seq):
        g = base_geom(poses, 0, **gk)
        front = ""
        if st:
            # 原圖蹲下格那種 ( ) 抖動線
            front += arcs(F(poses, g, 70, 300), 180, r=24, n=2, w=4.6) + arcs(F(poses, g, 440, 296), 0, r=24, n=2, w=4.6)
            txt_c = F(poses, g, 420 + 8 * (i % 2), 150)
            frames_txt = [("哈", (txt_c[0], txt_c[1] - 8 * (i % 2)), 12, 30), ("哈", (txt_c[0] + 30, txt_c[1] + 22), 18, 24)]
        else:
            frames_txt = []
        if st == 3:
            for e, sd in ((EYE_L, -1), (EYE_R, 1)):
                c = F(poses, g, e[0] + sd * 16, e[1] + 8)
                front += drop_svg((c[0] + sd * 4, c[1] + 4), 5.2, deg=-sd * 30)
        fr = FR(poses, lab, gk, face, front)
        fr["texts"] = frames_txt
        frames.append(fr)
    return frames


def face_proud(poses):
    seq = [
        ("待機", dict(), dict(), 0),
        ("吸氣挺胸", dict(h=1.02, w=1.01, lag=0.03), dict(eyes="dot", mouth="w"), 0),
        ("閉眼抬下巴", dict(h=1.04, lag=0.10, rot=-3), dict(eyes="happy", mouth="w", brows="up"), 1),
        ("哼～（閃光）", dict(h=1.045, lag=0.13, rot=-4), dict(eyes="happy", mouth="w", brows="up"), 2),
        ("得意晃", dict(h=1.04, lag=0.12, rot=-2), dict(eyes="happy", mouth="w", brows="up"), 3),
        ("得意晃（另一邊）", dict(h=1.045, lag=0.13, rot=-5), dict(eyes="happy", mouth="w", brows="up"), 2),
        ("閃光最亮", dict(h=1.05, lag=0.14, rot=-4), dict(eyes="happy", mouth="w", brows="up"), 3),
        ("偷睜一眼", dict(h=1.045, lag=0.13, rot=-3.5), dict(eyes=("happy", "half"), mouth="w", brows="up"), 2),
        ("再閉回去", dict(h=1.04, lag=0.12, rot=-4), dict(eyes="happy", mouth="w", brows="up"), 3),
        ("下巴放下", dict(h=1.02, lag=0.05, rot=-2), dict(eyes="happy", mouth="w"), 1),
        ("睜眼微笑", dict(h=1.0, lag=0.0), dict(eyes="dot", mouth="open_s"), 0),
        ("回待機", dict(h=0.995), dict(), 0),
    ]
    frames = []
    for i, (lab, gk, face, sp) in enumerate(seq):
        g = base_geom(poses, 0, **gk)
        front = ""
        # 兩隻小肉掌插腰（貼在身體兩側下方）
        if 1 <= i <= 10:
            for sx, deg, side in ((92, 160, 0), (418, 20, 1)):
                c = F(poses, g, sx, 388)
                front += paw_svg(c, deg - body_rot(g), r=15, squash=0.86, seed=60 + side, open_side=(0 if side else 180))
        if sp:
            k = {1: 0.55, 2: 0.85, 3: 1.1}[sp]
            front += sparkle(F(poses, g, 430, 150), 17 * k) + sparkle(F(poses, g, 470, 210), 10 * k) + \
                sparkle(F(poses, g, 80, 160), 12 * k * (1.1 if i % 2 else 0.8))
            front += motion_lines(F(poses, g, 256, 128), 90, spread=34, r0=6, length=12 * k, n=3, w=4.6)
        frames.append(FR(poses, lab, gk, face, front))
    return frames


def face_think(poses):
    seq = [
        ("待機", dict(), dict(), 0, 0),
        ("眼睛往上飄", dict(lag=0.02), dict(eyes="dot", mouth="w", look=(3, -4)), 0, 0),
        ("托下巴、往上看", dict(lag=0.05, rot=-3), dict(eyes="dot", mouth="o", look=(6, -7)), 0, 1),
        ("嗯…（一點）", dict(lag=0.06, rot=-4), dict(eyes="dot", mouth="o", look=(6, -8)), 1, 1),
        ("嗯…（兩點）", dict(lag=0.06, rot=-4.5), dict(eyes="dot", mouth="o", look=(5, -8)), 2, 1),
        ("嗯…（三點）", dict(lag=0.07, rot=-5), dict(eyes="dot", mouth="w", look=(4, -8)), 3, 1),
        ("眼睛轉另一邊", dict(lag=0.06, rot=-4), dict(eyes="dot", mouth="w", look=(-3, -8)), 3, 1),
        ("點點跳一下", dict(lag=0.07, rot=-5), dict(eyes="dot", mouth="o", look=(-5, -7)), 4, 1),
        ("還在想", dict(lag=0.06, rot=-4), dict(eyes="dot", mouth="o", look=(2, -8)), 3, 1),
        ("想到了！", dict(lag=-0.03, h=1.03, rot=0), dict(eyes="shine", mouth="open_m", look=(0, -2), brows="up"), 5, 0),
        ("想到了（亮）", dict(h=1.01), dict(eyes="shine", mouth="open_s", brows="up"), 6, 0),
        ("回待機", dict(h=0.995), dict(), 0, 0),
    ]
    frames = []
    for i, (lab, gk, face, dots, paw) in enumerate(seq):
        g = base_geom(poses, 0, **gk)
        front = ""
        if paw:
            front += paw_svg(F(poses, g, 352, 334), 115 - body_rot(g), r=17, squash=0.9, seed=33, open_side=290)  # 小肉掌托著右臉頰下緣
        if dots:
            base = F(poses, g, 380, 112)
            n = min(dots, 3)
            if dots <= 4:
                front += dots_svg((base[0] - 4, base[1]), n, bounce=8 if dots == 4 else 0)
            else:   # 想到了：燈泡（點點變成小燈泡＋放射線）
                c = F(poses, g, 400, 104)
                k = 1.0 if dots == 5 else 0.9
                bulb = smooth_closed(jitter([(c[0] + 18 * k * math.cos(a), c[1] - 4 + 20 * k * math.sin(a))
                                             for a in np.linspace(0, 2 * math.pi, 12, endpoint=False)], 0.5, 4))
                front += f'<g transform="rotate(10,{f(c[0])},{f(c[1])})">' + shape(bulb, STAR, lw=4.4) + \
                    shape(smooth_closed(rrect_pts(c[0], c[1] + 22 * k, 16 * k, 10 * k, 3, 1, 2)), "#CFC6BD", lw=3.6) + \
                    brush(bez((c[0] - 6, c[1]), (c[0] - 3, c[1] - 8), (c[0] + 3, c[1] - 8), (c[0] + 6, c[1]), 8), 3.2, 3.2, STAR_DK) + '</g>'
                front += motion_lines((c[0] + 2, c[1] - 4), 90, spread=42, r0=28 * k, length=10, n=3, w=4.4)
        frames.append(FR(poses, lab, gk, face, front))
    return frames


def face_shock(poses):
    seq = [
        ("待機", dict(), dict(), 0, 0),
        ("咦？（縮一下）", dict(h=0.95, w=1.03, lag=0.03), dict(eyes="dot", mouth="o", es=(0.85, 0.85)), 0, 0),
        ("嚇一跳！跳起、毛炸開", dict(h=1.07, w=0.96, bottom=-16, lag=-0.07), dict(eyes="wide", mouth="O", es=(1.15, 1.15)), 1.0, 1),
        ("最高點", dict(h=1.05, w=0.98, bottom=-20, lag=-0.05), dict(eyes="wide", mouth="O", es=(1.2, 1.2)), 1.2, 1),
        ("落地（毛還炸著）", dict(h=0.96, w=1.04, bottom=0), dict(eyes="wide", mouth="O", es=(1.15, 1.15)), 1.0, 2),
        ("發抖（左）", dict(h=1.0, rot=-2.5, cx=-3), dict(eyes="wide", mouth="O", es=(1.1, 1.1)), 0.85, 2),
        ("發抖（右）", dict(h=1.0, rot=2.5, cx=3), dict(eyes="wide", mouth="O", es=(1.12, 1.12)), 0.8, 2),
        ("發抖（左）", dict(h=1.0, rot=-2.0, cx=-2), dict(eyes="wide", mouth="O", es=(1.08, 1.08)), 0.6, 2),
        ("毛慢慢收回", dict(h=1.0, rot=1.0, cx=1), dict(eyes="wide", mouth="o", es=(1.0, 1.0)), 0.35, 0),
        ("眨一下", dict(h=0.99), dict(eyes="blink", mouth="o"), 0, 0),
        ("回神", dict(h=1.0), dict(eyes="dot", mouth="w", es=(1.05, 1.05)), 0, 0),
        ("回待機", dict(h=0.995), dict(), 0, 0),
    ]
    frames = []
    for i, (lab, gk, face, bu, ex) in enumerate(seq):
        g = base_geom(poses, 0, **gk)
        front = ""
        if ex:
            top = F(poses, g, 256, 120)
            front += exmark((top[0] + 2, top[1] - 26), k=1.15 if ex == 1 else 1.0, deg=4)
            front += motion_lines((top[0] - 80, top[1] + 18), 140, spread=28, r0=6, length=15, n=3, w=5) + \
                motion_lines((top[0] + 88, top[1] + 14), 40, spread=28, r0=6, length=15, n=3, w=5)
        if i in (5, 6, 7):
            front += drop_svg(F(poses, g, 400, 205), 8.5, deg=-20)
        frames.append(FR(poses, lab, gk, face, front, burst=bu))
    return frames


def face_sweat(poses):
    # 汗滴從頭的右上冒出 → 沿臉側滑下（第 3～9 格），第 7 格再冒第二滴
    seq = [
        ("待機", dict(), dict(), None),
        ("呃…眼睛飄開", dict(h=0.99), dict(eyes="dot", mouth="w", look=(-6, 1), brows="worry"), None),
        ("尷尬笑、冒汗", dict(h=0.98, w=1.01, rot=-2), dict(eyes="dot", mouth="wavy", look=(-6, 1), brows="worry", blush="lines"), 0.0),
        ("汗往下滑", dict(h=0.98, w=1.01, rot=-2.5), dict(eyes="dot", mouth="wavy", look=(-7, 1), brows="worry", blush="lines"), 0.18),
        ("抓抓頭", dict(h=0.985, rot=-3), dict(eyes="happy", mouth="wavy", brows="worry", blush="lines"), 0.34),
        ("抓抓頭（另一下）", dict(h=0.98, rot=-2), dict(eyes="happy", mouth="wavy", brows="worry", blush="lines"), 0.5),
        ("汗滑到臉頰", dict(h=0.985, rot=-2.5), dict(eyes="dot", mouth="wavy", look=(-6, 2), brows="worry", blush="lines"), 0.66),
        ("又冒一滴", dict(h=0.98, rot=-2), dict(eyes="dot", mouth="wavy", look=(-6, 2), brows="worry", blush="lines"), 0.82),
        ("嘿嘿…", dict(h=0.985, rot=-1.5), dict(eyes="happy", mouth="w", brows="worry", blush="lines"), 1.0),
        ("汗滴掉下去", dict(h=0.99, rot=-1), dict(eyes="dot", mouth="w", look=(-3, 1), blush="soft"), 1.2),
        ("鬆口氣", dict(h=0.98, w=1.01), dict(eyes="blink", mouth="w"), None),
        ("回待機", dict(h=0.995), dict(), None),
    ]
    frames = []
    for i, (lab, gk, face, t) in enumerate(seq):
        g = base_geom(poses, 0, **gk)
        front = ""
        if t is not None:
            # 汗滴路徑（原圖座標）：頭右上 → 臉右側 → 腮紅外側；超過 1 就離開身體往下掉
            if t <= 1:
                px, py = 418 - 12 * t, 168 + 120 * ease(t)
                c = F(poses, g, px, py)
                front += drop_svg(c, 9 + 3 * min(1, t * 3), deg=-12)
            else:
                c = F(poses, g, 420, 330)
                front += drop_svg((c[0] + 10, c[1] + 20), 8.5, deg=0) + motion_lines((c[0] + 10, c[1] - 6), 90, spread=0.1, r0=6, length=10, n=1, w=3.6)
        if 0.8 <= (t or 0) <= 1.0:
            front += drop_svg(F(poses, g, 404, 175), 6.5 + 3 * (t - 0.8) * 5, deg=-12)
        if i in (4, 5):
            # 小肉掌在頭右上抓抓（只有肉掌）
            # 小肉掌在頭左上抓抓（汗滴在右邊，兩邊不擠在一起）
            c = F(poses, g, 128 - (10 if i == 5 else 0), 190 + (6 if i == 5 else 0))
            front += paw_svg(c, -50 - body_rot(g), r=15, squash=0.86, seed=70 + i, open_side=120)
            front += motion_lines((c[0] - 8, c[1] - 6), 125, spread=32, r0=16, length=8, n=2, w=3.6)
        frames.append(FR(poses, lab, gk, face, front))
    return frames


def face_wink(poses):
    seq = [
        ("待機", dict(), dict(), 0),
        ("歪頭預備", dict(rot=-3, lag=-0.02), dict(eyes="dot", mouth="w"), 0),
        ("右眼眨！", dict(rot=-6, h=1.02, lag=-0.04), dict(eyes=("dot", "happy"), mouth="tongue"), 2),
        ("吐舌（最俏皮）", dict(rot=-7, h=1.025, lag=-0.05), dict(eyes=("shine", "happy"), mouth="tongue", blush="soft"), 3),
        ("定住", dict(rot=-6.5, h=1.02), dict(eyes=("shine", "happy"), mouth="tongue", blush="soft"), 2),
        ("小彈一下", dict(rot=-6, h=1.03, bottom=-4), dict(eyes=("shine", "happy"), mouth="tongue", blush="soft"), 3),
        ("落回", dict(rot=-6, h=0.99, w=1.01), dict(eyes=("shine", "happy"), mouth="tongue", blush="soft"), 2),
        ("舌頭收一半", dict(rot=-5, h=1.01), dict(eyes=("dot", "happy"), mouth="w", blush="soft"), 1),
        ("眼睛張開", dict(rot=-3.5), dict(eyes="dot", mouth="w"), 0),
        ("頭回正", dict(rot=-1.5, h=1.005), dict(eyes="dot", mouth="open_s"), 0),
        ("微彈", dict(rot=0, h=0.985, w=1.01), dict(eyes="dot", mouth="w"), 0),
        ("回待機", dict(h=0.997), dict(), 0),
    ]
    frames = []
    for i, (lab, gk, face, sp) in enumerate(seq):
        g = base_geom(poses, 0, **gk)
        front = ""
        if sp:
            k = {1: 0.5, 2: 0.85, 3: 1.1}[sp]
            c = F(poses, g, 372, 228)
            front += star_svg((c[0] + 38, c[1] - 30), 12 * k, deg=15 * i, lw=3) + sparkle((c[0] + 64, c[1] - 2), 9 * k)
            if sp >= 2:
                front += heart_svg(F(poses, g, 110, 170), 9 * k, -15)
        frames.append(FR(poses, lab, gk, face, front))
    return frames


def face_star(poses):
    seq = [
        ("待機", dict(), dict(), 0),
        ("看到了！（眼睛放大）", dict(h=1.02, lag=-0.02), dict(eyes="shine", mouth="o", es=(1.15, 1.15)), 0),
        ("星星眼！", dict(h=1.05, w=0.97, bottom=-8, lag=-0.05), dict(eyes="star", mouth="open_l", es=(1.15, 1.15), edeg=(0, 0), brows="up"), 1),
        ("星星轉", dict(h=1.02, bottom=-4), dict(eyes="star", mouth="open_m", es=(1.0, 1.0), edeg=(18, -18), brows="up"), 2),
        ("落地閃閃", dict(h=0.97, w=1.03), dict(eyes="star", mouth="open_l", es=(1.18, 1.18), edeg=(36, -36), brows="up"), 3),
        ("星星轉", dict(h=1.02, rot=-2), dict(eyes="star", mouth="open_m", es=(1.0, 1.0), edeg=(54, -54), brows="up"), 2),
        ("再閃", dict(h=1.0, rot=2), dict(eyes="star", mouth="open_l", es=(1.18, 1.18), edeg=(72, -72), brows="up"), 3),
        ("星星轉", dict(h=1.01, rot=-1), dict(eyes="star", mouth="open_m", es=(1.02, 1.02), edeg=(90, -90), brows="up"), 2),
        ("最亮", dict(h=1.02, bottom=-3), dict(eyes="star", mouth="open_l", es=(1.2, 1.2), edeg=(108, -108), brows="up"), 3),
        ("星星縮小", dict(h=0.99), dict(eyes="star", mouth="open_s", es=(0.75, 0.75), edeg=(126, -126)), 1),
        ("眼睛還亮亮", dict(h=0.99, w=1.01), dict(eyes="shine", mouth="w", es=(1.08, 1.08)), 0),
        ("回待機", dict(h=0.997), dict(), 0),
    ]
    frames = []
    for i, (lab, gk, face, sp) in enumerate(seq):
        g = base_geom(poses, 0, **gk)
        front = ""
        if sp:
            k = {1: 0.6, 2: 0.85, 3: 1.15}[sp]
            for j, (sx, sy, r0) in enumerate(((60, 175, 14), (450, 150, 16), (480, 290, 10), (30, 300, 10), (256, 108, 9))):
                rr = r0 * k * (0.75 + 0.35 * ((i + j) % 2))
                front += sparkle(F(poses, g, sx, sy), rr) if j % 2 else star_svg(F(poses, g, sx, sy), rr, deg=20 * i, lw=2.6)
        frames.append(FR(poses, lab, gk, face, front))
    return frames


def face_sleepy(poses):
    # 不用熬夜看盤：打瞌睡 → 鼻涕泡變大 → 啵！醒 → 又瞇回去（接回第 1 格）
    seq = [
        ("睏睏（半閉眼）", dict(h=0.99), dict(eyes="half", mouth="w"), 0, 0),
        ("眼皮越來越重", dict(h=0.98, lag=-0.04, rot=-2), dict(eyes="line", mouth="w"), 0, 0),
        ("點頭睡著", dict(h=0.96, w=1.02, lag=-0.08, rot=-4), dict(eyes="line", mouth="tiny"), 1, 4),
        ("Zzz", dict(h=0.965, w=1.02, lag=-0.07, rot=-4.5), dict(eyes="line", mouth="tiny"), 2, 8),
        ("呼…吸（身體脹）", dict(h=0.975, w=1.03, lag=-0.07, rot=-4), dict(eyes="line", mouth="tiny"), 3, 13),
        ("呼…吐", dict(h=0.96, w=1.015, lag=-0.08, rot=-4.5), dict(eyes="line", mouth="tiny"), 4, 10),
        ("呼…吸", dict(h=0.975, w=1.03, lag=-0.07, rot=-4), dict(eyes="line", mouth="tiny"), 5, 17),
        ("泡泡最大", dict(h=0.97, w=1.025, lag=-0.075, rot=-4.5), dict(eyes="line", mouth="tiny"), 6, 22),
        ("啵！", dict(h=1.03, w=0.98, lag=0.02, rot=0, bottom=-6), dict(eyes="wide", mouth="o", es=(0.95, 0.95)), 0, -1),
        ("醒了？", dict(h=1.0), dict(eyes="dot", mouth="w"), 0, 0),
        ("又睏了", dict(h=0.99), dict(eyes="half", mouth="w"), 0, 0),
        ("瞇眼", dict(h=0.99, lag=-0.02), dict(eyes="half", mouth="tiny"), 0, 0),
    ]
    frames = []
    for i, (lab, gk, face, z, bub) in enumerate(seq):
        g = base_geom(poses, 0, **gk)
        front = ""
        texts = []
        if z:
            # 三個 Z 從頭右上往上飄（循環相位）
            for j in range(3):
                t = ((z - 1) / 6 + j / 3) % 1
                c = F(poses, g, 400 + 40 * t + 8 * math.sin(6 * t), 150 - 120 * t)
                px = 22 + 22 * t
                alpha = int(255 * (1 if t < 0.75 else (1 - t) / 0.25))
                texts.append(("Z", c, -14 + 10 * t, px, (42, 22, 16, alpha)))
        if bub > 0:
            c = F(poses, g, 278, 300)
            front += bubble_svg((c[0] + bub * 0.6, c[1] + 2), bub)
        elif bub < 0:
            c = F(poses, g, 278, 300)
            front += motion_lines((c[0] + 12, c[1]), 0, spread=40, r0=12, length=12, n=5, w=4.2)
            front += exmark(F(poses, g, 420, 140), k=0.6, deg=12)
        fr = FR(poses, lab, gk, face, front)
        fr["texts"] = texts
        frames.append(fr)
    return frames


def face_nod(poses):
    # 嗯嗯：點頭兩下（頭往下＝lag 負、身體壓），閉眼笑；頭上冒「嗯嗯」
    seq = [
        ("待機", dict(), dict(), 0),
        ("聽著（微笑）", dict(h=1.0, lag=0.02), dict(eyes="dot", mouth="w"), 0),
        ("點頭（下）", dict(h=0.95, w=1.025, lag=-0.11), dict(eyes="happy", mouth="w"), 1),
        ("點頭（最低）", dict(h=0.94, w=1.03, lag=-0.13), dict(eyes="happy", mouth="w"), 2),
        ("回來（上）", dict(h=1.015, lag=0.03), dict(eyes="happy", mouth="open_s"), 2),
        ("點頭（下）", dict(h=0.95, w=1.025, lag=-0.11), dict(eyes="happy", mouth="w"), 3),
        ("點頭（最低）", dict(h=0.94, w=1.03, lag=-0.13), dict(eyes="happy", mouth="w"), 3),
        ("回來（上）", dict(h=1.015, lag=0.03), dict(eyes="happy", mouth="open_s"), 3),
        ("嗯！（睜眼）", dict(h=1.005, lag=0.0), dict(eyes="shine", mouth="open_m", blush="soft"), 4),
        ("肯定的閃光", dict(h=1.0), dict(eyes="shine", mouth="w", blush="soft"), 4),
        ("放鬆", dict(h=0.99, w=1.005), dict(eyes="dot", mouth="w"), 0),
        ("回待機", dict(h=0.997), dict(), 0),
    ]
    frames = []
    for i, (lab, gk, face, st) in enumerate(seq):
        g = base_geom(poses, 0, **gk)
        front = ""
        texts = []
        if st:
            c = F(poses, g, 420, 140)
            if st >= 2:
                texts.append(("嗯", (c[0] - 4, c[1] - (6 if i in (3, 6) else 0)), 10, 30))
            if st >= 3:
                texts.append(("嗯", (c[0] + 30, c[1] + 26 - (6 if i in (6,) else 0)), 16, 26))
            if i in (2, 3, 5, 6):
                front += arcs(F(poses, g, 256, 118), 90, r=18, n=2, w=4.2)
            if st == 4:
                front += sparkle(F(poses, g, 80, 170), 13 if i == 8 else 9) + sparkle(F(poses, g, 450, 210), 9 if i == 8 else 13)
        fr = FR(poses, lab, gk, face, front)
        fr["texts"] = texts
        frames.append(fr)
    return frames


# ================================================================== 3. 自我介紹
PLATE_C = (250, 112)


def intro(poses, with_text=True):
    seq = [
        # 標籤, 幾何, 臉, 名牌縮放, 肉掌(揮手相位)
        ("從下方冒出頭", dict(bottom=200, h=1.06, w=0.95, lag=-0.05), dict(eyes="dot", mouth="w"), 0, None),
        ("往上竄（拉長）", dict(bottom=70, h=1.13, w=0.91, lag=-0.08), dict(eyes="shine", mouth="open_s"), 0, None),
        ("衝到最高", dict(bottom=-44, h=1.07, w=0.95, lag=-0.04), dict(eyes="shine", mouth="open_l"), 0, None),
        ("往下落", dict(bottom=-16, h=1.03, w=0.98, lag=0.02), dict(eyes="shine", mouth="open_m"), 0, None),
        ("落地壓扁", dict(h=0.88, w=1.08, lag=0.05), dict(eyes="happy", mouth="w"), 0, None),
        ("回彈", dict(h=1.04, w=0.97, lag=-0.02), dict(eyes="dot", mouth="open_s"), 0, None),
        ("站穩、名牌冒出", dict(h=1.0, lag=0.06), dict(eyes="dot", mouth="open_m", look=(0, -3)), 0.45, None),
        ("揮掌（外）、名牌彈大", dict(h=1.01, lag=0.08, rot=-1.5), dict(eyes="happy", mouth="open_l", blush="soft"), 1.14, 0),
        ("揮掌（內）", dict(h=1.0, lag=0.08, rot=1.0), dict(eyes="happy", mouth="open_m", blush="soft"), 0.96, 1),
        ("揮掌（外）", dict(h=1.01, lag=0.08, rot=-1.5), dict(eyes="happy", mouth="open_l", blush="soft"), 1.02, 0),
        ("揮掌（內）", dict(h=1.0, lag=0.08, rot=1.0), dict(eyes="happy", mouth="open_m", blush="soft"), 1.0, 1),
        ("掌放下、看名牌", dict(h=1.0, lag=0.10), dict(eyes="dot", mouth="w", look=(0, -4)), 1.0, None),
        ("回頭看鏡頭", dict(h=1.0, lag=0.04), dict(eyes="dot", mouth="open_s"), 1.0, None),
        ("眨眼！", dict(h=1.015, lag=0.02, rot=-3), dict(eyes=("dot", "happy"), mouth="tongue", blush="soft"), 1.0, None),
        ("微笑", dict(h=1.0, rot=-1), dict(eyes="dot", mouth="open_s", blush="soft"), 1.0, None),
        ("待機（名牌飄）", dict(h=0.995), dict(eyes="dot", mouth="w"), 1.0, None),
    ]
    frames = []
    for i, (lab, gk, face, ps, wave) in enumerate(seq):
        g = base_geom(poses, 0, **gk)
        front = ""
        texts = []
        if i <= 1:
            top = F(poses, g, 256, 150)
            front += motion_lines((top[0] - 110, top[1] + 60), 270, spread=0.1, r0=0, length=26, n=1, w=5) + \
                motion_lines((top[0] + 110, top[1] + 60), 270, spread=0.1, r0=0, length=26, n=1, w=5)
        if i == 4:
            front += motion_lines((CX_ - 160, 470), 160, spread=22, r0=4, length=12, n=2, w=4.6) + \
                motion_lines((CX_ + 160, 470), 20, spread=22, r0=4, length=12, n=2, w=4.6)
        if ps:
            ph = 2 * math.pi * i / 16
            c = (PLATE_C[0], PLATE_C[1] - 4 * math.sin(ph))
            deg = -3 + 2.5 * math.sin(ph + 1)
            front += BA.float_marks((c[0], c[1] + 58 * ps + 6), 230 * ps, ph) if ps >= 0.9 else ""
            front += plate_svg(c, ps, deg)
            if ps < 0.9:
                front += sparkle((c[0] - 120 * ps - 10, c[1] - 20), 10) + sparkle((c[0] + 130 * ps + 10, c[1] + 10), 8)
            if with_text and ps >= 0.9:
                r = math.radians(deg)
                def T(dx, dy):
                    return (c[0] + (dx * math.cos(r) - dy * math.sin(r)) * ps, c[1] + (dx * math.sin(r) + dy * math.cos(r)) * ps)
                texts.append(("比比", T(0, -12), deg, 54 * ps, (232, 96, 124, 255)))
                texts.append(("問題解答小助手", T(0, 32), deg, 21 * ps, (74, 44, 34, 255)))
        if wave is not None:
            pc = F(poses, g, 438 if wave == 0 else 420, 228 if wave == 0 else 250)
            deg = (60 if wave == 0 else 100) - body_rot(g)
            front += paw_svg(pc, deg, r=16, squash=0.86, seed=80 + i, open_side=deg + 180)
            front += arcs(pc, deg - 10, r=24, n=2, w=4.4)
        if i == 13:
            c = F(poses, g, 372, 228)
            front += star_svg((c[0] + 40, c[1] - 30), 12, deg=20, lw=3) + sparkle((c[0] + 66, c[1] - 2), 9)
        fr = FR(poses, lab, gk, face, front)
        fr["texts"] = texts
        frames.append(fr)
    return frames


CX_ = BA.CX

CLIPS = {
    "talk_happy": ("說話・開心講（嘴巴三種嘴型輪替、講到開心處瞇眼）", talk_happy, [100] * 12, "說話"),
    "talk_explain": ("說話・認真講（挑眉、小肉掌打拍子）", talk_explain, [110] * 12, "說話"),
    "talk_excited": ("說話・興奮講（眼睛發亮、小星星）", talk_excited, [90] * 12, "說話"),
    "face_love": ("表情・愛心眼（飄小愛心）", face_love, [200, 90, 120, 110, 110, 120, 120, 120, 130, 100, 120, 180], "表情"),
    "face_laugh": ("表情・大笑瞇眼（身體抖）", face_laugh, [200, 110, 110, 70, 70, 70, 70, 110, 140, 120, 120, 160], "表情"),
    "face_proud": ("表情・得意（閉眼抬下巴、小閃光）", face_proud, [180, 110, 130, 140, 120, 120, 160, 160, 120, 110, 120, 160], "表情"),
    "face_think": ("表情・思考（往上看、點點點、想到了）", face_think, [180, 120, 140, 160, 160, 160, 140, 120, 140, 140, 160, 160], "表情"),
    "face_shock": ("表情・嚇一跳（白眼圈、毛炸開）", face_shock, [200, 90, 80, 100, 110, 60, 60, 60, 120, 90, 110, 160], "表情"),
    "face_sweat": ("表情・冒汗尷尬（汗滴滑落、抓抓頭）", face_sweat, [180, 130, 120, 110, 100, 100, 110, 110, 140, 110, 140, 160], "表情"),
    "face_wink": ("表情・眨眼吐舌", face_wink, [180, 90, 90, 150, 120, 80, 90, 100, 100, 100, 100, 160], "表情"),
    "face_star": ("表情・星星眼（轉圈、閃閃）", face_star, [180, 100, 100, 90, 100, 90, 100, 90, 140, 100, 120, 160], "表情"),
    "face_sleepy": ("表情・打瞌睡（Zzz、鼻涕泡、啵！）", face_sleepy, [220, 200, 160, 180, 200, 180, 200, 220, 140, 180, 200, 200], "表情"),
    "face_nod": ("表情・點頭嗯嗯（同意）", face_nod, [180, 110, 90, 90, 100, 90, 90, 100, 150, 130, 120, 160], "表情"),
    "intro": ("自我介紹（彈進畫面、揮掌、名牌、眨眼）", intro, [90, 70, 80, 80, 90, 90, 110, 110, 110, 110, 110, 140, 140, 220, 160, 360], "介紹"),
    "intro_blank": ("自我介紹・名牌留白版（影片自己放字）", lambda p: intro(p, with_text=False),
                    [90, 70, 80, 80, 90, 90, 110, 110, 110, 110, 110, 140, 140, 220, 160, 360], "介紹"),
}

USE = {
    "說話": "影片旁白段（比比在講解時循環播放），對嘴的速度跟字幕走",
    "表情": "影片情緒點綴／貼圖（12 格，待機→表情→回待機，可循環）",
    "介紹": "影片開場（比比第一次登場，播一次後停在最後一格）",
}


def write_storyboard(rd, key, name, frs, durs, kind):
    lines = [f"# 比比・{name}（{len(frs)} 格）", "",
             "- 需求：Andy 2026-10-10「幫我在影片中新增多點 GIF 圖，表情越豐富越好，情境越多越好，可以多點物件，"
             "動作可以跟影片有更多互動，讓觀眾有是比比在介紹的感覺」。",
             f"- 用途：{USE[kind]}。",
             f"- 製作：`BIBI_SIGN_FONT=<jf-openhuninn-2.1.ttf> python scripts/anim/bibi_faces_c.py --out <scratchpad>/bibi "
             f"--repo-out docs/anim --only {key}`。",
             "- 身體：原圖 `site/brand/src/support_anim_1009.gif` 第 0 張像素的網格變形（raster_first）；"
             "場景座標同 A／B 批（身體縮 0.75、中心 x=248、腳底 y=482）；512×512、透明。",
             "- 五官：在原圖座標上先用周圍毛色補掉原本的眼睛／嘴巴（腮紅保留），再用 SVG 三次 Bézier 畫新五官，"
             "跟身體一起變形，所以歪頭、壓扁時五官跟著臉走。臉外物件在場景座標畫、錨點跟著身體。",
             "- 依 Andy 退件教訓：不畫從身體伸出的長手臂，只露小肉掌。",
             f"- 合計 {sum(durs)}ms，無限循環；相鄰格皆有實際差異。", "",
             "| 格 | 動作／表情 | 停留 ms |", "|---|---|---|"]
    for j, (fr, d) in enumerate(zip(frs, durs)):
        lines.append(f"| {j+1:02d} | {fr['label']} | {d} |")
    (rd / "storyboard.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="site/brand/src/support_anim_1009.gif")
    ap.add_argument("--out", required=True)
    ap.add_argument("--repo-out", default="docs/anim")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    poses = pose_tween.load_poses(Path(a.src))
    out = Path(a.out)
    idx_path = out / "index_c.json"
    index = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else {}
    only = [x for x in a.only.split(",") if x]
    font = BA.HUNINN
    for key, (name, fn, durs, kind) in CLIPS.items():
        if only and key not in only:
            continue
        frs = fn(poses)
        assert len(frs) == len(durs), key
        imgs = [render(poses, fr, font) for fr in frs]
        fd = out / key / "frames"
        fd.mkdir(parents=True, exist_ok=True)
        for old in fd.glob("frame_*.png"):
            old.unlink()
        paths = []
        for j, im in enumerate(imgs):
            p = fd / f"frame_{j+1:02d}.png"
            im.save(p)
            paths.append(str(p.resolve()))
        rd = Path(a.repo_out) / f"bibi_{key}"
        rd.mkdir(parents=True, exist_ok=True)
        labels = [f"{j+1:02d} {fr['label']}" for j, fr in enumerate(frs)]
        sheet12(imgs, labels, rd / "sheet_12.png")
        imgs[0].save(rd / "anim.webp", save_all=True, append_images=imgs[1:], duration=durs, loop=0,
                     lossless=False, quality=88, method=6)
        imgs[0].save(out / key / "anim.gif", save_all=True, append_images=imgs[1:], duration=durs, loop=0, disposal=2)
        write_storyboard(rd, key, name, frs, durs, kind)
        arr = [np.asarray(i).astype(int) for i in imgs]
        n = len(arr)
        diffs = [int(np.abs(arr[k] - arr[(k + 1) % n]).sum() // 1000) for k in range(n)]
        index[key] = {"name": name, "size": [SIZE, SIZE], "frames": paths, "durations_ms": durs,
                      "labels": [fr["label"] for fr in frs], "adjacent_diff_k": diffs,
                      "scene": {"scale": BA.SCALE, "center_x": BA.CX, "ground_y": BA.GROUND},
                      "gif": str((out / key / "anim.gif").resolve()),
                      "webp": str((rd / "anim.webp").resolve()), "sheet": str((rd / "sheet_12.png").resolve())}
        print(key, "格數", n, "最小相鄰差", min(diffs), "→", rd, flush=True)
    # 平行跑多支時，寫回前重讀一次再合併，避免互相蓋掉
    mine = {k: v for k, v in index.items() if not only or k in only}
    index = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else {}
    index.update(mine)
    idx_path.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
