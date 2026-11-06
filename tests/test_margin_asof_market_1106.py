"""稽核 D：margin_asof 看該檔所屬市場的最新「完整日」，不是全湖 max(date)。"""
import pandas as pd

from pipeline.compute import stockpage


def _mk(rows):
    return pd.DataFrame(rows, columns=["date", "code"])


def test_partial_latest_day_not_counted():
    rows = []
    for d in ("2026-11-02", "2026-11-03", "2026-11-04"):
        rows += [(d, f"{i:04d}") for i in range(1000, 1100)]      # 上市 100 檔
        rows += [(d, f"{i:04d}") for i in range(6000, 6050)]      # 上櫃 50 檔
    rows += [("2026-11-05", f"{i:04d}") for i in range(6000, 6050)]   # 11-05 只有上櫃先到
    m = _mk(rows)
    twse = {f"{i:04d}" for i in range(1000, 1100)}
    tpex = {f"{i:04d}" for i in range(6000, 6050)}
    assert stockpage.margin_asof(m, None, None, codes=twse)["margin"] == "2026-11-04"
    assert stockpage.margin_asof(m, None, None, codes=tpex)["margin"] == "2026-11-05"
    # 全湖：11-05 只有 50/150 筆 → 未到齊，不算
    assert stockpage.margin_asof(m, None, None)["margin"] == "2026-11-04"
