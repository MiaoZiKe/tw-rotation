"""把比比動畫素材縮成網站右下角用的 160px 動態 WebP（site/brand/bibi/<名稱>.webp）。

為什麼要這支（2026-10-11，Andy：「右下方的GIF圖多點變化…可以摸摸他 餵它吃草 跟他玩球 讓他轉圈圈」）：
  docs/anim 的素材是 512px、每組約 200KB，整包 62MB，不能直接搬進 site。
  網站只需要右下角約 104px 顯示（2x 螢幕 ≈ 160px 就夠），而且每組都要能「用到才載」。

裁切一律用同一個框（不是每組各自裁到最小）：素材庫全部同一個場景座標（身體縮 0.75、中心 x=248、腳底 y=482，
見 docs/anim/bibi_library/index.md），用同一個框切，比比在每一組動畫裡的大小與腳底位置都一樣，
換動作時不會忽大忽小、上下跳。框外的道具（彩帶、金幣）會被切掉一部分，可接受。

素材來源順序：docs/anim/bibi_library/<名稱>/anim.webp（現有 67 組）→ docs/anim/bibi_<名稱>/anim.webp（動畫單位新交件）。
新素材到了：把名稱加進 NAMES、跑這支、再改 site/bibi.js 的 MAP（那張表寫「哪個動作用哪個檔」）。

用法：python scripts/anim/bibi_site.py            # 全部重做
      python scripts/anim/bibi_site.py props      # 給草／給球的手與道具（site/brand/bibi/props/）
      python scripts/anim/bibi_site.py pet ball    # 只做這幾組
輸出最後一行印出每組的總長毫秒（site/bibi.js 的 MS 表要抄這個數字，動作播完才回待機）。
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from PIL import Image, ImageSequence

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "docs" / "anim" / "bibi_library"
NEW = ROOT / "docs" / "anim"
OUT = ROOT / "site" / "brand" / "bibi"
SIZE = 160
BOX = (28, 52, 468, 492)      # 440×440，中心 x=248、腳底 482 往下留 10px
LIMIT = 60 * 1024
# 個別素材的例外（512 場景座標）：weekend 是比比趴在墊子上＋珍奶，墊子貼著畫面底，統一框會切掉珍奶底與墊子 → 框往下移 18px；
# 左上角那顆裝飾小太陽在網站右下角會漂在互動小圈之間（10-11 監督抓到），擦掉。
OVERRIDE = {
    "weekend": {"box": (19, 74, 459, 514), "erase": [(0, 0, 205, 235)]},
}
# 互動素材開頭的「待機」格剪掉（Andy 10-11 晚：「互動圖不需要前面特效，直接進入互動動作」——
# 點了小圈 0.2 秒內就要看到比比在動；G1 的 ball／eat_grass／pet 第 1 格是 700～900ms 的待機，網站版直接從第 2 格開始）
TRIM_HEAD = {"ball": 1, "eat_grass": 1, "pet": 1}

# 網站用到的才轉（情境待機＋互動動作；對照表在 site/bibi.js 的 MAP）
NAMES = [
    # 情境待機（現有素材庫）
    "wave", "coins", "growth", "magnifier", "fire", "calc", "news", "piggy", "calendar", "bulb", "clock", "star_save", "face_proud",
    # 動畫單位 G1（10-11）：摸摸頭、吃草、玩球、轉圈
    "pet", "eat_grass", "ball", "spin",
    # 動畫單位 G2（10-11）：擊掌、跳舞、抱抱、睡覺循環、叫醒、拍照＋情境待機（大跌安慰、大漲、週末、四款節日帽）
    "highfive", "dance", "hug", "sleep_loop", "wake_once", "selfie",
    "idle_down", "idle_bigup", "weekend", "festival_newyear", "festival_dragon", "festival_moon", "festival_xmas",
    # 10-11 晚 動作編排（bibi.js CHOREO）：跑步替代（素材庫 hop_l／hop_r）＋待機小動作；動畫單位的專屬零件到了就加進來（沒到會印「略過」）
    "hop_l", "hop_r", "face_curious", "tilt",
    "run_l", "run_r", "ball_catch", "eat_grass_v2", "pet_v2", "spin_v2",
    # 10-11 晚 Andy 追加：開心的跳（待機預設）、接過來（給草／給球）、爆米花跳；替代用 face_star
    "face_star", "happy_hop", "receive", "popcorn", "receive_grass", "receive_ball",
]


def src_of(name: str) -> Path | None:
    for p in (LIB / name / "anim.webp", NEW / f"bibi_{name}" / "anim.webp"):   # 現有素材庫優先；新交件的專屬素材在 docs/anim/bibi_<名稱>/
        if p.exists():
            return p
    return None


def encode(frames, durs, q, loop=0):
    buf = io.BytesIO()
    frames[0].save(buf, "WEBP", save_all=True, append_images=frames[1:], duration=durs, loop=loop,
                   quality=q, method=6, lossless=False, allow_mixed=False)
    return buf.getvalue()


def convert(name: str) -> tuple[int, int] | None:
    src = src_of(name)
    if not src:
        return None
    im = Image.open(src)
    frames, durs = [], []
    for f in ImageSequence.Iterator(im):
        fr = f.convert("RGBA")
        # 動畫單位 G1 起的互動素材直接交 160px 全幅（同一個 512 場景座標縮小）：裁切框照比例換算，比比大小才跟其他組一致
        k = fr.size[0] / 512
        ov = OVERRIDE.get(name, {})
        for ex in ov.get("erase", []):
            fr.paste((0, 0, 0, 0), tuple(round(v * k) for v in ex))
        box = tuple(round(v * k) for v in ov.get("box", BOX))
        frames.append(fr.crop(box).resize((SIZE, SIZE), Image.LANCZOS))
        durs.append(int(f.info.get("duration", im.info.get("duration", 100)) or 100))
    cut = TRIM_HEAD.get(name, 0)
    if cut:
        frames, durs = frames[cut:], durs[cut:]
    total = sum(durs)
    loop = int(im.info.get("loop", 0) or 0)   # 互動素材「播一次不循環」（loop=1）要保留：播完停在最後一格＝待機姿勢
    data = None
    for q in (82, 72, 62, 52):
        data = encode(frames, durs, q, loop)
        if len(data) <= LIMIT:
            break
    if len(data) > LIMIT and len(frames) > 6:   # 還是太大：隔格抽掉，總長不變
        frames2 = frames[::2]
        durs2 = [durs[i] + (durs[i + 1] if i + 1 < len(durs) else 0) for i in range(0, len(durs), 2)]
        data = encode(frames2, durs2, 62, loop)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.webp").write_bytes(data)
    return len(data), total


def icons():
    """互動小圈圖示（docs/anim/bibi_icons/*.png，96px）→ site/brand/bibi/icons/*.webp（同尺寸＝42px 小圈的 2 倍螢幕，檔案小一半以上）。"""
    src = NEW / "bibi_icons"
    if not src.exists():
        return
    (OUT / "icons").mkdir(parents=True, exist_ok=True)
    for f in sorted(src.glob("*.png")):
        im = Image.open(f).convert("RGBA")
        im.save(OUT / "icons" / (f.stem + ".webp"), "WEBP", quality=90, method=6)
        print(f"  圖示 {f.stem:10s} {(OUT / 'icons' / (f.stem + '.webp')).stat().st_size / 1024:4.1f} KB")


def props():
    """給草／給球的道具（docs/anim/bibi_receive/*.png，512 場景座標、手從右邊伸進來）→ site/brand/bibi/props/*.webp（256px）。

    除了原樣的「手拿草」「手拿球」，另外拆一張「只有手」：遞到比比肉掌那一格，網頁把手換成空手、東西改由比比的 receive 素材抱著，
    不然手縮回去時會帶著第二根草／第二顆球。拆法：手拿草那張裡，綠／黃（草）＋草旁邊的黑描邊（只取肉掌左緣 x<318 以左）去掉，
    再做一次「開運算」把抗鋸齒殘點清掉（細於 5px 的碎點）。動畫單位交 hand_prop.png 之後可以改用那張。
    """
    import numpy as np
    from PIL import ImageFilter
    src = NEW / "bibi_receive"
    if not (src / "hand_grass_prop.png").exists():
        print("  略過道具（docs/anim/bibi_receive 還沒到）")
        return
    dst = OUT / "props"
    dst.mkdir(parents=True, exist_ok=True)

    def mf(m, r, f):
        return np.array(Image.fromarray((m * 255).astype(np.uint8)).filter(f(r * 2 + 1))) > 127

    for nm in ("hand_grass_prop", "hand_ball_prop", "grass_prop"):
        Image.open(src / f"{nm}.png").convert("RGBA").resize((256, 256), Image.LANCZOS).save(dst / (nm.replace("_prop", "") + ".webp"), "WEBP", quality=90, method=6)
    a = np.array(Image.open(src / "hand_grass_prop.png").convert("RGBA")).astype(int)
    R, G, B, A = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    op = A > 10
    dark = op & (R + G + B < 200)
    xx = np.mgrid[0:A.shape[0], 0:A.shape[1]][1]
    grass = op & ~dark & (G > R - 12) & (G > B + 35)
    grass = grass | (dark & mf(grass, 9, ImageFilter.MaxFilter) & (xx < 318))
    hand = op & ~grass
    hand = hand & mf(mf(mf(hand, 2, ImageFilter.MinFilter), 2, ImageFilter.MaxFilter), 1, ImageFilter.MaxFilter)
    a[..., 3] = np.where(hand, A, 0)
    Image.fromarray(a.astype(np.uint8)).resize((256, 256), Image.LANCZOS).save(dst / "hand.webp", "WEBP", quality=90, method=6)
    for f in sorted(dst.glob("*.webp")):
        print(f"  道具 {f.stem:12s} {f.stat().st_size / 1024:4.1f} KB")


def main(argv):
    if argv == ["icons"]:
        icons()
        return
    if argv == ["props"]:
        props()
        return
    names = argv or NAMES
    ms = {}
    for n in names:
        r = convert(n)
        if r is None:
            print(f"  略過 {n}（素材還沒到）")
            continue
        size, total = r
        ms[n] = total
        print(f"  {n:14s} {size / 1024:5.1f} KB  {total} ms" + ("  ⚠ 超過 60KB" if size > LIMIT else ""))
    print(json.dumps(ms, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
