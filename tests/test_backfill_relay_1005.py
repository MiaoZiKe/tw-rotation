"""歷史回補「接力」（2026-10-05）：每日續補撞 402 要寫 quota_stopped，backfill.yml 的接力判斷要讀它。

為什麼要測：計畫補齊之後 plan:default.stopped_at 永遠是 None，只看它的話續補撞額度不會接力。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import textwrap
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline import run_backfill  # noqa: E402
from pipeline.util import http, store  # noqa: E402


@pytest.fixture
def sb(tmp_path, monkeypatch):
    prog_file = tmp_path / "backfill_progress.json"
    monkeypatch.setattr(run_backfill, "PROGRESS", prog_file)
    monkeypatch.setattr(run_backfill, "market_codes", lambda: ["2330", "2317"])
    tbl = pd.DataFrame({"code": ["2330", "2317"], "date": ["2026-10-01", "2026-10-01"]})
    monkeypatch.setattr(store, "read", lambda name: tbl)
    monkeypatch.setattr(run_backfill, "stale_inst_codes",
                        lambda t, p, u, cap: ("2026-10-02", ["2330", "2317"]))
    monkeypatch.setattr(http, "finmind_budget_left", lambda: 1000)
    return prog_file


def _prog(f: Path) -> dict:
    return json.loads(f.read_text()) if f.exists() else {}


def test_續補撞額度要寫quota_stopped(sb, monkeypatch):
    monkeypatch.setattr(run_backfill, "run", lambda *a, **k: {"finished": False, "exhausted": True})
    assert run_backfill.refresh_stale_inst({}, date(2026, 10, 5)) is False
    qs = _prog(sb)["quota_stopped"]
    assert qs["stopped"] is True and qs["steps"]


def test_續補做完就清掉quota_stopped(sb, monkeypatch):
    sb.write_text(json.dumps({"quota_stopped": {"stopped": True, "steps": ["inst"]}}))
    monkeypatch.setattr(run_backfill, "run", lambda *a, **k: {"finished": True, "exhausted": False})
    assert run_backfill.refresh_stale_inst({}, date(2026, 10, 5)) is True
    assert "quota_stopped" not in _prog(sb)


def test_一開始就沒額度也要記(sb, monkeypatch):
    monkeypatch.setattr(http, "finmind_budget_left", lambda: 0)
    assert run_backfill.refresh_stale_inst({}, date(2026, 10, 5)) is False
    assert _prog(sb)["quota_stopped"]["steps"] == ["inst_fresh"]


def _relay(tmp_path: Path, progress: dict, **env) -> bool:
    text = (ROOT / ".github" / "workflows" / "backfill.yml").read_text(encoding="utf-8")
    m = re.search(r"id: relay_check\n.*?python3 - <<'PY'[^\n]*\n(.*?)\n\s+PY\n", text, re.S)
    assert m, "backfill.yml 找不到接力判斷那段 Python"
    st = tmp_path / "data" / "_state"
    st.mkdir(parents=True, exist_ok=True)
    (st / "backfill_progress.json").write_text(json.dumps(progress))
    e = {**os.environ, "DATASETS": "plan", "LO": "false", "IO": "false", **env}
    out = subprocess.run([sys.executable, "-c", textwrap.dedent(m.group(1))], cwd=tmp_path,
                         env=e, capture_output=True, text=True, check=True).stdout
    return "relay=true" in out


def test_接力判斷(tmp_path):
    done = {"complete": {"plan:default": {"done": True, "stopped_at": None}}}
    assert _relay(tmp_path, done) is False
    assert _relay(tmp_path, {**done, "quota_stopped": {"stopped": True, "steps": ["inst"]}}) is True
    assert _relay(tmp_path, {"complete": {"plan:default": {"done": False, "stopped_at": "inst@market"}}}) is True
    # 只跑 Logo／分 K、或單一資料集，不接力
    q = {**done, "quota_stopped": {"stopped": True}}
    assert _relay(tmp_path, q, LO="true") is False
    assert _relay(tmp_path, q, DATASETS="inst") is False
