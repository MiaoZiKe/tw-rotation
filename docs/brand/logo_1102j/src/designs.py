"""第十輪（J 系列）：只做貼主題的概念。每款回傳 (底色, 100x100 座標的圖示內容)。"""
import math
from lib import n2, glyph

NAVY='#1F2A44'; CREAM='#FFF7E8'; OR='#E8590C'; BL='#2B6BF3'; PU='#7B4FE0'; TE='#0A8CA3'; RED='#D62839'; GRN='#0B8F4D'
# 深底用的提亮版（同色相）
OR2='#FF8A3D'; BL2='#6C9BFF'; PU2='#B197FF'; TE2='#3CC8DC'; RED2='#FF5468'; GRN2='#2FD08A'

def pt(cx,cy,r,a): return cx+r*math.cos(math.radians(a)), cy+r*math.sin(math.radians(a))
def circ(x,y,r,f,e=''): return f'<circle cx="{n2(x)}" cy="{n2(y)}" r="{n2(r)}" fill="{f}" {e}/>'
def rect(x,y,w,h,f,r=0,e=''): return f'<rect x="{n2(x)}" y="{n2(y)}" width="{n2(w)}" height="{n2(h)}" rx="{n2(r)}" fill="{f}" {e}/>'
def path(d,f='none',s=None,sw=0,e='',cap='round'):
    st=f' stroke="{s}" stroke-width="{n2(sw)}" stroke-linecap="{cap}" stroke-linejoin="round"' if s else ''
    return f'<path d="{d}" fill="{f}"{st} {e}/>'
def arc_arrow(cx,cy,r,a0,a1,col,sw,head=11,hw=7.5):
    """順時針弧線＋三角箭頭（箭頭尖端在 a1）"""
    ae=a1-math.degrees((head*0.8)/r)
    x0,y0=pt(cx,cy,r,a0); x1,y1=pt(cx,cy,r,ae)
    big=1 if ae-a0>180 else 0
    s=path(f'M{n2(x0)},{n2(y0)} A{n2(r)},{n2(r)} 0 {big} 1 {n2(x1)},{n2(y1)}',s=col,sw=sw)
    tx,ty=pt(cx,cy,r,a1+0); # 尖端沿切線再前進一點
    ang=math.radians(a1); tdx,tdy=-math.sin(ang),math.cos(ang); nx,ny=math.cos(ang),math.sin(ang)
    bx,by=pt(cx,cy,r,a1-math.degrees(head/r)); tipx,tipy=bx+tdx*head*1.0,by+tdy*head*1.0
    tipx,tipy=pt(cx,cy,r,a1)
    p1=(bx+nx*hw,by+ny*hw); p2=(bx-nx*hw,by-ny*hw)
    s+=path(f'M{n2(p1[0])},{n2(p1[1])} L{n2(tipx)},{n2(tipy)} L{n2(p2[0])},{n2(p2[1])} Z',col,col,2)
    return s
def candle(x,w,top,bot,wt,wb,col,r=1.5): 
    return rect(x+w/2-0.9,wt,1.8,wb-wt,col,0.9)+rect(x,top,w,bot-top,col,r)

D=[]
def design(id,name,theme,idea):
    def deco(fn): D.append(dict(id=id,name=name,theme=theme,idea=idea,mk=fn)); return fn
    return deco

# J01 ------------------------------------------------------------------
@design('J01','族群輪動箭頭','錢往哪個族群跑（資金在族群之間流動）',
        '三個族群色塊（藍／紫／青）排成三角，橘色箭頭順時針從一個族群接力跳到下一個＝資金輪動；中心留一點柔光，色塊有高光與底影的層次。')
