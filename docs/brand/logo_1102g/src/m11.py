from kit import *
KW=dict(stem=260,foot=420,top=92,bot=424,cx=316,cy=258,r=112,sx=-18,sy=-6,w=48)
def art(p, bgr=True, **kw):
    k=dict(KW,**kw); sx,sy=k['sx'],k['sy']
    T=lambda x,y:(256+x-300+sx, 256+y-256+sy)
    w=k['w']; gap=p['gap']; r=k['r']; cx,cy=k['cx'],k['cy']
    a0=math.radians(-38)
    s=T(cx+r*math.cos(a0), cy+r*math.sin(a0)); e=T(cx+r,cy); b=T(cx+4,cy)
    G=f'M{s[0]:.1f} {s[1]:.1f} A{r} {r} 0 1 0 {e[0]:.1f} {e[1]:.1f} L{b[0]:.1f} {b[1]:.1f}'
    xs,yt=T(k['stem'],k['top']+w/2); _,yb=T(k['stem'],k['bot']); xf,_=T(k['foot'],0); _,ym=T(0,cy)
    Llow=f'M{xs:.1f} {ym-30:.1f} L{xs:.1f} {yb:.1f} L{xf:.1f} {yb:.1f}'
    Lup=f'M{xs:.1f} {yt:.1f} L{xs:.1f} {ym+1.5:.1f}'
    st=lambda c,wd,cap='round': f'fill="none" stroke="{c}" stroke-width="{wd}" stroke-linejoin="round" stroke-linecap="{cap}"'
    o=[rect(0,0,512,512,p['bg'])] if bgr else []
    o.append(f'<path d="{Llow}" {st(p["L"],w)}/>')
    o.append(f'<path d="{G}" {st(p["bg"],w+2*gap)}/><path d="{G}" {st(p["G"],w)}/>')
    o.append(circ(xs,yt,w/2+gap,p['bg']))
    o.append(f'<path d="{Lup}" {st(p["bg"],w+2*gap,"butt")}/>')
    o.append(f'<path d="{Lup}" {st(p["L"],w,"butt")}/>'+circ(xs,yt,w/2,p['L']))
    return ''.join(o)
PAL=dict(bg=CREAM,L=INK,G=ORG,gap=8,txt=INK)
NAME='字母交織'
def hz(p):
    return default_hz(p,art,tfont='sans7',tcolor=INK,subcolor=ORG,mark_scale=0.82)
