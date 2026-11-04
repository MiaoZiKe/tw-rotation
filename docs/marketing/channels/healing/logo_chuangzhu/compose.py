# 後製：圓形頭像、總覽、色板、可讀性、配合示意、程式檢查
import json, os, textwrap
import numpy as np
from PIL import Image, ImageDraw, ImageFont
H = os.path.dirname(os.path.abspath(__file__)); os.chdir(H)
D = json.load(open('jobs.json', encoding='utf-8')); jobs, meta, TONES, BX, CK = D['jobs'], D['meta'], D['tones'], D['boxes'], D['chk']
M = {m['n']: m for m in meta}
F = lambda s, b=False: ImageFont.truetype(os.path.expanduser('~/.fonts/NotoSansCJKtc-%s.otf' % ('Bold' if b else 'Regular')), s)
def rgb(h): return np.array([int(h[i:i+2], 16) for i in (1, 3, 5)])
def lum(h):
    c = [x/255 for x in rgb(h)]; c = [x/12.92 if x <= .03928 else ((x+.055)/1.055)**2.4 for x in c]; return .2126*c[0]+.7152*c[1]+.0722*c[2]
def cr(a, b): x, y = sorted([lum(a), lum(b)], reverse=True); return round((x+.05)/(y+.05), 2)
def circ(im, n):
    big = im.convert('RGB').resize((n, n), Image.LANCZOS)
    m = Image.new('L', (n*4, n*4), 0); ImageDraw.Draw(m).ellipse((0, 0, n*4-1, n*4-1), fill=255); m = m.resize((n, n), Image.LANCZOS)
    o = Image.new('RGBA', (n, n), (0, 0, 0, 0)); o.paste(big, (0, 0), m); return o
def hit(a, b, mg=0): return not (a[2]+mg <= b[0] or b[2]+mg <= a[0] or a[3]+mg <= b[1] or b[3]+mg <= a[1])
rep = dict(items={}, fails=[])
def rec(n, name, ok, detail=''):
    rep['items'].setdefault(n, []).append((name, bool(ok), detail))
    if not ok: rep['fails'].append((n, name, detail))

for j in jobs:
    n = j['n']; nm = M[n]['name']; fo = M[n]['dir']
    if j['kind'] == 'avatar':
        im = Image.open(j['png']).convert('RGB'); P = TONES[j['tag']]; bg = rgb(P['bg'])
        diff = np.abs(np.array(im).astype(int) - bg).max(axis=2) > 24
        ys, xs = np.nonzero(diff); far = float(np.sqrt((xs-539.5)**2 + (ys-539.5)**2).max())
        rec(n, f'安全圓864 {j["tag"]}頭像(最遠{far:.0f}≤432)', far <= 432)
        if not P.get('mono'):
            cnt = int((np.abs(np.array(im).astype(int)-rgb(P['warm'])).max(axis=2) < 30).sum()); rec(n, f'暖光存在 {j["tag"]}({cnt}px)', cnt > 300)
        for s_ in (1080, 110, 44):
            circ(im, s_).save(f'{fo}/頭像_{s_}_{j["tag"]}.png' if s_ != 1080 else f'{fo}/頭像_1080圓形_{j["tag"]}.png')
    elif j['kind'] == 'wm':
        P = TONES[j['tag']]; im = Image.open(j['png']).convert('RGB'); bg = rgb(P['bg']); a = np.array(im).astype(int)
        diff = np.abs(a - bg).max(axis=2) > 24; ys, xs = np.nonzero(diff)
        rec(n, f'字標{"副標" if j["sub"] else ""} {j["tag"]} 離畫布邊緣≥10px', xs.min() >= 10 and ys.min() >= 10 and xs.max() <= j['w']-11 and ys.max() <= j['h']-11, f'x{xs.min()}–{xs.max()} y{ys.min()}–{ys.max()}')
        if j['tag'] == '霧紫灰':
            b = BX[j['png'][:-4]]; ks = list(b)
            ok = all(not hit(b[ks[i]], b[ks[k]], 4) for i in range(len(ks)) for k in range(i+1, len(ks)) if not (ks[i] == 'title' or ks[k] == 'title') or (n in (4,) and False))
            # title 與 icon／sub 一定要分開；n=4 的 title 是整體，另查其子件
            pairs = [(x, y) for x in ks for y in ks if x < y and not ((x == 'title' and y in ('雨線', '蜀', '窗')) or (y == 'title' and x in ('雨線', '蜀', '窗')))]
            ok = all(not hit(b[x], b[y], 4) for x, y in pairs)
            rec(n, f'字標{"副標" if j["sub"] else ""} 元件外框({"／".join(ks)}) 兩兩不相交，間距≥4', ok)
            if n not in (7, 8) and not j['sub']:
                ic = b['icon']; tl = b['title'][0]; gut = diff[:, int(ic[2])+1:int(tl)-1]
                rec(n, '字標 圖形與標題之間的縫隙像素為空', gut.sum() == 0)
