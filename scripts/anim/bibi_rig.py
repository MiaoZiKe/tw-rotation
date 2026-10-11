"""比比可擺姿勢的骨架（rig）：用官方部件總表的部件重新組出每一格，不再變形原 GIF。

為什麼有這支
------------
Andy 2026-10-11 退件：「動畫效果太差了，需要是點擊互動按鈕，他會有對應動作，不是基於原本的 GIF 加點東西上去。
例如我點球，他會跟著球跑，我點草，他會有吃草畫面等等」。
舊做法（bibi_interact_g1/g2）＝原圖第 0 張像素網格變形＋補五官＋貼道具 → 看起來就是原圖加東西。
新做法：本體、耳朵、肉掌、腳、眼、嘴、腮紅都是**獨立部件**（docs/anim/bibi_library/parts/），
每一格重新算位置／旋轉／本體擠壓拉伸，肢體真的動。

座標
----
- 場景座標用 512×512（中心 x=248、腳底 y=482），內部用 S=2 倍（1024）合成，最後 LANCZOS 縮回 512。
- 本體＝`body_blank`（無五官毛球），內容寬 BODY_W 單位。本體局部座標 (u, v)：u=0 左緣、u=1 右緣、v=0 頂、v=1 底。
- 所有部件預設「面向左」（跟總表 `pose_side`、`foot_*`、`hand_side` 一致）；面向右＝整張鏡像。
- 層序 z：數字小的先畫（在後面）。

造型鐵則（docs/anim/bibi_library/reference/README.md）
----------------------------------------------------
四肢只有貼身小肉掌與兩顆小圓腳，不畫手臂；部件比例以 0.6×總表單件大小為準（跟 pose_front 對過）。
沒有的角度用 SVG 三次 Bézier 補畫（描邊 #1A0907、毛 #FDF5E9、肉掌 #E07E5E／#C55E44）。
"""
from __future__ import annotations

import io
import math
from functools import lru_cache
from pathlib import Path

import cairosvg
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PARTS = ROOT / "docs/anim/bibi_library/parts"

S = 2                      # 內部倍率
SIZE = 512
CX, FOOT_Y = 248.0, 482.0  # 場景中心與腳底
BODY_W = 290.0             # 本體內容寬（512 單位）
PART_K = 0.6               # 單件部件相對總表大小的比例（手、腳）
FEET_DROP = 11.0           # 腳從本體底緣往下露出的量（512 單位）
EAR_K = 0.8                # 耳朵
EYE_K = 0.85               # 眼睛（對過 pose_front：眼寬約身寬 6%）

INK = "#1A0907"
FUR = "#FDF5E9"
PAW = "#E07E5E"
PAW_D = "#C55E44"
PAW_L = "#FFB4A0"


# ---------------------------------------------------------------- 部件載入
def _trim(im: Image.Image) -> Image.Image:
    bb = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    return im.crop(bb)


@lru_cache(None)
def raw(name: str) -> Image.Image:
    return _trim(Image.open(PARTS / f"{name}.png").convert("RGBA"))


def split_pair(im: Image.Image) -> tuple[Image.Image, Image.Image]:
    """一對眼睛／腮紅 → 左、右兩件（找中間最寬的透明縫）。"""
    a = np.asarray(im.getchannel("A")) > 20
    cols = a.any(axis=0)
    w = len(cols)
    best, bx = -1, w // 2
    x = w // 4
    while x < 3 * w // 4:
        if not cols[x]:
            s = x
            while x < w and not cols[x]:
                x += 1
            if x - s > best:
                best, bx = x - s, (s + x) // 2
        x += 1
    return _trim(im.crop((0, 0, bx, im.height))), _trim(im.crop((bx, 0, w, im.height)))


@lru_cache(None)
def sheet_scale() -> float:
    """總表像素 → 512 單位。"""
    return BODY_W / raw("body_blank").width


@lru_cache(None)
def part(name: str, k: float = PART_K, sub: str = "") -> Image.Image:
    """回傳已縮放到 S 倍世界的部件（RGBA）。sub='L'/'R' 取一對中的左／右。"""
    im = raw(name)
    if sub:
        im = split_pair(im)[0 if sub == "L" else 1]
    f = sheet_scale() * k * S
    w, h = max(1, round(im.width * f)), max(1, round(im.height * f))
    return im.convert("RGBa").resize((w, h), Image.LANCZOS).convert("RGBA")


# ---------------------------------------------------------------- 仿射放置
def mat(tx=0.0, ty=0.0, rot=0.0, sx=1.0, sy=1.0, shear=0.0, px=0.0, py=0.0):
    """把局部點 p 映到世界：T(tx,ty)·R(rot)·Shear·Scale·(p - pivot)。rot 為度、順時針為正（螢幕座標）。"""
    r = math.radians(rot)
    c, s = math.cos(r), math.sin(r)
    R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])
    Sh = np.array([[1, shear, 0], [0, 1, 0], [0, 0, 1.0]])
    Sc = np.array([[sx, 0, 0], [0, sy, 0], [0, 0, 1.0]])
    P = np.array([[1, 0, -px], [0, 1, -py], [0, 0, 1.0]])
    T = np.array([[1, 0, tx], [0, 1, ty], [0, 0, 1.0]])
    return T @ R @ Sh @ Sc @ P


def apply(M, x, y):
    v = M @ np.array([x, y, 1.0])
    return float(v[0]), float(v[1])


def warp_affine(im: Image.Image, M, size=(SIZE * S, SIZE * S)) -> Image.Image:
    """M：影像像素 → 畫布像素（皆為 S 倍）。"""
    inv = np.linalg.inv(M)
    data = (inv[0, 0], inv[0, 1], inv[0, 2], inv[1, 0], inv[1, 1], inv[1, 2])
    out = im.convert("RGBa").transform(size, Image.AFFINE, data, resample=Image.BICUBIC)
    return out.convert("RGBA")


def place(canvas: Image.Image, im: Image.Image, x, y, rot=0.0, sx=1.0, sy=1.0,
          anchor=(0.5, 0.5), alpha=1.0, flip=False):
    """把部件的錨點（相對寬高的比例）放到世界座標 (x,y)（512 單位）。"""
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
        anchor = (1 - anchor[0], anchor[1])
    if alpha < 1:
        a = im.getchannel("A").point(lambda v: int(v * alpha))
        im = im.copy()
        im.putalpha(a)
    M = mat(x * S, y * S, rot, sx, sy, 0, anchor[0] * im.width, anchor[1] * im.height)
    canvas.alpha_composite(warp_affine(im, M, canvas.size))


# ---------------------------------------------------------------- 網格變形（毛飄）
def mesh_warp(im: Image.Image, inv_fn, grid=24) -> Image.Image:
    """inv_fn(x, y) -> (sx, sy)：輸出像素對應的來源像素。"""
    w, h = im.size
    data = []
    xs = np.linspace(0, w, grid + 1)
    ys = np.linspace(0, h, grid + 1)
    for j in range(grid):
        for i in range(grid):
            x0, x1, y0, y1 = xs[i], xs[i + 1], ys[j], ys[j + 1]
            q = []
            for (x, y) in ((x0, y0), (x0, y1), (x1, y1), (x1, y0)):
                q += list(inv_fn(x, y))
            data.append(((int(x0), int(y0), int(math.ceil(x1)), int(math.ceil(y1))), q))
    return im.convert("RGBa").transform((w, h), Image.MESH, data, resample=Image.BICUBIC).convert("RGBA")


@lru_cache(None)
def body_img(margin=24) -> Image.Image:
    """本體（S 倍）加透明邊，讓毛飄不被裁掉。"""
    im = raw("body_blank")
    f = sheet_scale() * S
    b = im.convert("RGBa").resize((round(im.width * f), round(im.height * f)), Image.LANCZOS).convert("RGBA")
    m = margin * S
    c = Image.new("RGBA", (b.width + 2 * m, b.height + 2 * m))
    c.alpha_composite(b, (m, m))
    return c


def body_box():
    im = body_img()
    m = 24 * S
    return m, m, im.width - m, im.height - m  # 內容框（S 倍像素）


@lru_cache(maxsize=64)
def fluttered_body(amp=0.0, phase=0.0, back=1.0, top=0.6, mode="side") -> Image.Image:
    if mode == "front":
        return _flutter_front(amp, phase)
    return _flutter_side(amp, phase, back, top)


def _flutter_front(amp, phase):
    """正面毛飄：上跳時頭頂毛被往下壓（amp>0）、落地時往上蓬（amp<0）；兩側毛往外抖。"""
    im = body_img()
    if abs(amp) <= 0.01:
        return im
    x0, y0, x1, y1 = body_box()
    w, h = x1 - x0, y1 - y0
    A = amp * S

    def inv(x, y):
        u = (x - x0) / w
        v = (y - y0) / h
        et = max(0.0, min(1.0, (0.4 - v) / 0.4)) ** 1.4
        es = max(0.0, min(1.0, (abs(u - 0.5) - 0.3) / 0.2)) ** 1.4
        dy = -A * et * (0.7 + 0.3 * math.sin(phase + u * 9))
        dx = -A * 0.45 * es * (1 if u > 0.5 else -1) * (0.6 + 0.4 * math.sin(phase * 1.4 + v * 8))
        return x + dx, y + dy

    return mesh_warp(im, inv)


def _flutter_side(amp=0.0, phase=0.0, back=1.0, top=0.6) -> Image.Image:
    """毛飄：背後（u 大的一側）與頭頂的毛跟著正弦波擺，振幅 amp（512 單位）。面向左時背後在右。"""
    im = body_img()
    if abs(amp) <= 0.01:   # 負值＝往前甩（急停時的跟隨動作）
        return im
    x0, y0, x1, y1 = body_box()
    w, h = x1 - x0, y1 - y0
    A = amp * S

    def inv(x, y):
        u = (x - x0) / w
        v = (y - y0) / h
        eb = max(0.0, min(1.0, (u - 0.45) / 0.55)) ** 1.5 * back
        et = max(0.0, min(1.0, (0.45 - v) / 0.45)) ** 1.5 * top
        dx = -A * eb * (0.6 + 0.4 * math.sin(phase + v * 9.0)) - A * 0.5 * et * math.sin(phase + u * 7)
        dy = A * 0.5 * et * (0.5 + 0.5 * math.sin(phase * 1.3 + u * 8.0))
        return x + dx, y + dy

    return mesh_warp(im, inv)


# ---------------------------------------------------------------- SVG 補畫
def svg_layer(body: str) -> Image.Image:
    doc = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{SIZE*S}" height="{SIZE*S}" '
           f'viewBox="0 0 {SIZE} {SIZE}">{body}</svg>')
    png = cairosvg.svg2png(bytestring=doc.encode("utf-8"))
    return Image.open(io.BytesIO(png)).convert("RGBA")


