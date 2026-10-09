"""動畫設計單位：把「已經畫好的 N 格分鏡總表」裁成獨立影格 → 對齊 → GIF／WebP／總覽／ZIP（不重畫角色）。

總控 Prompt（docs/anim/prompt_kit/01_總控Prompt.md）INPUT_TYPE=storyboard 的做法：
只裁切、去掉標題編號、統一畫布、合成。AI 生的分鏡每格桌面高度會差幾 px，
所以用「桌面線」量垂直位移、用畫面下方（桌面／滑鼠／椅子）比對找水平位移，把每格對回第 1 格，
否則播放時整個場景會上下跳。

用法（2026-10-09 天竺鼠看盤 12 格）：
    python scripts/anim/storyboard_grid.py --in site/brand/src/laptop_storyboard_1009.webp --out docs/anim/laptop
"""
from __future__ import annotations
import argparse, json, zipfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# 卡片左上角（從總表量的）；美術區＝卡片內 (L,T) 起 W×W，避開上方 FRAME 字樣與圓角
CARDS = [(x, y) for y in (20, 420, 820) for x in (22, 400, 778, 1156)]
L, T, W, M = 18, 44, 332, 14
DESK = np.array([239, 200, 161])
DUR = [700, 350, 600, 350, 300, 300, 350, 300, 450, 400, 650, 450]   # 每格停留 ms（依表演節奏）


def desk_top(a, x, y):
    col = a[y + 40:y + 385, x + 30]
    tan = np.abs(col - DESK).sum(1) < 45
    return next(k for k in range(len(col) - 10) if tan[k:k + 10].all()) + 40


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", type=int, default=512)
    a = ap.parse_args()
    out = Path(a.out); (out / "frames").mkdir(parents=True, exist_ok=True)
    im = Image.open(a.src).convert("RGB"); arr = np.asarray(im).astype(int)
    d0 = desk_top(arr, *CARDS[0])
    ref = arr[CARDS[0][1] + T + int(W * .65):CARDS[0][1] + T + W, CARDS[0][0] + L:CARDS[0][0] + L + W]
    frames, shifts = [], []
    for (x, y) in CARDS:
        dy = desk_top(arr, x, y) - d0
        best = min(((np.abs(arr[y + T + dy + int(W * .65):y + T + dy + W, x + L + dx:x + L + dx + W] - ref).mean(), dx)
                    for dx in range(-M, M + 1)))
        dx = best[1]; shifts.append((dx, dy))
        f = im.crop((x + L + dx, y + T + dy, x + L + dx + W, y + T + dy + W)).resize((a.size, a.size), Image.LANCZOS)
        frames.append(f)
    for i, f in enumerate(frames):
        f.save(out / "frames" / f"frame_{i+1:02d}.png")
    pal = [f.quantize(colors=256, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG) for f in frames]
    pal[0].save(out / "animation.gif", save_all=True, append_images=pal[1:], duration=DUR, loop=0, disposal=1)
    frames[0].save(out / "animation.webp", save_all=True, append_images=frames[1:], duration=DUR, loop=0, quality=88, method=6)
    small = [f.resize((256, 256), Image.LANCZOS) for f in frames]
    sp = [f.quantize(colors=128, method=Image.MEDIANCUT) for f in small]
    sp[0].save(out / "animation-256.gif", save_all=True, append_images=sp[1:], duration=DUR, loop=0)
    # 總覽
    c, pad, lab = 240, 8, 24
    sheet = Image.new("RGB", (4 * (c + pad) + pad, 3 * (c + lab + pad) + pad), (40, 40, 48))
    dr = ImageDraw.Draw(sheet)
    font = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 15)
    for i, f in enumerate(frames):
        r, k = divmod(i, 4); X = pad + k * (c + pad); Y = pad + r * (c + lab + pad)
        sheet.paste(f.resize((c, c), Image.LANCZOS), (X, Y + lab))
        dr.text((X + 4, Y + 4), f"{i+1:02d}  {DUR[i]}ms  位移({shifts[i][0]},{shifts[i][1]})", fill=(235, 235, 235), font=font)
    sheet.save(out / "storyboard_12.png")
    g = Image.open(out / "animation.gif"); n = g.n_frames
    ds = []
    for k in range(n):
        g.seek(k); ds.append(g.info.get("duration"))
    rep = {"n_frames": n, "durations": ds, "total_ms": sum(ds), "loop": g.info.get("loop"), "size": list(g.size),
           "shifts_dx_dy": shifts}
    (out / "verify.json").write_text(json.dumps(rep, ensure_ascii=False), encoding="utf-8")
    with zipfile.ZipFile(out / "assets.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(out.rglob("*")):
            if p.is_file() and p.suffix != ".zip":
                z.write(p, p.relative_to(out))
    print(json.dumps(rep, ensure_ascii=False))


if __name__ == "__main__":
    main()
