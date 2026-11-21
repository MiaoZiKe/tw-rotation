# 「談晴說礙」LOGO 9 款（2026-11-06 Andy：「名稱就定談晴說礙 做LOGO給我看」）
# 主軸：雲＝礙（擋在前面的難），太陽＝晴（希望、正向）；字標「晴」太陽橘、「礙」雲灰；副標「礙還在，晴也在。」
# 重跑：rm -f fit.json; python3 gen_tq.py && node render.js && python3 fit_tq.py && python3 gen_tq.py && node render.js && python3 post_tq.py
import sys, os, json
H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(H, '..', 'logo_rrxq2')); sys.path.insert(0, os.path.join(H, '..', 'logo_rrxq6_雲帶'))
os.chdir(os.path.join(H, '..', 'logo_rrxq2')); import gen; os.chdir(H)
os.chdir(os.path.join(H, '..', 'logo_rrxq6_雲帶')); import gen6; os.chdir(H)
TONES, L = gen.TONES, gen.L
CHK = '/tmp/claude-0/-home-user-tw-rotation/ce50d787-1067-5482-ab44-99dc39a48890/scratchpad/tqsa'; os.makedirs(CHK, exist_ok=True)
FIT = json.load(open('fit.json')) if os.path.exists('fit.json') else {}
NAME = '談晴說礙'; SUB = '礙還在，晴也在。'
def blend(a, b, t):
    a = [int(a[i:i+2], 16) for i in (1, 3, 5)]; b = [int(b[i:i+2], 16) for i in (1, 3, 5)]
    return '#' + ''.join(f'{round(x+(y-x)*t):02X}' for x, y in zip(a, b))
mono = lambda P: P.get('mono')
def CL(P): return P['ink'] if mono(P) else P['C']                  # 雲（礙）
def SU(P): return P['bg'] if mono(P) else P['S']                   # 太陽（晴）
def SST(P, w=12): return f'stroke="{P["ink"]}" stroke-width="{w}"' if mono(P) else ''
def RAYC(P): return P['ink'] if mono(P) else P['S']
def cloud(cx, cy, s, col, extra=''):
    return (f'<g transform="translate({cx} {cy}) scale({s})" fill="{col}" {extra}><circle cx="-60" cy="0" r="70"/><circle cx="20" cy="-30" r="90"/>'
            f'<circle cx="100" cy="10" r="60"/><rect x="-130" y="0" width="290" height="70" rx="35"/></g>')
# 1 雲帶缺口（第二輪 07 原版）
def s1(P): return gen.s7(P)
# 2 雲帶精修（光暈）
def s2(P): return gen6.sC(P)
# 3 晴時多雲：太陽在後、雲在前，光從沒被擋住的那邊灑出來
def s3(P):
    sun = f'<circle cx="70" cy="-70" r="118" fill="{SU(P)}" {SST(P)}/>' + gen.rays(70, -70, 150, 200, 9, 18, RAYC(P), -200, 20)
    cl = cloud(-40, 80, 1.25, CL(P), f'stroke="{P["bg"]}" stroke-width="14"' if not mono(P) else f'stroke="{P["bg"]}" stroke-width="14"')
    return L('b', sun) + L('a', cl)
# 4 半晴半礙：一顆圓，左半是雲灰、右半是太陽橘，交界是雲朵的波浪邊
def s4(P):
    edge = 'M 0 -240 C -40 -200 30 -160 -10 -120 C -50 -80 20 -40 -20 0 C -60 40 10 80 -30 120 C -70 160 0 200 0 240'
    right = f'<clipPath id="ccl"><circle cx="0" cy="0" r="230"/></clipPath>'
    g = (f'<defs>{right}</defs><g clip-path="url(#ccl)"><rect x="-240" y="-240" width="480" height="480" fill="{CL(P)}"/>'
         f'<path d="{edge} L 240 240 L 240 -240 Z" fill="{SU(P)}"/></g>')
    ring = f'<circle cx="0" cy="0" r="230" fill="none" stroke="{P["ink"]}" stroke-width="{12 if mono(P) else 0}"/>'
    dot = gen.rays(110, 0, 52, 78, 8, 12, P['bg'] if not mono(P) else P['ink']) + f'<circle cx="110" cy="0" r="36" fill="{P["bg"] if not mono(P) else P["ink"]}"/>'
    return L('a', g + ring) + L('b', dot)
# 5 談與說：兩個對話框，一個是雲（說礙），一個是太陽（談晴）
def s5(P):
    c = CL(P)
    left = cloud(-95, 40, .95, c) + f'<path d="M -150 100 L -200 170 L -100 110 Z" fill="{c}"/>'
    sb = f'<circle cx="140" cy="-90" r="96" fill="{SU(P)}" {SST(P)}/><path d="M 170 -10 L 210 60 L 120 -8 Z" fill="{SU(P)}" {SST(P, 10)}/>'
    sr = gen.rays(140, -90, 118, 146, 10, 12, RAYC(P))
    return L('a', left) + L('b', sb + sr)