def ball_svg(cx, cy, r, ang=0.0, stroke=None) -> str:
    """紅白海灘球：兩條弧形紅瓣＋黃色中瓣＋亮點；ang 度旋轉。"""
    sw = stroke if stroke is not None else max(3.0, r * 0.11)
    k = r
    return f'''
<g transform="translate({cx:.2f},{cy:.2f}) rotate({ang:.2f})">
  <circle r="{k:.2f}" fill="#FFF8EE"/>
  <clipPath id="bc"><circle r="{k:.2f}"/></clipPath>
  <g clip-path="url(#bc)">
    <path d="M {-k*0.18:.2f} {-k*1.1:.2f} C {-k*0.75:.2f} {-k*0.4:.2f} {-k*0.75:.2f} {k*0.4:.2f} {-k*0.18:.2f} {k*1.1:.2f}
             L {-k*1.2:.2f} {k*1.1:.2f} L {-k*1.2:.2f} {-k*1.1:.2f} Z" fill="#E8564A"/>
    <path d="M {k*0.18:.2f} {-k*1.1:.2f} C {k*0.75:.2f} {-k*0.4:.2f} {k*0.75:.2f} {k*0.4:.2f} {k*0.18:.2f} {k*1.1:.2f}
             L {k*1.2:.2f} {k*1.1:.2f} L {k*1.2:.2f} {-k*1.1:.2f} Z" fill="#E8564A"/>
    <path d="M {-k*0.18:.2f} {-k*1.1:.2f} C {-k*0.75:.2f} {-k*0.4:.2f} {-k*0.75:.2f} {k*0.4:.2f} {-k*0.18:.2f} {k*1.1:.2f}"
          fill="none" stroke="{INK}" stroke-width="{sw*0.55:.2f}" stroke-linecap="round"/>
    <path d="M {k*0.18:.2f} {-k*1.1:.2f} C {k*0.75:.2f} {-k*0.4:.2f} {k*0.75:.2f} {k*0.4:.2f} {k*0.18:.2f} {k*1.1:.2f}"
          fill="none" stroke="{INK}" stroke-width="{sw*0.55:.2f}" stroke-linecap="round"/>
    <ellipse cx="0" cy="0" rx="{k*0.16:.2f}" ry="{k*0.16:.2f}" fill="#FFD25A" stroke="{INK}" stroke-width="{sw*0.45:.2f}"/>
    <path d="M {-k*1.2:.2f} {k*0.55:.2f} C {-k*0.5:.2f} {k*1.05:.2f} {k*0.5:.2f} {k*1.05:.2f} {k*1.2:.2f} {k*0.55:.2f} L {k*1.2:.2f} {k*1.3:.2f} L {-k*1.2:.2f} {k*1.3:.2f} Z"
          fill="#000" fill-opacity="0.10"/>
  </g>
  <circle r="{k - sw/2:.2f}" fill="none" stroke="{INK}" stroke-width="{sw:.2f}"/>
</g>
<ellipse cx="{cx - r*0.38 :.2f}" cy="{cy - r*0.45:.2f}" rx="{r*0.17:.2f}" ry="{r*0.10:.2f}" fill="#fff" fill-opacity="0.85"
  transform="rotate(-35 {cx - r*0.38:.2f} {cy - r*0.45:.2f})"/>
'''


def grass_svg(x, y, length, ang=0.0, w=13.0, bites=0) -> str:
    """一根牧草：從 (x,y) 往 ang 方向（度，0＝往左、順時針為正）長 length；頂端有穗；bites>0 時頂端是咬過的鋸齒。"""
    r = math.radians(ang)
    dx, dy = -math.cos(r), -math.sin(r)  # 往左上
    nx, ny = -dy, dx
    L = length
    pts = []
    # 兩側邊線（略彎）
    bend = L * 0.08
    tip = (x + dx * L, y + dy * L)
    ctrl = (x + dx * L * 0.5 + nx * bend, y + dy * L * 0.5 + ny * bend)
    hw = w / 2
    a1 = (x + nx * hw, y + ny * hw)
    a2 = (x - nx * hw, y - ny * hw)
    t1 = (tip[0] + nx * hw * 0.8, tip[1] + ny * hw * 0.8)
    t2 = (tip[0] - nx * hw * 0.8, tip[1] - ny * hw * 0.8)
    if bites:
        # 咬痕：三個小凹口
        mid = [(tip[0] + nx * hw * f + dx * (3 if i % 2 else -2), tip[1] + ny * hw * f + dy * (3 if i % 2 else -2))
               for i, f in enumerate((0.8, 0.3, -0.3, -0.8))]
        top = " ".join(f"L {p[0]:.2f} {p[1]:.2f}" for p in mid)
        head = ""
    else:
        top = f"Q {tip[0] + dx*w*0.9:.2f} {tip[1] + dy*w*0.9:.2f} {t2[0]:.2f} {t2[1]:.2f}"
        head = ""
    d = (f"M {a1[0]:.2f} {a1[1]:.2f} Q {ctrl[0]+nx*hw:.2f} {ctrl[1]+ny*hw:.2f} {t1[0]:.2f} {t1[1]:.2f} {top} "
         f"Q {ctrl[0]-nx*hw:.2f} {ctrl[1]-ny*hw:.2f} {a2[0]:.2f} {a2[1]:.2f} Z")
    vein = f"M {x:.2f} {y:.2f} Q {ctrl[0]:.2f} {ctrl[1]:.2f} {tip[0]-dx*6:.2f} {tip[1]-dy*6:.2f}"
    sw = max(3.0, w * 0.3)
    if not bites:
        # 牧草穗（提摩西草的圓柱穗）：沿莖方向的長橢圓＋短刻痕
        sl = min(L * 0.36, w * 3.6)
        cxp, cyp = tip[0] - dx * sl * 0.45, tip[1] - dy * sl * 0.45
        angd = math.degrees(math.atan2(dy, dx))
        ticks = "".join(
            f'<path d="M {-sl*0.5 + sl*f:.1f} {-w*0.85:.1f} l {w*0.25:.1f} {w*0.45:.1f} M {-sl*0.5 + sl*f:.1f} {w*0.85:.1f} '
            f'l {w*0.25:.1f} {-w*0.45:.1f}" stroke="#7D8F2E" stroke-width="{sw*0.5:.1f}" stroke-linecap="round"/>'
            for f in (0.2, 0.4, 0.6, 0.8))
        head = (f'<g transform="translate({cxp:.1f},{cyp:.1f}) rotate({angd:.1f})">'
                f'<ellipse rx="{sl*0.62:.1f}" ry="{w*0.8:.1f}" fill="#D9D77A" stroke="{INK}" stroke-width="{sw:.1f}"/>{ticks}</g>')
        # 一片葉子從莖中段岔出
        bx_, by_ = x + dx * L * 0.35, y + dy * L * 0.35
        lx, ly = bx_ + dx * L * 0.28 + nx * w * 2.6, by_ + dy * L * 0.28 + ny * w * 2.6
        head = (f'<path d="M {bx_:.1f} {by_:.1f} Q {bx_ + nx*w*2.4:.1f} {by_ + ny*w*2.4:.1f} {lx:.1f} {ly:.1f} '
                f'Q {bx_ + dx*L*0.18 + nx*w*0.6:.1f} {by_ + dy*L*0.18 + ny*w*0.6:.1f} {bx_:.1f} {by_:.1f} Z" '
                f'fill="#9AD46A" stroke="{INK}" stroke-width="{sw*0.8:.1f}" stroke-linejoin="round"/>') + head
    return (f'<path d="{d}" fill="#8CCB5E" stroke="{INK}" stroke-width="{sw:.1f}" stroke-linejoin="round"/>'
            f'<path d="{vein}" fill="none" stroke="#5E9E3A" stroke-width="{sw*0.6:.1f}" stroke-linecap="round"/>{head}')


def paw_svg(x, y, s=1.0, rot=0.0) -> str:
    """補畫的大肉掌（給東西的那隻手，向量才不糊）：手套形小圓團、蜜桃粉、根部深一點、
    C 形粗描邊在根部留缺口、指尖兩道短趾線 —— 照總表 hand_l 的樣子。(x,y)＝掌心；手指朝 rot 方向（0＝朝下）。"""
    k = s
    return f'''
<g transform="translate({x:.1f},{y:.1f}) rotate({rot:.1f}) scale({k:.3f})">
  <defs><linearGradient id="pg{int(x)}{int(y)}" x1="0" y1="-1" x2="0" y2="1">
    <stop offset="0" stop-color="{PAW_D}"/><stop offset="0.45" stop-color="{PAW}"/><stop offset="1" stop-color="{PAW_L}"/></linearGradient></defs>
  <path d="M -34 -30 C -50 0 -46 34 -22 46 C -6 56 10 56 24 46 C 48 34 50 0 34 -30 Z" fill="url(#pg{int(x)}{int(y)})"/>
  <path d="M -34 -30 C -50 0 -46 34 -22 46 C -6 56 10 56 24 46 C 48 34 50 0 34 -30" fill="none"
        stroke="{INK}" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M -8 50 L -8 36 M 9 50 L 9 36" stroke="{INK}" stroke-width="6.5" stroke-linecap="round"/>
  <ellipse cx="-12" cy="-6" rx="9" ry="6" fill="#fff" fill-opacity="0.35"/>
</g>'''


def text_svg(txt, x, y, size=34, rot=0.0, fill=INK) -> str:
    """擬聲字（嚼嚼、咕嚕…）：白色粗外框＋深色字，畫兩次（cairosvg 不支援 paint-order）。"""
    base = (f'x="{x:.1f}" y="{y:.1f}" font-family="WenQuanYi Zen Hei" font-size="{size}" font-weight="bold" '
            f'transform="rotate({rot:.1f} {x:.1f} {y:.1f})"')
    return (f'<text {base} fill="#fff" stroke="#fff" stroke-width="{size*0.22:.1f}" stroke-linejoin="round">{txt}</text>'
            f'<text {base} fill="{fill}">{txt}</text>')


def crumbs_svg(x, y, n=4, spread=26, seed=0, alpha=1.0) -> str:
    """草屑：幾截小綠段往外噴。"""
    out = []
    for i in range(n):
        a = math.radians((seed * 47 + i * 360 / n + 20) % 360)
        d = spread * (0.6 + 0.4 * ((i + seed) % 3) / 2)
        cx, cy = x + d * math.cos(a), y + d * math.sin(a) * 0.7
        rot = (seed * 31 + i * 57) % 180
        out.append(f'<rect x="{cx-5:.1f}" y="{cy-2.5:.1f}" width="10" height="5" rx="2" fill="#8CCB5E" stroke="{INK}" '
                   f'stroke-width="2" transform="rotate({rot} {cx:.1f} {cy:.1f})" opacity="{alpha:.2f}"/>')
    return "".join(out)


