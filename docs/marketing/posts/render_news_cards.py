"""新聞圖卡（D+，Andy 10-28）：每則新聞 1 張 1080×1350 封面卡，資料來自 <資料夾>/{pre,intra,post}.json 的 card 欄位。
用法：CHROMIUM=... python render_news_cards.py <新聞資料夾> <pre|intra|post> [總覽圖路徑]；輸出 <資料夾>/<時段>/<序號>.jpg 並做重疊檢查。
股價漲跌數字（帶 + 或 - 號）用台股紅漲綠跌 #C81234／#07794F；類別色標籤用 D+ 色票。"""
import sys, json, re, html
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_dplus import *

UP, DN = "#C81234", "#07794F"
CAT = {"美股": "blue", "台股": "green", "財報": "mustard", "總經": "coral", "科技": "ink"}
CVAR = {"blue": "--bl", "green": "--gr", "mustard": "--my", "coral": "--co", "ink": "--ink"}
CTXT = {"blue": "#fff", "green": "#fff", "mustard": P["ink"], "coral": P["ink"], "ink": "#fff"}
STRIPE = ["--gr", "--co", "--bl", "--my"]; TINT = ["--tg", "--tc", "--tb", "--tm"]
NUM = re.compile(r"(?<![A-Za-z\d])\d[\d,.]*\s*[%％兆億萬元點]*")
e = html.escape
def hl(title):  # 標題第一個數字（含單位）加芥黃底線，並用主綠
    m = NUM.search(title)
    if not m: return e(title)
    return e(title[:m.start()]) + f'<span class="u num ser" style="font-weight:700">{e(m.group(0))}</span>' + e(title[m.end():])
def vcolor(v):
    v = v.strip()
    return UP if v.startswith("+") else DN if v.startswith(("-", "－", "−")) else "var(--ink)"
def card(d, idx, tot):
    c = d["card"]; cat = c["category"]; ck = CAT.get(cat, "green"); nums = c["numbers"][:4]
    n = len(nums); rh = 160 if n <= 3 else 128; gap = 16; top = 1176 - (n*rh + (n-1)*gap)
    fs = 112 if len(c["title"]) <= 8 else 96
    rows = ''.join(
        f'<div class="row" style="position:absolute;left:64px;top:{top + i*(rh+gap)}px;width:952px;height:{rh}px;background:var({TINT[i]});border-left:8px solid var({STRIPE[i]});border-radius:4px;padding:0 32px;justify-content:space-between">'
        f'<span class="T3b">{e(x["label"])}</span><span class="row" style="gap:12px;align-items:baseline"><span class="ser num" style="font-size:56px;line-height:72px;font-weight:700;color:{vcolor(x["value"])}">{e(x["value"])}</span>'
        f'<span class="T4b" style="color:var(--mu)">{e(x["unit"])}</span></span></div>' for i, x in enumerate(nums))
    date = d["data_date"][:10].replace("-", "/")
    return (f'<body style="{V}">{cover_head("")}'
            f'<div class="a row" style="left:64px;top:152px"><span class="T3b" style="background:var({CVAR[ck]});color:{CTXT[ck]};padding:4px 24px;border-radius:4px">{e(cat)}</span></div>'
            f'<div class="a" style="left:64px;top:232px;width:952px;height:{top-232-32}px"><div style="font-size:{fs}px;line-height:{fs+16}px;font-weight:800;text-wrap:balance">{hl(c["title"])}</div>'
            f'<div class="T2" style="margin-top:24px;color:var(--co)">{e(c["subtitle"])}</div></div>'
            f'{rows}<div class="hr" style="top:1200px"></div>'
            f'<div class="ft T4"><span class="num">{date}・{idx} / {tot}</span><span style="margin-left:auto"></span>{bibi("face_think", 88)}</div></body>')
if __name__ == "__main__":
    root = Path(sys.argv[1]); slot = sys.argv[2]
    items = json.load(open(root/f"{slot}.json", encoding="utf-8"))
    out = root/slot; render("", [card(d, i, len(items)) for i, d in enumerate(items, 1)], out)
    if len(sys.argv) > 3: sheet(out, [f"{i}.jpg" for i in range(1, len(items)+1)], sys.argv[3], len(items), 400)
