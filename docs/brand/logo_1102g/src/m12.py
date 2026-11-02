from kit import *
GOLD1='#FFE59A'; GOLD2='#E9B64B'; GOLD3='#B27A1C'
def octagon(R, rot=22.5):
    return ' '.join(f'{256+R*math.cos(math.radians(rot+45*i)):.1f},{256+R*math.sin(math.radians(rot+45*i)):.1f}' for i in range(8))
def art(p, bgr=True):
    o=[]
    o.append(f'<defs><linearGradient id="gd" x1="0" y1="0" x2="0.35" y2="1"><stop offset="0" stop-color="{GOLD1}"/><stop offset=".5" stop-color="{GOLD2}"/><stop offset="1" stop-color="{GOLD3}"/></linearGradient>'
             f'<radialGradient id="bgr" cx="50%" cy="62%" r="70%"><stop offset="0" stop-color="#2E3C63"/><stop offset="1" stop-color="#141C33"/></radialGradient></defs>')
    if bgr: o.append(rect(0,0,512,512,'url(#bgr)'))
    o.append(f'<polygon points="{octagon(236)}" fill="none" stroke="url(#gd)" stroke-width="6" stroke-linejoin="miter"/>')
    o.append(f'<polygon points="{octagon(218)}" fill="none" stroke="url(#gd)" stroke-width="2.5" opacity=".9"/>')
    o.append('<g transform="translate(256 250) scale(1.14) translate(-256 -262)">')
    # 扇形光芒（從塔底中心放射）
    cx,cy=256,376
    rays=[]
    for i in range(0,13):
        ang=math.radians(180+i*15)
        r0=72; r1=150 if i%2==0 else 118
        rays.append(f'M{cx+r0*math.cos(ang):.1f} {cy+r0*math.sin(ang):.1f} L{cx+r1*math.cos(ang):.1f} {cy+r1*math.sin(ang):.1f}')
    o.append(f'<path d="{" ".join(rays)}" stroke="url(#gd)" stroke-width="5" fill="none"/>')
    # 弧線（細）
    o.append(f'<path d="M{cx-128} {cy} A128 128 0 0 1 {cx+128} {cy}" fill="none" stroke="url(#gd)" stroke-width="2.5" opacity=".85"/>')
    # 階梯塔（對稱，四層）
    tiers=[(150,28),(114,34),(80,42),(46,52)]
    y=cy; 
    for wd,h in tiers:
        y-=h
        o.append(rect(cx-wd/2,y,wd,h,'url(#gd)'))
        # 層間細縫
        o.append(rect(cx-wd/2,y+h-3,wd,3,'#141C33'))
    # 塔身中線（細）
    o.append(f'<path d="M{cx} {cy-28-34-42-52+8} V{cy-4}" stroke="#141C33" stroke-width="2.5" opacity=".55"/>')
    # 尖塔與菱形
    ty=y
    o.append(rect(cx-4,ty-46,8,48,'url(#gd)'))
    o.append(f'<polygon points="{cx},{ty-84} {cx+14},{ty-62} {cx},{ty-40} {cx-14},{ty-62}" fill="url(#gd)"/>')
    # 底座雙線
    o.append(rect(cx-112,cy+14,224,5,'url(#gd)')); o.append(rect(cx-76,cy+28,152,2.5,'url(#gd)'))
    o.append('</g>')
    return ''.join(o)
PAL=dict(bg='#141C33',txt=GOLD2)
NAME='裝飾藝術'
def hz(p):
    w,h,inner=default_hz(dict(p,bg='#141C33'),art,tfont='serif',tcolor='url(#gd)',subcolor='url(#gd)',tsize=140,mark_scale=0.86,ls=10)
    return w,h,inner
