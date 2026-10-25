"""IG 排程發文：格式、圖片規則、核准／時間判斷、寫回。不連外（發文函式用假的取代）。"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import ig_post as ip  # noqa: E402

TZ = timezone(timedelta(hours=8))
NOW = datetime(2026, 10, 26, 12, 0, tzinfo=TZ)


def doc(status="approved", at="2026-10-26T11:00+08:00", images="a.jpg", body="說明 #哩股哩股"):
    return f"---\nstatus: {status}\npublish_at: {at}\ntitle: t\nimages: {images}\n---\n{body}\n"


def test_parse_and_validate_ok(tmp_path):
    (tmp_path / "a.jpg").write_bytes(b"x")
    meta, cap = ip.parse(doc())
    assert ip.validate(meta, cap, root=tmp_path) == []


def test_requires_image_and_jpeg_and_count(tmp_path):
    for img in ("", "a.png"):
        meta, cap = ip.parse(doc(images=img))
        assert ip.validate(meta, cap, root=tmp_path, check_files=False)
    many = ", ".join(f"{i}.jpg" for i in range(11))
    meta, cap = ip.parse(doc(images=many))
    assert any("10" in e for e in ip.validate(meta, cap, root=tmp_path, check_files=False))


def test_missing_file_caught(tmp_path):
    meta, cap = ip.parse(doc(images="nope.jpg"))
    assert any("找不到圖片檔" in e for e in ip.validate(meta, cap, root=tmp_path))


def test_caption_limits(tmp_path):
    meta, cap = ip.parse(doc(body="字" * 2201))
    assert any("2200" in e for e in ip.validate(meta, cap, root=tmp_path, check_files=False))
    meta, cap = ip.parse(doc(body=" ".join(f"#t{i}" for i in range(31))))
    assert any("標籤" in e for e in ip.validate(meta, cap, root=tmp_path, check_files=False))
    meta, cap = ip.parse(doc(body="看 {連結}"))
    assert ip.validate(meta, cap, root=tmp_path, check_files=False)


def test_due_requires_approved_and_time():
    assert ip.is_due(ip.parse(doc())[0], NOW)
    assert not ip.is_due(ip.parse(doc(status="draft"))[0], NOW)
    assert not ip.is_due(ip.parse(doc(at="2026-10-26T13:00+08:00"))[0], NOW)


def test_draft_never_posts(tmp_path, monkeypatch):
    (tmp_path / "a.jpg").write_bytes(b"x")
    f = tmp_path / "d.md"
    f.write_text(doc(status="draft"), encoding="utf-8")
    monkeypatch.setattr(ip, "ROOT", tmp_path)
    monkeypatch.setattr(ip, "publish", lambda *a: (_ for _ in ()).throw(AssertionError("draft 不該發")))
    meta, cap = ip.parse(f.read_text(encoding="utf-8"))
    assert ip.validate(meta, cap, root=tmp_path) == []


def test_failure_marks_error_and_hides_token(tmp_path, monkeypatch, capsys):
    (tmp_path / "a.jpg").write_bytes(b"x")
    q = tmp_path / "q"
    q.mkdir()
    f = q / "e.md"
    f.write_text(doc(), encoding="utf-8")
    monkeypatch.setattr(ip, "ROOT", tmp_path)
    monkeypatch.setattr(ip, "publish", lambda *a: (_ for _ in ()).throw(ip.PostError("HTTP 400 test")))
    monkeypatch.setenv("IG_ACCESS_TOKEN", "secret-token-xyz")
    rc = ip.main(["--queue", str(q), "--now", "--file", "e.md"])
    assert rc == 1
    meta, _ = ip.parse(f.read_text(encoding="utf-8"))
    assert meta["status"] == "error"
    out = capsys.readouterr()
    assert "secret-token-xyz" not in out.out + out.err + f.read_text(encoding="utf-8")


def test_success_rewrites_and_no_repeat(tmp_path, monkeypatch):
    (tmp_path / "a.jpg").write_bytes(b"x")
    f = tmp_path / "ok.md"
    f.write_text(doc(), encoding="utf-8")
    monkeypatch.setattr(ip, "ROOT", tmp_path)
    monkeypatch.setattr(ip, "publish", lambda *a: {"id": "1", "permalink": "https://instagram.com/p/x"})
    assert ip.process(f, NOW, "tok") == "已發出"
    meta, _ = ip.parse(f.read_text(encoding="utf-8"))
    assert meta["status"] == "posted" and "instagram.com/p/x" in meta["urls"]
    monkeypatch.setattr(ip, "publish", lambda *a: (_ for _ in ()).throw(AssertionError("不該再發")))
    assert "略過" in ip.process(f, NOW, "tok")


def test_public_url_encoding():
    assert ip.public_url("social/ig/images/a b.jpg").endswith("social/ig/images/a%20b.jpg")


def test_repo_queue_valid():
    for f in sorted(ip.QUEUE.glob("*.md")):
        meta, cap = ip.parse(f.read_text(encoding="utf-8"))
        errs = ip.validate(meta, cap)
        if meta["status"] == "approved":
            assert errs == [], (f.name, errs)
