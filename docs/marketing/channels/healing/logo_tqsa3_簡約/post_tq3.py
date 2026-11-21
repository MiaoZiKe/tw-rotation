# 後製：圓形頭像 110／44、重疊與對比檢查、總覽、可讀性、字標比較、放進模板角落示意
import json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from gen_tq3 import SYMS, TONES, CHK, ratio, tq_text, ta_text, DEFAULT
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
def dil(m, px): return np.array(Image.fromarray((m*255).astype('uint8')).filter(ImageFilter.MaxFilter(px*2+1))) > 100
for j in J:
    if j['kind'] != 'avatar': continue
    im = Image.open(j['png']); fo = FO[j['n']]
    for s in (1080, 110, 44): circ(im, s).save(f'{fo}/頭像_{"1080圓" if s == 1080 else s}_{j["tag"]}.png')
    P = TONES[j['tag']]; bg = np.array([int(P['bg'][i:i+2], 16) for i in (1, 3, 5)])
    d = np.abs(np.array(im.convert('RGB')).astype(int)-bg).max(axis=2) > 24; ys, xs = np.nonzero(d)
    far = float(np.sqrt((xs-539.5)**2+(ys-539.5)**2).max())
    chk(far <= 432, f'{j["n"]:02d} {j["tag"]} 頭像內容在安全圓 432 內（實測 {far:.0f}）')
for n in FO:
    a, q = A(f'{CHK}/{n}av_a.png'), A(f'{CHK}/{n}av_q.png')
    chk(a.sum() > 800 and q.sum() > 800, f'{n:02d} 頭像「礙」「晴」圖層皆非空（{int(a.sum())}／{int(q.sum())}px）')
    chk(not (a & q).any(), f'{n:02d} 頭像「礙」×「晴」不相交')
    chk(not (dil(a, 8) & q).any(), f'{n:02d} 頭像「礙」與「晴」間距 ≥8px')
    for font in ('serif', 'sans'):
        m = {l: A(f'{CHK}/{n}wm_{font}_{l}.png') for l in ('sym', 'txt', 'sub')}
        for l in m: chk(m[l].sum() >= 500, f'{n:02d} 字標({font}) 圖層 {l} 非空（{int(m[l].sum())}px）')
        for x, y in (('sym', 'txt'), ('sym', 'sub'), ('txt', 'sub')): chk(not (m[x] & m[y]).any(), f'{n:02d} 字標({font}) {x}×{y} 不相交')
        xs = np.nonzero(m['sym'].any(0))[0]; xt = np.nonzero(m['txt'].any(0))[0]; g = int(xt.min()-xs.max())
        chk(g >= 30, f'{n:02d} 字標({font}) 圖示與文字間距 {g}px ≥30')
        chk(not (dil(m['txt'], 14) & m['sub']).any(), f'{n:02d} 字標({font}) 名稱與副標間距 ≥14px')
        al = m['sym'] | m['txt'] | m['sub']; ys2, xs2 = np.nonzero(al); h, w = al.shape
        chk(xs2.min() >= 20 and ys2.min() >= 20 and xs2.max() <= w-20 and ys2.max() <= h-20, f'{n:02d} 字標({font}) 內容離畫布邊 ≥20px')
for tag, P in TONES.items():
    for what, fg in (('「晴」字', tq_text(P)), ('「礙」字', ta_text(P)), ('「談／說」字', P['ink']), ('副標', P['sub'])):
        r = ratio(fg, P['bg']); CR.append(dict(tone=tag, what=what, fg=fg, bg=P['bg'], ratio=round(r, 2))); chk(r >= 4.5, f'對比 {tag} {what} {fg} 對 {P["bg"]} = {r:.2f}:1 ≥4.5')
    for what, fg in (('符號「晴」色', P['q']), ('符號「礙」色', P['a'])):   # 符號非文字，僅記錄（≥3:1 為圖形對比門檻）
        r = ratio(fg, P['bg']); CR.append(dict(tone=tag, what=what+'（符號，門檻 3:1）', fg=fg, bg=P['bg'], ratio=round(r, 2))); chk(r >= 3.0 or P.get('mono') and r >= 4.5, f'符號對比 {tag} {what} {r:.2f}:1 ≥3')
