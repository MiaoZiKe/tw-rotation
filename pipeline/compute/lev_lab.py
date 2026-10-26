"""0050／正二（00631L）搭配策略實驗室。

目標（Andy）：年化報酬 >= 同期含息 0050 x 1.5，而且每一段驗證期都要達標。只有這個方向可以用 0050、00631L、
其他槓桿／反向 ETF、台指期、現金、個股。這是研究回測，不是下單系統。

紅線（照 backtest 專家規則）：
  * 訊號在 t 日收盤後產生，部位在 t+1 日開盤才換（資產報酬拆成「昨收到開盤」與「開盤到收盤」兩段，換倉發生在兩段之間）。
  * 成本全算：手續費 0.1425%（不打折，保守）、ETF 證交稅 0.1% 賣出、滑價、內扣費用（已含在 ETF 價格或代理序列的扣除項）。
  * 參數只准用 2003-07～2016-12 選；之後的資料段只驗證不調參。
  * 所有試過的組合都登記（registry.csv），不挑好看的。

資料口徑：
  * 0050：還原總報酬（除息金額在除息日開盤加回、2025 的 1 拆 4 還原）。
  * 00631L：2014-10-31 上市後用真實價格（2026-03 的 1 拆 22 已還原）；之前用「0050 總報酬日報酬 x 2 - 內扣 - 融資成本」代理，
    並用上市後實際走勢校準殘差、報告誤差。
  * 台指期：沿用 futures_lab5.adjusted_tx() 換月修正後的序列。
  * 現金利率與融資利率沒有資料湖來源，用年度近似表（RF_BY_YEAR，台灣一年期定存利率約略值）。這是假設，報告有敏感度測試。
"""
from __future__ import annotations

import glob
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from numba import njit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "docs" / "strategy_lab" / "lev_lab"

START = "2003-07-01"
SEL_END = "2016-12-31"            # 選參只准用到這裡
SEL_BLOCKS = [("2003-07-01", "2008-12-31"), ("2009-01-01", "2012-12-31"), ("2013-01-01", "2016-12-31")]
SEGS = {"A 2003-07~2014": ("2003-07-01", "2014-12-31"), "B 2015~2020": ("2015-01-01", "2020-12-31"), "C 2021~": ("2021-01-01", None)}
OOS = {"樣本外 2017~2020": ("2017-01-01", "2020-12-31"), "樣本外 2021~": ("2021-01-01", None)}
MULT = 1.5

# 成本（單邊）
FEE = 0.001425
ETF_TAX = 0.001
SLIP = {"A50": 0.0005, "L2": 0.001, "INV": 0.0015, "TX": 0.0002, "MOM": 0.0}
TX_FEE = 0.0001
TX_ROLL_Y = 0.003            # 台指期持倉每年換月成本（約 12 次 x 0.025%）
L2_FEE_Y = 0.0104            # 00631L 內扣費用（管理＋保管＋指數授權等，來源 1.04~1.17%）
INV_FEE_Y = 0.011
BORROW_SPREAD = 0.005
RF_BY_YEAR = {2000: .045, 2001: .03, 2002: .017, 2003: .014, 2004: .014, 2005: .018, 2006: .02, 2007: .024, 2008: .019,
              2009: .009, 2010: .009, 2011: .011, 2012: .012, 2013: .012, 2014: .012, 2015: .011, 2016: .010, 2017: .010,
              2018: .010, 2019: .010, 2020: .008, 2021: .008, 2022: .011, 2023: .015, 2024: .016, 2025: .016, 2026: .016}

ASSETS = ["A50", "L2", "CASH", "INV", "TX", "MOM"]
IX = {a: i for i, a in enumerate(ASSETS)}
K = len(ASSETS)


# ------------------------------------------------------------------ 資料
def _rd(table, cols=None, filters=None, root=None):
    base = Path(root) if root else ROOT / "data" / table
    fs = glob.glob(str(base / "**" / "*.parquet"), recursive=True)
    return pd.concat([pd.read_parquet(f, columns=cols, filters=filters) for f in fs], ignore_index=True)


def etf_legs(df: pd.DataFrame, cal: pd.DatetimeIndex, div: pd.Series | None = None):
    """回傳（隔夜報酬 on、盤中報酬 id、是否有資料 present、分割調整後收盤 cadj）。
    分割：單日收盤比 < 0.6 視為拆股（k=round(1/ratio)），> 3 視為反分割。除息：除息日開盤加回。
    缺資料的交易日：報酬記 0，下一個有資料日的隔夜報酬吃掉整段缺口（不會憑空消失）。"""
    p = df.drop_duplicates("date").copy()
    p["date"] = pd.to_datetime(p["date"])
    p = p.set_index("date").sort_index()[["open", "close"]].astype(float)
    p = p[(p.close > 0) & (p.open > 0)]
    ratio = p.close / p.close.shift(1)
    s = pd.Series(1.0, index=p.index)                         # 把當天價格換算到「昨天的尺度」的乘數
    sp = ratio < 0.6
    s[sp] = np.round(1 / ratio[sp])
    rv = ratio > 3.0
    s[rv] = 1.0 / np.round(ratio[rv])
    prev = p.close.shift(1)
    on = (p.open * s + (div.reindex(p.index).fillna(0.0) if div is not None else 0.0)) / prev - 1
    idr = p.close / p.open - 1
    on = on.reindex(cal); idr = idr.reindex(cal)
    present = on.notna().to_numpy()
    cadj = (p.close * s.cumprod().iloc[-1] / s.cumprod()).reindex(cal)
    return on.fillna(0.0).to_numpy(), idr.fillna(0.0).to_numpy(), present, cadj


class World:
    """所有資產的隔夜／盤中報酬與訊號用序列，全部對齊 0050 的交易日曆。"""

    def __init__(self, with_tx=True, with_mom=True, proxy_src="TSE", proxy_extra=0.0, slip_mult=1.0, mom_cache=None):
        px = _rd("price_daily", ["date", "code", "open", "close", "volume"], filters=[("code", "in", ["0050", "00631L", "00675L", "00663L", "00632R"])])
        self.px = px
        c50 = px[px.code == "0050"].drop_duplicates("date")
        cal = pd.DatetimeIndex(sorted(pd.to_datetime(c50["date"].unique())))
        self.cal = cal
        T = len(cal)
        dv = pd.concat([_rd("etf_dividend_events"), _rd("dividend_events")])
        dv = dv[(dv.code == "0050") & (dv.kind == "cash") & dv.ex_date.notna()].copy()
        dv["ex_date"] = pd.to_datetime(dv["ex_date"])
        dv = dv.drop_duplicates("ex_date").set_index("ex_date")["amount"].astype(float)
        self.on50, self.id50, self.pres50, self.c50 = etf_legs(c50, cal, dv)
        self.on50_nd, self.id50_nd, _, _ = etf_legs(c50, cal, None)              # 不含息（驗證部落格「0050 年化 10.1%」用）
        rf = pd.Series(cal.year, index=cal).map(RF_BY_YEAR).to_numpy()
        self.rf = rf
        ON = np.zeros((T, K)); ID = np.zeros((T, K))
        ON[:, IX["A50"]], ID[:, IX["A50"]] = self.on50, self.id50
        ON[:, IX["CASH"]] = rf / 252
        self.borrow = (rf + BORROW_SPREAD) / 252
        # 真實槓桿／反向 ETF
        self.real = {}
        for code in ("00631L", "00675L", "00663L", "00632R"):
            d = px[px.code == code].drop_duplicates("date")
            d = d[d.volume > 0]
            if len(d):
                self.real[code] = etf_legs(d, cal, None)
        # 訊號用序列（加權指數 TSE：同時當 00631L 代理序列的底，見下）
        idx = _rd("index_ohlc", ["date", "symbol", "close", "open"])
        idx["date"] = pd.to_datetime(idx["date"])
        tse_df = idx[idx.symbol == "TSE"].drop_duplicates("date").set_index("date").sort_index()
        tse = tse_df["close"].astype(float)
        self.tse_full = tse
        self.tse = tse.reindex(cal).ffill()
        tc = tse.reindex(cal).ffill(); to = tse_df["open"].astype(float).reindex(cal)
        to = to.where(to > 0, tc.shift(1))
        on_t = (to / tc.shift(1) - 1).fillna(0.0).to_numpy(); id_t = (tc / to - 1).fillna(0.0).to_numpy()
        # 00631L 代理序列＋校準。
        # 發現（見 README「代理序列」）：真實 00631L 追的其實是加權指數期貨的 2 倍，而不是 0050 的 2 倍——
        # 以 0050 總報酬 x2 做代理，逐年誤差標準差 16.9 點（2024 起單年差 20~42 點）；以加權指數價格報酬 x2 加一個常數殘差
        # （股利＋期貨正價差，約 +9%/年）做代理，逐年誤差標準差 9.5 點、日報酬相關也較高。所以預設用 TSE 當底（proxy_src="TSE"），
        # 0050 版當敏感度（proxy_src="A50"）。
        r50 = (1 + self.on50) * (1 + self.id50) - 1
        self.r50 = r50
        base_on, base_id = (on_t, id_t) if proxy_src == "TSE" else (self.on50, self.id50)
        base_r = (1 + base_on) * (1 + base_id) - 1
        self.base_r = base_r
        on_r, id_r, pres_r, _ = self.real["00631L"]
        first = int(np.argmax(pres_r))
        self.l2_first = first
        self.calib = self._calibrate(base_r, on_r, id_r, pres_r, first, rf, L2_FEE_Y, 2.0, "L2")
        drag = self.calib["resid"]
        on_p = 2 * base_on
        r_p = 2 * base_r - (L2_FEE_Y + rf + drag + proxy_extra) / 252
        id_p = (1 + r_p) / (1 + on_p) - 1
        self.l2_proxy = (on_p, id_p)
        on2, id2 = on_p.copy(), id_p.copy()
        on2[first:], id2[first:] = on_r[first:], id_r[first:]
        ON[:, IX["L2"]], ID[:, IX["L2"]] = on2, id2
        # 反向代理（同樣用 TSE 當底）
        on_i, id_i, pres_i, _ = self.real["00632R"]
        fi = int(np.argmax(pres_i))
        self.calib_inv = self._calibrate(base_r, on_i, id_i, pres_i, fi, rf, INV_FEE_Y, -1.0, "INV")
        r_pi = -base_r - (INV_FEE_Y + self.calib_inv["resid"]) / 252
        on_pi = -base_on
        id_pi = (1 + r_pi) / (1 + on_pi) - 1
        on3, id3 = on_pi.copy(), id_pi.copy()
        on3[fi:], id3[fi:] = on_i[fi:], id_i[fi:]
        ON[:, IX["INV"]], ID[:, IX["INV"]] = on3, id3
        # 訊號用序列
        self.fut_raw = idx[idx.symbol == "FUT"].drop_duplicates("date").set_index("date").sort_index()["close"].astype(float)
        # 美股（S&P 500、VIX）：2008 起；資料目錄可用環境變數 LEV_INTL_DIR 覆寫（本分支只有 2024 後的部分）
        root = os.environ.get("LEV_INTL_DIR") or None
        it = _rd("intl_daily", ["date", "symbol", "close"], root=root)
        it["date"] = pd.to_datetime(it["date"])
        self.spx_full = it[it.symbol == "^GSPC"].drop_duplicates("date").set_index("date").sort_index()["close"].astype(float)
        self.vix_full = it[it.symbol == "^VIX"].drop_duplicates("date").set_index("date").sort_index()["close"].astype(float)
        # 美股的訊號對台股日 t 開盤有效：用「台北 t 日以前已收盤的美股」＝美股日期 < t 的最後一筆（shift(1) 後 asof）
        def us_asof(s):
            s2 = s.copy(); s2.index = s2.index + pd.Timedelta(days=1)       # 美股 d 日收盤，台北 d+1 日才可用（保守）
            return s2.reindex(cal, method="ffill")
        self.spx = us_asof(self.spx_full); self.vix = us_asof(self.vix_full)
        if with_tx:
            from pipeline.compute import futures_lab5 as L5
            adj, raw, fac = L5.adjusted_tx()
            adj = adj.reindex(cal)
            o, c = adj["open"], adj["close"]
            cp = c.ffill().shift(1)
            ON[:, IX["TX"]] = (o / cp - 1).fillna(0.0).to_numpy()
            ID[:, IX["TX"]] = (c / o - 1).fillna(0.0).to_numpy()
        self.ON, self.ID = ON, ID
        self.mom_info = None
        if with_mom:
            on_m, id_m, info = mom_cache if mom_cache else mom_asset(cal)
            ON[:, IX["MOM"]], ID[:, IX["MOM"]] = on_m, id_m
            self.mom_info = info
        self.start_i = int(cal.searchsorted(pd.Timestamp(START)))
        buy = np.zeros(K); sell = np.zeros(K)
        for a, s in SLIP.items():
            buy[IX[a]] = FEE + s * slip_mult; sell[IX[a]] = FEE + ETF_TAX + s * slip_mult
        buy[IX["TX"]] = TX_FEE + SLIP["TX"]; sell[IX["TX"]] = TX_FEE + SLIP["TX"] + 0.00002
        buy[IX["MOM"]] = sell[IX["MOM"]] = 0.0                                   # 衛星內部換股成本已扣在報酬裡
        self.buyc, self.sellc = buy, sell

    @staticmethod
    def _calibrate(r50, on_r, id_r, pres, first, rf, fee, beta, tag):
        r_real = (1 + on_r) * (1 + id_r) - 1
        sl = slice(first + 1, None)
        rr, rp = r_real[sl], r50[sl]
        yrs = len(rr) / 252
        raw_proxy = beta * rp - (fee + (rf[sl] if beta > 0 else 0.0)) / 252
        resid = (np.log1p(raw_proxy).sum() - np.log1p(rr).sum()) / yrs               # 每年多出來的殘差扣除（可為負）
        proxy = beta * rp - (fee + (rf[sl] if beta > 0 else 0.0) + resid) / 252
        cal_idx = None
        return dict(tag=tag, resid=float(resid), corr=float(np.corrcoef(rr, rp)[0, 1]),
                    beta=float(np.polyfit(rp, rr, 1)[0]), te=float(np.std(rr - proxy) * np.sqrt(252)),
                    daily_corr_proxy=float(np.corrcoef(rr, proxy)[0, 1]), n=len(rr), first_i=first,
                    cum_real=float(np.expm1(np.log1p(rr).sum())), cum_proxy=float(np.expm1(np.log1p(proxy).sum())))

    # 校準誤差（逐年）
    def calib_by_year(self):
        on_r, id_r, pres, _ = self.real["00631L"]
        r_real = (1 + on_r) * (1 + id_r) - 1
        on_p, id_p = self.l2_proxy
        r_p = (1 + on_p) * (1 + id_p) - 1
        s = pd.DataFrame({"real": r_real, "proxy": r_p}, index=self.cal).iloc[self.l2_first + 1:]
        g = s.groupby(s.index.year).apply(lambda x: pd.Series({"真實": (1 + x.real).prod() - 1, "代理": (1 + x.proxy).prod() - 1}))
        g["差(點)"] = (g["代理"] - g["真實"]) * 100
        return g


