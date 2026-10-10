"""動畫設計單位：吉祥物「比比」5 組新動作（揮手／指向／歪頭疑問／驚嘆／舉牌），每組 12 格、512×512、透明。

為什麼有這支
------------
宣傳影片 `docs/marketing/video_1010/storyboard.md` 第 4 節要 5 組原圖沒有的動作。
Andy 的總控規格（docs/anim/prompt_kit/01_總控Prompt.md）：raster_first、不准用生硬幾何重畫角色、
不准用疊圖或重複影格冒充補間；原圖沒有的部位才用 SVG 三次 Bézier 補繪、放大繪製再 LANCZOS 縮回。

做法
----
1. 身體：一律用原圖 `site/brand/src/support_anim_1009.gif` 的像素（第 0 張待機），沿用
   `pose_tween.warp_body` 的網格變形做擠壓／拉長／旋轉／頭頂毛慣性 —— 角色本體不重畫。
2. 補繪：手臂（毛茸茸的短手＋棕粉色肉掌）、牌子、「？」「！」、動作線、閃光，用 SVG 三次 Bézier 路徑，
   配色從原圖取樣（描邊 #1A0907、毛色 #FDF5E9、陰影 #F8E2CF、肉掌 #E07E5E／#C55E44），
   描邊粗細＝原圖描邊（約 7.5px）× 身體縮放，以 4 倍（2048）由 cairosvg 繪製，最後一次 LANCZOS 縮回 512。
3. 手臂接身體：手臂的毛色填滿會蓋掉肩膀處的身體描邊，手臂描邊落在身體內部的部分用「身體 alpha 內縮」遮掉，
   看起來是從身體長出來，不是貼片。
4. 補繪的部位位置用「原圖座標 → 場景座標」的正向映射算（跟身體同一組網格變形），身體壓扁或歪頭時手會跟著走。
5. 全部 5 組同一場景座標：身體縮 0.75、中心 x=248、腳底 y=482（跟 jump 的待機格同一隻、同比例縮放）。

用法
----
    python scripts/anim/bibi_actions.py --out <scratchpad>/bibi --repo-out docs/anim
輸出：<out>/<動作>/frames/frame_01.png…、<repo-out>/bibi_<動作>/sheet_12.png、anim.webp；<out>/index.json。
"""
from __future__ import annotations

import argparse
import io
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
import pose_tween  # noqa: E402

import cairosvg  # noqa: E402

SIZE = 512
SS = 4                     # 補繪與網格變形的超取樣倍數
pose_tween.SS = SS         # 只影響這支呼叫的 warp_body（jump 的輸出照舊用它自己的 SS=2）

# ---- 原圖取樣的顏色
INK = "#1A0907"
FUR = "#FDF5E9"
FUR_SH = "#F6E0CB"
PAW = "#E07E5E"
PAW_DK = "#C55E44"
PAW_LT = "#EE9C7E"
BLUSH = "#F9AB8C"
SPARK = "#F9C23C"

# ---- 場景座標（5 組共用）
SCALE = 0.75
CX, GROUND = 248.0, 482.0
OUT_W = 7.5 * SCALE        # 描邊粗細（原圖描邊約 7～8px）


# ================================================================== 幾何
def base_geom(poses, src=0, **kw):
    x0, y0, x1, y1 = poses[src]["box"]
    g = {"src": src, "cx": CX, "bottom": GROUND, "w": (x1 - x0) * SCALE, "h": (y1 - y0) * SCALE,
         "rot": 0.0, "lag": 0.0}
    for k, v in kw.items():
        if k in ("w", "h"):
            g[k] *= v                      # w／h 給倍率
        elif k in ("cx", "bottom"):
            g[k] += v                      # cx／bottom 給位移
        else:
            g[k] = v
    return g


def fwd(poses, g, px, py):
    """原圖座標 → 場景座標（warp_body 的正向）。"""
    x0, y0, x1, y1 = poses[g["src"]]["box"]
    sw, sh = x1 - x0, y1 - y0
    sax, say = (x0 + x1) / 2, y1
    sx = g["w"] / sw
    ur = (px - sax) * sx
    ts = (say - py) / sh
    lag = g.get("lag", 0.0)
    th = ts + lag * ts * (1 - ts) if 0 <= ts <= 1 else ts
    vr = -th * g["h"]
    r = math.radians(g.get("rot", 0.0))
    # warp_body 的逆：u_r = c*u + s*v, v_r = -s*u + c*v → 正向：u = c*u_r - s*v_r, v = s*u_r + c*v_r
    u = math.cos(r) * ur - math.sin(r) * vr
    v = math.sin(r) * ur + math.cos(r) * vr
    return g["cx"] + u, g["bottom"] + v


BODY_C = (254, 330)   # 原圖身體中心


def shoulder(poses, g, src_pt, depth=24.0):
    """肩膀錨點：身體邊上那一點往身體中心內縮 depth（場景 px），手臂從身體裡面長出來，接縫藏在毛裡。"""
    a = fwd(poses, g, *src_pt); c = fwd(poses, g, *BODY_C)
    v = (c[0] - a[0], c[1] - a[1]); n = math.hypot(*v)
    return (a[0] + v[0] / n * depth, a[1] + v[1] / n * depth)


def body_angle(g):
    """身體在畫面上的順時針旋轉角（度）：warp 的 rot 正值＝畫面上順時針。"""
    return g.get("rot", 0.0)


# ================================================================== SVG 小工具
def f(x):
    return f"{x:.2f}"


def P(pt):
    return f"{f(pt[0])},{f(pt[1])}"


