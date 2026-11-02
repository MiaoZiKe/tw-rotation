import sys, os, glob
sys.path.insert(0, os.path.dirname(__file__))
from marks import *
from playwright.sync_api import sync_playwright
OUT=os.path.join(os.path.dirname(__file__),'..'); SV=os.path.join(OUT,'svg')
def svg(w,h,inner,clip=None,size=None):
    sz=size or (w,h)
    if clip=='circle': inner=f'<clipPath id="cc"><circle cx="{w/2}" cy="{h/2}" r="{w/2}"/></clipPath><g clip-path="url(#cc)">{inner}</g>'
    if clip=='squircle': inner=f'<clipPath id="cc"><rect width="{w}" height="{h}" rx="{w*0.225}"/></clipPath><g clip-path="url(#cc)">{inner}</g>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{sz[0]}" height="{sz[1]}" viewBox="0 0 {w} {h}">{inner}</svg>'
def main(only=None):
    jobs=[]
    for did,name,idea,art,hz,pal,font in DIRS:
        if only and did not in only: continue
        for pk,p in pal.items():
            a=art(p); a=a if a.startswith('<defs') or True else a
            for fn,s in [(f'{did}_{pk}_icon512',svg(512,512,a,'squircle')),(f'{did}_{pk}_ig400',svg(512,512,a,'circle',(400,400))),
                         (f'{did}_{pk}_ig110',svg(512,512,a,'circle',(110,110))),(f'{did}_{pk}_ig40',svg(512,512,a,'circle',(40,40)))]:
                jobs.append((fn,s,None))
            w,h,inner=hz(p); jobs.append((f'{did}_{pk}_horizontal',svg(w,h,inner),None))
    with sync_playwright() as pw:
        b=pw.chromium.launch(executable_path=glob.glob("/opt/pw-browsers/chromium_headless_shell-1243/*/chrome-headless-shell")[0])
        for fn,s,_ in jobs:
            open(os.path.join(SV,fn+'.svg'),'w').write(s)
            import re
            m=re.search(r'width="([\d.]+)" height="([\d.]+)"',s); w,h=int(float(m.group(1))),int(float(m.group(2)))
            pg=b.new_page(viewport={'width':w,'height':h}); pg.set_content(f'<body style="margin:0;background:transparent">{s}</body>')
            pg.screenshot(path=os.path.join(OUT,fn+'.png'),omit_background=True); pg.close()
        b.close()
if __name__=='__main__': main(sys.argv[1:] or None)
