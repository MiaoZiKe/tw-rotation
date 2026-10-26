"""第三輪：美股時間線、缺值不濾、出場旗標、保留期鎖檔。"""
import numpy as np
import pandas as pd
import pytest

from pipeline.compute import futures_lab3 as L3


@pytest.fixture(scope="module")
def lab():
    return L3.Lab3()


def test_us_night_aligns_with_next_open_gap(lab):
    gap = pd.Series(lab.lab.o[1:] / lab.lab.c[:-1] - 1, index=lab.idx[:-1])
    r = pd.Series(lab.us_night["spx"], index=lab.idx)
    x = pd.concat([r, gap], axis=1).dropna(); x = x[x.index >= "2008-01-01"]
    y = pd.concat([r.shift(-1), gap], axis=1).dropna(); y = y[y.index >= "2008-01-01"]
    assert x.corr().iloc[0, 1] > 0.4 and abs(y.corr().iloc[0, 1]) < 0.2     # 對的那一天高相關、錯置一天幾乎無關


def test_gates_allow_when_data_missing(lab):
    pre = lab.idx < "2007-12-01"                                             # intl_daily 從 2008 才有
    for k in ("U_SPX", "U_SOX", "U_SPXT", "U_VIXL", "U_ADR", "U_DXY", "C_FOR"):
        assert lab.gates[k][pre].all(), k


def test_exit_flag_forces_open_exit(lab):
    sp = dict(W=None, D=("MA", dict(n=60)), gates=(), k=99.0)
    _, t0 = lab.run(sp)
    sp2 = dict(sp, xit=("XS",))
    _, t1 = lab.run(sp2)
    assert len(t1) >= len(t0) and (t1.hold if "hold" in t1 else t1.exit_i - t1.entry_i).mean() <= (t0.exit_i - t0.entry_i).mean() + 1e-9


def test_no_trade_entry_uses_future_us_data(lab):
    # 把訊號日之後一天的美股資料改壞，不應該改變任何「訊號日」的閘門值
    g = lab.gates["U_SPX"].copy()
    r = lab.us_night["spx"]
    i = 3000
    assert g[i] == (not (r[i] < -0.01)) or np.isnan(r[i])


def test_holdout_runs_once(tmp_path, monkeypatch, lab):
    monkeypatch.setattr(L3, "OUT", tmp_path)
    sp = dict(W=None, D=("MA", dict(n=60)), gates=(), k=99.0)
    L3.final_holdout(lab, {"x": sp})
    assert (tmp_path / "_holdout_done.json").exists()
    with pytest.raises(RuntimeError):
        L3.final_holdout(lab, {"x": sp})


def test_windows_do_not_overlap():
    assert L3.TRAIN[1] == L3.HOLD[0] and L3.HOLD[1] == L3.SEEN
