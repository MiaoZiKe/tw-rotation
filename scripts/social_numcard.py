"""主題文章第二張圖「鉤子＋重點數字卡」（2026-11-01 Andy：「IG Thread 上面也需要進行優化 讓熱度提升，
並且 盡量不要千篇一律的方式要有點變化」；Threads 規則「配圖只能 0 或 2 張」）。

主題文章原本只有 1 張實景封面 → Threads 不准 1 張、IG 單圖觸及低 → 補這張變 2 張輪播：
  第 1 張：原本的實景照片封面（不動，照片審核規則照舊）
  第 2 張：這張（純排版、不用照片、不用 AI 圖）：鉤子大字＋最多 3 個重點數字
版型 3 套輪替（依日期＋時段），避免每篇長一樣：
  hook_top   鉤子置頂、數字逐列
  hero_top   大數字置頂、鉤子在下
  grid       鉤子置頂、數字兩欄方塊
色票照 post_design_system.md（亮色 HUD）；圖上不放網址、資料來源、免責（andy_ui_rules 第 18 條）。
每個文字框兩兩不重疊、都在安全邊距內，程式檢查；放不下就縮字、少一列，回傳重疊筆數（>0 呼叫端不用這張）。
"""
from __future__ import annotations

import glob
import os
from pathlib import Path

W, H = 1080, 1350
M = 72                                 # 安全邊距（比 post_design_system 的 40 寬，數字卡留白多一點）
C = dict(bg="#E8EFF5", card="#F8FBFD", line="#CFDDE8", ink="#0A1B2A", ink2="#2C4559", ink3="#4A6377",
         accent="#0A6A86", br=(10, 106, 134), rise="#C4142F", fall="#07784E")
LAYOUTS = ("hook_top", "hero_top", "grid")
NO_HEAD = "，。、！？…」』）；：,.!?)%"
FONT_CANDS = [os.environ.get("SOCIAL_FONT_BOLD", ""),
              str(Path.home() / ".local/share/fonts/tw-rotation/NotoSansCJKtc-Bold.otf"),
              *glob.glob("/usr/share/fonts/**/NotoSansCJK*-Bold.*", recursive=True),
              *glob.glob("/usr/share/fonts/**/NotoSansTC*Bold*.ttf", recursive=True),
              *glob.glob(str(Path(__file__).resolve().parents[1] / "docs/**/NotoSans*TC*Bold*.[ot]tf"), recursive=True),
              "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"]


def font_path() -> str:
    for p in FONT_CANDS:
        if p and Path(p).exists():
            return p
    raise FileNotFoundError("找不到中文字型（Noto Sans CJK TC Bold）")


def layout_for(day: str, slot: str) -> str:
    n = sum(map(ord, f"{day}{slot}"))
    return LAYOUTS[n % 3]


def _wrap(draw, text, font, width, max_lines):
    lines, cur = [], ""
    for ch in text:
        if draw.textlength(cur + ch, font=font) > width and cur:
            lines.append(cur); cur = ch
            if len(lines) >= max_lines:
                return None
        else:
            cur += ch
    if cur:
        lines.append(cur)
    for i in range(1, len(lines)):           # 避頭點：行首不放標點，把上一行最後一個字帶下來
        while lines[i] and lines[i][0] in NO_HEAD and len(lines[i - 1]) > 1:
            lines[i] = lines[i - 1][-1] + lines[i]
            lines[i - 1] = lines[i - 1][:-1]
    if any(draw.textlength(l, font=font) > width for l in lines):
        return None
    return lines if len(lines) <= max_lines else None


def _overlaps(boxes):
    bad = []
    for i in range(len(boxes)):
        a = boxes[i][1]
        if a[0] < M - 1 or a[1] < M - 1 or a[2] > W - M + 1 or a[3] > H - M + 1:
            bad.append(f"{boxes[i][0]} 超出安全邊距")
        for j in range(i + 1, len(boxes)):
            b = boxes[j][1]
            if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                bad.append(f"{boxes[i][0]} 與 {boxes[j][0]} 重疊")
    return bad


