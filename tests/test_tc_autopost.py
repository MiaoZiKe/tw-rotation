"""頻道②「科技透明圈」自動發文（scripts/tc_token_intake.py、tc_post.py、meta_token_refresh.py 的 TC 組）：全部 mock，不連外。

涵蓋：收件流程（換長效、寫回、短效過期中文錯誤、頻道一帳號防呆）、只發 approved、上限順延、
log 與狀態檔不含權杖、沒有權杖時安靜跳過、監工告警、dry-run 不發不寫。
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import meta_token_refresh as mtr  # noqa: E402
import tc_post as tc  # noqa: E402
import tc_token_intake as ti  # noqa: E402

TPE = timezone(timedelta(hours=8))
NOW = datetime(2026, 11, 10, 21, 0, tzinfo=TPE)
SHORT, LONG, IGT, SECRET, PAT = ("THS_SHORT_aaaaaaaaaaaaaaaa", "THL_LONG_bbbbbbbbbbbbbbbbbb",
                                 "IGT_TOKEN_cccccccccccccccc", "APPSECRET_dddddddddddddd", "PAT_eeeeeeeeeeeeeeeeeeee")
ALL = (SHORT, LONG, IGT, SECRET, PAT)
CFG = {"enabled": True, "threads": True, "ig": True, "per_day": 1, "min_gap_hours": 20}


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    mtr._SECRETS.clear()
    tc._SECRETS.clear()
    monkeypatch.setattr(tc, "SLEEP", lambda s: None)


def _no_secret(*texts):
    for t in texts:
        body = t
        for s in ALL:
            body = body.replace("::add-mask::" + s, "")
        for s in ALL:
            assert s not in body


# ---------------- 收件 ----------------

def fake_meta(exchange_err=None, th_id="111", ig_id="222"):
    def f(url, params):
        if url == ti.EXCHANGE_URL:
            assert params["client_secret"] == SECRET and params["access_token"] == SHORT
            if exchange_err:
                raise RuntimeError(exchange_err)
            return {"access_token": LONG, "token_type": "bearer", "expires_in": 5184000}
        if url == ti.THREADS_ME:
            assert params["access_token"] == LONG
            return {"id": th_id, "username": "tc_threads"}
        if url == ti.IG_ME:
            assert params["access_token"] == IGT
            return {"user_id": ig_id, "username": "tc_ig"}
        raise AssertionError(url)
    return f


def intake(monkeypatch, tmp_path, env_extra=None, **kw):
    monkeypatch.setattr(mtr, "http_get", fake_meta(**kw))
    saved = []
    env = {"TC_THREADS_SHORT_TOKEN": SHORT, "META_APP_SECRET": SECRET, "TC_IG_ACCESS_TOKEN": IGT,
           "META_SECRETS_PAT": PAT, "GITHUB_REPOSITORY": "o/r", "THREADS_USER_ID": "999", "IG_USER_ID": "888"}
    env.update(env_extra or {})
    rc, st = ti.run(env, datetime(2026, 11, 8, 10, tzinfo=timezone.utc), state_path=tmp_path / "tc_token.json",
                    saver=lambda n, v, r, p: saved.append((n, v)) or True, lister=lambda r, p: {"META_APP_SECRET"})
    return rc, st, dict(saved)


def test_收件成功寫回四個Secret且不外洩(monkeypatch, tmp_path, capsys):
    rc, st, saved = intake(monkeypatch, tmp_path)
    assert rc == 0
    assert saved == {"TC_THREADS_ACCESS_TOKEN_AUTO": LONG, "TC_THREADS_USER_ID": "111",
                     "TC_IG_ACCESS_TOKEN_AUTO": IGT, "TC_IG_USER_ID": "222"}
    disk = (tmp_path / "tc_token.json").read_text()
    d = json.loads(disk)
    assert d["platforms"]["threads"]["username"] == "tc_threads" and d["platforms"]["threads"]["days_left"] == 60.0
    assert "111" not in disk and "222" not in disk          # 狀態檔不放 id
    out = capsys.readouterr().out
    assert "@tc_threads" in out and "成功" in out and "META_APP_SECRET：已設定" in out
    _no_secret(out, disk)


def test_短效權杖過期給中文錯誤(monkeypatch, tmp_path, capsys):
    rc, st, saved = intake(monkeypatch, tmp_path, exchange_err="HTTP 400 Error validating access token: Session has expired")
    assert rc == 1 and "TC_THREADS_ACCESS_TOKEN_AUTO" not in saved and "TC_IG_ACCESS_TOKEN_AUTO" in saved
    out = capsys.readouterr().out
    assert "短效權杖已過 1 小時，請重新產生" in out
    _no_secret(out)


def test_沒有AppSecret給中文提示(monkeypatch, tmp_path, capsys):
    rc, st, saved = intake(monkeypatch, tmp_path, env_extra={"META_APP_SECRET": ""})
    assert rc == 1 and "TC_THREADS_ACCESS_TOKEN_AUTO" not in saved
    assert "META_APP_SECRET 還沒設定" in capsys.readouterr().out


def test_頻道一帳號不寫回(monkeypatch, tmp_path, capsys):
    rc, st, saved = intake(monkeypatch, tmp_path, th_id="999", ig_id="888")
    assert rc == 1 and saved == {}
    assert "頻道一" in capsys.readouterr().out


def test_username對不上不寫回(monkeypatch, tmp_path):
    rc, st, saved = intake(monkeypatch, tmp_path, env_extra={"EXPECT_IG_USERNAME": "@other"})
    assert rc == 1 and "TC_IG_ACCESS_TOKEN_AUTO" not in saved and "TC_THREADS_ACCESS_TOKEN_AUTO" in saved


# ---------------- 續期（TC 組） ----------------

def test_續期沒有TC權杖安靜略過(monkeypatch, tmp_path):
    monkeypatch.setattr(mtr, "http_get", lambda u, p: {"access_token": p["access_token"], "expires_in": 5184000,
                                                       "id": "1", "user_id": "2"})
    rc, st = mtr.run({"THREADS_ACCESS_TOKEN": "a" * 20, "IG_ACCESS_TOKEN": "b" * 20}, datetime.now(timezone.utc),
                     False, state_path=tmp_path / "meta_token.json", saver=lambda *a: True)
    assert rc == 0 and not st["alert"]
    assert st["platforms"]["tc_threads"]["status"] == "missing" and st["platforms"]["tc_ig"]["status"] == "missing"


def test_續期TC優先AUTO且收件24小時內跳過(monkeypatch, tmp_path):
    now = datetime(2026, 11, 8, 12, tzinfo=timezone.utc)
    calls = []
    monkeypatch.setattr(mtr, "http_get", lambda u, p: calls.append((u, p["access_token"])) or
                        {"access_token": p["access_token"], "expires_in": 5184000, "id": "1", "user_id": "2"})
    (tmp_path / "tc_token.json").write_text(json.dumps({"platforms": {
        "threads": {"intake_at": (now - timedelta(hours=2)).isoformat(timespec="seconds"), "expires_on": "2027-01-07"}}}))
    env = {"TC_THREADS_ACCESS_TOKEN_AUTO": LONG, "TC_IG_ACCESS_TOKEN": IGT, "TC_IG_ACCESS_TOKEN_AUTO": "IGAUTO_ffffffffffff"}
    rc, st = mtr.run(env, now, False, state_path=tmp_path / "meta_token.json", saver=lambda *a: True)
    assert rc == 0
    assert st["platforms"]["tc_threads"]["status"] == "recent-skip"
    assert not any(t == LONG for _, t in calls)                       # 收件剛換過，不打 refresh
    assert ("https://graph.instagram.com/refresh_access_token", "IGAUTO_ffffffffffff") in calls   # AUTO 優先
    assert LONG not in (tmp_path / "meta_token.json").read_text()


# ---------------- 發文 ----------------

def mkpost(q: Path, name="20261110_a", status="approved", when="2026-11-10T20:30+08:00", imgs=("1.jpg", "2.jpg"),
           main="主文", reply="留言", extra=""):
    d = q / name
    d.mkdir(parents=True)
    for i in imgs:
        (d / i).write_bytes(b"\xff\xd8jpg")
    (d / "post.md").write_text(f"---\nstatus: {status}\nscheduled_at: {when}\nplatforms: ig, threads\n"
                               f"images: {', '.join(imgs)}\n{extra}---\n說明\n", encoding="utf-8")
    (d / "ig.txt").write_text("IG 說明 #科技透明圈", encoding="utf-8")
    (d / "threads.txt").write_text(f"【主文】\n{main}\n\n【第 1 則留言】\n{reply}\n", encoding="utf-8")
    return d


class FakeAPI:
    def __init__(self, th_id="111", ig_id="222", fail=None):
        self.calls, self.th_id, self.ig_id, self.fail, self.n = [], th_id, ig_id, fail, 0

    def __call__(self, platform, method, path, token, params=None):
        self.calls.append((platform, method, path, token, dict(params or {})))
        if self.fail and self.fail in (platform + path):
            raise tc.PostError(f"HTTP 400 {path}：boom")
        if path == "/me":
            return {"id": self.th_id, "username": "tc_threads"} if platform == "threads" else {"user_id": self.ig_id, "username": "tc_ig"}
        if method == "GET":
            f = (params or {}).get("fields", "")
            if "status" in f:
                return {"status": "FINISHED", "status_code": "FINISHED"}
            return {"permalink": f"https://{platform}.example/{path.strip('/')}",
                    "media_type": "CAROUSEL_ALBUM"}
        self.n += 1
        return {"id": f"{platform}{self.n}"}

    def posts(self, platform):
        return [c for c in self.calls if c[0] == platform and c[2].endswith(("media_publish", "threads_publish"))]


ENV = {"TC_THREADS_TOKEN": LONG, "TC_IG_TOKEN": IGT, "TC_THREADS_USER_ID": "111", "TC_IG_USER_ID": "222",
       "THREADS_USER_ID": "999", "IG_USER_ID": "888"}


def go(monkeypatch, tmp_path, env=ENV, dry=False, cfg=CFG, now=NOW, api=None):
    api = api or FakeAPI()
    monkeypatch.setattr(tc, "api", api)
    monkeypatch.setattr(tc, "check_public", lambda u: None)
    rc, res = tc.run(dict(env), now, dry, queue=tmp_path / "q", state_dir=tmp_path / "state", cfg=cfg)
    return rc, res, api


def test_只發approved並回寫urls與posted(monkeypatch, tmp_path, capsys):
    q = tmp_path / "q"
    a = mkpost(q, "20261110_a")
    mkpost(q, "20261110_b", status="draft")
    rc, res, api = go(monkeypatch, tmp_path)
    assert rc == 0 and res["posted"] == ["20261110_a"]
    assert len(api.posts("ig")) == 1 and len(api.posts("threads")) == 2      # Threads 主文＋第 1 則留言
    head = (a / "post.md").read_text()
    assert "status: posted" in head and "urls_ig: https://ig.example" in head and "urls_threads_reply:" in head
    assert "urls: https://" in head and "verified_ig: CAROUSEL_ALBUM" in head
    assert "status: draft" in (q / "20261110_b" / "post.md").read_text()
    # IG 是輪播、Threads 主文帶圖（不是純文字）
    ig_create = [c for c in api.calls if c[0] == "ig" and c[2].endswith("/media") and c[4].get("media_type") == "CAROUSEL"]
    th_main = [c for c in api.calls if c[0] == "threads" and c[4].get("media_type") == "CAROUSEL"]
    assert ig_create and th_main
    kid = next(c for c in api.calls if c[0] == "ig" and c[4].get("is_carousel_item"))
    assert kid[4]["image_url"].startswith(tc.RAW + "social/tc/queue/20261110_a/")
    reply = [c for c in api.calls if c[0] == "threads" and c[4].get("reply_to_id")]
    assert reply and reply[0][4]["text"] == "留言"
    posted = json.loads((tmp_path / "state" / "posted.json").read_text())
    assert posted["posts"][0]["id"] == "20261110_a" and posted["posts"][0]["ig"].startswith("https://")
    out = capsys.readouterr().out
    _no_secret(out, head, (tmp_path / "state" / "posted.json").read_text())


def test_沒有approved什麼都不做(monkeypatch, tmp_path):
    mkpost(tmp_path / "q", status="draft")
    rc, res, api = go(monkeypatch, tmp_path)
    assert rc == 0 and api.calls == [] and not res["alert"]


def test_上限順延不擠同一天(monkeypatch, tmp_path):
    q = tmp_path / "q"
    mkpost(q, "20261110_a", when="2026-11-10T20:00+08:00")
    b = mkpost(q, "20261110_b", when="2026-11-10T20:10+08:00")
    rc, res, api = go(monkeypatch, tmp_path)
    assert res["posted"] == ["20261110_a"]
    rc2, res2, api2 = go(monkeypatch, tmp_path, now=NOW + timedelta(minutes=15))
    assert api2.posts("ig") == [] and res2["deferred"]
    head = (b / "post.md").read_text()
    assert "status: approved" in head and "deferred_until: 2026-11-11T17:00+08:00" in head   # 20 小時後（同時跨日）
    assert not res2["alert"]                                                                 # 順延不算沒發
    rc3, res3, _ = go(monkeypatch, tmp_path, now=datetime(2026, 11, 11, 17, 5, tzinfo=TPE))
    assert res3["posted"] == ["20261110_b"]


def test_同一天第二篇順延到隔天(monkeypatch, tmp_path):
    p = {"meta": {"scheduled_at": "2026-11-10T23:00+08:00"}}
    hist = [datetime(2026, 11, 10, 1, 0, tzinfo=TPE)]
    due = tc.effective_due(p, hist, dict(CFG, min_gap_hours=0))
    assert due == datetime(2026, 11, 11, 0, 0, tzinfo=TPE)


def test_沒有權杖安靜跳過不失敗(monkeypatch, tmp_path, capsys):
    mkpost(tmp_path / "q")
    rc, res, api = go(monkeypatch, tmp_path, env={})
    assert rc == 0 and api.calls == [] and res["skipped"] == ["20261110_a"]
    assert "安靜跳過" in capsys.readouterr().out
    assert json.loads((tmp_path / "state" / "status.json").read_text())["no_token_since"]


def test_監工已核准超過30分鐘沒發開告警(monkeypatch, tmp_path):
    mkpost(tmp_path / "q", when="2026-11-10T20:00+08:00")
    rc, res, _ = go(monkeypatch, tmp_path, env={}, now=datetime(2026, 11, 10, 20, 40, tzinfo=TPE))
    assert res["alert"] and "沒有 TC 權杖" in res["alert"][0]
    rc, res, _ = go(monkeypatch, tmp_path, env={}, now=datetime(2026, 11, 10, 20, 20, tzinfo=TPE))
    assert not res["alert"]


def test_頻道一權杖整篇不發(monkeypatch, tmp_path):
    a = mkpost(tmp_path / "q")
    rc, res, api = go(monkeypatch, tmp_path, api=FakeAPI(th_id="999"))
    assert rc == 1 and api.posts("ig") == [] and api.posts("threads") == []
    assert "頻道一" in res["errors"][0]


def test_Threads失敗只記IG已發_修好只補Threads(monkeypatch, tmp_path):
    a = mkpost(tmp_path / "q")
    rc, res, api = go(monkeypatch, tmp_path, api=FakeAPI(fail="threads/111/threads"))
    head = (a / "post.md").read_text()
    assert rc == 1 and "status: error" in head and "done: ig" in head and res["alert"]
    (a / "post.md").write_text(head.replace("status: error", "status: approved"))
    rc2, res2, api2 = go(monkeypatch, tmp_path, now=NOW + timedelta(days=1))
    assert rc2 == 0 and api2.posts("ig") == [] and len(api2.posts("threads")) == 2
    assert "status: posted" in (a / "post.md").read_text()


def test_dry_run不發不寫(monkeypatch, tmp_path):
    a = mkpost(tmp_path / "q")
    before = (a / "post.md").read_text()
    rc, res, api = go(monkeypatch, tmp_path, dry=True)
    assert rc == 0 and api.posts("ig") == [] and api.posts("threads") == []
    assert all(c[1] == "GET" for c in api.calls)
    assert (a / "post.md").read_text() == before and not (tmp_path / "state").exists()


def test_開關關閉不連外(monkeypatch, tmp_path):
    mkpost(tmp_path / "q")
    rc, res, api = go(monkeypatch, tmp_path, cfg=dict(CFG, enabled=False))
    assert rc == 0 and api.calls == []


def test_設定檔沒有tc區塊就全關():
    assert tc.settings({"live": {}, "queue": {}})["enabled"] is False
    assert tc.settings({"tc": {"enabled": True, "per_day": "x"}})["enabled"] is False


def test_格式檢查擋PNG與沒圖():
    p = {"dir": Path("/nonexist"), "id": "x", "meta": {"status": "approved", "scheduled_at": "2026-11-10T20:30+08:00"},
         "platforms": ["ig"], "images": ["a.png"], "caption": "x", "main": "", "reply": "", "done": []}
    assert any("JPEG" in e for e in tc.validate(p))
    p["images"] = []
    assert any("封面一定要有圖" in e for e in tc.validate(p))


def test_廣達稿在佇列且是draft():
    d = Path(__file__).resolve().parent.parent / "social" / "tc" / "queue" / "20261105_quanta"
    p = tc.load(d)
    assert p["meta"]["status"] == "draft"
    assert p["images"] == ["1_cover.jpg", "2_fields.jpg"] and all((d / x).is_file() for x in p["images"])
    assert p["main"] and p["reply"] and p["caption"]


def test_正式開關檔tc區塊():
    s = tc.settings(json.loads(tc.post_quota.QUOTA_FILE.read_text(encoding="utf-8")))
    assert s["enabled"] and s["per_day"] == 1 and s["min_gap_hours"] == 20


# ---------------- 自動刪文 ----------------

def test_delete_at到了Threads刪留言與主文_IG開issue(monkeypatch, tmp_path):
    a = mkpost(tmp_path / "q", extra="delete_at: 2026-11-11T20:30+08:00\n")
    go(monkeypatch, tmp_path)                                        # 先發出
    head = (a / "post.md").read_text()
    assert "ids_threads:" in head and "ids_threads_reply:" in head and "ids_ig:" in head

    class DelAPI(FakeAPI):
        deleted = set()

        def __call__(self, platform, method, path, token, params=None):
            if method == "DELETE":
                self.calls.append((platform, method, path, token, {}))
                self.deleted.add(path)
                return {"success": True}
            if method == "GET" and path in self.deleted:
                raise tc.PostError("HTTP 400 not found")
            return super().__call__(platform, method, path, token, params)
    api = DelAPI()
    rc, res, _ = go(monkeypatch, tmp_path, now=datetime(2026, 11, 11, 20, 40, tzinfo=TPE), api=api)
    dels = [c[2] for c in api.calls if c[1] == "DELETE"]
    assert rc == 0 and len(dels) == 2 and all(c[0] == "threads" for c in api.calls if c[1] == "DELETE")
    assert res["ig_delete"] and "ig.example" in res["ig_delete"][0]
    head = (a / "post.md").read_text()
    assert "deleted_threads:" in head and "ig_delete_notified:" in head
    rc2, res2, api2 = go(monkeypatch, tmp_path, now=datetime(2026, 11, 11, 21, 0, tzinfo=TPE), api=DelAPI())
    assert not res2["ig_delete"] and not [c for c in api2.calls if c[1] == "DELETE"]   # 不重刪、不重開 issue


def test_delete_at沒到不刪(monkeypatch, tmp_path):
    mkpost(tmp_path / "q", extra="delete_at: 2026-12-01T20:30+08:00\n")
    go(monkeypatch, tmp_path)
    rc, res, api = go(monkeypatch, tmp_path, now=NOW + timedelta(days=2))
    assert not [c for c in api.calls if c[1] == "DELETE"] and not res["ig_delete"]


# ---------------- 自動測試發文 ----------------

import tc_selftest as stt  # noqa: E402


class SelfAPI(FakeAPI):
    def __init__(self, no_delete=False, **kw):
        super().__init__(**kw)
        self.no_delete, self.gone = no_delete, set()

    def __call__(self, platform, method, path, token, params=None):
        if method == "DELETE":
            self.calls.append((platform, method, path, token, {}))
            self.gone.add(path)
            return {"success": True}
        if path == "/me/threads_publishing_limit":
            self.calls.append((platform, method, path, token, dict(params or {})))
            return {"data": [{"quota_usage": 1}]} if self.no_delete else {"data": [{"delete_quota_usage": 0}]}
        if path == "/me/threads":
            return {"data": [{"id": f"threads{self.n}"}]}
        if method == "GET" and path in self.gone:
            raise tc.PostError("HTTP 400 not found")
        if path in ("/me/media",):
            return {"data": []}
        return super().__call__(platform, method, path, token, params)


def selftest(monkeypatch, tmp_path, api):
    monkeypatch.setattr(tc, "api", api)
    monkeypatch.setattr(tc, "check_public", lambda u: None)
    return stt.run(dict(ENV), NOW, state_path=tmp_path / "tc_selftest.json")


def test_自動測試Threads發了就刪_IG不發布(monkeypatch, tmp_path, capsys):
    api = SelfAPI()
    rc, st = selftest(monkeypatch, tmp_path, api)
    assert rc == 0 and st["ok"]
    assert len(api.posts("threads")) == 1 and [c for c in api.calls if c[1] == "DELETE"]
    assert not any(c[2].endswith("media_publish") for c in api.calls)           # IG 絕不發布
    assert any(c[0] == "ig" and c[2].endswith("/media") and c[1] == "POST" for c in api.calls)
    disk = (tmp_path / "tc_selftest.json").read_text()
    _no_secret(disk, capsys.readouterr().out)


def test_自動測試沒有刪除權限就不發測試文(monkeypatch, tmp_path):
    api = SelfAPI(no_delete=True)
    rc, st = selftest(monkeypatch, tmp_path, api)
    assert rc == 1 and api.posts("threads") == []
    assert not st["platforms"]["threads"]["ok"]


def test_自動測試沒有權杖跳過(monkeypatch, tmp_path):
    rc, st = stt.run({}, NOW, state_path=tmp_path / "s.json")
    assert rc == 0 and not (tmp_path / "s.json").exists()


# ---------------- Threads 留言關鍵字公開回覆 ----------------

import tc_threads_replies as tr  # noqa: E402


class ReplyAPI(FakeAPI):
    def __call__(self, platform, method, path, token, params=None):
        if path == "/me/threads":
            return {"data": [{"id": "p1"}]}
        if path == "/p1/replies":
            return {"data": [{"id": "r1", "text": "求 透 明 整理", "username": "amy"},
                             {"id": "r2", "text": "透明！", "username": "amy"},      # 同一人同一篇只回 1 次
                             {"id": "r3", "text": "路過", "username": "bob"},
                             {"id": "r4", "text": "透明", "username": "tc_threads"}]}  # 自己不回
        return super().__call__(platform, method, path, token, params)


def _cfg(tmp_path, legal=True):
    c = json.loads((Path(__file__).resolve().parent.parent / "social/tc/dm_config.json").read_text(encoding="utf-8"))
    c["legal_reviewed"] = legal
    p = tmp_path / "cfg.json"
    p.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    return p


def test_Threads關鍵字回覆每人一次且不存原文(monkeypatch, tmp_path):
    api = ReplyAPI()
    monkeypatch.setattr(tc, "api", api)
    rc, res = tr.run(dict(ENV), NOW, False, config_path=_cfg(tmp_path), state_path=tmp_path / "rep.json")
    sent = [c for c in api.calls if c[4].get("reply_to_id")]
    assert rc == 0 and res["replied"] == 1 and sent[0][4]["reply_to_id"] == "r1"
    assert "liguligu-puipui.com" in sent[0][4]["text"]
    disk = (tmp_path / "rep.json").read_text()
    assert "amy" not in disk and "透明" not in disk and "r1" not in disk
    api2 = ReplyAPI()
    monkeypatch.setattr(tc, "api", api2)
    rc, res = tr.run(dict(ENV), NOW, False, config_path=_cfg(tmp_path), state_path=tmp_path / "rep.json")
    assert res["replied"] == 0 and not [c for c in api2.calls if c[4].get("reply_to_id")]


def test_Threads回覆沒過法遵只記錄(monkeypatch, tmp_path):
    api = ReplyAPI()
    monkeypatch.setattr(tc, "api", api)
    rc, res = tr.run(dict(ENV), NOW, False, config_path=_cfg(tmp_path, legal=False), state_path=tmp_path / "rep.json")
    assert res["replied"] == 0 and res["would_reply"] == 1 and not [c for c in api.calls if c[1] == "POST"]


# ---------------- IG 留言 → 私訊 → 回「好了」→ 查追蹤 → 送整理 ----------------

import tc_ig_dm as dm  # noqa: E402


class DMAPI(FakeAPI):
    def __init__(self, follows=True, reply_text="好了", **kw):
        super().__init__(**kw)
        self.follows, self.reply_text, self.sent = follows, reply_text, []

    def __call__(self, platform, method, path, token, params=None):
        p = dict(params or {})
        self.calls.append((platform, method, path, token, p))
        if path == "/me":
            return {"user_id": "222", "username": "tc_ig"}
        if path == "/222/media":
            return {"data": [{"id": "m1"}]}
        if path == "/m1/comments":
            return {"data": [{"id": "c1", "text": "想看透明整理", "timestamp": "2026-11-10T12:00:00+0000", "from": {"id": "u9", "username": "amy"}},
                             {"id": "c2", "text": "路過", "timestamp": "2026-11-10T12:00:00+0000", "from": {"id": "u8"}}]}
        if path == "/me/conversations":
            return {"data": [{"id": "cv1", "updated_time": "2026-11-10T12:50:00+0000"}]}
        if path == "/cv1":
            return {"messages": {"data": [{"id": "msg1", "from": {"id": "u9"}, "message": self.reply_text}]}}
        if path == "/u9":
            return {"is_user_follow_business": self.follows}
        if path == "/222/messages":
            self.sent.append((json.loads(p["recipient"]), json.loads(p["message"])["text"]))
            return {"message_id": "x"}
        raise AssertionError(path)


def dm_run(monkeypatch, tmp_path, api, legal=True, now=NOW):
    monkeypatch.setattr(tc, "api", api)
    return dm.run(dict(ENV), now, False, config_path=_cfg(tmp_path, legal), state_path=tmp_path / "igdm.json",
                  posted_path=tmp_path / "posted.json")


def test_IG兩段式_先私回再查追蹤才送內容(monkeypatch, tmp_path):
    (tmp_path / "posted.json").write_text(json.dumps({"posts": [{"id": "20261105_quanta", "ids_ig": "m1"}]}))
    api = DMAPI(follows=True)
    rc, res = dm_run(monkeypatch, tmp_path, api)
    assert rc == 0 and res["prompted"] == 1 and res["delivered"] == 1
    first, second = api.sent
    assert first[0] == {"comment_id": "c1"} and "@tc_ig" in first[1] and "好了" in first[1]
    assert second[0] == {"id": "u9"} and "58～69K" in second[1] and "liguligu-puipui.com" in second[1]
    # 追蹤查詢一定在第 1 則私訊之後（Meta：要對方先傳訊息才查得到）
    idx_prof = next(i for i, c in enumerate(api.calls) if c[2] == "/u9")
    idx_first = next(i for i, c in enumerate(api.calls) if c[2] == "/222/messages")
    assert idx_first < idx_prof
    disk = (tmp_path / "igdm.json").read_text()
    assert "amy" not in disk and "u9" not in disk and "透明" not in disk
    api2 = DMAPI(follows=True)                                   # 再跑一輪：不重複私回、不重送
    rc, res = dm_run(monkeypatch, tmp_path, api2)
    assert api2.sent == []


def test_IG沒追蹤回提醒(monkeypatch, tmp_path):
    api = DMAPI(follows=False)
    rc, res = dm_run(monkeypatch, tmp_path, api)
    assert res["not_following"] == 1 and "還沒看到你追蹤" in api.sent[-1][1]


def test_IG沒過法遵只記錄不送(monkeypatch, tmp_path):
    api = DMAPI()
    rc, res = dm_run(monkeypatch, tmp_path, api, legal=False)
    assert api.sent == [] and res["would"] == 1


def test_IG_mode是webhook時輪詢不動作(monkeypatch, tmp_path):
    p = _cfg(tmp_path)
    c = json.loads(p.read_text(encoding="utf-8"))
    c["ig_dm"]["mode"] = "webhook"
    p.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    api = DMAPI()
    monkeypatch.setattr(tc, "api", api)
    rc, res = dm.run(dict(ENV), NOW, False, config_path=p, state_path=tmp_path / "s.json", posted_path=tmp_path / "p.json")
    assert rc == 0 and api.calls == []


def test_私訊文案沒有禁用字():
    c = json.loads((Path(__file__).resolve().parent.parent / "social/tc/dm_config.json").read_text(encoding="utf-8"))
    blob = json.dumps(c["ig_dm"], ensure_ascii=False) + c["threads_reply"]["text"]
    for w in ("投資建議", "內部", "爆料", "買進", "賣出", "保證", "飆"):
        assert w not in blob


def test_Worker_tc_dm_node測試():
    import shutil
    import subprocess
    if not shutil.which("node"):
        pytest.skip("沒有 node")
    root = Path(__file__).resolve().parent.parent
    r = subprocess.run(["node", "--test", "workers/tc-dm/test/worker.test.mjs"], cwd=root, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-1000:]
    assert "workers_dev = true" in (root / "workers/tc-dm/wrangler.toml").read_text(encoding="utf-8")
