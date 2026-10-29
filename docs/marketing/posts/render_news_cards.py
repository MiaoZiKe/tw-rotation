"""新聞圖卡（D+，Andy 10-28）：每則新聞 1 張 1080×1350 封面卡，資料來自 <資料夾>/{pre,intra,post}.json 的 card 欄位。
用法：CHROMIUM=... python render_news_cards.py <新聞資料夾> <pre|intra|post> [總覽圖路徑]；輸出 <資料夾>/<時段>/<序號>.jpg 並做重疊檢查。
股價漲跌數字（帶 + 或 - 號）用台股紅漲綠跌 #C81234／#07794F；類別色標籤用 D+ 色票。"""
import sys, os, io, json, re, html, base64
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_dplus import *
from datetime import datetime as datetime

UP, DN = "#C81234", "#07794F"
CAT = {"美股": "blue", "台股": "green", "財報": "mustard", "總經": "coral", "科技": "ink"}
CVAR = {"blue": "--bl", "green": "--gr", "mustard": "--my", "coral": "--co", "ink": "--ink"}
CTXT = {"blue": "#fff", "green": "#fff", "mustard": P["ink"], "coral": P["ink"], "ink": "#fff"}
STRIPE = ["--gr", "--co", "--bl", "--my"]; TINT = ["--tg", "--tc", "--tb", "--tm"]
NUM = re.compile(r"(?<![A-Za-z\d])\d[\d,.]*\s*[%％兆億萬]*(?:美元|元|點)?")   # 「億美元」整段保留（Andy 10-28：單位改成億美元）
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
        elif ord(a) < 0x2E80 and a != " " and ord(b) > 0x2E80 and b not in "%％兆億萬元點美": cands[1].append((i, t[:i], t[i:]))
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
# ---- cover_v2：全幅圖封面（Andy 10-28：口袋證券等級的完成度，保留 D+ 品牌）----
DEEP = "#123325"        # 主綠加深（只用於壓字底，不當前景色）
CHIP2 = {"美股": ("#4C86B0", "#fff"), "台股": ("#C81234", "#fff"), "財報": (P["mustard"], P["ink"]), "總經": (P["coral"], P["ink"]), "科技": ("#F7F3EA", P["ink"])}   # 深色底上的實心標籤（台股紅底白字）
ICONS = {"美股": "chart", "台股": "chart", "財報": "coin", "總經": "pct", "科技": "chip", "default": "target"}
def hl2(line):   # 白字標題裡的第一個數字（含單位）改芥黃＋襯線
    m = NUM.search(line)
    if not m: return e(line)
    return e(line[:m.start()]) + f'<span class="ser num" style="color:var(--my);font-weight:700">{e(m.group(0))}</span>' + e(line[m.end():])
def lines_of(v):
    if not v: return []
    return [x for x in (v if isinstance(v, list) else str(v).replace("／", "\n").split("\n")) if x.strip()]
def bg_cover(path, w, h):
    """AI 圖鋪滿 w×h（取上緣，放大用 Lanczos＋輕微銳化；偏暗者提亮）"""
    from PIL import ImageFilter, ImageStat, ImageEnhance
    im = Image.open(path).convert("RGB")
    if "pollinations" in str(path): im = im.crop((0, 0, im.width, im.height - int(im.height*0.07)))
    m = ImageStat.Stat(im.convert("L")).mean[0]
    if m < 130: im = ImageEnhance.Brightness(im).enhance(min(1.3, 135/m))
    sc = max(w/im.width, h/im.height); im = im.resize((int(im.width*sc)+1, int(im.height*sc)+1), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=1.5, percent=50, threshold=3))
    x0 = (im.width - w)//2; y0 = int((im.height - h)*0.2)
    im = im.crop((x0, y0, x0+w, y0+h)); b = io.BytesIO(); im.save(b, "JPEG", quality=92)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
BIBI_BY_CAT = {"科技": "face_think", "台股": "magnifier", "財報": "trophy", "美股": "rocket", "總經": "calendar"}
def hero_art(c, tl, cat):
    """沒有合格 AI 圖時的上半部：D+ 色系幾何圖形＋放大的關鍵數字（取自大標第一個數字）＋比比"""
    hero = None
    for l in tl:
        m = NUM.search(l)
        if m: hero = m.group(0).strip(); break
    num = re.match(r"[\d,.]+", hero).group(0) if hero else ""
    unit = hero[len(num):].strip() if hero else ""
    label = ""
    for x in c["numbers"]:
        if num and num.replace(",", "") in x["value"].replace(",", "").replace("+", ""): label = x["label"]; break
    bib = bibi(BIBI_BY_CAT.get(cat, "face_think"), 330, "").replace("height:330px", "height:330px;max-width:300px;object-fit:contain")
    shapes = (
        '<div class="a" data-bg=1 style="left:0;top:0;width:1080px;height:1350px;background:linear-gradient(135deg,#1E4D3B 0%,#2C6A6E 60%,#3F6F94 100%)"></div>'
        '<div class="a" data-bg=1 style="left:640px;top:150px;width:520px;height:520px;border-radius:50%;background:#D2583C;opacity:.92"></div>'
        '<div class="a" data-bg=1 style="left:556px;top:96px;width:132px;height:132px;border-radius:50%;background:#E0A526"></div>'
        '<div class="a" data-bg=1 style="left:-140px;top:520px;width:380px;height:380px;border-radius:50%;border:28px solid rgba(255,255,255,.16)"></div>'
        '<div class="a" data-bg=1 style="left:720px;top:700px;width:44px;height:44px;border-radius:50%;background:#F7F3EA;opacity:.85"></div>'
        '<div class="a" data-bg=1 style="left:800px;top:704px;width:120px;height:36px;border-radius:18px;background:rgba(255,255,255,.2)"></div>')
    art = f'<div class="a" style="left:700px;top:210px;width:300px;height:330px;display:flex;align-items:flex-end;justify-content:center">{bib.replace("<img", "<img data-art=1", 1)}</div>'
    hx = ""
    if num:
        hx = ((f'<div class="a T3b" style="left:64px;top:312px;color:var(--my);letter-spacing:.08em">{e(label)}</div>' if label else "") +
              f'<div class="a ser num" style="left:64px;top:372px;color:#fff;font-size:208px;line-height:224px;font-weight:700;white-space:nowrap;text-shadow:0 4px 24px rgba(0,0,0,.25)">{e(num)}<span style="font-size:72px;color:var(--my);margin-left:12px">{e(unit)}</span></div>')
    return shapes, art + hx
