from kit import *
import random
def wash(i, color, pts, seed, op=.78, disp=34):
    return (f'<filter id="w{i}" x="-25%" y="-25%" width="150%" height="150%" color-interpolation-filters="sRGB">'
      f'<feTurbulence type="fractalNoise" baseFrequency="0.011 0.014" numOctaves="3" seed="{seed}" result="n1"/>'
      f'<feDisplacementMap in="SourceGraphic" in2="n1" scale="{disp}" xChannelSelector="R" yChannelSelector="G" result="d"/>'
      f'<feGaussianBlur in="d" stdDeviation="1.1" result="db"/>'
      f'<feTurbulence type="fractalNoise" baseFrequency="0.03" numOctaves="4" seed="{seed+5}" result="n2"/>'
      f'<feColorMatrix in="n2" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 -1.5 1.55" result="na"/>'
      f'<feComposite in="db" in2="na" operator="in"/></filter>'
      f'<g filter="url(#w{i})" style="mix-blend-mode:multiply"><path d="{pts}" fill="{color}" fill-opacity="{op}" stroke="{color}" stroke-opacity=".5" stroke-width="9" stroke-linejoin="round"/></g>')
def blob(cx,cy,r,seed,n=14,j=.10):
    rnd=random.Random(seed); pts=[]
    for k in range(n):
        a=2*math.pi*k/n; rr=r*(1+rnd.uniform(-j,j)); pts.append((cx+rr*math.cos(a),cy+rr*math.sin(a)))
    # 平滑封閉曲線
    d=f'M{(pts[0][0]+pts[-1][0])/2:.1f} {(pts[0][1]+pts[-1][1])/2:.1f}'
    for k in range(n):
        p1=pts[k]; p2=pts[(k+1)%n]; d+=f' Q{p1[0]:.1f} {p1[1]:.1f} {(p1[0]+p2[0])/2:.1f} {(p1[1]+p2[1])/2:.1f}'
    return d+'Z'
def art(p, bgr=True):
    o=[rect(0,0,512,512,p['bg'])] if bgr else []
    o.append(wash(1,'#FFC93C',blob(228,206,150,1),3,.85))
    o.append(wash(2,'#F0701E',blob(196,246,112,2),11,.8))
    o.append(wash(3,'#2B6BF3',blob(338,332,118,3),21,.8))
    o.append(wash(4,'#7B4FE0',blob(392,146,52,4),31,.75,22))
    # 墨點飛濺
    for x,y,r in [(116,372,9),(92,340,5),(430,420,8),(150,432,4.5),(452,252,5.5),(70,170,4)]:
        o.append(circ(x,y,r,p['ink'],'opacity=".8"'))
    o.append(P(cg('sans7','哩',290,254,258),p['ink']))
    return ''.join(o)
PAL=dict(bg=CREAM,ink=INK,txt=INK)
NAME='水彩潑墨'
def hz(p):
    w,h,inner=default_hz(p,art,tfont='sans7',tcolor=INK,subcolor=TEA,mark_scale=0.86)
    return w,h,inner
