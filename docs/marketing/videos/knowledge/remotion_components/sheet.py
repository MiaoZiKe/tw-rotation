import sys,subprocess,glob,os
from PIL import Image, ImageDraw
name,step,cols=sys.argv[1],int(sys.argv[2]),int(sys.argv[3])
d=f'sheets/{name}'; os.makedirs(d,exist_ok=True)
for f in glob.glob(d+'/*.png'): os.remove(f)
subprocess.run(['ffmpeg','-v','error','-i',f'out/{name}.mp4','-vf',f"select='not(mod(n\\,{step}))',scale=360:640",'-vsync','0',f'{d}/f%03d.png'],check=True)
fs=sorted(glob.glob(d+'/f*.png'))
rows=(len(fs)+cols-1)//cols
sh=Image.new('RGB',(cols*360,rows*640),(0,0,0))
for i,p in enumerate(fs):
    im=Image.open(p); ImageDraw.Draw(im).text((8,8),f'f{i*step}',fill=(255,255,0)); sh.paste(im,((i%cols)*360,(i//cols)*640))
    os.remove(p)
sh.save(f'sheets/{name}_sheet.png'); print(sh.size,len(fs))
