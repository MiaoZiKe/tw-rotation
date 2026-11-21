"""動畫設計單位：把 Andy 10-11 給的比比官方部件總表切成一件一件的透明 PNG。

為什麼有這支
------------
Andy 2026-10-11：「打招呼的手不會長這樣，四肢都是短短的，圖二給你放入素材庫，記得按照上面細節去繪製」。
總表原圖 `site/brand/src/bibi_parts_sheet_1011.webp`（1254×1254 白底）＝以後所有比比繪製的唯一依據。
這支把它切成 `docs/anim/bibi_library/parts/<id>.png`，並寫 `parts/index.md`（中文名＋預覽）。

去背做法（不整片吃白：本體是奶油白）
------------------------------------
1. 背景候選＝接近純白（最暗通道 > 242、彩度 < 10）或淺灰影子（彩度 < 14、亮度 196～250）。
2. 從圖片四邊灌水（沿用 gif_pipeline._flood），只有「跟外面連通」的白才算背景 → 被描邊圍住的奶油白身體、
   對話泡泡的白底都留著。
3. 前景做 8 連通分塊；每一件用手量的框：分塊有一半以上落在框裡就整塊收進來；
   一大塊橫跨好幾件（例如棉被那三格黏在一起）才退回只取框內那一段。
4. 邊緣 2px 從白底反混色（算出 alpha、還原顏色），深色底上不會有白邊。每件裁到內容框＋8px 透明邊。

用法
----
    python scripts/anim/bibi_parts.py [--src site/brand/src/bibi_parts_sheet_1011.webp] [--out docs/anim/bibi_library/parts]
"""
from __future__ import annotations

import argparse
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from gif_pipeline import _dilate, _flood  # noqa: E402

FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"

