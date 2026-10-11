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
      python scripts/anim/bibi_site.py default_idle   # Andy 指定的 Default 待機（圖三，單張）
      python scripts/anim/bibi_site.py idle_hop       # ★ 待機（唯一一款）：第一版客服鈕的 8 格跳躍 GIF，一直循環（Andy 10-12）
      python scripts/anim/bibi_site.py jump           # （10-12 起不再用在待機）圖二 docs/anim/jump
      python scripts/anim/bibi_site.py props      # 給草／給球的手與道具（site/brand/bibi/props/；含拆出來的「空手」）
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
TRIM_HEAD = {"ball": 1, "eat_grass": 1, "pet": 1}   # （G1 舊素材用；新素材第 1 格就是動作，不用剪）
# 骨架版（bibi_rig.py）素材的比比是「原版 Default 參考圖」的原尺寸（描邊寬 384、腳底 y=488），比素材庫大 1.34 倍 →
# 以腳底為準縮 0.745、對到素材庫的位置（中心 x=247.5、腳底 481），換圖時才不會忽大忽小（10-11 晚量的：happy_hop 第 1 格 vs wave 第 1 格）
RIG_FIT = (0.745, 248, 488, 247.5, 481)
RIG_NAMES = {"happy_hop", "receive", "receive_grass", "receive_ball",
             # 10-11 深夜動畫單位全部照原版造型重畫的互動（舊 G1／G2 改名 *_old 保留）：同一套骨架尺寸，一樣要縮
             "eat_grass_v2", "ball_catch", "ball_catch_l", "popcorn", "pet_v2", "spin_v2",
             "highfive", "dance", "hug", "wake_once", "selfie", "sleep_loop",
             "run_r", "run_l", "run_start_r", "run_stop_r", "hit", "cry", "dizzy"}

