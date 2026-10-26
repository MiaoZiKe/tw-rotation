"""委員 futures：台指期「趨勢濾網 x 曝險槓桿 x 波動目標」小型回測。
資料：data/index_ohlc 的 FUT（台指期日盤近月連續）與 TSE（加權現貨）。
換月修正：沿用 futures_lab round4 的作法，結算日（每月第三個週三）隔天的報酬改用現貨報酬。
訊號：收盤算，隔日才生效（持倉 shift(1)）。成本：單邊 3 點（滑價+手續費+稅合併估），除以當日價位。
0050 基準：直接引用 docs/futures_lab/round6/README.md 的含息扣成本年化，不重算。
所有數字都落在 round5/6 已被窺視的資料上，只能當線索，不是乾淨樣本外。
用法：在 repo 根目錄 python3 docs/strategy_lab/council/scripts/futures_levtrend.py"""
import numpy as np
import pandas as pd

D = pd.read_parquet('data/index_ohlc')
D['date'] = pd.to_datetime(D['date'])
f = D[D.symbol == 'FUT'].set_index('date').sort_index()
s = D[D.symbol == 'TSE'].set_index('date').sort_index()
idx = f.index.intersection(s.index)
f, s = f.loc[idx], s.loc[idx]
rf, rs = f.close.pct_change(), s.close.pct_change()

sett = []
for (y, m), _ in pd.Series(idx, index=idx).groupby([idx.year, idx.month]):
    wed = [d for d in pd.date_range(f'{y}-{m:02d}-01', periods=31, freq='D')
           if d.month == m and d.weekday() == 2]
    nxt = idx[idx >= wed[2]]
    if len(nxt):
        sett.append(nxt[0])
pos_of = {d: i for i, d in enumerate(idx)}
after = [idx[pos_of[d] + 1] for d in sett if pos_of[d] + 1 < len(idx)]
mask = f.index.isin(after)
# 拆成「隔夜跳空」與「日內」兩段：訊號收盤算、隔日開盤才成交（舊部位吃跳空、新部位吃日內）
gap_f = f.open / f.close.shift(1) - 1
day_f = f.close / f.open - 1
gap_s = s.open / s.close.shift(1) - 1
day_s = s.close / s.open - 1
gap = gap_f.where(~mask, gap_s).fillna(0)
day = day_f.where(~mask, day_s).fillna(0)

ma = s.close.rolling(200).mean()
vol = rs.rolling(20).std() * np.sqrt(252)
SEG = {'03-07~07': ('2003-07-01', '2007-12-31', 11.7), '2008~16': ('2008-01-01', '2016-12-31', 4.2),
       '2017~20': ('2017-01-01', '2020-12-31', 18.3), '2021起': ('2021-01-01', '2026-12-31', 27.6)}


def run(L_on, L_off=0.0, trend=True, vt=None, skip_settle=False):
    up = (s.close > ma).astype(float) if trend else pd.Series(1.0, index=idx)
    L = up * L_on + (1 - up) * L_off
    if vt:
        L = L.where(up == 0, np.minimum(L_on, vt / vol.clip(lower=0.08)))
    if skip_settle:  # 結算日整天空手：收盤前一天不留倉過結算日，隔日開盤再回場
        L = L.where(~L.index.isin(sett), 0.0)
    pos = L.shift(1).fillna(0)          # 今天執行的目標部位（昨收訊號）
    old = pos.shift(1).fillna(0)        # 昨天持有到今天開盤的部位
    cost = (pos - old).abs() * 3.0 / f.open
    cash = 0.01 / 252 * (1 - pos / 6).clip(lower=0)
    return old * gap + pos * day - cost + cash, pos


def stat(ret, a, b):
    x = ret.loc[a:b]
    eq = (1 + x).cumprod()
    yrs = (x.index[-1] - x.index[0]).days / 365.25
    return (eq.iloc[-1] ** (1 / yrs) - 1) * 100, ((eq / eq.cummax() - 1).min()) * 100


cfgs = [('持有1.2x', dict(L_on=1.2, trend=False)), ('持有1.3x', dict(L_on=1.3, trend=False)),
        ('200MA 上1.5x/下1.0x(軟降)', dict(L_on=1.5, L_off=1.0)), ('200MA 上1.3x/下0.7x', dict(L_on=1.3, L_off=0.7)),
        ('持有1x', dict(L_on=1, trend=False)), ('持有1.5x', dict(L_on=1.5, trend=False)),
        ('持有2x', dict(L_on=2, trend=False))]
cfgs.append(('200MA 1.5/1.0 結算日空手', dict(L_on=1.5, L_off=1.0, skip_settle=True)))
cfgs.append(('持有1.3x 結算日空手', dict(L_on=1.3, trend=False, skip_settle=True)))
for lon in (1.0, 1.5, 2.0):
    for loff in (0.0, 0.5):
        cfgs.append((f'200MA 上{lon}x/下{loff}x', dict(L_on=lon, L_off=loff)))
for lon in (1.5, 2.0, 2.5):
    cfgs.append((f'200MA 上限{lon}x+波動目標18%/下0', dict(L_on=lon, vt=0.18)))
rows = []
for name, kw in cfgs:
    ret, pos = run(**kw)
    row = {'策略': name}
    wins = 0
    for k, (a, b, b50) in SEG.items():
        ann, _ = stat(ret, a, b)
        row[k] = f'{ann:.1f}({ann - b50:+.1f})'
        wins += ann > b50
    ann, dd = stat(ret, '2003-07-01', '2026-12-31')
    row['全期年化'] = f'{ann:.1f}'
    row['全期回撤'] = f'{dd:.0f}%'
    row['過幾段'] = f'{wins}/4'
    row['平均曝險'] = f'{pos.loc["2003-07":].mean():.2f}'
    rows.append(row)
pd.set_option('display.width', 250)
print(pd.DataFrame(rows).to_string(index=False))
print('現貨最慘 5 日：', rs.nsmallest(5).round(3).to_dict())
print('資料尾', idx[-1].date(), '樣本天數', len(idx))

# 保證金風險：2x 持有時，單日現貨最大跌幅 x 曝險 = 單日權益損失；日內最低點對前收的最大不利偏移
adv = (f.low / f.close.shift(1) - 1).nsmallest(3)
print('期貨日內最大不利偏移（低點/前收-1）前3：', adv.round(3).to_dict())
for L in (1.5, 2.0):
    print(f'{L}x 在現貨最慘日單日權益損失：', round(rs.min() * L * 100, 1), '%')
