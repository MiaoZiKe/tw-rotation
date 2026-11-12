# 把多張截圖拼成一張：python3 sheet.py out.png cols scale a.png b.png ...
import sys
from PIL import Image,ImageDraw
out,cols,scale=sys.argv[1],int(sys.argv[2]),float(sys.argv[3]); fs=sys.argv[4:]
ims=[Image.open(f).convert('RGB') for f in fs]; ims=[i.resize((int(i.width*scale),int(i.height*scale)),Image.LANCZOS) for i in ims]
w,h=ims[0].size; rows=(len(ims)+cols-1)//cols; S=Image.new('RGB',(w*cols,h*rows),'white'); d=ImageDraw.Draw(S)
for k,(i,f) in enumerate(zip(ims,fs)):
    S.paste(i,((k%cols)*w,(k//cols)*h)); d.text(((k%cols)*w+6,(k//cols)*h+4),f.split('/')[-1][:-4],fill=(200,0,60))
S.save(out)