def rot2(v, deg):
    r = math.radians(deg)
    return (v[0] * math.cos(r) - v[1] * math.sin(r), v[0] * math.sin(r) + v[1] * math.cos(r))


def add(a, b, k=1.0):
    return (a[0] + b[0] * k, a[1] + b[1] * k)


def dirv(deg):
    """畫面角度（0＝往右，90＝往上）→ 單位向量（SVG y 向下）。"""
    r = math.radians(deg)
    return (math.cos(r), -math.sin(r))


def limb_paths(anchor, deg, length, hw_root=23.0, hw_tip=19.0, root_in=0.0, seed=0, bumps=0.9):
    """毛茸茸短手臂：回傳 (fill_path, outline_path, tip)。
    兩側邊用連續三次 Bézier 扇貝（毛邊），尖端是圓弧（之後被肉掌蓋住）。"""
    d = dirv(deg)
    n = (-d[1], d[0])            # 左法線（畫面上）
    rng = np.random.default_rng(seed)
    x_start, x_end = -root_in, length
    seg = 4
    xs = np.linspace(x_start, x_end, seg + 1)

    def hw(x):
        t = (x - x_start) / (x_end - x_start)
        return hw_root + (hw_tip - hw_root) * t

    def pt(x, side, extra=0.0):
        return add(add(anchor, d, x), n, side * (hw(x) + extra))

    def side_path(side, xs_):
        cmds = []
        for a, b in zip(xs_[:-1], xs_[1:]):
            amp = bumps * (2.2 + rng.uniform(0, 1.6))
            c1 = add(pt(a + (b - a) * 0.25, side, amp), d, 0)
            c2 = pt(a + (b - a) * 0.80, side, amp * 1.1)
            e = pt(b, side, rng.uniform(-0.6, 0.4))
            cmds.append(f"C {P(c1)} {P(c2)} {P(e)}")
        return cmds

    up = side_path(+1, xs)
    tipc = add(anchor, d, length)
    r_t = hw_tip
    # 尖端半圓（兩段三次 Bézier，k=0.5523）
    k = 0.5523 * r_t
    a0 = add(tipc, n, r_t)
    mid = add(tipc, d, r_t)
    a1 = add(tipc, n, -r_t)
    tip_cmds = [f"C {P(add(a0, d, k))} {P(add(mid, n, k))} {P(mid)}",
                f"C {P(add(mid, n, -k))} {P(add(a1, d, k))} {P(a1)}"]
    down = side_path(-1, xs[::-1])
    start = pt(x_start, +1)
    fill = f"M {P(start)} " + " ".join(up + tip_cmds + down) + " Z"
    outline = f"M {P(start)} " + " ".join(up + tip_cmds + down)
    return fill, outline, tipc


def paw_svg(c, deg, r=12.0, open_side=None, squash=0.86, seed=0, spots=True):
    """肉掌：不規則圓（四段三次 Bézier）＋暗色斑＋亮點＋ C 形手繪描邊（留一個缺口，像原圖）。
    deg＝掌心朝向（畫面角度），open_side＝描邊缺口朝向（預設朝手臂那側＝deg+180）。"""
    rng = np.random.default_rng(seed + 11)
    d = dirv(deg)
    n = (-d[1], d[0])
    rx, ry = r * 1.06, r * squash
    pts = []
    for i in range(4):
        a = math.radians(i * 90)
        jit = 1 + rng.uniform(-0.06, 0.06)
        pts.append(add(add(c, d, math.cos(a) * rx * jit), n, math.sin(a) * ry * jit))
    kk = 0.5523
    segs = []
    for i in range(4):
        p0, p1 = pts[i], pts[(i + 1) % 4]
        a0, a1 = math.radians(i * 90), math.radians((i + 1) * 90)
        t0 = add((0, 0), add((d[0] * -math.sin(a0) * rx, d[1] * -math.sin(a0) * rx),
                             (n[0] * math.cos(a0) * ry, n[1] * math.cos(a0) * ry)))
        t1 = add((0, 0), add((d[0] * -math.sin(a1) * rx, d[1] * -math.sin(a1) * rx),
                             (n[0] * math.cos(a1) * ry, n[1] * math.cos(a1) * ry)))
        segs.append(f"C {P(add(p0, t0, kk))} {P(add(p1, t1, -kk))} {P(p1)}")
    blob = f"M {P(pts[0])} " + " ".join(segs) + " Z"
    # 描邊：從缺口一側繞 260° 到另一側
    gap = (deg + 180) if open_side is None else open_side
    a_start = math.radians(gap + 55)
    pts2 = []
    for j in range(28):
        a = a_start + math.radians(250) * j / 27
        rr = 1.0 + 0.04 * math.sin(j * 1.7 + seed)
        # 用畫面角度（不是掌心座標）走一圈
        pts2.append((c[0] + math.cos(a) * rx * rr, c[1] - math.sin(a) * ry * rr * (1 / squash) * squash))
    stroke = "M " + P(pts2[0]) + " " + " ".join(
        f"Q {P(pts2[i])} {P(((pts2[i][0] + pts2[i + 1][0]) / 2, (pts2[i][1] + pts2[i + 1][1]) / 2))}"
        for i in range(1, len(pts2) - 1)) + f" L {P(pts2[-1])}"
    out = [f'<path d="{blob}" fill="{PAW}"/>']
    if spots:
        s1 = add(add(c, d, -r * 0.25), n, r * 0.30)
        out.append(f'<ellipse cx="{f(s1[0])}" cy="{f(s1[1])}" rx="{f(r*0.32)}" ry="{f(r*0.24)}" fill="{PAW_DK}" opacity="0.75"/>')
        s2 = add(add(c, d, r * 0.35), n, -r * 0.35)
        out.append(f'<ellipse cx="{f(s2[0])}" cy="{f(s2[1])}" rx="{f(r*0.22)}" ry="{f(r*0.16)}" fill="{PAW_LT}" opacity="0.9"/>')
    out.append(f'<path d="{stroke}" fill="none" stroke="{INK}" stroke-width="{f(OUT_W*0.95)}" '
               f'stroke-linecap="round" stroke-linejoin="round"/>')
    return "\n".join(out)


