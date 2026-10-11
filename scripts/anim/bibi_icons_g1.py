"""比比 G1 批：10 個互動小圈圖示（96×96 透明 PNG，手繪風粗描邊，跟比比同一套配色與描邊）。

做法：每個圖示都是「奶油白圓底＋粗描邊」上面放一個小圖案；SVG 三次 Bézier 以 4 倍繪製再 LANCZOS 縮回 96。
配色同比比：描邊 #1A0907、毛 #FDF5E9、肉掌 #FFB4A0／#F58C78（官方部件總表）。
由 bibi_interact_g1.py --icons 呼叫；也可單獨：python scripts/anim/bibi_icons_g1.py docs/anim/bibi_icons
"""
from __future__ import annotations

import io
import math
import sys
from pathlib import Path

import cairosvg
from PIL import Image

INK = "#1A0907"
FUR = "#FDF5E9"
PAW, PAW_DK, PAW_LT = "#FFB4A0", "#F58C78", "#FFD3C4"
GRASS, GRASS_DK = "#9CC95E", "#6FA03C"
HEART = "#F0607A"
GOLD = "#FFD96B"
SW = 4.2   # 圖案描邊（96 座標）


def st(w=SW):
    return f'stroke="{INK}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"'


def badge(inner, bg=FUR):
    return (f'<circle cx="48" cy="49.5" r="43" fill="#E9D2BC" opacity="0.0"/>'
            f'<circle cx="48" cy="48" r="43" fill="{bg}" {st(4.6)}/>'
            f'<path d="M 17,66 Q 48,88 79,66" fill="none" stroke="#F3DCC4" stroke-width="5" stroke-linecap="round" opacity="0.9"/>'
            + inner)


def ic_hand():
    # 肉球面：大掌墊＋上面三顆小肉球，外面一圈蜜桃粉
    return (f'<path d="M 28,56 C 24,40 34,28 48,28 C 62,28 72,40 68,56 C 66,70 58,76 48,76 C 38,76 30,70 28,56 Z" fill="{PAW}" {st()}/>'
            f'<path d="M 36,58 C 36,50 41,47 48,47 C 55,47 60,50 60,58 C 60,66 55,69 48,69 C 41,69 36,66 36,58 Z" fill="{PAW_DK}" {st(3.2)}/>'
            + "".join(f'<ellipse cx="{x}" cy="{y}" rx="5.2" ry="6.4" fill="{PAW_DK}" {st(3.0)} transform="rotate({r},{x},{y})"/>'
                      for x, y, r in ((33, 40, -22), (48, 34, 0), (63, 40, 22)))
            + f'<ellipse cx="41" cy="52" rx="2.6" ry="1.6" fill="{PAW_LT}" transform="rotate(-30,41,52)"/>')


def blade(b, t, w, bend):
    dx, dy = t[0] - b[0], t[1] - b[1]
    L = math.hypot(dx, dy)
    nx, ny = -dy / L, dx / L
    q1 = (b[0] + dx * .3 + nx * (w + bend), b[1] + dy * .3 + ny * (w + bend))
    q2 = (b[0] + dx * .72 + nx * (w * .5 + bend), b[1] + dy * .72 + ny * (w * .5 + bend))
    r1 = (b[0] + dx * .3 - nx * (w - bend), b[1] + dy * .3 - ny * (w - bend))
    r2 = (b[0] + dx * .72 - nx * (w * .5 - bend), b[1] + dy * .72 - ny * (w * .5 - bend))
    return (f'<path d="M {b[0]:.1f},{b[1]:.1f} C {q1[0]:.1f},{q1[1]:.1f} {q2[0]:.1f},{q2[1]:.1f} {t[0]:.1f},{t[1]:.1f} '
            f'C {r2[0]:.1f},{r2[1]:.1f} {r1[0]:.1f},{r1[1]:.1f} {b[0]:.1f},{b[1]:.1f} Z" fill="{GRASS}" {st(3.6)}/>'
            f'<path d="M {b[0]:.1f},{b[1]:.1f} Q {(b[0]+t[0])/2+bend:.1f},{(b[1]+t[1])/2:.1f} {t[0]:.1f},{t[1]:.1f}" fill="none" stroke="{GRASS_DK}" stroke-width="2" stroke-linecap="round"/>')


def ic_grass():
    return (blade((46, 70), (26, 24), 5.5, -4) + blade((50, 70), (70, 26), 5.5, 4) + blade((48, 70), (48, 18), 6.2, 0)
            + f'<path d="M 38,68 Q 48,63 58,68 L 56,76 Q 48,81 40,76 Z" fill="#F7C46B" {st(3.6)}/>')


def ic_ball():
    cx, cy, r = 48, 46, 22
    return (f'<clipPath id="bc"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#F2705E"/>'
            f'<g clip-path="url(#bc)"><path d="M 20,40 Q 48,28 76,46 L 76,56 Q 48,40 20,50 Z" fill="#FFFFFF"/>'
            f'<ellipse cx="{cx}" cy="{cy+22}" rx="26" ry="12" fill="#D9503F" opacity="0.7"/></g>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" {st(4.2)}/>'
            f'<ellipse cx="40" cy="36" rx="4" ry="2.6" fill="#FFFFFF" transform="rotate(-35,40,36)"/>'
            f'<path d="M 34,77 Q 48,81 62,77" fill="none" {st(3.4)}/>')


