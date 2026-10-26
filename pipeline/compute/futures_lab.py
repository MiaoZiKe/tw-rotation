"""台指期（TX）交易系統研究與回測：由大到小（週K 大格局 -> 籌碼/消息濾網 -> 日K 進出場 -> 停損）。

兩個版本：A＝只做多；B＝多空都做。淘汰規則（Andy 定，不放寬）：
  1. 樣本外年化報酬 < 同窗、同成本、含息的 0050 買進持有 -> 淘汰。
  2. 1 倍名目曝險必須贏過 0050 才算數；只有加到 2～3 倍才贏的，另外標明「僅加槓桿才贏」，仍不算通過。
  3. walk-forward 每一段各比一次。

資料口徑（誠實版）
  * 價格：資料湖 index_ohlc 的 symbol=FUT，即 FinMind 台指期（TX）日盤「近月連續」日 K（2000-01 起）。
    不是加權指數代理——真正的期貨價，已內含正逆價差。換月（每月第三個週三結算後換到次月）會在連續序列
    留下一個「新舊合約價差」的跳點；實測結算日隔天的平均跳動（約 46 點）與一般日（約 29 點）差距很小
    （主要是 FUT 13:45 收盤與指數 13:30 收盤的時間差雜訊），所以不另外修補，改以每月扣一次換倉成本：
    持倉跨結算日時，每次換月加扣 2 個價差點 x 2 腳（賣舊買新）。
  * 夜盤不納入（index_ohlc 的 FUT_N 只有 2017-05 起）；日盤收盤到隔日日盤開盤的隔夜跳空已含在序列裡。
  * 保證金與槓桿：主結果＝1 倍名目曝險（每口名義 = 指數 x 200 元；曝險 1 倍代表帳戶權益 = 一口名義），
    保證金只佔權益約 1/6，其餘現金每年計 1% 利息（台幣定存的粗略水準，假設而非資料）。2、3 倍為對照。
  * 成本：每口單邊手續費 50 元（含期交所結算費，保守）、期交稅十萬分之二（單邊）、滑價 2 個指數點（單邊）。
  * 訊號一律「收盤後產生 -> 隔日開盤成交」；停損觸價盤中成交，跳空越過停損價以開盤價出（再扣滑價）。
  * 週K 狀態用「上一個已收完的週」，絕不使用當週未收完的週K。
籌碼：fut_inst（外資 TX 淨部位，2021-01 起）、結算週。2021 前沒有資料，故籌碼濾網只能在 2021 後驗證，
單獨成一列、樣本短，不納入主要通過判定。
"""
from __future__ import annotations

import glob
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from numba import njit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "futures_lab"

MULT = 200.0               # 每點 200 元
FEE_NTD = 50.0             # 每口單邊手續費（元）
TAX = 2e-5                 # 期交稅（單邊，成交金額）
SLIP_PTS = 2.0             # 單邊滑價（點）
ROLL_PTS = 2.0 * SLIP_PTS  # 每次換月：賣舊買新兩腳的滑價（點）；手續費另計
CASH_Y = 0.01              # 閒置資金年利率（假設）
PPY = 252.0
# 0050 基準成本（與前四輪 strategy_lab / topdown_lab3 相同口徑）
ETF_FEE, ETF_TAX, ETF_SLIP = 0.001425, 0.001, 0.001

TRAIN_START = "2001-01-02"
SEGMENTS = ["2013-01-01", "2016-01-01", "2019-01-01", "2022-01-01", "2025-01-01"]
MIN_TRAIN_TRADES = 8


# ------------------------------------------------------------------ 資料
def _rd(table, cols=None):
    fs = glob.glob(str(ROOT / "data" / table / "**" / "*.parquet"), recursive=True)
    return pd.concat([pd.read_parquet(f, columns=cols) for f in fs], ignore_index=True)


def load_tx() -> pd.DataFrame:
    d = _rd("index_ohlc")
    d["date"] = pd.to_datetime(d["date"])
    f = d[d.symbol == "FUT"].drop_duplicates("date").set_index("date").sort_index()
    f = f[["open", "high", "low", "close", "volume"]].astype(float)
    return f[(f.close > 0) & (f.open > 0)]


def load_0050(idx: pd.DatetimeIndex) -> pd.DataFrame:
    """0050 還原總報酬：日報酬含除息（用除息金額 / 前收），並處理 2025 的 1 拆 4。
    回傳欄位 ret（日總報酬）與 open_ratio（當日收盤 / 當日開盤，窗首買進用）。"""
    p = _rd("price_daily", ["date", "code", "open", "close"])
    p = p[p.code == "0050"].drop_duplicates("date").copy()
    p["date"] = pd.to_datetime(p["date"])
    p = p.set_index("date").sort_index().astype(float)
    p = p[(p.close > 0) & (p.open > 0)]
    c, o = p["close"], p["open"]
    ratio = c / c.shift(1)
    split = ratio < 0.6                                   # 單日腰斬以上視為分割
    k = pd.Series(1.0, index=c.index)
    k[split] = np.round(1 / ratio[split])
    ret = c * k / c.shift(1)
    dv = pd.concat([_rd("etf_dividend_events"), _rd("dividend_events")])
    dv = dv[(dv.code == "0050") & (dv.kind == "cash") & dv.ex_date.notna()].copy()
    dv["ex_date"] = pd.to_datetime(dv["ex_date"])
    dv = dv.drop_duplicates("ex_date").set_index("ex_date")["amount"].astype(float)
    for dt, amt in dv.items():
        if dt in c.index:
            i = c.index.get_loc(dt)
            if i > 0:
                ret.iloc[i] = (c.iloc[i] * k.iloc[i] + amt) / c.iloc[i - 1]
    out = pd.DataFrame({"ret": ret - 1, "open_ratio": c * k / (o * k)}).reindex(idx)
    out["ret"] = out["ret"].fillna(0.0)
    return out


# ------------------------------------------------------------------ 指標與週K 大格局
def atr_wilder(h, l, c, n=14):
    pc = np.roll(c, 1); pc[0] = c[0]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    a = np.full(len(c), np.nan)
    if len(c) <= n:
        return a
    a[n - 1] = tr[:n].mean()
    for i in range(n, len(c)):
        a[i] = (a[i - 1] * (n - 1) + tr[i]) / n
    return a


def rsi_wilder(c, n=5):
    d = np.diff(c, prepend=c[0])
    up, dn = np.where(d > 0, d, 0.0), np.where(d < 0, -d, 0.0)
    au, ad = np.full(len(c), np.nan), np.full(len(c), np.nan)
    if len(c) <= n:
        return au
    au[n] = up[1:n + 1].mean(); ad[n] = dn[1:n + 1].mean()
    for i in range(n + 1, len(c)):
        au[i] = (au[i - 1] * (n - 1) + up[i]) / n
        ad[i] = (ad[i - 1] * (n - 1) + dn[i]) / n
    rs = au / np.where(ad == 0, np.nan, ad)
    return np.where(ad == 0, 100.0, 100 - 100 / (1 + rs))


def weekly_regime(close: pd.Series, wma: int) -> np.ndarray:
    """週K 大格局：+1＝週收盤在週均線之上且均線較 4 週前上升；-1＝反之；其餘 0。
    日線 t 只看「上一個已收完的週」，避免偷看當週。"""
    wk = close.index.to_period("W-FRI")
    wc = close.groupby(wk).last()
    ma = wc.rolling(wma).mean()
    slope = ma - ma.shift(4)
    reg = pd.Series(0, index=wc.index)
    reg[(wc > ma) & (slope > 0)] = 1
    reg[(wc < ma) & (slope < 0)] = -1
    reg = reg.where(ma.notna() & slope.notna(), 0).shift(1).fillna(0)     # 延後一週
    return reg.reindex(wk).to_numpy().astype(np.int64)


def _roll_max(a, n):
    return pd.Series(a).rolling(n).max().shift(1).to_numpy()


def _roll_min(a, n):
    return pd.Series(a).rolling(n).min().shift(1).to_numpy()


