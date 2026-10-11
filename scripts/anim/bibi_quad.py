"""比比四腳骨架（10-12 Andy 最高原則：比比是天竺鼠，四隻腳著地，不站立、不用手）。

Andy 10-12 原話：「比比設定為天竺鼠，天竺鼠不是兩腳站立……所有互動畫面都需要符合真的天竺鼠他會有的，
不可以因為配合互動就改變身體原有設定」。

做法（建在 bibi_rig 的原版 Default 骨架上）
------------------------------------------
- 本體仍是 `default_idle_1011.webp` 的原像素（局部網格變形：耳朵繞耳根轉、毛邊飄、臉頰鼓）。
- 原圖底下那兩顆烤在像素裡的小腳**切掉**（`blank_nf`：切口補一道同粗細的深色描邊），
  四隻腳改成獨立的小圓腳（原版橘粉色＋深色粗描邊＋趾縫），畫在本體後面、從毛底下露出半顆：
  前腳兩顆、後腳兩顆，每隻都可以各自抬起／邁步／往外撐，地面影子跟著身體走。
- 五官各自擺位（左眼、右眼、嘴、左右腮紅），用來做正面、3/4、側面與「低頭」：
  側面只剩近側一隻眼、嘴在身體前下方；遠側五官水平壓窄。
- **最後一格回 Default** 時用 `feet="orig"`＋正面＋原圖五官 ＝ 跟原圖逐像素一樣。
- 不畫任何手掌／手臂。所有姿勢的檢查：`quad_selfcheck()` 會確認四隻腳都有畫、
  每隻腳的世界座標都在身體下半部（沒有「站起來」），沒有任何 paws。

座標同 bibi_rig：512 場景、腳底 y=482、中心 x=248；原圖座標 DEF_*。
"""
from __future__ import annotations

import math
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
import bibi_rig as R  # noqa: E402

S = R.S
W = R.SIZE * S
INK = R.DEF_INK
RUST, RUST_D = R.DEF_RUST, R.DEF_RUST_D
GROUND = R.FOOT_Y

# 原圖兩顆腳的範圍（x0, x1, 左緣切口 y, 右緣切口 y）
_FOOT_CUTS = [(146, 216, 452, 468), (292, 366, 468, 452)]

# ---------------------------------------------------------------- 本體：切掉原圖的兩顆腳


@lru_cache(None)
def blank_nf() -> Image.Image:
    """無五官、無腳的本體（S 倍 RGBA）。切口沿一條略往下鼓的弧線，再補一道 11px 深色描邊（跟原圖描邊同粗）。"""
    A = R.default_assets()
    src = A["blank"].copy()
    a = np.asarray(src.getchannel("A")).astype(np.float32)
    H = a.shape[0]
    yy, xx = np.mgrid[0:H, 0:H] / S
    cut = np.zeros_like(a, dtype=bool)
    paths = []
    for x0, x1, ya, yb in _FOOT_CUTS:
        t = (xx - x0) / (x1 - x0)
        ycut = ya + (yb - ya) * t - 4 * np.sin(np.clip(t, 0, 1) * math.pi)
        cut |= (t >= 0) & (t <= 1) & (yy > ycut)
        pts = []
        for i in range(25):
            tt = i / 24
            y = ya + (yb - ya) * tt - 4 * math.sin(tt * math.pi) - 1.5 * math.sin(tt * math.pi * 3)  # 小毛邊起伏
            pts.append(f"{x0 + (x1 - x0) * tt:.1f},{y:.1f}")
        paths.append(pts)
    a[cut] = 0
    src.putalpha(Image.fromarray(a.astype(np.uint8)))
    ink = "".join(f'<polyline points="{" ".join(p)}" fill="none" stroke="{INK}" stroke-width="11" '
                  f'stroke-linecap="round" stroke-linejoin="round"/>' for p in paths)
    src.alpha_composite(R.svg_layer(ink))
    return src


def body_layer(p, feet_orig: bool) -> Image.Image:
    """依姿勢畫本體（原圖像素網格變形）。feet_orig=True 用原圖兩顆腳。"""
    A = R.default_assets()
    if feet_orig:
        return R.def_body_layer(p)
    keep = A["blank"]
    A["blank"] = blank_nf()
    try:
        return R.def_body_layer(p)
    finally:
        A["blank"] = keep


# ---------------------------------------------------------------- 腳


