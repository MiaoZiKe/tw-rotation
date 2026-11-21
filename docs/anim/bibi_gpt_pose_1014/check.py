"""自檢：身體面積比、腮紅占比、眼睛位置、腳掌左右比；輸出 check.json + contact_sheet.png"""
import numpy as np, json, glob, os
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
D='docs/anim/bibi_gpt_pose_1014/'
NAMES=['side_r','run_A','run_B','run_C','q34_r','lie_front','lie_side','sniff','sit','lay','squash','apex']
CN={'side_r':'右側面站姿','run_A':'奔跑A','run_B':'奔跑B(騰空)','run_C':'奔跑C','q34_r':'右前3/4','lie_front':'趴姿正面','lie_side':'趴姿側面','sniff':'低頭嗅地','sit':'坐姿','lay':'躺姿','squash':'正面壓縮','apex':'空中最高點'}
# 基準
idle=Image.open('docs/anim/bibi_library/reference/default_idle_1011.webp').convert('RGBA')
a=np.asarray(idle.convert('RGB')).astype(int); bgc=a[2,2]
m=(np.abs(a-bgc).sum(2)>40)
# 影子（灰橢圓）去除：只留最大連通且排除淡灰
lab,nl=ndi.label(ndi.binary_fill_holes(m)); sz=ndi.sum(m,lab,range(1,nl+1)); body=lab==(1+int(np.argmax(sz)))
idle_a=np.dstack([a,body*255]).astype('uint8'); idle_t=Image.fromarray(idle_a,'RGBA')
hop=Image.open('docs/anim/bibi_library/reference/hop_sheet_ref_1011.png').convert('RGBA').crop((6,246,114,354)).resize((512,512),Image.LANCZOS)
base_area=int(body.sum())
def stats(im):
    A=np.asarray(im); al=A[...,3]>128; rgb=A[...,:3].astype(int)
    area=int(al.sum()); ys,xs=np.where(al); bb=(xs.min(),ys.min(),xs.max(),ys.max()); w,h=bb[2]-bb[0],bb[3]-bb[1]
    pink=al&(rgb[...,0]>220)&(rgb[...,1]>130)&(rgb[...,1]<190)&(rgb[...,2]>100)&(rgb[...,2]<170)
    lab,n=ndi.label(pink); sz=ndi.sum(pink,lab,range(1,n+1)) if n else []
    cheeks=sorted([(int(s),i+1) for i,s in enumerate(sz) if s>800],reverse=True)
    cheek_area=[c[0] for c in cheeks[:2]]
    dark=al&(rgb.sum(2)<150); lab2,n2=ndi.label(dark); eyes=[]
    for i in range(1,n2+1):
        yy,xx=np.where(lab2==i)
        if 150<len(yy)<2500 and (yy.max()-yy.min())<60 and abs((yy.max()-yy.min())-(xx.max()-xx.min()))<10 and yy.mean()<bb[1]+h*0.7 and yy.mean()>bb[1]+h*0.1:
            # 圓點：填滿率高
            if len(yy)/((np.ptp(yy)+1)*(np.ptp(xx)+1))>0.65: eyes.append((round((xx.mean()-bb[0])/w,3),round((yy.mean()-bb[1])/h,3),int(len(yy))))
    # 腳掌：底部 25% 內的粉橘（不含腮紅元件）
    cheekids={c[1] for c in cheeks[:2]}
    foot=pink&~np.isin(lab,list(cheekids)); foot[:int(bb[1]+h*0.7)]=False
    cx=(bb[0]+bb[2])/2; fl=int(foot[:, :int(cx)].sum()); fr=int(foot[:, int(cx):].sum())
    return dict(area=area,area_ratio_vs_default=round(area/base_area,3),bbox_w=int(w),bbox_h=int(h),cheek_areas=cheek_area,cheek_ratio=round(cheek_area[0]/area,4) if cheek_area else None,eyes_rel_bbox_x_y_px=eyes[:2],foot_px_left=fl,foot_px_right=fr,foot_LR_ratio=round(min(fl,fr)/max(fl,fr),2) if max(fl,fr)>0 else None)
res={'default_idle':stats(idle_t)}
tiles=[('default_idle',idle_t),('跳躍第9格',hop)]
for n in NAMES:
    im=Image.open(D+f'png/{n}.png'); res[n]=stats(im); tiles.append((CN[n],im))
res['_說明']='area_ratio=不透明面積/default_idle 身體面積(影子已去除)；cheek=粉橘大塊元件(腮紅)；eyes=黑色圓點在 bbox 內的相對座標；foot_LR=底部粉橘(非腮紅)中軸左右像素比，側面姿勢左右比無意義'
json.dump(res,open(D+'check.json','w'),ensure_ascii=False,indent=1)
from PIL import ImageFont
f=ImageFont.truetype('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',14)
cell=256; cols=7
bgs=[('奶油白',(254,248,232)),('淺藍',(224,236,250)),('深色',(30,32,40))]
rows=(len(tiles)+cols-1)//cols
S=Image.new('RGB',(cols*cell,len(bgs)*rows*(cell+18)),(0,0,0))
for bi,(bn,col) in enumerate(bgs):
    for i,(t,im) in enumerate(tiles):
        x=(i%cols)*cell; y=(bi*rows+i//cols)*(cell+18)
        c=Image.new('RGBA',(512,512),col+(255,)); c.alpha_composite(im.convert('RGBA'))
        S.paste(c.convert('RGB').resize((cell,cell),Image.LANCZOS),(x,y+18))
        d=ImageDraw.Draw(S); d.rectangle([x,y,x+cell,y+18],fill=col); d.text((x+3,y),f'{bn}｜{t}',fill=(0,0,0) if bi<2 else (255,255,255),font=f)
        d.line([x,y+18+int(485/2),x+cell,y+18+int(485/2)],fill=(255,0,0),width=1)
S.save(D+'contact_sheet.png')
print(json.dumps({k:{kk:v[kk] for kk in('area_ratio_vs_default','cheek_ratio','eyes_rel_bbox_x_y_px','foot_LR_ratio')} for k,v in res.items() if k[0]!='_'},ensure_ascii=False))
