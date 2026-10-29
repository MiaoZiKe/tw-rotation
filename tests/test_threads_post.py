"""Threads 排程發文：格式、字數、核准／時間判斷、串文寫回。不連外（發文函式用假的取代）。"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import threads_post as tp  # noqa: E402

TZ = timezone(timedelta(hours=8))
NOW = datetime(2026, 10, 26, 12, 0, tzinfo=TZ)


def doc(status="approved", at="2026-10-26T11:00+08:00", body="第一則\n-----\n第二則"):
    return f"---\nstatus: {status}\npublish_at: {at}\ntitle: t\n---\n{body}\n"


def test_parse_thread_split():
    meta, posts = tp.parse(doc())
    assert meta["status"] == "approved" and posts == ["第一則", "第二則"]


def test_validate_ok_and_errors():
    assert tp.validate(*tp.parse(doc())) == []
    assert tp.validate(*tp.parse(doc(status="oops")))
    assert tp.validate(*tp.parse(doc(at="昨天")))
    assert tp.validate(*tp.parse(doc(body="x" * 501)))
    assert tp.validate(*tp.parse(doc(body="看這裡 {連結}")))


def test_missing_header_raises():
    try:
        tp.parse("沒有檔頭")
    except tp.PostError:
        return
    raise AssertionError("應該丟 PostError")


def test_due_requires_approved_and_time():
    assert tp.is_due(tp.parse(doc())[0], NOW)
    assert not tp.is_due(tp.parse(doc(status="draft"))[0], NOW)
    assert not tp.is_due(tp.parse(doc(at="2026-10-26T13:00+08:00"))[0], NOW)
    assert not tp.is_due(tp.parse(doc(status="posted"))[0], NOW)


def test_process_posts_and_rewrites(tmp_path, monkeypatch):
    f = tmp_path / "a.md"
    f.write_text(doc(), encoding="utf-8")
    monkeypatch.setattr(tp, "publish_chain", lambda posts, token, images=None: [{"id": "1", "permalink": "https://threads/x"}, {"id": "2", "permalink": ""}])
    assert "已發出 2 則" in tp.process(f, NOW, "tok")
    meta, _ = tp.parse(f.read_text(encoding="utf-8"))
    assert meta["status"] == "posted" and "https://threads/x" in meta["urls"]
    # 再跑一次不會重複發
    monkeypatch.setattr(tp, "publish_chain", lambda *a: (_ for _ in ()).throw(AssertionError("不該再發")))
    assert "略過" in tp.process(f, NOW, "tok")


def test_draft_never_posts(tmp_path, monkeypatch):
    f = tmp_path / "d.md"
    f.write_text(doc(status="draft"), encoding="utf-8")
    monkeypatch.setattr(tp, "publish_chain", lambda *a: (_ for _ in ()).throw(AssertionError("draft 不該發")))
    assert "略過" in tp.process(f, NOW, "tok")


def test_failure_marks_error_no_retry(tmp_path, monkeypatch, capsys):
    f = tmp_path / "e.md"
    f.write_text(doc(), encoding="utf-8")

    def boom(*a):
        raise tp.PostError("HTTP 400 test")
    monkeypatch.setattr(tp, "publish_chain", boom)
    monkeypatch.setenv("THREADS_ACCESS_TOKEN", "secret-token-xyz")
    rc = tp.main(["--queue", str(tmp_path), "--now"])
    assert rc == 1
    meta, _ = tp.parse(f.read_text(encoding="utf-8"))
    assert meta["status"] == "error"
    out = capsys.readouterr()
    assert "secret-token-xyz" not in out.out + out.err + f.read_text(encoding="utf-8")


def test_repo_queue_files_valid():
    for f in sorted(tp.QUEUE.glob("*.md")):
        meta, posts = tp.parse(f.read_text(encoding="utf-8"))
        errs = tp.validate(meta, posts)
        # 草稿允許還有佔位符以外的問題；已核准者必須完全通過
        if meta["status"] == "approved":
            assert errs == [], (f.name, errs)
        assert meta["status"] != "posted" or meta.get("urls")


def test_emoji_counts_as_utf8_bytes():
    assert tp._tlen("🐹") == 4
    assert tp._tlen("abc") == 3
    assert tp._tlen("📊") > 1
    # 499 個字 + 1 個 emoji（4 位元組）→ 超過 500，必須被擋
    assert tp.validate(*tp.parse(doc(body="字" * 499 + "🐹")))


def test_repo_drafts_within_limit_by_bytes():
    for f in sorted(tp.QUEUE.glob("*.md")):
        meta, posts = tp.parse(f.read_text(encoding="utf-8"))
        assert all(tp._tlen(p) <= tp.MAX_LEN for p in posts), f.name


def test_images_of_封面圖帶進第一則():
    # 2026-10-29 Andy：「為何沒有貼文?」—— 主題文章 Threads 要帶封面圖
    import scripts.threads_post as tp
    assert tp.images_of({"images": "social/ig/images/news/a.jpg"}) == ["social/ig/images/news/a.jpg"]
    assert tp.images_of({"images": "a.jpg, b.jpg"}) == ["a.jpg", "b.jpg"]
    assert tp.images_of({}) == []


def test_publish_chain_第一則用圖片(monkeypatch):
    import scripts.threads_post as tp
    calls = []
    def fake(method, path, token, params=None):
        calls.append((path, dict(params or {})))
        if path == "/me":
            return {"id": "u"}
        if path.endswith("/threads"):
            return {"id": f"c{len(calls)}"}
        if path.endswith("/threads_publish"):
            return {"id": f"m{len(calls)}"}
        return {"permalink": "https://x"}
    monkeypatch.setattr(tp, "_call", fake)
    monkeypatch.setattr(tp.time, "sleep", lambda s: None)
    tp.publish_chain(["一", "二"], "tok", ["social/a.jpg"])
    made = [p for path, p in calls if path == "/u/threads"]
    assert made[0]["media_type"] == "IMAGE" and made[0]["image_url"].endswith("social/a.jpg")
    assert made[1]["media_type"] == "TEXT" and made[1]["reply_to_id"]


def test_封面圖失敗改發純文字(monkeypatch):
    import scripts.threads_post as tp
    made = []
    def fake(method, path, token, params=None):
        if path == "/me":
            return {"id": "u"}
        if path.endswith("/threads"):
            if params.get("media_type") == "IMAGE":
                raise tp.PostError("HTTP 400 image")
            made.append(params)
            return {"id": "c"}
        if path.endswith("/threads_publish"):
            return {"id": "m"}
        return {"permalink": ""}
    monkeypatch.setattr(tp, "_call", fake)
    monkeypatch.setattr(tp.time, "sleep", lambda s: None)
    tp.publish_chain(["一"], "tok", ["a.jpg"])
    assert made[0]["media_type"] == "TEXT"