def popcorn_svg(x, y, s=1.0, rot=0.0) -> str:
    """一顆爆米花：四團奶油白蓬蓬＋底下一點黃色殼，粗描邊。"""
    blobs = [(0, 0, 11), (-10, -6, 9), (9, -8, 9), (1, -15, 8), (-4, 7, 7)]
    circ = "".join(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="{r:.1f}"/>' for bx, by, r in blobs)
    return (f'<g transform="translate({x:.1f},{y:.1f}) rotate({rot:.1f}) scale({s:.3f})">'
            f'<g fill="none" stroke="{INK}" stroke-width="6">{circ}</g><g fill="#FFF6DC">{circ}</g>'
            f'<path d="M -7 8 Q 0 14 8 6 Q 3 3 -7 8 Z" fill="#F6C453" stroke="{INK}" stroke-width="2.4" stroke-linejoin="round"/>'
            f'<path d="M -6 -9 q 3 -3 6 -1" fill="none" stroke="#E9D9B5" stroke-width="2.4" stroke-linecap="round"/></g>')


def popcorn_icon_svg() -> str:
    """互動小圈圖示：紅白直條紋爆米花桶＋桶口冒出四顆蓬蓬的爆米花（512 畫布座標）。"""
    shape = "M 132 240 L 380 240 L 346 462 L 166 462 Z"
    top = (popcorn_svg(176, 216, 4.6, -14) + popcorn_svg(338, 214, 4.6, 16) + popcorn_svg(258, 150, 5.2, 4)
           + popcorn_svg(250, 228, 4.4, -4))
    stripes = "".join(f'<rect x="{150 + i*46:.0f}" y="230" width="23" height="250" fill="#E8564A"/>' for i in range(5))
    bucket = (f'<clipPath id="bk"><path d="{shape}"/></clipPath><path d="{shape}" fill="#FFF8EE"/>'
              f'<g clip-path="url(#bk)">{stripes}</g>'
              f'<path d="{shape}" fill="none" stroke="{INK}" stroke-width="18" stroke-linejoin="round"/>'
              f'<path d="M 124 240 L 388 240" stroke="{INK}" stroke-width="20" stroke-linecap="round"/>')
    return top + bucket


def burst_svg(x, y, r=26, n=8, rot=0.0, w=5.0, color=None) -> str:
    """放射短線（擊掌、閃光燈、驚嚇）。"""
    c = color or INK
    out = []
    for i in range(n):
        a = math.radians(rot + i * 360 / n)
        x0, y0 = x + r * 0.55 * math.cos(a), y + r * 0.55 * math.sin(a)
        x1, y1 = x + r * math.cos(a), y + r * math.sin(a)
        out.append(f'<path d="M {x0:.1f} {y0:.1f} L {x1:.1f} {y1:.1f}" stroke="{c}" stroke-width="{w}" stroke-linecap="round"/>')
    return "".join(out)


def speed_lines_svg(x, y, n=3, length=60, gap=16, alpha=0.9, seed=0) -> str:
    out = []
    for i in range(n):
        L = length * (0.6 + 0.4 * ((i * 7 + seed) % 3) / 2)
        yy = y + (i - (n - 1) / 2) * gap
        xx = x + ((i * 13 + seed * 5) % 3) * 8
        out.append(f'<path d="M {xx:.1f} {yy:.1f} L {xx+L:.1f} {yy:.1f}" stroke="{INK}" stroke-opacity="{alpha:.2f}" '
                   f'stroke-width="4.5" stroke-linecap="round"/>')
    return "".join(out)


def dust_svg(x, y, s=1.0, alpha=1.0) -> str:
    """塵土雲：三顆圓疊起來＋描邊。"""
    c = [(0, 0, 13), (15, -5, 11), (-13, -3, 9), (6, -14, 9)]
    circ = "".join(f'<circle cx="{x+dx*s:.1f}" cy="{y+dy*s:.1f}" r="{r*s:.1f}"/>' for dx, dy, r in c)
    return (f'<g opacity="{alpha:.2f}"><g fill="none" stroke="{INK}" stroke-width="{5}">{circ}</g>'
            f'<g fill="#EFE3CF">{circ}</g></g>')


def star_svg(x, y, r=14.0, rot=0.0, fill="#FFD25A") -> str:
    pts = []
    for i in range(10):
        a = math.radians(rot - 90 + i * 36)
        rr = r if i % 2 == 0 else r * 0.45
        pts.append(f"{x + rr*math.cos(a):.2f},{y + rr*math.sin(a):.2f}")
    return (f'<polygon points="{" ".join(pts)}" fill="{fill}" stroke="{INK}" stroke-width="3.5" '
            f'stroke-linejoin="round"/>')


def mouth_svg(kind: str, x, y, s=1.0, facing_left=True) -> str:
    """側面／正面的小嘴（512 單位）。kind：open／o／w／chew_a／chew_b／chew_c／smile／flat／none。"""
    k = s
    if kind == "none":
        return ""
    if kind == "open":   # 小開口吐舌（側面三角）
        return (f'<path d="M {x-9*k:.1f} {y-4*k:.1f} C {x-8*k:.1f} {y+9*k:.1f} {x+8*k:.1f} {y+9*k:.1f} {x+9*k:.1f} {y-4*k:.1f} Z" '
                f'fill="#8A2B22" stroke="{INK}" stroke-width="{3.6*k:.1f}" stroke-linejoin="round"/>'
                f'<path d="M {x-5*k:.1f} {y+4*k:.1f} C {x-3*k:.1f} {y+8*k:.1f} {x+4*k:.1f} {y+8*k:.1f} {x+6*k:.1f} {y+3*k:.1f} Z" fill="#F08C7C"/>')
    if kind == "o":
        return (f'<ellipse cx="{x:.1f}" cy="{y+2*k:.1f}" rx="{6*k:.1f}" ry="{8*k:.1f}" fill="#8A2B22" stroke="{INK}" stroke-width="{3.6*k:.1f}"/>'
                f'<ellipse cx="{x:.1f}" cy="{y+6*k:.1f}" rx="{3.6*k:.1f}" ry="{2.6*k:.1f}" fill="#F08C7C"/>')
    if kind == "w":
        return (f'<path d="M {x-12*k:.1f} {y-2*k:.1f} Q {x-6*k:.1f} {y+7*k:.1f} {x:.1f} {y-1*k:.1f} Q {x+6*k:.1f} {y+7*k:.1f} {x+12*k:.1f} {y-2*k:.1f}" '
                f'fill="none" stroke="{INK}" stroke-width="{3.6*k:.1f}" stroke-linecap="round" stroke-linejoin="round"/>')
    if kind == "smile":
        return (f'<path d="M {x-11*k:.1f} {y-3*k:.1f} Q {x:.1f} {y+10*k:.1f} {x+11*k:.1f} {y-3*k:.1f} Z" fill="#8A2B22" '
                f'stroke="{INK}" stroke-width="{3.6*k:.1f}" stroke-linejoin="round"/>'
                f'<path d="M {x-5*k:.1f} {y+3*k:.1f} Q {x:.1f} {y+7*k:.1f} {x+5*k:.1f} {y+3*k:.1f} Z" fill="#F08C7C"/>')
    if kind == "wavy":   # 波浪嘴（暈、尷尬）
        return (f'<path d="M {x-14*k:.1f} {y:.1f} q {3.5*k:.1f} {-5*k:.1f} {7*k:.1f} 0 t {7*k:.1f} 0 t {7*k:.1f} 0 t {7*k:.1f} 0" '
                f'fill="none" stroke="{INK}" stroke-width="{3.6*k:.1f}" stroke-linecap="round" stroke-linejoin="round"/>')
    if kind == "flat":
        return (f'<path d="M {x-7*k:.1f} {y:.1f} Q {x:.1f} {y+3*k:.1f} {x+7*k:.1f} {y:.1f}" fill="none" stroke="{INK}" '
                f'stroke-width="{3.6*k:.1f}" stroke-linecap="round"/>')
    if kind.startswith("chew"):
        # 啃咬：a＝張大（露門牙）、b＝半開、c＝閉嘴鼓起
        if kind == "chew_a":
            return (f'<path d="M {x-9*k:.1f} {y-3*k:.1f} C {x-9*k:.1f} {y+12*k:.1f} {x+9*k:.1f} {y+12*k:.1f} {x+9*k:.1f} {y-3*k:.1f} Z" '
                    f'fill="#8A2B22" stroke="{INK}" stroke-width="{3.6*k:.1f}" stroke-linejoin="round"/>'
                    f'<rect x="{x-5*k:.1f}" y="{y-3*k:.1f}" width="{10*k:.1f}" height="{6*k:.1f}" rx="{1.5*k:.1f}" fill="#fff" stroke="{INK}" stroke-width="{2*k:.1f}"/>')
        if kind == "chew_b":
            return (f'<path d="M {x-9*k:.1f} {y-1*k:.1f} C {x-6*k:.1f} {y+6*k:.1f} {x+6*k:.1f} {y+6*k:.1f} {x+9*k:.1f} {y-1*k:.1f} Z" '
                    f'fill="#8A2B22" stroke="{INK}" stroke-width="{3.6*k:.1f}" stroke-linejoin="round"/>'
                    f'<rect x="{x-4*k:.1f}" y="{y-1.5*k:.1f}" width="{8*k:.1f}" height="{4*k:.1f}" rx="{1.2*k:.1f}" fill="#fff" stroke="{INK}" stroke-width="{1.8*k:.1f}"/>')
        return (f'<path d="M {x-10*k:.1f} {y:.1f} Q {x-5*k:.1f} {y+5*k:.1f} {x:.1f} {y+1*k:.1f} Q {x+5*k:.1f} {y+5*k:.1f} {x+10*k:.1f} {y:.1f}" '
                f'fill="none" stroke="{INK}" stroke-width="{3.6*k:.1f}" stroke-linecap="round"/>')
    raise ValueError(kind)


def blush_svg(x, y, a=1.0, s=1.0, lines=False) -> str:
    """腮紅：蜜桃粉橢圓（總表 pose_front 的樣子）；a＝濃度（臉紅時 >1 會更大更紅）。"""
    if a <= 0.01:
        return ""
    rx, ry = 27 * s * (0.9 + 0.1 * a), 18 * s * (0.9 + 0.1 * a)
    op = min(1.0, 0.55 * a)
    out = f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="#F7948A" fill-opacity="{op:.2f}"/>'
    if lines:
        for i in (-1, 0, 1):
            xx = x + i * rx * 0.42
            out += (f'<path d="M {xx-4:.1f} {y+6:.1f} L {xx+4:.1f} {y-6:.1f}" stroke="#fff" stroke-width="3" '
                    f'stroke-linecap="round" stroke-opacity="0.9"/>')
    return out


def eye_svg(kind: str, x, y, s=1.0) -> str:
    """補畫的眼型：arc（彎月 ︶ 開心）、squint（> 用力）、star（星星眼）、x（暈）、wide（大圓＋兩亮點）。"""
    k = s
    if kind == "arc":
        return (f'<path d="M {x-10*k:.1f} {y+2*k:.1f} Q {x:.1f} {y-9*k:.1f} {x+10*k:.1f} {y+2*k:.1f}" fill="none" '
                f'stroke="{INK}" stroke-width="{4.6*k:.1f}" stroke-linecap="round"/>')
    if kind == "smile":
        return (f'<path d="M {x-10*k:.1f} {y-3*k:.1f} Q {x:.1f} {y+8*k:.1f} {x+10*k:.1f} {y-3*k:.1f}" fill="none" '
                f'stroke="{INK}" stroke-width="{4.6*k:.1f}" stroke-linecap="round"/>')
    if kind == "squint":  # 面向左的 >（用力）
        return (f'<path d="M {x+8*k:.1f} {y-8*k:.1f} L {x-6*k:.1f} {y:.1f} L {x+8*k:.1f} {y+8*k:.1f}" fill="none" '
                f'stroke="{INK}" stroke-width="{4.6*k:.1f}" stroke-linecap="round" stroke-linejoin="round"/>')
    if kind == "star":
        return star_svg(x, y, 14.5 * k, 0, "#FFD25A")
    if kind == "spiral":   # 暈眩螺旋眼
        pts = []
        for i in range(36):
            t = i / 35 * 4.2 * math.pi
            r = 1.0 + 9.5 * k * i / 35
            pts.append(f"{x + r*math.cos(t):.1f},{y + r*math.sin(t):.1f}")
        return (f'<polyline points="{" ".join(pts)}" fill="none" stroke="{INK}" stroke-width="{3.4*k:.1f}" '
                f'stroke-linecap="round" stroke-linejoin="round"/>')
    if kind == "x":
        return (f'<path d="M {x-7*k:.1f} {y-7*k:.1f} L {x+7*k:.1f} {y+7*k:.1f} M {x+7*k:.1f} {y-7*k:.1f} L {x-7*k:.1f} {y+7*k:.1f}" '
                f'stroke="{INK}" stroke-width="{4.4*k:.1f}" stroke-linecap="round"/>')
    if kind == "wide":
        k *= 1.3
        return (f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{8.5*k:.1f}" ry="{10*k:.1f}" fill="{INK}"/>'
                f'<circle cx="{x-3*k:.1f}" cy="{y-4*k:.1f}" r="{3.2*k:.1f}" fill="#fff"/>'
                f'<circle cx="{x+3*k:.1f}" cy="{y+3.5*k:.1f}" r="{1.6*k:.1f}" fill="#fff"/>')
    raise ValueError(kind)


# ---------------------------------------------------------------- 內插
def ease(t: float, kind: str = "inout") -> float:
    t = max(0.0, min(1.0, t))
    if kind == "in":
        return t * t
    if kind == "out":
        return 1 - (1 - t) ** 2
    if kind == "back":   # 稍微衝過頭再回來
        c = 1.70158
        return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2
    if kind == "linear":
        return t
    return t * t * (3 - 2 * t)


def lerp_pose(a: dict, b: dict, t: float) -> dict:
    """數值鍵 ease 內插；字串／布林鍵取 t<0.5 的那邊；巢狀 dict 遞迴。"""
    out = {}
    for k in set(a) | set(b):
        # 一邊沒寫的鍵用預設姿勢補（不然「站好→蹲下」少寫 sy 就不會內插）
        va, vb = a.get(k, DEFAULT.get(k, b.get(k))), b.get(k, DEFAULT.get(k, a.get(k)))
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)) and not isinstance(va, bool):
            out[k] = va + (vb - va) * t
        elif isinstance(va, dict) and isinstance(vb, dict):
            out[k] = lerp_pose(va, vb, t)
        elif isinstance(va, (tuple, list)) and isinstance(vb, (tuple, list)) and len(va) == len(vb) \
                and all(isinstance(x, (int, float)) for x in va + vb):
            out[k] = type(va)(x + (y - x) * t for x, y in zip(va, vb))
        else:
            out[k] = va if t < 0.5 else vb
    return out


