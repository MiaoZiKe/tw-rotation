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
    body = pose_tween.warp_body(fr.get("pose") or poses[fr["g"]["src"]], fr["g"], SIZE).convert("RGBA")
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
    if fr.get("mid"):        # 身體前面、post 之前（例如報紙、眼鏡框底下的東西）
        canvas = Image.alpha_composite(canvas, raster(fr["mid"]))
    for t in fr.get("texts_mid", []):
        canvas = Image.alpha_composite(canvas, text_layer(*t))
    if fr.get("post"):       # 對 2048 畫布做處理（例如放大鏡把鏡片裡的畫面放大）
        canvas = fr["post"](canvas)
    if fr.get("front"):
        canvas = Image.alpha_composite(canvas, raster(fr["front"]))
    for t in fr.get("texts", []):
        canvas = Image.alpha_composite(canvas, text_layer(*t))
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
# 牌面字：jf open 粉圓（justfont，SIL OFL 1.1，跟影片泡泡同一套）。字型檔不進 repo，
# 用環境變數 BIBI_SIGN_FONT 指到 jf-openhuninn-2.1.ttf；找不到就退回文泉驛正黑。
import os  # noqa: E402
HUNINN = os.environ.get("BIBI_SIGN_FONT") if os.path.exists(os.environ.get("BIBI_SIGN_FONT", "")) else None


def text_layer(txt, c, deg, px, font_path=None, color=(42, 22, 16, 255), stroke=0.6):
    big = Image.new("RGBA", (SIZE * SS, SIZE * SS), (0, 0, 0, 0))
    font = ImageFont.truetype(font_path or _FONT, int(px * SS))
    tmp = Image.new("RGBA", (int(px * SS * (len(txt) + 1)), int(px * SS * 1.6)), (0, 0, 0, 0))
    dr = ImageDraw.Draw(tmp)
    dr.text((tmp.width / 2, tmp.height / 2), txt, font=font, fill=color, anchor="mm",
            stroke_width=int(stroke * SS), stroke_fill=color)
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


SIGN_BOX = (98, 50, 398, 198)   # 牌底離頭頂毛 23～29px（站著的格；蹲下兩格更遠）


def float_marks(c, w, phase):
    """牌子下方的「浮著」記號：3 顆小閃光（大小固定、不閃爍）＋2 道淡淡的弧形飄浮線，跟著牌子走。"""
    out = ""
    for dx, dy, r in ((-0.40, 13, 6.0), (0.41, 11, 5.0), (-0.02, 9, 3.6)):
        out += sparkle((c[0] + dx * w, c[1] + dy), r)
    for dx in (-0.22, 0.20):
        x = c[0] + dx * w; y = c[1] + 8
        out += (f'<g opacity="0.35">' + brush(bez((x - 16, y), (x - 6, y + 6), (x + 6, y + 6), (x + 16, y), 10), 3.6, 3.0, INK)
                + '</g>')
    return out


def act_sign(poses, text=None, font=None):
    """2026-10-10 Andy 退件「許願的手太奇怪了，改成用懸空的方式呈現」：拿掉手臂與肉掌，
    牌子懸空飄在頭頂上方（上下輕飄、左右擺 ±4°），比比抬頭看牌子（lag>0 臉往上推）＋開心彈一下
    （蹲下與落地兩格用原圖第 2 張瞇眼笑的像素）。"""
    plan = [
        # 標籤, 像素來源, 身體幾何
        ("抬頭看牌子", 0, dict(lag=0.12)),
        ("抬頭更高", 0, dict(lag=0.16, h=1.01)),
        ("開心蹲（瞇眼笑）", 2, dict()),
        ("彈起拉長", 0, dict(bottom=-6, h=1.03, w=0.97, lag=0.14)),
        ("最高點", 0, dict(bottom=-9, h=1.02, w=0.98, lag=0.13)),
        ("往下落", 0, dict(bottom=-4, h=1.02, w=0.98, lag=0.10)),
        ("落地壓扁（瞇眼笑）", 2, dict(w=1.02)),
        ("回彈", 0, dict(h=1.02, w=0.985, lag=0.10)),
        ("站穩抬頭", 0, dict(lag=0.13)),
        ("看著牌子微晃右", 0, dict(lag=0.14, rot=2.0)),
        ("看著牌子微晃左", 0, dict(lag=0.13, rot=-1.5)),
        ("回到抬頭", 0, dict(lag=0.12, h=0.995)),
    ]
    frames = []
    x0, y0, x1, y1 = SIGN_BOX
    for i, (lab, src, gk) in enumerate(plan):
        g = base_geom(poses, src, **gk)
        if src == 2:   # 原圖第 2 張的天然高度（蹲），腳底同一條地面線
            pass
        fr = {"g": g, "label": lab, "limbs": [], "front": ""}
        ph = 2 * math.pi * i / 12
        dy = -6.0 * math.sin(ph - 0.52)         # 上下輕飄 ±6px：身體彈到最高（第 5 格）時牌子也在最高點
        sdeg = 4.0 * math.sin(ph + math.pi / 2)  # 左右擺 ±4°，跟上下錯開相位
        sy0, sy1 = y0 + dy, y1 + dy
        scx, scy = (x0 + x1) / 2, (sy0 + sy1) / 2
        fr["front"] += float_marks((scx, sy1), x1 - x0, ph) + sign_svg(x0, sy0, x1, sy1, sdeg)
        fr["sign"] = {"center": [round(scx, 1), round(scy, 1)], "size": [x1 - x0, y1 - y0], "deg": round(sdeg, 2)}
        if text:
            fr["text"] = (text, (scx, scy - 2), sdeg, 86, font)
        frames.append(fr)
    return frames


