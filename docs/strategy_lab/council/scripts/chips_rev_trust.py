"""chips 第一回合小回測：月營收動能（S2 精簡版）x 投信／融資籌碼濾網。
口徑（粗糙，僅供立場書佐證，屬「假說級」證據）：
- 價格未還原；個股日報酬 |r|>10.5% 視為除權／分割設 0，所以股票與 0050 都少算股息（0050 約少 3%/年）
- 每月 11 日起第一個交易日收盤產生訊號並以收盤近似成交（略樂觀）
- 成本：換手 x (手續費 0.1425% + 滑價 0.1%)，賣出邊另加證交稅 0.3%
- 股票池：當時近 60 日平均成交值前 200 檔 4 碼股（含存活者偏誤，見 factor_lab README）
執行：python docs/strategy_lab/council/scripts/chips_rev_trust.py（在 repo 根目錄）
"""
import glob
import pandas as pd


def load(t, cols, y0=2016):
    fs = [f for f in sorted(glob.glob(f'data/{t}/**/*.parquet', recursive=True))
          if int(f.split('year=')[1][:4]) >= y0]
    return pd.concat([pd.read_parquet(f, columns=cols) for f in fs])


px = load('price_daily', ['date', 'code', 'close', 'turnover'], 2015)
px = px[px.code.str.fullmatch(r'\d{4}')]
px['date'] = pd.to_datetime(px.date)
C = px.pivot_table(index='date', columns='code', values='close').sort_index()
T = px.pivot_table(index='date', columns='code', values='turnover').sort_index()
R = C.pct_change(fill_method=None)
R = R.where(R.abs() < 0.105, 0).fillna(0)
ma60 = C.rolling(60).mean()
tv60 = T.rolling(60, min_periods=40).mean()

inst = load('inst_daily', ['date', 'code', 'trust'])
inst['date'] = pd.to_datetime(inst.date)
TR = inst.pivot_table(index='date', columns='code', values='trust').reindex(C.index).fillna(0)
tr20 = TR.rolling(20).sum()

mg = load('margin_daily', ['date', 'code', 'margin_balance'], 2021)
mg['date'] = pd.to_datetime(mg.date)
MB = mg.pivot_table(index='date', columns='code', values='margin_balance').reindex(C.index).ffill()
mgchg = MB / MB.shift(20) - 1

rv = load('revenue_monthly', ['ym', 'code', 'revenue'], 2015)
RV = rv.pivot_table(index='ym', columns='code', values='revenue').sort_index()
ratio = RV.rolling(3).mean() / RV.rolling(12, min_periods=12).mean()
dates = C.index

rebal = {}
for ym in RV.index:
    y, m = map(int, ym.split('-'))
    m += 1
    if m == 13:
        y, m = y + 1, 1
    d = dates[dates >= pd.Timestamp(y, m, 11)]
    if len(d):
        rebal[d[0]] = ym


def run(mode, N=10):
    w = pd.Series(dtype=float)
    nav, out = 1.0, {}
    for dt in dates:
        if len(w):
            nav *= 1 + (R.loc[dt, w.index] * w).sum()
        if dt in rebal:
            s = ratio.loc[rebal[dt]].dropna()
            pool = tv60.loc[dt].dropna().nlargest(200).index
            s = s[s.index.isin(pool) & (s > 1.0)]
            above = (C.loc[dt] > ma60.loc[dt]).reindex(s.index).fillna(False).astype(bool)
            s = s[above]
            if mode in ('trust', 'trust_mg'):
                s = s[tr20.loc[dt].reindex(s.index).fillna(0) > 0]
            if mode == 'trust_mg' and dt >= pd.Timestamp(2021, 3, 1):
                s = s[~(mgchg.loc[dt].reindex(s.index).fillna(0) > 0.25)]
            pick = s.nlargest(N).index
            nw = pd.Series(1 / len(pick), index=pick) if len(pick) else pd.Series(dtype=float)
            diff = nw.sub(w, fill_value=0)
            nav *= 1 - diff.abs().sum() * 0.002425 - diff[diff < 0].abs().sum() * 0.003
            w = nw
        out[dt] = nav
    return pd.Series(out)


def yearly(s):
    return s.resample('YE').last().pct_change().dropna()


rb = C['0050'].pct_change().fillna(0)
rb = rb.where(rb.abs() < 0.3, 0)  # 2025 年 1 拆 4
res = {'0050未含息': yearly((1 + rb).cumprod())}
for m in ['base', 'trust', 'trust_mg']:
    res[m] = yearly(run(m))
df = pd.DataFrame(res)
df.index = df.index.year
print(df.loc[2017:].round(3).to_string())
for a, b in [(2017, 2020), (2021, 2026), (2017, 2026)]:
    sub = df.loc[a:b]
    print(a, b, ((1 + sub).prod() ** (1 / len(sub)) - 1).round(3).to_dict())