def brush(pts, w0, w1=None, color=INK):
    """手繪筆刷：沿著點列做「兩頭尖、中間粗」的實心多邊形（比定寬 stroke 更像原圖的線）。"""
    w1 = w0 if w1 is None else w1
    pts = np.asarray(pts, float)
    n = len(pts)
    L, R = [], []
    for i in range(n):
        a = pts[max(i - 1, 0)]; b = pts[min(i + 1, n - 1)]
        t = b - a; t = t / (np.hypot(*t) + 1e-9)
        nn = np.array([-t[1], t[0]])
        s = i / (n - 1)
        w = (w0 + (w1 - w0) * s) * (0.45 + 0.55 * math.sin(math.pi * min(max(s, 0.0), 1.0)) ** 0.6)
        L.append(pts[i] + nn * w / 2); R.append(pts[i] - nn * w / 2)
    poly = L + R[::-1]
    d = "M " + " L ".join(P(p) for p in poly) + " Z"
    cap0 = f'<circle cx="{f(pts[0][0])}" cy="{f(pts[0][1])}" r="{f(w0*0.24)}" fill="{color}"/>'
    cap1 = f'<circle cx="{f(pts[-1][0])}" cy="{f(pts[-1][1])}" r="{f(w1*0.24)}" fill="{color}"/>'
    return f'<path d="{d}" fill="{color}"/>' + cap0 + cap1


def bez(p0, p1, p2, p3, n=24):
    out = []
    for i in range(n):
        t = i / (n - 1); mt = 1 - t
        out.append((mt**3 * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t**3 * p3[0],
                    mt**3 * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t**3 * p3[1]))
    return out


def xf(pts, c, k, deg):
    return [add(c, rot2((p[0] * k, p[1] * k), deg)) for p in pts]


def qmark(c, k=1.0, deg=0.0):
    """「？」：兩段三次 Bézier 的鉤＋圓點，粗黑筆刷。"""
    hook = bez((-15, -18), (-15, -44), (20, -46), (18, -22), 22) + \
        bez((18, -22), (17, -10), (2, -9), (2, 6), 14)[1:]
    pts = xf(hook, c, k, deg)
    dot = xf([(2, 22)], c, k, deg)[0]
    return brush(pts, 11 * k, 9 * k) + f'<circle cx="{f(dot[0])}" cy="{f(dot[1])}" r="{f(5.6*k)}" fill="{INK}"/>'


def exmark(c, k=1.0, deg=0.0):
    """「！」：上粗下細的楔形（三次 Bézier 兩側）＋圓點。"""
    pts = xf([(0, -40), (0, 4)], c, k, deg)
    top = xf([(-7.5, -40), (7.5, -40), (2.8, 4), (-2.8, 4)], c, k, deg)
    d = (f"M {P(top[0])} C {P(xf([(-7.5,-50)],c,k,deg)[0])} {P(xf([(7.5,-50)],c,k,deg)[0])} {P(top[1])} "
         f"C {P(xf([(7,-20)],c,k,deg)[0])} {P(xf([(4,-2)],c,k,deg)[0])} {P(top[2])} "
         f"C {P(xf([(1.5,8)],c,k,deg)[0])} {P(xf([(-1.5,8)],c,k,deg)[0])} {P(top[3])} "
         f"C {P(xf([(-4,-2)],c,k,deg)[0])} {P(xf([(-7,-20)],c,k,deg)[0])} {P(top[0])} Z")
    dot = xf([(0, 20)], c, k, deg)[0]
    del pts
    return f'<path d="{d}" fill="{INK}"/><circle cx="{f(dot[0])}" cy="{f(dot[1])}" r="{f(6.2*k)}" fill="{INK}"/>'


def motion_lines(c, deg, spread=34, r0=8, length=13, n=3, w=5.2):
    """放射短線（原圖跳躍格那種）：以 c 為中心、朝 deg 方向張開。"""
    out = []
    for i in range(n):
        a = deg + (i - (n - 1) / 2) * spread
        v = dirv(a)
        p0 = add(c, v, r0); p1 = add(c, v, r0 + length)
        m = add(add(p0, v, length * 0.5), (-v[1], v[0]), 1.2)
        out.append(brush(bez(p0, m, m, p1, 8), w, w * 0.8))
    return "".join(out)


def arcs(c, deg, r=26, n=2, w=4.6):
    """揮手的弧形動作線（原圖蹲下格「( )」那種）。"""
    out = []
    for i in range(n):
        rr = r + i * 9
        a0, a1 = deg - 22, deg + 22
        p0 = add(c, dirv(a0), rr); p3 = add(c, dirv(a1), rr)
        p1 = add(c, dirv(a0 + 11), rr * 1.05); p2 = add(c, dirv(a1 - 11), rr * 1.05)
        out.append(brush(bez(p0, p1, p2, p3, 12), w, w * 0.85))
    return "".join(out)


