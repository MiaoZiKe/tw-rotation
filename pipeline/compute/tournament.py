"""100 位投資者淘汰賽：用演化式優化找台股波段策略組合。

怎麼讀這支檔案（由上到下）：
  1. 資料準備  ：還原價、流動性前 300 名的可交易池、各面向原始序列。全部只讀資料湖，不寫。
  2. 基因庫    ：技術／籌碼／消息事件三個「進場條件庫」＋出場風控庫。每個條件 = 一張 日期×股票 的布林表。
  3. 模擬器    ：numba 逐日撮合。訊號 t 日收盤產生 → t+1 日開盤成交（紅線，不可妥協）。
  4. 淘汰賽    ：每回合半年、每人從 10 萬開始；淘汰後段班、交叉＋突變補滿 100 人。
  5. 凍結與保留期、隨機對照、deflated Sharpe。
  6. 報告輸出  ：docs/strategy_lab/tournament/。

誠實條款（寫在程式裡，免得之後被改掉）：
  · 比賽只用 2012-01 ~ 2020-12；2021 年以後只在「凍結名單」之後跑一次。
  · 融資資料 2021 年才有、當沖 2025 年才有 —— 訓練期沒有這兩種資料，所以不進演化，只在保留期做事後探索。
  · 只做多。台股放空要融券（保證金、借券費、平盤以下不得放空），10 萬元小帳戶不實際，列為限制不是疏漏。
  · 零股：模擬用可分割股數（盤中零股 2020-10 才開放），報告標註。
"""
from __future__ import annotations

import glob
import hashlib
import json
import math
import os
import pickle
import random
import sys
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
from numba import njit

ROOT = os.environ.get("TOURN_DATA", os.path.join(os.path.dirname(__file__), "..", "..", "data"))   # 以本 worktree 的 data/ 為準（主 checkout 的資料可能落後）
CACHE = os.environ.get("TOURN_CACHE", "/tmp/claude-0/-home-user-tw-rotation/fe3b946e-89a8-59da-b615-8ebf1e80fccc/scratchpad/tourn")
OUT = os.environ.get("TOURN_OUT", os.path.join(os.path.dirname(__file__), "..", "..", "docs", "strategy_lab", "tournament"))
os.makedirs(CACHE, exist_ok=True)

TRAIN_START, TRAIN_END = "2012-01-01", "2020-12-31"
HOLD_START = "2021-01-01"
CASH0 = 100_000.0
FEE, TAX, SLIP, MINFEE = 0.001425, 0.003, 0.001, 20.0   # 手續費不打折（保守）、證交稅賣出 0.3%、單邊滑價 0.1%、手續費最低 20 元
COOL = 5            # 賣出後同一檔 5 個交易日內不再買（避免停損後立刻重進）
BUST = 0.70         # 權益跌破 7 成 = 出局

# ============================================================== 1. 資料準備


def _rd(t, cols=None, start=None):
    fs = sorted(glob.glob(f"{ROOT}/{t}/**/*.parquet", recursive=True))
    if start:
        fs = [f for f in fs if "year=" not in f or int(f.split("year=")[1][:4]) >= int(start[:4])]
    return pd.concat([pd.read_parquet(f, columns=cols) for f in fs], ignore_index=True)


def _piv(df, col, dates, codes):
    return df.pivot(index="date", columns="code", values=col).reindex(index=dates, columns=codes)


def prepare():
    """建全部底表並存快取。第 t 日的每個數字只用 <= t 的資料（美股用 < t，營收用法定可用日）。"""
    pk = f"{CACHE}/base.pkl"
    if os.path.exists(pk):
        return pickle.load(open(pk, "rb"))
    px = _rd("price_daily", ["date", "code", "open", "high", "low", "close", "volume", "turnover"], "2011-01-01")
    ci = _rd("company_info", ["code", "market", "industry"])
    emerg = set(ci[ci.market == "EMERGING"].code)
    px = px[px.code.str.fullmatch(r"\d{4}") & ~px.code.str.startswith("00") & ~px.code.isin(emerg)]
    px = px.dropna(subset=["open", "high", "low", "close"])
    px = px[(px.close > 0) & (px.open > 0)].drop_duplicates(["date", "code"])
    px["date"] = pd.to_datetime(px.date)
    dates = pd.DatetimeIndex(sorted(px.date.unique()))
    codes = sorted(px.code.unique())
    # 還原價：除權息日前的價格乘累積係數（現金＋股票股利都含）
    dv = _rd("dividend_results", ["date", "code", "before_price", "reference_price"])
    dv = dv[dv.code.isin(codes)].copy()
    dv["f"] = dv.reference_price / dv.before_price
    dv = dv[(dv.f > 0.3) & (dv.f < 1.0)]
    dv["date"] = pd.to_datetime(dv.date)
    dv = dv.groupby(["date", "code"]).f.prod().reset_index()
    F = dv.pivot(index="date", columns="code", values="f")
    F = F.reindex(dates.union(F.index)).fillna(1.0)
    pos = dates.searchsorted(F.index)
    F2 = F.groupby(np.minimum(pos, len(dates) - 1)).prod()
    F2.index = dates[F2.index]
    F = F2.reindex(dates).fillna(1.0).reindex(columns=codes).fillna(1.0)
    M = (F[::-1].cumprod()[::-1]) / F
    craw = _piv(px, "close", dates, codes)
    adj0 = craw * M
    rr_ = adj0 / adj0.ffill().shift(1)
    ev = (rr_ < 0.62) | (rr_ > 1.6)       # 漲跌幅限制下不可能的單日變動 = 未記錄的分割／減資
    F3 = rr_.where(ev).fillna(1.0)
    M = M * ((F3[::-1].cumprod()[::-1]) / F3)
    d = {k: _piv(px, k, dates, codes) * M for k in ("open", "high", "low", "close")}
    d["V"] = _piv(px, "volume", dates, codes)
    d["T"] = _piv(px, "turnover", dates, codes)
    d["Craw"] = craw
    # 可交易池：當日（含）以前 60 日成交值中位數排名前 300、股價 >= 10、成交值 >= 2 千萬
    med60 = d["T"].rolling(60, min_periods=40).median()
    rank = med60.rank(axis=1, ascending=False)
    elig = (rank <= 300) & (med60 >= 2e7) & (craw >= 10)
    keep = list(elig.columns[elig.any()])
    for k in list(d):
        d[k] = d[k][keep]
    elig = elig[keep]
    d["elig"] = elig
    d["dates"], d["codes"] = dates, keep
    # 大盤
    idx = _rd("index_ohlc")
    idx = idx[idx.symbol == "TSE"].copy()
    idx["date"] = pd.to_datetime(idx.date)
    d["idx"] = idx.set_index("date").sort_index().close.reindex(dates).ffill()
    # 法人（股數）
    # 2018 以前資料湖的 foreign_total／inst_total 欄位是空的（只有 foreign、trust、dealer_self、dealer_hedge），
    # 所以早期用『外陸資 foreign』與『四欄加總』補上；外資自營商那一小塊早期缺，口徑略有差異，報告有註明。
    inst = _rd("inst_daily", ["date", "code", "foreign", "foreign_total", "trust", "dealer_self", "dealer_hedge", "inst_total"], "2011-01-01")
    inst["date"] = pd.to_datetime(inst.date)
    inst["foreign_total"] = inst.foreign_total.fillna(inst.foreign)
    inst["inst_total"] = inst.inst_total.fillna(inst.foreign_total + inst.trust.fillna(0) + inst.dealer_self.fillna(0) + inst.dealer_hedge.fillna(0))
    for k in ("foreign_total", "trust", "inst_total"):
        d["inst_" + k] = _piv(inst, k, dates, keep)
    # 融資（2021+，只供保留期事後探索）
    mg = _rd("margin_daily", ["date", "code", "margin_balance", "short_balance"])
    mg["date"] = pd.to_datetime(mg.date)
    d["margin_balance"] = _piv(mg, "margin_balance", dates, keep)
    d["short_balance"] = _piv(mg, "short_balance", dates, keep)
    # 月營收：法定可用日 = 次月 10 日，寧可晚用
    rv = _rd("revenue_monthly", ["ym", "code", "revenue"]).drop_duplicates(["ym", "code"])
    R = rv.pivot(index="ym", columns="code", values="revenue").sort_index()
    full = pd.period_range(R.index.min(), R.index.max(), freq="M").astype(str)
    R = R.reindex(full).reindex(columns=keep)
    yoy = R / R.shift(12) - 1
    yoy3 = yoy.rolling(3).mean()
    avail = pd.to_datetime(R.index + "-01") + pd.offsets.MonthBegin(1) + pd.Timedelta(days=9)

    def to_daily(X):
        X = X.copy()
        X.index = avail
        X = X[~X.index.duplicated()]
        return X.reindex(X.index.union(dates)).ffill().reindex(dates)
    d["yoy"], d["yoy3"] = to_daily(yoy), to_daily(yoy3)
    d["yoy_prev"] = to_daily(yoy.shift(1))
    ann_pos = np.unique(dates.searchsorted(avail))
    ann_pos = ann_pos[ann_pos < len(dates)]
    age = np.full(len(dates), 999)
    last = -999
    s = set(ann_pos.tolist())
    for i in range(len(dates)):
        if i in s:
            last = i
        age[i] = i - last if last > -999 else 999
    d["rev_age"] = age
    # 美股：決策日 t 只能用「日期 < t」的美股收盤（嚴格 T-1）
    ig = _rd("intl_daily", ["date", "symbol", "close"])
    ig["date"] = pd.to_datetime(ig.date)
    us = {}
    for sym in ("^SOX", "^IXIC", "TSM"):
        c = ig[ig.symbol == sym].drop_duplicates("date").set_index("date").sort_index().close
        r = (c / c.shift(1) - 1).dropna().rename("r").reset_index()
        m = pd.merge_asof(pd.DataFrame({"date": dates}), r.rename(columns={"date": "usd"}), left_on="date", right_on="usd",
                          allow_exact_matches=False, direction="backward")
        us[sym] = m["r"].values
    d["us"] = us
    # 事件（排程事件，事先已知）：換成台股「影響日」的位置
    import yaml
    evs = yaml.safe_load(open(os.path.join(os.path.dirname(__file__), "..", "groups", "events_history.yaml"), encoding="utf-8"))["events"]
    evpos = defaultdict(list)
    for e in evs:
        p = int(dates.searchsorted(pd.Timestamp(e["d"]))) + int(e.get("lag", 0))
        if 0 <= p < len(dates):
            evpos[e["t"]].append(p)
    d["evpos"] = {k: sorted(set(v)) for k, v in evpos.items()}
    pickle.dump(d, open(pk, "wb"), protocol=4)
    return d


