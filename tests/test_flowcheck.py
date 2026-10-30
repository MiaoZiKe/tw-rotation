"""流向驗證資料（pipeline/compute/flowcheck.py）：口徑、殘缺格剔除、訊號規則、無未來資料、邊界。"""
import math

import numpy as np
import pandas as pd
import pytest

from pipeline.compute import flowcheck as fc


# ------------------------------------------------------------------ 小工具
def test_wilson_and_window():
    assert fc.wilson(0, 0) == (None, None)
    lo, hi = fc.wilson(5, 10)
    assert lo < 50 < hi                      # 一半命中，CI 一定含 50%
    lo, hi = fc.wilson(10, 10)
    assert 0 <= lo <= hi <= 100              # 靠邊也不會跑出 0～100
    assert fc.sig_window("5m") == 6 and fc.sig_window("60m") == 1


def test_r_handles_nan_inf():
    assert fc._r(float("nan")) is None and fc._r(float("inf")) is None and fc._r(None) is None
    assert fc._r(1.23456, 3) == 1.235


# ------------------------------------------------------------------ 60 分 K 整理
def _bars(codes, hours=("09:00", "10:00", "11:00", "12:00", "13:00"), vol0=0.0):
    rows = []
    for c in codes:
        for i, h in enumerate(hours):
            rows.append({"ts": f"2026-10-13T{h}:00+08:00", "code": c, "open": 10 + i, "high": 11 + i,
                         "low": 9 + i, "close": 10.5 + i, "volume": vol0 if h == "09:00" else 1000.0})
    return pd.DataFrame(rows)


def test_frames_60m_times_gap_and_close_override():
    pc = pd.Series({"A": 10.0, "B": 10.0})
    fr = fc.frames_from_60m(_bars(["A", "B"], vol0=5000.0), pc, day_close=pd.Series({"A": 20.0, "B": 0.0}))
    assert list(fr["price"].index) == ["09:00", "10:00", "11:00", "12:00", "13:00", "13:30"]
    assert fr["gap_0900"] is True
    assert fr["price"].loc["09:00", "A"] == 10            # 第一格＝09:00 那根的開盤
    # 09:00 那根就算有量也整根視為缺 → 10:00 格累計值是 NaN，11:00 才有（10:00 那根 1000 股 × 11.5）
    assert np.isnan(fr["cum"].loc["10:00", "A"]) and np.isnan(fr["cum"].loc["09:00", "A"])
    assert fr["cum"].loc["11:00", "A"] == pytest.approx(1000 * 11.5)
    # 13:30 改用官方收盤；官方收盤 ≤ 0（缺）就保留 Yahoo 的
    assert fr["price"].loc["13:30", "A"] == 20.0
    assert fr["price"].loc["13:30", "B"] == 14.5
    assert fr["chg"].loc["13:30", "A"] == pytest.approx(100.0)


def test_frames_60m_rescales_adjusted_yahoo_prices():
    """Yahoo 歷史分 K 是還原權值價：用官方開盤 ÷ Yahoo 開盤把整天乘回原始價；比例離譜的那檔整天剔除。"""
    pc = pd.Series({"A": 20.0, "B": 10.0})
    bars = _bars(["A", "B"])                       # Yahoo 開盤 10（A 實際是 20：被還原縮了一半）
    fr = fc.frames_from_60m(bars, pc, day_close=pd.Series({"A": 29.0, "B": 14.5}),
                            day_open=pd.Series({"A": 20.0, "B": 50.0}))
    assert fr["price"].loc["09:00", "A"] == pytest.approx(20.0)
    assert fr["price"].loc["11:00", "A"] == pytest.approx(23.0)         # 11.5 × 2
    assert fr["cum"].loc["11:00", "A"] == pytest.approx(1000 * 23.0)
    assert fr["chg"].loc["09:00", "A"] == pytest.approx(0.0)
    assert fr["price"]["B"].isna().all()                                # 50 ÷ 10＝5 倍 → 對不上，剔除


