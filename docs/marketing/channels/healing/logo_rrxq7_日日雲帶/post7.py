# 後製：圓形頭像 110／44、重疊檢查、總覽、可讀性、色調
import json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from gen7 import VAR, TONES, CHK
H = os.path.dirname(os.path.abspath(__file__)); os.chdir(H)
J = json.load(open('jobs.json'))['jobs']; fails = []; items = []
FO = {v[0]: v[1] for v in VAR}
def circ(im, s):
    big = im.convert('RGB').resize((s, s), Image.LANCZOS); m = Image.new('L', (s*4, s*4), 0)
    ImageDraw.Draw(m).ellipse((0, 0, s*4-1, s*4-1), fill=255); m = m.resize((s, s), Image.LANCZOS)
    o = Image.new('RGBA', (s, s), (0, 0, 0, 0)); o.paste(big, (0, 0), m); return o
for j in J:
    if j['kind'] == 'avatar':
        im = Image.open(j['png'])
        for s in (1080, 110, 44): circ(im, s).save(f'{FO[j["n"]]}/頭像_{"1080圓" if s == 1080 else s}_{j["tag"]}.png')
        P = TONES[j['tag']]; bg = np.array([int(P['bg'][i:i+2], 16) for i in (1, 3, 5)])
        d = np.abs(np.array(im.convert('RGB')).astype(int)-bg).max(axis=2) > 24; ys, xs = np.nonzero(d)
        far = float(np.sqrt((xs-539.5)**2+(ys-539.5)**2).max()); items.append(f'{j["n"]} {j["tag"]} 安全圓 {far:.0f}≤432')
        if far > 432: fails.append(items[-1])
for n in FO:
    m = {l: np.array(Image.open(f'{CHK}/{n}wm_{l}.png'))[:, :, 3] > 20 for l in ('sym', 'txt', 'sub')}
    for l in m:
        items.append(f'{n} 字標圖層 {l} 非空（{int(m[l].sum())}px）')
        if m[l].sum() < 500: fails.append(items[-1])
    for a, b in (('sym', 'txt'), ('sym', 'sub'), ('txt', 'sub')):
        items.append(f'{n} 字標 {a}×{b} 不相交')
        if (m[a] & m[b]).any(): fails.append(items[-1])
    xs = np.nonzero(m['sym'].any(0))[0]; xt = np.nonzero(m['txt'].any(0))[0]; g = int(xt.min()-xs.max())
    items.append(f'{n} 圖示與文字間距 {g}px ≥30')
    if g < 30: fails.append(items[-1])
json.dump(dict(checked=len(items), fails=fails, items=items), open('overlap_report.json', 'w'), ensure_ascii=False, indent=1)
print('檢查', len(items), '項，失敗', len(fails), fails)
FD = os.path.expanduser('~/.fonts/'); F = lambda s, b=False: ImageFont.truetype(FD+('NotoSansCJKtc-Bold.otf' if b else 'NotoSansCJKtc-Regular.otf'), s)
def wrap(t, f, w, dr):
    out, cur = [], ''
    for ch in t:
        if dr.textlength(cur+ch, font=f) > w: out.append(cur); cur = ch
        else: cur += ch
    return out + [cur]
CW, CH = 540, 760; cols = 4; sh = Image.new('RGB', (cols*CW+40, 150+3*CH), '#FBF7F0'); dr = ImageDraw.Draw(sh)
dr.text((30, 26), '「日日小晴」LOGO：B 日日雲帶的 12 種變化（奶油晨光）', font=F(42, True), fill='#3A3A3A')
dr.text((30, 88), '共同骨架：兩個「日」＝日日，今天那格露出小太陽＝小晴；字標「晴」的日字旁點成橘色', font=F(26), fill='#8A5A2E')
for i, (n, fo, nm, mean, _) in enumerate(VAR):
    x = 20+(i % cols)*CW; y = 140+(i//cols)*CH
    dr.rounded_rectangle((x, y, x+CW-20, y+CH-20), 22, fill='white', outline='#EADFCF', width=2)
    av = Image.open(f'{fo}/頭像_1080圓_奶油晨光.png').resize((300, 300), Image.LANCZOS); sh.paste(av, (x+20, y+20), av)
    for k, t in enumerate(('晴空淡藍', '深色模式')):
        a = Image.open(f'{fo}/頭像_110_{t}.png').resize((96, 96), Image.LANCZOS); sh.paste(a, (x+340, y+30+k*110), a)
    a = Image.open(f'{fo}/頭像_44_奶油晨光.png'); sh.paste(a, (x+366, y+255), a)
    wm = Image.open(f'{fo}/字標含副標_奶油晨光.png').convert('RGB'); k = (CW-60)/wm.width; wm = wm.resize((CW-60, int(wm.height*k)), Image.LANCZOS); sh.paste(wm, (x+20, y+340))
    yy = y+350+wm.height; dr.text((x+20, yy), f'{n:02d}　{nm}', font=F(34, True), fill='#3A3A3A')
    for li, line in enumerate(wrap(mean, F(24), CW-70, dr)): dr.text((x+20, yy+52+li*34), line, font=F(24), fill='#555')
sh.save('contact_sheet_rrxq7.png')
t = ['奶油晨光', '晴空淡藍', '抹茶午後', '深色模式', '單色黑', '單色白']
rd = Image.new('RGB', (260+len(t)*180, 120+12*130), '#F4F4F4'); d2 = ImageDraw.Draw(rd)
d2.text((20, 30), '可讀性：110px 與 44px 實際大小', font=F(34, True), fill='#333')
for c, tg in enumerate(t): d2.text((260+c*180, 80), tg, font=F(22), fill='#555')
for r, (n, fo, nm, _, _) in enumerate(VAR):
    y = 120+r*130; d2.text((20, y+40), f'{n:02d} {nm}', font=F(26), fill='#333')
    for c, tg in enumerate(t):
        a = Image.open(f'{fo}/頭像_110_{tg}.png'); rd.paste(a, (260+c*180, y), a); b = Image.open(f'{fo}/頭像_44_{tg}.png'); rd.paste(b, (380+c*180, y+33), b)
rd.save('可讀性_rrxq7_110_44.png')
pal = Image.new('RGB', (6*230+40, 12*230+40), '#FBF7F0')
for r, v in enumerate(VAR):
    for c, tg in enumerate(t):
        a = Image.open(f'{v[1]}/頭像_1080圓_{tg}.png').resize((210, 210), Image.LANCZOS); pal.paste(a, (20+c*230, 20+r*230), a)
pal.save('palette_rrxq7.png'); print('ok')