# ================================================================== A 批情境（2026-10-10 Andy：「影片中新增多點 GIF 圖，越豐富、情境越多越好」）
# 舉牌退件的教訓：道具一律懸空／放在身前／貼著身體前方，不畫從身體長出來的長手；手只用小肉掌點綴。
GOLD, GOLD_DK, GOLD_LT = "#F9C23C", "#E09A1E", "#FFE08A"
BLUE, PINK, MINT, RED, CYAN = "#2AA6F5", "#F6A5A0", "#7ED6A5", "#E8504A", "#3FC3E8"
PAPER, PAPER_SH, GRID = "#FFFDF7", "#EFE4D4", "#CDBDA9"
EYE_RX, EYE_RY = 12.0, 13.5
_EYE_CACHE = {}


def pose_eyes(poses, src=0, look=(0.0, 0.0), scale=1.0, hl=False):
    """原圖第 0 張的眼睛是兩顆黑點：先用毛色蓋掉，再在 look（原圖 px）偏移處畫回同色黑點 →
    眼睛可以左右掃、往上看、睜大加亮點。只改眼睛那 2 小塊，其餘像素不動。"""
    key = (src, round(look[0], 1), round(look[1], 1), round(scale, 2), hl)
    if key in _EYE_CACHE:
        return _EYE_CACHE[key]
    base = poses[src]
    svg = ""
    arr = np.asarray(base["body"]).astype(float)
    yy, xx = np.mgrid[0:arr.shape[0], 0:arr.shape[1]]
    for e in (EYE_L, EYE_R):
        # 蓋眼睛用的毛色：取眼睛外圈 17～23px 的實際平均色（不是固定色，放大鏡底下才不會看出一圈）
        ring = ((xx - e[0]) ** 2 + (yy - e[1]) ** 2 >= 17 ** 2) & ((xx - e[0]) ** 2 + (yy - e[1]) ** 2 <= 23 ** 2)
        ring &= arr[..., :3].mean(2) > 200
        col = "#%02X%02X%02X" % tuple(int(v) for v in np.median(arr[ring][:, :3], 0))
        svg += f'<circle cx="{f(e[0])}" cy="{f(e[1])}" r="15.5" fill="{col}"/>'
    for e in (EYE_L, EYE_R):
        c = (e[0] + look[0], e[1] + look[1])
        svg += f'<ellipse cx="{f(c[0])}" cy="{f(c[1])}" rx="{f(EYE_RX*scale)}" ry="{f(EYE_RY*scale)}" fill="{INK}"/>'
        if hl:
            svg += (f'<circle cx="{f(c[0]+4*scale)}" cy="{f(c[1]-5*scale)}" r="{f(4.2*scale)}" fill="#FFFFFF"/>'
                    f'<circle cx="{f(c[0]-4*scale)}" cy="{f(c[1]+4.5*scale)}" r="{f(2.0*scale)}" fill="#FFFFFF"/>')
    ov = raster(svg).resize((SIZE, SIZE), Image.LANCZOS)
    body = base["body"].copy()
    a = body.getchannel("A")
    body = Image.alpha_composite(body, ov)
    body.putalpha(a)
    out = dict(base); out["body"] = body
    _EYE_CACHE[key] = out
    return out


def nat_geom(poses, src, **kw):
    """原圖某一張姿勢的「天然」幾何（跟原圖同一套相對位置），換算到比比的場景座標。"""
    x0, y0, x1, y1 = poses[src]["box"]
    g = {"src": src, "cx": CX + ((x0 + x1) / 2 - 254) * SCALE, "bottom": GROUND - (485 - y1) * SCALE,
         "w": (x1 - x0) * SCALE, "h": (y1 - y0) * SCALE, "rot": 0.0, "lag": 0.0}
    for k, v in kw.items():
        if k in ("w", "h"):
            g[k] *= v
        elif k in ("cx", "bottom"):
            g[k] += v
        else:
            g[k] = v
    return g


