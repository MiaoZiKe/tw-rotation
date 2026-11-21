from PIL import Image, ImageDraw, ImageFont
D='docs/anim/bibi_gpt_pose_1014/'; O='docs/anim/bibi_basepose_1012/png/'
f=ImageFont.truetype('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',16)
# (GPT名, 舊版檔名)
P=[('side_r','side_r'),('run_A','run_r_A'),('run_B','run_r_B'),('run_C','run_r_C'),('q34_r','q34_r'),('lie_front','lie_front'),('lie_side','lie_side_r'),('sniff','sniff_r'),('sit','sit_r'),('lay','lay_r'),('squash','front_squash'),('apex','side_apex_r')]
c=256; S=Image.new('RGB',(6*c,4*(c+20)),(254,248,232)); d=ImageDraw.Draw(S)
for i,(g,o) in enumerate(P):
    col=i%6; row=i//6
    for k,(p,t) in enumerate([(O+o+'.png','像素變形版'),(D+f'png/{g}.png','GPT版')]):
        y=(row*2+k)*(c+20); x=col*c
        im=Image.open(p).convert('RGBA').resize((c,c),Image.LANCZOS)
        bg=Image.new('RGBA',(c,c),(254,248,232,255)); bg.alpha_composite(im); S.paste(bg.convert('RGB'),(x,y+20))
        d.text((x+4,y+2),f'{g}｜{t}',fill=(0,0,0),font=f)
S.save(D+'before_after_1014.png')
