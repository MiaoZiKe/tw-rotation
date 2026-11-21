"""GPT 產圖（螢光綠底）→ 去背 → 512×512 透明 PNG，腳底對齊基準線 y=485，水平置中。"""
import numpy as np, json
from PIL import Image
D='docs/anim/bibi_gpt_pose_1014/'
# 名稱: (原檔, 騰空抬高px(512座標))
MAP={'side_r':('side_r',0),'run_A':('run_A2',0),'run_B':('run_B2',60),'run_C':('run_C2',0),'q34_r':('q34_r',0),
 'lie_front':('lie_front',0),'lie_side':('lie_side',0),'sniff':('sniff',0),'sit':('sit',0),'lay':('lay2',0),
 'squash':('squash',0),'apex':('apex2',150)}
BASE=485
def key(im):
    a=np.asarray(im.convert('RGB')).astype(float); r,g,b=a[...,0],a[...,1],a[...,2]
    d=g-np.maximum(r,b)            # 綠色優勢
    alpha=np.clip(1-(d-40)/80,0,1) # d>=120 全透明，<=40 全不透明
    out=a.copy()
    sp=(d>0)&(alpha>0)             # 去綠邊
    out[...,1]=np.where(sp,np.minimum(g,np.maximum(r,b)),g)
    return Image.fromarray(np.dstack([out,alpha*255]).astype('uint8'),'RGBA')
info={}
for n,(src,lift) in MAP.items():
    im=key(Image.open(D+f'raw/{src}.png')).resize((512,512),Image.LANCZOS)
    bb=im.getchannel('A').point(lambda v:255 if v>128 else 0).getbbox()
    cx=(bb[0]+bb[2])/2; dx=int(256-cx); dy=int(BASE-lift-bb[3])
    c=Image.new('RGBA',(512,512),(0,0,0,0)); c.alpha_composite(im,(dx,dy)) if dx>=0 and dy>=0 else c.paste(im,(dx,dy),im)
    c.save(D+f'png/{n}.png'); info[n]=bb
print(json.dumps(info))
