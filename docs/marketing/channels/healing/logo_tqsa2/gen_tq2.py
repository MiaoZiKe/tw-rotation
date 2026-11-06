# 「談晴說礙」LOGO 第二輪 11 款（2026-11-06 Andy：「LOGO元素新增 晴 礙」）：把「晴」「礙」兩個字放進圖形裡
# 規則：「晴」用太陽橘、「礙」用雲灰（淺底自動加深到對比 ≥4.5:1）；全自繪向量；字型 Noto Sans/Serif CJK TC（OFL）
# 圖層：h＝承載字的底（雲／太陽盤／章面）、x＝裝飾（光芒、描邊、波浪）、g1＝「晴」、g2＝「礙」
# 重跑：rm -f fit.json; python3 gen_tq2.py && node render.js && python3 fit_tq2.py && python3 gen_tq2.py && node render.js && python3 post_tq2.py
import sys, os, json, math
import numpy as np
from PIL import Image, ImageFont, ImageDraw
H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(H, '..', 'logo_rrxq2'))
os.chdir(os.path.join(H, '..', 'logo_rrxq2')); import gen; os.chdir(H)
TONES, L = gen.TONES, gen.L
CHK = '/tmp/claude-0/-home-user-tw-rotation/ce50d787-1067-5482-ab44-99dc39a48890/scratchpad/tqsa2'; os.makedirs(CHK, exist_ok=True)
FIT = json.load(open('fit.json')) if os.path.exists('fit.json') else {}
NAME = '談晴說礙'; SUB = '礙還在，晴也在。'
def rgb(h): return [int(h[i:i+2], 16) for i in (1, 3, 5)]
def blend(a, b, t):
    return '#' + ''.join(f'{round(x+(y-x)*t):02X}' for x, y in zip(rgb(a), rgb(b)))
def lum(h):
    f = lambda c: c/12.92 if c <= .03928 else ((c+.055)/1.055)**2.4
    r, g, b = [f(v/255) for v in rgb(h)]; return .2126*r+.7152*g+.0722*b
def ratio(a, b):
    x, y = sorted((lum(a), lum(b)), reverse=True); return (x+.05)/(y+.05)
def fix(base, fills, toward, target=4.5):
    for i in range(51):
        c = blend(base, toward, i/50)
        if all(ratio(c, f) >= target for f in fills): return c
    return toward
mono = lambda P: P.get('mono')
CRP = []   # 對比紀錄：(說明, 前景, 背景, 比值)
def rec(tag, what, fg, bg): CRP.append(dict(tone=tag, what=what, fg=fg, bg=bg, ratio=round(ratio(fg, bg), 2)))
# 色彩函式：fill＝字所在的底色
def SF(P): return P['bg'] if mono(P) else blend(P['S'], P['bg'], .72)           # 太陽盤底（淺橘）
def CF(P): return P['bg'] if mono(P) else blend(P['C'], P['bg'], .45)           # 雲底（淺灰）
def TQ(P, fill=None): return P['ink'] if mono(P) else fix(P['S'], [fill or P['bg']], P['ink'])   # 晴字色
def TA(P, fill=None): return P['ink'] if mono(P) else fix(P['C'], [fill or P['bg']], P['ink'])   # 礙字色
def OL(P, w=12): return f'stroke="{P["ink"]}" stroke-width="{w}" stroke-linejoin="round"' if mono(P) else ''
def SUNC(P): return P['ink'] if mono(P) else P['S']
def CLC(P): return P['ink'] if mono(P) else P['C']
def G(P, ch, fs, cx, cy, col, kind='sans', bold=5): return gen.glyph(ch, kind, fs, cx, cy, col, bold=bold)
def cloud(cx, cy, s, col, extra=''):
    return (f'<g transform="translate({cx} {cy}) scale({s})" fill="{col}" {extra}><circle cx="-60" cy="0" r="70"/><circle cx="20" cy="-30" r="90"/>'
            f'<circle cx="100" cy="10" r="60"/><rect x="-130" y="0" width="290" height="70" rx="35"/></g>')