# ============================================================== 2. 基因庫
class Ctx:
    """持有底表與條件快取。條件 key -> numpy bool (T,N)。"""

    def __init__(self, d):
        self.d = d
        self.dates, self.codes = d["dates"], d["codes"]
        self.T, self.N = len(self.dates), len(self.codes)
        self.O, self.H, self.L, self.C = (d[k] for k in ("open", "high", "low", "close"))
        self.V = d["V"]
        self.cache = {}
        pc = self.C.shift(1)
        tr = pd.concat([(self.H - self.L).stack(), (self.H - pc).abs().stack(), (self.L - pc).abs().stack()], axis=1).max(axis=1).unstack()
        tr = tr.reindex_like(self.C)
        self.TR = tr
        self.ATR = tr.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
        self.V20 = self.V.rolling(20).mean().shift(1)
        self.elig = d["elig"].values
        self.Onp, self.Hnp, self.Lnp, self.Cnp = (x.values for x in (self.O, self.H, self.L, self.C))
        self.Anp = self.ATR.values
        self.ma_exit = {}
        self.no_exit = np.zeros((self.T, self.N), dtype=bool)
        self.scores = {
            "mom20": (self.C / self.C.shift(20) - 1).values,
            "volratio": (self.V / self.V20).values,
            "turnover": d["T"].rolling(20).mean().values,
        }
        # 大盤與標的的報酬列對齊用
        self.idx = d["idx"]

    def arr(self, df):
        return df.fillna(False).astype(bool).values

    def get(self, cond):
        key = json.dumps(cond, sort_keys=True)
        if key not in self.cache:
            self.cache[key] = BUILD[cond["k"]](self, cond)
        return self.cache[key]

    def exit_ma(self, n):
        if n not in self.ma_exit:
            self.ma_exit[n] = (self.C < self.C.rolling(n).mean()).fillna(False).values
        return self.ma_exit[n]


@njit(cache=True)
def _supertrend(H, L, C, atr, mult):
    T, N = C.shape
    out = np.zeros((T, N), dtype=np.int8)
    for j in range(N):
        fub = np.nan
        flb = np.nan
        dr = 0
        for t in range(T):
            a = atr[t, j]
            if np.isnan(a) or np.isnan(C[t, j]):
                fub = np.nan
                flb = np.nan
                dr = 0
                continue
            hl2 = (H[t, j] + L[t, j]) / 2.0
            ub = hl2 + mult * a
            lb = hl2 - mult * a
            if np.isnan(fub):
                fub, flb, dr = ub, lb, 1
            else:
                pc = C[t - 1, j]
                nfub = ub if (ub < fub or pc > fub) else fub
                nflb = lb if (lb > flb or pc < flb) else flb
                if dr == 1 and C[t, j] < nflb:
                    dr = -1
                elif dr == -1 and C[t, j] > nfub:
                    dr = 1
                fub, flb = nfub, nflb
            out[t, j] = dr
    return out


def _within(x_bool_df, k):
    return x_bool_df.astype(float).rolling(k, min_periods=1).max() > 0


def _b_ma_trend(c, p):
    ma = c.C.rolling(p["n"]).mean()
    return c.arr((c.C > ma) & (ma > ma.shift(5)))


def _b_ma_cross(c, p):
    f, s = c.C.rolling(p["f"]).mean(), c.C.rolling(p["s"]).mean()
    x = (f > s) & (f.shift(1) <= s.shift(1))
    return c.arr(_within(x, 3))


def _b_macd(c, p):
    dif = c.C.ewm(span=12, adjust=False).mean() - c.C.ewm(span=26, adjust=False).mean()
    dea = dif.ewm(span=9, adjust=False).mean()
    osc = dif - dea
    if p["mode"] == "cross":
        return c.arr(_within((dif > dea) & (dif.shift(1) <= dea.shift(1)), 3) & (dif > dea))
    return c.arr((dif > 0) & (osc > 0) & (osc > osc.shift(1)))


def _rsi(c, n=14):
    ch = c.C.diff()
    up = ch.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-ch.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)


def _b_rsi(c, p):
    r = _rsi(c)
    if p["mode"] == "pull":      # 超賣回升：上穿門檻
        return c.arr(_within((r.shift(1) < p["th"]) & (r >= p["th"]), 3))
    return c.arr((r > p["th"]) & (r > r.shift(1)))


def _b_kd(c, p):
    ll, hh = c.L.rolling(9).min(), c.H.rolling(9).max()
    rsv = ((c.C - ll) / (hh - ll) * 100)
    k = rsv.ewm(alpha=1 / 3, adjust=False).mean()
    dd = k.ewm(alpha=1 / 3, adjust=False).mean()
    return c.arr(_within((k > dd) & (k.shift(1) <= dd.shift(1)), 2) & (k < p["th"] + 20))


def _b_boll(c, p):
    m, s = c.C.rolling(20).mean(), c.C.rolling(20).std(ddof=0)
    if p["mode"] == "break":
        return c.arr(c.C > m + 2 * s)
    low = m - 2 * s
    return c.arr(_within(c.C.shift(1) < low.shift(1), 2) & (c.C > low))


def _b_donchian(c, p):
    return c.arr(c.C > c.H.rolling(p["n"]).max().shift(1))


def _b_supertrend(c, p):
    atr10 = c.TR.ewm(alpha=1 / 10, adjust=False, min_periods=10).mean().values
    d = _supertrend(c.Hnp, c.Lnp, c.Cnp, atr10, float(p["m"]))
    up = d == 1
    if p["mode"] == "state":
        return up
    flip = up & (np.roll(d, 1, axis=0) == -1)
    f = pd.DataFrame(flip)
    return (f.astype(float).rolling(3, min_periods=1).max() > 0).values & up


def _b_volprice(c, p):
    return c.arr((c.V > p["m"] * c.V20) & (c.C > c.O) & (c.C >= c.L + (c.H - c.L) * 2 / 3))


def _b_weekly(c, p):
    Cw = c.C.resample("W-FRI").last()
    ma = Cw.rolling(p["n"]).mean()
    wk = ((Cw > ma) & (ma > ma.shift(2))).shift(1).fillna(False)      # 只用「上一個完整週」
    daily = wk.reindex(wk.index.union(c.dates)).bfill().reindex(c.dates).fillna(False).astype(bool)
    return daily.values


def _b_smc(c, p):
    """簡化 SMC：前後各 3 根的擺盪高點在第 3 根之後才確認（無未來資料）；
    BOS = 近 3 日內收盤上穿最近確認的擺盪高點，且最近擺盪低點比 20 日前的擺盪低點高（HH/HL 結構）。"""
    sh = c.H.where(c.H == c.H.rolling(7, center=True).max()).shift(3).ffill()
    sl = c.L.where(c.L == c.L.rolling(7, center=True).min()).shift(3).ffill()
    bos = _within((c.C > sh) & (c.C.shift(1) <= sh.shift(1)), 3)
    return c.arr(bos & (sl > sl.shift(20)))


def _b_idx_trend(c, p):
    ma = c.idx.rolling(p["n"]).mean()
    ok = (c.idx > ma).fillna(False).values
    return np.repeat(ok[:, None], c.N, axis=1)


def _chip_ratio(c, key, n):
    x = c.d["inst_" + key].fillna(0)
    return x.rolling(n).sum() / c.V.rolling(n).sum()


def _b_inst_buy(c, p):
    key = {"foreign": "foreign_total", "trust": "trust", "all": "inst_total"}[p["who"]]
    r = _chip_ratio(c, key, p["n"])
    return c.arr(r > p["th"] / 100.0)


def _b_inst_streak(c, p):
    key = {"foreign": "foreign_total", "trust": "trust", "all": "inst_total"}[p["who"]]
    x = (c.d["inst_" + key] > 0).astype(float)
    return c.arr(x.rolling(p["d"]).min() == 1)


def _b_both_buy(c, p):
    a = _chip_ratio(c, "foreign_total", p["n"])
    b = _chip_ratio(c, "trust", p["n"])
    return c.arr((a > p["th"] / 100.0) & (b > 0))


def _b_rev_yoy(c, p):
    return c.arr(c.d["yoy"] > p["th"] / 100.0)


def _b_rev_accel(c, p):
    return c.arr((c.d["yoy3"] > p["th"] / 100.0) & (c.d["yoy"] > c.d["yoy_prev"]))


def _b_rev_fresh(c, p):
    fresh = (c.d["rev_age"] <= p["w"])[:, None]
    return c.arr(c.d["yoy"] > p["th"] / 100.0) & fresh


def _b_us_night(c, p):
    r = c.d["us"][p["sym"]]
    ok = np.nan_to_num(r, nan=-9) > p["th"] / 100.0
    return np.repeat(ok[:, None], c.N, axis=1)


def _evmask(c, typ, lo, hi):
    """某類事件影響日落在 [t+lo, t+hi] 的日子為 True（lo/hi 可為負 = 事件已過）。"""
    m = np.zeros(c.T, dtype=bool)
    for p in c.d["evpos"].get(typ, []):
        a, b = max(0, p - hi), min(c.T - 1, p - lo)
        if a <= b:
            m[a:b + 1] = True
    return m


def _b_ev_avoid(c, p):       # 事件前 b 日不進場（訊號日 t，隔日買，事件日在 t+1..t+b）
    ok = ~_evmask(c, p["t"], 1, p["b"])
    return np.repeat(ok[:, None], c.N, axis=1)


def _b_ev_before(c, p):      # 只在事件前 b 日內進場（卡位）
    ok = _evmask(c, p["t"], 1, p["b"])
    return np.repeat(ok[:, None], c.N, axis=1)


def _b_ev_after(c, p):       # 只在事件後 a 日內進場（反應）
    ok = _evmask(c, p["t"], -p["a"] + 1, 0)
    return np.repeat(ok[:, None], c.N, axis=1)


BUILD = {
    "ma_trend": _b_ma_trend, "ma_cross": _b_ma_cross, "macd": _b_macd, "rsi": _b_rsi, "kd": _b_kd, "boll": _b_boll,
    "donchian": _b_donchian, "supertrend": _b_supertrend, "volprice": _b_volprice, "weekly": _b_weekly, "smc": _b_smc,
    "idx_trend": _b_idx_trend,
    "inst_buy": _b_inst_buy, "inst_streak": _b_inst_streak, "both_buy": _b_both_buy,
    "rev_yoy": _b_rev_yoy, "rev_accel": _b_rev_accel, "rev_fresh": _b_rev_fresh, "us_night": _b_us_night,
    "ev_avoid": _b_ev_avoid, "ev_before": _b_ev_before, "ev_after": _b_ev_after,
}

