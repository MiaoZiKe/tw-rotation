"""比比四腳版互動動作（10-12 Andy 最高原則重做）：吃草、睡覺／叫醒、哭／被敲、轉圈、拍照（＋之後的球、摸摸…）。

Andy 10-12：「比比是天竺鼠，他是 4 隻腳的，所以所有互動畫面都需要符合真的天竺鼠他會有的，
不可以因為配合互動就改變身體原有設定」。
→ 全部用 `bibi_quad.compose`（原版 Default 像素本體＋四隻獨立小腳），**不畫手掌、不站立**；
  每格跑 `quad_selfcheck`（四腳都在、都在身體下半部、著地格至少兩腳貼地、沒有 paws）。

用法
----
    python scripts/anim/bibi_quad_moves.py --out <scratchpad>/quad --repo-out docs/anim [--only eat_grass,sleep_loop]

輸出（每組）docs/anim/bibi_<名>/：anim.webp（160px ≤60KB）、sheet_12.png、sheet_all.png、storyboard.md、compare_default.png；
<out>/<名>/frames/NN.png（512 透明）、anim512.webp。舊版目錄第一次覆蓋前自動備份成 bibi_<名>_old（已有就 _old2、_old3…）。
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
import bibi_quad as Q  # noqa: E402
import bibi_rig as R  # noqa: E402
import bibi_moves_v2 as V  # noqa: E402

TAU = 2 * math.pi
INK = R.DEF_INK
GROUND = R.FOOT_Y
DEFAULT_END = dict(feet="orig", view="front")
lerp = R.lerp_pose
ease = R.ease


def F(pose, ms, label, **kw):
    return dict(pose=pose, ms=ms, label=label, **kw)


def tween(a, b, n, kind="inout"):
    """a→b 之間 n 格（不含 a、含 b）。"""
    return [lerp(a, b, ease((i + 1) / n, kind)) for i in range(n)]


# ================================================================== 效果小工具
def heart_svg(x, y, s=1.0, rot=0.0, fill="#F2647A") -> str:
    return (f'<g transform="translate({x:.1f},{y:.1f}) rotate({rot:.1f}) scale({s:.3f})">'
            f'<path d="M 0 10 C -4 6 -18 -2 -18 -11 C -18 -19 -8 -22 0 -14 C 8 -22 18 -19 18 -11 C 18 -2 4 6 0 10 Z" '
            f'fill="{fill}" stroke="{INK}" stroke-width="4.2" stroke-linejoin="round"/>'
            f'<ellipse cx="-8" cy="-12" rx="4" ry="2.6" fill="#fff" fill-opacity="0.8" transform="rotate(-30 -8 -12)"/></g>')


def sniff_svg(x, y, k=1.0, side=-1, alpha=1.0) -> str:
    """鼻子前的嗅嗅小弧線（兩道），side=-1 在左邊。"""
    out = ""
    for i in range(2):
        xx = x + side * (10 + 11 * i) * k
        out += (f'<path d="M {xx:.1f} {y-8*k-3*i:.1f} Q {xx+side*6*k:.1f} {y:.1f} {xx:.1f} {y+8*k+3*i:.1f}" fill="none" '
                f'stroke="{INK}" stroke-opacity="{alpha:.2f}" stroke-width="4.2" stroke-linecap="round"/>')
    return out


def zzz_svg(x, y, s=1.0, alpha=1.0, rot=-8) -> str:
    """一個 Z（深藍、粗描）。"""
    k = 13 * s
    return (f'<g transform="translate({x:.1f},{y:.1f}) rotate({rot})" opacity="{alpha:.2f}">'
            f'<path d="M {-k:.1f} {-k:.1f} L {k:.1f} {-k:.1f} L {-k:.1f} {k:.1f} L {k:.1f} {k:.1f}" fill="none" '
            f'stroke="#fff" stroke-width="{7*s+5:.1f}" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="M {-k:.1f} {-k:.1f} L {k:.1f} {-k:.1f} L {-k:.1f} {k:.1f} L {k:.1f} {k:.1f}" fill="none" '
            f'stroke="#26304F" stroke-width="{6*s:.1f}" stroke-linecap="round" stroke-linejoin="round"/></g>')


def music_svg(x, y, s=1.0, rot=0.0) -> str:
    return (f'<g transform="translate({x:.1f},{y:.1f}) rotate({rot:.1f}) scale({s:.3f})">'
            f'<path d="M -4 10 L -4 -18 L 14 -22 L 14 4" fill="none" stroke="{INK}" stroke-width="4.5" stroke-linejoin="round"/>'
            f'<ellipse cx="-9" cy="11" rx="7.5" ry="6" fill="{INK}" transform="rotate(-20 -9 11)"/>'
            f'<ellipse cx="9" cy="5" rx="7.5" ry="6" fill="{INK}" transform="rotate(-20 9 5)"/></g>')


def sparkle_svg(x, y, r=14.0, fill="#FFE07A") -> str:
    """四角閃光。"""
    return (f'<path d="M {x:.1f} {y-r:.1f} Q {x+r*0.18:.1f} {y-r*0.18:.1f} {x+r:.1f} {y:.1f} Q {x+r*0.18:.1f} {y+r*0.18:.1f} '
            f'{x:.1f} {y+r:.1f} Q {x-r*0.18:.1f} {y+r*0.18:.1f} {x-r:.1f} {y:.1f} Q {x-r*0.18:.1f} {y-r*0.18:.1f} {x:.1f} {y-r:.1f} Z" '
            f'fill="{fill}" stroke="{INK}" stroke-width="3.6" stroke-linejoin="round"/>')


# ================================================================== 1. 吃草（草放在地上，低頭湊過去啃）
def blade_svg(ax, ay, bx, by, bend=10.0, w=12.0, head=True, bite=False, flat_head=False) -> str:
    """一根割下來的牧草：從 A（地上那端，有穗）到 B（靠比比嘴那端）。bend＝中段往上拱。"""
    dx, dy = bx - ax, by - ay
    L = math.hypot(dx, dy) or 1
    ux, uy = dx / L, dy / L
    nx, ny = uy, -ux          # 法線（朝上那側）
    if ny > 0:
        nx, ny = -nx, -ny
    mx, my = (ax + bx) / 2 + nx * bend, (ay + by) / 2 + ny * bend
    hw = w / 2
    sw = max(3.0, w * 0.32)
    d = (f"M {ax + nx*hw:.1f} {ay + ny*hw:.1f} Q {mx + nx*hw:.1f} {my + ny*hw:.1f} {bx + nx*hw*0.8:.1f} {by + ny*hw*0.8:.1f} ")
    if bite:
        d += (f"L {bx + ux*3 + nx*hw*0.3:.1f} {by + uy*3 + ny*hw*0.3:.1f} L {bx - ux*2:.1f} {by - uy*2:.1f} "
              f"L {bx + ux*3 - nx*hw*0.3:.1f} {by + uy*3 - ny*hw*0.3:.1f} ")
    else:
        d += f"Q {bx + ux*w:.1f} {by + uy*w:.1f} "
    d += (f"{bx - nx*hw*0.8:.1f} {by - ny*hw*0.8:.1f} Q {mx - nx*hw:.1f} {my - ny*hw:.1f} {ax - nx*hw:.1f} {ay - ny*hw:.1f} Z")
    out = (f'<path d="{d}" fill="#8CCB5E" stroke="{INK}" stroke-width="{sw:.1f}" stroke-linejoin="round"/>'
           f'<path d="M {ax:.1f} {ay:.1f} Q {mx:.1f} {my:.1f} {bx - ux*6:.1f} {by - uy*6:.1f}" fill="none" stroke="#5E9E3A" '
           f'stroke-width="{sw*0.6:.1f}" stroke-linecap="round"/>')
    if head:      # 提摩西草穗（在地上那端）
        hx, hy = (1.0, 0.0) if flat_head else (ux, uy)     # 叼起來時穗平躺在地上（不會插進地面以下）
        ang = math.degrees(math.atan2(-hy, -hx))
        sl = w * 3.2
        cx, cy = ax - hx * sl * 0.38, ay - hy * sl * 0.38
        ticks = "".join(f'<path d="M {-sl*0.5 + sl*f:.1f} {-w*0.8:.1f} l {w*0.25:.1f} {w*0.42:.1f} M {-sl*0.5 + sl*f:.1f} {w*0.8:.1f} '
                        f'l {w*0.25:.1f} {-w*0.42:.1f}" stroke="#7D8F2E" stroke-width="{sw*0.5:.1f}" stroke-linecap="round"/>'
                        for f in (0.25, 0.5, 0.75))
        out = (f'<g transform="translate({cx:.1f},{cy:.1f}) rotate({ang:.1f})"><ellipse rx="{sl*0.6:.1f}" ry="{w*0.78:.1f}" '
               f'fill="#D9D77A" stroke="{INK}" stroke-width="{sw:.1f}"/>{ticks}</g>') + out
    return out


def leaf_svg(x, y, L=34, ang=-150, w=10) -> str:
    r = math.radians(ang)
    ux, uy = math.cos(r), math.sin(r)
    nx, ny = -uy, ux
    tx, ty = x + ux * L, y + uy * L
    return (f'<path d="M {x:.1f} {y:.1f} Q {x + ux*L*0.5 + nx*w:.1f} {y + uy*L*0.5 + ny*w:.1f} {tx:.1f} {ty:.1f} '
            f'Q {x + ux*L*0.5 - nx*w*0.4:.1f} {y + uy*L*0.5 - ny*w*0.4:.1f} {x:.1f} {y:.1f} Z" fill="#9AD46A" stroke="{INK}" '
            f'stroke-width="3.6" stroke-linejoin="round"/>')


def grass_bunch_svg(bx, by, L, lifted=True, bite=False, shadow=True) -> str:
    """一小把牧草（三根）放在地上：靠比比那端 B=(bx,by)（叼起時在嘴裡），另一端躺在地上往左延伸，總長 L。
    L 越來越短＝一截截被吃進去。"""
    if L <= 4:
        return ""
    out = ""
    gy = GROUND - 5
    # 草在地上的影子（跟比比的地面影子同一層的顏色）
    ax = bx - L * (0.92 if lifted else 1.0)
    if shadow:
        out += (f'<ellipse cx="{(ax + bx) / 2:.1f}" cy="{GROUND - 1:.1f}" rx="{max(10, (bx - ax) / 2 + 8):.1f}" ry="6" '
                f'fill="rgb(110,80,60)" fill-opacity="0.22"/>')
    for i, (oy, ox, w) in enumerate(((-3, 6, 14), (2, -4, 16), (6, 12, 13.5))):
        a_x, a_y = ax + ox, gy + oy * 0.6 - 2
        b_x, b_y = bx + ox * 0.15, by + oy * (0.35 if lifted else 0.6)
        if not lifted:
            b_y = gy + oy * 0.6 - 4
        bend = 6 if lifted else 3
        if lifted:
            a_y = min(a_y, gy - 4)
        out += blade_svg(a_x, a_y, b_x, b_y, bend=bend * (1 + 0.3 * i), w=w, head=(L > 60 and i != 1), bite=bite,
                         flat_head=lifted)
    if L > 70:
        out += leaf_svg(ax + L * 0.35, gy - 4, 30, -158, 9)
    return out


def eat_pose(h=0.0, bite=0.0, chew="", eye="default", cheek=0.0, ear=0.0, sq=0.0):
    """側面面向左吃草：h＝低頭深度 0～1（越大臉越低、越往前湊）；bite＝咬下去那一下的往前探。"""
    look = (-6 - 12 * h - 4 * bite, 40 + 52 * h + 6 * bite)
    return dict(view="side", x=R.CX + 62, face_k=1.14, shear=0.1 + 0.12 * h + 0.04 * bite, sy=0.9 - 0.06 * h - sq, sx=1.06 + sq * 0.5,
                look=look, mouth=chew or "nibble_c", eye=eye, cheek=cheek, ear=ear, ear2=ear * 0.7,
                legs={"bl": (6 * h, 0, 0, 0), "br": (6 * h, 0, 0, 0)})


def mouth_at(p):
    pp = {**Q.QDEF, **Q.EARS.get(p.get("view", "front"), {}), **p}
    return Q.feat_world(pp, "mouth")


def clip_eat_grass():
    fr = []
    # 草把：長度一截截變短（從 150 吃到 0）

    def grass(p, L, lifted=True, bite=False):
        mx, my = mouth_at(p)
        if not lifted:
            return [grass_bunch_svg(mx + 6, GROUND - 8, L, lifted=False)]
        return [grass_bunch_svg(mx + 2, my + 4, L, lifted=True, bite=bite)]

    seq = [
        # (pose, ms, label, grass_len, lifted, fx)
        (eat_pose(0.55, 0, "o", "default", 0, -12), 90, "低頭湊近草、鼻子嗅嗅（耳朵前傾）", 96, False, "sniff"),
        (eat_pose(0.75, 0.4, "o", "default", 0, -16), 80, "再湊近一點嗅（鼻子抖）", 96, False, "sniff2"),
        (eat_pose(0.9, 1.0, "nibble_a", "default", 0, -6), 70, "張嘴露門牙咬住草尖、叼起來", 96, True, ""),
        (eat_pose(0.8, 0, "nibble_c", "smile", 0.8, 8), 80, "嚼（臉頰鼓、耳朵抖）", 96, True, "crumb0"),
        (eat_pose(0.82, 0.3, "nibble_d", "smile", 1.1, -4), 80, "嚼（嘴形換邊）草短一截", 92, True, "crumb1"),
        (eat_pose(0.8, 0, "nibble_b", "smile", 0.9, 8), 80, "嚼（半開）", 92, True, ""),
        (eat_pose(0.92, 1.0, "nibble_a", "default", 0.3, -6), 70, "再咬一口（往前湊）", 92, True, ""),
        (eat_pose(0.82, 0, "nibble_c", "smile", 1.1, 8), 80, "嚼、草又短一截", 70, True, "crumb2"),
        (eat_pose(0.84, 0.3, "nibble_d", "smile", 1.2, -4), 80, "嚼（臉頰最鼓）", 70, True, ""),
        (eat_pose(0.94, 1.0, "nibble_a", "default", 0.4, -6), 70, "第三口", 70, True, ""),
        (eat_pose(0.82, 0, "nibble_c", "smile", 1.2, 8), 80, "嚼、草剩一小截", 46, True, "crumb3"),
        (eat_pose(0.86, 0.3, "nibble_d", "smile", 1.2, -4), 80, "嚼嚼", 46, True, ""),
        (eat_pose(0.78, 0.6, "nibble_c", "smile", 1.3, 6), 90, "最後一截吸進去", 22, True, "crumb4"),
        (eat_pose(0.5, 0, "w", "smile", 0.7, 2), 150, "吃完抬頭、滿足瞇眼＋小愛心", 0, True, "heart"),
    ]
    for (p, ms, lab, L, lifted, fx) in seq:
        fxs = []
        mx, my = mouth_at(p)
        if fx.startswith("sniff"):
            fxs.append(sniff_svg(mx - 26, my + 2, 1.0 if fx == "sniff" else 1.15, -1))
        if fx.startswith("crumb"):
            k = int(fx[-1])
            fxs.append(R.crumbs_svg(mx - 30, my + 18, 3, 16, seed=k))
        if fx == "heart":
            fxs.append(heart_svg(R.CX + 120, 196, 1.15, 12))
            fxs.append(heart_svg(R.CX + 160, 150, 0.8, -10))
        fr.append(F(p, ms, lab, props_mid=grass(p, L, lifted, bite=L < 96), fx=fxs))
    # 抬頭轉正 → Default
    up = dict(view="q3", eye="smile", mouth="w", blush=1.25, ear=-4)
    fr.append(F(up, 220, "轉正、瞇眼笑（小愛心往上飄）", fx=[heart_svg(R.CX + 150, 120, 0.9, 8)]))
    fr.append(F(DEFAULT_END, 500, "回 Default"))
    return fr


def make_grass_prop(path):
    """地上的牧草（透明，512）：一小把三根躺在地上的提摩西草。"""
    lay = R.svg_layer(f'<g transform="translate(-40,-120) scale(1.5)">{grass_bunch_svg(300, GROUND - 8, 190, lifted=False, shadow=False)}</g>')
    im = R.finish(lay)
    bb = im.getchannel("A").getbbox()
    c = Image.new("RGBA", (512, 512))
    crop = im.crop(bb)
    c.alpha_composite(crop, ((512 - crop.width) // 2, (512 - crop.height) // 2))
    c.save(path)


# ================================================================== 共用：世界座標
def wpt(p, x, y):
    return R.def_pt({**Q.QDEF, **p}, x, y)


def head_top(p, ox=253.0):
    return wpt(p, ox, V._head_top_y(ox))


def exclaim_svg(x, y, s=1.0, rot=0.0) -> str:
    """驚嚇的「！」（白底粗描邊）。"""
    return (f'<g transform="translate({x:.1f},{y:.1f}) rotate({rot:.1f}) scale({s:.3f})">'
            f'<path d="M -7 -30 L 7 -30 L 4 6 L -4 6 Z" fill="#FFD25A" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>'
            f'<circle cx="0" cy="18" r="6.5" fill="#FFD25A" stroke="{INK}" stroke-width="5"/></g>')


def ya_svg(x, y, s=1.0, rot=-8.0) -> str:
    """「YA!」字（黃字、深色粗描、白外框）：拍照那一瞬間的歡呼，用字＋特效表現，不舉手。"""
    base = (f'x="{x:.1f}" y="{y:.1f}" font-family="WenQuanYi Zen Hei" font-size="{44*s:.0f}" font-weight="bold" '
            f'text-anchor="middle" transform="rotate({rot:.1f} {x:.1f} {y:.1f})"')
    return (f'<text {base} fill="#fff" stroke="#fff" stroke-width="{16*s:.1f}" stroke-linejoin="round">YA!</text>'
            f'<text {base} fill="#FFD25A" stroke="{INK}" stroke-width="{5*s:.1f}" stroke-linejoin="round">YA!</text>')


def flash_svg(x, y, r=150, n=14, rot=0.0, alpha=1.0) -> str:
    """相機閃光：白黃色大放射星（畫在身體後面）。"""
    pts = []
    for i in range(2 * n):
        a = math.radians(rot + i * 180 / n)
        rr = r if i % 2 == 0 else r * 0.55
        pts.append(f"{x + rr*math.cos(a):.1f},{y + rr*math.sin(a):.1f}")
    return (f'<g opacity="{alpha:.2f}"><polygon points="{" ".join(pts)}" fill="#FFF3B0" stroke="#F2C94C" stroke-width="5" '
            f'stroke-linejoin="round"/><circle cx="{x:.1f}" cy="{y:.1f}" r="{r*0.42:.1f}" fill="#FFFDF0"/></g>')


# ================================================================== 2. 睡覺（趴著、蓋小被子、ZZZ）＋被叫醒
LIE_LEGS = {"fl": (-16, 0, 0, 0), "fr": (-10, -4, 0, 0), "bl": (0, -14, 0, 0), "br": (0, -14, 0, 0)}


def sleep_pose(i, n=8):
    a = TAU * i / n
    return dict(view="side", x=R.CX + 8, sx=1.12 - 0.012 * math.sin(a), sy=0.6 + 0.024 * math.sin(a), eye="sleep",
                mouth="w", look=(-14, 40), lying=True, blush=1.15, legs=LIE_LEGS,
                ear=2 + 3 * math.sin(a - 0.8), ear2=2 + 3 * math.sin(a - 0.8), flutter=1.5 * math.sin(a), fphase=a)


def zzz_fx(i, n=8, x0=150.0, y0=258.0):
    out = []
    for j in range(3):
        ph = ((i / n) + j / 3) % 1.0
        x = x0 + 70 * ph + 8 * math.sin(ph * 6)
        y = y0 - 150 * ph
        al = min(1.0, ph / 0.15) * min(1.0, (1 - ph) / 0.22)
        out.append(zzz_svg(x, y, 0.62 + 0.62 * ph, max(0.0, al), -10 + 8 * j))
    return out


def clip_sleep_loop():
    fr = []
    labs = ["吸氣（被子微微鼓起）", "吸氣", "吸飽（身體最圓）", "吐氣", "吐氣", "吐氣（身體最扁）", "停一下", "準備吸氣（接回第 1 格）"]
    for i in range(8):
        p = sleep_pose(i)
        a = TAU * i / 8
        fr.append(F(p, 170, f"趴著睡・{labs[i]}", fx=zzz_fx(i), overlay=Q.blanket_overlay(wave=0.5 * math.sin(a))))
    return fr


def clip_wake_once():
    fr = []
    s0 = sleep_pose(0)
    # 1 嚇一跳：整隻彈起來（四腳離地）、毛炸開、被子往上飛走
    p1 = dict(view="side", x=R.CX + 8, y=GROUND - 46, sx=0.98, sy=1.06, eye="wide", mouth="o", ear=-20, ear2=-16,
              flutter=-7, fphase=1.0, legs={"fl": (-8, 6, -10, 0.6), "fr": (-4, 4, -10, 0.6), "bl": (8, 6, 10, 0.6), "br": (6, 4, 10, 0.6)})
    ht = head_top(p1, 200)
    fr.append(F(p1, 70, "被叫醒嚇一跳：整隻彈起來、毛炸開",
                fx=[exclaim_svg(ht[0] - 40, ht[1] - 46, 1.15, -10)],
                overlay=Q.blanket_overlay(lift=30, dx=24, rot=10, alpha=0.95)))
    p2 = dict(p1, y=GROUND - 26, sy=1.03, sx=1.0, flutter=-4, ear=-14, ear2=-10)
    fr.append(F(p2, 70, "往下掉（被子飛走）", fx=[exclaim_svg(head_top(p2, 200)[0] - 40, head_top(p2, 200)[1] - 40, 1.0, -6)],
                overlay=Q.blanket_overlay(lift=10, dx=40, rot=24, alpha=0.4)))
    p3 = dict(view="side", x=R.CX + 8, sx=1.12, sy=0.82, eye="wide", mouth="o", ear=8, ear2=8, flutter=4)
    fr.append(F(p3, 80, "落地壓扁（四腳著地）", fx=[R.dust_svg(70, 466, 0.8), R.dust_svg(440, 466, 0.8)]))
    p4 = dict(view="side", x=R.CX + 8, sx=1.02, sy=1.03, eye="default", mouth="w", ear=-4, ear2=-4)
    fr.append(F(p4, 160, "睜開眼（還有點呆）"))
    p5 = dict(p4, eye="closed", sy=1.0, sx=1.04)
    fr.append(F(p5, 80, "眨眼"))
    # 伸懶腰：前腳往前伸、後腳往後伸、身體拉長壓低、打哈欠
    p6 = dict(view="side", x=R.CX + 8, sx=1.14, sy=0.84, shear=0.05, eye="squeeze", mouth="o", ear=14, ear2=14,
              legs={"fl": (-30, 0, -14, 0), "fr": (-24, 0, -14, 0), "bl": (26, 0, 14, 0), "br": (22, 0, 14, 0)})
    fr.append(F(p6, 260, "伸懶腰：前腳往前、後腳往後伸、打哈欠"))
    p7 = dict(p6, sx=1.18, sy=0.8, shear=0.07, mouth="big", legs={"fl": (-38, 0, -18, 0), "fr": (-30, 0, -18, 0),
                                                                  "bl": (32, 0, 18, 0), "br": (28, 0, 18, 0)})
    fr.append(F(p7, 300, "伸到底（身體拉最長、哈欠張最大）"))
    p8 = dict(view="side", x=R.CX + 8, sx=0.98, sy=1.05, eye="default", mouth="w", ear=-6, ear2=-6, flutter=-3)
    fr.append(F(p8, 90, "收回來、彈一下"))
    p9 = dict(view="q3", sx=1.0, sy=1.0, eye="smile", mouth="w", ear=4, ear2=4, flutter=6, fphase=2.0)
    fr.append(F(p9, 120, "轉正、抖抖毛"))
    fr.append(F(DEFAULT_END, 400, "回 Default"))
    return fr


# ================================================================== 3. 哭（淚汪汪，cry_ref_1012）／被敲
def cry_pose(i, n=8):
    a = TAU * i / n
    sob = i % 2 == 0
    return dict(view="front", x=R.CX + (3 if i % 4 == 0 else -3 if i % 4 == 2 else 0), y=GROUND - (3 if sob else 0),
                sx=1.04 - (0.02 if sob else 0), sy=0.94 + (0.03 if sob else 0), eye="teary_big", eye_s=1.3,
                mouth="wobble_small" if sob else "pout", blush=1.3, tear=1.0, rim=1.0, tear_ph=(i % 4) / 4,
                wobble=math.sin(2 * a), ear=22 + (5 if sob else 0), ear2=22 + (5 if sob else 0),
                flutter=2.0 * math.sin(2 * a), fphase=a, plant=True)


def clip_cry():
    fr = []
    labs = ["抽一下（身體往上縮、抖）", "淚汪汪撇嘴", "又抽一下（往另一邊抖）", "淚珠沿臉頰滑到底", "抽一下", "淚汪汪", "抽一下", "淚珠滑落（接回第 1 格）"]
    for i in range(8):
        fr.append(F(cry_pose(i), 90 if i % 2 == 0 else 160, labs[i]))
    return fr


def clip_hit():
    fr = []
    sq = dict(view="front", sy=0.62, sx=1.17, eye="squeeze", mouth="wail", ear=30, ear2=30, flutter=6,
              legs={"fl": (-18, 0, -22, 0), "fr": (18, 0, 22, 0), "bl": (-22, 0, -28, 0), "br": (22, 0, 28, 0)})
    ht = head_top(sq)
    fr.append(F(sq, 80, "被敲扁：整隻壓在地上、四腳往外撐",
                fx=[R.burst_svg(ht[0], ht[1] - 34, 60, 9, 0, 6.0), R.star_svg(ht[0] - 110, ht[1] - 50, 15, 10),
                    R.star_svg(ht[0] + 112, ht[1] - 44, 13, -12)]))
    st = dict(view="front", y=GROUND - 16, sy=1.14, sx=0.92, eye="wide", mouth="o", ear=-12, ear2=-12, flutter=-5,
              legs={"fl": (4, 4, 6, 0.5), "fr": (-4, 4, -6, 0.5), "bl": (6, 0, 0, 0.5), "br": (-6, 0, 0, 0.5)})
    fr.append(F(st, 70, "彈回來（拉長、嚇呆）"))
    back = dict(view="front", sy=0.9, sx=1.08, eye="teary_big", eye_s=1.0, mouth="pout", ear=18, ear2=18, rim=0.5, blush=1.2)
    ht = head_top(back)
    fr.append(F(back, 90, "壓回來、頭上腫一個包", fx=[V.bump_svg(ht[0] + 30, ht[1], 0.9)], fx_on_body=True))
    p4 = dict(cry_pose(1), tear=0.0, tear_ph=-1)
    ht = head_top(p4)
    fr.append(F(p4, 160, "眼睛含淚、嘴撇下來", fx=[V.bump_svg(ht[0] + 30, ht[1], 0.9)], fx_on_body=True))
    p5 = dict(cry_pose(1), tear=0.6, tear_ph=-1)
    fr.append(F(p5, 160, "眼淚流下來", fx=[V.bump_svg(head_top(p5)[0] + 30, head_top(p5)[1], 0.75)], fx_on_body=True))
    fr.append(F(cry_pose(0), 90, "淚汪汪（＝bibi_cry 第 1 格，接 cry 循環）"))
    return fr


# ================================================================== 4. 轉圈（四腳小跑繞一圈）→ 暈
def spin_frames():
    out = []
    n = 10
    for k in range(n):
        th = 90 + k * 36
        m = th % 360
        x = R.CX + 46 * math.cos(math.radians(th))
        depth = 0.5 + 0.5 * math.sin(math.radians(th))      # 1＝近（下方）、0＝遠（上方）
        sc = 0.93 + 0.07 * depth
        if 60 <= m < 120:
            view, facing = "side", "left"
        elif 120 <= m < 220:
            view, facing = "back", "left"
        elif 220 <= m < 300:
            view, facing = "side", "right"
        elif 300 <= m < 340:
            view, facing = "q3", "right"
        elif m >= 340 or m < 20:
            view, facing = "front", "left"
        else:
            view, facing = "q3", "left"
        ph = k % 2
        up = -12
        if view in ("side", "q3"):
            legs = {"fl": (-10 if ph == 0 else 6, up if ph == 0 else 0, -10 if ph == 0 else 6, 0),
                    "br": (-8 if ph == 0 else 8, up if ph == 0 else 0, -8 if ph == 0 else 8, 0),
                    "fr": (-10 if ph == 1 else 6, up if ph == 1 else 0, -10 if ph == 1 else 6, 0),
                    "bl": (-8 if ph == 1 else 8, up if ph == 1 else 0, -8 if ph == 1 else 8, 0)}
        else:
            legs = {"fl": (0, up if ph == 0 else 0, 0, 0), "br": (0, up if ph == 0 else 0, 0, 0),
                    "fr": (0, up if ph == 1 else 0, 0, 0), "bl": (0, up if ph == 1 else 0, 0, 0)}
        p = dict(view=view, facing=facing, x=x if facing == "left" else 2 * R.CX - x, sx=sc * (1.04 if view == "side" else 1.0),
                 sy=sc * (0.98 if ph else 0.94), y=GROUND, ear=20, ear2=20, flutter=6 + 2 * ph, fphase=k * 1.3,
                 eye="default" if k < 6 else "squeeze", mouth="default" if k < 4 else ("o" if k < 8 else "wobble:6:1"),
                 legs=legs, rot=-3 if view == "side" else 0, tail=(0, 0, 10 * (1 if ph else -1)))
        fx = []
        if view == "side":     # 效果用「面向左」的座標給，面向右時整格鏡像會跟著翻；動作線貼在背後上方
            fx.append(R.motion_marks_svg(p["x"] + 168, 176, 1, 1.0, 2))
        lab = {"side": "側面小跑", "back": "背對（往後跑）", "q3": "3/4 轉身", "front": "正面跑過來"}[view]
        out.append(F(p, 60, f"四腳小跑繞圈・{lab}", fx=fx,
                     fx_back=[R.dust_svg(p["x"] + 150, 468, 0.7, 0.8)] if k % 3 == 0 else None))
    return out


def clip_spin():
    fr = spin_frames()
    stop = dict(view="front", rot=10, sy=0.92, sx=1.06, eye="swirl:40", mouth="wobble:-6:1.2", ear=24, ear2=-6, flutter=-5,
                legs={"fl": (-10, 0, -10, 0), "fr": (8, -10, 10, 0), "bl": (-8, 0, 0, 0), "br": (6, 0, 0, 0)})
    fr.append(F(stop, 120, "急停、整隻往一邊歪（暈）"))
    d0 = V.dizzy_pose(0)
    front, nm, back = V.dizzy_stars(0, d0)
    fr.append(F(dict(d0, feet="orig"), 170, "暈眩臉（＝bibi_dizzy 第 1 格，要接暈眩循環就在這格切過去）", fx=front,
                props_back=back))
    fr.append(F(DEFAULT_END, 400, "回 Default"))
    return fr


# ================================================================== 5. 拍照（快門那一瞬間整隻跳起來，YA 用表情＋特效）
def clip_selfie():
    fr = []
    tuck = {"fl": (6, 2, 12, 1.0), "fr": (-6, 2, -12, 1.0), "bl": (10, -2, 6, 1.0), "br": (-10, -2, -6, 1.0)}
    p1 = dict(view="front", sy=0.84, sx=1.1, eye="smile", mouth="w", ear=14, ear2=14, blush=1.2)
    fr.append(F(p1, 90, "蹲低預備（瞇眼憋笑）"))
    p2 = dict(p1, sy=0.78, sx=1.14, eye="squeeze", ear=20, ear2=20)
    fr.append(F(p2, 70, "再蹲低（用力）"))
    p3 = dict(view="front", y=GROUND - 64, sy=1.12, sx=0.92, eye="star_big", mouth="big", ear=-16, ear2=-16, flutter=6,
              blush=1.3, legs=tuck)
    c = head_top(p3)
    fr.append(F(p3, 60, "喀嚓！快門瞬間整隻彈起來（四腳離地、星星眼）",
                fx_back=[flash_svg(c[0], c[1] + 120, 150, 14, 5)],
                fx=[sparkle_svg(70, 150, 20), sparkle_svg(430, 120, 16)]))
    p4 = dict(p3, y=GROUND - 84, sy=1.0, sx=1.0, rot=-5, flutter=3)
    c = head_top(p4)
    fr.append(F(p4, 220, "空中最高點：YA！（星星眼大笑、閃光）",
                fx_back=[flash_svg(c[0], c[1] + 130, 140, 14, 18, 0.75)],
                fx=[ya_svg(424, 96, 1.0, 10), sparkle_svg(62, 120, 18), R.star_svg(30, 300, 14, 15), R.star_svg(478, 280, 12, -10)]))
    p5 = dict(view="front", y=GROUND - 36, sy=1.07, sx=0.95, eye="arc", mouth="smile", ear=-8, ear2=-8, blush=1.2,
              legs={"fl": (4, 2, 6, 0.5), "fr": (-4, 2, -6, 0.5), "bl": (6, 0, 0, 0.5), "br": (-6, 0, 0, 0.5)})
    fr.append(F(p5, 70, "往下掉", fx=[R.star_svg(452, 200, 11, 0)]))
    p6 = dict(view="front", sy=0.8, sx=1.16, eye="arc", mouth="w", ear=16, ear2=16, flutter=-5, blush=1.2)
    fr.append(F(p6, 70, "落地壓扁（四腳著地）", fx=[R.dust_svg(64, 468, 0.8), R.dust_svg(434, 468, 0.8)]))
    p7 = dict(view="front", sy=1.05, sx=0.97, eye="default", mouth="default", ear=-4, ear2=-4, flutter=3)
    fr.append(F(p7, 80, "回彈"))
    p8 = dict(view="front", sy=0.98, sx=1.01, eye="smile", mouth="default", ear=2, ear2=2, blush=1.2)
    fr.append(F(p8, 140, "得意瞇眼", fx=[sparkle_svg(440, 170, 14)]))
    fr.append(F(DEFAULT_END, 400, "回 Default"))
    return fr


# ================================================================== 6. 玩球：四腳小跑、起跑、煞車、撲球
def run_pose4(i, n=8):
    """側面面向左四腳小跑：對角兩腳一組（左前＋右後、右前＋左後）輪流邁步，身體上下起伏、耳朵晃、毛飄。"""
    a = TAU * i / n

    def leg(ph, reach=16, up=15):
        return (-reach * math.cos(ph), -up * max(0.0, math.sin(ph)), -14 * math.cos(ph), 0.4 * max(0.0, math.sin(ph)))
    bob = abs(math.sin(a))
    return dict(view="side", y=GROUND - 5 * bob, plant=True, sx=1.05 - 0.03 * bob, sy=0.94 + 0.05 * bob,
                rot=-4 - 2 * math.sin(2 * a), ear=18 + 10 * math.sin(2 * a - 1.2), ear2=18 + 10 * math.sin(2 * a - 1.2),
                flutter=6 + 2 * math.sin(2 * a), fphase=2 * a, eye="default", mouth="default", blush=1.1,
                legs={"fl": leg(a), "br": leg(a + 0.25), "fr": leg(a + math.pi), "bl": leg(a + math.pi + 0.25)})


def run_fx4(i, p):
    out = [R.motion_marks_svg(p.get("x", R.CX) + 186, 190 + 6 * (i % 2), 1, 1.0, 2)]
    fxb = [R.dust_svg(p.get("x", R.CX) + 176 + 6 * (i % 2), 468, 0.7 if i % 4 == 0 else 0.9, 1.0 if i % 4 == 0 else 0.55)] \
        if i % 4 in (0, 1) else None
    return out, fxb


def clip_run():
    fr = []
    labs = ["左前＋右後邁步", "騰起", "落地", "推地", "右前＋左後邁步", "騰起", "落地", "推地（接回第 1 格）"]
    for i in range(8):
        p = run_pose4(i)
        fx, fxb = run_fx4(i, p)
        fr.append(F(p, 70, f"四腳小跑・{labs[i]}", fx=fx, fx_back=fxb))
    return fr


def clip_run_start():
    fr = []
    p1 = dict(view="q3", sy=0.9, sx=1.06, eye="wide", mouth="o", ear=-14, ear2=-14)
    fr.append(F(p1, 110, "看到球、耳朵豎起（3/4 轉身）"))
    p2 = dict(view="side", sy=0.84, sx=1.1, eye="default", mouth="w", ear=10, ear2=10, shear=-0.06,
              legs={"bl": (10, 0, 8, 0), "br": (10, 0, 8, 0)})
    fr.append(F(p2, 90, "壓低、屁股往後（預備）"))
    p3 = dict(view="side", sy=0.96, sx=1.12, eye="default", mouth="default", ear=20, ear2=20, shear=0.08, rot=-5, flutter=5,
              legs={"fl": (-18, -12, -14, 0.4), "fr": (-12, 0, -10, 0), "bl": (16, 0, 14, 0), "br": (14, -8, 12, 0.3)})
    fx, fxb = run_fx4(0, p3)
    fr.append(F(p3, 70, "後腳一蹬衝出去", fx=fx, fx_back=[R.dust_svg(R.CX + 190, 466, 1.0)]))
    p4 = run_pose4(0)
    fx, fxb = run_fx4(0, p4)
    fr.append(F(p4, 70, "＝run 第 1 格（直接接循環）", fx=fx, fx_back=fxb))
    return fr


def clip_run_stop():
    fr = []
    p0 = run_pose4(2)
    fx, fxb = run_fx4(2, p0)
    fr.append(F(p0, 70, "跑步中（＝run 第 3 格）", fx=fx, fx_back=fxb))
    p1 = dict(view="side", sy=0.9, sx=1.1, rot=5, shear=-0.08, eye="squeeze", mouth="o", ear=-14, ear2=-14, flutter=-7,
              legs={"fl": (-22, 0, -20, 0), "fr": (-16, 0, -16, 0), "bl": (6, 0, 0, 0), "br": (6, 0, 0, 0)})
    fr.append(F(p1, 80, "煞車：前腳往前撐、身體往後坐、毛往前甩", fx_back=[R.dust_svg(70, 466, 1.0), R.dust_svg(110, 470, 0.7, 0.7)]))
    p2 = dict(view="side", sy=0.84, sx=1.12, rot=-3, shear=0.06, eye="default", mouth="w", ear=10, ear2=10, flutter=4)
    fr.append(F(p2, 80, "往前一晃（跟隨）", fx_back=[R.dust_svg(60, 462, 1.2, 0.5)]))
    p3 = dict(view="side", sy=1.03, sx=0.99, eye="default", mouth="default", ear=0, ear2=0)
    fr.append(F(p3, 110, "站穩（側面）"))
    p4 = dict(view="q3", eye="default", mouth="default")
    fr.append(F(p4, 110, "轉回來"))
    fr.append(F(DEFAULT_END, 400, "回 Default"))
    return fr


def ball_l(x, y, ang, r=34.0):
    return R.svg_layer(R.ball_svg(x, y, r, ang))


def clip_ball_catch():
    """面向左撲球（clip 設定面向右時整組鏡像）：追→壓低扭屁股→撲上去用身體壓住→彈起→用鼻子推球→開心。"""
    fr = []
    BR = 34.0
    gy = GROUND - BR
    X0 = R.CX + 28

    def ball(x, ang, dy=0.0):
        return [ball_l(x, gy + dy, ang, BR)]
    p = dict(run_pose4(0), x=X0)
    fx, fxb = run_fx4(0, p)
    fr.append(F(p, 70, "追著球跑（球在前面滾）", fx=fx, fx_back=fxb, props_back=ball(46, -40)))
    p = dict(run_pose4(2), x=X0)
    fx, fxb = run_fx4(2, p)
    fr.append(F(p, 70, "追", fx=fx, fx_back=fxb, props_back=ball(46, -70)))
    p = dict(view="side", x=X0 - 8, sy=0.82, sx=1.08, shear=-0.05, eye="wide", mouth="w", ear=-10, ear2=-10,
             legs={"bl": (8, 0, 6, 0), "br": (8, 0, 6, 0)})
    fr.append(F(p, 110, "壓低盯著球（屁股往後）", props_back=ball(46, -80)))
    p = dict(p, rot=3, shear=-0.07)
    fr.append(F(p, 80, "屁股扭一下（預備）", props_back=ball(46, -80)))
    p = dict(view="side", x=X0 - 24, y=GROUND - 50, sy=0.9, sx=1.08, rot=-8, eye="squeeze", mouth="default", ear=26, ear2=26,
             flutter=7, legs={"fl": (-14, 0, -24, 0.6), "fr": (-10, 0, -20, 0.6), "bl": (16, 0, 24, 0.6), "br": (14, 0, 22, 0.6)})
    fr.append(F(p, 70, "撲出去（四腳伸直、整隻騰空）", props_back=ball(46, -80)))
    p = dict(view="side", x=X0 - 40, sy=0.78, sx=1.1, eye="smile", mouth="w", ear=16, ear2=16, flutter=-5, blush=1.3)
    fr.append(F(p, 90, "用身體壓住球！（球被壓在胸前下面）", props_back=ball(50, -80, 4), fx=[R.star_svg(150, 230, 13, 10)]))
    p = dict(p, sy=0.84, sx=1.07)
    fr.append(F(p, 150, "壓著不放（得意）", props_back=ball(50, -80, 4)))
    p = dict(view="side", x=X0 - 30, y=GROUND - 34, sy=1.06, sx=0.98, eye="default", mouth="default", ear=-8, ear2=-8,
             legs={"fl": (2, 2, 4, 0.5), "fr": (2, 2, 4, 0.5), "bl": (-2, 2, -4, 0.5), "br": (-2, 2, -4, 0.5)})
    fr.append(F(p, 70, "彈起來（球滾出去一點）", props_back=ball(46, -130)))
    p = dict(view="side", x=X0 - 20, sy=0.92, sx=1.06, eye="default", mouth="default", ear=6, ear2=6)
    fr.append(F(p, 80, "落地", props_back=ball(46, -160), fx_back=[R.dust_svg(X0 + 150, 468, 0.8)]))
    p = dict(view="side", x=X0 - 10, sy=0.9, sx=1.06, shear=0.12, look=(-14, 44), eye="default", mouth="w", ear=-8, ear2=-8)
    mx, my = mouth_at(p)
    fr.append(F(p, 120, "低頭用鼻子推球", props_back=ball(48, -170), fx=[sniff_svg(mx - 40, my - 30, 0.9, -1)]))
    p = dict(p, shear=0.16, x=X0 - 14)
    fr.append(F(p, 90, "推一下（球往前滾）", props_back=ball(44, -230)))
    p = dict(view="q3", x=R.CX + 30, eye="arc", mouth="default", blush=1.3, ear=-4, ear2=-4)
    fr.append(F(p, 160, "轉頭開心看鏡頭", props_back=ball(44, -250), fx=[heart_svg(R.CX + 170, 150, 1.0, 10)]))
    fr.append(F(dict(DEFAULT_END, x=R.CX + 30), 400, "回 Default（球停在身邊）", props_back=ball(44, -250)))
    return fr


# ================================================================== 7. 摸摸（趴低、瞇眼、耳朵往後貼、往上蹭）
def clip_pet():
    fr = []
    base = dict(view="front", eye="arc", mouth="w", blush=1.3, ear=26, ear2=26,
                legs={"fl": (-10, 0, -10, 0), "fr": (10, 0, 10, 0), "bl": (-14, 0, -12, 0), "br": (14, 0, 12, 0)})
    seq = [
        (dict(base, sy=0.86, sx=1.08, eye="default", ear=10, ear2=10), 90, "感覺到手、往下趴一點"),
        (dict(base, sy=0.8, sx=1.12, ear=32, ear2=32), 120, "趴低、四腳攤開、耳朵往後貼、瞇成彎月"),
        (dict(base, sy=0.88, sx=1.06, rot=5, shear=-0.04, flutter=3), 90, "往右上蹭"),
        (dict(base, sy=0.81, sx=1.11, rot=1), 90, "回來"),
        (dict(base, sy=0.9, sx=1.05, rot=7, shear=-0.05, blush=1.5, flutter=4), 100, "再蹭（臉更紅）"),
        (dict(base, sy=0.81, sx=1.11, rot=1, blush=1.5), 90, "回來"),
        (dict(base, sy=0.9, sx=1.05, rot=6, shear=-0.05, blush=1.6, flutter=4), 100, "蹭蹭"),
        (dict(base, sy=0.76, sx=1.15, eye="smile", blush=1.6, ear=34, ear2=34), 320, "舒服到融化（攤平）"),
        (dict(base, sy=0.96, sx=1.02, eye="smile", blush=1.4, ear=8, ear2=8), 120, "抬起來"),
        (dict(view="front", eye="arc", mouth="default", blush=1.3), 160, "開心"),
    ]
    for i, (p, ms, lab) in enumerate(seq):
        fx = []
        if i in (4, 6):
            fx = [heart_svg(430, 170 - 10 * (i == 6), 1.0, 12)]
        if i == 7:
            fx = [heart_svg(424, 200, 1.1, 10), heart_svg(70, 230, 0.8, -12)]
        fr.append(F(p, ms, lab, fx=fx))
    fr.append(F(DEFAULT_END, 400, "回 Default"))
    return fr


# ================================================================== 8. 其餘：碰鼻子、popcorn 連跳扭、蹭過來貼貼、低頭嗅、爆米花跳
def clip_boop():
    """單隻比比「向前伸頭碰鼻」（取代擊掌）：3/4 面向右（clip 設面向右）。"""
    fr = []
    q = dict(view="q3")
    seq = [
        (dict(q, eye="wide", mouth="o", ear=-18, ear2=-18), 100, "發現（耳朵豎起）", []),
        (dict(q, shear=0.1, sx=1.06, sy=0.95, look=(-10, 10), eye="default", mouth="w", ear=-14, ear2=-14), 80, "往前伸頭", []),
        (dict(q, shear=0.16, sx=1.08, sy=0.93, look=(-16, 14), eye="default", mouth="o", ear=-16, ear2=-16), 90, "鼻子前探、嗅嗅", "sniff"),
        (dict(q, shear=0.2, sx=1.1, sy=0.92, look=(-20, 16), eye="smile", mouth="w", ear=-10, ear2=-10, blush=1.4), 150, "碰！鼻子輕碰", "boop"),
        (dict(q, shear=0.12, sx=1.06, sy=0.95, look=(-12, 12), eye="smile", mouth="default", blush=1.5), 110, "冒小愛心", "heart"),
        (dict(q, sy=1.03, sx=0.98, eye="arc", mouth="default", blush=1.4), 110, "縮回來、開心", "heart2"),
        (dict(view="front", eye="arc", mouth="default", blush=1.3), 150, "轉正", []),
    ]
    for p, ms, lab, k in seq:
        fx = []
        if k:
            mx, my = mouth_at(p)
            if k == "sniff":
                fx = [sniff_svg(mx - 64, my - 14, 1.0, -1)]
            elif k == "boop":
                fx = [sparkle_svg(42, 250, 16)]
            elif k == "heart":
                fx = [heart_svg(60, 130, 1.0, -10)]
            else:
                fx = [heart_svg(110, 120, 1.1, -12)]
        fr.append(F(p, ms, lab, fx=fx))
    fr.append(F(DEFAULT_END, 400, "回 Default"))
    return fr


def hop_pose(h, rot=0.0, phase="air", eye="arc", mouth="default"):
    tuck = {"fl": (4, 2, 10, 0.8), "fr": (-4, 2, -10, 0.8), "bl": (8, -2, 4, 0.8), "br": (-8, -2, -4, 0.8)}
    if phase == "air":
        return dict(view="front", y=GROUND - h, sy=1.06, sx=0.96, rot=rot, eye=eye, mouth=mouth, ear=-10, ear2=-10,
                    flutter=5, legs=tuck, blush=1.25)
    if phase == "land":
        return dict(view="front", sy=0.82, sx=1.14, rot=rot * 0.3, eye=eye, mouth="w", ear=16, ear2=16, flutter=-5, blush=1.25)
    return dict(view="front", sy=0.88, sx=1.08, eye=eye, mouth="w", ear=10, ear2=10, blush=1.2)


def clip_dance():
    """原地 popcorn 連跳 3 下＋左右扭（四腳離地），音符。"""
    fr = []
    seq = [
        (hop_pose(0, phase="crouch", eye="smile"), 90, "蹲（預備）", [music_svg(56, 170, 1.1, -10)]),
        (hop_pose(56, 12), 80, "跳！往右扭", [music_svg(452, 96, 1.1, 10)]),
        (hop_pose(0, 10, "land"), 80, "落地", []),
        (hop_pose(56, -12), 80, "跳！往左扭", [music_svg(52, 96, 1.1, -10)]),
        (hop_pose(0, -10, "land"), 80, "落地", []),
        (hop_pose(70, 14, eye="star_big", mouth="big"), 90, "第三下跳最高（星星眼）", [music_svg(456, 70, 1.2, 12), music_svg(46, 110, 0.9, -8)]),
        (hop_pose(36, 4), 70, "往下掉", []),
        (hop_pose(0, 0, "land"), 80, "落地壓扁", []),
        (dict(view="front", sy=1.04, sx=0.98, eye="arc", mouth="default", blush=1.3, rot=-4), 120, "左右晃", [music_svg(456, 150, 1.0, 8)]),
        (dict(view="front", sy=1.0, eye="arc", mouth="default", blush=1.3, rot=4), 120, "晃回來", []),
    ]
    for p, ms, lab, fx in seq:
        fr.append(F(p, ms, lab, fx=fx))
    fr.append(F(DEFAULT_END, 400, "回 Default"))
    return fr


def clip_hug():
    """蹭過來貼貼：整隻往右側傾倒貼過去（四腳著地）、瞇眼臉紅、愛心。"""
    fr = []
    b = dict(view="q3", facing="right", mouth="w", blush=1.3)
    seq = [
        (dict(b, eye="default", ear=-8, ear2=-8), 100, "轉向一側", []),
        (dict(b, eye="smile", x=R.CX + 24, shear=0.08, sx=1.04, sy=0.94), 90, "往旁邊靠過去", []),
        (dict(b, eye="smile", x=R.CX + 30, shear=0.12, rot=-6, sx=1.06, sy=0.9, ear=20, ear2=20, blush=1.5), 160, "整隻貼過去蹭（臉紅）", "h1"),
        (dict(b, eye="smile", x=R.CX + 28, shear=0.1, rot=-3, sx=1.05, sy=0.92, ear=24, ear2=24, blush=1.6), 100, "蹭蹭", []),
        (dict(b, eye="smile", x=R.CX + 32, shear=0.13, rot=-7, sx=1.06, sy=0.89, ear=26, ear2=26, blush=1.6), 300, "貼著不放（愛心）", "h2"),
        (dict(b, eye="arc", x=R.CX + 12, shear=0.04, sx=1.0, sy=1.0, ear=4, ear2=4, blush=1.4), 110, "回正", []),
        (dict(view="front", eye="arc", mouth="default", blush=1.3), 150, "轉正", []),
    ]
    for p, ms, lab, k in seq:
        fx = []
        if k == "h1":
            fx = [heart_svg(80, 170, 1.0, -10)]
        if k == "h2":
            fx = [heart_svg(70, 140, 1.15, -12), heart_svg(130, 90, 0.8, 8)]
        fr.append(F(p, ms, lab, fx=fx))
    fr.append(F(DEFAULT_END, 400, "回 Default"))
    return fr


def clip_receive():
    """低頭嗅一嗅（網頁東西放在比比右前方地上）：頭前伸、鼻子抖、耳朵前傾，接著湊近。clip 面向右。"""
    fr = []
    s = dict(view="side", x=R.CX + 30)
    seq = [
        (dict(s, eye="wide", mouth="o", ear=-18, ear2=-18), 100, "發現東西（耳朵前傾）", None),
        (dict(s, shear=0.12, sy=0.92, look=(-10, 34), eye="default", mouth="o", ear=-20, ear2=-20), 80, "頭往前伸、低下去", None),
        (dict(s, shear=0.16, sy=0.9, look=(-14, 46), eye="default", mouth="w", ear=-22, ear2=-22), 70, "嗅（鼻子抖）", 1.0),
        (dict(s, shear=0.15, sy=0.91, look=(-12, 44), eye="default", mouth="o", ear=-16, ear2=-16), 70, "嗅", 1.2),
        (dict(s, shear=0.17, sy=0.9, look=(-14, 46), eye="default", mouth="w", ear=-22, ear2=-22), 70, "嗅嗅", 1.0),
        (dict(s, x=R.CX + 10, shear=0.2, sy=0.88, sx=1.08, look=(-16, 50), eye="smile", mouth="w", ear=-12, ear2=-12, blush=1.3,
              legs={"fl": (-14, -10, -10, 0.3), "br": (-10, -8, -8, 0.3)}), 90, "湊近（邁一步）", None),
        (dict(s, x=R.CX + 4, shear=0.18, sy=0.9, sx=1.06, look=(-14, 46), eye="arc", mouth="w", ear=-8, ear2=-8, blush=1.3), 160,
         "是好東西！（開心）", "h"),
        (dict(view="q3", eye="arc", mouth="default", blush=1.2), 140, "轉正", None),
    ]
    for p, ms, lab, k in seq:
        fx = []
        mx, my = mouth_at(p)
        if isinstance(k, float):
            fx = [sniff_svg(mx - 26, my + 2, k, -1)]
        elif k == "h":
            fx = [heart_svg(150, 100, 1.0, -8)]
        fr.append(F(p, ms, lab, fx=fx))
    fr.append(F(DEFAULT_END, 400, "回 Default"))
    return fr


def clip_popcorn():
    """爆米花跳：四腳離地垂直彈起、空中扭身（腳往外踢）、落地連彈 2～3 下越來越小。"""
    fr = []
    kick = {"fl": (-10, 6, -24, 0.8), "fr": (10, 6, 24, 0.8), "bl": (-16, 2, -30, 0.8), "br": (16, 2, 30, 0.8)}
    seq = [
        (hop_pose(0, phase="crouch", eye="squeeze"), 80, "蹲低（預備）", []),
        (dict(hop_pose(90, 18), legs=kick, eye="star_big", mouth="big"), 70, "垂直彈起！空中扭身、腳往外踢",
         ["pc"]),
        (dict(hop_pose(104, -16), eye="arc", mouth="big"), 90, "最高點反扭", []),
        (hop_pose(40, -4), 60, "往下掉", []),
        (hop_pose(0, 0, "land"), 70, "落地壓扁", []),
        (dict(hop_pose(52, 12), legs=kick), 70, "第二下（小一點）", []),
        (hop_pose(0, 4, "land"), 70, "落地", []),
        (hop_pose(22, -8), 70, "第三下（更小）", []),
        (dict(hop_pose(0, 0, "land"), sy=0.9, sx=1.06), 80, "落地", []),
        (dict(view="front", eye="arc", mouth="default", blush=1.3, sy=1.03), 160, "開心定格", []),
    ]
    for p, ms, lab, fx in seq:
        f = []
        if fx == ["pc"]:
            f = [R.popcorn_svg(40, 70, 1.4, -20), R.popcorn_svg(472, 64, 1.4, 15), R.popcorn_svg(38, 384, 1.3, 30)]
        fr.append(F(p, ms, lab, fx=f, fx_back=[R.dust_svg(70, 468, 0.8), R.dust_svg(430, 468, 0.8)] if "落地" in lab else None))
    fr.append(F(DEFAULT_END, 400, "回 Default"))
    return fr


# ================================================================== 丟東西 → 比比追（10-12 Andy：「我很喜歡丟球的互動效果，希望能多點這樣的」）
def seed_svg(x, y, s=1.0, rot=0.0) -> str:
    """葵瓜子：黑灰條紋水滴形。"""
    return (f'<g transform="translate({x:.1f},{y:.1f}) rotate({rot:.1f}) scale({s:.3f})">'
            f'<path d="M 0 -20 C 11 -12 12 8 0 20 C -12 8 -11 -12 0 -20 Z" fill="#3B3638" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>'
            f'<path d="M -4 -12 C -5 -2 -5 6 -3 14 M 4 -12 C 5 -2 5 6 3 14" stroke="#E9E4DA" stroke-width="2.6" fill="none" stroke-linecap="round"/>'
            f'<path d="M 0 -17 C 1 -6 1 6 0 17" stroke="#9E9890" stroke-width="2" fill="none"/></g>')


def carrot_svg(x, y, s=1.0, rot=0.0) -> str:
    """胡蘿蔔丁：圓角小方塊、橘色、亮面。"""
    return (f'<g transform="translate({x:.1f},{y:.1f}) rotate({rot:.1f}) scale({s:.3f})">'
            f'<rect x="-13" y="-13" width="26" height="26" rx="6" fill="#F28C28" stroke="{INK}" stroke-width="4"/>'
            f'<path d="M -13 -3 L 13 -3" stroke="#D8701A" stroke-width="2.4"/>'
            f'<rect x="-8" y="-9" width="8" height="4" rx="2" fill="#FFC27A"/></g>')


def bubble_svg(x, y, r=40.0, alpha=1.0) -> str:
    """半透明泡泡：淡藍紫漸層邊、兩個亮點。"""
    gid = f"bb{int(x)}{int(y)}{int(r)}"
    return (f'<defs><radialGradient id="{gid}" cx="0.5" cy="0.5" r="0.5"><stop offset="0.6" stop-color="#DDF1FF" stop-opacity="0.15"/>'
            f'<stop offset="0.92" stop-color="#9FD3F7" stop-opacity="0.55"/><stop offset="1" stop-color="#C9B4F5" stop-opacity="0.8"/>'
            f'</radialGradient></defs><g opacity="{alpha:.2f}">'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="url(#{gid})" stroke="#5E8FC9" stroke-width="{max(2.5, r*0.07):.1f}" stroke-opacity="0.8"/>'
            f'<ellipse cx="{x-r*0.38:.1f}" cy="{y-r*0.4:.1f}" rx="{r*0.2:.1f}" ry="{r*0.12:.1f}" fill="#fff" fill-opacity="0.9" '
            f'transform="rotate(-35 {x-r*0.38:.1f} {y-r*0.4:.1f})"/><circle cx="{x+r*0.42:.1f}" cy="{y+r*0.38:.1f}" r="{r*0.07:.1f}" fill="#fff" fill-opacity="0.8"/></g>')


def bubble_pop_svg(x, y, r, t) -> str:
    """泡泡破掉：t=0 變形、t=1 破成水花線、t=2 小水滴散開。"""
    if t == 0:
        return (f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{r*1.12:.1f}" ry="{r*0.88:.1f}" fill="#DDF1FF" fill-opacity="0.3" '
                f'stroke="#5E8FC9" stroke-width="{r*0.07:.1f}" stroke-dasharray="{r*0.5:.1f} {r*0.12:.1f}"/>')
    out = ""
    n = 8
    for i in range(n):
        a = math.radians(i * 360 / n + 10)
        r0, r1 = (r * 0.7, r * 1.25) if t == 1 else (r * 1.3, r * 1.55)
        if t == 1:
            out += (f'<path d="M {x + r0*math.cos(a):.1f} {y + r0*math.sin(a):.1f} L {x + r1*math.cos(a):.1f} {y + r1*math.sin(a):.1f}" '
                    f'stroke="#5E8FC9" stroke-width="{r*0.09:.1f}" stroke-linecap="round"/>')
        else:
            out += f'<circle cx="{x + r1*math.cos(a):.1f}" cy="{y + r1*math.sin(a):.1f}" r="{r*0.08:.1f}" fill="#9FD3F7" stroke="#5E8FC9" stroke-width="2"/>'
    return out


def feather_svg(x, y, s=1.0, rot=0.0, stick=True) -> str:
    """逗貓羽毛棒：細木棒＋線＋粉色羽毛。(x,y)＝羽毛中心。"""
    st = ""
    if stick:
        st = (f'<path d="M 30 -10 L 150 -150" stroke="{INK}" stroke-width="13" stroke-linecap="round"/>'
              f'<path d="M 30 -10 L 150 -150" stroke="#C99A62" stroke-width="7" stroke-linecap="round"/>'
              f'<path d="M 150 -150 Q 120 -90 22 -8" fill="none" stroke="{INK}" stroke-width="2.4"/>')
    vanes = "".join(f'<path d="M {i*9-30:.1f} {1 - i*0.6:.1f} L {i*9-23:.1f} {-8 - (3 - abs(i-3)):.1f}" fill="none" '
                    f'stroke="#D9577E" stroke-width="1.8" stroke-linecap="round"/>' for i in range(7))
    return (f'<g transform="translate({x:.1f},{y:.1f}) rotate({rot:.1f}) scale({s:.3f})">{st}'
            f'<g transform="rotate(-30) scale(2)"><path d="M -40 2 C -30 -26 10 -30 34 -6 C 12 6 -18 16 -40 2 Z" fill="#F7A3BE" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/>'
            f'{vanes}<path d="M -44 4 L 34 -6" stroke="#FFF2F6" stroke-width="2" stroke-linecap="round"/></g></g>')


def yarn_svg(x, y, r=38.0, rot=0.0, tail=True) -> str:
    """毛線球：粉紫色圓＋纏繞線＋拖一條線。"""
    lines = "".join(f'<path d="M {-r*0.9:.1f} {r*f:.1f} Q 0 {r*(f-0.5):.1f} {r*0.9:.1f} {r*f:.1f}" fill="none" stroke="#9B5FC0" '
                    f'stroke-width="{r*0.07:.1f}" stroke-linecap="round"/>' for f in (-0.45, -0.1, 0.25, 0.6))
    cross = (f'<path d="M {-r*0.3:.1f} {-r*0.9:.1f} Q {r*0.4:.1f} 0 {-r*0.2:.1f} {r*0.92:.1f}" fill="none" stroke="#9B5FC0" '
             f'stroke-width="{r*0.07:.1f}"/>')
    tl = ""
    if tail:
        tl = (f'<path d="M {r*0.7:.1f} {r*0.62:.1f} C {r*1.4:.1f} {r*1.1:.1f} {r*2.2:.1f} {r*0.7:.1f} {r*3.0:.1f} {r*0.95:.1f}" fill="none" '
              f'stroke="{INK}" stroke-width="{r*0.16:.1f}" stroke-linecap="round"/>'
              f'<path d="M {r*0.7:.1f} {r*0.62:.1f} C {r*1.4:.1f} {r*1.1:.1f} {r*2.2:.1f} {r*0.7:.1f} {r*3.0:.1f} {r*0.95:.1f}" fill="none" '
              f'stroke="#C68BE6" stroke-width="{r*0.08:.1f}" stroke-linecap="round"/>')
    return (f'<g transform="translate({x:.1f},{y:.1f})">{tl}<g transform="rotate({rot:.1f})">'
            f'<clipPath id="yc{int(x)}{int(y)}"><circle r="{r:.1f}"/></clipPath><circle r="{r:.1f}" fill="#D9A6F2"/>'
            f'<g clip-path="url(#yc{int(x)}{int(y)})">{lines}{cross}</g>'
            f'<circle r="{r - r*0.05:.1f}" fill="none" stroke="{INK}" stroke-width="{r*0.11:.1f}"/></g></g>')


def plane_svg(x, y, s=1.0, rot=0.0) -> str:
    """紙飛機：白紙三角＋摺線。"""
    return (f'<g transform="translate({x:.1f},{y:.1f}) rotate({rot:.1f}) scale({s:.3f})">'
            f'<path d="M -50 -6 L 52 -26 L -16 22 Z" fill="#FFFFFF" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>'
            f'<path d="M -50 -6 L 52 -26 L -6 4 Z" fill="#E6EEF8" stroke="{INK}" stroke-width="4" stroke-linejoin="round"/>'
            f'<path d="M -6 4 L -16 22" stroke="{INK}" stroke-width="4" stroke-linecap="round"/></g>')


def leaf_prop_svg(x, y, s=1.0, rot=0.0) -> str:
    """落葉：橘黃楓葉形的簡化葉子＋葉脈。"""
    return (f'<g transform="translate({x:.1f},{y:.1f}) rotate({rot:.1f}) scale({s:.3f})">'
            f'<path d="M 0 -42 C 18 -30 30 -10 26 10 C 22 26 8 34 0 40 C -8 34 -22 26 -26 10 C -30 -10 -18 -30 0 -42 Z" '
            f'fill="#F2A33A" stroke="{INK}" stroke-width="4.5" stroke-linejoin="round"/>'
            f'<path d="M 0 -36 L 0 52 M 0 -10 L 14 -22 M 0 6 L 18 -4 M 0 -10 L -14 -22 M 0 6 L -18 -4" stroke="#B9661A" '
            f'stroke-width="3" stroke-linecap="round" fill="none"/></g>')


def petal_svg(x, y, s=1.0, rot=0.0) -> str:
    """櫻花花瓣：淡粉、頂端小缺口。"""
    return (f'<g transform="translate({x:.1f},{y:.1f}) rotate({rot:.1f}) scale({s:.3f})">'
            f'<path d="M 0 34 C -26 18 -28 -18 -10 -34 L 0 -26 L 10 -34 C 28 -18 26 18 0 34 Z" fill="#FBC6D6" stroke="{INK}" '
            f'stroke-width="4.5" stroke-linejoin="round"/><path d="M 0 24 L 0 -12" stroke="#F294B0" stroke-width="3" stroke-linecap="round"/></g>')


def save_prop(svg: str, path: Path, icon: Path | None = None):
    """道具 512 透明 PNG（置中）＋ 96px 圖示。"""
    im = R.finish(R.svg_layer(svg))
    bb = im.getchannel("A").getbbox()
    crop = im.crop(bb)
    k = min(1.0, 440 / max(crop.size))
    if k < 1:
        crop = crop.resize((round(crop.width * k), round(crop.height * k)), Image.LANCZOS)
    c = Image.new("RGBA", (512, 512))
    c.alpha_composite(crop, ((512 - crop.width) // 2, (512 - crop.height) // 2))
    c.save(path)
    if icon:
        c.convert("RGBa").resize((96, 96), Image.LANCZOS).convert("RGBA").save(icon)


def clip_sniff_eat():
    """撒零食：低頭嗅地上的瓜子、啃一顆（6 格一次性）。clip 面向右（零食在右前方地上）。"""
    fr = []
    seq = [
        (eat_pose(0.6, 0, "o", "default", 0, -14), 80, "低頭嗅地上的零食（鼻子抖）", "sniff", True),
        (eat_pose(0.9, 1.0, "nibble_a", "default", 0, -6), 70, "張嘴咬住", "", True),
        (eat_pose(0.7, 0, "nibble_c", "smile", 1.1, 8), 80, "叼起來嚼（臉頰鼓）", "crumb", False),
        (eat_pose(0.72, 0.3, "nibble_d", "smile", 1.2, -4), 80, "嚼嚼", "", False),
        (dict(view="q3", eye="smile", mouth="w", blush=1.3), 160, "好吃！（小愛心）", "heart", False),
    ]
    for p, ms, lab, k, seed in seq:
        if p.get("view") == "side":
            p["x"] = R.CX + 40          # 面向右會以 x=248 鏡像，往左挪免得屁股出框
        mx, my = mouth_at(p)
        fx = []
        if k == "sniff":
            fx = [sniff_svg(mx - 30, my - 4, 1.0, -1)]
        if k == "crumb":
            fx = [R.crumbs_svg(mx - 30, my + 20, 3, 14, seed=2)]
        if k == "heart":
            fx = [heart_svg(R.CX + 150, 140, 1.0, 10)]
        mid = [seed_svg(mx - 8, GROUND - 18 if lab.startswith("低頭") else my + 8, 1.5, 70)] if seed else None
        fr.append(F(p, ms, lab, fx=fx, props_mid=mid))
    fr.append(F(DEFAULT_END, 400, "回 Default"))
    return fr


def clip_hop_reach():
    """吹泡泡：原地往上撲（四腳離地、鼻子往上頂泡泡）。"""
    fr = []
    up = (0, -34)
    seq = [
        (dict(view="front", sy=0.86, sx=1.08, eye="wide", mouth="o", look=up, ear=-12, ear2=-12), 90, "抬頭盯著泡泡、蹲低", []),
        (dict(view="front", y=GROUND - 50, sy=1.12, sx=0.92, eye="wide", mouth="o", look=(0, -40), ear=-18, ear2=-18, flutter=5,
              legs={"fl": (4, 4, 8, 0.6), "fr": (-4, 4, -8, 0.6), "bl": (6, 0, 0, 0.6), "br": (-6, 0, 0, 0.6)}), 70, "往上撲（四腳離地）", []),
        (dict(view="front", y=GROUND - 72, sy=1.06, sx=0.96, eye="arc", mouth="big", look=(0, -40), ear=-20, ear2=-20, flutter=3,
              legs={"fl": (6, 6, 12, 0.9), "fr": (-6, 6, -12, 0.9), "bl": (8, 0, 6, 0.9), "br": (-8, 0, -6, 0.9)}), 100,
         "最高點、鼻子碰到泡泡（網頁在這格播 pop_burst）", ["spark"]),
        (dict(view="front", y=GROUND - 30, sy=1.06, sx=0.96, eye="arc", mouth="default", ear=-8, ear2=-8), 70, "往下掉", []),
        (dict(view="front", sy=0.82, sx=1.14, eye="arc", mouth="w", ear=14, ear2=14, flutter=-4), 80, "落地壓扁", ["dust"]),
    ]
    for p, ms, lab, k in seq:
        fx, fxb = [], None
        if "spark" in k:
            fx = [sparkle_svg(130, 70, 16), sparkle_svg(380, 64, 14)]
        if "dust" in k:
            fxb = [R.dust_svg(64, 468, 0.8), R.dust_svg(434, 468, 0.8)]
        fr.append(F(p, ms, lab, fx=fx, fx_back=fxb))
    fr.append(F(DEFAULT_END, 400, "回 Default"))
    return fr


def clip_pounce():
    """羽毛棒：蹲低屁股扭 → 往前撲（clip 面向右，羽毛在右前方）。"""
    fr = []
    low = dict(view="side", x=R.CX + 8, sy=0.8, sx=1.12, shear=-0.05, eye="wide", mouth="w", ear=-14, ear2=-14,
               legs={"bl": (8, 0, 6, 0), "br": (8, 0, 6, 0)})
    seq = [
        (dict(low, sy=0.84), 100, "盯著羽毛、蹲低", []),
        (dict(low, rot=3, shear=-0.08), 70, "屁股扭（右）", ["m"]),
        (dict(low, rot=-1, shear=-0.03), 70, "屁股扭（左）", ["m"]),
        (dict(low, rot=3, shear=-0.08, eye="squeeze"), 70, "屁股扭、用力", ["m"]),
        (dict(view="side", x=R.CX - 6, y=GROUND - 56, sy=0.9, sx=1.14, rot=-8, eye="default", mouth="o", ear=26, ear2=26, flutter=7,
              legs={"fl": (-16, 0, -24, 0.6), "fr": (-12, 0, -20, 0.6), "bl": (18, 0, 24, 0.6), "br": (16, 0, 22, 0.6)}), 70,
         "往前撲！（四腳伸直騰空）", ["speed"]),
        (dict(view="side", x=R.CX - 14, sy=0.78, sx=1.14, eye="smile", mouth="w", ear=16, ear2=16, flutter=-5, blush=1.3), 90,
         "撲到、整隻壓低", ["dust"]),
        (dict(view="side", x=R.CX - 10, sy=1.04, sx=0.99, eye="arc", mouth="default", ear=0, ear2=0, blush=1.2), 110, "抬頭得意", []),
        (dict(view="q3", x=R.CX - 4, eye="arc", mouth="default", blush=1.2), 140, "轉正", []),
    ]
    for p, ms, lab, k in seq:
        fx, fxb = [], None
        if "m" in k:
            fx = [R.motion_marks_svg(p["x"] + 196, 300, 1, 1.0, 2)]
        if "speed" in k:
            fx = [R.speed_lines_svg(446, 186, 3, 30, 20, 0.8, 1)]
        if "dust" in k:
            fxb = [R.dust_svg(60, 468, 0.9), R.dust_svg(430, 468, 0.7)]
        fr.append(F(p, ms, lab, fx=fx, fx_back=fxb))
    fr.append(F(DEFAULT_END, 400, "回 Default"))
    return fr


def yarn_wrap_overlay(k=1.0, ph=0.0, loose=0.0):
    """毛線纏在身上：照本體輪廓畫 3 圈斜斜的紫色線（只畫在身體裡、不經過臉的高度）。"""
    def fn(p, A):
        Mb = A > 128
        ys, xs = np.nonzero(Mb)
        x0, x1, yt, yb = xs.min() / R.S, xs.max() / R.S, ys.min() / R.S, ys.max() / R.S
        w, h = x1 - x0, yb - yt
        sv = ""
        for i, f in enumerate((0.64, 0.76, 0.88)):
            yy = yt + h * f + 6 * math.sin(ph + i) + loose * 22 * (i + 1)
            sv += (f'<path d="M {x0 - 6:.1f} {yy - 18:.1f} Q {(x0 + x1) / 2:.1f} {yy + 22 + 4*i:.1f} {x1 + 6:.1f} {yy - 10:.1f}" fill="none" '
                   f'stroke="{INK}" stroke-width="10" stroke-linecap="round"/>'
                   f'<path d="M {x0 - 6:.1f} {yy - 18:.1f} Q {(x0 + x1) / 2:.1f} {yy + 22 + 4*i:.1f} {x1 + 6:.1f} {yy - 10:.1f}" fill="none" '
                   f'stroke="#C68BE6" stroke-width="5" stroke-linecap="round"/>')
        lay = R.svg_layer(sv)
        a = np.asarray(lay.getchannel("A")).astype(np.float32)
        mask = np.asarray(Image.fromarray(A).filter(ImageFilter.MaxFilter(13))).astype(np.float32) / 255
        lay.putalpha(Image.fromarray((a * mask * k).astype(np.uint8)))
        return lay
    return fn


def clip_tangle():
    """毛線球：撲到後被線纏住、扭兩下掙脫（接在四腳版 ball_catch 撲到之後；6 格）。"""
    fr = []
    b = dict(view="front", sy=0.9, sx=1.06, mouth="wobble_small", blush=1.2)
    seq = [
        (dict(b, eye="wide", ear=-12, ear2=-12), 90, "被線纏住（嚇一跳）", yarn_wrap_overlay(1, 0), ["ex"]),
        (dict(b, eye="squeeze", rot=-9, ear=20, ear2=-4, flutter=5), 80, "扭（左）", yarn_wrap_overlay(1, 1.2), ["m"]),
        (dict(b, eye="squeeze", rot=9, ear=-4, ear2=20, flutter=-5), 80, "扭（右）", yarn_wrap_overlay(1, 2.4), ["m"]),
        (dict(b, eye="squeeze", rot=-6, sy=1.06, sx=0.96, ear=-10, ear2=-10), 80, "用力一彈、線鬆開往下掉", yarn_wrap_overlay(0.8, 3.0, 0.5), []),
        (dict(view="front", eye="arc", mouth="default", sy=0.92, sx=1.06, blush=1.3), 150, "掙脫了！抖抖毛", yarn_wrap_overlay(0.0, 0), ["spark"]),
    ]
    for p, ms, lab, ov, k in seq:
        fx = []
        if "ex" in k:
            fx = [exclaim_svg(430, 150, 1.0, 10)]
        if "m" in k:
            fx = [R.motion_marks_svg(450 if p["rot"] < 0 else 46, 300, 1 if p["rot"] < 0 else -1, 1.0, 2)]
        if "spark" in k:
            fx = [sparkle_svg(436, 160, 16)]
        fr.append(F(p, ms, lab, fx=fx, overlay=ov))
    fr.append(F(DEFAULT_END, 400, "回 Default"))
    return fr


def clip_look_up():
    """紙飛機：抬頭、眼睛跟著飛機轉（循環 4 格：左上→上→右上→上）。"""
    fr = []
    seq = [((-30, -30), 4, -4, "看左上"), ((0, -40), 0, 0, "看正上方"), ((30, -30), -4, 4, "看右上"), ((0, -40), 0, 0, "看正上方（接回第 1 格）")]
    for look, rot, er, lab in seq:
        p = dict(view="front", look=look, rot=rot, eye="wide", mouth="o", ear=-14 + er, ear2=-14 - er, sy=1.02, sx=0.99)
        fr.append(F(p, 160, f"抬頭、眼睛跟著飛機轉・{lab}"))
    return fr


def make_toss_props(rd: Path, kind: str):
    if kind == "sniff_eat":
        save_prop(seed_svg(256, 256, 8.0, 30), rd / "seed_prop.png", rd / "seed_icon96.png")
        save_prop(carrot_svg(256, 256, 8.0, 12), rd / "carrot_prop.png", rd / "carrot_icon96.png")
    elif kind == "hop_reach":
        save_prop(bubble_svg(256, 256, 200), rd / "bubble_prop.png", rd / "bubble_icon96.png")
        frames = []
        for t in range(3):
            frames.append(R.finish(R.svg_layer(bubble_pop_svg(256, 256, 150, t))))
        sm = [f.convert("RGBa").resize((160, 160), Image.LANCZOS).convert("RGBA") for f in frames]
        sm[0].save(rd / "pop_burst.webp", save_all=True, append_images=sm[1:], duration=[60, 70, 90], loop=1, lossless=False,
                   quality=86, method=6)
        for t, f in enumerate(frames):
            f.save(rd / f"pop_burst_{t+1}.png")
    elif kind == "pounce":
        save_prop(feather_svg(150, 380, 2.0, 0), rd / "feather_prop.png", rd / "feather_icon96.png")
    elif kind == "tangle":
        save_prop(yarn_svg(150, 230, 100, 0), rd / "yarn_prop.png", rd / "yarn_icon96.png")
    elif kind == "look_up":
        save_prop(plane_svg(256, 256, 4.0, -10), rd / "plane_prop.png", rd / "plane_icon96.png")
        save_prop(leaf_prop_svg(256, 256, 4.5, 20), rd / "leaf_prop.png", rd / "leaf_icon96.png")
        save_prop(petal_svg(256, 256, 5.0, -15), rd / "petal_prop.png", rd / "petal_icon96.png")


# ================================================================== 框架：渲染、檢查、輸出
CLIPS = {
    "eat_grass": dict(make=clip_eat_grass, loop=False,
                      note="播一次（點草圖示）；畫面內含地上的牧草（三根一小把），比比低頭湊過去、叼起草尖一截截吃掉；"
                           "最後一格＝Default。網頁不必另外疊草；要單獨的草圖示用 grass_prop.png。",
                      allow={"propM0": "草尖叼在嘴裡（刻意碰到嘴，不碰眼）"}),
    "sleep_loop": dict(make=clip_sleep_loop, loop=True,
                       note="全部 8 格循環（約 1.4 秒呼吸一輪）；趴著（身體壓扁、頭枕在前、四腳收在肚子下只露前腳尖）、"
                            "蓋藍色小被子、三個 Z 輪流往上飄。被點 → 播 bibi_wake_once。"),
    "wake_once": dict(make=clip_wake_once, loop=False,
                      note="播一次（睡覺時被點）；第 1 格就是嚇一跳彈起（被子往上飛走），伸懶腰是前腳往前、後腳往後伸；最後一格＝Default。"),
    "cry": dict(make=clip_cry, loop=True,
                note="全部 8 格循環（約 1 秒）；照 cry_ref_1012 淚汪汪：大眼含一汪淚＋兩顆高光、眼眶紅、寬淚痕沿臉頰流下、淚珠滑落、"
                     "小撇嘴／抽噎波浪嘴、腮紅加深；四腳著地微蹲，一抖一抖。"),
    "hit": dict(make=clip_hit, loop=False,
                note="播一次（點槌子）；第 1 格就是被敲扁（四腳往外撐），最後一格＝bibi_cry 第 1 格 → 直接接 cry 循環。"
                     "槌子由網頁疊（hammer_prop.png 保留舊版）。"),
    "spin": dict(make=clip_spin, loop=False,
                 note="播一次；第 1～10 格四腳小跑繞一圈（側面→背對→另一側→正面跑回來，小腳兩兩交替邁步、耳朵往後、毛飄）；"
                      "第 12 格＝bibi_dizzy 第 1 格（要接暈眩循環就在第 12 格切過去）；第 13 格＝Default。"),
    "selfie": dict(make=clip_selfie, loop=False,
                   note="播一次；第 3～4 格是快門那一瞬間整隻跳起來（四腳離地收起、星星眼、閃光、YA! 字），不舉手；最後一格＝Default。"),
    "run_r": dict(make=clip_run, loop=True, facing="right", note="全部 8 格循環；四腳對角兩兩交替邁步、身體起伏；網頁負責位移，這裡原地跑。"),
    "run_l": dict(make=clip_run, loop=True, note="同 run_r，面向左。"),
    "run_start_r": dict(make=clip_run_start, loop=False, facing="right", note="播一次；最後一格＝run_r 第 1 格，直接接循環。"),
    "run_stop_r": dict(make=clip_run_stop, loop=False, facing="right", note="播一次；第 1 格＝跑步中（run_r 第 3 格），最後一格＝Default。"),
    "ball_catch": dict(make=clip_ball_catch, loop=False, facing="right",
                       note="播一次；接在 run_r 後面（球在比比右前方）。撲上去用身體壓住球（不抱）、彈起、用鼻子推球；最後一格＝Default＋球停在右邊。"
                            "球道具 ball_prop.png 保留。"),
    "ball_catch_l": dict(make=clip_ball_catch, loop=False, note="同 ball_catch，面向左（接 run_l）。"),
    "pet": dict(make=clip_pet, loop=False,
                note="播一次；網頁同時把手（bibi_pet_v2/hand_prop.png）放在頭頂右上方輕摸（第 2～8 格）；比比趴低、瞇眼、耳朵往後貼、往右上蹭；不畫手。"),
    "highfive": dict(make=clip_boop, loop=False, facing="right",
                     note="10-12 改成「向前伸頭碰鼻子」（天竺鼠不擊掌）：網頁的手指／東西在右前方約 (x 440, y 330)，第 4 格鼻子碰到。最後一格＝Default。"),
    "dance": dict(make=clip_dance, loop=False, note="10-12 改成「原地 popcorn 連跳 3 下＋左右扭」（四腳離地），音符；最後一格＝Default。"),
    "hug": dict(make=clip_hug, loop=False, note="10-12 改成「蹭過來貼貼」：整隻往右側傾倒貼過去（四腳著地）、瞇眼臉紅愛心；最後一格＝Default。"),
    "receive": dict(make=clip_receive, loop=False, facing="right",
                    note="10-12 改成「低頭嗅一嗅」：東西由網頁放在比比右前方地上（約 x 440, y 450），頭前伸、鼻子抖、耳朵前傾、邁一步湊近；最後一格＝Default。"),
    "popcorn": dict(make=clip_popcorn, loop=False,
                    note="播一次（點爆米花圖示 popcorn_icon.png，保留舊檔）；四腳離地垂直彈起、空中扭身踢腳、落地連彈越來越小；最後一格＝Default。"),
    "sniff_eat": dict(make=clip_sniff_eat, loop=False, facing="right",
                      note="撒零食：網頁一次撒 4～6 顆 seed_prop／carrot_prop 在地上，比比跑到一顆旁邊（run_r）後播這組：低頭嗅、咬住叼起來嚼"
                           "（第 1～2 格畫面內含一顆瓜子在嘴前，網頁把被吃那顆移掉）；最後一格＝Default。",
                      allow={"propM0": "瓜子在嘴前（刻意碰到嘴，不碰眼）"}),
    "hop_reach": dict(make=clip_hop_reach, loop=False,
                      note="吹泡泡／落葉／花瓣：網頁讓 bubble_prop（或 leaf_prop、petal_prop）飄到比比頭頂上方約 (x 256, y 60)，"
                           "第 3 格鼻子頂到 → 網頁在那個位置播 pop_burst.webp（3 格，60/70/90ms）；最後一格＝Default。"),
    "pounce": dict(make=clip_pounce, loop=False, facing="right",
                   note="羽毛棒：網頁把 feather_prop 在比比右前方地面附近晃（約 x 470, y 440）；第 5 格撲出去、第 6 格壓到；最後一格＝Default。"),
    "tangle": dict(make=clip_tangle, loop=False,
                   note="毛線球：yarn_prop 滾過去 → run_r → ball_catch（撲到）→ 播這組：線纏在身上、扭兩下、彈開掙脫；最後一格＝Default。"),
    "look_up": dict(make=clip_look_up, loop=True,
                    note="紙飛機：plane_prop 在頭頂飛時循環這 4 格（眼睛左上→上→右上→上）；飛機落地後 run_r 跑過去 → sniff_eat 前兩格（或 receive）聞一聞。"
                         "落葉／花瓣（leaf_prop、petal_prop 也放在這個資料夾）沿用 hop_reach／sniff_eat。"),
}


def nudge_fx(fxl, boxes, p, fr):
    """版面鐵則：特效不准疊到身體或臉。疊到的特效沿「身體中心→特效中心」方向往外推，直到不碰（最多 90px），
    推完不准出畫布。回傳有沒有推過（有就重畫一次）。"""
    if fr.get("fx_on_body"):
        return False
    ms = boxes.get("__masks", {})
    body = ms.get("body")
    if body is None:
        return False
    occ = body | ms.get("face", np.zeros_like(body))
    H = body.shape[0]
    k512 = R.SIZE / H
    by, bx = np.nonzero(body)
    cx, cy = bx.mean(), by.mean()
    moved = False
    for j in range(len(fxl)):
        m = ms.get(f"fx{j}")
        if m is None or int((m & occ).sum()) <= 1:
            continue
        ys, xs = np.nonzero(m)
        vx, vy = xs.mean() - cx, ys.mean() - cy
        n = math.hypot(vx, vy) or 1
        vx, vy = vx / n, vy / n
        best = None
        for step in range(1, 24):
            dx, dy = int(round(vx * step)), int(round(vy * step))
            sh = np.roll(np.roll(m, dy, 0), dx, 1)
            if (xs.min() + dx) < 1 or (xs.max() + dx) > H - 2 or (ys.min() + dy) < 1 or (ys.max() + dy) > H - 2:
                break
            if int((sh & occ).sum()) <= 1:
                best = (dx, dy)
                break
        if best is None:
            continue
        wx, wy = best[0] * k512, best[1] * k512
        if p.get("facing") == "right":
            wx = -wx
        fxl[j] = f'<g transform="translate({wx:.1f},{wy:.1f})">{fxl[j]}</g>'
        moved = True
    return moved


def render(name):
    cfg = CLIPS[name]
    frs = cfg["make"]()
    imgs, checks, selfc = [], [], []
    for fr in frs:
        p = dict(fr["pose"])
        if cfg.get("facing") == "right":
            p["facing"] = "right" if p.get("facing", "left") == "left" else "left"
        fxl = fr.get("fx")
        fxl = [fxl] if isinstance(fxl, str) else list(fxl or [])
        for _round in range(3):
            can, boxes = Q.compose(p, props_back=fr.get("props_back"), props_mid=fr.get("props_mid"),
                                   props_front=fr.get("props_front"), fx=fxl, fx_back=fr.get("fx_back"),
                                   overlay_fn=fr.get("overlay"))
            moved = nudge_fx(fxl, boxes, p, fr)
            if not moved:
                break
        fr["fx"] = fxl
        imgs.append(R.finish(can))
        selfc.append(Q.quad_selfcheck(fr["pose"], boxes))
        checks.append(boxes)
    return frs, imgs, checks, selfc


def verify(name, frs, imgs, checks):
    """全身入鏡＋特效／道具不壓眼嘴（臉遮罩外擴 2px）＋特效彼此不重疊。"""
    bad = []
    allow = CLIPS[name].get("allow", {})
    for i, (im, bx) in enumerate(zip(imgs, checks)):
        if not R.inside_canvas(im, 2):
            bad.append(f"第 {i+1} 格碰到畫布邊")
        ms = bx.get("__masks", {})
        face = ms.get("face")
        if face is None:
            continue
        fpad = face.copy()
        for sh in ((1, 0), (-1, 0), (0, 1), (0, -1), (2, 0), (-2, 0), (0, 2), (0, -2)):
            fpad |= np.roll(face, sh, axis=(0, 1))
        keys = [k for k in ms if k.startswith(("fx", "propF", "propM")) and not k.startswith("fxB")]   # fxB 畫在身體後面
        for k in keys:
            if k in allow:
                # 允許碰嘴：只檢查有沒有碰到眼睛那一半（臉遮罩上半部）
                ys = np.nonzero(face.any(axis=1))[0]
                if len(ys):
                    top = face.copy()
                    top[int((ys.min() + ys.max()) / 2) + 2:] = False
                    n = int((top & ms[k]).sum())
                    if n:
                        bad.append(f"第 {i+1} 格 {k} 壓到眼睛 {n}")
                continue
            n = int((fpad & ms[k]).sum())
            if n:
                bad.append(f"第 {i+1} 格 {k} 壓到臉 {n}")
        body = ms.get("body")
        for k in keys:
            if k.startswith("fx") and body is not None and k not in allow and not frs[i].get("fx_on_body"):
                n = int((body & ms[k]).sum())
                if n > 6:
                    bad.append(f"第 {i+1} 格 {k} 疊到身體 {n}")
        fxk = [k for k in keys if k.startswith("fx") and not k.startswith("fxB")]
        for a in range(len(fxk)):
            for b in range(a + 1, len(fxk)):
                n = int((ms[fxk[a]] & ms[fxk[b]]).sum())
                if n:
                    bad.append(f"第 {i+1} 格 {fxk[a]}×{fxk[b]} 特效互相重疊 {n}")
    return bad


def backup_dir(rd: Path):
    if not rd.exists() or (rd / ".quad1012").exists():
        return None
    base = rd.parent / f"{rd.name}_old"
    dst = base
    n = 2
    while dst.exists():
        dst = rd.parent / f"{rd.name}_old{n}"
        n += 1
    shutil.copytree(rd, dst)
    return dst


def write_storyboard(name, frs, durs, path, selfc, bad):
    cfg = CLIPS[name]
    lines = [f"# 比比・{name}（10-12 四腳天竺鼠版，{len(frs)} 格）", "",
             "- 依據：Andy 10-12「比比是天竺鼠，他是 4 隻腳的……不可以因為配合互動就改變身體原有設定」。",
             "- 做法：`scripts/anim/bibi_quad.py`（原版 Default 像素本體＋四隻獨立小腳，不畫手）＋"
             "`scripts/anim/bibi_quad_moves.py` 關鍵格（ease 補間）。",
             "- 規格：512×512 透明、全身入鏡；成品 160px 動態 WebP（anim.webp）；第 1 格就是動作、最後一格回 Default。",
             f"- 播放：{'循環' if cfg['loop'] else '播一次（loop=1）'}；{cfg['note']}",
             f"- 合計 {sum(durs)} ms。",
             f"- 四腳自檢（每格：四隻腳都在、腳在身體下半部、著地格≥2 腳貼地、無手掌）：{'全部通過' if not any(selfc) else '有問題，見下表'}。",
             f"- 重疊檢查（特效／道具 vs 眼嘴、特效彼此）：程式 {len(frs)} 格 {len(bad)} 筆。", "",
             "| 格 | 動作／表情 | 停留 ms | 四腳自檢 |", "|---|---|---|---|"]
    for j, (fr, d, sc) in enumerate(zip(frs, durs, selfc)):
        lines.append(f"| {j+1:02d} | {fr['label']} | {d} | {'OK' if not sc else '；'.join(sc)} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--repo-out", default="docs/anim")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    out, rep = Path(a.out), Path(a.repo_out)
    names = [n for n in a.only.split(",") if n] or list(CLIPS)
    report = {}
    for name in names:
        frs, imgs, checks, selfc = render(name)
        durs = [fr["ms"] for fr in frs]
        od = out / name / "frames"
        if od.exists():
            shutil.rmtree(od)
        od.mkdir(parents=True, exist_ok=True)
        for j, im in enumerate(imgs):
            im.save(od / f"{j+1:02d}.png")
        rd = rep / f"bibi_{name}"
        bk = backup_dir(rd)
        rd.mkdir(parents=True, exist_ok=True)
        (rd / ".quad1012").write_text("10-12 四腳版\n", encoding="utf-8")
        kb, q = V.save_webps(imgs, durs, rd / "anim.webp", out / name / "anim512.webp", CLIPS[name]["loop"])
        bad = verify(name, frs, imgs, checks)
        n = len(imgs)
        pick = list(range(n)) if n <= 12 else sorted({round(i * (n - 1) / 11) for i in range(12)})
        V.contact_sheet(imgs, frs, rd / "sheet_12.png", pick, 4, f"bibi_{name}（四腳版）：12 格接觸表（共 {n} 格）")
        V.contact_sheet(imgs, frs, rd / "sheet_all.png", None, 4, f"bibi_{name}（四腳版）：全部 {n} 格")
        V.compare_sheet(imgs, frs, rd / "compare_default.png")
        write_storyboard(name, frs, durs, rd / "storyboard.md", selfc, bad)
        extra = CLIPS[name].get("extra")
        if extra:
            extra(rd)
        report[name] = dict(frames=n, kb=round(kb, 1), q=q, ms=sum(durs), overlap=bad,
                            selfcheck=[f"{i+1}:{'；'.join(s)}" for i, s in enumerate(selfc) if s], backup=str(bk) if bk else "")
        print(name, json.dumps(report[name], ensure_ascii=False), flush=True)
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")


CLIPS["eat_grass"]["extra"] = lambda rd: make_grass_prop(rd / "grass_prop.png")
for _k in ("sniff_eat", "hop_reach", "pounce", "tangle", "look_up"):
    CLIPS[_k]["extra"] = (lambda kk: (lambda rd: make_toss_props(rd, kk)))(_k)

if __name__ == "__main__":
    main()
