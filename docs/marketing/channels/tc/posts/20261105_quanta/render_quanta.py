"""頻道二「科技透明圈」瑞士極簡版型套版範例（1080x1350）。
用法（廣達待遇文，改自 docs/tc/assets/scripts/render_samples.py）：python render_quanta.py <素材根目錄 ASSETS> <輸出目錄 OUT>
ASSETS 內要有 logos/、diagrams/、brand/icon_light.svg。字型 Noto Sans TC 由 TW_FONT_DIR（fontsource 解開的 package 目錄）提供。
色票：白底、黑 #111111、瑞士紅 #D4231A、輔助灰 #595959、細線 #CFCFCF、淡灰面 #EFEFEF。
輸出每張 PNG 之後，用 DOM 量每個文字／圖片的外框，兩兩比對重疊（程式檢查），結果印出並寫 overlap_report.json。"""
import base64, json, os, random, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ASSETS = Path(sys.argv[1]); OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
FD = Path(os.environ.get("TW_FONT_DIR", ""))
W, H = 1080, 1350
INK, RED, GREY, LINE, PALE = "#111111", "#D4231A", "#595959", "#CFCFCF", "#EFEFEF"


def b64(p):
    p = Path(p); mime = {"png": "image/png", "svg": "image/svg+xml"}[p.suffix[1:]]
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


FONTCSS = "".join(f'<link rel="stylesheet" href="file://{FD}/{w}.css">' for w in (400, 700, 900)) if FD.exists() else ""
CSS = f"""
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:{W}px;height:{H}px;font-family:'Noto Sans TC','WenQuanYi Zen Hei',sans-serif;color:{INK};background:#fff;display:flex;flex-direction:column;overflow:hidden}}
.n{{font-family:Inter,'Noto Sans TC',sans-serif;font-weight:800;font-variant-numeric:tabular-nums}}
.top{{height:128px;flex:none;padding:0 64px;display:flex;align-items:center;gap:20px;border-bottom:4px solid {INK}}}
.top .b{{font-size:38px;font-weight:900;letter-spacing:.02em}}
.top .t{{font-size:32px;font-weight:400;color:{GREY}}}
.top .p{{margin-left:auto;font-size:32px;font-weight:700}}
.body{{padding:52px 64px 0;flex:1;display:flex;flex-direction:column;min-height:0}}
.tag{{display:inline-flex;align-items:center;height:52px;padding:0 20px;font-size:32px;font-weight:700;border:2px solid {INK};white-space:nowrap}}
.tag.g{{border-color:#BDBDBD;color:{GREY}}}
.ft{{margin:auto 64px 40px;height:52px;border-top:2px solid {LINE};display:flex;align-items:flex-end;justify-content:space-between;flex:none}}
.ft span{{font-size:28px;color:{GREY};font-weight:400}}
.lab{{font-size:32px;font-weight:700;color:{GREY}}}
.ph{{border-bottom:4px solid {RED};font-weight:700;padding:0 4px;white-space:nowrap}}
.callout{{border-left:12px solid {RED};background:#F4F4F4;padding:26px 34px}}
.box{{border-top:3px solid {INK}}}
.red{{color:{RED}}}
"""


def top(label, pg):   # 統一決策：A/B/C 全系列頁首只放純文字「科技透明圈」，不放開口圈（A1 帶公司 LOGO，法遵 ② 不與開口圈組合；三系列一致才像同一頻道）
    ic = ""   # 不放開口圈
    return f'<div class="top">{ic}<div class="b">科技透明圈</div><div class="t">{label}</div><div class="p">{pg}</div></div>'


def ft(left, right="示意・範例"):
    return f'<div class="ft"><span>{left}</span><span>{right}</span></div>'


S = {}   # 檔名 -> body html

# ---------------- 範例 A：公司行情（法遵 7-3 六條）----------------
NAME = "台積電"
from PIL import Image, ImageChops
import io
def trimmed(path):
    im = Image.open(path).convert("RGB")
    bb = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255))).convert("L").point(lambda v: 255 if v > 12 else 0).getbbox()
    im = im.crop(bb); bio = io.BytesIO(); im.save(bio, "PNG")
    return "data:image/png;base64," + base64.b64encode(bio.getvalue()).decode(), im.size