def test_frames_empty():
    assert fc.frames_from_60m(pd.DataFrame(), pd.Series(dtype=float)) is None
    assert fc.frames_from_tape(pd.DataFrame()) is None


# ------------------------------------------------------------------ 盤中族群：加權口徑與殘缺格
def _fr(price, chg, cum):
    return {"gran": "5m", "price": price, "chg": chg, "cum": cum, "gap_0900": False}


def test_group_intraday_weighted_and_residual():
    times = ["09:15", "09:20", "09:25"]
    codes = ["A", "B", "C", "D"]
    price = pd.DataFrame(10.0, index=times, columns=codes)
    price.loc["09:20", ["B", "C", "D"]] = np.nan        # 這一格只剩 1/4 檔 → 殘缺格要整格剔除
    chg = pd.DataFrame({"A": [1.0, 1, 1], "B": [3.0, 3, 3], "C": [-1.0, -1, -1], "D": [0.0, 0, 0]}, index=times)
    cum = pd.DataFrame({"A": [100.0, 200, 300], "B": [100.0, 100, 100], "C": [50.0, 50, 50], "D": [50.0, 50, 50]},
                       index=times)
    w = pd.Series({"A": 3.0, "B": 1.0, "C": 0.0, "D": 4.0})  # 前一日成交值；C 權重 0 → 不進漲跌
    nmem = pd.Series({"A": 1, "B": 1, "C": 1, "D": 2})       # D 掛兩個族群 → 權重 ×1/2
    M = fc.group_intraday(_fr(price, chg, cum), {"g": ["A", "B", "C", "D"], "small": ["A", "B"]},
                          codes, w, nmem)
    assert M["times"] == ["09:15", "09:25"]
    g = M["G"]["g"]
    # 族群漲跌＝(1×3 + 3×1 + 0×2) ÷ (3+1+2) = 1.0；大盤＝(1×3+3×1+0×4)/(3+1+4)=0.75
    assert g["chg"][0] == pytest.approx(1.0)
    assert M["mkt"][0] == pytest.approx(0.75)
    assert g["rel"][0] == pytest.approx(0.25)
    assert g["share"][0] == pytest.approx(100.0)        # 全部成分股＝全部名單
    assert g["adv"][0] == 2 and g["dec"][0] == 1
    assert g["br"][0] == pytest.approx(50.0)
    assert "small" not in M["G"]                        # 少於 3 檔不算


def test_group_intraday_all_residual_empty():
    price = pd.DataFrame(np.nan, index=["09:15"], columns=["A"])
    M = fc.group_intraday(_fr(price, price, price), {"g": ["A"]}, ["A"], pd.Series({"A": 1.0}), pd.Series(dtype=float))
    assert M["G"] == {} and M["times"] == []


# ------------------------------------------------------------------ 訊號規則
def _M(rel, share, br, val, tot, gran="5m"):
    n = len(rel)
    return {"gran": gran, "times": [f"t{i:02d}" for i in range(n)], "tot": tot,
            "G": {"g": {"rel": rel, "share": share, "br": br, "val": val}}}


def test_flow_lead_triggers_first_time_only_after_window():
    n = 30
    tot = [1000.0 * (i + 1) for i in range(n)]
    val = [50.0 * (i + 1) + (1000.0 if i >= 25 else 0) for i in range(n)]   # 平均占比 5%，t=25 一次湧入
    share = [v / t * 100 for v, t in zip(val, tot)]
    s = fc.scan_signals(_M([-0.2] * n, share, [50.0] * n, val, tot))
    fl = [x for x in s if x["type"] == "flow_lead"]
    # t=25：最近 6 格新增占比 (2300−1000)/6000＝21.7%，累計 2300/26000＝8.8% → 2.46 倍 > 1.5；之後不再重記
    assert len(fl) == 1 and fl[0]["ti"] == 25
    assert fl[0]["num"]["x"] == pytest.approx(2.45, abs=0.02)
    assert fl[0]["rel_to_close"] == pytest.approx(0.0)


