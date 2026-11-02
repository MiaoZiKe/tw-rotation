import math, random
from glyph import glyph, text
INK='#1F2A44'; CREAM='#FFF7E8'; ORG='#E8590C'; BLU='#2B6BF3'; PUR='#7B4FE0'; TEA='#0A8CA3'; YEL='#FFC93C'; PNK='#FF8FB1'
def P(d, fill='none', extra=''): return f'<path d="{d}" fill="{fill}" {extra}/>'
def rect(x,y,w,h,f,r=0,extra=''): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{f}" {extra}/>'
def circ(x,y,r,f,extra=''): return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{f}" {extra}/>'
def poly(pts,f,extra=''): return '<polygon points="'+' '.join(f'{x:.1f},{y:.1f}' for x,y in pts)+f'" fill="{f}" {extra}/>'
def line(pts,stroke,w,extra=''): return '<polyline points="'+' '.join(f'{x:.1f},{y:.1f}' for x,y in pts)+f'" fill="none" stroke="{stroke}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round" {extra}/>'
def pth(d,stroke,w,extra=''): return f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round" {extra}/>'

# ---------- F01 負空間：圓內挖出「上升箭頭＝L」 ----------
PAL={}
PAL[1]=dict(bg=CREAM,disc=BLU,dot=ORG,fg=INK,sub=BLU)
def art1(p):
    # 藍圓盤，用 mask 真正挖空（露出米白底），挖空形狀 = 向上箭頭（箭桿）＋向右的腳 = L
    cut = ('M 232 128 L 318 232 L 270 232 L 270 322 L 380 322 L 380 372 L 214 372 L 214 232 L 158 232 Z')
    # 箭頭置中偏左：頭 (158..318, 232)，桿 214..270
    cut = 'M 196 124 L 298 236 L 244 236 L 244 316 L 366 316 L 366 372 L 188 372 L 188 236 L 134 236 Z'
    return (f'<defs><mask id="m1"><rect width="512" height="512" fill="#fff"/>'
            f'<path d="{cut}" fill="#000" stroke="#000" stroke-width="14" stroke-linejoin="round"/></mask></defs>'
            + rect(0,0,512,512,p['bg']) + circ(256,256,196,p['disc'],'mask="url(#m1)"') + circ(352,196,30,p['dot']))
# ---------- F02 摺紙：紙飛機（上升） ----------
PAL[2]=dict(bg=CREAM,l1='#FFB347',l2=ORG,l3='#B83C00',l4=INK,tr=BLU)
def art2(p):
    A=(428,132); B=(100,236); R=(236,288); K=(300,396); T=(214,348)
    o=[rect(0,0,512,512,p['bg'])]
    o.append(pth('M 70 430 C 140 420 170 380 215 372',p['tr'],10,'stroke-dasharray="2 22" opacity=".9"'))
    o.append(poly([A,B,R],p['l1']))
    o.append(poly([A,R,K],p['l2']))
    o.append(poly([R,K,T],p['l3']))
    o.append(poly([B,R,T],p['l4']))
    return ''.join(o)
# ---------- F03 像素 8-bit ----------
PAL[3]=dict(bg='#1F2A44',star='#4C5C8A',c1=('#6BE0F2','#0A8CA3','#066075'),c2=('#FFE27A','#FFC93C','#C98F00'),c3=('#FF9A57','#E8590C','#A33C00'),wh='#FFF7E8')
N3=17; C3=512/N3
def px(c,r,col,w=1,h=1): return f'<rect x="{c*C3:.2f}" y="{r*C3:.2f}" width="{w*C3+0.6:.2f}" height="{h*C3+0.6:.2f}" fill="{col}"/>'
def art3(p):
    o=[rect(0,0,512,512,p['bg'])]
    for c,r in [(2,3),(14,2),(15,9),(1,9),(5,1),(13,6)]: o.append(px(c,r,p['star']))
    bars=[(3,12,p['c1']),(7,10,p['c2']),(11,8,p['c3'])]
    for c0,top,(hi,mid,lo) in bars:
        o.append(px(c0+1,top-2,p['wh']))            # 上影線
        o.append(px(c0+1,top-1,p['wh']))
        o.append(px(c0,top,mid,3,15-top))
        o.append(px(c0,top,hi,3,1)); o.append(px(c0,top,hi,1,15-top))
        o.append(px(c0+2,top+1,lo,1,14-top))
    o.append(px(1,15,p['wh'],15,1))
    # 像素箭頭（左上）
    for k in range(7):
        o.append(px(3+k,8-k,p['wh'])); o.append(px(4+k,8-k,p['wh']))
    o.append(px(6,2,p['wh'],5,1)); o.append(px(6,3,p['wh'],5,1)); o.append(px(9,4,p['wh'],2,2))
    return ''.join(o)
