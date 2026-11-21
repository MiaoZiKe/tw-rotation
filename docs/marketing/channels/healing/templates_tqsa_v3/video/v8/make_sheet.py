#!/usr/bin/env python3
"""總覽圖（sheet）：從成片每鏡抽一格（該鏡 70% 處；片尾取最後 0.3 秒），4 欄排成一張 PNG。用法：python3 v8/make_sheet.py <mp4> <報告 json（含 scenes）> <輸出 png>"""
import sys, json, subprocess, tempfile, os
from PIL import Image, ImageDraw, ImageFont
mp4, rep, out = sys.argv[1:4]; sc = json.load(open(rep))["scenes"]; d = tempfile.mkdtemp(); ims = []
ft = ImageFont.truetype("/root/.fonts/NotoSansCJKtc-Bold.otf", 28) if os.path.exists("/root/.fonts/NotoSansCJKtc-Bold.otf") else None
for i, s in enumerate(sc):
    t = s["t1"] - .3 if s["type"] == "outro" else s["t0"] + .7 * (s["t1"] - s["t0"])
    f = os.path.join(d, "%02d.png" % i); subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "%.3f" % t, "-i", mp4, "-frames:v", "1", f], check=True)
    im = Image.open(f).resize((360, 640)); dr = ImageDraw.Draw(im); dr.rectangle([0, 0, 150, 40], fill="white"); dr.text((6, 4), "%s %.1fs" % (s["id"], t), fill="black", font=ft); ims.append(im)
cols = 4; rows = (len(ims) + cols - 1) // cols; W = Image.new("RGB", (360 * cols, 640 * rows), "white")
for i, im in enumerate(ims): W.paste(im, (360 * (i % cols), 640 * (i // cols)))
W.save(out); print(out, W.size)
