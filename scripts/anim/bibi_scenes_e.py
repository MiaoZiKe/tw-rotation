"""動畫設計單位：吉祥物「比比」E 批 12 個情境道具動畫，每組 12 格、512×512、透明。

為什麼有這支
------------
Andy 宣傳影片第 3 版（docs/marketing/video_1010/v3_brief.md 第 12 條）：「表情、情境、道具要更豐富，
做出來的表情、情境、道具要存成圖檔以後使用」。這批配合新分鏡會用到的頁面：
鬧鐘（省時間）、時鐘快轉（30 分變 3 分）、燈泡（原來如此）、亂紙進資料夾（統整資料）、地球＋新聞卡、
火苗＋溫度計（題材熱度）、星星收藏（自選清單）、獎盃＋1～5 名台階（ETF 前五名）、沙漏＋舊照片（週期統計）、
火箭（持續進步）、許願瓶（會員許願）、魔法方框（框住重點轉場，四角座標每格寫進索引）。

規格
----
- 比比本體＝原圖 `site/brand/src/support_anim_1009.gif` 的像素網格變形（沿用 bibi_actions／pose_tween），不重畫。
  表情只動眼睛那一小塊：用眼睛外圈的實際毛色蓋掉黑點，再補畫偏移的黑點／開心弧線／放鬆弧線。
- 道具用 SVG 三次 Bézier，4 倍繪製再 LANCZOS 縮回；描邊 #1A0907、粗細跟原圖一致。
- 舉牌退件教訓：道具一律懸空或放在身前地上，不畫從身體長出來的手臂，手只露小肉掌。
- 場景座標跟其他組相同：身體縮 0.75、中心 x=248、腳底 y=482。
- 只 import bibi_actions／pose_tween 的函式，不改那兩支（也不碰 B 批 bibi_scenes_b.py）。

用法
----
    BIBI_SIGN_FONT=<jf-openhuninn-2.1.ttf> python scripts/anim/bibi_scenes_e.py \
        --out <scratchpad>/bibi --repo-out docs/anim [--only alarm,clock]
輸出：<out>/<名>/frames/frame_01.png…、<repo-out>/bibi_<名>/sheet_12.png、anim.webp；<out>/index_e.json。
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
import bibi_actions as BA  # noqa: E402  （import 時 pose_tween.SS 已設成 4）
import pose_tween  # noqa: E402
from bibi_actions import (INK, FUR, SIZE, OUT_W, CX, GROUND, SCALE, EYE_L, EYE_R, HUNINN,  # noqa: E402
                          f, P, add, rot2, dirv, bez, brush, sparkle, exmark, motion_lines, paw_svg,
                          raster, base_geom, fwd, compose, sheet12, rrect, nat_geom, mini_paw,
                          GOLD, GOLD_DK, GOLD_LT, BLUE, PINK, MINT, RED, CYAN, PAPER, PAPER_SH, GRID)

LW = OUT_W * 0.85
WHITE = "#FFFFFF"
GRAY = "#9C948C"
SEPIA, SEPIA_DK = "#EAD9BC", "#B89A6E"
TXT = (42, 22, 16, 255)


# ================================================================== 表情（只動眼睛）
_FACE = {}


def face(poses, mode="dot", look=(0.0, 0.0), scale=1.0, hl=False, src=0):
    """mode：dot 黑點眼（可偏移、放大、加亮點）／happy 開心 ^ ^／relax 放鬆閉眼 ‿ ‿／star 星星眼。"""
    key = (src, mode, round(look[0], 1), round(look[1], 1), round(scale, 2), hl)
    if key in _FACE:
        return _FACE[key]
    base = poses[src]
    arr = np.asarray(base["body"]).astype(float)
    yy, xx = np.mgrid[0:arr.shape[0], 0:arr.shape[1]]
    svg = ""
    for e in (EYE_L, EYE_R):
        d2 = (xx - e[0]) ** 2 + (yy - e[1]) ** 2
        ring = (d2 >= 17 ** 2) & (d2 <= 23 ** 2) & (arr[..., :3].mean(2) > 200)
        col = "#%02X%02X%02X" % tuple(int(v) for v in np.median(arr[ring][:, :3], 0))
        svg += f'<circle cx="{f(e[0])}" cy="{f(e[1])}" r="15.5" fill="{col}"/>'
    for e in (EYE_L, EYE_R):
        c = (e[0] + look[0], e[1] + look[1])
        if mode == "dot":
            svg += f'<ellipse cx="{f(c[0])}" cy="{f(c[1])}" rx="{f(12*scale)}" ry="{f(13.5*scale)}" fill="{INK}"/>'
            if hl:
                svg += (f'<circle cx="{f(c[0]+4*scale)}" cy="{f(c[1]-5*scale)}" r="{f(4.2*scale)}" fill="#FFFFFF"/>'
                        f'<circle cx="{f(c[0]-4*scale)}" cy="{f(c[1]+4.5*scale)}" r="{f(2*scale)}" fill="#FFFFFF"/>')
        elif mode == "happy":       # ^ ^：往上拱的弧線（原圖第 2 張的瞇眼笑那種）
            svg += brush(bez((c[0] - 13, c[1] + 6), (c[0] - 6, c[1] - 10), (c[0] + 6, c[1] - 10), (c[0] + 13, c[1] + 6), 14), 7.5, 7.5)
        elif mode == "relax":       # ‿ ‿：往下彎的閉眼
            svg += brush(bez((c[0] - 13, c[1] - 2), (c[0] - 6, c[1] + 9), (c[0] + 6, c[1] + 9), (c[0] + 13, c[1] - 2), 14), 7.0, 7.0)
        elif mode == "star":
            r = 15 * scale
            pts = []
            for k in range(10):
                a = -math.pi / 2 + k * math.pi / 5
                rr = r if k % 2 == 0 else r * 0.45
                pts.append((c[0] + math.cos(a) * rr, c[1] + math.sin(a) * rr))
            d = "M " + " L ".join(P(p) for p in pts) + " Z"
            svg += f'<path d="{d}" fill="{GOLD}" stroke="{INK}" stroke-width="3.2" stroke-linejoin="round"/>'
    ov = raster(svg).resize((SIZE, SIZE), Image.LANCZOS)
    body = base["body"].copy()
    a = body.getchannel("A")
    body = Image.alpha_composite(body, ov)
    body.putalpha(a)
    out = dict(base); out["body"] = body
    _FACE[key] = out
    return out


# ================================================================== 小工具
def shape(d, fill, lw=LW, stroke=INK, extra=""):
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{f(lw)}" stroke-linejoin="round" stroke-linecap="round" {extra}/>'


def poly_d(pts, close=True):
    return "M " + " L ".join(P(p) for p in pts) + (" Z" if close else "")


def blob_d(c, rx, ry, seed=0, wob=0.06, n=8, deg=0.0):
    """不規則圓（Catmull-Rom → 三次 Bézier），手繪感。"""
    rng = np.random.default_rng(seed)
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        j = 1 + rng.uniform(-wob, wob)
        pts.append(add(c, rot2((math.cos(a) * rx * j, math.sin(a) * ry * j), deg)))
    return smooth_closed(pts)


def smooth_closed(pts):
    n = len(pts)
    d = f"M {P(pts[0])} "
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f"C {P(c1)} {P(c2)} {P(p2)} "
    return d + "Z"


def g_op(svg, op):
    return f'<g opacity="{op:.3f}">{svg}</g>' if op < 0.999 else svg


def sweat(c, s=1.0):
    d = f"M {P((c[0], c[1]-12*s))} C {P((c[0]+9*s, c[1]-1*s))} {P((c[0]+8*s, c[1]+9*s))} {P((c[0], c[1]+9*s))} C {P((c[0]-8*s, c[1]+9*s))} {P((c[0]-9*s, c[1]-1*s))} {P((c[0], c[1]-12*s))} Z"
    return shape(d, "#8FD3F5", 3.0) + f'<circle cx="{f(c[0]-3*s)}" cy="{f(c[1]+2*s)}" r="{f(2*s)}" fill="#FFFFFF"/>'


def glow_stroke(d, col=GOLD, core="#FFF7D6", w=7.0):
    """發光線：外圈半透明粗線疊兩層＋白芯（cairosvg 不支援模糊濾鏡，用疊線做）。"""
    return (f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{f(w*3.4)}" stroke-linecap="round" stroke-linejoin="round" opacity="0.18"/>'
            f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{f(w*2.0)}" stroke-linecap="round" stroke-linejoin="round" opacity="0.35"/>'
            f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{f(w)}" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="{d}" fill="none" stroke="{core}" stroke-width="{f(w*0.4)}" stroke-linecap="round" stroke-linejoin="round"/>')


def head_top(poses, g, dx=0):
    return fwd(poses, g, 256 + dx, 135)


def fr_(poses, g, label, pose=None, **kw):
    d = {"g": g, "label": label, "pose": pose or face(poses)}
    d.update(kw)
    return d


def T(txt, c, px, deg=0.0, color=TXT, stroke=0.4):
    return (txt, c, deg, px, HUNINN, color, stroke)


# ================================================================== 1. 鬧鐘
def alarm_svg(c, deg, ringing, stopped=False):
    R = 34
    out = ""
    for sgn in (-1, 1):           # 兩隻腳
        a = add(c, rot2((sgn * 20, 28), deg)); b = add(c, rot2((sgn * 28, 44), deg))
        out += f'<path d="M {P(a)} L {P(b)}" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>'
    for sgn in (-1, 1):           # 兩顆鈴
        bc = add(c, rot2((sgn * 24, -30), deg + sgn * (8 if ringing else 0)))
        out += shape(blob_d(bc, 15, 11, seed=3 + sgn, deg=deg + sgn * 35), GOLD)
    hm = add(c, rot2((0, -40), deg))
    out += f'<path d="M {P(add(c, rot2((0,-30),deg)))} L {P(hm)}" stroke="{INK}" stroke-width="5" stroke-linecap="round"/>'
    out += f'<circle cx="{f(hm[0])}" cy="{f(hm[1])}" r="6.5" fill="{RED}" stroke="{INK}" stroke-width="3.2"/>'
    out += shape(blob_d(c, R, R, seed=9, wob=0.03, deg=deg), RED)
    out += shape(blob_d(c, R * 0.74, R * 0.74, seed=4, wob=0.02), WHITE, 3.2)
    for k in range(12):
        a = math.radians(k * 30)
        p0 = (c[0] + math.cos(a) * R * 0.62, c[1] + math.sin(a) * R * 0.62)
        p1 = (c[0] + math.cos(a) * R * 0.52, c[1] + math.sin(a) * R * 0.52)
        out += f'<path d="M {P(p0)} L {P(p1)}" stroke="{INK}" stroke-width="{2.4 if k % 3 else 3.4}" stroke-linecap="round"/>'
    for ang, L, w in ((-60, R * 0.42, 4.2), (90 if not stopped else -90, R * 0.55, 3.2)):
        e = add(c, dirv(ang + deg * -1), L)
        out += f'<path d="M {P(c)} L {P(e)}" stroke="{INK}" stroke-width="{w}" stroke-linecap="round"/>'
    out += f'<circle cx="{f(c[0])}" cy="{f(c[1])}" r="3.4" fill="{INK}"/>'
    return out


def scene_alarm(poses):
    C = (436, 432)
    plan = [
        ("鬧鐘響！比比嚇一跳", 1, dict(h=1.04, w=0.97, bottom=-6, lag=-0.06), ("dot", (6, -1), 1.3, True)),
        ("鈴鈴鈴（左晃）", 2, dict(h=1.02, rot=1), ("dot", (7, 0), 1.25, True)),
        ("鈴鈴鈴（右晃）", 3, dict(h=1.0, rot=2), ("dot", (7, 0), 1.2, True)),
        ("吵死了…往鬧鐘靠", 2, dict(rot=5, cx=6, lag=-0.03), ("dot", (8, 1), 1.0, False)),
        ("身體壓過去", 3, dict(rot=9, cx=14, h=0.98, lag=0.02), ("dot", (8, 2), 1.0, False)),
        ("小肉掌按下去", 0, dict(rot=10, cx=16, h=0.96, w=1.03, lag=0.03), ("happy", (0, 0), 1, False)),
        ("叮——停了", 0, dict(rot=8, cx=12, h=0.98), ("happy", (0, 0), 1, False)),
        ("回正", 0, dict(rot=3, cx=4), ("dot", (2, 0), 1.0, False)),
        ("鬆一口氣", 0, dict(h=0.97, w=1.03), ("relax", (0, 0), 1, False)),
        ("省下時間、開心", 0, dict(h=1.02, lag=-0.04), ("happy", (0, 0), 1, False)),
        ("站好", 0, dict(), ("dot", (0, 0), 1.0, False)),
        ("…鬧鐘又要響了", 3, dict(lag=-0.02), ("dot", (6, 0), 1.05, False)),
    ]
    out = []
    for i, (lab, ring, gk, (m, lk, sc, hl)) in enumerate(plan):
        g = base_geom(poses, 0, **gk)
        shake = {1: -9, 2: 9, 3: -7}.get(ring, 0) if ring else 0
        cc = (C[0] + (shake * 0.3), C[1])
        svg = alarm_svg(cc, shake, bool(ring), stopped=(5 <= i <= 10))
        if ring:
            svg += motion_lines(add(cc, (0, -40)), 90, spread=34, r0=26, length=12, n=3) + \
                motion_lines((cc[0] - 40, cc[1] - 12), 165, spread=26, r0=6, length=11, n=2)
        if i == 0:
            svg += sweat(fwd(poses, g, 110, 210), 1.0)
        sprites = []
        if i == 5:   # 官方部件總表的小肉掌：從身體右側冒出一小截，往下按住鬧鐘
            at = BA.shoulder(poses, g, (436, 318), depth=10)
            sprites.append(BA.hand_layer(at, -18, 46, "R"))
        if i == 6:
            svg += sparkle((C[0] + 34, C[1] - 58), 11) + sparkle((C[0] - 40, C[1] - 54), 8)
        if i == 9:
            svg += sparkle((130, 200), 10) + sparkle((360, 190), 8)
        out.append(fr_(poses, g, lab, face(poses, m, lk, sc, hl), front=svg, sprites=sprites))
    return out


# ================================================================== 2. 時鐘快轉
def clock_svg(c, R, mins, blur=0.0):
    out = shape(blob_d(c, R + 7, R + 7, seed=21, wob=0.015), BLUE)
    out += shape(blob_d(c, R, R, seed=22, wob=0.01), WHITE, 3.4)
    for k in range(12):
        a = math.radians(k * 30 - 90)
        p0 = (c[0] + math.cos(a) * R * 0.86, c[1] + math.sin(a) * R * 0.86)
        p1 = (c[0] + math.cos(a) * R * 0.74, c[1] + math.sin(a) * R * 0.74)
        out += f'<path d="M {P(p0)} L {P(p1)}" stroke="{INK}" stroke-width="{3.6 if k % 3 == 0 else 2.4}" stroke-linecap="round"/>'
    am = math.radians(mins * 6 - 90)
    ah = math.radians((mins / 60) * 30 - 90 + 300)
    if blur > 0:   # 快轉：分針掃過的扇形殘影
        a0 = am - math.radians(blur)
        pts = [c] + [(c[0] + math.cos(a0 + (am - a0) * t) * R * 0.78, c[1] + math.sin(a0 + (am - a0) * t) * R * 0.78) for t in np.linspace(0, 1, 12)]
        out += f'<path d="{poly_d(pts)}" fill="{BLUE}" opacity="0.22"/>'
    out += f'<path d="M {P(c)} L {P((c[0]+math.cos(ah)*R*0.48, c[1]+math.sin(ah)*R*0.48))}" stroke="{INK}" stroke-width="6" stroke-linecap="round"/>'
    out += f'<path d="M {P(c)} L {P((c[0]+math.cos(am)*R*0.76, c[1]+math.sin(am)*R*0.76))}" stroke="{RED}" stroke-width="4.4" stroke-linecap="round"/>'
    out += f'<circle cx="{f(c[0])}" cy="{f(c[1])}" r="4.5" fill="{INK}"/>'
    return out


def scene_clock(poses):
    C, R = (396, 128), 54
    # 分針位置（分鐘）：前 6 格快轉一大圈多，第 7 格停在 3 分
    mins = [0, 52, 104, 156, 208, 300, 363, 363, 363, 363, 363, 363]
    blur = [0, 150, 160, 160, 160, 170, 30, 0, 0, 0, 0, 0]
    plan = [
        ("盯著時鐘", dict(lag=-0.05), ("dot", (6, -6), 1.0, False)),
        ("指針開始快轉", dict(lag=-0.06), ("dot", (7, -6), 1.1, False)),
        ("轉轉轉", dict(lag=-0.06, rot=1), ("dot", (8, -5), 1.15, True)),
        ("越轉越快", dict(lag=-0.07, rot=2, h=1.01), ("dot", (8, -6), 1.2, True)),
        ("眼花了", dict(lag=-0.06, rot=-1), ("dot", (6, -6), 1.2, True)),
        ("咻——", dict(lag=-0.06, h=1.02), ("dot", (8, -6), 1.15, True)),
        ("停！只要 3 分鐘", dict(h=1.04, w=0.97, bottom=-6, lag=-0.07), ("dot", (6, -5), 1.3, True)),
        ("放鬆～", dict(h=0.97, w=1.03), ("relax", (0, 0), 1, False)),
        ("融化般放鬆", dict(h=0.94, w=1.05, lag=0.04), ("relax", (0, 0), 1, False)),
        ("舒服晃一下", dict(h=0.95, w=1.045, rot=-2, lag=0.03), ("relax", (0, 0), 1, False)),
        ("再晃一下", dict(h=0.955, w=1.04, rot=2, lag=0.03), ("relax", (0, 0), 1, False)),
        ("睜眼回到時鐘", dict(h=0.99, lag=-0.03), ("dot", (5, -5), 1.0, False)),
    ]
    out = []
    for i, (lab, gk, (m, lk, sc, hl)) in enumerate(plan):
        g = base_geom(poses, 0, **gk)
        svg = clock_svg(C, R, mins[i], blur[i])
        texts = []
        if 1 <= i <= 5:
            svg += motion_lines((C[0] - R - 10, C[1]), 180, spread=30, r0=4, length=12, n=3)
        if i == 0 or 1 <= i <= 5:
            texts.append(T("30 分鐘", (C[0], C[1] + R + 28), 26, 0, (120, 110, 100, 255)))
        if i >= 6:
            k = 1.25 if i == 6 else 1.0
            texts.append(T("3 分鐘", (C[0], C[1] + R + 30), 30 * k, -4, (232, 80, 74, 255), 0.6))
            if i <= 8:
                svg += sparkle((C[0] - 66, C[1] + R + 22), 9) + sparkle((C[0] + 66, C[1] + R + 12), 7)
        if 7 <= i <= 10:
            top = head_top(poses, g)
            for k2 in range(2):     # 放鬆的小波浪線
                x = top[0] - 90 + k2 * 190; y = top[1] + 40
                svg += brush(bez((x - 12, y), (x - 4, y - 8), (x + 4, y + 8), (x + 12, y), 10), 4.4, 4.0)
        out.append(fr_(poses, g, lab, face(poses, m, lk, sc, hl), front=svg, texts=texts))
    return out


# ================================================================== 3. 燈泡
def bulb_svg(c, k, lit, deg=0.0):
    s = k
    Tf = lambda p: add(c, rot2((p[0] * s, p[1] * s), deg))  # noqa: E731
    glass = (f"M {P(Tf((-13,22)))} C {P(Tf((-15,10)))} {P(Tf((-30,2)))} {P(Tf((-30,-16)))} "
             f"C {P(Tf((-30,-36)))} {P(Tf((-16,-48)))} {P(Tf((0,-48)))} C {P(Tf((16,-48)))} {P(Tf((30,-36)))} {P(Tf((30,-16)))} "
             f"C {P(Tf((30,2)))} {P(Tf((15,10)))} {P(Tf((13,22)))} Z")
    out = ""
    if lit > 0:
        out += f'<circle cx="{f(Tf((0,-16))[0])}" cy="{f(Tf((0,-16))[1])}" r="{f(56*s)}" fill="#FFF3B0" opacity="{0.45*lit:.2f}"/>'
        for a in range(-150, 31, 30):
            v = dirv(-a - 90 + 90)
            p0 = add(Tf((0, -16)), v, 44 * s); p1 = add(Tf((0, -16)), v, (58 + 6 * lit) * s)
            out += brush([p0, p1], 6 * s, 5 * s, GOLD_DK)
    fill = "#FFE27A" if lit > 0.5 else ("#FFF6D0" if lit > 0 else "#F4F1EC")
    out += shape(glass, fill, LW * 0.9)
    fil = Tf((-8, 6)), Tf((-6, -10)), Tf((0, -2)), Tf((6, -10)), Tf((8, 6))
    out += f'<path d="{poly_d(fil, False)}" fill="none" stroke="{GOLD_DK if lit > 0.5 else GRAY}" stroke-width="2.8" stroke-linejoin="round"/>'
    out += shape(poly_d([Tf((-13, 22)), Tf((13, 22)), Tf((12, 36)), Tf((-12, 36))]), "#B8B2AA", LW * 0.8)
    for yy in (27, 32):
        out += f'<path d="M {P(Tf((-12,yy)))} L {P(Tf((12,yy)))}" stroke="{INK}" stroke-width="2.4"/>'
    out += shape(poly_d([Tf((-6, 36)), Tf((6, 36)), Tf((3, 42)), Tf((-3, 42))]), INK, 2)
    hl = Tf((-18, -26)), Tf((-16, -36)), Tf((-8, -41))
    out += brush(list(hl), 4.4 * s, 3 * s, WHITE)
    return out


def scene_bulb(poses):
    plan = [
        ("想啊想", 0, dict(lag=-0.05, rot=-3), ("dot", (-4, -6), 1.0, False), 0),
        ("還在想", 0, dict(lag=-0.05, rot=-4, h=0.99), ("dot", (-5, -7), 1.0, False), 1),
        ("想不通…", 0, dict(lag=-0.04, rot=-3, h=0.98), ("dot", (-4, -6), 1.0, False), 2),
        ("燈泡冒出來", 0.0, dict(lag=-0.05, rot=-1), ("dot", (0, -6), 1.05, False), 3),
        ("叮！燈泡亮了", 1.0, dict(h=1.05, w=0.96, bottom=-10, lag=-0.08), ("dot", (0, -5), 1.3, True), 0),
        ("原來如此！", 1.0, dict(h=1.02, bottom=-4, lag=-0.05), ("dot", (0, -5), 1.25, True), 0),
        ("落地", 1.0, dict(h=0.96, w=1.035), ("happy", (0, 0), 1, False), 0),
        ("開心點頭", 1.0, dict(h=1.01, lag=0.04), ("happy", (0, 0), 1, False), 0),
        ("懂了～", 1.0, dict(h=1.0), ("happy", (0, 0), 1, False), 0),
        ("燈泡慢慢暗", 0.5, dict(), ("dot", (0, -3), 1.0, False), 0),
        ("燈泡縮小", 0.0, dict(), ("dot", (-2, -4), 1.0, False), 0),
        ("又開始想", 0, dict(lag=-0.04, rot=-2), ("dot", (-4, -6), 1.0, False), 0),
    ]
    out = []
    for i, (lab, lit, gk, (m, lk, sc, hl), dots) in enumerate(plan):
        g = base_geom(poses, 0, **gk)
        top = head_top(poses, g)
        svg = ""
        bk = {3: 0.7, 10: 0.6, 11: 0.0}.get(i, 1.0 if 4 <= i <= 9 else 0)
        if bk > 0:
            svg += bulb_svg((top[0] + 6, top[1] - 62 - (6 if i == 4 else 0)), bk * (1.15 if i == 4 else 1.0), lit)
        if dots:
            for k in range(dots):
                p = (top[0] + 64 + k * 16, top[1] - 6 - k * 10)
                svg += f'<circle cx="{f(p[0])}" cy="{f(p[1])}" r="{4+k}" fill="{INK}"/>'
        if i == 4:
            svg += sparkle((top[0] - 92, top[1] - 30), 11) + sparkle((top[0] + 96, top[1] - 50), 9)
        out.append(fr_(poses, g, lab, face(poses, m, lk, sc, hl), front=svg))
    return out


# ================================================================== 4. 亂紙飛進資料夾
def paper_svg(c, deg, w=46, h=58, seed=0):
    out = shape(rrect(c[0], c[1], w, h, 5, deg, 0.8), PAPER, LW * 0.7)
    for k in range(4):
        y = -h / 2 + 12 + k * 10
        a = add(c, rot2((-w / 2 + 8, y), deg)); b = add(c, rot2((w / 2 - 8 - (12 if k == 3 else 0), y), deg))
        out += f'<path d="M {P(a)} L {P(b)}" stroke="{GRID}" stroke-width="2.6" stroke-linecap="round"/>'
    return out


def folder_back(c, w=168, h=104):
    x0, y0 = c[0] - w / 2, c[1] - h / 2
    d = (f"M {P((x0, y0+10))} L {P((x0+48, y0+10))} L {P((x0+58, y0-4))} L {P((x0+92, y0-4))} L {P((x0+100, y0+10))} "
         f"L {P((x0+w, y0+10))} L {P((x0+w, y0+h))} L {P((x0, y0+h))} Z")
    return shape(d, "#E9B656")


def folder_front(c, w=168, h=104, open_=1.0):
    x0, y0 = c[0] - w / 2, c[1] - h / 2
    top = y0 + 28 + (1 - open_) * -16
    d = f"M {P((x0-4, top))} L {P((x0+w+4, top))} L {P((x0+w, y0+h))} L {P((x0, y0+h))} Z"
    return shape(d, "#F6CF78")


def scene_folder(poses):
    FC = (CX + 4, 424)
    rng = np.random.default_rng(5)
    starts = [((70, 120), -25), ((420, 90), 20), ((110, 250), 35), ((440, 230), -30), ((250, 70), 10)]
    t0 = [0, 1, 2, 3, 4]      # 第幾格開始飛
    out = []
    labs = ["一堆亂紙到處飛", "紙往資料夾飛", "一張進去了", "又一張", "再一張", "最後一張", "全部收好",
            "整理好了！打勾", "開心", "拍拍資料夾", "站好", "紙又冒出來"]
    for i in range(12):
        gk = {7: dict(h=1.04, w=0.97, bottom=-8, lag=-0.06), 8: dict(h=0.97, w=1.03)}.get(i, dict(lag=-0.02))
        g = base_geom(poses, 0, **gk)
        if i <= 1:
            fc = face(poses, "dot", (0, -5), 1.15, True)
        elif i <= 6:
            fc = face(poses, "dot", (0, 4), 1.0, False)
        elif i <= 9:
            fc = face(poses, "happy")
        else:
            fc = face(poses)
        back = ""
        mid = folder_back(FC)
        flying = ""
        stacked = 0
        for k, ((sx, sy), sd) in enumerate(starts):
            u = (i - t0[k]) / 3.0   # 每張花 3 格飛進去
            if i == 11:             # 第 12 格：紙從資料夾冒一點出來（接回第 1 格的亂紙）
                u = 0.0 if k < 2 else 2.0
            if u <= 0:
                jig = 6 * math.sin(i * 2.1 + k)
                flying += paper_svg((sx + jig, sy + jig * 0.5), sd + jig * 2, seed=k) if (i < 11 or k < 2) else ""
            elif u < 1:
                e = BA.ease(u)
                tx, ty = FC[0] - 30 + k * 15, FC[1] - 40
                x = sx + (tx - sx) * e; y = sy + (ty - sy) * e - 60 * math.sin(math.pi * e)
                flying += paper_svg((x, y), sd * (1 - e) + 360 * e * (1 if k % 2 else -1) * 0.25, seed=k)
            else:
                stacked += 1
        for k in range(stacked):
            mid += paper_svg((FC[0] - 30 + k * 15, FC[1] - 26 - k * 2), (k - 2) * 3, seed=k)
        mid += folder_front(FC)
        mid += f'<path d="M {P((FC[0]-34, FC[1]+18))} L {P((FC[0]+34, FC[1]+18))}" stroke="#D69A33" stroke-width="3" stroke-linecap="round"/>'
        front = flying
        pl = (FC[0] - 70, FC[1] - 18); pr = (FC[0] + 70, FC[1] - 18)
        front += mini_paw(pl, 11, 100, i) + mini_paw(pr, 11, 80, i + 3)
        if 7 <= i <= 9:
            ck = (FC[0] + 96, FC[1] - 76)
            front += f'<circle cx="{f(ck[0])}" cy="{f(ck[1])}" r="22" fill="{MINT}" stroke="{INK}" stroke-width="{f(LW)}"/>'
            front += brush([(ck[0] - 10, ck[1]), (ck[0] - 3, ck[1] + 8), (ck[0] + 11, ck[1] - 8)], 6, 6, WHITE)
            front += sparkle((FC[0] - 100, FC[1] - 80), 10)
        if i == 9:
            front = front.replace(mini_paw(pl, 11, 100, i), mini_paw((pl[0] + 6, pl[1] + 6), 11, 100, i))
        out.append(fr_(poses, g, labs[i], fc, back=back, mid=mid, front=front))
    return out


# ================================================================== 5. 地球＋新聞卡
def globe_svg(c, R, rot, cid):
    out = f'<defs><clipPath id="{cid}"><circle cx="{f(c[0])}" cy="{f(c[1])}" r="{f(R)}"/></clipPath></defs>'
    out += f'<circle cx="{f(c[0])}" cy="{f(c[1])}" r="{f(R)}" fill="#7CCBF2"/>'
    land = ""
    for lon, lat, rx, ry, seed in ((0, -20, 22, 16, 1), (70, 10, 18, 22, 2), (150, -30, 26, 12, 3), (220, 25, 20, 15, 4),
                                   (290, -5, 16, 20, 5)):
        a = math.radians(lon + rot)
        z = math.cos(a)
        if z < -0.15:
            continue
        x = c[0] + R * math.sin(a) * 0.95
        y = c[1] + lat * R / 60
        land += f'<path d="{blob_d((x, y), rx * max(0.25, z), ry, seed=seed, wob=0.18)}" fill="{MINT}" stroke="#3E9C6A" stroke-width="2"/>'
    out += f'<g clip-path="url(#{cid})">{land}'
    for k in range(-1, 2):   # 經線：跟著轉
        a = math.radians(k * 60 + rot % 60)
        rx = abs(math.sin(a)) * R
        out += f'<ellipse cx="{f(c[0])}" cy="{f(c[1])}" rx="{f(max(rx,1))}" ry="{f(R)}" fill="none" stroke="#FFFFFF" stroke-width="1.6" opacity="0.6"/>'
    for yy in (-0.45, 0, 0.45):
        out += f'<path d="M {P((c[0]-R, c[1]+yy*R))} L {P((c[0]+R, c[1]+yy*R))}" stroke="#FFFFFF" stroke-width="1.6" opacity="0.6"/>'
    out += "</g>"
    out += f'<circle cx="{f(c[0])}" cy="{f(c[1])}" r="{f(R)}" fill="none" stroke="{INK}" stroke-width="{f(LW)}"/>'
    out += brush(bez((c[0] - R * 0.7, c[1] - R * 0.3), (c[0] - R * 0.65, c[1] - R * 0.7), (c[0] - R * 0.3, c[1] - R * 0.85), (c[0] - R * 0.05, c[1] - R * 0.88), 8), 5, 3.5, WHITE)
    # 底座
    out += f'<path d="M {P((c[0]+R*0.75, c[1]-R*0.75))} C {P((c[0]+R*1.25, c[1]-R*0.2))} {P((c[0]+R*1.1, c[1]+R*0.9))} {P((c[0]+R*0.2, c[1]+R*1.12))}" fill="none" stroke="#B7774F" stroke-width="5" stroke-linecap="round"/>'
    out += shape(rrect(c[0], c[1] + R + 20, 50, 12, 5), "#B7774F", LW * 0.8)
    out += f'<path d="M {P((c[0], c[1]+R))} L {P((c[0], c[1]+R+14))}" stroke="#B7774F" stroke-width="6"/>'
    return out


CARDS = [("國際", BLUE), ("科技", PINK), ("總經", MINT)]


def scene_globe(poses):
    C, R = (398, 214), 44
    targets = [(110, 92), (250, 62), (402, 70)]
    out = []
    labs = ["地球轉著", "第一張新聞卡飛出", "飛到左上", "第二張飛出", "飛到上面", "第三張飛出", "飛到右上",
            "三張都到齊", "眼睛發亮", "卡片飄一下", "卡片飛走", "地球繼續轉"]
    for i in range(12):
        gk = {8: dict(h=1.04, w=0.97, bottom=-8, lag=-0.07), 9: dict(h=0.98, w=1.02)}.get(i, dict(lag=-0.04))
        g = base_geom(poses, 0, **gk)
        lk = [(8, -4), (6, -6), (-4, -8), (4, -8), (0, -9), (8, -6), (8, -8), (0, -8), (0, -6), (0, -6), (2, -6), (8, -4)][i]
        fc = face(poses, "dot", lk, 1.3 if i == 8 else (1.15 if i == 9 else 1.0), i in (8, 9))
        svg = globe_svg(C, R, i * 30, f"gl{i}")
        texts = []
        for k, (name, col) in enumerate(CARDS):
            u = (i - (1 + 2 * k)) / 2.0
            if i >= 10:
                u = 1 + (i - 9) * 0.5
            if u <= 0:
                continue
            e = BA.ease(min(u, 1.0))
            fly_out = max(0.0, u - 1.0)
            x = C[0] + (targets[k][0] - C[0]) * e
            y = C[1] - 20 + (targets[k][1] - C[1] + 20) * e - 30 * math.sin(math.pi * e) - fly_out * 120
            s = 0.35 + 0.65 * e
            bob = 3 * math.sin(i * 1.3 + k) if 7 <= i <= 9 else 0
            y += bob
            deg = (-8 + 8 * k) * e
            op = max(0.0, 1 - fly_out * 1.6)
            if op <= 0:
                continue
            w, h = 92 * s, 46 * s
            card = shape(rrect(x, y, w, h, 9 * s, deg, 0.6), WHITE, LW * 0.8)
            strip = add((x, y), rot2((-w / 2 + 9 * s, 0), deg))
            card += f'<path d="M {P(add(strip, rot2((0,-h/2+7*s),deg)))} L {P(add(strip, rot2((0,h/2-7*s),deg)))}" stroke="{col}" stroke-width="{f(7*s)}" stroke-linecap="round"/>'
            svg += g_op(card, op)
            if op > 0.6:
                texts.append(T(name, add((x, y), rot2((7 * s, 0), deg)), 24 * s, deg))
        if i == 8:
            svg += sparkle((C[0] - 70, C[1] - 10), 10) + sparkle((C[0] + 2, C[1] - 70), 8)
        out.append(fr_(poses, g, labs[i], fc, front=svg, texts=texts))
    return out


# ================================================================== 6. 火苗＋溫度計
def flame_svg(base, s, t):
    """火苗：外焰橘紅、內焰黃，形狀每格用不同的 Bézier 控制點（真的在搖，不是放大縮小）。"""
    sw = 6 * math.sin(t * 1.9); sw2 = 4 * math.sin(t * 2.7 + 1)
    x, y = base
    d = (f"M {P((x, y))} C {P((x-30*s, y))} {P((x-30*s, y-34*s))} {P((x-14*s, y-52*s))} "
         f"C {P((x-10*s+sw, y-66*s))} {P((x-2*s+sw, y-80*s))} {P((x+4*s+sw, y-96*s))} "
         f"C {P((x+12*s+sw2, y-76*s))} {P((x+30*s, y-60*s))} {P((x+28*s, y-30*s))} "
         f"C {P((x+28*s, y-6*s))} {P((x+16*s, y))} {P((x, y))} Z")
    d2 = (f"M {P((x, y-4*s))} C {P((x-15*s, y-4*s))} {P((x-15*s, y-24*s))} {P((x-6*s, y-36*s))} "
          f"C {P((x-2*s+sw2, y-46*s))} {P((x+2*s+sw2, y-52*s))} {P((x+4*s+sw2, y-60*s))} "
          f"C {P((x+12*s, y-44*s))} {P((x+16*s, y-30*s))} {P((x+14*s, y-16*s))} C {P((x+12*s, y-6*s))} {P((x+6*s, y-4*s))} {P((x, y-4*s))} Z")
    return shape(d, "#F2774B", LW * 0.85) + f'<path d="{d2}" fill="{GOLD}"/>'


def thermo_svg(c, level):
    x, top, bot = c[0], c[1] - 120, c[1]
    tube = rrect(x, (top + bot) / 2 - 8, 26, bot - top - 4, 13)
    out = shape(tube, WHITE)
    lv = bot - 16 - (bot - top - 40) * level
    out += f'<path d="{rrect(x, (lv + bot - 10) / 2, 12, bot - 10 - lv, 6)}" fill="{RED}"/>'
    out += shape(blob_d((x, bot), 20, 20, seed=31, wob=0.02), RED)
    out += brush([(x - 7, bot - 6), (x - 9, bot + 2)], 4, 3, "#F7A39E")
    for k in range(5):
        yy = top + 14 + k * 18
        out += f'<path d="M {P((x+13, yy))} L {P((x+22, yy))}" stroke="{INK}" stroke-width="2.6" stroke-linecap="round"/>'
    return out


def scene_fire(poses):
    levels = [0.25, 0.32, 0.42, 0.54, 0.66, 0.78, 0.88, 0.95, 0.95, 0.8, 0.55, 0.35]
    labs = ["溫度計低低的", "題材開始熱", "越來越熱", "火苗變大", "熱度上升", "好熱！", "快爆表",
            "熱到頂！冒汗", "眼睛發亮", "慢慢降溫", "再降", "回到溫溫的"]
    out = []
    for i in range(12):
        lv = levels[i]
        gk = {7: dict(h=1.04, w=0.97, bottom=-8, lag=-0.07), 8: dict(h=1.0)}.get(i, dict(lag=-0.03, rot=1 if i % 2 else -1))
        g = base_geom(poses, 0, **gk)
        if 7 <= i <= 8:
            fc = face(poses, "dot", (0, -4), 1.3, True)
        elif lv > 0.5:
            fc = face(poses, "dot", (-6 if i % 2 else 6, -3), 1.1, False)
        else:
            fc = face(poses)
        svg = thermo_svg((74, 470), lv)
        svg += flame_svg((440, 480), 0.55 + 0.6 * lv, i * 1.7)
        if lv > 0.7:
            for k in range(3):   # 熱氣
                x = 410 + k * 26; y = 360 - 60 * lv
                svg += g_op(brush(bez((x, y + 20), (x - 8, y + 10), (x + 8, y), (x, y - 12), 10), 4, 3, GRAY), 0.7)
        if i >= 6 and i <= 9:
            svg += sweat(fwd(poses, g, 425, 215), 1.0)
        if i == 7:
            svg += sparkle((150, 175), 10) + sparkle((350, 165), 8)
        out.append(fr_(poses, g, labs[i], fc, front=svg))
    return out


# ================================================================== 7. 星星收藏
def star_d(c, r, deg=0.0, inner=0.47):
    pts = []
    for k in range(10):
        a = math.radians(deg - 90 + k * 36)
        rr = r if k % 2 == 0 else r * inner
        pts.append((c[0] + math.cos(a) * rr, c[1] + math.sin(a) * rr))
    # 圓角星：用 Catmull-Rom 讓尖角稍微圓
    return smooth_closed(pts) if False else poly_d(pts)


def box_svg(c, lid):
    w, h = 132, 70
    x0, y0 = c[0] - w / 2, c[1] - h / 2
    out = shape(rrect(c[0], c[1], w, h, 10), PINK)
    out += f'<path d="M {P((c[0], y0+2))} L {P((c[0], y0+h-2))}" stroke="{GOLD}" stroke-width="12"/>'
    out += f'<path d="M {P((c[0], y0+2))} L {P((c[0], y0+h-2))}" stroke="{INK}" stroke-width="2" opacity="0.3"/>'
    # 蓋子：以左後角為軸打開
    pivot = (x0 - 4, y0)
    lid_pts = [(0, 0), (w + 8, 0), (w + 8, -20), (0, -20)]
    pts = [add(pivot, rot2(p, -lid * 70)) for p in lid_pts]
    out += shape(smooth_closed(pts) if False else poly_d(pts), "#F8BDB8")
    mid = add(pivot, rot2(((w + 8) / 2, -10), -lid * 70))
    out += f'<circle cx="{f(mid[0])}" cy="{f(mid[1])}" r="8" fill="{GOLD}" stroke="{INK}" stroke-width="2.6"/>'
    return out


def scene_star_save(poses):
    BC = (CX + 4, 438)
    path = [(80, 110), (130, 70), (210, 80), (262, 160), (BC[0], BC[1] - 50)]
    labs = ["盒子關著", "星星出現", "星星飄過來", "盒子打開", "星星飛向盒子", "咻——掉進去", "蓋上！",
            "收藏 +1", "開心", "盒子彈一下", "站好", "下一顆星星"]
    out = []
    for i in range(12):
        gk = {7: dict(h=1.04, w=0.97, bottom=-8, lag=-0.06), 8: dict(h=0.97, w=1.03)}.get(i, dict(lag=-0.02))
        g = base_geom(poses, 0, **gk)
        lid = {3: 0.6, 4: 1.0, 5: 1.0, 6: 0.15}.get(i, 0.0)
        svg = ""
        texts = []
        # 星星位置：第 2～6 格沿路徑飛
        if 1 <= i <= 5 or i == 11:
            u = (i - 1) / 4.0 if i <= 5 else 0.0
            seg = min(int(u * 4), 3); t = u * 4 - seg
            p0, p1 = path[seg], path[seg + 1]
            sp = (p0[0] + (p1[0] - p0[0]) * BA.ease(t), p0[1] + (p1[1] - p0[1]) * BA.ease(t))
            sz = 22 if i < 5 else 16
            if i == 11:
                sp, sz = path[0], 14
            star = shape(star_d(sp, sz, i * 24), GOLD, LW * 0.8)
            svg += star + sparkle((sp[0] - 26, sp[1] + 14), 6)
            look = ((sp[0] - CX) / 30, (sp[1] - 300) / 40)
            fc = face(poses, "dot", (max(-7, min(7, look[0])), max(-7, min(6, look[1]))), 1.0, False)
        elif 6 <= i <= 9:
            fc = face(poses, "happy")
        else:
            fc = face(poses)
        bounce = {7: -6, 9: -4}.get(i, 0)
        mid = box_svg((BC[0], BC[1] + bounce), lid)
        mid += mini_paw((BC[0] - 74, BC[1] - 8 + bounce), 11, 100, i) + mini_paw((BC[0] + 74, BC[1] - 8 + bounce), 11, 80, i + 1)
        if 6 <= i <= 8:
            texts.append(T("+1", (BC[0] + 92, BC[1] - 74 - (i - 6) * 8), 34, 0, (232, 80, 74, 255), 0.8))
            svg += sparkle((BC[0] - 90, BC[1] - 62), 10) + sparkle((BC[0] + 40, BC[1] - 70), 7)
        out.append(fr_(poses, g, labs[i], fc, mid=mid, front=svg, texts=texts))
    return out


# ================================================================== 8. 獎盃＋1～5 名台階
def trophy_svg(c, s, deg):
    Tf = lambda p: add(c, rot2((p[0] * s, p[1] * s), deg))  # noqa: E731
    cup = (f"M {P(Tf((-26,-30)))} L {P(Tf((26,-30)))} C {P(Tf((26,0)))} {P(Tf((14,14)))} {P(Tf((0,16)))} "
           f"C {P(Tf((-14,14)))} {P(Tf((-26,0)))} {P(Tf((-26,-30)))} Z")
    out = ""
    for sgn in (-1, 1):
        a = Tf((sgn * 25, -24)); b = Tf((sgn * 40, -18)); cc = Tf((sgn * 38, 0)); d = Tf((sgn * 18, 6))
        out += f'<path d="M {P(a)} C {P(b)} {P(cc)} {P(d)}" fill="none" stroke="{INK}" stroke-width="{f(9*s)}" stroke-linecap="round"/>'
        out += f'<path d="M {P(a)} C {P(b)} {P(cc)} {P(d)}" fill="none" stroke="{GOLD}" stroke-width="{f(4.5*s)}" stroke-linecap="round"/>'
    out += shape(cup, GOLD)
    out += shape(poly_d([Tf((-6, 15)), Tf((6, 15)), Tf((8, 30)), Tf((-8, 30))]), GOLD_DK, LW * 0.8)
    out += shape(rrect(*Tf((0, 36)), 44 * s, 12 * s, 4 * s, deg), "#B7774F", LW * 0.8)
    out += brush([Tf((-16, -24)), Tf((-14, -6)), Tf((-8, 4))], 5 * s, 3 * s, GOLD_LT)
    return out


STEPS = [(4, 22, 98, 56), (2, 98, 176, 92), (1, 176, 320, 120), (3, 320, 398, 76), (5, 398, 490, 42)]


def scene_trophy(poses):
    labs = ["站在第 1 名台階後", "獎盃飄下來", "獎盃快到了", "獎盃停在頭上", "開心蹦！", "蹦到最高",
            "落地", "獎盃閃閃發亮", "左右晃", "右晃", "站好", "獎盃往上飄"]
    ty = [-120, -70, -30, 0, -8, -16, -4, 0, 0, 0, 0, -40]
    out = []
    for i in range(12):
        gk = {4: dict(h=1.05, w=0.96, bottom=-12, lag=-0.07), 5: dict(h=1.03, bottom=-18, lag=-0.05),
              6: dict(h=0.96, w=1.035), 8: dict(rot=-3), 9: dict(rot=3)}.get(i, dict(lag=-0.04))
        g = base_geom(poses, 0, **gk)
        fc = face(poses, "happy") if 4 <= i <= 9 else face(poses, "dot", (0, -7), 1.1 if i == 3 else 1.0, i == 3)
        mid = ""
        texts = []
        for (n, x0, x1, h) in STEPS:
            col = {1: GOLD, 2: "#DCDCE6", 3: "#E6B48A"}.get(n, "#CFE8F7")
            mid += shape(rrect((x0 + x1) / 2, GROUND - h / 2 + 2, x1 - x0 - 2, h, 6, 0, 0.5), col)
            texts.append(T(str(n), ((x0 + x1) / 2, GROUND - h / 2 + 4 + (18 if n == 1 else 0)), 30 if n == 1 else 24, 0,
                           TXT, 0.8))
        top = head_top(poses, g)
        svg = trophy_svg((top[0] + 4, top[1] - 52 + ty[i]), 1.1, 6 * math.sin(i * 1.1))
        if 7 <= i <= 9 or i == 4:
            c = (top[0] + 4, top[1] - 52 + ty[i])
            svg += sparkle((c[0] - 52, c[1] - 20), 10 if i % 2 else 7) + sparkle((c[0] + 54, c[1] + 4), 7 if i % 2 else 10)
        out.append(fr_(poses, g, labs[i], fc, mid=mid, front=svg, texts=texts))
    return out


# ================================================================== 9. 沙漏＋舊照片
def hourglass_svg(c, deg, top_amt, stream):
    Tf = lambda p: add(c, rot2(p, deg))  # noqa: E731
    out = shape(rrect(*Tf((0, -64)), 74, 12, 5, deg), "#B7774F", LW * 0.8)
    out += shape(rrect(*Tf((0, 64)), 74, 12, 5, deg), "#B7774F", LW * 0.8)
    for sgn in (-1, 1):
        a, b = Tf((sgn * 30, -58)), Tf((sgn * 30, 58))
        out += f'<path d="M {P(a)} L {P(b)}" stroke="#8A5A3B" stroke-width="5" stroke-linecap="round"/>'
    glass = (f"M {P(Tf((-24,-58)))} L {P(Tf((24,-58)))} C {P(Tf((24,-20)))} {P(Tf((5,-12)))} {P(Tf((5,0)))} "
             f"C {P(Tf((5,12)))} {P(Tf((24,20)))} {P(Tf((24,58)))} L {P(Tf((-24,58)))} "
             f"C {P(Tf((-24,20)))} {P(Tf((-5,12)))} {P(Tf((-5,0)))} C {P(Tf((-5,-12)))} {P(Tf((-24,-20)))} {P(Tf((-24,-58)))} Z")
    out += f'<path d="{glass}" fill="#EAF6FD"/>'
    sand = "#F2C462"
    if top_amt > 0.02:
        yt = -8 - 44 * top_amt
        w = 4 + 18 * top_amt
        out += f'<path d="{poly_d([Tf((-w, yt)), Tf((w, yt)), Tf((4, -6)), Tf((-4, -6))])}" fill="{sand}"/>'
    bot = 1 - top_amt
    if bot > 0.02:
        yb = 56 - 34 * bot
        out += f'<path d="M {P(Tf((-22,56)))} L {P(Tf((22,56)))} C {P(Tf((20,yb+8)))} {P(Tf((6,yb)))} {P(Tf((0,yb)))} C {P(Tf((-6,yb)))} {P(Tf((-20,yb+8)))} {P(Tf((-22,56)))} Z" fill="{sand}"/>'
    if stream:
        out += f'<path d="M {P(Tf((0,-4)))} L {P(Tf((0, 54 - 34*bot)))}" stroke="{sand}" stroke-width="3"/>'
    out += f'<path d="{glass}" fill="none" stroke="{INK}" stroke-width="{f(LW*0.85)}"/>'
    out += brush([Tf((-16, -50)), Tf((-14, -30))], 3.6, 2.4, WHITE)
    return out


def photo_svg(c, deg, kind, s=1.0):
    w, h = 86 * s, 98 * s
    out = shape(rrect(c[0], c[1], w, h, 5, deg, 0.5), "#FFFBF2", LW * 0.75)
    ic = add(c, rot2((0, -10 * s), deg))
    out += f'<path d="{rrect(ic[0], ic[1], w - 16 * s, h - 34 * s, 3, deg, 0.3)}" fill="{SEPIA}"/>'
    if kind == 0:   # 舊 K 線
        for k in range(5):
            x = -24 + k * 12; hh = [14, 22, 10, 26, 18][k]; y = [4, -2, 8, -8, -4][k]
            a = add(ic, rot2((x * s, (y - hh / 2) * s), deg)); b = add(ic, rot2((x * s, (y + hh / 2) * s), deg))
            out += f'<path d="M {P(a)} L {P(b)}" stroke="{SEPIA_DK}" stroke-width="{f(6*s)}" stroke-linecap="round"/>'
    elif kind == 1:  # 舊折線
        pts = [add(ic, rot2(((-28 + k * 11) * s, v * s), deg)) for k, v in enumerate([12, 4, 8, -6, -2, -16])]
        out += f'<path d="{poly_d(pts, False)}" fill="none" stroke="{SEPIA_DK}" stroke-width="{f(4*s)}" stroke-linejoin="round" stroke-linecap="round"/>'
    else:            # 舊長條
        for k in range(4):
            x = -21 + k * 14; hh = [16, 26, 20, 32][k]
            a = add(ic, rot2((x * s, 20 * s), deg)); b = add(ic, rot2((x * s, (20 - hh) * s), deg))
            out += f'<path d="M {P(a)} L {P(b)}" stroke="{SEPIA_DK}" stroke-width="{f(9*s)}"/>'
    return out


def scene_hourglass(poses):
    labs = ["沙漏開始流", "舊照片浮出來", "第二張", "第三張", "看著過去", "嗯…以前是這樣", "沙繼續流",
            "看懂了！", "開心", "沙快流完", "沙漏翻過來", "翻好，重新開始"]
    photos = [((372, 118), -8, 0), ((450, 210), 7, 1), ((300, 70), 3, 2)]
    out = []
    for i in range(12):
        gk = {7: dict(h=1.04, w=0.97, bottom=-8, lag=-0.06), 8: dict(h=0.97, w=1.03)}.get(i, dict(lag=-0.04, rot=1.5))
        g = base_geom(poses, 0, **gk)
        if i in (4, 5):
            fc = face(poses, "relax")
        elif i in (7, 8):
            fc = face(poses, "happy")
        else:
            fc = face(poses, "dot", (7, -6), 1.0, False)
        if i <= 9:
            amt, deg, stream = 1 - i / 9.5, 0, True
        elif i == 10:
            amt, deg, stream = 0.0, 90, False
        else:
            amt, deg, stream = 0.0, 180, False   # 翻過來＝滿的那半在上（圖形上下對稱，接回第 1 格）
        hg = hourglass_svg((86, 410), deg, amt if deg != 180 else 0.0, stream)
        if deg == 180:
            hg = hourglass_svg((86, 410), 0, 1.0, False)
        svg = hg
        for k, (pc, pd, kind) in enumerate(photos):
            u = (i - (1 + k)) / 1.5
            if i >= 10:
                u = 1 - (i - 9) * 0.45
            if u <= 0:
                continue
            e = BA.ease(min(u, 1))
            c = (pc[0], pc[1] + 30 * (1 - e) + 3 * math.sin(i + k))
            svg += g_op(photo_svg(c, pd + 4 * math.sin(i * 0.8 + k), kind, 0.6 + 0.4 * e), min(1, e * 1.2))
        if i == 7:
            svg += sparkle((150, 180), 10) + sparkle((250, 150), 8)
        out.append(fr_(poses, g, labs[i], fc, front=svg))
    return out


# ================================================================== 10. 火箭
def rocket_svg(c, deg, flame_t):
    Tf = lambda p: add(c, rot2(p, deg))  # noqa: E731
    out = ""
    fl = 1 + 0.25 * math.sin(flame_t * 2.3)
    out += shape(f"M {P(Tf((-10,34)))} C {P(Tf((-12,52*fl)))} {P(Tf((0,70*fl)))} {P(Tf((0,74*fl)))} C {P(Tf((0,70*fl)))} {P(Tf((12,52*fl)))} {P(Tf((10,34)))} Z", "#F2774B", 3)
    out += f'<path d="M {P(Tf((-5,36)))} C {P(Tf((-6,48*fl)))} {P(Tf((0,58*fl)))} {P(Tf((0,60*fl)))} C {P(Tf((0,58*fl)))} {P(Tf((6,48*fl)))} {P(Tf((5,36)))} Z" fill="{GOLD}"/>'
    for sgn in (-1, 1):
        out += shape(f"M {P(Tf((sgn*14,8)))} C {P(Tf((sgn*30,16)))} {P(Tf((sgn*32,32)))} {P(Tf((sgn*30,40)))} L {P(Tf((sgn*12,32)))} Z", RED)
    body = (f"M {P(Tf((0,-46)))} C {P(Tf((18,-30)))} {P(Tf((18,10)))} {P(Tf((14,34)))} L {P(Tf((-14,34)))} "
            f"C {P(Tf((-18,10)))} {P(Tf((-18,-30)))} {P(Tf((0,-46)))} Z")
    out += shape(body, WHITE)
    out += shape(f"M {P(Tf((0,-46)))} C {P(Tf((9,-38)))} {P(Tf((13,-30)))} {P(Tf((15,-24)))} L {P(Tf((-15,-24)))} C {P(Tf((-13,-30)))} {P(Tf((-9,-38)))} {P(Tf((0,-46)))} Z", RED, LW * 0.8)
    w = Tf((0, -4))
    out += f'<circle cx="{f(w[0])}" cy="{f(w[1])}" r="9" fill="{CYAN}" stroke="{INK}" stroke-width="3.4"/>'
    hw = Tf((-3, -7))
    out += f'<circle cx="{f(hw[0])}" cy="{f(hw[1])}" r="2.6" fill="{WHITE}"/>'
    return out


def scene_rocket(poses):
    labs = ["火箭在右下點火", "起飛！", "往上衝", "越飛越高", "飛過頭頂", "快出畫面", "咻——出去了",
            "眼睛發亮", "開心蹦", "蹦最高", "落地", "下一枚火箭準備"]
    out = []
    for i in range(12):
        u = (i / 7.0)
        gk = {7: dict(h=0.96, w=1.035), 8: dict(h=1.05, w=0.96, bottom=-12, lag=-0.07),
              9: dict(h=1.03, bottom=-18, lag=-0.05), 10: dict(h=0.96, w=1.035)}.get(i, dict(lag=-0.05))
        g = base_geom(poses, 0, **gk)
        svg = ""
        if i <= 6:
            x = 430 - 150 * u ** 1.3 * 1.0 + 40 * math.sin(u * 2.5)
            y = 470 - 560 * u ** 1.6
            deg = -10 - 20 * u
            for k in range(1, 5):   # 煙：一路留下的小雲
                uu = max(0.0, u - k * 0.12)
                px = 430 - 150 * uu ** 1.3 + 40 * math.sin(uu * 2.5); py = 470 - 560 * uu ** 1.6 + 60
                r = 9 + k * 3
                svg += g_op(shape(blob_d((px + 6 * k, py), r, r * 0.8, seed=k + i), "#F1ECE6", 2.4), max(0.2, 1 - k * 0.2))
            svg += rocket_svg((x, y), deg, i)
            look = (max(-7, min(8, (x - CX) / 22)), max(-8, min(5, (y - 320) / 30)))
            fc = face(poses, "dot", look, 1.1, i >= 4)
        elif i == 11:
            svg += rocket_svg((448, 488), -8, i)
            fc = face(poses, "dot", (8, 4), 1.0, False)
        else:
            fc = face(poses, "dot", (0, -7), 1.3, True) if i == 7 else face(poses, "happy")
            svg += sparkle((150, 140), 10) + sparkle((360, 90), 9) + sparkle((420, 180), 6)
        out.append(fr_(poses, g, labs[i], fc, front=svg))
    return out


# ================================================================== 11. 許願瓶
def jar_svg(c, fill_n, glow):
    w, h = 84, 104
    out = ""
    if glow > 0:
        out += f'<circle cx="{f(c[0])}" cy="{f(c[1])}" r="{f(70)}" fill="#FFF3B0" opacity="{0.35*glow:.2f}"/>'
    body = (f"M {P((c[0]-26, c[1]-h/2+14))} C {P((c[0]-w/2, c[1]-h/2+22))} {P((c[0]-w/2, c[1]-10))} {P((c[0]-w/2, c[1]+h/2-16))} "
            f"C {P((c[0]-w/2, c[1]+h/2))} {P((c[0]+w/2, c[1]+h/2))} {P((c[0]+w/2, c[1]+h/2-16))} "
            f"C {P((c[0]+w/2, c[1]-10))} {P((c[0]+w/2, c[1]-h/2+22))} {P((c[0]+26, c[1]-h/2+14))} Z")
    out += f'<path d="{body}" fill="#E4F4FC" opacity="0.9"/>'
    rng = np.random.default_rng(3)
    for k in range(fill_n):
        p = (c[0] + rng.uniform(-26, 26), c[1] + h / 2 - 18 - rng.uniform(0, 30) - (k // 4) * 8)
        out += shape(star_d(p, 9, rng.uniform(0, 70)), [GOLD, PINK, MINT][k % 3], 2.2)
    out += f'<path d="{body}" fill="none" stroke="{INK}" stroke-width="{f(LW)}"/>'
    out += shape(rrect(c[0], c[1] - h / 2 + 6, 40, 20, 6), "#C99567", LW * 0.85)
    out += brush([(c[0] - 30, c[1] - 14), (c[0] - 30, c[1] + 22)], 5, 3.5, WHITE)
    return out


def heart_d(c, s):
    x, y = c
    return (f"M {P((x, y+12*s))} C {P((x-20*s, y-2*s))} {P((x-14*s, y-18*s))} {P((x, y-8*s))} "
            f"C {P((x+14*s, y-18*s))} {P((x+20*s, y-2*s))} {P((x, y+12*s))} Z")


def scene_heart_wish(poses):
    JC = (424, 420)
    labs = ["閉眼許願", "許願星星冒出來", "星星飛向瓶子", "咻——", "掉進許願瓶", "瓶子亮一下", "愛心飄起來",
            "第二顆星星", "飛向瓶子", "又進去了", "瓶子亮、開心", "繼續許願"]
    out = []
    for i in range(12):
        gk = {5: dict(h=1.03, bottom=-6, lag=-0.05), 10: dict(h=1.03, bottom=-6, lag=-0.05)}.get(i, dict(lag=-0.03, h=0.99 + 0.01 * (i % 2)))
        g = base_geom(poses, 0, **gk)
        fc = face(poses, "relax") if i in (0, 1, 11) else face(poses, "happy") if i in (5, 6, 10) else face(poses, "dot", (8, 0), 1.0, False)
        n = 3 + (1 if i >= 4 else 0) + (1 if i >= 9 else 0)
        glow = 1.0 if i in (5, 10) else (0.5 if i in (6,) else 0)
        svg = jar_svg(JC, n, glow)
        top = head_top(poses, g)
        for start, t0 in ((0, 1), (1, 7)):
            u = (i - t0) / 3.0
            if 0 <= u < 1:
                e = BA.ease(u)
                p0 = (top[0] + 30, top[1] - 30); p1 = (JC[0], JC[1] - 40)
                x = p0[0] + (p1[0] - p0[0]) * e; y = p0[1] + (p1[1] - p0[1]) * e - 90 * math.sin(math.pi * e)
                svg += shape(star_d((x, y), 15, i * 30), GOLD, LW * 0.8)
                for k in range(3):   # 星星尾巴的小點
                    ee = max(0, e - 0.08 * (k + 1))
                    xx = p0[0] + (p1[0] - p0[0]) * ee; yy = p0[1] + (p1[1] - p0[1]) * ee - 90 * math.sin(math.pi * ee)
                    svg += f'<circle cx="{f(xx)}" cy="{f(yy)}" r="{3.2-k*0.7:.1f}" fill="{GOLD_DK}"/>'
        if 6 <= i <= 9:
            for k in range(2):
                hy = top[1] - 20 - (i - 6) * 14 - k * 20
                svg += g_op(shape(heart_d((top[0] - 70 + k * 40, hy), 1.0), PINK, 3), max(0.3, 1 - (i - 6) * 0.2))
        if i in (5, 10):
            svg += sparkle((JC[0] - 54, JC[1] - 64), 10) + sparkle((JC[0] + 50, JC[1] - 40), 8)
        out.append(fr_(poses, g, labs[i], fc, front=svg))
    return out


# ================================================================== 12. 魔法方框
FRAME_BOX = (40, 34, 472, 214)   # 方框（場景座標）；剪輯換算時照 index_e.json 每格寫的四角


def rect_path_progress(box, prog):
    """從左上角順時針沿四邊走 prog（0～1）：回傳路徑點與筆尖位置。"""
    x0, y0, x1, y1 = box
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    L = [math.dist(corners[k], corners[k + 1]) for k in range(4)]
    total = sum(L); goal = total * prog
    pts = [corners[0]]
    acc = 0
    for k in range(4):
        if acc + L[k] <= goal:
            pts.append(corners[k + 1]); acc += L[k]
        else:
            t = (goal - acc) / L[k]
            a, b = corners[k], corners[k + 1]
            pts.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
            break
    return pts, pts[-1]


def scene_magic_frame(poses):
    prog = [0.0, 0.12, 0.27, 0.42, 0.57, 0.72, 0.87, 1.0, 1.0, 1.0, 1.0, 1.0]
    labs = ["小肉掌準備揮", "揮！畫出上邊", "上邊畫完", "畫右邊", "畫下邊", "下邊快完", "畫左邊",
            "方框完成！", "方框發光", "比比開心", "方框亮著", "方框淡出"]
    out = []
    for i in range(12):
        gk = {7: dict(h=1.04, w=0.97, bottom=-8, lag=-0.06), 8: dict(h=0.97, w=1.03)}.get(i, dict(lag=-0.04, rot=2 * math.sin(i * 1.4)))
        g = base_geom(poses, 0, **gk)
        pts, tip = rect_path_progress(FRAME_BOX, prog[i])
        svg = ""
        op = 0.35 if i == 11 else 1.0
        if prog[i] > 0:
            d = "M " + " L ".join(P(p) for p in pts) + (" Z" if prog[i] >= 1 else "")
            w = 7.0 if i not in (8, 10) else 8.5
            svg += g_op(glow_stroke(d, GOLD, "#FFF7D6", w), op)
        # 小肉掌（官方部件總表原圖像素）：從身體右側冒出一小截，上下小幅揮動，魔法粉從掌尖飛到筆尖
        at = BA.shoulder(poses, g, (432, 318), depth=10)
        hdeg = 55 + 22 * math.sin(i * 1.9)
        pc = BA.hand_tip(at, hdeg, 46)
        if i <= 7:
            dust = bez(pc, (pc[0] + 30, pc[1] - 80), (tip[0] - 20, tip[1] + 60), tip, 14)
            for k, p in enumerate(dust[2:-1]):
                if k % 2 == 0:
                    svg += f'<circle cx="{f(p[0])}" cy="{f(p[1])}" r="{2.2 + 0.15*k:.1f}" fill="{GOLD}" opacity="0.8"/>'
            if prog[i] > 0 and prog[i] < 1:
                svg += sparkle(tip, 12)
            svg += BA.arcs(pc, hdeg - 70, r=16, n=1)
        fc = face(poses, "happy") if 7 <= i <= 9 else face(poses, "dot", (5, -6), 1.0, False)
        if i in (7, 9):
            for c in ((FRAME_BOX[0], FRAME_BOX[1]), (FRAME_BOX[2], FRAME_BOX[1]), (FRAME_BOX[2], FRAME_BOX[3]), (FRAME_BOX[0], FRAME_BOX[3])):
                svg += sparkle(c, 12 if i == 7 else 9)
        fr = fr_(poses, g, labs[i], fc, front=svg, sprites=[BA.hand_layer(at, hdeg - g.get("rot", 0) * 0, 46, "R")])
        x0, y0, x1, y1 = FRAME_BOX
        fr["frame_box"] = {"corners": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]], "drawn": round(prog[i], 3),
                           "tip": [round(tip[0], 1), round(tip[1], 1)], "opacity": op}
        out.append(fr)
    return out


# ================================================================== 輸出
SCENES = {
    "alarm": ("鬧鐘響→按掉（省時間）", scene_alarm, [90, 70, 70, 80, 70, 90, 110, 80, 120, 100, 90, 80]),
    "clock": ("時鐘快轉→放鬆（30 分變 3 分）", scene_clock, [120, 60, 60, 60, 60, 60, 140, 100, 110, 100, 100, 90]),
    "bulb": ("頭上燈泡亮（原來如此）", scene_bulb, [100, 90, 100, 80, 70, 100, 70, 90, 100, 80, 80, 90]),
    "folder": ("亂紙飛進資料夾（統整資料）", scene_folder, [100, 70, 70, 70, 70, 70, 90, 120, 90, 90, 90, 80]),
    "globe": ("地球轉＋新聞卡飛出", scene_globe, [90, 70, 80, 70, 80, 70, 80, 110, 100, 90, 80, 80]),
    "fire": ("火苗＋溫度計升高（題材熱度）", scene_fire, [90, 80, 80, 80, 80, 80, 80, 110, 100, 90, 90, 90]),
    "star_save": ("星星收藏進盒子（自選清單）", scene_star_save, [90, 80, 80, 80, 70, 70, 80, 110, 90, 90, 80, 80]),
    "trophy": ("獎盃＋1～5 名台階（ETF 前五名）", scene_trophy, [90, 70, 70, 100, 70, 70, 80, 100, 90, 90, 90, 80]),
    "hourglass": ("沙漏＋舊照片（週期統計看過往）", scene_hourglass, [90, 90, 90, 90, 110, 110, 90, 90, 90, 90, 70, 80]),
    "rocket": ("小火箭往上（持續進步）", scene_rocket, [90, 60, 60, 60, 60, 60, 70, 90, 70, 70, 90, 100]),
    "heart_wish": ("許願星星飛進許願瓶（會員許願）", scene_heart_wish, [120, 80, 70, 70, 80, 100, 90, 80, 70, 80, 100, 110]),
    "magic_frame": ("揮小肉掌畫出發光方框（框住重點）", scene_magic_frame, [100, 60, 60, 60, 60, 60, 60, 100, 100, 100, 100, 90]),
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
    only = [x for x in a.only.split(",") if x]
    for key, (name, fn, durs) in SCENES.items():
        if only and key not in only:
            continue
        frs = fn(poses)
        assert len(frs) == 12 and len(durs) == 12, key
        imgs = [compose(poses, fr) for fr in frs]
        fd = out / key / "frames"
        fd.mkdir(parents=True, exist_ok=True)
        paths = []
        for j, im in enumerate(imgs):
            p = fd / f"frame_{j+1:02d}.png"
            im.save(p); paths.append(str(p.resolve()))
        rd = Path(a.repo_out) / f"bibi_{key}"
        rd.mkdir(parents=True, exist_ok=True)
        sheet12(imgs, [f"{j+1:02d} {fr['label']}" for j, fr in enumerate(frs)], rd / "sheet_12.png")
        imgs[0].save(rd / "anim.webp", save_all=True, append_images=imgs[1:], duration=durs, loop=0,
                     lossless=False, quality=88, method=6)
        imgs[0].save(out / key / "anim.gif", save_all=True, append_images=imgs[1:], duration=durs, loop=0, disposal=2)
        arr = [np.asarray(im).astype(int) for im in imgs]
        diffs = [int(np.abs(arr[k] - arr[(k + 1) % 12]).sum() // 1000) for k in range(12)]
        entry = {"name": name, "size": [SIZE, SIZE], "frames": paths, "durations_ms": durs,
                 "labels": [fr["label"] for fr in frs], "adjacent_diff_k": diffs,
                 "scene": {"scale": SCALE, "center_x": CX, "ground_y": GROUND}}
        if key == "magic_frame":
            entry["frame_box_per_frame"] = [fr["frame_box"] for fr in frs]
        (out / key / "meta.json").write_text(json.dumps(entry, ensure_ascii=False, indent=1), encoding="utf-8")
        print(key, "min diff", min(diffs), "→", rd)
    idx = {}
    for k in SCENES:
        mp = out / k / "meta.json"
        if mp.exists():
            idx[k] = json.loads(mp.read_text(encoding="utf-8"))
    (out / "index_e.json").write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
