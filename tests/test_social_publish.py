"""社群自動發布（scripts/social_publish.py）：mock HTTP，驗流程、dry-run、防重複、權杖不外洩。"""
import json

import pytest

from scripts import social_publish as sp

TOK_T, TOK_I = "THREADS_SECRET_TOKEN_123", "IG_SECRET_TOKEN_456"
ENV = {"THREADS_USER_ID": "11", "THREADS_ACCESS_TOKEN": TOK_T, "IG_USER_ID": "22", "IG_ACCESS_TOKEN": TOK_I}
BASE = "https://x.test/snaps/2026-10-20"


@pytest.fixture(autouse=True)
def _fast(monkeypatch, tmp_path_factory):
    monkeypatch.setattr(sp, "_sleep", lambda s: None)
    sp._SECRETS.clear()
    # 既有測試驗「真的發」的流程 → 預設把總開關指到一個存在的暫存檔；總開關關閉的情況在下面另外測
    on = tmp_path_factory.mktemp("flag") / "LIVE_ENABLED"
    on.write_text("", encoding="utf-8")
    monkeypatch.setattr(sp, "LIVE_FLAG", on)


def mk(tmp_path, images=("a.png",), story=("s1.png", "s2.png"), kind="intraday", t="2026-10-20T10:35:00+08:00"):
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({"kind": kind, "taken_at": t, "threads": {"text": "盤中即時", "images": list(images)},
                             "story": list(story)}), encoding="utf-8")
    return p


class Fake:
    def __init__(self, fail_first_create=False):
        self.calls, self.n, self.fail = [], 0, fail_first_create

    def __call__(self, method, url, **kw):
        self.calls.append((method, url, kw))
        if "refresh_access_token" in url:
            return {"access_token": kw["params"]["access_token"], "expires_in": 5183944}
        if method == "GET":
            f = kw["params"]["fields"]
            if f == "permalink":
                return {"permalink": "https://link/" + url.rsplit("/", 1)[1]}
            return {f: "FINISHED"}
        if self.fail and url.endswith(("/threads", "/media")):
            self.fail = False
            raise RuntimeError("HTTP 500 暫時錯誤")
        self.n += 1
        return {"id": f"id{self.n}"}


def posts(fake, suffix):
    return [c for c in fake.calls if c[0] == "POST" and c[1].endswith(suffix)]


def test_單圖走_IMAGE_限動逐張(tmp_path, monkeypatch):
    f = Fake(); monkeypatch.setattr(sp, "http", f)
    assert sp.run(mk(tmp_path), BASE, env=ENV) == 0
    c = posts(f, "/11/threads")
    assert len(c) == 1 and c[0][2]["data"]["media_type"] == "IMAGE"
    assert c[0][2]["data"]["image_url"] == BASE + "/a.png"
    assert len(posts(f, "/11/threads_publish")) == 1
    assert [x[2]["data"]["media_type"] for x in posts(f, "/22/media")] == ["STORIES", "STORIES"]
    assert len(posts(f, "/22/media_publish")) == 2


def test_多圖走_carousel(tmp_path, monkeypatch):
    f = Fake(); monkeypatch.setattr(sp, "http", f)
    sp.run(mk(tmp_path, images=("a.png", "b.png", "c.png"), story=()), BASE, env=ENV)
    c = posts(f, "/11/threads")
    assert [x[2]["data"]["media_type"] for x in c] == ["IMAGE", "IMAGE", "IMAGE", "CAROUSEL"]
    assert c[-1][2]["data"]["children"].count(",") == 2


def test_缺金鑰只_dry_run_不報錯不呼叫API(tmp_path, monkeypatch, capsys):
    f = Fake(); monkeypatch.setattr(sp, "http", f)
    assert sp.run(mk(tmp_path), BASE, env={}) == 0
    assert f.calls == []
    out = capsys.readouterr().out
    assert "dry-run" in out and BASE + "/a.png" in out
    assert not (tmp_path / "posted.json").exists()


def test_dry_run_旗標即使有金鑰也不發(tmp_path, monkeypatch):
    f = Fake(); monkeypatch.setattr(sp, "http", f)
    sp.run(mk(tmp_path), BASE, dry_run=True, env=ENV)
    assert f.calls == []


