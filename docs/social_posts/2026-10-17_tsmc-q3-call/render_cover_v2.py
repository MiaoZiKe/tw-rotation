from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import random,shutil
P=Path(__file__).parent
(P/'qa').mkdir(exist_ok=True)
W,H=1080,1350
C='#321A14'; M='#795B49'
im=Image.new('RGB',(W,H),'#FFF9EF'); d=ImageDraw.Draw(im)
def font(n,b=False): return ImageFont.truetype('C:/Windows/Fonts/msjhbd.ttc' if b else 'C:/Windows/Fonts/msjh.ttc',n)
def text(x,y,s,n=36,c=C,b=False,stroke=0):
 f=font(n,b); box=d.textbbox((x,y),s,font=f,stroke_width=stroke)
 assert box[0]>=64 and box[2]<=1016 and box[3]<=1290,(s,box)
 d.text((x,y),s,font=f,fill=c,stroke_width=stroke,stroke_fill=c)
def center(y,s,n=36,c=C,b=False,stroke=0):
 f=font(n,b); x=(W-d.textlength(s,font=f))/2
 text(x,y,s,n,c,b,stroke)
random.seed(17)
for _ in range(8000):
 x=random.randrange(W); y=random.randrange(H)
 d.point((x,y),fill=random.choice(['#F6EFE5','#FFF9EF','#FFF9EF']))
d.rounded_rectangle((74,68,423,126),29,fill='#FFD4BA',outline=C,width=3)
text(98,77,'比比快訊・法說研究室',27,b=True)
text(840,81,'01 / 校準',26,b=True)
# 大標：貼紙留邊與淡黃刷色底，文字由程式後製。
f=font(106,True); s='台積電法說'; x=78; y=153
d.text((x,y),s,font=f,fill=C,stroke_width=10,stroke_fill='#FFFFFF')
d.text((x,y),s,font=f,fill=C,stroke_width=1,stroke_fill=C)
d.rounded_rectangle((74,300,1006,426),39,fill='#FFE5A5')
center(292,'看哪五個數字？',102,b=True,stroke=1)
text(81,446,'比比帶你讀懂產業線索',37,b=True)
# 大型科技情境，角色有與主題相關的觀察動作。
scene_path=P/'assets/bibi_research_scene_v001.png'
if not scene_path.exists(): scene_path=P.parents[1]/'social_assets/author_unverified/bibi_chip_research_host/v001.png'
scene=Image.open(scene_path).convert('RGBA')
scene.thumbnail((970,584),Image.Resampling.LANCZOS)
sx=(W-scene.width)//2; sy=534
im.paste(scene,(sx,sy),scene); d=ImageDraw.Draw(im)
# 獨立台詞：尾巴指向左側比比；不覆蓋角色或零件。
d.rounded_rectangle((80,510,520,596),27,fill='#FFFFFF',outline=C,width=3)
d.polygon([(320,595),(360,630),(364,595)],fill='#FFFFFF')
d.line([(320,595),(360,630),(364,595)],fill=C,width=3)
text(106,517,'先分清楚，',29,b=True)
text(106,554,'實際還是財測？',29,b=True)
# 五個財務入口獨立成列，沒有指向科技構件的線。
labels=[('營收','#FFD4BA'),('毛利率','#FFE5A5'),('營收財測','#B9DFF0'),('製程占比','#B9DBCC'),('資本支出','#DCCEF0')]
for i,(label,color) in enumerate(labels):
 x=76+i*188
 d.rounded_rectangle((x,1127,x+176,1191),22,fill=color,outline=C,width=2)
 f=font(31,True); tx=x+(176-d.textlength(label,font=f))/2
 text(tx,1140,label,31,b=True)
text(80,1220,'來源：台積電 2026 年第 3 季公告（SEC）',27,c=M)
text(80,1257,'哩股哩股',25,b=True)
text(278,1259,'整理公開資訊，非投顧，投資請自行判斷。',24)
im.save(P/'slides/01_v2.png',optimize=True)
im.resize((360,450),Image.Resampling.LANCZOS).save(P/'slides/01_v2_mobile.png')
# 角色與道具接觸放大檢查，不改寫原始圖。
scene_original=Image.open(scene_path).convert('RGBA')
crop=scene_original.crop((100,120,950,880))
bg=Image.new('RGBA',crop.size,'#FFF9EF'); bg.alpha_composite(crop)
bg.convert('RGB').resize((1700,1520),Image.Resampling.LANCZOS).save(P/'qa/bibi_contact_200.png')
print('v2 rendered; text bounds verified')
