# 後製：圓形頭像、程式檢查、總覽／色調／可讀性／配合示意
import json, os, glob
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
H = os.path.dirname(os.path.abspath(__file__)); os.chdir(H)
CHK = '/tmp/claude-0/-home-user-tw-rotation/ce50d787-1067-5482-ab44-99dc39a48890/scratchpad/rrxq_chk'
D = json.load(open('jobs.json', encoding='utf-8')); jobs, meta, TONES = D['jobs'], D['meta'], D['tones']
M = {m['n']: m for m in meta}
FD = os.path.expanduser('~/.fonts/')
def F(s, b=False, serif=False): return ImageFont.truetype(FD+('NotoSerifCJKtc-' if serif else 'NotoSansCJKtc-')+('Bold' if b else 'Regular')+'.otf', s)
def lum(h):
    h = h.lstrip('#'); c = [int(h[i:i+2], 16)/255 for i in (0, 2, 4)]
    c = [x/12.92 if x <= .03928 else ((x+.055)/1.055)**2.4 for x in c]; return .2126*c[0]+.7152*c[1]+.0722*c[2]
def cr(a, b): x, y = sorted([lum(a), lum(b)], reverse=True); return round((x+.05)/(y+.05), 2)
def rgb(h): return np.array([int(h[i:i+2], 16) for i in (1, 3, 5)])
def circ(im, n):
    big = im.convert('RGB').resize((n, n), Image.LANCZOS)
    m = Image.new('L', (n*4, n*4), 0); ImageDraw.Draw(m).ellipse((0, 0, n*4-1, n*4-1), fill=255); m = m.resize((n, n), Image.LANCZOS)
    o = Image.new('RGBA', (n, n), (0, 0, 0, 0)); o.paste(big, (0, 0), m); return o
