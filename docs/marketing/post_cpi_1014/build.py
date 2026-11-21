import sys, json, time
from lib import *
import icons as I
STK=HERE+"stk/s%d.png"
def num(c,name,cx,cy,r,n,fill=O_CORAL,parent=None):
    c.ell((cx-r,cy-r,cx+r,cy+r),fill,BR,4); c.reg(name,(cx-r,cy-r,cx+r,cy+r),parent)
    f=font(r*1.2); tw=f.getlength(str(n))/S
    c.d.text(((cx-tw/2)*S,(cy-r*0.72)*S),str(n),font=f,fill=WHITE)
def bub_side(c,name,bibi,text,sz,side,maxw,cy,tail=40,gap=13,parent=None,xlim=None):
    w,h=bsize(c,text,sz,maxw)
    if side=="right":   # 泡泡在比比右側
        x0=bibi[2]+gap+tail; box=(x0,cy-h/2,x0+w,cy+h/2); tip=(bibi[2]+gap,cy+12)
        return c.bubble(name,box,("left",cy,tip[0],tip[1]),text,sz,parent)
    else:
        x1=bibi[0]-gap-tail; box=(x1-w,cy-h/2,x1,cy+h/2); tip=(bibi[0]-gap,cy+12)
        return c.bubble(name,box,("right",cy,tip[0],tip[1]),text,sz,parent)
def header(c,n,title,segs=None):
    c.pagenum(n); c.title(title,segs=segs)
def s1():
    c=C(1); c.pagenum(1)
    c.pill("標籤",(48,48,300,108),ROSE,O_CORAL,"財經小教室",38)
    c.text("標題1",48,125,900,"CPI 是什麼？",140,segs=[("CPI",PINK),(" 是什麼？",BR)],stroke=3)
    c.text("標題2",48,300,984,"為什麼大家都在等它？",82,stroke=2.5)
    c.rr((48,425,1032,505),40,YEL,O_YEL,5); c.reg("副標條",(48,425,1032,505),None,"card")
    c.text("副標",60,438,960,"一個數字，牽動升息、降息和股市",44,align="center",parent="副標條")
    b=c.sticker("比比",STK%1,cx=540,y=700,h=520)
    for nm,txt,sx,bp in [("泡泡左","物價漲了嗎？",48,None),("泡泡右","看 CPI 就知道！",None,None)]:
        w,h=bsize(c,txt,44,520); y1=700-13-38; box=None
        if nm=="泡泡左": x0=60; box=(x0,y1-h,x0+w,y1); bp_=min(x0+w-60,b[0]+120)
        else: x1=1020; box=(x1-w,y1-h,x1,y1); bp_=max(x1-w+70,b[2]-120)
        c.bubble(nm,box,("down",bp_,bp_,700-13),txt,44)
    c.star("星1",95,840,34); c.star("星2",990,880,28)
    c.text("往右滑",800,1262,160,"往右滑",38,BR,align="right")
    I.arrow_right(c,(970,1266,1032,1308)); c.reg("往右滑箭頭",(970,1266,1032,1308))
    return c
