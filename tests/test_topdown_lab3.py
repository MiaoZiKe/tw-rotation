"""第三輪紅線測試：次日開盤成交、ATR 停損的跳空／盤中觸價成交價、追跳空取消、淘汰閘門、0050 基準含成本。"""
import numpy as np
import pandas as pd

from pipeline.compute import topdown_lab3 as T3
from pipeline.compute.strategy_lab import SLIP


def _M(T=60, ent_t=None, o=None, lo=None, atr_v=2.0):
    idx = pd.bdate_range("2021-03-01", periods=T)
    o = np.full((T, 1), 100.0) if o is None else o
    c = o.copy()
    h = o + 1
    l = o - 1 if lo is None else lo
    ent = np.zeros((T, 1), bool)
    if ent_t is not None:
        ent[ent_t, 0] = True
    return dict(idx=idx, codes=["1111"], O=o, H=h, L=l, C=c, Cf=c.copy(),
                sig={"ST": (ent, np.zeros((T, 1), bool), np.ones((T, 1), bool), np.full((T, 1), atr_v))},
                score=pd.Series(np.full(T, 9.0), index=idx), gscore=np.full((T, 1), 8.0),
                mem_mat=np.ones((1, 1), bool), stock_rs=np.zeros((T, 1)),
                O50=np.full(T, 100.0), C50=np.full(T, 100.0))


def _t0():
    return pd.bdate_range("2021-03-01", periods=60).searchsorted(pd.Timestamp(T3.T_START))


CFG = dict(entry="ST", use_l1=False, use_l2=False, sizing="equal", base=False)


def test_次日開盤進場():
    t0 = _t0()
    M = _M(ent_t=t0 + 3)
    _, tr, _, _ = T3.simulate3(M, CFG)
    inf = M["_info"]
    (i, t), v = next(iter(inf.items()))
    assert t == t0 + 4                         # 訊號隔天
    assert np.isclose(v["stop"], 100.0 - T3.STOP_ATR * 2.0)


def test_開盤跳空跌破停損以開盤價出場():
    t0 = _t0()
    o = np.full((60, 1), 100.0); o[t0 + 8:] = 80.0       # 停損 94，隔天跳空到 80
    M = _M(ent_t=t0 + 3, o=o)
    _, tr, _, _ = T3.simulate3(M, CFG)
    assert len(tr) == 1 and "開盤跳空" in tr.loc[0, "exit_reason"]
    assert np.isclose(tr.loc[0, "exit_px"], 80.0 * (1 - SLIP))


def test_盤中觸價以停損價出場():
    t0 = _t0()
    lo = np.full((60, 1), 99.0); lo[t0 + 8, 0] = 90.0     # 開盤沒跳空，最低 90 < 停損 94
    M = _M(ent_t=t0 + 3, lo=lo)
    _, tr, _, _ = T3.simulate3(M, CFG)
    assert len(tr) == 1 and "盤中觸價" in tr.loc[0, "exit_reason"]
    assert np.isclose(tr.loc[0, "exit_px"], 94.0 * (1 - SLIP))


def test_開盤跳空追價取消進場():
    t0 = _t0()
    o = np.full((60, 1), 100.0); o[t0 + 4:] = 110.0       # 隔天開盤高出前收 10 > 1 ATR(2)
    M = _M(ent_t=t0 + 3, o=o)
    _, tr, _, _ = T3.simulate3(M, CFG)
    assert len(tr) == 0 and not M["_info"]


def test_淘汰閘門():
    e = pd.DataFrame({"策略": ["X", "Y"], "判定": ["通過", "淘汰，不使用"]})
    assert T3.paper_gate(e, "X")[0] is True
    assert T3.paper_gate(e, "Y")[0] is False
    assert T3.paper_gate(e, "不存在")[0] is False


def test_0050基準有扣成本():
    t0 = _t0()
    M = _M()
    M["C50"] = np.linspace(100, 160, 60); M["O50"] = M["C50"].copy()
    r = T3.bh0050(M, T3.T_START)
    raw = M["C50"][-1] / M["O50"][t0] - 1
    assert (1 + r).prod() - 1 < raw - 0.002
