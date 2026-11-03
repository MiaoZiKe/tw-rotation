#!/usr/bin/env python3
"""哩股哩股 LOGO 第三輪（有寓意）：八款向量圖示 + 全套輸出。
用法：python build.py <字型根目錄，內含 package/files 與 package/700.css 之類 fontsource-noto-sans-tc 解開的內容> [fast]
圖示本身是純向量、不含文字（「里」字用字型輪廓轉成路徑）；橫式與個人頁的字用 Noto Sans TC（SIL OFL 1.1）。
需要：Pillow、fonttools、brotli、google-chrome（無頭模式渲染）。
"""
import sys, os, subprocess, math, shutil
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen
from PIL import Image

FONT_ROOT = Path(sys.argv[1]).resolve()
FAST = len(sys.argv) > 2 and sys.argv[2] == "fast"
OUT = Path(__file__).resolve().parent.parent
TMP = OUT / "src" / "_tmp"
TMP.mkdir(exist_ok=True)
CHROME = shutil.which("google-chrome") or "google-chrome"
FILES = FONT_ROOT / "package" / "files"

# ---------- 色票：陽光糖果（暖色）。一個主色橘，墨色與奶油為輔，不螢光 ----------
THEMES = {
    "light": dict(bg="#FFF4E2", main="#F2762E", ink="#3B2A20", soft="#FFD3B0", page="#FFFFFF", text="#3B2A20", sub="#8A7667"),
    "dark":  dict(bg="#2A1F19", main="#FF8F4A", ink="#FFF1E0", soft="#6E4A32", page="#17110D", text="#FFF1E0", sub="#B7A08F"),
}

# ---------- 字型輪廓：取「里」 ----------
_font = TTFont(str(FILES / "noto-sans-tc-chinese-traditional-900-normal.woff2"))
_gs = _font.getGlyphSet(); _cmap = _font.getBestCmap()

def glyph_path(ch, x, y_base, size):
    """回傳 (path d, 寬, bbox)；x、y_base 為左下基準，size 為 em 像素。"""
    name = _cmap[ord(ch)]
    k = size / _font["head"].unitsPerEm
    pen = SVGPathPen(_gs)
    _gs[name].draw(TransformPen(pen, (k, 0, 0, -k, x, y_base)))
    bp = BoundsPen(_gs); _gs[name].draw(bp)
    return pen.getCommands(), bp.bounds, k

def wedge(cx, cy, r, a0, a1):
    """扇形（角度：0=右、順時針為正，單位度）。"""
    x0, y0 = cx + r*math.cos(math.radians(a0)), cy + r*math.sin(math.radians(a0))
    x1, y1 = cx + r*math.cos(math.radians(a1)), cy + r*math.sin(math.radians(a1))
    large = 1 if (a1 - a0) % 360 > 180 else 0
    return f"M{cx:.1f} {cy:.1f}L{x0:.1f} {y0:.1f}A{r} {r} 0 {large} 1 {x1:.1f} {y1:.1f}Z"

# ---------- 八款符號（512 座標，內容控制在圓心半徑 ~185 內，IG 圓形裁切不會被切）----------
def s1_dual_l(c):
    # 兩個 L 對扣（風車），中間留一格放「被選中的那檔股」
    return f'''
<g>
<path d="M116 116h64v216h138v64H116z" fill="{c['main']}"/>
<path d="M396 396h-64V180H194v-64h202z" fill="{c['ink']}"/>
<rect x="212" y="212" width="88" height="88" rx="22" fill="{c['main']}"/>
</g>'''

def s2_pie(c):
    cx, cy, r, off = 232, 280, 116, 50
    d1 = f"M{cx} {cy}L{cx} {cy-r}A{r} {r} 0 1 0 {cx+r} {cy}Z"
    d2 = wedge(cx+off, cy-off, r, -90, 0)
    return f'''
<path d="{d1}" fill="{c['main']}"/>
<path d="{d2}" fill="{c['ink']}"/>
<path d="M{cx+r*0.35:.0f} {cy-r*0.35-6:.0f}L{cx+r*0.35+16:.0f} {cy-r*0.35-22:.0f}" stroke="{c['soft']}" stroke-width="10" stroke-linecap="round"/>'''

