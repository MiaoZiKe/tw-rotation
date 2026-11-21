"""大盤三張圖 1H／4H：指數分 K 入湖、時段切 K、增量去重、夜盤歸屬（2026-09-25）。全部用假資料，不打真 API。"""
from __future__ import annotations

import pandas as pd
import pytest

from pipeline import config
from pipeline.compute import intraday_bars as ib
from pipeline.util import store


def _w(s: str) -> int:
    """'2026-09-24 09:15' 台北時間 → 牆鐘秒數。"""
    return int((pd.Timestamp(s) - pd.Timestamp("1970-01-01")).total_seconds())


def _bars(times, interval="15m", symbol="TSE", base=100.0):
    rows = []
    for i, t in enumerate(times):
        ts = pd.Timestamp(t).tz_localize("Asia/Taipei").isoformat()
        p = base + i
        rows.append({"ts": ts, "symbol": symbol, "interval": interval,
                     "open": p, "high": p + 0.5, "low": p - 0.5, "close": p + 0.2, "volume": 10.0})
    return pd.DataFrame(rows)


# ------------------------------------------------------------ 時段切 K
def test_day_session_h1_keys():
    assert ib.session_key(_w("2026-09-24 08:45"), "H1") == _w("2026-09-24 09:00")  # 期貨早開併進 09
    assert ib.session_key(_w("2026-09-24 10:45"), "H1") == _w("2026-09-24 10:00")
    assert ib.session_key(_w("2026-09-24 13:15"), "H1") == _w("2026-09-24 13:00")
    assert ib.session_key(_w("2026-09-24 13:30"), "H1") == _w("2026-09-24 13:00")  # 13:30 併到 13:00
    assert ib.session_key(_w("2026-09-24 13:45"), "H4") == _w("2026-09-24 09:00")


def test_night_session_belongs_to_open_day():
    # 凌晨 02:00 屬於前一天 15:00 開的那一盤
    assert ib.session_key(_w("2026-09-25 02:00"), "H4") == _w("2026-09-24 15:00")
    assert ib.session_key(_w("2026-09-24 23:30"), "H4") == _w("2026-09-24 15:00")
    assert ib.session_key(_w("2026-09-25 05:00"), "H4") == _w("2026-09-24 15:00")
    assert ib.session_key(_w("2026-09-25 00:15"), "H1") == _w("2026-09-25 00:00")


def test_build_synth_one_day_15m():
    times = pd.date_range("2026-09-24 09:00", "2026-09-24 13:15", freq="15min")  # 18 根
    out = ib.build(_bars(times))
    h1, h4 = out["TSE"]["H1"], out["TSE"]["H4"]
    assert [b[0] for b in h1] == [_w(f"2026-09-24 {h:02d}:00") for h in (9, 10, 11, 12, 13)]
    assert len(h4) == 1 and h4[0][0] == _w("2026-09-24 09:00")
    assert h4[0][1] == 100.0 and h4[0][4] == pytest.approx(117.2)   # 開＝第一根開、收＝最後一根收
    assert h4[0][5] == pytest.approx(180.0)
    assert h1[-1][5] == pytest.approx(20.0)                         # 13:00、13:15 兩根


def test_build_prefers_15m_same_day_and_60m_elsewhere():
    old = _bars(["2026-09-01 09:00", "2026-09-01 10:00"], interval="60m", base=50)
    dup60 = _bars(["2026-09-24 09:00"], interval="60m", base=999)
    new = _bars(["2026-09-24 09:00", "2026-09-24 09:15"], interval="15m")
    out = ib.build(pd.concat([old, dup60, new]))
    h1 = out["TSE"]["H1"]
    assert len(h1) == 3
    assert h1[-1][1] == 100.0                  # 同一盤用 15 分，不被 60 分的 999 蓋掉
    assert out["TSE"]["src"]["days"] == 2
    # 原始 15 分 K 也吐出來：只有 15m 那兩根（60 分那幾根不算），時間是牆鐘秒數
    assert [b[0] for b in out["TSE"]["M15"]] == [_w("2026-09-24 09:00"), _w("2026-09-24 09:15")]