def rrect(cx, cy, w, h, r, deg=0.0, wob=1.2):
    """手繪圓角矩形（四邊微彎的三次 Bézier），回傳 path d。"""
    hw, hh = w / 2, h / 2
    T = lambda p: add((cx, cy), rot2(p, deg))  # noqa: E731
    k = 0.5523 * r
    return (f"M {P(T((-hw+r,-hh)))} C {P(T((-hw*0.3,-hh-wob)))} {P(T((hw*0.3,-hh+wob*0.6)))} {P(T((hw-r,-hh)))} "
            f"C {P(T((hw-r+k,-hh)))} {P(T((hw,-hh+r-k)))} {P(T((hw,-hh+r)))} "
            f"C {P(T((hw+wob,-hh*0.3)))} {P(T((hw-wob*0.6,hh*0.3)))} {P(T((hw,hh-r)))} "
            f"C {P(T((hw,hh-r+k)))} {P(T((hw-r+k,hh)))} {P(T((hw-r,hh)))} "
            f"C {P(T((hw*0.3,hh+wob)))} {P(T((-hw*0.3,hh-wob*0.6)))} {P(T((-hw+r,hh)))} "
            f"C {P(T((-hw+r-k,hh)))} {P(T((-hw,hh-r+k)))} {P(T((-hw,hh-r)))} "
            f"C {P(T((-hw-wob,hh*0.3)))} {P(T((-hw+wob*0.6,-hh*0.3)))} {P(T((-hw,-hh+r)))} "
            f"C {P(T((-hw,-hh+r-k)))} {P(T((-hw+r-k,-hh)))} {P(T((-hw+r,-hh)))} Z")


def mini_paw(c, r=10.5, deg=90, seed=0):
    return paw_svg(c, deg, r=r, squash=0.85, seed=seed, spots=True)


# ---------------------------------------------------------------- 1. 看財經新聞（財經日曆紙）
def calendar_svg(cx, cy, w, h, deg, mark=0.0):
    """攤開的月曆紙：上緣淡藍標頭、5×3 小格、幾格有小點；mark>0 時其中一格畫上紅圈（重點）。"""
    out = (f'<path d="{rrect(cx, cy + 4, w, h, 12, deg)}" fill="{PAPER_SH}"/>'
           f'<path d="{rrect(cx, cy, w, h, 12, deg)}" fill="{PAPER}"/>')
    T = lambda p: add((cx, cy), rot2(p, deg))  # noqa: E731
    hw, hh = w / 2, h / 2
    band = (f"M {P(T((-hw+12,-hh)))} L {P(T((hw-12,-hh)))} C {P(T((hw-4,-hh)))} {P(T((hw,-hh+4)))} {P(T((hw,-hh+12)))} "
            f"L {P(T((hw,-hh+30)))} L {P(T((-hw,-hh+30)))} L {P(T((-hw,-hh+12)))} "
            f"C {P(T((-hw,-hh+4)))} {P(T((-hw+4,-hh)))} {P(T((-hw+12,-hh)))} Z")
    out += f'<path d="{band}" fill="#D6EEFD"/>'
    gx0, gy0, cols, rows = -hw + 12, -hh + 40, 5, 3
    cw, ch = (w - 24) / cols, (h - 52) / rows
    for r_ in range(rows + 1):
        a, b = T((gx0, gy0 + r_ * ch)), T((gx0 + cols * cw, gy0 + r_ * ch))
        out += f'<path d="M {P(a)} L {P(b)}" stroke="{GRID}" stroke-width="1.6" stroke-linecap="round"/>'
    for c_ in range(cols + 1):
        a, b = T((gx0 + c_ * cw, gy0)), T((gx0 + c_ * cw, gy0 + rows * ch))
        out += f'<path d="M {P(a)} L {P(b)}" stroke="{GRID}" stroke-width="1.6" stroke-linecap="round"/>'
    for (c_, r_, col) in ((0, 0, BLUE), (2, 1, MINT), (4, 0, BLUE), (1, 2, GOLD), (3, 2, MINT)):
        p = T((gx0 + (c_ + 0.5) * cw, gy0 + (r_ + 0.5) * ch))
        out += f'<circle cx="{f(p[0])}" cy="{f(p[1])}" r="3.4" fill="{col}"/>'
    if mark > 0:
        p = T((gx0 + 3.5 * cw, gy0 + 1.5 * ch))
        rr = (ch * 0.62) * mark
        pts = [(p[0] + math.cos(t) * rr * 1.25, p[1] + math.sin(t) * rr) for t in np.linspace(-2.6, 3.9, 26)]
        out += brush(pts, 4.6, 3.6, RED)
    out += f'<path d="{rrect(cx, cy, w, h, 12, deg)}" fill="none" stroke="{INK}" stroke-width="{f(OUT_W)}" stroke-linejoin="round"/>'
    return out