def foot_svg(x, y, rot=0.0, s=1.0, far=False, sole=0.0) -> str:
    """一隻小圓腳（原版橘粉＋深色粗描邊＋前緣兩道趾縫）。(x,y)＝腳的中心；rot 度；far＝遠側壓暗。
    sole>0：抬腳時露出一點腳底肉球（淡粉）。"""
    fill = RUST_D if far else RUST
    sw = 9.5
    body = (f'<path d="M -27 -6 C -29 -20 -14 -22 0 -22 C 14 -22 29 -20 27 -6 C 26 8 15 14 0 14 C -15 14 -26 8 -27 -6 Z" '
            f'fill="{fill}" stroke="{INK}" stroke-width="{sw}" stroke-linejoin="round"/>')
    toes = (f'<path d="M -8 14 L -8 6 M 8 14 L 8 6" stroke="{INK}" stroke-width="4.6" stroke-linecap="round"/>')
    pad = ""
    if sole > 0.05:
        pad = (f'<ellipse cx="0" cy="2" rx="{13*sole:.1f}" ry="{7*sole:.1f}" fill="#FFC9B8"/>')
    return (f'<g transform="translate({x:.1f},{y:.1f}) rotate({rot:.1f}) scale({s:.3f})">{body}{pad}{toes}</g>')


# 四隻腳的停放點（原圖座標，正面）：前腳＝原圖那兩顆的位置；後腳＝在外側後方，只露出一點
FEET_FRONT = {"fl": (181.0, 466.0, 1.0), "fr": (327.0, 466.0, 1.0),
              "bl": (128.0, 458.0, 0.86), "br": (380.0, 458.0, 0.86)}
# 3/4 面向左：前腳在左前（近側大、遠側小一點）、後腳在右後
FEET_Q3 = {"fl": (150.0, 468.0, 1.0), "fr": (226.0, 462.0, 0.9),
           "bl": (318.0, 468.0, 1.0), "br": (378.0, 458.0, 0.86)}
# 側面面向左：近側前後腳在前、遠側前後腳往後一點、高一點、暗一點
FEET_SIDE = {"fl": (128.0, 468.0, 1.0), "fr": (168.0, 460.0, 0.9),
             "bl": (348.0, 468.0, 1.0), "br": (388.0, 460.0, 0.9)}
FEET_BACK = {"bl": (181.0, 466.0, 1.0), "br": (327.0, 466.0, 1.0),
             "fl": (128.0, 458.0, 0.86), "fr": (380.0, 458.0, 0.86)}
FAR_FEET = {"front": ("bl", "br"), "q3": ("fr", "br"), "side": ("fr", "br"), "back": ("fl", "fr")}


def feet_rest(view):
    return {"front": FEET_FRONT, "q3": FEET_Q3, "side": FEET_SIDE, "back": FEET_BACK}[view]


# ---------------------------------------------------------------- 五官擺位
# (dx, dy, kx, alpha)：以該部件中心為軸水平壓 kx，再平移 dx,dy（原圖座標）
FACE_FRONT = dict(eye_l=(0, 0, 1, 1), eye_r=(0, 0, 1, 1), mouth=(0, 0, 1, 1), blush_l=(0, 0, 1, 1), blush_r=(0, 0, 1, 1))
FACE_Q3 = dict(eye_l=(-50, 4, 0.92, 1), eye_r=(-72, 4, 0.74, 1), mouth=(-60, 6, 0.9, 1),
               blush_l=(-26, 6, 0.85, 1), blush_r=(-74, 6, 0.72, 0.85))
FACE_SIDE = dict(eye_l=(-36, 4, 0.9, 1), eye_r=(-150, 6, 0.4, 0), mouth=(-112, 24, 0.8, 1),
                 blush_l=(-2, 14, 0.85, 1), blush_r=(-120, 10, 0.4, 0))
# 各視角的耳朵（3/4：兩耳往前挪、遠側耳小一點；側面：近側耳挪到眼睛後上方、遠側耳收進毛裡）
EARS = {"front": {}, "q3": dict(ear_tx=-16, ear_sc_r=0.86),
        "side": dict(ear_tx_l=10, ear_sc_r=0.72, ear2=18)}


FACE_BACK = {k: (0, 0, 1, 0) for k in FACE_FRONT}


def face_layout(view):
    return {"front": FACE_FRONT, "q3": FACE_Q3, "side": FACE_SIDE, "back": FACE_BACK}[view]


_CENT = {"eye_l": R.DEF_EYE_L, "eye_r": R.DEF_EYE_R, "mouth": R.DEF_MOUTH,
         "blush_l": R.DEF_BLUSH_L, "blush_r": R.DEF_BLUSH_R}

