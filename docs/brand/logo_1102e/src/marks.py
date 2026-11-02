import math, random
from glyph import glyph, text, arc_text
INK='#1F2A44'; CREAM='#FFF7E8'; ORG='#E8590C'; BLU='#2B6BF3'; PUR='#7B4FE0'; TEA='#0A8CA3'; YEL='#FFC93C'; PNK='#FF8FB1'
def P(d, fill, extra=''): return f'<path d="{d}" fill="{fill}" {extra}/>'
def rect(x,y,w,h,f,r=0,extra=''): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{f}" {extra}/>'
def circ(x,y,r,f,extra=''): return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{f}" {extra}/>'
def uid(): 
    uid.n+=1; return f'g{uid.n}'
uid.n=0
def centered(k, s, size, cx, cy_base, f, ls=0, extra=''):
    d,w=text(k,s,size,cx,cy_base,anchor='middle',ls=ls); return P(d,f,extra)

# ---------------- D1 純字標 ----------------
PAL1={'A':dict(bg=CREAM,fg=INK,dot=ORG,dot2=BLU,acc=ORG),'B':dict(bg=BLU,fg=CREAM,dot=YEL,dot2=PNK,acc=YEL)}
def _ligu(x,base,S,fg,dotc,anchor='start'):
    """ligu：ı 用大圓點取代點，回傳 (svg, 寬)"""
    its=text('fr','lıgu',S,x,base,anchor=anchor,items=True)
    out=[]; 
    for ch,cx,a,bd in its:
        d,_,_=glyph('fr',ch,S,cx,base); out.append(P(d,fg))
        if ch=='ı':
            mid=cx+(bd[0]+bd[2])/2; r=S*0.115
            out.append(circ(mid,base-S*0.495-S*0.075-r,r,dotc))
    W=its[-1][1]+its[-1][2]-its[0][1]
    return ''.join(out),W
def art1(p):
    S=380; its=text('fr','lı',S,0,0,items=True); W=its[-1][1]+its[-1][2]
    x=256-W/2-8; base=256+0.755*S/2+10
    o=[rect(0,0,512,512,p['bg'])]
    for ch,cx,a,bd in text('fr','lı',S,x,base,items=True):
        d,_,_=glyph('fr',ch,S,cx,base); o.append(P(d,p['fg']))
        if ch=='ı':
            mid=cx+(bd[0]+bd[2])/2; r=S*0.125
            o.append(circ(mid,base-S*0.495-S*0.07-r,r,p['dot']))
    return ''.join(o)
def horiz1(p):
    S=215; base=215
    a,w1=_ligu(0,0,S,p['fg'],p['dot'])
    b,w2=_ligu(0,0,S,p['acc'],p['fg'])
    gap=S*0.22; tot=w1+gap+w2; x0=(1200-tot)/2
    d,cw=text('sans7','哩股哩股',52,600,338,anchor='middle',ls=70)
    o=[rect(0,0,1200,400,p['bg']),f'<g transform="translate({x0},{base+20})">{a}</g>',f'<g transform="translate({x0+w1+gap},{base+20})">{b}</g>',P(d,p['fg'],'opacity=".85"')]
    return 1200,400,''.join(o)

# ---------------- D2 圓體可愛 ----------------
PAL2={'A':dict(bg=CREAM,ink=INK,b1=ORG,b2=BLU,t=CREAM,sp=YEL),'B':dict(bg=BLU,ink=INK,b1=YEL,b2=PNK,t=INK,sp=CREAM)}
def sticker(k,ch,size,cx,base,fill,ink,rot=0,sh=(7,9),sw=14):
    d,a,bd=glyph(k,ch,size,0,0,rot=rot)
    x=cx-a/2
    d,a,bd=glyph(k,ch,size,x,base,rot=rot)
    return (f'<path d="{d}" transform="translate({sh[0]},{sh[1]})" fill="{ink}" stroke="{ink}" stroke-width="{sw}" stroke-linejoin="round"/>'
            f'<path d="{d}" fill="{fill}" stroke="{ink}" stroke-width="{sw}" stroke-linejoin="round" paint-order="stroke"/>')
