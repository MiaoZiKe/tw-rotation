"""v3 新資料源：FinMind 股利 / 除權息 / 融資券 / 股權分散歷史，與 Yahoo 分 K。

開發環境沒有對外網路，全部用規格書裡的實測回應樣本 monkeypatch。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import config  # noqa: E402
from pipeline.sources import finmind, tdcc, yahoo  # noqa: E402
from pipeline.sources import twse  # noqa: E402
from pipeline.util import http  # noqa: E402

# ------------------------------------------------------------------ 樣本（規格書實測）

DIVIDEND_ROW = {
    "AnnouncementDate": "2026-09-01", "CashDividendPaymentDate": "2026-10-08",
    "CashEarningsDistribution": 7.00000137, "CashExDividendTradingDate": "2026-09-16",
    "CashStatutorySurplus": 0, "StockEarningsDistribution": 0, "StockStatutorySurplus": 0,
    "StockExDividendTradingDate": "", "date": "2026-09-22", "stock_id": "2330",
    "year": "115年第1季",
}
DIVIDEND_ROW_BOTH = {
    "AnnouncementDate": "2025-03-01", "CashDividendPaymentDate": "",
    "CashEarningsDistribution": 1.5, "CashExDividendTradingDate": "",
    "CashStatutorySurplus": 0.5, "StockEarningsDistribution": 0.2, "StockStatutorySurplus": 0.3,
    "StockExDividendTradingDate": "2025-08-01", "date": "2025-07-22", "stock_id": "2330",
    "year": "114年",
}
DIVRESULT_ROW = {
    "after_price": 2248.99, "before_price": 2255, "date": "2026-06-11", "max_price": 2470,
    "min_price": 2025, "open_price": 2250, "reference_price": 2248.99,
    "stock_and_cache_dividend": 6.000035, "stock_id": "2330", "stock_or_cache_dividend": "息",
}
MARGIN_ROW = {
    "MarginPurchaseBuy": 728, "MarginPurchaseCashRepayment": 6, "MarginPurchaseLimit": 6483092,
    "MarginPurchaseSell": 227, "MarginPurchaseTodayBalance": 28474,
    "MarginPurchaseYesterdayBalance": 27979, "OffsetLoanAndShort": 0,
    "ShortSaleBuy": 30, "ShortSaleCashRepayment": 4, "ShortSaleLimit": 6483092,
    "ShortSaleSell": 0, "ShortSaleTodayBalance": 2, "ShortSaleYesterdayBalance": 36,
    "date": "2026-09-10", "stock_id": "2330",
}


def _holding_row(level: str, people: int, unit: float, pct: float) -> dict:
    return {"date": "2026-09-05", "stock_id": "2330", "HoldingSharesLevel": level,
            "people": people, "unit": unit, "percent": pct}


HOLDING_ROWS = [
    _holding_row("1-999", 100, 1000, 1.5),
    _holding_row("1,000-5,000", 50, 2000, 2.5),
    _holding_row(" 1,000,001 以上", 3, 8000, 40.0),      # 帶空白也要對得上
    _holding_row("more than 1,000,001", 5, 9000, 60.0),
    _holding_row("total", 155, 12000, 100.0),
    _holding_row("差異數調整", 0, 0, 0.0),
    _holding_row("whatever", 9, 9, 9.0),                 # 對不上的略過
]


@pytest.fixture()
def fake_finmind(monkeypatch):
    """把 http.finmind_get 換成查表；記下每次呼叫的參數。"""
    calls: list[dict] = []
    payloads: dict[str, object] = {}

    def fake_get(dataset, **kw):
        calls.append({"dataset": dataset, **kw})
        return payloads.get(dataset)

    monkeypatch.setattr(http, "finmind_get", fake_get)
    return payloads, calls


# ------------------------------------------------------------------ 股利公告

def test_dividend_events_expands_cash_and_skips_zero_stock(fake_finmind):
    payloads, calls = fake_finmind
    payloads["TaiwanStockDividend"] = [DIVIDEND_ROW]
    df = finmind.dividend_events("2330", "2016-01-01", wait=False)

    assert calls == [{"dataset": "TaiwanStockDividend", "data_id": "2330",
                      "start_date": "2016-01-01", "wait_when_exhausted": False}]
    assert list(df.columns) == ["code", "period", "kind", "amount", "announce_date",
                                "ex_date", "payment_date", "fiscal_year"]
    assert len(df) == 1, "股票股利為 0 不輸出"
    r = df.iloc[0]
    assert r["code"] == "2330" and r["period"] == "115年第1季" and r["kind"] == "cash"
    assert r["amount"] == pytest.approx(7.00000137)
    assert r["announce_date"] == "2026-09-01"
    assert r["ex_date"] == "2026-09-16"
    assert r["payment_date"] == "2026-10-08"
    assert r["fiscal_year"] == 2026


def test_dividend_events_both_kinds_and_blank_dates(fake_finmind):
    payloads, _ = fake_finmind
    payloads["TaiwanStockDividend"] = [DIVIDEND_ROW, DIVIDEND_ROW_BOTH]
    df = finmind.dividend_events("2330", "2016-01-01")
    assert len(df) == 3
    both = df[df["period"] == "114年"].set_index("kind")
    assert set(both.index) == {"cash", "stock"}
    # 現金 = 盈餘 + 公積；股票同理
    assert both.loc["cash", "amount"] == pytest.approx(2.0)
    assert both.loc["stock", "amount"] == pytest.approx(0.5)
    # 空字串日期 → None
    assert both.loc["cash", "ex_date"] is None
    assert both.loc["cash", "payment_date"] is None
    assert both.loc["stock", "ex_date"] == "2025-08-01"
    assert both.loc["stock", "payment_date"] is None, "股票股利沒有發放日"
    assert (both["fiscal_year"] == 2025).all()
    # key 欄位齊全，可以進資料湖
    assert all(k in df.columns for k in config.TABLES["dividend_events"])


def test_dividend_events_non_200_returns_empty(fake_finmind):
    payloads, _ = fake_finmind
    payloads["TaiwanStockDividend"] = None       # finmind_get 遇到非 200 回 None
    assert finmind.dividend_events("2330", "2016-01-01").empty
    payloads["TaiwanStockDividend"] = []
    assert finmind.dividend_events("2330", "2016-01-01").empty


@pytest.mark.parametrize("period,expected", [
    ("115年第1季", 2026), ("114年", 2025), ("113年上半年", 2024), ("2024", 2024),
    ("", None), (None, None), ("N/A", None),
])
def test_fiscal_year_parse(period, expected):
    assert finmind.fiscal_year_of(period) == expected


# ------------------------------------------------------------------ 除權息結果

def test_dividend_results_fields(fake_finmind):
    payloads, calls = fake_finmind
    payloads["TaiwanStockDividendResult"] = [DIVRESULT_ROW]
    df = finmind.dividend_results("2330", "2016-01-01", wait=False)
    assert calls[0]["dataset"] == "TaiwanStockDividendResult"
    assert list(df.columns) == ["date", "code", "kind", "dividend", "before_price",
                                "reference_price", "open_price"]
    r = df.iloc[0]
    assert r["date"] == "2026-06-11" and r["code"] == "2330" and r["kind"] == "息"
    assert r["dividend"] == pytest.approx(6.000035)
    assert r["before_price"] == 2255
    assert r["reference_price"] == pytest.approx(2248.99)
    assert r["open_price"] == 2250
    assert all(k in df.columns for k in config.TABLES["dividend_results"])


def test_dividend_results_non_200_returns_empty(fake_finmind):
    payloads, _ = fake_finmind
    payloads["TaiwanStockDividendResult"] = None
    assert finmind.dividend_results("2330", "2016-01-01").empty


# ------------------------------------------------------------------ 融資融券

def test_margin_history_aligns_with_twse_margin_daily(fake_finmind, monkeypatch):
    payloads, calls = fake_finmind
    payloads["TaiwanStockMarginPurchaseShortSale"] = [MARGIN_ROW]
    df = finmind.margin_history("2330", "2021-01-01", wait=False)
    assert calls[0]["dataset"] == "TaiwanStockMarginPurchaseShortSale"
    assert calls[0]["start_date"] == "2021-01-01"

    r = df.iloc[0]
    assert r["date"] == "2026-09-10" and r["code"] == "2330"
    assert r["margin_balance"] == 28474
    assert r["margin_change"] == 28474 - 27979
    assert r["short_balance"] == 2
    assert r["short_change"] == 2 - 36
    assert r["margin_buy"] == 728 and r["margin_sell"] == 227
    assert r["short_sell"] == 0 and r["short_cover"] == 30
    assert r["offset"] == 0

    # 欄位要跟證交所 MI_MARGN 的轉換完全一致，才能 append 進同一張 margin_daily
    monkeypatch.setattr(twse, "_fetch", lambda key: [{
        "股票代號": "2330", "融資前日餘額": "27979", "融資今日餘額": "28474",
        "融券前日餘額": "36", "融券今日餘額": "2", "融資買進": "728", "融資賣出": "227",
        "融券賣出": "0", "融券買進": "30", "資券互抵": "0",
    }])
    ref = twse.margin_daily("2026-09-10")
    assert list(df.columns) == list(ref.columns)
    assert df.iloc[0].to_dict() == {k: (v if isinstance(v, str) else float(v))
                                    for k, v in ref.iloc[0].to_dict().items()}


def test_margin_history_non_200_returns_empty(fake_finmind):
    payloads, _ = fake_finmind
    payloads["TaiwanStockMarginPurchaseShortSale"] = None
    assert finmind.margin_history("2330", "2021-01-01").empty


# ------------------------------------------------------------------ 股權分散

def test_holding_history_maps_levels_loosely(fake_finmind, caplog):
    payloads, calls = fake_finmind
    payloads["TaiwanStockHoldingSharesPer"] = HOLDING_ROWS
    with caplog.at_level("WARNING"):
        df = finmind.holding_history("2330", "2021-01-01", wait=False)
    assert calls[0]["dataset"] == "TaiwanStockHoldingSharesPer"

    assert list(df.columns) == ["date", "code", "level", "level_label",
                                "holders", "shares", "pct"]
    assert df["level"].tolist() == [1, 2, 15, 15, 17, 16], "對不上的 whatever 要略過"
    assert df["level_label"].tolist() == [tdcc.LEVEL_LABELS[v] for v in df["level"]]
    assert df["holders"].tolist() == [100, 50, 3, 5, 155, 0]
    assert df["shares"].tolist() == [1000, 2000, 8000, 9000, 12000, 0]
    assert df["pct"].tolist() == [1.5, 2.5, 40.0, 60.0, 100.0, 0.0]
    assert (df["date"] == "2026-09-05").all() and (df["code"] == "2330").all()
    # 對不上的級距只 log 一次，且把標籤列出來
    warn = [r for r in caplog.records if "級距" in r.getMessage()]
    assert len(warn) == 1 and "whatever" in warn[0].getMessage()
    assert all(k in df.columns for k in config.TABLES["shareholding_weekly"])


def test_holding_history_non_200_or_all_unknown_returns_empty(fake_finmind):
    payloads, _ = fake_finmind
    payloads["TaiwanStockHoldingSharesPer"] = None      # 免費層不開放 → 非 200 → None
    assert finmind.holding_history("2330", "2021-01-01").empty
    payloads["TaiwanStockHoldingSharesPer"] = [_holding_row("??", 1, 1, 1.0)]
    assert finmind.holding_history("2330", "2021-01-01").empty


@pytest.mark.parametrize("label,expected", [
    ("1-999", 1), ("1,000-5,000", 2), ("1,000,001以上", 15), ("more than 1,000,001", 15),
    ("MORE THAN 1,000,001", 15), ("total", 17), ("合計", 17), ("差異數調整", 16),
    ("800,001 - 1,000,000", 14), ("", None), (None, None), ("nope", None),
])
def test_holding_level_lookup(label, expected):
    assert finmind.holding_level(label) == expected


# ------------------------------------------------------------------ Yahoo 分 K

def _multi_frame(symbols: list[str], n: int = 3, freq: str = "60min") -> pd.DataFrame:
    idx = pd.date_range("2026-09-10 09:00", periods=n, freq=freq, tz="Asia/Taipei")
    cols = pd.MultiIndex.from_product([symbols, ["Open", "High", "Low", "Close", "Adj Close", "Volume"]])
    data = np.arange(n * len(cols), dtype=float).reshape(n, len(cols))
    return pd.DataFrame(data, index=idx, columns=cols)


@pytest.fixture()
def fake_yf(monkeypatch):
    import yfinance
    calls: list[dict] = []
    state = {"frame": None, "error": None}

    def fake_download(tickers, **kw):
        calls.append({"tickers": list(tickers), **kw})
        if state["error"]:
            raise state["error"]
        f = state["frame"]
        return f(tickers) if callable(f) else f

    monkeypatch.setattr(yfinance, "download", fake_download)
    monkeypatch.setattr(yahoo.time, "sleep", lambda s: None)
    return state, calls


def test_intraday_multiindex_to_long(fake_yf):
    state, calls = fake_yf
    frame = _multi_frame(["2330.TW", "6488.TWO"])
    frame.loc[frame.index[1], ("6488.TWO", "Close")] = np.nan     # 缺 K 要丟掉
    state["frame"] = frame

    df = yahoo.intraday(["2330", "6488"], {"6488": "TPEX", "2330": "TWSE"}, "60m", "730d")

    assert calls[0]["tickers"] == ["2330.TW", "6488.TWO"], "上櫃 .TWO、上市 .TW"
    assert calls[0]["interval"] == "60m" and calls[0]["period"] == "730d"
    assert calls[0]["group_by"] == "ticker" and calls[0]["auto_adjust"] is False
    assert calls[0]["progress"] is False and calls[0]["threads"] is True

    assert list(df.columns) == ["ts", "code", "open", "high", "low", "close", "volume"]
    assert df["code"].tolist() == ["2330"] * 3 + ["6488"] * 2
    assert df["ts"].str.endswith("+08:00").all()
    assert df["ts"].iloc[0] == "2026-09-10T09:00:00+08:00"
    assert df["ts"].iloc[1] == "2026-09-10T10:00:00+08:00"
    # 2330 第一根：Open/High/Low/Close/Volume 對到 0/1/2/3/5（Adj Close 是 4，不要拿錯）
    first = df.iloc[0]
    assert (first["open"], first["high"], first["low"], first["close"], first["volume"]) == (0, 1, 2, 3, 5)


def test_intraday_single_level_frame(fake_yf):
    state, calls = fake_yf
    idx = pd.date_range("2026-09-10 09:00", periods=2, freq="15min", tz="Asia/Taipei")
    state["frame"] = pd.DataFrame({"Open": [1.0, 2.0], "High": [1.5, 2.5], "Low": [0.5, 1.5],
                                   "Close": [1.2, np.nan], "Adj Close": [1.2, 2.2],
                                   "Volume": [10, 20]}, index=idx)
    df = yahoo.intraday(["2330"], {}, "15m", "60d")
    assert calls[0]["tickers"] == ["2330.TW"], "不在 markets 裡的代號視為上市"
    assert len(df) == 1 and df.iloc[0]["code"] == "2330"
    assert df.iloc[0]["ts"] == "2026-09-10T09:00:00+08:00"
    assert df.iloc[0]["close"] == pytest.approx(1.2)


def test_intraday_converts_utc_and_naive_to_taipei(fake_yf):
    state, _ = fake_yf
    utc_idx = pd.date_range("2026-09-10 01:00", periods=1, freq="60min", tz="UTC")
    state["frame"] = pd.DataFrame({"Open": [1.0], "High": [1.0], "Low": [1.0],
                                   "Close": [1.0], "Volume": [1]}, index=utc_idx)
    df = yahoo.intraday(["2330"], {}, "60m", "730d")
    assert df.iloc[0]["ts"] == "2026-09-10T09:00:00+08:00"

    naive_idx = pd.date_range("2026-09-10 09:00", periods=1, freq="60min")
    state["frame"] = pd.DataFrame({"Open": [1.0], "High": [1.0], "Low": [1.0],
                                   "Close": [1.0], "Volume": [1]}, index=naive_idx)
    df = yahoo.intraday(["2330"], {}, "60m", "730d")
    assert df.iloc[0]["ts"] == "2026-09-10T09:00:00+08:00"


def test_intraday_batches_and_keeps_partial_on_error(fake_yf):
    state, calls = fake_yf
    codes = [f"{2300 + i}" for i in range(5)]

    def frame_for(tickers):
        if "2303.TW" in tickers:
            raise RuntimeError("Yahoo 掛了")
        return _multi_frame(list(tickers), n=1)

    state["frame"] = frame_for
    df = yahoo.intraday(codes, {}, "60m", "730d", batch=2)
    assert [c["tickers"] for c in calls] == [["2300.TW", "2301.TW"], ["2302.TW", "2303.TW"], ["2304.TW"]]
    assert sorted(df["code"].unique()) == ["2300", "2301", "2304"], "失敗那批略過，其餘保留"


def test_intraday_all_failed_or_empty_returns_empty(fake_yf):
    state, _ = fake_yf
    state["error"] = RuntimeError("boom")
    assert yahoo.intraday(["2330"], {}, "60m", "730d").empty
    state["error"] = None
    state["frame"] = pd.DataFrame()
    assert yahoo.intraday(["2330"], {}, "60m", "730d").empty
    assert yahoo.intraday([], {}, "60m", "730d").empty
