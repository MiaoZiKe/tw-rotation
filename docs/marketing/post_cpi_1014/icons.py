from lib import *
GOLD=(232,176,112); RED=(232,84,84); BLUE=(100,160,220); GREEN=(120,190,100); YEL2=(255,214,70); GRAY=(190,190,190)
def basket(c,box,cross=False,name=None):
    x0,y0,x1,y1=box; w=x1-x0; h=y1-y0
    by=y0+h*0.45
    # items
    # milk
    c.poly([(x0+w*.14,by),(x0+w*.14,y0+h*.12),(x0+w*.32,y0+h*.12),(x0+w*.32,by)],(255,255,255),BR,3)
    c.poly([(x0+w*.14,y0+h*.3),(x0+w*.32,y0+h*.3),(x0+w*.32,y0+h*.42),(x0+w*.14,y0+h*.42)],BLUE,None)
    # bread
    c.rr((x0+w*.36,y0+h*.2,x0+w*.62,by),14,(240,200,130),BR,3)
    # veg (green)
    c.ell((x0+w*.64,y0+h*.18,x0+w*.80,by+2),GREEN,BR,3)
    # oil bottle
    c.rr((x0+w*.82,y0+h*.1,x0+w*.94,by),8,YEL2,BR,3)
    c.poly([(x0,by),(x1,by),(x1-w*.1,y1),(x0+w*.1,y1)],GOLD,BR,4)
    for i in range(1,4):
        yy=by+(y1-by)*i/4; c.line([(x0+w*.04,yy),(x1-w*.04,yy)],(190,130,70),3)
    for i in range(1,6):
        xx=x0+w*i/6; c.line([(xx,by+2),(xx+(0 if True else 0),y1-2)],(190,130,70),3)
    if cross:
        for (a,b) in [((x0+w*.64,y0+h*.12),(x0+w*.80,by+8)),((x0+w*.82,y0+h*.04),(x0+w*.94,by+8))]:
            c.line([a,b],RED,7); c.line([(a[0],b[1]),(b[0],a[1])],RED,7)
def bowl(c,b):
    x0,y0,x1,y1=b; w=x1-x0; h=y1-y0
    c.ell((x0+w*.15,y0+h*.2,x0+w*.85,y0+h*.65),(255,255,255),BR,4)
    c.d.pieslice([(x0+w*.05)*S,(y0+h*.3)*S,(x0+w*.95)*S,(y0+h*1.0)*S],0,180,fill=(240,130,120),outline=BR,width=4*S)
    c.line([(x0+w*.65,y0+h*.05),(x0+w*.95,y0+h*.32)],BR,5); c.line([(x0+w*.75,y0),(x0+w*1.0,y0+h*.22)],BR,5)
def shirt(c,b):
    x0,y0,x1,y1=b; w=x1-x0; h=y1-y0
    pts=[(.3,.05),(.42,.15),(.58,.15),(.7,.05),(1,.3),(.85,.5),(.75,.42),(.75,.98),(.25,.98),(.25,.42),(.15,.5),(0,.3)]
    c.poly([(x0+w*a,y0+h*b_) for a,b_ in pts],BLUE,BR,4)
def house(c,b):
    x0,y0,x1,y1=b; w=x1-x0; h=y1-y0
    c.rr((x0+w*.12,y0+h*.4,x0+w*.88,y1),8,(255,236,200),BR,4)
    c.poly([(x0,y0+h*.45),(x0+w*.5,y0+h*.02),(x1,y0+h*.45)],(235,120,110),BR,4)
    c.rr((x0+w*.4,y0+h*.62,x0+w*.6,y1),6,GOLD,BR,3)
def bus(c,b):
    x0,y0,x1,y1=b; w=x1-x0; h=y1-y0
    c.rr((x0,y0+h*.1,x1,y0+h*.82),16,YEL2,BR,4)
    for i in range(3): c.rr((x0+w*(.1+.28*i),y0+h*.22,x0+w*(.32+.28*i),y0+h*.5),5,BLU,BR,3)
    c.ell((x0+w*.16,y0+h*.68,x0+w*.36,y0+h*.98),(90,90,90),BR,3); c.ell((x0+w*.64,y0+h*.68,x0+w*.84,y0+h*.98),(90,90,90),BR,3)
