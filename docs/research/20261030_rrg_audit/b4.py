# 複核 rrg 口徑用的一次性腳本（只讀資料湖）。在 repo 根目錄執行：PYTHONPATH=. python docs/research/20261030_rrg_audit/b4.py；依序 b3→b4→b5→b6（b5、b6 讀 b4 的中間檔）。
import pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
from pipeline.util import store
from pipeline.compute import rrg, flow, fundamental
from pipeline.util.roc import is_tradable_security
import os; OUT=os.environ.get("RRG_AUDIT_OUT","/tmp/rrg_audit/"); os.makedirs(OUT, exist_ok=True)
p = store.read("price_daily", years=[2025, 2026]); p["date"]=p["date"].astype(str)
p = fundamental.clean_price(p)
p = p[p["date"]<="2026-10-29"]   # 10-30 尚未完整，對齊 index_daily
company = store.read("company_info")
gh = flow.group_daily(p, company)
# 前一日成交值加權的族群漲跌：重現 group_daily 的拆分邏輯
df = flow._attach_groups(p, company)
df["turnover"]=pd.to_numeric(df["turnover"],errors="coerce").fillna(0)
df=df.sort_values(["code","group_id","date"])
df["prev_close"]=df["close"]-df["change"].fillna(0)
df["chg_pct"]=np.where(df["prev_close"]>0, df["change"]/df["prev_close"]*100, np.nan)
tvp = df.groupby(["code","group_id"])["turnover"].shift(1)*df["weight"]
ww = tvp.where(df["chg_pct"].notna(),0).fillna(0)
t = pd.DataFrame({"date":df["date"],"group_id":df["group_id"],"w":ww,"cw":df["chg_pct"].fillna(0)*ww})
a = t.groupby(["date","group_id"]).sum()
alt = (a["cw"]/a["w"].replace(0,np.nan)).rename("chg_prev").reset_index()
gh2 = gh.merge(alt,on=["date","group_id"],how="left")
gh2["bias"]=gh2["chg_pct"]-gh2["chg_prev"]
last60 = sorted(gh2.date.unique())[-120:]
s = gh2[gh2.date.isin(last60)]
print("族群日漲跌偏差（當日權重 − 前日權重，百分點）：近120天 平均", round(s.bias.mean(),3), "中位", round(s.bias.median(),3),
      "p90", round(s.bias.quantile(.9),3), "p10", round(s.bias.quantile(.1),3))
gb = s.groupby("group_name")["bias"].mean().sort_values()
print("最偏高族群:", gb.tail(5).round(3).to_dict()); print("最偏低:", gb.head(3).round(3).to_dict())
gh2.to_parquet(OUT+"gh2.parquet")
# 大盤三種
b_cur = rrg.market_index(p)
px = p[p["code"].map(is_tradable_security)][["date","code","close","change","turnover"]].copy()
px["turnover"]=pd.to_numeric(px["turnover"],errors="coerce").fillna(0)
prev=px["close"]-px["change"].fillna(0); px["chg"]=np.where(prev>0,px["change"]/prev,np.nan)
px=px.sort_values(["code","date"]); px["tvp"]=px.groupby("code")["turnover"].shift(1)
px=px.dropna(subset=["chg","tvp"])
r_prev = px.groupby("date").apply(lambda g: float((g.chg*g.tvp).sum()/g.tvp.sum()) if g.tvp.sum()>0 else 0.0)
b_prev = (1+r_prev).cumprod()
# 0050 當長期市值加權代理
e = p[p.code=="0050"].set_index("date"); r50 = e["change"]/(e["close"]-e["change"])
r_cur = b_cur.pct_change()
cmp = pd.DataFrame({"cur":r_cur,"prev":r_prev,"0050":r50}).dropna()
for n in (len(cmp),120,60):
    q=cmp.tail(n)
    print(f"近{n}天({q.index.min()}~) 日均%:",(q.mean()*100).round(3).to_dict(),"複利%:",(((1+q).prod()-1)*100).round(1).to_dict(),
          "相關(對0050):",q.corr()["0050"].round(3).to_dict())
pd.DataFrame({"cur":b_cur,"prev":b_prev}).to_parquet(OUT+"bench.parquet")
# 機制：同日 成交值變化(對前日) 與 報酬 的橫斷面相關
px["dtv"]=np.log(px.turnover.replace(0,np.nan)/px.tvp.replace(0,np.nan))
q=px[px.date>=last60[0]].dropna(subset=["dtv"])
cc=q.groupby("date").apply(lambda g: g["dtv"].corr(g["chg"]))
print("橫斷面 corr(當日成交值/前日 的 log, 當日報酬) 平均", round(cc.mean(),3), "正的天數比例", round((cc>0).mean(),3))
up=q[q.chg>0.02]; dn=q[q.chg<-0.02]
print("漲>2% 成交值中位倍數(對前日)", round(np.exp(up.dtv.median()),2), " 跌>2%", round(np.exp(dn.dtv.median()),2))
