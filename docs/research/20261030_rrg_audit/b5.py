# 複核 rrg 口徑用的一次性腳本（只讀資料湖）。在 repo 根目錄執行：PYTHONPATH=. python docs/research/20261030_rrg_audit/b5.py；依序 b3→b4→b5→b6（b5、b6 讀 b4 的中間檔）。
import pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
from pipeline.util import store
from pipeline.compute import rrg
import os; OUT=os.environ.get("RRG_AUDIT_OUT","/tmp/rrg_audit/"); os.makedirs(OUT, exist_ok=True)
gh=pd.read_parquet(OUT+"gh2.parquet"); b=pd.read_parquet(OUT+"bench.parquet")
p = store.read("price_daily", years=[2025,2026]); p["date"]=p["date"].astype(str)
e=p[p.code=="0050"].set_index("date").sort_index(); r50=(e["change"]/(e["close"]-e["change"]))
b["e50"]=(1+r50.reindex(b.index).fillna(0)).cumprod()
def axes(col, bcol, params=(10,40,10)):
    rrg.RS_SMOOTH, rrg.RS_BASE, rrg.MOM_ROC = params
    g=gh.sort_values("date").copy()
    g["gi"]=(1+g[col].fillna(0)/100).groupby(g.group_id).cumprod()
    g["bi"]=g.date.map(b[bcol]); g=g.dropna(subset=["bi"])
    g=rrg.rrg_axes(g,"group_id").dropna(subset=["rs_ratio","rs_mom"])
    g["q"]=[rrg.quadrant_of(x,y) for x,y in zip(g.rs_ratio,g.rs_mom)]
    return g.set_index(["date","group_id"])
A=axes("chg_pct","cur"); B=axes("chg_prev","prev"); C=axes("chg_prev","e50"); D=axes("chg_pct","e50")
latest=gh.date.max(); dates=sorted(gh.date.unique())[-31:]
keep=set(gh[(gh.date==latest)&(gh.turnover_share>=0.3)].group_id)
def agree(X,Y,ds):
    idx=[(d,g) for d in ds for g in keep if (d,g) in X.index and (d,g) in Y.index]
    return round(float(np.mean([X.loc[i,"q"]==Y.loc[i,"q"] for i in idx])),3), len(idx)
print("族群數", len(keep), "最新日", latest)
for nm,Y in (("B 族群+大盤都改前日權重",B),("C 族群前日權重+大盤0050",C),("D 只換大盤0050",D)):
    print(nm, "象限一致率 最新日", agree(A,Y,[latest]), " 近31天", agree(A,Y,dates))
# x 軸水準偏移
for nm,Y in (("B",B),("C",C),("D",D)):
    j=A.loc[[(latest,g) for g in keep if (latest,g) in A.index and (latest,g) in Y.index]]
    k=Y.loc[j.index]; print(nm,"最新日 rs_ratio 平均差(Y−A)", round((k.rs_ratio-j.rs_ratio).mean(),2), "rs_mom", round((k.rs_mom-j.rs_mom).mean(),2))
cnt=lambda X: X.loc[latest].loc[[g for g in keep if g in X.loc[latest].index]].q.value_counts().to_dict()
print("最新日象限分布 A",cnt(A)," B",cnt(B)," C",cnt(C), " D",cnt(D))
# PCB 硬板
names=gh[gh.date==latest].set_index("group_id").group_name
pcb=[g for g,n in names.items() if "硬板" in str(n)]
print("PCB 硬板 id", pcb)
S=axes("chg_prev","prev",(5,20,5)); S0=axes("chg_pct","cur",(5,20,5))
for gid in pcb:
    rows=[]
    for d in dates[-8:]:
        r=gh[(gh.date==d)&(gh.group_id==gid)].iloc[0]
        rows.append((d, round(r.chg_pct,2), round(r.chg_prev,2), A.loc[(d,gid),"q"], B.loc[(d,gid),"q"], S0.loc[(d,gid),"q"], S.loc[(d,gid),"q"]))
    print("日期 漲跌(現) 漲跌(前日權重) 象限A 象限B 短窗(現) 短窗(修)"); [print(x) for x in rows]
# 短週期整體：一日步長與一致率
def step(X):
    X=X.reset_index(); X=X[X.group_id.isin(keep)&X.date.isin(dates)].sort_values(["group_id","date"])
    dx=X.groupby("group_id").rs_ratio.diff(); dy=X.groupby("group_id").rs_mom.diff()
    rad=np.hypot(X.rs_ratio-100,X.rs_mom-100).groupby(X.date).transform("max")
    return round(float((np.hypot(dx,dy)/rad).median()),3)
print("一日步長/盤面半徑 中位：標準", step(B), " 短窗5/20/5", step(S))
# 象限換段頻率
def flips(X):
    X=X.reset_index(); X=X[X.group_id.isin(keep)&X.date.isin(dates)].sort_values(["group_id","date"])
    return round(float((X.groupby("group_id").q.shift()!=X.q).groupby(X.group_id).apply(lambda s:s.iloc[1:].mean()).mean()),3)
print("每日換象限機率：標準", flips(B), " 短窗", flips(S))
# 領先度：前一日象限 → 次日相對報酬（族群前日權重報酬 − 大盤前日權重報酬）
rb=b["prev"].pct_change()*100
def nextday(X):
    X=X.reset_index().sort_values(["group_id","date"])
    X["rel"]=X.chg_prev-X.date.map(rb); X["rel_next"]=X.groupby("group_id").rel.shift(-1)
    X=X[X.group_id.isin(keep)].dropna(subset=["rel_next"])
    return X.groupby("q").rel_next.agg(["mean","count"]).round(3).to_dict("index")
print("前日象限→次日相對報酬 標準", nextday(B)); print("短窗", nextday(S))
