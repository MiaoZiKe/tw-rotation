"""淘汰賽引擎的底線測試：不依賴資料湖，用合成資料驗證紅線。
重點是『訊號 t 日收盤 → t+1 開盤成交』『成本有扣』『停損跳空以開盤價成交』『基因操作不產生非法策略』。"""
import math
import random

import numpy as np

from pipeline.compute import tournament as T


def _flat(nd=40, nj=1, px=100.0):
    O = np.full((nd, nj), px)
    return O.copy(), O.copy(), O.copy(), O.copy(), np.full((nd, nj), 2.0)


def _run(O, H, L, C, A, sig, **kw):
    p = dict(stopk=2.0, rr=0.0, trailk=0.0, maxhold=10, risk=0.02, maxpos=1)
    p.update(kw)
    score = np.ones_like(O)
    ex = np.zeros(O.shape, dtype=bool)
    return T._sim(O, H, L, C, A, sig, score, ex, 5, O.shape[0] - 1, p["stopk"], p["rr"], p["trailk"], p["maxhold"], p["risk"], p["maxpos"],
                  T.CASH0, T.FEE, T.TAX, T.SLIP, T.MINFEE, T.COOL, 100)


def test_entry_is_next_open_not_signal_close():
    O, H, L, C, A = _flat()
    C[10] = 100.0
    O[11] = 105.0        # 隔天開盤 105（漲 5%，非漲停）
    H[11:] = 106
    L[11:] = 104
    C[11:] = 105
    O[12:] = 105
    sig = np.zeros(O.shape, dtype=bool)
    sig[10, 0] = True    # 訊號在第 10 天收盤
    out = T._sim(O, H, L, C, A, sig, np.ones_like(O), np.zeros(O.shape, dtype=bool), 5, 39, 2.0, 0.0, 0.0, 10, 0.02, 1, T.CASH0, T.FEE, T.TAX, T.SLIP, T.MINFEE, T.COOL, 100)
    assert out[1] >= 1
    assert out[2][0] == 0 and out[3][0] == 11, "進場日必須是訊號日的下一天"
    assert abs(out[5][0] - 105.0) < 1e-9, "進場價必須是隔日開盤價，不是訊號日收盤 100"


def test_costs_are_charged_on_flat_price():
    O, H, L, C, A = _flat()
    sig = np.zeros(O.shape, dtype=bool)
    sig[10, 0] = True
    out = _run(O, H, L, C, A, sig, maxhold=3)
    ret = out[8]
    assert len(ret) == 1
    # 價格完全不動：虧損 = 買賣滑價 0.2% + 手續費 0.285% + 證交稅 0.3% 左右
    assert -0.0105 < ret[0] < -0.0075, ret[0]


def test_gap_down_fills_at_open_not_stop():
    O, H, L, C, A = _flat()
    sig = np.zeros(O.shape, dtype=bool)
    sig[10, 0] = True
    O[13:] = 80.0        # 持有期間跳空跌到 80，遠低於停損 96
    H[13:] = 81
    L[13:] = 79
    C[13:] = 80
    out = _run(O, H, L, C, A, sig, maxhold=20)
    assert abs(out[6][0] - 80.0) < 1e-9, "跳空跌破停損要以開盤價成交（保守），不是以停損價"


def test_limit_up_open_is_skipped():
    O, H, L, C, A = _flat()
    C[10] = 100.0
    O[11] = 109.6        # 開盤鎖漲停（>= +9.5%）買不到
    H[11:] = 110
    L[11:] = 109
    C[11:] = 109.6
    O[12:] = 109.6
    sig = np.zeros(O.shape, dtype=bool)
    sig[10, 0] = True
    out = _run(O, H, L, C, A, sig)
    assert out[1] == 0


def test_genome_ops_stay_valid():
    rng = random.Random(3)
    for cls, cats in T.CLASS_SET.items():
        g = T.rand_genome(cats, rng)
        assert T.gclass(g) == cls
        assert any(c["k"] not in T.FILTERS for cat in T.CATS for c in g[cat]), "至少要有一個真正的進場觸發條件"
        for _ in range(30):
            g = T.mutate(g, rng, 2)
            h = T.crossover(g, T.rand_genome(cats, rng), rng, cats)
            assert set(T.active_cats(h)) == set(cats)
            for cat in T.CATS:
                for c in h[cat]:
                    assert c["k"] in T.GRID[cat]
            assert T.describe(h)


def test_deflated_sharpe_penalizes_many_trials():
    rng = np.random.default_rng(0)
    r = rng.normal(0.0006, 0.01, 2250)
    _, _, d1 = T.deflated_sharpe(r, 10, 1e-3)
    _, _, d2 = T.deflated_sharpe(r, 15000, 1e-3)
    assert d2 < d1, "試越多策略，同一個 Sharpe 的顯著性越低"
    assert 0 <= d2 <= 1
