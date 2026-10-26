"""委員 futures 第二回合驗證：
 (A) 0050 含息報酬自建（修正 price_daily 讀檔問題、2025-06 分割），與前輪引用的 0050 年化對帳。
 (B) 「1 倍台指期輸 0050」是股利還是權值股 beta：拆成加權價格報酬、0050 價格報酬、股利殖利率。
 (C) 0050 + 台指期 overlay 實測（0050 占 0.8、現金 0.2 當保證金緩衝、期貨 0.7 倍，總曝險約 1.5）。
 (D) 逐年勝負與滾動 3 年視窗（回應 alloc 的滾動窗口質疑）。
price_daily 讀檔問題：year=2026 分區 schema 與其他年份不同（多 name/px_source 欄，volume/turnover/transactions 由 int64 變 double 且含小數），
pd.read_parquet 整個資料夾時以第一個分區的 int64 合併，遇到小數就報 truncated。逐檔讀再 concat 即可。
用法：在 repo 根目錄 python3 docs/strategy_lab/council/scripts/futures_r2_overlay.py"""
import glob
import numpy as np
import pandas as pd

# ---------- 0050 含息 ----------
p = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob('data/price_daily/year=*/part.parquet'))])
x = p[p.code == '0050'].copy()
x['date'] = pd.to_datetime(x.date)
x = x.sort_values('date').set_index('date')
adj = x.close.copy()
adj[adj.index < '2025-06-18'] /= 4.0   # 2025-06 一拆四
adj_o = x.open.copy()
adj_o[adj_o.index < '2025-06-18'] /= 4.0
dv = pd.read_parquet(glob.glob('data/etf_dividend_events/**/*.parquet', recursive=True)[0])
dv = dv[(dv.code == '0050') & (dv.kind == 'cash')].copy()
dv['ex'] = pd.to_datetime(dv.ex_date)
dv['amt'] = np.where(dv.ex < '2025-06-18', dv.amount / 4.0, dv.amount)
div = dv.groupby('ex').amt.sum().reindex(adj.index).fillna(0)
tr50 = (adj + div) / adj.shift(1) - 1           # 含息日報酬（不計股利稅，略高估）；2009 前無股利資料
px50 = adj.pct_change()

D = pd.read_parquet('data/index_ohlc')
D['date'] = pd.to_datetime(D['date'])
f = D[D.symbol == 'FUT'].set_index('date').sort_index()
s = D[D.symbol == 'TSE'].set_index('date').sort_index()
idx = f.index.intersection(s.index)
f, s = f.loc[idx], s.loc[idx]
rs = s.close.pct_change()

SEG = {'2003-07~07': ('2003-07-01', '2007-12-31'), '2008~16': ('2008-01-01', '2016-12-31'),
       '2017~20': ('2017-01-01', '2020-12-31'), '2021起': ('2021-01-01', '2026-12-31')}


def ann(r, a, b):
    x_ = r.loc[a:b].dropna()
    return ((1 + x_).prod() ** (365.25 / (x_.index[-1] - x_.index[0]).days) - 1) * 100


print('== (A)(B) 價格報酬與含息報酬年化（0050 含息：2009 前無股利資料，只看 2017 後兩段較可信）')
rows = []
for k, (a, b) in SEG.items():
    rows.append({'區段': k, '加權價格': round(ann(rs, a, b), 1), '0050價格': round(ann(px50, a, b), 1),
                 '0050含息(自建)': round(ann(tr50, a, b), 1)})
print(pd.DataFrame(rows).to_string(index=False))
y = pd.DataFrame({'加權價格': rs, '0050價格': px50, '0050含息': tr50}).dropna()
print('0050 殖利率（年度股利/年初價）：', (div.groupby(div.index.year).sum() / adj.groupby(adj.index.year).first()).round(3).loc[2012:].to_dict())

# ---------- 期貨引擎（同 futures_levtrend，換月修正＋隔日開盤成交） ----------
sett = []
for (yy, m), _ in pd.Series(idx, index=idx).groupby([idx.year, idx.month]):
    wed = [d for d in pd.date_range(f'{yy}-{m:02d}-01', periods=31, freq='D') if d.month == m and d.weekday() == 2]
    nxt = idx[idx >= wed[2]]
    if len(nxt):
        sett.append(nxt[0])
