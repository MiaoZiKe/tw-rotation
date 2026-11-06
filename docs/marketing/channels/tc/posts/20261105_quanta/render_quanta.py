"""頻道二「科技透明圈」糖果陽光（收斂版）套版範例（1080x1350）。
用法（廣達待遇文，改自 docs/tc/assets/scripts/render_samples.py）：python render_quanta.py <素材根目錄 ASSETS> <輸出目錄 OUT>
ASSETS 內要有 logos/、diagrams/、brand/icon_light.svg。字型 Noto Sans TC 由 TW_FONT_DIR（fontsource 解開的 package 目錄）提供。
色票（2026-11-06 Andy：跟頭貼一樣、類似糖果陽光風，但不用那麼甜）：頁底 #F4F7FB、卡片白、深藍黑 #0F1B33、LOGO 藍 #1F6FEB、LOGO 橘 #FF9F1C、淡藍 #E8F0FD、輔助灰 #55627A、細線 #DCE4F0。
輸出每張 PNG 之後，用 DOM 量每個文字／圖片的外框，兩兩比對重疊（程式檢查），結果印出並寫 overlap_report.json。"""
import base64, json, os, random, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ASSETS = Path(sys.argv[1]); OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
FD = Path(os.environ.get("TW_FONT_DIR", ""))
W, H = 1080, 1350
INK, BLUE, ORG, GREY, LINE, PALE = "#0F1B33", "#1F6FEB", "#FF9F1C", "#55627A", "#DCE4F0", "#E8EEF7"
BG, TINT = "#F4F7FB", "#E8F0FD"   # 頁底很淡的藍灰；淡藍（標籤、提示塊）
SHADOW = "0 6px 18px rgba(31,111,235,.08)"   # 柔和陰影（藍色低透明度）
RAD = 20   # 卡片圓角；標籤／小塊用 14


def b64(p):
    p = Path(p); mime = {"png": "image/png", "svg": "image/svg+xml"}[p.suffix[1:]]
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


FONTCSS = "".join(f'<link rel="stylesheet" href="file://{FD}/{w}.css">' for w in (400, 700, 900)) if FD.exists() else ""
CSS = f"""
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:{W}px;height:{H}px;font-family:'Noto Sans TC','WenQuanYi Zen Hei',sans-serif;color:{INK};background:{BG};display:flex;flex-direction:column;overflow:hidden}}
.n{{font-family:Inter,'Noto Sans TC',sans-serif;font-weight:800;font-variant-numeric:tabular-nums}}
.strip{{position:absolute;left:0;top:0;width:{W}px;height:14px;background:{BLUE}}}
.strip i{{position:absolute;right:0;top:0;width:170px;height:14px;background:{ORG}}}
.top{{height:128px;flex:none;padding:14px 48px 0;display:flex;align-items:center;gap:20px;background:#fff;border-bottom:2px solid {LINE}}}
.top .b{{font-size:38px;font-weight:900;letter-spacing:.02em}}
.top .t{{font-size:32px;font-weight:400;color:{GREY}}}
.top .p{{margin-left:auto;font-size:30px;font-weight:700;color:{BLUE};background:{TINT};padding:6px 20px;border-radius:14px}}
.body{{padding:52px 48px 0;flex:1;display:flex;flex-direction:column;min-height:0}}
.tag{{display:inline-flex;align-items:center;height:52px;padding:0 22px;font-size:32px;font-weight:700;background:{TINT};color:{BLUE};border-radius:14px;white-space:nowrap}}
.tag.g{{background:#fff;border:2px solid {LINE};color:{GREY}}}
.ft{{margin:auto 48px 40px;height:52px;border-top:2px solid {LINE};display:flex;align-items:flex-end;justify-content:space-between;flex:none}}
.ft span{{font-size:28px;color:{GREY};font-weight:400}}
.lab{{font-size:32px;font-weight:700;color:{GREY}}}
.ph{{border-bottom:4px solid {ORG};font-weight:700;padding:0 4px;white-space:nowrap}}
.card{{background:#fff;border:2px solid {LINE};border-radius:{RAD}px;box-shadow:{SHADOW}}}
.callout{{background:{TINT};border-radius:18px;padding:26px 34px}}
.box{{background:#fff;border:2px solid {LINE};border-radius:{RAD}px;box-shadow:{SHADOW};padding:0 24px}}
.box>div:first-child{{border-top:0 !important}}
.red{{color:{BLUE}}}
"""


