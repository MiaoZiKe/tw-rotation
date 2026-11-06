# 後製：圓形頭像 110／44、重疊檢查、對比檢查、總覽、可讀性、色調、上一輪對照
import json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from gen_tq2 import SYMS, SIMPLE, TONES, CHK, ALLOW, ratio, blend, TQ, TA, CF, SF, mono, NAME
H = os.path.dirname(os.path.abspath(__file__)); os.chdir(H)
J = json.load(open('jobs.json'))['jobs']; fails = []; items = []; CR = []
FO = {n: v[0] for n, v in SYMS.items()}
def circ(im, s):
    big = im.convert('RGB').resize((s, s), Image.LANCZOS); m = Image.new('L', (s*4, s*4), 0)
    ImageDraw.Draw(m).ellipse((0, 0, s*4-1, s*4-1), fill=255); m = m.resize((s, s), Image.LANCZOS)
    o = Image.new('RGBA', (s, s), (0, 0, 0, 0)); o.paste(big, (0, 0), m); return o
def chk(ok, msg):
    items.append(msg)
    if not ok: fails.append(msg)
A = lambda p: np.array(Image.open(p))[:, :, 3] > 20
for j in J:
    if j['kind'] in ('avatar', 'savatar'):
        im = Image.open(j['png']); fo = FO[j['n']] if j['kind'] == 'avatar' else '頭像簡化版'; pre = '' if j['kind'] == 'avatar' else f'{j["n"]}_'
        for s in (1080, 110, 44): circ(im, s).save(f'{fo}/{pre}頭像_{"1080圓" if s == 1080 else s}_{j["tag"]}.png')
        P = TONES[j['tag']]; bg = np.array([int(P['bg'][i:i+2], 16) for i in (1, 3, 5)])
        d = np.abs(np.array(im.convert('RGB')).astype(int)-bg).max(axis=2) > 24; ys, xs = np.nonzero(d)
        far = float(np.sqrt((xs-539.5)**2+(ys-539.5)**2).max())
        chk(far <= 432, f'{j["n"]} {j["tag"]} 頭像內容在安全圓 432 內（實測 {far:.0f}）')
for n in FO:
    m = {l: A(f'{CHK}/{n}wm_{l}.png') for l in ('sym', 'txt', 'sub')}
    for l in m: chk(m[l].sum() >= 500, f'{n} 字標圖層 {l} 非空（{int(m[l].sum())}px）')
    for a, b in (('sym', 'txt'), ('sym', 'sub'), ('txt', 'sub')): chk(not (m[a] & m[b]).any(), f'{n} 字標 {a}×{b} 不相交')
    xs = np.nonzero(m['sym'].any(0))[0]; xt = np.nonzero(m['txt'].any(0))[0]; g = int(xt.min()-xs.max())
    chk(g >= 30, f'{n} 圖示與文字間距 {g}px ≥30')
    # 頭像逐層：晴／礙兩字不相交、字在底的內側（縮 8px 後仍包含）、字與裝飾不相交（允許款除外）
    lay = {l: A(f'{CHK}/{n}av_{l}.png') for l in ('h', 'x', 'g1', 'g2')}
    for l in (('g1',) if n == 2 else ('g1', 'g2')): chk(lay[l].sum() > 800, f'{n} 頭像圖層 {l} 非空（{int(lay[l].sum())}px）')
    chk(n == 2 or not (lay['g1'] & lay['g2']).any(), f'{n} 頭像「晴」×「礙」不相交')
    chk(n == 2 or (not (lay['x'] & lay['g1']).any() and not (lay['x'] & lay['g2']).any()), f'{n} 頭像字×裝飾不相交')
    if lay['h'].sum() > 0:
        er = np.array(Image.fromarray((lay['h']*255).astype('uint8')).filter(ImageFilter.MinFilter(17))) > 100
        for l in ('g1', 'g2'):
            out = int((lay[l] & ~er).sum())
            if lay[l].sum() and n not in (2, 6, 9):
                chk(out == 0, f'{n} 頭像「{"晴" if l == "g1" else "礙"}」在底內側留 8px（超出 {out}px）')
# 對比
for n, (fo, nm, mean, fn) in SYMS.items():
    pass
