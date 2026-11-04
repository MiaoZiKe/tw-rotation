#!/usr/bin/env python3
"""C1 雙 L 對扣 第三版：讓小寫「i」明顯出來（Li Li＝哩哩），八款。
用法：python build_c1v3.py <字型根目錄>   （沿用 build.py 的渲染與版型函式）
各款可指定淺色底的主橘（原 #F2762E／柔和 #E9803F／更柔 #D9774A），深色底一律 #FF8F4A。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build as B
from PIL import Image

OUT3 = B.OUT / "c1v3"; OUT3.mkdir(exist_ok=True)
OUT2 = B.OUT / "c1v2"

def ls(a, b):
    """原 C1 雙 L 骨架（a＝左下 L 顏色，b＝右上 L 顏色）"""
    return (f'<path d="M116 116h64v216h138v64H116z" fill="{a}"/>'
            f'<path d="M396 396h-64V180H194v-64h202z" fill="{b}"/>')

def i_mark(cx, dy, dot_c, stem_c, ring=False, dr=22, sw=44, top=252, bot=322):
    """小寫 i：圓點（可為圓環）＋圓角直柱。座標 512。"""
    if ring:
        dot = f'<circle cx="{cx}" cy="{dy}" r="{dr-6}" fill="none" stroke="{dot_c}" stroke-width="15"/>'
    else:
        dot = f'<circle cx="{cx}" cy="{dy}" r="{dr}" fill="{dot_c}"/>'
    stem = f'<rect x="{cx-sw/2}" y="{top}" width="{sw}" height="{bot-top}" rx="12" fill="{stem_c}"/>'
    return dot + stem

# ① 中央整根橘 i
def s1(c): return f'<g>{ls(c["ink"],c["ink"])}{i_mark(256,214,c["main"],c["main"],dr=28,sw=52,top=250)}</g>'
# ② 墨柱橘點：點＝錢的落點
def s2(c): return f'<g>{ls(c["ink"],c["ink"])}{i_mark(256,214,c["main"],c["ink"],dr=27,sw=42)}</g>'
# ③ 連體 Li 風車：L 的腳延伸成 i 的柱，上方加點；兩組旋轉 180° 對扣
def s3(c):
    unit = (f'<path d="M120 120h56v216h88v-74h52v130H120z" fill="{c["ink"]}"/>'
            f'<circle cx="290" cy="220" r="27" fill="{c["main"]}"/>')
    return f'<g>{unit}<g transform="rotate(180 256 256)">{unit}</g></g>'
# ④ 左右鏡像 Li｜iL
def s4(c):
    unit = (f'<path d="M56 140h50v194h50v48H56z" fill="{c["ink"]}"/>'
            f'<circle cx="195" cy="218" r="25" fill="{c["main"]}"/>'
            f'<rect x="172" y="262" width="46" height="120" rx="12" fill="{c["main"]}"/>')
    return (f'<g transform="translate(0,-4)"><g transform="translate(26,0)">{unit}</g>'
            f'<g transform="translate(512,0) scale(-1,1) translate(26,0)">{unit}</g></g>')
# ⑤ i 的點做成圓環 O
def s5(c): return f'<g>{ls(c["ink"],c["ink"])}{i_mark(256,214,c["main"],c["ink"],ring=True,dr=33,sw=42,top=258)}</g>'
# ⑥ 字標式：縮小的雙 L＋i，下方「Li Li」小字
def s6(c):
    return (f'<g transform="translate(256,222) scale(0.78) translate(-256,-256)">{ls(c["ink"],c["ink"])}'
            f'{i_mark(256,216,c["main"],c["main"],dr=26,sw=46)}</g>'
            f'<text x="256" y="430" text-anchor="middle" font-family="NST,sans-serif" font-weight="900" font-size="76" letter-spacing="6" fill="{c["ink"]}">Li Li</text>')
# ⑦ 雙 i 對扣：一正一倒（旋轉 180°），各自落在自己那個 L 的懷裡
def s7(c):
    one = i_mark(222,220,c["main"],c["ink"],dr=22,sw=40,top=254,bot=324)
    return f'<g>{ls(c["ink"],c["ink"])}{one}<g transform="rotate(180 256 256)">{one}</g></g>'
# ⑧ 保留原 C1 橘＋墨雙色 L，中間墨柱＋橘環點
def s8(c): return f'<g>{ls(c["main"],c["ink"])}{i_mark(256,214,c["main"],c["ink"],ring=True,dr=33,sw=42,top=258)}</g>'

ORG, SOFT, SOFTER = "#F2762E", "#E9803F", "#D9774A"
VARS = [
 ("v1_橘i",   "①　整根橘 i",     s1, ORG,    "第一層：墨色雙 L 中間一個橘色小寫 i｜第二層：L‧i‧L，Li Li（哩哩）"),
 ("v2_橘點墨柱","②　橘點墨柱 i",  s2, SOFTER, "第一層：墨色 L＋墨色 i，只有 i 的點是橘色｜第二層：橘點＝錢的落點，Li Li"),
 ("v3_連體Li風車","③　連體 Li 風車", s3, SOFT, "第一層：兩個 L 的腳各長出一根柱、上面頂一顆橘點｜第二層：兩個「Li」旋轉對扣"),
 ("v4_鏡像LiiL","④　鏡像 Li｜iL", s4, ORG,    "第一層：左右兩組 Li 鏡像並排｜第二層：Li 與 iL 對扣，你的股我的股"),
 ("v5_圓環點i", "⑤　圓環點 i",   s5, SOFT,   "第一層：墨色 L＋墨柱，i 的點是圓環｜第二層：環＝O，延續喜歡的圓環，Li Li"),
 ("v6_字標式",  "⑥　字標式 Li Li", s6, ORG,   "第一層：縮小的雙 L＋i，下方一行 Li Li｜第二層：圖示直接念出哩哩"),
 ("v7_雙i對扣", "⑦　雙 i 對扣",  s7, SOFTER, "第一層：中間一正一倒兩個 i｜第二層：兩個 L 各養一個 i，共 Li Li"),
 ("v8_雙色L環點","⑧　雙色 L＋環點 i", s8, SOFT, "第一層：保留橘＋墨雙色 L，中間墨柱橘環點｜第二層：橘 L‧i‧墨 L"),
]

_orig_h = B.horizontal_html
def h_lili(fn, theme, scale=1.0):
    c = B.THEMES[theme]
    return f'''<div style="width:1000px;height:240px;background:{c['page']};display:flex;align-items:center;padding-left:60px;gap:36px">
<div style="width:150px;height:150px;border-radius:34px;overflow:hidden;flex:none">{B.icon_svg(fn, theme, 150)}</div>
<div><div style="font-weight:900;font-size:84px;line-height:1.05;color:{c['text']};letter-spacing:4px">哩股哩股</div>
<div style="font-weight:700;font-size:30px;letter-spacing:8px;color:{c['main']};margin-top:6px">Li Li ・ LIGULIGU</div></div></div>'''

for cid,_,fn,mainl,_ in VARS:
    (OUT3/cid).mkdir(exist_ok=True)
    keep = B.THEMES["light"]["main"]; B.THEMES["light"]["main"] = mainl
    B.horizontal_html = h_lili if cid.startswith("v6") else _orig_h
    B.build_concept("c1v3/"+cid, cid, fn)
    B.THEMES["light"]["main"] = keep; B.horizontal_html = _orig_h
    print("ok", cid)

def card(title, sub, d, hexs):
    return f'''<div style="width:620px;background:#fff;border-radius:20px;padding:22px">
<div style="font-weight:900;font-size:30px;color:#3B2A20">{title}<span style="font-weight:700;font-size:18px;color:#8A7667">　{hexs}</span></div>
<div style="font-weight:700;font-size:17px;color:#6b5a4d;margin-top:8px;line-height:1.55;height:56px">{sub}</div>
<div style="display:flex;gap:16px;margin-top:10px;align-items:center">
<img src="file://{d}/icon_light.png" width="176" height="176" style="border-radius:34px"><img src="file://{d}/icon_dark.png" width="176" height="176" style="border-radius:34px">
<div style="display:flex;flex-direction:column;gap:10px">
<div style="display:flex;gap:10px;align-items:center"><img src="file://{d}/circle110_light.png" width="110" height="110" style="border-radius:50%"><img src="file://{d}/circle40_light.png" width="40" height="40" style="border-radius:50%"></div>
<div style="display:flex;gap:10px;align-items:center;background:#17110D;padding:6px;border-radius:12px"><img src="file://{d}/circle110_dark.png" width="110" height="110" style="border-radius:50%"><img src="file://{d}/circle40_dark.png" width="40" height="40" style="border-radius:50%"></div>
</div></div>
<img src="file://{d}/horizontal_light.png" width="576" style="margin-top:14px;border-radius:10px"></div>'''
cards = [card("上一輪推薦　②圓環 O（對照）","第一層：墨色雙 L 中間一個橘環｜第二層：L‧O‧L（本輪要改成讀得出小寫 i）",OUT2/"v2_圓環O","#F2762E")]
cards += [card(t, s, OUT3/cid, m) for (cid,t,_,m,s) in VARS]
html = f'<div style="width:2000px;background:#EDE7DD;padding:40px;display:grid;grid-template-columns:repeat(3,620px);gap:30px"><div style="grid-column:1/4;font-weight:900;font-size:40px;color:#3B2A20">C1 雙 L 對扣 第三版　小寫 i 要看得見（Li Li）　·　圓形 110／40 為實際像素</div>{"".join(cards)}</div>'
B.shot(html, 2000, 1900, B.TMP/"ov.png")
Image.open(B.TMP/"ov.png").convert("RGB").save(OUT3/"overview.png")
print("done")
