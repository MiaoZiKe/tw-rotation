"""IG 權杖兩種都吃（2026-11-10）：EAA（Facebook 登入）走 graph.facebook.com，/me/accounts 找 IG 商業帳號；
verify 印權限與粉絲專頁診斷；留言私訊用專頁權杖；續期沒有 app secret 就跳過。權杖字元一律不外洩。"""
import json
from datetime import datetime, timedelta, timezone

import pytest

from scripts import healing_post as hp
from scripts import healing_comments as hc
from scripts import meta_token_refresh as mtr

TPE = timezone(timedelta(hours=8))
NOW = datetime(2026, 11, 10, 20, 30, tzinfo=TPE)
EAA = "EAAsecretFBTOKEN_zzzzzzzzzzzzzzzz"
PAGE_TOK = "EAApageTOKEN_yyyyyyyyyyyyyyyyy"
PAGES = {"data": [
    {"name": "別的專頁", "id": "p1", "access_token": "EAAother_page_tok_xxxxxxxx",
     "instagram_business_account": {"id": "17841400000000001", "username": "other_acct"}},
    {"name": "科技透明圈", "id": "p2", "access_token": PAGE_TOK,
     "instagram_business_account": {"id": "17841400000000002", "username": "tech_01010909"}},
    {"name": "沒連 IG", "id": "p3", "access_token": "EAAp3_tok_wwwwwwwwwwwwwwww"},
]}


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    hp.SP._SECRETS.clear()
    monkeypatch.setattr(hp.SP, "_sleep", lambda s: None)
    hc._PAGE.clear()


def fake_http(calls, perms=None, pages=PAGES, expires=0):
    def http(method, url, **kw):
        calls.append((method, url, dict(kw.get("params") or {}), dict(kw.get("data") or {})))
        if url.endswith("/me/accounts"):
            return pages
        if url.endswith("/me/permissions"):
            return {"data": perms if perms is not None else [
                {"permission": x, "status": "granted"} for x in hp.FB_PERMS]}
        if url.endswith("/debug_token"):
            return {"data": {"type": "USER", "expires_at": expires, "is_valid": True}}
        if url.endswith("/media") and method == "POST":
            return {"id": "c%d" % len(calls)}
        if method == "GET" and "fields" in (kw.get("params") or {}) and kw["params"]["fields"] == "status_code":
            return {"status_code": "FINISHED"}
        return {}
    return http


def test_主機依權杖類型():
    assert hp.ig_host(EAA) == hp.FB_HOST and "graph.facebook.com" in hp.FB_HOST
    assert hp.ig_host("IGAAxxxx") == hp.SP.IG_HOST


def test_帳號名對應與不猜():
    lst = [{"name": "A", "ig_id": "1", "ig_username": "a"}, {"name": "B", "ig_id": "2", "ig_username": "Tech_01010909"}]
    assert hp.pick_ig(lst, "tech_01010909")[0] == "2"           # 大小寫不拘
    assert hp.pick_ig(lst, "caffaine.ai")[0] == ""                # 多個又對不上 → 不猜
    assert hp.pick_ig(lst[:1], "caffaine.ai")[0] == "1"           # 只有一個 → 用它但警告
    assert "不同" in hp.pick_ig(lst[:1], "caffaine.ai")[1]
    assert hp.pick_ig([{"name": "X", "ig_id": "", "ig_username": ""}], "a")[0] == ""
    assert hp.channel_account("TECH_") == "Tech_01010909"
    assert hp.channel_account("CAFFAINE_") == "caffaine.ai"


