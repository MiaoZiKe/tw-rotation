import sys, importlib, os
sys.path.insert(0, os.path.dirname(__file__))
from kit import *
NAMES={'11':'字母交織 Monogram','12':'裝飾藝術 Art Deco','13':'點陣矩陣','14':'水彩潑墨','15':'台灣老招牌','16':'Y2K 鉻金屬','17':'新粗野主義','18':'3D 立體擠出字','19':'太空軌道','20':'台灣花磚'}
def main(only=None):
    items=[]
    for n in NAMES:
        if only and n not in only: continue
        m=importlib.import_module('m'+n)
        items+=make('G'+n,m)
    # 先存 svg 再轉 png
    for fn,s in items: open(os.path.join(OUT,'svg',fn+'.svg'),'w').write(s)
    shot_svgs(items,OUT)
if __name__=='__main__': main(sys.argv[1:] or None)
