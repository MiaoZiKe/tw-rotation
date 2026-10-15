"""新版比比：原始4×4分鏡→512影格→同時長160網站素材。保留舊圖庫。"""
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw,ImageFont
from scipy import ndimage
import numpy as np
import argparse,json,hashlib,shutil,re,io

ROOT=Path(__file__).resolve().parents[2]
MS={'sleep_loop':1360,'wake_once':1630,'selfie':1200,'hit':650,'cry':1000,'eat_q':1900,'spin_q':1290,'run_r':560,'run_l':560,'run_start_r':340,'run_stop_r':850,'ball_catch':1560,'ball_catch_l':1560,'pet_q':1680,'highfive':1190,'dance':1290,'hug':1410,'receive':1180,'popcorn':1220,'sniff_eat':870,'hop_reach':810,'pounce':1120,'tangle':880,'look_up':640}
LOOPS={'sleep_loop','cry','run_r','run_l','look_up'}

def timing(key):
    total=MS[key]
    if key=='highfive': lead=[100,80,90,100]; weights=[1]*10+[2,4]
    elif key=='selfie': lead=[80,70,70,220]; weights=[1]*10+[2,4]
    elif key=='hop_reach': lead=[30,40,40,50,100,40,30,80]; weights=[1]*7+[12]
    elif key in LOOPS or key.startswith('run_'): lead=[];weights=[1]*16
    elif key=='eat_q':lead=[];weights=[1,1,1,1,1,1,1,1,1,1,1,1,1,2,3,4]
    else:lead=[];weights=[1]*12+[1,2,2,4]
    remain=total-sum(lead); raw=[remain*w/sum(weights) for w in weights]
    values=[max(10,int(v/10)*10) for v in raw]
    order=sorted(range(len(raw)),key=lambda i:(raw[i]-values[i],(i*.618)%1),reverse=True)
    for i in order[:(remain-sum(values))//10]:values[i]+=10
    assert min(values)>0 and sum(lead+values)==total
    return lead+values

def encode(frames,durations,loop,q):
    b=io.BytesIO();frames[0].save(b,'WEBP',save_all=True,append_images=frames[1:],duration=durations,loop=loop,quality=q,method=5,allow_mixed=False)
    return b.getvalue()

def extract(path,key):
    image=Image.open(path).convert('RGBA'); w,h=image.size
    cells=[];boxes=[]
    for i in range(16):
        cell=image.crop((round(i%4*w/4),round(i//4*h/4),round((i%4+1)*w/4),round((i//4+1)*h/4)))
        lab,n=ndimage.label(np.asarray(cell.getchannel('A'))>96)
        counts=np.bincount(lab.ravel());counts[0]=0
        sl=ndimage.find_objects(lab)[int(counts.argmax())-1]
        box=(sl[1].start,sl[0].start,sl[1].stop,sl[0].stop)
        cells.append(cell);boxes.append(box)
    base=boxes[0]; scale=300/(base[2]-base[0])
    out=[]
    for i,(cell,box) in enumerate(zip(cells,boxes)):
        # Keep original component layout/props. Neighboring cell fragments are outside the sprite envelope.
        envelope=(max(0,box[0]-16),max(0,box[1]-16),min(cell.width,box[2]+42),min(cell.height,box[3]+16))
        tile=cell.crop(envelope); tile=tile.resize((round(tile.width*scale),round(tile.height*scale)),Image.Resampling.LANCZOS)
        cx=(box[0]+box[2])/2-envelope[0];by=box[3]-envelope[1]
        dy=([0,0,-35,-75,-45,-10,0,0,0,0,0,0,0,0,0,0][i] if key=='selfie' else 0)
        frame=Image.new('RGBA',(512,512));frame.alpha_composite(tile,(round(247.5-cx*scale),round(481-by*scale+dy)))
        out.append(frame)
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);a=ap.parse_args()
    dest=ROOT/'docs/anim/bibi_web_1015';dest.mkdir(parents=True,exist_ok=True)
    frames={}
    for key in MS:
        if key in {'run_l','ball_catch_l'}:continue
        source=a.source/key/'source_sheet.png'
        if not source.exists():raise RuntimeError(f'缺少原始分鏡：{key}')
        frames[key]=extract(source,key)
    # Reuse exact joint images, rather than cross-fading two incompatible character silhouettes.
    frames['hit'][-1]=frames['cry'][0].copy()
    frames['wake_once'][0]=frames['sleep_loop'][-1].copy()
    for key in LOOPS-{'run_l'}:frames[key][-1]=frames[key][0].copy()
    for key in ['run_l','ball_catch_l']:frames[key]=[ImageOps.mirror(f) for f in frames[key[:-2]+'_r' if key=='run_l' else 'ball_catch']]
    manifest=[]
    for key,fr in frames.items():
        folder=dest/key;(folder/'frames').mkdir(parents=True,exist_ok=True)
        durations=timing(key);loop=0 if key in LOOPS else 1
        for i,f in enumerate(fr):f.save(folder/'frames'/f'{i+1:02d}.png')
        web=[f.crop((28,52,468,492)).resize((160,160),Image.Resampling.LANCZOS) for f in fr]
        for quality in [86,78,68,58]:
            data=encode(web,durations,loop,quality)
            if len(data)<=61440:break
        runtime=ROOT/'site/brand/bibi'/f'{key}.webp';runtime.write_bytes(data)
        # Preserve full-resolution alpha animation, timings, and a neutral three-background review strip.
        (folder/'anim.webp').write_bytes(encode(fr,durations,loop,92))
        atlas=Image.new('RGB',(640,640),'#fff7e8')
        for i,f in enumerate(web):
            bg=Image.new('RGBA',(160,160),'#fff7e8');bg.alpha_composite(f);atlas.paste(bg.convert('RGB'),(i%4*160,i//4*160))
        palette=atlas.quantize(colors=255);pal=palette.getpalette();pal[765:768]=[255,0,255];palette.putpalette(pal)
        gifs=[]
        for f in web:
            q=f.convert('RGB').quantize(palette=palette,dither=Image.Dither.NONE);pixels=np.array(q);pixels[np.asarray(f.getchannel('A'))<128]=255
            q=Image.fromarray(pixels);q.putpalette(pal);q.info['transparency']=255;gifs.append(q)
        gifs[0].save(folder/'anim.gif',save_all=True,append_images=gifs[1:],duration=durations,loop=0,disposal=2,transparency=255,optimize=False)
        source_key=key[:-2]+'_r' if key=='run_l' else 'ball_catch' if key=='ball_catch_l' else key
        metadata=json.loads((a.source/source_key/'metadata.json').read_text())
        metadata.update({'file':key,'frames':16,'durations_ms':durations,'total_ms':sum(durations),'loop':loop,'mirrored':key in {'run_l','ball_catch_l'},'contact_note':'使用同一網站時間表；接觸點依新圖修正。'})
        (folder/'storyboard.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2))
        sheet=Image.new('RGBA',(4*160,4*184));draw=ImageDraw.Draw(sheet)
        for i,f in enumerate(web):
            bg=Image.new('RGBA',(160,160),['#fff5e7','#e2ecf5','#342b32'][i%3]);bg.alpha_composite(f);sheet.alpha_composite(bg,(i%4*160,i//4*184));draw.text((i%4*160+5,i//4*184+163),f'{i+1:02d} {durations[i]}ms',fill='#392820')
        sheet.save(folder/'sheet_all.png')
        check=Image.open(runtime);d=[]
        for i in range(check.n_frames):check.seek(i);check.load();d.append(check.info['duration'])
        assert sum(d)==MS[key] and check.size==(160,160)
        manifest.append({'file':key,'frames':check.n_frames,'total_ms':sum(d),'loop':loop,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'quality':quality})
    (dest/'manifest.json').write_text(json.dumps({'version':'1015gpt1','animations':manifest},ensure_ascii=False,indent=2))
    print(json.dumps(manifest,ensure_ascii=False))

if __name__=='__main__':main()