def blob(cx,cy,r,f,ink,rot=0,sh=(10,12)):
    return (f'<circle cx="{cx+sh[0]}" cy="{cy+sh[1]}" r="{r}" fill="{ink}"/><circle cx="{cx}" cy="{cy}" r="{r}" fill="{f}" stroke="{ink}" stroke-width="10"/>')
def art2(p):
    o=[rect(0,0,512,512,p['bg'])]
    o.append(blob(222,236,172,p['b1'],p['ink']))
    # 高光
    o.append(f'<path d="M110 190 A120 120 0 0 1 200 112" stroke="#fff" stroke-opacity=".55" stroke-width="16" stroke-linecap="round" fill="none"/>')
    o.append(sticker('huninn','哩',250,222,330,p['t'],p['ink'],rot=-7,sw=0.1) if False else '')
    # 字：白底貼紙字
    d,a,bd=glyph('huninn','哩',250,0,0,rot=-6); x=222-a/2
    d,a,bd=glyph('huninn','哩',250,x,322,rot=-6)
    o.append(f'<path d="{d}" transform="translate(6,8)" fill="{p["ink"]}"/><path d="{d}" fill="{p["t"]}"/>')
    o.append(blob(392,392,82,p['b2'],p['ink'],sh=(8,10)))
    d,a,bd=glyph('huninn','股',104,0,0,rot=7); x=392-a/2
    d,a,bd=glyph('huninn','股',104,x-2,428,rot=7)
    o.append(f'<path d="{d}" transform="translate(4,5)" fill="{p["ink"]}"/><path d="{d}" fill="#fff"/>')
    # 星星
    o.append(circ(420,118,26,p['sp'],f'stroke="{p["ink"]}" stroke-width="8"'))
    o.append(f'<path d="M96 408 v52 M70 434 h52" stroke="{p["ink"]}" stroke-width="12" stroke-linecap="round"/>')
    return ''.join(o)
def horiz2(p):
    cols=[ORG,BLU,PUR,TEA] if p['bg']==CREAM else [YEL,PNK,CREAM,'#8EE3FF']
    tcol=['#fff']*4 if p['bg']==CREAM else [INK]*4
    ys=[-26,22,-18,26]; rots=[-6,5,-4,6]; o=[rect(0,0,1200,400,p['bg'])]
    for i,ch in enumerate('哩股哩股'):
        cx=190+i*273; cy=200+ys[i]
        o.append(f'<g transform="rotate({rots[i]} {cx} {cy})">'
                 f'<rect x="{cx-110+9}" y="{cy-110+11}" width="220" height="220" rx="78" fill="{INK}"/>'
                 f'<rect x="{cx-110}" y="{cy-110}" width="220" height="220" rx="78" fill="{cols[i]}" stroke="{INK}" stroke-width="9"/>'
                 f'<path d="M{cx-86} {cy-52} A62 62 0 0 1 {cx-40} {cy-90}" stroke="#fff" stroke-opacity=".6" stroke-width="13" stroke-linecap="round" fill="none"/>')
        d,a,bd=glyph('huninn',ch,150,0,0); x=cx-a/2
        d,a,bd=glyph('huninn',ch,150,x,cy+50)
        o.append(f'<path d="{d}" transform="translate(4,5)" fill="{INK}" opacity=".35"/><path d="{d}" fill="{tcol[i]}"/></g>')
    return 1200,400,''.join(o)

# ---------------- D3 單線 ----------------
PAL3={'A':dict(bg=CREAM,l=INK,acc=ORG),'B':dict(bg=BLU,l=CREAM,acc=YEL)}
def line_art(p,sw=18):
    st=lambda c,w: f'fill="none" stroke="{c}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"'
    o=[f'<circle cx="140" cy="120" r="26" {st(p["acc"],sw)}/>',
       f'<path d="M140 174 V352 Q140 396 188 396 H246 C318 396 322 312 376 308 C418 304 428 236 452 192" {st(p["l"],sw)}/>',
       f'<path d="M414 184 H454 V224" {st(p["l"],sw)}/>',
       f'<path d="M196 448 H252 C324 448 330 372 384 372 C430 372 440 330 470 296" {st(p["acc"],sw*0.5)} opacity=".9"/>']
    return ''.join(o)
