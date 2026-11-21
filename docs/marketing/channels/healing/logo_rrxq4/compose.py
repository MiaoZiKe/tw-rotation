# 後製：圓形頭像、程式檢查、總覽／色調／可讀性／配合示意
import json, os, glob
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
H = os.path.dirname(os.path.abspath(__file__)); os.chdir(H)
CHK = '/tmp/claude-0/-home-user-tw-rotation/ce50d787-1067-5482-ab44-99dc39a48890/scratchpad/rrxq4_chk'
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
    circ(im, 1080).save(f'{fo}/頭像_1080圓_{tag}.png')
    sm = Image.open(f'{fo}/頭像_簡化小圖版1080方_{tag}.png').convert('RGB')
    circ(sm, 1080).save(f'{fo}/頭像_簡化小圖版1080圓_{tag}.png'); circ(sm, 110).save(f'{fo}/頭像_110_{tag}.png'); circ(sm, 44).save(f'{fo}/頭像_44_{tag}.png')
    circ(im, 110).save(f'{fo}/頭像_110完整版_{tag}.png')
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
# ---------- 3. 符號內部配對（各款自己的圖層：圖示／文字／標記兩兩不相交；刻意的前後遮擋見 README）----------
def lay(n, l): return mask(f'{CHK}/av{n}_{l}.png')
def G(n, a, b, g): rec(f'款{n} 圖層{a}與{b}間距≥{g}', gap_ok(lay(n, a), lay(n, b), g))
def IN(n, a, b, m): rec(f'款{n} 圖層{a}全在{b}內且離邊≥{m}', int((lay(n, a) & ~lay(n, b)).sum()) == 0 and gap_ok(lay(n, a), ~lay(n, b), m))
G(1, 'a', 'b', 20); G(1, 'a', 'c', 12); G(1, 'b', 'c', 12); G(1, 'd', 'a', 10); G(1, 'd', 'c', 10); IN(1, 'e', 'c', 6)
G(2, 'a', 'd', 10); G(2, 'd', 'e', 12); G(2, 'a', 'g', 10); G(2, 'e', 'c', 12); G(2, 'd', 'c', 12)
IN(3, 'c', 'b', 12); G(3, 'b', 'd', 12); IN(3, 'e', 'd', 10); G(3, 'f', 'd', 12); G(3, 'f', 'b', 12)
G(4, 'b', 'c', 12); G(4, 'b', 'd', 12); G(4, 'c', 'd', 12); G(4, 'r', 'c', 8); G(4, 'r', 'd', 8); G(4, 'r', 'b', 8); G(4, 'e', 'b', 10); G(4, 'e', 'r', 8); G(4, 'e', 'c', 10)
G(5, 'c', 'b', 14); G(5, 'f', 'c', 6); G(5, 'f', 'b', 12); G(5, 'e', 'b', 12); IN(5, 'b', 'a', 20); IN(5, 'e', 'a', 10)
G(6, 'b', 'd', 10); G(6, 'c', 'd', 10); G(6, 'e', 'b', 10); G(6, 'e', 'c', 10); G(6, 'e', 'd', 10)
G(7, 'c', 'd', 12); IN(7, 'c', 'a', 8); IN(7, 'd', 'a', 6)
G(8, 'p', 'c', 20); G(8, 't', 'p', 12)
for p in (('b', 'c'), ('b', 'd'), ('b', 'e'), ('b', 'f'), ('c', 'd'), ('c', 'e'), ('c', 'f'), ('d', 'e'), ('d', 'f'), ('e', 'f')): G(9, p[0], p[1], 12)
for l in 'bcdef': IN(9, l, 'a', 10)
G(10, 'd', 'b', 8); IN(10, 'f', 'e', 10); IN(10, 'e', 'a', 10); G(10, 'g', 'b', 10); G(10, 'g', 'd', 10)
IN(11, 't', 'h', 10); G(11, 'p', 't', 12); G(11, 'x', 'b', 12); G(11, 'b', 'c', 12); IN(11, 'c', 'a', 8); IN(11, 'b', 'a', 12); IN(11, 'x', 'a', 12)
G(12, 'c', 'e', 10)
for n in range(1, 13):
    for kind, fn_ in (('完整版', f'{CHK}/av{n}_all.png'), ('簡化版', f'{CHK}/avs{n}_all.png')):
        a = mask(fn_); ys, xs = np.nonzero(a); far = np.sqrt((xs-539.5)**2+(ys-539.5)**2).max()
        rec(f'款{n}{kind}符號在安全圓內（最遠{far:.0f}≤432）', far <= 432)