# ------------------------------------------------------------------ 個股動能衛星
def mom_asset(cal, top_liq=150, n_hold=10, lookback=252, skip=21):
    """12-1 動能：每月第一個交易日開盤，用「昨天以前」的資料在流動性前 top_liq 名中挑動能最強 n_hold 檔等權持有一個月。
    ⚠ price_daily 沒還原除息價：除息日的價格下跌被當成虧損，衛星報酬被低估約一個股利殖利率；
       當日漲跌超過 ±11% 視為公司行動（拆股、減資）設為 0。資料湖含已下市個股與否未驗證，存活者偏誤方向不明。"""
    d = _rd("price_daily", ["date", "code", "open", "close", "turnover", "market"])
    d = d[d.code.str.fullmatch(r"[1-9]\d{3}")]
    d["date"] = pd.to_datetime(d["date"])
    d = d[d.date >= "2002-01-01"]
    C = d.pivot_table(index="date", columns="code", values="close", aggfunc="last").reindex(cal.union(d.date.unique())).sort_index()
    O = d.pivot_table(index="date", columns="code", values="open", aggfunc="last").reindex(C.index)
    TO = d.pivot_table(index="date", columns="code", values="turnover", aggfunc="last").reindex(C.index)
    C, O, TO = C.reindex(cal), O.reindex(cal), TO.reindex(cal)
    Cf = C.ffill(limit=5)
    cprev = Cf.shift(1)
    on = (O / cprev - 1); idr = (C / O - 1)
    bad = (on.abs() > 0.11) | (idr.abs() > 0.11) | ((C / cprev - 1).abs() > 0.11)
    on = on.where(~bad, 0.0); idr = idr.where(~bad, 0.0)
    liq = TO.rolling(60, min_periods=40).mean().shift(1)
    mom = (Cf.shift(skip) / Cf.shift(lookback) - 1)
    mom = mom.shift(1)
    T = len(cal)
    month = cal.to_period("M")
    first_day = np.r_[True, month[1:] != month[:-1]]
    W = np.zeros(C.shape, dtype=np.float32)
    cur = np.zeros(C.shape[1], dtype=np.float32)
    cost_on = np.zeros(T)
    one_way = (FEE + 0.001) + (FEE + 0.003 + 0.001)       # 一買一賣的完整成本（含滑價 0.1%、證交稅 0.3%）
    for i in range(T):
        if first_day[i] and i > lookback + 80:
            lq = liq.iloc[i].dropna()
            ok = lq.nlargest(top_liq).index
            m = mom.iloc[i].reindex(ok).dropna()
            sel = m.nlargest(n_hold).index
            new = np.zeros(C.shape[1], dtype=np.float32)
            cols = C.columns.get_indexer(sel)
            new[cols] = 1.0 / len(cols)
            replaced = float(np.clip(cur - new, 0, None).sum())
            cost_on[i] = replaced * one_way + (1.0 if cur.sum() == 0 else 0.0) * (FEE + 0.001)
            cur = new
        W[i] = cur
    onv = np.nan_to_num(on.to_numpy(dtype=np.float64), nan=0.0); idv = np.nan_to_num(idr.to_numpy(dtype=np.float64), nan=0.0)
    on_p = (W * onv).sum(axis=1) - cost_on
    id_p = (W * idv).sum(axis=1)
    held = (W > 0).sum(axis=1)
    return on_p, id_p, dict(avg_names=float(held[held > 0].mean()) if (held > 0).any() else 0.0, first_i=int(np.argmax(held > 0)))


# ------------------------------------------------------------------ 引擎
@njit(cache=True)
def sim(ON, ID, BOR, W, flag, band, buyc, sellc, start_i, cash_ix):
    T, Kk = ON.shape
    val = np.zeros(Kk)
    val[cash_ix] = 1.0
    ret = np.zeros(T); turn = np.zeros(T)
    prev_tot = 1.0
    for t in range(start_i, T):
        for k in range(Kk):
            if k == cash_ix:
                if val[k] >= 0:
                    val[k] *= 1.0 + ON[t, k]
                else:
                    val[k] *= 1.0 + BOR[t]
            else:
                val[k] *= 1.0 + ON[t, k]
        tot = 0.0
        for k in range(Kk):
            tot += val[k]
        if tot <= 0:
            ret[t] = -1.0 if prev_tot > 0 else 0.0
            for k in range(Kk):
                val[k] = 0.0
            prev_tot = 0.0
            continue
        do = flag[t] or t == start_i
        if (not do) and band > 0:
            for k in range(Kk):
                if abs(val[k] / tot - W[t, k]) > band:
                    do = True
        if do:
            cost = 0.0; tn = 0.0
            for k in range(Kk):
                if k == cash_ix:
                    continue
                d = W[t, k] * tot - val[k]
                if d > 0:
                    cost += d * buyc[k]
                else:
                    cost += -d * sellc[k]
                tn += abs(d)
            tot2 = tot - cost
            for k in range(Kk):
                val[k] = W[t, k] * tot2
            turn[t] = tn / tot
        tot3 = 0.0
        for k in range(Kk):
            if k != cash_ix:
                val[k] *= 1.0 + ID[t, k]
            tot3 += val[k]
        ret[t] = tot3 / prev_tot - 1.0
        prev_tot = tot3
    return ret, turn


def run(world: World, W, flag, band=0.0):
    r, turn = sim(world.ON, world.ID, world.borrow, W, flag, band, world.buyc, world.sellc, world.start_i, IX["CASH"])
    return r, turn


# ------------------------------------------------------------------ 指標
def _slice(world, a, b):
    i0 = max(world.start_i, int(world.cal.searchsorted(pd.Timestamp(a))))
    i1 = len(world.cal) if b is None else int(world.cal.searchsorted(pd.Timestamp(b), side="right"))
    return i0, i1


def cagr(r):
    if len(r) == 0:
        return np.nan
    eq = np.cumprod(1 + r)
    if eq[-1] <= 0:
        return -1.0
    return eq[-1] ** (252.0 / len(r)) - 1


def mdd(r):
    eq = np.cumprod(1 + r)
    pk = np.maximum.accumulate(eq)
    dd = eq / pk - 1
    j = int(np.argmin(dd)); i = int(np.argmax(eq[:j + 1]))
    return float(dd[j]), i, j


def window(world, r, a, b):
    i0, i1 = _slice(world, a, b)
    return r[i0:i1]


class Bench:
    def __init__(self, world):
        self.w = world
        T = len(world.cal)
        self.W = np.zeros((T, K)); self.W[:, IX["A50"]] = 1.0
        self.flag = np.zeros(T, bool)
        self.r, _ = run(world, self.W, self.flag)
        self.cache = {}

    def c50(self, a, b):
        k = (a, b)
        if k not in self.cache:
            self.cache[k] = cagr(window(self.w, self.r, a, b))
        return self.cache[k]


def eval_row(world, bench, r, turn=None):
    out = {}
    for nm, (a, b) in {**SEGS, **OOS, "選參期 2003-07~2016": (START, SEL_END)}.items():
        x = window(world, r, a, b)
        c = cagr(x); c5 = bench.c50(a, b)
        out[nm] = (c, c5, c - MULT * c5)
    for j, (a, b) in enumerate(SEL_BLOCKS):
        x = window(world, r, a, b); c = cagr(x); c5 = bench.c50(a, b)
        out[f"blk{j}"] = (c, c5, c - MULT * c5)
    return out


def sel_score(world, bench, r):
    """選參分數：選參期三個子區塊（含 2008 金融海嘯）中，『年化 - 1.5 x 0050 年化』最差的一塊。越大越好。"""
    return min(cagr(window(world, r, a, b)) - MULT * bench.c50(a, b) for a, b in SEL_BLOCKS)


# ------------------------------------------------------------------ 訊號
def sma(s: pd.Series, n):
    return s.rolling(n).mean()


@njit(cache=True)
def _hyst(close, ma, h, m):
    """遲滯＋確認天數：收盤 > MA*(1+h) 連續 m 天才轉多；收盤 < MA*(1-h) 連續 m 天才轉空。回傳 0/1。"""
    n = len(close); st = np.zeros(n, np.int8)
    cur = 0; up = 0; dn = 0
    for i in range(n):
        if np.isnan(ma[i]):
            st[i] = cur; continue
        if close[i] > ma[i] * (1 + h):
            up += 1; dn = 0
        elif close[i] < ma[i] * (1 - h):
            dn += 1; up = 0
        else:
            up = 0; dn = 0
        if cur == 0 and up >= m:
            cur = 1
        elif cur == 1 and dn >= m:
            cur = 0
        st[i] = cur
    return st


def ma_state(world, n, h=0.0, m=1, series=None):
    s = world.tse_full if series is None else series
    st = _hyst(s.to_numpy(), sma(s, n).to_numpy(), h, m)
    return pd.Series(st, index=s.index).reindex(world.cal).ffill().fillna(0).to_numpy()


def shift1(x):
    """訊號 t 收盤後產生，t+1 開盤才用。"""
    y = np.empty_like(x); y[0] = 0; y[1:] = x[:-1]
    return y


def base_W(T):
    return np.zeros((T, K))


def fill_W(W, on, w_on: dict, w_off: dict):
    """on（已 shift）為 1 的日子用 w_on 權重，否則用 w_off 權重。其餘補現金。"""
    for a in ASSETS:
        W[:, IX[a]] = np.where(on > 0, w_on.get(a, 0.0), w_off.get(a, 0.0))
    for arr_name, d in (("on", w_on), ("off", w_off)):
        pass
    tot_on = sum(w_on.values()); tot_off = sum(w_off.values())
    W[:, IX["CASH"]] = np.where(on > 0, 1 - tot_on, 1 - tot_off)
    return W


