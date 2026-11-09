"""廣達封面標題字五款排版（2026-11-06 Andy：「廣達透明說 特效有夠爛 跟PPT一樣 請專人設計 不同風格」）。
用法：TITLE_STYLE=1..5 python render_quanta.py <ASSETS> <OUT>（由 render_quanta.py 呼叫 main(globals())）。
只用排版（字重、字體、網格、色塊、層次）表達「透明」：不描邊加填色、不漸層、不外發光、不立體陰影。
字型：Noto Sans TC 可變字型（OFL，wght 100～900，TITLE_SANS 指到 .ttf）、Noto Serif TC 可變字型（OFL，@fontsource-variable/noto-serif-tc，TITLE_SERIF_DIR 指到解開的 package 目錄）。
重疊檢查採「墨跡外框」：每個元素單獨顯示、用像素量出真實字形範圍，兩兩比對；另外檢查任何東西不得蓋住照片裡的 Quanta 立體字。"""
import io, json, os
from pathlib import Path
from PIL import Image

STYLES = {
    1: "編輯雜誌風",
    2: "瑞士網格風",
    3: "照片疊字風",
    4: "毛玻璃面板風",
    5: "極簡字重對比風",
}
REASON = {
    1: "襯線粗體像雜誌刊頭，標題從白色缺角探進照片下緣，一條細線加藍橘小塊把副標隔成「欄」；透明感來自留白與層次，不靠特效。",
    2: "五個字拆成五格方塊：「廣達」實心深色、「透明」淡藍底淺色格（像一片玻璃）、「說」橘色收尾；用格線與色塊切割把透明做成結構。",
    3: "照片截短，兩行大字從照片下緣往外長：「廣達」上半白字壓在階梯上、下半深色落到底色，同一個字被照片邊界切成兩種顏色；「透明說」整行藍字。",
    4: "毛玻璃面板橫跨照片下緣，面板裡的照片真的被模糊透出來；字是乾淨的深色，透明由面板這個元件承擔，字本身不加任何效果。",
    5: "字重對比：「廣達」900 極粗當實心的公司，「透明說」100 極細像一層薄膜；大量留白，副標靠右對齊「廣達」基線。",
}
SUB = "茶水間常聊的那些"
TITLE = "廣達透明說"
SANS = os.environ.get("TITLE_SANS", "")   # Noto Sans TC 可變字型 .ttf；沒設就用 TW_FONT_DIR 的 fontsource css
SERIF = Path(os.environ.get("TITLE_SERIF_DIR", "/nonexistent"))   # Noto Serif TC 可變字型套件（只有舊版試作用到，定稿版不需要）


def font_css():
    """有可變字型就定義 TCS（100～900）；沒有就退回 TW_FONT_DIR 的 fontsource css（Noto Sans TC 400／700／900），讓樣本腳本在別的環境也能跑。"""
    if SANS and Path(SANS).is_file():
        css = f"@font-face{{font-family:'TCS';font-weight:100 900;src:url('file://{SANS}')}}"
    else:
        FD = os.environ.get("TW_FONT_DIR", "")
        css = "".join(f'@import url("file://{FD}/{w}.css");' for w in (400, 700, 900)) if FD else ""
    if (SERIF / "wght.css").exists():
        css += (SERIF / "wght.css").read_text(encoding="utf8").replace("url(./files/", f"url(file://{SERIF}/files/")
    return css


