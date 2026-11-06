#!/usr/bin/env python3
"""總覽_晝版.png（3 頁並排）與 下一頁記號_比較.png（同一張封面套 A／B／C，上排整張縮圖、下排右下角 2 倍放大）。"""
import os
from PIL import Image, ImageDraw, ImageFont
B = os.path.dirname(os.path.abspath(__file__)); O = os.path.join(B, "..", "首篇_短版3張")
F = ImageFont.truetype("/root/.fonts/NotoSansCJKtc-Regular.otf", 30)
ims = [Image.open(f"{O}/晝版/{n}.png").convert("RGB") for n in (1, 2, 3)]
s = .5; tw, th = int(1080 * s), int(1350 * s)
img = Image.new("RGB", (3 * (tw + 20) + 20, th + 60 + 20), (70, 70, 70)); d = ImageDraw.Draw(img); d.text((20, 14), "晝版（預設）", font=F, fill=(235, 235, 235))
for c, im in enumerate(ims): img.paste(im.resize((tw, th), Image.LANCZOS), (20 + c * (tw + 20), 56))
img.save(O + "/總覽_晝版.png")
names = {"A": "A：頁數＋箭頭", "B": "B：頁點＋箭頭", "C": "C 主版：雲→小太陽"}
tw, th = 432, 540
img = Image.new("RGB", (3 * (tw + 20) + 20, 60 + th + 20 + 330), (70, 70, 70)); d = ImageDraw.Draw(img)
for c, k in enumerate("ABC"):
    im = Image.open(f"{B}/tmp/pager_{k}.png").convert("RGB"); x = 20 + c * (tw + 20)
    d.text((x, 14), names[k], font=F, fill=(235, 235, 235)); img.paste(im.resize((tw, th), Image.LANCZOS), (x, 56))
    crop = im.crop((640, 1200, 1080, 1320)).resize((880 // 2 * 1, 240 // 2 * 1 * 1), Image.LANCZOS)
    crop = im.crop((680, 1220, 1000, 1310)).resize((432, 122), Image.LANCZOS); img.paste(crop, (x, 56 + th + 20))
    crop2 = im.crop((680, 1220, 1000, 1310)).resize((640, 180), Image.LANCZOS)
img.save(O + "/下一頁記號_比較.png"); print("ok")