def s3_screen(c):
    # 「哩」＝口 + 里。口做成看盤螢幕（裡面一條上揚線），里用字型輪廓
    d, bb, k = glyph_path("里", 0, 0, 270)
    gx0, gy0, gx1, gy1 = bb[0]*k, -bb[3]*k, bb[2]*k, -bb[1]*k   # 轉成螢幕座標範圍
    gw, gh = gx1-gx0, gy1-gy0
    sw, sh, gap = 150, 132, 22
    total = sw + gap + gw
    X0 = 256 - total/2
    top = 256 - gh/2
    d, bb, k = glyph_path("里", X0 + sw + gap - gx0, top - gy0, 270)
    sy = top + gh*0.12
    return f'''
<rect x="{X0:.1f}" y="{sy:.1f}" width="{sw}" height="{sh}" rx="22" fill="{c['main']}"/>
<polyline points="{X0+30:.1f},{sy+sh-32:.1f} {X0+64:.1f},{sy+sh-64:.1f} {X0+90:.1f},{sy+sh-44:.1f} {X0+120:.1f},{sy+32:.1f}" fill="none" stroke="{c['bg']}" stroke-width="14" stroke-linecap="round" stroke-linejoin="round"/>
<path d="{d}" fill="{c['ink']}"/>'''

def s4_river(c):
    dots = ""
    return f'''
<g transform="translate(-10,-4)">
<path d="M150 112V338Q150 396 208 396H320" fill="none" stroke="{c['main']}" stroke-width="64" stroke-linecap="round" stroke-linejoin="round"/>
<circle cx="150" cy="168" r="9" fill="{c['bg']}"/><circle cx="150" cy="238" r="9" fill="{c['bg']}"/><circle cx="150" cy="306" r="9" fill="{c['bg']}"/>
<circle cx="262" cy="396" r="9" fill="{c['bg']}"/>
<circle cx="390" cy="396" r="44" fill="{c['ink']}"/>
<circle cx="390" cy="396" r="18" fill="{c['bg']}"/>
</g>'''

def s5_fork(c):
    return f'''
<g transform="translate(0,-4)">
<path d="M256 410V300" stroke="{c['ink']}" stroke-width="36" stroke-linecap="round" fill="none"/>
<path d="M256 300L136 186" stroke="{c['soft']}" stroke-width="36" stroke-linecap="round" fill="none"/>
<path d="M256 300V152" stroke="{c['soft']}" stroke-width="36" stroke-linecap="round" fill="none"/>
<path d="M256 300L376 186" stroke="{c['main']}" stroke-width="48" stroke-linecap="round" fill="none"/>
<circle cx="136" cy="176" r="30" fill="{c['soft']}"/>
<circle cx="256" cy="142" r="30" fill="{c['soft']}"/>
<circle cx="386" cy="176" r="46" fill="{c['main']}"/>
<circle cx="256" cy="300" r="40" fill="{c['ink']}"/>
<circle cx="256" cy="300" r="14" fill="{c['bg']}"/>
</g>'''

def s6_lens(c):
    cx, cy, r = 232, 232, 118
    pr = 76
    return f'''
<g transform="translate(9,9)">
<path d="M{cx+84} {cy+84}L388 388" stroke="{c['ink']}" stroke-width="46" stroke-linecap="round"/>
<circle cx="{cx}" cy="{cy}" r="{r}" fill="{c['bg']}"/>
<path d="{wedge(cx,cy,pr,-100,150)}" fill="{c['main']}"/>
<path d="{wedge(cx+8*math.cos(math.radians(195)),cy+8*math.sin(math.radians(195)),pr,150,240)}" fill="{c['soft']}"/>
<path d="{wedge(cx,cy,pr,240,260)}" fill="{c['soft']}"/>
<path d="{wedge(cx,cy,pr,260,260)}" fill="{c['soft']}"/>
<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{c['ink']}" stroke-width="40"/>
</g>'''

