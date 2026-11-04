# 「我們這一代」8 種風格 LOGO（全部自繪向量，不用 AI 圖、不用吉祥物）
# 用法：python3 gen.py → node render.js → python3 compose.py
import json, os
from PIL import ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
NAME = '我們這一代'
FD = os.path.expanduser('~/.fonts/')
FONTS = {'serifB': (FD+'NotoSerifCJKtc-Bold.otf', "'Noto Serif CJK TC',serif", 700),
         'serifR': (FD+'NotoSerifCJKtc-Regular.otf', "'Noto Serif CJK TC',serif", 400),
         'sansB': (FD+'NotoSansCJKtc-Bold.otf', "'Noto Sans CJK TC',sans-serif", 700),
         'sansR': (FD+'NotoSansCJKtc-Regular.otf', "'Noto Sans CJK TC',sans-serif", 400),
         'kai': (FD+'LXGWWenKaiTC-Regular.ttf', "'LXGW WenKai TC',serif", 400)}
PAL = {
 '霧紫灰': dict(bg='#4A4454', ink='#F3EFF5', line='#ABA0B5', lamp='#F2D88E', card='#554E60', seal='#E3B3A8', paper='#F3EFF5', pink='#4A4454', mono=False),
 '單色白': dict(bg='#000000', ink='#FFFFFF', line='#FFFFFF', lamp='#FFFFFF', card='#000000', seal='#FFFFFF', paper='#FFFFFF', pink='#000000', mono=True),
 '單色黑': dict(bg='#FFFFFF', ink='#000000', line='#000000', lamp='#000000', card='#FFFFFF', seal='#000000', paper='#000000', pink='#FFFFFF', mono=True),
}
def tw(fk, s, fs, ls):
    f = ImageFont.truetype(FONTS[fk][0], 200)
    return f.getlength(s) * fs / 200 + ls * fs * len(s)
def T(i, x, y, fk, s, fs, ls, fill, anchor='start'):
    fam, w = FONTS[fk][1], FONTS[fk][2]
    if anchor == 'middle': x += ls * fs / 2
    return (f'<text id="{i}" x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-weight="{w}" font-size="{fs}" '
            f'letter-spacing="{ls*fs:.1f}" text-anchor="{anchor}" fill="{fill}">{s}</text>')
def Ls(c, sw, col=None):
    return f'fill="none" stroke="{col or c["line"]}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"'
def wrap(w, h, c, body, transparent=False, defs=''):
    bg = '' if transparent else f'<rect width="{w}" height="{h}" fill="{c["bg"]}"/>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><defs>{defs}</defs>{bg}{body}</svg>'
GRAIN = ('<filter id="grain" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".75" numOctaves="2" seed="7"/>'
         '<feColorMatrix type="matrix" values="0 0 0 0 .29  0 0 0 0 .27  0 0 0 0 .33  1.6 0 0 0 -.75"/></filter>')
ROUGH = ('<filter id="rough" x="-10%" y="-10%" width="120%" height="120%"><feTurbulence type="fractalNoise" baseFrequency=".05" numOctaves="2" seed="3" result="t"/>'
         '<feDisplacementMap in="SourceGraphic" in2="t" scale="2.2"/></filter>')

# ---------- 各款符號（單位座標，原點置中）。回傳 (svg, 半寬, 半高, defs) ----------
def sym1(c):   # 細線條極簡：落地燈（燈罩只畫輪廓，燈在罩裡）
    L = Ls(c, 7)
    return (f'<path d="M-34 -88 H34 L52 -34 H-52 Z" {L}/><circle cx="0" cy="-56" r="9" fill="{c["lamp"]}"/>'
            f'<path d="M0 -34 V80 M-24 82 H24" {L}/><path d="M-80 82 H80" {L}/>'), 84, 92, ''
def sym2(c):   # 手寫溫柔：吊燈＋一點點歪的線＋三個小點
    L = Ls(c, 8)
    return (f'<path d="M2 -92 C-1 -76 3 -62 0 -46" {L}/>'
            f'<path d="M-44 -6 C-46 -30 -26 -46 -2 -46 C24 -47 46 -30 43 -8 C20 -2 -18 -10 -44 -6 Z" {L}/>'
            f'<circle cx="1" cy="15" r="11" fill="{c["lamp"]}"/>'
            f'<path d="M-74 74 C-40 68 -10 80 24 72 C44 68 60 74 76 70" {L}/>'
            f'<circle cx="-26" cy="50" r="6" fill="{c["line"]}"/><circle cx="2" cy="54" r="6" fill="{c["line"]}"/><circle cx="30" cy="49" r="6" fill="{c["line"]}"/>'), 82, 94, ''
