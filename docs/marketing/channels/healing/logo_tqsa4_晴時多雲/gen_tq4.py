# 「談晴說礙」LOGO：以簡約第三輪 07 晴時多雲為底，多一點元素＋更多色系（2026-11-06 Andy：「這個挺不錯的 但在多點東西和其他色系」）
# 重跑：rm -f fit.json; python3 gen_tq4.py && node render.js && python3 fit_tq4.py && python3 gen_tq4.py && node render.js && python3 post_tq4.py
import sys, os, json, math
H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(H, '..', 'logo_tqsa3_簡約'))
import gen_tq3 as g; os.chdir(H)
CHK = '/tmp/claude-0/-home-user-tw-rotation/ce50d787-1067-5482-ab44-99dc39a48890/scratchpad/tqsa4'; os.makedirs(CHK, exist_ok=True)
FIT = json.load(open('fit.json')) if os.path.exists('fit.json') else {}
st, fl, SW = g.st, g.fl, g.SW
def thin(c, w=12, op=1): return f'fill="none" stroke="{c}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round" opacity="{op}"'
# 色系：bg 底、ink 主字、sub 副標、a 礙（雲灰）、q 晴（光）
T = {
 '夜版':     ('#2B2A2E', '#F3EEE6', '#B8B1A7', '#CFC9C0', '#F2B35E'),
 '霧紫夜':   ('#2E2B36', '#F1EDF5', '#B9B2C4', '#CFC8DA', '#F2C66E'),
 '深海藍':   ('#1E2733', '#EEF2F6', '#A9B4C0', '#C3CED9', '#F4B860'),
 '森林綠':   ('#212B25', '#EEF2EC', '#AEB8AE', '#C5CFC3', '#F2B35E'),
 '暖陶棕':   ('#3A2F2B', '#F5EDE6', '#C2B3A8', '#D9CBBE', '#F3A65A'),
 '晝版':     ('#F6F1E8', '#2F2D2B', '#6E6A66', '#6E6A66', '#D9822B'),
 '奶油晨光': ('#FFF6E5', '#3A3A3A', '#6E6A66', '#7A746E', '#D9822B'),
 '晴空淡藍': ('#EAF4FB', '#1F3C54', '#4F6577', '#5F7384', '#D98A2B'),
 '抹茶午後': ('#EEF2E6', '#2F3F29', '#5A6A55', '#6B7A66', '#C97A2B'),
 '蜜桃傍晚': ('#FCEDE6', '#5A4636', '#7A6656', '#8A7566', '#C9672B'),
}
TONES = {k: dict(bg=v[0], ink=v[1], sub=v[2], a=v[3], q=v[4]) for k, v in T.items()}
for P in TONES.values():   # 符號色對底至少 3:1（圖形門檻）
    P['q'] = g.fix(P['q'], P['bg'], P['ink'], 3.0); P['a'] = g.fix(P['a'], P['bg'], P['ink'], 3.0)
# 2026-11-06 Andy：「礙這字顏色不明顯」→ 字標裡的「礙」改用雨雲藍（淺底 #3F5E78、深底 #A9C3D8），和「談說」的墨色、「晴」的橘都分得開
for k, P in TONES.items():
    P['at'] = g.fix('#A9C3D8', P['bg'], P['ink']) if g.lum(P['bg']) < .2 else g.fix('#3F5E78', P['bg'], P['ink'])
_ta = g.ta_text
g.ta_text = lambda P: P['at'] if 'at' in P else _ta(P)
TONES['單色黑'] = g.TONES['單色黑']; TONES['單色白'] = g.TONES['單色白']
# ---- 基本：太陽弧＋雲（同第三輪 07）
def sun_arc(q):
    P = lambda d: (80+110*math.cos(math.radians(d)), -50+110*math.sin(math.radians(d)))
    (x1, y1), (x2, y2) = P(195), P(395)
    return f'<path d="M {x1:.1f} {y1:.1f} A 110 110 0 0 1 {x2:.1f} {y2:.1f}" {st(q)}/>'
