#!/usr/bin/env python3
"""v4 動作序列圖：每鏡插圖面板抽 6 格（同一裁切框，證明是物件在動、整張沒縮放）。用法：python3 motion_strip.py <名> <輸出png>"""
import subprocess,sys,json,glob,os,shutil
from PIL import Image,ImageDraw,ImageFont
name,out=sys.argv[1:3];B=os.path.dirname(os.path.abspath(__file__))
# 每鏡：(id, 面板 top, 高, 取樣起, 終)
SC=[("s1",972,528,0.3,2.3),("s2",392,348,0.3,3.3),("s3",392,348,0.3,1.7),("s4",310,330,0.3,3.4),("s5",392,368,0.4,2.6),("s6",392,368,0.3,2.4),("s7",392,508,0.3,2.6),("s8",392,368,0.3,1.8)]
if "v5" in name: SC[0]=("s1",978,528,0.3,2.3)
ft=ImageFont.truetype("/root/.fonts/NotoSansCJKtc-Bold.otf",26) if os.path.exists("/root/.fonts/NotoSansCJKtc-Bold.otf") else None
rows=[]
for id,top,h,a,b in SC:
    d="/tmp/claude-0/scratch/ms_"+id;shutil.rmtree(d,ignore_errors=True)
    subprocess.run(["node",B+"/preview_frames.js",name,d,"scene:%s:6:%s:%s"%(id,a,b),"96,%d,888,%d"%(top,h)],check=True,capture_output=True)
    fs=sorted(glob.glob(d+"/*.png"));ims=[Image.open(f).resize((444,int(h*444/888))) for f in fs]
    row=Image.new("RGB",(444*6+50,ims[0].height+4),"white")
    for i,im in enumerate(ims): row.paste(im,(50+444*i,0))
    dr=ImageDraw.Draw(row);dr.text((4,8),id,fill="black",font=ft)
    for i,f in enumerate(fs): dr.text((56+444*i,ims[0].height-30),os.path.basename(f)[1:-4]+"s",fill=(120,60,0),font=ft)
    rows.append(row)
W=Image.new("RGB",(rows[0].width,sum(r.height for r in rows)),"white");y=0
for r in rows: W.paste(r,(0,y));y+=r.height
W.save(out);print(out,W.size)
