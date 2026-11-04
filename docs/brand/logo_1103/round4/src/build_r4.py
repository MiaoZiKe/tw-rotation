#!/usr/bin/env python3
"""哩股哩股 LOGO 第四輪：八種風格 × 八組色調。
用法：python build_r4.py <fontsource-noto-sans-tc 解開的根目錄>
全部向量，圖示不含文字；橫式字用 Noto Sans TC（SIL OFL 1.1）。沿用上一輪 src/build.py 的 Chrome 渲染函式。"""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "src"))
import build as B
from PIL import Image

R4 = HERE.parent
TMP = HERE / "_tmp"; TMP.mkdir(exist_ok=True)

def mix(a, b, t):
    a = [int(a[i:i+2], 16) for i in (1, 3, 5)]; b = [int(b[i:i+2], 16) for i in (1, 3, 5)]
    return "#%02X%02X%02X" % tuple(round(x*(1-t)+y*t) for x, y in zip(a, b))

# ---------- 八組色調：light/dark 各 (底, 墨=主體, 主=重點色) ----------
PAL = {
 "A": ("陽光橘＋墨",      ("#FFF4E2", "#3B2A20", "#F2762E"), ("#2A1F19", "#FFF1E0", "#FF8F4A")),
 "B": ("柔和陶土",        ("#FBF1E6", "#3B2A20", "#D9774A"), ("#2A1F19", "#FFF1E0", "#E9915F")),
 "C": ("專業深藍＋銅紅",  ("#FBFAF6", "#14213D", "#A8482A"), ("#0E1830", "#FBFAF6", "#D0643F")),
 "D": ("墨綠＋金",        ("#F6F3E8", "#1F4D3A", "#C9A227"), ("#12261D", "#EFEBD8", "#D8B545")),
 "E": ("灰藍＋珊瑚",      ("#F4F6F8", "#3D5A73", "#E8735A"), ("#1B2833", "#E6EDF3", "#F08A72")),
 "F": ("黑白單色",        ("#FFFFFF", "#111111", "#7A7A7A"), ("#111111", "#FFFFFF", "#A8A8A8")),
 "G": ("青綠科技",        ("#F1F7F6", "#134E4A", "#1F9E94"), ("#0F2423", "#E4F2F0", "#3FBDB1")),
 "H": ("酒紅＋米白",      ("#F6EEDF", "#5E1A2A", "#A8324A"), ("#2A0F16", "#F6EEDF", "#D9788A")),
}
def theme(pid, th):
    bg, ink, main = PAL[pid][1 if th == "light" else 2]
    page = "#FFFFFF" if th == "light" else mix(bg, "#000000", .35)
    return dict(bg=bg, ink=ink, main=main, soft=mix(main, bg, .45), page=page, sub=mix(ink, bg, .45))

# ---------- 八種風格（512 座標，內容落在中央約 56–72%）----------
def ls_fill(a, b):  # 幾何雙 L（對照用）
    return (f'<path d="M116 116h64v216h138v64H116z" fill="{a}"/>'
            f'<path d="M396 396h-64V180H194v-64h202z" fill="{b}"/>')

def st1_mono(c):
    k = 'fill="none" stroke-linecap="round" stroke-linejoin="round"'
    return (f'<g {k} stroke="{c["ink"]}" stroke-width="26"><path d="M138 118V374H318"/><path d="M374 394V138H194"/></g>'
            f'<circle cx="256" cy="222" r="17" fill="none" stroke="{c["main"]}" stroke-width="11"/>'
            f'<path d="M256 268V322" stroke="{c["main"]}" stroke-width="26" stroke-linecap="round"/>')

def st2_flat(c):
    return (ls_fill(c["ink"], c["ink"]) +
            f'<circle cx="256" cy="214" r="28" fill="{c["main"]}"/>'
            f'<rect x="230" y="250" width="52" height="72" rx="12" fill="{c["main"]}"/>')

def st3_soft(c):
    k = 'fill="none" stroke-linecap="round" stroke-linejoin="round"'
    return (f'<g {k} stroke="{c["ink"]}" stroke-width="54"><path d="M140 140V358H294"/><path d="M372 372V154H218"/></g>'
            f'<circle cx="256" cy="222" r="23" fill="{c["main"]}"/>'
            f'<rect x="235" y="262" width="42" height="44" rx="21" fill="{c["main"]}"/>')

