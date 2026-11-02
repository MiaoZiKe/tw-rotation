from kit import *
def spark(cx,cy,r,fill,extra='',k=0.10):
    c=r*k
    return (f'<path d="M{cx} {cy-r} Q{cx+c} {cy-c} {cx+r} {cy} Q{cx+c} {cy+c} {cx} {cy+r} Q{cx-c} {cy+c} {cx-r} {cy} Q{cx-c} {cy-c} {cx} {cy-r}Z" fill="{fill}" {extra}/>')
def art(p, bgr=True):
    o=['<defs>'
       '<radialGradient id="yb" cx="35%" cy="22%" r="95%"><stop offset="0" stop-color="#C9B6FF"/><stop offset=".45" stop-color="#7B4FE0"/><stop offset="1" stop-color="#2B3FC4"/></radialGradient>'
       '<linearGradient id="ch" gradientUnits="userSpaceOnUse" x1="0" y1="92" x2="0" y2="440">'
       '<stop offset="0" stop-color="#FFFFFF"/><stop offset=".22" stop-color="#D5E4FF"/><stop offset=".42" stop-color="#7C9BE8"/><stop offset=".50" stop-color="#1D2C78"/>'
       '<stop offset=".54" stop-color="#5E83E6"/><stop offset=".72" stop-color="#E7D2FF"/><stop offset=".88" stop-color="#FFB5E6"/><stop offset="1" stop-color="#FFFFFF"/></linearGradient>'
       '<filter id="sh" x="-20%" y="-20%" width="150%" height="150%"><feGaussianBlur stdDeviation="9"/></filter>'
       '<filter id="gl" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6"/></filter></defs>']
    if bgr: o.append(rect(0,0,512,512,'url(#yb)'))
    # 地面反光橢圓
    o.append(f'<ellipse cx="256" cy="448" rx="190" ry="26" fill="#1A1F6B" opacity=".45" filter="url(#sh)"/>')
    # 晶片 L：Inter ExtraBold
    dL=cg('inter','L',410,196,266)
    # 箭頭：由 L 腳右端往右上
    arrow=('M286 398 L330 398 L408 226 L440 240 L452 150 L368 176 L398 192 Z')
    shapes=[dL,arrow]
    for d in shapes:
        o.append(f'<path d="{d}" fill="#0E1550" opacity=".55" transform="translate(10 14)" filter="url(#sh)"/>')
    for i,d in enumerate(shapes):
        o.append(f'<clipPath id="cl{i}"><path d="{d}"/></clipPath>')
        o.append(f'<path d="{d}" fill="url(#ch)" stroke="#16206E" stroke-width="5" stroke-linejoin="round"/>')
        o.append(f'<g clip-path="url(#cl{i})"><path d="{d}" fill="none" stroke="#FFFFFF" stroke-width="12" stroke-linejoin="round" opacity=".75"/>'
                 f'<path d="{d}" fill="none" stroke="#5E83E6" stroke-width="3" transform="translate(5 6)" opacity=".5"/></g>')
    # 閃光
    o.append(spark(122,112,70,'#FFFFFF',k=0.07)); o.append(spark(122,112,70,'#FFFFFF','filter="url(#gl)" opacity=".7"',k=0.07))
    o.append(spark(424,356,30,'#FFFFFF',k=0.09)); o.append(spark(88,330,20,'#FFE9FF',k=0.09))
    return ''.join(o)
PAL=dict(bg='#7B4FE0',txt='#FFFFFF')
NAME='Y2K鉻金屬'
def hz(p):
    w,h,inner=default_hz(p,art,tfont='sans7',tcolor='url(#ch2)',subcolor='#FFFFFF',mark_scale=0.9,hbg='url(#yb)')
    defs=('<defs><radialGradient id="yb" cx="20%" cy="0%" r="130%"><stop offset="0" stop-color="#B9A2FF"/><stop offset=".5" stop-color="#7B4FE0"/><stop offset="1" stop-color="#2B3FC4"/></radialGradient>'
          '<linearGradient id="ch2" gradientUnits="userSpaceOnUse" x1="0" y1="96" x2="0" y2="240"><stop offset="0" stop-color="#FFFFFF"/><stop offset=".42" stop-color="#CFE0FF"/><stop offset=".5" stop-color="#1F2F9A"/><stop offset=".58" stop-color="#8FB0FF"/><stop offset="1" stop-color="#FFFFFF"/></linearGradient></defs>')
    inner=inner.replace(f'<path d="',f'<path stroke="#1A1F6B" stroke-width="6" stroke-linejoin="round" d="',0)
    return w,h,defs+inner
