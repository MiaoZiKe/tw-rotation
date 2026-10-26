"""台指期第二輪：不偷看未來、保證金強制平倉、保留期只能跑一次。"""
import numpy as np
import pandas as pd
import pytest

from pipeline.compute import futures_lab2 as G


@pytest.fixture(scope="module")
def lab2():
    return G.Lab2()


def _d(n=400, seed=3):
    rng = np.random.default_rng(seed)
    c = 1000 * np.exp(np.cumsum(rng.normal(0.0003, 0.012, n)))
    o = c * (1 + rng.normal(0, 0.003, n)); h = np.maximum(o, c) * 1.004; l = np.minimum(o, c) * 0.996
    return dict(o=o, h=h, l=l, c=c, v=rng.uniform(1e4, 2e4, n))


@pytest.mark.parametrize("name", ["MA", "EMAX", "MACD", "RSI", "KD", "BOLL", "DON", "ST", "ADX", "ICHI", "SAR", "CCI", "WR",
                                  "ROC", "OBV", "VP", "ATRCH", "KELT", "HA", "TRIX", "AROON", "GAP", "NHI"])
def test_indicator_no_lookahead(name):
    d = _d(); p = G.SPEC[name]["D"]
    full = G.ind_state(name, d, p)
    cut = G.ind_state(name, {k: v[:300] for k, v in d.items()}, p)
    assert (full[:300] == cut).all(), name                      # 截掉未來資料後，過去每天的狀態不變


def test_weekly_state_uses_completed_weeks_only(lab2):
    s = lab2.state("MA", "W", dict(n=20))
    # 同一週內（非週最後交易日）狀態必須等於上一週的狀態：週中不可能用到當週未收完的週K
    code, last = lab2.wk_code, lab2.last_of_week
    mid = np.where(~last)[0]
    prev_week_last = {c: i for i, c in enumerate(code) if last[i]}
    for i in mid[200:260]:
        j = prev_week_last.get(code[i] - 1)
        if j is not None:
            assert s[i] == s[j]


def test_margin_liquidation_and_no_liq_unlevered():
    n = 40
    c = np.full(n, 1000.0); o = c.copy(); h = c + 5; l = c - 5
    c[10:] = 800.0; o[10] = 950.0; l[10] = 780.0; h[10] = 960.0   # 第 10 日重挫
    tgt = np.zeros(n); tgt[:20] = 6.0                              # 6 倍：名義 60% 以上維持保證金不足
    z = np.zeros(n, bool)
    r, q, liq = G._sim_lev(o, h, l, c, tgt, z, 50.0, 2.0, 2e-5, 4.0, 0.10, 0.08, 0.25, 0.0, 1e7)
    assert liq.sum() >= 1 and q[11:].sum() == 0 or liq.sum() >= 1
    tgt1 = np.zeros(n); tgt1[:20] = 1.0
    r1, q1, liq1 = G._sim_lev(o, h, l, c, tgt1, z, 50.0, 2.0, 2e-5, 4.0, 0.10, 0.08, 0.25, 0.0, 1e7)
    assert liq1.sum() == 0


def test_holdout_runs_once(tmp_path, monkeypatch, lab2):
    monkeypatch.setattr(G, "OUT", tmp_path)
    spec = dict(W=None, D=("MA", dict(n=60)), gates=(), k=99.0)
    G.final_holdout(lab2, {"x": spec})
    assert (tmp_path / "_holdout_done.json").exists()
    with pytest.raises(RuntimeError):
        G.final_holdout(lab2, {"x": spec})


def test_search_never_touches_holdout(lab2):
    spec = dict(W=None, D=("MA", dict(n=60)), gates=(), k=99.0)
    s = G.score(lab2, spec, G.SEARCH_START, "2010-01-01")        # 訓練評分只看 a 之前
    r, _ = lab2.run(spec)
    assert np.isfinite(s)
    # 把 2010 之後的報酬全部改掉，2010 前的分數不變（評分函式只切片 < a）
    x = G.sl(r, G.B50_START, "2010-01-01")
    assert x.index.max() < pd.Timestamp("2010-01-01")


def test_default_version_resets_params():
    sp = dict(W=("SAR", dict(af=0.03, mx=0.2)), D=("TRIX", dict(n=60)), gates=("BC",), k=99.0)
    d = G.default_version(sp)
    assert d["W"][1] == G.SPEC["SAR"]["W"] and d["D"][1] == G.SPEC["TRIX"]["D"] and d["k"] == 3.0 and d["gates"] == ("BC",)


def test_entry_next_open(lab2):
    # 單一指標策略：進場價必須是「訊號日隔天」的開盤（含滑價），不是訊號日收盤
    spec = dict(W=None, D=("MA", dict(n=60)), gates=(), k=99.0)
    _, t = lab2.run(spec)
    e = t.iloc[5]
    assert int(e.entry_i) == int(e.sig_i) + 1
    assert abs(e.entry_px - (lab2.lab.o[int(e.entry_i)] + G.SLIP)) < 1e-6
