"""raw 截圖 → 1080x1350 白底素材（置中、等比例，不裁切圖）＋底部「示意圖，非實物比例」小字。"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont
RAW, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
S = json.load(open(f"{RAW}/_summary.json", encoding="utf8"))
F = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 28)
man = {}
for slot, v in S.items():
    im = Image.open(f"{RAW}/{slot}_raw.png").convert("RGB")
    w = 1000
    h = round(im.height * w / im.width)
    if h > 1190:
        h = 1190; w = round(im.width * h / im.height)
    im = im.resize((w, h), Image.LANCZOS)
    cv = Image.new("RGB", (1080, 1350), "#FFFFFF")
    y = 60 + (1190 - h) // 2
    cv.paste(im, ((1080 - w) // 2, y))
    d = ImageDraw.Draw(cv)
    d.line([(40, 1286), (1040, 1286)], fill="#CFCFCF", width=2)
    d.text((40, 1296), f"{v['title']}　｜　示意圖，非實物比例", font=F, fill="#595959")
    cv.save(f"{OUT}/{slot}_2d.png", optimize=True)
    man[slot] = dict(title=v["title"], size=cv.size, cut=v.get("cut", []), codes=v.get("codes", []))
    print(slot, cv.size)
json.dump(man, open(f"{OUT}/_manifest.json", "w", encoding="utf8"), ensure_ascii=False, indent=1)
