"""因子實驗室紅線測試：法定可用日、訊號收盤後次日開盤成交、事件持有期、保留期只跑一次。"""
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from pipeline.compute import factor_lab as F  # noqa: E402
from pipeline.compute.strategy_lab import SLIP  # noqa: E402


def _P(T=120, N=4):
    idx = pd.bdate_range("2020-01-01", periods=T)
    O = np.tile(np.linspace(10, 20, T)[:, None], (1, N)) * (1 + 0.01 * np.arange(N))
    C = O * 1.002
    P = dict(idx=idx, cols=[f"{1000 + i}" for i in range(N)], O=O, Cf=C, C=C, rawC=C, V=np.ones((T, N)) * 1e6)
    P["ci"] = {c: i for i, c in enumerate(P["cols"])}
    P["elig"] = {200: np.ones((T, N), bool), 100: np.ones((T, N), bool)}
    P["f"] = {"ma200": C * 0.9}
    P["ff"] = {"sig": np.tile(np.arange(N, dtype=float), (T, 1)), "yoy1": np.zeros((T, N))}
    P["mf"] = {}
    P["br"] = {200: np.ones(T), 100: np.ones(T)}
    P["c50"] = pd.Series(C[:, 0], index=idx)
    P["o50"] = pd.Series(O[:, 0], index=idx)
    P["is_fin"] = np.zeros(N, bool)
    P["rev_events"] = []
    P["earn_events"] = []
    return P


def test_法定可用日():
    assert F.legal_date(2022 * 4 + 0) == pd.Timestamp("2022-05-15")      # Q1
    assert F.legal_date(2022 * 4 + 1) == pd.Timestamp("2022-08-14")      # Q2
    assert F.legal_date(2022 * 4 + 2) == pd.Timestamp("2022-11-14")      # Q3
    assert F.legal_date(2022 * 4 + 3) == pd.Timestamp("2023-03-31")      # 年報在隔年
    assert F.rev_avail(pd.period_range("2022-12", periods=1, freq="M"))[0] == pd.Timestamp("2023-01-10")


def test_公布前不可見():
    idx = pd.bdate_range("2022-04-01", periods=60)
    df = pd.DataFrame({"a": [1.0, 2.0]}, index=[0, 1])
    out = F._daily(df, [pd.Timestamp("2022-05-15"), pd.Timestamp("2022-08-14")], idx, ["a"])
    s = pd.Series(out[:, 0], index=idx)
    assert s[:"2022-05-13"].isna().all() and s["2022-05-16"] == 1.0 and s["2022-06-20"] == 1.0


def test_定期換股次日開盤成交():
    P = _P()
    sp = dict(comps=("sig",), N=1, rebal="M", mf=None)
    r = F.run_periodic(P, sp, 200, str(P["idx"][5].date()), str(P["idx"][100].date()), trades=True)
    t = r["trades"].iloc[0]
    i = P["idx"].get_loc(t["entry"])
    assert t["code"] == P["cols"][-1]                                     # 分數最高者
    assert abs(t["entry_px"] - P["O"][i, 3] * (1 + SLIP)) < 1e-9          # 進場價＝成交日開盤價，不是訊號日收盤
    assert i >= 5


def test_事件持有期與次日開盤():
    P = _P()
    P["rev_events"] = [20]
    P["ff"]["yoy1"][20] = np.array([0.1, 0.9, 0.2, 0.8])
    sp = dict(ev="rev", thr=0.5, hold=10, K=1, mf=None)
    r = F.run_event(P, sp, 200, str(P["idx"][5].date()), str(P["idx"][100].date()), trades=True)
    t = r["trades"].iloc[0]
    assert t["code"] == P["cols"][1]                                      # 年增率最高的先佔位
    assert P["idx"].get_loc(t["entry"]) == 21 and P["idx"].get_loc(t["exit"]) == 31
    assert abs(t["entry_px"] - P["O"][21, 1] * (1 + SLIP)) < 1e-9


def test_保留期只跑一次(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "LOG", tmp_path / "log.csv")
    monkeypatch.setattr(F, "OUT", tmp_path)
    calls = []
    monkeypatch.setattr(F, "metrics_row", lambda P, sp, pool, lo, hi: calls.append(1) or dict(cagr=.1, mdd=-.2, sharpe=1, bh=.05, bh_mdd=-.3, excess=.05, ywin=2, ynum=4, yrets="{}", y0050="{}", expo=.5, turn=1, years=4))
    F.holdout(None, '{"x":1}', 200, "內部保留")
    F.holdout(None, '{"x":1}', 200, "內部保留")
    assert len(calls) == 1
