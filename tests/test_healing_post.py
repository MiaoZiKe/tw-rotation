"""頻道④談晴說礙自動發文（scripts/healing_post.py）：空跑、取下一則、不重發、開關、缺權杖、短效換長效、權杖不外洩。"""
import json
from datetime import datetime, timedelta, timezone

import pytest

from scripts import healing_post as hp
from scripts import meta_token_refresh as mtr

TPE = timezone(timedelta(hours=8))
NOW = datetime(2026, 11, 10, 20, 30, tzinfo=TPE)
TOK_I, TOK_T = "IGQ_HEALING_SECRET_aaaaaaaaaaaa", "THQ_HEALING_SECRET_bbbbbbbbbbbb"
ENV = {"HEALING_IG_ACCESS_TOKEN": TOK_I, "HEALING_THREADS_ACCESS_TOKEN": TOK_T,
       "HEALING_IG_USER_ID": "9001", "HEALING_THREADS_USER_ID": "9002"}


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    hp.SP._SECRETS.clear()
    monkeypatch.setattr(hp.SP, "_sleep", lambda s: None)


def mk_item(q, name, status="approved", n=3, publish_at=None, platforms=("ig", "threads"), caption="今天的一小段晴？"):
    d = q / name
    d.mkdir(parents=True)
    for i in range(1, n + 1):
        (d / f"{i}.png").write_bytes(b"x")
        (d / f"{i}.jpg").write_bytes(b"x")
    (d / "caption.txt").write_text(caption, encoding="utf-8")
    (d / "meta.json").write_text(json.dumps({"platforms": list(platforms), "status": status,
                                             "publish_at": publish_at}), encoding="utf-8")
    return d


@pytest.fixture
def box(tmp_path, monkeypatch):
    q, st = tmp_path / "queue", tmp_path / "state"
    q.mkdir()
    quota = tmp_path / "post_quota.json"
    quota.write_text('{"live": true, "per_day": 1}', encoding="utf-8")
    monkeypatch.setattr(hp, "ROOT", tmp_path)       # public_url 用 ROOT 算相對路徑
    calls = []

    def fake_ig(uid, token, urls, caption):
        calls.append(("ig", uid, token, list(urls), caption))
        return {"id": "ig1", "link": "https://www.instagram.com/p/AAA/"}

    def fake_th(uid, token, text, urls):
        calls.append(("threads", uid, token, list(urls), text))
        return {"id": "th1", "link": "https://www.threads.com/@x/post/BBB"}

    def fake_ver(p):
        def f(uid, token, urls, text):
            calls.append(("verify-" + p, uid, token, list(urls), text))
            return "c-" + p
        return f

    def go(env=ENV, dry=False, now=NOW, pubs=None, check=lambda u, w: None, vers=None):
        return hp.run(dict(env), now, dry, queue=q, state=st, quota_path=quota,
                      publishers=pubs or {"ig": fake_ig, "threads": fake_th}, check=check,
                      saver=lambda *a: True, verifiers=vers or {"ig": fake_ver("ig"), "threads": fake_ver("threads")})
    # Threads 權杖檢查會打 refresh：預設回同一把（長效、字串不變）
    monkeypatch.setattr(hp.SP, "http", lambda m, url, **kw: {"access_token": kw["params"]["access_token"],
                                                            "expires_in": 5184000})
    return {"q": q, "st": st, "quota": quota, "calls": calls, "go": go}


def posted(box):
    return json.loads((box["st"] / "posted.json").read_text(encoding="utf-8"))


def test_缺權杖空跑不呼叫任何端點(box, monkeypatch, capsys):
    mk_item(box["q"], "20261108_intro")

    def boom(*a, **k):
        raise AssertionError("空跑不准呼叫 Meta")
    monkeypatch.setattr(hp.SP, "http", boom)
    # 頻道①的權杖就算在環境裡也絕不能用
    rc, res = box["go"](env={"IG_ACCESS_TOKEN": "CH1_IG", "THREADS_ACCESS_TOKEN": "CH1_TH"})
    assert rc == 0 and not box["calls"]
    assert "等待 Andy 設定權杖" in res["summary"]
    assert not (box["st"] / "posted.json").exists()
    out = capsys.readouterr().out
    assert "raw.githubusercontent.com" in out and "1.jpg" in out and "1.png" in out and "今天的一小段晴" in out


