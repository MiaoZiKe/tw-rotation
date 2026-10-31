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
    assert nw.verdict(tr, te, 0.01)[0] == "pass"
    assert nw.verdict(tr, te, 0.2)[0] == "weak"                       # 沒過校正不能叫有效
    assert nw.verdict(tr, {**te, "net": -0.1}, 0.01)[0] != "pass"      # 扣成本後為負不能叫有效
    assert nw.verdict({"ic": -0.01}, te, 0.01)[0] != "pass"            # 訓練期方向不一致
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
