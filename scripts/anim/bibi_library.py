"""動畫設計單位：把所有比比動畫整理成素材庫 `docs/anim/bibi_library/`。

為什麼有這支
------------
Andy 第 3 版（docs/marketing/video_1010/v3_brief.md 第 12 條）：「表情、情境、道具要更豐富，
做出來的表情、情境、道具要存成圖檔以後使用」。這支把 A／B／C／D／E／F 各批的逐格 PNG（scratchpad 的 index*.json）
整理成以後直接拿來用的圖檔：

    docs/anim/bibi_library/<名>/key.png    512 透明代表格（表情最滿的那一格）
    docs/anim/bibi_library/<名>/sheet.png  12 格橫排 sprite（每格 256、透明、調色盤壓縮）
    docs/anim/bibi_library/<名>/anim.webp  動態 WebP（docs/anim 已有就複製，沒有才從逐格重新編）
    docs/anim/bibi_library/index.md        索引表（名稱、中文、類別、適合用途、格數、預覽）
    docs/anim/bibi_library/catalog.png     總目錄（每組代表格＋中文名）

逐格 PNG 只在 scratchpad，素材庫是給「以後要用」的那一份，所以 sheet 一律 256 格＋PNG 調色盤壓縮，整個資料夾目標 ≤ 25MB。

用法
----
    python scripts/anim/bibi_library.py --bibi <scratchpad>/bibi --out docs/anim/bibi_library
（index_e.json 出現後再跑一次就會補進 E 批；已有的組會覆蓋成最新。）
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
BATCHES = [("index.json", "A"), ("index_b.json", "B"), ("index_c.json", "C"), ("index_d.json", "D"),
           ("index_e.json", "E"), ("index_f.json", "F")]

ACTION = {"wave", "point_r", "point_ur", "point_dr", "tilt", "wow", "intro", "intro_blank"}
PROP = {"sign", "sign_text", "news", "coins", "magnifier", "3dglasses", "celebrate",
        "piggy", "calc", "growth", "boba", "calendar"}

USE = {
    "wave": "開場打招呼、片尾說再見", "point_r": "指向畫面右側的重點", "point_ur": "指向右上方的標題／數字",
    "point_dr": "指向右下方的按鈕／表格", "tilt": "提出問題、「這是什麼？」", "wow": "驚人數字出現時",
    "sign": "頭上牌子（留白，影片自己放字）", "sign_text": "許願、許願清單段落", "news": "看財經新聞／日曆",
    "coins": "談收益、配息、錢流進來", "magnifier": "放大看細節、深入分析", "3dglasses": "介紹 3D 剖析圖",
    "celebrate": "達成、上線、好消息", "piggy": "存錢、配息、累積", "calc": "試算、計算報酬",
    "growth": "複利、長期成長", "boba": "輕鬆段落、下班時間", "calendar": "日期、事件日曆、每天更新",
    "talk_happy": "旁白講解（輕鬆）", "talk_explain": "旁白講解（認真說明功能）", "talk_excited": "旁白講解（亮點、新功能）",
    "face_love": "喜歡這個功能", "face_laugh": "輕鬆好笑的段落", "face_proud": "自豪的功能介紹",
    "face_think": "提出疑問、思考", "face_shock": "風險提醒、嚇一跳的數字", "face_sweat": "常見錯誤、尷尬狀況",
    "face_wink": "小撇步、俏皮提醒", "face_star": "超讚、驚豔", "face_sleepy": "「不用熬夜看盤」",
    "face_nod": "同意、肯定", "intro": "影片開場自我介紹", "intro_blank": "開場自我介紹（名牌留白，自己放字）",
    "face_relief": "問題解決、安心了", "face_cool": "很酷的功能、帥氣登場", "face_shy": "被稱讚、不好意思",
    "face_determined": "加油打氣、一起努力", "face_curious": "好奇湊近看新東西", "face_surprise_happy": "驚喜、好消息公布",
    "face_thumbs": "推薦、按讚", "face_clap": "鼓掌、恭喜", "face_bow": "片尾謝謝收看", "face_thinking_bulb": "想通了、恍然大悟",
}


def category(key, batch):
    if batch == "D":
        return "互動"
    if batch in ("C", "F") or key.startswith(("face_", "talk_")):
        return "動作" if key in ACTION else "表情"
    if key in ACTION:
        return "動作"
    if key in PROP or batch == "B":
        return "情境道具"
    return "互動" if batch == "E" else "情境道具"


def find_webp(key, entry, repo):
    w = entry.get("webp")
    if w and Path(w).exists():
        return Path(w)
    d = repo / "docs/anim" / f"bibi_{key}" / "anim.webp"
    if d.exists():
        return d
    if "_" in key:
        base, suf = key.rsplit("_", 1)
        d = repo / "docs/anim" / f"bibi_{base}" / f"anim_{suf}.webp"
        if d.exists():
            return d
    return None


def quant(im):
    """RGBA → 調色盤 PNG（保留透明），檔案約小 3～4 倍。"""
    return im.quantize(colors=256, method=Image.FASTOCTREE, dither=Image.NONE)


def key_index(imgs):
    a = [np.asarray(i.convert("RGBA")).astype(np.int32) for i in imgs]
    d = [int(np.abs(x - a[0]).sum()) for x in a]
    # 表情最滿的那一格：跟第 1 格差最多的；但避開身體不完整的格（不透明像素太少，例如從畫面外彈進來）
    area = [int((x[..., 3] > 128).sum()) for x in a]
    ok = [i for i in range(len(a)) if area[i] > 0.8 * max(area)]
    return max(ok, key=lambda i: d[i])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bibi", required=True)
    ap.add_argument("--out", default="docs/anim/bibi_library")
    ap.add_argument("--repo", default=".")
    a = ap.parse_args()
    bibi, out, repo = Path(a.bibi), Path(a.out), Path(a.repo)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for fn, batch in BATCHES:
        p = bibi / fn
        if not p.exists():
            continue
        for key, e in json.loads(p.read_text(encoding="utf-8")).items():
            frames = [Path(x) for x in e["frames"]]
            if not all(x.exists() for x in frames):
                print("⚠ 逐格不見了，跳過", key)
                continue
            imgs = [Image.open(x).convert("RGBA") for x in frames]
            d = out / key
            d.mkdir(parents=True, exist_ok=True)
            ki = key_index(imgs)
            quant(imgs[ki]).save(d / "key.png", optimize=True)
            n = len(imgs)
            sheet = Image.new("RGBA", (256 * n, 256), (0, 0, 0, 0))
            for j, im in enumerate(imgs):
                sheet.alpha_composite(im.resize((256, 256), Image.LANCZOS), (256 * j, 0))
            quant(sheet).save(d / "sheet.png", optimize=True)
            w = find_webp(key, e, repo)
            if w:
                shutil.copyfile(w, d / "anim.webp")
            else:
                imgs[0].save(d / "anim.webp", save_all=True, append_images=imgs[1:], duration=e["durations_ms"],
                             loop=0, quality=85, method=6)
            rows.append({"key": key, "name": e["name"], "batch": batch, "cat": category(key, batch),
                         "use": USE.get(key, e["name"]), "n": n, "ms": sum(e["durations_ms"]), "key_frame": ki + 1,
                         "webp_src": str(w.relative_to(repo.resolve())) if w and w.is_relative_to(repo.resolve()) else "重新編碼"})
            print(batch, key, n, "代表格", ki + 1, flush=True)
    order = {"動作": 0, "表情": 1, "情境道具": 2, "互動": 3}
    rows.sort(key=lambda r: (order[r["cat"]], r["batch"], r["key"]))

    # ---- 總目錄
    cols, cell, lab = 8, 200, 34
    nrow = math.ceil(len(rows) / cols)
    head = 56
    cat = Image.new("RGB", (cols * cell, head + nrow * (cell + lab)), (250, 246, 240))
    dr = ImageDraw.Draw(cat)
    ft = ImageFont.truetype(FONT, 17); fh = ImageFont.truetype(FONT, 26); fs = ImageFont.truetype(FONT, 13)
    dr.text((16, 14), f"比比素材庫　共 {len(rows)} 組（動作／表情／情境道具／互動）", fill=(42, 22, 16), font=fh)
    tint = {"動作": (232, 240, 252), "表情": (252, 236, 240), "情境道具": (252, 246, 228), "互動": (232, 246, 236)}
    for i, r in enumerate(rows):
        x, y = (i % cols) * cell, head + (i // cols) * (cell + lab)
        dr.rectangle((x + 3, y + 3, x + cell - 3, y + cell + lab - 3), fill=tint[r["cat"]])
        k = Image.open(out / r["key"] / "key.png").convert("RGBA").resize((cell - 16, cell - 16), Image.LANCZOS)
        cat.paste(k, (x + 8, y + 8), k)
        dr.text((x + 8, y + 8), r["cat"], fill=(120, 90, 80), font=fs)
        nm = r["name"].split("（")[0].replace("表情・", "")
        dr.text((x + cell / 2, y + cell + lab / 2 - 4), nm[:12], fill=(42, 22, 16), font=ft, anchor="mm")
    quant(cat.convert("RGBA")).save(out / "catalog.png", optimize=True)

    # ---- 索引表
    L = ["# 比比素材庫", "",
         "Andy 第 3 版（`docs/marketing/video_1010/v3_brief.md` 第 12 條）：「表情、情境、道具要更豐富，做出來的要存成圖檔以後使用」。",
         "", "每組一個資料夾：`key.png`（512×512 透明代表格）、`sheet.png`（橫排 sprite，每格 256×256、透明）、`anim.webp`（動態、透明、無限循環）。",
         "全部同一隻、同一個場景座標（身體縮 0.75、中心 x=248、腳底 y=482），疊到影片時位置可以直接對齊。",
         f"重建：`python scripts/anim/bibi_library.py --bibi <scratchpad>/bibi --out docs/anim/bibi_library`（逐格 PNG 在 scratchpad，各批產生腳本見 `scripts/anim/`）。",
         "", "**造型規格以 `reference/parts_sheet_1011.webp`（Andy 10-11 官方部件總表）為準**，規格說明在 `reference/README.md`；"
         "總表逐件切出的透明部件（本體、耳、手掌、腳、五官、效果符號、道具、姿勢、動作參考）在 `parts/`（`parts/index.md`）。",
         "", f"總目錄：![總目錄](catalog.png)", "",
         "| 名稱 | 中文 | 類別 | 適合用途 | 格數 | 長度 | 預覽 |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| `{r['key']}` | {r['name']} | {r['cat']} | {r['use']} | {r['n']} | {r['ms']/1000:.2f} 秒 | "
                 f"[代表格]({r['key']}/key.png)・[sprite]({r['key']}/sheet.png)・[動畫]({r['key']}/anim.webp) |")
    (out / "index.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    tot = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    print(f"共 {len(rows)} 組，資料夾 {tot/1e6:.1f} MB")


if __name__ == "__main__":
    main()
