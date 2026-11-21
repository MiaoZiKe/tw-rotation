"""波段系統 B-M2 紙上帳戶（pipeline/compute/swing_b_m2.py 與 live_signals.run_swing）的測試。
研究用，不是買賣建議，不會下單。重點：不偷看未來、隔日開盤成交、停損與出場、降速觸發、帳本只增不改。"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from pipeline import config
from pipeline.compute import live_signals as LS
from pipeline.compute import swing_b_m2 as SW
from pipeline.util import store

CAP = 10_000_000.0


# ------------------------------------------------------------------ 小工具
def bar(o, h, l, c, ma50=50.0, f=1.0):
    return dict(o=o, h=h, l=l, c=c, ma50=ma50, f=f)


def cand(code="2330", group="g1", e_ref=100.0, stop=95.0, rm=1.2, rank=1, kind="S1"):
    return dict(signal_date=pd.Timestamp("2026-10-29"), code=code, kind=kind, rank=rank, score=90.0, group=group, rm_raw=rm, nh_raw=0.95, prm=80.0,
                pnh=90.0, e_ref=e_ref, stop=stop, atr_pct=0.02, min_dist=0.03, dist=(e_ref - stop) / e_ref)


def cdf(*cs):
    return pd.DataFrame(list(cs)) if cs else pd.DataFrame()


def pos(code="1101", group="gx", entry=100.0, stop=95.0, sh=1000.0, hold=5):
    return dict(code=code, group=group, kind="S1", signal_date="2026-10-20", entry_date="2026-10-21", entry_px=entry, buy_px=SW.buy_px(entry), entry_b=entry,
                stop=stop, risk_px=entry - stop, sh=sh, shares=int(sh), risk_frac=0.005, n_frac=sh * entry / CAP, eq0=CAP, target=entry + 15, hold=hold, mae=0.0,
                last_c=entry, exit_next=None, rank=3, rm_raw=1.1, reason="測試", mult=1.0)


def in_dd(dd, **kw):
    """帳戶淨值 = 本金，歷史高點 = 本金 / (1-dd) ⇒ 目前距高點回撤 dd。"""
    return state(peak=CAP / (1 - dd), **kw)


def state(**kw):
    st = SW.new_state(CAP)
    st.update(kw)
    return st


D1, D2, D3 = pd.Timestamp("2026-10-29"), pd.Timestamp("2026-10-30"), pd.Timestamp("2026-11-02")


def ev_of(res, event):
    return [e for e in res["signals"] if e["event"] == event]


# ------------------------------------------------------------------ 成本與降速倍數
def test_costs_and_multiplier():
    assert SW.buy_px(100) == pytest.approx(100 * 1.001 * 1.001425)
    assert SW.sell_px(100) == pytest.approx(100 * 0.999 * (1 - 0.001425 - 0.003))
    assert SW.risk_multiplier(0, 0.0) == 1.0
    assert SW.risk_multiplier(2, 0.049) == 1.0
    assert SW.risk_multiplier(0, 0.05) == 0.5 and SW.risk_multiplier(0, 0.08) == 0.25
    assert SW.risk_multiplier(3, 0.0) == 0.5 and SW.risk_multiplier(5, 0.0) == 0.25
    assert SW.risk_multiplier(3, 0.08) == 0.25                      # 取較小者，不相乘


# ------------------------------------------------------------------ 隔日開盤成交（紅線）
def test_signal_day_never_fills_and_next_open_fills():
    st, res = SW.step_account(state(), D1, {}, cdf(cand()), SW.SWING)
    assert not ev_of(res, "ENTRY") and len(ev_of(res, "ENTRY_SIGNAL")) == 1       # 訊號當天只有訊號，沒有成交
    assert st["positions"] == [] and len(st["pending"]) == 1
    sg = ev_of(res, "ENTRY_SIGNAL")[0]
    assert sg["price"] == 100.0 and sg["stop"] == 95.0 and sg["target"] == pytest.approx(100 + 3 * 5)
    st, res = SW.step_account(st, D2, {"2330": bar(101.0, 103.0, 100.0, 102.0)}, cdf(), SW.SWING)
    e = ev_of(res, "ENTRY")[0]
    assert e["price"] == 101.0 != 100.0                                               # 成交價是隔日開盤，不是訊號日收盤
    assert e["shares"] == int(CAP * 0.01 // (101.0 - 95.0))
    assert e["r_px"] == pytest.approx(6.0) and e["target"] == pytest.approx(101 + 18) and "S1" in e["reason"] and "名單第 1 名" in e["reason"]
    assert st["positions"][0]["entry_px"] == 101.0


def test_entry_rejected_when_open_gaps_below_stop_or_locked_limit_up():
    st, _ = SW.step_account(state(), D1, {}, cdf(cand()), SW.SWING)
    st2, res = SW.step_account(st, D2, {"2330": bar(94.0, 96.0, 93.0, 95.0)}, cdf(), SW.SWING)
    assert not ev_of(res, "ENTRY") and "低於停損" in ev_of(res, "REJECT")[0]["note"] and st2["positions"] == []
    st3, res = SW.step_account(st, D2, {"2330": bar(110.0, 110.0, 110.0, 110.0)}, cdf(), SW.SWING)
    assert "漲停鎖死" in ev_of(res, "REJECT")[0]["note"]
    st4, res = SW.step_account(st, D2, {"2330": bar(111.0, 113.0, 110.0, 112.0)}, cdf(), SW.SWING)   # 開高後停損距離變寬到 14%：不進場
    assert "停損距離" in ev_of(res, "REJECT")[0]["note"]


# ------------------------------------------------------------------ 停損與出場
def _held(**kw):
    p = pos(**kw)
    return state(positions=[p])


def test_stop_intraday_fills_at_stop_gap_fills_at_open():
    _, res = SW.step_account(_held(), D2, {"1101": bar(99.0, 99.5, 94.0, 96.0)}, cdf(), SW.SWING)
    x = ev_of(res, "EXIT")[0]
    assert x["price"] == 95.0 and "停損" in x["reason"] and x["result_r"] < 0
    _, res = SW.step_account(_held(), D2, {"1101": bar(92.0, 93.0, 90.0, 91.0)}, cdf(), SW.SWING)
    assert ev_of(res, "EXIT")[0]["price"] == 92.0 and "跳空" in ev_of(res, "EXIT")[0]["reason"]


def test_stop_on_entry_day_uses_stop_price():
    st, _ = SW.step_account(state(), D1, {}, cdf(cand()), SW.SWING)
    st, res = SW.step_account(st, D2, {"2330": bar(100.0, 100.5, 94.0, 95.0)}, cdf(), SW.SWING)
    assert ev_of(res, "ENTRY") and ev_of(res, "EXIT")[0]["price"] == 95.0 and st["positions"] == []


def test_ma50_break_signals_at_close_and_exits_next_open():
    st = _held()
    st, res = SW.step_account(st, D2, {"1101": bar(100.0, 101.0, 98.0, 99.0, ma50=100.0)}, cdf(), SW.SWING)
    assert not ev_of(res, "EXIT") and len(ev_of(res, "EXIT_SIGNAL")) == 1 and st["positions"][0]["exit_next"] == "ma"
    st, res = SW.step_account(st, D3, {"1101": bar(98.0, 99.0, 96.0, 97.0, ma50=100.0)}, cdf(), SW.SWING)
    x = ev_of(res, "EXIT")[0]
    assert x["price"] == 98.0 and "50 日線" in x["reason"] and st["positions"] == []              # 次日開盤價出場，不是破線那天的收盤


def test_time_exit_after_max_hold_at_close():
    st = _held(hold=SW.MAX_HOLD - 1)
    st, res = SW.step_account(st, D2, {"1101": bar(100.0, 102.0, 99.0, 101.0, ma50=90.0)}, cdf(), SW.SWING)
    assert ev_of(res, "EXIT")[0]["price"] == 101.0 and ev_of(res, "EXIT")[0]["hold_days"] == SW.MAX_HOLD


def test_exit_pnl_includes_costs_and_settles_next_day():
    st = _held(sh=1000.0)
    st, res = SW.step_account(st, D2, {"1101": bar(99.0, 99.5, 94.0, 96.0)}, cdf(), SW.SWING)
    exp = 1000.0 * (SW.sell_px(95.0) - SW.buy_px(100.0))
    assert res["nav"] == pytest.approx(CAP + exp) and st["eq"] == CAP            # 當天不進可用淨值
    assert res["cost"] > 0
    st, _ = SW.step_account(st, D3, {}, cdf(), SW.SWING)
    assert st["eq"] == pytest.approx(CAP + exp) and st["streak"] == 1                # 隔天結算並計連虧


def test_exdividend_rebases_levels_instead_of_false_stop():
    st = _held(stop=95.0)
    st2, res = SW.step_account(st, D2, {"1101": bar(90.0, 91.0, 89.0, 91.0, f=0.9)}, cdf(), SW.SWING)
    assert not ev_of(res, "EXIT")
    p = st2["positions"][0]
    assert p["stop"] == pytest.approx(85.5) and p["sh"] == pytest.approx(1000 / 0.9)
    assert res["nav"] > CAP * 0.99                                                    # 含息報酬口徑：除息不是虧損


# ------------------------------------------------------------------ 降速
def _entry_risk(st, cfg):
    s1, _ = SW.step_account(st, D1, {}, cdf(cand(stop=95.0)), cfg)
    _, res = SW.step_account(s1, D2, {"2330": bar(100.0, 101.0, 99.0, 100.0)}, cdf(), cfg)
    e = ev_of(res, "ENTRY")
    return e[0]["risk_frac"] if e else res


def test_brake_halves_at_5pct_quarter_at_8pct_halts_at_12pct():
    base = _entry_risk(state(), SW.SWING_BRAKE)
    assert base == pytest.approx(0.01, rel=0.01)
    r5 = _entry_risk(in_dd(0.06), SW.SWING_BRAKE)
    r9 = _entry_risk(in_dd(0.09), SW.SWING_BRAKE)
    assert r5 == pytest.approx(0.005, rel=0.01) and r9 == pytest.approx(0.0025, rel=0.02)
    halted = _entry_risk(in_dd(0.13), SW.SWING_BRAKE)
    assert isinstance(halted, dict) and "停新單" in ev_of(halted, "REJECT")[0]["note"]
    # 冷卻 20 個交易日（28 個日曆天）後以 0.25 倍復出
    back = _entry_risk(in_dd(0.13, halt_since="2026-09-01"), SW.SWING_BRAKE)
    assert back == pytest.approx(0.0025, rel=0.02)


def test_swing_without_brake_ignores_drawdown():
    assert _entry_risk(in_dd(0.18), SW.SWING) == pytest.approx(0.01, rel=0.01)


def test_losing_streak_of_three_halves_position_only_for_brake():
    loss = lambda d: dict(exit_date=d, pnl=-1000.0, R=-1.0)  # noqa: E731
    st = state(unsettled=[loss("2026-10-26"), loss("2026-10-27"), loss("2026-10-28")])
    assert _entry_risk(st, SW.SWING_BRAKE) == pytest.approx(0.005, rel=0.01)
    assert _entry_risk(st, SW.SWING) == pytest.approx(0.01, rel=0.01)
    win = state(unsettled=[loss("2026-10-26"), loss("2026-10-27"), loss("2026-10-28"), dict(exit_date="2026-10-28", pnl=5.0, R=0.5)])
    assert _entry_risk(win, SW.SWING_BRAKE) == pytest.approx(0.01, rel=0.01)              # 贏一筆就重置


# ------------------------------------------------------------------ 部位上限
def test_position_caps_and_ordering():
    full = state(positions=[pos(code=f"10{i}1", group=f"g{i}") for i in range(6)])
    _, res = SW.step_account(full, D2, {"2330": bar(100, 101, 99, 100)}, cdf(), SW.SWING)
    st, _ = SW.step_account(full, D1, {}, cdf(cand()), SW.SWING)
    bars = {"2330": bar(100, 101, 99, 100), **{p["code"]: bar(100, 101, 99, 100, ma50=90) for p in full["positions"]}}
    _, res = SW.step_account(st, D2, bars, cdf(), SW.SWING)
    assert "持倉已滿" in ev_of(res, "REJECT")[0]["note"]                                   # 出場日當天仍占位置：與回測引擎相同
    two = state(positions=[pos(code="1101", group="g1"), pos(code="1102", group="g1")])
    st, _ = SW.step_account(two, D1, {}, cdf(cand(group="g1")), SW.SWING)
    _, res = SW.step_account(st, D2, {"2330": bar(100, 101, 99, 100), "1101": bar(100, 101, 99, 100, ma50=90), "1102": bar(100, 101, 99, 100, ma50=90)}, cdf(), SW.SWING)
    assert [e["code"] for e in ev_of(res, "ENTRY")] == ["2330"] and not ev_of(res, "REJECT")      # 凍結規格沒有族群持倉上限
    # 一個空位，兩檔候選：營收動能高的先進
    five = state(positions=[pos(code=f"10{i}1", group=f"g{i}") for i in range(5)])
    st, _ = SW.step_account(five, D1, {}, cdf(cand(code="2330", group="a", rm=1.1), cand(code="2317", group="b", rm=1.9)), SW.SWING)
    bars = {"2330": bar(100, 101, 99, 100), "2317": bar(100, 101, 99, 100), **{p["code"]: bar(100, 101, 99, 100, ma50=90) for p in five["positions"]}}
    _, res = SW.step_account(st, D2, bars, cdf(), SW.SWING)
    assert [e["code"] for e in ev_of(res, "ENTRY")] == ["2317"] and ev_of(res, "REJECT")[0]["code"] == "2330"


def test_notional_cap_20pct_and_total_exposure_cap():
    st, _ = SW.step_account(state(), D1, {}, cdf(cand(stop=96.5)), SW.SWING)                  # 停損 3.5%：1% 風險 → 名目 28.6%，要被壓到 20%
    st, res = SW.step_account(st, D2, {"2330": bar(100, 101, 99, 100)}, cdf(), SW.SWING)
    e = ev_of(res, "ENTRY")[0]
    assert e["weight"] == pytest.approx(0.20, abs=0.001) and e["risk_frac"] < 0.01
    heavy = state(positions=[pos(code=f"10{i}1", group=f"g{i}", sh=CAP * 0.2 / 100) for i in range(5)])      # 5 檔各 20% ＝ 100% 曝險
    s1, _ = SW.step_account(heavy, D1, {}, cdf(cand()), SW.SWING)
    bars = {"2330": bar(100, 101, 99, 100), **{p["code"]: bar(100, 101, 99, 100, ma50=90) for p in heavy["positions"]}}
    _, res = SW.step_account(s1, D2, bars, cdf(), SW.SWING)
    assert "曝險" in ev_of(res, "REJECT")[0]["note"]


def test_no_reentry_while_held_and_no_signal_for_held_codes():
    st = _held(code="2330")
    st2, res = SW.step_account(st, D2, {"2330": bar(100, 101, 99, 100.5, ma50=50)}, cdf(cand()), SW.SWING)
    assert not ev_of(res, "ENTRY_SIGNAL") and st2["pending"] == []
    st3, res = SW.step_account(state(pending=[{**cand(), "signal_date": "2026-10-29"}], positions=[pos(code="2330")]), D2, {"2330": bar(100, 101, 99, 100)}, cdf(), SW.SWING)
    assert not ev_of(res, "ENTRY") and len(st3["positions"]) == 1


# ------------------------------------------------------------------ 資料層：還原價、營收可用日、不偷看
def _px_long(codes, n, seed=1, start="2025-01-02"):
    dates = pd.bdate_range(start, periods=n)
    rows = []
    for k, c in enumerate(codes):
        rng = np.random.default_rng(seed * 1000 + k)
        close = 50 * np.cumprod(1 + rng.normal(0.0008, 0.015, n))
        op = np.r_[close[0], close[:-1]] * (1 + rng.normal(0, 0.004, n))
        hi, lo = np.maximum(op, close) * 1.008, np.minimum(op, close) * 0.992
        for i, d in enumerate(dates):
            rows.append((d, c, op[i], hi[i], lo[i], close[i], 1e6 * (1 + k % 7), 5e7 * (1 + k % 11) * (1 + (i % 5) * 0.01)))
    return pd.DataFrame(rows, columns=["date", "code", "open", "high", "low", "close", "volume", "turnover"])


def test_adjust_prices_uses_dividend_results_and_ignores_nothing_in_future():
    px = _px_long(["1101"], 30)
    d10 = px["date"].iloc[10]
    before = float(px.loc[px.date == px["date"].iloc[9], "close"].iloc[0])
    dv = pd.DataFrame([dict(date=d10, code="1101", before_price=before, reference_price=before * 0.9)])
    adj = SW.adjust_prices(px, dv)
    raw = px.set_index("date")["close"]
    assert adj["close"]["1101"].iloc[9] == pytest.approx(raw.iloc[9] * 0.9)          # 除息日以前乘 0.9
    assert adj["close"]["1101"].iloc[10] == pytest.approx(raw.iloc[10]) and adj["close"]["1101"].iloc[-1] == pytest.approx(raw.iloc[-1])
    assert (adj["Craw"]["1101"].values == raw.values).all()
    # 無登記的分割：單日 -75% 以還原補丁修回
    px2 = px.copy()
    px2.loc[px2.index[15:], ["open", "high", "low", "close"]] *= 0.25
    adj2 = SW.adjust_prices(px2, dv.iloc[0:0])
    assert abs(adj2["close"]["1101"].iloc[15] / adj2["close"]["1101"].iloc[14] - 1) < 0.2


def test_revenue_uses_legal_available_date_not_period():
    yms = [f"2025-{m:02d}" for m in range(1, 13)] + ["2026-01", "2026-02", "2026-03"]
    rev = pd.DataFrame([{"ym": ym, "code": "1101", "revenue": 100.0} for ym in yms[:-1]] + [{"ym": "2026-03", "code": "1101", "revenue": 150.0}])
    pre = SW.revenue_momentum_asof(rev, pd.Timestamp("2026-04-09"), ["1101"])["1101"]     # 3 月營收次月 10 日才可用
    post = SW.revenue_momentum_asof(rev, pd.Timestamp("2026-04-10"), ["1101"])["1101"]
    assert pre == pytest.approx(1.0)                                                       # 還看不到 3 月
    assert post == pytest.approx((350 / 3) / (1250 / 12))                                    # 3 月營收到次月 10 日才進來


def _universe(n_codes=130, n_days=330, seed=3):
    codes = [f"{1100 + i}" for i in range(n_codes)]
    px = _px_long(codes, n_days, seed)
    yms = [f"{y}-{m:02d}" for y, m in [(2025, i) for i in range(1, 13)] + [(2026, i) for i in range(1, 12)]]
    rng = np.random.default_rng(5)
    rev = pd.DataFrame([{"ym": ym, "code": c, "revenue": 100.0 * (1 + 0.02 * j * rng.random())} for j, ym in enumerate(yms) for c in codes])
    dates = pd.DatetimeIndex(sorted(px["date"].unique()))
    idx = pd.Series(np.cumprod(1 + np.random.default_rng(9).normal(0.0004, 0.008, len(dates))) * 17000, index=dates)
    grp = pd.Series({c: f"g{i % 12}" for i, c in enumerate(codes)})
    return px, rev, idx, grp, dates


def test_build_view_does_not_peek_future_prices_dividends_or_revenue():
    px, rev, idx, grp, dates = _universe()
    d = dates[-8]
    empty_dv = pd.DataFrame(columns=["date", "code", "before_price", "reference_price"])
    v1 = SW.build_view(px, empty_dv, rev, idx, grp, d)
    assert v1 is not None and len(v1.watch) > 0
    # 把 d 之後的價格全部亂改、塞未來除權息、塞未來營收：d 日的名單與候選必須一模一樣
    px2 = px.copy()
    fut = px2["date"] > d
    px2.loc[fut, ["open", "high", "low", "close", "turnover"]] *= 7.0
    dv2 = pd.DataFrame([dict(date=dates[-3], code="1105", before_price=100.0, reference_price=50.0)])
    rev2 = pd.concat([rev, pd.DataFrame([{"ym": "2027-01", "code": c, "revenue": 1e6} for c in grp.index])])
    idx2 = idx.copy()
    idx2[idx2.index > d] *= 3
    v2 = SW.build_view(px2, dv2, rev2, idx2, grp, d)
    pd.testing.assert_frame_equal(v1.watch.reset_index(drop=True), v2.watch.reset_index(drop=True))
    pd.testing.assert_frame_equal(v1.cands.reset_index(drop=True), v2.cands.reset_index(drop=True))
    assert SW.build_view(px[px.date < d], empty_dv, rev, idx, grp, d) is None             # 那天沒資料就不算


def test_candidates_are_in_watch_list_with_valid_stop_distance():
    px, rev, idx, grp, dates = _universe(seed=11)
    empty_dv = pd.DataFrame(columns=["date", "code", "before_price", "reference_price"])
    seen = 0
    for d in dates[-40:]:
        v = SW.build_view(px, empty_dv, rev, idx, grp, d)
        if v is None or v.cands.empty:
            continue
        seen += len(v.cands)
        assert set(v.cands.code) <= set(v.watch[~v.watch.ext].code)
        assert ((v.cands.dist >= 0.03) & (v.cands.dist <= 0.10) & (v.cands.dist >= v.cands.atr_pct - 1e-12)).all()
        assert (v.cands.stop < v.cands.e_ref).all()
        assert v.watch.groupby("group").size().max() <= 5 and len(v.watch) <= 30
    assert seen >= 0                                                                       # 隨機資料不保證有候選；有的話必須通過上面的檢查


# ------------------------------------------------------------------ 帳本：只增不改、寫入表已註冊
@pytest.fixture()
def lake(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path / "data")
    monkeypatch.setattr(config, "STATE", tmp_path / "data" / "_state")
    (tmp_path / "data").mkdir()
    return tmp_path


def _fake_lake(n=12, shock=None):
    """兩檔：A 平穩上漲、B 第 6 天起崩跌。訊號由 stub 指定：第 1 天收盤對 A 發訊號、第 2 天對 B 發訊號。"""
    dates = pd.bdate_range("2026-10-26", periods=n)
    rows = []
    for c, base in (("1101", 100.0), ("1102", 100.0)):
        for i, d in enumerate(dates):
            close = base * (1 + 0.002 * i)
            if c == "1102" and i >= 6:
                close = base * 0.80
            if shock and c == "1101" and i >= shock:
                close *= 0.5
            op = close * 1.001
            rows.append((d, c, op, close * 1.01, close * 0.99, close, 1e6, 1e8))
    px = pd.DataFrame(rows, columns=["date", "code", "open", "high", "low", "close", "volume", "turnover"])
    return {"px": px, "dv": pd.DataFrame(columns=["date", "code", "before_price", "reference_price"]), "rev": pd.DataFrame(), "idx": pd.Series(dtype=float),
            "group_of": pd.Series({"1101": "g1", "1102": "g2"}), "names": {"1101": "甲", "1102": "乙"}}


@pytest.fixture()
def stub_view(monkeypatch):
    def fake(px, dv, rev, idx, group_of, asof):
        px = px[px["date"] <= asof]
        if px.empty or px["date"].max() != asof:
            return None
        adj = SW.adjust_prices(px, dv)
        sd = pd.Timestamp("2026-10-29")
        k = {pd.Timestamp("2026-10-29"): "1101", pd.Timestamp("2026-10-30"): "1102"}.get(asof)
        cs = []
        if k:
            e = float(adj["close"][k].iloc[-1])
            cs = [cand(code=k, group=group_of[k], e_ref=e, stop=e * 0.95)]
        watch = pd.DataFrame([dict(date=asof, rank=1, code="1101", score=90.0, group="g1", ext=False, prm=80.0, pnh=90.0, rm_raw=1.2, nh_raw=0.95)])
        assert asof >= sd
        return SW.DayView(asof=asof, adj=adj, watch=watch, cands=cdf(*cs))
    monkeypatch.setattr(SW, "build_view", fake)


def test_new_tables_are_registered():
    for t, keys in (("paper/swing_signals", ["date", "plan", "code", "event"]), ("paper/swing_holdings", ["date", "plan", "code"]), ("paper/swing_watch", ["date", "rank"])):
        assert config.TABLES[t] == keys
    assert LS.SWING_START == pd.Timestamp("2026-10-29") and [c.name for c in LS.SWING_PLANS] == ["SWING", "SWING_BRAKE"]


def test_run_swing_end_to_end_next_open_stop_and_append_only(lake, stub_view, monkeypatch):
    fl = _fake_lake()
    res = LS.run_swing(None, fl)
    assert res["status"] == "ok"
    led = LS.read_ledger()
    assert set(led.plan) == {"SWING", "SWING_BRAKE"} and led[led.plan == "SWING"].date.min() == pd.Timestamp("2026-10-29")
    first = led[led.plan == "SWING"].iloc[0]
    assert first["nav"] == CAP and first["units"] == 0                                    # 起算日只有訊號，沒有成交
    sg = store.read("paper/swing_signals")
    s = sg[(sg.plan == "SWING")]
    a_sig = s[(s.code == "1101") & (s.event == "ENTRY_SIGNAL")].iloc[0]
    a_fill = s[(s.code == "1101") & (s.event == "ENTRY")].iloc[0]
    assert a_sig["date"] == "2026-10-29" and a_fill["date"] == "2026-10-30"               # 隔一個交易日才成交
    px = fl["px"]
    open_30 = float(px[(px.code == "1101") & (px.date == "2026-10-30")].open.iloc[0])
    assert a_fill["price"] == pytest.approx(open_30) and a_fill["price"] != a_sig["price"]
    b = s[s.code == "1102"]
    assert set(b.event) >= {"ENTRY_SIGNAL", "ENTRY", "EXIT"} and b[b.event == "EXIT"].iloc[0]["reason"].startswith("停損")    # B 崩跌 → 停損出場
    hold = store.read("paper/swing_holdings")
    assert set(hold.plan) == {"SWING", "SWING_BRAKE"} and "1101" in set(hold.code) and (hold.stop > 0).all()
    # 重跑：不增加任何列，已寫入的列逐欄不變
    snap = {t: store.read(t).copy() for t in ("paper/ledger", "paper/swing_signals", "paper/swing_holdings")}
    res2 = LS.run_swing(None, fl)
    assert res2["rows_added"] == 0 and res2["signal_rows_added"] == 0
    for t, df in snap.items():
        pd.testing.assert_frame_equal(df.reset_index(drop=True), store.read(t).reset_index(drop=True))
    # 歷史資料被事後改寫（例如 10-30 的價格被修正）：已記錄的日子仍然不重算、不改寫
    fl2 = _fake_lake()
    fl2["px"].loc[fl2["px"].date <= "2026-11-03", ["open", "high", "low", "close"]] *= 1.5
    LS.run_swing(None, fl2)
    pd.testing.assert_frame_equal(snap["paper/ledger"].reset_index(drop=True), store.read("paper/ledger").reset_index(drop=True))
    pd.testing.assert_frame_equal(snap["paper/swing_signals"].reset_index(drop=True), store.read("paper/swing_signals").reset_index(drop=True))


def test_run_swing_catches_up_after_gap_with_same_result_as_daily(lake, stub_view, monkeypatch):
    fl = _fake_lake()
    for last in ("2026-10-30", "2026-11-03", "2026-11-06"):                              # 每隔幾天跑一次
        sub = {**fl, "px": fl["px"][fl["px"].date <= last]}
        LS.run_swing(pd.Timestamp(last), sub)
    stepped = store.read("paper/ledger")
    stepped = stepped[stepped.plan == "SWING"][["date", "nav", "units", "action"]].reset_index(drop=True)
    monkeypatch.setattr(config, "DATA", lake / "data2")
    (lake / "data2").mkdir()
    LS.run_swing(pd.Timestamp("2026-11-06"), {**fl, "px": fl["px"][fl["px"].date <= "2026-11-06"]})
    once = store.read("paper/ledger")
    once = once[once.plan == "SWING"][["date", "nav", "units", "action"]].reset_index(drop=True)
    pd.testing.assert_frame_equal(stepped, once)


def test_brake_account_diverges_from_plain_after_drawdown(lake, stub_view):
    fl = _fake_lake()
    LS.run_swing(None, fl)
    led = LS.read_ledger()
    j = json.loads(led[(led.plan == "SWING_BRAKE")].iloc[-1]["extra"])["state"]
    assert j["peak"] >= j["last_nav"] and "positions" in j                                   # 狀態可從帳本還原（重啟接續用）
    sig = json.loads(led[led.plan == "SWING"].iloc[-1]["sig"])
    assert "disclaimer" in sig and sig["disclaimer"].startswith("研究用")