def top(label, pg):   # 統一決策：A/B/C 全系列頁首只放純文字「科技透明圈」，不放開口圈（A1 帶公司 LOGO，法遵 ② 不與開口圈組合；三系列一致才像同一頻道）
    return f'<div class="strip"><i></i></div><div class="top"><div class="b">科技透明圈</div><div class="t">{label}</div><div class="p">{pg}</div></div>'


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
BAR_H = 14                    # 頂色條（藍底、右端橘塊 170px）
PX = 24                       # 照片左右內縮（與 LOGO 左緣同線）、圓角 20
LOGO_X = 24                   # LOGO 左緣（淡藍底塊左緣距畫布左緣；只管 LOGO，其餘仍用 M_L）
LOGO_H = 48                   # 橫式 LOGO 高度（原 76）
LOGO_PAD = 20                 # LOGO 上方（紅條下緣到 LOGO）與下方（LOGO 到照片）留白相等
LOGO_TOP = BAR_H + LOGO_PAD   # 34
PIC_TOP = LOGO_TOP + LOGO_H + LOGO_PAD   # 102：照片上緣（頂列總高 = 紅條 + 88）
GAP = 56                      # 照片到紅短線、副標到頁底，兩段留白相等
RL_H, RL_GAP, TT_H, SUB_GAP, SUB_H = 8, 40, 248, 0, 0   # 紅短線高、紅線到標題、標題兩行高（72px／106 行高，兩行分開的 div 字框不互疊）；廣達這篇沒有副標列（Andy 11-05：「下方只需要表示廣達行情」），提示併入標題第二行右側
PIC_H = 690                   # 2026-11-06 Andy 提供廣達總部照（640x427）：照片框 1032x690（比例同原圖 1.5），放大約 1.6 倍，避免糊；多出的高度給標題區
BELOW = H - PIC_TOP - PIC_H
GAP = (BELOW - RL_H - RL_GAP - TT_H - SUB_GAP - SUB_H) // 2   # 照片到紅線、標題到頁底兩段留白相等
RL_TOP = PIC_TOP + PIC_H + GAP
TT_TOP = RL_TOP + RL_H + RL_GAP
SUB_TOP = TT_TOP + TT_H + SUB_GAP
LOGO_W = round(LOGO_H * _LS[0] / _LS[1])
OPEN_RING = f'<img data-b src="{_LU}" width="{LOGO_W}" height="{LOGO_H}" style="display:block">'
COVER_CSS = f"""
.cv{{position:absolute;left:0;top:0;width:{W}px;height:{H}px;background:{BG}}}
.cv .hd{{position:absolute;left:0;top:0;width:{W}px;height:{PIC_TOP}px;background:#fff}}
.cv .lg{{position:absolute;left:{LOGO_X}px;top:{LOGO_TOP}px;height:{LOGO_H}px}}
.cv .pic{{position:absolute;left:{PX}px;top:{PIC_TOP}px;width:{W-2*PX}px;height:{PIC_H}px;border-radius:{RAD}px;box-shadow:{SHADOW};background-color:{PALE};background-size:cover;background-repeat:no-repeat}}
.cv .rl{{position:absolute;left:{M_L}px;top:{RL_TOP}px;width:120px;height:{RL_H}px}}
.cv .rl b{{position:absolute;left:0;top:0;width:88px;height:{RL_H}px;border-radius:4px;background:{BLUE}}}
.cv .rl i{{position:absolute;left:100px;top:0;width:20px;height:{RL_H}px;border-radius:4px;background:{ORG}}}
.cv .tt{{position:absolute;left:{M_L}px;top:{TT_TOP}px;width:{W-2*M_L}px;height:{TT_H}px;font-size:84px;font-weight:700;line-height:90px;color:{INK}}}
.cv .row{{position:absolute;left:{M_L}px;top:{SUB_TOP}px;width:{W-2*M_L}px;height:{SUB_H}px;display:flex;justify-content:space-between;align-items:baseline;font-size:34px;line-height:{SUB_H}px;white-space:nowrap}}
.cv .sub{{color:{GREY}}}
.cv .hint{{font-weight:700;color:{BLUE}}}
.cv .ph{{border-bottom:0;color:{BLUE};padding:0}}
"""


