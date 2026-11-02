from kit import *
def lerp(c0,c1,t):
    a=[int(c0[i:i+2],16) for i in (1,3,5)]; b=[int(c1[i:i+2],16) for i in (1,3,5)]
    return '#%02X%02X%02X'%tuple(round(a[i]+(b[i]-a[i])*t) for i in range(3))
def extrude(d, gid, depth, c0, c1, face, edge, x=0, y=0, step=0.7, dx=0.8, dy=0.8):
    n=int(depth/step); o=[f'<defs><path id="{gid}" d="{d}"/></defs>']
    for i in range(n,0,-1):
        t=i/n   # i 大＝離臉遠（深處）
        o.append(f'<use href="#{gid}" x="{x+i*step*dx:.2f}" y="{y+i*step*dy:.2f}" fill="{lerp(c0,c1,t)}"/>')
    o.append(f'<use href="#{gid}" x="{x}" y="{y}" fill="{face}"/>')
    return ''.join(o)
def art(p, bgr=True):
    o=['<defs><linearGradient id="f18" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFF6C2"/><stop offset="1" stop-color="#FFD84D"/></linearGradient><linearGradient id="b18" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3C7BFF"/><stop offset="1" stop-color="#1A3FB0"/></linearGradient>'
       '<filter id="s18" x="-20%" y="-20%" width="150%" height="150%"><feGaussianBlur stdDeviation="10"/></filter></defs>']
    if bgr: o.append(rect(0,0,512,512,'url(#b18)'))
    d=cg('sans','哩',336,236,236)
    o.append(f'<path d="{d}" fill="#0B1E6B" opacity=".5" transform="translate(52 62)" filter="url(#s18)"/>')
    o.append(extrude(d,'g18',44,'#F26A1B','#A83400','url(#f18)','#C94A0A',step=0.8))
    # 面上高光：內緣白線
    return ''.join(o)
PAL=dict(bg='#2B6BF3',face='#FFE27A',txt='#FFFFFF')
NAME='立體擠出字'
def hz(p):
    o=['<defs><linearGradient id="b18h" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3C7BFF"/><stop offset="1" stop-color="#1A3FB0"/></linearGradient></defs>',rect(0,0,1200,400,'url(#b18h)')]
    o.append(f'<g transform="translate(40 30) scale(0.68)">{art(p,False)}</g>')
    d,w=text('sans','哩股哩股',150,0,0,ls=6); d,w=text('sans','哩股哩股',150,500,222,ls=6)
    o.append(extrude(d,'t18',20,'#F26A1B','#A83400','#FFE27A','#C94A0A',step=0.8))
    dd,ww=text('inter','LIGU LIGU',52,500,336,ls=20); o.append(P(dd,'#FFFFFF'))
    return 1200,400,''.join(o)
