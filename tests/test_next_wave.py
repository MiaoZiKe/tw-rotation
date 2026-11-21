"""next_wave 的核心不變量：沒有偷看未來、月營收用法定公布日、統計工具正確。"""
import numpy as np
import pandas as pd

from pipeline.compute import next_wave as nw


def _dates(n=400):
    return [d.strftime("%Y-%m-%d") for d in pd.bdate_range("2023-01-02", periods=n)]


def _rev(codes=("1111", "2222")):
    rows = []
    for c, g in zip(codes, (1.0, 1.5)):
        for ym in pd.period_range("2022-01", "2024-06", freq="M"):
            k = (ym - pd.Period("2022-01", "M")).n
            rows.append({"ym": str(ym), "code": c, "revenue": 100 * (1 + 0.03 * k) * g,
                         "announce_date": ((ym + 1).to_timestamp() + pd.Timedelta(days=9)).strftime("%Y-%m-%d")})
    return pd.DataFrame(rows)


def test_revenue_not_visible_before_announce_date():
    dates = _dates()
    out = nw.revenue_factors(_rev(), dates, ["1111", "2222"])["yoy"]
    # 2023-05 營收法定公布日 2023-06-10（週六）→ 順延到 2023-06-12 才可用；之前看到的只能是 2023-04 的值
    d_before, d_ann = "2023-06-09", "2023-06-12"
    yoy_may = _rev().query("code=='1111'").set_index("ym")["revenue"]
    expect_may = yoy_may["2023-05"] / yoy_may["2022-05"] - 1
    expect_apr = yoy_may["2023-04"] / yoy_may["2022-04"] - 1
    assert abs(out.loc[d_before, "1111"] - expect_apr) < 1e-9
    assert abs(out.loc[d_ann, "1111"] - expect_may) < 1e-9


def test_revenue_factor_truncation_invariant():
    """砍掉後面的資料，前面日期的因子值不變（沒有用到未來）。"""
    dates = _dates()
    full = nw.revenue_factors(_rev(), dates, ["1111", "2222"])
    cut_rev = _rev()
    cut_rev = cut_rev[cut_rev["ym"] <= "2023-09"]
    part = nw.revenue_factors(cut_rev, dates[:250], ["1111", "2222"])
    for k in ("yoy", "acc"):
        a = full[k].loc[dates[:250]]
        b = part[k]
        # 部分資料只到 2023-09 營收（公布 2023-10-10），這之前兩者必須完全一致
        idx = [d for d in dates[:250] if d < "2023-10-10"]
        pd.testing.assert_frame_equal(a.loc[idx], b.loc[idx], check_freq=False)


def test_rank_z_and_cs_stats_perfect_signal():
    rng = np.random.default_rng(0)
    T, N = 80, 40
    F = pd.DataFrame(rng.normal(size=(T, N)))
    X = F * 2 + 0.01                      # 因子完全預測報酬
    elig = pd.DataFrame(True, index=F.index, columns=F.columns)
    st = nw.cs_stats(F, X, elig, np.arange(10, 70, 5), +1)
    assert np.allclose(st["ic"], 1.0)
    assert (st["top"] > st["uni"]).all()
    st2 = nw.cs_stats(F, X, elig, np.arange(10, 70, 5), -1)   # 方向反了 → IC＝-1
    assert np.allclose(st2["ic"], -1.0)
    z = nw.rank_z(F)
    assert abs(z.mean(axis=1)).max() < 1e-9


def test_nw_t_and_wilson():
    t, p = nw.nw_t(np.full(30, 0.5) + np.random.default_rng(1).normal(0, 0.1, 30), 3)
    assert t > 10 and p < 1e-6
    t0, p0 = nw.nw_t(np.random.default_rng(2).normal(0, 1, 200), 3)
    assert abs(t0) < 3.5
    lo, hi = nw.wilson(3, 3)           # 3 個樣本 100% 勝率，區間仍然很寬
    assert lo < 0.5 and hi == 1.0 or hi > 0.99


