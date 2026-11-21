"""練習室籌碼檔：2018 年以前資料湖的 foreign_total／dealer 欄位是空的，外資改用外陸資 foreign、自營商改用自買＋避險補上
（和淘汰賽報告同口徑）；2018 年起有 foreign_total 就用 foreign_total。單位：股 → 張。"""
import json

import pandas as pd

from pipeline.compute import lab


def _tables():
    inst = pd.DataFrame({
        "date": ["2016-01-04", "2016-01-05", "2018-06-01"],
        "code": ["1111"] * 3,
        "foreign": [10_000, 20_000, 1_000],
        "foreign_total": [None, None, 5_000],            # 2018 以前空、2018 起有（含外資自營商）
        "trust": [1_000, 2_000, 3_000],
        "dealer_self": [4_000, 5_000, 0],
        "dealer_hedge": [1_000, None, 0],
        "dealer": [None, None, 7_000],
    })
    empty = pd.DataFrame({"date": [], "code": []})
    rev = pd.DataFrame({"ym": [], "code": [], "revenue": []})
    return {"inst_daily": inst, "margin_daily": empty, "daytrade_daily": empty, "revenue_monthly": rev}


def test_早年外資自營商用備援欄位(tmp_path, monkeypatch):
    t = _tables()
    monkeypatch.setattr(lab.store, "read", lambda name, *a, **k: t[name])
    p = pd.DataFrame({"code": ["1111"] * 3, "date": ["2016-01-04", "2016-01-05", "2018-06-01"], "close": [10.0, 11.0, 12.0]})
    items = [{"c": "1111", "k": "stock"}]
    monkeypatch.setattr(lab, "DAILY_FROM", "2016-01-01")
    lab.export_chips(p, items, tmp_path, only=["1111"])
    j = json.loads((tmp_path / "c" / "1111.json").read_text(encoding="utf-8"))
    assert j["fn"] == [10, 20, 5]          # 前兩天 foreign_total 空 → 用 foreign（10,000 股＝10 張）；最後一天用 foreign_total（5,000 股＝5 張）
    assert j["dl"] == [5, 5, 7]            # 前兩天 dealer 空 → 自買＋避險（4,000＋1,000＝5 張；5,000＋空＝5 張）；最後一天用 dealer 7 張
    assert j["tr"] == [1, 2, 3]