def photo_uri(rel, box=None):
    im = Image.open(PHOTO_ROOT / rel).convert("RGB")
    if box: im = im.crop(box)
    bio = io.BytesIO(); im.save(bio, "JPEG", quality=92)
    return "data:image/jpeg;base64," + base64.b64encode(bio.getvalue()).decode()


def photo_uri_abs(p):
    return 'data:image/jpeg;base64,' + base64.b64encode(Path(p).read_bytes()).decode()


def cover(title, sub, hint, photo, pos="50% 50%"):
    """封面不放任何署名／免責／商標句（Andy 11-04：下方備註不用，文案備註就好）；署名與免責寫進貼文文案，範本句見 README。"""
    return (f'<div class="cv"><div class="hd"></div><div class="strip"><i></i></div><div class="lg">{OPEN_RING}</div>'
            f'<div class="pic" data-b style="background-image:url({photo});background-position:{pos}"></div>'
            f'<div class="rl"><b></b><i></i></div><div class="tt">{title}</div><div class="row"><div class="sub">{sub}</div><div class="hint">{hint}</div></div></div>')


PH = lambda t: f'<span class="ph">{t}</span>'
DISC = "網友回報，非公司公告・與各公司無合作或授權關係"

# ================= 廣達待遇文（2 頁）：A1 封面＋A2 台灣地圖＋待遇表 =================
NAME = "廣達"
TITLE_FMT = "{公司}透明說"            # 封面第一行大標（公司名＋透明說）
HINT = os.environ.get("TC_HINT") or "大人才知道的那些事"   # 封面第二行（隱晦、不直白；Andy 還會從候選挑，7～10 字單行；法遵：不得出現內部／爆料／內幕／獨家／祕密）
COVER_HINT = "右滑看透明圈"
SECTION_TITLE = "工程師待遇"          # 欄位標題；若文章是特定單位，寫成「廣達 BU9 透明圈」
HQ_LABEL = "總部：桃園龜山"
S = {}
TW = json.load(open(Path(__file__).resolve().parent / "taiwan_path.json"))   # taiwan-atlas（MIT；內政部國土測繪中心縣市界線，政府資料開放授權條款第1版）→ make_taiwan_path.mjs

# ---- 封面：兩行標題在照片下方區塊垂直置中、靠左；「右滑看透明圈」輕量小標籤獨立貼右下角 ----
TT_PX, HT_PX = 108, 60
# 提示：白底細藍框圓角小標籤＋右側三個由淡到深的箭頭（›››，自繪 SVG，非文字箭頭）
SWIPE = (f'<div class="sw"><span>{COVER_HINT}</span>'
         f'<svg data-b width="64" height="36" viewBox="0 0 64 36" fill="none" stroke-linecap="round" stroke-linejoin="round" stroke-width="6">'
         f'<path d="M6 6 L18 18 L6 30" stroke="{BLUE}" stroke-opacity=".3"/><path d="M26 6 L38 18 L26 30" stroke="{BLUE}" stroke-opacity=".6"/>'
         f'<path d="M46 6 L58 18 L46 30" stroke="{BLUE}"/></svg></div>')
