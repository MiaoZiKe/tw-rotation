"""逐幀外框碰撞檢查（layout_rules.md）：每個元素登記外框，兩兩外擴 6px 相交就記一筆。

例外只有三種（程式明確白名單）：
  ① 點擊漣漪（不登記）；比比「踩按鈕」整段動作（role=bibi_tap）與網站畫面重疊 → 記入「例外」不算違規
  ② 發光框框線與魔法棒星光（不登記，框內是網站內容本身）
  ③ 半透明浮層壓純空白區（本版版面已改成上下留細帶，浮層全部在帶內，不再壓畫面）
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

CUR: list = []
LOG: list = []      # 違規：(seg, t, a, b, area)
EXC: list = []      # 例外：(seg, t, kind)
EXPAND = 6
BUBBLE_CHK: list = []   # (path 條數, 尾巴 bbox, 文字 box, 其他元素)


def begin():
    CUR.clear()
    BUBBLE_CHK.clear()


def reg(name, rect, role="ui", group=None):
    x0, y0, x1, y1 = rect
    CUR.append((name, (float(x0), float(y0), float(x1), float(y1)), role, group))


def reg_xywh(name, x, y, w, h, role="ui", group=None):
    reg(name, (x, y, x + w, y + h), role, group)


@lru_cache(maxsize=4096)
def _bbox512(path: str):
    a = np.array(Image.open(path).convert("RGBA"))[..., 3]
    ys, xs = np.nonzero(a > 28)
    if len(xs) == 0:
        return (0, 0, 1, 1)
    return (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)


def sprite_rect(path, foot, size):
    s = size / 512
    x0, y0, x1, y1 = _bbox512(path)
    return (foot[0] + (x0 - 248) * s, foot[1] + (y0 - 482) * s, foot[0] + (x1 - 248) * s, foot[1] + (y1 - 482) * s)


def _inter(a, b):
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    w = min(ax1, bx1) - max(ax0, bx0)
    h = min(ay1, by1) - max(ay0, by0)
    return w * h if (w > 0 and h > 0) else 0.0


def end(seg, t, W=None, H=None):
    items = list(CUR)
    for single, tail, text in BUBBLE_CHK:
        if not single:
            LOG.append((seg, round(t, 3), 'bubble', '泡泡非單一路徑', 0))
        if _inter((tail[0] - 10, tail[1] - 10, tail[2] + 10, tail[3] + 10), text) > 0:
            LOG.append((seg, round(t, 3), 'bubble_tail', '尾巴離文字<10px', 0))
    BUBBLE_CHK.clear()
    n = len(items)
    for i in range(n):
        na, ra, roa, ga = items[i]
        ea = (ra[0] - EXPAND, ra[1] - EXPAND, ra[2] + EXPAND, ra[3] + EXPAND)
        for j in range(i + 1, n):
            nb, rb, rob, gb = items[j]
            if ga is not None and ga == gb:
                continue
            eb = (rb[0] - EXPAND, rb[1] - EXPAND, rb[2] + EXPAND, rb[3] + EXPAND)
            ar = _inter(ea, eb)
            if ar <= 0:
                continue
            roles = {roa, rob}
            if roles == {"bibi_tap", "site"} or roles == {"bibi_tap"} or roles == {"bibi_tap", "bibi"}:
                EXC.append((seg, round(t, 3), f"{na}×{nb}"))
                continue
            LOG.append((seg, round(t, 3), na, nb, round(ar)))
    if W:
        for name, r, ro, g in items:
            if r[0] < -2 or r[1] < -2 or r[2] > W + 2 or r[3] > H + 2:
                LOG.append((seg, round(t, 3), name, "畫面外", 0))