def st4_fine(c):
    return (f'<g fill="none" stroke="{c["ink"]}" stroke-width="14" stroke-linejoin="miter"><path d="M130 100V380H330"/><path d="M382 412V132H182"/></g>'
            f'<circle cx="256" cy="224" r="19" fill="{c["main"]}"/>'
            f'<rect x="249" y="268" width="14" height="68" fill="{c["main"]}"/>')

def st5_wordmark(c):
    # 「Li」連字：L 的腳一路延伸，i 的柱子直接從腳上長出來
    return (f'<g transform="translate(27,0)">'
            f'<path d="M118 104H190V330H340V400H118Z" fill="{c["ink"]}"/>'
            f'<rect x="276" y="214" width="64" height="116" fill="{c["main"]}"/>'
            f'<circle cx="308" cy="154" r="38" fill="{c["main"]}"/></g>')

def st6_badge(c):
    return (f'<circle cx="256" cy="256" r="204" fill="{c["ink"]}"/>'
            f'<circle cx="256" cy="256" r="182" fill="none" stroke="{c["main"]}" stroke-width="6"/>'
            f'<g transform="translate(256,256) scale(0.6) translate(-256,-256)">{ls_fill(c["bg"], c["bg"])}'
            f'<circle cx="256" cy="214" r="28" fill="{c["main"]}"/><rect x="230" y="250" width="52" height="72" rx="12" fill="{c["main"]}"/></g>')

def st7_negative(c):
    # 實心方塊，被一道「i」形空白切成兩個互扣的 L；i 的點是一顆圓孔，孔中一點重點色
    ch = c["bg"]
    return (f'<rect x="106" y="106" width="300" height="300" rx="60" fill="{c["ink"]}"/>'
            f'<g fill="{ch}"><rect x="226" y="226" width="60" height="120" rx="8"/>'
            f'<rect x="106" y="217" width="130" height="18"/><rect x="276" y="337" width="130" height="18"/>'
            f'<circle cx="256" cy="168" r="34"/></g>'
            f'<circle cx="256" cy="168" r="19" fill="{c["main"]}"/>')

def st8_pixel(c):
    P, S, X0 = 36, 30, 94
    cells = []
    def cell(col, row, color): cells.append(f'<rect x="{X0+col*P}" y="{X0+row*P}" width="{S}" height="{S}" rx="4" fill="{color}"/>')
    for r in range(9):
        for cc in range(9):
            L1 = (cc <= 1) or (r >= 7 and cc <= 5)
            L2 = (cc >= 7) or (r <= 1 and cc >= 3)
            if L1 or L2: cell(cc, r, c["ink"])
    cell(4, 3, c["main"]); cell(4, 5, c["main"]); cell(4, 6, c["main"])
    return "".join(cells)

STY = [  # id, 名稱, 函式, 第一層, 第二層, 最適合色調
 ("s1_單線描邊", "①　單線描邊", st1_mono, "等寬圓頭線條畫成兩個 L，中間一個空心點的 i", "L‧i‧L＝Li Li（哩哩）；一筆到底的線＝資金流過的軌跡", "E"),
 ("s2_幾何扁平", "②　幾何扁平（對照）", st2_flat, "實心塊雙 L 對扣，中間橘 i", "L‧i‧L＝Li Li；實心塊＝穩，橘 i＝被選中的那檔", "A"),
 ("s3_圓潤軟糖", "③　圓潤軟糖", st3_soft, "大圓角胖筆畫雙 L，中間圓胖的 i", "兩個 L 抱住一顆 i，Li Li；軟＝親切、不嚇人", "B"),
 ("s4_細緻精品", "④　細緻精品", st4_fine, "細線雙 L＋大量留白，i 的點是唯一實心", "留白＝克制，唯一的點＝重點；像私人銀行的標", "D"),
 ("s5_字標連字", "⑤　字標優先（Li 連字）", st5_wordmark, "大寫 L 與小寫 i 共用同一條底線的字母組合", "L 的腳長出 i＝Li（哩）；i 的點＝被選中的那檔", "C"),
 ("s6_徽章", "⑥　徽章（細框不加粗）", st6_badge, "實心圓章，章內白色雙 L＋彩色 i，內縮一圈細框線", "圓章＝信用背書；章內仍是 Li Li", "H"),
 ("s7_負空間", "⑦　負空間", st7_negative, "一塊實心方塊，被一道「i」形空白切開", "切開的兩半是互扣的 L 與 L，空白本身是 i：Li Li", "F"),
 ("s8_像素點陣", "⑧　像素點陣", st8_pixel, "9×9 方格排出雙 L，中間三格彩色 i", "格子＝一筆筆成交資料；L‧i‧L＝Li Li", "G"),
]

