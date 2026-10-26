"""MK 策略紅線測試：題材濾網不看未來、純個股版不持有 ETF、週訊號隔日成交、配置權重。"""
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from test_swing_lab5 import _P  # noqa: E402

from pipeline.compute import mk_lab as M  # noqa: E402


def _eps():
    return pd.DataFrame({"集數": ["EP1", "EP2", "EP3", "EP4"],
                         "上架日": pd.to_datetime(["2024-01-02", "2024-01-05", "2024-01-09", "2024-01-20"]),
                         "codes": [["2454"], [], [], []], "themes": [["M"], ["M"], ["M"], ["M"]]})


def test_題材濾網只用上架日之前的集數():
    eps = _eps()
    assert not M.theme_ok(eps, "2408", pd.Timestamp("2024-01-09"))      # 第 3 集 1/9 當天才上架，不能用
    assert M.theme_ok(eps, "2408", pd.Timestamp("2024-01-10"))          # 隔天起前 3 集都可用（>=3 集記憶體題材）
    assert M.theme_ok(eps, "2454", pd.Timestamp("2024-01-03"))          # 直接點名 1/2 上架，1/3 起可用
    assert not M.theme_ok(eps, "2454", pd.Timestamp("2024-01-02"))      # 當天不可用


def test_配置權重():
    w = M.weights_for(5)
    assert abs(sum(w) - 0.90) < 1e-9 and w[0] == 0.30 and len(w) == 5
    assert M.V2["weights"] == (0.30, 0.15, 0.15, 0.15, 0.15) and M.V2["reserve"] == 0.10


def test_純個股版不持有ETF且大盤轉弱全現金():
    P = _P()
    T = P["C"].shape[0]
    P["c50"] = pd.Series(np.linspace(130, 60, T), index=P["idx"])          # 0050 一路下跌 -> 一直在 100 日線下
    P["o50"] = P["c50"].copy()
    P["f"]["ma200"] = P["C"] * 0.9
    spec = M.cfg(M.V2, theme=False, pool="pit200", etf=False, fill="open", costs="ours")
    r = M.run_mk(P, spec, "2020-01-02", "2020-08-31", None)
    assert r["expo"] == 0.0 and r["trades"].empty and abs(r["eq"].iloc[-1] - 1.0) < 1e-9     # 全程現金，沒有 0050 部位


def test_週訊號隔日成交():
    P = _P()
    idx = P["idx"]; T = len(idx)
    P["c50"] = pd.Series(np.linspace(60, 130, T), index=idx); P["o50"] = P["c50"].copy()
    C = np.cumprod(1 + np.full((T, 4), 0.003), axis=0) * 100
    P["C"] = C; P["O"] = C.copy(); P["Cf"] = C; P["rawC"] = C; P["H"] = C; P["L"] = C
    spec = M.cfg(M.V2, theme=False, pool="pit200", etf=False, fill="open", costs="ours")
    r = M.run_mk(P, spec, "2020-02-03", "2020-08-31", None)
    lg = r["log"]
    assert len(lg) > 0
    wk = idx.to_period("W-FRI")
    for d in pd.to_datetime(lg["日期"]):
        i = idx.get_loc(d)
        assert i == 0 or wk[i] != wk[i - 1]                                # 成交日是新的一週的第一個交易日
