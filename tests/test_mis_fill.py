"""「今天的上市要不要用 mis 補」這個判斷。

2026-09-15 線上真的踩到的坑（Andy：「我沒看到最新的」，網站整天停在 09-14）：

    資料湖 09-15 的內容 → 上櫃 1,006 檔、上市 0 檔
    openapi 還停在 09-14（它本來就是 T-1）
    舊的判斷寫成「mis 的交易日 <= 資料湖最新日期 就不用補」
    —— 上櫃自己先把資料湖最新日期推到 09-15 了，於是上市那一半永遠補不進來。
    build_payload 的 last_complete_date 看到「上市 0 檔」不讓日期前進，網站就每天慢一天。

所以這裡守的是：**判斷依據必須是「那一天的上市有幾檔」，不是「資料湖最新日期」。**
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from pipeline import run_daily

TPE = timezone(timedelta(hours=8))


def _px(rows: list[tuple[str, str, int]]) -> pd.DataFrame:
    """(日期, 市場, 檔數) → price_daily 的樣子。"""
    out = []
    for date, market, n in rows:
        base = 1000 if market == "TWSE" else 4000
        out += [{"date": date, "code": str(base + i), "market": market, "close": 10.0}
                for i in range(n)]
    return pd.DataFrame(out)


def _info(n: int = 50) -> pd.DataFrame:
    return pd.DataFrame([{"code": str(1000 + i), "name": f"股{i}", "market": "TWSE"}
                         for i in range(n)])


@pytest.fixture
def lab(monkeypatch):
    """把資料湖與 mis 都換成假的，回一個可以設定情境的小工具。"""
    state: dict = {"px": pd.DataFrame(), "mis_date": None, "snapshot_called": 0,
                   "read_years": None}

    def fake_read(table, *a, **k):
        if table == "price_daily":
            state["read_years"] = k.get("years")
            return state["px"]
        if table == "company_info":
            return _info()
        return pd.DataFrame()

    def fake_latest_date(table, *a, **k):
        px = state["px"]
        return "" if px.empty else str(px["date"].max())

    def fake_snapshot(pairs):
        state["snapshot_called"] += 1
        return pd.DataFrame([{"date": state["mis_date"], "code": c, "market": m,
                              "close": 10.0, "px_source": "mis"} for c, m in pairs])

    monkeypatch.setattr(run_daily.store, "read", fake_read)
    monkeypatch.setattr(run_daily.store, "latest_date", fake_latest_date)
    monkeypatch.setattr(run_daily.mis, "latest_date", lambda *a, **k: state["mis_date"])
    monkeypatch.setattr(run_daily.mis, "price_snapshot", fake_snapshot)
    # 預設把時鐘停在 2026-09-15 收盤後（15:30 那輪），免得每個案例都要自己設
    state["clock"] = datetime(2026, 9, 15, 15, 30, tzinfo=TPE)
    monkeypatch.setattr(run_daily, "_tpe_now", lambda: state["clock"])
    run_daily.RESULT["steps"].pop("mis.date_check", None)
    return state


def _check() -> dict:
    return run_daily.RESULT["steps"]["mis.date_check"]


# ------------------------------------------------------ 2026-09-15 那天的重現

def test_上櫃先到而上市還沒到時要補(lab):
    """線上真的發生的情境：09-15 只有上櫃 1,006 檔，上市 0 檔。"""
    lab["px"] = _px([("2026-09-14", "TWSE", 1324), ("2026-09-14", "TPEX", 1006),
                     ("2026-09-15", "TPEX", 1006)])
    lab["mis_date"] = "2026-09-15"

    got = run_daily.fill_today_from_mis("2026-09-14")

    assert _check()["will_fill"] is True, "上市 0 檔卻判成不用補 —— 這就是網站停在前一天的原因"
    assert _check()["twse_rows_on_mis_date"] == 0
    assert not got.empty and lab["snapshot_called"] == 1


def test_資料湖最新日期不能拿來當判斷依據(lab):
    """同一份資料，最新日期已經是 09-15（上櫃推上去的）—— 舊寫法就是敗在這裡。"""
    lab["px"] = _px([("2026-09-15", "TPEX", 1006)])
    lab["mis_date"] = "2026-09-15"

    run_daily.fill_today_from_mis("2026-09-14")

    assert _check()["lake_latest"] == "2026-09-15"   # 最新日期確實已經是今天
    assert _check()["will_fill"] is True             # 但還是要補，因為上市沒到


# ------------------------------------------------------ 反面：不該白打端點

def test_上市已經到齊就不補(lab):
    lab["px"] = _px([("2026-09-15", "TWSE", 1324), ("2026-09-15", "TPEX", 1006)])
    lab["mis_date"] = "2026-09-15"

    got = run_daily.fill_today_from_mis("2026-09-15")

    assert _check()["will_fill"] is False
    assert got.empty and lab["snapshot_called"] == 0, "已經有資料還去打人家端點"


def test_報價比openapi還舊就不補(lab):
    """假日或 mis 還沒換日：補進去只是把昨天的重寫一次。"""
    lab["px"] = _px([("2026-09-15", "TWSE", 1324)])
    lab["mis_date"] = "2026-09-14"                   # 比 openapi 的 09-15 還舊

    got = run_daily.fill_today_from_mis("2026-09-15")

    assert _check()["will_fill"] is False
    assert got.empty and lab["snapshot_called"] == 0


def test_只差一點點也要補齊(lab):
    """上市只回了 200 檔（半天／來源壞掉）也算沒到齊。"""
    lab["px"] = _px([("2026-09-15", "TWSE", 200), ("2026-09-15", "TPEX", 1006)])
    lab["mis_date"] = "2026-09-15"

    run_daily.fill_today_from_mis("2026-09-14")

    assert _check()["will_fill"] is True
    assert _check()["min_needed"] == run_daily.MIS_FILL_MIN_TWSE


def test_mis拿不到交易日就安靜跳過(lab):
    lab["px"] = _px([("2026-09-15", "TPEX", 1006)])
    lab["mis_date"] = None

    got = run_daily.fill_today_from_mis("2026-09-14")

    assert got.empty and lab["snapshot_called"] == 0
    assert "mis.date_check" not in run_daily.RESULT["steps"]


# ------------------------------------------------------ 盤中不准寫當天的日 K

def test_盤中手動觸發不會把中午的價格寫成當天收盤(lab):
    """盤中寫進去的話，後面幾輪看到「上市已有 1,300 檔」就不會再補，整天的收盤價都是錯的。"""
    lab["px"] = _px([("2026-09-16", "TPEX", 1006)])
    lab["mis_date"] = "2026-09-16"
    lab["clock"] = datetime(2026, 9, 16, 10, 40, tzinfo=TPE)      # 盤中

    got = run_daily.fill_today_from_mis("2026-09-15")

    assert _check()["session_closed"] is False
    assert _check()["will_fill"] is False
    assert got.empty and lab["snapshot_called"] == 0


def test_收盤後同一個情境就要補(lab):
    """跟上一個案例只差時鐘 —— 證明擋下來的是時間，不是別的條件。"""
    lab["px"] = _px([("2026-09-16", "TPEX", 1006)])
    lab["mis_date"] = "2026-09-16"
    lab["clock"] = datetime(2026, 9, 16, 15, 30, tzinfo=TPE)

    got = run_daily.fill_today_from_mis("2026-09-15")

    assert _check()["session_closed"] is True
    assert _check()["will_fill"] is True
    assert not got.empty


def test_比今天早的日期不必問收盤(lab):
    """跨日之後才跑（排程被延遲到半夜）：昨天那一場當然收了。"""
    lab["clock"] = datetime(2026, 9, 17, 1, 5, tzinfo=TPE)
    assert run_daily.session_closed("2026-09-16") is True


def test_收盤那一刻的邊界(lab):
    lab["clock"] = datetime(2026, 9, 16, 13, 34, tzinfo=TPE)
    assert run_daily.session_closed("2026-09-16") is False
    lab["clock"] = datetime(2026, 9, 16, 13, 35, tzinfo=TPE)
    assert run_daily.session_closed("2026-09-16") is True


# ------------------------------------------------------ twse_rows_on 本身

def test_twse_rows_on只數上市(lab):
    lab["px"] = _px([("2026-09-15", "TWSE", 7), ("2026-09-15", "TPEX", 99),
                     ("2026-09-14", "TWSE", 500)])
    assert run_daily.twse_rows_on("2026-09-15") == 7
    assert run_daily.twse_rows_on("2026-09-13") == 0


def test_twse_rows_on沒有market欄位時退回全部(lab):
    """舊資料湖可能沒有 market 欄位；那時只能用總數，總比當成 0 一直重補好。"""
    lab["px"] = pd.DataFrame([{"date": "2026-09-15", "code": str(1000 + i)} for i in range(900)])
    assert run_daily.twse_rows_on("2026-09-15") == 900


def test_資料湖是空的也不會炸(lab):
    lab["px"] = pd.DataFrame()
    assert run_daily.twse_rows_on("2026-09-15") == 0


def test_只讀那一年的分割檔(lab):
    """price_daily 是 2000 年到現在的歷史，為了數一天的檔數整張讀進來太浪費。"""
    lab["px"] = _px([("2026-09-15", "TWSE", 3)])
    run_daily.twse_rows_on("2026-09-15")
    assert lab["read_years"] == [2026]
