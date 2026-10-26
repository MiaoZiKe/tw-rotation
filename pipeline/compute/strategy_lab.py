"""策略實驗室：多策略 x 多參數 x 多週期（4H／日K／週K）回測，先廣後收斂。

只讀資料湖（price_daily、intraday_60m、index_ohlc），不寫回 data/。結果寫 docs/strategy_lab/。
這是研究用的回測，不是交易系統、不下單、不構成買賣建議。

■ 無前視偏誤的做法（紅線）
  - 訊號用「一根 K 收盤後」的資訊，成交一律在「下一根 K 的開盤」。
  - 高週期濾網（週K、日K）只取「已完成」的那根：週K 以該週最後交易日為標記 ffill 到日線，
    日K 濾網給 4H 用時再往後延一天，絕不用當天尚未收完的資訊。
  - ATR 移動停損也是收盤判定、隔根開盤出場。
■ 成本：手續費 0.1425% x 買賣各一次（不打折，保守）、證交稅 0.3% 賣出、滑價 0.10%/邊。
■ 4H 口徑：由 60m K 合成。台股 09:00-13:30，TradingView 慣例切成兩根：
    第一根 = 09:00-13:00（60m 的 09,10,11,12 四根合併，真正 4 小時）
    第二根 = 13:00-13:30（只有 60m 的 13:00 那根，30 分鐘）
  訊號在第一根收盤（13:00）、成交在第二根開盤（13:00）；第二根收盤訊號、隔日 09:00 成交。
■ 價格未還原除權息（資料湖就是原始價），只還原明顯分割（單日跌/漲超過 40%，例如 0050 的 1 拆 4）。
  買進持有基準用同一套價格，所以兩邊相對比較公平，但絕對報酬低估股利約每年 2-4%。
■ 已知偏誤（報告也會寫）：股票池用「近一年成交值前 100」= 存活者偏誤，會高估多頭策略；
  漲跌停鎖死買不到／賣不掉沒有模擬。
"""
from __future__ import annotations

import glob
import itertools
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from numba import njit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline import indicators as ind  # noqa: E402

FEE = 0.001425          # 手續費（買、賣各一次）
TAX = 0.003             # 證交稅（賣）
SLIP = 0.001            # 滑價（每邊，價格方向不利）
OUT = ROOT / "docs" / "strategy_lab"

# 樣本內／外切分（日、週：2011-2018 定參數、2019 起驗；4H 資料只有 2023-09 起）
SPLIT = {"D": "2019-01-01", "W": "2019-01-01", "4H": "2025-04-01"}
START = {"D": "2011-01-01", "W": "2011-01-01", "4H": "2023-09-19"}


# ------------------------------------------------------------------ 資料
def _read(table, cols):
    fs = glob.glob(str(ROOT / "data" / table / "*" / "*.parquet"))
    return pd.concat([pd.read_parquet(f, columns=cols) for f in fs], ignore_index=True)


def _fix_splits(df: pd.DataFrame) -> pd.DataFrame:
    """單日價格比超過 [0.6, 1.67] 視為分割／減資，往回調整價格（台股漲跌幅 10%，正常不會出現）。"""
    c = df["close"].to_numpy(float)
    r = c[1:] / c[:-1]
    idx = np.where((r < 0.6) | (r > 1.67))[0]
    if len(idx) == 0:
        return df
    df = df.copy()
    for i in idx[::-1]:
        f = c[i + 1] / c[i]
        df.iloc[: i + 1, df.columns.get_indexer(["open", "high", "low", "close"])] *= f
    return df


LIQ_WINDOW = {"D": ("2018-01-01", "2018-12-31"), "W": ("2018-01-01", "2018-12-31"),
              "4H": ("2023-10-01", "2025-03-31")}


