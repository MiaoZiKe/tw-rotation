from kit import *
SW=13; OFF=16
def box(x,y,w,h,fill,ink,r=12,off=OFF,sw=SW):
    return (rect(x+off,y+off,w,h,ink,r)+rect(x+sw/2,y+sw/2,w-sw,h-sw,fill,r-3,f'stroke="{ink}" stroke-width="{sw}"'))
def burst(cx,cy,R,r,n,fill,ink,rot=0,off=10):
    pts=[]
    for i in range(n*2):
        a=math.radians(rot+i*180/n); rr=R if i%2==0 else r
        pts.append(f'{cx+rr*math.cos(a):.1f},{cy+rr*math.sin(a):.1f}')
    s=' '.join(pts)
    return (f'<polygon points="{s}" fill="{ink}" transform="translate({off} {off})"/>'
            f'<polygon points="{s}" fill="{fill}" stroke="{ink}" stroke-width="9" stroke-linejoin="round"/>')
def art(p, bgr=True):
    o=[rect(0,0,512,512,p['bg'])] if bgr else []
    ink=p['ink']
    bw,gap=96,22; x0=256-(3*bw+2*gap)/2-6; base=392
    for i,(h,c) in enumerate([(120,p['c1']),(204,p['c2']),(290,p['c3'])]):
        o.append(box(x0+i*(bw+gap),base-h,bw,h,c,ink))
    o.append(box(x0-18,base-2,3*bw+2*gap+36,26,ink,ink,r=8,off=0,sw=2))
    o[-1]=rect(x0-18+OFF,base-2+OFF,3*bw+2*gap+36,26,ink,8)+rect(x0-18,base-2,3*bw+2*gap+36,26,p['c4'],8,f'stroke="{ink}" stroke-width="{SW}"')
    # 圓形貼紙：上升箭頭
    cx,cy,R=x0+62,142,52
    o.append(circ(cx+10,cy+10,R,ink)); o.append(circ(cx,cy,R-5,p['c4'],f'stroke="{ink}" stroke-width="{SW}"'))
    o.append(f'<path d="M{cx-22} {cy+22} L{cx+20} {cy-20} M{cx-2} {cy-22} L{cx+22} {cy-22} L{cx+22} {cy+2}" fill="none" stroke="{ink}" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/>')
    return ''.join(o)
PAL=dict(bg='#FFC93C',ink=INK,c1='#FF8FB1',c2='#2B6BF3',c3='#E8590C',c4='#FFF7E8',txt=INK)
NAME='新粗野主義'
def hz(p):
    ink=INK
    o=[rect(0,0,1200,400,p['bg'])]
    o.append(f'<g transform="translate(46 40) scale(0.69)">{art(p,False)}</g>')
    # 字標：白底粗框牌 + 硬陰影
    x,y,w,h=470,92,660,150
    o.append(box(x,y,w,h,CREAM,ink,r=14,off=14,sw=10))
    d,ww=text('sans','哩股哩股',112,0,0,ls=14); d,ww=text('sans','哩股哩股',112,x+w/2-ww/2,y+h/2+40,ls=14)
    o.append(P(d,ink))
    x2,y2,w2,h2=470,278,420,64
    o.append(box(x2,y2,w2,h2,p['c3'],ink,r=12,off=10,sw=8))
    d,ww=text('inter','LIGU LIGU',40,0,0,ls=12); d,ww=text('inter','LIGU LIGU',40,x2+w2/2-ww/2,y2+h2/2+14,ls=12)
    o.append(P(d,CREAM))
    return 1200,400,''.join(o)