def sunhold(P, cx, cy, r, ring=14, clip=''):   # 太陽盤：淺橘底＋橘圈
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{SF(P)}" stroke="{SUNC(P)}" stroke-width="{ring if not mono(P) else 12}" {clip}/>'
def cloudhold(P, cx, cy, s, bgring=0):         # 雲底：淺灰底；單色用描邊
    ex = f'stroke="{P["bg"]}" stroke-width="{bgring}" stroke-linejoin="round" paint-order="stroke"' if bgring else ''
    if mono(P):   # 單色：外描墨線、內填底色
        return (cloud(cx, cy, s, P['ink'], f'stroke="{P["ink"]}" stroke-width="{26 if True else 0}" stroke-linejoin="round"') + cloud(cx, cy, s, P['bg']))
    return cloud(cx, cy, s, CF(P), ex)
def rays(P, cx, cy, r1, r2, n, w, a0=0, a1=360): return gen.rays(cx, cy, r1, r2, n, w, SUNC(P), a0, a1)
def scallop(cx, cy, r): return f'<circle cx="{cx}" cy="{cy}" r="{r}"/>'

# ---- 01 雲帶缺口．晴：頂上一條雲帶寫「礙」，缺口的小太陽裡寫「晴」
def s1(P):
    tc = TA(P, CF(P)); tq = TQ(P, SF(P))
    def bar(x1, x2, y, hgt, bumps=()):
        return f'<rect x="{x1}" y="{y}" width="{x2-x1}" height="{hgt}" rx="{hgt/2}"/>' + ''.join(f'<circle cx="{bx}" cy="{by}" r="{br}"/>' for bx, by, br in bumps)
    def grp(inner):
        if mono(P): return f'<g fill="{P["ink"]}" stroke="{P["ink"]}" stroke-width="26" stroke-linejoin="round">{inner}</g><g fill="{P["bg"]}">{inner}</g>'
        return f'<g fill="{CF(P)}">{inner}</g>'
    top = grp(bar(-250, 250, -250, 170, ((-120, -250, 62), (30, -272, 84), (170, -245, 54))))
    side = grp(bar(-290, -160, 20, 66, ((-225, 22, 38),)) + bar(160, 290, 20, 66, ((225, 22, 38),)) + bar(-250, 250, 250, 60, ((-90, 252, 38), (80, 246, 46))))
    sun = sunhold(P, 0, 62, 126)
    return L('h', top + side + sun) + L('g2', G(P, '礙', 118, 0, -165, tc)) + L('g1', G(P, '晴', 140, 0, 64, tq))
# ---- 02 雲帶淡礙：大「礙」襯在雲帶後面、被雲帶蓋住一部分；缺口小太陽裡是「晴」
def s2(P):
    bars = ''
    for x1, x2, y in ((-280, 130, -225), (-300, -140, -75), (140, 300, -75), (-130, 280, 150)):
        bars += f'<rect x="{x1}" y="{y}" width="{x2-x1}" height="70" rx="35"/>'
    gl = P['ink'] if mono(P) else blend(P['bg'], TA(P), .55)
    back = G(P, '礙', 580, 0, 0, gl, bold=6)
    if mono(P): barsvg = f'<g fill="{P["bg"]}" stroke="{P["ink"]}" stroke-width="14" stroke-linejoin="round">{bars}</g>'
    else: barsvg = f'<g fill="{CF(P)}" stroke="{P["bg"]}" stroke-width="16" stroke-linejoin="round" paint-order="stroke">{bars}</g>'
    bgc = f'<circle cx="0" cy="25" r="128" fill="{P["bg"]}"/>'
    return L('x', back) + L('h', bgc + barsvg + sunhold(P, 0, 25, 108)) + L('g1', G(P, '晴', 120, 0, 28, TQ(P, SF(P))))
# ---- 03 雙泡對話：灰雲泡說「礙」，橘日泡談「晴」
def s3(P):
    tc = TA(P, CF(P)); tq = TQ(P, SF(P)); c = CF(P) if not mono(P) else P['bg']
    tail_c = f'<path d="M -170 135 L -245 235 L -105 150 Z" fill="{c}" {OL(P, 10)}/>'
    cl = cloudhold(P, -80, 60, 1.35)
    sun = sunhold(P, 165, -150, 130)
    tail_s = f'<path d="M 235 -50 L 290 30 L 180 -30 Z" fill="{SF(P)}" stroke="{SUNC(P)}" stroke-width="10" stroke-linejoin="round"/>'
    return L('x', rays(P, 165, -150, 152, 182, 6, 14, -175, -25)) + L('h', tail_c + cl + tail_s + sun) + L('g2', G(P, '礙', 135, -53, 72, tc)) + L('g1', G(P, '晴', 135, 165, -148, tq))