def load_universe(top_n=100, mode="pit"):
    p = _read("price_daily", ["date", "code", "open", "high", "low", "close", "volume", "turnover"])
    p = p[p["code"].str.fullmatch(r"\d{4}")]
    p = p[p["close"] > 0].sort_values(["code", "date"])
    last = p["date"].max()

    def top(a, b):
        w = p[(p["date"] >= a) & (p["date"] <= b)]
        liq = w.groupby("code")["turnover"].median().sort_values(ascending=False)
        return [c for c in liq.index if not c.startswith("00")][:top_n]   # 排除 00 開頭 ETF
    if mode == "pit":   # 只用「樣本內期間」的流動性選股，避免用未來的贏家（降低存活者偏誤）
        uni = {tf: top(*LIQ_WINDOW[tf]) for tf in LIQ_WINDOW}
    else:               # 現況：近一年成交值前 N（存活者偏誤明顯，僅作對照）
        cur = top((pd.Timestamp(last) - pd.Timedelta(days=365)).strftime("%Y-%m-%d"), last)
        uni = {tf: cur for tf in LIQ_WINDOW}
    codes = sorted(set(itertools.chain(*uni.values())))
    daily = {}
    for code, g in p[p["code"].isin(codes + ["0050"])].groupby("code"):
        g = g.set_index(pd.to_datetime(g["date"]))[["open", "high", "low", "close", "volume"]]
        g = g[~g.index.duplicated()]
        daily[code] = _fix_splits(g)
    return codes, daily, uni


def load_60m(codes):
    m = _read("intraday_60m", ["ts", "code", "open", "high", "low", "close", "volume"])
    m = m[m["code"].isin(codes)]
    m["ts"] = pd.to_datetime(m["ts"].str[:19])
    out = {}
    for code, g in m.groupby("code"):
        g = g.drop_duplicates("ts").sort_values("ts")
        d = g["ts"].dt.normalize()
        # 09,10,11,12 時 -> 第一根（標記 09:00）；13 時 -> 第二根（標記 13:00）
        slot = np.where(g["ts"].dt.hour <= 12, 0, 1)
        key = d + pd.to_timedelta(np.where(slot == 0, 9, 13), unit="h")
        agg = g.groupby(key.values).agg(open=("open", "first"), high=("high", "max"),
                                        low=("low", "min"), close=("close", "last"),
                                        volume=("volume", "sum"))
        out[code] = _fix_splits(agg)
    return out


_WEEK_LABEL: dict = {}   # 週 -> 全市場該週最後交易日（所有個股共用同一組週K 時間軸，避免各股標記不同）


def set_calendar(dates: pd.DatetimeIndex):
    s = pd.Series(dates, index=dates)
    _WEEK_LABEL.clear()
    _WEEK_LABEL.update(s.groupby(dates.to_period("W-FRI")).max().to_dict())


def to_weekly(d: pd.DataFrame) -> pd.DataFrame:
    wk = d.index.to_period("W-FRI")
    g = d.groupby(wk)
    w = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(),
                      "close": g["close"].last(), "volume": g["volume"].sum()})
    w.index = [_WEEK_LABEL.get(k, d.index[wk == k][-1]) for k in w.index]   # 以全市場該週最後交易日標記（收完才知道）
    return w


