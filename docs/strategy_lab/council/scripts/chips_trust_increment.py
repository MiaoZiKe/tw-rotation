"""chips 第二回合：投信濾網是不是動能的影子？
在 S2 候選股（前 200 流動性池、近3月/近12月營收>1、站上 60 日線）裡，
每個換股日依「20 日漲幅」分三組，組內比較 投信 20 日買超>0 與 <=0 的下一期（到下次換股日）平均報酬，
報告每組的月平均差、t 值與分年結果；另報排除航運（company_info 產業含「航運」）後的結果。
口徑同 chips_rev_trust.py（價格未還原、|r|>10.5% 設 0）。執行：在 repo 根目錄 python 本檔。
"""
import glob
import numpy as np
import pandas as pd


def load(t, cols, y0=2016):
    fs = [f for f in sorted(glob.glob(f'data/{t}/**/*.parquet', recursive=True))
          if 'year=' not in f or int(f.split('year=')[1][:4]) >= y0]
    return pd.concat([pd.read_parquet(f, columns=cols) for f in fs])


px = load('price_daily', ['date', 'code', 'close', 'turnover'], 2015)
px = px[px.code.str.fullmatch(r'\d{4}')]
px['date'] = pd.to_datetime(px.date)
C = px.pivot_table(index='date', columns='code', values='close').sort_index()
T = px.pivot_table(index='date', columns='code', values='turnover').sort_index()
R = C.pct_change(fill_method=None)
R = R.where(R.abs() < 0.105, 0).fillna(0)
LR = np.log1p(R).cumsum()
ma60 = C.rolling(60).mean()
tv60 = T.rolling(60, min_periods=40).mean()
inst = load('inst_daily', ['date', 'code', 'trust'])
inst['date'] = pd.to_datetime(inst.date)
TR = inst.pivot_table(index='date', columns='code', values='trust').reindex(C.index).fillna(0)
tr20 = TR.rolling(20).sum()
rv = load('revenue_monthly', ['ym', 'code', 'revenue'], 2015)
RV = rv.pivot_table(index='ym', columns='code', values='revenue').sort_index()
ratio = RV.rolling(3).mean() / RV.rolling(12, min_periods=12).mean()
try:
    ci = pd.concat([pd.read_parquet(f) for f in glob.glob('data/company_info/**/*.parquet', recursive=True)])
    col = [c for c in ci.columns if 'industry' in c][0]
    ship = set(ci[ci[col].astype(str).str.contains('航運')].code.astype(str))
except Exception as e:
    print('company_info 讀取失敗', e); ship = set()
print('航運檔數', len(ship))
dates = C.index
rebal = []
for ym in RV.index:
    y, m = map(int, ym.split('-')); m += 1
    if m == 13: y, m = y + 1, 1
    d = dates[dates >= pd.Timestamp(y, m, 11)]
    if len(d): rebal.append((d[0], ym))
rows = []
for (dt, ym), (nx, _) in zip(rebal[:-1], rebal[1:]):
    s = ratio.loc[ym].dropna()
    pool = tv60.loc[dt].dropna().nlargest(200).index
    s = s[s.index.isin(pool) & (s > 1.0)]
    s = s[(C.loc[dt] > ma60.loc[dt]).reindex(s.index).fillna(False).astype(bool)]
    if len(s) < 15: continue
    i = dates.get_loc(dt)
    mom = (LR.iloc[i] - LR.iloc[i - 20]).reindex(s.index)
    fwd = np.expm1(LR.loc[nx] - LR.loc[dt]).reindex(s.index)
    d = pd.DataFrame({'mom': mom, 'fwd': fwd, 'tr': tr20.loc[dt].reindex(s.index).fillna(0)})
    d['terc'] = pd.qcut(d.mom.rank(method='first'), 3, labels=['低', '中', '高'])
    d['ship'] = d.index.isin(ship)
    d['dt'] = dt
    rows.append(d)
D = pd.concat(rows)
D = D[D.dt >= '2017-01-01']


def summarize(D, tag):
    g = D.groupby(['dt', 'terc', D.tr > 0], observed=True).fwd.mean().unstack()
    g.columns = ['投信<=0', '投信>0']
    g['差'] = g['投信>0'] - g['投信<=0']
    print(f'\n== {tag}')
    for t in ['低', '中', '高']:
        x = g.xs(t, level='terc')['差'].dropna()
        print(f'20日漲幅{t}組：月均差 {x.mean()*100:+.2f}% t={x.mean()/x.std()*np.sqrt(len(x)):.2f} n={len(x)} 正比例 {(x>0).mean():.0%}')
    allx = g['差'].groupby(level='dt').mean().dropna()
    print(f'三組平均：月均差 {allx.mean()*100:+.2f}% t={allx.mean()/allx.std()*np.sqrt(len(allx)):.2f} n={len(allx)}')
    print('分年月均差(%)：', (allx.groupby(allx.index.year).mean() * 100).round(2).to_dict())


summarize(D, '全部')
summarize(D[~D.ship], '排除航運')