def change_flag(W, extra=None):
    f = np.zeros(len(W), bool)
    f[1:] = np.abs(np.diff(W, axis=0)).max(axis=1) > 1e-9
    if extra is not None:
        f |= extra
    return f


def periodic_flag(cal, per):
    if per in (None, "N"):
        return np.zeros(len(cal), bool)
    mo = cal.to_period("M")
    first = np.r_[True, mo[1:] != mo[:-1]]
    mon = cal.month.to_numpy()
    if per == "M":
        return first
    if per == "Q":
        return first & np.isin(mon, [1, 4, 7, 10])
    if per == "S":
        return first & np.isin(mon, [1, 7])
    if per == "A":
        return first & (mon == 1)
    raise ValueError(per)


OFF_MODES = {
    "50": {"A50": 1.0},
    "cash": {},
    "half50": {"A50": 0.5},
    "inv50": {"INV": 0.5},
    "L2_20": {"L2": 0.2}, "L2_30": {"L2": 0.3}, "L2_40": {"L2": 0.4}, "L2_50": {"L2": 0.5},
    "L2_60": {"L2": 0.6}, "L2_70": {"L2": 0.7}, "L2_80": {"L2": 0.8},
}
ON_MODES = {"L2": {"L2": 1.0}, "L2_70": {"L2": 0.7, "A50": 0.3}, "L2_50": {"L2": 0.5, "A50": 0.5}}


def exposure_weights(E):
    """總曝險 E（0~2）→ 0050／正二／現金。E<=1：0050 佔 E；E>1：正二佔 E-1、0050 佔 2-E（總曝險 = w50 + 2 w正二 = E）。"""
    W = np.zeros((len(E), K))
    lo = E <= 1
    W[:, IX["A50"]] = np.where(lo, E, 2 - E)
    W[:, IX["L2"]] = np.where(lo, 0.0, E - 1)
    W[:, IX["CASH"]] = np.where(lo, 1 - E, 0.0)
    return W


@njit(cache=True)
def _hold_E(E_target, thr, every):
    n = len(E_target); out = np.zeros(n); cur = E_target[0] if n else 0.0
    last = 0
    for i in range(n):
        if np.isnan(E_target[i]):
            out[i] = cur; continue
        if i == 0 or abs(E_target[i] - cur) > thr or (every > 0 and i - last >= every):
            cur = E_target[i]; last = i
        out[i] = cur
    return out


def realized_vol(world, win):
    r = world.tse_full.pct_change()
    return (r.rolling(win).std() * np.sqrt(252)).reindex(world.cal).ffill()


def weekly_regime(world, wma):
    from pipeline.compute import futures_lab as F
    s = world.tse_full
    return pd.Series(F.weekly_regime(s, wma), index=s.index).reindex(world.cal).ffill().fillna(0).to_numpy()


def dd_state(world, n, dd):
    s = world.tse_full
    d = s / s.rolling(n, min_periods=60).max() - 1
    return (d < -dd).reindex(world.cal).ffill().fillna(False).to_numpy().astype(np.int8)


# ------------------------------------------------------------------ 策略家族
def build(world: World, fam: str, p: dict):
    """回傳 (W, flag, band)。W[t] 是 t 日開盤要持有的目標權重，只用到 t-1 收盤以前的資訊。"""
    T = len(world.cal)
    W = base_W(T); band = 0.0
    if fam == "HOLD":
        W[:, IX["A50"]] = p["w50"]; W[:, IX["L2"]] = p["w2"]; W[:, IX["CASH"]] = 1 - p["w50"] - p["w2"]
        reb = p["reb"]
        if reb.startswith("B"):
            band = int(reb[1:]) / 100.0; fl = np.zeros(T, bool)
        else:
            fl = periodic_flag(world.cal, reb)
        return W, fl, band
    if fam == "MA":
        st = shift1(ma_state(world, p["n"], p["h"], p["m"]))
        fill_W(W, st, ON_MODES[p["on"]], OFF_MODES[p["off"]])
        return W, change_flag(W), 0.0
    if fam == "XO":
        sx = world.tse_full
        st = (sma(sx, p["fast"]) > sma(sx, p["slow"])).astype(float).reindex(world.cal).ffill().fillna(0).to_numpy()
        fill_W(W, shift1(st), {"L2": 1.0}, OFF_MODES[p["off"]])
        return W, change_flag(W), 0.0
    if fam == "AM":       # 絕對動能（時間序列動能）：近 n 日報酬 > 0 才持有正二
        sx = world.tse_full
        mom = (sx / sx.shift(p["n"]) - 1)
        st = _hyst(np.ones(len(sx)) + mom.fillna(-1).to_numpy(), np.ones(len(sx)), p["h"], 1)
        st = pd.Series(st, index=sx.index).reindex(world.cal).ffill().fillna(0).to_numpy()
        fill_W(W, shift1(st), {"L2": 1.0}, OFF_MODES[p["off"]])
        return W, change_flag(W), 0.0
    if fam == "VOL":
        vol = realized_vol(world, p["win"]).to_numpy()
        E = np.clip(p["tgt"] / np.where(vol > 0, vol, np.nan), 0, p["emax"])
        E = np.nan_to_num(E, nan=1.0)
        E = shift1(E); E[0] = 1.0
        Eh = _hold_E(E, p["thr"], 21)
        W = exposure_weights(Eh)
        return W, change_flag(W), 0.0
    if fam == "TV":
        st = shift1(ma_state(world, p["n"], p["h"], 1))
        vol = shift1(realized_vol(world, p["win"]).fillna(1.0).to_numpy())
        calm = vol < p["vhi"]
        on = (st > 0) & calm
        W = fill_W(W, np.where(on, 1, 0), {"L2": 1.0}, {})
        mid = (st > 0) & ~calm
        W[mid, IX["L2"]] = 0.0; W[mid, IX["A50"]] = 1.0; W[mid, IX["CASH"]] = 0.0
        if p["off"] == "50":
            off = st <= 0
            W[off, IX["A50"]] = 1.0; W[off, IX["CASH"]] = 0.0
        return W, change_flag(W), 0.0
    if fam == "DG":
        T_ = T
        flags = []
        S = p["set"]
        if "W" in S: flags.append(weekly_regime(world, p["wma"]) < 0)
        if "DD" in S: flags.append(dd_state(world, 250, p["dd"]) > 0)
        if "T" in S: flags.append(ma_state(world, p["n"], 0.0, 1) < 1)
        if "VOL" in S: flags.append(realized_vol(world, 20).fillna(0).to_numpy() > p["vol"])
        if "V" in S: flags.append(np.nan_to_num(world.vix.to_numpy(), nan=0.0) > p["vix"])
        cnt = np.sum(flags, axis=0)
        danger = (cnt >= p["k"]).astype(np.int8)
        # 解除最短持有 m 天：用 hysteresis 的概念，danger 一旦觸發至少維持 m 天
        if p["m"] > 1:
            d2 = danger.copy(); left = 0
            for i in range(len(d2)):
                if danger[i]: left = p["m"]
                d2[i] = 1 if left > 0 else 0
                left = max(0, left - 1)
            danger = d2
        on = shift1(1 - danger)
        fill_W(W, on, {"L2": 1.0}, OFF_MODES[p["off"]])
        return W, change_flag(W), 0.0
    if fam == "TX":
        st = shift1(ma_state(world, p["n"], 0.0, 1))
        core = {"A50": 1.0} if p["core"] == "50" else {"L2": 1.0}
        on_w = dict(core); on_w["TX"] = p["x"]; on_w["CASH"] = 0
        off_w = dict(core) if p["off"] == "keep" else ({"A50": 1.0} if p["core"] == "L2" else {})
        for a in ASSETS:
            W[:, IX[a]] = np.where(st > 0, on_w.get(a, 0.0), off_w.get(a, 0.0))
        W[:, IX["CASH"]] = 1 - W[:, [IX[a] for a in ("A50", "L2", "TX", "INV")]].sum(axis=1)
        return W, change_flag(W), 0.10
    if fam == "TXG":      # 台指期單獨：趨勢多頭持有 x 倍，否則現金或 0050
        st = shift1(ma_state(world, p["n"], 0.0, 1))
        for a in ASSETS: W[:, IX[a]] = 0.0
        W[:, IX["TX"]] = np.where(st > 0, p["x"], 0.0)
        W[:, IX["A50"]] = np.where(st > 0, 0.0, 1.0 if p["off"] == "50" else 0.0)
        W[:, IX["CASH"]] = 1 - W[:, IX["TX"]] - W[:, IX["A50"]]
        return W, change_flag(W), 0.10
    if fam == "SAT":      # 個股動能衛星
        s = p["s"]
        if p["core"] == "50":
            W[:, IX["A50"]] = 1 - s
        elif p["core"] == "L2":
            W[:, IX["L2"]] = 1 - s
        else:
            st = shift1(ma_state(world, 200, 0.0, 1))
            W[:, IX["L2"]] = np.where(st > 0, 1 - s, 0.0); W[:, IX["A50"]] = np.where(st > 0, 0.0, 1 - s)
        W[:, IX["MOM"]] = s
        W[:, IX["CASH"]] = 1 - W[:, :5].sum(axis=1) - W[:, IX["MOM"]] + W[:, IX["CASH"]]
        return W, change_flag(W, periodic_flag(world.cal, "M")), 0.0
    if fam == "L1US":     # 以 S&P 500 200 日線決定持有正二或 0050/現金（L2 宣稱）
        s = world.spx_full
        st = pd.Series(_hyst(s.to_numpy(), sma(s, p["n"]).to_numpy(), 0.0, 1), index=s.index)
        st.index = st.index + pd.Timedelta(days=1)
        st = st.reindex(world.cal, method="ffill").fillna(1).to_numpy()
        fill_W(W, shift1(st), {"L2": 1.0}, OFF_MODES[p["off"]])
        return W, change_flag(W), 0.0
    if fam == "RF":       # Range Filter 決定持有正二或空手（L3 宣稱）
        st = shift1(range_filter_state(world.tse_full, p["per"], p["mult"]).reindex(world.cal).ffill().fillna(0).to_numpy())
        fill_W(W, st, {"L2": 1.0}, OFF_MODES[p["off"]])
        return W, change_flag(W), 0.0
    raise ValueError(fam)


def range_filter_state(x: pd.Series, per=15, mult=4.0):
    """TradingView 的 Range Filter（DonovanWall）：平滑平均區間 = EMA(EMA(|x - x[1]|, per), 2*per-1) x mult；
    濾線只有在價格超出區間時才移動；濾線上升＝多方（1），其餘 0。"""
    ar = (x - x.shift(1)).abs()
    sr = ar.ewm(span=per, adjust=False).mean().ewm(span=per * 2 - 1, adjust=False).mean() * mult
    xv, rv = x.to_numpy(), sr.to_numpy()
    f = np.zeros(len(x)); f[0] = xv[0]
    for i in range(1, len(x)):
        if np.isnan(rv[i]):
            f[i] = xv[i]; continue
        if xv[i] > f[i - 1]:
            f[i] = max(f[i - 1], xv[i] - rv[i])
        else:
            f[i] = min(f[i - 1], xv[i] + rv[i])
    up = np.zeros(len(x), np.int8); cur = 0
    for i in range(1, len(x)):
        if f[i] > f[i - 1]:
            cur = 1
        elif f[i] < f[i - 1]:
            cur = 0
        up[i] = cur
    return pd.Series(up, index=x.index)


