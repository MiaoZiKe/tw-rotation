from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import random
P=Path(__file__).parent
W,H=1080,1350
im=Image.new('RGB',(W,H),'#FFF9EF'); d=ImageDraw.Draw(im)
C='#321A14'; M='#795B49'
def font(n,b=False): return ImageFont.truetype('C:/Windows/Fonts/msjhbd.ttc' if b else 'C:/Windows/Fonts/msjh.ttc',n)
def text(x,y,s,n=36,c=C,b=False): d.text((x,y),s,font=font(n,b),fill=c)
def card(box,fill,r=28,width=3): d.rounded_rectangle(box,r,fill=fill,outline=C,width=width)
random.seed(4)
for _ in range(10000):
 x=random.randrange(W); y=random.randrange(H)
 d.point((x,y),fill=random.choice(['#F6EFE4','#FFF9EF','#FFF9EF']))
card((72,66,402,124),'#FFD4BA',29,2)
text(98,76,'比比快訊・研究筆記',28,b=True)
text(841,78,'01 / 試做',26)
text(77,168,'台積電法說',106,b=True)
d.rounded_rectangle((75,319,716,432),28,fill='#FFE5A5')
text(79,306,'看什麼？',112,b=True)
text(80,465,'從五個數字，讀懂產業線索',39,b=True)
# 科技研究桌：物件示意，不代表數據或訂單關係。
card((75,548,1005,1075),'#F8F0E1',36,3)
card((118,591,542,951),'#B9DFF0',25,3)
text(148,613,'法說觀察清單',35,b=True)
for i,(label,color) in enumerate([('營收','#FFD4BA'),('毛利率','#FFE5A5'),('營收財測','#B9DBCC'),('製程占比','#DCCEF0'),('資本支出','#FFD4BA')]):
 y=685+i*47
 d.ellipse((150,y,181,y+31),fill=color,outline=C,width=2)
 text(158,y-1,str(i+1),21,b=True); text(197,y-5,label,31)
# 晶圓示意與桌面底座
d.ellipse((644,848,944,1018),fill='#525E6B',outline=C,width=5)
d.ellipse((655,840,933,997),fill='#B9DFF0',outline=C,width=4)
for x in range(685,920,39): d.line((x,859,x,975),fill='#795B49',width=2)
for y in range(872,985,28): d.line((674,y,917,y),fill='#795B49',width=2)
d.rounded_rectangle((609,985,970,1027),17,fill='#FFD4BA',outline=C,width=3)
# 已修正的比比插圖，原生透明圖保留完整毛邊。
asset=Image.open(P/'assets/bibi_clean.png').convert('RGBA')
box=asset.getbbox(); asset=asset.crop(box); asset.thumbnail((365,365),Image.Resampling.LANCZOS)
im.paste(asset,(610+(365-asset.width)//2,654),asset)
d=ImageDraw.Draw(im)
card((622,566,954,652),'#FFFFFF',26,3)
d.polygon([(695,650),(718,680),(734,650)],fill='#FFFFFF')
d.line([(695,650),(718,680),(734,650)],fill=C,width=3)
text(649,590,'一起找重點！',34,b=True)
text(80,1115,'先分清楚：實際表現與公司財測',38,b=True)
text(80,1181,'來源：台積電第三季公告（SEC）｜2026.10.15',25,c=M)
d.line((80,1234,1000,1234),fill='#DECAB8',width=2)
text(80,1254,'哩股哩股',27,b=True)
text(286,1257,'整理公開資訊，非投顧，投資請自行判斷。',26)
im.save(P/'slides/01.png')
im.resize((360,450),Image.Resampling.LANCZOS).save(P/'slides/01_mobile.png')
print('已輸出 1080×1350 封面與 360 px 縮圖')
