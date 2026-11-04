#!/usr/bin/env python3
"""v3 收尾：caption.md、image_sources.md、三張對照總覽（compare_post1/2/3.png，上排無人、下排有人）、清暫存。
全流程：python3 gen2.py && node render.js && python3 contrast.py && python3 finalize.py"""
import json, os, re, glob
from PIL import Image
B = os.path.dirname(os.path.abspath(__file__)); SRC = os.path.join(B, "..", "20261104_gen2000")
FONT = "Noto Serif CJK TC／Noto Sans CJK TC（Regular；SIL OFL 1.1，可商用）"
SCN = {"home": "小套房（窗外對面大樓、書桌帳單泡麵、床）", "dinner": "過年飯桌（圓桌碗筷、紅包袋、窗外淡煙火）", "deskbills": "書桌（帳單、計算機、記帳 App、便利貼）",
       "window": "窗前夜景（對面樓群亮窗）", "balcony": "封閉陽台收衣", "bedroom": "臥室（床頭燈、月曆、書架）", "salary": "薪資書桌（薪資單、計算機、便利貼、記帳 App）",
       "skyline": "窗外亮晃晃高樓群 vs 近處小窗", "store": "便利商店微波加熱", "desk": "書桌前（履歷螢幕、書架）", "mrt": "末班捷運車廂（座椅、扶手、窗外流光）",
       "morning": "晨光小桌（筆記本、馬克杯）", "blocks": "窗外整排公寓亮窗", "rent": "租金轉帳桌（手機、月曆、植物）"}
for p in ("post1", "post2", "post3", "post4"):
    d = json.load(open(f"{B}/{p}/data.json", encoding="utf-8"))
    rows = ["| 檔案（無人／有人） | 來源 | 人物 |", "|---|---|---|"]
    for s in d["slides"]:
        base = s["name"]
        sc = ("自繪向量場景（%s；背景／中景／前景三層，程式產生 SVG）＋" % SCN[s["illus"]]) if s.get("illus") else ""
        who = "原創簡化線條人形（無五官、不像真人、非照片、非 AI 圖）" if s.get("illus") else "無人物（出處頁，兩版相同）"
        rows.append("| %s_noperson.png／%s_person.png | %s程式排版（HTML／CSS／SVG，Playwright 截圖）＋顆粒與暗角 | %s |" % (base, base, sc, who))
    open(f"{B}/{p}/image_sources.md", "w", encoding="utf-8").write(
        "# %s 圖片來源（逐張）\n\n" % p + "\n".join(rows) + "\n\n字體：%s。\n全部自製：無照片、無 AI 圖、無比比；人物為原創簡化線條，非真人；資料數字出處見各篇出處頁與說明文字。色碼全走 CSS 變數（--w-*）。\n" % FONT)
S = 0.36
def sheet(rows, out):
    W = max(len(r) for r in rows) * (int(1080 * S) + 12) + 12; H = len(rows) * (int(1350 * S) + 12) + 12
    img = Image.new("RGB", (W, H), (60, 60, 60))
    for ri, r in enumerate(rows):
        for ci, f in enumerate(r):
            im = Image.open(f).resize((int(1080 * S), int(1350 * S)), Image.LANCZOS); img.paste(im, (12 + ci * (im.width + 12), 12 + ri * (im.height + 12)))
    img.save(out)
for p, out in (("post1", "compare_post1.png"), ("post2", "compare_post2.png"), ("post3", "compare_post3.png"), ("post4", "compare_post4.png")):
    d = json.load(open(f"{B}/{p}/data.json", encoding="utf-8"))
    names = [s["name"] for s in d["slides"]]
    sheet([[f"{B}/{p}/{n}_noperson.png" for n in names], [f"{B}/{p}/{n}_person.png" for n in names]], f"{B}/{out}")
for f in glob.glob(B + "/post*/*.bg.png") + glob.glob(B + "/post*/*.tx.json"): os.remove(f)
print("finalize ok")
# caption.md 與 txt 同步（2026-11-04 加入）：post1 取 txt 全文；post2～4 取「說明文字」之後，去掉重疊檢查行
_CAP = {"post1": "範例1_threads.txt", "post2": "範例2_ig輪播.txt", "post3": "範例3_ig輪播.txt", "post4": "範例4_微光篇.txt"}
for _p, _f in _CAP.items():
    _t = open(os.path.join(SRC, _f), encoding="utf-8").read()
    _t = "\n".join(l for l in _t.split("\n") if not l.startswith("重疊檢查")).strip()
    if _p != "post1":
        _t = re.split(r"^說明文字[^\n]*：\n", _t, flags=re.M)[1].strip()
    open(f"{B}/{_p}/caption.md", "w", encoding="utf-8").write("# %s 說明文字（取自 %s 最新版，finalize.py 自動同步）\n\n%s\n" % (_p, _f, _t))
print("caption sync ok")
