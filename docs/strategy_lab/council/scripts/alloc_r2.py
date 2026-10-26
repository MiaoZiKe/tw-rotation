"""alloc 第二回合：(1) 訊號來源敏感度（TSE vs 0050 未還原 vs 0050 還原含息） (2) 災難停損 (3) 滾動 3／5 年達標率比較。
用 lev_lab.World，訊號 t 收盤、t+1 開盤（shift1）。"""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, ".")
from pipeline.compute import lev_lab as L

w = L.World(with_tx=False, with_mom=False)
b = L.Bench(w)
cal = w.cal
p50 = w.px[w.px.code == "0050"].drop_duplicates("date")
raw50 = pd.Series(p50.close.astype(float).to_numpy(), index=pd.to_datetime(p50.date)).sort_index()
adj50 = pd.Series(w.c50, index=cal) if len(np.atleast_1d(w.c50)) == len(cal) else None
sources = {"TSE加權指數": w.tse_full, "0050未還原收盤": raw50}
if adj50 is not None:
    sources["0050還原含息"] = adj50


def run_state(st, off_w):
    W = L.base_W(len(cal))
    L.fill_W(W, L.shift1(st), L.ON_MODES["L2"], L.OFF_MODES[off_w])
    return L.run(w, W, L.change_flag(W), 0.0)[0]


def cat_state(series, n=200, dd=0.2, look=252):
    s = series.reindex(cal).ffill()
    ma = s.rolling(n).mean(); hi = s.rolling(look).max()
    st = np.ones(len(s)); cur = 1
    for i, (x, m, h) in enumerate(zip(s, ma, hi)):
        if np.isnan(m):
            st[i] = 1; continue
        if cur == 1 and x < m and x < h * (1 - dd):
            cur = 0
        elif cur == 0 and x > m:
            cur = 1
        st[i] = cur
    return st


def roll(r, yrs):
    res = []
    for y in range(2004, 2027 - yrs + 1):
        i0, i1 = L._slice(w, f"{y}-01-01", f"{y+yrs-1}-12-31")
        if i1 - i0 < 200 * yrs:
            continue
        res.append((L.cagr(r[i0:i1]), L.cagr(b.r[i0:i1])))
    return res


def report(nm, r):
    seg = {k: (L.cagr(L.window(w, r, a, bb)), L.cagr(L.window(w, b.r, a, bb))) for k, (a, bb) in {**L.SEGS, "17~20": ("2017-01-01", "2020-12-31")}.items()}
    gaps = " ".join(f"{k}:{(v[0]-1.5*v[1])*100:+.1f}" for k, v in seg.items())
    out = f"{nm:34s} 對1.5x門檻差距(點) {gaps}"
    for yrs in (3, 5):
        rr = roll(r, yrs)
        out += f" | 滾{yrs}年過線 {sum(a >= 1.5*c for a, c in rr)}/{len(rr)} 勝0050 {sum(a > c for a, c in rr)}/{len(rr)}"
    s = L.stats(w, r, L.START)
    out += f" | 全期{s['cagr']*100:.1f}% MDD{s['mdd']*100:.1f}%"
    print(out)


for nm, ser in sources.items():
    n = nm
    st = pd.Series(L._hyst(ser.to_numpy(), ser.rolling(200).mean().to_numpy(), 0.02, 1), index=ser.index).reindex(cal).ffill().fillna(0).to_numpy()
    report(f"MA200±2% 訊號={n} off=L2_30", run_state(st, "L2_30"))
for nm, ser in sources.items():
    report(f"災難停損(MA200且距高點-20%) 訊號={nm}", run_state(cat_state(ser), "L2_30"))
report("00631L 買進持有", L.run_key(w, "HOLD", dict(w50=0.0, w2=1.0, reb="N")))
report("0050 買進持有", b.r)

print("--- 固定比例（月再平衡）：正二 x ＋ 0050 (1-x) ---")
for x in (0.6, 0.7, 0.8, 0.9, 1.0):
    report(f"HOLD 正二{x:.0%}+0050{1-x:.0%} 季再平衡", L.run_key(w, "HOLD", dict(w50=round(1 - x, 2), w2=x, reb="Q")) if x < 1 else L.run_key(w, "HOLD", dict(w50=0.0, w2=1.0, reb="N")))
