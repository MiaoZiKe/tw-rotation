#!/usr/bin/env python3
"""收尾：caption.md（取自 txt 最新版）、image_sources.md、縮圖並排、N/F/M 對照、清掉暫存。
全流程：python3 gen2.py && node render.js && python3 contrast.py && python3 finalize.py"""
import json, os, re, glob, subprocess
from PIL import Image
B = os.path.dirname(os.path.abspath(__file__)); SRC = os.path.join(B, "..", "20261104_gen2000")
def txt(n): return open(os.path.join(SRC, n), encoding="utf-8").read()
FONT = "Noto Serif CJK TC／Noto Sans CJK TC（Regular；SIL OFL 1.1，可商用，字檔在 ~/.fonts）"
# caption
t1 = txt("範例1_threads.txt").strip()
open(B + "/post1/caption.md", "w", encoding="utf-8").write("# post1 文案（Threads，取自範例1_threads.txt 最新版）\n\n" + t1 + "\n")
for p, f in (("post2", "範例2_ig輪播.txt"), ("post3", "範例3_ig輪播.txt")):
    t = txt(f); m = re.search(r"說明文字[^\n]*\n(.*?)(?:\n重疊檢查|\Z)", t, re.S)
    open(f"{B}/{p}/caption.md", "w", encoding="utf-8").write("# %s 說明文字（IG，取自%s最新版）\n\n%s\n" % (p, f, m.group(1).strip()))
# image_sources
SC = {"S1": "S1 租屋小套房一盞燈＋帳單", "S2": "S2 末班捷運車廂", "S3": "S3 便利商店微波便當", "S4": "S4 桌上帳單薪資單＋檯燈", "S6": "S6 陽台晾衣（玻璃門）", "S7": "S7 天花板吸頂燈", "S8": "S8 空書桌"}
DS = {"post1": "內政部〈住宅價格負擔能力統計〉2025Q2（媒體轉述，2026-11-04 取用）；1989 臺北 8.58 倍為巢運引用估算、口徑不同（自行重繪）",
      "post2": "內政部 2025 年第 2 季全國房貸負擔率 43.12%（圖表）；內政部戶政統計 2025 總生育率 0.695（數字，媒體轉述）",
      "post3": "主計總處薪資及生產力統計 2025、國民所得統計 2025 概估、家庭收支調查 2025（媒體轉述）"}
for p in ("post1", "post2", "post3"):
    d = json.load(open(f"{B}/{p}/data.json", encoding="utf-8"))
    rows = ["| 檔案 | 來源 | 資料來源 | 字體授權 |", "|---|---|---|---|"]
    for s in d["slides"]:
        fn = "threads.png" if p == "post1" else s["name"] + ".png"
        kind = "自繪向量插圖（%s，程式產生，SVG）＋" % SC[s["illus"]] if s.get("illus") else ""
        chart = "長條／比例條自繪（長度依數值成比例）＋" if any(b["t"] in ("bars", "strip") for b in s.get("blocks", [])) else ""
        rows.append("| %s | %s%s程式排版（HTML／CSS／SVG，Playwright 截圖）＋程式產生顆粒與暗角 | %s | %s |" % (fn, kind, chart, DS[p] if (chart or s["type"] == "sources" or s["name"].endswith(("02_inner", "03_inner"))) else "—（無資料圖表）", FONT))
    open(f"{B}/{p}/image_sources.md", "w", encoding="utf-8").write("# %s 圖片來源（逐張）\n\n" % p + "\n".join(rows) + "\n\n全部自製：無照片、無 AI 圖、無比比、無人物；所有色碼走 CSS 變數（--w-*）。\n")
# 0.36 並排
S = 0.36
def sheet(files, out):
    ims = [Image.open(f).resize((int(1080 * S), int(1350 * S)), Image.LANCZOS) for f in files]
    W = Image.new("RGB", (len(ims) * (ims[0].width + 12) + 12, ims[0].height + 24), (60, 60, 60))
    for i, im in enumerate(ims): W.paste(im, (12 + i * (im.width + 12), 12))
    W.save(out)
sheet([B + "/post1/threads.png"], B + "/post1/sheet_036.png")
for p in ("post2", "post3"):
    sheet(sorted(f for f in glob.glob(f"{B}/{p}/0*.png") if ".bg." not in f), f"{B}/{p}/sheet_036.png")
# N/F/M 對照（post1 同一頁）
subprocess.run(["node", B + "/cmp.js"], check=True)
shots = [f"{B}/post1/_cmp_{p}.png" for p in "NFM"]
sheet(shots, B + "/compare_NFM_post1.png")
for f in shots + glob.glob(B + "/post*/*.bg.png") + glob.glob(B + "/post*/*.tx.json"): os.remove(f)
print("finalize ok")