def test_flow_lead_blocked_when_price_already_up():
    n = 30
    tot = [1000.0 * (i + 1) for i in range(n)]
    val = [50.0 * (i + 1) + (1000.0 if i >= 25 else 0) for i in range(n)]
    share = [v / t * 100 for v, t in zip(val, tot)]
    s = fc.scan_signals(_M([0.5] * n, share, [50.0] * n, val, tot))
    assert not [x for x in s if x["type"] == "flow_lead"]   # 相對大盤 > 0 → 價格已經動了，不算資金先行


def test_breadth_and_open_low_recover():
    n = 9
    br = [30.0] * 6 + [55.0, 60.0, 60.0]                # t=6 時比 t=0 多 25pp
    rel = [-2.0, -1.8, -1.6, -1.5, -1.2, -1.1, -0.8, -0.5, 0.3]
    share = [3.0] * 6 + [3.1, 3.2, 3.3]
    tot = [100.0] * n
    s = fc.scan_signals(_M(rel, share, br, [3.0] * n, tot))
    ty = {x["type"]: x for x in s}
    assert ty["breadth"]["ti"] == 6
    # 開低回升：t=6 回升 (−0.8+2)/2=60% > 50%，占比 3.1 > 3.0
    assert ty["open_low_recover"]["ti"] == 6
    assert ty["open_low_recover"]["rel_to_close"] == pytest.approx(1.1)


def test_no_signal_before_window_and_fresh_not_scored():
    n = 7
    br = [0.0] * 6 + [90.0]
    s = fc.scan_signals(_M([0.0] * n, [1.0] * n, br, [1.0] * n, [100.0] * n))
    assert len(s) == 1 and s[0]["ti"] == 6 and s[0]["fresh"] and s[0]["rel_to_close"] is None
    s = fc.scan_signals(_M([0.0] * 5, [1.0] * 5, [0, 0, 0, 0, 90.0], [1.0] * 5, [100.0] * 5))
    assert s == []                                       # 不到 6 格不判斷


def test_signals_use_no_future_data():
    """把第 k 格之後的資料砍掉，k 之前觸發的訊號（時間點與數字）必須完全一樣。"""
    rng = np.random.default_rng(0)
    n = 40
    tot = np.cumsum(rng.uniform(50, 150, n)).tolist()
    val = np.cumsum(rng.uniform(0, 20, n)).tolist()
    share = [v / t * 100 for v, t in zip(val, tot)]
    rel = (np.cumsum(rng.normal(0, 0.3, n)) - 1.5).tolist()
    br = rng.uniform(0, 100, n).tolist()
    full = fc.scan_signals(_M(rel, share, br, val, tot))
    for k in (10, 20, 30):
        cut = fc.scan_signals(_M(rel[:k], share[:k], br[:k], val[:k], tot[:k]))
        a = {(x["type"], x["ti"], str(x["num"])) for x in full if x["ti"] < k - 1}
        b = {(x["type"], x["ti"], str(x["num"])) for x in cut if x["ti"] < k - 1}
        assert a == b


