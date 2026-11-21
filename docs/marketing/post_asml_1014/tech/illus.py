"""可重用科技插畫（SVG 字串 → cairosvg 算圖）。全部是「示意圖，非實際構造」。
每支函式回傳 (svg 字串, 寬, 高)；座標用自己的 viewBox，render() 依目標像素縮放。
色票＝Creamy Tech Lab：奶油白／奶油黃／蜜桃粉／珊瑚橘／可可棕／深線條／科技藍／湖水青／薄荷綠。
"""
import io, math
import cairosvg
from PIL import Image

CREAM = "#FFF8EF"; YEL = "#FFE5A3"; PEACH = "#F6B299"; CORAL = "#EC886A"; COCOA = "#53362F"
INK = "#251713"; BLUE = "#7DADDE"; AQUA = "#8EDBD4"; MINT = "#BDE4BE"; VIO = "#9C86E0"; LILAC = "#E4DBFA"
SW = 5  # 主描邊


def render(svg, w, h):
    png = cairosvg.svg2png(bytestring=svg.encode("utf-8"), output_width=int(w), output_height=int(h))
    return Image.open(io.BytesIO(png)).convert("RGBA")


def _wrap(vw, vh, body, defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vw} {vh}" width="{vw}" height="{vh}">'
            f'<defs>{COMMON_DEFS}{defs}</defs>{body}</svg>')


COMMON_DEFS = f"""
<linearGradient id="gMetal" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#EFE3D4"/></linearGradient>
<linearGradient id="gMetalSide" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#E6D6C4"/><stop offset="1" stop-color="#D2BFAA"/></linearGradient>
<linearGradient id="gTop" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#F7EEE2"/></linearGradient>
<linearGradient id="gGlass" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#CFE4F7"/><stop offset="0.55" stop-color="{BLUE}"/><stop offset="1" stop-color="#5E8FC4"/></linearGradient>
<linearGradient id="gWafer" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#E9EEF6"/><stop offset="0.45" stop-color="#B9C6DA"/><stop offset="0.7" stop-color="#D9E1EE"/><stop offset="1" stop-color="#8E9FBA"/></linearGradient>
<linearGradient id="gBeam" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{VIO}" stop-opacity="0.85"/><stop offset="1" stop-color="#C9B8F5" stop-opacity="0.55"/></linearGradient>
<linearGradient id="gCoral" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F6A88C"/><stop offset="1" stop-color="{CORAL}"/></linearGradient>
<linearGradient id="gYel" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFF0C7"/><stop offset="1" stop-color="#FFD877"/></linearGradient>
<linearGradient id="gAqua" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#C4F0EB"/><stop offset="1" stop-color="{AQUA}"/></linearGradient>
<linearGradient id="gBlue" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#B9D5F0"/><stop offset="1" stop-color="{BLUE}"/></linearGradient>
<linearGradient id="gMint" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#E2F4E2"/><stop offset="1" stop-color="{MINT}"/></linearGradient>
<linearGradient id="gPeach" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FBD3C3"/><stop offset="1" stop-color="{PEACH}"/></linearGradient>
<radialGradient id="gPlasma"><stop offset="0" stop-color="#FFFFFF"/><stop offset="0.25" stop-color="#FFF3B0"/><stop offset="0.55" stop-color="#C9A8FF" stop-opacity="0.85"/><stop offset="1" stop-color="{VIO}" stop-opacity="0"/></radialGradient>
<radialGradient id="gGlow"><stop offset="0" stop-color="#FFFFFF" stop-opacity="0.95"/><stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></radialGradient>
<radialGradient id="gDrop" cx="0.35" cy="0.3"><stop offset="0" stop-color="#FFFFFF"/><stop offset="0.5" stop-color="#C9CED6"/><stop offset="1" stop-color="#7E8794"/></radialGradient>
<linearGradient id="gMirror" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F5F1FF"/><stop offset="1" stop-color="#B9A9E8"/></linearGradient>
<pattern id="pHatch" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="14" height="14" fill="{YEL}"/><rect width="6" height="14" fill="#FFD36B"/></pattern>
"""


def _ln(pts, stroke=INK, w=SW, fill="none", extra=""):
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round" {extra}/>'


def _poly(pts, fill, stroke=INK, w=SW, extra=""):
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + " Z"
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{w}" stroke-linejoin="round" {extra}/>'


