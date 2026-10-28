"""第九輪（大型股增強指數）的小測試：上限分配、Newey-West t 值、市值加權權重總和。"""
import numpy as np

from pipeline.compute import index_lab9 as L


def test_cap_redistributes_and_sums_to_one():
    w = np.array([0.6, 0.2, 0.1, 0.1])
    c = L._cap(w, 0.3)
    assert abs(c.sum() - 1) < 1e-9 and c.max() <= 0.3 + 1e-9


def test_nw_t_zero_mean_small():
    rng = np.random.default_rng(1)
    assert abs(L.nw_t(rng.normal(0, 1, 2000))) < 4


def test_nw_t_detects_positive_mean():
    rng = np.random.default_rng(2)
    assert L.nw_t(rng.normal(0.2, 1, 2000)) > 3
