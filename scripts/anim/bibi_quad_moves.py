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
from PIL import Image

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
def blade_svg(ax, ay, bx, by, bend=10.0, w=12.0, head=True, bite=False) -> str:
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
        ang = math.degrees(math.atan2(-uy, -ux))
        sl = w * 3.2
        cx, cy = ax - ux * sl * 0.38, ay - uy * sl * 0.38
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
    for i, (oy, ox, w) in enumerate(((-3, 6, 11), (2, -4, 12.5), (6, 12, 10.5))):
        a_x, a_y = ax + ox, gy + oy * 0.6 - 2
        b_x, b_y = bx + ox * 0.15, by + oy * (0.35 if lifted else 0.6)
        if not lifted:
            b_y = gy + oy * 0.6 - 4
        bend = 6 if lifted else 3
        out += blade_svg(a_x, a_y, b_x, b_y, bend=bend * (1 + 0.3 * i), w=w, head=(L > 60 and i != 1), bite=bite)
    if L > 70:
        out += leaf_svg(ax + L * 0.35, gy - 4, 30, -158, 9)
    return out


def eat_pose(h=0.0, bite=0.0, chew="", eye="default", cheek=0.0, ear=0.0, sq=0.0):
    """側面面向左吃草：h＝低頭深度 0～1（越大臉越低、越往前湊）；bite＝咬下去那一下的往前探。"""
    look = (-8 - 16 * h - 4 * bite, 46 + 60 * h + 6 * bite)
    return dict(view="side", x=R.CX + 44, shear=0.1 + 0.12 * h + 0.04 * bite, sy=0.9 - 0.06 * h - sq, sx=1.06 + sq * 0.5,
                look=look, mouth=chew or "nibble_c", eye=eye, cheek=cheek, ear=ear, ear2=ear * 0.7,
                legs={"bl": (6 * h, 0, 0, 0), "br": (6 * h, 0, 0, 0)})


def mouth_at(p):
    pp = {**Q.QDEF, **Q.EARS.get(p.get("view", "front"), {}), **p}
    return Q.feat_world(pp, "mouth")


def clip_eat_grass():
    fr = []
    # 草把：長度一截截變短（從 150 吃到 0）
    lens = [150, 150, 150, 150, 122, 122, 122, 92, 92, 92, 60, 60, 30, 0, 0, 0]
    ex_rest = None

    def grass(p, L, lifted=True, bite=False):
        mx, my = mouth_at(p)
        if not lifted:
            return [grass_bunch_svg(mx - 10, GROUND - 8, L, lifted=False)]
        return [grass_bunch_svg(mx + 2, my + 4, L, lifted=True, bite=bite)]

    seq = [
        # (pose, ms, label, grass_len, lifted, fx)
        (eat_pose(0.55, 0, "o", "default", 0, -12), 90, "低頭湊近草、鼻子嗅嗅（耳朵前傾）", 150, False, "sniff"),
        (eat_pose(0.75, 0.4, "o", "default", 0, -16), 80, "再湊近一點嗅（鼻子抖）", 150, False, "sniff2"),
        (eat_pose(0.9, 1.0, "nibble_a", "default", 0, -6), 70, "張嘴露門牙咬住草尖", 150, True, ""),
        (eat_pose(0.8, 0, "nibble_c", "smile", 0.8, 8), 80, "叼起來嚼（臉頰鼓、耳朵抖）", 150, True, "crumb0"),
        (eat_pose(0.82, 0.3, "nibble_d", "smile", 1.1, -4), 80, "嚼（嘴形換邊）草短一截", 122, True, "crumb1"),
        (eat_pose(0.8, 0, "nibble_b", "smile", 0.9, 8), 80, "嚼（半開）", 122, True, ""),
        (eat_pose(0.92, 1.0, "nibble_a", "default", 0.3, -6), 70, "再咬一口（往前湊）", 122, True, ""),
        (eat_pose(0.82, 0, "nibble_c", "smile", 1.1, 8), 80, "嚼、草又短一截", 92, True, "crumb2"),
        (eat_pose(0.84, 0.3, "nibble_d", "smile", 1.2, -4), 80, "嚼（臉頰最鼓）", 92, True, ""),
        (eat_pose(0.94, 1.0, "nibble_a", "default", 0.4, -6), 70, "第三口", 92, True, ""),
        (eat_pose(0.82, 0, "nibble_c", "smile", 1.2, 8), 80, "嚼、草剩一小截", 60, True, "crumb3"),
        (eat_pose(0.86, 0.3, "nibble_d", "smile", 1.2, -4), 80, "嚼嚼", 60, True, ""),
        (eat_pose(0.78, 0.6, "nibble_c", "smile", 1.3, 6), 90, "最後一截吸進去", 30, True, "crumb4"),
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
        fr.append(F(p, ms, lab, props_mid=grass(p, L, lifted, bite=L < 150), fx=fxs))
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


# ================================================================== 框架：渲染、檢查、輸出
CLIPS = {
    "eat_grass": dict(make=clip_eat_grass, loop=False,
                      note="播一次（點草圖示）；畫面內含地上的牧草（三根一小把），比比低頭湊過去、叼起草尖一截截吃掉；"
                           "最後一格＝Default。網頁不必另外疊草；要單獨的草圖示用 grass_prop.png。",
                      allow={"propM0": "草尖叼在嘴裡（刻意碰到嘴，不碰眼）"}),
}


def render(name):
    cfg = CLIPS[name]
    frs = cfg["make"]()
    imgs, checks, selfc = [], [], []
    for fr in frs:
        p = dict(fr["pose"])
        if cfg.get("facing") == "right":
            p["facing"] = "right" if p.get("facing", "left") == "left" else "left"
        can, boxes = Q.compose(p, props_back=fr.get("props_back"), props_mid=fr.get("props_mid"),
                               props_front=fr.get("props_front"), fx=fr.get("fx"), fx_back=fr.get("fx_back"))
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
        keys = [k for k in ms if k.startswith(("fx", "propF", "propM"))]
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

if __name__ == "__main__":
    main()