def act_news(poses, font=None):
    # look：眼睛偏移（原圖 px）；eye：(倍率, 亮點)；mark：紅圈；ex：「！」大小；gk：身體幾何
    plan = [
        ("低頭看月曆", (0, 4), (1.0, False), 0, 0, dict(lag=-0.03)),
        ("眼睛掃到左邊", (-6, 4), (1.0, False), 0, 0, dict(lag=-0.03, rot=-1.0)),
        ("左邊再看仔細", (-7, 5), (1.0, False), 0, 0, dict(lag=-0.04, rot=-2.0, h=0.99)),
        ("掃回中間", (0, 4), (1.0, False), 0, 0, dict(lag=-0.03)),
        ("掃到右邊", (6, 4), (1.0, False), 0, 0, dict(lag=-0.03, rot=1.0)),
        ("右邊停住…", (7, 5), (1.0, False), 0.4, 0, dict(lag=-0.04, rot=2.0, h=0.99)),
        ("看到重點！驚一下", (3, 1), (1.3, True), 1.0, 1.2, dict(h=1.05, w=0.96, bottom=-8, lag=-0.08)),
        ("眼睛發亮", (3, 1), (1.25, True), 1.0, 1.0, dict(h=1.02, w=0.98, bottom=-3, lag=-0.04)),
        ("落回、還盯著", (4, 3), (1.15, True), 1.0, 0.8, dict(h=0.98, w=1.02)),
        ("點點頭", (2, 5), (1.0, False), 1.0, 0, dict(lag=-0.05, h=0.985)),
        ("紅圈留著、回到中間", (0, 4), (1.0, False), 0.6, 0, dict(lag=-0.03)),
        ("準備再看一次", (-2, 4), (1.0, False), 0.2, 0, dict(lag=-0.03, rot=-0.5)),
    ]
    frames = []
    for i, (lab, look, (es, hl), mark, ex, gk) in enumerate(plan):
        g = base_geom(poses, 0, **gk)
        fr = {"g": g, "label": lab, "pose": pose_eyes(poses, 0, look, es, hl)}
        lift = g["bottom"] - GROUND
        deg = -1.5 + 0.6 * g.get("rot", 0)
        cx, cy, w, h = CX + 2, 412 + lift * 0.6, 176, 112
        fr["mid"] = calendar_svg(cx, cy, w, h, deg, mark)
        # 小肉掌扶在紙的上緣兩角
        pl = add((cx, cy), rot2((-w / 2 + 16, -h / 2 + 2), deg)); pr = add((cx, cy), rot2((w / 2 - 16, -h / 2 + 2), deg))
        fr["front"] = mini_paw(pl, 11, 95, i) + mini_paw(pr, 11, 85, i + 7)
        if ex:
            top = fwd(poses, g, 256, 130)
            fr["front"] += exmark((top[0] + 70, top[1] - 6), k=0.9 * ex, deg=12)
            fr["front"] += motion_lines((top[0] - 70, top[1] + 20), 140, spread=30, r0=6, length=13, n=2)
        fr["texts_mid"] = [("財經日曆", add((cx, cy), rot2((0, -h / 2 + 15), deg)), deg, 17, font, (31, 79, 120, 255), 0.3)]
        frames.append(fr)
    return frames


# ---------------------------------------------------------------- 2. 錢幣飛過
def coin_svg(c, r, phase):
    """金幣：翻轉用寬度 |cos| 表現（真的在轉，不是放大縮小）；外框、內圈、亮面高光、「$」。"""
    k = max(0.16, abs(math.cos(phase)))
    rx, ry = r * k, r
    edge = f'<ellipse cx="{f(c[0]+ (1-k)*r*0.18)}" cy="{f(c[1])}" rx="{f(rx)}" ry="{f(ry)}" fill="{GOLD_DK}"/>' if k < 0.95 else ""
    out = edge + f'<ellipse cx="{f(c[0])}" cy="{f(c[1])}" rx="{f(rx)}" ry="{f(ry)}" fill="{GOLD}"/>'
    if k > 0.35:
        out += f'<ellipse cx="{f(c[0])}" cy="{f(c[1])}" rx="{f(rx*0.7)}" ry="{f(ry*0.7)}" fill="none" stroke="{GOLD_DK}" stroke-width="2.6"/>'
        sx = rx * 0.32
        pts = bez((c[0] + sx, c[1] - r * 0.30), (c[0] - sx * 1.6, c[1] - r * 0.42), (c[0] - sx * 1.4, c[1] - r * 0.02),
                  (c[0], c[1]), 10) + bez((c[0], c[1]), (c[0] + sx * 1.4, c[1] + r * 0.02), (c[0] + sx * 1.6, c[1] + r * 0.42),
                                         (c[0] - sx, c[1] + r * 0.30), 10)[1:]
        out += brush(pts, 3.6, 3.2, GOLD_DK)
        out += f'<path d="M {P((c[0], c[1]-r*0.46))} L {P((c[0], c[1]+r*0.46))}" stroke="{GOLD_DK}" stroke-width="2.4" stroke-linecap="round"/>'
        out += brush(bez((c[0] - rx * 0.62, c[1] - r * 0.28), (c[0] - rx * 0.62, c[1] - r * 0.6), (c[0] - rx * 0.3, c[1] - r * 0.72),
                         (c[0] - rx * 0.05, c[1] - r * 0.74), 8), 3.4, 2.4, GOLD_LT)
    out += f'<ellipse cx="{f(c[0])}" cy="{f(c[1])}" rx="{f(rx)}" ry="{f(ry)}" fill="none" stroke="{INK}" stroke-width="{f(OUT_W*0.8)}"/>'
    return out


