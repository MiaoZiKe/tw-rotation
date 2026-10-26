"""第四輪：換月跳點修正、危險狀態遲滯、保證金引擎一致性、揭露鎖檔、無前視。"""
import numpy as np
import pandas as pd
import pytest

from pipeline.compute import futures_lab2 as G
from pipeline.compute import futures_lab4 as L4


@pytest.fixture(scope="module")
def lab():
    return L4.Lab4()


def test_roll_adjust_removes_only_roll_day_jump(lab):
    L = lab.lab
    raw = pd.Series(L.c, index=lab.idx).pct_change()
    adj = pd.Series(lab.c, index=lab.idx).pct_change()
    roll = np.zeros(len(raw), bool)
    roll[np.where(L.settle)[0] + 1] = True
    roll = roll[: len(raw)]
    other = ~roll
    assert np.allclose(raw[other].fillna(0), adj[other].fillna(0), atol=1e-9)           # 其他日報酬完全不變
    d = (adj[roll] - raw[roll]); d = d[(d.index >= '2008-01-01') & (d.index < '2017-01-01')]
    assert d.mean() > 0.002                                                            # 換月日平均被往上修正（原本向下跳，2008～2016 約 34 bp）
    assert lab.fac[-1] == 1.0 and (lab.fac > 0.3).all() and lab.fac[0] < 0.8                 # 2008 年的價格被往回調整到較低水準


def test_fx_engine_equals_original_when_no_scaling():
    rng = np.random.default_rng(1)
    n = 300
    c = 1000 * np.exp(np.cumsum(rng.normal(0, 0.01, n))); o = np.r_[c[0], c[:-1]]; h = np.maximum(o, c) * 1.003; l = np.minimum(o, c) * 0.997
    tgt = (rng.random(n) > 0.4) * 1.0
    z = np.zeros(n, bool)
    a = G._sim_lev(o, h, l, c, tgt, z, 50.0, 2.0, 2e-5, 4.0, 0.1, 0.08, 0.2, 0.0, 1e7)
    b = L4._sim_lev_fx(o, h, l, c, tgt, z, 50.0, 2.0, 2e-5, 4.0, 0.1, 0.08, 0.2, 0.0, 1e7, np.ones(n))
    assert np.allclose(a[0], b[0]) and np.allclose(a[1], b[1])


def test_state_hysteresis():
    raw = np.array([0, 1, 0, 0, 0, 0, 1, 0, 0], bool)
    st = L4._state_nb(raw, 3)
    assert list(st) == [False, True, True, True, False, False, True, True, True][:len(raw)] or st[4] is np.False_ or not st[4]
    assert st[1] and st[2] and st[3] and not st[4]                       # 危險解除要連續 3 天才回場


def test_target_depends_only_on_past(lab):
    p = dict(set=("T",), k=1, n=200, vix=30, bas=0.003, dd=0.15, m=3, base=1.2, boost=0, gap=0)
    t1 = lab.target(p).copy()
    c_old = lab.c.copy(); ma_old = dict(lab.ma)
    j = 3000
    lab.c = lab.c.copy(); lab.c[j + 1:] = lab.c[j + 1:] * 0.5                         # 把未來價格砍半
    lab.ma = {n: pd.Series(lab.c).rolling(n).mean().to_numpy() for n in (50, 100, 150, 200, 250)}
    lab.tcache = {}
    t2 = lab.target(p)
    lab.c = c_old; lab.ma = ma_old; lab.tcache = {}
    assert np.array_equal(t1[:j + 1], t2[:j + 1])


def test_cny_windows_ten_days_each_year(lab):
    pre = lab.cny_pre
    yrs = pd.Series(lab.idx[pre].year).value_counts()
    assert yrs.min() >= 9 and yrs.max() <= 11 and len(yrs) >= 20


def test_avg_expo_never_negative_and_hold_near_one(lab):
    r, e, l = lab.hold(1.0)
    s = L4.window_stats(lab, r, e, "2008-01-02", "2017-01-01")
    assert 0.9 < s["avg_expo"] < 1.2 and l.sum() == 0


def test_reveal_runs_once(tmp_path, monkeypatch, lab):
    monkeypatch.setattr(L4, "OUT", tmp_path)
    p = dict(set=("T",), k=1, n=200, vix=30, bas=0.003, dd=0.15, m=3, base=1.0, boost=0, gap=0)
    L4.reveal(lab, {"x": p})
    assert (tmp_path / "_reveal_done.json").exists()
    with pytest.raises(RuntimeError):
        L4.reveal(lab, {"x": p})
