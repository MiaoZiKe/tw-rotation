"""第四輪紅線測試：分群只用過去資料、核心 0050 等同基準（含成本）、大盤分數極低時核心降水位、衛星次日開盤成交。"""
import numpy as np
import pandas as pd

from pipeline.compute import topdown_lab4 as T4
from pipeline.compute import topdown_lab3 as T3


def _ret(seed=0, T=400, N=30):
    rng = np.random.default_rng(seed)
    f = rng.normal(0, 0.01, (T, 3))
    load = rng.normal(0, 1, (3, N))
    return pd.DataFrame(f @ load + rng.normal(0, 0.01, (T, N)), index=pd.bdate_range("2020-01-01", periods=T))


def test_分群不用未來資料():
    r = _ret()
    a = T4.mech_labels(r, k=5, lookback=60)
    r2 = r.copy()
    cut = 200
    r2.iloc[cut:] = np.random.default_rng(9).normal(0, 0.02, r2.iloc[cut:].shape)     # 竄改 cut 當天(含)以後
    b = T4.mech_labels(r2, k=5, lookback=60)
    month_start = np.where(r.index.to_period("M") == r.index[cut].to_period("M"))[0][0]
    m0 = min(cut, month_start)
    assert (a[:m0] == b[:m0]).all()          # 竄改點以前的標籤完全不變


def _M(T=80, score=9.0, o50=None):
    idx = pd.bdate_range("2021-03-01", periods=T)
    o50 = np.linspace(100, 120, T) if o50 is None else o50
    z = np.zeros((T, 1))
    return dict(idx=idx, codes=["1111"], O=np.full((T, 1), 100.0), L=np.full((T, 1), 99.0), Cf=np.full((T, 1), 100.0),
                sig4={"PB": (np.zeros((T, 1), bool), np.zeros((T, 1), bool), np.ones((T, 1), bool), np.full((T, 1), 2.0))},
                score=pd.Series(np.full(T, score), index=idx), gs=z, elig=np.ones((T, 1), bool), stock_rs=z,
                O50=o50.copy(), C50=o50.copy())


def test_純核心等於0050基準():
    M = _M()
    t0 = M["idx"].searchsorted(pd.Timestamp(T4.T_START))
    r = T4.run4(M, dict(S=0.0, use_cut=False), liquidate=True)
    bh = (1 + T3.bh0050(M, T4.T_START).dropna()).prod() - 1
    assert abs(r["eq"].iloc[-1] - 1 - bh) < 0.01


def test_大盤分數極低核心降到一半():
    M = _M(score=0.5)
    r = T4.run4(M, dict(S=0.0, use_cut=True))
    assert 0.45 < r["tot"].iloc[-1] < 0.55
    r2 = T4.run4(M, dict(S=0.0, use_cut=False))
    assert r2["tot"].iloc[-1] > 0.95


def test_衛星隔日開盤進場():
    M = _M()
    t0 = M["idx"].searchsorted(pd.Timestamp(T4.T_START))
    ent = np.zeros((80, 1), bool); ent[t0 + 5, 0] = True
    M["sig4"]["PB"] = (ent,) + M["sig4"]["PB"][1:]
    r = T4.run4(M, dict(entry="PB", S=0.3, slots=3, use_group=False))
    (i, t), v = next(iter(r["info"].items()))
    assert t == t0 + 6 and np.isclose(v["w"], 0.1)
