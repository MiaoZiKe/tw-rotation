"""trend 立場書補證：週K 定方向（0050 週收盤 vs 40 週均線）切換正二（00631L），對照日線 200MA 與買進持有。

為什麼要跑：lev_lab 的冠軍是「看日K、隔日換」的 200 日線切換。趨勢派主張「週K 定方向、日K 找點」，
週線確認可以少掉假跌破來回洗（台股 2015 起多次短暫跌破 200MA 隨即收復）。這支只驗「週K 方向濾網」這一層。

口徑：
- 真實 ETF 價（資料湖 price_daily，2015 起），不使用代理序列。
- 0050 含息：除息日把現金股利加回當日報酬（etf_dividend_events）。00631L 拆分以單日 |報酬|>40% 偵測、該日報酬視為 0。
- 訊號只用 <= 當週週五收盤的資料，下一個交易日開盤換倉（無未來函數）；
  用「開盤到開盤」報酬計，避免拿收盤訊號吃當天收盤價。
- 每次換倉的變動部位扣 0.1425%x2 手續費 + 0.1% ETF 證交稅 + 0.1% 滑價。閒置現金年息 1%。
- 只讀資料湖，不寫回。
"""
import glob
import numpy as np
import pandas as pd

fs = glob.glob('data/price_daily/**/*.parquet', recursive=True)
px = pd.concat(pd.read_parquet(f, columns=['date', 'code', 'open', 'close']) for f in fs)
px = px[px.code.isin(['0050', '00631L'])].copy()
px['date'] = pd.to_datetime(px.date)
px = px.drop_duplicates(['date', 'code']).pivot(index='date', columns='code').sort_index()
px = px[px.index >= '2014-06-01'].dropna()
c, o = px['close'].copy(), px['open']
# 訊號用收盤做拆分還原（往前乘回比例），不然拆分當天會被誤判成崩跌
for k in c.columns:
    jump = c[k] / c[k].shift(1)
    adj = pd.Series(1.0, index=c.index)
    for d in jump[(jump < 0.6)].index:
        adj[adj.index < d] *= jump[d]
    c[k] = c[k] * adj

dv = pd.concat(map(pd.read_parquet, glob.glob('data/etf_dividend_events/**/*.parquet', recursive=True)))
dv = dv[(dv.code == '0050') & (dv.kind == 'cash')].copy()
dv['ex_date'] = pd.to_datetime(dv.ex_date)
div = dv.groupby('ex_date').amount.sum().reindex(c.index).fillna(0)

# 開盤到開盤報酬（第 t 天開盤 -> 第 t+1 天開盤），股利在除息日開盤前發生，加到前一段
r50 = (o['0050'].shift(-1) + div.shift(-1)) / o['0050'] - 1
r50[r50.abs() > 0.4] = 0.0  # 0050 2025 年 1 拆 4
rL2 = o['00631L'].shift(-1) / o['00631L'] - 1
rL2[rL2.abs() > 0.4] = 0.0  # 拆分
cash_d = 0.01 / 252
COST = 0.001425 * 2 + 0.001 + 0.001


def run(w):
    """w：每天開盤時持有的正二權重（其餘現金）。"""
    w = w.reindex(c.index).ffill().fillna(1.0)
    turn = w.diff().abs().fillna(0)
    ret = w * rL2 + (1 - w) * cash_d - turn * COST
    return ret.dropna()


# 1) 買進持有正二
bh = pd.Series(1.0, index=c.index)
# 2) 日線 200MA ±2%、遲滯，跌破持 30%（lev_lab 事後挑選 2 的規則，用 0050 收盤代替加權指數）
ma = c['0050'].rolling(200).mean()
state, s = [], 1.0
for p, m in zip(c['0050'], ma):
    if not np.isnan(m):
        if p > m * 1.02: s = 1.0
        elif p < m * 0.98: s = 0.3
    state.append(s)
d200 = pd.Series(state, index=c.index).shift(1)  # 今日收盤訊號 -> 明日開盤
# 3) 週K：週五收盤 vs 40 週均線，連 2 週確認才翻向；跌破持 30%
wk = c['0050'].resample('W-FRI').last().dropna()
wma = wk.rolling(40).mean()
above = (wk > wma).astype(int)
state, s = [], 1.0
for i in range(len(wk)):
    if i >= 1 and not np.isnan(wma.iloc[i]):
        if above.iloc[i] and above.iloc[i - 1]: s = 1.0
        elif not above.iloc[i] and not above.iloc[i - 1]: s = 0.3
    state.append(s)
wsig = pd.Series(state, index=wk.index)
# 週五收盤訊號 -> 下一個交易日開盤生效
wdaily = wsig.reindex(c.index, method='ffill').shift(1)
# 4) 週K 方向 + 日K 回場：週線看空時，若 0050 收盤重新站上 20 日高點則提前回到 100%（趨勢派「週定方向、日找點」）
hh20 = c['0050'].rolling(20).max()
wd = wsig.reindex(c.index, method='ffill')
mix = wd.copy()
mix[(wd < 1) & (c['0050'] >= hh20)] = 1.0
mix = mix.shift(1)

base = r50.dropna()
segs = {'B 2015~2020': ('2015-01-01', '2020-12-31'), 'C 2021~': ('2021-01-01', '2100-01-01'),
        '2017~2020': ('2017-01-01', '2020-12-31'), '全期 2015~': ('2015-01-01', '2100-01-01')}


def stats(r, a, b):
    r = r[(r.index >= a) & (r.index <= b)]
    eq = (1 + r).cumprod()
    yrs = len(r) / 252
    cagr = eq.iloc[-1] ** (1 / yrs) - 1
    mdd = (eq / eq.cummax() - 1).min()
    return cagr, mdd


rows = []
for name, w in [('買進持有正二', bh), ('日線200MA±2% 跌破30%', d200), ('週K40週 連2週確認 跌破30%', wdaily),
                ('週K方向+日K20日新高回場', mix)]:
    r = run(w)
    for sname, (a, b) in segs.items():
        cg, md = stats(r, a, b)
        bc, bm = stats(base, a, b)
        rows.append([name, sname, f'{cg*100:.1f}%', f'{md*100:.1f}%', f'{bc*100:.1f}%', f'{bc*1.5*100:.1f}%',
                     f'{(cg-bc*1.5)*100:+.1f}', int((w.diff().abs() > 0).sum())])
out = pd.DataFrame(rows, columns=['方案', '區段', '年化', '最大回撤', '0050含息', '門檻1.5x', '差距(點)', '全期換倉次數'])
print(out.to_string(index=False))
