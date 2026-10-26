"""台指期第二輪（方向修正版）：重點在策略，不在槓桿。三階段：單一指標普查 -> 加入消息面與濾網 -> 多指標組合與參數優化。

主結果：1 倍名目曝險、只做多（上一輪放空是淨負貢獻）、扣手續費／期交稅／滑價／換月成本（同第一輪 futures_lab.py）。
槓桿（2、3 倍，含保證金與強制平倉模擬）只放附表。

防過度擬合（程式強制執行）
  * 所有搜尋、選參、優化只用 2001-01-02～2018-12-31；2019-01-01 起是「最終保留期」，只能由 final_holdout() 跑一次
    （同一次同時算「優化版」「預設參數版」與槓桿附表），跑完寫鎖檔 round2/_holdout_done.json，再呼叫直接拒絕。
  * 所有試過的組合都登記進 registry_*.csv。
  * 冠軍要同時通過：(1) 搜尋期 walk-forward 多數段（> 1/2）年化贏 0050；(2) 參數鄰域 >= 2/3 贏 0050 年化；
    (3) 保留期年化高於 0050 且最大回撤不比 0050 差。
  * 誠實揭露：第一輪已經看過 2013～2026 的整體結果（含 2019 以後），所以保留期並非真正沒看過的資料；
    本輪所有設計都沒有用保留期調整，但這個污染要讓讀者知道。

保證金假設（附表用，非資料）：原始保證金 = 名義 10%、維持保證金 = 名義 8%；每日以最不利價（多單用最低價）檢查，
跌破維持保證金 -> 以該價再扣滑價強制平倉。期交所 TX 原始保證金歷史：2021-02 167,000（約名義 5%）、2024-11 338,000（約 7%）、
2025-03 307,000；2000 年代約 10～12%（出處見 README）。口數連續值近似、起始權益 1,000 萬。
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from numba import njit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.compute import futures_lab as F  # noqa: E402

OUT = ROOT / "docs" / "futures_lab" / "round2"
MULT, FEE_NTD, TAX, SLIP, ROLL_PTS = F.MULT, F.FEE_NTD, F.TAX, F.SLIP_PTS, F.ROLL_PTS
E0 = 1.0e7
M_INIT, M_MAINT = 0.10, 0.08
BAND = 0.25
SEARCH_START, SEARCH_END = "2001-01-02", "2019-01-01"
B50_START = "2003-07-01"
HOLDOUT = "2019-01-01"
WF_TEST = ["2008-01-01", "2011-01-01", "2014-01-01", "2017-01-01"]
CENSUS_START = "2001-01-02"


# ------------------------------------------------------------------ 帶保證金的權益引擎
@njit(cache=True)
def _sim_lev(o, h, l, c, tgt, rollday, fee, slip, tax, roll_pts, m_init, m_maint, band, cash_d, e0):
    n = len(c)
    r = np.zeros(n); qa = np.zeros(n); liq = np.zeros(n)
    E = e0; q = 0.0
    for i in range(1, n):
        Eo = E + q * 200.0 * (o[i] - c[i - 1])
        if Eo <= 0:
            Eo = 1e-6
        qt = tgt[i - 1] * Eo / (o[i] * 200.0)
        qmax = Eo / (m_init * o[i] * 200.0)
        if qt > qmax:
            qt = qmax
        do = False
        if q == 0.0 and qt > 0.0:
            do = True
        elif qt == 0.0 and q > 0.0:
            do = True
        elif q > 0.0 and abs(qt - q) > band * q:
            do = True
        if do:
            dq = qt - q
            Eo -= abs(dq) * (fee + 200.0 * slip) + tax * abs(dq) * 200.0 * o[i]
            q = qt
        if q > 0.0:
            eadv = Eo + q * 200.0 * (l[i] - o[i])
            if eadv < m_maint * q * 200.0 * l[i]:       # 強制平倉
                Eo = eadv - q * (fee + 200.0 * slip) - tax * q * 200.0 * l[i]
                if Eo <= 0:
                    Eo = 1e-6
                liq[i] = 1.0
                q = 0.0
                Ec = Eo * (1.0 + cash_d)
                r[i] = Ec / E - 1.0; E = Ec; qa[i] = 0.0
                continue
        Ec = Eo + q * 200.0 * (c[i] - o[i])
        if rollday[i] and q > 0.0:
            Ec -= q * (roll_pts * 200.0 + 2.0 * fee)
        if Ec <= 0:
            Ec = 1e-6
        Ec *= (1.0 + cash_d)
        r[i] = Ec / E - 1.0; E = Ec; qa[i] = q
    return r, qa, liq



# ------------------------------------------------------------------ 指標（回傳「多方狀態」布林陣列；狀態在該根 K 收盤已知）
def _sma(x, n):
    return pd.Series(x).rolling(n).mean().to_numpy()


def _ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def _hh(x, n):
    return pd.Series(x).rolling(n).max().to_numpy()


def _ll(x, n):
    return pd.Series(x).rolling(n).min().to_numpy()


def _clean(a):
    return np.nan_to_num(np.asarray(a, float), nan=0.0) > 0.5


@njit(cache=True)
def _hyst_nb(enter, exit_):
    n = len(enter); out = np.zeros(n, np.bool_); s = False
    for i in range(n):
        if s and exit_[i]:
            s = False
        elif (not s) and enter[i]:
            s = True
        out[i] = s
    return out


@njit(cache=True)
def _kd_nb(h, l, c, n):
    m = len(c); K = np.full(m, 50.0); D = np.full(m, 50.0)
    for i in range(n - 1, m):
        hh = h[i - n + 1:i + 1].max(); ll = l[i - n + 1:i + 1].min()
        rsv = 50.0 if hh == ll else (c[i] - ll) / (hh - ll) * 100.0
        K[i] = K[i - 1] * 2.0 / 3.0 + rsv / 3.0
        D[i] = D[i - 1] * 2.0 / 3.0 + K[i] / 3.0
    return K, D


@njit(cache=True)
def _supertrend_nb(h, l, c, atr, mult):
    n = len(c); up = np.zeros(n, np.bool_)
    fub = np.full(n, np.nan); flb = np.full(n, np.nan)
    trend = 1
    for i in range(1, n):
        if np.isnan(atr[i]):
            continue
        hl2 = (h[i] + l[i]) / 2.0
        ub = hl2 + mult * atr[i]; lb = hl2 - mult * atr[i]
        pu = fub[i - 1]; pl = flb[i - 1]
        fub[i] = ub if (np.isnan(pu) or ub < pu or c[i - 1] > pu) else pu
        flb[i] = lb if (np.isnan(pl) or lb > pl or c[i - 1] < pl) else pl
        if trend == 1 and c[i] < flb[i]:
            trend = -1
        elif trend == -1 and c[i] > fub[i]:
            trend = 1
        up[i] = trend == 1
    return up


@njit(cache=True)
def _sar_nb(h, l, af0, afmax):
    n = len(h); up = np.zeros(n, np.bool_)
    bull = True; sar = l[0]; ep = h[0]; af = af0
    for i in range(1, n):
        sar = sar + af * (ep - sar)
        if bull:
            sar = min(sar, l[i - 1], l[i - 2] if i >= 2 else l[i - 1])
            if l[i] < sar:
                bull = False; sar = ep; ep = l[i]; af = af0
            elif h[i] > ep:
                ep = h[i]; af = min(af + af0, afmax)
        else:
            sar = max(sar, h[i - 1], h[i - 2] if i >= 2 else h[i - 1])
            if h[i] > sar:
                bull = True; sar = ep; ep = h[i]; af = af0
            elif l[i] < ep:
                ep = l[i]; af = min(af + af0, afmax)
        up[i] = bull
    return up


@njit(cache=True)
def _ha_nb(o, h, l, c):
    n = len(c); hac = (o + h + l + c) / 4.0; hao = np.zeros(n)
    hao[0] = (o[0] + c[0]) / 2.0
    for i in range(1, n):
        hao[i] = (hao[i - 1] + hac[i - 1]) / 2.0
    return hac > hao


def _dmi(h, l, c, n):
    up = np.diff(h, prepend=h[0]); dn = -np.diff(l, prepend=l[0])
    pdm = np.where((up > dn) & (up > 0), up, 0.0); mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    pc = np.roll(c, 1); pc[0] = c[0]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    a = lambda x: pd.Series(x).ewm(alpha=1.0 / n, adjust=False).mean().to_numpy()
    atr_ = a(tr); pdi = 100 * a(pdm) / np.where(atr_ > 0, atr_, np.nan); mdi = 100 * a(mdm) / np.where(atr_ > 0, atr_, np.nan)
    dx = 100 * abs(pdi - mdi) / np.where((pdi + mdi) > 0, pdi + mdi, np.nan)
    return pdi, mdi, a(np.nan_to_num(dx))


def ind_state(name: str, d: dict, p: dict) -> np.ndarray:
    o, h, l, c, v = d["o"], d["h"], d["l"], d["c"], d["v"]
    n_ = len(c)
    if name == "MA":
        return _clean(c > _sma(c, p["n"]))
    if name == "EMAX":
        return _clean(_ema(c, p["a"]) > _ema(c, p["b"]))
    if name == "MACD":
        dif = _ema(c, p["f"]) - _ema(c, p["s"]); dea = _ema(dif, p["g"])
        return _clean(dif > dea)
    if name == "RSI":
        return _clean(F.rsi_wilder(c, p["n"]) > 50)
    if name == "KD":
        K, D = _kd_nb(h, l, c, p["n"])
        return _clean(K > D)
    if name == "BOLL":
        m = _sma(c, p["n"]); sd = pd.Series(c).rolling(p["n"]).std().to_numpy()
        return _hyst_nb(_clean(c > m + p["m"] * sd), _clean(c < m))
    if name == "DON":
        hi = pd.Series(c).rolling(p["i"]).max().shift(1).to_numpy(); lo = pd.Series(c).rolling(p["o"]).min().shift(1).to_numpy()
        return _hyst_nb(_clean(c > hi), _clean(c < lo))
    if name == "ST":
        return _supertrend_nb(h, l, c, F.atr_wilder(h, l, c, p["n"]), float(p["m"]))
    if name == "ADX":
        pdi, mdi, adx = _dmi(h, l, c, 14)
        return _clean((pdi > mdi) & (adx > p["thr"]))
    if name == "ICHI":
        t = (_hh(h, p["t"]) + _ll(l, p["t"])) / 2; k = (_hh(h, p["k"]) + _ll(l, p["k"])) / 2
        a = np.r_[np.full(p["k"], np.nan), ((t + k) / 2)[:-p["k"]]]
        b = np.r_[np.full(p["k"], np.nan), ((_hh(h, p["b"]) + _ll(l, p["b"])) / 2)[:-p["k"]]]
        return _clean(c > np.fmax(a, b))
    if name == "SAR":
        return _sar_nb(h, l, p["af"], p["mx"])
    if name == "CCI":
        tp = (h + l + c) / 3; m = _sma(tp, p["n"])
        md = pd.Series(tp).rolling(p["n"]).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True).to_numpy()
        return _clean((tp - m) / (0.015 * np.where(md > 0, md, np.nan)) > 0)
    if name == "WR":
        hh, ll = _hh(h, p["n"]), _ll(l, p["n"])
        return _clean((c - ll) / np.where(hh > ll, hh - ll, np.nan) > 0.5)
    if name == "ROC":
        return _clean(c / pd.Series(c).shift(p["n"]).to_numpy() > 1.0)
    if name == "OBV":
        obv = np.cumsum(np.sign(np.diff(c, prepend=c[0])) * v)
        return _clean(obv > _sma(obv, p["n"]))
    if name == "VP":
        m = _sma(c, p["n"])
        return _hyst_nb(_clean((c > m) & (v > 1.2 * _sma(v, p["n"]))), _clean(c < m))
    if name == "ATRCH":
        m = _sma(c, p["n"]); a = F.atr_wilder(h, l, c, 14)
        return _hyst_nb(_clean(c > m + p["m"] * a), _clean(c < m))
    if name == "KELT":
        m = _ema(c, p["n"]); a = F.atr_wilder(h, l, c, 10)
        return _hyst_nb(_clean(c > m + p["m"] * a), _clean(c < m))
    if name == "HA":
        g = _ha_nb(o, h, l, c).astype(float)
        return _clean(pd.Series(g).rolling(p["k"]).min().to_numpy())
    if name == "TRIX":
        e = _ema(_ema(_ema(c, p["n"]), p["n"]), p["n"])
        return _clean(np.diff(e, prepend=e[0]) / e > 0)
    if name == "AROON":
        n = p["n"]
        up = pd.Series(h).rolling(n + 1).apply(lambda x: 100.0 * np.argmax(x) / n, raw=True).to_numpy()
        dn = pd.Series(l).rolling(n + 1).apply(lambda x: 100.0 * np.argmin(x) / n, raw=True).to_numpy()
        return _clean((up > dn) & (up > 50))
    if name == "GAP":
        ph = np.r_[np.nan, h[:-1]]
        return _hyst_nb(_clean(o > ph * (1 + p["g"])), _clean(c < _sma(c, 10)))
    if name == "NHI":
        hi = pd.Series(h).rolling(p["i"]).max().shift(1).to_numpy(); lo = pd.Series(l).rolling(p["o"]).min().shift(1).to_numpy()
        return _hyst_nb(_clean(c > hi), _clean(c < lo))
    raise ValueError(name)


NAMES = {"VOTE": "多指標投票", "MA": "均線 MA", "EMAX": "EMA 交叉", "MACD": "MACD", "RSI": "RSI(>50)", "KD": "KD(9,3,3)", "BOLL": "布林通道突破",
         "DON": "唐奇安通道", "ST": "SuperTrend", "ADX": "ADX/DMI", "ICHI": "一目均衡(雲帶)", "SAR": "拋物線 SAR", "CCI": "CCI",
         "WR": "威廉 %R", "ROC": "ROC 動量", "OBV": "OBV", "VP": "量價(量增站上均線)", "ATRCH": "ATR 通道", "KELT": "Keltner 通道",
         "HA": "Heikin-Ashi", "TRIX": "TRIX", "AROON": "Aroon", "GAP": "缺口(跳空向上)", "NHI": "N 日新高(高點)"}

# 每個指標：日K 預設 / 週K 預設 / 優化格點（日、週）。預設＝教科書常用參數，事先固定，不看結果。
SPEC = {
    "MA": dict(D=dict(n=60), W=dict(n=20), gD=dict(n=[30, 60, 120, 200]), gW=dict(n=[10, 20, 40])),
    "EMAX": dict(D=dict(a=12, b=26), W=dict(a=5, b=20), gD=dict(a=[5, 12], b=[26, 60]), gW=dict(a=[3, 5], b=[13, 20, 40])),
    "MACD": dict(D=dict(f=12, s=26, g=9), W=dict(f=12, s=26, g=9), gD=dict(f=[8, 12, 19], s=[17, 26, 39], g=[9]),
                 gW=dict(f=[6, 12], s=[13, 26], g=[9])),
    "RSI": dict(D=dict(n=14), W=dict(n=14), gD=dict(n=[7, 14, 21, 34]), gW=dict(n=[7, 14, 21])),
    "KD": dict(D=dict(n=9), W=dict(n=9), gD=dict(n=[5, 9, 14, 21]), gW=dict(n=[5, 9, 14])),
    "BOLL": dict(D=dict(n=20, m=2.0), W=dict(n=20, m=2.0), gD=dict(n=[20, 40], m=[1.5, 2.0]), gW=dict(n=[10, 20], m=[1.5, 2.0])),
    "DON": dict(D=dict(i=20, o=10), W=dict(i=13, o=4), gD=dict(i=[20, 40, 60, 100], o=[10, 20, 50]), gW=dict(i=[13, 26, 52], o=[4, 8, 13])),
    "ST": dict(D=dict(n=10, m=3), W=dict(n=10, m=3), gD=dict(n=[10, 14], m=[2, 3, 4]), gW=dict(n=[7, 10], m=[2, 3])),
    "ADX": dict(D=dict(thr=20), W=dict(thr=20), gD=dict(thr=[15, 20, 25]), gW=dict(thr=[15, 20, 25])),
    "ICHI": dict(D=dict(t=9, k=26, b=52), W=dict(t=9, k=26, b=52), gD=dict(t=[7, 9], k=[22, 26], b=[44, 52]), gW=dict(t=[9], k=[26], b=[52])),
    "SAR": dict(D=dict(af=0.02, mx=0.2), W=dict(af=0.02, mx=0.2), gD=dict(af=[0.015, 0.02, 0.03], mx=[0.2]), gW=dict(af=[0.02, 0.03], mx=[0.2])),
    "CCI": dict(D=dict(n=20), W=dict(n=20), gD=dict(n=[14, 20, 40, 60]), gW=dict(n=[14, 20, 40])),
    "WR": dict(D=dict(n=14), W=dict(n=14), gD=dict(n=[10, 14, 28, 60]), gW=dict(n=[10, 14, 28])),
    "ROC": dict(D=dict(n=60), W=dict(n=26), gD=dict(n=[20, 60, 120, 250]), gW=dict(n=[13, 26, 52])),
    "OBV": dict(D=dict(n=50), W=dict(n=26), gD=dict(n=[20, 50, 100]), gW=dict(n=[13, 26, 52])),
    "VP": dict(D=dict(n=20), W=dict(n=10), gD=dict(n=[10, 20, 60]), gW=dict(n=[5, 10, 20])),
    "ATRCH": dict(D=dict(n=20, m=1.5), W=dict(n=10, m=1.5), gD=dict(n=[20, 50], m=[1.0, 1.5, 2.0]), gW=dict(n=[10, 20], m=[1.0, 1.5])),
    "KELT": dict(D=dict(n=20, m=2.0), W=dict(n=20, m=2.0), gD=dict(n=[20, 50], m=[1.5, 2.0, 3.0]), gW=dict(n=[10, 20], m=[1.5, 2.0])),
    "HA": dict(D=dict(k=2), W=dict(k=2), gD=dict(k=[1, 2, 3, 4]), gW=dict(k=[1, 2, 3])),
    "TRIX": dict(D=dict(n=15), W=dict(n=15), gD=dict(n=[9, 15, 30, 60]), gW=dict(n=[9, 15, 30])),
    "AROON": dict(D=dict(n=25), W=dict(n=25), gD=dict(n=[14, 25, 50, 100]), gW=dict(n=[14, 25, 50])),
    "GAP": dict(D=dict(g=0.005), W=None, gD=dict(g=[0.003, 0.005, 0.01]), gW=None),
    "VOTE": dict(D=dict(m=3), W=None, gD=dict(m=[2, 3, 4]), gW=None),
    "NHI": dict(D=dict(i=60, o=20), W=dict(i=26, o=8), gD=dict(i=[60, 120, 250], o=[20, 40, 60]), gW=dict(i=[26, 52], o=[8, 13])),
}


def grid_of(g: dict):
    keys = list(g)
    return [dict(zip(keys, vals)) for vals in itertools.product(*[g[k] for k in keys])]


def pstr(name, tf, p):
    return f"{name}[{tf}]({','.join(f'{k}={v}' for k, v in p.items())})"


# ------------------------------------------------------------------ 資料與回測器
class Lab2:
    def __init__(self):
        self.lab = L = F.Lab()
        self.idx = L.idx
        tx = L.tx
        self.d = dict(o=L.o, h=L.h, l=L.l, c=L.c, v=tx["volume"].to_numpy(float))
        wk = self.idx.to_period("W-FRI")
        codes, uniq = pd.factorize(wk)
        self.wk_code = codes
        g = tx.groupby(codes)
        self.w = dict(o=g["open"].first().to_numpy(), h=g["high"].max().to_numpy(), l=g["low"].min().to_numpy(),
                      c=g["close"].last().to_numpy(), v=g["volume"].sum().to_numpy(float))
        nxt = np.r_[codes[1:], -1]
        self.last_of_week = nxt != codes
        self.atr = np.nan_to_num(L.atr, nan=1e9)
        self.atr_ok = ~np.isnan(L.atr)
        self.regime40 = L.X["reg"][40]
        v20 = (pd.Series(L.c).pct_change().rolling(20).std() * np.sqrt(252)).to_numpy()
        self.rv20 = v20
        st = L.settle
        self.gates = {
            "S": ~(st | np.append(st[1:], False)),                                  # 結算週：訊號日或進場日是結算日不開新倉
            "JA": ~np.isin(self.idx.month, (7, 8)),                                 # 除權息旺季 7～8 月不開新倉
            "BA": np.isnan(L.X["bas"]) | (L.X["bas"] >= -0.003),                    # 5 日平均基差深度逆價差（< -0.3%）不開新倉
            "RV": np.isnan(v20) | (v20 <= 0.25),                                    # 已實現波動 > 25% 不開新倉（VIX 的替身）
            "BC": np.isnan(L.X["bas"]) | (L.X["bas"] <= 0.0),                       # 反向：只在基差 <= 0（逆價差或平水）時開新倉
        }
        self.sc, self.rc, self.registry = {}, {}, []
        self.vote_names = []
        self.fee_pts = FEE_NTD / MULT

    def state(self, name, tf, p):
        key = (name, tf, tuple(sorted(p.items())))
        if key in self.sc:
            return self.sc[key]
        if name == "VOTE":                                   # 多指標投票：階段 1 日K 前五名（預設參數）至少 m 個同時看多
            s = sum(self.state(n, "D", SPEC[n]["D"]).astype(int) for n in self.vote_names) >= p["m"]
        elif tf == "D":
            s = ind_state(name, self.d, p)
        else:
            sw = ind_state(name, self.w, p)
            code = self.wk_code
            prev = np.r_[False, sw[:-1]]
            s = np.where(self.last_of_week, sw[code], prev[code])
        s = np.asarray(s, bool)
        self.sc[key] = s
        return s

    def spec_state(self, spec):
        s = np.ones(len(self.idx), bool)
        for tf in ("W", "D"):
            comp = spec.get(tf)
            if comp:
                s &= self.state(comp[0], tf, comp[1])
        return s

    def run(self, spec):
        key = json.dumps(spec, sort_keys=True, default=str)
        if key in self.rc:
            return self.rc[key]
        s = self.spec_state(spec) & self.atr_ok
        z = np.zeros(len(s), bool)
        gl = np.ones(len(s), bool)
        for g in spec.get("gates", ()):
            gl &= self.gates[g]
        L = self.lab
        pnl, tr = F._sim(L.o, L.h, L.l, L.c, self.atr, s, z, ~s, z, gl, np.ones(len(s), bool),
                         float(spec.get("k", 99.0)), self.fee_pts, F.TAX, F.SLIP_PTS, F.ROLL_PTS, L.settle)
        prev = np.roll(L.c, 1); prev[0] = L.c[0]
        r = pd.Series(pnl / prev, index=self.idx)
        t = pd.DataFrame(tr, columns=["dir", "sig_i", "entry_i", "exit_i", "entry_px", "exit_px", "reason", "pnl_pts", "mae_pts", "mfe_pts"])
        res = (L.lev_ret(r, 1.0), t)
        self.rc[key] = res
        return res

    def b50(self, a, b=None):
        return F.stats(self.lab.bh_0050(a, b))

    def tx_hold(self, lev=1.0):
        return self.lab.lev_ret(self.lab.bh_tx(), lev)


def sl(r, a, b=None):
    return F.slice_(r, a, b)


def metrics(lab2, spec, a, b=None):
    r, t = lab2.run(spec)
    x = sl(r, a, b); s = F.stats(x)
    ts = F.trade_stats(t, lab2.idx, a, b)
    if len(t):
        ent = lab2.idx[t.entry_i.to_numpy().astype(int)]
        m = (ent >= pd.Timestamp(a)) & ((ent < pd.Timestamp(b)) if b else True)
        days = (t.exit_i - t.entry_i)[m].sum()
    else:
        days = 0
    nd = ((lab2.idx >= a) & ((lab2.idx < b) if b else True)).sum()
    s.update(n=ts["n"], win=ts["win"], payoff=ts["payoff"], hold=ts["hold"], expo=days / max(nd, 1))
    s["vol"] = float(x.std() * np.sqrt(252)) if len(x) > 2 else np.nan
    return s


def regime_table(lab2, r):
    """策略日報酬在三種市況（週K 40 週均線狀態：多頭／空頭／盤整）下的年化貢獻（含空手日＝0）。"""
    R = lab2.regime40
    x = sl(r, SEARCH_START, SEARCH_END); Rr = pd.Series(R, index=lab2.idx).reindex(x.index)
    return {nm: float(x[Rr == code].mean() * 252) for nm, code in (("多頭", 1), ("空頭", -1), ("盤整", 0))}


def reg_add(lab2, phase, label, spec, m):
    lab2.registry.append(dict(階段=phase, 策略=label, 搜尋期年化=m["cagr"], 搜尋期回撤=m["mdd"], 夏普=m["sharpe"], 勝率=m["win"],
                              交易數=m["n"], spec=json.dumps(spec, sort_keys=True, default=str)))


# ------------------------------------------------------------------ 階段 1：單一指標普查
def phase1(lab2):
    a, b = B50_START, SEARCH_END
    b50 = lab2.b50(a, b); txh = F.stats(sl(lab2.tx_hold(), a, b))
    rows = []
    for name, sp in SPEC.items():
        for tf in ("D", "W"):
            if sp[tf] is None:
                continue
            spec = {tf: (name, sp[tf]), "k": 99.0}
            m = metrics(lab2, spec, a, b)
            r, _ = lab2.run(spec)
            rg = regime_table(lab2, r)
            reg_add(lab2, "1 單一指標", pstr(name, tf, sp[tf]), spec, m)
            rows.append(dict(指標=NAMES[name], 代號=name, 週期="日K" if tf == "D" else "週K", 預設參數=",".join(f"{k}={v}" for k, v in sp[tf].items()),
                             年化=m["cagr"], 回撤=m["mdd"], 夏普=m["sharpe"], 勝率=m["win"], 賺賠比=m["payoff"], 交易數=m["n"],
                             持倉比=m["expo"], 多頭貢獻=rg["多頭"], 空頭貢獻=rg["空頭"], 盤整貢獻=rg["盤整"],
                             贏0050=m["cagr"] >= b50["cagr"], 回撤不輸0050=m["mdd"] >= b50["mdd"], _spec=spec, _tf=tf, _name=name))
    df = pd.DataFrame(rows)
    rt = regime_table(lab2, lab2.tx_hold())
    return df, b50, txh, rt


# ------------------------------------------------------------------ 階段 2：消息面／濾網
def phase2(lab2, bases):
    a, b = B50_START, SEARCH_END
    rows = []
    for gname, gdesc in (("S", "結算週不開新倉"), ("JA", "7～8 月（除權息旺季）不開新倉"), ("BA", "基差深度逆價差(<-0.3%)不開新倉"),
                         ("RV", "已實現波動>25% 不開新倉（VIX 替身）"), ("BC", "只在基差<=0 時開新倉（逆價差逆向）")):
        better = 0; d_cagr = []; d_mdd = []; d_win = []
        for bs in bases:
            m0 = metrics(lab2, bs["_spec"], a, b)
            sp = dict(bs["_spec"]); sp["gates"] = (gname,)
            m1 = metrics(lab2, sp, a, b)
            reg_add(lab2, "2 消息面濾網", f"{bs['代號']}[{bs['週期']}]+{gname}", sp, m1)
            c0 = m0["cagr"] / max(abs(m0["mdd"]), 1e-6); c1 = m1["cagr"] / max(abs(m1["mdd"]), 1e-6)
            better += c1 > c0
            d_cagr.append(m1["cagr"] - m0["cagr"]); d_mdd.append(m1["mdd"] - m0["mdd"]); d_win.append((m1["win"] or 0) - (m0["win"] or 0))
        rows.append(dict(濾網=gname, 說明=gdesc, 變好比例=f"{better}/{len(bases)}", 平均年化變化=np.mean(d_cagr), 平均回撤變化=np.mean(d_mdd),
                         平均勝率變化=np.mean(d_win), 採用=better > len(bases) / 2))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ 階段 3：組合與優化
def build_space(lab2, wnames, dnames, gate_opts):
    """回傳所有組合 spec：W 選項 x D 選項 x 濾網 x 停損倍數。(W,D) 不得同為 None。"""
    wopts = [None] + [(n, p) for n in wnames for p in grid_of(SPEC[n]["gW"])]
    dopts = [None] + [(n, p) for n in dnames for p in grid_of(SPEC[n]["gD"])]
    out = []
    for w in wopts:
        for d in dopts:
            if w is None and d is None:
                continue
            for g in gate_opts:
                for k in (3.0, 5.0, 99.0):
                    out.append(dict(W=w, D=d, gates=tuple(g), k=k))
    return out, wopts, dopts


def spec_label(sp):
    parts = []
    for tf in ("W", "D"):
        if sp.get(tf):
            parts.append(pstr(sp[tf][0], tf, sp[tf][1]))
    return " & ".join(parts) + (f" | 濾網{'+'.join(sp['gates'])}" if sp.get("gates") else "") + f" | 停損{sp['k']:g}ATR"


def score(lab2, spec, t0, a):
    c0 = max(pd.Timestamp(t0), pd.Timestamp(B50_START)).strftime("%Y-%m-%d")
    m = metrics(lab2, spec, c0, a); b = lab2.b50(c0, a)
    return (m["cagr"] if m["mdd"] >= b["mdd"] else -1 + m["mdd"])


def select(lab2, space, t0, a):
    best, bs = None, -9
    for sp in space:
        sc = score(lab2, sp, t0, a)
        if sc > bs:
            best, bs = sp, sc
    return best, bs


def wf(lab2, space):
    ends = WF_TEST[1:] + [HOLDOUT]
    rows, parts = [], []
    for a, b in zip(WF_TEST, ends):
        sp, tr = select(lab2, space, SEARCH_START, a)
        m = metrics(lab2, sp, a, b); bb = lab2.b50(a, b)
        rows.append(dict(a=a, b=b, spec=sp, train=tr, cagr=m["cagr"], mdd=m["mdd"], b50=bb["cagr"], b50mdd=bb["mdd"],
                         beat=m["cagr"] >= bb["cagr"], n=m["n"]))
        parts.append(sl(lab2.run(sp)[0], a, b))
    return rows, pd.concat(parts)


def neighbors(sp, wopts, dopts, gate_opts):
    """只動一個維度、相鄰一格：W 或 D 的單一參數 ±1 格、停損倍數 ±1 格、濾網組合 ±1 格。"""
    res = []

    def adj(opts, cur, spname, tf):
        if cur is None:
            return []
        name, p = cur
        out = []
        g = SPEC[name]["g" + tf]
        for key, vals in g.items():
            if p[key] not in vals:
                continue
            i = vals.index(p[key])
            for j in (i - 1, i + 1):
                if 0 <= j < len(vals):
                    q = dict(p); q[key] = vals[j]
                    out.append((name, q))
        return out
    for tf in ("W", "D"):
        for c in adj(None, sp.get(tf), None, tf):
            q = dict(sp); q[tf] = c; res.append(q)
    ks = [3.0, 5.0, 99.0]; i = ks.index(sp["k"])
    for j in (i - 1, i + 1):
        if 0 <= j < 3:
            q = dict(sp); q["k"] = ks[j]; res.append(q)
    gl = [tuple(g) for g in gate_opts]; i = gl.index(tuple(sp["gates"]))
    for j in (i - 1, i + 1):
        if 0 <= j < len(gl):
            q = dict(sp); q["gates"] = gl[j]; res.append(q)
    return res


def neigh_check(lab2, sp, wopts, dopts, gate_opts):
    b = lab2.b50(B50_START, SEARCH_END)
    nb = neighbors(sp, wopts, dopts, gate_opts)
    res = [metrics(lab2, q, B50_START, SEARCH_END) for q in nb]
    if not res:
        return np.nan, np.nan, 0
    return (float(np.mean([m["cagr"] >= b["cagr"] for m in res])),
            float(np.mean([m["cagr"] >= b["cagr"] and m["mdd"] >= b["mdd"] for m in res])), len(res))


def default_version(sp):
    """預設參數版：同樣的指標與濾網結構，指標參數換回教科書預設，停損 3 ATR。"""
    d = dict(sp); d["k"] = 3.0
    for tf in ("W", "D"):
        if sp.get(tf):
            d[tf] = (sp[tf][0], dict(SPEC[sp[tf][0]][tf]))
    return d


# ------------------------------------------------------------------ 槓桿附表（保證金模擬）與保留期
def tgt_from_trades(lab2, spec, lev):
    _, t = lab2.run(spec)
    tgt = np.zeros(len(lab2.idx))
    for e, x in zip(t.entry_i.astype(int), t.exit_i.astype(int)):
        tgt[e - 1:max(e, x - 1)] = lev        # 訊號持有區間；停損改在停損日開盤出（近似，README 註明）
    return tgt


def lev_run(lab2, spec, lev):
    L = lab2.lab
    tgt = tgt_from_trades(lab2, spec, lev)
    r, q, liq = _sim_lev(L.o, L.h, L.l, L.c, tgt, L.settle, FEE_NTD, SLIP, TAX, ROLL_PTS, M_INIT, M_MAINT, BAND, F.CASH_Y / F.PPY, E0)
    return pd.Series(r, index=lab2.idx), liq


def lev_table(lab2, spec, a, b=None):
    rows = []
    for lev in (1, 2, 3):
        r, liq = lev_run(lab2, spec, lev)
        s = F.stats(sl(r, a, b)); m = (lab2.idx >= a) & ((lab2.idx < b) if b else True)
        rows.append(dict(槓桿=f"{lev} 倍", 年化=s["cagr"], 最大回撤=s["mdd"], 夏普=s["sharpe"], 強平次數=int(liq[m].sum())))
    return pd.DataFrame(rows)


def final_holdout(lab2, specs: dict):
    """最終保留期（2019-01-01 起）：只准跑一次。specs = {名稱: spec}，同一次算完（優化版／預設版／對照）。"""
    lock = OUT / "_holdout_done.json"
    if lock.exists():
        raise RuntimeError("保留期已經跑過一次，依規則不得再跑：" + lock.read_text(encoding="utf-8")[:200])
    b = F.stats(lab2.lab.bh_0050(HOLDOUT)); txh = F.stats(sl(lab2.tx_hold(), HOLDOUT))
    res = {"0050": b, "台指期持有1倍": txh, "策略": {}}
    for nm, sp in specs.items():
        m = metrics(lab2, sp, HOLDOUT)
        lt = lev_table(lab2, sp, HOLDOUT)
        res["策略"][nm] = dict(label=spec_label(sp), m=m, 通過=bool(m["cagr"] > b["cagr"] and m["mdd"] >= b["mdd"]),
                              槓桿=lt.to_dict("records"))
    OUT.mkdir(parents=True, exist_ok=True)
    lock.write_text(json.dumps(res, ensure_ascii=False, default=float), encoding="utf-8")
    return res


# ------------------------------------------------------------------ 逐筆筆記
def notes_table(lab2, spec, a, b=None, tag=""):
    L = lab2.lab
    _, t = lab2.run(spec)
    net = F.foreign_net_oi(lab2.idx); chg = net - net.shift(5)
    rows = []
    desc = " & ".join(f"{'週K' if tf == 'W' else '日K'}{NAMES[spec[tf][0]]}({','.join(f'{k}={v}' for k, v in spec[tf][1].items())})多方"
                      for tf in ("W", "D") if spec.get(tf))
    for _, x in t.iterrows():
        ei, xi, si = int(x.entry_i), int(x.exit_i), int(x.sig_i)
        ed = lab2.idx[ei]
        if ed < pd.Timestamp(a) or (b and ed >= pd.Timestamp(b)):
            continue
        hold = (lab2.idx[xi] - ed).days
        ch = chg.iloc[si]
        chip_s = "無資料" if np.isnan(ch) else ("順向" if ch > 0 else ("反向" if ch < 0 else "持平"))
        sw = "是" if not lab2.gates["S"][si] else "否"
        R = lab2.regime40[si]
        give = (1 - x.pnl_pts / x.mfe_pts) if x.mfe_pts > 0 and x.pnl_pts > 0 else np.nan
        bas = L.X["bas"][si]
        rows.append(dict(
            版本=tag, 進場日=ed.date(), 進場價=round(x.entry_px, 1), 出場日=lab2.idx[xi].date(), 出場價=round(x.exit_px, 1),
            出場原因=F.REASON[int(x.reason)], 損益點=round(x.pnl_pts, 1), 損益元每口=round(x.pnl_pts * MULT),
            報酬率_名義=round(x.pnl_pts / x.entry_px, 4), 持有天數=hold, 最大不利偏移點=round(x.mae_pts, 1),
            最大不利偏移_pct=round(x.mae_pts / x.entry_px, 4), 最大有利偏移點=round(x.mfe_pts, 1),
            大格局40週=("多頭" if R == 1 else "空頭" if R == -1 else "盤整"), 進場理由=desc,
            基差5日pct=None if np.isnan(bas) else round(float(bas) * 100, 3), 外資期貨5日變化口=None if np.isnan(ch) else int(ch),
            籌碼=chip_s, 結算週=sw, 事後檢討=F.review(x, 1, hold, chip_s, sw, give, R)))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ 主流程
def run_search(lab2):
    df, b50, txh, rt = phase1(lab2)
    dw = df[df._tf == "D"].sort_values("夏普", ascending=False).head(5)
    ww = df[df._tf == "W"].sort_values("夏普", ascending=False).head(3)
    bases = [r for _, r in pd.concat([dw, ww]).iterrows()]
    p2 = phase2(lab2, bases)
    acc = [g for g, a in zip(p2.濾網, p2.採用) if a]
    gate_opts = [()] + [(g,) for g in acc] + ([tuple(acc)] if len(acc) > 1 else [])
    wn, dn = list(ww.代號), list(dw.代號)
    lab2.vote_names = dn
    space, wo, do = build_space(lab2, wn, dn + ["VOTE"], gate_opts)
    rows, oos = wf(lab2, space)
    ch, sc = select(lab2, space, SEARCH_START, SEARCH_END)
    for sp in space:                      # 登記階段 3 所有試過的組合
        m = metrics(lab2, sp, B50_START, SEARCH_END)
        reg_add(lab2, "3 組合優化", spec_label(sp), sp, m)
    nb = neigh_check(lab2, ch, wo, do, gate_opts)
    dv = default_version(ch)
    # 演進表
    s1 = df.sort_values("夏普", ascending=False).iloc[0]
    sp1 = s1["_spec"]
    sp2 = dict(sp1); sp2["gates"] = tuple(acc)
    evo = [("階段1 最佳單一指標（預設參數、無停損）", sp1, "加了：—（單一指標 %s）" % pstr(s1["_name"], s1["_tf"], SPEC[s1["_name"]][s1["_tf"]])),
           ("階段2 + 消息面濾網", sp2, f"加了：濾網 {'+'.join(acc) if acc else '（無通過者）'}（基差<=0 才開新倉等）"),
           ("階段3 多指標組合（預設參數）", dv, "加了：週K 方向 + 日K 進場 + 濾網 + 3 ATR 停損，參數教科書預設"),
           ("階段3 多指標組合（優化參數）", ch, "加了：2001～2018 網格優化指標參數、停損倍數")]
    return dict(df=df, b50=b50, txh=txh, rt=rt, p2=p2, acc=acc, space_n=len(space), wo=wo, do=do, gate_opts=gate_opts,
                wf_rows=rows, wf_oos=oos, champ=ch, nb=nb, default=dv, evo=evo, bases=bases, wn=wn, dn=dn, s1=s1)


def main(do_holdout=False):
    OUT.mkdir(parents=True, exist_ok=True)
    lab2 = Lab2()
    R = run_search(lab2)
    ch = R["champ"]
    wins = sum(r["beat"] for r in R["wf_rows"])
    print("WF 贏段", wins, "/", len(R["wf_rows"]), "鄰域", R["nb"], "冠軍", spec_label(ch))
    print("優化版搜尋期", metrics(lab2, ch, B50_START, SEARCH_END))
    print("預設版搜尋期", metrics(lab2, R["default"], B50_START, SEARCH_END))
    print("搜尋期 0050", R["b50"], "登記組數", len(lab2.registry), "不重複回測", len(lab2.rc))
    pd.DataFrame(lab2.registry).drop_duplicates(subset=["階段", "策略"]).to_csv(OUT / "registry.csv", index=False, encoding="utf-8-sig")
    if not do_holdout:
        return lab2, R, None
    lock = OUT / "_holdout_done.json"
    if lock.exists():
        H = json.loads(lock.read_text(encoding="utf-8"))
    else:
        specs = {"優化版": ch, "預設參數版": R["default"]}
        for i, (nm, sp, _) in enumerate(R["evo"][:2]):
            specs[nm] = sp
        H = final_holdout(lab2, specs)
    write_docs(lab2, R, H)
    return lab2, R, H


def fp(x, d=1):
    return F.fmt(x, True, d)


def md(df):
    h = "| " + " | ".join(map(str, df.columns)) + " |\n|" + "---|" * len(df.columns) + "\n"
    return h + "\n".join("| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False)) + "\n"


def write_docs(lab2, R, H):
    b50s, txs = R["b50"], R["txh"]
    ch, dv = R["champ"], R["default"]
    wins = sum(r["beat"] for r in R["wf_rows"]); nseg = len(R["wf_rows"])
    gate1 = wins > nseg / 2; gate2 = R["nb"][2] > 0 and R["nb"][0] >= 2 / 3
    hb = H["0050"]; ht = H["台指期持有1倍"]
    S = H["策略"]
    assert S["優化版"]["label"] == spec_label(ch), "鎖檔中的候選與目前搜尋結果不同，拒絕產生文件"
    names = list(S)
    # 已知缺陷（保留期跑完後才發現，依規則不回頭改搜尋與保留期）：VOTE 被誤放進階段 1 普查，且因零交易、報酬為常數，
    # 夏普分母趨近 0 而排第一，導致 (a) 日K 前五名被它佔掉一格（NHI 被擠出）；(b) 階段 2 的 8 個基底有 1 個是退化的。
    # 這裡的顯示層改用「排除 VOTE 後」的真正最佳單一指標，且只列搜尋期數字（保留期已鎖，不再為它們新增揭露）。
    df = R["df"][R["df"]["代號"] != "VOTE"].copy()
    s1 = df.sort_values("夏普", ascending=False).iloc[0]
    sp1 = s1["_spec"]; sp2 = dict(sp1); sp2["gates"] = tuple(R["acc"])
    R["evo"] = [("階段1 最佳單一指標（預設參數、無停損）", sp1, "加了：—（單一指標 %s）" % pstr(s1["_name"], s1["_tf"], SPEC[s1["_name"]][s1["_tf"]])),
                ("階段2 + 消息面濾網", sp2, f"加了：濾網 {'+'.join(R['acc'])}（只在基差 <= 0 時開新倉）"),
                R["evo"][2], R["evo"][3]]
    ms = {nm: metrics(lab2, spec, B50_START, SEARCH_END) for nm, spec in
          zip(["優化版", "預設參數版", "S1", "S2"], [ch, dv, sp1, sp2])}
    opt, dfl = S["優化版"], S["預設參數版"]
    gate3 = opt["通過"]
    champ_ok = gate1 and gate2 and gate3
    def verdict(nm, is_opt=False):
        s = S[nm]; m = s["m"]
        if s["通過"]:
            return ("**冠軍**（三關全過）" if (is_opt and champ_ok) else ("保留期達標，但搜尋期關卡未全過，不是冠軍" if is_opt else "保留期達標（未過搜尋期關卡，不是冠軍）"))
        why = []
        if m["cagr"] <= hb["cagr"]:
            why.append("保留期年化輸 0050")
        if m["mdd"] < hb["mdd"]:
            why.append("保留期回撤比 0050 差")
        return "**淘汰**：" + "、".join(why)
    rows = []
    def add(label, nm, is_opt=False):
        s = S[nm]; m = s["m"]; sm = ms[nm]
        rows.append({"候選": label, "搜尋期年化": fp(sm["cagr"]), "搜尋期0050": fp(b50s["cagr"]), "搜尋期回撤": fp(sm["mdd"]),
                     "保留期年化": fp(m["cagr"]), "保留期0050": fp(hb["cagr"]), "差距": f"{(m['cagr'] - hb['cagr']) * 100:+.1f} 點",
                     "保留期回撤": fp(m["mdd"]), "0050回撤": fp(hb["mdd"]), "保留期勝率": fp(m["win"], 0), "保留期交易數": int(m["n"]),
                     "判定": verdict(nm, is_opt)})
    add("階段3 優化版（冠軍候選）", "優化版", True)
    add("階段3 預設參數版", "預設參數版")
    for lab_, key in (("階段2 最佳單一指標＋濾網", "S2"), ("階段1 最佳單一指標", "S1")):
        sm = ms[key]
        rows.append({"候選": lab_ + "（僅搜尋期）", "搜尋期年化": fp(sm["cagr"]), "搜尋期0050": fp(b50s["cagr"]), "搜尋期回撤": fp(sm["mdd"]),
                     "保留期年化": "未跑", "保留期0050": fp(hb["cagr"]), "差距": "-", "保留期回撤": "未跑", "0050回撤": fp(hb["mdd"]),
                     "保留期勝率": "-", "保留期交易數": "-", "判定": "**淘汰**：搜尋期年化輸 0050，不進保留期"})
    tab0 = pd.DataFrame(rows)
    n_lose = int((~df["贏0050"]).sum())
    L = []
    L.append("# 台指期第二輪：單一指標 -> 消息面 -> 多指標組合優化（1 倍曝險、只做多）\n")
    L.append("> **免責**：歷史資料的研究回測，非買賣建議、不下單。淘汰規則沿用 Andy 的：年化輸同期含息扣成本的 0050 -> 淘汰；本輪另加「最大回撤不得比 0050 差」。"
             "搜尋、選參、優化全部只用 2001～2018；2019-01-01 起是最終保留期，**只跑了一次**（鎖檔 `_holdout_done.json`），跑完沒有回頭改任何東西。\n")
    L.append("> **誠實揭露**：第一輪已看過 2013～2026 整體結果（含 2019 以後的 V 型反彈錯過），保留期不是真正沒看過的資料；本輪沒有用它調整設計，但這個污染存在。\n")
    L.append("## 〇、通過／淘汰清單\n")
    L.append(f"保留期（2019-01-01 至資料尾）：0050 含息扣成本年化 {fp(hb['cagr'])}、最大回撤 {fp(hb['mdd'])}；台指期永遠持有（1 倍）年化 {fp(ht['cagr'])}、最大回撤 {fp(ht['mdd'])}。"
             f"搜尋期（2003-07～2018）：0050 年化 {fp(b50s['cagr'])}、最大回撤 {fp(b50s['mdd'])}；台指期持有 {fp(txs['cagr'])}、{fp(txs['mdd'])}。\n")
    L.append(md(tab0))
    L.append(f"\n冠軍三關：關卡 1 搜尋期 walk-forward 多數段贏 0050：**{wins}/{nseg} 段**（{'過' if gate1 else '未過'}）；"
             f"關卡 2 參數鄰域 >= 2/3 贏 0050 年化：**{fp(R['nb'][0], 0)}**（{R['nb'][2]} 個鄰居；{'過' if gate2 else '未過'}）；"
             f"關卡 3 保留期年化高於 0050 且回撤不輸：{'過' if gate3 else '未過'}。**結論：{'有冠軍' if champ_ok else '沒有冠軍，全數淘汰'}。**\n")
    L.append(f"階段 1 普查的 {len(df)} 個有效單一指標（日K／週K）在搜尋期**全部**年化低於 0050（{n_lose}/{len(df)}）——但回撤普遍遠小於 0050（0050 含 2008 年 {fp(b50s['mdd'])}），"
             "所以它們是防禦工具、不是報酬增強工具。完整表見第二節。\n")
    L.append("## 一、三階段演進表（每階段加了什麼、為什麼、數字變多少）\n")
    ev = []
    prev = None
    why = ["普查 23 種指標 x 日K／週K，每個指標用教科書預設參數、不設停損，先看誰的風險調整後報酬最好（夏普最高者進下一階段）。",
           "疊加台灣可驗證的消息／籌碼面濾網（結算週、7～8 月除權息旺季、基差、已實現波動替身 VIX、基差逆向）；『變好比例』過半才採用，事先定好。",
           "週K 定方向 + 日K 進場 + 濾網 + 3 ATR 停損，參數仍是教科書預設：驗證『組合』本身有沒有用。",
           "對組合的所有參數（指標參數、停損倍數、濾網組合）在 2001～2018 網格優化（含 W/D 指標選擇與多指標投票）；接受過擬合探索，但只在搜尋期。"]
    for i, (nm, spec, desc) in enumerate(R["evo"]):
        m = metrics(lab2, spec, B50_START, SEARCH_END)
        key = nm
        hk = {2: "預設參數版", 3: "優化版"}.get(i)
        hm = S[hk]["m"] if hk else None
        d_c = "-" if prev is None else f"{(m['cagr'] - prev['cagr']) * 100:+.1f} 點"
        d_d = "-" if prev is None else f"{(m['mdd'] - prev['mdd']) * 100:+.1f} 點"
        d_w = "-" if prev is None else f"{((m['win'] or 0) - (prev['win'] or 0)) * 100:+.1f} 點"
        ev.append({"階段": nm, "加了什麼": desc, "為什麼": why[i], "搜尋期年化": fp(m["cagr"]), "年化變化": d_c, "搜尋期回撤": fp(m["mdd"]),
                   "回撤變化": d_d, "勝率": fp(m["win"], 0), "勝率變化": d_w, "交易數": m["n"],
                   "保留期年化": fp(hm["cagr"]) if hm else "未跑", "保留期回撤": fp(hm["mdd"]) if hm else "未跑"})
        prev = m
    L.append(md(pd.DataFrame(ev)))
    L.append("參數怎麼選的：階段 3 優化版 = " + spec_label(ch) + "；預設版 = " + spec_label(dv) + "。\n")
    eo_s = ms["優化版"]["cagr"] - b50s["cagr"]; eo_h = opt["m"]["cagr"] - hb["cagr"]
    ed_s = ms["預設參數版"]["cagr"] - b50s["cagr"]; ed_h = dfl["m"]["cagr"] - hb["cagr"]
    L.append(f"**過擬合程度一眼看**（保留期是大多頭，絕對年化比搜尋期高不代表策略變好，所以看『相對 0050 的差距』）："
             f"優化版相對 0050：搜尋期 {eo_s * 100:+.1f} 點 -> 保留期 {eo_h * 100:+.1f} 點；預設參數版：搜尋期 {ed_s * 100:+.1f} 點 -> 保留期 {ed_h * 100:+.1f} 點。"
             f"優化讓搜尋期多 {(ms['優化版']['cagr'] - ms['預設參數版']['cagr']) * 100:+.1f} 點，保留期多 {(opt['m']['cagr'] - dfl['m']['cagr']) * 100:+.1f} 點——"
             "優化幾乎沒有帶來可帶出樣本的額外報酬（也沒有明顯過擬合，因為本來能優化的空間就小）；兩版共同的問題是都大幅輸給 0050。\n")
    L.append("## 二、階段 1：單一指標普查（搜尋期 2003-07～2018，1 倍、扣成本、無停損）\n")
    L.append(f"『多頭／空頭／盤整貢獻』= 週K 40 週均線狀態（延後一週，無前視）分類後，策略在該類日子的年化平均報酬（含空手日＝0）。台指期持有的對照：多頭 {fp(R['rt']['多頭'])}、空頭 {fp(R['rt']['空頭'])}、盤整 {fp(R['rt']['盤整'])}"
             "（空頭標籤日之後的報酬為正，是因為標籤落後，急殺後的反彈日被歸在『空頭』）。\n")
    t1 = df.sort_values("夏普", ascending=False).copy()
    for c in ("年化", "回撤", "勝率", "持倉比", "多頭貢獻", "空頭貢獻", "盤整貢獻"):
        t1[c] = t1[c].map(fp)
    t1["夏普"] = t1["夏普"].map(lambda x: f"{x:.2f}"); t1["賺賠比"] = t1["賺賠比"].map(lambda x: f"{x:.2f}")
    t1["贏0050"] = t1["贏0050"].map(lambda x: "是" if x else "否"); t1["回撤不輸0050"] = t1["回撤不輸0050"].map(lambda x: "是" if x else "否")
    L.append(md(t1.drop(columns=["代號", "_spec", "_tf", "_name"])))
    L.append("進入階段 2 的是日K 夏普前 5 名與週K 前 3 名（事先定好的規則）：" + "、".join(f"{b['代號']}[{b['週期']}]" for b in R["bases"] if b['代號'] != 'VOTE') + "。\n")
    L.append("> **已知缺陷（保留期跑完後才發現，依規則沒有回頭重跑）**：普查表誤含一列「多指標投票 VOTE」（零交易、報酬為常數），其夏普因分母趨近 0 排第一，"
             "佔掉日K 前五名的一格（原本第 5 名 NHI 因此沒進階段 3 的組合空間），並使階段 2 的 8 個基底中有 1 個是退化的。後果：(1) 階段 2 的『變好比例』分母多 1，"
             "7～8 月濾網 JA 實際是 4/7（過半，本應採用）卻被判 4/8 不採用——**JA 沒被測**；(2) NHI 沒進組合空間。"
             "這些只影響『搜尋範圍』，冠軍候選仍完全由 2001～2018 選出，保留期結果有效；但下一輪應補測 JA 與 NHI。本表因此排除該列，共 " + str(len(df)) + " 個有效單一指標。\n")
    L.append("## 三、階段 2：消息面與濾網（疊加在上述 8 個指標上；搜尋期）\n")
    p2 = R["p2"].copy()
    for c in ("平均年化變化", "平均回撤變化", "平均勝率變化"):
        p2[c] = p2[c].map(lambda x: f"{x * 100:+.2f} 點")
    p2["採用"] = p2["採用"].map(lambda x: "採用" if x else "不採用")
    L.append(md(p2))
    L.append("『變好比例』= 加濾網後 Calmar（年化／回撤）變高的指標數，過半才採用。\n")
    L.append("**美股與其他消息面——資料抓不到，沒有驗證**：\n")
    L.append("| 項目 | 狀態 | 說明 |\n|---|---|---|\n"
             "| S&P 500、Nasdaq、費半、VIX、美元指數、台積電 ADR | **未驗證** | 資料湖 `intl_daily` 只有 2024-10 起，搜尋期（2001～2018）完全沒有；此容器對 Yahoo、FinMind、FRED 的出口被代理擋下（HTTP 403），無法補抓。已寫好回補腳本 `scripts/backfill_futlab2_data.py`（走 `store.append()`，**未能在本容器執行，未驗證**），需在有網路的環境或 Actions 執行。 |\n"
             "| 美債殖利率 | 部分 | `macro` 的 DGS10／T10Y2Y 只有 2015 起（搜尋期只覆蓋 2015～2018，約 4 年），不足以驗證。 |\n"
             "| 外資期貨淨部位、三大法人 | 僅 2021 後 | `fut_inst` 2021-01 起，全落在保留期；FinMind 該資料集據文件約 2018 年中起，無法涵蓋 2008（未驗證）。 |\n"
             "| 選擇權 P/C 比 | 無資料 | 資料湖沒有；期交所歷史資料需申請。 |\n"
             "| 事件日（FOMC、CPI、財報季） | 無歷史 | `macro_calendar` 只有 2026 年 27 筆未來事件；FOMC 日期表資料湖沒有。結算日與 7～8 月以規則推得，已測。 |\n"
             "| 台指期夜盤 | 2017-05 起 | `index_ohlc` 的 FUT_N；搜尋期僅 1.6 年，不足。 |\n")
    L.append("## 四、階段 3：組合與優化\n")
    L.append(f"組合空間共 {R['space_n']} 組（週K 選項 x 日K 選項 x 濾網組合 x 停損 3／5／無）。walk-forward：訓練窗從 2001-01-02 起擴張，測試窗 2008–2010、2011–2013、2014–2016、2017–2018；每段只用之前資料選參，選參要求訓練期回撤不比 0050 差。\n")
    wrows = pd.DataFrame([dict(測試窗=f"{r['a']}～{r['b']}", 選到的組合=spec_label(r["spec"]), 訓練期年化=fp(r["train"]), 測試年化=fp(r["cagr"]),
                              同窗0050=fp(r["b50"]), 測試回撤=fp(r["mdd"]), **{"0050回撤": fp(r["b50mdd"])}, 交易數=r["n"],
                              勝負="贏" if r["beat"] else "輸") for r in R["wf_rows"]])
    L.append(md(wrows))
    L.append(f"串接後（2008～2018）年化 {fp(F.stats(R['wf_oos'])['cagr'])}、回撤 {fp(F.stats(R['wf_oos'])['mdd'])}；同窗 0050 年化 {fp(lab2.b50('2008-01-01', HOLDOUT)['cagr'])}、回撤 {fp(lab2.b50('2008-01-01', HOLDOUT)['mdd'])}。\n")
    L.append(f"參數鄰域（優化版只動一個維度、相鄰一格，共 {R['nb'][2]} 個）：贏 0050 年化的比例 {fp(R['nb'][0], 0)}、年化與回撤都贏 {fp(R['nb'][1], 0)}。\n")
    L.append("## 五、槓桿附表（不是手段，只是對照；保證金：原始 10%／維持 8%，每日最不利價檢查，跌破即強制平倉）\n")
    for nm in ("優化版", "預設參數版"):
        lt = pd.DataFrame(S[nm]["槓桿"])
        for c in ("年化", "最大回撤"):
            lt[c] = lt[c].map(fp)
        lt["夏普"] = lt["夏普"].map(lambda x: f"{x:.2f}")
        L.append(f"**{nm}（保留期）**\n\n" + md(lt))
    lt = lev_table(lab2, ch, B50_START, SEARCH_END)
    for c in ("年化", "最大回撤"):
        lt[c] = lt[c].map(fp)
    lt["夏普"] = lt["夏普"].map(lambda x: f"{x:.2f}")
    L.append("**優化版（搜尋期）**\n\n" + md(lt))
    L.append("附表以訊號持有區間近似（ATR 停損改在停損日開盤出場），1 倍列與主表略有差異屬正常。\n")
    L.append("## 六、出處（上網查到的文獻與資料）\n")
    L.append("| 主題 | 來源類別 | 出處 | 取用的點 |\n|---|---|---|---|\n"
             "| 波動目標部位 | 學術 | [Moreira & Muir, Volatility-Managed Portfolios, JF 2017 (NBER w22208)](https://www.nber.org/papers/22208) | 高波動降曝險可提高夏普；但 Cederburg 等 2020 年複驗認為樣本外並不穩定——故本輪只把已實現波動當濾網，不當主軸。 |\n"
             "| 趨勢跟隨＋波動調整 | 業界 | [Invesco：Navigating Momentum](https://invesco.com/content/dam/invesco/emea/en/pdf/RRE_2024_Q2_NavigatingMomentum.pdf)、[Swedroe：Trend Following As Insurance](https://www.etf.com/sections/index-investor-corner/swedroe-trend-following-insurance) | 趨勢跟隨的價值在降低回撤（與本輪『回撤遠小於 0050』一致），不在提高報酬。 |\n"
             "| 隔夜／日盤報酬 | 學位論文 | [中央大學 2022：隔夜與日內報酬（Lou et al. 方法）](https://www.airitilibrary.com/Article/Detail/U0020-1307202219594600)、[中央大學：台指期日盤報酬與夜盤、美股](https://etd.lib.ncu.edu.tw/thesis/detail/9f4013a8feb582c833dd3a53a7c710ec) | 夜盤報酬與日盤報酬負相關；本輪資料湖無夜盤歷史，只能用開盤跳空近似，未納入策略。 |\n"
             "| 結算日與除權息 | 財經媒體／學位論文 | [CMoney：結算日行為統計](https://www.cmoney.tw/notes/note-detail.aspx?nid=51494)、[CMoney：6 月結算 7 月合約逆價差 206 點](https://www.cmoney.tw/notes/note-detail.aspx?nid=56768)、[台大論文：結算價改制後結算日波動](https://tdr.lib.ntu.edu.tw/handle/123456789/62926?locale=en) | 除息旺季（6 月中～8 月底）期貨逆價差擴大、結算日易殺尾盤——據此測 7～8 月、結算週濾網與基差濾網。 |\n"
             "| 保證金 | 官方／媒體 | [期交所保證金頁](https://www.taifex.com.tw/cht/5/indexMarging)、[鉅亨：保證金調整紀錄](https://hao.cnyes.com/post/141707) | TX 原始保證金 2021-02 167,000、2024-11 338,000、2025-03 307,000；以名義 5～12% 為範圍，採保守 10%／8%。 |\n")
    L.append("## 七、試了幾組\n")
    reg = pd.read_csv(OUT / "registry.csv")
    L.append(f"- 登記於 `registry.csv`：階段 1 {int((reg['階段'] == '1 單一指標').sum())} 組、階段 2 {int((reg['階段'] == '2 消息面濾網').sum())} 組、階段 3 {int((reg['階段'] == '3 組合優化').sum())} 組，共 {len(reg)} 組。\n"
             "- 階段 3 的組合空間是在看到階段 1／2 結果後才定義（誰進階段 3、哪些濾網採用），選擇規則（夏普前 N、變好比例過半）事先寫死；但『要做哪三個階段、加投票指標』是看過第一輪結果後決定的。\n"
             "- 階段 1 的 8 個進階指標與階段 3 的冠軍都在同一個搜尋期內選出，多重比較未做校正；因此冠軍必須再過 walk-forward、鄰域與保留期三關。\n")
    L.append("## 八、結論與下一步\n")
    L.append(CONCLUSION(lab2, R, H, champ_ok, gate1, gate2, gate3))
    L.append("## 九、重現\n\n`python -m pipeline.compute.futures_lab2`（只跑搜尋期，約 1 分鐘）；`--holdout` 才會跑保留期（已跑過，鎖檔存在時直接讀鎖檔結果）。測試：`pytest tests/test_futures_lab2.py -q`。\n")
    (OUT / "README.md").write_text("\n".join(L), encoding="utf-8")
    # 逐筆筆記
    N = ["# 台指期第二輪交易筆記（優化版與預設參數版，搜尋期與保留期分開）\n",
         "每筆含進場理由、出場原因、損益、最大不利偏移、事後檢討（規則式自動產生，彙整見 README 第八節）。"
         "大格局 = 週K 40 週均線狀態；基差、外資期貨（2021 後才有）、結算週僅為紀錄，不一定是該版本的條件。\n"]
    csv_all = []
    for nm, spec in (("優化版", ch), ("預設參數版", dv)):
        for per, (a, b) in (("搜尋期 2001～2018", (SEARCH_START, HOLDOUT)), ("保留期 2019 起", (HOLDOUT, None))):
            t = notes_table(lab2, spec, a, b, tag=f"{nm}/{per}")
            csv_all.append(t)
            N.append(f"\n## {nm} - {per}（{len(t)} 筆）\n\n策略：{spec_label(spec)}\n")
            for _, r in t.iterrows():
                N.append(f"- **{r['進場日']}** 進 {r['進場價']} -> {r['出場日']} 出 {r['出場價']}（{r['出場原因']}，持有 {r['持有天數']} 天）｜損益 {r['損益點']} 點（每口 {r['損益元每口']:,} 元，名義 {r['報酬率_名義']:.2%}）｜"
                         f"MAE {r['最大不利偏移點']} 點（{r['最大不利偏移_pct']:.2%}）｜進場理由：{r['進場理由']}；大格局 {r['大格局40週']}、基差 {r['基差5日pct']}%、外資期貨 {r['籌碼']}、結算週 {r['結算週']}｜**檢討**：{r['事後檢討']}")
    pd.concat(csv_all).to_csv(OUT / "trades_round2.csv", index=False, encoding="utf-8-sig")
    (OUT / "trades_notes_round2.md").write_text("\n".join(N), encoding="utf-8")


def CONCLUSION(lab2, R, H, champ_ok, g1, g2, g3):
    S = H["策略"]; hb = H["0050"]; o = S["優化版"]["m"]; d = S["預設參數版"]["m"]
    t_o = notes_table(lab2, R["champ"], SEARCH_START, HOLDOUT)
    t_h = notes_table(lab2, R["champ"], HOLDOUT, None)
    lines = [f"- 保留期（只跑一次）：優化版年化 {fp(o['cagr'])}／回撤 {fp(o['mdd'])}，預設版 {fp(d['cagr'])}／{fp(d['mdd'])}，0050 {fp(hb['cagr'])}／{fp(hb['mdd'])}。"
             + ("有冠軍。" if champ_ok else "沒有冠軍：與第一輪同一個原因——1 倍多頭擇時在大多頭年代不如永遠持有 0050，擇時省下的回撤換不回少賺的報酬。"),
             f"- 最慘的五筆（優化版）：\n\n" + md(pd.concat([t_o, t_h]).nsmallest(5, "損益點")[["進場日", "進場價", "出場日", "出場價", "出場原因", "損益點", "報酬率_名義", "最大不利偏移_pct", "持有天數", "事後檢討"]]),
             f"- 優化空間（由逐筆檢討彙整）：搜尋期 {len(t_o)} 筆中停損 {int((t_o.出場原因 != '訊號出場').sum())} 筆；平均持有 {t_o.持有天數.mean():.0f} 天；贏家平均吐回最大浮盈 "
             f"{((t_o[t_o.損益點 > 0].最大有利偏移點 - t_o[t_o.損益點 > 0].損益點) / t_o[t_o.損益點 > 0].最大有利偏移點).median():.0%}（中位數）。",
             "- 這套多指標組合的價值是『回撤小』，不是『報酬高』：2008 年同期 0050 -46%，策略搜尋期最大回撤約 -20%。若要贏過 0050，方向應從『取代 0050』改為『與 0050 搭配』（0050 核心＋期貨避險腳），這是下一輪假說，不是本輪結論。",
             "- 美股／VIX／ADR 與外資期貨 2008 年起的歷史資料沒有補到，這是本輪最大的缺口；補到後只能再開新一輪，且新的保留期需另切（2019 起已用掉）。"]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main(do_holdout="--holdout" in sys.argv)