def _shadow(cx, cy, rx, ry, op=0.16):
    return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{COCOA}" opacity="{op}"/>'


def _iso_box(x, y, w, h, dx, dy, front="url(#gMetal)", top="url(#gTop)", side="url(#gMetalSide)", r=0):
    """前面左上 (x,y)，寬 w 高 h，往右上縱深 (dx,-dy)。"""
    s = _poly([(x, y), (x + dx, y - dy), (x + w + dx, y - dy), (x + w, y)], top)
    s += _poly([(x + w, y), (x + w + dx, y - dy), (x + w + dx, y + h - dy), (x + w, y + h)], side)
    s += f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{front}" stroke="{INK}" stroke-width="{SW}" stroke-linejoin="round"/>'
    return s


def _wafer_disk(cx, cy, rx, ry, thick=10, grid=True, die_fill="#9FB3D1"):
    s = f'<ellipse cx="{cx}" cy="{cy + thick}" rx="{rx}" ry="{ry}" fill="#7F8EA8" stroke="{INK}" stroke-width="{SW}"/>'
    s += f'<rect x="{cx - rx}" y="{cy}" width="{2 * rx}" height="{thick}" fill="#7F8EA8"/>'
    s += f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="url(#gWafer)" stroke="{INK}" stroke-width="{SW}"/>'
    if grid:
        clip = f"cw{int(cx)}{int(cy)}"
        s += f'<clipPath id="{clip}"><ellipse cx="{cx}" cy="{cy}" rx="{rx * 0.9}" ry="{ry * 0.9}"/></clipPath><g clip-path="url(#{clip})">'
        n = 7
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                px = cx + i * rx * 0.2 + j * rx * 0.0
                py = cy + j * ry * 0.2
                s += f'<rect x="{px - rx * 0.085:.1f}" y="{py - ry * 0.085:.1f}" width="{rx * 0.17:.1f}" height="{ry * 0.17:.1f}" rx="2" fill="{die_fill}" opacity="0.55"/>'
        s += "</g>"
        s += f'<path d="M{cx - rx * 0.6},{cy - ry * 0.55} Q{cx},{cy - ry * 1.05} {cx + rx * 0.55},{cy - ry * 0.6}" stroke="#FFFFFF" stroke-width="6" fill="none" opacity="0.8" stroke-linecap="round"/>'
    return s


