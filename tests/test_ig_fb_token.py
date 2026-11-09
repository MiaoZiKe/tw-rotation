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


def test_續期_EAA沒有appsecret跳過不紅燈(tmp_path, monkeypatch):
    seen = []

    def hg(url, params):
        seen.append(url)
        if url.endswith("/debug_token"):
            return {"data": {"expires_at": 0}}
        if url.endswith("/me"):
            return {"id": "u1"}
        raise AssertionError("不該呼叫 " + url)
    monkeypatch.setattr(mtr, "http_get", hg)
    rc, st = mtr.run({"TECH_IG_ACCESS_TOKEN": EAA}, datetime.now(timezone.utc), False,
                     state_path=tmp_path / "m.json", pat_checker=lambda p, r: {"ok": True})
    ps = st["platforms"]["tech_ig"]
    assert ps["status"] == "fb-no-secret" and ps["ok"] and rc == 0
    assert all("graph.instagram.com" not in u for u in seen)
    assert EAA not in (tmp_path / "m.json").read_text()


def test_續期_EAA有appsecret換長效並寫回(tmp_path, monkeypatch):
    def hg(url, params):
        if url.endswith("/oauth/access_token"):
            assert params["grant_type"] == "fb_exchange_token"
            return {"access_token": "EAAnewLONGtoken_qqqqqqqqqqqq", "expires_in": 5184000}
        if url.endswith("/me"):
            return {"id": "u1"}
        raise AssertionError(url)
    monkeypatch.setattr(mtr, "http_get", hg)
    saved = []
    rc, st = mtr.run({"TECH_IG_ACCESS_TOKEN": EAA, "META_APP_ID": "123", "META_APP_SECRET": "sec_aaaaaaaa",
                      "META_SECRETS_PAT": "pat_bbbbbbbbbb"}, datetime.now(timezone.utc), False,
                     state_path=tmp_path / "m.json", saver=lambda n, v, r, p: saved.append(n) or True,
                     pat_checker=lambda p, r: {"ok": True})
    assert st["platforms"]["tech_ig"]["status"] == "refreshed" and "TECH_IG_ACCESS_TOKEN_AUTO" in saved
