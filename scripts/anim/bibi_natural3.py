"""比比自然互動第三輪：透明分鏡共同裁切匯出；不生圖、不補畫、不改原圖。"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import io
import json
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from gif_pipeline import save_gif, sheet

ROOT = Path(__file__).resolve().parents[2]
VERSION = '1015natural3'
PLANS = {
    # 此source_sheet.png是工作樹恢復後重新生成的無舌咬嘴；不可沿用已退件舊錨點。
    'leaf_bite': {'source_filename':'source_sheet.png','total_ms':1200,'contact_frame':6,'contact_ms':300,
        'sequence':[1,2,3,4,5,6,7,8,7,8,9,10,11,12,13,14,15,16],
        'durations_ms':[60,50,50,60,80,70,80,60,80,60,80,60,80,60,70,90,20,90]},
    'bubble_react': {'source_filename':'source_sheet.png','total_ms':1000,'contact_frame':4,'contact_ms':200},
    'plane_react': {'source_filename':'source_sheet.png','source_grid_offset':[14,20],'total_ms':1200,'contact_frame':6,'contact_ms':200,
        'durations_ms':[40,40,40,40,40,70,180,120,70,80,90,90,80,80,70,70]},
    'yarn_tumble': {'source_filename':'source_sheet.png','total_ms':2600,'contact_frame':6,'contact_ms':600},
}


def dump(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def distribute(total,weights):
    raw=np.asarray(weights,dtype=float);raw=raw/raw.sum()*(total//10)
    units=np.floor(raw).astype(int)
    for i in np.argsort(-(raw-units))[:total//10-units.sum()]: units[i]+=1
    return [int(v)*10 for v in units]


def timing(plan):
    sequence=plan.get('sequence',list(range(1,17)))
    if 'durations_ms' in plan:return sequence,plan['durations_ms']
    split=sequence.index(plan['contact_frame'])
    durations=distribute(plan['contact_ms'],[1.2 if i==0 else 1 for i in range(split)])
    durations+=distribute(plan['total_ms']-plan['contact_ms'],[1.4 if f in (7,9,16) else 1 for f in sequence[split:]])
    return sequence,durations


def extract(source,settings):
    im=Image.open(source).convert('RGBA');px,py=settings.get('source_cell_padding',[0,0]);cw,ch=(im.width+3)//4+2*px,(im.height+3)//4+2*py
    dx,dy=settings.get('source_grid_offset',[0,0]);cells=[];cleaning=[]
    for i in range(16):
        box=(round(i%4*im.width/4)+dx-px,round(i//4*im.height/4)+dy-py,round((i%4+1)*im.width/4)+dx+px,round((i//4+1)*im.height/4)+dy+py)
        cell=Image.new('RGBA',(cw,ch));cell.alpha_composite(im.crop(box),(0,0));a=np.array(cell)
        fringe_count=0
        if settings.get('remove_magenta_fringe',False):
            fringe=(a[:,:,0]>180)&(a[:,:,2]>140)&(a[:,:,1]<90)&(a[:,:,3]>0)
            fringe_count=int(fringe.sum());a[:,:,3][fringe]=0
        alpha=a[:,:,3]
        if (alpha==0).mean()<.05:raise ValueError(f'第{i+1}格透明背景不足')
        labels,n=ndimage.label(alpha>8);sizes=np.bincount(labels.ravel());sizes[0]=0
        if not n:raise ValueError(f'第{i+1}格空白')
        # 只去極小孤立雜點及碰格邊的鄰格小碎片；主體碰邊必須退件。
        keep=sizes>=max(3,sizes.max()*.0005);keep[0]=False
        for label in np.unique(np.concatenate([labels[0],labels[-1],labels[:,0],labels[:,-1]])):
            if sizes[label]<sizes.max()*.02:keep[label]=False
        if settings.get('isolate_main_character',False):
            keep[:]=False;keep[int(np.argmax(sizes))]=True
        removed=int(((alpha>0)&~keep[labels]).sum());a[:,:,3][~keep[labels]]=0
        edge=int(np.count_nonzero(np.concatenate([a[0,:,3],a[-1,:,3],a[:,0,3],a[:,-1,3]])))
        if edge:raise ValueError(f'第{i+1}格主體碰格邊（{edge}像素）；不得裁掉身體，需修正共同取樣窗或退圖')
        c=Image.fromarray(a);cells.append(c);cleaning.append({'frame':i+1,'source_crop':box,'source_bbox':c.getbbox(),'removed_tiny_pixels':removed,'removed_magenta_fringe_pixels':fringe_count,'edge_pixels':edge})
    boxes=[c.getbbox() for c in cells]
    union=(min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes))
    scale=min(456/(union[2]-union[0]),456/(union[3]-union[1]))
    wh=(round((union[2]-union[0])*scale),round((union[3]-union[1])*scale));origin=((512-wh[0])//2,(512-wh[1])//2)
    frames=[]
    for c in cells:
        f=Image.new('RGBA',(512,512));f.alpha_composite(c.crop(union).resize(wh,Image.Resampling.LANCZOS),origin);frames.append(f)
    geometry={'source_size':im.size,'cell_size':[cw,ch],'source_grid_offset':[dx,dy],'source_cell_padding':[px,py],'union_box':union,'scale_xy':[wh[0]/(union[2]-union[0]),wh[1]/(union[3]-union[1])],'origin':origin,'alignment':'全格共同裁切／縮放／置中，保留側跌位移；非整除分格只透明補齊，不各格拉伸'}
    return frames,geometry,cleaning


def point(xy,g,size=160):
    x,y=xy;ux,uy=g['union_box'][:2];sx,sy=g['scale_xy'];ox,oy=g['origin']
    return [round(((x-ux)*sx+ox)*size/512,2),round(((y-uy)*sy+oy)*size/512,2)]


def verify(path,total):
    im=Image.open(path);elapsed=0;bad=[]
    for i in range(im.n_frames):
        im.seek(i);im.load();elapsed+=im.info.get('duration',0);rgba=im.convert('RGBA')
        if any(rgba.getpixel(p)[3] for p in [(0,0),(im.width-1,0),(0,im.height-1),(im.width-1,im.height-1)]):bad.append(i+1)
    if bad or elapsed!=total:raise ValueError(f'{path}: 四角{bad}，時長{elapsed}/{total}')
    return {'frames':im.n_frames,'duration_ms':elapsed,'bytes':path.stat().st_size,'opaque_corners':bad,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def export(folder,key,revision):
    settings_path=folder/'export_settings.json';settings=json.loads(settings_path.read_text()) if settings_path.exists() else {}
    plan={**PLANS[key],**settings};source=folder/plan['source_filename'];sequence,durations=timing(plan)
    if not sequence or any(f not in range(1,17) for f in sequence) or len(sequence)!=len(durations) or any(d<=0 or d%10 for d in durations):raise ValueError('播放格須在來源1至16內，停留為正10ms倍數；來源16PNG全部保留')
    if sum(durations)!=plan['total_ms']:raise ValueError('時長合計不符規格')
    base,g,cleaning=extract(source,plan)
    output=folder/f'export_{revision}';output.mkdir(parents=True,exist_ok=True);(output/'frames').mkdir(exist_ok=True)
    for i,f in enumerate(base):f.save(output/'frames'/f'{i+1:02d}.png')
    frames=[base[i-1] for i in sequence];small=[f.resize((160,160),Image.Resampling.LANCZOS) for f in frames]
    base[0].save(output/'poster-512.png');save_gif(frames,durations,output/'anim-512.gif')
    frames[0].save(output/'anim-512.webp','WEBP',save_all=True,append_images=frames[1:],duration=durations,loop=0,lossless=True,method=4)
    for quality in [88,80,72,64,56,48]:
        buffer=io.BytesIO();small[0].save(buffer,'WEBP',save_all=True,append_images=small[1:],duration=durations,loop=0,quality=quality,method=4)
        if len(buffer.getvalue())<=81920:break
    (output/'anim.webp').write_bytes(buffer.getvalue());sheet([f.resize((160,160),Image.Resampling.LANCZOS) for f in base],output/'sheet_three_backgrounds.png')
    for name,color in [('magenta','#ff00ff'),('dark','#0e1628'),('light','#f4f7fc')]:
        atlas=Image.new('RGBA',(1024,1120),color);draw=ImageDraw.Draw(atlas)
        for i,f in enumerate(base):
            xy=(i%4*256,i//4*280);atlas.alpha_composite(f.resize((256,256),Image.Resampling.LANCZOS),xy);draw.text((xy[0]+8,xy[1]+260),f'{i+1:02d}',fill='white' if name=='dark' else 'black')
        atlas.save(output/f'qa_{name}.png')
    anchors=[{**a,'canvas512_xy':point(a['source_cell_xy'],g,512),'runtime160_xy':point(a['source_cell_xy'],g)} for a in settings.get('anchors',[])]
    timeline=[];t=0;bodies=settings.get('body_source',[])
    for n,(f,d) in enumerate(zip(sequence,durations)):
        item={'playback_frame':n+1,'source_frame':f,'start_ms':t,'duration_ms':d};t+=d
        support=settings.get('source_support_160',[])
        item['support_160']=support[f-1] if len(support)==16 else None
        for name in ['mouth','nose']:
            anchor=next((a for a in anchors if a['frame']==f and a['name']==name),None);item[name+'_160']=anchor['runtime160_xy'] if anchor else None
        if len(bodies)==16:
            cx,cy,rx,ry,angle=bodies[f-1];sx,sy=g['scale_xy'];item['body160']=[*point([cx,cy],g),round(rx*sx*160/512,2),round(ry*sy*160/512,2),angle]
        else:item['body160']=None
        timeline.append(item)
    contact=next(v['start_ms'] for v in timeline if v['source_frame']==plan['contact_frame'])
    tracks={'file':key,'revision':revision,'ground_y_160':settings.get('ground_y_160',155),'total_ms':t,'contact_ms':contact,'events_ms':settings.get('events_ms',{}),'tracks':timeline,'measurement_note':settings.get('measurement_note','未量錨點以null標示，不可拿總外框猜嘴或靜態錨點掩蓋動圖缺漏')}
    dump(output/'engine_tracks.json',tracks)
    details={'file':key,'version':VERSION,'revision':revision,'output_dir':str(output.relative_to(ROOT)),'source_filename':source.name,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'created_utc':datetime.now(timezone.utc).isoformat(),'source_frames':16,'sequence':sequence,'durations_ms':durations,'total_ms':t,'contact_source_frame':plan['contact_frame'],'contact_ms':contact,'geometry':g,'cleaning':cleaning,'anchors':anchors,'runtime_quality':quality,'runtime_within_80kb':len(buffer.getvalue())<=81920,'visual_review':settings.get('visual_review',{'status':'待三底與瀏覽器動態審片，機器檢查不代表流暢通過'}),'validation':{n:verify(output/n,t) for n in ['anim-512.gif','anim-512.webp','anim.webp']}}
    dump(output/'storyboard.json',details);return details


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,default=ROOT/'docs/anim/bibi_natural3');ap.add_argument('--keys',nargs='+',choices=list(PLANS),default=list(PLANS));ap.add_argument('--revision',default='natural3',help='版本資料夾後綴，舊版不覆寫');args=ap.parse_args();args.source.mkdir(parents=True,exist_ok=True)
    for key in args.keys:
        folder=args.source/key;p=folder/'export_settings.json';settings=json.loads(p.read_text()) if p.exists() else {};filename=settings.get('source_filename',PLANS[key]['source_filename'])
        if not (folder/filename).exists():print(f'尚缺本輪原圖：{key}/{filename}');continue
        d=export(folder,key,args.revision);print(f'{key}：{d["total_ms"]}毫秒，接觸{d["contact_ms"]}毫秒；待人工審片')
    entries=[]
    for key in PLANS:
        p=args.source/key/f'export_{args.revision}'/'storyboard.json'
        if p.exists():entries.append(json.loads(p.read_text()))
    dump(args.source/'manifest.json',{'version':VERSION,'revision':args.revision,'animations':entries,'missing':[k for k in PLANS if k not in {e['file'] for e in entries}]})

if __name__=='__main__':main()