QDEF = dict(R.DEFAULT, view="front", eye="default", mouth="default", feet=None, legs=None,
            blush=1.0, look=(0.0, 0.0), ear_tx=0.0, ear_sc_l=1.0, ear_sc_r=1.0, face=None,
            tear=0.0, rim=0.0, mouth_s=1.0, eye_s=1.0)


def _feat(layer, p, c, spec, extra=(0.0, 0.0)):
    """把一層原圖座標的五官（S 倍）以中心 c 水平壓 kx、平移，再跟著本體仿射。"""
    dx, dy, kx, al = spec
    dx += extra[0]
    dy += extra[1]
    M = R.mat((c[0] + dx) * S, (c[1] + dy) * S, 0, kx, 1.0, 0, c[0] * S, c[1] * S)
    im = R.warp_affine(layer, M)
    if al < 0.99:
        im.putalpha(im.getchannel("A").point(lambda v: int(v * al)))
    return R.def_layer_affine(im, p)


def _split_blush():
    A = R.default_assets()
    a0 = np.asarray(A["blush"].getchannel("A"))
    half = np.zeros_like(a0)
    half[:, : int(R.DEF_FOOT[0] * S)] = 255
    l_ = A["blush"].copy()
    l_.putalpha(Image.fromarray(np.minimum(a0, half)))
    r_ = A["blush"].copy()
    r_.putalpha(Image.fromarray(np.minimum(a0, 255 - half)))
    return l_, r_


_BL = None


def feat_world(p, key, extra=(0.0, 0.0)):
    """某個五官在世界（512）的位置。"""
    lay = p.get("face") or face_layout(p["view"])
    dx, dy, _, _ = lay[key]
    c = _CENT[key]
    lu, lv = p["look"]
    return R.def_pt(p, c[0] + dx + lu + extra[0], c[1] + dy + lv + extra[1])


# ---------------------------------------------------------------- 合成


