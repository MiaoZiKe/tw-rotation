from kit import *
PITCH=74
def art(p, bgr=True):
    o=[rect(0,0,512,512,p['bg'])] if bgr else []
    n=5
    x0=256-(n-1)*PITCH/2; y0=256-(n-1)*PITCH/2
    on={}
    sizes=[17,21,25,29,32]
    for r in range(n): on[(0,r)]=(p['ink'],sizes[r])
    on[(1,4)]=(p['ink'],32); on[(2,4)]=(p['ink'],32)
    on[(3,3)]=(p['acc'],32); on[(4,2)]=(p['acc'],40)
    for c in range(n):
        for r in range(n):
            x=x0+c*PITCH; y=y0+r*PITCH
            if (c,r) in on:
                col,rad=on[(c,r)]; o.append(circ(round(x,1),round(y,1),rad,col))
            else:
                o.append(circ(round(x,1),round(y,1),11,p['faint']))
    x=x0+4*PITCH; y=y0+2*PITCH
    o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="54" fill="none" stroke="{p["acc"]}" stroke-width="6"/>')
    return ''.join(o)
PAL=dict(bg=CREAM,ink=INK,acc=ORG,faint='#E3D2B4',txt=INK)
NAME='點陣矩陣'
def hz(p):
    return default_hz(p,art,tfont='sans7',tcolor=INK,subcolor=ORG,mark_scale=0.84)