def art3(p): return rect(0,0,512,512,p['bg'])+f'<g transform="translate(-6,-4)">{line_art(p,20)}</g>'
def horiz3(p):
    o=[rect(0,0,1200,400,p['bg']),f'<g transform="translate(70,10) scale(.72)">{line_art(p,18)}</g>']
    d,w=text('sans7','哩股哩股',112,500,235,ls=22); o.append(P(d,p['l']))
    d,w2=text('fr7','LIGU  LIGU',40,502,300,ls=16); o.append(P(d,p['acc']))
    o.append(f'<path d="M504 262 H{504+w}" stroke="{p["l"]}" stroke-width="3" opacity=".35"/>')
    return 1200,400,''.join(o)

# ---------------- D4 徽章 ----------------
PAL4={'A':dict(bg=INK,band=INK,ring=CREAM,tx=CREAM,disc=CREAM,sun=ORG,bar=INK,star=YEL),
      'B':dict(bg=ORG,band=ORG,ring=CREAM,tx=CREAM,disc=INK,sun=YEL,bar=CREAM,star=CREAM)}
def art4(p):
    o=[rect(0,0,512,512,p['bg'])]
    c=256
    o.append(circ(c,c,238,'none',f'stroke="{p["ring"]}" stroke-width="6"'))
    o.append(circ(c,c,228,'none',f'stroke="{p["ring"]}" stroke-width="2"'))
    o.append(circ(c,c,160,p['disc']))
    o.append(circ(c,c,170,'none',f'stroke="{p["ring"]}" stroke-width="3"'))
    # 弧形字
    o.append(P(arc_text('fr','LIGU LIGU',54,c,c,184,0,ls=10),p['tx']))
    o.append(P(arc_text('serif','哩股哩股',42,c,c,213,0,bottom=True,ls=20),p['tx']))
    # 左右星
    for sx in (c-203,c+203):
        o.append(star(sx,c+3,16,p['star']))
    # 中央：旭日＋三柱
    cl=uid(); o.append(f'<clipPath id="{cl}"><circle cx="{c}" cy="{c}" r="152"/></clipPath><g clip-path="url(#{cl})">')
    sy=300
    for i in range(13):
        a=math.radians(-180+ i*15); 
        o.append(f'<path d="M{c+40*math.cos(a):.1f} {sy+40*math.sin(a):.1f} L{c+150*math.cos(a):.1f} {sy+150*math.sin(a):.1f}" stroke="{p["sun"]}" stroke-width="7" stroke-linecap="round" opacity=".9"/>' if 0<i<12 else '')
    o.append(f'<path d="M{c-62} {sy} A62 62 0 0 1 {c+62} {sy}Z" fill="{p["sun"]}"/>')
    o.append(rect(c-150,sy,300,160,p['disc']))
    for i,h in enumerate((44,74,108)):
        o.append(rect(c-88+i*64,sy+8+(108-h)*0+0-h+78,50,h+ (160),p['bar'],6))
    o.append('</g>')
    return ''.join(o)
def star(x,y,r,f):
    pts=[]
    for i in range(10):
        a=math.radians(-90+i*36); rr=r if i%2==0 else r*0.42
        pts.append(f'{x+rr*math.cos(a):.1f},{y+rr*math.sin(a):.1f}')
    return f'<polygon points="{" ".join(pts)}" fill="{f}"/>'
def horiz4(p):
    # 橫式：徽章 + 字標
    o=[rect(0,0,1200,400,CREAM if p['bg']==INK else INK)]
    fg=INK if p['bg']==INK else CREAM
    o.append(f'<g transform="translate(60,30) scale(.7)"><clipPath id="hc4{p["bg"][1:]}"><circle cx="256" cy="256" r="256"/></clipPath><g clip-path="url(#hc4{p["bg"][1:]})">{art4(p)}</g></g>')
    d,w=text('serif','哩股哩股',150,470,225,ls=12); o.append(P(d,fg))
    d,w2=text('fr','LIGU LIGU',58,474,312,ls=30); o.append(P(d,ORG if p['bg']==INK else YEL))
    return 1200,400,''.join(o)

