"""IG 共用防重複發文（2026-11-24）：social_publish.ig_publish_once 與 ig_post／tc_post 的 media_publish 呼叫點。"""
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import social_publish as SP  # noqa: E402
import ig_post as IG  # noqa: E402
import tc_post as TC  # noqa: E402

CAP = "今天外資買超哪些族群\n電子與金融\n#財經"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000")
HIT = {"data": [{"id": "9", "caption": CAP, "timestamp": NOW, "permalink": "https://ig/p/9"}]}
E403 = RuntimeError('HTTP 403 {"code": 4, "error_subcode": 2207051, "is_transient": false}')


@pytest.fixture(autouse=True)
def _nosleep(monkeypatch):
    monkeypatch.setattr(SP, "_sleep", lambda s: None)


def lister_seq(*feeds):
    it = iter(feeds)
    calls = []

    def f():
        calls.append(1)
        v = next(it)
        if isinstance(v, Exception):
            raise v
        return v
    return f, calls


def test_403後帳號已有同文案_只publish一次():
    lister, _ = lister_seq({"data": []}, HIT)
    sent = []

    def go():
        sent.append(1)
        raise E403
    r = SP.ig_publish_once("h", "u", "t", CAP, go, lister=lister)
    assert r["id"] == "9" and len(sent) == 1


def test_發前已有同文案_不呼叫publish():
    lister, _ = lister_seq(HIT)
    sent = []
    r = SP.ig_publish_once("h", "u", "t", CAP, lambda: sent.append(1) or "x", lister=lister)
    assert r["id"] == "9" and sent == []


def test_查詢失敗_不重試():
    lister, _ = lister_seq({"data": []}, RuntimeError("查詢壞了"))
    sent = []

    def go():
        sent.append(1)
        raise RuntimeError("HTTP 500")
    with pytest.raises(RuntimeError, match="HTTP 500"):
        SP.ig_publish_once("h", "u", "t", CAP, go, lister=lister)
    assert len(sent) == 1


def test_ig_post呼叫點走共用防重複(monkeypatch):
    posts = []

    def call(method, path, token, params=None):
        if method == "GET" and path.endswith("/media"):
            return {"data": []} if not posts else HIT
        if path.endswith("/media_publish"):
            posts.append(1)
            raise IG.PostError('HTTP 403 {"error_subcode": 2207051}')
        raise AssertionError(path)
    monkeypatch.setattr(IG, "_call", call)
    r = IG._publish_once("u", "c1", CAP, "t")
    assert r["id"] == "9" and len(posts) == 1


def test_tc_post呼叫點走共用防重複(monkeypatch):
    posts = []

    def api(platform, method, path, token, params=None):
        if method == "GET" and path.endswith("/media"):
            return HIT
        posts.append(1)
        return {"id": "new"}
    monkeypatch.setattr(TC, "api", api)
    assert TC._ig_publish_once("u", "c1", CAP, "t") == "9" and posts == []
