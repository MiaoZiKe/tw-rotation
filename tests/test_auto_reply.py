"""自動回覆（scripts/auto_reply.py、reply_lint.py）與熱門串採集（threads_search.py、threads_hot_collect.py）。
全部離線：Meta API 與 Claude 都用假的函式代替，不會真的發文。"""
from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import auto_reply as AR  # noqa: E402
import reply_lint as RL  # noqa: E402
import threads_hot_collect as HC  # noqa: E402
import threads_search as S  # noqa: E402

TPE = timezone(timedelta(hours=8))
NOW = datetime(2026, 11, 10, 14, 0, tzinfo=TPE)
GOOD = "外資這波賣超其實集中在權值股，中小型反而有人在接，籌碼比表面看起來分散很多"
GOOD2 = "其實殖利率高不代表配得穩，看一下近五年填息天數會比較準，這個常被忽略掉"


def q(**b):
    x = AR.load_quota(ROOT / "docs" / "marketing" / "social_unit" / "reply_quota.json")
    x["b_others"].update(b)
    return x


# ── reply_lint ──
def test_lint_pass_and_redlines():
    assert RL.check(GOOD) == []
    e = " ".join(RL.check("台積電上看1500，趕快上車 https://x.com"))
    for w in ("長度", "網址", "上看", "上車", "台積電", "代號"):
        assert w in e


def test_lint_template_promo_similarity():
    assert any("模板" in x for x in RL.check("感謝分享！" + GOOD[:30]))
    assert any("導流" in x for x in RL.check("更多整理都在我們網站上，" + GOOD[:30]))
    assert any("太像" in x for x in RL.check(GOOD[:-2] + "喔", recent=[GOOD]))
    assert RL.check(GOOD2, recent=[GOOD]) == []


def test_skip_reason():
    assert "政治" in RL.skip_reason("民進黨又來了")
    assert "謾罵" in RL.skip_reason("你這智障")
    assert "指控" in RL.skip_reason("這檔就是主力倒貨")
    assert RL.skip_reason("今天盤面好弱") == ""


def test_quota_defaults_a_on_b_off():
    x = AR.load_quota(ROOT / "docs" / "marketing" / "social_unit" / "reply_quota.json")
    assert x["a_own"]["enabled"] is True and x["b_others"]["enabled"] is False
    assert 8 <= x["b_others"]["per_day_min"] <= x["b_others"]["per_day_max"] <= 15
    assert x["window"] == {"start": "09:00", "end": "23:00"}


# ── A 層 collect ──
def fake_threads(method, path, tok, params=None):
    if path == "/me":
        return {"id": "U1", "username": "liguligu0818"}
    if path == "/me/threads":
        return {"data": [{"id": "P1", "text": "盤後整理", "timestamp": "2026-11-10T05:00:00+0000"}]}
    if path == "/P1/replies":
        return {"data": [
            {"id": "R1", "text": "外資今天怎麼賣這麼多？", "username": "a", "timestamp": "2026-11-10T05:10:00+0000"},
            {"id": "R2", "text": "國民黨怎樣怎樣", "username": "b", "timestamp": "2026-11-10T05:11:00+0000"},
            {"id": "R3", "text": "自己的出處", "username": "liguligu0818", "timestamp": "2026-11-10T05:12:00+0000"},
            {"id": "R4", "text": "很久以前的留言", "username": "c", "timestamp": "2026-10-01T05:12:00+0000"}]}
    raise AssertionError(path)


def test_collect_a_filters_and_dedupes():
    st = {"items": {}}
    r = AR.collect_a(st, q(), {"THREADS_ACCESS_TOKEN": "x"}, NOW, tcall=fake_threads)
    assert (r["new"], r["skipped"]) == (1, 1)
    items = list(st["items"].values())
    assert {i["status"] for i in items} == {"pending", "skipped"}
    assert all("username" not in i and len(i["author"]) == 16 for i in items)       # 不存帳號名稱
    r2 = AR.collect_a(st, q(), {"THREADS_ACCESS_TOKEN": "x"}, NOW, tcall=fake_threads)
    assert r2["new"] == 0                                                              # 不重複


# ── 寫稿／套稿／排程 ──
def _pending(layer="A"):
    st = {"items": {}}
    AR._add(st, NOW, "k1", layer=layer, platform="threads", target_id="R1", post_id="P1", author="h", context="", comment="外資？",
            status="pending", reason="")
    return st


def test_draft_without_key_leaves_for_ceo():
    st = _pending()
    r = AR.draft(st, q(), {}, NOW, random.Random(1))
    assert r["left_for_ceo"] == 1 and st["items"]["k1"]["status"] == "pending"


