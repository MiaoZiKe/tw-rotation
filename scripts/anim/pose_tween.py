"""動畫設計單位：從「原圖手繪姿勢」排出 12 關鍵幀＋12 中間幀（24 格）→ PNG／總覽圖／GIF／WebP／ZIP。

為什麼有這支
------------
Andy 10-09 交來「角色原圖高保真 GIF 製作總控 Prompt」（docs/anim/prompt_kit/01_總控Prompt.md），
要求：優先保留原圖像素（raster_first）、統一場景座標保留真實位移、12 關鍵幀＋12 中間幀、
I12 接回 K01、不准用透明度疊圖或重複影格冒充補間。

做法（不重畫角色）
------------------
1. 原圖每一格在「未裁切的 512 畫布」上去背（沿用 gif_pipeline.cutout，坑 1～5 都避開），
   再分成「身體」（含耳朵腳，最大連通塊）與「動作線」兩層。
2. 每一個影格寫成一組「目標幾何」：身體寬、高、底部 y、中心 x、旋轉、頂部慣性（lag）。
   關鍵幀直接指定；中間幀把前後兩個關鍵幀的幾何用 ease in/out 內插 —— 所以每一格的
   壓扁／拉長／高度都是真的新姿勢，不是同一張上下搬。
3. 渲染：挑「長寬比最接近目標」的原圖姿勢當像素來源，以腳底中心為錨點做網格變形
   （非均勻垂直縮放：lag>0 時頭頂毛與耳朵比腳慢一拍＝慣性延遲），先放大 2 倍做變形、
   最後一次 LANCZOS 縮回，預乘 alpha 避免白邊。
4. 動作線只平移、不跟著擠壓，只出現在跟原圖同一姿勢的影格。

用法
----
    python scripts/anim/pose_tween.py --src site/brand/src/support_anim_1009.gif --out <輸出資料夾>
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import zipfile
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from gif_pipeline import cutout  # noqa: E402

SS = 2  # 超取樣倍數


# ------------------------------------------------------------------ 原圖 → 身體層＋動作線層
def _component(mask: np.ndarray, seed) -> np.ndarray:
    h, w = mask.shape
    out = np.zeros_like(mask, bool)
    q = deque([seed]); out[seed] = True
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not out[ny, nx]:
                out[ny, nx] = True; q.append((ny, nx))
    return out


def load_poses(src: Path):
    im = Image.open(src)
    poses = []
    for i in range(im.n_frames):
        im.seek(i)
        rgb = np.asarray(im.convert("RGB"))
        a = cutout(rgb) > 0
        ys, xs = np.nonzero(a)
        cy, cx = int(np.median(ys)), int(np.median(xs))
        if not a[cy, cx]:  # 中心點剛好落在洞上就往外找最近的實心點
            d = (ys - cy) ** 2 + (xs - cx) ** 2
            k = int(np.argmin(d)); cy, cx = int(ys[k]), int(xs[k])
        body = _component(a, (cy, cx))
        lines = a & ~body
        by, bx = np.nonzero(body)
        box = (int(bx.min()), int(by.min()), int(bx.max()) + 1, int(by.max()) + 1)
        def rgba(m):
            arr = np.dstack([rgb, np.where(m, 255, 0).astype(np.uint8)])
            return Image.fromarray(arr, "RGBA")
        poses.append({"body": rgba(body), "lines": rgba(lines), "box": box,
                      "has_lines": bool(lines.sum() > 30)})
    return poses


# ------------------------------------------------------------------ 幾何與變形
def ease(t):  # slow in / slow out
    return 0.5 - 0.5 * math.cos(math.pi * t)


def lerp(a, b, t):
    return a + (b - a) * t


def warp_body(pose, g, size):
    """把 pose 身體變形到目標幾何 g（cx, bottom, w, h, rot, lag），回傳 size×size RGBA。"""
    x0, y0, x1, y1 = pose["box"]
    sw, sh = x1 - x0, y1 - y0
    sax, say = (x0 + x1) / 2, y1                    # 原圖錨點：腳底中心
    S = size * SS
    src = pose["body"].resize((pose["body"].width * SS, pose["body"].height * SS), Image.LANCZOS).convert("RGBa")
    sx, sy = g["w"] / sw, g["h"] / sh
    lag = g.get("lag", 0.0)
    rot = math.radians(g.get("rot", 0.0))
    cr, sr = math.cos(rot), math.sin(rot)
    H = g["h"]
    # 垂直非均勻：t＝高度比例（0 腳底、1 頭頂）；dst_t = t + lag*t*(1-t)。反函數用查表。
    tt = np.linspace(0, 1, 401)
    dt = tt + lag * tt * (1 - tt)

    def inv(xo, yo):
        # 目標座標（未超取樣）→ 原圖座標（未超取樣）
        u, v = xo - g["cx"], yo - g["bottom"]
        u, v = cr * u + sr * v, -sr * u + cr * v    # 逆旋轉
        th = -v / H
        if 0 <= th <= dt[-1]:
            ts = float(np.interp(th, dt, tt))
        else:
            ts = th
        return sax + u / sx, say - ts * sh

    step = 16
    mesh = []
    for yo in range(0, size, step):
        for xo in range(0, size, step):
            box = (xo * SS, yo * SS, (xo + step) * SS, (yo + step) * SS)
            q = []
            for px, py in ((xo, yo), (xo, yo + step), (xo + step, yo + step), (xo + step, yo)):
                a, b = inv(px, py); q += [a * SS, b * SS]
            mesh.append((box, q))
    out = src.transform((S, S), Image.MESH, mesh, Image.BICUBIC)
    return out


def place_lines(pose, g, size):
    """動作線只平移（跟著身體錨點走），不擠壓。"""
    x0, y0, x1, y1 = pose["box"]
    dx = g["cx"] - (x0 + x1) / 2
    dy = g["bottom"] - y1
    S = size * SS
    big = pose["lines"].resize((pose["lines"].width * SS, pose["lines"].height * SS), Image.LANCZOS).convert("RGBa")
    canvas = Image.new("RGBa", (S, S), (0, 0, 0, 0))
    canvas.paste(big, (int(round(dx * SS)), int(round(dy * SS))))
    return canvas


def render(poses, spec, size):
    p = poses[spec["src"]]
    layer = warp_body(p, spec, size)
    if spec.get("lines") and p["has_lines"]:
        ln = place_lines(p, spec, size)
        layer = Image.alpha_composite(layer.convert("RGBA"), ln.convert("RGBA")).convert("RGBa")
    return layer.resize((size, size), Image.LANCZOS).convert("RGBA")


# ------------------------------------------------------------------ 跳躍：12 關鍵幀
def jump_keys(poses):
    def nat(i, **kw):  # 原圖姿勢的天然幾何（同一場景座標）
        x0, y0, x1, y1 = poses[i]["box"]
        g = {"src": i, "cx": (x0 + x1) / 2, "bottom": y1, "w": x1 - x0, "h": y1 - y0,
             "rot": 0.0, "lag": 0.0, "lines": False}
        g.update(kw); return g
    k0 = nat(0)
    G = k0["bottom"]                                 # 地面線
    W0, H0 = k0["w"], k0["h"]
    # 原圖 8 格量到的腳底 y：0 待機 485、1 蹲 486、2 深蹲 488、3 起跳 421、4 上升 407、5 最高 379、6 落地 488、7 回正 484
    # → 原 GIF 只有上升沒有下落（5 直接切到 6）。下落段由 K08～K10 用 4／5 的像素反向補出來。
    keys = [
        ("K01 待機",        nat(0)),
        ("K02 下蹲",        nat(1, lines=True)),
        ("K03 蓄力深蹲瞇眼",  nat(2, lines=True)),
        ("K04 起跳拉長",     nat(3, bottom=G - 30, w=W0 * 0.90, h=H0 * 1.10, lag=-0.10, rot=-3)),
        ("K05 上升",        nat(3, lines=True)),
        ("K06 上升到頂前",   nat(4, bottom=395, lines=True)),
        ("K07 最高點",      nat(5, lines=True)),
        ("K08 滯空回圓",     nat(5, bottom=376, rot=4, lag=0.04)),
        ("K09 下落毛往上飄",  nat(4, bottom=432, rot=2, lag=0.12)),
        ("K10 觸地拉長",     nat(4, bottom=G, w=W0 * 0.93, h=H0 * 1.05, lag=0.10)),
        ("K11 落地壓扁",     nat(6, lines=True)),
        ("K12 回彈微拉高",   nat(7, w=W0 * 0.97, h=H0 * 1.04, lag=-0.06)),
    ]
    return keys


def tween(a, b, t, poses):
    e = ease(t)
    g = {k: lerp(a[k], b[k], e) for k in ("cx", "bottom", "w", "h", "rot", "lag")}
    # 像素來源：長寬比最接近目標的原圖姿勢（只從前後兩個關鍵幀的來源挑，避免跳到不相干表情）
    ar = g["w"] / g["h"]
    cand = [a["src"], b["src"]]
    def score(i):
        x0, y0, x1, y1 = poses[i]["box"]; return abs((x1 - x0) / (y1 - y0) - ar)
    g["src"] = min(cand, key=score) if a["src"] != b["src"] else a["src"]
    g["lines"] = False
    return g


# ------------------------------------------------------------------ 輸出
def sheet(frames, labels, cols, path, cell=200, bg=(246, 240, 230)):
    rows = math.ceil(len(frames) / cols)
    pad, lab = 6, 22
    W = cols * (cell + pad) + pad
    Hh = rows * (cell + lab + pad) + pad
    img = Image.new("RGB", (W, Hh), (40, 40, 48))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 14)
    except OSError:
        font = ImageFont.load_default()
    for i, (f, t) in enumerate(zip(frames, labels)):
        r, c = divmod(i, cols)
        x = pad + c * (cell + pad); y = pad + r * (cell + lab + pad)
        tile = Image.new("RGB", (cell, cell), bg)
        tile.paste(f.resize((cell, cell), Image.LANCZOS), (0, 0), f.resize((cell, cell), Image.LANCZOS))
        img.paste(tile, (x, y + lab))
        d.text((x + 4, y + 3), t, fill=(240, 240, 240), font=font)
        d.line([(x, y + lab + cell * 0.92), (x + cell, y + lab + cell * 0.92)], fill=(200, 190, 175))
    img.save(path)


def save_gif(frames, dur, loop, path):
    pal = []
    for f in frames:
        a = np.asarray(f)[:, :, 3]
        rgb = f.convert("RGB").quantize(colors=255, method=Image.MEDIANCUT, dither=Image.NONE)
        arr = np.asarray(rgb).copy()
        arr[a < 128] = 255
        p = Image.fromarray(arr, "P"); p.putpalette(rgb.getpalette()[:765] + [0, 0, 0])
        p.info["transparency"] = 255
        pal.append(p)
    pal[0].save(path, save_all=True, append_images=pal[1:], duration=dur, loop=loop,
                disposal=2, transparency=255, optimize=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", type=int, default=512)
    ap.add_argument("--duration", type=int, default=50)
    ap.add_argument("--loop", type=int, default=0)
    a = ap.parse_args()
    out = Path(a.out)
    for sub in ("keyframes", "inbetweens", "frames"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    poses = load_poses(Path(a.src))
    keys = jump_keys(poses)
    n = len(keys)
    K = [render(poses, g, a.size) for _, g in keys]
    I, Ispec = [], []
    for i in range(n):
        g = tween(keys[i][1], keys[(i + 1) % n][1], 0.5, poses)
        Ispec.append(g); I.append(render(poses, g, a.size))
    for i in range(n):
        K[i].save(out / "keyframes" / f"K{i+1:02d}.png")
        I[i].save(out / "inbetweens" / f"I{i+1:02d}.png")
    frames, labels = [], []
    for i in range(n):
        frames += [K[i], I[i]]
        labels += [keys[i][0], f"I{i+1:02d} {keys[i][0][:3]}→K{(i+1)%n+1:02d}"]
    for j, f in enumerate(frames):
        f.save(out / "frames" / f"frame_{j+1:02d}.png")
    sheet(K, [k for k, _ in keys], 6, out / "keyframes_12.png")
    sheet(frames, [f"{j+1:02d} " + l for j, l in enumerate(labels)], 6, out / "storyboard_24.png")
    save_gif(frames, a.duration, a.loop, out / "animation.gif")
    frames[0].save(out / "animation.webp", save_all=True, append_images=frames[1:], duration=a.duration,
                   loop=a.loop, lossless=False, quality=90, method=6)
    # 驗證
    g = Image.open(out / "animation.gif")
    arrs = []
    for k in range(g.n_frames):
        g.seek(k); arrs.append(np.asarray(g.convert("RGBA")).astype(int))
    diffs = [int(np.abs(arrs[k] - arrs[(k + 1) % len(arrs)]).sum() // 1000) for k in range(len(arrs))]
    report = {"n_frames": g.n_frames, "duration": g.info.get("duration"), "loop": g.info.get("loop"),
              "size": list(g.size), "min_adjacent_diff_k": min(diffs), "adjacent_diff_k": diffs,
              "sources": {"K": [s["src"] for _, s in keys], "I": [s["src"] for s in Ispec]}}
    (out / "verify.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    with zipfile.ZipFile(out / "assets.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(out.rglob("*")):
            if p.is_file() and p.name != "assets.zip":
                z.write(p, p.relative_to(out))
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