def j01():
    s=''
    cx,cy=50,55
    s+=circ(cx,cy,19,'#FFE3C2','opacity=".55"')
    blocks=[(-90,BL,'#6C9BFF'),(30,TE,'#3CC8DC'),(150,PU,'#B197FF')]
    for a,c,hi in blocks:
        x,y=pt(cx,cy,28,a)
        s+=rect(x-11,y-9,22,22,'#1F2A44',6,'opacity=".14"')           # 底影
        s+=rect(x-11,y-11,22,22,c,6)
        s+=rect(x-8,y-8.5,16,5,hi,2.5,'opacity=".55"')                 # 高光
    for a0 in (-90,30,150):
        s+=arc_arrow(cx,cy,28,a0+36,a0+120-34,OR,5.2,10,7)
    return CREAM,s

# J02 ------------------------------------------------------------------
@design('J02','輪動時鐘','錢往哪個族群跑（輪動時鐘：指針＝錢現在在哪）',
        '四段色環＝四個象限／族群，指針停在橘色那一段，指尖一顆亮點＝「錢現在在這」；指針後方拖一段淡尾跡表示剛從隔壁輪過來。')
def j02():
    s=''; cx=cy=50; r=33
    cols=[(OR2),(PU2),(BL2),(TE2)]
    for i,c in enumerate(cols):
        a0=-90+i*90+4; a1=-90+(i+1)*90-4
        x0,y0=pt(cx,cy,r,a0); x1,y1=pt(cx,cy,r,a1)
        s+=path(f'M{n2(x0)},{n2(y0)} A{r},{r} 0 0 1 {n2(x1)},{n2(y1)}',s=c,sw=13,cap='butt')
    s+=circ(cx,cy,20,'#2A3858')
    # 尾跡
    for k,al in enumerate((.18,.3,.45)):
        a=-45-26+k*9
        x,y=pt(cx,cy,r,a); s+=circ(x,y,4.5+k*.8,CREAM,f'opacity="{al}"')
    ax,ay=pt(cx,cy,r,-45)
    s+=path(f'M{cx},{cy} L{n2(ax)},{n2(ay)}',s=CREAM,sw=5)
    s+=circ(ax,ay,8,CREAM)+circ(ax,ay,4,OR)
    s+=circ(cx,cy,6.5,CREAM)+circ(cx,cy,2.6,NAVY)
    return NAVY,s

# J03 ------------------------------------------------------------------
@design('J03','熱力圖 L','族群熱力圖（哪格最熱、錢集中在哪）',
        '4×4 熱力圖方格，只有組成字母 L 的 7 格上了橘色，越靠轉角越熱（色階由淺到深）；其餘格子是淡藍／淡紫／淡青底，像一張真的族群熱力圖。')
def j03():
    s=''; cell=13; gap=3; off=18
    vals={(0,0):.45,(0,1):.62,(0,2):.8,(0,3):1.0,(1,3):.88,(2,3):.7,(3,3):.52}
    tint=[BL,PU,TE]
    def mix(v):
        a=(255,196,150); b=(232,89,12)
        return '#%02x%02x%02x'%tuple(round(a[i]+(b[i]-a[i])*v) for i in range(3))
    k=0
    for c in range(4):
        for r in range(4):
            x=off+c*(cell+gap); y=off+r*(cell+gap)
            if (c,r) in vals: s+=rect(x,y,cell,cell,mix(vals[(c,r)]),3.2)
            else:
                s+=rect(x,y,cell,cell,tint[k%3],3.2,f'opacity="{[.3,.42,.26,.36][k%4]}"'); k+=1
    return CREAM,s

# J04 ------------------------------------------------------------------
@design('J04','K 線＋量柱 L','台股（K 線、紅漲綠跌、成交量）',
        'L 的直筆是一根紅 K 棒（含上下影線），L 的橫筆是由低到高的成交量柱；右上再加兩根小 K 棒（綠、紅）形成走勢，一眼就是台股盤面。')
def j04():
    s=''
    s+=path('M18,80.5 H84',s=NAVY,sw=1.8,e='opacity=".35"')
    s+=candle(22,15,26,64,15,74,RED,2.5)
    hs=[10,17,25,35]; cs=[NAVY,NAVY,NAVY,RED]
    for i,h in enumerate(hs):
        s+=rect(43+i*11.5,79-h,8.5,h,cs[i],2,'opacity=".92"' if cs[i]==NAVY else '')
    s+=candle(54,8,34,44,30,50,GRN,1.8)
    s+=candle(68,8,26,37,22,42,RED,1.8)
    return CREAM,s

