from kit import *
def art(p, bgr=True):
    o=[rect(0,0,512,512,p['bg'])] if bgr else []
    H=166; x=256-H; y=256-H; S=2*H
    # 磚底影與磚面
    o.append(rect(x+8,y+10,S,S,'#07586A',18,'opacity=".45"'))
    o.append(rect(x,y,S,S,p['tile'],18))
    o.append(rect(x+14,y+14,S-28,S-28,'none',10,f'stroke="{p["ink"]}" stroke-width="6"'))
    o.append(rect(x+26,y+26,S-52,S-52,'none',5,f'stroke="{p["ink"]}" stroke-width="2.5" opacity=".7"'))
    i0=x+30; i1=x+S-30; j0=y+30; j1=y+S-30
    o.append(f'<clipPath id="tl"><rect x="{i0}" y="{j0}" width="{i1-i0}" height="{j1-j0}" rx="3"/></clipPath><g clip-path="url(#tl)">')
    for cx_,cy_ in [(i0,j0),(i1,j0),(i0,j1),(i1,j1)]:
        o.append(circ(cx_,cy_,58,p['blue'])); o.append(circ(cx_,cy_,42,p['tile'])); o.append(circ(cx_,cy_,26,p['acc'])); o.append(circ(cx_,cy_,10,p['tile']))
    o.append('</g>')
    # 中央：四大瓣＋四小瓣
    big="M0 -30 C 46 -60 46 -104 0 -132 C -46 -104 -46 -60 0 -30Z"
    small="M0 -34 C 28 -54 28 -78 0 -98 C -28 -78 -28 -54 0 -34Z"
    for i in range(4):
        o.append(f'<g transform="translate(256 256) rotate({45+90*i})"><path d="{small}" fill="{p["teal"]}"/></g>')
    for i in range(4):
        o.append(f'<g transform="translate(256 256) rotate({90*i})"><path d="{big}" fill="{p["acc"]}"/><path d="M0 -44 C 18 -62 18 -92 0 -110 C -18 -92 -18 -62 0 -44Z" fill="{p["tile"]}" opacity=".9"/></g>')
    o.append(circ(256,256,36,p['ink'])); o.append(circ(256,256,22,p['tile'])); o.append(circ(256,256,10,p['acc']))
    return ''.join(o)
PAL=dict(bg='#0A8CA3',tile='#FFF7E8',ink=INK,acc='#E8590C',blue='#2B6BF3',teal='#0A8CA3',txt='#FFF7E8')
NAME='花磚紋樣'
def hz(p):
    o=[rect(0,0,1200,400,p['bg'])]
    # 紅磚疊砌淡紋（極簡）
    for r in range(6):
        for c in range(-1,12):
            xx=c*120+(60 if r%2 else 0); yy=r*68-4
            o.append(rect(xx,yy,112,60,'#FFFFFF',6,'opacity=".05"'))
    o.append(f'<g transform="translate(56 30) scale(0.68)">{art(p,False)}</g>')
    d,w=text('sans7','哩股哩股',150,500,226,ls=8); o.append(P(d,CREAM))
    dd,ww=text('inter','LIGU LIGU',52,504,318,ls=22); o.append(P(dd,YEL))
    return 1200,400,''.join(o)