# ------------------------------------------------------------------ 回測引擎
@njit(cache=True)
def _run(o, h, l, c, entry, exitsig, atr, stop_mult, fb, fs, slip):
    """單檔、只做多、全倉。回傳每根 K 的報酬與交易清單 (進場idx, 出場idx, 報酬, 最大不利偏移)。"""
    n = len(c)
    ret = np.zeros(n)
    tr = np.full((n // 2 + 2, 4), np.nan)
    nt = 0
    pos = False
    pend_in = False
    pend_out = False
    epx = 0.0
    eidx = 0
    trail = -1e18
    mae = 0.0
    for i in range(1, n):
        if np.isnan(o[i]) or np.isnan(c[i]):
            continue
        if pend_in and not pos:
            epx = o[i] * (1 + slip)
            ret[i] = c[i] / epx - 1 - fb
            pos = True
            eidx = i
            trail = -1e18
            mae = min(0.0, l[i] / epx - 1)
        elif pos and pend_out:
            xpx = o[i] * (1 - slip)
            ret[i] = xpx / c[i - 1] - 1 - fs
            pos = False
            if nt < tr.shape[0]:
                tr[nt, 0] = eidx
                tr[nt, 1] = i
                tr[nt, 2] = xpx * (1 - fs) / (epx * (1 + fb)) - 1
                tr[nt, 3] = mae
                nt += 1
        elif pos:
            ret[i] = c[i] / c[i - 1] - 1
            mae = min(mae, l[i] / epx - 1)
        pend_in = False
        pend_out = False
        # 收盤後產生訊號 -> 下一根開盤成交
        if pos:
            if stop_mult > 0 and not np.isnan(atr[i]):
                trail = max(trail, c[i] - stop_mult * atr[i])
                if c[i] < trail:
                    pend_out = True
            if exitsig[i]:
                pend_out = True
        else:
            if entry[i]:
                pend_in = True
    return ret, tr[:nt]


# ------------------------------------------------------------------ 指標與策略
class Ctx:
    """單檔單週期的 K 線與指標快取；filt 為高週期濾網（已對齊、只含已完成資訊）。"""

    def __init__(self, df: pd.DataFrame, tf: str, higher: dict | None = None):
        self.df, self.tf = df, tf
        self.o, self.h, self.l, self.c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
        self.v = df["volume"].to_numpy(float)
        self.higher = higher or {}
        self._cache = {}

    def get(self, key, fn):
        if key not in self._cache:
            self._cache[key] = fn()
        return self._cache[key]

    s = property(lambda self: pd.Series(self.c, index=self.df.index))

    def sma(self, n):
        return self.get(("sma", n), lambda: pd.Series(self.c).rolling(n).mean().to_numpy())

    def ema(self, n):
        return self.get(("ema", n), lambda: ind.ema(pd.Series(self.c), n).to_numpy())

    def macd(self, f, s, g):
        return self.get(("macd", f, s, g), lambda: ind.macd(pd.Series(self.c), f, s, g))

    def rsi(self, n):
        return self.get(("rsi", n), lambda: ind.rsi(pd.Series(self.c), n).to_numpy())

    def kd(self):
        return self.get("kd", lambda: ind.kd(pd.Series(self.h), pd.Series(self.l), pd.Series(self.c)))

    def atr(self, n=14):
        return self.get(("atr", n), lambda: ind.atr(pd.Series(self.h), pd.Series(self.l),
                                                    pd.Series(self.c), n).to_numpy())

    def hh(self, n):  # 前 n 根最高（不含當根，突破才有意義）
        return self.get(("hh", n), lambda: pd.Series(self.h).rolling(n).max().shift(1).to_numpy())

    def ll(self, n):
        return self.get(("ll", n), lambda: pd.Series(self.l).rolling(n).min().shift(1).to_numpy())

    def boll(self, n, k):
        def f():
            s = pd.Series(self.c)
            m = s.rolling(n).mean()
            sd = s.rolling(n).std(ddof=0)
            return m.to_numpy(), (m + k * sd).to_numpy(), (m - k * sd).to_numpy()
        return self.get(("boll", n, k), f)

    def supertrend(self, n, mult):
        def f():
            a = self.atr(n)
            hl2 = (self.h + self.l) / 2
            return _supertrend(self.h, self.l, self.c, a, hl2, mult)
        return self.get(("st", n, mult), f)


@njit(cache=True)
def _supertrend(h, l, c, a, hl2, mult):
    n = len(c)
    up = np.full(n, np.nan)
    lo = np.full(n, np.nan)
    trend = np.zeros(n)  # 1 多 -1 空
    d = 1.0
    for i in range(n):
        if np.isnan(a[i]):
            continue
        bu = hl2[i] + mult * a[i]
        bl = hl2[i] - mult * a[i]
        if i == 0 or np.isnan(up[i - 1]):
            up[i], lo[i] = bu, bl
        else:
            up[i] = bu if (bu < up[i - 1] or c[i - 1] > up[i - 1]) else up[i - 1]
            lo[i] = bl if (bl > lo[i - 1] or c[i - 1] < lo[i - 1]) else lo[i - 1]
            if d == 1.0 and c[i] < lo[i]:
                d = -1.0
            elif d == -1.0 and c[i] > up[i]:
                d = 1.0
        trend[i] = d
    return trend


def _cross_up(a, b):
    with np.errstate(invalid="ignore"):
        return (a > b) & (np.roll(a, 1) <= np.roll(b, 1))


def _cross_dn(a, b):
    with np.errstate(invalid="ignore"):
        return (a < b) & (np.roll(a, 1) >= np.roll(b, 1))


def sig(fam: str, p: dict, x: Ctx):
    """回傳 (entry, exit) 布林陣列，皆為「該根收盤後可知」。"""
    c = x.c
    n = len(c)
    F = np.zeros(n, bool)
    if fam == "ma_cross":
        f, s = x.sma(p["f"]), x.sma(p["s"])
        return _cross_up(f, s), _cross_dn(f, s)
    if fam == "macd":
        m = x.macd(p["f"], p["s"], p["g"])
        dif, mac = m["dif"].to_numpy(), m["macd"].to_numpy()
        en = _cross_up(dif, mac)
        if p.get("zero"):
            en &= dif > 0
        return en, _cross_dn(dif, mac)
    if fam == "rsi_rev":
        r = x.rsi(p["n"])
        en = r < p["lo"]
        if p.get("trend"):
            en &= c > x.sma(p["trend"])
        return en, r > p["hi"]
    if fam == "kd":
        k = x.kd()
        K, D = k["k"].to_numpy(), k["d"].to_numpy()
        en = _cross_up(K, D) & (K < p["lo"])
        ex = (K > p["hi"]) | _cross_dn(K, D) if p.get("dead") else (K > p["hi"])
        return en, ex
    if fam == "boll_break":
        m, u, lo = x.boll(p["n"], p["k"])
        return (c > u), (c < m)
    if fam == "boll_revert":
        m, u, lo = x.boll(p["n"], p["k"])
        en = c < lo
        if p.get("trend"):
            en &= c > x.sma(p["trend"])
        return en, (c > m)
    if fam == "donchian":
        return c > x.hh(p["n_in"]), c < x.ll(p["n_out"])
    if fam == "supertrend":
        t = x.supertrend(p["n"], p["m"])
        prev = np.roll(t, 1)
        return (t == 1) & (prev == -1), (t == -1)
    if fam == "vol_break":
        vma = pd.Series(x.v).rolling(20).mean().shift(1).to_numpy()
        with np.errstate(invalid="ignore"):
            en = (c > x.hh(p["n"])) & (x.v > p["vm"] * vma)
        return en, c < x.sma(p["exit_ma"])
    raise ValueError(fam)


@dataclass
class Spec:
    fam: str
    p: dict
    tf: str
    filt: str = ""        # "" / "W"（週趨勢）/ "D"（日趨勢）/ "DW"
    stop: float = 0.0     # ATR 移動停損倍數
    name: str = field(default="")

    def __post_init__(self):
        ps = ",".join(f"{k}={v}" for k, v in self.p.items())
        self.name = f"{self.fam}({ps})" + (f"+濾網{self.filt}" if self.filt else "") + \
                    (f"+ATR停損{self.stop:g}" if self.stop else "") + f"@{self.tf}"


def build_grid():
    base = []
    for f, s in [(5, 20), (10, 30), (20, 60), (10, 50)]:
        base.append(("ma_cross", dict(f=f, s=s), 0))
    base.append(("ma_cross", dict(f=10, s=30), 3.0))
    for (f, s, g) in [(12, 26, 9), (6, 13, 5)]:
        for z in (0, 1):
            base.append(("macd", dict(f=f, s=s, g=g, zero=z), 0))
    base += [("rsi_rev", dict(n=2, lo=10, hi=65, trend=100), 0),
             ("rsi_rev", dict(n=2, lo=5, hi=65, trend=100), 0),
             ("rsi_rev", dict(n=14, lo=30, hi=55, trend=0), 0),
             ("rsi_rev", dict(n=14, lo=30, hi=55, trend=100), 0),
             ("rsi_rev", dict(n=14, lo=40, hi=60, trend=100), 0)]
    base += [("kd", dict(lo=30, hi=80, dead=0), 0), ("kd", dict(lo=30, hi=80, dead=1), 0),
             ("kd", dict(lo=50, hi=80, dead=1), 0), ("kd", dict(lo=20, hi=70, dead=1), 0)]
    base += [("boll_break", dict(n=20, k=2.0), 0), ("boll_break", dict(n=20, k=2.5), 0),
             ("boll_break", dict(n=50, k=2.0), 0),
             ("boll_revert", dict(n=20, k=2.0, trend=0), 0), ("boll_revert", dict(n=20, k=2.0, trend=100), 0),
             ("boll_revert", dict(n=20, k=2.5, trend=100), 0)]
    base += [("donchian", dict(n_in=10, n_out=5), 0), ("donchian", dict(n_in=20, n_out=10), 0),
             ("donchian", dict(n_in=40, n_out=20), 0), ("donchian", dict(n_in=55, n_out=20), 0),
             ("donchian", dict(n_in=20, n_out=10), 3.0)]
    base += [("supertrend", dict(n=10, m=3.0), 0), ("supertrend", dict(n=10, m=2.0), 0),
             ("supertrend", dict(n=14, m=3.0), 0), ("supertrend", dict(n=7, m=3.0), 0),
             ("supertrend", dict(n=20, m=4.0), 0)]
    base += [("vol_break", dict(n=20, vm=1.5, exit_ma=10), 0), ("vol_break", dict(n=20, vm=2.0, exit_ma=10), 0),
             ("vol_break", dict(n=20, vm=1.5, exit_ma=10), 3.0)]
    specs = []
    for tf in ("D", "W", "4H"):
        for fam, p, st in base:
            specs.append(Spec(fam, p, tf, "", st))
    # 跨週期濾網：週K 趨勢 -> 日K 進場；日K（＋週K）趨勢 -> 4H 進場
    mtf_fams = [("donchian", dict(n_in=20, n_out=10), 0), ("ma_cross", dict(f=10, s=30), 0),
                ("macd", dict(f=12, s=26, g=9, zero=0), 0), ("rsi_rev", dict(n=14, lo=30, hi=55, trend=0), 0),
                ("rsi_rev", dict(n=2, lo=10, hi=65, trend=100), 0), ("kd", dict(lo=30, hi=80, dead=1), 0),
                ("boll_break", dict(n=20, k=2.0), 0), ("supertrend", dict(n=10, m=3.0), 0),
                ("vol_break", dict(n=20, vm=1.5, exit_ma=10), 0)]
    for fam, p, st in mtf_fams:
        specs.append(Spec(fam, p, "D", "W", st))
        specs.append(Spec(fam, p, "4H", "D", st))
        specs.append(Spec(fam, p, "4H", "DW", st))
    return specs


# ------------------------------------------------------------------ 高週期濾網
def trend_series_weekly(daily: pd.DataFrame) -> pd.Series:
    """週K 趨勢：週收盤 EMA10 > EMA30 且週收盤 > EMA10。標記為該週最後交易日（收完才知道）。"""
    w = to_weekly(daily)
    c = w["close"]
    e10, e30 = ind.ema(c, 10), ind.ema(c, 30)
    return ((e10 > e30) & (c > e10)).astype(float).where(e30.notna())


def trend_series_daily(daily: pd.DataFrame) -> pd.Series:
    c = daily["close"]
    return (c > c.rolling(20).mean()).astype(float).where(c.rolling(20).mean().notna())


def align(series: pd.Series, index: pd.DatetimeIndex, lag_days: int = 0) -> np.ndarray:
    """把高週期序列對到低週期：只取標記時間 <= 該根時間（再扣 lag 天）的最後一個值。"""
    s = series.dropna()
    tgt = index - pd.Timedelta(days=lag_days) if lag_days else index
    # 4H 的 bar 標記為 09:00/13:00，日K 標記為 00:00，須 < 當天才算「前一日已完成」
    pos = s.index.searchsorted(tgt, side="right") - 1
    out = np.where(pos >= 0, s.to_numpy()[np.clip(pos, 0, None)], np.nan)
    return out


# ------------------------------------------------------------------ 組合統計
def ppy_of(idx):
    yrs = (idx[-1] - idx[0]).days / 365.25
    return len(idx) / max(yrs, 1e-9)


def stats(r: pd.Series, ppy: float):
    r = r.dropna()
    if len(r) < 20:
        return dict(cagr=np.nan, mdd=np.nan, sharpe=np.nan)
    eq = (1 + r).cumprod()
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    cagr = eq.iloc[-1] ** (1 / max(yrs, 1e-9)) - 1
    mdd = (eq / eq.cummax() - 1).min()
    sh = r.mean() / r.std() * np.sqrt(ppy) if r.std() > 0 else np.nan
    return dict(cagr=cagr, mdd=mdd, sharpe=sh)


def run_spec(spec: Spec, ctxs: dict, daily_all: dict, weekly_tr: dict, daily_tr: dict, start: str):
    rets, trades = {}, []
    for code, x in ctxs.items():
        entry, exitsig = sig(spec.fam, spec.p, x)
        if spec.filt:
            idx = x.df.index
            ok = np.ones(len(idx), bool)
            if "W" in spec.filt:
                wt = weekly_tr[code]
                ok &= align(wt, idx, 0 if spec.tf == "D" else 1) == 1
            if spec.filt in ("D", "DW") and spec.tf == "4H":
                ok &= align(daily_tr[code], idx.normalize() - pd.Timedelta(days=0), 1) == 1
                # 上一行：idx.normalize() 為當日 00:00，lag 1 天後只取「前一日(含)以前」已完成的日K
            entry = entry & ok
        a = x.atr(14)
        r, tr = _run(x.o, x.h, x.l, x.c, entry, exitsig, a, spec.stop, FEE, TAX + FEE, SLIP)
        rets[code] = pd.Series(r, index=x.df.index)
        for e, xx, rr, mae in tr:
            trades.append((code, x.df.index[int(e)], x.df.index[int(xx)], rr, mae))
    R = pd.DataFrame(rets).loc[start:]
    avail = pd.DataFrame({k: pd.Series(1.0, index=v.df.index) for k, v in ctxs.items()}).loc[start:]
    port = R.sum(axis=1) / avail.sum(axis=1).clip(lower=1)    # 資本平分給「已上市」的標的，空手那份報酬為 0
    expo = float((R != 0).sum().sum() / max(avail.sum().sum(), 1))   # 平均持倉比例
    return port, pd.DataFrame(trades, columns=["code", "entry", "exit", "ret", "mae"]), expo


def summarize(spec, port, trades, bh_port, split, expo=np.nan):
    ppy = ppy_of(port.index)
    cut = pd.Timestamp(split)
    out = dict(name=spec.name, fam=spec.fam, tf=spec.tf, filt=spec.filt, stop=spec.stop,
               params=json.dumps(spec.p), exposure=expo)
    for tag, seg, bseg, tseg in [("all", port, bh_port, trades),
                                 ("is", port[port.index < cut], bh_port[bh_port.index < cut],
                                  trades[trades["entry"] < cut]),
                                 ("oos", port[port.index >= cut], bh_port[bh_port.index >= cut],
                                  trades[trades["entry"] >= cut])]:
        s = stats(seg, ppy)
        b = stats(bseg, ppy)
        out.update({f"{tag}_{k}": v for k, v in s.items()})
        out[f"{tag}_bh_cagr"] = b["cagr"]
        out[f"{tag}_bh_sharpe"] = b["sharpe"]
        out[f"{tag}_bh_mdd"] = b["mdd"]
        out[f"{tag}_n"] = len(tseg)
        out[f"{tag}_win"] = (tseg["ret"] > 0).mean() if len(tseg) else np.nan
        w = tseg.loc[tseg["ret"] > 0, "ret"].mean() if len(tseg) else np.nan
        ls = -tseg.loc[tseg["ret"] <= 0, "ret"].mean() if len(tseg) else np.nan
        out[f"{tag}_payoff"] = w / ls if ls and ls > 0 else np.nan
        out[f"{tag}_avg_ret"] = tseg["ret"].mean() if len(tseg) else np.nan
    # 平均持有（以根數計；用日曆天近似）
    out["hold_days"] = (trades["exit"] - trades["entry"]).dt.total_seconds().mean() / 86400 if len(trades) else np.nan
    return out


def main(top_n=100, mode="pit"):
    OUT.mkdir(parents=True, exist_ok=True)
    codes, daily, uni = load_universe(top_n, mode)
    m60 = load_60m(codes)
    set_calendar(pd.DatetimeIndex(sorted(set().union(*[set(d.index) for d in daily.values()]))))
    wk = {c: to_weekly(d) for c, d in daily.items()}
    weekly_tr = {c: trend_series_weekly(daily[c]) for c in codes}
    daily_tr = {c: trend_series_daily(daily[c]) for c in codes}
    data = {"D": {c: daily[c] for c in uni["D"]}, "W": {c: wk[c] for c in uni["W"]},
            "4H": {c: m60[c] for c in uni["4H"] if c in m60 and len(m60[c]) > 300}}
    bh = {}
    for tf, st in START.items():
        R = pd.DataFrame({c: d["close"].pct_change() for c, d in data[tf].items()}).loc[st:]
        bh[tf] = R.mean(axis=1)
    bh0050 = daily["0050"]["close"].pct_change().loc["2011-01-01":]
    ctx = {tf: {c: Ctx(d, tf) for c, d in data[tf].items()} for tf in data}
    specs = build_grid()
    rows, allret, alltr = [], {}, {}
    for i, sp in enumerate(specs):
        port, tr, expo = run_spec(sp, ctx[sp.tf], daily, weekly_tr, daily_tr, START[sp.tf])
        rows.append(summarize(sp, port, tr, bh[sp.tf].loc[port.index[0]:], SPLIT[sp.tf], expo))
        allret[sp.name] = port
        alltr[sp.name] = tr
        if i % 40 == 0:
            print(i, len(specs), sp.name, flush=True)
    res = pd.DataFrame(rows)
    res.to_csv(OUT / f"all_results_{mode}.csv", index=False)
    pd.to_pickle({"ret": allret, "trades": alltr, "bh": bh, "bh0050": bh0050, "uni": uni,
                  "n_stocks": {tf: len(v) for tf, v in data.items()}}, OUT / f"_cache_{mode}.pkl")
    print("done", len(res), {tf: len(v) for tf, v in data.items()})
    return res


if __name__ == "__main__":
    main(100, sys.argv[1] if len(sys.argv) > 1 else "pit")