def s7_candles(c):
    # 兩根 K 棒＝「哩」：左邊空心 K 棒＝口；右邊 K 棒的實體切成田、影線＝里中間那一豎、底座＝土
    ox = 33
    return f'''
<g transform="translate({ox},0)">
<path d="M147 160V190M147 290V330" stroke="{c['main']}" stroke-width="14" stroke-linecap="round"/>
<rect x="104" y="196" width="86" height="92" rx="14" fill="none" stroke="{c['main']}" stroke-width="24"/>
<path d="M282 112V150" stroke="{c['ink']}" stroke-width="22" stroke-linecap="round"/>
<rect x="228" y="150" width="108" height="112" rx="14" fill="{c['ink']}"/>
<path d="M282 150V262M228 206H336" stroke="{c['bg']}" stroke-width="12"/>
<path d="M282 262V396" stroke="{c['ink']}" stroke-width="22"/>
<path d="M250 322H314" stroke="{c['ink']}" stroke-width="22" stroke-linecap="round"/>
<path d="M214 396H350" stroke="{c['ink']}" stroke-width="26" stroke-linecap="round"/>
</g>'''

def s8_door(c):
    # 方框＝「口」，硬幣掉進缺口
    return f'''
<g transform="translate(0,16)">
<path d="M196 168H138Q116 168 116 190V360Q116 382 138 382H374Q396 382 396 360V190Q396 168 374 168H316" fill="none" stroke="{c['main']}" stroke-width="40" stroke-linecap="round" stroke-linejoin="round"/>
<circle cx="256" cy="120" r="44" fill="{c['ink']}"/>
<path d="M256 99v42M240 112h24q10 0 10 9t-10 9h-20" stroke="none"/>
<path d="M222 262l34 34l34 -34" fill="none" stroke="{c['soft']}" stroke-width="16" stroke-linecap="round" stroke-linejoin="round"/>
</g>'''

CONCEPTS = [
    ("c1_雙L對扣", "雙 L 對扣", s1_dual_l, "兩個 L（Li‧Li）對扣成一個方框", "框中那一格＝被你選中的那檔股；你的股、我的股互相扣住"),
    ("c2_飛走的一角", "飛走的一角", s2_pie, "一塊圓餅缺了一角，那一角飛向右上", "資金從這個族群跑去下一個（輪動）"),
    ("c3_哩的螢幕", "哩的螢幕", s3_screen, "「哩」字：左邊的口是一台看盤螢幕", "口＝盤面，上揚線＝看懂資金往哪走"),
    ("c4_河道成L", "河道成 L", s4_river, "一條河彎成字母 L，流進一顆圓", "L＝哩；河＝資金流，終點圓＝它流進的族群"),
    ("c5_岔路的點", "岔路的點", s5_fork, "一個點站在三岔路口，橘色那條最粗", "錢在選族群；橘色＝資金最大宗流向"),
    ("c6_看懂的放大鏡", "看懂的放大鏡", s6_lens, "放大鏡裡有一塊圓餅", "放大＝看懂；橘色那塊＝錢集中的族群"),
    ("c7_K棒哩字", "K 棒哩字", s7_candles, "兩根 K 棒", "空心 K 棒＝口，田字實體＋影線＋底座＝里，合起來是「哩」"),
    ("c8_入口", "錢的入口", s8_door, "一枚硬幣掉進方框缺口", "方框＝哩的口，也是資金入口；帶你看錢從哪個口進場"),
]

def icon_svg(fn, theme, size=512, full=True):
    c = THEMES[theme]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="{size}" height="{size}">'
            f'<rect width="512" height="512" fill="{c["bg"]}"/>{fn(c)}</svg>')

