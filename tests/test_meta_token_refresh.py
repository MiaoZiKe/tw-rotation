"""Meta 權杖自動續期（scripts/meta_token_refresh.py）：mock HTTP 與寫回，驗成功、失敗、到期告警、log 不含權杖。"""
import json
from datetime import datetime, timedelta, timezone

import pytest

from scripts import meta_token_refresh as mtr

NOW = datetime(2026, 11, 1, 2, 23, tzinfo=timezone.utc)
TOK_T, TOK_I = "THQ_SECRET_THREADS_TOKEN_aaaaaaaaaaaa", "IGQ_SECRET_IG_TOKEN_bbbbbbbbbbbbbbbb"
NEW_T = "THQ_NEW_THREADS_TOKEN_cccccccccccccccc"
PAT = "PAT_SECRET_dddddddddddddddd"
ENV = {"THREADS_ACCESS_TOKEN": TOK_T, "IG_ACCESS_TOKEN": TOK_I, "GITHUB_REPOSITORY": "o/r"}


@pytest.fixture(autouse=True)
def _clean():
    mtr._SECRETS.clear()


def fake_http(new_for=None, fail_for=(), me_ok=True):
    calls = []

    def f(url, params):
        calls.append((url, dict(params)))
        tok = params["access_token"]
        if "refresh_access_token" in url:
            plat = "threads" if "threads" in url else "ig"
            if plat in fail_for:
                raise RuntimeError("HTTP 400 Session has expired")
            return {"access_token": (new_for or {}).get(plat, tok), "expires_in": 5184000}
        if not me_ok:
            raise RuntimeError("HTTP 190 invalid token")
        return {"id": "1"} if "threads" in url else {"user_id": "2"}
    f.calls = calls
    return f


def go(monkeypatch, tmp_path, env=ENV, dry=False, saver=None, pat=None, **kw):
    monkeypatch.setattr(mtr, "http_get", fake_http(**kw))
    saved = []

    def _saver(name, value, repo, p):
        saved.append((name, value, repo, p))
        return True
    e = dict(env)
    if pat:
        e["META_SECRETS_PAT"] = pat
    rc, st = mtr.run(e, NOW, dry, state_path=tmp_path / "meta_token.json", saver=saver or _saver,
                     pat_checker=lambda p, r: {"present": True, "ok": True,
                                               "expires_at": (NOW + timedelta(days=300)).isoformat()})
    return rc, st, saved


def test_續期成功字串不變(monkeypatch, tmp_path, capsys):
    rc, st, saved = go(monkeypatch, tmp_path)
    assert rc == 0 and st["status"] == "ok" and not saved
    t = st["platforms"]["threads"]
    assert t["ok"] and t["saved"] == "unchanged" and t["days_left"] == 60.0
    disk = (tmp_path / "meta_token.json").read_text()
    out = capsys.readouterr().out
    for s in (TOK_T, TOK_I):
        assert s not in disk
        assert s not in out.replace("::add-mask::" + s, "")


def test_新字串有PAT就寫回AUTO(monkeypatch, tmp_path, capsys):
    rc, st, saved = go(monkeypatch, tmp_path, pat=PAT, new_for={"threads": NEW_T})
    assert rc == 0 and saved == [("THREADS_ACCESS_TOKEN_AUTO", NEW_T, "o/r", PAT)]
    assert st["platforms"]["threads"]["saved"] == "written"
    out = capsys.readouterr().out
    assert "::add-mask::" + NEW_T in out
    body = out.replace("::add-mask::" + NEW_T, "").replace("::add-mask::" + PAT, "")
    for s in (TOK_T, TOK_I, NEW_T, PAT):
        assert s not in body.replace("::add-mask::" + s, "")
    assert NEW_T not in (tmp_path / "meta_token.json").read_text()


def test_優先讀AUTO(monkeypatch, tmp_path):
    env = dict(ENV, THREADS_ACCESS_TOKEN_AUTO=NEW_T)
    monkeypatch.setattr(mtr, "http_get", f := fake_http())
    mtr.run(env, NOW, False, state_path=tmp_path / "s.json", saver=lambda *a: True)
    th = [p["access_token"] for u, p in f.calls if "threads" in u]
    assert th == [NEW_T]


def test_新字串沒PAT就紅燈且告警(monkeypatch, tmp_path):
    rc, st, saved = go(monkeypatch, tmp_path, new_for={"ig": "IGQ_NEW_eeeeeeeeeeeeeeeeeeee"})
    assert rc == 1 and not saved
    assert st["platforms"]["ig"]["status"] == "needs-writeback"
    assert st["alert"] and st["status"] == "bad"     # 到期日未知 → 保守告警


def test_續期失敗但還很久才到期只紅燈不告警(monkeypatch, tmp_path):
    prev = {"platforms": {"threads": {"expires_at": (NOW + timedelta(days=40)).isoformat(), "last_ok_at": "x"}}}
    (tmp_path / "meta_token.json").write_text(json.dumps(prev))
    rc, st, _ = go(monkeypatch, tmp_path, fail_for=("threads",))
    assert rc == 1 and st["platforms"]["threads"]["status"] == "refresh-failed"
    assert st["platforms"]["threads"]["days_left"] == 40.0
    assert not st["alert"] and st["status"] == "warn"


def test_到期前10天仍失敗就告警(monkeypatch, tmp_path):
    prev = {"platforms": {"threads": {"expires_at": (NOW + timedelta(days=8)).isoformat()}}}
    (tmp_path / "meta_token.json").write_text(json.dumps(prev))
    rc, st, _ = go(monkeypatch, tmp_path, fail_for=("threads",))
    assert rc == 1 and st["alert"] and "剩 8.0 天" in st["alert_reasons"][0]