# ---------------------------------------------------------------- 角色合成
DEFAULT = dict(
    view="side",          # side（面向左）/ front
    x=CX, y=FOOT_Y,       # 本體底部中心（512 單位）
    sx=1.0, sy=1.0,       # 擠壓伸展（以底部中心為錨）
    rot=0.0, shear=0.0,   # 本體傾斜（度）、剪切
    flutter=0.0, fphase=0.0,
    ear=0.0, ear2=0.0,    # 耳朵旋轉（度，正＝往後倒）
    eye="dot", mouth="w", blush=1.0, eye_open=1.0,
    # 四肢偏移（512 單位，相對預設錨點）與旋轉
    fp_near=(0.0, 0.0, 0.0), fp_far=(0.0, 0.0, 0.0),  # 前掌（側面）／左右手（正面）
    bf_near=(0.0, 0.0, 0.0), bf_far=(0.0, 0.0, 0.0),  # 後腳（側面）／左右腳（正面）
    tail=(0.0, 0.0, 0.0),
    hands_front=False,    # 正面時手是否舉到身前（捧東西）
    look=(0.0, 0.0),      # 五官整體偏移（u, v）
    cheek=0.0,            # 臉頰鼓起（0～1.3，嚼東西）
    gx=0.0, gy=0.0, grot=0.0, gpx=CX, gpy=330.0,  # 整組旋轉（翻滾用）
    facing="left",
)


def body_matrix(p):
    """本體圖（S 倍像素）→ 畫布（S 倍像素）。"""
    x0, y0, x1, y1 = body_box()
    px, py = (x0 + x1) / 2, y1 - 6 * S   # 錨點：底部中心（毛的最下緣再往上一點，讓腳貼地）
    # 腳掌會從身體底下露出約 FEET_DROP，所以本體錨點抬高，讓「腳底」落在 p["y"]（場景腳底 y=482）
    return mat(p["x"] * S, (p["y"] - FEET_DROP) * S, p["rot"], p["sx"], p["sy"], p["shear"], px, py)


def body_pt(p, u, v):
    """本體局部 (u,v) → 世界（512 單位），跟本體一起擠壓／傾斜。"""
    x0, y0, x1, y1 = body_box()
    M = body_matrix(p)
    X, Y = apply(M, x0 + u * (x1 - x0), y0 + v * (y1 - y0))
    return X / S, Y / S