def build(n, g):
    BG, INK, BLUE, ORG, GREY, LINE, TINT = (g[k] for k in ("BG", "INK", "BLUE", "ORG", "GREY", "LINE", "TINT"))
    PIC_TOP, PIC_H, PX, W = g["PIC_TOP"], g["PIC_H"], g["PX"], g["W"]
    photo = g["photo_uri_abs"](Path(g["__file__"]).resolve().parent / "cover_photo.jpg")
    PB = PIC_TOP + PIC_H                       # 792：照片下緣
    SERIFF = "'Noto Serif TC Variable','Noto Serif TC',serif"
    base_hd = f'<div class="hd"></div><div class="strip"><i></i></div><div class="lg">{g["OPEN_RING"]}</div>'
    pic_h = PIC_H
    allow = set()                              # 允許相交的元素對（刻意疊圖）
    css = ""
    body = ""
    if n == 1:
        css = f"""
.tab{{position:absolute;left:{PX}px;top:{PB-80}px;width:996px;height:200px;background:{BG};border-top-right-radius:48px}}
.t1{{position:absolute;left:60px;top:{PB-52}px;font-family:{SERIFF};font-weight:900;font-size:186px;line-height:200px;color:{INK};white-space:nowrap;letter-spacing:.01em}}
.ar{{position:absolute;left:60px;top:{PB+196}px;width:120px;height:8px}}
.ar b{{position:absolute;left:0;top:0;width:88px;height:8px;border-radius:4px;background:{BLUE}}}
.ar i{{position:absolute;left:100px;top:0;width:20px;height:8px;border-radius:4px;background:{ORG}}}
.hl{{position:absolute;left:60px;top:{PB+236}px;width:960px;height:3px;background:{LINE}}}
.s1{{position:absolute;left:60px;top:{PB+262}px;font-family:{SERIFF};font-weight:600;font-size:58px;line-height:80px;color:{GREY};white-space:nowrap;letter-spacing:.06em}}
"""
        body = (f'<div class="tab" data-k="tab"></div><div class="t1" data-k="title">{TITLE}</div>'
                f'<div class="ar" data-k="acc"><b></b><i></i></div><div class="hl" data-k="rule"></div><div class="s1" data-k="sub">{SUB}</div>')
        allow |= {("tab", "photo"), ("photo", "title"), ("tab", "title")}
    elif n == 2:
        pic_h = PIC_H + 50; PB = PIC_TOP + pic_h; T = PB + 50
        tiles = [("廣", INK, "#fff"), ("達", INK, "#fff"), ("透", "#DCE8FB", BLUE), ("明", "#DCE8FB", BLUE), ("說", ORG, INK)]
        tw = (960 - 4 * 6) / 5
        th = "".join(f'<div class="tl" style="left:{i*(tw+6):.1f}px;width:{tw:.1f}px;background:{bg};border-color:{BLUE if bg=="#DCE8FB" else bg}"></div>' for i, (c, bg, fg) in enumerate(tiles))
        ch = "".join(f'<div class="tc" data-k="c{i}" style="left:{60+i*(tw+6):.1f}px;width:{tw:.1f}px;color:{fg}">{c}</div>' for i, (c, bg, fg) in enumerate(tiles))
        css = f"""
.tr{{position:absolute;left:60px;top:{T}px;width:960px;height:{tw:.1f}px}}
.tl{{position:absolute;top:0;height:{tw:.1f}px;border-radius:18px;border:2px solid transparent;box-sizing:border-box}}
.tc{{position:absolute;top:{T}px;height:{tw:.1f}px;line-height:{tw:.1f}px;text-align:center;font-weight:900;font-size:150px;white-space:nowrap}}
.s2{{position:absolute;left:60px;top:{T+tw+30:.0f}px;font-weight:700;font-size:58px;line-height:80px;color:{INK};white-space:nowrap;letter-spacing:.04em}}
"""
        body = f'<div class="tr" data-k="tiles">{th}</div>{ch}<div class="s2" data-k="sub">{SUB}</div>'
        allow |= {("tiles", f"c{i}") for i in range(5)}
    elif n == 3:
        pic_h = 600; PB3 = PIC_TOP + pic_h          # 702
        top_a, LH = 593, 215
        E = PB3 - top_a
        css = f"""
.a1,.a2,.b1{{position:absolute;font-weight:900;font-size:210px;line-height:{LH}px;white-space:nowrap}}
.a1{{right:60px;top:{top_a}px;color:#fff;clip-path:inset(0 0 {LH-E}px 0)}}
.a2{{right:60px;top:{top_a}px;color:{INK};clip-path:inset({E}px 0 0 0)}}
.b1{{left:60px;top:{top_a+LH}px;color:{BLUE}}}
.s3{{position:absolute;left:60px;top:{top_a+2*LH+22}px;font-weight:700;font-size:58px;line-height:80px;color:{INK};white-space:nowrap;letter-spacing:.04em}}
"""
        body = (f'<div class="a1" data-k="a_up">廣達</div><div class="a2" data-k="a_dn">廣達</div><div class="b1" data-k="b">透明說</div>'
                f'<div class="s3" data-k="sub">{SUB}</div>')
        allow |= {("a_up", "photo")}
    elif n == 4:
        GT, GH = PB - 150, 440
        css = f"""
.gl{{position:absolute;left:{PX}px;top:{GT}px;width:{W-2*PX}px;height:{GH}px;border-radius:36px;background:rgba(255,255,255,.46);-webkit-backdrop-filter:blur(11px) saturate(1.2);backdrop-filter:blur(11px) saturate(1.2);border:2px solid rgba(255,255,255,.85)}}
.g1{{position:absolute;left:60px;width:960px;top:{GT+84}px;text-align:center;font-weight:800;font-size:170px;line-height:190px;color:{INK};white-space:nowrap}}
.g2{{position:absolute;left:60px;width:960px;top:{GT+294}px;text-align:center;font-weight:700;font-size:60px;line-height:84px;color:{BLUE};white-space:nowrap;letter-spacing:.06em}}
"""
        body = f'<div class="gl" data-k="glass"></div><div class="g1" data-k="title">{TITLE}</div><div class="g2" data-k="sub">{SUB}</div>'
        allow |= {("glass", "photo"), ("glass", "title"), ("glass", "sub"), ("photo", "title"), ("photo", "sub")}
    elif n == 5:
        T = PB + 14; LH = 188
        css = f"""
.m1,.m2{{position:absolute;left:54px;font-size:186px;line-height:{LH}px;color:{INK};white-space:nowrap}}
.m1{{top:{T}px;font-weight:900}}
.m2{{top:{T+LH+4}px;font-weight:200;color:{BLUE}}}
.s5{{position:absolute;right:60px;top:{T+LH-58}px;font-weight:400;font-size:56px;line-height:80px;color:{INK};white-space:nowrap;letter-spacing:.06em}}
"""
        body = f'<div class="m1" data-k="a">廣達</div><div class="m2" data-k="b">透明說</div><div class="s5" data-k="sub">{SUB}</div>'
    pic = (f'<div class="pic" data-k="photo" style="box-shadow:none;background-size:cover;height:{pic_h}px;background-image:url({photo});background-position:50% 0%"></div>')
    sw = g["SWIPE"].replace('<div class="sw">', '<div class="sw" data-k="swipe">')
    html = f'<div class="cv">{base_hd}{pic}{body}{sw}</div>'
    return html, css, allow


