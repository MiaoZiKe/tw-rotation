import sys, os, re, glob, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import *
import designs
from playwright.sync_api import sync_playwright

SV = os.path.join(OUT, 'svg')

def svg(w, h, inner, clip=None, size=None):
    sz = size or (w, h)
    if clip == 'circle': inner = f'<clipPath id="cc"><circle cx="{w/2}" cy="{h/2}" r="{w/2}"/></clipPath><g clip-path="url(#cc)">{inner}</g>'
    if clip == 'squircle': inner = f'<clipPath id="cc"><rect width="{w}" height="{h}" rx="{w*0.225}"/></clipPath><g clip-path="url(#cc)">{inner}</g>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{sz[0]}" height="{sz[1]}" viewBox="0 0 {w} {h}">{inner}</svg>'

def jobs_for(only=None):
    jobs = []
    for D in designs.DESIGNS:
        if only and D['id'] not in only: continue
        for pk in 'AB':
            # 橫式：淺底、深底
            for mode in ('light', 'dark'):
                P = PAL[pk][mode]
                word, _ = D['mk'](P, pk, mode)
                inner, bounds = word
                body = R(0, 0, 1200, 400, P['bg']) + fit(inner, bounds, 1200, 400, 880, 220)
                jobs.append((f"{D['id']}_{pk}_{mode}", svg(1200, 400, body)))
            # 圖示
            im = D['icon_modes'][0 if pk == 'A' else 1]
            P = PAL[pk][im]
            _, ico = D['mk'](P, pk, im)
            inner, bounds = ico
            body = R(0, 0, 512, 512, P['bg']) + fit(inner, bounds, 512, 512, *D['box'])
            jobs.append((f"{D['id']}_{pk}_icon512", svg(512, 512, body, 'squircle')))
            jobs.append((f"{D['id']}_{pk}_ig400", svg(512, 512, body, 'circle', (400, 400))))
            jobs.append((f"{D['id']}_{pk}_ig110", svg(512, 512, body, 'circle', (110, 110))))
            jobs.append((f"{D['id']}_{pk}_ig40", svg(512, 512, body, 'circle', (40, 40))))
    return jobs

def main(only=None):
    jobs = jobs_for(only)
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=glob.glob("/opt/pw-browsers/chromium_headless_shell-*/*/chrome-headless-shell")[0])
        for fn, s in jobs:
            open(os.path.join(SV, fn + '.svg'), 'w').write(s)
            m = re.search(r'width="([\d.]+)" height="([\d.]+)"', s); w, h = int(float(m.group(1))), int(float(m.group(2)))
            pg = b.new_page(viewport={'width': w, 'height': h})
            pg.set_content(f'<body style="margin:0;background:transparent">{s}</body>')
            pg.screenshot(path=os.path.join(OUT, fn + '.png'), omit_background=True); pg.close()
        b.close()
    print(len(jobs), 'files')

if __name__ == '__main__':
    main(sys.argv[1:] or None)
