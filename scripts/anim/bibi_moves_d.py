"""動畫設計單位：吉祥物「比比」D 批 8 組「跟影片畫面互動」的動作，每組 12 格、512×512、透明。

為什麼有這支
------------
Andy 2026-10-10：「幫我在影片中新增多點 GIF 圖，表情越豐富越好，情境越多越好，可以多點物件，
動作可以跟影片有更多互動，讓觀眾有是比比在介紹的感覺」。
這批會疊在網站錄影上，剪輯要能把比比放到錄影中某個按鈕／圖表旁邊，所以每格都輸出「互動點」座標
（腳踩的位置、指示棒尖端、光圈、手機螢幕四角、布幕開口…），寫進 storyboard.md 與 index_d.json。

A 批在 `bibi_actions.py`、B 批在 `bibi_scenes_b.py`、C 批（表情）另一位在做；這支只 import 它們的函式，**不改它們**。

規格（docs/anim/prompt_kit/01_總控Prompt.md）
--------------------------------------------
- 比比本體＝原圖 `site/brand/src/support_anim_1009.gif` 的像素網格變形（raster_first），不重畫角色。
  跳躍用原圖第 1～7 張（蹲、深蹲瞇眼、起跳、上升、最高、落地壓扁、回正）；眼睛方向／認真臉只改眼睛與嘴巴那兩小塊像素。
- 道具（指示棒、聚光燈、滑板、手機、布幕、漣漪、灰塵）用 SVG 三次 Bézier（Catmull-Rom 轉 C）畫，
  描邊色與粗細跟原圖一致（#1A0907、7.5px×0.75），4 倍繪製再 LANCZOS 縮回。
- Andy 退件教訓：不准從身體伸出長手臂 → 道具一律懸空或在身前，手只露小肉掌。
- 場景座標跟 A／B 批相同：身體縮 0.75、中心 x=248、腳底 y=482（探頭那組例外：整隻斜著從畫面角落冒出來）。

用法
----
    python scripts/anim/bibi_moves_d.py --out <scratchpad>/bibi --repo-out docs/anim [--only tap,pointer_r]
輸出：<out>/<名>/frames/frame_01.png…、<repo-out>/bibi_<組>/sheet_12[_r|_l].png、anim[_r|_l].webp、storyboard.md；
<out>/index_d.json（每格互動點）。
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
import bibi_scenes_b as SB  # noqa: E402
import pose_tween  # noqa: E402

from bibi_actions import (INK, FUR_SH, SPARK, SIZE, OUT_W, f, P, add, dirv, bez, brush,  # noqa: E402
                          sparkle, motion_lines, paw_svg, base_geom, nat_geom, fwd, raster, sheet12,
                          exmark, arcs, ease)
from bibi_scenes_b import (smooth_closed, smooth_open, jitter, rot_pts, rrect_pts, ellipse_pts, shape,  # noqa: E402
                           clip, shine, eyes_svg, coin_svg)

LW = OUT_W
LW2 = OUT_W * 0.62
K = 0.5523
WOOD, WOOD_DK, WOOD_LT, GRIP = "#E2B27A", "#B9824E", "#F6D9A8", "#8C5A3A"
RUBBER = "#E8504A"
LIGHT, LIGHT_DK = "#FFE08A", "#F7C948"
LAMP, LAMP_DK = "#6B6580", "#4E4960"
DECK, DECK_LT, DECK_DK = "#7FCBEA", "#BDE6F6", "#4FA9CF"
WHEEL, WHEEL_DK = "#FFE08A", "#E09A1E"
CASE, CASE_DK = "#A9D7EA", "#82BFD9"
VELVET, VELVET_DK, VELVET_LT = "#E8504A", "#B8362F", "#F47C6B"
GOLD, GOLD_DK = "#F9C23C", "#E09A1E"
DUST = "#F6E0CB"


# ================================================================== 臉：只改眼睛／嘴巴那兩小塊像素
_FACE = {}
EYE_L, EYE_R = (192, 264), (309, 261)
MOUTH = (251, 291)


def _fur_ring(arr, c, r0, r1):
    yy, xx = np.mgrid[0:arr.shape[0], 0:arr.shape[1]]
    d2 = (xx - c[0]) ** 2 + (yy - c[1]) ** 2
    ring = (d2 >= r0 ** 2) & (d2 <= r1 ** 2) & (arr[..., :3].mean(2) > 200) & (arr[..., 3] > 200)
    return "#%02X%02X%02X" % tuple(int(v) for v in np.median(arr[ring][:, :3], 0))


def face_pose(poses, look=(0.0, 0.0), scale=1.0, hl=False, serious=False):
    """原圖第 0 張：眼睛改看 look 方向（原圖 px 偏移）；serious＝加兩道往內壓的眉毛＋把張嘴換成抿著的小嘴。"""
    key = (round(look[0], 1), round(look[1], 1), round(scale, 2), hl, serious)
    if key in _FACE:
        return _FACE[key]
    base = poses[0]
    arr = np.asarray(base["body"]).astype(float)
    svg = ""
    for e in (EYE_L, EYE_R):
        svg += f'<circle cx="{f(e[0])}" cy="{f(e[1])}" r="15.5" fill="{_fur_ring(arr, e, 17, 23)}"/>'
    if serious:
        col = _fur_ring(arr, MOUTH, 36, 42)
        svg += f'<ellipse cx="{f(MOUTH[0])}" cy="{f(MOUTH[1]+1)}" rx="35" ry="33" fill="{col}"/>'
        # 小鼻頭＋抿著的嘴（微微往下彎）
        svg += brush(bez((240, 276), (245, 271), (257, 271), (262, 276), 10), 6.5, 6.5)
        svg += brush(bez((232, 298), (244, 294), (258, 294), (270, 299), 12), 7.5, 7.5)
        # 眉毛：內側低、外側高（認真）
        svg += brush(bez((170, 232), (180, 230), (194, 233), (207, 240), 12), 7.5, 6.0)
        svg += brush(bez((294, 238), (306, 230), (318, 227), (330, 228), 12), 6.0, 7.5)
    for e in (EYE_L, EYE_R):
        c = (e[0] + look[0], e[1] + look[1])
        svg += f'<ellipse cx="{f(c[0])}" cy="{f(c[1])}" rx="{f(12*scale)}" ry="{f(13.5*scale)}" fill="{INK}"/>'
        if hl:
            svg += (f'<circle cx="{f(c[0]+4*scale)}" cy="{f(c[1]-5*scale)}" r="{f(4.2*scale)}" fill="#FFFFFF"/>'
                    f'<circle cx="{f(c[0]-4*scale)}" cy="{f(c[1]+4.5*scale)}" r="{f(2.0*scale)}" fill="#FFFFFF"/>')
    ov = raster(svg).resize((SIZE, SIZE), Image.LANCZOS)
    body = base["body"].copy()
    a = body.getchannel("A")
    body = Image.alpha_composite(body, ov)
    body.putalpha(a)
    out = dict(base); out["body"] = body
    _FACE[key] = out
    return out


# ================================================================== 共用小道具
def ellipse_d(cx, cy, rx, ry):
    return (f"M {P((cx-rx, cy))} C {P((cx-rx, cy-K*ry))} {P((cx-K*rx, cy-ry))} {P((cx, cy-ry))} "
            f"C {P((cx+K*rx, cy-ry))} {P((cx+rx, cy-K*ry))} {P((cx+rx, cy))} "
            f"C {P((cx+rx, cy+K*ry))} {P((cx+K*rx, cy+ry))} {P((cx, cy+ry))} "
            f"C {P((cx-K*rx, cy+ry))} {P((cx-rx, cy+K*ry))} {P((cx-rx, cy))} Z")


def ring_brush(c, rx, ry, w, color, a0=0, a1=360, n=40, gap=0.0):
    """手繪橢圓環：沿橢圓取點的筆刷（頭尾尖），gap 留一小段缺口像手畫。"""
    pts = []
    for i in range(n):
        a = math.radians(a0 + (a1 - a0 - gap) * i / (n - 1))
        pts.append((c[0] + rx * math.cos(a), c[1] + ry * math.sin(a)))
    return brush(pts, w, w * 0.85, color)


def dust_puff(c, r, seed, op=1.0):
    """落地灰塵：三顆不規則小圓團（米色＋描邊）。"""
    s = ""
    for k, (dx, dy, kr) in enumerate(((-0.9, 0.2, 0.75), (0.0, -0.25, 1.0), (0.95, 0.15, 0.7))):
        cc = (c[0] + dx * r, c[1] + dy * r)
        d = smooth_closed(jitter(ellipse_pts(cc[0], cc[1], r * kr, r * kr * 0.85, 9, seed=seed + k), r * 0.04, seed + k))
        s += shape(d, DUST, lw=LW * 0.8)
    return s if op >= 1 else f'<g opacity="{op:.2f}">{s}</g>'


def float_bits(c, w, phase=0.0):
    """懸空記號：兩顆小閃光＋一道淡弧線（跟 A 批許願牌同一套語彙，尺寸固定不閃）。"""
    out = sparkle((c[0] - w * 0.42, c[1] + 6), 5.5) + sparkle((c[0] + w * 0.4, c[1] + 4), 4.5)
    x, y = c[0], c[1] + 6
    out += f'<g opacity="0.35">{brush(bez((x-14, y), (x-5, y+5), (x+5, y+5), (x+14, y), 10), 3.4, 2.8)}</g>'
    return out


def render(poses, fr):
    body = pose_tween.warp_body(fr.get("pose") or poses[fr["g"]["src"]], fr["g"], SIZE).convert("RGBA")
    canvas = Image.new("RGBA", body.size, (0, 0, 0, 0))
    if fr.get("back"):
        canvas = Image.alpha_composite(canvas, raster(fr["back"]))
    canvas = Image.alpha_composite(canvas, body)
    for key in ("mid", "front"):
        if fr.get(key):
            canvas = Image.alpha_composite(canvas, raster(fr[key]))
    return canvas.resize((SIZE, SIZE), Image.LANCZOS)


def r1(x):
    return round(float(x), 1)


# ================================================================== 1. 跳上去踩按鈕＋漣漪
TAP_C = (248.0, 484.0)   # 漣漪中心＝腳底中心（剪輯把這點對準錄影裡的按鈕中心）


def ripple_svg(rx, ry, op, second=None):
    c = TAP_C
    s = f'<path d="{ellipse_d(c[0], c[1], rx, ry)}" fill="{LIGHT}" opacity="{op*0.45:.2f}"/>'
    s += f'<g opacity="{op:.2f}">{ring_brush(c, rx, ry, 10.0, LIGHT_DK, 200, 560, 48, gap=24)}</g>'
    if second:
        rx2, ry2, op2 = second
        s += f'<g opacity="{op2:.2f}">{ring_brush(c, rx2, ry2, 8.0, "#F2A93B", 10, 370, 40, gap=30)}</g>'
    return s


def scene_tap(poses):
    W0, H0 = 386, 337
    plan = [
        ("站在按鈕上方", lambda: base_geom(poses, 0), None),
        ("下蹲", lambda: nat_geom(poses, 1), None),
        ("蓄力深蹲（瞇眼）", lambda: nat_geom(poses, 2), None),
        ("起跳拉長", lambda: nat_geom(poses, 3, bottom=25.5, w=W0 * .90 / 369, h=H0 * 1.10 / 343, lag=-0.10, rot=-3), None),
        ("上升", lambda: nat_geom(poses, 3), None),
        ("到頂前", lambda: nat_geom(poses, 4, bottom=-9), None),
        ("最高點", lambda: nat_geom(poses, 5), None),
        ("往下落（毛往上飄）", lambda: nat_geom(poses, 4, bottom=18.5, rot=2, lag=0.12), None),
        ("腳碰到按鈕：漣漪冒出", lambda: nat_geom(poses, 4, bottom=58.5, w=W0 * .93 / 361, h=H0 * 1.05 / 338, lag=0.10),
         (62, 11, 1.0, None)),
        ("踩下去壓扁（瞇眼）", lambda: nat_geom(poses, 6), (118, 18, 1.0, (70, 12, 0.9))),
        ("回彈：漣漪擴散", lambda: nat_geom(poses, 7, w=W0 * .97 / 384, h=H0 * 1.04 / 343, lag=-0.06), (168, 23, 0.75, (120, 18, 0.8))),
        ("站穩：漣漪淡出", lambda: base_geom(poses, 0, h=0.995), (205, 26, 0.35, (165, 22, 0.45))),
    ]
    frames = []
    for i, (lab, gfn, rip) in enumerate(plan):
        g = gfn()
        back, front = "", ""
        ip = {"foot": [r1(g["cx"]), r1(g["bottom"])], "contact": rip is not None}
        if rip:
            rx, ry, op, sec = rip
            back += ripple_svg(rx, ry, op, sec)
            ip["ripple"] = {"center": list(TAP_C), "rx": rx, "ry": ry, "opacity": op}
        if i == 9:
            front += motion_lines((TAP_C[0] - 150, TAP_C[1] - 18), 160, spread=26, r0=4, length=14, n=2) + \
                motion_lines((TAP_C[0] + 150, TAP_C[1] - 18), 20, spread=26, r0=4, length=14, n=2)
            front += sparkle((TAP_C[0] - 178, TAP_C[1] - 46), 11) + sparkle((TAP_C[0] + 182, TAP_C[1] - 50), 13)
        if i == 10:
            front += sparkle((TAP_C[0] - 196, TAP_C[1] - 60), 7) + sparkle((TAP_C[0] + 200, TAP_C[1] - 66), 9)
        if i in (3, 4):
            front += motion_lines((g["cx"], g["bottom"] + 6), -90, spread=34, r0=4, length=14, n=3, w=4.6)
        frames.append({"g": g, "label": lab, "back": back, "front": front, "ip": ip})
    return frames


# ================================================================== 2. 懸空指示棒
def stick_svg(base, tip, seed=1):
    """細長木指示棒：手把深色防滑段、木紋、紅色橡皮頭；外框手繪抖動。"""
    u = ((tip[0] - base[0]), (tip[1] - base[1]))
    L = math.hypot(*u); u = (u[0] / L, u[1] / L); n = (-u[1], u[0])
    w0, w1 = 7.6, 4.2   # 半寬
    side_a, side_b = [], []
    for t in (0.0, 0.25, 0.5, 0.75, 1.0):
        w = w0 + (w1 - w0) * t
        p = add(base, u, L * t)
        side_a.append(add(p, n, w)); side_b.append(add(p, n, -w))
    pts = side_a + [add(tip, u, 2.0)] + side_b[::-1] + [add(base, u, -w0 * 0.8)]
    pts = jitter(pts, 0.25, seed)
    d = smooth_closed(pts)
    inner = f'<path d="{d}" fill="{WOOD}"/>'
    # 手把段（0～24%）
    g0, g1 = add(base, u, -10), add(base, u, L * 0.24)
    grip = (f"M {P(add(g0, n, -12))} L {P(add(g0, n, 12))} L {P(add(g1, n, 12))} L {P(add(g1, n, -12))} Z")
    inner += f'<path d="{grip}" fill="{GRIP}"/>'
    inner += brush([add(g1, n, -8), add(g1, n, 8)], 3.0, 3.0)
    for t in (0.07, 0.15):   # 手把上的防滑紋
        q = add(base, u, L * t)
        inner += f'<g opacity="0.55">{brush([add(q, n, -5), add(q, n, 5)], 2.2, 2.2, "#5E3A24")}</g>'
    # 木紋＋亮線
    inner += f'<g opacity="0.65">{brush([add(add(base, u, L*0.32), n, -1.6), add(add(base, u, L*0.62), n, -1.0)], 1.8, 1.4, WOOD_DK)}</g>'
    inner += f'<g opacity="0.9">{brush([add(add(base, u, L*0.30), n, 2.6), add(add(base, u, L*0.86), n, 1.4)], 2.0, 1.4, WOOD_LT)}</g>'
    s = clip(f"stk{seed}{int(base[0])}{int(base[1])}", d, inner)
    s += f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{f(LW*0.85)}" stroke-linejoin="round"/>'
    # 紅色橡皮頭
    cap_c = add(tip, u, -3.0)
    cap = smooth_closed([add(add(cap_c, u, 7.5), n, 0), add(add(cap_c, u, 3), n, 5.6), add(add(cap_c, u, -4), n, 5.2),
                         add(add(cap_c, u, -4), n, -5.2), add(add(cap_c, u, 3), n, -5.6)])
    s += shape(cap, RUBBER, lw=LW * 0.8)
    return s


def scene_pointer(poses, s):
    """s=+1 指向右上、-1 指向左上。棒子沿自己的方向滑出去戳兩下，比比認真臉盯著尖端。"""
    ang = 62 if s > 0 else 118
    u = dirv(ang)
    B0 = (248 + s * 146, 384.0)       # 手把端（休息位置）
    L = 172.0
    # 標籤、滑出距離、棒子垂直漂浮、身體幾何、眼睛看、亮點、效果
    plan = [
        ("盯著尖端（認真臉）", 0, 0.0, dict(lag=0.06), (7, -6), None),
        ("棒子往後收（預備）", -12, 1.0, dict(lag=0.05, rot=-s * 1.0, h=0.99), (6, -5), None),
        ("戳！", 24, 0.0, dict(lag=0.08, rot=s * 2.5), (8, -7), "poke"),
        ("停在那裡", 18, -1.0, dict(lag=0.08, rot=s * 2.0), (8, -7), "hit"),
        ("收回一點", -5, 0.0, dict(lag=0.06, rot=s * 0.5, h=0.995), (7, -6), None),
        ("再戳！", 26, 1.0, dict(lag=0.09, rot=s * 3.0, h=1.01), (8, -8), "poke"),
        ("停住（這裡！）", 20, 0.0, dict(lag=0.09, rot=s * 2.5), (8, -8), "hit2"),
        ("慢慢收回", 6, -1.0, dict(lag=0.07, rot=s * 1.0), (7, -6), None),
        ("轉頭看觀眾", 0, -2.0, dict(lag=0.03), (0, 0), "look"),
        ("點點頭", 1, -2.5, dict(lag=-0.02, h=0.985, w=1.01), (0, 2), "nod"),
        ("再看回尖端", 2, -1.0, dict(lag=0.04), (5, -4), None),
        ("盯著（接回第 1 格）", 1, 1.0, dict(lag=0.05), (6, -5), None),
    ]
    frames = []
    for i, (lab, dist, flo, gk, look, fx) in enumerate(plan):
        g = base_geom(poses, 0, **gk)
        pose = face_pose(poses, look=(s * look[0], look[1]), serious=fx not in ("look", "nod"), hl=fx in ("look", "nod"))
        nperp = (-u[1], u[0])
        bse = add(add(B0, u, dist), nperp, flo)
        tip = add(bse, u, L)
        front = float_bits(add(add(bse, u, L * 0.42), (0, 1), 22), 50)
        front += stick_svg(bse, tip, seed=3)
        if fx == "poke":
            front += motion_lines(add(tip, u, 4), ang, spread=36, r0=10, length=14, n=3, w=5.0)
            front += f'<g opacity="0.5">{brush([add(bse, u, -14), add(bse, u, -40)], 3.6, 2.0)}</g>'
        if fx in ("hit", "hit2"):
            front += sparkle(add(add(tip, u, 16), nperp, s * 10), 11 if fx == "hit" else 14)
            front += sparkle(add(add(tip, u, 6), nperp, -s * 16), 7)
        if fx == "hit2":
            front += exmark(add(fwd(poses, g, 254 + s * 150, 150), (0, -18)), 0.55, s * 12)
        if fx == "nod":
            front += sparkle(fwd(poses, g, 254 - s * 190, 190), 8)
        ip = {"tip": [r1(tip[0]), r1(tip[1])], "handle": [r1(bse[0]), r1(bse[1])], "angle_deg": ang}
        frames.append({"g": g, "pose": pose, "label": lab, "front": front, "ip": ip})
    return frames


# ================================================================== 3. 原地跳步（左右方向）
def scene_hop(poses, s):
    """兩下跳步一個循環；身體往行進方向傾、動作線與灰塵在後方。剪輯水平平移就是「跳著走」。"""
    seq = [
        # 標籤、幾何、看、落地灰塵、空中
        ("落地蹲（第 1 步）", lambda: nat_geom(poses, 1, w=1.02), None, "land", False),
        ("蹬地拉長", lambda: base_geom(poses, 0, h=1.06, w=0.95, bottom=-8, rot=s * 5, lag=-0.05), (7, -2), "puff", False),
        ("騰空上升", lambda: nat_geom(poses, 3, bottom=482 - 34 - 434, rot=s * 6), None, None, True),
        ("最高點", lambda: nat_geom(poses, 5, bottom=482 - 50 - 402.5, rot=s * 4), None, None, True),
        ("往下落", lambda: nat_geom(poses, 4, bottom=482 - 22 - 423.5, rot=s * 3, lag=0.10), None, None, True),
        ("腳尖著地", lambda: base_geom(poses, 0, h=1.04, w=0.97, bottom=-3, rot=s * 2, lag=0.06), (7, 0), None, False),
        ("落地蹲（第 2 步，瞇眼笑）", lambda: nat_geom(poses, 2, w=1.0), None, "land", False),
        ("蹬地拉長（亮眼）", lambda: base_geom(poses, 0, h=1.07, w=0.95, bottom=-9, rot=s * 5.5, lag=-0.06), (8, -4), "puff", False),
        ("騰空上升", lambda: nat_geom(poses, 3, bottom=482 - 38 - 434, rot=s * 7, lag=0.02), None, None, True),
        ("最高點", lambda: nat_geom(poses, 5, bottom=482 - 54 - 402.5, rot=s * 5, lag=0.03), None, None, True),
        ("往下落", lambda: nat_geom(poses, 4, bottom=482 - 24 - 423.5, rot=s * 3.5, lag=0.12), None, None, True),
        ("腳尖著地（接回第 1 格）", lambda: base_geom(poses, 0, h=1.04, w=0.97, bottom=-3, rot=s * 2.5, lag=0.07), (7, 1), None, False),
    ]
    frames = []
    for i, (lab, gfn, look, dust, air) in enumerate(seq):
        g = gfn()
        pose = face_pose(poses, look=(s * look[0], look[1]), hl=i >= 6) if look and g["src"] == 0 else None
        back, front = "", ""
        behind = 248 - s * 150
        if dust == "land":
            back += dust_puff((behind, 474), 15, 20 + i) + dust_puff((248 + s * 152, 478), 9, 40 + i)
        if dust == "puff":
            back += dust_puff((behind - s * 22, 466), 19, 60 + i, op=0.65)
        if air:
            top = fwd(poses, g, 254, 200)
            front += motion_lines((top[0] - s * 150, top[1] + 70), 180 if s > 0 else 0, spread=22, r0=6, length=22, n=3, w=4.8)
            front += f'<g opacity="0.55">{motion_lines((g["cx"] - s * 120, g["bottom"] - 10), 180 + s * 30 if s > 0 else -30, spread=20, r0=4, length=14, n=2, w=4.0)}</g>'
        ip = {"foot": [r1(g["cx"]), r1(g["bottom"])], "airborne": air}
        frames.append({"g": g, "pose": pose, "label": lab, "back": back, "front": front, "ip": ip})
    return frames


# ================================================================== 4. 從畫面角落探頭
def scene_peek(poses, s):
    """s=+1 從右下角探出（裁切邊＝畫布右緣 x=512 與下緣 y=512）、-1 從左下角（x=0 與 y=512）。"""
    rot = -22.0 * s
    up = (math.sin(math.radians(rot)), -math.cos(math.radians(rot)))
    A1 = (512 - 14 if s > 0 else 14, 530.0)    # 完全探出時的腳底錨點（在畫布外）
    plan = [
        # 標籤、探出量 t、眼睛（look,hl）、覆蓋（blink/happy）、效果
        ("耳朵尖冒出來", 0.22, (0, 0), False, None, None),
        ("頭頂冒出一半", 0.62, (0, -3), False, None, "up"),
        ("探出來（過頭一點）", 1.06, (-7, -3), False, None, None),
        ("定住，眼睛往裡看", 0.98, (-9, -2), False, None, None),
        ("眼睛往上看", 1.03, (-7, -8), False, None, "q"),
        ("眨眼", 1.0, (0, 0), False, "blink", None),
        ("看觀眾（亮眼）", 1.0, (0, 0), True, None, None),
        ("開心瞇眼", 1.02, (0, 0), False, "happy", "spark"),
        ("準備縮回", 1.04, (0, 0), True, None, None),
        ("縮回一半", 0.52, (0, 0), False, None, "down"),
        ("只剩耳朵", 0.2, (0, 0), False, None, None),
        ("幾乎看不見（接回第 1 格）", 0.08, (0, 0), False, None, None),
    ]
    dist = 260.0   # t=1 時從起點往「上」移動的距離
    frames = []
    for i, (lab, t, look, hl, ov, fx) in enumerate(plan):
        a = add(A1, up, -dist * (1 - t))
        tilt = [0, 0, 0, 2.0, -3.5, -1.0, 1.5, 3.0, 0, 0, 0, 0][i]   # 歪頭（正＝往畫面內側再歪一點）
        g = base_geom(poses, 0, rot=rot - s * tilt, lag=0.04 if fx == "up" else (-0.04 if fx == "down" else 0.0))
        g["cx"], g["bottom"] = a
        pose = face_pose(poses, look=(s * look[0], look[1]), hl=hl)
        front = ""
        if ov:
            front += eyes_svg(poses, g, ov)
        if fx == "up":
            top = fwd(poses, g, 254, 150)
            front += motion_lines(top, 90 + 22 * s, spread=34, r0=26, length=14, n=3, w=4.8)
        if fx == "down":
            top = fwd(poses, g, 254, 150)
            front += f'<g opacity="0.7">{motion_lines(top, 90 + 22 * s, spread=30, r0=22, length=12, n=2, w=4.2)}</g>'
        if fx == "q":
            top = fwd(poses, g, 254 - s * 150, 120)
            front += BA.qmark(add(top, (-s * 24, -16)), 0.62, -s * 12)
        if fx == "spark":
            top = fwd(poses, g, 254, 130)
            front += sparkle(add(top, (-s * 80, -6)), 12) + sparkle(add(top, (-s * 30, -40)), 8)
        head = fwd(poses, g, 254, 148)
        eyel, eyer = fwd(poses, g, *EYE_L), fwd(poses, g, *EYE_R)
        ip = {"head_top": [r1(head[0]), r1(head[1])], "eye_l": [r1(eyel[0]), r1(eyel[1])],
              "eye_r": [r1(eyer[0]), r1(eyer[1])], "peek_t": t}
        frames.append({"g": g, "pose": pose, "label": lab, "front": front, "ip": ip})
    return frames


# ================================================================== 5. 聚光燈介紹
LAMP_C = (138.0, 86.0)
GROUND_Y = 482.0
SPOT_RX, SPOT_RY = 92.0, 22.0


def lamp_svg(c, aim):
    """舞台小聚光燈：上方 U 形吊架（不轉）、燈筒朝 aim 角度（畫面角，y 往下為正）、前緣發光鏡片。"""
    T = lambda p: add(c, BA.rot2(p, aim))  # noqa: E731
    s = ""
    yoke = f"M {P((c[0]-30, c[1]+2))} C {P((c[0]-32, c[1]-30))} {P((c[0]+32, c[1]-30))} {P((c[0]+30, c[1]+2))}"
    s += f'<path d="{yoke}" stroke="{INK}" stroke-width="{f(LW*2.1)}" fill="none" stroke-linecap="round"/>'
    s += f'<path d="{yoke}" stroke="{LAMP_DK}" stroke-width="{f(LW*0.9)}" fill="none" stroke-linecap="round"/>'
    s += f'<path d="M {P((c[0], c[1]-24))} L {P((c[0], c[1]-34))}" stroke="{INK}" stroke-width="{f(LW*1.2)}" stroke-linecap="round"/>'
    can = smooth_closed(jitter([T((-30, -10)), T((-24, -16)), T((0, -18)), T((26, -22)), T((30, -20)),
                                T((30, 20)), T((26, 22)), T((0, 18)), T((-24, 16)), T((-30, 10))], 0.3, 4))
    s += shape(can, LAMP)
    band = f"M {P(T((6, -20)))} L {P(T((6, 20)))}"
    s += f'<path d="{band}" stroke="{LAMP_DK}" stroke-width="{f(LW*1.1)}" stroke-linecap="round"/>'
    s += f'<g opacity="0.8">{brush([T((-20, -10)), T((18, -14))], 3.0, 2.2, "#9B95B0")}</g>'
    lens = smooth_closed([T((30, -20)), T((36, -12)), T((38, 0)), T((36, 12)), T((30, 20)), T((26, 0))])
    s += shape(lens, LIGHT)
    s += f'<g opacity="0.9">{brush([T((33, -12)), T((35, -2))], 2.6, 2.0, "#FFFFFF")}</g>'
    for k in (-1, 1):
        s += f'<circle cx="{f(c[0]+30*k)}" cy="{f(c[1])}" r="5" fill="{LAMP_DK}" stroke="{INK}" stroke-width="{f(LW*0.7)}"/>'
    return s


def beam_svg(c, aim, ex):
    T = lambda p: add(c, BA.rot2(p, aim))  # noqa: E731
    l1, l2 = T((36, -16)), T((36, 16))
    lft, rgt = (l1, l2) if l1[0] < l2[0] else (l2, l1)
    ey = GROUND_Y + 2
    rx, ry = SPOT_RX, SPOT_RY
    d = (f"M {P(lft)} L {P((ex-rx, ey))} C {P((ex-rx, ey+K*ry))} {P((ex-K*rx, ey+ry))} {P((ex, ey+ry))} "
         f"C {P((ex+K*rx, ey+ry))} {P((ex+rx, ey+K*ry))} {P((ex+rx, ey))} L {P(rgt)} Z")
    gid = f"bm{int(ex)}"
    grad = (f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="{f(c[0])}" y1="{f(c[1])}" x2="{f(ex)}" y2="{f(ey)}">'
            f'<stop offset="0" stop-color="{LIGHT}" stop-opacity="0.42"/><stop offset="1" stop-color="{LIGHT}" stop-opacity="0.10"/></linearGradient>')
    return grad + f'<path d="{d}" fill="url(#{gid})"/>'


def pool_svg(ex):
    ey = GROUND_Y + 2
    gid = f"pl{int(ex)}"
    grad = (f'<radialGradient id="{gid}"><stop offset="0" stop-color="{LIGHT}" stop-opacity="0.75"/>'
            f'<stop offset="0.75" stop-color="{LIGHT}" stop-opacity="0.45"/><stop offset="1" stop-color="{LIGHT}" stop-opacity="0.15"/></radialGradient>')
    s = grad + f'<path d="{ellipse_d(ex, ey, SPOT_RX, SPOT_RY)}" fill="url(#{gid})"/>'
    s += f'<g opacity="0.55">{ring_brush((ex, ey), SPOT_RX, SPOT_RY, 4.5, LIGHT_DK, 15, 375, 40, gap=40)}</g>'
    return s


def scene_spotlight(poses):
    plan = [
        # 標籤、光圈中心 x、身體、眼睛 look、hl、pose 來源、效果
        ("聚光燈打在比比身上", 248, dict(), (0, 0), True, 0, "shine"),
        ("開心縮一下（瞇眼）", 250, dict(), None, False, 2, "shine"),
        ("光往右移、眼睛跟著", 276, dict(rot=1.0), (8, 2), False, 0, None),
        ("光圈滑過去", 330, dict(rot=2.0, lag=0.03), (10, 3), False, 0, None),
        ("快到了", 385, dict(rot=3.0, lag=0.04), (11, 3), False, 0, None),
        ("光圈停在介紹對象", 420, dict(rot=3.5, lag=0.05), (11, 2), True, 0, "target"),
        ("「就是這個！」", 424, dict(rot=4.0, lag=0.06, h=1.01), (11, 1), True, 0, "target2"),
        ("光開始回來", 405, dict(rot=3.0, lag=0.04), (9, 2), False, 0, None),
        ("滑回來", 355, dict(rot=2.0, lag=0.02), (6, 2), False, 0, None),
        ("快回到身上", 300, dict(rot=1.0), (3, 1), False, 0, None),
        ("回到身上、看觀眾", 264, dict(h=1.01), (0, 0), True, 0, None),
        ("站在光裡（接回第 1 格）", 250, dict(h=0.995), (0, -1), True, 0, "shine"),
    ]
    frames = []
    for i, (lab, ex, gk, look, hl, src, fx) in enumerate(plan):
        g = base_geom(poses, src, **gk) if src == 0 else nat_geom(poses, src)
        pose = face_pose(poses, look=look, hl=hl) if look is not None else None
        aim = math.degrees(math.atan2(GROUND_Y - 30 - LAMP_C[1], ex - LAMP_C[0]))
        lamp_c = (LAMP_C[0], LAMP_C[1] + 3 * math.sin(2 * math.pi * i / 12))
        back = pool_svg(ex)
        front = beam_svg(lamp_c, aim, ex)
        front += float_bits((lamp_c[0], lamp_c[1] + 26), 52)
        front += lamp_svg(lamp_c, aim)
        if fx == "shine":
            top = fwd(poses, g, 254, 150)
            front += sparkle(add(top, (-118, 30)), 9) + sparkle(add(top, (122, 20)), 7)
        if fx in ("target", "target2"):
            front += sparkle((ex + 48, GROUND_Y - 34), 12 if fx == "target" else 15) + sparkle((ex - 40, GROUND_Y - 52), 8)
            # 小肉掌貼在身體右側比「這邊」（不伸手臂）
            pc = fwd(poses, g, 440, 330)
            front += paw_svg(add(pc, (6, 0)), 0, r=12.5, squash=0.85, seed=90 + i)
            if fx == "target2":
                front += motion_lines(add(pc, (14, 0)), 0, spread=32, r0=14, length=12, n=3, w=4.6)
        ip = {"lamp": [r1(lamp_c[0]), r1(lamp_c[1])], "aim_deg": r1(aim),
              "pool": {"center": [ex, GROUND_Y + 2], "rx": SPOT_RX, "ry": SPOT_RY}}
        frames.append({"g": g, "pose": pose, "label": lab, "back": back, "front": front, "ip": ip})
    return frames


# ================================================================== 6. 坐滑板滑過
DECK_Y = 462.0


def board_svg(s, i, bob):
    """滑板：前端（行進方向）翹起、中間金幣貼紙、兩顆黃輪子（輪上一個記號點，每格轉 30°）。"""
    X = lambda x: 248 + s * (x - 248)  # noqa: E731
    y0 = DECK_Y + bob
    top = [(126, y0 - 4), (150, y0), (248, y0 + 1), (340, y0), (366, y0 - 8), (380, y0 - 20)]
    bot = [(384, y0 - 13), (370, y0 + 4), (340, y0 + 12), (248, y0 + 13), (150, y0 + 12), (128, y0 + 6), (118, y0 - 2)]
    pts = [(X(x), y) for x, y in top + bot]
    s_ = ""
    # 輪架＋輪子（在板子後面）
    for wx in (170, 326):
        cx = X(wx); cy = y0 + 25
        s_ += shape(smooth_closed(rrect_pts(cx, y0 + 15, 26, 10, 3, 1, 2)), "#8A8798", lw=LW * 0.8)
        s_ += shape(ellipse_d(cx, cy, 12.5, 12.5), WHEEL)
        a = math.radians(30 * i * s + wx)
        s_ += f'<circle cx="{f(cx)}" cy="{f(cy)}" r="3.4" fill="{WHEEL_DK}"/>'
        s_ += f'<circle cx="{f(cx+7.2*math.cos(a))}" cy="{f(cy+7.2*math.sin(a))}" r="2.6" fill="{INK}"/>'
    d = smooth_closed(jitter(pts, 0.3, 8))
    inner = f'<path d="{d}" fill="{DECK}"/>'
    inner += f'<path d="M {P((X(130), y0+7))} C {P((X(200), y0+13))} {P((X(300), y0+13))} {P((X(372), y0+2))} L {P((X(390), y0+20))} L {P((X(110), y0+20))} Z" fill="{DECK_DK}"/>'
    inner += f'<g opacity="0.9">{brush([(X(160), y0+3), (X(330), y0+3)], 2.6, 2.0, DECK_LT)}</g>'
    s_ += clip(f"dk{i}{s}", d, inner) + f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{f(LW)}" stroke-linejoin="round"/>'
    return s_


def scene_slide(poses, s):
    labs = ["滑行（亮眼）", "壓到小石頭彈一下", "落回板子", "風吹毛往後", "加速（瞇眼笑）", "瞇眼享受",
            "張眼往前看", "小彈跳", "落回", "風吹", "張嘴笑", "穩穩滑（接回第 1 格）"]
    bobs = [0, -5, 1.5, 0, 0, -1, 0, -4, 1, 0, 0, -0.5]
    frames = []
    for i in range(12):
        ph = 2 * math.pi * i / 12
        bob = bobs[i]
        g = base_geom(poses, 0, bottom=DECK_Y - GROUND_Y + 1 + bob, rot=-s * (7 + 1.5 * math.sin(ph)),
                      lag=0.07 + 0.03 * math.sin(ph * 2), h=0.985 if bobs[i] > 0.5 else 1.0)
        happy = i in (4, 5)
        pose = face_pose(poses, look=(s * 7, -2), hl=i not in (4, 5, 10)) if not happy else None
        back, front = "", ""
        # 速度線：行進方向的後方，每格往後移 30px（120px 一循環 → 12 格剛好 3 圈）
        for k, (yy, base_x, ln) in enumerate(((300, 20, 60), (348, 70, 46), (396, 0, 70), (436, 50, 54), (470, 95, 40))):
            off = (base_x + 30 * i) % 120
            x1 = 112 - off + 60          # 前端
            x0 = x1 - ln
            xa, xb = (x0, x1) if s > 0 else (496 - x0, 496 - x1)
            opac = 0.85 if k % 2 == 0 else 0.55
            back += f'<g opacity="{opac}">{brush([(xa, yy), ((xa+xb)/2, yy-1), (xb, yy)], 6.5, 5.5)}</g>'
        # 尾流小金幣（資金流向）：往後飄、翻面
        for k in range(2):
            t = ((i + 6 * k) % 12) / 12
            cx = 248 - s * (150 + 120 * t)
            cy = 400 - 70 * t + (k * 30) - 10 * math.sin(math.pi * t)
            op = 1 - t ** 2
            front += f'<g opacity="{op:.2f}">{coin_svg((cx, cy), 13 - 3 * t, math.cos(ph * 2 + k), deg=s * 10)}</g>'
        # 後輪灰塵
        if i % 3 == 0:
            back += dust_puff((248 - s * 150, DECK_Y + 22), 11, 70 + i, op=0.9)
        elif i % 3 == 1:
            back += dust_puff((248 - s * 176, DECK_Y + 16), 14, 70 + i, op=0.55)
        front += board_svg(s, i, bob)
        # 兩隻小肉掌扶著板子邊（不伸手臂）
        for side in (-1, 1):
            front += paw_svg((248 + side * 122, DECK_Y + bob - 4), 90, r=11.5, squash=0.85, seed=110 + side)
        if happy:
            front += eyes_svg(poses, g, "happy")
        if i == 1:
            front += motion_lines((248, DECK_Y + 36), -90, spread=40, r0=2, length=10, n=3, w=4.2)
        ip = {"board_center": [248, r1(DECK_Y + bob + 6)], "wheels": [[r1(248 - s * 78), r1(DECK_Y + bob + 25)],
                                                                    [r1(248 + s * 78), r1(DECK_Y + bob + 25)]],
              "direction": "右" if s > 0 else "左"}
        frames.append({"g": g, "pose": pose, "label": labs[i], "back": back, "front": front, "ip": ip})
    return frames


# ================================================================== 7. 抱著懸空小手機（螢幕留白）
PH_W, PH_H, SC_W, SC_H = 214.0, 128.0, 188.0, 106.0


def phone_svg(c, deg):
    s = ""
    back = smooth_closed(rot_pts(jitter(rrect_pts(c[0] + 3, c[1] + 5, PH_W, PH_H, 22), 0.4, 5), c, deg))
    s += shape(back, CASE_DK)
    body = smooth_closed(rot_pts(jitter(rrect_pts(c[0], c[1], PH_W, PH_H, 22), 0.4, 6), c, deg))
    s += shape(body, CASE)
    # 側邊鏡頭點與按鈕（在右側邊框）
    cam = rot_pts([(c[0] + PH_W / 2 - 6.5, c[1])], c, deg)[0]
    s += f'<circle cx="{f(cam[0])}" cy="{f(cam[1])}" r="3.2" fill="{INK}"/>'
    btn = rot_pts([(c[0] - 30, c[1] - PH_H / 2 - 2), (c[0] + 4, c[1] - PH_H / 2 - 2)], c, deg)
    s = f'<g>{brush(btn, 6.5, 6.5, INK)}</g>' + s
    # 螢幕：純白、直角（剪輯直接貼錄影），細描邊
    sc = rot_pts([(c[0] - SC_W / 2, c[1] - SC_H / 2), (c[0] + SC_W / 2, c[1] - SC_H / 2),
                  (c[0] + SC_W / 2, c[1] + SC_H / 2), (c[0] - SC_W / 2, c[1] + SC_H / 2)], c, deg)
    d = "M " + " L ".join(P(p) for p in sc) + " Z"
    s += f'<path d="{d}" fill="#FFFFFF" stroke="{INK}" stroke-width="{f(LW2)}" stroke-linejoin="round"/>'
    return s, sc


def scene_phone(poses):
    plan = [
        # 標籤、身體、看、hl、覆蓋、效果
        ("低頭看螢幕", dict(lag=-0.02), (0, 7), False, None, None),
        ("眼睛往左掃", dict(lag=-0.02, rot=-0.8), (-5, 7), False, None, None),
        ("眼睛往右掃", dict(lag=-0.02, rot=0.8), (5, 7), False, None, None),
        ("看到了！", dict(lag=0.0, h=1.01), (0, 5), True, None, "ex"),
        ("眨眼", dict(lag=0.02), (0, 0), False, "blink", None),
        ("抬頭", dict(lag=0.08), (0, -2), True, None, None),
        ("對觀眾笑（亮眼）", dict(lag=0.10, h=1.01), (0, 0), True, None, "spark"),
        ("開心瞇眼", dict(lag=0.10, h=1.015, w=0.995), (0, 0), False, "happy", "spark2"),
        ("跳一下", dict(lag=0.12, bottom=-5, h=1.03, w=0.98), (0, 0), False, "happy", "hop"),
        ("落下看觀眾", dict(lag=0.06, w=1.01), (0, 0), True, None, None),
        ("低頭回去看", dict(lag=0.0), (0, 5), False, None, None),
        ("看螢幕（接回第 1 格）", dict(lag=-0.02), (0, 7), False, None, None),
    ]
    frames = []
    for i, (lab, gk, look, hl, ov, fx) in enumerate(plan):
        g = base_geom(poses, 0, **gk)
        pose = face_pose(poses, look=look, hl=hl)
        ph = 2 * math.pi * i / 12
        mouth_y = fwd(poses, g, 251, 322)[1]
        c = (248 + 3 * math.sin(ph), mouth_y + PH_H / 2 + 8 + 2 * math.sin(ph + 1))
        deg = 2.5 * math.sin(ph + 0.4)
        front, sc = "", None
        ph_svg, sc = phone_svg(c, deg)
        front += ph_svg
        # 兩隻小肉掌扶住手機左右兩側（不伸手臂）
        for side in (-1, 1):
            pc = rot_pts([(c[0] + side * (PH_W / 2 + 2), c[1] + 14)], c, deg)[0]
            front += paw_svg(pc, 180 if side < 0 else 0, r=13, squash=0.85, seed=130 + side)
        if fx == "ex":
            top = fwd(poses, g, 400, 165)
            front += exmark(add(top, (16, -20)), 0.6, 14)
        if fx in ("spark", "spark2"):
            top = fwd(poses, g, 254, 150)
            k = 1.0 if fx == "spark" else 1.25
            front += sparkle(add(top, (-140, 40)), 9 * k) + sparkle(add(top, (146, 30)), 11 * k)
        if fx == "hop":
            front += motion_lines((g["cx"] - 160, g["bottom"] - 40), 160, spread=26, r0=4, length=12, n=2) + \
                motion_lines((g["cx"] + 160, g["bottom"] - 40), 20, spread=26, r0=4, length=12, n=2)
        if ov:
            front = eyes_svg(poses, g, ov) + front
        ip = {"screen_corners": [[r1(x), r1(y)] for x, y in sc], "phone_center": [r1(c[0]), r1(c[1])], "deg": r1(deg)}
        frames.append({"g": g, "pose": pose, "label": lab, "front": front, "ip": ip})
    return frames


# ================================================================== 8. 拉開布幕
ROD_Y, CUR_TOP, CUR_BOT = 44.0, 58.0, 198.0
CUR_L, CUR_R = 92.0, 404.0
MID = (CUR_L + CUR_R) / 2


def panel_svg(side, o, sway, seed):
    """一片布幕：外緣固定在 CUR_L／CUR_R，內緣隨開口 o 往外收；5 道摺痕跟著壓縮；下襬波浪。"""
    outer = CUR_L if side < 0 else CUR_R
    full = MID - CUR_L
    w = full * (1 - 0.84 * o)
    inner = outer - side * w
    tie = o > 0.45
    bot_inner = inner + side * (14 * o) + sway
    mid_y = CUR_TOP + (CUR_BOT - CUR_TOP) * 0.62
    pinch = side * 10 * o if tie else 0
    # 外框：上緣直、外緣直、內緣三次曲線（綁起來時中段往外凹）、下襬波浪
    n = 5
    hem = []
    for k in range(n * 2 + 1):
        t = k / (n * 2)
        x = outer + (bot_inner - outer) * t
        y = CUR_BOT + (6 if k % 2 else 0) + 2 * math.sin(seed + k)
        hem.append((x, y))
    d = f"M {P((outer, CUR_TOP))} L {P((inner, CUR_TOP))} "
    d += f"C {P((inner + pinch * 0.2, CUR_TOP + 40))} {P((inner + pinch * 1.6, mid_y - 10))} {P((inner + pinch, mid_y))} "
    d += f"C {P((inner + pinch * 0.6, mid_y + 20))} {P((bot_inner, CUR_BOT - 18))} {P((bot_inner, CUR_BOT))} "
    hem_r = hem[::-1]
    for k in range(1, len(hem_r)):
        a, b = hem_r[k - 1], hem_r[k]
        m = ((a[0] + b[0]) / 2, max(a[1], b[1]) + 4)
        d += f"Q {P(m)} {P(b)} "
    d += "Z"
    inner_body = f'<path d="{d}" fill="{VELVET}"/>'
    # 摺痕：暗色＋亮色細條
    for k in range(1, n):
        t = k / n
        xt = outer + (inner - outer) * t
        xb = outer + (bot_inner - outer) * t
        xm = outer + (inner + pinch - outer) * t
        inner_body += f'<g opacity="0.75">{brush(bez((xt, CUR_TOP + 4), (xm, mid_y - 30), (xm, mid_y + 10), (xb, CUR_BOT + 2), 16), 7.5 - 3 * o, 6 - 2 * o, VELVET_DK)}</g>'
        xt2, xb2 = xt + side * -6 * (1 - 0.7 * o), xb + side * -6 * (1 - 0.7 * o)
        inner_body += f'<g opacity="0.55">{brush(bez((xt2, CUR_TOP + 10), (xm - side * 5, mid_y - 30), (xm - side * 5, mid_y), (xb2, CUR_BOT - 6), 14), 2.8, 2.0, VELVET_LT)}</g>'
    s = clip(f"cp{side}{int(o*100)}{int(sway)}", d, inner_body)
    s += f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{f(LW)}" stroke-linejoin="round"/>'
    if tie:
        # 金色綁繩＋流蘇
        tx0 = outer + side * -4
        tx1 = inner + pinch + side * 6
        s += brush(bez((tx0, mid_y - 4), ((tx0 + tx1) / 2, mid_y + 8), ((tx0 + tx1) / 2, mid_y + 8), (tx1, mid_y - 2), 12), 7.5, 7.5, INK)
        s += brush(bez((tx0, mid_y - 4), ((tx0 + tx1) / 2, mid_y + 8), ((tx0 + tx1) / 2, mid_y + 8), (tx1, mid_y - 2), 12), 4.2, 4.2, GOLD)
        tc = (tx1, mid_y + 2)
        tas = smooth_closed([(tc[0], tc[1]), (tc[0] + 6, tc[1] + 10), (tc[0] + 5, tc[1] + 24), (tc[0] - 5, tc[1] + 24), (tc[0] - 6, tc[1] + 10)])
        s += shape(tas, GOLD, lw=LW * 0.75)
        s += f'<circle cx="{f(tc[0])}" cy="{f(tc[1])}" r="5" fill="{GOLD_DK}" stroke="{INK}" stroke-width="{f(LW*0.7)}"/>'
    return s, inner, bot_inner


def curtain_svg(o, sway=0.0, bob=0.0):
    s = ""
    pl, il, bl = panel_svg(-1, o, -sway, 1)
    pr, ir, br = panel_svg(1, o, sway, 2)
    s += pl + pr
    # 上方垂幔（深紅、扇形下緣、金邊）
    n = 6
    d = f"M {P((CUR_L - 8, ROD_Y + 2))} L {P((CUR_R + 8, ROD_Y + 2))} L {P((CUR_R + 8, CUR_TOP + 4))} "
    for k in range(n, 0, -1):
        x0 = CUR_L - 8 + (CUR_R - CUR_L + 16) * k / n
        x1 = CUR_L - 8 + (CUR_R - CUR_L + 16) * (k - 1) / n
        d += f"C {P((x0 - 6, CUR_TOP + 22))} {P((x1 + 6, CUR_TOP + 22))} {P((x1, CUR_TOP + 4))} "
    d += "Z"
    s += shape(d, VELVET_DK)
    for k in range(n):
        x0 = CUR_L - 8 + (CUR_R - CUR_L + 16) * (k + 1) / n
        x1 = CUR_L - 8 + (CUR_R - CUR_L + 16) * k / n
        s += brush(bez((x0 - 4, CUR_TOP + 6), (x0 - 8, CUR_TOP + 17), (x1 + 8, CUR_TOP + 17), (x1 + 4, CUR_TOP + 6), 12), 3.4, 3.4, GOLD)
    # 桿子＋兩端金球
    s += brush([(CUR_L - 22, ROD_Y), (CUR_R + 22, ROD_Y)], 9.5, 9.5, INK)
    s += brush([(CUR_L - 20, ROD_Y), (CUR_R + 20, ROD_Y)], 5.0, 5.0, WOOD_DK)
    for x in (CUR_L - 26, CUR_R + 26):
        s += shape(ellipse_d(x, ROD_Y, 9, 9), GOLD, lw=LW * 0.8)
        s += f'<circle cx="{f(x-3)}" cy="{f(ROD_Y-3)}" r="2.2" fill="#FFFFFF" opacity="0.9"/>'
    s = f'<g transform="translate(0,{bob:.2f})">{s}</g>'
    return s, (il, ir)


def scene_reveal(poses):
    plan = [
        # 標籤、開口 o、擺動、身體、看、hl、pose、效果
        ("布幕關著，抬頭看", 0.0, 0, dict(lag=0.12), (0, -8), False, 0, None),
        ("布幕晃一下（要開了）", 0.02, 4, dict(lag=0.13, h=1.01), (0, -8), True, 0, "wig"),
        ("蹲下蓄力", 0.06, -2, None, None, False, 1, None),
        ("開始拉開", 0.18, 0, dict(lag=0.14, h=1.03, w=0.98, bottom=-4), (0, -7), True, 0, "pull"),
        ("拉開三分之一", 0.36, -2, dict(lag=0.15, bottom=-8, h=1.03, w=0.97), (0, -7), True, 0, "pull"),
        ("拉開一半", 0.56, -3, dict(lag=0.14, bottom=-5, h=1.02), (0, -6), True, 0, "pull"),
        ("快拉開了", 0.74, -2, dict(lag=0.12, h=1.01), (0, -6), True, 0, None),
        ("拉到底", 0.88, 1, dict(lag=0.12), (0, -5), True, 0, None),
        ("登登！（瞇眼笑）", 0.96, 2, None, None, False, 2, "tada"),
        ("全開、看觀眾", 1.0, 1, dict(lag=0.06, h=1.01), (0, 0), True, 0, "tada2"),
        ("全開、閃光", 1.0, 0, dict(lag=0.05), (0, 0), True, 0, "tada"),
        ("全開（停在這格）", 1.0, 0, dict(lag=0.05, h=0.995), (0, 0), True, 0, None),
    ]
    frames = []
    for i, (lab, o, sway, gk, look, hl, src, fx) in enumerate(plan):
        g = base_geom(poses, 0, **gk) if src == 0 else nat_geom(poses, src)
        pose = face_pose(poses, look=look, hl=hl) if look is not None else None
        bob = 2.0 * math.sin(2 * math.pi * i / 12)
        cur, (il, ir) = curtain_svg(o, sway, bob)
        front = cur
        front += sparkle((CUR_L - 40, ROD_Y - 18 + bob), 6) + sparkle((CUR_R + 42, ROD_Y - 16 + bob), 5)
        if fx == "wig":
            front += arcs((CUR_L - 18, CUR_BOT - 30), 180, r=10, n=2, w=4.0) + arcs((CUR_R + 18, CUR_BOT - 30), 0, r=10, n=2, w=4.0)
        if fx == "pull":
            front += motion_lines((il + 6, CUR_BOT - 60), 0, spread=26, r0=4, length=14, n=2, w=4.4) + \
                motion_lines((ir - 6, CUR_BOT - 60), 180, spread=26, r0=4, length=14, n=2, w=4.4)
        if fx in ("tada", "tada2"):
            k = 1.0 if fx == "tada" else 0.75
            front += sparkle((MID - 70, 110 + bob), 16 * k) + sparkle((MID + 80, 94 + bob), 12 * k) + \
                sparkle((MID + 10, 160 + bob), 9 * k) + sparkle((MID - 120, 170 + bob), 7 * k)
        ip = {"opening": {"x0": r1(il), "x1": r1(ir), "y0": r1(CUR_TOP + bob), "y1": r1(CUR_BOT + bob)}, "open": o}
        frames.append({"g": g, "pose": pose, "label": lab, "front": front, "ip": ip})
    return frames


# ================================================================== 組別、說明
SCENES = {
    "tap": ("跳上去踩按鈕（漣漪）", lambda p: scene_tap(p), [120, 80, 90, 60, 60, 70, 80, 60, 60, 90, 90, 140], "tap", ""),
    "pointer_r": ("懸空指示棒・往右上戳", lambda p: scene_pointer(p, 1), [160, 90, 70, 110, 80, 70, 120, 90, 140, 110, 100, 120], "pointer", "_r"),
    "pointer_l": ("懸空指示棒・往左上戳", lambda p: scene_pointer(p, -1), [160, 90, 70, 110, 80, 70, 120, 90, 140, 110, 100, 120], "pointer", "_l"),
    "hop_r": ("原地跳步・往右", lambda p: scene_hop(p, 1), [80, 60, 70, 80, 70, 60] * 2, "hop", "_r"),
    "hop_l": ("原地跳步・往左", lambda p: scene_hop(p, -1), [80, 60, 70, 80, 70, 60] * 2, "hop", "_l"),
    "peek_r": ("從右下角探頭", lambda p: scene_peek(p, 1), [110, 80, 70, 180, 160, 90, 160, 200, 80, 60, 70, 220], "peek", "_r"),
    "peek_l": ("從左下角探頭", lambda p: scene_peek(p, -1), [110, 80, 70, 180, 160, 90, 160, 200, 80, 60, 70, 220], "peek", "_l"),
    "spotlight": ("聚光燈介紹", lambda p: scene_spotlight(p), [160, 120, 90, 80, 80, 140, 180, 90, 80, 80, 110, 140], "spotlight", ""),
    "slide_r": ("坐滑板滑過・往右", lambda p: scene_slide(p, 1), [70] * 12, "slide", "_r"),
    "slide_l": ("坐滑板滑過・往左", lambda p: scene_slide(p, -1), [70] * 12, "slide", "_l"),
    "phone": ("抱著懸空小手機（螢幕留白）", lambda p: scene_phone(p), [180, 140, 140, 160, 90, 100, 160, 200, 90, 120, 120, 160], "phone", ""),
    "reveal": ("拉開布幕", lambda p: scene_reveal(p), [220, 120, 90, 70, 70, 70, 70, 80, 160, 200, 200, 400], "reveal", ""),
}

NOTES = {
    "tap": [
        "互動點＝**漣漪中心 (248, 484)**，就是腳底中心：剪輯把這一點對準錄影裡的「播放鍵」「切換 3D」按鈕中心。",
        "第 9 格腳碰到按鈕、漣漪冒出；第 10～12 格漣漪擴散淡出（rx 62→205、ry 11→26）。漣漪畫在身體後面（上半圈被身體擋住＝踩在按鈕上的透視）。",
        "跳躍用原圖第 1～7 張的像素（跟 `docs/anim/jump/` 同一套關鍵姿勢），最高點腳底 y≈402、頭頂 y≈188。",
        "建議：錄影的按鈕在第 9～10 格同時做「按下」的效果（變色或縮一下），看起來就是比比踩下去的。",
    ],
    "pointer": [
        "互動點＝**指示棒紅色橡皮頭的尖端**（下表 tip 欄，每格像素）。右上版指向 62°、左上版 118°（0°＝往右、90°＝往上）。",
        "棒子懸空浮在比比身旁（下方兩顆小閃光＋淡弧線＝浮著），沿自己的方向滑出去戳兩下（第 3、6 格），第 4、7 格停住有閃光；比比認真臉（眉毛往內壓、嘴巴抿著）盯著尖端，第 9～10 格轉頭看觀眾、點頭。",
        "剪輯：把 tip 對準要介紹的按鈕或圖表的邊；第 4～7 格是「戳到了」。不需要尖端剛好碰到也可以留 10～20px 空隙。",
    ],
    "hop": [
        "原地跳兩步一個循環（第 1～6 格第 1 步、第 7～12 格第 2 步，第 2 步落地瞇眼笑、之後亮眼）。身體往行進方向傾 2～7°，動作線與灰塵在後方。",
        "互動點＝**腳底中心**（下表 foot 欄）。剪輯要「跳著走過畫面」時把整張圖水平平移：建議每 12 格（780ms）平移 160～200px（以 512 畫布計），騰空格（第 3～5、9～11 格）移多一點、落地格（1、6、7、12）幾乎不動，腳才不會在地上滑。",
        "_r＝往右走、_l＝往左走（身體像素不鏡像，只換傾斜方向、眼睛方向、動作線與灰塵的位置）。",
    ],
    "peek": [
        "**裁切邊**：_r 版＝畫布**右緣 x=512 與下緣 y=512**；_l 版＝畫布**左緣 x=0 與下緣 y=512**。比比整隻斜 22° 從那個角落冒出來，身體超出畫布的部分本來就切掉了。",
        "剪輯：把畫布的右下角（_l 是左下角）對齊錄影畫面的右下角（或某個卡片的角），就是從畫面邊緣探頭。",
        "流程：耳朵尖 → 頭頂冒一半 → 探出（過頭一點）→ 眼睛往裡看 → 往上看冒「？」→ 眨眼 → 看觀眾（亮眼）→ 開心瞇眼 → 縮回 → 只剩耳朵。第 12 格只剩一點頭頂毛（不是全空），接回第 1 格。",
        "互動點：頭頂、兩眼座標每格寫在下表（要在比比眼睛旁邊加字幕或箭頭時用）。",
    ],
    "spotlight": [
        "比比左上方懸空一盞小聚光燈（上方 U 形吊架，下方兩顆小閃光＝浮著），燈筒跟著光圈轉向。",
        "互動點＝**地上光圈**（橢圓 rx 92、ry 22，中心 y=484）：第 1～2 格在比比腳下，第 3～6 格往右掃到 x≈420～424（介紹對象），第 7 格停住、比比用身體右側的小肉掌比「這邊」，第 8～11 格掃回來。",
        "光錐與光圈是半透明暖黃（#FFE08A，透明度 0.2～0.75，WebP 保留半透明；GIF 只能全透或不透，要用 GIF 請改用 WebP 或錄影軟體疊 WebP）。剪輯可以把整張放大，讓光圈蓋到錄影裡的卡片上。",
        "比比表情：亮眼 → 瞇眼縮一下 → 眼睛跟著光往右看 → 回頭看觀眾。",
    ],
    "slide": [
        "比比坐在小滑板上（兩隻小肉掌扶著板子邊，不伸手），行進方向的前端翹起；後方速度線每格往後移 30px、12 格剛好轉 3 圈（循環無縫），尾流有兩枚翻面的小金幣（資金流向）與後輪灰塵；輪子上的記號點每格轉 30°。",
        "互動點＝**滑板中心與兩顆輪子**（下表）。剪輯把整張從畫面一側平移到另一側（例如 1.2 秒 從 x=-512 到畫面寬），12 格約 840ms 一循環。",
        "表情：亮眼看前方 → 第 5～6 格瞇眼享受 → 張眼。第 2、8 格壓到小石頭彈一下。",
    ],
    "phone": [
        "比比抱著懸空的橫式小手機（藍色外殼，兩隻小肉掌扶左右兩側，不伸手臂），**螢幕是純白直角矩形 188×106（16:9）**，剪輯直接把網站錄影貼進去。",
        "互動點＝**螢幕四角**（下表，順序：左上、右上、右下、左下）；手機每格微微上下浮 ±2px、轉 ±2.5°，貼錄影時用四角做 corner pin（四角定位）就會跟著動。",
        "表情：低頭看螢幕（眼睛左右掃）→ 看到了「！」→ 眨眼 → 抬頭 → 對觀眾笑（亮眼）→ 開心瞇眼跳一下 → 低頭回去看。",
    ],
    "reveal": [
        "比比頭上懸空一條小舞台布幕（桿子兩端金球、深紅垂幔＋金邊、兩片紅絨布），第 1 格關著，第 2 格晃一下，第 3～9 格從中間往兩側拉開，第 5 格起金色綁繩把布收在兩側，第 9～11 格「登登！」閃光。",
        "互動點＝**布幕開口**（下表 opening：x0～x1、y0～y1）：開口裡是透明的，剪輯把下一段的畫面放在這個框裡（或從這個框放大轉場）。全開時開口約 x 117～379、y 58～198。",
        "這組是「揭曉」用的一次性動作：建議**播一次停在第 12 格**（第 12 格停 400ms）；要循環也可以，但第 12 格會直接跳回關著。",
    ],
}


def ip_cells(name, ip):
    """storyboard 表格中「互動點」欄位文字。"""
    if name == "tap":
        s = f"腳底 ({ip['foot'][0]:.0f}, {ip['foot'][1]:.0f})"
        if "ripple" in ip:
            r = ip["ripple"]
            s += f"；漣漪中心 (248, 484) rx {r['rx']} ry {r['ry']}"
        return s
    if name == "pointer":
        return f"尖端 **({ip['tip'][0]:.0f}, {ip['tip'][1]:.0f})**；手把 ({ip['handle'][0]:.0f}, {ip['handle'][1]:.0f})"
    if name == "hop":
        return f"腳底 ({ip['foot'][0]:.0f}, {ip['foot'][1]:.0f})" + ("（騰空）" if ip["airborne"] else "")
    if name == "peek":
        return (f"頭頂 ({ip['head_top'][0]:.0f}, {ip['head_top'][1]:.0f})；左眼 ({ip['eye_l'][0]:.0f}, {ip['eye_l'][1]:.0f})；"
                f"右眼 ({ip['eye_r'][0]:.0f}, {ip['eye_r'][1]:.0f})")
    if name == "spotlight":
        return f"光圈中心 **({ip['pool']['center'][0]:.0f}, {ip['pool']['center'][1]:.0f})**；燈 ({ip['lamp'][0]:.0f}, {ip['lamp'][1]:.0f}) 朝 {ip['aim_deg']:.0f}°"
    if name == "slide":
        w = ip["wheels"]
        return f"板中心 ({ip['board_center'][0]:.0f}, {ip['board_center'][1]:.0f})；輪 ({w[0][0]:.0f}, {w[0][1]:.0f})／({w[1][0]:.0f}, {w[1][1]:.0f})"
    if name == "phone":
        c = ip["screen_corners"]
        return " ".join(f"({x:.0f},{y:.0f})" for x, y in c) + f"；{ip['deg']:+.1f}°"
    if name == "reveal":
        o = ip["opening"]
        return f"開口 x {o['x0']:.0f}～{o['x1']:.0f}、y {o['y0']:.0f}～{o['y1']:.0f}"
    return ""


def write_storyboard(rd, group, entries):
    lines = [f"# 比比・{entries[0][1].split('・')[0]} 12 格（D 批：跟影片畫面互動）", "",
             "- 需求：Andy 2026-10-10「動作可以跟影片有更多互動，讓觀眾有是比比在介紹的感覺」；規格照 `docs/anim/prompt_kit/01_總控Prompt.md`（raster_first）。",
             f"- 製作：`python scripts/anim/bibi_moves_d.py --out <scratchpad>/bibi --repo-out docs/anim --only {','.join(e[0] for e in entries)}`。",
             "- 身體：原圖 `site/brand/src/support_anim_1009.gif` 的像素網格變形，沒有重畫；眼睛方向、眉毛、抿嘴只改眼睛／嘴巴那兩小塊像素。道具是 SVG 三次 Bézier 手繪路徑，描邊 #1A0907、7.5px×0.75，2048 繪製再 LANCZOS 縮回 512。不伸長手臂，手只露小肉掌。",
             "- 座標系：512×512 透明畫布，左上 (0,0)；身體縮 0.75、中心 x=248、腳底 y=482（跟 A／B 批同一隻、同大小）。下表座標都是這張 512 畫布上的像素；剪輯縮放時等比換算。",
             "- 每格互動點的完整數字（含小數）在 scratchpad `bibi/index_d.json` 的 `interaction`。獨立 PNG 在 scratchpad `bibi/<名>/frames/`（不進版控）。", ""]
    for ln in NOTES[group]:
        lines.append(f"- {ln}")
    for key, name, durs, labels, ips, suffix in entries:
        lines += ["", f"## {name}（`{key}`，合計 {sum(durs)}ms，檔案 `anim{suffix}.webp`／`sheet_12{suffix}.png`）", "",
                  "| 格 | 動作／表情 | 停留 ms | 互動點（512 畫布像素） |", "|---|---|---|---|"]
        for j, (lab, d, ip) in enumerate(zip(labels, durs, ips)):
            lines.append(f"| {j+1:02d} | {lab} | {d} | {ip_cells(group, ip)} |")
    (rd / "storyboard.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="site/brand/src/support_anim_1009.gif")
    ap.add_argument("--out", required=True)
    ap.add_argument("--repo-out", default="docs/anim")
    ap.add_argument("--only", default="")
    ap.add_argument("--index", default="index_d.json", help="平行跑時各組寫不同檔，最後用 --merge 併回 index_d.json")
    ap.add_argument("--merge", action="store_true")
    a = ap.parse_args()
    if a.merge:
        out = Path(a.out); index = {}
        for q in sorted(out.glob("index_d_*.json")):
            index.update(json.loads(q.read_text(encoding="utf-8"))); q.unlink()
        main_idx = out / "index_d.json"
        old = json.loads(main_idx.read_text(encoding="utf-8")) if main_idx.exists() else {}
        old.update(index); main_idx.write_text(json.dumps(old, ensure_ascii=False, indent=1), encoding="utf-8")
        print("merged", sorted(old)); return
    poses = pose_tween.load_poses(Path(a.src))
    out = Path(a.out)
    idx_path = out / a.index
    index = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else {}
    only = [x for x in a.only.split(",") if x]
    groups = {}
    for key, (name, fn, durs, group, suffix) in SCENES.items():
        if only and key not in only and group not in only:
            continue
        frs = fn(poses)
        assert len(frs) == 12 and len(durs) == 12, key
        imgs = [render(poses, fr) for fr in frs]
        fd = out / key / "frames"
        fd.mkdir(parents=True, exist_ok=True)
        paths = []
        for j, im in enumerate(imgs):
            p = fd / f"frame_{j+1:02d}.png"
            im.save(p)
            paths.append(str(p.resolve()))
        rd = Path(a.repo_out) / f"bibi_{group}"
        rd.mkdir(parents=True, exist_ok=True)
        labels = [fr["label"] for fr in frs]
        sheet12(imgs, [f"{j+1:02d} {l}" for j, l in enumerate(labels)], rd / f"sheet_12{suffix}.png")
        imgs[0].save(rd / f"anim{suffix}.webp", save_all=True, append_images=imgs[1:], duration=durs, loop=0,
                     lossless=False, quality=88, method=6)
        imgs[0].save(out / key / "anim.gif", save_all=True, append_images=imgs[1:], duration=durs, loop=0, disposal=2)
        arr = [np.asarray(i).astype(int) for i in imgs]
        diffs = [int(np.abs(arr[k] - arr[(k + 1) % 12]).sum() // 1000) for k in range(12)]
        ips = [fr["ip"] for fr in frs]
        index[key] = {"name": name, "group": group, "size": [SIZE, SIZE], "frames": paths, "durations_ms": durs,
                      "labels": labels, "adjacent_diff_k": diffs, "interaction": ips,
                      "scene": {"scale": BA.SCALE, "center_x": BA.CX, "ground_y": BA.GROUND},
                      "webp": str((rd / f"anim{suffix}.webp").resolve()), "sheet": str((rd / f"sheet_12{suffix}.png").resolve()),
                      "storyboard": str((rd / "storyboard.md").resolve())}
        groups.setdefault(group, []).append((key, name, durs, labels, ips, suffix))
        print(key, "min diff", min(diffs), "→", rd)
    for group, entries in groups.items():
        # 同一組另一個方向這次沒重跑時，從 index 補回來，storyboard 才完整
        have = {e[0] for e in entries}
        for key, (name, _fn, durs, g2, suffix) in SCENES.items():
            if g2 == group and key not in have and key in index:
                entries.append((key, name, index[key]["durations_ms"], index[key]["labels"], index[key]["interaction"], suffix))
        entries.sort(key=lambda e: list(SCENES).index(e[0]))
        write_storyboard(Path(a.repo_out) / f"bibi_{group}", group, entries)
    idx_path.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
