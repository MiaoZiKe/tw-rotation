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
    assert config.TABLES["paper/e2sat_holdings"] == ["date", "code"]


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
    assert set(led.plan) == {"BENCH", "E2", "F2", "SAT", "E2SAT"}
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


def test_satellite_is_recorded_with_e2sat_weight(lake):
    mk = make_market()
    LS.run(market=truncate(mk, "2026-11-20"))
    sat = store.read(LS.T_SAT)
    assert len(sat) > 0 and (sat.weight_pct == LS.E2SAT_W_SAT).all() and (sat.disclaimer == LS.DISCLAIMER).all()
    led = LS.read_ledger()
    s = led[led.plan == "SAT"]
    assert (s.target == LS.E2SAT_W_SAT).all()                                  # 衛星在 E2SAT 內占 20%


def test_main_never_raises_and_writes_state(lake, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("資料壞掉")
    monkeypatch.setattr(LS, "run", boom)
    assert LS.main() == 0
    state = json.loads((config.STATE / "live_signals.json").read_text(encoding="utf-8"))
    assert state["status"] == "error" and state["disclaimer"] == LS.DISCLAIMER


# ------------------------------------------------------------------ E2SAT：80% E2 + 20% 衛星，每年再平衡
def test_pick_satellite_requires_ma3_per_frozen_spec():
    """凍結規格 x2=nh85 含 ma3（收盤站上 20/60/120 日線）：站不上任一條均線的不能入選。"""
    cal = pd.bdate_range("2025-01-01", periods=300)
    up = pd.Series(np.linspace(50, 100, 300), index=cal)
    dip = up.copy()
    dip.iloc[-1] = up.iloc[-1] * 0.99            # 仍在 52 週高 85% 內，但收盤跌破 20 日線以下
    dip.iloc[-30:-1] = up.iloc[-1] * 1.0
    close = pd.DataFrame({"1101": up, "1102": dip})
    turn = pd.DataFrame(1e8, index=cal, columns=close.columns)
    pk = LS.pick_satellite(close, turn, pd.Series({"1101": 1.2, "1102": 1.5}), cal[-1])
    assert list(pk.code) == ["1101"]


def test_year_rebalance_day_is_first_trading_day_of_year():
    cal = pd.bdate_range("2026-12-28", "2027-01-08")
    days = [d for i, d in enumerate(cal) if LS.is_year_rebalance_day(d, cal[i - 1] if i else None)]
    assert days == [pd.Timestamp("2027-01-01")]
    assert not LS.is_year_rebalance_day(pd.Timestamp("2026-10-27"), None)       # 起算日不算再平衡


def _e2sat(led):
    return led[led.plan == "E2SAT"].reset_index(drop=True)


def test_e2sat_starts_80_20_and_weights_drift_between_rebalances(lake):
    mk = make_market(end="2027-02-26")
    LS.run(market=truncate(mk, "2026-10-27"))
    r0 = _e2sat(LS.read_ledger()).iloc[0]
    assert r0.nav == LS.CAPITAL and r0.cash == pytest.approx(LS.CAPITAL * 0.8)          # 起算日：E2 子帳戶拿 80%
    assert json.loads(r0.extra)["sat_nav"] == pytest.approx(LS.CAPITAL * 0.2)
    LS.run(market=truncate(mk, "2026-12-31"))
    e = _e2sat(LS.read_ledger())
    w = e.apply(lambda r: json.loads(r.extra)["sat_nav"] / r.nav, axis=1)
    assert w.iloc[1:].std() > 0 and (w.iloc[1:] != 0.2).any()                           # 年中不調，權重會漂移
    assert not e.action.str.contains("年度再平衡").any()


def test_e2sat_rebalances_to_80_20_on_first_trading_day_of_year(lake):
    mk = make_market(end="2027-02-26")
    LS.run(market=truncate(mk, "2026-12-31"))
    LS.run(market=truncate(mk, "2027-01-04"))
    e = _e2sat(LS.read_ledger())
    first = pd.Timestamp("2027-01-01")                                                  # bdate_range 把元旦當交易日；真實資料湖以實際交易日為準
    row = e[e.date == first].iloc[0]
    assert "年度再平衡" in row.action
    sig = json.loads(row.sig)
    # 再平衡在開盤；收盤時兩邊各自漲跌，所以收盤權重只會「接近」20%，開盤一刻才是 20%
    assert sig["sat_weight"] == pytest.approx(0.2, abs=0.03)
    assert row.cost > 0
    assert e[e.date > first].action.str.contains("年度再平衡").sum() == 0                # 同一年只調一次


def test_e2sat_rebalance_exact_80_20_at_open_when_flat(lake):
    """把元旦當天價格全部壓平（開=收=昨收），收盤權重就等於開盤再平衡後的權重 -> 應是精準的 80/20（扣掉成本前後差在成本量級）。"""
    mk = make_market(end="2027-02-26")
    d = pd.Timestamp("2027-01-01")
    prev = mk["etf"]["00631L"].index[mk["etf"]["00631L"].index.get_loc(d) - 1]
    mk["etf"]["00631L"].loc[d, ["open", "close"]] = mk["etf"]["00631L"].loc[prev, "close"]
    mk["stk_open"].loc[d] = mk["stk_close"].loc[prev]
    mk["stk_close"].loc[d] = mk["stk_close"].loc[prev]
    LS.run(market=truncate(mk, "2027-01-04"))
    row = _e2sat(LS.read_ledger()).query("date == @d").iloc[0]
    sig = json.loads(row.sig)
    assert sig["sat_weight"] == pytest.approx(0.2, abs=0.004)
    assert sig["e2_value"] / row.nav == pytest.approx(0.8, abs=0.004)


def test_e2sat_sleeve_costs_and_next_open_fill(lake):
    mk = make_market()
    LS.run(market=truncate(mk, "2026-10-28"))
    r = _e2sat(LS.read_ledger()).iloc[1]
    assert r.fill_px == pytest.approx(mk["etf"]["00631L"].loc["2026-10-28", "open"])    # 隔日開盤價成交
    assert r.cost > 0 and r.units > 0
    assert r.nav == pytest.approx(json.loads(r.extra)["sat_nav"] + r.cash + r.units * mk["etf"]["00631L"].loc["2026-10-28", "close"])


def test_e2sat_does_not_peek_at_future_and_is_append_only(lake, tmp_path, monkeypatch):
    mk = make_market(end="2027-02-26")
    LS.run(market=truncate(mk, "2027-01-12"))
    a = _e2sat(LS.read_ledger())
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.setattr(config, "DATA", other)
    mk2 = make_market(end="2027-02-26")
    for k in ("open", "close"):
        mk2["etf"]["00631L"].loc["2027-01-13":, k] *= 0.1
        mk2["idx"]["TSE"].loc["2027-01-13":, k] *= 0.1
    mk2["stk_close"].loc["2027-01-13":] *= 0.1
    mk2["stk_open"].loc["2027-01-13":] *= 0.1
    LS.run(market=mk2, asof=pd.Timestamp("2027-01-12"))
    b = _e2sat(LS.read_ledger())
    pd.testing.assert_frame_equal(a, b)                                                 # asof 以後的資料被竄改，E2SAT 的列一模一樣
    monkeypatch.undo()
    # 只增不改：同一個湖再往後推，舊列完全不變
    monkeypatch.setattr(config, "DATA", lake / "data")
    monkeypatch.setattr(config, "STATE", lake / "data" / "_state")
    LS.run(market=mk)
    later = _e2sat(LS.read_ledger())
    pd.testing.assert_frame_equal(a, later[later.date <= a.date.max()].reset_index(drop=True))
    assert LS.run(market=mk)["rows_added"] == 0


def test_e2sat_holdings_table_written(lake):
    mk = make_market()
    LS.run(market=truncate(mk, "2026-11-20"))
    h = store.read(LS.T_E2SAT)
    assert {"E2", "SAT"} <= set(h.sleeve) and "00631L" in set(h.code)
    last = h[h.date == h.date.max()]
    assert last.weight.sum() == pytest.approx(1.0, abs=0.02)