# ---------- Chrome 渲染 ----------
def fonts_css():
    rules = []
    for w in (700, 900):
        for line in (FONT_ROOT/"package"/f"{w}.css").read_text().split("@font-face"):
            if "url(" not in line: continue
            fn = line.split("url(./files/")[1].split(")")[0]
            ur = line.split("unicode-range:")[1].split(";")[0]
            rules.append("@font-face{font-family:'NST';font-weight:%d;src:url('file://%s/%s');unicode-range:%s}" % (w, FILES, fn, ur))
    return "\n".join(rules)
FONTS_CSS = fonts_css()

def shot(html, w, h, out):
    f = TMP / "p.html"
    f.write_text(f'<!doctype html><meta charset="utf-8"><style>{FONTS_CSS}html,body{{margin:0;background:#fff}}*{{box-sizing:border-box;font-family:NST,sans-serif}}</style><body>{html}</body>', encoding="utf-8")
    subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
                    "--force-device-scale-factor=1", f"--window-size={w},{h}", f"--screenshot={out}", f"file://{f}"],
                   check=True, capture_output=True, timeout=120)

def horizontal_html(fn, theme, scale=1.0):
    c = THEMES[theme]
    return f'''<div style="width:1000px;height:240px;background:{c['page']};display:flex;align-items:center;padding-left:60px;gap:36px">
<div style="width:150px;height:150px;border-radius:34px;overflow:hidden;flex:none">{icon_svg(fn, theme, 150)}</div>
<div><div style="font-weight:900;font-size:84px;line-height:1.05;color:{c['text']};letter-spacing:4px">哩股哩股</div>
<div style="font-weight:700;font-size:32px;letter-spacing:12px;color:{c['main']};margin-top:6px">LIGULIGU</div></div></div>'''

def profile_html(fn, theme):
    c = THEMES[theme]
    return f'''<div style="width:1000px;height:420px;background:{c['page']};padding:36px 48px;position:relative;color:{c['text']}">
<div style="display:flex;justify-content:space-between;align-items:flex-start">
<div><div style="font-weight:900;font-size:44px">哩股哩股</div><div style="font-weight:700;font-size:26px;color:{c['sub']};margin-top:6px">liguligu.tw（示意）</div></div>
<div style="width:110px;height:110px;border-radius:50%;overflow:hidden">{icon_svg(fn, theme, 110)}</div></div>
<div style="font-weight:700;font-size:28px;line-height:1.5;margin-top:26px">錢往哪個族群跑，每天盤後一張圖講白話。</div>
<div style="font-weight:700;font-size:24px;color:{c['sub']};margin-top:14px">每天盤後更新　·　只談資金與族群，不報明牌</div>
<div style="margin-top:28px;display:flex;gap:16px"><div style="padding:14px 70px;border-radius:14px;border:2px solid {c['sub']};font-weight:900;font-size:26px">追蹤</div><div style="padding:14px 70px;border-radius:14px;border:2px solid {c['sub']};font-weight:900;font-size:26px">提及</div></div></div>'''

def build_concept(cid, name, fn):
    d = OUT / cid; d.mkdir(exist_ok=True)
    cells = []
    for i, th in enumerate(("light", "dark")):
        (d / f"icon_{th}.svg").write_text(icon_svg(fn, th), encoding="utf-8")
        cells.append(f'<div style="position:absolute;left:{i*1024}px;top:0">{icon_svg(fn, th, 1024)}</div>')
        cells.append(f'<div style="position:absolute;left:{i*130}px;top:1024px;width:110px;height:110px;border-radius:50%;overflow:hidden">{icon_svg(fn, th, 110)}</div>')
        cells.append(f'<div style="position:absolute;left:{300+i*70}px;top:1024px;width:40px;height:40px;border-radius:50%;overflow:hidden">{icon_svg(fn, th, 40)}</div>')
        cells.append(f'<div style="position:absolute;left:{i*1024}px;top:1160px">{horizontal_html(fn, th)}</div>')
        cells.append(f'<div style="position:absolute;left:{i*1024}px;top:1420px">{profile_html(fn, th)}</div>')
    shot("".join(cells), 2048, 1850, TMP / "sheet.png")
    im = Image.open(TMP / "sheet.png").convert("RGB")
    for i, th in enumerate(("light", "dark")):
        im.crop((i*1024, 0, i*1024+1024, 1024)).save(d / f"icon_{th}.png")
        im.crop((i*130, 1024, i*130+110, 1134)).save(d / f"circle110_{th}.png")
        im.crop((300+i*70, 1024, 340+i*70, 1064)).save(d / f"circle40_{th}.png")
        im.crop((i*1024, 1160, i*1024+1000, 1400)).save(d / f"horizontal_{th}.png")
        im.crop((i*1024, 1420, i*1024+1000, 1840)).save(d / f"profile_{th}.png")

