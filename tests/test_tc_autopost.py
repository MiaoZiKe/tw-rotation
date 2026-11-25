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
    assert p["meta"]["status"] in ("draft", "approved", "posted")  # 2026-11-10 Andy：「廣達核准」；11-12 發出後是 posted
    assert p["images"] == ["1_cover.jpg", "2_fields.jpg"] and all((d / x).is_file() for x in p["images"])
    assert p["main"] and p["reply"] and p["caption"]


def test_正式開關檔tc區塊():
    s = tc.settings(json.loads(tc.post_quota.QUOTA_FILE.read_text(encoding="utf-8")))
    assert s["enabled"] and s["per_day"] == 2 and s["min_gap_hours"] == 6  # 2026-11-15 Andy 選「C：全部改成影片」每天 1 支，間隔 20→12 小時


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
    assert sent[0][4]["text"] == "完整內容請到 IG 私訊我們，馬上傳給您!~"   # 2026-11-23 Andy：「Threads請他訊IG」；沒對到篇＝預設句、不放網址
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
    for w in ("投資建議", "內部", "爆料", "買進", "賣出", "保證", "飆", "完整整理", "FW 面談"):
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


# ---------------- 2026-11-09 法遵審後修改 ----------------

def test_follow_gate關閉_不查追蹤直接私回重點(monkeypatch, tmp_path):
    p = _cfg(tmp_path)
    c = json.loads(p.read_text(encoding="utf-8"))
    c["ig_dm"]["follow_gate"] = False
    p.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "posted.json").write_text(json.dumps({"posts": [{"id": "20261105_quanta", "ids_ig": "m1"}]}))
    api = DMAPI(follows=False)
    monkeypatch.setattr(tc, "api", api)
    rc, res = dm.run(dict(ENV), NOW, False, config_path=p, state_path=tmp_path / "s.json", posted_path=tmp_path / "posted.json")
    assert not any(c[2] == "/u9" for c in api.calls)                 # 不查追蹤
    first = api.sent[0]
    assert first[0] == {"comment_id": "c1"}
    assert first[1].startswith("謝謝留言！重點整理在下面，想看後續可以追蹤 @tc_ig") and "58～69K" in first[1]
    assert all("還沒看到你追蹤" not in t for _, t in api.sent)        # 對方回「好了」也不會被要求追蹤


def test_法遵審後的正式設定():
    root = Path(__file__).resolve().parent.parent
    c = json.loads((root / "social/tc/dm_config.json").read_text(encoding="utf-8"))
    blob = json.dumps(c, ensure_ascii=False)
    assert c["legal_reviewed"] is True and "2026-11-09 法遵審過" in c["legal_note"]
    assert c["ig_dm"]["follow_gate"] is True
    assert "完整整理" not in blob and "FW 面談" not in blob and "網友分享的面試方向" in blob
    assert c["threads_reply"]["ask_ig_default"] == "完整內容請到 IG 私訊我們，馬上傳給您!~"   # 2026-11-23 Andy：「Threads請他訊IG」
    assert c["ig_dm"]["ack_public_default"] == "已經將完整內容私訊您囉!~"
    assert "僅保存去識別化的編號與時間，30 天後刪除" in (root / "docs/marketing/channels/tc/app_review/README.md").read_text(encoding="utf-8")


def test_廣達Threads主文在500字內():
    d = Path(__file__).resolve().parent.parent / "social" / "tc" / "queue" / "20261105_quanta"
    p = tc.load(d)
    assert tc.validate(p) == []
    # 2026-11-09 起改用 Andy 親寫文案（docs/marketing/channels/tc/andy_style.md）：主文不放聲明，出處一行放第 1 則留言
    assert "52～64K" in p["main"] and "非公司公告" not in p["main"]
    assert "國土測繪中心" in p["reply"] and "廣達官方" not in p["reply"]  # 封面是 Andy 本人拍攝（2026-11-10）


# ---------------- 2026-11-10 頻道④交接：TECH_* 的 IG 是 EAA 系統用戶權杖（graph.facebook.com） ----------------

EAA = "EAA_SYSTEM_USER_TOKEN_gggggggggggggggg"