def act_coins(poses):
    frames = []
    NC = 3
    for i in range(12):
        coins, us = [], []
        for k in range(NC):
            u = (i / 12 + k / NC) % 1.0
            x = -50 + u * 612
            y = 168 - 52 * math.sin(math.pi * u) + (k - 1) * 10
            coins.append(((x, y), 28 - k * 2, 2 * math.pi * (i / 12) * 3 + k * 1.3))
            us.append(u)
        # 眼睛追著「正在中段」那一枚（每 4 格換下一枚 → 轉頭追下一枚）
        lead = min(range(NC), key=lambda k: abs(us[k] - 0.5))
        dx = (us[lead] - 0.5) * 2 * 7.5
        hop = {4: dict(h=0.95, w=1.04, lag=0.03), 5: dict(h=1.05, w=0.96, bottom=-14, lag=-0.06),
               6: dict(h=1.03, w=0.98, bottom=-20, lag=-0.04), 7: dict(h=1.02, bottom=-8), 8: dict(h=0.96, w=1.035)}.get(i, {})
        gk = dict(rot=dx * 0.35, lag=hop.pop("lag", -0.05))
        gk.update(hop)
        g = base_geom(poses, 0, **gk)
        fr = {"g": g, "label": "", "pose": pose_eyes(poses, 0, (dx, -5), 1.1 if 5 <= i <= 7 else 1.0, 5 <= i <= 7)}
        svg = ""
        for (c, r, ph) in coins:
            for j, dl in enumerate((26, 42)):
                y = c[1] + (j - 0.5) * 9
                svg += f'<path d="M {P((c[0]-r-6-dl*0.4, y))} L {P((c[0]-r-6-dl, y))}" stroke="#B9AFA5" stroke-width="3.4" stroke-linecap="round" opacity="0.7"/>'
            svg += coin_svg(c, r, ph)
        if 5 <= i <= 7:
            top = fwd(poses, g, 256, 130)
            svg += sparkle((top[0] - 92, top[1] + 30), 10) + sparkle((top[0] + 96, top[1] + 44), 8)
        fr["front"] = svg
        fr["label"] = ["金幣從左邊飛進來", "眼睛追第一枚", "追到中間", "追到右邊", "準備蹦（下蹲）", "蹦起來！眼睛發亮",
                       "蹦到最高", "往下落", "落地壓扁", "轉頭追下一枚", "追到中間", "追到右邊"][i]
        frames.append(fr)
    return frames


