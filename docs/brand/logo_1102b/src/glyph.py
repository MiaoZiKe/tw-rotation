from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.boundsPen import BoundsPen
def load(w=900): return TTFont(f'/home/user/tw-rotation/docs/brand/logo_1102b/fonts/noto-sans-tc-chinese-traditional-{w}-normal.woff2')
def contours(font,ch):
    gs=font.getGlyphSet(); name=font.getBestCmap()[ord(ch)]
    rec=RecordingPen(); gs[name].draw(rec)
    cs=[];cur=[]
    for op,args in rec.value:
        cur.append((op,args))
        if op in('closePath','endPath'): cs.append(cur);cur=[]
    out=[]
    for c in cs:
        r=RecordingPen()
        for op,a in c: getattr(r,op)(*a)
        b=BoundsPen(None); r.replay(b); out.append((c,b.bounds))
    return out
def path(c,tx=0,ty=0,s=1.0,flip_h=1000):
    # font y-up -> svg y-down; origin (tx,ty) is svg position of glyph (0,0 baseline) 
    p=SVGPathPen(None)
    t=TransformPen(p,(s,0,0,-s,tx,ty))
    r=RecordingPen(); 
    for op,a in c: getattr(r,op)(*a)
    r.replay(t); return p.getCommands()
if __name__=='__main__':
    f=load()
    for ch in '哩股':
        print(ch,[tuple(round(x) for x in b) for c,b in contours(f,ch)])
