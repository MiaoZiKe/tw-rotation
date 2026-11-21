"""動畫設計單位：比比「G1 批」客服鈕互動動作 4 組（每組 12 格、512×512、透明）＋ 10 個互動小圈圖示。

為什麼有這支
------------
Andy 要網頁版右下角客服鈕「比比」更像真的在陪伴你：摸摸頭、吃草、玩球、轉圈圈，加上 10 個互動選單小圈圖示。
沿用 F 批（bibi_faces_f.py）的做法：身體＝原圖 `support_anim_1009.gif` 第 0 張的像素網格變形（不重畫），
五官在原圖座標補掉再重畫，跟著身體一起變形；臉外的物件在場景座標畫（身體縮 0.75、中心 x=248、腳底 y=482）。
手只畫「貼身小肉掌」（官方部件總表樣式，不畫手臂）；道具懸空或放在身前。SVG 三次 Bézier 4 倍繪製再 LANCZOS 縮回。

動作
----
pet 摸摸頭／eat_grass 吃草／ball 玩球／spin 轉圈圈。spin 用「假 3D 轉身」：身體輪廓不變（毛球轉起來輪廓本來就是圓的），
五官／腮紅依轉角在球面上移動、橫向壓縮，轉到背面時臉消失、露出一小團尾巴毛。

用法
----
    python scripts/anim/bibi_interact_g1.py --out <scratchpad>/bibi_g --repo-out docs/anim [--only pet,ball] [--icons]
輸出：<out>/<名>/frames/frame_01.png…（512）、<out>/<名>/anim512.webp；
<repo-out>/bibi_<名>/sheet_12.png、anim.webp（160px）、storyboard.md；圖示 <repo-out>/bibi_icons/<名>.png＋index.md。
"""
from __future__ import annotations

import argparse
import io
import math
import sys
from pathlib import Path

import cairosvg
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import bibi_actions as BA  # noqa: E402
import bibi_faces_c as C  # noqa: E402
import pose_tween  # noqa: E402
from bibi_actions import (INK, FUR, SIZE, f, P, add, dirv, bez, brush, sparkle, motion_lines, arcs,  # noqa: E402
                          base_geom, raster, sheet12, ease)
from bibi_faces_c import (paw_svg, PAW2, PAW2_DK, PAW2_LT, EYE_L, EYE_R, CHEEK_L, CHEEK_R, SW, F, FR,  # noqa: E402
                          render, heart_svg, star_svg, body_rot, smooth_closed, jitter)

GRASS, GRASS_DK, GRASS_LT = "#9CC95E", "#6FA03C", "#CFE79A"
BALL, BALL_DK = "#F2705E", "#D9503F"
LW = BA.OUT_W * 0.8


# ================================================================== 小工具
def lerp(a, b, t):
    return a + (b - a) * t


def lerp2(p, q, t):
    return (lerp(p[0], q[0], t), lerp(p[1], q[1], t))


def g_op(svg, op):
    return svg if op >= 0.999 else f'<g opacity="{op:.2f}">{svg}</g>'


# ================================================================== 官方肉掌部件（貼圖）
PARTS = Path(__file__).resolve().parents[2] / "docs" / "anim" / "bibi_library" / "parts"
_SP = {}


def sprite(name, c, deg=0.0, k=1.0, flip=False):
    """官方部件總表切出的透明 PNG（hand_l 往下摸、hand_side 橫放）：c＝場景座標中心，deg＝逆時針度數。"""
    return {"name": name, "c": c, "deg": deg, "k": k, "flip": flip}


