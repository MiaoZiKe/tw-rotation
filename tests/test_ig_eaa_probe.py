"""系統用戶權杖（EAA，只指派 IG 帳號＋廣告帳號、沒有粉絲專頁）找 IG 帳號編號的多路徑探查（2026-11-10）。
/me/accounts 回 0 個 → 改從 debug_token 授權範圍、assigned_instagram_accounts、廣告帳號找；以 username 對頻道帳號；
驗證模式逐一建容器、第一個 FINISHED 的路名記進 verify.json（不記編號），權杖與完整編號一律不外洩。"""
import json
from datetime import datetime, timedelta, timezone

import pytest

from scripts import healing_post as hp
from scripts import healing_comments as hc

TPE = timezone(timedelta(hours=8))
NOW = datetime(2026, 11, 10, 21, 0, tzinfo=TPE)
EAA = "EAAsystemUSERtoken_zzzzzzzzzzzzzzzzzz"
F = hp.FB_HOST
IG_TALK, IG_TECH, IG_CAF, IG_LEGACY = "17841400000001111", "17841400000002222", "17841400000003333", "9990000004444"
USERNAMES = {IG_TALK: "talk_01010909", IG_TECH: "Tech_01010909"}


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    hp.SP._SECRETS.clear()
    monkeypatch.setattr(hp.SP, "_sleep", lambda s: None)
    hc._PAGE.clear()


def sys_user_http(calls, bad_container=()):
    def http(method, url, **kw):
        prm = dict(kw.get("params") or {})
        calls.append((method, url, prm, dict(kw.get("data") or {})))
        if url == f"{F}/me":
            return [{"id": "1220000000005555", "name": "Aito Post 系統用戶"}]   # 實測：系統用戶 /me 回陣列
        if url == f"{F}/me/accounts":
            return {"data": []}
        if url == f"{F}/me/permissions":
            return {"data": [{"permission": x, "status": "granted"} for x in
                             ("ads_management", "ads_read", "instagram_basic", "instagram_manage_messages",
                              "instagram_manage_comments", "instagram_content_publish")]}
        if url == f"{F}/debug_token":
            return {"data": {"type": "SYSTEM_USER", "expires_at": 0, "is_valid": True, "granular_scopes": [
                {"scope": "instagram_basic", "target_ids": [IG_TALK, IG_TECH]},
                {"scope": "instagram_content_publish", "target_ids": [IG_TALK, IG_TECH]},
                {"scope": "ads_read"}]}}
        if url == f"{F}/1220000000005555/assigned_instagram_accounts":
            return {"data": [{"id": IG_CAF, "username": "caffaine.ai"}]}
        if url == f"{F}/1220000000005555/assigned_pages":
            raise RuntimeError("HTTP 400 {\"message\": \"(#100) Missing permissions\"}")
        if url == f"{F}/me/businesses":
            raise RuntimeError("HTTP 403 {\"message\": \"(#200) Requires business_management permission\"}")
        if url == f"{F}/me/adaccounts":
            return {"data": [{"id": "act_77", "name": "廣告帳號"}]}
        if url == f"{F}/act_77/instagram_accounts":
            return {"data": [{"id": IG_LEGACY, "username": "Tech_01010909"}]}
        if url == f"{F}/act_77/connected_instagram_accounts":
            return {"data": [{"id": IG_TECH}]}
        if method == "GET" and prm.get("fields") == "username":
            return {"username": USERNAMES.get(url.rsplit("/", 1)[1], "")}
        if method == "POST" and url.endswith("/media"):
            uid = url.rsplit("/", 2)[1]
            if uid in bad_container:
                raise RuntimeError("HTTP 400 {\"message\": \"Invalid user id\", \"code\": 100}")
            return {"id": "c%d" % len(calls)}
        if method == "GET" and prm.get("fields") == "status_code":
            return {"status_code": "FINISHED"}
        return {}
    return http


