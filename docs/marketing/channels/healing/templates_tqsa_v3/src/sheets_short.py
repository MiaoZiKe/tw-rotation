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
tw, th = 432, 540
img = Image.new("RGB", (3 * (tw + 20) + 20, 56 + th + 20 + 3 * 200 + 40), (70, 70, 70)); d = ImageDraw.Draw(img)
old = Image.open(f"{B}/tmp/pager_B.png").convert("RGB")
d.text((20, 12), "舊 B：實心圓", font=F, fill=(235, 235, 235)); img.paste(old.resize((tw, th), Image.LANCZOS), (20, 56))
d.text((20 + tw + 20, 12), "新 B（主版）：目前頁＝小太陽", font=F, fill=(235, 235, 235)); img.paste(ims[0].resize((tw, th), Image.LANCZOS), (20 + tw + 20, 56))
y0 = 56 + th + 24
for c, im in enumerate(ims):
    x = 20 + c * (tw + 20)
    d.text((x, y0 - 4), "新 B 放大：第 %d 頁" % (c + 1), font=F, fill=(235, 235, 235))
    img.paste(im.crop((690, 1240, 1000, 1300)).resize((432, 84), Image.LANCZOS), (x, y0 + 40))
oldc = old.crop((690, 1240, 1000, 1300)).resize((432, 84), Image.LANCZOS)
d.text((20 + 2 * (tw + 20), 12), "（舊 B 右下放大見下）", font=F, fill=(235, 235, 235)); img.paste(oldc, (20 + 2 * (tw + 20), 56))
img.save(O + "/下一頁記號_比較.png"); print("ok")