# ─────────────────────────── 1. EUV 曝光機外觀（封面主視覺）
def euv_machine():
    vw, vh = 960, 640
    b = _shadow(500, 598, 430, 34)
    # 背景電路線（手繪感）
    b += f'<g opacity="0.5" stroke="{BLUE}" stroke-width="4" fill="none" stroke-linecap="round">'
    b += '<path d="M40,120 H170 V60 H300"/><path d="M820,70 H900 V170"/><path d="M60,250 H120"/>'
    b += "</g>"
    for x, y in [(300, 60), (40, 120), (900, 170), (60, 250), (120, 250)]:
        b += f'<circle cx="{x}" cy="{y}" r="9" fill="{CREAM}" stroke="{BLUE}" stroke-width="4"/>'
    # 光源模組（左）
    b += _iso_box(30, 330, 190, 240, 46, 34)
    b += f'<rect x="58" y="362" width="134" height="80" rx="16" fill="url(#gPeach)" stroke="{INK}" stroke-width="4"/>'
    b += f'<circle cx="125" cy="402" r="26" fill="url(#gPlasma)"/><circle cx="125" cy="402" r="9" fill="#FFFFFF"/>'
    for i in range(4):
        b += f'<rect x="62" y="{466 + i * 22}" width="126" height="9" rx="4.5" fill="#D9C7B3"/>'
    # 連接管（有環節）
    b += f'<rect x="218" y="410" width="92" height="56" rx="14" fill="url(#gMetal)" stroke="{INK}" stroke-width="{SW}"/>'
    for x in (238, 262, 286):
        b += f'<rect x="{x}" y="404" width="12" height="68" rx="6" fill="#E9DCCB" stroke="{INK}" stroke-width="3.5"/>'
    # 主機殼
    b += _iso_box(300, 200, 520, 370, 90, 62, r=10)
    # 頂部模組（光學艙）
    b += _iso_box(420, 120, 260, 82, 60, 40)
    b += f'<rect x="440" y="140" width="220" height="44" rx="12" fill="url(#gAqua)" stroke="{INK}" stroke-width="4"/>'
    for i in range(6):
        b += f'<rect x="{452 + i * 34}" y="152" width="20" height="20" rx="5" fill="#FFFFFF" opacity="0.75"/>'
    # 前面板：觀察窗
    b += f'<rect x="336" y="236" width="300" height="196" rx="26" fill="url(#gGlass)" stroke="{INK}" stroke-width="{SW}"/>'
    # 窗內：光束→晶圓
    b += _poly([(380, 262), (470, 262), (520, 360), (470, 360)], "url(#gBeam)", stroke="none", w=0)
    b += _wafer_disk(500, 380, 92, 24, thick=8, grid=True)
    b += f'<path d="M352,252 Q370,244 392,250" stroke="#FFFFFF" stroke-width="7" fill="none" opacity="0.9" stroke-linecap="round"/>'
    b += f'<rect x="552" y="256" width="62" height="16" rx="8" fill="#FFFFFF" opacity="0.55"/>'
    # 右側：控制面板
    b += f'<rect x="660" y="236" width="132" height="196" rx="20" fill="url(#gTop)" stroke="{INK}" stroke-width="4"/>'
    for i, c in enumerate([MINT, YEL, CORAL]):
        b += f'<circle cx="{690 + i * 36}" cy="268" r="12" fill="{c}" stroke="{INK}" stroke-width="3.5"/><circle cx="{686 + i * 36}" cy="264" r="3.5" fill="#FFFFFF"/>'
    b += f'<rect x="680" y="298" width="92" height="56" rx="10" fill="#2E3B55" stroke="{INK}" stroke-width="3.5"/>'
    b += _ln([(690, 340), (708, 322), (724, 332), (744, 310), (762, 318)], stroke=AQUA, w=4)
    for i in range(3):
        b += f'<rect x="680" y="{372 + i * 18}" width="92" height="8" rx="4" fill="#D9C7B3"/>'
    # 下方散熱格柵
    for i in range(9):
        b += f'<rect x="{340 + i * 52}" y="470" width="34" height="74" rx="10" fill="#EFE2D2" stroke="{INK}" stroke-width="3"/>'
    # 邊緣高光
    b += f'<path d="M312,212 H808" stroke="#FFFFFF" stroke-width="5" opacity="0.9" stroke-linecap="round"/>'
    # 腳座
    for x in (330, 560, 780):
        b += f'<rect x="{x}" y="566" width="40" height="22" rx="6" fill="{COCOA}" stroke="{INK}" stroke-width="3"/>'
    # 晶片接點裝飾
    b += f'<g transform="translate(860,300)"><rect x="0" y="0" width="76" height="76" rx="12" fill="url(#gYel)" stroke="{INK}" stroke-width="4"/>'
    b += f'<rect x="18" y="18" width="40" height="40" rx="7" fill="{COCOA}"/>'
    for k in range(3):
        b += f'<rect x="{14 + k * 20}" y="-12" width="8" height="12" fill="{INK}"/><rect x="{14 + k * 20}" y="76" width="8" height="12" fill="{INK}"/>'
    b += "</g>"
    return _wrap(vw, vh, b), vw, vh