pos_of = {d: i for i, d in enumerate(idx)}
after = [idx[pos_of[d] + 1] for d in sett if pos_of[d] + 1 < len(idx)]
mask = f.index.isin(after)
gap = (f.open / f.close.shift(1) - 1).where(~mask, s.open / s.close.shift(1) - 1).fillna(0)
day = (f.close / f.open - 1).where(~mask, s.close / s.open - 1).fillna(0)
ma = s.close.rolling(200).mean()
up = (s.close > ma).astype(float)


def fut(L_on, L_off=None):
    L = up * L_on + (1 - up) * (L_on if L_off is None else L_off)
    pos = L.shift(1).fillna(0)
    old = pos.shift(1).fillna(0)
    cost = (pos - old).abs() * 3.0 / f.open
    return old * gap + pos * day - cost, pos


def eq_curve(r):
    return (1 + r.fillna(0)).cumprod()


def dd(r):
    e = eq_curve(r)
    return (e / e.cummax() - 1).min() * 100


cash = 0.01 / 252
cands = {}
r1, _ = fut(1.0)
cands['0050 持有（自建含息）'] = tr50.reindex(idx)
cands['台指期 1x（含現金息 0.83%）'] = r1 + cash * 5 / 6
r, _ = fut(0.7)
cands['0050x0.8 + 現金0.2 + 期貨0.7x（靜態）'] = 0.8 * tr50.reindex(idx) + 0.2 * cash + r
r, _ = fut(0.7, 0.2)
cands['0050x0.8 + 期貨 上0.7x/下0.2x（200MA）'] = 0.8 * tr50.reindex(idx) + 0.2 * cash + r
r, _ = fut(1.5, 1.0)
cands['F1 台指期 200MA 1.5x/1.0x'] = r + cash * 0.7
for L in (1.2, 1.3):
    r, _ = fut(L)
    cands[f'台指期 持有{L}x'] = r + cash * (1 - L / 6)
r, _ = fut(1.5)
cands['台指期 持有1.5x'] = r + cash * 0.7

print('\n== (C) overlay 與對照（只看 2017 後兩段較可信；0050 自建值與前輪 18.3/27.6 對帳）')
rows = []
for k, rr in cands.items():
    row = {'策略': k}
    for sk in ('2017~20', '2021起'):
        a, b = SEG[sk]
        row[sk] = round(ann(rr, a, b), 1)
    row['2009起全期'] = round(ann(rr, '2009-01-01', '2026-12-31'), 1)
    row['回撤(2009起)'] = round(dd(rr.loc['2009':]), 0)
    rows.append(row)
print(pd.DataFrame(rows).to_string(index=False))

print('\n== (D) 逐年勝負（2009 起，各候選 vs 0050 自建含息）與滾動 3 年視窗')
base = tr50.reindex(idx)
for k, rr in cands.items():
    if k.startswith('0050 持有'):
        continue
    yr = pd.DataFrame({'a': (1 + rr.loc['2009':]).groupby(rr.loc['2009':].index.year).prod() - 1,
                       'b': (1 + base.loc['2009':]).groupby(base.loc['2009':].index.year).prod() - 1})
    roll = []
    for y0 in range(2009, 2024):
        a, b = f'{y0}-01-01', f'{y0 + 2}-12-31'
        roll.append(ann(rr, a, b) > ann(base, a, b))
    roll15 = []
    for y0 in range(2009, 2024):
        a, b = f'{y0}-01-01', f'{y0 + 2}-12-31'
        roll15.append(ann(rr, a, b) >= 1.5 * ann(base, a, b))
    print(f'{k}: 逐年贏 {(yr.a > yr.b).sum()}/{len(yr)}；滾動3年贏0050 {sum(roll)}/{len(roll)}；達0050x1.5 {sum(roll15)}/{len(roll15)}；最差年 {yr.a.min()*100:.0f}%')