# ---- 04 雲朵對話框：雲朵泡裡是「礙」，泡的尾巴是一顆小太陽，上面寫「晴」
def s4(P):
    tc = TA(P, CF(P)); tq = TQ(P, SF(P))
    cl = cloudhold(P, 20, -90, 1.6)
    ring = f'<circle cx="-120" cy="115" r="122" fill="{P["bg"]}"/>'
    return L('h', cl + ring + sunhold(P, -120, 115, 105)) + L('g2', G(P, '礙', 185, 42, -95, tc)) + L('g1', G(P, '晴', 125, -120, 118, tq))
# ---- 05 半晴半礙：一顆圓，左半雲灰寫「礙」、右半太陽橘寫「晴」，交界是雲的波浪邊
def s5(P):
    tc = TA(P, CF(P)); tq = TQ(P, SF(P))
    edge = 'M 0 -240 C -40 -200 30 -160 -10 -120 C -50 -80 20 -40 -20 0 C -60 40 10 80 -30 120 C -70 160 0 200 0 240'
    cp = '<clipPath id="ccl"><circle cx="0" cy="0" r="238"/></clipPath>'
    h = (f'<defs>{cp}</defs><g clip-path="url(#ccl)"><rect x="-240" y="-240" width="480" height="480" fill="{CF(P)}"/>'
         f'<path d="{edge} L 240 240 L 240 -240 Z" fill="{SF(P)}"/></g>')
    ring = f'<circle cx="0" cy="0" r="238" fill="none" stroke="{P["ink"] if mono(P) else P["S"]}" stroke-width="{12 if mono(P) else 14}"/>'
    sep = f'<path d="{edge}" fill="none" stroke="{P["ink"]}" stroke-width="10" stroke-linecap="round"/>' if mono(P) else ''
    return L('h', h) + L('x', ring + sep) + L('g2', G(P, '礙', 142, -125, 0, tc, bold=6)) + L('g1', G(P, '晴', 150, 122, 0, tq, bold=6))
# ---- 06 日旁成日、雲遮礙：「晴」的日字旁換成小太陽；「礙」的下半被一朵雲遮住
def split_x(ch, fs):
    f = ImageFont.truetype(gen.FONTS['sans'][2], fs); l, t, r, b = f.getbbox(ch, anchor='ls')
    im = Image.new('L', (int(r-l)+40, int(b-t)+40), 0); ImageDraw.Draw(im).text((20-l, 20-t), ch, font=f, fill=255, anchor='ls')
    a = np.array(im) > 60; cols = a.any(0); xs = np.nonzero(cols)[0]; x0 = xs.min(); x = x0
    while cols[x]: x += 1
    return (x0-20+l, x-20+l, (r-l))
def s6(P):
    tq = TQ(P); tc = TA(P)
    fs = 215; l0, l1, wd = split_x('晴', fs); cx = 130
    gx, gy = gen.gp('晴', 'sans', fs, cx, -40)
    rl = gx + l0; rr = gx + l1; sx = (rl+rr)/2; sr = (rr-rl)/2*1.75
    sh = 40
    clip = f'<clipPath id="qc"><rect x="{rr+3}" y="-300" width="400" height="600"/></clipPath>'
    qing = f'<defs>{clip}</defs><g clip-path="url(#qc)"><g transform="translate({sh} 0)">' + gen.TX('晴', 'sans', fs, gx, gy, tq, bold=5) + '</g></g>'
    sunc = f'<circle cx="{sx:.1f}" cy="-40" r="{sr:.1f}" fill="{P["ink"] if mono(P) else P["S"]}"/>' + gen.rays(sx, -40, sr+10, sr+34, 6, 10, P['ink'] if mono(P) else P['S'], 150, 390) if False else f'<circle cx="{sx:.1f}" cy="-40" r="{sr:.1f}" fill="{P["ink"] if mono(P) else P["S"]}"/>'
    ai = G(P, '礙', 215, -140, -40, tc, bold=5)
    cl = cloudhold(P, -150, 160, 1.2, bgring=16)
    return L('g2', ai) + L('h', cl) + L('g1', sunc + qing)