def sym3(c):   # 印章：雙圈＋「我們」＋一點燈
    s = c['seal']
    return (f'<g filter="url(#rough)"><g transform="rotate(-6)"><circle cx="0" cy="0" r="98" {Ls(c,9,s)}/><circle cx="0" cy="0" r="82" {Ls(c,5,s)}/>'
            f'<circle id="dot" cx="0" cy="-66" r="6" fill="{c["lamp"]}"/>'
            + T('st', 0, 24, 'serifB', '我們', 64, 0.04, s, 'middle') + '</g></g>'), 103, 103, ROUGH
WIN_LIT = {(0, 2), (1, 0), (2, 1)}
def sym4(c):   # 公寓窗格：4 層 3 戶，只有 3 扇亮
    L = Ls(c, 7); o = f'<rect x="-66" y="-92" width="132" height="170" rx="6" {L}/><path d="M-96 78 H96" {L}/>'
    for r, y in enumerate([-66, -30, 6, 42]):
        for k, x in enumerate([-36, 0, 36]):
            if (r, k) in WIN_LIT: o += f'<rect x="{x-12}" y="{y-12}" width="24" height="24" rx="4" fill="{c["lamp"]}"/>'
            else: o += f'<rect x="{x-12}" y="{y-12}" width="24" height="24" rx="4" {Ls(c,6)}/>'
    return o, 98, 94, ''
def dai(c, sw, lamp=True):   # 結構化「代」：亻＋弋，弋上那一點就是燈
    L = f'fill="none" stroke="{c["ink"]}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"'
    return (f'<path d="M-36 -54 L-60 -14" {L}/><path d="M-44 -26 V58" {L}/>'
            f'<path d="M-2 -58 C18 -12 30 18 44 44 C52 58 66 52 68 34" {L}/><path d="M-6 -22 H58" {L}/>'
            f'<circle cx="46" cy="-50" r="{sw*0.95:.1f}" fill="{c["lamp"]}"/>')
def sym5(c):
    return (f'<rect x="-88" y="-88" width="176" height="176" rx="20" {Ls(c,8)}/>' + dai(c, 15)), 92, 92, ''
def sym6(c):   # 收據：鋸齒底、三行品項、合計線、條碼，燈是頂端那顆圓
    pts = [(-64, -88), (64, -88)]
    for i in range(17): pts.append((64 - 8 * i, 66 if i % 2 == 0 else 78))
    d = 'M' + ' L'.join(f'{x} {y}' for x, y in pts) + ' Z'
    pi = c['pink']; L = Ls(c, 6, pi)
    o = f'<clipPath id="pp"><path d="{d}"/></clipPath><path d="{d}" fill="{c["paper"]}"/>'
    if not c['mono']: o += '<rect x="-70" y="-92" width="140" height="176" filter="url(#grain)" clip-path="url(#pp)"/>'
    lampfill = c['lamp'] if not c['mono'] else pi
    o += f'<circle cx="0" cy="-60" r="14" fill="{lampfill}" stroke="{pi}" stroke-width="5"/>'
    for y in (-26, -2, 22):
        o += (f'<path d="M-44 {y} h26 M32 {y} h12" {L}/><path d="M-8 {y} H20" fill="none" stroke="{pi}" stroke-width="6" stroke-linecap="round" stroke-dasharray="0.1 11"/>')
    o += f'<path d="M-44 38 H44" {L}/>'
    for x in range(-42, 43, 12): o += f'<path d="M{x} 49 V62" {L}/>'
    return f'<g transform="rotate(3)">{o}</g>', 68, 92, GRAIN
def sym7(c):   # 圓角徽章：拱形窗亮一盞燈
    L = Ls(c, 8)
    return (f'<circle cx="0" cy="0" r="100" fill="{c["card"]}" {Ls(c,9)}/>'
            f'<path d="M-34 56 V-14 A34 34 0 0 1 34 -14 V56 Z" fill="{c["bg"]}" {L}/>'
            f'<circle cx="0" cy="20" r="13" fill="{c["lamp"]}"/><path d="M-48 62 H48" {L}/>'
            f'<circle cx="-30" cy="-64" r="5" fill="{c["line"]}"/><circle cx="0" cy="-72" r="5" fill="{c["line"]}"/><circle cx="30" cy="-64" r="5" fill="{c["line"]}"/>'), 105, 105, ''

