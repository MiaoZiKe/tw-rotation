"""scripts/social_handoff.py：骨架、檢查與 ready 的把關（用暫存資料夾，不碰真實交接檔）。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import social_handoff as sh  # noqa: E402


def _setup(tmp_path, monkeypatch):
    monkeypatch.setattr(sh, "ROOT", tmp_path)
    monkeypatch.setattr(sh, "HANDOFF", tmp_path / "docs" / "social_handoff")
    return tmp_path


def test_new_creates_draft_skeleton(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    assert sh.main(["new", "2026-10-16", "demo", "示範"]) == 0
    folder = tmp_path / "docs" / "social_handoff" / "2026-10-16_demo"
    m = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    assert m["status"] == "draft" and m["revision"] == 1
    assert m["style_guide_status"] == "missing"
    for k in sh.REQUIRED_KEYS:
        assert k in m


def test_ready_refused_while_incomplete(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    sh.main(["new", "2026-10-16", "demo", "示範"])
    folder = tmp_path / "docs" / "social_handoff" / "2026-10-16_demo"
    assert sh.main(["ready", str(folder)]) == 1
    m = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    assert m["status"] == "draft"  # 沒被改


def test_ready_succeeds_when_complete(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    sh.main(["new", "2026-10-16", "demo", "示範"])
    folder = tmp_path / "docs" / "social_handoff" / "2026-10-16_demo"
    (folder / "brief.md").write_text("\n".join(f"## {s}\n內容" for s in sh.BRIEF_SECTIONS), encoding="utf-8")
    (folder / "sources.md").write_text("| # | 標題 | 發布者 | 發布日期 | 連結 | 摘要 |\n|---|---|---|---|---|---|\n| 1 | 標題 | 發布者 | 2026-10-15 | https://example.com | x |\n", encoding="utf-8")
    sg = tmp_path / "docs" / "social_handoff" / "style" / "LIGULIGU_IG_Threads_Style_Guide.md"
    sg.parent.mkdir(parents=True)
    sg.write_text("x", encoding="utf-8")
    mp = folder / "manifest.json"
    m = json.loads(mp.read_text(encoding="utf-8"))
    m["style_guide_status"] = "present"
    mp.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    assert sh.main(["ready", str(folder)]) == 0
    assert json.loads(mp.read_text(encoding="utf-8"))["status"] == "ready_for_gpt"


def test_bad_asset_category_and_missing_path_flagged(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    sh.main(["new", "2026-10-16", "demo", "示範"])
    folder = tmp_path / "docs" / "social_handoff" / "2026-10-16_demo"
    mp = folder / "manifest.json"
    m = json.loads(mp.read_text(encoding="utf-8"))
    m["asset_references"] = [{"path": "nope.png", "category": "guess", "original_author": "unknown",
                              "processed_by": "unknown", "provenance_evidence": "", "parent_path": ""}]
    mp.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    errs = sh.check(folder)
    assert any("category 不合法" in e for e in errs)
    assert any("路徑不存在" in e for e in errs)


def test_empty_sources_table_and_template_placeholder_flagged(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    sh.main(["new", "2026-10-16", "demo", "示範"])
    folder = tmp_path / "docs" / "social_handoff" / "2026-10-16_demo"
    errs = sh.check(folder)
    assert any("沒有任何一筆來源" in e for e in errs)
    (folder / "brief.md").write_text("\n".join(f"## {s}\n<填寫>" for s in sh.BRIEF_SECTIONS), encoding="utf-8")
    assert any("<填寫>" in e for e in sh.check(folder))


def test_from_article_builds_folder_and_blocks_until_filled(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    post = {"title": "測試文章", "subtitle": "副標", "date": "2026-10-16", "summary": "摘要", "confidence": "高",
            "blocks": [{"t": "h", "text": "三句話重點"}, {"t": "ul", "items": ["甲", "乙", "丙"]},
                       {"t": "kpi", "items": [{"label": "營收", "value": "1", "unit": "億", "delta": "+1%", "note": "n"}]}],
            "site_links": [{"label": "頁", "hash": "#overview"}],
            "sources": [{"title": "T", "publisher": "P", "date": "2026-10-15", "url": "https://example.com/a"}]}
    pp = tmp_path / "post.json"
    pp.write_text(json.dumps(post, ensure_ascii=False), encoding="utf-8")
    assert sh.main(["from-article", str(pp), "demo"]) == 0
    folder = tmp_path / "docs" / "social_handoff" / "2026-10-16_demo"
    assert "| 1 | T | P | 2026-10-15 | https://example.com/a |" in (folder / "sources.md").read_text(encoding="utf-8")
    assert "1. 甲" in (folder / "brief.md").read_text(encoding="utf-8")
    assert any("<填寫>" in e for e in sh.check(folder))
