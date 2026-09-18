"""個股的 1–12 月平均漲幅（C5）。

Andy 2026-09-18 拍板：「統計過往 15 年 1-12 月的平均漲幅，
並且可以切時間週期 1、3、5 年（可自行填寫）」。

這裡守住三件會出錯的事：
1. **沒有 15 年的就從它有資料的那一年開始算**，並且把實際年數講出來 ——
   上市三年的公司硬湊 15 年只會變成假數字。
2. **當月還沒收完就不算**：把半個月的漲幅算進平均，最近那個月會永遠被拉歪。
3. **給逐年原始值**，前端才切得動 1/3/5/自填年數；只給一個平均值就切不動了。
"""
from __future__ import annotations

import pandas as pd

from pipeline.compute import stockpage


def _px(rows):
    return pd.DataFrame([{"code": c, "date": d, "close": v} for c, d, v in rows])


def _month(code, ym, closes):
    """一個月給幾天，最後一天是月收。"""
    return [(code, f"{ym}-{i + 1:02d}", v) for i, v in enumerate(closes)]


def test_月報酬是月收比前一月收():
    # 3 月的最後一筆給 03-31：那個月是走完的，才不會被「當月還沒收完」那條規則丟掉
    px = _px(_month("2330", "2020-01", [100.0, 110.0])
             + _month("2330", "2020-02", [111.0, 121.0])          # 110 → 121 ＝ +10%
             + [("2330", "2020-03-02", 120.0), ("2330", "2020-03-31", 108.9)])   # 121 → 108.9 ＝ −10%
    got = stockpage.monthly_seasonality(px, "2330", 15)
    assert got["by_year"]["2020"]["2"] == 10.0, got
    assert got["by_year"]["2020"]["3"] == -10.0, got
    assert "1" not in got["by_year"]["2020"], "第一個月沒有前一月可比，不該給數字"


def test_年數不夠就用實際有的年數():
    px = _px(sum([_month("1101", f"{y}-{m:02d}", [10.0, 10.0 + m]) for y in (2024, 2025) for m in (1, 2, 3)], []))
    got = stockpage.monthly_seasonality(px, "1101", 15)
    assert got["years"] == 2, got
    assert got["from"] == "2024" and got["to"] == "2025", got


def test_只取最近N年():
    px = _px(sum([_month("2317", f"{y}-{m:02d}", [10.0, 10.0 + m]) for y in range(2010, 2026) for m in (1, 2)], []))
    got = stockpage.monthly_seasonality(px, "2317", 5)
    assert got["years"] == 5, got
    assert got["from"] == "2021" and got["to"] == "2025", got


def test_當月還沒收完就不算進去():
    """月中抓到的資料，那個月只走了一半 —— 算進平均會把最近一個月拉歪。"""
    px = _px(_month("2454", "2026-07", [100.0, 100.0])
             + _month("2454", "2026-08", [100.0, 120.0])
             + [("2454", "2026-09-01", 121.0), ("2454", "2026-09-10", 60.0)])   # 9 月才走十天
    got = stockpage.monthly_seasonality(px, "2454", 15)
    assert "9" not in got["by_year"].get("2026", {}), got["by_year"]
    assert got["by_year"]["2026"]["8"] == 20.0, got["by_year"]


def test_月底那天抓的就算數():
    """跑在月底最後一個交易日，那個月是走完的，不該被丟掉。"""
    px = _px(_month("2454", "2026-07", [100.0, 100.0])
             + [("2454", "2026-08-31", 120.0)])
    got = stockpage.monthly_seasonality(px, "2454", 15)
    assert got["by_year"]["2026"]["8"] == 20.0, got["by_year"]


def test_逐年給出來前端才切得動():
    px = _px(sum([_month("3008", f"{y}-{m:02d}", [10.0, 10.0 + m]) for y in (2023, 2024, 2025) for m in (1, 2)], []))
    got = stockpage.monthly_seasonality(px, "3008", 15)
    assert set(got["by_year"]) == {"2023", "2024", "2025"}
    assert got["months"] == list(range(1, 13))


def test_查無此股或空資料都不會炸():
    assert stockpage.monthly_seasonality(pd.DataFrame(), "2330", 15)["years"] == 0
    assert stockpage.monthly_seasonality(None, "2330", 15)["years"] == 0
    px = _px(_month("2330", "2020-01", [100.0, 110.0]))
    assert stockpage.monthly_seasonality(px, "9999", 15)["years"] == 0
    assert stockpage.monthly_seasonality(px, "2330", 15)["years"] == 0   # 只有一個月，算不出報酬
