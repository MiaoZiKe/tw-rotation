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