def test_dry_run有權杖也不發(box):
    mk_item(box["q"], "20261108_intro")
    rc, res = box["go"](dry=True)
    assert rc == 0 and not box["calls"] and res["mode"] == "dry-run"
    assert not (box["st"] / "posted.json").exists() and not (box["st"] / "last_run.json").exists()


def test_發最早一則並記紀錄_不重發(box):
    mk_item(box["q"], "20261109_b")
    mk_item(box["q"], "20261108_a")
    rc, res = box["go"]()
    assert rc == 0 and res["item"] == "20261108_a"
    kinds = [c[0] for c in box["calls"]]
    assert kinds == ["verify-ig", "ig", "verify-threads", "threads"]      # 權杖第一次出現：先驗證才發
    v = json.loads((box["st"] / "verify.json").read_text(encoding="utf-8"))
    assert v["ig"]["verified"] and v["threads"]["verified"]
    box["calls"][:] = [c for c in box["calls"] if not c[0].startswith("verify")]
    ig = box["calls"][0]
    assert ig[1] == "9001" and ig[2] == TOK_I and all(u.endswith(".jpg") for u in ig[3]) and len(ig[3]) == 3
    th = box["calls"][1]
    assert th[1] == "9002" and all(u.endswith(".png") for u in th[3])
    p = posted(box)
    assert p["20261108_a"]["ig"]["link"].startswith("https://www.instagram.com/")
    meta = json.loads((box["q"] / "20261108_a" / "meta.json").read_text(encoding="utf-8"))
    assert meta["status"] == "posted" and "ig" in meta["urls"]
    # 同一天再跑：額度用完，不發第二則
    box["calls"].clear()
    rc, res = box["go"]()
    assert rc == 0 and not box["calls"] and "per_day" in res["summary"]
    # 隔天：發下一則，不會重發第一則
    rc, res = box["go"](now=NOW + timedelta(days=1))
    assert res["item"] == "20261109_b" and [c[0] for c in box["calls"]] == ["ig", "threads"]   # 驗證過了不再驗


def test_佇列空(box):
    mk_item(box["q"], "20261108_draft", status="draft")
    rc, res = box["go"]()
    assert rc == 0 and "佇列已空" in res["summary"] and not box["calls"]


def test_開關false略過(box):
    mk_item(box["q"], "20261108_intro")
    box["quota"].write_text('{"live": false, "per_day": 1}', encoding="utf-8")
    rc, res = box["go"]()
    assert rc == 0 and not box["calls"] and "開關關閉" in res["summary"]


def test_publish_at未到看下一則(box):
    mk_item(box["q"], "20261108_later", publish_at="2026-11-20T20:27+08:00")
    mk_item(box["q"], "20261109_now")
    rc, res = box["go"]()
    assert res["item"] == "20261109_now"


def test_一個平台失敗_紅燈_下次只補那個平台(box):
    mk_item(box["q"], "20261108_intro")
    n = {"k": 0}

    def bad_th(uid, token, text, urls):
        n["k"] += 1
        raise RuntimeError("HTTP 500 " + token)       # 錯誤訊息裡有權杖也要被遮掉
    pubs = {"ig": lambda uid, t, urls, c: {"id": "ig1", "link": "L1"}, "threads": bad_th}
    rc, res = box["go"](pubs=pubs)
    assert rc == 1 and "threads" in res["errors"] and TOK_T not in res["errors"]["threads"]
    last = (box["st"] / "last_run.json").read_text(encoding="utf-8")
    assert TOK_T not in last and TOK_I not in last
    assert set(posted(box)["20261108_intro"]) >= {"ig", "at"}
    # 同一天再跑（21:57 保底）：發一半的那則照補，不受 per_day 擋，而且 IG 不會重發
    box["calls"].clear()
    rc, res = box["go"](now=NOW + timedelta(hours=1, minutes=27))
    assert rc == 0 and [c[0] for c in box["calls"] if not c[0].startswith("verify")] == ["threads"]