# (id, 中文名, 分類, 框 x0,y0,x1,y1)  —— 座標是總表原圖像素
PARTS = [
    # 本體與四肢
    ("body_front", "本體・正面（有五官）", "本體", (14, 35, 332, 296)),
    ("body_blank", "本體・無五官（毛球）", "本體", (344, 45, 550, 238)),
    ("ear_l", "耳朵・左", "本體", (558, 70, 620, 125)),
    ("ear_r", "耳朵・右", "本體", (648, 70, 710, 125)),
    ("hand_l", "手掌・左（往上舉）", "本體", (562, 138, 618, 208)),
    ("hand_r", "手掌・右（往上舉）", "本體", (652, 138, 708, 208)),
    ("hand_side", "手掌・側面（橫放）", "本體", (552, 218, 616, 272)),
    ("hand_pad", "手掌・肉球面", "本體", (652, 218, 714, 275)),
    ("foot_l", "腳・左", "本體", (358, 246, 428, 298)),
    ("foot_r", "腳・右", "本體", (458, 246, 530, 298)),
    # 五官
    ("eyes_dot", "眼睛・圓點（一對）", "五官", (748, 62, 842, 104)),
    ("eye_closed_smile", "眼睛・閉眼笑 ︶", "五官", (852, 64, 916, 98)),
    ("eye_closed_l", "眼睛・閉眼 ︵（左）", "五官", (924, 64, 976, 96)),
    ("eye_closed_r", "眼睛・閉眼 ︵（右）", "五官", (982, 64, 1034, 96)),
    ("eyes_angry", "眼睛・生氣（含眉）", "五官", (1050, 56, 1140, 104)),
    ("face_sparkle", "臉旁閃光", "五官", (1148, 52, 1236, 112)),
    ("face_cat_small", "小臉・·ω·", "五官", (748, 108, 816, 164)),
    ("mouth_open", "嘴・張開吐舌", "五官", (826, 116, 884, 166)),
    ("mouth_wide", "嘴・大張（ω＋舌）", "五官", (892, 112, 968, 170)),
    ("mouth_o", "嘴・圓 o", "五官", (986, 112, 1034, 168)),
    ("mouth_wavy", "嘴・波浪（尷尬）", "五官", (1056, 126, 1134, 162)),
    ("mouth_small", "嘴・小開口", "五官", (1166, 122, 1218, 168)),
    ("eyes_serious", "眼睛・認真（含眉）", "五官", (746, 182, 834, 236)),
    ("face_sad", "小臉・難過", "五官", (846, 184, 918, 238)),
    ("face_angry", "小臉・生氣", "五官", (942, 184, 1026, 240)),
    ("blush", "腮紅（一對，含斜線）", "五官", (1062, 186, 1176, 242)),
    ("nose", "鼻子", "五官", (1196, 192, 1240, 232)),
    # 效果符號
    ("fx_anger", "怒（青筋）", "效果", (12, 326, 88, 400)),
    ("fx_sweat", "汗滴（兩滴）", "效果", (92, 326, 156, 400)),
    ("fx_drop", "淚滴／水滴", "效果", (162, 326, 216, 400)),
    ("fx_tears", "淚流", "效果", (222, 334, 292, 400)),
    ("fx_exclaim", "！！", "效果", (294, 326, 364, 400)),
    ("fx_question", "？", "效果", (366, 326, 420, 400)),
    ("fx_heart", "愛心", "效果", (420, 330, 490, 400)),
    ("fx_hearts_small", "小愛心群", "效果", (488, 324, 552, 404)),
    ("fx_sparkle", "閃光", "效果", (552, 324, 620, 404)),
    ("fx_music", "音符", "效果", (622, 326, 708, 404)),
    ("fx_zzz", "Zzz", "效果", (708, 326, 764, 386)),
    ("fx_bubble", "對話泡泡", "效果", (766, 320, 864, 406)),
    ("fx_slash", "斜線（害羞）", "效果", (870, 340, 942, 390)),
    ("fx_speed", "速度線", "效果", (956, 328, 1074, 400)),
    ("fx_swirl", "漩渦（暈）", "效果", (1078, 318, 1164, 404)),
    ("fx_smoke", "煙／哈氣雲", "效果", (1164, 326, 1244, 404)),
    # 道具
    ("prop_wizard_hat", "巫師帽", "道具", (12, 412, 118, 514)),
    ("prop_laptop", "筆電", "道具", (118, 426, 222, 508)),
    ("prop_phone", "手機", "道具", (222, 426, 278, 508)),
    ("prop_money_bag", "錢袋", "道具", (278, 418, 358, 512)),
    ("prop_coin", "金幣", "道具", (356, 450, 410, 510)),
    ("prop_coin_stack", "金幣疊", "道具", (410, 434, 488, 510)),
    ("prop_bill", "鈔票", "道具", (488, 446, 562, 508)),
    ("prop_bill_stack", "鈔票疊", "道具", (562, 432, 662, 512)),
    ("prop_kbar", "K 棒", "道具", (662, 436, 730, 508)),
    ("prop_arrow_up", "上漲箭頭", "道具", (730, 432, 804, 510)),
    ("prop_arrow_down", "下跌箭頭", "道具", (808, 432, 876, 504)),
    ("prop_monitor", "看盤螢幕", "道具", (880, 418, 996, 516)),
    ("prop_sign_red", "紅色舉牌", "道具", (998, 422, 1068, 512)),
    ("prop_sign_green", "綠色舉牌", "道具", (1068, 422, 1148, 512)),
    ("prop_sign_green_wide", "綠色寬舉牌", "道具", (1148, 416, 1244, 510)),
    ("prop_shield", "盾牌（$）", "道具", (12, 520, 94, 614)),
    ("prop_diamond", "鑽石", "道具", (94, 530, 168, 606)),
    ("prop_glasses", "眼鏡", "道具", (168, 540, 260, 594)),
    ("prop_newspaper", "報紙", "道具", (256, 530, 340, 612)),
    ("prop_book", "書", "道具", (340, 536, 432, 612)),
    ("prop_coffee", "咖啡", "道具", (432, 520, 496, 608)),
    ("prop_boba", "珍奶", "道具", (496, 520, 558, 612)),
    ("prop_seeds", "瓜子", "道具", (556, 550, 638, 608)),
    ("prop_backpack", "背包", "道具", (638, 524, 710, 612)),
    ("prop_straw_hat", "草帽", "道具", (708, 530, 798, 598)),
    ("prop_suitcase", "行李箱", "道具", (798, 520, 860, 612)),
    ("prop_dumbbell", "啞鈴", "道具", (860, 540, 952, 598)),
    ("prop_towel", "毛巾", "道具", (952, 536, 1052, 608)),
    ("prop_sleeping_bag", "睡袋（比比在裡面）", "道具", (1052, 526, 1150, 604)),
    ("prop_fur_balls", "毛球", "道具", (1150, 530, 1246, 604)),
    # 姿勢
    ("pose_front", "姿勢・正面", "姿勢", (14, 628, 222, 798)),
    ("pose_front_3q", "姿勢・斜前方", "姿勢", (228, 626, 424, 798)),
    ("pose_back", "姿勢・背面（露耳）", "姿勢", (428, 624, 610, 798)),
    ("pose_back_tail", "姿勢・背面（小尾巴）", "姿勢", (622, 626, 824, 798)),
    ("pose_side", "姿勢・側面", "姿勢", (834, 626, 1020, 798)),
    ("pose_front_big", "姿勢・正面（開心）", "姿勢", (1026, 624, 1240, 798)),
]
# 動作參考三排：第一排 12 格、第二排 9 格、第三排 9 格（框只決定歸屬，實際輪廓照分塊）
ACT1 = [(14, 826, 120, 940), (120, 840, 218, 940), (218, 852, 336, 940), (338, 830, 438, 940), (438, 826, 532, 940),
        (532, 824, 630, 940), (630, 836, 724, 942), (724, 832, 816, 942), (816, 840, 908, 942), (910, 840, 992, 940),
        (992, 840, 1114, 940), (1114, 816, 1250, 940)]