ISO = "body *{visibility:hidden !important} body{background:#ff00ff !important} .cv{background:transparent !important}"


def ink_boxes(pg, keys):
    out = {}
    for k in keys:
        pg.evaluate("""k=>{let s=document.getElementById('iso');if(!s){s=document.createElement('style');s.id='iso';document.head.appendChild(s)}
          s.textContent=%r+'[data-k="'+k+'"],[data-k="'+k+'"] *{visibility:visible !important}'}""" % ISO, k)
        im = Image.open(io.BytesIO(pg.screenshot())).convert("RGB")
        diff = Image.eval(Image.merge("L", [Image.eval(c, lambda v: v) for c in [im.split()[1]]]), lambda v: 255 if v > 12 else 0)   # 綠色通道：洋紅底 G=0，任何有墨跡處 G>0
        out[k] = diff.getbbox()
    pg.evaluate("document.getElementById('iso').remove()")
    return out


def main(g):
    n = int(os.environ["TITLE_STYLE"]); OUT = g["OUT"]; sync_playwright = g["sync_playwright"]
    html, css, allow = build(n, g)
    doc = (f'<!doctype html><html><head><meta charset="utf-8"><style>{font_css()}</style><style>{g["CSS"]}{g["COVER_CSS"]}{g["SWIPE_CSS"]}'
           f"body{{font-family:'TCS','Noto Sans TC',sans-serif}}{css}</style></head><body>{html}</body></html>")
    f = OUT / f"_title_{n}.html"; f.write_text(doc, encoding="utf8")
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        pg = b.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
        pg.goto(f"file://{f}", wait_until="networkidle"); pg.wait_for_timeout(800)
        pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(300)
        pg.screenshot(path=str(OUT / f"title_{n}.png"))
        keys = pg.evaluate("[...document.querySelectorAll('[data-k]')].map(e=>e.dataset.k)")
        # 墨跡外框要排除洋紅底本身：洋紅底 G=0，其他有色處 G>0；白字、深字皆 G>0（INK 的 G=27）
        boxes = ink_boxes(pg, keys)
        fs = pg.evaluate("[...document.querySelectorAll('[data-k]')].filter(e=>e.textContent.trim()&&!e.querySelector('*')).map(e=>[e.dataset.k,parseFloat(getComputedStyle(e).fontSize)])")
        ph = boxes["photo"]; sc = (ph[3] - ph[1]) / 690 if n == 2 else 1; sc = max(sc, 1); ox0 = (1032 * sc - 1032) / 2
        sign = (ph[0] + 430 * sc - ox0, ph[1] + 310 * sc - (0 if n == 2 else 0), ph[0] + 925 * sc - ox0, ph[1] + 480 * sc)
        bad, onpic, oob = [], [], []
        ks = [k for k in keys]
        for i in range(len(ks)):
            for j in range(i + 1, len(ks)):
                a, c = ks[i], ks[j]; A, C = boxes[a], boxes[c]
                if not A or not C: continue
                ox = min(A[2], C[2]) - max(A[0], C[0]); oy = min(A[3], C[3]) - max(A[1], C[1])
                if ox > 2 and oy > 2:
                    (onpic if ((a, c) in allow or (c, a) in allow) else bad).append((a, c, ox, oy))
        sign_hit = [k for k in ks if k not in ("photo",) and boxes[k] and min(boxes[k][2], sign[2]) - max(boxes[k][0], sign[0]) > 0 and min(boxes[k][3], sign[3]) - max(boxes[k][1], sign[1]) > 0 and k not in ("tab", "glass")]
        # tab／glass 面板本身也不得蓋到 Quanta 字
        sign_hit += [k for k in ("tab", "glass") if k in boxes and boxes[k] and min(boxes[k][3], 10**4) > sign[1] and boxes[k][1] < sign[3] and min(boxes[k][2], sign[2]) - max(boxes[k][0], sign[0]) > 0]
        for k in ks:
            B = boxes[k]
            if B and (B[0] < 0 or B[1] < 0 or B[2] > 1080 or B[3] > 1350): oob.append(k)
        minfs = min(v for k, v in fs if k not in ("swipe",)) if fs else 0
        res = {"style": n, "name": STYLES[n], "boxes": boxes, "疊圖(刻意)": onpic, "重疊": bad, "壓到Quanta字": sign_hit, "出界": oob, "最小字級": minfs, "字級": fs}
        json.dump(res, open(OUT / f"overlap_title_{n}.json", "w"), ensure_ascii=False, indent=1)
        print(f"title_{n} {STYLES[n]}：重疊 {len(bad)} 出界 {len(oob)} 壓到Quanta {len(sign_hit)} 刻意疊圖 {len(onpic)} 最小字級 {minfs:.0f}px", bad[:3])
        b.close()
    f.unlink()