# ─────────────────────────── 2. EUV 剖面示意（光源→反射鏡→光罩→晶圓）
def euv_cross():
    vw, vh = 1000, 620
    b = f'<rect x="8" y="8" width="984" height="604" rx="40" fill="#F1F4FB" stroke="{INK}" stroke-width="{SW}"/>'
    b += f'<rect x="26" y="26" width="948" height="568" rx="30" fill="none" stroke="{BLUE}" stroke-width="4" stroke-dasharray="14 12"/>'
    # 光源艙（左下）
    b += f'<rect x="56" y="300" width="300" height="270" rx="30" fill="#FBEFE6" stroke="{INK}" stroke-width="4"/>'
    # 收集鏡（橢圓碗）
    b += f'<path d="M110,350 Q70,440 110,530" stroke="{INK}" stroke-width="22" fill="none" stroke-linecap="round"/>'
    b += f'<path d="M110,350 Q70,440 110,530" stroke="url(#gMirror)" stroke-width="14" fill="none" stroke-linecap="round"/>'
    # 錫滴產生器（上）＋錫滴
    b += f'<rect x="196" y="300" width="44" height="46" rx="10" fill="url(#gMetal)" stroke="{INK}" stroke-width="4"/>'
    for i, y in enumerate([370, 398, 426]):
        b += f'<circle cx="218" cy="{y}" r="8" fill="url(#gDrop)" stroke="{INK}" stroke-width="3"/>'
    # 雷射（右下射入）
    b += f'<path d="M340,560 L230,452" stroke="{CORAL}" stroke-width="16" stroke-linecap="round" opacity="0.35"/>'
    b += f'<path d="M340,560 L230,452" stroke="{CORAL}" stroke-width="7" stroke-linecap="round"/>'
    b += f'<rect x="318" y="540" width="40" height="40" rx="10" fill="url(#gCoral)" stroke="{INK}" stroke-width="4"/>'
    # 電漿
    b += f'<circle cx="218" cy="448" r="48" fill="url(#gPlasma)"/><circle cx="218" cy="448" r="10" fill="#FFFFFF"/>'
    # EUV 光束：收集鏡 → 中間焦點 → M1 → 光罩 → M2 → 晶圓
    beam = [((110, 360), (110, 520), (392, 300)),]
    b += _poly([(112, 372), (112, 508), (392, 300)], "url(#gBeam)", stroke="none", w=0)
    b += _poly([(380, 292), (404, 300), (540, 116), (500, 104)], "url(#gBeam)", stroke="none", w=0)   # → M1
    b += _poly([(520, 110), (540, 122), (650, 100), (640, 76)], "url(#gBeam)", stroke="none", w=0)    # M1 → 光罩
    b += _poly([(650, 92), (668, 84), (770, 300), (744, 306)], "url(#gBeam)", stroke="none", w=0)     # 光罩 → M2
    b += _poly([(744, 306), (772, 300), (830, 470), (800, 474)], "url(#gBeam)", stroke="none", w=0)   # M2 → 晶圓
    # 多層反射鏡 M1、M2（鉬矽多層：條紋）
    def mirror(cx, cy, ang):
        s = f'<g transform="translate({cx},{cy}) rotate({ang})"><rect x="-58" y="-16" width="116" height="34" rx="9" fill="#FFFFFF" stroke="{INK}" stroke-width="4"/>'
        for k in range(5):
            s += f'<rect x="-52" y="{-11 + k * 6}" width="104" height="3.4" fill="{VIO if k % 2 == 0 else BLUE}" opacity="0.85"/>'
        return s + "</g>"
    b += mirror(512, 92, -18) + mirror(776, 318, 30)
    # 光罩（上，反射式）
    b += f'<g transform="translate(600,34)"><rect x="0" y="0" width="150" height="46" rx="8" fill="url(#gYel)" stroke="{INK}" stroke-width="4"/>'
    for k in range(6):
        b += f'<rect x="{12 + k * 22}" y="12" width="12" height="22" rx="3" fill="{COCOA}" opacity="0.8"/>'
    b += "</g>"
    # 晶圓台（右下）
    b += f'<rect x="700" y="500" width="250" height="56" rx="16" fill="url(#gMetalSide)" stroke="{INK}" stroke-width="4"/>'
    b += _wafer_disk(824, 482, 104, 26, thick=9)
    # 中間焦點（光源艙出口）
    b += f'<circle cx="392" cy="300" r="26" fill="url(#gGlow)"/><circle cx="392" cy="300" r="7" fill="#FFFFFF" stroke="{VIO}" stroke-width="3"/>'
    # 放大圈：多層反射鏡的膜層（鉬／矽交替）
    b += f'<path d="M512,110 L560,330" stroke="{INK}" stroke-width="3" stroke-dasharray="8 8" opacity="0.6"/>'
    b += f'<clipPath id="cZoom"><circle cx="560" cy="430" r="96"/></clipPath>'
    b += f'<circle cx="560" cy="430" r="104" fill="#FFFFFF" stroke="{INK}" stroke-width="{SW + 2}"/>'
    b += '<g clip-path="url(#cZoom)">'
    for k in range(14):
        y = 340 + k * 14
        b += f'<rect x="460" y="{y}" width="200" height="14" fill="{"#8F7AD6" if k % 2 == 0 else "#DCE9F7"}"/>'
    b += f'<path d="M470,350 L560,420 L650,350" stroke="#FFF3B0" stroke-width="7" fill="none" opacity="0.9" stroke-linejoin="round"/>'
    b += "</g>"
    b += f'<circle cx="560" cy="430" r="96" fill="none" stroke="#FFFFFF" stroke-width="5" opacity="0.7"/>'
    b += f'<path d="M634,506 L668,540" stroke="{COCOA}" stroke-width="18" stroke-linecap="round"/>'
    return _wrap(vw, vh, b), vw, vh


