"""0050／正二搭配實驗室的測試：引擎記帳、成交時點（無前視）、拆股還原、代理序列校準。"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline.compute import lev_lab as L  # noqa: E402


# ------------------------------------------------------------------ 引擎（合成資料，不碰資料湖）
def _engine_inputs(T=10):
    ON = np.zeros((T, L.K)); ID = np.zeros((T, L.K)); BOR = np.zeros(T)
    return ON, ID, BOR


def test_buy_and_hold_compounds_exactly_and_charges_one_entry_cost():
    ON, ID, BOR = _engine_inputs()
    ON[:, L.IX["A50"]] = 0.001; ID[:, L.IX["A50"]] = 0.002
    W = np.zeros((10, L.K)); W[:, L.IX["A50"]] = 1.0
    buy = np.zeros(L.K); sell = np.zeros(L.K); buy[L.IX["A50"]] = 0.01; sell[L.IX["A50"]] = 0.02
    r, turn = L.sim(ON, ID, BOR, W, np.zeros(10, bool), 0.0, buy, sell, 0, L.IX["CASH"])
    eq = np.prod(1 + r)
    # 第 0 天：先過夜（空手，現金 0 報酬）、開盤買進（成本 1%）、盤中 +0.2%；之後每天 (1.001)(1.002)
    expect = (1 - 0.01) * (1.002) * ((1.001 * 1.002) ** 9)
    assert eq == pytest.approx(expect, rel=1e-12)
    assert turn[0] == pytest.approx(1.0) and turn[1:].sum() == 0


def test_signal_trades_next_open_not_same_day():
    """目標權重在第 t 天的『開盤』才換：t 天的隔夜報酬還是舊部位的，盤中才是新部位的。"""
    ON, ID, BOR = _engine_inputs(6)
    a = L.IX["A50"]
    ON[:, a] = 0.10; ID[:, a] = 0.01                       # 隔夜 +10%（舊部位才吃得到）、盤中 +1%
    W = np.zeros((6, L.K)); W[:, L.IX["CASH"]] = 1.0
    W[3:, a] = 1.0; W[3:, L.IX["CASH"]] = 0.0              # 第 3 天開盤才買
    fl = np.zeros(6, bool); fl[3] = True
    r, _ = L.sim(ON, ID, BOR, W, fl, 0.0, np.zeros(L.K), np.zeros(L.K), 0, L.IX["CASH"])
    assert np.allclose(r[:3], 0.0)                         # 買進前完全沒吃到 +10% 的隔夜
    assert r[3] == pytest.approx(0.01)                     # 第 3 天只吃到盤中 +1%，隔夜的 +10% 沒有
    assert r[4] == pytest.approx(1.10 * 1.01 - 1)


def test_borrowing_pays_borrow_rate_and_cash_earns_rate():
    ON, ID, BOR = _engine_inputs(4)
    ON[:, L.IX["CASH"]] = 0.001; BOR[:] = 0.002
    a = L.IX["TX"]
    W = np.zeros((4, L.K)); W[:, a] = 1.5; W[:, L.IX["CASH"]] = -0.5     # 1.5 倍：借 0.5
    r, _ = L.sim(ON, ID, BOR, W, np.zeros(4, bool), 0.0, np.zeros(L.K), np.zeros(L.K), 0, L.IX["CASH"])
    assert r[1] == pytest.approx(-0.5 * 0.002 / 1.0, abs=1e-9)           # 資產報酬 0，只付借款利息（第 0 天已建倉，權重不再調）


def test_drift_band_rebalances_only_when_breached():
    ON, ID, BOR = _engine_inputs(20)
    a, b = L.IX["A50"], L.IX["L2"]
    ID[:, a] = 0.05
    W = np.zeros((20, L.K)); W[:, a] = 0.5; W[:, b] = 0.5
    r, turn = L.sim(ON, ID, BOR, W, np.zeros(20, bool), 0.10, np.zeros(L.K), np.zeros(L.K), 0, L.IX["CASH"])
    assert turn[0] > 0                                     # 起始建倉
    assert turn[1:].sum() > 0                              # 漂移超過 10 個百分點才再平衡
    first = int(np.argmax(turn[1:] > 0)) + 1
    assert first >= 3                                      # 一開始漂移不夠大，不能天天再平衡


# ------------------------------------------------------------------ 還原與訊號
def test_split_adjustment_makes_returns_continuous():
    cal = pd.bdate_range("2026-03-25", periods=6)
    df = pd.DataFrame({"date": cal.strftime("%Y-%m-%d"), "open": [400, 402, 404, 18.5, 18.6, 18.7],
                       "close": [401, 403, 405, 18.4, 18.8, 18.9], "volume": 1})
    on, idr, present, _ = L.etf_legs(df, cal)
    r = (1 + on) * (1 + idr) - 1
    assert np.abs(r).max() < 0.10                          # 1 拆 22 之後沒有 -95% 的假報酬
    assert present[1:].all()                               # 第一天沒有前收，不算


def test_missing_day_return_is_compounded_into_next_overnight_leg():
    cal = pd.bdate_range("2024-01-01", periods=5)
    df = pd.DataFrame({"date": cal[[0, 1, 3, 4]].strftime("%Y-%m-%d"), "open": [100, 100, 110, 110], "close": [100, 100, 110, 110], "volume": 1})
    on, idr, present, _ = L.etf_legs(df, cal)
    assert not present[2]
    assert on[2] == 0 and idr[2] == 0                      # 缺資料那天記 0
    assert on[3] == pytest.approx(0.10)                    # 下一個有資料日的隔夜吃掉整段缺口


def test_shift1_is_strictly_lagged():
    x = np.array([0, 1, 1, 0, 1], float)
    y = L.shift1(x)
    assert list(y) == [0, 0, 1, 1, 0]


def test_exposure_weights_sum_and_exposure():
    E = np.array([0.0, 0.5, 1.0, 1.5, 2.0])
    W = L.exposure_weights(E)
    assert np.allclose(W.sum(axis=1), 1.0)
    expo = W[:, L.IX["A50"]] + 2 * W[:, L.IX["L2"]]
    assert np.allclose(expo, E)


def test_hysteresis_and_confirmation_days():
    close = np.array([10, 11, 12, 9, 12, 12, 8, 8, 8], float)
    ma = np.full(9, 10.0)
    st = L._hyst(close, ma, 0.0, 2)
    # 需要連續 2 天才轉多／轉空
    assert list(st) == [0, 0, 1, 1, 1, 1, 1, 0, 0]


def test_stationary_bootstrap_is_deterministic_and_scale_sensible():
    rng = np.random.default_rng(0)
    r = rng.normal(0.0005, 0.01, 500); b = rng.normal(0.0003, 0.01, 500)
    d1 = L.stationary_bootstrap(r, b, 0, 500, n_rep=50, seed=3)
    d2 = L.stationary_bootstrap(r, b, 0, 500, n_rep=50, seed=3)
    assert np.allclose(d1, d2) and d1.shape == (50,)


def test_range_filter_state_is_binary_and_follows_trend():
    x = pd.Series(np.r_[np.linspace(100, 200, 200), np.linspace(200, 100, 200)], index=pd.bdate_range("2020-01-01", periods=400))
    st = L.range_filter_state(x, 15, 4.0)
    assert set(st.unique()) <= {0, 1}
    assert st.iloc[150] == 1 and st.iloc[-1] == 0


# ------------------------------------------------------------------ 資料湖（需要 data/；沒有就略過）
@pytest.fixture(scope="module")
def world():
    if not (ROOT / "data" / "price_daily").exists():
        pytest.skip("沒有資料湖")
    w = L.World(with_tx=False, with_mom=False)
    return w


def test_real_00631l_split_is_adjusted(world):
    on, idr, pres, _ = world.real["00631L"]
    r = (1 + on) * (1 + idr) - 1
    assert np.abs(r[pres]).max() < 0.25                    # 2026-03-31 的 1 拆 22 已還原


def test_proxy_is_spliced_at_listing_and_calibrated(world):
    c = world.calib
    assert world.cal[c["first_i"]] >= pd.Timestamp("2014-10-31")
    assert abs(c["cum_real"] - c["cum_proxy"]) / abs(c["cum_real"]) < 0.01      # 殘差讓上市後累積報酬對齊
    assert c["daily_corr_proxy"] > 0.95
    assert 1.7 < c["beta"] < 2.3


def test_buy_hold_matches_manual_compounding(world):
    r, _ = L.run(world, *L.build(world, "HOLD", dict(w50=0.0, w2=1.0, reb="N"))[:2])
    on = world.ON[:, L.IX["L2"]]; idr = world.ID[:, L.IX["L2"]]
    s0 = world.start_i
    # 第一天：隔夜還是現金、開盤才買進，所以只吃盤中；之後每天隔夜加盤中
    manual = (1 + idr[s0]) * np.prod((1 + on[s0 + 1:]) * (1 + idr[s0 + 1:]))
    got = np.prod(1 + r[s0:])
    cash_on = world.ON[s0, L.IX["CASH"]]
    # 只差一次買進成本與滑價（以及第一天隔夜的現金利息）
    assert got / manual == pytest.approx((1 - (L.FEE + L.SLIP["L2"])) * (1 + cash_on), rel=1e-9)


def test_ma_signal_has_no_lookahead(world):
    """把某一天『之後』的指數全部亂改，這一天（含）以前的目標權重必須完全不變。"""
    W0, _, _ = L.build(world, "MA", dict(n=60, h=0.0, m=1, on="L2", off="cash"))
    cut = int(world.cal.searchsorted(pd.Timestamp("2012-06-01")))
    saved = world.tse_full.copy()
    try:
        fake = saved.copy()
        fake[fake.index > world.cal[cut]] *= np.random.default_rng(1).uniform(0.3, 3.0, (fake.index > world.cal[cut]).sum())
        world.tse_full = fake
        W1, _, _ = L.build(world, "MA", dict(n=60, h=0.0, m=1, on="L2", off="cash"))
    finally:
        world.tse_full = saved
    assert np.allclose(W0[:cut + 1], W1[:cut + 1])
    assert not np.allclose(W0[cut + 5:], W1[cut + 5:])


def test_costs_reduce_return(world):
    W, fl, band = L.build(world, "MA", dict(n=20, h=0.0, m=1, on="L2", off="cash"))
    r_cost, turn = L.run(world, W, fl, band)
    buy, sell = world.buyc.copy(), world.sellc.copy()
    world.buyc[:] = 0; world.sellc[:] = 0
    try:
        r_free, _ = L.run(world, W, fl, band)
    finally:
        world.buyc[:], world.sellc[:] = buy, sell
    assert np.prod(1 + r_free) > np.prod(1 + r_cost)
    assert turn.sum() > 20


def test_grid_keys_unique_and_registered():
    G = L.grid()
    ks = [L.key(f, p) for f, p in G]
    assert len(ks) == len(set(ks))
    assert {"HOLD", "MA", "XO", "AM", "VOL", "TV", "DG", "TX", "TXG", "SAT", "RF", "L1US"} <= {f for f, _ in G}