def compose(p: dict, props_back=None, props_mid=None, props_front=None, fx=None, fx_back=None, shadow=True,
            overlay_fn=None):
    """四腳比比一格（S 倍畫布, boxes）。p 的鍵見 QDEF：
    view＝front／q3／side；feet＝'orig'（原圖兩腳＝Default）或 None（四隻獨立小腳）；
    legs＝{fl,fr,bl,br: (dx, dy, rot, sole)} 各腳相對停放點的位移（世界單位）；
    eye／mouth＝'default'（原圖像素）或 bibi_rig 的補畫名稱；face＝自訂五官擺位；look＝五官整體再平移（原圖座標）。"""
    global _BL
    p = {**QDEF, **EARS.get(p.get("view", "front"), {}), **p}
    if "plant" not in p:
        p["plant"] = p["y"] > GROUND - 6
    if p.get("pivot") and (abs(p["rot"]) > 0.01 or abs(p["sy"] - 1) > 0.001 or abs(p["sx"] - 1) > 0.001):
        # 以原圖某點（例如前腳）為軸傾斜／擠壓：算出那點在「沒傾斜」時的位置，整隻平移回去
        px_, py_ = p["pivot"]
        a = R.def_pt(dict(p, rot=0.0, sx=1.0, sy=1.0, shear=0.0), px_, py_)
        b = R.def_pt(p, px_, py_)
        p["x"] += a[0] - b[0]
        p["y"] += a[1] - b[1]
    can = Image.new("RGBA", (W, W))
    boxes, masks = {}, {}
    A = R.default_assets()

    def put(lst, tag):
        for i, it in enumerate(lst or []):
            if isinstance(it, str):
                lay = R.svg_layer(it)
            elif isinstance(it, Image.Image):
                lay = it
            else:
                im, x, y, r, anc = it
                lay = Image.new("RGBA", (W, W))
                R.place(lay, im, x, y, r, anchor=anc)
            bb = lay.getchannel("A").getbbox()
            if bb:
                boxes[f"{tag}{i}"] = bb
                masks[f"{tag}{i}"] = lay.getchannel("A")
            can.alpha_composite(lay)

    lift = max(0.0, GROUND - p["y"])
    if shadow:
        k = max(0.35, 1 - lift / 160)
        rx = 152 * k * min(1.25, p["sx"]) * p.get("shadow_k", 1.0)
        can.alpha_composite(R.svg_layer(
            f'<ellipse cx="{p["x"] + 2 + p.get("shadow_dx", 0):.1f}" cy="{GROUND - 1:.1f}" rx="{rx:.1f}" '
            f'ry="{12 * k:.1f}" fill="rgb(110,80,60)" fill-opacity="{0.27 * (0.45 + 0.55 * k):.2f}"/>'))
    put(fx_back, "fxB")
    put(props_back, "propB")

    feet_orig = p["feet"] == "orig"
    feet_pos = {}
    if not feet_orig:
        rest = feet_rest(p["view"])
        legs = p["legs"] or {}
        far = FAR_FEET[p["view"]]
        order = sorted(rest, key=lambda k_: (k_ not in far, rest[k_][1]))   # 遠側先畫
        sv = ""
        for key in order:
            ux, uy, sc = rest[key]
            X, Y = R.def_pt(p, ux, uy)
            dx, dy, rot, sole = (tuple(legs.get(key, (0, 0, 0, 0))) + (0, 0, 0, 0))[:4]
            # 腳跟著身體走，但壓扁時腳不跟著變形（腳是硬的小圓），只取位置
            if p["plant"] and key not in p.get("unplant", ()):
                Y = GROUND - 18 + dy        # 著地：腳底貼地（dy<0＝這隻腳正抬起來邁步）
                X = X + dx
            else:
                X, Y = X + dx, Y + dy
            feet_pos[key] = (X, Y)
            sv += foot_svg(X, Y, rot + p["rot"] * 0.6, sc * p.get("foot_s", 1.0), far=key in far, sole=sole)
        can.alpha_composite(R.svg_layer(sv))
    boxes["__feet"] = feet_pos

    body = body_layer(p, feet_orig)
    boxes["body"] = body.getchannel("A").getbbox()
    masks["body"] = body.getchannel("A")
    can.alpha_composite(body)
    put(props_mid, "propM")
    if p["view"] == "back":          # 背面：沒有五官，中下方一小團圓尾巴毛
        tx_, ty_ = R.def_pt(p, R.DEF_FOOT[0], 404)
        R.place(can, R.tail_img(1.25), tx_ + p["tail"][0], ty_ + p["tail"][1], p["tail"][2] + p["rot"], anchor=(0.5, 0.5))

    lay = p["face"] or face_layout(p["view"])
    look = p["look"]
    inner = np.asarray(body.getchannel("A").filter(ImageFilter.MinFilter(31))).astype(np.float32) / 255
    # 腮紅
    if p["blush"] > 0.01:
        if _BL is None:
            _BL = _split_blush()
        bl = Image.new("RGBA", (W, W))
        for key, im in (("blush_l", _BL[0]), ("blush_r", _BL[1])):
            spec = lay[key]
            if spec[3] <= 0.01:
                continue
            bl.alpha_composite(_feat(im, p, _CENT[key], spec, look))
        if p["blush"] < 0.99:
            bl.putalpha(bl.getchannel("A").point(lambda v: int(v * p["blush"])))
        bl.putalpha(Image.fromarray((np.asarray(bl.getchannel("A")) * inner).astype(np.uint8)))
        can.alpha_composite(bl)
        if p["blush"] > 1.05:
            extra = ""
            for key in ("blush_l", "blush_r"):
                if lay[key][3] <= 0.01:
                    continue
                X, Y = feat_world(p, key)
                extra += (f'<ellipse cx="{X:.1f}" cy="{Y:.1f}" rx="{30 * p["sx"] * lay[key][2]:.1f}" ry="{26 * p["sy"]:.1f}" '
                          f'fill="#F4735A" fill-opacity="{min(0.42, 0.35 * (p["blush"] - 1)):.2f}"/>')
            can.alpha_composite(R.svg_layer(extra))

    face = Image.new("RGBA", (W, W))
    eye = p["eye"]
    if eye == "default" and p["eye_open"] > 0.5:
        for key in ("eye_l", "eye_r"):
            if lay[key][3] > 0.01:
                face.alpha_composite(_feat(A[key], p, _CENT[key], lay[key], look))
    else:
        kind = "closed" if (eye == "default" or p["eye_open"] <= 0.5) else eye
        sv = ""
        for key, side in (("eye_l", "l"), ("eye_r", "r")):
            if lay[key][3] <= 0.01:
                continue
            X, Y = feat_world(p, key)
            kk = kind
            if kind == "squeeze":
                kk = "squeeze_l" if side == "l" else "squeeze_r"
            sv += eye_kind_svg(kk, X, Y, side, p, lay[key][2])
        face.alpha_composite(R.svg_layer(sv))
    m = p["mouth"]
    if lay["mouth"][3] > 0.01 and m != "none":
        if m == "default":
            face.alpha_composite(_feat(A["mouth"], p, _CENT["mouth"], lay["mouth"], look))
        else:
            X, Y = feat_world(p, "mouth", (0, -6))
            face.alpha_composite(R.svg_layer(mouth_kind_svg(m, X, Y, p["mouth_s"])))
    fa = Image.fromarray(np.asarray(body.getchannel("A"))).filter(ImageFilter.MinFilter(17))
    face.putalpha(Image.fromarray(np.minimum(np.asarray(face.getchannel("A")), np.asarray(fa))))
    bb = face.getchannel("A").getbbox()
    if bb:
        boxes["face"] = bb
        masks["face"] = face.getchannel("A")
    can.alpha_composite(face)
    # 淚痕、淚珠（畫在臉上、身體裡）
    if p["tear"] > 0.01 or p["rim"] > 0.01:
        can.alpha_composite(R.svg_layer(tears_svg(p, lay)))

    if overlay_fn is not None:       # 例如小被子：照本體實際輪廓算出來，蓋在身上（不蓋臉）
        ov = overlay_fn(p, np.asarray(body.getchannel("A")))
        if ov is not None:
            bb = ov.getchannel("A").getbbox()
            if bb:
                boxes["propF_ov"] = bb
                masks["propF_ov"] = ov.getchannel("A")
            can.alpha_composite(ov)
    put(props_front, "propF")
    for i, piece in enumerate([fx] if isinstance(fx, str) else (fx or [])):
        if not piece:
            continue
        fl = R.svg_layer(piece)
        bb = fl.getchannel("A").getbbox()
        if bb:
            boxes[f"fx{i}"] = bb
            masks[f"fx{i}"] = fl.getchannel("A")
        can.alpha_composite(fl)

    M = np.eye(3)
    if abs(p["grot"]) > 0.01 or abs(p["gx"]) > 0.01 or abs(p["gy"]) > 0.01:
        M = R.mat((p["gpx"] + p["gx"]) * S, (p["gpy"] + p["gy"]) * S, p["grot"], 1, 1, 0, p["gpx"] * S, p["gpy"] * S)
    if p["facing"] == "right":
        M = np.array([[-1, 0, 2 * R.CX * S], [0, 1, 0], [0, 0, 1.0]]) @ M
    if not np.allclose(M, np.eye(3)):
        can = R.warp_affine(can, M, can.size)
        fp = boxes.pop("__feet")
        boxes = {k: R._tf_box(v, M) for k, v in boxes.items() if v}
        Mw = np.diag([1 / S, 1 / S, 1]) @ M @ np.diag([S, S, 1])
        boxes["__feet"] = {k: R.apply(Mw, *v) for k, v in fp.items()}
        inv = np.linalg.inv(M)
        data = (inv[0, 0], inv[0, 1], inv[0, 2], inv[1, 0], inv[1, 1], inv[1, 2])
        masks = {k: mm.transform(can.size, Image.AFFINE, data, resample=Image.BILINEAR) for k, mm in masks.items()}
    boxes["__masks"] = {k: np.asarray(mm.reduce(4)) > 40 for k, mm in masks.items()}
    return can, boxes


