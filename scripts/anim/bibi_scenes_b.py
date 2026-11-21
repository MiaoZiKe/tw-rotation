"""動畫設計單位：吉祥物「比比」B 批 5 個情境（存錢筒／按計算機／複利長大／喝珍奶／翻日曆），每組 12 格、512×512、透明。

為什麼有這支
------------
Andy 2026-10-10：「幫我在影片中新增多點 GIF 圖，並且越豐富，情境越多越好」（IG／Threads 宣傳影片，
分鏡 `docs/marketing/video_1010/storyboard.md`）。A 批（揮手／指向／歪頭／驚嘆／舉牌）在 `bibi_actions.py`；
這支只 import 它與 `pose_tween.py` 的函式，**不改那兩支**（另一位設計師同時在改）。

規格（docs/anim/prompt_kit/01_總控Prompt.md）
--------------------------------------------
- 比比本體＝原圖 `site/brand/src/support_anim_1009.gif` 的像素網格變形（raster_first），不重畫角色。
  開心蹲／落地用原圖第 2 張（瞇眼笑）；閉眼、滿足瞇眼只在眼睛那一小塊蓋毛色再補一道手繪弧線。
- 道具（存錢筒、金幣、計算機、珍奶、日曆、小樹）用 SVG 三次 Bézier（Catmull-Rom 轉 C）畫，
  外框點加微小抖動＝手繪感；描邊色／粗細與原圖一致（#1A0907、7.5px×0.75），4 倍繪製再 LANCZOS 縮回。
- Andy 退件教訓：從身體伸出的長手臂很怪 → 道具一律懸空／放在比比身前地上／貼著身體前方，手只露小肉掌。
- 場景座標跟 A 批相同：身體縮 0.75、中心 x=248、腳底 y=482。

用法
----
    BIBI_SIGN_FONT=<jf-openhuninn-2.1.ttf> python scripts/anim/bibi_scenes_b.py \
        --out <scratchpad>/bibi --repo-out docs/anim [--only piggy,calc]
輸出：<out>/<名>/frames/frame_01.png…、<repo-out>/bibi_<名>/sheet_12.png、anim.webp；<out>/index_b.json。
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

from bibi_actions import (INK, FUR_SH, SPARK, SIZE, OUT_W, f, P, add, dirv, bez, brush,  # noqa: E402
                          sparkle, motion_lines, paw_svg, base_geom, fwd, raster, text_layer, sheet12,
                          float_marks, ease)

FUR_FACE = "#FDF4E6"     # 臉部毛色（原圖第 0 張眼睛四周取樣平均）
GOLD, GOLD_DK, GOLD_LT = "#F9C23C", "#E39A22", "#FFE7A3"
PIG, PIG_DK, PIG_SN = "#F7B9C3", "#EC98A8", "#F29DAE"
LEAF, LEAF_DK, LEAF_LT = "#A6DB8F", "#7DBF6C", "#CFEFBF"
BARK, BARK_DK = "#C08A62", "#9C6A47"
TEA, TEA_DK, PEARL = "#DDB085", "#C9935F", "#4A2A1E"
STRAW = "#8ED3B8"
CALC, CALC_DK, SCREEN = "#A9D7EA", "#82BFD9", "#E8F2D5"
CAL_RED = "#F28B7D"

EYE_L, EYE_R = (192, 263.5), (309, 261)  # 原圖第 0 張眼睛中心（黑點約 25px 寬）
MOUTH0 = (250, 288)                       # 原圖第 0 張嘴巴中心

LW = OUT_W            # 道具主描邊
LW2 = OUT_W * 0.62    # 道具內部細線


# ================================================================== 手繪路徑工具
def smooth_closed(pts):
    """封閉 Catmull-Rom → 三次 Bézier（每段 C），線條圓順、沒有幾何折角。"""
    n = len(pts)
    d = f"M {P(pts[0])} "
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f"C {P(c1)} {P(c2)} {P(p2)} "
    return d + "Z"


def smooth_open(pts):
    n = len(pts)
    d = f"M {P(pts[0])} "
    for i in range(n - 1):
        p0 = pts[max(i - 1, 0)]; p1 = pts[i]; p2 = pts[i + 1]; p3 = pts[min(i + 2, n - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f"C {P(c1)} {P(c2)} {P(p2)} "
    return d


def jitter(pts, amp, seed):
    rng = np.random.default_rng(seed)
    return [(x + rng.uniform(-amp, amp), y + rng.uniform(-amp, amp)) for x, y in pts]


def rot_pts(pts, c, deg):
    r = math.radians(deg); cr, sr = math.cos(r), math.sin(r)
    return [(c[0] + (x - c[0]) * cr - (y - c[1]) * sr, c[1] + (x - c[0]) * sr + (y - c[1]) * cr) for x, y in pts]


def rrect_pts(cx, cy, w, h, r, per_edge=2, per_corner=3):
    """圓角矩形外框取樣點（順時針），給 smooth_closed 用。"""
    hw, hh = w / 2, h / 2
    pts = []
    corners = [(hw - r, -hh + r, -90), (hw - r, hh - r, 0), (-hw + r, hh - r, 90), (-hw + r, -hh + r, 180)]
    for k, (ox, oy, a0) in enumerate(corners):
        for j in range(per_corner):
            a = math.radians(a0 + 90 * (j + 0.5) / per_corner)
            pts.append((cx + ox + r * math.cos(a), cy + oy + r * math.sin(a)))
        nx = corners[(k + 1) % 4]
        for j in range(1, per_edge + 1):
            t = j / (per_edge + 1)
            ax, ay = ox + r * math.cos(math.radians(a0 + 90)), oy + r * math.sin(math.radians(a0 + 90))
            bx, by = nx[0] + r * math.cos(math.radians(nx[2])), nx[1] + r * math.sin(math.radians(nx[2]))
            pts.append((cx + ax + (bx - ax) * t, cy + ay + (by - ay) * t))
    return pts


def ellipse_pts(cx, cy, rx, ry, n=10, bump=0.0, seed=0, phase=0.0):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        a = 2 * math.pi * i / n + phase
        k = 1 + bump * (0.5 + 0.5 * math.cos(i * math.pi)) + rng.uniform(-0.015, 0.015)
        out.append((cx + rx * k * math.cos(a), cy + ry * k * math.sin(a)))
    return out


def shape(d, fill, lw=LW, stroke=INK, extra=""):
    s = f'<path d="{d}" fill="{fill}" {extra}/>'
    if lw:
        s += f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{f(lw)}" stroke-linejoin="round" stroke-linecap="round"/>'
    return s


def clip(cid, d, body):
    return f'<clipPath id="{cid}"><path d="{d}"/></clipPath><g clip-path="url(#{cid})">{body}</g>'


def squash_g(body, c, sx, sy):
    """以 c（底部中心）為錨點擠壓整組道具。"""
    return (f'<g transform="translate({f(c[0])},{f(c[1])}) scale({sx:.4f},{sy:.4f}) '
            f'translate({f(-c[0])},{f(-c[1])})">{body}</g>')


def shine(c, r, deg=-135, w=3.2):
    """道具左上角的白色亮光短弧（跟原圖肉掌亮點同一種處理）。"""
    p0 = add(c, dirv(deg - 25), r); p3 = add(c, dirv(deg + 25), r)
    m1 = add(c, dirv(deg - 8), r * 1.04); m2 = add(c, dirv(deg + 8), r * 1.04)
    return f'<g opacity="0.85">{brush(bez(p0, m1, m2, p3, 10), w, w * 0.8, "#FFFFFF")}</g>'


# ================================================================== 臉部小修（只蓋眼睛那一小塊）
def eyes_svg(poses, g, mode):
    """mode：'blink'（閉眼 ‿）、'half'（半閉）、'happy'（滿足瞇眼 ︶ 反過來的 ∩）。"""
    out = (f'<radialGradient id="eg"><stop offset="0.74" stop-color="{FUR_FACE}" stop-opacity="1"/>'
           f'<stop offset="1" stop-color="{FUR_FACE}" stop-opacity="0"/></radialGradient>')
    for e in (EYE_L, EYE_R):
        c = fwd(poses, g, *e)
        r = 11.2
        if mode == "half":
            # 上半蓋毛色（漸層邊、只蓋眼睛上半）＋眼皮線
            cid = f"eh{int(c[0]*10)}"
            out += (f'<clipPath id="{cid}"><rect x="{f(c[0]-17)}" y="{f(c[1]-17)}" width="34" height="17.5"/></clipPath>'
                    f'<circle cx="{f(c[0])}" cy="{f(c[1])}" r="15.5" fill="url(#eg)" clip-path="url(#{cid})"/>')
            out += brush(bez((c[0]-8, c[1]+0.5), (c[0]-3, c[1]-1.2), (c[0]+3, c[1]-1.2), (c[0]+8, c[1]+0.5), 10), 4.6, 4.6)
            continue
        out += f'<circle cx="{f(c[0])}" cy="{f(c[1])}" r="15.5" fill="url(#eg)"/>'
        if mode == "blink":
            out += brush(bez((c[0]-8, c[1]-1), (c[0]-3, c[1]+3.5), (c[0]+3, c[1]+3.5), (c[0]+8, c[1]-1), 12), 4.8, 4.8)
        else:  # happy
            out += brush(bez((c[0]-8.5, c[1]+3), (c[0]-4, c[1]-4.5), (c[0]+4, c[1]-4.5), (c[0]+8.5, c[1]+3), 12), 4.8, 4.8)
    return out


def puff_svg(poses, g):
    """臉頰鼓起：腮紅外側兩道小弧線（原圖蹲下格那種動作線），不改角色輪廓。"""
    out = ""
    for (px, py), side in (((118, 300), -1), ((392, 296), 1)):
        c = fwd(poses, g, px, py)
        p0 = (c[0], c[1] - 9); p3 = (c[0], c[1] + 9)
        m = (c[0] + side * 5, c[1])
        out += brush(bez(p0, m, m, p3, 10), 3.8, 3.2)
    return out


# ================================================================== 道具：金幣
def coin_svg(c, r=17, spin=1.0, deg=0.0):
    """正面金幣：spin＝水平寬度比例（翻轉），太窄時畫成側面的一條金邊。"""
    sx = max(abs(spin), 0.16)
    rx, ry = r * sx, r
    pts = rot_pts(ellipse_pts(c[0], c[1], rx, ry, 12, seed=int(r * 10)), c, deg)
    d = smooth_closed(pts)
    s = shape(d, GOLD if abs(spin) > 0.3 else GOLD_DK)
    if abs(spin) > 0.3:
        inner = smooth_closed(rot_pts(ellipse_pts(c[0], c[1], rx * 0.64, ry * 0.64, 10, seed=3), c, deg))
        s += f'<path d="{inner}" fill="none" stroke="{GOLD_DK}" stroke-width="{f(LW2)}"/>'
        s += f'<g opacity="0.9">{brush(bez((c[0]-rx*0.18, c[1]-ry*0.28), (c[0]-rx*0.05, c[1]-ry*0.05), (c[0]-rx*0.05, c[1]+ry*0.1), (c[0]-rx*0.18, c[1]+ry*0.3), 8), 3.4*sx+1, 2.6*sx+1, GOLD_LT)}</g>'
    return s


def coin_stack_svg(cx, bottom, n, rx=36, ry=11, th=12.5, seed=7):
    """側面疊起的金幣：由下往上畫，每枚 x 有固定小偏移（手疊的樣子）。"""
    rng = np.random.default_rng(seed)
    offs = [rng.uniform(-4, 4) for _ in range(10)]
    s = ""
    for i in range(n):
        x = cx + offs[i]
        ty = bottom - ry - th - i * th            # 這枚頂面中心
        # 側邊帶：左邊往下 → 下半橢圓 → 右邊往上 → 上半橢圓的前緣（藏在頂面下）
        side = (f"M {P((x-rx, ty))} L {P((x-rx, ty+th))} "
                f"C {P((x-rx, ty+th+ry*1.33))} {P((x+rx, ty+th+ry*1.33))} {P((x+rx, ty+th))} "
                f"L {P((x+rx, ty))} C {P((x+rx, ty+ry*1.33))} {P((x-rx, ty+ry*1.33))} {P((x-rx, ty))} Z")
        s += shape(side, GOLD_DK)
        for k in range(-3, 4):   # 側邊刻紋
            xx = x + k * rx * 0.27
            yy = ty + ry * math.sqrt(max(0, 1 - (k * 0.27) ** 2)) * 0.98
            s += f'<path d="M {P((xx, yy+2.5))} L {P((xx, yy+th-1.5))}" stroke="#B8761A" stroke-width="2.2" stroke-linecap="round" opacity="0.7"/>'
        top = smooth_closed(ellipse_pts(x, ty, rx, ry, 12, seed=seed + i))
        s += shape(top, GOLD)
        s += f'<path d="{smooth_closed(ellipse_pts(x, ty, rx*0.62, ry*0.58, 10, seed=i+30))}" fill="none" stroke="{GOLD_DK}" stroke-width="{f(LW2)}"/>'
        s += f'<g opacity="0.9">{brush(bez((x-rx*0.55, ty-ry*0.15), (x-rx*0.4, ty-ry*0.55), (x-rx*0.15, ty-ry*0.62), (x, ty-ry*0.6), 8), 2.8, 2.2, GOLD_LT)}</g>'
    return s


# ================================================================== 情境 1：存錢筒
PIG_C = (404, 428)   # 存錢筒身體中心
PIG_BOT = 481.0


def piggy_svg(sq=1.0, wig=0.0):
    cx, cy = PIG_C[0] + wig, PIG_C[1]
    rx, ry = 68, 47
    s = ""
    # 四隻短腳（在身體後面）
    for i, lx in enumerate((-34, -12, 14, 36)):
        x = cx + lx
        leg = smooth_closed(jitter(rrect_pts(x, PIG_BOT - 13, 17, 26, 7, 1, 2), 0.5, 40 + i))
        s += shape(leg, PIG_DK if i in (1, 3) else PIG)
    # 尾巴（右側小捲）
    tail = [(cx + rx - 4, cy - 6), (cx + rx + 12, cy - 12), (cx + rx + 16, cy - 2), (cx + rx + 7, cy + 1), (cx + rx + 11, cy - 10), (cx + rx + 22, cy - 14)]
    s += f'<path d="{smooth_open(tail)}" fill="none" stroke="{INK}" stroke-width="{f(LW*0.85)}" stroke-linecap="round"/>'
    # 後耳
    ear_b = [(cx - 24, cy - ry + 8), (cx - 14, cy - ry - 16), (cx - 2, cy - ry + 4)]
    s += shape(smooth_closed(ear_b), PIG_DK)
    # 身體
    body = smooth_closed(jitter(ellipse_pts(cx, cy, rx, ry, 14, seed=5), 0.6, 9))
    s += shape(body, PIG)
    # 身體下半陰影
    sh = (f"M {P((cx-rx+12, cy+14))} C {P((cx-rx*0.4, cy+ry*0.55))} {P((cx+rx*0.4, cy+ry*0.55))} {P((cx+rx-10, cy+12))} "
          f"C {P((cx+rx*0.5, cy+ry*1.02))} {P((cx-rx*0.5, cy+ry*1.02))} {P((cx-rx+12, cy+14))} Z")
    s += f'<path d="{sh}" fill="{PIG_DK}" opacity="0.55"/>'
    s += shine((cx + 8, cy + 4), 46, deg=115, w=3.6)
    # 前耳
    ear_f = [(cx - 44, cy - ry + 12), (cx - 40, cy - ry - 14), (cx - 22, cy - ry + 2)]
    s += shape(smooth_closed(ear_f), PIG)
    # 鼻子（朝左，朝向比比）
    sn = smooth_closed(jitter(ellipse_pts(cx - rx + 2, cy + 2, 12, 15, 10, seed=2), 0.4, 3))
    s += shape(sn, PIG_SN)
    for dy in (-5, 6):
        s += f'<ellipse cx="{f(cx-rx+2)}" cy="{f(cy+2+dy)}" rx="2.6" ry="3.4" fill="{INK}"/>'
    # 眼睛＋腮紅
    s += f'<circle cx="{f(cx-30)}" cy="{f(cy-10)}" r="4.6" fill="{INK}"/><circle cx="{f(cx-31.5)}" cy="{f(cy-11.8)}" r="1.5" fill="#FFFFFF"/>'
    s += f'<ellipse cx="{f(cx-22)}" cy="{f(cy+8)}" rx="9" ry="6" fill="#F58C9E" opacity="0.7"/>'
    # 投幣孔
    slot = f"M {P((cx+4, cy-ry+3))} C {P((cx+10, cy-ry+0.5))} {P((cx+18, cy-ry+0.5))} {P((cx+24, cy-ry+3.5))}"
    s += f'<path d="{slot}" stroke="{INK}" stroke-width="7" stroke-linecap="round" fill="none"/>'
    return squash_g(s, (cx, PIG_BOT), 1 / sq ** 0.5 if sq != 1 else 1, sq)


SLOT = (PIG_C[0] + 14, PIG_C[1] - 47)


def scene_piggy(poses):
    # 標籤、身體來源、幾何、金幣(y, spin)、存錢筒擠壓、閃光等級、「叮」
    plan = [
        ("金幣冒出、抬頭看", 0, dict(lag=0.10, rot=1.5), (70, 1.0), 1.0, 0, False),
        ("金幣往下掉（翻面）", 0, dict(lag=0.07, rot=2.5), (150, 0.35), 1.0, 0, False),
        ("金幣經過臉旁", 0, dict(lag=0.02, rot=3.0), (240, -0.8), 1.0, 0, False),
        ("金幣對準投幣孔", 0, dict(lag=-0.03, rot=3.5, h=0.99), (322, 0.2), 1.0, 0, False),
        ("投進去！存錢筒一沉", 0, dict(lag=-0.04, rot=3.0, h=0.98, w=1.01), (SLOT[1] - 4, 0.0), 0.93, 0, False),
        ("「叮」閃光", 0, dict(rot=1.5), None, 1.04, 2, True),
        ("開心蹲（瞇眼笑）", 2, dict(), None, 1.0, 2, True),
        ("彈起來", 0, dict(bottom=-9, h=1.03, w=0.97, lag=0.06), None, 1.0, 1, False),
        ("落地（瞇眼笑）", 2, dict(w=1.015), None, 1.0, 1, False),
        ("回彈、摸摸小豬", 0, dict(h=1.015, w=0.99, rot=1.0), None, 1.0, 0, False),
        ("微晃", 0, dict(rot=2.0, lag=0.03), None, 1.0, 0, False),
        ("抬頭等下一枚", 0, dict(lag=0.08, rot=1.0), None, 1.0, 0, False),
    ]
    frames = []
    for i, (lab, src, gk, coin, sq, sp, ding) in enumerate(plan):
        g = base_geom(poses, src, **gk)
        mid, front = "", ""
        if coin:
            y, spin = coin
            x = SLOT[0] + 4 * math.sin(i * 1.3)
            if i == 4:   # 半枚已經進孔：只畫孔上方那一截（存錢筒在上層蓋住下半）
                mid += coin_svg((SLOT[0], y), 16, 0.18)
            else:
                mid += coin_svg((x, y), 16, spin, deg=8 * math.sin(i))
                if i in (1, 2, 3):
                    mid += f'<g opacity="0.5">{brush([(x, y - 22), (x, y - 40)], 3.6, 2.4)}{brush([(x - 9, y - 20), (x - 9, y - 32)], 3, 2)}{brush([(x + 9, y - 20), (x + 9, y - 32)], 3, 2)}</g>'
        front += piggy_svg(sq, wig={9: -1.5, 10: 1.5}.get(i, 0.0))
        # 小肉掌貼在存錢筒左上（比比摸著小豬），不畫手臂
        pawc = (350 + (2 if i == 9 else 0), 392 + (2 if src == 2 else 0) + (3 if i == 9 else 0))
        front += paw_svg(pawc, -100, r=12, squash=0.85, seed=i + 300)
        if sp:
            k = 1.0 if sp == 2 else 0.6
            front += sparkle((SLOT[0] + 4, SLOT[1] - 22), 15 * k) + sparkle((SLOT[0] + 40, SLOT[1] - 6), 10 * k) + \
                sparkle((SLOT[0] - 26, SLOT[1] - 14), 8 * k)
        text = None
        if ding:
            text = ("叮！", (SLOT[0] + 44, SLOT[1] - 48), -8 if i == 5 else 4, 34 if i == 5 else 30)
        frames.append({"g": g, "label": lab, "mid": mid, "front": front, "texts": [text] if text else []})
    return frames


# ================================================================== 情境 2：按計算機
CALC_C = (300, 420)


def calc_svg(cx, cy, deg, pressed=None):
    w, h = 104, 126
    s = ""
    # 機身（後層厚度＋正面）
    back = smooth_closed(rot_pts(jitter(rrect_pts(cx + 4, cy + 5, w, h, 18), 0.5, 1), (cx, cy), deg))
    s += shape(back, CALC_DK)
    face = smooth_closed(rot_pts(jitter(rrect_pts(cx, cy, w, h, 18), 0.5, 2), (cx, cy), deg))
    s += shape(face, CALC)
    s += f'<path d="{smooth_closed(rot_pts(rrect_pts(cx + 3, cy + 6, w - 22, h - 28, 12), (cx, cy), deg))}" fill="#FFFFFF" opacity="0.18"/>'
    # 螢幕
    scr = smooth_closed(rot_pts(jitter(rrect_pts(cx, cy - 36, w - 24, 34, 8), 0.4, 3), (cx, cy), deg))
    s += shape(scr, SCREEN, lw=LW2 * 1.2)
    # 按鍵 3 列 × 3 欄，右下角那顆是橘色「＝」
    for r in range(3):
        for c in range(3):
            kx, ky = cx - 28 + c * 28, cy + 6 + r * 23
            on = pressed == (r, c)
            col = "#FFB86B" if (r, c) == (2, 2) else "#FFF8EE"
            if on:
                col = "#F2D7B8" if (r, c) != (2, 2) else "#F09A45"
            kp = rot_pts(jitter(rrect_pts(kx, ky + (2 if on else 0), 21, 16 - (2 if on else 0), 6, 1, 2), 0.35, 10 + r * 3 + c),
                         (cx, cy), deg)
            if not on:
                kps = rot_pts(rrect_pts(kx, ky + 3, 21, 16, 6, 1, 2), (cx, cy), deg)
                s += f'<path d="{smooth_closed(kps)}" fill="{CALC_DK}"/>'
            s += shape(smooth_closed(kp), col, lw=LW2)
    s += shine((cx - 8, cy + 8), 58, deg=-150, w=3.4)
    return s


def scene_calc(poses):
    # 標籤、身體幾何、螢幕字、按下的鍵、肉掌在哪一鍵(或 None＝懸著)、按下去了沒、表情
    K = {"1": (0, 0), "2": (0, 1), "3": (0, 2), "4": (1, 0), "5": (1, 1), "6": (1, 2), "7": (2, 0), "8": (2, 1), "=": (2, 2)}
    plan = [
        ("看著計算機", dict(lag=-0.02), "0", None, "1", False, None),
        ("按 1", dict(lag=-0.04, h=0.995), "1", "1", "1", True, None),
        ("移到 2", dict(lag=-0.03), "1", None, "2", False, None),
        ("按 2", dict(lag=-0.05, h=0.99), "12", "2", "2", True, None),
        ("按 3", dict(lag=-0.05, h=0.99), "123", "3", "3", True, None),
        ("點頭（往下）", dict(lag=-0.10, h=0.975, w=1.01), "123", None, "3", False, "happy"),
        ("點頭（回來）", dict(lag=0.02, h=1.005), "123", None, "4", False, None),
        ("按 4", dict(lag=-0.05, h=0.99), "4", "4", "4", True, None),
        ("按 5", dict(lag=-0.05, h=0.99), "45", "5", "5", True, None),
        ("按 6", dict(lag=-0.05, h=0.99), "456", "6", "6", True, None),
        ("點頭（往下）", dict(lag=-0.10, h=0.975, w=1.01), "456", None, "6", False, "happy"),
        ("點頭（回來）", dict(lag=0.0, h=1.0), "0", None, "1", False, None),
    ]
    frames = []
    for i, (lab, gk, txt, pk, at, down, face) in enumerate(plan):
        g = base_geom(poses, 0, **gk)
        bob = 3.0 * math.sin(2 * math.pi * i / 12)
        cx, cy = CALC_C[0], CALC_C[1] + bob
        deg = -6 + 1.2 * math.sin(2 * math.pi * i / 12 + 1)
        front = ""
        if face:
            front += eyes_svg(poses, g, face)
        front += calc_svg(cx, cy, deg, K[pk] if pk else None)
        r, c = K[at]
        kx, ky = cx - 28 + c * 28, cy + 6 + r * 23
        kp = rot_pts([(kx - 4, ky - (2 if down else 15))], (cx, cy), deg)[0]
        front += paw_svg(kp, -95, r=12.5, squash=0.82, seed=i + 500)
        if down:
            front += motion_lines((kp[0] + 4, kp[1] + 4), 30, spread=34, r0=14, length=9, n=2, w=3.8)
        # 螢幕數字（只出現抽象數字，靠右）
        scx, scy = rot_pts([(cx + 22 - 6 * len(txt), cy - 36)], (cx, cy), deg)[0]
        frames.append({"g": g, "label": lab, "front": front, "texts": [(txt, (scx, scy + 1), deg, 27)],
                       "screen_text": txt})
    return frames


# ================================================================== 情境 3：複利長大
STACK_X, TREE_X = 58, 452


def leaf_svg(base, deg, L, wd, seed=0):
    d = dirv(deg); n = (-d[1], d[0])
    tip = add(base, d, L)
    c1 = add(add(base, d, L * 0.25), n, wd); c2 = add(add(base, d, L * 0.8), n, wd * 0.7)
    c3 = add(add(base, d, L * 0.8), n, -wd * 0.7); c4 = add(add(base, d, L * 0.25), n, -wd)
    pth = f"M {P(base)} C {P(c1)} {P(c2)} {P(tip)} C {P(c3)} {P(c4)} {P(base)} Z"
    s = shape(pth, LEAF, lw=LW * 0.85)
    s += f'<path d="M {P(add(base, d, L*0.12))} Q {P(add(add(base, d, L*0.5), n, wd*0.12))} {P(add(base, d, L*0.78))}" stroke="{LEAF_DK}" stroke-width="2.6" fill="none" stroke-linecap="round"/>'
    return s


def tree_svg(t, sway=0.0):
    """t：0＝剛冒芽、1＝小樹。莖／樹幹長高、葉片變多，最後長出毛茸茸的圓樹冠（跟比比的毛邊同一種扇貝）。"""
    bx, by = TREE_X, 480.0
    s = ""
    # 土堆
    mound = (f"M {P((bx-30, by+1))} C {P((bx-22, by-12))} {P((bx+22, by-12))} {P((bx+30, by+1))} Z")
    s += shape(mound, "#C9A27E", lw=LW * 0.85)
    H = 30 + 185 * ease(min(t, 1.0))
    top = (bx + sway, by - H)
    if t < 0.55:   # 綠色嫩莖
        wst = 4.5 + 4 * t
        stem = bez((bx, by - 6), (bx - 2, by - H * 0.4), (bx + sway * 0.6 + 3, by - H * 0.7), top, 16)
        s += brush(stem, wst + LW * 1.6, wst + LW * 1.2)
        s += brush(stem, wst, wst * 0.8, LEAF_DK)
        nl = 2 if t < 0.2 else (3 if t < 0.4 else 4)
        Ls = 26 + 36 * t
        s += leaf_svg(top, 145 + sway, Ls, Ls * 0.42) + leaf_svg(top, 35 + sway, Ls, Ls * 0.42)
        if nl >= 3:
            p = bez((bx, by - 6), (bx - 2, by - H * 0.4), (bx + sway * 0.6 + 3, by - H * 0.7), top, 16)[8]
            s += leaf_svg(p, 160, Ls * 0.8, Ls * 0.34)
        if nl >= 4:
            p = bez((bx, by - 6), (bx - 2, by - H * 0.4), (bx + sway * 0.6 + 3, by - H * 0.7), top, 16)[5]
            s += leaf_svg(p, 20, Ls * 0.75, Ls * 0.32)
    else:          # 樹幹＋圓樹冠
        k = (t - 0.55) / 0.45
        tw = 9 + 6 * k
        trunk = (f"M {P((bx-tw, by-4))} C {P((bx-tw*0.7, by-H*0.4))} {P((top[0]-tw*0.5, by-H*0.7))} {P((top[0]-tw*0.45, top[1]+20))} "
                 f"L {P((top[0]+tw*0.45, top[1]+20))} C {P((top[0]+tw*0.5, by-H*0.7))} {P((bx+tw*0.7, by-H*0.4))} {P((bx+tw, by-4))} Z")
        s += shape(trunk, BARK)
        s += f'<path d="M {P((bx+tw*0.35, by-10))} C {P((bx+tw*0.3, by-H*0.4))} {P((top[0]+tw*0.2, by-H*0.6))} {P((top[0]+tw*0.15, top[1]+30))}" stroke="{BARK_DK}" stroke-width="3" fill="none" stroke-linecap="round" opacity="0.7"/>'
        R = 34 + 22 * k
        cc = (top[0], top[1] - R * 0.35)
        n = 11
        pts = []
        for j in range(n * 2):   # 扇貝毛邊：外凸點與內凹點交替
            a = 2 * math.pi * j / (n * 2) - math.pi / 2
            rr = R * (1.0 if j % 2 == 0 else 0.86)
            pts.append((cc[0] + rr * math.cos(a), cc[1] + rr * 0.9 * math.sin(a)))
        crown = smooth_closed(jitter(pts, 0.8, 21))
        s += shape(crown, LEAF)
        sh = smooth_closed(jitter(ellipse_pts(cc[0] + 4, cc[1] + R * 0.35, R * 0.78, R * 0.42, 10, seed=4), 0.6, 5))
        s += clip(f"cr{int(t*1000)}", crown, f'<path d="{sh}" fill="{LEAF_DK}" opacity="0.55"/>')
        s += f'<g opacity="0.9">{brush(bez((cc[0]-R*0.62, cc[1]-R*0.05), (cc[0]-R*0.58, cc[1]-R*0.45), (cc[0]-R*0.3, cc[1]-R*0.7), (cc[0]-R*0.05, cc[1]-R*0.72), 10), 4, 3, LEAF_LT)}</g>'
        if k > 0.5:   # 結一顆小金果（複利的果實）
            fr_ = (cc[0] + R * 0.38, cc[1] + R * 0.12)
            s += coin_svg(fr_, 8 + 3 * (k - 0.5) * 2, 1.0)
    return s


def scene_growth(poses):
    # 標籤、身體來源、幾何、金幣層數、落下中的金幣 y（None＝沒有）、樹 t、樹擺動、閃光
    plan = [
        ("看著 3 枚金幣、小芽", 0, dict(lag=0.03, rot=-1.5), 3, None, 0.00, 0, 0),
        ("一枚落下", 0, dict(lag=0.06, rot=-2.0), 3, 330, 0.08, 2, 0),
        ("疊上第 4 層、芽長高", 0, dict(lag=0.02, rot=-1.0, h=0.99), 4, None, 0.18, -2, 1),
        ("又一枚落下", 0, dict(lag=0.06, rot=0.5), 4, 316, 0.30, 2, 0),
        ("第 5 層、長出新葉", 0, dict(lag=0.08, rot=1.5), 5, None, 0.42, -1, 1),
        ("再一枚落下、抬頭", 0, dict(lag=0.11, rot=2.5), 5, 300, 0.56, 2, 0),
        ("第 6 層、長成小樹", 0, dict(lag=0.14, rot=3.0, h=1.01), 6, None, 0.72, -2, 1),
        ("樹冠變大", 0, dict(lag=0.16, rot=3.5, h=1.015), 6, None, 0.88, 1, 0),
        ("結出小金果", 0, dict(lag=0.17, rot=3.5, h=1.02), 6, None, 1.00, -1, 2),
        ("開心蹲（瞇眼笑）", 2, dict(), 6, None, 1.00, 1, 2),
        ("彈起來", 0, dict(bottom=-8, h=1.03, w=0.97, lag=0.10), 6, None, 1.00, -1, 1),
        ("站好、閃光一收（接回第 1 格）", 0, dict(lag=0.04, h=0.99, w=1.008), 3, None, 0.0, 0, 3),
    ]
    frames = []
    for i, (lab, src, gk, n, drop, t, sway, sp) in enumerate(plan):
        g = base_geom(poses, src, **gk)
        back = tree_svg(t, sway)
        front = coin_stack_svg(STACK_X, 481, n)
        if drop:
            front += coin_svg((STACK_X + 2, drop), 15, 0.55 + 0.4 * math.sin(i)) + \
                f'<g opacity="0.5">{brush([(STACK_X + 2, drop - 22), (STACK_X + 2, drop - 42)], 3.4, 2.2)}</g>'
        if sp == 1:
            front += sparkle((STACK_X + 40, 481 - 24 - n * 12.5 - 14), 10)
        if sp == 2:
            front += sparkle((TREE_X - 46, 250), 13) + sparkle((TREE_X + 44, 232), 10) + sparkle((STACK_X + 30, 400), 9)
        if sp == 3:   # 第 12 格：換回 3 枚＋小芽的瞬間用一圈小閃光帶過
            front += sparkle((STACK_X, 410), 9) + sparkle((TREE_X, 420), 9)
        frames.append({"g": g, "label": lab, "back": back, "front": front, "texts": []})
    return frames


# ================================================================== 情境 4：喝珍奶
def boba_svg(c, deg, level, pearl_ph, sip_dots, mouth):
    """c：杯底中心。level：茶面高度比例（0～1）。sip_dots：吸管裡珍珠的位置（0＝杯內、1＝嘴）。"""
    cx, by = c
    H, wt, wb = 96, 74, 58
    ty = by - H
    T = lambda pts: rot_pts(pts, c, deg)  # noqa: E731
    cup_pts = T(jitter([(cx - wt / 2, ty), (cx - wt * 0.47, ty + H * 0.35), (cx - wb * 0.52, by - 14), (cx - wb / 2 + 4, by),
                        (cx, by + 1.5), (cx + wb / 2 - 4, by), (cx + wb * 0.52, by - 14), (cx + wt * 0.47, ty + H * 0.35),
                        (cx + wt / 2, ty)], 0.4, 3))
    cup = smooth_open(cup_pts) + "Z"
    # 吸管：杯中 → 嘴
    s_in = T([(cx + 6, by - 18)])[0]
    s_lid = T([(cx + 2, ty - 4)])[0]
    straw_pts = bez(s_in, add(s_lid, (0, 20)), add(s_lid, (-6, -18)), mouth, 24)
    straw_d = smooth_open(straw_pts)
    s = ""
    s += f'<path d="{straw_d}" stroke="{INK}" stroke-width="{f(13 + LW*1.3)}" fill="none" stroke-linecap="round"/>'
    s += f'<path d="{straw_d}" stroke="{STRAW}" stroke-width="13" fill="none" stroke-linecap="round"/>'
    s += f'<path d="{straw_d}" stroke="#FFFFFF" stroke-width="3" fill="none" stroke-linecap="round" opacity="0.55" transform="translate(-3,-1)"/>'
    for u in sip_dots:
        p = straw_pts[min(int(u * 23), 23)]
        s += f'<circle cx="{f(p[0])}" cy="{f(p[1])}" r="4.6" fill="{PEARL}"/>'
    # 奶茶（裁在杯子裡）
    ly = by - H * level
    tea = f"M {P((cx-60, ly+1.5))} C {P((cx-20, ly-2))} {P((cx+20, ly+3))} {P((cx+60, ly))} L {P((cx+60, by+20))} L {P((cx-60, by+20))} Z"
    tea = f'<path d="{tea}" fill="{TEA}" transform="rotate({deg:.2f},{f(cx)},{f(by)})"/>'
    tea += f'<path d="M {P((cx-60, by-36))} L {P((cx+60, by-36))} L {P((cx+60, by+20))} L {P((cx-60, by+20))} Z" fill="{TEA_DK}" opacity="0.35" transform="rotate({deg:.2f},{f(cx)},{f(by)})"/>'
    rng = np.random.default_rng(4)
    for k in range(13):
        px = cx + rng.uniform(-22, 22) + 1.5 * math.sin(pearl_ph + k)
        py = by - 9 - rng.uniform(0, 26) + 1.2 * math.cos(pearl_ph * 1.3 + k)
        q = T([(px, py)])[0]
        tea += f'<circle cx="{f(q[0])}" cy="{f(q[1])}" r="6.2" fill="{PEARL}"/><circle cx="{f(q[0]-2)}" cy="{f(q[1]-2.2)}" r="1.6" fill="#FFFFFF" opacity="0.6"/>'
    s += clip(f"cup{int(level*1000)}{int(pearl_ph*100)}", cup, tea)
    # 透明杯身＋亮光
    s += f'<path d="{cup}" fill="#FFFFFF" opacity="0.22"/>'
    s += f'<path d="{cup}" fill="none" stroke="{INK}" stroke-width="{f(LW)}" stroke-linejoin="round"/>'
    hl = T([(cx - wt * 0.33, ty + 14), (cx - wt * 0.31, ty + 40), (cx - wb * 0.35, by - 22)])
    s += f'<g opacity="0.8">{brush(bez(hl[0], hl[1], hl[1], hl[2], 10), 4.2, 3, "#FFFFFF")}</g>'
    # 封口杯蓋（上緣一條圈）
    lid = smooth_closed(T(jitter(rrect_pts(cx, ty - 1, wt + 10, 13, 6, 2, 2), 0.35, 6)))
    s += shape(lid, "#FFFFFF")
    # 吸管露在蓋子上方那段要壓在蓋子前面
    top_pts = [p for p in straw_pts if p[1] < ty - 6] or straw_pts[-3:]
    td = smooth_open(top_pts)
    s += f'<path d="{td}" stroke="{INK}" stroke-width="{f(13 + LW*1.3)}" fill="none" stroke-linecap="round"/>'
    s += f'<path d="{td}" stroke="{STRAW}" stroke-width="13" fill="none" stroke-linecap="round"/>'
    for u in sip_dots:
        p = straw_pts[min(int(u * 23), 23)]
        if p[1] < ty - 6:
            s += f'<circle cx="{f(p[0])}" cy="{f(p[1])}" r="4.6" fill="{PEARL}"/>'
    return s


def scene_boba(poses):
    # 標籤、幾何、杯底中心、杯傾角、吸管頭到嘴的距離（0＝含住）、茶面、吸管裡珍珠、表情、鼓臉
    plan = [
        ("看著珍奶", dict(lag=-0.02), (322, 480), 4, 26, 0.80, [], None, False),
        ("杯子湊近", dict(lag=-0.03, rot=1.0), (310, 474), 2, 12, 0.80, [], None, False),
        ("含住吸管", dict(lag=-0.04, rot=1.5, h=0.995), (300, 470), 0, 0, 0.80, [], None, False),
        ("吸！臉頰鼓起", dict(lag=-0.05, rot=1.5, w=1.035, h=0.985), (300, 470), 0, 0, 0.77, [0.25], "blink", True),
        ("珍珠往上跑", dict(lag=-0.05, rot=1.5, w=1.04, h=0.98), (300, 470), 0, 0, 0.74, [0.55, 0.15], "blink", True),
        ("吸到嘴裡", dict(lag=-0.04, rot=1.5, w=1.03, h=0.985), (300, 470), 0, 0, 0.71, [0.88, 0.45], "happy", True),
        ("嚼嚼（臉頰一鼓）", dict(lag=-0.03, rot=1.0, w=1.045, h=0.98), (300, 470), 0, 0, 0.69, [0.7], "happy", True),
        ("嚼嚼（臉頰一收）", dict(lag=-0.02, rot=1.0, w=1.015, h=0.99), (300, 470), 0, 0, 0.68, [0.97], "happy", False),
        ("滿足瞇眼", dict(lag=0.03, rot=0.5, h=1.0), (302, 471), 0, 3, 0.68, [], "happy", False),
        ("滿足晃一下", dict(lag=0.04, rot=-1.5, h=1.005), (306, 473), 2, 10, 0.68, [], "happy", False),
        ("杯子放回", dict(lag=0.02, rot=0.0), (314, 477), 3, 18, 0.72, [], "half", False),
        ("張眼回待機", dict(lag=-0.01, h=0.995), (320, 479), 4, 24, 0.78, [], None, False),
    ]
    frames = []
    for i, (lab, gk, base, deg, gap, level, dots, face, puff) in enumerate(plan):
        g = base_geom(poses, 0, **gk)
        m = fwd(poses, g, *MOUTH0)
        mouth = (m[0] + gap * 0.9, m[1] + 4 + gap * 0.5)
        front = ""
        if face:
            front += eyes_svg(poses, g, face)
        if puff:
            front += puff_svg(poses, g)
        front += boba_svg(base, deg, level, i * 0.7, dots, mouth)
        # 一隻小肉掌扶著杯子左下（貼在身體前方）
        front += paw_svg((base[0] - 36, base[1] - 34), 10, r=12.5, squash=0.85, seed=i + 700)
        if i == 8:
            front += sparkle((m[0] - 70, m[1] - 70), 10) + sparkle((m[0] + 82, m[1] - 64), 8)
        if i == 9:
            front += sparkle((m[0] - 72, m[1] - 74), 7) + sparkle((m[0] + 84, m[1] - 60), 11)
        frames.append({"g": g, "label": lab, "front": front, "texts": []})
    return frames


# ================================================================== 情境 5：翻日曆
CAL_C = (248, 126)
CAL_W, CAL_H = 150, 132


def page_face(x0, y0, w, h, page, opacity=1.0):
    """一頁日曆：紅色頁首＋格子（點點代表日期，不寫數字），圈起來那一天有一枚小金幣（配息日）。"""
    s = ""
    d = smooth_closed(jitter(rrect_pts(x0 + w / 2, y0 + h / 2, w, h, 12, 2, 3), 0.4, 50 + page))
    s += shape(d, "#FFFFFF")
    hdr = f"M {P((x0, y0+28))} L {P((x0+w, y0+28))} L {P((x0+w, y0-6))} L {P((x0, y0-6))} Z"
    s += clip(f"pg{page}{int(y0)}{int(h)}", d, f'<path d="{hdr}" fill="{CAL_RED}"/>'
              f'<path d="M {P((x0, y0+28))} L {P((x0+w, y0+28))}" stroke="{INK}" stroke-width="{f(LW2)}"/>')
    s += f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{f(LW)}" stroke-linejoin="round"/>'
    if h > 60:
        mark = [(1, 2), (2, 0), (0, 3), (2, 2)][page % 4]
        for r in range(3):
            for c in range(4):
                px, py = x0 + 24 + c * (w - 48) / 3, y0 + 50 + r * (h - 66) / 2.4
                if (r, c) == mark:
                    ring = smooth_closed(jitter(ellipse_pts(px, py, 15, 13, 9, seed=page), 0.7, page + 9))
                    s += f'<path d="{ring}" fill="none" stroke="{CAL_RED}" stroke-width="3.6" stroke-linecap="round"/>'
                    s += coin_svg((px, py), 8.5, 1.0)
                else:
                    s += f'<circle cx="{f(px)}" cy="{f(py)}" r="3.4" fill="#C9B9AA"/>'
    return s if opacity >= 1 else f'<g opacity="{opacity}">{s}</g>'


def calendar_svg(c, page, phase, deg):
    """phase：0＝平放、1＝這頁往上掀一半、2＝掀過頭頂（背面朝外）。"""
    cx, cy = c
    x0, y0 = cx - CAL_W / 2, cy - CAL_H / 2 + 8
    s = ""
    # 底板＋頁疊厚度
    for k in (2, 1):
        bk = smooth_closed(jitter(rrect_pts(cx + 2 * k, cy + 8 + 4 * k, CAL_W, CAL_H, 12, 2, 3), 0.4, 70 + k))
        s += shape(bk, "#F3E6D8" if k == 1 else "#E6D3C0")
    if phase == 0:
        s += page_face(x0, y0, CAL_W, CAL_H, page)
    else:
        s += page_face(x0, y0, CAL_W, CAL_H, page + 1)    # 底下露出下一頁
        if phase == 1:   # 掀起一半：頁面往上收、底緣捲起
            hh = CAL_H * 0.42
            d = (f"M {P((x0, y0-4))} L {P((x0+CAL_W, y0-4))} L {P((x0+CAL_W, y0+hh-8))} "
                 f"C {P((x0+CAL_W*0.75, y0+hh+10))} {P((x0+CAL_W*0.3, y0+hh+12))} {P((x0, y0+hh))} Z")
            s += shape(d, "#FBF3EA")
            s += f'<path d="M {P((x0+8, y0+hh-4))} C {P((x0+CAL_W*0.3, y0+hh+4))} {P((x0+CAL_W*0.7, y0+hh+2))} {P((x0+CAL_W-8, y0+hh-12))}" stroke="{FUR_SH}" stroke-width="5" fill="none" stroke-linecap="round"/>'
        else:            # 翻過頭頂：背面朝外、往上捲走
            hh = CAL_H * 0.26
            d = (f"M {P((x0+6, y0-2))} L {P((x0+CAL_W-6, y0-2))} C {P((x0+CAL_W-2, y0-hh*0.6))} {P((x0+CAL_W-14, y0-hh))} {P((x0+CAL_W-24, y0-hh-2))} "
                 f"L {P((x0+24, y0-hh-2))} C {P((x0+14, y0-hh))} {P((x0+2, y0-hh*0.6))} {P((x0+6, y0-2))} Z")
            s += shape(d, "#F6EADC")
            s += motion_lines((cx + CAL_W / 2 - 6, y0 - hh * 0.6), 30, spread=34, r0=8, length=9, n=2, w=3.8) + \
                motion_lines((cx - CAL_W / 2 + 6, y0 - hh * 0.6), 150, spread=34, r0=8, length=9, n=2, w=3.8)
    # 兩個環扣
    for rx_ in (cx - 38, cx + 38):
        ring = f"M {P((rx_-6, y0+6))} C {P((rx_-8, y0-14))} {P((rx_+8, y0-14))} {P((rx_+6, y0+6))}"
        s += f'<path d="{ring}" stroke="{INK}" stroke-width="{f(LW*1.7)}" fill="none" stroke-linecap="round"/>'
        s += f'<path d="{ring}" stroke="#D9D4CF" stroke-width="{f(LW*0.7)}" fill="none" stroke-linecap="round"/>'
    return f'<g transform="rotate({deg:.2f},{f(cx)},{f(cy)})">{s}</g>'


def scene_calendar(poses):
    # 每 3 格翻一頁：平放 → 掀一半 → 翻過頭；4 頁循環，第 12 格翻完剛好回到第 1 格那一頁
    eye = {6: "half", 7: "blink", 8: "half"}
    frames = []
    labs = ["看著日曆", "這頁掀起來", "翻過去", "新的一頁", "再掀", "翻過去", "新的一頁（眨眼）",
            "眼睛閉上", "張開一半", "新的一頁", "最後一掀", "翻過去（接回第 1 格）"]
    for i in range(12):
        page, phase = divmod(i, 3)
        gk = dict(lag=0.13 + 0.03 * math.sin(2 * math.pi * i / 12), rot=1.8 * math.sin(2 * math.pi * i / 12 + 0.6))
        if phase == 2:
            gk["h"] = 1.01
        g = base_geom(poses, 0, **gk)
        ph = 2 * math.pi * i / 12
        dy = -5.0 * math.sin(ph)
        deg = 3.0 * math.sin(ph + math.pi / 2)
        c = (CAL_C[0], CAL_C[1] + dy)
        front = ""
        if i in eye:
            front += eyes_svg(poses, g, eye[i])
        front += float_marks((c[0], c[1] + CAL_H / 2 + 14), CAL_W, ph)
        front += calendar_svg(c, page, phase, deg)
        frames.append({"g": g, "label": labs[i], "front": front, "texts": []})
    return frames


# ================================================================== 合成
def render(poses, fr, font):
    body = pose_tween.warp_body(poses[fr["g"]["src"]], fr["g"], SIZE).convert("RGBA")
    canvas = Image.new("RGBA", body.size, (0, 0, 0, 0))
    if fr.get("back"):
        canvas = Image.alpha_composite(canvas, raster(fr["back"]))
    canvas = Image.alpha_composite(canvas, body)
    for key in ("mid", "front"):
        if fr.get(key):
            canvas = Image.alpha_composite(canvas, raster(fr[key]))
    for t in fr.get("texts", []):
        txt, c, deg, px = t
        canvas = Image.alpha_composite(canvas, text_layer(txt, c, deg, px, font))
    return canvas.resize((SIZE, SIZE), Image.LANCZOS)


SCENES = {
    "piggy": ("存錢筒（金幣投進去、叮）", scene_piggy, [140, 70, 60, 60, 70, 110, 80, 70, 80, 90, 90, 110]),
    "calc": ("按計算機（螢幕數字跳、點頭）", scene_calc, [130, 90, 70, 90, 90, 110, 90, 90, 90, 90, 110, 110]),
    "growth": ("複利長大（金幣疊高、小芽長成樹）", scene_growth, [160, 80, 110, 80, 110, 80, 110, 110, 150, 80, 80, 140]),
    "boba": ("喝珍奶（含吸管、鼓臉頰、滿足瞇眼）", scene_boba, [150, 90, 90, 90, 80, 90, 90, 90, 200, 120, 90, 110]),
    "calendar": ("翻日曆（一頁頁往上翻、眨眼看）", scene_calendar, [150, 80, 70, 150, 80, 70, 120, 70, 70, 150, 80, 70]),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="site/brand/src/support_anim_1009.gif")
    ap.add_argument("--out", required=True)
    ap.add_argument("--repo-out", default="docs/anim")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    poses = pose_tween.load_poses(Path(a.src))
    out = Path(a.out)
    idx_path = out / "index_b.json"
    index = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else {}
    only = [x for x in a.only.split(",") if x]
    font = BA.HUNINN
    for key, (name, fn, durs) in SCENES.items():
        if only and key not in only:
            continue
        frs = fn(poses)
        assert len(frs) == 12 and len(durs) == 12, key
        imgs = [render(poses, fr, font) for fr in frs]
        fd = out / key / "frames"
        fd.mkdir(parents=True, exist_ok=True)
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
        arr = [np.asarray(i).astype(int) for i in imgs]
        diffs = [int(np.abs(arr[k] - arr[(k + 1) % 12]).sum() // 1000) for k in range(12)]
        index[key] = {"name": name, "size": [SIZE, SIZE], "frames": paths, "durations_ms": durs,
                      "labels": [fr["label"] for fr in frs], "adjacent_diff_k": diffs,
                      "scene": {"scale": BA.SCALE, "center_x": BA.CX, "ground_y": BA.GROUND},
                      "webp": str((rd / "anim.webp").resolve()), "sheet": str((rd / "sheet_12.png").resolve())}
        print(key, "min diff", min(diffs), "→", rd)
    idx_path.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
