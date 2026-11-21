# 產出米克斯兩版全套：python3 build.py && node ../render.js（在本資料夾以 jobs.json 執行）&& python3 build.py post
import sys, json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from mix import *
H = os.path.dirname(os.path.abspath(__file__)); os.chdir(H)
CHK = '/tmp/claude-0/-home-user-tw-rotation/ce50d787-1067-5482-ab44-99dc39a48890/scratchpad/mix'
FIT0 = 363.08  # 原 04 的最遠半徑，沿用同一縮放讓大小一致
if len(sys.argv) == 1:
    jobs = []
    for v, fo, fn in VAR:
        os.makedirs(fo, exist_ok=True)
        ka = min(420/FIT0, 1.6) if v == 'A' else 1.10; kw = min(172/FIT0, 1.2) if v == 'A' else .45
        for tag, P in TONES.items():
            sym = fn(P)
            p = f'{fo}/頭像_1080方_{tag}'; open(p+'.svg', 'w').write(gen.avatar_svg(P, sym, ka)); jobs.append(dict(v=v, kind='avatar', tag=tag, svg=p+'.svg', png=p+'.png', w=1080, h=1080))
            for sub, suf in ((False, '字標'), (True, '字標含副標')):
                sv, W = gen.wm_svg(P, 4, sym, 'sans', 14, kw, sub); p = f'{fo}/{suf}_{tag}'; open(p+'.svg', 'w').write(sv)
                jobs.append(dict(v=v, kind='wm', tag=tag, svg=p+'.svg', png=p+'.png', w=W, h=gen.WH))
                if not P.get('mono'):
                    sv, W = gen.wm_svg(P, 4, sym, 'sans', 14, kw, sub, bg=False); p = f'{fo}/{suf}_透明_{tag}'; open(p+'.svg', 'w').write(sv)
                    jobs.append(dict(v=v, kind='wmT', tag=tag, svg=p+'.svg', png=p+'.png', w=W, h=gen.WH, transparent=True))
        P = TONES['奶油晨光']; sym = fn(P)
        open(f'{CHK}/{v}av.svg', 'w').write(gen.avatar_svg(P, sym, ka, bg=False))
        jobs.append(dict(v=v, kind='chk', svg=f'{CHK}/{v}av.svg', png=f'{CHK}/{v}av_all.png', w=1080, h=1080, transparent=True))
        sv, W = gen.wm_svg(P, 4, sym, 'sans', 14, kw, True, bg=False); open(f'{CHK}/{v}wm.svg', 'w').write(sv)
        for lay in ('sym', 'txt', 'sub'):
            jobs.append(dict(v=v, kind='chkwm', layer=lay, svg=f'{CHK}/{v}wm.svg', png=f'{CHK}/{v}wm_{lay}.png', w=W, h=gen.WH, transparent=True, show=([lay,'a','b'] if lay=='sym' else [lay])))
    json.dump(dict(jobs=jobs), open('jobs.json', 'w'), ensure_ascii=False); print(len(jobs))
