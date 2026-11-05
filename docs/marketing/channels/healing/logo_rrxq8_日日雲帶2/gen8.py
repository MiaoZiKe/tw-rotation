# 「日日小晴」LOGO：B 日日雲帶 第二批變化 13～24（2026-11-05 Andy：「再多點變化給我」）
# 共同骨架同第一批：兩個「日」＝日日；今天那格露出小太陽＝小晴
# 重跑：rm -f fit.json; python3 gen8.py && node render.js && python3 fit8.py && python3 gen8.py && node render.js && python3 post8.py
import sys, os, json
H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(H, '..', 'logo_rrxq7_日日雲帶'))
_c = os.getcwd(); os.chdir(os.path.join(H, '..', 'logo_rrxq7_日日雲帶')); import gen7; os.chdir(H)
from gen7 import gen, TONES, L, blend, SUN, sun, rays, glyph, C, WARM, wm_svg, WH
CHK = '/tmp/claude-0/-home-user-tw-rotation/ce50d787-1067-5482-ab44-99dc39a48890/scratchpad/rrxq8'; os.makedirs(CHK, exist_ok=True)
FIT = json.load(open('fit.json')) if os.path.exists('fit.json') else {}
mono = lambda P: P.get('mono')
def pair(P, lc=None, rc=None, dx=104, sc=.56, ly=0, ry=0, **kw):
    a, _ = glyph(-dx, ly, sc, lc or C(P), 'cloud', P, bump=(-30, -90), **kw); b, s = glyph(dx, ry, sc, rc or C(P), 'sun', P, **kw); return a, b, s
def fontpair(P, kind, fs=300, ls=-10):
    """用字型寫「日日」：右邊那個「日」的中橫用底色蓋掉，換成小太陽"""
    ink = P['C'] if not mono(P) else P['ink']; w = gen.text_w('日日', kind, fs, ls); x0 = -w/2
    t = gen.TX('日日', kind, fs, x0, .36*fs, ink, ls=ls)
    cw = gen.text_w('日', kind, fs, 0); rx = x0 + cw + ls
    cover = f'<rect x="{rx+cw*.30}" y="{-fs*.075}" width="{cw*.40}" height="{fs*.15}" fill="{P["bg"]}"/>'
    cl = f'<circle cx="{x0+cw*.5}" cy="{-fs*.03}" r="{fs*.07}" fill="{ink}"/><circle cx="{x0+cw*.62}" cy="{-fs*.01}" r="{fs*.05}" fill="{ink}"/>'
    return L('a', t + cover + cl) + L('b', sun(P, rx+cw*.5, 0, fs*.075))
def v13(P): return fontpair(P, 'kai', 330)
def v14(P): return fontpair(P, 'serif', 300)
def v15(P):  # 泡泡日日：超圓胖的字，像棉花糖雲
    c = C(P); s = ''
    for cx, sunny in ((-128, False), (128, True)):
        s += f'<g transform="translate({cx} 0)"><rect x="-86" y="-140" width="172" height="280" rx="70" fill="none" stroke="{c}" stroke-width="50"/>'
        s += (f'<path d="M -66 0 L -62 0 M 62 0 L 66 0" stroke="{c}" stroke-width="50" stroke-linecap="round"/>' if sunny else f'<path d="M -66 0 L 66 0" stroke="{c}" stroke-width="50" stroke-linecap="round"/><circle cx="-12" cy="-12" r="32" fill="{c}"/>') + '</g>'
    return L('a', s) + L('b', sun(P, 128, 0, 24))
def v16(P):  # 晴空填色：昨天那格灰灰的，今天那格是藍天
    a, b, (x, y, r) = pair(P)
    if mono(P): fill = ''
    else:
        g = blend(P['C'], P['bg'], .55); sky = '#BFE0F5' if P['bg'] != '#1E1A16' else '#3E5A70'
        fill = (f'<rect x="{-104-80}" y="-122" width="160" height="244" rx="8" fill="{g}"/>'
                f'<rect x="{104-80}" y="-122" width="160" height="244" rx="8" fill="{sky}"/>')
    return L('c', fill) + L('a', a+b) + L('b', sun(P, x, y, r))
def v17(P):  # 雲中日日：兩個「日」被一朵大雲托著
    cl = blend(P['C'], P['bg'], .6) if not mono(P) else P['bg']; st = P['ink'] if mono(P) else 'none'
    big = (f'<g fill="{cl}" stroke="{st}" stroke-width="10"><circle cx="-150" cy="40" r="120"/><circle cx="0" cy="-30" r="170"/><circle cx="150" cy="40" r="120"/>'
           f'<rect x="-270" y="40" width="540" height="120" rx="60"/></g>')
    a, b, (x, y, r) = pair(P, dx=86, sc=.44, ly=20, ry=20)
    return L('c', big) + L('a', a+b) + L('b', sun(P, x, y, r))