for n, lst in CK.items():
    for name, ok in lst: rec(int(n), name, ok)

# ---------- 排版工具 ----------
def trim(img):
    bb = img.getbbox(); return img.crop(bb) if bb else img
def fit(img, w=None, h=None):
    r = (w / img.width) if w else (h / img.height); return img.resize((max(1, int(img.width*r)), max(1, int(img.height*r))), Image.LANCZOS)
MB = TONES['霧紫灰']
def wrapzh(s, n): return textwrap.wrap(s, n)

# ① 總覽 contact sheet（12 款，每款：圓形頭像、字標、含義、風格）
CW, CH = 470, 700; cols, rows = 4, 3
sheet = Image.new('RGB', (cols*CW+16, rows*CH+80), '#1c1a21'); d = ImageDraw.Draw(sheet)
d.text((24, 22), '「燭窗」LOGO 12 款（霧紫灰底 #4A4454；窗＝觀察的視角，燭＝窗裡那一點光；其餘色調見 palette_chuangzhu.png）', font=F(26, True), fill='#f3eef6')
for i, m in enumerate(meta):
    x0 = 8 + (i % cols)*CW; y0 = 72 + (i // cols)*CH
    d.rectangle((x0, y0, x0+CW-8, y0+CH-8), fill=MB['bg'])
    d.text((x0+16, y0+14), f'{m["n"]}. {m["name"]}', font=F(24, True), fill=MB['ink'])
    sw = d.textlength(m['style'], font=F(18)); d.text((x0+CW-8-16-sw, y0+20), m['style'], font=F(18), fill=MB['warm'])
    av = circ(Image.open(f'{m["dir"]}/頭像_1080_霧紫灰.png'), 300); sheet.paste(av, (x0+(CW-8-300)//2, y0+56), av)
    wm = Image.open(f'{m["dir"]}/字標_副標_霧紫灰.png').convert('RGB'); wm = fit(wm, w=min(400, wm.width)) if wm.width > 400 else wm
    sheet.paste(wm, (x0+(CW-8-wm.width)//2, y0+372))
    for k, ln in enumerate(wrapzh('含義：' + m['mean'], 22)): d.text((x0+16, y0+372+wm.height+12+k*28), ln, font=F(19), fill=MB['ink'])
sheet.save('contact_sheet_chuangzhu.png')

# ② 色板 12 款 × 6 色
names = list(TONES); CS = 150
pal = Image.new('RGB', (190 + 6*(CS+14), 150 + 12*(CS+12)), '#1c1a21'); d = ImageDraw.Draw(pal)
d.text((20, 18), '「燭窗」12 款 × 6 色調（圓形頭像；上方色票＝底／主色／輔色／暖光）', font=F(24, True), fill='#f3eef6')
for t, tn in enumerate(names):
    P = TONES[tn]; x = 190 + t*(CS+14)
    d.text((x, 62), tn, font=F(20, True), fill='#f3eef6')
    for k, key in enumerate(('bg', 'ink', 'mid', 'warm')):
        d.rectangle((x+k*36, 94, x+k*36+30, 124), fill=P[key], outline='#777');
    d.text((x, 126), f'{P["bg"]} ／ {P["warm"]}', font=F(12), fill='#bdb6c6')
for i, m in enumerate(meta):
    y = 150 + i*(CS+12); d.text((16, y+CS//2-14), f'{m["n"]}. {m["name"]}', font=F(18, True), fill='#f3eef6')
    for t, tn in enumerate(names):
        av = circ(Image.open(f'{m["dir"]}/頭像_1080_{tn}.png'), CS); pal.paste(av, (190+t*(CS+14), y), av)
pal.save('palette_chuangzhu.png')

# ③ 可讀性：110／44px，三種暗色調＋米白紙＋單色黑；放在 IG 個人頁常見的深／淺底
show = ['霧紫灰', '深夜藍', '灰綠', '米白紙', '單色黑']
rd = Image.new('RGB', (200 + len(show)*190, 90 + 12*128), '#121212'); d = ImageDraw.Draw(rd)
d.text((16, 14), '可讀性：IG 個人頁實際大小 110px／44px（左 110，右 44）；底：深色頁 #121212、淺色頁 #FFFFFF', font=F(22, True), fill='#f3eef6')
for t, tn in enumerate(show): d.text((200+t*190, 56), tn, font=F(18, True), fill='#f3eef6')
for i, m in enumerate(meta):
    y = 90 + i*128
    d.text((14, y+46), f'{m["n"]}. {m["name"]}', font=F(18), fill='#f3eef6')
    for t, tn in enumerate(show):
        x = 200 + t*190; light = tn in ('米白紙', '單色黑')
        d.rectangle((x-6, y, x+176, y+122), fill='#ffffff' if light else '#121212')
        a = Image.open(f'{m["dir"]}/頭像_110_{tn}.png'); b = Image.open(f'{m["dir"]}/頭像_44_{tn}.png')
        rd.paste(a, (x, y+6), a); rd.paste(b, (x+118, y+40), b)
rd.save('可讀性_chuangzhu_110_44.png')

# ④ 配合示意：封面右下角（抹掉原小字「我們這一代」，換成字標；寬 ≥220px）
os.makedirs('配合示意', exist_ok=True)
cov0 = Image.open('../samples/20261104_gen2000_v5/post2/01_cover.png').convert('RGB')
cov = cov0.copy(); patch = cov0.crop((820, 1145, 995, 1185)).resize((175, 40))
for yy in (1218, 1235): cov.paste(patch.crop((0, 0, 175, 20)) if yy == 1218 else patch.crop((0, 20, 175, 40)), (820, yy+0))
cov.paste(cov0.crop((820, 1145, 995, 1275)).resize((175, 40)).resize((175, 130)), (820, 1210)) if False else None
fill = cov0.crop((820, 1140, 995, 1140+60)); cov.paste(fill, (820, 1215)); cov.paste(cov0.crop((820, 1140, 995, 1140+30)), (820, 1262-17))
strips = []; fitrep = []
for m in meta:
    wm = Image.open(f'{m["dir"]}/字標_透明_霧紫灰.png').convert('RGBA'); wm = trim(wm); wm = fit(wm, w=240)
    c = cov.copy().convert('RGBA'); px, py = 985-wm.width, 1280-wm.height
    c.alpha_composite(wm, (px, py)); c = c.convert('RGB'); c.save(f'配合示意/{m["n"]:02d}_{m["name"]}.png')
    box = (px, py, px+wm.width, py+wm.height)
    # 檢查：字標與同封面其他元素（沒有馬上回答…、往右滑）不相交；寬≥220
    others = {'副標句': (97, 1150, 505, 1186), '往右滑': (97, 1228, 225, 1262), '大標': (97, 985, 612, 1105), '頁碼': (918, 100, 985, 135)}
    ok = all(not hit(box, o, 8) for o in others.values()) and wm.width >= 220 and box[2] <= 985 and box[3] <= 1285
    rec(m['n'], f'配合示意 字標寬{wm.width}px≥220、與封面文字不相交、右緣≤985', ok)
    strips.append(c.crop((480, 1100, 1080, 1350)))
ps = Image.new('RGB', (3*610+10, 4*290+60), '#1c1a21'); d = ImageDraw.Draw(ps)
d.text((16, 14), '配合示意：字標放在 samples/20261104_gen2000_v5/post2/01_cover.png 右下角（寬 240px，原小字已抹除；取封面右下 600×250 區塊）', font=F(22, True), fill='#f3eef6')
for i, s_ in enumerate(strips):
    x = 8 + (i % 3)*610; y = 54 + (i//3)*290; ps.paste(s_, (x, y+30)); d.text((x+6, y+4), f'{meta[i]["n"]}. {meta[i]["name"]}', font=F(20, True), fill='#f3eef6')
ps.save('配合示意_chuangzhu_封面右下角.png')

json.dump(dict(items=rep['items'], fails=rep['fails']), open('overlap_report.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for n in sorted(rep['items']): print(n, len(rep['items'][n]), 'items,', sum(1 for _, ok, _ in rep['items'][n] if not ok), 'fail')
print('FAILS', rep['fails'])
print({tn: dict(ink=cr(P['ink'], P['bg']), warm=cr(P['warm'], P['bg'])) for tn, P in TONES.items()})