# ---------------- D5 黏土立體 ----------------
PAL5={'A':dict(bg=('#FFF3DF','#FFD8B5'),seg=[('#5B97FF',BLU,'#1D47B8'),('#FF9E57',ORG,'#B33C00'),('#B79BFF',PUR,'#4B2AA8')],core=('#FFE27A',YEL,'#E39A00')),
      'B':dict(bg=('#EAF6FF','#C9DFFF'),seg=[('#4FE0CF','#13B5A6','#0B7A72'),('#FFB0C8',PNK,'#D9527C'),('#FFE27A',YEL,'#E39A00')],core=('#6EA2FF',BLU,'#1D47B8'))}
def arcd(cx,cy,r,a0,a1):
    p0=(cx+r*math.sin(math.radians(a0)),cy-r*math.cos(math.radians(a0))); p1=(cx+r*math.sin(math.radians(a1)),cy-r*math.cos(math.radians(a1)))
    return f'M{p0[0]:.1f} {p0[1]:.1f} A{r} {r} 0 {1 if a1-a0>180 else 0} 1 {p1[0]:.1f} {p1[1]:.1f}'
def art5(p):
    i=uid(); defs=[f'<linearGradient id="{i}bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{p["bg"][0]}"/><stop offset="1" stop-color="{p["bg"][1]}"/></linearGradient>',
                   f'<filter id="{i}b8" filterUnits="userSpaceOnUse" x="-100" y="-100" width="712" height="712"><feGaussianBlur stdDeviation="9"/></filter>',
                   f'<filter id="{i}b3" filterUnits="userSpaceOnUse" x="-100" y="-100" width="712" height="712"><feGaussianBlur stdDeviation="3.5"/></filter>']
    o=[rect(0,0,512,512,f'url(#{i}bg)')]
    c=256; R=150; W=82
    for k,(lt,mid,dk) in enumerate(p['seg']):
        a0=-62+k*120; a1=a0+82
        defs.append(f'<linearGradient id="{i}s{k}" x1="0" y1="0" x2="0.3" y2="1"><stop offset="0" stop-color="{lt}"/><stop offset=".55" stop-color="{mid}"/><stop offset="1" stop-color="{dk}"/></linearGradient>')
        mid_a=math.radians((a0+a1)/2); pop=(14*math.sin(mid_a),-14*math.cos(mid_a)) if k==0 else (0,0)
        sh=26 if k==0 else 16
        d=arcd(c,c,R,a0,a1)
        o.append(f'<g transform="translate({pop[0]:.1f},{pop[1]:.1f})">'
                 f'<path d="{d}" transform="translate(0,{sh})" fill="none" stroke="#3a2a55" stroke-opacity=".28" stroke-width="{W}" stroke-linecap="round" filter="url(#{i}b8)"/>'
                 f'<path d="{d}" fill="none" stroke="url(#{i}s{k})" stroke-width="{W}" stroke-linecap="round"/>'
                 f'<path d="{arcd(c,c,R+6,a0+8,a1-14)}" transform="translate(-5,-7)" fill="none" stroke="#fff" stroke-opacity=".6" stroke-width="16" stroke-linecap="round" filter="url(#{i}b3)"/>'
                 f'<path d="{arcd(c,c,R-26,a0+4,a1-4)}" fill="none" stroke="{dk}" stroke-opacity=".28" stroke-width="12" stroke-linecap="round" filter="url(#{i}b3)"/></g>')
    lt,mid,dk=p['core']
    defs.append(f'<radialGradient id="{i}core" cx=".36" cy=".3" r=".8"><stop offset="0" stop-color="{lt}"/><stop offset=".6" stop-color="{mid}"/><stop offset="1" stop-color="{dk}"/></radialGradient>')
    o.append(f'<ellipse cx="{c+2}" cy="{c+44}" rx="40" ry="12" fill="#3a2a55" opacity=".25" filter="url(#{i}b8)"/>')
    o.append(circ(c,c,46,f'url(#{i}core)'))
    o.append(f'<ellipse cx="{c-15}" cy="{c-20}" rx="17" ry="10" fill="#fff" opacity=".75" transform="rotate(-32 {c-15} {c-20})" filter="url(#{i}b3)"/>')
    return f'<defs>{"".join(defs)}</defs>'+''.join(o)
