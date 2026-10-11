"""比比互動動作 v2：用 bibi_rig 骨架逐格擺姿勢（關鍵格＋ease 補間），不再變形原 GIF。

Andy 2026-10-11 退件：「需要是點擊互動按鈕，他會有對應動作，不是基於原本的 GIF 加點東西上去。
例如我點球，他會跟著球跑，我點草，他會有吃草畫面等等」＋「動作要再豐富生動一點」。
每組都照動畫 12 原則：預備／擠壓伸展、跟隨與重疊（耳朵、毛、尾巴慢 1～2 格）、弧線與次要動作、
表情 ≥3 種穿插、節奏有快有慢、特效畫進素材（速度線、塵土、星星…）。

用法
----
    python scripts/anim/bibi_moves_v2.py --out <scratchpad>/bibi_v2 --repo-out docs/anim [--only run_r,ball_catch]
    # 10-11 晚新增：--only hit,cry（＋槌子圖示 bibi_icons/hammer.png）、--only dizzy,spin_v2

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
    out = [R.speed_lines_svg(x0 + (i % 3) * 4, 318 + (i % 2) * 5, n=3, length=36, gap=18, alpha=0.75, seed=i)]
    k = i % (n // 2)
    if k in (0, 1):
        s = 0.8 if k == 0 else 1.05
        a = 1.0 if k == 0 else 0.55
        bx = 380 + (10 if k == 1 else 0) + (8 if i >= n // 2 else 0)
        out.append(R.dust_svg(bx, 470 - 4 * k, s, a))
    return out


def run_fx_d(i: int, n: int = 8) -> list[str]:
    """原版大身體用：速度線在身後（面向左時的右側 x 446～486）、塵土在後腳旁。"""
    out = [R.speed_lines_svg(434 + (i % 3) * 3, 286 + (i % 2) * 6, n=3, length=34, gap=20, alpha=0.75, seed=i)]
    k = i % (n // 2)
    if k in (0, 1):
        out.append(R.dust_svg(444 + 6 * k, 468 - 3 * k, 0.75 if k == 0 else 0.95, 1.0 if k == 0 else 0.55))
    return out


def clip_run_d() -> list[dict]:
    fr = clip_run()
    for i, f in enumerate(fr):
        f["fx"] = run_fx_d(i)
        p = f["pose"]
        for key in ("bf_near", "bf_far"):     # 小腳踢得明顯一點（原版腳在身體底下）
            dx, dy, r = p[key]
            p[key] = (dx * 1.5, dy * 1.4, r)
    return fr


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
                     dict(eye=eyes[i], mouth=mouths[i], rot=7 * side, x=R.CX + 5 * side, shear=0.05 * side,
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
                          blush=1.0, flutter=-2 * br, fphase=a,
                          props=z)))
    return _front_clip(rows)


def clip_wake_once():
    """睡著被點→整隻彈起（耳朵豎、毛炸開、！！）→落地→左右張望→不好意思（汗滴、波浪嘴）→伸懶腰→站好。第 1 格直接彈起。"""
    return _front_clip([
        (70, "嚇！彈起來（圓眼、毛炸開）", dict(eye="wide", mouth="o", y=R.FOOT_Y - 46, sy=1.14, sx=0.92, ear=-26, ear2=-26,
                                        flutter=-9, fp_far=(-10, -50, -40), fp_near=(10, -50, 40),
                                        props=[fx_part("fx_exclaim", 404, 160, 0.7, 12)],
                                        fx=[R.burst_svg(150, 90, 30, 7, -90, 5)])),
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


# ================================================================== 原版 Default 造型（Andy 10-11 第二次退件後）
def _dp(pose, ox, oy):
    """原圖座標 → 這一格的世界座標（跟著本體擠壓、傾斜）。"""
    return R.def_pt({**R.DEFAULT, **pose}, ox, oy)


SIDE_PAWS = lambda rl=-60, rr=60, dy=0: [(70, 350, -4, dy, rl), (438, 350, 4, dy, rr)]  # noqa: E731


def clip_happy_hop_d() -> list[dict]:
    """開心跳（原版造型，照 hop_sheet_ref 節奏）：Default→微蹲→壓扁^^→更扁><→起跳左傾（露腳底、下方速度線）→
    最高點右傾（星星眼、頭上放射線）→下落→落地壓扁><→回彈→眨眼接回 Default。循環。"""
    fr = []

    def add(ms, label, fx=None, props=None, **kw):
        fr.append(dict(pose=dict(kw), ms=ms, label=label, fx=fx or [], props_front=props or []))

    mm = lambda y, s=1.0: [R.motion_marks_svg(30, y, -1, s), R.motion_marks_svg(466, y, 1, s)]  # noqa: E731
    add(260, "Default 站好（原版）")
    add(120, "微蹲預備（耳朵慢一拍）", sy=0.94, sx=1.04, ear=6, ear2=6)
    add(110, "壓扁（^^ 瞇眼笑＋動作線）", sy=0.85, sx=1.1, eye="arc", ear=14, ear2=14, flutter=-4, fx=mm(318))
    add(90, "壓到最扁（>< 用力）", sy=0.78, sx=1.15, eye="squeeze", mouth="w", ear=22, ear2=22, flutter=-6, fphase=0.5,
        fx=mm(338, 1.1))
    add(80, "起跳！左傾、露腳底", y=R.FOOT_Y - 56, rot=-14, sy=1.08, sx=0.95, eye="arc", ear=18, ear2=22,
        flutter=7, fphase=1.0, bf_far=(-12, 12, 0), bf_near=(10, 9, 0), paws=SIDE_PAWS(-70, 70, -6),
        fx=[R.drop_lines_svg(248, 446, 3, 30, 24)])
    add(120, "最高點右傾（星星眼、頭上放射線）", y=R.FOOT_Y - 78, rot=16, sy=1.02, eye="star", mouth="smile", blush=1.4,
        ear=-14, ear2=-10, flutter=4, fphase=1.8, bf_far=(-6, -8, 0), bf_near=(6, -10, 0), paws=SIDE_PAWS(-40, 40, -18),
        fx=[R.burst_svg(290, 44, 34, 7, -90, 5, R.DEF_INK)])
    add(70, "往下掉（耳朵還在上）", y=R.FOOT_Y - 36, rot=2, sy=1.07, sx=0.95, ear=-8, ear2=-8, flutter=-3, fphase=2.4,
        bf_far=(0, 10, 0), bf_near=(0, 10, 0), fx=[R.drop_lines_svg(248, 52, 3, 34, 22)])
    add(100, "落地壓扁（><＋動作線）", sy=0.8, sx=1.14, eye="squeeze", mouth="w", ear=24, ear2=24, flutter=-7, fphase=3.0,
        fx=mm(350, 1.1))
    add(110, "回彈（拉長一點）", y=R.FOOT_Y - 6, sy=1.05, sx=0.97, ear=8, ear2=8, flutter=3, fphase=3.6)
    add(140, "眨眼、耳朵回位（接回第 1 格）", sy=0.98, rot=-2, eye_open=0.2, ear=-2, ear2=-2)
    return fr


def clip_receive_d(item: str = "") -> list[dict]:
    """接收（原版造型）：第 1 格就是看到東西彈一下 → 星星眼往右傾、肉掌合在胸前 → 往右前伸 → 接住往回收 →
    抱到胸前（臉紅）→ 開心彈一下 → 抱著東西回 Default 表情。東西從右上遞進來。"""
    fr = []

    def item_at(pose, where, dx=0.0, dy=0.0):
        if not item:
            return []
        if where == "reach":
            x, y = _dp(pose, 424, 304)
            x, y = x + dx, y + dy
            if item == "ball":
                return [ball_layer(x, y, 20, 40)]
            return [R.svg_layer(R.grass_svg(x - 34, y + 66, 170, 118, 18))]
        x, y = _dp(pose, 253, 410)
        x, y = x + dx, y + dy
        if item == "ball":
            return [ball_layer(x, y, 0, 46)]
        return [R.svg_layer(R.grass_svg(x + 96, y + 8, 196, 8, 18))]

    def add(ms, label, where=None, idx=None, fx=None, props=None, **kw):
        mid = item_at(kw, where, *(idx or (0, 0))) if where else []
        fr.append(dict(pose=dict(kw), ms=ms, label=label, fx=fx or [], props_front=props or [], props_mid=mid))

    chest = [(212, 404, 0, 0, -18), (296, 404, 0, 0, 18)]
    add(140, "看到東西彈一下（圓眼、耳朵豎）", y=R.FOOT_Y - 12, sy=1.05, sx=0.97, eye="wide", mouth="o", ear=-14, ear2=-14,
        flutter=3, look=(0.02, 0))
    add(220, "眼睛發亮（星星眼）往右傾、肉掌合胸前", rot=7, eye="star", blush=1.5, look=(0.03, 0), ear=6, ear2=-6,
        paws=chest, fx=[R.star_svg(70, 236, 11, 10), R.star_svg(54, 290, 8, 30, "#FFE58A")])
    add(110, "雙肉掌往右前伸（拉長）", rot=10, sx=0.96, sy=1.05, eye="wide", mouth="big", look=(0.035, -0.01), ear=-8,
        ear2=16, flutter=4, paws=[(432, 300, 4, -6, 60), (350, 392, 0, 0, 40)], where="reach")
    add(130, "接住！往回收（瞇眼笑）", rot=4, sx=1.03, sy=0.97, eye="arc", look=(0.03, 0.01), ear=-2, ear2=20,
        paws=[(420, 330, 4, 0, 50), (330, 398, 0, 0, 30)], where="reach", idx=(-28, 14),
        fx=[R.star_svg(476, 238, 11, 15)] if item else [])
    add(140, "抱到胸前（壓扁、臉紅）", sy=0.9, sx=1.06, eye="smile", mouth="w", blush=1.8, ear=16, ear2=16, flutter=-4,
        paws=chest, where="chest", idx=(0, 4))
    add(110, "開心彈一下（愛心）", y=R.FOOT_Y - 16, sy=1.07, sx=0.96, eye="arc", blush=1.5, ear=-8, ear2=-8, flutter=4,
        paws=chest, where="chest", props=[fx_part("fx_hearts_small", 444, 200, 0.6, 8)])
    add(520, "抱著東西（回 Default 表情）", blush=1.2, paws=chest, where="chest",
        props=[fx_part("fx_heart", 452, 172, 0.45, 18)])
    return fr



def clip_eat_grass_d() -> list[dict]:
    """吃草（原版造型）：雙小肉掌捧牧草、穗那頭在嘴邊；啃一口短一截、臉頰越嚼越鼓、耳朵隨咀嚼抖、腳輕拍、
    頭一點一點；吃完咕嚕吞下→打嗝冒小愛心→回 Default 表情滿足。第 1 格直接把草送到嘴邊（接 receive_grass）。"""
    fr = []

    def add(ms, label, L, bites, fx=None, props=None, paw_dy=0.0, **kw):
        pose = dict(kw)
        full = {**R.DEFAULT, **pose}
        mx, my = R.def_pt(full, R.DEF_MOUTH[0], R.DEF_MOUTH[1] + 18)   # 嘴下緣
        mid = []
        if L > 0:
            mid = [R.svg_layer(R.grass_svg(mx + 4 + L * 0.2, my + L, L, 79, 22, bites=bites))]
            py = my + max(L * 0.6, 26) + paw_dy
            px = mx + 4 + L * 0.2 * 0.4
            pose["paws"] = [(0, 0, 0, 0, 0)]   # 佔位，下面換成世界座標
            pose["paws_world"] = [(px - 24, py, -24), (px + 24, py + 4, 24)]
        fr.append(dict(pose=pose, ms=ms, label=label, fx=fx or [], props_front=props or [], props_mid=mid,
                       allow_touch=["propM0"]))

    chew = lambda i: R.text_svg("嚼嚼", 384 + (i % 2) * 8, 150 - (i % 3) * 6, 34, 12 - (i % 2) * 8)  # noqa: E731
    cr = lambda i, a=1.0: [R.crumbs_svg(158, 352, 3, 26, i, a), R.crumbs_svg(346, 350, 3, 26, i + 5, a)]  # noqa: E731

    add(120, "把草送到嘴邊（圓眼期待）", 150, 0, eye="wide", mouth="o", ear=-10, ear2=-10, y=R.FOOT_Y - 8, sy=1.04)
    add(90, "第一口！（張嘴露門牙）", 150, 0, eye="default", mouth="chew_a", sy=0.97, sx=1.02, ear=4, ear2=4)
    add(90, "咬下來、臉頰鼓（草屑噴）", 128, 1, eye="closed", mouth="chew_c", cheek=0.6, ear=-8, ear2=8, fx=cr(0) + [chew(0)])
    add(80, "嚼（半開）、耳朵抖", 128, 1, eye="default", mouth="chew_b", cheek=0.7, ear=8, ear2=-8, bf_near=(0, -8, 0))
    add(80, "嚼（閉）", 128, 1, eye="closed", mouth="chew_c", cheek=0.85, ear=-6, ear2=6, fx=[chew(1)])
    add(90, "第二口", 128, 1, eye="default", mouth="chew_a", cheek=0.5, ear=2, ear2=2, sy=0.97)
    add(90, "咬下來（草短一截）", 104, 1, eye="default", eye_open=0.2, mouth="chew_c", cheek=0.9, ear=-8, ear2=8,
        fx=cr(1)[:1] + [chew(2)])
    add(80, "嚼、左腳輕拍（彎月眼）", 104, 1, eye="arc", mouth="chew_b", cheek=1.0, ear=9, ear2=-6, bf_far=(0, -10, 0))
    add(90, "第三口", 104, 1, eye="arc", mouth="chew_a", cheek=0.8, sy=0.97)
    add(90, "咬下來（越來越短）", 74, 1, eye="arc", mouth="chew_c", cheek=1.1, ear=-8, ear2=8, fx=cr(2) + [chew(3)])
    add(80, "嚼、右腳輕拍", 74, 1, eye="arc", mouth="chew_b", cheek=1.15, ear=8, ear2=-8, bf_near=(0, -10, 0))
    add(100, "最後一口（只剩一小截）", 36, 1, eye="default", mouth="chew_a", cheek=1.0, sy=0.97, paw_dy=4)
    add(170, "臉頰塞滿（閉眼笑）", 0, 0, eye="smile", mouth="chew_c", cheek=1.3, ear=12, ear2=12, sy=0.96, sx=1.03,
        fx=cr(3, 0.7)[1:] + [chew(4)])
    add(120, "咕嚕吞下去（拉長、圓眼）", 0, 0, eye="wide", mouth="o", y=R.FOOT_Y - 8, sy=1.07, sx=0.96, ear=-14, ear2=-14,
        fx=[R.text_svg("咕嚕", 392, 150, 34, 10)])
    add(220, "打嗝冒小愛心", 0, 0, eye="arc", mouth="o", sy=0.94, sx=1.05, blush=1.7, ear=16, ear2=16, flutter=-3,
        props=[fx_part("fx_hearts_small", 420, 168, 0.65, 6)], fx=[R.text_svg("嗝", 82, 170, 36, -10)])
    add(520, "滿足拍拍肚子（回 Default 表情）", 0, 0, blush=1.4,
        props=[fx_part("fx_heart", 430, 140, 0.5, 14)])
    # 咀嚼時頭一點一點（上下彈＋左右輕晃）
    for i in range(1, 12):
        f = fr[i]["pose"]
        f.setdefault("rot", (-3.5 if i % 2 else 3.5))
        f["y"] = f.get("y", R.FOOT_Y) - (6 if i % 3 == 1 else 0)
        f["sy"] = f.get("sy", 1.0) * (0.97 if i % 2 else 1.02)
    # 沒有草之後，肉掌放肚子上（拍肚子）
    for k, f in enumerate(fr[-4:-1]):
        f["pose"]["paws"] = [(186, 392, 0, 6 * (k % 2), -38), (320, 392, 0, -6 * (k % 2), 38)]
    fr[-1]["pose"]["paws"] = None          # 最後一格＝Default（原版平常看不到手）
    return fr



# ================================================================== 原版造型：爆米花跳／撲球／摸摸／轉圈
def _F(fr, ms, label, fx=None, props=None, mid=None, back=None, **kw):
    fr.append(dict(pose=dict(kw), ms=ms, label=label, fx=fx or [], props_front=props or [], props_mid=mid or [],
                   props_back=back or []))


def clip_popcorn_d() -> list[dict]:
    """爆米花跳（原版正面）：瞬間一縮→垂直彈起→空中扭身＋小腳亂踢→反扭→落地壓扁→第 2 下→第 3 下越來越小→開心→Default。"""
    fr = []
    pc = lambda pts: [R.popcorn_svg(x, y, s, r) for x, y, s, r in pts]  # noqa: E731
    mm = lambda y: [R.motion_marks_svg(30, y, -1), R.motion_marks_svg(468, y, 1)]  # noqa: E731
    _F(fr, 50, "突然一縮（瞬間壓扁、圓眼）", sy=0.8, sx=1.13, eye="wide", mouth="o", ear=-12, ear2=-12, flutter=-4)
    _F(fr, 60, "嘣！垂直彈起（拉長、耳朵被甩下）", y=R.FOOT_Y - 76, sy=1.14, sx=0.9, eye="wide", mouth="big", ear=30, ear2=30,
       flutter=8, bf_far=(0, 14, 0), bf_near=(0, 14, 0), fx=[R.drop_lines_svg(248, 444, 3, 30, 26)])
    _F(fr, 90, "空中扭身＋小腳亂踢（星星眼）", y=R.FOOT_Y - 92, rot=18, eye="star", blush=1.5, ear=-16, ear2=-16, flutter=5,
       fphase=1.2, bf_far=(-26, -14, 0), bf_near=(26, -22, 0),
       fx=pc([(40, 116, 1.2, -20), (474, 92, 1.3, 18), (482, 236, 1.0, 40)]))
    _F(fr, 80, "反方向扭（耳朵甩回來）", y=R.FOOT_Y - 86, rot=-17, eye="arc", ear=16, ear2=16, flutter=-5, fphase=2.0,
       bf_far=(-28, -20, 0), bf_near=(24, -6, 0), fx=pc([(36, 84, 1.2, 10), (470, 64, 1.1, -24), (30, 236, 1.1, 30)]))
    _F(fr, 60, "往下掉（耳朵還往上）", y=R.FOOT_Y - 44, rot=-4, sy=1.08, sx=0.95, eye="arc", ear=-12, ear2=-12, flutter=-4,
       bf_far=(0, 12, 0), bf_near=(0, 12, 0), fx=pc([(44, 196, 1.0, 30), (474, 170, 1.0, -10)]))
    _F(fr, 80, "落地壓扁（閉眼笑＋動作線）", sy=0.8, sx=1.14, eye="smile", mouth="w", ear=26, ear2=26, flutter=-7,
       fphase=2.8, fx=mm(372))
    _F(fr, 70, "第 2 下（踢腳）", y=R.FOOT_Y - 54, rot=12, sy=1.1, sx=0.93, eye="star", ear=-14, ear2=-14, flutter=5,
       fphase=3.4, bf_far=(-18, -10, 0), bf_near=(18, -14, 0), fx=pc([(44, 170, 1.0, 12), (470, 150, 1.0, -16)]))
    _F(fr, 80, "第 2 下最高（反扭）", y=R.FOOT_Y - 62, rot=-10, eye="arc", ear=12, ear2=12, flutter=-3, fphase=4.0)
    _F(fr, 70, "落地（小壓扁、><）", sy=0.86, sx=1.09, eye="squeeze", mouth="w", ear=20, ear2=20, flutter=-5, fphase=4.6,
       fx=mm(390))
    _F(fr, 70, "第 3 下小小彈", y=R.FOOT_Y - 24, rot=6, sy=1.05, sx=0.97, eye="arc", ear=-8, ear2=-8, flutter=3,
       fx=pc([(46, 240, 0.9, 0)]))
    _F(fr, 70, "輕輕落地", sy=0.93, sx=1.04, ear=10, ear2=10)
    _F(fr, 160, "開心！小肉掌舉起（星星眼）", y=R.FOOT_Y - 10, sy=1.05, sx=0.97, eye="star", blush=1.5, ear=-10, ear2=-10,
       paws=[(70, 330, -6, -16, -60), (438, 330, 6, -16, 60)],
       fx=[R.star_svg(36, 170, 13, 0), R.star_svg(476, 160, 14, 20)])
    _F(fr, 170, "開心晃（彎月眼、愛心）", rot=-5, sy=0.97, eye="arc", blush=1.4, ear=8, ear2=-4,
       props=[fx_part("fx_hearts_small", 470, 150, 0.6, 8)])
    _F(fr, 420, "Default（原版）")
    return fr


def clip_ball_catch_d() -> list[dict]:
    """撲球（原版造型，面向左；ball_catch＝鏡像成面向右）：追球跑來→急煞瞇眼瞄準→蹲低蓄力（！）→飛撲→
    整隻壓到球上（坐在球上、星星迸出）→在球上前後搖→從球上彈起→轉正面落地、肉掌按住球→抱著球開心晃→Default 抱球。"""
    fr = []
    BR = 52
    q3 = dict(view="q3", ear_tx=22, ear_sc_r=0.8)
    B = lambda x, y, a: [ball_layer(x, y, a, BR)]  # noqa: E731
    held = [(186, 420, 0, 0, -30), (320, 420, 0, 0, 30)]
    run2 = R.to_default_pose(dict(run_pose(2), x=270))
    run2.update(eye="wide", mouth="big")
    _F(fr, 110, "追球跑來（圓眼盯球）", mid=B(58, 430, -20), **run2)
    _F(fr, 130, "急煞、瞇眼瞄準（專注）", **q3, x=262, sy=0.87, sx=1.06, rot=8, ear=-20, ear2=-20, flutter=-6, eye="squeeze",
       mouth="w", bf_far=(-16, 0, 0), mid=B(78, 430, -50), fx=[R.dust_svg(150, 474, 0.8)])
    _F(fr, 220, "蹲到最低蓄力（停頓）", **q3, x=262, sy=0.8, sx=1.09, rot=2, ear=14, ear2=14, eye="squeeze", mouth="w",
       bf_near=(14, 0, 0), mid=B(90, 430, -70), props=[fx_part("fx_exclaim", 300, 92, 0.75, 8)])
    _F(fr, 80, "飛撲！（拉長、耳朵往後）", **q3, x=250, y=R.FOOT_Y - 70, rot=-18, sy=1.12, sx=0.92, ear=34, ear2=34,
       flutter=9, eye="wide", mouth="big", bf_near=(30, -8, 0), bf_far=(26, -12, 0),
       mid=B(116, 430, -100), fx=[R.speed_lines_svg(430, 200, 3, 30, 20, 0.8, 1)])
    _F(fr, 160, "整隻壓到球上（壓扁、星星）", **q3, x=232, y=R.FOOT_Y - 44, sy=0.84, sx=1.08, rot=-6, ear=-18, ear2=-18,
       flutter=-6, eye="squeeze", mouth="big", back=B(196, 430, -130),
       fx=[R.star_svg(52, 360, 14, 10), R.star_svg(44, 410, 10, -20, "#FFE58A"), R.star_svg(96, 450, 9, 30)])
    _F(fr, 90, "在球上往前搖", **q3, x=250, y=R.FOOT_Y - 48, rot=-18, sy=0.9, sx=1.05, ear=22, ear2=22, flutter=6,
       eye="arc", back=B(212, 430, -170), fx=[R.motion_marks_svg(466, 250, 1)])
    _F(fr, 90, "往後搖回來", **q3, x=240, y=R.FOOT_Y - 42, rot=9, sy=0.92, sx=1.04, ear=-10, ear2=-10, flutter=-4,
       eye="arc", back=B(200, 430, -140), fx=[R.motion_marks_svg(40, 260, -1)])
    _F(fr, 90, "再往前搖（閉眼笑）", **q3, x=236, y=R.FOOT_Y - 46, rot=-12, sy=0.9, sx=1.04, ear=16, ear2=16, eye="smile",
       back=B(192, 430, -180))
    _F(fr, 90, "從球上彈起（星星眼）", y=R.FOOT_Y - 96, sy=1.08, sx=0.94, eye="star", mouth="big", ear=-14, ear2=-14,
       flutter=6, bf_far=(0, 12, 0), bf_near=(0, 12, 0), back=B(226, 430, -220))
    _F(fr, 110, "落地、肉掌按住球（><）", sy=0.86, sx=1.08, eye="squeeze", mouth="w", ear=22, ear2=22, flutter=-6,
       mid=B(248, 432, -240), paws=held, fx=[R.motion_marks_svg(30, 380, -1), R.motion_marks_svg(470, 380, 1)])
    _F(fr, 200, "抱著球左晃（彎月眼、愛心）", rot=-6, sy=0.97, eye="arc", blush=1.5, ear=10, ear2=-4,
       mid=B(240, 432, -250), paws=held, props=[fx_part("fx_heart", 456, 150, 0.6, 12)])
    _F(fr, 200, "抱著球右晃", rot=6, sy=0.98, eye="arc", blush=1.4, ear=-4, ear2=10,
       mid=B(256, 432, -230), paws=held, props=[fx_part("fx_hearts_small", 40, 150, 0.6, -8)])
    _F(fr, 600, "Default 抱著球", mid=B(248, 432, -240), paws=held)
    return fr


def clip_pet_d() -> list[dict]:
    """摸摸（原版正面）：手（網頁疊 hand_prop）從右上摸頭 → 一縮 → 縮更低、彎月眼、耳朵往後貼、臉紅 → 往手那邊蹭兩下 →
    融化 → 手離開彈回來 → 意猶未盡晃 → Default。頭頂右上（約 x 330, y 150）留給手。"""
    fr = []
    hearts = lambda i: [fx_part("fx_hearts_small", 46, 190 - 18 * i, 0.55 + 0.05 * i, -8)]  # noqa: E731
    _F(fr, 90, "被摸到！一縮（耳朵往後）", eye="arc", mouth="o", sy=0.9, sx=1.06, ear=24, ear2=28, flutter=6, blush=1.3)
    _F(fr, 140, "縮更低、彎月眼、臉紅", eye="smile", mouth="w", sy=0.84, sx=1.1, ear=38, ear2=42, flutter=8, fphase=0.6,
       blush=1.8)
    _F(fr, 140, "往手那邊蹭（右傾）", eye="smile", sy=0.88, sx=1.06, rot=8, look=(0.015, -0.01), ear=30, ear2=44,
       flutter=7, fphase=1.3, blush=1.8, props=hearts(0))
    _F(fr, 120, "蹭更用力", eye="smile", sy=0.9, sx=1.04, rot=11, look=(0.02, -0.01), ear=26, ear2=48, flutter=9, fphase=2.0,
       blush=1.9, props=hearts(1))
    _F(fr, 120, "回來一點", eye="smile", mouth="w", sy=0.88, sx=1.05, rot=3, ear=34, ear2=38, flutter=5, fphase=2.7,
       blush=1.9, props=hearts(1))
    _F(fr, 120, "再蹭一下（毛被搓亂）", eye="smile", sy=0.9, sx=1.04, rot=10, look=(0.02, -0.01), ear=28, ear2=46, flutter=10,
       fphase=3.4, blush=2.0, props=hearts(2))
    _F(fr, 180, "融化（壓扁、張嘴笑）", eye="smile", sy=0.8, sx=1.13, rot=2, ear=40, ear2=40, flutter=6, fphase=4.1, blush=2.0,
       props=hearts(3))
    _F(fr, 100, "手離開、彈回來（耳朵彈起）", eye="wide", mouth="o", y=R.FOOT_Y - 12, sy=1.07, sx=0.95, ear=-14, ear2=-14,
       flutter=-5, fphase=4.8, blush=1.6)
    _F(fr, 150, "意猶未盡左晃（彎月眼）", eye="arc", rot=-5, sy=0.98, ear=6, ear2=-4, blush=1.5,
       props=[fx_part("fx_heart", 470, 160, 0.5, 14)])
    _F(fr, 150, "右晃", eye="arc", rot=4, ear=-3, ear2=6, blush=1.4, props=[fx_part("fx_heart", 474, 128, 0.45, 18)])
    _F(fr, 420, "Default（原版）")
    return fr


def clip_spin_d() -> list[dict]:
    """轉一圈（原版造型）：預備反扭→3/4 左→更側→背面（小尾巴）→3/4 右→回正面衝過頭（螺旋眼）→暈眩搖晃
    （星星繞頭、頭上漩渦）→甩甩頭→回神開心→Default。"""
    fr = []
    whoosh = lambda side: [  # noqa: E731
        f'<path d="M {248 + side*214} 236 Q {248 + side*236} 330 {248 + side*200} 420" fill="none" '
        f'stroke="{R.DEF_INK}" stroke-width="5" stroke-linecap="round" stroke-opacity="0.6"/>']
    orbit = lambda k: [R.star_svg(248 + 150 * math.cos(math.radians(k * 55 + j * 120)),  # noqa: E731
                                  112 + 18 * math.sin(math.radians(k * 55 + j * 120)), 13 - 2 * (j == 2), k * 20,
                                  "#FFD25A" if j != 1 else "#FFE58A") for j in range(3)]
    _F(fr, 80, "往反方向扭（預備）", rot=-6, sy=0.92, sx=1.05, eye="arc", mouth="w", ear=10, ear2=-6, look=(0.02, 0))
    _F(fr, 60, "轉到斜側（3/4）", view="q3", ear_tx=22, ear_sc_r=0.8, sx=0.96, rot=3, eye="wide", mouth="o", ear=-6,
       ear2=22, flutter=5, fphase=0.4, fx=whoosh(1))
    _F(fr, 60, "更側（耳朵甩開）", view="q3", look=(-0.17, 0), ear_tx=44, ear_sc_r=0.6, sx=0.93, rot=-3, eye="wide",
       mouth="o", ear=30, ear2=10, flutter=9, fphase=1.0, fx=whoosh(1))
    _F(fr, 60, "背面（露小尾巴）", view="back", sx=0.96, ear=22, ear2=-10, tail=(-6, 0, -20), flutter=6, fphase=1.6,
       fx=whoosh(-1))
    _F(fr, 60, "另一側", view="q3", facing="right", look=(-0.17, 0), ear_tx=44, ear_sc_r=0.6, sx=0.93, rot=-3, eye="wide",
       mouth="o", ear=30, ear2=10, flutter=9, fphase=2.2, fx=whoosh(1))
    _F(fr, 60, "轉回斜前方", view="q3", facing="right", ear_tx=22, ear_sc_r=0.8, sx=0.96, rot=3, eye="wide", mouth="o",
       ear=-6, ear2=22, flutter=5, fphase=2.8, fx=whoosh(1))
    _F(fr, 90, "正面停（衝過頭、螺旋眼）", rot=6, sx=1.05, sy=0.94, eye="spiral", mouth="wavy", ear=-16, ear2=20, flutter=-6,
       fphase=3.4)
    for k, (rot, ear, ear2) in enumerate([(-10, 14, -10), (9, -10, 16), (-7, 10, -6), (5, -4, 8)]):
        _F(fr, 130, "暈眩搖晃（螺旋眼、星星繞頭）", rot=rot, sx=1.02, sy=0.97 + 0.02 * (k % 2), eye="spiral", mouth="wavy",
           ear=ear, ear2=ear2, look=(0.01 * (1 if rot > 0 else -1), 0), fx=orbit(k),
           props=[fx_part("fx_swirl", 248 + rot * 3, 56, 0.5, k * 70)] if k < 2 else [])
    _F(fr, 110, "甩甩頭（恢復）", rot=-3, sy=1.03, eye="smile", mouth="o", ear=-14, ear2=-14, flutter=4, fphase=4.2)
    _F(fr, 150, "回神開心（彎月眼、小肉掌舉起）", y=R.FOOT_Y - 10, sy=1.05, sx=0.97, eye="arc", blush=1.4, ear=-6, ear2=-6,
       paws=[(70, 330, -6, -16, -60), (438, 330, 6, -16, 60)])
    _F(fr, 400, "Default（原版）")
    return fr


def clip_run_start_d() -> list[dict]:
    fr = clip_run_start()
    fr[2]["fx"] = [R.dust_svg(440, 468, 0.9, 1.0), R.speed_lines_svg(430, 300, 2, 30, 22, 0.6)]
    fr[-1]["fx"] = run_fx_d(0)
    fr[-1]["pose"] = clip_run_d()[0]["pose"]
    return fr


def clip_run_stop_d() -> list[dict]:
    fr = clip_run_stop()
    fr[0]["pose"] = clip_run_d()[2]["pose"]
    fr[0]["fx"] = run_fx_d(2)
    fr[1]["fx"] = [R.dust_svg(40, 462, 0.9), R.dust_svg(74, 466, 0.65, 0.8)]
    fr[2]["fx"] = [R.dust_svg(34, 458, 1.1, 0.45)]
    fr[1]["pose"]["rot"] = 6            # 原版身體大：後仰太多會讓屁股掉出畫面
    fr[1]["pose"]["y"] = R.FOOT_Y - 8
    return fr


# ================================================================== 10-11 晚：被打（hit）／哭哭（cry）／暈眩（dizzy）
# Andy：「頭暈應該要表情暈眩」「需要新增打他互動，並且他會哭哭」。無手（網頁已拿掉手）。
TEAR_FILL, TEAR_INK = R.TEAR_FILL, R.TEAR_INK


def _head_top_y(ox: float) -> float:
    """原圖 x=ox 那一欄，毛的最上緣（原圖座標，含描邊）。"""
    fg = R.default_assets()["masks"]["fg"]
    col = np.nonzero(fg[:, int(round(ox))])[0]
    return float(col.min()) if len(col) else 150.0


def drop_svg(x, y, r, ang) -> str:
    """飛行中的大顆淚滴：圓頭＋尾尖指向 ang 的反方向（ang＝速度方向，度）；藍描邊、白高光。"""
    return (f'<g transform="translate({x:.1f},{y:.1f}) rotate({ang - 90:.1f})">'
            f'<path d="M 0 {-1.9*r:.1f} C {0.8*r:.1f} {-0.8*r:.1f} {r:.1f} {-0.3*r:.1f} {r:.1f} {0.15*r:.1f} '
            f'A {r:.1f} {r:.1f} 0 1 1 {-r:.1f} {0.15*r:.1f} C {-r:.1f} {-0.3*r:.1f} {-0.8*r:.1f} {-0.8*r:.1f} 0 {-1.9*r:.1f} Z" '
            f'fill="{TEAR_FILL}" stroke="{TEAR_INK}" stroke-width="{max(2.6, r*0.33):.1f}" stroke-linejoin="round"/>'
            f'<ellipse cx="{-0.38*r:.1f}" cy="{-0.05*r:.1f}" rx="{0.26*r:.1f}" ry="{0.42*r:.1f}" fill="#fff"/></g>')


def puddle_svg(x, y, rx, ry, ripple=0.0) -> str:
    """地上的小水窪（淡藍＋藍描邊＋白高光）；ripple 0～1＝水波圈往外擴。"""
    s = (f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{TEAR_FILL}" fill-opacity="0.92" '
         f'stroke="{TEAR_INK}" stroke-width="3.2"/>'
         f'<path d="M {x-rx*0.55:.1f} {y-ry*0.25:.1f} Q {x-rx*0.2:.1f} {y-ry*0.6:.1f} {x+rx*0.1:.1f} {y-ry*0.45:.1f}" '
         f'fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round"/>')
    if ripple > 0.01:
        k = 0.35 + 0.55 * ripple
        s += (f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{rx*k:.1f}" ry="{ry*k:.1f}" fill="none" stroke="{TEAR_INK}" '
              f'stroke-width="2.4" stroke-opacity="{0.85 - 0.6*ripple:.2f}"/>')
    return s


def splash_svg(x, y, t, side) -> str:
    """水滴落地濺起：兩三顆小水珠往上外彈（t 0～1）。"""
    out = []
    for j, (dx, h, r) in enumerate(((-16, 26, 4.6), (4, 34, 5.2), (20, 22, 4.2))):
        xx = x + side * dx * (0.4 + 0.9 * t)
        yy = y - h * 4 * t * (1 - t) * 1.2 - 6
        out.append(f'<circle cx="{xx:.1f}" cy="{yy:.1f}" r="{r * (1 - 0.35*t):.1f}" fill="{TEAR_FILL}" stroke="{TEAR_INK}" '
                   f'stroke-width="2.4"/>')
    return "".join(out)


def bump_svg(x, y_top, k=1.0) -> str:
    """頭頂鼓起的包：桃粉圓丘從毛裡冒出（往毛裡漸層融回毛色、蓋住那段毛緣描邊），只描露出毛外的上緣；亮點。
    (x, y_top)＝這一格頭頂毛緣（世界座標）。"""
    rx, ry = 36 * k, 31 * k
    cy = y_top + 8                      # 圓丘中心埋在毛緣下面一點 → 露出約 ry-6
    gid = f"bp{int(x)}{int(y_top)}{int(k*100)}"
    clip = f"cl{gid}"
    y0, y1 = cy - ry, cy + ry
    f = lambda yy: max(0.0, min(1.0, (yy - y0) / (y1 - y0)))  # noqa: E731
    return (f'<defs><linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="0" y1="{y0:.1f}" x2="0" y2="{y1:.1f}">'
            f'<stop offset="0" stop-color="#F49A86"/><stop offset="{f(y_top - 4):.3f}" stop-color="#F8B9A6"/>'
            f'<stop offset="{f(y_top + 10):.3f}" stop-color="#FBE6DA"/><stop offset="{f(y_top + 16):.3f}" stop-color="#FDF5E9"/>'
            f'<stop offset="{f(y_top + 26):.3f}" stop-color="#FDF5E9" stop-opacity="0"/>'
            f'</linearGradient>'
            f'<clipPath id="{clip}"><rect x="{x-2*rx:.1f}" y="{y0-10:.1f}" width="{4*rx:.1f}" height="{y_top + 3 - (y0 - 10):.1f}"/></clipPath></defs>'
            f'<ellipse cx="{x:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="url(#{gid})"/>'
            f'<g clip-path="url(#{clip})"><ellipse cx="{x:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="none" '
            f'stroke="{R.DEF_INK}" stroke-width="6.2" stroke-linecap="round"/></g>'
            f'<ellipse cx="{x - rx*0.36:.1f}" cy="{cy - ry*0.6:.1f}" rx="{rx*0.2:.1f}" ry="{ry*0.13:.1f}" fill="#fff" '
            f'fill-opacity="0.9" transform="rotate(-28 {x - rx*0.36:.1f} {cy - ry*0.6:.1f})"/>')


def bump_top(y_top, k=1.0):
    return y_top + 8 - 31 * k


def burst_up_svg(x, y, r=60, n=7, w=6.0) -> str:
    """只往上半圈放射的衝擊短線（敲中頭頂那一下，不壓進身體）。"""
    out = []
    for i in range(n):
        a = math.radians(-165 + i * 150 / (n - 1))
        x0, y0 = x + r * 0.5 * math.cos(a), y + r * 0.5 * math.sin(a)
        x1, y1 = x + r * math.cos(a), y + r * math.sin(a)
        out.append(f'<path d="M {x0:.1f} {y0:.1f} L {x1:.1f} {y1:.1f}" stroke="{R.DEF_INK}" stroke-width="{w}" stroke-linecap="round"/>')
    return "".join(out)


def throb_svg(x, y, r, a=1.0) -> str:
    """包兩側一跳一跳的「痛」短弧線。"""
    out = []
    for sg in (-1, 1):
        for j, d in enumerate((0, 10)):
            xx = x + sg * (r + 8 + d)
            out.append(f'<path d="M {xx:.1f} {y - 9 - j*3:.1f} Q {xx + sg*6:.1f} {y:.1f} {xx:.1f} {y + 9 + j*3:.1f}" fill="none" '
                       f'stroke="{R.DEF_INK}" stroke-width="4.5" stroke-linecap="round" stroke-opacity="{a:.2f}"/>')
    return "".join(out)


def _bump_at(pose, ox=272.0, k=1.0):
    """包：照這一格實際畫出來的本體（含毛飄）長出來。回傳 (X, 毛緣Y, 圖層 S 倍)。
    填色在毛裡面往內 ~12px 漸層融回毛色（蓋住那段毛緣描邊）；描邊只畫在身體外面（往內吃 2px 跟毛緣描邊接起來）。"""
    from PIL import ImageFilter
    full = {**R.DEFAULT, "eye": "default", "mouth": "default", "paws": None, **pose}
    X, _ = _dp(pose, ox, _head_top_y(ox))
    body = R.def_body_layer(full).getchannel("A")
    a = np.asarray(body) > 128
    tops = []
    for xx in range(int((X - 14) * R.S), int((X + 14) * R.S) + 1, 2):
        c = np.nonzero(a[:, xx])[0]
        if len(c):
            tops.append(c.min() / R.S)
    Y = float(np.median(tops))
    rx, ry = 36 * k, 31 * k
    cy = Y + 8
    gid = f"bp{int(X)}{int(Y)}{int(k*100)}"
    fill = R.svg_layer(
        f'<defs><linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="0" y1="{cy-ry:.1f}" x2="0" y2="{cy+ry:.1f}">'
        f'<stop offset="0" stop-color="#F49A86"/><stop offset="0.55" stop-color="#F8BCA9"/><stop offset="1" stop-color="#FCE9DE"/>'
        f'</linearGradient></defs><ellipse cx="{X:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="url(#{gid})"/>'
        f'<ellipse cx="{X - rx*0.36:.1f}" cy="{cy - ry*0.6:.1f}" rx="{rx*0.2:.1f}" ry="{ry*0.13:.1f}" fill="#fff" '
        f'fill-opacity="0.9" transform="rotate(-28 {X - rx*0.36:.1f} {cy - ry*0.6:.1f})"/>')
    stroke = R.svg_layer(f'<ellipse cx="{X:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="none" '
                         f'stroke="{R.DEF_INK}" stroke-width="6.2"/>')
    ba = np.asarray(body).astype(np.float32) / 255
    deep = np.asarray(body.filter(ImageFilter.MinFilter(25))).astype(np.float32) / 255   # 往內 ~6px（512 單位）
    blur = np.asarray(Image.fromarray((deep * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(10))).astype(np.float32) / 255
    fa = np.asarray(fill.getchannel("A")).astype(np.float32) * np.clip(1 - blur * 1.6, 0, 1)
    fill.putalpha(Image.fromarray(fa.astype(np.uint8)))
    ins = np.asarray(body.filter(ImageFilter.MinFilter(9))).astype(np.float32) / 255     # 往內 2px
    sa = np.asarray(stroke.getchannel("A")).astype(np.float32) * (1 - ins)
    stroke.putalpha(Image.fromarray(sa.astype(np.uint8)))
    fill.alpha_composite(stroke)
    return X, Y, fill


def bump_top(y_top, k=1.0):
    return y_top + 8 - 31 * k


def clip_hit() -> list[dict]:
    """被敲頭（播一次 6 格）：第 1 格就被敲中→瞬間壓扁、><、耳朵被壓扁、頭頂衝擊線→彈起拉長、包冒出來＋星星→
    回壓（波浪嘴）→小彈、眼睛含淚（包一跳一跳）→停一下委屈→回 Default。網頁的槌子從右上往頭頂敲（第 1 格接觸）。"""
    fr = []

    def add(ms, label, bump=None, stars=None, throb=0.0, extra=None, names=None, **kw):
        pose = dict(kw)
        fx, nm, pf = [], [], []
        if bump:
            X, Y, lay = _bump_at(pose, k=bump)
            pf.append(lay)
            bt = bump_top(Y, bump)
            if throb > 0:
                fx.append(throb_svg(X, (bt + Y) / 2, 36 * bump, throb)); nm.append("throb")
            for j, (ang, r) in enumerate(stars or []):
                a = math.radians(ang)
                fx.append(R.star_svg(X + 100 * math.cos(a), bt - 6 + 26 * math.sin(a), r, ang * 0.5,
                                     "#FFD25A" if j % 2 == 0 else "#FFE58A").replace('stroke-width="3.5"', 'stroke-width="4.2"'))
                nm.append(f"star{j}")
        for s, n in zip(extra or [], names or []):
            fx.append(s); nm.append(n)
        fr.append(dict(pose=pose, ms=ms, label=label, fx=fx, fx_names=nm, props_front=pf,
                       prop_names={"propF0": "bump"} if pf else {}))

    # 第 1 格：敲中瞬間
    p1 = dict(sy=0.7, sx=1.2, eye="squeeze", mouth="o", ear=46, ear2=46, ear_sc_l=0.8, ear_sc_r=0.8, flutter=-9)
    tx, ty = _dp(p1, 262, _head_top_y(262))
    hitfx = [burst_up_svg(tx, ty - 8, 66, 7, 6), R.text_svg("咚！", 384, 168, 46, 12)]
    hitfx += [R.dust_svg(70, 470, 0.9), R.dust_svg(428, 470, 0.9)]
    add(60, "敲中！瞬間壓扁（><、耳朵被壓扁、衝擊線）", extra=hitfx, names=["burst", "text", "dust0", "dust1"], **p1)
    add(70, "彈起拉長、頭頂冒包＋星星（耳朵甩起）", bump=1.3, stars=[(-160, 15), (-20, 14), (-100, 11)],
        y=R.FOOT_Y - 16, sy=1.14, sx=0.9, eye="squeeze", mouth="o", ear=-24, ear2=-24, flutter=8, fphase=0.6)
    add(90, "回壓（波浪嘴、星星繞包）", bump=1.05, stars=[(-185, 14), (-35, 13), (-80, 10)],
        sy=0.88, sx=1.08, eye="squeeze", mouth="wavy", ear=22, ear2=22, flutter=-5, fphase=1.2)
    add(110, "小彈一下、眼睛含淚（包一跳一跳）", bump=1.12, stars=[(-215, 12), (-25, 11)], throb=1.0,
        y=R.FOOT_Y - 6, sy=1.04, sx=0.97, eye="cry_wide", mouth="frown", ear=12, ear2=16, blush=1.4, flutter=3, fphase=1.8)
    add(300, "委屈（含淚、撇嘴，包還在跳）", bump=1.0, stars=[(-165, 10)], throb=0.8,
        rot=-3, sy=0.99, eye="cry_wide", mouth="frown", ear=26, ear2=30, blush=1.5)
    add(400, "Default（原版）")
    return fr


def cry_pose(i: int) -> dict:
    """哭哭循環 8 格（一個循環兩次抽噎）：0、4＝抽一下往上（大哭 ><＋張嘴）、1、5＝抽完壓扁、其餘＝含淚撇嘴微抖。"""
    k = i % 4
    j = i // 4
    shake = (-3 if (i % 2) else 3) * (1 if j == 0 else -1)
    if k == 0:
        return dict(y=R.FOOT_Y - 8, sy=1.07, sx=0.95, rot=shake * 0.6, x=R.CX + shake * 0.6, eye="cry_squeeze", mouth="wail",
                    ear=30, ear2=34, blush=1.4, flutter=5, fphase=0.8 + j, bf_far=(0, 6, 0), bf_near=(0, 6, 0))
    if k == 1:
        return dict(sy=0.9, sx=1.07, rot=-shake * 0.5, eye="cry_squeeze", mouth="wail", ear=40, ear2=44, blush=1.4,
                    flutter=-5, fphase=1.4 + j)
    if k == 2:
        return dict(sy=1.0, sx=1.0, rot=shake * 0.7, x=R.CX + shake, eye="cry_wide", mouth="frown", ear=38, ear2=36,
                    blush=1.35, flutter=2, fphase=2.0 + j)
    return dict(sy=0.97, sx=1.02, rot=-shake * 0.4, x=R.CX - shake * 0.6, eye="cry_wide", mouth="frown", ear=34, ear2=38,
                blush=1.35, flutter=-2, fphase=2.6 + j)


def cry_fx(i: int, n: int = 8, pose=None):
    """兩眼外眼角噴出大顆淚滴（每邊 3 顆錯開相位，拋物線落地）→ 落到兩側水窪、濺起小水珠、水波圈。"""
    fx, nm = [], []
    eye_l = _dp(pose, R.DEF_EYE_L[0], R.DEF_EYE_L[1])
    eye_r = _dp(pose, R.DEF_EYE_R[0], R.DEF_EYE_R[1])
    sides = [(-1, (eye_l[0] - 42, eye_l[1] - 8), (52.0, 471.0)), (1, (eye_r[0] + 42, eye_r[1] - 10), (444.0, 469.0))]
    wail = cry_pose(i)["mouth"] == "wail"
    for sg, S0, L in sides:
        # 水窪（先畫，淚滴落在上面）
        land_t = [((i / n) + q / 3 + (0.5 if sg > 0 else 0.0) / 3) % 1.0 for q in range(3)]
        rip = max([1 - t / 0.34 for t in land_t if t < 0.34] or [0.0])
        fx.append(puddle_svg(L[0], L[1], 36, 8.5, rip if rip > 0 else 0.0)); nm.append(f"puddle{sg}")
        for q, t in enumerate(land_t):
            H = 70 if wail else 52
            x = S0[0] + (L[0] - S0[0]) * t + sg * 34 * 4 * t * (1 - t)      # 往外噴的弧
            y = S0[1] - 4 * H * t * (1 - t) * 0.9 + (L[1] - 12 - S0[1]) * t * t
            if t < 0.2 and not wail:
                continue                      # 沒在大哭時，剛冒出眼角那一段不畫（淚珠還含在眼角）
            if t > 0.9:
                continue                      # 快落地那段由水窪＋濺水接手
            vx = (L[0] - S0[0]) + sg * 34 * 4 * (1 - 2 * t)
            vy = -4 * H * (1 - 2 * t) * 0.9 + 2 * (L[1] - 12 - S0[1]) * t
            ang = math.degrees(math.atan2(vy, vx))
            r = 9.5 + 3.5 * min(1.0, t * 2) + (1.5 if wail else 0)
            fx.append(drop_svg(x, y, r, ang)); nm.append(f"drop{sg}_{q}")
            if t < 0.22:   # 剛落地的那顆（相位循環）在水窪濺起
                pass
        just = [t for t in land_t if t < 0.3]
        if just:
            fx.append(splash_svg(L[0] + sg * 6, L[1], just[0] / 0.3, sg)); nm.append(f"splash{sg}")
    return fx, nm


def clip_cry() -> list[dict]:
    fr = []
    durs = [70, 90, 180, 160, 70, 90, 180, 200]
    labels = ["抽一下往上（大哭 ><、張嘴、淚噴出）", "抽完壓扁（耳朵垂到底）", "含淚撇嘴（八字眉、抖）", "抖回來（淚珠滾落）",
              "又抽一下（大哭）", "壓扁（抽噎）", "含淚撇嘴（往另一邊抖）", "吸鼻子（接回第 1 格）"]
    for i in range(8):
        p = cry_pose(i)
        fx, nm = cry_fx(i, 8, p)
        fr.append(dict(pose=p, ms=durs[i], label=labels[i], fx=fx, fx_names=nm))
    return fr


def dizzy_pose(i: int, n: int = 8) -> dict:
    """暈眩循環：身體左右慢晃（弧線）、耳朵一高一低（慢一拍）、漩渦眼每格轉、歪波浪嘴、小腳站不穩。"""
    a = TAU * i / n
    s = math.sin(a)
    return dict(rot=8 * s, x=R.CX + 9 * s, y=R.FOOT_Y - 3 * abs(math.cos(a)), sy=1 - 0.025 * math.cos(2 * a),
                sx=1 + 0.02 * math.cos(2 * a), eye=f"swirl:{-60 * i}", mouth=f"wobble:{-7 * s:.1f}:{a * 2:.2f}",
                ear=6 + 20 * math.sin(a - 0.9), ear2=6 - 20 * math.sin(a - 0.9), blush=1.0,
                flutter=4 * math.sin(a - 0.6), fphase=a,
                bf_far=(0, -8 * max(0.0, -s), 0), bf_near=(0, -8 * max(0.0, s), 0))


def dizzy_stars(i: int, pose, n: int = 8):
    """頭上 3 顆小星星繞圈（一個循環繞一圈）：前半圈在頭前面、大一點；後半圈在頭後面、小一點。"""
    tx, ty = _dp(pose, 253, _head_top_y(253))
    front, back, nm = [], [], []
    for j in range(3):
        th = TAU * (i / n) + j * TAU / 3
        x = tx + 118 * math.cos(th)
        y = ty - 26 + 20 * math.sin(th)
        depth = math.sin(th)
        r = 13 + 4 * depth
        svg = R.star_svg(x, y, r, i * 25 + j * 40, "#FFD25A" if j != 1 else "#FFE58A").replace(
            'stroke-width="3.5"', 'stroke-width="4"')
        if depth >= -0.2:
            front.append(svg); nm.append(f"star{j}")
        else:
            back.append(R.svg_layer(svg))
    return front, nm, back


def clip_dizzy() -> list[dict]:
    fr = []
    labels = ["晃到中間（漩渦眼 @_@）", "往右晃", "右邊最遠（停一下）", "晃回來", "中間", "往左晃", "左邊最遠（停一下）", "晃回來（接回第 1 格）"]
    durs = [170, 170, 200, 170, 170, 170, 200, 170]
    for i in range(8):
        p = dizzy_pose(i)
        front, nm, back = dizzy_stars(i, p)
        fr.append(dict(pose=p, ms=durs[i], label=labels[i], fx=front, fx_names=nm, props_back=back))
    return fr


def clip_spin_dizzy() -> list[dict]:
    """轉一圈（改版）：前 6 格照舊轉身；第 7 格衝過頭直接變暈眩臉（漩渦眼＋歪波浪嘴＋星星），
    晃 4 格（＝bibi_dizzy 第 6、7、8、1 格，倒數第 2 格跟 bibi_dizzy 第 1 格一模一樣，可以直接接暈眩循環），最後 1 格 Default。
    不畫手（Andy：伸出去的手太奇怪了）。"""
    fr = clip_spin_d()[:6]
    p = dict(rot=10, sx=1.06, sy=0.93, eye="swirl:30", mouth="wobble:6:0.5", ear=-18, ear2=22, flutter=-7, fphase=3.4)
    front, nm, back = dizzy_stars(4, p)
    fr.append(dict(pose=p, ms=90, label="正面停（衝過頭）→ 暈眩臉、星星冒出", fx=front, fx_names=nm, props_back=back))
    for k, i in enumerate((5, 6, 7, 0)):
        p = dizzy_pose(i)
        front, nm, back = dizzy_stars(i, p)
        lab = ["暈眩晃（往左）", "暈眩晃（左邊最遠）", "暈眩晃回來", "暈眩臉（＝bibi_dizzy 第 1 格，可接暈眩循環）"][k]
        fr.append(dict(pose=p, ms=[150, 190, 150, 220][k], label=lab, fx=front, fx_names=nm, props_back=back))
    fr.append(dict(pose={}, ms=400, label="Default（原版）", fx=[]))
    return fr


def hammer_svg(cx=48.0, cy=48.0, s=1.0, rot=-32.0, fx=True) -> str:
    """玩具嗶嗶槌（96 座標，s 倍）：圓胖紅色槌身＋兩端黃色風琴摺圓蓋＋黃色握柄（紅色握把尾端）；
    打擊端（左）外側有一顆星星與三條衝擊短線。"""
    INK = "#1A0907"
    RED, RED_D, YEL, YEL_D = "#EE5A4A", "#C8402F", "#FFD25A", "#E9B23A"
    st = f'stroke="{INK}" stroke-width="{4.2 / s:.2f}" stroke-linejoin="round" stroke-linecap="round"'   # 縮小後描邊仍＝其他圖示的 4.2
    cap = lambda sg: (  # noqa: E731
        f'<path d="M {sg*17} -17 Q {sg*29} -17 {sg*29} -5 Q {sg*29} 7 {sg*17} 7 Z" fill="{YEL}" {st}/>'
        f'<path d="M {sg*21.5} -15.5 L {sg*21.5} 5.5 M {sg*25.5} -13 L {sg*25.5} 3" stroke="{YEL_D}" stroke-width="2.6" '
        f'stroke-linecap="round"/>')
    g = (
        f'<rect x="-5" y="4" width="10" height="36" rx="5" fill="{YEL}" {st}/>'
        f'<path d="M -1.5 10 L -1.5 26" stroke="#FFF1B8" stroke-width="2.4" stroke-linecap="round"/>'
        f'<rect x="-6.5" y="30" width="13" height="13" rx="6" fill="{RED}" {st}/>'
        + cap(-1) + cap(1) +
        f'<rect x="-18" y="-19" width="36" height="28" rx="11" fill="{RED}" {st}/>'
        f'<path d="M -10 -13 Q 0 -15.5 10 -13" fill="none" stroke="#FFA597" stroke-width="3.4" stroke-linecap="round"/>'
        f'<path d="M -15 3 Q 0 6 15 3" fill="none" stroke="{RED_D}" stroke-width="2.6" stroke-linecap="round"/>'
    )
    out = f'<g transform="translate({cx},{cy}) scale({s}) rotate({rot})">{g}</g>'
    if fx:
        a = math.radians(rot)
        lx, ly = -34.0, -5.0                                  # 打擊端外側（局部座標）
        ex, ey = cx + s * (lx * math.cos(a) - ly * math.sin(a)), cy + s * (lx * math.sin(a) + ly * math.cos(a))
        base = math.degrees(math.atan2(ey - cy, ex - cx))
        lines = "".join(
            f'<path d="M {ex + s*math.cos(math.radians(base + d))*4:.1f} {ey + s*math.sin(math.radians(base + d))*4:.1f} '
            f'L {ex + s*math.cos(math.radians(base + d))*10:.1f} {ey + s*math.sin(math.radians(base + d))*10:.1f}" '
            f'stroke="{INK}" stroke-width="{3.6*s:.1f}" stroke-linecap="round"/>' for d in (-50, 0, 50))
        star = R.star_svg(ex + 4 * s, ey + 17 * s, 7.5 * s, 12, YEL).replace(
            'stroke-width="3.5"', f'stroke-width="{3.2*s:.1f}"').replace(R.INK, INK)
        out = lines + out + star
    return out


def make_hammer_icon(outdir: Path):
    """96×96 奶油白圓底圖示（與 bibi_icons 同版型）＋更新 index.md。"""
    import bibi_icons_g1 as IC
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="384" height="384" viewBox="0 0 96 96">'
           + IC.badge(hammer_svg(53, 43, 0.8, -35)) + '</svg>')
    import cairosvg
    import io
    im = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode("utf-8")))).convert("RGBA")
    im = im.convert("RGBa").resize((96, 96), Image.LANCZOS).convert("RGBA")
    outdir.mkdir(parents=True, exist_ok=True)
    im.save(outdir / "hammer.png", optimize=True)
    idx = outdir / "index.md"
    txt = idx.read_text(encoding="utf-8")
    row = '| <img src="hammer.png" width="48"> | `hammer.png` | 玩具嗶嗶槌 | 敲一下（bibi_hit → bibi_cry） |'
    if "hammer.png" not in txt:
        txt = txt.replace("# 比比互動小圈圖示（10 個）", "# 比比互動小圈圖示（11 個）").rstrip("\n") + "\n" + row + "\n"
        txt += ("\n- `hammer.png`（10-11 晚新增）：`python scripts/anim/bibi_moves_v2.py --out <scratchpad>/bibi_v2 "
                "--repo-out docs/anim --only hit` 會一起重畫（`make_hammer_icon`）。\n")
        idx.write_text(txt, encoding="utf-8")
    return im


def make_hammer_prop(path: Path):
    """512 透明大槌子（網頁疊在比比頭上右上方揮下來用；不含星星特效）。"""
    lay = R.svg_layer(f'<g transform="scale(5.33)">{hammer_svg(48, 50, 1.25, -35, fx=False)}</g>')
    lay.convert("RGBa").resize((512, 512), Image.LANCZOS).convert("RGBA").save(path)


def verify_fx_pairs(frs, checks):
    """特效彼此也不准互相壓（星星／包／衝擊線／字／淚滴）；淚滴落進水窪、濺水在水窪上是設計，不算。"""
    ok_pairs = {("drop", "puddle"), ("splash", "puddle"), ("bump", "throb")}
    bad = []
    for i, (fr, c) in enumerate(zip(frs, checks)):
        names = fr.get("fx_names") or []
        ms_ = c.get("__masks", {})
        ks = [(f"fx{j}", nm) for j, nm in enumerate(names) if f"fx{j}" in ms_]
        ks += [(k_, v_) for k_, v_ in (fr.get("prop_names") or {}).items() if k_ in ms_]
        for a in range(len(ks)):
            for b in range(a + 1, len(ks)):
                na, nb = ks[a][1], ks[b][1]
                ta, tb = na.rstrip("0123456789-_"), nb.rstrip("0123456789-_")
                ta, tb = ta.split("-")[0].rstrip("0123456789"), tb.split("-")[0].rstrip("0123456789")
                if (ta, tb) in ok_pairs or (tb, ta) in ok_pairs:
                    continue
                n = int((ms_[ks[a][0]] & ms_[ks[b][0]]).sum())
                if n:
                    bad.append(f"第 {i+1} 格 {na}×{nb} 互壓 {n} 格點")
    return bad


# ================================================================== 渲染
CLIPS = {
    "hit": dict(make=clip_hit, facing="left", rig="default", loop=False,
                note="播一次（點槌子圖示）；第 1 格就是敲中；網頁可把 hammer_prop.png 從右上揮到頭頂（約 x 300, y 150）只在第 1 格碰到。"
                     "最後一格＝Default；要哭就接 bibi_cry。"),
    "cry": dict(make=clip_cry, facing="left", rig="default", loop=True,
                note="全部 8 格循環（一輪抽噎兩次，約 1 秒）；兩眼淚滴拋物線落到身體兩側的小水窪（左 x≈52、右 x≈444，地面 y≈470）。"),
    "dizzy": dict(make=clip_dizzy, facing="left", rig="default", loop=True,
                  note="全部 8 格循環（約 1.4 秒）；spin_v2 倒數第 2 格＝本組第 1 格，可直接接；播完切 Default。"),
    "highfive": dict(make=clip_highfive, facing="left", rig="default", convert=True, loop=False, note="播一次；網頁的手在右上（約 x 400, y 190）迎上來擊掌（第 3 格）。"),
    "dance": dict(make=clip_dance, facing="left", rig="default", convert=True, loop=False, note="播一次；最後一格＝站好。"),
    "hug": dict(make=clip_hug, facing="left", rig="default", convert=True, loop=False, note="播一次；最後一格＝站好。"),
    "sleep_loop": dict(make=clip_sleep_loop, facing="left", rig="default", convert=True, loop=True, note="全部 8 格循環（呼吸一輪＋Zzz 輪流往上飄）。"),
    "wake_once": dict(make=clip_wake_once, facing="left", rig="default", convert=True, loop=False, note="播一次（打瞌睡時被點）；最後一格＝站好。"),
    "selfie": dict(make=clip_selfie, facing="left", rig="default", convert=True, loop=False, note="播一次；三個姿勢各閃一次光；最後一格＝看鏡頭笑。"),
    "pet_v2": dict(make=clip_pet_d, facing="left", rig="default", loop=False,
                   note="播一次；網頁同時把 hand_prop.png 從右上伸到頭頂右上（約 x 300, y 190，第 1～7 格），第 8 格手離開。"),
    "spin_v2": dict(make=clip_spin_dizzy, facing="left", rig="default", loop=False,
                    note="播一次；第 7～11 格收在暈眩臉（漩渦眼＋歪波浪嘴＋星星繞頭）；第 11 格＝bibi_dizzy 第 1 格（要接暈眩循環就在第 11 格切過去），"
                         "第 12 格＝Default。"),
    "popcorn": dict(make=clip_popcorn_d, facing="left", rig="default", loop=False,
                    note="播一次（點爆米花圖示）；第 1 格直接起跳預備，最後一格＝正面開心定格，可接 happy_hop。"),
    "eat_grass_v2": dict(make=clip_eat_grass_d, facing="left", loop=False, rig="default",
                         note="播一次；接在 receive_grass 後面（第 1 格直接把草送到嘴邊）；最後一格＝正面滿足，可接 happy_hop。"),
    "happy_hop": dict(make=clip_happy_hop_d, facing="left", loop=True, rig="default",
                      note="全部 10 格循環＝大部分情境的預設待機（正面，不分左右）。"),
    "receive": dict(make=lambda: clip_receive_d(""), facing="left", loop=False, rig="default",
                    note="播一次；東西由網頁疊（從右上遞進來），第 4～5 格肉掌在右上 (约 x 350, y 330) 接。"),
    "receive_grass": dict(make=lambda: clip_receive_d("grass"), facing="left", loop=False, rig="default",
                          note="播一次；畫面內含牧草：第 4 格起草在右前方肉掌上，第 6 格抱到胸前。接 eat_grass_v2。"),
    "receive_ball": dict(make=lambda: clip_receive_d("ball"), facing="left", loop=False, rig="default",
                         note="播一次；畫面內含球：第 4 格起球在右前方肉掌上，第 6 格抱到胸前。之後網頁丟球→run_r→ball_catch。"),
    "run_r": dict(make=clip_run_d, facing="right", rig="default", convert=True, push=False, loop=True, note="全部 8 格循環（第 8 格接回第 1 格）；網頁負責位移，這裡原地跑。"),
    "run_l": dict(make=clip_run_d, facing="left", rig="default", convert=True, push=False, loop=True, note="同 run_r，面向左。"),
    "run_start_r": dict(make=clip_run_start_d, facing="right", rig="default", convert=True, push=False, loop=False, note="播一次；最後一格＝run_r 第 1 格，直接接循環。"),
    "run_stop_r": dict(make=clip_run_stop_d, facing="right", rig="default", convert=True, push=False, loop=False, note="播一次；第 1 格＝跑步中，最後一格＝側面站好。"),
    "ball_catch": dict(make=clip_ball_catch_d, facing="right", rig="default", loop=False,
                       note="播一次；接在 run_r 後面（球在比比右前方）。最後一格停住＝正面抱球。"),
    "ball_catch_l": dict(make=clip_ball_catch_d, facing="left", rig="default", loop=False, note="同 ball_catch，面向左（接 run_l）。"),
}


def _push_svg(svg: str, cx: float, cy: float, k: float = 1.3) -> str:
    """把一段效果 SVG 以 (cx,cy) 為中心整段往外推 k 倍（位置）——但不能只縮放位置，所以整段縮放 k 再縮回一點大小。
    做法：先算這段的外框中心 c，平移到 cx+(c-cx)*k，大小放 1.12 倍。"""
    lay = R.svg_layer(svg)
    bb = lay.getchannel("A").getbbox()
    if not bb:
        return svg
    c0 = ((bb[0] + bb[2]) / 2 / R.S, (bb[1] + bb[3]) / 2 / R.S)
    c1 = [cx + (c0[0] - cx) * k, cy + (c0[1] - cy) * k]
    sc = 1.12
    # 推出去之後不准出框：外框（放大後）超出 8px 邊界就往內收
    hw, hh = (bb[2] - bb[0]) / 2 / R.S * sc, (bb[3] - bb[1]) / 2 / R.S * sc
    c1[0] = min(max(c1[0], 8 + hw), R.SIZE - 8 - hw)
    c1[1] = min(max(c1[1], 8 + hh), R.SIZE - 8 - hh)
    return (f'<g transform="translate({c1[0]:.1f},{c1[1]:.1f}) scale({sc}) translate({-c0[0]:.1f},{-c0[1]:.1f})">'
            f'{svg}</g>')


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
        if cfg.get("rig") == "default":      # 原版 Default 造型骨架
            fxs, pfs = fr.get("fx"), fr.get("props_front")
            if cfg.get("convert") and not cfg.get("push", True):
                dp = R.to_default_pose(pose)
            elif cfg.get("convert"):
                dp = R.to_default_pose(pose)
                # v1 的效果位置是照小一號的身體排的：以身體中心往外推 1.3 倍（符號本身放大 1.15）
                cx_, cy_ = R.CX, 320.0
                fxs = [_push_svg(x, cx_, cy_) for x in ([fxs] if isinstance(fxs, str) else (fxs or []))]
                pf2 = []
                for it in (pfs or []):
                    if isinstance(it, Image.Image) or callable(it):
                        pf2.append(it)
                    else:
                        im_, x_, y_, r_, anc_ = it
                        nx_, ny_ = cx_ + (x_ - cx_) * 1.3, cy_ + (y_ - cy_) * 1.3
                        hw_, hh_ = im_.width / R.S / 2 + 8, im_.height / R.S / 2 + 8
                        nx_ = min(max(nx_, hw_), R.SIZE - hw_)
                        ny_ = min(max(ny_, hh_), R.SIZE - hh_)
                        pf2.append((im_, nx_, ny_, r_, anc_))
                pfs = pf2
            else:
                dp = dict(fr["pose"], facing=ff)
            can, boxes = R.compose_default(dp, props_mid=mid, props_front=pfs,
                                           props_back=fr.get("props_back"), fx=fxs)
        else:
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


def compare_sheet(imgs, frs, path, n=3):
    """與原版並排：default_idle_1011、jump/animation.gif 第 9 格、這組挑 n 格（含第 1 格與最後一格）。"""
    from PIL import ImageSequence
    jump = [f.convert("RGBA") for f in ImageSequence.Iterator(Image.open(R.ROOT / "docs/anim/jump/animation.gif"))]
    pick = sorted({0, len(imgs) // 2, len(imgs) - 1})[:n]
    cells = [(Image.open(R.DEF_SRC).convert("RGBA"), "原圖 default_idle"), (jump[8], "原版 jump 第 9 格")]
    cells += [(imgs[i], f"{i+1:02d} {frs[i]['label']}"[:14]) for i in pick]
    W = Image.new("RGB", (400 * len(cells), 448), (30, 33, 40))
    d = ImageDraw.Draw(W)
    f = ImageFont.truetype(FONT, 20)
    for j, (im, t) in enumerate(cells):
        b = Image.new("RGBA", (512, 512), (252, 246, 239, 255))
        b.alpha_composite(im)
        W.paste(b.convert("RGB").resize((400, 400), Image.LANCZOS), (400 * j, 48))
        d.text((400 * j + 8, 12), t, font=f, fill=(240, 240, 240))
    W.save(path)


def save_webps(imgs, durs, p160, p512, loop, target_kb=60):
    lp = 0 if loop else 1
    sm = [im.convert("RGBa").resize((160, 160), Image.LANCZOS).convert("RGBA") for im in imgs]
    # 先降色彩品質到 62，還超過再降透明度通道品質（原版毛邊細節多，16 格容易超過 60KB）
    tries = [(q_, 100) for q_ in (86, 80, 74, 68, 62)] + [(q_, aq) for aq in (80, 65, 50) for q_ in (70, 62, 54, 46)]
    for q, aq in tries:
        sm[0].save(p160, save_all=True, append_images=sm[1:], duration=durs, loop=lp, lossless=False,
                   quality=q, alpha_quality=aq, method=6)
        kb = Path(p160).stat().st_size / 1024
        if kb <= target_kb:
            break
    q = f"{q}/a{aq}"
    imgs[0].save(p512, save_all=True, append_images=imgs[1:], duration=durs, loop=lp, lossless=False,
                 quality=88, method=6)
    return kb, q


def write_storyboard(name, frs, durs, path, extra=""):
    cfg = CLIPS[name]
    total = sum(durs)
    lines = [f"# 比比・{name}（v2 骨架重做，{len(frs)} 格）", "",
             "- 退件原因（Andy 10-11）：舊版是原 GIF 第 0 張變形＋貼東西，沒有真的肢體動作。",
             "- 做法：`scripts/anim/bibi_rig.py` 原版 Default 骨架（本體、耳朵、肉掌、腳、尾巴、眼、嘴、腮紅獨立擺位）＋"
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
        if any(fr.get("fx_names") or fr.get("prop_names") for fr in frs):
            bad += verify_fx_pairs(frs, checks)
        n = len(imgs)
        pick = list(range(n)) if n <= 12 else sorted({round(i * (n - 1) / 11) for i in range(12)})
        contact_sheet(imgs, frs, rd / "sheet_12.png", pick, 4, f"bibi_{name}：12 格接觸表（共 {n} 格）")
        contact_sheet(imgs, frs, rd / "sheet_all.png", None, 4, f"bibi_{name}：全部 {n} 格")
        write_storyboard(name, frs, durs, rd / "storyboard.md")
        if name.startswith("ball_catch"):
            make_ball_prop(rd / "ball_prop.png")
        if CLIPS[name].get("rig") == "default":
            compare_sheet(imgs, frs, rd / "compare_default.png")
        if name == "pet_v2":
            make_pet_hand(rd / "hand_prop.png")
        if name == "hit":
            make_hammer_prop(rd / "hammer_prop.png")
            make_hammer_icon(rep / "bibi_icons")
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