# J05 ------------------------------------------------------------------
@design('J05','ETF 堆疊硬幣','ETF 存股（長期累積、配息）',
        '三疊硬幣逐年長高（2→4→6 枚），最高一疊頂上一顆「配息」小亮點；底下一條基準線＋三個年度刻度＝年年累積。')
def j05():
    s=''; base=80; th=6.6; rx=11.5; ry=4.4
    s+=rect(14,base+4,72,3.2,CREAM,1.6,'opacity=".35"')
    for i,(cx,n) in enumerate(((27,2),(50,4),(73,6))):
        for k in range(n):
            y=base-k*th
            s+=f'<ellipse cx="{cx}" cy="{n2(y)}" rx="{rx}" ry="{ry}" fill="#B93F00"/>'
            s+=rect(cx-rx,y-th,2*rx,th,OR,0)
            s+=f'<ellipse cx="{cx}" cy="{n2(y)}" rx="{rx}" ry="{ry}" fill="#E8590C"/>'
            if k: s+=path(f'M{cx-rx+.5},{n2(y)} A{rx-.5},{ry} 0 0 0 {cx+rx-.5},{n2(y)}',s='#FFB070',sw=1,e='opacity=".7"')
            s+=f'<ellipse cx="{cx}" cy="{n2(y-th)}" rx="{rx}" ry="{ry}" fill="{OR2}"/>'
            s+=f'<ellipse cx="{cx}" cy="{n2(y-th)}" rx="{rx-4}" ry="{ry-1.6}" fill="none" stroke="#FFD2A8" stroke-width="1" opacity=".8"/>'
        # 去掉兩側因橢圓重疊產生的縫
    top=base-6*th-th
    sx,sy=73,top-9
    s+=path(f'M{sx},{sy-6} Q{sx},{sy} {sx+6},{sy} Q{sx},{sy} {sx},{sy+6} Q{sx},{sy} {sx-6},{sy} Q{sx},{sy} {sx},{sy-6} Z',CREAM,CREAM,1.2)
    return NAVY,s

# J06 ------------------------------------------------------------------
@design('J06','輪轉圓餅','族群資金占比輪轉（圓餅分塊）',
        '圓餅分成五塊族群占比，橘色最大那塊被拉出來（現在錢最多的族群），外圈一條藍色弧形箭頭沿圓餅順時針繞＝占比在輪轉。')
def j06():
    s=''; cx,cy,r=49,50,26
    vals=[(30,OR),(25,BL),(20,PU),(15,TE),(10,NAVY)]; a=-90; 
    for i,(v,c) in enumerate(vals):
        a1=a+v*3.6; mid=(a+a1)/2
        ox,oy=(pt(0,0,5,mid) if i==0 else (0,0))
        x0,y0=pt(cx+ox,cy+oy,r,a); x1,y1=pt(cx+ox,cy+oy,r,a1)
        big=1 if a1-a>180 else 0
        s+=path(f'M{n2(cx+ox)},{n2(cy+oy)} L{n2(x0)},{n2(y0)} A{r},{r} 0 {big} 1 {n2(x1)},{n2(y1)} Z',c,CREAM,2.4)
        a=a1
    s+=arc_arrow(cx,cy,37,-8,72,BL,4.4,9,6.5)
    return CREAM,s

# J07 ------------------------------------------------------------------
@design('J07','族群泡泡圖','產業鏈／族群地圖（族群大小與位置）',
        '族群泡泡圖：每顆泡泡一個族群，大小＝成交金額；橘色泡泡留著三顆漸淡的殘影，表示它一路從左下輪到右上；背景是淡淡的十字象限線。')
