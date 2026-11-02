import glob, os
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw
OUT='/home/user/tw-rotation/docs/brand/logo_1102'
with sync_playwright() as p:
    b=p.chromium.launch(executable_path="/opt/pw-browsers/chromium"); pg=b.new_page(viewport={'width':512,'height':512})
    for f in sorted(glob.glob(OUT+'/d?_*.svg')):
        pg.goto('file://'+f); pg.screenshot(path=f[:-4]+'.png'); 
    b.close()
def circ(img, n):
    S=n*4
    im=img.convert('RGB').resize((n,n),Image.LANCZOS)
    m=Image.new('L',(S,S),0); ImageDraw.Draw(m).ellipse((0,0,S-1,S-1),fill=255); m=m.resize((n,n),Image.LANCZOS)
    o=Image.new('RGBA',(n,n),(0,0,0,0)); o.paste(im,(0,0),m); return o
for f in sorted(glob.glob(OUT+'/d?_*.png')):
    if '_circle' in f: continue
    im=Image.open(f)
    for n in (110,40): circ(im,n).save(f[:-4]+f'_circle{n}.png')
print('done')
