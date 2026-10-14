"""交件前品質檢查（Andy 10-11 版面鐵則＋這批任務的 6 項）。
python validate_output.py → check/report.md（並印摘要）；任何一項不合格 exit 1。
1 重疊：所有登記元素兩兩不相交（父子關係除外；同一父層的兄弟要檢查）
2 文字：數字逐一對照 content.json；禁用字；頁碼；標題字數
3 390 寬縮圖：最小字在 390 寬下的像素高
4 一致性：LOGO 區塊逐像素相同、頁碼位置、比比高度範圍、色票
5 比比：貼紙外緣一圈的顏色（深描邊比例）、角落透明、無方塊底
6 人工逐張看：本程式只產出 390 縮圖與放大檢查圖，人工結果寫在報告最後（手動填）
"""
import json, os, re, sys
from PIL import Image
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
L = json.load(open(HERE + "check/layout.json"))
CT = json.load(open(HERE + "content.json"))
out = []; fails = []


def inter(a, b, tol=0.5):
    return min(a[2], b[2]) - max(a[0], b[0]) > tol and min(a[3], b[3]) - max(a[1], b[1]) > tol


def chain(els, name):
    by = {e["name"]: e for e in els}; res = set(); cur = by.get(name)
    while cur and cur.get("parent"):
        res.add(cur["parent"]); cur = by.get(cur["parent"])
    return res


# 1 重疊
total_pairs = 0; hits = []
for n, pg in sorted(L.items(), key=lambda x: int(x[0])):
    els = [e for e in pg["els"] if e["kind"] not in ("fx",)]
    for i in range(len(els)):
        for j in range(i + 1, len(els)):
            a, b = els[i], els[j]
            if a["name"] in chain(els, b["name"]) or b["name"] in chain(els, a["name"]): continue
            total_pairs += 1
            if inter(a["box"], b["box"]): hits.append((n, a["name"], b["name"], a["box"], b["box"]))
    for e in pg["els"]:
        x0, y0, x1, y1 = e["box"]
        if x0 < 0 or y0 < 0 or x1 > 1080 or y1 > 1350: hits.append((n, e["name"], "畫布邊界", e["box"], None))
        if e["kind"] in ("text",) and (x0 < 30 or x1 > 1050): hits.append((n, e["name"], "安全邊界30px", e["box"], None))
out.append(f"## 1 重疊檢查\n程式 {len(L)} 張、{total_pairs} 組元素配對，{len(hits)} 筆")
for h in hits: out.append(f"- 第 {h[0]} 張：{h[1]} × {h[2]} {h[3]} {h[4]}")
if hits: fails.append("重疊")