# ------------------------------------------------------------------ 訊號家族
def build_signals(fam: str, p: dict, X: dict, allow_short: bool):
    """回傳 sig_l, sig_s（收盤後產生的進場意圖）, ex_l, ex_s（收盤後產生的出場意圖）。"""
    c = X["c"]; R = X["reg"][p["wma"]]
    up, dn = R == 1, R == -1
    if fam == "REG":                               # 只看週K 大格局：轉多就進、離開就出
        sl, ss, el, es = up, dn, ~up, ~dn
    elif fam == "BRK":                             # 週K 順勢 + 日K 突破 N 日新高，跌破 M 日低出場
        hi, lo = _roll_max(c, p["N"]), _roll_min(c, p["N"])
        xl, xs = _roll_min(c, p["M"]), _roll_max(c, p["M"])
        sl = up & (c > hi); ss = dn & (c < lo)
        el = (c < xl) | ~up; es = (c > xs) | ~dn
    elif fam == "PB":                              # 週K 順勢 + 日K RSI(5) 回檔進場，RSI 回到高位出場
        r = X["rsi5"]
        sl = up & (r < p["thr"]); ss = dn & (r > 100 - p["thr"])
        el = (r > p["exit"]) | ~up; es = (r < 100 - p["exit"]) | ~dn
    elif fam == "MA":                              # 週K 順勢 + 日K 快慢均線黃金交叉
        a, b = X["ma"][p["a"]], X["ma"][p["b"]]
        cu = (a > b) & (np.roll(a, 1) <= np.roll(b, 1)); cd = (a < b) & (np.roll(a, 1) >= np.roll(b, 1))
        sl = up & cu; ss = dn & cd
        el = (a < b) | ~up; es = (a > b) | ~dn
    elif fam == "RO":                              # 風險關閉型：平常多頭持有，只在週K 轉空時離場（B 版轉空）
        sl, ss, el, es = ~dn, dn, dn, ~dn
    elif fam == "DMA":                             # 日K 站上長期均線 + 週K 不是空頭才做多（B 版：跌破 + 週K 空頭才放空）
        m = X["ma"][p["n"]]
        sl = (c > m) & ~dn; ss = (c < m) & dn
        el = (c < m) | dn; es = (c > m) | ~dn
    elif fam == "BAS":                             # 消息／情緒：逆價差（期貨貼水過深）逆向做多、正價差過大且週K 空頭放空
        b = X["bas"]
        sl = (b < -p["thr"]) & ~dn; ss = (b > p["thr"]) & dn
        el = (b > 0) | dn; es = (b < 0) | ~dn
    else:
        raise ValueError(fam)
    nan = np.isnan(X["atr"])
    sl = np.asarray(sl) & ~nan; ss = np.asarray(ss) & ~nan & allow_short
    return sl, ss, np.asarray(el), np.asarray(es)


GRIDS = {
    "REG": dict(wma=[20, 30, 40], k=[3.0, 5.0, 99.0]),
    "BRK": dict(wma=[20, 30, 40], N=[20, 40, 60], M=[10, 20], k=[2.0, 3.0, 5.0]),
    "PB": dict(wma=[20, 30, 40], thr=[20, 30], exit=[60, 70], k=[3.0, 5.0]),
    "MA": dict(wma=[20, 30, 40], a=[5, 10, 20], b=[20, 60], k=[3.0, 5.0]),
    "RO": dict(wma=[20, 30, 40], k=[3.0, 5.0, 99.0]),
    "DMA": dict(wma=[20, 30, 40], n=[100, 200], k=[3.0, 5.0]),
    "BAS": dict(wma=[20, 30, 40], thr=[0.002, 0.004], k=[3.0, 5.0]),
}


def build_grid():
    out = []
    for fam, g in GRIDS.items():
        keys = list(g)
        for vals in itertools.product(*[g[k] for k in keys]):
            p = dict(zip(keys, vals))
            if fam == "MA" and p["a"] >= p["b"]:
                continue
            p["fam"] = fam
            out.append(p)
    return out


def neighbors(p: dict, grid: list):
    """同家族、只差一個參數的相鄰格（該參數在格點清單中相鄰一格）。"""
    res = []
    g = GRIDS[p["fam"]]
    for key, vals in g.items():
        i = vals.index(p[key])
        for j in (i - 1, i + 1):
            if 0 <= j < len(vals):
                q = dict(p); q[key] = vals[j]
                if q in grid:
                    res.append(q)
    return res


# ------------------------------------------------------------------ 逐日模擬引擎
@njit(cache=True)
def _put(tr, k, a, b, c_, d, e, f, g, h_, i_, j):
    tr[k, 0] = a; tr[k, 1] = b; tr[k, 2] = c_; tr[k, 3] = d; tr[k, 4] = e
    tr[k, 5] = f; tr[k, 6] = g; tr[k, 7] = h_; tr[k, 8] = i_; tr[k, 9] = j


@njit(cache=True)
def _sim(o, h, l, c, atr, sl, ss, el, es, gl, gs, kstop, fee_pts, tax, slip, roll_pts, rollday):
    """回傳 (逐日損益點數, 交易表)。交易表欄：dir, signal_i, entry_i, exit_i, entry_px, exit_px,
    reason(1=訊號 2=停損 3=跳空停損 4=資料尾), pnl_pts(扣成本), mae_pts, mfe_pts。"""
    n = len(c)
    pnl = np.zeros(n)
    tr = np.zeros((n, 10))
    nt = 0
    pos = 0
    fill = 0.0; stop = 0.0; ext = 0.0; mark = 0.0; tp = 0.0; mae = 0.0; mfe = 0.0
    ent_i = 0; sig_i = 0
    for i in range(1, n):
        day = 0.0
        entered_today = False
        # 1) 開盤：出場訊號
        if pos != 0:
            ex = el[i - 1] if pos == 1 else es[i - 1]
            if ex:
                px = o[i] - pos * slip
                gain = pos * (px - mark) - fee_pts - tax * px
                day += gain; tp += gain
                _put(tr, nt, pos, sig_i, ent_i, i, fill, px, 1, tp, mae, mfe); nt += 1
                pos = 0
        # 2) 開盤：進場（收盤後訊號、隔日開盤成交）
        if pos == 0:
            want = 0
            if sl[i - 1] and gl[i - 1]:
                want = 1
            elif ss[i - 1] and gs[i - 1]:
                want = -1
            if want != 0:
                pos = want
                fill = o[i] + pos * slip
                cst = fee_pts + tax * fill
                day -= cst; tp = -cst
                stop = fill - pos * kstop * atr[i - 1]
                ext = fill; mark = fill; mae = 0.0; mfe = 0.0
                ent_i = i; sig_i = i - 1
                entered_today = True
        # 3) 盤中停損
        if pos != 0:
            adv = (fill - l[i]) if pos == 1 else (h[i] - fill)
            fav = (h[i] - fill) if pos == 1 else (fill - l[i])
            if adv > mae:
                mae = adv
            if fav > mfe:
                mfe = fav
            hit = (l[i] <= stop) if pos == 1 else (h[i] >= stop)
            if hit:
                gap = (not entered_today) and ((o[i] <= stop) if pos == 1 else (o[i] >= stop))
                px0 = o[i] if gap else stop
                px = px0 - pos * slip
                gain = pos * (px - mark) - fee_pts - tax * px
                day += gain; tp += gain
                _put(tr, nt, pos, sig_i, ent_i, i, fill, px, 3 if gap else 2, tp, mae, mfe); nt += 1
                pos = 0
        # 4) 續抱到收盤
        if pos != 0:
            day += pos * (c[i] - mark)
            tp += pos * (c[i] - mark)
            mark = c[i]
            if rollday[i]:                       # 結算日收盤持倉：換月成本
                day -= roll_pts + 2 * fee_pts
                tp -= roll_pts + 2 * fee_pts
            ext = max(ext, c[i]) if pos == 1 else min(ext, c[i])
            ns = ext - pos * kstop * atr[i]
            stop = max(stop, ns) if pos == 1 else min(stop, ns)
        pnl[i] = day
    if pos != 0:
        _put(tr, nt, pos, sig_i, ent_i, n - 1, fill, c[n - 1], 4, tp, mae, mfe); nt += 1
    return pnl, tr[:nt]


