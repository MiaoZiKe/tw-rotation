"""動畫設計單位：吉祥物「比比」G2 批——客服鈕互動與情境待機（Andy 2026-10-11，「更像真的在陪伴你」）。

互動（播一次）：highfive 擊掌、dance 跳舞、hug 抱抱、wake_once 被叫醒驚跳、selfie 比 YA 拍照
循環：sleep_loop 打瞌睡
情境待機（循環）：idle_down 大盤下跌安慰、idle_bigup 大漲輕量慶祝、festival_newyear／dragon／moon／xmas、weekend 週末放鬆

規格：每組 12 格、512×512 透明；比比本體＝原圖 support_anim_1009.gif 像素網格變形（跟 bibi_actions 同一套座標：
身體 0.75 倍、中心 x=248、腳底 y=482）；四肢只有官方部件總表（reference/parts_sheet_1011.webp）的小肉掌，
手只在身側／身前貼身出現，不畫手臂；效果符號與道具優先用 docs/anim/bibi_library/parts/ 切好的透明部件。
表情＝用周圍毛色蓋掉原眼睛／嘴，再用 Bézier 重畫（face2）。只 import 既有腳本，不改它們。

用法
----
    python scripts/anim/bibi_interact_g2.py --out <scratchpad>/bibi_g [--repo-out docs/anim] [--only highfive,dance]
輸出：<out>/<名>/frames/frame_01.png…、<repo-out>/bibi_<名>/{sheet_12.png,anim.webp(160px)，storyboard.md 另寫}、<out>/<名>/overlap.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
import bibi_actions as BA  # noqa: E402
import pose_tween  # noqa: E402
from bibi_actions import (INK, FUR, FUR_SH, SIZE, SS, CX, GROUND, SCALE, OUT_W, EYE_L, EYE_R,  # noqa: E402
                          f, P, add, rot2, dirv, bez, brush, sparkle, base_geom, fwd, compose, sheet12,
                          GOLD, GOLD_DK, GOLD_LT, BLUE, PINK, MINT, RED, CYAN, BLUSH)

PARTS = Path("docs/anim/bibi_library/parts")
PAWC, PAWD = "#FFB4A0", "#F58C78"        # 官方總表手掌配色
LW = OUT_W * 0.85
MOUTH0 = (250, 291)                       # 原圖第 0 張嘴的中心
CHEEK_L, CHEEK_R = (150, 287), (345, 285)  # 腮紅中心（原圖座標）


# ================================================================== 部件與圖層小工具
_PART = {}


def part_img(name):
    if name not in _PART:
        _PART[name] = Image.open(PARTS / f"{name}.png").convert("RGBA")
    return _PART[name]


def part(name, c, h, deg=0.0, op=1.0, flip=False):
    """把部件放到場景座標 c（中心），高度 h（場景 px），順時針轉 deg；回傳 2048 圖層。"""
    im = part_img(name)
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    k = h * SS / im.height
    big = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
    if deg:
        big = big.rotate(-deg, resample=Image.BICUBIC, expand=True)
    if op < 0.999:
        a = big.getchannel("A").point(lambda v: int(v * max(op, 0)))
        big.putalpha(a)
    lay = Image.new("RGBA", (SIZE * SS, SIZE * SS), (0, 0, 0, 0))
    lay.alpha_composite(big, (int(c[0] * SS - big.width / 2), int(c[1] * SS - big.height / 2)))
    return lay


def svg_layer(svg):
    return BA.raster(svg)


def hand(poses, g, side, deg, k=1.0, src_pt=None, depth=10):
    """小肉掌：side R／L；deg＝畫面角度（0 右、90 上），從身側肩點冒出；回傳 2048 圖層。"""
    sp = src_pt or ((432, 322) if side == "R" else (70, 322))
    at = BA.shoulder(poses, g, sp, depth=depth)
    return BA.hand_layer(at, deg, 54 * k, side), at


def hand_at(at, deg, k=1.0, side="R"):
    return BA.hand_layer(at, deg, 54 * k, side)


def peace_paw(c, k=1.0, deg=0.0, spread=16.0):
    """比 YA 的短肉掌：蜜桃粉小圓掌＋兩根短短圓圓的指頭（V 形）。c＝掌心，deg＝順時針轉。"""
    def T(p):
        return add(c, rot2((p[0] * k, p[1] * k), deg))
    out = ""
    for sgn in (-1, 1):
        base = T((sgn * 7.5, -9))
        tip = T((sgn * 7.5 + sgn * math.sin(math.radians(spread)) * 20, -9 - math.cos(math.radians(spread)) * 20))
        out += (f'<path d="M {P(base)} L {P(tip)}" stroke="{INK}" stroke-width="{f((15 + 5.2) * k)}" stroke-linecap="round"/>'
                f'<path d="M {P(base)} L {P(tip)}" stroke="{PAWC}" stroke-width="{f(15 * k)}" stroke-linecap="round"/>')
    pts = [T((math.cos(a) * 20, math.sin(a) * 18 + 4)) for a in np.linspace(0, 2 * math.pi, 18, endpoint=False)]
    d = "M " + " L ".join(P(p) for p in pts) + " Z"
    out += (f'<path d="{d}" fill="{PAWC}" stroke="{INK}" stroke-width="{f(5.2 * k)}" stroke-linejoin="round"/>'
            f'<path d="M {P(T((-6,-2)))} Q {P(T((0,3)))} {P(T((6,-2)))}" stroke="{PAWD}" stroke-width="{f(3.2*k)}" fill="none" stroke-linecap="round"/>')
    # 兩指縫之間補一小塊底色，掌與指接得乾淨
    out += f'<ellipse cx="{f(T((0,-6))[0])}" cy="{f(T((0,-6))[1])}" rx="{f(10*k)}" ry="{f(9*k)}" fill="{PAWC}"/>'
    return out


# ================================================================== 表情（改原圖的眼睛、嘴、腮紅）
_FACE = {}


def _ring_col(arr, c, r0, r1):
    yy, xx = np.mgrid[0:arr.shape[0], 0:arr.shape[1]]
    d2 = (xx - c[0]) ** 2 + (yy - c[1]) ** 2
    ring = (d2 >= r0 ** 2) & (d2 <= r1 ** 2) & (arr[..., :3].mean(2) > 232) & (arr[..., 3] > 200)
    if ring.sum() < 20:
        ring = (d2 >= r0 ** 2) & (d2 <= r1 ** 2) & (arr[..., :3].mean(2) > 210) & (arr[..., 3] > 200)
    return "#%02X%02X%02X" % tuple(int(v) for v in np.median(arr[ring][:, :3], 0))


def _eye_svg(mode, c, scale=1.0, hl=False):
    if mode == "dot":
        s = f'<ellipse cx="{f(c[0])}" cy="{f(c[1])}" rx="{f(13.5*scale)}" ry="{f(15*scale)}" fill="{INK}"/>'
        if hl:
            s += f'<circle cx="{f(c[0]+4.5*scale)}" cy="{f(c[1]-5.5*scale)}" r="{f(4.4*scale)}" fill="#FFFFFF"/>'
        return s
    if mode == "happy":     # ^
        return brush(bez((c[0] - 13, c[1] + 6), (c[0] - 6, c[1] - 10), (c[0] + 6, c[1] - 10), (c[0] + 13, c[1] + 6), 14), 7.5, 7.5)
    if mode == "relax":     # ‿ 閉眼
        return brush(bez((c[0] - 13, c[1] - 2), (c[0] - 6, c[1] + 9), (c[0] + 6, c[1] + 9), (c[0] + 13, c[1] - 2), 14), 7.0, 7.0)
    if mode == "flat":      # — 睡著的眼線
        return brush(bez((c[0] - 13, c[1] + 1), (c[0] - 5, c[1] + 4), (c[0] + 5, c[1] + 4), (c[0] + 13, c[1] + 1), 14), 6.5, 6.5)
    return ""


def _mouth_svg(mode, m=MOUTH0):
    x, y = m
    if mode == "smile":
        return brush(bez((x - 14, y - 4), (x - 7, y + 9), (x + 7, y + 9), (x + 14, y - 4), 14), 7, 7)
    if mode == "omega":
        return (brush(bez((x - 15, y - 3), (x - 12, y + 10), (x - 3, y + 10), (x, y), 12), 6.5, 6.5) +
                brush(bez((x, y), (x + 3, y + 10), (x + 12, y + 10), (x + 15, y - 3), 12), 6.5, 6.5))
    if mode == "o":
        return (f'<ellipse cx="{f(x)}" cy="{f(y+6)}" rx="10" ry="12.5" fill="#E8705A" stroke="{INK}" stroke-width="6"/>')
    if mode == "tiny":
        return (f'<ellipse cx="{f(x)}" cy="{f(y+3)}" rx="6.5" ry="6" fill="#E8705A" stroke="{INK}" stroke-width="5"/>')
    if mode == "grin":
        d = (f"M {P((x-19,y-4))} Q {P((x,y+3))} {P((x+19,y-4))} Q {P((x+16,y+24))} {P((x,y+24))} Q {P((x-16,y+24))} {P((x-19,y-4))} Z")
        return (f'<path d="{d}" fill="#EE7B66" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>'
                f'<ellipse cx="{f(x)}" cy="{f(y+16)}" rx="8" ry="5" fill="#FF9C8A"/>')
    return ""


def _blush_svg(strength):
    """腮紅加深＋三道白斜線（官方總表『害羞』腮紅）。"""
    out = ""
    for c in (CHEEK_L, CHEEK_R):
        out += f'<ellipse cx="{f(c[0])}" cy="{f(c[1])}" rx="31" ry="27" fill="#F58C78" opacity="{0.55*strength:.2f}"/>'
        for j in (-1, 0, 1):
            a = (c[0] + j * 11 - 4, c[1] + 10)
            b = (c[0] + j * 11 + 5, c[1] - 10)
            out += f'<path d="M {P(a)} L {P(b)}" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" opacity="{min(1,strength):.2f}"/>'
    return out


def face2(poses, eyes=("dot", "dot"), mouth="keep", scale=1.0, hl=False, look=(0, 0), blush=0.0, eye_scale=None):
    key = (eyes, mouth, scale, hl, round(look[0], 1), round(look[1], 1), round(blush, 2))
    if key in _FACE:
        return _FACE[key]
    base = poses[0]
    if eyes == ("dot", "dot") and mouth == "keep" and scale == 1.0 and not hl and look == (0, 0) and blush == 0:
        _FACE[key] = base
        return base
    arr = np.asarray(base["body"]).astype(float)
    svg = ('<defs><radialGradient id="cv"><stop offset="0" stop-color="#fff" stop-opacity="1"/><stop offset="0.72" stop-color="#fff" stop-opacity="1"/>'
           '<stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient></defs>')

    def cover(c, rx, ry, col):
        # 羽化的毛色蓋章：中心不透明、邊緣漸隱，不留圓形痕跡
        g_ = col
        return (f'<defs><radialGradient id="g{abs(hash((c, rx)))}"><stop offset="0" stop-color="{g_}" stop-opacity="1"/>'
                f'<stop offset="0.7" stop-color="{g_}" stop-opacity="1"/><stop offset="1" stop-color="{g_}" stop-opacity="0"/></radialGradient></defs>'
                f'<ellipse cx="{f(c[0])}" cy="{f(c[1])}" rx="{rx}" ry="{ry}" fill="url(#g{abs(hash((c, rx)))})"/>')
    svg = ""
    for e in (EYE_L, EYE_R):
        svg += cover(e, 22, 22, _ring_col(arr, e, 20, 28))
    if mouth != "keep":
        svg += cover((MOUTH0[0], MOUTH0[1] - 1), 56, 40, _ring_col(arr, (MOUTH0[0], MOUTH0[1] - 1), 46, 56))
    if blush:
        svg += _blush_svg(blush)
    for e, mode in zip((EYE_L, EYE_R), eyes):
        svg += _eye_svg(mode, (e[0] + look[0], e[1] + look[1]), scale, hl)
    if mouth != "keep":
        svg += _mouth_svg(mouth)
    ov = BA.raster(svg).resize((SIZE, SIZE), Image.LANCZOS)
    body = base["body"].copy()
    a = body.getchannel("A")
    body = Image.alpha_composite(body, ov)
    body.putalpha(a)
    out = dict(base); out["body"] = body
    _FACE[key] = out
    return out


# ================================================================== 毛炸（驚嚇時外緣長出一圈短尖毛）
def spike_back(poses, g, pose, amp, seed=0):
    body = pose_tween.warp_body(pose, g, SIZE).convert("RGBA")
    al = np.asarray(body.getchannel("A").resize((SIZE, SIZE), Image.BILINEAR)) > 128
    ys, xs = np.nonzero(al)
    c = (xs.mean(), ys.mean())
    rng = np.random.default_rng(seed)
    N = 40
    pts = []
    for k in range(N):
        th = 2 * math.pi * k / N
        r = 0
        for rr in range(40, 330):
            x, y = int(c[0] + math.cos(th) * rr), int(c[1] + math.sin(th) * rr)
            if 0 <= x < SIZE and 0 <= y < SIZE and al[y, x]:
                r = rr
        r -= 3
        th2 = th + math.pi / N
        pts.append((c[0] + math.cos(th) * (r - 2), c[1] + math.sin(th) * (r - 2)))
        r2 = r + amp * rng.uniform(0.7, 1.15)
        pts.append((c[0] + math.cos(th2) * r2, c[1] + math.sin(th2) * r2))
    d = "M " + " L ".join(P(p) for p in pts) + " Z"
    return f'<path d="{d}" fill="{FUR}" stroke="{INK}" stroke-width="{f(OUT_W)}" stroke-linejoin="round"/>'


# ================================================================== 幀規格與輸出
def fr(poses, g, label, face=None, fx=None, sprites=None, front="", back="", hands=None, flash=0.0):
    """fx：[(名稱, 圖層)] 效果符號（不得跟身體或彼此重疊，輸出時檢查）；
    sprites：貼身的帽子、道具等圖層（不檢查）；hands：貼身小肉掌（允許碰身體，但不得碰 fx）。"""
    return {"g": g, "label": label, "pose": face or poses[0], "fx": fx or [], "sprites": sprites or [],
            "front": front, "back": back, "flash": flash, "hands": hands or []}


def render(poses, d):
    fr_ = dict(d)
    fr_["sprites"] = list(d["sprites"]) + [lay for _, lay in d["hands"]] + [lay for _, lay in d["fx"]]
    return fr_


def render_frame(poses, d):
    img = compose(poses, render(poses, d))
    if d.get("flash"):
        a = img.getchannel("A")
        rgb = np.asarray(img.convert("RGB")).astype(float)
        lum = rgb.mean(2, keepdims=True)
        k = d["flash"] * np.clip((lum - 110) / 90, 0, 1)      # 只提亮毛色，黑描邊維持深色
        rgb = rgb + (255 - rgb) * k
        out = Image.fromarray(rgb.astype(np.uint8), "RGB").convert("RGBA")
        out.putalpha(a)
        img = out
    return img


def body_alpha(poses, d):
    b = pose_tween.warp_body(d["pose"], d["g"], SIZE).convert("RGBA")
    return np.asarray(b.getchannel("A").resize((SIZE, SIZE), Image.BILINEAR)) > 40


def overlap_check(poses, d):
    """效果符號（fx）跟身體、跟彼此的重疊像素數（越小越好；0＝完全不碰）。"""
    ba = body_alpha(poses, d)
    ms = []
    for nm, lay in d["fx"]:
        ms.append((nm, np.asarray(lay.getchannel("A").resize((SIZE, SIZE), Image.BILINEAR)) > 40))
    hits = []
    for nm, lay in d["hands"]:
        hm = np.asarray(lay.getchannel("A").resize((SIZE, SIZE), Image.BILINEAR)) > 40
        for nm2, m in ms:
            n = int((m & hm).sum())
            if n:
                hits.append((nm2, nm, n))
    for nm, m in ms:
        n = int((m & ba).sum())
        if n:
            hits.append((nm, "身體", n))
    for i in range(len(ms)):
        for j in range(i + 1, len(ms)):
            n = int((ms[i][1] & ms[j][1]).sum())
            if n:
                hits.append((ms[i][0], ms[j][0], n))
    return hits


def fade(u):
    """0→1→0 的淡入淡出（循環接縫處為 0）。"""
    return max(0.0, math.sin(math.pi * u)) ** 0.6


# ================================================================== 場景一：5 擊掌（播一次）
def lerp(a, b, t):
    return a + (b - a) * t


def scene_highfive(poses):
    PAD_C = (410, 298)
    plan = [
        # 標籤, 幾何, 手(deg,k)／"pad", 眼, 嘴, 火花
        ("待機", {}, None, ("dot", "dot"), "keep", 0),
        ("微蹲蓄力、肉掌從身側冒出", dict(h=0.97, w=1.02, rot=-1), (15, 0.6), ("dot", "dot"), "keep", 0),
        ("小肉掌舉起", dict(rot=-1.5, h=1.01, lag=-0.03), (50, 0.95), ("dot", "dot"), "keep", 0),
        ("舉高", dict(rot=-2.5, h=1.02, lag=-0.04), (78, 1.0), ("dot", "dot"), "keep", 0),
        ("往後蓄力", dict(rot=-5, cx=-5, h=1.02, lag=-0.05), (90, 0.92), ("dot", "dot"), "keep", 0),
        ("拍！（肉球面朝前）", dict(rot=4, cx=6, h=1.02, lag=-0.03), "pad", ("happy", "happy"), "grin", 1),
        ("停留、星星火花", dict(rot=4.5, cx=7, h=1.015), "pad", ("happy", "happy"), "grin", 2),
        ("火花散開", dict(rot=3, cx=4, h=1.0), "pad2", ("happy", "happy"), "grin", 3),
        ("手往下放", dict(rot=1, h=1.0), (62, 0.95), ("dot", "dot"), "keep", 0),
        ("手再往下", dict(rot=0, h=0.99), (28, 0.8), ("dot", "dot"), "keep", 0),
        ("縮回身側", dict(h=0.985, w=1.01), (0, 0.6), ("dot", "dot"), "keep", 0),
        ("回待機（微彈）", dict(h=0.992, w=1.008), None, ("dot", "dot"), "keep", 0),
    ]
    out = []
    for i, (lab, gk, hd, eyes, mouth, spark) in enumerate(plan):
        g = base_geom(poses, 0, **gk)
        face = face2(poses, eyes, mouth, hl=(eyes == ("dot", "dot") and hd is not None))
        hands, fx = [], []
        if isinstance(hd, tuple):
            lay, at = hand(poses, g, "R", hd[0], hd[1])
            hands.append(("hand", lay))
        elif hd in ("pad", "pad2"):
            c = PAD_C if hd == "pad" else (PAD_C[0] - 2, PAD_C[1] + 14)
            hands.append(("pad", part("hand_pad", add(c, (g["cx"] - CX, 0)), 72, deg=-8)))
            # 小肉掌根部：身側一小截，讓掌不是飄著的
            lay, _ = hand(poses, g, "R", 40, 0.55)
            hands.append(("root", lay))
        if spark:
            pc = add(PAD_C, (g["cx"] - CX, 0))
            if spark == 1:
                fx.append(("spark1", part("fx_sparkle", add(pc, (46, -64)), 52)))
                fx.append(("spark2", part("fx_sparkle", add(pc, (-26, -78)), 34, deg=-12)))
            elif spark == 2:
                fx.append(("spark1", part("fx_sparkle", add(pc, (50, -70)), 62)))
                fx.append(("spark2", part("fx_sparkle", add(pc, (-28, -80)), 40, deg=-12)))
                fx.append(("spark3", part("fx_sparkle", add(pc, (66, 6)), 34, deg=10)))
            else:
                fx.append(("spark1", part("fx_sparkle", add(pc, (56, -80)), 40, op=0.8)))
                fx.append(("spark3", part("fx_sparkle", add(pc, (72, 2)), 26, deg=10, op=0.7)))
        out.append(fr(poses, g, lab, face, fx=fx, hands=hands))
    return out


# ================================================================== 場景二：6 跳舞（播一次，兩個來回）
def scene_dance(poses):
    out = []
    for t in range(12):
        ang = 2 * math.pi * 2 * t / 11
        env = math.sin(math.pi * t / 11)             # 兩端 0：開頭結尾回待機
        s = math.sin(ang) * env
        g = base_geom(poses, 0, rot=7.5 * s, cx=9 * s, bottom=-9 * math.cos(ang) ** 2 * env,
                      h=1 + 0.025 * math.cos(2 * ang) * env, w=1 - 0.015 * math.cos(2 * ang) * env, lag=-0.03 * env)
        eyes = ("happy", "happy") if (t % 2 == 1 and 0 < t < 11) else ("dot", "dot")
        face = face2(poses, eyes, "grin" if (t in (3, 4, 7, 8)) else "keep", hl=(eyes[0] == "dot" and 0 < t < 11))
        hands, fx = [], []
        if env > 0.25:
            lay, _ = hand(poses, g, "R", 42 + 34 * s, 0.6 + 0.4 * env)
            hands.append(("handR", lay))
            lay, _ = hand(poses, g, "L", 138 + 34 * s, 0.6 + 0.4 * env)
            hands.append(("handL", lay))
        uA = (t - 0.5) / 10.5
        uB = (t - 3.5) / 7.5
        if 0 < uA < 1:
            fx.append(("noteA", part("fx_music", (lerp(372, 412, uA), lerp(205, 92, uA)), 54, deg=lerp(-8, 10, uA), op=fade(uA))))
        if 0 < uB < 1:
            fx.append(("noteB", part("fx_music", (lerp(138, 98, uB), lerp(200, 100, uB)), 48, deg=lerp(8, -10, uB), op=fade(uB), flip=True)))
        out.append(fr(poses, g, f"第 {t+1} 拍", face, fx=[x for x in fx if x[1].getbbox()], hands=hands))
    labs = ["待機、起拍", "左右扭（右）", "扭到右", "彈起（左掌舉）", "往左", "扭到左", "彈起（右掌舉）", "往右", "扭到右", "往中間", "放手", "回待機"]
    for d, l in zip(out, labs):
        d["label"] = l
    return out


# ================================================================== 場景三：7 抱抱（播一次）
def scene_hug(poses):
    # 手：side 接點(畫面) → 抱在肚子前的接點；s＝0 在身側、1 抱住
    HUG = {"R": ((318, 372), 172, 58), "L": ((178, 380), 8, 58)}
    plan = [
        ("待機", {}, None, ("dot", "dot"), "keep", 0, 0),
        ("身體前傾、肉掌從身側冒出", dict(h=0.98, w=1.015, rot=1), 0.0, ("dot", "dot"), "keep", 0.0, 0),
        ("兩邊肉掌張開", dict(h=1.0, w=1.01, rot=0), 0.15, ("dot", "dot"), "keep", 0.3, 0),
        ("肉掌往身前收", dict(h=1.0, w=1.0, rot=-1), 0.5, ("dot", "dot"), "smile", 0.5, 0),
        ("快抱住", dict(h=1.015, w=0.985, rot=-1.5), 0.85, ("relax", "relax"), "smile", 0.8, 0),
        ("抱住自己（臉紅）", dict(h=1.035, w=0.965, rot=-2), 1.0, ("happy", "happy"), "smile", 1.0, 1),
        ("抱緊、愛心冒出", dict(h=1.04, w=0.96, rot=0.5), 1.0, ("happy", "happy"), "smile", 1.0, 2),
        ("輕輕搖（右）", dict(h=1.035, w=0.965, rot=2.5), 1.0, ("happy", "happy"), "smile", 1.0, 3),
        ("輕輕搖（左）", dict(h=1.035, w=0.965, rot=-2.5), 1.0, ("relax", "relax"), "smile", 1.0, 4),
        ("鬆開一點", dict(h=1.01, w=0.99, rot=-1), 0.55, ("happy", "happy"), "smile", 0.7, 5),
        ("肉掌放回身側", dict(h=0.99, w=1.005), 0.0, ("dot", "dot"), "keep", 0.3, 0),
        ("回待機", dict(h=0.992, w=1.008), None, ("dot", "dot"), "keep", 0, 0),
    ]
    hearts = [  # (起點, 終點, 高, 零件, 起始格, 長度)
        ((326, 190), (368, 122), 46, "fx_heart", 5, 5),
        ((176, 190), (144, 118), 60, "fx_hearts_small", 6, 5),
        ((252, 160), (262, 88), 34, "fx_heart", 7, 4),
    ]
    out = []
    for i, (lab, gk, s, eyes, mouth, bl, hh) in enumerate(plan):
        g = base_geom(poses, 0, **gk)
        face = face2(poses, eyes, mouth, hl=(eyes[0] == "dot" and s is not None), blush=bl)
        hands, fx = [], []
        if s is not None:
            for side in ("R", "L"):
                (hx, hy), hdeg, hlen = HUG[side]
                sgn = 1 if side == "R" else -1
                sx, sy = BA.shoulder(poses, g, (432, 322) if side == "R" else (70, 322), depth=10)
                if s < 0.2:
                    k = lerp(0.6, 0.95, s / 0.2)
                    sd = (-25 if side == "R" else 205) if s == 0 else (20 if side == "R" else 160)
                    lay = BA.hand_layer((sx, sy), sd, 54 * k, side)
                else:
                    u = (s - 0.15) / 0.85
                    at = (lerp(sx, hx + (g["cx"] - CX), u), lerp(sy, hy, u))
                    d0 = 20 if side == "R" else 160
                    lay = BA.hand_layer(at, lerp(d0, hdeg, u), lerp(54, hlen, u), side)
                hands.append((f"hand{side}", lay))
        for (p0, p1, hgt, nm, start, ln) in hearts:
            u = (i - start + 0.5) / ln
            if 0 < u < 1:
                c = (lerp(p0[0], p1[0], u), lerp(p0[1], p1[1], u))
                fx.append((nm + str(start), part(nm, c, hgt * (0.8 + 0.25 * u), op=fade(u))))
        out.append(fr(poses, g, lab, face, fx=fx, hands=hands))
    return out


# ================================================================== 場景四：8 打瞌睡（循環）與被叫醒（一次）
def _sleep_g(poses, t, n=12):
    ang = 2 * math.pi * t / n
    return base_geom(poses, 0, h=0.935 + 0.012 * math.sin(ang - 0.6), w=1.05 - 0.008 * math.sin(ang - 0.6),
                     rot=3.2 * math.sin(ang), lag=0.02)


def _zzz(t, n=12):
    fx = []
    for off, nm in ((0.0, "zA"), (0.5, "zB")):
        u = (t / n + off) % 1.0
        c = (lerp(322, 404, u), lerp(222, 96, u))
        fx.append((nm, part("fx_zzz", c, 28 + 28 * u, deg=lerp(-6, 8, u), op=fade(u))))
    return fx


def scene_sleep_loop(poses):
    out = []
    for t in range(12):
        ang = 2 * math.pi * t / 12
        g = _sleep_g(poses, t)
        mouth = "tiny" if math.sin(ang - 0.6) > 0.35 else "omega"
        face = face2(poses, ("relax", "relax"), mouth, blush=0.35)
        fx = [x for x in _zzz(t) if x[1].getbbox()]
        out.append(fr(poses, g, f"呼吸／點頭 {t+1}", face, fx=fx))
    labs = ["頭正、吸氣", "吸飽", "開始往前點", "點頭中", "點到最低", "呼氣", "回彈", "抬回來", "歪向另一邊", "再往回", "吸氣", "接回第 1 格"]
    for d, l in zip(out, labs):
        d["label"] = l
    return out


def scene_wake_once(poses):
    plan = [
        ("睡著中（Zzz 淡出）", dict(h=0.935, w=1.05, rot=3.2, lag=0.02), ("relax", "relax"), "tiny", 1.0, 0, 0, 0.35, 0),
        ("被叫醒：整隻彈起！", dict(bottom=-14, h=1.05, w=0.96, lag=-0.05), ("dot", "dot"), "o", 1.35, 8, 1, 0, 0),
        ("驚跳上升（毛炸）", dict(bottom=-34, h=1.075, w=0.945, lag=-0.07), ("dot", "dot"), "o", 1.4, 17, 1, 0, 1),
        ("最高點（毛炸最大）", dict(bottom=-44, h=1.07, w=0.95, lag=-0.05, rot=-2), ("dot", "dot"), "o", 1.4, 19, 1, 0, 1),
        ("往下落", dict(bottom=-16, h=1.04, w=0.97, lag=0.05, rot=1.5), ("dot", "dot"), "o", 1.3, 12, 1, 0, 0),
        ("落地壓扁、毛還炸著", dict(bottom=0, h=0.915, w=1.075, lag=0.03), ("dot", "dot"), "o", 1.2, 7, 0, 0, 1),
        ("彈回、東張西望（左）", dict(h=1.02, w=0.99), ("dot", "dot"), "tiny", 1.1, 0, 0, 0, 1),
        ("東張西望（右）", dict(h=1.0, w=1.0, rot=1), ("dot", "dot"), "tiny", 1.1, 0, 0, 0, 1),
        ("眨眼（搞清楚狀況）", dict(h=0.99, w=1.01), ("relax", "relax"), "smile", 1.0, 0, 0, 0.3, 0),
        ("鬆口氣、笑", dict(h=1.015, w=0.995), ("happy", "happy"), "smile", 1.0, 0, 0, 0.3, 0),
        ("睜眼看著你", dict(h=0.995), ("dot", "dot"), "keep", 1.0, 0, 0, 0, 0),
        ("回待機", dict(h=0.992, w=1.008), ("dot", "dot"), "keep", 1.0, 0, 0, 0, 0),
    ]
    out = []
    for i, (lab, gk, eyes, mouth, es, amp, ex, bl, sweat) in enumerate(plan):
        g = base_geom(poses, 0, **gk)
        look = {6: (-9, 0), 7: (9, 0)}.get(i, (0, 0))
        face = face2(poses, eyes, mouth, scale=es, hl=(eyes[0] == "dot" and i > 0), look=look, blush=bl)
        back = spike_back(poses, g, face, amp, seed=3 + i) if amp else ""
        fx = []
        if i == 0:
            fx.append(("z", part("fx_zzz", (404, 100), 56, deg=8, op=0.5)))
        if ex:
            fx.append(("exclaim", part("fx_exclaim", (394, 138), 58, deg=10)))
        if sweat:
            fx.append(("sweat", part("fx_sweat", (112, 196), 46)))
        if i == 1:
            fx.append(("z", part("fx_zzz", (150, 160), 30, op=0.0)))
        out.append(fr(poses, g, lab, face, fx=[x for x in fx if x[1].getbbox()], back=back))
    return out


# ================================================================== 場景五：9 比 YA 拍照（播一次）
def brackets(on=True, w=5.0):
    if not on:
        return ""
    s = ""
    for (x, y, sx, sy) in ((58, 150, 1, 1), (454, 150, -1, 1), (58, 502, 1, -1), (454, 502, -1, -1)):
        s += (f'<path d="M {P((x, y + 34 * sy))} L {P((x, y))} L {P((x + 34 * sx, y))}" fill="none" stroke="{INK}" '
              f'stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>')
    return s


def scene_selfie(poses):
    V = (392, 296)
    plan = [
        ("待機", {}, None, ("dot", "dot"), "keep", 0, 0),
        ("肉掌從身側冒出", dict(rot=-1), ("h", 30, 0.8), ("dot", "dot"), "keep", 0, 0),
        ("舉到臉旁", dict(rot=-2, lag=-0.02), ("h", 66, 1.0), ("dot", "dot"), "keep", 0, 0),
        ("比 YA（擺姿勢、出現取景框）", dict(rot=-4, cx=-4, lag=-0.03, h=1.01), ("v", 16), ("happy", "happy"), "keep", 1, 0),
        ("YA＋眨左眼", dict(rot=-4.5, cx=-4, lag=-0.03, h=1.01), ("v", 16), ("happy", "dot"), "grin", 1, 0),
        ("閃光！", dict(rot=-4, cx=-3, h=1.015), ("v", 16), ("happy", "happy"), "grin", 1, 0.38),
        ("閃光餘暉", dict(rot=-3.5, cx=-3, h=1.01), ("v", 16), ("happy", "happy"), "grin", 1, 0.12),
        ("拍好了、取景框消失", dict(rot=-2, h=1.0), ("v", 14), ("happy", "happy"), "keep", 0, 0),
        ("眨眼", dict(rot=-1, h=0.99), ("v", 12), ("relax", "relax"), "smile", 0, 0),
        ("YA 收起來", dict(rot=0, h=0.992), ("v", 4), ("dot", "dot"), "keep", 0, 0),
        ("肉掌縮回身側", dict(h=0.99, w=1.008), ("h", 15, 0.6), ("dot", "dot"), "keep", 0, 0),
        ("回待機", dict(h=0.992, w=1.006), None, ("dot", "dot"), "keep", 0, 0),
    ]
    out = []
    for i, (lab, gk, hd, eyes, mouth, brk, fl) in enumerate(plan):
        g = base_geom(poses, 0, **gk)
        face = face2(poses, eyes, mouth, hl=(eyes[0] == "dot" and hd is not None))
        hands, fx = [], []
        if hd and hd[0] == "h":
            lay, _ = hand(poses, g, "R", hd[1], hd[2])
            hands.append(("hand", lay))
        elif hd:
            c = (V[0] + (g["cx"] - CX), V[1] + (14 if i >= 9 else 0))
            hands.append(("V", svg_layer(peace_paw(c, 1.0, 8, hd[1]))))
        if brk:
            fx.append(("brackets", svg_layer(brackets())))
        if i == 5:
            fx += [("sp1", part("fx_sparkle", (92, 204), 46)), ("sp2", part("fx_sparkle", (424, 210), 40, deg=8)),
                   ("sp3", part("fx_sparkle", (66, 330), 34, deg=-8)), ("sp4", part("fx_sparkle", (452, 352), 36))]
        if i == 6:
            fx += [("sp1", part("fx_sparkle", (92, 204), 30, op=0.8)), ("sp2", part("fx_sparkle", (424, 210), 28, op=0.8))]
        out.append(fr(poses, g, lab, face, fx=fx, hands=hands, flash=fl))
    return out


# ================================================================== 情境待機（循環）
def breathe(poses, t, amp=0.012, rot=1.2, **kw):
    ang = 2 * math.pi * t / 12
    base = dict(h=1 + amp * math.sin(ang), w=1 - amp * 0.5 * math.sin(ang), rot=rot * math.sin(ang + 0.5), lag=0.012 * math.sin(ang))
    base.update(kw)
    return base_geom(poses, 0, **base), ang


def scene_idle_down(poses):
    """大盤下跌：不哭、不慌，閉眼輕輕拍拍胸口＋抱著肚子，像在說『沒事沒事』。"""
    dy = [-13, -7, 0, -7, -13, -7, 0, -7, -13, -7, 0, -7]
    out = []
    for t in range(12):
        g, ang = breathe(poses, t, amp=0.01, rot=1.0, h=0.975)
        pat = dy[t] == 0
        eyes = ("relax", "relax") if t not in (0, 11, 1) else ("dot", "dot")
        face = face2(poses, eyes, "smile", look=(0, 4) if eyes[0] == "dot" else (0, 0), hl=eyes[0] == "dot", blush=0.25)
        hands = []
        # 拍胸口的右掌（畫面右側）：貼在胸前，上下輕拍；左掌放肚子上不動
        hands.append(("palmL", BA.hand_layer((190, 392), 8, 50, "L")))
        hands.append(("palmR", BA.hand_layer((312, 368 + dy[t] * 0.9), 172, 50, "R")))
        fx = []
        u = (t / 12 + 0.1) % 1.0
        c = (lerp(330, 352, u), lerp(190, 118, u))
        fx.append(("heart", part("fx_heart", c, 30 + 8 * u, op=0.9 * fade(u))))
        fx = [x for x in fx if x[1].getbbox()]
        out.append(fr(poses, g, ["輕拍胸口（舉）", "輕拍（下）", "拍到胸口", "回彈", "輕拍胸口（舉）", "輕拍（下）", "拍到胸口", "回彈", "輕拍胸口（舉）", "輕拍（下）", "拍到胸口", "回彈、接回第 1 格"][t],
                      face, fx=fx, hands=hands))
    return out


def _confetti_fx(t):
    rng = np.random.default_rng(11)
    out = ""
    cols = (PINK, GOLD, BLUE, MINT, "#F08A5D")
    xs = [44, 74, 428, 462, 58, 440, 90, 410]
    for k, x0 in enumerate(xs):
        ph = rng.uniform(0, 1)
        u = (ph + t / 12) % 1.0
        y = -10 + u * 520
        x = x0 + 9 * math.sin(2 * math.pi * (u * 2 + ph))
        w = 10 * max(0.25, abs(math.cos(2 * math.pi * (t / 12 * 2 + ph * 6))))
        rot = rng.uniform(0, 180) + 40 * t
        pts = [add((x, y), rot2(p, rot)) for p in ((-w / 2, -3), (w / 2, -3), (w / 2, 3), (-w / 2, 3))]
        out += f'<path d="M {" L ".join(P(p) for p in pts)} Z" fill="{cols[k % 5]}" stroke="{INK}" stroke-width="1.3" stroke-linejoin="round"/>'
    return out


def scene_idle_bigup(poses):
    """大漲：輕量彩帶小跳（比 celebrate 小、輕，循環）。"""
    out = []
    labs = ["落地輕壓", "起跳", "上升、舉小肉掌", "接近最高", "最高點（笑）", "開始落下", "落地輕壓", "起跳", "上升", "接近最高", "最高點（笑）", "落下、接回第 1 格"]
    for t in range(12):
        ph = (t % 6) / 6
        hop = math.sin(math.pi * ph) if ph > 0 else 0.0
        g = base_geom(poses, 0, bottom=-15 * hop, h=1 + 0.03 * hop - (0.045 if ph == 0 else 0), w=1 - 0.02 * hop + (0.03 if ph == 0 else 0),
                      rot=2.5 * math.sin(2 * math.pi * t / 12), lag=-0.03 * hop)
        up = hop > 0.5
        face = face2(poses, ("happy", "happy") if up else ("dot", "dot"), "grin" if up else "keep", hl=not up)
        hands = []
        if hop > 0.1:
            lay, _ = hand(poses, g, "R", 20 + 45 * hop, 0.5 + 0.35 * hop)
            hands.append(("handR", lay))
            lay, _ = hand(poses, g, "L", 160 - 45 * hop, 0.5 + 0.35 * hop)
            hands.append(("handL", lay))
        fx = [("confetti", svg_layer(_confetti_fx(t)))]
        if up:
            fx.append(("sp1", part("fx_sparkle", (96 + (g["cx"] - CX), 212), 30)))
            fx.append(("sp2", part("fx_sparkle", (402 + (g["cx"] - CX), 202), 26, deg=8)))
        out.append(fr(poses, g, labs[t], face, fx=fx, hands=hands))
    return out


# ---- 節日帽與道具（本地座標：原點＝帽底中心，y 向上為負）
def at(svg, c, deg=0.0):
    return f'<g transform="translate({f(c[0])},{f(c[1])}) rotate({deg:.2f})">{svg}</g>'


def _st(w=None):
    return f'stroke="{INK}" stroke-width="{w or 5.0}" stroke-linejoin="round" stroke-linecap="round"'


def hat_xmas():
    return (f'<path d="M -50,6 C -46,-30 -18,-68 24,-66 C 48,-64 62,-46 62,-26 L 52,6 Z" fill="{RED}" {_st()}/>'
            f'<path d="M -34,-6 C -28,-34 -8,-52 14,-56" fill="none" stroke="#F58A80" stroke-width="5" stroke-linecap="round"/>'
            f'<circle cx="62" cy="-24" r="12.5" fill="#FFFFFF" {_st(4.6)}/>'
            f'<rect x="-58" y="-9" width="116" height="23" rx="11.5" fill="#FFFFFF" {_st()}/>'
            f'<path d="M -40,2 L -20,2 M 6,4 L 30,4" stroke="#E9DFD2" stroke-width="3.5" stroke-linecap="round"/>')


def hat_newyear():
    return (f'<path d="M -44,6 C -44,-34 -22,-54 0,-54 C 22,-54 44,-34 44,6 Z" fill="{RED}" {_st()}/>'
            f'<path d="M -30,-8 C -28,-28 -14,-42 -2,-46" fill="none" stroke="#F58A80" stroke-width="4.5" stroke-linecap="round"/>'
            f'<rect x="-50" y="-8" width="100" height="18" rx="8" fill="{GOLD}" {_st()}/>'
            f'<circle cx="0" cy="-58" r="7.5" fill="{GOLD}" {_st(4.2)}/>'
            f'<path d="M 0,-44 L 17,-27 L 0,-10 L -17,-27 Z" fill="#C7322E" stroke="{GOLD}" stroke-width="3.6" stroke-linejoin="round"/>')


def zongzi_svg(k=1.0):
    return (f'<path d="M 0,-74 C 16,-52 40,-24 50,-4 C 34,10 -36,10 -50,-4 C -40,-24 -16,-52 0,-74 Z" fill="#7CC768" {_st()}/>'
            f'<path d="M 0,-74 C 16,-52 40,-24 50,-4 C 32,-10 10,-34 0,-74 Z" fill="#58A850" {_st(4.2)}/>'
            f'<path d="M -22,-24 C -12,-34 -6,-46 -2,-58 M -34,-8 C -22,-18 -18,-30 -12,-40" fill="none" stroke="#A8E08E" stroke-width="3.2" stroke-linecap="round"/>'
            f'<path d="M -42,-12 C -18,-2 18,-4 44,-14" fill="none" stroke="{INK}" stroke-width="10.5" stroke-linecap="round"/>'
            f'<path d="M -42,-12 C -18,-2 18,-4 44,-14" fill="none" stroke="{RED}" stroke-width="6" stroke-linecap="round"/>'
            f'<path d="M -2,-76 C -8,-86 -14,-86 -16,-80 M 2,-76 C 8,-86 14,-86 16,-80" fill="none" stroke="{RED}" stroke-width="4" stroke-linecap="round"/>')


def bunny_ear(deg):
    return (f'<g transform="rotate({deg:.2f})"><path d="M 0,20 C -22,-6 -20,-62 -4,-76 C 12,-78 22,-30 14,20 Z" fill="{FUR}" {_st()}/>'
            f'<path d="M -1,10 C -11,-8 -9,-44 -2,-56 C 5,-52 9,-20 6,10 Z" fill="{BLUSH}"/></g>')


def mooncake(c, deg=0.0):
    out = f'<circle r="27" fill="#D9A25B" {_st()}/><circle r="19" fill="none" stroke="#B97A3A" stroke-width="3"/>'
    for k in range(4):
        a = k * 90 + 45
        out += f'<ellipse cx="{f(math.cos(math.radians(a))*9)}" cy="{f(math.sin(math.radians(a))*9)}" rx="6.5" ry="3.8" transform="rotate({a} {f(math.cos(math.radians(a))*9)} {f(math.sin(math.radians(a))*9)})" fill="#F0CC8F"/>'
    out += '<circle r="3.6" fill="#B97A3A"/>'
    return at(out, c, deg)


def red_packet(c, deg=0.0):
    out = (f'<rect x="-23" y="-31" width="46" height="62" rx="6" fill="{RED}" {_st()}/>'
           f'<path d="M -23,-12 L 0,4 L 23,-12" fill="none" stroke="{INK}" stroke-width="3.4" stroke-linejoin="round"/>'
           f'<circle cx="0" cy="6" r="10" fill="{GOLD}" {_st(3.6)}/><path d="M -4,6 L 4,6 M 0,2 L 0,10" stroke="{INK}" stroke-width="2.4" stroke-linecap="round"/>')
    return at(out, c, deg)


def _festival(poses, kind):
    out = []
    for t in range(12):
        g, ang = breathe(poses, t, amp=0.014, rot=1.4)
        head = fwd(poses, g, 254, 172)
        wob = g.get("rot", 0) + 2.2 * math.sin(ang + 1.3)
        blink = t == 8
        happy = t in (4, 5)
        eyes = ("relax", "relax") if blink else (("happy", "happy") if happy else ("dot", "dot"))
        face = face2(poses, eyes, "grin" if happy else "keep", hl=(eyes[0] == "dot" and t % 3 == 0))
        back, front, sprites, fx, hands = "", "", [], [], []
        bob = 3 * math.sin(ang)
        if kind == "xmas":
            front += at(hat_xmas(), add(head, (4, 10)), wob + 4)
            # 雪花（青藍色六角線，淺／深底都看得到），只在身體兩側落下
            for k, x0 in enumerate((52, 84, 428, 458)):
                u = (k * 0.27 + t / 12) % 1.0
                c = (x0 + 8 * math.sin(2 * math.pi * (u * 2 + k)), -10 + u * 500)
                fl = ""
                for a in range(3):
                    v = dirv(a * 60)
                    fl += f'<path d="M {P(add(c, v, -7))} L {P(add(c, v, 7))}" stroke="#4FB4E8" stroke-width="2.6" stroke-linecap="round"/>'
                fx.append((f"snow{k}", svg_layer(fl)))
        elif kind == "newyear":
            front += at(hat_newyear(), add(head, (0, 12)), wob)
            sprites.append(BA.text_layer("福", add(head, rot2((0, -16), wob)), wob, 17, BA._FONT, (249, 194, 60, 255), 0.3))
            hands.append(("hold", BA.hand_layer((356, 468), 118, 38, "R")))
            front += red_packet((334, 432 + bob), 8 + 3 * math.sin(ang))
            for k, (x0, y0) in enumerate(((166, 186), (330, 178))):
                r = 7 + 5 * max(0, math.sin(ang * 2 + k * 2))
                fx.append((f"sp{k}", svg_layer(sparkle((x0, y0), r, GOLD))))
        elif kind == "dragon":
            front += at(zongzi_svg(), add(head, (0, 12)), wob + 3)
            u = (t / 12) % 1.0
            fx.append(("steam", part("fx_smoke", (lerp(244, 262, u), lerp(128, 88, u)), 30, op=0.8 * fade(u))))
            fx = [x for x in fx if x[1].getbbox()]
            hands.append(("hold", BA.hand_layer((356, 468), 118, 38, "R")))
            front += at(zongzi_svg(), (334, 440 + bob), 6 + 3 * math.sin(ang)).replace("<g ", '<g transform-origin="0 0" ', 0)
        elif kind == "moon":
            for sgn, ph in ((-1, 0.0), (1, 1.6)):
                c = fwd(poses, g, 254 + sgn * 26, 190)
                back += at(bunny_ear(sgn * 11 + 6 * math.sin(ang + ph) + wob), c, 0)
            hands.append(("hold", BA.hand_layer((356, 468), 118, 38, "R")))
            front += mooncake((334, 436 + bob), 10 * math.sin(ang) )
            for k, (x0, y0) in enumerate(((150, 176), (352, 170))):
                r = 6 + 5 * max(0, math.sin(ang * 2 + k * 2))
                fx.append((f"sp{k}", svg_layer(sparkle((x0, y0), r, GOLD))))
        labs = ["輕輕呼吸", "帽子晃", "晃回", "帽子晃", "笑一下", "笑", "回正", "帽子晃", "眨眼", "睜眼", "帽子晃", "接回第 1 格"]
        out.append(fr(poses, g, labs[t], face, fx=fx, sprites=sprites, front=front, back=back, hands=hands))
    return out


def scene_festival_newyear(poses):
    return _festival(poses, "newyear")


def scene_festival_dragon(poses):
    return _festival(poses, "dragon")


def scene_festival_moon(poses):
    return _festival(poses, "moon")


def scene_festival_xmas(poses):
    return _festival(poses, "xmas")


# ---- 週末：躺著喝珍奶、曬太陽（原圖第 6 張＝趴扁的身體；表情是原圖的 > < 瞇眼）
def sun_svg(c, rot):
    out = ""
    for k in range(12):
        a = k * 30 + rot
        p0, p1 = add(c, dirv(a), 31), add(c, dirv(a), 43 if k % 2 == 0 else 38)
        out += f'<path d="M {P(p0)} L {P(p1)}" stroke="{INK}" stroke-width="9.5" stroke-linecap="round"/><path d="M {P(p0)} L {P(p1)}" stroke="{GOLD}" stroke-width="5" stroke-linecap="round"/>'
    out += (f'<circle cx="{f(c[0])}" cy="{f(c[1])}" r="25" fill="{GOLD_LT}" {_st()}/>'
            f'<path d="M {P(add(c,(-13,-4)))} Q {P(add(c,(-9,-10)))} {P(add(c,(-5,-4)))} M {P(add(c,(5,-4)))} Q {P(add(c,(9,-10)))} {P(add(c,(13,-4)))}" fill="none" stroke="{INK}" stroke-width="3.2" stroke-linecap="round"/>'
            f'<path d="M {P(add(c,(-5,5)))} Q {P(add(c,(0,10)))} {P(add(c,(5,5)))}" fill="none" stroke="{INK}" stroke-width="3.2" stroke-linecap="round"/>')
    return out


def scene_weekend(poses):
    import bibi_scenes_b as BB
    out = []
    labs = ["躺平、吸一口", "珍珠往上", "珍珠到嘴", "嚼嚼", "放鬆", "呼氣", "再吸一口", "珍珠往上", "珍珠到嘴", "嚼嚼", "曬太陽放鬆", "接回第 1 格"]
    for t in range(12):
        ang = 2 * math.pi * t / 12
        g = base_geom(poses, 6, h=1 + 0.018 * math.sin(ang), w=1 - 0.008 * math.sin(ang), lag=0.01 * math.sin(ang))
        sip = (t % 6)
        dots = {0: [], 1: [0.3], 2: [0.62, 0.2], 3: [0.92, 0.5], 4: [0.8], 5: []}[sip]
        m = fwd(poses, g, 246, 419)
        mouth = (m[0] + 3, m[1] + 2)
        back = ""
        mat_y = 478
        back += (f'<path d="M 84,{mat_y} Q 248,{mat_y-8} 412,{mat_y} L 420,{mat_y+22} Q 248,{mat_y+30} 76,{mat_y+22} Z" fill="#8FD3F5" {_st(4.4)}/>'
                 f'<path d="M 96,{mat_y+10} Q 248,{mat_y+2} 400,{mat_y+10}" fill="none" stroke="#FFFFFF" stroke-width="4" stroke-linecap="round" opacity="0.8"/>')
        front = BB.boba_svg((352, 494), 4, 0.74 - 0.05 * (1 if sip in (3, 4) else 0), t * 0.7, dots, (mouth[0] + 8, mouth[1] + 3))
        fx = [("sun", svg_layer(sun_svg((104, 150), t * 2.5)))]
        hands = [("hold", BA.hand_layer((322, 478), 96, 30, "L"))]
        face = poses[6]
        out.append(fr(poses, g, labs[t], face, fx=fx, front=front, back=back, hands=hands))
    return out


# ================================================================== 輸出
# 名稱 → (中文名, 場景函式, 每格停留 ms, 是否循環, 用途)
SCENES = {
    "highfive": ("擊掌", scene_highfive, [140, 100, 90, 90, 120, 90, 180, 130, 110, 110, 120, 200], False, "客服鈕：點一下比比→跟你擊掌"),
    "dance": ("跳舞", scene_dance, [130] * 12, False, "客服鈕：連點／長按→開心跳舞，頭上飄音符"),
    "hug": ("抱抱", scene_hug, [140, 100, 100, 110, 120, 170, 170, 160, 160, 120, 110, 180], False, "客服鈕：安慰、感謝時抱抱自己臉紅冒愛心"),
    "sleep_loop": ("打瞌睡（循環）", scene_sleep_loop, [150] * 12, True, "客服鈕：久未操作→打瞌睡，Zzz 往上飄"),
    "wake_once": ("被叫醒驚跳", scene_wake_once, [220, 70, 70, 80, 80, 100, 130, 130, 110, 130, 120, 200], False, "客服鈕：打瞌睡時被點→驚跳、回待機"),
    "idle_down": ("大盤下跌・輕拍胸口安慰", scene_idle_down, [120] * 12, True, "大盤下跌時的待機：平靜溫柔，沒事沒事"),
    "idle_bigup": ("大漲・輕量彩帶小跳", scene_idle_bigup, [100] * 12, True, "大盤大漲時的待機：小跳＋彩帶，比 celebrate 輕"),
    "festival_newyear": ("新年・小春聯帽＋紅包", scene_festival_newyear, [130] * 12, True, "春節待機"),
    "festival_dragon": ("端午・粽子帽", scene_festival_dragon, [130] * 12, True, "端午節待機"),
    "festival_moon": ("中秋・兔耳＋月餅", scene_festival_moon, [130] * 12, True, "中秋節待機"),
    "festival_xmas": ("聖誕・聖誕帽", scene_festival_xmas, [130] * 12, True, "聖誕節待機"),
    "weekend": ("週末・躺著喝珍奶曬太陽", scene_weekend, [130] * 12, True, "週末（非交易日）放鬆待機"),
    "selfie": ("比 YA 拍照", scene_selfie, [140, 100, 100, 130, 150, 90, 80, 150, 130, 110, 110, 190], False, "客服鈕：拍照、分享截圖時"),
}


def save_webp(imgs, durs, path, px=160, budget=60_000):
    small = [im.resize((px, px), Image.LANCZOS) for im in imgs]
    for q in (80, 70, 60, 50, 40):
        small[0].save(path, save_all=True, append_images=small[1:], duration=durs, loop=0, lossless=False,
                      quality=q, method=6)
        if Path(path).stat().st_size <= budget:
            return q, Path(path).stat().st_size
    return q, Path(path).stat().st_size


def write_storyboard(path, key, name, labels, durs, loop, use, hits):
    L = [f"名稱：bibi_{key}（{name}）",
         f"用途：{use}｜網頁版客服鈕 160px 顯示｜輸出 512×512 透明（動態 WebP 為 160px 版）｜"
         f"{'循環' if loop else '播一次後最後一格回待機'}｜總長 {sum(durs)/1000:.2f} 秒",
         "造型：以官方部件總表為準——四肢只有貼身小肉掌，沒有手臂；效果符號用官方部件。", "",
         "| 格 | 動作與表情 | 停留 ms | 備註 |", "|---|---|---|---|"]
    for i, (lb, d) in enumerate(zip(labels, durs)):
        note = ""
        if i == 0:
            note = "循環起點" if loop else "待機起點"
        if i == len(labels) - 1:
            note = "接回第 1 格" if loop else "回待機（跟第 1 格同姿勢）"
        L.append(f"| {i+1:02d} | {lb} | {d} | {note} |")
    L += ["", f"重疊檢查（效果符號 vs 身體／彼此／小肉掌，程式逐幀）：12 幀 {len(hits)} 筆。"]
    for h in hits:
        L.append(f"- 第 {h[0]} 格：{h[1]} × {h[2]}（{h[3]} px）")
    Path(path).write_text("\n".join(L) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="site/brand/src/support_anim_1009.gif")
    ap.add_argument("--out", required=True)
    ap.add_argument("--repo-out", default="docs/anim")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    poses = pose_tween.load_poses(Path(a.src))
    only = [x for x in a.only.split(",") if x]
    for key, (name, fn, durs, loop, use) in SCENES.items():
        if only and key not in only:
            continue
        frs = fn(poses)
        assert len(frs) == 12 and len(durs) == 12, (key, len(frs))
        imgs = [render_frame(poses, d) for d in frs]
        hits = []
        for j, d in enumerate(frs):
            for h in overlap_check(poses, d):
                hits.append((j + 1, h[0], h[1], h[2]))
        fd = Path(a.out) / key / "frames"
        fd.mkdir(parents=True, exist_ok=True)
        for j, im in enumerate(imgs):
            im.save(fd / f"frame_{j+1:02d}.png")
        rd = Path(a.repo_out) / f"bibi_{key}"
        rd.mkdir(parents=True, exist_ok=True)
        labels = [d["label"] for d in frs]
        sheet12(imgs, [f"{j+1:02d} {l}" for j, l in enumerate(labels)], rd / "sheet_12.png")
        q, sz = save_webp(imgs, durs, rd / "anim.webp")
        imgs[0].save(Path(a.out) / key / "anim.gif", save_all=True, append_images=imgs[1:], duration=durs, loop=0, disposal=2)
        write_storyboard(rd / "storyboard.md", key, name, labels, durs, loop, use, hits)
        arr = [np.asarray(im).astype(int) for im in imgs]
        diffs = [int(np.abs(arr[k] - arr[(k + 1) % 12]).sum() // 1000) for k in range(12)]
        print(f"{key}: webp160 {sz/1024:.1f}KB(q{q}) 相鄰差 min {min(diffs)} 重疊 {len(hits)} 筆 {hits[:6]}")


if __name__ == "__main__":
    main()