def horiz5(p):
    bgc=p['bg'][0]
    ic=art5(p)
    o=[rect(0,0,1200,400,bgc),f'<g transform="translate(70,40) scale(.62)"><clipPath id="sq5"><rect width="512" height="512" rx="115"/></clipPath><g clip-path="url(#sq5)">{ic}</g></g>']
    i=uid()
    d,w=text('sans','哩股哩股',150,470,230,ls=10)
    o.append(f'<filter id="{i}f"><feGaussianBlur stdDeviation="4"/></filter><path d="{d}" transform="translate(0,12)" fill="#3a2a55" opacity=".25" filter="url(#{i}f)"/>'+P(d,INK))
    d,w=text('sans7','LIGU LIGU · ETF · 資金輪動',34,474,300,ls=6); o.append(P(d,p['seg'][1][2]))
    return 1200,400,''.join(o)

# ---------------- D6 霓虹 ----------------
PAL6={'A':dict(bg=('#0B1030','#1B1450'),c1='#35F2FF',c2='#C45BFF',grid='#5B6BFF'),
      'B':dict(bg=('#0A0F1F','#161B38'),c1='#FF4D5E',c2='#FFC93C',grid='#7A86C8')}
def neon_line(p,i,x0=0,y0=0):
    pts=[(130,110),(130,382),(246,382)]
    d='M130 108 V380 H214 L284 300 L322 322 L426 186'
    return d
def art6(p):
    i=uid()
    defs=[f'<radialGradient id="{i}bg" cx=".5" cy=".4" r=".85"><stop offset="0" stop-color="{p["bg"][1]}"/><stop offset="1" stop-color="{p["bg"][0]}"/></radialGradient>',
          f'<filter id="{i}g" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="9" result="a"/><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="a"/><feMergeNode in="a"/><feMergeNode in="b"/></feMerge></filter>']
    o=[rect(0,0,512,512,f'url(#{i}bg)')]
    for k in range(1,8):
        o.append(f'<path d="M{k*64} 0V512M0 {k*64}H512" stroke="{p["grid"]}" stroke-opacity=".13" stroke-width="2"/>')
    d=neon_line(p,i)
    sty='fill="none" stroke-linecap="round" stroke-linejoin="round"'
    o.append(f'<path d="{d}" {sty} stroke="{p["c1"]}" stroke-width="30" filter="url(#{i}g)"/>')
    o.append(f'<path d="{d}" {sty} stroke="{p["c1"]}" stroke-width="20"/>')
    o.append(f'<path d="{d}" {sty} stroke="#fff" stroke-opacity=".85" stroke-width="6"/>')
    # 外圈環
    ring=f'M256 38 A218 218 0 1 1 100 100'
    o.append(f'<path d="{ring}" {sty} stroke="{p["c2"]}" stroke-width="16" filter="url(#{i}g)"/>')
    o.append(f'<path d="{ring}" {sty} stroke="{p["c2"]}" stroke-width="9"/><path d="{ring}" {sty} stroke="#fff" stroke-opacity=".8" stroke-width="3"/>')
    # 末端亮點
    o.append(f'<circle cx="426" cy="186" r="22" fill="{p["c2"]}" filter="url(#{i}g)"/><circle cx="426" cy="186" r="13" fill="#fff"/>')
    return f'<defs>{"".join(defs)}</defs>'+''.join(o)
def horiz6(p):
    i=uid()
    o=[f'<defs><linearGradient id="{i}h" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{p["bg"][1]}"/><stop offset="1" stop-color="{p["bg"][0]}"/></linearGradient>'
       f'<filter id="{i}g" x="-20%" y="-40%" width="140%" height="180%"><feGaussianBlur stdDeviation="9" result="a"/><feMerge><feMergeNode in="a"/><feMergeNode in="a"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>',
       rect(0,0,1200,400,f'url(#{i}h)')]
    o.append(f'<g transform="translate(60,36) scale(.6)"><clipPath id="{i}c"><rect width="512" height="512" rx="100"/></clipPath><g clip-path="url(#{i}c)">{art6(p)}</g></g>')
    d,w=text('inter','LIGU LIGU',128,450,215,ls=8)
    o.append(f'<path d="{d}" fill="{p["c1"]}" filter="url(#{i}g)"/>'+P(d,'#fff','opacity=".92"'))
    d,w2=text('sans7','哩股哩股',60,454,310,ls=40)
    o.append(f'<path d="{d}" fill="{p["c2"]}" filter="url(#{i}g)"/>'+P(d,p['c2']))
    return 1200,400,''.join(o)