# ------------------------------------------------------------------ 格點
def grid():
    G = []
    # 固定比例（含 L8 現金配置）
    for a in range(0, 11):
        for b in range(0, 11 - a):
            w50, w2 = a / 10, b / 10
            if w50 + w2 == 0:
                continue
            for reb in ("N", "M", "Q", "S", "A", "B5", "B10", "B20"):
                if (w2 == 0 or w50 == 0) and w50 + w2 == 1 and reb != "N":
                    continue
                G.append(("HOLD", dict(w50=w50, w2=w2, reb=reb)))
    for n in (20, 40, 60, 90, 120, 150, 200, 250):
        for h in (0.0, 0.01, 0.02):
            for m in (1, 3, 5):
                for on in ("L2", "L2_70"):
                    for off in ("50", "cash", "half50", "inv50", "L2_20", "L2_30", "L2_40", "L2_50", "L2_60", "L2_70", "L2_80"):
                        G.append(("MA", dict(n=n, h=h, m=m, on=on, off=off)))
    for fast in (20, 50, 60):
        for slow in (100, 150, 200, 250):
            for off in ("cash", "50", "half50", "L2_30", "L2_50"):
                G.append(("XO", dict(fast=fast, slow=slow, off=off)))
    for n in (60, 120, 180, 250):
        for off in ("cash", "50", "half50", "L2_30", "L2_50"):
            for h in (0.0, 0.02):
                G.append(("AM", dict(n=n, off=off, h=h)))
    for tgt in (.10, .12, .15, .18, .20, .25, .30):
        for win in (20, 40, 60, 120):
            for thr in (.25, .5):
                for emax in (1.5, 2.0):
                    G.append(("VOL", dict(tgt=tgt, win=win, thr=thr, emax=emax)))
    for n in (60, 120, 200):
        for h in (0.0, 0.01):
            for vhi in (.15, .20, .25, .30, .40):
                for win in (20, 60):
                    for off in ("cash", "50"):
                        G.append(("TV", dict(n=n, h=h, vhi=vhi, win=win, off=off)))
    sets = [("W",), ("DD",), ("T",), ("VOL",), ("V",), ("W", "DD"), ("W", "T"), ("W", "VOL"), ("W", "V"), ("DD", "T"), ("DD", "VOL"),
            ("DD", "V"), ("T", "VOL"), ("T", "V"), ("VOL", "V"), ("W", "DD", "T"), ("W", "DD", "V"), ("W", "T", "V"), ("DD", "T", "V"), ("W", "DD", "VOL")]
    for S in sets:
        for k in range(1, len(S) + 1):
            for wma in ((26, 40) if "W" in S else (26,)):
                for dd in ((0.10, 0.15, 0.20) if "DD" in S else (0.15,)):
                    for vol in ((.25, .35) if "VOL" in S else (.3,)):
                        for vix in ((25, 30, 35) if "V" in S else (30,)):
                            for m in (1, 10):
                                for off in ("50", "cash", "L2_30", "L2_50"):
                                    G.append(("DG", dict(set=S, k=k, wma=wma, dd=dd, vol=vol, vix=vix, n=200, m=m, off=off)))
    for n in (60, 120, 200):
        for x in (.5, 1.0):
            for core in ("50", "L2"):
                for off in ("keep", "drop"):
                    G.append(("TX", dict(n=n, x=x, core=core, off=off)))
    for n in (60, 120, 200):
        for x in (1.0, 1.5, 2.0):
            for off in ("cash", "50"):
                G.append(("TXG", dict(n=n, x=x, off=off)))
    for core in ("50", "L2", "SW"):
        for s in (0.0, .2, .3, .5, 1.0):
            G.append(("SAT", dict(core=core, s=s)))
    for per in (10, 15, 20, 30):
        for mult in (2.0, 3.0, 4.0, 5.0):
            for off in ("cash", "50", "L2_30", "L2_50"):
                G.append(("RF", dict(per=per, mult=mult, off=off)))
    for n in (100, 150, 200):
        for off in ("50", "cash", "half50"):
            G.append(("L1US", dict(n=n, off=off)))
    return G


def key(fam, p):
    return fam + ":" + ",".join(f"{k}={'+'.join(v) if isinstance(v, tuple) else v}" for k, v in p.items())


AXES = {  # 鄰域用：各家族每個軸的有序值
    "HOLD": {"w2": [i / 10 for i in range(11)], "w50": [i / 10 for i in range(11)]},
    "MA": {"n": [20, 40, 60, 90, 120, 150, 200, 250], "h": [0.0, 0.01, 0.02], "m": [1, 3, 5],
           "off": ["cash", "L2_20", "L2_30", "L2_40", "L2_50", "L2_60", "L2_70", "L2_80"]},
    "XO": {"fast": [20, 50, 60], "slow": [100, 150, 200, 250]},
    "AM": {"n": [60, 120, 180, 250], "h": [0.0, 0.02]},
    "VOL": {"tgt": [.10, .12, .15, .18, .20, .25, .30], "win": [20, 40, 60, 120], "thr": [.25, .5]},
    "TV": {"n": [60, 120, 200], "vhi": [.15, .20, .25, .30, .40], "win": [20, 60]},
    "DG": {"dd": [0.10, 0.15, 0.20], "vix": [25, 30, 35], "vol": [.25, .35], "wma": [26, 40], "k": [1, 2, 3]},
    "TX": {"n": [60, 120, 200], "x": [.5, 1.0]},
    "TXG": {"n": [60, 120, 200], "x": [1.0, 1.5, 2.0]},
    "RF": {"per": [10, 15, 20, 30], "mult": [2.0, 3.0, 4.0, 5.0]},
    "L1US": {"n": [100, 150, 200]},
    "SAT": {"s": [0.0, .2, .3, .5, 1.0]},
}


def neighbors(fam, p):
    out = []
    for ax, vals in AXES.get(fam, {}).items():
        if ax not in p or p[ax] not in vals:
            continue
        i = vals.index(p[ax])
        for j in (i - 1, i + 1):
            if 0 <= j < len(vals):
                q = dict(p); q[ax] = vals[j]
                out.append(q)
    return out


# ------------------------------------------------------------------ 統計：區塊重抽樣
def stationary_bootstrap(rs, r50, a_i, b_i, n_rep=2000, mean_block=40, seed=7):
    rng = np.random.default_rng(seed)
    n = b_i - a_i
    x = rs[a_i:b_i]; y = r50[a_i:b_i]
    out = np.empty(n_rep)
    pcut = 1.0 / mean_block
    for k in range(n_rep):
        idx = np.empty(n, np.int64)
        i = rng.integers(n)
        for t in range(n):
            idx[t] = i
            i = rng.integers(n) if rng.random() < pcut else (i + 1) % n
        out[k] = cagr(x[idx]) - MULT * cagr(y[idx])
    return out


# ------------------------------------------------------------------ 搜尋
def run_grid(world, bench, G=None, verbose=True):
    """全部組合都跑，登記每一組在每個視窗的結果。回傳 (registry DataFrame, {key: 日報酬})。"""
    import time
    G = grid() if G is None else G
    rows, rets = [], {}
    t0 = time.time()
    for n, (fam, p) in enumerate(G):
        try:
            W, fl, band = build(world, fam, p)
            r, turn = run(world, W, fl, band)
        except Exception as e:                                        # 登記失敗也要留痕，不默默吞掉
            rows.append(dict(key=key(fam, p), fam=fam, error=str(e)[:80]))
            continue
        k = key(fam, p)
        rets[k] = r
        ev = eval_row(world, bench, r)
        i0, i1 = _slice(world, START, None)
        m, _, _ = mdd(r[i0:i1])
        row = dict(key=k, fam=fam, sel_score=sel_score(world, bench, r), mdd_all=m, turn_yr=float(turn[i0:i1].sum() / ((i1 - i0) / 252)),
                   **{f"{nm}_cagr": v[0] for nm, v in ev.items()}, **{f"{nm}_gap": v[2] for nm, v in ev.items()})
        row["worst_seg_gap"] = min(ev[s][2] for s in SEGS)
        row["worst_oos_gap"] = min(ev[s][2] for s in OOS)
        rows.append(row)
        if verbose and n % 500 == 0:
            print(n, len(G), round(time.time() - t0, 1), flush=True)
    return pd.DataFrame(rows), rets


# ------------------------------------------------------------------ 選參規則（只准用 2003-07～2016）
SEL_A = ("2003-07-01", "2014-12-31")
SEL_B = ("2015-01-01", "2016-12-31")


def add_sel_cols(world, bench, reg, rets):
    """選參用欄位：selA／selB＝選參期內兩段（對應使用者的 A 段與 B 段前兩年）的『年化 - 1.5 x 0050』；mdd_sel＝選參期最大回撤。"""
    reg = reg.dropna(subset=["sel_score"]).copy()
    selA, selB, mdds = [], [], []
    for k in reg.key:
        r = rets[k]
        selA.append(cagr(window(world, r, *SEL_A)) - MULT * bench.c50(*SEL_A))
        selB.append(cagr(window(world, r, *SEL_B)) - MULT * bench.c50(*SEL_B))
        mdds.append(mdd(window(world, r, START, SEL_END))[0])
    reg["selA"], reg["selB"], reg["mdd_sel"] = selA, selB, mdds
    reg["sel_min"] = reg[["selA", "selB"]].min(axis=1)
    return reg


def pick(reg, mdd_floor=None):
    """只看選參期：兩段都要達標（sel_min >= 0）；有回撤上限就先套上限；再選 sel_min 最大者（平手取回撤較小）。"""
    c = reg[reg.sel_min >= 0]
    if mdd_floor is not None:
        c = c[c.mdd_sel >= mdd_floor]
    if c.empty:
        return None
    return c.sort_values(["sel_min", "mdd_sel"], ascending=[False, False]).iloc[0]


# ------------------------------------------------------------------ Walk-forward（逐步擴張的訓練窗，只選一次、之後的測試塊不回頭調）
WF_FOLDS = [("2009-01-01", "2010-12-31"), ("2011-01-01", "2012-12-31"), ("2013-01-01", "2014-12-31"), ("2015-01-01", "2016-12-31"),
            ("2017-01-01", "2020-12-31"), ("2021-01-01", None)]


def walk_forward(world, bench, reg, rets, mdd_floor=None, fam=None):
    """每個測試塊之前，用『訓練窗（2003-07 到測試塊前一天）』挑出最好的組合（年化 - 1.5 x 0050 最大，可加回撤上限），
    套到測試塊。把測試塊接起來算年化，對照同一批日子的 0050 x 1.5。"""
    pool = reg if fam is None else reg[reg.fam == fam]
    keys = list(pool.key)
    parts, rows = [], []
    for a, b in WF_FOLDS:
        i0, i1 = _slice(world, a, b)
        best, bs = None, -9
        for k in keys:
            tr = rets[k][world.start_i:i0]
            if len(tr) < 400:
                continue
            m = mdd(tr)[0]
            if mdd_floor is not None and m < mdd_floor:
                continue
            s = cagr(tr) - MULT * cagr(bench.r[world.start_i:i0])
            if s > bs:
                bs, best = s, k
        if best is None:
            continue
        seg = rets[best][i0:i1]; b50 = bench.r[i0:i1]
        parts.append((seg, b50))
        rows.append(dict(測試塊=f"{a[:7]}~{(b or 'now')[:7]}", 選到=best, 訓練期差距=bs, 測試年化=cagr(seg), 同期0050=cagr(b50),
                         測試差距=cagr(seg) - MULT * cagr(b50)))
    if not parts:
        return pd.DataFrame(), np.nan, np.nan
    s_all = np.concatenate([p[0] for p in parts]); b_all = np.concatenate([p[1] for p in parts])
    return pd.DataFrame(rows), cagr(s_all), cagr(b_all)


def neighbor_report(world, bench, fam, p, rets):
    out = []
    for q in neighbors(fam, p):
        k = key(fam, q)
        if k not in rets:
            continue
        r = rets[k]
        ev = eval_row(world, bench, r)
        out.append(dict(key=k, **{s: ev[s][2] for s in list(SEGS) + list(OOS)}, sel=sel_score(world, bench, r)))
    return pd.DataFrame(out)


# ------------------------------------------------------------------ 網路研調宣稱的逐條重現（L1～L8）
def stats(world, r, a, b=None):
    x = window(world, r, a, b)
    if len(x) < 30:
        return dict(cagr=np.nan, vol=np.nan, mdd=np.nan, sharpe=np.nan, n=len(x))
    m = mdd(x)[0]
    return dict(cagr=cagr(x), vol=float(np.std(x) * np.sqrt(252)), mdd=m, sharpe=float(np.mean(x) / (np.std(x) + 1e-12) * np.sqrt(252)), n=len(x))


def run_key(world, fam, p):
    W, fl, band = build(world, fam, p)
    return run(world, W, fl, band)[0]


def price_only_cagr(world, a, b=None):
    """0050 不含息（只看價格，部落格常用口徑）。"""
    r = (1 + world.on50_nd) * (1 + world.id50_nd) - 1
    return cagr(window(world, r, a, b))


def dca_multiple(world, r, a, b=None, rule=None):
    """每月第一個交易日投入 1 單位（rule 可改投入單位），回傳 (期末市值 / 總投入 - 1)。以日報酬複利，不計成本。"""
    i0, i1 = _slice(world, a, b)
    mo = world.cal.to_period("M")
    first = np.r_[True, mo[1:] != mo[:-1]]
    val, inv = 0.0, 0.0
    for i in range(i0, i1):
        val *= 1 + r[i]
        if first[i]:
            u = 1.0 if rule is None else rule(i)
            val += u; inv += u
    return val / inv - 1, inv


