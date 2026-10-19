"""功能介紹影片 01 ETF：封面兩張（16:9 1920×1080、9:16 1080×1920）。

視覺照 docs/social_handoff/style/LIGULIGU_IG_Threads_Style_Guide.md：奶油紙底 #FFF9EF、深咖啡字 #321A14、
珊瑚 #F58C83／蜜桃 #FFD4BA／淡黃 #FFE5A5 強調；標題 ≤ 14 字；網站畫面用錄影當下的實際畫面（配息行事曆）。
元素外框兩兩比對（外擴 6px），有重疊就印出來。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render_etf as R  # noqa: E402

PAPER = (255, 249, 239)
INK = (50, 26, 20)
SUB = (121, 91, 73)
CORAL = (245, 140, 131)
PEACH = (255, 212, 186)
YEL = (255, 229, 165)


def shot_crop():
    f = R.RAW / "d_cal.json"
    meta = json.loads(f.read_text(encoding="utf-8")) if f.exists() else json.loads((R.RAW / "d_meta.json").read_text(encoding="utf-8"))["cal"]
    # 點了日期之後、清單出現的那一刻（第 4 句泡泡出現後 1.5 秒）
    t = (meta["says"][2]["t"] + 1.0) if R.FAST else (meta["says"][4]["t"] + 1.5)
    cap = cv2.VideoCapture(str(R.RAW / "d_cal.mp4"))
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * 30))
    ok, fr = cap.read()
    im = Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
    cx = meta.get("content_x") or [0, im.width]
    # 配息行事曆卡片：左右用內容區、上下取卡片範圍（約 css 64～872）
    asof = json.loads((R.REPO / "site" / "data" / "etf.json").read_text(encoding="utf-8")).get("asof")
    return im.crop((cx[0] + 10, 2 * 64, cx[1] - 10, 2 * 836)), asof or meta.get("data_date")


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


def make(kind):
    W, H = (1920, 1080) if kind == "16x9" else (1080, 1920)
    cv = paper(W, H)
    d = ImageDraw.Draw(cv, "RGBA")
    reg = R.Reg()
    crop, data_date = shot_crop()
    f_pill = R.font(R.F_BOLD, 34 if kind == "16x9" else 40)
    f_big = R.font(R.F_BLACK, 150 if kind == "16x9" else 170)
    f_sub = R.font(R.F_BOLD, 44 if kind == "16x9" else 50)
    f_note = R.font(R.F_MED, 26 if kind == "16x9" else 30)
    # 膠囊
    s = "哩股哩股・功能介紹 01"
    tw, th, bb = R.tsize(f_pill, s)
    px, py = (80, 70) if kind == "16x9" else (80, 110)
    d.rounded_rectangle([px, py, px + tw + 56, py + th + 34], (th + 34) // 2, fill=CORAL + (255,), outline=INK + (255,), width=3)
    d.text((px + 28 - bb[0], py + 17 - bb[1]), s, font=f_pill, fill=(255, 255, 255))
    reg.add("膠囊", (px, py, px + tw + 56, py + th + 34))
    # 大標：ETF（珊瑚）＋一頁看懂（淡黃刷底）
    y = py + th + 34 + (40 if kind == "16x9" else 70)
    x = px
    for word, col, brush in (("ETF", CORAL, False), ("一頁看懂", INK, True)):
        w_, h_, b_ = R.tsize(f_big, word)
        if brush:
            d.rounded_rectangle([x - 6, y + h_ * 0.52, x + w_ + 10, y + h_ + 14], 18, fill=YEL + (255,))
        d.text((x - b_[0], y - b_[1]), word, font=f_big, fill=col)
        reg.add("大標" + word, (x - 6, y, x + w_ + 10, y + h_ + 14), "大標")
        if kind == "16x9":
            x += w_ + 36
        else:
            if word == "ETF":
                y += h_ + 40
    big_bottom = y + R.tsize(f_big, "一頁看懂")[1] + 14
    s2 = "配息行事曆・類型總覽・報酬比較"
    w_, h_, b_ = R.tsize(f_sub, s2)
    ys = big_bottom + (34 if kind == "16x9" else 44)
    d.text((px - b_[0], ys - b_[1]), s2, font=f_sub, fill=SUB)
    reg.add("副標", (px, ys, px + w_, ys + h_))
    # 網站畫面貼紙
    if kind == "16x9":
        st = sticker(crop, 900)
        sx, sy = W - st.width - 70, H - st.height - 130
    else:
        st = sticker(crop, 940)
        sx, sy = (W - st.width) // 2, ys + h_ + 110
    sh = Image.new("RGBA", st.size, (0, 0, 0, 0))
    sh.paste((50, 26, 20, 60), (0, 0, st.width, st.height), st.split()[3])
    cv.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)), (sx + 10, sy + 14))
    cv.alpha_composite(st, (sx, sy))
    reg.add("網站畫面", (sx, sy, sx + st.width, sy + st.height))
    # 比比（好奇歪頭）
    bimg = Image.open(R.LIB / "face_curious" / "key.png").convert("RGBA")
    bs = 430 if kind == "16x9" else 560
    bimg = bimg.resize((bs, bs), Image.LANCZOS)
    a = np.array(bimg)[..., 3]
    ys_, xs_ = np.nonzero(a > 24)
    if kind == "16x9":
        bx, by = 40, H - bs - 40
    else:
        bx, by = (W - bs) // 2, H - bs - 110
    cv.alpha_composite(bimg, (bx, by))
    reg.add("比比", (bx + xs_.min(), by + ys_.min(), bx + xs_.max(), by + ys_.max()))
    # 註記
    note = f"網站實際畫面・資料日 {data_date}｜歷史資料，不代表未來表現"
    w_, h_, b_ = R.tsize(f_note, note)
    nx = W - 70 - w_ if kind == "16x9" else (W - w_) // 2
    ny = H - 70 if kind == "16x9" else H - 60
    d.text((nx - b_[0], ny - b_[1]), note, font=f_note, fill=SUB)
    reg.add("註記", (nx, ny, nx + w_, ny + h_))
    for name, box in [(n, b) for (n, _g, b) in reg.items]:
        reg.text_in(name, box, (0, 0, W, H), 30)
    out = HERE / f"cover_{kind}.png"
    cv.convert("RGB").save(out, optimize=True)
    print(out, "重疊", reg.overlaps(), "出框", reg.issues)


if __name__ == "__main__":
    make("16x9")
    make("9x16")
