from PIL import Image
import glob
ns=['logo1_把燈留著','logo2_今天先這樣就好','logo3_沒關係的房間']
S=Image.new('RGB',(3*330,330+130+120+330),'#9a9a9a')
for i,n in enumerate(ns):
    x=i*330
    a=Image.open(f'{n}_頭像_淺_圓形.png').resize((300,300)); S.paste(a,(x+15,15),a)
    for j,t in enumerate(['淺','深','單色黑','單色白','單色主色']):
        pass
    y=340
    for k,t in enumerate(['淺','深']):
        for m,sz in enumerate([110,44]):
            im=Image.open(f'{n}_頭像_{t}_{sz}圓形.png'); S.paste(im,(x+15+k*150+m*0,y if m==0 else y+120),im)
    for k,t in enumerate(['單色黑','單色白','單色主色']):
        im=Image.open(f'{n}_頭像_{t}.png').resize((96,96)); S.paste(im,(x+15+k*104,y+175))
    w=Image.open(f'{n}_橫式_淺.png').resize((300,86)); S.paste(w,(x+15,y+290-0))
    w=Image.open(f'{n}_橫式_深.png').resize((300,86)); S.paste(w,(x+15,y+385-0))
S.crop((0,0,990,820)).save('contact_sheet_頭像圓形_110_44_單色_橫式.png')
