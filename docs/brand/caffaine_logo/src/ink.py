import glob,json,os,sys
PFX=sys.argv[1] if len(sys.argv)>1 else 'a'; OUTF=sys.argv[2] if len(sys.argv)>2 else 'ink_report.json'; N=int(sys.argv[3]) if len(sys.argv)>3 else 8
from PIL import Image
import tempfile;base=tempfile.gettempdir()+'/cf_layers/'
def bb(f): return Image.open(f).convert('RGBA').split()[3].point(lambda v:255 if v>20 else 0).getbbox()
def gap(a,b):
    dx=max(b[0]-a[2],a[0]-b[2]); dy=max(b[1]-a[3],a[1]-b[3]); return max(dx,dy)
rows=[];worst=1e9
for i in range(1,N+1):
  for th in ('dark','light'):
    p={k:bb(f'{base}{PFX}{i}_{th}_{k}.png') for k in ('gi','gw','gt')}
    g=(gap(p['gi'],p['gw']),gap(p['gi'],p['gt']),gap(p['gw'],p['gt']))
    worst=min(worst,*g); rows.append((f'{PFX}{i}',th)+g)
    print(f'{PFX}{i} {th}: 圖形-文字標 {g[0]}px, 圖形-標語 {g[1]}px, 文字標-標語 {g[2]}px')
print('最小間距',worst)
json.dump(rows,open(os.path.dirname(os.path.abspath(__file__))+'/'+OUTF,'w'))