def test_draft_with_fake_claude_and_schedule_in_window():
    st = _pending()
    r = AR.draft(st, q(), {"ANTHROPIC_API_KEY": "k"}, NOW, random.Random(1), writer=lambda it, k, rec: GOOD)
    it = st["items"]["k1"]
    assert r["drafted"] == 1 and it["status"] == "drafted" and it["drafter"] == "claude-api"
    due = AR.parse_t(it["due_at"])
    assert NOW + timedelta(minutes=6) <= due <= NOW + timedelta(minutes=75)


def test_bad_draft_rejected_then_skipped_after_three():
    st = _pending()
    for _ in range(3):
        AR.apply_drafts(st, q(), {"k1": "台積電會漲啦"}, NOW, random.Random(1))
    assert st["items"]["k1"]["status"] == "skipped"


def test_schedule_late_night_moves_to_next_morning():
    st = _pending()
    late = datetime(2026, 11, 10, 22, 50, tzinfo=TPE)
    AR.apply_drafts(st, q(), {"k1": GOOD}, late, random.Random(3))
    due = AR.parse_t(st["items"]["k1"]["due_at"])
    assert due.date() == (late + timedelta(days=1)).date() and 9 <= due.hour <= 10


def test_b_schedule_keeps_gap():
    st = {"items": {}}
    qq = q(enabled=True)
    for i in range(6):
        AR._add(st, NOW, f"b{i}", layer="B", platform="threads", target_id=str(i), post_id=str(i), author=str(i),
                comment="x", status="pending", reason="")
        AR.apply_drafts(st, qq, {f"b{i}": [GOOD, GOOD2, GOOD + "啊", "半導體庫存去化比預期快，但終端需求還沒跟上，這段落差可能才是接下來的重點",
                                         "降息預期一直被往後推，資金其實有在往防禦型族群挪，這週成交量就看得出來", "高股息這幾年規模變太大，換股時的衝擊成本反而變成新的風險"][i]},
                        NOW, random.Random(i))
    dues = sorted(AR.parse_t(x["due_at"]) for x in st["items"].values() if x["status"] == "drafted")
    assert all(b - a >= timedelta(minutes=25) for a, b in zip(dues, dues[1:]))


# ── 送出 ──
def test_send_dry_run_and_real_with_fake_poster():
    st = _pending()
    AR.apply_drafts(st, q(), {"k1": GOOD}, NOW, random.Random(1))
    later = NOW + timedelta(hours=2)
    r = AR.send(st, q(), {}, later, dry_run=True, checker=lambda it, env: False)
    assert r["dry"] == 1 and st["items"]["k1"]["status"] == "drafted"
    AR.SLEEP = lambda s: None
    r = AR.send(st, q(), {}, later, dry_run=False, poster=lambda it, env: "RID", checker=lambda it, env: False)
    assert r["sent"] == 1 and st["items"]["k1"]["reply_id"] == "RID"
    assert "今天送出的回覆" in AR.report(st, q(), later) and GOOD in AR.report(st, q(), later)


def test_send_blocks_b_when_disabled_and_outside_window():
    st = _pending("B")
    AR.apply_drafts(st, q(enabled=True), {"k1": GOOD}, NOW, random.Random(1))
    r = AR.send(st, q(enabled=False), {}, NOW + timedelta(hours=3), dry_run=False, poster=lambda it, env: 1 / 0)
    assert r["sent"] == 0 and any("B 層關閉" in h for h in r["held"])
    r = AR.send(st, q(enabled=True), {}, datetime(2026, 11, 11, 2, 0, tzinfo=TPE), dry_run=False, poster=lambda it, env: 1 / 0)
    assert r["held"] == ["不在 09:00～23:00"]


def test_send_relints_before_posting():
    st = _pending()
    AR.apply_drafts(st, q(), {"k1": GOOD}, NOW, random.Random(1))
    qq = q()
    qq["blacklist"] = ["權值股"]
    r = AR.send(st, qq, {}, NOW + timedelta(hours=2), dry_run=False, poster=lambda it, env: 1 / 0, checker=lambda it, env: False)
    assert r["sent"] == 0 and st["items"]["k1"]["status"] == "skipped"


def test_send_skips_when_api_says_already_replied():
    st = _pending()
    AR.apply_drafts(st, q(), {"k1": GOOD}, NOW, random.Random(1))
    r = AR.send(st, q(), {}, NOW + timedelta(hours=2), dry_run=False, poster=lambda it, env: 1 / 0, checker=lambda it, env: True)
    assert r["sent"] == 0 and st["items"]["k1"]["status"] == "skipped" and "API" in st["items"]["k1"]["reason"]


def test_send_holds_when_api_check_fails():
    st = _pending()
    AR.apply_drafts(st, q(), {"k1": GOOD}, NOW, random.Random(1))

    def boom(it, env):
        raise RuntimeError("HTTP 500")
    r = AR.send(st, q(), {}, NOW + timedelta(hours=2), dry_run=False, poster=lambda it, env: 1 / 0, checker=boom)
    assert r["sent"] == 0 and st["items"]["k1"]["status"] == "drafted" and "先不送" in r["held"][0]