# ---------------------------------------------------------------- 3. 放大鏡
def act_magnifier(poses):
    frames = []
    labs = ["放大鏡飄到臉中間", "往右眼飄", "停在右眼：眼睛被放大", "右眼上方晃", "往回飄", "飄過鼻子嘴巴",
            "往左眼飄", "停在左眼：眼睛被放大", "左眼下方晃", "往回飄", "回到中間", "微微上浮"]
    for i in range(12):
        ph = 2 * math.pi * (i - 2) / 12 + math.pi / 2      # 第 3 格正對右眼、第 8 格正對左眼
        g = base_geom(poses, 0, h=1.0 + 0.012 * math.sin(2 * ph), lag=-0.02)
        el = fwd(poses, g, *EYE_L); er = fwd(poses, g, *EYE_R)
        mx, hx = (el[0] + er[0]) / 2, (er[0] - el[0]) / 2
        lx = mx + hx * math.sin(ph)
        ly = (el[1] + er[1]) / 2 + 6 * math.cos(ph) ** 2 * (1 if math.sin(2 * ph) > 0 else -1)
        R, Z = 44.0, 1.7
        look = (5 * math.sin(ph), 0)
        fr = {"g": g, "label": labs[i], "pose": pose_eyes(poses, 0, look, 1.0, False)}

        def post(cv, lx=lx, ly=ly):
            r_src = R / Z
            box = (int((lx - r_src) * SS), int((ly - r_src) * SS), int((lx + r_src) * SS), int((ly + r_src) * SS))
            crop = cv.crop(box).resize((int(2 * R * SS), int(2 * R * SS)), Image.LANCZOS)
            m = Image.new("L", crop.size, 0)
            ImageDraw.Draw(m).ellipse((0, 0, crop.size[0] - 1, crop.size[1] - 1), fill=255)
            glass = Image.new("RGBA", crop.size, (232, 246, 255, 255))   # 鏡片底（看得到後面是空的）
            glass.alpha_composite(crop)
            glass.putalpha(m)
            out = cv.copy()
            out.alpha_composite(glass, (int((lx - R) * SS), int((ly - R) * SS)))
            return out
        fr["post"] = post
        hdeg = 48 + 6 * math.sin(ph + 1.0)          # 手把朝右下
        d = dirv(-hdeg)
        h0 = add((lx, ly), d, R + 3); h1 = add((lx, ly), d, R + 64)
        n = (-d[1], d[0])
        hw = 8.5
        handle = (f"M {P(add(h0, n, hw))} L {P(add(h1, n, hw))} C {P(add(add(h1, d, 11), n, hw))} {P(add(add(h1, d, 11), n, -hw))} "
                  f"{P(add(h1, n, -hw))} L {P(add(h0, n, -hw))} Z")
        svg = (f'<path d="{handle}" fill="#B7774F" stroke="{INK}" stroke-width="{f(OUT_W*0.9)}" stroke-linejoin="round"/>'
               + brush([add(add(h0, d, 10), n, -3), add(add(h1, d, -4), n, -3)], 3.2, 3.0, "#D9A27A")
               + f'<path d="M {P(add(add(h0, d, 6), n, hw))} L {P(add(add(h0, d, 6), n, -hw))}" stroke="{INK}" stroke-width="3"/>')
        svg += (f'<circle cx="{f(lx)}" cy="{f(ly)}" r="{f(R)}" fill="#BFE6FF" opacity="0.16"/>'
                f'<circle cx="{f(lx)}" cy="{f(ly)}" r="{f(R+4.5)}" fill="none" stroke="#6F5446" stroke-width="9"/>'
                f'<circle cx="{f(lx)}" cy="{f(ly)}" r="{f(R+9)}" fill="none" stroke="{INK}" stroke-width="{f(OUT_W*0.8)}"/>'
                f'<circle cx="{f(lx)}" cy="{f(ly)}" r="{f(R)}" fill="none" stroke="{INK}" stroke-width="2.6"/>')
        hl = [(lx + math.cos(t) * R * 0.74, ly + math.sin(t) * R * 0.74) for t in np.linspace(3.5, 4.5, 10)]
        svg += f'<g opacity="0.85">{brush(hl, 6.5, 4.5, "#FFFFFF")}</g>'
        fr["front"] = svg
        frames.append(fr)
    return frames


# ---------------------------------------------------------------- 4. 3D 眼鏡
def cube_svg(c, s, ang, tilt=24, cols=(BLUE, PINK, GOLD)):
    """真的 3D 方塊：繞 y 軸轉 ang、往前傾 tilt，正交投影，只畫朝向鏡頭的面（三色＋黑描邊）。"""
    a, t = math.radians(ang), math.radians(tilt)
    V = [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]

    def tr(v):
        x, y, z = v
        x, z = x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a)
        y, z = y * math.cos(t) - z * math.sin(t), y * math.sin(t) + z * math.cos(t)
        return x, y, z
    TV = [tr(v) for v in V]
    faces = [((0, 1, 3, 2), (-1, 0, 0)), ((4, 5, 7, 6), (1, 0, 0)), ((0, 1, 5, 4), (0, -1, 0)),
             ((2, 3, 7, 6), (0, 1, 0)), ((0, 2, 6, 4), (0, 0, -1)), ((1, 3, 7, 5), (0, 0, 1))]
    out = []
    for idx, nrm in faces:
        nz = tr(nrm)[2]
        if nz <= 0.02:
            continue
        ny = tr(nrm)[1]
        col = cols[2] if ny < -0.4 else (cols[0] if abs(nrm[0]) else cols[1])
        pts = [(c[0] + TV[j][0] * s, c[1] + TV[j][1] * s) for j in idx]
        mx = sum(p[0] for p in pts) / 4; my = sum(p[1] for p in pts) / 4
        pts.sort(key=lambda p: math.atan2(p[1] - my, p[0] - mx))   # 四個角依角度排好，面才不會交叉成沙漏
        d = "M " + " L ".join(P(p) for p in pts) + " Z"
        out.append((nz, f'<path d="{d}" fill="{col}" stroke="{INK}" stroke-width="3.4" stroke-linejoin="round"/>'))
    return "".join(x for _, x in sorted(out))


