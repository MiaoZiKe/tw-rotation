"""從比比素材庫挑貼紙 → 裁到本體外框、清掉半透明雜邊 → assets/bibi_*.png。
只用原圖素材（不重畫）。挑選理由寫在 PICK；四腳無手是人工逐張看過的（見 check/sticker_sheet.png）。
"""
import json, os
from PIL import Image, ImageFilter

REPO = "/home/user/tw-rotation/"
HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
PICK = {
    "s01": ("docs/anim/bibi_basepose_1012/png/front_stand_rebuild.png", "興奮", "跳起騰空（站姿整隻上移＋地面影子＋速度線；front_jump 原檔右耳描邊有缺口不用）", "封面：跳起來看曝光機"),
    "s02": ("docs/anim/bibi_library/calendar/key.png", "開心期待", "四腳坐、日曆懸空在頭上", "今天 10/14 財報日"),
    "s03": ("docs/anim/bibi_library/tilt/key.png", "疑惑", "歪頭", "ASML 是誰？"),
    "s04": ("docs/anim/bibi_basepose_1012/png/sniff_r.png", "專心", "低頭嗅地，鼻子沿著流程往右", "跟著製程一步步聞過去"),
    "s05": ("docs/anim/bibi_library/face_shock/key.png", "嚇一跳", "毛炸開、白眼圈", "雷射打錫滴？！"),
    "s06": ("docs/anim/bibi_basepose_1012/png/side_r.png", "認真", "側面站、面向右，放大鏡懸空在身旁（sit_r 原檔右下有一隻脫離的腳不用）", "比較三代光"),
    "s07": ("docs/anim/bibi_library/face_thinking_bulb/key.png", "恍然大悟", "瞇眼點頭、燈泡亮", "想通因果鏈"),
    "s08": ("docs/anim/bibi_library/peek_r/key.png", "好奇", "從右下角探頭", "偷看財報數字"),
    "s09": ("docs/anim/bibi_basepose_1012/png/lie_front.png", "放鬆", "正面趴著", "趴在產業鏈旁邊"),
    "s10": ("docs/anim/bibi_library/face_star/key.png", "超讚", "星星眼", "總結"),
}


def clean(im):
    im = im.convert("RGBA")
    r, g, b, a = im.split()
    # 半透明雜邊：alpha < 60 的像素直接透明；其餘不動（保留描邊抗鋸齒）
    a = a.point(lambda v: 0 if v < 60 else v)
    im = Image.merge("RGBA", (r, g, b, a))
    bb = im.getbbox()
    return im.crop(bb)


if __name__ == "__main__":
    meta = {}
    for k, (src, emo, act, ctx) in PICK.items():
        im = clean(Image.open(REPO + src))
        out = HERE + f"bibi_{k}.png"
        im.save(out)
        meta[k] = dict(src=src, size=im.size, 表情=emo, 動作=act, 情境=ctx)
        print(k, src, im.size)
    json.dump(meta, open(HERE + "stickers.json", "w"), ensure_ascii=False, indent=1)