def icon(fn, pid, th, size):
    c = theme(pid, th)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="{size}" height="{size}">'
            f'<rect width="512" height="512" fill="{c["bg"]}"/>{fn(c)}</svg>')

def horiz(fn, pid, th, scale=1.0):
    c = theme(pid, th)
    return f'''<div style="width:1000px;height:240px;background:{c['page']};display:flex;align-items:center;padding-left:60px;gap:36px">
<div style="width:150px;height:150px;border-radius:34px;overflow:hidden;flex:none">{icon(fn, pid, th, 150)}</div>
<div><div style="font-weight:900;font-size:84px;line-height:1.05;color:{c['ink'] if th=='dark' else c['ink']};letter-spacing:4px">哩股哩股</div>
<div style="font-weight:700;font-size:32px;letter-spacing:12px;color:{c['main']};margin-top:6px">LIGULIGU</div></div></div>'''

def circle(fn, pid, th, px):
    return f'<div style="width:{px}px;height:{px}px;border-radius:50%;overflow:hidden;flex:none">{icon(fn, pid, th, px)}</div>'

def export_style(sid, fn, pid):
    d = R4 / sid; d.mkdir(exist_ok=True)
    cells = []
    for i, th in enumerate(("light", "dark")):
        (d / f"icon_{th}.svg").write_text(icon(fn, pid, th, 512), encoding="utf-8")
        cells.append(f'<div style="position:absolute;left:{i*1024}px;top:0">{icon(fn, pid, th, 1024)}</div>')
        cells.append(f'<div style="position:absolute;left:{i*130}px;top:1024px">{circle(fn, pid, th, 110)}</div>')
        cells.append(f'<div style="position:absolute;left:{300+i*70}px;top:1024px">{circle(fn, pid, th, 40)}</div>')
        cells.append(f'<div style="position:absolute;left:{i*1024}px;top:1160px">{horiz(fn, pid, th)}</div>')
    B.shot("".join(cells), 2048, 1420, TMP / "sheet.png")
    im = Image.open(TMP / "sheet.png").convert("RGB")
    for i, th in enumerate(("light", "dark")):
        im.crop((i*1024, 0, i*1024+1024, 1024)).save(d / f"icon_{th}.png")
        im.crop((i*130, 1024, i*130+110, 1134)).save(d / f"circle110_{th}.png")
        im.crop((300+i*70, 1024, 340+i*70, 1064)).save(d / f"circle40_{th}.png")
        im.crop((i*1024, 1160, i*1024+1000, 1400)).save(d / f"horizontal_{th}.png")

