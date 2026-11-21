"""來源健康紀錄（2026-11-06 稽核 B）：跨執行累積、同日去重、成功歸零。"""
from pipeline.util import source_health as sh


def test_連續失敗按天累積_同一天多輪只算一次():
    h = {}
    fail = {"twse.price_daily": {"ok": False, "rows": 0, "error": "HTTP 500"}}
    for day in ("2026-11-02", "2026-11-03", "2026-11-03", "2026-11-03"):  # 三輪同一天
        h = sh.update(h, fail, day)
    assert h["twse.price_daily"]["consecutive_fail"] == 2
    assert h["twse.price_daily"]["last_error"] == "HTTP 500"


def test_成功就歸零_並記最新資料日期():
    h = {"x": {"last_ok_date": None, "consecutive_fail": 3, "last_fail_date": "2026-11-04", "last_error": "e"}}
    h = sh.update(h, {"x": {"ok": True, "rows": 10}}, "2026-11-05")
    assert h["x"]["consecutive_fail"] == 0
    assert h["x"]["last_ok_date"] == "2026-11-05"
    assert h["x"]["last_error"] is None


def test_沒有ok欄位的不是來源_略過():
    h = sh.update({}, {"price_daily": {"stored": 1200}}, "2026-11-05")
    assert h == {}


def test_failing_門檻兩天():
    h = {"a": {"consecutive_fail": 1}, "b": {"consecutive_fail": 2, "last_ok_date": "2026-11-01"}}
    assert [x["source"] for x in sh.failing(h)] == ["b"]


def test_meta_payload帶出連續失敗來源(monkeypatch, tmp_path):
    import json as _j
    import pipeline.build_payload as bp
    (tmp_path / "source_health.json").write_text(_j.dumps(
        {"twse.price_daily": {"consecutive_fail": 2, "last_ok_date": "2026-11-02", "last_error": "HTTP 500"},
         "tpex.price_daily": {"consecutive_fail": 0, "last_ok_date": "2026-11-05"}}))
    (tmp_path / "last_run.json").write_text(_j.dumps({"errors": [], "empty": []}))
    monkeypatch.setattr(bp.config, "STATE", tmp_path)
    monkeypatch.setattr(bp.freshness, "check", lambda *a, **k: {})
    m = bp.meta_payload("2026-11-05", 10)
    assert [x["source"] for x in m["source_failing"]] == ["twse.price_daily"]
    assert m["last_run_errors"] == []
