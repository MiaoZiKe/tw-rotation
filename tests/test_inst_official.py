"""官方三大法人（證交所／櫃買 openapi）寬鬆解析。用假回應，不打真 API。"""
from __future__ import annotations

import pandas as pd

from pipeline.sources import inst_official as io

_real_fetch_all = io.fetch_all      # conftest 會把 io.fetch_all 換成空替身，這裡留真的


def _twse_rows(n=400, date="1131020"):
    return [{"Date": date, "Code": f"{1101 + i}", "Name": "x",
             "外陸資買賣超股數(不含外資自營商)": "1,000", "外資自營商買賣超股數": "50",
             "投信買賣超股數": "-200", "自營商買賣超股數(自行買賣)": "30",
             "自營商買賣超股數(避險)": "20", "三大法人買賣超股數": "900"} for i in range(n)]


def test_classify_cn_en():
    assert io.classify("外陸資買賣超股數(不含外資自營商)") == "foreign"
    assert io.classify("外資自營商買賣超股數") == "foreign_dealer"
    assert io.classify("投信買賣超股數") == "trust"
    assert io.classify("自營商買賣超股數(自行買賣)") == "dealer_self"
    assert io.classify("自營商買賣超股數(避險)") == "dealer_hedge"
    assert io.classify("自營商買賣超股數") == "dealer"
    assert io.classify("三大法人買賣超股數") == "total"
    assert io.classify("外陸資買進股數") is None
    assert io.classify("Dealers(Proprietary)-Difference") == "dealer_self"
    assert io.classify("InvestmentTrust-Difference") == "trust"
    assert io.classify("ForeignInvestorsIncludeMainlandAreaInvestors-Difference") == "foreign"


def test_parse_and_merge_single_endpoint():
    df = io.merge_parts([io.parse_rows(_twse_rows())])
    assert len(df) == 400 and df["date"].iloc[0] == "2024-10-20"
    r = df.iloc[0]
    assert r["foreign"] == 1000 and r["foreign_dealer"] == 50 and r["foreign_total"] == 1050
    assert r["dealer"] == 50 and r["inst_total"] == 1050 - 200 + 50


def test_merge_three_endpoints():
    a = [{"Date": "1131020", "Code": f"{1101+i}", "外資買賣超股數": "10"} for i in range(5)]
    b = [{"Date": "1131020", "Code": f"{1101+i}", "投信買賣超股數": "5"} for i in range(5)]
    c = [{"Date": "1131020", "Code": f"{1101+i}", "自營商買賣超股數": "-3"} for i in range(5)]
    df = io.merge_parts([io.parse_rows(x) for x in (a, b, c)])
    assert len(df) == 5 and df["inst_total"].iloc[0] == 12


def test_missing_category_returns_empty():
    a = [{"Date": "1131020", "Code": "1101", "外資買賣超股數": "10"}]
    assert io.merge_parts([io.parse_rows(a)]).empty


def test_bad_shapes_return_empty():
    assert io.parse_rows([]).empty
    assert io.parse_rows({"x": 1}).empty
    assert io.parse_rows([{"foo": "bar"}]).empty
    nodate = [{"Code": "1101", "投信買賣超股數": "5"}]
    assert io.parse_rows(nodate).empty          # 沒有日期欄就不收


def test_fetch_all_with_fake_http(monkeypatch):
    io._cache.clear()
    calls = []

    def fake(url):
        calls.append(url)
        if url.endswith("/fund/T86"):
            return 200, _twse_rows(400)
        return 404, None

    monkeypatch.setattr(io, "_get", fake)
    df = _real_fetch_all(use_cache=False)
    assert len(df) == 400                      # 上櫃全 404 → 只剩上市
    assert not any(u.endswith("/fund/TWT38U") for u in calls)   # 湊齊就不再試其餘候選


def test_fetch_all_too_few_rows(monkeypatch):
    monkeypatch.setattr(io, "_get", lambda url: (200, _twse_rows(10)) if url.endswith("T86") else (404, None))
    assert _real_fetch_all(use_cache=False).empty