# ---------------------------------------------------------------- 表情補畫
TEAR_FILL, TEAR_INK = R.TEAR_FILL, R.TEAR_INK


def eye_kind_svg(kind, X, Y, side, p, kx=1.0) -> str:
    """補畫眼：沿用 bibi_rig.def_eye_svg，另加 teary_big（淚汪汪：大黑眼＋兩顆高光＋下半含一大汪淚，
    照 cry_ref_1012）與 sleep（︶ 睡著）、dot（原版大小的黑點，給側面用）。"""
    if kind == "teary_big":
        k = 1.9 * p.get("eye_s", 1.0)
        rx, ry = 9.4 * k * kx, 10.6 * k
        wob = p.get("wobble", 0.0)
        return (f'<ellipse cx="{X:.1f}" cy="{Y:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{INK}"/>'
                # 下半含淚：藍色淚池，上緣波動
                f'<path d="M {X-rx*0.92:.1f} {Y+ry*0.12:.1f} Q {X-rx*0.4:.1f} {Y+ry*(0.0+0.08*wob):.1f} {X:.1f} {Y+ry*0.08:.1f} '
                f'Q {X+rx*0.45:.1f} {Y+ry*(0.16-0.08*wob):.1f} {X+rx*0.92:.1f} {Y+ry*0.12:.1f} '
                f'Q {X+rx*0.9:.1f} {Y+ry*1.02:.1f} {X:.1f} {Y+ry*1.12:.1f} Q {X-rx*0.9:.1f} {Y+ry*1.02:.1f} {X-rx*0.92:.1f} {Y+ry*0.12:.1f} Z" '
                f'fill="#7CC4F0" fill-opacity="0.92" stroke="{TEAR_INK}" stroke-width="3.2"/>'
                f'<circle cx="{X-rx*0.36:.1f}" cy="{Y-ry*0.38:.1f}" r="{rx*0.4:.1f}" fill="#fff"/>'
                f'<circle cx="{X+rx*0.38:.1f}" cy="{Y-ry*0.05:.1f}" r="{rx*0.17:.1f}" fill="#fff"/>'
                f'<ellipse cx="{X-rx*0.2:.1f}" cy="{Y+ry*0.62:.1f}" rx="{rx*0.32:.1f}" ry="{ry*0.12:.1f}" fill="#fff" fill-opacity="0.85"/>')
    if kind == "sleep":
        k = 1.9
        return (f'<path d="M {X-9*k*kx:.1f} {Y-1*k:.1f} Q {X:.1f} {Y+5*k:.1f} {X+9*k*kx:.1f} {Y-1*k:.1f}" fill="none" '
                f'stroke="{INK}" stroke-width="6.2" stroke-linecap="round"/>')
    if kind == "dot":
        k = 1.9
        return (f'<ellipse cx="{X:.1f}" cy="{Y:.1f}" rx="{6.6*k*kx:.1f}" ry="{7.4*k:.1f}" fill="{INK}"/>'
                f'<circle cx="{X-2.4*k*kx:.1f}" cy="{Y-2.8*k:.1f}" r="{2.2*k:.1f}" fill="#fff"/>')
    if kind == "star_big":
        return R.star_svg(X, Y, 25, 0, "#FFD25A").replace('stroke-width="3.5"', 'stroke-width="5.5"') + \
            f'<circle cx="{X-6:.1f}" cy="{Y-6:.1f}" r="3.2" fill="#fff"/>'
    return R.def_eye_svg(kind, X, Y, side=side)