# ---------------- 第 1 張封面共用規格（2026-11-04 Andy：封面需要公司照片，風格參照時事範例、附 LOGO，照片大、字維持現狀）----------------
# 上半部照片全幅寬 1080x760（top 112），下半部白底標題；左上固定「開口圈」LOGO 原色＋「科技透明圈」字標（36px）。
# 右上主題 34px、標題 72px、副標 34px、署名與頁底 24px（法遵檢查要求 ≥24px）。公司 LOGO 一律不上封面；照片裡建築本身的招牌不算我方放的 LOGO。
PHOTO_ROOT = Path(os.environ.get("TC_PHOTO_ROOT") or Path(__file__).resolve().parents[4] / "social" / "photo_lib")
# 頂列只放橫式 LOGO（開口圈＋「科技透明圈」字標，原色不改；2026-11-04 Andy：「上面應該直接放上LOGO即可 行情會寫在下方」）。
# 來源 docs/brand/tc_logo_1102/c1_開口圈/horizontal_light.png（只有 PNG、無 svg），裁掉四周白邊後內嵌；高 76px、左 60px。
def _hlogo():
    p = Path(os.environ.get("TC_HLOGO") or Path(__file__).resolve().parents[1] / "brand" / "horizontal_light.png")
    im = Image.open(p).convert("RGB"); im = im.crop((4, 4, im.width - 8, im.height - 4))   # 原檔右緣有 2px 灰線，先去掉再裁白邊
    bb = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255))).convert("L").point(lambda v: 255 if v > 6 else 0).getbbox()
    im = im.crop(bb); bio = io.BytesIO(); im.save(bio, "PNG")
    return "data:image/png;base64," + base64.b64encode(bio.getvalue()).decode(), im.size
_LU, _LS = _hlogo()
# ---- 封面版面常數（2026-11-04 Andy：LOGO 縮小靠左、拿掉圖上備註、排版整齊；A1／B1／C1 與時事範例 01～04 共用同一組數值）----
M_L = 60                      # 左右邊界：LOGO、紅短線、標題、副標、「往右滑」右緣（W-60）同一條線
BAR_H = 14                    # 頂紅條
LOGO_X = 24                   # LOGO 左緣（淡藍底塊左緣距畫布左緣；只管 LOGO，其餘仍用 M_L）
LOGO_H = 48                   # 橫式 LOGO 高度（原 76）
LOGO_PAD = 20                 # LOGO 上方（紅條下緣到 LOGO）與下方（LOGO 到照片）留白相等
LOGO_TOP = BAR_H + LOGO_PAD   # 34
PIC_TOP = LOGO_TOP + LOGO_H + LOGO_PAD   # 102：照片上緣（頂列總高 = 紅條 + 88）
GAP = 56                      # 照片到紅短線、副標到頁底，兩段留白相等
RL_H, RL_GAP, TT_H, SUB_GAP, SUB_H = 6, 24, 212, 0, 0   # 紅短線高、紅線到標題、標題兩行高（72px／106 行高，兩行分開的 div 字框不互疊）；廣達這篇沒有副標列（Andy 11-05：「下方只需要表示廣達行情」），提示併入標題第二行右側
BELOW = GAP + RL_H + RL_GAP + TT_H + SUB_GAP + SUB_H + GAP   # 照片以下總高 386
PIC_H = H - PIC_TOP - BELOW   # 862：拿掉備註後的空間全部給照片
RL_TOP = PIC_TOP + PIC_H + GAP
TT_TOP = RL_TOP + RL_H + RL_GAP
SUB_TOP = TT_TOP + TT_H + SUB_GAP
LOGO_W = round(LOGO_H * _LS[0] / _LS[1])
OPEN_RING = f'<img data-b src="{_LU}" width="{LOGO_W}" height="{LOGO_H}" style="display:block">'
COVER_CSS = f"""
.cv{{position:absolute;left:0;top:0;width:{W}px;height:{H}px;background:#fff}}
.cv .bar{{position:absolute;left:0;top:0;width:{W}px;height:{BAR_H}px;background:{RED}}}
.cv .lg{{position:absolute;left:{LOGO_X}px;top:{LOGO_TOP}px;height:{LOGO_H}px}}
.cv .pic{{position:absolute;left:0;top:{PIC_TOP}px;width:{W}px;height:{PIC_H}px;background-color:{PALE};background-size:cover;background-repeat:no-repeat}}
.cv .rl{{position:absolute;left:{M_L}px;top:{RL_TOP}px;width:120px;height:{RL_H}px;background:{RED}}}
.cv .tt{{position:absolute;left:{M_L}px;top:{TT_TOP}px;width:{W-2*M_L}px;height:{TT_H}px;font-size:72px;font-weight:700;line-height:90px;color:{INK}}}
.cv .row{{position:absolute;left:{M_L}px;top:{SUB_TOP}px;width:{W-2*M_L}px;height:{SUB_H}px;display:flex;justify-content:space-between;align-items:baseline;font-size:34px;line-height:{SUB_H}px;white-space:nowrap}}
.cv .sub{{color:{GREY}}}
.cv .hint{{font-weight:700;color:{RED}}}
.cv .ph{{border-bottom:0;color:{RED};padding:0}}
"""