ACT2 = [(12, 948, 134, 1082), (134, 958, 250, 1084), (250, 978, 364, 1084), (368, 944, 474, 1084), (474, 944, 578, 1084),
        (578, 944, 690, 1084), (716, 1000, 866, 1092), (858, 936, 1002, 1094), (986, 996, 1120, 1090), (1120, 994, 1236, 1090)]
ACT3 = [(6, 1108, 132, 1226), (134, 1108, 272, 1226), (272, 1108, 406, 1226), (414, 1108, 546, 1226), (546, 1108, 700, 1226),
        (700, 1108, 850, 1226), (854, 1108, 984, 1226), (984, 1108, 1122, 1226), (1122, 1108, 1252, 1226)]
for r, (row, nm) in enumerate(((ACT1, "動作參考第一排"), (ACT2, "動作參考第二排"), (ACT3, "動作參考第三排"))):
    for j, b in enumerate(row):
        PARTS.append((f"act{r+1}_{j+1:02d}", f"{nm}・第 {j+1} 格", "動作參考", b))


def labels(m):
    H, W = m.shape
    lab = np.zeros((H, W), np.int32)
    n = 0
    for y in range(H):
        for x in np.nonzero(m[y] & (lab[y] == 0))[0]:
            if lab[y, x]:
                continue
            n += 1
            q = deque([(y, x)]); lab[y, x] = n
            while q:
                cy, cx = q.popleft()
                for dy in (-1, 0, 1):
                    yy = cy + dy
                    if not 0 <= yy < H:
                        continue
                    for dx in (-1, 0, 1):
                        xx = cx + dx
                        if 0 <= xx < W and m[yy, xx] and not lab[yy, xx]:
                            lab[yy, xx] = n; q.append((yy, xx))
    return lab, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="site/brand/src/bibi_parts_sheet_1011.webp")
    ap.add_argument("--out", default="docs/anim/bibi_library/parts")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rgb = np.asarray(Image.open(a.src).convert("RGB")).astype(np.float32)
    mn, mx = rgb.min(2), rgb.max(2); lum = rgb.mean(2)
    cand = ((mn > 242) & (mx - mn < 10)) | ((mx - mn < 14) & (lum > 196) & (lum <= 250))
    fg = ~_flood(cand)
    lab, n = labels(_dilate(fg, 1))
    lab = np.where(fg, lab, 0)
    cnt = np.bincount(lab.ravel(), minlength=n + 1)
    # 邊緣反混色：靠近背景 2px 的前景像素，alpha 依「離白多遠」估，顏色從白底還原
    ring = fg & _dilate(~fg, 2)
    alpha = np.where(fg, 1.0, 0.0)
    alpha[ring] = np.clip((255 - mn[ring]) / 190.0, 0, 1)
    col = rgb.copy()
    k = np.maximum(alpha, 1e-3)[..., None]
    col = np.where(ring[..., None], np.clip((rgb - 255 * (1 - k)) / k, 0, 255), rgb)
    rows = []
    for pid, name, cat, (x0, y0, x1, y1) in PARTS:
        sub = lab[y0:y1, x0:x1]
        ids, c_in = np.unique(sub[sub > 0], return_counts=True)
        keep = np.zeros_like(fg)
        box_area = (x1 - x0) * (y1 - y0)
        for i, ci in zip(ids, c_in):
            if ci >= 0.5 * cnt[i]:
                keep |= lab == i
            elif ci >= 0.12 * box_area:      # 黏在一起的大塊：只取框內那一段
                m = np.zeros_like(fg); m[y0:y1, x0:x1] = lab[y0:y1, x0:x1] == i
                keep |= m
        ys, xs = np.nonzero(keep)
        if len(ys) == 0:
            print("⚠ 空的", pid); continue
        bx0, by0, bx1, by1 = xs.min() - 8, ys.min() - 8, xs.max() + 9, ys.max() + 9
        bx0, by0 = max(bx0, 0), max(by0, 0)
        A = (alpha * keep * 255).astype(np.uint8)
        if pid == "prop_glasses":   # 鏡片是透明的：被鏡框圍住的白也挖掉
            A = np.where(cand, 0, A).astype(np.uint8)
        im = Image.fromarray(np.dstack([col.astype(np.uint8), A]), "RGBA").crop((bx0, by0, bx1, by1))
        im.save(out / f"{pid}.png", optimize=True)
        rows.append((pid, name, cat, im.size))
    # 預覽總表（三種底）
    cols, cell, labh = 10, 120, 30
    nrow = (len(rows) + cols - 1) // cols
    prev = Image.new("RGB", (cols * cell, nrow * (cell + labh)), (40, 40, 48))
    d = ImageDraw.Draw(prev); ft = ImageFont.truetype(FONT, 12)
    bgs = [(255, 0, 255), (14, 22, 40), (244, 247, 252)]
    for i, (pid, name, cat, sz) in enumerate(rows):
        x, y = (i % cols) * cell, (i // cols) * (cell + labh)
        tile = Image.new("RGBA", (cell - 4, cell - 4), bgs[i % 3] + (255,))
        p = Image.open(out / f"{pid}.png"); p.thumbnail((cell - 12, cell - 12), Image.LANCZOS)
        tile.alpha_composite(p, ((tile.width - p.width) // 2, (tile.height - p.height) // 2))
        prev.paste(tile.convert("RGB"), (x + 2, y + 2))
        d.text((x + 4, y + cell + 2), pid[:18], fill=(235, 235, 235), font=ft)
    prev.save(out / "_preview.png", optimize=True)
    L = ["# 比比部件（從官方部件總表切出）", "",
         "來源：`../reference/parts_sheet_1011.webp`（Andy 2026-10-11）。每件透明 PNG、裁到內容框＋8px 透明邊、原圖像素（未縮放）。",
         "重切：`python scripts/anim/bibi_parts.py`。總覽：`_preview.png`（洋紅／深／淺底輪流，檢查白邊）。", "",
         "| 預覽 | id | 中文名 | 類別 | 尺寸 |", "|---|---|---|---|---|"]
    for pid, name, cat, sz in rows:
        L.append(f"| <img src=\"{pid}.png\" height=\"48\"> | `{pid}` | {name} | {cat} | {sz[0]}×{sz[1]} |")
    (out / "index.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(len(rows), "件 →", out)


if __name__ == "__main__":
    main()