SW_R, SW_B, SW_H = M_L, 40, 72      # 小標籤右緣與標題左緣同邊距 60、底距 40、高 72
LOW_TOP = PIC_TOP + PIC_H
SWIPE_CSS = f"""
.cv .low{{position:absolute;left:{M_L}px;top:{LOW_TOP}px;width:{W-2*M_L}px;height:{H-LOW_TOP-SW_B-SW_H-16}px;display:flex;flex-direction:column;justify-content:center}}
.cv .nm{{font-size:{TT_PX}px;font-weight:900;line-height:132px;color:{BLUE};white-space:nowrap}}
.cv .tg{{font-size:{HT_PX}px;font-weight:700;line-height:80px;margin-top:16px;color:{INK};white-space:nowrap}}
.cv .sw{{position:absolute;right:{SW_R}px;bottom:{SW_B}px;height:{SW_H}px;display:flex;align-items:center;gap:14px;padding:0 24px 0 28px;border-radius:{SW_H//2}px;background:#fff;border:3px solid {BLUE};color:{BLUE};font-size:32px;font-weight:700;white-space:nowrap}}
.cv .sw svg{{display:block}}
.cv .co{{font-size:44px;font-weight:700;line-height:60px;margin-top:12px;color:{BLUE};white-space:nowrap}}
"""
# ---- 「透明」二字特效（2026-11-06 第三輪 Andy：「透明 就需要點特效在文字上 廣達兩字可能不用」）----
# TITLE_FX：空＝一般實心；A 鏤空透視（藍描邊、字內透出封面照片）、B 玻璃質感（35% 淡藍＋白內高光＋細描邊）、
# C 淡出掃光（左 100%→右 25% 藍＋斜白光帶）、D 只寫「透明說」（透明用 A 款），公司名放副標之後。
TITLE_FX = os.environ.get("TITLE_FX", "").upper()
_ph = "data:image/jpeg;base64," + base64.b64encode((Path(__file__).resolve().parent / "cover_photo.jpg").read_bytes()).decode()
# 用 SVG 畫「透明」二字：描邊改用濾鏡（字形外擴 N px 再扣掉字形本身＝只留外環），避免可變字型的重疊輪廓在字內畫出多餘的線。
FX_W, FX_H, FX_PAD, FX_BASE = 108 * 2 + 12, 132, 6, 111   # svg 寬（兩字＋左右各 6px 給外環）、高、左右內距、字基線 y


def fx_svg(kind):
    ring = {"A": (3.5, BLUE, 1), "D": (3.5, BLUE, 1), "B": (2.5, BLUE, 1), "C": (2, BLUE, .5)}[kind]
    t = lambda extra: (f'<text x="{FX_PAD}" y="{FX_BASE}" font-size="108" font-weight="700" font-family="Noto Sans TC" {extra}>透明</text>')
    defs = (f'<filter id="rg" x="-10%" y="-10%" width="120%" height="120%"><feMorphology in="SourceAlpha" operator="dilate" radius="{ring[0]}" result="d"/>'
            f'<feComposite in="d" in2="SourceAlpha" operator="out" result="r"/><feFlood flood-color="{ring[1]}" flood-opacity="{ring[2]}"/><feComposite in2="r" operator="in"/></filter>')
    if kind in ("A", "D"):
        defs += (f'<pattern id="ph" patternUnits="userSpaceOnUse" x="0" y="0" width="{FX_W}" height="{FX_H}"><rect width="{FX_W}" height="{FX_H}" fill="#fff"/>'
                 f'<image href="{_ph}" x="-110" y="-26" width="640" height="427" preserveAspectRatio="none"/></pattern>')
        body = t('fill="url(#ph)"') + t('fill="#000" filter="url(#rg)"')
    elif kind == "B":
        defs += (f'<linearGradient id="hl" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".95"/><stop offset=".4" stop-color="#fff" stop-opacity=".5"/><stop offset=".55" stop-color="#fff" stop-opacity="0"/></linearGradient>'
                 f'<filter id="sh" x="-10%" y="-10%" width="120%" height="130%"><feGaussianBlur in="SourceAlpha" stdDeviation="6"/><feOffset dy="6"/><feFlood flood-color="{BLUE}" flood-opacity=".28"/><feComposite in2="SourceAlpha" operator="in" result="x"/></filter>')
        body = t(f'fill="{BLUE}" fill-opacity=".35"') + t('fill="url(#hl)"') + t('fill="#000" filter="url(#rg)"')
    else:
        defs += (f'<linearGradient id="fd" gradientUnits="userSpaceOnUse" x1="{FX_PAD}" y1="0" x2="{FX_W-FX_PAD}" y2="0"><stop offset="0" stop-color="{BLUE}" stop-opacity="1"/><stop offset="1" stop-color="{BLUE}" stop-opacity=".25"/></linearGradient>'
                 f'<linearGradient id="bd" gradientUnits="userSpaceOnUse" x1="70" y1="20" x2="120" y2="110"><stop offset=".34" stop-color="#fff" stop-opacity="0"/><stop offset=".45" stop-color="#fff" stop-opacity=".95"/><stop offset=".55" stop-color="#fff" stop-opacity="0"/></linearGradient>')
        body = t('fill="url(#fd)"') + t('fill="url(#bd)"') + t('fill="#000" filter="url(#rg)"')
    return f'<svg data-b width="{FX_W}" height="{FX_H}" viewBox="0 0 {FX_W} {FX_H}" style="display:block;flex:none"><defs>{defs}</defs>{body}</svg>'