CLOUD = 'M -120 120 H 110 A 40 40 0 0 0 110 40 A 67.5 67.5 0 0 0 -25 35 A 55 55 0 0 0 -120 120 Z'
def cloud(a): return f'<path d="{CLOUD}" {st(a)}/>'
def rays(q, angs=(235, 270, 305), r1=145, r2=180, w=SW):
    s = ''
    for d in angs:
        c, sn = math.cos(math.radians(d)), math.sin(math.radians(d))
        s += f'<line x1="{80+r1*c:.1f}" y1="{-50+r1*sn:.1f}" x2="{80+r2*c:.1f}" y2="{-50+r2*sn:.1f}" {st(q).replace(f"stroke-width=\"{SW}\"", f"stroke-width=\"{w}\"")}/>'
    return s
def spark(q, x, y, r):
    return f'<path d="M {x} {y-r} Q {x} {y} {x+r} {y} Q {x} {y} {x} {y+r} Q {x} {y} {x-r} {y} Q {x} {y} {x} {y-r} Z" fill="{q}"/>'
def v1(q, a): return sun_arc(q), cloud(a)
def v2(q, a): return sun_arc(q) + rays(q), cloud(a)                                  # 三道短光
def v3(q, a): return sun_arc(q) + spark(q, -105, -110, 30) + f'<circle cx="-150" cy="-55" r="9" fill="{q}"/>', cloud(a)   # 一顆星芒、一個光點
def v4(q, a): return sun_arc(q), cloud(a) + f'<g transform="translate(-130 -95) scale(.42)"><path d="{CLOUD}" {thin(a, SW/.42)}/></g>'   # 遠方一朵小雲
def v5(q, a): return sun_arc(q), cloud(a) + f'<path d="M -170 172 H 40 M 90 172 H 190" {st(a)}/>'   # 地平線（中間留一段空，晴從那裡出來）
def v6(q, a): return sun_arc(q), cloud(a) + f'<path d="M -5 78 A 50 50 0 0 1 62 62" {thin(a, 14)}/><path d="M -95 98 A 30 30 0 0 1 -62 82" {thin(a, 14)}/>'   # 雲裡一道內線，雲更立體
def v7(q, a):   # 地上的光：雲的影子是灰的，旁邊那一段地面被晴照亮
    return sun_arc(q) + f'<path d="M 70 172 H 190" {st(q)}/>', cloud(a) + f'<path d="M -170 172 H 20" {st(a)}/>'
def v8(q, a):   # 雲變成對話框（談、說）
    return sun_arc(q), f'<path d="M -120 120 H 110 A 40 40 0 0 0 110 40 A 67.5 67.5 0 0 0 -25 35 A 55 55 0 0 0 -120 120 Z" {st(a)}/><path d="M -70 120 L -95 175 L -25 120" {st(a)}/>'
def v9(q, a): return sun_arc(q) + rays(q, (225, 260, 295, 330), 145, 172, 18) + spark(q, -120, -120, 26), cloud(a)   # 光芒＋星芒
def v10(q, a):  # 雙層太陽弧：光一圈一圈往外
    Pp = lambda r, d: (80+r*math.cos(math.radians(d)), -50+r*math.sin(math.radians(d)))
    (x1, y1), (x2, y2) = Pp(160, 210), Pp(160, 330)
    return sun_arc(q) + f'<path d="M {x1:.1f} {y1:.1f} A 160 160 0 0 1 {x2:.1f} {y2:.1f}" {thin(q, 14, .9)}/>', cloud(a)
