"""日線找訊號的測試：無未來資料、規則正確、隔日開盤進場、統計工具。"""
import numpy as np
import pandas as pd

from pipeline.compute import daily_signals as ds


def _idx(n):
    return [f"2024-01-{i + 1:02d}" for i in range(n)] if n <= 28 else [str(d.date()) for d in pd.bdate_range("2024-01-01", periods=n)]


def test_forward_excess_entry_next_open():
    """訊號日 t 的未來報酬從 t+1「開盤」算起：t+1 開→收、t+2…t+h 收盤報酬；不含 t 日自己的任何報酬。"""
    d = _idx(8)
    cc = pd.DataFrame({"a": [0.5, 0.0, 0.10, 0.10, 0.0, 0.0, 0.0, 0.0]}, index=d)   # t=0 當天大漲 50%：不該算進去
    oc = pd.DataFrame({"a": [0.0, 0.05, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}, index=d)   # t+1 開→收 +5%
    z = pd.Series(0.0, index=d)
    ex = ds.forward_excess(cc, oc, z, z, 3)
    # t=0：(1.05)×(1.10)(1.10)... h=3 → 第 2、3 日(索引2,3)的收盤報酬 → 1.05*1.1*1.1-1
    assert abs(ex["a"].iloc[0] - (1.05 * 1.1 * 1.1 - 1) * 100) < 1e-9
    # 最後 3 天還沒到期 → 缺值，不補 0
    assert ex["a"].iloc[-3:].isna().all()


def test_forward_excess_subtracts_market_and_missing_exit_is_nan():
    d = _idx(6)
    cc = pd.DataFrame({"a": [0, 0.01, 0.01, np.nan, 0, 0]}, index=d)
    oc = pd.DataFrame({"a": [0, 0.0, 0, 0, 0, 0]}, index=d)
    m = pd.Series(0.01, index=d)
    ex = ds.forward_excess(cc, oc, m, pd.Series(0.0, index=d), 2)
    # 出場日(t+2=3)收盤缺值 → t=1 缺值
    assert np.isnan(ex["a"].iloc[1])
    # t=0：標的 (1+0)*(1+0.01)-1=1%；大盤 (1+0)*(1.01)-1=1% → 超額 0
    assert abs(ex["a"].iloc[0]) < 1e-9


def _panel(n=60, seed=1, cols=("a", "b", "c")):
    rng = np.random.default_rng(seed)
    d = _idx(n)
    cc = pd.DataFrame(rng.normal(0, 0.01, (n, len(cols))), index=d, columns=list(cols))
    tv = pd.DataFrame(rng.uniform(1e8, 3e8, (n, len(cols))), index=d, columns=list(cols))
    net = pd.DataFrame(rng.normal(0, 1e6, (n, len(cols))), index=d, columns=list(cols))
    share = tv.div(tv.sum(axis=1), axis=0) * 100
    mk = pd.Series(rng.normal(0, 0.005, n), index=d)
    return cc, tv, net, share, mk


def test_no_lookahead_flags_same_after_truncating_future():
    """把最後 15 天砍掉，前面每一天的訊號必須一模一樣 —— 證明 t 日訊號沒偷看 t 以後。"""
    cc, tv, net, share, mk = _panel(80)
    full = ds.flags_basic(cc, tv, net, share, mk)
    k = 65
    part = ds.flags_basic(cc.iloc[:k], tv.iloc[:k], net.iloc[:k], share.iloc[:k], mk.iloc[:k])
    for key in ("1", "2", "3"):
        pd.testing.assert_frame_equal(full[key].iloc[:k], part[key], check_dtype=False)


def test_no_lookahead_quadrant_flags():
    rng = np.random.default_rng(3)
    d = _idx(120)
    g_share = pd.DataFrame(rng.uniform(0.5, 5, (120, 3)), index=d, columns=["g1", "g2", "g3"])
    g_cc = pd.DataFrame(rng.normal(0, 0.01, (120, 3)), index=d, columns=["g1", "g2", "g3"])
    mk = pd.Series(rng.normal(0, 0.005, 120), index=d)
    full = ds.flags_quadrant(g_share, g_cc, mk)
    k = 100
    part = ds.flags_quadrant(g_share.iloc[:k], g_cc.iloc[:k], mk.iloc[:k])
    for key in ("4", "5"):
        pd.testing.assert_frame_equal(full[key].iloc[:k], part[key], check_dtype=False)


def test_rule_s3_volume_up_price_flat():
    """量增價穩：5 日均/20 日均 > 1.5 且 5 日漲跌 ±3% 內。"""
    n = 40
    d = _idx(n)
    tv = pd.DataFrame({"flat": 1e8, "up": 1e8, "jump": 1e8}, index=d)
    tv.iloc[-5:, :] = 3e8                                   # 最近 5 日量放大 3 倍 → 比值約 1.67... 5 日 3e8、20 日均 (15*1e8+5*3e8)/20=1.5e8
    cc = pd.DataFrame(0.0, index=d, columns=["flat", "up", "jump"])
    cc.iloc[-1, 1] = 0.02                                    # 5 日 +2%：價穩
    cc.iloc[-1, 2] = 0.05                                    # 5 日 +5%：超過 3% → 不算
    f = ds.flags_basic(cc, tv, cc * np.nan, tv.div(tv.sum(axis=1), axis=0) * 100, pd.Series(0.0, index=d))
    last = f["3"].iloc[-1]
    assert last["flat"] and last["up"] and not last["jump"]
    assert not f["3"].iloc[-6].any()                          # 放量之前不觸發


def test_rule_s2_streak_and_not_breakout():
    n = 40
    d = _idx(n)
    net = pd.DataFrame({"ok": 1.0, "broken": 1.0, "breakout": 1.0}, index=d)
    net.iloc[-3, 1] = -1                                     # 中間斷一天 → 不算連買 5 日
    cc = pd.DataFrame(0.0, index=d, columns=net.columns)
    cc.iloc[-1, 2] = 0.08                                    # 今天創高 → 已突破，不算
    tv = pd.DataFrame(1e8, index=d, columns=net.columns)
    f = ds.flags_basic(cc, tv, net, tv * 0 + 1, pd.Series(0.0, index=d))["2"].iloc[-1]
    assert f["ok"] and not f["broken"] and not f["breakout"]


def test_rule_s1_share_rising_and_lagging_price():
    n = 30
    d = _idx(n)
    share = pd.DataFrame({"x": 1.0, "y": 1.0}, index=d)
    share.iloc[-4:, 0] = [1.0, 1.1, 1.2, 1.3]               # 連 3 日上升
    share.iloc[-4:, 1] = [1.0, 1.1, 1.2, 1.3]
    cc = pd.DataFrame(0.0, index=d, columns=["x", "y"])
    cc.iloc[-2, 1] = 0.05                                    # y 近 5 日大漲 → 價格已表態 → 不算
    mk = pd.Series(0.0, index=d)
    f = ds.flags_basic(cc, cc + 1e8, cc * np.nan, share, mk)["1"].iloc[-1]
    assert f["x"] and not f["y"]
    # 只升 2 日不算
    share2 = share.copy(); share2.iloc[-4, 0] = 1.2
    assert not ds.flags_basic(cc, cc + 1e8, cc * np.nan, share2, mk)["1"].iloc[-1]["x"]


def test_cooldown_dedup():
    d = _idx(40)
    f = pd.DataFrame(False, index=d, columns=["a"])
    f.iloc[[5, 7, 15, 17, 30], 0] = True
    ev = ds.cooldown_events(f, 10)["a"]
    assert list(np.flatnonzero(ev.to_numpy())) == [5, 17, 30]


def test_holm_monotone_and_bounded():
    adj = ds._holm([0.01, 0.04, 0.03, 0.5])
    assert adj[0] == 0.04 and adj[2] == 0.09 and adj[1] == 0.09 and adj[3] == 0.5
    assert all(a <= 1 for a in adj)


def test_evaluate_counts_and_purge():
    """訓練期事件在 split 前 h 天截止；樣本外只算 split 以後；缺值不算樣本。"""
    T = 60
    d = _idx(T)
    ev = pd.DataFrame(False, index=d, columns=["a"])
    ev.iloc[[10, 38, 45, 50], 0] = True
    ex = pd.DataFrame(1.0, index=d, columns=["a"])
    ex.iloc[50, 0] = np.nan
    res = ds.evaluate(ev, ex, ev | True, h=5, split_idx=40, rng=np.random.default_rng(0), with_rand=True)
    assert res["train"]["n"] == 1            # 10 在 [0,35)；38 因持有期跨進樣本外被排除
    assert res["test"]["n"] == 1             # 45；50 的未來報酬缺值
    assert res["test"]["mean"] == 1.0 and "p" in res["test"]


def test_compute_on_synthetic_panel_runs_and_schema():
    rng = np.random.default_rng(7)
    n, nc = 120, 8
    d = [str(x.date()) for x in pd.bdate_range("2023-11-01", periods=n)]
    codes = [str(1101 + i) for i in range(nc)]
    cc = pd.DataFrame(rng.normal(0, 0.012, (n, nc)), index=d, columns=codes)
    oc = pd.DataFrame(rng.normal(0, 0.006, (n, nc)), index=d, columns=codes)
    tv = pd.DataFrame(rng.uniform(2e8, 9e8, (n, nc)), index=d, columns=codes)
    net = pd.DataFrame(rng.normal(0, 1e6, (n, nc)), index=d, columns=codes)
    M = np.zeros((nc, 2)); M[:4, 0] = 1; M[4:, 1] = 1
    pairs = pd.DataFrame({"code": codes, "group_id": ["g1"] * 4 + ["g2"] * 4,
                          "group_name": ["甲"] * 4 + ["乙"] * 4, "chain": "x", "weight": 1.0})
    panel = {"dates": d, "codes": codes, "cc": cc, "oc": oc, "tv": tv, "net": net, "M": M,
             "groups": pairs.drop_duplicates("group_id").set_index("group_id")[["group_name", "chain"]], "pairs": pairs}
    out = ds.compute(panel, with_rand=False)
    assert {r["id"] for r in out["rules"]} == {r["id"] for r in ds.RULES}
    assert set(out) == {"meta", "rules", "recent", "latest"}
    # 最新一天的事件，之後報酬都該是 None（還沒到期）
    for r in out["recent"]:
        if r["date"] == d[-1]:
            assert all(v is None for v in r["fwd"].values())