def j07():
    s=''
    s+=path('M50,16 V84 M16,50 H84',s=NAVY,sw=1.4,e='opacity=".18"')
    for x,y,r,c in ((27,30,9,PU),(30,66,12,BL),(68,70,10,TE),(52,82,0,NAVY)):
        if r: s+=circ(x,y,r,c,'opacity=".92"')+circ(x-r*.3,y-r*.35,r*.3,'#FFF','opacity=".28"')
    for x,y,r,al in ((40,60,8,.18),(49,51,11,.32),(57,43,14,.5)):
        s+=circ(x,y,r,OR,f'opacity="{al}"')
    s+=circ(68,34,17,OR)+circ(68-5,34-6,5,'#fff','opacity=".3"')
    return CREAM,s

# J08 ------------------------------------------------------------------
@design('J08','資金河流','錢往哪個族群跑（桑基圖：資金流量與流向）',
        '桑基圖意象：左邊四條資金來源（橘、藍、紫、青）帶狀流過交叉，匯入右邊兩個族群節點；橘色那條最寬最亮＝流量最大的一條。')
def j08():
    s=''; xa,xb=20,80; xm=50
    def band(a0,a1,b0,b1,c,al):
        return path(f'M{xa},{a0} C{xm},{a0} {xm},{b0} {xb},{b0} L{xb},{b1} C{xm},{b1} {xm},{a1} {xa},{a1} Z',c,e=f'opacity="{al}"')
    s+=band(37,49,54,66,BL2,.8)      # 藍→右下（與紫交叉）
    s+=band(52,62,36,46,PU2,.8)      # 紫→右上
    s+=band(65,73,66,74,TE2,.85)
    s+=band(20,34,22,36,OR2,.95)
    for y0,y1,c in ((20,34,OR2),(37,49,BL2),(52,62,PU2),(65,73,TE2)): s+=rect(xa-5,y0,5,y1-y0,c,1.5)
    s+=rect(xb,22,5,24,CREAM,1.5)+rect(xb,54,5,20,CREAM,1.5)
    return NAVY,s

# J09 ------------------------------------------------------------------
@design('J09','族群雷達','錢往哪個族群跑（雷達掃描找出資金熱點）',
        '雷達掃描盤面：同心環＝強弱層級，掃描扇形一路掃過各族群光點（藍／紫／青），停在橘色的最亮點＝資金熱點，外圈一圈漣漪。')
def j09():
    s=''; cx=cy=50
    for r in (38,26,14): s+=circ(cx,cy,r,'none',f'stroke="{CREAM}" stroke-width="1.8" opacity=".3"')
    s+=path('M50,12 V88 M12,50 H88',s=CREAM,sw=1.2,e='opacity=".18"')
    a_end=-40
    for k in range(7):
        a0=a_end-70+k*10; a1=a0+10
        x0,y0=pt(cx,cy,38,a0); x1,y1=pt(cx,cy,38,a1)
        s+=path(f'M{cx},{cy} L{n2(x0)},{n2(y0)} A38,38 0 0 1 {n2(x1)},{n2(y1)} Z',TE2,e=f'opacity="{.04+k*.05:.2f}"')
    x,y=pt(cx,cy,38,a_end); s+=path(f'M{cx},{cy} L{n2(x)},{n2(y)}',s=TE2,sw=2.4)
    for ang,rr,c,sz in ((-120,24,BL2,4),(-82,14,PU2,3.6),(170,30,TE2,3.6),(60,22,BL2,3.4),(110,12,PU2,3)):
        px,py=pt(cx,cy,rr,ang); s+=circ(px,py,sz,c)
    hx,hy=pt(cx,cy,27,-52)
    s+=circ(hx,hy,10,OR2,'opacity=".25"')+circ(hx,hy,6,OR2)+circ(hx,hy,2.2,CREAM)
    return NAVY,s

# J10 ------------------------------------------------------------------
@design('J10','放大鏡看 K 線','台股 K 線＋每天盤後 3 分鐘看清楚（不預測，只看清楚）',
        '放大鏡把一排 K 線放大（紅漲綠跌），鏡片內的 K 線被放大到一眼看清；橘色握把。不預測、不報明牌，只是把盤面看清楚。')