# 參數格（離散，才算得出「評估過多少個策略」）。cross 的 (f,s) 用索引表示成 pair 字串。
GRID = {
    "tech": {
        "ma_trend": {"n": [10, 20, 60]},
        "ma_cross": {"f": [5, 10, 20], "s": [20, 60]},
        "macd": {"mode": ["cross", "zero"]},
        "rsi": {"mode": ["pull", "mom"], "th": [30, 40, 50, 55, 60, 70]},
        "kd": {"th": [20, 30, 50]},
        "boll": {"mode": ["break", "revert"]},
        "donchian": {"n": [10, 20, 55]},
        "supertrend": {"m": [2, 3], "mode": ["state", "flip"]},
        "volprice": {"m": [1.5, 2.0, 3.0]},
        "weekly": {"n": [10, 30]},
        "smc": {"x": [0]},
        "idx_trend": {"n": [20, 60, 120]},
    },
    "chip": {
        "inst_buy": {"who": ["foreign", "trust", "all"], "n": [3, 5, 10], "th": [0.5, 1.0, 2.0, 4.0]},
        "inst_streak": {"who": ["foreign", "trust", "all"], "d": [3, 5]},
        "both_buy": {"n": [3, 5, 10], "th": [0.5, 1.0, 2.0]},
    },
    "news": {
        "rev_yoy": {"th": [10, 20, 40]},
        "rev_accel": {"th": [10, 20]},
        "rev_fresh": {"th": [10, 20, 30], "w": [3, 5, 10]},
        "us_night": {"sym": ["^SOX", "^IXIC", "TSM"], "th": [0, 1]},
        "ev_avoid": {"t": ["fomc", "nfp", "settle", "tsmc"], "b": [1, 2]},
        "ev_before": {"t": ["fomc", "tsmc", "exdiv", "settle"], "b": [3, 7]},
        "ev_after": {"t": ["fomc", "tsmc", "exdiv", "settle"], "a": [3, 7]},
    },
}
FILTERS = {"idx_trend", "ev_avoid"}        # 純濾網：不能單獨當進場觸發
CATS = ["tech", "chip", "news"]
EXIT_GRID = {"atr_k": [1.5, 2.0, 3.0], "rr": [0, 1.5, 2.0, 3.0], "trail": [0, 2.5, 3.5], "ma": [0, 10, 20], "maxhold": [10, 20, 40]}
RISK_GRID = {"risk": [0.01, 0.02, 0.03], "maxpos": [2, 3, 4, 5]}
RANKS = ["mom20", "volratio", "turnover"]
CLASSES = ["單一技術", "單一籌碼", "單一消息", "技術+籌碼", "技術+消息", "籌碼+消息", "三面全開"]
CLASS_SET = {"單一技術": ("tech",), "單一籌碼": ("chip",), "單一消息": ("news",), "技術+籌碼": ("tech", "chip"),
             "技術+消息": ("tech", "news"), "籌碼+消息": ("chip", "news"), "三面全開": ("tech", "chip", "news")}
SET_CLASS = {v: k for k, v in CLASS_SET.items()}
START_MIX = {"單一技術": 14, "單一籌碼": 8, "單一消息": 8, "技術+籌碼": 12, "技術+消息": 12, "籌碼+消息": 12, "三面全開": 34}


def rand_cond(cat, rng):
    k = rng.choice(list(GRID[cat]))
    c = {"k": k}
    for pn, vals in GRID[cat][k].items():
        c[pn] = rng.choice(vals)
    if k == "ma_cross" and c["f"] >= c["s"]:
        c["f"] = 5 if c["s"] == 20 else 10
    return c


def has_trigger(conds):
    return any(c["k"] not in FILTERS for c in conds)


def rand_genome(cats, rng):
    g = {"tech": [], "chip": [], "news": []}
    for cat in cats:
        g[cat] = [rand_cond(cat, rng)]
        if rng.random() < 0.3:
            c2 = rand_cond(cat, rng)
            if c2["k"] != g[cat][0]["k"]:
                g[cat].append(c2)
    g["exit"] = {k: rng.choice(v) for k, v in EXIT_GRID.items()}
    g["risk"] = {k: rng.choice(v) for k, v in RISK_GRID.items()}
    g["rank"] = rng.choice(RANKS)
    return repair(g, rng)


def active_cats(g):
    return tuple(c for c in CATS if g[c])


def gclass(g):
    return SET_CLASS[active_cats(g)]


def repair(g, rng):
    """保證：沒有重複條件類型、每個啟用面向至少一個真正的觸發條件、整體至少一個觸發。"""
    for cat in CATS:
        seen, out = set(), []
        for c in g[cat]:
            if c["k"] in seen:
                continue
            seen.add(c["k"])
            if c["k"] == "ma_cross" and c["f"] >= c["s"]:
                c["f"] = 5 if c["s"] == 20 else 10
            out.append(c)
        g[cat] = out[:2]
        if g[cat] and not has_trigger(g[cat]):
            if cat == "tech" or cat == "news":
                trig = [k for k in GRID[cat] if k not in FILTERS]
                c = {"k": rng.choice(trig)}
                for pn, vals in GRID[cat][c["k"]].items():
                    c[pn] = rng.choice(vals)
                g[cat].append(c)
                g[cat] = g[cat][-1:] + g[cat][:-1]
                g[cat] = g[cat][:2]
    return g


def ghash(g):
    return hashlib.md5(json.dumps(g, sort_keys=True).encode()).hexdigest()[:10]


def mutate(g, rng, strength=1):
    """小幅突變：把 strength 個參數挪到格子上相鄰的值；偶爾換掉或增減一個條件。"""
    g = json.loads(json.dumps(g))
    for _ in range(strength):
        r = rng.random()
        if r < 0.35:
            cats = [c for c in CATS if g[c]]
            if cats:
                cat = rng.choice(cats)
                c = rng.choice(g[cat])
                pn = [p for p in GRID[cat][c["k"]] if len(GRID[cat][c["k"]][p]) > 1]
                if pn:
                    p = rng.choice(pn)
                    vals = GRID[cat][c["k"]][p]
                    i = vals.index(c[p]) if c[p] in vals else 0
                    c[p] = vals[max(0, min(len(vals) - 1, i + rng.choice([-1, 1])))]
        elif r < 0.45:
            cats = [c for c in CATS if g[c]]
            if cats:
                cat = rng.choice(cats)
                i = rng.randrange(len(g[cat]))
                g[cat][i] = rand_cond(cat, rng)
        elif r < 0.55:
            cats = [c for c in CATS if g[c]]
            if cats:
                cat = rng.choice(cats)
                if len(g[cat]) < 2:
                    g[cat].append(rand_cond(cat, rng))
                elif len(g[cat]) == 2:
                    g[cat].pop(rng.randrange(2))
        elif r < 0.8:
            k = rng.choice(list(EXIT_GRID))
            vals = EXIT_GRID[k]
            i = vals.index(g["exit"][k])
            g["exit"][k] = vals[max(0, min(len(vals) - 1, i + rng.choice([-1, 1])))]
        elif r < 0.95:
            k = rng.choice(list(RISK_GRID))
            vals = RISK_GRID[k]
            i = vals.index(g["risk"][k])
            g["risk"][k] = vals[max(0, min(len(vals) - 1, i + rng.choice([-1, 1])))]
        else:
            g["rank"] = rng.choice(RANKS)
    return repair(g, rng)


def crossover(a, b, rng, cats_lock=None):
    """交叉：每個面向的條件組整組從 A 或 B 拿；出場、風控、排序各自擲骰。
    cats_lock 不為 None 時（類別聯盟）面向集合固定，不允許跑出別的類別。"""
    g = {"tech": [], "chip": [], "news": []}
    for cat in CATS:
        src = a if rng.random() < 0.5 else b
        g[cat] = json.loads(json.dumps(src[cat]))
    g["exit"] = {k: (a if rng.random() < 0.5 else b)["exit"][k] for k in EXIT_GRID}
    g["risk"] = {k: (a if rng.random() < 0.5 else b)["risk"][k] for k in RISK_GRID}
    g["rank"] = (a if rng.random() < 0.5 else b)["rank"]
    if cats_lock is not None:
        for cat in CATS:
            if cat in cats_lock and not g[cat]:
                src = a if a[cat] else b
                g[cat] = json.loads(json.dumps(src[cat])) if src[cat] else [rand_cond(cat, rng)]
            if cat not in cats_lock:
                g[cat] = []
    elif not any(g[c] for c in CATS):
        cc = rng.choice(CATS)
        g[cc] = [rand_cond(cc, rng)]
    return repair(g, rng)


def force_cats(g, cats, rng):
    for cat in CATS:
        if cat in cats and not g[cat]:
            g[cat] = [rand_cond(cat, rng)]
        if cat not in cats:
            g[cat] = []
    return repair(g, rng)


