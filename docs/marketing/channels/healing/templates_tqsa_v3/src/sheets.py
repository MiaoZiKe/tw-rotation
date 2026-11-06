#!/usr/bin/env python3
"""總覽圖與「參考圖 vs 新版」對照圖。"""
import json, os
from PIL import Image, ImageDraw, ImageFont
B = os.path.dirname(os.path.abspath(__file__)); O = os.path.join(B, "..")
REF = os.path.join(O, "..", "samples", "20261104_gen2000_v5", "post2")
FONT = ImageFont.truetype("/root/.fonts/NotoSansCJKtc-Regular.otf", 26)
BG = (70, 70, 70)
def sheet(rows, out, th=520, labels=None):
    """rows：每列是檔案清單（可混 1080×1350 與 1080×1920，統一縮到同高 th）。labels：每列左上標籤。"""
    gap = 14; lab_h = 40 if labels else 0
    ims = [[Image.open(f).convert("RGB") for f in r] for r in rows]
    ims = [[im.resize((round(im.width * th / im.height), th), Image.LANCZOS) for im in r] for r in ims]
    W = max(sum(im.width for im in r) + gap * (len(r) + 1) for r in ims); H = len(ims) * (th + gap + lab_h) + gap
    img = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(img)
    for ri, r in enumerate(ims):
        y = gap + ri * (th + gap + lab_h)
        if labels: d.text((gap, y + 4), labels[ri], font=FONT, fill=(235, 235, 235))
        x = gap
        for im in r: img.paste(im, (x, y + lab_h)); x += im.width + gap
    img.save(out)
P = lambda folder, theme, n: f"{O}/{folder}/{theme}/{n}.png"
sheet([[P("首篇_3張", t, i) for i in "123"] for t in ("夜版", "晝版")], O + "/首篇_3張_總覽.png", 700, ["夜版（主）", "晝版（輔）"])
sheet([[P("長輩的期待", t, i) for i in "12345"] for t in ("夜版", "晝版")], O + "/長輩的期待_總覽.png", 520, ["夜版（主）", "晝版（輔）"])
T = ["1_封面", "2_內頁一句話", "3_數據頁", "4_出處與求助", "5_Threads單張", "6_Reels封面"]
sheet([[P("模板", t, n) for n in T] for t in ("夜版", "晝版")], O + "/模板_總覽.png", 600, ["夜版（主）：封面／內頁一句話／數據頁／出處與求助／Threads 單張／Reels 封面", "晝版（輔）"])
sheet([[f"{REF}/01_cover.png", f"{REF}/02_inner.png"], [P("長輩的期待", "夜版", "1"), P("長輩的期待", "夜版", "2")], [P("長輩的期待", "晝版", "1"), P("長輩的期待", "晝版", "2")]],
      O + "/對照_參考圖_vs_新版.png", 760, ["參考圖（長輩的期待 v5：霧紫灰、粗線）", "新版夜版（雲灰＋晴光橘、細線＋細節）", "新版晝版"])
print("sheets ok")
