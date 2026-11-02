import sys, os, re, glob
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
def main(only=None):
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=glob.glob("/opt/pw-browsers/chromium_headless_shell-*/*/chrome-headless-shell")[0])
        mp = b.new_page()
        def measure(inner):
            mp.set_content(f'<svg xmlns="http://www.w3.org/2000/svg" width="2000" height="1000" viewBox="-500 -500 2000 1000"><g id="g">{inner}</g></svg>')
            r = mp.evaluate('(()=>{const b=document.getElementById("g").getBBox();return [b.x,b.y,b.x+b.width,b.y+b.height]})()')
            return (r[0] - 9, r[1] - 9, r[2] + 9, r[3] + 9)
        jobs = []
        for D in designs.DESIGNS:
            if only and D['id'] not in only: continue
            for mode in ('light', 'dark'):
                P = PAL['A'][mode]
                word, ico = D['mk'](P, mode)
                body = R(0, 0, 1200, 400, P['bg']) + fit(word, measure(word), 1200, 400, 880, 220)
                jobs.append((f"{D['id']}_{mode}", svg(1200, 400, body)))
                bg = P[D['icon_bg']] if D['icon_bg'] else P['bg']
                if D['icon_bg']:
                    P2 = dict(P); P2['bg'] = P['bg']; word, ico = D['mk'](P2, mode)
                body = R(0, 0, 512, 512, bg) + fit(ico, measure(ico), 512, 512, *D['box'])
                jobs.append((f"{D['id']}_icon512_{mode}", svg(512, 512, body, 'squircle')))
                jobs.append((f"{D['id']}_ig400_{mode}", svg(512, 512, body, 'circle', (400, 400))))
                jobs.append((f"{D['id']}_ig110_{mode}", svg(512, 512, body, 'circle', (110, 110))))
                jobs.append((f"{D['id']}_ig40_{mode}", svg(512, 512, body, 'circle', (40, 40))))
        for fn, s in jobs:
            open(os.path.join(SV, fn + '.svg'), 'w').write(s)
            m = re.search(r'width="([\d.]+)" height="([\d.]+)"', s); w, h = int(float(m.group(1))), int(float(m.group(2)))
            pg = b.new_page(viewport={'width': w, 'height': h})
            pg.set_content(f'<body style="margin:0;background:transparent">{s}</body>')
            pg.screenshot(path=os.path.join(OUT, fn + '.png'), omit_background=True); pg.close()
        b.close(); print(len(jobs))
if __name__ == '__main__': main(sys.argv[1:] or None)