def glasses_svg(lc, rc, deg):
    """紅藍 3D 眼鏡：白色紙框＋黑描邊、左紅右藍半透明鏡片（看得到後面的眼睛）。"""
    mid = ((lc[0] + rc[0]) / 2, (lc[1] + rc[1]) / 2)
    span = math.hypot(rc[0] - lc[0], rc[1] - lc[1])
    W, H = span + 74, 54
    out = f'<path d="{rrect(mid[0], mid[1], W, H, 16, deg, 0.8)}" fill="#FFFFFF" stroke="{INK}" stroke-width="{f(OUT_W*0.9)}" stroke-linejoin="round"/>'
    for c, col in ((lc, RED), (rc, CYAN)):
        out += f'<path d="{rrect(c[0], c[1], 50, 38, 12, deg, 0.5)}" fill="{col}" opacity="0.58" stroke="{INK}" stroke-width="3.6"/>'
        hl = add(c, rot2((-14, -9), deg))
        out += f'<path d="M {P(hl)} l 8,-3" stroke="#FFFFFF" stroke-width="3.4" stroke-linecap="round" opacity="0.9"/>'
    # 鏡腳往兩側（一小段，掛在頭上）
    for sgn, c in ((-1, lc), (1, rc)):
        a = add(c, rot2((sgn * 37, -6), deg)); b = add(c, rot2((sgn * 52, -12), deg))
        out += f'<path d="M {P(a)} L {P(b)}" stroke="{INK}" stroke-width="4.4" stroke-linecap="round"/>'
    return out


def act_3dglasses(poses):
    # (標籤, 眼鏡往上偏移, 眼鏡轉角, 身體幾何, 眼睛(倍率,亮點), 方塊大小)
    plan = [
        ("3D 眼鏡從上面掉下來", -190, -14, dict(lag=-0.06), (1.0, False), 0.0),
        ("往下掉", -120, -7, dict(lag=-0.08), (1.0, False), 0.0),
        ("快戴上", -46, 5, dict(lag=-0.08, h=1.01), (1.05, False), 0.0),
        ("戴上！壓一下", 0, 0, dict(h=0.95, w=1.04, lag=0.04), (1.0, False), 0.0),
        ("驚喜彈起、方塊冒出", 0, -2, dict(h=1.05, w=0.96, bottom=-10, lag=-0.06), (1.3, True), 0.55),
        ("方塊轉起來", 0, 1, dict(h=1.02, bottom=-4), (1.25, True), 1.0),
        ("左右看方塊（左）", 0, -2, dict(rot=-2.5), (1.2, True), 1.0),
        ("左右看方塊（右）", 0, 2, dict(rot=2.5), (1.2, True), 1.0),
        ("開心晃", 0, 0, dict(h=1.015, lag=-0.03), (1.2, True), 1.0),
        ("方塊繼續轉", 0, -1, dict(h=0.99), (1.15, True), 1.0),
        ("眼鏡往上彈開", -52, 8, dict(h=1.02, lag=-0.05), (1.05, False), 0.6),
        ("飛出畫面、方塊收起", -140, 14, dict(lag=-0.05), (1.0, False), 0.2),
    ]
    frames = []
    for i, (lab, gy, gdeg, gk, (es, hl), cs) in enumerate(plan):
        g = base_geom(poses, 0, **gk)
        lk = (0, -1) if not (6 <= i <= 7) else ((-4 if i == 6 else 4), -1)
        fr = {"g": g, "label": lab, "pose": pose_eyes(poses, 0, lk, es, hl)}
        lc = fwd(poses, g, EYE_L[0] - 2, EYE_L[1] + 2); rc = fwd(poses, g, EYE_R[0] + 2, EYE_R[1] + 2)
        lc = (lc[0], lc[1] + gy); rc = (rc[0], rc[1] + gy)
        svg = ""
        if cs > 0:
            ang = 90 * i / 12 * 2
            for (c, s, a0, cols) in (((112, 190), 24, 0, (BLUE, PINK, GOLD)), ((392, 176), 20, 30, (PINK, MINT, GOLD)),
                                     ((410, 300), 16, 60, (MINT, BLUE, GOLD))):
                svg += cube_svg((c[0], c[1] + 4 * math.sin(2 * math.pi * i / 12 + a0)), s * cs, ang + a0, cols=cols)
        svg += glasses_svg(lc, rc, gdeg + g.get("rot", 0))
        if i == 4:
            top = fwd(poses, g, 256, 130)
            svg += motion_lines((top[0] - 60, top[1] + 10), 135, spread=30, r0=6, length=14, n=2) + \
                motion_lines((top[0] + 66, top[1] + 8), 45, spread=30, r0=6, length=14, n=2)
        if 5 <= i <= 9:
            svg += sparkle((150, 120), 10 if i % 2 else 8) + sparkle((350, 112), 8 if i % 2 else 10)
        fr["front"] = svg
        frames.append(fr)
    return frames


# ---------------------------------------------------------------- 5. 慶祝
_CONF_COLS = (PINK, GOLD, BLUE, MINT, "#F08A5D")


