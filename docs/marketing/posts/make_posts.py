"""IG 輪播示意圖（1080x1350）：真實截圖＋大標＋吉祥物 LOGO。輸出到 docs/marketing/posts/。"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path('/home/user/tw-rotation')
import os
SH = Path(os.environ.get('TW_POST_SHOTS', '.'))  # 截圖所在資料夾（先用 scripts/_show.py 拍）
OUT = ROOT / 'docs/marketing/posts'
OUT.mkdir(parents=True, exist_ok=True)
FONT = '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'
LOGO = Image.open(ROOT / 'site/brand/src/logo_1009.jpg').convert('RGB')

W, H = 1080, 1350
BLUE = (34, 150, 230)
SKY = (226, 243, 255)
CREAM = (255, 251, 240)
INK = (28, 40, 58)
SUB = (84, 100, 122)
YEL = (255, 214, 56)
NAVY = (12, 22, 38)
DISC = '本站為公開資料整理與視覺化工具，非投資建議；投資請自行判斷並承擔風險。'
URL = 'miaozike.github.io/tw-rotation'


def F(sz):
    return ImageFont.truetype(FONT, sz)


def text(d, xy, s, sz, fill=INK, bold=True, anchor='la'):
    d.text(xy, s, font=F(sz), fill=fill, anchor=anchor,
           stroke_width=(2 if sz >= 80 else 1 if sz >= 56 else 0) if bold else 0, stroke_fill=fill)


def rounded(im, r):
    m = Image.new('L', im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, im.size[0] - 1, im.size[1] - 1], r, fill=255)
    out = Image.new('RGBA', im.size)
    out.paste(im, (0, 0), m)
    return out


def logo(sz):
    return rounded(LOGO.resize((sz, sz), Image.LANCZOS), int(sz * 0.2))


def footer(cv, d, page, total):
    d.rectangle([0, H - 86, W, H], fill=(245, 248, 252))
    text(d, (48, H - 60), DISC, 22, SUB, bold=False)
    text(d, (W - 48, H - 60), f'{page}/{total}', 24, SUB, anchor='ra')


def header_brand(cv, d):
    cv.paste(logo(84), (48, 40), logo(84))
    text(d, (148, 58), '哩股哩股', 36, INK)
    text(d, (148, 104), '台股資金輪動儀表板', 22, SUB, bold=False)


def cover(name, kicker, title_lines, sub, page, total, chip='註冊會員免費使用'):
    cv = Image.new('RGB', (W, H), SKY)
    d = ImageDraw.Draw(cv)
    # 背景格線（呼應 LOGO 的格子）
    for x in range(0, W, 90):
        d.line([x, 0, x, H], fill=(206, 230, 250), width=2)
    for y in range(0, H, 90):
        d.line([0, y, W, y], fill=(206, 230, 250), width=2)
    header_brand(cv, d)
    # 小標籤
    tw = d.textlength(kicker, font=F(34)) + 56
    d.rounded_rectangle([48, 230, 48 + tw, 290], 30, fill=YEL)
    text(d, (76, 241), kicker, 34, INK)
    y = 330
    for ln in title_lines:
        text(d, (48, y), ln, 92, INK)
        y += 118
    text(d, (52, y + 14), sub, 38, SUB, bold=False)
    # 吉祥物
    lg = logo(470)
    sh = Image.new('RGBA', (510, 510), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([20, 30, 490, 500], 94, fill=(20, 80, 140, 70))
    sh = sh.filter(ImageFilter.GaussianBlur(14))
    cv.paste(sh, (W - 560, H - 640), sh)
    cv.paste(lg, (W - 540, H - 660), lg)
    cw = d.textlength(chip, font=F(30)) + 60
    d.rounded_rectangle([48, H - 250, 48 + cw, H - 186], 32, fill=BLUE)
    text(d, (78, H - 237), chip, 30, (255, 255, 255))
    text(d, (52, H - 150), '左滑看真實畫面 →', 30, BLUE)
    footer(cv, d, page, total)
    cv.save(OUT / name, optimize=True)


def shot(name, src, box, title, caption, notes, page, total):
    cv = Image.new('RGB', (W, H), CREAM)
    d = ImageDraw.Draw(cv)
    cv.paste(logo(64), (48, 40), logo(64))
    text(d, (128, 50), '哩股哩股', 30, INK)
    text(d, (48, 140), title, 60, INK)
    text(d, (50, 226), caption, 32, SUB, bold=False)
    im = Image.open(src).convert('RGB').crop(box)
    maxw, maxh = W - 96, H - 300 - 110 - 40 * len(notes) - 30
    s = min(maxw / im.width, maxh / im.height)
    im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    x = (W - im.width) // 2
    y = 290
    # 外框（假的螢幕邊）
    d.rounded_rectangle([x - 14, y - 14, x + im.width + 14, y + im.height + 14], 26, fill=NAVY)
    cv.paste(rounded(im, 14), (x, y), rounded(im, 14))
    ny = y + im.height + 40
    for n in notes:
        d.ellipse([52, ny + 10, 68, ny + 26], fill=BLUE)
        text(d, (84, ny), n, 30, INK, bold=False)
        ny += 44
    text(d, (W - 48, 62), '真實畫面', 24, BLUE, anchor='ra')
    footer(cv, d, page, total)
    cv.save(OUT / name, optimize=True)


def cta(name, line, page, total):
    cv = Image.new('RGB', (W, H), BLUE)
    d = ImageDraw.Draw(cv)
    lg = logo(380)
    cv.paste(lg, ((W - 380) // 2, 150), lg)
    text(d, (W // 2, 590), '免費註冊，就能每天用', 64, (255, 255, 255), anchor='ma')
    text(d, (W // 2, 690), line, 36, (225, 242, 255), bold=False, anchor='ma')
    d.rounded_rectangle([170, 800, W - 170, 900], 50, fill=YEL)
    text(d, (W // 2, 826), '用 Google 帳號一鍵註冊', 42, INK, anchor='ma')
    text(d, (W // 2, 950), URL, 34, (255, 255, 255), anchor='ma')
    text(d, (W // 2, 1006), '連結在個人檔案（Bio）', 30, (225, 242, 255), bold=False, anchor='ma')
    d.rounded_rectangle([90, 1090, W - 90, 1220], 20, fill=(20, 110, 185))
    text(d, (W // 2, 1112), '不報明牌、不喊單、不保證獲利', 32, (255, 255, 255), anchor='ma')
    text(d, (W // 2, 1162), '我們只把公開資料整理成看得懂的圖', 28, (225, 242, 255), bold=False, anchor='ma')
    footer(cv, d, page, total)
    cv.save(OUT / name, optimize=True)


S = SH
FLOW = S / 'flow-1080.png'
HEAT = S / 'heatmap_industry-1080.png'
SEASON = S / 'season-1080.png'
ETFCAL = S / 'etf_cal-1080.png'

# 輪播 1：錢往哪個族群跑（4 張）
cover('p1_flow_1_cover.png', '每天 5 分鐘', ['今天的錢', '往哪個族群跑？'], '一張圖看懂資金輪動，不用自己翻報表', 1, 4)
shot('p1_flow_2_rotation.png', FLOW, (92, 62, 1062, 1032), '資金輪盤', '每個點是一個族群，看它在四個象限怎麼移動',
     ['領先／改善／轉弱／落後，四格一眼分', '右邊排行：哪些族群資金占比變多、變少', '拉桿可以倒回 20 天前看軌跡'], 2, 4)
shot('p1_flow_3_heatmap.png', HEAT, (92, 60, 1062, 1340), '熱力圖：整個台股一次看', '方塊越大＝成交越多；紅漲綠跌',
     ['依產業鏈分區：半導體、AI 伺服器、傳產…', '哪一塊特別紅、特別綠，一眼就看到'], 3, 4)
cta('p1_flow_4_cta.png', '資金流向、熱力圖、產業地圖，註冊會員都看得到', 4, 4)

# 輪播 2：季節性（3 張）
cover('p2_season_1_cover.png', '歷史統計', ['10 月了，', '哪些族群歷年', '比較有表現？'], '看過去 20 多年的月份規律（不代表未來）', 1, 3)
shot('p2_season_2_table.png', SEASON, (92, 60, 1062, 740), '週期統計：族群 × 月份', '每一格＝該族群在那個月，平均比大盤多或少幾 %',
     ['可切近 3／5／10 年、看勝率', '紅＝歷年平均強於大盤，綠＝弱於大盤', '這是過去的平均，不是對今年的預測'], 2, 3)
cta('p2_season_3_cta.png', '季節性統計，註冊會員每天都能查', 3, 3)

# 輪播 3：ETF 配息行事曆（3 張）
cover('p3_etf_1_cover.png', '存股族必收', ['ETF 哪天除息？', '一張月曆看完'], '除息日、配多少、填息幾天，不用一檔一檔查', 1, 3)
shot('p3_etf_2_calendar.png', ETFCAL, (92, 60, 1062, 985), 'ETF 配息行事曆', '每一天有哪幾檔除息，點月份就能翻',
     ['下方列出配息金額、當次殖利率、發放日', '填息天數自動算，還沒填息的也標出來'], 2, 3)
cta('p3_etf_3_cta.png', 'ETF 配息行事曆，註冊會員免費使用', 3, 3)
print('ok')
