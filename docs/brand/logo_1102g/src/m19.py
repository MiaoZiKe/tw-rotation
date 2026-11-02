from kit import *
import random
def sphere(x,y,r,gid): return circ(round(x,1),round(y,1),r,f'url(#{gid})')
def art(p, bgr=True):
    o=['<defs>'
       '<radialGradient id="sb" cx="50%" cy="45%" r="75%"><stop offset="0" stop-color="#2D3B68"/><stop offset="1" stop-color="#111729"/></radialGradient>'
       '<radialGradient id="pl" cx="34%" cy="30%" r="80%"><stop offset="0" stop-color="#FFC68A"/><stop offset=".38" stop-color="#F26A1B"/><stop offset="1" stop-color="#8F2D00"/></radialGradient>'
       '<radialGradient id="s1" cx="35%" cy="30%" r="75%"><stop offset="0" stop-color="#BFD4FF"/><stop offset=".45" stop-color="#2B6BF3"/><stop offset="1" stop-color="#14349A"/></radialGradient>'
       '<radialGradient id="s2" cx="35%" cy="30%" r="75%"><stop offset="0" stop-color="#C8FFF6"/><stop offset=".45" stop-color="#14B8C4"/><stop offset="1" stop-color="#07586A"/></radialGradient>'
       '<radialGradient id="s3" cx="35%" cy="30%" r="75%"><stop offset="0" stop-color="#FFF6C2"/><stop offset=".5" stop-color="#FFC93C"/><stop offset="1" stop-color="#C98A00"/></radialGradient>'
       '<radialGradient id="s4" cx="35%" cy="30%" r="75%"><stop offset="0" stop-color="#E4D4FF"/><stop offset=".5" stop-color="#8E63F0"/><stop offset="1" stop-color="#4A2AA8"/></radialGradient>'
       '<radialGradient id="gl" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#F26A1B" stop-opacity=".45"/><stop offset="1" stop-color="#F26A1B" stop-opacity="0"/></radialGradient>'
       '</defs>']
    if bgr: o.append(rect(0,0,512,512,'url(#sb)'))
    rnd=random.Random(7)
    for i in range(34):
        x,y=rnd.uniform(14,498),rnd.uniform(14,498)
        if math.hypot(x-256,y-256)<110: continue
        o.append(circ(round(x),round(y),rnd.choice([1.6,2.2,2.8]),'#FFF7E8',f'opacity="{rnd.choice([.45,.7,.9])}"'))
    cx=cy=256
    orbits=[dict(rx=196,ry=66,rot=-24,sat=[(196,'s1',24),(32,'s2',13)]),
            dict(rx=134,ry=44,rot=26,sat=[(118,'s3',17),(335,'s4',11)])]
    def half(rx,ry,front):
        return (f'M{cx+rx} {cy} A{rx} {ry} 0 0 1 {cx-rx} {cy}' if front else f'M{cx-rx} {cy} A{rx} {ry} 0 0 1 {cx+rx} {cy}')
    def satpos(rx,ry,ang):
        a=math.radians(ang); return cx+rx*math.cos(a), cy+ry*math.sin(a), math.sin(a)>0   # y>0＝畫面下半＝前
    back=[];front=[]
    for ob in orbits:
        rx,ry,rot=ob['rx'],ob['ry'],ob['rot']
        g=f'<g transform="rotate({rot} {cx} {cy})">'
        bs=g+f'<path d="{half(rx,ry,False)}" fill="none" stroke="#FFF7E8" stroke-opacity=".38" stroke-width="3.5"/>'
        fs=g+f'<path d="{half(rx,ry,True)}" fill="none" stroke="#FFF7E8" stroke-opacity=".9" stroke-width="4.5"/>'
        for ang,gid,r in ob['sat']:
            x,y,fr=satpos(rx,ry,ang)
            # 衛星須抵銷旋轉才是球形（圓不受影響）
            (fs if fr else bs)
            s=sphere(x,y,r,gid)+circ(round(x,1),round(y,1),r,'none',f'stroke="#0F1530" stroke-width="2.5" stroke-opacity=".5"')
            if fr: fs+=s
            else: bs+=s
        back.append(bs+'</g>'); front.append(fs+'</g>')
    o.append('<g transform="translate(256 256) scale(1.13) translate(-256 -256)">')
    o+=back
    o.append(circ(cx,cy,150,'url(#gl)'))
    o.append(circ(cx,cy,80,'url(#pl)'))
    # 星球條帶
    o.append(f'<clipPath id="pc"><circle cx="{cx}" cy="{cy}" r="80"/></clipPath><g clip-path="url(#pc)" opacity=".28"><path d="M170 232 Q256 214 342 236 L342 252 Q256 232 170 250Z" fill="#FFF0D8"/><path d="M170 272 Q256 258 342 276 L342 286 Q256 270 170 284Z" fill="#7A2200"/></g>')
    o+=front
    o.append('</g>')
    return ''.join(o)
PAL=dict(bg='#141B33',txt='#FFF7E8')
NAME='太空軌道'
def hz(p):
    w,h,inner=default_hz(p,art,tfont='sans7',tcolor='#FFF7E8',subcolor='#FFC93C',mark_scale=0.92,hbg='#141B33')
    # 橫式也要底：再放入星空漸層
    return w,h,'<defs><radialGradient id="sb" cx="20%" cy="45%" r="90%"><stop offset="0" stop-color="#2D3B68"/><stop offset="1" stop-color="#111729"/></radialGradient></defs>'+inner.replace('fill="#141B33"','fill="url(#sb)"',1)
