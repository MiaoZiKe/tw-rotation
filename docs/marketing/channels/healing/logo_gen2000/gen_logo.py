# 2000 後頻道 LOGO：4 名稱 × 2 方向。純向量自繪（不用 AI 圖、不用吉祥物）。
# 用法：python3 gen_logo.py（產 SVG 與 jobs.json）→ node render.js（出 PNG 與外框）→ python3 compose.py（圓形、總覽、示意、檢查）
import json, os
from PIL import ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
SERIF_BOLD = os.path.expanduser('~/.fonts/NotoSerifCJKtc-Bold.otf')
SER = "'Noto Serif CJK TC',serif"
SW = 9  # 符號線寬（單位座標；頭像放大 3.0 倍＝1080 圖上約 27px）
# 三種底色：bg 底、ink 字標、line 線條、lamp 燈（與樣張一致）
PAL = {
 '④霧紫灰': dict(bg='#4A4454', ink='#F3EFF5', line='#ABA0B5', lamp='#E9CF9E'),
 '⑤水泥暖灰': dict(bg='#56524D', ink='#F4F0EA', line='#B9B1A6', lamp='#E9CF9E'),
 '①灰藍夜': dict(bg='#3B4553', ink='#F1F3F6', line='#A9B6C6', lamp='#E9CF9E'),
 '單色白': dict(bg='#000000', ink='#FFFFFF', line='#FFFFFF', lamp='#FFFFFF'),
 '單色黑': dict(bg='#FFFFFF', ink='#000000', line='#000000', lamp='#000000'),
}
LOGOS = [  # (代號, 名稱, 方向名, 概念一句)
 ('1a', '薪水追不上', '進度條', '兩條進度條，上面那條帶著一盞燈跑在前面，下面那條停在半路、後段只剩虛線。'),
 ('1b', '薪水追不上', '月曆發薪日', '一張細線月曆，格子都是暗點，只有一格亮成燈：發薪日。'),
 ('2a', '慢慢來，我們的版本', '半開的窗', '一扇窗拉開一半，關著的那一格亮著燈：不趕、先留一點光。'),
 ('2b', '慢慢來，我們的版本', '彎路與燈', '一條不走直線的小路慢慢彎向遠處的一盞燈：每個人的路徑不同。'),
 ('3a', '租屋日記 2000 後', '鑰匙', '一把細線鑰匙，鑰匙圈裡是一盞燈：租來的家裡，燈是自己留的。'),
 ('3b', '租屋日記 2000 後', '門牌與門', '一扇拱門，門把是燈，上方一塊小門牌：租屋的門口。'),
 ('4a', '我們這一代', '一排小窗', '三乘三的小窗，只有一扇亮著：很多人在各自的格子裡。'),
 ('4b', '我們這一代', '落地燈', '地平線上一盞落地燈，對應樣張「無人場景＋一盞燈」的語彙。'),
]
def sym(k, c):
    L = f'fill="none" stroke="{c["line"]}" stroke-width="{SW}" stroke-linecap="round" stroke-linejoin="round"'
    P = f'fill="{c["lamp"]}"'
    if k == '1a':
        return (f'<path d="M-90 -34 H64" {L}/><circle cx="90" cy="-34" r="13" {P}/>'
                f'<path d="M-90 34 H-14" {L}/><path d="M26 34 H90" fill="none" stroke="{c["line"]}" stroke-width="{SW}" stroke-linecap="round" stroke-dasharray="0.1 22" opacity=".6"/>')
    if k == '1b':
        dots = ''.join(f'<circle cx="{x}" cy="{y}" r="8" fill="{c["line"]}" opacity=".55"/>' for x, y in [(-40,10),(0,10),(40,10),(-40,50),(0,50)])
        return (f'<rect x="-80" y="-68" width="160" height="148" rx="16" {L}/><path d="M-80 -28 H80" {L}/>'
                f'<path d="M-38 -88 V-52 M38 -88 V-52" {L}/>{dots}<circle cx="40" cy="50" r="13" {P}/>')
    if k == '2a':
        return (f'<rect x="-88" y="-62" width="176" height="124" rx="8" {L}/><path d="M0 -62 V62" {L}/>'
                f'<path d="M-88 -62 L-48 -46 V46 L-88 62" {L}/><path d="M-100 82 H100" {L}/><circle cx="44" cy="0" r="16" {P}/>')
    if k == '2b':
        return (f'<path d="M-90 62 C-46 62 -52 4 -10 4 C32 4 24 -56 70 -56" {L}/><circle cx="90" cy="-62" r="14" {P}/>'
                f'<circle cx="-90" cy="62" r="6" fill="{c["line"]}"/>')
    if k == '3a':
        return (f'<g transform="rotate(-28)"><circle cx="-46" cy="0" r="38" {L}/><circle cx="-46" cy="0" r="12" {P}/>'
                f'<path d="M-8 0 H92 M62 0 V26 M84 0 V22" {L}/></g>')
    if k == '3b':
        return (f'<rect x="-74" y="-76" width="88" height="166" rx="6" {L}/><circle cx="-8" cy="22" r="11" {P}/>'
                f'<rect x="38" y="-36" width="54" height="34" rx="6" {L}/><path d="M50 -19 H80" {L}/><path d="M-96 90 H96" {L}/>')
    if k == '4a':
        out = ''
        for r in range(3):
            for col in range(3):
                x, y = -56 + 56 * col - 21, -56 + 56 * r - 21
                if (r, col) == (1, 2): out += f'<rect x="{x}" y="{y}" width="42" height="42" rx="7" {P}/>'
                else: out += f'<rect x="{x}" y="{y}" width="42" height="42" rx="7" {L}/>'
        return out
    if k == '4b':
        return (f'<path d="M-36 -84 H36 L56 -24 H-56 Z" fill="{c["lamp"]}" stroke="{c["line"]}" stroke-width="{SW}" stroke-linejoin="round"/>'
                f'<path d="M0 -24 V84" {L}/><path d="M-92 86 H92" {L}/>')
