"""迷你走勢圖（compute/sparks.py，v2，DECISIONS #290）的口徑釘子。

v2 要跟自選展開大圖（site/app.js trendSeries）逐點相同：分時＝最近 5 個交易日、每天開盤＋每根 60 分 K 收盤；
沒有分時＝最近 60 日收盤。基準＝昨收（日線倒數第二天），方向跟列上的漲跌幅同一件事。
每檔帶真實價位（最低／最高／基準／起／訖），前端才畫得出基準線、算得出漲跌幅。"""
import pandas as pd

from pipeline.compute import sparks


def _daily(code, closes, start="2026-06-01"):
    ds = pd.bdate_range(start, periods=len(closes)).strftime("%Y-%m-%d")
    return pd.DataFrame({"date": ds, "code": code, "close": closes})


def _m60(code, day, opens, closes):
    hrs = ["09:00", "10:00", "11:00", "12:00", "13:00"][: len(closes)]
    return pd.DataFrame({"ts": [f"{day}T{h}:00+08:00" for h in hrs], "code": code,
                         "open": opens, "high": closes, "low": closes, "close": closes, "volume": 1000.0})


def _md(d):
    return d[5:7] + "/" + d[8:10]


def _dec(entry, abc=sparks.ABC):
    """照前端的還原方式：64 階 → 價位（第一點、最後一點用真實值）。"""
    s, lo, hi = entry[0], entry[1], entry[2]
    v = [lo + abc.index(ch) / (len(abc) - 1) * (hi - lo) for ch in s[2:]]
    v[0], v[-1] = entry[4], entry[5]
    return v


def test_encode_levels():
    s = sparks.encode([10, 15, 20])
    assert s[0] == sparks.ABC[0] and s[-1] == sparks.ABC[-1] and len(s) == 3
    assert sparks.encode([5, 5, 5]) == sparks.ABC[32] * 3     # 平的放中間，不除以零


def test_intraday_five_days_thirty_points_with_real_prices_and_prev_close_base():
    d = _daily("2330", [100.0] * 29 + [106.5])                # 最新一天正式收盤 106.5（60 分 K 最後一根是 106）
    days = list(d["date"].iloc[-6:])                          # 6 天分 K：前 1 天當基準、後 5 天是窗口
    parts = [_m60("2330", days[0], [99] * 5, [99, 99, 99, 99, 98])]
    parts += [_m60("2330", dd, [100 + i] * 5, [100 + i, 101 + i, 100 + i, 101 + i, 102 + i]) for i, dd in enumerate(days[1:])]
    out = sparks.build(d, pd.concat(parts), days[-1], ["2330"])
    e = out["s"]["2330"]
    assert e[0][0] == "i" and len(e[0]) == 2 + 30            # 5 天 × (開盤 1 點＋5 根收盤)
    assert e[9] == "66666"
    assert e[3] == 100                                        # 基準＝昨收（日線倒數第二天），不是窗口前一天的 98
    assert e[4] == 100 and e[5] == 106.5                      # 起＝第一天開盤、訖＝最新一天正式收盤（不是 60 分 K 的 106）
    assert e[1] == 100 and e[2] == 106.5
    assert e[0][1] == "+"                                     # 106.5 > 昨收 100 → 漲（紅）
    assert e[6] == _md(days[1]) and e[7] == _md(days[-1]) and e[8] == _md(days[-2])
    want = [p for i in range(5) for p in [100 + i, 100 + i, 101 + i, 100 + i, 101 + i, 102 + i]]
    want[-1] = 106.5
    v = _dec(e)
    assert max(abs(a - b) for a, b in zip(v, want)) <= (106.5 - 100) / 63 / 2 + 1e-9   # 64 階還原誤差 < 半階
    assert out["stat"] == {"intraday": 1, "daily": 0, "none": 0}


def test_intraday_single_day_window_base_is_prev_close():
    d = _daily("2330", [100.0] * 25 + [99.0])
    latest = d["date"].iloc[-1]
    m = _m60("2330", latest, [101, 102, 103, 102, 103], [102, 103, 102, 103, 99])
    e = sparks.build(d, m, latest, ["2330"])["s"]["2330"]
    assert e[0][0] == "i" and len(e[0]) == 2 + 6 and e[3] == 100 and e[0][1] == "-"   # 99 < 昨收 100 → 跌
    assert e[8] == _md(d["date"].iloc[-2])


def test_stale_intraday_falls_back_to_60_daily_closes():
    closes = [float(x) for x in range(40, 105)]               # 65 天一路漲
    d = _daily("2454", closes)
    latest = d["date"].iloc[-1]
    stale = d["date"].iloc[-2]                                # 60 分 K 只到前一天 → 不能當最新的分時
    m = _m60("2454", stale, [1, 1, 1, 1, 1], [1, 2, 3, 4, 5])
    out = sparks.build(d, m, latest, ["2454"])
    e = out["s"]["2454"]
    assert e[0][0] == "d" and len(e[0]) == 2 + sparks.DAILY_N and e[0][1] == "+"
    assert e[0][2] == sparks.ABC[0] and e[0][-1] == sparks.ABC[-1]
    assert e[3] == closes[-2] and e[4] == closes[-sparks.DAILY_N] and e[5] == closes[-1]
    assert e[8] == _md(d["date"].iloc[-2]) and e[9] == ""


def test_short_daily_history():
    d = _daily("1101", [30.0, 31.0, 29.0])
    e = sparks.build(d, pd.DataFrame(), d["date"].iloc[-1], ["1101"])["s"]["1101"]
    assert e[0] == "d-" + sparks.encode([30, 31, 29]) and e[3] == 31 and e[8] == _md(d["date"].iloc[-2])


def test_missing_stock_counted_as_none():
    d = _daily("1101", [30.0])
    out = sparks.build(d, pd.DataFrame(), d["date"].iloc[-1], ["1101", "9999"])
    assert out["s"] == {} and out["stat"]["none"] == 2