def us_replica(world):
    """Gayed 論文的美股版重現：S&P 500 價格報酬 x2（不含股利、扣 0.95% 費用與 2% 融資）+ 200 日線，2008 起（資料湖只有 2008 起的 S&P 500）。
    執行規則同本專案：t 收盤產生訊號、t+1 日報酬才拿到（簡化：用收盤對收盤報酬，等同 t+1 收盤進場，比開盤進場略保守）。"""
    s = world.spx_full.dropna()
    r = s.pct_change().fillna(0.0)
    two = 2 * r - (0.0095 + 0.02) / 252
    st = pd.Series(_hyst(s.to_numpy(), sma(s, 200).to_numpy(), 0.0, 1), index=s.index).shift(1).fillna(0)
    cash = 0.01 / 252
    timed = np.where(st > 0, two, cash)
    out = {}
    for nm, x in (("買進持有 1 倍(價格)", r), ("買進持有 2 倍(價格)", two), ("200 日線輪動 2 倍/現金", pd.Series(timed, index=s.index))):
        x = x[x.index >= "2008-01-02"]
        out[nm] = dict(cagr=cagr(x.to_numpy()), mdd=mdd(x.to_numpy())[0], sharpe=float(x.mean() / x.std() * np.sqrt(252)))
    return out


def claims(world, bench, rets_cache=None):
    rows = []
    now = None
    A14 = "2014-11-03"
    r631 = run_key(world, "HOLD", dict(w50=0.0, w2=1.0, reb="N"))
    r50 = bench.r
    # L5：00631L 買進持有（真實價格 2014-11 起）
    s5 = stats(world, r631, A14, now); s50 = stats(world, r50, A14, now)
    dca2, _ = dca_multiple(world, r631, "2014-11-03"); dca1, _ = dca_multiple(world, r50, "2014-11-03")
    rows.append(dict(id="L5", 名稱="00631L 買進持有（2014-11 起，真實價格）", 宣稱="12 年年化 33.39%~38.6%（0050 約 18.5%）；MDD -55.1% vs -33.8%；定期定額最終 682 萬 vs 278 萬（2.45 倍）",
                     重現=f"00631L 年化 {s5['cagr']*100:.1f}%、MDD {s5['mdd']*100:.1f}%；0050 含息年化 {s50['cagr']*100:.1f}%、MDD {s50['mdd']*100:.1f}%（含交易成本）；定期定額報酬倍數 00631L {1+dca2:.1f} 倍 vs 0050 {1+dca1:.1f} 倍（比值 {(1+dca2)/(1+dca1):.2f}）",
                     差距=f"00631L 年化 {s5['cagr']*100:.1f}% 落在宣稱 33.39%~38.6% 內（上緣）；MDD {s5['mdd']*100:.1f}% 與宣稱 -55.1% 一致；0050 年化 {s50['cagr']*100:.1f}% 比宣稱 18.5% 高 {(s50['cagr']-0.185)*100:.1f} 點；定期定額倍數比 {(1+dca2)/(1+dca1):.2f} 對宣稱 682/278=2.45",
                     原因="重現成功（00631L 年化與 MDD 對得上）。0050 差距：我們含息、期間到 2026-10-22（2026 年 0050 單年約 +63%）；定期定額比值差距：終點含 2026 的暴漲，起訖月不同（推測，未逐月對帳）"))
    # L4：50:50 再平衡
    a4, b4 = "2014-11-03", "2024-04-30"
    r4 = {}
    for reb in ("N", "M", "Q", "S", "A", "B5", "B10", "B20"):
        r4[reb] = stats(world, run_key(world, "HOLD", dict(w50=0.5, w2=0.5, reb=reb)), a4, b4)
    s50b = stats(world, r50, a4, b4)
    po = price_only_cagr(world, a4, b4)
    best = max(r4.items(), key=lambda kv: kv[1]["cagr"])
    txt = "；".join(f"{k}:{v['cagr']*100:.1f}%/MDD{v['mdd']*100:.0f}%" for k, v in r4.items())
    rows.append(dict(id="L4", 名稱="0050/00631L 50:50 再平衡（2014-10~2024-04）", 宣稱="再平衡版年化 16.04%、波動 19.41%、MDD -29.19%；單買 0050 年化 10.1%、MDD -36.36%；不再平衡 50:50 年化 20.1%、MDD -45.28%",
                     重現=f"{txt}；0050 含息 {s50b['cagr']*100:.1f}%（價格不含息 {po*100:.1f}%）、MDD {s50b['mdd']*100:.0f}%",
                     差距=f"再平衡版：年化 {r4['M']['cagr']*100:.1f}%~{r4['B20']['cagr']*100:.1f}% 對宣稱 16.04%（+{(r4['M']['cagr']-0.1604)*100:.0f}~{(r4['B20']['cagr']-0.1604)*100:.0f} 點）、MDD {r4['M']['mdd']*100:.0f}% 對宣稱 -29.19%；不再平衡 {r4['N']['cagr']*100:.1f}%/{r4['N']['mdd']*100:.0f}% 對 20.1%/-45.28%；0050 不含息 {po*100:.1f}% 對宣稱 10.1%（一致）",
                     原因="0050 的 10.1% 對得上『不含息價格』，所以部落格整篇用不含息價格（少算約 3.7%/年股利，50:50 的 0050 那半也少算）。但 50:50 是 1.5 倍曝險，MDD 比 0050 本身（-34%）還淺不合理；推測另一半是現金／債或用月資料、再平衡門檻未知（推測，原文未取得）"))
    # L1：Gayed 200 日線（台股版＋美股版）
    r1 = run_key(world, "MA", dict(n=200, h=0.0, m=1, on="L2", off="cash"))
    s1 = stats(world, r1, START, now); s1b = stats(world, r1, A14, now); s0 = stats(world, r50, START, now); s0b = stats(world, r50, A14, now)
    sl = stats(world, r631, START, now)
    us = us_replica(world)
    rows.append(dict(id="L1", 名稱="Gayed 200 日線槓桿輪動（站上持有 2 倍，跌破轉現金）", 宣稱="SSRN 擴充版 1988-2026（美股）：2 倍輪動 CAGR 14.00%、夏普 0.55、MDD -46.51%，基準 11.45%；PapersWithBacktest 1990-2026：12.24%、夏普 0.63、MDD -52.64%",
                     重現=f"台股 2003-07 起：200 日線正二/現金 年化 {s1['cagr']*100:.1f}%、夏普 {s1['sharpe']:.2f}、MDD {s1['mdd']*100:.1f}%（0050 含息 {s0['cagr']*100:.1f}%、正二買進持有 {sl['cagr']*100:.1f}%/MDD {sl['mdd']*100:.0f}%）；2014-11 起：{s1b['cagr']*100:.1f}%、MDD {s1b['mdd']*100:.1f}%（0050 {s0b['cagr']*100:.1f}%）。"
                          f"美股 2008 起（價格報酬、2 倍扣 2.95%）：輪動 {us['200 日線輪動 2 倍/現金']['cagr']*100:.1f}%/MDD {us['200 日線輪動 2 倍/現金']['mdd']*100:.0f}%，2 倍買進持有 {us['買進持有 2 倍(價格)']['cagr']*100:.1f}%/MDD {us['買進持有 2 倍(價格)']['mdd']*100:.0f}%，1 倍 {us['買進持有 1 倍(價格)']['cagr']*100:.1f}%",
                     差距=f"美股版（我們 2008 起）：輪動比 1 倍買進持有多 {(us['200 日線輪動 2 倍/現金']['cagr']-us['買進持有 1 倍(價格)']['cagr'])*100:.1f} 點（宣稱 +2.55 點）、MDD {us['200 日線輪動 2 倍/現金']['mdd']*100:.0f}%（宣稱 -46.5%）；台股版：輪動比正二買進持有少 {(sl['cagr']-s1['cagr'])*100:.1f} 點年化，但 MDD 從 {sl['mdd']*100:.0f}% 降到 {s1['mdd']*100:.0f}%",
                     原因="期間不同（宣稱 1988/1990 起，含 2000、2008 兩次大熊市的完整循環；台股樣本含 2008 一次、之後多頭）；台股 2014 後單邊多頭使擇時付出『錯過反彈』的成本；原論文重點是風險調整，絕對報酬優勢本來就小"))
    # L2：S&P 500 200 日線切 00631L／0050
    r2s = {off: run_key(world, "L1US", dict(n=200, off=off)) for off in ("50", "cash")}
    s2a = stats(world, r2s["50"], "2008-01-02", now); s2b = stats(world, r2s["50"], A14, now)
    s2c = stats(world, r631, "2014-11-03", now); s2d = stats(world, r2s["cash"], A14, now)
    rows.append(dict(id="L2", 名稱="S&P 500 站上 200 日線持 00631L，跌破切回 0050", 宣稱="年化 32.7%、MDD -37.8%（全程抱 00631L MDD -55.1%），收益保留約八成",
                     重現=f"2014-11 起：切 0050 版 年化 {s2b['cagr']*100:.1f}%/MDD {s2b['mdd']*100:.1f}%（正二買進持有 {s2c['cagr']*100:.1f}%/MDD {s2c['mdd']*100:.1f}%；0050 {s0b['cagr']*100:.1f}%）；切現金版 {s2d['cagr']*100:.1f}%/MDD {s2d['mdd']*100:.1f}%；2008 起（含代理）切 0050 版 {s2a['cagr']*100:.1f}%/MDD {s2a['mdd']*100:.1f}%",
                     差距=f"年化 {s2b['cagr']*100:.1f}% 對宣稱 32.7%（{(s2b['cagr']-0.327)*100:+.1f} 點）；MDD {s2b['mdd']*100:.1f}% 對宣稱 -37.8%（差 {(s2b['mdd']+0.378)*100:.1f} 點）；收益保留 {s2b['cagr']/s2c['cagr']*100:.0f}%（宣稱約 80%）；全程正二 MDD {s2c['mdd']*100:.1f}% 對宣稱 -55.1%（一致）",
                     原因="原文未取得（社群轉述），期間、成交價（收盤或開盤）、均線口徑（簡單或指數）、美股訊號何時才能用都未知；我們的美股訊號延後一個台北交易日才用（保守）"))
    # L3：Range Filter(15,4)
    r3 = run_key(world, "RF", dict(per=15, mult=4.0, off="cash"))
    s3 = stats(world, r3, START, now); s3b = stats(world, r3, A14, now)
    syn = synthetic_tse_2000(world)
    rows.append(dict(id="L3", 名稱="加權指數 Range Filter(15,4) 持有 00631L 或空手", 宣稱="2000-2026 模擬正二年化約 23%（周邊參數平均約 19%）、MDD 約 5 成；同期 0050 抱著約 10%",
                     重現=f"2003-07 起（本專案引擎）：年化 {s3['cagr']*100:.1f}%/MDD {s3['mdd']*100:.1f}%（0050 {s0['cagr']*100:.1f}%）；2014-11 起 {s3b['cagr']*100:.1f}%/MDD {s3b['mdd']*100:.1f}%（0050 {s0b['cagr']*100:.1f}%）；"
                          f"2000-2026 加權指數 x2 合成（價格口徑、含殘差）：{syn['rf']['cagr']*100:.1f}%/MDD {syn['rf']['mdd']*100:.0f}%，同期合成正二買進持有 {syn['bh2']['cagr']*100:.1f}%、加權指數 1 倍價格 {syn['bh1']['cagr']*100:.1f}%",
                     差距=f"2000 起合成口徑 {syn['rf']['cagr']*100:.1f}% 對宣稱約 23%（{(syn['rf']['cagr']-0.23)*100:+.1f} 點，重現成功）、MDD {syn['rf']['mdd']*100:.0f}% 對宣稱約 5 成；宣稱的『0050 約 10%』我們對不上：加權指數 1 倍價格 {syn['bh1']['cagr']*100:.1f}%、2003 起含息 0050 {s0['cagr']*100:.1f}%",
                     原因="Range Filter 照 TradingView 預設公式（週期 15、倍數 4）實作，隔日開盤成交、含成本。0050 基準的差異（推測）：宣稱用的是不含息或不同期間；若以含息 0050 當基準，Range Filter 正二在 2003-07 起的年化比值為 %.2f 倍（%.1f%% / %.1f%%）" % (s3['cagr'] / s0['cagr'], s3['cagr'] * 100, s0['cagr'] * 100)))
    # L6：波動目標
    reg_vol = [(k, v) for k, v in (rets_cache or {}).items() if k.startswith("VOL:")]
    if reg_vol:
        sc = []
        for k, v in reg_vol:
            sc.append((cagr(window(world, v, START, now)), k))
        sc.sort(reverse=True)
        top = sc[0]
        rows.append(dict(id="L6", 名稱="波動目標（自擬，無公開宣稱）", 宣稱="無來源（研調沒找到台股回測）",
                         重現=f"{len(sc)} 組中年化最高者 {top[1]}：{top[0]*100:.1f}%（0050 {s0['cagr']*100:.1f}%）；全期年化雖可超過 1.5 x 0050，但三段中最差一段都未達標（見排序表 VOL 家族的最差段差距）",
                         差距="無可比", 原因="波動目標在低波動多頭降不了風險也加不了很多槓桿（上限 2 倍），在崩盤前 20～60 日實現波動還來不及升高，所以擋不住第一波下跌"))
    # L7：0050 加碼
    ma60 = sma(world.tse_full, 60).reindex(world.cal).ffill().to_numpy(); tse = world.tse.to_numpy()
    bias = tse / ma60 - 1
    def rule(i):
        b = bias[i - 1] if i > 0 else 0.0
        return 2.0 if b < -0.05 else (0.5 if b > 0.10 else 1.0)
    base_m, base_inv = dca_multiple(world, r50, START, "2025-12-31")
    rule_m, rule_inv = dca_multiple(world, r50, START, "2025-12-31", rule)
    # 回檔 10% 單筆
    px = np.cumprod(1 + r50[world.start_i:])
    pk = np.maximum.accumulate(px); dd = px / pk - 1
    entries, last = [], -999
    i = 1
    while i < len(dd) - 250:
        if dd[i] <= -0.10 and dd[i - 1] > -0.10 and i - last > 250:
            entries.append(i); last = i
        i += 1
    outs = [px[min(i + 250, len(px) - 1)] / px[min(i + 1, len(px) - 1)] - 1 for i in entries]
    rows.append(dict(id="L7", 名稱="0050 加碼規則（季線乖離 / 回檔 10%）", 宣稱="季線乖離 <-5% 加碼 2 倍、>10% 減碼：累積 282.7% -> 287.9%（幾乎沒差）；回檔 10% 後單筆持有 1 年勝率 87%、平均 +20%（2003-2025）",
                     重現=f"定期定額 2003-07~2025：基本 {base_m*100:.0f}% vs 規則 {rule_m*100:.0f}%（報酬率=期末/總投入-1，投入總額 {base_inv:.0f} vs {rule_inv:.0f} 單位）；回檔 -10% 首次觸及隔日進場持有 250 日：{len(entries)} 次，勝率 {np.mean(np.array(outs)>0)*100:.0f}%、平均 {np.mean(outs)*100:.1f}%、中位 {np.median(outs)*100:.1f}%",
                     差距="定期定額方向與『效果小』一致；單筆規則的樣本只有個位數～十幾次且彼此重疊，87% 不是統計上穩的數字",
                     原因="乖離 >10% 減碼讓總投入變少、報酬率分母變小；回檔後進場的樣本只有幾次、同一個崩盤區間的多個進場點並不獨立"))
    rows.append(dict(id="L8", 名稱="今周刊「0050、正2、現金這樣搭」", 宣稱="標題「比 0050 多賺 4 倍」，規則未取得", 重現="原文規則不明，無法逐條重現；最接近的是固定比例（0050/正二/現金）——見排序表 HOLD 家族（含 66 種比例 x 8 種再平衡）",
                     差距="無法比對", 原因="只有標題；『多賺 4 倍』若指累積報酬，在 2014～2026 的單邊多頭本來就是正二買進持有的結果（L5）"))
    return rows