def compose(p: dict, extra_back: str = "", extra_front: str = "", props_back=None, props_mid=None,
            props_front=None, fx=None) -> tuple[Image.Image, dict]:
    """依姿勢參數合成一格（S 倍畫布）。回傳 (畫布, 各元素外框 dict) —— 外框給重疊檢查用。

    props_*：list of (image_S倍, x, y, rot, anchor) 或 callable(canvas)。
    extra_*：SVG 片段（在身體後／在最前）。fx：效果 SVG（最上層；字串或字串清單，清單逐件記外框）。
    """
    p = {**DEFAULT, **p}
    W = SIZE * S
    can = Image.new("RGBA", (W, W))
    boxes: dict[str, tuple] = {}
    masks: dict[str, Image.Image] = {}   # 逐件 alpha（重疊檢查用像素比對，不只外框）
    side = p["view"] == "side"
    lu, lv = p["look"]

    def put_props(lst, tag):
        for i, it in enumerate(lst or []):
            if isinstance(it, Image.Image):      # 已經畫好的整張畫布圖層（例如 SVG 球）
                boxes[f"{tag}{i}"] = it.getchannel("A").getbbox()
                masks[f"{tag}{i}"] = it.getchannel("A")
                can.alpha_composite(it)
                continue
            if callable(it):
                it(can)
                continue
            im, x, y, r, anc = it
            lay = Image.new("RGBA", (W, W))
            place(lay, im, x, y, r, anchor=anc)
            boxes[f"{tag}{i}"] = lay.getchannel("A").getbbox()
            masks[f"{tag}{i}"] = lay.getchannel("A")
            can.alpha_composite(lay)

    if extra_back:
        can.alpha_composite(svg_layer(extra_back))
    put_props(props_back, "propB")

    # --- 身體後面的肢體（遠側）
    if side:
        # 後腳遠側、前掌遠側
        fx_, fy_, fr = p["bf_far"]
        X, Y = body_pt(p, 0.66, 0.97)
        place(can, _shade(part("foot_r")), X + fx_, Y + fy_, fr, anchor=(0.45, 0.35))
        fx_, fy_, fr = p["fp_far"]
        X, Y = body_pt(p, 0.30, 0.95)
        place(can, _shade(part("foot_l", PART_K * 0.85)), X + fx_, Y + fy_, fr, anchor=(0.5, 0.35))
        # 尾巴（背後毛團）
        tx, ty, tr = p["tail"]
        X, Y = body_pt(p, 0.95, 0.66)
        place(can, tail_img(0.75), X + tx, Y + ty, tr, anchor=(0.25, 0.5))
    else:
        for key, u, nm in (("bf_far", 0.30, "foot_l"), ("bf_near", 0.70, "foot_r")):
            fx_, fy_, fr = p[key]
            X, Y = body_pt(p, u, 0.965)
            place(can, part(nm, PART_K * 0.9), X + fx_, Y + fy_, fr, anchor=(0.5, 0.35))

    # --- 耳朵（在身體後面，插進毛裡）
    if p["view"] == "front":
        X, Y = body_pt(p, 0.235 + lu, 0.17)
        place(can, part("ear_l", EAR_K), X, Y, -14 - p["ear"], anchor=(0.6, 0.9))
        X, Y = body_pt(p, 0.765 + lu, 0.17)
        place(can, part("ear_r", EAR_K), X, Y, 14 + p["ear2"], anchor=(0.4, 0.9))
    elif p["view"] == "back":
        X, Y = body_pt(p, 0.21, 0.15)
        place(can, part("ear_l", EAR_K), X, Y, -14 - p["ear"], anchor=(0.6, 0.9))
        X, Y = body_pt(p, 0.79, 0.15)
        place(can, part("ear_r", EAR_K), X, Y, 14 + p["ear2"], anchor=(0.4, 0.9))

    # --- 本體
    b = fluttered_body(round(p["flutter"], 2), round(p["fphase"], 2), mode="front" if p["view"] != "side" else "side")
    blay = warp_affine(b, body_matrix(p), can.size)
    boxes["body"] = blay.getchannel("A").getbbox()
    can.alpha_composite(blay)
    put_props(props_mid, "propM")

    # --- 前面的肢體（近側）
    if side:
        fx_, fy_, fr = p["bf_near"]
        X, Y = body_pt(p, 0.60, 0.985)
        place(can, part("foot_r"), X + fx_, Y + fy_, fr, anchor=(0.45, 0.30))
        fx_, fy_, fr = p["fp_near"]
        X, Y = body_pt(p, 0.24, 0.93)
        place(can, part("hand_side", PART_K * 0.85), X + fx_, Y + fy_, fr, anchor=(0.55, 0.4))

    # --- 五官
    face = []
    if side:
        # 側面耳朵：長在頭頂後方、畫在毛上面（同 pose_side）
        X, Y = body_pt(p, 0.40 + lu * 0.5, 0.19)
        place(can, part("ear_r", EAR_K), X, Y, 10 + p["ear"], anchor=(0.45, 0.92))
        ex, ey = body_pt(p, 0.15 + lu, 0.43 + lv)
        bx, by = body_pt(p, 0.18 + lu, 0.555 + lv)
        mx, my = body_pt(p, 0.055 + lu, 0.545 + lv)
        can.alpha_composite(svg_layer(blush_svg(bx, by, p["blush"], 0.8)))
        flay = Image.new("RGBA", can.size)
        _draw_eye(flay, p["eye"], ex, ey, p["eye_open"], left=True)
        flay.alpha_composite(svg_layer(mouth_svg(p["mouth"], mx, my, 1.2)))
        boxes["face"] = flay.getchannel("A").getbbox()
        masks["face"] = flay.getchannel("A")
        can.alpha_composite(flay)
    elif p["view"] == "front":
        flay = Image.new("RGBA", can.size)   # 臉（眼＋嘴）外框給重疊檢查；腮紅另畫不算
        if p.get("cheek", 0) > 0.01:          # 鼓起的臉頰：嘴兩側往外鼓的弧線（嚼東西）
            ck = p["cheek"]
            arcs = ""
            for sgn in (-1, 1):
                cx_, cy_ = body_pt(p, 0.5 + lu + sgn * 0.2, 0.545 + lv)
                r = 24 + 10 * ck
                a0, a1 = (math.radians(-25), math.radians(75)) if sgn > 0 else (math.radians(205), math.radians(105))
                x0_, y0_ = cx_ + r * math.cos(a0), cy_ + r * math.sin(a0)
                x1_, y1_ = cx_ + r * math.cos(a1), cy_ + r * math.sin(a1)
                sweep = 1 if sgn > 0 else 0
                arcs += (f'<path d="M {x0_:.1f} {y0_:.1f} A {r:.1f} {r:.1f} 0 0 {sweep} {x1_:.1f} {y1_:.1f}" fill="none" '
                         f'stroke="{INK}" stroke-width="5" stroke-linecap="round" stroke-opacity="{min(1, 0.6 + 0.4*ck):.2f}"/>')
            can.alpha_composite(svg_layer(arcs))
        for sgn, sub in ((-1, "L"), (1, "R")):
            ex, ey = body_pt(p, 0.5 + lu + sgn * 0.13, 0.42 + lv)
            bx, by = body_pt(p, 0.5 + lu + sgn * 0.27, 0.53 + lv)
            can.alpha_composite(svg_layer(blush_svg(bx, by, p["blush"])))
            _draw_eye(flay, p["eye"], ex, ey, p["eye_open"], left=(sgn < 0))
        mx, my = body_pt(p, 0.5 + lu, 0.50 + lv)
        flay.alpha_composite(svg_layer(mouth_svg(p["mouth"], mx, my, 1.5)))
        boxes["face"] = flay.getchannel("A").getbbox()
        masks["face"] = flay.getchannel("A")
        can.alpha_composite(flay)
        # 正面的手：貼在身體兩側或身前
        for key, u, nm, sgn in (("fp_far", 0.10, "hand_l", -1), ("fp_near", 0.90, "hand_r", 1)):
            fx_, fy_, fr = p[key]
            if p["hands_front"]:
                u = 0.5 + sgn * 0.17
                X, Y = body_pt(p, u, 0.80)
            else:
                X, Y = body_pt(p, u, 0.70)
            place(can, part(nm, PART_K * 0.85), X + fx_, Y + fy_, fr, anchor=(0.5, 0.6))
    elif p["view"] == "back":
        tx, ty, tr = p["tail"]
        X, Y = body_pt(p, 0.5, 0.72)
        place(can, tail_img(1.0), X + tx, Y + ty, tr, anchor=(0.5, 0.5))

    put_props(props_front, "propF")
    if extra_front:
        can.alpha_composite(svg_layer(extra_front))
    if fx:
        # 效果符號逐件畫，每件各自記外框（重疊檢查要逐件比，不是整片聯集）
        for i, piece in enumerate([fx] if isinstance(fx, str) else fx):
            if not piece:
                continue
            fl = svg_layer(piece)
            bb = fl.getchannel("A").getbbox()
            if bb:
                boxes[f"fx{i}"] = bb
                masks[f"fx{i}"] = fl.getchannel("A")
            can.alpha_composite(fl)

    # --- 整組旋轉（翻滾）與面向
    M = np.eye(3)
    if abs(p["grot"]) > 0.01 or abs(p["gx"]) > 0.01 or abs(p["gy"]) > 0.01:
        M = mat((p["gpx"] + p["gx"]) * S, (p["gpy"] + p["gy"]) * S, p["grot"], 1, 1, 0, p["gpx"] * S, p["gpy"] * S)
    if p["facing"] == "right":
        F = np.array([[-1, 0, 2 * CX * S], [0, 1, 0], [0, 0, 1.0]])
        M = F @ M
    if not np.allclose(M, np.eye(3)):
        can = warp_affine(can, M, can.size)
        boxes = {k: _tf_box(v, M) for k, v in boxes.items() if v}
        inv = np.linalg.inv(M)
        data = (inv[0, 0], inv[0, 1], inv[0, 2], inv[1, 0], inv[1, 1], inv[1, 2])
        masks = {k: m.transform(can.size, Image.AFFINE, data, resample=Image.BILINEAR) for k, m in masks.items()}
    boxes["__masks"] = {k: np.asarray(m.reduce(4)) > 40 for k, m in masks.items()}
    return can, boxes


def _tf_box(bb, M):
    x0, y0, x1, y1 = bb
    pts = [apply(M, x, y) for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))]
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def _shade(im: Image.Image, f=0.86) -> Image.Image:
    """遠側肢體壓暗一點，讀得出前後。"""
    a = np.asarray(im).astype(np.float32)
    a[..., :3] *= f
    return Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA")


@lru_cache(None)
def tail_img(k: float = 0.9) -> Image.Image:
    """背面小尾巴毛團：從 pose_back_tail 切出（中下方那團），保留原毛邊像素。"""
    im = raw("pose_back_tail")
    w, h = im.size
    box = (int(w * 0.36), int(h * 0.60), int(w * 0.64), int(h * 0.93))
    t = im.crop(box)
    # 只留跟中心連通、亮的那團（尾巴有自己的描邊圈）：用橢圓遮罩
    m = Image.new("L", t.size, 0)
    from PIL import ImageDraw
    ImageDraw.Draw(m).ellipse((1, 1, t.width - 2, t.height - 2), fill=255)
    a = np.minimum(np.asarray(t.getchannel("A")), np.asarray(m))
    t.putalpha(Image.fromarray(a))
    t = _trim(t)
    f = sheet_scale() * k * S   # pose_back_tail 跟 body_blank 在總表上大小相近，直接用同一比例
    return t.convert("RGBa").resize((max(1, round(t.width * f)), max(1, round(t.height * f))), Image.LANCZOS).convert("RGBA")


def _draw_eye(lay, kind, x, y, open_=1.0, left=True):
    if kind == "wink":      # 眨一隻眼：左眼圓點、右眼彎月
        kind = "dot" if left else "arc"
    if kind == "dot":
        if open_ < 0.35:   # 眨眼中段：閉成一條線
            lay.alpha_composite(svg_layer(
                f'<path d="M {x-8:.1f} {y+1:.1f} Q {x:.1f} {y+4:.1f} {x+8:.1f} {y+1:.1f}" fill="none" stroke="{INK}" '
                f'stroke-width="4.4" stroke-linecap="round"/>'))
        else:
            im = part("eyes_dot", EYE_K, "L" if left else "R")
            place(lay, im, x, y, 0, 1.0, open_)
    elif kind == "closed":
        lay.alpha_composite(svg_layer(
            f'<path d="M {x-9:.1f} {y:.1f} Q {x:.1f} {y+5:.1f} {x+9:.1f} {y:.1f}" fill="none" stroke="{INK}" '
            f'stroke-width="4.4" stroke-linecap="round"/>'))
    else:
        lay.alpha_composite(svg_layer(eye_svg(kind, x, y, 1.0)))


def finish(can: Image.Image) -> Image.Image:
    """S 倍畫布 → 512（LANCZOS，預乘 alpha 避免黑邊）。"""
    return can.convert("RGBa").resize((SIZE, SIZE), Image.LANCZOS).convert("RGBA")


# ---------------------------------------------------------------- 檢查工具
def bbox512(bb):
    if not bb:
        return None
    return tuple(v / S for v in bb)


def overlap(a, b, pad=0.0):
    if not a or not b:
        return 0.0
    x0, y0 = max(a[0], b[0]) - pad, max(a[1], b[1]) - pad
    x1, y1 = min(a[2], b[2]) + pad, min(a[3], b[3]) + pad
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)


def inside_canvas(im: Image.Image, margin=1) -> bool:
    """全身入鏡：四邊 margin 像素內沒有不透明像素。"""
    a = np.asarray(im.getchannel("A"))
    return not (a[:margin].any() or a[-margin:].any() or a[:, :margin].any() or a[:, -margin:].any())


# ====================================================================================================
# 原版 Default 骨架（Andy 10-11 第二次退件後的正式版）
# ----------------------------------------------------------------------------------------------------
# Andy：「這個已經跟原來的不同了，請參考原本的圖三作為 Default，大部分時間都是那樣子」。
# → 本體不再用總表的 body_blank，而是直接用 `reference/default_idle_1011.webp`（原版比比待機）的像素：
#   1. 灌水去背（深色粗描邊是封閉的），邊緣 1px 從底色反混色。
#   2. 拆件：眼（左右兩顆黑點）、嘴（ㅅ＋小舌頭）、腮紅（兩顆大桃粉圓）各自是一層原像素；
#      本體無五官＝把五官位置用周圍毛色擴散補平。
#   3. 耳朵、腳不切開（它們跟毛邊黏在同一圈描邊上），改用「局部網格變形」：
#      耳朵繞耳根轉、腳往下垂／往上縮／往外踢，毛邊照樣是原圖像素。
#   4. 地面影子另畫（淡棕橢圓），跳起來會變小變淡。
# 座標：DEF_* 都是原圖（512）像素；場景上把原圖的「腳底中心」對到 (CX, FOOT_Y)。
# ====================================================================================================
DEF_SRC = ROOT / "docs/anim/bibi_library/reference/default_idle_1011.webp"
DEF_BG = np.array([252, 246, 239], np.float32)
DEF_FOOT = (253.5, 478.0)          # 原圖腳底中心（描邊最下緣約 484）
DEF_EYE_L, DEF_EYE_R = (192.5, 264.0), (309.5, 261.0)
DEF_MOUTH = (250.5, 290.0)
DEF_BLUSH_L, DEF_BLUSH_R = (151.0, 288.0), (351.0, 284.0)
DEF_EAR_L, DEF_EAR_R = (142.0, 205.0), (368.0, 203.0)     # 耳朵中心
DEF_EARP_L, DEF_EARP_R = (166.0, 236.0), (344.0, 233.0)   # 耳根（旋轉軸）
DEF_FOOT_L, DEF_FOOT_R = (183.0, 462.0), (325.0, 461.0)
DEF_BODY_C, DEF_BODY_R = (254.0, 318.0), 190.0
DEF_RUST = "#ED8A66"       # 腳／肉掌色（取自原圖腳）
DEF_RUST_D = "#D2694B"
DEF_INK = "#140504"


