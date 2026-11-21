# 後製：圓形頭像、程式檢查、總覽／色調／可讀性／配合示意
import json, os, glob
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
H = os.path.dirname(os.path.abspath(__file__)); os.chdir(H)
CHK = '/tmp/claude-0/-home-user-tw-rotation/ce50d787-1067-5482-ab44-99dc39a48890/scratchpad/rrxq2_chk'
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
ka1 = M[1]['ka']; ys, xs = np.nonzero(lay(1, 'b')); r_ = np.hypot(xs-539.5, ys-539.5)/ka1
rec(f'款1 「小」筆畫在太陽圓內且離圓線≥12（最遠 {r_.max():.0f}≤155；圓內緣167）', r_.max() <= 155)
rec('款2 上方日與水線間距≥6', gap_ok(lay(2, 'a'), lay(2, 'c'), 6))
rec('款2 倒影與水線間距≥6', gap_ok(lay(2, 'b'), lay(2, 'c'), 6))
rec('款5 車廂與光流間距≥16', gap_ok(lay(5, 'a'), lay(5, 'b'), 16))
rec('款7 雲帶與太陽間距≥16', gap_ok(lay(7, 'a'), lay(7, 'b'), 16))
rec('款9 塗鴉與膠帶全在手帳紙內以外無溢出（塗鴉出紙 0 px）', int((lay(9, 'b') & ~lay(9, 'a')).sum()) == 0)
rec('款12 光芒與電池間距≥16', gap_ok(lay(12, 'a'), lay(12, 'b'), 16))
rec('款6 太陽露出書頁的面積≥2000px（透光看得見）', int((lay(6, 'b') & ~lay(6, 'a')).sum()) >= 2000)
rec('款4 貓與陽光塊：陽光塊露出面積≥15000px', int((lay(4, 'b') & ~lay(4, 'a')).sum()) >= 15000)
for n in range(1, 13):
    a = mask(f'{CHK}/av{n}_all.png'); ys, xs = np.nonzero(a); ka = M[n]['ka']
    rec(f'款{n}符號在安全圓內（最遠{np.sqrt((xs-539.5)**2+(ys-539.5)**2).max():.0f}≤432）', np.sqrt((xs-539.5)**2+(ys-539.5)**2).max() <= 432)
