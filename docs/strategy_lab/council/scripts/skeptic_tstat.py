"""skeptic 第二回合：用實際回測日序列算 t 值（取代第一回合的假設追蹤誤差）。
為什麼：第一回合 S2 的 t 值是用假設的追蹤誤差 20～30% 推的，必須換成實際序列。
做法：日報酬差 d = 策略 - 基準，加總成月資料後算 t（月資料可降低自我相關），另報 Newey-West(6) t。
基準：正二與 TX 用 0050 含息（lev_lab Bench）；S2+投信沿用 chips 口徑（未還原、未含息），
基準也用同口徑的未含息 0050，兩邊都少算股息，超額偏差較小但並非零。
執行：在 repo 根目錄 python3 docs/strategy_lab/council/scripts/skeptic_tstat.py"""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, '.')
from pipeline.compute import lev_lab as L


def report(name, d):
    d = d.dropna()
    m = d.groupby([d.index.year, d.index.month]).sum()
    n = len(m)
    t = m.mean() / m.std(ddof=1) * np.sqrt(n)
    x = m.values - m.mean()
    lag = 6
    g = [x[k:] @ x[:n - k] / n for k in range(lag + 1)]
    v = g[0] + 2 * sum((1 - k / (lag + 1)) * g[k] for k in range(1, lag + 1))
    tnw = m.mean() / np.sqrt(v / n)
    te = m.std(ddof=1) * np.sqrt(12)
    print(f"{name:36s} 月數{n:4d} 年化超額{m.mean()*1200:6.1f}% 追蹤誤差{te*100:5.1f}% "
          f"IR{m.mean()*12/te:5.2f} t{t:5.2f} NW-t{tnw:5.2f}")


w = L.World(with_tx=False, with_mom=False)
b = L.Bench(w)
cal = pd.DatetimeIndex(w.cal)
r50 = pd.Series(b.r, index=cal).iloc[w.start_i:]
cands = {"正二200日線 L2/L2_30": ("MA", dict(n=200, h=0.02, m=1, on="L2", off="L2_30")),
         "正二持有": ("HOLD", dict(w50=0.0, w2=1.0, reb="N"))}
for nm, (f, p) in cands.items():
    r = pd.Series(L.run_key(w, f, p), index=cal).iloc[w.start_i:]
    report(nm + " 對1.5x0050", r - 1.5 * r50)
    report(nm + " 2015起 對1.5x0050", (r - 1.5 * r50).loc['2015':])

src = open('docs/strategy_lab/council/scripts/futures_levtrend.py', encoding='utf-8').read().split("cfgs = [")[0]
ns = {}
exec(src, ns)
for nm, kw in {"TX 持有1.5x": dict(L_on=1.5, trend=False),
               "TX 200MA 1.5/1.0": dict(L_on=1.5, L_off=1.0),
               "TX 持有1.0x": dict(L_on=1.0, trend=False)}.items():
    ret, _ = ns['run'](**kw)
    j = ret.index.intersection(r50.index)
    report(nm + " 對0050", ret.loc[j] - r50.loc[j])

src = open('docs/strategy_lab/council/scripts/chips_rev_trust.py', encoding='utf-8').read().split("def yearly")[0]
ns = {}
exec(src, ns)
C = ns['C']
rb = C['0050'].pct_change().fillna(0)
rb = rb.where(rb.abs() < 0.3, 0)
for mode in ('base', 'trust'):
    rs = ns['run'](mode).pct_change().fillna(0)
    d = (rs - rb).loc['2017':]
    report(f"S2 {mode} 2017起 對0050", d)
    report(f"S2 {mode} 2021起", d.loc['2021':])
    report(f"S2 {mode} 去掉2021年", d[d.index.year != 2021])
    report(f"S2 {mode} 去掉2021年 對1.5x0050", (rs - 1.5 * rb).loc['2017':][lambda s: s.index.year != 2021])