def _components(mask: np.ndarray):
    """8 連通分塊（無 scipy）。回傳 [(像素數, x0, y0, x1, y1, 座標陣列)]。"""
    from collections import deque
    H, W = mask.shape
    lab = np.zeros((H, W), np.int32)
    out = []
    ys, xs = np.nonzero(mask)
    n = 0
    for y, x in zip(ys, xs):
        if lab[y, x]:
            continue
        n += 1
        q = deque([(y, x)])
        lab[y, x] = n
        pts = []
        while q:
            cy, cx = q.popleft()
            pts.append((cy, cx))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < H and 0 <= nx < W and mask[ny, nx] and not lab[ny, nx]:
                        lab[ny, nx] = n
                        q.append((ny, nx))
        p = np.array(pts)
        out.append((len(pts), p[:, 1].min(), p[:, 0].min(), p[:, 1].max(), p[:, 0].max(), p))
    return out


def _disk(shape, c, r):
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    return (xx - c[0]) ** 2 + (yy - c[1]) ** 2 <= r * r


def _inpaint(rgb: np.ndarray, mask: np.ndarray, iters=400) -> np.ndarray:
    """遮罩內的像素用四鄰平均反覆擴散（周圍毛色流進來），補平五官。"""
    out = rgb.copy()
    m = mask.copy()
    # 初值：遮罩外最近的奶油白
    out[m] = np.array([253, 246, 234], np.float32)
    for _ in range(iters):
        avg = (np.roll(out, 1, 0) + np.roll(out, -1, 0) + np.roll(out, 1, 1) + np.roll(out, -1, 1)) / 4
        out[m] = avg[m]
    return out


@lru_cache(None)
def default_assets() -> dict:
    """原版 Default 拆件（S 倍 RGBA）。"""
    from PIL import ImageFilter
    import sys as _s
    _s.path.insert(0, str(Path(__file__).parent))
    from gif_pipeline import _dilate, _flood

    rgb = np.asarray(Image.open(DEF_SRC).convert("RGB")).astype(np.float32)
    lum = rgb.mean(axis=2)
    fg = ~_flood(~(lum < 170))
    # 外緣 1px：從底色反混色
    ring = _dilate(fg, 1) & ~fg
    a = np.zeros(lum.shape, np.float32)
    a[fg] = 1.0
    ink = np.array([15, 3, 3], np.float32)
    bgl, inkl = DEF_BG.mean(), ink.mean()
    ra = np.clip((bgl - lum) / (bgl - inkl), 0, 1)
    a[ring] = ra[ring]
    col = rgb.copy()
    with np.errstate(divide="ignore", invalid="ignore"):
        un = (rgb - (1 - a[..., None]) * DEF_BG) / np.maximum(a[..., None], 1e-3)
    col[ring] = np.clip(un[ring], 0, 255)

    # 五官：深色分塊裡，落在眼／嘴位置的那幾塊
    dark = lum < 140
    comps = _components(dark & fg)
    face_dark = np.zeros_like(dark)
    parts = {"eye_l": np.zeros_like(dark), "eye_r": np.zeros_like(dark), "mouth": np.zeros_like(dark)}
    for n, x0, y0, x1, y1, p in comps:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        for key, c in (("eye_l", DEF_EYE_L), ("eye_r", DEF_EYE_R), ("mouth", DEF_MOUTH)):
            if abs(cx - c[0]) < 25 and abs(cy - c[1]) < 25 and n > 100:
                parts[key][p[:, 0], p[:, 1]] = True
    # 嘴內部（舌頭）＝嘴外框的凸包內非奶油色
    yy, xx = np.nonzero(parts["mouth"])
    mbox = np.zeros_like(dark)
    mbox[yy.min():yy.max() + 1, xx.min():xx.max() + 1] = True
    nonfur = (np.abs(rgb - np.array([253, 246, 234])).sum(axis=2) > 40)
    parts["mouth"] |= mbox & nonfur & fg
    r_, g_, b_ = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    peach = (r_ - b_ > 45) & fg
    blush = (_disk(dark.shape, DEF_BLUSH_L, 40) | _disk(dark.shape, DEF_BLUSH_R, 40)) & peach
    blush = _dilate(blush, 2) & fg & ~_dilate(parts["mouth"], 1)
    face = _dilate(parts["eye_l"] | parts["eye_r"] | parts["mouth"], 7) | _dilate(blush, 4)
    face &= fg & ~_dilate(~fg, 6)
    blank = _inpaint(col, face)

    def rgba(c, al):
        return Image.fromarray(np.dstack([np.clip(c, 0, 255), np.clip(al * 255, 0, 255)]).astype(np.uint8), "RGBA")

    def soft(m, r=1.2):
        im = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r))
        return np.asarray(im).astype(np.float32) / 255

    def up(im):
        return im.convert("RGBa").resize((SIZE * S, SIZE * S), Image.LANCZOS).convert("RGBA")

    out = {
        "full": up(rgba(col, a)),
        "blank": up(rgba(blank, a)),
        "blush": up(rgba(col, soft(_dilate(blush, 2)) * fg)),
        "eye_l": up(rgba(col, soft(_dilate(parts["eye_l"], 2), 0.8))),
        "eye_r": up(rgba(col, soft(_dilate(parts["eye_r"], 2), 0.8))),
        "mouth": up(rgba(col, soft(_dilate(parts["mouth"], 2), 0.8))),
        "masks": {k: v for k, v in parts.items()} | {"blush": blush, "face": face, "fg": fg},
    }
    return out


def _smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def def_matrix(p):
    """原圖像素 → 世界（512）：腳底中心對到 (x, y)，以腳底為錨擠壓／傾斜。"""
    return mat(p["x"], p["y"], p["rot"], p["sx"], p["sy"], p["shear"], DEF_FOOT[0], DEF_FOOT[1])


def def_pt(p, x, y):
    return apply(def_matrix(p), x, y)


def _def_local_inv(p):
    """原圖座標上的局部變形（反向）：耳朵繞耳根轉、腳平移、毛邊飄。回傳 f(x,y)->(sx,sy)（向量化）。"""
    ears = [(DEF_EAR_L, DEF_EARP_L, -p["ear"]), (DEF_EAR_R, DEF_EARP_R, p["ear2"])]
    # 大傾斜時耳朵自己調位置（CEO 10-11：傾斜 >18° 耳朵不能只跟著身體轉）：
    # 兩耳都往傾斜方向（頭頂移動方向）挪一點；背向那一耳縮小、收進毛裡一點。
    rot = p["rot"]
    tilt = max(0.0, abs(rot) - 8) * (1 if rot > 0 else -1)
    ear_tx = [0.55 * tilt + p.get("ear_tx", 0.0), 0.55 * tilt + p.get("ear_tx", 0.0)]
    ear_sc = [(1 - max(0.0, tilt) / 70) * p.get("ear_sc_l", 1.0), (1 - max(0.0, -tilt) / 70) * p.get("ear_sc_r", 1.0)]
    feet = [(DEF_FOOT_L, p["bf_far"]), (DEF_FOOT_R, p["bf_near"])]
    amp, ph = p["flutter"], p["fphase"]
    bx, by = DEF_BODY_C

    def f(X, Y):
        sx_, sy_ = X.copy(), Y.copy()
        # 耳朵：權重＝離耳朵中心近、且在頭頂（y 小於耳根下方一點）
        for k_, (ec, pv, ang) in enumerate(ears):
            tx, sc = ear_tx[k_], ear_sc[k_]
            if abs(ang) < 0.05 and abs(tx) < 0.05 and abs(sc - 1) < 0.005:
                continue
            d = np.hypot(X - ec[0] - tx, Y - ec[1])
            w = _smooth((78 - d) / 40) * _smooth((pv[1] + 22 - Y) / 30)
            th = np.radians(-ang) * w        # 反向旋轉
            c, s = np.cos(th), np.sin(th)
            dx, dy = (X - tx * w - pv[0]) / (1 + (sc - 1) * w), (Y - pv[1]) / (1 + (sc - 1) * w)
            sx_ += (c * dx - s * dy + pv[0]) - X
            sy_ += (s * dx + c * dy + pv[1]) - Y
        # 腳：在腳附近平移（反向：取 p - d·w，w 在「移過去的位置」估）
        for (fc, (fdx, fdy, frot)) in feet:
            if abs(fdx) + abs(fdy) < 0.05:
                continue
            for _ in range(2):
                d = np.hypot((X - fdx) - fc[0], (Y - fdy) - fc[1] * 1.0)
                w = _smooth((52 - d) / 26) * _smooth((Y - (fc[1] - 40)) / 20 + 0.0 * d)
            sx_ -= fdx * w
            sy_ -= fdy * w
        # 臉頰鼓起（嚼東西）：腮紅那一圈高度的兩側輪廓往外鼓
        ck = p.get("cheek", 0.0)
        if ck > 0.01:
            band = _smooth(1 - np.abs(Y - 300) / 70)
            side = _smooth((np.abs(X - bx) - 90) / 90)
            sx_ += -np.sign(X - bx) * ck * 16 * band * side
        # 毛邊飄（正面）：頭頂的毛往下壓（amp>0）或往上蓬（amp<0）、兩側毛往外抖
        if abs(amp) > 0.01:
            r = np.hypot(X - bx, Y - by)
            edge = _smooth((r - (DEF_BODY_R - 60)) / 50)
            top = _smooth((by - 40 - Y) / 80)
            wav = 0.65 + 0.35 * np.sin(ph + X * 0.05)
            sy_ += -amp * top * edge * wav
            side = _smooth((np.abs(X - bx) - 120) / 60)
            sx_ += -amp * 0.45 * side * edge * np.sign(X - bx) * (0.6 + 0.4 * np.sin(ph * 1.4 + Y * 0.04))
        return sx_, sy_

    return f


def def_body_layer(p, grid=64) -> Image.Image:
    """把無五官本體依姿勢畫到 S 倍畫布：輸出像素 → 世界 → 原圖（反仿射）→ 局部變形（反向）→ 取樣。"""
    A = default_assets()
    src = A["blank"]
    W = SIZE * S
    Minv = np.linalg.inv(def_matrix(p))
    loc = _def_local_inv(p)
    xs = np.linspace(0, W, grid + 1)
    X, Y = np.meshgrid(xs, xs)
    wx, wy = X / S, Y / S
    ox = Minv[0, 0] * wx + Minv[0, 1] * wy + Minv[0, 2]
    oy = Minv[1, 0] * wx + Minv[1, 1] * wy + Minv[1, 2]
    lx, ly = loc(ox, oy)
    lx, ly = lx * S, ly * S
    data = []
    for j in range(grid):
        for i in range(grid):
            box = (int(xs[i]), int(xs[j]), int(math.ceil(xs[i + 1])), int(math.ceil(xs[j + 1])))
            q = (lx[j, i], ly[j, i], lx[j + 1, i], ly[j + 1, i], lx[j + 1, i + 1], ly[j + 1, i + 1],
                 lx[j, i + 1], ly[j, i + 1])
            data.append((box, q))
    return src.convert("RGBa").transform((W, W), Image.MESH, data, resample=Image.BICUBIC).convert("RGBA")


