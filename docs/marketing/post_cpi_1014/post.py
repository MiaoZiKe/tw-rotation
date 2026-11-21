"""去背：以邊界連通區域判定背景（含綠色光暈），再去綠邊。stk/sN_raw.png → stk/sN.png"""
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as ndi
H="/home/user/tw-rotation/docs/marketing/post_cpi_1014/stk/"
KEEP_GREEN=False
def key(im):
    a=np.asarray(im.convert('RGB')).astype(float); r,g,b=a[...,0],a[...,1],a[...,2]
    border=np.concatenate([a[0],a[-1],a[:,0],a[:,-1]]); bg=np.median(border,axis=0)
    dist=np.sqrt(((a-bg)**2).sum(-1)); d=g-np.maximum(r,b)
    cand=(dist<90)|((d>12)&(np.minimum(np.minimum(r,g),b)<235)&(r+g+b>300))
    lab,n=ndi.label(cand); edge=set(np.unique(np.concatenate([lab[0],lab[-1],lab[:,0],lab[:,-1]])))-{0}
    bgm=np.isin(lab,list(edge))
    bgm=ndi.binary_dilation(bgm,iterations=2)           # 吃掉邊緣綠暈
    alpha=(~bgm).astype(float)
    alpha=np.asarray(Image.fromarray((alpha*255).astype('uint8')).filter(ImageFilter.GaussianBlur(0.8)))/255.0
    out=a.copy()
    # 去綠邊（外緣 6px 帶）與本體偏綠白毛
    band=ndi.binary_dilation(~bgm,iterations=1)&~ndi.binary_erosion(~bgm,iterations=6)
    sp=(g>np.maximum(r,b))&band
    out[...,1]=np.where(sp,np.maximum(r,b),out[...,1])
    tint=(g>0.93*r)&(g>=b+8)&(np.minimum(np.minimum(r,g),b)>110)&~bgm
    tint0=(g>r)&(np.minimum(np.minimum(r,g),b)>110)&~bgm
    m=np.maximum(r,g)
    out[...,0]=np.where(tint,m,out[...,0]); out[...,1]=np.where(tint,m*0.965,out[...,1]); out[...,2]=np.where(tint,np.maximum(b,m*0.87),out[...,2])
    if KEEP_GREEN is False:
        left=(g-np.maximum(r,b)>28)&(r<215)&~bgm&(a.sum(-1)>200)
        bgm=bgm|ndi.binary_dilation(left,iterations=1)
        alpha=np.minimum(alpha,np.asarray(Image.fromarray(((~bgm)*255).astype('uint8')).filter(ImageFilter.GaussianBlur(0.8)))/255.0)
    im2=Image.fromarray(out.clip(0,255).astype('uint8'),'RGB').convert('RGBA'); im2.putalpha(Image.fromarray((alpha*255).astype('uint8'))); return im2
if __name__=="__main__":
    for i in range(1,10):
        im=key(Image.open(H+f"s{i}_raw.png")); bb=im.getchannel('A').point(lambda v:255 if v>128 else 0).getbbox()
        im.crop(bb).save(H+f"s{i}.png"); print(i,bb)
