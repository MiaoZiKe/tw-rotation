"""daily.yml 的測試範圍檢查（2026-10-30 初版，2026-11-09 改白名單）。

事故：10-28 社群封面測試缺 Playwright、11-06 test_exrights 寫死 6669 本益比窗、11-09 IG 短影片測試缺中文字型，
三次擋死整條盤後資料。現在每日關卡只跑 scripts/daily_test_list.py 動態產生的白名單（會 import pipeline 的測試檔），
並用 -m "not realdata" 排掉依賴資料湖真實內容的斷言。這裡確認白名單不含 Playwright／中文字型／實打外網的檔。
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WF = (ROOT / ".github" / "workflows" / "daily.yml").read_text(encoding="utf-8")
PUSH_WF = (ROOT / ".github" / "workflows" / "tests-on-push.yml").read_text(encoding="utf-8")

_spec = importlib.util.spec_from_file_location("daily_test_list", ROOT / "scripts" / "daily_test_list.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
SELECTED = _mod.select()
_SELF = f"tests/{Path(__file__).name}"

# 不准出現在每日白名單裡的內容特徵
_BAD = {
    "Playwright": re.compile(r"playwright", re.I),
    "中文字型": re.compile(r"FONT_CANDIDATES|ImageFont"),
    "實打外網": re.compile(r"requests\.(get|post)\(\s*[\"']https?://"),
}


def test_daily_pytest_uses_whitelist_and_excludes_realdata():
    m = re.search(r"python -m pytest \$FILES[^\n]*", WF)
    assert m, "daily.yml 的 pytest 步驟沒有改用白名單 $FILES"
    assert '-m "not realdata"' in m.group(0)
    assert "scripts/daily_test_list.py" in WF
    assert "tests/ -q" not in m.group(0), "daily 不准退回全跑 tests/"


def test_push_workflow_uses_same_whitelist():
    assert "scripts/daily_test_list.py" in PUSH_WF
    assert '-m "not realdata"' in PUSH_WF
    assert "每日管線測試紅了" in PUSH_WF


def test_whitelist_not_empty_and_has_core_pipeline_tests():
    assert SELECTED, "白名單是空的"
    names = {Path(f).name for f in SELECTED}
    for core in ("test_indicators.py", "test_flow_periods.py", "test_fundamental.py", "test_etf_freq_payload.py"):
        assert core in names, f"核心管線測試 {core} 不在白名單"
    assert any("build_payload" in n or "payload" in n for n in names)


def test_whitelist_excludes_social_ig_tc():
    for f in SELECTED:
        n = Path(f).name
        assert not n.startswith(("test_social", "test_tc_", "test_ig_")), f"白名單不該含 {n}"


def test_whitelist_has_no_playwright_font_or_network_files():
    bad = []
    for f in SELECTED:
        if f == _SELF:
            continue
        txt = (ROOT / f).read_text(encoding="utf-8", errors="ignore")
        for label, rx in _BAD.items():
            if rx.search(txt):
                bad.append(f"{f}（{label}）")
    assert not bad, f"daily 白名單會跑到不該跑的測試：{bad}"


def test_whitelist_empty_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(_mod, "TESTS", tmp_path)
    assert _mod.select() == []


def test_daily_has_failure_summary_step():
    assert "GITHUB_STEP_SUMMARY" in WF and "指標庫測試失敗警示" in WF