def v18(P):  # 圓徽日日：一圈圓環把兩個「日」框住，環上一顆小太陽
    c = C(P); ring = f'<circle cx="0" cy="0" r="250" fill="none" stroke="{c}" stroke-width="26"/><circle cx="0" cy="0" r="214" fill="none" stroke="{c}" stroke-width="6" stroke-dasharray="2 18" stroke-linecap="round"/>'
    a, b, (x, y, r) = pair(P, dx=78, sc=.4)
    return L('a', ring + a + b) + L('b', sun(P, x, y, r) + sun(P, 0, -250, 30))
def v19(P):  # 疊影日日：今天疊在昨天前面一點
    a, _ = glyph(-70, -40, .56, blend(P['C'], P['bg'], .4) if not mono(P) else P['ink'], 'cloud', P, bump=(-30, -90))
    bk = f'<rect x="{70-96}" y="{40-140}" width="192" height="280" rx="18" fill="{P["bg"]}"/>'
    b, (x, y, r) = glyph(70, 40, .56, C(P), 'sun', P)
    return L('a', a + bk + b) + L('b', sun(P, x, y, r))
def v20(P):  # 跳舞日日：兩個「日」一左一右歪著，像在晃
    a, _ = glyph(0, 0, .52, C(P), 'cloud', P, bump=(-30, -90)); b, _ = glyph(0, 0, .52, C(P), 'sun', P)
    return (L('a', f'<g transform="translate(-110 14) rotate(-9)">{a}</g><g transform="translate(110 -14) rotate(8)">{b}</g>')
            + L('b', f'<g transform="translate(110 -14) rotate(8)">{sun(P, 0, 0, 27)}</g>'))
def v21(P):  # 撕紙拼貼：昨天貼灰紙，今天貼一張暖黃紙
    import random; rnd = random.Random(7)
    def torn(x, y, w, h, col):
        pts = []
        for i in range(13): pts.append((x+w*i/12, y+rnd.uniform(-8, 8)))
        for i in range(13): pts.append((x+w+rnd.uniform(-8, 8), y+h*i/12))
        for i in range(13): pts.append((x+w-w*i/12, y+h+rnd.uniform(-8, 8)))
        for i in range(13): pts.append((x+rnd.uniform(-8, 8), y+h-h*i/12))
        return f'<polygon points="{" ".join(f"{a:.0f},{b:.0f}" for a, b in pts)}" fill="{col}" filter="url(#sh)"/>'
    if mono(P): papers = ''
    else: papers = f'<g transform="rotate(-4)">{torn(-230, -190, 240, 360, blend(P["C"], P["bg"], .55))}</g><g transform="rotate(5)">{torn(-4, -186, 240, 360, blend(P["S"], P["bg"], .55))}</g>'
    a, b, (x, y, r) = pair(P, sc=.5, rc=P['ink'] if mono(P) else blend(P['C'], P['ink'], .25), lc=P['ink'] if mono(P) else blend(P['C'], P['ink'], .25))
    return L('c', papers) + L('a', a+b) + L('b', sun(P, x, y, r))
