#!/usr/bin/env python3
"""談晴說礙說明型貼文（gen_posts.py）對比檢查：以「無字底圖」（含顆粒、暗角、插圖）實取每個文字框內的底色，取最亮與最暗兩端，
對文字色算 WCAG 對比，取最差值；≥ 4.5 才過。結果併入 ../overlap_report.json 的 contrast_min／contrast_pass。"""
import json, os, re
from PIL import Image
B = os.path.dirname(os.path.abspath(__file__)); mf = json.load(open(B + "/manifest_posts.json")); Q = B + "/../../queue/"
reps = {p: json.load(open(Q + p + "/overlap_report.json")) for p in {m["post"] for m in mf}}
def lin(c):
    c /= 255; return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
def lum(rgb): return 0.2126 * lin(rgb[0]) + 0.7152 * lin(rgb[1]) + 0.0722 * lin(rgb[2])
def cr(a, b): a, b = max(a, b), min(a, b); return (a + 0.05) / (b + 0.05)
bad = 0; worst_all = 99; worst_key = ""
for m in mf:
    k = m["key"]; stem = os.path.join(B, "tmp", k.replace("/", "__"))
    im = Image.open(stem + ".bg.png").convert("RGB"); tx = json.load(open(stem + ".tx.json")); worst = 99
    for t in tx:
        col = tuple(int(float(x)) for x in re.findall(r"[\d.]+", t["color"])[:3])
        box = (max(0, int(t["x"])), max(0, int(t["y"])), min(m["W"], int(t["x"] + t["w"]) + 1), min(m["H"], int(t["y"] + t["h"]) + 1))
        ls = sorted(lum(q) for q in im.crop(box).get_flattened_data()); lo, hi = ls[int(len(ls) * .01)], ls[int(len(ls) * .99)]
        worst = min(worst, cr(lum(col), lo), cr(lum(col), hi))
    reps[m["post"]][k]["contrast_min"] = round(worst, 2); reps[m["post"]][k]["contrast_pass"] = worst >= 4.5
    if worst < 4.5: bad += 1; print("對比不足", k, round(worst, 2))
    if worst < worst_all: worst_all, worst_key = worst, k
for p, rep in reps.items(): json.dump(rep, open(Q + p + "/overlap_report.json", "w"), ensure_ascii=False, indent=1)
print("對比檢查 %d 張，不過（門檻 4.5）%d 張，最差 %.2f（%s）" % (len(mf), bad, worst_all, worst_key))