def ic_spin():
    # 圓弧箭頭（逆時針轉 300°）：先畫粗黑再畫黃色，形成描邊
    def arc(r, a0, a1):
        p0 = (48 + r * math.cos(math.radians(a0)), 48 + r * math.sin(math.radians(a0)))
        p1 = (48 + r * math.cos(math.radians(a1)), 48 + r * math.sin(math.radians(a1)))
        return f"M {p0[0]:.1f},{p0[1]:.1f} A {r},{r} 0 1 1 {p1[0]:.1f},{p1[1]:.1f}"
    d = arc(21, -70, 205)
    tip = (48 + 21 * math.cos(math.radians(205)), 48 + 21 * math.sin(math.radians(205)))
    # 箭頭三角形（指向切線方向）
    a = math.radians(205)
    tx, ty = -math.sin(a), math.cos(a)      # 順時針（角度增加）方向的切線
    nx, ny = math.cos(a), math.sin(a)
    head = [(tip[0] + tx * 15, tip[1] + ty * 15), (tip[0] + nx * 12, tip[1] + ny * 12), (tip[0] - nx * 12, tip[1] - ny * 12)]
    hd = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in head) + " Z"
    return (f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="13" stroke-linecap="round"/>'
            f'<path d="{d}" fill="none" stroke="{GOLD}" stroke-width="6" stroke-linecap="round"/>'
            f'<path d="{hd}" fill="{GOLD}" {st(4)}/>'
            f'<circle cx="48" cy="48" r="4" fill="{PAW_DK}" {st(2.6)}/>')


def ic_highfive():
    # 往上舉的小肉掌（略斜）＋三條放射線＋星
    return (f'<g transform="rotate(-14,46,56)">'
            f'<path d="M 30,60 C 26,44 36,32 46,32 C 58,32 66,44 62,60 C 60,72 54,78 46,78 C 38,78 32,72 30,60 Z" fill="{PAW}" {st()}/>'
            f'<path d="M 36,62 C 36,55 40,52 46,52 C 52,52 56,55 56,62 C 56,69 52,72 46,72 C 40,72 36,69 36,62 Z" fill="{PAW_DK}" {st(3.0)}/>'
            + "".join(f'<ellipse cx="{x}" cy="{y}" rx="4.6" ry="5.8" fill="{PAW_DK}" {st(2.8)} transform="rotate({r},{x},{y})"/>'
                      for x, y, r in ((35, 44, -22), (46, 38, 0), (57, 44, 22)))
            + '</g>'
            f'<path d="M 66,26 L 70,20 M 73,35 L 79,32 M 59,22 L 60,15" fill="none" {st(3.8)}/>'
            f'<path d="M 18,30 L 20.5,35 L 26,36 L 21.5,39.5 L 23,45 L 18,41.5 L 13,45 L 14.5,39.5 L 10,36 L 15.5,35 Z" fill="{GOLD}" {st(3)}/>')


def ic_music():
    return (f'<path d="M 36,28 L 66,22 L 66,32 L 36,38 Z" fill="{INK}" {st(3)}/>'
            f'<path d="M 36,32 L 36,64 M 66,26 L 66,58" fill="none" {st(4.4)}/>'
            f'<ellipse cx="29.5" cy="66" rx="9" ry="7" fill="#F7A7B8" {st(4)} transform="rotate(-18,29.5,66)"/>'
            f'<ellipse cx="59.5" cy="60" rx="9" ry="7" fill="#F7A7B8" {st(4)} transform="rotate(-18,59.5,60)"/>'
            f'<ellipse cx="27" cy="64" rx="2.6" ry="1.6" fill="#FFFFFF" transform="rotate(-30,27,64)"/>'
            f'<ellipse cx="57" cy="58" rx="2.6" ry="1.6" fill="#FFFFFF" transform="rotate(-30,57,58)"/>')


def ic_heart():
    s = 23
    pts = [(0, 0.9), (-0.2, 0.7), (-1.0, 0.25), (-1.0, -0.3), (-1.0, -0.85), (-0.35, -1.0), (0, -0.5),
           (0.35, -1.0), (1.0, -0.85), (1.0, -0.3), (1.0, 0.25), (0.2, 0.7), (0, 0.9)]
    T = [(48 + x * s, 49 + y * s) for x, y in pts]
    p = lambda q: f"{q[0]:.1f},{q[1]:.1f}"
    d = (f"M {p(T[0])} C {p(T[1])} {p(T[2])} {p(T[3])} C {p(T[4])} {p(T[5])} {p(T[6])} "
         f"C {p(T[7])} {p(T[8])} {p(T[9])} C {p(T[10])} {p(T[11])} {p(T[12])} Z")
    return (f'<path d="{d}" fill="{HEART}" {st(4.6)}/>'
            f'<ellipse cx="36" cy="37" rx="4.6" ry="3" fill="#FFFFFF" opacity="0.9" transform="rotate(-35,36,37)"/>')


