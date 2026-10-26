"""委員 factor 第二回合驗證：台指期「擇時」對「單純持有」的配對差異檢定。
沿用 futures_levtrend.py 的資料、換月修正與成本（只取其定義段，不改原檔）。
檢定：月報酬差的 t 值、12 個月區塊 bootstrap 的年化差 95% 信賴區間。
用法：在 repo 根目錄 python3 docs/strategy_lab/council/scripts/factor_paired_timing.py"""
import numpy as np
import pandas as pd

src = open('docs/strategy_lab/council/scripts/futures_levtrend.py', encoding='utf-8').read()
exec(src[src.index('import numpy'):src.index('def stat')])

rng = np.random.default_rng(0)


def mret(r):
    return (1 + r.loc['2003-07':]).resample('ME').prod() - 1


pairs = [('F1 200MA 1.5/1.0', dict(L_on=1.5, L_off=1.0), '持有1.2x', dict(L_on=1.2, trend=False)),
         ('F1 200MA 1.5/1.0', dict(L_on=1.5, L_off=1.0), '持有1.36x(同平均曝險)', dict(L_on=1.36, trend=False)),
         ('200MA 1.0/0', dict(L_on=1.0, L_off=0.0), '持有1x', dict(L_on=1.0, trend=False))]
for na, ka, nb, kb in pairs:
    d = (mret(run(**ka)[0]) - mret(run(**kb)[0])).dropna()
    t = d.mean() / d.std(ddof=1) * np.sqrt(len(d))
    v = d.values
    n, B = len(v), 12
    bs = []
    for _ in range(5000):
        st = rng.integers(0, n - B, n // B + 1)
        bs.append(np.concatenate([v[i:i + B] for i in st])[:n].mean() * 12)
    lo, hi = np.percentile(bs, [2.5, 97.5])
    print(f'{na} 減 {nb}: 月數 {n} 年化差(算術) {d.mean() * 1200:+.2f}pt t={t:.2f} '
          f'95%CI [{lo * 100:+.2f},{hi * 100:+.2f}]')