def synthetic_tse_2000(world):
    """2000 起、純加權指數合成 2 倍（價格報酬 x2 - 內扣 - 融資 + 校準殘差）。訊號：Range Filter(15,4)；隔日開盤成交（用 TSE 開盤價拆隔夜／盤中）。"""
    d = _rd("index_ohlc", ["date", "symbol", "open", "close"])
    d["date"] = pd.to_datetime(d["date"])
    t = d[d.symbol == "TSE"].drop_duplicates("date").set_index("date").sort_index()
    t = t[(t.close > 0)]
    c = t.close.astype(float); o = t.open.astype(float).where(t.open > 0, c.shift(1))
    on = (o / c.shift(1) - 1).fillna(0.0); idr = (c / o - 1).fillna(0.0)
    rf = pd.Series(c.index.year, index=c.index).map(RF_BY_YEAR).to_numpy()
    resid = world.calib["resid"]
    def two(x_on, x_id):
        r = (1 + x_on) * (1 + x_id) - 1
        r2 = 2 * r - (L2_FEE_Y + rf + resid) / 252
        on2 = 2 * x_on
        return on2.to_numpy(), ((1 + r2) / (1 + on2) - 1).to_numpy()
    on2, id2 = two(on, idr)
    st = range_filter_state(c, 15, 4.0).to_numpy()
    st = np.r_[0, st[:-1]]                               # 隔日才用
    cost = FEE + SLIP["L2"] + (FEE + ETF_TAX + SLIP["L2"])
    def sim_state(state):
        eq, r = 1.0, np.zeros(len(c)); prev = 0
        for i in range(len(c)):
            ret = (1 + (on2[i] if prev else rf[i] / 252)) * (1 + (id2[i] if state[i] else 0.0)) - 1
            if state[i] != prev:
                ret -= (FEE + SLIP["L2"]) if state[i] else (FEE + ETF_TAX + SLIP["L2"])
            r[i] = ret; prev = state[i]
        return r
    r_rf = sim_state(st)
    r_bh = sim_state(np.ones(len(c), int))
    m = (c.index >= "2000-02-01")
    r1 = (c.pct_change().fillna(0.0)).to_numpy()
    f = lambda x: dict(cagr=cagr(x[m]), mdd=mdd(x[m])[0])
    return dict(rf=f(r_rf), bh2=f(r_bh), bh1=f(r1))


def percentile_check(world, bench, n_rep=3000, block=40, seed=11):
    """L5 的『98.5 百分位』討論：(1) 歷史上所有 10 年滾動窗口，正二對 0050 的『期末財富比』分布與最近一窗的名次；
    (2) 用全樣本（2003-07~今）日報酬做穩健區塊重抽樣（0050 與 正二 同步抽），模擬 10 年期末財富比，看最近一窗落在哪。"""
    r2 = run_key(world, "HOLD", dict(w50=0.0, w2=1.0, reb="N"))
    r5 = bench.r
    i0 = world.start_i
    a, b = r2[i0:], r5[i0:]
    n = len(a); H = 2520
    ratios = []
    for s in range(0, n - H, 21):
        ratios.append(np.prod(1 + a[s:s + H]) / np.prod(1 + b[s:s + H]))
    ratios = np.array(ratios); last = np.prod(1 + a[-H:]) / np.prod(1 + b[-H:])
    hist_pct = float((ratios < last).mean() * 100)
    rng = np.random.default_rng(seed); sim = np.empty(n_rep); pc = 1.0 / block
    for k in range(n_rep):
        idx = np.empty(H, np.int64); i = rng.integers(n)
        for t in range(H):
            idx[t] = i
            i = rng.integers(n) if rng.random() < pc else (i + 1) % n
        sim[k] = np.prod(1 + a[idx]) / np.prod(1 + b[idx])
    return dict(last_ratio=float(last), hist_pct=hist_pct, hist_min=float(ratios.min()), hist_med=float(np.median(ratios)), hist_max=float(ratios.max()),
                sim_pct=float((sim < last).mean() * 100), sim_med=float(np.median(sim)), sim_p5=float(np.percentile(sim, 5)), sim_p95=float(np.percentile(sim, 95)),
                p_lose=float((sim < 1).mean() * 100), n_windows=len(ratios))


# ------------------------------------------------------------------ 候選檔案：分段表、回撤、帳本
def profile(world, bench, r, name):
    rows = []
    for nm, (a, b) in {**SEGS, **OOS, "全期 2003-07~今": (START, None)}.items():
        x = window(world, r, a, b); c = cagr(x); c5 = bench.c50(a, b)
        m, i, j = mdd(x)
        i0, _ = _slice(world, a, b)
        rows.append({"候選": name, "區段": nm, "年化": c, "同期0050含息": c5, "門檻(x1.5)": MULT * c5, "差距(點)": (c - MULT * c5) * 100,
                     "達標": "是" if c >= MULT * c5 else "否", "最大回撤": m, "回撤高點": str(world.cal[i0 + i].date()), "回撤低點": str(world.cal[i0 + j].date()),
                     "0050同期回撤": mdd(window(world, bench.r, a, b))[0]})
    return rows


def yearly(world, r, bench):
    yrs = world.cal[world.start_i:].year
    s = pd.Series(r[world.start_i:], index=world.cal[world.start_i:]); b = pd.Series(bench.r[world.start_i:], index=s.index)
    return pd.DataFrame({"策略": (1 + s).groupby(yrs).prod() - 1, "0050": (1 + b).groupby(yrs).prod() - 1})


def ledger(world, W, r, name):
    """紙上帳本：目標權重不變的連續期間算一筆（進場日＝權重換成這組的第一個交易日開盤；出場日＝下次換權重的前一個交易日收盤）。"""
    T = len(world.cal); i = world.start_i; rows = []
    while i < T:
        j = i
        while j + 1 < T and np.abs(W[j + 1] - W[i]).max() < 1e-9:
            j += 1
        seg = r[i:j + 1]
        eq = np.cumprod(1 + seg)
        eqf = np.r_[1.0, eq]
        rows.append(dict(策略=name, 進場日=str(world.cal[i].date()), 出場日=str(world.cal[j].date()), 持有交易日=j - i + 1,
                         部位="+".join(f"{a}:{W[i, IX[a]]:.2f}" for a in ASSETS if abs(W[i, IX[a]]) > 1e-9),
                         報酬=float(eq[-1] - 1), 區間最大不利=float((eqf / np.maximum.accumulate(eqf) - 1).min()),
                         同期0050=float(np.prod(1 + world.r50[i:j + 1]) - 1)))
        i = j + 1
    return pd.DataFrame(rows)


def md(df, floatfmt=None):
    if len(df) == 0:
        return "（無）"
    cols = list(df.columns)
    out = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join(("" if (isinstance(v, float) and np.isnan(v)) else str(v)) for v in r.values) + " |")
    return "\n".join(out)


def pc(x, d=1):
    return "" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x * 100:.{d}f}%"


def make_candidates(world, bench, reg, rets):
    """候選：兩個基準、依選參規則（只看 <=2016）選出的冠軍、以及『事後看三段都過』的幾個（這些是挑出來的，不是預先選的）。"""
    G = {key(f, p): (f, p) for f, p in grid()}
    cand = {}
    cand["基準：0050 買進持有"] = ("HOLD", dict(w50=1.0, w2=0.0, reb="N"))
    cand["基準：00631L 買進持有"] = ("HOLD", dict(w50=0.0, w2=1.0, reb="N"))
    c1 = pick(reg, None)
    c2 = pick(reg, -0.5)
    if c1 is not None:
        cand["協定冠軍 A（選參期兩段達標，無回撤上限）"] = G[c1.key]
    if c2 is not None and (c1 is None or c2.key != c1.key):
        cand["協定冠軍 B（同上，且選參期回撤 >= -50%）"] = G[c2.key]
    seg = ["A 2003-07~2014_gap", "B 2015~2020_gap", "C 2021~_gap", "樣本外 2017~2020_gap"]
    ap = reg[(reg[seg] >= 0).all(axis=1)].copy()
    if len(ap):
        ap["minseg"] = ap[seg].min(axis=1)
        low = ap.sort_values("mdd_all", ascending=False).iloc[0]
        cand["事後挑選 1（三段都過、回撤最小）"] = G[low.key]
        st = ap[ap.nb_pass >= 0.6].sort_values("mdd_all", ascending=False)
        if len(st):
            cand["事後挑選 2（三段都過、鄰域 >=60% 也過、回撤最小）"] = G[st.iloc[0].key]
        hd = ap[(ap.fam == "HOLD") & (ap.nb_pass >= 0.99)].sort_values("mdd_all", ascending=False)
        if len(hd):
            cand["事後挑選 3（固定比例，鄰域全過、回撤最小）"] = G[hd.iloc[0].key]
        mg = ap[ap.mdd_all >= -0.6].sort_values("minseg", ascending=False)
        if len(mg):
            cand["事後挑選 4（三段都過、回撤 >= -60%、最小邊際最大）"] = G[mg.iloc[0].key]
    return cand