else:
    J = json.load(open('jobs.json'))['jobs']; fails = []; n = 0
    def circ(im, s):
        big = im.convert('RGB').resize((s, s), Image.LANCZOS); m = Image.new('L', (s*4, s*4), 0)
        ImageDraw.Draw(m).ellipse((0, 0, s*4-1, s*4-1), fill=255); m = m.resize((s, s), Image.LANCZOS)
        o = Image.new('RGBA', (s, s), (0, 0, 0, 0)); o.paste(big, (0, 0), m); return o
    for j in J:
        if j['kind'] == 'avatar':
            fo = dict((v, f) for v, f, _ in VAR)[j['v']]; im = Image.open(j['png'])
            for s in (1080, 110, 44): circ(im, s).save(f'{fo}/頭像_{"1080圓" if s==1080 else s}_{j["tag"]}.png')
            P = TONES[j['tag']]; bg = np.array([int(P['bg'][i:i+2], 16) for i in (1, 3, 5)])
            d = np.abs(np.array(im.convert('RGB')).astype(int)-bg).max(axis=2) > 24; ys, xs = np.nonzero(d)
            far = float(np.sqrt((xs-539.5)**2+(ys-539.5)**2).max()); n += 1
            if far > 432: fails.append(f'{j["v"]} {j["tag"]} 超出安全圓 {far:.0f}')
        if j['kind'] == 'chkwm' and j['layer'] == 'sym':
            m = {l: np.array(Image.open(f'{CHK}/{j["v"]}wm_{l}.png'))[:, :, 3] > 20 for l in ('sym', 'txt', 'sub')}
            for a, b in (('sym', 'txt'), ('sym', 'sub'), ('txt', 'sub')):
                n += 1
                if (m[a] & m[b]).any(): fails.append(f'{j["v"]} 字標 {a}×{b} 相交')
            xs = np.nonzero(m['sym'].any(0))[0]; xt = np.nonzero(m['txt'].any(0))[0]; n += 1
            if xt.min()-xs.max() < 30: fails.append(f'{j["v"]} 圖示與文字間距 {xt.min()-xs.max()}px <30')
    json.dump(dict(checked=n, fails=fails), open('overlap_report.json', 'w'), ensure_ascii=False, indent=1)
    print('檢查', n, '項，失敗', len(fails), fails)
    # 比較圖：原版／A／B 各一列：1080 圓頭像（縮 300）＋110＋44＋字標
    FD = os.path.expanduser('~/.fonts/'); f1 = ImageFont.truetype(FD+'NotoSansCJKtc-Bold.otf', 34); f2 = ImageFont.truetype(FD+'NotoSansCJKtc-Regular.otf', 24)
    rows = [('原版 04 貓睡陽光（黑貓剪影）', '../04_貓睡陽光'), ('A 米克斯打盹（保留原姿勢）', 'A_米克斯打盹'), ('B 米克斯歪頭（照片那種坐姿）', 'B_米克斯歪頭')]
    W, RH = 2000, 400; sheet = Image.new('RGB', (W, 120+RH*3), '#FBF7F0'); dr = ImageDraw.Draw(sheet)
    dr.text((40, 34), '「日日小晴」04 貓睡陽光 → 米克斯版（奶油晨光）', font=f1, fill='#3A3A3A')
    for i, (lab, fo) in enumerate(rows):
        y = 120+i*RH; dr.text((40, y+8), lab, font=f2, fill='#8A5A2E')
        sheet.paste(Image.open(f'{fo}/頭像_1080圓_奶油晨光.png').resize((300, 300), Image.LANCZOS), (40, y+50), Image.open(f'{fo}/頭像_1080圓_奶油晨光.png').resize((300, 300)).split()[3])
        a = Image.open(f'{fo}/頭像_110_奶油晨光.png'); sheet.paste(a, (380, y+145), a)
        a = Image.open(f'{fo}/頭像_44_奶油晨光.png'); sheet.paste(a, (520, y+178), a)
        a = Image.open(f'{fo}/頭像_44_深色模式.png'); sheet.paste(a, (580, y+178), a)
        wm = Image.open(f'{fo}/字標含副標_奶油晨光.png').convert('RGB'); k = 300/wm.height; wm = wm.resize((int(wm.width*k), 300), Image.LANCZOS)
        sheet.paste(wm, (680, y+50))
        dr.text((380, y+290), '110px／44px／44px 深色', font=f2, fill='#777')
    sheet.save('米克斯_比較.png')
    t = ['奶油晨光', '晴空淡藍', '抹茶午後', '深色模式', '單色黑', '單色白']
    pal = Image.new('RGB', (6*300+40, 2*320+40), '#FBF7F0')
    for r, (v, fo, _) in enumerate(VAR):
        for c, tg in enumerate(t):
            a = Image.open(f'{fo}/頭像_1080圓_{tg}.png').resize((280, 280), Image.LANCZOS); pal.paste(a, (20+c*300, 20+r*320), a)
    pal.save('米克斯_色調.png'); print('ok')