# ============================================================== 3. 模擬器
@njit(cache=True)
def _sim(O, Hh, Ll, C, A, sig, score, exma, t0, t1, stopk, rr, trailk, maxhold, risk, maxpos,
         cash0, fee, tax, slip, minfee, cool, maxtr):
    N = O.shape[1]
    nd = t1 - t0 + 1
    eq = np.zeros(nd)
    pj = -np.ones(maxpos, dtype=np.int64)
    psh = np.zeros(maxpos)
    pent = np.zeros(maxpos)
    pstop = np.zeros(maxpos)
    ptgt = np.zeros(maxpos)
    phh = np.zeros(maxpos)
    patr = np.zeros(maxpos)
    pet = np.zeros(maxpos, dtype=np.int64)
    pmae = np.zeros(maxpos)
    pnext = np.zeros(maxpos, dtype=np.bool_)
    pcost = np.zeros(maxpos)
    pdist = np.zeros(maxpos)
    plast = np.zeros(maxpos)
    last_exit = -100 * np.ones(N, dtype=np.int64)
    held = np.zeros(N, dtype=np.bool_)
    tj = np.zeros(maxtr, dtype=np.int64)
    te = np.zeros(maxtr, dtype=np.int64)
    tx = np.zeros(maxtr, dtype=np.int64)
    tent = np.zeros(maxtr)
    tex = np.zeros(maxtr)
    tsh = np.zeros(maxtr)
    tret = np.zeros(maxtr)
    tmae = np.zeros(maxtr)
    tdist = np.zeros(maxtr)
    trs = np.zeros(maxtr, dtype=np.int64)
    nt = 0
    cash = cash0
    candj = np.zeros(N, dtype=np.int64)
    for t in range(t0, t1 + 1):
        # ---- 當日權益（用前一日收盤）決定部位大小
        eqp = cash
        for s in range(maxpos):
            if pj[s] >= 0:
                eqp += psh[s] * plast[s]
        # ---- 1. 開盤進場（訊號來自 t-1 收盤）
        nfree = 0
        for s in range(maxpos):
            if pj[s] < 0:
                nfree += 1
        if nfree > 0:
            nc = 0
            for j in range(N):
                if sig[t - 1, j] and not held[j] and (t - last_exit[j]) > cool:
                    o = O[t, j]
                    a = A[t - 1, j]
                    sc = score[t - 1, j]
                    if np.isnan(o) or np.isnan(a) or np.isnan(sc) or np.isnan(C[t - 1, j]):
                        continue
                    if o >= 1.095 * C[t - 1, j]:      # 開盤鎖漲停買不到
                        continue
                    candj[nc] = j
                    nc += 1
            # 依 score 由大到小取前 nfree 檔
            for _ in range(min(nfree, nc)):
                bi = -1
                bs = -1e300
                for q in range(nc):
                    jj = candj[q]
                    if jj >= 0 and score[t - 1, jj] > bs:
                        bs = score[t - 1, jj]
                        bi = q
                if bi < 0:
                    break
                j = candj[bi]
                candj[bi] = -1
                o = O[t, j]
                stop = o - stopk * A[t - 1, j]
                if stop <= 0:
                    continue
                dist = (o - stop) / o
                buy_eff = o * (1 + slip)
                val = min(eqp * risk / dist, eqp / maxpos, cash / (1 + fee))
                if val < 5000.0:
                    continue
                sh = val / buy_eff
                bfee = max(minfee, sh * buy_eff * fee)
                if sh * buy_eff + bfee > cash:
                    continue
                for s in range(maxpos):
                    if pj[s] < 0:
                        pj[s] = j
                        psh[s] = sh
                        pent[s] = o
                        pstop[s] = stop
                        ptgt[s] = o + rr * (o - stop) if rr > 0 else 1e18
                        phh[s] = o
                        patr[s] = A[t - 1, j]
                        pet[s] = t
                        pmae[s] = 0.0
                        pnext[s] = False
                        pcost[s] = sh * buy_eff + bfee
                        pdist[s] = dist
                        plast[s] = o
                        held[j] = True
                        cash -= pcost[s]
                        break
        # ---- 2. 盤中／收盤處理持股
        for s in range(maxpos):
            j = pj[s]
            if j < 0:
                continue
            if np.isnan(O[t, j]) or np.isnan(C[t, j]) or np.isnan(Hh[t, j]) or np.isnan(Ll[t, j]):
                continue            # 停牌／缺資料：照舊持有、以最後有效價計值
            exit_px = -1.0
            reason = 0
            if pnext[s]:                       # 前一日收盤已判定要出場 -> 今天開盤賣
                exit_px = O[t, j]
                reason = 4
            elif O[t, j] <= pstop[s]:
                exit_px = O[t, j]
                reason = 1
            elif Ll[t, j] <= pstop[s]:
                exit_px = pstop[s]
                reason = 1
            elif Hh[t, j] >= ptgt[s]:
                exit_px = max(O[t, j], ptgt[s])
                reason = 2
            if exit_px < 0 and t == t1:        # 段尾強制平倉（讓每回合的報酬是已實現的）
                exit_px = C[t, j]
                reason = 3
            if exit_px >= 0:
                eff = exit_px * (1 - slip)
                gross = psh[s] * eff
                proceeds = gross - max(minfee, gross * fee) - gross * tax
                cash += proceeds
                if nt < maxtr:
                    tj[nt] = j
                    te[nt] = pet[s]
                    tx[nt] = t
                    tent[nt] = pent[s]
                    tex[nt] = exit_px
                    tsh[nt] = psh[s]
                    tret[nt] = proceeds / pcost[s] - 1.0
                    tmae[nt] = pmae[s]
                    tdist[nt] = pdist[s]
                    trs[nt] = reason
                    nt += 1
                held[j] = False
                last_exit[j] = t
                pj[s] = -1
                continue
            # 仍持有：更新最高價、MAE、移動停損（隔日生效）、收盤型出場旗標
            if Hh[t, j] > phh[s]:
                phh[s] = Hh[t, j]
            m = Ll[t, j] / pent[s] - 1.0
            if m < pmae[s]:
                pmae[s] = m
            if trailk > 0:
                ns = phh[s] - trailk * patr[s]
                if ns > pstop[s]:
                    pstop[s] = ns
            if exma[t, j] or (t - pet[s] + 1) >= maxhold:
                pnext[s] = True
        # ---- 3. 收盤權益
        e = cash
        for s in range(maxpos):
            if pj[s] >= 0:
                if not np.isnan(C[t, pj[s]]):
                    plast[s] = C[t, pj[s]]
                e += psh[s] * plast[s]
        eq[t - t0] = e
    return eq, nt, tj[:nt], te[:nt], tx[:nt], tent[:nt], tex[:nt], tsh[:nt], tret[:nt], tmae[:nt], tdist[:nt], trs[:nt]


def signal_matrix(ctx: Ctx, g):
    s = ctx.elig.copy()
    for cat in CATS:
        for c in g[cat]:
            s &= ctx.get(c)
    return s


def run_genome(ctx: Ctx, g, t0, t1, cash0=CASH0, extra_sig=None):
    sig = signal_matrix(ctx, g)
    if extra_sig is not None:
        sig &= extra_sig
    e, r, k = g["exit"], g["risk"], g["rank"]
    exma = ctx.exit_ma(e["ma"]) if e["ma"] else ctx.no_exit
    return _sim(ctx.Onp, ctx.Hnp, ctx.Lnp, ctx.Cnp, ctx.Anp, sig, ctx.scores[k], exma,
                t0, t1, float(e["atr_k"]), float(e["rr"]), float(e["trail"]), int(e["maxhold"]), float(r["risk"]), int(r["maxpos"]),
                cash0, FEE, TAX, SLIP, MINFEE, COOL, 4000)


def tr_df(ctx: Ctx, out):
    eq, nt, tj, te, tx, tent, tex, tsh, tret, tmae, tdist, trs = out
    rs = np.array(["", "停損", "停利", "段尾平倉", "均線/到期"])
    return pd.DataFrame({
        "code": [ctx.codes[j] for j in tj], "entry_date": ctx.dates[te].strftime("%Y-%m-%d"), "entry_px": tent,
        "exit_date": ctx.dates[tx].strftime("%Y-%m-%d"), "exit_px": tex, "shares": tsh, "ret": tret,
        "hold_days": tx - te + 1, "mae": tmae, "r_mult": tret / np.maximum(tdist, 1e-6), "reason": rs[trs],
    })


def metrics(out, nd=None):
    eq, nt, tj, te, tx, tent, tex, tsh, tret = out[:9]
    e = np.concatenate([[CASH0], eq])
    ret = e[-1] / e[0] - 1
    peak = np.maximum.accumulate(e)
    dd = float(np.max(1 - e / peak))
    nd = len(eq)
    cagr = (max(1 + ret, 1e-6)) ** (252 / nd) - 1
    dr = np.diff(e) / e[:-1]
    sd = dr.std()
    sharpe = float(dr.mean() / sd * math.sqrt(252)) if sd > 0 else 0.0
    n = int(nt)
    if n:
        w, l = tret[tret > 0], tret[tret <= 0]
        win = len(w) / n
        payoff = (w.mean() / abs(l.mean())) if len(w) and len(l) and l.mean() != 0 else (9.99 if len(w) else 0.0)
        hold = float((tx - te + 1).mean())
        exp_ = float(tret.mean())
    else:
        win = payoff = hold = exp_ = 0.0
    return {"ret": float(ret), "cagr": float(cagr), "dd": dd, "calmar": float(cagr / max(dd, 0.03)), "sharpe": sharpe, "n": n,
            "win": float(win), "payoff": float(payoff), "hold": hold, "exp": exp_, "mineq": float(e.min() / CASH0)}


def round_score(m):
    """回合分數 = 報酬 / 最大回撤（回撤至少算 4%），再依出手次數打折（少於 8 筆不給滿分）。沒出手 = 負分。"""
    if m["n"] < 3:
        return -1.0
    base = m["ret"] / max(m["dd"], 0.04)
    return base * math.sqrt(min(1.0, m["n"] / 8.0)) if base > 0 else base


# ============================================================== 4. 淘汰賽
def rounds_train(ctx):
    segs = []
    for y in range(2012, 2021):
        for a, b in (("01-01", "06-30"), ("07-01", "12-31")):
            i0 = int(ctx.dates.searchsorted(pd.Timestamp(f"{y}-{a}")))
            i1 = int(ctx.dates.searchsorted(pd.Timestamp(f"{y}-{b}"), side="right")) - 1
            segs.append((f"{y}{'H1' if a == '01-01' else 'H2'}", i0, i1))
    return segs


def describe_features(g):
    f = {c: bool(g[c]) for c in CATS}
    f["atr_k"], f["rr"], f["trail"], f["ma"], f["maxhold"] = (g["exit"][k] for k in ("atr_k", "rr", "trail", "ma", "maxhold"))
    f["risk"], f["maxpos"] = g["risk"]["risk"], g["risk"]["maxpos"]
    f["kinds"] = [c["k"] for cat in CATS for c in g[cat]]
    return f