# ---------- F04 等角 3D ----------
PAL[4]=dict(bg=CREAM,top=('#FFD166','#FF8A4C','#7FA6FF'),right=('#E8A800','#E8590C','#2B6BF3'),left=('#FFB62E','#C84600','#1E4FC0'),shadow='#E8D9B8')
def art4(p):
    u=54; cx,cy=188,391; c30=math.cos(math.radians(30)); s30=0.5
    def pr(x,y,z): return (cx+(x-y)*c30*u, cy+(x+y)*s30*u - z*u)
    bars=[(0,0,1.3),(0,-1.45,2.5),(0,-2.9,3.7)]  # (x,y,h)  沿 -y 方向上升
    o=[rect(0,0,512,512,p['bg'])]
    # 地面影
    for i,(x,y,h) in enumerate(bars): pass
    w=1.0;d=1.0
    for i,(x,y,h) in sorted(enumerate(bars),key=lambda t:t[1][0]+t[1][1]):
        T=[pr(x,y,h),pr(x+w,y,h),pr(x+w,y+d,h),pr(x,y+d,h)]
        Rt=[pr(x+w,y,0),pr(x+w,y+d,0),pr(x+w,y+d,h),pr(x+w,y,h)]
        L=[pr(x,y+d,0),pr(x+w,y+d,0),pr(x+w,y+d,h),pr(x,y+d,h)]
        o.append(poly(L,p['left'][i],'stroke-linejoin="round" stroke-width="2" stroke="'+p['left'][i]+'"'))
        o.append(poly(Rt,p['right'][i],'stroke-width="2" stroke="'+p['right'][i]+'"'))
        o.append(poly(T,p['top'][i],'stroke-width="2" stroke="'+p['top'][i]+'"'))
    # 最高柱頂端：浮空小方塊（資金落點）
    x,y,h=bars[2]; z=h+0.55; w2=.5
    T=[pr(x+.25,y+.25,z+w2),pr(x+.25+w2,y+.25,z+w2),pr(x+.25+w2,y+.25+w2,z+w2),pr(x+.25,y+.25+w2,z+w2)]
    Rt=[pr(x+.25+w2,y+.25,z),pr(x+.25+w2,y+.25+w2,z),pr(x+.25+w2,y+.25+w2,z+w2),pr(x+.25+w2,y+.25,z+w2)]
    L=[pr(x+.25,y+.25+w2,z),pr(x+.25+w2,y+.25+w2,z),pr(x+.25+w2,y+.25+w2,z+w2),pr(x+.25,y+.25+w2,z+w2)]
    o+= [poly(L,'#B8A98A'),poly(Rt,'#D8C8A8'),poly(T,INK)]
    return ''.join(o)
# ---------- F05 極光網格漸層 ----------
PAL[5]=dict(bg='#FFE9D2',b=[('#FF8A5B',140,150,170),('#FF5E9C',390,120,150),('#7B4FE0',390,400,190),('#2B6BF3',110,410,170),('#FFC93C',250,250,120)],wh='#FFFFFF')
def art5(p):
    o=['<defs><filter id="bl" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="46"/></filter>'
       '<filter id="sh" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="0" dy="10" stdDeviation="12" flood-color="#4a1a8a" flood-opacity=".28"/></filter></defs>',rect(0,0,512,512,p['bg'])]
    o.append('<g filter="url(#bl)">'+''.join(circ(x,y,r,c,'opacity=".95"') for c,x,y,r in p['b'])+'</g>')
    o.append('<g filter="url(#sh)">'+pth('M 140 318 L 256 206 L 372 318',p['wh'],44)+pth('M 172 392 L 256 312 L 340 392',p['wh'],44,'opacity=".75"')+'</g>')
    return ''.join(o)
