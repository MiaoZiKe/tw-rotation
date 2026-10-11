"""比比互動動作 v2：用 bibi_rig 骨架逐格擺姿勢（關鍵格＋ease 補間），不再變形原 GIF。

Andy 2026-10-11 退件：「需要是點擊互動按鈕，他會有對應動作，不是基於原本的 GIF 加點東西上去。
例如我點球，他會跟著球跑，我點草，他會有吃草畫面等等」＋「動作要再豐富生動一點」。
每組都照動畫 12 原則：預備／擠壓伸展、跟隨與重疊（耳朵、毛、尾巴慢 1～2 格）、弧線與次要動作、
表情 ≥3 種穿插、節奏有快有慢、特效畫進素材（速度線、塵土、星星…）。

用法
----
    python scripts/anim/bibi_moves_v2.py --out <scratchpad>/bibi_v2 --repo-out docs/anim [--only run_r,ball_catch]

輸出
----
<out>/<名>/frames/NN.png（512 透明）、<out>/<名>/anim512.webp
<repo-out>/bibi_<名>/anim.webp（160px 動態 WebP ≤60KB）、sheet_12.png（12 格接觸表）、sheet_all.png、storyboard.md
道具：<repo-out>/bibi_ball_catch/ball_prop.png（512 透明球）
每組跑：全身入鏡、效果／道具不壓臉（逐件外框）、相鄰格差異（肢體位置真的變）。
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
import bibi_rig as R  # noqa: E402

FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
TAU = 2 * math.pi


# ================================================================== 共用小工具
def ball_layer(x, y, ang, r=42.0):
    return R.svg_layer(R.ball_svg(x, y, r, ang))


def fx_part(name, x, y, k=0.7, rot=0.0):
    """效果部件（總表的 fx_*）→ props 條目。"""
    return (R.part(name, k), x, y, rot, (0.5, 0.5))


# ================================================================== 跑步循環
def run_pose(i: int, n: int = 8) -> dict:
    """面向左原地跑。a=0 前掌落地、a=π 後腳落地；a=π/2、3π/2 騰空最高。"""
    a = TAU * i / n
    lift = 12 * math.sin(a) ** 2                       # 一個循環彈兩次
    squash = math.cos(a) ** 2                          # 落地格壓扁
    sy = 1 - 0.075 * squash + 0.05 * (1 - squash)
    sx = 1 + 0.06 * squash - 0.03 * (1 - squash)

    def limb(ph, reach=27, up=15, rot=26):
        x = -reach * math.cos(ph)
        y = up * min(0.0, math.sin(ph))                # 往前擺時抬起
        if math.sin(ph) > 0:                           # 支撐期：腳踩住地，抵銷身體騰空
            y += lift * 0.8
        return (x, y, rot * math.cos(ph))

    return dict(
        view="side", y=R.FOOT_Y - lift, sx=sx, sy=sy,
        rot=-6 - 3 * math.sin(2 * a - 0.6),            # 前傾＋點頭（弧線）
        flutter=7, fphase=2 * a,
        ear=16 + 14 * math.sin(2 * a - 1.7),           # 跟隨：比身體慢約 1 格
        eye="dot", mouth="open", blush=1.0,
        look=(0.0, 0.012 * math.sin(2 * a - 0.8)),
        fp_near=limb(a), fp_far=limb(a + 0.8, 22, 12),
        bf_near=limb(a + math.pi, 25, 13, 30), bf_far=limb(a + math.pi + 0.8, 21, 10, 30),
        tail=(3 * math.sin(2 * a - 1.0), 5 * math.sin(2 * a - 1.5), 18 * math.sin(2 * a - 1.3)),
    )


def run_fx(i: int, n: int = 8, x0: float = 400.0) -> list[str]:
    """速度線（背後，每格位置不同）＋塵土（後腳／前掌落地那兩格冒、下一格散開）。"""
    out = [R.speed_lines_svg(x0 + (i % 3) * 6, 318 + (i % 2) * 5, n=3, length=52, gap=20, alpha=0.75, seed=i)]
    k = i % (n // 2)
    if k in (0, 1):
        s = 0.8 if k == 0 else 1.05
        a = 1.0 if k == 0 else 0.55
        bx = 372 + (12 if k == 1 else 0) + (10 if i >= n // 2 else 0)
        out.append(R.dust_svg(bx, 468 - 4 * k, s, a))
    return out


def clip_run() -> list[dict]:
    fr = []
    ms = [80, 70, 80, 70, 80, 70, 80, 70]   # 落地格稍停、騰空格快
    lab = ["前掌落地（壓扁）", "推地", "騰空最高（拉長）", "後腳往前收", "後腳落地（壓扁）", "前掌往前伸", "騰空", "前掌準備落地"]
    for i in range(8):
        fr.append(dict(pose=run_pose(i), fx=run_fx(i), ms=ms[i], label=lab[i]))
    return fr


def clip_run_start() -> list[dict]:
    idle = dict(view="side", eye="dot", mouth="w", ear=4)
    crouch = dict(view="side", sy=0.84, sx=1.1, rot=6, ear=-14, flutter=-3, eye="squint", mouth="flat",
                  fp_near=(6, 2, 10), bf_near=(14, 0, 18), bf_far=(12, 0, 18), tail=(0, 4, -10))
    push = dict(view="side", y=R.FOOT_Y - 14, sy=1.12, sx=0.92, rot=-13, ear=34, flutter=9, fphase=1.0,
                eye="wide", mouth="open", fp_near=(-30, -14, -24), fp_far=(-24, -10, -20),
                bf_near=(30, -2, 40), bf_far=(26, -4, 36), tail=(6, -4, 22))
    return [
        dict(pose=idle, ms=260, label="站好（看前方）"),
        dict(pose=R.lerp_pose(idle, crouch, R.ease(0.55)), ms=90, label="往下縮（預備）", fx=[]),
        dict(pose=crouch, ms=200, label="蹲低蓄力、耳朵往前甩", fx=[]),
        dict(pose=push, ms=90, label="蹬出去（拉長）", fx=[R.dust_svg(388, 466, 1.0, 1.0), R.speed_lines_svg(410, 330, 2, 40, 22, 0.6)]),
        dict(pose=run_pose(0), ms=80, label="接跑步循環第 1 格", fx=run_fx(0)),
    ]


def clip_run_stop() -> list[dict]:
    brake = dict(view="side", sy=0.88, sx=1.09, rot=12, ear=-30, flutter=-8, fphase=0.5, eye="squint", mouth="o",
                 fp_near=(-36, 0, -12), fp_far=(-30, 0, -10), bf_near=(4, 0, 0), bf_far=(2, 0, 0), tail=(-4, 2, -24))
    rock = dict(view="side", sy=1.05, sx=0.97, rot=-7, ear=-18, flutter=-5, fphase=1.6, eye="dot", mouth="o",
                fp_near=(-14, 0, -6), bf_near=(6, -4, 10), tail=(-2, -2, -14))
    settle = dict(view="side", sy=0.98, sx=1.01, rot=3, ear=8, flutter=0, eye="dot", mouth="w", blush=1.2,
                  tail=(1, 1, 6))
    idle = dict(view="side", eye="dot", mouth="w", ear=2, blush=1.0)
    return [
        dict(pose=run_pose(2), ms=70, label="跑步中", fx=run_fx(2)),
        dict(pose=brake, ms=140, label="急煞：往後仰、前掌撐地、耳毛往前甩",
             fx=[R.dust_svg(70, 466, 1.0), R.dust_svg(104, 470, 0.7, 0.8)]),
        dict(pose=rock, ms=110, label="身體往前晃回來（耳朵還在前）", fx=[R.dust_svg(60, 458, 1.25, 0.45)]),
        dict(pose=settle, ms=150, label="回彈、耳朵慢一拍倒回"),
        dict(pose=dict(idle, eye_open=0.2), ms=90, label="眨眼"),
        dict(pose=idle, ms=500, label="站好"),
    ]


# ================================================================== 撲球
def clip_ball_catch() -> list[dict]:
    """面向左：球在前方地上滾，比比急煞蓄力→飛撲→抱住→抱著球滾一圈→轉正面抱球開心。"""
    BR = 42
    frames = []

    def F(pose, ms, label, ball=None, ball_layer_="mid", fx=None, props=None, props_back=None):
        frames.append(dict(pose=pose, ms=ms, label=label, ball=ball, ball_layer=ball_layer_, fx=fx or [],
                           props_front=props or [], props_back=props_back or []))

    # 1 跑過來（盯著球）
    p1 = dict(run_pose(2), x=330, eye="wide", mouth="open")
    F(p1, 110, "追球跑來（圓眼盯球）", ball=(118, 440, -20), fx=run_fx(2, x0=480 - 70))
    # 2 急煞＋預備
    F(dict(view="side", x=318, sy=0.87, sx=1.09, rot=9, ear=-22, flutter=-6, fphase=0.4, eye="squint",
           mouth="flat", fp_near=(-30, 0, -14), fp_far=(-24, 0, -12), bf_near=(8, 0, 6), tail=(-4, 2, -22)),
      130, "急煞、瞇眼瞄準（專注）", ball=(124, 440, -45),
      fx=[R.dust_svg(186, 468, 0.9), R.dust_svg(160, 472, 0.6, 0.8)])
    # 3 蹲到最低蓄力（屁股翹、後腳踩緊）
    F(dict(view="side", x=318, sy=0.79, sx=1.14, rot=3, ear=14, flutter=2, fphase=1.2, eye="squint", mouth="flat",
           fp_near=(-10, 2, -6), fp_far=(-8, 2, -6), bf_near=(18, 2, 22), bf_far=(14, 2, 22), tail=(2, 6, 16),
           look=(0.0, 0.03)),
      230, "蹲到最低蓄力（停頓）", ball=(128, 440, -60),
      props=[fx_part("fx_exclaim", 300, 230, 0.75, 8)])
    # 4 飛撲（拉長、前掌伸、後腳拖、耳朵往後）
    F(dict(view="side", x=262, y=438, sy=1.15, sx=0.9, rot=-22, ear=38, flutter=10, fphase=2.0, eye="wide",
           mouth="open", fp_near=(-34, -16, -38), fp_far=(-28, -12, -32), bf_near=(30, -6, 46),
           bf_far=(26, -8, 42), tail=(8, -6, 26)),
      80, "飛撲！（拉長）", ball=(134, 440, -80),
      fx=[R.speed_lines_svg(410, 300, 3, 56, 20, 0.8, 1)])
    # 5 下墜接近球（前掌往下抓）
    F(dict(view="side", x=222, y=448, sy=1.06, sx=0.96, rot=-14, ear=30, flutter=8, fphase=2.8, eye="wide",
           mouth="o", fp_near=(-16, 10, -24), fp_far=(-12, 8, -20), bf_near=(24, -10, 36), bf_far=(20, -10, 32),
           tail=(6, -6, 20)),
      80, "撲下去（O 嘴）", ball=(140, 442, -95),
      fx=[R.speed_lines_svg(372, 290, 2, 44, 22, 0.55, 2)])
    # 6 抱住球（壓扁、星星迸出）
    hug = dict(view="side", x=228, sy=0.84, sx=1.12, rot=-5, ear=-16, flutter=-6, fphase=3.4, eye="squint",
               mouth="open", fp_near=(-22, -34, -60), fp_far=(-18, -28, -50), bf_near=(8, 0, 4), bf_far=(6, 0, 4),
               tail=(-3, 3, -18))
    F(hug, 170, "抱住球！（壓扁＋星星）", ball=(148, 446, -100),
      fx=[R.star_svg(84, 410, 15, 10), R.star_svg(70, 456, 11, -20, "#FFE58A"), R.star_svg(108, 380, 9, 30)])
    # 7～11 抱著球往前滾一圈（整組旋轉；耳朵、尾巴、毛跟著甩）
    roll = dict(hug, sy=0.9, sx=1.04, eye="smile", mouth="open", ear=24, flutter=8, blush=1.4,
                fp_near=(-22, -34, -60), fp_far=(-18, -28, -50), tail=(4, -2, 20))
    pivot = (200.0, 400.0)
    seq = [(-72, 34, -96), (-144, 46, -150), (-216, 46, -150), (-288, 36, -104), (-360, 22, -40)]
    for j, (gr, gx, gy) in enumerate(seq):
        pp = dict(roll, grot=gr, gpx=pivot[0], gpy=pivot[1], gx=gx, gy=gy, fphase=3.4 + j, ear=24 + 10 * math.sin(j),
                  tail=(4, -2, 20 * math.cos(j)))
        # 動作弧線：畫在世界座標（不跟著轉），在滾動方向後方
        arcs = R.svg_layer(
            f'<path d="M {pivot[0]+gx+150:.0f} {pivot[1]+gy-120:.0f} A 190 190 0 0 1 {pivot[0]+gx+190:.0f} {pivot[1]+gy+40:.0f}" '
            f'fill="none" stroke="{R.INK}" stroke-width="5" stroke-linecap="round" stroke-opacity="0.7"/>'
            f'<path d="M {pivot[0]+gx+128:.0f} {pivot[1]+gy-150:.0f} A 220 220 0 0 1 {pivot[0]+gx+170:.0f} {pivot[1]+gy-90:.0f}" '
            f'fill="none" stroke="{R.INK}" stroke-width="4" stroke-linecap="round" stroke-opacity="0.5"/>')
        frames.append(dict(pose=pp, ms=[70, 60, 60, 70, 90][j], label=f"抱球翻滾 {abs(gr)}°（閉眼笑）",
                           ball=(148, 446, -100 - 72 * (j + 1)), ball_layer="mid", fx=[], post=arcs,
                           props_front=[], props_back=[]))
    # 12 落地（壓扁、塵土）
    F(dict(view="side", x=236, sy=0.82, sx=1.13, rot=4, ear=-20, flutter=-7, fphase=0.3, eye="squint", mouth="w",
           fp_near=(-22, -34, -60), fp_far=(-18, -28, -50), tail=(-4, 4, -20)),
      120, "滾完落地（壓扁、耳朵往前甩）", ball=(156, 446, -470),
      fx=[R.dust_svg(70, 470, 1.0, 0.9), R.dust_svg(400, 470, 0.9, 0.8)])
    # 13 轉正面、抱球跳一下（星星眼）
    front = dict(view="front", x=248, hands_front=True, blush=1.5, mouth="smile")
    F(dict(front, y=466, sy=1.08, sx=0.95, eye="star", ear=-14, ear2=-14),
      200, "轉正面抱球（星星眼）", ball=(248, 424, -470),
      fx=[R.star_svg(96, 236, 13, 0), R.star_svg(404, 222, 15, 18), R.star_svg(430, 286, 9, 30)])
    # 14 抱著球左晃（彎月眼、愛心）
    F(dict(front, rot=-7, sy=0.97, sx=1.02, eye="arc", ear=10, ear2=-4),
      220, "抱緊左晃（彎月眼）", ball=(240, 430, -480),
      props=[fx_part("fx_heart", 404, 214, 0.6, 12)])
    # 15 右晃
    F(dict(front, rot=7, sy=0.98, sx=1.01, eye="arc", ear=-4, ear2=10),
      220, "抱緊右晃", ball=(256, 430, -460),
      props=[fx_part("fx_heart", 410, 176, 0.5, 18), fx_part("fx_hearts_small", 96, 214, 0.6, -10)])
    # 16 滿足
    F(dict(front, rot=0, eye="dot", mouth="w", blush=1.2, ear=2, ear2=2),
      700, "抱著球滿足（回待機姿勢）", ball=(248, 430, -470))
    return frames


# ================================================================== 渲染
CLIPS = {
    "run_r": dict(make=clip_run, facing="right", loop=True, note="全部 8 格循環（第 8 格接回第 1 格）；網頁負責位移，這裡原地跑。"),
    "run_l": dict(make=clip_run, facing="left", loop=True, note="同 run_r，面向左。"),
    "run_start_r": dict(make=clip_run_start, facing="right", loop=False, note="播一次；最後一格＝run_r 第 1 格，直接接循環。"),
    "run_stop_r": dict(make=clip_run_stop, facing="right", loop=False, note="播一次；第 1 格＝跑步中，最後一格＝側面站好。"),
    "ball_catch": dict(make=clip_ball_catch, facing="right", loop=False,
                       note="播一次；接在 run_r 後面（球在比比右前方）。最後一格停住＝正面抱球。"),
    "ball_catch_l": dict(make=clip_ball_catch, facing="left", loop=False, note="同 ball_catch，面向左（接 run_l）。"),
}


def render_clip(name: str):
    cfg = CLIPS[name]
    frs = cfg["make"]()
    imgs, checks = [], []
    for fr in frs:
        pose = dict(fr["pose"], facing=cfg["facing"])
        mid = []
        if fr.get("ball"):
            bx, by, ang = fr["ball"]
            mid = [ball_layer(bx, by, ang)]
        can, boxes = R.compose(pose, props_mid=mid, props_front=fr.get("props_front"),
                               props_back=fr.get("props_back"), fx=fr.get("fx"))
        if fr.get("post") is not None:
            post = fr["post"]
            if cfg["facing"] == "right":
                post = post.transpose(Image.FLIP_LEFT_RIGHT)
                post = post.transform(post.size, Image.AFFINE, (1, 0, (R.SIZE * R.S - 2 * R.CX * R.S), 0, 1, 0))
            boxes["fx_arc"] = post.getchannel("A").getbbox()
            can.alpha_composite(post)
        im = R.finish(can)
        imgs.append(im)
        checks.append({k: R.bbox512(v) for k, v in boxes.items() if v})
    return frs, imgs, checks


def verify(name, frs, imgs, checks):
    """全身入鏡＋效果／道具不壓臉＋相鄰格差異。回傳 (問題清單, 相鄰差)。"""
    bad = []
    for i, (im, bx) in enumerate(zip(imgs, checks)):
        if not R.inside_canvas(im, 2):
            bad.append(f"第 {i+1} 格碰到畫布邊（裁切）")
        face = bx.get("face")
        for k, b in bx.items():
            if k.startswith("fx") or k.startswith("propF") or k.startswith("propM"):
                if R.overlap(face, b) > 0:
                    bad.append(f"第 {i+1} 格 {k} 壓到臉 {tuple(round(v) for v in b)}")
    diffs = []
    for a, b in zip(imgs, imgs[1:] + ([imgs[0]] if CLIPS[name]["loop"] else [])):
        A = np.asarray(a.getchannel("A")) > 128
        B = np.asarray(b.getchannel("A")) > 128
        diffs.append(round(float((A ^ B).sum()) / 1000, 1))  # 輪廓不同的像素（千）
    return bad, diffs


def contact_sheet(imgs, frs, path, pick=None, cols=4, title=""):
    idx = pick if pick is not None else list(range(len(imgs)))
    cell = 256
    rows = math.ceil(len(idx) / cols)
    head = 40
    sh = Image.new("RGBA", (cols * cell, rows * (cell + 28) + head), (30, 33, 40, 255))
    d = ImageDraw.Draw(sh)
    f = ImageFont.truetype(FONT, 17)
    ft = ImageFont.truetype(FONT, 20)
    d.text((10, 8), title, font=ft, fill=(240, 240, 240))
    bgs = [(250, 246, 238, 255), (238, 243, 250, 255)]
    for n, i in enumerate(idx):
        x, y = (n % cols) * cell, head + (n // cols) * (cell + 28)
        bg = Image.new("RGBA", (cell, cell), bgs[n % 2])
        bg.alpha_composite(imgs[i].resize((cell, cell), Image.LANCZOS))
        sh.alpha_composite(bg, (x, y + 28))
        d.text((x + 6, y + 4), f"{i+1:02d} {frs[i]['label']}"[:18], font=f, fill=(235, 235, 235))
    sh.convert("RGB").save(path)


def save_webps(imgs, durs, p160, p512, loop, target_kb=60):
    lp = 0 if loop else 1
    sm = [im.convert("RGBa").resize((160, 160), Image.LANCZOS).convert("RGBA") for im in imgs]
    q = 86
    while True:
        sm[0].save(p160, save_all=True, append_images=sm[1:], duration=durs, loop=lp, lossless=False,
                   quality=q, method=6)
        kb = Path(p160).stat().st_size / 1024
        if kb <= target_kb or q <= 40:
            break
        q -= 6
    imgs[0].save(p512, save_all=True, append_images=imgs[1:], duration=durs, loop=lp, lossless=False,
                 quality=88, method=6)
    return kb, q


def write_storyboard(name, frs, durs, path, extra=""):
    cfg = CLIPS[name]
    total = sum(durs)
    lines = [f"# 比比・{name}（v2 骨架重做，{len(frs)} 格）", "",
             "- 退件原因（Andy 10-11）：舊版是原 GIF 第 0 張變形＋貼東西，沒有真的肢體動作。",
             "- 做法：`scripts/anim/bibi_rig.py` 官方部件骨架（本體、耳朵、肉掌、腳、尾巴、眼、嘴、腮紅獨立擺位）＋"
             "`scripts/anim/bibi_moves_v2.py` 關鍵格（ease 補間，不是 crossfade）。",
             "- 規格：512×512 透明、全身入鏡、場景座標中心 x=248、腳底 y=482；成品 160px 動態 WebP（anim.webp）。",
             f"- 播放：{'循環' if cfg['loop'] else '播一次（loop=1）'}；{cfg['note']}",
             f"- 合計 {total} ms。{extra}", "",
             "| 格 | 動作／表情 | 停留 ms |", "|---|---|---|"]
    for j, (fr, d) in enumerate(zip(frs, durs)):
        lines.append(f"| {j+1:02d} | {fr['label']} | {d} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_ball_prop(path):
    lay = R.svg_layer(R.ball_svg(256, 256, 236, 0, stroke=18))
    lay.convert("RGBa").resize((512, 512), Image.LANCZOS).convert("RGBA").save(path)


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
        frs, imgs, checks = render_clip(name)
        durs = [fr["ms"] for fr in frs]
        od = out / name / "frames"
        od.mkdir(parents=True, exist_ok=True)
        for j, im in enumerate(imgs):
            im.save(od / f"{j+1:02d}.png")
        rd = rep / f"bibi_{name}"
        rd.mkdir(parents=True, exist_ok=True)
        kb, q = save_webps(imgs, durs, rd / "anim.webp", out / name / "anim512.webp", CLIPS[name]["loop"])
        bad, diffs = verify(name, frs, imgs, checks)
        n = len(imgs)
        pick = list(range(n)) if n <= 12 else sorted({round(i * (n - 1) / 11) for i in range(12)})
        contact_sheet(imgs, frs, rd / "sheet_12.png", pick, 4, f"bibi_{name}：12 格接觸表（共 {n} 格）")
        contact_sheet(imgs, frs, rd / "sheet_all.png", None, 4, f"bibi_{name}：全部 {n} 格")
        write_storyboard(name, frs, durs, rd / "storyboard.md")
        if name.startswith("ball_catch"):
            make_ball_prop(rd / "ball_prop.png")
        report[name] = dict(frames=n, kb=round(kb, 1), q=q, problems=bad, diffs=diffs, ms=sum(durs))
        print(name, json.dumps(report[name], ensure_ascii=False), flush=True)
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
