# 複核 rrg 口徑用的一次性腳本（只讀資料湖）。在 repo 根目錄執行：PYTHONPATH=. python docs/research/20261030_rrg_audit/b6.py；依序 b3→b4→b5→b6（b5、b6 讀 b4 的中間檔）。
import pandas as pd, numpy as np
import os; OUT=os.environ.get("RRG_AUDIT_OUT","/tmp/rrg_audit/"); os.makedirs(OUT, exist_ok=True)
gh=pd.read_parquet(OUT+"gh2.parquet"); b=pd.read_parquet(OUT+"bench.parquet")
ds=sorted(gh.date.unique())
latest=ds[-1]; keep=set(gh[(gh.date==latest)&(gh.turnover_share>=0.3)].group_id)
for n in (5,20):
    s=gh[gh.date.isin(ds[-n:])&gh.group_id.isin(keep)]
    c=s.groupby("group_id").apply(lambda g: pd.Series({"cur":((1+g.chg_pct/100).prod()-1)*100,"prev":((1+g.chg_prev/100).prod()-1)*100}))
    d=c.cur-c.prev
    bc=(b["cur"].loc[ds[-1]]/b["cur"].loc[ds[-1-n]]-1)*100; bp=(b["prev"].loc[ds[-1]]/b["prev"].loc[ds[-1-n]]-1)*100
    print(f"{n}日 族群複利報酬 偏差(現−前日權重) 平均 {d.mean():.2f}pp 中位 {d.median():.2f} 最大 {d.max():.2f}；大盤 現 {bc:.2f}% 前日權重 {bp:.2f}%")
    # 排名變動
    print("   排名 Spearman", round(c.cur.rank().corr(c.prev.rank()),3))