def mouth_kind_svg(kind, X, Y, s=1.0) -> str:
    """補畫嘴：沿用 def_mouth_svg；另加 pout（淚汪汪的小撇嘴）、nibble_a/b/c（啃草：門牙／半開／閉嘴鼓）。"""
    k = 2.3 * s
    if kind == "pout":     # 小而撇：短倒弧＋右邊嘴角多一點往下
        return (f'<path d="M {X-7*k:.1f} {Y+4*k:.1f} Q {X-1*k:.1f} {Y-2.6*k:.1f} {X+7*k:.1f} {Y+5*k:.1f}" fill="none" '
                f'stroke="{INK}" stroke-width="{6*s:.1f}" stroke-linecap="round"/>')
    if kind == "wobble_small":   # 抽噎：小波浪嘴
        return (f'<path d="M {X-8*k:.1f} {Y+2*k:.1f} q {2*k:.1f} {-3*k:.1f} {4*k:.1f} 0 t {4*k:.1f} 0 t {4*k:.1f} 0 t {4*k:.1f} 0" '
                f'fill="none" stroke="{INK}" stroke-width="{6*s:.1f}" stroke-linecap="round" stroke-linejoin="round"/>')
    if kind == "nibble_a":   # 張嘴露兩顆門牙
        return (f'<path d="M {X-8*k:.1f} {Y-3*k:.1f} C {X-8*k:.1f} {Y+9*k:.1f} {X+8*k:.1f} {Y+9*k:.1f} {X+8*k:.1f} {Y-3*k:.1f} Z" '
                f'fill="#6E1E16" stroke="{INK}" stroke-width="{6*s:.1f}" stroke-linejoin="round"/>'
                f'<path d="M {X-4.6*k:.1f} {Y-3*k:.1f} h {9.2*k:.1f} v {4.2*k:.1f} h {-9.2*k:.1f} Z M {X:.1f} {Y-3*k:.1f} v {4.2*k:.1f}" '
                f'fill="#fff" stroke="{INK}" stroke-width="{2.6*s:.1f}" stroke-linejoin="round"/>')
    if kind == "nibble_b":   # 半開
        return (f'<path d="M {X-7*k:.1f} {Y-1*k:.1f} C {X-6*k:.1f} {Y+5*k:.1f} {X+6*k:.1f} {Y+5*k:.1f} {X+7*k:.1f} {Y-1*k:.1f} Z" '
                f'fill="#6E1E16" stroke="{INK}" stroke-width="{6*s:.1f}" stroke-linejoin="round"/>'
                f'<path d="M {X-3.6*k:.1f} {Y-1*k:.1f} h {7.2*k:.1f} v {2.8*k:.1f} h {-7.2*k:.1f} Z" fill="#fff" '
                f'stroke="{INK}" stroke-width="{2.2*s:.1f}"/>')
    if kind == "nibble_c":   # 閉嘴嚼（ω 偏一邊）
        return (f'<path d="M {X-9*k:.1f} {Y-2*k:.1f} Q {X-5*k:.1f} {Y+5*k:.1f} {X-0.5*k:.1f} {Y-0.5*k:.1f} Q {X+4*k:.1f} {Y+4*k:.1f} '
                f'{X+8*k:.1f} {Y-3*k:.1f}" fill="none" stroke="{INK}" stroke-width="{6*s:.1f}" stroke-linecap="round" stroke-linejoin="round"/>')
    if kind == "nibble_d":   # 閉嘴嚼（ω 偏另一邊）
        return (f'<path d="M {X-8*k:.1f} {Y-3*k:.1f} Q {X-4*k:.1f} {Y+4*k:.1f} {X+0.5*k:.1f} {Y-0.5*k:.1f} Q {X+5*k:.1f} {Y+5*k:.1f} '
                f'{X+9*k:.1f} {Y-2*k:.1f}" fill="none" stroke="{INK}" stroke-width="{6*s:.1f}" stroke-linecap="round" stroke-linejoin="round"/>')
    return R.def_mouth_svg(kind, X, Y, s)


