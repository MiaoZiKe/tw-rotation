"""市場明細三張卡（融資餘額／外資台指期口數／小台散戶多空比）：解析、口徑、空值。"""
import pandas as pd

from pipeline.compute import mktfut as c
from pipeline.sources import mktfut as s


def test_parse_margin_total_wide():
    rows = []
    for d, mp, ml, sl in (("2026-10-16", 2.5e8, 8.0e6, 3e5), ("2026-10-19", 2.6e8, 8.1e6, 3.1e5)):
        rows += [{"date": d, "name": "MarginPurchase", "TodayBalance": ml, "YesBalance": ml - 1},
                 {"date": d, "name": "ShortSale", "TodayBalance": sl, "YesBalance": sl - 1},
                 {"date": d, "name": "MarginPurchaseMoney", "TodayBalance": mp, "YesBalance": mp - 5}]
    df = s.parse_margin_total(rows)
    assert list(df["date"]) == ["2026-10-16", "2026-10-19"]
    assert df.iloc[-1]["margin_money"] == 2.6e8 and df.iloc[-1]["margin_lots"] == 8.1e6


def test_parse_empty_and_unknown_columns():
    assert s.parse_margin_total(None).empty
    assert s.parse_margin_total([{"x": 1}]).empty
    assert s.parse_fut_inst([{"date": "2026-10-19"}], "TX").empty
    assert s.parse_fut_oi([{"a": 1}], "TMF").empty


def _inst(fid, d, who, lo, so):
    return {"date": d, "futures_id": fid, "institutional_investors": who,
            "long_open_interest_balance_volume": lo, "short_open_interest_balance_volume": so,
            "long_open_interest_balance_amount": 1, "short_open_interest_balance_amount": 1,
            "long_deal_volume": 1, "short_deal_volume": 1}


def test_parse_fut_inst_who():
    df = s.parse_fut_inst([_inst("TX", "2026-10-19", "外資", 30000, 50000), _inst("TX", "2026-10-19", "投信", 100, 200),
                           _inst("TX", "2026-10-19", "自營商", 5, 7), _inst("TX", "2026-10-19", "其他", 1, 1)], "TX")
    assert sorted(df["who"]) == ["dealer", "foreign", "trust"]


def test_parse_fut_oi_sums_months_and_drops_spreads():
    rows = [{"date": "2026-10-19", "contract_date": "202610", "open_interest": 100, "trading_session": "position"},
            {"date": "2026-10-19", "contract_date": "202611", "open_interest": 50, "trading_session": "position"},
            {"date": "2026-10-19", "contract_date": "202610/202611", "open_interest": 9, "trading_session": "position"},
            {"date": "2026-10-19", "contract_date": "202610", "open_interest": 7, "trading_session": "after_market"}]
    df = s.parse_fut_oi(rows, "TMF")
    assert df.iloc[0]["oi"] == 150


def test_retail_ratio_template_example():
    # Andy 範本 10/19：全市場 139,906；散戶多 122,789、空 51,206 → +51.17%
    fi = s.parse_fut_inst([_inst("TMF", "2026-10-19", "外資", 9000, 60000), _inst("TMF", "2026-10-19", "投信", 100, 200),
                           _inst("TMF", "2026-10-19", "自營商", 8017, 28500)], "TMF")
    oi = pd.DataFrame({"date": ["2026-10-19"], "futures_id": "TMF", "oi": [139906]})
    idx = pd.DataFrame({"date": ["2026-10-19"], "symbol": "TSE", "close": [20000.0]})
    r = c.retail_ratio_json(fi, oi, idx)
    assert r["asof"] == "2026-10-19" and r["order"] == "asc" and set(r["products"]) == {"TX", "MTX", "TMF"}
    t = r["products"]["TMF"]
    assert t["retail_long"] == [122789.0] and t["retail_short"] == [51206.0]
    assert round(t["ratio_pct"][0], 2) == 51.17 and t["retail_net"] == [71583.0] and t["taiex"] == [20000.0]
    assert r["products"]["TX"]["dates"] == [] and r["products"]["MTX"]["dates"] == []   # 沒資料的商品是空殼，不報錯
    assert c.retail_ratio_json(pd.DataFrame(), oi)["products"]["TMF"]["dates"] == []
    # 三家不齊 → 該日不算
    fi2 = s.parse_fut_inst([_inst("TMF", "2026-10-19", "外資", 1, 1)], "TMF")
    assert c.retail_ratio_json(fi2, oi)["products"]["TMF"]["dates"] == []


