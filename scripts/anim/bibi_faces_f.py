"""動畫設計單位：吉祥物「比比」F 批 10 種新表情（每組 12 格、512×512、透明、可循環）。

為什麼有這支
------------
Andy 2026-10-10 第 3 版要求（docs/marketing/video_1010/v3_brief.md 第 12 條）：
「表情、情境、道具要更豐富，做出來的表情、情境、道具要存成圖檔以後使用」。
C 批（說話＋10 種表情＋自我介紹）在 `bibi_faces_c.py`；這支沿用它的五官系統（原圖座標上補掉原五官再畫新的，
跟身體一起網格變形），只加新表情與新小道具（墨鏡、比讚肉掌、拳頭、哈氣雲、愛心花）。
規格同 A／B／C 批：身體縮 0.75、中心 x=248、腳底 y=482；只用小肉掌，不從身體伸出長手臂。

用法
----
    BIBI_SIGN_FONT=<jf-openhuninn-2.1.ttf> python scripts/anim/bibi_faces_f.py \
        --out <scratchpad>/bibi --repo-out docs/anim [--only face_cool,face_clap]
輸出：<out>/<名>/frames/frame_01.png…、<out>/<名>/anim.gif、<repo-out>/bibi_<名>/sheet_12.png、anim.webp、
storyboard.md；<out>/index_f.json。
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import bibi_actions as BA  # noqa: E402
import bibi_faces_c as C  # noqa: E402
import pose_tween  # noqa: E402

from bibi_actions import (INK, FUR, SIZE, f, P, add, bez, brush, sparkle, motion_lines, arcs, paw_svg,  # noqa: E402
                          base_geom, sheet12, qmark, ease)
from bibi_faces_c import (EYE_L, EYE_R, SW, F, FR, render, heart_svg, star_svg, drop_svg, dots_svg,  # noqa: E402
                          body_rot, smooth_closed, jitter, rrect_pts, shape, STAR, STAR_DK)

LENS, LENS_HL = "#2E2A36", "#8C88A0"
FLOWER, FLOWER_DK = "#F7A7B8", "#E9849A"


# ================================================================== 小道具
def glasses_svg(lc, rc, k=1.0, deg=0.0, glint=0.0):
    """小墨鏡：兩片圓角鏡片＋鼻樑＋往外的短鏡腳。lc／rc＝左右鏡片中心，k＝縮放（原圖座標用 1，場景座標用 0.75）。"""
    out = ""
    cx, cy = (lc[0] + rc[0]) / 2, (lc[1] + rc[1]) / 2
    for c, side in ((lc, -1), (rc, 1)):
        d = smooth_closed(jitter(rrect_pts(c[0], c[1], 54 * k, 40 * k, 15 * k, 2, 3), 0.4 * k, 5 + side))
        out += shape(d, LENS, lw=7.0 * k)
        hl = bez((c[0] - 16 * k, c[1] - 5 * k), (c[0] - 14 * k, c[1] - 12 * k), (c[0] - 8 * k, c[1] - 14 * k), (c[0] - 1 * k, c[1] - 13 * k), 8)
        out += f'<g opacity="0.8">{brush(hl, 4.6 * k, 3.6 * k, LENS_HL)}</g>'
        arm0 = (c[0] + side * 27 * k, c[1] - 6 * k)
        out += brush([arm0, (arm0[0] + side * 22 * k, arm0[1] - 3 * k)], 6.4 * k, 5 * k)
    out += brush(bez((lc[0] + 26 * k, lc[1] - 4 * k), (cx - 6 * k, cy - 13 * k), (cx + 6 * k, cy - 13 * k), (rc[0] - 26 * k, rc[1] - 4 * k), 10), 6.4 * k, 6.4 * k)
    if glint:
        g = (rc[0] + 10 * k, rc[1] - 8 * k)
        out += sparkle(g, 14 * k * glint, "#FFFFFF") + f'<circle cx="{f(g[0])}" cy="{f(g[1])}" r="{f(2.4*k*glint)}" fill="#FFFFFF"/>'
    return f'<g transform="rotate({deg:.1f},{f(cx)},{f(cy)})">{out}</g>' if deg else out


def thumb_svg(c, deg=0.0, r=19.0, seed=0):
    """比讚的小肉掌：握起來的圓掌（兩道指節線）＋往上翹的長大拇指（同肉掌配色、手繪描邊），不接手臂。"""
    tc = (c[0] - r * 0.25, c[1] - r * 1.05)
    tb = smooth_closed(jitter([(tc[0] + 8.5 * math.cos(a), tc[1] + 15 * math.sin(a))
                               for a in np.linspace(0, 2 * math.pi, 10, endpoint=False)], 0.3, seed))
    s = shape(tb, BA.PAW, lw=BA.OUT_W * 0.95)
    s += f'<ellipse cx="{f(tc[0]-2.5)}" cy="{f(tc[1]-5)}" rx="2.4" ry="4.2" fill="{BA.PAW_LT}"/>'
    body = smooth_closed(jitter([(c[0] + r * 1.08 * math.cos(a), c[1] + r * 0.9 * math.sin(a))
                                 for a in np.linspace(0, 2 * math.pi, 12, endpoint=False)], 0.5, seed + 1))
    s += shape(body, BA.PAW, lw=BA.OUT_W * 0.95)
    s += f'<ellipse cx="{f(c[0]-r*0.3)}" cy="{f(c[1]+r*0.25)}" rx="{f(r*0.32)}" ry="{f(r*0.22)}" fill="{BA.PAW_DK}" opacity="0.7"/>'
    for dy in (-0.25, 0.2):   # 捲起來的四指：右側兩道指節線
        y = c[1] + r * dy
        s += brush(bez((c[0] + r * 0.15, y), (c[0] + r * 0.45, y - 2), (c[0] + r * 0.75, y - 2), (c[0] + r * 1.02, y + 1), 8), 3.2, 2.6)
    return f'<g transform="rotate({deg:.1f},{f(c[0])},{f(c[1])})">{s}</g>' if deg else s


def fist_svg(c, deg=0.0, r=15.0, seed=0):
    """握拳：肉掌＋兩道指節線。"""
    s = paw_svg(c, 90, r=r, squash=0.95, seed=seed, open_side=270, spots=False)
    for dx in (-5, 3):
        s += brush(bez((c[0] + dx, c[1] - r * 0.7), (c[0] + dx + 1.5, c[1] - r * 0.35), (c[0] + dx + 1.5, c[1] - r * 0.1), (c[0] + dx, c[1] + r * 0.05), 6), 2.8, 2.4)
    return f'<g transform="rotate({deg:.1f},{f(c[0])},{f(c[1])})">{s}</g>' if deg else s


def puff_cloud(c, k, op=1.0):
    """哈氣的小雲：三團不規則圓，白底黑邊。"""
    s = ""
    for dx, dy, r in ((0, 0, 11), (12, -5, 9), (21, 3, 7)):
        d = smooth_closed(jitter([(c[0] + dx * k + r * k * math.cos(a), c[1] + dy * k + r * k * math.sin(a))
                                  for a in np.linspace(0, 2 * math.pi, 8, endpoint=False)], 0.5 * k, int(r)))
        s += shape(d, "#FFFFFF", lw=3.6 * k)
    return s if op >= 1 else f'<g opacity="{op:.2f}">{s}</g>'


def flower_svg(c, k=1.0, deg=0.0):
    s = ""
    for j in range(5):
        a = math.radians(deg + j * 72)
        pc = (c[0] + 11 * k * math.cos(a), c[1] + 11 * k * math.sin(a))
        d = smooth_closed(jitter([(pc[0] + 8.5 * k * math.cos(b), pc[1] + 8.5 * k * math.sin(b))
                                  for b in np.linspace(0, 2 * math.pi, 8, endpoint=False)], 0.4 * k, j))
        s += shape(d, FLOWER, lw=3.4 * k)
    s += f'<circle cx="{f(c[0])}" cy="{f(c[1])}" r="{f(7*k)}" fill="{STAR}" stroke="{INK}" stroke-width="{f(3.2*k)}"/>'
    return s


def brows_extra(kind):
    """F 批另外要的眉毛（原圖座標，交給 face_pose(extra=...)）：determined＝內側壓低的倔強眉；relief＝八字下垂。"""
    out = ""
    for e, side in ((EYE_L, -1), (EYE_R, 1)):
        x, y = e[0], e[1] - 30
        if kind == "determined":
            a = (x - side * 13, y - 6); b = (x + side * 11, y + 4)
            out += brush(bez(a, (x - side * 4, y - 4), (x + side * 4, y), b, 10), 7.0, 6.0)
        elif kind == "relief":
            a = (x - side * 12, y + 3); b = (x + side * 11, y - 4)
            out += brush(bez(b, (x + side * 3, y - 6), (x - side * 4, y - 1), a, 10), 5.6, 5.0)
    return out


DET = brows_extra("determined")
REL = brows_extra("relief")


def glasses_on_face():
    return glasses_svg((EYE_L[0], EYE_L[1] + 2), (EYE_R[0], EYE_R[1] + 2), 1.0)


GL_FACE = glasses_on_face()


# ================================================================== 10 種表情
def face_relief(poses):
    seq = [
        ("待機", dict(), dict(), 0),
        ("緊張（憋氣、眉頭皺）", dict(h=1.03, w=0.98, lag=-0.02), dict(eyes="dot", mouth="wavy", brows="worry", es=(0.9, 0.9)), 1),
        ("憋到最滿", dict(h=1.05, w=0.97, lag=-0.03), dict(eyes="line", mouth="w", brows="worry"), 1),
        ("呼～（開始吐氣）", dict(h=1.0, w=1.01), dict(eyes="blink", mouth="o", extra=REL), 2),
        ("呼～～（身體洩氣）", dict(h=0.96, w=1.03, lag=0.02), dict(eyes="blink", mouth="o", extra=REL), 3),
        ("吐完、整隻軟掉", dict(h=0.93, w=1.05, lag=0.03), dict(eyes="blink", mouth="tiny", extra=REL), 4),
        ("軟趴趴晃", dict(h=0.935, w=1.05, rot=-2), dict(eyes="happy", mouth="w", extra=REL), 5),
        ("軟趴趴晃（回）", dict(h=0.94, w=1.045, rot=1.5), dict(eyes="happy", mouth="w", extra=REL), 6),
        ("慢慢回彈", dict(h=0.97, w=1.02), dict(eyes="happy", mouth="open_s"), 0),
        ("安心微笑", dict(h=1.01, w=0.995), dict(eyes="happy", mouth="w", blush="soft"), 0),
        ("睜眼", dict(h=1.0), dict(eyes="dot", mouth="w"), 0),
        ("回待機", dict(h=0.995), dict(), 0),
    ]
    frames = []
    for i, (lab, gk, face, st) in enumerate(seq):
        g = base_geom(poses, 0, **gk)
        front = ""
        if st == 1:
            front += drop_svg(F(poses, g, 412, 180), 9, deg=-12)
        if 2 <= st <= 5:
            m = F(poses, g, 262, 296)
            t = (st - 2) / 3
            front += puff_cloud((m[0] + 62 + 45 * t, m[1] - 14 - 14 * t), 0.8 + 0.6 * t, op=1.0 if t < 0.9 else 0.6)
            front += motion_lines((m[0] + 22, m[1]), 0, spread=22, r0=4, length=10, n=2, w=3.6)
        if st == 2:   # 汗滴被甩開
            front += drop_svg(F(poses, g, 450, 160), 8, deg=30)
        if st in (5, 6):
            front += sparkle(F(poses, g, 70, 230), 9) + sparkle(F(poses, g, 440, 210), 7)
        frames.append(FR(poses, lab, gk, face, front))
    return frames


def face_cool(poses):
    # 墨鏡從上方掉下來 → 戴上（畫在原圖座標的臉上，跟臉一起變形）→ 酷酷歪頭、鏡片閃光 → 墨鏡往上推走
    eyes_cool = dict(eyes="dot", mouth="w", extra=GL_FACE)
    seq = [
        ("待機", dict(), dict(), None, 0),
        ("墨鏡從天而降", dict(lag=0.04), dict(eyes="dot", mouth="o", look=(0, -6)), (0, -150), 0),
        ("快到了", dict(lag=0.03), dict(eyes="dot", mouth="o", look=(0, -4)), (0, -60), 0),
        ("戴上！（身體一沉）", dict(h=0.96, w=1.03), dict(eyes_cool), None, 0),
        ("酷（歪頭）", dict(h=1.01, rot=-5, lag=0.04), dict(eyes="dot", mouth="w", extra=GL_FACE, blush=None), None, 0),
        ("鏡片閃光", dict(h=1.015, rot=-6, lag=0.05), dict(eyes="dot", mouth="w", extra=GL_FACE), None, 1.0),
        ("嘴角一勾", dict(h=1.015, rot=-6, lag=0.05), dict(eyes="dot", mouth="tongue", extra=GL_FACE), None, 0.6),
        ("酷酷點頭", dict(h=0.98, rot=-5, lag=-0.05), dict(eyes="dot", mouth="w", extra=GL_FACE), None, 0),
        ("酷（另一邊）", dict(h=1.01, rot=-4, lag=0.04), dict(eyes="dot", mouth="w", extra=GL_FACE), None, 0.4),
        ("把墨鏡往上推", dict(h=1.0, rot=-2, lag=0.03), dict(eyes="happy", mouth="w"), (0, -40), 0),
        ("墨鏡飛走、眨眼", dict(h=1.0, rot=-1), dict(eyes=("dot", "happy"), mouth="w"), (40, -140), 0),
        ("回待機", dict(h=0.995), dict(), None, 0),
    ]
    frames = []
    for i, (lab, gk, face, fly, glint) in enumerate(seq):
        g = base_geom(poses, 0, **gk)
        front = ""
        if fly:
            lc = F(poses, g, *EYE_L); rc = F(poses, g, *EYE_R)
            dx, dy = fly
            front += glasses_svg((lc[0] + dx, lc[1] + dy), (rc[0] + dx, rc[1] + dy), 0.75, deg=-8 if dx else 4)
            if dy < -50 and not dx:
                front += motion_lines(((lc[0] + rc[0]) / 2, lc[1] + dy - 30), 90, spread=30, r0=0, length=14, n=3, w=4)
        if glint:
            rc = F(poses, g, EYE_R[0] + 12, EYE_R[1] - 10)
            front += sparkle(rc, 15 * glint, "#FFFFFF") + sparkle(rc, 9 * glint)
        if i == 3:
            front += motion_lines(F(poses, g, 60, 250), 180, spread=26, r0=4, length=12, n=2, w=4.4) + \
                motion_lines(F(poses, g, 450, 245), 0, spread=26, r0=4, length=12, n=2, w=4.4)
        if i in (5, 6, 8):
            front += star_svg(F(poses, g, 440, 160), 10, deg=12 * i, lw=2.6)
        frames.append(FR(poses, lab, gk, face, front))
    return frames


def face_shy(poses):
    # 兩隻小肉掌從下方舉到眼睛前摀住 → 從指縫偷看 → 放下
    seq = [
        ("待機", dict(), dict(), 0.0, 0),
        ("被稱讚了（臉紅）", dict(h=0.99, rot=-1), dict(eyes="dot", mouth="w", blush="soft"), 0.3, 0),
        ("肉掌舉起", dict(h=0.97, w=1.02, rot=-2, lag=-0.03), dict(eyes="happy", mouth="wavy", blush="lines"), 0.7, 0),
        ("摀住臉！", dict(h=0.95, w=1.03, rot=-3, lag=-0.05), dict(eyes="happy", mouth="wavy", blush="lines"), 1.0, 0),
        ("扭一下（左）", dict(h=0.95, w=1.03, rot=-6, lag=-0.05), dict(eyes="happy", mouth="wavy", blush="lines"), 1.0, 0),
        ("扭一下（右）", dict(h=0.95, w=1.03, rot=2, lag=-0.05), dict(eyes="happy", mouth="wavy", blush="lines"), 1.0, 0),
        ("從指縫偷看", dict(h=0.96, w=1.025, rot=-2, lag=-0.04), dict(eyes=("dot", "happy"), mouth="w", blush="lines"), 1.0, 1),
        ("被發現了！再摀", dict(h=0.95, w=1.03, rot=-4, lag=-0.05), dict(eyes="happy", mouth="wavy", blush="lines"), 1.0, 0),
        ("害羞冒愛心", dict(h=0.955, w=1.03, rot=-3, lag=-0.05), dict(eyes="happy", mouth="wavy", blush="lines"), 1.0, 0),
        ("肉掌放下一半", dict(h=0.97, w=1.02, rot=-2), dict(eyes="happy", mouth="w", blush="lines"), 0.6, 0),
        ("嘿嘿", dict(h=0.99, rot=-1), dict(eyes="happy", mouth="open_s", blush="soft"), 0.2, 0),
        ("回待機", dict(h=0.995), dict(), 0.0, 0),
    ]
    frames = []
    for i, (lab, gk, face, t, peek) in enumerate(seq):
        g = base_geom(poses, 0, **gk)
        front = ""
        if t > 0:
            e = ease(t)
            for e0, low, side in ((EYE_L, (150, 420), -1), (EYE_R, (356, 420), 1)):
                tx = e0[0] + side * (14 if (peek and side > 0) else 0)
                px = low[0] + (tx - low[0]) * e
                py = low[1] + (e0[1] + 4 - low[1]) * e
                c = F(poses, g, px, py)
                front += paw_svg(c, 90 - body_rot(g), r=19 * (0.8 + 0.2 * e), squash=0.95, seed=150 + side,
                                 open_side=270)
        if i in (4, 5, 7, 8):
            front += arcs(F(poses, g, 70, 300), 180, r=22, n=2, w=4.2) + arcs(F(poses, g, 440, 296), 0, r=22, n=2, w=4.2)
        if i == 8 or i == 9:
            k = 1.0 if i == 8 else 0.7
            front += heart_svg(F(poses, g, 430, 150), 13 * k, 14) + heart_svg(F(poses, g, 90, 160), 9 * k, -14)
        frames.append(FR(poses, lab, gk, face, front))
    return frames


def face_determined(poses):
    seq = [
        ("待機", dict(), dict(), None, 0),
        ("眼神變認真", dict(h=1.0), dict(eyes="dot", mouth="w", extra=DET), (0.0, 0), 0),
        ("握拳蓄力（縮）", dict(h=0.95, w=1.03, lag=0.02), dict(eyes="dot", mouth="w", extra=DET), (0.3, 0), 0),
        ("加油！（拳頭往上）", dict(h=1.05, w=0.97, bottom=-8, lag=-0.04), dict(eyes="shine", mouth="open_l", extra=DET), (1.0, 1), 1),
        ("落地", dict(h=0.98, w=1.02), dict(eyes="shine", mouth="open_m", extra=DET), (0.6, 0), 1),
        ("再一次！", dict(h=1.05, w=0.97, bottom=-8, lag=-0.04), dict(eyes="shine", mouth="open_l", extra=DET), (1.0, 1), 2),
        ("落地", dict(h=0.98, w=1.02), dict(eyes="shine", mouth="open_m", extra=DET), (0.6, 0), 2),
        ("拳頭定住、燃起來", dict(h=1.02, lag=-0.02), dict(eyes="shine", mouth="w", extra=DET), (0.9, 0), 3),
        ("火更旺", dict(h=1.025, lag=-0.02), dict(eyes="shine", mouth="w", extra=DET), (0.92, 0), 4),
        ("點頭（嗯！）", dict(h=0.97, w=1.02, lag=-0.08), dict(eyes="happy", mouth="w", extra=DET), (0.5, 0), 0),
        ("放下拳頭", dict(h=1.0), dict(eyes="dot", mouth="w"), (0.0, 0), 0),
        ("回待機", dict(h=0.995), dict(), None, 0),
    ]
    frames = []
    for i, (lab, gk, face, fist, fire) in enumerate(seq):
        g = base_geom(poses, 0, **gk)
        back = ""
        front = ""
        texts = []
        if fire:
            # 背後的鬥志火焰（三片三次 Bézier 火舌，畫在身體後面）
            k = {1: 0.6, 2: 0.75, 3: 0.95, 4: 1.1}[fire]
            for j, (sx, h0) in enumerate(((84, 62), (256, 80), (424, 62))):
                b = F(poses, g, sx, 236 if j != 1 else 196)
                hh = h0 * k * (1 + 0.12 * math.sin(i * 1.9 + j))
                w0 = 50 * k
                d = (f"M {P((b[0]-w0, b[1]+50))} C {P((b[0]-w0*1.1, b[1]-hh*0.4))} {P((b[0]-w0*0.2, b[1]-hh*0.6))} {P((b[0]+w0*0.1, b[1]-hh))} "
                     f"C {P((b[0]+w0*0.3, b[1]-hh*0.55))} {P((b[0]+w0*1.2, b[1]-hh*0.35))} {P((b[0]+w0, b[1]+50))} Z")
                back += shape(d, "#FFB259", lw=5.0)
                d2 = (f"M {P((b[0]-w0*0.5, b[1]+20))} C {P((b[0]-w0*0.5, b[1]-hh*0.25))} {P((b[0]-w0*0.1, b[1]-hh*0.35))} {P((b[0]+w0*0.05, b[1]-hh*0.6))} "
                      f"C {P((b[0]+w0*0.2, b[1]-hh*0.3))} {P((b[0]+w0*0.6, b[1]-hh*0.2))} {P((b[0]+w0*0.5, b[1]+20))} Z")
                back += f'<path d="{d2}" fill="#FFE07A"/>'
        if fist:
            t, up = fist
            for sx, side in ((150, -1), (356, 1)):
                py = 420 - 120 * t - (30 if (up and side > 0) else 0)
                px = sx + side * (40 if (up and side > 0) else 0)
                c = F(poses, g, px, py)
                front += fist_svg(c, deg=side * 8 - body_rot(g), r=17, seed=170 + side)
                if up and side > 0:
                    front += motion_lines((c[0], c[1] - 18), 90, spread=34, r0=8, length=14, n=3, w=4.6)
        if fire in (1, 2):
            c = F(poses, g, 70, 150)
            texts.append(("加油！", (c[0] + 4, c[1] - 6 * (fire - 1)), -10, 34, (230, 82, 60, 255)))
        frames.append(FR(poses, lab, gk, face, front, back=back, texts=texts))
    return frames


def face_curious(poses):
    # 好奇湊近鏡頭：身體放大＋往前、眼睛發亮、嗅嗅；頭上冒小「？」
    seq = [
        ("待機", dict(), dict(), 0, 0),
        ("咦？（眼睛一亮）", dict(rot=-3), dict(eyes="shine", mouth="o", es=(1.05, 1.05)), 1, 0),
        ("歪頭看", dict(rot=-7, lag=0.03), dict(eyes="shine", mouth="o", look=(3, -2), es=(1.08, 1.08)), 2, 0),
        ("湊近一點", dict(w=1.08, h=1.08, bottom=8, rot=-4), dict(eyes="shine", mouth="w", es=(1.12, 1.12)), 2, 0),
        ("再湊近（貼到鏡頭）", dict(w=1.17, h=1.17, bottom=22, rot=-2), dict(eyes="shine", mouth="w", es=(1.18, 1.18)), 0, 1),
        ("嗅嗅（左）", dict(w=1.17, h=1.16, bottom=22, rot=-4), dict(eyes="shine", mouth="tiny", es=(1.18, 1.18), look=(-3, 0)), 0, 2),
        ("嗅嗅（右）", dict(w=1.17, h=1.165, bottom=22, rot=0), dict(eyes="shine", mouth="tiny", es=(1.18, 1.18), look=(3, 0)), 0, 2),
        ("眨眨眼", dict(w=1.17, h=1.17, bottom=22, rot=-2), dict(eyes="blink", mouth="w"), 0, 0),
        ("喔～原來如此", dict(w=1.12, h=1.12, bottom=14, rot=-1), dict(eyes="happy", mouth="open_m"), 3, 0),
        ("退回來", dict(w=1.05, h=1.05, bottom=5), dict(eyes="dot", mouth="open_s"), 0, 0),
        ("站好", dict(h=0.98, w=1.01), dict(eyes="dot", mouth="w"), 0, 0),
        ("回待機", dict(h=0.995), dict(), 0, 0),
    ]
    frames = []
    for i, (lab, gk, face, q, sniff) in enumerate(seq):
        g = base_geom(poses, 0, **gk)
        front = ""
        if q in (1, 2):
            top = F(poses, g, 420, 140)
            front += qmark((top[0] + 10, top[1] - 8), k=0.75 if q == 1 else 0.95, deg=14)
        if q == 3:
            front += sparkle(F(poses, g, 430, 150), 14) + sparkle(F(poses, g, 80, 170), 10)
        if sniff:
            m = F(poses, g, 250, 300)
            if sniff == 1:
                front += sparkle(F(poses, g, 440, 200), 10)
            else:
                front += arcs((m[0], m[1] + 4), 200 if i == 5 else -20, r=60, n=2, w=4.2)
        frames.append(FR(poses, lab, gk, face, front))
    return frames


def face_surprise_happy(poses):
    seq = [
        ("待機", dict(), dict(), 0),
        ("咦？", dict(h=0.98, w=1.01), dict(eyes="dot", mouth="o", es=(0.9, 0.9)), 0),
        ("哇！（蹲）", dict(h=0.93, w=1.05, lag=0.03), dict(eyes="wide", mouth="O", es=(1.1, 1.1)), 0),
        ("驚喜跳起、嘴張超大", dict(h=1.08, w=0.95, bottom=-22, lag=-0.06), dict(eyes="shine", mouth="laugh", es=(1.2, 1.2), brows="up"), 1),
        ("最高點、彩帶爆開", dict(h=1.06, w=0.96, bottom=-28, lag=-0.05), dict(eyes="star", mouth="laugh", es=(1.1, 1.1), brows="up"), 2),
        ("往下落", dict(h=1.03, w=0.98, bottom=-12), dict(eyes="star", mouth="laugh", es=(1.0, 1.0), edeg=(30, -30), brows="up"), 3),
        ("落地壓扁", dict(h=0.93, w=1.05), dict(eyes="gt", mouth="laugh", blush="soft"), 4),
        ("開心抖", dict(h=1.03, w=0.98, rot=-3), dict(eyes="shine", mouth="open_l", es=(1.15, 1.15), blush="soft"), 5),
        ("開心抖（另一邊）", dict(h=1.02, w=0.985, rot=3), dict(eyes="shine", mouth="open_l", es=(1.1, 1.1), blush="soft"), 6),
        ("還在笑", dict(h=1.0), dict(eyes="happy", mouth="open_m", blush="soft"), 7),
        ("收嘴", dict(h=0.99, w=1.005), dict(eyes="happy", mouth="w"), 0),
        ("回待機", dict(h=0.995), dict(), 0),
    ]
    cols = ("#F6A5A0", STAR, "#2AA6F5", "#7ED6A5", "#F08A5D")
    frames = []
    for i, (lab, gk, face, st) in enumerate(seq):
        g = base_geom(poses, 0, **gk)
        front = ""
        if st:
            top = F(poses, g, 256, 150)
            t = min(1.0, (st - 1) / 5)
            rng = np.random.default_rng(3)
            for j in range(14):   # 彩帶片：從頭頂往外噴、慢慢落下
                ang = math.radians(200 + j * 140 / 13 + rng.uniform(-6, 6))
                sp = rng.uniform(110, 190)
                x = top[0] + math.cos(ang) * sp * (0.35 + 0.65 * ease(t))
                y = top[1] + math.sin(ang) * sp * (0.35 + 0.65 * ease(t)) + 160 * t * t
                if not (6 < x < 506 and 6 < y < 506):
                    continue
                w0, h0 = 9, 5
                deg = rng.uniform(0, 180) + 60 * st
                front += (f'<rect x="{f(x-w0/2)}" y="{f(y-h0/2)}" width="{w0}" height="{h0}" rx="1.5" fill="{cols[j % 5]}" '
                          f'stroke="{INK}" stroke-width="1.6" transform="rotate({deg:.0f},{f(x)},{f(y)})"/>')
            if st <= 3:
                front += motion_lines((top[0], top[1] - 18), 90, spread=36, r0=10, length=18, n=5, w=5.0)
        if st in (2, 3, 5, 6):
            front += sparkle(F(poses, g, 60, 220), 14) + sparkle(F(poses, g, 455, 200), 11)
        frames.append(FR(poses, lab, gk, face, front))
    return frames


def face_thumbs(poses):
    seq = [
        ("待機", dict(), dict(), None, 0),
        ("肉掌冒出來", dict(h=0.99), dict(eyes="dot", mouth="w"), (0.35, 0), 0),
        ("比讚！（往前推）", dict(h=1.03, w=0.98, lag=-0.03, rot=-2), dict(eyes=("dot", "happy"), mouth="open_m", blush="soft"), (1.0, 1), 1),
        ("讚！閃光", dict(h=1.02, rot=-3), dict(eyes=("shine", "happy"), mouth="w", blush="soft"), (1.0, 0), 2),
        ("讚往前點一下", dict(h=1.025, rot=-3, lag=-0.02), dict(eyes=("shine", "happy"), mouth="open_s", blush="soft"), (1.0, 1), 2),
        ("讚定住", dict(h=1.02, rot=-3), dict(eyes=("shine", "happy"), mouth="w", blush="soft"), (1.0, 0), 3),
        ("眼睛張開、微笑", dict(h=1.015, rot=-1.5), dict(eyes="shine", mouth="open_s"), (1.0, 0), 2),
        ("再比一次（雙眨）", dict(h=1.03, rot=-2, lag=-0.03), dict(eyes="happy", mouth="open_m", blush="soft"), (1.0, 1), 1),
        ("讚！", dict(h=1.02, rot=-2), dict(eyes="happy", mouth="w", blush="soft"), (1.0, 0), 3),
        ("肉掌收一半", dict(h=1.0, rot=-1), dict(eyes="dot", mouth="w"), (0.55, 0), 0),
        ("收回", dict(h=0.99), dict(eyes="dot", mouth="w"), (0.2, 0), 0),
        ("回待機", dict(h=0.995), dict(), None, 0),
    ]
    frames = []
    for i, (lab, gk, face, th, sp) in enumerate(seq):
        g = base_geom(poses, 0, **gk)
        front = ""
        texts = []
        if th:
            t, push = th
            px = 330 + 40 * t; py = 430 - 80 * t
            c = F(poses, g, px, py)
            r = 14 + 6 * t + (2 if push else 0)
            front += thumb_svg(c, deg=-8 - body_rot(g), r=r, seed=190)
            if push:
                front += motion_lines((c[0] + 12, c[1] - 10), 40, spread=30, r0=22, length=10, n=3, w=4.2)
        if sp:
            k = {1: 0.6, 2: 0.9, 3: 1.1}[sp]
            c = F(poses, g, 420, 150)
            front += sparkle((c[0] + 20, c[1] + 40), 14 * k) + star_svg((c[0] - 300, c[1] + 20), 10 * k, deg=15 * i, lw=2.6)
            texts.append(("讚！", (c[0] + 6, c[1] - 4 * (i % 2)), 10, 34 * (0.75 + 0.25 * k), (230, 82, 60, 255)))
        frames.append(FR(poses, lab, gk, face, front, texts=texts))
    return frames


def face_clap(poses):
    # 兩隻小肉掌在身前拍：分開（gap 大）→ 合起來（拍到、衝擊線＋「啪」）
    gaps = [None, 0.9, 0.0, 0.8, 0.0, 0.8, 0.0, 0.8, 0.0, 0.7, 0.9, None]
    labs = ["待機", "肉掌張開", "啪！", "張開", "啪！", "張開", "啪！（最用力）", "張開", "啪！", "慢下來", "肉掌放下", "回待機"]
    frames = []
    for i, gp in enumerate(gaps):
        hit = gp == 0.0
        gk = dict(h=0.975 if hit else 1.015, w=1.015 if hit else 0.99, lag=-0.02 if hit else 0.02)
        if i in (0, 11):
            gk = dict(h=0.995) if i == 11 else dict()
        g = base_geom(poses, 0, **gk)
        if i in (0, 11):
            face = dict()
        elif hit:
            face = dict(eyes="happy", mouth="open_l" if i == 6 else "open_m", blush="soft")
        else:
            face = dict(eyes="shine" if 2 < i < 10 else "dot", mouth="w")
        front = ""
        texts = []
        if gp is not None:
            cx, cy = 256, 380
            half = 10 + 42 * gp
            for side in (-1, 1):
                c = F(poses, g, cx + side * half, cy - (8 if hit else 0))
                deg = (0 if side < 0 else 180) - body_rot(g)
                front += paw_svg(c, deg, r=17, squash=0.86, seed=210 + side, open_side=deg + 180)
            if hit:
                c = F(poses, g, cx, cy - 8)
                front += motion_lines((c[0], c[1] - 10), 90, spread=34, r0=22, length=12, n=3, w=4.6)
                front += motion_lines((c[0] - 18, c[1] + 4), 200, spread=30, r0=18, length=10, n=2, w=4.2) + \
                    motion_lines((c[0] + 18, c[1] + 4), -20, spread=30, r0=18, length=10, n=2, w=4.2)
                t = F(poses, g, 70 if i % 4 == 2 else 440, 160)
                texts.append(("啪！", t, -12 if i % 4 == 2 else 12, 38 if i == 6 else 30, (42, 22, 16, 255)))
                front += star_svg(F(poses, g, 440 if i % 4 == 2 else 70, 180), 10, deg=20 * i, lw=2.6)
        frames.append(FR(poses, labs[i], gk, face, front, texts=texts))
    return frames


def face_bow(poses):
    # 鞠躬：頭往前壓（lag 負、身體壓扁、往前傾）＋兩隻肉掌合在身前；起身後「謝謝」＋小花
    seq = [
        ("待機", dict(), dict(), 0, 0),
        ("肉掌合在身前", dict(h=0.995), dict(eyes="dot", mouth="w"), 1, 0),
        ("開始鞠躬", dict(h=0.96, w=1.02, lag=-0.08, rot=2), dict(eyes="happy", mouth="w"), 1, 0),
        ("鞠到最低", dict(h=0.88, w=1.06, lag=-0.18, rot=3), dict(eyes="happy", mouth="w"), 1, 1),
        ("停一下（謝謝）", dict(h=0.875, w=1.065, lag=-0.19, rot=3), dict(eyes="happy", mouth="w"), 1, 1),
        ("起身", dict(h=0.95, w=1.03, lag=-0.08, rot=1), dict(eyes="happy", mouth="w"), 1, 0),
        ("抬頭（微笑）", dict(h=1.02, w=0.99, lag=0.04), dict(eyes="happy", mouth="open_m", blush="soft"), 1, 2),
        ("謝謝！小花冒出", dict(h=1.01, lag=0.02), dict(eyes="happy", mouth="open_s", blush="soft"), 1, 3),
        ("小花晃", dict(h=1.0, rot=-2), dict(eyes="dot", mouth="w", blush="soft"), 1, 4),
        ("小花晃（另一邊）", dict(h=1.0, rot=2), dict(eyes="dot", mouth="w", blush="soft"), 1, 5),
        ("肉掌放下", dict(h=0.99), dict(eyes="dot", mouth="w"), 0, 6),
        ("回待機", dict(h=0.995), dict(), 0, 0),
    ]
    frames = []
    for i, (lab, gk, face, paws, st) in enumerate(seq):
        g = base_geom(poses, 0, **gk)
        front = ""
        texts = []
        if paws:
            for side in (-1, 1):
                c = F(poses, g, 256 + side * 14, 372)
                deg = (0 if side < 0 else 180) - body_rot(g)
                front += paw_svg(c, deg, r=16, squash=0.86, seed=230 + side, open_side=deg + 180)
        if st == 1:
            front += arcs(F(poses, g, 256, 140), 90, r=20, n=2, w=4.2)
        if st >= 2 and st <= 6:
            k = {2: 0.5, 3: 1.0, 4: 1.0, 5: 1.0, 6: 0.7}[st]
            front += flower_svg(F(poses, g, 96, 170), 1.0 * k, deg=15 * i) + flower_svg(F(poses, g, 420, 160), 0.8 * k, deg=-15 * i)
            front += heart_svg(F(poses, g, 450, 230), 8 * k, 12)
            if st >= 3:
                c = F(poses, g, 256, 112)
                texts.append(("謝謝！", (c[0], c[1] - 10 - 3 * (i % 2)), -4 + 8 * (i % 2) * 0.5, 40 * (0.85 + 0.15 * k), (232, 96, 124, 255)))
        frames.append(FR(poses, lab, gk, face, front, texts=texts))
    return frames


def bulb_svg(c, k=1.0, lit=True):
    bulb = smooth_closed(jitter([(c[0] + 18 * k * math.cos(a), c[1] - 4 + 20 * k * math.sin(a))
                                 for a in np.linspace(0, 2 * math.pi, 12, endpoint=False)], 0.5, 4))
    s = shape(bulb, STAR if lit else "#F3EEE6", lw=4.4)
    s += shape(smooth_closed(rrect_pts(c[0], c[1] + 22 * k, 16 * k, 10 * k, 3, 1, 2)), "#CFC6BD", lw=3.6)
    s += brush(bez((c[0] - 6, c[1]), (c[0] - 3, c[1] - 8), (c[0] + 3, c[1] - 8), (c[0] + 6, c[1]), 8), 3.2, 3.2,
               STAR_DK if lit else "#B9AFA4")
    out = f'<g transform="rotate(10,{f(c[0])},{f(c[1])})">{s}</g>'
    if lit:
        out += motion_lines((c[0] + 2, c[1] - 4), 90, spread=42, r0=28 * k, length=10, n=3, w=4.4)
    return out


def face_thinking_bulb(poses):
    seq = [
        ("待機", dict(), dict(), 0, 0),
        ("往上看（想）", dict(lag=0.04, rot=-3), dict(eyes="dot", mouth="o", look=(5, -7)), 1, 0),
        ("點點點", dict(lag=0.05, rot=-4), dict(eyes="dot", mouth="w", look=(-4, -8)), 2, 0),
        ("燈泡冒出（還沒亮）", dict(lag=0.06, rot=-4), dict(eyes="dot", mouth="o", look=(4, -8)), 3, 0),
        ("叮！燈泡亮", dict(h=1.04, lag=-0.03), dict(eyes="shine", mouth="open_l", brows="up"), 4, 0),
        ("懂了！", dict(h=1.02), dict(eyes="shine", mouth="open_m", brows="up"), 4, 0),
        ("點頭（下）", dict(h=0.95, w=1.025, lag=-0.11), dict(eyes="happy", mouth="w"), 5, 1),
        ("回來", dict(h=1.015, lag=0.03), dict(eyes="happy", mouth="open_s"), 5, 0),
        ("再點頭（下）", dict(h=0.95, w=1.025, lag=-0.11), dict(eyes="happy", mouth="w"), 5, 1),
        ("回來（嗯！）", dict(h=1.015, lag=0.03), dict(eyes="shine", mouth="open_s", blush="soft"), 6, 0),
        ("燈泡淡掉", dict(h=1.0), dict(eyes="dot", mouth="w"), 7, 0),
        ("回待機", dict(h=0.995), dict(), 0, 0),
    ]
    frames = []
    for i, (lab, gk, face, st, nod) in enumerate(seq):
        g = base_geom(poses, 0, **gk)
        front = ""
        texts = []
        c = F(poses, g, 400, 104)
        if st in (1, 2):
            front += dots_svg((c[0] - 20, c[1] + 8), st + 1 if st == 2 else 1)
        if st == 3:
            front += bulb_svg(c, 0.85, lit=False)
        if st in (4, 5, 6):
            front += bulb_svg(c, 1.05 if st == 4 else 0.95, lit=True)
        if st == 7:
            front += f'<g opacity="0.45">{bulb_svg(c, 0.8, lit=True)}</g>'
        if st == 4:
            texts.append(("叮！", (c[0] - 70, c[1] - 6), -8, 30, (42, 22, 16, 255)))
        if nod:
            front += arcs(F(poses, g, 256, 118), 90, r=18, n=2, w=4.2)
        if st in (5, 6) and not nod:
            t = F(poses, g, 90, 150)
            texts.append(("嗯！", t, -10, 30, (42, 22, 16, 255)))
        frames.append(FR(poses, lab, gk, face, front, texts=texts))
    return frames


CLIPS = {
    "face_relief": ("表情・鬆一口氣（憋氣→哈氣→軟趴趴）", face_relief, [180, 130, 150, 120, 120, 160, 130, 130, 110, 140, 120, 160]),
    "face_cool": ("表情・戴小墨鏡（從天而降、鏡片閃光）", face_cool, [160, 90, 70, 120, 130, 140, 140, 120, 130, 110, 120, 160]),
    "face_shy": ("表情・害羞摀臉（小肉掌、指縫偷看）", face_shy, [160, 120, 90, 120, 110, 110, 180, 100, 130, 100, 120, 160]),
    "face_determined": ("表情・握拳加油（鬥志火焰）", face_determined, [160, 110, 110, 100, 90, 100, 90, 120, 120, 120, 110, 160]),
    "face_curious": ("表情・好奇湊近（歪頭、湊到鏡頭、嗅嗅）", face_curious, [160, 120, 130, 100, 130, 100, 100, 110, 150, 100, 110, 160]),
    "face_surprise_happy": ("表情・驚喜張大嘴（跳起、彩帶）", face_surprise_happy, [160, 90, 90, 90, 100, 100, 100, 90, 90, 120, 110, 160]),
    "face_thumbs": ("表情・比讚（小肉掌在身前）", face_thumbs, [160, 100, 110, 130, 100, 150, 120, 110, 140, 100, 100, 160]),
    "face_clap": ("表情・拍手（小肉掌、啪啪）", face_clap, [160, 90, 90, 80, 90, 80, 110, 80, 90, 110, 110, 160]),
    "face_bow": ("表情・鞠躬謝謝（起身冒小花）", face_bow, [160, 110, 120, 140, 220, 120, 120, 140, 120, 120, 110, 160]),
    "face_thinking_bulb": ("表情・思考後點頭（燈泡亮、嗯嗯）", face_thinking_bulb, [160, 150, 150, 140, 120, 110, 90, 100, 90, 120, 120, 160]),
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
    idx_path = out / "index_f.json"
    only = [x for x in a.only.split(",") if x]
    font = BA.HUNINN
    mine = {}
    for key, (name, fn, durs) in CLIPS.items():
        if only and key not in only:
            continue
        frs = fn(poses)
        assert len(frs) == len(durs) == 12, key
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
        sheet12(imgs, [f"{j+1:02d} {fr['label']}" for j, fr in enumerate(frs)], rd / "sheet_12.png")
        imgs[0].save(rd / "anim.webp", save_all=True, append_images=imgs[1:], duration=durs, loop=0,
                     lossless=False, quality=88, method=6)
        imgs[0].save(out / key / "anim.gif", save_all=True, append_images=imgs[1:], duration=durs, loop=0, disposal=2)
        C.write_storyboard(rd, key, name, frs, durs, "表情")
        txt = (rd / "storyboard.md").read_text(encoding="utf-8").replace(
            "- 需求：Andy 2026-10-10「幫我在影片中新增多點 GIF 圖", "- 需求：Andy 第 3 版（v3_brief 第 12 條）「表情、情境、道具要更豐富，做出來的要存成圖檔以後使用」；延續 2026-10-10「幫我在影片中新增多點 GIF 圖").replace(
            "bibi_faces_c.py", "bibi_faces_f.py")
        (rd / "storyboard.md").write_text(txt, encoding="utf-8")
        arr = [np.asarray(i).astype(int) for i in imgs]
        diffs = [int(np.abs(arr[k] - arr[(k + 1) % 12]).sum() // 1000) for k in range(12)]
        mine[key] = {"name": name, "size": [SIZE, SIZE], "frames": paths, "durations_ms": durs,
                     "labels": [fr["label"] for fr in frs], "adjacent_diff_k": diffs,
                     "scene": {"scale": BA.SCALE, "center_x": BA.CX, "ground_y": BA.GROUND},
                     "gif": str((out / key / "anim.gif").resolve()),
                     "webp": str((rd / "anim.webp").resolve()), "sheet": str((rd / "sheet_12.png").resolve())}
        print(key, "最小相鄰差", min(diffs), "→", rd, flush=True)
    index = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else {}
    index.update(mine)
    idx_path.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