def tears_svg(p, lay) -> str:
    """淚汪汪（cry_ref_1012）：眼眶下緣一點紅（rim）＋淚痕沿臉頰往下（tear＝長度 0～1，tear_ph＝淚珠滑到哪）。"""
    out = ""
    for key, sg in (("eye_l", -1), ("eye_r", 1)):
        if lay[key][3] <= 0.01:
            continue
        X, Y = feat_world(p, key)
        k = 1.9 * p.get("eye_s", 1.0)
        rx, ry = 9.4 * k * lay[key][2], 10.6 * k
        if p["rim"] > 0.01:
            out += (f'<path d="M {X-rx*1.05:.1f} {Y+ry*0.7:.1f} Q {X:.1f} {Y+ry*1.55:.1f} {X+rx*1.05:.1f} {Y+ry*0.7:.1f}" fill="none" '
                    f'stroke="#F06A5A" stroke-opacity="{0.55*p["rim"]:.2f}" stroke-width="5" stroke-linecap="round"/>')
        t = p["tear"]
        if t > 0.01:
            # 淚痕（cry_ref：一條寬寬的淡藍淚流從眼睛下緣沿臉頰流下來）
            x0, y0 = X + sg * rx * 0.35, Y + ry * 0.85
            L = 62 * t
            x1, y1 = x0 + sg * 6, y0 + L
            out += (f'<path d="M {x0-12:.1f} {y0:.1f} C {x0-12:.1f} {y0+L*0.4:.1f} {x1-9:.1f} {y1-L*0.3:.1f} {x1-8:.1f} {y1:.1f} '
                    f'Q {x1:.1f} {y1+9:.1f} {x1+8:.1f} {y1:.1f} C {x1+9:.1f} {y1-L*0.3:.1f} {x0+12:.1f} {y0+L*0.4:.1f} {x0+12:.1f} {y0:.1f} Z" '
                    f'fill="#A9DDF8" fill-opacity="0.95" stroke="{TEAR_INK}" stroke-width="3" stroke-linejoin="round"/>'
                    f'<path d="M {x0-3:.1f} {y0+6:.1f} C {x0-3:.1f} {y0+L*0.4:.1f} {x1-2:.1f} {y1-L*0.4:.1f} {x1-2:.1f} {y1-8:.1f}" '
                    f'fill="none" stroke="#fff" stroke-opacity="0.8" stroke-width="3" stroke-linecap="round"/>')
            ph = p.get("tear_ph", -1.0)
            if ph >= 0:     # 一顆淚珠沿淚痕滑下、滑到底掉出去
                ty = y0 + 10 + (L + 18) * ph
                out += R.tear_bead_svg(x0 + sg * 6 * min(1.0, ph), ty, 9.0)
    return out


# ---------------------------------------------------------------- 自檢