if TITLE_FX == "D":
    TITLE_HTML = f'<div class="nm" style="display:flex">{fx_svg("D")}<span>說</span></div>'
    EXTRA = f'<div class="co">{NAME}</div>'
elif TITLE_FX:
    TITLE_HTML = f'<div class="nm" style="display:flex"><span>{NAME}</span>{fx_svg(TITLE_FX)}<span>說</span></div>'; EXTRA = ""
else:
    TITLE_HTML = f'<div class="nm">{TITLE_FMT.format(公司=NAME)}</div>'; EXTRA = ""
S["1_cover"] = (f'<div class="cv"><div class="hd"></div><div class="strip"><i></i></div><div class="lg">{OPEN_RING}</div>'
    f'<div class="pic" data-b style="background-image:url({photo_uri_abs(Path(__file__).resolve().parent / "cover_photo.jpg")});background-position:50% 50%"></div>'
    f'<div class="low">{TITLE_HTML}<div class="tg">{HINT}</div>{EXTRA}</div>{SWIPE}</div>')

# ---- 待遇表：上半台灣地圖＋總部位置，下半「工程師待遇」6 欄（欄名＋重點值，不放備註） ----
rows = [
    ("碩畢月薪", "約 58～69K・中位約 62K"),
    ("年終・分紅", "整包約 18～22 個月"),
    ("升等路徑", "依單位而異"),
    ("加班時數", "網友多回報經常加班"),
    ("繁忙程度", "網友普遍回報工時長、壓力大"),
    ("出差頻率", "時間不定，依客戶與專案"),
]
trs = "".join(f'<div class="rw" style="display:flex;align-items:center;flex:1;border-top:2px solid {LINE}">'
              f'<div class="n" style="width:66px;font-size:32px;color:{BLUE}">{i+1:02d}</div>'
              f'<div style="width:220px;font-size:38px;font-weight:800;white-space:nowrap">{a}</div>'
              f'<div style="flex:1;min-width:0;font-size:36px;font-weight:700;white-space:nowrap">{b}</div></div>' for i, (a, b) in enumerate(rows))
