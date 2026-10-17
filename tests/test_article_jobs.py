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


def test_頻率設定同步_第2版_只寫四個欄位_沒變不寫_沒設定不建檔(tmp_path):
    """產文章頻率設定（2026-10-16 第 2 版規則清單）：data/_state/article_schedule.json 在 public repo，不能帶 uid／email；內容沒變就不重寫。"""
    p = tmp_path / "article_schedule.json"
    assert aj.write_schedule_if_changed(None, p) is False and not p.exists()
    rules = [{"days": [1, 3, 5], "hours": [10, 14], "cats": {"news": 1, "intro": 0, "know": 0}},
             {"dates": ["2026-10-20"], "hours": [21], "cats": {"news": 0, "intro": 2, "know": 1}}]
    sch = {"ver": 2, "enabled": True, "rules": rules, "updated": 1792130000000, "by": "uid-secret", "email": "a@b", "legacy": False}
    assert aj.write_schedule_if_changed(sch, p) is True
    d = json.loads(p.read_text(encoding="utf-8"))
    assert set(d) == {"ver", "enabled", "rules", "updated"} and d["ver"] == 2 and d["rules"] == rules
    assert "uid-secret" not in p.read_text(encoding="utf-8")
    assert aj.write_schedule_if_changed({**sch, "updated": 1792139999999}, p) is False   # 只有時間變＝不寫
    assert aj.write_schedule_if_changed({**sch, "enabled": False}, p) is True
    assert aj.write_schedule_if_changed({**sch, "enabled": False, "rules": rules[:1]}, p) is True


def test_頻率設定同步_舊格式也轉成第2版(tmp_path):
    """Worker 還沒重新部署時機器路由回的是第 1 版（slots／cats）；寫進 repo 前一樣轉成第 2 版，Claude 排程只需要認一種。"""
    p = tmp_path / "article_schedule.json"
    old = {"enabled": True, "slots": {"1": ["09:50", "20:50"], "3": ["09:50", "20:50"], "5": ["14:50"]},
           "cats": {"news": 2, "intro": 0, "know": 1}, "updated": 1792130000000}
    assert aj.write_schedule_if_changed(old, p) is True
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d["ver"] == 2 and d["enabled"] is True
    assert d["rules"] == [{"days": [1, 3], "hours": [9, 20], "cats": {"news": 2, "intro": 0, "know": 1}},
                          {"days": [5], "hours": [14], "cats": {"news": 2, "intro": 0, "know": 1}}]
    # 篇數全 0 → 沒規則 → 一律視為關閉
    assert aj.write_schedule_if_changed({**old, "cats": {"news": 0}}, p) is True
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d["enabled"] is False and d["rules"] == []


def test_頻率設定到點_對日期星期與小時_只看最近兩小時():
    from datetime import timezone, timedelta
    tz = timezone(timedelta(hours=8))
    sch = {"ver": 2, "enabled": True, "rules": [
        {"days": [1, 3, 5], "hours": [10, 14], "cats": {"news": 1, "intro": 0, "know": 0}},
        {"dates": ["2026-10-20"], "hours": [21], "cats": {"news": 0, "intro": 2, "know": 0}}]}
    mon = datetime(2026, 10, 19, 10, 41, tzinfo=tz)          # 週一 10:41
    assert [(d, h, i) for d, h, i, _ in aj.due_slots(sch, mon)] == [("2026-10-19", 10, 1)]
    assert [(d, h, i) for d, h, i, _ in aj.due_slots(sch, datetime(2026, 10, 19, 11, 41, tzinfo=tz))] == [("2026-10-19", 10, 1)]  # 晚一小時還補得到
    assert aj.due_slots(sch, datetime(2026, 10, 19, 12, 41, tzinfo=tz)) == []                       # 再晚就不補
    assert aj.due_slots(sch, datetime(2026, 10, 21, 10, 5, tzinfo=tz))[0][:3] == ("2026-10-21", 10, 1)  # 週三
    assert aj.due_slots(sch, datetime(2026, 10, 20, 10, 41, tzinfo=tz)) == []                       # 週二不在 days
    assert [(d, h, i) for d, h, i, _ in aj.due_slots(sch, datetime(2026, 10, 20, 21, 41, tzinfo=tz))] == [("2026-10-20", 21, 2)]
    # UTC 時間傳進來也照台北算（容器跑 UTC）
    assert aj.due_slots(sch, datetime(2026, 10, 19, 2, 41, tzinfo=timezone.utc))[0][:2] == ("2026-10-19", 10)
    assert aj.due_slots({**sch, "enabled": False}, mon) == []
    assert aj.due_slots({"enabled": True, "slots": {"1": ["09:50"]}}, mon) == []   # 不是第 2 版不認