# ---------- F06 線稿圖示 ----------
PAL[6]=dict(bg=CREAM,ln=INK,ac=ORG,fill='#FFE3CC')
def art6(p):
    sw=26
    o=[rect(0,0,512,512,p['bg'])]
    bars=[(112,300,78,92),(216,240,78,152),(320,196,78,196)]  # x,y,w,h  底 392
    for x,y,w,h in bars:
        o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="22" fill="{p["fill"]}" stroke="{p["ln"]}" stroke-width="{sw}" stroke-linejoin="round"/>')
    o.append(pth('M 90 424 L 422 424',p['ln'],sw))
    o.append(pth('M 112 232 C 170 200 210 166 262 144 L 352 100',p['ac'],sw))
    o.append(pth('M 292 98 L 360 96 L 366 164',p['ac'],sw))
    return ''.join(o)
# ---------- F07 家紋 ----------
PAL[7]=dict(bg=INK,fg=CREAM,ac=ORG)
def art7(p):
    f=p['fg']; o=[rect(0,0,512,512,p['bg'])]
    o.append(circ(256,256,206,'none',f'stroke="{f}" stroke-width="22"'))
    o.append(circ(256,256,176,'none',f'stroke="{f}" stroke-width="5"'))
    big='M 0 0 C 46 -40 52 -104 0 -150 C -52 -104 -46 -40 0 0 Z'
    sm='M 0 -4 C 22 -30 24 -66 0 -92 C -24 -66 -22 -30 0 -4 Z'
    for k in range(4):
        a=k*90
        o.append(f'<g transform="translate(256 256) rotate({a})"><path d="{big}" fill="{f}"/></g>')
    for k in range(4):
        a=45+k*90
        o.append(f'<g transform="translate(256 256) rotate({a})"><path d="{sm}" fill="{f}" transform="translate(0 -62)"/></g>')
    o.append(circ(256,256,34,p['bg']))
    o.append(circ(256,256,24,p['ac']))
    return ''.join(o)
# ---------- F08 包浩斯 ----------
PAL[8]=dict(bg='#F3EAD3',red='#E8450C',blu='#2B6BF3',yel='#FFC93C',ink='#1F2A44')
def art8(p):
    o=[rect(0,0,512,512,p['bg']),'<g transform="translate(256 262) scale(.86) translate(-256 -262)">']
    o.append(rect(72,262,150,150,p['blu']))                           # 方
    o.append(circ(262,318,94,p['yel']))                               # 圓
    o.append(poly([(394,92),(476,262),(312,262)],p['red']))           # 三角（向上）
    o.append(rect(72,412,404,18,p['ink']))
    o.append('</g>')
    return ''.join(o)
# ---------- F09 塗鴉 ----------
PAL[9]=dict(bg='#FFF1C9',ink=INK,c1=ORG,c2=BLU,c3='#FF8FB1',c4=YEL)
def smooth(pts,closed=False):
    n=len(pts); d=f'M {pts[0][0]:.1f} {pts[0][1]:.1f} '
    for i in range(n-1):
        p0=pts[max(i-1,0)];p1=pts[i];p2=pts[i+1];p3=pts[min(i+2,n-1)]
        c1=(p1[0]+(p2[0]-p0[0])/6,p1[1]+(p2[1]-p0[1])/6); c2=(p2[0]-(p3[0]-p1[0])/6,p2[1]-(p3[1]-p1[1])/6)
        d+=f'C {c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f} '
    return d
def wob(pts,amp=3.5,seed=1,step=26):
    r=random.Random(seed); out=[]
    for i in range(len(pts)-1):
        (x0,y0),(x1,y1)=pts[i],pts[i+1]; L=math.hypot(x1-x0,y1-y0); k=max(1,int(L/step))
        for j in range(k):
            t=j/k; out.append((x0+(x1-x0)*t+r.uniform(-amp,amp),y0+(y1-y0)*t+r.uniform(-amp,amp)))
    out.append((pts[-1][0]+r.uniform(-amp,amp)*.4,pts[-1][1]+r.uniform(-amp,amp)*.4)); return out
