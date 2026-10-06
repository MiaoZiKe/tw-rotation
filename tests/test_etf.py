"""ETF 專區計算（pipeline/compute/etf.py）：用手算得出的數字對答案。"""
import math

import pandas as pd
import pytest

from pipeline.compute import etf


def test_年化報酬_手算():
    # 兩年漲 21% → 年化 10%
    assert etf.annualize(1.21, 2.0) == pytest.approx(0.10)
    assert etf.annualize(0.81, 2.0) == pytest.approx(-0.10)
    assert etf.annualize(1.1, 0) is None, "年數 0 不准外插"
    assert etf.annualize(0, 2) is None


def test_含息總報酬指數_除息日再投入():
    # 10 元 → 除息 1 元、收 9 元（含息不賺不賠）→ 漲回 10 元（再投入後多賺 1/9）
    tr = etf.total_return_index([10, 9, 10], [0, 1, 0])
    assert tr == pytest.approx([1.0, 1.0, 10 / 9])


def test_分割還原_一拆四():
    # 0050 2025-06-18 一拆四：188.65 → 47.57（比值 0.252 → 認成 1/4）
    f = etf.split_factors(["d1", "d2", "d3"], [188.65, 47.57, 48.0])
    assert f == pytest.approx([0.25, 1.0, 1.0])
    # 正常漲跌（槓桿 2 倍跌 18%）不能被當成分割
    assert etf.split_factors(["a", "b"], [100, 82]) == [1.0, 1.0]


def test_期間指標_手算對答案():
    dates = ["2020-01-02", "2021-01-01", "2022-01-02"]
    px = [10.0, 11.0, 12.1]
    div = [0.0, 0.5, 0.5]
    tr = etf.total_return_index(px, div)
    s = etf.period_stats(dates, px, tr, div, "2020-01-01", history_complete=True, div_covered=True)
    y = 731 / 365.25
    assert s["ok"] and s["years"] == round(y, 2)
    assert s["price_ann"] == pytest.approx(1.21 ** (1 / y) - 1, abs=1e-5)
    tr_end = (11.5 / 10) * (12.6 / 11)
    assert s["tr_ann"] == pytest.approx(tr_end ** (1 / y) - 1, abs=1e-5)
    assert s["cum_div"] == pytest.approx(1.0)
    assert s["div_ann"] == pytest.approx(1.1 ** (1 / y) - 1, abs=1e-5)
    assert s["avg_yield"] == pytest.approx(1.0 / y / ((10 + 11 + 12.1) / 3), abs=1e-5)
    assert s["tr_ann"] > s["price_ann"], "含息一定不小於不含息（配息為正）"


def test_資料不足_不給數字只給理由():
    dates = ["2020-01-02", "2022-01-03"]
    s = etf.period_stats(dates, [10, 12], [1, 1.2], [0, 0], "2015-01-01",
                         history_complete=True, div_covered=True)
    assert s == {"ok": False, "why": "上市未滿 8 年（有 2.0 年）"}
    s2 = etf.period_stats(dates, [10, 12], [1, 1.2], [0, 0], "2015-01-01",
                          history_complete=False, div_covered=True)
    assert s2["why"] == "價量歷史尚未回補"
    s3 = etf.period_stats(dates, [10, 12], None, [0, 0], "2020-01-01",
                          history_complete=True, div_covered=False)
    assert s3["ok"] and s3["tr_ann"] is None and s3["why_div"] == "配息資料尚未取得"
    assert s3["price_ann"] is not None


@pytest.mark.parametrize("code,name,n,cat", [
    ("0050", "元大台灣50", 2, "市值型"),
    ("006208", "富邦台50", 2, "市值型"),
    ("0056", "元大高股息", 4, "配息型"),
    ("00878", "國泰永續高股息", 4, "配息型"),
    ("00631L", "元大台灣50正2", 0, "槓桿反向"),
    ("00632R", "元大台灣50反1", 0, "槓桿反向"),
    ("00679B", "元大美債20年", 4, "債券型"),
    ("00635U", "期元大S&P黃金", 0, "其他"),
    ("00981A", "主動統一台股增長", 0, "主動式"),
    ("00881", "國泰台灣科技龍頭", 2, "主題型"),
    ("00999", "某某科技", 12, "配息型"),          # 名稱沒寫息，但月配 → 配息型
    ("0061", "元大寶滬深", 0, "主題型"),           # 追蹤的是中國，不是台灣大盤
])
def test_分類規則(code, name, n, cat):
    assert etf.classify(code, name, n) == cat


def test_配息頻率():
    assert [etf.freq_label(n) for n in (12, 6, 4, 2, 1, 0)] == ["月配", "雙月配", "季配", "半年配", "年配", "不配息"]