CROSS_BADGES = {  # 編號圓章位置（viewBox 座標）：1 錫滴 2 雷射 3 電漿 4 收集鏡 5 反射鏡 6 光罩 7 晶圓
    1: (268, 384), 2: (378, 516), 3: (164, 470), 4: (80, 330), 5: (448, 132), 6: (776, 58), 7: (880, 576),
}


# ─────────────────────────── 3. 小圖示
def chip_icon():
    vw, vh = 200, 200
    b = _shadow(100, 186, 70, 9)
    for k in range(4):
        for side in range(4):
            x = 52 + k * 28
            if side == 0: b += f'<rect x="{x}" y="22" width="12" height="22" rx="3" fill="{INK}"/>'
            if side == 1: b += f'<rect x="{x}" y="156" width="12" height="22" rx="3" fill="{INK}"/>'
            if side == 2: b += f'<rect x="22" y="{x}" width="22" height="12" rx="3" fill="{INK}"/>'
            if side == 3: b += f'<rect x="156" y="{x}" width="22" height="12" rx="3" fill="{INK}"/>'
    b += f'<rect x="38" y="38" width="124" height="124" rx="20" fill="url(#gYel)" stroke="{INK}" stroke-width="{SW}"/>'
    b += f'<rect x="66" y="66" width="68" height="68" rx="10" fill="{COCOA}"/>'
    b += f'<path d="M74,78 H100 V96 H126" stroke="{AQUA}" stroke-width="4" fill="none"/><circle cx="126" cy="96" r="5" fill="{AQUA}"/>'
    b += f'<path d="M50,54 Q60,46 72,48" stroke="#FFFFFF" stroke-width="5" fill="none" stroke-linecap="round"/>'
    return _wrap(vw, vh, b), vw, vh


def fab_icon():
    vw, vh = 240, 200
    b = _shadow(120, 186, 100, 10)
    b += _iso_box(30, 82, 150, 96, 34, 26)
    b += f'<path d="M30,82 L30,60 L80,40 L80,82" fill="url(#gPeach)" stroke="{INK}" stroke-width="{SW}" stroke-linejoin="round"/>'
    for i in range(3):
        b += f'<rect x="{46 + i * 44}" y="104" width="30" height="28" rx="6" fill="url(#gGlass)" stroke="{INK}" stroke-width="3.5"/>'
    b += f'<rect x="88" y="142" width="34" height="36" rx="6" fill="{COCOA}" stroke="{INK}" stroke-width="3.5"/>'
    b += f'<rect x="196" y="30" width="20" height="70" rx="8" fill="url(#gMetal)" stroke="{INK}" stroke-width="4"/>'
    b += f'<circle cx="206" cy="18" r="10" fill="{AQUA}" opacity="0.6"/>'
    return _wrap(vw, vh, b), vw, vh


def machine_icon():
    vw, vh = 240, 200
    b = _shadow(120, 186, 104, 10)
    b += _iso_box(26, 70, 160, 108, 32, 24, r=8)
    b += f'<rect x="40" y="84" width="94" height="66" rx="14" fill="url(#gGlass)" stroke="{INK}" stroke-width="4"/>'
    b += _poly([(66, 92), (90, 92), (104, 128), (80, 128)], "url(#gBeam)", stroke="none", w=0)
    b += f'<circle cx="160" cy="98" r="9" fill="{MINT}" stroke="{INK}" stroke-width="3"/><circle cx="160" cy="124" r="9" fill="{CORAL}" stroke="{INK}" stroke-width="3"/>'
    return _wrap(vw, vh, b), vw, vh