# ---- 07 圓章：「晴」在上、「礙」在下，上緣一圈光芒、下緣一圈雲邊
def s7(P):
    fillc = P['bg'] if mono(P) else blend(P['bg'], P['S'], .10)
    tq = TQ(P, fillc); tc = TA(P, fillc)
    h = f'<circle cx="0" cy="0" r="238" fill="{fillc}"/>'
    ring = f'<circle cx="0" cy="0" r="238" fill="none" stroke="{P["ink"] if mono(P) else CLC(P)}" stroke-width="14"/><circle cx="0" cy="0" r="212" fill="none" stroke="{P["ink"] if mono(P) else CLC(P)}" stroke-width="5"/>'
    top = rays(P, 0, 0, 266, 312, 9, 16, -165, -15)
    cs = ''.join(f'<circle cx="{268*math.cos(math.radians(a)):.1f}" cy="{268*math.sin(math.radians(a)):.1f}" r="22" fill="{CLC(P)}"/>' for a in range(30, 151, 20))
    wave = f'<path d="M -110 0 C -85 -22 -60 22 -35 0 S 15 -22 40 0 S 90 22 110 0" fill="none" stroke="{CLC(P)}" stroke-width="12" stroke-linecap="round"/>'
    return L('x', top + cs) + L('h', h) + L('x', ring + wave) + L('g1', G(P, '晴', 165, 0, -104, tq, 'serif', 5)) + L('g2', G(P, '礙', 165, 0, 106, tc, 'serif', 5))
# ---- 08 四字方印：談 晴／說 礙 的 2×2 方印，「晴」橘、「礙」灰
def s8(P):
    fillc = P['bg'] if mono(P) else blend(P['bg'], P['C'], .18)
    ink = P['ink']; tq = TQ(P, fillc); tc = TA(P, fillc)
    h = f'<rect x="-250" y="-250" width="500" height="500" rx="64" fill="{fillc}"/>'
    ring = f'<rect x="-250" y="-250" width="500" height="500" rx="64" fill="none" stroke="{ink if mono(P) else CLC(P)}" stroke-width="16"/><rect x="-222" y="-222" width="444" height="444" rx="44" fill="none" stroke="{ink if mono(P) else CLC(P)}" stroke-width="5"/>'
    d = 108; fs = 172
    return L('h', h) + L('x', ring) + L('g3', G(P, '談', fs, -d, -d, ink, 'serif', 4) + G(P, '說', fs, -d, d, ink, 'serif', 4)) + L('g1', G(P, '晴', fs, d, -d, tq, 'serif', 4)) + L('g2', G(P, '礙', fs, d, d, tc, 'serif', 4))
# ---- 09 雲帶夾字：「晴」在上、一道雲帶隔開、「礙」在下
def s9(P):
    tq = TQ(P); tc = TA(P)
    band = ''.join(scallop(x, -14 if i % 2 == 0 else 14, 30) for i, x in enumerate(range(-210, 211, 70)))
    band = f'<g fill="{CLC(P)}">{band}<rect x="-250" y="-16" width="500" height="32" rx="16"/></g>'
    return L('x', band) + L('g1', G(P, '晴', 240, 0, -172, tq, 'sans', 6)) + L('g2', G(P, '礙', 240, 0, 178, tc, 'sans', 6))
# ---- 10 牆後日出：太陽從一堵灰牆後面升起，日裡寫「晴」，牆上刻「礙」
def s10(P):
    tq = TQ(P, SF(P)); wc = CF(P) if not mono(P) else P['bg']; tc = TA(P, wc)
    cp = '<clipPath id="wl"><rect x="-300" y="-330" width="600" height="400"/></clipPath>'
    sun = f'<defs>{cp}</defs><g clip-path="url(#wl)">' + sunhold(P, 0, -60, 170, 16) + '</g>'
    if mono(P): wall = f'<rect x="-270" y="70" width="540" height="210" rx="26" fill="{P["bg"]}" stroke="{P["ink"]}" stroke-width="14"/>'
    else: wall = f'<rect x="-270" y="70" width="540" height="210" rx="26" fill="{wc}"/>'
    return L('x', rays(P, 0, -60, 198, 252, 7, 16, -170, -10)) + L('h', sun + wall) + L('g1', G(P, '晴', 170, 0, -70, tq)) + L('g2', G(P, '礙', 160, 0, 176, tc))
