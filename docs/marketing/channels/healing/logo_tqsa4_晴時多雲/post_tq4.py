# 後製：圓形頭像 110／44、重疊與對比檢查、總覽、色系比較
import json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from gen_tq4 import SYMS, TONES, CHK, g
H = os.path.dirname(os.path.abspath(__file__)); os.chdir(H)
J = json.load(open('jobs.json'))['jobs']; fails = []; items = []
FO = {n: v[0] for n, v in SYMS.items()}
def circ(im, s):
    big = im.convert('RGB').resize((s, s), Image.LANCZOS); m = Image.new('L', (s*4, s*4), 0)
    ImageDraw.Draw(m).ellipse((0, 0, s*4-1, s*4-1), fill=255); m = m.resize((s, s), Image.LANCZOS)
    o = Image.new('RGBA', (s, s), (0, 0, 0, 0)); o.paste(big, (0, 0), m); return o
def chk(ok, msg):
    items.append(msg)
    if not ok: fails.append(msg)
A = lambda p: np.array(Image.open(p))[:, :, 3] > 20
def dil(m, px): return np.array(Image.fromarray((m*255).astype('uint8')).filter(ImageFilter.MaxFilter(px*2+1))) > 100
for j in J:
    if j['kind'] != 'avatar': continue
    im = Image.open(j['png']); fo = FO[j['n']]
    for s in (1080, 110, 44): circ(im, s).save(f'{fo}/頭像_{"1080圓" if s == 1080 else s}_{j["tag"]}.png')
    P = TONES[j['tag']]; bg = np.array([int(P['bg'][i:i+2], 16) for i in (1, 3, 5)])
    d = np.abs(np.array(im.convert('RGB')).astype(int)-bg).max(axis=2) > 24; ys, xs = np.nonzero(d)
    far = float(np.sqrt((xs-539.5)**2+(ys-539.5)**2).max()); chk(far <= 432, f'{j["n"]:02d} {j["tag"]} 安全圓 {far:.0f}≤432')
for n in FO:
    a, q = A(f'{CHK}/{n}av_a.png'), A(f'{CHK}/{n}av_q.png')
    chk(a.sum() > 800 and q.sum() > 800, f'{n:02d} 頭像晴、礙圖層非空')
    chk(not (dil(a, 8) & q).any(), f'{n:02d} 頭像晴與礙不相交且間距 ≥8px')
    m = {l: A(f'{CHK}/{n}wm_{l}.png') for l in ('sym', 'txt', 'sub')}
    for l in m: chk(m[l].sum() >= 500, f'{n:02d} 字標圖層 {l} 非空（{int(m[l].sum())}px）')
    for x, y in (('sym', 'txt'), ('sym', 'sub'), ('txt', 'sub')): chk(not (m[x] & m[y]).any(), f'{n:02d} 字標 {x}×{y} 不相交')
    xs = np.nonzero(m['sym'].any(0))[0]; xt = np.nonzero(m['txt'].any(0))[0]; gp = int(xt.min()-xs.max()); chk(gp >= 30, f'{n:02d} 圖文間距 {gp}px ≥30')
CR = []
for tag, P in TONES.items():
    for what, fg in (('晴字', g.tq_text(P)), ('礙字', g.ta_text(P)), ('談說字', P['ink']), ('副標', P['sub'])):
        r = g.ratio(fg, P['bg']); CR.append((tag, what, fg, round(r, 2))); chk(r >= 4.5, f'對比 {tag} {what} {r:.2f}≥4.5')
    for what, fg in (('符號晴', P['q']), ('符號礙', P['a'])):
        r = g.ratio(fg, P['bg']); chk(r >= 3.0, f'符號對比 {tag} {what} {r:.2f}≥3')
json.dump(dict(checked=len(items), fails=fails, items=items, contrast=CR), open('overlap_report.json', 'w'), ensure_ascii=False, indent=1)
print('檢查', len(items), '項，失敗', len(fails), fails)
FD = os.path.expanduser('~/.fonts/'); F = lambda s, b=False: ImageFont.truetype(FD+('NotoSansCJKtc-Bold.otf' if b else 'NotoSansCJKtc-Regular.otf'), s)
# 總覽：10 款（夜版頭像＋44px＋字標）
CW, CH = 1100, 470; sh = Image.new('RGB', (2*CW+60, 160+5*CH), '#EFEAE0'); dr = ImageDraw.Draw(sh)
dr.text((30, 26), '「談晴說礙」LOGO：晴時多雲 10 種變化（夜版）', font=F(44, True), fill='#2F2D2B')
dr.text((30, 96), '以簡約第三輪 07 為底多一點東西；晴＝橘（太陽、光），礙＝雲灰（雲、影子）。色系比較見 色系_tqsa4.png', font=F(26), fill='#6E6A66')
for i, (n, (fo, nm, mean, qd, ad, _)) in enumerate(SYMS.items()):
    x = 20+(i % 2)*(CW+20); y = 150+(i//2)*CH
    dr.rounded_rectangle((x, y, x+CW, y+CH-16), 20, fill='#2B2A2E')
    av = Image.open(f'{fo}/頭像_1080圓_夜版.png').resize((220, 220), Image.LANCZOS); sh.paste(av, (x+24, y+24), av)
    a = Image.open(f'{fo}/頭像_110_夜版.png'); sh.paste(a, (x+264, y+24), a); a = Image.open(f'{fo}/頭像_44_夜版.png'); sh.paste(a, (x+394, y+57), a)
    a = Image.open(f'{fo}/頭像_44_奶油晨光.png'); sh.paste(a, (x+450, y+57), a)
    dr.text((x+520, y+24), f'{n:02d}　{nm}', font=F(38, True), fill='#F3EEE6')
    dr.text((x+520, y+80), f'晴：{qd}', font=F(24), fill='#F2B35E'); dr.text((x+520, y+114), f'礙：{ad}', font=F(24), fill='#CFC9C0')
    yy = y+150; t = mean
    while t: dr.text((x+520, yy), t[:22], font=F(22), fill='#B8B1A7'); t = t[22:]; yy += 32
    wm = Image.open(f'{fo}/字標含副標_夜版.png').convert('RGB'); k = 190/wm.height; wm = wm.resize((int(wm.width*k), 190), Image.LANCZOS); sh.paste(wm, (x+24, y+260))
sh.save('contact_sheet_tqsa4.png')
# 色系比較：每個色系一列 → 3 款頭像 + 字標
tags = [t for t in TONES]; pick = [1, 2, 9]
RH = 230; cs = Image.new('RGB', (2300, 120+len(tags)*RH), '#EFEAE0'); dr = ImageDraw.Draw(cs)
dr.text((30, 30), '色系比較：每列一個色系（頭像 01 原版／02 三道光／09 光芒星芒＋字標）', font=F(36, True), fill='#2F2D2B')
for r, tg in enumerate(tags):
    y = 110+r*RH; P = TONES[tg]; dr.rectangle((20, y, 2280, y+RH-14), fill=P['bg'])
    dr.text((40, y+86), tg, font=F(32, True), fill=P['ink'])
    for c, n in enumerate(pick):
        a = Image.open(f'{FO[n]}/頭像_1080方_{tg}.png').resize((200, 200), Image.LANCZOS); cs.paste(a, (260+c*215, y+8))
    wm = Image.open(f'{FO[1]}/字標含副標_{tg}.png').convert('RGB'); k = 200/wm.height; wm = wm.resize((int(wm.width*k), 200), Image.LANCZOS); cs.paste(wm, (920, y+8))
cs.save('色系_tqsa4.png'); print('ok')
