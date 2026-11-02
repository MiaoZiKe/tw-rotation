import sys, math, os
sys.path.insert(0,'/home/user/tw-rotation/docs/brand/logo_1102b/src')
import glyph
OUT='/home/user/tw-rotation/docs/brand/logo_1102d'
FONTS='/home/user/tw-rotation/docs/brand/logo_1102b/fonts'

def hx(h): h=h.lstrip('#'); return [int(h[i:i+2],16) for i in (0,2,4)]
def shade(h,k):  # k<0 darker, >0 lighter
    r=hx(h); o=[]
    for v in r: o.append(int(v*(1+k)) if k<0 else int(v+(255-v)*k))
    return '#%02X%02X%02X'%tuple(max(0,min(255,x)) for x in o)

# 配色：brand=品牌色底版本，light=淺底版本
PALETTES={
 'p1':dict(name='糖果橘珊瑚',
   brand=dict(bg=('#FF7E5A','#EE4630'),f='#FFFFFF',a='#FFC93C',b='#1F2A44',g='#FF9F1C'),
   light=dict(bg=('#FFF9EC','#FFEFD3'),f='#1F2A44',a='#EE4630',b='#FFB400',g='#FFA11D')),
 'p2':dict(name='清新藍綠',
   brand=dict(bg=('#2DD4BF','#0A8CA3'),f='#FFFFFF',a='#FFE27A',b='#0B3C49',g='#FFB347'),
   light=dict(bg=('#F0FDFA','#D6F5EF'),f='#0B3C49',a='#0A8CA3',b='#FF8A3D',g='#2DD4BF')),
 'p3':dict(name='紫藍漸層',
   brand=dict(bg=('#9B7BFF','#2B6BF3'),f='#FFFFFF',a='#FFD166',b='#FF8FB1',g='#FF9F6B'),
   light=dict(bg=('#F6F2FF','#E6DEFF'),f='#2A2470',a='#7B4FE0',b='#2B6BF3',g='#2B6BF3')),
 'p4':dict(name='深色質感',
   brand=dict(bg=('#27324F','#101626'),f='#F4F6FF',a='#FF7A3D',b='#4FE3C1',g='#FF4D6D'),
   light=dict(bg=('#F4F6FB','#E3E8F2'),f='#1F2A44',a='#E8590C',b='#0A8CA3',g='#FFA93A')),
}

def pt(cx,cy,r,deg): 
    t=math.radians(deg); return cx+r*math.cos(t), cy+r*math.sin(t)
def arc(cx,cy,r,a0,a1):
    x0,y0=pt(cx,cy,r,a0); x1,y1=pt(cx,cy,r,a1); large=1 if (a1-a0)%360>180 else 0
    return f'M{x0:.1f} {y0:.1f} A{r} {r} 0 {large} 1 {x1:.1f} {y1:.1f}'
def sector(cx,cy,R,r,a0,a1,dx=0,dy=0):
    # 環形扇區，順時針 a0->a1
    cx+=dx;cy+=dy
    X0,Y0=pt(cx,cy,R,a0);X1,Y1=pt(cx,cy,R,a1);x1,y1=pt(cx,cy,r,a1);x0,y0=pt(cx,cy,r,a0)
    large=1 if (a1-a0)%360>180 else 0
    return f'M{X0:.1f} {Y0:.1f} A{R} {R} 0 {large} 1 {X1:.1f} {Y1:.1f} L{x1:.1f} {y1:.1f} A{r} {r} 0 {large} 0 {x0:.1f} {y0:.1f}Z'
def lg(i,c1,c2,x1=0,y1=0,x2=1,y2=1,o1=1,o2=1):
    return f'<linearGradient id="{i}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"><stop offset="0" stop-color="{c1}" stop-opacity="{o1}"/><stop offset="1" stop-color="{c2}" stop-opacity="{o2}"/></linearGradient>'

