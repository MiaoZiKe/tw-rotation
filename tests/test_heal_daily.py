"""scripts/heal_daily.decide：排程被丟掉時該不該補派、補哪個 phase。"""
import importlib.util
import pathlib
from datetime import datetime, timezone

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("heal_daily", ROOT / "scripts" / "heal_daily.py")
hd = importlib.util.module_from_spec(spec); spec.loader.exec_module(hd)

def u(h, m, d=20):  # 2026-10-20 是週二；台北 = UTC+8
    return datetime(2026, 10, d, h, m, tzinfo=timezone.utc)

def test_價量還沒到時間不補():
    assert hd.decide(u(7, 30), {}, []) is None          # 台北 15:30

def test_沒紀錄補_price_晚了補_full():
    assert hd.decide(u(8, 5), {}, []) == "price"        # 台北 16:05
    assert hd.decide(u(10, 45), {}, []) == "full"       # 台北 18:45

def test_已有該phase就不補():
    last = {"phase": "full", "finished_at": "2026-10-20T10:50:00+00:00"}
    assert hd.decide(u(11, 5), last, []) is None
    # inst 輪不算價量：仍要補
    last = {"phase": "inst", "finished_at": "2026-10-20T09:41:00+00:00"}
    assert hd.decide(u(10, 45), last, []) == "full"

def test_昨天的紀錄不算():
    last = {"phase": "full", "finished_at": "2026-10-19T10:50:00+00:00"}
    assert hd.decide(u(8, 5), last, []) == "price"

def test_有排隊中或今天補過不重複():
    q = [{"status": "in_progress", "created_at": "2026-10-20T08:00:00Z", "display_title": "x", "actor_login": "a"}]
    assert hd.decide(u(8, 30), {}, q) is None
    done = [{"status": "completed", "created_at": "2026-10-20T08:10:00Z",
             "display_title": "每日盤後管線 (price)", "actor_login": "github-actions[bot]"}]
    assert hd.decide(u(9, 30), {}, done) is None

def test_週末與深夜不補():
    assert hd.decide(u(8, 5, d=24), {}, []) is None     # 週六
    assert hd.decide(u(14, 30), {}, []) is None         # 台北 22:30

def test_兩個workflow可解析且cron避開整點半點():
    d = yaml.safe_load((ROOT / ".github/workflows/daily.yml").read_text(encoding="utf-8"))
    for c in d[True]["schedule"]:
        assert c["cron"].split()[0] not in ("0", "30"), c
    b = yaml.safe_load((ROOT / ".github/workflows/backfill.yml").read_text(encoding="utf-8"))
    assert b["jobs"]["heal"]["permissions"]["actions"] == "write"