def box(x,y,w,h,seed,amp=4): return smooth(wob([(x,y+h),(x+1,y),(x+w,y+1),(x+w+3,y+h),(x-6,y+h+2)],amp,seed,40))
def art9(p):
    ink=p['ink']; o=[rect(0,0,512,512,p['bg'])]
    # 色塊（刻意錯位，像沒對準的彩色筆）
    bars=[(120,300,84,100,p['c2']),(214,236,84,164,p['c1']),(308,170,84,230,p['c4'])]
    for i,(x,y,w,h,c) in enumerate(bars):
        o.append(rect(x+10,y+10,w,h,c,6,'opacity=".92"'))
    for i,(x,y,w,h,c) in enumerate(bars):
        o.append(pth(box(x,y,w,h,i+3),ink,13))
    o.append(pth(smooth(wob([(78,418),(432,414)],3,9,40)),ink,13))
    # 彎曲上升箭頭
    ar=smooth(wob([(88,226),(150,180),(214,150),(290,112),(372,74)],4,5,30))
    o.append(pth(ar,p['c3'],17))
    o.append(pth(smooth(wob([(316,64),(380,66),(384,128)],3,7,30)),p['c3'],17))
    # 閃光
    def spark(x,y,s,c): return pth(f'M {x-s} {y} L {x+s} {y} M {x} {y-s} L {x} {y+s}',c,9)
    o.append(spark(100,118,20,ink)); o.append(spark(430,196,15,p['c2'])); o.append(circ(440,90,9,p['c1']))
    return ''.join(o)
# ---------- F10 剪紙／窗花 ----------
PAL[10]=dict(bg='#C8102E',cr='#FFF1DC')
def art10(p):
    r,c=p['bg'],p['cr']; o=[rect(0,0,512,512,r)]
    o.append(circ(256,256,186,'none',f'stroke="{c}" stroke-width="7"'))
    for k in range(24):
        a=math.radians(k*15); o.append(circ(256+222*math.sin(a),256-222*math.cos(a),8.5,c))
    big='M 0 -92 C 34 -118 38 -158 0 -184 C -38 -158 -34 -118 0 -92 Z'
    sm='M 0 -150 C 12 -164 12 -176 0 -186 C -12 -176 -12 -164 0 -150 Z'
    inner='M 0 -112 C 16 -126 18 -146 0 -162 C -18 -146 -16 -126 0 -112 Z'
    for k in range(8):
        o.append(f'<g transform="translate(256 256) rotate({k*45})"><path d="{big}" fill="{c}"/><path d="{inner}" fill="{r}"/></g>')
        o.append(f'<g transform="translate(256 256) rotate({k*45+22.5})"><path d="{sm}" fill="{c}"/></g>')
    o.append(circ(256,256,84,c))
    o.append(circ(256,256,68,'none',f'stroke="{r}" stroke-width="7"'))
    for k in range(8):
        o.append(f'<g transform="translate(256 256) rotate({k*45})"><circle cx="0" cy="-76" r="0" fill="{r}"/></g>')
    o.append(rect(228,228,56,56,r,6,'transform="rotate(45 256 256)"'))
    o.append(circ(256,256,12,c))
    return ''.join(o)

# ---------- 橫式 ----------
def px_text(s,x,y,cell,col):
    G={'L':["X....","X....","X....","X....","X....","X....","XXXXX"],'I':["XXXXX","..X..","..X..","..X..","..X..","..X..","XXXXX"],
       'G':[".XXX.","X...X","X....","X.XXX","X...X","X...X",".XXX."],'U':["X...X","X...X","X...X","X...X","X...X","X...X",".XXX."]}
    o=''; cx=x
    for ch in s:
        if ch==' ': cx+=3*cell; continue
        for r,row in enumerate(G[ch]):
            for c,v in enumerate(row):
                if v=='X': o+=f'<rect x="{cx+c*cell:.1f}" y="{y+r*cell:.1f}" width="{cell+.5}" height="{cell+.5}" fill="{col}"/>'
        cx+=6*cell
    return o, cx-x-cell
def horiz(art,p,shape='squircle',main_font='sans',main_col=INK,sub_font='inter',sub_col=None,bg='#FFFFFF',main_ls=10,sub_ls=14,sub_text='LIGU LIGU',pixsub=False):
    W,H=1200,400; S=260; x0=118; y0=70
    o=[rect(0,0,W,H,bg)]
    cid='hc'
    clip=(f'<rect x="{x0}" y="{y0}" width="{S}" height="{S}" rx="{S*0.225}"/>' if shape=='squircle' else f'<circle cx="{x0+S/2}" cy="{y0+S/2}" r="{S/2}"/>')
    o.append(f'<defs><clipPath id="{cid}">{clip}</clipPath></defs>')
    o.append(f'<g clip-path="url(#{cid})"><g transform="translate({x0} {y0}) scale({S/512})">{art(p)}</g></g>')
    tx=x0+S+70; size=132
    d,w=text(main_font,'哩股哩股',size,tx,y0+S/2+4,ls=main_ls); o.append(P(d,main_col))
    sc=sub_col or main_col
    if pixsub:
        cell=9; g,sw=px_text(sub_text,tx+4,y0+S/2+46,cell,sc); o.append(g)
    else:
        d2,w2=text(sub_font,sub_text,46,tx+4,y0+S/2+100,ls=sub_ls); o.append(P(d2,sc))
    return W,H,''.join(o)
