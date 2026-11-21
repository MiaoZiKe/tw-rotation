# 量每款符號（k=1）離中心最遠的像素半徑，存 fit.json，供頭像與字標自動縮放
import json, numpy as np
from PIL import Image
CHK='/tmp/claude-0/-home-user-tw-rotation/ce50d787-1067-5482-ab44-99dc39a48890/scratchpad/rrxq3_chk'
o={}
for n in range(1,13):
    a=np.array(Image.open(f'{CHK}/av{n}_1.png'))[:,:,3]>20; ys,xs=np.nonzero(a)
    o[str(n)]=float(np.sqrt((xs-539.5)**2+(ys-539.5)**2).max())
json.dump(o,open('fit.json','w')); print(o)
