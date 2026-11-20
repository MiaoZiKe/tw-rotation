"""頻道①短影片（2026-11-16 Andy：「我沒有看到LIGULIGU IG Thread 有影片 需要發布」）：
threads_post／ig_post 佇列檔支援 video:（Threads VIDEO、IG REELS）、first_comment:（網址放第一則留言）、
影片檔失敗自動重試（attempts）。不連外：_call 一律用假的。"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import ig_post as ip  # noqa: E402
import threads_post as tp  # noqa: E402

TZ = timezone(timedelta(hours=8))
NOW = datetime(2026, 11, 17, 12, 20, tzinfo=TZ)
VID = "site/media/ligu/20261116v_nvda_kress/video.mp4"


def doc(extra=""):
    return ("---\nstatus: approved\npublish_at: 2026-11-17T12:15+08:00\ntitle: t\nformat: threads_v2\n"
            f"video: {VID}\nfirst_comment: 來源：https://liguligu-puipui.com/?u=th-vd-20261117#article/x\n{extra}---\n主文\n")


def fake_threads(calls, fail_site=False):
    def fake(method, path, token, params=None):
        params = dict(params or {})
        calls.append((method, path, params))
        if path == "/me":
            return {"id": "u"}
        if path == "/u/threads":
            if fail_site and params.get("video_url", "").startswith(tp.SITE):
                raise tp.PostError("HTTP 400 site")
            return {"id": f"c{len(calls)}"}
        if path.endswith("/threads_publish"):
            return {"id": f"m{len(calls)}"}
        if method == "GET" and params.get("fields") == "status,error_message":
            return {"status": "FINISHED"}
        return {"permalink": f"https://www.threads.com/@liguligu0818/post/{path.strip('/')}"}
    return fake


def test_threads_影片貼文_第一則留言(tmp_path, monkeypatch):
    f = tmp_path / "a.md"
    f.write_text(doc(), encoding="utf-8")
    calls = []
    monkeypatch.setattr(tp, "_call", fake_threads(calls))
    monkeypatch.setattr(tp.time, "sleep", lambda s: None)
    assert "第一則留言" in tp.process(f, NOW, "tok")
    made = [p for m, path, p in calls if path == "/u/threads"]
    assert made[0]["media_type"] == "VIDEO" and made[0]["video_url"] == tp.SITE + "media/ligu/20261116v_nvda_kress/video.mp4"
    assert made[1]["media_type"] == "TEXT" and made[1]["reply_to_id"] and "liguligu-puipui.com" in made[1]["text"]
    meta, _ = tp.parse(f.read_text(encoding="utf-8"))
    assert meta["status"] == "posted" and meta["urls"].startswith("https://www.threads.com/") and meta["comment_url"]


def test_threads_正式站失敗改用raw(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(tp, "_call", fake_threads(calls, fail_site=True))
    monkeypatch.setattr(tp.time, "sleep", lambda s: None)
    tp.publish_chain(["主文"], "tok", [], video=tp.video_urls({"video": VID}))
    vids = [p["video_url"] for m, path, p in calls if path == "/u/threads"]
    assert vids[0].startswith(tp.SITE) and vids[1].startswith(tp.RAW)


def test_threads_影片失敗先重試再標error(tmp_path, monkeypatch):
    f = tmp_path / "a.md"
    f.write_text(doc(), encoding="utf-8")
    monkeypatch.setattr(tp, "publish_chain", lambda *a, **k: (_ for _ in ()).throw(tp.PostError("HTTP 500 x")))
    for n in range(1, tp.VIDEO_ATTEMPTS + 1):
        assert tp.main(["--queue", str(tmp_path), "--now"]) == 1
        meta, _ = tp.parse(f.read_text(encoding="utf-8"))
        assert meta["attempts"] == str(n)
        assert meta["status"] == ("error" if n == tp.VIDEO_ATTEMPTS else "approved")


def test_ig_reels_正式站優先_封面_第一則留言(tmp_path, monkeypatch):
    f = tmp_path / "a.md"
    f.write_text(doc("cover: site/media/ligu/20261116v_nvda_kress/cover.jpg\n").replace("th-vd", "ig-vd"), encoding="utf-8")
    calls = []

    def fake(method, path, token, params=None):
        params = dict(params or {})
        calls.append((method, path, params))
        if path == "/me":
            return {"user_id": "u"}
        if path == "/u/media":
            return {"id": "c1"}
        if path == "/c1":
            return {"status_code": "FINISHED"}
        if path == "/u/media_publish":
            return {"id": "m1"}
        if path == "/m1/comments":
            return {"id": "k1"}
        return {"permalink": "https://www.instagram.com/reel/abc/"}
    monkeypatch.setattr(ip, "_call", fake)
    monkeypatch.setattr(ip, "check_public", lambda u: None)
    assert "第一則留言" in ip.process(f, NOW, "tok")
    media = [p for m, path, p in calls if path == "/u/media"][0]
    assert media["media_type"] == "REELS" and media["video_url"].startswith(ip.SITE) and media["cover_url"].endswith("cover.jpg")
    assert media["share_to_feed"] == "false"  # 2026-11-20 Andy：Reels 只進 Reels 分頁
    assert "ig-vd-20261117" in [p for m, path, p in calls if path == "/m1/comments"][0]["message"]
    meta, _ = ip.parse(f.read_text(encoding="utf-8"))
    assert meta["status"] == "posted" and meta["urls"] == "https://www.instagram.com/reel/abc/" and meta["comment_id"] == "k1"


def test_ig_留言失敗不擋主文(tmp_path, monkeypatch):
    def fake(method, path, token, params=None):
        raise ip.PostError("HTTP 403 (#10) no permission")
    monkeypatch.setattr(ip, "_call", fake)
    out = ip.first_comment({"first_comment": "x"}, {"id": "m1"}, "tok")
    assert "comment_error" in out


def test_repo_頻道一影片佇列檔():
    for q, mod in ((ROOT / "social" / "threads" / "queue", tp), (ROOT / "social" / "ig" / "queue", ip)):
        for f in sorted(q.glob("*_ligu-*.md")):
            text = f.read_text(encoding="utf-8")
            meta, body = mod.parse(text)
            assert meta.get("hook_type"), f.name
            assert "查證截至" in (body if isinstance(body, str) else "\n".join(body)), f.name
            assert "liguligu-puipui.com" not in (body if isinstance(body, str) else "\n".join(body)), f"{f.name} 網址只能放第一則留言"
            assert ("?u=th-vd-" if mod is tp else "?u=ig-vd-") in meta["first_comment"], f.name
            assert (ROOT / meta["video"]).is_file(), f.name
            assert meta["publish_at"].endswith("T12:15+08:00"), f"{f.name} 照午休時段 12:15 發"
