# 後製：圓形頭像 1080／110／44、總覽、可讀性、配合示意、程式檢查
import json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
H = os.path.dirname(os.path.abspath(__file__)); os.chdir(H)
D = json.load(open('jobs.json', encoding='utf-8')); jobs, styles, PAL = D['jobs'], D['styles'], D['pal']
boxes = json.load(open('boxes.json'))
F = lambda s, b=False: ImageFont.truetype(os.path.expanduser('~/.fonts/NotoSansCJKtc-%s.otf' % ('Bold' if b else 'Regular')), s)
def lum(h):
    h = h.lstrip('#'); c = [int(h[i:i+2], 16)/255 for i in (0, 2, 4)]
    c = [x/12.92 if x <= .03928 else ((x+.055)/1.055)**2.4 for x in c]; return .2126*c[0]+.7152*c[1]+.0722*c[2]
def cr(a, b): x, y = sorted([lum(a), lum(b)], reverse=True); return round((x+.05)/(y+.05), 2)
def circ(im, n):
    big = im.convert('RGB').resize((n, n), Image.LANCZOS)
    m = Image.new('L', (n*4, n*4), 0); ImageDraw.Draw(m).ellipse((0, 0, n*4-1, n*4-1), fill=255); m = m.resize((n, n), Image.LANCZOS)
    o = Image.new('RGBA', (n, n), (0, 0, 0, 0)); o.paste(big, (0, 0), m); return o
def hit(a, b): return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])
SN = {s['n']: s for s in styles}; FO = lambda n: f"{n:02d}_{SN[n]['name']}"
def P(n, kind, tag): return f'{FO(n)}/{kind}_{tag}.png'
rep = dict(items=[], fails=[])
def rec(name, ok, detail=''):
    rep['items'].append((name, ok, detail))
    if not ok: rep['fails'].append((name, detail))
for j in jobs:
    bx = boxes[j['svg']]; nm = SN[j['n']]['name']
    if j['kind'] == 'avatar':
        im = Image.open(j['png']).convert('RGB'); h = PAL[j['tag']]['bg']; bg = np.array([int(h[i:i+2], 16) for i in (1, 3, 5)])
        diff = np.abs(np.array(im).astype(int) - bg).max(axis=2) > 24
        ys, xs = np.nonzero(diff); far = float(np.sqrt((xs-539.5)**2 + (ys-539.5)**2).max())
        yl = np.array([int(PAL['霧紫灰']['lamp'][i:i+2], 16) for i in (1, 3, 5)]) if j['tag'] == '霧紫灰' else None
        if yl is not None: rec(f'暖黃燈存在 {nm}（{int((np.abs(np.array(im).astype(int)-yl).max(axis=2)<30).sum())}px）', int((np.abs(np.array(im).astype(int)-yl).max(axis=2)<30).sum()) > 300)
        rec(f'安全圓864 {nm}{j["tag"]}頭像(最遠{far:.0f}px)', far <= 432)
        FS = {}
        def ink(i):   # 文字只取墨跡範圍（字型行高會讓外框虛大）：基線上 0.88 字高、下 0.12 字高
            b = bx[i]; f = FS.get((j['n'], i))
            if not f: return b
            base = b[1] + 1.16 * f * j['sc']; return [b[0], base - 0.88 * f * j['sc'], b[2], base + 0.12 * f * j['sc']]
        for pa in j['pairs']:
            rec(f'頭像內不重疊 {nm}{j["tag"]} {pa}', not hit(ink(pa[0]), ink(pa[1])))
        for s in (1080, 110, 44): circ(im, s).save(f'{FO(j["n"])}/頭像_{s}_{j["tag"]}.png' if s != 1080 else f'{FO(j["n"])}/頭像_1080圓形_{j["tag"]}.png')
    elif j['kind'] == 'wm':
        s, t = bx['sym'], bx['nm']; gap = t[0]-s[2]; need = .25*120
        rec(f'字標符號與字不重疊且間距≥0.25字高 {nm}{j["tag"]}(間距{gap:.0f}≥{need:.0f})', (not hit(s, t)) and gap >= need)
cont = {}
for tag, c in PAL.items():
    cont[tag] = dict(線條對底=cr(c['line'], c['bg']), 燈對底=cr(c['lamp'], c['bg']), 字標對底=cr(c['ink'], c['bg']))