def test_holm_monotone_and_verdict_rules():
    adj = nw.holm([0.001, 0.02, 0.5])
    assert adj[0] == 0.003 and adj[1] <= adj[2]
    tr = {"ic": 0.02}
    te = {"n_dates": 100, "spread": 1.0, "net": 0.5, "ic": 0.05, "ic_p": 0.001}
    assert nw.verdict(tr, te, 0.01)[0] == "experimental"      # 第二版：不再輸出 pass
    assert nw.verdict(tr, te, 0.2)[0] == "weak"                       # 沒過校正不能叫有效
    assert nw.verdict(tr, {**te, "net": -0.1}, 0.01)[0] != "experimental"      # 扣成本後為負不能叫有效
    assert nw.verdict({"ic": -0.01}, te, 0.01)[0] != "experimental"            # 訓練期方向不一致
    assert nw.verdict(tr, {**te, "n_dates": 10}, 0.01)[0] == "unproven"
    assert nw.verdict(tr, te, 0.01, short_sample=True)[0] == "short"


def test_signs_preregistered():
    assert nw.sign_of("MOM20", "group") == 1 and nw.sign_of("MOM20", "stock") == -1
    assert nw.sign_of("MARGIN20", "group") == -1
    assert all(f["id"] for f in nw.FACTORS)


def test_customer_pairs_only_tw_supplies():
    sc = {"companies": [{"id": "a", "ticker": "1101"}, {"id": "b", "ticker": "2330"}, {"id": "c", "ticker": ""}],
          "edges": [{"from": "a", "to": "b", "rel": "supplies"}, {"from": "a", "to": "c", "rel": "supplies"},
                    {"from": "b", "to": "a", "rel": "outsources_to"}]}
    assert nw.customer_pairs(sc, ["1101", "2330"]) == [("1101", "2330")]


def test_verdict_never_returns_pass():
    for p in (0.0, 0.01, 0.5):
        for ic in (-0.1, 0.1):
            te = {"n_dates": 200, "spread": 2.0, "net": 1.0, "ic": ic, "ic_p": 0.0001}
            assert nw.verdict({"ic": 0.1}, te, p)[0] != "pass"


def _fq():
    rows = []
    for c in ("1111", "2222"):
        for y in range(2020, 2024):
            for q in (1, 2, 3, 4):
                rows.append({"year": y, "quarter": q, "code": c, "announce_date": "2000-01-01",   # 故意標得比法定早
                             "eps": 1.0 + 0.1 * ((y - 2020) * 4 + q) + (0.5 if (c == "2222" and y == 2023 and q == 2) else 0)})
    return pd.DataFrame(rows)


def test_sue_uses_legal_deadline_not_earlier_announce_date():
    """資料標的公告日比法定早 → 以法定公告日為準（Q2 → 8/14），寧晚勿早。"""
    dates = _dates(1000)
    out = nw.eps_factors(_fq(), dates, ["1111", "2222"])["sue"]
    ok = [d for d in dates if "2023-08-10" <= d <= "2023-08-18"]
    before = [d for d in ok if d < "2023-08-14"]
    after = [d for d in ok if d >= "2023-08-14"]
    assert out.loc[before, "2222"].isna().all() or out.loc[before, "2222"].iloc[-1] != out.loc[after, "2222"].iloc[0]
    # 2222 在 2023Q2 有正向驚喜：法定公告日之後 SUE 為正且高於 1111
    assert out.loc[after[0], "2222"] > out.loc[after[0], "1111"]


def test_sue_truncation_invariant():
    dates = _dates(1000)
    full = nw.eps_factors(_fq(), dates, ["1111", "2222"])["sue"]
    cut = _fq()
    cut = cut[(cut["year"] < 2023) | (cut["quarter"] <= 1)]            # 拿掉 2023Q2 之後
    part = nw.eps_factors(cut, dates, ["1111", "2222"])["sue"]
    idx = [d for d in dates if d < "2023-08-14"]
    pd.testing.assert_frame_equal(full.loc[idx], part.loc[idx], check_freq=False)