# ------------------------------------------------------------------ 日線：無未來資料、背離、樣本不足
def _synth(n_days=120, n_groups=6):
    rng = np.random.default_rng(1)
    dates = pd.bdate_range("2026-01-01", periods=n_days).strftime("%Y-%m-%d").tolist()
    gh, px = [], []
    for gi in range(n_groups):
        for d in dates:
            gh.append({"date": d, "group_id": f"g{gi}", "group_name": f"族群{gi}", "tier": "x", "chain": "c",
                       "turnover": rng.uniform(1e8, 1e9), "chg_pct": rng.normal(0, 1.5), "advancers": 1.0,
                       "decliners": 1.0, "constituents": 3.0, "foreign_net": np.nan, "trust_net": 1000.0,
                       "dealer_net": 0.0, "margin_change": np.nan})
    for c in ("1101", "1102", "2330"):
        close = 100.0
        for d in dates:
            ch = close * rng.normal(0, 0.01)
            close += ch
            px.append({"date": d, "code": c, "close": close, "change": ch, "turnover": rng.uniform(1e8, 1e9)})
    gh = pd.DataFrame(gh)
    gh["turnover_share"] = gh["turnover"] / gh.groupby("date")["turnover"].transform("sum") * 100
    return gh, pd.DataFrame(px), dates


def test_daily_table_no_future_data():
    gh, px, dates = _synth()
    full = fc.daily_table(gh, px, 200)
    cut_d = dates[90]
    cut = fc.daily_table(gh[gh["date"] <= cut_d], px[px["date"] <= cut_d], 200)
    cols = ["rel", "dshare", "rot", "rs_ratio", "rs_mom", "m_x", "m_y"]
    a = full[full["date"] == cut_d].set_index("group_id")[cols].sort_index()
    b = cut[cut["date"] == cut_d].set_index("group_id")[cols].sort_index()
    pd.testing.assert_frame_equal(a, b)
    assert a["m_x"].notna().all() and a["rs_ratio"].notna().all()


def test_daily_table_rel_and_dshare():
    gh, px, dates = _synth(30, 5)
    D = fc.daily_table(gh, px, 100)
    r = D[(D["date"] == dates[5]) & (D["group_id"] == "g0")].iloc[0]
    assert r["rel"] == pytest.approx(r["chg_pct"] - r["mkt_chg"])
    prev = gh[(gh["date"] == dates[4]) & (gh["group_id"] == "g0")]["turnover_share"].iloc[0]
    assert r["dshare"] == pytest.approx(r["turnover_share"] - prev)
    assert D[D["date"] == dates[0]]["dshare"].isna().all()   # 第一天沒有前一天 → null，不是 0


def test_divergence_and_agree_small_sample():
    day = pd.DataFrame({"group_id": ["a", "b", "c"], "dshare": [1.0, -1, 0.5], "rel": [-1.0, 1, 0.2]})
    assert fc.divergence(day, {"a", "b", "c"}) == {}
    assert fc.agree_stats(day, {"a", "b", "c"})["agree"] is None
    day = pd.DataFrame({"group_id": list("abcdefghij"), "dshare": np.arange(10.0) - 4.5,
                        "rel": [1, 1, 1, 1, 1, 1, 1, 1, -1, -1.0]})
    div = fc.divergence(day, set("abcdefghij"))
    assert div["i"] == "A" and div["j"] == "A"          # 資金前 30%、相對大盤 < −0.3
    assert div["a"] == "B"                              # 相對大盤 > +0.3、資金後 30%
    st = fc.agree_stats(day, set("abcdefghij"))
    assert st["n"] == 10 and st["agree"] == pytest.approx(30.0)


# ------------------------------------------------------------------ 新聞、回測、空資料
def test_day_news_matching_and_cap():
    news = pd.DataFrame([{"news_id": f"n{i}", "published_at": "Mon, 05 Oct 2026 10:0%d:00 +0800" % i,
                          "title": f"台積電 消息{i}", "url": "u", "source": "udn", "codes": ""} for i in range(10)]
                        + [{"news_id": "x", "published_at": "Mon, 05 Oct 2026 11:00:00 +0800",
                            "title": "無關新聞", "url": "", "source": "udn", "codes": "2330"}])
    out = fc.day_news(news, None, {"fd": ["2330"]}, {"2330": "台積電"}, {"fd": "晶圓代工"})
    assert len(out) == fc.NEWS_PER_GROUP
    assert all(o["gids"] == ["fd"] and o["codes"] == ["2330"] for o in out)
    assert fc.day_news(None, None, {"fd": ["2330"]}, {}, {}) == []


