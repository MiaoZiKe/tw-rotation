"""版面檢查：同層元素兩兩不相交、子元素在父卡內、泡泡文字離尾巴>=10px、尾巴尖端離比比12~14px、尾巴為單一路徑（程式合成）"""
import json
H="/home/user/tw-rotation/docs/marketing/post_cpi_1014/"
lay=json.load(open(H+"final/layout.json"))
def inter(a,b): return min(a[2],b[2])-max(a[0],b[0])>0.5 and min(a[3],b[3])-max(a[1],b[1])>0.5
def inside(a,p,tol=0.5): return a[0]>=p[0]-tol and a[1]>=p[1]-tol and a[2]<=p[2]+tol and a[3]<=p[3]+tol
tot=0; rep=[]
for k,d in lay.items():
    els={e["name"]:e for e in d["els"]}; bad=[]
    groups={}
    for e in d["els"]: groups.setdefault(e["parent"],[]).append(e)
    for par,es in groups.items():
        for i in range(len(es)):
            for j in range(i+1,len(es)):
                if inter(es[i]["box"],es[j]["box"]): bad.append(f"重疊 {es[i]['name']} × {es[j]['name']}")
        if par:
            for e in es:
                if not inside(e["box"],els[par]["box"]): bad.append(f"超出父框 {e['name']} ⊄ {par}")
        else:
            for e in es:
                if not inside(e["box"],[24,24,1056,1326]): bad.append(f"超出安全邊界 {e['name']} {e['box']}")
    for t in d["tails"]:
        tb=t["tail"]; ex=[tb[0]-10,tb[1]-10,tb[2]+10,tb[3]+10]; tx=t["text"]
        # 尾巴根部嵌在邊內 6px，文字離尾巴外擴 10px 不得相交
        if inter(ex,tx): bad.append(f"泡泡文字離尾巴<10px {t['bubble']}")
        if "比比" in els:
            b=els["比比"]["box"]
            # 尖端離比比外框距離
            tip=None
            xs=[tb[0],tb[2]]; ys=[tb[1],tb[3]]
            cand=[(x,y) for x in xs for y in ys]
            def dist(p): 
                dx=max(b[0]-p[0],0,p[0]-b[2]); dy=max(b[1]-p[1],0,p[1]-b[3]); return (dx*dx+dy*dy)**.5
            dm=min(dist(p) for p in cand)
            if not (11.5<=dm<=14.5): bad.append(f"尾巴尖端離比比 {dm:.1f}px（應 12~14）{t['bubble']}")
    # 比比大小、頁碼
    rep.append((k,len(d["els"]),bad)); tot+=len(bad)
for k,n,bad in rep:
    print(f"第 {k} 張：登記 {n} 個外框，違規 {len(bad)} 筆"); [print("   ",b) for b in bad]
print(f"程式檢查：{len(rep)} 張，共 {tot} 筆")
