"""端點探測器的離線測試：不連網，只驗「回應被記成什麼樣子」。

探測器的產出是後面寫 parser 的唯一依據，所以它自己不能出錯：
連不上要記成結果而不是丟例外、list 要記欄位名、swagger 要只留命中的路徑。
"""
from __future__ import annotations

import json

import pytest

from scripts import probe_sources as ps


class FakeResp:
    def __init__(self, payload, status=200, ctype="application/json", text=None):
        self._payload = payload
        self.status_code = status
        self.headers = {"Content-Type": ctype}
        self.text = text if text is not None else json.dumps(payload, ensure_ascii=False)
        self.content = self.text.encode("utf-8")

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


def _patch(monkeypatch, resp):
    monkeypatch.setattr(ps.requests, "request", lambda *a, **k: resp)


def test_候選端點的_id_不可以重複():
    for name, probes in ps.PROBES.items():
        ids = [p["id"] for p in probes]
        assert len(ids) == len(set(ids)), f"{name} 有重複的 id"


def test_每個候選都要有網址與說明():
    for name, probes in ps.PROBES.items():
        for p in probes:
            assert p["url"].startswith("https://"), f"{name}/{p['id']} 不是 https"
            assert p.get("note"), f"{name}/{p['id']} 沒寫這是在試什麼"


def test_list_回應要記下筆數與欄位名(monkeypatch):
    _patch(monkeypatch, FakeResp([{"公司代號": "2330", "發言日期": "1150910", "主旨": "說明媒體報導"}] * 5))
    r = ps.one({"id": "x", "url": "https://example.com/a", "note": "n"})
    assert r["kind"] == "list" and r["n"] == 5
    assert r["fields"] == ["主旨", "公司代號", "發言日期"]      # 欄位名是寫 parser 的關鍵
    assert len(r["sample"]) == 3                                # 樣本只留前三筆，不要把整包塞進 repo


def test_swagger_只留命中重大訊息的路徑(monkeypatch):
    swagger = {"paths": {
        "/opendata/t187ap04_L": {"get": {"summary": "公開資訊觀測站-重大訊息", "description": "上市公司重大訊息"}},
        "/exchangeReport/STOCK_DAY_ALL": {"get": {"summary": "上市個股日成交資訊"}},
    }}
    _patch(monkeypatch, FakeResp(swagger))
    r = ps.one({"id": "sw", "url": "https://example.com/swagger.json", "note": "n"})
    assert r["all_paths_n"] == 2
    assert list(r["matched_paths"]) == ["/opendata/t187ap04_L"]
    assert "paths" not in json.dumps(r["matched_paths"])        # 沒有把整份目錄夾帶進來


def test_不是_json_的回應記成純文字(monkeypatch):
    _patch(monkeypatch, FakeResp(None, ctype="text/html", text="<html>維護中</html>"))
    r = ps.one({"id": "h", "url": "https://example.com/x", "note": "n"})
    assert r["kind"] == "text" and "維護中" in r["sample_text"]


def test_連不上要記成結果而不是丟例外(monkeypatch):
    def boom(*a, **k):
        raise ps.requests.exceptions.ConnectTimeout("timed out")
    monkeypatch.setattr(ps.requests, "request", boom)
    r = ps.one({"id": "dead", "url": "https://example.com/x", "note": "n"})
    assert r["status"] is None and "ConnectTimeout" in r["error"]
    assert "elapsed_ms" in r


def test_探測結果寫成_fixture_檔(monkeypatch, tmp_path):
    _patch(monkeypatch, FakeResp([{"公司代號": "2330"}]))
    monkeypatch.setattr(ps, "OUT", tmp_path)
    monkeypatch.setattr(ps, "PROBES", {"t": [{"id": "a", "url": "https://example.com/a", "note": "n"}]})
    f = ps.run("t")
    got = json.loads(f.read_text(encoding="utf-8"))
    assert got["probe"] == "t" and got["results"][0]["status"] == 200