# ------------------------------------------------------------ 期貨逐筆 → 60 分（跨日夜盤）
def test_ticks_to_60m_day_night_and_near_month():
    ticks = pd.DataFrame([
        {"date": "2026-09-24 08:46:00", "contract_date": "202610", "price": 100, "volume": 5},
        {"date": "2026-09-24 09:30:00", "contract_date": "202610", "price": 105, "volume": 5},
        {"date": "2026-09-24 09:31:00", "contract_date": "202611", "price": 900, "volume": 1},   # 遠月丟
        {"date": "2026-09-24 09:32:00", "contract_date": "202610/202611", "price": 3, "volume": 99},  # 價差丟
        {"date": "2026-09-24 15:10:00", "contract_date": "202610", "price": 110, "volume": 2},
        {"date": "2026-09-25 01:10:00", "contract_date": "202610", "price": 111, "volume": 2},
    ])
    out = ib.ticks_to_60m(ticks)
    day = out[out["symbol"] == "FUT"]
    night = out[out["symbol"] == "FUT_N"]
    assert len(day) == 1 and day.iloc[0]["high"] == 105 and day.iloc[0]["low"] == 100
    assert len(night) == 2
    assert set(night["interval"]) == {"60m"}
    # 夜盤兩根合成 4H 應只有一根，歸在 09-24 15:00
    h4 = ib.build(out)["FUT_N"]["H4"]
    assert len(h4) == 1 and h4[0][0] == _w("2026-09-24 15:00")


def test_ticks_empty_safe():
    assert ib.ticks_to_60m(pd.DataFrame()).empty


# ------------------------------------------------------------ 入湖增量去重
@pytest.fixture
def lake(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path)
    return tmp_path


def test_store_append_dedup(lake):
    a = _bars(["2026-09-24 09:00", "2026-09-24 09:15"])
    assert store.append("index_intraday", a) == 2
    b = _bars(["2026-09-24 09:15", "2026-09-24 09:30"])
    store.append("index_intraday", b)
    got = store.read("index_intraday")
    assert len(got) == 3
    # 同一時間不同 interval 不算重複
    store.append("index_intraday", _bars(["2026-09-24 09:00"], interval="60m"))
    assert len(store.read("index_intraday")) == 4


def test_yahoo_since_filters_old_rows(monkeypatch):
    from pipeline.sources import yahoo
    have = _bars(["2026-09-24 09:00", "2026-09-24 09:15"])
    fetched = _bars(["2026-09-24 09:00", "2026-09-24 09:15", "2026-09-24 09:30"])
    asked = {}

    def fake(interval, period, symbols=None):
        asked["p"] = period
        return fetched[fetched["interval"] == interval].reset_index(drop=True)

    monkeypatch.setattr(yahoo, "index_intraday", fake)
    out = yahoo.index_intraday_since(have, "15m")
    assert list(out["ts"]) == [fetched["ts"].iloc[2]]
    # 湖裡沒有 60m → 全量補滿保留上限
    yahoo.index_intraday_since(have, "60m")
    assert asked["p"] == "730d"


def test_yahoo_index_intraday_failure_returns_empty(monkeypatch):
    import sys, types
    from pipeline.sources import yahoo
    fake = types.SimpleNamespace(download=lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setitem(sys.modules, "yfinance", fake)
    assert yahoo.index_intraday("60m", "5d").empty


def test_futures_ticks_bad_columns(monkeypatch):
    from pipeline.sources import finmind
    from pipeline.util import http
    monkeypatch.setattr(http, "finmind_get", lambda *a, **k: [{"foo": 1}])
    assert finmind.futures_ticks("2026-09-24").empty
    monkeypatch.setattr(http, "finmind_get", lambda *a, **k: None)
    assert finmind.futures_ticks("2026-09-24").empty