# ---------- 4. 對比 ----------
for tag, P in TONES.items():
    rec(f'文字對比 {tag} 字:底 = {cr(P["ink"], P["bg"])}（≥4.5）', cr(P['ink'], P['bg']) >= 4.5)

def av(n, tag, s):
    if s == 1080: return Image.open(f'{M[n]["dir"]}/頭像_1080圓_{tag}.png').convert('RGBA')
    return Image.open(f'{M[n]["dir"]}/頭像_{s}_{tag}.png').convert('RGBA')
def paste(canvas, im, xy): canvas.paste(im, xy, im)
def wrap(txt, font, wmax, d):
    lines, cur = [], ''
    for ch in txt:
        if d.textlength(cur+ch, font=font) > wmax: lines.append(cur); cur = ch
        else: cur += ch
    return lines+[cur]
# ---------- contact_sheet ----------
TW, TH, G_ = 520, 900, 30
sheet = Image.new('RGB', (4*TW+5*G_, 3*TH+4*G_+150), '#FBF7F0'); d = ImageDraw.Draw(sheet)
d.text((G_, 34), '「日日小晴」LOGO 第四輪 12 款：素材更豐富（奶油晨光；其他色調見 palette_rrxq4.png）', font=F(44, True), fill='#3A3A3A')
d.text((G_, 100), '6 款為第三輪升級加料、6 款為新的豐富構圖；右側小圖為 110／44px 簡化小圖版', font=F(28), fill='#5A5A5A')
for i, m in enumerate(meta):
    n = m['n']; x = G_+(i % 4)*(TW+G_); y = 150+G_+(i//4)*(TH+G_)
    d.rounded_rectangle((x, y, x+TW, y+TH), 28, fill='#FFFFFF', outline='#E8DFD0', width=2)
    paste(sheet, av(n, '奶油晨光', 1080).resize((300, 300), Image.LANCZOS), (x+30, y+30))
    for k, tg in enumerate(('晴空淡藍', '抹茶午後', '深色模式')):
        paste(sheet, av(n, tg, 110).resize((84, 84), Image.LANCZOS), (x+372, y+36+k*96))
    paste(sheet, av(n, '奶油晨光', 44), (x+372, y+36+3*96))
    w = Image.open(f'{m["dir"]}/字標含副標_奶油晨光.png').convert('RGB'); w = w.resize((TW-60, int(w.height*(TW-60)/w.width)), Image.LANCZOS); sheet.paste(w, (x+30, y+404))
    ty = y+404+w.height+22
    d.text((x+30, ty), f'{n:02d}　{m["name"]}', font=F(36, True), fill='#3A3A3A')
    sl = wrap(f'風格：{m["style"]}', F(24), TW-60, d)
    for k, ln in enumerate(sl): d.text((x+30, ty+52+k*32), ln, font=F(24), fill='#B5651D')
    yy = ty+52+len(sl)*32+6
    lines = wrap('含義：'+m['mean'], F(22), TW-60, d); rec(f'總覽含義不超格 款{n}（{len(lines)} 行）', len(lines) <= 6)
    for k, ln in enumerate(lines): d.text((x+30, yy+k*32), ln, font=F(22), fill='#3A3A3A')
    yy += len(lines)*32+8
    el = wrap('配角：'+m['added'], F(20), TW-60, d)
    for k, ln in enumerate(el): d.text((x+30, yy+k*29), ln, font=F(20), fill='#6B6B6B')
    bottom = yy+len(el)*29; rec(f'總覽文字在格內 款{n}（底{bottom}≤{y+TH-12}）', bottom <= y+TH-12)
sheet.save('contact_sheet_rrxq4.png')
# ---------- palette ----------
tags = list(TONES); CW, RH, LW = 230, 190, 300
pal = Image.new('RGB', (LW+6*CW+30, 280+12*RH+30), '#FFFFFF'); d = ImageDraw.Draw(pal)
d.text((30, 24), '「日日小晴」第四輪 12 款 × 6 色調', font=F(40, True), fill='#222222')
for c, tg in enumerate(tags):
    P = TONES[tg]; x = LW+c*CW; d.text((x, 90), tg, font=F(28, True), fill='#222222')
    ks = ['bg', 'S', 'M', 'soft', 'ink', 'G', 'C']
    for k, key in enumerate(ks): d.rectangle((x+k*31, 138, x+k*31+26, 174), fill=P[key], outline='#999999')
    for r_, grp in enumerate((ks[:3], ks[3:5]+['T'], ks[5:7])): d.text((x, 180+r_*18), ' '.join(P[k] for k in grp), font=F(13), fill='#555555')
    if P.get('mono'): d.text((x, 236), '（單色：僅黑／白）', font=F(14), fill='#555555')
for i, m in enumerate(meta):
    y = 270+i*RH; d.text((20, y+70), f'{m["n"]:02d} {m["name"]}', font=F(24, True), fill='#222222')
    for c, tg in enumerate(tags): paste(pal, av(m['n'], tg, 1080).resize((150, 150), Image.LANCZOS), (LW+c*CW, y+10))
pal.save('palette_rrxq4.png')
# ---------- 可讀性 ----------
cols = [('奶油晨光', '#F5F5F5'), ('晴空淡藍', '#F5F5F5'), ('抹茶午後', '#F5F5F5'), ('深色模式', '#F5F5F5'), ('單色黑', '#F5F5F5'), ('單色白', '#F5F5F5'), ('奶油晨光', '#121212'), ('深色模式', '#121212'), ('單色白', '#121212')]
UW = 180; X0 = 260+150; rd = Image.new('RGB', (X0+len(cols)*UW+20, 130+12*128+20), '#F5F5F5'); d = ImageDraw.Draw(rd)
d.rectangle((X0+6*UW, 0, rd.width, rd.height), fill='#121212')
d.text((20, 20), '可讀性：簡化小圖版 110px／44px 實際大小（左六欄淺色底；右三欄 IG 深色底）；最左欄為「完整版」110px 對照', font=F(24, True), fill='#222222')
d.text((262, 70), '完整版110', font=F(15), fill='#222222')
for c, (tg, b) in enumerate(cols): d.text((X0+c*UW+8, 70), tg+('（深色底）' if b == '#121212' else ''), font=F(15), fill='#222222' if b != '#121212' else '#EEEEEE')
for i, m in enumerate(meta):
    y = 110+i*128; d.text((16, y+40), f'{m["n"]:02d} {m["name"]}', font=F(21, True), fill='#222222')
    paste(rd, Image.open(f'{m["dir"]}/頭像_110完整版_奶油晨光.png').convert('RGBA'), (262, y+4))
    for c, (tg, b) in enumerate(cols):
        paste(rd, av(m['n'], tg, 110), (X0+c*UW+4, y+4)); paste(rd, av(m['n'], tg, 44), (X0+c*UW+4+110+12, y+37))
rd.save('可讀性_rrxq4_110_44.png')
# ---------- 配合示意 ----------
TPL = '../templates_rrxq/1_cover/1_cover_%s.png'
def trim(im):
    a = np.array(im)[:, :, 3] > 20; ys, xs = np.nonzero(a); return im.crop((xs.min(), ys.min(), xs.max()+1, ys.max()+1))
def cover(n, tpl='cream', tone='奶油晨光'):
    im = Image.open(TPL % tpl).convert('RGB'); bgc = tuple(im.getpixel((20, 20)))
    d = ImageDraw.Draw(im); d.rectangle((90, 90, 330, 160), fill=bgc)
    w = trim(Image.open(f'{M[n]["dir"]}/字標_透明_{tone}.png').convert('RGBA')); w = w.resize((int(w.width*.2), int(w.height*.2)), Image.LANCZOS)
    pos = (96, 120-w.height//2); im.paste(w, pos, w); wb = (pos[0], pos[1], pos[0]+w.width, pos[1]+w.height)
    return im, wb
tiles = []
for n in range(1, 13):
    im, wb = cover(n)
    rec(f'配合示意 款{n} 字標高{wb[3]-wb[1]}≥36、與插畫距≥12、與頁碼距≥100、左緣96', (wb[3]-wb[1]) >= 36 and 168-wb[3] >= 12 and wb[1] >= 60 and 915-wb[2] >= 100 and wb[0] == 96)
    tiles.append(im.crop((60, 60, 700, 200)))
sh = Image.new('RGB', (2*640+3*20, 6*(140+56)+20), '#DDDDDD'); d = ImageDraw.Draw(sh)
for i, t in enumerate(tiles):
    x = 20+(i % 2)*(640+20); y = 20+(i//2)*(140+56); sh.paste(t, (x, y+40)); d.text((x, y+6), f'{i+1:02d} {M[i+1]["name"]}（封面左上角，字標比例 0.2，原尺寸裁切）', font=F(22, True), fill='#222222')
sh.save('配合示意_rrxq4_封面左上角.png')
# ---------- 對照：第三輪 vs 第四輪 ----------
PAIRS = [('08_一筆圓相', 1, '第三輪 08 一筆圓相', ['淡彩光暈（橘／藍／綠暈開）', '「晴」字落款小印', '三顆閃光']),
         ('06_黏土太陽', 2, '第三輪 06 黏土太陽', ['一株小芽（兩片葉）＋一撮小草', '地面柔影', '指紋壓痕、右下小雲保留']),
         ('10_搪瓷晴招牌', 3, '第三輪 10 搪瓷晴招牌', ['雙層邊框＋一圈小圓點', '四角鉚釘', '「每天，一小段晴」小字帶']),
         ('04_繡線太陽', 4, '第三輪 04 繡線太陽', ['方章改圓章、四色鎖邊線', '跑針圈、小雲、小草、十字繡', '太陽輻射改為雙色線'])]
RW, RHh = 1900, 470
cmp_ = Image.new('RGB', (RW, 150+4*RHh+20), '#FBF7F0'); d = ImageDraw.Draw(cmp_)
d.text((40, 30), '第三輪 vs 第四輪：同一個方向，多了什麼（奶油晨光、圓形頭像）', font=F(44, True), fill='#3A3A3A')
d.text((40, 96), '左：第三輪原版（單一主元素）　右：第四輪（主元素＋配角＋質感）', font=F(28), fill='#5A5A5A')
for i, (d3, n4, cap, adds) in enumerate(PAIRS):
    y = 150+i*RHh
    d.rounded_rectangle((30, y, RW-30, y+RHh-20), 26, fill='#FFFFFF', outline='#E8DFD0', width=2)
    a = Image.open(f'../logo_rrxq3/{d3}/頭像_1080圓_奶油晨光.png').convert('RGBA').resize((380, 380), Image.LANCZOS); paste(cmp_, a, (70, y+20))
    d.text((70, y+408), cap, font=F(22), fill='#5A5A5A')
    d.text((500, y+170), '→', font=F(80, True), fill='#B5651D')
    b = av(n4, '奶油晨光', 1080).resize((380, 380), Image.LANCZOS); paste(cmp_, b, (640, y+20))
    d.text((640, y+408), f'第四輪 {n4:02d} {M[n4]["name"]}', font=F(22, True), fill='#3A3A3A')
    d.text((1100, y+60), '多了什麼', font=F(34, True), fill='#B5651D')
    for k, t in enumerate(adds): d.text((1100, y+120+k*58), '・'+t, font=F(28), fill='#3A3A3A')
    d.text((1100, y+120+3*58+20), '110／44px 用簡化小圖版，輪廓不變', font=F(22), fill='#7A7A7A')
cmp_.save('對照_rrxq3_vs_rrxq4.png')
json.dump(dict(items=rep['items'], fails=rep['fails'], total=len(rep['items'])), open('overlap_report.json', 'w'), ensure_ascii=False, indent=1)
print('檢查項目', len(rep['items']), '失敗', len(rep['fails']))
for f in rep['fails']: print('FAIL', f)