def card_v2(d, idx, tot, bg=None):
    c = d["card"]; cat = c["category"]; ck = CAT.get(cat, "green")
    tl = lines_of(c.get("cover_title")) or breakit(c["title"], 88).split("\n")
    dl = lines_of(c.get("cover_desc"))
    if not dl:   # 暫代：副標＋關鍵數字串成一句說明（財經編輯補 cover_desc 後即不再使用）
        nums = "、".join(f'{x["label"]} {x["value"]}{x["unit"]}' for x in c["numbers"][:3])
        dl = [c["subtitle"] + " " + nums]
    fs = min(96, int(944 / max(wid(l) for l in tl)) // 4 * 4)
    tl = tl[:2]; dl = dl[:2]
    import math
    nl = sum(max(1, math.ceil(wid(x)*36/96/ (944/96) * 1.04)) for x in dl)   # 說明實際折行數（每行 944px、36px 字）
    hi = next((i for i, l in enumerate(tl) if NUM.search(l)), -1)
    foot = 1272; dh = nl*52; dtop = 1240 - dh; ttop = dtop - 24 - len(tl)*(fs+12); chipt = ttop - 24 - 60
    extra = ""
    if bg: img = f'<div class="a" data-bg=1 style="left:0;top:0;width:1080px;height:1000px;background:url({bg_cover(bg, 1080, 1000)}) center/cover"></div>'
    else:
        img, extra = hero_art(c, tl, cat)
    shade = (f'<div class="a" data-bg=1 style="left:0;top:0;width:1080px;height:1350px;background:linear-gradient(180deg,rgba(12,38,28,.55) 0%,rgba(12,38,28,0) 16%,rgba(12,38,28,0) 34%,rgba(18,51,37,.82) 52%,{DEEP} 66%,{DEEP} 100%)"></div>')
    sh = "text-shadow:0 2px 14px rgba(0,0,0,.35)"
    return (f'<body style="{V};background:{DEEP}">{img}{shade}{extra}'
            f'<div class="brand T3b" style="color:#fff;top:48px;{sh}">哩股哩股</div>'
            f'<div class="a row" style="left:64px;top:{chipt}px"><span class="T3b" style="background:{CHIP2.get(cat, (P["green"], "#fff"))[0]};color:{CHIP2.get(cat, (P["green"], "#fff"))[1]};padding:6px 28px;border-radius:4px;letter-spacing:.12em">{e(cat)}</span></div>'
            f'<div class="a" style="left:64px;top:{ttop}px;width:952px;color:#fff;font-size:{fs}px;line-height:{fs+12}px;font-weight:800;letter-spacing:-.01em;{sh}">'
            + "".join(f'<div style="white-space:nowrap">{hl2(l) if i == hi else e(l)}</div>' for i, l in enumerate(tl)) + '</div>'
            f'<div class="a T3" style="left:64px;top:{dtop}px;width:952px;color:rgba(255,255,255,.92);line-height:52px;{sh}">' + "".join(f"<div>{e(l)}</div>" for l in dl) + '</div>'
            f'<div class="a" style="left:64px;top:1264px;width:952px;height:2px;background:rgba(255,255,255,.28)"></div>'
            f'<div class="a row T4" style="left:64px;top:{foot+4}px;width:952px;height:56px;color:rgba(255,255,255,.78)"><span class="num">{d["data_date"][:10].replace("-", "/")}・{idx} / {tot}</span></div></body>')
# ---- cover_v3（Andy 10-28：比比全拿掉、色調太醜）：單一主色＋一個強調色＋中性色；漲跌仍用台股紅綠 ----
PALS = {
 "A": dict(name="深海藍單色", bg="#0A1A2F", ink="#FFFFFF", sub="#C3D2E6", acc="#7CC4FF", chip="#1E5BD8", chipfg="#FFFFFF",
           tile="#FFFFFF", tilebd="#FFFFFF", tl="#475569", tu="#64748B", tv="#0A1A2F", rule="rgba(255,255,255,.25)", foot="#A9BBD3",
           duo=("#050E1C", "#8FB8E8"), shade="10,26,47", ring="rgba(124,196,255,.22)", panel="linear-gradient(135deg,#0F2A4F 0%,#123C7A 100%)", dark=True),
 "B": dict(name="亮白藍橘", bg="#F3F6FB", ink="#0B1F3A", sub="#475569", acc="#E8590C", chip="#0B3D91", chipfg="#FFFFFF",
           tile="#FFFFFF", tilebd="#D5DDEA", tl="#475569", tu="#64748B", tv="#0B1F3A", rule="#C9D3E3", foot="#64748B",
           duo=("#0B2447", "#A9C4EA"), shade="11,36,71", ring="rgba(255,255,255,.22)", panel="linear-gradient(135deg,#0B3D91 0%,#1F5FC4 100%)", dark=False),
}
PALS["C"] = dict(name="比比色", bg="#FEF8E8", ink="#2A1410", sub="#5A3E36", acc="#2A1410", chip="#F58C78", chipfg="#2A1410", mark="#FFB4A0",
           tile="#FFFFFF", tilebd="#EBDCC8", tl="#5A3E36", tu="#7A6258", tv="#2A1410", rule="#E6D5BE", foot="#7A6258",
           duo=("#2A1410", "#FFD9C9"), shade="42,20,16", ring="rgba(255,255,255,.38)", panel="linear-gradient(135deg,#FFB4A0 0%,#F58C78 100%)", dark=False,
           herofg="#2A1410", toppanel="#2A1410")
SLOTN = {"pre": "盤前新聞", "intra": "盤中新聞", "post": "盤後新聞", "wk1": "週末精選", "wk2": "週末精選", "fb": "精選"}
def hdr_of(c, slot):
    """卡片右上角時段字；常備文庫（知識卡）自帶 hdr，不冒充「盤後新聞」。"""
    return c.get("hdr") or SLOTN.get(slot, "")
def foot_of(c, idx, tot):
    """卡片底列：左＝資料來源（c["foot"]），右＝張數（只有多張才放，單張不放「1 / 1」）。"""
    L = f'<span class="T4" style="flex:1;white-space:nowrap">{e(c["foot"])}</span>' if c.get("foot") else ""
    R = f'<span class="num">{idx} / {tot}</span>' if tot > 1 else ""
    return L + R
def vfs(v):
    """資訊列右側數值字級：數字用 56px 襯線；含中文的文字值縮成 44px，避免字高貼滿 80px 的列（常備文庫知識卡）。"""
    return "font-size:44px;line-height:56px" if re.search(r"[\u2e80-\ua000\uff00-\uffef]", v) else "font-size:56px;line-height:64px"
def vcls(v):
    """含中文的值整串用無襯線（避免「IC 設計公司」「運算晶片＋HBM」英數襯線、中文黑體混字）；純英數才用襯線。"""
    return "num" if re.search(r"[\u2e80-\ua000\uff00-\uffef]", v) else "ser num"
def hero_fs(num):
    """大字字級依字數縮放（全形 1.0、半形 0.55 em），上限 280px：大數字填滿灰框，不留右半邊空白。"""
    w = sum(1.0 if ord(ch) > 0x2E80 else 0.55 for ch in num) or 1
    return int(max(120, min(280, 800 / w)))
def bg_duo(path, w, h, pal):
    """AI 圖統一轉成同一組雙色調（暗→亮），整組色調一致；取上緣鋪滿"""
    from PIL import ImageFilter, ImageOps, ImageStat
    im = Image.open(path).convert("RGB")
    if "pollinations" in str(path): im = im.crop((0, 0, im.width, im.height - int(im.height*0.07)))
    g = ImageOps.autocontrast(im.convert("L"), cutoff=1)
    sc = max(w/g.width, h/g.height); g = g.resize((int(g.width*sc)+1, g.height and int(g.height*sc)+1), Image.LANCZOS).filter(ImageFilter.UnsharpMask(radius=1.5, percent=50, threshold=3))
    x0 = (g.width - w)//2; y0 = int((g.height - h)*0.2); g = g.crop((x0, y0, x0+w, y0+h))
    out = ImageOps.colorize(g, pal["duo"][0], pal["duo"][1]); b = io.BytesIO(); out.save(b, "JPEG", quality=92)
    return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
def vcolor3(v, pal):
    v = v.strip()
    if v.startswith(("+", "買超")): return UP
    if v.startswith(("-", "－", "−", "賣超")): return DN
    return pal["tv"]
def hero3(c, tl, pal):
    """沒有 AI 圖：純色漸層面板＋幾何圓環＋放大的關鍵數字（取自大標第一個數字），無任何插圖"""
    hero = None
    for l in tl:
        m = NUM.search(l)
        if m: hero = m.group(0).strip(); break
    shapes = (f'<div class="a" data-bg=1 style="left:0;top:0;width:1080px;height:760px;background:{pal["panel"]}"></div>'
              f'<div class="a" data-bg=1 style="left:560px;top:-120px;width:640px;height:640px;border-radius:50%;border:2px solid {pal["ring"]}"></div>'
              f'<div class="a" data-bg=1 style="left:640px;top:-40px;width:480px;height:480px;border-radius:50%;border:2px solid {pal["ring"]}"></div>'
              f'<div class="a" data-bg=1 style="left:720px;top:40px;width:320px;height:320px;border-radius:50%;background:{pal["ring"]}"></div>'
              + "".join(f'<div class="a" data-bg=1 style="left:0;top:{y}px;width:1080px;height:1px;background:{pal["ring"]}"></div>' for y in (260, 340, 420)))
    if not hero: return shapes, ""
    num = re.match(r"[\d,.]+", hero).group(0); unit = hero[len(num):].strip(); label = ""
    for x in c["numbers"]:
        if num.replace(",", "") in x["value"].replace(",", "").replace("+", ""): label = x["label"]; break
    fg = pal.get("herofg", "#fff"); fsz = 208 if len(num) <= 5 else 160
    hx = ((f'<div class="a T3b" style="left:64px;top:176px;color:{fg};opacity:.85;letter-spacing:.08em">{e(label)}</div>') if label else "") + \
         f'<div class="a ser num" style="left:64px;top:232px;color:{fg};font-size:{fsz}px;line-height:{fsz+16}px;font-weight:700;white-space:nowrap">{e(num)}<span style="font-size:64px;margin-left:12px">{e(unit)}</span></div>'
    return shapes, hx
def card_v3(d, idx, tot, bg=None, pal="A", slot="pre"):
    P3 = PALS[pal]; c = d["card"]; cat = c["category"]
    tl = (lines_of(c.get("cover_title")) or breakit(c["title"], 88).split("\n"))[:2]
    dl = (lines_of(c.get("cover_desc")) or [c["subtitle"]])[:2]
    fs = min(96, int(944 / max(wid(l) for l in tl)) // 4 * 4)
    nums = c["numbers"][:3]; n = len(nums); rh, g = 88, 10
    rtop = 1240 - (n*rh + (n-1)*g); dtop = rtop - 28 - len(dl)*52; ttop = dtop - 20 - len(tl)*(fs+12); chipt = ttop - 20 - 56
    hi = next((i for i, l in enumerate(tl) if NUM.search(l)), -1)
    def hl3(l):
        m = NUM.search(l)
        if not m: return e(l)
        mk = f';background:{P3["mark"]};padding:0 6px;border-radius:4px' if P3.get("mark") else ""
        return e(l[:m.start()]) + f'<span class="ser num" style="color:{P3["acc"]};font-weight:700{mk}">{e(m.group(0))}</span>' + e(l[m.end():])
    extra = ""
    if bg:
        img = f'<div class="a" data-bg=1 style="left:0;top:0;width:1080px;height:760px;background:url({bg_duo(bg, 1080, 760, P3)}) center/cover"></div>'
    else: img, extra = hero3(c, tl, P3)
    sh = P3["shade"]
    shade = (f'<div class="a" data-bg=1 style="left:0;top:0;width:1080px;height:1350px;background:linear-gradient(180deg,rgba({sh},{0.55 if bg else 0}) 0%,rgba({sh},0) 12%,rgba({sh},0) 30%,rgba({sh},.0) 34%,{P3["bg"]}EE 44%,{P3["bg"]} 52%,{P3["bg"]} 100%)"></div>')
    rows = ''.join(
        f'<div class="row" style="position:absolute;left:64px;top:{rtop + i*(rh+g)}px;width:952px;height:{rh}px;background:{P3["tile"]};border:1px solid {P3["tilebd"]};border-left:8px solid {P3["chip"]};border-radius:4px;padding:0 28px;justify-content:space-between">'
        f'<span class="T3b" style="color:{P3["tl"]}">{e(x["label"])}</span><span class="row" style="gap:8px;align-items:baseline"><span class="ser num" style="font-size:56px;line-height:64px;font-weight:700;color:{vcolor3(x["value"], P3)}">{e(x["value"])}</span>'
        f'<span class="T4b" style="color:{P3["tu"]}">{e(x["unit"])}</span></span></div>' for i, x in enumerate(nums))
    date = d["data_date"][:10].replace("-", "/"); topc = P3.get("toppanel", "#fff") if (not bg and P3.get("toppanel")) else "#fff"
    return (f'<body style="{V};background:{P3["bg"]}">{img}{shade}{extra}'
            f'<div class="a" style="left:64px;top:48px;width:952px;height:2px;background:{topc};opacity:.45" data-bg=1></div>'
            f'<div class="brand T3b" style="color:{topc};top:64px">哩股哩股</div><div class="hdate T4b num" style="color:{topc};top:68px">{SLOTN.get(slot, "")}・{date}</div>'
            f'<div class="a row" style="left:64px;top:{chipt}px"><span class="T3b" style="background:{P3["chip"]};color:{P3["chipfg"]};padding:4px 28px;border-radius:4px;letter-spacing:.12em">{e(cat)}</span></div>'
            f'<div class="a" style="left:64px;top:{ttop}px;width:952px;color:{P3["ink"]};font-size:{fs}px;line-height:{fs+12}px;font-weight:800;letter-spacing:-.01em">'
            + "".join(f'<div style="white-space:nowrap">{hl3(l) if i == hi else e(l)}</div>' for i, l in enumerate(tl)) + '</div>'
            f'<div class="a T3" style="left:64px;top:{dtop}px;width:952px;color:{P3["sub"]};line-height:52px">' + "".join(f"<div>{e(l)}</div>" for l in dl) + '</div>'
            f'{rows}<div class="a" style="left:64px;top:1264px;width:952px;height:2px;background:{P3["rule"]}"></div>'
            f'<div class="a row T4" style="left:64px;top:1272px;width:952px;height:56px;color:{P3["foot"]}"><span class="num">{idx} / {tot}</span></div></body>')
# ---- cover_v4（--pal D，Andy 10-28 退件：AI 圖不可染色、色調要舒適）----
D4 = dict(bg="#FAF9F6", ink="#1F2328", sub="#4B5563", mu="#6B7280", acc="#A85D49", tile="#FFFFFF", tbd="#E5E2DA", bar="#CFCBC2", panel="#EFEDE8", rule="#D9D5CB")
def bg_plain(path, w, h, ya=0.6):
    """AI 圖保持原色：只裁切與縮放（取上緣），不套任何色調、遮罩、亮度調整"""
    im = Image.open(path).convert("RGB")
    if "pollinations" in str(path): im = im.crop((0, 0, im.width, im.height - int(im.height*0.07)))
    sc = max(w/im.width, h/im.height); im = im.resize((int(im.width*sc)+1, int(im.height*sc)+1), Image.LANCZOS)
    x0 = (im.width - w)//2; y0 = int((im.height - h)*ya); im = im.crop((x0, y0, x0+w, y0+h))
    b = io.BytesIO(); im.save(b, "JPEG", quality=93); return "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()
def card_v4(d, idx, tot, bg=None, slot="pre"):
    K = D4; c = d["card"]; cat = c["category"]
    tl = (lines_of(c.get("cover_title")) or breakit(c["title"], 88).split("\n"))[:2]
    dl = (lines_of(c.get("cover_desc")) or [c["subtitle"]])[:2]
    fs = min(88, int(920 / max(wid(l) for l in tl)) // 4 * 4)
    nums = c["numbers"][:3]; n = len(nums); rh, g = 80, 8
    rtop = 1240 - (n*rh + (n-1)*g); dtop = rtop - 24 - len(dl)*52; ttop = dtop - 16 - len(tl)*(fs+12); chipt = ttop - 16 - 56
    imgh = (chipt - 16 - 128) // 8 * 8
    hi = next((i for i, l in enumerate(tl) if c["hl"] and c["hl"] in l), -1) if "hl" in c else next((i for i, l in enumerate(tl) if NUM.search(l)), -1)
    def hl4(l):
        if "hl" in c:      # 自動產稿（scripts/social_news.py）指定要畫底線的字；空字串＝不畫
            k = l.find(c["hl"]) if c["hl"] else -1
            a, b = (k, k + len(c["hl"])) if k >= 0 else (None, None)
        else:
            m = NUM.search(l); a, b = (m.start(), m.end()) if m else (None, None)
        if a is None: return e(l)
        return e(l[:a]) + f'<span class="ser num" style="font-weight:700;text-decoration:underline;text-decoration-color:{K["acc"]};text-decoration-thickness:6px;text-underline-offset:8px">{e(l[a:b])}</span>' + e(l[b:])
    if bg: art = f'<img class="a" data-g=1 style="left:64px;top:128px;width:952px;height:{imgh}px;border-radius:4px" src="{bg_plain(bg, 952, imgh)}">'
    else:
        hero = c.get("hero") or next((NUM.search(l).group(0).strip() for l in tl if NUM.search(l)), None)
        if not hero and nums: hero = (nums[0]["value"] + nums[0]["unit"]).strip()
        mm = re.match(r"[約逾\s]*([\d,.]+)\s*(.*)", hero or ""); num = mm.group(1) if mm else (hero or ""); unit = mm.group(2) if mm else ""
        hit = next((x for x in nums if num and num.replace(",", "") in x["value"].replace(",", "")), None)
        label = c.get("hero_label") or (hit["label"] if hit else "")
        if hit and "美元" in hit["unit"] and "美元" not in unit: unit = hit["unit"]   # 對應單位含美元時顯示完整（如「億美元」），不截成「億」
        fsz = hero_fs(num)
        art = (f'<div class="a" data-bg=1 style="left:64px;top:128px;width:952px;height:{imgh}px;background:{K["panel"]};border-radius:4px"></div>'
               f'<div class="a T3b" style="left:96px;top:{128 + (imgh - fsz - 16 - 48)//2}px;color:{K["mu"]}">{e(label)}</div>'
               f'<div class="a ser num" style="left:96px;top:{128 + (imgh - fsz - 16 - 48)//2 + 64}px;color:{K["ink"]};font-size:{fsz}px;line-height:{fsz+16}px;height:{fsz+16}px;font-weight:700;white-space:nowrap">{e(num)}<span style="font-size:64px;line-height:64px;margin-left:12px;color:{K["sub"]}">{e(unit)}</span></div>')
    rows = ''.join(
        f'<div class="row" style="position:absolute;left:64px;top:{rtop + i*(rh+g)}px;width:952px;height:{rh}px;background:{K["tile"]};border:1px solid {K["tbd"]};border-left:8px solid {K["bar"]};border-radius:4px;padding:0 28px;justify-content:space-between">'
        f'<span class="T3b" style="color:{K["sub"]}">{e(x["label"])}</span><span class="row" style="gap:8px;align-items:baseline"><span class="{vcls(x["value"])}" style="{vfs(x["value"])};font-weight:700;color:{vcolor3(x["value"], dict(tv=K["ink"]))}">{e(x["value"])}</span>'
        f'<span class="T4b" style="color:{K["mu"]}">{e(x["unit"])}</span></span></div>' for i, x in enumerate(nums))
    date = d["data_date"][:10].replace("-", "/")
    return (f'<body style="{V};background:{K["bg"]}"><div class="a" style="left:64px;top:40px;width:952px;height:4px;background:{K["ink"]}" data-bg=1></div>'
            f'<div class="brand T3b" style="color:{K["ink"]}">哩股哩股</div><div class="hdate T4b num" style="color:{K["mu"]}">{hdr_of(c, slot)}・{date}</div>'
            f'<div class="a" style="left:64px;top:112px;width:952px;height:2px;background:{K["rule"]}" data-bg=1></div>{art}'
            f'<div class="a row" style="left:64px;top:{chipt}px"><span class="T3b" style="background:{K["acc"]};color:#fff;padding:4px 28px;border-radius:4px;letter-spacing:.12em">{e(cat)}</span></div>'
            f'<div class="a" style="left:64px;top:{ttop}px;width:952px;color:{K["ink"]};font-size:{fs}px;line-height:{fs+12}px;font-weight:800">'
            + "".join(f'<div style="white-space:nowrap">{hl4(l) if i == hi else e(l)}</div>' for i, l in enumerate(tl)) + '</div>'
            f'<div class="a T3" style="left:64px;top:{dtop}px;width:952px;color:{K["sub"]};line-height:52px">' + "".join(f"<div>{e(l)}</div>" for l in dl) + '</div>'
            f'{rows}<div class="a" style="left:64px;top:1264px;width:952px;height:2px;background:{K["rule"]}"></div>'
            f'<div class="a row T4" style="left:64px;top:1272px;width:952px;height:56px;color:{K["mu"]}">{foot_of(c, idx, tot)}</div></body>')
# ---- D-實景（Andy 10-28）：上方放主體公司的實景照片（原色、只裁切），照片上方帶狀區放小標（主體＋事件），大數字留在下方大標 ----
PHOTO_LIB = Path(__file__).resolve().parents[3] / "social" / "photo_lib"
KIND_LAYOUT = {"總部/廠房": "D-實景(公司)", "產品": "D-實景(產品)", "相關場景": "D-實景(類別)", "類別": "D-實景(類別)"}
TOPIC_CAT = {"總經": "總經"}          # 主體不在名單時，依新聞主題分類退到類別圖池
ROTATE_DAYS = 14
def _pool(d):
    try: return json.loads((d / "pool.json").read_text(encoding="utf-8"))
    except Exception: return None
# 央行圖池的照片是「特定一家央行」的建築（Fed／ECB／日銀）：只配給講那一家的新聞；泰國央行之類其他央行不配圖（10-29 泰國央行配到 Fed 大樓）
CB_PHOTO = [(r"Fed|FOMC|聯準會|美國央行|鮑爾", "Federal Reserve"), (r"歐洲央行|ECB|拉加德", "European Central Bank"), (r"日銀|日本央行|日本銀行|植田", "Bank of Japan")]
def cb_filter(text):
    """回傳央行圖池可用照片的 query 關鍵字清單；空清單＝這則講的不是這三家，央行圖池整池不用。"""
    return [q for kw, q in CB_PHOTO if re.search(kw, text or "")]
def _rotate(d, key, used, today, allow_unreviewed, only=None):
    """圖池裡挑一張：只要已審；近 14 天用過的往後排（全都用過就挑最久沒用的）。回傳 (路徑, meta) 或 None。
    only＝照片 query 必須含其中一個字（央行圖池用）。"""
    pool = _pool(d)
    if not pool: return None
    ph = [m for m in pool.get("photos", []) if (m.get("reviewed") or (allow_unreviewed and not m.get("reject_reason") and m.get("prescreen") != "fail")) and (d / m.get("file", "")).exists()]
    if only is not None:
        ph = [m for m in ph if not m.get("query") or any(q in m["query"] for q in only)]     # 沒寫 query 的視為通用
    if not ph: return None
    used = used or {}
    def last(m): return max(used.get(f"{key}/{m['file']}", []) or [""])
    def recent(m):
        l = last(m)
        if not (l and today): return False
        try: return (datetime.fromisoformat(today) - datetime.fromisoformat(l)).days < ROTATE_DAYS
        except Exception: return False
    m = sorted(ph, key=lambda m: (recent(m), last(m), m["file"]))[0]
    return d / m["file"], m
# 主體不在名單（或名單裡沒有可用圖）時，依新聞文字對應類別池（Andy 10-28：「如果是外商，或是總經面相關呢？」）。依序比對，先中先用。
TOPIC_KW = [
    ("記憶體", r"記憶體|DRAM|NAND|HBM|快閃|SSD|DDR\d"),
    ("半導體", r"晶圓|半導體|製程|先進封裝|CoWoS|晶片|IC設計|EUV|微影|蝕刻|奈米"),
    ("AI伺服器", r"AI伺服器|伺服器|GPU|機櫃|算力|加速器"),
    ("資料中心", r"資料中心|數據中心|雲端|超大規模|data center"),
    ("散熱", r"散熱|液冷|水冷|均熱"),
    ("PCB", r"PCB|印刷電路板|載板|CCL|銅箔"),
    ("網通", r"網通|交換器|光通訊|光模組|矽光子|CPO|路由器|乙太網路"),
    ("電信", r"電信|5G|基地台|資費|頻譜"),
    ("汽車", r"汽車|電動車|車廠|新車|自駕|EV\b|車用"),
    ("航太", r"航太|飛機|客機|航空|波音|空巴"),
    ("能源", r"石油|原油|油價|天然氣|LNG|煉油|OPEC|核電|電廠|綠能|太陽能|風電"),
    ("航運", r"航運|貨櫃|運價|散裝|船隊|SCFI"),
    ("鋼鐵", r"鋼鐵|鋼價|鋼材"),
    ("石化", r"石化|塑化|乙烯"),
    ("金融", r"銀行|金控|壽險|投行|券商|華爾街|基金|資產管理|併購"),
    ("零售消費", r"零售|超市|量販|消費者|飲料|球鞋|服飾|電商"),
    ("娛樂媒體", r"串流|影音|電影|影集|訂閱戶"),
    ("消費電子", r"手機|iPhone|筆電|平板|遊戲機|穿戴|消費性電子|PC\b"),
]
MACRO_KW = [      # 總經子類（依序比對）；都沒中就用 _category/總經
    ("總經_央行", r"Fed|FOMC|聯準會|央行|理監事|日銀|歐洲央行|ECB|英格蘭銀行|鮑爾|降息|升息|貨幣政策|縮表|QE"),
    ("總經_物價就業", r"CPI|PCE|PPI|通膨|物價|非農|就業|失業率|薪資|初領"),
    ("總經_貿易關稅", r"關稅|貿易|出口|進口|外銷訂單|海關|貿易戰"),
    ("總經_能源", r"油價|原油|OPEC|布蘭特|WTI|天然氣"),
    ("總經_匯率", r"匯率|新台幣|美元指數|日圓|日元|人民幣|歐元|升值|貶值|外匯"),
    ("總經_利率債券", r"殖利率|公債|美債|債券|利差|國債"),
    ("總經_房市", r"房市|房價|房貸|新屋|成屋|營建|住宅"),
    ("總經_景氣", r"GDP|PMI|景氣|燈號|經濟成長|衰退|工業生產|消費者信心|零售銷售"),
]
def topic_cats(text, topic=None):
    """依新聞文字回傳候選類別池（依序）。總經新聞：命中的子類 → 總經；其他：產業類別。"""
    t = text or ""; out = []
    macro = [c for c, kw in MACRO_KW if re.search(kw, t, re.I)]
    inds = [c for c, kw in TOPIC_KW if re.search(kw, t, re.I)]
    if topic == "總經":
        out = macro[:1] + ["總經"] + inds[:1]
    else:
        macro = [c for c in macro if c != "總經_匯率"]      # 非總經新聞的「人民幣／歐元」只是計價幣別，不配鈔票圖（10-29 摩爾線程配到歐元）
        out = inds[:2] + macro[:1] + (["總經"] if macro else [])
    return [c for i, c in enumerate(out) if c not in out[:i]]
def photo_pick(subject, topic=None, used=None, today=None, allow_unreviewed=False, text=None):
    """選圖順序（Andy 10-28 v3）：該公司已審圖池（近 14 天用過的避開、輪替）→ 該公司所屬類別池
    → 依新聞文字對應的類別池（總經新聞先找子類：央行／物價就業／利率債券／匯率／能源／貿易關稅／景氣／房市）→ None（灰框大數字）。
    主體名只認 aliases.json 的完全相同名稱。回傳 (路徑, meta, layout 標籤, 使用紀錄鍵) 或 None。"""
    try: aliases = json.loads((PHOTO_LIB / "aliases.json").read_text(encoding="utf-8"))
    except Exception: aliases = {}
    slug = aliases.get((subject or "").strip())
    cats = []
    if slug:
        r = _rotate(PHOTO_LIB / slug, slug, used, today, allow_unreviewed)
        if r: return r[0], r[1], KIND_LAYOUT.get(r[1].get("kind"), "D-實景(公司)"), f"{slug}/{r[1]['file']}"
        try: cats = [next((t.get("category") for t in json.loads((PHOTO_LIB / "targets.json").read_text(encoding="utf-8")) if t.get("slug") == slug), None)]
        except Exception: cats = []
    if re.search(r"央行|中央銀行", subject or "") and not cb_filter(subject):
        return None                      # 其他國家央行：沒有對應照片，總經池又全是台北街景 → 灰框大數字，不配錯圖
    cats += topic_cats(f"{subject or ''} {text or ''}", topic) + [TOPIC_CAT.get(topic or "")]
    seen = set()
    for cat in cats:
        if not cat or cat in seen: continue
        seen.add(cat)
        only = cb_filter(f"{subject or ''} {text or ''}") if cat == "總經_央行" else None
        if only == []: continue
        r = _rotate(PHOTO_LIB / "_category" / cat, f"_category/{cat}", used, today, allow_unreviewed, only)
        if r: return r[0], r[1], "D-實景(類別)", f"_category/{cat}/{r[1]['file']}"
    return None
def photo_for(subject, allow_unreviewed=False):
    """相容舊呼叫：只回 (路徑, meta)。"""
    r = photo_pick(subject, allow_unreviewed=allow_unreviewed)
    return (r[0], r[1]) if r else None
def credit_of(meta):
    a = re.sub(r"\s+", " ", meta.get("author") or "不詳").strip()
    if len(a) > 24: a = a[:23] + "…"
    return f"攝影：{a}／{meta.get('license', '')}・Wikimedia Commons"
def card_photo(d, idx, tot, photo, slot="pre", pending=False):
    """photo＝(路徑, meta)。小標＝cover_title 第 1 行（主體＋事件）放照片上方的乾淨帶狀區；大標只留數字那行，避免重複。"""
    K = D4; c = d["card"]; cat = c["category"]; path, meta = photo
    tl0 = (lines_of(c.get("cover_title")) or breakit(c["title"], 88).split("\n"))[:2]
    kicker = c.get("kicker") or tl0[0]
    tl = tl0[1:] if len(tl0) > 1 else tl0
    dl = (lines_of(c.get("cover_desc")) or [c["subtitle"]])[:2]
    fs = min(88, int(920 / max(wid(l) for l in tl)) // 4 * 4)
    nums = c["numbers"][:3]; n = len(nums); rh, g = 80, 8
    rtop = 1240 - (n*rh + (n-1)*g); dtop = rtop - 24 - len(dl)*52; ttop = dtop - 16 - len(tl)*(fs+12); chipt = ttop - 16 - 56
    ktop = 128; ptop = 216; credt = chipt - 16 - 40; imgh = (credt - 8 - ptop) // 8 * 8
    def hl5(l):
        h = c.get("hl")
        if h is not None:
            k = l.find(h) if h else -1; a, b = (k, k + len(h)) if k >= 0 else (None, None)
        else:
            m = NUM.search(l); a, b = (m.start(), m.end()) if m else (None, None)
        if a is None: return e(l)
        return e(l[:a]) + f'<span class="ser num" style="font-weight:700;text-decoration:underline;text-decoration-color:{K["acc"]};text-decoration-thickness:6px;text-underline-offset:8px">{e(l[a:b])}</span>' + e(l[b:])
    tag = '<span class="T4b" style="margin-left:16px;color:#fff;background:#B45309;padding:0 12px;border-radius:4px">待審</span>' if pending else ""
    date = d["data_date"][:10].replace("-", "/")
    rows = ''.join(
        f'<div class="row" style="position:absolute;left:64px;top:{rtop + i*(rh+g)}px;width:952px;height:{rh}px;background:{K["tile"]};border:1px solid {K["tbd"]};border-left:8px solid {K["bar"]};border-radius:4px;padding:0 28px;justify-content:space-between">'
        f'<span class="T3b" style="color:{K["sub"]}">{e(x["label"])}</span><span class="row" style="gap:8px;align-items:baseline"><span class="{vcls(x["value"])}" style="{vfs(x["value"])};font-weight:700;color:{vcolor3(x["value"], dict(tv=K["ink"]))}">{e(x["value"])}</span>'
        f'<span class="T4b" style="color:{K["mu"]}">{e(x["unit"])}</span></span></div>' for i, x in enumerate(nums))
    return (f'<body style="{V};background:{K["bg"]}"><div class="a" style="left:64px;top:40px;width:952px;height:4px;background:{K["ink"]}" data-bg=1></div>'
            f'<div class="brand T3b" style="color:{K["ink"]}">哩股哩股</div><div class="hdate T4b num" style="color:{K["mu"]}">{hdr_of(c, slot)}・{date}</div>'
            f'<div class="a" style="left:64px;top:112px;width:952px;height:2px;background:{K["rule"]}" data-bg=1></div>'
            f'<div class="a row" style="left:64px;top:{ktop}px;width:952px;height:72px"><span class="T2" style="font-weight:800;color:{K["ink"]};white-space:nowrap">{e(kicker)}</span>{tag}</div>'
            f'<img class="a" data-g=1 style="left:64px;top:{ptop}px;width:952px;height:{imgh}px;border-radius:4px" src="{bg_plain(path, 952, imgh, 0.5)}">'
            f'<div class="a row" style="left:64px;top:{credt}px;width:952px;height:40px;justify-content:flex-end"><span style="font-size:28px;line-height:40px;color:{K["mu"]};white-space:nowrap">{e(credit_of(meta))}</span></div>'
            f'<div class="a row" style="left:64px;top:{chipt}px"><span class="T3b" style="background:{K["acc"]};color:#fff;padding:4px 28px;border-radius:4px;letter-spacing:.12em">{e(cat)}</span></div>'
            f'<div class="a" style="left:64px;top:{ttop}px;width:952px;color:{K["ink"]};font-size:{fs}px;line-height:{fs+12}px;font-weight:800">'
            + "".join(f'<div style="white-space:nowrap">{hl5(l) if NUM.search(l) or (c.get("hl") and c["hl"] in l) else e(l)}</div>' for l in tl) + '</div>'
            f'<div class="a T3" style="left:64px;top:{dtop}px;width:952px;color:{K["sub"]};line-height:52px">' + "".join(f"<div>{e(l)}</div>" for l in dl) + '</div>'
            f'{rows}<div class="a" style="left:64px;top:1264px;width:952px;height:2px;background:{K["rule"]}"></div>'
            f'<div class="a row T4" style="left:64px;top:1272px;width:952px;height:56px;color:{K["mu"]}">{foot_of(c, idx, tot)}</div></body>')
def card_auto(d, idx, tot, slot="pre", allow_unreviewed=False, used=None, today=None):
    """自動版：公司圖池 → 類別圖池 → card_v4 灰框大數字。回傳 (html, layout 標籤, 選圖資訊 dict 或 None)。
    選圖資訊＝{key, kind, file}；呼叫端用 key 記使用紀錄（輪替）、kind 寫進 meta.photo_kind。"""
    c = d["card"]
    text = " ".join([c.get("title", ""), c.get("cover_title", "") if isinstance(c.get("cover_title"), str) else " ".join(c.get("cover_title") or []),
                     c.get("kicker", "")] + [x.get("name", "") for x in d.get("sources", [])])
    ph = None if c.get("no_photo") else photo_pick(c.get("subject"), d.get("meta", {}).get("topic_category") or c.get("category"), used, today, allow_unreviewed, text=text)
    if ph:
        path, meta, lay, key = ph
        return card_photo(d, idx, tot, (path, meta), slot, pending=not meta.get("reviewed")), lay, dict(key=key, kind=meta.get("kind", ""), file=str(path))
    return card_v4(d, idx, tot, None, slot), "D-無圖大數字", None
if __name__ == "__main__":
    root = Path(sys.argv[1]); slot = sys.argv[2]
    def _opt(k, dv=None): return sys.argv[sys.argv.index(k)+1] if k in sys.argv else dv
    PAL = _opt("--pal", "A"); ONLY = _opt("--only"); OUT = _opt("--out")
    from playwright.sync_api import sync_playwright as _sp
    _pw = _sp().start(); _br = _pw.chromium.launch(executable_path=os.environ.get("CHROMIUM") or None); _PG = _br.new_page(); _PG.set_content("<body></body>")
    items = json.load(open(root/f"{slot}.json", encoding="utf-8"))
    out = Path(OUT) if OUT else root/slot; bgmap = json.load(open(root/"news_bg.json", encoding="utf-8")) if (root/"news_bg.json").exists() else {}
    fn = (lambda d, i, t, b: card_v4(d, i, t, b, slot)) if PAL == "D" else (lambda d, i, t, b: card_v3(d, i, t, b, PAL, slot))
    pages = [fn(d, i, len(items), (root/bgmap[d["id"]]) if bgmap.get(d["id"]) else None) for i, d in enumerate(items, 1)]
    if ONLY: pages = [pages[int(x)-1] for x in ONLY.split(",")]
    _br.close(); _pw.stop()      # 量字寬用的瀏覽器先關掉，才能開渲染用的
    render("", pages, out)
    if len(sys.argv) > 3 and not sys.argv[3].startswith("--"): sheet(out, [f"{i}.jpg" for i in range(1, len(pages)+1)], sys.argv[3], len(pages), 400)
