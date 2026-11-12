# 步驟2：綁骨架＋蒙皮權重＋分區上色＋正面投影座標 → 輸出 glb
# 用法：python3 -I s2_build.py <config.json>
import sys,json,struct,os,numpy as np,scipy.sparse as sp,scipy.sparse.linalg as spl,scipy.sparse.csgraph as cg
cfg=json.load(open(sys.argv[1])); sys.path.insert(0,cfg['pipe_dir'])
from landmarks import estimate
from PIL import Image
PARTS=['hair','skin','top','pants','shoes']
BONES=['hips','spine','chest','neck','head','shoulderL','upperArmL','foreArmL','handL','shoulderR','upperArmR','foreArmR','handR','thighL','shinL','footL','thighR','shinR','footR']
PARENT={'hips':None,'spine':'hips','chest':'spine','neck':'chest','head':'neck','shoulderL':'chest','upperArmL':'shoulderL','foreArmL':'upperArmL','handL':'foreArmL','shoulderR':'chest','upperArmR':'shoulderR','foreArmR':'upperArmR','handR':'foreArmR','thighL':'hips','shinL':'thighL','footL':'shinL','thighR':'hips','shinR':'thighR','footR':'shinR'}
END={'hips':'spine','spine':'chest','chest':'neck','neck':'head','head':'head_end','shoulderL':'upperArmL','upperArmL':'foreArmL','foreArmL':'handL','handL':'handL_end','shoulderR':'upperArmR','upperArmR':'foreArmR','foreArmR':'handR','handR':'handR_end','thighL':'shinL','shinL':'footL','footL':'footL_end','thighR':'shinR','shinR':'footR','footR':'footR_end'}
out=cfg['out_dir']; src=np.load(f'{out}/mesh_src.npz')
J,info=estimate(src['V'])
for k,v in cfg.get('joint_override',{}).items(): J[k]=np.array(v,float)
H=info['H']; cx=info['cx']; neck_y=info['neck_y']; crotch=info['crotch']

def vnormals(V,F):
    fn=np.cross(V[F[:,1]]-V[F[:,0]],V[F[:,2]]-V[F[:,0]]); N=np.zeros_like(V)
    for i in range(3): np.add.at(N,F[:,i],fn)
    return N/np.maximum(np.linalg.norm(N,axis=1,keepdims=True),1e-12)
def cotlap(V,F):
    n=len(V); I=[];Jx=[];W=[]
    for i in range(3):
        a,b,c=F[:,i],F[:,(i+1)%3],F[:,(i+2)%3]
        u=V[a]-V[c]; v=V[b]-V[c]
        cot=np.einsum('ij,ij->i',u,v)/np.maximum(np.linalg.norm(np.cross(u,v),axis=1),1e-12)
        cot=np.clip(cot,0.05,8)*0.5
        I+=[a,b];Jx+=[b,a];W+=[cot,cot]
    A=sp.coo_matrix((np.concatenate(W),(np.concatenate(I),np.concatenate(Jx))),shape=(n,n)).tocsr()
    return sp.diags(np.asarray(A.sum(1)).ravel())-A, A
def segdist(P,a,b):
    ab=b-a; t=np.clip(((P-a)@ab)/max(ab@ab,1e-12),0,1); return np.linalg.norm(P-(a+np.outer(t,ab)),axis=1)
def regions(V):
    """0=軀幹 1=頭 2=左臂 3=右臂 4=左腿 5=右腿"""
    R=np.zeros(len(V),int)
    zn=J['head'][2]; R[V[:,1]>neck_y+0.01-cfg.get('chin_slope',0.3)*np.clip(V[:,2]-zn-0.05,0,None)]=1
    for s,n,code in ((1,'L',2),(-1,'R',3)):
        ax=info['armpit'][s][1]; a=info[f'armaxis{n}']
        rel=V-J[f'upperArm{n}']; tt=rel@a; rad=np.linalg.norm(rel-np.outer(tt,a),axis=1)
        Larm=(J[f'hand{n}_end']-J[f'upperArm{n}'])@a
        m=((V[:,0]-ax)*s>0)&(V[:,1]<neck_y)&(tt>0.0)&(tt<Larm*1.08)&(rad<0.2*H/1.96)
        R[m]=code
    R[(V[:,1]<crotch-0.012)&(V[:,0]>cx)&(R==0)]=4
    R[(V[:,1]<crotch-0.012)&(V[:,0]<=cx)&(R==0)]=5
    return R
