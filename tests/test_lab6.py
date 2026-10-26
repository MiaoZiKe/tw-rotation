"""第六輪紅線測試：保留期只跑一次（重跑只讀紀錄）、單檔停損次日開盤出場、選股只用 t 日以前資料、不持有 ETF。"""
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from test_swing_lab5 import _P  # noqa: E402

from pipeline.compute import lab6 as L  # noqa: E402


def _P6():
    P = _P()
    T, N = P["C"].shape
    P["f6"] = dict(vol=np.full((T, N), 0.3), r20=np.zeros((T, N)), r60=np.zeros((T, N)))
    P["f"]["ma200"] = P["C"] * 0.9
    return P


def test_保留期只跑一次(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "LOG", tmp_path / "log.csv")
    monkeypatch.setattr(L, "OUT", tmp_path)
    calls = []
    monkeypatch.setattr(L, "metrics_row", lambda P, sp, pool, lo, hi: calls.append(1) or dict(cagr=0.1, mdd=-0.2, sharpe=1, bh=0.05, bh_mdd=-0.3, excess=0.05, ywin=2, ynum=4, yrets="{}", y0050="{}", expo=.5, turn=1, years=4))
    a = L.holdout(None, '{"fam":"x"}', 200, "內部保留")
    b = L.holdout(None, '{"fam":"x"}', 200, "內部保留")
    assert len(calls) == 1 and a["cagr"] == b["cagr"]            # 第二次只讀紀錄，沒有重算
    L.holdout(None, '{"fam":"x"}', 100, "內部保留")
    assert len(calls) == 2


def test_單檔停損次日開盤出場():
    P = _P6()
    T = P["C"].shape[0]
    P["C"][-60:, 2] *= 0.5; P["O"][-60:, 2] *= 0.5; P["Cf"] = P["C"]; P["rawC"] = P["C"]
    P["f"]["mom252"][:, 2] = 9.0
    spec = dict(fam="nh6", N=1, rebal="Q", mf="br200", sl=0.2)
    P["f"]["nh"][:, 2] = 1.0
    r = L.run6(P, spec, 200, "2019-12-02", "2020-08-31", trades=True)
    t = r["trades"]
    stops = t[t["exit_reason"].str.contains("單檔停損")]
    assert len(stops) >= 1 and (set(t["code"]) <= {"1101", "1102", "1103"})   # 從不持有 0050


def test_選股不使用未來資料():
    P = _P6()
    spec = dict(fam="nh6", N=2, rebal="Q", mf="br200")
    t = 300
    a = L.pick6(P, spec, t, 200)[0]
    P2 = {**P, "f": {k: v.copy() for k, v in P["f"].items()}}
    for k in ("mom252", "nh"):
        P2["f"][k][t + 1:] = np.random.default_rng(1).normal(size=P2["f"][k][t + 1:].shape)
    assert L.pick6(P2, spec, t, 200)[0] == a