def build_overview():
    cards = []
    for cid, name, fn, l1, l2 in CONCEPTS:
        n = cid.split("_")[0].upper()
        cards.append(f'''<div style="width:620px;background:#fff;border-radius:20px;padding:22px;margin:0">
<div style="font-weight:900;font-size:30px;color:#3B2A20">{n}　{name}</div>
<div style="font-weight:700;font-size:18px;color:#6b5a4d;margin-top:8px;line-height:1.5">第一層：{l1}<br>第二層：{l2}</div>
<div style="display:flex;gap:16px;margin-top:16px;align-items:center">
<img src="file://{OUT}/{cid}/icon_light.png" width="200" height="200" style="border-radius:34px"><img src="file://{OUT}/{cid}/icon_dark.png" width="200" height="200" style="border-radius:34px">
<div style="display:flex;flex-direction:column;gap:10px">
<div style="display:flex;gap:10px;align-items:center"><img src="file://{OUT}/{cid}/circle110_light.png" width="110" height="110" style="border-radius:50%"><img src="file://{OUT}/{cid}/circle40_light.png" width="40" height="40" style="border-radius:50%"></div>
<div style="display:flex;gap:10px;align-items:center;background:#17110D;padding:6px;border-radius:12px"><img src="file://{OUT}/{cid}/circle110_dark.png" width="110" height="110" style="border-radius:50%"><img src="file://{OUT}/{cid}/circle40_dark.png" width="40" height="40" style="border-radius:50%"></div>
</div></div></div>''')
    html = f'<div style="width:2620px;background:#EDE7DD;padding:40px;display:grid;grid-template-columns:repeat(4,620px);gap:30px"><div style="grid-column:1/5;font-weight:900;font-size:44px;color:#3B2A20">哩股哩股 LOGO 第三輪（有寓意）　八個方向　·　圓形 110／40 為實際像素</div>{"".join(cards)}</div>'
    shot(html, 2620, 1030, TMP / "ov.png")
    Image.open(TMP / "ov.png").convert("RGB").save(OUT / "overview.png")

def build_detail():
    rows = []
    for cid, name, fn, l1, l2 in CONCEPTS:
        n = cid.split("_")[0].upper()
        rows.append(f'''<div style="background:#fff;border-radius:20px;padding:20px;margin-bottom:24px"><div style="font-weight:900;font-size:30px;color:#3B2A20;margin-bottom:12px">{n}　{name}</div>
<div style="display:flex;gap:16px"><img src="file://{OUT}/{cid}/horizontal_light.png" width="800"><img src="file://{OUT}/{cid}/horizontal_dark.png" width="800"></div>
<div style="display:flex;gap:16px;margin-top:12px"><img src="file://{OUT}/{cid}/profile_light.png" width="800"><img src="file://{OUT}/{cid}/profile_dark.png" width="800"></div></div>''')
    html = f'<div style="width:1760px;background:#EDE7DD;padding:40px">{"".join(rows)}</div>'
    shot(html, 1760, 8*(20+20+42+192+12+336+24)+120, TMP / "dt.png")
    Image.open(TMP / "dt.png").convert("RGB").save(OUT / "overview_detail.png")

if __name__ == "__main__":
    if not FAST:
        for cid, name, fn, *_ in CONCEPTS:
            build_concept(cid, name, fn); print("ok", cid)
    build_overview(); build_detail(); print("done")