# ---------------- D7 書法 ----------------
PAL7={'A':dict(bg=CREAM,ink=INK,sun=ORG,paper=True),'B':dict(bg=INK,ink=CREAM,sun=ORG,paper=False)}
def ensou(cx,cy,r,start,sweep,w0,seed=3):
    random.seed(seed); n=220; outer=[]; inner=[]
    for k in range(n+1):
        u=k/n; th=math.radians(start+sweep*u)
        w=w0*(1-0.78*u**1.3)*min(1,(u/0.035)**0.5)*min(1,((1-u)/0.12)**0.7)+1.5
        rc=r+7*math.sin(u*5.2)+ (1-u)*5
        ro=rc+w/2; ri=rc-w/2
        outer.append((cx+ro*math.sin(th),cy-ro*math.cos(th))); inner.append((cx+ri*math.sin(th),cy-ri*math.cos(th)))
    pts=outer+inner[::-1]
    return 'M'+' L'.join(f'{x:.1f} {y:.1f}' for x,y in pts)+'Z'
def art7(p):
    i=uid()
    o=[f'<defs><filter id="{i}r" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency=".035" numOctaves="3" seed="4"/><feDisplacementMap in="SourceGraphic" scale="7"/></filter>'
       f'<filter id="{i}t" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency=".06" numOctaves="2" seed="9"/><feDisplacementMap in="SourceGraphic" scale="3"/></filter></defs>',rect(0,0,512,512,p['bg'])]
    o.append(f'<path d="{ensou(256,262,196,80,320,50)}" fill="{p["ink"]}" filter="url(#{i}r)"/>')
    o.append(circ(430,150,34,p['sun'],f'filter="url(#{i}t)"'))
    d,a,bd=glyph('wk','哩',290,0,0,rot=-2); x=250-a/2
    d,a,bd=glyph('wk','哩',290,x,368,rot=-2)
    o.append(f'<path d="{d}" fill="{p["ink"]}" filter="url(#{i}t)"/>')
    return ''.join(o)
def horiz7(p):
    i=uid(); o=[f'<defs><filter id="{i}t" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency=".05" numOctaves="2" seed="9"/><feDisplacementMap in="SourceGraphic" scale="3"/></filter></defs>',rect(0,0,1200,400,p['bg'])]
    rots=[-3,2,-2,3]; ys=[0,-8,6,-4]
    for k,ch in enumerate('哩股哩股'):
        d,a,bd=glyph('wk',ch,222,0,0,rot=rots[k]); x=105+k*225
        d,a,bd=glyph('wk',ch,222,x,250+ys[k],rot=rots[k])
        o.append(f'<path d="{d}" fill="{p["ink"]}" filter="url(#{i}t)"/>')
    o.append(circ(1040,210,30,p['sun'],f'filter="url(#{i}t)"'))
    d,w=text('fr7','LIGU  LIGU',40,600,335,anchor='middle',ls=34); o.append(P(d,p['ink'],'opacity=".8"'))
    return 1200,400,''.join(o)

# ---------------- D8 孟菲斯 ----------------
PAL8={'A':dict(bg=YEL,L=BLU,foot=ORG,ring=PNK,tri=TEA,zig=PUR,dot=CREAM,ink=INK),'B':dict(bg=PUR,L=CREAM,foot=YEL,ring=PNK,tri='#2CE0C8',zig=YEL,dot=BLU,ink=INK)}
def zig(x,y,n,w,h,c,sw=14):
    d=f'M{x} {y}'+''.join(f' l{w} {-h if k%2==0 else h}' for k in range(n))
    return f'<path d="{d}" fill="none" stroke="{c}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>'
