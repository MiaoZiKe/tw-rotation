# 複核 rrg 口徑用的一次性腳本（只讀資料湖）。在 repo 根目錄執行：PYTHONPATH=. python docs/research/20261030_rrg_audit/b3.py；依序 b3→b4→b5→b6（b5、b6 讀 b4 的中間檔）。
import pandas as pd, numpy as np
import os; os.makedirs("/tmp/rrg_audit", exist_ok=True)
from pipeline.util import store
from pipeline.util.roc import is_tradable_security, is_etf
from pipeline.compute import rrg
p = store.read("price_daily", years=[2025, 2026])
ix = store.read("index_daily")
tw = ix[ix["index"].isin(["發行量加權股價指數"])].copy()
print("TAIEX rows", len(tw), tw.date.min(), tw.date.max())
tw["date"]=tw["date"].astype(str); tw=tw.set_index("date")["change_pct"]/100
bench = rrg.market_index(p)
bench.index = bench.index.astype(str)
r_cur = bench.pct_change()
# 第一天 pct_change NaN；直接重算日報酬
px = p.copy(); px["date"]=px["date"].astype(str)
px = px[px["code"].map(is_tradable_security)]
px["turnover"]=pd.to_numeric(px["turnover"],errors="coerce").fillna(0)
prev = px["close"]-px["change"].fillna(0)
px["chg"]=np.where(prev>0, px["change"]/prev, np.nan)
px=px.dropna(subset=["chg"]).sort_values(["code","date"])
px["tv_prev"]=px.groupby("code")["turnover"].shift(1)
px["mcap_proxy"]=prev  # 無股數 → 只做價格加權不可用；略
def wavg(g,col): 
    w=g[col].fillna(0); return float((g["chg"]*w).sum()/w.sum()) if w.sum()>0 else np.nan
cut = bench.index[-200] if len(bench)>200 else bench.index[0]
q = px[px["date"]>=cut]
res = pd.DataFrame({
 "cur": q.groupby("date").apply(lambda g: wavg(g,"turnover")),
 "prevtv": q.groupby("date").apply(lambda g: wavg(g,"tv_prev")),
 "eq": q.groupby("date")["chg"].mean(),
 "cur_noetf": q[~q["code"].map(is_etf)].groupby("date").apply(lambda g: wavg(g,"turnover")),
})
res["taiex"]=tw.reindex(res.index)
res=res.dropna(subset=["taiex"])
print("共同天數", len(res), res.index.min(), res.index.max())
for n in (len(res), 120, 60, 32):
    s=res.tail(n)
    print(f"\n近{n}天 平均日報酬(%)：", (s.mean()*100).round(3).to_dict())
    print("  與TAIEX差 平均(%)：", ((s.drop(columns='taiex').sub(s['taiex'],axis=0)).mean()*100).round(3).to_dict())
    print("  相關：", s.corr()["taiex"].round(3).to_dict())
    print("  複利累積(%)：", (((1+s).prod()-1)*100).round(2).to_dict())
res.to_csv("/tmp/rrg_audit/daily.csv")
