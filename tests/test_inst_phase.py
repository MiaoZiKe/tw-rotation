"""phase=inst：台北 16:15 起搶當天三大法人。用假回應，不打真 API。"""
from __future__ import annotations

import pandas as pd
import pytest
import yaml

from pipeline import run_daily


def _inst(date, codes):
    return pd.DataFrame({"date": date, "code": codes, "inst_total": 1.0})


@pytest.fixture
def env(monkeypatch, tmp_path):
    run_daily.RESULT.clear()
    run_daily.RESULT.update({"steps": {}, "errors": [], "empty": []})
    out = tmp_path / "gh_out"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    monkeypatch.setattr(run_daily.config, "STATE", tmp_path)
    monkeypatch.setattr(run_daily.store, "latest_date", lambda t: "2026-10-20")
    monkeypatch.setattr(run_daily, "universe", lambda n: ["2330", "2317", "3008"])
    monkeypatch.setattr(run_daily.http, "finmind_budget_left", lambda: 100)
    # 整天全市場補抓、新鮮度檢查會讀湖／打網路，這裡不測它們（見 test_data_fresh_1020.py）
    monkeypatch.setattr(run_daily.inst_bulk, "fill_inst_bulk", lambda *a, **k: pd.DataFrame())
    monkeypatch.setattr(run_daily.inst_bulk, "site_codes", lambda: [])
    monkeypatch.setattr(run_daily.freshness, "check", lambda *a, **k: {})
    monkeypatch.setattr("sys.argv", ["run_daily", "--phase", "inst"])
    calls = {"saved": [], "built": 0, "fetch": 0}
    monkeypatch.setattr(run_daily, "save",
                        lambda t, df: calls["saved"].append(t) or len(df))
    import pipeline.build_payload as bp
    monkeypatch.setattr(bp, "build", lambda: calls.__setitem__("built", calls["built"] + 1))
    calls["out"] = out
    return calls


def test_phase_inst_在_choices(env, monkeypatch):
    # argparse 接受 inst（不接受會 SystemExit 2）；FinMind 一定要 mock，否則會真的打網路
    monkeypatch.setattr(run_daily.finmind, "institutional",
                        lambda c, s, e=None, wait=True: pd.DataFrame())
    assert run_daily.main() == 0


def test_還沒出法人_不抓不存不部署(env, monkeypatch):
    monkeypatch.setattr(run_daily.finmind, "institutional",
                        lambda c, s, e=None, wait=True: _inst("2026-10-19", [c]))
    monkeypatch.setattr(run_daily, "fetch_institutional",
                        lambda *a, **k: env.__setitem__("fetch", 1) or pd.DataFrame())
    assert run_daily.main() == 0
    assert env["fetch"] == 0 and env["saved"] == [] and env["built"] == 0
    assert "inst_new=false" in env["out"].read_text()


def test_出了法人_存湖並重算並通知部署(env, monkeypatch):
    monkeypatch.setattr(run_daily.finmind, "institutional",
                        lambda c, s, e=None, wait=True: _inst("2026-10-20", [c]))
    monkeypatch.setattr(run_daily, "fetch_institutional",
                        lambda codes, d, lb=10: _inst(d, codes))
    assert run_daily.main() == 0
    assert set(env["saved"]) == {"inst_daily"} and env["built"] == 1
    assert "inst_new=true" in env["out"].read_text()


def test_已到齊_沒新列就不部署(env, monkeypatch):
    monkeypatch.setattr(run_daily.finmind, "institutional",
                        lambda c, s, e=None, wait=True: _inst("2026-10-20", [c]))
    monkeypatch.setattr(run_daily, "fetch_institutional",
                        lambda *a, **k: pd.DataFrame())
    assert run_daily.main() == 0
    assert env["built"] == 0
    assert "inst_new=false" in env["out"].read_text()


def test_workflow_cron_與_phase_分派():
    wf = yaml.safe_load(open(".github/workflows/daily.yml", encoding="utf-8"))
    crons = [c["cron"] for c in wf[True]["schedule"]]
    assert "15,45 8 * * 1-5" in crons and "15 9 * * 1-5" in crons
    assert "inst" in wf[True]["workflow_dispatch"]["inputs"]["phase"]["options"]
    text = open(".github/workflows/daily.yml", encoding="utf-8").read()
    assert "PHASE=inst" in text
    assert "cancel-in-progress: false" in text and "cancel-in-progress: true" not in text
    assert wf["jobs"]["deploy"]["if"] == "needs.collect.outputs.inst_new != 'false'"
