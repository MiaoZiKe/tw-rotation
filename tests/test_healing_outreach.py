import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import healing_outreach as HO  # noqa: E402

NOW = datetime(2026, 11, 26, 4, 0, tzinfo=timezone.utc)
G1 = "月薪四萬的人扣掉房租之後，剩下的錢其實不到三分之一，這種感受很真實，中位數比平均更貼近大多數人的日子。"
G2 = "加班費沒算進去的話，時薪其實被稀釋很多，主計總處的經常性薪資口徑跟實際到手的差距可能比想像大。"


def d(i, author, text=G1, approved=True):
    return {"target_id": str(i), "author": author, "draft": text, "approved": approved, "status": "pending"}


def fake_post(sentlog):
    def f(dd, tok):
        sentlog.append(dd["target_id"])
        return "rid" + dd["target_id"]
    return f


def test_lint_ok_and_redlines():
    assert HO.lint(G1) == []
    e = " ".join(HO.lint("我們的網站有整理 https://x.com 追蹤一下 1925"))
    for w in ("長度", "網址", "導流", "自稱"):
        assert w in e
    assert any("自傷" in x for x in HO.lint("想死的時候真的會覺得什麼都沒有意義，這種心情很需要被好好接住才行啊"))
    assert any("太像" in x for x in HO.lint(G1[:-2] + "喔", recent=[G1]))
    assert HO.lint(G2, recent=[G1]) == []


def test_skip_reason():
    assert "政治" in HO.skip_reason("民進黨又來了")
    assert "自傷" in HO.skip_reason("真的不想活了")
    assert HO.skip_reason("今天薪水又被房租吃掉一半") == ""


def test_dry_run_does_not_send():
    log = []
    r = HO.send([d(1, "a")], {"sent": []}, NOW, live=False, poster=fake_post(log))
    assert r["would"] == 1 and r["sent"] == 0 and log == []


def test_unapproved_not_sent():
    log = []
    r = HO.send([d(1, "a", approved=False)], {"sent": []}, NOW, live=True, poster=fake_post(log))
    assert r["sent"] == 0 and log == []


def test_daily_cap():
    sent = {"sent": [{"ts": (NOW - timedelta(hours=1, minutes=i * 15)).isoformat(), "target_id": f"x{i}", "author": f"p{i}"} for i in range(5)]}
    assert "上限" in HO.can_send(d(9, "z"), sent, NOW)


def test_gap_10_min():
    sent = {"sent": [{"ts": (NOW - timedelta(minutes=5)).isoformat(), "target_id": "x", "author": "p"}]}
    assert "10" in HO.can_send(d(9, "z"), sent, NOW)
    sent["sent"][0]["ts"] = (NOW - timedelta(minutes=11)).isoformat()
    assert HO.can_send(d(9, "z"), sent, NOW) == ""


def test_same_author_once_a_day_and_same_target_once():
    sent = {"sent": [{"ts": (NOW - timedelta(hours=2)).isoformat(), "target_id": "x", "author": "p"}]}
    assert "同一個人" in HO.can_send(d(9, "p"), sent, NOW)
    assert "已回過" in HO.can_send(d("x", "q"), sent, NOW)


def test_live_send_records_and_one_per_run():
    log, sent = [], {"sent": []}
    ds = [d(1, "a"), d(2, "b", G2)]
    r = HO.send(ds, sent, NOW, live=True, poster=fake_post(log), max_per_run=1)
    assert r["sent"] == 1 and log == ["1"] and ds[0]["status"] == "sent" and len(sent["sent"]) == 1


def test_collect_skips_bad_and_dupes():
    ds, sent = [], {"sent": [{"ts": NOW.isoformat(), "target_id": "9", "author": "z"}]}
    c = [{"target_id": "1", "context": "薪水好低", "author": "a", "source": "manual"},
         {"target_id": "2", "context": "民進黨又來了", "author": "b", "source": "manual"},
         {"target_id": "9", "context": "已回過", "author": "z", "source": "manual"},
         {"target_id": "1", "context": "重複", "author": "a", "source": "manual"}]
    assert HO.collect(c, ds, sent, NOW) == 1 and ds[0]["approved"] is False and ds[0]["draft"] == ""


def test_search_own_only_returns_empty():
    me = "healing_me"
    def fake(token, kw, t, n):
        return [{"id": "1", "username": me, "text": "x"}], "f"
    assert HO.search_candidates("t", me, keywords=("薪資",), search=fake) == ([], "own_only")