def test_EAA權杖IG走Facebook網域_帳號編號重用頻道4探查(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(tc, "_fb_call", lambda m, p, t, q=None: calls.append((m, p, t, dict(q or {}))) or (
        {"id": "17840", "username": "tech_01010909"} if p == "/17840" else
        {"status_code": "FINISHED"} if (q or {}).get("fields") == "status_code" else
        {"permalink": "https://www.instagram.com/p/x/", "media_type": "CAROUSEL_ALBUM"} if m == "GET" else {"id": f"c{len(calls)}"}))
    monkeypatch.setattr(tc, "resolve_eaa_uid", lambda tok: "17840")
    monkeypatch.setattr(tc, "check_public", lambda u: None)
    uid, uname = tc.preflight("ig", EAA, "", "888")
    assert (uid, uname) == ("17840", "tech_01010909")
    r = tc.post_ig(uid, ["https://raw/a.jpg", "https://raw/b.jpg"], "cap", EAA)
    assert r["media_type"] == "CAROUSEL_ALBUM"
    assert all(c[2] == EAA for c in calls) and any(c[1] == "/17840/media_publish" for c in calls)
    with pytest.raises(tc.PostError, match="不能用 API 刪除"):
        tc.api("ig", "DELETE", "/1", EAA)


def test_EAA沒有粉絲專頁時IG私訊安靜跳過_發文不受影響(monkeypatch, tmp_path):
    import healing_post as HP
    monkeypatch.setattr(tc, "_fb_call", lambda m, p, t, q=None: {"id": "17840", "username": "tech_01010909"})
    monkeypatch.setattr(tc, "resolve_eaa_uid", lambda tok: "17840")
    monkeypatch.setattr(HP, "fb_pages", lambda tok, with_token=False: [])
    rc, res = dm.run({"TC_IG_TOKEN": EAA}, NOW, False, config_path=_cfg(tmp_path), state_path=tmp_path / "s.json",
                     posted_path=tmp_path / "p.json")
    assert rc == 0 and "Messenger Platform" in res["unsupported"]


def test_EAA有粉絲專頁就用專頁權杖與page端點(monkeypatch):
    import healing_post as HP
    monkeypatch.setattr(HP, "fb_pages", lambda tok, with_token=False: [
        {"ig_id": "17840", "page_id": "999", "page_token": "EAA_PAGE_TOKEN_hhhhhhhhhhhh", "name": "x", "ig_username": "tech_01010909"}])
    ctx, why = dm.messaging_ctx("17840", EAA)
    assert ctx == {"send": "/999/messages", "conv": "/999/conversations", "tok": "EAA_PAGE_TOKEN_hhhhhhhhhhhh"}


def test_工作流吃TECH權杖_channel_post不再排tech():
    root = Path(__file__).resolve().parent.parent
    for f in ("tc_post.yml", "tc_selftest.yml"):
        y = (root / ".github/workflows" / f).read_text(encoding="utf-8")
        assert "secrets.TECH_IG_ACCESS_TOKEN_AUTO || secrets.TECH_IG_ACCESS_TOKEN" in y
        assert "secrets.TECH_THREADS_ACCESS_TOKEN_AUTO || secrets.TECH_THREADS_ACCESS_TOKEN" in y
        assert "secrets.TC_IG_ACCESS" not in y and "secrets.TC_THREADS_ACCESS" not in y
    ch = json.loads((root / "docs/marketing/channels/channels.json").read_text(encoding="utf-8"))
    assert ch["channels"]["tech"]["handed_over"] == "tc_post.yml"
    assert "頻道② 改用 tc_post.yml，2026-11-10 頻道④交接" in (root / ".github/workflows/channel_post.yml").read_text(encoding="utf-8")


# ---------------- 星期幾防呆（2026-11-12 事故：把 11/13 週五誤當週四，週四當晚沒發；Andy：「避免再度發生」） ----------------

def test_星期對得上照常發(monkeypatch, tmp_path, capsys):
    q = tmp_path / "q"
    mkpost(q, when="2026-11-12T20:30+08:00", extra="weekday: 四\n")
    p = tc.load(q / "20261110_a")
    assert tc.weekday_check(p) == ("", "") and tc.validate(p) == []
    rc, res, api = go(monkeypatch, tmp_path, now=datetime(2026, 11, 12, 20, 31, tzinfo=TPE))
    assert rc == 0 and res["posted"] == ["20261110_a"]
    assert "weekday" not in capsys.readouterr().out          # 對得上不印警告


def test_星期對不上擋下不發(monkeypatch, tmp_path, capsys):
    q = tmp_path / "q"
    a = mkpost(q, when="2026-11-13T20:30+08:00", extra="weekday: 四\n")   # 11/13 是星期五
    errs = tc.validate(tc.load(a))
    assert any("星期對不上" in e and "星期五" in e for e in errs)
    rc, res, api = go(monkeypatch, tmp_path, now=datetime(2026, 11, 13, 21, 0, tzinfo=TPE))
    assert rc == 0 and res["posted"] == [] and not api.calls            # 一個 Meta API 都沒打；整輪不失敗
    assert any("星期對不上" in e for e in res["errors"]) and any("星期對不上" in x for x in res["alert"])
    assert "status: approved" in (a / "post.md").read_text()          # 不改稿、不發
    assert tc.main(["--check", "--queue", str(q)]) == 0               # --check 只警告，不讓整個工作流失敗
    out = capsys.readouterr().out
    assert "星期對不上" in out and "::warning::" in out


def test_缺weekday只警告不擋(monkeypatch, tmp_path, capsys):
    q = tmp_path / "q"
    mkpost(q, when="2026-11-12T20:30+08:00")
    p = tc.load(q / "20261110_a")
    err, warn = tc.weekday_check(p)
    assert err == "" and "weekday: 四" in warn
    assert tc.main(["--check", "--queue", str(q)]) == 0
    assert "沒有 weekday" in capsys.readouterr().out
    rc, res, api = go(monkeypatch, tmp_path, now=datetime(2026, 11, 12, 20, 31, tzinfo=TPE))
    assert rc == 0 and res["posted"] == ["20261110_a"]


def test_weekday寫法容錯():
    p = {"id": "x", "meta": {"scheduled_at": "2026-11-14T11:00+08:00", "weekday": "週六"}}
    assert tc.weekday_check(p) == ("", "")
    p["meta"]["weekday"] = "星期六"
    assert tc.weekday_check(p) == ("", "")
    p["meta"]["weekday"] = "Sat"
    assert "看不懂" in tc.weekday_check(p)[0]


def test_佇列稿件都有weekday且對得上():
    q = Path(__file__).resolve().parent.parent / "social" / "tc" / "queue"
    for d in sorted(q.glob("*/")):
        if (d / "post.md").is_file():
            p = tc.load(d)
            if p["meta"].get("status") in ("approved", "draft"):
                assert tc.weekday_check(p) == ("", ""), d.name


# ---------------- 影片發文（2026-11-14：IG Reels＋Threads VIDEO） ----------------

def mkvideo(q: Path, name="20261115_v", when="2026-11-15T20:00+08:00", imgs=(), extra="weekday: 日\n"):
    d = q / name
    d.mkdir(parents=True)
    (d / "ep.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")
    for i in imgs:
        (d / i).write_bytes(b"\xff\xd8jpg")
    (d / "post.md").write_text(f"---\nstatus: approved\nscheduled_at: {when}\n{extra}platforms: ig, threads\n"
                               f"media: video\nvideo: ep.mp4\nimages: {', '.join(imgs)}\n---\n說明\n", encoding="utf-8")
    (d / "ig.txt").write_text("IG 影片說明 #科技透明圈", encoding="utf-8")
    (d / "threads.txt").write_text("【主文】\n影片主文\n\n【第 1 則留言】\n影片留言\n", encoding="utf-8")
    return d


class VideoAPI(FakeAPI):
    """容器狀態照順序回（IN_PROGRESS → … → FINISHED），回查 media_type 回影片。"""

    def __init__(self, seq=("IN_PROGRESS", "IN_PROGRESS", "FINISHED"), ig_type="VIDEO", th_type="VIDEO", **kw):
        super().__init__(**kw)
        self.seq = {"ig": list(seq), "threads": list(seq)}
        self.types = {"ig": ig_type, "threads": th_type}
        self.polls = {"ig": 0, "threads": 0}

    def __call__(self, platform, method, path, token, params=None):
        f = (params or {}).get("fields", "")
        if method == "GET" and path != "/me" and "status" in f:
            self.calls.append((platform, method, path, token, dict(params or {})))
            self.polls[platform] += 1
            s = self.seq[platform].pop(0) if len(self.seq[platform]) > 1 else self.seq[platform][0]
            return {"status": s, "status_code": s, "error_message": "bad codec" if s == "ERROR" else ""}
        if method == "GET" and "media_type" in f:
            self.calls.append((platform, method, path, token, dict(params or {})))
            return {"permalink": f"https://{platform}.example/{path.strip('/')}", "media_type": self.types[platform]}
        return super().__call__(platform, method, path, token, params)


VNOW = datetime(2026, 11, 15, 20, 1, tzinfo=TPE)


def test_影片稿件通過驗證_images可空_weekday照查():
    import tempfile
    q = Path(tempfile.mkdtemp())
    p = tc.load(mkvideo(q))
    assert p["media"] == "video" and p["video"] == "ep.mp4" and p["images"] == []
    assert tc.validate(p) == []
    assert tc.main(["--check", "--queue", str(q)]) == 0
    bad = tc.load(mkvideo(q, "20261115_w", extra="weekday: 六\n"))      # 11/15 是星期日
    assert any("星期對不上" in e for e in tc.validate(bad))
    nofile = tc.load(mkvideo(q, "20261115_x"))
    (nofile["dir"] / "ep.mp4").unlink()
    assert any("找不到影片檔" in e for e in tc.validate(nofile))
    nofile["video"] = ""
    assert any("video: 沒填" in e for e in tc.validate(nofile))
    nofile["media"] = "gif"
    assert any("media 只能填" in e for e in tc.validate(nofile))


def test_IG影片一直查到FINISHED才發布_每10秒(monkeypatch, tmp_path, capsys):
    sleeps = []
    monkeypatch.setattr(tc, "SLEEP", lambda s: sleeps.append(s))
    a = mkvideo(tmp_path / "q", imgs=("cover.jpg",))
    api = VideoAPI(seq=("IN_PROGRESS", "IN_PROGRESS", "IN_PROGRESS", "FINISHED"))
    rc, res, api = go(monkeypatch, tmp_path, api=api, now=VNOW)
    assert rc == 0 and res["posted"] == ["20261115_v"]
    ig = [c for c in api.calls if c[0] == "ig"]
    create = next(c for c in ig if c[2] == "/222/media")
    assert create[4]["media_type"] == "REELS" and create[4]["caption"] == "IG 影片說明 #科技透明圈"
    assert create[4]["share_to_feed"] == "false"  # 2026-11-20 Andy：Reels 只進 Reels 分頁
    assert create[4]["video_url"] == tc.RAW + "social/tc/queue/20261115_v/ep.mp4"
    assert create[4]["cover_url"] == tc.RAW + "social/tc/queue/20261115_v/cover.jpg"
    assert "image_url" not in create[4]
    i_create, i_pub = ig.index(create), next(i for i, c in enumerate(ig) if c[2].endswith("media_publish"))
    polls = [i for i, c in enumerate(ig) if c[1] == "GET" and "status" in c[4].get("fields", "")]
    assert len(polls) == 4 and all(i_create < i < i_pub for i in polls)      # 4 次查到 FINISHED 才發布
    assert sleeps.count(10) >= 3
    head = (a / "post.md").read_text()
    assert "status: posted" in head and "verified_ig: VIDEO" in head and "verified_threads: VIDEO" in head
    assert "回查 media_type" not in capsys.readouterr().out                 # 影片回查不跳警告


def test_IG影片ERROR就報錯不發布(monkeypatch, tmp_path):
    a = mkvideo(tmp_path / "q")
    rc, res, api = go(monkeypatch, tmp_path, api=VideoAPI(seq=("IN_PROGRESS", "ERROR")), now=VNOW)
    assert rc == 1 and api.posts("ig") == [] and api.posts("threads") == []
    assert "IG 影片容器處理失敗（ERROR）" in res["errors"][0] and res["alert"]
    assert "status: error" in (a / "post.md").read_text()


def test_影片容器5分鐘沒好就報錯(monkeypatch, tmp_path):
    mkvideo(tmp_path / "q")
    api = VideoAPI(seq=("IN_PROGRESS",))
    rc, res, api = go(monkeypatch, tmp_path, api=api, now=VNOW)
    assert rc == 1 and api.posts("ig") == [] and api.polls["ig"] == 30       # 300 秒 ÷ 10 秒
    assert "5 分鐘內沒處理完" in res["errors"][0]


def test_Threads影片可以發出_再發第1則留言(monkeypatch, tmp_path):
    a = mkvideo(tmp_path / "q")
    rc, res, api = go(monkeypatch, tmp_path, api=VideoAPI(), now=VNOW)
    assert rc == 0
    th = [c for c in api.calls if c[0] == "threads" and c[1] == "POST"]
    main = th[0]
    assert main[4] == {"media_type": "VIDEO", "video_url": tc.RAW + "social/tc/queue/20261115_v/ep.mp4", "text": "影片主文"}
    assert api.polls["threads"] >= 1
    assert len(api.posts("threads")) == 2                                      # 主文＋第 1 則留言
    reply = [c for c in th if c[4].get("reply_to_id")]
    assert reply and reply[0][4]["text"] == "影片留言" and reply[0][4]["media_type"] == "TEXT"
    head = (a / "post.md").read_text()
    assert "urls_threads: https://threads.example" in head and "urls_threads_reply:" in head


def test_Threads影片ERROR報錯_IG已發只補Threads(monkeypatch, tmp_path):
    class ThErr(VideoAPI):
        def __call__(self, platform, method, path, token, params=None):
            if platform == "threads":
                self.seq["threads"] = ["ERROR"]
            return super().__call__(platform, method, path, token, params)
    a = mkvideo(tmp_path / "q")
    rc, res, api = go(monkeypatch, tmp_path, api=ThErr(), now=VNOW)
    head = (a / "post.md").read_text()
    assert rc == 1 and "done: ig" in head and api.posts("threads") == []
    assert "Threads 影片容器處理失敗（ERROR）：bad codec" in res["errors"][0]


def test_影片回查不是影片會警告(monkeypatch, tmp_path, capsys):
    mkvideo(tmp_path / "q")
    rc, res, api = go(monkeypatch, tmp_path, api=VideoAPI(ig_type="IMAGE"), now=VNOW)
    assert rc == 0
    assert "ig 回查 media_type＝IMAGE，不是影片貼文" in capsys.readouterr().out


def test_影片dry_run不發不寫(monkeypatch, tmp_path, capsys):
    a = mkvideo(tmp_path / "q")
    before = (a / "post.md").read_text()
    rc, res, api = go(monkeypatch, tmp_path, dry=True, api=VideoAPI(), now=VNOW)
    assert rc == 0 and all(c[1] == "GET" for c in api.calls)
    assert (a / "post.md").read_text() == before
    assert "影片 ep.mp4" in capsys.readouterr().out


def test_圖片稿件行為不變_不帶影片參數_回查影片會警告(monkeypatch, tmp_path, capsys):
    a = mkpost(tmp_path / "q")
    p = tc.load(a)
    assert p["media"] == "image" and p["video"] == "" and tc.validate(p) == []
    rc, res, api = go(monkeypatch, tmp_path)
    assert rc == 0
    assert not any(c[4].get("media_type") in ("REELS", "VIDEO") or "video_url" in c[4] for c in api.calls)
    assert not any("cover_url" in c[4] for c in api.calls)
    assert not any("share_to_feed" in c[4] for c in api.calls)  # 只有 REELS 才帶
    # 圖片稿回查到 VIDEO 照舊警告
    b = mkpost(tmp_path / "q2", "20261111_b")
    monkeypatch.setattr(tc, "api", VideoAPI(seq=("FINISHED",)))
    tc.run(dict(ENV), NOW + timedelta(days=1), False, queue=tmp_path / "q2", state_dir=tmp_path / "s2", cfg=CFG)
    assert "不是圖片貼文" in capsys.readouterr().out
    assert "verified_ig: VIDEO" in (b / "post.md").read_text()
    # 圖片稿沒圖照舊擋
    p["images"] = []
    assert any("封面一定要有圖" in e for e in tc.validate(p))


# ---------------- 2026-11-15 每篇專屬關鍵字（Andy：「往後製作影片後面可以補上 留言『XXXX』我就把資訊傳給他，IG Thread 都是」） ----------------

import tc_dm_keys as K  # noqa: E402

URL_2NM = "https://liguligu-puipui.com/#article/tc-2nm"


def _cfg2(tmp_path, legal=True, ready=False):
    """正式設定＋（ready＝True 時）把 2nm 的文章網址填好、法遵待審拿掉。"""
    p = _cfg(tmp_path, legal)
    c = json.loads(p.read_text(encoding="utf-8"))
    if ready:
        c["legal_pending"] = []
        c["threads_reply"]["texts"]["2nm"] = [t.split("https://")[0] + URL_2NM for t in c["threads_reply"]["texts"]["2nm"]]
        c["ig_dm"]["contents"]["2nm"] = "謝謝留言！「2 奈米不是尺寸」完整解說放在這：" + URL_2NM
        c["ig_dm"]["public_fallback"] = True   # 測保底公開回覆的機制本身；正式設定 11-23 起關閉（見下一個測試）
    p.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    return p


def _posted2(tmp_path):
    p = tmp_path / "posted.json"
    p.write_text(json.dumps({"posts": [
        {"id": "20261122_2nm", "ids_threads": "p1", "ids_ig": "m1"},
        {"id": "20261105_quanta", "threads": "https://www.threads.com/@tech_01010909/post/QQQ", "ids_ig": "m2"}]}))
    return p


class KwThreadsAPI(FakeAPI):
    def __init__(self, rows, **kw):
        super().__init__(**kw)
        self.rows = rows

    def __call__(self, platform, method, path, token, params=None):
        if path == "/me/threads":
            return {"data": [{"id": "p1"}, {"id": "p2", "permalink": "https://www.threads.com/@tech_01010909/post/QQQ"}]}
        if path in ("/p1/replies", "/p2/replies"):
            return {"data": self.rows.get(path, [])}
        return super().__call__(platform, method, path, token, params)


def _threads_kw(monkeypatch, tmp_path, rows, legal=True, ready=True):
    api = KwThreadsAPI(rows)
    monkeypatch.setattr(tc, "api", api)
    rc, res = tr.run(dict(ENV), NOW, False, config_path=_cfg2(tmp_path, legal, ready), state_path=tmp_path / "rep.json",
                     posted_path=_posted2(tmp_path))
    return rc, res, [c[4] for c in api.calls if c[4].get("reply_to_id")]


def test_設定_2nm專屬關鍵字與待填條目():
    c = json.loads((Path(__file__).resolve().parent.parent / "social/tc/dm_config.json").read_text(encoding="utf-8"))
    assert "透明" in c["keywords"]                                              # 全域保留
    assert "2奈米" in c["post_keywords"]["2nm"]
    texts = c["threads_reply"]["texts"]["2nm"]
    assert isinstance(texts, list) and 1 <= len(texts) <= 3                      # 2026-11-20 公開回覆統一成「已經將XXX完整資訊給你囉～」，單句也行
    for t in texts + [c["ig_dm"]["contents"]["2nm"]]:
        assert "liguligu-puipui.com/#article/" in t
        for w in ("僅供參考", "未經查證", "網友回報", "網路上說", "據了解", "完整資料"):   # lessons 第 5 條；措辭改「完整解說」
            assert w not in t
        if "2nm" in c["legal_pending"]:
            pass                                                                 # 文章還沒上 main：網址可以還是待填
        else:
            assert "待填" not in t and t.endswith("#article/2026-11-15-tech-2nm")   # 拿掉 legal_pending ＝ 網址一定填好
    assert "完整解說" in c["ig_dm"]["contents"]["2nm"]


def test_專屬關鍵字只觸發該篇_Threads(monkeypatch, tmp_path):
    rows = {"/p1/replies": [{"id": "a1", "text": "2 奈米！", "username": "amy"}],
            "/p2/replies": [{"id": "b1", "text": "2奈米", "username": "bob"}]}       # 廣達那篇留 2奈米：不觸發
    rc, res, sent = _threads_kw(monkeypatch, tmp_path, rows)
    assert rc == 0 and [s["reply_to_id"] for s in sent] == ["a1"]
    assert sent[0]["text"] == "「2 奈米不是尺寸」完整內容請到 IG @tech_01010909 私訊「2奈米」，馬上傳給您!~"   # 回的是這篇的主題
    assert "http" not in sent[0]["text"]


def test_全域關鍵字仍然有效_兩篇都回(monkeypatch, tmp_path):
    rows = {"/p1/replies": [{"id": "a1", "text": "透明", "username": "amy"}],
            "/p2/replies": [{"id": "b1", "text": "求透明", "username": "bob"}]}
    rc, res, sent = _threads_kw(monkeypatch, tmp_path, rows)
    assert sorted(s["reply_to_id"] for s in sent) == ["a1", "b1"]
    by = {s["reply_to_id"]: s["text"] for s in sent}
    assert "「2 奈米不是尺寸」" in by["a1"] and "私訊「2奈米」" in by["a1"]        # 2nm 那篇回 2nm 的主題
    assert by["b1"] == "完整內容請到 IG 私訊我們，馬上傳給您!~"                  # 廣達沒有主題：回預設
    assert all("http" not in t for t in by.values())


def test_文章網址待填或法遵待審_改送預設文字不送半成品(monkeypatch, tmp_path):
    rows = {"/p1/replies": [{"id": "a1", "text": "2奈米", "username": "amy"}, {"id": "a2", "text": "2奈米", "username": "bob"}]}
    c = json.loads((Path(__file__).resolve().parent.parent / "social/tc/dm_config.json").read_text(encoding="utf-8"))
    for case in ("待填", "法遵待審"):
        c2 = json.loads(json.dumps(c))
        if case == "待填":
            c2["threads_reply"]["texts"]["2nm"] = ["謝謝留言！完整解說在這：https://liguligu-puipui.com/#article/【待填：文章 id】"]
        else:
            c2["legal_pending"] = ["2nm"]
        cp = tmp_path / f"cfg_{case}.json"
        cp.write_text(json.dumps(c2, ensure_ascii=False), encoding="utf-8")
        api = KwThreadsAPI(rows)
        monkeypatch.setattr(tc, "api", api)
        tr.run(dict(ENV), NOW, False, config_path=cp, state_path=tmp_path / f"rep_{case}.json", posted_path=_posted2(tmp_path))
        sent = [x[4] for x in api.calls if x[4].get("reply_to_id")]
        assert len(sent) == 2 and all(x["text"] == c["threads_reply"]["ask_ig_default"] for x in sent), case   # 保底：照樣回，用預設


def test_專屬關鍵字_法遵閘照舊只記錄(monkeypatch, tmp_path):
    rows = {"/p1/replies": [{"id": "a1", "text": "2奈米", "username": "amy"}]}
    rc, res, sent = _threads_kw(monkeypatch, tmp_path, rows, legal=False)
    assert sent == [] and res["would_reply"] == 1 and res["replied"] == 0


class KwIGAPI(DMAPI):
    def __call__(self, platform, method, path, token, params=None):
        p = dict(params or {})
        if path == "/222/media":
            self.calls.append((platform, method, path, token, p))
            return {"data": [{"id": "m1"}, {"id": "m2"}]}
        if path in ("/m1/comments", "/m2/comments"):
            self.calls.append((platform, method, path, token, p))
            return {"data": [{"id": "c-" + path[1:3], "text": "2奈米", "timestamp": "2026-11-10T12:00:00+0000",
                              "from": {"id": "u9" if path == "/m1/comments" else "u7"}}]}
        if path.endswith("/replies") and method == "POST":
            self.calls.append((platform, method, path, token, p))
            self.sent.append((path, p["message"]))
            return {"id": "rep"}
        return super().__call__(platform, method, path, token, params)


def test_IG專屬關鍵字只觸發該篇_並送該篇內容(monkeypatch, tmp_path):
    p = _cfg2(tmp_path, ready=True)
    c = json.loads(p.read_text(encoding="utf-8"))
    c["ig_dm"]["follow_gate"] = False                                           # 直接送內容，方便看送了哪篇
    p.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    api = KwIGAPI()
    monkeypatch.setattr(tc, "api", api)
    rc, res = dm.run(dict(ENV), NOW, False, config_path=p, state_path=tmp_path / "s.json", posted_path=_posted2(tmp_path))
    first = [s for s in api.sent if s[0] == {"comment_id": "c-m1"}]
    assert len(first) == 1 and URL_2NM in first[0][1]
    assert not any(s[0] == {"comment_id": "c-m2"} for s in api.sent)            # 廣達那篇留 2奈米：不觸發


def test_IG私訊接不通_保底公開回覆留言加連結(monkeypatch, tmp_path):
    monkeypatch.setattr(dm, "messaging_ctx", lambda uid, tok: (None, "看不到粉絲專頁"))
    api = KwIGAPI()
    monkeypatch.setattr(tc, "api", api)
    rc, res = dm.run(dict(ENV), NOW, False, config_path=_cfg2(tmp_path, ready=True), state_path=tmp_path / "s.json",
                     posted_path=_posted2(tmp_path))
    assert rc == 0 and res["public"] == 1 and res["prompted"] == 0
    cfg = json.loads(_cfg2(tmp_path, ready=True).read_text(encoding="utf-8"))
    assert api.sent == [("/c-m1/replies", "已經將「2 奈米不是尺寸」完整內容私訊您囉!~")]   # 2026-11-23 Andy 指定措辭
    assert "http" not in api.sent[0][1]
    assert not any(c[2].endswith("/messages") or c[2] == "/me/conversations" for c in api.calls)   # 沒有試私訊
    api2 = KwIGAPI()                                                            # 再跑一輪不重複回
    monkeypatch.setattr(tc, "api", api2)
    dm.run(dict(ENV), NOW, False, config_path=_cfg2(tmp_path, ready=True), state_path=tmp_path / "s.json",
           posted_path=_posted2(tmp_path))
    assert api2.sent == []
    # 法遵閘照舊：沒過法遵就只記錄
    api3 = KwIGAPI()
    monkeypatch.setattr(tc, "api", api3)
    rc, res = dm.run(dict(ENV), NOW, False, config_path=_cfg2(tmp_path, legal=False, ready=True),
                     state_path=tmp_path / "s2.json", posted_path=_posted2(tmp_path))
    assert api3.sent == [] and res["would"] == 1


def test_佇列文案的留言關鍵字都有設定_Threads不講私訊():
    q = Path(__file__).resolve().parent.parent / "social" / "tc" / "queue"
    for d in sorted(x for x in q.iterdir() if (x / "post.md").is_file()):
        assert tc.cta_check(tc.load(d)) == [], d.name


def test_交件檢查抓得到沒設的關鍵字與Threads講私訊():
    p = {"id": "20261122_2nm", "caption": "…\n留言「3奈米」，我把完整資料傳給你", "main": "…\n留言「2奈米」，我把完整資料傳給你"}
    w = tc.cta_check(p, {"keywords": ["透明"], "post_keywords": {"2nm": ["2奈米"]}})
    assert any("3奈米" in x for x in w) and any("公開回覆" in x for x in w)
    ok = {"id": "20261122_2nm", "caption": "留言「2奈米」，我把完整解說回覆給你", "main": "留言「2奈米」，我把完整解說回覆給你"}
    old = {"id": "20261122_2nm", "caption": "留言「2奈米」，我把完整資料回覆給你", "main": ""}
    assert any("完整解說" in x for x in tc.cta_check(old, {"keywords": ["透明"], "post_keywords": {"2nm": ["2奈米"]}}))
    assert tc.cta_check(ok, {"keywords": ["透明"], "post_keywords": {"2nm": ["2奈米"]}}) == []
    assert K.slug("20261122_2nm") == "2nm" and K.keywords_for({"keywords": ["透明"], "post_keywords": {"2nm": "2奈米"}}, "x_2nm") == ["透明"]


# ---------------- 2026-11-15 法遵再審：措辭、預設文字、防洗版 ----------------

def test_法遵再審_預設文字與廣達出處句():
    c = json.loads((Path(__file__).resolve().parent.parent / "social/tc/dm_config.json").read_text(encoding="utf-8"))
    assert c["ig_dm"]["contents"]["default"] == "謝謝留言！科技透明圈的整理都放在這：https://liguligu-puipui.com/"
    q = c["ig_dm"]["contents"]["20261105_quanta"]
    assert "出處：網友公開分享，非公司公告；隨單位而異。" in q and "58～69K" in q
    assert "未經查證" not in q and "僅供參考" not in q
    assert c["ig_dm"]["public_max_per_minute"] == 3 and c["ig_dm"]["public_max_per_post_hour"] == 30
    assert "出處：網友公開分享，非公司公告" in (Path(__file__).resolve().parent.parent
                                     / "docs/marketing/channels/tc/andy_style.md").read_text(encoding="utf-8")


def test_回覆輪流_用留言id雜湊_固定可重現且會分散():
    texts = ["甲", "乙", "丙"]
    picks = [K.rotate(texts, f"c{i}") for i in range(60)]
    assert picks == [K.rotate(texts, f"c{i}") for i in range(60)]           # 同一則留言永遠同一句
    assert set(picks) == set(texts)                                         # 三句都會輪到
    import hashlib
    assert K.rotate(texts, "abc") == texts[int(hashlib.sha256(b"abc").hexdigest(), 16) % 3]
    assert K.rotate("單句", "x") == "單句"


def test_Threads回覆依留言輪流不同句(monkeypatch, tmp_path):
    rows = {"/p1/replies": [{"id": f"a{i}", "text": "2奈米", "username": f"u{i}"} for i in range(9)]}
    rc, res, sent = _threads_kw(monkeypatch, tmp_path, rows)
    cfg = json.loads(_cfg2(tmp_path, ready=True).read_text(encoding="utf-8"))
    assert [s["text"] for s in sent] == [K.threads_ask_ig(cfg, "20261122_2nm")] * len(sent)   # 2026-11-23 起固定一句
    assert len(sent) == 9


class ManyIGAPI(KwIGAPI):
    def __init__(self, n, **kw):
        super().__init__(**kw)
        self.n = n

    def __call__(self, platform, method, path, token, params=None):
        if path == "/m1/comments":
            self.calls.append((platform, method, path, token, dict(params or {})))
            return {"data": [{"id": f"c{i}", "text": "2奈米", "timestamp": "2026-11-10T12:00:00+0000",
                              "from": {"id": f"u{i}"}} for i in range(self.n)]}
        if path == "/m2/comments":
            return {"data": []}
        return super().__call__(platform, method, path, token, params)


def test_IG公開回覆防洗版_每分鐘3則_每篇每小時30則(monkeypatch, tmp_path):
    monkeypatch.setattr(dm, "messaging_ctx", lambda uid, tok: (None, "看不到粉絲專頁"))
    cfgp, posted, st = _cfg2(tmp_path, ready=True), _posted2(tmp_path), tmp_path / "s.json"
    total, now = 0, NOW
    for i in range(12):                                                     # 12 輪，每輪間隔 1 分鐘
        api = ManyIGAPI(40)
        monkeypatch.setattr(tc, "api", api)
        rc, res = dm.run(dict(ENV), now + timedelta(minutes=i), False, config_path=cfgp, state_path=st, posted_path=posted)
        assert res["public"] <= 3
        total += res["public"]
    assert total == 30                                                      # 第 11 輪起這篇這小時滿了
    d = json.loads(st.read_text())
    import re as _re
    assert all(_re.fullmatch(r"[0-9a-f]{24}", k) for k in list(d["rate"]) + list(d["comments"]))   # 計數只存雜湊
    api = ManyIGAPI(40)                                                     # 一小時後又可以回
    monkeypatch.setattr(tc, "api", api)
    rc, res = dm.run(dict(ENV), now + timedelta(minutes=75), False, config_path=cfgp, state_path=st, posted_path=posted)
    assert res["public"] == 3


# ---------------- 逐篇檢查（2026-11-17 事故 1） ----------------

def test_一篇壞一篇到時間_到時間的照發_整輪exit0但有alert(monkeypatch, tmp_path):
    q = tmp_path / "q"
    # 壞稿：已到時間、Threads 留言 > 500 字
    bad = mkpost(q, "20261110_bad", when="2026-11-10T09:00+08:00", reply="長" * 600)
    good = mkpost(q, "20261110_good", when="2026-11-10T20:30+08:00")
    rc, res, api = go(monkeypatch, tmp_path)
    assert rc == 0                                                       # 整輪不失敗
    assert res["posted"] == ["20261110_good"] and len(api.posts("ig")) == 1
    assert any("20261110_bad" in x and "超過" in x for x in res["alert"])  # 只標壞的那篇
    assert not any("20261110_good" in x for x in res["alert"])
    assert "status: posted" in (good / "post.md").read_text()
    assert "status: approved" in (bad / "post.md").read_text()


def test_還沒到時間的稿格式錯只警告_不alert不失敗(monkeypatch, tmp_path, capsys):
    q = tmp_path / "q"
    mkpost(q, "20261118_future", when="2026-11-18T12:15+08:00", reply="長" * 600)
    good = mkpost(q, "20261110_good")
    rc, res, api = go(monkeypatch, tmp_path)
    assert rc == 0 and res["posted"] == ["20261110_good"] and res["alert"] == [] and res["errors"] == []
    o = capsys.readouterr().out
    assert "::warning::" in o and "還沒到發文時間" in o
    assert tc.main(["--check", "--queue", str(q)]) == 0
    assert "status: posted" in (good / "post.md").read_text()


def test_留言私訊輪詢獨立成tc_comments_不受發文檢查影響():
    """2026-11-20：留言回覆從 tc_post.yml 拆到 tc_comments.yml（Worker 每 10 分鐘派）；發文工作流不再跑留言步驟，避免兩邊同時改 state/tc。"""
    base = Path(__file__).resolve().parents[1] / ".github/workflows"
    assert "tc_ig_dm.py" not in (base / "tc_post.yml").read_text(encoding="utf-8")
    wf = (base / "tc_comments.yml").read_text(encoding="utf-8")
    assert "scripts/tc_threads_replies.py" in wf and "scripts/tc_ig_dm.py" in wf
    seg = wf.split("Threads 留言關鍵字")[1].split("run:")[0]
    assert "continue-on-error: true" in seg and "if:" not in seg


# ---------------- 容器 ERROR 自動重試（事故 2） ----------------

def test_IG影片容器ERROR一次後重建成功_用同一支影片(monkeypatch, tmp_path):
    sleeps = []
    monkeypatch.setattr(tc, "SLEEP", lambda s: sleeps.append(s))
    a = mkvideo(tmp_path / "q")
    rc, res, api = go(monkeypatch, tmp_path, api=VideoAPI(seq=("ERROR", "FINISHED")), now=VNOW)
    assert rc == 0 and res["posted"] == ["20261115_v"] and res["errors"] == []
    creates = [c for c in api.calls if c[0] == "ig" and c[1] == "POST" and c[2] == "/222/media"]
    assert len(creates) == 2 and creates[0][4] == creates[1][4]           # 同一支影片重建
    assert len(api.posts("ig")) == 1                                       # 只發布一次
    assert any(30 <= x <= 60 for x in sleeps)
    assert "status: posted" in (a / "post.md").read_text()


def test_容器ERROR三次就標error_已發平台不重發(monkeypatch, tmp_path):
    a = mkvideo(tmp_path / "q")
    rc, res, api = go(monkeypatch, tmp_path, api=VideoAPI(seq=("ERROR",)), now=VNOW)
    creates = [c for c in api.calls if c[0] == "ig" and c[1] == "POST" and c[2] == "/222/media"]
    assert rc == 1 and len(creates) == 3 and api.posts("ig") == []        # 1 次 + 重試 2 次
    assert "status: error" in (a / "post.md").read_text() and res["alert"]


def test_IG已發成功_Threads容器ERROR三次_重跑只補Threads(monkeypatch, tmp_path):
    a = mkvideo(tmp_path / "q")

    class OnlyThreadsBad(VideoAPI):
        def __call__(self, platform, method, path, token, params=None):
            r = super().__call__(platform, method, path, token, params)
            if platform == "ig" and isinstance(r, dict) and "status_code" in r:
                return {"status_code": "FINISHED", "status": "FINISHED"}
            return r

    rc, res, api = go(monkeypatch, tmp_path, api=OnlyThreadsBad(seq=("ERROR",)), now=VNOW)
    assert rc == 1 and len(api.posts("ig")) == 1 and api.posts("threads") == []
    assert "done: ig" in (a / "post.md").read_text()
    (a / "post.md").write_text((a / "post.md").read_text().replace("status: error", "status: approved"), encoding="utf-8")
    rc, res, api = go(monkeypatch, tmp_path, api=VideoAPI(), now=VNOW + timedelta(hours=21))
    assert rc == 0 and api.posts("ig") == [] and len(api.posts("threads")) == 2   # IG 不重發


# ---------------- 2026-11-23 公開回覆改一句話、不放網址（Andy：「幫我先把留言回覆改成"已經將XXX完整內容私訊您囉!~"」「Threads請他訊IG」） ----------------

PENDING_POSTS = ["waferflow", "etch", "deposition", "cmp", "metrology", "clean", "icdesign", "foundry"]


def _real_cfg():
    return json.loads((Path(__file__).resolve().parent.parent / "social/tc/dm_config.json").read_text(encoding="utf-8"))


def test_IG公開回覆_每篇帶主題_不含網址():
    c = _real_cfg()
    for code in PENDING_POSTS + ["2nm", "euv", "800v"]:
        t = K.ig_public_ack(c, code)
        topic = K.topic_of(c["threads_reply"]["texts"][code])
        assert topic and t == f"已經將「{topic}」完整內容私訊您囉!~", code
        assert "http" not in t
    assert K.ig_public_ack(c, "20261128_cmp") == "已經將「化學機械研磨：每一層都要磨平」完整內容私訊您囉!~"
    assert c["ig_dm"]["ack_public"] == "已經將「{topic}」完整內容私訊您囉!~"


def test_IG與Threads公開回覆_default與取不到主題():
    c = _real_cfg()
    for code in ("default", "20261105_quanta", "no_such_post", None):   # 沒登記的代號（implant 已在 11-30 排程，改用不存在的鍵）
        assert K.ig_public_ack(c, code) == "已經將完整內容私訊您囉!~"
        assert K.threads_ask_ig(c, code) == "完整內容請到 IG 私訊我們，馬上傳給您!~"
    c2 = json.loads(json.dumps(c))
    c2["legal_pending"] = ["cmp"]                                            # 法遵待審：不帶主題
    assert K.ig_public_ack(c2, "cmp") == "已經將完整內容私訊您囉!~"
    c2["threads_reply"]["texts"]["etch"] = ["【待填】"]
    assert K.threads_ask_ig(c2, "etch") == "完整內容請到 IG 私訊我們，馬上傳給您!~"


def test_Threads公開回覆_請到IG私訊該篇關鍵字_不含網址():
    c = _real_cfg()
    for code in PENDING_POSTS:
        t = K.threads_ask_ig(c, code)
        topic = K.topic_of(c["threads_reply"]["texts"][code])
        kw = c["post_keywords"][code][0]
        assert t == f"「{topic}」完整內容請到 IG @tech_01010909 私訊「{kw}」，馬上傳給您!~", code
        assert "http" not in t
    c2 = json.loads(json.dumps(c))
    c2["threads_reply"]["ig_handle"] = ""                                     # 沒有帳號名稱：寫 IG「科技透明圈」
    assert K.threads_ask_ig(c2, "cmp") == "「化學機械研磨：每一層都要磨平」完整內容請到 IG「科技透明圈」私訊「研磨」，馬上傳給您!~"
    c2["post_keywords"].pop("cmp")                                            # 沒有專屬關鍵字：用全域「透明」
    assert "私訊「透明」" in K.threads_ask_ig(c2, "cmp")


def test_佇列每篇都對得到主題():
    c = _real_cfg()
    q = Path(__file__).resolve().parent.parent / "social" / "tc" / "queue"
    for d in sorted(x for x in q.iterdir() if (x / "post.md").is_file()):
        if K.slug(d.name) in c["post_keywords"] and not K.in_pending(d.name, c.get("legal_pending")):
            assert K.topic_for(c, d.name), d.name   # 法遵待審的篇刻意不給主題（改送預設文字），不算缺


def test_IG公開回覆_正式設定已關閉_改由Meta規則():
    """2026-11-23 Andy：「關掉 IG 公開回覆」——IG 留言的公開回覆與私訊改由 Meta Business Suite 規則負責。"""
    c = json.loads((Path(__file__).resolve().parent.parent / "social/tc/dm_config.json").read_text(encoding="utf-8"))
    assert c["ig_dm"]["public_fallback"] is False
    assert c["threads_reply"]["enabled"] is True   # Threads 公開回覆照舊
