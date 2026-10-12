"""比比「基礎姿勢資產包」（2026-10-12 全部重做第一步）。

為什麼有這支
------------
Andy 10-12：線上版比比的側面與跑步「不像原本的比比」（側臉縮在角落、輪廓變瘦變幾何、跑步忽胖忽瘦）。
規格：docs/anim/bibi_library/reference/rules_1012_redo_all.md（ASSET_MODE=raster_first）。

做法（原圖擷取＋分層＋假 3D 轉身）
---------------------------------
1. 只用 `default_idle_1011.webp` 的原始像素：去背 → 拆成「身體毛球（含毛邊、描邊、側邊毛色斑）」、
   兩隻耳朵、兩隻腳、兩隻眼睛、嘴（含舌頭）、兩顆腮紅。五官挖掉的地方用周圍奶油色補（inpaint）。
2. 毛球近似一顆球：**繞垂直軸轉身時球的外輪廓不變**，所以身體外框（波浪毛邊、粗描邊）每個姿勢都是原圖那一圈，
   只有「貼在球面上的東西」跟著轉：五官依經度位移＋輕微透視壓縮（壓縮量刻意減半，避免側臉縮成一小塊）、
   耳朵沿頭頂輪廓滑動、四隻腳放在身體下方的地面圓上依經度排前後。
3. 壓縮／拉伸／趴：身體用「極座標位移變形」——內部等比縮放、外圈 15% 只平移不縮放，
   所以描邊粗細不變、毛邊不被拉扁；sx×sy＝1（體積守恆）。五官／耳朵／腳不縮放，只換位置。
4. 一律在 2048×2048 合成（原圖 ×4），最後 LANCZOS（預乘 alpha）縮到 512 透明 PNG。

座標系統（512 單位）：畫布 512×512；地面（腳底）基準線 y=GROUND；身體水平中心 x=CX。
所有姿勢共用這一組，不重新置中。

用法：python scripts/anim/bibi_basepose.py [--out docs/anim/bibi_basepose_1012]
"""
from __future__ import annotations

import argparse
import json
import math
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageSequence
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "docs/anim/bibi_library/reference"
SRC_DEFAULT = REF / "default_idle_1011.webp"
SRC_GIF = ROOT / "site/brand/src/support_anim_1009.gif"
JUMP_GIF = ROOT / "docs/anim/jump/animation.gif"

K = 4                 # 工作倍率：512 → 2048
W = 512 * K
INK = np.array([16, 4, 3], float)
BG = np.array([252, 246, 239], float)
CREAM = np.array([253, 246, 235], float)

# 原圖量到的錨點（512 單位）
SEED_FUR = (256, 380)
SEED_EAR = [(144, 203), (359, 201)]      # 左耳（畫面左）、右耳
SEED_FOOT = [(181, 462), (327, 462)]
SEED_PATCH = [(110, 257), (396, 254)]   # 兩側深色毛斑（側面時朝前那塊淡出，否則會黏在嘴邊）
EYES_BB = [(180, 250, 205, 277), (297, 248, 321, 275)]
MOUTH_BB = (221, 263, 280, 318)
BLUSH_SEED = [(151, 289), (351, 284)]


# ---------------------------------------------------------------- 小工具
def disk(r: int) -> np.ndarray:
    y, x = np.ogrid[-r:r + 1, -r:r + 1]
    return (x * x + y * y) <= r * r


def up(m: np.ndarray) -> np.ndarray:
    """512 的遮罩（bool/float）→ 2048 的平滑 float 遮罩。"""
    f = m.astype(np.float32)
    return cv2.resize(f, (W, W), interpolation=cv2.INTER_LINEAR)


def comp_at(mask: np.ndarray, seed) -> np.ndarray:
    lab, _ = ndi.label(mask)
    v = lab[seed[1], seed[0]]
    assert v, f"seed {seed} 不在遮罩裡"
    return lab == v


def lum(a: np.ndarray) -> np.ndarray:
    return a[..., :3].mean(-1)


def to_img(rgba: np.ndarray) -> Image.Image:
    """內部陣列：RGB 0~255、alpha 0~1（非預乘）。"""
    out = np.empty(rgba.shape, np.uint8)
    out[..., :3] = np.clip(rgba[..., :3], 0, 255).round()
    out[..., 3] = np.clip(rgba[..., 3] * 255, 0, 255).round()
    return Image.fromarray(out, "RGBA")


def down512(im: Image.Image) -> Image.Image:
    return im.convert("RGBa").resize((512, 512), Image.LANCZOS).convert("RGBA")


def scallop(mask: np.ndarray, zone: np.ndarray, step=20 * K, rad=12 * K, off=-5 * K) -> np.ndarray:
    """在 zone 內沿輪廓加一圈小圓弧（跟原圖毛邊同尺寸的波浪），避免補出來的輪廓變成光滑幾何線。"""
    m = mask.copy()
    er = cv2.erode(mask.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    edge = mask & ~er & zone
    ys, xs = np.nonzero(edge)
    if len(xs) == 0:
        return m
    sm = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), 4 * K)
    gy, gx = np.gradient(sm)
    taken = []
    rng = np.random.default_rng(7)
    for i in rng.permutation(len(xs)):
        x, y = xs[i], ys[i]
        if any((x - a) ** 2 + (y - b) ** 2 < step * step for a, b in taken):
            continue
        taken.append((x, y))
    canvas = np.zeros(mask.shape, np.uint8)
    for x, y in taken:
        nx, ny = -gx[y, x], -gy[y, x]
        nn = math.hypot(nx, ny) or 1.0
        cx_, cy_ = x + nx / nn * off, y + ny / nn * off
        cv2.circle(canvas, (int(cx_), int(cy_)), int(rad), 1, -1, lineType=cv2.LINE_8)
    return m | ((canvas > 0) & zone)