def test_backtest_splits_granularity():
    ev = [{"date": "2026-10-01", "gid": "g", "type": "breadth", "granularity": "60m", "t": "10:00",
           "rel_to_close": 0.5, "rel_next_day": -0.1},
          {"date": "2026-10-30", "gid": "g", "type": "breadth", "granularity": "5m", "t": "09:45",
           "rel_to_close": -0.5, "rel_next_day": None}]
    bt = fc.backtest(ev, "2026-10-30")
    rows = {(r["granularity"], r["type"]): r for r in bt["summary"]}
    assert rows[("60m", "breadth")]["hit_rate"] == 100.0 and rows[("5m", "breadth")]["hit_rate"] == 0.0
    assert rows[("5m", "breadth")]["n_next"] == 0 and rows[("5m", "breadth")]["avg_next"] is None
    assert all(r["low_n"] for r in bt["summary"]) and bt["passed_multiple_test"] is False
    assert rows[("60m", "breadth")]["avg_excess_net"] == pytest.approx(0.5 - fc.COST)
    assert fc.backtest([], None)["summary"] == []


def test_build_empty_and_write(tmp_path):
    res = fc.build(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(columns=["code", "group_id", "group_name"]),
                   None, None, None, {})
    assert res["day"] == {} and res["index"]["dates"] == []
    st = fc.write(res, tmp_path)
    assert (tmp_path / "index.json").exists() and st["files"] == 2


def test_build_end_to_end_small():
    gh, px, dates = _synth(80, 4)
    mem = pd.DataFrame([{"code": c, "group_id": "g0", "group_name": "族群0", "tier": "x", "chain": "c"}
                        for c in ("1101", "1102", "2330")])
    res = fc.build(gh, px, mem, None, None, None, {"2330": "台積電"}, days=5, series_days=30, backtest_days=10)
    assert res["index"]["dates"] == dates[-5:]
    d = res["day"][dates[-1]]
    assert d["granularity"] is None and d["m60"] is None          # 沒有盤中資料的日子
    assert set(d["members"]) == {"1101", "1102", "2330"}
    contrib = sum(m["contrib"]["g0"] for m in d["members"].values())
    # 成分股貢獻加總＝成分股前一日成交值加權漲跌（不是族群 chg_pct：合成資料的族群表是亂數）
    p = fc.tv_prev_table(px)
    p = p[p["date"] == dates[-1]]
    assert contrib == pytest.approx((p["chg"] * p["tv_prev"]).sum() / p["tv_prev"].sum(), abs=1e-2)
    assert len(res["series"]["g0"]["dates"]) == 30
    assert math.isclose(res["series"]["g0"]["idx"][0], 100 * (1 + gh[(gh.group_id == "g0") & (gh.date == dates[-30])]["chg_pct"].iloc[0] / 100), rel_tol=1e-3)


# ------------------------------------------------------------------ 2026-10-30：大盤改加權指數
def _tx_ohlc():
    return pd.DataFrame({"date": ["2026-10-22", "2026-10-27", "2026-10-28"], "open": [100.0, 100, 102],
                         "close": [100.0, 102.0, 104.04], "change": [-1.0, 2.0, 2.04]})


def test_taiex_daily_and_intraday_fallback():
    intra = pd.DataFrame({"ts": ["2026-10-29T09:00:00+08:00", "2026-10-29T13:30:00+08:00"], "interval": ["1m", "1m"],
                          "open": [104.0, 103.0], "close": [103.5, 101.9592]})
    tx = fc.taiex_daily(_tx_ohlc(), intra)
    assert tx.at["2026-10-28", "chg"] == pytest.approx(2.0)
    assert tx.at["2026-10-28", "src"] == "index_ohlc"
    assert tx.at["2026-10-29", "src"] == "intraday"                  # 官方日線還沒進湖 → 盤中最後一根暫定
    assert tx.at["2026-10-29", "chg"] == pytest.approx(-2.0)
    assert fc.taiex_daily(None).empty