def test_同時段不重複發(tmp_path, monkeypatch):
    f = Fake(); monkeypatch.setattr(sp, "http", f)
    m = mk(tmp_path)
    sp.run(m, BASE, env=ENV)
    n = len(f.calls)
    sp.run(m, BASE, env=ENV)
    assert len(f.calls) == n  # 第二次完全沒打 API
    assert "intraday-2026-10-20" in json.loads((tmp_path / "posted.json").read_text())


def test_盤中一天一個鍵_Worker與GitHub備援不重複發():
    k = lambda hhmm, d="26": sp.slot_key({"kind": "intraday", "taken_at": f"2026-10-{d}T{hhmm}:00+08:00"})
    assert k("12:00") == k("12:01") == k("12:30") == "intraday-2026-10-26"      # 備援晚到也是同一鍵
    assert k("12:00") != k("12:00", "27")
    assert sp.slot_key({"kind": "close", "taken_at": "2026-10-20T14:30:00+08:00"}) == "close-2026-10-20"


def test_盤中同一時段跨整點仍同一鍵_Worker與GitHub備援不重複發():
    from scripts import social_snap as ss
    for hhmm in ("12:00", "12:01", "12:30"):
        assert ss.slot_key_for("intraday", "2026-10-26", f"2026-10-26T{hhmm}:00+08:00") == "intraday-2026-10-26"


def test_盤後融資以資料日為鍵_跟盤後法人分開():
    # 融資常到隔天清晨才齊：10/21 的融資在 10/22 05:10 發，鍵要是 10/21，而且不能跟 close-10-21 撞在一起
    m = {"kind": "credit", "taken_at": "2026-10-22T05:10:00+08:00", "data_date": "2026-10-21"}
    assert sp.slot_key(m) == "credit-2026-10-21"
    assert sp.slot_key({"kind": "close", "taken_at": "2026-10-22T05:10:00+08:00", "data_date": "2026-10-21"}) == "close-2026-10-21"   # 合併後以資料日為鍵
    from scripts import social_snap as ss
    assert ss.slot_key_for("credit", "2026-10-21", m["taken_at"]) == sp.slot_key(m)
    assert ss.slot_key_for("close", "2026-10-21", "2026-10-21T17:20:00+08:00") == "close-2026-10-21"
    assert ss.slot_key_for("intraday", "2026-10-21", "2026-10-21T11:05:00+08:00") == \
        sp.slot_key({"kind": "intraday", "taken_at": "2026-10-21T11:05:00+08:00"})


def test_失敗重試一次後成功(tmp_path, monkeypatch):
    f = Fake(fail_first_create=True); monkeypatch.setattr(sp, "http", f)
    assert sp.run(mk(tmp_path, story=()), BASE, env=ENV) == 0
    assert len(posts(f, "/11/threads_publish")) == 1


def test_連續失敗回傳1且不記為已發(tmp_path, monkeypatch, capsys):
    def boom(method, url, **kw):
        if "refresh" in url:
            return {"access_token": kw["params"]["access_token"], "expires_in": 1}
        raise RuntimeError(sp.redact("HTTP 400 token=" + TOK_T))
    monkeypatch.setattr(sp, "http", boom)
    assert sp.run(mk(tmp_path, story=()), BASE, env=ENV) == 1
    assert TOK_T not in capsys.readouterr().out
    assert not (tmp_path / "posted.json").exists()


def test_權杖不出現在輸出(tmp_path, monkeypatch, capsys):
    f = Fake(); monkeypatch.setattr(sp, "http", f)
    sp.run(mk(tmp_path), BASE, env=ENV)
    out = capsys.readouterr().out
    assert TOK_T not in out and TOK_I not in out
    assert TOK_T not in (tmp_path / "posted.json").read_text()


def test_延長後換新字串會遮蔽且提醒(monkeypatch, capsys):
    monkeypatch.setattr(sp, "http", lambda *a, **k: {"access_token": "NEWTOKEN999", "expires_in": 5183944})
    assert sp.refresh_token("threads", "OLD") == "NEWTOKEN999"
    out = capsys.readouterr().out
    assert "::add-mask::NEWTOKEN999" in out and "人工更新" in out
    assert "NEWTOKEN999" not in out.replace("::add-mask::NEWTOKEN999", "")


def test_延長失敗不中斷(monkeypatch):
    def boom(*a, **k): raise RuntimeError("x")
    monkeypatch.setattr(sp, "http", boom)
    assert sp.refresh_token("ig", "T") == "T"


