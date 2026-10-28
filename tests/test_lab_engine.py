"""交易練習室回測引擎：跑 tests/lab_engine_check.js（人工可算的小序列＋帳務恆等式＋無未來資料＋指標口徑）。"""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(shutil.which("node") is None, reason="沒有 node")
def test_lab_engine_numbers():
    r = subprocess.run(["node", str(ROOT / "tests" / "lab_engine_check.js")], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "全數通過" in r.stdout