def test_寫回失敗紅燈(monkeypatch, tmp_path):
    rc, st, _ = go(monkeypatch, tmp_path, pat=PAT, new_for={"threads": NEW_T}, saver=lambda *a: False)
    assert rc == 1 and st["platforms"]["threads"]["status"] == "writeback-failed"


def test_dry_run不續期不寫檔(monkeypatch, tmp_path):
    rc, st, saved = go(monkeypatch, tmp_path, dry=True)
    assert rc == 0 and not saved and not (tmp_path / "meta_token.json").exists()
    assert not any("refresh_access_token" in u for u, _ in mtr.http_get.calls)


def test_dry_run權杖失效紅燈(monkeypatch, tmp_path):
    rc, st, _ = go(monkeypatch, tmp_path, dry=True, me_ok=False)
    assert rc == 1


def test_PAT快到期告警(monkeypatch, tmp_path):
    monkeypatch.setattr(mtr, "http_get", fake_http())
    rc, st = mtr.run(dict(ENV, META_SECRETS_PAT=PAT), NOW, False, state_path=tmp_path / "s.json",
                     saver=lambda *a: True,
                     pat_checker=lambda p, r: {"present": True, "ok": True, "expires_at": "2026-11-10 00:00:00 UTC"})
    assert rc == 0 and st["alert"] and "PAT" in st["alert_reasons"][0]


def test_meta_payload告警算一項失敗(monkeypatch, tmp_path):
    import pipeline.build_payload as bp
    (tmp_path / "meta_token.json").write_text(json.dumps(
        {"status": "bad", "alert": True, "platforms": {"threads": {"days_left": 5}}}))
    monkeypatch.setattr(bp.config, "STATE", tmp_path)
    monkeypatch.setattr(bp.freshness, "check", lambda *a, **k: {})
    m = bp.meta_payload("2026-10-30", 10)
    assert "meta_token_refresh" in m["last_run_errors"]
    assert m["meta_token"]["days_left"] == {"threads": 5}


def test_24小時內續過就跳過不打Meta(monkeypatch, tmp_path):
    """2026-11-08：排程晚跑、前面剛手動續過 → 跳過，不亮紅燈；滿 24 小時才真的續。"""
    exp = (NOW + timedelta(days=59)).isoformat()
    prev = {"platforms": {p: {"ok": True, "source_after": "auto", "expires_at": exp,
                              "last_ok_at": (NOW - timedelta(hours=6)).isoformat()} for p in ("threads", "ig")}}
    (tmp_path / "meta_token.json").write_text(json.dumps(prev))
    fh = fake_http(fail_for=("threads", "ig"))
    monkeypatch.setattr(mtr, "http_get", fh)
    rc, st = mtr.run(dict(ENV), NOW, False, state_path=tmp_path / "meta_token.json", saver=lambda *a: True,
                     pat_checker=lambda p, r: {"present": True, "ok": True})
    assert rc == 0 and st["status"] == "ok" and not st["alert"]
    assert all(st["platforms"][p]["status"] == "recent-skip" for p in ("threads", "ig"))
    assert st["platforms"]["threads"]["days_left"] == 59.0
    assert not any("refresh_access_token" in u for u, _ in fh.calls)
    # 滿 24 小時 → 真的去續（這裡 mock 失敗 → 紅燈）
    prev["platforms"]["threads"]["last_ok_at"] = (NOW - timedelta(hours=25)).isoformat()
    (tmp_path / "meta_token.json").write_text(json.dumps(prev))
    rc2, st2 = mtr.run(dict(ENV), NOW, False, state_path=tmp_path / "meta_token.json", saver=lambda *a: True,
                       pat_checker=lambda p, r: {"present": True, "ok": True})
    assert rc2 == 1 and st2["platforms"]["threads"]["status"] == "refresh-failed"


def test_每日檢查_非EAA只驗證不續期_失敗立即告警(monkeypatch, tmp_path):
    """2026-11-10：每天用權杖實際呼叫一次；成功不續期、不動到期日，失敗立即告警（開 issue）。"""
    exp = (NOW + timedelta(days=50)).isoformat()
    prev = {"platforms": {"threads": {"ok": True, "expires_at": exp, "last_ok_at": "2026-10-30T00:00:00+00:00"}}}
    (tmp_path / "meta_token.json").write_text(json.dumps(prev))
    fh = fake_http()
    monkeypatch.setattr(mtr, "http_get", fh)
    rc, st = mtr.run(dict(ENV), NOW, False, state_path=tmp_path / "meta_token.json", saver=lambda *a: True,
                     pat_checker=lambda p, r: {"present": True, "ok": True}, check=True)
    assert rc == 0 and st["mode"] == "check" and not st["alert"]
    assert st["platforms"]["threads"]["status"] == "check-ok" and st["platforms"]["threads"]["days_left"] == 50.0
    assert st["platforms"]["threads"]["last_ok_at"] == "2026-10-30T00:00:00+00:00"
    assert not any("refresh_access_token" in u for u, _ in fh.calls)
    monkeypatch.setattr(mtr, "http_get", fake_http(me_ok=False))
    rc, st = mtr.run(dict(ENV), NOW, False, state_path=tmp_path / "meta_token.json", saver=lambda *a: True,
                     pat_checker=lambda p, r: {"present": True, "ok": True}, check=True)
    assert rc == 1 and st["alert"] and any("每日檢查失敗" in r for r in st["alert_reasons"])