def discussion(rows, rname):
    """從前 20% 與後 20% 的差異用白話寫出『討論紀錄』。rows: list of (score, metrics, genome)。"""
    act = [r for r in rows if r[1]["n"] >= 3] or rows
    k = max(5, len(rows) // 5)
    top, bot = rows[:k], rows[-k:]
    ft = lambda rs: [describe_features(r[2]) for r in rs]
    T, B = ft(top), ft(bot)
    avg = lambda L, key: float(np.mean([x[key] for x in L]))
    lines = []
    for lab, key in (("技術面", "tech"), ("籌碼面", "chip"), ("消息面", "news")):
        a, b = avg(T, key), avg(B, key)
        if abs(a - b) >= 0.15:
            lines.append(f"前段班{'更常' if a > b else '較少'}使用{lab}（{a:.0%} vs 後段班 {b:.0%}）")
    kt, kb = Counter(x for f in T for x in f["kinds"]), Counter(x for f in B for x in f["kinds"])
    top_kinds = [f"{n}（前段 {kt[n]} 人／後段 {kb.get(n, 0)} 人）" for n, _ in kt.most_common(3) if kt[n] - kb.get(n, 0) >= 3]
    if top_kinds:
        lines.append("前段班偏好的條件：" + "、".join(top_kinds))
    bad_kinds = [f"{n}（後段 {kb[n]} 人／前段 {kt.get(n, 0)} 人）" for n, _ in kb.most_common(3) if kb[n] - kt.get(n, 0) >= 3]
    if bad_kinds:
        lines.append("被淘汰者的共同條件：" + "、".join(bad_kinds))
    for key, lab, fmt in (("atr_k", "停損寬度", "{:.1f} 倍 ATR"), ("maxhold", "最長持有", "{:.0f} 天"), ("maxpos", "同時持股上限", "{:.1f} 檔"), ("risk", "每筆風險", "{:.1%}")):
        a, b = avg(T, key), avg(B, key)
        if abs(a - b) / max(abs(b), 1e-9) >= 0.18:
            lines.append(f"{lab}：前段班平均 {fmt.format(a)}，後段班 {fmt.format(b)}")
    for key, lab in (("trail", "移動停損"), ("ma", "跌破均線出場")):
        a, b = np.mean([x[key] > 0 for x in T]), np.mean([x[key] > 0 for x in B])
        if abs(a - b) >= 0.2:
            lines.append(f"{lab}：前段班開啟率 {a:.0%}，後段班 {b:.0%}")
    nt, nb = np.mean([r[1]["n"] for r in top]), np.mean([r[1]["n"] for r in bot])
    lines.append(f"出手次數：前段班平均 {nt:.0f} 筆，後段班 {nb:.0f} 筆；沒出手（少於 3 筆）的人有 {sum(r[1]['n'] < 3 for r in rows)} 位")
    bust = sum(r[1]["mineq"] < BUST for r in rows)
    if bust:
        lines.append(f"權益曾跌破 7 成直接出局：{bust} 人")
    return lines


def run_league(ctx, name, seed, cats_lock=None, pop=100, verbose=False):
    rng = random.Random(seed)
    segs = rounds_train(ctx)
    people = []     # dict(id, genome, born, lineage)
    nid = [0]

    def newp(g, born, how):
        nid[0] += 1
        return {"id": nid[0], "g": g, "born": born, "how": how, "wins": 0}

    if cats_lock is None:
        for cls, n in START_MIX.items():
            for _ in range(n):
                people.append(newp(rand_genome(CLASS_SET[cls], rng), 0, "開局"))
    else:
        for _ in range(pop):
            people.append(newp(rand_genome(cats_lock, rng), 0, "開局"))
    seen = {ghash(p["g"]): p["g"] for p in people}
    hist, disc, evals = [], [], 0
    for ri, (rname, i0, i1) in enumerate(segs):
        rows = []
        for p in people:
            out = run_genome(ctx, p["g"], i0, i1)
            m = metrics(out)
            sc = -99.0 if m["mineq"] < BUST else round_score(m)
            rows.append((sc, m, p["g"], p))
            evals += 1
        rows.sort(key=lambda r: -r[0])
        n_keep = pop // 2
        surv, dead = rows[:n_keep], rows[n_keep:]
        disc.append((rname, discussion([(r[0], r[1], r[2]) for r in rows], rname)))
        cl_all = Counter(gclass(r[2]) for r in rows)
        cl_sv = Counter(gclass(r[2]) for r in surv)
        gene_cnt = Counter(c["k"] for r in surv for cat in CATS for c in r[2][cat])
        hist.append({"round": rname, "n_dead": len(dead), "best_score": rows[0][0], "best_ret": rows[0][1]["ret"], "median_ret": float(np.median([r[1]["ret"] for r in rows])),
                     "class_all": dict(cl_all), "class_surv": dict(cl_sv), "gene_surv": dict(gene_cnt), "ids_dead": [r[3]["id"] for r in dead],
                     "ids_surv": [r[3]["id"] for r in surv],
                     "rows": [(r[3]["id"], gclass(r[2]), r[3]["how"], r[3]["wins"], r[0], r[1]["ret"], r[1]["dd"], r[1]["win"], r[1]["n"], r[1]["hold"], "存活" if k < n_keep else "淘汰")
                              for k, r in enumerate(rows)], "top": [(r[3]["id"], r[0], r[1]["ret"], r[1]["win"], r[1]["n"]) for r in rows[:5]],
                     "bust": int(sum(r[1]["mineq"] < BUST for r in rows))})
        if ri == len(segs) - 1:
            final = [r[3] for r in surv]
            break
        # --- 倖存者互相討論：前 25% 當導師；其餘倖存者小幅自我調整
        for r in surv:
            r[3]["wins"] += 1
        mentors = [r[2] for r in surv[: max(4, n_keep // 2)]]
        nxt = []
        for i, r in enumerate(surv):
            p = r[3]
            if i >= 12 and rng.random() < 0.5:             # 非菁英倖存者：自己小幅突變（變成新的策略，戰績歸零）
                g2 = mutate(p["g"], rng, 1)
                if cats_lock is not None:
                    g2 = force_cats(g2, cats_lock, rng)
                p = newp(g2, ri + 1, "自我調整")
                p["wins"] = 0
            nxt.append(p)
        need = pop - len(nxt)
        n_imm = max(5, need // 5)
        for _ in range(need - n_imm):
            a, b = rng.sample(mentors, 2) if len(mentors) > 1 else (mentors[0], mentors[0])
            g2 = crossover(a, b, rng, cats_lock)
            if rng.random() < 0.7:
                g2 = mutate(g2, rng, 1)
            if cats_lock is not None:
                g2 = force_cats(g2, cats_lock, rng)
            nxt.append(newp(g2, ri + 1, "交叉"))
        for _ in range(n_imm):
            if cats_lock is None:
                cls = rng.choice(CLASSES)
                g2 = rand_genome(CLASS_SET[cls], rng)
            else:
                g2 = rand_genome(cats_lock, rng)
            nxt.append(newp(g2, ri + 1, "新秀"))
        people = nxt
        for p in people:
            seen[ghash(p["g"])] = p["g"]
    return {"name": name, "seed": seed, "cats_lock": cats_lock, "final": final, "hist": hist, "disc": disc, "evals": evals, "genomes": seen}


# ============================================================== 5. 統計：deflated Sharpe、隨機對照
def norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def norm_ppf(p):
    from scipy.stats import norm
    return float(norm.ppf(p))


def deflated_sharpe(daily_ret, n_trials, trial_sharpe_var):
    """Bailey & López de Prado 的 deflated Sharpe。回傳 (年化 SR, 期望最大 SR0 年化, DSR 機率)。
    單位是日報酬；n_trials = 評估過的策略數；trial_sharpe_var = 這些策略日 Sharpe 的變異數。"""
    from scipy.stats import skew, kurtosis
    r = np.asarray(daily_ret)
    T = len(r)
    sr = r.mean() / r.std()
    g3, g4 = skew(r), kurtosis(r, fisher=False)
    em = 0.5772156649
    sr0 = math.sqrt(trial_sharpe_var) * ((1 - em) * norm_ppf(1 - 1 / n_trials) + em * norm_ppf(1 - 1 / (n_trials * math.e)))
    den = math.sqrt(max(1e-9, 1 - g3 * sr + (g4 - 1) / 4 * sr ** 2))
    dsr = norm_cdf((sr - sr0) * math.sqrt(T - 1) / den)
    return sr * math.sqrt(252), sr0 * math.sqrt(252), dsr


# ============================================================== 6. 白話規則與練習室腳本
COND_TXT = {
    "ma_trend": lambda c: f"收盤站上 {c['n']} 日均線，且該均線比 5 天前更高（趨勢向上）",
    "ma_cross": lambda c: f"{c['f']} 日均線近 3 天內上穿 {c['s']} 日均線",
    "macd": lambda c: "MACD 的 DIF 近 3 天內上穿 DEA 且仍在上方" if c["mode"] == "cross" else "DIF 與柱狀體 OSC 都在 0 軸上方且 OSC 持續放大",
    "rsi": lambda c: (f"RSI(14) 近 3 天由 {c['th']} 以下回升穿越（超賣反彈）" if c["mode"] == "pull" else f"RSI(14) 大於 {c['th']} 且比前一天高（強勢動能）"),
    "kd": lambda c: f"KD(9,3,3) 的 K 近 2 天內上穿 D，且 K 值低於 {c['th'] + 20}",
    "boll": lambda c: "收盤突破布林上軌(20,2)" if c["mode"] == "break" else "前兩天曾跌破布林下軌，今天收回下軌之上（反轉）",
    "donchian": lambda c: f"收盤突破前 {c['n']} 日最高價（唐奇安通道）",
    "supertrend": lambda c: (f"Supertrend(10,{c['m']}) 為多頭" if c["mode"] == "state" else f"Supertrend(10,{c['m']}) 近 3 天剛翻多"),
    "volprice": lambda c: f"成交量大於 20 日均量 {c['m']} 倍、收紅，且收在當日振幅的上三分之一",
    "weekly": lambda c: f"週 K：上一個完整週的收盤在 {c['n']} 週均線之上且均線上揚（多週期方向向上）",
    "smc": lambda c: "SMC 結構：近 3 天內收盤突破最近確認的擺盪高點（BOS），且最近擺盪低點高於 20 天前（HH/HL）",
    "idx_trend": lambda c: f"大盤（加權指數）收盤在 {c['n']} 日均線之上",
    "inst_buy": lambda c: f"{ {'foreign': '外資', 'trust': '投信', 'all': '三大法人合計'}[c['who']] } 近 {c['n']} 日淨買超股數占成交量 {c['th']}% 以上",
    "inst_streak": lambda c: f"{ {'foreign': '外資', 'trust': '投信', 'all': '三大法人合計'}[c['who']] } 連續 {c['d']} 日買超",
    "both_buy": lambda c: f"外資近 {c['n']} 日買超占成交量 {c['th']}% 以上，且投信同期也是買超",
    "rev_yoy": lambda c: f"最新公布的月營收年增率 > {c['th']}%（法定公布日次月 10 日後才算）",
    "rev_accel": lambda c: f"近 3 個月營收年增率均值 > {c['th']}% 且最新月年增率比上月更高",
    "rev_fresh": lambda c: f"營收公布後 {c['w']} 個交易日內，且該月年增率 > {c['th']}%",
    "us_night": lambda c: f"美股前一晚 {c['sym']} 漲幅 > {c['th']}%（只用台股決策日之前已收盤的美股）",
    "ev_avoid": lambda c: f"{ {'fomc': 'FOMC', 'nfp': '美國非農', 'settle': '台指期結算', 'tsmc': '台積電法說'}[c['t']] } 影響日前 {c['b']} 天內不進場",
    "ev_before": lambda c: f"只在 { {'fomc': 'FOMC', 'tsmc': '台積電法說', 'exdiv': '除權息旺季', 'settle': '台指期結算'}[c['t']] } 前 {c['b']} 天內進場（卡位）",
    "ev_after": lambda c: f"只在 { {'fomc': 'FOMC', 'tsmc': '台積電法說', 'exdiv': '除權息旺季', 'settle': '台指期結算'}[c['t']] } 後 {c['a']} 天內進場（事後反應）",
}
RANK_TXT = {"mom20": "20 日漲幅最大者優先", "volratio": "量比（今量／20 日均量）最大者優先", "turnover": "20 日平均成交值最大者優先"}


def describe(g):
    parts = []
    nm = {"tech": "技術面", "chip": "籌碼面", "news": "消息事件面"}
    for cat in CATS:
        if g[cat]:
            parts.append(f"【{nm[cat]}】" + "；且 ".join(COND_TXT[c["k"]](c) for c in g[cat]))
    e, r = g["exit"], g["risk"]
    ex = [f"停損：進場價 − {e['atr_k']} 倍 ATR(14)"]
    ex.append(f"停利：{e['rr']}R（風險的 {e['rr']} 倍）" if e["rr"] else "不設固定停利")
    ex.append(f"移動停損：最高價 − {e['trail']} 倍 ATR，只上移" if e["trail"] else "不用移動停損")
    ex.append(f"收盤跌破 {e['ma']} 日均線，隔日開盤出場" if e["ma"] else "不用均線出場")
    ex.append(f"最長持有 {e['maxhold']} 個交易日（到期隔日開盤出）")
    txt = ("進場：上述全部條件在 T 日收盤後同時成立 → T+1 開盤買進（開盤鎖漲停則放棄）。" + " ".join(parts)
           + f"。候選太多時：{RANK_TXT[g['rank']]}。部位：每筆最多虧本金 {r['risk']:.0%}（部位 = 本金×風險%÷停損幅度，單檔不超過本金/{r['maxpos']}），最多同時持有 {r['maxpos']} 檔。"
           + "出場：" + "；".join(ex) + "；同日停損與停利都碰到以停損計（保守）；停損跳空以開盤價成交。")
    return txt


def class_of(g):
    return gclass(g)


def to_expr(g, med_atr_pct=0.03):
    """轉成交易練習室腳本（site/lab/expr.js）。回傳 (script, 無法完整轉換的清單)。
    練習室沒有的：月營收、美股前一晚（沒這兩種資料）、SMC 擺盪結構、跨股票排序／池篩選、ATR 倍數停損（只有 % 停損，用訓練期 ATR% 中位數換算）。"""
    L, miss = [], []
    cond = []
    for cat in CATS:
        for c in g[cat]:
            k = c["k"]
            if k == "ma_trend":
                cond.append(f"收盤 > 均線(收盤,{c['n']}) 且 均線(收盤,{c['n']}) > 均線(收盤,{c['n']})[5]")
            elif k == "ma_cross":
                cond.append(f"最高價(上穿(均線(收盤,{c['f']}), 均線(收盤,{c['s']})),3) > 0")
            elif k == "macd":
                cond.append("最高價(上穿(macd_dif(收盤), macd_dea(收盤)),3) > 0 且 macd_dif(收盤) > macd_dea(收盤)" if c["mode"] == "cross"
                            else "macd_dif(收盤) > 0 且 macd_osc(收盤) > 0 且 macd_osc(收盤) > macd_osc(收盤)[1]")
            elif k == "rsi":
                cond.append(f"最高價(上穿(rsi(收盤,14), {c['th']}),3) > 0" if c["mode"] == "pull" else f"rsi(收盤,14) > {c['th']} 且 rsi(收盤,14) > rsi(收盤,14)[1]")
            elif k == "kd":
                cond.append(f"最高價(上穿(kd_k(9), kd_d(9)),2) > 0 且 kd_k(9) < {c['th'] + 20}")
            elif k == "boll":
                cond.append("收盤 > bb_up(收盤,20,2)" if c["mode"] == "break" else "最低價(收盤 - bb_low(收盤,20,2),2) < 0 且 收盤 > bb_low(收盤,20,2)")
            elif k == "donchian":
                cond.append(f"收盤 > 最高價(最高,{c['n']})[1]")
            elif k == "supertrend":
                cond.append(f"supertrend_dir({10},{c['m']}) > 0" + ("" if c["mode"] == "state" else "（近似：以多頭狀態代替『近 3 天剛翻多』）"))
            elif k == "volprice":
                cond.append(f"成交量 > {c['m']} * 均線(成交量,20)[1] 且 收盤 > 開盤 且 收盤 >= 最低 + (最高 - 最低) * 2 / 3")
            elif k == "inst_buy":
                nm = {"foreign": "外資", "trust": "投信", "all": "法人"}[c["who"]]
                cond.append(f"累計(chip(\"{nm}\"),{c['n']}) > 0（近似：練習室用買賣超絕對量，不是占成交量 {c['th']}%）")
            elif k == "inst_streak":
                nm = {"foreign": "外資", "trust": "投信", "all": "法人"}[c["who"]]
                cond.append(f"連買賣(chip(\"{nm}\")) >= {c['d']}")
            elif k == "both_buy":
                cond.append(f"累計(chip(\"外資\"),{c['n']}) > 0 且 累計(chip(\"投信\"),{c['n']}) > 0（近似）")
            elif k == "ev_avoid":
                cond.append(f"非 事件(\"{c['t']}\",{c['b']},0)（近似：練習室的事件窗以事件日為基準）")
            elif k in ("ev_before", "ev_after"):
                cond.append(f"事件(\"{c['t']}\"," + (f"{c['b']},0" if k == "ev_before" else f"0,{c['a']}") + ")")
            else:
                miss.append(COND_TXT[k](c))
    if cond:
        L.append("// 進場條件（全部成立才進場）")
        L.append("若 " + " 且 ".join(f"({x.split('（')[0]})" for x in cond) + " 則 進場(\"多\")")
        for x in cond:
            if "（" in x:
                L.append("// 註：" + x[x.index("（"):].strip("（）"))
    e = g["exit"]
    sl = round(e["atr_k"] * med_atr_pct * 100, 1)
    parts = [f"停損%={sl}"]
    if e["rr"]:
        parts.append(f"停利%={round(sl * e['rr'], 1)}")
    if e["trail"]:
        parts.append(f"移動%={round(e['trail'] * med_atr_pct * 100, 1)}")
    parts.append(f"最長持有={e['maxhold']}")
    L.append(f"出場(\"風控\", {', '.join(parts)})")
    if e["ma"]:
        L.append(f"若 收盤 < 均線(收盤,{e['ma']}) 則 平倉(\"多\")")
    L.append(f"// ATR 停損 {e['atr_k']} 倍以訓練期交易的 ATR 中位數 {med_atr_pct:.1%} 換算成固定百分比，是近似")
    if miss:
        L.append("// 練習室目前無法表達的條件（轉換時略過，結果會與本報告不同）：" + "；".join(miss))
    return "\n".join(L), miss


# ============================================================== 7. 總流程
CTX: Ctx | None = None
LEAGUES = [("主賽", 0, None)] + [(f"類別賽-{c}", 10 + i, CLASS_SET[c]) for i, c in enumerate(CLASSES)] + [(f"重複賽-{s}", s, None) for s in range(1, 6)]


def _league_job(spec):
    name, seed, lock = spec
    r = run_league(CTX, name, seed, lock)
    for p in r["final"]:
        p["gh"] = ghash(p["g"])
    return r


def warm(ctx):
    import itertools
    for cat in CATS:
        for k, grid in GRID[cat].items():
            names = list(grid)
            for vals in itertools.product(*[grid[n] for n in names]):
                c = {"k": k, **dict(zip(names, vals))}
                if k == "ma_cross" and c["f"] >= c["s"]:
                    continue
                ctx.get(c)


def yearly(eq, dates, i0):
    """分年度報酬。第一年以 10 萬為起點，其後每年以上一年底權益為起點。"""
    sr = pd.Series(eq, index=dates[i0:i0 + len(eq)])
    ye = sr.groupby(sr.index.year).last()
    prev = np.concatenate([[CASH0], ye.values[:-1]])
    return pd.Series(ye.values / prev - 1, index=ye.index)


def run_all():
    global CTX
    import multiprocessing as mp
    d = prepare()
    ctx = Ctx(d)
    CTX = ctx
    print("暖機條件快取…", flush=True)
    warm(ctx)
    print("條件數", len(ctx.cache), flush=True)
    with mp.get_context("fork").Pool(4) as pool:
        res = pool.map(_league_job, LEAGUES)
    pickle.dump(res, open(f"{CACHE}/leagues.pkl", "wb"))
    return ctx, res


def _full_job(g):
    out = run_genome(CTX, g, I0, I1)
    return metrics(out), out[0]


def _hold_job(g):
    out = run_genome(CTX, g, H0, H1)
    return metrics(out), out[0]


def _rand_job(args):
    g = args
    o1 = run_genome(CTX, g, I0, I1)
    o2 = run_genome(CTX, g, H0, H1)
    return metrics(o1), metrics(o2), g


def _sharpe_job(g):
    out = run_genome(CTX, g, I0, I1)
    e = np.concatenate([[CASH0], out[0]])
    r = np.diff(e) / e[:-1]
    return float(r.mean() / r.std()) if r.std() > 0 else 0.0


I0 = I1 = H0 = H1 = 0


def finalize(n_random=3600, seed=777):
    """凍結 -> 保留期只跑一次 -> 隨機對照 -> deflated Sharpe -> 全部輸出到 final.pkl"""
    global CTX, I0, I1, H0, H1
    import multiprocessing as mp
    d = prepare()
    ctx = Ctx(d)
    CTX = ctx
    warm(ctx)
    res = pickle.load(open(f"{CACHE}/leagues.pkl", "rb"))
    dates = ctx.dates
    I0 = int(dates.searchsorted(pd.Timestamp(TRAIN_START)))
    I1 = int(dates.searchsorted(pd.Timestamp(TRAIN_END), side="right")) - 1
    H0 = int(dates.searchsorted(pd.Timestamp(HOLD_START)))
    H1 = len(dates) - 1
    pool = mp.get_context("fork").Pool(4)
    # ---- 1. 訓練期完整回測（這一步仍是訓練期，可看）
    people = []
    for r in res:
        for p in r["final"]:
            people.append({"league": r["name"], "id": p["id"], "g": p["g"], "gh": ghash(p["g"]), "wins": p["wins"], "how": p["how"], "born": p["born"]})
    uniq = {}
    for p in people:
        uniq.setdefault(p["gh"], p["g"])
    keys = list(uniq)
    tr = dict(zip(keys, pool.map(_full_job, [uniq[k] for k in keys], chunksize=4)))
    for p in people:
        p["train"], p["train_eq"] = tr[p["gh"]]
        p["cls"] = gclass(p["g"])
    # ---- 2. 凍結：名單與基因先寫檔，再碰保留期
    os.makedirs(OUT, exist_ok=True)
    frozen = [{"league": p["league"], "id": p["id"], "genome": p["g"], "train": p["train"]} for p in people]
    json.dump({"frozen_at_note": "保留期（2021-01-01 以後）在這份名單寫出之後才執行，只執行一次", "n": len(frozen), "people": frozen},
              open(f"{OUT}/frozen_before_holdout.json", "w"), ensure_ascii=False, indent=1)
    # ---- 3. 保留期（一次）
    ho = dict(zip(keys, pool.map(_hold_job, [uniq[k] for k in keys], chunksize=4)))
    for p in people:
        p["hold"], p["hold_eq"] = ho[p["gh"]]
    # ---- 4. 隨機對照組：同樣的基因空間、同樣的開局比例，不演化，直接隨機抽
    rng = random.Random(seed)
    rg = []
    per = {c: round(n_random * n / 100) for c, n in START_MIX.items()}
    for c, n in per.items():
        rg += [rand_genome(CLASS_SET[c], rng) for _ in range(n)]
    rr = pool.map(_rand_job, rg, chunksize=8)
    rand = [{"train": a, "hold": b, "g": g, "cls": gclass(g)} for a, b, g in rr]
    # ---- 5. 評估過的策略數與試驗 Sharpe 變異數
    allg = {}
    for r in res:
        allg.update(r["genomes"])
    n_trials = len(allg)
    ks = list(allg)
    random.Random(1).shuffle(ks)
    sh = pool.map(_sharpe_job, [allg[k] for k in ks[:1500]], chunksize=8)
    var_sh = float(np.var(sh))
    pool.close()
    final = {"people": people, "rand": rand, "n_trials": n_trials, "var_sh": var_sh, "res_meta": [(r["name"], r["seed"], r["evals"], len(r["genomes"])) for r in res],
             "I0": I0, "I1": I1, "H0": H0, "H1": H1, "dates_end": str(dates[-1].date())}
    pickle.dump(final, open(f"{CACHE}/final.pkl", "wb"))
    return final


# ============================================================== 8. 報告輸出
KIND_ZH = {
    "ma_trend": "均線趨勢向上", "ma_cross": "均線黃金交叉", "macd": "MACD", "rsi": "RSI", "kd": "KD", "boll": "布林通道", "donchian": "唐奇安突破",
    "supertrend": "Supertrend", "volprice": "量價齊揚", "weekly": "週K方向", "smc": "SMC結構突破", "idx_trend": "大盤濾網",
    "inst_buy": "法人買超(占成交量)", "inst_streak": "法人連買", "both_buy": "外資+投信同買",
    "rev_yoy": "營收年增率", "rev_accel": "營收加速", "rev_fresh": "營收公布後短窗", "us_night": "美股前一晚",
    "ev_avoid": "事件前避開", "ev_before": "事件前卡位", "ev_after": "事件後進場",
}


def zh(text):
    import re
    for k, v in sorted(KIND_ZH.items(), key=lambda kv: -len(kv[0])):
        text = re.sub(rf"(?<![A-Za-z_]){k}(?![A-Za-z_])", v, text)
    return text


def P(x, d=1):
    return f"{x * 100:.{d}f}%"


def _mrow(m):
    return f"{P(m['cagr'])} | {P(m['win'], 0)} | {m['payoff']:.2f} | {P(m['dd'], 0)} | {m['calmar']:.2f} | {m['n']} | {m['hold']:.0f}"


def render():
    global CTX, I0, I1, H0, H1
    d = prepare()
    ctx = Ctx(d)
    CTX = ctx
    F = pickle.load(open(f"{CACHE}/final.pkl", "rb"))
    res = pickle.load(open(f"{CACHE}/leagues.pkl", "rb"))
    I0, I1, H0, H1 = F["I0"], F["I1"], F["H0"], F["H1"]
    people, rand = F["people"], F["rand"]
    os.makedirs(f"{OUT}/trades", exist_ok=True)
    main = [p for p in people if p["league"] == "主賽"]
    elig = [p for p in main if p["train"]["n"] >= 30]
    top_ret = sorted(elig, key=lambda p: -p["train"]["cagr"])[:10]
    top_win = sorted([p for p in elig if p["train"]["ret"] > 0], key=lambda p: -p["train"]["win"])[:10]
    top_rr = sorted(elig, key=lambda p: -p["train"]["calmar"])[:10]
    lists = {"報酬": top_ret, "勝率": top_win, "風險報酬比": top_rr}
    union = {}
    for nm, L in lists.items():
        for i, p in enumerate(L):
            union.setdefault(p["gh"], p)
    ids = {gh: f"M{p['id']:03d}" for gh, p in union.items()}
    out = []
    A = out.append

    # ---------------- 面向比較表
    A("## 一、面向比較表：哪種組合最好？\n")
    A("每一類各自跑一場完整淘汰賽（同樣 100 人、同樣 18 回合、同樣的搜尋預算），只准用該類的面向；"
      "下表取該場最後倖存的 50 位。『最佳』= 訓練期報酬回撤比（Calmar）第一名（至少 30 筆交易），後面的保留期是那個人凍結後跑一次的結果。\n")
    A("| 類別 | 倖存者訓練期年化中位數 | 訓練期最佳：年化／勝率／筆數 | 同一人保留期：年化／勝率／筆數 | 倖存者保留期年化中位數 | 保留期年化為正的比例 | 隨機對照（同類）保留期年化中位數 |")
    A("|---|---|---|---|---|---|---|")
    class_rows = []
    for c in CLASSES:
        ps = [p for p in people if p["league"] == f"類別賽-{c}"]
        el = [p for p in ps if p["train"]["n"] >= 30] or ps
        best = max(el, key=lambda p: p["train"]["calmar"])
        mt = np.median([p["train"]["cagr"] for p in ps])
        mh = np.median([p["hold"]["cagr"] for p in ps])
        pos = np.mean([p["hold"]["cagr"] > 0 for p in ps])
        rc = [r["hold"]["cagr"] for r in rand if r["cls"] == c]
        class_rows.append((c, mt, best, mh, pos, float(np.median(rc))))
        A(f"| {c} | {P(mt)} | {P(best['train']['cagr'])}／{P(best['train']['win'], 0)}／{best['train']['n']} | "
          f"{P(best['hold']['cagr'])}／{P(best['hold']['win'], 0)}／{best['hold']['n']} | {P(mh)} | {P(pos, 0)} | {P(float(np.median(rc)))} |")
    A("")

    # ---------------- 榜單
    A("## 二、最終榜單（主賽，100 人淘汰賽最後 50 位倖存者中取前 10）\n")
    A("排序依據全部是訓練期（2012-2020）完整回測；保留期（2021-01 至 " + F["dates_end"] + "）是凍結之後只跑一次。"
      "進榜門檻：訓練期至少 30 筆交易。勝率榜另外要求訓練期報酬為正（否則『勝率高但賠錢』會霸榜）。\n")
    hdr = "| # | 編號 | 類別 | 訓練 年化 | 勝率 | 賺賠比 | 最大回撤 | Calmar | 筆數 | 均持有 | 保留 年化 | 勝率 | 賺賠比 | 最大回撤 | Calmar | 筆數 | 均持有 |\n|" + "---|" * 17
    for nm, L in lists.items():
        A(f"### 依「{nm}」排序前 10\n")
        A(hdr)
        for i, p in enumerate(L, 1):
            A(f"| {i} | {ids[p['gh']]} | {p['cls']} | {_mrow(p['train'])} | {_mrow(p['hold'])} |")
        A("")

    # ---------------- 隨機對照
    rr_el = [r for r in rand if r["train"]["n"] >= 30]
    rtop = sorted(rr_el, key=lambda r: -r["train"]["calmar"])[:10]
    rng = random.Random(5)
    boots1, boots10 = [], []
    for _ in range(400):
        # 抽與主賽相同的試驗數（主賽評估過的不同基因數），再套同樣的 n>=30 門檻與 Calmar 前 10
        sub = [r for r in rng.sample(rand, min(len(rand), len(res[0]["genomes"]))) if r["train"]["n"] >= 30]
        s10 = sorted(sub, key=lambda r: -r["train"]["calmar"])[:10]
        boots1.append(s10[0]["hold"]["cagr"])
        boots10.append(float(np.mean([r["hold"]["cagr"] for r in s10])))
    ev10 = float(np.mean([p["hold"]["cagr"] for p in top_rr]))
    ev1 = top_rr[0]["hold"]["cagr"]
    rand_hold_med = float(np.median([r["hold"]["cagr"] for r in rand]))
    rand_hold_pos = float(np.mean([r["hold"]["cagr"] > 0 for r in rand]))
    A("## 三、與隨機對照組比較\n")
    A(f"隨機對照組：在同一個基因空間、同樣的開局比例下直接隨機抽 {len(rand)} 組策略（不演化、不淘汰），用同樣的『訓練期 Calmar 取前 10』流程挑冠軍，再跑保留期。"
      f"比較的是『演化』有沒有比『隨機抽很多組再挑最好』多出東西 —— 這個對照把『挑最好』的選擇偏誤也算給隨機組了。\n")
    A("| 項目 | 演化主賽（Calmar 前 10） | 隨機對照（Calmar 前 10） |\n|---|---|---|")
    A(f"| 訓練期年化平均 | {P(np.mean([p['train']['cagr'] for p in top_rr]))} | {P(np.mean([r['train']['cagr'] for r in rtop]))} |")
    A(f"| 保留期年化平均 | {P(ev10)} | {P(np.mean([r['hold']['cagr'] for r in rtop]))} |")
    A(f"| 保留期年化冠軍（訓練期 Calmar 第一） | {P(ev1)} | {P(rtop[0]['hold']['cagr'])} |")
    A(f"| 隨機組全部 {len(rand)} 組：保留期年化中位數／為正比例 | — | {P(rand_hold_med)}／{P(rand_hold_pos, 0)} |")
    A(f"| 隨機重抽 400 次（每次抽與演化相同的試驗數再挑前 10）：保留期年化平均的分布 | {P(ev10)} 落在第 {np.mean(np.array(boots10) < ev10) * 100:.0f} 百分位 | 中位 {P(float(np.median(boots10)))}，5%～95% = {P(float(np.percentile(boots10, 5)))}～{P(float(np.percentile(boots10, 95)))} |")
    A("")
    # 複製賽
    A("### 重複賽（同規則、不同隨機種子）：結論穩不穩？\n")
    A("| 賽 | 種子 | 訓練期 Calmar 第一名類別 | 訓練期年化 | 保留期年化 | 保留期勝率 | 保留期筆數 |\n|---|---|---|---|---|---|---|")
    rep = []
    for nm in ["主賽"] + [f"重複賽-{s}" for s in range(1, 6)]:
        ps = [p for p in people if p["league"] == nm]
        el = [p for p in ps if p["train"]["n"] >= 30] or ps
        b = max(el, key=lambda p: p["train"]["calmar"])
        rep.append(b)
        A(f"| {nm} | {[r['seed'] for r in res if r['name'] == nm][0]} | {b['cls']} | {P(b['train']['cagr'])} | {P(b['hold']['cagr'])} | {P(b['hold']['win'], 0)} | {b['hold']['n']} |")
    A("")

    # ---------------- DSR
    A("## 四、統計顯著性（deflated Sharpe）\n")
    A(f"整個專案共評估過 **{F['n_trials']:,}** 個不同的策略基因（13 場比賽合計去重；加上隨機對照 {len(rand)} 組不計入），"
      f"這些策略的日 Sharpe 變異數（抽樣 1,500 組估計）= {F['var_sh']:.2e}。deflated Sharpe（DSR）= 在『試了這麼多組』的前提下，冠軍的 Sharpe 仍然顯著大於『純運氣最大值』的機率；"
      "DSR 低於 95% 代表不能排除是挑出來的運氣。\n")
    A("| 冠軍 | 訓練期年化 Sharpe | 運氣門檻 SR0（年化） | DSR | 保留期年化 Sharpe | 保留期單尾 p 值（Sharpe>0） |\n|---|---|---|---|---|---|")
    dsr_rows = {}
    for nm, L in lists.items():
        p = L[0]
        e = np.concatenate([[CASH0], p["train_eq"]])
        r = np.diff(e) / e[:-1]
        sr, sr0, dsr = deflated_sharpe(r, F["n_trials"], F["var_sh"])
        e2 = np.concatenate([[CASH0], p["hold_eq"]])
        r2 = np.diff(e2) / e2[:-1]
        srh = r2.mean() / r2.std() * math.sqrt(252) if r2.std() > 0 else 0
        pval = 1 - norm_cdf(r2.mean() / r2.std() * math.sqrt(len(r2))) if r2.std() > 0 else 1
        dsr_rows[nm] = (sr, sr0, dsr, srh, pval)
        A(f"| {nm}冠軍 {ids[p['gh']]} | {sr:.2f} | {sr0:.2f} | {dsr:.1%} | {srh:.2f} | {pval:.3f} |")
    A("")

    # ---------------- 回合記錄
    hist = res[0]["hist"]
    A("## 五、主賽回合記錄與族群演化\n")
    A("每回合 = 半年（2012H1 ~ 2020H2 共 18 回合），每人從 10 萬元重新開始；淘汰後 50 名，倖存者前 12 名原樣保留、其餘各有 50% 機率小幅突變，"
      "缺額由『前段班交叉＋突變』與約 20% 隨機新秀補滿。每回合每一位投資者的成績、存活或淘汰，完整在 `leaderboard_rounds.csv`。\n")
    A("| 回合 | 當回合冠軍報酬 | 全體中位數報酬 | 爆倉(<7成)人數 | 存活者類別分布 |\n|---|---|---|---|---|")
    for h in hist:
        cs = "、".join(f"{k}{v}" for k, v in sorted(h["class_surv"].items(), key=lambda kv: -kv[1]))
        A(f"| {h['round']} | {P(h['best_ret'])} | {P(h['median_ret'])} | {h['bust']} | {cs} |")
    A("")
    gc_first, gc_last = hist[0]["gene_surv"], hist[-1]["gene_surv"]
    A("**條件基因越來越多／越來越少（存活者中使用該條件的人數，第 1 回合 → 第 18 回合）**\n")
    A("| 條件 | 第1回合 | 第18回合 |\n|---|---|---|")
    for k in sorted(set(gc_first) | set(gc_last), key=lambda k: -(gc_last.get(k, 0) - gc_first.get(k, 0))):
        A(f"| {KIND_ZH.get(k, k)} | {gc_first.get(k, 0)} | {gc_last.get(k, 0)} |")
    A("")

    A("## 六、討論紀錄（每回合前段班的共同特徵與被淘汰者的共同弱點）\n")
    for rname, lines in res[0]["disc"]:
        A(f"**{rname}**\n")
        for ln in lines:
            A(f"- {zh(ln)}")
        A("")

    # ---------------- 逐人詳情 + 交易明細
    det = ["# 淘汰賽冠軍與前 10 名逐人詳情\n", "每人：完整白話規則、訓練期與保留期績效、分年度報酬、交易明細檔位置。年度報酬是該年度權益變化（訓練期與保留期各自從 10 萬元起算，年度間複利）。\n"]
    expr_rows = []
    for gh, p in union.items():
        pid = ids[gh]
        o_tr = run_genome(ctx, p["g"], I0, I1)
        o_ho = run_genome(ctx, p["g"], H0, H1)
        t1, t2 = tr_df(ctx, o_tr), tr_df(ctx, o_ho)
        t1["period"], t2["period"] = "訓練", "保留"
        pd.concat([t1, t2]).to_csv(f"{OUT}/trades/{pid}.csv", index=False, encoding="utf-8-sig")
        yt, yh = yearly(o_tr[0], ctx.dates, I0), yearly(o_ho[0], ctx.dates, H0)
        # 最慘 5 筆
        worst = pd.concat([t1, t2]).sort_values("ret").head(5)
        in_lists = [nm for nm, L in lists.items() if gh in [q["gh"] for q in L]]
        det.append(f"## {pid}（{p['cls']}；上榜：{'、'.join(in_lists)}；連續存活 {p['wins']} 回合；來源：{p['how']}）\n")
        det.append(describe(p["g"]) + "\n")
        det.append("| 期間 | 年化 | 勝率 | 賺賠比 | 最大回撤 | Calmar | 筆數 | 均持有(日) | 總報酬 |\n|---|---|---|---|---|---|---|---|---|")
        det.append(f"| 訓練 2012-2020 | {_mrow(p['train'])} | {P(p['train']['ret'], 0)} |")
        det.append(f"| 保留 2021-{F['dates_end'][:7]} | {_mrow(p['hold'])} | {P(p['hold']['ret'], 0)} |\n")
        det.append("分年度：" + "、".join(f"{y} {P(v)}" for y, v in list(yt.items()) + list(yh.items())) + "\n")
        det.append("最慘 5 筆：\n")
        for _, w in worst.iterrows():
            det.append(f"- {w.period} {w.code} {w.entry_date} 買 {w.entry_px:.2f} → {w.exit_date} 賣 {w.exit_px:.2f}（{w.reason}）報酬 {P(w.ret)}，持有 {w.hold_days} 天，期間最大不利 {P(w.mae)}")
        det.append(f"\n交易明細：`trades/{pid}.csv`\n")
        if p in [q for L in lists.values() for q in L[:1]] or True:
            atrp = float(np.median([ctx.Anp[int(ctx.dates.searchsorted(pd.Timestamp(r.entry_date))) - 1, ctx.codes.index(r.code)] /
                                    ctx.Onp[int(ctx.dates.searchsorted(pd.Timestamp(r.entry_date))), ctx.codes.index(r.code)] for r in t1.itertuples()])) if len(t1) else 0.03
            sc, miss = to_expr(p["g"], atrp)
            expr_rows.append((pid, p, sc, miss, atrp))
    open(f"{OUT}/strategies_detail.md", "w", encoding="utf-8").write("\n".join(det))

    # ---------------- 融資事後探索（保留期）
    mb = d["margin_balance"]
    ext = (mb.diff(5) < 0).fillna(False).values
    A("## 七、融資探索（事後、只在保留期、不進演化）\n")
    A("融資資料 2021 年才有，訓練期沒有，所以融資基因無法放進淘汰賽。這裡把榜上『風險報酬比前 10 名』在保留期各加一道濾網：融資餘額近 5 日減少才進場，看有沒有改善。"
      "這是事後看保留期的探索，樣本小，**只能當線索，不能當結論**。\n")
    A("| 編號 | 保留期原版 年化／勝率／筆數 | 加融資減少濾網 年化／勝率／筆數 |\n|---|---|---|")
    mg_rows = []
    for p in top_rr:
        o = run_genome(ctx, p["g"], H0, H1, extra_sig=ext)
        m = metrics(o)
        mg_rows.append((p["hold"], m))
        A(f"| {ids[p['gh']]} | {P(p['hold']['cagr'])}／{P(p['hold']['win'], 0)}／{p['hold']['n']} | {P(m['cagr'])}／{P(m['win'], 0)}／{m['n']} |")
    A(f"\n10 人平均年化：原版 {P(np.mean([a['cagr'] for a, b in mg_rows]))} → 加濾網 {P(np.mean([b['cagr'] for a, b in mg_rows]))}。\n")

    # ---------------- 附錄：練習室腳本
    A("## 附錄：冠軍轉成交易練習室腳本（site/lab/expr.js 語法）\n")
    A("轉換原則：價格與法人條件逐條翻譯；練習室沒有的資料（月營收、美股前一晚）與 SMC 擺盪結構無法翻譯，會在腳本註解標明『略過』，"
      "略過之後的結果和本報告不同。ATR 倍數停損換成固定百分比（用該策略訓練期進場時 ATR÷股價的中位數）。"
      "練習室是單一標的回測，沒有『跨股票挑最強』『同時最多 N 檔』『依風險%決定部位』，所以只能驗證單一股票上的進出場邏輯。\n")
    for pid, p, sc, miss, atrp in expr_rows:
        if any(p["gh"] == L[0]["gh"] for L in lists.values()):
            A(f"### {pid}（{p['cls']}）\n")
            A("```\n" + sc + "\n```\n")
            A("完整腳本（含所有上榜者）：`expr_scripts.txt`\n")
    with open(f"{OUT}/expr_scripts.txt", "w", encoding="utf-8") as f:
        for pid, p, sc, miss, atrp in expr_rows:
            f.write(f"===== {pid}（{p['cls']}）{'【含無法翻譯的條件】' if miss else ''} =====\n{sc}\n\n")

    # ---------------- CSV
    rows = []
    for r in res[0]["hist"]:
        for (pid_, cls, how, wins, sc, ret, dd, win, n, hold, st) in r["rows"]:
            rows.append({"回合": r["round"], "編號": f"M{pid_:03d}", "類別": cls, "來源": how, "已連續存活回合": wins, "回合分數": round(sc, 3), "報酬": round(ret, 4),
                         "最大回撤": round(dd, 4), "勝率": round(win, 3), "筆數": n, "均持有日": round(hold, 1), "結果": st})
    pd.DataFrame(rows).to_csv(f"{OUT}/leaderboard_rounds.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"回合": h["round"], **{f"存活_{k}": v for k, v in h["class_surv"].items()}, **{f"條件_{k}": v for k, v in h["gene_surv"].items()}} for h in hist]).to_csv(
        f"{OUT}/evolution_by_round.csv", index=False, encoding="utf-8-sig")
    fin = []
    for nm, L in lists.items():
        for i, p in enumerate(L, 1):
            fin.append({"榜單": nm, "名次": i, "編號": ids[p["gh"]], "類別": p["cls"],
                        **{f"訓練_{k}": round(v, 4) for k, v in p["train"].items()}, **{f"保留_{k}": round(v, 4) for k, v in p["hold"].items()}, "規則": describe(p["g"])})
    pd.DataFrame(fin).to_csv(f"{OUT}/final_lists.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"類別": c, "倖存者訓練年化中位數": mt, "最佳編號": f"{b['league']}#{b['id']}", "最佳訓練年化": b["train"]["cagr"], "最佳訓練勝率": b["train"]["win"],
                   "最佳保留年化": b["hold"]["cagr"], "最佳保留勝率": b["hold"]["win"], "倖存者保留年化中位數": mh, "保留期為正比例": pos, "隨機同類保留年化中位數": rm}
                  for c, mt, b, mh, pos, rm in class_rows]).to_csv(f"{OUT}/class_comparison.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"cls": r["cls"], **{f"train_{k}": v for k, v in r["train"].items()}, **{f"hold_{k}": v for k, v in r["hold"].items()}} for r in rand]).to_csv(
        f"{OUT}/random_control.csv", index=False, encoding="utf-8-sig")
    open(f"{OUT}/_auto_sections.md", "w", encoding="utf-8").write("\n".join(out))
    pickle.dump({"dsr": dsr_rows, "ev10": ev10, "ev1": ev1, "boots10": boots10, "boots1": boots1, "rep": [(b["league"], b["cls"], b["train"], b["hold"]) for b in rep],
                 "class_rows": [(c, mt, b["train"], b["hold"], mh, pos, rm) for c, mt, b, mh, pos, rm in class_rows]}, open(f"{CACHE}/render_summary.pkl", "wb"))
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "finalize":
        finalize()
    elif len(sys.argv) > 1 and sys.argv[1] == "render":
        render()
    else:
        run_all()


