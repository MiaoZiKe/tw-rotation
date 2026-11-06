"""盤後官方交叉比對（2026-11-06 稽核 C）：判定邏輯用假資料測，不打網路。"""
import pandas as pd

from pipeline.compute import crosscheck as cc


def _lake(date, rows):
    df = pd.DataFrame({"date": [date] * len(rows), "code": [r[0] for r in rows],
                       "close": [r[1] for r in rows], "market": ["TWSE"] * len(rows)})
    return cc._summ(df, "TWSE")


def _official(date, rows):
    df = pd.DataFrame({"date": [date] * len(rows), "code": [r[0] for r in rows],
                       "close": [r[1] for r in rows], "market": ["TWSE"] * len(rows)})
    return cc._summ(df, "TWSE")


ROWS = [(f"{1100 + i}", 10.0 + i) for i in range(20)]


def test_完全一致_判ok():
    r = cc.compare(_official("2026-11-05", ROWS), _lake("2026-11-05", ROWS))
    assert r["verdict"] == "ok" and r["sample_checked"] == 5 and r["sample_mismatch"] == []


def test_湖落後_判lake_behind():
    r = cc.compare(_official("2026-11-05", ROWS), _lake("2026-11-04", ROWS))
    assert r["verdict"] == "lake_behind"


def test_湖比官方新_判lake_ahead不算錯():
    r = cc.compare(_official("2026-11-05", ROWS), _lake("2026-11-06", ROWS))
    assert r["verdict"] == "lake_ahead"


def test_收盤價對不上_判mismatch():
    off = _official("2026-11-05", ROWS)
    target = off["sample"][0]                    # 官方抽樣中的一檔，確定會被比到
    lake_rows = [(c, 99.0 if c == target else p) for c, p in ROWS]
    r = cc.compare(off, _lake("2026-11-05", lake_rows))
    assert r["verdict"] == "mismatch"
    assert [x["code"] for x in r["sample_mismatch"]] == [target]


def test_檔數少超過5_判mismatch():
    r = cc.compare(_official("2026-11-05", ROWS), _lake("2026-11-05", ROWS[:10]))
    assert r["verdict"] == "mismatch" and r["rows_ok"] is False


def test_官方抓不到_判unknown():
    assert cc.compare(None, _lake("2026-11-05", ROWS))["verdict"] == "unknown"


def test_run_寫進source_health的crosscheck(monkeypatch, tmp_path):
    import json
    monkeypatch.setattr(cc.twse, "price_daily", lambda: pd.DataFrame())
    monkeypatch.setattr(cc.tpex, "price_daily", lambda **k: pd.DataFrame())
    monkeypatch.setattr(cc, "_lake_by_market", lambda now: pd.DataFrame())
    p = tmp_path / "source_health.json"
    p.write_text(json.dumps({"twse.price_daily": {"consecutive_fail": 1}}))
    r = cc.run(path=p)
    h = json.loads(p.read_text())
    assert h["crosscheck"]["verdict"] == "unknown"
    assert h["twse.price_daily"]["consecutive_fail"] == 1
    assert r["TWSE"]["verdict"] == "unknown"