def def_layer_affine(im: Image.Image, p) -> Image.Image:
    """原圖座標的一層（S 倍）跟著本體仿射走。"""
    M = def_matrix(p)
    Sm = np.diag([S, S, 1.0])
    return warp_affine(im, Sm @ M @ np.linalg.inv(Sm))


def motion_marks_svg(x, y, side=1, s=1.0, n=2) -> str:
    """身體旁的小弧形動作線（原版跳躍參考圖那種）：side=1 畫在右邊（弧往右彎）。"""
    out = []
    for i in range(n):
        yy = y + i * 22 * s
        xx = x + side * i * 6 * s
        out.append(f'<path d="M {xx:.1f} {yy-10*s:.1f} Q {xx + side*9*s:.1f} {yy:.1f} {xx:.1f} {yy+10*s:.1f}" fill="none" '
                   f'stroke="{DEF_INK}" stroke-width="{5*s:.1f}" stroke-linecap="round"/>')
    return "".join(out)


def drop_lines_svg(x, y, n=3, gap=26, L=26) -> str:
    """身體下方的短直線（往上跳時的速度線）。"""
    return "".join(f'<path d="M {x + (i-(n-1)/2)*gap:.1f} {y:.1f} L {x + (i-(n-1)/2)*gap:.1f} {y+L:.1f}" stroke="{DEF_INK}" '
                   f'stroke-width="5" stroke-linecap="round"/>' for i in range(n))


def def_paw_svg(x, y, rot=0.0, s=1.0) -> str:
    """原版風格的小肉掌（跟腳同色：橘粉、深色粗描邊、根部留缺口、兩道趾線）。(x,y) 掌心，rot＝指尖方向（0 朝上）。"""
    return f'''<g transform="translate({x:.1f},{y:.1f}) rotate({rot:.1f}) scale({s:.3f})">
  <path d="M -15 14 C -20 0 -17 -16 -6 -20 C 3 -23 13 -19 16 -8 C 19 3 16 13 13 17 Z" fill="{DEF_RUST}"/>
  <path d="M -15 14 C -20 0 -17 -16 -6 -20 C 3 -23 13 -19 16 -8 C 19 3 16 13 13 17" fill="none" stroke="{DEF_INK}"
        stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M -4 -19 L -3 -11 M 6 -18 L 5 -10" stroke="{DEF_INK}" stroke-width="3.6" stroke-linecap="round"/>
</g>'''


def def_eye_svg(kind, x, y, s=1.0) -> str:
    """原版尺寸的補畫眼（原版圓點眼約 25×28、描邊約 6px）。"""
    k = s * 1.9
    if kind == "arc":      # ^ 彎月（開心）
        return (f'<path d="M {x-10*k:.1f} {y+4*k:.1f} Q {x:.1f} {y-8*k:.1f} {x+10*k:.1f} {y+4*k:.1f}" fill="none" '
                f'stroke="{DEF_INK}" stroke-width="{6.5*s:.1f}" stroke-linecap="round"/>')
    if kind == "smile":    # ‿ 閉眼笑
        return (f'<path d="M {x-10*k:.1f} {y-3*k:.1f} Q {x:.1f} {y+8*k:.1f} {x+10*k:.1f} {y-3*k:.1f}" fill="none" '
                f'stroke="{DEF_INK}" stroke-width="{6.5*s:.1f}" stroke-linecap="round"/>')
    if kind == "squeeze_l":   # > （瞇眼用力，左眼）
        return (f'<path d="M {x-8*k:.1f} {y-7*k:.1f} L {x+7*k:.1f} {y:.1f} L {x-8*k:.1f} {y+7*k:.1f}" fill="none" '
                f'stroke="{DEF_INK}" stroke-width="{6.5*s:.1f}" stroke-linecap="round" stroke-linejoin="round"/>')
    if kind == "squeeze_r":   # <
        return (f'<path d="M {x+8*k:.1f} {y-7*k:.1f} L {x-7*k:.1f} {y:.1f} L {x+8*k:.1f} {y+7*k:.1f}" fill="none" '
                f'stroke="{DEF_INK}" stroke-width="{6.5*s:.1f}" stroke-linecap="round" stroke-linejoin="round"/>')
    if kind == "star":
        return star_svg(x, y, 22 * s, 0, "#FFD25A").replace('stroke-width="3.5"', 'stroke-width="5"')
    if kind == "wide":
        return (f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{8*k:.1f}" ry="{9*k:.1f}" fill="{DEF_INK}"/>'
                f'<circle cx="{x-3*k:.1f}" cy="{y-3.5*k:.1f}" r="{2.8*k:.1f}" fill="#fff"/>')
    if kind == "closed":
        return (f'<path d="M {x-9*k:.1f} {y:.1f} Q {x:.1f} {y+4*k:.1f} {x+9*k:.1f} {y:.1f}" fill="none" '
                f'stroke="{DEF_INK}" stroke-width="{6*s:.1f}" stroke-linecap="round"/>')
    return eye_svg(kind, x, y, k)


def def_mouth_svg(kind, x, y, s=1.0) -> str:
    """原版尺寸的補畫嘴（原版嘴寬約 60、描邊約 6px）。"""
    k = s * 2.3
    sw = 6.2 * s
    if kind == "w":     # ω 閉嘴笑
        return (f'<path d="M {x-12*k:.1f} {y-4*k:.1f} Q {x-6*k:.1f} {y+6*k:.1f} {x:.1f} {y-2*k:.1f} Q {x+6*k:.1f} {y+6*k:.1f} '
                f'{x+12*k:.1f} {y-4*k:.1f}" fill="none" stroke="{DEF_INK}" stroke-width="{sw:.1f}" stroke-linecap="round" '
                f'stroke-linejoin="round"/>')
    if kind == "smile":   # 張嘴笑（D 形＋舌）
        return (f'<path d="M {x-11*k:.1f} {y-5*k:.1f} Q {x:.1f} {y-2*k:.1f} {x+11*k:.1f} {y-5*k:.1f} Q {x+9*k:.1f} {y+9*k:.1f} '
                f'{x:.1f} {y+9*k:.1f} Q {x-9*k:.1f} {y+9*k:.1f} {x-11*k:.1f} {y-5*k:.1f} Z" fill="#6E1E16" stroke="{DEF_INK}" '
                f'stroke-width="{sw:.1f}" stroke-linejoin="round"/>'
                f'<path d="M {x-6*k:.1f} {y+6*k:.1f} Q {x:.1f} {y+1*k:.1f} {x+6*k:.1f} {y+6*k:.1f} Q {x:.1f} {y+9.5*k:.1f} '
                f'{x-6*k:.1f} {y+6*k:.1f} Z" fill="#F08A72"/>')
    if kind == "o":
        return (f'<ellipse cx="{x:.1f}" cy="{y+2*k:.1f}" rx="{5.5*k:.1f}" ry="{7*k:.1f}" fill="#6E1E16" stroke="{DEF_INK}" '
                f'stroke-width="{sw:.1f}"/><ellipse cx="{x:.1f}" cy="{y+6*k:.1f}" rx="{3.2*k:.1f}" ry="{2.2*k:.1f}" fill="#F08A72"/>')
    if kind == "big":     # 大張嘴（驚喜、歡呼）
        return (f'<path d="M {x-12*k:.1f} {y-5*k:.1f} Q {x:.1f} {y-3*k:.1f} {x+12*k:.1f} {y-5*k:.1f} Q {x+11*k:.1f} {y+14*k:.1f} '
                f'{x:.1f} {y+14*k:.1f} Q {x-11*k:.1f} {y+14*k:.1f} {x-12*k:.1f} {y-5*k:.1f} Z" fill="#6E1E16" '
                f'stroke="{DEF_INK}" stroke-width="{sw:.1f}" stroke-linejoin="round"/>'
                f'<path d="M {x-7*k:.1f} {y+10*k:.1f} Q {x:.1f} {y+3*k:.1f} {x+7*k:.1f} {y+10*k:.1f} Q {x:.1f} {y+14*k:.1f} '
                f'{x-7*k:.1f} {y+10*k:.1f} Z" fill="#F08A72"/>')
    if kind.startswith("chew"):
        return mouth_svg(kind, x, y, s * 2.9).replace('stroke-width="10.4"', 'stroke-width="6.5"')
    return mouth_svg(kind, x, y, k)