def test_taiex_slots_uses_only_closed_bars():
    intra = pd.DataFrame({"ts": [f"2026-10-28T{h}:00+08:00" for h in ("09:00", "09:01", "09:14", "13:29")],
                          "interval": "1m", "open": [101.0, 101, 101, 101], "close": [101.5, 102.0, 103.0, 104.0]})
    s = fc.taiex_slots(["09:00", "09:01", "09:15", "13:00", "13:30"], intra, 100.0, 104.04)
    assert s["09:00"] == pytest.approx(1.0)        # 還沒有任何一根收盤 → 第一根開盤
    assert s["09:01"] == pytest.approx(1.5)        # 09:00 那根收在 09:01
    assert s["09:15"] == pytest.approx(3.0)        # 09:14 那根收在 09:15
    assert s["13:00"] == pytest.approx(3.0)        # 13:29 那根還沒收，不准偷看
    assert s["13:30"] == pytest.approx(4.04)       # 收盤用官方收盤
    assert fc.taiex_slots(["09:00"], intra, None, None).isna().all()   # 昨收缺 → 不給
    assert fc.taiex_slots(["09:00"], None, 100.0, None).isna().all()


def test_daily_table_rel_vs_taiex():
    gh, px, dates = _synth(40, 5)
    tx = pd.DataFrame({"date": dates, "open": 100.0, "close": 100.0, "change": 0.0})
    tx.loc[tx["date"] == dates[10], ["close", "change"]] = [102.0, 2.0]
    T = fc.taiex_daily(tx)
    D = fc.daily_table(gh, px, 100, taiex=T)
    r = D[(D["date"] == dates[10]) & (D["group_id"] == "g1")].iloc[0]
    assert r["mkt_chg"] == pytest.approx(2.0)
    assert r["rel"] == pytest.approx(r["chg_pct"] - 2.0)
    assert r["mkt_site"] != pytest.approx(2.0)              # 主站口徑另存，不混進 rel
    assert "rs_ratio_site" in D.columns


def test_calendar_gaps_split_closed_and_missing():
    T = fc.taiex_daily(pd.DataFrame({"date": ["2026-10-21", "2026-10-22", "2026-10-27"],
                                     "open": 1.0, "close": [100.0, 100, 100], "change": 0.0}))
    sd = ["2026-10-21", "2026-10-27"]
    g = fc.calendar_gaps(T, sd, ["2026-10-21", "2026-10-27"], {"2026-10-21": ["daily", "m60"], "2026-10-27": ["daily"]})
    assert g["closed_days"] == ["2026-10-23", "2026-10-26"]     # 加權指數沒開＝休市
    assert g["missing_days"] == ["2026-10-22"]                  # 加權有開、價量湖沒有＝缺資料
    assert g["missing_intraday"] == ["2026-10-27"]
    assert fc.calendar_gaps(pd.DataFrame(), sd, sd, {}) == {"closed_days": [], "missing_days": [], "missing_intraday": []}


def test_group_intraday_mkt_override():
    times = ["09:15", "09:20"]
    price = pd.DataFrame(10.0, index=times, columns=list("ABC"))
    chg = pd.DataFrame(1.0, index=times, columns=list("ABC"))
    M = fc.group_intraday(_fr(price, chg, price), {"g": list("ABC")}, list("ABC"), pd.Series(1.0, index=list("ABC")),
                          pd.Series(dtype=float), mkt_override=pd.Series({"09:15": 0.5, "09:20": float("nan")}))
    assert M["G"]["g"]["rel"][0] == pytest.approx(0.5)
    assert math.isnan(M["G"]["g"]["rel"][1])                   # 加權指數那格缺 → 相對大盤 null，不拿別的頂替
