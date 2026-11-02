from kit import *
def bulbs(cx,cy,R,n,r,c1,c2,gid='bg'):
    o=[]
    for i in range(n):
        a=2*math.pi*i/n-math.pi/2; x=cx+R*math.cos(a); y=cy+R*math.sin(a)
        c=c1 if i%2==0 else c2
        o.append(circ(round(x,1),round(y,1),r*2.3,f'url(#{gid})'))
    for i in range(n):
        a=2*math.pi*i/n-math.pi/2; x=cx+R*math.cos(a); y=cy+R*math.sin(a)
        c=c1 if i%2==0 else c2
        o.append(circ(round(x,1),round(y,1),r,c,f'stroke="#7A2A06" stroke-width="3"'))
    return ''.join(o)
def sign(s,size,cx,cy,p,ls=0,k='sans',off=10):
    d=cgs(k,s,size,cx,cy,ls=ls)
    return (P(d,p['shadow'],f'transform="translate({off} {off})" stroke="{p["shadow"]}" stroke-width="20" stroke-linejoin="round"')
           +P(d,p['ink'],f'stroke="{p["ink"]}" stroke-width="20" stroke-linejoin="round"')
           +P(d,p['face']))
def art(p, bgr=True):
    o=[f'<defs><radialGradient id="rb" cx="50%" cy="42%" r="75%"><stop offset="0" stop-color="#F26F20"/><stop offset="1" stop-color="#C9440A"/></radialGradient>'
       f'<radialGradient id="bg"><stop offset="0" stop-color="#FFE9A0" stop-opacity=".75"/><stop offset="1" stop-color="#FFE9A0" stop-opacity="0"/></radialGradient></defs>']
    if bgr: o.append(rect(0,0,512,512,'url(#rb)'))
    o.append(f'<circle cx="256" cy="256" r="212" fill="none" stroke="{p["ink"]}" stroke-width="7"/>')
    o.append(f'<circle cx="256" cy="256" r="198" fill="none" stroke="#FFE9A0" stroke-width="3" opacity=".8"/>')
    o.append(bulbs(256,256,230,28,9.5,'#FFF3C4','#FFD84D'))
    # 招牌字：兩字橫排
    o.append(sign('哩股',160,256,226,p,ls=8))
    # 底下小橫牌
    bw=214; o.append(rect(256-bw/2,324,bw,48,p['ink'],24))
    d,w=text('inter','LIGU',34,0,0,ls=12); dd,ww=text('inter','LIGU',34,256-(w)/2,360,ls=12)
    o.append(P(dd,'#FFE9A0'))
    return ''.join(o)
PAL=dict(bg='#E8590C',ink=INK,face='#FFD84D',shadow='#8F2D00',txt=INK)
NAME='老招牌'
def hz(p):
    o=[rect(0,0,1200,400,'url(#rb)')]
    o.append('<defs><radialGradient id="rb" cx="50%" cy="42%" r="75%"><stop offset="0" stop-color="#F26F20"/><stop offset="1" stop-color="#C9440A"/></radialGradient></defs>')
    o.append(f'<g transform="translate(40 30) scale(0.72)">{art(p,False)}</g>')
    o.append(sign('哩股哩股',148,760,170,p,ls=10,off=8))
    d,w=text('inter','LIGU  LIGU',50,0,0,ls=18); dd,ww=text('inter','LIGU  LIGU',50,760-w/2,330,ls=18)
    o.append(P(dd,'#FFE9A0'))
    return 1200,400,''.join(o)
