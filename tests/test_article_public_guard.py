"""新精選文章不得洩漏到公開檔（scripts/article_publish.py）：索引只有標題等欄位、repo 裡不得有新文章的全文。"""
import json

import pytest

from scripts import article_publish as ap

POST = {"id": "2026-10-17-know-test-a", "cat": "know", "title": "測試", "date": "2026-10-17", "topic": "k_test",
        "subtitle": "SUB", "summary": "SUM", "tags": ["x"], "reading_min": 3,
        "groups": [{"id": "foundry", "name": "晶圓代工"}], "blocks": [{"t": "p", "text": "BODY"}], "sources": [{"title": "s"}]}


def test_公開索引項目不含任何內文欄位():
    e = ap.public_entry(POST)
    assert set(e) <= set(ap.PUBLIC_KEYS)
    assert e["src"] == "api" and e["topic"] == "k_test" and e["groups"] == [{"id": "foundry", "name": "晶圓代工"}]
    for k in ap.LEAK_KEYS:
        assert k not in e
    assert "BODY" not in json.dumps(e, ensure_ascii=False) and "SUM" not in json.dumps(e, ensure_ascii=False)


@pytest.mark.parametrize("patch", [{"id": "../x"}, {"cat": "other"}, {"date": "2026/10/17"}, {"blocks": []}, {"topic": ""}])
def test_壞的全文不產出索引(patch):
    p = {**POST, **patch}
    if "topic" in patch:
        p.pop("topic")
    with pytest.raises(ValueError):
        ap.public_entry(p)


def test_洩漏檢查抓得到內容欄位與公開全文檔(tmp_path):
    idx, posts = tmp_path / "index.json", tmp_path / "posts"
    posts.mkdir()
    ok = ap.public_entry(POST)
    idx.write_text(json.dumps({"updated": "2026-10-17", "articles": [ok, {"id": "2026-10-14-know-old1", "cat": "know", "summary": "舊文章維持原狀"}]}), encoding="utf-8")
    assert ap.leaks(idx, posts) == []
    idx.write_text(json.dumps({"articles": [{**ok, "summary": "洩漏"}]}), encoding="utf-8")
    assert any("summary" in m for m in ap.leaks(idx, posts))
    idx.write_text(json.dumps({"articles": [ok]}), encoding="utf-8")
    (posts / f"{ok['id']}.json").write_text("{}", encoding="utf-8")
    assert any("posts" in m for m in ap.leaks(idx, posts))


def test_加入索引取代同id且最新在前(tmp_path):
    idx = tmp_path / "index.json"
    idx.write_text(json.dumps({"updated": "2026-10-16", "articles": [{"id": "2026-10-14-know-old1"}]}), encoding="utf-8")
    ap.add_to_index(ap.public_entry(POST), idx)
    ap.add_to_index({**ap.public_entry(POST), "title": "改過"}, idx)
    d = json.loads(idx.read_text(encoding="utf-8"))
    assert [a["id"] for a in d["articles"]] == ["2026-10-17-know-test-a", "2026-10-14-know-old1"] and d["articles"][0]["title"] == "改過"
    assert d["updated"] == "2026-10-17"


def test_實際的公開檔現在是乾淨的():
    assert ap.leaks() == []


def test_全文檔放在repo裡面會被拒(tmp_path, monkeypatch, capsys):
    inside = ap.ROOT / "docs" / "_tmp_post_test.json"
    inside.write_text(json.dumps(POST), encoding="utf-8")
    try:
        assert ap.main([str(inside)]) == 2
    finally:
        inside.unlink()
    assert "repo 裡面" in capsys.readouterr().out


def test_沒有機器鑰匙就不上傳不寫索引(tmp_path, monkeypatch, capsys):
    f = tmp_path / "p.json"
    f.write_text(json.dumps(POST), encoding="utf-8")
    monkeypatch.delenv("ACCOUNT_API_URL", raising=False)
    monkeypatch.delenv("ARTICLE_BOT_KEY", raising=False)
    monkeypatch.delenv("BACKUP_TOKEN", raising=False)
    before = ap.INDEX.read_text(encoding="utf-8")
    assert ap.main([str(f)]) == 3
    assert ap.INDEX.read_text(encoding="utf-8") == before
    assert "不要把全文推進 repo" in capsys.readouterr().out


def test_上傳後清單確認不到就不寫索引(tmp_path, monkeypatch):
    f = tmp_path / "p.json"
    f.write_text(json.dumps(POST), encoding="utf-8")
    monkeypatch.setenv("ACCOUNT_API_URL", "https://x.example")
    monkeypatch.setenv("ARTICLE_BOT_KEY", "k" * 20)
    idx = tmp_path / "index.json"
    idx.write_text(json.dumps({"articles": []}), encoding="utf-8")
    monkeypatch.setattr(ap, "INDEX", idx)
    sent = []
    monkeypatch.setattr(ap.aj, "call", lambda b, t, body: (sent.append(body["op"]), {"ok": True, "bytes": 99} if body["op"] == "put_body" else {"bodies": []})[1])
    assert ap.main([str(f)]) == 4
    assert sent == ["put_body", "list_bodies"] and json.loads(idx.read_text(encoding="utf-8"))["articles"] == []
    monkeypatch.setattr(ap.aj, "call", lambda b, t, body: {"ok": True, "bytes": 99} if body["op"] == "put_body" else {"bodies": [{"id": POST["id"], "bytes": 99}]})
    assert ap.main([str(f)]) == 0
    assert json.loads(idx.read_text(encoding="utf-8"))["articles"][0]["id"] == POST["id"]
