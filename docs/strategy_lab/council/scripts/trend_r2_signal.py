"""trend 第二回合：補驗 r1 第 6 節的驗證 1（訊號來源敏感度）與驗證 2（災難停損，僅真實 ETF 段）。

為什麼：r1 用 0050 收盤當 200MA 訊號得 B 段 -11.0，lev_lab 用加權指數得 +2.9，差 14 點。
要分清楚是「訊號來源」造成，還是我 r1 的引擎（開盤到開盤）與 lev_lab 不同造成。
因此同一引擎下，只換訊號來源：加權指數 TSE、0050 未還原（含除息缺口）、0050 含息還原。
另跑災難停損：週收盤 < 40 週均線 且 自 52 週高點回落 > 20%，才降到 30% 正二；週收盤站回 40 週線就回 100%。
口徑同 trend_weekly_l2.py（真實 ETF、0050 含息、拆分以單日 |報酬|>40% 偵測、開盤換倉、扣成本、現金 1%）。
"""
import glob
import numpy as np
import pandas as pd

exec(open('docs/strategy_lab/council/scripts/trend_weekly_l2.py').read().split('# 1) 買進持有正二')[0])

ix = pd.concat(map(pd.read_parquet, glob.glob('data/index_ohlc/**/*.parquet', recursive=True)))
ix = ix[ix.symbol == 'TSE'].copy()
ix['date'] = pd.to_datetime(ix.date)
tse = ix.drop_duplicates('date').set_index('date').close.sort_index().reindex(c.index).ffill()

# 0050 含息還原收盤（往前把股利扣回，等同總報酬指數）
tr = (c['0050'] / c['0050'].shift(1) + (div / c['0050'].shift(1)).fillna(0)).fillna(1).cumprod()


def ma_switch(sig, n=200, h=0.02, off=0.3):
    ma = sig.rolling(n).mean()
    st, s = [], 1.0
    for p, m in zip(sig, ma):
        if not np.isnan(m):
            if p > m * (1 + h): s = 1.0
            elif p < m * (1 - h): s = off
        st.append(s)
    return pd.Series(st, index=sig.index).shift(1)


def disaster(sig, off=0.3):
    wk = sig.resample('W-FRI').last().dropna()
    wma = wk.rolling(40).mean()
    hi52 = wk.rolling(52, min_periods=20).max()
    st, s = [], 1.0
    for p, m, h in zip(wk, wma, hi52):
        if not np.isnan(m):
            if p < m and p < h * 0.8: s = off
            elif p > m: s = 1.0
        st.append(s)
    return pd.Series(st, index=wk.index).reindex(sig.index, method='ffill').shift(1)


segs = {'B 2015~2020': ('2015-01-01', '2020-12-31'), '2017~2020': ('2017-01-01', '2020-12-31'),
        'C 2021~': ('2021-01-01', '2100-01-01'), '2018~2020': ('2018-01-01', '2020-12-31'),
        '2022~2024': ('2022-01-01', '2024-12-31')}


def stats(r, a, b):
    r = r[(r.index >= a) & (r.index <= b)]
    eq = (1 + r).cumprod()
    return eq.iloc[-1] ** (252 / len(r)) - 1, (eq / eq.cummax() - 1).min()


base = r50.dropna()
rows = []
cands = [('買進持有正二', pd.Series(1.0, index=c.index)),
         ('200MA±2% 訊號=加權指數', ma_switch(tse)),
         ('200MA±2% 訊號=0050未還原', ma_switch(c['0050'])),
         ('200MA±2% 訊號=0050含息還原', ma_switch(tr)),
         ('200MA 無遲滯 訊號=加權指數', ma_switch(tse, h=0.0)),
         ('災難停損 訊號=加權指數', disaster(tse)),
         ('災難停損 訊號=0050含息還原', disaster(tr))]
for name, w in cands:
    r = run(w)
    line = [name]
    for sn, (a, b) in segs.items():
        cg, md = stats(r, a, b)
        bc, _ = stats(base, a, b)
        line.append(f'{cg*100:.1f}%/{md*100:.0f}% ({(cg-1.5*bc)*100:+.1f})')
    line.append(int((w.diff().abs() > 0).sum()))
    rows.append(line)
print('0050 含息：', {k: f'{stats(base, *v)[0]*100:.1f}%' for k, v in segs.items()})
print(pd.DataFrame(rows, columns=['方案'] + list(segs) + ['換倉次數']).to_string(index=False))
