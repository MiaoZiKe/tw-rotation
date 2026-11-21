"""最新交易日的挑選：上市資料到齊才算「最新一天」。

背景：2026-09-11 的每日管線只拿到櫃買的最新一天（證交所 OpenAPI 仍是前一天），
build_payload 用 max(date) 當最新日，結果整個上市股票被算漏：個股頁 404、族群統計只剩上櫃。
"""
from __future__ import annotations

import pandas as pd

from pipeline.build_payload import last_complete_date


def _rows(date: str, market: str, n: int) -> list[dict]:
    return [{"date": date, "code": f"{market[0]}{i:04d}", "market": market, "close": 10.0} for i in range(n)]


def test_ignores_day_with_only_otc_rows():
    rows = (_rows("2026-09-09", "TWSE", 1100) + _rows("2026-09-09", "TPEX", 1000)
            + _rows("2026-09-10", "TWSE", 1300) + _rows("2026-09-10", "TPEX", 1000)
            + _rows("2026-09-11", "TPEX", 1000))          # 只有櫃買到了
    assert last_complete_date(pd.DataFrame(rows)) == "2026-09-10"


def test_otc_failure_does_not_stall_update():
    rows = (_rows("2026-09-10", "TWSE", 1300) + _rows("2026-09-10", "TPEX", 1000)
            + _rows("2026-09-11", "TWSE", 1290))          # 櫃買當天抓失敗，上市有到
    assert last_complete_date(pd.DataFrame(rows)) == "2026-09-11"


def test_partial_primary_day_is_rejected():
    rows = (_rows("2026-09-10", "TWSE", 1300)
            + _rows("2026-09-11", "TWSE", 200))            # 上市只回了一小部分（半天／壞資料）
    assert last_complete_date(pd.DataFrame(rows)) == "2026-09-10"


def test_without_market_column_uses_total_counts():
    rows = ([{"date": "2026-09-10", "code": f"{i:04d}"} for i in range(500)]
            + [{"date": "2026-09-11", "code": f"{i:04d}"} for i in range(480)])
    assert last_complete_date(pd.DataFrame(rows)) == "2026-09-11"


def test_single_day_and_empty():
    assert last_complete_date(pd.DataFrame(_rows("2026-09-10", "TWSE", 3))) == "2026-09-10"
    assert last_complete_date(pd.DataFrame(columns=["date", "code"])) == ""