def book(c,b):
    x0,y0,x1,y1=b; w=x1-x0; h=y1-y0
    c.poly([(x0,y0+h*.15),(x0+w*.5,y0+h*.3),(x0+w*.5,y1),(x0,y0+h*.85)],(240,150,140),BR,4)
    c.poly([(x1,y0+h*.15),(x0+w*.5,y0+h*.3),(x0+w*.5,y1),(x1,y0+h*.85)],(250,190,170),BR,4)
    for k in (.45,.6): c.line([(x0+w*.1,y0+h*k),(x0+w*.4,y0+h*(k+.1))],(255,255,255),4); c.line([(x0+w*.9,y0+h*k),(x0+w*.6,y0+h*(k+.1))],(255,255,255),4)
def ticket(c,b):
    x0,y0,x1,y1=b; w=x1-x0; h=y1-y0
    c.rr((x0,y0+h*.2,x1,y0+h*.85),14,(255,190,200),BR,4)
    c.ell((x0-8,y0+h*.43,x0+10,y0+h*.62),BG,BR,3); c.ell((x1-10,y0+h*.43,x1+8,y0+h*.62),BG,BR,3)
    c.star("",x0+w*.5,y0+h*.52,h*.22,YEL2,reg=False)
def bars(c,b,color=BLUE):
    x0,y0,x1,y1=b; w=x1-x0; h=y1-y0
    c.rr((x0+w*.05,y0+h*.55,x0+w*.3,y1),6,(190,215,240),BR,4)
    c.rr((x0+w*.7,y0+h*.15,x0+w*.95,y1),6,color,BR,4)
    c.line([(x0+w*.36,y0+h*.5),(x0+w*.62,y0+h*.3)],PINK,6); c.poly([(x0+w*.66,y0+h*.27),(x0+w*.55,y0+h*.26),(x0+w*.6,y0+h*.4)],PINK,None)
def coffee(c,b):
    x0,y0,x1,y1=b; w=x1-x0; h=y1-y0
    c.d.arc([(x0+w*.62)*S,(y0+h*.42)*S,(x0+w*1.0)*S,(y0+h*.78)*S],270,90,fill=BR,width=6*S)
    c.poly([(x0+w*.08,y0+h*.3),(x0+w*.72,y0+h*.3),(x0+w*.62,y1),(x0+w*.18,y1)],(255,255,255),BR,4)
    c.poly([(x0+w*.09,y0+h*.3),(x0+w*.71,y0+h*.3),(x0+w*.68,y0+h*.5),(x0+w*.12,y0+h*.5)],(170,110,70),None)
    for xx in (.28,.5): c.line([(x0+w*xx,y0+h*.02),(x0+w*(xx+.06),y0+h*.12),(x0+w*xx,y0+h*.22)],(190,170,150),4)
def calendar(c,b,star=True,rows=2):
    x0,y0,x1,y1=b; w=x1-x0; h=y1-y0
    c.rr((x0,y0+h*.08,x1,y1),16,WHITE,BR,4); c.rr((x0,y0+h*.08,x1,y0+h*.3),16,(240,110,110),BR,4)
    c.line([(x0+w*.28,y0),(x0+w*.28,y0+h*.16)],BR,6); c.line([(x0+w*.72,y0),(x0+w*.72,y0+h*.16)],BR,6)
    for r in range(rows):
        for q in range(4):
            c.rr((x0+w*(.1+.22*q),y0+h*(.4+.28*r),x0+w*(.26+.22*q),y0+h*(.56+.28*r)),3,(235,225,210),None,0)
    if star: c.star("",x0+w*.68,y0+h*.68,min(w,h)*.17,YEL2,reg=False)
def flag_tw(c,b):
    x0,y0,x1,y1=b; w=x1-x0; h=y1-y0
    c.rr((x0,y0,x1,y1),8,(230,70,70),BR,4); c.rr((x0,y0,x0+w*.5,y0+h*.5),4,(60,90,190),BR,3)
    c.ell((x0+w*.15,y0+h*.1,x0+w*.35,y0+h*.4),WHITE,None,0)
