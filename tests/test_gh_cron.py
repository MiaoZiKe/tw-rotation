"""Worker tw-gh-cron（workers/gh-cron）：排程判斷由 node 測試負責，這裡守三件事——
1) node 測試全過；2) 休市日清單跟 pipeline/calendar/tw_holidays.yaml 同步；
3) Worker 會派的 workflow／輸入，在對應的 .github/workflows 裡真的有（不然 GitHub 回 422，整輪白派）。"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
W = ROOT / "workers/gh-cron"


@pytest.mark.skipif(shutil.which("node") is None, reason="沒有 node")
def test_node_排程測試全過():
    r = subprocess.run(["node", "--test", str(W / "test/schedule.test.mjs")], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-1000:]


def test_休市日清單與_yaml_同步():
    doc = yaml.safe_load((ROOT / "pipeline/calendar/tw_holidays.yaml").read_text(encoding="utf-8"))
    js = set(re.findall(r"'(\d{4}-\d{2}-\d{2})'", (W / "src/holidays.js").read_text(encoding="utf-8")))
    assert js == {str(d) for d in doc["days"]}, "改了 tw_holidays.yaml 要重跑 python scripts/gen_gh_cron_holidays.py"
    assert "2026-10-26" in js


@pytest.mark.skipif(shutil.which("node") is None, reason="沒有 node")
def test_派出去的輸入都是_workflow_認得的值():
    out = subprocess.run(
        ["node", "-e", "import('./workers/gh-cron/src/schedule.js').then(m=>console.log(JSON.stringify(m.SCHEDULE)))"],
        capture_output=True, text=True, cwd=ROOT, check=True).stdout
    sched = json.loads(out)
    for j in sched:
        wf = yaml.safe_load((ROOT / ".github/workflows" / j["workflow"]).read_text(encoding="utf-8"))
        on = wf.get("on") or wf.get(True)
        inputs = on["workflow_dispatch"]["inputs"]
        for k, v in j["inputs"].items():
            assert k in inputs, f"{j['workflow']} 沒有輸入 {k}"
            opts = inputs[k].get("options")
            if opts:
                assert v in opts, f"{j['workflow']} 的 {k} 沒有選項 {v}"
            if inputs[k].get("type") == "boolean":
                assert v in ("true", "false")


def test_premarket_已開啟():      # 2026-10-27 Andy「開始發」
    assert re.search(r'ENABLE_PREMARKET\s*=\s*"1"', (W / "wrangler.toml").read_text(encoding="utf-8"))


def test_index_沒有對外服務():
    src = (W / "src/index.js").read_text(encoding="utf-8")
    assert "404" in src and "GH_DISPATCH_TOKEN" in src
    assert "workers_dev = false" in (W / "wrangler.toml").read_text(encoding="utf-8")