def test_send_skips_same_target_already_sent_in_queue():
    st = _pending()
    AR.apply_drafts(st, q(), {"k1": GOOD}, NOW, random.Random(1))
    st["items"]["old"] = {"key": "old", "layer": "A", "platform": "threads", "target_id": "R1", "status": "sent",
                          "draft": GOOD2, "created_at": AR.iso(NOW), "sent_at": AR.iso(NOW)}
    r = AR.send(st, q(), {}, NOW + timedelta(hours=2), dry_run=False, poster=lambda it, env: 1 / 0, checker=lambda it, env: False)
    assert r["sent"] == 0 and st["items"]["k1"]["status"] == "skipped"


def test_already_replied_checks_api():
    def th(m, path, tok, params=None):
        if path == "/me":
            return {"id": "U1", "username": "liguligu0818"}
        return {"data": [{"id": "x", "username": "someone"}, {"id": "y", "username": "liguligu0818"}]}
    it = {"platform": "threads", "target_id": "R1"}
    assert AR.already_replied(it, {"THREADS_ACCESS_TOKEN": "t"}, tcall=th) is True
    th2 = lambda m, path, tok, params=None: {"username": "liguligu0818"} if path == "/me" else {"data": [{"username": "a"}]}  # noqa: E731
    assert AR.already_replied({"platform": "ig", "target_id": "C1"}, {"IG_ACCESS_TOKEN": "t"}, icall=th2) is False


def test_prune_drops_text_after_7_days():
    st = _pending()
    AR.prune(st, NOW + timedelta(days=8))
    assert "comment" not in st["items"]["k1"]
    AR.prune(st, NOW + timedelta(days=31))
    assert st["items"] == {}


def test_b_collect_own_only_makes_no_candidates():
    st = {"items": {}}
    rows = [{"id": "1", "text": "x", "username": "liguligu0818", "keyword": "台股"}]
    r = AR.collect_b(st, q(enabled=True), {"THREADS_ACCESS_TOKEN": "x"}, NOW, search=lambda *a, **k: (rows, ""),
                     tcall=fake_threads)
    assert r["permission"] == "own_only" and st["items"] == {}


def test_b_collect_off_by_default():
    r = AR.collect_b({"items": {}}, q(), {"THREADS_ACCESS_TOKEN": "x"}, NOW, search=lambda *a, **k: 1 / 0)
    assert r["permission"] == "off"


def test_shortcode_to_id():
    assert AR.shortcode_to_id("https://www.threads.net/@x/post/B") == "1"
    assert AR.shortcode_to_id("BA") == str(64)


# ── 熱門串採集 ──
def test_search_falls_back_to_basic_fields():
    calls = []

    def call(m, p, t, params):
        calls.append(params["fields"])
        if "like_count" in params["fields"]:
            raise S.SearchError("HTTP 400 bad field")
        return {"data": [{"id": "1", "text": "台股？", "username": "a"}]}
    rows, used = S.search("t", "台股", call=call)
    assert used == S.FIELDS_BASIC and rows[0]["keyword"] == "台股" and len(calls) == 2


def test_stats_and_write(tmp_path):
    rows = [{"id": "1", "text": "台股又崩了？", "timestamp": "2026-11-09T12:00:00+0000", "media_type": "TEXT", "username": "a", "keyword": "台股"},
            {"id": "2", "text": "3 檔高股息 ETF 比一比", "timestamp": "2026-11-09T01:00:00+0000", "media_type": "IMAGE", "username": "a", "keyword": "ETF"},
            {"id": "2", "text": "重複", "username": "a", "keyword": "高股息"}]
    st = S.stats(rows)
    assert st["posts"] == 2 and st["opener"] == {"問句": 1, "數字開頭": 1}
    assert st["hour_taipei"] == {"9": 1, "20": 1} and st["with_media_ratio"] == 0.5
    assert st["unique_accounts"] == 1 and st["account_post_counts"] == [2]
    fs = HC.write(tmp_path, "2026-11-09", st, "approved", {})
    blob = "".join(f.read_text(encoding="utf-8") for f in fs)
    d = json.loads(fs[0].read_text(encoding="utf-8"))
    assert "rows" not in d and sorted(f.name for f in tmp_path.iterdir()) == ["2026-11-09_stats.json", "2026-11-09_stats.md"]
    for raw in ("台股又崩了", "高股息 ETF 比一比", '"a"', "permalink"):        # 不存全文、帳號名、permalink
        assert raw not in blob


def test_permission_state():
    assert S.permission_state([], "me") == "empty"
    assert S.permission_state([{"username": "me"}], "me") == "own_only"
    assert S.permission_state([{"username": "me"}, {"username": "x"}], "me") == "approved"