MAP_W, MAP_H = 980, 496           # 地圖 svg 尺寸（卡片 984x500 扣 2px 邊框；body 左右各 48）
IS_H = 448                        # 台灣（含澎湖）高度，寬依比例
IS_W = IS_H * TW["w"] / TW["h"]
IS_X, IS_Y = (MAP_W - IS_W) / 2, (MAP_H - IS_H) / 2   # 本島左上角（置中）
k = IS_H / TW["h"]
PX_, PY_ = IS_X + TW["pt"][0] * k, IS_Y + TW["pt"][1] * k   # 龜山點位
LBL_W, LBL_H = 380, 76
LBL_X, LBL_Y = 70, PY_ - LBL_H / 2
MAP_SVG = (f'<svg data-b width="{MAP_W}" height="{MAP_H}" viewBox="0 0 {MAP_W} {MAP_H}" style="display:block">'
    f'<g transform="translate({IS_X:.1f} {IS_Y:.1f}) scale({k:.5f})"><path d="{TW["land"]}" fill="#D3E2FA" stroke="#fff" stroke-width="{3/k:.1f}" stroke-linejoin="round"/>'
    f'<path d="{TW["borders"]}" fill="none" stroke="#A9C3EC" stroke-width="{1.6/k:.1f}" stroke-linejoin="round" stroke-linecap="round"/></g>'
    f'<line x1="{LBL_X+LBL_W}" y1="{PY_:.1f}" x2="{PX_-30:.1f}" y2="{PY_:.1f}" stroke="{BLUE}" stroke-width="3" stroke-dasharray="2 8" stroke-linecap="round"/>'
    f'<circle cx="{PX_:.1f}" cy="{PY_:.1f}" r="30" fill="#fff" fill-opacity=".7" stroke="{BLUE}" stroke-width="8"/>'
    f'<circle cx="{PX_+19:.1f}" cy="{PY_-19:.1f}" r="13" fill="{ORG}" stroke="#fff" stroke-width="4"/>'
    f'<rect x="{LBL_X}" y="{LBL_Y:.1f}" width="{LBL_W}" height="{LBL_H}" rx="38" fill="#fff" stroke="{LINE}" stroke-width="2"/>'
    f'<text x="{LBL_X+LBL_W/2}" y="{LBL_Y+LBL_H/2+1:.1f}" text-anchor="middle" dominant-baseline="central" font-size="40" font-weight="800" fill="{INK}" font-family="Noto Sans TC">{HQ_LABEL}</text></svg>')
S["2_fields"] = f"""{top('公司行情', '2 / 2')}
<div class="body" style="padding-top:28px">
  <div style="display:flex;gap:14px"><span class="tag">{NAME}</span><span class="tag g">代號：肉鬆</span></div>
  <div class="card" style="margin-top:20px;height:{MAP_H+4}px;background:{TINT};border-color:#CFE0FA;overflow:hidden;flex:none">{MAP_SVG}</div>
  <div style="font-size:58px;font-weight:900;line-height:80px;margin-top:20px;flex:none">{SECTION_TITLE}</div>
  <div class="box" style="margin-top:8px;margin-bottom:36px;flex:1;display:flex;flex-direction:column;min-height:0">{trs}</div>
</div>"""

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
 return {bad,oob,ovf,small,clip,wide,n:rects.length,clipdbg:[...document.querySelectorAll('body *')].filter(e=>e.scrollWidth>e.clientWidth+1&&getComputedStyle(e).overflow!=='visible').map(e=>[e.tagName,e.scrollWidth,e.clientWidth])};
}"""

if os.environ.get("TITLE_R"):   # 2026-11-06 第二輪：公司名開口環＋透明說橘色（title_r.py）
    import title_r; title_r.main(globals()); sys.exit(0)
if os.environ.get("TITLE_STYLE"):   # 2026-11-06 標題字五款排版（title_styles.py），只產 title_N.png，不動 1_cover
    import title_styles; title_styles.main(globals()); sys.exit(0)
if TITLE_FX: S = {f'cover_{TITLE_FX}': S['1_cover']}
report = {}
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    for name, html in S.items():
        doc = f'<!doctype html><html><head><meta charset="utf-8">{FONTCSS}<style>{CSS}{COVER_CSS}{SWIPE_CSS}</style></head><body>{html}</body></html>'
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
json.dump(report, open(OUT / (f"overlap_report_{TITLE_FX}.json" if TITLE_FX else "overlap_report.json"), "w"), ensure_ascii=False, indent=1)
tot = sum(len(v["bad"]) + len(v["oob"]) + int(v["ovf"]) + len(v["clip"]) + len(v["wide"]) + len(v["small"]) for v in report.values())
print(f"重疊檢查：程式 {len(report)} 張 {tot} 筆")
