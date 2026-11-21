"""練習室籌碼檔的月營收三條序列（pipeline/compute/lab.py _rev_series）：法定可用日＝次月 10 日、年增率、公布後第幾個交易日。"""
import pandas as pd
import pytest

from pipeline.compute.lab import _rev_series


def _rev():
    ym = [str(p) for p in pd.period_range("2024-01", "2025-02", freq="M")]
    return pd.DataFrame({"ym": ym, "revenue": [100.0] * 12 + [150.0, 150.0]})   # 2024 全年 100，2025-01、02 各 150


def _dates():
    return [d.strftime("%Y-%m-%d") for d in pd.bdate_range("2025-02-03", "2025-03-14")]


def test_營收年增率要到次月10日才能用():
    r = _rev_series(_rev(), _dates())
    ry = r["ry"]
    assert pd.isna(ry["2025-02-07"])                      # 2025-01 營收要 2025-02-10 才算公布，7 號還看不到（上一期 2024-12 沒有去年同月＝NaN）
    assert ry["2025-02-10"] == pytest.approx(50.0)        # 2025-01 年增 = 150/100 − 1 = 50%
    assert ry["2025-03-07"] == pytest.approx(50.0)        # 2025-02 營收到 3/10 才可用；3/7 還是上一期
    assert ry["2025-03-10"] == pytest.approx(50.0)        # 2025-02 年增也是 50%


def test_公布後第幾個交易日():
    ra = _rev_series(_rev(), _dates())["ra"]
    assert ra["2025-02-10"] == 0 and ra["2025-02-11"] == 1 and ra["2025-02-14"] == 4
    assert ra["2025-03-10"] == 0 and ra["2025-03-11"] == 1       # 新一期公布，重新計數
    assert ra["2025-02-05"] == 99                                 # 還沒有任何一期可用


def test_營收動能比值():
    rv = _rev_series(_rev(), _dates())["rv"]
    # 2025-02-10：近 3 月＝2024-11、2024-12、2025-01 = (100+100+150)/3；近 12 月＝2024-02～2025-01 = (11×100+150)/12
    assert rv["2025-02-10"] == pytest.approx((350 / 3) / (1250 / 12) * 100)
