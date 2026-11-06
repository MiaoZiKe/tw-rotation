#!/usr/bin/env python3
import os
from PIL import Image, ImageDraw, ImageFont
O = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "首篇_短版3張")
F = ImageFont.truetype("/root/.fonts/NotoSansCJKtc-Regular.otf", 30)
def row(k): return [Image.open(f"{O}/{k}/{n}.png").convert("RGB") for n in (1, 2, 3)]
def sheet(keys, out, s=.5):
    tw, th = int(1080 * s), int(1350 * s); H = len(keys) * (th + 60) + 20
    img = Image.new("RGB", (3 * (tw + 20) + 20, H), (70, 70, 70)); d = ImageDraw.Draw(img)
    for r, k in enumerate(keys):
        d.text((20, r * (th + 60) + 14), k, font=F, fill=(235, 235, 235))
        for c, im in enumerate(row(k)): img.paste(im.resize((tw, th), Image.LANCZOS), (20 + c * (tw + 20), r * (th + 60) + 56))
    img.save(out)
sheet(["晝版"], O + "/總覽_晝版.png"); sheet(["奶油晨光"], O + "/總覽_奶油晨光.png"); sheet(["晝版", "奶油晨光"], O + "/總覽_晝版vs奶油.png", .42)