# 2 文字／事實
facts_txt = " ".join(f["text"] for f in CT["facts"].values()) + CT["event"]["title"] + CT["event"]["date"]
allow_nums = {str(i) for i in range(1, 11)} | {"01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "0", "50", "100", "2026", "2025", "1984", "10", "14", "13", "7", "15", "3", "2"}
bad = []; forbid = ["買進", "賣出", "目標價", "推薦買", "http", "www", ".com", "@", "會員", "VIP", "Email"]
for n, pg in L.items():
    alltext = " ".join(t["text"] for t in pg["texts"])
    for t in pg["texts"]:
        for num in re.findall(r"\d+(?:\.\d+)?", t["text"]):
            if num in allow_nums: continue
            if num not in facts_txt: bad.append((n, t["name"], num, t["text"]))
        for fw in forbid:
            if fw in t["text"]: bad.append((n, t["name"], "禁用字:" + fw, t["text"]))
    pn = [t for t in pg["texts"] if t["name"] == "頁碼_字"]
    if not pn or pn[0]["text"] != f"{int(n):02d} / 10": bad.append((n, "頁碼", pn[0]["text"] if pn else "缺", ""))
    if n == "10" and CT["disclaimer"] not in alltext.replace(" ", ""): bad.append((n, "免責", "缺免責", ""))
    if n == "10" and "搜尋「哩股哩股」" not in alltext: bad.append((n, "CTA", "缺", ""))
cover = CT["slides"][0]["title"]; han = len(re.findall(r"[一-鿿]", cover))
out.append(f"\n## 2 文字與事實\n封面標題「{cover}」中文 {han} 字（上限 14）；數字對照 content.json 不符 {len(bad)} 筆")
if han > 14: fails.append("封面字數")
for b in bad: out.append(f"- 第 {b[0]} 張 {b[1]}：{b[2]}｜{b[3]}")
if bad: fails.append("文字")

# 3 390 寬
os.makedirs(HERE + "check/w390", exist_ok=True)
small = []
for n, pg in L.items():
    im = Image.open(HERE + f"final/slide_{int(n):02d}.png").resize((390, 488), Image.LANCZOS); im.save(HERE + f"check/w390/slide_{int(n):02d}.png")
    for t in pg["texts"]:
        px = t["size"] * 390 / 1080
        if t["role"] in ("body", "bubble", "title", "sub") and t["size"] < 28: small.append((n, t["name"], t["size"]))
        if px < 7.9: small.append((n, t["name"], t["size"]))
mins = {n: min(t["size"] for t in pg["texts"]) for n, pg in L.items()}
out.append(f"\n## 3 手機 390 寬\n各張最小字級（1080 寬）：{mins}；390 寬下最小 {min(mins.values()) * 390 / 1080:.1f}px（腳註／標籤），正文最小 28px＝{28 * 390 / 1080:.1f}px。不合格 {len(small)} 筆")
for s_ in small: out.append(f"- 第 {s_[0]} 張 {s_[1]} {s_[2]}px")
if small: fails.append("字級")

# 4 一致性
ref = np.asarray(Image.open(HERE + "final/slide_01.png").crop((36, 32, 446, 124))).astype(int)
logo_diff = {}
for n in range(1, 11):
    a = np.asarray(Image.open(HERE + f"final/slide_{n:02d}.png").crop((36, 32, 446, 124))).astype(int)
    logo_diff[n] = float(np.abs(a - ref).mean())
bh = {n: round(next(e for e in pg["els"] if e["kind"] == "bibi")["box"][3] - next(e for e in pg["els"] if e["kind"] == "bibi")["box"][1]) for n, pg in L.items()}
pn_box = {n: next(e for e in pg["els"] if e["name"] == "頁碼")["box"] for n, pg in L.items()}
same_pn = len({tuple(v) for v in pn_box.values()}) == 1
out.append(f"\n## 4 一致性\nLOGO 區塊與第 1 張逐像素平均差：{ {k: round(v, 2) for k, v in logo_diff.items()} }（0＝完全相同）\n頁碼位置一致：{same_pn}\n比比顯示高度（px）：{bh}")
if max(logo_diff.values()) > 1.0 or not same_pn: fails.append("一致性")

# 5 比比去背
st = json.load(open(HERE + "assets/stickers.json")); rows = []
for k, m in st.items():
    im = np.asarray(Image.open(HERE + f"assets/bibi_{k}.png").convert("RGBA")).astype(int)
    a = im[..., 3]; op = a > 0
    pad = np.pad(op, 1); inner = pad[1:-1, 1:-1] & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
    rgb = im[..., :3][inner]; lum = rgb.mean(1)
    light = float((lum > 170).mean()); semi = float(((a > 0) & (a < 128)).sum() / max(op.sum(), 1))
    corners = [a[0, 0], a[0, -1], a[-1, 0], a[-1, -1]]
    rows.append((k, m["src"].split("anim/")[-1], round(light * 100, 1), round(semi * 100, 2), all(c == 0 for c in corners)))
out.append("\n## 5 比比去背\n| 貼紙 | 素材 | 外緣一圈亮色比例% | 半透明像素% | 四角透明 |\n|---|---|---|---|---|")
for r in rows: out.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} |")
for r in rows:
    if r[2] > 25 or not r[4]: fails.append(f"去背{r[0]}")
out.append("（外緣亮色比例＝貼紙最外一圈像素中亮度>170 的比例；有白邊或方塊底會偏高。四腳無手為人工逐張檢查，見第 6 節。）")

rep = "# ASML 輪播 品質檢查報告（validate_output.py 產出）\n\n" + "\n".join(out) + f"\n\n## 結論\n不合格項目：{fails or '無'}\n"
manual = HERE + "check/manual.md"
if os.path.exists(manual): rep += "\n" + open(manual).read()
open(HERE + "check/report.md", "w").write(rep)
print(rep)
sys.exit(1 if fails else 0)
