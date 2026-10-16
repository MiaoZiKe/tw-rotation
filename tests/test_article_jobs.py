"""精選文章產出佇列同步（scripts/article_jobs.py）：快照不帶會員欄位、沒變不寫、已上架的 topic 對得到文章。"""
import json
from datetime import datetime

from scripts import article_jobs as aj


def test_快照只留未完成且不帶會員欄位():
    s = aj.snapshot([{"id": 1, "topic_id": "a", "kind": "article", "title": "t", "status": "queued", "by": "uid-x"},
                     {"id": 2, "topic_id": "b", "kind": "video", "title": "t", "status": "done"}],
                    now=datetime(2026, 10, 16, 12, 0))
    assert [j["id"] for j in s["jobs"]] == [1]
    assert "by" not in s["jobs"][0]


def test_沒變不寫(tmp_path):
    p = tmp_path / "j.json"
    d = {"updated": "x", "jobs": [{"id": 1}]}
    assert aj.write_if_changed(d, p) is True
    assert aj.write_if_changed({"updated": "y", "jobs": [{"id": 1}]}, p) is False
    assert aj.write_if_changed({"updated": "y", "jobs": []}, p) is True


def test_已上架topic對應最新文章(tmp_path):
    p = tmp_path / "index.json"
    p.write_text(json.dumps({"articles": [
        {"id": "a1", "topic": "t1", "date": "2026-10-01"}, {"id": "a2", "topic": "t1", "date": "2026-10-10"},
        {"id": "a3", "date": "2026-10-10"}, {"id": "a4", "topic": "t2", "date": "2026-10-10", "status": "draft"}]}), encoding="utf-8")
    assert aj.published_topics(p) == {"t1": "a2"}


def test_沒設金鑰就跳過(monkeypatch):
    monkeypatch.delenv("ACCOUNT_API_URL", raising=False)
    monkeypatch.delenv("BACKUP_TOKEN", raising=False)
    monkeypatch.delenv("ARTICLE_BOT_KEY", raising=False)
    assert aj.main([]) == 0
