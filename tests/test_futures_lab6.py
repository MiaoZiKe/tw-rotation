"""第六輪：快速回場狀態機、曝險上限、區塊重抽樣、鄰域、鎖檔。"""
import numpy as np
import pandas as pd
import pytest

from pipeline.compute import futures_lab6 as L6


def test_state_fast_releases_on_clear_signal():
    raw = np.array([0, 1, 0, 0, 0, 0], bool)
    clear = np.array([0, 0, 1, 0, 0, 0], bool)
    st = L6._state_fast(raw, 5, clear)
    assert list(st) == [False, True, False, False, False, False]          # 危險一解除、且快速回場訊號成立，下一根就回場
    st2 = L6._state_fast(raw, 3, np.zeros(6, bool))
    assert list(st2) == [False, True, True, True, False, False]            # 沒有快速訊號：要連續 m=3 天才解除


def test_grid_has_no_inconsistent_dyn_b():
    g = L6.grid6()
    assert all(not (p["dyn"] != "none" and p["b"] != 1.0) for p in g)
    assert all(p["gap"] == 0 and p["boost"] == 0 for p in g)
    assert all(not ("SM" in p["set"] and p["k"] < 2) for p in g)             # Sell in May 一定要與其他旗標同時成立才出場
    assert all(p["stage"] == 0 for p in g if p["k"] == 1)


def test_neighbors_change_one_axis():
    g = L6.grid6()
    p = next(x for x in g if x["set"] == ("W", "DD") and x["k"] == 2 and x["stage"] == 0.5 and x["fast"] == "W" and x["dyn"] == "none" and x["b"] == 1.0)
    for q in L6.neighbors6(p):
        diff = [k for k in L6.AX6 if q[k] != p[k]]
        assert 1 <= len(diff) <= 2                                           # 只動一個維度（動態曝險切換時 b 會連動歸 1.0）


def test_boot_excess_detects_clear_edge_and_null():
    rng = np.random.default_rng(0)
    rb = rng.normal(0.0004, 0.01, 1500)
    edge = L6.boot_excess(rb + 0.0006, rb)
    same = L6.boot_excess(rb, rb)
    noisy = L6.boot_excess(rb + rng.normal(0, 0.005, 1500), rb)             # 每天多 50bp 的雜訊（平均 0）：區間要夠寬、能跨過 0
    assert edge["lo"] > 0 and edge["p_pos"] > 0.99
    assert abs(same["lo"]) < 1e-9 and abs(same["hi"]) < 1e-9
    assert (noisy["hi"] - noisy["lo"]) > 2 * (edge["hi"] - edge["lo"])             # 雜訊大的區間遠寬於穩定超額的區間


@pytest.fixture(scope="module")
def lab():
    return L6.Lab6()


def test_target_depends_only_on_past(lab):
    p = dict(set=("W", "DD"), k=2, n=200, vix=30, bas=0.003, dd=0.10, m=3, fast="MA20", stage=0.5, dyn="1.2/0.8", b=1.0, bmod=1, gap=0, boost=0)
    t1 = lab.target(p).copy()
    j = 3000
    c_old, ma_old, ma20_old, dd_old = lab.c.copy(), dict(lab.ma), lab.ma20.copy(), lab.dd250.copy()
    lab.c = lab.c.copy(); lab.c[j + 1:] *= 0.5
    lab.ma = {n: pd.Series(lab.c).rolling(n).mean().to_numpy() for n in (50, 100, 150, 200, 250)}
    lab.ma20 = pd.Series(lab.c).rolling(20).mean().to_numpy()
    lab.dd250 = lab.c / pd.Series(lab.c).rolling(250, min_periods=60).max().to_numpy() - 1
    lab.tcache = {}
    t2 = lab.target(p)
    lab.c, lab.ma, lab.ma20, lab.dd250, lab.tcache = c_old, ma_old, ma20_old, dd_old, {}
    assert np.array_equal(t1[:j + 1], t2[:j + 1])                            # 週K 狀態來自預先算好的陣列（不受此處改價影響）；其餘旗標只用 <= j 的價格


def test_exposure_cap_in_selection(lab):
    p = dict(set=("T",), k=1, n=200, vix=30, bas=0.003, dd=0.10, m=1, fast="none", stage=0, dyn="none", b=1.2, bmod=0, gap=0, boost=0)
    sc, s = L6.score(lab, p, *L6.SEARCH)
    assert s["avg_expo"] <= 1.2 or sc < 0                                     # 超過平均曝險上限的不得拿到正分數


def test_reveal_lock_reuse(tmp_path, monkeypatch, lab):
    monkeypatch.setattr(L6, "OUT", tmp_path)
    r, e, l = lab.hold(1.0)
    c = [dict(name="x", r=r, e=e, p=None, label="x", kind="hold", gates=None)]
    V1 = L6.reveal(lab, c)
    V2 = L6.reveal(lab, c)                                                    # 鎖檔存在：直接讀回，不重算
    assert V1["cands"]["x"]["wins"]["C"]["cagr"] == V2["cands"]["x"]["wins"]["C"]["cagr"] and (tmp_path / "_reveal_done.json").exists()