CAND={0:['hips','spine','chest','neck','shoulderL','shoulderR','thighL','thighR'],1:['head'],
      2:['upperArmL','foreArmL','handL'],3:['upperArmR','foreArmR','handR'],4:['thighL','shinL','footL'],5:['thighR','shinR','footR']}
def skin_weights(V,F,R):
    n=len(V); L,A=cotlap(V,F)
    D=np.full((n,len(BONES)),1e9)
    for r,names in CAND.items():
        m=R==r
        for b in names: D[m,BONES.index(b)]=segdist(V[m],J[b],J[END[b]])
    dmin=D.min(1); near=D<=dmin[:,None]*1.05
    Hd=cfg.get('heat',1.0)/np.maximum(dmin,0.01)**2
    M=(L+sp.diags(Hd)).tocsc(); lu=spl.splu(M)
    W=np.zeros((n,len(BONES)))
    for j in range(len(BONES)):
        if near[:,j].any(): W[:,j]=lu.solve(Hd*near[:,j]/near.sum(1))
    W=np.clip(W,0,None)
    # 關節處再平滑幾輪，讓彎折處不會出現硬摺
    Dg=np.asarray(A.sum(1)).ravel()
    for _ in range(cfg.get('weight_smooth',6)): W=0.5*W+0.5*(A@W)/Dg[:,None]
    # 頭部剛性：臉與頭髮不能被頸部帶著變形
    hi=BONES.index('head'); zn=J['head'][2]; t=np.clip((V[:,1]-(neck_y+0.01-cfg.get('chin_slope',0.3)*np.clip(V[:,2]-zn-0.05,0,None)))/0.05,0,1)[:,None]
    Wh=np.zeros_like(W); Wh[:,hi]=1; W=W*(1-t)+Wh*t*W.sum(1,keepdims=True)
    # 取前四大
    idx=np.argsort(-W,axis=1)[:,:4]; w=np.take_along_axis(W,idx,1); w/=w.sum(1,keepdims=True)
    q=np.floor(w*255+0.5).astype(int); q[:,0]+=255-q.sum(1)
    return idx.astype(np.uint8),q.astype(np.uint8),W
def zbuffer(V,F,res=0.004):
    x0,y0=V[:,0].min()-0.02,V[:,1].min()-0.02
    w=int((V[:,0].max()-x0+0.02)/res)+1; h=int((V[:,1].max()-y0+0.02)/res)+1
    Z=np.full((h,w),-1e9); P=np.stack([(V[:,0]-x0)/res,(V[:,1]-y0)/res],1)
    T=P[F]; zz=V[F,2]
    mn=np.floor(T.min(1)).astype(int); mx=np.ceil(T.max(1)).astype(int)
    for k in range(len(F)):
        a,b,c=T[k]; x_0,y_0=mn[k]; x_1,y_1=mx[k]
        den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den)<1e-12: continue
        xs,ys=np.meshgrid(np.arange(x_0,x_1+1),np.arange(y_0,y_1+1))
        l1=((b[1]-c[1])*(xs-c[0])+(c[0]-b[0])*(ys-c[1]))/den; l2=((c[1]-a[1])*(xs-c[0])+(a[0]-c[0])*(ys-c[1]))/den; l3=1-l1-l2
        m=(l1>=-0.02)&(l2>=-0.02)&(l3>=-0.02)
        if not m.any(): continue
        z=l1*zz[k,0]+l2*zz[k,1]+l3*zz[k,2]
        sub=Z[y_0:y_1+1,x_0:x_1+1]; sub[m]=np.maximum(sub[m],z[m])
    pi=np.clip(np.round(P).astype(int),0,[w-1,h-1])
    return V[:,2]>=Z[pi[:,1],pi[:,0]]-0.015
