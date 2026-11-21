"""吉祥物精靈圖去背（512 原圖 → assets/mascot_sheet.png，每格 384px）。

做法（跟 site/brand/sup-anim-128.gif 同一套）：
1. 深色描邊（亮度 < 150）往外擴 2px，把描邊上的小縫補起來；
2. 從四邊做 flood fill（只走非描邊像素）標出背景；
3. 背景往描邊方向補回：背景中緊貼描邊、亮度 > 150 的像素還給背景（去白邊）；
4. 再吃掉 1px 亮度 > 110 的毛邊；alpha 二值化。
跳起來那兩格、底下的影子都會被當成背景去掉。
用法：python docs/marketing/video/make_mascot.py <原圖 gif> <輸出 png>
"""
import sys
from collections import deque

import numpy as np
from PIL import Image


def dilate(m: np.ndarray, iterations: int = 1) -> np.ndarray:
    """8 鄰接膨脹（只用 numpy，不依賴 scipy）。"""
    for _ in range(iterations):
        p = np.pad(m, 1)
        out = np.zeros_like(m)
        for dy in (0, 1, 2):
            for dx in (0, 1, 2):
                out |= p[dy:dy + m.shape[0], dx:dx + m.shape[1]]
        m = out
    return m


def matte(rgb: np.ndarray) -> np.ndarray:
    lum = rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114
    line = lum < 150
    wall = dilate(line, 2)
    free = ~wall
    h, w = free.shape
    bg = np.zeros_like(free)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if free[y, x] and not bg[y, x]:
                bg[y, x] = True; q.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if free[y, x] and not bg[y, x]:
                bg[y, x] = True; q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and free[ny, nx] and not bg[ny, nx]:
                bg[ny, nx] = True; q.append((ny, nx))
    # 背景往描邊方向補回亮度 > 150 的像素（擴 2px 時吃進去的白邊）
    for _ in range(3):
        grow = dilate(bg) & ~bg & (lum > 150)
        if not grow.any():
            break
        bg |= grow
    # 再吃 1px 亮度 > 110 的毛邊
    bg |= dilate(bg) & (lum > 110)
    return ~bg


def main(src: str, out: str, cell: int = 384) -> None:
    im = Image.open(src)
    n = im.n_frames
    sheet = Image.new("RGBA", (cell * n, cell), (0, 0, 0, 0))
    for i in range(n):
        im.seek(i)
        fr = im.convert("RGB")
        a = matte(np.asarray(fr).astype(np.float32))
        rgba = fr.convert("RGBA")
        rgba.putalpha(Image.fromarray((a * 255).astype(np.uint8)))
        sheet.paste(rgba.resize((cell, cell), Image.LANCZOS), (cell * i, 0))
    sheet.save(out)
    print("寫出", out, n, "格")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
