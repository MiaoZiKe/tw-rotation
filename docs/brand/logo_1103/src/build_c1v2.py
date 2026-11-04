#!/usr/bin/env python3
"""C1 雙 L 對扣：強化「喔」（中間那一格）的四個變體。
用法：python build_c1v2.py <字型根目錄>   （沿用 build.py 的渲染與版型函式）"""
import sys, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build as B
from PIL import Image

OUT2 = B.OUT / "c1v2"; OUT2.mkdir(exist_ok=True)

def ls(c, a, b):
    return (f'<path d="M116 116h64v216h138v64H116z" fill="{a}"/>'
            f'<path d="M396 396h-64V180H194v-64h202z" fill="{b}"/>')

def v1(c):  # 對比：兩個 L 都墨色，中間放大成純橘實心方塊（幾乎填滿中空）
    return f'<g>{ls(c,c["ink"],c["ink"])}<rect x="186" y="186" width="140" height="140" rx="30" fill="{c["main"]}"/></g>'
def v2(c):  # 圓環 O
    return f'<g>{ls(c,c["ink"],c["ink"])}<circle cx="256" cy="256" r="50" fill="none" stroke="{c["main"]}" stroke-width="36"/></g>'
def v3(c):  # 實心圓
    return f'<g>{ls(c,c["ink"],c["ink"])}<circle cx="256" cy="256" r="66" fill="{c["main"]}"/></g>'
def v4(c):  # 浮出：保留橘＋墨雙色 L，奶油留縫，中間橘方塊壓在兩個 L 的內角上
    return (f'<g>{ls(c,c["main"],c["ink"])}'
            f'<rect x="170" y="170" width="172" height="172" rx="40" fill="{c["bg"]}"/>'
            f'<rect x="188" y="188" width="136" height="136" rx="30" fill="{c["main"]}"/></g>')

VARS = [("v1_對比方塊","①　對比方塊",v1,"L 全改墨色，中間放大成純橘實心方塊"),
        ("v2_圓環O","②　圓環 O",v2,"中間改成圓角「O」圓環，直接讀得出 O"),
        ("v3_實心圓","③　實心圓",v3,"中間改成實心橘圓，40px 最耐看"),
        ("v4_浮出框","④　浮出框",v4,"橘＋墨雙色 L 不變，中間橘方塊加奶油留縫外框浮出來")]

for cid,_,fn,_ in VARS:
    (OUT2/cid).mkdir(exist_ok=True)
    B.build_concept("c1v2/"+cid, cid, fn)
    print("ok", cid)

def card(title, sub, d):
    return f'''<div style="width:620px;background:#fff;border-radius:20px;padding:22px">
<div style="font-weight:900;font-size:30px;color:#3B2A20">{title}</div>
<div style="font-weight:700;font-size:18px;color:#6b5a4d;margin-top:8px;line-height:1.5;height:54px">{sub}</div>
<div style="display:flex;gap:16px;margin-top:16px;align-items:center">
<img src="file://{d}/icon_light.png" width="176" height="176" style="border-radius:34px"><img src="file://{d}/icon_dark.png" width="176" height="176" style="border-radius:34px">
<div style="display:flex;flex-direction:column;gap:10px">
<div style="display:flex;gap:10px;align-items:center"><img src="file://{d}/circle110_light.png" width="110" height="110" style="border-radius:50%"><img src="file://{d}/circle40_light.png" width="40" height="40" style="border-radius:50%"></div>
<div style="display:flex;gap:10px;align-items:center;background:#17110D;padding:6px;border-radius:12px"><img src="file://{d}/circle110_dark.png" width="110" height="110" style="border-radius:50%"><img src="file://{d}/circle40_dark.png" width="40" height="40" style="border-radius:50%"></div>
</div></div>
<img src="file://{d}/horizontal_light.png" width="576" style="margin-top:14px;border-radius:10px"></div>'''
cards = [card("原 C1　雙 L 對扣（對照）","第三輪原版：橘＋墨 L，中間小橘方塊",B.OUT/"c1_雙L對扣")]
cards += [card(t, s, OUT2/cid) for cid,t,_,s in VARS]
html = f'<div style="width:2000px;background:#EDE7DD;padding:40px;display:grid;grid-template-columns:repeat(3,620px);gap:30px"><div style="grid-column:1/4;font-weight:900;font-size:40px;color:#3B2A20">C1 雙 L 對扣　強化「喔」四款　·　圓形 110／40 為實際像素</div>{"".join(cards)}</div>'
B.shot(html, 2000, 1330, B.TMP/"ov.png")
Image.open(B.TMP/"ov.png").convert("RGB").save(OUT2/"overview.png")
print("done")