def reink(body: np.ndarray, cut: np.ndarray, t: int) -> np.ndarray:
    """耳朵／腳拿走後，毛球在那幾處缺了描邊、留下凹口：
    在切口附近把輪廓修圓（閉運算＋平滑＋毛邊小波浪），新補的毛用周圍顏色 inpaint，再沿新輪廓補上同粗細的描邊。"""
    zone = cv2.dilate(cut.astype(np.uint8), disk(6 * K).astype(np.uint8)) > 0
    zp = cv2.dilate(cut.astype(np.uint8), disk(t + 10 * K).astype(np.uint8)) > 0     # 補描邊的範圍
    zw = cv2.GaussianBlur(zp.astype(np.float32), (0, 0), 4 * K)                      # 邊緣羽化
    zw = np.clip((zw - 0.5) * 2.5 + 0.5, 0, 1)
    bm = body[..., 3] > 0.5
    closed = cv2.morphologyEx(bm.astype(np.uint8), cv2.MORPH_CLOSE, disk(22 * K).astype(np.uint8)) > 0
    newm = np.where(zone, closed, bm)
    sm = cv2.GaussianBlur(newm.astype(np.float32), (0, 0), 2.5 * K)
    newm = np.where(zone, sm > 0.5, bm)
    newm = scallop(newm, zone & (closed & ~bm))
    sm = cv2.GaussianBlur(newm.astype(np.float32), (0, 0), 1.0 * K)
    newm = np.where(zone, sm > 0.5, bm)
    rgb = body[..., :3].copy()
    bgr = cv2.cvtColor(np.clip(rgb, 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
    dark = lum(rgb) < 140
    holem = ((newm & ~bm) | (zone & (body[..., 3] < 0.99)) | (dark & zone)).astype(np.uint8)
    inp = cv2.inpaint(bgr, holem, 8, cv2.INPAINT_TELEA)
    inp = cv2.cvtColor(inp, cv2.COLOR_BGR2RGB).astype(np.float32)
    rgb = np.where(holem[..., None].astype(bool), inp, rgb)
    # 沿新輪廓畫描邊：距外緣 < t 的內圈塗墨
    din = ndi.distance_transform_edt(newm)
    soft = np.clip((t + 1.5 * K - din) / (1.5 * K), 0, 1)
    soft = np.where(zp, soft, 0) * np.maximum(zw, (holem > 0))
    rgb = rgb * (1 - soft[..., None]) + INK * soft[..., None]
    a = body[..., 3].copy()
    edge = cv2.GaussianBlur(newm.astype(np.float32), (0, 0), 0.8 * K)
    a = np.where(zone, edge, a)
    return np.dstack([rgb, a]).astype(np.float32)


# ---------------------------------------------------------------- 1. 拆層
@lru_cache(None)
def layers():
    src = Image.open(SRC_DEFAULT).convert("RGB")
    a512 = np.asarray(src).astype(float)
    L = lum(a512)
    ink = L < 110
    filled = ndi.binary_fill_holes(ink)
    nonink = filled & ~ink
    r_, g_, b_ = a512[..., 0], a512[..., 1], a512[..., 2]
    colp = nonink & ((r_ - b_) > 35) & (g_ < 200)              # 粉橘／棕色（耳、腳、腮紅、側邊毛斑）
    fur = ndi.binary_fill_holes(comp_at(nonink & ~colp, SEED_FUR))   # 毛球內部（含五官洞）
    ears = [ndi.binary_fill_holes(comp_at(colp, s)) for s in SEED_EAR]
    feet = [ndi.binary_fill_holes(comp_at(colp, s)) for s in SEED_FOOT]

    big = np.asarray(src.resize((W, W), Image.LANCZOS)).astype(np.float32)
    Lb = lum(big)

    # --- 去背：填滿區 alpha=1；外圈 2px 用亮度跟「局部底色」反解 alpha
    fill4 = up(filled) > 0.5
    ring = cv2.dilate(fill4.astype(np.uint8), disk(3 * K // 2 + 1).astype(np.uint8)) > 0
    ring &= ~fill4
    bgL = np.where(fill4, 0, Lb)
    bgL = ndi.maximum_filter(bgL, size=4 * K + 1)
    bgL = np.maximum(bgL, 150)
    a_ring = np.clip((bgL - Lb) / np.maximum(bgL - INK.mean(), 1), 0, 1)
    alpha = np.where(fill4, 1.0, np.where(ring, a_ring, 0.0)).astype(np.float32)
    rgb = big.copy()
    rgb[ring] = INK          # 外圈顏色＝描邊色（alpha 決定深淺）

    # --- 每個像素屬於誰：耳朵／腳（含自己那一圈描邊），但跟毛球共用的那條描邊留給身體
    t = 13 * K                                   # 描邊厚度（原圖約 12px）
    fur4 = up(fur) > 0.5
    d_fur = ndi.distance_transform_edt(~fur4)    # 到毛球內部的距離
    def owned(region512):
        r4 = up(region512) > 0.5
        d = ndi.distance_transform_edt(~r4)
        return (d <= t + 3 * K) & (d_fur > d) & (alpha > 0)
    ear_own = [owned(e) for e in ears]
    foot_own = [owned(f) for f in feet]

    def cut(own):
        m = own.astype(np.float32)
        out = np.dstack([rgb, alpha * m])
        return out

    # --- 五官遮罩
    eye_m = []
    for bb in EYES_BB:
        m = np.zeros_like(ink)
        x0, y0, x1, y1 = bb
        m[y0 - 2:y1 + 3, x0 - 2:x1 + 3] = True
        eye_m.append(m & fur)
    x0, y0, x1, y1 = MOUTH_BB
    mouth_m = np.zeros_like(ink)
    mouth_m[y0 - 3:y1 + 4, x0 - 3:x1 + 4] = True
    mouth_m &= fur
    r, g, b = a512[..., 0], a512[..., 1], a512[..., 2]
    peach = (r > 200) & (g < 225) & ((r - b) > 40)
    blush_m = [ndi.binary_dilation(comp_at(peach & fur & ~mouth_m, s), disk(4)) & fur for s in BLUSH_SEED]

    # --- 身體底：五官挖掉後 inpaint（只在毛球內）
    hole = np.zeros_like(ink)
    for m in eye_m + blush_m + [mouth_m]:
        hole |= ndi.binary_dilation(m, disk(4))
    hole4 = (up(hole) > 0.3).astype(np.uint8)
    bgr = cv2.cvtColor(big.astype(np.uint8), cv2.COLOR_RGB2BGR)
    inp = cv2.inpaint(bgr, hole4, 12, cv2.INPAINT_TELEA)
    body_rgb = cv2.cvtColor(inp, cv2.COLOR_BGR2RGB).astype(np.float32)
    # inpaint 會在大洞中間留下不自然的平塊，再用大範圍模糊的奶油色柔化一次
    blur = cv2.GaussianBlur(body_rgb, (0, 0), 6 * K)
    hm = cv2.GaussianBlur(hole4.astype(np.float32), (0, 0), 2 * K)[..., None]
    body_rgb = body_rgb * (1 - hm) + blur * hm
    body_rgb = np.where(fill4[..., None], body_rgb, rgb)
    own_any = np.zeros_like(fill4)
    for o in ear_own + foot_own:
        own_any |= o
    body = np.dstack([body_rgb, alpha * (~own_any)])
    body = reink(body, own_any, t)

    # --- 五官貼片：對奶油色反解 alpha，顏色固定（拿到哪裡貼都乾淨）
    def decal_dark(m512):
        m4 = up(ndi.binary_dilation(m512, disk(1))) > 0.3
        a = np.clip((CREAM.mean() - Lb) / (CREAM.mean() - INK.mean()), 0, 1) * m4
        out = np.zeros((W, W, 4), np.float32)
        out[..., :3] = INK
        out[..., 3] = a
        return out

    def decal_mouth(m512):
        inside = ndi.binary_fill_holes((L < 110) & m512)
        in4 = up(ndi.binary_erosion(inside, disk(1))) > 0.5
        m4 = up(m512) > 0.3
        a = np.clip((CREAM.mean() - Lb) / (CREAM.mean() - INK.mean()), 0, 1) * m4
        out = np.zeros((W, W, 4), np.float32)
        out[..., :3] = INK
        out[..., 3] = a
        out[in4, :3] = big[in4]          # 嘴裡（舌頭、深色口腔）保留原色
        out[in4, 3] = 1
        return out

    def decal_blush(m512):
        m4 = up(m512) > 0.3
        G = big[..., 1]
        col = np.array([252, 176, 142], np.float32)
        a = np.clip((CREAM[1] - G) / (CREAM[1] - col[1]), 0, 1) * m4
        out = np.zeros((W, W, 4), np.float32)
        out[..., :3] = col
        out[..., 3] = a
        return out

    feats = {
        "eye_l": decal_dark(eye_m[0]), "eye_r": decal_dark(eye_m[1]),
        "mouth": decal_mouth(mouth_m),
        "blush_l": decal_blush(blush_m[0]), "blush_r": decal_blush(blush_m[1]),
    }
    # 兩側毛斑淡出版本：毛斑像素用周圍的毛色補掉（描邊不動）
    nop = []
    for sd in SEED_PATCH:
        pm = ndi.binary_dilation(comp_at(colp, sd), disk(2)) & ~ink
        pm4 = (up(pm) > 0.3) & (body[..., 3] > 0.5) & (lum(body) > 110)
        ring_ = cv2.dilate(pm4.astype(np.uint8), disk(12 * K).astype(np.uint8)).astype(bool) & ~pm4
        src_ = ring_ & (lum(body) > 215) & (body[..., 3] > 0.9)
        col = np.median(body[src_][:, :3], 0)
        w_ = cv2.GaussianBlur(pm4.astype(np.float32), (0, 0), 1.5 * K)[..., None]
        w_ = np.clip(w_ * 1.6, 0, 1) * (lum(body) > 110)[..., None]
        b2 = body.copy()
        b2[..., :3] = body[..., :3] * (1 - w_) + col * w_
        nop.append(b2)
    parts = {
        "body": body,
        "body_nopatch_l": nop[0], "body_nopatch_r": nop[1],
        "fur": up(fur).astype(np.float32),
        "ear_l": cut(ear_own[0]), "ear_r": cut(ear_own[1]),
        "foot_l": cut(foot_own[0]), "foot_r": cut(foot_own[1]),
        **feats,
        "_orig": np.dstack([rgb, alpha]),
    }
    return parts


def crop_part(arr: np.ndarray):
    """回傳 (裁切後陣列, 左上角 x, y)。"""
    ys, xs = np.nonzero(arr[..., 3] > 0.01)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    return arr[y0:y1, x0:x1].copy(), x0, y0


# ---------------------------------------------------------------- 2. 幾何量測
def _rows_extent(mask: np.ndarray):
    """每一列的左右界（沒有就 nan）。"""
    h = mask.shape[0]
    xl = np.full(h, np.nan)
    xr = np.full(h, np.nan)
    any_ = mask.any(1)
    idx = np.nonzero(any_)[0]
    xl[idx] = mask[idx].argmax(1)
    xr[idx] = mask.shape[1] - 1 - mask[idx][:, ::-1].argmax(1)
    return xl, xr


def _cols_top(mask: np.ndarray):
    w = mask.shape[1]
    top = np.full(w, np.nan)
    bot = np.full(w, np.nan)
    any_ = mask.any(0)
    idx = np.nonzero(any_)[0]
    top[idx] = mask[:, idx].argmax(0)
    bot[idx] = mask.shape[0] - 1 - mask[::-1, idx].argmax(0)
    return top, bot


def _smooth(v: np.ndarray, sig: float) -> np.ndarray:
    ok = ~np.isnan(v)
    f = ndi.gaussian_filter1d(np.where(ok, v, 0.0), sig)
    wgt = ndi.gaussian_filter1d(ok.astype(float), sig)
    out = f / np.maximum(wgt, 1e-6)
    out[wgt < 0.2] = np.nan
    return out


def centroid(arr):
    a = arr[..., 3]
    ys, xs = np.nonzero(a > 0.05)
    w = a[ys, xs]
    return float((xs * w).sum() / w.sum()), float((ys * w).sum() / w.sum())


@lru_cache(None)
def geo():
    P = layers()
    bm = P["body"][..., 3] > 0.5
    ys, xs = np.nonzero(bm)
    g = {}
    g["x0"], g["x1"], g["y0"], g["y1"] = xs.min(), xs.max(), ys.min(), ys.max()
    g["cx"] = (g["x0"] + g["x1"]) / 2
    g["cy"] = (g["y0"] + g["y1"]) / 2
    g["RX"] = (g["x1"] - g["x0"]) / 2
    om = P["_orig"][..., 3] > 0.5
    g["ground"] = float(np.nonzero(om.any(1))[0].max())        # 原圖腳底
    # 身體在各方向的半徑（以 cx,cy 為中心），平滑掉毛邊起伏
    n = 720
    th = np.linspace(-np.pi, np.pi, n, endpoint=False)
    rr = np.arange(0, W, 1.0)
    R = np.zeros(n)
    for i, t in enumerate(th):
        x = g["cx"] + rr * np.cos(t)
        y = g["cy"] + rr * np.sin(t)
        ok = (x >= 0) & (x < W) & (y >= 0) & (y < W)
        inside = np.zeros_like(rr, bool)
        inside[ok] = bm[y[ok].astype(int), x[ok].astype(int)]
        R[i] = rr[inside].max() if inside.any() else 0
    Rs = ndi.gaussian_filter1d(np.concatenate([R, R, R]), 10)[n:2 * n]
    g["th"], g["R"] = th, Rs
    for k in ("eye_l", "eye_r", "mouth", "blush_l", "blush_r", "ear_l", "ear_r", "foot_l", "foot_r"):
        g[k] = centroid(P[k])
    return g


# ---------------------------------------------------------------- 3. 身體變形（極座標位移，描邊不變粗）
def warp_body(sx=1.0, sy_top=1.0, sy_bot=1.0, fade_r=0.0, fade_l=0.0):
    """回傳 (變形後身體 RGBA, 變形後毛球內部遮罩, 新中心 cx, cy)。底部貼地不動、水平中心不動。"""
    P, g = layers(), geo()
    cx, cy, by = g["cx"], g["cy"], float(g["y1"])
    cy2 = by - (by - cy) * sy_bot
    yy, xx = np.mgrid[0:W, 0:W].astype(np.float32)
    dx, dy = xx - cx, yy - cy2
    syv = np.where(dy < 0, sy_top, sy_bot)
    dxs, dys = dx / sx, dy / syv
    rs = np.hypot(dxs, dys)
    r = np.hypot(dx, dy)
    k = r / np.maximum(rs, 1e-6)
    th = np.arctan2(dys, dxs)
    Rt = np.interp(th, g["th"], g["R"], period=2 * np.pi)
    t = r / np.maximum(k * Rt, 1e-6)
    s = np.clip((t - 0.55) / 0.33, 0, 1)
    s = s * s * (3 - 2 * s)
    gg = t + (1 - t) * s
    gg = np.where(t > 0.88, 1.0 + (t - 0.88) * 0, gg)
    r_src = r - (k - 1) * Rt * gg
    mx = (cx + r_src * np.cos(th)).astype(np.float32)
    my = (cy + r_src * np.sin(th)).astype(np.float32)
    body = P["body"]
    if fade_r > 0:
        body = body * (1 - fade_r) + P["body_nopatch_r"] * fade_r
    if fade_l > 0:
        body = body * (1 - fade_l) + P["body_nopatch_l"] * fade_l
    pm = np.dstack([body[..., :3] * body[..., 3:4], body[..., 3:4], P["fur"][..., None]]).astype(np.float32)
    o1 = cv2.remap(np.ascontiguousarray(pm[..., :4]), mx, my, cv2.INTER_CUBIC,
                   borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    o2 = cv2.remap(np.ascontiguousarray(pm[..., 4]), mx, my, cv2.INTER_LINEAR,
                   borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    out = np.dstack([o1, o2])
    a = np.clip(out[..., 3], 0, 1)
    rgb = out[..., :3] / np.maximum(a[..., None], 1e-4)
    return np.dstack([rgb, a]), np.clip(out[..., 4], 0, 1), cx, cy2


# ---------------------------------------------------------------- 4. 貼片放置
def _pil(arr):
    return to_img(arr)


@lru_cache(None)
def decal(name: str):
    """裁切後的 PIL 貼片與「回到原圖位置時」的錨點（原圖質心，相對裁切框）。"""
    if name == "foot_l":
        # 左右腳用同一張（右腳原圖鏡射），保證每一格、每一隻腳都一樣大
        im, ax, ay = decal("foot_r")
        return im.transpose(Image.FLIP_LEFT_RIGHT), im.width - ax, ay
    P = layers()
    arr = P[name]
    gx, gy = centroid(arr)
    c, x0, y0 = crop_part(arr)
    if name.startswith("foot"):
        c, y0 = extend_foot(c, y0)
    return _pil(c), gx - x0, gy - y0


def extend_foot(c: np.ndarray, y0: int):
    """原圖腳只露出下半，上緣是被毛蓋住的切口（還混著毛的陰影色）。
    找到第一列「整列都是腳掌粉橘＋兩側描邊」的乾淨列，把它以下的原圖像素上下鏡射，補成完整的扁圓腳。"""
    a = c[..., 3] > 0.5
    r, g, b = c[..., 0], c[..., 1], c[..., 2]
    peach = (r - b > 60) & (g < 190) & a
    span = a.sum(1)
    frac = peach.sum(1) / np.maximum(span, 1)
    mx = span.max()
    r0 = None
    for i in range(c.shape[0]):
        if frac[i] > 0.62 and span[i] > 0.75 * mx:
            r0 = i + K
            break
    if r0 is None:
        return c, y0
    low = c[r0:]
    top = low[::-1][:-1]
    out = np.concatenate([top, low], 0)       # 上下對稱的扁圓腳（上半藏在身體後面）
    return out, y0 + r0 - top.shape[0]


def paste(canvas: Image.Image, name: str, x: float, y: float, sx=1.0, sy=1.0, rot=0.0,
          flip=False, clip=None, alpha=1.0, img=None, anchor=None):
    """把貼片的質心放到 (x,y)（2048 座標）。rot：度，順時針為正。"""
    if img is None:
        im, ax, ay = decal(name)
    else:
        im = img
        ax, ay = anchor
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
        ax = im.width - ax
    r = math.radians(rot)
    c, s_ = math.cos(r), math.sin(r)
    # 正向：p' = T + R·S·(p - a)
    A = np.array([[c * sx, -s_ * sy], [s_ * sx, c * sy]])
    Ai = np.linalg.inv(A)
    off = np.array([ax, ay]) - Ai @ np.array([x, y])
    data = (Ai[0, 0], Ai[0, 1], off[0], Ai[1, 0], Ai[1, 1], off[1])
    lay = im.convert("RGBa").transform(canvas.size, Image.AFFINE, data, resample=Image.BICUBIC).convert("RGBA")
    if clip is not None or alpha < 1:
        la = np.asarray(lay).astype(np.float32)
        m = np.ones(la.shape[:2], np.float32) * alpha
        if clip is not None:
            m = m * clip
        la[..., 3] *= m
        lay = Image.fromarray(la.clip(0, 255).astype(np.uint8), "RGBA")
    canvas.alpha_composite(lay)


def closed_eye(kind: str, w: float, sw: float):
    """閉眼（︶ 笑眼或 > < 用力閉眼）。以原圖眼睛的墨色與嘴線粗細畫；2048 尺寸。"""
    pad = int(sw * 2)
    if kind == "smile":
        W_, H_ = int(w + 2 * pad), int(w * 0.6 + 2 * pad)
        im = Image.new("RGBA", (W_ * 2, H_ * 2), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        pts = [(pad + w * i / 20, pad + w * 0.42 * math.sin(math.pi * i / 20)) for i in range(21)]
        pts = [(2 * a, 2 * b) for a, b in pts]
        d.line(pts, fill=(16, 4, 3, 255), width=int(2 * sw), joint="curve")
        for p in (pts[0], pts[-1]):
            d.ellipse([p[0] - sw, p[1] - sw, p[0] + sw, p[1] + sw], fill=(16, 4, 3, 255))
    else:  # ">" 形（右眼用鏡像）
        W_, H_ = int(w * 0.8 + 2 * pad), int(w * 0.9 + 2 * pad)
        im = Image.new("RGBA", (W_ * 2, H_ * 2), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        pts = [(pad, pad), (pad + w * 0.75, pad + w * 0.42), (pad, pad + w * 0.84)]
        pts = [(2 * a, 2 * b) for a, b in pts]
        d.line(pts, fill=(16, 4, 3, 255), width=int(2 * sw), joint="curve")
        for p in pts:
            d.ellipse([p[0] - sw, p[1] - sw, p[0] + sw, p[1] + sw], fill=(16, 4, 3, 255))
    im = im.resize((im.width // 2, im.height // 2), Image.LANCZOS)
    return im, (im.width / 2, im.height / 2)


# ---------------------------------------------------------------- 5. 組一個姿勢
FACE_YAW = 0.5            # 五官跟著轉的比例（<1：側面時臉不會擠到最邊、不會縮成一小塊）
FACE_FS = 0.45            # 透視壓縮強度（0＝不壓縮，1＝真實球面），減半保留五官大小
EAR_RHO = 0.65            # 耳朵所在那一圈（相對身體半寬）
EAR_LAM = math.radians(117)
EAR_SINK = 6.0            # 轉身後耳朵往頭裡收（512 單位），切口藏進毛裡
EAR_SINK_FAR = 18.0       # 遠側耳朵再多收一些：只露一點   # 耳朵在頭頂偏後方（|經度|>90°）
FOOT_LAM_F = math.radians(50)
FOOT_LAM_B = math.radians(130)
FEET_DROP = 7.0           # 身體底部描邊補齊後，腳要往下露出的量（512 單位），讓露出的腳掌跟原圖一樣多
DEPTH_RAISE = 7.0         # 遠側的腳往上縮（512 單位），表現俯視一點點的透視
FEET = {  # 名稱: (基本經度, 用哪一張腳的原圖)
    "FR": (-FOOT_LAM_F, "foot_l"), "FL": (FOOT_LAM_F, "foot_r"),
    "BR": (-FOOT_LAM_B, "foot_l"), "BL": (FOOT_LAM_B, "foot_r"),
}


@lru_cache(None)
def foot_home():
    P, g = layers(), geo()
    out = {}
    for nm in ("foot_l", "foot_r"):
        out[nm] = centroid(P[nm])
    u0 = abs(out["foot_r"][0] - out["foot_l"][0]) / 2 / g["RX"]
    rho = u0 / math.sin(FOOT_LAM_F)
    return out, rho


@lru_cache(None)
def ear_base(nm):
    """回傳 (基點 x, 沿法線高度 h, 基點切線角 rad)。"""
    g = geo()
    _, _, otop = orig_extents()
    ex, ey = g[nm]
    xs = np.arange(W)
    ok = ~np.isnan(otop)
    d = np.hypot(xs[ok] - ex, otop[ok] - ey)
    i = int(np.argmin(d))
    bx = float(xs[ok][i])
    h = float(d[i])
    x = int(bx)
    phi = math.atan2(otop[x + 2 * K] - otop[x - 2 * K], 4 * K)
    return bx, h, phi


@lru_cache(None)
def orig_extents():
    P = layers()
    bm = P["body"][..., 3] > 0.5
    xl, xr = _rows_extent(bm)
    top, _ = _cols_top(bm)
    return _smooth(xl, 3 * K), _smooth(xr, 3 * K), _smooth(top, 8 * K)


def compose(p: dict, stats: dict | None = None) -> Image.Image:
    """回傳 2048×2048 RGBA。p 的鍵見 POSES 的說明。"""
    P, g = layers(), geo()
    yaw = math.radians(p.get("yaw", 0.0))
    sx, syt, syb = p.get("sx", 1.0), p.get("sy_top", 1.0), p.get("sy_bot", 1.0)
    fr = float(np.clip((abs(p.get("yaw", 0.0)) - 25) / 45, 0, 1))
    body, fur, cx, cy2 = warp_body(sx, syt, syb, fade_r=fr if yaw > 0 else 0.0, fade_l=fr if yaw < 0 else 0.0)
    bm = body[..., 3] > 0.5
    xl, xr = _rows_extent(bm)
    xl, xr = _smooth(xl, 3 * K), _smooth(xr, 3 * K)
    top, _ = _cols_top(bm)
    top_s = _smooth(top, 8 * K)
    oxl, oxr, otop = orig_extents()
    by = float(g["y1"])
    canvas = Image.new("RGBA", (W, W), (0, 0, 0, 0))

    def ymap(y):
        sy = syt if y < g["cy"] else syb
        return cy2 + (y - g["cy"]) * sy

    def slope_deg(arr, x):
        x = int(np.clip(round(x), 2 * K, W - 2 * K - 1))
        d = arr[x + 2 * K] - arr[x - 2 * K]
        if np.isnan(d):
            return 0.0
        return math.degrees(math.atan2(d, 4 * K))

    # ---- 耳朵（永遠在身體後面），沿頭頂輪廓滑動
    ears = []
    for nm, sgn in (("ear_l", -1), ("ear_r", 1)):
        ex, ey = g[nm]
        lam = sgn * EAR_LAM
        eyaw = yaw * (0.55 + 0.45 * (abs(yaw) / (math.pi / 2)) ** 2)   # 3/4 時耳朵少轉一點，側面才完全轉到頭頂後方
        lam2 = lam + eyaw
        u = EAR_RHO * math.sin(lam2)
        u0 = EAR_RHO * math.sin(lam)
        # 原圖：找耳朵質心最近的頭頂輪廓點（基點）＋沿法線的高度 h；轉身後基點沿輪廓滑動、耳朵沿新法線立起
        bx, h, phi0 = ear_base(nm)
        bx2 = cx + (bx - g["cx"]) * sx + (u - u0) * g["RX"] * sx
        bx2 = float(np.clip(bx2, 0, W - 1))
        phi = math.radians(slope_deg(top_s, bx2))
        by2 = top_s[int(round(bx2))]
        # 增量寫法：不轉身、不變形時剛好回到原圖位置
        sink = (EAR_SINK * abs(math.sin(yaw)) + EAR_SINK_FAR * max(0.0, -math.cos(lam2)) * abs(math.sin(yaw))) * K
        hh = h * (syt ** 0.3) - sink
        x2 = ex + (bx2 - bx) + hh * math.sin(phi) - h * math.sin(phi0)
        y2 = ey + (by2 - otop[int(round(bx))]) - hh * math.cos(phi) + h * math.cos(phi0) + p.get("ear_dy", 0.0) * K
        rot = math.degrees(phi - phi0)
        rot += sgn * p.get("ear_out", 0.0) - p.get("ear_back", 0.0)
        esx = 0.86 + 0.14 * abs(math.cos(yaw))
        ears.append((math.cos(lam2), nm, x2, y2, rot, esx))
    for _, nm, x2, y2, rot, esx in sorted(ears):
        paste(canvas, nm, x2, y2, sx=esx, rot=rot)

    # ---- 腳（在身體後面；遠側先畫、往上縮）
    (fh, rho) = foot_home()
    z0 = math.cos(FOOT_LAM_F)
    feet = []
    gait = p.get("feet", {})
    for key, (lam, src) in FEET.items():
        lam2 = lam + yaw
        z = math.cos(lam2)
        x2 = cx + rho * math.sin(lam2) * g["RX"] * sx * p.get("spread", 1.0)
        fx, fy = fh[src]
        y2 = fy - (z0 - z) * DEPTH_RAISE * K * (0.6 + 0.4 * abs(math.sin(yaw)))
        dx, dy = gait.get(key, (0.0, 0.0))
        x2 += dx * K
        y2 -= dy * K
        y2 += (FEET_DROP + p.get("feet_dy", 0.0)) * K
        feet.append((z, key, src, x2, y2))
    tilt = p.get("tilt", 0.0)
    lift = p.get("lift", 0.0) * K
    if p.get("pivot", "ground") == "ground":
        pv = (cx + p.get("pivot_dx", 0.0) * K, g["ground"])
    else:
        pv = (cx, cy2)
    follow = p.get("feet_follow", True)
    fcan = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    for z, key, src, x2, y2 in sorted(feet):
        if key in p.get("hide_feet", ()):
            continue
        if not follow and tilt:
            # 腳留在地上：只把 x 跟著身體轉過去
            tr = math.radians(tilt)
            x2 = pv[0] + (x2 - pv[0]) * math.cos(tr) - (y2 - pv[1]) * math.sin(tr)
        paste(fcan, src, x2, y2, rot=p.get("foot_rot", {}).get(key, 0.0))
        if stats is not None:
            one = Image.new("RGBA", (W, W), (0, 0, 0, 0))
            paste(one, src, x2, y2, rot=p.get("foot_rot", {}).get(key, 0.0))
            stats.setdefault("_foot_layers", {})[key] = one

    # ---- 身體
    canvas.alpha_composite(to_img(body))

    # ---- 五官（貼在毛球表面，超出毛球的部分裁掉）
    clip = cv2.GaussianBlur(cv2.erode(fur, disk(2 * K).astype(np.uint8)), (0, 0), 1.0 * K)
    fyaw = yaw * FACE_YAW
    face_dy = p.get("face_dy", 0.0) * K
    eyes = p.get("eyes", "open")
    for nm in ("blush_l", "blush_r", "eye_l", "eye_r", "mouth"):
        fx, fy = g[nm]
        iy = int(round(fy))
        ocx = (oxl[iy] + oxr[iy]) / 2
        orx = (oxr[iy] - oxl[iy]) / 2
        u = np.clip((fx - ocx) / orx, -0.999, 0.999)
        lam = math.asin(u)
        lam2 = lam + fyaw
        lim = math.radians(62 if nm.startswith("eye") else 76)
        if abs(lam2) > lim:
            continue
        fade = float(np.clip((lim - abs(lam2)) / math.radians(6), 0, 1))
        y2 = ymap(fy) + face_dy
        iy2 = int(np.clip(round(y2), 0, W - 1))
        ncx = (xl[iy2] + xr[iy2]) / 2
        nrx = (xr[iy2] - xl[iy2]) / 2
        x2 = ncx + nrx * math.sin(lam2) * p.get("face_spread", 1.0)
        fs = (1 - FACE_FS + FACE_FS * math.cos(lam2)) / (1 - FACE_FS + FACE_FS * math.cos(lam))
        if nm.startswith("eye") and eyes != "open":
            sw = 5.5 * K
            w_ = 30 * K
            if eyes == "smile":
                im, anc = closed_eye("smile", w_, sw)
                paste(canvas, "", x2, y2 + 2 * K, sx=fs, img=im, anchor=anc, clip=clip, alpha=fade)
            else:
                im, anc = closed_eye("squeeze", w_ * 0.95, sw)
                flip = nm == "eye_r"
                paste(canvas, "", x2, y2, sx=fs, img=im, anchor=anc, clip=clip, alpha=fade, flip=flip)
            continue
        msx = p.get("mouth_sx", 1.0) if nm == "mouth" else 1.0
        paste(canvas, nm, x2, y2, sx=fs * msx, clip=clip, alpha=fade)

    # ---- 整體：傾斜＋離地（腳 follow=True 時跟著一起動，否則留在地上）
    def move(im, rot=True, up=True):
        if tilt and rot:
            im = im.convert("RGBa").rotate(-tilt, resample=Image.BICUBIC, center=pv).convert("RGBA")
        dxp = int(round(p.get("dx", 0.0) * K))
        dyp = -int(round(lift)) if up else 0
        if dxp or dyp:
            c2 = Image.new("RGBA", (W, W), (0, 0, 0, 0))
            c2.alpha_composite(im, (dxp, dyp)) if dxp >= 0 and dyp >= 0 else c2.paste(im, (dxp, dyp))
            im = c2
        return im
    canvas = move(canvas)
    fcan = move(fcan, rot=follow, up=follow)
    if stats is not None:
        upper_a = np.asarray(canvas.getchannel("A")).astype(np.float32) / 255
        stats["body_area"] = float((body[..., 3] > 0.5).sum()) / K / K
        stats["upper_area"] = float((upper_a > 0.5).sum()) / K / K
        fa = {}
        for key, one in stats.pop("_foot_layers", {}).items():
            one = move(one, rot=follow, up=follow)
            a1 = np.asarray(one.getchannel("A")).astype(np.float32) / 255
            fa[key] = {"full": float((a1 > 0.5).sum()) / K / K,
                       "visible": float(((a1 > 0.5) & (upper_a < 0.5)).sum()) / K / K}
        stats["feet"] = fa
    fcan.alpha_composite(canvas)
    return fcan


# ---------------------------------------------------------------- 6. 姿勢表（全部面向右或正面；面向左＝整張水平鏡像）
SIDE = 90.0
RUN_S, RUN_H, RUN_B = 14.0, 8.0, 3.0      # 奔跑：步幅、抬腳高度、身體起伏（512 單位）


def run_pose(phase: float) -> dict:
    """側面四腳奔跑（對角步態）。phase 0＝A（前後腳張開著地）、0.25＝B（騰空收腳）、0.5＝C（另一對張開）。
    身體只做 sx×sy＝1 的微擠壓（面積不變），不會忽胖忽瘦。"""
    f = 2 * math.pi * phase
    d1 = (RUN_S * math.cos(f), RUN_H * max(0.0, math.sin(f)))
    d2 = (RUN_S * math.cos(f + math.pi), RUN_H * max(0.0, math.sin(f + math.pi)))
    sxx = 1 + 0.018 * math.cos(2 * f)
    return dict(
        yaw=SIDE, sx=sxx, sy_top=1 / sxx, sy_bot=1 / sxx,
        lift=RUN_B * abs(math.sin(f)), tilt=2.0 + 1.2 * math.sin(2 * f), pivot="center",
        feet={"FR": d1, "BL": d1, "FL": d2, "BR": d2},
        ear_back=6 + 4 * math.sin(2 * f),
    )


POSES = {
    # 名稱: (中文名, 參數)
    "front_squash": ("正面壓縮", dict(sx=1.13, sy_top=1 / 1.13, sy_bot=1 / 1.13, spread=1.1, ear_out=6)),
    "front_stretch": ("正面拉伸", dict(sx=0.9, sy_top=1 / 0.9, sy_bot=1 / 0.9, spread=0.92, ear_dy=-3, ear_out=-4)),
    "front_jump": ("正面跳躍（空中）", dict(sx=0.96, sy_top=1 / 0.96, sy_bot=1 / 0.96, lift=70, spread=0.95,
                                       feet_dy=4, ear_dy=-5, ear_out=-6)),
    "front_land": ("正面落地壓縮", dict(sx=1.18, sy_top=1 / 1.18, sy_bot=1 / 1.18, spread=1.14, ear_out=12,
                                     eyes="squeeze")),
    "q34_r": ("右前 3/4 站姿", dict(yaw=40)),
    "side_r": ("右側面站姿", dict(yaw=SIDE)),
    "run_r_A": ("側面奔跑 A（張開著地）", run_pose(0.0)),
    "run_r_B": ("側面奔跑 B（騰空收腳）", run_pose(0.25)),
    "run_r_C": ("側面奔跑 C（另一對張開）", run_pose(0.5)),
    "side_takeoff_r": ("側面起跳", dict(yaw=SIDE, sx=0.9, sy_top=1 / 0.9, sy_bot=1 / 0.9, tilt=-9, pivot="ground",
                                     pivot_dx=-50, lift=4, feet_follow=False,
                                     feet={"FR": (6, 6), "FL": (6, 6), "BR": (-9, 0), "BL": (-9, 0)},
                                     ear_back=12)),
    "side_apex_r": ("側面空中最高點", dict(yaw=SIDE, lift=78, tilt=-2, pivot="center",
                                       feet={"FR": (-4, 3), "FL": (-4, 3), "BR": (4, 3), "BL": (4, 3)},
                                       ear_dy=-4, ear_back=-4)),
    "side_land_r": ("側面落地", dict(yaw=SIDE, sx=1.15, sy_top=1 / 1.15, sy_bot=1 / 1.15, tilt=4, pivot="ground",
                                   feet={"FR": (8, 0), "FL": (8, 0), "BR": (-7, 0), "BL": (-7, 0)},
                                   ear_back=-8, eyes="squeeze")),
    "lie_front": ("趴姿（正面）", dict(sx=1.2, sy_top=0.92, sy_bot=0.75, spread=1.12, feet_dy=-4, ear_out=10)),
    "lie_side_r": ("趴姿（側面）", dict(yaw=SIDE, sx=1.2, sy_top=0.92, sy_bot=0.75, feet_dy=-4, face_dy=4,
                                    feet={"FR": (7, 0), "FL": (7, 0), "BR": (-7, 0), "BL": (-7, 0)}, ear_back=8)),
    "sit_r": ("坐姿（四腳著地）", dict(yaw=SIDE, sx=0.95, sy_top=1.1, sy_bot=0.96, tilt=-8, pivot="ground", pivot_dx=-80,
                                   feet_follow=False, face_dy=-4,
                                   feet={"FR": (3, 0), "FL": (3, 0), "BR": (-2, 2), "BL": (-2, 2)}, ear_back=6)),
    "lay_r": ("躺姿（側面攤平）", dict(yaw=SIDE, sx=1.28, sy_top=0.9, sy_bot=0.66, face_dy=6, eyes="smile",
                                   feet={"FR": (14, 0), "FL": (14, 0), "BR": (-52, 2), "BL": (-46, 2)},
                                   feet_dy=-2, ear_back=14)),
    "sniff_r": ("低頭嗅地", dict(yaw=SIDE, sx=1.04, sy_top=0.94, sy_bot=1 / 1.04 / 0.94 * 0.94, tilt=6, pivot="ground",
                              pivot_dx=60, feet_follow=False, face_dy=16,
                              feet={"FR": (4, 0), "FL": (4, 0), "BR": (-3, 0), "BL": (-3, 0)}, ear_back=10)),
}
MIRROR = {  # 左版＝右版鏡像
    "q34_l": ("左前 3/4 站姿", "q34_r"), "side_l": ("左側面站姿", "side_r"),
    "run_l_A": ("側面奔跑 A（左）", "run_r_A"), "run_l_B": ("側面奔跑 B（左）", "run_r_B"),
    "run_l_C": ("側面奔跑 C（左）", "run_r_C"),
    "side_takeoff_l": ("側面起跳（左）", "side_takeoff_r"), "side_apex_l": ("側面空中最高點（左）", "side_apex_r"),
    "side_land_l": ("側面落地（左）", "side_land_r"), "lie_side_l": ("趴姿側面（左）", "lie_side_r"),
    "sit_l": ("坐姿（左）", "sit_r"), "lay_l": ("躺姿（左）", "lay_r"), "sniff_l": ("低頭嗅地（左）", "sniff_r"),
}


# ---------------------------------------------------------------- 7. 輸出、接觸表、奔跑預覽、自檢
FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
BGS = [("奶油白", (251, 244, 234)), ("淺藍", (227, 238, 249)), ("深色", (31, 35, 41))]


def ground512() -> float:
    return geo()["ground"] / K


def baseline_images():
    """接觸表左邊的兩張基準：default_idle（原圖去背）與第一版跳躍 GIF 第 9 格。"""
    d = down512(to_img(layers()["_orig"]))
    jg = Image.open(JUMP_GIF)
    jg.seek(8)
    j9 = jg.convert("RGBA")
    return [("基準：default_idle", d), ("基準：跳躍第 9 格", j9)]


def corner_opaque(im: Image.Image) -> bool:
    a = np.asarray(im.getchannel("A"))
    return bool(max(a[:8, :8].max(), a[:8, -8:].max(), a[-8:, :8].max(), a[-8:, -8:].max()) > 0)


def contact_sheet(items, path: Path, cols=8, cell=220):
    font = ImageFont.truetype(FONT, 15)
    tfont = ImageFont.truetype(FONT, 22)
    rows = (len(items) + cols - 1) // cols
    lab_h, band_t = 26, 40
    band_h = band_t + rows * (cell + lab_h)
    sheet = Image.new("RGB", (cols * cell, band_h * len(BGS)), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    gy = ground512() * cell / 512
    for bi, (bname, bg) in enumerate(BGS):
        y0 = bi * band_h
        fg = (235, 235, 235) if sum(bg) < 300 else (40, 40, 40)
        d.rectangle([0, y0, sheet.width, y0 + band_h], fill=bg)
        d.text((10, y0 + 8), f"比比基礎姿勢資產包 1012｜底色：{bname}｜紅線＝地面基準線 y={ground512():.0f}（512 座標）", font=tfont, fill=fg)
        for i, (label, im) in enumerate(items):
            cx, cy = (i % cols) * cell, y0 + band_t + (i // cols) * (cell + lab_h)
            t = im.resize((cell, cell), Image.LANCZOS)
            tile = Image.new("RGBA", (cell, cell), bg + (255,))
            tile.alpha_composite(t)
            sheet.paste(tile.convert("RGB"), (cx, cy))
            d.line([(cx + 4, cy + gy), (cx + cell - 4, cy + gy)], fill=(220, 60, 60), width=1)
            d.rectangle([cx, cy, cx + cell - 1, cy + cell + lab_h - 1], outline=(150, 150, 150))
            d.text((cx + 6, cy + cell + 4), label, font=font, fill=fg)
    sheet.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "docs/anim/bibi_basepose_1012"))
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    out = Path(a.out)
    (out / "png").mkdir(parents=True, exist_ok=True)
    report = {"ground_y_512": ground512(), "center_x_512": geo()["cx"] / K, "poses": {}}
    imgs = {}
    st0 = {}
    base = down512(to_img(layers()["_orig"]))
    imgs["front_stand"] = ("正面站姿（＝Default 原圖）", base)
    rebuild = compose({}, st0)
    imgs["front_stand_rebuild"] = ("正面站姿（分層重組版）", down512(rebuild))
    report["poses"]["front_stand_rebuild"] = st0
    names = [n for n in POSES if not a.only or n in a.only.split(",")]
    for n in names:
        zh, p = POSES[n]
        st = {}
        im = down512(compose(p, st))
        imgs[n] = (zh, im)
        report["poses"][n] = st
        print("完成", n, zh, flush=True)
    for n, (zh, srcn) in MIRROR.items():
        if srcn in imgs:
            imgs[n] = (zh, imgs[srcn][1].transpose(Image.FLIP_LEFT_RIGHT))
            report["poses"][n] = {"mirror_of": srcn}
    for n, (zh, im) in imgs.items():
        im.save(out / "png" / f"{n}.png")
        report["poses"].setdefault(n, {})
        report["poses"][n]["name_zh"] = zh
        report["poses"][n]["corner_opaque"] = corner_opaque(im)
    # 接觸表
    order = ["front_stand", "front_stand_rebuild", "front_squash", "front_stretch", "front_jump", "front_land",
             "q34_r", "q34_l", "side_r", "side_l", "run_r_A", "run_r_B", "run_r_C",
             "side_takeoff_r", "side_apex_r", "side_land_r", "lie_front", "lie_side_r", "sit_r", "lay_r", "sniff_r",
             "run_l_A", "run_l_B", "run_l_C", "side_takeoff_l", "side_apex_l", "side_land_l",
             "lie_side_l", "sit_l", "lay_l", "sniff_l"]
    items = baseline_images() + [(f"{imgs[n][0]}", imgs[n][1]) for n in order if n in imgs]
    contact_sheet(items, out / "contact_sheet.png")
    # 奔跑循環 12 格
    frames, rst = [], []
    for k in range(12):
        st = {}
        frames.append(down512(compose(run_pose(k / 12), st)))
        rst.append(st)
        print("奔跑格", k + 1, flush=True)
    frames[0].save(out / "run_cycle.webp", save_all=True, append_images=frames[1:], duration=60, loop=0,
                   lossless=False, quality=92, method=6)
    strip = Image.new("RGBA", (12 * 256, 256 * 2), (0, 0, 0, 0))
    for bi, bg in enumerate([(251, 244, 234), (31, 35, 41)]):
        for k, f in enumerate(frames):
            tile = Image.new("RGBA", (256, 256), bg + (255,))
            tile.alpha_composite(f.resize((256, 256), Image.LANCZOS))
            dd = ImageDraw.Draw(tile)
            dd.line([(0, ground512() / 2), (256, ground512() / 2)], fill=(220, 60, 60, 255))
            dd.text((6, 6), f"{k + 1:02d}", font=ImageFont.truetype(FONT, 16), fill=(200, 60, 60, 255))
            strip.alpha_composite(tile, (k * 256, bi * 256))
    strip.convert("RGB").save(out / "run_cycle_sheet.png")
    areas = [s["body_area"] for s in rst]
    ua = [s["upper_area"] for s in rst]
    m = sum(areas) / len(areas)
    mu = sum(ua) / len(ua)
    report["run_cycle"] = {
        "body_area": areas, "body_area_max_dev_pct": max(abs(x - m) / m * 100 for x in areas),
        "upper_area": ua, "upper_area_max_dev_pct": max(abs(x - mu) / mu * 100 for x in ua),
        "feet": [s["feet"] for s in rst],
        "corner_opaque": [corner_opaque(f) for f in frames],
    }
    (out / "check.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
    print("輸出完成", out)


if __name__ == "__main__":
    main()
