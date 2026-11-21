"""2026-11-14 週報：收盤後「本來就沒有新資料」的三個來源改記 skipped，不再每晚記成連續失敗。

mis.price_snapshot、yahoo.index_intraday、yahoo.intraday_60m 每晚都被 source_health 記「回空（0 筆）連續失敗 1」。
原因是這幾步在收盤後的第二輪起「湖裡已經有、沒有新的」。比照 11-11 optivx.daily 的做法宣告 skipped。
⚠ 反面一樣重要：Yahoo 完全沒回、或盤中時段回空，仍然要記失敗，不准把真的抓不到藏起來。
"""
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from pipeline import intraday60, run_daily
from pipeline.sources import yahoo

TPE = timezone(timedelta(hours=8))
AFTER = datetime(2026, 11, 13, 18, 30, tzinfo=TPE)    # 週五收盤後
DURING = datetime(2026, 11, 13, 10, 30, tzinfo=TPE)   # 週五盤中


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.setattr(run_daily, "_tpe_now", lambda: AFTER)
    run_daily.RESULT["steps"].clear()
    run_daily.RESULT["empty"].clear()
    yield


def _step(name, fn, *a):
    return run_daily.step(name, fn, *a)


# ---------------------------------------------------------------- 60 分 K
def _patch_60(monkeypatch, got_codes, rows):
    df = pd.DataFrame([{"code": "2330", "ts": "2026-11-13T13:00:00+08:00"}] * rows)
    monkeypatch.setattr(intraday60, "daily_increment",
                        lambda: (df, {"codes": 400, "got_codes": got_codes, "rows": rows, "lake_last": "2026-11-13T13:00:00+08:00"}))


def test_60分K_Yahoo有回但都已在湖裡_記skipped(monkeypatch):
    _patch_60(monkeypatch, 398, 0)
    _step("yahoo.intraday_60m", run_daily.collect_intraday_60m)
    s = run_daily.RESULT["steps"]["yahoo.intraday_60m"]
    assert s["ok"] is True and "skipped" in s
    assert "yahoo.intraday_60m" not in run_daily.RESULT["empty"]


def test_60分K_Yahoo一檔都沒回_仍算失敗(monkeypatch):
    _patch_60(monkeypatch, 0, 0)
    _step("yahoo.intraday_60m", run_daily.collect_intraday_60m)
    assert run_daily.RESULT["steps"]["yahoo.intraday_60m"]["ok"] is False
    assert "yahoo.intraday_60m" in run_daily.RESULT["empty"]


def test_60分K_盤中回空_仍算失敗(monkeypatch):
    monkeypatch.setattr(run_daily, "_tpe_now", lambda: DURING)
    _patch_60(monkeypatch, 398, 0)
    _step("yahoo.intraday_60m", run_daily.collect_intraday_60m)
    assert run_daily.RESULT["steps"]["yahoo.intraday_60m"]["ok"] is False


def test_60分K_有新資料_照常(monkeypatch):
    _patch_60(monkeypatch, 398, 5)
    _step("yahoo.intraday_60m", run_daily.collect_intraday_60m)
    s = run_daily.RESULT["steps"]["yahoo.intraday_60m"]
    assert s["ok"] is True and s["rows"] == 5 and "skipped" not in s


# ---------------------------------------------------------------- 大盤分 K
def _since(fetched):
    out = pd.DataFrame()
    out.attrs["fetched"] = fetched
    return out


def test_大盤分K_Yahoo有回但都是舊根_記skipped(monkeypatch):
    monkeypatch.setattr(run_daily.store, "read", lambda *a, **k: pd.DataFrame())
    monkeypatch.setattr(yahoo, "index_intraday_since", lambda have, iv: _since(120))
    _step("yahoo.index_intraday", run_daily.collect_index_intraday)
    s = run_daily.RESULT["steps"]["yahoo.index_intraday"]
    assert s["ok"] is True and "skipped" in s


def test_大盤分K_Yahoo完全沒回_仍算失敗(monkeypatch):
    monkeypatch.setattr(run_daily.store, "read", lambda *a, **k: pd.DataFrame())
    monkeypatch.setattr(yahoo, "index_intraday_since", lambda have, iv: pd.DataFrame())
    _step("yahoo.index_intraday", run_daily.collect_index_intraday)
    assert run_daily.RESULT["steps"]["yahoo.index_intraday"]["ok"] is False


def test_大盤分K_盤中回空_仍算失敗(monkeypatch):
    monkeypatch.setattr(run_daily, "_tpe_now", lambda: DURING)
    monkeypatch.setattr(run_daily.store, "read", lambda *a, **k: pd.DataFrame())
    monkeypatch.setattr(yahoo, "index_intraday_since", lambda have, iv: _since(120))
    _step("yahoo.index_intraday", run_daily.collect_index_intraday)
    assert run_daily.RESULT["steps"]["yahoo.index_intraday"]["ok"] is False


def test_index_intraday_since_回傳帶fetched(monkeypatch):
    raw = pd.DataFrame({"symbol": ["TSE", "TSE"], "ts": ["2026-11-13T05:00:00Z", "2026-11-13T04:00:00Z"]})
    have = pd.DataFrame({"symbol": ["TSE"], "interval": ["60m"], "ts": ["2026-11-13T05:00:00Z"]})
    monkeypatch.setattr(yahoo, "index_intraday", lambda iv, per: raw)
    monkeypatch.setattr(yahoo, "INDEX_CANDIDATES", ["TSE"])
    out = yahoo.index_intraday_since(have, "60m")
    assert out.empty and out.attrs["fetched"] == 2


# ---------------------------------------------------------------- mis 補今天
@pytest.mark.parametrize("closed_clock,expect_skipped", [(AFTER, True), (DURING, False)])
def test_mis不用補_收盤後skipped_盤中維持回空(monkeypatch, closed_clock, expect_skipped):
    monkeypatch.setattr(run_daily, "_tpe_now", lambda: closed_clock)
    monkeypatch.setattr(run_daily.mis, "latest_date", lambda *a, **k: "2026-11-13")
    monkeypatch.setattr(run_daily, "twse_rows_on", lambda d: 1330)       # 官方已到齊
    monkeypatch.setattr(run_daily.store, "latest_date", lambda *a, **k: "2026-11-13")
    _step("mis.price_snapshot", run_daily.fill_today_from_mis, "2026-11-13")
    s = run_daily.RESULT["steps"]["mis.price_snapshot"]
    if expect_skipped:
        assert s["ok"] is True and "skipped" in s
    else:
        assert s["ok"] is False and "skipped" not in s


def test_mis拿不到交易日_仍算失敗(monkeypatch):
    monkeypatch.setattr(run_daily.mis, "latest_date", lambda *a, **k: None)
    _step("mis.price_snapshot", run_daily.fill_today_from_mis, "2026-11-13")
    assert run_daily.RESULT["steps"]["mis.price_snapshot"]["ok"] is False