def v22(P):  # 日日貼紙：白邊貼紙，帶一點陰影
    a, b, (x, y, r) = pair(P)
    edge = '#FFFFFF' if not mono(P) else P['bg']
    f = (f'<filter id="stk" x="-20%" y="-20%" width="140%" height="140%"><feMorphology in="SourceAlpha" operator="dilate" radius="22" result="d"/>'
         f'<feFlood flood-color="{edge}"/><feComposite in2="d" operator="in" result="w"/><feDropShadow in="w" dx="0" dy="8" stdDeviation="8" flood-color="#5A4636" flood-opacity="{0 if mono(P) else .3}" result="ws"/>'
         f'<feMerge><feMergeNode in="ws"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
    mstroke = f'<rect x="-240" y="-170" width="480" height="340" rx="40" fill="none" stroke="{P["ink"]}" stroke-width="8" stroke-dasharray="14 12"/>' if mono(P) else ''
    return f'<defs>{f}</defs>' + L('a', f'<g filter="url(#stk)">{a}{b}{sun(P, x, y, r)}</g>' + mstroke) + L('b', '')
def v23(P):  # 小彩虹：兩個「日」中間搭一道小彩虹
    a, b, (x, y, r) = pair(P, ly=40, ry=40)
    cols = [P['ink']]*3 if mono(P) else [P['S'], '#F6D57A', '#9CC9E8']
    arc = ''.join(f'<path d="M {-104-rr} {-100} A {104+rr} {104+rr} 0 0 1 {104+rr} -100" fill="none" stroke="{c}" stroke-width="16" stroke-linecap="round" transform="scale(1 .55) translate(0 -150)"/>' for c, rr in zip(cols, (40, 20, 0)))
    return L('c', arc) + L('a', a+b) + L('b', sun(P, x, y, r))
def v24(P):  # 地平線日出：今天那個「日」的下半格，太陽正從底邊升起
    a, _ = glyph(-104, 0, .56, C(P), 'cloud', P, bump=(-30, -90)); b, _ = glyph(104, 0, .56, C(P), 'cloud', P)
    cut = f'<rect x="{104-50}" y="-30" width="100" height="40" fill="{P["bg"]}"/>'
    rise = f'<clipPath id="hz"><rect x="{104-70}" y="-20" width="140" height="122"/></clipPath><g clip-path="url(#hz)">{sun(P, 104, 102, 46)}</g>'
    return L('a', a+b) + L('b', rise + rays(P, 104, 102, 60, 76, 5, 9, -160, -20))
VAR = [
 (13, '13_書法日日', '書法日日', '用楷書寫「日日」，右邊那個「日」的中橫換成小太陽，左邊中間飄一朵小雲。', v13),
 (14, '14_明體日日', '明體日日', '端正的明體「日日」，今天那個字的中橫被小太陽取代：像印在報紙上的天氣。', v14),
 (15, '15_泡泡日日', '泡泡日日', '圓胖到像棉花糖雲的兩個「日」，軟軟的，今天那格有小太陽。', v15),
 (16, '16_晴空填色', '晴空填色', '昨天那格灰灰的，今天那格填成藍天，小太陽掛在中間。', v16),
 (17, '17_雲中日日', '雲中日日', '一大朵雲托著兩個「日」：日子在雲裡，也有一格晴。', v17),
 (18, '18_圓徽日日', '圓徽日日', '圓環把兩個「日」框成一枚徽章，環頂再一顆小太陽。', v18),
 (19, '19_疊影日日', '疊影日日', '今天疊在昨天前面一點：昨天淡淡的，今天比較清楚。', v19),
 (20, '20_跳舞日日', '跳舞日日', '兩個「日」一左一右歪著，像在晃：辛苦但還是輕鬆一點。', v20),
 (21, '21_撕紙拼貼', '撕紙拼貼', '昨天貼一張灰紙，今天貼一張暖黃紙：手帳裡的一天一頁。', v21),
 (22, '22_日日貼紙', '日日貼紙', '整個「日日」做成白邊貼紙，可以貼在任何地方。', v22),
 (23, '23_小彩虹', '小彩虹', '兩個「日」中間搭一道小彩虹：從昨天走到今天的那一小段晴。', v23),
 (24, '24_地平線日出', '地平線日出', '今天那個「日」的下半格，太陽正從底邊慢慢升起。', v24),
]
if __name__ == '__main__':
    jobs = []
    for n, fo, nm, mean, fn in VAR:
        os.makedirs(fo, exist_ok=True)
        far = FIT.get(str(n), 300); ka = min(420/far, 1.8); kw = min(172/far, 1.2)
        for tag, P in TONES.items():
            sym = fn(P)
            p = f'{fo}/頭像_1080方_{tag}'; open(p+'.svg', 'w').write(gen.avatar_svg(P, sym, ka)); jobs.append(dict(n=n, kind='avatar', tag=tag, svg=p+'.svg', png=p+'.png', w=1080, h=1080))
            for sub, suf in ((False, '字標'), (True, '字標含副標')):
                for bg in (True, False):
                    if not bg and P.get('mono'): continue
                    sv, W = wm_svg(P, sym, kw, sub, bg); p = f'{fo}/{suf}_{"" if bg else "透明_"}{tag}'; open(p+'.svg', 'w').write(sv)
                    jobs.append(dict(n=n, kind='wm', tag=tag, svg=p+'.svg', png=p+'.png', w=W, h=WH, transparent=not bg))
        P = TONES['奶油晨光']; sym = fn(P)
        open(f'{CHK}/{n}fit.svg', 'w').write(gen.avatar_svg(P, sym, 1.0, bg=False)); jobs.append(dict(n=n, kind='fit', svg=f'{CHK}/{n}fit.svg', png=f'{CHK}/{n}fit.png', w=1080, h=1080, transparent=True))
        sv, W = wm_svg(P, sym, kw, True, bg=False); open(f'{CHK}/{n}wm.svg', 'w').write(sv)
        for lay in ('sym', 'txt', 'sub'):
            jobs.append(dict(n=n, kind='chkwm', layer=lay, svg=f'{CHK}/{n}wm.svg', png=f'{CHK}/{n}wm_{lay}.png', w=W, h=WH, transparent=True, show=([lay, 'a', 'b', 'c'] if lay == 'sym' else [lay])))
    json.dump(dict(jobs=jobs), open('jobs.json', 'w'), ensure_ascii=False); print(len(jobs))
