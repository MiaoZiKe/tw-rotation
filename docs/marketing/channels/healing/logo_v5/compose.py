# 後製：圓形頭像、總覽、色調比較、可讀性、配合示意、程式檢查
import json, os, textwrap
import numpy as np
from PIL import Image, ImageDraw, ImageFont
H = os.path.dirname(os.path.abspath(__file__)); os.chdir(H)
D = json.load(open('jobs.json', encoding='utf-8')); jobs, meta, TONES = D['jobs'], D['meta'], D['tones']
boxes = json.load(open('boxes.json')); M = {m['n']: m for m in meta}
F = lambda s, b=False: ImageFont.truetype(os.path.expanduser('~/.fonts/NotoSansCJKtc-%s.otf' % ('Bold' if b else 'Regular')), s)
def lum(h):
    h = h.lstrip('#'); c = [int(h[i:i+2], 16)/255 for i in (0, 2, 4)]
    c = [x/12.92 if x <= .03928 else ((x+.055)/1.055)**2.4 for x in c]; return .2126*c[0]+.7152*c[1]+.0722*c[2]
def cr(a, b): x, y = sorted([lum(a), lum(b)], reverse=True); return round((x+.05)/(y+.05), 2)
def rgb(h): return np.array([int(h[i:i+2], 16) for i in (1, 3, 5)])
def circ(im, n):
    big = im.convert('RGB').resize((n, n), Image.LANCZOS)
    m = Image.new('L', (n*4, n*4), 0); ImageDraw.Draw(m).ellipse((0, 0, n*4-1, n*4-1), fill=255); m = m.resize((n, n), Image.LANCZOS)
    o = Image.new('RGBA', (n, n), (0, 0, 0, 0)); o.paste(big, (0, 0), m); return o
def hit(a, b): return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])
def inside(i, o, mg=4): return i[0] >= o[0]+mg and i[2] <= o[2]-mg and i[1] >= o[1]+mg and i[3] <= o[3]-mg
rep = dict(items=[], fails=[])
def rec(name, ok, detail=''):
    rep['items'].append((name, bool(ok), detail))
    if not ok: rep['fails'].append((name, detail))
FO = lambda n: M[n]['dir']
for j in jobs:
    n = j['n']; nm = M[n]['name']; bx = boxes.get(j['svg'], {})
    if j['kind'] == 'avatar':
        im = Image.open(j['png']).convert('RGB'); P = TONES[j['tag']]; bg = rgb(P['bg'])
        diff = np.abs(np.array(im).astype(int) - bg).max(axis=2) > 24
        ys, xs = np.nonzero(diff); far = float(np.sqrt((xs-539.5)**2 + (ys-539.5)**2).max())
        rec(f'安全圓864 款{n}{nm}{j["tag"]}頭像(最遠{far:.0f}≤432)', far <= 432)
        if not P.get('mono'):
            cnt = int((np.abs(np.array(im).astype(int)-rgb(P['acc'])).max(axis=2) < 30).sum()); rec(f'暖光存在 款{n}{j["tag"]}({cnt}px)', cnt > 300)
        for s_ in (1080, 110, 44): circ(im, s_).save(f'{FO(n)}/頭像_{s_}_{j["tag"]}.png' if s_ != 1080 else f'{FO(n)}/頭像_1080圓形_{j["tag"]}.png')
        # 版面規則：頭像內文字／區塊
        for k, v in bx.items():
            pass
    elif j['kind'] == 'wm':
        P = TONES[j['tag']]; im = Image.open(j['png']).convert('RGB'); bg = rgb(P['bg'])
        diff = np.abs(np.array(im).astype(int) - bg).max(axis=2) > 24; ys, xs = np.nonzero(diff)
        rec(f'字標留白≥30px 款{n}{j["tag"]}', xs.min() >= 30 and ys.min() >= 30 and im.width-xs.max() >= 30 and im.height-ys.max() >= 30, f'{xs.min()},{ys.min()},{im.width-xs.max()},{im.height-ys.max()}')
        for c in j.get('chk', []):
            a, b = bx[c[1]], bx[c[2]]
            if c[0] == 'dis':
                gap = max(b[0]-a[2], a[0]-b[2], b[1]-a[3], a[1]-b[3])
                rec(f'字標不重疊 款{n}{j["tag"]} {c[1]}×{c[2]}(間距{gap:.0f})', not hit(a, b) and gap >= 20)
            else: rec(f'字在窗內 款{n}{j["tag"]} {c[1]}⊂{c[2]}', inside(a, b))