def s2():
    c=C(2); header(c,2,"CPI 是什麼？")
    c.card("定義卡",(48,150,1032,470),PEACH,O_CORAL)
    c.text("定義1",68,185,944,"消費者物價指數",72,align="center",parent="定義卡",stroke=2)
    c.text("定義2",68,285,944,"（Consumer Price Index）",42,align="center",parent="定義卡")
    c.text("定義3",68,370,944,"追蹤一籃子日常消費品的價格變化",44,align="center",parent="定義卡")
    items=[("食",I.bowl,GRN,O_GRN),("衣",I.shirt,BLU,O_BLUE),("住",I.house,PEACH,O_CORAL),("行",I.bus,YEL,O_YEL),("育",I.book,ROSE,O_PINK),("樂",I.ticket,LIL,O_LIL)]
    for i,(ch,fn,fl,ol) in enumerate(items):
        x=48+(i%3)*336; y=500+(i//3)*214; nm=f"格{ch}"
        c.card(nm,(x,y,x+312,y+190),fl,ol)
        ib=(x+312/2-45,y+18,x+312/2+45,y+108); fn(c,ib); c.reg(f"圖示{ch}",ib,nm)
        c.text(f"字{ch}",x+16,y+118,280,ch,50,align="center",parent=nm,stroke=1.5)
    c.rr((48,925,1032,1000),40,YEL,O_YEL,5); c.reg("黃條",(48,925,1032,1000),None,"card")
    c.text("黃條字",60,936,960,"物價漲得快不快，用它來量",44,align="center",parent="黃條")
    b=c.sticker("比比",STK%2,x=48,y=1025,h=290)
    bub_side(c,"泡泡",b,"你今天花了哪一格？",44,"right",560,1170)
    return c
def s3():
    c=C(3); header(c,3,"數字怎麼看？")
    for k,(x,fl,ol,hd,tx,col) in enumerate([(48,BLU,O_BLUE,"年增率（YoY）","跟去年同一個月比",I.BLUE),(552,GRN,O_GRN,"月增率（MoM）","跟上個月比",I.GREEN)]):
        nm=f"卡{k}"; c.card(nm,(x,150,x+480,560),fl,ol)
        c.text(f"卡{k}標",x+20,176,440,hd,48,align="center",parent=nm,stroke=1.5)
        c.text(f"卡{k}文",x+20,252,440,tx,42,align="center",parent=nm)
        ib=(x+150,340,x+330,530); I.bars(c,ib,col); c.reg(f"卡{k}圖",ib,nm)
    c.card("舉例框",(48,590,1032,900),YEL,O_YEL)
    c.text("舉例標",80,612,500,"簡單舉例",50,parent="舉例框",stroke=1.5)
    for k,t in enumerate(["去年一杯咖啡 50 元","今年變 52 元","年增率就是 4%"]):
        c.text(f"舉例{k}",80,696+k*62,640,t,46,parent="舉例框",color=BR if k<2 else PINK,stroke=1.2)
    cb=(790,640,950,860); I.coffee(c,cb); c.reg("咖啡圖",cb,"舉例框")
    c.text("免責例",48,922,700,"例子僅供說明，不是實際數據",32,color=(120,90,70))
    b=c.sticker("比比",STK%3,x=1032-370,y=1010,w=370)
    bub_side(c,"泡泡",b,"50 變 52，\n就是 4% 喔！",44,"left",560,(b[1]+b[3])/2)
    return c
def s4():
    c=C(4); header(c,4,"整體 CPI vs 核心 CPI")
    for k,(x,fl,ol,hd,tx,cross) in enumerate([(48,BLU,O_BLUE,"整體 CPI","全部項目都算",False),(552,PEACH,O_CORAL,"核心 CPI","扣掉價格大起大落\n的項目",True)]):
        nm=f"卡{k}"; c.card(nm,(x,150,x+480,540),fl,ol)
        c.text(f"卡{k}標",x+20,172,440,hd,54,align="center",parent=nm,stroke=1.8)
        c.text(f"卡{k}文",x+25,250,430,tx,42,align="center",parent=nm)
        ib=(x+115,370,x+365,520); I.basket(c,ib,cross); c.reg(f"卡{k}圖",ib,nm)
    rows=[("台灣：常見核心 CPI 扣掉蔬果和能源",GRN,O_GRN),("美國：核心 CPI 扣掉食品和能源",YEL,O_YEL),("為什麼扣？因為它們波動大，容易誤判趨勢",ROSE,O_PINK)]
    for k,(t,fl,ol) in enumerate(rows):
        y=570+k*125; nm=f"列{k}"; c.card(nm,(48,y,1032,y+105),fl,ol,r=40)
        c.text(f"列{k}字",68,y+30,944,t,42,align="center",parent=nm)
    b=c.sticker("比比",STK%4,x=1032-400,y=990,w=400)
    bub_side(c,"泡泡",b,"波動大的先扣掉，\n看趨勢更準！",44,"left",540,(b[1]+b[3])/2)
    return c
def s5():
    c=C(5); header(c,5,"誰公布？什麼時候？")
    for k,(x,fl,ol,fn,nm_,org,desc) in enumerate([(48,GRN,O_GRN,I.flag_tw,"台灣","行政院主計總處","通常每月上旬\n公布上個月數字"),(552,BLU,O_BLUE,I.flag_us,"美國","勞工統計局（BLS）","通常每月中旬前後公布")]):
        n=f"卡{k}"; c.card(n,(x,150,x+480,590),fl,ol)
        fb=(x+60,178,x+60+120,178+80); fn(c,fb); c.reg(f"旗{k}",fb,n)
        c.text(f"國{k}",x+200,184,260,nm_,60,parent=n,stroke=2)
        c.text(f"機構{k}",x+20,290,440,org,46,align="center",parent=n,stroke=1.2)
        c.text(f"說明{k}",x+25,370,430,desc,42,align="center",parent=n)
        c.pill(f"旬{k}",(x+120,500,x+360,572),YEL if k==0 else PEACH,O_YEL if k==0 else O_CORAL,"上旬" if k==0 else "中旬前後",44,parent=n)
    cb=(430,625,650,795); I.calendar(c,cb); c.reg("月曆",cb,None)
    c.star("星a",310,710,30); c.star("星b",770,690,26)
    c.rr((48,830,1032,910),40,YEL,O_YEL,5); c.reg("黃條",(48,830,1032,910),None,"card")
    c.text("黃條字",60,843,960,"實際日期以官方公布為準",44,align="center",parent="黃條")
    b=c.sticker("比比",STK%5,x=48,y=945,h=370)
    bub_side(c,"泡泡",b,"別錯過公布日！",46,"right",560,1150)
    return c
def s6():
    c=C(6); header(c,6,"CPI 為什麼牽動利率？")
    c.card("左標",(48,150,508,300),ROSE,O_PINK); c.text("左標字",68,205,420,"物價漲太快",50,align="center",parent="左標",stroke=1.5)
    c.card("右標",(572,150,1032,300),BLU,O_BLUE); c.text("右標字",592,170,420,"央行可能升息\n或延後降息",42,align="center",parent="右標")
    sb=(48,330,1032,750); I.seesaw(c,sb); c.reg("蹺蹺板",sb)
    for k,(x,fl,ol,hd,tx) in enumerate([(48,GRN,O_GRN,"通膨降溫","降息空間變大"),(552,PEACH,O_CORAL,"通膨偏高","利率可能維持高檔")]):
        n=f"卡{k}"; c.card(n,(x,780,x+480,990),fl,ol)
        c.text(f"卡{k}標",x+20,805,440,hd,52,align="center",parent=n,stroke=1.5)
        c.text(f"卡{k}文",x+20,895,440,tx,42,align="center",parent=n)
        ab=(x+215,865,x+265,890); 
    c.text("註",48,1012,900,"許多央行以 2% 左右為目標",34,color=(120,90,70))
    b=c.sticker("比比",STK%6,x=48,y=1085,h=225)
    bub_side(c,"泡泡",b,"物價一翹，\n利率跟著變！",44,"right",440,1190)
    return c
def s7():
    c=C(7); header(c,7,"CPI 和股市有什麼關係？")
    xs=[48,396,744]; txt=["CPI 公布","改變利率預期","股市跟著波動"]; fl=[BLU,PEACH,GRN]; ol=[O_BLUE,O_CORAL,O_GRN]
    for k in range(3):
        n=f"流程{k}"; c.card(n,(xs[k],150,xs[k]+288,300),fl[k],ol[k])
        c.text(f"流程{k}字",xs[k]+8,195,272,txt[k],42,align="center",parent=n,stroke=1.2)
    for k in range(2):
        ab=(xs[k]+288+8,200,xs[k]+288+48,250); I.arrow_right(c,ab); c.reg(f"箭頭{k}",ab)
    for k,(x,fl_,ol_,hd,tx,up) in enumerate([(48,ROSE,O_PINK,"高於預期","升息預期升高，\n成長股、科技股\n常承壓",True),(552,GRN,O_GRN,"低於預期","降息預期升溫，\n市場情緒\n常偏樂觀",False)]):
        n=f"卡{k}"; c.card(n,(x,330,x+480,780),fl_,ol_)
        c.text(f"卡{k}標",x+20,352,440,hd,54,align="center",parent=n,stroke=1.8)
        c.text(f"卡{k}文",x+25,445,430,tx,42,align="center",parent=n)
        ab=(x+190,650,x+290,750)
        if up: I.arrow_up(c,ab)
        else:
            c.ell(ab,(255,236,230),BR,4); I.arrow_down(c,(ab[0]+25,ab[1]+20,ab[2]-25,ab[3]-20),(90,170,100))
        c.reg(f"卡{k}圖",ab,n)
    c.rr((48,810,1032,900),44,YEL,O_YEL,5); c.reg("黃條",(48,810,1032,900),None,"card")
    c.text("黃條字",60,827,960,"重點是「預期 vs 實際」的差距",48,align="center",parent="黃條",stroke=1.5)
    b=c.sticker("比比",STK%7,x=48,y=980,h=290)
    bub_side(c,"泡泡",b,"重點是預期差距，\n不是數字本身。",44,"right",520,1100)
    c.text("註",560,1280,472,"市場反應不一定單向",34,color=(120,90,70),align="right")
    return c
def s8():
    c=C(8); header(c,8,"哩股哩股怎麼看 CPI？")
    c.card("月曆卡",(48,150,1032,650),WHITE,O_BLUE)
    c.pill("月曆標",(70,170,330,236),BLU,O_BLUE,"財經日曆",44,parent="月曆卡")
    wd="日一二三四五六"; cw=920/7
    for i,ch in enumerate(wd):
        c.text(f"週{i}",80+i*cw,262,cw,ch,32,align="center",parent="月曆卡",color=(120,90,70))
    tags={(0,2):("CPI",PINK,WHITE),(1,4):("FOMC",O_BLUE,WHITE),(2,1):("非農",O_GRN,WHITE),(2,5):("CPI",PINK,WHITE),(3,3):("FOMC",O_BLUE,WHITE)}
    for r in range(4):
        for q in range(7):
            x=80+q*cw+4; y=312+r*84; n=f"格{r}{q}"
            c.card(n,(x,y,x+cw-8,y+76),(250,243,232),(225,210,190),parent="月曆卡",r=14,w=3)
            if (r,q) in tags:
                t,col,tc=tags[(r,q)]; tw=font(30).getlength(t)/S
                c.pill(f"標{r}{q}",(x+8,y+16,x+cw-16,y+60),col,BR,t,30,parent=n,color=tc)
    for k,(x,fl,ol,fn,tx,nn) in enumerate([(48,GRN,O_GRN,I.calendar,"看日期",1),(392,BLU,O_BLUE,I.flow,"看資金流向",2),(736,ROSE,O_PINK,I.heat,"看熱力圖",3)]):
        n=f"步驟{k}"; c.card(n,(x,685,x+296,905),fl,ol)
        ib=(x+98,705,x+198,795)
        if k==0: I.calendar(c,ib,True,2)
        else: fn(c,ib)
        c.reg(f"步驟圖{k}",ib,n)
        num(c,f"步驟號{k}",x+44,845,26,nn,O_CORAL,n)
        c.text(f"步驟字{k}",x+84,825,200,tx,38,parent=n)
    c.rr((48,935,1032,1015),40,YEL,O_YEL,5); c.reg("黃條",(48,935,1032,1015),None,"card")
    c.text("黃條字",60,948,960,"重要數據日，先在財經日曆標起來",44,align="center",parent="黃條")
    b=c.sticker("比比",STK%8,x=1032-360,y=1030,w=360)
    bub_side(c,"泡泡",b,"重要日子\n我幫你標好了！",44,"left",540,(b[1]+b[3])/2-10)
    return c
def s9():
    c=C(9); header(c,9,"3 句話記住 CPI")
    for k,(t,fl,ol) in enumerate([("CPI 量的是物價漲得快不快",BLU,O_BLUE),("核心 CPI 看趨勢，整體 CPI 看全貌",GRN,O_GRN),("市場在意的是「有沒有超出預期」",PEACH,O_CORAL)]):
        y=150+k*245; n=f"卡{k}"; c.card(n,(48,y,1032,y+220),fl,ol)
        num(c,f"號{k}",140,y+110,56,k+1,ol,n)
        c.text(f"卡{k}字",225,y+50,780,t,46,parent=n,stroke=1.2)
    c.rr((48,905,610,1015),55,PINK,BR,5); c.reg("按鈕",(48,905,610,1015),None,"card")
    c.text("按鈕字",60,935,538,"搜尋「哩股哩股」",48,color=WHITE,align="center",parent="按鈕",stroke=1.5)
    b=c.sticker("比比",STK%9,x=1032-340,y=880,w=340)
    bub_side(c,"泡泡",b,"記住這 3 句，\n下次看 CPI 就不慌！",44,"left",540,1130)
    c.text("免責",48,1268,984,"本內容為公開資料整理，不構成任何投資建議；投資有風險，請自行判斷。",26,color=(110,80,60))
    return c
if __name__=="__main__":
    t0=time.time(); lay={}
    sel=[int(a) for a in sys.argv[1:]] or range(1,10)
    import os; os.makedirs(HERE+"final",exist_ok=True)
    for i in sel:
        t=time.time(); c=globals()[f"s{i}"](); c.save(HERE+f"final/slide_{i:02d}.png")
        lay[i]=dict(els=c.els,tails=getattr(c,"tails",[])); print(i,round(time.time()-t,1),"s")
    json.dump(lay,open(HERE+"final/layout.json","w"),ensure_ascii=False)
