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
    assert r["retail_long"] == [122789.0] and r["retail_short"] == [51206.0]
    assert round(r["ratio_pct"][0], 2) == 51.17 and r["retail_net"] == [71583.0] and r["taiex"] == [20000.0]
    assert c.retail_ratio_json(pd.DataFrame(), oi)["dates"] == []
    # 三家不齊 → 該日不算
    fi2 = s.parse_fut_inst([_inst("TMF", "2026-10-19", "外資", 1, 1)], "TMF")
    assert c.retail_ratio_json(fi2, oi)["dates"] == []


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
                       "short_lots": [5.0, 6.0], "short_lots_prev": [5.0, 5.0], "margin_money": [1e6, 1e6]})   # 仟元 → 融資總餘額 10 億元
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
    # 市值 = 10000*1000*100 + 20000*1000*50 = 2e9 ；借款 = 1e6*1000 = 1e9 → 200%
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
