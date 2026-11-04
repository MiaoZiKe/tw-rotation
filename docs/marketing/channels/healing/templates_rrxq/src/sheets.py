#!/usr/bin/env python3
"""總覽圖：templates_overview.png（7 種 × 奶油晨光）、templates_palettes.png（封面 × 4 色調）。"""
import os, json
from PIL import Image, ImageDraw, ImageFont
B = os.path.dirname(os.path.abspath(__file__)); O = os.path.join(B, "..")
F = ImageFont.truetype("/root/.fonts/NotoSansCJKtc-Bold.otf", 34); Fs = ImageFont.truetype("/root/.fonts/NotoSansCJKtc-Regular.otf", 26)
names = [("1_cover", "①IG 輪播封面"), ("2_data", "②數據頁"), ("3_line", "③一句話頁"), ("4_daily", "④今日小晴"), ("5_sources", "⑤出處與求助"), ("6_threads", "⑥Threads 配圖"), ("7_reels", "⑦Reels 封面")]
pal = {"cream": "奶油晨光", "sky": "晴空淡藍", "matcha": "抹茶午後", "peach": "蜜桃傍晚"}
def sheet(items, cols, th, out, title):
    pad, lab = 40, 56
    ims = [(Image.open(f"{O}/{p}"), t) for p, t in items]
    ims = [(im.resize((int(im.width * th / im.height), th), Image.LANCZOS), t) for im, t in ims]
    rows = [ims[i:i + cols] for i in range(0, len(ims), cols)]
    W = max(sum(im.width for im, _ in r) + pad * (len(r) + 1) for r in rows)
    H = 90 + sum(th + lab + pad for _ in rows) + pad
    S = Image.new("RGB", (W, H), "#FAF7F2"); d = ImageDraw.Draw(S); d.text((pad, 26), title, font=F, fill="#3A3A3A")
    y = 90
    for r in rows:
        x = pad
        for im, t in r:
            S.paste(im, (x, y)); d.rectangle([x - 1, y - 1, x + im.width, y + im.height], outline="#CFC8BC", width=2)
            d.text((x, y + th + 12), t, font=Fs, fill="#3A3A3A"); x += im.width + pad
        y += th + lab + pad
    S.save(f"{O}/{out}"); print(out, S.size)
sheet([(f"{t}/{t}_cream.png", n) for t, n in names], 4, 640, "templates_overview.png", "日日小晴 模板總覽（奶油晨光，7 種）")
sheet([(f"1_cover/1_cover_{k}.png", v) for k, v in pal.items()], 4, 640, "templates_palettes.png", "同一張封面 × 4 色調")