def photo_uri(rel, box=None):
    im = Image.open(PHOTO_ROOT / rel).convert("RGB")
    if box: im = im.crop(box)
    bio = io.BytesIO(); im.save(bio, "JPEG", quality=92)
    return "data:image/jpeg;base64," + base64.b64encode(bio.getvalue()).decode()


def cover(title, sub, hint, photo, pos="50% 50%"):
    """封面不放任何署名／免責／商標句（Andy 11-04：下方備註不用，文案備註就好）；署名與免責寫進貼文文案，範本句見 README。"""
    return (f'<div class="cv"><div class="bar"></div><div class="lg">{OPEN_RING}</div>'
            f'<div class="pic" data-b style="background-image:url({photo});background-position:{pos}"></div>'
            f'<div class="rl"></div><div class="tt">{title}</div><div class="row"><div class="sub">{sub}</div><div class="hint">{hint}</div></div></div>')


PH = lambda t: f'<span class="ph">{t}</span>'
DISC = "網友回報，非公司公告・與各公司無合作或授權關係"

# ================= 廣達待遇文（2 頁）：A1 封面＋A2 待遇欄位表 =================
NAME = "廣達"
S = {}
# 2026-11-05 Andy：「下方只需要表示廣達行情 並且嘗試有點偷偷說的感覺標題」→ 兩行標題、第二行瑞士紅，提示與第二行基線對齊靠右；不放副標、不放表情符號
S["1_cover"] = (f'<div class="cv"><div class="bar"></div><div class="lg">{OPEN_RING}</div>'
    f'<div class="pic" data-b style="background-image:url({photo_uri("quanta/photo_12.jpg", (0, 130, 1920, 1440))});background-position:10% 50%"></div>'
    f'<div class="rl"></div><div class="tt" style="line-height:106px"><div>噓，偷偷跟你說</div>'
    f'<div style="display:flex;justify-content:space-between;align-items:baseline"><span style="color:{RED};font-weight:900">{NAME}行情</span>'
    f'<span class="hint" style="font-size:34px;line-height:44px;white-space:nowrap">往右滑看行情 →</span></div></div></div>')
rows = [
    ("總部地點", "桃園龜山", "網友提到的地點另有林口、桃園"),
    ("碩畢月薪", "約 58～69K・中位約 62K", "業內朋友 1 位＋網友 21 筆（2025～2026）對得上<br>網友樣本多未標學歷"),
    ("年終・分紅", "整包約 18～22 個月", "含底薪年度總額；網友 17 筆，隨單位差很多"),
    ("升等路徑", "依單位而異", "網友回報近年較難升；調薪幅度各單位不同"),
    ("加班時數", "網友多回報經常加班", "網友 171 筆（不限職位）58% 選「經常」<br>週工時中位約 48 小時"),
    ("繁忙程度", "網友普遍回報工時長、壓力大", "隨單位與專案差很多"),
    ("出差頻率", "時間不定，依客戶與專案", "網友樣本多數未提；少數評價提到赴中國、東南亞廠"),
]
trs = "".join(f'<div class="rw" style="display:flex;align-items:center;flex:1;border-top:2px solid {LINE}">'
              f'<div class="n" style="width:74px;font-size:32px;color:{RED}">{i+1:02d}</div>'
              f'<div style="width:226px;font-size:38px;font-weight:800;white-space:nowrap">{a}</div>'
              f'<div style="flex:1;min-width:0"><div style="font-size:36px;font-weight:700;line-height:54px;white-space:nowrap">{b}</div>'
              f'<div style="font-size:26px;line-height:34px;color:{GREY};margin-top:2px">{c}</div></div></div>' for i, (a, b, c) in enumerate(rows))