def render(out: str | Path, hook: str, rows: list[dict], label: str = "", date_md: str = "", layout: str = "hook_top") -> dict:
    """畫一張 1080×1350；rows=[{label,value,unit}]。回傳 {path, layout, bad:[...]}。"""
    from PIL import Image, ImageDraw, ImageFont
    fp = font_path()
    F = lambda s: ImageFont.truetype(fp, s)  # noqa: E731
    img = Image.new("RGB", (W, H), C["bg"])
    d = ImageDraw.Draw(img)
    for x in range(0, W, 32):                 # HUD 細格線
        d.line([(x, 0), (x, H)], fill="#E1EAF1")
    for y in range(0, H, 32):
        d.line([(0, y), (W, y)], fill="#E1EAF1")
    d.rounded_rectangle([M - 24, M - 24, W - M + 24, H - M + 24], 10, fill=C["card"], outline=C["line"], width=2)
    for (x, y, sx, sy) in ((M - 24, M - 24, 1, 1), (W - M + 24, M - 24, -1, 1), (M - 24, H - M + 24, 1, -1), (W - M + 24, H - M + 24, -1, -1)):
        d.line([(x, y), (x + 30 * sx, y)], fill=C["br"], width=5); d.line([(x, y), (x, y + 30 * sy)], fill=C["br"], width=5)
    boxes = []
    inner = W - 2 * M
    y = M + 8
    if label:                                  # 頂部小標（類別｜主體）
        f = F(38)
        t = label[:24]
        d.rectangle([M, y + 4, M + 8, y + 46], fill=C["accent"])
        d.text((M + 24, y), t, font=f, fill=C["accent"])
        boxes.append(("小標", (M, y, M + 24 + d.textlength(t, font=f), y + 50)))
        if date_md:
            fw = d.textlength(date_md, font=f)
            d.text((W - M - fw, y), date_md, font=f, fill=C["ink3"])
            boxes.append(("日期", (W - M - fw, y, W - M, y + 50)))
        y += 90

    def draw_hook(y, size=66, max_lines=5):
        for s in (size, 60, 54, 48):
            f = F(s)
            ls = _wrap(d, hook, f, inner, max_lines)
            if ls:
                lh = int(s * 1.42)
                for i, l in enumerate(ls):
                    d.text((M, y + i * lh), l, font=f, fill=C["ink"])
                boxes.append(("鉤子", (M, y, M + inner, y + lh * len(ls))))
                return y + lh * len(ls) + 40
        return y

    def draw_hero(y):
        if not rows:
            return y
        r = rows[0]
        v = f"{r.get('value', '')}{r.get('unit', '')}"
        for s in (180, 150, 120, 96):
            f = F(s)
            if d.textlength(v, font=f) <= inner:
                d.text((M, y), v, font=f, fill=C["accent"])
                boxes.append(("大數字", (M, y, M + d.textlength(v, font=f), y + int(s * 1.25))))
                y += int(s * 1.25) + 6
                fl = F(42)
                lab = str(r.get("label", ""))[:20]
                d.text((M, y), lab, font=fl, fill=C["ink2"])
                boxes.append(("大數字標籤", (M, y, M + d.textlength(lab, font=fl), y + 56)))
                return y + 90
        return y

    def draw_rows(y, rs):
        if not rs:
            return y
        # 列高依剩下的空間平均分（160～250），避免卡片下半部大片留白（andy_ui_rules：留白是退件項）
        rh = int(max(160, min(250, (H - M - y) / len(rs))))
        fl, fv = F(40 if rh < 200 else 46), F(64 if rh < 200 else 84)
        for i, r in enumerate(rs):
            if y + 150 > H - M:
                break
            lab = str(r.get("label", ""))[:18]
            v = f"{r.get('value', '')}{r.get('unit', '')}"
            d.line([(M, y), (W - M, y)], fill=C["line"], width=2)
            d.text((M, y + 18), lab, font=fl, fill=C["ink2"])
            boxes.append((f"列{i + 1}標籤", (M, y + 18, M + d.textlength(lab, font=fl), y + 72)))
            vw = d.textlength(v, font=fv)
            if vw > inner:
                continue
            vy = y + rh - int(fv.size * 1.25) - 6
            d.text((W - M - vw, vy), v, font=fv, fill=C["accent"])
            boxes.append((f"列{i + 1}數字", (W - M - vw, max(vy + 10, y + 74), W - M, y + rh - 4)))
            y += rh
        return y

    def draw_grid(y, rs):
        gap = 28
        cw = (inner - gap) // 2
        nrow = (min(len(rs), 4) + 1) // 2 or 1
        th = int(max(190, min(320, (H - M - y - gap * (nrow - 1)) / nrow)))
        fl, fv = F(36), F(64 if th > 240 else 56)
        for i, r in enumerate(rs[:4]):
            cx = M + (i % 2) * (cw + gap)
            cy = y + (i // 2) * (th + gap)
            if cy + th > H - M:
                break
            if len(rs) % 2 == 1 and i == len(rs) - 1:     # 單數：最後一格拉滿整列，不留半格空白
                cw2 = inner
            else:
                cw2 = cw
            d.rounded_rectangle([cx, cy, cx + cw2, cy + th], 10, fill="#EEF4F8", outline=C["line"], width=2)
            lab = str(r.get("label", ""))[:10]
            v = f"{r.get('value', '')}{r.get('unit', '')}"
            while d.textlength(v, font=fv) > cw2 - 48 and fv.size > 32:
                fv = F(fv.size - 4)
            while d.textlength(lab, font=fl) > cw2 - 48 and len(lab) > 2:
                lab = lab[:-1]
            d.text((cx + 24, cy + 24), lab, font=fl, fill=C["ink2"])
            d.text((cx + 24, cy + th - int(fv.size * 1.3) - 20), v, font=fv, fill=C["accent"])
            boxes.append((f"格{i + 1}", (cx, cy, cx + cw2, cy + th)))
        return y + (th + gap) * nrow

    rows = [r for r in rows if str(r.get("value", "")).strip()][:3]
    if layout == "grid" and len(rows) < 3:          # 兩格以下的方塊排不滿，改逐列（不留大片空白）
        layout = "hook_top"
    if layout == "hero_top" and len(rows) < 2:
        layout = "hook_top"
    if layout == "hero_top":
        y = draw_hero(y)
        y = draw_hook(y, 56, 4)
        draw_rows(y, rows[1:])
    elif layout == "grid":
        y = draw_hook(y)
        draw_grid(y + 10, rows)
    else:
        y = draw_hook(y)
        draw_rows(y + 10, rows)
    bad = _overlaps(boxes)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=92)
    return dict(path=str(out), layout=layout, bad=bad, boxes=len(boxes))
