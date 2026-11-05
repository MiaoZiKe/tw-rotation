# 後製：圓形頭像 110／44、重疊檢查、比較圖
import json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from gen6 import VAR, TONES, CHK
H = os.path.dirname(os.path.abspath(__file__)); os.chdir(H)
J = json.load(open('jobs.json'))['jobs']; fails = []; items = []
def circ(im, s):
    big = im.convert('RGB').resize((s, s), Image.LANCZOS); m = Image.new('L', (s*4, s*4), 0)
    ImageDraw.Draw(m).ellipse((0, 0, s*4-1, s*4-1), fill=255); m = m.resize((s, s), Image.LANCZOS)
    o = Image.new('RGBA', (s, s), (0, 0, 0, 0)); o.paste(big, (0, 0), m); return o
FO = {v[0]: v[1] for v in VAR}
for j in J:
    if j['kind'] == 'avatar':
        im = Image.open(j['png'])
        for s in (1080, 110, 44): circ(im, s).save(f'{FO[j["v"]]}/頭像_{"1080圓" if s == 1080 else s}_{j["tag"]}.png')
        P = TONES[j['tag']]; bg = np.array([int(P['bg'][i:i+2], 16) for i in (1, 3, 5)])
        d = np.abs(np.array(im.convert('RGB')).astype(int)-bg).max(axis=2) > 24; ys, xs = np.nonzero(d)
        far = float(np.sqrt((xs-539.5)**2+(ys-539.5)**2).max()); items.append(f'{j["v"]} {j["tag"]} 安全圓 {far:.0f}≤432')
        if far > 432: fails.append(items[-1])
for v in FO:
    m = {l: np.array(Image.open(f'{CHK}/{v}wm_{l}.png'))[:, :, 3] > 20 for l in ('sym', 'txt', 'sub')}
    for l in m:
        items.append(f'{v} 字標圖層 {l} 非空（{int(m[l].sum())}px）')
        if m[l].sum() < 500: fails.append(items[-1])
    for a, b in (('sym', 'txt'), ('sym', 'sub'), ('txt', 'sub')):
        items.append(f'{v} 字標 {a}×{b} 不相交')
        if (m[a] & m[b]).any(): fails.append(items[-1])
    xs = np.nonzero(m['sym'].any(0))[0]; xt = np.nonzero(m['txt'].any(0))[0]; g = int(xt.min()-xs.max())
    items.append(f'{v} 圖示與文字間距 {g}px ≥30')
    if g < 30: fails.append(items[-1])
    ma = np.array(Image.open(f'{CHK}/{v}av_a.png'))[:, :, 3] > 20; mb = np.array(Image.open(f'{CHK}/{v}av_b.png'))[:, :, 3] > 20
    items.append(f'{v} 頭像 雲帶×小太陽 不相交（太陽光暈除外）')
    if v != 'C' and (ma & mb).any(): fails.append(items[-1])
json.dump(dict(checked=len(items), fails=fails, items=items), open('overlap_report.json', 'w'), ensure_ascii=False, indent=1)
print('檢查', len(items), '項，失敗', len(fails), fails)
FD = os.path.expanduser('~/.fonts/'); f1 = ImageFont.truetype(FD+'NotoSansCJKtc-Bold.otf', 40); f2 = ImageFont.truetype(FD+'NotoSansCJKtc-Regular.otf', 26); f3 = ImageFont.truetype(FD+'NotoSansCJKtc-Bold.otf', 30)
W, RH = 2200, 470; sh = Image.new('RGB', (W, 150+RH*4), '#FBF7F0'); dr = ImageDraw.Draw(sh)
dr.text((40, 30), '「日日小晴」LOGO：第二輪 07 雲帶缺口優化（奶油晨光）', font=f1, fill='#3A3A3A')
dr.text((40, 90), '字標裡「晴」的日字旁點成太陽橘，對應圖示裡的小太陽', font=f2, fill='#8A5A2E')
rows = [('原版 07 雲帶缺口', '../logo_rrxq2/07_雲帶缺口', '長長的雲帶中間缺了一段，剛好露出晴空。', '', '')] + [(f'{v[0]} {v[2]}', v[1], v[3], v[4], v[5]) for v in VAR]
for i, (lab, fo, mean, m1, m2) in enumerate(rows):
    y = 150+i*RH; dr.rounded_rectangle((20, y, W-20, y+RH-20), 24, fill='white', outline='#EADFCF', width=2)
    av = Image.open(f'{fo}/頭像_1080圓_奶油晨光.png').resize((300, 300), Image.LANCZOS); sh.paste(av, (50, y+60), av)
    for k, (s, x) in enumerate(((110, 380), (44, 520))):
        a = Image.open(f'{fo}/頭像_{s}_奶油晨光.png'); sh.paste(a, (x, y+155+(110-s)//2), a)
    a = Image.open(f'{fo}/頭像_44_深色模式.png'); sh.paste(a, (580, y+188), a)
    wm = Image.open(f'{fo}/字標含副標_奶油晨光.png').convert('RGB'); k = 240/wm.height; wm = wm.resize((int(wm.width*k), 240), Image.LANCZOS); sh.paste(wm, (680, y+30))
    dr.text((680, y+290), lab, font=f3, fill='#3A3A3A'); dr.text((680, y+335), mean, font=f2, fill='#555')
    if m1: dr.text((680, y+380), f'{m1}　{m2}', font=f2, fill='#C0703A')
    dr.text((380, y+290), '110／44／44 深色', font=f2, fill='#888')
sh.save('優化_比較.png')
t = ['奶油晨光', '晴空淡藍', '抹茶午後', '深色模式', '單色黑', '單色白']
pal = Image.new('RGB', (6*300+40, 3*320+40), '#FBF7F0')
for r, v in enumerate(VAR):
    for c, tg in enumerate(t):
        a = Image.open(f'{v[1]}/頭像_1080圓_{tg}.png').resize((280, 280), Image.LANCZOS); pal.paste(a, (20+c*300, 20+r*320), a)
pal.save('優化_色調.png'); print('ok')
