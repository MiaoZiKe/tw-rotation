import sys, math
sys.path.insert(0,'/home/user/tw-rotation/docs/brand/logo_1102b/src')
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union
from shapely import affinity
from marks import rnd, render, Q
def L_wedge(): return rnd(Polygon([(0,0),(17,0),(17,40),(50,22),(50,56),(0,56)]),3.2,2.0)
def L_plain(w=17,h=56,fl=44,t=15): return rnd(Polygon([(0,0),(w,0),(w,h-t),(fl,h-t),(fl,h),(0,h)]),3.2,2.0)
def sector(cx,cy,R,a0,a1,r=2.6):
    pts=[(cx,cy)]+[(cx+R*math.cos(math.radians(a0+(a1-a0)*t/Q)), cy-R*math.sin(math.radians(a0+(a1-a0)*t/Q))) for t in range(Q+1)]
    return rnd(Polygon(pts),r,0)
def dot(x,y,r=8.8): return Point(x,y).buffer(r,quad_segs=Q)
def pill(x0,y0,x1,y1): return rnd(box(x0,y0,x1,y1),(x1-x0)/2-0.05,0)
def A0(p): return [(L_wedge(),p['main']),(dot(38.5,3),p['acc'])]
def B1(p):  # L 的腳換成被抽離的圓餅四分之一
    return [(rnd(box(0,0,17,56),3.2,0),p['main']),(sector(20.4,56,35,0,90),p['acc'])]
def B2(p):  # 黃點換成圓餅小塊
    return [(L_wedge(),p['main']),(sector(30,14,17,0,90,2.2),p['acc'])]
def B3(p):  # 圓餅缺口形成 L，缺掉的那塊飛出去
    c=Point(0,0).buffer(30,quad_segs=Q*2); cut=box(-11,-40,40,11)
    Lg=rnd(c.difference(cut),2.6,1.5); piece=c.intersection(cut)
    piece=affinity.translate(piece.buffer(-2.2,quad_segs=Q),0,0)
    piece=rnd(piece,2.4,0); piece=affinity.translate(piece,4.5,-4.5)
    return [(Lg,p['main']),(piece,p['acc'])]
def C1(p):  # L 的腳上揚成最高的 K 棒：棒身＋影線頂端＝Li 的 i
    L=L_plain(17,56,36,14)
    bar=pill(41,16,57,56); wick=pill(47.8,0,50.2,16)
    return [(L,p['main']),(bar,p['acc']),(wick,p['acc'])]
def C2(p):  # 豎筆＋兩根漸高的圓角 K 棒（最高的帶影線）
    stem=rnd(box(0,0,17,56),3.2,0)
    b1=pill(23,34,38,56); b2=pill(44,20,59,56); wick=pill(50.3,6,52.7,20)
    return [(stem,p['main']),(b1,p['main']),(b2,p['acc']),(wick,p['acc'])]
def C3(p):  # 黃點變成 K 棒影線頂端（棒立在楔形上）
    L=L_wedge(); wick=pill(41.6,6,45.4,27)
    return [(L,p['main']),(wick,p['acc']),(dot(43.5,3,8.8),p['acc'])]
def D1(p):  # Li Li：兩顆 Li 逐步上升，各自一點
    s=0.66; a=A0(p)
    one=[(affinity.scale(g,s,s,origin=(0,0)),c) for g,c in a]
    two=[(affinity.translate(g,36,-14),c) for g,c in one]
    return one+two
def D2(p):  # 雙 L 旋轉對稱：一個 L 與它轉 180° 的影子互扣（輪動），縫隙一致
    l1=L_plain(15,60,40,15); l2=affinity.rotate(l1,180,origin=(30,30))
    return [(l1,p['main']),(l2,p['acc'])]
VARS=[('A0','A 基準 Li 上揚',A0),('B1','A+B1 圓餅當腳',B1),('B2','A+B2 圓點換圓餅',B2),('B3','A+B3 圓餅缺口成 L',B3),
      ('C1','A+C1 K 棒當 i',C1),('C2','A+C2 漸高 K 棒腳',C2),('C3','A+C3 影線頂端圓點',C3),('D1','雙 Li 上升',D1),('D2','雙 L 旋轉對稱',D2)]
