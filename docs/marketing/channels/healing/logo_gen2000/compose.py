# 後製：圓形頭像（1080／110／44）、總覽、配合示意、程式檢查（重疊／安全圓／對比）。
import json, os
from PIL import Image, ImageDraw, ImageFont
H = os.path.dirname(os.path.abspath(__file__)); os.chdir(H)
D = json.load(open('jobs.json', encoding='utf-8')); jobs, logos, PAL = D['jobs'], D['logos'], D['pal']
boxes = json.load(open('boxes.json'))
SW, SC = 9, 3.0
F = lambda s, b=False: ImageFont.truetype(os.path.expanduser('~/.fonts/NotoSans%sCJKtc-%s.otf' % ('', 'Bold' if b else 'Regular')), s)
def lum(h):
    h = h.lstrip('#'); c = [int(h[i:i+2], 16)/255 for i in (0, 2, 4)]
    c = [x/12.92 if x <= .03928 else ((x+.055)/1.055)**2.4 for x in c]; return .2126*c[0]+.7152*c[1]+.0722*c[2]
def cr(a, b): x, y = sorted([lum(a), lum(b)], reverse=True); return round((x+.05)/(y+.05), 2)
def circ(im, n):
    big = im.convert('RGB').resize((n, n), Image.LANCZOS)
    m = Image.new('L', (n*4, n*4), 0); ImageDraw.Draw(m).ellipse((0, 0, n*4-1, n*4-1), fill=255); m = m.resize((n, n), Image.LANCZOS)
    o = Image.new('RGBA', (n, n), (0, 0, 0, 0)); o.paste(big, (0, 0), m); return o
report = dict(overlap=[], safe=[], contrast={}, checked=0)
def hit(a, b): return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])
# 1) 圓形輸出＋ 字標／頭像 檢查
for j in jobs:
    base = j['png'][:-4]; bx = boxes[j['svg']]
    if j['kind'] == 'avatar':
        im = Image.open(j['png']); circ(im, 1080).save(base + '_圓形1080.png'); circ(im, 110).save(base + '_110圓形.png'); circ(im, 44).save(base + '_44圓形.png')
        s = bx['sym']; hw = SW*SC/2; s = [s[0]-hw, s[1]-hw, s[2]+hw, s[3]+hw]
        far = max(((x-540)**2+(y-540)**2)**.5 for x in (s[0], s[2]) for y in (s[1], s[3]))
        report['safe'].append((base, round(far), far <= 432)); report['checked'] += 1
    elif j['kind'] in ('wm', 'cover'):
        s, t = bx['sym'], bx['nm']; fs = j['fs']; gap = t[0]-s[2]
        ok = (not hit(s, t)) and gap >= 0.25*fs
        report['overlap'].append((base, round(gap, 1), round(0.25*fs, 1), ok)); report['checked'] += 1
for k, name, d, c in logos: pass
for t, c in PAL.items():
    report['contrast'][t] = dict(線條對底=cr(c['line'], c['bg']), 燈對底=cr(c['lamp'], c['bg']), 字標對底=cr(c['ink'], c['bg']))
def P(k, kind, tag, suf=''):
    for k0, name, d, _ in logos:
        if k0 == k: return f'{k}_{name.replace(" ", "")}_{d}/{k}_{kind}_{tag}{suf}.png'
# 2) 總覽
TAGS = ['④霧紫灰', '⑤水泥暖灰', '①灰藍夜']
LW, AV, WMW, PADX, RH = 250, 170, 330, 20, 200
BW = PADX + AV + 16 + WMW + PADX
SW_, SH_ = LW + 3*BW + 40, 110 + 8*RH + 30
sh = Image.new('RGB', (SW_, SH_), '#1E1C22'); dr = ImageDraw.Draw(sh); rects = []
dr.text((24, 24), '2000 後頻道 LOGO 總覽（8 款 × 三底色 × 頭像／字標）', font=F(30, True), fill='#EEE')
for i, t in enumerate(TAGS):
    dr.text((LW + i*BW + 10, 74), t + '  底 ' + PAL[t]['bg'], font=F(20), fill='#BBB')
for r, (k, name, d, _) in enumerate(logos):
    y0 = 110 + r*RH
    dr.text((20, y0 + 60), f'{k.upper()} {d}', font=F(26, True), fill='#EEE'); dr.text((20, y0 + 100), name, font=F(22), fill='#BBB')
    for i, t in enumerate(TAGS):
        x0 = LW + i*BW; blk = (x0, y0 + 6, x0 + BW - 8, y0 + RH - 6)
        dr.rectangle(blk, fill=PAL[t]['bg'])
        av = circ(Image.open(P(k, '頭像', t)), AV - 10); ax, ay = x0 + PADX, y0 + (RH - (AV - 10))//2; sh.paste(av, (ax, ay), av)
        wm = Image.open(P(k, '字標', t)).convert('RGB'); sc = min((WMW - 10)/wm.width, 100/wm.height); wm = wm.resize((int(wm.width*sc), int(wm.height*sc)), Image.LANCZOS)
        wx, wy = x0 + PADX + AV + 16, y0 + (RH - wm.height)//2; sh.paste(wm, (wx, wy))
        a, w = (ax, ay, ax + AV - 10, ay + AV - 10), (wx, wy, wx + wm.width, wy + wm.height)
        for q in (a, w):
            if not (blk[0] <= q[0] and q[2] <= blk[2] and blk[1] <= q[1] and q[3] <= blk[3]): report['overlap'].append((f'總覽{k}{t}超出格', 0, 0, False))
        report['overlap'].append((f'總覽{k}{t}頭像vs字標', 0, 0, not hit(a, w))); report['checked'] += 1
