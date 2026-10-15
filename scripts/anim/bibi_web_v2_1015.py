"""比比第二版匯出：共同畫布，保留起跳高度，不覆蓋第一版原始素材。"""
from pathlib import Path
import argparse, hashlib, json, shutil, io
import numpy as np
from PIL import Image, ImageSequence, ImageDraw
from scipy import ndimage
from gif_pipeline import save_gif, save_webp, sheet, verify_gif

ROOT = Path(__file__).resolve().parents[2]
TIMES = {
 'popcorn':[150,110,70,70,90,100,70,110,70,90,110,90,140,180,240,310],
 'selfie':[150,120,110,120,180,200,180,100,90,90,110,110,100,100,100,140],
 'dance':[160,160,150,140,140,150,140,130,140,150,140,130,140,160,180,190],
 'hug':[180,150,130,120,120,110,120,140,180,220,170,140,120,100,90,110],
 'cry':[130,100,100,110,120,130,130,110,100,100,110,120,120,110,100,110],
 'spin_q':[120,100,90,90,90,90,90,90,90,90,90,100,110,120,120,120],
}

def extract(source, metadata):
    im=Image.open(source).convert('RGBA')
    cells=[]
    for i in range(16):
        cell=im.crop((round(i%4*im.width/4),round(i//4*im.height/4),round((i%4+1)*im.width/4),round((i//4+1)*im.height/4)))
        alpha=np.asarray(cell.getchannel('A'))
        if (alpha==0).mean()<.05:
            raise ValueError(f'{source} 第{i+1}格沒有足夠透明背景；不得把背景當角色輸出')
        # 僅去除面積小於最大連通區 0.1% 的孤立雜點，保留分離的腳掌與情緒符號。
        labels,n=ndimage.label(alpha>8)
        sizes=np.bincount(labels.ravel());sizes[0]=0
        keep=sizes>=max(4,sizes.max()*.001);keep[0]=False
        # 切格邊界上的小碎片來自鄰格動態線，排除它們，絕不裁掉主體。
        edge_ids=np.unique(np.concatenate([labels[0],labels[-1],labels[:,0],labels[:,-1]]))
        for component in edge_ids:
            if sizes[component]<sizes.max()*.02:keep[component]=False
        clean=np.array(cell);clean[...,3][~keep[labels]]=0
        cells.append(Image.fromarray(clean).resize((round(im.width/4),round(im.height/4)),Image.Resampling.LANCZOS))
    if len({c.size for c in cells})!=1:
        raise ValueError('分鏡尺寸不可整除為共同4×4畫布')
    # 所有影格使用同一聯集裁切與唯一仿射變換，不能各格對齊腳底。
    boxes=[c.getbbox() for c in cells]
    if any(b is None for b in boxes):raise ValueError('空白影格')
    box=(min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes))
    scale=min(456/(box[2]-box[0]),456/(box[3]-box[1]))
    size=(round((box[2]-box[0])*scale),round((box[3]-box[1])*scale))
    xy=((512-size[0])//2,484-size[1])
    frames=[]
    for cell in cells:
        f=Image.new('RGBA',(512,512));f.alpha_composite(cell.crop(box).resize(size,Image.Resampling.LANCZOS),xy);frames.append(f)
    return frames,{'union_box':box,'scale':scale,'origin':xy,'alignment':'全格共同畫布；保留空中位移'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,default=ROOT/'docs/anim/bibi_web_v2_1015');ap.add_argument('--keys',nargs='*',default=list(TIMES));ap.add_argument('--runtime',action='store_true',help='審核後另行明確啟用覆寫網站檔');a=ap.parse_args()
    manifest=[]
    for key in a.keys:
        folder=a.source/key;source=folder/'source_sheet.png'
        if not source.exists():print(f'尚缺分鏡：{key}');continue
        meta_path=folder/'metadata.json';meta=json.loads(meta_path.read_text()) if meta_path.exists() else {}
        durations=meta.get('durations_ms',TIMES[key]);assert len(durations)==16 and all(v>0 and v%10==0 for v in durations)
        frames,geometry=extract(source,meta)
        out=folder/'frames';out.mkdir(parents=True,exist_ok=True)
        for i,f in enumerate(frames):f.save(out/f'{i+1:02d}.png')
        web=[f.resize((160,160),Image.Resampling.LANCZOS) for f in frames]
        save_gif(frames,durations,folder/'anim-512.gif')
        frames[0].save(folder/'anim-512.webp','WEBP',save_all=True,append_images=frames[1:],duration=durations,loop=0,quality=90,method=3)
        save_gif(web,durations,folder/'anim.gif')
        for quality in [86,78,68]:
            buffer=io.BytesIO();web[0].save(buffer,'WEBP',save_all=True,append_images=web[1:],duration=durations,loop=0,quality=quality,method=4)
            if len(buffer.getvalue())<=81920:break
        (folder/'anim.webp').write_bytes(buffer.getvalue())
        sheet(web,folder/'sheet_three_backgrounds.png')
        atlas=Image.new('RGBA',(640,4*184),'#f4f7fc');draw=ImageDraw.Draw(atlas)
        for i,f in enumerate(web):
            atlas.alpha_composite(f,(i%4*160,i//4*184));draw.text((i%4*160+5,i//4*184+163),f'{i+1:02d} {durations[i]}ms',fill='#352d28')
        atlas.save(folder/'sheet_all.png')
        details={**meta,'file':key,'version':'1015gpt2','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'frames':16,'durations_ms':durations,'total_ms':sum(durations),'geometry':geometry,'transparent':True,'runtime_quality':quality,'runtime_size_limit_bytes':81920}
        checks={}
        for name in ['anim.gif','anim.webp','anim-512.gif','anim-512.webp']:
            file=folder/name;im=Image.open(file);elapsed=0;corners=[]
            for i in range(im.n_frames):
                im.seek(i);im.load();elapsed+=im.info.get('duration',0);rgba=im.convert('RGBA')
                if any(rgba.getpixel(p)[3] for p in [(0,0),(im.width-1,0),(0,im.height-1),(im.width-1,im.height-1)]):corners.append(i)
            assert elapsed==sum(durations),(name,elapsed,sum(durations))
            assert not corners,(name,corners)
            checks[name]={'frames':im.n_frames,'duration_ms':elapsed,'bytes':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'opaque_corners':corners}
        details['validation']=checks
        (folder/'storyboard.json').write_text(json.dumps(details,ensure_ascii=False,indent=2))
        if a.runtime:shutil.copy2(folder/'anim.webp',ROOT/'site/brand/bibi'/f'{key}.webp')
        manifest.append(details)
        print(f'{key}：16格／{sum(durations)}毫秒／透明角落驗證通過')
    # 分批產圖／匯出時合併已完成項，不能讓單項重跑覆寫整份索引。
    by_key={item['file']:item for item in manifest}
    for key in TIMES:
        old=a.source/key/'storyboard.json'
        if key not in by_key and old.exists():by_key[key]=json.loads(old.read_text())
    manifest=[by_key[key] for key in TIMES if key in by_key]
    (a.source/'manifest.json').parent.mkdir(parents=True,exist_ok=True)
    (a.source/'manifest.json').write_text(json.dumps({'version':'1015gpt2','animations':manifest},ensure_ascii=False,indent=2))
    lines=['# 比比網頁互動第二版素材', '', '原始分鏡、提示詞與 metadata 保留於各動作資料夾。所有影格共用裁切與縮放，不逐格重新對齊腳底。', '', '| 動作 | 影格 | 時長（毫秒） | 輸出 |', '|---|---:|---:|---|']
    for item in manifest:
        key=item['file'];lines.append(f"| {key} | 16 | {item['total_ms']} | [透明動畫]({key}/anim.webp)、[逐格檢查]({key}/sheet_all.png) |")
    (a.source/'index.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':main()
