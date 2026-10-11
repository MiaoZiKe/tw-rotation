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
def ball_layer(x, y, ang, r=48.0):
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
        dict(pose=dict(idle, eye_open=0.2, rot=2, sy=0.98), ms=90, label="眨眼"),
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
    p1 = dict(run_pose(2), x=312, eye="wide", mouth="open")
    F(p1, 110, "追球跑來（圓眼盯球）", ball=(112, 434, -20), fx=run_fx(2, x0=480 - 70))
    # 2 急煞＋預備
    F(dict(view="side", x=300, sy=0.87, sx=1.09, rot=9, ear=-22, flutter=-6, fphase=0.4, eye="squint",
           mouth="flat", fp_near=(-30, 0, -14), fp_far=(-24, 0, -12), bf_near=(8, 0, 6), tail=(-4, 2, -22)),
      130, "急煞、瞇眼瞄準（專注）", ball=(118, 434, -45),
      fx=[R.dust_svg(178, 468, 0.9), R.dust_svg(196, 474, 0.6, 0.8)])
    # 3 蹲到最低蓄力（屁股翹、後腳踩緊）
    F(dict(view="side", x=298, sy=0.79, sx=1.14, rot=3, ear=14, flutter=2, fphase=1.2, eye="squint", mouth="flat",
           fp_near=(-10, 2, -6), fp_far=(-8, 2, -6), bf_near=(18, 2, 22), bf_far=(14, 2, 22), tail=(2, 6, 16),
           look=(0.0, 0.03)),
      230, "蹲到最低蓄力（停頓）", ball=(124, 434, -60),
      props=[fx_part("fx_exclaim", 286, 226, 0.75, 8)])
    # 4 飛撲（拉長、前掌伸、後腳拖、耳朵往後）
    F(dict(view="side", x=252, y=438, sy=1.15, sx=0.9, rot=-22, ear=38, flutter=10, fphase=2.0, eye="wide",
           mouth="open", fp_near=(-34, -16, -38), fp_far=(-28, -12, -32), bf_near=(30, -6, 46),
           bf_far=(26, -8, 42), tail=(8, -6, 26)),
      80, "飛撲！（拉長）", ball=(132, 434, -80),
      fx=[R.speed_lines_svg(410, 300, 3, 56, 20, 0.8, 1)])
    # 5 下墜接近球（前掌往下抓）
    F(dict(view="side", x=222, y=448, sy=1.06, sx=0.96, rot=-14, ear=30, flutter=8, fphase=2.8, eye="wide",
           mouth="o", fp_near=(-16, 10, -24), fp_far=(-12, 8, -20), bf_near=(24, -10, 36), bf_far=(20, -10, 32),
           tail=(6, -6, 20)),
      80, "撲下去（O 嘴）", ball=(140, 436, -95),
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



# ================================================================== 開心跳（預設待機）
FRONT = dict(view="front", mouth="smile", blush=1.2)


def clip_happy_hop() -> list[dict]:
    """正面原地小跳循環：站→蹲（預備）→蹬（拉長）→最高（星星眼、手舉高）→下落→落地壓扁→回彈→歪頭→眨眼→站。"""
    F = FRONT
    up = lambda dx, dy, r: ((-dx, dy, -r), (dx, dy, r))   # noqa: E731  (左手, 右手) 對稱
    fr = []

    def add(ms, label, fx=None, props=None, **kw):
        lf, rf = kw.pop("hands", ((0, 0, 0), (0, 0, 0)))
        fr.append(dict(pose=dict(F, fp_far=lf, fp_near=rf, **kw), ms=ms, label=label, fx=fx or [],
                       props_front=props or []))

    add(240, "站好（圓眼）", eye="dot", mouth="w", ear=0, ear2=0)
    add(110, "往下蹲（預備、瞇眼笑）", eye="arc", sy=0.84, sx=1.1, ear=16, ear2=16, flutter=-4,
        hands=up(-6, 6, -12), bf_far=(-4, 0, -8), bf_near=(4, 0, 8))
    add(70, "蹬起來（拉長、手舉起）", eye="arc", mouth="open", y=R.FOOT_Y - 24, sy=1.13, sx=0.91, ear=26, ear2=26,
        flutter=6, fphase=0.6, hands=up(8, -46, 24), bf_far=(2, 8, 10), bf_near=(-2, 8, -10))
    add(130, "跳到最高（星星眼、耳朵往上甩）", eye="star", mouth="smile", y=R.FOOT_Y - 50, sy=1.03, sx=0.98,
        ear=-12, ear2=-12, flutter=3, fphase=1.4, hands=up(12, -62, 36), bf_far=(6, -6, -16), bf_near=(-6, -6, 16),
        fx=[R.star_svg(110, 196, 12, 0), R.star_svg(392, 186, 14, 20), R.star_svg(424, 240, 8, 40, "#FFE58A")])
    add(70, "往下掉（耳朵還在上）", eye="arc", mouth="open", y=R.FOOT_Y - 26, sy=1.08, sx=0.95, ear=-6, ear2=-6,
        flutter=-3, fphase=2.0, hands=up(6, -30, 18), bf_far=(0, 6, 6), bf_near=(0, 6, -6))
    add(100, "落地壓扁（閉眼笑）", eye="smile", mouth="w", sy=0.8, sx=1.15, ear=30, ear2=30, flutter=-7,
        fphase=2.6, hands=up(14, 6, 26), bf_far=(-8, 0, -10), bf_near=(8, 0, 10),
        fx=[R.dust_svg(88, 470, 0.9, 0.9), R.dust_svg(412, 470, 0.9, 0.9)])
    add(90, "回彈（耳朵慢一拍）", eye="dot", mouth="smile", y=R.FOOT_Y - 8, sy=1.06, sx=0.97, ear=12, ear2=12,
        flutter=3, fphase=3.2, hands=up(0, -10, 6),
        fx=[R.dust_svg(70, 462, 1.1, 0.45), R.dust_svg(430, 462, 1.1, 0.45)])
    add(170, "歪頭笑（耳朵甩過頭）", eye="dot", mouth="smile", rot=-5, sy=0.98, ear=-6, ear2=4, look=(-0.015, 0.0),
        props=[fx_part("fx_heart", 404, 214, 0.45, 14)])
    add(100, "眨眼", eye="dot", eye_open=0.2, mouth="smile", rot=3, ear=2, ear2=-2,
        props=[fx_part("fx_heart", 410, 190, 0.4, 20)])
    add(150, "微微縮一下、準備再跳", eye="dot", mouth="smile", rot=0, sy=0.95, sx=1.03, ear=8, ear2=8,
        hands=up(-3, 4, -6))
    return fr


# ================================================================== 接收（給草／給球）
def clip_receive(item: str = "") -> list[dict]:
    """正面：看到東西（圓眼＋！）→ 眼睛發亮（星星眼、身體往右前傾）→ 雙肉掌往右前伸 → 接住 → 抱回胸前 → 開心彈一下。
    item：''（不畫東西，網頁自己疊）／'grass'／'ball'。東西從畫面右上方遞進來。"""
    F = FRONT
    fr = []
    held_reach = (352, 330)

    def item_layer(where, dx=0.0, dy=0.0):
        if not item:
            return []
        if where == "reach":   # 兩隻肉掌之間（身體右前方，不擋臉）
            if item == "ball":
                return [ball_layer(384 + dx, 366 + dy, 20)]
            return [R.svg_layer(R.grass_svg(338 + dx, 418 + dy, 150, 128, 15))]
        if item == "ball":     # 胸前（嘴巴以下）
            return [ball_layer(248 + dx, 420 + dy, 0)]
        return [R.svg_layer(R.grass_svg(334 + dx, 432 + dy, 172, 8, 15))]

    def add(ms, label, fx=None, props=None, mid=None, **kw):
        fr.append(dict(pose=dict(F, **kw), ms=ms, label=label, fx=fx or [], props_front=props or [],
                       props_mid=mid or []))

    # Andy 10-11：「互動圖不需要前面特效，直接進入互動動作」→ 第 1 格就是動作（看到東西彈一下），不放待機格、不先冒符號
    add(150, "看到東西彈一下（圓眼、耳朵豎）", eye="wide", mouth="o", y=R.FOOT_Y - 10, sy=1.05, sx=0.97,
        ear=-16, ear2=-16, flutter=3, look=(0.02, 0.0))
    add(220, "眼睛發亮（星星眼、往右傾）", eye="star", mouth="smile", rot=6, look=(0.035, 0.0), ear=6, ear2=-4,
        blush=1.5, hands_front=True, fp_far=(6, -6, 10), fp_near=(-6, -6, -10),
        fx=[R.star_svg(130, 250, 10, 10), R.star_svg(110, 300, 7, 30, "#FFE58A")])
    add(110, "雙肉掌往右前伸（拉長）", eye="wide", mouth="open", rot=11, sx=0.95, sy=1.06, look=(0.04, -0.01),
        ear=-8, ear2=14, flutter=4, fp_far=(150, 22, 30), fp_near=(36, -56, 34),
        mid=item_layer("reach", 14, -8) if item else [])
    add(130, "接住！往回收（瞇眼笑）", eye="arc", mouth="open", rot=4, sx=1.03, sy=0.97, look=(0.03, 0.01),
        ear=-2, ear2=20, fp_far=(124, 30, 14), fp_near=(10, -30, 16), mid=item_layer("reach", -24, 10),
        fx=[R.star_svg(420, 238, 11, 15)] if item else [])
    add(140, "抱回胸前（壓扁、臉紅）", eye="smile", mouth="w", rot=0, sy=0.9, sx=1.07, blush=1.7, ear=16, ear2=16,
        flutter=-4, hands_front=True, mid=item_layer("chest", 0, 6))
    add(110, "開心彈一下", eye="arc", mouth="smile", y=R.FOOT_Y - 16, sy=1.07, sx=0.96, ear=-8, ear2=-8, flutter=4,
        blush=1.5, hands_front=True, mid=item_layer("chest", 0, -2), props=[fx_part("fx_hearts_small", 402, 206, 0.6, 8)])
    add(520, "抱著滿足（圓眼）", eye="dot", mouth="smile", ear=2, ear2=2, blush=1.3, hands_front=True,
        mid=item_layer("chest"), props=[fx_part("fx_heart", 412, 176, 0.45, 18)])
    return fr


def make_hand_prop(path, item):
    """給東西的那隻手：從右上角伸進來的短肉掌（粉色肉掌＋奶油色毛袖口），拿著草或球。512 透明。"""
    can = Image.new("RGBA", (R.SIZE * R.S, R.SIZE * R.S))
    if item == "ball":
        can.alpha_composite(R.svg_layer(R.ball_svg(296, 262, 88, 15, stroke=10)))
    else:
        can.alpha_composite(R.svg_layer(R.grass_svg(404, 160, 360, -38, 26)))
    # 袖口：一圈短短的毛（從右上角外面伸進來；只露袖口＋肉掌，不畫長手臂）
    can.alpha_composite(R.svg_layer(
        R.paw_svg(390 if item == "ball" else 396, 180 if item == "ball" else 176, 1.45, 50)
        + f'<path d="M 470 40 C 430 52 404 92 412 128 C 420 160 456 176 490 168 L 560 140 L 540 0 Z" '
        f'fill="{R.FUR}" stroke="{R.INK}" stroke-width="11" stroke-linejoin="round"/>'
        f'<path d="M 432 104 q 9 7 19 0 M 444 140 q 9 6 18 -1" fill="none" stroke="#E2CDB0" stroke-width="6" '
        f'stroke-linecap="round"/>'))
    R.finish(can).save(path)


def make_grass_prop(path):
    can = R.svg_layer(R.grass_svg(336, 486, 470, 68, 32))
    R.finish(can).save(path)


# ================================================================== 吃草
def clip_eat_grass() -> list[dict]:
    """正面：雙小肉掌捧一根牧草，穗那頭在嘴邊，啃一口短一截、臉頰越嚼越鼓、耳朵隨咀嚼抖、腳掌輕拍，
    吃完吞下去→打嗝冒小愛心→滿足。第 1 格直接是把草送到嘴邊（接 receive_grass 的結尾）。"""
    F = dict(view="front", blush=1.2)
    fr = []

    def add(ms, label, L, bites, fx=None, props=None, paw_dy=0.0, **kw):
        pose = dict(F, **kw)
        full = {**R.DEFAULT, **pose}
        mx, my = R.body_pt(full, 0.5 + full["look"][0], 0.50 + full["look"][1])
        tip_y = my + 13                       # 草尖貼在嘴下緣
        mid = []
        if L > 0:
            mid = [R.svg_layer(R.grass_svg(mx + 2 + L * 0.2, tip_y + L, L, 79, 19, bites=bites))]
        # 兩隻肉掌夾住草莖（從胸前兩側往中間收）；草越短手越靠近嘴
        hx, hy = R.body_pt(full, 0.5, 0.80)
        py = tip_y + max(L * 0.62, 24) - hy + paw_dy
        sx_ = L * 0.2 * 0.62
        pose.update(hands_front=True, fp_far=(38 + sx_, py, 18), fp_near=(-34 + sx_, py, -18))
        fr.append(dict(pose=pose, ms=ms, label=label, fx=fx or [], props_front=props or [], props_mid=mid,
                       allow_touch=["propM0"]))

    chew = lambda i: R.text_svg("嚼嚼", 356 + (i % 2) * 8, 206 - (i % 3) * 6, 30, 12 - (i % 2) * 8)  # noqa: E731
    cr = lambda i, a=1.0: [R.crumbs_svg(178, 352, 3, 22, i, a), R.crumbs_svg(326, 350, 3, 22, i + 5, a)]  # noqa: E731

    add(120, "把草送到嘴邊（圓眼期待）", 128, 0, eye="wide", mouth="o", ear=-8, ear2=-8, y=R.FOOT_Y - 6, sy=1.04)
    add(90, "第一口！（張嘴露門牙）", 128, 0, eye="dot", eye_open=0.55, mouth="chew_a", sy=0.97, sx=1.02, ear=4, ear2=4,
        look=(0, 0.01))
    add(90, "咬下來、臉頰鼓（草屑噴）", 112, 1, eye="dot", eye_open=0.55, mouth="chew_c", cheek=0.6, ear=-6, ear2=6,
        fx=cr(0) + [chew(0)])
    add(80, "嚼（半開）、耳朵抖", 112, 1, eye="dot", eye_open=0.55, mouth="chew_b", cheek=0.7, ear=6, ear2=-6,
        bf_near=(0, -8, 14))
    add(80, "嚼（閉）", 112, 1, eye="dot", eye_open=0.55, mouth="chew_c", cheek=0.85, ear=-4, ear2=4, fx=[chew(1)])
    add(90, "第二口", 112, 1, eye="dot", eye_open=0.55, mouth="chew_a", cheek=0.5, ear=2, ear2=2, sy=0.97)
    add(90, "咬下來（草短一截）", 92, 1, eye="dot", eye_open=0.2, mouth="chew_c", cheek=0.9, ear=-6, ear2=6,
        fx=cr(1)[:1] + [chew(2)])
    add(80, "嚼、左腳輕拍", 92, 1, eye="arc", mouth="chew_b", cheek=1.0, ear=7, ear2=-5, bf_far=(0, -9, -14))
    add(90, "第三口", 92, 1, eye="arc", mouth="chew_a", cheek=0.8, ear=0, ear2=0, sy=0.97)
    add(90, "咬下來（越來越短）", 66, 1, eye="arc", mouth="chew_c", cheek=1.1, ear=-6, ear2=6, fx=cr(2) + [chew(3)])
    add(80, "嚼、右腳輕拍", 66, 1, eye="arc", mouth="chew_b", cheek=1.15, ear=6, ear2=-6, bf_near=(0, -9, 14))
    add(100, "最後一口（草只剩一小截）", 34, 1, eye="dot", eye_open=0.55, mouth="chew_a", cheek=1.0, ear=0, ear2=0,
        sy=0.97, paw_dy=4)
    add(170, "臉頰塞滿（閉眼笑）", 0, 0, eye="smile", mouth="chew_c", cheek=1.3, ear=10, ear2=10, sy=0.96, sx=1.03,
        fx=cr(3, 0.7)[1:] + [chew(4)])
    add(120, "咕嚕吞下去（拉長、圓眼）", 0, 0, eye="wide", mouth="o", cheek=0.0, y=R.FOOT_Y - 6, sy=1.07, sx=0.96,
        ear=-12, ear2=-12, fx=[R.text_svg("咕嚕", 360, 214, 30, 10)])
    add(220, "打嗝冒小愛心", 0, 0, eye="arc", mouth="o", sy=0.94, sx=1.05, blush=1.7, ear=14, ear2=14, flutter=-3,
        props=[fx_part("fx_hearts_small", 380, 214, 0.6, 6)], fx=[R.text_svg("嗝", 140, 222, 32, -10)])
    add(520, "滿足拍拍肚子（彎月眼）", 0, 0, eye="smile", mouth="w", blush=1.5, ear=0, ear2=0,
        props=[fx_part("fx_heart", 394, 170, 0.5, 14)])
    # 咀嚼時頭一點一點（上下彈＋左右輕晃），讓相鄰格差更明顯（次要動作）
    for i in range(1, 12):
        f = fr[i]["pose"]
        f.setdefault("rot", (-3.5 if i % 2 else 3.5))
        f["y"] = f.get("y", R.FOOT_Y) - (5 if i % 3 == 1 else 0)
        f.setdefault("sy", 1.0)
        f["sy"] = f["sy"] * (0.97 if i % 2 else 1.02)
        f["ear"] = f.get("ear", 0) * 2
        f["ear2"] = f.get("ear2", 0) * 2
    # 最後兩格的手放肚子上（覆蓋上面自動算的捧草位置）
    for f in fr[-4:]:
        f["pose"].update(fp_far=(18, 0, 10), fp_near=(-18, 0, -10))
    fr[-1]["pose"].update(fp_far=(14, -6, 16), fp_near=(-14, 4, -8))
    return fr


# ================================================================== 爆米花跳
def clip_popcorn() -> list[dict]:
    """天竺鼠招牌「爆米花跳」：突然垂直彈起→空中扭身＋後腳踢→落地→再彈兩下越來越小→轉正面開心定格。
    第 1 格直接是動作（瞬間壓扁），不放待機格。"""
    fr = []

    def add(ms, label, fx=None, props=None, **kw):
        fr.append(dict(pose=dict(kw), ms=ms, label=label, fx=fx or [], props_front=props or []))

    pc = lambda pts: [R.popcorn_svg(x, y, s, r) for x, y, s, r in pts]  # noqa: E731
    vlines = lambda y0: [  # noqa: E731
        f'<path d="M {x} {y0} L {x} {y0+34}" stroke="{R.INK}" stroke-width="5" stroke-linecap="round" stroke-opacity="0.8"/>'
        for x in (214, 248, 282)]

    add(50, "突然一縮（瞬間壓扁）", view="side", sy=0.8, sx=1.14, eye="wide", mouth="o", ear=-14, flutter=-4,
        bf_near=(6, 0, 8), fp_near=(-4, 0, -6))
    add(60, "嘣！垂直彈起（拉長、耳朵被甩下）", view="side", y=R.FOOT_Y - 74, sy=1.18, sx=0.88, eye="wide",
        mouth="open", ear=40, flutter=9, fphase=0.5, bf_near=(6, 10, 10), bf_far=(4, 10, 8), fp_near=(-2, 8, -4),
        fp_far=(-2, 8, -4), tail=(0, 6, 10), fx=vlines(452))
    add(90, "空中扭身＋後腳往後踢（星星眼）", view="side", y=R.FOOT_Y - 112, x=CXo(-14), rot=18, shear=0.12, sy=1.02,
        eye="star", mouth="smile", ear=-26, flutter=6, fphase=1.4, bf_near=(36, -18, 72), bf_far=(30, -22, 64),
        fp_near=(-8, -10, -20), fp_far=(-6, -10, -18), tail=(8, -8, 30), blush=1.4,
        fx=pc([(92, 150, 1.5, -20), (420, 120, 1.6, 18), (440, 236, 1.2, 40)]))
    add(80, "反方向扭（耳朵甩回來）", view="side", y=R.FOOT_Y - 104, x=CXo(10), rot=-18, shear=-0.12, sy=1.03,
        eye="arc", mouth="smile", ear=22, flutter=-6, fphase=2.2, bf_near=(40, -8, 84), bf_far=(34, -12, 78),
        fp_near=(-14, -4, -26), tail=(-6, -4, -24), blush=1.4,
        fx=pc([(78, 120, 1.5, 10), (430, 92, 1.4, -24), (452, 210, 1.4, 30)]) + [R.star_svg(110, 210, 11, 0)])
    add(60, "往下掉（耳朵還往上）", view="side", y=R.FOOT_Y - 48, rot=-4, sy=1.08, sx=0.95, eye="arc", mouth="open",
        ear=-18, flutter=-5, fphase=2.8, bf_near=(4, 6, 6), bf_far=(2, 6, 4), fp_near=(-4, 6, -6),
        fx=pc([(60, 96, 1.3, 30), (462, 70, 1.2, -10)]))
    add(80, "落地壓扁（閉眼笑）", view="side", sy=0.78, sx=1.16, eye="smile", mouth="w", ear=30, flutter=-8, fphase=3.4,
        bf_near=(10, 0, 10), fp_near=(-10, 0, -10), tail=(-4, 6, -20),
        fx=[R.dust_svg(98, 470, 0.9), R.dust_svg(404, 470, 0.9)])
    add(70, "又彈一下！（第 2 下，踢腳）", view="side", y=R.FOOT_Y - 56, rot=14, shear=0.08, sy=1.12, sx=0.92,
        eye="star", mouth="smile", ear=-20, flutter=6, fphase=4.0, bf_near=(26, -12, 46), bf_far=(22, -14, 40),
        tail=(6, -6, 24), fx=pc([(98, 200, 1.3, 12), (408, 178, 1.3, -16)]))
    add(80, "第 2 下最高（反扭）", view="side", y=R.FOOT_Y - 64, rot=-11, shear=-0.06, sy=1.04, eye="arc",
        mouth="smile", ear=16, flutter=-4, fphase=4.6, bf_near=(18, -6, 30), fp_near=(-10, -4, -16), tail=(-4, -4, -16))
    add(70, "落地（小壓扁）", view="side", sy=0.85, sx=1.1, eye="smile", mouth="w", ear=22, flutter=-5, fphase=5.2,
        fx=[R.dust_svg(112, 472, 0.7, 0.8), R.dust_svg(392, 472, 0.7, 0.8)])
    add(70, "第 3 下小小彈", view="side", y=R.FOOT_Y - 26, rot=7, sy=1.06, sx=0.96, eye="arc", mouth="smile", ear=-10,
        flutter=3, fphase=5.8, bf_near=(12, -4, 20), fx=pc([(116, 250, 1.1, 0)]))
    add(70, "輕輕落地", view="side", sy=0.92, sx=1.05, eye="dot", mouth="w", ear=12, fphase=6.4)
    add(160, "轉正面！雙手舉高（星星眼）", view="front", y=R.FOOT_Y - 10, sy=1.06, sx=0.96, eye="star", mouth="smile",
        blush=1.5, ear=-10, ear2=-10, fp_far=(-8, -56, -30), fp_near=(8, -56, 30),
        fx=[R.star_svg(104, 214, 13, 0), R.star_svg(398, 196, 14, 20), R.star_svg(422, 268, 8, 35, "#FFE58A")])
    add(170, "開心晃（彎月眼、愛心）", view="front", rot=-5, sy=0.96, sx=1.03, eye="arc", mouth="smile", blush=1.4,
        ear=10, ear2=-4, fp_far=(-4, -24, -16), fp_near=(4, -24, 16),
        props=[fx_part("fx_hearts_small", 396, 206, 0.6, 8)])
    add(420, "開心定格（圓眼笑）", view="front", eye="dot", mouth="smile", blush=1.3, ear=0, ear2=0,
        props=[fx_part("fx_heart", 404, 180, 0.45, 14)])
    return fr


def CXo(dx):
    return R.CX + dx


def make_popcorn_icon(path):
    lay = R.svg_layer(R.popcorn_icon_svg())
    im = R.finish(lay)
    bb = im.getchannel("A").getbbox()
    im = im.crop(bb)
    side = max(im.size) + 24
    sq = Image.new("RGBA", (side, side))
    sq.alpha_composite(im, ((side - im.width) // 2, (side - im.height) // 2))
    sq.convert("RGBa").resize((96, 96), Image.LANCZOS).convert("RGBA").save(path)


# ================================================================== 被摸
def clip_pet() -> list[dict]:
    """正面：手從右上摸頭（網頁疊 hand_prop.png）→ 身體往下縮、眼睛瞇成彎月、耳朵往後貼、臉紅 → 往手那邊蹭兩下 →
    融化 → 手離開彈回來 → 滿足晃。第 1 格直接是被摸到的反應。頭頂右上 (約 x 300, y 190) 留給手。"""
    fr = []

    def add(ms, label, fx=None, props=None, **kw):
        fr.append(dict(pose=dict(view="front", **kw), ms=ms, label=label, fx=fx or [], props_front=props or []))

    hearts = lambda i: [fx_part("fx_hearts_small", 112 - 4 * (i % 2), 236 - 14 * i, 0.55 + 0.04 * i, -8)]  # noqa: E731
    add(90, "被摸到！一縮（耳朵往後）", eye="arc", mouth="o", sy=0.9, sx=1.06, ear=22, ear2=26, flutter=5, blush=1.3)
    add(140, "往下縮、瞇成彎月眼、臉紅", eye="smile", mouth="w", sy=0.84, sx=1.1, ear=36, ear2=40, flutter=7, fphase=0.6,
        blush=1.7, fp_far=(8, 4, 12), fp_near=(-8, 4, -12))
    add(140, "往手那邊蹭（右傾）", eye="smile", mouth="smile", sy=0.88, sx=1.07, rot=9, shear=0.05, look=(0.02, -0.01),
        ear=30, ear2=44, flutter=6, fphase=1.3, blush=1.7, props=hearts(0))
    add(120, "蹭更用力", eye="smile", mouth="smile", sy=0.9, sx=1.05, rot=13, shear=0.08, look=(0.03, -0.01),
        ear=26, ear2=48, flutter=8, fphase=2.0, blush=1.8, props=hearts(1))
    add(120, "回來一點", eye="smile", mouth="w", sy=0.88, sx=1.06, rot=4, shear=0.02, ear=34, ear2=38, flutter=5,
        fphase=2.7, blush=1.8, props=hearts(1))
    add(120, "再蹭一下（毛被搓亂）", eye="smile", mouth="smile", sy=0.9, sx=1.05, rot=12, shear=0.07, look=(0.03, -0.01),
        ear=28, ear2=46, flutter=9, fphase=3.4, blush=1.9, props=hearts(2))
    add(180, "融化（壓扁、張嘴笑）", eye="smile", mouth="smile", sy=0.8, sx=1.14, rot=3, ear=40, ear2=40, flutter=6,
        fphase=4.1, blush=2.0, fp_far=(12, 6, 18), fp_near=(-12, 6, -18), props=hearts(3))
    add(100, "手離開，彈回來（耳朵彈起）", eye="dot", mouth="o", y=R.FOOT_Y - 12, sy=1.08, sx=0.95, ear=-14, ear2=-14,
        flutter=-5, fphase=4.8, blush=1.6)
    add(150, "意猶未盡左晃（彎月眼）", eye="arc", mouth="smile", rot=-6, sy=0.98, ear=6, ear2=-4, blush=1.5,
        props=[fx_part("fx_heart", 396, 214, 0.5, 14)])
    add(150, "右晃", eye="arc", mouth="smile", rot=5, ear=-3, ear2=6, blush=1.4,
        props=[fx_part("fx_heart", 404, 182, 0.45, 18)])
    add(420, "滿足（圓眼笑）", eye="dot", mouth="smile", blush=1.3, ear=0, ear2=0)
    return fr


def make_pet_hand(path):
    """摸頭的手：右上角伸進來的短肉掌（掌心朝下、手指朝左下），512 透明。"""
    can = R.svg_layer(
        R.paw_svg(372, 188, 1.6, 40)
        + f'<path d="M 470 40 C 430 52 404 92 412 128 C 420 160 456 176 490 168 L 560 140 L 540 0 Z" '
          f'fill="{R.FUR}" stroke="{R.INK}" stroke-width="11" stroke-linejoin="round"/>'
          f'<path d="M 432 104 q 9 7 19 0 M 444 140 q 9 6 18 -1" fill="none" stroke="#E2CDB0" stroke-width="6" '
          f'stroke-linecap="round"/>')
    R.finish(can).save(path)


# ================================================================== 轉圈
def clip_spin() -> list[dict]:
    """真的轉一圈：正面→3/4→側面→背面（露尾巴）→另一側→3/4→正面，耳朵與毛跟著甩；轉完暈眩搖晃（螺旋眼、
    頭上星星繞圈）→ 甩甩頭恢復 → 開心。第 1 格直接是轉身預備（往反方向扭）。"""
    fr = []

    def add(ms, label, fx=None, props=None, **kw):
        fr.append(dict(pose=dict(kw), ms=ms, label=label, fx=fx or [], props_front=props or []))

    whoosh = lambda side: [  # noqa: E731  轉動弧線（身體兩側）
        f'<path d="M {248 + side*170} 300 A 175 70 0 0 {1 if side > 0 else 0} {248 + side*120} 420" fill="none" '
        f'stroke="{R.INK}" stroke-width="5" stroke-linecap="round" stroke-opacity="0.65"/>']
    orbit = lambda k: [R.star_svg(248 + 112 * math.cos(math.radians(k * 55 + j * 120)),  # noqa: E731
                                  170 + 22 * math.sin(math.radians(k * 55 + j * 120)), 12 - 2 * (j == 2), k * 20,
                                  "#FFD25A" if j != 1 else "#FFE58A") for j in range(3)]

    add(80, "往反方向扭（預備）", view="front", rot=-7, sy=0.92, sx=1.05, eye="arc", mouth="w", ear=10, ear2=-6,
        look=(0.03, 0), fp_far=(4, 0, 8), fp_near=(-4, 0, -8))
    add(60, "轉到斜側（3/4）", view="front", look=(-0.12, 0), sx=0.96, rot=3, eye="wide", mouth="open", ear=-6, ear2=22,
        flutter=5, fphase=0.4, fx=whoosh(1))
    add(60, "側面（耳朵甩開）", view="side", facing="left", sx=0.95, rot=-3, eye="wide", mouth="open", ear=34, flutter=9,
        fphase=1.0, tail=(4, -2, 26), fx=whoosh(1))
    add(60, "背面（露小尾巴）", view="back", sx=0.97, ear=24, ear2=-10, tail=(-6, 0, -20), flutter=6, fphase=1.6,
        fx=whoosh(-1))
    add(60, "另一側", view="side", facing="right", sx=0.95, rot=3, eye="wide", mouth="open", ear=34, flutter=9,
        fphase=2.2, tail=(4, -2, -26), fx=whoosh(-1))
    add(60, "轉回斜前方", view="front", look=(0.12, 0), sx=0.96, rot=-3, eye="wide", mouth="open", ear=22, ear2=-6,
        flutter=5, fphase=2.8, fx=whoosh(-1))
    add(90, "正面停（衝過頭、耳朵往前甩）", view="front", rot=6, sx=1.05, sy=0.94, eye="spiral", mouth="wavy", ear=-16,
        ear2=20, flutter=-6, fphase=3.4)
    for k, (rot, ear, ear2, ms) in enumerate([(-11, 14, -10, 130), (10, -10, 16, 130), (-7, 10, -6, 130), (5, -4, 8, 130)]):
        add(ms, "暈眩搖晃（螺旋眼、星星繞頭）", view="front", rot=rot, sx=1.02, sy=0.97 + 0.02 * (k % 2), eye="spiral",
            mouth="wavy", ear=ear, ear2=ear2, look=(0.01 * (1 if rot > 0 else -1), 0), blush=1.0, fx=orbit(k),
            props=[fx_part("fx_swirl", 248 + rot * 3, 132, 0.55, k * 70)] if k < 2 else [])
    add(110, "甩甩頭（恢復）", view="front", rot=-3, sy=1.03, eye="smile", mouth="o", ear=-14, ear2=-14, flutter=4,
        fphase=4.2)
    add(150, "回神開心（彎月眼）", view="front", y=R.FOOT_Y - 10, sy=1.05, sx=0.97, eye="arc", mouth="smile", blush=1.4,
        ear=-6, ear2=-6, fp_far=(-6, -40, -24), fp_near=(6, -40, 24))
    add(400, "站好（圓眼笑）", view="front", eye="dot", mouth="smile", blush=1.2, ear=0, ear2=0)
    return fr


# ================================================================== 其餘：擊掌、跳舞、抱抱、打瞌睡、被叫醒、拍照
def _front_clip(rows):
    """rows：(ms, label, kw)；kw 可含 fx、props。"""
    fr = []
    for ms, label, kw in rows:
        kw = dict(kw)
        fx = kw.pop("fx", [])
        props = kw.pop("props", [])
        fr.append(dict(pose=dict(view="front", **kw), ms=ms, label=label, fx=fx, props_front=props))
    return fr


def clip_highfive():
    """右肉掌舉到身體右上緣跟你擊掌（網頁的手在右上 約 x 400, y 190 迎上來）。第 1 格直接是蓄力舉掌。"""
    return _front_clip([
        (90, "蹲低蓄力、右肉掌往上冒（圓眼）", dict(eye="wide", mouth="o", sy=0.86, sx=1.08, rot=-4, ear=10, ear2=14,
                                           fp_near=(6, -26, 18))),
        (70, "跳起來、肉掌舉到右上緣", dict(eye="arc", mouth="open", y=R.FOOT_Y - 28, sy=1.12, sx=0.92, rot=6, ear=24, ear2=30,
                                    flutter=6, fp_near=(20, -118, 34), bf_far=(0, 8, 6), bf_near=(0, 8, -6))),
        (120, "啪！擊掌（星星迸出）", dict(eye="arc", mouth="smile", y=R.FOOT_Y - 36, sy=1.04, rot=9, ear=-12, ear2=-16, flutter=3,
                                      fp_near=(30, -130, 8), blush=1.5,
                                      fx=[R.burst_svg(404, 168, 44, 8, 10, 6), R.text_svg("啪", 408, 120, 36, 10),
                                          R.star_svg(452, 230, 10, 0)])),
        (90, "被拍回來（星星眼）", dict(eye="star", mouth="open", y=R.FOOT_Y - 20, sy=1.06, rot=-5, ear=18, ear2=22,
                                   fp_near=(22, -96, 46), fp_far=(-4, -10, -6),
                                   fx=[R.star_svg(420, 200, 11, 20), R.star_svg(104, 220, 9, 0, "#FFE58A")])),
        (90, "落地壓扁（閉眼笑）", dict(eye="smile", mouth="w", sy=0.84, sx=1.1, ear=30, ear2=30, flutter=-6,
                                   fp_near=(8, 0, 12), fx=[R.dust_svg(96, 470, 0.8), R.dust_svg(404, 470, 0.8)])),
        (110, "雙掌舉起歡呼（彈一下）", dict(eye="arc", mouth="smile", y=R.FOOT_Y - 12, sy=1.06, sx=0.96, ear=-10, ear2=-10,
                                      fp_far=(-8, -60, -30), fp_near=(8, -60, 30), blush=1.4,
                                      props=[fx_part("fx_hearts_small", 404, 200, 0.6, 8)])),
        (130, "開心晃（左）", dict(eye="arc", mouth="smile", rot=-6, ear=8, ear2=-4, fp_far=(-4, -28, -16), fp_near=(4, -20, 12))),
        (130, "開心晃（右）", dict(eye="dot", mouth="smile", rot=5, ear=-3, ear2=8, fp_far=(0, -12, -6), fp_near=(4, -26, 16))),
        (400, "站好（圓眼笑）", dict(eye="dot", mouth="smile", blush=1.2)),
    ])


EYE_NAME = {"arc": "彎月眼", "dot": "圓眼", "star": "星星眼", "smile": "閉眼笑", "wide": "大圓眼", "spiral": "螺旋眼",
            "closed": "閉眼", "wink": "眨眼"}


def clip_dance():
    """左右扭＋踏腳＋肉掌輪流舉，頭上飄音符；表情輪換。第 1 格直接扭。"""
    rows = []
    eyes = ["arc", "dot", "star", "arc", "smile", "dot", "arc", "star", "arc", "smile", "dot"]
    mouths = ["smile", "open", "smile", "w", "open", "smile", "open", "smile", "w", "open", "smile"]
    for i in range(11):
        side = 1 if i % 2 == 0 else -1
        up = i % 4 in (0, 1)
        lift = -10 if i % 2 == 0 else 0
        props = [fx_part("fx_music", 118 + 10 * ((i + 1) % 3) if side > 0 else 382 - 10 * (i % 3), 214 - 12 * (i % 3), 0.55,
                         -10 * side)]
        rows.append((110 if i % 4 != 3 else 150, ["扭右", "扭左", "跳一下舉掌", "扭左停一拍"][i % 4] + f"（{EYE_NAME[eyes[i]]}）",
                     dict(eye=eyes[i], mouth=mouths[i], rot=9 * side, x=R.CX + 12 * side, shear=0.05 * side,
                          y=R.FOOT_Y - (14 if i % 4 == 2 else 0), sy=0.93 if i % 2 else 1.04, sx=1.04 if i % 2 else 0.97,
                          ear=14 * side + 6, ear2=-14 * side + 6, flutter=5 * side, fphase=i * 0.8, blush=1.3,
                          fp_far=(-6, -58, -28) if (up and side > 0) else (0, -8, -6),
                          fp_near=(6, -58, 28) if (up and side < 0) or i % 4 == 2 else (0, -8, 6),
                          bf_far=(0, lift if side < 0 else 0, -10 if side < 0 else 0),
                          bf_near=(0, lift if side > 0 else 0, 10 if side > 0 else 0),
                          props=props)))
    rows.append((400, "收尾站好（圓眼笑）", dict(eye="dot", mouth="smile", blush=1.2)))
    return _front_clip(rows)


def clip_hug():
    """自己抱抱：兩隻肉掌交叉抱在胸前、身體一擠一擠左右晃、臉紅冒愛心。第 1 格直接把掌收到胸前。"""
    cross = dict(hands_front=True, fp_far=(30, -14, 30), fp_near=(-30, -6, -30))
    return _front_clip([
        (100, "肉掌收到胸前（圓眼）", dict(cross, eye="wide", mouth="o", sy=1.04, sx=0.97, ear=-8, ear2=-8)),
        (140, "抱緊！身體擠一下（閉眼笑、臉紅）", dict(cross, eye="smile", mouth="w", sy=0.9, sx=0.95, ear=20, ear2=20, flutter=-4,
                                           blush=1.8, fp_far=(40, -16, 40), fp_near=(-40, -8, -40))),
        (140, "左晃", dict(cross, eye="smile", mouth="smile", rot=-9, sy=0.93, sx=0.96, ear=26, ear2=8, blush=1.8,
                         props=[fx_part("fx_hearts_small", 402, 214, 0.55, 8)])),
        (140, "右晃", dict(cross, eye="smile", mouth="smile", rot=9, sy=0.93, sx=0.96, ear=8, ear2=26, blush=1.9,
                         props=[fx_part("fx_hearts_small", 98, 214, 0.55, -8)])),
        (130, "左晃（小）", dict(cross, eye="arc", mouth="smile", rot=-5, sy=0.95, ear=18, ear2=10, blush=1.8)),
        (130, "右晃（小）", dict(cross, eye="arc", mouth="w", rot=5, sy=0.95, ear=10, ear2=18, blush=1.8)),
        (160, "大愛心冒出來（拉長）", dict(cross, eye="star", mouth="smile", y=R.FOOT_Y - 10, sy=1.06, sx=0.96, ear=-10, ear2=-10,
                                       blush=1.6, props=[fx_part("fx_heart", 404, 170, 0.8, 12)])),
        (130, "放開（彎月眼）", dict(eye="arc", mouth="smile", sy=0.97, ear=4, ear2=4, blush=1.4,
                                 props=[fx_part("fx_heart", 412, 136, 0.6, 18)])),
        (400, "站好（圓眼笑）", dict(eye="dot", mouth="smile", blush=1.3)),
    ])


def clip_sleep_loop():
    """坐著打瞌睡（循環 8 格）：吸氣鼓起→吐氣扁下、頭一點一點、耳朵垂、Zzz 一個接一個往上飄。"""
    rows = []
    for i in range(8):
        a = TAU * i / 8
        br = math.sin(a)                     # 呼吸
        nod = max(0.0, math.sin(a - 0.6))    # 吐氣時頭往下點
        z = []
        for j in range(3):
            t = ((i / 8) + j / 3) % 1.0
            zx, zy = 378 + 46 * t + 8 * math.sin(t * 9), 196 - 120 * t   # 從右耳外側往右上飄，不壓耳朵
            z.append(fx_part("fx_zzz", zx, zy, 0.35 + 0.35 * t, -10 + 20 * t))
        rows.append((180, ["吸氣", "吸飽（鼓起）", "停", "吐氣", "吐氣（頭往下點）", "扁扁", "頭抬一點", "準備吸氣"][i] + "（閉眼）",
                     dict(eye="closed", mouth="o" if br < -0.3 else "w", sy=1 + 0.05 * br, sx=1 - 0.04 * br,
                          rot=4 * math.sin(a - 1.0), look=(0, 0.02 * nod), ear=22 + 6 * nod, ear2=22 + 6 * nod,
                          blush=1.0, flutter=-2 * br, fphase=a, hands_front=True, fp_far=(10, 4, 14), fp_near=(-10, 4, -14),
                          props=z)))
    return _front_clip(rows)


def clip_wake_once():
    """睡著被點→整隻彈起（耳朵豎、毛炸開、！！）→落地→左右張望→不好意思（汗滴、波浪嘴）→伸懶腰→站好。第 1 格直接彈起。"""
    return _front_clip([
        (70, "嚇！彈起來（圓眼、毛炸開）", dict(eye="wide", mouth="o", y=R.FOOT_Y - 46, sy=1.14, sx=0.92, ear=-26, ear2=-26,
                                        flutter=-9, fp_far=(-10, -50, -40), fp_near=(10, -50, 40),
                                        props=[fx_part("fx_exclaim", 404, 160, 0.7, 12)],
                                        fx=[R.burst_svg(248, 84, 46, 7, -90, 5)])),
        (90, "最高點（還在驚）", dict(eye="wide", mouth="o", y=R.FOOT_Y - 56, sy=1.06, ear=-20, ear2=-20, flutter=-6, fphase=1,
                                  fp_far=(-8, -44, -30), fp_near=(8, -44, 30),
                                  props=[fx_part("fx_exclaim", 410, 150, 0.7, 16)])),
        (80, "落地壓扁", dict(eye="wide", mouth="o", sy=0.82, sx=1.12, ear=26, ear2=26, flutter=-6, fphase=2,
                            fx=[R.dust_svg(96, 470, 0.8), R.dust_svg(404, 470, 0.8)])),
        (140, "往左看", dict(eye="dot", mouth="o", look=(-0.05, 0), rot=-4, ear=4, ear2=-8)),
        (140, "往右看", dict(eye="dot", mouth="w", look=(0.05, 0), rot=4, ear=-8, ear2=4)),
        (90, "眨眼", dict(eye="dot", eye_open=0.2, mouth="w", ear=0, ear2=0)),
        (160, "不好意思（汗滴、波浪嘴）", dict(eye="arc", mouth="wavy", sy=0.97, blush=1.6, ear=14, ear2=14,
                                        props=[fx_part("fx_sweat", 400, 236, 0.55, 0)])),
        (180, "伸懶腰（拉長、雙掌舉高）", dict(eye="closed", mouth="open", y=R.FOOT_Y - 6, sy=1.1, sx=0.93, ear=-10, ear2=-10,
                                        fp_far=(-6, -70, -30), fp_near=(6, -70, 30))),
        (400, "站好（圓眼笑）", dict(eye="dot", mouth="smile", blush=1.2)),
    ])


def clip_selfie():
    """擺三個拍照姿勢（眨眼＋肉掌貼臉邊、星星眼、雙掌歡呼），每擺一個就閃光燈「咔嚓」。第 1 格直接擺第一個姿勢。"""
    flash = lambda: [R.burst_svg(80, 120, 50, 8, 0, 6, "#FFD25A"), R.burst_svg(432, 120, 50, 8, 22, 6, "#FFD25A"),  # noqa: E731
                     R.text_svg("咔嚓", 192, 110, 34, -6)]
    return _front_clip([
        (100, "歪頭眨眼、右掌貼臉邊", dict(eye="wink", mouth="smile", rot=-9, look=(-0.01, 0), ear=-4, ear2=16, blush=1.5,
                                     fp_near=(6, -64, 10))),
        (120, "咔嚓！（閃光）", dict(eye="wink", mouth="smile", rot=-10, ear=-4, ear2=18, blush=1.5, fp_near=(6, -66, 6),
                                 fx=flash())),
        (100, "換姿勢：往右歪、左掌舉起", dict(eye="star", mouth="open", rot=9, sy=0.96, ear=18, ear2=-4, fp_far=(-6, -70, -14),
                                       fp_near=(0, 0, 0))),
        (120, "咔嚓！（星星眼）", dict(eye="star", mouth="open", rot=10, ear=20, ear2=-4, fp_far=(-6, -72, -10), fx=flash())),
        (90, "蹲一下", dict(eye="arc", mouth="w", sy=0.86, sx=1.08, ear=16, ear2=16, flutter=-4)),
        (100, "跳起雙掌歡呼", dict(eye="arc", mouth="smile", y=R.FOOT_Y - 30, sy=1.1, sx=0.93, ear=-14, ear2=-14, flutter=5,
                                fp_far=(-8, -64, -30), fp_near=(8, -64, 30))),
        (130, "咔嚓！（空中定格）", dict(eye="arc", mouth="smile", y=R.FOOT_Y - 34, sy=1.06, ear=-12, ear2=-12,
                                    fp_far=(-10, -66, -34), fp_near=(10, -66, 34), fx=flash())),
        (90, "落地", dict(eye="smile", mouth="w", sy=0.86, sx=1.1, ear=24, ear2=24, flutter=-5)),
        (400, "看鏡頭笑（愛心）", dict(eye="dot", mouth="smile", blush=1.3, props=[fx_part("fx_heart", 404, 190, 0.5, 14)])),
    ])


# ================================================================== 渲染
CLIPS = {
    "highfive": dict(make=clip_highfive, facing="left", loop=False, note="播一次；網頁的手在右上（約 x 400, y 190）迎上來擊掌（第 3 格）。"),
    "dance": dict(make=clip_dance, facing="left", loop=False, note="播一次；最後一格＝站好。"),
    "hug": dict(make=clip_hug, facing="left", loop=False, note="播一次；最後一格＝站好。"),
    "sleep_loop": dict(make=clip_sleep_loop, facing="left", loop=True, note="全部 8 格循環（呼吸一輪＋Zzz 輪流往上飄）。"),
    "wake_once": dict(make=clip_wake_once, facing="left", loop=False, note="播一次（打瞌睡時被點）；最後一格＝站好。"),
    "selfie": dict(make=clip_selfie, facing="left", loop=False, note="播一次；三個姿勢各閃一次光；最後一格＝看鏡頭笑。"),
    "pet_v2": dict(make=clip_pet, facing="left", loop=False,
                   note="播一次；網頁同時把 hand_prop.png 從右上伸到頭頂右上（約 x 300, y 190，第 1～7 格），第 8 格手離開。"),
    "spin_v2": dict(make=clip_spin, facing="left", loop=False, note="播一次；最後一格＝正面站好，可接 happy_hop。"),
    "popcorn": dict(make=clip_popcorn, facing="left", loop=False,
                    note="播一次（點爆米花圖示）；第 1 格直接起跳預備，最後一格＝正面開心定格，可接 happy_hop。"),
    "eat_grass_v2": dict(make=clip_eat_grass, facing="left", loop=False,
                         note="播一次；接在 receive_grass 後面（第 1 格直接把草送到嘴邊）；最後一格＝正面滿足，可接 happy_hop。"),
    "happy_hop": dict(make=clip_happy_hop, facing="left", loop=True,
                      note="全部 10 格循環＝大部分情境的預設待機（正面，不分左右）。"),
    "receive": dict(make=lambda: clip_receive(""), facing="left", loop=False,
                    note="播一次；東西由網頁疊（從右上遞進來），第 4～5 格肉掌在右上 (约 x 350, y 330) 接。"),
    "receive_grass": dict(make=lambda: clip_receive("grass"), facing="left", loop=False,
                          note="播一次；畫面內含牧草：第 4 格起草在右前方肉掌上，第 6 格抱到胸前。接 eat_grass_v2。"),
    "receive_ball": dict(make=lambda: clip_receive("ball"), facing="left", loop=False,
                         note="播一次；畫面內含球：第 4 格起球在右前方肉掌上，第 6 格抱到胸前。之後網頁丟球→run_r→ball_catch。"),
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
        ff = fr["pose"].get("facing", "left")          # 轉圈這種逐格換面向的：clip 面向右時整組反過來
        if cfg["facing"] == "right":
            ff = "right" if ff == "left" else "left"
        pose = dict(fr["pose"], facing=ff)
        mid = []
        if fr.get("ball"):
            bx, by, ang = fr["ball"]
            mid = [ball_layer(bx, by, ang)]
        mid = mid + list(fr.get("props_mid") or [])
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
        masks = boxes.pop("__masks", {})
        if fr.get("post") is not None:
            masks["fx_arc"] = np.asarray(post.getchannel("A").reduce(4)) > 40
        c = {k: R.bbox512(v) for k, v in boxes.items() if v}
        c["__masks"] = masks
        checks.append(c)
    return frs, imgs, checks


def verify(name, frs, imgs, checks):
    """全身入鏡＋效果／道具不壓臉＋相鄰格差異。回傳 (問題清單, 相鄰差)。"""
    bad = []
    for i, (im, bx) in enumerate(zip(imgs, checks)):
        if not R.inside_canvas(im, 2):
            bad.append(f"第 {i+1} 格碰到畫布邊（裁切）")
        ms_ = bx.get("__masks", {})
        face = ms_.get("face")
        if face is None:
            continue
        # 臉（眼＋嘴）往外擴 2px（512 單位）當安全邊
        fpad = face.copy()
        for sh in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            fpad |= np.roll(face, sh, axis=(0, 1))
        for k, m in ms_.items():
            if k.startswith(("fx", "propF", "propM")) and k not in frs[i].get("allow_touch", []):
                n = int((fpad & m).sum())
                if n:
                    bad.append(f"第 {i+1} 格 {k} 壓到臉 {n} 格點")
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
    f = ImageFont.truetype(FONT, 15)
    ft = ImageFont.truetype(FONT, 20)
    d.text((10, 8), title, font=ft, fill=(240, 240, 240))
    bgs = [(250, 246, 238, 255), (238, 243, 250, 255)]
    for n, i in enumerate(idx):
        x, y = (n % cols) * cell, head + (n // cols) * (cell + 28)
        bg = Image.new("RGBA", (cell, cell), bgs[n % 2])
        bg.alpha_composite(imgs[i].resize((cell, cell), Image.LANCZOS))
        sh.alpha_composite(bg, (x, y + 28))
        d.text((x + 6, y + 4), f"{i+1:02d} {frs[i]['label']}"[:16], font=f, fill=(235, 235, 235))
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
        if name == "pet_v2":
            make_pet_hand(rd / "hand_prop.png")
        if name == "popcorn":
            make_popcorn_icon(rd / "popcorn_icon.png")
        if name == "receive":
            make_hand_prop(rd / "hand_grass_prop.png", "grass")
            make_hand_prop(rd / "hand_ball_prop.png", "ball")
            make_grass_prop(rd / "grass_prop.png")
        report[name] = dict(frames=n, kb=round(kb, 1), q=q, problems=bad, diffs=diffs, ms=sum(durs))
        print(name, json.dumps(report[name], ensure_ascii=False), flush=True)
    (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
