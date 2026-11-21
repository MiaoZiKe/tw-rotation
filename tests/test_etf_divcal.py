"""ETF 配息行事曆補下個月（Andy 2026-11-01：「ETF 行事曆每個禮拜都要更新 到下個月」）。全部用假資料，不打真 API。"""
import pandas as pd

from pipeline.compute import etf
from pipeline.sources import exright_notice
from pipeline.util import freshness


def _divs(rows):
    return pd.DataFrame(rows, columns=["code", "ex_date", "amount"])


def test_estimate_covers_this_and_next_month():
    d = _divs([("00878", "2025-11-18", 0.4), ("00878", "2026-08-18", 1.01),
               ("00919", "2025-12-16", 0.54), ("00919", "2026-09-16", 1.1)])
    r = {(x["code"], x["ex"][:7]) for x in etf.estimate_calendar(d, "2026-11-01")}
    assert ("00878", "2026-11") in r and ("00919", "2026-12") in r
    assert {x["ex"][:7] for x in etf.estimate_calendar(d, "2026-11-01")} <= {"2026-11", "2026-12"}


def test_estimate_skips_announced_and_inactive_and_weekend():
    d = _divs([("00878", "2025-11-18", 0.4), ("00878", "2026-11-17", 0.5),      # 已正式公告 → 不預估
               ("00001", "2024-11-20", 1.0),                                     # 太久沒配 → 不預估
               ("00900", "2025-11-15", 0.3), ("00900", "2026-09-01", 0.3)])     # 去年週六 → 順延到週一
    got = {x["code"]: x["ex"] for x in etf.estimate_calendar(d, "2026-11-01")}
    assert "00878" not in got and "00001" not in got
    assert pd.Timestamp(got["00900"]).weekday() < 5


def test_estimate_empty_is_safe():
    assert etf.estimate_calendar(pd.DataFrame(), "2026-11-01") == []


def test_notice_parse_keeps_only_etf_with_amount():
    rows = [{"Date": "1151118", "Code": "00878", "Name": "國泰永續高股息", "CashDividend": "0.42"},
            {"Date": "1151118", "Code": "2330", "Name": "台積電", "CashDividend": "5"},
            {"Date": "1151118", "Code": "00929", "Name": "x", "CashDividend": "0"}]
    df = exright_notice.parse(rows, "TWSE")
    assert list(df["code"]) == ["00878"] and df["ex_date"].iloc[0] == "2026-11-18"
    assert df["period"].iloc[0] == "115" and df["kind"].iloc[0] == "cash"


def test_notice_parse_bad_shape_returns_empty_not_raise():
    assert exright_notice.parse([{"foo": "bar"}], "TPEX").empty
    assert exright_notice.parse(None, "TPEX").empty


def test_notice_fetch_failure_flags(monkeypatch):
    monkeypatch.setattr(exright_notice.http, "get", lambda *a, **k: None)
    df = exright_notice.fetch()
    assert df.empty and df.attrs["raw_ok"] is False and "error" in df.attrs


def test_guard_warns_only_when_month_empty_after_15th():
    ex = ["2025-11-18", "2026-10-20"]
    assert freshness.etf_cal_guard(ex, "2026-11-20")["status"] == "warn"
    assert freshness.etf_cal_guard(ex, "2026-11-05") is None          # 月初投信還沒公告，不告警
    assert freshness.etf_cal_guard(ex + ["2026-11-17"], "2026-11-20") is None
    assert freshness.etf_cal_guard([], "2026-11-20") is None          # 去年同月也沒有 → 不告警