def flag_us(c,b):
    x0,y0,x1,y1=b; w=x1-x0; h=y1-y0
    c.rr((x0,y0,x1,y1),8,WHITE,BR,4)
    for i in range(0,6,2): c.rr((x0+3,y0+h*i/6+3,x1-3,y0+h*(i+1)/6+2),0,(230,70,70),None,0)
    c.rr((x0,y0,x0+w*.45,y0+h*.52),4,(60,90,190),BR,3)
    for r in range(2):
        for q in range(3): c.ell((x0+w*(.08+.12*q),y0+h*(.1+.17*r),x0+w*(.14+.12*q),y0+h*(.17+.17*r)),WHITE,None,0)
def arrow_up(c,b,fill=RED):
    x0,y0,x1,y1=b; w=x1-x0; h=y1-y0
    c.ell(b,(255,236,230),BR,4)
    c.poly([(x0+w*.5,y0+h*.2),(x0+w*.78,y0+h*.52),(x0+w*.6,y0+h*.52),(x0+w*.6,y0+h*.8),(x0+w*.4,y0+h*.8),(x0+w*.4,y0+h*.52),(x0+w*.22,y0+h*.52)],fill,BR,3)
def arrow_right(c,b,fill=O_CORAL):
    x0,y0,x1,y1=b; w=x1-x0; h=y1-y0
    c.poly([(x0,y0+h*.3),(x0+w*.55,y0+h*.3),(x0+w*.55,y0),(x1,y0+h*.5),(x0+w*.55,y1),(x0+w*.55,y0+h*.7),(x0,y0+h*.7)],fill,BR,4)
def arrow_down(c,b,fill=O_CORAL):
    x0,y0,x1,y1=b; w=x1-x0; h=y1-y0
    c.poly([(x0+w*.3,y0),(x0+w*.7,y0),(x0+w*.7,y0+h*.5),(x1,y0+h*.5),(x0+w*.5,y1),(x0,y0+h*.5),(x0+w*.3,y0+h*.5)],fill,BR,4)
def heat(c,b):
    x0,y0,x1,y1=b; w=x1-x0; h=y1-y0
    cols=[[(240,120,110),(250,190,150),(160,210,150)],[(250,190,150),(240,120,110),(255,230,150)],[(160,210,150),(255,230,150),(240,120,110)]]
    for r in range(3):
        for q in range(3): c.rr((x0+w*q/3+2,y0+h*r/3+2,x0+w*(q+1)/3-2,y0+h*(r+1)/3-2),6,cols[r][q],BR,3)
def flow(c,b):
    x0,y0,x1,y1=b; w=x1-x0; h=y1-y0
    c.rr((x0,y0+h*.1,x0+w*.4,y0+h*.45),8,(190,215,240),BR,3); c.rr((x0+w*.6,y0+h*.1,x1,y0+h*.45),8,(250,190,170),BR,3)
    c.rr((x0+w*.3,y0+h*.6,x0+w*.7,y1),8,(200,230,190),BR,3)
    c.line([(x0+w*.4,y0+h*.28),(x0+w*.6,y0+h*.28)],BR,4); c.line([(x0+w*.5,y0+h*.45),(x0+w*.5,y0+h*.6)],BR,4)
def seesaw(c,b):
    """b 外框；左低右高；左端坐箭頭圖示"""
    x0,y0,x1,y1=b; w=x1-x0; h=y1-y0
    # fulcrum
    c.poly([(x0+w*.5,y0+h*.55),(x0+w*.4,y1),(x0+w*.6,y1)],(240,200,120),BR,5)
    # plank (tilted: left low)
    import math
    L=(x0+w*.04,y0+h*.78); R=(x1-w*.04,y0+h*.2); t=16
    dx,dy=R[0]-L[0],R[1]-L[1]; n=math.hypot(dx,dy); nx,ny=-dy/n*t,dx/n*t
    c.poly([(L[0]+nx,L[1]+ny),(R[0]+nx,R[1]+ny),(R[0]-nx,R[1]-ny),(L[0]-nx,L[1]-ny)],(230,160,90),BR,5)
    arrow_up(c,(x0+w*.04+14,y0+h*.78-110,x0+w*.04+114,y0+h*.78-10))
    arrow_up(c,(x1-w*.04-114,y0+h*.2-126,x1-w*.04-14,y0+h*.2-26),(70,130,210))
def tag_x(c,b):
    pass
