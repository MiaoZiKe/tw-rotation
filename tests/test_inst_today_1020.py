"""當日三大法人彙總（compute/inst_today.py）。"""
import pandas as pd

from pipeline.compute import inst_today


def _inst(date, rows):
    return pd.DataFrame([{"date": date, "code": c, "foreign_total": f, "trust": t, "dealer": d,
                          "inst_total": f + t + d} for c, f, t, d in rows])


def test_日期取涵蓋夠的最新一天_不用只有幾檔的最新日():
    full = pd.concat([_inst("2026-10-16", [(str(1000 + i), 1000, 0, 0) for i in range(10)]),
                      _inst("2026-10-19", [("1000", 1000, 0, 0)])])
    assert inst_today.pick_date(full)[0] == "2026-10-16"


def test_金額與排行():
    inst = _inst("2026-10-16", [("2330", 2_000_000, 0, -1_000_000), ("2317", -3_000_000, 1_000_000, 0),
                                ("9999", 5000, 0, 0)])
    price = pd.DataFrame({"date": "2026-10-16", "code": ["2330", "2317"], "close": [1000.0, 100.0]})
    p = inst_today.payload(inst, price, {"2330": "台積電", "2317": "鴻海"})
    assert p["date"] == "2026-10-16"
    # 外資：2330 +2000張×1000=+20億、2317 -3000張×100=-3億；9999 沒收盤價不計金額但張數計入
    assert p["who"]["foreign"]["net_amt"] == 2_000_000_000 - 300_000_000
    assert p["who"]["foreign"]["net_lots"] == 2000 - 3000 + 5
    assert p["top"]["foreign"]["buy"][0]["code"] == "2330"
    assert p["top"]["foreign"]["sell"][0]["name"] == "鴻海"
    assert all(r["code"] != "9999" for r in p["top"]["foreign"]["buy"])
    # 合計 = 外資 + 投信 + 自營
    w = p["who"]
    assert w["total"]["net_amt"] == w["foreign"]["net_amt"] + w["trust"]["net_amt"] + w["dealer"]["net_amt"]


def test_空資料不炸():
    assert inst_today.payload(pd.DataFrame(), pd.DataFrame(), {})["date"] is None


# ------------------------------------------------------------ 全市場官方金額（日報）
from pipeline.compute import inst_market
from pipeline.sources import finmind


def _fm(date, vals):
    names = ["Foreign_Investor", "Foreign_Dealer_Self", "Investment_Trust", "Dealer_self", "Dealer_Hedging"]
    return [{"date": date, "name": n, "buy": b, "sell": s} for n, (b, s) in zip(names, vals)]


def test_finmind長格式轉寬格式_外資含外資自營_自營含避險():
    data = _fm("2026-10-19", [(100e8, 300e8), (5e8, 10e8), (40e8, 20e8), (30e8, 25e8), (10e8, 15e8)])
    df = finmind.parse_market_institutional(data)
    r = df.iloc[0]
    assert r["foreign_buy"] == 105e8 and r["foreign_sell"] == 310e8
    assert r["dealer_buy"] == 40e8 and r["dealer_sell"] == 40e8
    assert r["total_buy"] - r["total_sell"] == (105 + 40 + 40 - 310 - 20 - 40) * 1e8


def test_缺一種法人的日子不寫():
    assert finmind.parse_market_institutional(_fm("2026-10-19", [(1, 1)] * 3)[:3]).empty


def test_日報序列_官方優先_缺的日子用上市估算補且標est():
    mkt = finmind.parse_market_institutional(_fm("2026-10-16", [(0, 200e8), (0, 0), (50e8, 0), (0, 0), (0, 0)]))
    ohlc = pd.DataFrame({"symbol": "TSE", "date": ["2026-10-16", "2026-10-19"], "close": [20000.0, 20100.0]})
    inst = pd.DataFrame([{"date": d, "code": c, "foreign_total": 1_000_000, "trust": 0, "dealer": 0, "inst_total": 1_000_000}
                         for d in ("2026-10-16", "2026-10-19") for c in ("2330", "6488")])
    price = pd.DataFrame([{"date": d, "code": c, "close": 100.0, "market": m}
                          for d in ("2026-10-16", "2026-10-19") for c, m in (("2330", "TWSE"), ("6488", "TPEX"))])
    s = inst_market.series(mkt, inst, price, ohlc)
    a, b = s["rows"]
    assert a["est"] is False and a["f"] == -200.0 and a["t"] == 50.0 and a["tot"] == -150.0 and a["tw"] == 20000.0
    # 10/19 估算：只算上市 2330：100 萬股 ×100 元 = 1 億（上櫃 6488 不算）
    assert b["est"] is True and b["f"] == 1.0 and s["official_from"] == "2026-10-16" and s["n_est"] == 1


def test_期間累計與逐檔身分_供個股元件用():
    """2026-10-20：個股元件要能切身分、切期間。all_by 是當日逐檔；win 是近 N 日「股數×當日收盤」逐日加總。"""
    inst = pd.concat([_inst("2026-10-15", [("2330", 1_000_000, 0, 0)]), _inst("2026-10-16", [("2330", 2_000_000, 0, 0)])])
    price = pd.DataFrame({"date": ["2026-10-15", "2026-10-16"], "code": ["2330", "2330"], "close": [100.0, 200.0]})
    p = inst_today.payload(inst, price, {"2330": "台積電"})
    assert p["all_by"]["foreign"] == [["2330", 2000, 4.0]]                    # 當日：2000 張 × 200 = 4 億
    assert p["win"]["5"]["foreign"] == [["2330", 3000, 5.0]]                  # 兩天：1 億（10/15）+ 4 億（10/16）
    assert p["win"]["5"]["total"][0][1] == 3000
