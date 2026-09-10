"""來源解析的迴歸測試。

這裡防的是一種特別陰險的壞法：**沒有噴例外，但整張表安靜地變成空的**。
2026-09 第一次上線時就中了兩發 ——
證交所股利端點的欄位叫「股利年度」不是「股利所屬年度」，
集保 CSV 開頭有 UTF-8 BOM 讓第一個欄名變成 '﻿資料日期'。
兩者都讓每一列被 skip 條件濾掉，管線照樣回報成功，資料卻一筆都沒進來。

所以這些測試全部離線跑，直接餵真實端點的欄位名進解析函式。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import run_daily  # noqa: E402
from pipeline.sources import tdcc, twse  # noqa: E402


# ------------------------------------------------------------------ 證交所股利

# 欄位名逐字取自 openapi.twse.com.tw/v1/opendata/t187ap45_L 的實際回應。
# 改這份 fixture 之前先確認端點真的改了，不要為了讓測試過而改它。
DIVIDEND_ROW = {
    "出表日期": "1150909",
    "公司代號": "1101",
    "公司名稱": "台泥",
    "股利年度": "114",
    "股利所屬年(季)度": "年度",
    "股東會日期": "1150522",
    "股東配發-盈餘分配之現金股利(元/股)": "2.00000000",
    "股東配發-法定盈餘公積發放之現金(元/股)": "0.0",
    "股東配發-資本公積發放之現金(元/股)": "0.80000000",
    "股東配發-盈餘轉增資配股(元/股)": "0.10000000",
    "股東配發-法定盈餘公積轉增資配股(元/股)": "0.0",
    "股東配發-資本公積轉增資配股(元/股)": "0.0",
}


def test_dividend_parses_real_field_names(monkeypatch):
    """欄位名對得上，而且不是回空表。"""
    monkeypatch.setattr(twse, "_fetch", lambda key: [DIVIDEND_ROW])
    df = twse.dividend()

    assert not df.empty, "欄位名對不上時會靜悄悄回空表，這就是要擋的情況"
    row = df.iloc[0]
    assert row["code"] == "1101"
    assert row["year"] == 2025          # 民國 114 -> 西元 2025


def test_dividend_sums_all_cash_and_stock_components():
    """三個現金來源要相加；只取第一個會少算資本公積那部分。"""
    monkey = pytest.MonkeyPatch()
    monkey.setattr(twse, "_fetch", lambda key: [DIVIDEND_ROW])
    try:
        df = twse.dividend()
    finally:
        monkey.undo()

    assert df.iloc[0]["cash_dividend"] == pytest.approx(2.8)   # 2.0 + 0 + 0.8
    assert df.iloc[0]["stock_dividend"] == pytest.approx(0.1)  # 0.1 + 0 + 0


def test_dividend_leaves_ex_date_empty(monkeypatch):
    """這支端點沒有除權息交易日，不可以拿股東會日期充數。"""
    monkeypatch.setattr(twse, "_fetch", lambda key: [DIVIDEND_ROW])
    assert twse.dividend().iloc[0]["ex_date"] is None


def test_dividend_missing_all_components_is_none_not_zero(monkeypatch):
    """「沒這筆資料」與「配發 0 元」必須分得開，否則殖利率會被灌水成 0。"""
    row = {"公司代號": "9999", "股利年度": "114"}
    monkeypatch.setattr(twse, "_fetch", lambda key: [row])
    assert twse.dividend().iloc[0]["cash_dividend"] is None


# ------------------------------------------------------------------ 集保 BOM

TDCC_CSV = (
    "資料日期,證券代號,持股分級,人數,股數,占集保庫存數比例%\n"
    "20260904,2330,15,2,1000000,45.00\n"
    "20260904,2330,1,500,12345,0.55\n"
)


def test_tdcc_survives_utf8_bom(monkeypatch):
    """集保 CSV 帶 BOM。沒剝掉的話 68867 列會全部被 skip。"""
    monkeypatch.setattr(tdcc.http, "get",
                        lambda *a, **k: "﻿" + TDCC_CSV)
    df = tdcc.shareholding_weekly()

    assert not df.empty, "BOM 沒處理掉時每一列的 資料日期 都會是 None"
    assert df["date"].iloc[0] == "2026-09-04"
    assert set(df["code"]) == {"2330"}


def test_tdcc_without_bom_still_works(monkeypatch):
    """哪天集保拿掉 BOM 了也不能壞。"""
    monkeypatch.setattr(tdcc.http, "get", lambda *a, **k: TDCC_CSV)
    assert len(tdcc.shareholding_weekly()) == 2


def test_tdcc_thousand_lot_level_survives_parsing(monkeypatch):
    """千張大戶（分級 15）是 M1 要用的，確認它有被留下來。"""
    monkeypatch.setattr(tdcc.http, "get",
                        lambda *a, **k: "﻿" + TDCC_CSV)
    df = tdcc.shareholding_weekly()
    ratio = tdcc.big_holder_ratio(df)
    assert ratio.iloc[0]["thousand_lot_pct"] == pytest.approx(45.0)


# ------------------------------------------------------------------ 空來源要浮上來

def test_empty_source_is_recorded_not_swallowed(monkeypatch):
    """回空表不會噴例外，但一定要進 empty_sources，否則摘要會謊報「錯誤數：0」。"""
    import pandas as pd

    monkeypatch.setitem(run_daily.RESULT, "steps", {})
    monkeypatch.setitem(run_daily.RESULT, "errors", [])
    monkeypatch.setitem(run_daily.RESULT, "empty_sources", [])

    run_daily.step("假來源.回空", lambda: pd.DataFrame())

    assert run_daily.RESULT["empty_sources"] == ["假來源.回空"]
    assert run_daily.RESULT["steps"]["假來源.回空"]["ok"] is False
    assert run_daily.RESULT["errors"] == []   # 它確實不是例外，別混為一談


def test_non_empty_source_is_not_flagged(monkeypatch):
    import pandas as pd

    monkeypatch.setitem(run_daily.RESULT, "steps", {})
    monkeypatch.setitem(run_daily.RESULT, "empty_sources", [])

    run_daily.step("假來源.有料", lambda: pd.DataFrame({"a": [1, 2]}))

    assert run_daily.RESULT["empty_sources"] == []
    assert run_daily.RESULT["steps"]["假來源.有料"]["ok"] is True