S["2_fields"] = f"""{top('公司行情', '2 / 2')}
<div class="body" style="padding-top:40px">
  <div style="display:flex;gap:14px"><span class="tag">{NAME}</span><span class="tag g">代號：肉鬆</span></div>
  <div style="font-size:68px;font-weight:900;line-height:1.2;margin-top:20px">七個欄位，一次看完</div>
  <div class="box" style="margin-top:24px;flex:1;display:flex;flex-direction:column;min-height:0">{trs}</div>
</div>{ft(DISC, "")}"""

# ---------------- 轉圖 + 重疊檢查 ----------------
JS = """() => {
 const out=[]; const els=[...document.querySelectorAll('body *')];
 const rects=[];
 for (const e of els) {
   if (e.tagName==='IMG'||e.tagName==='svg'||e.hasAttribute('data-b')) { const r=e.getBoundingClientRect(); if(r.width>0) rects.push({k:(e.tagName+(e.className&&e.className.baseVal===undefined?'.'+e.className:'')),r:[r.left,r.top,r.right,r.bottom],e}); continue; }
   for (const n of e.childNodes) if (n.nodeType===3 && n.textContent.trim()) { const g=document.createRange(); g.selectNodeContents(n); for (const r of g.getClientRects()) if(r.width>1) rects.push({k:'txt:'+n.textContent.trim().slice(0,12),r:[r.left,r.top,r.right,r.bottom],e}); }
 }
 const bad=[];
 for (let i=0;i<rects.length;i++) for (let j=i+1;j<rects.length;j++) {
   const a=rects[i], b=rects[j]; if (a.e===b.e) continue; if (a.e.contains(b.e)||b.e.contains(a.e)) continue;
   if (a.e.closest('svg') && b.e.closest('svg') && a.e.closest('svg')===b.e.closest('svg')) continue;
   const ox=Math.min(a.r[2],b.r[2])-Math.max(a.r[0],b.r[0]), oy=Math.min(a.r[3],b.r[3])-Math.max(a.r[1],b.r[1]);
   if (ox>2 && oy>2) bad.push([a.k,b.k,Math.round(ox),Math.round(oy)]);
 }
 const oob=rects.filter(x=>x.r[0]<-1||x.r[2]>1081||x.r[3]>1351||x.r[1]<-1).map(x=>x.k);
 const body=document.body; const ovf = body.scrollHeight>1350+1 || body.scrollWidth>1081;
 const small=[...document.querySelectorAll('body *')].filter(e=>[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())&&parseFloat(getComputedStyle(e).fontSize)<24).map(e=>e.textContent.trim().slice(0,10));
 const clip=[...document.querySelectorAll('body *')].filter(e=>e.scrollWidth>e.clientWidth+1&&getComputedStyle(e).overflow!=='visible'||(e.classList.contains('rw')&&e.scrollHeight>e.clientHeight+1)).map(e=>e.textContent.trim().slice(0,10));
 const wide=[...document.querySelectorAll('.rw div div')].filter(e=>e.getBoundingClientRect().right>1020+1).map(e=>e.textContent.slice(0,10));
 return {bad,oob,ovf,small,clip,wide,n:rects.length};
}"""

report = {}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    for name, html in S.items():
        doc = f'<!doctype html><html><head><meta charset="utf-8">{FONTCSS}<style>{CSS}{COVER_CSS}</style></head><body>{html}</body></html>'
        f = OUT / f"_{name}.html"; f.write_text(doc, encoding="utf8")
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        pg.goto(f"file://{f}", wait_until="networkidle"); pg.wait_for_timeout(600)
        pg.evaluate("document.fonts.ready")
        res = pg.evaluate(JS)
        pg.screenshot(path=str(OUT / f"{name}.png"))
        pg.close(); f.unlink()
        report[name] = res
        print(name, "重疊", len(res["bad"]), "出界", len(res["oob"]), "溢出", res["ovf"], "小字(<24px)", res["small"], "截切", res["clip"], "超右界", res["wide"], res["bad"][:3])
    b.close()
json.dump(report, open(OUT / "overlap_report.json", "w"), ensure_ascii=False, indent=1)
tot = sum(len(v["bad"]) + len(v["oob"]) + int(v["ovf"]) + len(v["clip"]) + len(v["wide"]) + len(v["small"]) for v in report.values())
print(f"重疊檢查：程式 {len(report)} 張 {tot} 筆")