rec('對比：線條>=3、字標>=4.5、燈>=3', all(v['線條對底'] >= 3 and v['燈對底'] >= 3 and v['字標對底'] >= 4.5 for v in cont.values()), json.dumps(cont, ensure_ascii=False))
TAGS = list(PAL); N = len(styles)
# ---- 總覽 5x2 ----
CW, CH = 500, 680
SH = Image.new('RGB', (5*CW + 60, 2*CH + 110), '#1E1C22'); d = ImageDraw.Draw(SH)
d.text((24, 22), '「我們這一代」創意概念 LOGO 10 款（④霧紫灰 底 #4A4454）：頭像＋字標', font=F(32, True), fill='#EEE')
for i, st in enumerate(styles):
    n = st['n']; x0 = 10 + (i % 5)*(CW+10); y0 = 80 + (i//5)*(CH+10)
    d.rectangle((x0, y0, x0+CW, y0+CH), fill=PAL['霧紫灰']['bg'])
    av = circ(Image.open(P(n, '頭像_1080', '霧紫灰')), 300); SH.paste(av, (x0+100, y0+60), av)
    wm = Image.open(P(n, '字標', '霧紫灰')).convert('RGB'); sc = min((CW-40)/wm.width, 110/wm.height); wm = wm.resize((int(wm.width*sc), int(wm.height*sc)), Image.LANCZOS)
    SH.paste(wm, (x0 + (CW-wm.width)//2, y0+400))
    d.text((x0+16, y0+14), f'{n}. {st["name"]}', font=F(26, True), fill='#F3EFF5')
    line, yy = '', y0+535
    for ch in st['exp'] + '':
        if F(21).getlength(line+ch) > CW-32: d.text((x0+16, yy), line, font=F(21), fill='#E6DFEA'); yy += 30; line = ch
        else: line += ch
    d.text((x0+16, yy), line, font=F(21), fill='#E6DFEA'); d.text((x0+16, y0+CH-34), '手法：'+st['how'], font=F(18), fill='#ABA0B5')
    rec(f'總覽 {st["name"]} 概念句不超出格底', yy+30 < y0+CH-36)
    rec(f'總覽 {st["name"]} 頭像與字標版面不重疊', not hit((x0+100, y0+60, x0+400, y0+360), (x0+(CW-wm.width)//2, y0+400, x0+(CW+wm.width)//2, y0+400+wm.height)))
    rec(f'總覽 {st["name"]} 標題與頭像不重疊', not hit((x0+16, y0+14, x0+260, y0+48), (x0+100, y0+60, x0+400, y0+360)))
SH.save('contact_sheet_idea.png')
# ---- 可讀性 ----
RHt = 120; S2 = Image.new('RGB', (3*330 + 240, 110 + N*RHt + 30), '#1E1C22'); d2 = ImageDraw.Draw(S2)
d2.text((24, 20), '縮圖可讀性：IG 實際 110px 與留言區 44px（實際大小），三種底色', font=F(28, True), fill='#EEE')
for i, t in enumerate(TAGS): d2.text((240 + i*330 + 10, 70), t, font=F(22, True), fill='#CCC')
for r, st in enumerate(styles):
    n = st['n']; y0 = 110 + r*RHt; d2.text((20, y0+40), f'{n}. {st["name"]}', font=F(24, True), fill='#EEE')
    for i, t in enumerate(TAGS):
        x0 = 240 + i*330; d2.rectangle((x0, y0+4, x0+320, y0+RHt-4), fill=PAL[t]['bg'])
        a = Image.open(P(n, '頭像_110', t)); S2.paste(a, (x0+14, y0+5), a)
        b = Image.open(P(n, '頭像_44', t)); S2.paste(b, (x0+14+110+16, y0+40), b)
        z = b.resize((88, 88), Image.NEAREST); S2.paste(z, (x0+14+110+16+44+20, y0+16), z)
d2.text((24, 110 + N*RHt + 2), '每列右側最大者為 44px 放大 2 倍，只方便肉眼，不代表實際。', font=F(18), fill='#999')
S2.save('可讀性_idea_110_44.png')
# ---- 配合示意 ----
cov = Image.open('../samples/20261104_gen2000_v3/post2/01_cover_noperson.png').convert('RGB')
patch = cov.crop((740, 1130, 1000, 1204)); cov.paste(patch, (740, 1196))   # 蓋掉原本右下角的舊字標
OTHER = {'往右滑': (96, 1226, 222, 1262), '副句': (96, 1108, 514, 1150)}
mocks = []
for st in styles:
    n = st['n']; wm = Image.open(f'{FO(n)}/字標_透明_霧紫灰.png').convert('RGBA'); wm = wm.crop(wm.getbbox())
    sc = 224 / wm.width; wm = wm.resize((224, max(1, int(wm.height*sc))), Image.LANCZOS)
    im = cov.copy(); x = 984 - wm.width; y = 1262 - wm.height - 4; im.paste(wm, (x, y), wm); bb = (x, y, x+wm.width, y+wm.height)
    rec(f'封面示意 {st["name"]} 不壓往右滑/副句、寬{wm.width}>=220、距右>=88、距下>=88', all(not hit(bb, o) for o in OTHER.values()) and wm.width >= 220 and 1080-bb[2] >= 88 and 1350-bb[3] >= 88)
    im.save(f'{FO(n)}/配合示意_封面右下角.png'); mocks.append((st, im, wm.size))
tw_, th_ = 360, 450; S3 = Image.new('RGB', (5*tw_ + 6*20, 2*(th_+50) + 80), '#1E1C22'); d3 = ImageDraw.Draw(S3)
d3.text((20, 22), '配合示意：10 款字標放在 01_cover_noperson 右下角，寬 224（≥220）、距邊≥88', font=F(26, True), fill='#EEE')
for i, (st, im, sz) in enumerate(mocks):
    x, y = 20 + (i % 5)*(tw_+20), 80 + (i//5)*(th_+50); S3.paste(im.resize((tw_, th_), Image.LANCZOS), (x, y+36)); d3.text((x, y), f'{st["n"]}. {st["name"]}（{sz[0]}×{sz[1]}）', font=F(20), fill='#DDD')
S3.save('配合示意_idea_封面右下角.png')
strip = Image.new('RGB', (520, N*82+8), '#222')
for i, (st, im, sz) in enumerate(mocks): strip.paste(im.crop((560, 1180, 1080, 1262)), (0, 4+i*82))
strip.save('配合示意_idea_右下角1比1.png')
json.dump(dict(程式檢查項數=len(rep['items']), 失敗=len(rep['fails']), 失敗明細=rep['fails'], 對比=cont, 全部=[(a, b) for a, b, c in rep['items']]), open('overlap_report.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('checks', len(rep['items']), 'fails', rep['fails'])