def test_build_殖利率與行事曆():
    dates = pd.bdate_range("2025-01-01", "2026-10-02").strftime("%Y-%m-%d").tolist()
    rows = [{"date": d, "code": "0056", "close": 40.0, "turnover": 1e9} for d in dates]
    price = pd.DataFrame(rows)
    ev = pd.DataFrame([{"code": "0056", "kind": "cash", "amount": a, "ex_date": d, "payment_date": None}
                       for d, a in (("2025-10-23", 1.0), ("2026-01-22", 0.8), ("2026-04-23", 0.6),
                                    ("2026-07-21", 0.6))])
    out = etf.build(price, {"0056": "元大高股息"}, {"0056"}, ev, pd.DataFrame(), pd.DataFrame(), "2026-10-02")
    it = out["items"][0]
    assert it["cat"] == "配息型" and it["freq"] == "季配"
    assert it["yield_ttm"] == pytest.approx(3.0 / 40.0), "近 12 個月配息 3.0 ÷ 現價 40"
    assert len(out["calendar"]) == 4 and out["calendar"][0]["y"] == pytest.approx(1.0 / 40.0)
    # 無配息資料的 ETF：殖利率 None 而不是 0
    out2 = etf.build(price, {"0056": "元大高股息"}, {"0056"}, pd.DataFrame(), pd.DataFrame(),
                     pd.DataFrame(), "2026-10-02")
    assert out2["items"][0]["yield_ttm"] is None
    assert math.isclose(out2["items"][0]["stats"]["Y2025"]["price_ann"], 0.0, abs_tol=1e-9)
    # 2026-10-06：「確定不配息」要有證據 —— 沒問過（no_data 鍵不存在）的 div_none 是 False（不知道≠0）
    assert out2["items"][0]["div_none"] is False
    out3 = etf.build(price, {"0056": "元大高股息"}, {"0056"}, pd.DataFrame(), pd.DataFrame(),
                     pd.DataFrame(), "2026-10-02", nodata_keys={"etfdiv@etfx2009:0056"})
    assert out3["items"][0]["div_none"] is True, "上游明確回空、湖裡 0 列 → 確定不配息"
    # 湖裡有配息列時，就算進度檔寫 no_data（舊鍵）也不算不配息
    out4 = etf.build(price, {"0056": "元大高股息"}, {"0056"}, ev, pd.DataFrame(), pd.DataFrame(),
                     "2026-10-02", nodata_keys={"etfdiv@etfx2009:0056"})
    assert out4["items"][0]["div_none"] is False


def test_填息天數_手算():
    # 除息前一日收盤 10.0（索引 1），除息日（索引 2）收 9.5，之後 9.8 → 10.0：第 3 個交易日收回 → 3 天
    close = [9.9, 10.0, 9.5, 9.8, 10.0, 10.2]
    assert etf.fill_info(close, 2) == (3, None)
    # 除息當天就收回 ≥ 前一日收盤 → 1 天（與個股除權息分頁同一口徑：除息日算第 1 天）
    assert etf.fill_info([10.0, 10.0, 10.1], 1) == (1, None)
    # 到最後一天都沒填：回「已經過 N 個交易日」（含除息日）＝ 6 − 2 ＝ 4
    assert etf.fill_info([9.9, 10.0, 9.5, 9.6, 9.7, 9.9], 2) == (None, 4)
    # 除息日是第一根（沒有前一日收盤）或不在行情裡 → 資料不足
    assert etf.fill_info([10.0, 9.5], 0) == (None, None)
    assert etf.fill_info([10.0, 9.5], 5) == (None, None)


def test_build_填息與自選走勢():
    dates = pd.bdate_range("2026-01-01", "2026-03-31").strftime("%Y-%m-%d").tolist()
    # 0056：每天 40 元；1/15 除息那天跌到 39，1/16 也 39，1/19（第 3 個交易日）回到 40 → 填息 3 天
    #       3/20 除息後一路 39 到最後 → 尚未填息，已 8 個交易日（3/20～3/31）
    px = {d: 40.0 for d in dates}
    for d in ("2026-01-15", "2026-01-16"):
        px[d] = 39.0
    for d in dates:
        if d >= "2026-03-20":
            px[d] = 39.0
    price = pd.DataFrame([{"date": d, "code": "0056", "close": px[d], "turnover": 1e9} for d in dates])
    ev = pd.DataFrame([{"code": "0056", "kind": "cash", "amount": 1.0, "ex_date": d, "payment_date": None}
                       for d in ("2026-01-15", "2026-03-20")])
    out = etf.build(price, {"0056": "元大高股息"}, {"0056"}, ev, pd.DataFrame(), pd.DataFrame(), "2026-03-31")
    cal = {c["ex"]: c for c in out["calendar"]}
    assert (cal["2026-01-15"]["fill"], cal["2026-01-15"]["fill_wait"]) == (3, None)
    assert (cal["2026-03-20"]["fill"], cal["2026-03-20"]["fill_wait"]) == (None, 8)
    it = out["items"][0]
    assert it["fill_avg"] == 3.0 and it["fill_n"] == 2 and it["fill_open"] == 1, "平均只算已填息的那一次"
    assert it["fill_last"] == [None, 8]
    # 自選比較的走勢：共用週取樣日期軸，最後一天一定在軸上，數值是分割還原後收盤
    sa = out["series_all"]
    assert sa["D"][-1] == "2026-03-31" and sa["s"]["0056"]["i"] == 0
    assert len(sa["s"]["0056"]["p"]) == len(sa["D"]) and sa["s"]["0056"]["p"][-1] == 39.0


def test_個股除權息_尚未填息寫出已經過天數():
    from pipeline.compute import stockpage
    dates = pd.bdate_range("2026-09-01", "2026-09-30").strftime("%Y-%m-%d").tolist()
    price = pd.DataFrame([{"date": d, "code": "9999", "close": (100.0 if d < "2026-09-10" else 97.0)}
                          for d in dates])
    res = pd.DataFrame([{"code": "9999", "date": "2026-09-10", "before_price": 100.0, "reference_price": 97.0,
                         "dividend": 3.0, "kind": "息"}])
    out = stockpage.dividends(pd.DataFrame(), res, price, "9999", 97.0, asof="2026-09-30")
    r = out["results"][0]
    # 9/10～9/30 共 15 個交易日都 97 < 100 → 尚未填息、已 15 天；不到 250 天所以不是 -1
    assert r["fill_days"] is None and r["fill_wait"] == 15