# ---------- 概念 ----------
def c1(C):
    f,a,b=C['f'],C['a'],C['b']
    pts=[(306,346),(350,292),(378,318),(426,246)]
    tr='M'+' L'.join(f'{x} {y}' for x,y in pts)
    area='M306 366 L'+' L'.join(f'{x} {y}' for x,y in pts)+' L426 366Z'
    defs=(lg('gf',f,shade(f,-0.12),0,0,0,1)+lg('ga',a,C['b2'],0,1,1,0)
          +f'<linearGradient id="ar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{a}" stop-opacity=".5"/><stop offset="1" stop-color="{a}" stop-opacity="0"/></linearGradient>')
    body=(f'<path d="{area}" fill="url(#ar)"/>'
          f'<path d="M146 104 V330 Q146 366 182 366 H250" stroke="url(#gf)" stroke-width="60" stroke-linecap="round" stroke-linejoin="round" fill="none"/>'
          f'<path d="{tr}" stroke="url(#ga)" stroke-width="30" stroke-linecap="round" stroke-linejoin="round" fill="none"/>'
          f'<path d="M398 232 L448 222 L430 274Z" fill="{a}" stroke="{a}" stroke-width="12" stroke-linejoin="round"/>')
    return defs,body

def c2(C):
    f,a,b=C['f'],C['a'],C['b']
    defs=lg('g1',f,shade(f,-0.14),0,0,1,1)+lg('g2',a,C['b2'],0,0,1,1)
    p1='M150 118 V252 Q150 332 230 332 H282'
    p2='M362 394 V260 Q362 180 282 180 H230'
    body=(f'<path d="{p1}" stroke="url(#g1)" stroke-width="58" stroke-linecap="round" stroke-linejoin="round" fill="none"/>'
          f'<path d="{p2}" stroke="url(#g2)" stroke-width="58" stroke-linecap="round" stroke-linejoin="round" fill="none"/>'
          f'<circle cx="256" cy="256" r="17" fill="{b if C["mode"]=="light" else f}" fill-opacity=".95"/>')
    return defs,body

def c3(C):
    f,a,b=C['f'],C['a'],C['b']
    cx=cy=256;R=150;r=58;off=20
    defs=lg('g1',f,shade(f,-0.16),0,0,1,1)+lg('g2',a,C['b2'],0,1,1,0)
    big=sector(cx,cy,R,r,0,270)
    q=sector(cx,cy,R,r,270,360,off,-off)
    body=(f'<path d="{big}" fill="url(#g1)"/><path d="{q}" fill="url(#g2)"/>'
          f'<circle cx="{cx}" cy="{cy}" r="24" fill="{a if C["mode"]=="light" else a}"/>'
          f'<circle cx="{cx-6}" cy="{cy-7}" r="8" fill="#fff" fill-opacity=".55"/>')
    return defs,body

def c4(C):
    f,a,b=C['f'],C['a'],C['b']
    Ox,Oy=290,248
    defs=lg('g2',a,C['b2'],0,0,1,1)
    body=''
    for r,top,ext,col,op in ((132,104,118,f,1),(84,156,86,'url(#g2)',1),(36,208,54,b,1 if C['mode']=='light' else .95)):
        body+=f'<path d="M{Ox-r} {top} V{Oy} A{r} {r} 0 0 0 {Ox} {Oy+r} H{Ox+ext}" stroke="{col}" stroke-opacity="{op}" stroke-width="34" stroke-linecap="round" fill="none"/>'
    return defs,body

_g=None
def c5(C):
    global _g
    f,a,b=C['f'],C['a'],C['b']
    font=glyph.load(900); cs=glyph.contours(font,'里')
    xs=[bd for c,bd in cs]; x0=min(b_[0] for b_ in xs);y0=min(b_[1] for b_ in xs);x1=max(b_[2] for b_ in xs);y1=max(b_[3] for b_ in xs)
    s=250/(y1-y0); gw=(x1-x0)*s
    gx=512-120-gw; gy=256+135
    d=' '.join(glyph.path(c,gx-x0*s,gy+y0*s,s) for c,_b in cs)  # baseline mapping
    # 重新精確放：用 bounds 對齊頂端 y=121
    d=' '.join(glyph.path(c,gx-x0*s,121+y1*s,s) for c,_b in cs)
    ccx,ccy,R,r=0,121+104,104,42
    ccx=gx-120
    defs=lg('g1',f,shade(f,-0.14),0,0,0,1)+lg('g2',a,C['b2'],0,1,1,0)
    big=sector(ccx,ccy,R,r,0,270); q=sector(ccx,ccy,R,r,270,360,14,-14)
    body=f'<path d="{d}" fill="url(#g1)"/><path d="{big}" fill="url(#g1)"/><path d="{q}" fill="url(#g2)"/>'
    return defs,body,(ccx-R,gx+gw)