def test_resolve_uid_用粉絲專頁找_有填USER_ID優先(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(hp.SP, "http", fake_http(calls))
    assert hp.resolve_uid("ig", "", EAA, "TECH_") == "17841400000000002"
    assert hp.resolve_uid("ig", "555", EAA, "TECH_") == "555"
    out = capsys.readouterr().out
    assert EAA not in out and "::add-mask::17841400000000002" in out


def test_verify_走facebook並輸出診斷_不外洩(tmp_path, monkeypatch, capsys):
    q, st = tmp_path / "queue", tmp_path / "state"
    d = q / "20261110_a"
    d.mkdir(parents=True)
    for i in (1, 2):
        (d / f"{i}.png").write_bytes(b"x")
        (d / f"{i}.jpg").write_bytes(b"x")
    (d / "caption.txt").write_text("內文", encoding="utf-8")
    (d / "meta.json").write_text(json.dumps({"platforms": ["ig"], "status": "approved"}), encoding="utf-8")
    monkeypatch.setattr(hp, "ROOT", tmp_path)
    calls = []
    monkeypatch.setattr(hp.SP, "http", fake_http(calls, perms=[
        {"permission": "instagram_basic", "status": "granted"},
        {"permission": "pages_show_list", "status": "granted"},
        {"permission": "instagram_content_publish", "status": "declined"}]))
    rc, res = hp.run_verify({"TECH_IG_ACCESS_TOKEN": EAA}, NOW, queue=q, state=st, check=lambda u, w: None,
                            prefix="TECH_")
    assert rc == 0, res
    posts = [c for c in calls if c[0] == "POST"]
    assert posts and all(c[1].startswith("https://graph.facebook.com/") for c in posts)
    assert all("/17841400000000002/media" in c[1] for c in posts)
    assert not any(c[1].endswith("media_publish") for c in calls)            # 驗證不發布
    notes = "\n".join(res["notes"])
    assert "@tech_01010909" in notes and "缺少權限" in notes and "instagram_content_publish" in notes
    assert "缺發文必要權限" in notes
    out = "\n".join(x for x in capsys.readouterr().out.splitlines() if not x.startswith("::add-mask::"))
    blob = out + json.dumps(res, ensure_ascii=False) + (st / "last_run.json").read_text()
    assert EAA not in blob and PAGE_TOK not in blob


def test_診斷_沒連IG與短效(monkeypatch):
    calls = []
    exp = int(datetime.now(timezone.utc).timestamp()) + 3600
    monkeypatch.setattr(hp.SP, "http", fake_http(calls, pages={"data": [{"name": "只有專頁"}]}, expires=exp))
    dg = hp.fb_diag(EAA, "caffaine.ai")
    pb = "\n".join(dg["problems"])
    assert "所有路徑都找不到" in pb and "短效" in pb


def test_刪文走facebook(monkeypatch):
    calls = []
    monkeypatch.setattr(hp.SP, "http", fake_http(calls))
    hp.delete_media("ig", "m1", EAA)
    assert calls[-1][0] == "DELETE" and calls[-1][1] == f"{hp.FB_HOST}/m1"


def test_留言私訊_EAA用專頁權杖(monkeypatch):
    calls = []

    def http(method, url, **kw):
        calls.append((method, url, kw))
        if url.endswith("/me/accounts"):
            return PAGES
        return {}
    monkeypatch.setattr(hc.SP, "http", http)
    acct = hc.me(EAA, "TECH_")
    assert acct["id"] == "17841400000000002"
    hc.private_reply(acct["id"], EAA, "cm1", "嗨")
    m, url, kw = calls[-1]
    assert url == f"{hc.FB}/p2/messages" and kw["params"]["access_token"] == PAGE_TOK
    hc.follows("igsid1", EAA)
    assert calls[-1][1] == f"{hc.FB}/igsid1" and calls[-1][2]["params"]["access_token"] == PAGE_TOK
    hc.comments("med1", EAA)
    assert calls[-1][1] == f"{hc.FB}/med1/comments"


# ---------- 續期（scripts/meta_token_refresh.py）對 EAA 權杖：2026-11-10 改版 ----------
# 實測：系統用戶權杖 graph.facebook.com/me 回空陣列（http_get 當成 {}），之前因此誤報「驗證失敗」、整個工作流變紅。
DAY = 86400


def fb_http(kind="SYSTEM_USER", exp_days=None, app_id="123", good_secrets=("sec_aaaaaaaa",), ig_ok=True,
            new_tok="EAAnewLONGtoken_qqqqqqqqqqqq", self_debug_denied=False):
    calls = []
    now = int(datetime.now(timezone.utc).timestamp())

    def hg(url, params):
        calls.append((url, dict(params)))
        assert "graph.instagram.com" not in url and "graph.threads.net" not in url
        if url.endswith("/me"):
            return {}                                   # 系統用戶：回空陣列 → {}
        if url.endswith("/app"):
            return {"id": app_id}
        if url.endswith("/me/assigned_instagram_accounts"):
            if not ig_ok:
                raise RuntimeError("HTTP 400 Invalid OAuth access token")
            return {"data": [{"id": "17841400000000002", "username": "tech_01010909"}]}
        if url.endswith("/me/accounts"):
            if not ig_ok:
                raise RuntimeError("HTTP 400 Invalid OAuth access token")
            return {"data": []}
        if url.endswith("/debug_token"):
            at = params["access_token"]
            if "|" in at:                               # app 權杖：驗 secret 屬不屬於這個應用程式
                aid, sec = at.split("|", 1)
                if aid != app_id or sec not in good_secrets:
                    raise RuntimeError("HTTP 400 Invalid OAuth access token signature")
            elif self_debug_denied:                     # 11-10 實測：權杖自己打 debug_token 被拒
                raise RuntimeError("HTTP 400 (#100) You must provide an app access token")
            if not ig_ok:
                return {"data": {"is_valid": False}}
            return {"data": {"is_valid": True, "type": kind, "app_id": app_id,
                             "expires_at": 0 if exp_days is None else now + int(exp_days * DAY)}}
        if url.endswith("/oauth/access_token"):
            assert params["grant_type"] == "fb_exchange_token" and params["client_id"] == app_id
            return {"access_token": new_tok, "expires_in": 60 * DAY}
        raise AssertionError("不該呼叫 " + url)
    hg.calls = calls
    return hg


def fb_run(monkeypatch, tmp_path, env, dry=False, check=False, **kw):
    hg = fb_http(**kw)
    monkeypatch.setattr(mtr, "http_get", hg)
    saved = []
    rc, st = mtr.run(dict(env), datetime.now(timezone.utc), dry, state_path=tmp_path / "m.json",
                     saver=lambda n, v, r, p: saved.append((n, v)) or True,
                     pat_checker=lambda p, r: {"ok": True}, check=check)
    return rc, st, saved, hg


def test_續期_EAA系統用戶_me回空陣列也算通過_永不到期不續(tmp_path, monkeypatch):
    rc, st, saved, hg = fb_run(monkeypatch, tmp_path, {"TECH_IG_ACCESS_TOKEN": EAA})
    ps = st["platforms"]["tech_ig"]
    assert rc == 0 and ps["ok"] and ps["status"] == "fb-never-expires" and ps["never_expires"]
    assert not st["alert"] and not saved
    assert not any(u.endswith("/oauth/access_token") for u, _ in hg.calls)
    assert "assigned_instagram_accounts" in ps["via"]
    assert EAA not in (tmp_path / "m.json").read_text()


def test_dry_run_EAA不再誤報(tmp_path, monkeypatch):
    rc, st, saved, _ = fb_run(monkeypatch, tmp_path, {"TECH_IG_ACCESS_TOKEN": EAA}, dry=True)
    assert rc == 0 and st["platforms"]["tech_ig"]["status"] == "dry-run-ok" and not saved
    assert not (tmp_path / "m.json").exists()


def test_EAA權杖失效_紅燈且立即告警(tmp_path, monkeypatch):
    rc, st, _, _ = fb_run(monkeypatch, tmp_path, {"TECH_IG_ACCESS_TOKEN": EAA}, ig_ok=False, check=True)
    assert rc == 1 and st["platforms"]["tech_ig"]["status"] == "fb-invalid" and st["alert"]


def test_EAA使用者權杖_沒有appsecret_寫明需要並到期前告警(tmp_path, monkeypatch):
    rc, st, saved, _ = fb_run(monkeypatch, tmp_path, {"TECH_IG_ACCESS_TOKEN": EAA}, kind="USER", exp_days=40)
    ps = st["platforms"]["tech_ig"]
    assert rc == 0 and ps["status"] == "fb-no-secret" and "META_APP_SECRET" in ps["note"] and not st["alert"]
    assert 39 < ps["days_left"] <= 40
    rc, st, _, _ = fb_run(monkeypatch, tmp_path, {"TECH_IG_ACCESS_TOKEN": EAA}, kind="USER", exp_days=5)
    assert rc == 0 and st["alert"] and "META_APP_SECRET" in st["alert_reasons"][0]


def test_EAA使用者權杖_有META_APP_ID與SECRET_換長效寫回AUTO(tmp_path, monkeypatch):
    env = {"TECH_IG_ACCESS_TOKEN": EAA, "META_APP_ID": "123", "META_APP_SECRET": "sec_aaaaaaaa",
           "META_SECRETS_PAT": "pat_bbbbbbbbbb"}
    rc, st, saved, _ = fb_run(monkeypatch, tmp_path, env, kind="USER", exp_days=40)
    ps = st["platforms"]["tech_ig"]
    assert rc == 0 and ps["status"] == "refreshed" and ps["saved"] == "written"
    assert saved == [("TECH_IG_ACCESS_TOKEN_AUTO", "EAAnewLONGtoken_qqqqqqqqqqqq")]
    assert 59 < ps["days_left"] <= 60


def test_THREADS_APP_SECRET不同應用程式就不用(tmp_path, monkeypatch):
    env = {"TECH_IG_ACCESS_TOKEN": EAA, "THREADS_APP_SECRET": "threads_other_app_secret", "META_SECRETS_PAT": "pat_bbbbbbbbbb"}
    rc, st, saved, hg = fb_run(monkeypatch, tmp_path, env, kind="USER", exp_days=40)
    ps = st["platforms"]["tech_ig"]
    assert rc == 0 and ps["status"] == "fb-no-secret" and "THREADS_APP_SECRET 對不上" in ps["note"] and not saved
    assert not any(u.endswith("/oauth/access_token") for u, _ in hg.calls)


def test_THREADS_APP_SECRET屬於同一個應用程式就拿來換長效(tmp_path, monkeypatch):
    env = {"TECH_IG_ACCESS_TOKEN": EAA, "THREADS_APP_SECRET": "same_app_secret_zz", "META_SECRETS_PAT": "pat_bbbbbbbbbb"}
    rc, st, saved, _ = fb_run(monkeypatch, tmp_path, env, kind="USER", exp_days=40, good_secrets=("same_app_secret_zz",))
    assert rc == 0 and st["platforms"]["tech_ig"]["status"] == "refreshed" and saved


def test_每日檢查_EAA還很久才到期不換_快到期才換(tmp_path, monkeypatch):
    env = {"TECH_IG_ACCESS_TOKEN": EAA, "META_APP_ID": "123", "META_APP_SECRET": "sec_aaaaaaaa", "META_SECRETS_PAT": "p_x"}
    rc, st, saved, _ = fb_run(monkeypatch, tmp_path, env, check=True, kind="USER", exp_days=45)
    assert rc == 0 and st["platforms"]["tech_ig"]["status"] == "fb-ok" and not saved
    rc, st, saved, _ = fb_run(monkeypatch, tmp_path, env, check=True, kind="USER", exp_days=20)
    assert rc == 0 and st["platforms"]["tech_ig"]["status"] == "refreshed" and saved


def test_EAA優先用AUTO(tmp_path, monkeypatch):
    auto = "EAAautoTOKEN_ppppppppppppppppp"
    rc, st, _, hg = fb_run(monkeypatch, tmp_path, {"TECH_IG_ACCESS_TOKEN": EAA, "TECH_IG_ACCESS_TOKEN_AUTO": auto})
    assert st["platforms"]["tech_ig"]["source"] == "auto"
    assert {p["access_token"] for u, p in hg.calls if "|" not in p["access_token"]} == {auto}


def test_發文端IG與Threads都優先用AUTO():
    import scripts.healing_post as hp2
    env = {"CAFFAINE_IG_ACCESS_TOKEN": EAA, "CAFFAINE_IG_ACCESS_TOKEN_AUTO": "EAAauto_ig_rrrrrrrrrrrr",
           "CAFFAINE_THREADS_ACCESS_TOKEN": "THQorig_tttttttttt", "CAFFAINE_THREADS_ACCESS_TOKEN_AUTO": "THQauto_uuuuuuuuuu"}
    t = hp2.tokens(env, "CAFFAINE_")
    assert t == {"ig": "EAAauto_ig_rrrrrrrrrrrr", "threads": "THQauto_uuuuuuuuuu"}
    assert hp2.tokens({"CAFFAINE_IG_ACCESS_TOKEN": EAA}, "CAFFAINE_")["ig"] == EAA


def test_權杖自己讀不到debug_token_用app查編號再用THREADS_APP_SECRET驗證(tmp_path, monkeypatch):
    """11-10 實測：EAA 權杖自己打 debug_token 回 #100 → 用 /app 查應用程式編號，再用 app 權杖讀到期日。"""
    env = {"TECH_IG_ACCESS_TOKEN": EAA, "THREADS_APP_SECRET": "same_app_secret_zz", "META_SECRETS_PAT": "p_x"}
    rc, st, saved, hg = fb_run(monkeypatch, tmp_path, env, self_debug_denied=True, good_secrets=("same_app_secret_zz",))
    ps = st["platforms"]["tech_ig"]
    assert rc == 0 and ps["status"] == "fb-never-expires" and ps["token_type"] == "SYSTEM_USER" and not saved
    assert any(u.endswith("/app") for u, _ in hg.calls)
    # 不同應用程式的 secret：讀不到到期日 → 寫明需要 META_APP_SECRET，仍綠燈
    rc, st, _, _ = fb_run(monkeypatch, tmp_path, dict(env, THREADS_APP_SECRET="other_x"), self_debug_denied=True)
    ps = st["platforms"]["tech_ig"]
    assert rc == 0 and ps["status"] == "fb-no-secret" and ps["days_left"] is None
    assert "讀不到到期日" in ps["note"] and "THREADS_APP_SECRET 對不上" in ps["note"]