def test_多路徑探查_粉絲專頁0個也找得到(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(hp.SP, "http", sys_user_http(calls))
    probe = []
    c = hp.fb_ig_candidates(EAA, probe)
    got = {(x["id"], x["username"], x["via"]) for x in c}
    assert (IG_TALK, "talk_01010909", "granular") in got and (IG_TECH, "Tech_01010909", "granular") in got
    assert (IG_CAF, "caffaine.ai", "assigned") in got and (IG_LEGACY, "Tech_01010909", "ads") in got
    assert len(c) == 4                                           # IG_TECH 在廣告帳號又出現一次 → 去重
    text = "\n".join(probe)
    assert "失敗" in text and "business_management" in text      # 失敗的路徑有記錄、不中斷
    assert "粉絲專頁 0 個" in text and "…1111" in text
    out = "\n".join(x for x in capsys.readouterr().out.splitlines() if not x.startswith("::add-mask::"))
    assert EAA not in out + text and IG_TALK not in text and IG_CAF not in text


def test_依帳號名挑_優先用驗證通過的路(monkeypatch):
    calls = []
    monkeypatch.setattr(hp.SP, "http", sys_user_http(calls))
    c = hp.fb_ig_candidates(EAA)
    assert hp.ig_choices(c, "tech_01010909")[0] == [IG_TECH, IG_LEGACY]
    assert hp.ig_choices(c, "tech_01010909", "ads")[0] == [IG_LEGACY, IG_TECH]
    assert hp.ig_choices(c, "caffaine.ai")[0] == [IG_CAF]
    assert hp.ig_choices(c, "talk_01010909")[0] == [IG_TALK]
    assert hp.ig_choices(c, "shrimp_01010909")[0] == []         # 多個又對不上 → 不猜
    assert hp.ig_choices([], "a")[0] == [] and "所有路徑" in hp.ig_choices([], "a")[1]
    assert hp.resolve_uid("ig", "", EAA, "CAFFAINE_") == IG_CAF
    assert hp.resolve_uid("ig", "123", EAA, "CAFFAINE_") == "123"   # *_IG_USER_ID 有填仍優先


def _queue(tmp_path):
    q, st = tmp_path / "queue", tmp_path / "state"
    d = q / "20261110_a"
    d.mkdir(parents=True)
    for i in (1, 2):
        (d / f"{i}.png").write_bytes(b"x")
        (d / f"{i}.jpg").write_bytes(b"x")
    (d / "caption.txt").write_text("內文", encoding="utf-8")
    (d / "meta.json").write_text(json.dumps({"platforms": ["ig"], "status": "approved"}), encoding="utf-8")
    return q, st


def test_verify_逐一建容器_第一個失敗換下一個_記路名(tmp_path, monkeypatch, capsys):
    q, st = _queue(tmp_path)
    monkeypatch.setattr(hp, "ROOT", tmp_path)
    calls = []
    monkeypatch.setattr(hp.SP, "http", sys_user_http(calls, bad_container={IG_TECH}))
    rc, res = hp.run_verify({"TECH_IG_ACCESS_TOKEN": EAA}, NOW, queue=q, state=st, check=lambda u, w: None,
                            prefix="TECH_")
    assert rc == 0, res
    assert not any(c[1].endswith("media_publish") for c in calls)            # 驗證不發布
    assert any(f"/{IG_LEGACY}/media" in c[1] for c in calls if c[0] == "POST")
    v = json.loads((st / "verify.json").read_text())
    assert v["ig"]["verified"] and v["ig"]["via"] == "ads" and IG_LEGACY not in json.dumps(v)
    notes = "\n".join(res["notes"])
    assert "建容器失敗" in notes and "缺發文必要權限" not in notes             # 沒有粉絲專頁權限不算缺
    assert "廣告帳號" in res["summary"]
    out = "\n".join(x for x in capsys.readouterr().out.splitlines() if not x.startswith("::add-mask::"))
    blob = out + json.dumps(res, ensure_ascii=False) + (st / "last_run.json").read_text()
    assert EAA not in blob and IG_TECH not in blob and IG_LEGACY not in blob
    # 正式發文：用驗證通過的那條路
    assert hp._live_token("ig", {}, {"ig": EAA}, [], None, "TECH_", st)[1] == IG_LEGACY


def test_verify_全部建容器失敗_回報Meta原文(tmp_path, monkeypatch):
    q, st = _queue(tmp_path)
    monkeypatch.setattr(hp, "ROOT", tmp_path)
    calls = []
    monkeypatch.setattr(hp.SP, "http", sys_user_http(calls, bad_container={IG_CAF}))
    rc, res = hp.run_verify({"CAFFAINE_IG_ACCESS_TOKEN": EAA}, NOW, queue=q, state=st, check=lambda u, w: None,
                            prefix="CAFFAINE_")
    assert rc == 1 and "Invalid user id" in res["errors"]["ig"]
    assert not (st / "verify.json").exists() or "ig" not in json.loads((st / "verify.json").read_text())


def test_留言_沒有粉絲專頁改用探查(monkeypatch):
    calls = []
    monkeypatch.setattr(hp.SP, "http", sys_user_http(calls))
    monkeypatch.setattr(hc.SP, "http", sys_user_http(calls))
    assert hc.me(EAA, "CAFFAINE_")["id"] == IG_CAF