def quad_selfcheck(p: dict, boxes: dict) -> list[str]:
    """四腳著地自檢：沒有 paws；四隻腳都畫了（或 Default 原圖兩腳）；腳都在身體下半部；
    著地格（y≈地面）四腳底部都貼地（±8），騰空格（y<地面-10）允許腳一起離地。"""
    bad = []
    if p.get("paws") or p.get("paws_world"):
        bad.append("有手掌（paws）")
    fp = boxes.get("__feet") or {}
    if p.get("feet") == "orig":
        return bad
    if len(fp) != 4:
        bad.append(f"腳只有 {len(fp)} 隻")
        return bad
    bb = boxes.get("body")
    if bb:
        y0, y1 = bb[1] / S, bb[3] / S
        for k, (x, y) in fp.items():
            if y < y0 + (y1 - y0) * 0.55:
                bad.append(f"{k} 腳在身體上半部（像站起來／舉手）")
    airborne = p.get("y", GROUND) < GROUND - 10 or p.get("air", False)
    if not airborne and not p.get("lying", False):
        down = [k for k, (x, y) in fp.items() if abs((y + 18) - GROUND) <= 6]
        if len(down) < 2:
            bad.append(f"著地格只有 {len(down)} 隻腳貼地")
    return bad


# ---------------------------------------------------------------- 小被子（睡覺：照 sleep_ref_1012 的藍色小被子）
def blanket_overlay(front=0.34, lean=0.16, pad=9.0, wave=0.0, lift=0.0, alpha=1.0, dx=0.0, rot=0.0):
    """回傳 overlay_fn：被子＝本體輪廓往外 pad（世界單位）、只蓋 x 大於前緣 xcut(y) 的部分（臉在前面露出來）。
    front＝前緣在身寬的比例、lean＝前緣下方往後斜；wave＝前緣波動相位（呼吸時布會動）；
    lift／dx／rot：被子被掀開（叫醒時往上飛走）。"""
    def fn(p, A):
        Sx = S
        Mb = A > 128
        ys, xs = np.nonzero(Mb)
        if not len(ys):
            return None
        x0, x1, yt, yb = xs.min(), xs.max(), ys.min(), ys.max()
        im = Image.fromarray((Mb * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(int(pad * Sx) * 2 + 1))
        R_ = np.asarray(im) > 128
        H = R_.shape[0]
        yy, xx = np.mgrid[0:H, 0:H]
        t = np.clip((yy - yt) / max(1, yb - yt), 0, 1)
        xc = x0 + (x1 - x0) * (front + lean * t) + 7 * Sx * np.sin(t * 7 + wave)
        R_ &= (xx > xc) & (yy < (GROUND - 1) * Sx)
        sm = Image.fromarray((R_ * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3 * Sx))
        R_ = np.asarray(sm) > 128
        ink = np.asarray(Image.fromarray((R_ * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(19))) > 128
        rgb = np.zeros((H, H, 4), np.uint8)
        rgb[ink] = (0x1A, 0x14, 0x30, 255)
        base = np.array([0x5C, 0x8C, 0xE6], np.float32)
        hi = np.array([0x8F, 0xB7, 0xF6], np.float32)
        k = np.clip(1 - (yy - yt) / max(1, (yb - yt) * 0.55), 0, 1)[..., None] * 0.85
        col = base * (1 - k) + hi * k
        rgb[R_, :3] = col[R_].astype(np.uint8)
        rgb[R_, 3] = 255
        lay = Image.fromarray(rgb, "RGBA")
        # 布紋：兩道摺痕（從頂部往後下方）＋前緣反摺的布邊
        sv = ""
        X0, X1, YT, YB = x0 / Sx, x1 / Sx, yt / Sx, yb / Sx
        w_, h_ = X1 - X0, YB - YT
        for f, g in ((0.62, 0.0), (0.8, 0.12)):
            ax, ay = X0 + w_ * f, YT + h_ * (0.18 + g)
            bx, by = X0 + w_ * (f + 0.1), YB - 8
            sv += (f'<path d="M {ax:.1f} {ay:.1f} Q {ax + w_*0.02:.1f} {(ay+by)/2:.1f} {bx:.1f} {by:.1f}" fill="none" '
                   f'stroke="#2F5AA8" stroke-width="5" stroke-linecap="round"/>')
        fold = Image.new("RGBA", lay.size)
        fold.alpha_composite(R.svg_layer(sv))
        fa = np.asarray(fold.getchannel("A")).astype(np.float32) * (np.asarray(Image.fromarray((R_ * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(13))) > 128)
        fold.putalpha(Image.fromarray(fa.astype(np.uint8)))
        lay.alpha_composite(fold)
        if lift or dx or rot or alpha < 1:
            M = R.mat((X0 + w_ * 0.6 + dx) * Sx, (YT + h_ * 0.5 - lift) * Sx, rot, 1, 1, 0, (X0 + w_ * 0.6) * Sx, (YT + h_ * 0.5) * Sx)
            lay = R.warp_affine(lay, M, lay.size)
            if alpha < 1:
                lay.putalpha(lay.getchannel("A").point(lambda v: int(v * alpha)))
        return lay
    return fn
