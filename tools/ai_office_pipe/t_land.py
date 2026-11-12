import sys,numpy as np
sys.path.insert(0,sys.argv[2]); from landmarks import estimate
V=np.load(sys.argv[1])['V']; J,info=estimate(V)
for k,v in info.items(): print(k,v)
for k,v in J.items(): print(k,np.round(v,3))
