"""新聞圖卡（D+，Andy 10-28）：每則新聞 1 張 1080×1350 封面卡，資料來自 <資料夾>/{pre,intra,post}.json 的 card 欄位。
用法：CHROMIUM=... python render_news_cards.py <新聞資料夾> <pre|intra|post> [總覽圖路徑]；輸出 <資料夾>/<時段>/<序號>.jpg 並做重疊檢查。
股價漲跌數字（帶 + 或 - 號）用台股紅漲綠跌 #C81234／#07794F；類別色標籤用 D+ 色票。"""
import sys, os, io, json, re, html, base64
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
    col = UP if ("漲" in title and "跌" not in title) else DN if ("賣超" in title or "跌" in title) else None  # 台股紅漲綠跌
    st = f";color:{col}" if col else ""
    return e(title[:m.start()]) + f'<span class="u num ser" style="font-weight:700{st}">{e(m.group(0))}</span>' + e(title[m.end():])
def vcolor(v):
    v = v.strip()
    if v.startswith(("+", "買超")): return UP     # 台股紅漲（買超同紅）
    if v.startswith(("-", "－", "−", "賣超")): return DN
    return "var(--ink)"
TIMEW = ["上週", "去年", "昨日", "昨天", "本週", "單日", "單季"]
_M = {}
def wid(t):  # 用真實瀏覽器量字寬（以 96px 為單位 1.0），標題字型與渲染相同
    if t not in _M:
        _M[t] = _PG.evaluate("t=>{const s=document.createElement('span');s.style.cssText=\"font:800 96px 'Noto Sans CJK TC','Noto Sans TC',sans-serif;white-space:nowrap;position:absolute\";s.textContent=t;document.body.appendChild(s);const w=s.getBoundingClientRect().width;s.remove();return w}", t) / 96
    return _M[t]
_PG = None
def breakit(t, fs):
    """標題太長才斷行；優先序：空白 > 英文轉中文處 > 時間詞後 > 數字前；同級取兩行最均衡，兩行都要放得下。"""
    lim = (952 - 8) / fs * 0.92
    if wid(t) <= lim: return t
    cands = {0: [], 1: [], 2: [], 3: []}
    for i in range(1, len(t)):
        a, b = t[i-1], t[i]
        if a == " ": cands[0].append((i, t[:i].rstrip(), t[i:]))
        elif ord(a) < 0x2E80 and a != " " and ord(b) > 0x2E80: cands[1].append((i, t[:i], t[i:]))
        elif any(t[:i].endswith(w) for w in TIMEW): cands[2].append((i, t[:i], t[i:]))
        elif b.isdigit() and not (a.isdigit() or a in ".,"): cands[3].append((i, t[:i], t[i:]))
    for k in range(4):
        ok = [c for c in cands[k] if wid(c[1]) <= lim and wid(c[2]) <= lim]
        if ok:
            c = min(ok, key=lambda c: abs(wid(c[1]) - wid(c[2]))); return c[1] + "\n" + c[2]
    return t
def card_plain(d, idx, tot):
    c = d["card"]; cat = c["category"]; ck = CAT.get(cat, "green"); nums = c["numbers"][:4]
    n = len(nums); gap = 16
    fs = 112 if len(c["title"]) <= 8 else 96
    btitle = breakit(c["title"], fs)
    tl = btitle.count("\n") + 1; thh = tl*(fs+16) + 24 + 72     # 標題＋副標高度
    rtop = 232 + thh + 40; rh = min((1176 - rtop - (n-1)*gap) // n, 240)
    rtop = 1176 - (n*rh + (n-1)*gap)                              # 數字格貼底、高度吃掉空白
    rows = ''.join(
        f'<div class="row" style="position:absolute;left:64px;top:{rtop + i*(rh+gap)}px;width:952px;height:{rh}px;background:var({TINT[i]});border-left:8px solid var({STRIPE[i]});border-radius:4px;padding:0 32px;justify-content:space-between">'
        f'<span class="T3b">{e(x["label"])}</span><span class="row" style="gap:12px;align-items:baseline"><span class="ser num" style="font-size:72px;line-height:88px;font-weight:700;color:{vcolor(x["value"])}">{e(x["value"])}</span>'
        f'<span class="T4b" style="color:var(--mu)">{e(x["unit"])}</span></span></div>' for i, x in enumerate(nums))
    top = rtop
    date = d["data_date"][:10].replace("-", "/")
    return (f'<body style="{V}">{cover_head("")}'
            f'<div class="a row" style="left:64px;top:152px"><span class="T3b" style="background:var({CVAR[ck]});color:{CTXT[ck]};padding:4px 24px;border-radius:4px">{e(cat)}</span></div>'
            f'<div class="a" style="left:64px;top:232px;width:952px;height:{thh}px"><div style="font-size:{fs}px;line-height:{fs+16}px;font-weight:800;text-wrap:balance">{hl(btitle).replace(chr(10), "<br>")}</div>'
            f'<div class="T2" style="margin-top:24px;color:var(--co)">{e(c["subtitle"])}</div></div>'
            f'{rows}<div class="hr" style="top:1200px"></div>'
            f'<div class="ft T4"><span class="num">{date}・{idx} / {tot}</span><span style="margin-left:auto"></span>{bibi("face_think", 88)}</div></body>')
def bg_uri(path, w, h):
    """AI 背景：中心偏上裁成 w×h（Pollinations 先裁掉右下浮水印帶），放大到 2 倍寬用 Lanczos＋輕微銳化"""
    from PIL import ImageFilter
    im = Image.open(path).convert("RGB")
    if "pollinations" in str(path): im = im.crop((0, 0, im.width, im.height - int(im.height*0.07)))   # 裁掉右下浮水印帶（約 6%）
    sc = max(w*2/im.width, h*2/im.height); im = im.resize((int(im.width*sc)+1, int(im.height*sc)+1), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=3))
    from PIL import ImageStat, ImageEnhance
    m = ImageStat.Stat(im.convert("L")).mean[0]
    if m < 130: im = ImageEnhance.Brightness(im).enhance(min(1.3, 135/m))     # 偏暗的圖提亮到灰階均值約 135（審查項 4 要求 ≥120）
    x0 = (im.width - w*2)//2; y0 = int((im.height - h*2)*0.35)
    im = im.crop((x0, y0, x0+w*2, y0+h*2)).resize((w, h), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, "JPEG", quality=90); return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