def dots(x,y,n,m,gap,r,c): return ''.join(circ(x+i*gap,y+j*gap,r,c) for i in range(n) for j in range(m))
def art8(p):
    o=[rect(0,0,512,512,p['bg'])]
    o.append(rect(104,92,116,300,p['L']))
    o.append(f'<path d="M220 282 H340 A55 55 0 0 1 340 392 H220Z" fill="{p["foot"]}"/>')
    o.append(circ(382,150,46,'none',f'stroke="{p["ring"]}" stroke-width="26"'))
    o.append(f'<polygon points="60,470 130,420 200,470" fill="{p["tri"]}"/>')
    o.append(zig(262,248,5,28,18,p['zig'],14)); o.append(f'<path d="M420 52 a40 40 0 0 1 56 56Z" fill="{p["tri"]}" transform="rotate(0)"/>')
    o.append(dots(330,436,4,2,30,8,p['dot']))
    o.append(circ(462,300,0,'none'))
    o.append(rect(420,226,40,40,p['ink'],0,'transform="rotate(20 440 246)"') if False else '')
    return ''.join(o)
def horiz8(p):
    o=[rect(0,0,1200,400,p['bg'] if p['bg']==YEL else '#F2ECFF'),'<g transform="translate(60,70) scale(.8)">']
    cols=[BLU,PUR,ORG,TEA]; y=0; x=0; H=220; s=50
    o.append(rect(x,y,s,H,cols[0])); o.append(rect(x+s,y+H-s,90,s,cols[0]) )
    x2=x+170; o.append(rect(x2,y+60,s,H-60,cols[1])); o.append(circ(x2+s/2,y+26,26,ORG))
    x3=x2+s+30; cx,cy,r=x3+110,y+110,85
    ex=cx+r*math.cos(math.radians(-40)); ey=cy+r*math.sin(math.radians(-40))
    o.append(f'<path d="M{ex:.1f} {ey:.1f} A{r} {r} 0 1 0 {cx+r} {cy}" fill="none" stroke="{cols[2]}" stroke-width="50"/>')
    o.append(rect(cx+8,cy-25,r+25-8+0,25,cols[2]))
    x4=x3+240; o.append(f'<path d="M{x4+25} {y} V{y+140} A55 55 0 0 0 {x4+135} {y+140} V{y}" fill="none" stroke="{cols[3]}" stroke-width="50"/>')
    o.append('</g>')
    o.append(zig(70,310,9,26,22,p['zig'],12))
    o.append(f'<polygon points="520,330 560,270 600,330" fill="{PNK if p["bg"]==YEL else YEL}"/>')
    d,w=text('sans','哩股哩股',122,640,240,ls=4); o.append(P(d,INK))
    o.append(circ(1130,118,16,ORG))
    return 1200,400,''.join(o)

DIRS=[
 ('d1','純字標','ligu 小寫字標＋大圓點取代 i 點',art1,horiz1,PAL1,'Fraunces Black'),
 ('d2','圓體可愛','四顆彈跳糖果貼紙',art2,horiz2,PAL2,'粉圓 Huninn'),
 ('d3','單線 Monoline','一筆畫：L 流成資金線',art3,horiz3,PAL3,'無（純向量）＋Noto Sans TC Bold'),
 ('d4','復古徽章','雙環弧形字＋旭日三柱',art4,horiz4,PAL4,'Fraunces Black／Noto Serif TC Black'),
 ('d5','黏土立體','三塊黏土甜甜圈切片',art5,horiz5,PAL5,'Noto Sans TC Black'),
 ('d6','霓虹科技','發光 L 趨勢線＋霓虹環',art6,horiz6,PAL6,'Inter ExtraBold／Noto Sans TC Bold'),
 ('d7','書法手寫','霞鶩文楷＋墨色圓相與旭日',art7,horiz7,PAL7,'霞鶩文楷 LXGW WenKai TC'),
 ('d8','孟菲斯拼貼','彩色幾何塊拼 L 與 LIGU',art8,horiz8,PAL8,'Noto Sans TC Black'),
]
