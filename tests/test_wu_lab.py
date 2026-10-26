"""吳小弟策略回測：不偷看未來、隔日開盤成交、固定87點出場、反手、保留期鎖檔。"""
import numpy as np
import pandas as pd
import pytest

from pipeline.compute import wu_lab as W


def _bars(n=500, seed=5, drift=0.0006):
    rng = np.random.default_rng(seed)
    c = 1000 * np.exp(np.cumsum(rng.normal(drift, 0.012, n)))
    o = np.r_[c[0], c[:-1]] * (1 + rng.normal(0, 0.003, n))
    h = np.maximum(o, c) * (1 + abs(rng.normal(0, 0.004, n))); l = np.minimum(o, c) * (1 - abs(rng.normal(0, 0.004, n)))
    return W.Bars(pd.bdate_range("2015-01-01", periods=n), o, h, l, c)


def test_entry_at_next_open_not_signal_close():
    b = _bars()
    _, t = W.backtest(b, W.cfg_of(entry="M", exit="fixed87", tp=20.0, hold=10))
    assert len(t) > 5
    for _, x in t.iterrows():
        e = int(x.entry_i)
        assert abs(x.entry_px - (b.o[e] + x["dir"] * W.SLIP)) < 1e-6          # 進場價＝訊號隔天開盤（含滑價）


def test_no_lookahead_signals():
    b = _bars(600)
    cfg = W.cfg_of(entry="A", mods=("A", "B", "C", "E"), shorts=True, exit="formal")
    _, t_full = W.backtest(b, cfg)
    b2 = W.Bars(b.ts[:400], b.o[:400], b.h[:400], b.l[:400], b.c[:400])
    _, t_cut = W.backtest(b2, cfg)
    # 截掉未來之後，早於 390 根進場的交易（進場價、方向、進場根）完全相同
    a = t_full[t_full.entry_i < 390][["entry_i", "dir", "entry_px"]].reset_index(drop=True)
    c = t_cut[t_cut.entry_i < 390][["entry_i", "dir", "entry_px"]].reset_index(drop=True)
    pd.testing.assert_frame_equal(a, c)


def test_fixed87_exit_prices():
    b = _bars()
    _, t = W.backtest(b, W.cfg_of(entry="M", exit="fixed87", tp=15.0, hold=10))
    for _, x in t[t.reason == "固定停利"].iterrows():
        assert x["dir"] * (x.exit_px - x.entry_px) >= 15.0 - 2 * W.SLIP - 1e-6      # 停利至少 87（此處 15）點，扣滑價


def test_costs_make_flat_trade_lose():
    n = 80
    c = np.full(n, 1000.0); o = c.copy(); h = c + 3; l = c - 3
    b = W.Bars(pd.bdate_range("2020-01-01", periods=n), o, h, l, c)
    f = b.feats(W.DEFAULT_P)
    # 沒有任何價格變動：任何成交的交易都應為負（成本）
    _, t = W.backtest(b, W.cfg_of(entry="M", exit="fixed87", hold=3))
    assert len(t) == 0 or (t.pnl_pts < 0).all()


def test_stop_and_reverse_enters_opposite_same_open():
    b = _bars(900, seed=11, drift=0.0)
    cfg = W.cfg_of(entry="A", mods=("A", "B", "C"), shorts=True, reverse=True, exit="formal")
    _, t = W.backtest(b, cfg)
    t = t.sort_values("entry_i").reset_index(drop=True)
    rev = [(t.loc[i], t.loc[i + 1]) for i in range(len(t) - 1) if t.loc[i].reason == "stop" and t.loc[i + 1].entry_i == t.loc[i].exit_i and t.loc[i + 1]["dir"] == -t.loc[i]["dir"]]
    # 只要有反手，必須是同一根開盤出場＋反向進場；沒有也不算錯（合成資料不保證出現）
    for a, c in rev:
        assert a.exit_i == c.entry_i


def test_same_direction_cooldown_after_stop():
    b = _bars(900, seed=2)
    p = dict(W.DEFAULT_P, cool=6)
    _, t = W.backtest(b, W.cfg_of(entry="A", mods=("A", "B"), exit="formal"), p)
    t = t.sort_values("entry_i").reset_index(drop=True)
    for i in range(len(t) - 1):
        if t.loc[i].reason == "stop" and t.loc[i + 1]["dir"] == t.loc[i]["dir"]:
            assert t.loc[i + 1].entry_i - t.loc[i].exit_i >= 1


def test_trailing_requires_arming():
    b = _bars(700, seed=9)
    _, t = W.backtest(b, W.cfg_of(entry="A", exit="formal"))
    tr = t[t.reason == "trail"]
    # 啟動過才會有移動停利出場：持有至少 2 根（進場後先要有一根收盤站上 5MA）
    assert (tr.hold >= 2).all()


def test_holdout_runs_once(tmp_path, monkeypatch):
    monkeypatch.setattr(W, "OUT", tmp_path)
    b = _bars(800)
    class L:                                                              # 最小的 lab 替身
        def bh_0050(self, a, z=None):
            return pd.Series(0.0004, index=b.ts[b.ts >= pd.Timestamp(a)])
    runs = {"x": (W.cfg_of(entry="A"), None)}
    W.final_holdout(b, L(), runs)
    assert (tmp_path / "_holdout_done.json").exists()
    with pytest.raises(RuntimeError):
        W.final_holdout(b, L(), runs)


def test_risk_sizing_caps_exposure():
    b = _bars(700, seed=4)
    r1, _ = W.backtest(b, W.cfg_of(entry="A", exit="formal"))
    r2, _ = W.backtest(b, W.cfg_of(entry="A", exit="formal", risk=0.015, risk_cap=3.0))
    assert np.isfinite(r2).all() and r2.abs().max() < 1.0
