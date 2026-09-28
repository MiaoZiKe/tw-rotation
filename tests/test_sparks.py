"""搜尋下拉迷你走勢圖（compute/sparks.py）的口徑釘子。"""
import pandas as pd

from pipeline.compute import sparks


def _daily(code, closes, start="2026-09-01"):
    ds = pd.bdate_range(start, periods=len(closes)).strftime("%Y-%m-%d")
    return pd.DataFrame({"date": ds, "code": code, "close": closes})


def _m60(code, day, opens, closes):
    hrs = ["09:00", "10:00", "11:00", "12:00", "13:00"][: len(closes)]
    return pd.DataFrame({"ts": [f"{day}T{h}:00+08:00" for h in hrs], "code": code,
                         "open": opens, "high": closes, "low": closes, "close": closes, "volume": 1000.0})


def test_encode_levels():
    s = sparks.encode([10, 15, 20])
    assert s[0] == sparks.ABC[0] and s[-1] == sparks.ABC[-1] and len(s) == 3
    assert sparks.encode([5, 5, 5]) == sparks.ABC[32] * 3     # 平的放中間，不除以零


def test_intraday_uses_latest_day_open_plus_closes_and_prev_close_direction():
    d = _daily("2330", [100.0] * 24 + [104.0])                 # 最後一天 104、前一天 100
    latest = d["date"].iloc[-1]
    m = _m60("2330", latest, [101, 102, 103, 102, 103], [102, 103, 102, 103, 99])
    out = sparks.build(d, m, latest, ["2330"])
    s = out["s"]["2330"]
    assert s[0] == "i" and len(s) == 2 + 6                   # 開盤 1 點＋5 根收盤
    assert s[1] == "-"                                       # 最後一點 99 < 前一日收盤 100 → 跌（綠）
    assert out["stat"] == {"intraday": 1, "daily": 0, "none": 0}


def test_stale_intraday_falls_back_to_20_daily_closes():
    closes = [float(x) for x in range(80, 105)]              # 25 天一路漲
    d = _daily("2454", closes)
    latest = d["date"].iloc[-1]
    stale = d["date"].iloc[-2]                              # 60 分 K 只到前一天 → 不能當今天的分時
    m = _m60("2454", stale, [1, 1, 1, 1, 1], [1, 2, 3, 4, 5])
    out = sparks.build(d, m, latest, ["2454"])
    s = out["s"]["2454"]
    assert s[0] == "d" and len(s) == 2 + sparks.DAILY_N and s[1] == "+"
    assert s[2] == sparks.ABC[0] and s[-1] == sparks.ABC[-1]


def test_missing_stock_counted_as_none():
    d = _daily("1101", [30.0])
    out = sparks.build(d, pd.DataFrame(), d["date"].iloc[-1], ["1101", "9999"])
    assert out["s"] == {} and out["stat"]["none"] == 2