def server_icon():
    vw, vh = 200, 220
    b = _shadow(100, 206, 76, 9)
    for i in range(3):
        y = 30 + i * 56
        b += f'<rect x="34" y="{y}" width="132" height="48" rx="12" fill="url(#gBlue)" stroke="{INK}" stroke-width="{SW}"/>'
        b += f'<circle cx="58" cy="{y + 24}" r="7" fill="{MINT}" stroke="{INK}" stroke-width="3"/>'
        for k in range(4):
            b += f'<rect x="{82 + k * 18}" y="{y + 14}" width="10" height="20" rx="3" fill="#FFFFFF" opacity="0.8"/>'
    return _wrap(vw, vh, b), vw, vh


def phone_icon():
    vw, vh = 160, 220
    b = _shadow(80, 208, 52, 8)
    b += f'<rect x="30" y="16" width="100" height="184" rx="22" fill="url(#gPeach)" stroke="{INK}" stroke-width="{SW}"/>'
    b += f'<rect x="42" y="36" width="76" height="136" rx="10" fill="url(#gGlass)" stroke="{INK}" stroke-width="3.5"/>'
    b += f'<circle cx="80" cy="186" r="6" fill="{INK}"/>'
    b += f'<path d="M52,60 Q60,52 70,54" stroke="#FFFFFF" stroke-width="5" fill="none" stroke-linecap="round"/>'
    return _wrap(vw, vh, b), vw, vh


def wafer_icon(layers=0, pattern=False, lit=False):
    """製程步驟用：等角晶圓；layers＝上面疊幾層（光阻／圖案），lit＝正在曝光。"""
    vw, vh = 240, 200
    b = _shadow(120, 176, 104, 14)
    b += _wafer_disk(120, 132, 100, 34, thick=12, grid=False)
    cols = [PEACH, AQUA, YEL, MINT]
    for i in range(layers):
        y = 126 - i * 12
        b += f'<ellipse cx="120" cy="{y + 6}" rx="92" ry="30" fill="#00000000"/>'
        b += f'<path d="M28,{y} A92,30 0 0 0 212,{y} L212,{y - 8} A92,30 0 0 1 28,{y - 8} Z" fill="{cols[i % 4]}" stroke="{INK}" stroke-width="3"/>'
        b += f'<ellipse cx="120" cy="{y - 8}" rx="92" ry="30" fill="{cols[i % 4]}" stroke="{INK}" stroke-width="3.5"/>'
    top = 126 - layers * 12 if layers else 132
    if pattern:
        for k in range(-3, 4):
            b += f'<rect x="{112 + k * 22}" y="{top - 22 + abs(k) * 2}" width="12" height="{34 - abs(k) * 5}" rx="3" fill="{COCOA}" opacity="0.85"/>'
    if lit:
        b += _poly([(96, 0), (144, 0), (176, top - 6), (64, top - 6)], "url(#gBeam)", stroke="none", w=0)
        b += f'<ellipse cx="120" cy="{top - 6}" rx="60" ry="16" fill="url(#gGlow)"/>'
    if not layers:
        b += f'<path d="M50,118 Q120,88 190,116" stroke="#FFFFFF" stroke-width="6" fill="none" opacity="0.85" stroke-linecap="round"/>'
    return _wrap(vw, vh, b), vw, vh


def reticle_icon():
    vw, vh = 220, 150
    b = _shadow(110, 138, 90, 8)
    b += _poly([(20, 70), (70, 20), (210, 20), (160, 70)], "url(#gYel)")
    b += _poly([(20, 70), (160, 70), (160, 92), (20, 92)], "#E8C97A")
    b += _poly([(160, 70), (210, 20), (210, 42), (160, 92)], "#D9B55E")
    for k in range(5):
        x = 56 + k * 22
        b += _poly([(x, 60), (x + 12, 48), (x + 22, 48), (x + 10, 60)], COCOA, stroke="none", w=0)
        b += _poly([(x + 18, 42), (x + 26, 34), (x + 36, 34), (x + 28, 42)], COCOA, stroke="none", w=0)
    return _wrap(vw, vh, b), vw, vh


