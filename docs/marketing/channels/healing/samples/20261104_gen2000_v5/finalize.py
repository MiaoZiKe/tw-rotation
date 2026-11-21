#!/usr/bin/env python3
"""v5 收尾：caption.md、image_sources.md、三張對照總覽（compare_v4_v5_postN.png，上排 v4、下排 v5）、清暫存。
全流程：python3 gen2.py && node render.js && python3 contrast.py && python3 finalize.py"""
import json, os, re, glob
from PIL import Image
B = os.path.dirname(os.path.abspath(__file__)); SRC = os.path.join(B, "..", "20261104_gen2000")
FONT = "Noto Serif CJK TC／Noto Sans CJK TC（Bold 主句、Regular 小字；SIL OFL 1.1，可商用）"
SCN = {"price": "樓頂連成往上爬的房價折線，對照小燈下幾乎平的存款簿", "qtable": "圓桌俯視，碗排成問號，問號的點是一碗熱湯", "scale": "天平：一碗熱湯（輕）對一疊帳單與圈起來的房租日（重）",
       "steamq": "碗上的熱氣原本要捲成問號，越往上越淡", "ring": "問號收成一圈：六碗圍著桌心一盞小燈",
       "treepot": "大樹與小苗，樹根沒伸到小苗那一塊土", "treepot2": "大樹與小苗，樹根多伸了一段（虛線）", "tree": "大樹與一把刻度尺，最上一格亮著（成長率）",
       "means": "九根柱子，一根特高把平均線拉高，亮的是中位數", "slips": "九張薪資單，正中間那張被抽出來亮著",
       "mailboxes": "一面信箱只有一格有信、透出暖光", "windows": "102 格公寓窗，87 格亮著（核准）", "patch": "一張房租帳單，右下角縫了暖色補丁",
       "mailbox1": "公告與一只亮著的信箱", "teacup": "一杯冒著熱氣的茶，杯口亮著"}
for p in ("post1", "post2", "post3", "post4"):
    d = json.load(open(f"{B}/{p}/data.json", encoding="utf-8"))
    rows = ["| 檔案 | 概念 | 來源 |", "|---|---|---|"]
    for s in d["slides"]:
        base = s["name"]
        if s.get("illus"): rows.append("| %s.png | %s | 自繪向量（程式產生 SVG），程式排版（HTML／CSS／SVG，Playwright 截圖） |" % (base, SCN[s["illus"]]))
        else: rows.append("| %s.png | 出處頁，無插圖 | 程式排版 |" % base)
    open(f"{B}/{p}/image_sources.md", "w", encoding="utf-8").write(
        "# %s 圖片來源（逐張）\n\n" % p + "\n".join(rows) + "\n\n字體：%s。\n全部自製：無照片、無 AI 圖、無比比、無人物；資料數字出處見各篇出處頁與說明文字。色碼全走 CSS 變數（--w-*）。\n" % FONT)
S = 0.36
def sheet(rows, out):
    W = max(len(r) for r in rows) * (int(1080 * S) + 12) + 12; H = len(rows) * (int(1350 * S) + 12) + 12
    img = Image.new("RGB", (W, H), (60, 60, 60))
    for ri, r in enumerate(rows):
        for ci, f in enumerate(r):
            im = Image.open(f).resize((int(1080 * S), int(1350 * S)), Image.LANCZOS); img.paste(im, (12 + ci * (im.width + 12), 12 + ri * (im.height + 12)))
    img.save(out)
V4 = os.path.join(B, "..", "20261104_gen2000_v4")
def sheet2(rows, out, S=0.3):
    n = max(len(r) for r in rows); tw, th = int(1080 * S), int(1350 * S)
    img = Image.new("RGB", (n * (tw + 12) + 12, len(rows) * (th + 12) + 12), (60, 60, 60))
    for ri, r in enumerate(rows):
        for ci, f in enumerate(r):
            img.paste(Image.open(f).resize((tw, th), Image.LANCZOS), (12 + ci * (tw + 12), 12 + ri * (th + 12)))
    img.save(out)
for p in ("post1", "post2", "post3", "post4"):
    d = json.load(open(f"{B}/{p}/data.json", encoding="utf-8"))
    old = sorted(glob.glob(f"{V4}/{p}/*.png")); old = [f for f in old if ".bg" not in f]
    new = [f"{B}/{p}/{s['name']}.png" for s in d["slides"]]
    sheet2([old, new], f"{B}/compare_v4_v5_{p}.png")
for f in glob.glob(B + "/post*/*.bg.png") + glob.glob(B + "/post*/*.tx.json"): os.remove(f)
print("finalize ok")
# caption.md 與 txt 同步（2026-11-04 加入）：post1 取 txt 全文；post2～4 取「說明文字」之後，去掉重疊檢查行
_CAP = {"post1": "範例1_threads.txt", "post2": "範例2_ig輪播.txt", "post3": "範例3_ig輪播.txt", "post4": "範例4_微光篇.txt"}
for _p, _f in _CAP.items():
    _t = open(os.path.join(SRC, _f), encoding="utf-8").read()
    _t = "\n".join(l for l in _t.split("\n") if not l.startswith("重疊檢查")).strip()
    if _p == "post1":
        _t = _t.split("【貼文全文】\n", 1)[1].strip()
    else:
        _t = re.split(r"^說明文字[^\n]*：\n", _t, flags=re.M)[1].strip()
    open(f"{B}/{_p}/caption.md", "w", encoding="utf-8").write("# %s 說明文字（取自 %s 最新版，finalize.py 自動同步）\n\n%s\n" % (_p, _f, _t))
print("caption sync ok")
