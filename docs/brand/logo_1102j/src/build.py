import sys, os, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import OUT, run, n2
import designs as DS
from playwright.sync_api import sync_playwright
NAVY, CREAM, OR = '#1F2A44', '#FFF7E8', '#E8590C'
K = 5.12
def tile_inner(bg, inner):
    return f'<rect width="512" height="512" fill="{bg}"/><g transform="scale({K})">{inner}</g>'
def svg(w, h, body, size=None):
    s = size or (w, h)
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{s[0]}" height="{s[1]}" viewBox="0 0 {w} {h}">{body}</svg>'
def text_paths(font, txt, size, fill, track=0):
    items, w = run(font, txt, size, track)
    return ''.join(f'<path transform="translate({n2(x)},0)" d="{d}" fill="{fill}"/>' for ch, d, x, adv, b in items), w
def horizontal(bg, inner):
    th = 236
    t1, w1 = text_paths('sans', '哩股哩股', 118, NAVY, 0.04)
    t2, w2 = text_paths('poppins', 'LIGU LIGU', 40, OR, 0.34)
    tw = max(w1, w2); total = th + 54 + tw; x0 = (1200 - total) / 2
    ring = '' if bg == NAVY else f'<rect x="{x0}" y="82" width="{th}" height="{th}" rx="{th*.225}" fill="none" stroke="{NAVY}" stroke-opacity=".14" stroke-width="3"/>'
    tile = (f'<clipPath id="tc"><rect x="{x0}" y="82" width="{th}" height="{th}" rx="{th*.225}"/></clipPath>'
            f'<g clip-path="url(#tc)"><g transform="translate({x0},82) scale({th/512})">{tile_inner(bg, inner)}</g></g>{ring}')
    tx = x0 + th + 54
    return svg(1200, 400, f'<rect width="1200" height="400" fill="{CREAM}"/>{tile}'
        f'<g transform="translate({tx},{82+th*.58-8})">{t1}</g><g transform="translate({tx},{82+th*.58+62})">{t2}</g>')
def sq(bg, inner, clip, size):
    body = tile_inner(bg, inner)
    if clip == 'circle': body = f'<clipPath id="cc"><circle cx="256" cy="256" r="256"/></clipPath><g clip-path="url(#cc)">{body}</g>'
    else: body = f'<clipPath id="cc"><rect width="512" height="512" rx="115"/></clipPath><g clip-path="url(#cc)">{body}</g>'
    return svg(512, 512, body, (size, size))
jobs = []
for D in DS.D:
    bg, inner = D['mk']()
    i = D['id']
    jobs += [(f'{i}_icon512', sq(bg, inner, 'sq', 512)), (f'{i}_ig400', sq(bg, inner, 'circle', 400)),
             (f'{i}_ig110', sq(bg, inner, 'circle', 110)), (f'{i}_ig40', sq(bg, inner, 'circle', 40)),
             (f'{i}_horizontal', horizontal(bg, inner))]
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=glob.glob("/opt/pw-browsers/chromium_headless_shell-*/*/chrome-headless-shell")[0])
    for fn, s in jobs:
        open(os.path.join(OUT, 'svg', fn + '.svg'), 'w').write(s)
        import re
        m = re.search(r'width="([\d.]+)" height="([\d.]+)"', s); w, h = int(float(m.group(1))), int(float(m.group(2)))
        pg = b.new_page(viewport={'width': w, 'height': h})
        pg.set_content(f'<body style="margin:0;background:transparent">{s}</body>')
        pg.screenshot(path=os.path.join(OUT, fn + '.png'), omit_background=True); pg.close()
    b.close()
print(len(jobs))