sh.save('contact_sheet.png')
# 3) 單色與可讀性
CW = 150
S2 = Image.new('RGB', (230 + 3*(2*CW + 380) + 20, 110 + 8*150 + 20), '#1E1C22'); d2 = ImageDraw.Draw(S2)
d2.text((24, 24), '單色白／單色黑與 110px／44px 可讀性（④底為參照）', font=F(28, True), fill='#EEE')
for i, t in enumerate(['④霧紫灰', '單色白', '單色黑']):
    d2.text((230 + i*(2*CW + 380) + 10, 74), t + '：頭像 110／44 ＋ 字標', font=F(20), fill='#BBB')
for r, (k, name, d, _) in enumerate(logos):
    y0 = 110 + r*150; d2.text((20, y0 + 50), f'{k.upper()} {d}', font=F(24, True), fill='#EEE')
    for i, t in enumerate(['④霧紫灰', '單色白', '單色黑']):
        x0 = 230 + i*(2*CW + 380); bg = PAL[t]['bg']; d2.rectangle((x0, y0 + 4, x0 + 2*CW + 370, y0 + 146), fill=bg)
        a = Image.open(P(k, '頭像', t, '_110圓形')); S2.paste(a, (x0 + 20, y0 + 20), a)
        b = Image.open(P(k, '頭像', t, '_44圓形')); S2.paste(b, (x0 + 20 + 110 + 24, y0 + 53), b)
        wm = Image.open(P(k, '字標', t)).convert('RGB'); sc = min(320/wm.width, 100/wm.height); wm = wm.resize((int(wm.width*sc), int(wm.height*sc)), Image.LANCZOS); S2.paste(wm, (x0 + 2*CW + 20, y0 + 25))
S2.save('contact_sheet_單色與可讀性110_44.png')
# 4) 配合示意：放進 post2/01_cover.png 右下角
cov = Image.open('../samples/20261104_gen2000_v2/post2/01_cover.png').convert('RGB')
patch = cov.crop((790, 1165, 995, 1213)); cov.paste(patch, (790, 1220))
base = cov.copy(); mocks = []
OTHER = {'往右滑': (97, 1226, 220, 1262), '副句': (97, 1108, 512, 1150)}
for k, name, d, _ in logos:
    p = P(k, '字標', '封面用_透明'); wm = Image.open(p).convert('RGBA'); wm = wm.crop(wm.getbbox())
    im = base.copy(); x = 983 - wm.width; y = 1243 - wm.height//2; im.paste(wm, (x, y), wm)
    bb = (x, y, x + wm.width, y + wm.height); ok = all(not hit(bb, o) for o in OTHER.values()) and bb[0] >= 97 and bb[2] <= 983 + 1
    report['overlap'].append((f'封面示意{k}', 0, 0, ok)); report['checked'] += 1
    im.save(f'cover_mock_{k}.png'); mocks.append((k, name, d, im))
tw_, th_ = 540, 675; S3 = Image.new('RGB', (4*tw_ + 5*20, 2*(th_ + 56) + 70), '#1E1C22'); d3 = ImageDraw.Draw(S3)
d3.text((20, 20), '配合示意：字標替換封面右下「頻道名稱待定」（④霧紫灰）', font=F(28, True), fill='#EEE')
for i, (k, name, d, im) in enumerate(mocks):
    x, y = 20 + (i % 4)*(tw_ + 20), 70 + (i//4)*(th_ + 56); S3.paste(im.resize((tw_, th_), Image.LANCZOS), (x, y + 30)); d3.text((x, y), f'{k.upper()} {name}／{d}', font=F(20), fill='#DDD')
S3.save('配合示意_封面右下角.png')
# 封面右下角放大對照（1:1 裁切）
strip = Image.new('RGB', (520, 8*70 + 10), '#222'); 
for i, (k, n_, d_, im) in enumerate(mocks): strip.paste(im.crop((560, 1205, 1080, 1275)), (0, 5 + i*70))
strip.save('配合示意_右下角1比1.png')
bad = [o for o in report['overlap'] if not o[3]] + [s for s in report['safe'] if not s[2]]
json.dump(dict(checked=report['checked'], failures=len(bad), 失敗明細=bad, 安全圓=report['safe'], 字標間距=report['overlap'], 對比=report['contrast']), open('overlap_report.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('checked', report['checked'], 'fail', len(bad), bad); print(json.dumps(report['contrast'], ensure_ascii=False))
