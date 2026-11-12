import sys,numpy as np,scipy.sparse as sp,scipy.sparse.csgraph as cg
sys.path.insert(0,sys.argv[2])
from glbio import read_glb
js,V,F=read_glb(sys.argv[1])
print(json_nodes:=js.get('nodes'),js.get('scenes'))
print(V.shape,F.shape,V.min(0),V.max(0))
n=len(V);A=sp.coo_matrix((np.ones(len(F)*3),(F.ravel(),np.roll(F,1,1).ravel())),shape=(n,n))
nc,lab=cg.connected_components(A,directed=False)
cnt=np.bincount(lab);print('components',nc,np.sort(cnt)[::-1][:10])
# duplicates
u=np.unique(np.round(V,6),axis=0);print('unique pos',len(u))
