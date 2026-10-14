"""去背：stk/sN_raw.png → stk/sN.png（透明、裁到本體）"""
import numpy as np, sys
from PIL import Image, ImageFilter
H="/home/user/tw-rotation/docs/marketing/post_cpi_1014/stk/"
def key(im):
    a=np.asarray(im.convert('RGB')).astype(float); r,g,b=a[...,0],a[...,1],a[...,2]
    d=g-np.maximum(r,b)
    alpha=np.clip(1-(d-12)/30,0,1)
    out=a.copy(); sp=(d>0)
    out[...,1]=np.where(sp,np.minimum(g,np.maximum(r,b)),g)
    tint=(g>r)&(np.minimum(np.minimum(r,g),b)>110)
    out[...,1]=np.where(tint,r*0.975,out[...,1]); out[...,2]=np.where(tint,np.maximum(b,r*0.86),out[...,2])
    A=Image.fromarray((alpha*255).astype('uint8')).filter(ImageFilter.MinFilter(3))
    im2=Image.fromarray(out.astype('uint8'),'RGB').convert('RGBA'); im2.putalpha(A); return im2
for i in range(1,10):
    im=key(Image.open(H+f"s{i}_raw.png")); bb=im.getchannel('A').point(lambda v:255 if v>128 else 0).getbbox()
    im.crop(bb).save(H+f"s{i}.png"); print(i,bb)
