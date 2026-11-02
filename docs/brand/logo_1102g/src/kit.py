import sys, os, glob, re, math
sys.path.insert(0, os.path.dirname(__file__))
from glyph import glyph, text, arc_text
INK='#1F2A44'; CREAM='#FFF7E8'; ORG='#E8590C'; BLU='#2B6BF3'; PUR='#7B4FE0'; TEA='#0A8CA3'; YEL='#FFC93C'; PNK='#FF8FB1'
OUT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
def P(d, fill, extra=''): return f'<path d="{d}" fill="{fill}" {extra}/>'
def rect(x,y,w,h,f,r=0,extra=''): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{f}" {extra}/>'
def circ(x,y,r,f,extra=''): return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{f}" {extra}/>'
def cg(k,ch,S,cx,cy,rot=0):
    """字元以邊界框中心置於 (cx,cy)，回傳 path d"""
    _,a,b=glyph(k,ch,S); x=cx-(b[0]+b[2])/2; y=cy-(b[1]+b[3])/2
    return glyph(k,ch,S,x,y,rot)[0]
def cgs(k,s,S,cx,cy,ls=0):
    """一串字整體置中（以基線偏移粗估用字高中心），回傳 d"""
    its=text(k,s,S,0,0,items=True,ls=ls); x0=its[0][1]+(its[0][3][0] if its[0][3] else 0)
    x1=its[-1][1]+(its[-1][3][2] if its[-1][3] else its[-1][2])
    ys=[b[1] for _,_,_,b in its if b]; ye=[b[3] for _,_,_,b in its if b]
    ox=cx-(x0+x1)/2; oy=cy-(min(ys)+max(ye))/2
    d,_=text(k,s,S,ox,oy,ls=ls); return d
def tw(k,s,S,ls=0):
    """文字實際墨跡寬、上下界"""
    its=text(k,s,S,0,0,items=True,ls=ls)
    x0=its[0][1]+its[0][3][0]; x1=its[-1][1]+its[-1][3][2]
    return x1-x0, x0
def svg(w,h,inner,clip=None,size=None):
    sz=size or (w,h)
    if clip=='circle': inner=f'<clipPath id="cc"><circle cx="{w/2}" cy="{h/2}" r="{w/2}"/></clipPath><g clip-path="url(#cc)">{inner}</g>'
    if clip=='squircle': inner=f'<clipPath id="cc"><rect width="{w}" height="{h}" rx="{w*0.225}"/></clipPath><g clip-path="url(#cc)">{inner}</g>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{sz[0]}" height="{sz[1]}" viewBox="0 0 {w} {h}">{inner}</svg>'
_B=None
def shot_svgs(items, outdir):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b=pw.chromium.launch(executable_path=glob.glob("/opt/pw-browsers/chromium_headless_shell-1243/*/chrome-headless-shell")[0])
        for fn,s in items:
            m=re.search(r'width="([\d.]+)" height="([\d.]+)"',s); w,h=int(float(m.group(1))),int(float(m.group(2)))
            pg=b.new_page(viewport={'width':w,'height':h}); pg.set_content(f'<body style="margin:0;background:transparent">{s}</body>')
            pg.screenshot(path=os.path.join(outdir,fn+'.png'),omit_background=True); pg.close()
        b.close()

def default_hz(p, art_fn, tfont='sans', sub=True, tcolor=None, subcolor=None, mark_scale=0.68, tsize=150, ls=8, tdy=0, hbg=None, tail=''):
    """橫式 1200x400：左符號、右「哩股哩股」＋LIGU LIGU"""
    bg=hbg or p['bg']; tc=tcolor or p['txt']; sc=subcolor or tc
    ms=400*mark_scale; mx=70; my=(400-ms)/2
    o=[rect(0,0,1200,400,bg)]
    o.append(f'<g transform="translate({mx},{my}) scale({ms/512})">{art_fn(p,False)}</g>')
    x0=mx+ms+56
    d,w=text(tfont,'哩股哩股',tsize,x0,226+tdy,ls=ls)
    o.append(P(d,tc))
    if sub:
        d2,w2=text('inter','LIGU LIGU',58,x0+4,318+tdy,ls=22)
        o.append(P(d2,sc))
    o.append(tail)
    return 1200,400,''.join(o)
def make(did, mod, outdir=None):
    p=mod.PAL; a=mod.art
    hz=getattr(mod,'hz',None)
    items=[]
    items.append((f'{did}_icon512',svg(512,512,a(p),'squircle')))
    items.append((f'{did}_ig400',svg(512,512,a(p),'circle',(400,400))))
    items.append((f'{did}_ig110',svg(512,512,a(p),'circle',(110,110))))
    items.append((f'{did}_ig40',svg(512,512,a(p),'circle',(40,40))))
    w,h,inner=hz(p) if hz else default_hz(p,a)
    items.append((f'{did}_horizontal',svg(w,h,inner)))
    return items