def mask(p): return np.array(Image.open(p))[:, :, 3] > 20
def gap_ok(A, B, g):
    """A、B 兩個遮罩的最短距離 ≥ g 像素？（半解析度膨脹法）"""
    a = Image.fromarray((A*255).astype('uint8')); a = a.resize((a.width//2, a.height//2), Image.BOX).point(lambda v: 255 if v > 0 else 0)
    r = max(1, g//2); a = a.filter(ImageFilter.MaxFilter(2*r+1))
    b = Image.fromarray((B*255).astype('uint8')).resize(a.size, Image.BOX).point(lambda v: 255 if v > 0 else 0)
    return not (np.array(a) > 0)[np.array(b) > 0].any()
rep = dict(items=[], fails=[])
def rec(name, ok, detail=''):
    rep['items'].append((name, bool(ok), detail))
    if not ok: rep['fails'].append((name, detail))

# ---------- 1. 頭像圓形／110／44 ----------
for j in jobs:
    if j['kind'] != 'avatar': continue
    fo = M[j['n']]['dir']; tag = j['tag']; im = Image.open(j['png']).convert('RGB')
    circ(im, 1080).save(f'{fo}/頭像_1080圓_{tag}.png'); circ(im, 110).save(f'{fo}/頭像_110_{tag}.png'); circ(im, 44).save(f'{fo}/頭像_44_{tag}.png')
    P = TONES[tag]; bg = rgb(P['bg']); diff = np.abs(np.array(im).astype(int)-bg).max(axis=2) > 24; ys, xs = np.nonzero(diff)
    far = float(np.sqrt((xs-539.5)**2+(ys-539.5)**2).max())
    rec(f'安全圓864 款{j["n"]}{M[j["n"]]["name"]}{tag}（最遠{far:.0f}≤432）', far <= 432)
    if not P.get('mono'):
        cnt = int((np.abs(np.array(im).astype(int)-rgb(P['S'])).max(axis=2) < 30).sum()); rec(f'太陽色存在 款{j["n"]}{tag}（{cnt}px）', cnt > 300)
    # 字標圖像：符號不被裁（左右、上下留白）
# ---------- 2. 字標留白與間距 ----------
for n in range(1, 13):
    for sub in (False, True):
        sf = 's' if sub else ''; al = mask(f'{CHK}/wm{n}{sf}_all.png'); ys, xs = np.nonzero(al); Hh, W = al.shape
        mg = (xs.min(), W-1-xs.max(), ys.min(), Hh-1-ys.max())
        rec(f'字標留白≥30 款{n}{M[n]["name"]}{"含副標" if sub else ""}（左{mg[0]}右{mg[1]}上{mg[2]}下{mg[3]}）', min(mg) >= 30)
        L_ = {l: mask(f'{CHK}/wm{n}{sf}_{l}.png') for l in ('sym', 'sym2', 'txt', 'sub') if os.path.exists(f'{CHK}/wm{n}{sf}_{l}.png')}
        if 'sym' in L_ and 'txt' in L_: rec(f'字標符號與字間距≥24 款{n}{"含副標" if sub else ""}', gap_ok(L_['sym'], L_['txt'], 24))
        if 'sym2' in L_: rec(f'字標波浪線與字間距≥10 款{n}{"含副標" if sub else ""}', gap_ok(L_['sym2'], L_['txt'], 10))
        if 'sub' in L_: rec(f'字標副標與主字間距≥16 款{n}', gap_ok(L_['sub'], L_['txt'], 16))
        if 'sub' in L_ and 'sym' in L_: rec(f'字標副標與符號間距≥16 款{n}', gap_ok(L_['sub'], L_['sym'], 16))
        if 'sub' in L_ and 'sym2' in L_: rec(f'字標副標與波浪線間距≥12 款{n}', gap_ok(L_['sub'], L_['sym2'], 12))
# ---------- 3. 符號內部配對 ----------
def lay(n, l): return mask(f'{CHK}/av{n}_{l}.png')
rec('款4 太陽與青字間距≥16', gap_ok(lay(4, 'a'), lay(4, 'b'), 16))
rec('款8 傘與太陽間距≥14', gap_ok(lay(8, 'a'), lay(8, 'b'), 14))
ys, xs = np.nonzero(lay(10, 'b')); r_ = np.hypot(xs-539.5, ys-539.5)/M[10]['ka']
rec(f'款10 環字距內圈線≥8、距外圈線≥8（字帶 {r_.min():.0f}～{r_.max():.0f}；內圈外緣194、外圈內緣282）', r_.min()-194 >= 8 and 282-r_.max() >= 8)
rec('款11 手繪太陽與晴字間距≥14', gap_ok(lay(11, 'a'), lay(11, 'b'), 14))
rec('款11 波浪線與晴字間距≥10', gap_ok(lay(11, 'c'), lay(11, 'b'), 10))
# 款9：四個字都在內框內（內框內緣單位 ±232；單位 = (px-540)/ka）
ka = M[9]['ka']; t = lay(9, 'b'); ys, xs = np.nonzero(t); ext = max(abs((xs-539.5)).max(), abs((ys-539.5)).max())/ka
rec(f'款9 印面字距內框≥14（字最遠 {ext:.0f}≤218）', ext <= 218)
# 款9：四字兩兩間距
for n in range(1, 13):
    a = mask(f'{CHK}/av{n}_all.png'); ys, xs = np.nonzero(a); ka = M[n]['ka']
    rec(f'款{n}符號在安全圓內（最遠{np.sqrt((xs-539.5)**2+(ys-539.5)**2).max():.0f}≤432）', np.sqrt((xs-539.5)**2+(ys-539.5)**2).max() <= 432)
# ---------- 4. 對比 ----------
for tag, P in TONES.items():
    rec(f'文字對比 {tag} 字:底 = {cr(P["ink"], P["bg"])}（≥4.5）', cr(P['ink'], P['bg']) >= 4.5)
    if not P.get('mono'): rec(f'印面字對比 {tag} 字:太陽色 = {cr(P["ink"], P["S"])}（≥4.5）', cr(P['ink'], P['S']) >= 4.5)

# ---------- 5. 圓形頭像總覽圖共用素材 ----------
def av(n, tag, s): return Image.open(f'{M[n]["dir"]}/頭像_{s}_{tag}.png').convert('RGBA') if s != 1080 else Image.open(f'{M[n]["dir"]}/頭像_1080圓_{tag}.png').convert('RGBA')
def paste(canvas, im, xy): canvas.paste(im, xy, im)
def wrap(txt, font, wmax, d):
    lines, cur = [], ''
    for ch in txt:
        if d.textlength(cur+ch, font=font) > wmax: lines.append(cur); cur = ch
        else: cur += ch
    return lines+[cur]
# ---------- contact_sheet ----------
TW, TH, G = 520, 860, 30
sheet = Image.new('RGB', (4*TW+5*G, 3*TH+4*G+150), '#FBF7F0'); d = ImageDraw.Draw(sheet)
d.text((G, 34), '「日日小晴」LOGO 12 款（奶油晨光主色調，另有 5 種色調見 palette_rrxq.png）', font=F(44, True), fill='#3A3A3A')
d.text((G, 100), '悠閒、溫和、帶希望：不求天天大晴，每天有一小段晴就好', font=F(28), fill='#5A5A5A')
for i, m in enumerate(meta):
    n = m['n']; x = G+(i % 4)*(TW+G); y = 150+G+(i//4)*(TH+G)
    d.rounded_rectangle((x, y, x+TW, y+TH), 28, fill='#FFFFFF', outline='#E8DFD0', width=2)
    a = av(n, '奶油晨光', 1080).resize((300, 300), Image.LANCZOS); paste(sheet, a, (x+30, y+30))
    for k, tg in enumerate(('晴空淡藍', '抹茶午後', '蜜桃傍晚')):
        paste(sheet, av(n, tg, 110), (x+350, y+30+k*98)) if False else paste(sheet, av(n, tg, 110).resize((84, 84), Image.LANCZOS), (x+372, y+36+k*96))
    paste(sheet, av(n, '奶油晨光', 44), (x+372, y+36+3*96)); 
    w = Image.open(f'{m["dir"]}/字標含副標_奶油晨光.png').convert('RGB'); w = w.resize((TW-60, int(w.height*(TW-60)/w.width)), Image.LANCZOS); sheet.paste(w, (x+30, y+404))
    ty = y+404+w.height+22
    d.text((x+30, ty), f'{n:02d}　{m["name"]}', font=F(36, True), fill='#3A3A3A')
    d.text((x+30, ty+54), f'風格：{m["style"]}', font=F(24), fill='#B5651D')
    lines = wrap('含義：'+m['mean'], F(24), TW-60, d); rec(f'總覽含義不超格 款{n}（{len(lines)} 行）', len(lines) <= 4)
    for k, ln in enumerate(lines): d.text((x+30, ty+96+k*36), ln, font=F(24), fill='#3A3A3A')
    bottom = ty+96+len(lines)*36; rec(f'總覽文字在格內 款{n}（底{bottom}≤{y+TH-12}）', bottom <= y+TH-12)
sheet.save('contact_sheet_rrxq.png')
# ---------- palette ----------
tags = list(TONES); CW, RH, LW = 230, 190, 300
pal = Image.new('RGB', (LW+6*CW+30, 280+12*RH+30), '#FFFFFF'); d = ImageDraw.Draw(pal)
d.text((30, 24), '「日日小晴」12 款 × 6 色調', font=F(40, True), fill='#222222')
for c, tg in enumerate(tags):
    P = TONES[tg]; x = LW+c*CW; d.text((x, 90), tg, font=F(28, True), fill='#222222')
    for k, (nm, key) in enumerate((('底', 'bg'), ('太陽', 'S'), ('主', 'M'), ('淺', 'soft'), ('字', 'ink'))):
        d.rectangle((x+k*42, 138, x+k*42+36, 174), fill=P[key], outline='#999999'); 
    d.text((x, 182), f'{P["bg"]} {P["S"]}', font=F(14), fill='#555555'); d.text((x, 202), f'{P["M"]} {P["ink"]}', font=F(14), fill='#555555')
    if P.get('mono'): d.text((x, 226), '（單色：僅黑／白）', font=F(14), fill='#555555')
for i, m in enumerate(meta):
    y = 270+i*RH; d.text((20, y+70), f'{m["n"]:02d} {m["name"]}', font=F(26, True), fill='#222222')
    for c, tg in enumerate(tags):
        a = av(m['n'], tg, 1080).resize((150, 150), Image.LANCZOS); bgc = '#F1F1F1' if tg != '單色白' else '#F1F1F1'
        paste(pal, a, (LW+c*CW, y+10))
pal.save('palette_rrxq.png')
# ---------- 可讀性 ----------
cols = [('奶油晨光', '#F5F5F5'), ('晴空淡藍', '#F5F5F5'), ('抹茶午後', '#F5F5F5'), ('蜜桃傍晚', '#F5F5F5'), ('單色黑', '#F5F5F5'), ('單色白', '#F5F5F5'), ('奶油晨光', '#121212'), ('單色白', '#121212')]
UW = 180; rd = Image.new('RGB', (260+len(cols)*UW+20, 130+12*128+20), '#F5F5F5'); d = ImageDraw.Draw(rd)
d.rectangle((260+6*UW, 0, rd.width, rd.height), fill='#121212')
d.text((20, 20), '可讀性：110px 與 44px 實際大小（左六欄淺色底；右兩欄為 IG 深色模式底）', font=F(24, True), fill='#222222')
for c, (tg, b) in enumerate(cols): d.text((260+c*UW+8, 70), tg+('（深色底）' if b == '#121212' else ''), font=F(15), fill='#222222' if b != '#121212' else '#EEEEEE')
for i, m in enumerate(meta):
    y = 110+i*128; d.text((16, y+40), f'{m["n"]:02d} {m["name"]}', font=F(22, True), fill='#222222')
    for c, (tg, b) in enumerate(cols):
        paste(rd, av(m['n'], tg, 110), (260+c*UW+4, y+4)); paste(rd, av(m['n'], tg, 44), (260+c*UW+4+110+12, y+37))
rd.save('可讀性_rrxq_110_44.png')
# ---------- 配合示意：淺色底封面右下角 ----------
CW_, CH_ = 1080, 1350
def cover(n):
    im = Image.new('RGB', (CW_, CH_), '#FFFDF8'); d = ImageDraw.Draw(im)
    boxes = []
    for txt, y, f, col in (('週五午後', 360, F(110, True, True), '#3A3A3A'), ('窗邊多了一小段陽光', 500, F(86, True, True), '#3A3A3A'), ('慢慢來，今天也算數。', 660, F(44), '#6B6B6B')):
        d.text((80, y), txt, font=f, fill=col); bb = d.textbbox((80, y), txt, font=f); boxes.append(bb)
    d.rounded_rectangle((80, 280, 200, 292), 6, fill='#F2A65A')
    w = Image.open(f'{M[n]["dir"]}/字標_透明_奶油晨光.png').convert('RGBA'); tw = 300; w = w.resize((tw, int(w.height*tw/w.width)), Image.LANCZOS)
    pos = (CW_-60-tw, CH_-60-w.height); im.paste(w, pos, w); wb = (pos[0], pos[1], pos[0]+tw, pos[1]+w.height)
    return im, boxes, wb
tiles = []
for n in range(1, 13):
    im, boxes, wb = cover(n)
    hit = any(not (wb[2] <= b[0] or b[2] <= wb[0] or wb[3] <= b[1] or b[3] <= wb[1]) for b in boxes)
    rec(f'配合示意 款{n} 字標寬{wb[2]-wb[0]}≥220 且不壓封面文字', (wb[2]-wb[0]) >= 220 and not hit)
    if n == 1: im.save('配合示意_rrxq_整張封面範例.png')
    tiles.append(im.crop((420, 1000, 1080, 1350)))
sh = Image.new('RGB', (3*660+4*20, 4*(350+60)+20), '#DDDDDD'); d = ImageDraw.Draw(sh)
for i, t in enumerate(tiles):
    x = 20+(i % 3)*(660+20); y = 20+(i//3)*(350+60); sh.paste(t, (x, y+50)); d.text((x, y+8), f'{i+1:02d} {M[i+1]["name"]}（字標寬 300px，原尺寸裁切）', font=F(24, True), fill='#222222')
sh.save('配合示意_rrxq_封面右下角.png')
json.dump(dict(items=rep['items'], fails=rep['fails'], total=len(rep['items'])), open('overlap_report.json', 'w'), ensure_ascii=False, indent=1)
print('檢查項目', len(rep['items']), '失敗', len(rep['fails']))
for f in rep['fails']: print('FAIL', f)
