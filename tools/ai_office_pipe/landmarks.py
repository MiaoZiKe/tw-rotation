# 依幾何估關節位置。輸入：高面數頂點 V（腳底 y=0、面向 +Z、A 字站姿）
import numpy as np
def runs_at(V,y,tol=0.012,gap=0.03):
    m=np.abs(V[:,1]-y)<tol
    xs=np.sort(V[m,0]); 
    if len(xs)==0: return []
    cut=np.where(np.diff(xs)>gap)[0]; out=[];s=0
    for g in list(cut)+[len(xs)-1]:
        if g-s>=3: out.append((xs[s],xs[g]))
        s=g+1
    return out
def slice_c(V,y,x0,x1,tol=0.015):
    m=(np.abs(V[:,1]-y)<tol)&(V[:,0]>=x0)&(V[:,0]<=x1)
    P=V[m]; return np.array([(P[:,0].min()+P[:,0].max())/2,y,(P[:,2].min()+P[:,2].max())/2])
def estimate(V,log=print):
    H=V[:,1].max(); J={}; info={'H':H}
    ys=np.arange(0.05*H,0.6*H,0.004)
    # 胯下：由下往上，第一個「兩腿合成一段」的高度
    crotch=None
    for y in ys:
        r=[q for q in runs_at(V,y) if q[1]-q[0]>0.08*H*0.5]
        big=[q for q in r if q[1]-q[0]>0.05]
        if crotch is None and len(big)>=2: last=big; continue
        if len(big)>=1 and 'last' in dir() and crotch is None:
            # 合併的判定：有一段同時蓋住之前兩腿
            l0,l1=sorted(last,key=lambda q:q[0])[:2] if len(last)>=2 else (None,None)
            for q in big:
                if l0 and q[0]<=l0[1] and q[1]>=l1[0]: crotch=y;legs=(l0,l1)
        if crotch: break
    cx=(legs[0][1]+legs[1][0])/2
    info.update(crotch=crotch,cx=cx)
    # 腋下：由胯往上，手臂那段與軀幹合併的高度
    arm={}
    for s in (1,-1):
        prev=None
        for y in np.arange(crotch+0.02,0.8*H,0.004):
            r=runs_at(V,y); tor=[q for q in r if q[0]<=cx<=q[1]]
            if not tor: continue
            tor=tor[0]
            side=[q for q in r if (q[0]-cx)*s>0 and (q[1]-cx)*s>0]
            if side: prev=(y,(tor[1]+min(q[0] for q in side))/2 if s>0 else (tor[0]+max(q[1] for q in side))/2)
            elif prev and y-prev[0]<0.02: arm[s]=prev; break
    info['armpit']={s:arm[s] for s in arm}
    apy=max(arm[1][0],arm[-1][0])
    # 頸：腋下以上、0.85H 以下，全寬最窄處
    best=None
    for y in np.arange(apy+0.1,0.85*H,0.004):
        r=runs_at(V,y); 
        if not r: continue
        w=r[-1][1]-r[0][0]
        if best is None or w<best[0]: best=(w,y,r[0][0],r[-1][1])
    neck_y=best[1]; info['neck_y']=neck_y; info['neck_w']=best[0]
    def zc(y,hw):
        return slice_c(V,y,cx-hw,cx+hw)[2]
    hipy=crotch+0.035*H
    J['hips']=np.array([cx,hipy,zc(hipy,0.1)])
    sp1=hipy+(neck_y-hipy)*0.30; sp2=hipy+(neck_y-hipy)*0.62; nk=neck_y-0.07*(neck_y-hipy)*2
    J['spine']=np.array([cx,sp1,zc(sp1,0.1)]); J['chest']=np.array([cx,sp2,zc(sp2,0.1)])
    # 頸與頭的 z：取頸部切片的中心，稍微偏後
    m=(np.abs(V[:,1]-neck_y)<0.02); zn=(V[m,2].min()+V[m,2].max())/2
    J['neck']=np.array([cx,nk,(J['chest'][2]+zn)/2]); J['head']=np.array([cx,neck_y+0.02,zn])
    J['head_end']=np.array([cx,H,zn])
    for s,n in ((1,'L'),(-1,'R')):
        ay,ax=arm[s]
        m=((V[:,0]-ax)*s>0)&(V[:,1]<neck_y)&(V[:,1]>crotch-0.1)
        P=V[m]; c=P.mean(0); u,sv,vt=np.linalg.svd(P-c,full_matrices=False); ax_=vt[0]
        if ax_[0]*s<0: ax_=-ax_
        t=(P-c)@ax_; tip_t=t.max()
        # 肩：軸線穿過 x=ax 往內 0.035H 的地方
        ts=((ax-s*0.02*H)-c[0])/ax_[0]; sh=c+ax_*ts
        L=tip_t-ts
        # 半徑剖面找手腕（袖口之後最細處）
        tt=(t-ts)/L; rad=np.linalg.norm((P-c)-np.outer(t,ax_),axis=1)
        prof=[]
        for a in np.arange(0.3,0.98,0.02):
            mm=np.abs(tt-a)<0.02
            prof.append((a,np.percentile(rad[mm],90) if mm.sum()>5 else 9))
        info[f'armprof{n}']=[(round(a,2),round(r,3)) for a,r in prof]
        # 袖口鬆緊帶是 0.65~0.9 之間最粗處；手腕取袖口之後半徑掉到 80% 以下的第一點
        ck=max((r,a) for a,r in prof if 0.68<=a<=0.9); wa=None
        for a,r in prof:
            if a>ck[1] and r<0.8*ck[0]: wa=a;break
        if wa is None or wa>0.9: wa=0.8
        wa-=0.01
        # 袖口（手腕之前最粗處）到手腕的落差太小就用比例
        info[f'wrist_t{n}']=wa
        wr=sh+ax_*L*wa; el=sh+ax_*L*wa*0.48; tip=sh+ax_*L
        J[f'shoulder{n}']=np.array([cx+s*abs(ax-cx)*0.35,sh[1]+0.02*H,sh[2]])
        J[f'upperArm{n}']=sh; J[f'foreArm{n}']=el; J[f'hand{n}']=wr; J[f'hand{n}_end']=tip; info[f'armaxis{n}']=ax_
        # 腿
        lg=legs[1] if s>0 else legs[0]
        x0,x1=(cx,cx+0.6) if s>0 else (cx-0.6,cx)
        # 鞋頂：腳尖往前凸出消失的高度
        zmax=lambda y:V[(np.abs(V[:,1]-y)<0.01)&(V[:,0]>=x0)&(V[:,0]<=x1),2].max()
        ref=np.median([zmax(y) for y in np.arange(0.12*H,0.25*H,0.01)])
        shoe=0.03*H
        for y in np.arange(0.12*H,0.01,-0.004):
            if zmax(y)>ref+0.05: shoe=y;break
        info[f'shoe_top{n}']=shoe
        anky=shoe+0.015*H
        hp=slice_c(V,crotch-0.03,x0,x1); hp[1]=crotch+0.02*H; hp[0]=cx+(hp[0]-cx)*0.9
        ak=slice_c(V,anky,x0,x1); 
        ky=anky+(hp[1]-anky)*0.5; kn=slice_c(V,ky,x0,x1)
        m=(V[:,1]<shoe)&(V[:,0]>=x0)&(V[:,0]<=x1); toe=np.array([ak[0],0.02*H,V[m,2].max()])
        ak[2]=min(ak[2],kn[2]+0.0)
        J[f'thigh{n}']=hp; J[f'shin{n}']=kn; J[f'foot{n}']=ak; J[f'foot{n}_end']=toe
    return J,info