def load_image():
    im=Image.open(cfg['image']).convert('RGB'); a=np.asarray(im).astype(float); h,w=a.shape[:2]
    white=(a.min(2)>cfg.get('bg_thresh',236))
    import scipy.ndimage as ndi
    lab,_=ndi.label(white); border=np.unique(np.concatenate([lab[0],lab[-1],lab[:,0],lab[:,-1]])); bg=np.isin(lab,border[border>0])
    fg=~bg; rows=np.where(fg.any(1))[0]; yt,yb=rows[0],rows[-1]; hh=yb-yt+1
    ext=lambda r:(np.where(fg[r])[0][0],np.where(fg[r])[0][-1]+1)
    # 圖上的頸：頭頂往下 20%~50% 之間最窄的一列
    cand=[(ext(r)[1]-ext(r)[0],r) for r in range(yt+int(hh*0.2),yt+int(hh*0.5))]; ny=min(cand)[1]
    hc=np.where(fg[yt:ny-1].any(0))[0]; lc=np.where(fg[yb-int(hh*0.3):yb].any(0))[0]
    return a,fg,dict(yt=int(yt),yb=int(yb),ny=int(ny),hx0=int(hc[0]),hx1=int(hc[-1]+1),legc=float((lc[0]+lc[-1]+1)/2),w=w,h=h)
def img_coords(V,R,im):
    """模型座標 → 圖片像素。頭與身體各自對位（圖轉 3D 的比例不會跟原圖一模一樣），頸部附近平滑銜接"""
    hm=R==1; x0,x1=V[hm,0].min(),V[hm,0].max()
    pxh=im['hx0']+(V[:,0]-x0)/(x1-x0)*(im['hx1']-im['hx0']); pyh=im['yt']+(H-V[:,1])/(H-neck_y)*(im['ny']-im['yt'])
    sb=(im['yb']+1-im['ny'])/neck_y
    pxb=im['legc']+(V[:,0]-cx)*sb; pyb=im['ny']+(neck_y-V[:,1])*sb
    t=np.clip((V[:,1]-(neck_y-0.05))/0.1,0,1); t=t*t*(3-2*t)
    return pxb*(1-t)+pxh*t, pyb*(1-t)+pyh*t
def classify(a,fg):
    pal=np.array([cfg['palette'][p] for p in PARTS],float); px=a[fg]
    for it in range(4):
        d=((px[:,None,:]-pal[None])**2).sum(2); l=d.argmin(1)
        for k in range(5):
            if (l==k).sum()>20: pal[k]=0.5*pal[k]+0.5*np.median(px[l==k],axis=0)
    return pal
def ledge(V,N,mask,c,up=(0,1,0),nsec=12,q=50,tol=0.06):
    """找衣服邊緣（下襬、袖口）：法線背向 up 的那圈面。回傳每個頂點所在角度的邊緣高度（沿 up 量），找不到回 None"""
    up=np.array(up,float); up/=np.linalg.norm(up); c=np.array(c,float)
    e1=np.cross(up,[0,0,1.0]); 
    if np.linalg.norm(e1)<0.3: e1=np.cross(up,[1.0,0,0])
    e1/=np.linalg.norm(e1); e2=np.cross(up,e1)
    rel=V-c; hgt=rel@up; th=np.arctan2(rel@e2,rel@e1)
    m=mask&((N@up)<-0.45)
    if m.sum()<12: return None,hgt
    f=(th+np.pi)/(2*np.pi)*nsec; sec=f.astype(int)%nsec
    hy=np.full(nsec,np.nan)
    for k in range(nsec):
        mm=m&(sec==k)
        if mm.sum()>=3: hy[k]=np.percentile(hgt[mm],q)
    if np.isnan(hy).all(): return None,hgt
    med=np.nanmedian(hy); hy[np.abs(hy-med)>tol*H]=np.nan
    idx=np.arange(nsec)+0.5; ok=~np.isnan(hy)
    xs=np.concatenate([idx[ok]-nsec,idx[ok],idx[ok]+nsec]); ys=np.tile(hy[ok],3)
    hy=np.interp(idx,xs,ys); hy=(np.roll(hy,1)+2*hy+np.roll(hy,-1))/4
    return np.interp(f,np.concatenate([idx-nsec,idx,idx+nsec]),np.tile(hy,3)),hgt
