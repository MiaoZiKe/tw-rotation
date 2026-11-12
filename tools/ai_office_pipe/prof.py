import sys,numpy as np
d=np.load(sys.argv[1]);V=d['V']
H=V[:,1].max()
print('H',H)
for y in np.arange(0.02,H,0.04):
    m=np.abs(V[:,1]-y)<0.012
    xs=np.sort(V[m,0]); 
    # runs in x
    gaps=np.where(np.diff(xs)>0.03)[0]
    runs=[];s=0
    for g in list(gaps)+[len(xs)-1]:
        runs.append((round(xs[s],2),round(xs[g],2)));s=g+1
    c=np.abs(V[:,0])<0.05
    zz=V[m&c,2]
    print(f'y={y:.2f} x-runs={runs} z(center)=[{zz.min() if len(zz) else 0:.2f},{zz.max() if len(zz) else 0:.2f}] zall=[{V[m,2].min():.2f},{V[m,2].max():.2f}]')