def test_只有一把權杖_只發那個平台(box):
    mk_item(box["q"], "20261108_intro")
    env = {"HEALING_IG_ACCESS_TOKEN": TOK_I, "HEALING_IG_USER_ID": "9001"}
    rc, res = box["go"](env=env)
    assert rc == 0 and [c[0] for c in box["calls"]] == ["verify-ig", "ig"]
    assert any("threads 沒有權杖" in n for n in res["notes"])


def test_USER_ID沒填_用權杖查(box, monkeypatch):
    mk_item(box["q"], "20261108_intro")

    def http(m, url, **kw):
        if url.endswith("/me"):
            return {"id": "77777777"} if "threads" in url else {"user_id": "88888888"}
        return {"access_token": kw["params"]["access_token"], "expires_in": 5184000}
    monkeypatch.setattr(hp.SP, "http", http)
    rc, _ = box["go"](env={"HEALING_IG_ACCESS_TOKEN": TOK_I, "HEALING_THREADS_ACCESS_TOKEN": TOK_T})
    assert rc == 0 and box["calls"][1][1] == "88888888" and box["calls"][3][1] == "77777777"


def test_Threads短效自動換長效並寫回(monkeypatch):
    seen, saved = [], []

    def http(m, url, **kw):
        seen.append(url)
        if "refresh_access_token" in url:
            raise RuntimeError("HTTP 400 token 不能續")
        return {"access_token": "THQ_LONG_NEW_cccccccccccc", "expires_in": 5184000}
    monkeypatch.setattr(hp.SP, "http", http)
    notes = []
    env = {"THREADS_APP_SECRET": "APPSECRET_dddd", "META_SECRETS_PAT": "PAT_eeee"}
    new = hp.threads_token_check("THQ_SHORT", env, notes, saver=lambda *a: saved.append(a) or True)
    assert new == "THQ_LONG_NEW_cccccccccccc" and any("access_token" in u for u in seen)
    assert saved and saved[0][0] == "HEALING_THREADS_ACCESS_TOKEN_AUTO"
    # 沒有 app secret：照用原權杖，摘要提醒換長效
    notes = []
    assert hp.threads_token_check("THQ_SHORT", {}, notes) == "THQ_SHORT"
    assert any("短效" in n for n in notes)


def test_首篇佇列格式正確():
    q = hp.QUEUE
    it = hp.read_item(q / "20261108_intro")
    assert hp.validate(it) == [] and it["images"] == ["1.png", "2.png", "3.png"]
    assert all((q / "20261108_intro" / f).exists() for f in hp.ig_files(it))
    assert it["meta"]["publish_at"] is None and it["platforms"] == ["ig", "threads"]


def test_續期涵蓋頻道四權杖():
    assert mtr.PLATFORMS["healing_threads"]["env"] == "HEALING_THREADS_ACCESS_TOKEN"
    assert mtr.PLATFORMS["healing_ig"]["env"] == "HEALING_IG_ACCESS_TOKEN"
    assert mtr.PLATFORMS["threads"]["env"] == "THREADS_ACCESS_TOKEN"     # 頻道①不動


def test_驗證模式失敗_不發文_紅燈(box):
    mk_item(box["q"], "20261108_intro")

    def bad(uid, token, urls, text):
        raise RuntimeError("HTTP 400 media 抓不到 " + token)
    rc, res = box["go"](vers={"ig": bad, "threads": bad})
    assert rc == 1 and not [c for c in box["calls"] if c[0] in ("ig", "threads")]
    assert "驗證模式失敗" in res["errors"]["ig"] and TOK_I not in res["errors"]["ig"]
    assert not (box["st"] / "verify.json").exists()
    assert not (box["st"] / "posted.json").exists()


