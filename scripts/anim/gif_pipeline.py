"""動畫設計單位：分鏡 → 逐格 → 去背 → 合成 GIF／WebP 的整套流程（2026-10-09 建）

為什麼有這支
------------
Andy 10-09：「幫我將 LOGO GIF 圖設計成立動畫設計單位，之後會需要請相關人員製作動畫以及 GIF 圖片…
將上述從給你分鏡圖片到你合成 GIF 以及去背整套流程寫個系統先儲存」。

那天客服鈕 GIF 前後退了三次件，每一次的根因都是流程上的坑，這支把它們固定下來：
  1. 只在「第一格」寫了透明色 → 其他格的背景還在（PIL 存 GIF 時沒每格帶 transparency）。
  2. 先裁切再去背 → 天竺鼠跳起來那兩格頭頂碰到裁切邊，灌水從邊緣直接灌進身體，整隻被挖空。
  3. 描邊有細縫（毛邊、動態模糊） → 灌水從縫漏進去。要先把深色描邊往外擴幾 px 補縫。
  4. 地上的淡色影子跟背景相連 → 用「亮度 > 門檻」一起吃掉，只留本體。
  5. 圖片本身加了 CSS drop-shadow → 在淺色底上看起來像「還有背景」（Andy 第三次退件的原因）。
     → 去背結果一律不加陰影；要陰影由使用端決定，而且要先問。

用法
----
    # 一條龍：輸入 GIF／MP4／一個資料夾的分鏡圖 → 去背 → 輸出 128px GIF＋WebP＋第一格 PNG＋檢查圖
    python scripts/anim/gif_pipeline.py run --in site/brand/src/support_anim_1009.gif \
        --out site/brand/sup-anim --sizes 128 --fps 10

    # 分鏡圖資料夾（檔名排序就是播放順序；每張停多久可用 --hold 重複幀數，或 --durations 逐張指定 ms）
    python scripts/anim/gif_pipeline.py run --in docs/anim/mascot_wave/frames/ --out site/brand/mascot-wave \
        --sizes 64,128 --durations 120,120,120,400

    # 只看去背結果（不輸出成品）：產生 洋紅／深色／淺色 三種底的檢查圖
    python scripts/anim/gif_pipeline.py check --in site/brand/sup-anim-128.gif

參數重點
--------
--dark   描邊判定門檻（亮度 < 這個值算描邊，預設 150）。角色描邊是淺色時要調高或改用 --bg-color。
--seal   描邊補縫半徑 px（預設 2；若有格子被挖空，腳本會自動往上試 3、5、7）。
--light  背景／影子判定門檻（亮度 > 這個值、且跟背景相連 → 透明，預設 150）。
--bg-color  背景是單一純色（例如綠幕 00ff00）時改用色差去背，比灌水準。
--keep-shadow  保留地上的影子（預設會吃掉）。
--pad    裁切時在所有格聯集框外多留幾 px（預設 8）。

輸出（以 --out site/brand/sup-anim、--sizes 128 為例）
  site/brand/sup-anim-128.gif     每一格都帶透明（二值 alpha，GIF 只支援全透／不透）
  site/brand/sup-anim-128.webp    動態 WebP，真的半透明邊緣、檔案通常更小（新瀏覽器優先用）
  site/brand/sup-anim-128.png     第一格靜態圖（減少動態偏好、或當封面）
  <scratchpad 或 --sheet 指定>/sheet_*.png   洋紅／深色／淺色三種底的逐格檢查圖 —— 交件前一定要用 Read 打開看

依賴：Pillow、numpy（imageio-ffmpeg 只有輸入 MP4 時才需要）。不需要 scipy。
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageSequence

IMG_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


# ------------------------------------------------------------------ 讀入
def load_frames(src: str, hold: int = 1, fps: float | None = None, durations: list[int] | None = None):
    """回傳 [(RGB ndarray, duration_ms), ...]。支援 GIF／動態 WebP／MP4／MOV／資料夾（分鏡圖）。"""
    p = Path(src)
    out: list[tuple[np.ndarray, int]] = []
    if p.is_dir():
        files = sorted(f for f in p.iterdir() if f.suffix.lower() in IMG_EXT)
        if not files:
            sys.exit(f"資料夾裡沒有圖：{p}")
        base = int(1000 / fps) if fps else 100
        for i, f in enumerate(files):
            d = durations[i] if durations and i < len(durations) else base
            for _ in range(max(1, hold)):
                out.append((np.asarray(Image.open(f).convert("RGB")), d))
    elif p.suffix.lower() in (".mp4", ".mov", ".webm", ".m4v"):
        try:
            import imageio_ffmpeg
        except ImportError:
            sys.exit("輸入影片需要 imageio-ffmpeg：pip install imageio-ffmpeg")
        ff = imageio_ffmpeg.get_ffmpeg_exe()
        rate = fps or 12
        tmp = Path(os.environ.get("TMPDIR", "/tmp")) / f"gifpipe_{os.getpid()}"
        tmp.mkdir(parents=True, exist_ok=True)
        subprocess.run([ff, "-loglevel", "error", "-i", str(p), "-vf", f"fps={rate}", str(tmp / "f_%04d.png")], check=True)
        for f in sorted(tmp.glob("f_*.png")):
            out.append((np.asarray(Image.open(f).convert("RGB")), int(1000 / rate)))
    else:
        im = Image.open(p)
        for f in ImageSequence.Iterator(im):
            d = f.info.get("duration", im.info.get("duration", 100)) or 100
            out.append((np.asarray(f.convert("RGB")), int(d)))
    if durations and not p.is_dir():
        out = [(a, durations[i] if i < len(durations) else d) for i, (a, d) in enumerate(out)]
    return out


# ------------------------------------------------------------------ 去背
def _dilate(m: np.ndarray, r: int) -> np.ndarray:
    o = m.copy()
    for _ in range(r):
        n = o.copy()
        n[1:] |= o[:-1]; n[:-1] |= o[1:]; n[:, 1:] |= o[:, :-1]; n[:, :-1] |= o[:, 1:]
        o = n
    return o


def _flood(passable: np.ndarray) -> np.ndarray:
    """從四條邊往內灌水，回傳「跟邊緣相連、且可通過」的像素。"""
    H, W = passable.shape
    bg = np.zeros((H, W), bool)
    q: deque = deque()
    edge = [(y, x) for x in range(W) for y in (0, H - 1)] + [(y, x) for y in range(H) for x in (0, W - 1)]
    for y, x in edge:
        if passable[y, x] and not bg[y, x]:
            bg[y, x] = True; q.append((y, x))
    while q:
        y, x = q.popleft()
        for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
            if 0 <= ny < H and 0 <= nx < W and not bg[ny, nx] and passable[ny, nx]:
                bg[ny, nx] = True; q.append((ny, nx))
    return bg


def cutout(rgb: np.ndarray, dark=150, seal=2, light=150, fringe=110, bg_color=None, bg_tol=40,
           keep_shadow=False, min_body=0.08) -> np.ndarray:
    """回傳 alpha（0／255）。⚠ 一定要在「還沒裁切」的原圖上做（坑 2）。"""
    a = rgb.astype(int)
    lum = a.mean(axis=2)
    if bg_color is not None:                       # 純色背景（綠幕）：色差去背
        diff = np.abs(a - np.array(bg_color)).sum(axis=2)
        bg = _flood(diff < bg_tol)
        return np.where(bg, 0, 255).astype(np.uint8)
    d = lum < dark
    total = lum.size
    for r in (seal, seal + 1, seal + 3, seal + 5, seal + 8):   # 補縫半徑不夠就自動加大（坑 3）
        bg = _flood(~_dilate(d, r))
        if (~bg).sum() > min_body * total:
            break
    grow = light if not keep_shadow else 230
    for _ in range(r + 1):                         # 把補縫時吃掉的那圈背景補回來（坑 4：順便吃掉影子）
        bg |= _dilate(bg, 1) & (lum > grow)
    bg |= _dilate(bg, 1) & (lum > fringe)          # 再吃 1px 淡色毛邊
    return np.where(bg, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------ 輸出
def union_box(alphas: list[np.ndarray], pad: int):
    m = np.any(np.stack([al > 0 for al in alphas]), axis=0)
    ys, xs = np.where(m)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    side = max(y1 - y0, x1 - x0) + 2 * pad
    cy, cx = (y0 + y1) // 2, (x0 + x1) // 2
    return (int(cx - side // 2), int(cy - side // 2), int(cx - side // 2 + side), int(cy - side // 2 + side))


def render(frames, alphas, box, size: int):
    outs = []
    for (rgb, _), al in zip(frames, alphas):
        im = Image.fromarray(np.dstack([rgb, al]), "RGBA").crop(box).resize((size, size), Image.LANCZOS)
        outs.append(im)
    return outs


def save_gif(frames_rgba, durations, path: Path):
    """GIF 只有全透／不透：alpha 二值化，每一格都帶透明（坑 1：交給 Pillow 的 RGBA 存法逐格處理）。"""
    fixed = []
    for im in frames_rgba:
        ar = np.asarray(im).copy()
        ar[..., 3] = np.where(ar[..., 3] >= 128, 255, 0)
        fixed.append(Image.fromarray(ar, "RGBA"))
    fixed[0].save(path, save_all=True, append_images=fixed[1:], duration=durations, loop=0, disposal=2)


def save_webp(frames_rgba, durations, path: Path):
    frames_rgba[0].save(path, save_all=True, append_images=frames_rgba[1:], duration=durations, loop=0,
                        lossless=False, quality=90, method=6)


def sheet(frames_rgba, path: Path):
    """逐格檢查圖：洋紅（抓殘留背景最明顯）／深色主題底／淺色主題底 三排。"""
    n, s = len(frames_rgba), frames_rgba[0].size[0]
    rows = [(255, 0, 255, 255), (14, 22, 40, 255), (244, 247, 252, 255)]
    sh = Image.new("RGBA", (s * n, s * len(rows)))
    for r, c in enumerate(rows):
        sh.paste(c, (0, r * s, s * n, (r + 1) * s))
        for i, f in enumerate(frames_rgba):
            sh.alpha_composite(f.convert("RGBA"), (i * s, r * s))
    sh.save(path)


def verify_gif(path: Path):
    """讀回成品：每一格的四個角都要是透明（不是就代表某格背景沒去掉）。"""
    bad = []
    for i, f in enumerate(ImageSequence.Iterator(Image.open(path))):
        ar = np.asarray(f.convert("RGBA"))
        h, w = ar.shape[:2]
        if any(ar[y, x, 3] for y, x in ((0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1))):
            bad.append(i)
    return bad


# ------------------------------------------------------------------ 指令
def main():
    ap = argparse.ArgumentParser(description="分鏡／GIF／影片 → 去背 → GIF＋WebP＋PNG＋檢查圖")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--in", dest="src", required=True)
    r.add_argument("--out", required=True, help="輸出前綴，例如 site/brand/sup-anim（會加 -128.gif 等）")
    r.add_argument("--sizes", default="128")
    r.add_argument("--fps", type=float, default=None)
    r.add_argument("--hold", type=int, default=1, help="分鏡圖每張重複幾格")
    r.add_argument("--durations", default="", help="逐格毫秒，逗號分隔")
    r.add_argument("--dark", type=int, default=150)
    r.add_argument("--seal", type=int, default=2)
    r.add_argument("--light", type=int, default=150)
    r.add_argument("--bg-color", default="", help="純色背景，例如 00ff00")
    r.add_argument("--keep-shadow", action="store_true")
    r.add_argument("--pad", type=int, default=8)
    r.add_argument("--no-webp", action="store_true")
    r.add_argument("--sheet", default="", help="檢查圖輸出資料夾（預設跟成品同資料夾的 _check/，不進版控請自行刪）")
    c = sub.add_parser("check")
    c.add_argument("--in", dest="src", required=True)
    c.add_argument("--sheet", default="")
    a = ap.parse_args()

    if a.cmd == "check":
        frames = [f.convert("RGBA") for f in ImageSequence.Iterator(Image.open(a.src))]
        dst = Path(a.sheet or Path(a.src).parent / "_check")
        dst.mkdir(parents=True, exist_ok=True)
        sheet(frames, dst / f"sheet_{Path(a.src).stem}.png")
        bad = verify_gif(Path(a.src)) if a.src.lower().endswith(".gif") else []
        print(f"檢查圖：{dst / f'sheet_{Path(a.src).stem}.png'}；角落不透明的格：{bad or '無'}")
        return

    durs = [int(x) for x in a.durations.split(",") if x.strip()] or None
    frames = load_frames(a.src, a.hold, a.fps, durs)
    bgc = tuple(int(a.bg_color[i:i + 2], 16) for i in (0, 2, 4)) if a.bg_color else None
    alphas = [cutout(rgb, dark=a.dark, seal=a.seal, light=a.light, bg_color=bgc, keep_shadow=a.keep_shadow)
              for rgb, _ in frames]
    body = [int((al > 0).sum()) for al in alphas]
    med = sorted(body)[len(body) // 2]
    for i, b in enumerate(body):
        if b < 0.5 * med:
            print(f"⚠ 第 {i} 格本體面積只有中位數的 {b / med:.0%}，可能被灌水挖空 —— 加大 --seal 或改 --bg-color")
    box = union_box(alphas, a.pad)
    dts = [d for _, d in frames]
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    chk = Path(a.sheet) if a.sheet else out.parent / "_check"
    chk.mkdir(parents=True, exist_ok=True)
    for s in [int(x) for x in a.sizes.split(",")]:
        imgs = render(frames, alphas, box, s)
        g = out.with_name(f"{out.name}-{s}.gif"); save_gif(imgs, dts, g)
        if not a.no_webp:
            save_webp(imgs, dts, out.with_name(f"{out.name}-{s}.webp"))
        imgs[0].save(out.with_name(f"{out.name}-{s}.png"), optimize=True)
        sheet(imgs, chk / f"sheet_{out.name}-{s}.png")
        bad = verify_gif(g)
        print(f"{g}（{g.stat().st_size // 1024} KB，{len(imgs)} 格）角落不透明的格：{bad or '無'}")
    print(f"檢查圖在 {chk}/ —— 交件前用 Read 打開看三種底（洋紅／深／淺）每一格")


if __name__ == "__main__":
    main()
