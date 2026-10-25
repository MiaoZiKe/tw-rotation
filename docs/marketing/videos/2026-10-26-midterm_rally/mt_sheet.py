"""把抽格 PNG 拼成接觸表（每張 6 格＝3 欄×2 列，單格寬 540px，左上角標秒數），評審與人工檢查用。
用法：python mt_sheet.py <輸出資料夾> <png...>"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONT = "/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/font/NotoSansTC-Bold.ttf"


def make(files, out_dir, per=6, cols=3, cw=540, prefix="sheet", start=1):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ch = cw * 16 // 9
    f = ImageFont.truetype(FONT, 30)
    outs = []
    for si in range(0, len(files), per):
        grp = files[si:si + per]
        rows = (len(grp) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * (cw + 6) + 6, rows * (ch + 6) + 6), (90, 90, 90))
        for k, p in enumerate(grp):
            im = Image.open(p).convert("RGB").resize((cw, ch), Image.LANCZOS)
            d = ImageDraw.Draw(im)
            lab = Path(p).stem.split("_")[-1] + "s"
            d.rectangle([0, 0, 120, 40], fill=(0, 0, 0))
            d.text((8, 4), lab, font=f, fill=(255, 255, 0))
            sheet.paste(im, (6 + (k % cols) * (cw + 6), 6 + (k // cols) * (ch + 6)))
        o = out_dir / f"{prefix}_{start + si // per:03d}.png"
        sheet.save(o)
        outs.append(o)
    return outs


if __name__ == "__main__":
    print("\n".join(map(str, make(sys.argv[2:], sys.argv[1]))))