def card(d, idx, tot, bg=None):
    """上半部情境圖（AI 或已審背景）＋下半部 D+ 文字區；沒有圖就用純色版 card_plain"""
    if not bg: return card_plain(d, idx, tot)
    c = d["card"]; cat = c["category"]; ck = CAT.get(cat, "green"); nums = c["numbers"][:4]; n = len(nums)
    fs = 112 if len(c["title"]) <= 8 else 96
    btitle = breakit(c["title"], fs); tl = btitle.count("\n") + 1
    rh, g = 64, 8; rtop = 1240 - (n*rh + (n-1)*g)
    subt = rtop - 24 - 72; titt = subt - 16 - tl*(fs+16); chipt = titt - 16 - 56; imgh = (chipt - 24 - 128) // 8 * 8
    rows = ''.join(
        f'<div class="row" style="position:absolute;left:64px;top:{rtop + i*(rh+g)}px;width:952px;height:{rh}px;background:var({TINT[i]});border-left:8px solid var({STRIPE[i]});border-radius:4px;padding:0 24px;justify-content:space-between">'
        f'<span class="T3b">{e(x["label"])}</span><span class="row" style="gap:8px;align-items:baseline"><span class="ser num" style="font-size:56px;line-height:64px;font-weight:700;color:{vcolor(x["value"])}">{e(x["value"])}</span>'
        f'<span class="T4b" style="color:var(--mu)">{e(x["unit"])}</span></span></div>' for i, x in enumerate(nums))
    date = d["data_date"][:10].replace("-", "/")
    return (f'<body style="{V}">{cover_head("")}'
            f'<img class="a" data-g=1 style="left:64px;top:128px;width:952px;height:{imgh}px;object-fit:cover;border-radius:4px" src="{bg_uri(bg, 952, imgh)}">'
            f'<div class="a row" style="left:64px;top:{chipt}px"><span class="T3b" style="background:var({CVAR[ck]});color:{CTXT[ck]};padding:4px 24px;border-radius:4px">{e(cat)}</span></div>'
            f'<div class="a" style="left:64px;top:{titt}px;width:952px;font-size:{fs}px;line-height:{fs+16}px;font-weight:800">{hl(btitle).replace(chr(10), "<br>")}</div>'
            f'<div class="a T2" style="left:64px;top:{subt}px;color:var(--co);white-space:nowrap">{e(c["subtitle"])}</div>'
            f'{rows}<div class="hr" style="top:1264px"></div>'
            f'<div class="a row T4" style="left:64px;top:1272px;width:952px;height:64px;color:var(--mu)"><span class="num">{date}・{idx} / {tot}</span><span style="margin-left:auto"></span>{bibi("face_think", 60)}</div></body>')
if __name__ == "__main__":
    root = Path(sys.argv[1]); slot = sys.argv[2]
    from playwright.sync_api import sync_playwright as _sp
    _pw = _sp().start(); _br = _pw.chromium.launch(executable_path=os.environ.get("CHROMIUM") or None); _PG = _br.new_page(); _PG.set_content("<body></body>")
    items = json.load(open(root/f"{slot}.json", encoding="utf-8"))
    out = root/slot; bgmap = json.load(open(root/"news_bg.json", encoding="utf-8")) if (root/"news_bg.json").exists() else {}
    pages = [card(d, i, len(items), (root/bgmap[d["id"]]) if bgmap.get(d["id"]) else None) for i, d in enumerate(items, 1)]
    _br.close(); _pw.stop()      # 量字寬用的瀏覽器先關掉，才能開渲染用的
    render("", pages, out)
    if len(sys.argv) > 3: sheet(out, [f"{i}.jpg" for i in range(1, len(items)+1)], sys.argv[3], len(items), 400)