# 網站用到的才轉（情境待機＋互動動作；對照表在 site/bibi.js 的 MAP）
NAMES = [
    # 情境待機（現有素材庫）
    "wave", "coins", "growth", "magnifier", "fire", "calc", "news", "piggy", "calendar", "bulb", "clock", "star_save", "face_proud",
    # （G1 的 pet／eat_grass／ball／spin 與跑步替代 hop_l／hop_r 已由 10-11 深夜的原版造型新素材取代，不再轉）
    # 動畫單位 G2（10-11）：擊掌、跳舞、抱抱、睡覺循環、叫醒、拍照＋情境待機（大跌安慰、大漲、週末、四款節日帽）
    "highfive", "dance", "hug", "sleep_loop", "wake_once", "selfie",
    "idle_down", "idle_bigup", "weekend", "festival_newyear", "festival_dragon", "festival_moon", "festival_xmas",
    # 10-11 晚 動作編排（bibi.js CHOREO）：跑步替代（素材庫 hop_l／hop_r）＋待機小動作；動畫單位的專屬零件到了就加進來（沒到會印「略過」）
    "face_curious", "tilt",
    "hit", "cry", "dizzy",   # 打他（被敲，播一次）／哭哭（循環）／暈眩（循環，轉圈播完接）：10-11 深夜到貨
    # 10-11 深夜：動畫單位照原版造型重畫的互動全到（擊掌／跳舞／抱抱／睡覺／叫醒／拍照也換成新版，同名覆蓋）
    "run_l", "run_r", "run_start_r", "run_stop_r", "ball_catch", "ball_catch_l", "eat_grass_v2", "pet_v2", "spin_v2", "popcorn",
    # 10-11 晚 Andy 追加：開心的跳（待機預設）、接過來（給草／給球）、爆米花跳；替代用 face_star
    # 骨架第 1 組（10-11 第一版造型偏離原版被 Andy 退件；照原版 Default 重做後 CEO 對照過）：互動「接東西」可以接。
    # ⚠ happy_hop 不轉：Andy「使用圖2 圖3 GIF圖片就好」→ 待機用 default_idle＋jump（各自的子指令），骨架版只在互動用
    "face_star", "receive", "receive_grass", "receive_ball",
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
        if name in RIG_NAMES:
            sc_, x0, y0, x1, y1 = RIG_FIT
            big = fr.resize((round(fr.size[0] * sc_), round(fr.size[1] * sc_)), Image.LANCZOS)
            canvas = Image.new("RGBA", fr.size, (0, 0, 0, 0))
            canvas.alpha_composite(big, (round((x1 - x0 * sc_) * k), round((y1 - y0 * sc_) * k)))
            fr = canvas
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
    extra = [NEW / "bibi_popcorn" / "popcorn_icon.png"]   # 爆米花小圈圖示跟著 popcorn 素材交（10-11 深夜）
    for f in sorted(src.glob("*.png")) + [e for e in extra if e.exists()]:
        im = Image.open(f).convert("RGBA")
        stem = f.stem.replace("_icon", "")
        im.save(OUT / "icons" / (stem + ".webp"), "WEBP", quality=90, method=6)
        print(f"  圖示 {stem:10s} {(OUT / 'icons' / (stem + '.webp')).stat().st_size / 1024:4.1f} KB")


def props():
    """道具（從被點的小圈飛到比比面前）→ site/brand/bibi/props/ball.webp、grass.webp（裁到東西本身、長邊 128px）。

    Andy 10-11：「伸出去的手太奇怪了，需要修正」→ hand_*_prop.png 一律不用，改成道具自己飛過去。
    來源：docs/anim/bibi_ball_catch/ball_prop.png、docs/anim/bibi_eat_grass_v2/grass_prop.png（512 畫布、透明）。
    """
    dst = OUT / "props"
    dst.mkdir(parents=True, exist_ok=True)
    for f in dst.glob("hand*.webp"):          # 舊版的手（10-11 晚用過）一律清掉
        f.unlink()
    for name, src in (("ball", NEW / "bibi_ball_catch" / "ball_prop.png"), ("grass", NEW / "bibi_eat_grass_v2" / "grass_prop.png"),
                      ("hammer", NEW / "bibi_hit" / "hammer_prop.png")):
        if not src.exists():
            print(f"  略過道具 {name}（{src} 還沒到）")
            continue
        im = Image.open(src).convert("RGBA")
        im = im.crop(im.getbbox())
        k = 128 / max(im.size)
        im = im.resize((max(1, round(im.size[0] * k)), max(1, round(im.size[1] * k))), Image.LANCZOS)
        im.save(dst / f"{name}.webp", "WEBP", quality=90, method=6)
        print(f"  道具 {name:6s} {im.size[0]}×{im.size[1]}  {(dst / f'{name}.webp').stat().st_size / 1024:4.1f} KB")

def _fit_original(fr):
    """原版造型（default_idle_1011／jump 都是同一個座標：描邊寬 385、中心 x=253.5、腳底 y=483）→ 素材庫場景座標
    （寬 287、中心 247.5、腳底 481；縮 0.745）→ 同一個裁切框縮成 160px。跟其他情境款大小、腳底一致，換圖不會忽大忽小。"""
    s = 0.745
    big = fr.resize((round(fr.size[0] * s), round(fr.size[1] * s)), Image.LANCZOS)
    scene = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    scene.alpha_composite(big, (round(247.5 - 253.5 * s), round(481 - 483 * s)))
    return scene.crop(BOX).resize((SIZE, SIZE), Image.LANCZOS)


def default_idle():
    """Andy 10-11 指定的 Default 待機（圖三：docs/anim/bibi_library/reference/default_idle_1011.webp，單張、米色底 RGB）→ site/brand/bibi/default_idle.webp。

    Andy：「請參考原本的圖三作為 Default，大部分時間都是那樣子」「不對，使用圖2 圖3 GIF圖片就好」。
    去背用動畫單位的 gif_pipeline.cutout（深色描邊補縫後從四邊灌水、連地上淡影子一起吃掉、不加陰影），再對齊素材庫座標。
    """
    import numpy as np
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from gif_pipeline import cutout
    src = LIB / "reference" / "default_idle_1011.webp"
    if not src.exists():
        print("  略過 default_idle（參考圖還沒到）")
        return
    rgb = np.asarray(Image.open(src).convert("RGB"))
    al = cutout(rgb)
    fr = _fit_original(Image.fromarray(np.dstack([rgb, al]), "RGBA"))
    OUT.mkdir(parents=True, exist_ok=True)
    fr.save(OUT / "default_idle.webp", "WEBP", quality=88, method=6)
    print(f"  default_idle  {(OUT / 'default_idle.webp').stat().st_size / 1024:5.1f} KB（單張）")


def idle_hop(sheet_dir: str | None = None):
    """比比的待機（唯一一款）：Andy 最早給的 8 格跳躍 GIF（site/brand/src/support_anim_1009.gif，第一版客服鈕 sup-anim-128.gif 的來源）
    → site/brand/bibi/idle_hop.webp（160px 透明動態 WebP、無限循環）＋ idle_hop_still.webp（第 1 格靜態，減少動態偏好用）。

    Andy 10-12：「比比改成一直跳，但是是在主畫面狀態，我說的狀態就是第一版做出來的樣式，一直處於跳的狀態…『跳跳』小圓 拿掉」＋「是這張喔」
    （附的 9 格分格圖＝站好 → 微蹲 → 壓扁 ^^ → 壓扁 >< → 起跳左傾 → 最高點右傾 → 往下掉 → 落地壓扁 → 站好，就是這支 GIF 的 8 格再回第 1 格）。
    去背走動畫單位的 gif_pipeline（load_frames＋cutout：在沒裁切的 512 原圖上補縫灌水、吃掉地上淡影子、不加陰影）。
    這支 GIF 第 1 格跟原版 Default（default_idle_1011）同一個座標（描邊 x 61～446、腳底 484，10-12 量過），
    所以直接用 _fit_original 對到素材庫場景座標 → 大小、腳底跟所有互動素材一致，互動播完切回待機不會忽大忽小。"""
    import numpy as np
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from gif_pipeline import load_frames, cutout, sheet
    src = ROOT / "site" / "brand" / "src" / "support_anim_1009.gif"
    frames, durs = [], []
    for rgb, d in load_frames(str(src)):
        frames.append(_fit_original(Image.fromarray(np.dstack([rgb, cutout(rgb)]), "RGBA")))
        durs.append(int(d))
    data = None
    for q in (86, 80, 72, 62):
        data = encode(frames, durs, q, 0)   # loop=0＝無限循環
        if len(data) <= LIMIT:
            break
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "idle_hop.webp").write_bytes(data)
    frames[0].save(OUT / "idle_hop_still.webp", "WEBP", quality=88, method=6)
    if sheet_dir:
        Path(sheet_dir).mkdir(parents=True, exist_ok=True)
        sheet(frames, Path(sheet_dir) / "sheet_idle_hop.png")
    print(f"  idle_hop      {len(data) / 1024:5.1f} KB  {len(frames)} 格  {sum(durs)} ms（＋ idle_hop_still 第 1 格）")