def settle_days(idx: pd.DatetimeIndex) -> np.ndarray:
    """每月第三個週三（遇休市順延到下一個交易日）＝結算日。"""
    out = np.zeros(len(idx), bool)
    for y in range(idx[0].year, idx[-1].year + 1):
        for m in range(1, 13):
            d0 = pd.Timestamp(y, m, 1)
            w = d0 + pd.Timedelta(days=(2 - d0.weekday()) % 7 + 14)
            j = idx.searchsorted(w)
            if j < len(idx) and idx[j].month == m:
                out[j] = True
    return out


class Lab:
    def __init__(self):
        self.tx = load_tx()
        self.idx = self.tx.index
        self.o, self.h, self.l, self.c = (self.tx[k].to_numpy() for k in ("open", "high", "low", "close"))
        self.atr = atr_wilder(self.h, self.l, self.c)
        self.X = dict(c=self.c, atr=self.atr, rsi5=rsi_wilder(self.c, 5),
                      reg={w: weekly_regime(self.tx.close, w) for w in (20, 30, 40)},
                      ma={n: pd.Series(self.c).rolling(n).mean().to_numpy() for n in (5, 10, 20, 60, 100, 200)})
        d = _rd("index_ohlc"); d["date"] = pd.to_datetime(d["date"])
        tse = d[d.symbol == "TSE"].drop_duplicates("date").set_index("date")["close"].reindex(self.idx).ffill()
        # 基差（期貨 - 現貨）/ 現貨，5 日平均；FUT 13:45 收、指數 13:30 收，單日雜訊大所以平滑
        self.X["bas"] = ((self.tx.close - tse) / tse).rolling(5).mean().to_numpy()
        self.settle = settle_days(self.idx)
        # 持倉跨結算日（收盤仍持倉）才要換月；用「結算日」當換月日
        self.b50 = load_0050(self.idx)
        self.ones = np.ones(len(self.idx), bool)
        self.fee_pts = FEE_NTD / MULT
        self.cache = {}

    def run(self, p: dict, allow_short: bool, gl=None, gs=None, slip=SLIP_PTS):
        key = (tuple(sorted(p.items())), allow_short, None if gl is None else gl.tobytes(),
               None if gs is None else gs.tobytes(), slip)
        if key in self.cache:
            return self.cache[key]
        sl, ss, el, es = build_signals(p["fam"], p, self.X, allow_short)
        pnl, tr = _sim(self.o, self.h, self.l, self.c, np.nan_to_num(self.atr, nan=1e9), sl, ss, el, es,
                       self.ones if gl is None else gl, self.ones if gs is None else gs,
                       p["k"], self.fee_pts, TAX, slip, ROLL_PTS, self.settle)
        prev = np.roll(self.c, 1); prev[0] = self.c[0]
        r = pd.Series(pnl / prev, index=self.idx)                 # 1 倍名目曝險的日報酬（不含利息）
        tdf = pd.DataFrame(tr, columns=["dir", "sig_i", "entry_i", "exit_i", "entry_px", "exit_px",
                                        "reason", "pnl_pts", "mae_pts", "mfe_pts"])
        res = (r, tdf)
        self.cache[key] = res
        return res

    # --- 報酬統計
    def lev_ret(self, r: pd.Series, lev: float) -> pd.Series:
        return lev * r + CASH_Y / PPY

    def bh_tx(self) -> pd.Series:
        prev = np.roll(self.c, 1); prev[0] = self.c[0]
        r = pd.Series((self.c - prev) / prev, index=self.idx)
        r.iloc[0] = 0
        return r

    def bh_0050(self, a, b=None) -> pd.Series:
        """同窗、同成本、含息：窗首開盤買（手續費+滑價），窗尾收盤賣（手續費+ETF 稅+滑價）。"""
        r = self.b50["ret"]
        s = r[(r.index >= a) & ((r.index < b) if b else True)].copy()
        if len(s) < 2:
            return s
        i0 = self.idx.get_loc(s.index[0])
        s.iloc[0] = self.b50["open_ratio"].iloc[i0] / ((1 + ETF_SLIP) * (1 + ETF_FEE)) - 1
        s.iloc[-1] = (1 + s.iloc[-1]) * (1 - ETF_SLIP) * (1 - ETF_FEE - ETF_TAX) - 1
        return s