# ---- 11 晴時多雲：太陽在後（晴）、灰雲在前（礙）；光從沒被擋住的那邊灑出來
def s11(P):
    tq = TQ(P, SF(P)); tc = TA(P, CF(P))
    sun = sunhold(P, 95, -100, 150)
    cl = cloudhold(P, -90, 130, 1.5, bgring=18)
    return L('x', rays(P, 95, -100, 176, 228, 8, 16, -200, 20)) + L('h', sun + cl) + L('g1', G(P, '晴', 150, 118, -125, tq)) + L('g2', G(P, '礙', 146, -70, 120, tc))
SYMS = {
 1: ('01_雲帶缺口晴', '雲帶缺口．晴', '最上面一條雲帶寫著「礙」，雲帶中間缺了一段，缺口裡的小太陽寫著「晴」。', s1),
 2: ('02_雲帶淡礙', '雲帶淡礙', '大大的「礙」襯在後面，被一條條雲帶蓋住一部分；缺口裡的小太陽寫著「晴」：礙還在，晴也在。', s2),
 3: ('03_雙泡對話', '雙泡對話', '兩個對話框：灰雲泡說「礙」，橘色太陽泡談「晴」，正好是「談晴說礙」。', s3),
 4: ('04_雲泡太陽尾', '雲泡太陽尾', '雲朵形狀的對話框裡是「礙」，對話框的尾巴是一顆寫著「晴」的小太陽。', s4),
 5: ('05_半晴半礙', '半晴半礙', '一顆圓，左半雲灰寫「礙」、右半太陽橘寫「晴」，交界是雲朵的波浪邊。', s5),
 6: ('06_日旁成日', '日旁成日', '「晴」的日字旁換成一顆真正的太陽；「礙」的下半被一朵雲遮住。', s6),
 7: ('07_圓章', '圓章', '一枚圓章：「晴」在上、「礙」在下；上緣一圈光芒、下緣一圈雲邊，中間一道雲浪分隔。', s7),
 8: ('08_四字方印', '四字方印', '「談晴說礙」四個字排成 2×2 的方印，「晴」橘、「礙」灰、談與說用墨色。', s8),
 9: ('09_雲帶夾字', '雲帶夾字', '「晴」在上、一道雲帶隔開、「礙」在下：兩個字就是一個 LOGO。', s9),
 10: ('10_牆後日出', '牆後日出', '太陽從一堵灰牆後面升起，日裡寫「晴」，牆上刻「礙」。', s10),
 11: ('11_晴時多雲', '晴時多雲', '太陽（晴）在後、灰雲（礙）在前，光從沒被擋住的那一邊灑出來。', s11),
}
# 允許的「刻意重疊」：n -> 說明（其餘一律不准疊）
ALLOW = {2: '「礙」襯在雲帶後面，雲帶刻意蓋住一部分（雲帶有背景色描邊）', 4: '太陽尾巴壓在雲泡一角（背景色描邊分隔）', 6: '雲刻意遮住「礙」下半（背景色描邊）', 10: '牆刻意擋住太陽下半', 11: '雲刻意壓在太陽前（背景色描邊）'}
# 頭像簡化版（只留一個字）：A 晴日、B 礙雲
def simpleA(P):
    tq = TQ(P, SF(P)); return L('x', rays(P, 0, 0, 200, 262, 12, 20)) + L('h', sunhold(P, 0, 0, 175, 18)) + L('g1', G(P, '晴', 230, 0, 4, tq, 'sans', 8))
def simpleB(P):
    tc = TA(P, CF(P)); return L('h', cloudhold(P, 0, 40, 1.9)) + L('g2', G(P, '礙', 270, 25, 35, tc, 'sans', 8))
SIMPLE = {'A_晴日': ('晴日（只留「晴」）', simpleA), 'B_礙雲': ('礙雲（只留「礙」）', simpleB)}
WH = 420
def wcols(P):
    ink = P['ink']; return [ink, TQ(P), ink, TA(P)]
