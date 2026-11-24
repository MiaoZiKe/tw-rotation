"""IG 防重複發文（2026-11-24 Andy：「IG有嚴重重複發文問題幫我檢查並處理 避免發生」）。"""
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import healing_post as HP  # noqa: E402

CAP = "加班的人變少，時數卻變多？\n有加班者每月16.2小時\n#談晴說礙"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000")


@pytest.fixture(autouse=True)
def _nosleep(monkeypatch):
    monkeypatch.setattr(HP.SP, "_sleep", lambda s: None)


def fake_media(monkeypatch, feed):
    calls = {"get": 0}

    def http(method, url, data=None, params=None, **kw):
        assert method == "GET" and url.endswith("/media")
        calls["get"] += 1
        return {"data": feed(calls["get"])}
    monkeypatch.setattr(HP.SP, "http", http)
    return calls


def test_已有同文案就不發(monkeypatch):
    fake_media(monkeypatch, lambda n: [{"id": "9", "caption": CAP, "timestamp": NOW, "permalink": "https://ig/p/9"}])
    sent = []
    r = HP.ig_publish_once("h", "u", "t", CAP, lambda: sent.append(1) or "x")
    assert r["id"] == "9" and sent == []


def test_回錯但其實已發出_不重試(monkeypatch):
    fake_media(monkeypatch, lambda n: [] if n == 1 else [{"id": "7", "caption": CAP, "timestamp": NOW, "permalink": "L"}])
    sent = []

    def go():
        sent.append(1)
        raise RuntimeError("HTTP 500 暫時錯誤")
    r = HP.ig_publish_once("h", "u", "t", CAP, go)
    assert r["id"] == "7" and len(sent) == 1


def test_封鎖類錯誤不重試(monkeypatch):
    fake_media(monkeypatch, lambda n: [])
    sent = []

    def go():
        sent.append(1)
        raise RuntimeError('HTTP 403 {"code": 4, "error_subcode": 2207051, "is_transient": false}')
    with pytest.raises(RuntimeError):
        HP.ig_publish_once("h", "u", "t", CAP, go)
    assert len(sent) == 1


def test_查不到是否已發就不重試(monkeypatch):
    n = {"get": 0}

    def http(method, url, data=None, params=None, **kw):
        n["get"] += 1
        if n["get"] == 1:
            return {"data": []}
        raise RuntimeError("查詢失敗")
    monkeypatch.setattr(HP.SP, "http", http)
    sent = []

    def go():
        sent.append(1)
        raise RuntimeError("HTTP 500")
    with pytest.raises(RuntimeError):
        HP.ig_publish_once("h", "u", "t", CAP, go)
    assert len(sent) == 1


def test_暫時錯誤且確認沒發_才重試(monkeypatch):
    fake_media(monkeypatch, lambda n: [])
    sent = []

    def go():
        sent.append(1)
        if len(sent) < 2:
            raise RuntimeError("HTTP 500 暫時錯誤")
        return "new"
    assert HP.ig_publish_once("h", "u", "t", CAP, go)["id"] == "new"
    assert len(sent) == 2


def test_舊貼文同文案超過72小時不算(monkeypatch):
    fake_media(monkeypatch, lambda n: [{"id": "1", "caption": CAP, "timestamp": "2020-01-01T00:00:00+0000"}])
    assert HP.ig_publish_once("h", "u", "t", CAP, lambda: "new")["id"] == "new"