STYLES = [
 dict(n=1, name='細線條極簡', sym=sym1, scale=3.1, fk='serifR', ls=0.16, concept='一盞只畫輪廓的落地燈，燈在罩子裡：最少的線，留下最多的安靜。'),
 dict(n=2, name='手寫溫柔', sym=sym2, scale=1.9, fk='kai', ls=0.08, concept='手繪感吊燈，線條微微歪，底下三個小點是「我們」：不完美也沒關係。'),
 dict(n=3, name='印章郵戳', sym=sym3, scale=4.0, fk='serifB', ls=0.08, concept='低飽和玫瑰灰的雙圈印，蓋著「我們」與一點燈，像寄給自己的一封信。'),
 dict(n=4, name='公寓窗格', sym=sym4, scale=3.2, fk='sansB', ls=0.1, concept='一棟公寓十二扇窗，只亮三扇：每扇窗後面都是一個我們。'),
 dict(n=5, name='幾何符號', sym=sym5, scale=3.2, fk='sansB', ls=0.1, concept='把「代」拆成直線與一點：亻＋弋，弋上的那一點就是燈，整體框成一扇窗。'),
 dict(n=6, name='收據膠片', sym=sym6, scale=3.4, fk='sansB', ls=0.12, concept='一張薪資單般的收據，鋸齒邊、帶顆粒，頂端圓點是唯一亮著的一項。'),
 dict(n=7, name='圓角徽章', sym=sym7, scale=4.0, fk='sansB', ls=0.06, concept='圓徽章裡一扇拱窗亮著燈，字標放進膠囊：柔和、適合頭像。'),
 dict(n=8, name='純字標', sym=None, scale=0, fk='serifR', ls=0.42, concept='只有字：寬字距、細字重，最後一字「代」是整個標誌裡唯一亮著的字。'),
]
def folder(st): return f"{st['n']:02d}_{st['name']}"

# ---------- 頭像（1080，內容須在中央 864 圓內）----------
def avatar(st, c):
    n = st['n']; body = ''; pairs = []; defs = ''
    if n == 8:
        body = T('nm', 540, 540 + 300 * 0.36, 'serifB', '我們', 300, 0.16, c['ink'], 'middle')
        body = body.replace('我們<', f'我<tspan fill="{c["lamp"]}">們</tspan><')
    elif n == 2:
        s, hw, hh, defs = st['sym'](c)
        body = (f'<g id="sym" transform="translate(540 470) scale(1.9)">{s}</g>'
                + T('nm', 540, 740 + 200 * 0.36, 'kai', '我們', 200, 0.1, c['ink'], 'middle'))
        pairs = [['sym', 'nm']]
    elif n == 3:
        s, hw, hh, defs = st['sym'](c)
        body = f'<g transform="translate(540 540) scale(4.0)">{s}</g>'; pairs = [['dot', 'st']]
    elif n == 5:
        s, hw, hh, defs = st['sym'](c); body = f'<g transform="translate(540 540) scale(3.2)">{s}</g>'
    else:
        s, hw, hh, defs = st['sym'](c); body = f'<g id="sym" transform="translate(540 540) scale({st["scale"]})">{s}</g>'
    return wrap(1080, 1080, c, body, defs=defs), pairs

