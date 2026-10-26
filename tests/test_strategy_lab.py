"""策略實驗室回測引擎的紅線測試：次根開盤成交、成本、高週期濾網不偷看。"""
import numpy as np
import pandas as pd

from pipeline.compute.strategy_lab import _run, align, FEE, TAX


def _bars(n=10):
    o = np.arange(100.0, 100.0 + n)
    return o, o + 1, o - 1, o + 0.5


def test_訊號在收盤後_成交在下一根開盤():
    o, h, l, c = _bars()
    entry = np.zeros(10, bool); entry[2] = True        # 第 2 根收盤產生進場訊號
    exitsig = np.zeros(10, bool); exitsig[5] = True    # 第 5 根收盤產生出場訊號
    ret, tr = _run(o, h, l, c, entry, exitsig, np.full(10, 1.0), 0.0, 0.0, 0.0, 0.0)
    assert int(tr[0, 0]) == 3 and int(tr[0, 1]) == 6    # 第 3 根進、第 6 根出
    assert np.isclose(tr[0, 2], o[6] / o[3] - 1)          # 報酬用開盤價算，不是用訊號那根收盤
    assert ret[2] == 0 and ret[3] == c[3] / o[3] - 1


def test_成本有扣():
    o, h, l, c = _bars()
    entry = np.zeros(10, bool); entry[2] = True
    exitsig = np.zeros(10, bool); exitsig[5] = True
    _, t0 = _run(o, h, l, c, entry, exitsig, np.ones(10), 0.0, 0.0, 0.0, 0.0)
    _, t1 = _run(o, h, l, c, entry, exitsig, np.ones(10), 0.0, FEE, TAX + FEE, 0.001)
    assert t0[0, 2] - t1[0, 2] > FEE * 2 + TAX


def test_週K濾網只用已完成的週():
    wk = pd.Series([1.0, 0.0], index=pd.to_datetime(["2024-01-05", "2024-01-12"]))
    days = pd.to_datetime(["2024-01-08", "2024-01-11", "2024-01-12"])
    v = align(wk, days, 0)
    assert list(v) == [1.0, 1.0, 0.0]   # 週中仍用上一週；週五收盤後才換成這週的值
