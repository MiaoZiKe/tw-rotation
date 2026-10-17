"""動畫師：第 6 版主持表情的交件圖與素材庫索引。

在 `bibi_host_v6.py` 跑完之後執行：
    python scripts/anim/bibi_host_v6_sheets.py --v6 <scratchpad>/bibi_v6
做四件事：
1. <v6>/before_after.png：改版前（舊 sheet 12 格）與改版後（v2 逐格）上下並排，棋盤格底。
2. <v6>/new_sets.png：新增 6 組逐格總覽（白／黑／棋盤格三種底輪流）。
3. docs/anim/bibi_library/index.md：表格補上（或更新）v6 各組的列；舊列一個字不動。
4. docs/anim/bibi_library/catalog.png：依 index.md 全部列重畫總目錄；docs/anim/bibi_library/host_v6_timing.md：時間表＋接觸表。
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[2]
LIB = REPO / "docs/anim/bibi_library"
FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
PAIRS = [("talk_happy", "talk_happy_v2"), ("talk_explain", "talk_explain_v2"), ("talk_excited", "talk_excited_v2"),
         ("face_nod", "face_nod_v2"), ("face_think", "face_think_v2"), ("point_r", "point_r_v2"),
         ("point_ur", "point_ur_v2"), ("point_dr", "point_dr_v2")]
NEW = ["happy_spin", "shy_rub", "surprise_jump", "proud_shine", "sulk_curl", "invite_nod"]


def checker(w, h, s=10):
    yy, xx = np.indices((h, w))
    v = np.where(((yy // s) + (xx // s)) % 2, 205, 245).astype(np.uint8)
    return Image.fromarray(np.dstack([v, v, v, np.full_like(v, 255)]), "RGBA")


def cells(sheet_path):
    sh = Image.open(sheet_path).convert("RGBA")
    n = sh.width // 256
    return [sh.crop((256 * j, 0, 256 * j + 256, 256)) for j in range(n)]


def row(imgs, cell, bg):
    out = Image.new("RGBA", (cell * len(imgs), cell))
    for j, im in enumerate(imgs):
        t = bg(j).copy()
        t.alpha_composite(im.resize((cell, cell), Image.LANCZOS))
        out.paste(t, (cell * j, 0))
    return out


def before_after(path, timing):
    cell, lab = 120, 26
    maxn = max(len(cells(LIB / b / "sheet.png")) for _, b in PAIRS)
    W = 170 + cell * maxn
    H = 50 + len(PAIRS) * (2 * cell + lab + 18)
    out = Image.new("RGB", (W, H), (52, 52, 60))
    d = ImageDraw.Draw(out)
    fh, ft = ImageFont.truetype(FONT, 22), ImageFont.truetype(FONT, 14)
    d.text((10, 12), "比比主持表情 改版前（上，舊 12 格）／改版後 v2（下）　棋盤格底", fill=(255, 220, 120), font=fh)
    chk = checker(cell, cell)
    y = 50
    for old, new in PAIRS:
        a, b = cells(LIB / old / "sheet.png"), cells(LIB / new / "sheet.png")
        t = timing.get(new, {})
        d.text((8, y), f"{old} → {new}　舊 {len(a)} 格／新 {len(b)} 格 {t.get('ms', 0)/1000:.2f} 秒", fill=(240, 240, 240), font=ft)
        y += lab
        d.text((8, y + cell // 2 - 8), "改版前", fill=(200, 200, 200), font=ft)
        out.paste(row(a, cell, lambda j: chk).convert("RGB"), (170, y))
        d.text((8, y + cell + cell // 2 - 8), "改版後 v2", fill=(140, 230, 160), font=ft)
        out.paste(row(b, cell, lambda j: chk).convert("RGB"), (170, y + cell))
        y += 2 * cell + 18
    out.save(path)


def new_sets(path, timing):
    cell, lab = 120, 26
    maxn = max(len(cells(LIB / k / "sheet.png")) for k in NEW)
    W = cell * maxn
    H = 50 + len(NEW) * (cell + lab + 12)
    out = Image.new("RGB", (W, H), (52, 52, 60))
    d = ImageDraw.Draw(out)
    fh, ft = ImageFont.truetype(FONT, 22), ImageFont.truetype(FONT, 14)
    d.text((10, 12), "比比主持表情 新增 6 組（逐格；白／黑／棋盤格底輪流）", fill=(255, 220, 120), font=fh)
    bgs = [Image.new("RGBA", (cell, cell), (255, 255, 255, 255)), Image.new("RGBA", (cell, cell), (0, 0, 0, 255)), checker(cell, cell)]
    y = 50
    for k in NEW:
        t = timing.get(k, {})
        im = cells(LIB / k / "sheet.png")
        d.text((8, y + 4), f"{k}　{t.get('name', '')}　{len(im)} 格 {t.get('ms', 0)/1000:.2f} 秒", fill=(240, 240, 240), font=ft)
        out.paste(row(im, cell, lambda j: bgs[j % 3]).convert("RGB"), (0, y + lab))
        y += cell + lab + 12
    out.save(path)


def update_index(timing):
    p = LIB / "index.md"
    lines = p.read_text(encoding="utf-8").splitlines()
    keys = [b for _, b in PAIRS] + NEW
    lines = [ln for ln in lines if not any(ln.startswith(f"| `{k}` |") for k in keys)]
    # v6 說明段（只加一次）
    note = ("**2026-10-17 第 6 版主持表情**（Andy：「在對表情動作上需要在多點優化」）：`*_v2` 是 talk_*／face_nod／face_think／point_* 的改版"
            "（加眨眼、三段嘴型、耳朵次要動作、預備→主動作→回穩；舊組保留，舊影片可重建），類別「主持」是新增 6 組。"
            "產生：`python scripts/anim/bibi_host_v6.py --out <scratchpad>/bibi_v6`；時間表＋接觸表：[host_v6_timing.md](host_v6_timing.md)。")
    if not any(ln.startswith("**2026-10-17 第 6 版主持表情**") for ln in lines):
        i = next(j for j, ln in enumerate(lines) if ln.startswith("總目錄："))
        lines[i:i] = [note, ""]
    rows = []
    for k in keys:
        t = timing[k]
        rows.append(f"| `{k}` | {t['name']} | {t['cat']} | {t['use']} | {t['frames']} | {t['ms']/1000:.2f} 秒 | "
                    f"[代表格]({k}/key.png)・[sprite]({k}/sheet.png)・[動畫]({k}/anim.webp) |")
    last = max(j for j, ln in enumerate(lines) if ln.startswith("| `"))
    lines[last + 1:last + 1] = rows
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")


def catalog():
    rows = []
    for ln in (LIB / "index.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\| `([^`]+)` \| (.+?) \| (.+?) \|", ln)
        if m:
            rows.append((m.group(1), m.group(2), m.group(3)))
    cols, cell, lab, head = 8, 200, 34, 56
    nrow = math.ceil(len(rows) / cols)
    cat = Image.new("RGB", (cols * cell, head + nrow * (cell + lab)), (250, 246, 240))
    dr = ImageDraw.Draw(cat)
    ft, fh, fs = ImageFont.truetype(FONT, 17), ImageFont.truetype(FONT, 26), ImageFont.truetype(FONT, 13)
    kinds = "／".join(dict.fromkeys(r[2] for r in rows))
    dr.text((16, 14), f"比比素材庫　共 {len(rows)} 組（{kinds}）", fill=(42, 22, 16), font=fh)
    tint = {"動作": (232, 240, 252), "表情": (252, 236, 240), "情境道具": (252, 246, 228), "互動": (232, 246, 236),
            "主持": (240, 232, 252)}
    for i, (k, name, c) in enumerate(rows):
        x, y = (i % cols) * cell, head + (i // cols) * (cell + lab)
        dr.rectangle((x + 3, y + 3, x + cell - 3, y + cell + lab - 3), fill=tint.get(c, (240, 240, 240)))
        im = Image.open(LIB / k / "key.png").convert("RGBA").resize((cell - 16, cell - 16), Image.LANCZOS)
        cat.paste(im, (x + 8, y + 8), im)
        dr.text((x + 8, y + 8), c + ("・v2" if k.endswith("_v2") else ""), fill=(120, 90, 80), font=fs)
        nm = name.split("（")[0].replace("表情・", "").replace("說話・", "")
        dr.text((x + cell / 2, y + cell + lab / 2 - 4), nm[:12], fill=(42, 22, 16), font=ft, anchor="mm")
    cat.convert("RGBA").quantize(colors=256, method=Image.FASTOCTREE, dither=Image.NONE).save(LIB / "catalog.png", optimize=True)
    return len(rows)


def timing_md(timing):
    keys = [b for _, b in PAIRS] + NEW
    L = ["# 比比主持表情第 6 版：時間表＋接觸表", "",
         "Andy 2026-10-17：「在對表情動作上需要在多點優化」。產生腳本 `scripts/anim/bibi_host_v6.py`。",
         "座標同素材庫（512×512、身體縮 0.75、中心 x=248、腳底 y=482）。",
         "「接觸」＝四腳著地格（腳底 y 應 ≥ 478）；「離地」＝跳躍／空中格。耳朵角度：正＝往外甩、負＝往上豎（彈簧模擬＋指定偏移）。",
         "每組第 1 格＝待機，最後一格回到待機，可無縫循環。", ""]
    for k in keys:
        t = timing[k]
        L += [f"## `{k}`　{t['name']}", "", f"{t['frames']} 格、{t['ms']/1000:.2f} 秒、代表格第 {t['key_frame']} 格。", "",
              "| 格 | 動作 | ms | 接觸 | 腳底 y | 耳（左, 右）° |", "|---|---|---|---|---|---|"]
        for j, (lab, ms, ck, ear) in enumerate(zip(t["labels"], t["durations_ms"], t["check"], t["ears_deg"])):
            L.append(f"| {j+1:02d} | {lab} | {ms} | {'接觸' if ck['contact'] else '離地'} | {ck['foot_y']} | {ear[0]:+.0f}, {ear[1]:+.0f} |")
        L.append("")
    (LIB / "host_v6_timing.md").write_text("\n".join(L), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v6", required=True)
    a = ap.parse_args()
    v6 = Path(a.v6)
    timing = json.loads((v6 / "timing.json").read_text(encoding="utf-8"))
    before_after(v6 / "before_after.png", timing)
    new_sets(v6 / "new_sets.png", timing)
    update_index(timing)
    n = catalog()
    timing_md(timing)
    print("完成：總目錄", n, "組")


if __name__ == "__main__":
    main()
