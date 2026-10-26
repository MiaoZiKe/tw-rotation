"""alloc 立場書補證據：只讀 lev_lab 的 World，不改既有檔。
問題：(1) 200MA+正二這套在「每一年／每個滾動3年」是否都贏 0050x1.5？ (2) 凱利槓桿多大？
(3) 趨勢濾網的 off 狀態改持 0050（而非現金／30%正二）會怎樣？"""
import sys
import numpy as np
sys.path.insert(0, ".")
from pipeline.compute import lev_lab as L

w = L.World(with_tx=False, with_mom=False)
b = L.Bench(w)


def yr_gaps(r):
    out = {}
    for y in range(2004, 2027):
        i0, i1 = L._slice(w, f"{y}-01-01", f"{y}-12-31")
        if i1 - i0 < 100:
            continue
        out[y] = (L.cagr(r[i0:i1]), L.cagr(b.r[i0:i1]))
    return out


def roll(r, yrs=3):
    res = []
    for y in range(2004, 2027 - yrs + 1):
        i0, i1 = L._slice(w, f"{y}-01-01", f"{y+yrs-1}-12-31")
        if i1 - i0 < 200 * yrs:
            continue
        res.append((y, L.cagr(r[i0:i1]), L.cagr(b.r[i0:i1])))
    return res


cands = {
    "0050": ("HOLD", dict(w50=1.0, w2=0.0, reb="N")),
    "00631L持有": ("HOLD", dict(w50=0.0, w2=1.0, reb="N")),
    "MA200 off=L2_30": ("MA", dict(n=200, h=0.02, m=1, on="L2", off="L2_30")),
    "MA200 off=L2_80": ("MA", dict(n=200, h=0.02, m=1, on="L2", off="L2_80")),
    "MA200 off=0050": ("MA", dict(n=200, h=0.02, m=1, on="L2", off="50")),
    "MA200 on=L2_70 off=0050": ("MA", dict(n=200, h=0.02, m=1, on="L2_70", off="50")),
    "MA200 on=L2_50 off=0050": ("MA", dict(n=200, h=0.02, m=1, on="L2_50", off="50")),
    "MA200 on=L2_50 off=half50": ("MA", dict(n=200, h=0.02, m=1, on="L2_50", off="half50")),
}
for nm, (f, p) in cands.items():
    r = L.run_key(w, f, p)
    rows = roll(r)
    yg = yr_gaps(r)
    n_y_win = sum(1 for y, (a, c) in yg.items() if a > c)
    worst3 = min(rows, key=lambda t: t[1] - 1.5 * t[2])
    pass3 = sum(1 for t in rows if t[1] >= 1.5 * t[2])
    seg = {k: L.cagr(L.window(w, r, a, bb)) for k, (a, bb) in L.SEGS.items()}
    full = L.stats(w, r, L.START)
    wy = min(yg.items(), key=lambda kv: kv[1][0] - kv[1][1])
    print(f"{nm:28s} 全期{full['cagr']*100:5.1f}% MDD{full['mdd']*100:6.1f}% 夏普{full['sharpe']:.2f} | "
          f"A{seg['A 2003-07~2014']*100:5.1f} B{seg['B 2015~2020']*100:5.1f} C{seg['C 2021~']*100:5.1f} | "
          f"滾動3年過1.5x {pass3}/{len(rows)} 最差窗{worst3[0]}~{worst3[0]+2}:{worst3[1]*100:.1f}% vs 0050 {worst3[2]*100:.1f}% | "
          f"贏0050年數 {n_y_win}/{len(yg)} 最差年{wy[0]} {wy[1][0]*100:.0f}% vs {wy[1][1]*100:.0f}%")

r50 = b.r[w.start_i:]
rf = w.rf[w.start_i:] / 252
ex = r50 - rf
mu, var = ex.mean() * 252, ex.var() * 252
print(f"0050 超額年化 {mu*100:.1f}% 年化波動 {np.sqrt(var)*100:.1f}% 凱利槓桿 f*=mu/var={mu/var:.2f}，半凱利 {mu/var/2:.2f}")
for lev in (1, 1.5, 2, 2.5, 3):
    rr = rf + lev * ex - (lev - 1) * 0.006 / 252
    print(f"  固定{lev}倍0050(日再平衡，借款利差0.6%): 年化{L.cagr(rr)*100:.1f}% MDD{L.mdd(rr)[0]*100:.1f}%")