# ---------- 橫式字標 ----------
def wordmark(st, c, transparent=False, H=400):
    n = st['n']; fk, ls = st['fk'], st['ls']; pad = 70; fs = 120
    cy = H / 2; base = cy + fs * 0.36; check = True; defs = ''
    if n == 8:
        W = round(pad * 2 + tw(fk, NAME, fs, ls) - ls * fs)
        t = T('nm', pad, base, fk, NAME, fs, ls, c['ink']).replace('一代<', f'一<tspan fill="{c["lamp"]}">代</tspan><')
        return W, H, wrap(W, H, c, t, transparent), False, 'nm'
    if n == 5:   # 「我們這一」用字型、「代」用自繪結構字，筆畫粗細對齊
        pre = NAME[:-1]; w1 = tw('sansB', pre, fs, ls); gx = pad + w1 + fs / 2
        sc = 0.97
        W = round(pad + w1 + fs + pad)
        g = f'<g transform="translate({gx:.1f} {cy - 0.0:.1f}) scale({sc})">{dai(c, 12.4)}</g>'
        t = T('nm', pad, base, 'sansB', pre, fs, ls, c['ink'])
        return W, H, wrap(W, H, c, t + g, transparent), False, 'nm'
    s, hw, hh, defs = st['sym'](c); ss = 120 / hh
    if n == 7:
        fs = 96; base = cy + fs * 0.36; ph = fs * 1.5; gap = 0.5 * 120
        sx = pad + hw * ss; px = pad + 2 * hw * ss + gap; tw_ = tw(fk, NAME, fs, ls); pw = tw_ - ls * fs + 80
        W = round(px + pw + pad)
        body = (f'<g id="sym" transform="translate({sx:.1f} {cy}) scale({ss:.3f})">{s}</g>'
                f'<rect id="nm" x="{px:.1f}" y="{cy-ph/2:.1f}" width="{pw:.1f}" height="{ph:.1f}" rx="{ph/2:.1f}" {Ls(c,6)}/>'
                + T('tx', px + 40, base, fk, NAME, fs, ls, c['ink']))
        return W, H, wrap(W, H, c, body, transparent, defs), 'fs96', 'nm'
    gap = 0.5 * fs; sx = pad + hw * ss; tx = pad + 2 * hw * ss + gap; tl = tw(fk, NAME, fs, ls) - ls * fs
    if n == 6: fs = 100; base = cy + fs * 0.36; tl = tw(fk, NAME, fs, ls) - ls * fs
    extra = ''; W = round(tx + tl + pad)
    if n == 3:
        wx = tx + tl + 40
        wv = ''.join(f'<path d="M{wx:.1f} {cy+dy} q18 -14 36 0 t36 0 t36 0 t36 0" {Ls(c,6,c["seal"])}/>' for dy in (-26, 0, 26))
        extra = f'<g id="dec">{wv}</g>'; W = round(wx + 144 + pad)
    if n == 6:
        for yy in (cy - 0.75 * fs, cy + 0.75 * fs):
            extra += f'<path d="M{tx:.1f} {yy:.1f} H{tx+tl:.1f}" fill="none" stroke="{c["line"]}" stroke-width="4" stroke-dasharray="10 8"/>'
    body = (f'<g id="sym" transform="translate({sx:.1f} {cy}) scale({ss:.3f})">{s}</g>'
            + T('nm', tx, base, fk, NAME, fs, ls, c['ink']) + extra)
    return W, H, wrap(W, H, c, body, transparent, defs), fs, 'nm'

jobs = []
for st in STYLES:
    fo = folder(st); os.makedirs(fo, exist_ok=True)
    for tag, c in PAL.items():
        av, pairs = avatar(st, c); p = f'{fo}/頭像_1080_{tag}'
        open(p + '.svg', 'w', encoding='utf-8').write(av)
        jobs.append(dict(svg=p + '.svg', png=p + '.png', w=1080, h=1080, kind='avatar', n=st['n'], tag=tag, pairs=pairs, ids=['sym', 'nm', 'dot', 'st']))
        W, H, sv, fs, nmid = wordmark(st, c); p = f'{fo}/字標_{tag}'
        open(p + '.svg', 'w', encoding='utf-8').write(sv)
        jobs.append(dict(svg=p + '.svg', png=p + '.png', w=W, h=H, kind='wm', n=st['n'], tag=tag, fs=(96 if fs == 'fs96' else fs), nmid=nmid, ids=['sym', 'nm']))
    W, H, sv, fs, nmid = wordmark(st, PAL['霧紫灰'], True); p = f'{fo}/字標_透明_霧紫灰'
    open(p + '.svg', 'w', encoding='utf-8').write(sv)
    jobs.append(dict(svg=p + '.svg', png=p + '.png', w=W, h=H, kind='cover', n=st['n'], tag='透明', transparent=True, ids=[]))
json.dump(dict(jobs=jobs, styles=[{k: v for k, v in s.items() if k != 'sym'} for s in STYLES], pal=PAL), open('jobs.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(jobs), 'jobs')