def jump():
    """Andy 10-11 圖二：docs/anim/jump/animation.gif（24 格跳躍、每格 50ms、每格本身就帶透明）→ site/brand/bibi/jump.webp（播一次）。
    網站的 Default 待機＝default_idle 靜止幾秒 → 播一次 jump → 回 default（bibi.js 的 hopLoop）。超過 60KB 就隔格抽掉（總長不變）。"""
    src = NEW / "jump" / "animation.gif"
    if not src.exists():
        print("  略過 jump（docs/anim/jump 還沒到）")
        return
    im = Image.open(src)
    frames, durs = [], []
    for f in ImageSequence.Iterator(im):
        frames.append(_fit_original(f.convert("RGBA")))
        durs.append(int(f.info.get("duration", 50) or 50))
    data = None
    for step in (1, 2, 3):
        fs = frames[::step]
        ds = [sum(durs[i:i + step]) for i in range(0, len(durs), step)]
        for q in (82, 72, 62):
            data = encode(fs, ds, q, 0)   # 循環：Andy 10-11「Default 改成一直跳」
            if len(data) <= LIMIT:
                break
        if len(data) <= LIMIT:
            break
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "jump.webp").write_bytes(data)
    print(f"  jump          {len(data) / 1024:5.1f} KB  {len(fs)} 格  {sum(ds)} ms")


def main(argv):
    if argv == ["icons"]:
        icons()
        return
    if argv == ["props"]:
        props()
        return
    if argv == ["default_idle"]:
        default_idle()
        return
    if argv == ["jump"]:
        jump()
        return
    if argv == ["idle_hop"]:
        idle_hop()
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