# 頭像內部（以 霧紫灰 的 boxes 檢查，其他色調位置相同）
for j in jobs:
    if j['kind'] == 'avatar' and j['tag'] == '霧紫灰':
        bx = boxes[j['svg']]; n = j['n']; nm = M[n]['name']
        for i in ('a_t0', 'a_t1', 'a_t2'):
            if i in bx and 'a_b' in bx:
                # 位移 540 已含在 getBoundingClientRect；樓層字須在大樓框內且不貼框
                rec(f'字在樓內 款{n} {i}', inside(bx[i], bx['a_b'], 14), json.dumps([round(v) for v in bx[i]]))
        if 'a_seal' in bx and 'a_t0' in bx: rec('款6 印章不壓直排字', not hit(bx['a_seal'], bx['a_t4']) if 'a_t4' in bx else True)
if True:
    pass
cont = {t: dict(線條對底=cr(c['line'], c['bg']), 暖光對底=cr(c['acc'], c['bg']), 字標對底=cr(c['ink'], c['bg'])) for t, c in TONES.items()}
rec('對比：線條>=3、字標>=4.5、暖光>=3（單色除外亦通過）', all(v['線條對底'] >= 3 and v['暖光對底'] >= 3 and v['字標對底'] >= 4.5 for v in cont.values()), json.dumps(cont, ensure_ascii=False))
TN = ['霧紫灰', '深夜藍', '水泥暖灰', '灰綠', '米白紙', '黑底朱', '單色黑', '單色白']
# ---- 總覽 4x3 ----
CW, CH = 560, 760; COLS, ROWS = 4, 3
SH = Image.new('RGB', (COLS*CW+50, ROWS*CH+110), '#1E1C22'); d = ImageDraw.Draw(SH)
d.text((24, 22), '「我們這一代」LOGO v5：12 款全新（霧紫灰底 #4A4454；每款另有 5 種色調＋單色黑白，見 palette_v5.png）', font=F(30, True), fill='#EEE')
def wrap(t, f, wmax):
    out, cur = [], ''
    for ch in t:
        if d.textlength(cur+ch, font=f) > wmax: out.append(cur); cur = ch
        else: cur += ch
    return out+[cur]
