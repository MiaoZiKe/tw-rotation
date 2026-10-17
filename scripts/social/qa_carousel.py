"""可驗證項目與人工美術判斷分開，通過機器檢查不等於可發布。"""
import argparse,json
from pathlib import Path
from PIL import Image
def intersection(a,b):return max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--project',required=True);ap.add_argument('--cover-only',action='store_true');a=ap.parse_args();p=Path(a.project)
 rows=json.loads((p/'qa/layout_boxes.json').read_text(encoding='utf-8'));issues=[];checks=[]
 expected=[1] if a.cover_only else list(range(1,11))
 if [r['page'] for r in rows]!=expected:issues.append('版面記錄頁碼不完整或不連續')
 for r in rows:
  n=r['page'];file=p/f'slides/{n:02d}.png';im=Image.open(file)
  if im.size!=(1080,1350):issues.append(f'{n}頁尺寸錯誤')
  texts=[];pictures=[]
  for b in r['boxes']:
   for bb in b['actual']:
    if bb[0]<64 or bb[1]<64 or bb[2]>1016 or bb[3]>1310:
     # 科技插畫容許55px，文字安全邊距64px
     if b['kind']=='text':issues.append(f'{n}頁文字越過安全邊界：{b["name"]}')
    if bb[0]<0 or bb[1]<0 or bb[2]>1080 or bb[3]>1350:issues.append(f'{n}頁元素超出畫布：{b["name"]}')
    if b['kind']=='text':texts.append((b['name'],bb))
    else:pictures.append((b['name'],bb))
   if b['kind']=='text' and b['font_size']<24:issues.append(f'{n}頁文字小於24px')
  for i,(name,bb) in enumerate(texts):
   for other,ob in texts[i+1:]:
    if intersection(bb,ob)>0:issues.append(f'{n}頁文字重疊：{name}／{other}')
   for other,ob in pictures:
    if intersection(bb,ob)>0:issues.append(f'{n}頁文字壓到插畫預留區：{name}／{other}')
  if not any(b['name']=='page_number' for b in r['boxes']):issues.append(f'{n}頁未記錄頁號')
  for asset in r['assets']:
   lo,hi=asset['alpha_extrema']
   if not (lo<255 and hi>0):issues.append(f'{n}頁資產非有效透明圖：{asset["path"]}')
  checks.append({'page':n,'size':list(im.size),'text_count':len(texts),'illustrations':len(pictures),'bounds_checked':True})
 manual=[{'item':x,'status':'needs_human_review'} for x in ['角色造型一致、無尾巴及多餘肢體','角色與道具200～400%放大接觸合理','科技示意與來源符合、沒有不合理光路','360px手機縮圖閱讀與圖卡精緻度','逐項數字日期單位與來源核對','無第三方浮水印、帳號與Logo','全篇主持動作與視線至少變化兩項']]
 report={'machine_status':'pass' if not issues else 'fail','issues':issues,'pages':checks,'human_review':manual,'release_status':'needs_human_review'}
 (p/'qa/machine_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'machine_status':report['machine_status'],'issues':issues},ensure_ascii=False))
 raise SystemExit(1 if issues else 0)
if __name__=='__main__':main()
