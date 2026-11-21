"""60 分 K 進資料湖：按月分割、增量去重。

為什麼有這一組（Andy 2026-09-18）：
分 K 以前**完全不存**，每次部署都從零重抓 400 檔，害部署 14 分鐘裡有 13 分 43 秒卡在那一步。
`pipeline/sources/yahoo.py` 的 docstring 當初還白紙黑字寫著「這層資料不進資料湖」。
通則寫在 DECISIONS #155，保留期限寫在 #156。

這裡守住三件會出事的事：
1. **按月分割**。`append()` 每次重寫整個分割檔，而 `data/` 每天 commit 進 repo；
   照年分割的話每天要重寫 26 MB，一年多好幾 GB 的 git 歷史。
2. **同一根 K 棒重寫不會變兩列**（key = ts + code）。盤中重跑、排程延遲重跑都是常態。
3. **時區**。ts 是台北時間；用 UTC 去分月，台北早上 09:00 的那根會被分到前一個月。
"""
from __future__ import annotations

import pandas as pd
import pytest

from pipeline import config
from pipeline.util import store


@pytest.fixture
def lake(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path)
    return tmp_path


def _bars(rows: list[tuple[str, str, float]]) -> pd.DataFrame:
    return pd.DataFrame([{"ts": ts, "code": c, "open": v, "high": v, "low": v,
                          "close": v, "volume": 1000} for ts, c, v in rows])


def test_按月分割而不是按年(lake):
    store.append("intraday_60m", _bars([
        ("2026-09-18T10:00:00+08:00", "2330", 1000.0),
        ("2026-08-18T10:00:00+08:00", "2330", 900.0),
    ]))
    parts = sorted(p.parent.name for p in lake.glob("intraday_60m/year=*/part.parquet"))
    assert parts == ["year=202608", "year=202609"], parts


def test_同一根K棒重寫不會變兩列(lake):
    store.append("intraday_60m", _bars([("2026-09-18T10:00:00+08:00", "2330", 1000.0)]))
    store.append("intraday_60m", _bars([("2026-09-18T10:00:00+08:00", "2330", 1010.0)]))
    got = store.read("intraday_60m")
    assert len(got) == 1, got
    assert got["close"].iloc[0] == 1010.0, "後到的應該覆蓋先到的（盤中重跑會修正收盤價）"


def test_增量只重寫當月那一個檔(lake):
    """這就是按月分割的理由 —— 每天的資料 commit 只動一個小檔。"""
    store.append("intraday_60m", _bars([("2026-08-03T10:00:00+08:00", "2330", 900.0)]))
    aug = lake / "intraday_60m/year=202608/part.parquet"
    before = aug.stat().st_mtime_ns
    store.append("intraday_60m", _bars([("2026-09-18T11:00:00+08:00", "2330", 1000.0)]))
    assert aug.stat().st_mtime_ns == before, "寫 9 月的資料不該動到 8 月的分割檔"


def test_時區用台北不是UTC(lake):
    """台北 2026-09-01 09:00 換算 UTC 是 08-31 01:00。用 UTC 分月會掉到 8 月去。"""
    store.append("intraday_60m", _bars([("2026-09-01T09:00:00+08:00", "1101", 50.0)]))
    parts = [p.parent.name for p in lake.glob("intraday_60m/year=*/part.parquet")]
    assert parts == ["year=202609"], parts


def test_跨月一次寫進去會分成兩個檔(lake):
    n = store.append("intraday_60m", _bars([
        ("2026-09-30T13:00:00+08:00", "2330", 1000.0),
        ("2026-10-01T09:00:00+08:00", "2330", 1005.0),
    ]))
    assert n == 2
    parts = sorted(p.parent.name for p in lake.glob("intraday_60m/year=*/part.parquet"))
    assert parts == ["year=202609", "year=202610"], parts


def test_讀回來的欄位與內容都對(lake):
    store.append("intraday_60m", _bars([
        ("2026-09-18T09:00:00+08:00", "2330", 1000.0),
        ("2026-09-18T10:00:00+08:00", "2330", 1010.0),
        ("2026-09-18T09:00:00+08:00", "1101", 50.0),
    ]))
    got = store.read("intraday_60m")
    assert len(got) == 3
    for col in ("ts", "code", "open", "high", "low", "close", "volume"):
        assert col in got.columns, f"少了 {col}"
    assert set(got["code"]) == {"2330", "1101"}


def test_按年分割的表不受影響(lake):
    """只有 intraday_60m 按月；別的表改壞了會整個資料湖亂掉。"""
    store.append("price_daily", pd.DataFrame([
        {"date": "2026-09-18", "code": "2330", "close": 1000.0},
        {"date": "2026-08-18", "code": "2330", "close": 900.0},
    ]))
    parts = sorted(p.parent.name for p in lake.glob("price_daily/year=*/part.parquet"))
    assert parts == ["year=2026"], parts


def test_空的不會建出空檔案(lake):
    assert store.append("intraday_60m", pd.DataFrame()) == 0
    assert not list(lake.glob("intraday_60m/year=*/part.parquet"))