def magnifier_prop():
    """懸空放大鏡（道具放身旁，非手持）。"""
    vw, vh = 220, 220
    b = f'<path d="M140,140 L196,196" stroke="{COCOA}" stroke-width="26" stroke-linecap="round"/>'
    b += f'<path d="M140,140 L196,196" stroke="#8A5A49" stroke-width="14" stroke-linecap="round"/>'
    b += f'<circle cx="92" cy="92" r="70" fill="#DDEEFB" fill-opacity="0.75" stroke="{INK}" stroke-width="{SW + 3}"/>'
    b += f'<circle cx="92" cy="92" r="60" fill="none" stroke="#FFFFFF" stroke-width="4" opacity="0.8"/>'
    b += f'<path d="M52,70 Q62,44 90,38" stroke="#FFFFFF" stroke-width="9" fill="none" stroke-linecap="round"/>'
    return _wrap(vw, vh, b), vw, vh


def tower_icon():
    """前哨瞭望塔（雷達波）。"""
    vw, vh = 260, 340
    b = _shadow(130, 322, 96, 12)
    b += _poly([(96, 320), (112, 150), (148, 150), (164, 320)], "url(#gMetal)")
    for y in (190, 240, 290):
        b += _ln([(106 + (y - 150) * 0.0, y), (154, y)], w=3.5)
    b += _ln([(108, 170), (158, 300)], w=3); b += _ln([(152, 170), (102, 300)], w=3)
    b += f'<rect x="72" y="104" width="116" height="52" rx="16" fill="url(#gCoral)" stroke="{INK}" stroke-width="{SW}"/>'
    b += f'<rect x="92" y="116" width="76" height="26" rx="8" fill="url(#gGlass)" stroke="{INK}" stroke-width="3.5"/>'
    b += f'<path d="M64,104 Q130,60 196,104 Z" fill="url(#gYel)" stroke="{INK}" stroke-width="{SW}" stroke-linejoin="round"/>'
    b += f'<rect x="125" y="40" width="10" height="34" rx="5" fill="{INK}"/><circle cx="130" cy="38" r="12" fill="{AQUA}" stroke="{INK}" stroke-width="4"/>'
    for r, op in ((34, 0.9), (58, 0.6), (82, 0.35)):
        b += f'<path d="M{130 + r * 0.7:.0f},{38 - r * 0.7:.0f} A{r},{r} 0 0 1 {130 + r:.0f},{38:.0f}" stroke="{BLUE}" stroke-width="6" fill="none" stroke-linecap="round" opacity="{op}"/>'
        b += f'<path d="M{130 - r * 0.7:.0f},{38 - r * 0.7:.0f} A{r},{r} 0 0 0 {130 - r:.0f},{38:.0f}" stroke="{BLUE}" stroke-width="6" fill="none" stroke-linecap="round" opacity="{op}"/>'
    return _wrap(vw, vh, b), vw, vh


def news_clip():
    """剪報紙（摺角＋膠帶）。文字由 Pillow 疊上。"""
    vw, vh = 900, 380
    b = f'<path d="M24,30 H836 L876,70 V356 H24 Z" fill="#FFFDF8" stroke="{INK}" stroke-width="{SW}" stroke-linejoin="round"/>'
    b += _poly([(836, 30), (836, 70), (876, 70)], "#EADCC8", w=4)
    for y in range(110, 356, 46):
        b += f'<path d="M48,{y} H852" stroke="#F1E2CF" stroke-width="3"/>'
    b += f'<rect x="24" y="30" width="16" height="326" fill="{CORAL}" opacity="0.85"/>'
    b += f'<g transform="translate(70,6) rotate(-6)"><rect width="120" height="38" rx="6" fill="{AQUA}" opacity="0.75"/></g>'
    b += f'<g transform="translate(700,330) rotate(5)"><rect width="130" height="40" rx="6" fill="{YEL}" opacity="0.9"/></g>'
    return _wrap(vw, vh, b), vw, vh


def calendar_page():
    vw, vh = 300, 330
    b = _shadow(150, 316, 116, 10)
    b += f'<rect x="20" y="40" width="260" height="270" rx="30" fill="#FFFFFF" stroke="{INK}" stroke-width="{SW}"/>'
    b += f'<path d="M20,110 V70 A30,30 0 0 1 50,40 H250 A30,30 0 0 1 280,70 V110 Z" fill="url(#gCoral)" stroke="{INK}" stroke-width="{SW}" stroke-linejoin="round"/>'
    for x in (80, 220):
        b += f'<rect x="{x - 9}" y="14" width="18" height="50" rx="9" fill="{COCOA}" stroke="{INK}" stroke-width="3"/>'
    b += f'<circle cx="150" cy="208" r="80" fill="none" stroke="{CORAL}" stroke-width="7" stroke-dasharray="40 10" opacity="0.9"/>'
    return _wrap(vw, vh, b), vw, vh