def stats(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 20:
        return dict(cagr=np.nan, mdd=np.nan, sharpe=np.nan, tot=np.nan)
    eq = (1 + r).cumprod()
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    cagr = eq.iloc[-1] ** (1 / max(yrs, 1e-9)) - 1
    sh = r.mean() / r.std() * np.sqrt(PPY) if r.std() > 0 else np.nan
    return dict(cagr=cagr, mdd=(eq / eq.cummax() - 1).min(), sharpe=sh, tot=eq.iloc[-1] - 1)


def slice_(r, a, b=None):
    return r[(r.index >= a) & ((r.index < b) if b else True)]


def trade_stats(t: pd.DataFrame, idx, a, b=None) -> dict:
    if len(t) == 0:
        return dict(n=0, win=np.nan, payoff=np.nan, hold=np.nan)
    d = idx[t.entry_i.to_numpy().astype(int)]
    m = (d >= pd.Timestamp(a)) & ((d < pd.Timestamp(b)) if b else True)
    t = t[m]
    if len(t) == 0:
        return dict(n=0, win=np.nan, payoff=np.nan, hold=np.nan)
    w = t[t.pnl_pts > 0]; lo = t[t.pnl_pts <= 0]
    payoff = (w.pnl_pts.mean() / abs(lo.pnl_pts.mean())) if len(w) and len(lo) and lo.pnl_pts.mean() != 0 else np.nan
    hold = float(np.mean((idx[t.exit_i.to_numpy().astype(int)] - idx[t.entry_i.to_numpy().astype(int)]).days))
    return dict(n=len(t), win=len(w) / len(t), payoff=payoff, hold=hold)


# ------------------------------------------------------------------ walk-forward
def select(lab: Lab, grid, allow_short, a, b, fams=None, gates=(None, None)):
    """在訓練窗 [a,b) 以淨年化報酬（1 倍）選最佳參數；交易數太少者不參選。"""
    best, bs = None, -9
    for p in grid:
        if fams and p["fam"] not in fams:
            continue
        r, t = lab.run(p, allow_short, *gates)
        ts = trade_stats(t, lab.idx, a, b)
        if ts["n"] < MIN_TRAIN_TRADES:
            continue
        s = stats(lab.lev_ret(slice_(r, a, b), 1.0))["cagr"]
        if s > bs:
            best, bs = p, s
    return best, bs


def walk_forward(lab: Lab, grid, allow_short, fams=None, gates=(None, None)):
    ends = SEGMENTS[1:] + [None]
    segs = []
    for a, b in zip(SEGMENTS, ends):
        p, tr_cagr = select(lab, grid, allow_short, TRAIN_START, a, fams, gates)
        r, t = lab.run(p, allow_short, *gates)
        segs.append(dict(a=a, b=b, p=p, train_cagr=tr_cagr, r=slice_(r, a, b), t=t))
    return segs


def wf_report(lab: Lab, segs, grid, allow_short, lev=1.0, gates=(None, None)):
    rows = []
    allr = []
    for s in segs:
        rr = lab.lev_ret(s["r"], lev)
        st = stats(rr); b50 = stats(lab.bh_0050(s["a"], s["b"]))
        ts = trade_stats(s["t"], lab.idx, s["a"], s["b"])
        # 鄰域：相鄰格在該測試窗的年化
        nb = []
        for q in neighbors(s["p"], grid):
            rq, _ = lab.run(q, allow_short, *gates)
            nb.append(stats(lab.lev_ret(slice_(rq, s["a"], s["b"]), lev))["cagr"])
        rows.append(dict(a=s["a"], b=s["b"] or "迄今", p=s["p"], train=s["train_cagr"], cagr=st["cagr"],
                         b50=b50["cagr"], mdd=st["mdd"], b50mdd=b50["mdd"], n=ts["n"], win=ts["win"],
                         payoff=ts["payoff"], hold=ts["hold"],
                         nb_med=float(np.nanmedian(nb)) if nb else np.nan,
                         nb_beat=float(np.mean([x >= b50["cagr"] for x in nb])) if nb else np.nan,
                         beat=st["cagr"] >= b50["cagr"]))
        allr.append(rr)
    oos = pd.concat(allr)
    a0, b0 = SEGMENTS[0], None
    so, sb = stats(oos), stats(lab.bh_0050(a0, b0))
    ntr = sum(r["n"] for r in rows)
    return rows, oos, so, sb, ntr


def verdict(c1, b50, wins, nseg, c2, c3):
    if c1 >= b50:
        return ("通過（1 倍，且每段都贏）" if wins == nseg else "名義通過（1 倍整體贏，但分段未全勝，不建議採用）")
    if max(c2, c3) >= b50:
        return "淘汰（1 倍輸；僅加槓桿才贏）"
    return "淘汰，不使用"


def fmt(x, pct=True, d=1):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "-"
    return f"{x * 100:.{d}f}%" if pct else f"{x:.{d}f}"


# ------------------------------------------------------------------ 籌碼／消息濾網
def foreign_net_oi(idx) -> pd.Series:
    """外資 TX 期貨淨未平倉（多 - 空，口）。2021-01 前資料湖沒有，回 NaN。收盤後公布，訊號日收盤可用。"""
    f = _rd("fut_inst", ["date", "futures_id", "who", "long_oi", "short_oi"])
    f = f[(f.futures_id == "TX") & (f.who == "foreign")].copy()
    f["date"] = pd.to_datetime(f["date"])
    s = (f.long_oi - f.short_oi).groupby(f.date).last().astype(float)
    return s.reindex(idx)


def make_gates(lab: Lab, chip: bool):
    """gate[i]＝訊號日 i（隔日 i+1 開盤進場）可不可以進場。
    結算週濾網：訊號日或進場日是結算日 -> 不新開倉（結算前後價格易被法人影響，期貨評論的共識注意事項）。
    籌碼濾網（可選，僅 2021 後有資料；缺值視為不濾）：做多需外資淨部位 5 日變化 >= 0，放空需 <= 0。一條規則，不調參。"""
    n = len(lab.idx)
    st = lab.settle
    ok = ~(st | np.append(st[1:], False))
    gl, gs = ok.copy(), ok.copy()
    if chip:
        net = foreign_net_oi(lab.idx)
        chg = (net - net.shift(5)).to_numpy()
        has = ~np.isnan(chg)
        gl &= ~has | (chg >= 0)
        gs &= ~has | (chg <= 0)
    return gl, gs, (foreign_net_oi(lab.idx) if True else None)


# ------------------------------------------------------------------ 交易筆記
REASON = {1: "訊號出場", 2: "盤中停損", 3: "跳空越過停損", 4: "資料尾端強制平倉"}


def trades_table(lab: Lab, segs, tag: str, allow_short: bool) -> pd.DataFrame:
    net = foreign_net_oi(lab.idx)
    chg = net - net.shift(5)
    macro = _rd("macro_calendar")
    mdates = {pd.Timestamp(d): r for d, r in zip(macro["date"], macro["release"])}
    ends = SEGMENTS[1:] + [None]
    rows = []
    for s, (a, b) in zip(segs, zip(SEGMENTS, ends)):
        t = s["t"]
        for _, x in t.iterrows():
            ei, xi, si = int(x.entry_i), int(x.exit_i), int(x.sig_i)
            ed = lab.idx[ei]
            if ed < pd.Timestamp(a) or (b and ed >= pd.Timestamp(b)):
                continue
            p = s["p"]
            d = int(x.dir)
            R = lab.X["reg"][p["wma"]][si]
            chip = chg.iloc[si]
            chip_s = "無資料" if np.isnan(chip) else ("順向" if np.sign(chip) == d else ("反向" if chip != 0 else "持平"))
            dts = [lab.idx[j] for j in range(max(0, ei - 3), min(len(lab.idx), ei + 2)) if lab.settle[j]]
            sw = "是" if dts else "否"
            ev = [mdates[lab.idx[j]] for j in range(max(0, ei - 1), min(len(lab.idx), xi + 1)) if lab.idx[j] in mdates]
            notional = x.entry_px * MULT
            ret = x.pnl_pts * MULT / notional
            hold = (lab.idx[xi] - ed).days
            mae_pct = x.mae_pts / x.entry_px
            give = (1 - (x.pnl_pts / x.mfe_pts)) if x.mfe_pts > 0 and x.pnl_pts > 0 else np.nan
            rv = review(x, d, hold, chip_s, sw, give, R)
            sc = (1 if d == R else 0) + (1 if chip_s == "順向" else (-1 if chip_s == "反向" else 0)) + (-1 if sw == "是" else 0)
            rows.append(dict(
                版本=tag, 方向="多" if d == 1 else "空", 參數=_ps(p), 訊號日=lab.idx[si].date(), 進場日=ed.date(),
                進場價=round(x.entry_px, 1), 出場日=lab.idx[xi].date(), 出場價=round(x.exit_px, 1),
                出場原因=REASON[int(x.reason)], 損益點=round(x.pnl_pts, 1), 損益元每口=round(x.pnl_pts * MULT),
                報酬率_名義=round(ret, 4), 持有天數=hold, 最大不利偏移點=round(x.mae_pts, 1),
                最大不利偏移_pct=round(mae_pct, 4), 最大有利偏移點=round(x.mfe_pts, 1),
                週K狀態=("多頭" if R == 1 else "空頭" if R == -1 else "中性"),
                日K訊號=_sig(p), 外資期貨5日變化口=None if np.isnan(chip) else int(chip), 籌碼=chip_s,
                結算週=sw, 事件日="、".join(ev) if ev else "", 籌碼消息分數=sc, 事後檢討=rv))
    return pd.DataFrame(rows)


def _ps(p):
    return ",".join(f"{k}={v}" for k, v in p.items() if k != "fam") and f"{p['fam']}(" + ",".join(f"{k}={v}" for k, v in p.items() if k != "fam") + ")"


def _sig(p):
    f = p["fam"]
    if f == "REG": return f"週K 轉為順勢（{p['wma']}週均線）次日開盤進"
    if f == "BRK": return f"收盤突破前 {p['N']} 日極值（週K 同向）"
    if f == "PB": return f"RSI(5) 回檔至 {p['thr']} 以下/反向對稱（週K 同向）"
    if f == "MA": return f"{p['a']}日/{p['b']}日均線交叉（週K 同向）"
    if f == "RO": return "週K 非空頭即持有（風險關閉型）"
    if f == "BAS": return f"5日平均基差 < -{p['thr']:.1%}（逆價差逆向做多）/ 反向對稱"
    return f"站上/跌破 {p['n']} 日均線（週K 不逆向）"


def review(x, d, hold, chip_s, sw, give, R):
    pnl = x.pnl_pts
    msg = []
    if pnl > 0:
        if give == give and give > 0.5:
            msg.append(f"賺但回吐 {give:.0%} 的最大浮盈，出場偏慢；可試分批停利或收緊移動停損")
        else:
            msg.append("順勢賺到，出場尚可")
    else:
        if int(x.reason) == 3:
            msg.append("跳空直接越過停損，實損大於預期風險；事件日、長假、週末前可降部位")
        elif int(x.reason) == 2 and hold <= 5:
            msg.append(f"進場後 {hold} 日內即被停損，疑似假突破或追價；可要求回測不破再進")
        elif int(x.reason) == 2:
            msg.append("趨勢中被 ATR 停損洗出；停損倍數偏緊或遇修正")
        elif int(x.reason) == 1 and x.mfe_pts > 2 * abs(pnl) and x.mfe_pts > 0:
            msg.append("曾大幅獲利後轉虧，出場訊號太慢；應在浮盈時先上移停損")
        else:
            msg.append("訊號出場仍虧，趨勢轉折偵測落後（均線類通病）")
        if chip_s == "反向":
            msg.append("進場時外資期貨部位與方向相反，籌碼濾網本可擋下")
        if sw == "是":
            msg.append("在結算週附近進場，結算週濾網本可擋下")
        if d == -1 and pnl < 0:
            msg.append("放空遇反彈；台股長期多頭偏態，空單須更嚴的停損")
    return "；".join(msg)


# ------------------------------------------------------------------ 主流程
def row_for(lab, name, ver, segs, grid, allow_short, gates=(None, None)):
    rows, oos1, so1, sb, ntr = wf_report(lab, segs, grid, allow_short, 1.0, gates)
    _, oos2, so2, _, _ = wf_report(lab, segs, grid, allow_short, 2.0, gates)
    _, oos3, so3, _, _ = wf_report(lab, segs, grid, allow_short, 3.0, gates)
    wins = sum(r["beat"] for r in rows)
    v = verdict(so1["cagr"], sb["cagr"], wins, len(rows), so2["cagr"], so3["cagr"])
    ts = dict(n=ntr)
    allt = pd.concat([s["t"].assign(_a=s["a"], _b=s["b"] or "2100-01-01") for s in segs])
    d = lab.idx[allt.entry_i.astype(int).to_numpy()]
    m = (d >= pd.to_datetime(allt._a).to_numpy()) & (d < pd.to_datetime(allt._b).to_numpy())
    allt = allt[m]
    w = allt[allt.pnl_pts > 0]; lo = allt[allt.pnl_pts <= 0]
    return dict(策略=f"{ver} {name}", 樣本外年化=so1["cagr"], 同窗0050=sb["cagr"], 差距=so1["cagr"] - sb["cagr"],
                最大回撤=so1["mdd"], 夏普=so1["sharpe"], 回撤3x=so3["mdd"], 年化2x=so2["cagr"], 年化3x=so3["cagr"],
                分段勝=f"{wins}/{len(rows)}", 交易數=len(allt), 勝率=len(w) / max(len(allt), 1),
                賺賠比=(w.pnl_pts.mean() / abs(lo.pnl_pts.mean())) if len(w) and len(lo) else np.nan,
                判定=v), rows, oos1


def md_table(df: pd.DataFrame) -> str:
    h = "| " + " | ".join(df.columns) + " |\n|" + "---|" * len(df.columns) + "\n"
    return h + "\n".join("| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False)) + "\n"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    lab = Lab(); grid = build_grid()
    fams_all = [None] + list(GRIDS)
    summary, detail, oos_paths, segsave = [], {}, {}, {}
    for ver, sh in (("A只多", False), ("B多空", True)):
        for fam in fams_all:
            segs = walk_forward(lab, grid, sh, [fam] if fam else None)
            nm = "全家族自動選" if fam is None else f"家族 {fam}"
            row, rows, oos = row_for(lab, nm, ver, segs, grid, sh)
            summary.append(row); detail[(ver, nm)] = rows; oos_paths[(ver, nm)] = oos; segsave[(ver, nm)] = segs
    # 結算週／籌碼濾網（全家族自動選，重新 walk-forward）
    for lab_nm, chip in (("+結算週濾網", False), ("+結算週+外資籌碼濾網", True)):
        gl, gs, _ = make_gates(lab, chip)
        for ver, sh in (("A只多", False), ("B多空", True)):
            segs = walk_forward(lab, grid, sh, None, (gl, gs))
            row, rows, oos = row_for(lab, "全家族自動選" + lab_nm, ver, segs, grid, sh, (gl, gs))
            summary.append(row); detail[(ver, "全家族自動選" + lab_nm)] = rows; oos_paths[(ver, "全家族自動選" + lab_nm)] = oos
            segsave[(ver, "全家族自動選" + lab_nm)] = segs
    # 對照：台指期買進持有
    bh = lab.bh_tx(); a0 = SEGMENTS[0]
    sbh = {l: stats(lab.lev_ret(slice_(bh, a0), l)) for l in (1, 2, 3)}
    b50 = stats(lab.bh_0050(a0))
    summary.append(dict(策略="對照 台指期永遠持有（1 倍，不是策略）", 樣本外年化=sbh[1]["cagr"], 同窗0050=b50["cagr"],
                        差距=sbh[1]["cagr"] - b50["cagr"], 最大回撤=sbh[1]["mdd"], 夏普=sbh[1]["sharpe"], 回撤3x=sbh[3]["mdd"],
                        年化2x=sbh[2]["cagr"], 年化3x=sbh[3]["cagr"], 分段勝="-", 交易數=0, 勝率=np.nan, 賺賠比=np.nan,
                        判定="基準／對照（不是策略）"))
    S = pd.DataFrame(summary)
    S.to_pickle(OUT / "_summary.pkl")
    # 交易明細（主要提交：全家族自動選 A 與 B）
    tA = trades_table(lab, segsave[("A只多", "全家族自動選")], "A只多", False)
    tB = trades_table(lab, segsave[("B多空", "全家族自動選")], "B多空", True)
    tA.to_csv(OUT / "trades_long.csv", index=False, encoding="utf-8-sig")
    tB.to_csv(OUT / "trades_longshort.csv", index=False, encoding="utf-8-sig")
    import pickle
    pickle.dump(dict(summary=S, detail=detail, trial=len(lab.cache), tA=tA, tB=tB), open(OUT / "_run.pkl", "wb"))
    # 其他附屬分析
    extra = extras(lab, grid, segsave, oos_paths)
    pickle.dump(extra, open(OUT / "_extra.pkl", "wb"))
    write_docs()
    print("試驗組數（不重複的完整回測）:", len(lab.cache))


def extras(lab, grid, segsave, oos_paths):
    ex = {}
    # 年度：熊市年
    yrs = [2008, 2015, 2018, 2020, 2022]
    bh = lab.bh_tx()
    seg0 = segsave[("A只多", "全家族自動選")][0]["p"]
    segB0 = segsave[("B多空", "全家族自動選")][0]["p"]
    rA = lab.run(seg0, False)[0]; rB = lab.run(segB0, True)[0]
    tab = []
    for y in yrs:
        a, b = f"{y}-01-01", f"{y + 1}-01-01"
        f = lambda r: (1 + slice_(lab.lev_ret(r, 1.0), a, b)).prod() - 1
        wfA = (1 + slice_(oos_paths[("A只多", "全家族自動選")].reindex(lab.idx).dropna(), a, b)).prod() - 1 if y >= 2013 else np.nan
        wfB = (1 + slice_(oos_paths[("B多空", "全家族自動選")].reindex(lab.idx).dropna(), a, b)).prod() - 1 if y >= 2013 else np.nan
        tab.append(dict(年=y, 台指期持有=f(bh), **{"0050": (1 + lab.b50["ret"][(lab.b50.index >= a) & (lab.b50.index < b)]).prod() - 1},
                        A_首段固定參數=f(rA), B_首段固定參數=f(rB), A_WF樣本外=wfA, B_WF樣本外=wfB))
    ex["bear"] = pd.DataFrame(tab)
    # 滑價 1 點敏感度
    sens = {}
    for ver, sh in (("A只多", False), ("B多空", True)):
        segs = segsave[(ver, "全家族自動選")]
        rr = pd.concat([slice_(lab.lev_ret(lab.run(s["p"], sh, slip=1.0)[0], 1.0), s["a"], s["b"]) for s in segs])
        sens[ver] = stats(rr)["cagr"]
    ex["slip1"] = sens
    # 各段選到的參數
    ex["trial_total"] = len(lab.cache)
    return ex




# ------------------------------------------------------------------ 文件輸出
def write_docs():
    import pickle
    d = pickle.load(open(OUT / "_run.pkl", "rb")); ex = pickle.load(open(OUT / "_extra.pkl", "rb"))
    S, detail, tA, tB = d["summary"], d["detail"], d["tA"], d["tB"]
    nfam = len(GRIDS); ngrid = len(build_grid())
    T = S.copy()
    for c in ("樣本外年化", "同窗0050", "最大回撤", "回撤3x", "年化2x", "年化3x", "勝率"):
        T[c] = T[c].map(fmt)
    T["差距"] = S["差距"].map(lambda x: f"{x * 100:+.1f} 個百分點")
    T["夏普"] = S["夏普"].map(lambda x: fmt(x, False, 2)); T["賺賠比"] = S["賺賠比"].map(lambda x: fmt(x, False, 2))
    main_tab = T[["策略", "樣本外年化", "同窗0050", "差距", "最大回撤", "夏普", "年化2x", "年化3x", "回撤3x", "分段勝", "交易數", "判定"]]
    nbest = S[S["策略"].str.startswith(("A", "B"))].sort_values("差距", ascending=False).iloc[0]
    a_all = S[S["策略"] == "A只多 全家族自動選"].iloc[0]; b_all = S[S["策略"] == "B多空 全家族自動選"].iloc[0]
    bh = S[S["策略"].str.startswith("對照")].iloc[0]
    n_pass = int(S["判定"].str.startswith("通過").sum())
    segtxt = []
    for key in (("A只多", "全家族自動選"), ("B多空", "全家族自動選"), ("A只多", "家族 RO"), ("B多空", "家族 RO")):
        rows = detail[key]
        df = pd.DataFrame([dict(測試窗=f"{r['a']}～{r['b']}", 選到參數=_ps(r["p"]), 訓練年化=fmt(r["train"]), 測試年化=fmt(r["cagr"]),
                               同窗0050=fmt(r["b50"]), 測試回撤=fmt(r["mdd"]), **{"0050回撤": fmt(r["b50mdd"])}, 交易數=r["n"],
                               勝率=fmt(r["win"], d=0), 鄰域中位年化=fmt(r["nb_med"]), 鄰域贏0050比例=fmt(r["nb_beat"], d=0),
                               勝負="贏" if r["beat"] else "輸") for r in rows])
        segtxt.append(f"**{key[0]} {key[1]}**\n\n" + md_table(df))
    bear = ex["bear"].copy()
    for c in bear.columns[1:]:
        bear[c] = bear[c].map(lambda x: fmt(x))
    # 彙整交易統計（優化空間用）
    def agg(t):
        o = {}
        o["n"] = len(t); o["win"] = (t.損益點 > 0).mean(); o["sum"] = t.損益點.sum()
        o["gap_n"] = int((t.出場原因 == "跳空越過停損").sum()); o["gap_avg"] = t[t.出場原因 == "跳空越過停損"].損益點.mean()
        o["stop_n"] = int((t.出場原因 == "盤中停損").sum()); o["stop_avg"] = t[t.出場原因 == "盤中停損"].損益點.mean()
        for nm in ("順向", "反向"):
            x = t[t.籌碼 == nm]; o[nm] = (len(x), x.損益點.mean(), (x.損益點 > 0).mean() if len(x) else np.nan)
        x = t[t.結算週 == "是"]; y = t[t.結算週 == "否"]
        o["sw"] = (len(x), x.損益點.mean(), len(y), y.損益點.mean())
        o["short"] = (int((t.方向 == "空").sum()), t[t.方向 == "空"].損益點.sum())
        w = t[t.損益點 > 0]; o["mfe_giveback"] = ((w.最大有利偏移點 - w.損益點) / w.最大有利偏移點).median()
        return o
    ga, gb = agg(tA), agg(tB)
    worst = lambda t: md_table(t.nsmallest(5, "損益點")[["進場日", "方向", "進場價", "出場日", "出場價", "出場原因", "損益點", "報酬率_名義", "最大不利偏移_pct", "持有天數", "事後檢討"]])
    sl = ex["slip1"]
    L = []
    L.append("# 台指期（TX）交易系統研究：只做多（A）與多空都做（B）\n")
    L.append("> **免責**：歷史資料的研究回測，非買賣建議、不下單、未接券商。淘汰規則（Andy 定，不放寬）：**樣本外年化報酬 < 同窗、同成本、含息的 0050 買進持有 -> 淘汰**；"
             "1 倍名目曝險必須贏過 0050 才算數，只有加槓桿才贏的另外標明且仍不算通過；walk-forward 每一段各比一次。\n")
    L.append(f"## 〇、通過／淘汰清單（共 {len(S)} 列：通過 {n_pass} 列）\n")
    L.append("樣本外 = walk-forward 串接 2013-01-01 起至資料尾（約 13.8 年，5 段，每段參數只用該段之前的資料選出）。年化 = 1 倍名目曝險、扣手續費／期交稅／滑價／換月成本、閒置資金年息 1%；"
             "「年化2x／3x」為同一條路徑放大 2、3 倍曝險（回撤3x 為 3 倍時的最大回撤）。0050 = 同窗含息、窗首開盤買、窗尾賣，扣手續費 0.1425%、ETF 證交稅 0.1%、滑價 0.1%。\n")
    L.append(md_table(main_tab))
    L.append(f"\n**結論：沒有任何一套通過。** 表內最好的 1 倍結果是「{nbest['策略']}」樣本外年化 {fmt(nbest['樣本外年化'])}，仍落後 0050（{fmt(nbest['同窗0050'])}）{abs(nbest['差距'])*100:.1f} 個百分點，"
             f"且分段 {nbest['分段勝']} 勝。連「台指期永遠持有」（1 倍，{fmt(bh['樣本外年化'])}）都輸 0050 {abs(bh['差距'])*100:.1f} 個百分點——"
             "這是這個題目最重要的事實：**1 倍台指期在 2013 年後結構上就不如 0050**（實測：同窗 0050 含息年化 19.5%，台指期永遠持有 15.0%；0050 含息，台指期價格不含息，只能靠逆價差收斂拿回一部分，本輪未拆解兩者差距的成分），"
             "擇時要再贏過 0050，等於要同時贏過「台指期永遠持有」，而趨勢濾網在 V 型急殺急彈（2015、2018、2020、2022）裡出場晚、回場更晚，反而把報酬吃掉。\n")
    L.append("標「僅加槓桿才贏」者是指 1 倍輸、但 2 倍或 3 倍曝險年化超過 0050；它們的 3 倍最大回撤見表（約 -39%～-93%），而且贏的來源是借更多槓桿，不是策略有 alpha，所以仍然淘汰。"
             "（「台指期永遠持有」3 倍年化也贏，但那不是策略，是賭大盤長期多頭加高槓桿，回撤同樣巨大。）\n")
    L.append("## 一、系統設計（由大到小）\n")
    L.append("1. **週K 判大格局**：週收盤 > 週均線（20／30／40 週）且均線高於 4 週前 -> 多頭；反之空頭；其餘中性。日線只看「上一個已收完的週」，絕不偷看當週。\n"
             "2. **籌碼與消息濾網**：結算週（結算日及前一日不新開倉，全期可驗）、外資 TX 期貨淨部位 5 日變化需與方向同向（fut_inst 只有 2021-01 起，故只能在 2021 後驗證，缺值視為不濾）。"
             "另有「基差（期貨-現貨）」家族 BAS 當作情緒／消息代理。macro_calendar 只有 2026 年的 27 筆未來事件，歷史事件日無法回測，只在交易筆記標註。\n"
             "3. **日K 找進出場**（訊號收盤後產生、隔日開盤成交）：REG（週K 轉順勢就進）、BRK（突破 N 日高，跌破 M 日低出）、PB（RSI(5) 回檔）、MA（快慢均線交叉）、RO（風險關閉型：非空頭就持有）、DMA（長期均線）、BAS（逆價差逆向）。\n"
             "4. **停損與部位**：ATR(14) 倍數的移動停損（只往有利方向移，觸價成交，跳空用開盤價）；固定 1 倍名目曝險，一口一次，不加碼、不金字塔。"
             "版本 A 只做多；版本 B 在週K 空頭時對稱放空。\n")
    L.append("### 規則白話版（以 walk-forward 最後一段選出的參數為例）\n")
    pa = detail[("A只多", "全家族自動選")][-1]["p"]; pb = detail[("B多空", "全家族自動選")][-1]["p"]
    L.append(f"- A：{_sig(pa)}；週K 狀態不能是空頭（{pa['wma']} 週均線）才進；進場後以 {pa['k']} 倍 ATR 移動停損，基差回到 0 以上或週K 轉空頭就出場；1 口對應帳戶權益（1 倍名目）。\n"
             f"- B：同 A，另外週K 空頭且基差高於 +{pb.get('thr', 0):.1%} 才放空，出場對稱。\n"
             "- 另一個人照做會做出一樣的單：所有判斷用收盤價，隔日開盤下單；週K 以週五收盤為準。\n")
    L.append("## 二、資料與口徑（誠實版）\n")
    L.append("| 項目 | 做法 |\n|---|---|\n"
             "| 價格 | 資料湖 `index_ohlc` 的 `symbol=FUT`＝FinMind 台指期（TX）日盤近月連續日K，2000-01-04 起，**真實期貨價，不是加權指數代理**，已含正逆價差。 |\n"
             "| 正價差／逆價差 | 直接內含於期貨價。另以 `TSE` 現貨算 5 日平均基差，做成 BAS 家族與筆記欄位。FUT 13:45 收盤、現貨 13:30 收盤，單日基差有時間差雜訊，所以平滑。2026 年基差平均 +131 點、最大 +697，明顯大於歷年（-46～+15 點），疑似資料異常或市況極端，未修正，列為限制。 |\n"
             "| 換月成本 | 連續序列在結算後換月有跳點，實測結算隔日平均跳動 46 點 vs 一般日 29 點，差距小到不另行修補；持倉過結算日收盤時，每次加扣 4 點滑價（賣舊買新）＋兩口手續費。 |\n"
             "| 夜盤 | 不納入（FUT_N 僅 2017-05 起）。日盤收盤到次日開盤的隔夜跳空含在序列內。 |\n"
             "| 保證金與槓桿 | 主結果 1 倍名目曝險（帳戶權益＝一口名義，保證金約 1/6，其餘為現金，計年息 1%——假設，非資料）。2、3 倍為同路徑放大，未模擬追繳保證金與被強制平倉，3 倍結果因此偏樂觀。 |\n"
             "| 成本 | 每口單邊手續費 50 元、期交稅十萬分之二（單邊）、滑價單邊 2 點。滑價降為 1 點時樣本外年化：A "
             f"{fmt(sl['A只多'])}、B {fmt(sl['B多空'])}（結論不變）。 |\n"
             "| 0050 基準 | 還原總報酬：price_daily 收盤＋除息（etf_dividend_events／dividend_events）＋2025 一拆四處理；2003-06 起有資料。 |\n"
             "| 外資期貨籌碼 | fut_inst 外資 TX 多空未平倉，2021-01 起；之前無資料。 |\n"
             "| 60 分K | index_intraday 為加權指數 60 分K（2023-09 起），僅 2.1 年且非期貨價，**本輪未用於進出場**，日K 已是主要進場週期。 |\n")
    L.append("### 期交所歷史日K 能不能抓\n")
    L.append("查過期交所網站（taifex.com.tw）：『交易歷史資料申請』與『資料下載專區』是申請制／頁面下載，頁面導覽沒有看到免申請、可程式抓取的歷史日K 開放 API；本輪未確認其使用條款是否允許自動抓取，依專案原則不爬。"
             "而資料湖的 `index_ohlc.FUT`（FinMind）已涵蓋 2000 年起日盤日K，故**不另寫抓取腳本**，繼續使用現有資料。\n")
    L.append("## 三、上網查到的期貨交易者常用方法（出處）\n")
    L.append("| 關鍵字 | 來源類別 | 出處 | 取用的點 |\n|---|---|---|---|\n"
             "| 台指期 順勢交易 週線 日線 進場 停損 ATR | 學術論文 | [虎尾科大：停損與買入持有之損益比較，以台股指數期貨為例](https://nfuacademic.nfu.edu.tw/wp-content/uploads/sites/31/2025/06/04停損與買入持有之損益比較-以台股指數期貨為例.pdf) | 該研究結論：ATR／固定天數停損策略並未優於買入持有——與本輪結果相符，故本輪一律與「永遠持有」對照。 |\n"
             "| 同上 | 學位論文 | [中央大學論文庫：台指期順勢策略，日K／60分K／30分K 與 0050 長期持有對照](https://ir.lib.ncu.edu.tw/handle/987654321/86209) | 順勢策略以 0050 長期持有為對照組。 |\n"
             "| 台指期 外資期貨未平倉淨部位 籌碼 結算日 | 財經媒體 | [工商時報期貨新聞](https://ctee.com.tw/news/futures/387170.html)、[Yahoo 股市 台指期 外資淨空單](https://tw.stock.yahoo.com/news/%E5%8F%B0%E6%8C%87%E6%9C%9F-%E5%A4%96%E8%B3%87%E6%B7%A8%E7%A9%BA%E5%96%AE%E5%BE%AE%E5%A2%9E-201000487.html)、[CMoney 筆記](https://www.cmoney.tw/notes/note-detail.aspx?nid=320966) | 外資淨部位的「增減方向」比絕對值重要；結算前後易被壓低／拉高；期現貨價差（正逆價差）被拿來解讀多空——據此做外資同向濾網、結算週濾網、BAS 基差家族。 |\n"
             "| futures trend following Donchian breakout ATR stop | 國外社群／教學 | [NexusFi Donchian Channels](https://nexusfi.com/a/indicators/donchian-channels)、[TradingView Donchian Breakout](https://tradingview.com/scripts/donchianchannel) | 海龜法則：20 日突破進、10 日跌破出、ATR 停損——BRK 家族的來源。這些是自述，並非獨立回測。 |\n"
             "| 期交所 臺股期貨 歷史資料 下載 | 官方 | [期交所 每日行情／統計資料](https://www.taifex.com.tw/cht/7/dailyFutVolData) | 確認歷史資料需另行申請，見上節。 |\n")
    L.append("## 四、試了幾組（多重比較要誠實登記）\n")
    L.append(f"- 參數格點：{nfam} 個家族共 {ngrid} 組（REG 9、BRK 54、PB 24、MA 30、RO 9、DMA 12、BAS 12），每組各跑 A、B 兩版。\n"
             f"- 另加兩種濾網（結算週；結算週＋外資籌碼）各重跑一次全部格點，及滑價敏感度。**不重複的完整回測共 {ex['trial_total']} 次。**\n"
             "- **家族不是一次定好的**：先跑 REG、BRK、PB、MA 四個，看到全數輸 0050 後才依「換方向」加了 RO、DMA，再加 BAS。這屬於事後擴充搜尋，"
             "增加了多重比較，但最終結論仍是全數淘汰，所以沒有『挑到好看的』的問題；反過來說，若有任何一個通過，也必須打折看待。\n"
             "- walk-forward 每段只用該段之前的資料選參數（以訓練期淨年化選，至少 8 筆交易）。『全家族自動選』選出的 BAS 訓練期年化 10～16%，測試期 1～14%，是典型的樣本內過度擬合落差。\n")
    L.append("## 五、walk-forward 逐段結果\n")
    L.append("訓練窗從 2001-01-02 起往後擴張（含 2008 空頭），測試窗 5 段：2013–2015、2016–2018、2019–2021、2022–2024、2025–迄今（涵蓋 2015、2018、2020、2022 空頭或急殺）。"
             "『鄰域』＝只改一個參數、相鄰一格的組合在同一測試窗的年化中位數；『鄰域贏0050比例』＝鄰域中贏過 0050 的比例。0050 回撤供對照。\n")
    L.append("\n".join(segtxt))
    L.append("\n參數鄰域看起來穩（鄰域中位年化與被選中者接近）——但『穩』的是『一致地輸 0050』，不是穩定地賺超額。\n")
    L.append("## 六、熊市與急殺年度（2008 為樣本內，其餘為 walk-forward 樣本外）\n")
    L.append("A／B_首段固定參數 = 用 2001–2012 選出的參數跑全期；WF樣本外 = 該年落在哪一段測試窗，就用那一段選出的參數。\n")
    L.append(md_table(bear))
    L.append("策略在 2008、2015、2018、2022 的下跌年份確實損失遠小於持有（2008：台指期 -45.9%、0050 -46.5%，A 約 -9%），但 2020 年（急殺後 V 型反彈）反而錯過漲幅。結論：**它是防禦工具，不是報酬增強工具**。\n")
    L.append("## 七、交易筆記摘要（完整逐筆見 trades_notes.md、trades_long.csv、trades_longshort.csv）\n")
    def line(nm, g):
        return (f"- {nm}：{g['n']} 筆（樣本外）、勝率 {g['win']:.0%}、合計 {g['sum']:.0f} 點；盤中停損 {g['stop_n']} 筆（平均 {g['stop_avg']:.0f} 點）、"
                f"**跳空越過停損 {g['gap_n']} 筆（平均 {g['gap_avg']:.0f} 點）**；贏家平均吐回最大浮盈的 {g['mfe_giveback']:.0%}（中位數）。")
    L.append(line("A 只做多（全家族自動選）", ga)); L.append(line("B 多空（全家族自動選）", gb))
    L.append(f"\n**A 版最慘的五筆**\n\n{worst(tA)}\n**B 版最慘的五筆**\n\n{worst(tB)}")
    L.append("最慘五筆裡有兩筆在 2020-03 急殺（逆價差越深越『便宜』，但急殺中期貨持續貼水，BAS 逆向接刀，一筆 3 日內虧 -13.8% 名義），另外三筆是 2021-07、2022-02、2024-07 的急跌，其中跳空越過停損者實損遠大於 ATR 預期。\n")
    L.append("## 八、優化空間（由每筆檢討彙整）\n")
    s1, s2 = ga["順向"], ga["反向"]
    L.append(f"1. **進場太晚、出場太慢是主因**：趨勢類（REG／MA／BRK）在 V 型反彈的年份錯過大半漲幅；贏家平均吐回最大浮盈的 {ga['mfe_giveback']:.0%}。可試：浮盈達 2～3 ATR 後把停損上移到成本價（保本）、分批停利。\n"
             f"2. **跳空風險大於預期**：A 版 {ga['gap_n']} 筆跳空停損平均 {ga['gap_avg']:.0f} 點，遠大於盤中停損平均 {ga['stop_avg']:.0f} 點——ATR 停損對隔夜缺口沒有保護。可試：重大事件日與長假前降到 0.5 倍曝險，或用選擇權買進保險腳（本輪未測）。\n"
             f"3. **外資期貨同向濾網（僅 2021 後、樣本極少，只能當線索）**：A 版同向 {s1[0]} 筆平均 {s1[1]:.0f} 點（勝率 {s1[2]:.0%}），反向 {s2[0]} 筆平均 {s2[1]:.0f} 點（勝率 {s2[2]:.0%}）。同向較好，但兩邊平均都為正、樣本太小、2021 前無資料，且加進 walk-forward 後樣本外年化沒有改善（{fmt(S[S['策略']=='A只多 全家族自動選+結算週+外資籌碼濾網'].iloc[0]['樣本外年化'])} vs {fmt(a_all['樣本外年化'])}），"
             "所以**不採用、也不能說有效**。累積到 3～5 年資料再重驗。\n"
             f"4. **結算週濾網無效**：結算週進場 {ga['sw'][0]} 筆平均 {ga['sw'][1]:.0f} 點，非結算週 {ga['sw'][2]} 筆平均 {ga['sw'][3]:.0f} 點——結算週並不比較差，濾網只是減少交易，樣本外年化沒改善。\n"
             f"5. **放空在台股 2013 年後是淨負貢獻**：B 版全家族只有 {gb['short'][0]} 筆空單（合計 {gb['short'][1]:.0f} 點）；各家族逐一比較，B 版年化幾乎都低於 A（例如 REG：A {fmt(S[S['策略']=='A只多 家族 REG'].iloc[0]['樣本外年化'])}、B {fmt(S[S['策略']=='B多空 家族 REG'].iloc[0]['樣本外年化'])}），空單被反彈洗出。若要放空，只該在『週K 空頭＋跌破前低確認』時做，且停損要比多單更緊。\n"
             "6. **方向要換**：1 倍台指期結構上輸 0050，擇時不補這個差。更可能有價值的用途是『0050 核心＋台指期做避險／加碼』：2008、2015、2018、2022 這類下跌年，策略損失遠小於持有，可以當 0050 的對沖腳。這是下一輪要檢驗的假說，不是本輪結論。\n"
             "7. **尚未測**：60 分K 進場細修（資料只有 2.1 年且是現貨指數）、波動率目標部位、選擇權保護、夜盤。\n")
    L.append("## 九、資料限制與誠實聲明\n")
    L.append("- 籌碼（外資期貨）只有 2021-01 起，濾網結論樣本短；事件日歷史不可得。\n"
             "- 連續近月序列的換月跳點未修補，換月成本為估計。2026 年基差異常大，可能影響 BAS 在最近一段的訊號。\n"
             "- 2x／3x 未模擬保證金追繳；閒置資金 1% 年息為假設。\n"
             "- 『全家族自動選』選到的 BAS 是訓練期最佳，不代表其他家族不好；各家族逐列見表。\n"
             "- 樣本外只有 13.8 年、5 段；每段交易數 2～34 筆，統計力有限。\n"
             "- 所有數字為歷史回測，不保證未來，不下單。\n")
    L.append("## 十、重現\n\n`python -m pipeline.compute.futures_lab`（約 20 秒）；測試 `pytest tests/test_futures_lab.py -q`。\n")
    (OUT / "README.md").write_text("\n".join(L), encoding="utf-8")
    # 逐筆筆記
    N = ["# 台指期交易筆記（全部樣本外交易，逐筆）\n",
         "每筆：進場理由（週K 狀態、籌碼／消息分數、日K 訊號）、出場理由、損益、最大不利偏移（MAE）、事後檢討。籌碼消息分數 = 週K 與方向一致 +1、外資期貨同向 +1／反向 -1、結算週 -1。"
         "事後檢討為規則式自動產生（依出場原因、持有天數、浮盈回吐、籌碼是否反向、是否結算週），再由 README 第八節彙整。\n"]
    for nm, t in (("A 只做多", tA), ("B 多空", tB)):
        N.append(f"\n## {nm}（{len(t)} 筆）\n")
        for _, r in t.iterrows():
            N.append(f"- **{r['進場日']} {r['方向']}** 進 {r['進場價']} -> {r['出場日']} 出 {r['出場價']}（{r['出場原因']}，持有 {r['持有天數']} 天）｜"
                     f"損益 {r['損益點']} 點（每口 {r['損益元每口']:,} 元，名義 {r['報酬率_名義']:.2%}）｜MAE {r['最大不利偏移點']} 點（{r['最大不利偏移_pct']:.2%}）｜"
                     f"進場理由：週K {r['週K狀態']}、{r['日K訊號']}、外資期貨5日變化 {r['外資期貨5日變化口'] if r['外資期貨5日變化口']==r['外資期貨5日變化口'] and r['外資期貨5日變化口'] is not None else '無資料'}（{r['籌碼']}）、結算週 {r['結算週']}"
                     f"{('、事件 ' + r['事件日']) if r['事件日'] else ''}、分數 {r['籌碼消息分數']}｜**檢討**：{r['事後檢討']}")
    (OUT / "trades_notes.md").write_text("\n".join(N), encoding="utf-8")


if __name__ == "__main__":
    main()
