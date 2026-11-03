"""公司 LOGO 512 方形白底版。只做指稱用途：不改色、不變形、不裁切，等比例置中放在白底。
來源只用 repo 內既有圖（data/logos/<代號>.png、data/logos/tc/<網域>.png）。
輸出：<OUT>/logos/<公司>.png 與 <OUT>/logos/_manifest.json"""
import json, os, re, sys
from PIL import Image

ROOT = "/home/user/tw-rotation/.claude/worktrees/agent-a269082c5aeb4fe8e"
OUT = sys.argv[1]
os.chdir(ROOT)
t = open("site/tc/logos.js", encoding="utf8").read()
dom = dict(re.findall(r"'([^']+)':\s*'([a-z0-9.\-]+)'", t))

# (公司, 代號, 是否前20, 用在哪)
CO = [("台積電", "2330", 1), ("日月光", "3711", 1), ("聯發科", "2454", 1), ("美光台灣", "", 1), ("台達電", "2308", 1),
      ("廣達", "2382", 1), ("聯電", "2303", 1), ("聯詠", "3034", 1), ("華碩", "2357", 1), ("世界先進", "5347", 1),
      ("鴻海", "2317", 1), ("南亞科", "2408", 1), ("力積電", "6770", 1), ("瑞昱", "2379", 1), ("群聯", "8299", 1),
      ("矽品", "", 1), ("緯穎", "6669", 1), ("緯創", "3231", 1), ("Lam Research", "", 1), ("華邦電", "2344", 1),
      ("應用材料", "", 0), ("ASML", "", 0), ("英業達", "2356", 0), ("和碩", "4938", 0), ("光寶", "2301", 0),
      ("瑞鼎", "3592", 0), ("欣興", "3037", 0), ("KLA", "", 0), ("NVIDIA", "", 0), ("京元電子", "2449", 0),
      ("仁寶", "2324", 0), ("慧榮", "", 0), ("智易", "3596", 0)]
FILE = {"Lam Research": "Lam_Research", "美光台灣": "美光台灣"}

os.makedirs(f"{OUT}/logos", exist_ok=True)
man = []
for name, code, top20 in CO:
    d = dom.get(name)
    cands = []
    if code and os.path.exists(f"data/logos/{code}.png"):
        cands.append((f"data/logos/{code}.png", Image.open(f"data/logos/{code}.png")))
    if d and os.path.exists(f"data/logos/tc/{d}.png"):
        cands.append((f"data/logos/tc/{d}.png", Image.open(f"data/logos/tc/{d}.png")))
    cands = [c for c in cands if max(c[1].size) >= 32]
    row = dict(name=name, code=code, domain=d, top20=top20)
    if not cands:
        row.update(status="缺圖", src="", px=0)
        man.append(row)
        continue
    src, im = max(cands, key=lambda c: max(c[1].size))
    im = im.convert("RGBA")
    # 只裁掉透明／純白的空邊（不改色、不變形）
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255)); bg.alpha_composite(im)
    from PIL import ImageChops
    diff = ImageChops.difference(bg.convert("RGB"), Image.new("RGB", im.size, (255, 255, 255))).convert("L").point(lambda v: 255 if v > 12 else 0)
    bb = diff.getbbox()
    if bb: im = im.crop(bb)
    px = max(im.size)
    if px < 32:
        row.update(status="缺圖（原圖僅殘留小圖示）", src=src, px=px); man.append(row); continue
    # 等比例放大，上限 320；最多放 4 倍，避免糊成一團
    box = min(320, px * 4)
    r = box / max(im.size)
    im2 = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    cv = Image.new("RGB", (512, 512), "#FFFFFF")
    cv.paste(im2, ((512 - im2.width) // 2, (512 - im2.height) // 2), im2)
    fn = FILE.get(name, name)
    cv.save(f"{OUT}/logos/{fn}.png", optimize=True)
    row.update(status=("可用" if px >= 96 else ("低解析" if px >= 32 else "缺圖（原圖僅殘留小圖示）")), src=src, px=px, file=f"logos/{fn}.png", scale=round(r, 2))
    man.append(row)
json.dump(man, open(f"{OUT}/logos/_manifest.json", "w", encoding="utf8"), ensure_ascii=False, indent=1)
for r in man:
    print(r["name"], r["status"], r["px"], r.get("scale", ""), r["src"])
