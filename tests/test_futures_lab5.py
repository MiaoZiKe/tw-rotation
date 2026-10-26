"""第五輪：修正引擎的不變量（成本換算方向、與原引擎一致、修正只動換月日、保留期鎖檔）。"""
import numpy as np
import pandas as pd
import pytest

from pipeline.compute import futures_lab as F
from pipeline.compute import futures_lab5 as L5


@pytest.fixture(scope="module")
def lab():
    return L5.Lab5()


def _toy(n=120, seed=2):
    rng = np.random.default_rng(seed)
    c = 1000 * np.exp(np.cumsum(rng.normal(0.0004, 0.01, n))); o = np.r_[c[0], c[:-1]]; h = np.maximum(o, c) * 1.003; l = np.minimum(o, c) * 0.997
    sl = rng.random(n) > 0.9
    return o, h, l, c, sl


def test_sim_cm_equals_original_when_cm_is_one():
    o, h, l, c, sl = _toy()
    n = len(c); z = np.zeros(n, bool); one = np.ones(n, bool); atr = np.full(n, 8.0)
    a = F._sim(o, h, l, c, atr, sl, z, ~sl, z, one, one, 3.0, 0.25, 2e-5, 2.0, 4.0, z)
    b = L5._sim_cm(o, h, l, c, atr, sl, z, ~sl, z, one, one, 3.0, 0.25, 2e-5, 2.0, 4.0, z, np.ones(n))
    assert np.allclose(a[0], b[0]) and np.allclose(a[1], b[1])


def test_cost_scale_direction_cheaper_when_cm_small():
    o, h, l, c, sl = _toy()
    n = len(c); z = np.zeros(n, bool); one = np.ones(n, bool); atr = np.full(n, 8.0)
    full = L5._sim_cm(o, h, l, c, atr, sl, z, ~sl, z, one, one, 3.0, 0.25, 0.0, 2.0, 4.0, z, np.ones(n))[0].sum()
    cheap = L5._sim_cm(o, h, l, c, atr, sl, z, ~sl, z, one, one, 3.0, 0.25, 0.0, 2.0, 4.0, z, np.full(n, 0.5))[0].sum()
    assert cheap > full                                                     # 成本係數 < 1（價格被調低）時，每口成本要比較小


def test_fixed_world_restores_patches():
    orig_load, orig_lab = F.load_tx, F.Lab
    with L5.fixed_world():
        assert F.Lab is L5.FixedLab and F.load_tx is not orig_load
    assert F.load_tx is orig_load and F.Lab is orig_lab


def test_adjustment_only_changes_roll_days(lab):
    raw = L5.RAW["raw"]["close"].pct_change()
    adj = pd.Series(lab.lab.c, index=lab.idx).pct_change()
    roll = np.zeros(len(raw), bool); roll[np.where(lab.lab.settle)[0] + 1] = True; roll = roll[:len(raw)]
    assert np.allclose(raw[~roll].fillna(0), adj[~roll].fillna(0), atol=1e-9)
    assert lab.fixfac[-1] == 1.0 and 0.3 < lab.fixfac[0] < 0.9


def test_basis_uses_unadjusted_price(lab):
    # 基差是真實價差，不能被調整係數扭曲：早期基差的量級應與調整前相同（|基差| 通常 < 3%）
    b = lab.lab.X["bas"][:2000]
    assert np.nanmax(np.abs(b)) < 0.1


def test_hold_1x_beats_unfixed_in_search(lab):
    from pipeline.compute import futures_lab4 as L4
    a, b = L4.TRAIN
    r, e, l = lab.hold(1.0)
    s = L4.window_stats(lab, r, e, a, b)
    assert s["cagr"] > 0.03 and 0.9 < s["avg_expo"] < 1.2                  # 修正後持有年化約 5%（前三輪口徑只有 1.3%）


def test_reveal_runs_once(tmp_path, monkeypatch, lab):
    monkeypatch.setattr(L5, "OUT", tmp_path)
    r, e, l = lab.hold(1.0)
    c = dict(name="x", rnd=0, r=r, expo=e, eligible=False, note="", own=None, spec=None, label="")
    L5.reveal([c], lab, lab)
    with pytest.raises(RuntimeError):
        L5.reveal([c], lab, lab)