# ---------- 4. 對比 ----------
for tag, P in TONES.items():
    rec(f'文字對比 {tag} 字:底 = {cr(P["ink"], P["bg"])}（≥4.5）', cr(P['ink'], P['bg']) >= 4.5)

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
d.text((G, 34), '「日日小晴」LOGO 第二輪 12 款（奶油晨光主色調，另有 5 種色調見 palette_rrxq2.png）', font=F(44, True), fill='#3A3A3A')
d.text((G, 100), '悠閒、溫和、帶希望：不求天天大晴，每天有一小段晴就好', font=F(28), fill='#5A5A5A')
for i, m in enumerate(meta):
    n = m['n']; x = G+(i % 4)*(TW+G); y = 150+G+(i//4)*(TH+G)
    d.rounded_rectangle((x, y, x+TW, y+TH), 28, fill='#FFFFFF', outline='#E8DFD0', width=2)
    a = av(n, '奶油晨光', 1080).resize((300, 300), Image.LANCZOS); paste(sheet, a, (x+30, y+30))
    for k, tg in enumerate(('晴空淡藍', '抹茶午後', '深色模式')):
        paste(sheet, av(n, tg, 110), (x+350, y+30+k*98)) if False else paste(sheet, av(n, tg, 110).resize((84, 84), Image.LANCZOS), (x+372, y+36+k*96))
    paste(sheet, av(n, '奶油晨光', 44), (x+372, y+36+3*96)); 
    w = Image.open(f'{m["dir"]}/字標含副標_奶油晨光.png').convert('RGB'); w = w.resize((TW-60, int(w.height*(TW-60)/w.width)), Image.LANCZOS); sheet.paste(w, (x+30, y+404))
    ty = y+404+w.height+22
    d.text((x+30, ty), f'{n:02d}　{m["name"]}', font=F(36, True), fill='#3A3A3A')
    d.text((x+30, ty+54), f'風格：{m["style"]}', font=F(24), fill='#B5651D')
    lines = wrap('含義：'+m['mean'], F(24), TW-60, d); rec(f'總覽含義不超格 款{n}（{len(lines)} 行）', len(lines) <= 4)
    for k, ln in enumerate(lines): d.text((x+30, ty+96+k*36), ln, font=F(24), fill='#3A3A3A')
    bottom = ty+96+len(lines)*36; rec(f'總覽文字在格內 款{n}（底{bottom}≤{y+TH-12}）', bottom <= y+TH-12)
sheet.save('contact_sheet_rrxq2.png')
# ---------- palette ----------
tags = list(TONES); CW, RH, LW = 230, 190, 300
pal = Image.new('RGB', (LW+6*CW+30, 280+12*RH+30), '#FFFFFF'); d = ImageDraw.Draw(pal)
d.text((30, 24), '「日日小晴」第二輪 12 款 × 6 色調', font=F(40, True), fill='#222222')
for c, tg in enumerate(tags):
    P = TONES[tg]; x = LW+c*CW; d.text((x, 90), tg, font=F(28, True), fill='#222222')
    for k, (nm, key) in enumerate((('底', 'bg'), ('太陽', 'S'), ('主', 'M'), ('淺', 'soft'), ('字', 'ink'), ('綠', 'G'), ('雲', 'C'))):
        d.rectangle((x+k*31, 138, x+k*31+26, 174), fill=P[key], outline='#999999'); 
    ks = ['bg', 'S', 'M', 'soft', 'ink', 'G', 'C']
    for r_, grp in enumerate((ks[:3], ks[3:5]+['T'], ks[5:7])): d.text((x, 180+r_*18), ' '.join(P[k] for k in grp), font=F(13), fill='#555555')
    if P.get('mono'): d.text((x, 236), '（單色：僅黑／白）', font=F(14), fill='#555555')
for i, m in enumerate(meta):
    y = 270+i*RH; d.text((20, y+70), f'{m["n"]:02d} {m["name"]}', font=F(26, True), fill='#222222')
    for c, tg in enumerate(tags):
        a = av(m['n'], tg, 1080).resize((150, 150), Image.LANCZOS); bgc = '#F1F1F1' if tg != '單色白' else '#F1F1F1'
        paste(pal, a, (LW+c*CW, y+10))
pal.save('palette_rrxq2.png')
# ---------- 可讀性 ----------
cols = [('奶油晨光', '#F5F5F5'), ('晴空淡藍', '#F5F5F5'), ('抹茶午後', '#F5F5F5'), ('深色模式', '#F5F5F5'), ('單色黑', '#F5F5F5'), ('單色白', '#F5F5F5'), ('奶油晨光', '#121212'), ('深色模式', '#121212'), ('單色白', '#121212')]
UW = 180; rd = Image.new('RGB', (260+len(cols)*UW+20, 130+12*128+20), '#F5F5F5'); d = ImageDraw.Draw(rd)
d.rectangle((260+6*UW, 0, rd.width, rd.height), fill='#121212')
d.text((20, 20), '可讀性：110px 與 44px 實際大小（左六欄淺色底；右三欄為 IG 深色模式底）', font=F(24, True), fill='#222222')
for c, (tg, b) in enumerate(cols): d.text((260+c*UW+8, 70), tg+('（深色底）' if b == '#121212' else ''), font=F(15), fill='#222222' if b != '#121212' else '#EEEEEE')
for i, m in enumerate(meta):
    y = 110+i*128; d.text((16, y+40), f'{m["n"]:02d} {m["name"]}', font=F(22, True), fill='#222222')
    for c, (tg, b) in enumerate(cols):
        paste(rd, av(m['n'], tg, 110), (260+c*UW+4, y+4)); paste(rd, av(m['n'], tg, 44), (260+c*UW+4+110+12, y+37))
rd.save('可讀性_rrxq2_110_44.png')
# ---------- 配合示意：放進封面模板左上角（圖示＋文字）----------
TPL = '../templates_rrxq/1_cover/1_cover_%s.png'; WMH = 0
def trim(im):
    a = np.array(im)[:, :, 3] > 20; ys, xs = np.nonzero(a); return im.crop((xs.min(), ys.min(), xs.max()+1, ys.max()+1))
def cover(n, tpl='cream', tone='奶油晨光'):
    im = Image.open(TPL % tpl).convert('RGB'); bgc = tuple(im.getpixel((20, 20)))
    d = ImageDraw.Draw(im); d.rectangle((90, 90, 330, 160), fill=bgc)      # 抹掉原本純文字字標（x102-256, y105-142）
    w = trim(Image.open(f'{M[n]["dir"]}/字標_透明_{tone}.png').convert('RGBA')); w = w.resize((int(w.width*.2), int(w.height*.2)), Image.LANCZOS)
    pos = (96, 120-w.height//2); im.paste(w, pos, w); wb = (pos[0], pos[1], pos[0]+w.width, pos[1]+w.height)
    return im, wb
tiles = []
for n in range(1, 13):
    im, wb = cover(n)
    # 不壓：頁碼「1／6」(x915-985,y105-142)、插畫上緣 y168、左緣 96
    rec(f'配合示意 款{n} 字標高{wb[3]-wb[1]}≥36、與插畫距≥12、與頁碼距≥100、左緣96', (wb[3]-wb[1]) >= 36 and 168-wb[3] >= 12 and wb[1] >= 60 and 915-wb[2] >= 100 and wb[0] == 96)
    tiles.append(im.crop((60, 60, 700, 200)))
for n, tpl, tone in ((3, 'cream', '奶油晨光'), (4, 'sky', '晴空淡藍'), (12, 'matcha', '抹茶午後')):
    cover(n, tpl, tone)[0].save(f'配合示意_rrxq2_整張封面_款{n:02d}_{tone}.png')
sh = Image.new('RGB', (2*640+3*20, 6*(140+56)+20), '#DDDDDD'); d = ImageDraw.Draw(sh)
for i, t in enumerate(tiles):
    x = 20+(i % 2)*(640+20); y = 20+(i//2)*(140+56); sh.paste(t, (x, y+40)); d.text((x, y+6), f'{i+1:02d} {M[i+1]["name"]}（封面左上角，字標比例 0.2，原尺寸裁切）', font=F(22, True), fill='#222222')
sh.save('配合示意_rrxq2_封面左上角.png')
json.dump(dict(items=rep['items'], fails=rep['fails'], total=len(rep['items'])), open('overlap_report.json', 'w'), ensure_ascii=False, indent=1)
print('檢查項目', len(rep['items']), '失敗', len(rep['fails']))
for f in rep['fails']: print('FAIL', f)