def card(title, l1, l2, fn, pid):
    nm = PAL[pid][0]
    hx = " / ".join(PAL[pid][1][1:])
    dk = theme(pid, "dark")
    return f'''<div style="width:620px;background:#fff;border-radius:20px;padding:20px">
<div style="font-weight:900;font-size:28px;color:#2b2b2b">{title}</div>
<div style="font-weight:700;font-size:16px;color:#6b6b6b;margin-top:6px;line-height:1.5;height:48px">第一層：{l1}<br>第二層：{l2}</div>
<div style="font-weight:700;font-size:15px;color:#333;margin-top:6px">色調 {pid}　{nm}　<span style="color:#888">{hx}</span></div>
<div style="display:flex;gap:14px;margin-top:10px;align-items:center">
<div style="border-radius:30px;overflow:hidden;flex:none">{icon(fn, pid, "light", 176)}</div><div style="border-radius:30px;overflow:hidden;flex:none">{icon(fn, pid, "dark", 176)}</div>
<div style="display:flex;flex-direction:column;gap:10px">
<div style="display:flex;gap:10px;align-items:center;padding:6px;background:#fff;border:1px solid #e5e5e5;border-radius:12px">{circle(fn,pid,"light",110)}{circle(fn,pid,"light",40)}</div>
<div style="display:flex;gap:10px;align-items:center;padding:6px;background:{dk['page']};border-radius:12px">{circle(fn,pid,"dark",110)}{circle(fn,pid,"dark",40)}</div>
</div></div>
<div style="display:flex;gap:12px;margin-top:12px"><div style="width:280px;height:67px;overflow:hidden;border-radius:8px;border:1px solid #eee"><div style="transform:scale(.28);transform-origin:0 0">{horiz(fn,pid,'light')}</div></div>
<div style="width:280px;height:67px;overflow:hidden;border-radius:8px"><div style="transform:scale(.28);transform-origin:0 0">{horiz(fn,pid,'dark')}</div></div></div></div>'''

def overview_styles():
    cards = [card(t, a, b, fn, pid) for (_, t, fn, a, b, pid) in STY]
    html = (f'<div style="width:2620px;background:#EDEAE4;padding:40px;display:grid;grid-template-columns:repeat(4,620px);gap:30px">'
            f'<div style="grid-column:1/5;font-weight:900;font-size:42px;color:#2b2b2b">哩股哩股 LOGO 第四輪　八種風格（各配最適合的色調）　·　圓形 110／40 為實際像素</div>{"".join(cards)}</div>')
    B.shot(html, 2620, 1180, TMP / "ov1.png")
    Image.open(TMP / "ov1.png").convert("RGB").save(R4 / "overview_styles.png")

def overview_palettes(picks):
    pids = list(PAL)
    head = "".join(f'<div style="width:190px;text-align:center;font-weight:900;font-size:19px;color:#2b2b2b;line-height:1.3">{p}　{PAL[p][0]}<br><span style="font-weight:700;font-size:13px;color:#888">{PAL[p][1][1]}／{PAL[p][1][2]}</span></div>' for p in pids)
    rows = ""
    for (sid, t, fn, a, b, _) in picks:
        cells = ""
        for p in pids:
            dk = theme(p, "dark")
            cells += f'''<div style="width:190px;display:flex;flex-direction:column;align-items:center;gap:8px">
<div style="flex:none;border-radius:30px;overflow:hidden;box-shadow:0 0 0 1px #0001">{icon(fn,p,"light",150)}</div>
<div style="flex:none;border-radius:30px;overflow:hidden">{icon(fn,p,"dark",150)}</div>
<div style="flex:none;display:flex;gap:10px;align-items:center">{circle(fn,p,"light",40)}<div style="padding:4px;background:{dk['page']};border-radius:24px">{circle(fn,p,"dark",40)}</div></div></div>'''
        rows += f'<div style="display:flex;gap:12px;align-items:flex-start"><div style="width:130px;font-weight:900;font-size:22px;color:#2b2b2b;padding-top:60px;line-height:1.3">{t}</div>{cells}</div>'
    html = (f'<div style="width:1850px;background:#EDEAE4;padding:36px 40px;display:flex;flex-direction:column;gap:26px">'
            f'<div style="font-weight:900;font-size:38px;color:#2b2b2b">三個推薦風格 × 八組色調　·　每格上到下：淺底方形、深底方形、IG 圓形 40px（淺／深）</div>'
            f'<div style="display:flex;gap:12px"><div style="width:130px"></div>{head}</div>{rows}</div>')
    B.shot(html, 1850, 1480, TMP / "ov2.png")
    Image.open(TMP / "ov2.png").convert("RGB").save(R4 / "overview_palettes.png")

if __name__ == "__main__":
    for (sid, t, fn, a, b, pid) in STY:
        export_style(sid, fn, pid); print("ok", sid)
    overview_styles()
    pick = sys.argv[2].split(",") if len(sys.argv) > 2 else ["s5_字標連字", "s3_圓潤軟糖", "s6_徽章"]
    overview_palettes([s for k in pick for s in STY if s[0] == k])
    print("done")
