"""每日盤後訊號與紙上帳本（pipeline/compute/live_signals.py）的測試。
研究用，不是買賣建議，不會下單。重點：訊號不偷看未來、隔日開盤成交並扣成本、帳本只增不改。"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from pipeline import config
from pipeline.compute import live_signals as LS
from pipeline.util import store


# ------------------------------------------------------------------ 合成市場
def _walk(n, start, seed, vol=0.01):
    rng = np.random.default_rng(seed)
    return start * np.cumprod(1 + rng.normal(0.0004, vol, n))


def make_market(end="2026-11-30", seed=1):
    cal = pd.bdate_range("2025-06-02", end)
    n = len(cal)
    tse_c = _walk(n, 20000, seed)
    tse_o = np.r_[tse_c[0], tse_c[:-1]] * (1 + np.random.default_rng(seed + 1).normal(0, 0.002, n))
    fut_c = tse_c * 1.001
    fut_o = tse_o * 1.001
    def etf(base, k, sd):
        c = _walk(n, base, sd, 0.012 * k)
        o = np.r_[c[0], c[:-1]] * (1 + np.random.default_rng(sd + 7).normal(0, 0.002, n))
        return pd.DataFrame({"open": o, "close": c}, index=cal)
    codes = [f"{1100 + i}" for i in range(40)]
    sc = pd.DataFrame({c: _walk(n, 50 + i, 100 + i, 0.02) for i, c in enumerate(codes)}, index=cal)
    so = sc.shift(1).fillna(sc.iloc[0]) * 1.001
    turn = pd.DataFrame({c: np.full(n, 1e8 * (i + 1)) for i, c in enumerate(codes)}, index=cal)
    yms = [f"{y}-{m:02d}" for y, m in [(2025, i) for i in range(1, 13)] + [(2026, i) for i in range(1, 11)]]
    rev = pd.DataFrame([{"ym": ym, "code": c, "revenue": 100.0 * (1 + 0.03 * (j if i % 2 == 0 else -j / 3))} for j, ym in enumerate(yms) for i, c in enumerate(codes)])
    return {"etf": {"0050": etf(150, 1, seed + 2), "00631L": etf(36, 2, seed + 3)},
            "stk_open": so, "stk_close": sc, "stk_turn": turn,
            "idx": {"TSE": pd.DataFrame({"open": tse_o, "close": tse_c}, index=cal), "FUT": pd.DataFrame({"open": fut_o, "close": fut_c}, index=cal)},
            "div": pd.Series({pd.Timestamp("2026-11-10"): 1.0}), "rev": rev}


def truncate(mk, last):
    last = pd.Timestamp(last)
    cut = lambda df: df.loc[:last]  # noqa: E731
    return {"etf": {k: cut(v) for k, v in mk["etf"].items()}, "stk_open": cut(mk["stk_open"]), "stk_close": cut(mk["stk_close"]), "stk_turn": cut(mk["stk_turn"]),
            "idx": {k: cut(v) for k, v in mk["idx"].items()}, "div": mk["div"][mk["div"].index <= last], "rev": mk["rev"]}


@pytest.fixture()
def lake(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path / "data")
    monkeypatch.setattr(config, "STATE", tmp_path / "data" / "_state")
    (tmp_path / "data").mkdir()
    return tmp_path


# ------------------------------------------------------------------ 訊號
def test_tables_registered():
    assert config.TABLES["paper/ledger"] == ["date", "plan"]
    assert config.TABLES["paper/satellite"] == ["date", "rank"]


def test_e2_signal_hysteresis_band():
    c = pd.Series(np.r_[np.full(200, 100.0), [101.0, 103.0, 101.0, 99.0, 97.0, 99.0, 103.0]], index=pd.bdate_range("2025-01-01", periods=207))
    s = LS.e2_signal(c)
    assert s.state.iloc[199] == 0                                  # 均線剛有值：收盤 = 均線，帶內，維持 0
    assert s.state.iloc[201] == 1                                  # 103 > 均線 x 1.02 -> 線上
    assert s.state.iloc[202] == 1 and s.state.iloc[203] == 1       # 帶內維持
    assert s.state.iloc[204] == 0                                  # 97 < 均線 x 0.98 -> 線下
    assert s.state.iloc[205] == 0                                  # 99 又回到帶內，維持線下
    assert s.state.iloc[206] == 1
    assert np.allclose(s.upper, s.ma * 1.02, equal_nan=True) and np.allclose(s.lower, s.ma * 0.98, equal_nan=True)


def test_e2_signal_does_not_peek_at_future():
    mk = make_market()
    c = mk["idx"]["TSE"]["close"]
    a = LS.e2_signal(c)
    c2 = c.copy()
    c2.iloc[300:] *= np.random.default_rng(0).uniform(0.3, 3.0, len(c2) - 300)
    b = LS.e2_signal(c2)
    pd.testing.assert_frame_equal(a.iloc[:300], b.iloc[:300])      # 300 列以前完全不受後面影響
    assert not a.iloc[310:].equals(b.iloc[310:])


def test_settle_days_third_wednesday_and_roll_tomorrow():
    cal = pd.bdate_range("2026-10-01", "2026-12-31")
    sd = settle_dates = cal[LS.settle_days(cal)]
    assert list(sd.strftime("%m-%d")) == ["10-21", "11-18", "12-16"]
    info = LS.futures_calendar(pd.Timestamp("2026-11-17"))           # 週二，明天是 11-18 結算
    assert info["roll_tomorrow"] is True and info["next_settle"] == pd.Timestamp("2026-11-18")
    assert LS.futures_calendar(pd.Timestamp("2026-11-16"))["roll_tomorrow"] is False
    info = LS.futures_calendar(pd.Timestamp("2026-10-30"))           # 月底最後一天：明天(週一 11-02)是下個月第一個交易日
    assert info["check_tomorrow"] is True and info["next_check"] == pd.Timestamp("2026-11-02")


def test_f2_sizing_scales_with_nav():
    a = LS.f2_sizing(10_000_000, 46000)
    assert a["notional"] == pytest.approx(13_000_000)
    assert a["big"] == pytest.approx(13_000_000 / (46000 * 200))
    assert a["micro"] == round(13_000_000 / (46000 * 10))
    assert LS.f2_sizing(20_000_000, 46000)["big"] == pytest.approx(2 * a["big"])


def test_revenue_not_used_before_legal_availability_date():
    mk = make_market()
    r_before = LS.rev_ratio_asof(mk["rev"], pd.Timestamp("2026-10-10"))      # 2026-09 營收要等 10-11 才可用
    r_after = LS.rev_ratio_asof(mk["rev"], pd.Timestamp("2026-10-11"))
    assert not r_before.equals(r_after)
    rev2 = mk["rev"].copy()
    rev2.loc[rev2.ym == "2026-09", "revenue"] *= 5
    assert LS.rev_ratio_asof(rev2, pd.Timestamp("2026-10-10")).equals(r_before)   # 10-10 以前改 9 月營收完全無影響


def test_pick_satellite_rules():
    mk = make_market()
    sc, st = mk["stk_close"], mk["stk_turn"]
    asof = pd.Timestamp("2026-10-27")
    ratio = LS.rev_ratio_asof(mk["rev"], asof)
    pk = LS.pick_satellite(sc, st, ratio, asof)
    assert len(pk) <= LS.SAT_N and list(pk["rank"]) == list(range(1, len(pk) + 1))
    assert (pk.rev_ratio > 1.0).all() and (pk.near_high >= LS.SAT_NEAR_HIGH).all()
    assert pk.rev_ratio.is_monotonic_decreasing


# ------------------------------------------------------------------ 帳戶單日步進
def test_step_etf_trades_next_open_and_charges_cost():
    r0 = LS.step_etf(None, pd.Timestamp("2026-10-27"), 36.0, 36.5, None, "00631L", 1.0)
    assert r0["units"] == 0 and r0["nav"] == LS.CAPITAL and r0["target"] == 1.0 and np.isnan(r0["held"])
    prev = dict(cash=r0["cash"], units=r0["units"], held=r0["held"], target=r0["target"], nav=r0["nav"])
    r1 = LS.step_etf(prev, pd.Timestamp("2026-10-28"), 37.0, 38.0, 36.5, "00631L", 1.0)
    assert r1["fill"] == 37.0                                              # 以次一交易日開盤價成交
    assert r1["cost"] == pytest.approx(r1["traded"] * (LS.FEE + LS.SLIP["00631L"]), rel=1e-6)
    assert r1["units"] * 37.0 == pytest.approx(LS.CAPITAL * (1 + LS.RF / 252) / (1 + LS.FEE + LS.SLIP["00631L"]), rel=1e-4)    # 100% 買滿（成本含在內、不借錢）
    assert r1["cash"] >= -1e-6
    assert r1["nav"] == pytest.approx(r1["cash"] + r1["units"] * 38.0)
    prev2 = dict(cash=r1["cash"], units=r1["units"], held=r1["held"], target=r1["target"], nav=r1["nav"])
    r2 = LS.step_etf(prev2, pd.Timestamp("2026-10-29"), 38.0, 38.0, 38.0, "00631L", 0.3)   # 今天收盤才決定改 30%
    assert r2["fill"] is None or np.isnan(r2["fill"])                      # 今天沒有成交（昨天的目標還是 100%）
    prev3 = dict(cash=r2["cash"], units=r2["units"], held=r2["held"], target=r2["target"], nav=r2["nav"])
    r3 = LS.step_etf(prev3, pd.Timestamp("2026-10-30"), 40.0, 40.0, 38.0, "00631L", 0.3)
    assert r3["fill"] == 40.0 and r3["traded"] < 0                         # 隔天開盤才賣到 30%
    assert r3["cost"] == pytest.approx(abs(r3["traded"]) * (LS.FEE + LS.TAX + LS.SLIP["00631L"]), rel=1e-6)
    assert r3["units"] * 40.0 / (r3["cash"] + r3["units"] * 40.0) == pytest.approx(0.3, rel=1e-2)


def test_step_fut_sizing_and_monthly_check_band():
    r0 = LS.step_fut(None, pd.Timestamp("2026-10-27"), 100, 100, None, 100, None, False, False, False, None)
    prev = dict(cash=r0["cash"], notional=r0["nf"])
    r1 = LS.step_fut(prev, pd.Timestamp("2026-10-28"), 100.0, 100.0, 100.0, 100.0, 100.0, False, False, False, 100.0)
    assert r1["nf"] == pytest.approx(LS.F2_X * r1["cash"] / 1.0, rel=0.01) or r1["exposure"] == pytest.approx(LS.F2_X, rel=0.01)
    assert r1["traded"] > 0 and r1["cost"] > 0
    # 偏離 <= 0.10 倍、又是檢查日：不動
    prev2 = dict(cash=r1["cash"], notional=r1["nf"] * 1.05)
    r2 = LS.step_fut(prev2, pd.Timestamp("2026-11-02"), 100.0, 100.0, 100.0, 100.0, 100.0, False, False, True, 100.0)
    assert r2["traded"] == 0.0
    # 偏離 > 0.10 倍且不是檢查日：也不動
    prev3 = dict(cash=r1["cash"], notional=r1["nf"] * 0.8)
    assert LS.step_fut(prev3, pd.Timestamp("2026-11-03"), 100.0, 100.0, 100.0, 100.0, 100.0, False, False, False, 100.0)["traded"] == 0.0
    # 偏離 > 0.10 倍且是檢查日：調回
    r4 = LS.step_fut(prev3, pd.Timestamp("2026-11-03"), 100.0, 100.0, 100.0, 100.0, 100.0, False, False, True, 100.0)
    assert r4["traded"] > 0


# ------------------------------------------------------------------ 帳本：推進、只增不改、不偷看
def test_run_before_start_writes_nothing(lake):
    mk = truncate(make_market(), "2026-10-26")
    res = LS.run(market=mk)
    assert res["rows_added"] == 0 and "起算日" in res["status"]
    assert LS.read_ledger().empty
    assert res["signals"]["E2"]["tse_close"] > 0 and res["signals"]["disclaimer"] == LS.DISCLAIMER


def test_run_first_signal_row_and_next_open_fill(lake):
    mk = make_market()
    LS.run(market=truncate(mk, "2026-10-27"))
    led = LS.read_ledger()
    e2 = led[led.plan == "E2"]
    assert list(e2.date.dt.strftime("%Y-%m-%d")) == ["2026-10-27"]
    assert e2.iloc[0].nav == LS.CAPITAL and e2.iloc[0].units == 0           # 起算日只有訊號，沒有成交
    sig = json.loads(e2.iloc[0].sig)
    assert {"tse_close", "ma200", "upper", "lower", "state", "target_next", "switch_tomorrow"} <= set(sig)
    assert set(led.plan) == {"BENCH", "E2", "F2", "SAT"}
    assert (led.disclaimer == LS.DISCLAIMER).all()
    LS.run(market=truncate(mk, "2026-10-28"))
    led = LS.read_ledger()
    r = led[(led.plan == "E2") & (led.date == "2026-10-28")].iloc[0]
    assert r.fill_px == pytest.approx(mk["etf"]["00631L"].loc["2026-10-28", "open"])        # 隔日開盤價成交
    assert r.cost > 0 and r.units > 0
    b = led[(led.plan == "BENCH") & (led.date == "2026-10-28")].iloc[0]
    assert b.fill_px == pytest.approx(mk["etf"]["0050"].loc["2026-10-28", "open"])
    f = led[(led.plan == "F2") & (led.date == "2026-10-28")].iloc[0]
    assert f.exposure == pytest.approx(LS.F2_X, rel=0.02)
    assert f.thresh_cum == pytest.approx(f.bench_cum) and led[(led.plan == "E2") & (led.date == "2026-10-28")].iloc[0].thresh_cum == pytest.approx(1.5 * f.bench_cum)


def test_ledger_is_append_only_and_idempotent(lake):
    mk = make_market()
    LS.run(market=truncate(mk, "2026-11-05"))
    first = LS.read_ledger()
    assert LS.run(market=truncate(mk, "2026-11-05"))["rows_added"] == 0       # 重跑不新增
    pd.testing.assert_frame_equal(first, LS.read_ledger())
    LS.run(market=mk)                                                          # 再往後推
    later = LS.read_ledger()
    old = later[later.date <= "2026-11-05"].reset_index(drop=True)
    pd.testing.assert_frame_equal(first, old)                                  # 舊列一個欄位都沒變
    assert later.date.max() > first.date.max()


def test_append_only_blocks_overwrite_and_backfill(lake):
    row = lambda d, plan, nav: pd.DataFrame([LS._row(pd.Timestamp(d), plan, nav=nav)])      # noqa: E731
    assert LS.append_only(LS.T_LEDGER, row("2026-10-28", "E2", 1.0), ["date", "plan"]) == 1
    assert LS.append_only(LS.T_LEDGER, row("2026-10-28", "E2", 999.0), ["date", "plan"]) == 0      # 同 key 不覆蓋
    assert LS.append_only(LS.T_LEDGER, row("2026-10-27", "E2", 5.0), ["date", "plan"]) == 0        # 不回填更早的日子
    assert LS.append_only(LS.T_LEDGER, row("2026-10-27", "F2", 5.0), ["date", "plan"]) == 1        # 別的方案各自獨立
    led = LS.read_ledger()
    assert led[(led.plan == "E2")].nav.tolist() == [1.0]


def test_ledger_rows_do_not_peek_at_future(lake, tmp_path, monkeypatch):
    mk = make_market()
    LS.run(market=truncate(mk, "2026-11-12"))
    a = LS.read_ledger()
    # 另一個資料湖：同一天為止，但『之後』的價格被竄改——算出來的 11-12 以前的列必須一模一樣
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.setattr(config, "DATA", other)
    mk2 = make_market()
    for k in ("open", "close"):
        mk2["etf"]["00631L"].loc["2026-11-13":, k] *= 0.1
        mk2["idx"]["TSE"].loc["2026-11-13":, k] *= 0.1
        mk2["idx"]["FUT"].loc["2026-11-13":, k] *= 0.1
    mk2["stk_close"].loc["2026-11-13":] *= 0.1
    LS.run(market=mk2, asof=pd.Timestamp("2026-11-12"))
    b = LS.read_ledger()
    pd.testing.assert_frame_equal(a.drop(columns=["sig"]), b.drop(columns=["sig"]))


def test_satellite_is_recorded_with_zero_weight(lake):
    mk = make_market()
    LS.run(market=truncate(mk, "2026-11-20"))
    sat = store.read(LS.T_SAT)
    assert len(sat) > 0 and (sat.weight_pct == 0.0).all() and (sat.disclaimer == LS.DISCLAIMER).all()
    led = LS.read_ledger()
    s = led[led.plan == "SAT"]
    assert (s.target == 0.0).all()                                             # 權重 0%：不放資金


def test_main_never_raises_and_writes_state(lake, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("資料壞掉")
    monkeypatch.setattr(LS, "run", boom)
    assert LS.main() == 0
    state = json.loads((config.STATE / "live_signals.json").read_text(encoding="utf-8"))
    assert state["status"] == "error" and state["disclaimer"] == LS.DISCLAIMER
