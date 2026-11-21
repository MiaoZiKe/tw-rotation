#!/usr/bin/env python3
"""對比檢查：取「文字拿掉後的底圖」在每個文字框內的最亮／最暗兩端（1%／99% 分位），對文字色算 WCAG 對比，要 ≥ 4.5。"""
import json, os, re
from PIL import Image
B = os.path.dirname(os.path.abspath(__file__))
def lin(c):
    c /= 255; return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
def lum(r): return .2126 * lin(r[0]) + .7152 * lin(r[1]) + .0722 * lin(r[2])
def cr(a, b): a, b = max(a, b), min(a, b); return (a + .05) / (b + .05)
rep = json.load(open(B + "/report.json")); bad = 0; worst_all = 99; tot = 0; per = {}
for name, r in rep.items():
    im = Image.open(f"{B}/bg_{name}.png").convert("RGB"); worst = 99
    for t in r["boxes"]:
        if not t["txt"]: continue
        col = tuple(int(float(x)) for x in re.findall(r"[\d.]+", t["color"])[:3])
        box = (max(0, t["x"]), max(0, t["y"]), min(im.width, t["r"] + 1), min(im.height, t["b"] + 1))
        ls = sorted(lum(q) for q in im.crop(box).getdata())
        lo, hi = ls[int(len(ls) * .01)], ls[int(len(ls) * .99)]
        c = min(cr(lum(col), lo), cr(lum(col), hi)); worst = min(worst, c)
        if c < 4.5: print("對比不足", name, t["o"], round(c, 2))
    per[name] = round(worst, 2); tot += 1; worst_all = min(worst_all, worst); bad += worst < 4.5
json.dump(per, open(B + "/contrast.json", "w")); print("對比檢查 %d 張，不過 %d 張，最差 %.2f" % (tot, bad, worst_all))