def test_retail_ratio_three_products(monkeypatch):
    """大台／小台／微台各自用自己的全市場未平倉與法人口數，互不串。"""
    rows, oirows = [], []
    for fid, tot, (fl, fs) in (("TX", 1000, (300, 500)), ("MTX", 2000, (100, 900)), ("TMF", 139906, (9000, 60000))):
        rows += [_inst(fid, "2026-10-19", "外資", fl, fs), _inst(fid, "2026-10-19", "投信", 0, 0), _inst(fid, "2026-10-19", "自營商", 0, 0)]
        oirows.append({"date": "2026-10-19", "contract_date": "202610", "open_interest": tot, "trading_session": "position"})
    fi = pd.concat([s.parse_fut_inst([x for x in rows if x["futures_id"] == f], f) for f in ("TX", "MTX", "TMF")])
    oi = pd.concat([s.parse_fut_oi([o], f) for o, f in zip(oirows, ("TX", "MTX", "TMF"))])
    r = c.retail_ratio_json(fi, oi)["products"]
    assert round(r["TX"]["ratio_pct"][0], 2) == round(((1000 - 300) - (1000 - 500)) / 1000 * 100, 2) == 20.0
    assert round(r["MTX"]["ratio_pct"][0], 2) == round((900 - 100) / 2000 * 100, 2)
    assert r["TMF"]["total_oi"] == [139906.0]


def test_collect_fetches_three_products(monkeypatch):
    calls = []
    monkeypatch.setattr(s.http, "finmind_get", lambda ds, **kw: calls.append((ds, kw.get("data_id"))) or [])
    s.collect("2026-10-01")
    assert ("TaiwanFuturesDaily", "TX") in calls and ("TaiwanFuturesDaily", "MTX") in calls and ("TaiwanFuturesDaily", "TMF") in calls
    assert all(("TaiwanFuturesInstitutionalInvestors", f) in calls for f in ("TX", "MTX", "TMF"))


def test_fut_oi_json_and_settle():
    rows = []
    for d, k in (("2026-10-16", 1), ("2026-10-19", 2)):
        rows += [_inst("TX", d, "外資", 30000 * k, 50000), _inst("TX", d, "投信", 100, 200), _inst("TX", d, "自營商", 5, 7)]
    fi = s.parse_fut_inst(rows, "TX")
    r = c.fut_oi_json(fi)
    assert r["dates"] == ["2026-10-16", "2026-10-19"] and r["foreign"]["net"] == [-20000.0, 10000.0] and r["order"] == "asc"
    assert c.fut_oi_json(pd.DataFrame())["dates"] == []
    # 結算日＝每月第三個星期三（2026-10-21）；沒開盤順延
    ds = ["2026-10-20", "2026-10-22", "2026-10-23"]
    assert c.settle_dates(ds) == ["2026-10-22"]
    assert c.settle_dates(["2026-10-21", "2026-10-22"]) == ["2026-10-21"]


def test_margin_maintenance_ratio_and_rank():
    mt = pd.DataFrame({"date": ["2026-10-16", "2026-10-19"], "margin_lots": [100.0, 110.0], "margin_lots_prev": [99.0, 100.0],
                       "short_lots": [5.0, 6.0], "short_lots_prev": [5.0, 5.0], "margin_money": [1e9, 1e9]})   # 單位元 → 融資總餘額 10 億元
    company = pd.DataFrame({"code": ["A", "B", "C"], "name": ["甲", "乙", "丙"], "market": ["TWSE", "TWSE", "TPEX"]})
    rows = []
    for d in mt["date"]:
        rows += [{"date": d, "code": "A", "margin_balance": 10000.0, "margin_change": 300.0},
                 {"date": d, "code": "B", "margin_balance": 20000.0, "margin_change": -500.0},
                 {"date": d, "code": "C", "margin_balance": 9e9, "margin_change": 9e9}]    # 上櫃不計
    md = pd.DataFrame(rows)
    px = pd.DataFrame({"date": list(mt["date"]) * 3, "code": ["A"] * 2 + ["B"] * 2 + ["C"] * 2, "close": [100.0] * 2 + [50.0] * 2 + [1.0] * 2})
    idx = pd.DataFrame({"date": mt["date"], "symbol": "TSE", "close": [20000.0, 20100.0]})
    mem = pd.DataFrame({"code": ["A"], "group_name": ["族群甲"]})
    r = c.margin_block(mt, md, company, px, idx, mem)
    # 市值 = 10000*1000*100 + 20000*1000*50 = 2e9 ；借款 = 1e9 元 → 200%
    assert round(r["rows"][-1]["ratio"], 6) == 200.0
    assert r["rows"][-1]["margin_chg"] == 10.0 and r["rows"][-1]["short_chg"] == 1.0 and r["rows"][-1]["taiex"] == 20100.0
    rr = {x["code"]: x for x in r["rank"]["rows"]}
    assert rr["A"]["chg"] == 300.0 and rr["B"]["chg"] == -500.0 and rr["A"]["g"] == ["族群甲"] and rr["B"]["g"] == [] and "C" not in rr
    assert c.margin_block(pd.DataFrame(), md, company, px)["rows"] == []
    assert c.margin_block(mt, pd.DataFrame(), company, px)["rows"][-1]["ratio"] is None      # 沒有個股資料 → 不亂給維持率