def confetti(i, layer):
    """紙花＋彩帶：每片固定的下落軌跡（12 格剛好落完一輪，循環無接縫），翻面用寬度 |cos|。"""
    rng = np.random.default_rng(7 + layer)
    out = ""
    n = 14
    for k in range(n):
        x0 = rng.uniform(20, 492); ph = rng.uniform(0, 1); col = _CONF_COLS[k % 5]
        u = (ph + i / 12) % 1.0
        y = -24 + u * 560
        x = x0 + 16 * math.sin(2 * math.pi * (u * 2 + ph))
        if layer == 1 and 170 < x < 330 and y > 250:
            continue
        w0, h0 = rng.uniform(8, 12), rng.uniform(5, 7)
        flip = abs(math.cos(2 * math.pi * (i / 12) * 2 + ph * 6))
        rot = rng.uniform(0, 180) + 30 * (i * (1 + k % 2))
        w = w0 * max(0.2, flip)
        pts = [add((x, y), rot2(p, rot)) for p in ((-w / 2, -h0 / 2), (w / 2, -h0 / 2), (w / 2, h0 / 2), (-w / 2, h0 / 2))]
        out += f'<path d="M {" L ".join(P(p) for p in pts)} Z" fill="{col}" stroke="{INK}" stroke-width="1.5" stroke-linejoin="round"/>'
    if layer == 0:
        for k, (x0, ph, col) in enumerate(((80, 0.1, PINK), (250, 0.45, BLUE), (430, 0.75, GOLD))):
            u = (ph + i / 12) % 1.0
            y = -60 + u * 600
            pts = [(x0 + 9 * math.sin(2 * math.pi * (j / 12 * 1.5 + u * 2)), y + j * 6) for j in range(13)]
            out += brush(pts, 9.5, 8.5, INK) + brush(pts, 6.5, 5.5, col)
    return out


def act_celebrate(poses):
    plan = [
        ("站著、彩帶開始落", 0, dict()),
        ("下蹲", 1, dict()),
        ("蓄力深蹲（瞇眼笑）", 2, dict()),
        ("起跳拉長", 3, dict(bottom=18, w=0.95, h=1.06, lag=-0.08, rot=-3)),
        ("往上衝", 3, dict()),
        ("快到頂（張嘴笑）", 4, dict()),
        ("最高點", 5, dict()),
        ("滯空", 5, dict(bottom=4, rot=4, lag=0.04)),
        ("往下落", 4, dict(bottom=30, rot=2, lag=0.10)),
        ("落地壓扁（瞇眼笑）", 6, dict()),
        ("回彈", 7, dict(h=1.03, lag=-0.05)),
        ("站好", 0, dict(h=0.99, w=1.008)),
    ]
    frames = []
    for i, (lab, src, kw) in enumerate(plan):
        g = nat_geom(poses, src, **kw)
        frames.append({"g": g, "label": lab, "back": confetti(i, 0), "front": confetti(i, 1)})
    return frames


ACTIONS = {
    "wave": ("揮手", lambda p: act_wave(p), [140, 80, 70, 70, 70, 70, 70, 70, 70, 70, 80, 140]),
    "point_r": ("指向・右", lambda p: act_point(p, 0, "右"), [140, 80, 60, 60, 70, 90, 60, 70, 60, 90, 70, 80]),
    "point_ur": ("指向・右上", lambda p: act_point(p, 35, "右上"), [140, 80, 60, 60, 70, 90, 60, 70, 60, 90, 70, 80]),
    "point_dr": ("指向・右下", lambda p: act_point(p, -35, "右下"), [140, 80, 60, 60, 70, 90, 60, 70, 60, 90, 70, 80]),
    "tilt": ("歪頭疑問", lambda p: act_tilt(p), [140, 70, 60, 70, 60, 60, 80, 80, 160, 70, 70, 120]),
    "wow": ("驚嘆", lambda p: act_wow(p), [140, 70, 50, 60, 70, 50, 50, 50, 140, 70, 80, 120]),
    "news": ("看財經日曆", lambda p: act_news(p, HUNINN), [120, 80, 100, 80, 80, 110, 70, 90, 80, 90, 90, 80]),
    "coins": ("金幣飛過", lambda p: act_coins(p), [70] * 12),
    "magnifier": ("放大鏡", lambda p: act_magnifier(p), [90, 80, 120, 80, 80, 80, 80, 120, 80, 80, 80, 80]),
    "3dglasses": ("戴 3D 眼鏡", lambda p: act_3dglasses(p), [80, 60, 60, 90, 70, 80, 90, 90, 90, 90, 70, 80]),
    "celebrate": ("慶祝", lambda p: act_celebrate(p), [80, 70, 80, 60, 60, 70, 80, 80, 60, 80, 70, 90]),
    "sign": ("許願牌懸空（牌面留白）", lambda p: act_sign(p), [120, 90, 70, 60, 70, 60, 70, 80, 90, 100, 100, 100]),
    "sign_text": ("許願牌懸空（牌面「許願」）", lambda p: act_sign(p, "許願", HUNINN), [120, 90, 70, 60, 70, 60, 70, 80, 90, 100, 100, 100]),
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
        suffix = "" if "_" not in key else "_" + key.split("_", 1)[1]
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