def c6(C):
    f,a,b=C['f'],C['a'],C['b']
    defs=(lg('s1',f,shade(f,-0.12),0,0,1,0)+lg('s2',a,C['b2'],0,0,1,1)
          +f'<radialGradient id="orb" cx=".35" cy=".3" r=".8"><stop offset="0" stop-color="{shade(b,.55)}"/><stop offset=".5" stop-color="{b}"/><stop offset="1" stop-color="{shade(b,-.3)}"/></radialGradient>')
    body=(f'<polygon points="160,104 232,104 232,322 160,394" fill="url(#s1)"/>'
          f'<polygon points="160,394 232,322 392,252 392,324 322,394" fill="url(#s2)"/>'
          f'<polygon points="232,322 392,252 392,262 232,334" fill="#fff" fill-opacity=".25"/>'
          f'<g transform="translate(330 148) rotate(-24)"><ellipse rx="72" ry="25" fill="none" stroke="{f}" stroke-opacity=".5" stroke-width="7"/></g>'
          f'<circle cx="330" cy="148" r="38" fill="url(#orb)"/>'
          f'<g transform="translate(330 148) rotate(-24)"><path d="M-72 0 A72 25 0 0 0 72 0" fill="none" stroke="{f}" stroke-width="7"/></g>')
    return defs,body

CONCEPTS={
 'c1':('流動 L',c1,'L 的腳留出呼吸空隙後「流」成向右上的資金趨勢線，下方帶漸層面積；一個符號同時是 L 與上升的走勢。'),
 'c2':('輪動環 L',c2,'兩個 L 旋轉 180° 互相咬合＝LIGU LIGU 的重複與輪動；中間一點是 Li 的 i 點，也是資金落點，整體像一股迴旋的水流。'),
 'c3':('缺口圓餅 L',c3,'甜甜圈圓餅被切出一道 L 形縫隙，被抽離的右上扇區是「現在的熱點」，縫隙的轉角直指中心的資金池。'),
 'c4':('三層資金流 L',c4,'三道同心圓角 L 由外而內逐層縮短（主色／暖色漸層／輔色），像資金一層層往內輪動、也像成長的年輪。'),
 'c5':('哩字口＝圓餅',c5,'「哩」＝口＋里，把口字旁換成缺口圓餅（資金池），右邊保留 Noto Sans TC Black 原字的「里」，不變形、只換一個部件。'),
 'c6':('摺紙 Li 軌道球',c6,'延續 Li 上揚：L 做成摺紙折面（兩個明暗面），腳楔形上揚；i 點變成帶軌道環的立體球＝輪動中的資金熱點。'),
}

def make(cid,pid,mode,shape='sq'):
    P=PALETTES[pid][mode]
    C=dict(P); C['mode']=mode
    C['b2']=P['g']
    if cid=='c5':
        defs,body,ext=CONCEPTS[cid][1](C)
        # 整體置中：內容寬 ext，縮放到 ~300
        w=ext[1]-ext[0]; sc=340/w; tx=256-(ext[0]+ext[1])/2*sc; ty=256-256*sc
        content=f'<g transform="translate({tx:.1f} {ty:.1f}) scale({sc:.3f})">{body}</g>'
    else:
        defs,body=CONCEPTS[cid][1](C); content=body
    rx=112 if shape=='sq' else 0
    b1,b2=P['bg']
    glow='<radialGradient id="hl" cx=".22" cy=".12" r=".9"><stop offset="0" stop-color="#fff" stop-opacity="%s"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>'%('.22' if mode=='brand' else '.55')
    svg=(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512"><defs>{lg("bg",b1,b2,.2,0,.8,1)}{glow}{defs}</defs>'
         f'<rect width="512" height="512" rx="{rx}" fill="url(#bg)"/><rect width="512" height="512" rx="{rx}" fill="url(#hl)"/>{content}</svg>')
    return svg

if __name__=='__main__':
    os.makedirs(OUT+'/svg',exist_ok=True)
    for cid in CONCEPTS:
        for pid in PALETTES:
            for mode in ('brand','light'):
                open(f'{OUT}/svg/{cid}_{pid}_{mode}.svg','w').write(make(cid,pid,mode))
    print('ok')
