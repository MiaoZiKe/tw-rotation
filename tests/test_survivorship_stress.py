"""存活者偏誤壓力測試：不改候選參數、注入邏輯單調、q=0 不動權益。"""
import numpy as np
import pandas as pd

from pipeline.compute import rev_lab8 as R8, survivorship_stress as X


def _eq():
    return pd.Series(np.linspace(1, 2, 10), index=pd.bdate_range("2020-01-01", periods=10))


def _tr(ret=0.1):
    return pd.DataFrame(dict(code=["2330"], exit=[pd.Timestamp("2020-01-08")], ret=[ret]))


def test_q為零權益不變():
    e = _eq()
    assert X.adjust_equity(e, _tr(), 0.0, -1.0).equals(e)


def test_虧損越大權益越低且只影響出場日之後():
    e = _eq()
    a = X.adjust_equity(e, _tr(), 0.5, -0.1); b = X.adjust_equity(e, _tr(), 0.5, -1.0)
    assert (b <= a).all() and (a <= e).all()
    assert (b[b.index < "2020-01-08"] == e[e.index < "2020-01-08"]).all()
    assert b.iloc[-1] < e.iloc[-1]


def test_上界單調():
    assert X.clopper_upper(0, 50) < X.clopper_upper(1, 50) < X.clopper_upper(5, 50)


def test_候選規格未被改動():
    sp = X.specs()["候選 營收動能+近52週高85%"]
    assert sp["axes"] == R8.make_spec(x2="nh85")["axes"] and sp["N"] == 10
    assert X.specs()["S2-R（產業上限 2）"]["axes"]["cap"] == 2
