import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("ti", Path(__file__).resolve().parent.parent / "scripts" / "threads_insights.py")
ti = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ti)


def test_append_與_report(tmp_path, monkeypatch):
    monkeypatch.setattr(ti, "OUT", tmp_path / "m.csv")
    ti.append([{"fetched_at": "t1", "post_id": "1", "kind": "post", "posted_at": "2026-11-01T10:00",
                "permalink": "u", "text_head": "哈囉", "views": 10, "likes": 2}])
    ti.append([{"fetched_at": "t2", "post_id": "1", "kind": "post", "posted_at": "2026-11-01T10:00",
                "permalink": "u", "text_head": "哈囉", "views": 30, "likes": 5}])
    out = ti.report()
    assert "瀏覽30" in out and "讚5" in out and out.count("哈囉") == 1


def test_insights_解析(monkeypatch):
    monkeypatch.setattr(ti, "_get", lambda *a, **k: {"data": [
        {"name": "views", "values": [{"value": 7}]}, {"name": "likes", "total_value": {"value": 3}}]})
    assert ti.insights("tok", "1") == {"views": 7, "likes": 3}
