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
            return (r[0] - 3, r[1] - 3, r[2] + 3, r[3] + 3)
        jobs = []
        for D in designs.DESIGNS:
            if only and D['id'] not in only: continue
            P = designs.PALS[D['pal']]
            word, av = D['mk'](P)
            body = R(0, 0, 1200, 400, P['bg']) + fit(word, measure(word), 1200, 400, 900, 230)
            jobs.append((f"{D['id']}_word", svg(1200, 400, body)))
            body = R(0, 0, 512, 512, P['bg']) + fit(av, measure(av), 512, 512, D['box'], D['box'])
            jobs.append((f"{D['id']}_icon512", svg(512, 512, body, 'squircle')))
            for n in (400, 110, 40): jobs.append((f"{D['id']}_ig{n}", svg(512, 512, body, 'circle', (n, n))))
        for fn, s in jobs:
            open(os.path.join(SV, fn + '.svg'), 'w').write(s)
            m = re.search(r'width="([\d.]+)" height="([\d.]+)"', s); w, h = int(float(m.group(1))), int(float(m.group(2)))
            pg = b.new_page(viewport={'width': w, 'height': h})
            pg.set_content(f'<body style="margin:0;background:transparent">{s}</body>')
            pg.screenshot(path=os.path.join(OUT, fn + '.png'), omit_background=True); pg.close()
        b.close(); print(len(jobs))
if __name__ == '__main__': main(sys.argv[1:] or None)