def tw(name, fs):
    f = ImageFont.truetype(SERIF_BOLD, 200)
    return f.getlength(name) * fs / 200 + 0.05 * fs * len(name)
def avatar(k, c):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1080" viewBox="0 0 1080 1080"><rect width="1080" height="1080" fill="{c["bg"]}"/>'
            f'<g id="sym" transform="translate(540 540) scale(3.0)">{sym(k, c)}</g></svg>')
def wordmark(k, name, c, fs, ss, pad, H, transparent=False):
    gap = 0.5 * fs; sx = pad + 105 * ss; tx = pad + 210 * ss + gap
    W = round(tx + tw(name, fs) + pad)
    bg = '' if transparent else f'<rect width="{W}" height="{H}" fill="{c["bg"]}"/>'
    return W, (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{bg}'
               f'<g id="sym" transform="translate({sx:.1f} {H/2}) scale({ss})">{sym(k, c)}</g>'
               f'<text id="nm" x="{tx:.1f}" y="{H/2 + fs*0.36:.1f}" font-family="{SER}" font-size="{fs}" font-weight="700" letter-spacing="{0.05*fs:.1f}" fill="{c["ink"]}">{name}</text></svg>')
jobs = []
for k, name, d, concept in LOGOS:
    folder = f'{k}_{name.replace(" ", "")}_{d}'
    os.makedirs(os.path.join(HERE, folder), exist_ok=True)
    fs = 120 if len(name) <= 5 else 92
    for tag, c in PAL.items():
        p = f'{folder}/{k}_頭像_{tag}'
        open(os.path.join(HERE, p + '.svg'), 'w', encoding='utf-8').write(avatar(k, c))
        jobs.append(dict(svg=p + '.svg', png=p + '.png', w=1080, h=1080, kind='avatar', k=k, tag=tag))
        W, s = wordmark(k, name, c, fs, 1.3, 70, 400)
        p = f'{folder}/{k}_字標_{tag}'
        open(os.path.join(HERE, p + '.svg'), 'w', encoding='utf-8').write(s)
        jobs.append(dict(svg=p + '.svg', png=p + '.png', w=W, h=400, kind='wm', k=k, tag=tag, fs=fs))
    # 配合示意用：④ 色、透明底、小尺寸（符號高約 44px、字 30px）
    W, s = wordmark(k, name, PAL['④霧紫灰'], 30, 0.22, 2, 60, True)
    p = f'{folder}/{k}_字標_封面用_透明'
    open(os.path.join(HERE, p + '.svg'), 'w', encoding='utf-8').write(s)
    jobs.append(dict(svg=p + '.svg', png=p + '.png', w=W, h=60, kind='cover', k=k, tag='封面', fs=30, transparent=True))
json.dump(dict(jobs=jobs, logos=LOGOS, pal=PAL), open(os.path.join(HERE, 'jobs.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(jobs), 'jobs')
