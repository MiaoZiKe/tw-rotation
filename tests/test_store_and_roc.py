"""資料湖與格式轉換的驗證。

這兩層錯掉的代價比指標算錯更高：指標算錯可以重算，資料存壞就永遠回不來了。
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.util import roc  # noqa: E402


# ------------------------------------------------------------------ 日期與數值

@pytest.mark.parametrize("raw,expected", [
    ("1150909", date(2026, 9, 9)),        # 民國緊湊格式
    ("115年09月10日", date(2026, 9, 10)),  # 官網中文格式
    ("115/09/10", date(2026, 9, 10)),     # 斜線格式
    ("20260904", date(2026, 9, 4)),       # TDCC 用的是西元
    ("2026-09-04", date(2026, 9, 4)),     # FinMind 用 ISO
])
def test_roc_date_formats(raw, expected):
    assert roc.roc_to_date(raw) == expected


@pytest.mark.parametrize("raw", ["", "--", "N/A", None, "亂碼", "115年13月01日"])
def test_roc_date_rejects_garbage(raw):
    assert roc.roc_to_date(raw) is None


def test_roc_ym():
    assert roc.roc_ym_to_iso("11507") == "2026-07"
    assert roc.roc_ym_to_iso("10012") == "2011-12"
    assert roc.roc_ym_to_iso("11513") is None       # 月份不合法
    assert roc.roc_ym_to_iso("abc") is None


@pytest.mark.parametrize("raw,expected", [
    ("1,234,567", 1234567.0),
    ("-12.5", -12.5),
    ("＋3.2", 3.2),          # 全形正號
    ("(45)", -45.0),         # 括號負數
    ("12.5%", 12.5),
    ("--", None),
    ("X", None),
])
def test_to_float(raw, expected):
    assert roc.to_float(raw) == expected


def test_thousand_scale():
    """月營收與財報是千元單位，換算錯會讓所有基本面數字差 1000 倍。"""
    assert roc.to_float("1,000", thousand_scale=True) == 1_000_000.0


def test_code_classification():
    assert roc.is_common_stock("2330")
    assert not roc.is_common_stock("0050")      # ETF
    assert not roc.is_common_stock("2330A")     # 特別股
    assert roc.is_etf("0050") and roc.is_etf("00878")
    assert roc.clean_code("  2330 ") == "2330"


# ------------------------------------------------------------------ 資料湖

@pytest.fixture()
def store(tmp_path, monkeypatch):
    """把資料湖指到暫存目錄，避免測試污染真實資料。"""
    from pipeline import config
    monkeypatch.setattr(config, "DATA", tmp_path / "data")
    (tmp_path / "data").mkdir()
    import importlib

    from pipeline.util import store as store_mod
    importlib.reload(store_mod)
    monkeypatch.setattr(store_mod.config, "DATA", tmp_path / "data")
    return store_mod


def _price(dates, code="2330", close=100.0):
    return pd.DataFrame({
        "date": dates,
        "code": [code] * len(dates),
        "close": [close] * len(dates),
    })


def test_append_then_read(store):
    n = store.append("price_daily", _price(["2026-09-09", "2026-09-10"]))
    assert n == 2
    df = store.read("price_daily")
    assert len(df) == 2 and set(df["date"]) == {"2026-09-09", "2026-09-10"}


def test_append_is_idempotent(store):
    """同一天的資料重跑兩次，不能變成兩列 —— 排程重試時一定會發生。"""
    store.append("price_daily", _price(["2026-09-10"]))
    added = store.append("price_daily", _price(["2026-09-10"]))
    assert added == 0
    assert len(store.read("price_daily")) == 1


def test_reprocessed_data_wins(store):
    """後到的同一筆視為更正版本，覆蓋舊值但不新增列。"""
    store.append("price_daily", _price(["2026-09-10"], close=100.0))
    store.append("price_daily", _price(["2026-09-10"], close=105.0))
    df = store.read("price_daily")
    assert len(df) == 1 and df["close"].iloc[0] == 105.0


def test_non_trading_day_duplicate_absorbed(store):
    """非交易日 API 會靜默回上一個交易日的資料，去重必須把它吃掉。"""
    friday = _price(["2026-09-11"])
    store.append("price_daily", friday)
    store.append("price_daily", friday)   # 週六抓到的是同一份
    assert len(store.read("price_daily")) == 1


def test_year_partitioning(store):
    store.append("price_daily", _price(["2025-12-31", "2026-01-02"]))
    parts = sorted(p.parent.name for p in
                   (store.config.DATA / "price_daily").glob("year=*/part.parquet"))
    assert parts == ["year=2025", "year=2026"]


def test_append_rejects_missing_key(store):
    with pytest.raises(ValueError, match="缺少 key 欄位"):
        store.append("price_daily", pd.DataFrame({"close": [1.0]}))


def test_append_rejects_unknown_table(store):
    with pytest.raises(KeyError):
        store.append("no_such_table", _price(["2026-09-10"]))


def test_empty_append_is_noop(store):
    assert store.append("price_daily", pd.DataFrame()) == 0
    assert store.read("price_daily").empty


def test_latest_date(store):
    store.append("price_daily", _price(["2026-09-08", "2026-09-10", "2026-09-09"]))
    assert store.latest_date("price_daily") == "2026-09-10"


def test_monthly_table_partitions_by_ym(store):
    df = pd.DataFrame({"ym": ["2026-07", "2025-12"], "code": ["2330", "2330"],
                       "revenue": [1.0, 2.0]})
    store.append("revenue_monthly", df)
    parts = sorted(p.parent.name for p in
                   (store.config.DATA / "revenue_monthly").glob("year=*/part.parquet"))
    assert parts == ["year=2025", "year=2026"]


# ------------------------------------------------------------------ 標的過濾

@pytest.mark.parametrize("code,expected", [
    ("2330", True),    # 普通股
    ("1101", True),
    ("2603", True),
    ("0050", True),    # ETF
    ("00878", True),
    ("00631L", True),  # 正2
    ("00981A", True),  # 主動式
    ("030123", False), # 權證
    ("088456", False),
    ("07123X", False),
    ("2881A", False),  # 特別股
    ("12345", False),
    ("", False),
    (None, False),
])
def test_tradable_security_filter(code, expected):
    """權證數量遠多於股票，濾錯會讓「上漲家數」變成五千多家。"""
    assert roc.is_tradable_security(code) is expected


@pytest.mark.parametrize("raw, expected", [
    ("其他電子類", "其他電子業"),   # 上櫃寫法要併回上市寫法
    ("其他電子業", "其他電子業"),
    ("上櫃ETF", "ETF"),
    ("上櫃指數股票型基金(ETF)", "ETF"),
    ("指數投資證券(ETN)", "ETN"),
    ("居家生活類", "居家生活"),
    ("金融業", "金融保險"),
    ("  半導體業 ", "半導體業"),     # 前後空白
    ("91", "其他"),                  # 殘留代號不是產業別
    ("大盤", "其他"),
    ("所有證券", "其他"),
    ("", "其他"),
    (None, "其他"),
    (float("nan"), "其他"),
])
def test_norm_industry(raw, expected):
    """上市／上櫃兩套產業別沒統一的話，同一個產業會產出兩個族群頁與兩塊熱力圖板塊。"""
    assert roc.norm_industry(raw) == expected


def test_purge_removes_only_non_tradable(store):
    df = pd.DataFrame({
        "date": ["2026-09-10"] * 4,
        "code": ["2330", "0050", "030123", "088456"],
        "close": [1000.0, 200.0, 1.2, 0.8],
    })
    store.append("price_daily", df)
    assert len(store.read("price_daily")) == 4

    removed = store.purge("price_daily", roc.is_tradable_security)
    assert removed == 2
    left = store.read("price_daily")
    assert sorted(left["code"]) == ["0050", "2330"]

    # 再清一次不該有任何變動
    assert store.purge("price_daily", roc.is_tradable_security) == 0