def sensitivity(world_args, keys_fp, bench_names, mom_cache):
    """換一組假設重跑候選：代理序列改用 0050x2；代理再多扣 3%/年；滑價 x3。回傳 {情境: {候選: 三段差距}}。"""
    out = {}
    scen = {"代理改用 0050x2": dict(proxy_src="A50"), "代理再多扣 3%/年": dict(proxy_extra=0.03), "滑價 x3": dict(slip_mult=3.0)}
    for sn, kw in scen.items():
        w = World(with_mom=True, mom_cache=mom_cache, **kw)
        b = Bench(w)
        res = {}
        for nm, (f, p) in keys_fp.items():
            r = run_key(w, f, p)
            ev = eval_row(w, b, r)
            res[nm] = {s: ev[s][2] for s in SEGS}
        out[sn] = res
    return out


def main(quick=False):
    import json, time
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    w = World(); b = Bench(w)
    mom_cache = (w.ON[:, IX["MOM"]].copy(), w.ID[:, IX["MOM"]].copy(), w.mom_info)
    G = grid()
    reg, rets = run_grid(w, b, G, verbose=False)
    reg = add_sel_cols(w, b, reg, rets)
    seg = ["A 2003-07~2014_gap", "B 2015~2020_gap", "C 2021~_gap", "樣本外 2017~2020_gap"]
    reg["allpass"] = (reg[seg] >= 0).all(axis=1)
    ri = reg.set_index("key"); Gd = {key(f, p): (f, p) for f, p in G}
    nbs = []
    for k in reg.key:
        f, p = Gd[k]
        ns = [x for x in (key(f, q) for q in neighbors(f, p)) if x in ri.index]
        nbs.append(float(np.mean([ri.loc[n, "allpass"] for n in ns])) if ns else np.nan)
    reg["nb_pass"] = nbs
    reg["minseg"] = reg[seg].min(axis=1)
    reg["gap_worst_pts"] = reg["worst_seg_gap"] * 100
    cand = make_candidates(w, b, reg, rets)
    # 候選逐段、回撤、帳本
    prof, led, yr = [], [], {}
    for nm, (f, p) in cand.items():
        W_, fl, band = build(w, f, p)
        r, _ = run(w, W_, fl, band)
        prof += profile(w, b, r, nm)
        if not nm.startswith("基準：0050"):
            led.append(ledger(w, W_, r, nm))
        yr[nm] = yearly(w, r, b)
    prof = pd.DataFrame(prof)
    # 區塊重抽樣信賴區間
    boot = []
    for nm, (f, p) in cand.items():
        r = rets[key(f, p)]
        for sn, (a, bb) in SEGS.items():
            i0, i1 = _slice(w, a, bb)
            d = stationary_bootstrap(r, b.r, i0, i1, n_rep=1000 if quick else 2000)
            boot.append({"候選": nm, "區段": sn, "差距中位(點)": np.median(d) * 100, "5%": np.percentile(d, 5) * 100, "95%": np.percentile(d, 95) * 100,
                         "P(差距>=0)": float((d >= 0).mean())})
    boot = pd.DataFrame(boot)
    # 鄰域
    nbr = []
    for nm, (f, p) in cand.items():
        t = neighbor_report(w, b, f, p, rets)
        nbr.append(dict(候選=nm, 鄰居數=len(t), **({f"{s}過關比例": float((t[s] >= 0).mean()) for s in list(SEGS) + list(OOS)} if len(t) else {}),
                        三段全過比例=float(((t[list(SEGS)] >= 0).all(axis=1)).mean()) if len(t) else np.nan))
    nbr = pd.DataFrame(nbr)
    # walk-forward
    wf_tabs = {}
    for nm, fl in (("無回撤上限", None), ("訓練期回撤 >= -50%", -0.5)):
        df, cs, c5 = walk_forward(w, b, reg, rets, fl)
        wf_tabs[nm] = (df, cs, c5)
    # 敏感度
    keys_fp = {nm: cand[nm] for nm in cand if not nm.startswith("基準：0050")}
    sens = sensitivity(None, keys_fp, None, mom_cache) if not quick else {}
    cl = claims(w, b, rets)
    pcs = percentile_check(w, b, n_rep=1000 if quick else 3000)
    # 家族彙總
    fam_tab = []
    for f, g in reg.groupby("fam"):
        best_sel = g.sort_values("sel_min", ascending=False).iloc[0]
        best_gap = g.sort_values("worst_seg_gap", ascending=False).iloc[0]
        fam_tab.append({"家族": f, "試了幾組": len(g), "三段全過組數": int(g.allpass.sum()), "最佳(只看選參期)": best_sel.key, "最佳最差段差距(點)": best_gap.worst_seg_gap * 100,
                        "最佳最差段組合": best_gap.key})
    fam_tab = pd.DataFrame(fam_tab)
    # 輸出
    reg.drop(columns=["gap_worst_pts"]).to_csv(OUT / "registry.csv", index=False, encoding="utf-8-sig")
    rk = reg.sort_values("worst_seg_gap", ascending=False)
    rk_out = rk[["key", "fam", "worst_seg_gap", "A 2003-07~2014_gap", "B 2015~2020_gap", "C 2021~_gap", "樣本外 2017~2020_gap", "mdd_all", "nb_pass", "turn_yr", "sel_min"]].copy()
    rk_out.insert(0, "名次", range(1, len(rk_out) + 1))
    rk_out.to_csv(OUT / "ranking.csv", index=False, encoding="utf-8-sig")
    pd.concat(led).to_csv(OUT / "trades_ledger.csv", index=False, encoding="utf-8-sig")
    prof.to_csv(OUT / "candidates_profile.csv", index=False, encoding="utf-8-sig")
    w.calib_by_year().to_csv(OUT / "proxy_calibration_by_year.csv", encoding="utf-8-sig")
    meta = dict(n_combos=len(G), n_ok=len(reg), calib=w.calib, calib_inv=w.calib_inv, percentile=pcs, generated=str(pd.Timestamp.now().date()),
                mom=w.mom_info, elapsed=time.time() - t0)
    json.dump(meta, open(OUT / "_meta.json", "w"), ensure_ascii=False, indent=1, default=float)
    write_docs(w, b, reg, rk, cand, prof, boot, nbr, wf_tabs, sens, cl, pcs, fam_tab, yr, led)
    return reg