def test_mode_verify_只建容器(box):
    mk_item(box["q"], "20261108_intro")
    seen = []
    vers = {p: (lambda p: lambda uid, t, urls, x: seen.append(p) or "c1")(p) for p in ("ig", "threads")}
    rc, res = hp.run_verify(dict(ENV), NOW, queue=box["q"], state=box["st"], check=lambda u, w: None,
                            saver=lambda *a: True, verifiers=vers)
    assert rc == 0 and seen == ["ig", "threads"] and "通過" in res["summary"]
    assert hp.is_verified(box["st"], "ig") and hp.is_verified(box["st"], "threads")
    # 沒權杖：不跑、綠燈
    rc, res = hp.run_verify({}, NOW, queue=box["q"], state=box["st"], verifiers=vers)
    assert rc == 0 and "等待 Andy" in res["summary"]


def _posted_one(box):
    box["st"].mkdir(parents=True, exist_ok=True)
    (box["st"] / "posted.json").write_text(json.dumps({"20261108_intro": {
        "ig": {"id": "IG1", "link": "https://www.instagram.com/p/AAA/"},
        "threads": {"id": "TH1", "link": "https://www.threads.com/@x/post/BBB"}, "at": "2026-11-10T20:30"}}),
        encoding="utf-8")


def test_刪文_Threads成功_IG不支援列手動(box):
    _posted_one(box)
    got = []

    def deleter(p, mid, token):
        got.append((p, mid, token))
        if p == "ig":
            raise RuntimeError("HTTP 400 Unsupported delete request")
        return {"success": True}
    rc, res = hp.run_delete(dict(ENV), NOW, "20261108_intro", state=box["st"], deleter=deleter)
    assert rc == 0 and ("threads", "TH1", TOK_T) in got
    p = posted(box)["20261108_intro"]
    assert p["threads"].get("deleted") and not p["ig"].get("deleted")
    assert any("IG 無法用 API 刪除，需手動" in n for n in res["notes"])
    man = json.loads((box["st"] / "manual_delete.json").read_text(encoding="utf-8"))
    assert man[0]["id"] == "IG1"
    # 再刪一次：Threads 已標 deleted 不再呼叫
    got.clear()
    hp.run_delete(dict(ENV), NOW, "20261108_intro", platforms=("threads",), state=box["st"], deleter=deleter)
    assert not got


def test_刪文_用貼文id_與空跑(box):
    _posted_one(box)
    got = []
    rc, res = hp.run_delete(dict(ENV), NOW, "TH1", dry_run=True, state=box["st"],
                            deleter=lambda *a: got.append(a))
    assert rc == 0 and not got and "TH1" in res["summary"]
    rc, res = hp.run_delete(dict(ENV), NOW, "TH1", state=box["st"], deleter=lambda *a: got.append(a) or {})
    assert rc == 0 and got[0][:2] == ("threads", "TH1") and posted(box)["20261108_intro"]["threads"]["deleted"]


def test_Threads真發測試再刪(box):
    mk_item(box["q"], "20261108_intro")
    order = []

    def pub(uid, token, text, urls):
        order.append(("pub", text))
        return {"id": "T9", "link": "https://www.threads.com/@x/post/T9"}
    rc, res = hp.run_test_delete(dict(ENV), NOW, queue=box["q"], state=box["st"], check=lambda u, w: None,
                                 saver=lambda *a: True, publisher=pub,
                                 deleter=lambda p, mid, t: order.append(("del", p, mid)) or {"success": True})
    assert rc == 0 and order[0][0] == "pub" and order[1] == ("del", "threads", "T9")
    t = json.loads((box["st"] / "tests.json").read_text(encoding="utf-8"))[-1]
    assert t["published"] and t["deleted"] and t["seconds"] < 60
    assert not (box["st"] / "posted.json").exists()      # 測試貼文不進正式紀錄
