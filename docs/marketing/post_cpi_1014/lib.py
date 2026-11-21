import json
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
FONT="/tmp/claude-0/-home-user-tw-rotation/3d7a42eb-0e07-50fa-8c50-cf31c62d682f/scratchpad/font/jf-openhuninn-2.1.ttf"
HERE="/home/user/tw-rotation/docs/marketing/post_cpi_1014/"
W,H=1080,1350; S=2
BG=(255,246,232); BR=(75,46,30); PINK=(240,110,130); WHITE=(255,255,255)
PEACH=(255,226,210); YEL=(255,233,160); GRN=(214,236,200); BLU=(214,232,247); LIL=(232,223,247); ROSE=(255,222,226)
O_CORAL=(233,140,115); O_BLUE=(111,163,216); O_GRN=(125,179,107); O_YEL=(230,181,60); O_PINK=(236,120,140); O_LIL=(155,130,210)
_f={}
def font(sz):
    if sz not in _f: _f[sz]=ImageFont.truetype(FONT,int(sz*S))
    return _f[sz]
def inter(a,b):
    return max(0,min(a[2],b[2])-max(a[0],b[0]))>0 and max(0,min(a[3],b[3])-max(a[1],b[1]))>0
class C:
    def __init__(s,n):
        s.n=n; s.im=Image.new("RGBA",(W*S,H*S),BG+(255,)); s.d=ImageDraw.Draw(s.im); s.els=[]
    def reg(s,name,box,parent=None,kind="leaf"):
        s.els.append(dict(name=name,box=[round(v,1) for v in box],parent=parent,kind=kind)); return name
    def rr(s,box,r=34,fill=WHITE,out=BR,w=5):
        s.d.rounded_rectangle([v*S for v in box],radius=r*S,fill=fill,outline=out,width=w*S if out else 0)
    def card(s,name,box,fill,out,parent=None,r=34,w=5):
        s.rr(box,r,fill,out,w); return s.reg(name,box,parent,"card")
    def poly(s,pts,fill,out=BR,w=4):
        s.d.polygon([(x*S,y*S) for x,y in pts],fill=fill)
        if out: s.d.line([(x*S,y*S) for x,y in pts+[pts[0]]],fill=out,width=w*S,joint="curve")
    def ell(s,box,fill,out=BR,w=4):
        s.d.ellipse([v*S for v in box],fill=fill,outline=out,width=w*S if out else 0)
    def line(s,pts,fill=BR,w=4):
        s.d.line([(x*S,y*S) for x,y in pts],fill=fill,width=w*S,joint="curve")
    def lines(s,text,sz,maxw):
        import re
        f=font(sz); out=[]; NOSTART="，。、；：！？）」』…,.;:!?)%"
        for para in text.split("\n"):
            toks=re.findall(r"[A-Za-z0-9%/\.\-]+|.",para)
            def wrap(w):
                ls=[];cur=""
                for tk in toks:
                    if cur and f.getlength(cur+tk)/S>w and tk[0] not in NOSTART:
                        ls.append(cur);cur=tk.lstrip()
                    else: cur+=tk
                ls.append(cur); return ls
            ls=wrap(maxw); n=len(ls)
            if n>1:
                lo,hi=maxw*0.5,maxw
                for _ in range(14):
                    mid=(lo+hi)/2
                    if len(wrap(mid))<=n: hi=mid
                    else: lo=mid
                ls2=wrap(hi)
                if len(ls2)==n and all(len(l)>=2 for l in ls2): ls=ls2
            out+=ls
        return out
    def text(s,name,x,y,w,text,sz,color=BR,align="left",parent=None,gap=1.28,segs=None,stroke=1.0):
        """x,y 為文字區左上；w 為最大寬；回傳 (實際外框)"""
        f=font(sz); ls=s.lines(text,sz,w) if segs is None else [text]
        bx0=bx1=None; yy=y; by0=y
        for ln in ls:
            lw=f.getlength(ln)/S
            xx=x if align=="left" else (x+(w-lw)/2 if align=="center" else x+w-lw)
            if segs is None: s.d.text((xx*S,yy*S),ln,font=f,fill=color,stroke_width=int(stroke*S*0.5),stroke_fill=color)
            else:
                cx=xx
                for t,c in segs:
                    s.d.text((cx*S,yy*S),t,font=f,fill=c,stroke_width=int(stroke*S*0.5),stroke_fill=c); cx+=f.getlength(t)/S
            x0=xx; x1=xx+lw
            bx0=x0 if bx0 is None else min(bx0,x0); bx1=x1 if bx1 is None else max(bx1,x1)
            yy+=sz*gap
        bb=f.getbbox(ls[0]); top=y+bb[1]/S
        box=(bx0,top,bx1,y+(len(ls)-1)*sz*gap+ f.getbbox(ls[-1])[3]/S)
        s.reg(name,box,parent); return box
    def sticker(s,name,path,cx=None,x=None,y=None,h=None,w=None,parent=None):
        im=Image.open(path).convert("RGBA")
        if h: w=im.width*h/im.height
        else: h=im.height*w/im.width
        im=im.resize((int(w*S),int(h*S)),Image.LANCZOS)
        if cx is not None: x=cx-w/2
        s.im.alpha_composite(im,(int(x*S),int(y*S))); s.d=ImageDraw.Draw(s.im)
        box=(x,y,x+w,y+h); s.reg(name,box,parent); return box
    def bubble(s,name,box,tail,text,sz=40,parent=None):
        """box=(x0,y0,x1,y1)；tail=(side,base_pos,tipx,tipy)；side in down/up/left/right；單一封閉路徑"""
        x0,y0,x1,y1=box; side,bp,tx,ty=tail; hw=24
        if side=="down": pts=[(bp-hw,y1-6),(tx,ty),(bp+hw,y1-6)]
        elif side=="up": pts=[(bp-hw,y0+6),(tx,ty),(bp+hw,y0+6)]
        elif side=="left": pts=[(x0+6,bp-hw),(tx,ty),(x0+6,bp+hw)]
        else: pts=[(x1-6,bp-hw),(tx,ty),(x1-6,bp+hw)]
        m=Image.new("L",(W*S,H*S),0); md=ImageDraw.Draw(m)
        md.rounded_rectangle([v*S for v in box],radius=34*S,fill=255); md.polygon([(a*S,b*S) for a,b in pts],fill=255)
        ol=m.filter(ImageFilter.MaxFilter(2*5*S+1))
        s.im.paste(Image.new("RGBA",m.size,BR+(255,)),(0,0),ol)
        s.im.paste(Image.new("RGBA",m.size,WHITE+(255,)),(0,0),m); s.d=ImageDraw.Draw(s.im)
        tb=(min(p[0] for p in pts),min(p[1] for p in pts),max(p[0] for p in pts),max(p[1] for p in pts))
        ub=(min(x0,tb[0]),min(y0,tb[1]),max(x1,tb[2]),max(y1,tb[3]))
        s.reg(name,ub,parent,"bubble")
        pad=26; nl=len(s.lines(text,sz,x1-x0-2*pad)); th=(nl-1)*sz*1.28+sz*0.95
        tb2=s.text(name+"_字",x0+pad,y0+((y1-y0)-th)/2-sz*0.08,x1-x0-2*pad,text,sz,parent=name,align="center")
        # 垂直置中
        s.tails=getattr(s,"tails",[])+[dict(bubble=name,tail=[round(v,1) for v in tb],text=[round(v,1) for v in tb2],body=list(box))]
        return ub
    def pill(s,name,box,fill,out,text,sz,parent=None,color=BR,r=None):
        s.rr(box,r or (box[3]-box[1])/2,fill,out,4); s.reg(name,box,parent,"card")
        tw=font(sz).getlength(text)/S
        s.text(name+"_字",box[0]+(box[2]-box[0]-tw)/2,box[1]+((box[3]-box[1])-sz*1.0)/2-sz*0.12,tw+4,text,sz,color,parent=name)
    def star(s,name,cx,cy,r,fill=(255,214,70),parent=None,reg=True):
        import math
        pts=[]
        for i in range(8):
            a=math.pi/4*i-math.pi/2; rr_=r if i%2==0 else r*0.38; pts.append((cx+rr_*math.cos(a),cy+rr_*math.sin(a)))
        s.poly(pts,fill,BR,3)
        if reg: s.reg(name,(cx-r,cy-r,cx+r,cy+r),parent)
    def pagenum(s,n):
        s.pill("頁碼",(872,44,1032,104),WHITE,O_CORAL,f"{n} / 9",36)
    def title(s,text,sz=68,segs=None,w=800):
        return s.text("標題",48,48,w,text,sz,BR,segs=segs,stroke=2.0)
    def save(s,path):
        im=s.im.resize((W,H),Image.LANCZOS).convert("RGB"); im.save(path); return im

def bsize(c,text,sz,maxw,pad=26):
    """依文字算泡泡尺寸（寬取最長行）"""
    ls=c.lines(text,sz,maxw-2*pad); w=max(font(sz).getlength(l)/S for l in ls)+2*pad+8
    return w,(len(ls)-1)*sz*1.28+sz*0.95+2*pad+6