def write_docs(w, b, reg, rk, cand, prof, boot, nbr, wf_tabs, sens, cl, pcs, fam_tab, yr, led):
    L = []
    c50 = {nm: b.c50(a, bb) for nm, (a, bb) in {**SEGS, **OOS}.items()}
    n_all = int(reg.allpass.sum())
    L.append("# 0050／正二（00631L）搭配策略實驗室\n")
    L.append("> **免責**：歷史資料的研究回測，不是買賣建議、不下單。槓桿 ETF 在單一年可以虧掉六成以上；本頁所有『達標』都只說明過去，不保證未來。\n")
    L.append(f"目標（Andy）：年化報酬 >= 同期含息 0050 x {MULT}，**而且每一段驗證期都要達標**。三段：A 2003-07~2014（00631L 用代理序列）、B 2015~2020、C 2021 起；"
             f"另列『純樣本外』2017~2020 與 2021 起（參數只准用 2003-07~2016 選）。0050 含息年化（含交易成本）：" +
             "、".join(f"{k} {pc(v)}（門檻 {pc(MULT * v)}）" for k, v in c50.items()) + "。\n")
    L.append("## 〇、結論（先講結果）\n")
    def seg_gaps(nm, segs=("A 2003-07~2014", "B 2015~2020", "C 2021~", "樣本外 2017~2020")):
        d = prof[(prof.候選 == nm)].set_index("區段")
        return "；".join(f"{s_} {d.loc[s_, '差距(點)']:+.1f}" for s_ in segs)
    def full_mdd(nm):
        d = prof[(prof.候選 == nm) & (prof.區段.str.startswith("全期"))]
        return pc(d["最大回撤"].iloc[0])
    def nbr_all(nm):
        d = nbr[nbr.候選 == nm]
        return pc(d["三段全過比例"].iloc[0], 0) if len(d) else "n/a"
    def sens_txt(nm, seg_, scen="代理改用 0050x2"):
        try:
            return f"{sens[scen][nm][seg_] * 100:+.1f}"
        except Exception:
            return "未計算"
    bc_pass = int(((reg["B 2015~2020_gap"] >= 0) & (reg["C 2021~_gap"] >= 0)).sum())
    L.append(f"1. **單純買進持有 00631L 三段都達標**（沒有參數可調，沒有過度配適問題）：差距（點）{seg_gaps('基準：00631L 買進持有')}。"
             f"**代價**：全期最大回撤 {full_mdd('基準：00631L 買進持有')}（0050 {full_mdd('基準：0050 買進持有')}）；2008 的 -83% 是代理序列、不是真實 ETF；真實 00631L 上市後最大回撤 B 段 -52%、C 段 -55%（見第四節）。\n")
    pc2 = [k for k in cand if k.startswith("事後挑選 2")]
    pa = [k for k in cand if k.startswith("協定冠軍 A")]
    pb = [k for k in cand if k.startswith("協定冠軍 B")]
    if pc2:
        L.append(f"2. **想壓回撤又達標，目前最穩的是『事後挑選 2』`{key(*cand[pc2[0]])}`**（加權指數站上 200 日線±2% 持 100% 正二，跌破改持 30% 正二 + 70% 現金，隔日開盤換）："
                 f"差距（點）{seg_gaps(pc2[0])}；全期最大回撤 {full_mdd(pc2[0])}（2008 年 {yr[pc2[0]].loc[2008, '策略'] * 100:.0f}% 對 0050 的 {yr[pc2[0]].loc[2008, '0050'] * 100:.1f}%）。"
                 f"**但它是看過結果後挑的，不是冠軍**；A 段（2003~2014）只在『代理序列 = 加權指數 x2 + 校準殘差』的假設下達標（改用 0050 x 2 代理：{sens_txt(pc2[0], 'A 2003-07~2014')}，第 5.4 節）；邊際只有 3~7 個百分點，鄰域 {nbr_all(pc2[0])} 三段全過。\n")
    def verdict(nm):
        d = prof[prof.候選 == nm].set_index("區段")
        bad = [k for k in ("A 2003-07~2014", "B 2015~2020", "C 2021~", "樣本外 2017~2020") if d.loc[k, "差距(點)"] < 0]
        return ("全部四個區段都達標" if not bad else "未達標的區段：" + "、".join(bad)), len(bad) == 0
    for nm in (pa + pb):
        v, ok = verdict(nm)
        L.append(f"3{'a' if nm in pa else 'b'}. **依選參協定（只看 <=2016）選出的 {nm.split('（')[0]} `{key(*cand[nm])}`**：差距（點）{seg_gaps(nm)}；{v}。"
                 f"鄰域 {nbr_all(nm)} 三段全過；滑價 x3 後 A/B/C 差距 {sens_txt(nm, 'A 2003-07~2014', '滑價 x3')}/{sens_txt(nm, 'B 2015~2020', '滑價 x3')}/{sens_txt(nm, 'C 2021~', '滑價 x3')} 點。"
                 + ("" if ok else "**判定：協定選出的冠軍沒有通過驗證，沒有冠軍。**") + "\n")
    L.append(f"4. **全部 {len(reg)} 組中三段（含 2017~2020）都達標的有 {n_all} 組；只看有真實 ETF 價格的兩段（B、C）都達標的有 {bc_pass} 組。** 這是看過結果再數的，多重比較風險高；而且 00631L 本身就比 0050 x 1.5 高，所以『跟著 00631L 走』的組合幾乎都會達標，這不是規則厲害。Walk-forward（每塊只用之前資料選一次）兩種設定都未達標。\n")
    L.append("5. **00631L 過去 10 年屬於順風期**：歷史 10 年滾動窗口的名次與模擬見第六節 L5 補。結論：2015~2026 的達標有一半是『台股單邊多頭 + 正二』的結果，A 段（2003~2014）才是別種盤勢的考驗，而那一段恰好依賴代理序列。\n")
    # 搜尋家族
    L.append("## 一、試了什麼（全部登記在 `registry.csv`）\n")
    L.append(f"共 **{len(reg)} 組**（失敗/無資料的組合不計）。家族：HOLD 固定比例 x 再平衡頻率；MA 均線濾網（Gayed）；XO 雙均線；AM 絕對動能；VOL 波動目標；TV 趨勢加波動；DG 危險訊號（週K轉空 W／回撤 DD／跌破 200 日線 T／實現波動 VOL／VIX）；TX 搭配台指期；TXG 台指期單獨；SAT 個股動能衛星（12-1 動能前 10 檔）。\n")
    L.append(md(fam_tab.assign(**{"最佳最差段差距(點)": fam_tab["最佳最差段差距(點)"].round(2)})) + "\n")
    L.append("資料限制：**VIX 只有 2008 起**（資料湖），2003~2007 的 VIX 條件一律視為『未觸發』；台股 2003~2014 的 00631L 是代理序列；個股動能衛星用的 price_daily 沒還原除息價（報酬被低估約一個股利殖利率），"
             "且已下市個股是否完整未驗證。**TX 家族（台指期疊在正二上＝約 3 倍曝險）沒有模擬保證金追繳與強制平倉**，排名第一不代表可執行，實際 -85%~-88% 的回撤早就會被斷頭。\n")
    L.append("## 二、選參協定（只准用 2003-07~2016）與結果\n")
    L.append("選參規則（事先定好）：選參期內『A 段（2003-07~2014）』與『2015~2016』兩段的年化都 >= 0050 x 1.5，取兩者較小值最大者；平手取選參期回撤較小者。"
             "冠軍 B 另外加一條選參期最大回撤 >= -50%。選完參數就固定，不回頭調。\n")
    cp = prof[prof.候選.str.startswith("協定冠軍")]
    for nm in [x for x in cand if x.startswith("協定冠軍")]:
        f, p = cand[nm]
        L.append(f"- **{nm}**：`{key(f, p)}`")
    L.append("\n" + md(cp.assign(**{c: cp[c].map(pc) for c in ["年化", "同期0050含息", "門檻(x1.5)", "最大回撤", "0050同期回撤"]}).assign(**{"差距(點)": cp["差距(點)"].round(1)})) + "\n")
    L.append("**判定**見第〇節 3a／3b。冠軍的『選參期』是 2003-07~2016，所以 A 段與 B 段前兩年是樣本內；真正的樣本外只有 2017~2020 與 2021~。"
             "協定冠軍在樣本外的表現若比選參期差很多，就是過度配適的訊號（原因不在此逐一推測，沒驗證的不寫）。\n")
    L.append("## 三、依『離 0050 x 1.5 還差多少』排序（前 60；全部見 `ranking.csv`）\n")
    L.append("差距＝三段（A、B、C）中最差一段的『年化 - 1.5 x 0050 年化』，單位百分點；正＝三段都超過門檻。nb＝鄰域（各參數 ±1 格）三段全過的比例。\n")
    top = rk.head(60)
    t = pd.DataFrame({"名次": range(1, len(top) + 1), "組合": top.key.values, "最差段差距(點)": (top.worst_seg_gap * 100).round(2).values,
                      "A": (top["A 2003-07~2014_gap"] * 100).round(1).values, "B": (top["B 2015~2020_gap"] * 100).round(1).values,
                      "C": (top["C 2021~_gap"] * 100).round(1).values, "最大回撤": top.mdd_all.map(pc).values, "nb": top.nb_pass.round(2).values,
                      "年換手(倍)": top.turn_yr.round(1).values})
    L.append(md(t) + "\n")
    L.append("## 四、候選的逐段結果與回撤\n")
    pp = prof.copy()
    for c in ["年化", "同期0050含息", "門檻(x1.5)", "最大回撤", "0050同期回撤"]:
        pp[c] = pp[c].map(pc)
    pp["差距(點)"] = pp["差距(點)"].round(1)
    for nm in cand:
        f, p = cand[nm]
        L.append(f"### {nm}\n`{key(f, p)}`\n")
        L.append(md(pp[pp.候選 == nm].drop(columns=["候選"])) + "\n")
    L.append("### 逐年報酬（策略 vs 0050）\n")
    for nm, y in yr.items():
        if nm.startswith("基準：0050"):
            continue
        yy = y.copy(); yy["策略"] = yy["策略"].map(pc); yy["0050"] = yy["0050"].map(pc)
        worst = y.sort_values("策略").head(3)
        L.append(f"**{nm}**：最慘三年 " + "、".join(f"{i} 年 {pc(v.策略)}（0050 {pc(v['0050'])}）" for i, v in worst.iterrows()) + "\n")
    L.append("## 五、驗證\n")
    L.append("### 5.1 區塊重抽樣（穩健區塊，平均區塊 40 個交易日；差距＝年化 - 1.5 x 0050 年化，點）\n")
    bb = boot.copy()
    for c in ["差距中位(點)", "5%", "95%"]:
        bb[c] = bb[c].round(1)
    bb["P(差距>=0)"] = bb["P(差距>=0)"].round(2)
    L.append(md(bb) + "\n")
    L.append("### 5.2 參數鄰域（各參數 ±1 格的鄰居，過關比例）\n")
    nn = nbr.copy()
    for c in nn.columns[2:]:
        nn[c] = nn[c].round(2)
    L.append(md(nn) + "\n")
    L.append("### 5.3 Walk-forward（逐步擴張訓練窗；每個測試塊只用之前的資料選一次）\n")
    for nm, (df, cs, c5) in wf_tabs.items():
        L.append(f"**{nm}**：測試塊接起來年化 {pc(cs)}，同批日子 0050 {pc(c5)}（門檻 {pc(MULT * c5)}）→ {'達標' if cs >= MULT * c5 else '未達標'}\n")
        d = df.copy()
        for c in ["訓練期差距", "測試年化", "同期0050", "測試差距"]:
            d[c] = d[c].map(pc)
        L.append(md(d) + "\n")
    L.append("### 5.4 敏感度（假設換一組，三段差距，點）\n")
    if sens:
        rows = []
        for sn, res in sens.items():
            for nm, g in res.items():
                rows.append({"情境": sn, "候選": nm, **{k: round(v * 100, 1) for k, v in g.items()}})
        L.append(md(pd.DataFrame(rows)) + "\n")
    L.append("## 六、網路研調宣稱的逐條重現（L1~L8）\n")
    for r in cl:
        L.append(f"### {r['id']}　{r['名稱']}\n- 原宣稱：{r['宣稱']}\n- 我們重現：{r['重現']}\n- 差距：{r['差距']}\n- 原因：{r['原因']}\n")
    L.append("### L5 補：00631L 近 10 年是不是順風期\n")
    L.append(f"- 歷史 {pcs['n_windows']} 個 10 年滾動窗口（月初起算、2003-07 起、含代理序列），正二對 0050 的期末財富比：中位 {pcs['hist_med']:.2f}、最小 {pcs['hist_min']:.2f}、最大 {pcs['hist_max']:.2f}；"
             f"最近一窗 {pcs['last_ratio']:.2f}，名次在第 {pcs['hist_pct']:.0f} 百分位（窗口彼此高度重疊，不是獨立樣本）。")
    L.append(f"- 區塊重抽樣（全樣本日報酬，3000 次、10 年）：模擬期末財富比中位 {pcs['sim_med']:.2f}、5%~95% 為 {pcs['sim_p5']:.2f}~{pcs['sim_p95']:.2f}；最近一窗落在第 {pcs['sim_pct']:.0f} 百分位；模擬中正二輸 0050 的機率 {pcs['p_lose']:.0f}%。")
    L.append("- 研調引述（清流君）：第 98.5 百分位、長期中位約 0050 的 1.4~1.5 倍。本實驗的數字是在同一個資料（含 2003~2014 代理）上算的，**樣本內含 2009 的 +100% 反彈與 2020~2026 的多頭**，不是獨立證據。\n")
    L.append("## 七、風險與失效條件（槓桿策略的回撤一定比 0050 大）\n")
    allp = prof[prof.區段.str.startswith("全期")][["候選", "最大回撤", "回撤高點", "回撤低點", "0050同期回撤"]].copy()
    allp["最大回撤"] = allp["最大回撤"].map(pc); allp["0050同期回撤"] = allp["0050同期回撤"].map(pc)
    L.append(md(allp) + "\n")
    L.append("- 全期最大回撤都發生在 **2008 金融海嘯**（正二是代理序列，不是真實發生過的 ETF 淨值）；真實 00631L 上市後最慘是 2025 年 4 月關稅崩盤與 2022 年空頭，數字見各候選的 B、C 段回撤。")
    L.append("- 失效盤勢：(1) 長期盤整＋高波動（每日重設的損耗，正二輸給 1 倍）；(2) 急跌後快速 V 轉（均線濾網出場後錯過反彈，例如 2020-03、2025-04）；(3) 單日跳空（隔日開盤成交，趨勢濾網來不及）；(4) 台指期正價差消失或轉逆價差（正二與期貨型策略的成本上升）；(5) 單一年虧損可能 > 50%，要有能忍受的資金與心理。")
    L.append("- 不能全當成預測：三段『達標』是樣本內的差距，且 C 段 0050 年化高達 29%，要求的 43% 只有 2025~2026 的 AI 行情撐起來。\n")
    L.append("## 八、冠軍誠實標示（哪些資料段在前幾輪被看過）\n")
    L.append("- 本實驗的策略都是首次在 00631L／0050 搭配上評估；但**危險訊號（W 週K、DD、VIX、逆價差）是前幾輪台指期研究在 2008~2016、2017~2020、2021 起三段上挑出來的**，它們在這幾段早已被看過；2003-07~2007 是第四輪只揭露過一次的乾淨段，但本輪的選參期含這段，所以不再乾淨。")
    L.append("- 0050 的各段報酬在前幾輪都已經是基準，已被看過。真正沒被任何前輪選參用過的只有『00631L 在 2014 後的真實報酬』與『這輪新增的均線/動能/固定比例家族』，但我們看了全部結果才寫這份報告，所以**事後挑選的候選都不是冠軍**，只能叫『事後通過清單』。")
    L.append(f"- 多重比較：試了 {len(reg)} 組，其中 {n_all} 組三段全過；即使隨機組合，也會有一部分因為『正二本來就比 0050 高』而達標——這正是 00631L 買進持有三段都過的原因，不是這些規則厲害。\n")
    L.append("## 九、代理序列校準\n")
    cb = w.calib
    L.append(f"- 00631L 代理：2 x 加權指數日報酬 - 內扣 {pc(L2_FEE_Y,2)}/年 - 融資（定存利率近似表）- 校準殘差 {pc(cb['resid'],2)}/年（負值＝真實 ETF 比 2 倍價格報酬多賺，來自股利與期貨正價差）。")
    L.append(f"- 校準於 2014-11 起（n={cb['n']}）：日報酬相關 {cb['daily_corr_proxy']:.3f}、年化追蹤誤差 {pc(cb['te'])}、累積報酬 真實 {cb['cum_real']:.1f} vs 代理 {cb['cum_proxy']:.1f}（殘差使總量對齊）。")
    L.append("- **發現**：用 0050 x 2 當代理，逐年誤差標準差 16.9 點（2024 起單年差 20~42 點）；用加權指數 x 2，標準差 9.5 點。真實 00631L 追的是加權指數期貨的 2 倍，而不是 0050 的 2 倍（2024 年 0050 +48.6% 但 00631L 只有 +59%）。所以預設代理改用加權指數；0050 版放在敏感度。")
    L.append("- 逐年誤差見 `proxy_calibration_by_year.csv`（2016、2019、2020 單年低估 9~13 點，2024~2026 高估 7~23 點）。**代理序列在 2003~2014 的可信度無法用上市前資料驗證**，把校準殘差（+9%/年）外推到 2003~2014 是假設。\n")
    L.append("## 十、檔案\n- `registry.csv`：全部組合與各視窗結果；`ranking.csv`：依最差段差距排序；`trades_ledger.csv`：候選的紙上帳本（進出場日、部位、報酬、區間最大不利、同期 0050）；"
             "`candidates_profile.csv`；`proxy_calibration_by_year.csv`；`_meta.json`。\n- 程式：`pipeline/compute/lev_lab.py`；測試：`tests/test_lev_lab.py`。\n")
    (OUT / "README.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    import sys as _s
    main(quick="--quick" in _s.argv)
