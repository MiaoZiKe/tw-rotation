import numpy as np,sys
d=np.load(sys.argv[1]); m=np.load(sys.argv[2]); V=m['V'];F=m['F']; W=d['W'];R=d['R']
W=W/W.sum(1,keepdims=True)
B=['hips','spine','chest','neck','head','shoulderL','upperArmL','foreArmL','handL','shoulderR','upperArmR','foreArmR','handR','thighL','shinL','footL','thighR','shinR','footR']
arm=W[:,[7,8,11,12]].sum(1); body=W[:,[0,1,13,16,14,17]].sum(1)
bad=(arm>0.1)&(body>0.1); print('mixed',bad.sum()); print(np.round(V[bad][:10],2), R[bad][:10])
# 邊跨區：手臂區與軀幹/腿區直接相鄰的邊
E=np.concatenate([F[:,[0,1]],F[:,[1,2]],F[:,[2,0]]]); ra,rb=R[E[:,0]],R[E[:,1]]
for a,b in ((2,0),(3,0),(2,4),(3,5),(4,5),(2,1),(3,1)):
    mm=((ra==a)&(rb==b)); 
    if mm.any(): P=V[E[mm,0]]; print(a,b,mm.sum(),'y range',P[:,1].min().round(2),P[:,1].max().round(2),'x',P[:,0].min().round(2),P[:,0].max().round(2))
