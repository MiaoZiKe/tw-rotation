"""功能介紹影片 06／07 共用封面（16:9 1920×1080、9:16 1080×1920）。
視覺照 docs/social_handoff/style/LIGULIGU_IG_Threads_Style_Guide.md：奶油紙底、深咖啡字、珊瑚／淡黃強調；網站畫面用錄影當下的實際畫面（取自一鏡到底原片的一格）。
元素外框兩兩比對（外擴 6px），有重疊就印出來。cfg：pill、words（兩個詞）、sub、raw（錄影資料夾）、t（原片秒）、crop（css 外框）、bibi（動作名）、out（資料夾）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import renderlib_v3 as R  # noqa: E402

PAPER = (255, 249, 239)
INK = (50, 26, 20)
SUB = (121, 91, 73)
CORAL = (245, 140, 131)
YEL = (255, 229, 165)


def shot_crop(cfg):
    raw = Path(cfg["raw"])
    js = json.loads((raw / "d_main.json").read_text(encoding="utf-8"))
    cap = cv2.VideoCapture(str(raw / "d_main.mp4"))
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(cfg["t"] * 30))
    ok, fr = cap.read()
    im = Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
    d = js["dsf"]
    x, y, w, h = cfg["crop"]
    return im.crop((int(x * d), int(y * d), int((x + w) * d), int((y + h) * d)))


def sticker(im, w, radius=34, border=14):
    h = int(im.height * w / im.width)
    im = im.resize((w, h), Image.LANCZOS)
    out = Image.new("RGBA", (w + 2 * border, h + 2 * border), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    d.rounded_rectangle([0, 0, out.width - 1, out.height - 1], radius + border, fill=(255, 255, 255, 255), outline=INK + (255,), width=4)
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], radius, fill=255)
    out.paste(im, (border, border), m)
    return out


def paper(W, H):
    rng = np.random.default_rng(7)
    a = np.ones((H, W, 3), np.float32) * np.array(PAPER, np.float32)
    a += rng.normal(0, 2.0, (H, W, 1))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")


def make(kind, cfg):
    W, H = (1920, 1080) if kind == "16x9" else (1080, 1920)
    cv = paper(W, H)
    d = ImageDraw.Draw(cv, "RGBA")
    reg = R.Reg()
    crop = shot_crop(cfg)
    f_pill = R.font(R.F_BOLD, 34 if kind == "16x9" else 40)
    f_big = R.font(R.F_BLACK, 150 if kind == "16x9" else 170)
    f_sub = R.font(R.F_BOLD, 44 if kind == "16x9" else 50)
    s = cfg["pill"]
    tw, th, bb = R.tsize(f_pill, s)
    px, py = (80, 70) if kind == "16x9" else (80, 110)
    d.rounded_rectangle([px, py, px + tw + 56, py + th + 34], (th + 34) // 2, fill=CORAL + (255,), outline=INK + (255,), width=3)
    d.text((px + 28 - bb[0], py + 17 - bb[1]), s, font=f_pill, fill=(255, 255, 255))
    reg.add("膠囊", (px, py, px + tw + 56, py + th + 34))
    y = py + th + 34 + (40 if kind == "16x9" else 70)
    x = px
    for i, word in enumerate(cfg["words"]):
        col, brush = (CORAL, False) if i == 0 else (INK, True)
        w_, h_, b_ = R.tsize(f_big, word)
        if brush:
            d.rounded_rectangle([x - 6, y + h_ * 0.52, x + w_ + 10, y + h_ + 14], 18, fill=YEL + (255,))
        d.text((x - b_[0], y - b_[1]), word, font=f_big, fill=col)
        reg.add("大標" + word, (x - 6, y, x + w_ + 10, y + h_ + 14), "大標")
        if kind == "16x9":
            x += w_ + 36
        elif i == 0:
            y += h_ + 40
    big_bottom = y + R.tsize(f_big, cfg["words"][-1])[1] + 14
    s2 = cfg["sub"]
    w_, h_, b_ = R.tsize(f_sub, s2)
    ys = big_bottom + (34 if kind == "16x9" else 44)
    d.text((px - b_[0], ys - b_[1]), s2, font=f_sub, fill=SUB)
    reg.add("副標", (px, ys, px + w_, ys + h_))
    if kind == "16x9":
        st = sticker(crop, 900)
        sx, sy = W - st.width - 70, H - st.height - 130
    else:
        st = sticker(crop, 940)
        sx, sy = (W - st.width) // 2, ys + h_ + 80
    sh = Image.new("RGBA", st.size, (0, 0, 0, 0))
    sh.paste((50, 26, 20, 60), (0, 0, st.width, st.height), st.split()[3])
    cv.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)), (sx + 10, sy + 14))
    cv.alpha_composite(st, (sx, sy))
    reg.add("網站畫面", (sx, sy, sx + st.width, sy + st.height))
    bimg = Image.open(R.LIB / cfg["bibi"] / "key.png").convert("RGBA")
    bs = 430 if kind == "16x9" else 470
    bimg = bimg.resize((bs, bs), Image.LANCZOS)
    a = np.array(bimg)[..., 3]
    ys_, xs_ = np.nonzero(a > 24)
    if kind == "16x9":
        bx, by = 40, H - bs - 40
    else:
        bx, by = (W - bs) // 2, min(sy + st.height + 8, H - bs - 20)
    cv.alpha_composite(bimg, (bx, by))
    reg.add("比比", (bx + xs_.min(), by + ys_.min(), bx + xs_.max(), by + ys_.max()))
    for name, box in [(n, b) for (n, _g, b) in reg.items]:
        reg.text_in(name, box, (0, 0, W, H), 30)
    out = Path(cfg["out"]) / f"cover_{kind}.png"
    cv.convert("RGB").save(out, optimize=True)
    print(out, "重疊", reg.overlaps(), "出框", reg.issues)
