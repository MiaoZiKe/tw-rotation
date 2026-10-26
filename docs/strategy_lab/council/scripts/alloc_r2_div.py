"""1 倍台指期輸 0050，是股利還是台積電 beta？拆成：TSE價格報酬 vs 0050價格報酬 vs 0050含息。"""
import sys
sys.path.insert(0, ".")
from pipeline.compute import lev_lab as L

w = L.World(with_tx=False, with_mom=False)
b = L.Bench(w)
tse = w.tse.pct_change().fillna(0).to_numpy()
for nm, (a, z) in {"2013-16": ("2013-01-01", "2016-12-31"), "2017-20": ("2017-01-01", "2020-12-31"),
                   "2021~": ("2021-01-01", None), "2013~": ("2013-01-01", None)}.items():
    t = L.cagr(L.window(w, tse, a, z))
    p = L.price_only_cagr(w, a, z)
    tot = L.cagr(L.window(w, b.r, a, z))
    print(f"{nm}: TSE價格 {t*100:.1f}%  0050價格 {p*100:.1f}%  0050含息 {tot*100:.1f}%  股利貢獻 {(tot-p)*100:.1f}點  0050價格-TSE價格 {(p-t)*100:.1f}點")