def test_中途失敗重跑只補沒發的限動(tmp_path, monkeypatch):
    f = Fake(); monkeypatch.setattr(sp, "http", f)
    m = mk(tmp_path, images=())
    (tmp_path / "posted.json").write_text(json.dumps(
        {"intraday-2026-10-20": {"story": [{"id": "old", "link": ""}]}}), encoding="utf-8")
    sp.run(m, BASE, env=ENV)
    assert len(posts(f, "/22/media_publish")) == 1  # 只補第 2 張


# ---------- 2026-10-26：總開關 LIVE_ENABLED、USER_ID 空白時用權杖自動查 ----------
ENV_NOID = {"THREADS_USER_ID": "", "THREADS_ACCESS_TOKEN": TOK_T, "IG_USER_ID": "", "IG_ACCESS_TOKEN": TOK_I}
TH_ID, IG_ID = "17841400000098765", "17841400000054321"


class FakeMe(Fake):
    def __call__(self, method, url, **kw):
        if method == "GET" and url == sp.THREADS_ME:
            self.calls.append((method, url, kw))
            assert kw["params"]["fields"] == "id"
            return {"id": TH_ID}
        if method == "GET" and url == sp.IG_ME:
            self.calls.append((method, url, kw))
            assert kw["params"]["fields"] == "user_id,username"
            return {"user_id": IG_ID, "username": "x", "id": "OTHER_APP_SCOPED_ID"}
        return super().__call__(method, url, **kw)


def test_總開關檔不存在_有金鑰也只_dry_run(tmp_path, monkeypatch, capsys):
    f = Fake(); monkeypatch.setattr(sp, "http", f)
    monkeypatch.setattr(sp, "LIVE_FLAG", tmp_path / "nope" / "LIVE_ENABLED")
    assert sp.run(mk(tmp_path), BASE, env=ENV) == 0
    assert f.calls == []                      # 連查編號、延長權杖都不打
    out = capsys.readouterr().out
    assert "總開關關閉" in out and "dry-run" in out
    assert not (tmp_path / "posted.json").exists()


def test_repo_的總開關已開啟():
    # 2026-10-27 Andy「開始發…接下來就是自動發文」→ repo 要有 LIVE_ENABLED；要停發就刪檔並把這條改回 not exists
    from pathlib import Path
    assert (Path(sp.__file__).resolve().parents[1] / "docs/marketing/social_unit/LIVE_ENABLED").exists()


def test_USER_ID_空白時用權杖查_IG_用_user_id(tmp_path, monkeypatch, capsys):
    f = FakeMe(); monkeypatch.setattr(sp, "http", f)
    assert sp.run(mk(tmp_path), BASE, env=ENV_NOID) == 0
    assert len(posts(f, f"/{TH_ID}/threads_publish")) == 1
    assert len(posts(f, f"/{IG_ID}/media_publish")) == 2       # 用 user_id，不是 id
    out = capsys.readouterr().out
    assert TH_ID not in out.replace("::add-mask::" + TH_ID, "") and IG_ID not in out.replace("::add-mask::" + IG_ID, "")
    assert TH_ID[-4:] in out and IG_ID[-4:] in out             # 只印末 4 碼
    assert TOK_T not in out and TOK_I not in out


def test_有填_USER_ID_就不查(tmp_path, monkeypatch):
    f = FakeMe(); monkeypatch.setattr(sp, "http", f)
    sp.run(mk(tmp_path), BASE, env=ENV)
    assert not [c for c in f.calls if c[1] in (sp.THREADS_ME, sp.IG_ME)]


def test_查不到編號_回1不發(tmp_path, monkeypatch, capsys):
    def h(method, url, **kw):
        if url in (sp.THREADS_ME, sp.IG_ME):
            raise RuntimeError("HTTP 400 bad token " + TOK_T)
        raise AssertionError("查不到編號就不該打其他 API：" + url)
    monkeypatch.setattr(sp, "http", h)
    assert sp.run(mk(tmp_path), BASE, env=ENV_NOID) == 1
    out = capsys.readouterr().out
    assert "查不到" in out and TOK_T not in out


def test_工作流讀總開關():
    from pathlib import Path
    y = (Path(sp.__file__).resolve().parents[1] / ".github/workflows/social-live.yml").read_text(encoding="utf-8")
    assert "docs/marketing/social_unit/LIVE_ENABLED" in y and "總開關關閉" in y
