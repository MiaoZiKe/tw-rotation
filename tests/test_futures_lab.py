"""台指期研究的關鍵不變量：不偷看未來、隔日開盤成交、成本、跳空停損、結算日。"""
import numpy as np
import pandas as pd

from pipeline.compute import futures_lab as F


def _flat(n=30, px=1000.0):
    o = np.full(n, px); return o.copy(), o + 5, o - 5, o.copy()


def _sim(o, h, l, c, sl, el, k=99.0, atr=10.0, ss=None, es=None):
    n = len(c); z = np.zeros(n, bool); one = np.ones(n, bool)
    return F._sim(o, h, l, c, np.full(n, atr), sl, z if ss is None else ss, el, z if es is None else es,
                  one, one, k, 0.25, F.TAX, 2.0, 4.0, z)


def test_entry_at_next_open_not_signal_close():
    o, h, l, c = _flat()
    c[5] = 1010.0; o[6] = 1020.0; h[6] = 1030.0; c[6] = 1020.0       # 第 5 日收盤出訊號，第 6 日開 1020
    sl = np.zeros(30, bool); sl[5] = True
    el = np.zeros(30, bool)
    pnl, tr = _sim(o, h, l, c, sl, el)
    assert tr[-1][2] == 6 and tr[-1][4] == 1020.0 + 2.0              # 進場日=隔日，價=開盤+滑價，不是訊號日收盤 1010


def test_round_trip_cost_exact():
    o, h, l, c = _flat()
    sl = np.zeros(30, bool); sl[5] = True
    el = np.zeros(30, bool); el[10] = True
    pnl, tr = _sim(o, h, l, c, sl, el)
    x = tr[0]
    # 價格完全不動：虧 = 兩邊滑價 4 點 + 兩邊手續費 0.5 點 + 兩邊期交稅
    exp = -(4.0 + 0.5 + F.TAX * (1002.0 + 998.0))
    assert abs(x[7] - exp) < 1e-9
    assert abs(pnl.sum() - exp) < 1e-9                                # 逐日損益加總與交易損益一致


def test_gap_through_stop_fills_at_open():
    o, h, l, c = _flat()
    sl = np.zeros(30, bool); sl[5] = True
    el = np.zeros(30, bool)
    o[8] = 900.0; h[8] = 905; l[8] = 880; c[8] = 890               # 跳空開在停損(約 1002-3*10=972)之下
    pnl, tr = _sim(o, h, l, c, sl, el, k=3.0)
    x = tr[0]
    assert x[6] == 3 and x[5] == 900.0 - 2.0                         # 以開盤價（不是停損價）成交，再扣滑價


def test_short_symmetry_and_stop():
    o, h, l, c = _flat()
    ss = np.zeros(30, bool); ss[5] = True
    z = np.zeros(30, bool)
    h[8] = 1100.0
    pnl, tr = _sim(o, h, l, c, z, z, k=3.0, ss=ss, es=z)
    x = tr[0]
    assert x[0] == -1 and x[6] in (2, 3) and x[7] < 0


def test_weekly_regime_no_lookahead():
    idx = pd.bdate_range("2015-01-01", periods=600)
    rng = np.random.default_rng(1)
    s = pd.Series(1000 + np.cumsum(rng.normal(0, 5, len(idx))), index=idx)
    full = F.weekly_regime(s, 20)
    cut = F.weekly_regime(s.iloc[:400], 20)
    # 截斷未來資料後，已存在日期的週K 狀態不變（除了最後一個不完整週之後才可能不同的日期）
    assert (full[:395] == cut[:395]).all()


def test_signals_unchanged_when_future_removed():
    lab = F.Lab(); p = dict(fam="BRK", wma=30, N=20, M=10, k=3.0)
    sl, ss, el, es = F.build_signals("BRK", p, lab.X, True)
    n = 3000
    X2 = dict(c=lab.c[:n], atr=lab.atr[:n], rsi5=lab.X["rsi5"][:n],
              reg={w: F.weekly_regime(lab.tx.close.iloc[:n], w) for w in (20, 30, 40)},
              ma={k: v[:n] for k, v in lab.X["ma"].items()}, bas=lab.X["bas"][:n])
    sl2, ss2, el2, es2 = F.build_signals("BRK", p, X2, True)
    assert (sl[:n - 10] == sl2[:n - 10]).all() and (el[:n - 10] == el2[:n - 10]).all()


def test_settle_days_third_wednesday():
    idx = pd.bdate_range("2024-01-01", "2024-12-31")
    st = F.settle_days(idx)
    d = idx[st]
    assert len(d) == 12 and all(x.weekday() == 2 and 15 <= x.day <= 21 for x in d)


def test_verdict_rules():
    assert F.verdict(0.2, 0.19, 5, 5, 0, 0).startswith("通過")
    assert "僅加槓桿" in F.verdict(0.1, 0.19, 0, 5, 0.2, 0.3)
    assert F.verdict(0.1, 0.19, 0, 5, 0.1, 0.1) == "淘汰，不使用"
    assert "名義通過" in F.verdict(0.2, 0.19, 3, 5, 0, 0)


def test_neighbors_one_step():
    g = F.build_grid(); p = next(x for x in g if x["fam"] == "BRK" and x["N"] == 40 and x["wma"] == 30)
    nb = F.neighbors(p, g)
    assert all(sum(q[k] != p[k] for k in p) == 1 for q in nb) and len(nb) >= 4
