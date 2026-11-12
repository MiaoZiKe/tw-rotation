# 步驟1：減面。用法 python3 -I s1_simplify.py <in.glb> <outdir> <pipe_dir>
import sys,numpy as np
sys.path.insert(0,sys.argv[3])
from glbio import read_glb
import fast_simplification as fs
js,V,F=read_glb(sys.argv[1])
# 正規化：腳底 y=0、x/z 置中
V=V.copy(); V[:,1]-=V[:,1].min(); 
for name,target in (('hi',30000),('lo',10000)):
    v,f=fs.simplify(V.astype(np.float32),F.astype(np.int32),target_count=target,agg=5)
    v=v.astype(np.float64); f=f.astype(np.int64)
    # 去除退化面
    ok=(f[:,0]!=f[:,1])&(f[:,1]!=f[:,2])&(f[:,0]!=f[:,2]); f=f[ok]
    used=np.unique(f); remap=-np.ones(len(v),int); remap[used]=np.arange(len(used)); v=v[used]; f=remap[f]
    np.savez(f'{sys.argv[2]}/mesh_{name}.npz',V=v,F=f)
    print(name,v.shape,f.shape)
np.savez(f'{sys.argv[2]}/mesh_src.npz',V=V,F=F)
