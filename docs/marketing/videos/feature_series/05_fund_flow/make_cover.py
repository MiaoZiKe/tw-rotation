"""功能介紹影片 05 資金流向：封面兩張（16:9 1920×1080、9:16 1080×1920）。

視覺照 docs/social_handoff/style/LIGULIGU_IG_Threads_Style_Guide.md：奶油紙底 #FFF9EF、深咖啡字 #321A14、
珊瑚 #F58C83／蜜桃 #FFD4BA／淡黃 #FFE5A5 強調；標題 ≤ 14 字；網站畫面用錄影當下的實際畫面（資金分流樹全圖：台股成交值 → 產業鏈 → 族群，只有族群層級，沒有個股）。
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
import render_flow as R  # noqa: E402

PAPER = (255, 249, 239)
INK = (50, 26, 20)
SUB = (121, 91, 73)
CORAL = (245, 140, 131)
PEACH = (255, 212, 186)
YEL = (255, 229, 165)


def shot_crop():
    """d_tree：資金分流樹整張卡（族群層級，沒有個股）。取第一次點「看哪一天」拉桿之後 0.6 秒那一格（游標停在右上角拉桿上、不壓到樹），
    裁切範圍＝全圖定位那一拍量到的卡片外框。"""
    js = json.loads((R.RAW / "d_tree.json").read_text(encoding="utf-8"))
    card = js["cams"][int((js["says"][0]["t"] + 0.5) * 30)][6]
    t = [c for c in js["clicks"] if "看哪一天" in (c.get("label") or "")][0]["t"] + 0.6
    k = int(t * 30)
    cap = cv2.VideoCapture(str(R.RAW / "d_tree.mp4"))
    cap.set(cv2.CAP_PROP_POS_FRAMES, k)
    ok, fr = cap.read()
    im = Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
    x, y, w, h = card
    return im.crop((int(x), int(y), int(x + w), int(y + h))), None


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
    crop, _ = shot_crop()
    f_pill = R.font(R.F_BOLD, 34 if kind == "16x9" else 40)
    f_big = R.font(R.F_BLACK, 150 if kind == "16x9" else 170)
    f_sub = R.font(R.F_BOLD, 44 if kind == "16x9" else 50)
    f_note = R.font(R.F_MED, 26 if kind == "16x9" else 30)
    # 膠囊
    s = "哩股哩股・功能介紹 05"
    tw, th, bb = R.tsize(f_pill, s)
    px, py = (80, 70) if kind == "16x9" else (80, 110)
    d.rounded_rectangle([px, py, px + tw + 56, py + th + 34], (th + 34) // 2, fill=CORAL + (255,), outline=INK + (255,), width=3)
    d.text((px + 28 - bb[0], py + 17 - bb[1]), s, font=f_pill, fill=(255, 255, 255))
    reg.add("膠囊", (px, py, px + tw + 56, py + th + 34))
    # 大標：資金（珊瑚）＋流向（淡黃刷底）
    y = py + th + 34 + (40 if kind == "16x9" else 70)
    x = px
    for word, col, brush in (("資金", CORAL, False), ("流向", INK, True)):
        w_, h_, b_ = R.tsize(f_big, word)
        if brush:
            d.rounded_rectangle([x - 6, y + h_ * 0.52, x + w_ + 10, y + h_ + 14], 18, fill=YEL + (255,))
        d.text((x - b_[0], y - b_[1]), word, font=f_big, fill=col)
        reg.add("大標" + word, (x - 6, y, x + w_ + 10, y + h_ + 14), "大標")
        if kind == "16x9":
            x += w_ + 36
        else:
            if word == "資金":
                y += h_ + 40
    big_bottom = y + R.tsize(f_big, "流向")[1] + 14
    s2 = "錢往哪個族群跑？一頁看懂"
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
        sx, sy = (W - st.width) // 2, ys + h_ + 80
    sh = Image.new("RGBA", st.size, (0, 0, 0, 0))
    sh.paste((50, 26, 20, 60), (0, 0, st.width, st.height), st.split()[3])
    cv.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)), (sx + 10, sy + 14))
    cv.alpha_composite(st, (sx, sy))
    reg.add("網站畫面", (sx, sy, sx + st.width, sy + st.height))
    # 比比（拿放大鏡）
    bimg = Image.open(R.LIB / "magnifier" / "key.png").convert("RGBA")
    bs = 430 if kind == "16x9" else 470
    bimg = bimg.resize((bs, bs), Image.LANCZOS)
    a = np.array(bimg)[..., 3]
    ys_, xs_ = np.nonzero(a > 24)
    if kind == "16x9":
        bx, by = 40, H - bs - 40
    else:
        bx, by = (W - bs) // 2, sy + st.height - 40   # 9:16：比比放在網站畫面正下方（不留大片空白）
    cv.alpha_composite(bimg, (bx, by))
    reg.add("比比", (bx + xs_.min(), by + ys_.min(), bx + xs_.max(), by + ys_.max()))
    # 註記
    # Andy 10-19：不放資料日／歷史資料角標
    for name, box in [(n, b) for (n, _g, b) in reg.items]:
        reg.text_in(name, box, (0, 0, W, H), 30)
    out = HERE / f"cover_{kind}.png"
    cv.convert("RGB").save(out, optimize=True)
    print(out, "重疊", reg.overlaps(), "出框", reg.issues)


if __name__ == "__main__":
    make("16x9")
    make("9x16")
