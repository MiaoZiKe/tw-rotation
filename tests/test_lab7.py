"""第七輪紅線測試：沒有法人資料的股票不會被選、法人特徵不使用未來資料、保留期只跑一次（沿用第六輪機制）。"""
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from test_swing_lab5 import _P  # noqa: E402

from pipeline.compute import lab7 as L7  # noqa: E402


def _P7():
    P = _P()
    T, N = P["C"].shape
    P["f"]["ma200"] = P["C"] * 0.9
    P["f6"] = dict(vol=np.full((T, N), 0.3), ti20=np.random.default_rng(0).normal(size=(T, N)), fi60=np.random.default_rng(1).normal(size=(T, N)),
                   streak=np.random.default_rng(2).integers(0, 10, (T, N)).astype(float), it20=np.zeros((T, N)), fchg=np.zeros((T, N)), fi120=np.zeros((T, N)))
    return P


def test_沒有法人資料的股票不會被選():
    P = _P7()
    P["f6"]["ti20"][:, 2] = np.nan; P["f6"]["fi60"][:, 2] = np.nan; P["f6"]["streak"][:, 2] = np.nan
    for fam in ("trust", "foreign", "instcombo", "nhinst"):
        picks, _ = L7.pick7(P, dict(fam=fam, N=3), 300, 200)
        assert 2 not in picks and 0 not in picks          # 0 是 0050（不可交易），2 沒有法人資料


def test_法人特徵不用未來資料():
    P = _P7()
    spec = dict(fam="instcombo", N=2)
    a = L7.pick7(P, spec, 300, 200)[0]
    P2 = {**P, "f6": {k: v.copy() for k, v in P["f6"].items()}}
    for k in ("ti20", "fi60"):
        P2["f6"][k][301:] = 99.0
    assert L7.pick7(P2, spec, 300, 200)[0] == a


def test_批次數與累計試驗():
    n = sum(len(v) for v in L7.batches7().values())
    assert n == 288 and L7.PRIOR_TRIALS + n == 1146
