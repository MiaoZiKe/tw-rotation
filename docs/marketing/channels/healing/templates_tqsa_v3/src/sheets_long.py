#!/usr/bin/env python3
import os
from PIL import Image
O = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "首篇_長版2頁")
for k in ("奶油晨光", "晝版", "黑白混搭"):
    ims = [Image.open(f"{O}/{k}/{n}.png").convert("RGB") for n in (1, 2)]
    img = Image.new("RGB", (2 * 1080 + 60, 1350 + 40), (70, 70, 70)); img.paste(ims[0], (20, 20)); img.paste(ims[1], (1120, 20))
    img = img.resize((img.width * 6 // 10, img.height * 6 // 10), Image.LANCZOS); img.save(f"{O}/總覽_{k}.png")
print("ok")