json.dump(dict(checked=len(items), fails=fails, items=items, contrast=CR), open('overlap_report.json', 'w'), ensure_ascii=False, indent=1)
print('檢查', len(items), '項，失敗', len(fails)); [print(' ', f) for f in fails]
# ===== 總覽 =====
FD = os.path.expanduser('~/.fonts/'); F = lambda s, b=False: ImageFont.truetype(FD+('NotoSansCJKtc-Bold.otf' if b else 'NotoSansCJKtc-Regular.otf'), s)
CW, CH = 1100, 560; sh = Image.new('RGB', (2*CW+60, 190+5*CH), '#EFEAE0'); dr = ImageDraw.Draw(sh)
dr.text((30, 26), '「談晴說礙」LOGO 第三輪：簡約 10 款', font=F(44, True), fill='#2F2D2B')
dr.text((30, 100), '符號只用 1～3 個幾何元素、同一線寬；晴＝晴光橘、礙＝雲灰；字不放進圖形。夜版為主、晝版為輔。', font=F(26), fill='#6E6A66')
dr.text((30, 140), '每格：頭像（圓）300／110／44px 與橫式字標（含副標）。', font=F(24), fill='#6E6A66')
for i, (n, (fo, nm, mean, qd, ad, _)) in enumerate(SYMS.items()):
    x = 20+(i % 2)*(CW+20); y = 190+(i//2)*CH
    dr.rounded_rectangle((x, y, x+CW, y+CH-16), 20, fill='#2B2A2E')
    av = Image.open(f'{fo}/頭像_1080圓_夜版.png').resize((260, 260), Image.LANCZOS); sh.paste(av, (x+24, y+24), av)
    px = x+310
    for t, s, yy in (('夜版', 110, 24), ('晝版', 110, 24), ('夜版', 44, 160), ('晝版', 44, 160)):
        a = Image.open(f'{fo}/頭像_{s}_{t}.png'); sh.paste(a, (px, y+yy), a); px += 130 if s == 110 else 70
        if s == 110 and t == '晝版': px = x+310
    dr.text((x+310, y+215), '110／44px：夜版、晝版', font=F(20), fill='#B8B1A7')
    dr.text((x+620, y+30), f'{n:02d}　{nm}', font=F(40, True), fill='#F3EEE6')
    dr.text((x+620, y+92), f'晴：{qd}', font=F(23), fill='#F2B35E'); dr.text((x+620, y+130), f'礙：{ad}', font=F(23), fill='#CFC9C0')
    dr.text((x+620, y+168), mean, font=F(21), fill='#B8B1A7')
    w1 = Image.open(f'{fo}/字標含副標_夜版.png').convert('RGB'); k = 500/w1.width; w1 = w1.resize((500, int(w1.height*k)), Image.LANCZOS); sh.paste(w1, (x+24, y+300))
    w2 = Image.open(f'{fo}/字標含副標_晝版.png').convert('RGB'); w2 = w2.resize((500, int(w2.height*k)), Image.LANCZOS); sh.paste(w2, (x+560, y+300))
sh.save('contact_sheet_tqsa3.png')
# ===== 可讀性 =====
t = ['夜版', '晝版', '單色黑', '單色白']
rd = Image.new('RGB', (230+len(t)*200, 130+10*130), '#E6E1D8'); d2 = ImageDraw.Draw(rd)
d2.text((20, 24), '可讀性：110px 與 44px 實際大小（每格左 110、右 44）', font=F(32, True), fill='#2F2D2B')
for c, tg in enumerate(t): d2.text((230+c*200, 82), tg, font=F(22), fill='#555')
for r, (n, v) in enumerate(SYMS.items()):
    y = 120+r*130; d2.text((20, y+40), f'{n:02d} {v[1]}', font=F(24), fill='#2F2D2B')
    for c, tg in enumerate(t):
        a = Image.open(f'{v[0]}/頭像_110_{tg}.png'); rd.paste(a, (230+c*200, y), a); b = Image.open(f'{v[0]}/頭像_44_{tg}.png'); rd.paste(b, (350+c*200, y+33), b)
rd.save('可讀性_tqsa3_110_44.png')
# ===== 字標比較（推薦三款 × 4 種字型／點色）=====
REC = [8, 9, 10]; VN = ['襯線_晴礙點色', '襯線_全單色', '黑體_晴礙點色', '黑體_全單色']
ims = {(n, v): Image.open(f'{FO[n]}/字標變體_夜版_{v}.png').convert('RGB') for n in REC for v in VN}
cw = max(i.width for i in ims.values()); ch = ims[(8, VN[0])].height
cmp_ = Image.new('RGB', (2*(cw//2+30)+30, 120+3*2*(ch//2+30)), '#1E1D20'); d4 = ImageDraw.Draw(cmp_)
d4.text((30, 24), '字標比較（夜版）：襯線／黑體 × 晴礙點色／全單色', font=F(34, True), fill='#F3EEE6')
for r, n in enumerate(REC):
    for c, v in enumerate(VN):
        im = ims[(n, v)]; im = im.resize((im.width//2, im.height//2), Image.LANCZOS)
        xx = 30+(c % 2)*(cw//2+30); yy = 90+(r*2+c//2)*(ch//2+30)
        cmp_.paste(im, (xx, yy)); d4.text((xx, yy+ch//2+2), f'{n:02d} {v}', font=F(18), fill='#B8B1A7')
cmp_.save('字標比較_tqsa3.png')
# ===== 放進模板角落示意 =====
SRC = '../samples/20261104_gen2000_v4/post2/01_cover.png'; cov = Image.open(SRC).convert('RGB')
mocks = []; mk_items = []
for n in REC:
    im = cov.copy(); im.paste(cov.crop((80, 175, 420, 235)), (80, 85))   # 拿同底的空白區蓋掉原本的頁標，讓出左上角
    wm = Image.open(f'{FO[n]}/字標_透明_夜版.png').convert('RGBA'); k = 330/wm.width; wm = wm.resize((330, int(wm.height*k)), Image.LANCZOS)
    px, py = 80, 117-wm.height//2; im.paste(wm, (px, py), wm)
    # 重疊檢查：logo 的外框不得碰到 1/6 頁碼（右上）與主插圖（y>180）
    box = wm.getbbox(); lx1 = px+box[2]; ly1 = py+box[3]
    mk_items.append(lx1 < 900 and ly1 < 180)
    im.save(f'示意_放進模板角落_{n:02d}_{SYMS[n][1]}.png'); mocks.append(im)
sheet = Image.new('RGB', (3*540+40, 1350//2+120), '#1E1D20'); d5 = ImageDraw.Draw(sheet)
d5.text((20, 24), '放進模板角落（深色底＋細線插畫＋一點暖光，LOGO 在左上）：08 缺口圓／09 三點／10 雙圓對談', font=F(28, True), fill='#F3EEE6')
for i, im in enumerate(mocks): sheet.paste(im.resize((540, 675), Image.LANCZOS), (10+i*550, 90))
sheet.save('示意_放進模板角落.png')
# 角落特寫（原尺寸左上 1080×300）
cr = Image.new('RGB', (1080, 3*300+20), '#1E1D20')
for i, im in enumerate(mocks): cr.paste(im.crop((0, 0, 1080, 300)), (0, i*310))
cr.save('示意_放進模板角落_特寫.png')
print('角落示意檢查', mk_items, 'ok')
rep = json.load(open('overlap_report.json')); rep['mock_ok'] = mk_items; json.dump(rep, open('overlap_report.json', 'w'), ensure_ascii=False, indent=1)