def paste_sprites(im, sprites):
    for sp in sprites:
        key = sp["name"]
        if key not in _SP:
            _SP[key] = Image.open(PARTS / f"{key}.png").convert("RGBA")
        t = _SP[key]
        if sp["flip"]:
            t = t.transpose(Image.FLIP_LEFT_RIGHT)
        t = t.resize((int(t.width * sp["k"] * 4), int(t.height * sp["k"] * 4)), Image.LANCZOS)
        t = t.rotate(sp["deg"], resample=Image.BICUBIC, expand=True)
        t = t.resize((max(1, t.width // 4), max(1, t.height // 4)), Image.LANCZOS)
        im.alpha_composite(t, (int(round(sp["c"][0] - t.width / 2)), int(round(sp["c"][1] - t.height / 2))))
    return im


def render_g(poses, fr, font):
    return paste_sprites(render(poses, fr, font), fr.get("sprites", []))


# ================================================================== 1. 摸摸頭
def clip_pet(poses):
    # (標籤, 幾何, 臉, 肉掌(x,y,deg) 或 None, 愛心數 0~3, 動作線)
    P0 = (330, 130, -125)   # 肉掌飛來的位置（懸空，指尖朝左下）
    seq = [
        ("待機", dict(), dict(), None, 0, 0),
        ("肉掌從右上飛來", dict(h=1.005), dict(eyes="dot", mouth="w", look=(6, -4)), (352, 150, -122), 0, 0),
        ("輕輕放到頭頂（頭微壓）", dict(h=0.975, w=1.012, lag=-0.05), dict(eyes="happy", mouth="w", blush="soft"), (262, 212, -92), 0, 0),
        ("摸過去（往左）", dict(h=0.972, w=1.014, lag=-0.05, rot=-2.2), dict(eyes="happy", mouth="open_s", blush="soft"), (228, 214, -78), 1, 1),
        ("摸過來（往右）", dict(h=0.972, w=1.014, lag=-0.05, rot=2.2), dict(eyes="happy", mouth="w", blush="soft"), (292, 214, -104), 2, 2),
        ("摸過去（往左）", dict(h=0.97, w=1.016, lag=-0.055, rot=-2.4), dict(eyes="happy", mouth="open_s", blush="soft"), (226, 215, -78), 3, 1),
        ("摸過來（往右）", dict(h=0.97, w=1.016, lag=-0.055, rot=2.4), dict(eyes="happy", mouth="w", blush="soft"), (294, 215, -104), 3, 2),
        ("享受（肉掌停在頭上）", dict(h=0.975, w=1.012, lag=-0.05), dict(eyes="happy", mouth="open_m", blush="soft"), (260, 213, -92), 3, 0),
        ("肉掌抬起", dict(h=0.995, lag=-0.01), dict(eyes="happy", mouth="open_s", blush="soft"), (276, 188, -100), 2, 0),
        ("肉掌飛走", dict(h=1.01, lag=0.02), dict(eyes="shine", mouth="open_s", blush="soft"), (338, 126, -118), 0, 0),
        ("回味（微笑）", dict(h=1.0), dict(eyes="shine", mouth="w", blush="soft"), None, 0, 0),
        ("回待機", dict(h=0.998), dict(), None, 0, 0),
    ]
    heart_pos = [((372, 168), 15, 8), ((142, 150), 13, -10), ((392, 232), 11, 12)]
    frames = []
    for i, (lab, gk, face, paw, nh, ln) in enumerate(seq):
        g = base_geom(poses, 0, **gk)
        front = ""
        sprites = []
        if paw:
            c = (paw[0], paw[1])
            sprites.append(sprite("hand_l", c, deg=(paw[2] + 90) * 1.0, k=1.15))
            if ln == 1:     # 往左摸：右側兩條弧形動作線（在肉掌後面）
                front += arcs((c[0] + 36, c[1] - 6), 0, r=14, n=2, w=4.0)
            if ln == 2:
                front += arcs((c[0] - 36, c[1] - 6), 180, r=14, n=2, w=4.0)
        for k in range(nh):
            pos, s, dg = heart_pos[k]
            rise = (i % 3) * 3.0 if nh == 3 else 0.0
            op = 1.0
            if i in (8, 9):
                op = 0.7 if i == 8 else 0.4
            front += heart_svg((pos[0], pos[1] - rise - (i - 3) * 1.5), s, deg=dg, op=op)
        if i in (4, 6):
            front += sparkle((118, 215), 9) + sparkle((402, 280), 8)
        frames.append(FR(poses, lab, gk, face, front, sprites=sprites))
    return frames


PET_D = [900, 150, 170, 190, 190, 190, 190, 200, 160, 150, 160, 600]


# ================================================================== 2. 吃草
def blade(base, tip, w, bend, col=GRASS, col_dk=GRASS_DK):
    """一片牧草（兩頭尖、略彎、帶中肋）。base 是握著的那頭，tip 是啃的那頭。"""
    dx, dy = tip[0] - base[0], tip[1] - base[1]
    L = math.hypot(dx, dy) + 1e-9
    nx, ny = -dy / L, dx / L
    mid = (lerp(base[0], tip[0], 0.5) + nx * bend, lerp(base[1], tip[1], 0.5) + ny * bend)
    q1 = (lerp(base[0], tip[0], 0.25) + nx * (bend * 0.9 + w), lerp(base[1], tip[1], 0.25) + ny * (bend * 0.9 + w))
    q2 = (lerp(base[0], tip[0], 0.75) + nx * (bend * 0.9 + w * 0.6), lerp(base[1], tip[1], 0.75) + ny * (bend * 0.9 + w * 0.6))
    r1 = (lerp(base[0], tip[0], 0.25) + nx * (bend * 0.9 - w), lerp(base[1], tip[1], 0.25) + ny * (bend * 0.9 - w))
    r2 = (lerp(base[0], tip[0], 0.75) + nx * (bend * 0.9 - w * 0.6), lerp(base[1], tip[1], 0.75) + ny * (bend * 0.9 - w * 0.6))
    d = (f"M {P(base)} C {P(q1)} {P(q2)} {P(tip)} C {P(r2)} {P(r1)} {P(base)} Z")
    rib = f"M {P(base)} Q {P(mid)} {P(tip)}"
    return (f'<path d="{d}" fill="{col}" stroke="{INK}" stroke-width="{f(LW*0.75)}" stroke-linejoin="round"/>'
            f'<path d="{rib}" fill="none" stroke="{col_dk}" stroke-width="2.4" stroke-linecap="round"/>')


def grass_bundle(top_y, x=254, base_y=458, tilt=0.0):
    """一把牧草：從身前下方（肉掌握著）往上伸到嘴邊；top_y＝最上端（越大代表被啃掉越多）。"""
    s = ""
    specs = [(-12, -9, 8.0, -4), (12, 10, 8.0, 4), (0, 1, 9.5, 0)]
    for k, (bx, tx, w, bend) in enumerate(specs):
        t_y = top_y + (7 if k == 0 else (11 if k == 1 else 0))
        s += blade((x + bx * 0.7, base_y), (x + tx + tilt, t_y), w, bend)
    return s


def crumb(c, deg=0, s=1.0, op=1.0):
    pts = [(c[0] - 6 * s, c[1]), (c[0], c[1] - 3.2 * s), (c[0] + 6 * s, c[1]), (c[0], c[1] + 3.2 * s)]
    d = "M " + " L ".join(P(p) for p in pts) + " Z"
    return g_op(f'<path d="{d}" fill="{GRASS}" stroke="{INK}" stroke-width="2.4" stroke-linejoin="round" '
                f'transform="rotate({deg},{f(c[0])},{f(c[1])})"/>', op)


def cheek_puff(k):
    """臉頰鼓起：腮紅加大加深（原圖座標）。"""
    out = ""
    for c in (CHEEK_L, CHEEK_R):
        out += (f'<ellipse cx="{c[0]}" cy="{c[1]+2}" rx="{f(29+7*k)}" ry="{f(22+6*k)}" fill="{C.BLUSH2}" opacity="{0.35+0.25*k:.2f}"/>')
    return out


def clip_eat(poses):
    # (標籤, 幾何, 臉, 牧草末端 x 或 None, 肉掌 x, 鼓臉 0~1, 碎屑)
    seq = [
        ("待機", dict(), dict(), None, None, 0, 0),
        ("肉掌捧著牧草從下方升起", dict(h=1.005, lag=0.01), dict(eyes="shine", mouth="w", look=(0, 8)), 384, 254, 0, 0),
        ("牧草送到嘴邊", dict(h=1.01, lag=0.02), dict(eyes="shine", mouth="open_s", look=(0, 8)), 345, 254, 0, 0),
        ("咬一口", dict(h=0.985, w=1.02, lag=-0.02), dict(eyes="happy", mouth="w", blush="soft"), 347, 254, 0.7, 1),
        ("啃啃（鼓臉）", dict(h=1.01, w=0.995, lag=0.01), dict(eyes="happy", mouth="w", blush="soft"), 355, 254, 1.0, 2),
        ("啃啃（咬）", dict(h=0.982, w=1.025, lag=-0.02), dict(eyes="happy", mouth="w", blush="soft"), 360, 254, 0.8, 1),
        ("啃啃（鼓臉）", dict(h=1.012, w=0.995, lag=0.012), dict(eyes="happy", mouth="w", blush="soft"), 368, 254, 1.0, 2),
        ("啃啃（咬）", dict(h=0.98, w=1.027, lag=-0.02), dict(eyes="blink", mouth="w", blush="soft"), 376, 254, 0.9, 1),
        ("吞下去（鼓臉消）", dict(h=1.012, w=0.995, lag=0.012), dict(eyes="blink", mouth="w", blush="soft"), 390, 254, 0.4, 2),
        ("好滿足（牧草啃完）", dict(h=1.015, lag=0.02), dict(eyes="happy", mouth="open_s", blush="soft"), None, None, 0.1, 3),
        ("滿足的微笑", dict(h=1.005), dict(eyes="shine", mouth="w", blush="soft"), None, None, 0, 3),
        ("回待機", dict(h=0.998), dict(), None, None, 0, 0),
    ]
    frames = []
    for i, (lab, gk, face, gx, px, puff, cr) in enumerate(seq):
        face = dict(face)
        if puff:
            face["extra"] = cheek_puff(puff)
        g = base_geom(poses, 0, **gk)
        front = ""
        sprites = []
        if gx is not None:
            sh = 2 if i % 2 == 1 else 0
            front += grass_bundle(gx + sh, x=254, base_y=458, tilt=(-2 if i % 2 else 2))
            # 兩隻小肉掌從左右兩側捧著牧草（指尖朝內、貼在牧草兩邊）
            sprites.append(sprite("hand_side", (px - 34, 418 + sh), 0, 1.1, flip=True))
            sprites.append(sprite("hand_side", (px + 36, 418 + sh), 0, 1.1))
        if cr == 1:      # 咬下去：碎屑
            front += crumb((222, 366), 20, 1.0) + crumb((288, 374), -15, 0.8)
        elif cr == 2:
            front += crumb((218, 372), 35, 1.0, 0.9) + crumb((292, 380), -30, 0.9, 0.9) + crumb((200, 392), 10, 0.7, 0.8)
        elif cr == 3:
            front += sparkle((106, 232), 10) + sparkle((402, 250), 9)
        if puff and i in (4, 6, 8):    # 咀嚼的小動作線（兩側）
            front += arcs((92, 330), 180, r=14, n=2, w=3.8) + arcs((414, 330), 0, r=14, n=2, w=3.8)
        frames.append(FR(poses, lab, gk, face, front, sprites=sprites))
    return frames


EAT_D = [700, 170, 220, 160, 150, 160, 150, 170, 220, 260, 260, 600]


# ================================================================== 3. 玩球
def ball_svg(c, r=24, rot=0.0, sq=(1.0, 1.0), sq_deg=0.0):
    """彈力球：珊瑚紅、一條白色斜帶（會隨 rot 轉）、左上高光；sq＝(沿 sq_deg 方向, 垂直方向) 的壓扁倍率。"""
    cid = f"bl{abs(int(c[0]*3+c[1]*7+rot))}"
    inner = (f'<clipPath id="{cid}"><circle cx="0" cy="0" r="{r}"/></clipPath>'
             f'<circle cx="0" cy="0" r="{r}" fill="{BALL}"/>'
             f'<g clip-path="url(#{cid})" transform="rotate({rot:.1f})">'
             f'<path d="M {-r*1.2},{-r*0.38} Q 0,{-r*0.78} {r*1.2},{-r*0.38} L {r*1.2},{r*0.12} Q 0,{-r*0.28} {-r*1.2},{r*0.12} Z" fill="#FFFFFF"/>'
             f'<ellipse cx="0" cy="{r*0.95}" rx="{r*1.1}" ry="{r*0.5}" fill="{BALL_DK}" opacity="0.7"/></g>'
             f'<circle cx="0" cy="0" r="{r}" fill="none" stroke="{INK}" stroke-width="{f(LW)}"/>'
             f'<ellipse cx="{-r*0.42}" cy="{-r*0.48}" rx="{r*0.2}" ry="{r*0.12}" fill="#FFFFFF" opacity="0.9" transform="rotate(-35,{-r*0.42},{-r*0.48})"/>')
    return (f'<g transform="translate({f(c[0])},{f(c[1])}) rotate({sq_deg:.1f}) scale({sq[0]:.3f},{sq[1]:.3f}) rotate({-sq_deg:.1f})">'
            f'{inner}</g>')


def dots_path(pts, r=3.0, op=0.8):
    return "".join(f'<circle cx="{f(p[0])}" cy="{f(p[1])}" r="{f(r*(0.6+0.4*k/max(1,len(pts)-1)))}" fill="{INK}" opacity="{op:.2f}"/>'
                   for k, p in enumerate(pts))


def parab(p0, p1, apex_h, t):
    """p0→p1 的拋物線，apex_h＝中點往上拱的高度。"""
    x = lerp(p0[0], p1[0], t)
    y = lerp(p0[1], p1[1], t) - 4 * apex_h * t * (1 - t)
    return (x, y)


def clip_ball(poses):
    HIT = (272, 208)          # 頭頂接球點（球心；球半徑 24，下緣剛好壓在頭頂毛上）
    IN0, OUT1 = (480, 70), (470, 96)
    # 球位置（None＝不在）：進場 → 落到頭頂 → 彈回
    ball = [
        None,
        (468, 74),
        parab(IN0, HIT, 70, 0.30),
        parab(IN0, HIT, 70, 0.55),
        parab(IN0, HIT, 70, 0.80),
        HIT,
        (322, 146),
        (382, 98),
        (430, 70),
        (466, 66),
        None,
        None,
    ]
    seq = [
        ("待機", dict(), dict(), 0),
        ("球從右上彈進來", dict(h=1.0), dict(eyes="shine", mouth="open_s", look=(8, -10)), 0),
        ("球飛來（比比盯著）", dict(h=0.99, lag=-0.02, rot=-1), dict(eyes="shine", mouth="open_s", look=(7, -12)), 0),
        ("蹲低準備", dict(h=0.96, w=1.03, lag=-0.06, rot=-1.5), dict(eyes="shine", mouth="open_m", look=(5, -12)), 0),
        ("往上一頂", dict(h=1.045, w=0.98, lag=0.09, rot=2), dict(eyes="happy", mouth="open_m", blush="soft"), 0),
        ("頭頂到球！", dict(h=1.03, w=0.985, lag=0.06, rot=3), dict(eyes="happy", mouth="open_s", blush="soft"), 1),
        ("球被頂回去", dict(h=1.0, lag=0.02, rot=1), dict(eyes="shine", mouth="open_m", look=(8, -12), blush="soft"), 0),
        ("目送球飛（弧線）", dict(h=1.0, lag=0.01), dict(eyes="shine", mouth="open_s", look=(9, -12), blush="soft"), 0),
        ("球飛遠了", dict(h=1.0), dict(eyes="shine", mouth="open_s", look=(9, -10), blush="soft"), 0),
        ("球飛出畫面", dict(h=1.005), dict(eyes="happy", mouth="open_s", blush="soft"), 0),
        ("得意微笑", dict(h=1.01, lag=0.02), dict(eyes="happy", mouth="w", blush="soft"), 2),
        ("回待機", dict(h=0.998), dict(), 0),
    ]
    frames = []
    for i, (lab, gk, face, fx) in enumerate(seq):
        g = base_geom(poses, 0, **gk)
        front = ""
        b = ball[i]
        if b is not None:
            hit = i == 5
            rot = i * 55
            rad = {6: 29, 7: 27, 8: 24, 9: 19}.get(i, 30)
            if hit:
                front += ball_svg(b, 30, rot, sq=(1.16, 0.86), sq_deg=0)
                front += motion_lines((b[0], b[1] - 2), 90, spread=46, r0=36, length=12, n=3, w=4.4)
            else:
                front += ball_svg(b, rad, rot)
            # 軌跡虛點（弧線）
            if i in (2, 3, 4):
                trail = [parab(IN0, HIT, 70, t) for t in np.linspace(max(0.0, [0.30, 0.55, 0.80][i - 2] - 0.2), [0.30, 0.55, 0.80][i - 2] - 0.06, 3)]
                front += dots_path(trail, 3.8, 0.6)
            if i in (6, 7, 8, 9):
                lo = {6: 0.0, 7: 0.1, 8: 0.2, 9: 0.3}[i]
                trail = [(lerp(HIT[0], 466, t), lerp(HIT[1], 66, t) - 4 * 120 * t * (1 - t)) for t in np.linspace(lo, lo + 0.18, 3)]
                trail = [p for p in trail if np.hypot(p[0] - b[0], p[1] - b[1]) > 44]
                front += dots_path(trail, 3.8, 0.6)
        if fx == 2:
            front += sparkle((112, 230), 10) + sparkle((404, 220), 9)
        frames.append(FR(poses, lab, gk, face, front))
    return frames


BALL_D = [700, 170, 140, 140, 120, 130, 150, 150, 150, 200, 300, 600]
# ball 軌跡用 ball 陣列手排，不再依賴 OUT1


# ================================================================== 4. 轉圈圈
_YAW = {}
R_SPH = 150.0   # 球面半徑（原圖座標）


def _fur_at(arr, c, r0=30, r1=44):
    yy, xx = np.mgrid[0:arr.shape[0], 0:arr.shape[1]]
    d2 = (xx - c[0]) ** 2 + (yy - c[1]) ** 2
    ring = (d2 >= r0 ** 2) & (d2 <= r1 ** 2) & (arr[..., :3].mean(2) > 215)
    return "#%02X%02X%02X" % tuple(int(v) for v in np.median(arr[ring][:, :3], 0))


def _xs(cx_orig, y, theta, phi_off=0.0):
    """原圖座標 (cx_orig) 的點，球面轉 theta 度後的 (x', 橫向壓縮倍率 or None＝在背面)。"""
    dx = max(-0.98, min(0.98, (cx_orig - 250.0) / R_SPH))
    ang = math.asin(dx) + math.radians(theta) + phi_off
    c = math.cos(ang)
    if c < 0.10:
        return None, 0.0
    return 250.0 + R_SPH * math.sin(ang), c


def _sq(svg, cx, cy, sx):
    return f'<g transform="translate({f(cx)},{f(cy)}) scale({sx:.3f},1) translate({f(-cx)},{f(-cy)})">{svg}</g>'


def spiral_eye(e, s=1.0, deg=0.0):
    pts = []
    for k in range(60):
        t = k / 59
        a = t * 4.2 * math.pi + math.radians(deg)
        r = (2.0 + 11.5 * t) * s
        pts.append((e[0] + r * math.cos(a), e[1] + r * math.sin(a)))
    return brush(pts, 4.4, 4.0)


def yaw_pose(poses, theta, kind="face"):
    """theta：轉角（度，0＝正面、180＝背面）。kind＝face（正常五官）／dizzy（螺旋眼＋波浪嘴）。"""
    key = (round(theta), kind)
    if key in _YAW:
        return _YAW[key]
    body = C.clean_body(poses, eyes=True, mouth=True)
    arr = np.asarray(body).astype(np.float32)
    H, W = arr.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    # 1) 把原本的腮紅也抹掉（轉起來腮紅要跟著球面走）
    rgb = arr[..., :3]
    rb = rgb[..., 0] - rgb[..., 2]
    cheek_mask = np.zeros((H, W), bool)
    for c in (CHEEK_L, CHEEK_R):
        cheek_mask |= (((xx - c[0]) / 44.0) ** 2 + ((yy - c[1]) / 36.0) ** 2 <= 1) & (rb > 30) & (rgb[..., 0] > 200)
    cheek_mask = C._dilate(cheek_mask, 5)
    cleaned = C._fill_onion(arr, cheek_mask)
    cleaned[..., 3] = arr[..., 3]
    body2 = Image.fromarray(np.clip(cleaned, 0, 255).astype(np.uint8), "RGBA")
    svg = ""
    # 2) 臉部（在球面上轉）
    eyes_y, mouth_y, cheek_y = EYE_L[1], 285.0, 289.0
    for e, side in ((EYE_L, -1), (EYE_R, 1)):
        x, sx = _xs(e[0], e[1], theta)
        if x is not None:
            ee = (x, e[1] + (0 if kind == "face" else 0))
            if kind == "dizzy":
                svg += _sq(spiral_eye(ee, 1.0, deg=theta), ee[0], ee[1], sx)
            else:
                svg += _sq(C.eye_svg(ee, "shine", (0, 0), 1.0, side, 0.0), ee[0], ee[1], sx)
    x, sx = _xs(250.0, mouth_y, theta)
    if x is not None:
        m = C.mouth_svg("wavy" if kind == "dizzy" else "w")
        svg += f'<g transform="translate({f(x-250)},0)">' + _sq(m, 250, mouth_y, sx) + "</g>"
    for c in (CHEEK_L, CHEEK_R):
        x, sx = _xs(c[0], c[1], theta)
        if x is not None:
            svg += _sq(f'<ellipse cx="{f(x)}" cy="{c[1]+2}" rx="26" ry="19" fill="#FBB5A4"/>'
                       f'<ellipse cx="{f(x)}" cy="{c[1]+2}" rx="26" ry="19" fill="{C.BLUSH2}" opacity="0.3"/>', x, c[1], sx)
    # 3) 背面：一小團尾巴毛
    x, sx = _xs(250.0, 400.0, theta, phi_off=math.pi)
    if x is not None:
        ty = 418.0
        pts = []
        for k in range(20):          # 毛球尾巴：扇貝邊的小圓團
            ang = 2 * math.pi * k / 20
            rr = 27 + (4.5 if k % 2 == 0 else -1.5)
            pts.append((x + math.cos(ang) * rr * sx, ty + math.sin(ang) * rr * 0.95))
        d = smooth_closed(pts)
        tuft = (f'<path d="{d}" fill="{FUR}" stroke="{INK}" stroke-width="{SW}" stroke-linejoin="round"/>'
                f'<path d="M {f(x-14*sx)},{ty+6} Q {f(x)},{ty+16} {f(x+14*sx)},{ty+6}" fill="none" stroke="#EBCDB3" stroke-width="3.6" stroke-linecap="round"/>'
                f'<path d="M {f(x-10*sx)},{ty-8} Q {f(x-3*sx)},{ty-14} {f(x+4*sx)},{ty-10}" fill="none" stroke="#EBCDB3" stroke-width="3" stroke-linecap="round"/>')
        svg += tuft
    ov = raster(svg).resize((SIZE, SIZE), Image.LANCZOS)
    a = body2.getchannel("A")
    nb = Image.alpha_composite(body2, ov)
    nb.putalpha(a)
    out = dict(poses[0]); out["body"] = nb
    _YAW[key] = out
    return out


def wisps(poses, g, k, n=4):
    """轉圈的弧形風圈＋甩出去的毛（身體兩側；左低右高表示旋轉方向）。k 越大越明顯。"""
    c = (250.0, 345.0 + g.get("bottom", 482) - 482)
    s = arcs(c, 196, r=170, n=2 if k > 0.5 else 1, w=5.0) + arcs(c, 16, r=170, n=2 if k > 0.5 else 1, w=5.0)
    # 甩出去的毛：左右各 1~2 小撮（短弧）
    for (x, y, dg) in ((68, 262, 150), (446, 396, -30), (72, 400, 205), (442, 262, 28)):
        if k <= 0.5 and x in (72, 442):
            continue
        p0 = (x, y + (c[1] - 345.0))
        v = dirv(dg)
        p1 = add(p0, v, 16 + 8 * k)
        m = add(add(p0, v, 8), (-v[1], v[0]), 4)
        s += brush(bez(p0, m, m, p1, 8), 5.0, 3.0)
    return s


def clip_spin(poses):
    # (標籤, 轉角, 幾何, 型態, 飛毛強度 0~1, 星星)
    seq = [
        ("蹲低蓄力", 0, dict(h=0.955, w=1.035, lag=-0.05), "face", 0, 0),
        ("起轉（45°）", 45, dict(h=1.03, w=1.0, lag=0.05, bottom=-10), "face", 0.3, 0),
        ("側面（90°）", 90, dict(h=1.04, w=0.99, lag=0.06, bottom=-20), "face", 0.7, 0),
        ("斜後（135°）", 135, dict(h=1.045, w=0.985, lag=0.06, bottom=-24), "face", 1.0, 0),
        ("背面（180°）露尾巴", 180, dict(h=1.045, w=0.985, lag=0.05, bottom=-24), "face", 1.0, 0),
        ("斜後（225°）", 225, dict(h=1.04, w=0.99, lag=0.05, bottom=-18), "face", 1.0, 0),
        ("側面（270°）", 270, dict(h=1.03, w=1.0, lag=0.04, bottom=-12), "face", 0.7, 0),
        ("轉回來（315°）", 315, dict(h=1.0, w=1.01, lag=0.02, bottom=-4), "face", 0.3, 0),
        ("落地（360°）", 360, dict(h=0.96, w=1.035, lag=-0.04), "dizzy", 0, 1),
        ("暈暈的（頭上小星星）", 360, dict(h=1.0, rot=-5), "dizzy", 0, 2),
        ("暈暈的（往另一邊晃）", 360, dict(h=1.0, rot=4), "dizzy", 0, 3),
        ("回待機", 360, dict(h=0.998), "face", 0, 0),
    ]
    frames = []
    for i, (lab, th, gk, kind, wk, st) in enumerate(seq):
        g = base_geom(poses, 0, **gk)
        pose = poses[0] if (i == 11) else yaw_pose(poses, th % 360 if th != 360 else 0, kind)
        front = ""
        if wk:
            front += wisps(poses, g, wk, n=4)
        if st:
            cx, cy = F(poses, g, 250, 150)
            cy -= 36
            ph = {1: 0.0, 2: 1.4, 3: 2.8}[st]
            for k in range(3):
                a = ph + k * 2 * math.pi / 3
                sx_, sy_ = cx + 64 * math.cos(a), cy + 15 * math.sin(a)
                front += star_svg((sx_, sy_), 11, deg=30 * i + 40 * k, lw=2.8)
        fr = {"g": g, "label": lab, "pose": pose, "front": front, "texts": []}
        frames.append(fr)
    return frames


SPIN_D = [220, 90, 80, 80, 80, 80, 80, 90, 160, 260, 260, 600]


CLIPS = {
    "pet": ("摸摸頭", clip_pet, PET_D, False,
            "客服鈕互動：使用者點「摸摸頭」。一隻小肉掌從右上飛來輕輕放在頭上來回摸，比比瞇眼享受、冒小愛心。"),
    "eat_grass": ("吃草", clip_eat, EAT_D, False,
                  "客服鈕互動：使用者點「餵牧草」。肉掌捧著一把牧草送到嘴邊，啃啃啃、臉頰鼓起，牧草越啃越短。"),
    "ball": ("玩球", clip_ball, BALL_D, False,
             "客服鈕互動：使用者點「玩球」。小球從右上弧線彈進來，比比蹲低、用頭頂把球頂回去，球再沿弧線飛走。"),
    "spin": ("轉圈圈", clip_spin, SPIN_D, False,
             "客服鈕互動：使用者點「轉圈圈」。原地轉一圈（臉在球面上轉到背面露尾巴再轉回來），毛飄起來，轉完有點暈、頭上小星星。"),
}


def write_story(rd, key, name, frs, durs, use):
    lines = [f"# 比比・{name}（{len(frs)} 格）", "",
             "- 需求：網頁版客服鈕「比比」互動素材（右下角 160px 顯示），要更像真的在陪伴你。",
             f"- 用途：{use}",
             "- 播放：**播一次不循環**（loop=1 播完停在最後一格＝待機姿勢）；顯示 160px、來源 512×512 透明、全身入鏡不裁切。",
             f"- 製作：`python scripts/anim/bibi_interact_g1.py --out <scratchpad>/bibi_g --repo-out docs/anim --only {key}`。",
             "- 身體：原圖 `site/brand/src/support_anim_1009.gif` 第 0 張的像素網格變形；五官在原圖座標補掉再重畫；"
             "場景座標同其他組（身體縮 0.75、中心 x=248、腳底 y=482）。手只畫貼身小肉掌（官方部件總表樣式），不畫手臂。",
             f"- 合計 {sum(durs)}ms；相鄰格皆有實際差異；最後一格＝待機（可直接接回待機動畫）。", "",
             "| 格 | 動作／表情 | 停留 ms |", "|---|---|---|"]
    for j, (fr, d) in enumerate(zip(frs, durs)):
        lines.append(f"| {j+1:02d} | {fr['label']} | {d} |")
    (rd / "storyboard.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def save_webps(imgs, durs, path160, path512, target_kb=60):
    sm = [im.resize((160, 160), Image.LANCZOS) for im in imgs]
    q = 82
    while True:
        sm[0].save(path160, save_all=True, append_images=sm[1:], duration=durs, loop=1, lossless=False, quality=q, method=6)
        kb = Path(path160).stat().st_size / 1024
        if kb <= target_kb or q <= 40:
            break
        q -= 8
    imgs[0].save(path512, save_all=True, append_images=imgs[1:], duration=durs, loop=1, lossless=False, quality=85, method=6)
    return kb, q


# ================================================================== 圖示（見下半）
from bibi_icons_g1 import make_icons  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="site/brand/src/support_anim_1009.gif")
    ap.add_argument("--out", required=True)
    ap.add_argument("--repo-out", default="docs/anim")
    ap.add_argument("--only", default="")
    ap.add_argument("--icons", action="store_true")
    a = ap.parse_args()
    out = Path(a.out)
    only = [x for x in a.only.split(",") if x]
    if a.icons:
        make_icons(Path(a.repo_out) / "bibi_icons")
        return
    poses = pose_tween.load_poses(Path(a.src))
    for key, (name, fn, durs, _loop, use) in CLIPS.items():
        if only and key not in only:
            continue
        frs = fn(poses)
        assert len(frs) == len(durs) == 12, key
        imgs = [render_g(poses, fr, BA.HUNINN) for fr in frs]
        fd = out / key / "frames"
        fd.mkdir(parents=True, exist_ok=True)
        for j, im in enumerate(imgs):
            im.save(fd / f"frame_{j+1:02d}.png")
        rd = Path(a.repo_out) / f"bibi_{key}"
        rd.mkdir(parents=True, exist_ok=True)
        sheet12(imgs, [f"{j+1:02d} {fr['label']}" for j, fr in enumerate(frs)], rd / "sheet_12.png")
        kb, q = save_webps(imgs, durs, rd / "anim.webp", out / key / "anim512.webp")
        write_story(rd, key, name, frs, durs, use)
        arr = [np.asarray(i).astype(int) for i in imgs]
        diffs = [int(np.abs(arr[k] - arr[k + 1]).sum() // 1000) for k in range(11)]
        print(key, f"anim.webp {kb:.0f}KB q{q}", "相鄰差(k)", diffs, flush=True)


if __name__ == "__main__":
    main()