def labels(V,F,N,R,A):
    a,fg,im=load_image(); pal=classify(a,fg); n=len(V)
    px,py=img_coords(V,R,im)
    uv=np.stack([px/im['w'],py/im['h']],1)
    ix=np.clip(px.astype(int),0,im['w']-1); iy=np.clip(py.astype(int),0,im['h']-1)
    vis=zbuffer(V,F); infg=fg[iy,ix]
    import scipy.ndimage as ndi
    # 圖上的頭髮：最接近頭髮色的像素，先侵蝕一圈再取最大連通塊（把眼睛、眉毛跟瀏海拆開），再膨脹回來
    d=((a[:,:,None,:]-pal[None,None])**2).sum(3); cls=d.argmin(2); hair=(cls==0)&fg
    er=ndi.binary_erosion(hair,iterations=cfg.get('hair_erode',1)); lb,nl=ndi.label(er)
    if nl: 
        big=np.argmax(np.bincount(lb.ravel())[1:])+1; hair=ndi.binary_dilation(lb==big,iterations=cfg.get('hair_erode',1))&hair
    core=ndi.binary_erosion(fg,iterations=1)[iy,ix]
    lab=-np.ones(n,int); trusted=vis&(N[:,2]>0.3)&core
    m=trusted&(R==1); lab[m]=np.where(hair[iy[m],ix[m]],0,1)
    lab[(R==1)&(V[:,1]>neck_y+0.6*(H-neck_y))&(N[:,2]<0.5)]=0
    lab[(R==1)&(N[:,2]<-0.2)&(V[:,1]>neck_y+0.25*(H-neck_y))]=0
    # 手：手腕平面之外是皮膚
    for s,nm,code in ((1,'L',2),(-1,'R',3)):
        ax_=info[f'armaxis{nm}']; t=(V-J[f'hand{nm}'])@ax_; m=R==code
        cy,hg=ledge(V,N,m&(np.abs(t)<0.05*H),J[f'hand{nm}'],up=-ax_,tol=0.03)
        cut=-cy if cy is not None else np.zeros(n)
        lab[m&(t>cut)]=1; lab[m&(t<=cut)]=2
    # 上衣下襬
    tor=R==0; lab[tor]=2
    lo=(V[:,1]<crotch+0.2*H)
    hy,_=ledge(V,N,(tor|(R>=4))&(V[:,1]>crotch-0.03*H)&(V[:,1]<crotch+0.13*H),(cx,0,J['hips'][2]))
    hem=hy if hy is not None else np.full(n,crotch+0.05*H)
    lab[tor&(V[:,1]<hem)]=3
    info['hem_top']=float(np.median(hem))
    # 褲管與鞋
    for s,nm,code in ((1,'L',4),(-1,'R',5)):
        m=R==code; lab[m]=3
        fy,_=ledge(V,N,m&(V[:,1]>0.045*H)&(V[:,1]<0.2*H),(J[f'foot{nm}'][0],0,J[f'foot{nm}'][2]))
        sh=fy if fy is not None else np.full(n,info[f'shoe_top{nm}'])
        lab[m&(V[:,1]<sh)]=4
    G=A.copy(); ii,jj=G.nonzero(); G=sp.csr_matrix((np.linalg.norm(V[ii]-V[jj],axis=1)+1e-9,(ii,jj)),shape=(n,n))
    def fill(lab):
        srcs=np.where(lab>=0)[0]
        if len(srcs)==n: return lab
        _,_,so=cg.dijkstra(G,indices=srcs,min_only=True,return_predecessors=True)
        return lab[so]
    lab=fill(lab)
    # 人工補筆：config 的 paint = [{"c":[x,y,z],"r":半徑,"part":"skin"}]
    for pt in cfg.get('paint',[]):
        lab[np.linalg.norm(V-np.array(pt['c']),axis=1)<pt['r']]=PARTS.index(pt['part'])
    ALLOW={0:[2,3],1:[0,1],2:[1,2],3:[1,2],4:[3,4],5:[3,4]}
    B=(A>0).astype(float)
    for it in range(cfg.get('label_smooth',3)):
        O=np.stack([B@(lab==k).astype(float)+0.5*(lab==k) for k in range(5)],1)
        for r,al in ALLOW.items():
            m=R==r; mask=np.full(5,-1e9); mask[al]=0; lab[m]=(O[m]+mask).argmax(1)
    # 交界吸附到摺痕：鄰居法線越一致影響越大，跨過摺痕（下襬、袖口、髮際）的影響很小
    ii,jj=A.nonzero(); wn=np.clip((N[ii]*N[jj]).sum(1),0.02,1)**cfg.get('crease_pow',6)
    Bn=sp.csr_matrix((wn,(ii,jj)),shape=(n,n))
    dn=np.asarray(Bn.sum(1)).ravel()
    for rnd in range(cfg.get('crease_rounds',4)):
        O=np.eye(5)[lab]
        for it in range(cfg.get('crease_iter',10)): O=0.5*O+0.5*(Bn@O)/dn[:,None]
        for r,al in ALLOW.items():
            m=R==r; mask=np.full(5,-1e9); mask[al]=0; lab[m]=(O[m]+mask).argmax(1)
    Bc=B.tocsr()
    for k in range(5):
        m=lab==k
        if not m.any(): continue
        sub=Bc[m][:,m]; nc,cl=cg.connected_components(sub,directed=False); cnt=np.bincount(cl)
        keep={0:1,4:2,2:1,3:1}.get(k,None); order=np.argsort(-cnt)
        bad=np.zeros(nc,bool)
        if keep: bad[order[keep:]]=True
        bad|=cnt<max(8,n*cfg.get('island',0.004))
        idx=np.where(m)[0]; lab[idx[bad[cl]]]=-1
    lab=fill(lab)
    faceW=((lab==1)&(R==1)&vis&(N[:,2]>0.4)).astype(float)
    projW=(vis&infg).astype(float)*np.clip((N[:,2]-0.15)/0.35,0,1)
    return lab,uv,faceW,projW,pal,im
