"""哩股哩股分層輪播引擎；所有正式文字以字型後製，缺插畫即失敗。"""
import argparse, json, math, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W,H=1080,1350
INK='#321A14'; PAPER='#FFF9EF'; CORAL='#E7806F'; BLUE='#B9DFF0'; MINT='#B9DBCC'; YELLOW='#FFE5A5'; PURPLE='#DCCEF0'
FONT='C:/Windows/Fonts/msjh.ttc'; BOLD='C:/Windows/Fonts/msjhbd.ttc'
def font(size,bold=False): return ImageFont.truetype(BOLD if bold else FONT,size)

class Page:
 def __init__(self,p,project):
  self.p=p;self.project=project;self.boxes=[];self.assets=[]
  self.im=Image.new('RGB',(W,H),PAPER);self.d=ImageDraw.Draw(self.im)
  rng=random.Random(111)
  for _ in range(1800):
   x=rng.randrange(W);y=rng.randrange(H);self.d.point((x,y),fill='#EFE7D9')
  self.d.rounded_rectangle((32,32,1048,1318),radius=43,outline='#E8C9AB',width=2)
 def card(self,box,fill=PAPER,outline='#C7A68C',radius=28): self.d.rounded_rectangle(box,radius,fill,outline,3)
 def text(self,txt,box,size=36,bold=False,color=INK,align='left',label='text',leading=1.25):
  x,y,x2,y2=box; f=font(size,bold); lines=[]
  for para in str(txt).split('\n'):
   line=''
   for char in para:
    if self.d.textlength(line+char,font=f)>x2-x:
     if not line:raise ValueError('字元超過文字區')
     lines.append(line);line=char
    else:line+=char
   lines.append(line)
  step=round(size*leading); height=step*(len(lines)-1)+max((self.d.textbbox((0,0),line,font=f,anchor='lt')[3] for line in lines),default=size)
  if y+height>y2:raise ValueError(f'第{self.p["page"]}頁文字溢出 {label}: {txt}，需{height}高/有{y2-y}')
  actual=[]
  for i,line in enumerate(lines):
   width=self.d.textlength(line,font=f);xx=x if align=='left' else x+(x2-x-width)/2
   bb=self.d.textbbox((xx,y+i*step),line,font=f,anchor='lt')
   self.d.text((xx,y+i*step),line,font=f,fill=color,anchor='lt')
   actual.append(list(bb))
  self.boxes.append({'kind':'text','name':label,'text':str(txt),'reserved':list(box),'actual':actual,'font_size':size})
 def asset(self,path,box,name='illustration',transparent=True):
  path=Path(path)
  if not path.is_file():raise FileNotFoundError(f'必要插畫尚未就緒：{path}')
  im=Image.open(path).convert('RGBA'); ab=im.getchannel('A').getbbox()
  if not ab:raise ValueError(f'空白素材 {path}')
  extrema=im.getchannel('A').getextrema()
  if transparent and extrema[0]==255:raise ValueError(f'需透明插畫卻沒有透明像素 {path}')
  im=im.crop(ab);im.thumbnail((box[2]-box[0],box[3]-box[1]),Image.Resampling.LANCZOS)
  x=box[0]+(box[2]-box[0]-im.width)//2;y=box[1]+(box[3]-box[1]-im.height)//2
  self.im.paste(im,(x,y),im)
  self.boxes.append({'kind':'illustration','name':name,'reserved':list(box),'actual':[[x,y,x+im.width,y+im.height]],'expected_occlusion':'角色與道具內部接觸需人工檢查'})
  self.assets.append({'path':str(path),'alpha_extrema':extrema,'source_size':list(Image.open(path).size)})
 def arrow(self,a,b,color=CORAL,width=9):
  self.d.line([a,b],fill=color,width=width);ang=math.atan2(b[1]-a[1],b[0]-a[0]);l=20
  self.d.polygon([b,(b[0]-l*math.cos(ang-.5),b[1]-l*math.sin(ang-.5)),(b[0]-l*math.cos(ang+.5),b[1]-l*math.sin(ang+.5))],fill=color)
 def header(self):
  p=self.p
  self.card((72,66,398,112),YELLOW,outline=YELLOW,radius=20)
  self.text('比比的科技研究筆記',(88,73,390,110),24,True)
  self.text(f'{p["page"]:02d} / 10',(830,73,1000,116),26,True,align='center',label='page_number')
  self.text(p['title'],(72,152,1008,330),64,True,label='title')
  if p.get('subtitle'):self.text(p['subtitle'],(76,330,1004,431),34,color='#795B49',label='subtitle')
 def footer(self):
  self.d.line((76,1240,1004,1240),fill='#D8BFA5',width=2)
  self.text(self.p.get('source_note','完整來源見說明'),(76,1257,1004,1300),24,label='source_note')
 def bubble(self,pose=1):
  pose_path=self.p.get('pose_asset') or self.p.get('bibi',{}).get('asset_path') or f'assets/poses/{pose:02d}.png'
  pose_file=Path(pose_path)
  if not pose_file.is_absolute():pose_file=self.project/pose_file
  if self.p.get('layout')=='definition':
   self.asset(pose_file,(690,560,993,810),'bibi_observes_wafer')
   self.card((92,1010,986,1186),'#FFFDF6',INK,32)
   self.d.polygon([(868,1010),(892,982),(912,1010)],fill='#FFFDF6')
   self.d.line([(868,1010),(892,982),(912,1010)],fill=INK,width=3)
   self.text(self.p.get('bubble',''),(124,1050,954,1158),36,True,label='host_bubble')
   return
  if self.p.get('layout') in ('summary','risks','cta'):
   self.asset(pose_file,(699,946,1003,1222),'bibi_notebook_host')
   self.card((82,1000,668,1188),'#FFFDF6',INK,32)
   self.d.polygon([(668,1070),(700,1104),(668,1125)],fill='#FFFDF6')
   self.d.line([(668,1070),(700,1104),(668,1125)],fill=INK,width=3)
   self.text(self.p.get('bubble',''),(110,1042,639,1168),34,True,label='host_bubble')
   return
  self.asset(pose_file,(76,965,358,1214),'bibi_host')
  self.card((390,1010,1002,1195),'#FFFDF6',INK,32)
  self.d.polygon([(390,1080),(355,1113),(390,1130)],fill='#FFFDF6')
  self.d.line([(390,1080),(355,1113),(390,1130)],fill=INK,width=3)
  self.text(self.p.get('bubble','一起把科技看懂！'),(420,1043,972,1172),34,True,label='host_bubble')
 def chip(self,box,label='晶片',fill='#586A78'):
  x,y,x2,y2=box
  for xx in range(x+15,x2-5,28):self.d.rounded_rectangle((xx,y-12,xx+12,y2+12),4,'#E8BA69',INK,2)
  self.d.rounded_rectangle(box,18,fill,INK,5)
  self.d.line((x+15,y+17,x2-20,y+17),fill='#D6E6E7',width=4)
  self.text(label,(x+15,y+35,x2-15,y2-8),30,True,color='white',align='center',label='chip_label')
 def render(self):
  p=self.p;n=p['page'];layout=p.get('layout',['cover','definition','signal','euv','comparison','results','chain','risks','summary','cta'][n-1])
  if layout=='cover':
   self.card((72,67,398,114),YELLOW,outline=YELLOW)
   self.text('比比的科技研究筆記',(88,76,390,113),24,True)
   self.text('01 / 10',(845,77,1008,117),26,True,label='page_number')
   self.text(p.get('brand_label','ASML'),(70,160,1010,287),110,True,color='#173D68',label='brand')
   self.text(p.get('cover_title',p['title']),(72,295,1008,525),88,True,label='title')
   self.asset(self.project/'assets/cover_scene.png',(55,520,1025,1053),'cover_scene')
   self.text('設備場景示意・非真實機型剖面',(120,1054,990,1087),24,label='scene_note')
   self.card((76,1095,1004,1200),'#FFF0D4',outline='#EACCA3')
   self.text(p.get('bubble',p.get('subtitle','')),(105,1113,976,1191),36,True,label='cover_promise')
  else:
   self.header()
   if layout=='definition':
    self.asset(self.project/'assets/tech_illustrated/machine.png',(86,450,660,790),'euv_machine')
    self.asset(self.project/'assets/tech_illustrated/wafer.png',(650,510,990,802),'wafer')
    self.arrow((590,660),(700,660))
    self.card((80,825,1000,952),BLUE,outline='#8CB4CA')
    self.text('\n'.join(p.get('body',[])),(110,845,970,942),36,True,label='body')
   elif layout=='signal':
    items=p.get('items',[{'title':x,'detail':''} for x in p.get('body',[])])
    for i,item in enumerate(items[:3]):
     x=85+i*310;y=600-i*45
     self.d.ellipse((x+38,y,x+218,y+180),fill=[BLUE,YELLOW,MINT][i],outline=INK,width=4)
     self.text(str(i+1),(x+90,y+22,x+170,y+82),44,True,align='center')
     self.text(item['title'],(x+9,y+105,x+271,y+170),36,True,align='center')
     self.text(item.get('detail',''),(x,y+212,x+281,y+325),32,align='center')
     if i<2:self.arrow((x+229,y+86),(x+327,y+48),width=7)
    for i,path in enumerate(p.get('item_icons',['assets/tech_illustrated/fab.png','assets/tech_illustrated/machine.png','assets/tech_illustrated/wafer.png'])):
     icon=Path(path);icon=icon if icon.is_absolute() else self.project/icon
     self.asset(icon,(100+i*310,417,280+i*310,510),'demand_icon_'+str(i))
   elif layout=='euv':
    # 錫滴→雷射→電漿→反射鏡→晶圓：概念示意非機台比例
    self.card((80,445,1000,952),'#EAF2F8',outline='#A8BBC8')
    self.d.ellipse((135,555,185,605),fill='#9AA8AE',outline=INK,width=4)
    self.text('錫滴',(108,481,242,535),32,True)
    self.d.rounded_rectangle((120,699,271,784),12,'#7C8FA5',INK,4)
    self.text('雷射',(139,723,260,769),32,True,color='white')
    self.arrow((273,735),(441,628),'#EF806A',12)
    self.arrow((194,580),(442,596),'#9DAFB7',6)
    self.d.ellipse((432,550,534,652),fill='#F4B8D5',outline='#A77AB5',width=5)
    self.text('電漿發光',(381,467,650,522),34,True)
    for x,y in [(653,571),(805,580)]:
     self.d.arc((x-42,y-62,x+42,y+62),65,290,fill='#566F87',width=14)
    self.arrow((542,601),(639,576),'#AD87C4',7)
    self.d.polygon([(690,654),(728,640),(765,657),(725,674)],fill='#596D82',outline=INK,width=3)
    for off in range(0,36,10):self.d.line((703+off,652-off//4,715+off,662-off//4),fill='#E5E4ED',width=3)
    self.arrow((674,603),(725,649),'#AD87C4',6);self.arrow((725,649),(793,598),'#AD87C4',6)
    self.d.line((712,676,680,754),fill='#795B49',width=2)
    self.text('光罩圖案',(565,762,786,810),30,True)
    self.d.ellipse((712,839,923,887),fill='#8AB5D0',outline=INK,width=4)
    self.arrow((813,644),(813,833),'#AD87C4',7)
    self.text('反射鏡導引',(660,464,971,522),32,True)
    self.text('晶圓曝光',(714,899,970,945),32,True)
    self.text('真空光路・概念示意',(106,893,650,939),24,color='#795B49')
   elif layout=='comparison':
    cols=p.get('columns',[])
    for i,c in enumerate(cols):
     cw=920//len(cols);x=80+i*cw;self.card((x,450,x+cw-18,948),[BLUE,PURPLE,YELLOW][i%3])
     self.text(c['title'],(x+18,477,x+cw-36,590),36,True,align='center')
     self.d.ellipse((x+cw//2-45,625,x+cw//2+45,715),fill=INK)
     self.text(str(i+1),(x+cw//2-25,644,x+cw//2+25,698),36,True,color='white',align='center')
     copy='\n'.join(c.get('items',[])).replace('不等於已認列營收','不等於\n已認列營收').replace('受交付與認列影響','受交付與\n認列影響')
     self.text(copy,(x+18,767,x+cw-36,933),32,True)
   elif layout=='results':
    chart=p.get('chart')
    if chart:
     vals=chart['values'];fc=chart.get('forecast');maxv=max(vals+([fc['high']] if fc else []))*1.18
     self.text(chart.get('unit',''),(94,438,980,486),26,label='chart_unit')
     self.d.line((140,844,970,844),fill=INK,width=3)
     self.text('0',(90,826,135,875),26,label='zero_baseline')
     for tick in [50,100,150]:
      yy=844-320*tick/maxv
      self.d.line((140,yy,970,yy),fill='#E3D8CB',width=1)
      self.text(str(tick),(77,yy-13,132,yy+30),26,color='#795B49',align='center',label='axis_tick')
     for i,(label,val) in enumerate(zip(chart['labels'],vals)):
      x=172+i*265;height=320*val/maxv
      self.d.rounded_rectangle((x,844-height,x+145,844),14,[BLUE,CORAL,MINT][i%3],INK,3)
      self.text(str(val),(x-10,792-height,x+160,844-height),34,True,align='center')
      self.text(label,(x-20,865,x+180,950),28,True,align='center')
     if fc:
      x=702;height=320*fc['high']/maxv;self.d.rounded_rectangle((x,844-height,x+145,844),14,PAPER,CORAL,5)
      self.text(str(fc['low'])+'–'+str(fc['high']),(x-20,792-height,x+175,844-height),32,True,color='#A85648',align='center')
      self.text(fc['label'],(x-20,865,x+180,950),28,True,color='#A85648',align='center')
      low_y=844-320*fc['low']/maxv
      self.d.line((x-10,low_y,x+155,low_y),fill=CORAL,width=3)
      bracket_x=890
      self.d.line((bracket_x,844-height,bracket_x,low_y),fill=CORAL,width=4)
      self.d.line((bracket_x-12,844-height,bracket_x+12,844-height),fill=CORAL,width=4)
      self.d.line((bracket_x-12,low_y,bracket_x+12,low_y),fill=CORAL,width=4)
    else:
     for i,line in enumerate(p.get('body',[])):
      self.card((80,455+i*160,1000,590+i*160),[BLUE,YELLOW,MINT][i%3]);self.text(line,(112,480+i*160,970,580+i*160),38,True)
   elif layout=='chain':
    items=p.get('items',[{'title':x,'detail':''} for x in p.get('body',[])])
    for i,item in enumerate(items):
     y=450+i*125;self.card((235,y,1000,y+106),[BLUE,MINT,YELLOW,PURPLE][i%4])
     path=p.get('item_icons',['assets/tech_illustrated/mirror.png','assets/tech_illustrated/machine.png','assets/tech_illustrated/fab.png','assets/tech_illustrated/server.png'])[i]
     icon=Path(path);icon=icon if icon.is_absolute() else self.project/icon
     self.asset(icon,(82,y+1,214,y+106),'chain_icon_'+str(i))
     self.text(item['title'],(263,y+15,970,y+72),38,True)
     self.text(item.get('detail',''),(263,y+64,970,y+104),28)
     if i<len(items)-1:self.arrow((622,y+108),(622,y+123),width=5)
   elif layout=='summary':
    self.d.rounded_rectangle((83,448,1000,951),24,'#E3CDB4',INK,4)
    self.d.rounded_rectangle((97,458,986,938),18,'#FFFDF5',INK,3)
    self.d.line((170,474,170,921),fill='#D99B85',width=3)
    for y in range(520,925,57):self.d.line((115,y,967,y),fill='#DDDCD1',width=2)
    items=p.get('items',[])
    for i,item in enumerate(items[:3]):
     y=489+i*143
     self.d.ellipse((122,y+4,153,y+35),fill=MINT,outline=INK,width=2)
     self.text(item['title'],(199,y,934,y+59),40,True)
     self.text(item.get('detail',''),(199,y+64,934,y+114),32)
   elif layout=='risks':
    items=p.get('items',[{'title':x,'detail':''} for x in p.get('body',[])])
    for i,item in enumerate(items[:3]):
     y=450+i*162;self.card((80,y,1000,y+137),[YELLOW,BLUE,MINT][i])
     self.d.ellipse((105,y+29,174,y+98),fill=CORAL if layout=='risks' else '#659780')
     self.text('!' if layout=='risks' else str(i+1),(120,y+40,160,y+91),34,True,color='white',align='center')
     self.text(item['title'],(200,y+20,960,y+74),38,True)
     self.text(item.get('detail',''),(200,y+81,960,y+128),30)
   elif layout=='cta':
    self.card((80,448,1000,650),YELLOW)
    self.text(p.get('question','你會先看哪個觀察指標？'),(112,482,970,626),46,True,label='question')
    source_copy=p.get('source_copy','\n'.join(p.get('body',[])))
    self.text(source_copy,(90,690,996,955),28,label='sources')
   else:raise ValueError(f'未知版型 {layout}')
   self.bubble(((n-2)%8)+1)
  self.footer();return self

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--project',required=True);ap.add_argument('--cover-only',action='store_true');args=ap.parse_args()
 project=Path(args.project);data=json.loads((project/'slides_content.json').read_text(encoding='utf-8-sig'));slides=data['slides']
 for p in slides:p.setdefault('brand_label',data.get('brand_label','ASML'))
 if [p['page'] for p in slides]!=list(range(1,11)):raise ValueError('必須依序提供1..10頁')
 out=project/'slides';out.mkdir(exist_ok=True);qa=project/'qa';qa.mkdir(exist_ok=True);mobile=qa/'mobile';mobile.mkdir(exist_ok=True)
 records=[]
 for p in slides[:1] if args.cover_only else slides:
  pg=Page(p,project).render();pg.im.save(out/f'{p["page"]:02d}.png');pg.im.resize((360,450),Image.Resampling.LANCZOS).save(mobile/f'{p["page"]:02d}.png')
  records.append({'page':p['page'],'boxes':pg.boxes,'assets':pg.assets})
 (qa/'layout_boxes.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
 if not args.cover_only:
  for name,tw,th in [('overview.png',324,405),('mobile_contact.png',360,450)]:
   sheet=Image.new('RGB',(tw*5,th*2),PAPER)
   for i in range(10):sheet.paste(Image.open(out/f'{i+1:02d}.png').resize((tw,th),Image.Resampling.LANCZOS),((i%5)*tw,(i//5)*th))
   sheet.save(project/name)
 print('已渲染',len(records),'頁')
if __name__=='__main__':main()