def test_margin_partial_day_dropped():
    mt = pd.DataFrame({"date": ["2026-10-16", "2026-10-19"], "margin_lots": [1.0, 1.0], "margin_lots_prev": [1.0, 1.0],
                       "short_lots": [1.0, 1.0], "short_lots_prev": [1.0, 1.0], "margin_money": [1e6, 1e6]})
    company = pd.DataFrame({"code": list("ABCDE"), "name": list("abcde"), "market": ["TWSE"] * 5})
    md = pd.DataFrame([{"date": "2026-10-16", "code": k, "margin_balance": 1.0, "margin_change": 0.0} for k in "ABCDE"]
                      + [{"date": "2026-10-19", "code": "A", "margin_balance": 1.0, "margin_change": 0.0}])
    px = pd.DataFrame([{"date": d, "code": k, "close": 10.0} for d in mt["date"] for k in "ABCDE"])
    r = c.margin_block(mt, md, company, px)
    assert r["rows"][0]["ratio"] is not None and r["rows"][1]["ratio"] is None


def _lake(t):
    import glob, os
    fs = glob.glob(f"data/{t}/**/*.parquet", recursive=True)
    return pd.concat(pd.read_parquet(f) for f in fs) if fs else pd.DataFrame()


def test_margin_block_units_synthetic():
    """margin_money 單位是元：6.4e11 元＝6,400 億；前日 6.5e11 → 較前日 -100 億；市值＝融資張×1000×收盤價。"""
    mt = pd.DataFrame({"date": ["2026-10-16", "2026-10-19"], "margin_lots": [100.0, 100.0], "margin_lots_prev": [99.0, 100.0],
                       "short_lots": [5.0, 4.0], "short_lots_prev": [5.0, 5.0],
                       "margin_money": [6.5e11, 6.4e11], "margin_money_prev": [6.5e11, 6.5e11]})
    codes = ["1101", "1102"]
    md = pd.DataFrame([{"date": d, "code": c, "margin_balance": 50.0, "margin_change": 0.0} for d in mt["date"] for c in codes])
    co = pd.DataFrame({"code": codes, "name": ["a", "b"], "market": ["TWSE", "TWSE"]})
    px = pd.DataFrame([{"date": d, "code": c, "close": 1.28e7} for d in mt["date"] for c in codes])
    b = c.margin_block(mt, md, co, px)
    last, prev = b["rows"][-1], b["rows"][-2]
    assert abs(last["margin_yi"] - 6400.0) < 1e-6 and abs(last["margin_yi"] - prev["margin_yi"] + 100.0) < 1e-6
    # 市值 100張×1000×1.28e7＝1.28e12；÷6.4e11＝200%
    assert abs(last["ratio"] - 200.0) < 1e-6