def smooth(A,X,it=2,lam=0.5):
    Dg=np.asarray(A.sum(1)).ravel(); 
    for _ in range(it): X=(1-lam)*X+lam*(A@X)/Dg[:,None]
    return X
def write_glb(path,V,F,N,ji,jw,PA,PB,uv,col):
    bufs=[];views=[];accs=[]
    def add(arr,ctype,typ,norm=False,target=None,minmax=False):
        b=arr.tobytes(); off=sum(len(x) for x in bufs); pad=(-len(b))%4; bufs.append(b+b'\0'*pad)
        v={'buffer':0,'byteOffset':off,'byteLength':len(b)}
        if target: v['target']=target
        views.append(v); a={'bufferView':len(views)-1,'componentType':ctype,'count':len(arr),'type':typ}
        if norm: a['normalized']=True
        if minmax: a['min']=arr.min(0).tolist(); a['max']=arr.max(0).tolist()
        accs.append(a); return len(accs)-1
    at={'POSITION':add(V.astype('<f4'),5126,'VEC3',target=34962,minmax=True),'NORMAL':add(N.astype('<f4'),5126,'VEC3',target=34962),
        'TEXCOORD_0':add(uv.astype('<f4'),5126,'VEC2',target=34962),'COLOR_0':add(col,5121,'VEC4',True,34962),
        'JOINTS_0':add(ji,5121,'VEC4',target=34962),'WEIGHTS_0':add(jw,5121,'VEC4',True,34962),
        '_PARTA':add(PA,5121,'VEC4',True,34962),'_PARTB':add(PB,5121,'VEC4',True,34962)}
    idx=add(F.astype('<u2').reshape(-1,1) if len(V)<65536 else F.astype('<u4').reshape(-1,1),5123 if len(V)<65536 else 5125,'SCALAR',target=34963)
    ibm=np.zeros((len(BONES),4,4),'<f4')
    for i,b in enumerate(BONES): ibm[i]=np.eye(4); ibm[i][3,:3]=-J[b]   # 欄優先
    ib=add(ibm.reshape(len(BONES),16),5126,'MAT4')
    nodes=[{'name':'rig','children':[1,2]},{'name':'body','mesh':0,'skin':0}]
    for b in BONES:
        p=PARENT[b]; t=J[b]-(J[p] if p else 0)
        nodes.append({'name':b,'translation':[float(x) for x in t]})
    for i,b in enumerate(BONES):
        ch=[2+k for k,c in enumerate(BONES) if PARENT[c]==b]
        if ch: nodes[2+i]['children']=ch
    js={'asset':{'version':'2.0','generator':'office-rig-pipeline'},'scene':0,'scenes':[{'nodes':[0]}],'nodes':nodes,
        'meshes':[{'primitives':[{'attributes':at,'indices':idx,'material':0}]}],
        'materials':[{'name':'body','pbrMetallicRoughness':{'baseColorFactor':[1,1,1,1],'metallicFactor':0,'roughnessFactor':0.8}}],
        'skins':[{'joints':[2+i for i in range(len(BONES))],'inverseBindMatrices':ib,'skeleton':2}],
        'accessors':accs,'bufferViews':views,'buffers':[{'byteLength':sum(len(x) for x in bufs)}]}
    jb=json.dumps(js,separators=(',',':')).encode(); jb+=b' '*((-len(jb))%4); bb=b''.join(bufs)
    with open(path,'wb') as f:
        f.write(struct.pack('<4sII',b'glTF',2,12+8+len(jb)+8+len(bb))); f.write(struct.pack('<II',len(jb),0x4E4F534A)); f.write(jb)
        f.write(struct.pack('<II',len(bb),0x004E4942)); f.write(bb)