def j10():
    s=''
    s+=path('M64,64 L82,82',s=OR,sw=11)
    s+=circ(41,41,27,'#FFFFFF')+circ(41,41,27,'none',f'stroke="{NAVY}" stroke-width="6.5"')
    s+='<clipPath id="lens"><circle cx="41" cy="41" r="23"/></clipPath><g clip-path="url(#lens)">'
    s+=candle(25,7,44,54,39,59,GRN,2)+candle(35,7,38,50,32,54,RED,2)+candle(45,7,40,48,34,54,GRN,2)+candle(55,7,28,41,23,46,RED,2)
    s+='</g>'
    s+=path('M24,30 A20,20 0 0 1 33,21',s='#FFFFFF',sw=3,e='opacity=".9"')
    return CREAM,s

# J11 ------------------------------------------------------------------
@design('J11','存股複利曲線','ETF 存股（長期累積、配息再投入）',
        'L 形座標軸＋一條越爬越陡的複利曲線，曲線下方橘色面積；線上依序放大的硬幣＝每年配息再投入，最後一顆發亮＝累積的成果。')
def j11():
    s=''; 
    def y_of(t): return 72-48*(math.exp(3*t)-1)/(math.exp(3)-1)
    pts=[(30+48*t/40, y_of(t/40)) for t in range(41)]
    d='M'+' L'.join(f'{n2(x)},{n2(y)}' for x,y in pts)
    s+=path(d+' L78,76 L30,76 Z',OR2,e='opacity=".25"')
    s+=path('M22,18 V76 H82',s=CREAM,sw=5.5)
    s+=path(d,s=OR2,sw=5)
    for t,r in ((.25,2.8),(.5,3.7),(.75,4.8)):
        s+=circ(30+48*t,y_of(t),r,CREAM,f'stroke="{OR2}" stroke-width="1.8"')
    s+=circ(78,y_of(1),9,OR2,'opacity=".3"')+circ(78,y_of(1),6,CREAM,f'stroke="{OR2}" stroke-width="2.4"')
    return NAVY,s

# J12 ------------------------------------------------------------------
@design('J12','盤後三分鐘','每天盤後 3 分鐘看懂（簡單、快速）＋台股 K 線',
        '碼表／計時鐘面：橘色扇形＝3 分鐘（指針停在 3 點鐘），鐘面下半放三根迷你 K 棒（紅綠紅）＝這 3 分鐘看的是台股盤面。')
def j12():
    s=''; cx,cy,r=50,55,31
    s+=rect(44,12,12,6,NAVY,2.5)+rect(47.5,16,5,6,NAVY)+path('M77,29 L82,24',s=NAVY,sw=5)
    s+=circ(cx,cy,r+4,NAVY)+circ(cx,cy,r,'#FFFFFF')
    x1,y1=pt(cx,cy,r-3,0)
    s+=path(f'M{cx},{cy} L{cx},{cy-r+3} A{r-3},{r-3} 0 0 1 {n2(x1)},{n2(y1)} Z',OR)
    for k in range(12):
        a=-90+k*30; xa,ya=pt(cx,cy,r-3,a); xb,yb=pt(cx,cy,r-7,a)
        if k in (1,2): continue
        s+=path(f'M{n2(xa)},{n2(ya)} L{n2(xb)},{n2(yb)}',s=NAVY,sw=1.8 if k%3 else 2.6)
    s+=candle(34,6,66,73,63,77,RED,1.4)+candle(47,6,62,70,59,75,GRN,1.4)+candle(60,6,58,67,55,72,RED,1.4)
    d,adv,bd=glyph('poppins','3',20)
    s+=f'<path transform="translate({n2(63-adv/2)},{n2(46)})" d="{d}" fill="#FFF7E8"/>'
    s+=circ(cx,cy,4.5,NAVY)
    return CREAM,s
