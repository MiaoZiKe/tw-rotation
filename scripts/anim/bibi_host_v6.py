"""動畫師：宣傳影片第 6 版的比比主持表情／動作（改版 v2 ＋ 新增 6 組），直接存進 `docs/anim/bibi_library/`。

為什麼有這支
------------
Andy 2026-10-17（看完宣傳影片 v5）：「在對表情動作上需要在多點優化」。
v5 用最多的 talk_*、face_nod、face_think、point_* 都只有「整顆上下晃＋換嘴」，這支把它們重做成 v2（另存新名，舊的不動，
舊影片可以重建），並新增 6 組主持用的動作。全部遵守：
- 比比是四腳天竺鼠：沒有手、沒有尾巴、不兩腳站立；這一版**連小肉掌也不畫**，指向改用「整隻往那邊傾＋鼻子帶路＋懸空箭頭」。
- 身體一律是原圖 `site/brand/src/support_anim_1009.gif` 第 0 張的像素（沿用 bibi_faces_c 的網格變形與五官重畫），
  場景座標同素材庫：512×512 透明、身體縮 0.75、中心 x=248、腳底 y=482。
- 每組都有：眨眼（半閉→閉→半閉）、嘴型三段（閉 ω／微張／張開）、耳朵次要動作（彈簧模擬，跟著身體加速度甩）、
  預備→主動作→回穩（擠壓伸展），第一格＝最後一格的下一格（待機），可無縫循環。

耳朵次要動作
------------
原圖耳朵是身體像素的一部分，所以在原圖座標把兩耳區域繞耳根旋轉（權重從耳心往外平滑衰減到 0，
不碰眼睛與腮紅），再交給 warp_body。耳朵角度由彈簧模擬：驅動＝頭頂的速度（往上竄耳朵往外甩、往下沉耳朵往上翹），
再加每格指定的偏移（害羞垂耳、驚訝豎耳）。彈簧跑三圈取最後一圈，所以循環接縫處耳朵也連續。

用法
----
    python scripts/anim/bibi_host_v6.py --out <scratchpad>/bibi_v6 [--only talk_happy_v2,happy_spin]
產出：docs/anim/bibi_library/<名>/key.png、sheet.png、anim.webp；<out>/frames/<名>/frame_XX.png；
<out>/check/<名>_bg3.png（白／黑／棋盤格三種底逐格總覽）；<out>/timing.json（時間表＋接觸表＋自動檢查結果）。
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).parent))
import bibi_actions as BA  # noqa: E402
import bibi_faces_c as C  # noqa: E402
import pose_tween  # noqa: E402
from bibi_actions import (INK, SIZE, f, P, brush, bez, sparkle, motion_lines, arcs, base_geom, fwd)  # noqa: E402
from bibi_faces_c import (face_pose, heart_svg, star_svg, drop_svg, dots_svg, render)  # noqa: E402
from bibi_scenes_b import smooth_closed, rrect_pts, jitter, shape  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
LIB = REPO / "docs/anim/bibi_library"
FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
ARROW, ARROW_LT = "#4AA8F0", "#BFE3FF"
GLOOM = "#8E93BE"

# ================================================================== 耳朵（原圖座標）
EAR = {  # 耳心、耳根（旋轉軸）
    "l": ((138.0, 204.0), (168.0, 236.0)),
    "r": ((364.0, 204.0), (336.0, 236.0)),
}
R_IN, R_OUT = 30.0, 58.0
_EARC = {}


def ear_warp(pose, al, ar):
    """al／ar：度，正值＝往外甩（左耳逆時針、右耳順時針，畫面上看）。"""
    key = (id(pose["body"]), round(al * 2) / 2, round(ar * 2) / 2)
    if key in _EARC:
        return _EARC[key]
    if abs(al) < 0.25 and abs(ar) < 0.25:
        return pose
    arr = np.asarray(pose["body"]).astype(np.float32)
    a = arr[..., 3:4] / 255.0
    pm = np.concatenate([arr[..., :3] * a, arr[..., 3:4]], 2)
    H, W = arr.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    sy, sx = yy.copy(), xx.copy()
    for side, ang in (("l", al), ("r", ar)):
        if abs(ang) < 0.25:
            continue
        (ecx, ecy), (px, py) = EAR[side]
        d = np.hypot(xx - ecx, yy - ecy)
        w = np.clip((R_OUT - d) / (R_OUT - R_IN), 0, 1)
        w = w * w * (3 - 2 * w)
        # 畫面上「往外」：左耳逆時針（y 往下的座標系是負角）、右耳順時針
        th = math.radians(-ang if side == "l" else ang) * w
        # 逆映射：輸出點繞耳根轉 -th 回到來源
        dx, dy = xx - px, yy - py
        c, s = np.cos(-th), np.sin(-th)
        m = w > 0
        sx[m] = (px + c * dx - s * dy)[m]
        sy[m] = (py + s * dx + c * dy)[m]
    out = np.stack([ndimage.map_coordinates(pm[..., k], [sy, sx], order=1, mode="constant", cval=0) for k in range(4)], 2)
    al_ = np.clip(out[..., 3:4], 0, 255)
    rgb = np.where(al_ > 0.5, out[..., :3] / np.maximum(al_ / 255.0, 1e-3), 0)
    im = Image.fromarray(np.clip(np.concatenate([rgb, al_], 2), 0, 255).astype(np.uint8), "RGBA")
    o = dict(pose); o["body"] = im
    _EARC[key] = o
    return o


def ear_spring(poses, gks, bias, durs, gain=1.1, k=0.22, damp=0.32):
    """彈簧：驅動＝頭頂速度（場景 px／格）；回傳每格 (左, 右) 角度。"""
    tops = []
    for gk in gks:
        g = base_geom(poses, 0, **gk)
        tops.append(fwd_s(poses, g, 256, 160))
    n = len(gks)
    x = np.zeros(2); v = np.zeros(2)
    res = []
    for loop in range(3):
        res = []
        for i in range(n):
            p0, p1 = tops[i - 1], tops[i]
            vy = p1[1] - p0[1]          # 正＝往下
            vx = p1[0] - p0[0]
            drive = -vy * gain           # 往上竄 → 往外甩
            tgt = np.array([drive + vx * 0.5 + bias[i][0], drive - vx * 0.5 + bias[i][1]])
            v += k * (tgt - x) - damp * v
            x += v
            x = np.clip(x, -26, 30)
            res.append((float(x[0]), float(x[1])))
    return res


# ================================================================== 臉外物件
def arrow_svg(c, deg, s=1.0, op=1.0):
    """懸空粗箭頭（藍、粗描邊、高光），c＝箭頭中心，deg＝指向（0 往右，正值往上）。"""
    pts = [(-34, -9), (6, -9), (6, -22), (36, 0), (6, 22), (6, 9), (-34, 9)]
    r = math.radians(-deg)
    T = [(c[0] + (x * math.cos(r) - y * math.sin(r)) * s, c[1] + (x * math.sin(r) + y * math.cos(r)) * s) for x, y in pts]
    d = "M " + " L ".join(P(p) for p in T) + " Z"
    hl = [(-28, -4), (2, -4)]
    H = [(c[0] + (x * math.cos(r) - y * math.sin(r)) * s, c[1] + (x * math.sin(r) + y * math.cos(r)) * s) for x, y in hl]
    g = (f'<path d="{d}" fill="{ARROW}" stroke="{INK}" stroke-width="{f(5.2*min(1.0, s))}" stroke-linejoin="round"/>'
         + brush(H, 3.4 * s, 3.0 * s, ARROW_LT))
    return g if op >= 1 else f'<g opacity="{op:.2f}">{g}</g>'


def sad_brows():
    """委屈八字眉（原圖座標）：內側高、外側低。bibi_faces_c 的 worry 在這張臉上看起來像生氣眉，所以另畫。"""
    out = ""
    for e, side in ((C.EYE_L, -1), (C.EYE_R, 1)):
        x, y = e[0], e[1] - 31
        inner = (x - side * 11, y - 6)
        outer = (x + side * 13, y + 4)
        out += brush(bez(inner, (x - side * 3, y - 6), (x + side * 6, y - 2), outer, 10), 5.6, 4.6)
    return out


SAD = sad_brows()


def gloom_svg(c, k):
    out = ""
    for j, dx in enumerate((-34, 0, 34)):
        x = c[0] + dx
        pts = [(x + 4 * math.sin(t * 2.6 + j), c[1] + t * 13 * k) for t in np.linspace(0, 3, 10)]
        out += brush(pts, 4.2, 3.2, GLOOM)
    return out


def bulb_svg(c, k=1.0):
    bulb = smooth_closed(jitter([(c[0] + 18 * k * math.cos(a), c[1] - 4 + 20 * k * math.sin(a))
                                 for a in np.linspace(0, 2 * math.pi, 12, endpoint=False)], 0.5, 4))
    return (f'<g transform="rotate(10,{f(c[0])},{f(c[1])})">' + shape(bulb, C.STAR, lw=4.4)
            + shape(smooth_closed(rrect_pts(c[0], c[1] + 22 * k, 16 * k, 10 * k, 3, 1, 2)), "#CFC6BD", lw=3.6)
            + brush(bez((c[0] - 6, c[1]), (c[0] - 3, c[1] - 8), (c[0] + 3, c[1] - 8), (c[0] + 6, c[1]), 8), 3.2, 3.2, C.STAR_DK)
            + '</g>' + motion_lines((c[0] + 2, c[1] - 4), 90, spread=42, r0=28 * k, length=10, n=3, w=4.4))


def note_svg(c, s=1.0):
    x, y = c
    return (f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="{f(8*s)}" ry="{f(6*s)}" fill="{INK}" transform="rotate(-20,{f(x)},{f(y)})"/>'
            + brush([(x + 7 * s, y - 1 * s), (x + 7 * s, y - 30 * s)], 3.6 * s, 3.6 * s)
            + brush(bez((x + 7 * s, y - 30 * s), (x + 14 * s, y - 26 * s), (x + 20 * s, y - 22 * s), (x + 18 * s, y - 12 * s), 8), 3.6 * s, 3.0 * s))


# ================================================================== 影格規格
def blink_eyes(i, at, base="dot"):
    """at＝閉眼那一格：at-1、at+1 半閉。"""
    if i == at:
        return "blink"
    if i in (at - 1, at + 1):
        return "half"
    return base


def rot_center(poses, gk, ang, lift=0.0):
    """繞身體中心轉 ang 度（不是繞腳底），lift＝身體中心往上移的量；回傳要合進 gk 的 cx／bottom 位移。"""
    g = base_geom(poses, 0, **gk)
    hh = g["h"] * 0.5
    r = math.radians(ang)
    # 腳底錨點 = 中心 − R(ang)·(0, −h/2)；中心固定在 (CX, GROUND − h/2 − lift)
    return dict(cx=-math.sin(r) * hh, bottom=-hh + math.cos(r) * hh - lift)


class Clip:
    def __init__(self, key, name, use, cat="主持"):
        self.key, self.name, self.use, self.cat = key, name, use, cat
        self.fr = []

    def add(self, lab, gk, face, ms, fx=None, ear=(0.0, 0.0), contact=True, burst=0):
        # 四腳著地：繞腳底轉超過 2° 會把一隻腳抬離地面，多出來的傾斜改用剪切（腳底線不動）
        r = gk.get("rot", 0.0)
        if 2.0 < abs(r) < 30:
            sg = 1 if r > 0 else -1
            gk = dict(gk, rot=2.0 * sg, sh=gk.get("sh", 0.0) + (r - 2.0 * sg) * 0.013)
        self.fr.append(dict(lab=lab, gk=gk, face=face, ms=ms, fx=fx, ear=ear, contact=contact, burst=burst))


def talk_base(c, mouths, accents=(), blink_at=None, brows=None, eyes="dot", looks=None, amp=1.0, hop=(),
              blush=None, fx=None, ms=80, lean=0.0, es=1.0):
    """說話：嘴越開身體越拉長（吸氣→出聲），閉嘴時擠一點；重音格頭抬高、瞇眼；hop＝小蹦。"""
    n = len(mouths)
    for i, m in enumerate(mouths):
        o = C.OPEN_AMT[m]
        ph = 2 * math.pi * i / n
        acc = i in accents
        h = 1 + amp * (0.03 * (o - 0.4) + (0.025 if acc else 0))
        gk = dict(h=h, w=1 / math.sqrt(h), lag=amp * (0.035 * (o - 0.4) + (0.05 if acc else 0)),
                  rot=lean + 1.8 * amp * math.sin(ph))
        if i in hop:
            gk.update(bottom=-14 * amp, h=gk["h"] * 1.03, w=gk["w"] * 0.985)
        if i - 1 in hop and i not in hop:
            gk.update(h=gk["h"] * 0.95, w=gk["w"] * 1.03)
        ey = "happy" if acc else eyes
        if blink_at is not None:
            ey = blink_eyes(i, blink_at, ey)
        lk = looks[i] if looks else (0.0, 0.0)
        face = dict(eyes=ey, mouth=m, brows=brows, blush=("soft" if acc else blush), look=lk, es=(es, es))
        lab = "說話：" + {"w": "閉嘴", "open_s": "微張", "open_m": "張開", "open_l": "大開", "o": "「喔」"}[m]
        if acc:
            lab += "（重音、瞇眼）"
        if blink_at is not None and abs(i - blink_at) <= 1:
            lab += "（眨眼）"
        c.add(lab, gk, face, ms, fx=(lambda g, i=i, m=m, acc=acc: fx(g, i, m, acc)) if fx else None,
              ear=((-10.0, -10.0) if acc else (0.0, 0.0)), contact=i not in hop)


def fwd_s(poses, g, x, y):
    """fwd＋剪切（sh：腳底不動、越高越往旁邊推，用來做「四腳著地的傾身」）。"""
    p = fwd(poses, g, x, y)
    return (p[0] + g.get("sh", 0.0) * (BA.GROUND - p[1]), p[1])


def sound(poses, g, i, n=2):
    return motion_lines(fwd_s(poses, g, 445, 236), 25, spread=30, r0=8, length=15 + 3 * (i % 2), n=n, w=5.0)


def build(poses):
    clips = []
    F = lambda g, x, y: fwd_s(poses, g, x, y)  # noqa: E731

    # ---------------------------------------------------------------- 1 talk_happy_v2
    c = Clip("talk_happy_v2", "說話・開心講 v2（三段嘴型、重音瞇眼抬頭、眨眼、耳朵跟著甩）", "旁白講解（輕鬆），取代 talk_happy", "表情")
    mouths = ["w", "open_s", "open_m", "open_s", "w", "open_m", "open_l", "open_m", "open_s", "w",
              "open_s", "open_m", "open_s", "w", "w", "open_s", "open_m", "open_l", "open_s", "w"]

    def fx1(g, i, m, acc):
        s = sound(poses, g, i) if C.OPEN_AMT[m] >= 0.7 else ""
        if acc:
            s += sparkle(F(g, 70, 196), 15) + sparkle(F(g, 445, 175), 12)
        return s
    talk_base(c, mouths, accents=(6, 17), blink_at=13, fx=fx1, ms=80)
    clips.append(c)

    # ---------------------------------------------------------------- 2 talk_explain_v2
    c = Clip("talk_explain_v2", "說話・認真講 v2（挑眉、往前一傾強調、眼神左右、眨眼）", "旁白講解（認真說明功能），取代 talk_explain", "表情")
    mouths = ["w", "open_s", "open_m", "open_s", "w", "o", "open_s", "open_m", "open_m", "open_s",
              "w", "w", "open_s", "open_m", "open_s", "w", "open_s", "open_m", "open_s", "w"]
    looks = [(3, -1)] * 8 + [(0, 0)] * 4 + [(-3, -1)] * 8

    def fx2(g, i, m, acc):
        s = ""
        if i in (7, 8):
            s += motion_lines(F(g, 256, 140), 90, spread=34, r0=6, length=13, n=3, w=4.6)
        if i == 8:
            s += sparkle(F(g, 440, 180), 13)
        return s
    talk_base(c, mouths, accents=(), blink_at=11, brows="raise", looks=looks, fx=fx2, ms=88, lean=0.0)
    for fr in c.fr:
        fr["gk"]["sh"] = -0.03
    # 第 6～9 格：預備（往後縮）→ 往前傾強調 → 回穩
    for i, add in ((5, dict(h=0.96, w=1.025, lag=-0.02, rot=-1.0, sh=-0.07)), (6, dict(h=0.985, rot=-0.5, sh=-0.04)),
                   (7, dict(h=1.05, w=0.975, lag=0.07, rot=1.0, sh=0.06)), (8, dict(h=1.035, lag=0.05, rot=1.0, sh=0.05)),
                   (9, dict(h=1.0, rot=0, sh=0.0))):
        c.fr[i]["gk"].update(add)
        c.fr[i]["lab"] += {5: "（預備：縮）", 7: "（往前傾強調）", 9: "（回穩）"}.get(i, "")
    clips.append(c)

    # ---------------------------------------------------------------- 3 talk_excited_v2
    c = Clip("talk_excited_v2", "說話・興奮講 v2（亮晶晶眼、兩次小蹦、落地擠壓、眨眼）", "旁白講解（亮點、新功能），取代 talk_excited", "表情")
    mouths = ["w", "open_s", "open_m", "open_l", "open_m", "open_s", "w", "open_m", "open_l", "open_s",
              "w", "open_s", "open_m", "open_l", "open_m", "open_s", "w", "w"]

    def fx3(g, i, m, acc):
        s = ""
        for j, (sx, sy, r0) in enumerate(((58, 200, 13), (452, 168, 15), (470, 300, 10), (40, 320, 9))):
            t = (i / 18 + j * 0.25) % 1
            sz = r0 * (0.3 + 0.7 * math.sin(math.pi * t))
            s += star_svg(F(g, sx, sy - 18 * t), sz, deg=40 * t + j * 20, lw=max(2.0, sz * 0.22))
        if C.OPEN_AMT[m] >= 0.7:
            s += sound(poses, g, i, 3)
        return s
    talk_base(c, mouths, accents=(), blink_at=10, eyes="shine", brows="up", blush="soft", fx=fx3, ms=82,
              amp=1.3, hop=(3, 4, 13), es=1.06)
    c.fr[2]["gk"].update(h=0.93, w=1.04, lag=-0.03); c.fr[2]["lab"] += "（預備蹲）"
    c.fr[12]["gk"].update(h=0.93, w=1.04, lag=-0.03); c.fr[12]["lab"] += "（預備蹲）"
    clips.append(c)

    # ---------------------------------------------------------------- 4 face_nod_v2
    c = Clip("face_nod_v2", "表情・點頭嗯嗯 v2（先抬頭聽、點兩下耳朵甩、嗯！睜眼、眨眼）", "同意、肯定，取代 face_nod", "表情")
    seq = [
        ("待機", dict(), dict(eyes="dot", mouth="w"), 0),
        ("聽著（抬頭預備）", dict(h=1.025, w=0.99, lag=0.05), dict(eyes="dot", mouth="open_s", look=(0, -2)), 0),
        ("抬到最高", dict(h=1.035, w=0.985, lag=0.07), dict(eyes="dot", mouth="open_s", look=(0, -3)), 0),
        ("點頭（下）", dict(h=0.95, w=1.03, lag=-0.10), dict(eyes="happy", mouth="w"), 1),
        ("點頭（最低、壓扁）", dict(h=0.92, w=1.045, lag=-0.14), dict(eyes="happy", mouth="w"), 2),
        ("回彈（上）", dict(h=1.03, w=0.985, lag=0.04), dict(eyes="happy", mouth="open_s"), 2),
        ("點頭（下）", dict(h=0.95, w=1.03, lag=-0.10), dict(eyes="happy", mouth="w"), 3),
        ("點頭（最低）", dict(h=0.93, w=1.04, lag=-0.13), dict(eyes="happy", mouth="w"), 3),
        ("回彈（上）", dict(h=1.03, w=0.985, lag=0.04), dict(eyes="happy", mouth="open_s"), 3),
        ("嗯！（睜眼、嘴張開）", dict(h=1.04, w=0.98, lag=0.03), dict(eyes="shine", mouth="open_m", blush="soft"), 4),
        ("肯定（閃光）", dict(h=1.01), dict(eyes="shine", mouth="open_s", blush="soft"), 4),
        ("回穩（輕壓）", dict(h=0.98, w=1.01), dict(eyes="dot", mouth="w"), 0),
        ("眨眼（半閉）", dict(h=1.0), dict(eyes="half", mouth="w"), 0),
        ("眨眼（閉）", dict(h=1.0), dict(eyes="blink", mouth="w"), 0),
        ("眨眼（半閉）", dict(h=1.0), dict(eyes="half", mouth="w"), 0),
        ("回待機", dict(h=0.997), dict(eyes="dot", mouth="w"), 0),
    ]
    ms = [140, 90, 80, 70, 90, 70, 70, 90, 70, 120, 110, 90, 50, 60, 50, 140]

    def fxn(st, i):
        def _f(g):
            s, tx = "", ""
            if st:
                cc = F(g, 420, 140)
                if st >= 2:
                    s += _txt("嗯", (cc[0] - 4, cc[1]), 10, 30)
                if st >= 3:
                    s += _txt("嗯", (cc[0] + 30, cc[1] + 26), 16, 26)
                if i in (3, 4, 6, 7):
                    s += arcs(F(g, 256, 118), 90, r=18, n=2, w=4.2)
                if st == 4:
                    s += sparkle(F(g, 80, 170), 13 if i == 9 else 9) + sparkle(F(g, 450, 210), 9 if i == 9 else 13)
            return s
        return _f
    for i, ((lab, gk, face, st), m) in enumerate(zip(seq, ms)):
        c.add(lab, gk, face, m, fx=fxn(st, i), ear=(-4.0, -4.0) if st == 4 else (0.0, 0.0))
    clips.append(c)

    # ---------------------------------------------------------------- 5 face_think_v2
    c = Clip("face_think_v2", "表情・思考 v2（歪頭往上看、單耳抽動、點點點、眨眼、蹦起想到了）", "提出疑問、思考，取代 face_think", "表情")
    seq = [
        ("待機", dict(), dict(eyes="dot", mouth="w"), 0, (0, 0)),
        ("眼睛往上飄", dict(lag=0.02), dict(eyes="dot", mouth="w", look=(3, -4)), 0, (0, 0)),
        ("歪頭（預備）", dict(lag=0.04, rot=-3, h=0.99), dict(eyes="dot", mouth="o", look=(5, -6)), 0, (0, 0)),
        ("歪到底、往上看", dict(lag=0.06, rot=-6), dict(eyes="dot", mouth="o", look=(6, -8)), 1, (0, 0)),
        ("嗯…（一點）", dict(lag=0.06, rot=-6.5), dict(eyes="dot", mouth="w", look=(6, -8)), 1, (0, -8)),
        ("右耳抽一下", dict(lag=0.06, rot=-6), dict(eyes="dot", mouth="w", look=(6, -8)), 2, (0, 12)),
        ("嗯…（兩點）", dict(lag=0.06, rot=-6.5), dict(eyes="dot", mouth="open_s", look=(4, -8)), 2, (0, -4)),
        ("眨眼（半閉）", dict(lag=0.06, rot=-6), dict(eyes="half", mouth="w", look=(2, -6)), 3, (0, 0)),
        ("眨眼（閉）", dict(lag=0.06, rot=-6), dict(eyes="blink", mouth="w"), 3, (0, 0)),
        ("眨眼（半閉）、眼睛換邊", dict(lag=0.06, rot=-5.5), dict(eyes="half", mouth="w", look=(-3, -6)), 3, (0, 0)),
        ("嗯…（三點）往另一邊看", dict(lag=0.06, rot=-5), dict(eyes="dot", mouth="o", look=(-5, -8)), 3, (0, 0)),
        ("點點跳一下", dict(lag=0.07, rot=-5.5), dict(eyes="dot", mouth="wavy", look=(-4, -8)), 4, (-8, 0)),
        ("還在想", dict(lag=0.06, rot=-5), dict(eyes="dot", mouth="w", look=(2, -8)), 3, (6, 0)),
        ("預備：縮（快想到了）", dict(h=0.93, w=1.04, lag=-0.03, rot=-2), dict(eyes="dot", mouth="w", es=(0.85, 0.85)), 3, (0, 0)),
        ("想到了！蹦起（拉長）", dict(h=1.08, w=0.95, lag=-0.05, bottom=-18), dict(eyes="shine", mouth="open_l", brows="up"), 5, (-10, -10)),
        ("最高點", dict(h=1.04, w=0.98, bottom=-22), dict(eyes="shine", mouth="open_m", brows="up"), 5, (-10, -10)),
        ("落地壓扁", dict(h=0.92, w=1.045, lag=0.03), dict(eyes="happy", mouth="open_m", brows="up", blush="soft"), 6, (0, 0)),
        ("回彈", dict(h=1.03, w=0.985), dict(eyes="shine", mouth="open_s", blush="soft"), 6, (0, 0)),
        ("回穩", dict(h=0.99, w=1.005), dict(eyes="dot", mouth="open_s"), 6, (0, 0)),
        ("回待機", dict(h=0.997), dict(eyes="dot", mouth="w"), 0, (0, 0)),
    ]
    ms = [140, 100, 90, 110, 120, 70, 120, 50, 60, 50, 140, 110, 120, 80, 70, 80, 80, 80, 100, 140]

    def fxt(dots, i):
        def _f(g):
            s = ""
            if 1 <= dots <= 4:
                b = F(g, 380, 112)
                s += dots_svg((b[0] - 4, b[1]), min(dots, 3), bounce=8 if dots == 4 else 0)
            elif dots >= 5:
                s += bulb_svg(F(g, 400, 104), 1.0 if dots == 5 else 0.9)
            if i == 14:
                s += motion_lines((CXg(g) - 110, 470), 200, spread=18, r0=0, length=16, n=2, w=4.6) + \
                    motion_lines((CXg(g) + 110, 470), -20, spread=18, r0=0, length=16, n=2, w=4.6)
            return s
        return _f
    for i, ((lab, gk, face, dots, ear), m) in enumerate(zip(seq, ms)):
        c.add(lab, gk, face, m, fx=fxt(dots, i), ear=ear, contact=i not in (14, 15))
    clips.append(c)

    # ---------------------------------------------------------------- 6–8 point_*_v2
    for key, nm, deg, use, hk, lagk, look, apos in (
        ("point_r_v2", "指向・右 v2（往後縮預備→整隻往右傾、鼻子帶路、箭頭彈出、眨眼）", 0, "指向畫面右側的重點，取代 point_r",
         1.04, 0.03, (7, 0), (470, 300)),
        ("point_ur_v2", "指向・右上 v2（縮→往右上伸長、箭頭彈出、眨眼）", 35, "指向右上方的標題／數字，取代 point_ur",
         1.07, 0.08, (6, -6), (468, 205)),
        ("point_dr_v2", "指向・右下 v2（縮→往右下探頭、箭頭彈出、眨眼）", -35, "指向右下方的按鈕／表格，取代 point_dr",
         0.95, -0.08, (6, 6), (470, 400)),
    ):
        c = Clip(key, nm, use, "動作")
        seq = [
            ("待機", dict(), dict(eyes="dot", mouth="w"), 0, (0, 0)),
            ("看過去", dict(rot=0.5), dict(eyes="dot", mouth="w", look=look), 0, (0, 0)),
            ("預備：往左後縮", dict(h=0.94, w=1.035, rot=-4, cx=-6, lag=-0.02), dict(eyes="dot", mouth="w", look=look, es=(0.9, 0.9)), 0, (0, 0)),
            ("往指的方向傾（伸展）", dict(h=hk + 0.02, w=0.975, rot=7, cx=10, lag=lagk), dict(eyes="shine", mouth="open_m", look=look, brows="up"), 0.6, (-6, 8)),
            ("傾到底（過頭）", dict(h=hk + 0.01, w=0.98, rot=9, cx=14, lag=lagk * 1.2), dict(eyes="shine", mouth="open_l", look=look, brows="up"), 1.25, (-4, 10)),
            ("回一點（箭頭定位）", dict(h=hk, w=0.985, rot=6, cx=10, lag=lagk), dict(eyes="shine", mouth="open_m", look=look), 0.95, (0, 4)),
            ("「看這裡」", dict(h=hk, w=0.985, rot=6.5, cx=11, lag=lagk), dict(eyes="dot", mouth="open_s", look=look), 1.05, (0, 0)),
            ("箭頭戳一下", dict(h=hk, w=0.985, rot=7, cx=12, lag=lagk), dict(eyes="dot", mouth="open_m", look=look), 1.0, (0, 0)),
            ("眨眼（半閉）", dict(h=hk, w=0.985, rot=6.5, cx=11, lag=lagk), dict(eyes="half", mouth="w", look=look), 1.0, (0, 0)),
            ("眨眼（閉）", dict(h=hk, w=0.985, rot=6.5, cx=11, lag=lagk), dict(eyes="blink", mouth="w"), 1.0, (0, 0)),
            ("眨眼（半閉）", dict(h=hk, w=0.985, rot=6.5, cx=11, lag=lagk), dict(eyes="half", mouth="w", look=look), 1.0, (0, 0)),
            ("箭頭戳一下", dict(h=hk, w=0.985, rot=7, cx=12, lag=lagk), dict(eyes="dot", mouth="open_s", look=look), 1.0, (0, 0)),
            ("轉回鏡頭（回穩）", dict(h=0.97, w=1.02, rot=1.5, cx=3), dict(eyes="dot", mouth="open_s"), 0.6, (0, 0)),
            ("輕彈", dict(h=1.015, w=0.995, rot=-0.8, cx=0), dict(eyes="dot", mouth="w"), 0, (0, 0)),
            ("微笑", dict(h=1.0), dict(eyes="happy", mouth="w", blush="soft"), 0, (0, 0)),
            ("回待機", dict(h=0.997), dict(eyes="dot", mouth="w"), 0, (0, 0)),
        ]
        ms = [130, 80, 90, 60, 70, 80, 110, 90, 50, 60, 50, 90, 90, 80, 110, 130]

        def fxp(sc, i, deg=deg, apos=apos):
            def _f(g):
                if not sc:
                    return ""
                poke = 8 if "戳" in c_lab(i) else 0
                r = math.radians(deg)
                pc = (apos[0] + math.cos(r) * poke, apos[1] - math.sin(r) * poke)
                s = arrow_svg(pc, deg, 0.9 * sc, op=min(1.0, sc / 0.6))
                if i in (3, 4):
                    s += motion_lines((pc[0] - 40, pc[1]), 180 - deg, spread=26, r0=0, length=14, n=2, w=4.2)
                if poke:
                    s += sparkle((pc[0] + math.cos(r) * 46, pc[1] - math.sin(r) * 46), 10)
                return s
            return _f
        labs = [s[0] for s in seq]
        c_lab = labs.__getitem__  # noqa: E731
        for i, ((lab, gk, face, sc, ear), m) in enumerate(zip(seq, ms)):
            c.add(lab, gk, face, m, fx=fxp(sc, i), ear=ear)
        clips.append(c)

    # ================================================================ 新增 6 組
    # ---------------------------------------------------------------- happy_spin
    c = Clip("happy_spin", "開心蹦跳轉一圈（天竺鼠 popcorn：蹲→跳起空中轉一圈→落地）", "好消息、上線、開心結尾", "主持")
    spin = [0, 0, 0, 0, 45, 110, 180, 250, 315, 360, 360, 360]
    seq = []
    seq.append(("待機", dict(), dict(eyes="dot", mouth="w"), 0, 0))
    seq.append(("發現好事（眼睛亮）", dict(h=1.01), dict(eyes="shine", mouth="open_s"), 0, 0))
    seq.append(("預備蹲（壓扁）", dict(h=0.9, w=1.06, lag=-0.03), dict(eyes="happy", mouth="w", blush="soft"), 0, 0))
    seq.append(("蹬地起跳（拉長）", dict(h=1.1, w=0.94, lag=-0.05), dict(eyes="happy", mouth="open_m", blush="soft"), 0, 40))
    for j, ang in enumerate((60, 130, 200, 270, 330)):
        seq.append((f"空中轉圈 {ang}°", dict(h=1.0, w=1.0, rot=ang), dict(eyes="happy", mouth="open_l", blush="soft"), ang, 95 + 15 * math.sin(math.pi * (j + 1) / 6)))
    seq.append(("轉完、往下落", dict(h=1.04, w=0.97, rot=360), dict(eyes="shine", mouth="open_m", blush="soft"), 360, 40))
    seq.append(("落地壓扁", dict(h=0.88, w=1.07, lag=0.04), dict(eyes="happy", mouth="open_m", blush="soft"), 0, 0))
    seq.append(("回彈", dict(h=1.05, w=0.97, lag=-0.02), dict(eyes="shine", mouth="open_l", blush="soft"), 0, 0))
    seq.append(("小彈", dict(h=0.97, w=1.02), dict(eyes="happy", mouth="open_s", blush="soft"), 0, 0))
    seq.append(("開心笑", dict(h=1.01), dict(eyes="happy", mouth="open_m", blush="soft"), 0, 0))
    seq.append(("眨眼（半閉）", dict(h=1.0), dict(eyes="half", mouth="open_s"), 0, 0))
    seq.append(("眨眼（閉）", dict(h=1.0), dict(eyes="blink", mouth="w"), 0, 0))
    seq.append(("眨眼（半閉）", dict(h=1.0), dict(eyes="half", mouth="w"), 0, 0))
    seq.append(("回待機", dict(h=0.997), dict(eyes="dot", mouth="w"), 0, 0))
    ms = [120, 90, 90, 60, 60, 60, 60, 60, 60, 70, 80, 80, 80, 110, 50, 60, 50, 140]
    for i, ((lab, gk, face, ang, lift), m) in enumerate(zip(seq, ms)):
        gk = dict(gk)
        if ang or lift:
            rc = rot_center(poses, {k: v for k, v in gk.items() if k != "rot"}, gk.get("rot", 0.0), lift)
            gk["cx"] = gk.get("cx", 0) + rc["cx"]; gk["bottom"] = gk.get("bottom", 0) + rc["bottom"]

        def fxs(g, i=i, ang=ang, lift=lift):
            s = ""
            if 4 <= i <= 8:
                cx, cy = BA.CX, BA.GROUND - 140 - lift
                s += arcs((cx, cy), 0, r=150, n=1, w=5) + arcs((cx, cy), 180, r=150, n=1, w=5)
                s += sparkle((cx - 170, cy - 70), 12) + sparkle((cx + 170, cy + 40), 10)
            if i == 3:
                s += motion_lines((BA.CX - 90, 478), 200, spread=18, r0=0, length=16, n=2, w=4.6) + \
                    motion_lines((BA.CX + 90, 478), -20, spread=18, r0=0, length=16, n=2, w=4.6)
            if i == 10:
                s += motion_lines((BA.CX - 150, 470), 160, spread=22, r0=4, length=12, n=2, w=4.6) + \
                    motion_lines((BA.CX + 150, 470), 20, spread=22, r0=4, length=12, n=2, w=4.6)
            if 10 <= i <= 13:
                s += star_svg((BA.CX - 150, 230 - 8 * (i - 10)), 13, deg=15 * i) + star_svg((BA.CX + 160, 200 - 8 * (i - 10)), 10, deg=-15 * i)
            return s
        c.add(lab, gk, face, m, fx=fxs, ear=(10, 10) if 4 <= i <= 8 else (0, 0), contact=not (3 <= i <= 9))
    clips.append(c)

    # ---------------------------------------------------------------- shy_rub
    c = Clip("shy_rub", "害羞蹭蹭（低頭偷看→臉頰左右蹭、垂耳、小愛心）", "被稱讚、不好意思、撒嬌", "主持")
    seq = [("待機", dict(), dict(eyes="dot", mouth="w"), (0, 0), 0),
           ("被誇了（眼睛往下）", dict(h=0.99, lag=-0.03), dict(eyes="dot", mouth="w", look=(0, 4), blush="soft"), (0, 0), 0),
           ("眨眼（半閉）", dict(h=0.98, lag=-0.05), dict(eyes="half", mouth="wavy", look=(0, 4), blush="lines"), (8, 8), 0),
           ("眨眼（閉）", dict(h=0.97, lag=-0.06), dict(eyes="blink", mouth="wavy", blush="lines"), (12, 12), 0),
           ("偷看鏡頭", dict(h=0.97, lag=-0.05, rot=-2), dict(eyes="half", mouth="w", look=(-3, 2), blush="lines"), (12, 12), 1)]
    for j in range(10):
        ph = 2 * math.pi * j / 5
        sw = math.sin(ph)
        seq.append((f"蹭蹭（{'左' if sw < 0 else '右'}）", dict(h=0.97 - 0.015 * abs(sw), w=1.02 + 0.02 * abs(sw), lag=-0.05,
                                                           rot=5 * sw, cx=7 * sw),
                    dict(eyes="happy", mouth="w" if j % 3 else "open_s", blush="lines"), (14 - 6 * sw, 14 + 6 * sw), 1 + j))
    seq += [("停下、偷笑", dict(h=0.985, lag=-0.02), dict(eyes="happy", mouth="open_s", blush="lines"), (8, 8), 11),
            ("抬頭微笑", dict(h=1.01, lag=0.02), dict(eyes="dot", mouth="open_m", blush="soft"), (0, 0), 0),
            ("回穩", dict(h=0.99), dict(eyes="dot", mouth="w", blush="soft"), (0, 0), 0),
            ("回待機", dict(h=0.997), dict(eyes="dot", mouth="w"), (0, 0), 0)]
    ms = [130, 100, 60, 80, 120] + [85] * 10 + [110, 100, 90, 130]
    for i, ((lab, gk, face, ear, ht), m) in enumerate(zip(seq, ms)):
        def fxr(g, ht=ht, i=i):
            s = ""
            if ht:
                for j, (x0, sz, sp) in enumerate(((90, 11, 0.0), (420, 9, 0.45), (380, 7, 0.75))):
                    t = ((ht / 11) + sp) % 1
                    if t < 0.92:
                        s += heart_svg(F(g, x0, 200 - 160 * t), sz * (0.6 + 0.6 * math.sin(math.pi * t)), deg=-12 + 24 * j,
                                       lw=2.6, op=min(1.0, 2.5 * (1 - t)))
            if 5 <= i <= 14:
                sd = 1 if math.sin(2 * math.pi * (i - 5) / 5) > 0 else -1
                s += arcs(F(g, 256 + sd * 200, 300), 0 if sd > 0 else 180, r=20, n=2, w=4.0)
            return s
        c.add(lab, gk, face, m, fx=fxr, ear=ear)
    clips.append(c)

    # ---------------------------------------------------------------- surprise_jump
    c = Clip("surprise_jump", "驚訝跳起（咦？縮→跳起豎耳炸毛、！、落地擠壓→眨眼回神）", "驚人數字、意外消息", "主持")
    seq = [("待機", dict(), dict(eyes="dot", mouth="w"), 0, 0, (0, 0)),
           ("咦？（眼睛縮小）", dict(h=0.98, lag=0.02), dict(eyes="dot", mouth="o", es=(0.8, 0.8)), 0, 0, (0, 0)),
           ("預備：縮成一團", dict(h=0.88, w=1.07, lag=-0.04), dict(eyes="dot", mouth="o", es=(0.75, 0.75)), 0, 0, (0, 0)),
           ("嚇跳起！（拉長）", dict(h=1.12, w=0.93, lag=-0.07, bottom=-30), dict(eyes="wide", mouth="O", es=(1.15, 1.15)), 1.0, 1, (-14, -14)),
           ("最高點（毛炸開）", dict(h=1.06, w=0.97, bottom=-44), dict(eyes="wide", mouth="O", es=(1.22, 1.22)), 1.2, 1, (-16, -16)),
           ("往下落", dict(h=1.04, w=0.98, bottom=-22), dict(eyes="wide", mouth="O", es=(1.18, 1.18)), 1.0, 2, (-6, -6)),
           ("落地壓扁", dict(h=0.88, w=1.07, lag=0.04), dict(eyes="wide", mouth="O", es=(1.12, 1.12)), 0.85, 2, (0, 0)),
           ("回彈", dict(h=1.05, w=0.97), dict(eyes="wide", mouth="o", es=(1.1, 1.1)), 0.6, 2, (0, 0)),
           ("抖（左）", dict(h=1.0, rot=-2.5, cx=-3), dict(eyes="wide", mouth="o", es=(1.06, 1.06)), 0.4, 0, (0, 0)),
           ("抖（右）", dict(h=1.0, rot=2.5, cx=3), dict(eyes="wide", mouth="o", es=(1.06, 1.06)), 0.25, 0, (0, 0)),
           ("眨眼（半閉）", dict(h=0.99), dict(eyes="half", mouth="o"), 0, 0, (0, 0)),
           ("眨眼（閉）", dict(h=0.99), dict(eyes="blink", mouth="open_s"), 0, 0, (0, 0)),
           ("眨眼（半閉）", dict(h=0.99), dict(eyes="half", mouth="open_s"), 0, 0, (0, 0)),
           ("回神「哇」", dict(h=1.02, lag=0.02), dict(eyes="shine", mouth="open_m"), 0, 0, (0, 0)),
           ("回穩", dict(h=0.99), dict(eyes="dot", mouth="w"), 0, 0, (0, 0)),
           ("回待機", dict(h=0.997), dict(eyes="dot", mouth="w"), 0, 0, (0, 0))]
    ms = [130, 100, 90, 60, 90, 60, 80, 80, 60, 60, 50, 60, 50, 110, 90, 130]
    for i, ((lab, gk, face, bu, ex, ear), m) in enumerate(zip(seq, ms)):
        def fxj(g, ex=ex, i=i):
            s = ""
            if ex:
                top = F(g, 256, 120)
                s += BA.exmark((top[0] + 2, top[1] - 26), k=1.15 if ex == 1 else 1.0, deg=4)
                s += motion_lines((top[0] - 80, top[1] + 18), 140, spread=28, r0=6, length=15, n=3, w=5) + \
                    motion_lines((top[0] + 88, top[1] + 14), 40, spread=28, r0=6, length=15, n=3, w=5)
            if i == 3:
                s += motion_lines((BA.CX - 100, 480), 200, spread=18, r0=0, length=16, n=2, w=4.6) + \
                    motion_lines((BA.CX + 100, 480), -20, spread=18, r0=0, length=16, n=2, w=4.6)
            if i == 6:
                s += motion_lines((BA.CX - 160, 470), 160, spread=22, r0=4, length=12, n=2, w=4.6) + \
                    motion_lines((BA.CX + 160, 470), 20, spread=22, r0=4, length=12, n=2, w=4.6)
            if i in (8, 9):
                s += drop_svg(F(g, 400, 205), 8.5, deg=-20)
            return s
        c.add(lab, gk, face, m, fx=fxj, ear=ear, burst=bu, contact=i not in (3, 4, 5))
    clips.append(c)

    # ---------------------------------------------------------------- proud_shine
    c = Clip("proud_shine", "得意抬頭閃光（吸氣挺胸→閉眼抬下巴、頭頂叮一聲閃光、偷睜一眼）", "自豪的功能介紹、帥氣亮相", "主持")
    seq = [("待機", dict(), dict(eyes="dot", mouth="w"), 0, (0, 0)),
           ("預備：吸氣（微縮）", dict(h=0.96, w=1.025, lag=-0.02), dict(eyes="dot", mouth="open_s"), 0, (0, 0)),
           ("挺胸（拉長）", dict(h=1.05, w=0.975, lag=0.06), dict(eyes="half", mouth="w", brows="up"), 0, (-6, -6)),
           ("閉眼抬下巴", dict(h=1.06, w=0.97, lag=0.13, rot=-3), dict(eyes="happy", mouth="w", brows="up"), 1, (-10, -10)),
           ("叮！閃光（最亮）", dict(h=1.065, lag=0.15, rot=-4), dict(eyes="happy", mouth="w", brows="up", blush="soft"), 3, (-10, -10)),
           ("哼～", dict(h=1.06, lag=0.14, rot=-4.5), dict(eyes="happy", mouth="open_s", brows="up", blush="soft"), 2, (-8, -8)),
           ("得意晃（左）", dict(h=1.06, lag=0.14, rot=-6), dict(eyes="happy", mouth="w", brows="up", blush="soft"), 2, (-6, -10)),
           ("得意晃（右）", dict(h=1.06, lag=0.14, rot=-2), dict(eyes="happy", mouth="open_s", brows="up", blush="soft"), 3, (-10, -6)),
           ("得意晃（左）", dict(h=1.06, lag=0.14, rot=-5), dict(eyes="happy", mouth="w", brows="up", blush="soft"), 2, (-6, -10)),
           ("偷睜一眼（半）", dict(h=1.055, lag=0.13, rot=-4), dict(eyes=("happy", "half"), mouth="w", brows="up", blush="soft"), 2, (-8, -8)),
           ("偷睜一眼（看鏡頭）", dict(h=1.055, lag=0.13, rot=-4), dict(eyes=("happy", "dot"), mouth="open_m", brows="up", blush="soft"), 3, (-8, -8)),
           ("再閉回去", dict(h=1.055, lag=0.13, rot=-4), dict(eyes="happy", mouth="w", brows="up", blush="soft"), 2, (-8, -8)),
           ("下巴放下（壓）", dict(h=0.97, w=1.02, lag=0.0, rot=-1), dict(eyes="happy", mouth="w"), 1, (0, 0)),
           ("回彈", dict(h=1.015, w=0.995), dict(eyes="dot", mouth="open_s"), 0, (0, 0)),
           ("眨眼（半閉）", dict(h=1.0), dict(eyes="half", mouth="w"), 0, (0, 0)),
           ("眨眼（閉）", dict(h=1.0), dict(eyes="blink", mouth="w"), 0, (0, 0)),
           ("眨眼（半閉）", dict(h=1.0), dict(eyes="half", mouth="w"), 0, (0, 0)),
           ("回待機", dict(h=0.997), dict(eyes="dot", mouth="w"), 0, (0, 0))]
    ms = [130, 100, 80, 90, 110, 100, 100, 100, 100, 70, 130, 90, 80, 80, 50, 60, 50, 140]
    for i, ((lab, gk, face, sp, ear), m) in enumerate(zip(seq, ms)):
        def fxp2(g, sp=sp, i=i):
            if not sp:
                return ""
            k = {1: 0.55, 2: 0.85, 3: 1.15}[sp]
            top = F(g, 300, 130)
            s = star_svg((top[0] + 120, top[1] - 30), 16 * k, deg=25 * i, lw=3.4)
            s += sparkle(F(g, 470, 210), 10 * k) + sparkle(F(g, 70, 160), 12 * k * (1.1 if i % 2 else 0.8))
            s += motion_lines(F(g, 256, 128), 90, spread=34, r0=6, length=12 * k, n=3, w=4.6)
            if i == 4:
                s += motion_lines((top[0] + 120, top[1] - 30), 90, spread=60, r0=20, length=14, n=6, w=4.0)
            return s
        c.add(lab, gk, face, m, fx=fxp2, ear=ear)
    clips.append(c)

    # ---------------------------------------------------------------- sulk_curl
    c = Clip("sulk_curl", "委屈縮成一團後恢復（扁嘴含淚→縮成球、烏雲線→深吸氣蹦回來、甩毛、笑）", "虧損、壞消息、先委屈再打起精神", "主持")
    seq = [("待機", dict(), dict(eyes="dot", mouth="w"), 0, (0, 0)),
           ("嗯…？（眼睛往下）", dict(h=0.99, lag=-0.02), dict(eyes="dot", mouth="wavy", look=(0, 3), extra=SAD), 0, (4, 4)),
           ("扁嘴（委屈）", dict(h=0.97, w=1.015, lag=-0.04), dict(eyes="shine", mouth="wavy", look=(0, 3), extra=SAD), 1, (8, 8)),
           ("含淚", dict(h=0.96, w=1.02, lag=-0.05), dict(eyes="shine", mouth="wavy", look=(0, 4), extra=SAD, es=(1.08, 1.08)), 2, (12, 12)),
           ("開始縮", dict(h=0.9, w=1.06, lag=-0.07), dict(eyes="line", mouth="wavy", extra=SAD), 3, (16, 16)),
           ("縮成一團", dict(h=0.84, w=1.09, lag=-0.09), dict(eyes="line", mouth="wavy", extra=SAD), 4, (20, 20)),
           ("縮著（微抖）", dict(h=0.83, w=1.095, lag=-0.09, rot=-1, cx=-2), dict(eyes="line", mouth="wavy", extra=SAD), 4, (21, 20)),
           ("縮著（微抖）", dict(h=0.84, w=1.09, lag=-0.09, rot=1, cx=2), dict(eyes="line", mouth="wavy", extra=SAD), 4, (20, 21)),
           ("縮著（吸鼻子）", dict(h=0.85, w=1.085, lag=-0.08), dict(eyes="line", mouth="tiny", extra=SAD), 4, (20, 20)),
           ("偷偷睜眼", dict(h=0.85, w=1.085, lag=-0.08), dict(eyes="half", mouth="tiny", extra=SAD), 5, (18, 18)),
           ("深吸一口氣（更縮）", dict(h=0.82, w=1.1, lag=-0.1), dict(eyes="blink", mouth="w"), 5, (18, 18)),
           ("蹦回來！（拉長）", dict(h=1.1, w=0.94, lag=-0.04, bottom=-16), dict(eyes="shine", mouth="open_l", brows="up"), 6, (-10, -10)),
           ("落地", dict(h=0.93, w=1.045, lag=0.03), dict(eyes="happy", mouth="open_m"), 6, (0, 0)),
           ("甩毛（左）", dict(h=1.01, rot=-4, cx=-4), dict(eyes="happy", mouth="open_s"), 7, (0, 0)),
           ("甩毛（右）", dict(h=1.01, rot=4, cx=4), dict(eyes="happy", mouth="open_s"), 7, (0, 0)),
           ("甩毛（左）", dict(h=1.0, rot=-2, cx=-2), dict(eyes="happy", mouth="w"), 7, (0, 0)),
           ("打起精神", dict(h=1.03, w=0.985, lag=0.04), dict(eyes="shine", mouth="open_m", brows="up", blush="soft"), 8, (-4, -4)),
           ("回穩", dict(h=0.99, w=1.005), dict(eyes="dot", mouth="open_s", blush="soft"), 0, (0, 0)),
           ("眨眼（半閉）", dict(h=1.0), dict(eyes="half", mouth="w"), 0, (0, 0)),
           ("眨眼（閉）", dict(h=1.0), dict(eyes="blink", mouth="w"), 0, (0, 0)),
           ("眨眼（半閉）", dict(h=1.0), dict(eyes="half", mouth="w"), 0, (0, 0)),
           ("回待機", dict(h=0.997), dict(eyes="dot", mouth="w"), 0, (0, 0))]
    ms = [130, 120, 120, 130, 90, 120, 90, 90, 130, 120, 110, 70, 80, 60, 60, 70, 120, 100, 50, 60, 50, 130]
    for i, ((lab, gk, face, st, ear), m) in enumerate(zip(seq, ms)):
        def fxc(g, st=st, i=i):
            s = ""
            if 2 <= st <= 5:
                e1 = F(g, 192, 285); e2 = F(g, 310, 283)
                if st == 2:
                    s += drop_svg((e1[0], e1[1] + 2), 5.5) + drop_svg((e2[0], e2[1] + 2), 5.5)
                else:
                    tt = (i - 3) * 6
                    s += drop_svg((e1[0] - 4, e1[1] + 6 + tt % 24), 6.5) + drop_svg((e2[0] + 4, e2[1] + 6 + (tt + 12) % 24), 6.5)
            if 4 <= st <= 5:
                top = F(g, 256, 150)
                s += gloom_svg((top[0], top[1] - 70), 1.0 + 0.1 * (i % 2))
            if st == 6 and i == 11:
                s += motion_lines((BA.CX - 120, 476), 200, spread=18, r0=0, length=16, n=2, w=4.6) + \
                    motion_lines((BA.CX + 120, 476), -20, spread=18, r0=0, length=16, n=2, w=4.6)
            if st == 7:
                s += arcs(F(g, 60, 300), 180, r=22, n=2, w=4.2) + arcs(F(g, 450, 300), 0, r=22, n=2, w=4.2)
            if st == 8:
                s += sparkle(F(g, 70, 190), 13) + sparkle(F(g, 450, 170), 11)
            return s
        c.add(lab, gk, face, m, fx=fxc, ear=ear, contact=i != 11)
    clips.append(c)

    # ---------------------------------------------------------------- invite_nod
    c = Clip("invite_nod", "跟觀眾點頭邀請（湊近鏡頭、點頭兩下、眨單眼＋愛心、小蹦一下）", "「一起玩」「一起來看」邀請段落、片尾呼籲", "主持")
    seq = [("待機", dict(), dict(eyes="dot", mouth="w"), 0, (0, 0)),
           ("看鏡頭（預備：縮）", dict(h=0.96, w=1.02, lag=-0.02), dict(eyes="shine", mouth="w"), 0, (0, 0)),
           ("湊近鏡頭（放大）", dict(h=1.07, w=1.06, lag=0.04, bottom=6), dict(eyes="shine", mouth="open_m"), 1, (-6, -6)),
           ("「一起」", dict(h=1.08, w=1.06, lag=0.05, bottom=6), dict(eyes="shine", mouth="open_l", blush="soft"), 1, (-6, -6)),
           ("點頭（下）", dict(h=1.0, w=1.09, lag=-0.08, bottom=6), dict(eyes="happy", mouth="open_s", blush="soft"), 2, (0, 0)),
           ("點頭（最低）", dict(h=0.98, w=1.1, lag=-0.11, bottom=6), dict(eyes="happy", mouth="w", blush="soft"), 2, (0, 0)),
           ("回來", dict(h=1.07, w=1.06, lag=0.04, bottom=6), dict(eyes="shine", mouth="open_s", blush="soft"), 2, (0, 0)),
           ("點頭（下）", dict(h=1.0, w=1.09, lag=-0.08, bottom=6), dict(eyes="happy", mouth="open_s", blush="soft"), 2, (0, 0)),
           ("點頭（最低）", dict(h=0.98, w=1.1, lag=-0.11, bottom=6), dict(eyes="happy", mouth="w", blush="soft"), 2, (0, 0)),
           ("回來「來玩！」", dict(h=1.08, w=1.06, lag=0.05, bottom=6), dict(eyes="shine", mouth="open_m", blush="soft"), 3, (-4, -4)),
           ("眨單眼（半）", dict(h=1.07, w=1.06, lag=0.04, bottom=6, rot=-2), dict(eyes=("dot", "half"), mouth="open_s", blush="soft"), 3, (0, 0)),
           ("眨單眼＋愛心", dict(h=1.07, w=1.06, lag=0.04, bottom=6, rot=-3), dict(eyes=("dot", "happy"), mouth="tongue", blush="lines"), 4, (0, 6)),
           ("退回（壓）", dict(h=0.92, w=1.05, lag=-0.02), dict(eyes="happy", mouth="w", blush="soft"), 4, (0, 0)),
           ("小蹦", dict(h=1.06, w=0.97, bottom=-16), dict(eyes="shine", mouth="open_m", blush="soft"), 5, (-8, -8)),
           ("落地", dict(h=0.94, w=1.035), dict(eyes="happy", mouth="open_s"), 5, (0, 0)),
           ("回穩", dict(h=1.01), dict(eyes="dot", mouth="w"), 0, (0, 0)),
           ("眨眼（半閉）", dict(h=1.0), dict(eyes="half", mouth="w"), 0, (0, 0)),
           ("眨眼（閉）", dict(h=1.0), dict(eyes="blink", mouth="w"), 0, (0, 0)),
           ("眨眼（半閉）", dict(h=1.0), dict(eyes="half", mouth="w"), 0, (0, 0)),
           ("回待機", dict(h=0.997), dict(eyes="dot", mouth="w"), 0, (0, 0))]
    ms = [120, 90, 90, 120, 70, 90, 70, 70, 90, 120, 60, 160, 80, 70, 80, 90, 50, 60, 50, 130]
    for i, ((lab, gk, face, st, ear), m) in enumerate(zip(seq, ms)):
        def fxi(g, st=st, i=i):
            s = ""
            if st == 1:
                s += sound(poses, g, i, 3)
            if st == 2 and i in (4, 5, 7, 8):
                s += arcs(F(g, 256, 118), 90, r=18, n=2, w=4.2)
            if st == 3:
                s += note_svg(F(g, 460, 170), 1.0) + sound(poses, g, i, 2)
            if st == 4:
                hc = F(g, 420, 190)
                s += heart_svg((hc[0] + 24, hc[1] - 20 - 10 * (i - 11)), 16, deg=12, lw=3.4)
            if st == 5:
                s += sparkle(F(g, 70, 190), 12) + sparkle(F(g, 450, 180), 12)
                if i == 13:
                    s += motion_lines((BA.CX - 110, 480), 200, spread=18, r0=0, length=14, n=2, w=4.4) + \
                        motion_lines((BA.CX + 110, 480), -20, spread=18, r0=0, length=14, n=2, w=4.4)
            return s
        c.add(lab, gk, face, m, fx=fxi, ear=ear, contact=i != 13)
    clips.append(c)
    return clips


def CXg(g):
    return g["cx"]


_FONT_CACHE = {}


def _txt(t, c, deg, px):
    """「嗯」字用 SVG text（中文字型由 text_layer 畫比較穩，這裡改回傳標記，render 時處理）。"""
    return f"<!--TXT|{t}|{c[0]:.1f}|{c[1]:.1f}|{deg}|{px}-->"


# ================================================================== 輸出與檢查
def draw_frame(poses, clip, i, ears):
    fr = clip.fr[i]
    g = base_geom(poses, 0, **fr["gk"])
    pose = face_pose(poses, **fr["face"])
    pose = ear_warp(pose, *ears[i])
    front = fr["fx"](g) if fr["fx"] else ""
    texts = []
    while "<!--TXT|" in front:
        a = front.index("<!--TXT|"); b = front.index("-->", a)
        _, t, x, y, deg, px = front[a:b].split("|")
        texts.append((t, (float(x), float(y)), float(deg), float(px)))
        front = front[:a] + front[b + 3:]
    return render_sh(poses, {"g": g, "pose": pose, "front": front, "texts": texts, "burst": fr["burst"]})


def render_sh(poses, fr):
    """同 bibi_faces_c.render，但身體可以剪切（g["sh"]）：腳底那條線不動，四腳一直著地。"""
    g = fr["g"]
    body = pose_tween.warp_body(fr["pose"], g, SIZE).convert("RGBA")
    k = g.get("sh", 0.0)
    if abs(k) > 1e-4:
        GS = BA.GROUND * pose_tween.SS
        body = body.transform(body.size, Image.AFFINE, (1, k, -k * GS, 0, 1, 0), Image.BICUBIC)
    canvas = Image.new("RGBA", body.size, (0, 0, 0, 0))
    if fr.get("burst"):
        canvas = Image.alpha_composite(canvas, BA.raster(C.burst_svg(body, g, poses, fr["burst"])))
    canvas = Image.alpha_composite(canvas, body)
    if fr.get("front"):
        canvas = Image.alpha_composite(canvas, BA.raster(fr["front"]))
    for t in fr.get("texts", []):
        txt, c, deg, px = t[:4]
        canvas = Image.alpha_composite(canvas, BA.text_layer(txt, c, deg, px, BA.HUNINN))
    return canvas.resize((SIZE, SIZE), Image.LANCZOS)


def checker(w, h, s=16):
    v = np.where(((np.indices((h, w))[0] // s) + (np.indices((h, w))[1] // s)) % 2, 205, 245).astype(np.uint8)
    return Image.fromarray(np.dstack([v, v, v, np.full_like(v, 255)]), "RGBA")


def bg3(imgs, labels, path, cell=180):
    n = len(imgs)
    lab = 20
    W, H = n * cell, 3 * (cell + lab) + 30
    out = Image.new("RGB", (W, H), (60, 60, 66))
    d = ImageDraw.Draw(out)
    ft = ImageFont.truetype(FONT, 12)
    bgs = [Image.new("RGBA", (cell, cell), (255, 255, 255, 255)), Image.new("RGBA", (cell, cell), (0, 0, 0, 255)), checker(cell, cell, 10)]
    for r, bg in enumerate(bgs):
        for j, im in enumerate(imgs):
            t = bg.copy(); t.alpha_composite(im.resize((cell, cell), Image.LANCZOS))
            y = 30 + r * (cell + lab)
            out.paste(t.convert("RGB"), (j * cell, y + lab))
            if r == 0:
                d.text((j * cell + 3, y + 3), f"{j+1:02d} {labels[j][:12]}", fill=(240, 240, 240), font=ft)
    d.text((6, 6), f"{path.stem}　白／黑／棋盤格三底逐格", fill=(255, 220, 120), font=ImageFont.truetype(FONT, 16))
    out.save(path)


def auto_check(imgs, contacts):
    """自動檢查：腳底 y（接觸格要 ≥ 478）、身體內破洞、白邊（半透明邊緣像素裡偏白的比例）。"""
    rep = []
    for im, ct in zip(imgs, contacts):
        a = np.asarray(im)
        al = a[..., 3]
        solid = al > 128
        ys = np.nonzero(solid.any(1))[0]
        lab, n = ndimage.label(solid)
        sizes = ndimage.sum(solid, lab, range(1, n + 1)) if n else []
        big = (lab == (int(np.argmax(sizes)) + 1)) if n else solid
        filled = ndimage.binary_fill_holes(big)
        holes = int((filled & ~big).sum())
        # 只看身體下緣（腳）：最大連通塊的最低點
        foot = int(np.nonzero(big.any(1))[0].max()) if big.any() else -1
        xs = np.nonzero(big.any(0))[0]
        mid = int((xs.min() + xs.max()) / 2) if len(xs) else 256
        fl = int(np.nonzero(big[:, :mid].any(1))[0].max()) if big[:, :mid].any() else -1
        fr_ = int(np.nonzero(big[:, mid:].any(1))[0].max()) if big[:, mid:].any() else -1
        edge = (al > 20) & (al < 230)
        rgb = a[..., :3].astype(int)
        white = edge & (rgb.min(2) > 225)
        rep.append(dict(foot_y=foot, foot_l_y=fl, foot_r_y=fr_, top_y=int(ys.min()) if len(ys) else -1, holes_px=holes,
                        edge_px=int(edge.sum()), white_edge_px=int(white.sum()), contact=ct))
    return rep


# 代表格指定（自動挑「跟第 1 格差最多」會挑到空中倒轉那格，總目錄上看不出是哪個表情）
KEY_FRAME = {"happy_spin": 12}


def quant(im):
    return im.quantize(colors=256, method=Image.FASTOCTREE, dither=Image.NONE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(REPO / "site/brand/src/support_anim_1009.gif"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    out = Path(a.out)
    poses = pose_tween.load_poses(Path(a.src))
    only = [x for x in a.only.split(",") if x]
    tpath = out / "timing.json"
    timing = json.loads(tpath.read_text(encoding="utf-8")) if tpath.exists() else {}
    sys.path.insert(0, str(Path(__file__).parent))
    from bibi_library import key_index
    for clip in build(poses):
        if only and clip.key not in only:
            continue
        gks = [fr["gk"] for fr in clip.fr]
        durs = [fr["ms"] for fr in clip.fr]
        ears = ear_spring(poses, gks, [fr["ear"] for fr in clip.fr], durs)
        imgs = [draw_frame(poses, clip, i, ears) for i in range(len(clip.fr))]
        fd = out / "frames" / clip.key
        fd.mkdir(parents=True, exist_ok=True)
        for old in fd.glob("frame_*.png"):
            old.unlink()
        for j, im in enumerate(imgs):
            im.save(fd / f"frame_{j+1:02d}.png")
        d = LIB / clip.key
        d.mkdir(parents=True, exist_ok=True)
        ki = KEY_FRAME[clip.key] - 1 if clip.key in KEY_FRAME else key_index(imgs)
        quant(imgs[ki]).save(d / "key.png", optimize=True)
        sheet = Image.new("RGBA", (256 * len(imgs), 256), (0, 0, 0, 0))
        for j, im in enumerate(imgs):
            sheet.alpha_composite(im.resize((256, 256), Image.LANCZOS), (256 * j, 0))
        quant(sheet).save(d / "sheet.png", optimize=True)
        imgs[0].save(d / "anim.webp", save_all=True, append_images=imgs[1:], duration=durs, loop=0, quality=88, method=6)
        (out / "check").mkdir(parents=True, exist_ok=True)
        labels = [fr["lab"] for fr in clip.fr]
        bg3(imgs, labels, out / "check" / f"{clip.key}_bg3.png")
        rep = auto_check(imgs, [fr["contact"] for fr in clip.fr])
        arr = [np.asarray(i).astype(int) for i in imgs]
        n = len(arr)
        diffs = [int(np.abs(arr[k] - arr[(k + 1) % n]).sum() // 1000) for k in range(n)]
        timing[clip.key] = {"name": clip.name, "use": clip.use, "cat": clip.cat, "frames": n, "ms": sum(durs),
                            "durations_ms": durs, "labels": labels, "key_frame": ki + 1,
                            "ears_deg": [[round(x, 1), round(y, 1)] for x, y in ears],
                            "check": rep, "adjacent_diff_k": diffs}
        bad_foot = [j + 1 for j, r in enumerate(rep) if r["contact"] and min(r["foot_l_y"], r["foot_r_y"]) < 476]
        holes = [j + 1 for j, r in enumerate(rep) if r["holes_px"] > 0]
        wmax = max(r["white_edge_px"] for r in rep)
        print(f"{clip.key}: {n} 格 {sum(durs)/1000:.2f} 秒 代表格 {ki+1} 接觸格有腳離地(<476) {bad_foot} 破洞格 {holes} "
              f"白邊像素最多 {wmax} 最小相鄰差 {min(diffs)}", flush=True)
    # 平行跑多支時，寫回前重讀一次再合併，避免互相蓋掉
    mine = {k: v for k, v in timing.items() if not only or k in only}
    timing = json.loads(tpath.read_text(encoding="utf-8")) if tpath.exists() else {}
    timing.update(mine)
    tpath.write_text(json.dumps(timing, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
