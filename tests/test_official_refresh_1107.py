"""2026-11-07 事故：news 輪的上市官方價量日期比暫定列舊，卻被記成 ok（W45 交叉比對 5 檔 mismatch）。

事故經過（全部用假資料，不打真 API）：
- 11-06 收盤後湖裡上市是 mis 暫定列（px_source=mis，1336 檔，2330 等）。
- 11-07 05:17 台北的 news 輪 openapi 還停在 11-05，回 1336 列，跟湖裡 11-05 一字不差 → 寫回去等於沒動，
  但 twse.price_daily 記 ok、rows=1336。
- 同一檔 05:30 的交叉比對才抓到官方 11-06，verdict=mismatch。
這支測的是：日期對不上時明寫 stale，同一天 mis 與官方兩筆都在時保留官方那筆。
"""
from __future__ import annotations

import pandas as pd
import pytest

from pipeline import config, run_daily
from pipeline.util import store


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path / "data")
    monkeypatch.setattr(config, "STATE", tmp_path / "state")
    (tmp_path / "data").mkdir()
    (tmp_path / "state").mkdir()
    return tmp_path


def _mis(code, date, close):
    return {"date": date, "code": code, "market": "TWSE", "close": close, "volume": 1000,
            "turnover": 1e7, "px_source": "mis"}


def _off(code, date, close):
    return {"date": date, "code": code, "market": "TWSE", "close": close, "volume": 5000,
            "turnover": 5e7}


def test_官方日期比暫定舊判stale(sandbox):
    lake = pd.DataFrame([_mis("00400A", "2026-11-06", 11.24), _mis("1465", "2026-11-06", 11.4)])
    official_yesterday = pd.DataFrame([_off("00400A", "2026-11-05", 12.06), _off("1465", "2026-11-05", 11.6)])
    ref = run_daily.official_refresh_status(official_yesterday, lake)
    assert ref["status"] == "stale"
    assert ref["official_date"] == "2026-11-05" and ref["provisional_date"] == "2026-11-06"


def test_官方日期追上暫定日判ready(sandbox):
    lake = pd.DataFrame([_mis("00400A", "2026-11-06", 11.24)])
    official = pd.DataFrame([_off("00400A", "2026-11-06", 11.18)])
    assert run_daily.official_refresh_status(official, lake)["status"] == "ready"


def test_湖裡沒有暫定列判no_provisional(sandbox):
    lake = pd.DataFrame([_off("00400A", "2026-11-05", 12.06)])
    ref = run_daily.official_refresh_status(pd.DataFrame([_off("00400A", "2026-11-05", 12.06)]), lake)
    assert ref["status"] == "no_provisional"


def test_沒抓到官方列判empty(sandbox):
    assert run_daily.official_refresh_status(pd.DataFrame(), pd.DataFrame())["status"] == "empty"


def test_同一天mis與官方兩筆都在時保留官方那筆(sandbox):
    store.append("price_daily", pd.DataFrame([_mis("2330", "2026-11-06", 2135.0)]))  # 暫定
    store.append("price_daily", pd.DataFrame([_off("2330", "2026-11-06", 2140.0)]))  # 官方後到
    df = store.read("price_daily")
    rows = df[df["code"] == "2330"]
    assert len(rows) == 1, "同一天同一檔只能留一列"
    assert rows.iloc[0]["close"] == pytest.approx(2140.0), "官方列要贏過暫定列"
    assert pd.isna(rows.iloc[0]["px_source"]), "官方列沒有 px_source，暫定標記要消失"


def test_stale時官方列的日期不會被當成今天的覆蓋(sandbox):
    # 暫定列是 11-06；官方只到 11-05 → 狀態要是 stale，且覆蓋前後 11-06 的暫定列都還在
    store.append("price_daily", pd.DataFrame([_mis("00400A", "2026-11-06", 11.24)]))
    official_yesterday = pd.DataFrame([_off("00400A", "2026-11-05", 12.06)])
    ref = run_daily.official_refresh_status(official_yesterday, store.read("price_daily"))
    assert ref["status"] == "stale"
    store.append("price_daily", official_yesterday)  # 照舊存檔，但 11-06 那列不會因此變官方
    df = store.read("price_daily")
    today = df[(df["code"] == "00400A") & (df["date"].astype(str) == "2026-11-06")].iloc[0]
    assert today["px_source"] == "mis" and today["close"] == pytest.approx(11.24)