def test_頻率設定到點_排隊清單_id防重複_不挑已用主題_候選用完寫自選():
    from datetime import timezone, timedelta
    tz = timezone(timedelta(hours=8))
    sch = {"ver": 2, "enabled": True, "rules": [{"days": [1], "hours": [10], "cats": {"news": 2, "intro": 0, "know": 1}}]}
    topics = [{"id": "n1", "cat": "news", "title": "快訊一", "score": 3}, {"id": "n2", "cat": "news", "title": "快訊二", "score": 5},
              {"id": "n3", "cat": "news", "title": "快訊三", "score": 4}, {"id": "k1", "cat": "know", "title": "知識一", "score": 1}]
    jobs = aj.plan_schedule_jobs(sch, datetime(2026, 10, 19, 10, 41, tzinfo=tz), topics, used={"n2"})
    assert [j["topic_id"] for j in jobs] == ["sch-20261019-10-r1-news-1", "sch-20261019-10-r1-news-2", "sch-20261019-10-r1-know-1"]
    assert [j["title"] for j in jobs] == ["快訊三", "快訊一", "知識一"]               # 分數高的先、已用的 n2 跳過、同輪不重複
    assert all(j["kind"] == "article" and "建議主題" in j["note"] for j in jobs)
    jobs2 = aj.plan_schedule_jobs(sch, datetime(2026, 10, 19, 10, 41, tzinfo=tz), topics[:1], used={"n1"})
    assert "自選" in jobs2[0]["title"] and jobs2[0]["note"].endswith("建議主題 無")
    # 佇列裡的「建議主題 X」與已上架都算用掉
    assert {"n3", "sch-x"} <= aj.used_topics([{"topic_id": "sch-x", "note": "排程自動排入（規則 1）；建議主題 n3"}], index_path=aj.ROOT / "nope.json")


def test_快照帶階段欄位():
    """2026-10-17 進度條：快照要帶 stage／stage_at，Claude 排程讀檔時看得到做到哪一步。"""
    s = aj.snapshot([{"id": 3, "topic_id": "a", "kind": "article", "title": "t", "status": "working",
                      "stage": "write", "stage_at": 1792130000000, "by": "uid-x"}], now=datetime(2026, 10, 17, 12, 0))
    assert s["jobs"][0]["stage"] == "write" and s["jobs"][0]["stage_at"] == 1792130000000
    assert "by" not in s["jobs"][0]


def test_標狀態帶階段_白名單外不送(capsys):
    assert aj.mark_body("7", "working", "", "write") == {"op": "mark", "id": 7, "status": "working", "result": "", "stage": "write"}
    assert aj.mark_body(7, "working", "", " Illus ")["stage"] == "illus"
    assert "stage" not in aj.mark_body(7, "working", "", "")
    b = aj.mark_body(7, "working", "", "87%")
    assert "stage" not in b and "不在白名單" in capsys.readouterr().out


def test_標狀態_main把階段送出去(monkeypatch):
    monkeypatch.setenv("ACCOUNT_API_URL", "https://x.example")
    monkeypatch.setenv("ARTICLE_BOT_KEY", "k" * 20)
    sent = []

    def fake(base, token, body):
        sent.append(body)
        return {"ok": True, "jobs": []} if body["op"] != "schedule" else {"error": "bad_op"}

    monkeypatch.setattr(aj, "call", fake)
    monkeypatch.setattr(aj, "write_if_changed", lambda *a, **k: False)
    monkeypatch.setattr(aj, "published_topics", lambda *a, **k: {})
    assert aj.main(["--mark", "5", "working", "--stage", "review"]) == 0
    assert sent[0] == {"op": "mark", "id": 5, "status": "working", "result": "", "stage": "review"}