SYMS = {
 1: ('01_原版', '原版', '太陽被雲擋住一半，只露出上緣的弧（第三輪 07）。', '露出的太陽弧', '雲輪廓', v1),
 2: ('02_三道光', '三道光', '太陽上方多三道短光：被擋住，光還是往外走。', '太陽弧＋三道光', '雲輪廓', v2),
 3: ('03_星芒', '星芒', '左上多一顆星芒和一個光點：雲旁邊，也有一點亮。', '太陽弧＋星芒', '雲輪廓', v3),
 4: ('04_遠雲', '遠雲', '遠方多一朵小雲：礙不只一個，晴還是在。', '太陽弧', '雲＋遠方小雲', v4),
 5: ('05_地平線', '地平線', '底下一道地平線，中間留一段空：晴從空隙裡出來。', '太陽弧', '雲＋地平線', v5),
 6: ('06_雲的層次', '雲的層次', '雲裡多一道內線，雲更立體。', '太陽弧', '雲＋內線', v6),
 7: ('07_地上的光', '地上的光', '雲的影子落在地上是灰的，旁邊那一段地面被晴照亮。', '太陽弧＋亮起的地面', '雲＋灰色地面', v7),
 8: ('08_雲朵對話框', '雲朵對話框', '雲多一個對話框尾巴：說著礙，晴在後面。', '太陽弧', '雲朵對話框', v8),
 9: ('09_光芒星芒', '光芒星芒', '四道光加一顆星芒，最明亮的一版。', '太陽弧＋光芒＋星芒', '雲輪廓', v9),
 10: ('10_雙層光', '雙層光', '太陽外多一圈淡淡的光：光一圈一圈往外。', '太陽弧＋外圈光', '雲輪廓', v10),
}
g.SYMS = SYMS
if __name__ == '__main__':
    jobs = []
    def add(**k): jobs.append(k)
    for n, (fo, nm, mean, qd, ad, fn) in SYMS.items():
        os.makedirs(fo, exist_ok=True)
        fit = FIT.get(str(n), [0, 0, 260]); cx, cy, far = fit; ka = 330/far
        for tag, P in TONES.items():
            p = f'{fo}/頭像_1080方_{tag}'; open(p+'.svg', 'w').write(g.avatar_svg(n, P, True, ka, (cx, cy))); add(svg=p+'.svg', png=p+'.png', w=1080, h=1080, kind='avatar', n=n, tag=tag)
            for sub, suf in ((False, '字標'), (True, '字標含副標')):
                for bg in ((True, False) if not P.get('mono') else (True,)):
                    sv, W, Hh = g.wm_svg(n, P, sub, bg, fit=fit, **g.DEFAULT); p = f'{fo}/{suf}_{"" if bg else "透明_"}{tag}'
                    open(p+'.svg', 'w').write(sv); add(svg=p+'.svg', png=p+'.png', w=W, h=Hh, kind='wm', n=n, tag=tag, transparent=not bg)
        N = TONES['夜版']
        open(f'{CHK}/{n}fit.svg', 'w').write(g.avatar_svg(n, N, False, 1.0)); add(svg=f'{CHK}/{n}fit.svg', png=f'{CHK}/{n}fit.png', w=1080, h=1080, transparent=True, kind='fit', n=n)
        open(f'{CHK}/{n}av.svg', 'w').write(g.avatar_svg(n, N, False, ka, (cx, cy)))
        for lay in ('a', 'q'): add(svg=f'{CHK}/{n}av.svg', png=f'{CHK}/{n}av_{lay}.png', w=1080, h=1080, transparent=True, show=[lay], kind='chk', n=n)
        sv, W, Hh = g.wm_svg(n, N, True, False, fit=fit, **g.DEFAULT); open(f'{CHK}/{n}wm.svg', 'w').write(sv)
        for lay in ('sym', 'txt', 'sub'):
            add(svg=f'{CHK}/{n}wm.svg', png=f'{CHK}/{n}wm_{lay}.png', w=W, h=Hh, transparent=True, show=([lay, 'a', 'q'] if lay == 'sym' else [lay]), kind='chk', n=n)
    json.dump(dict(jobs=jobs), open('jobs.json', 'w'), ensure_ascii=False); print(len(jobs))
