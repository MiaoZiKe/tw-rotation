"""index_lastday（總覽大盤三張圖開頁種子）：挑「點數足夠的最近一天」、昨收用那天的前一個交易日。"""
import pandas as pd

from pipeline.compute import lastday


def _day(day, n, start="09:00", sym="TSE", base=100.0):
    t0 = pd.Timestamp(f"{day} {start}")
    return [{"ts": (t0 + pd.Timedelta(minutes=i)).strftime("%Y-%m-%dT%H:%M:00+08:00"), "symbol": sym,
             "interval": "1m", "open": base, "high": base + 1, "low": base - 1, "close": base + i * 0.01,
             "volume": 1.0, "src": "x"} for i in range(n)]


OHLC = {"TSE": [["2026-09-30", 1, 1, 1, 90.0, 0], ["2026-10-01", 1, 1, 1, 95.0, 0], ["2026-10-02", 1, 1, 1, 99.0, 0]]}


def test_skips_incomplete_latest_day_and_uses_its_own_prev_close():
    lake = pd.DataFrame(_day("2026-10-01", 270) + _day("2026-10-02", 1))
    out = lastday.build(lake, OHLC)
    t = out["TSE"]
    assert t["date"] == "20261001"
    assert t["prev"] == 90.0 and t["prev_date"] == "2026-09-30"   # 不准配上 10-02 的昨收 95
    assert len(t["points"]) == 271                                  # 270 根 ＋ 13:30 收盤點
    assert t["points"][-1] == [810, 95.0]
    assert t["last"] == 95.0                                        # 收盤以當天日 K 為準
    assert t["chg"] == 5.0


def test_complete_latest_day_used():
    lake = pd.DataFrame(_day("2026-10-01", 270) + _day("2026-10-02", 270))
    t = lastday.build(lake, OHLC)["TSE"]
    assert t["date"] == "20261002" and t["prev"] == 95.0


def test_no_prev_close_gives_nothing():
    lake = pd.DataFrame(_day("2026-09-30", 270))
    assert "TSE" not in lastday.build(lake, OHLC)


def test_empty():
    assert lastday.build(pd.DataFrame(), {}) == {}
