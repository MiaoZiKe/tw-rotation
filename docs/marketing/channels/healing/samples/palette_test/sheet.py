import json,colorsys
from PIL import Image,ImageDraw,ImageFont
P=json.load(open('palettes.json',encoding='utf-8'))
def rgb(h): h=h.lstrip('#'); return tuple(int(h[i:i+2],16)/255 for i in (0,2,4))
def lum(c):
    f=lambda v: v/12.92 if v<=0.03928 else ((v+0.055)/1.055)**2.4
    r,g,b=map(f,c); return 0.2126*r+0.7152*g+0.0722*b
def cr(a,b):
    la,lb=sorted([lum(rgb(a)),lum(rgb(b))],reverse=True); return (la+0.05)/(lb+0.05)
rows=[]
for p in P:
    h,l,s=colorsys.rgb_to_hls(*rgb(p['bg']))
    rows.append(dict(id=p['id'],name=p['name'],bg=p['bg'],L=round(lum(rgb(p['bg']))*100,1),S=round(s*100),H=round(h*360),
        text=round(cr(p['text'],p['bg']),1),sub=round(cr(p['sub'],p['bg']),1),hint=round(cr(p['hint'],p['bg']),1),lamp=round(cr(p['lamp'],p['bg']),1)))
json.dump(rows,open('metrics.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
for r in rows: print(r)
F=ImageFont.truetype('/root/.fonts/NotoSansCJKtc-Regular.otf',30)
W,H=360,450; pad=20; top=70
pages=['post1','post2','post3']
sheet=Image.new('RGB',(pad+len(P)*(W+pad),top+len(pages)*(H+pad)+pad),(128,128,128))
d=ImageDraw.Draw(sheet)
for i,p in enumerate(P):
    x=pad+i*(W+pad); d.text((x,20),p['name'],fill=(255,255,255),font=F)
    for j,po in enumerate(pages):
        im=Image.open(f"{po}_{p['id']}.png").resize((W,H),Image.LANCZOS)
        sheet.paste(im,(x,top+j*(H+pad)))
sheet.save('palette_sheet.png')
# thumbnail sheet (IG grid size ~ 1/3 phone width)
T=Image.new('RGB',(pad+len(P)*(160+pad),60+200+pad),(250,250,250));dt=ImageDraw.Draw(T);F2=ImageFont.truetype('/root/.fonts/NotoSansCJKtc-Regular.otf',22)
for i,p in enumerate(P):
    x=pad+i*(160+pad); dt.text((x,15),p['name'][:4],fill=(40,40,40),font=F2)
    T.paste(Image.open(f"post2_{p['id']}.png").resize((160,200),Image.LANCZOS),(x,60))
T.save('palette_thumb.png')