for tag, P in TONES.items():
    for what, fg, bg in (('字標「晴」', TQ(P), P['bg']), ('字標「礙」', TA(P), P['bg']), ('字標「談／說」與副標', P['ink'], P['bg']),
                         ('底內「晴」（太陽盤）', TQ(P, SF(P)), SF(P)), ('底內「礙」（雲底）', TA(P, CF(P)), CF(P))):
        r = ratio(fg, bg); CR.append(dict(tone=tag, what=what, fg=fg, bg=bg, ratio=round(r, 2))); chk(r >= 4.5, f'對比 {tag} {what} {r:.2f}:1 ≥4.5')
json.dump(dict(checked=len(items), fails=fails, items=items, contrast=CR), open('overlap_report.json', 'w'), ensure_ascii=False, indent=1)
print('檢查', len(items), '項，失敗', len(fails)); [print(' ', f) for f in fails]
# ===== 總覽 =====
FD = os.path.expanduser('~/.fonts/'); F = lambda s, b=False: ImageFont.truetype(FD+('NotoSansCJKtc-Bold.otf' if b else 'NotoSansCJKtc-Regular.otf'), s)
def wrap(t, f, w, dr):
    out, cur = [], ''
    for ch in t:
        if dr.textlength(cur+ch, font=f) > w: out.append(cur); cur = ch
        else: cur += ch
    return out + [cur]