def compose_default(p: dict, props_back=None, props_mid=None, props_front=None, fx=None, shadow=True):
    """原版 Default 造型合成一格（正面）。p 同 DEFAULT 的鍵；eye='default'／mouth='default' 用原圖像素。
    回傳 (S 倍畫布, boxes)（boxes['__masks'] 給重疊檢查）。"""
    p = {**DEFAULT, "eye": "default", "mouth": "default", "paws": None, **p}
    W = SIZE * S
    can = Image.new("RGBA", (W, W))
    boxes, masks = {}, {}
    A = default_assets()

    def put(lst, tag):
        for i, it in enumerate(lst or []):
            if isinstance(it, Image.Image):
                lay = it
            else:
                im, x, y, r, anc = it
                lay = Image.new("RGBA", (W, W))
                place(lay, im, x, y, r, anchor=anc)
            bb = lay.getchannel("A").getbbox()
            if bb:
                boxes[f"{tag}{i}"] = bb
                masks[f"{tag}{i}"] = lay.getchannel("A")
            can.alpha_composite(lay)

    # 地面影子：跳越高越小越淡
    lift = max(0.0, R_FOOT() - p["y"])
    if shadow:
        k = max(0.35, 1 - lift / 160)
        can.alpha_composite(svg_layer(
            f'<ellipse cx="{p["x"] + 2:.1f}" cy="{R_FOOT() - 1:.1f}" rx="{152 * k * min(1.15, p["sx"]):.1f}" '
            f'ry="{12 * k:.1f}" fill="rgb(110,80,60)" fill-opacity="{0.27 * (0.45 + 0.55 * k):.2f}"/>'))
    put(props_back, "propB")
    body = def_body_layer(p)
    boxes["body"] = body.getchannel("A").getbbox()
    can.alpha_composite(body)
    put(props_mid, "propM")

    # 臉：腮紅（原像素，可加濃）→ 眼 → 嘴
    lu, lv = p["look"]
    off = (lu * 380, lv * 330)    # look 以身寬比例平移五官

    back = p["view"] == "back"
    q3 = p["view"] == "q3"     # 3/4 側（面向左）：五官往左偏、右邊（遠側）的眼和腮紅變窄
    if q3 and abs(lu) < 0.01:
        lu = -0.13
        off = (lu * 380, lv * 330)

    def shifted(im, far=None, fac=1.0):
        if abs(off[0]) + abs(off[1]) < 0.01 and far is None:
            return im
        if far is None and fac != 1.0:
            return im.transform(im.size, Image.AFFINE, (1, 0, -off[0] * fac * S, 0, 1, -off[1] * S), resample=Image.BICUBIC)
        if far is not None and q3:      # 遠側：以那個部件中心水平壓窄到 0.7
            cx_ = far[0] * S
            k_ = 0.7
            return im.transform(im.size, Image.AFFINE,
                                (1 / k_, 0, cx_ - cx_ / k_ - off[0] * S / k_ * 0 - (off[0] * 1.15) * S / k_, 0, 1, -off[1] * S),
                                resample=Image.BICUBIC)
        return im.transform(im.size, Image.AFFINE, (1, 0, -off[0] * S, 0, 1, -off[1] * S), resample=Image.BICUBIC)

    if back:     # 背面：無五官本體＝背影，加一小團尾巴毛
        tx_, ty_, tr_ = p["tail"]
        X, Y = def_pt(p, DEF_FOOT[0], 400)
        place(can, tail_img(1.25), X + tx_, Y + ty_, tr_, anchor=(0.5, 0.5))
    if p["blush"] > 0.01 and not back:
        if q3:
            half = Image.new("L", A["blush"].size, 0)
            from PIL import ImageDraw as _D
            _D.Draw(half).rectangle((0, 0, int(DEF_FOOT[0] * S), SIZE * S), fill=255)
            a0 = A["blush"].getchannel("A")
            left = A["blush"].copy(); left.putalpha(Image.fromarray(np.minimum(np.asarray(a0), np.asarray(half))))
            right = A["blush"].copy(); right.putalpha(Image.fromarray(np.minimum(np.asarray(a0), 255 - np.asarray(half))))
            bl = shifted(left, fac=0.5)    # 近側腮紅貼著臉的輪廓，挪少一點
            bl.alpha_composite(shifted(right, DEF_BLUSH_R))
        else:
            bl = shifted(A["blush"])
        if p["blush"] < 0.99:
            a_ = bl.getchannel("A").point(lambda v: int(v * p["blush"]))
            bl = bl.copy(); bl.putalpha(a_)
        bl = def_layer_affine(bl, p)
        # 腮紅只畫在身體裡面（扣掉描邊）：不會凸出輪廓
        ba = np.asarray(body.getchannel("A")).astype(np.float32)
        inner = np.asarray(Image.fromarray(ba.astype(np.uint8)).filter(__import__("PIL.ImageFilter", fromlist=["x"]).MinFilter(31))).astype(np.float32) / 255
        bl.putalpha(Image.fromarray((np.asarray(bl.getchannel("A")) * inner).astype(np.uint8)))
        can.alpha_composite(bl)
        if p["blush"] > 1.05:   # 臉更紅：再疊一層半透明桃紅
            extra = ""
            for c in (DEF_BLUSH_L, DEF_BLUSH_R):
                X, Y = def_pt(p, c[0] + off[0], c[1] + off[1])
                extra += (f'<ellipse cx="{X:.1f}" cy="{Y:.1f}" rx="{30 * p["sx"]:.1f}" ry="{27 * p["sy"]:.1f}" '
                          f'transform="rotate({p["rot"]:.1f} {X:.1f} {Y:.1f})" '
                          f'fill="#F4735A" fill-opacity="{min(0.4, 0.35 * (p["blush"] - 1)):.2f}"/>')
            can.alpha_composite(svg_layer(extra))
    face = Image.new("RGBA", (W, W))
    if back:
        pass
    elif p["eye"] == "default" and p["eye_open"] > 0.5:
        face.alpha_composite(def_layer_affine(shifted(A["eye_l"]), p))
        face.alpha_composite(def_layer_affine(shifted(A["eye_r"], DEF_EYE_R if q3 else None), p))
    else:
        kind = "closed" if (p["eye"] == "default" or p["eye_open"] <= 0.5) else p["eye"]
        sv = ""
        for c, side in ((DEF_EYE_L, "l"), (DEF_EYE_R, "r")):
            fo = off[0] * (1.15 if (q3 and side == "r") else 1.0)
            X, Y = def_pt(p, c[0] + fo, c[1] + off[1])
            kk = kind
            if kind == "squeeze":
                kk = "squeeze_l" if side == "l" else "squeeze_r"
            if kind == "wink":
                kk = "default_dot" if side == "l" else "arc"
            if kk == "default_dot":
                continue
            sv += def_eye_svg(kk, X, Y)
        face.alpha_composite(svg_layer(sv))
        if kind == "wink":
            face.alpha_composite(def_layer_affine(shifted(A["eye_l"]), p))
    # 張嘴笑一律用原版小舌頭嘴的原像素（CEO 10-11：不要大一號）；big＝同一張嘴往下拉長一點（驚喜、歡呼）
    if back:
        pass
    elif p["mouth"] in ("default", "smile", "open"):
        face.alpha_composite(def_layer_affine(shifted(A["mouth"]), p))
    elif p["mouth"] == "big":
        mx_, my_ = DEF_MOUTH[0] * S, (DEF_MOUTH[1] - 26) * S
        Mb = mat(mx_, my_, 0, 1.06, 1.3, 0, mx_, my_)
        face.alpha_composite(def_layer_affine(warp_affine(shifted(A["mouth"]), Mb), p))
    elif p["mouth"] != "none":
        X, Y = def_pt(p, DEF_MOUTH[0] + off[0], DEF_MOUTH[1] - 6 + off[1])
        face.alpha_composite(svg_layer(def_mouth_svg(p["mouth"], X, Y)))
    # 五官只畫在身體裡面（轉身、3/4 時靠邊的眼不會壓到描邊外）
    ba_ = Image.fromarray(np.asarray(body.getchannel("A"))).filter(
        __import__("PIL.ImageFilter", fromlist=["x"]).MinFilter(17))
    face.putalpha(Image.fromarray(np.minimum(np.asarray(face.getchannel("A")), np.asarray(ba_))))
    bb = face.getchannel("A").getbbox()
    if bb:
        boxes["face"] = bb
        masks["face"] = face.getchannel("A")
    can.alpha_composite(face)

    # 小肉掌（原版平常看不到手；要舉手、捧東西時才從身體邊緣冒出來）
    if p.get("paws_world"):          # 直接給世界座標（例如捧草：跟著草走）
        sv = "".join(def_paw_svg(x_, y_, r_, 1.3) for x_, y_, r_ in p["paws_world"])
        can.alpha_composite(svg_layer(sv))
    elif p["paws"]:
        sv = ""
        for (u, v, dx, dy, r) in p["paws"]:
            X, Y = def_pt(p, u, v)
            sv += def_paw_svg(X + dx, Y + dy, r + p["rot"], 1.3)
        can.alpha_composite(svg_layer(sv))
    put(props_front, "propF")
    for i, piece in enumerate([fx] if isinstance(fx, str) else (fx or [])):
        if not piece:
            continue
        fl = svg_layer(piece)
        bb = fl.getchannel("A").getbbox()
        if bb:
            boxes[f"fx{i}"] = bb
            masks[f"fx{i}"] = fl.getchannel("A")
        can.alpha_composite(fl)
    # 整組旋轉（抱球翻滾）與面向右（鏡像）
    M = np.eye(3)
    if abs(p["grot"]) > 0.01 or abs(p["gx"]) > 0.01 or abs(p["gy"]) > 0.01:
        M = mat((p["gpx"] + p["gx"]) * S, (p["gpy"] + p["gy"]) * S, p["grot"], 1, 1, 0, p["gpx"] * S, p["gpy"] * S)
    if p["facing"] == "right":
        M = np.array([[-1, 0, 2 * CX * S], [0, 1, 0], [0, 0, 1.0]]) @ M
    if not np.allclose(M, np.eye(3)):
        can = warp_affine(can, M, can.size)
        boxes = {k: _tf_box(v, M) for k, v in boxes.items() if v}
        inv = np.linalg.inv(M)
        data = (inv[0, 0], inv[0, 1], inv[0, 2], inv[1, 0], inv[1, 1], inv[1, 2])
        masks = {k: m.transform(can.size, Image.AFFINE, data, resample=Image.BILINEAR) for k, m in masks.items()}
    boxes["__masks"] = {k: np.asarray(m.reduce(4)) > 40 for k, m in masks.items()}
    return can, boxes


def R_FOOT():
    return FOOT_Y


# ---------------------------------------------------------------- v1 姿勢 → 原版骨架
_EYE_MAP = {"dot": "default", "squint": "squeeze"}
_MOUTH_MAP = {"w": "w", "o": "o", "smile": "default", "open": "default", "flat": "w"}
DEF_SCALE = 385 / BODY_W          # 原版身寬 ÷ v1 身寬：肢體位移等比放大


def to_default_pose(p: dict) -> dict:
    """把 v1（總表骨架）的姿勢參數換成原版骨架：side→3/4 側、dot→原圖眼、張嘴→原圖小舌頭嘴；
    手（fp_far/fp_near）只有真的動了或捧在胸前才畫成貼身小肉掌（原版平常看不到手）。"""
    q = dict(p)
    v = q.get("view", "front")
    if v == "side":
        q.update(view="q3", ear_tx=22, ear_sc_r=0.8)
    q["eye"] = _EYE_MAP.get(q.get("eye", "dot"), q.get("eye", "dot"))
    q["mouth"] = _MOUTH_MAP.get(q.get("mouth", "w"), q.get("mouth", "w"))
    if "shear" in q:
        q["shear"] = q["shear"] * 0.5      # 原版身體大一號，剪切減半免得出框
    paws = []
    hf = q.pop("hands_front", False)
    for key, side in (("fp_far", -1), ("fp_near", 1)):
        dx, dy, r = q.pop(key, (0.0, 0.0, 0.0))
        if hf:
            paws.append((DEF_FOOT[0] + side * 44, 404, dx * DEF_SCALE * 0.6, dy * DEF_SCALE * 0.8, r))
        elif abs(dx) + abs(dy) > 3 and v != "side":    # 側跑／撲球不畫前掌：小腳＋身體就夠（原版質感）
            u = 70 if side < 0 else 438
            if v == "side":   # 3/4 側：前掌在前下方
                u = 120 if side < 0 else 200
            # 身體是圓的：肉掌往上舉時沿著輪廓往內收（不會飄到身體外面）
            ddx = dx * 1.05 - side * 0.32 * max(0.0, -dy * DEF_SCALE)
            paws.append((u, 352 if v != "side" else 430, ddx, dy * DEF_SCALE, r + (-50 if side < 0 else 50)))
    q["paws"] = paws or None
    for key in ("bf_far", "bf_near"):
        if key in q:
            dx, dy, r = q[key]
            q[key] = (dx * DEF_SCALE * 0.8, dy * DEF_SCALE * 0.8, r)
    return q