def ic_moon():
    return (f'<path d="M 58,20 C 40,22 28,36 28,52 C 28,68 40,78 56,78 C 64,78 70,75 74,71 C 54,70 44,58 46,44 C 47,34 52,26 58,20 Z" fill="{GOLD}" {st(4.4)}/>'
            f'<circle cx="38" cy="56" r="2.6" fill="#F2BE4A"/><circle cx="46" cy="68" r="2.2" fill="#F2BE4A"/>'
            f'<path d="M 72,26 L 74.6,32 L 81,33 L 76,37.5 L 77.5,44 L 72,40.5 L 66.5,44 L 68,37.5 L 63,33 L 69.4,32 Z" fill="#FFF3B8" {st(3)}/>')


def ic_camera():
    return (f'<path d="M 34,34 L 40,26 L 56,26 L 62,34" fill="#BFD9F2" {st(4)}/>'
            f'<rect x="18" y="33" width="60" height="38" rx="9" fill="#BFD9F2" {st(4.4)}/>'
            f'<rect x="22" y="36" width="52" height="9" rx="4" fill="#E4F0FB" opacity="0.9"/>'
            f'<circle cx="48" cy="53" r="12.5" fill="#FFFFFF" {st(4.2)}/>'
            f'<circle cx="48" cy="53" r="6.8" fill="#4F7DB8" {st(3)}/>'
            f'<circle cx="45.5" cy="50.5" r="2.2" fill="#FFFFFF"/>'
            f'<circle cx="68" cy="41" r="2.8" fill="{HEART}" {st(2.4)}/>')


def ic_chat():
    return (f'<path d="M 22,30 C 22,24 26,21 32,21 L 64,21 C 70,21 74,24 74,30 L 74,52 C 74,58 70,61 64,61 L 44,61 L 32,73 L 33,61 C 26,61 22,58 22,52 Z" fill="#FFFFFF" {st(4.4)}/>'
            + "".join(f'<circle cx="{x}" cy="41" r="4" fill="{INK}"/>' for x in (36, 48, 60))
            + '<ellipse cx="29" cy="28" rx="3.2" ry="1.8" fill="#DCEBFA" transform="rotate(-25,29,28)"/>')


ICONS = [
    ("hand", "手（摸摸頭）", ic_hand),
    ("grass", "牧草（吃草）", ic_grass),
    ("ball", "球（玩球）", ic_ball),
    ("spin", "旋轉箭頭（轉圈圈）", ic_spin),
    ("highfive", "擊掌手（擊掌）", ic_highfive),
    ("music", "音符（聽音樂）", ic_music),
    ("heart", "愛心（比心）", ic_heart),
    ("moon", "月亮（晚安）", ic_moon),
    ("camera", "相機（拍照）", ic_camera),
    ("chat", "對話泡泡（聊天）", ic_chat),
]


def render_icon(fn, bg=FUR, size=96, ss=4):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size*ss}" height="{size*ss}" viewBox="0 0 96 96">'
           + badge(fn(), bg) + '</svg>')
    png = cairosvg.svg2png(bytestring=svg.encode("utf-8"), output_width=size * ss, output_height=size * ss)
    return Image.open(io.BytesIO(png)).convert("RGBA").resize((size, size), Image.LANCZOS)


def make_icons(outdir):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    ims = []
    lines = ["# 比比互動小圈圖示（10 個）", "",
             "- 用途：網頁版客服鈕「比比」互動選單的小圈圖示；每個 96×96 透明 PNG、手繪風粗描邊（#1A0907）、奶油白圓底，與比比同風格。",
             "- 製作：`python scripts/anim/bibi_interact_g1.py --out <scratchpad>/bibi_g --repo-out docs/anim --icons`（`scripts/anim/bibi_icons_g1.py`）。",
             "- 圓底外是透明；不加陰影，深淺主題都可直接用。", "",
             "| 預覽 | 檔名 | 圖示 | 對應互動 |", "|---|---|---|---|"]
    for key, name, fn in ICONS:
        im = render_icon(fn)
        im.save(outdir / f"{key}.png", optimize=True)
        ims.append(im)
        lines.append(f'| <img src="{key}.png" width="48"> | `{key}.png` | {name.split("（")[0]} | {name.split("（")[1].rstrip("）")} |')
    (outdir / "index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    # 檢查圖：洋紅／深／淺三種底（不進 repo，放 outdir 外層由呼叫者決定；這裡放 outdir/_preview.png）
    cell = 120
    sheet = Image.new("RGB", (cell * len(ims), cell * 3), (0, 0, 0))
    for r, bg in enumerate([(255, 0, 255), (14, 22, 40), (244, 247, 252)]):
        for k, im in enumerate(ims):
            tile = Image.new("RGBA", (cell, cell), bg + (255,))
            tile.alpha_composite(im, (12, 12))
            sheet.paste(tile.convert("RGB"), (k * cell, r * cell))
    sheet.save(outdir / "_preview.png")


if __name__ == "__main__":
    make_icons(sys.argv[1] if len(sys.argv) > 1 else "docs/anim/bibi_icons")