def wm_svg(P, sym, k, sub, bg=True):
    ink = P['ink']; kind = 'sans'; ls = 14
    fs = 150 if not sub else 134; ty = 210 if not sub else 170; symsz = 372
    tw = gen.text_w(NAME, kind, fs, ls); x0 = 60+symsz+54; W = int(x0+tw+70)
    body = L('sym', f'<g transform="translate({60+symsz/2} 210) scale({k})">{sym}</g>')
    txt = ''
    for i, ch in enumerate(NAME):
        x = x0 + (gen.text_w(NAME[:i], kind, fs, ls) + ls if i else 0)
        txt += gen.TX(ch, kind, fs, x, ty+.36*fs, wcols(P)[i], bold=2)
    body += L('txt', txt)
    if sub: body += L('sub', gen.TX(SUB, 'sans', 44, x0, 345, ink, ls=7))
    bgr = f'<rect width="{W}" height="{WH}" fill="{P["bg"]}"/>' if bg else ''
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{WH}" viewBox="0 0 {W} {WH}"><defs>{gen.defs(P)}</defs>{bgr}{body}</svg>', W
if __name__ == '__main__':
    jobs = []; N = TONES['奶油晨光']
    for n, (fo, nm, mean, fn) in SYMS.items():
        os.makedirs(fo, exist_ok=True)
        far = FIT.get(str(n), 300); ka = min(420/far*.96, 1.8); kw = min(172/far, 1.2)
        for tag, P in TONES.items():
            sym = fn(P)
            p = f'{fo}/頭像_1080方_{tag}'; open(p+'.svg', 'w').write(gen.avatar_svg(P, sym, ka)); jobs.append(dict(n=n, kind='avatar', tag=tag, svg=p+'.svg', png=p+'.png', w=1080, h=1080))
            for sub, suf in ((False, '字標'), (True, '字標含副標')):
                for bg in (True, False):
                    if not bg and mono(P): continue
                    sv, W = wm_svg(P, sym, kw, sub, bg); p = f'{fo}/{suf}_{"" if bg else "透明_"}{tag}'; open(p+'.svg', 'w').write(sv)
                    jobs.append(dict(n=n, kind='wm', tag=tag, svg=p+'.svg', png=p+'.png', w=W, h=WH, transparent=not bg))
            # 對比紀錄
            if not mono(P):
                pass
            for i, ch in enumerate(NAME):
                if ch in '晴礙': rec(tag, f'{n:02d} 字標「{ch}」對底色', wcols(P)[i], P['bg'])
        sym = fn(N)
        open(f'{CHK}/{n}fit.svg', 'w').write(gen.avatar_svg(N, sym, 1.0, bg=False)); jobs.append(dict(n=n, kind='fit', svg=f'{CHK}/{n}fit.svg', png=f'{CHK}/{n}fit.png', w=1080, h=1080, transparent=True))
        open(f'{CHK}/{n}av.svg', 'w').write(gen.avatar_svg(N, sym, ka, bg=False))
        for lay in ('h', 'x', 'g1', 'g2'):
            jobs.append(dict(n=n, kind='chkav', layer=lay, svg=f'{CHK}/{n}av.svg', png=f'{CHK}/{n}av_{lay}.png', w=1080, h=1080, transparent=True, show=[lay]))
        sv, W = wm_svg(N, sym, kw, True, bg=False); open(f'{CHK}/{n}wm.svg', 'w').write(sv)
        for lay in ('sym', 'txt', 'sub'):
            jobs.append(dict(n=n, kind='chkwm', layer=lay, svg=f'{CHK}/{n}wm.svg', png=f'{CHK}/{n}wm_{lay}.png', w=W, h=WH, transparent=True, show=([lay, 'h', 'x', 'g1', 'g2', 'g3'] if lay == 'sym' else [lay])))
    # 頭像簡化版
    os.makedirs('頭像簡化版', exist_ok=True)
    for key, (nm, fn) in SIMPLE.items():
        open(f'{CHK}/s{key[0]}fit.svg', 'w').write(gen.avatar_svg(N, fn(N), 1.0, bg=False)); jobs.append(dict(n=key, kind='sfit', svg=f'{CHK}/s{key[0]}fit.svg', png=f'{CHK}/s{key[0]}fit.png', w=1080, h=1080, transparent=True))
        far = FIT.get('s'+key[0], 300); ka = min(420/far*.96, 1.8)
        for tag, P in TONES.items():
            p = f'頭像簡化版/{key}_頭像_1080方_{tag}'; open(p+'.svg', 'w').write(gen.avatar_svg(P, fn(P), ka)); jobs.append(dict(n=key, kind='savatar', tag=tag, svg=p+'.svg', png=p+'.png', w=1080, h=1080))
    json.dump(dict(jobs=jobs), open('jobs.json', 'w'), ensure_ascii=False); print(len(jobs))
    json.dump(CRP, open('_crp_wm.json', 'w'), ensure_ascii=False)