CW, CH = 540, 800; cols = 3; rows = 4
sh = Image.new('RGB', (cols*CW+40, 150+rows*CH), '#FBF7F0'); dr = ImageDraw.Draw(sh)
dr.text((30, 26), '「談晴說礙」LOGO 第二輪 11 款：晴、礙兩個字放進圖形（奶油晨光）', font=F(40, True), fill='#3A3A3A')
dr.text((30, 88), '「晴」＝太陽橘（淺底加深到對比 4.5:1 以上）、「礙」＝雲灰；副標「礙還在，晴也在。」', font=F(26), fill='#8A5A2E')
for i, (n, (fo, nm, mean, _)) in enumerate(SYMS.items()):
    x = 20+(i % cols)*CW; y = 140+(i//cols)*CH
    dr.rounded_rectangle((x, y, x+CW-20, y+CH-20), 22, fill='white', outline='#EADFCF', width=2)
    av = Image.open(f'{fo}/頭像_1080圓_奶油晨光.png').resize((300, 300), Image.LANCZOS); sh.paste(av, (x+20, y+20), av)
    for k, t in enumerate(('晴空淡藍', '深色模式')):
        a = Image.open(f'{fo}/頭像_110_{t}.png').resize((96, 96), Image.LANCZOS); sh.paste(a, (x+340, y+30+k*110), a)
    a = Image.open(f'{fo}/頭像_44_奶油晨光.png'); sh.paste(a, (x+366, y+255), a)
    wm = Image.open(f'{fo}/字標含副標_奶油晨光.png').convert('RGB'); k = (CW-60)/wm.width; wm = wm.resize((CW-60, int(wm.height*k)), Image.LANCZOS); sh.paste(wm, (x+20, y+340))
    yy = y+350+wm.height; dr.text((x+20, yy), f'{n:02d}　{nm}', font=F(34, True), fill='#3A3A3A')
    for li, line in enumerate(wrap(mean, F(24), CW-70, dr)): dr.text((x+20, yy+52+li*34), line, font=F(24), fill='#555')
# 第 12 格：頭像簡化版
x = 20+2*CW; y = 140+3*CH + 0
x = 20+(11 % cols)*CW; y = 140+(11//cols)*CH
dr.rounded_rectangle((x, y, x+CW-20, y+CH-20), 22, fill='#FFF3DF', outline='#EADFCF', width=2)
dr.text((x+20, y+16), '頭像簡化版（只留一個字）', font=F(32, True), fill='#3A3A3A')
for k, (key, (nm, _)) in enumerate(SIMPLE.items()):
    a = Image.open(f'頭像簡化版/{key}_頭像_1080圓_奶油晨光.png').resize((230, 230), Image.LANCZOS); sh.paste(a, (x+20+k*250, y+70), a)
    a = Image.open(f'頭像簡化版/{key}_頭像_44_奶油晨光.png'); sh.paste(a, (x+20+k*250, y+320), a)
    a = Image.open(f'頭像簡化版/{key}_頭像_110_奶油晨光.png'); sh.paste(a, (x+90+k*250, y+300), a)
    dr.text((x+20+k*250, y+380), nm[:2]+key[0], font=F(26, True), fill='#3A3A3A')
for li, line in enumerate(wrap('44px 看不清楚「礙」的款式，頭像請改用這兩款簡化版（A 只留「晴」、B 只留「礙」），完整版留給橫式字標與大圖。', F(24), CW-70, dr)): dr.text((x+20, y+430+li*34), line, font=F(24), fill='#555')
sh.save('contact_sheet_tqsa2.png')
t = ['奶油晨光', '晴空淡藍', '抹茶午後', '深色模式', '單色黑', '單色白']
rd = Image.new('RGB', (260+len(t)*180, 120+13*130), '#F4F4F4'); d2 = ImageDraw.Draw(rd)
d2.text((20, 30), '可讀性：110px 與 44px 實際大小（每格左 110、右 44）', font=F(34, True), fill='#333')
for c, tg in enumerate(t): d2.text((260+c*180, 80), tg, font=F(22), fill='#555')
rowsl = [(f'{n:02d} {v[1]}', v[0], '') for n, v in SYMS.items()] + [(f'簡化{k[0]}', '頭像簡化版', k+'_') for k in SIMPLE]
for r, (lab, fo, pre) in enumerate(rowsl):
    y = 120+r*130; d2.text((20, y+40), lab, font=F(26), fill='#333')
    for c, tg in enumerate(t):
        a = Image.open(f'{fo}/{pre}頭像_110_{tg}.png'); rd.paste(a, (260+c*180, y), a); b = Image.open(f'{fo}/{pre}頭像_44_{tg}.png'); rd.paste(b, (380+c*180, y+33), b)
rd.save('可讀性_tqsa2_110_44.png')
pal = Image.new('RGB', (6*230+40, 13*230+40), '#FBF7F0')
for r, (lab, fo, pre) in enumerate(rowsl):
    for c, tg in enumerate(t):
        a = Image.open(f'{fo}/{pre}頭像_1080圓_{tg}.png').resize((210, 210), Image.LANCZOS); pal.paste(a, (20+c*230, 20+r*230), a)
pal.save('palette_tqsa2.png')
# 上一輪 vs 這輪（4 款升級）
OLD = '../logo_tqsa'; pairs = [('04 半晴半礙', f'{OLD}/04_半晴半礙', '05 半晴半礙', 5), ('05 談與說', f'{OLD}/05_談與說', '03 雙泡對話', 3), ('06 雲朵對話框', f'{OLD}/06_雲朵對話框', '04 雲泡太陽尾', 4), ('08 晴礙字章', f'{OLD}/08_晴礙字章', '07 圓章', 7), ('01 雲帶缺口', f'{OLD}/01_雲帶缺口', '01 雲帶缺口．晴', 1)]
cp = Image.new('RGB', (len(pairs)*440+40, 1180), '#FBF7F0'); d3 = ImageDraw.Draw(cp)
d3.text((30, 24), '上一輪 vs 這輪（升級款並排；上＝上一輪、下＝這輪，皆奶油晨光）', font=F(34, True), fill='#3A3A3A')
for i, (ol, od, nl, nn) in enumerate(pairs):
    x = 20+i*440
    for k, (lab, pth) in enumerate(((f'上一輪 {ol}', f'{od}/頭像_1080圓_奶油晨光.png'), (f'這輪 {nl}', f'{FO[nn]}/頭像_1080圓_奶油晨光.png'))):
        y = 90+k*540; d3.text((x+10, y), lab, font=F(28, True), fill='#3A3A3A')
        a = Image.open(pth).resize((400, 400), Image.LANCZOS); cp.paste(a, (x+10, y+44), a)
        a = Image.open(pth.replace('1080圓', '44')); cp.paste(a, (x+10, y+462), a); d3.text((x+66, y+466), '← 44px', font=F(20), fill='#777')
cp.save('對照_上一輪vs這輪.png'); print('ok')
