#!/usr/bin/env python3
"""總覽圖：首篇_3張_總覽、首篇_5張_總覽（各色調一列）、模板_總覽（7 種×奶油晨光）、Threads 四色、對照_單薄版_vs_素材版。"""
import os
from PIL import Image, ImageDraw, ImageFont
B = os.path.dirname(os.path.abspath(__file__)); O = os.path.join(B, ".."); OLD = os.path.join(O, "..", "templates_tqsa", "out")
F = ImageFont.truetype("/root/.fonts/NotoSansCJKtc-Bold.otf", 34); Fs = ImageFont.truetype("/root/.fonts/NotoSansCJKtc-Regular.otf", 26)
TONE = [("cream", "奶油晨光"), ("sky", "晴空淡藍"), ("matcha", "抹茶午後"), ("peach", "蜜桃傍晚")]
def sheet(rows, th, out, title, pad=36, lab=46):
    """rows: [(列標題, [(圖路徑, 小標), ...]), ...]"""
    ims = [[(Image.open(p).convert("RGB"), t) for p, t in r] for _, r in rows]
    ims = [[(im.resize((int(im.width * th / im.height), th), Image.LANCZOS), t) for im, t in r] for r in ims]
    W = max(sum(im.width for im, _ in r) + pad * (len(r) + 1) for r in ims)
    H = 96 + sum(th + lab + 40 + pad for _ in ims) + pad
    S = Image.new("RGB", (W, H), "#FAF7F2"); d = ImageDraw.Draw(S); d.text((pad, 28), title, font=F, fill="#3A3A3A"); y = 96
    for (rt, _), r in zip(rows, ims):
        if rt: d.text((pad, y), rt, font=F, fill="#3A3A3A")
        y += 44 if rt else 0; x = pad
        for im, t in r:
            S.paste(im, (x, y)); d.rectangle([x - 1, y - 1, x + im.width, y + im.height], outline="#CFC8BC", width=2); d.text((x, y + th + 8), t, font=Fs, fill="#3A3A3A"); x += im.width + pad
        y += th + lab + pad
    S = S.crop((0, 0, W, y)); S.save(f"{O}/{out}"); print(out, S.size)
sheet([(n, [(f"{O}/首篇_3張/{k}_{i}.png", f"第 {i} 張") for i in (1, 2, 3)]) for k, n in TONE], 600, "首篇_3張_總覽.png", "談晴說礙 首篇 3 張版（主推）× 4 色調")
sheet([(n, [(f"{O}/首篇_5張/{k}_{i}.png", f"第 {i} 張") for i in (1, 2, 3, 4, 5)]) for k, n in TONE], 460, "首篇_5張_總覽.png", "談晴說礙 首篇 5 張版 × 4 色調")
names = [("1_cover", "①封面"), ("2_data", "②數據頁"), ("3_line", "③一句話"), ("4_daily", "④今日的晴"), ("5_sources", "⑤出處與求助"), ("6_threads", "⑥Threads"), ("7_reels", "⑦Reels")]
sheet([("奶油晨光", [(f"{O}/模板/{t}/{t}_cream.png", n) for t, n in names[:4]]), ("", [(f"{O}/模板/{t}/{t}_cream.png", n) for t, n in names[4:]])], 560, "模板_總覽.png", "談晴說礙 模板總覽（7 種，奶油晨光）")
sheet([("Threads 單張版", [(f"{O}/首篇_threads/{k}.png", n) for k, n in TONE])], 560, "首篇_threads_總覽.png", "談晴說礙 首篇 Threads 單張版 × 4 色調")
sheet([("上一版（單薄：只有幾朵雲和太陽）", [(f"{OLD}/01_奶油晨光.png", "封面"), (f"{OLD}/02_奶油晨光.png", "第 2 張")]),
       ("這一版（沿用日日小晴素材：場景、層次、描線）", [(f"{O}/首篇_3張/cream_1.png", "封面"), (f"{O}/首篇_3張/cream_2.png", "第 2 張")])], 620, "對照_單薄版_vs_素材版.png", "上一版 vs 這一版（奶油晨光）")
