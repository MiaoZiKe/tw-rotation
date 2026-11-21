#!/usr/bin/env python3
"""對比檢查：以「無字底圖」（含顆粒、暗角、卡片）實取每個文字框內的底色，取最亮與最暗兩端，
對文字色算 WCAG 對比，取最差值；≥ 4.5 才過。結果併入各篇 overlap_report.json 的 contrast 欄。"""
import json, os, re, sys
from PIL import Image
B = os.path.dirname(os.path.abspath(__file__))
def lin(c):
    c /= 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
def lum(rgb): return 0.2126 * lin(rgb[0]) + 0.7152 * lin(rgb[1]) + 0.0722 * lin(rgb[2])
def cr(a, b):
    a, b = max(a, b), min(a, b); return (a + 0.05) / (b + 0.05)
bad = 0; total = 0; worst_all = 99
for p in ("post1", "post2", "post3", "post4"):
    d = os.path.join(B, p); rep = json.load(open(d + "/overlap_report.json")); mf = json.load(open(d + "/manifest.json"))
    for name in mf:
        im = Image.open(f"{d}/{name}.bg.png").convert("RGB"); tx = json.load(open(f"{d}/{name}.tx.json"))
        worst = 99; items = []
        for t in tx:
            m = re.findall(r"[\d.]+", t["color"]); col = tuple(int(float(x)) for x in m[:3])
            box = (max(0, int(t["x"])), max(0, int(t["y"])), min(1080, int(t["x"] + t["w"]) + 1), min(1350, int(t["y"] + t["h"]) + 1))
            px = list(im.crop(box).convert("RGB").getdata()); ls = sorted(lum(q) for q in px)
            lo, hi = ls[int(len(ls) * 0.01)], ls[int(len(ls) * 0.99)]
            c = min(cr(lum(col), lo), cr(lum(col), hi)); items.append((round(c, 2), t["t"]))
            worst = min(worst, c)
        rep[name]["contrast_min"] = round(worst, 2); rep[name]["contrast_pass"] = worst >= 7.0
        total += 1; worst_all = min(worst_all, worst)
        if worst < 7.0: bad += 1; print("對比不足", p, name, sorted(items)[:3])
    json.dump(rep, open(d + "/overlap_report.json", "w"), ensure_ascii=False, indent=1)
print("對比檢查 %d 張，不過（門檻 7） %d 張，最差 %.2f" % (total, bad, worst_all))