# 6 雲朵對話框：說著說著，裡面出現一顆小太陽
def s6(P):
    c = CL(P)
    bub = cloud(-10, 0, 1.45, c) + f'<path d="M -110 90 L -170 190 L -40 100 Z" fill="{c}"/>'
    return L('a', bub) + L('b', f'<circle cx="20" cy="18" r="56" fill="{P["bg"]}"/><circle cx="20" cy="18" r="40" fill="{SU(P)}" {SST(P, 8)}/>')
# 7 磚牆後的日出：一排矮磚是礙，太陽從後面升起來
def s7(P):
    c = CL(P); bricks = ''
    for row, y in enumerate((60, 140)):
        off = 0 if row == 0 else 60
        for i in range(-2, 3 if row == 0 else 2):
            x = i*120 - 50 + off
            bricks += f'<rect x="{x}" y="{y}" width="108" height="68" rx="16" fill="{c}"/>'
    sun = f'<clipPath id="wl"><rect x="-300" y="-300" width="600" height="352"/></clipPath><g clip-path="url(#wl)"><circle cx="10" cy="60" r="130" fill="{SU(P)}" {SST(P)}/></g>'
    return L('b', sun + gen.rays(10, 60, 160, 210, 7, 18, RAYC(P), -165, -15)) + L('a', bricks)
# 8 晴礙字章：圓章裡兩個字，「晴」橘、「礙」灰
def s8(P):
    ink = P['ink']; ring = f'<circle cx="0" cy="0" r="250" fill="none" stroke="{ink}" stroke-width="16"/><circle cx="0" cy="0" r="222" fill="none" stroke="{ink}" stroke-width="5"/>'
    t = gen.TX('晴', 'serif', 190, -205, 68, ink if mono(P) else P['S']) + gen.TX('礙', 'serif', 190, 15, 68, ink if mono(P) else blend(P['C'], ink, .45))
    return L('a', ring) + L('b', t)
# 9 太陽露臉：雲擋住太陽一角，光從另一邊照出來
def s9(P):
    sun = f'<circle cx="40" cy="-30" r="150" fill="{SU(P)}" {SST(P)}/>' + gen.rays(40, -30, 180, 232, 7, 18, RAYC(P), -150, 30)
    cl = cloud(-110, 90, .95, CL(P), f'stroke="{P["bg"]}" stroke-width="14"')
    return L('b', sun) + L('a', cl)
VAR = [
 (1, '01_雲帶缺口', '雲帶缺口', '一層層雲帶是擋在前面的礙，中間缺了一段，露出一小塊晴。', s1),
 (2, '02_雲帶精修', '雲帶精修', '同樣的雲帶缺口，小太陽外多一圈光暈：礙還在，晴也在。', s2),
 (3, '03_晴時多雲', '晴時多雲', '雲擋在前面，太陽在後面，光從沒被擋住的那一邊灑出來。', s3),
 (4, '04_半晴半礙', '半晴半礙', '一顆圓，一半是雲的灰、一半是太陽的橘：這一代的日子，兩邊都有。', s4),
 (5, '05_談與說', '談與說', '兩個對話框：灰色雲朵說礙，橘色太陽談晴。', s5),
 (6, '06_雲朵對話框', '雲朵對話框', '一個雲朵形狀的對話框，說著說著，裡面出現一顆小太陽。', s6),
 (7, '07_磚牆日出', '磚牆日出', '一排矮磚是擋在前面的礙，太陽從後面升起來。', s7),
 (8, '08_晴礙字章', '晴礙字章', '一枚圓章，「晴」是太陽橘、「礙」是雲灰，名字本身就是 LOGO。', s8),
 (9, '09_太陽露臉', '太陽露臉', '雲擋住太陽一角，光還是從另一邊照出來。', s9),
]
WH = 420
def wm_svg(P, sym, k, sub, bg=True):
    ink = P['ink']; kind = 'sans'; ls = 14
    fs = 150 if not sub else 134; ty = 210 if not sub else 170; symsz = 372
    tw = gen.text_w(NAME, kind, fs, ls); x0 = 60+symsz+54; W = int(x0+tw+70)
    body = L('sym', f'<g transform="translate({60+symsz/2} 210) scale({k})">{sym}</g>')
    cols = [ink, ink if mono(P) else P['S'], ink, ink if mono(P) else blend(P['C'], ink, .45)]
    txt = ''
    for i, ch in enumerate(NAME):
        x = x0 + (gen.text_w(NAME[:i], kind, fs, ls) + ls if i else 0)
        txt += gen.TX(ch, kind, fs, x, ty+.36*fs, cols[i])
    body += L('txt', txt)
    if sub: body += L('sub', gen.TX(SUB, 'sans', 44, x0, 345, ink, ls=7))
    bgr = f'<rect width="{W}" height="{WH}" fill="{P["bg"]}"/>' if bg else ''
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{WH}" viewBox="0 0 {W} {WH}"><defs>{gen.defs(P)}</defs>{bgr}{body}</svg>', W
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
