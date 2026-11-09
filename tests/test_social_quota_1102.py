"""2026-11-02 降量模式（Andy：「同意降量」）：docs/marketing/social_unit/post_quota.json 是唯一開關。

守的事：
  · 真的開關檔＝降量規格（只留盤後主貼文 Threads；盤前／盤中／IG 限動／主題文章全關；手寫照發）。
  · 關掉的 premarket／intraday／限動／主題文章：一個發布請求都不送、以成功結束、不寫發布紀錄。
  · close 的 Threads 照發（保留的那一則一定要發出），限動不發。
  · 排程：盤中、盤前備援、主題文章、IG 晚間、晚間監工的 cron 都拿掉；資料管線 daily.yml 的 cron 沒動。
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import ig_news_check  # noqa: E402
import ig_post as ip  # noqa: E402
import post_quota  # noqa: E402
import social_news  # noqa: E402
import threads_post as tp  # noqa: E402

from scripts import social_publish as sp  # noqa: E402

REAL = ROOT / "docs" / "marketing" / "social_unit" / "post_quota.json"
TZ = timezone(timedelta(hours=8))
NOW = datetime(2026, 11, 2, 21, 0, tzinfo=TZ)
ENV = {"THREADS_USER_ID": "11", "THREADS_ACCESS_TOKEN": "T_TOKEN_x", "IG_USER_ID": "22", "IG_ACCESS_TOKEN": "I_TOKEN_y"}


@pytest.fixture(autouse=True)
def _真開關檔(monkeypatch, tmp_path_factory):
    """這支測試一律用 repo 裡真的開關檔（conftest 預設是全開的暫存檔）。"""
    monkeypatch.setenv("POST_QUOTA_FILE", str(REAL))
    monkeypatch.setattr(sp, "_sleep", lambda s: None)
    on = tmp_path_factory.mktemp("flag") / "LIVE_ENABLED"
    on.write_text("", encoding="utf-8")
    monkeypatch.setattr(sp, "LIVE_FLAG", on)
    sp._SECRETS.clear()


class Fake:
    def __init__(self):
        self.calls, self.n = [], 0

    def __call__(self, method, url, **kw):
        self.calls.append((method, url, kw))
        if "refresh_access_token" in url:
            return {"access_token": kw["params"]["access_token"], "expires_in": 5183944}
        if method == "GET":
            f = kw["params"]["fields"]
            return {"permalink": "https://www.threads.com/@x/post/" + url.rsplit("/", 1)[1]} if f == "permalink" else {f: "FINISHED"}
        self.n += 1
        return {"id": f"id{self.n}"}


def manifest(tmp_path, kind, t="2026-11-02T08:20:00+08:00", **extra):
    p = tmp_path / "manifest.json"
    th = {"text": f"{kind} 主文", "images": ["a.png", "b.png"], **extra}
    p.write_text(json.dumps({"kind": kind, "taken_at": t, "data_date": t[:10], "threads": th,
                             "story": ["s1.png", "s2.png"]}), encoding="utf-8")
    return p


def test_真開關檔就是降量規格():
    q = json.loads(REAL.read_text(encoding="utf-8"))
    assert "同意降量" in q["note"]
    assert q["live"]["close"] == {"threads": True, "ig_story": False}
    for k in ("premarket", "intraday", "credit"):
        assert q["live"][k] == {"threads": False, "ig_story": False}, k
    assert q["queue"]["news"] == {"threads": False, "ig": False}
    assert q["queue"]["manual"] == {"threads": True, "ig": True}
    assert post_quota.any_on("close") and not post_quota.any_on("premarket") and not post_quota.any_on("news")


def test_開關檔壞掉或不見就用內建降量規格(tmp_path, monkeypatch):
    monkeypatch.setenv("POST_QUOTA_FILE", str(tmp_path / "nope.json"))
    assert post_quota.live_allowed("close", "threads") and not post_quota.live_allowed("close", "ig_story")
    assert not post_quota.live_allowed("premarket", "threads") and not post_quota.queue_allowed("ig", "2026-11-02_news-pre-1.md")
    bad = tmp_path / "bad.json"
    bad.write_text("{壞掉", encoding="utf-8")
    monkeypatch.setenv("POST_QUOTA_FILE", str(bad))
    assert post_quota.live_allowed("close", "threads") and not post_quota.live_allowed("intraday", "threads")
    assert not post_quota.live_allowed("沒寫到的kind", "threads")      # 沒寫到的一律關


def test_佇列檔分類():
    for n in ("2026-11-02_news-pre-1.md", "2026-10-31_news-wk2-1.md", "2026-11-02_news-fb-1"):
        assert post_quota.is_auto_news(n), n
    for n in ("2026-10-29_salary.md", "2026-10-30_urgent-selloff.md", "2026-11-02_pre.md", "news.md"):
        assert not post_quota.is_auto_news(n), n


@pytest.mark.parametrize("kind", ["premarket", "intraday", "credit"])
def test_盤前盤中融資_一個請求都不送(tmp_path, monkeypatch, kind, capsys):
    f = Fake(); monkeypatch.setattr(sp, "http", f)
    assert sp.run(manifest(tmp_path, kind, thread_posts=["串1"], reply_post="連結"), "https://x.test/b", env=ENV) == 0
    assert f.calls == []      # 連查帳號、延長權杖都沒有
    assert not (tmp_path / "posted.json").exists()
    out = capsys.readouterr().out
    assert "降量模式：略過" in out and f"live.{kind}.threads=false" in out and f"live.{kind}.ig_story=false" in out


def test_盤後主貼文_Threads_照發_限動不發(tmp_path, monkeypatch, capsys):
    f = Fake(); monkeypatch.setattr(sp, "http", f)
    m = manifest(tmp_path, "close", t="2026-11-02T17:35:00+08:00", thread_posts=["串1"], reply_post="網站連結")
    assert sp.run(m, "https://x.test/b", env=ENV) == 0
    posts = [c for c in f.calls if c[0] == "POST"]
    assert posts and all("graph.threads.net" in c[1] for c in posts)
    assert not [c for c in f.calls if "/media" in c[1] or "graph.instagram.com" in c[1]]      # IG 限動一個請求都沒有
    assert len([c for c in posts if c[1].endswith("/threads_publish")]) == 3      # 主文＋串文＋留言連結
    rec = json.loads((tmp_path / "posted.json").read_text(encoding="utf-8"))["close-2026-11-02"]
    assert rec["threads"]["link"].startswith("https://www.threads.com/") and "story" not in rec
    assert "live.close.ig_story=false" in capsys.readouterr().out


def test_盤後法人補充貼文_降量模式不發(tmp_path, monkeypatch, capsys):
    """2026-11-09 事故：11-06 降量模式下多發一則 close-inst-2026-11-06（20:27）。
    補充貼文是另一則貼文，查 live.close_inst（真開關檔沒寫＝關），不吃 close 的開關；一個請求都不送、不寫發布紀錄。"""
    f = Fake(); monkeypatch.setattr(sp, "http", f)
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({"kind": "close", "supplement": True, "taken_at": "2026-11-06T20:26:46+08:00",
                             "data_date": "2026-11-06", "threads": {"text": "法人補充", "images": ["a.png"]}, "story": ["s.png"]}),
                 encoding="utf-8")
    assert sp.run(p, "https://x.test/b", env=ENV) == 0
    assert f.calls == []
    assert not (tmp_path / "posted.json").exists()
    assert "live.close_inst.threads=false" in capsys.readouterr().out


def test_close_inst_開關():
    assert post_quota.live_kind({"kind": "close", "supplement": True}) == "close_inst"
    assert post_quota.live_kind({"kind": "close"}) == "close"
    assert post_quota.live_kind({}) == "intraday"
    q = json.loads(REAL.read_text(encoding="utf-8"))
    assert not post_quota.any_on("close_inst", q) and post_quota.any_on("close", q)
    assert post_quota.any_on("close_inst", {"live": {"close_inst": {"threads": True}}, "queue": {}})      # Andy 說要放量才加這一格


def test_盤後發布狀態_降量模式不進補充輪(capsys):
    """11-06 的實際紀錄：主貼文 partial=retail-ratio → 不該補充；就算拿掉的是法人卡，降量模式也不補發。"""
    import social_close_state as cs
    D = "2026-11-06"
    real = post_quota.load()
    retail_only = {f"close-{D}": {"threads": {"id": "1"}, "partial": ["retail-ratio"]}}
    assert cs.state(retail_only, D, q=real) == "skip"
    on = {"live": {"close_inst": {"threads": True}}, "queue": {}}
    assert cs.state(retail_only, D, q=on) == "skip"      # 法人三張已在主貼文裡，補充＝重發
    inst = {f"close-{D}": {"threads": {"id": "1"}, "partial": ["inst-today", "streak-foreign"]}}
    assert cs.state(inst, D, q=real) == "skip"
    assert "live.close_inst 關" in capsys.readouterr().err
    assert cs.state(inst, D, q=on) == "supplement"
    assert cs.state({}, D, q=real) == ""


def _q(tmp_path, name, body, images=""):
    q = tmp_path / "q"
    q.mkdir(exist_ok=True)
    img = f"images: {images}\n" if images else ""
    (q / name).write_text(f"---\nstatus: approved\npublish_at: 2026-11-01T20:00+08:00\ntitle: t\n{img}---\n{body}\n", encoding="utf-8")
    return q


def test_Threads_主題文章不送請求_改回草稿_手寫照發(tmp_path, monkeypatch, capsys):
    sent = []
    monkeypatch.setattr(tp, "publish_chain", lambda posts, token, images=None: sent.append(posts) or [{"id": "1", "permalink": "https://threads/x"}])
    monkeypatch.setattr(tp, "_call", lambda *a, **k: (_ for _ in ()).throw(AssertionError("不該連 Threads API")))
    monkeypatch.setenv("THREADS_ACCESS_TOKEN", "tok")
    monkeypatch.setenv("THREADS_V2_LEGACY", "0")
    q = _q(tmp_path, "2026-11-02_news-pre-1.md", "主題文章")
    _q(tmp_path, "2026-11-02_salary.md", "手寫")
    assert tp.main(["--queue", str(q)]) == 0
    assert sent == [["手寫"]]      # 只有手寫那篇送出
    news = tp.parse((q / "2026-11-02_news-pre-1.md").read_text(encoding="utf-8"))[0]
    assert news["status"] == "draft" and "queue.news.threads=false" in news["quota_skipped"]
    assert tp.parse((q / "2026-11-02_salary.md").read_text(encoding="utf-8"))[0]["status"] == "posted"
    assert "降量模式：略過" in capsys.readouterr().out
    assert tp.main(["--check", "--queue", str(q)]) == 0      # 改回草稿後格式仍然合法


def test_IG_主題文章不送請求_改回草稿_手寫照發(tmp_path, monkeypatch, capsys):
    sent = []
    monkeypatch.setattr(ip, "publish", lambda imgs, cap, token: sent.append(cap) or {"permalink": "https://www.instagram.com/p/x/"})
    monkeypatch.setattr(ip, "_call", lambda *a, **k: (_ for _ in ()).throw(AssertionError("不該連 IG API")))
    monkeypatch.setattr(ip, "validate", lambda *a, **k: [])
    q = _q(tmp_path, "2026-11-02_news-intra-1.md", "IG 主題文章", images="a.jpg")
    _q(tmp_path, "2026-10-29_salary.md", "IG 手寫", images="b.jpg")
    for f in sorted(q.glob("*.md")):
        ip.process(f, NOW, "tok")
    assert sent == ["IG 手寫"]
    news = ip.parse((q / "2026-11-02_news-intra-1.md").read_text(encoding="utf-8"))[0]
    assert news["status"] == "draft" and "queue.news.ig=false" in news["quota_skipped"]


def test_主題文章排稿_降量就不產稿(monkeypatch, capsys):
    monkeypatch.setattr(social_news, "run_slot", lambda *a, **k: (_ for _ in ()).throw(AssertionError("不該產稿")))
    assert social_news.main(["--slot", "auto", "--now", "2026-11-02T18:25+08:00", "--posted", "/nonexistent.json"]) == 0
    assert social_news.main(["--slot", "wk1", "--now", "2026-11-01T10:15+08:00"]) == 0
    assert "降量模式：略過" in capsys.readouterr().out


def test_IG_晚間監工_降量就成功結束不補發(monkeypatch, capsys):
    monkeypatch.setattr(ig_news_check, "check", lambda *a, **k: (_ for _ in ()).throw(AssertionError("不該檢查")))
    assert ig_news_check.main([]) == 0
    assert "降量模式：略過" in capsys.readouterr().out


def _crons(name):
    wf = yaml.safe_load((ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8"))
    on = wf.get("on") or wf.get(True)
    return [c["cron"] for c in (on.get("schedule") or [])]


def test_排程_停掉的拿掉_資料管線沒動():
    assert _crons("social-live.yml") == []      # 盤中 12:01、盤前 08:20／08:50／09:40
    assert _crons("social_news.yml") == []
    assert _crons("ig_news_watch.yml") == []
    assert _crons("threads_post.yml") == ["*/15 * * * *"]      # 只留給手寫貼文
    assert _crons("ig_post.yml") == ["*/15 * * * *"]
    assert len(_crons("daily.yml")) >= 3      # 資料管線排程一條都沒拿
    wf = yaml.safe_load((ROOT / ".github/workflows/social_news.yml").read_text(encoding="utf-8"))
    assert wf["jobs"]["news"]["needs"] == "gate"