def test_margin_block_partial_day_carries_forward():
    """最新一天個股只到一半：缺的檔順延前日餘額，仍給維持率並標 partial；不到一半就留白。"""
    codes = [str(1000 + i) for i in range(10)]
    mt = pd.DataFrame({"date": ["d1", "d2", "d3"], "margin_lots": [10.0] * 3, "margin_lots_prev": [10.0] * 3,
                       "short_lots": [1.0] * 3, "short_lots_prev": [1.0] * 3,
                       "margin_money": [1e7] * 3, "margin_money_prev": [1e7] * 3})
    rows = [{"date": d, "code": k, "margin_balance": 1.0, "margin_change": 0.0} for d in ("d1", "d2") for k in codes]
    rows += [{"date": "d3", "code": k, "margin_balance": 1.0, "margin_change": 0.0} for k in codes[:6]]
    co = pd.DataFrame({"code": codes, "name": codes, "market": "TWSE"})
    px = pd.DataFrame([{"date": d, "code": k, "close": 1000.0} for d in ("d1", "d2", "d3") for k in codes])
    b = c.margin_block(mt, pd.DataFrame(rows), co, px)
    assert abs(b["rows"][-1]["ratio"] - 100.0) < 1e-6 and b["rows"][-1]["partial"] is True
    rows = rows[:-6] + [{"date": "d3", "code": codes[0], "margin_balance": 1.0, "margin_change": 0.0}]
    assert c.margin_block(mt, pd.DataFrame(rows), co, px)["rows"][-1]["ratio"] is None


def test_margin_block_20261019_lake_regression():
    """資料湖真實 10/19：融資 6,406.2 億、較前日 -49.8 億、維持率約 181%（Andy 參考站 181.31%，容許 ±3pp）。"""
    mt, md = _lake("margin_total"), _lake("margin_daily")
    if mt.empty or md.empty or "2026-10-19" not in set(mt["date"]):
        import pytest; pytest.skip("資料湖沒有 2026-10-19")
    b = c.margin_block(mt, md, _lake("company_info"), _lake("price_daily"))
    r = {x["d"]: x for x in b["rows"]}
    assert abs(r["2026-10-19"]["margin_yi"] - 6406.2) < 0.1
    assert abs(r["2026-10-19"]["margin_yi"] - r["2026-10-16"]["margin_yi"] + 49.8) < 0.1
    assert r["2026-10-19"]["short_lots"] == 201916 and r["2026-10-19"]["short_chg"] == -31686
    assert abs(r["2026-10-19"]["ratio"] - 181.31) < 3


def test_margin_ratio_date_alignment_1022():
    """2026-10-25 查證（社群貼文 10/22 維持率 176.99%、較前日 −5.85pp，被懷疑日期錯位）：
    維持率那一列的日期＝融資餘額日＝收盤價日（同一天 merge），沒有錯位。
    10/21 大盤 +1.28% → 維持率上升；10/22 大盤 −1.80% → 下降；−5.85pp 是對 10/21（182.84%），不是對 10/20。
    這裡用合成資料鎖住：某一天收盤價跳動，只有「那一天」的維持率跟著動。"""
    days = ["2026-10-20", "2026-10-21", "2026-10-22"]
    mt = pd.DataFrame({"date": days, "margin_lots": [1.0] * 3, "margin_lots_prev": [1.0] * 3,
                       "short_lots": [1.0] * 3, "short_lots_prev": [1.0] * 3,
                       "margin_money": [1e6] * 3, "margin_money_prev": [1e6] * 3})
    co = pd.DataFrame({"code": ["A"], "name": ["a"], "market": ["TWSE"]})
    md = pd.DataFrame([{"date": d, "code": "A", "margin_balance": 1.0, "margin_change": 0.0} for d in days])
    px = pd.DataFrame({"date": days, "code": "A", "close": [1000.0, 1100.0, 1000.0]})
    rows = {r["d"]: round(r["ratio"], 6) for r in c.margin_block(mt, md, co, px)["rows"]}
    assert rows == {"2026-10-20": 100.0, "2026-10-21": 110.0, "2026-10-22": 100.0}


def test_margin_block_20261022_lake_regression():
    """資料湖真實值：10/21 182.84%、10/22 176.99%（差 −5.85pp），兩天都不是 partial。湖裡沒有就跳過。"""
    import pytest
    mt, md, co, px = (_lake(t) for t in ("margin_total", "margin_daily", "company_info", "price_daily"))
    if mt.empty or md.empty or "2026-10-22" not in set(mt["date"].astype(str)):
        pytest.skip("資料湖沒有 10/22")
    rows = {r["d"]: r for r in c.margin_block(mt, md, co, px)["rows"]}
    a, b = rows["2026-10-21"], rows["2026-10-22"]
    assert abs(a["ratio"] - 182.84) < 0.05 and abs(b["ratio"] - 176.99) < 0.05
    assert abs((b["ratio"] - a["ratio"]) + 5.85) < 0.05 and not a["partial"] and not b["partial"]