H1=lambda p:horiz(art1,p,main_col=INK,sub_col=BLU)
H2=lambda p:horiz(art2,p,main_font='sans7',main_col=INK,sub_col=ORG)
H3=lambda p:horiz(art3,p,main_col='#FFF7E8',sub_col='#FFC93C',bg='#1F2A44',pixsub=True)
H4=lambda p:horiz(art4,p,main_col=INK,sub_col=ORG,bg='#FFFDF7')
H5=lambda p:horiz(art5,p,main_font='sans7',main_col='#3A2470',sub_col='#7B4FE0',bg='#FFF7EF')
H6=lambda p:horiz(art6,p,main_font='sans7',main_col=INK,sub_col=ORG)
H7=lambda p:horiz(art7,p,shape='circle',main_font='serif',main_col=CREAM,sub_col=ORG,bg=INK,main_ls=14)
H8=lambda p:horiz(art8,p,main_col=INK,sub_col='#E8450C',bg='#F3EAD3')
H9=lambda p:horiz(art9,p,main_font='wk',main_col=INK,sub_col=ORG,bg='#FFF1C9',main_ls=6)
H10=lambda p:horiz(art10,p,main_font='serif',main_col='#C8102E',sub_col='#C8102E',bg='#FFF1DC',main_ls=14)
DIRS=[
 ('F01','負空間極簡','藍色圓盤中挖出一支向上的箭頭，箭桿加腳就是 L；露出的米白就是圖形，旁邊橘點是上漲的資金。','Noto Sans TC Black、Inter ExtraBold',art1,H1,[1]),
 ('F02','摺紙立體折面','一架摺紙飛機斜斜向上衝，四個折面各自一個明暗，後面拖著虛線航跡＝走勢向上。','Noto Sans TC Bold、Inter ExtraBold',art2,H2,[2]),
 ('F03','像素 8-bit','17×17 像素格的三根階梯 K 棒（有影線、受光面與暗面），左上一支像素箭頭，深藍底有星點。','像素字 LIGU（自繪方格）、Noto Sans TC Black',art3,H3,[3]),
 ('F04','等角 3D 積木','三根等角（Isometric）積木 K 棒沿斜線逐級升高，三面三階明暗；最高柱頂浮一顆小方塊＝資金落點。','Noto Sans TC Black、Inter ExtraBold',art4,H4,[4]),
 ('F05','極光網格漸層','橘、粉、紫、藍、黃五團模糊光暈揉成極光底，上面只放兩個白色上揚箭號（人字形）＝加速上升。','Noto Sans TC Bold、Inter ExtraBold',art5,H5,[5]),
 ('F06','線稿圖示','統一 26px 圓角描邊：三根墨藍輪廓長條圖加一條橘色走勢箭頭，所有轉角與端點同一個圓角。','Noto Sans TC Bold、Inter ExtraBold',art6,H6,[6]),
 ('F07','日式家紋','墨藍底、米白雙環中放八瓣對稱花紋（四大瓣＋四小瓣），圓心一顆橘點；是家紋的對稱幾何，不是印章。','Noto Serif TC Black、Inter ExtraBold',art7,H7,[7]),
 ('F08','包浩斯幾何','藍方塊、黃圓、橘紅三角形由左下往右上堆疊，下方一條黑色基線；圓、方、三角＋原色。','Noto Sans TC Black、Inter ExtraBold',art8,H8,[8]),
 ('F09','手繪塗鴉','歪歪的彩色筆：三根長條圖（色塊故意沒對準）、粉紅彎曲上升箭頭與閃光，線條帶手抖。','霞鶩文楷 LXGW WenKai TC、Inter ExtraBold',art9,H9,[9]),
 ('F10','剪紙窗花','中國紅底、米白鏤空：八大瓣八小瓣加一圈圓點，圓心是方孔錢（錢）；現代版只用乾淨的線與對稱。','Noto Serif TC Black、Inter ExtraBold',art10,H10,[10]),
]
