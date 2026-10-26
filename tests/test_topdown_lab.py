"""第二輪三層回測的紅線測試：次日開盤成交、大盤分數 < 門檻不進場並全數出場、成本有扣。"""
import numpy as np
import pandas as pd

from pipeline.compute import topdown_lab as td
from pipeline.compute.strategy_lab import SLIP


def _M(score_vals, ent_t=5, ex_t=None, T=60):
    idx = pd.bdate_range("2021-03-01", periods=T)
    o = np.linspace(100, 130, T).reshape(T, 1)
    c = o + 0.5
    ent = np.zeros((T, 1), bool); ent[ent_t, 0] = True
    ex = np.zeros((T, 1), bool)
    if ex_t is not None:
        ex[ex_t, 0] = True
    vc = np.ones((T, 1), bool)
    atr = np.full((T, 1), 1.0)
    return dict(idx=idx, codes=["1111"], O=o, H=o + 1, L=o - 1, C=c, Cf=c.copy(),
                sig={"ST": (ent, ex, vc, atr)}, score=pd.Series(score_vals, index=idx),
                g=dict(score=np.full((T, 1), 8.0)), info={}, mem_mat=np.ones((1, 1), bool),
                stock_rs=np.zeros((T, 1)))


def _first_t():
    return pd.bdate_range("2021-03-01", periods=60).searchsorted(pd.Timestamp(td.T_START))


def test_訊號次日開盤成交():
    t0 = _first_t()
    M = _M(np.full(60, 9.0), ent_t=t0 + 3, ex_t=t0 + 10)
    eq, tr, _ = td.simulate(M, dict(entry="ST", use_l1=True, use_l2=False))
    assert len(tr) == 1
    assert tr.loc[0, "entry_i"] == t0 + 4 and tr.loc[0, "exit_i"] == t0 + 11
    assert np.isclose(tr.loc[0, "entry_px"], M["O"][t0 + 4, 0] * (1 + SLIP))


def test_大盤分數低不進場():
    t0 = _first_t()
    M = _M(np.full(60, 2.0), ent_t=t0 + 3)
    _, tr, _ = td.simulate(M, dict(entry="ST", use_l1=True, use_l2=False))
    assert len(tr) == 0


def test_分數跌破門檻隔日全出():
    t0 = _first_t()
    sc = np.full(60, 9.0); sc[t0 + 8:] = 1.0     # t0+8 收盤分數跌破 4
    M = _M(sc, ent_t=t0 + 3)
    _, tr, _ = td.simulate(M, dict(entry="ST", use_l1=True, use_l2=False))
    assert len(tr) == 1 and tr.loc[0, "exit_i"] == t0 + 9 and "大盤分數" in tr.loc[0, "exit_reason"]
    assert tr.loc[0, "ret"] < (M["O"][t0 + 9, 0] / M["O"][t0 + 4, 0] - 1)    # 成本有扣