def iso_slab(fill_id, w=560, label_room=True):
    vw, vh = w + 120, 170
    b = _poly([(20, 70), (110, 20), (w + 110, 20), (w + 20, 70)], "url(#gTop)")
    b += _poly([(w + 20, 70), (w + 110, 20), (w + 110, 100), (w + 20, 150)], "url(#gMetalSide)")
    b += f'<rect x="20" y="70" width="{w}" height="80" rx="14" fill="url(#{fill_id})" stroke="{INK}" stroke-width="{SW}"/>'
    b += f'<path d="M40,84 H{w - 20}" stroke="#FFFFFF" stroke-width="5" opacity="0.7" stroke-linecap="round"/>'
    return _wrap(vw, vh, b), vw, vh


def gauge(lo, hi, maxv=100):
    """半圓儀表：0~maxv，lo~hi 那段塗亮。"""
    vw, vh = 400, 230
    cx, cy, r = 200, 206, 170
    def pt(v, rr):
        a = math.pi * (1 - v / maxv)
        return cx + rr * math.cos(a), cy - rr * math.sin(a)
    b = f'<path d="M{cx - r},{cy} A{r},{r} 0 0 1 {cx + r},{cy}" stroke="#EADCC8" stroke-width="40" fill="none" stroke-linecap="round"/>'
    x0, y0 = pt(lo, r); x1, y1 = pt(hi, r)
    b += f'<path d="M{cx - r},{cy} A{r},{r} 0 0 1 {x0:.1f},{y0:.1f}" stroke="{MINT}" stroke-width="40" fill="none" stroke-linecap="round"/>'
    b += f'<path d="M{x0:.1f},{y0:.1f} A{r},{r} 0 0 1 {x1:.1f},{y1:.1f}" stroke="{CORAL}" stroke-width="40" fill="none"/>'
    for v in range(0, maxv + 1, 10):
        a, c = pt(v, r - 34), pt(v, r - 24)
        b += _ln([a, c], w=3)
    nx, ny = pt((lo + hi) / 2, r - 46)
    b += _ln([(cx, cy), (nx, ny)], w=8)
    b += f'<circle cx="{cx}" cy="{cy}" r="16" fill="{COCOA}" stroke="{INK}" stroke-width="4"/>'
    return _wrap(vw, vh, b), vw, vh


def paperclip():
    vw, vh = 70, 150
    b = f'<path d="M20,120 V30 A15,15 0 0 1 50,30 V110 A8,8 0 0 1 34,110 V44" stroke="{COCOA}" stroke-width="7" fill="none" stroke-linecap="round"/>'
    return _wrap(vw, vh, b), vw, vh


def arrow_svg(length=120, color=CORAL, thick=14):
    vw, vh = length, thick * 3
    y = vh / 2
    b = f'<path d="M6,{y} H{length - thick * 1.6}" stroke="{INK}" stroke-width="{thick + 8}" stroke-linecap="round"/>'
    b += f'<path d="M6,{y} H{length - thick * 1.6}" stroke="{color}" stroke-width="{thick}" stroke-linecap="round"/>'
    b += _poly([(length - thick * 2.2, 5), (length - 4, y), (length - thick * 2.2, vh - 5)], color, w=4)
    return _wrap(vw, vh, b), vw, vh


def wave(period, width=560, amp=26, color=VIO):
    vw, vh = width, amp * 2 + 20
    pts = []
    n = max(200, int(width / max(period, 1) * 24))
    for i in range(n + 1):
        x = 6 + (width - 12) * i / n
        pts.append((x, vh / 2 - amp * math.sin(2 * math.pi * (x - 6) / period)))
    d = "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in pts)
    sw = 5 if period > 40 else 3.2
    b = f'<path d="{d}" stroke="{color}" stroke-width="{sw + 5}" fill="none" opacity="0.25" stroke-linejoin="round"/>'
    b += f'<path d="{d}" stroke="{color}" stroke-width="{sw}" fill="none" stroke-linejoin="round" stroke-linecap="round"/>'
    return _wrap(vw, vh, b), vw, vh