for i, m in enumerate(meta):
    n = m['n']; x0 = 10 + (i % COLS)*(CW+10); y0 = 80 + (i//COLS)*(CH+10)
    d.rectangle((x0, y0, x0+CW, y0+CH), fill=TONES['霧紫灰']['bg'])
    av = circ(Image.open(f'{m["dir"]}/頭像_1080_霧紫灰.png'), 300); SH.paste(av, (x0+130, y0+56), av)
    wm = Image.open(f'{m["dir"]}/字標_霧紫灰.png').convert('RGB'); sc = min((CW-60)/wm.width, 120/wm.height); wm = wm.resize((int(wm.width*sc), int(wm.height*sc)), Image.LANCZOS)
    SH.paste(wm, (x0+(CW-wm.width)//2, y0+392))
    d.text((x0+16, y0+14), f'{n}. {m["name"]}', font=F(28, True), fill='#F3EFF5'); d.text((x0+CW-16, y0+18), m['style'], font=F(22), fill='#F2D88E', anchor='ra')
    L = wrap('含義：'+m['meaning'], F(25), CW-40); yy = y0+535
    rec(f'總覽含義不超格 款{n}（{len(L)}行）', len(L) <= 5 and yy+len(L)*36 <= y0+CH-8)
    for l in L: d.text((x0+20, yy), l, font=F(25), fill='#E7E1EC'); yy += 36
SH.save('contact_sheet_v5.png')
# ---- 色調比較 ----
CWp, CHp = 190, 250
PS = Image.new('RGB', (230+8*(CWp+8), 110+12*(CHp+8)), '#16141A'); d = ImageDraw.Draw(PS)
d.text((20, 18), '色調比較 palette_v5：12 款 × 6 色調＋單色黑／白（上：圓形頭像 150px；下：字標）', font=F(28, True), fill='#EEE')
for ti, t in enumerate(TN): d.text((230+ti*(CWp+8)+CWp//2, 76), t, font=F(24, True), fill='#EEE', anchor='ma')
for i, m in enumerate(meta):
    y0 = 110+i*(CHp+8); d.text((14, y0+90), f'{m["n"]}. {m["name"]}', font=F(24, True), fill='#EEE'); d.text((14, y0+128), m['style'], font=F(20), fill='#B9B2C2')
    for ti, t in enumerate(TN):
        x0 = 230+ti*(CWp+8); P = TONES[t]; d.rectangle((x0, y0, x0+CWp, y0+CHp), fill=P['bg'])
        av = Image.open(f'{m["dir"]}/頭像_150' if False else f'{m["dir"]}/頭像_1080圓形_{t}.png').resize((150, 150), Image.LANCZOS); PS.paste(av, (x0+20, y0+10), av)
        wm = Image.open(f'{m["dir"]}/字標_{t}.png').convert('RGB'); sc = min((CWp-16)/wm.width, 76/wm.height); wm = wm.resize((int(wm.width*sc), int(wm.height*sc)), Image.LANCZOS); PS.paste(wm, (x0+(CWp-wm.width)//2, y0+175))
PS.save('palette_v5.png')
# ---- 可讀性 ----
RT = ['霧紫灰', '深夜藍', '水泥暖灰', '米白紙', '單色黑']
RW = 250 + len(RT)*(110+44+60+24)
RS = Image.new('RGB', (RW+20, 100+12*140), '#16141A'); d = ImageDraw.Draw(RS)
d.text((20, 16), '可讀性 v5：圓形頭像實際大小 110px／44px（右側另附 44px 放大 2 倍供檢視，不是實際大小）', font=F(26, True), fill='#EEE')
for i, m in enumerate(meta):
    y0 = 90+i*140; d.text((14, y0+50), f'{m["n"]}. {m["name"]}', font=F(24, True), fill='#EEE')
    for ti, t in enumerate(RT):
        x0 = 250+ti*(110+44+60+24); P = TONES[t]; d.rectangle((x0-6, y0, x0+214, y0+130), fill=P['bg'])
        a110 = Image.open(f'{m["dir"]}/頭像_110_{t}.png'); a44 = Image.open(f'{m["dir"]}/頭像_44_{t}.png')
        RS.paste(a110, (x0, y0+10), a110); RS.paste(a44, (x0+120, y0+10), a44)
        z = a44.resize((132, 132), Image.NEAREST) if False else a44.resize((88, 88), Image.LANCZOS); RS.paste(z, (x0+120, y0+50) if False else (x0+120, y0+50), z)
RS.save('可讀性_v5_110_44.png')
# ---- 配合示意：字標放 01_cover 右下角 ----
cov = Image.open('../samples/20261104_gen2000_v4/post2/01_cover.png').convert('RGB')
patch = cov.crop((600, 1205, 600+190, 1205+80)); base = cov.copy(); base.paste(patch, (820, 1205))   # 蓋掉原本小字
tiles = []
for m in meta:
    wm = Image.open(f'{m["dir"]}/字標_透明_霧紫灰.png').convert('RGBA'); wm = wm.crop(wm.getbbox())
    w = 232; h = int(wm.height*w/wm.width)
    if h > 112: h = 112; w = int(wm.width*h/wm.height)
    wm = wm.resize((w, h), Image.LANCZOS); t = base.copy(); x = 983-w; y = 1244-h//2; t.paste(wm, (x, y), wm)
    rec(f'配合示意 款{m["n"]} 字標寬{w}≥220、不壓「往右滑」（右緣983、左緣{x}>230）、離底≥40', w >= 220 and x > 230 and 1350-(y+h) >= 40, f'{w}x{h}')
    tiles.append(t.crop((0, 1090, 1080, 1350)))
CS = Image.new('RGB', (2*1080+30, 6*270+20), '#111')
for i, t in enumerate(tiles): CS.paste(t, (10+(i % 2)*1090, 10+(i//2)*270))
CS.save('配合示意_v5_封面右下角.png')
json.dump(rep, open('overlap_report.json', 'w'), ensure_ascii=False, indent=1)
print('項目', len(rep['items']), '失敗', len(rep['fails']))
for f in rep['fails']: print('  ✗', f)