def sparkle(c, r=11, color=SPARK):
    """四角閃光（看盤分鏡第 10 格那種黃色星），四段二次 Bézier 往內收。"""
    pts = [(c[0], c[1] - r), (c[0] + r, c[1]), (c[0], c[1] + r), (c[0] - r, c[1])]
    d = f"M {P(pts[0])} " + " ".join(f"Q {P(c)} {P(pts[(i+1)%4])}" for i in range(4)) + " Z"
    return f'<path d="{d}" fill="{color}"/>'


def sign_svg(x0, y0, x1, y1, deg=0.0):
    """白色圓角牌：手繪感（四邊是微彎的三次 Bézier）、底部一條米色陰影。"""
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hw, hh = (x1 - x0) / 2, (y1 - y0) / 2
    r = 24
    loc = [(-hw + r, -hh), (hw - r, -hh), (hw, -hh + r), (hw, hh - r), (hw - r, hh), (-hw + r, hh), (-hw, hh - r), (-hw, -hh + r)]
    T = lambda p: add((cx, cy), rot2(p, deg))  # noqa: E731
    k = 0.5523 * r
    d = (f"M {P(T(loc[0]))} C {P(T((-hw*0.3,-hh-2.0)))} {P(T((hw*0.3,-hh+1.2)))} {P(T(loc[1]))} "
         f"C {P(T((hw-r+k,-hh)))} {P(T((hw,-hh+r-k)))} {P(T(loc[2]))} "
         f"C {P(T((hw+1.5,-hh*0.3)))} {P(T((hw-1.0,hh*0.3)))} {P(T(loc[3]))} "
         f"C {P(T((hw,hh-r+k)))} {P(T((hw-r+k,hh)))} {P(T(loc[4]))} "
         f"C {P(T((hw*0.3,hh+1.8)))} {P(T((-hw*0.3,hh-1.0)))} {P(T(loc[5]))} "
         f"C {P(T((-hw+r-k,hh)))} {P(T((-hw,hh-r+k)))} {P(T(loc[6]))} "
         f"C {P(T((-hw-1.4,hh*0.3)))} {P(T((-hw+1.0,-hh*0.3)))} {P(T(loc[7]))} "
         f"C {P(T((-hw,-hh+r-k)))} {P(T((-hw+r-k,-hh)))} {P(T(loc[0]))} Z")
    sh = (f"M {P(T((-hw+10, hh-14)))} C {P(T((-hw*0.3, hh-9)))} {P(T((hw*0.3, hh-9)))} {P(T((hw-10, hh-14)))} "
          f"L {P(T((hw-14, hh-5)))} L {P(T((-hw+14, hh-5)))} Z")
    return (f'<path d="{d}" fill="#FFFFFF"/>'
            f'<path d="{sh}" fill="{FUR_SH}" opacity="0.8"/>'
            f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="{f(OUT_W)}" stroke-linejoin="round"/>')


# ================================================================== 繪製
def svg_doc(body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{SIZE*SS}" height="{SIZE*SS}" '
            f'viewBox="0 0 {SIZE} {SIZE}">{body}</svg>')


def raster(svg_body):
    if not svg_body:
        return Image.new("RGBA", (SIZE * SS, SIZE * SS), (0, 0, 0, 0))
    png = cairosvg.svg2png(bytestring=svg_doc(svg_body).encode("utf-8"), output_width=SIZE * SS,
                           output_height=SIZE * SS)
    return Image.open(io.BytesIO(png)).convert("RGBA")


def interior_mask(body_rgba):
    """身體 alpha 往內縮約一個描邊寬 → 手臂描邊落在這裡面的部分要遮掉（手臂從身體長出來）。"""
    a = body_rgba.getchannel("A")
    k = int(OUT_W * SS * 0.9) | 1
    small = a.resize((SIZE, SIZE), Image.BILINEAR).filter(ImageFilter.MinFilter(max(3, (k // SS) | 1)))
    return small.resize((SIZE * SS, SIZE * SS), Image.BILINEAR)


def compose(poses, fr):
    """fr：{"g": 身體幾何, "limbs": [...], "front": svg 字串（肉掌、符號、牌子）, "top": 最上層 svg}"""
    body = pose_tween.warp_body(poses[fr["g"]["src"]], fr["g"], SIZE).convert("RGBA")
    canvas = Image.new("RGBA", body.size, (0, 0, 0, 0))
    if fr.get("back"):
        canvas = Image.alpha_composite(canvas, raster(fr["back"]))
    canvas = Image.alpha_composite(canvas, body)
    limbs = fr.get("limbs", [])
    if limbs:
        fills = "".join(l["fill"] for l in limbs)
        lines = "".join(l["line"] for l in limbs if l.get("merge", True))
        free = "".join(l["line"] for l in limbs if not l.get("merge", True))
        canvas = Image.alpha_composite(canvas, raster(fills))
        ol = raster(lines)
        m = np.asarray(interior_mask(body)).astype(np.float32) / 255
        # 只在「肩膀根部」附近遮掉手臂描邊（手臂從身體長出來）；其他地方手臂在身體前面，描邊照畫
        disc = Image.new("L", body.size, 0)
        dd = ImageDraw.Draw(disc)
        alpha = np.asarray(body.getchannel("A"))
        for l in limbs:
            if l.get("merge", True):
                # 手臂軸線離開身體的那一點：只在這附近把手臂描邊遮掉（接縫），
                # 手臂壓在臉上的那段描邊照畫（看得出手在身體前面）
                ax, ay = l["anchor"]; d = dirv(l["deg"])
                ex, ey = ax, ay
                for t in range(0, 200):
                    x, y = ax + d[0] * t, ay + d[1] * t
                    xi, yi = int(x * SS), int(y * SS)
                    if not (0 <= xi < alpha.shape[1] and 0 <= yi < alpha.shape[0]) or alpha[yi, xi] < 128:
                        ex, ey = ax + d[0] * (t - 4), ay + d[1] * (t - 4); break
                r = l["root_r"] * SS
                dd.ellipse((ex * SS - r, ey * SS - r, ex * SS + r, ey * SS + r), fill=255)
        disc = disc.filter(ImageFilter.GaussianBlur(2 * SS))
        m = m * (np.asarray(disc).astype(np.float32) / 255)
        a = Image.fromarray((np.asarray(ol.getchannel("A")).astype(np.float32) * (1 - m)).astype(np.uint8))
        ol.putalpha(a)
        canvas = Image.alpha_composite(canvas, ol)
        if free:
            canvas = Image.alpha_composite(canvas, raster(free))
    if fr.get("front"):
        canvas = Image.alpha_composite(canvas, raster(fr["front"]))
    if fr.get("text"):
        canvas = Image.alpha_composite(canvas, text_layer(*fr["text"]))
    return canvas.resize((SIZE, SIZE), Image.LANCZOS)


def limb(anchor, deg, length, seed=0, merge=True, **kw):
    fill, outline, tip = limb_paths(anchor, deg, length, seed=seed, **kw)
    sh_fill = ""
    # 手臂下緣一道米色陰影（原圖身體下半部也是這樣上色）
    d = dirv(deg); n = (-d[1], d[0])
    s0 = add(add(anchor, d, 30), n, -10); s1 = add(add(anchor, d, length - 8), n, -9)
    sh_fill = brush(bez(s0, add(s0, d, (length - 38) * 0.3), add(s1, d, -(length - 38) * 0.3), s1, 10), 9, 6, FUR_SH) \
        if length > 46 else ""
    return {"fill": f'<path d="{fill}" fill="{FUR}"/><g opacity="0.55">' + sh_fill + '</g>',
            "line": f'<path d="{outline}" fill="none" stroke="{INK}" stroke-width="{f(OUT_W)}" '
                    f'stroke-linecap="round" stroke-linejoin="round"/>',
            "tip": tip, "merge": merge, "anchor": anchor, "deg": deg, "root_r": kw.get("hw_root", 23.0) * 1.25}


_FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"


def text_layer(txt, c, deg, px):
    big = Image.new("RGBA", (SIZE * SS, SIZE * SS), (0, 0, 0, 0))
    font = ImageFont.truetype(_FONT, int(px * SS))
    tmp = Image.new("RGBA", (int(px * SS * (len(txt) + 1)), int(px * SS * 1.6)), (0, 0, 0, 0))
    dr = ImageDraw.Draw(tmp)
    dr.text((tmp.width / 2, tmp.height / 2), txt, font=font, fill=(42, 22, 16, 255), anchor="mm",
            stroke_width=int(1.2 * SS), stroke_fill=(42, 22, 16, 255))
    tmp = tmp.rotate(-deg, resample=Image.BICUBIC, expand=True)
    big.alpha_composite(tmp, (int(c[0] * SS - tmp.width / 2), int(c[1] * SS - tmp.height / 2)))
    return big


# ================================================================== 動作：每組 12 格
def ease(t):
    return 0.5 - 0.5 * math.cos(math.pi * t)


# 原圖第 0 張量到的部位（原圖座標）
EYE_L, EYE_R = (192, 264), (309, 261)
CHEEK_L, CHEEK_R = (151, 289), (350, 284)
SH_R_WAVE = (434, 326)        # 揮手：畫面右側肩膀
SH_R_POINT = (438, 338)       # 指向：畫面右側腰側
SH_SIGN_L, SH_SIGN_R = (90, 342), (424, 338)


def act_wave(poses):
    # (角度：0＝往右、90＝往上；手長；身體 rot／壓扁；有無弧線)
    plan = [
        ("待機（跟 jump K01 同一格身體）", None, 0, dict()),
        ("右手從身側冒出", (-20, 52), 0, dict(rot=-1.0, h=0.99)),
        ("手舉到肩上", (40, 70), 0, dict(rot=-2.0, h=1.01, lag=-0.03)),
        ("手舉到最高、往外", (62, 80), 1, dict(rot=-3.0, h=1.02, lag=-0.04)),
        ("揮向內", (90, 78), 0, dict(rot=-1.0, h=1.01)),
        ("揮回外", (55, 80), 1, dict(rot=-3.5, h=1.02, lag=-0.05)),
        ("再揮向內", (92, 78), 0, dict(rot=-0.5, h=1.01)),
        ("再揮回外", (58, 80), 1, dict(rot=-3.0, h=1.02, lag=-0.04)),
        ("揮到正上方", (80, 76), 0, dict(rot=-1.5, h=1.01)),
        ("手往下收", (30, 72), 0, dict(rot=-1.0, h=1.0)),
        ("手收回身側", (-30, 50), 0, dict(rot=0.0, h=0.985, w=1.01)),
        ("回待機（微彈）", None, 0, dict(h=0.99, w=1.008)),
    ]
    frames = []
    for i, (lab, arm, arc, gk) in enumerate(plan):
        g = base_geom(poses, 0, **gk)
        fr = {"g": g, "label": lab, "limbs": [], "front": ""}
        if arm:
            deg, L = arm
            deg += -body_angle(g)
            sh = shoulder(poses, g, SH_R_WAVE)
            lb = limb(sh, deg, L, seed=i)
            fr["limbs"].append(lb)
            fr["front"] += paw_svg(add(lb["tip"], dirv(deg), 4), deg, r=16, seed=i)
            if arc:
                fr["front"] += arcs(add(lb["tip"], dirv(deg), 4), deg + 75, r=22) + \
                    arcs(add(lb["tip"], dirv(deg), 4), deg - 75, r=22, n=1)
        frames.append(fr)
    return frames


def act_point(poses, base_deg, tag):
    plan = [
        ("待機", None, dict()),
        ("預備：身體往後縮、手收在腰側", (base_deg - 70, 38), dict(rot=-3, w=1.02, h=0.97, lag=0.03)),
        ("手往前伸到一半", (base_deg - 15, 62), dict(rot=1, h=1.0)),
        ("伸直指出去、身體前傾", (base_deg, 80), dict(rot=4, h=1.02, lag=-0.05, cx=3)),
        ("過頭一點（慣性）", (base_deg + 3, 86), dict(rot=5, h=1.03, lag=-0.07, cx=5)),
        ("定住指著", (base_deg, 80), dict(rot=3.5, h=1.02, lag=-0.03, cx=4)),
        ("點一下：手縮回", (base_deg, 72), dict(rot=2.5, h=1.01, cx=3)),
        ("點一下：戳出去", (base_deg, 84), dict(rot=4.5, h=1.025, lag=-0.05, cx=5)),
        ("再縮回", (base_deg, 72), dict(rot=2.5, h=1.01, cx=3)),
        ("再戳出去", (base_deg, 84), dict(rot=4.5, h=1.025, lag=-0.05, cx=5)),
        ("手收回一半", (base_deg - 25, 60), dict(rot=1.5, h=1.0, cx=2)),
        ("手收回腰側", (base_deg - 75, 37), dict(rot=0, h=0.985, w=1.01)),
    ]
    frames = []
    for i, (lab, arm, gk) in enumerate(plan):
        g = base_geom(poses, 0, **gk)
        fr = {"g": g, "label": lab, "limbs": [], "front": ""}
        if arm:
            deg, L = arm
            sh = shoulder(poses, g, SH_R_POINT)
            lb = limb(sh, deg, L, seed=i + 40)
            fr["limbs"].append(lb)
            tip = add(lb["tip"], dirv(deg), 5)
            fr["front"] += paw_svg(tip, deg, r=16.5, squash=0.8, seed=i + 40)
            if L >= 80 and i in (3, 4, 7, 9):
                fr["front"] += motion_lines(add(tip, dirv(deg), 8), deg, spread=40, r0=12, length=16, w=6)
        frames.append(fr)
    for fr in frames:
        fr["dir"] = tag
    return frames


def act_tilt(poses):
    # 歪頭：rot 負值＝畫面上逆時針（頭往左歪），「？」在頭的右上
    plan = [
        ("待機", 0, 0.0, None),
        ("微縮（預備）", 0, 0.03, None),
        ("頭開始歪", -6, -0.04, None),
        ("歪到 14°（過頭）", -14, -0.10, None),
        ("回到 12°、「？」冒出", -12, -0.06, 0.45),
        ("「？」彈大", -12, -0.04, 1.22),
        ("「？」回正常", -12.5, -0.05, 1.0),
        ("「？」晃一下", -11.5, -0.04, 1.04),
        ("停著想", -12, -0.05, 1.0),
        ("頭開始回正、「？」縮", -7, -0.02, 0.62),
        ("快回正、「？」消失", -2.5, 0.02, 0.2),
        ("回待機（微彈）", 0, 0.0, None),
    ]
    frames = []
    for i, (lab, rot, lag, qk) in enumerate(plan):
        gk = dict(rot=rot, lag=lag)
        if i == 1:
            gk.update(h=0.97, w=1.02)
        if i == 11:
            gk.update(h=0.99, w=1.008)
        g = base_geom(poses, 0, **gk)
        fr = {"g": g, "label": lab, "limbs": [], "front": ""}
        if qk:
            top = fwd(poses, g, 420, 140)
            wob = {7: 8, 6: -4}.get(i, 0)
            fr["front"] += qmark((top[0] + 8, top[1] - 12), k=1.15 * qk, deg=14 + wob)
        frames.append(fr)
    return frames


def act_wow(poses):
    plan = [
        # 標籤, 身體幾何, 手掌位置比例(0 在身側 → 1 貼臉), 「！」大小, 眼睛亮點, 閃光
        ("待機", dict(), 0.0, 0, False, 0),
        ("預備：往下壓", dict(h=0.94, w=1.04, lag=0.04), 0.15, 0, False, 0),
        ("嚇一跳往上縮、手往上", dict(h=1.06, w=0.95, bottom=-10, lag=-0.08), 0.6, 0.5, True, 0),
        ("雙手貼臉、「！」彈出", dict(h=1.04, w=0.97, bottom=-6, lag=-0.04), 1.0, 1.25, True, 1),
        ("落回、眼睛發亮", dict(h=0.99, w=1.01, bottom=-1), 1.0, 1.0, True, 2),
        ("抖一下（左）", dict(h=1.0, rot=-2.5, cx=-2), 1.0, 1.05, True, 1),
        ("抖一下（右）", dict(h=1.0, rot=2.5, cx=2), 1.0, 0.98, True, 2),
        ("抖一下（左）", dict(h=1.01, rot=-1.5, cx=-1), 1.0, 1.03, True, 1),
        ("定住、閃光", dict(h=1.0), 1.0, 1.0, True, 2),
        ("「！」縮小", dict(h=0.99, w=1.01), 1.0, 0.6, True, 1),
        ("手放下", dict(h=0.98, w=1.015), 0.45, 0.0, False, 0),
        ("回待機（微彈）", dict(h=0.99, w=1.006), 0.0, 0, False, 0),
    ]
    frames = []
    for i, (lab, gk, t, ex, eye, sp) in enumerate(plan):
        g = base_geom(poses, 0, **gk)
        fr = {"g": g, "label": lab, "limbs": [], "front": ""}
        if t > 0:
            # 從身體下側（原圖座標）沿弧線移到臉頰外側
            for side, low, cheek, deg0 in ((-1, (120, 420), (138, 318), 70), (1, (388, 420), (366, 312), 110)):
                e = ease(t)
                px = low[0] + (cheek[0] - low[0]) * e - side * 14 * math.sin(math.pi * e)
                py = low[1] + (cheek[1] - low[1]) * e
                c = fwd(poses, g, px, py)
                deg = (deg0 if side < 0 else deg0) - body_angle(g)
                fr["front"] += paw_svg(c, deg, r=17, squash=0.92, seed=i + side + 120,
                                       open_side=(245 if side < 0 else 295))
        if eye:
            for e0 in (EYE_L, EYE_R):
                p = fwd(poses, g, e0[0] + 4, e0[1] - 5)
                q = fwd(poses, g, e0[0] - 4, e0[1] + 4)
                fr["front"] += (f'<circle cx="{f(p[0])}" cy="{f(p[1])}" r="3.3" fill="#FFFFFF"/>'
                                f'<circle cx="{f(q[0])}" cy="{f(q[1])}" r="1.6" fill="#FFFFFF"/>')
        if ex:
            top = fwd(poses, g, 256, 120)
            fr["front"] += exmark((top[0] + 4, top[1] - 26), k=1.05 * ex, deg=4)
            if ex >= 1.0:
                fr["front"] += motion_lines((top[0] - 70, top[1] + 12), 135, spread=30, r0=6, length=13, n=2) + \
                    motion_lines((top[0] + 78, top[1] + 10), 45, spread=30, r0=6, length=13, n=2)
        if sp:
            sz = {1: (15, 10), 2: (19, 9)}[sp]
            a = fwd(poses, g, 452, 190); b = fwd(poses, g, 60, 210)
            fr["front"] += sparkle(a, sz[0]) + sparkle(b, sz[1])
        frames.append(fr)
    return frames


SIGN_BOX = (72, 70, 424, 236)


def act_sign(poses, text=None):
    # 兩拍上下晃：牌子隨身體壓扁／拉長上下，左右微傾
    plan = [
        ("舉著（低點）", dict(h=0.96, w=1.03, lag=0.03), 6, -1.5),
        ("往上撐", dict(h=1.0, w=1.0), 0, -0.5),
        ("撐到最高", dict(h=1.04, w=0.975, lag=-0.05, bottom=-3), -8, 1.0),
        ("最高點晃右", dict(h=1.03, w=0.98, lag=-0.03, bottom=-2, rot=1.5), -7, 3.0),
        ("往下", dict(h=1.0, w=1.0, rot=1.0), -1, 2.0),
        ("落到低點", dict(h=0.955, w=1.035, lag=0.04, rot=0.5), 7, 0.5),
        ("低點回彈", dict(h=0.975, w=1.02, lag=0.02), 4, -0.5),
        ("再往上撐", dict(h=1.01, w=0.995), -2, -1.5),
        ("撐到最高晃左", dict(h=1.04, w=0.975, lag=-0.05, bottom=-3, rot=-1.5), -8, -3.0),
        ("最高點", dict(h=1.03, w=0.98, lag=-0.03, bottom=-2, rot=-1.0), -6, -2.5),
        ("往下", dict(h=1.0, w=1.0, rot=-0.5), 0, -2.0),
        ("快到低點", dict(h=0.97, w=1.02, lag=0.02), 4, -1.8),
    ]
    frames = []
    x0, y0, x1, y1 = SIGN_BOX
    for i, (lab, gk, dy, sdeg) in enumerate(plan):
        g = base_geom(poses, 0, **gk)
        fr = {"g": g, "label": lab, "limbs": [], "front": ""}
        sx0, sy0, sx1, sy1 = x0, y0 + dy, x1, y1 + dy
        scx, scy = (sx0 + sx1) / 2, (sy0 + sy1) / 2
        # 兩隻手抓在牌子下緣靠兩角（跟著牌子的傾斜）
        grips = [add((scx, scy), rot2((-(sx1 - sx0) / 2 + 30, (sy1 - sy0) / 2 - 2), sdeg)),
                 add((scx, scy), rot2(((sx1 - sx0) / 2 - 30, (sy1 - sy0) / 2 - 2), sdeg))]
        paws = ""
        for sh_src, gp, s in ((SH_SIGN_L, grips[0], 0), (SH_SIGN_R, grips[1], 1)):
            sh = shoulder(poses, g, sh_src, depth=14)
            v = (gp[0] - sh[0], gp[1] - sh[1])
            L = math.hypot(*v)
            deg = math.degrees(math.atan2(-v[1], v[0]))
            lb = limb(sh, deg, L - 6, seed=i * 2 + s + 200, hw_root=23, hw_tip=19)
            fr["limbs"].append(lb)
            paws += paw_svg(gp, deg, r=16, squash=0.86, seed=i * 2 + s + 200,
                            open_side=deg + 180)
        fr["front"] += sign_svg(sx0, sy0, sx1, sy1, sdeg) + paws
        fr["sign"] = {"center": [round(scx, 1), round(scy, 1)], "size": [sx1 - sx0, sy1 - sy0], "deg": sdeg}
        if text:
            fr["text"] = (text, (scx, scy - 4), sdeg, 84)
        frames.append(fr)
    return frames


ACTIONS = {
    "wave": ("揮手", lambda p: act_wave(p), [140, 80, 70, 70, 70, 70, 70, 70, 70, 70, 80, 140]),
    "point_r": ("指向・右", lambda p: act_point(p, 0, "右"), [140, 80, 60, 60, 70, 90, 60, 70, 60, 90, 70, 80]),
    "point_ur": ("指向・右上", lambda p: act_point(p, 35, "右上"), [140, 80, 60, 60, 70, 90, 60, 70, 60, 90, 70, 80]),
    "point_dr": ("指向・右下", lambda p: act_point(p, -35, "右下"), [140, 80, 60, 60, 70, 90, 60, 70, 60, 90, 70, 80]),
    "tilt": ("歪頭疑問", lambda p: act_tilt(p), [140, 70, 60, 70, 60, 60, 80, 80, 160, 70, 70, 120]),
    "wow": ("驚嘆", lambda p: act_wow(p), [140, 70, 50, 60, 70, 50, 50, 50, 140, 70, 80, 120]),
    "sign": ("舉牌（牌面留白）", lambda p: act_sign(p), [80] * 12),
    "sign_text": ("舉牌（牌面「許願」）", lambda p: act_sign(p, "許願"), [80] * 12),
}


# ================================================================== 輸出
def sheet12(frames, labels, path, cols=6, cell=240):
    """12 格總覽（洋紅／深／淺 三種底輪流當格底，順便看白邊）。"""
    rows = math.ceil(len(frames) / cols)
    lab, pad = 24, 6
    W = cols * (cell + pad) + pad
    H = rows * (cell + lab + pad) + pad
    img = Image.new("RGB", (W, H), (40, 40, 48))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(_FONT, 15)
    bgs = [(250, 246, 240), (14, 22, 40), (244, 247, 252)]
    for i, (fm, t) in enumerate(zip(frames, labels)):
        r, c = divmod(i, cols)
        x = pad + c * (cell + pad); y = pad + r * (cell + lab + pad)
        tile = Image.new("RGBA", (cell, cell), bgs[(r + c) % 2 * 2] + (255,))
        tile.alpha_composite(fm.resize((cell, cell), Image.LANCZOS))
        img.paste(tile.convert("RGB"), (x, y + lab))
        d.text((x + 4, y + 4), t, fill=(240, 240, 240), font=font)
    img.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="site/brand/src/support_anim_1009.gif")
    ap.add_argument("--out", required=True, help="frames 輸出（scratchpad，不進 repo）")
    ap.add_argument("--repo-out", default="docs/anim")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    poses = pose_tween.load_poses(Path(a.src))
    out = Path(a.out)
    idx_path = out / "index.json"
    index = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else {}
    only = [x for x in a.only.split(",") if x]
    for key, (name, fn, durs) in ACTIONS.items():
        if only and key not in only:
            continue
        frs = fn(poses)
        assert len(frs) == 12, key
        imgs = [compose(poses, fr) for fr in frs]
        fd = out / key / "frames"
        fd.mkdir(parents=True, exist_ok=True)
        paths = []
        for j, im in enumerate(imgs):
            p = fd / f"frame_{j+1:02d}.png"
            im.save(p)
            paths.append(str(p.resolve()))
        group = key.split("_")[0]
        rd = Path(a.repo_out) / f"bibi_{group}"
        rd.mkdir(parents=True, exist_ok=True)
        suffix = "" if key in ("wave", "tilt", "wow", "sign") else "_" + key.split("_", 1)[1]
        labels = [f"{j+1:02d} {fr['label']}" for j, fr in enumerate(frs)]
        sheet12(imgs, labels, rd / f"sheet_12{suffix}.png")
        imgs[0].save(rd / f"anim{suffix}.webp", save_all=True, append_images=imgs[1:], duration=durs, loop=0,
                     lossless=False, quality=88, method=6)
        imgs[0].save(out / key / "anim.gif", save_all=True, append_images=imgs[1:], duration=durs, loop=0,
                     disposal=2)
        # 相鄰差異（確認沒有重複影格）
        arr = [np.asarray(i).astype(int) for i in imgs]
        diffs = [int(np.abs(arr[k] - arr[(k + 1) % 12]).sum() // 1000) for k in range(12)]
        entry = {"name": name, "size": [SIZE, SIZE], "frames": paths, "durations_ms": durs,
                 "labels": [fr["label"] for fr in frs], "adjacent_diff_k": diffs,
                 "scene": {"scale": SCALE, "center_x": CX, "ground_y": GROUND}}
        if key.startswith("sign"):
            entry["sign_box_per_frame"] = [fr["sign"] for fr in frs]
        (out / key / "meta.json").write_text(json.dumps(entry, ensure_ascii=False, indent=1), encoding="utf-8")
        print(key, "min diff", min(diffs), "→", rd)
    # 合併各組的 meta.json → index.json（可平行跑 --only，最後一支寫齊）
    for k in ACTIONS:
        mp = out / k / "meta.json"
        if mp.exists():
            index[k] = json.loads(mp.read_text(encoding="utf-8"))
    idx_path.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