def test_revenue_sur_and_high_not_visible_before_announce_date():
    dates = _dates()
    full = nw.revenue_factors(_rev(), dates, ["1111", "2222"])
    assert set(full) == {"yoy", "acc", "sur", "high"}
    cut = _rev()
    cut = cut[cut["ym"] <= "2023-09"]
    part = nw.revenue_factors(cut, dates[:250], ["1111", "2222"])
    idx = [d for d in dates[:250] if d < "2023-10-10"]
    for k in ("sur", "high"):
        pd.testing.assert_frame_equal(full[k].loc[idx], part[k].loc[idx], check_freq=False)


def test_group_agg_requires_min_members():
    z = pd.DataFrame([[1.0, 2.0, 3.0, np.nan], [1.0, np.nan, np.nan, 4.0]])
    B = np.array([[1, 0], [1, 0], [1, 0], [0, 1]], dtype=float)
    g = nw._group_agg(z, B, ["a", "b"])
    assert g.iloc[0, 0] == 2.0 and np.isnan(g.iloc[0, 1])            # b 只有 1 個成員 < 3 → 缺值
    assert np.isnan(g.iloc[1, 0])                                      # a 第二列只有 1 個有值 < 3


def test_seg_masks_do_not_cross_boundaries():
    dates = [d.strftime("%Y-%m-%d") for d in pd.bdate_range("2018-01-01", "2026-06-30")]
    rows = np.arange(nw.FIRST_ROW, len(dates))
    h = 20
    m = nw.seg_masks(dates, rows, h)
    i_train = int(np.searchsorted(np.array(dates), nw.TRAIN_START))
    i_test = int(np.searchsorted(np.array(dates), nw.TEST_START))
    assert rows[m["hold"]].max() < i_train - h + 0
    assert rows[m["train"]].max() < i_test - h and rows[m["train"]].min() >= i_train
    assert rows[m["test"]].min() >= i_test
    assert not (m["hold"] & m["train"]).any() and not (m["train"] & m["test"]).any()


def test_forward_status_collecting_and_retire_rule(monkeypatch):
    dates = _dates(400)
    gids = ["a", "b", "c", "d", "e"]
    rng = np.random.default_rng(3)
    g_cc = pd.DataFrame(rng.normal(0, 0.01, (400, 5)), index=dates, columns=gids)
    g_oc = pd.DataFrame(rng.normal(0, 0.01, (400, 5)), index=dates, columns=gids)
    mk = pd.Series(0.0, index=dates)
    es = {"g_cc": g_cc, "g_oc": g_oc, "mk_cc": mk, "mk_oc": mk}
    E = pd.DataFrame(True, index=dates, columns=gids)
    assert nw.forward_status(None, dates, es, E)["status"] == "collecting"
    log = pd.DataFrame([{"date": d, "method": nw.FWD_METHOD, "group_id": "a"} for d in dates[100:140]])
    st = nw.forward_status(log, dates, es, E)
    assert st["status"] == "collecting" and st["n_periods"] <= 8 and "已" in st["status_text"]
    # 期數滿了：讓 a 族群之後都輸（報酬 −1%）→ 已失效
    monkeypatch.setattr(nw, "FWD_LOG_MIN_PERIODS", 5)
    g_oc2 = g_oc.copy(); g_oc2["a"] = -0.01
    g_cc2 = g_cc.copy(); g_cc2["a"] = -0.01
    es2 = {"g_cc": g_cc2, "g_oc": g_oc2, "mk_cc": mk, "mk_oc": mk}
    st2 = nw.forward_status(log, dates, es2, E)
    assert st2["n_periods"] >= 5 and st2["status"] == "retired"


def test_forward_table_registered_with_key():
    from pipeline import config
    assert config.TABLES["next_wave_forward"] == ["date", "method", "group_id"]
