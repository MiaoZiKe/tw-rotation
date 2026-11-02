"""四個候選的符號。全部用座標格＋shapely 做一致圓角，不是描圖、不是手抖。
每個 mark(p) 回傳 [(shapely geom 或 ('svgpath',d,bbox), fill), ...]；
render(parts, size) 會自動置中並縮到指定大小，輸出 SVG 內容（viewBox 0 0 100 100）。"""
import sys, math
sys.path.insert(0,'/home/user/tw-rotation/docs/brand/logo_1102b/src')
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union
from shapely import affinity
import glyph
WEIGHT=500
Q=48  # 圓弧解析度（每 1/4 圓段數）
WEIGHT=500

def rnd(g, r_out=3.0, r_in=None):
    """凸角圓角 r_out、凹角圓角 r_in。"""
    r_in = r_out if r_in is None else r_in
    g = g.buffer(-r_out, quad_segs=Q).buffer(r_out, quad_segs=Q)
    if r_in: g = g.buffer(r_in, quad_segs=Q).buffer(-r_in, quad_segs=Q)
    return g
def d_of(g):
    polys = [g] if g.geom_type=='Polygon' else list(g.geoms)
    out=''
    for pg in polys:
        for ring in [pg.exterior,*pg.interiors]:
            c=list(ring.coords)
            out+='M'+' L'.join(f'{x:.2f},{y:.2f}' for x,y in c[:-1])+'Z'
    return out

def mark_A(p):
    """Li：粗 L 的腳往右上揚成楔形（上升），上方一顆圓點＝i 的點＝資金落點。哩 → li。"""
    L = Polygon([(0,0),(17,0),(17,40),(50,22),(50,56),(0,56)])
    L = rnd(L, 3.2, 2.0)
    dot = Point(38.5,3).buffer(8.8, quad_segs=Q)
    return [(L,p['main']),(dot,p['accent'])]
def mark_B(p):
    """資金輪動：圓餅四等分，右上一塊被抽離（資金流進的族群）。空隙一律 3.4。"""
    R=30; g=3.4/2; parts=[]
    def sector(q, dx, dy, fill):
        a0=q*90; pts=[(0,0)]+[(R*math.cos(math.radians(a0+t*90/Q)), -R*math.sin(math.radians(a0+t*90/Q))) for t in range(Q+1)]
        s=Polygon(pts); s=rnd(s,2.6,0)
        return (affinity.translate(s,dx,dy),fill)
    parts.append(sector(1,-g,-g,p['c1'])); parts.append(sector(2,-g,g,p['c2'])); parts.append(sector(3,g,g,p['c3']))
    parts.append(sector(0,g+7.5,-g-7.5,p['accent']))
    return parts
def mark_C(p):
    """K 棒上升：三根圓角棒由矮到高，最高那根紅（漲）帶上影線。棒寬 15、間距 9、全圓角。"""
    W=18; G=8; hs=[30,46,64]; cols=[p['c1'],p['c2'],p['accent']]; out=[]
    for i,(h,c) in enumerate(zip(hs,cols)):
        x=i*(W+G); out.append((box(x,62-h,x+W,62).buffer(0), c))
    # 圓角棒（膠囊）
    out=[(rnd(g,W/2-0.05,0),c) for g,c in out]
    x=2*(W+G)+W/2
    out.append((rnd(box(x-1.7,-14,x+1.7,0),1.6,0),p['accent']))
    return out
def mark_D(p):
    """哩：Noto Sans TC Bold（700）原字，口 部首單獨上色。字形原樣，不加粗不變形。"""
    f=glyph.load(WEIGHT); cs=glyph.contours(f,'哩')
    s=0.066
    kou=''; rest=''; bb=[1e9,1e9,-1e9,-1e9]
    for i,(c,b) in enumerate(cs):
        d=glyph.path(c,0,0,s)
        if i in (5,6): kou+=d
        else: rest+=d
        bb=[min(bb[0],b[0]*s),min(bb[1],-b[3]*s),max(bb[2],b[2]*s),max(bb[3],-b[1]*s)]
    return [(('svgpath',rest,tuple(bb)),p['main']),(('svgpath',kou,tuple(bb)),p['accent'])]

MARKS={'A':mark_A,'B':mark_B,'C':mark_C,'D':mark_D}
def bounds(parts):
    xs=[];ys=[]
    for g,_ in parts:
        b=g[2] if isinstance(g,tuple) else g.bounds
        xs+= [b[0],b[2]]; ys+=[b[1],b[3]]
    return min(xs),min(ys),max(xs),max(ys)
def render(parts, fit=62, cx=50, cy=50, scale=None):
    """置中、等比縮放使最長邊 = fit，回傳 SVG 片段。"""
    x0,y0,x1,y1=bounds(parts); w,h=x1-x0,y1-y0
    s = scale or fit/max(w,h)
    tx=cx-(x0+w/2)*s; ty=cy-(y0+h/2)*s
    out=f'<g transform="translate({tx:.3f} {ty:.3f}) scale({s:.5f})">'
    for g,fill in parts:
        d=g[1] if isinstance(g,tuple) else d_of(g)
        out+=f'<path d="{d}" fill="{fill}" fill-rule="nonzero"/>'
    return out+'</g>'