meta=None
for lod in ('hi','lo'):
    d=np.load(f'{out}/mesh_{lod}.npz'); V,F=d['V'],d['F']; N=vnormals(V,F); R=regions(V)
    ji,jw,Wfull=skin_weights(V,F,R)
    L,A=cotlap(V,F)
    lab,uv,faceW,projW,pal,im=labels(V,F,N,R,A)
    B=(A>0).astype(float)
    ind=np.stack([(lab==k).astype(float) for k in range(5)],1)
    X=smooth(B,np.concatenate([ind,projW[:,None],faceW[:,None]],1),it=cfg.get('part_smooth',2))
    PA=np.round(X[:,:4]*255).astype(np.uint8); PB=np.round(np.stack([X[:,4],X[:,5],X[:,6],np.zeros(len(V))],1)*255).astype(np.uint8)
    col=np.concatenate([pal[lab],np.full((len(V),1),255)],1).round().astype(np.uint8)
    write_glb(f"{out}/{cfg['name']}_{lod}.glb",V,F,N,ji,jw,PA,PB,uv,col)
    np.savez(f'{out}/dbg_{lod}.npz',lab=lab,R=R,W=Wfull,uv=uv)
    print(lod,len(V),len(F),'parts',np.bincount(lab,minlength=5),'size',os.path.getsize(f"{out}/{cfg['name']}_{lod}.glb"))
    if lod=='hi':
        meta={'name':cfg['name'],'height':H,'bones':BONES,'joints':{k:[round(float(x),4) for x in v] for k,v in J.items()},
              'palette':{p:[int(round(c)) for c in pal[i]] for i,p in enumerate(PARTS)},
              'proj':im,'hem_top':info.get('hem_top'),
              'neck_y':neck_y,'crotch':crotch,'cx':cx}
json.dump(meta,open(f"{out}/{cfg['name']}.meta.json",'w'),ensure_ascii=False,indent=1)
print(json.dumps(meta['palette']))
