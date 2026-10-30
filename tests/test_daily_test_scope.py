"""daily.yml 的測試範圍檢查（2026-10-30）：管線測試不得依賴 Playwright。

事故：test_social_news.py 的封面測試要 Playwright，daily 沒裝 → 10-28 21:07 UTC 起「跑指標庫測試」紅 →
整條資料管線不抓資料。daily 的 pytest 一律排除 tests/test_social*；這裡確認「排除之後」沒有檔案 import playwright。
"""
from __future__ import annotations

import fnmatch
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WF = (ROOT / ".github" / "workflows" / "daily.yml").read_text(encoding="utf-8")


def _ignored_globs() -> list[str]:
    m = re.search(r"python -m pytest tests/ [^\n]*", WF)
    assert m, "daily.yml 找不到 pytest 指令"
    return re.findall(r"--ignore-glob='([^']+)'", m.group(0))


def test_daily_pytest_excludes_social():
    assert "tests/test_social*" in _ignored_globs()


def test_daily_pytest_has_no_playwright_files():
    globs = _ignored_globs()
    bad = []
    for f in sorted((ROOT / "tests").glob("test_*.py")):
        rel = f"tests/{f.name}"
        if any(fnmatch.fnmatch(rel, g) for g in globs):
            continue
        if f.name == Path(__file__).name:
            continue
        if re.search(r"playwright", f.read_text(encoding="utf-8"), re.I):
            bad.append(rel)
    assert not bad, f"daily 會跑到需要 Playwright 的測試：{bad}（請加進 --ignore-glob 或改名 test_social*）"


def test_daily_has_failure_summary_step():
    assert "GITHUB_STEP_SUMMARY" in WF and "指標庫測試失敗警示" in WF
