"""大戶／散戶買賣（推估）：演算法、門檻、前端與後端同一套規則、資料湖註冊、收集器不重複寫。"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline import config  # noqa: E402
from pipeline.compute import bigsmall as bs  # noqa: E402

VEC = json.loads((ROOT / "tests" / "fixtures" / "bigsmall_vectors.json").read_text(encoding="utf-8"))
KEYS = ["big_buy", "big_sell", "small_buy", "small_sell", "neutral", "auction", "observed", "pre", "sampled", "coverage"]


def _run_py():
    a = bs.Acc(thr=VEC["thr"])
    for s in VEC["snaps"]:
        a.step(s)
    return a


def test_vectors_python():
    a = _run_py()
    r = a.row("2026-11-09", "9999")
    for k in KEYS:
        assert r[k] == pytest.approx(VEC["expect"][k], abs=0.051), k
    assert a.series == VEC["expect"]["series"]
    # 總量守恆：大單＋小單＋不分方向＝收集期間的成交量
    assert r["big_buy"] + r["big_sell"] + r["small_buy"] + r["small_sell"] + r["neutral"] == pytest.approx(r["observed"], abs=0.2)


@pytest.mark.skipif(not shutil.which("node"), reason="沒有 node")
def test_vectors_js_same_as_python():
    """site/bigsmall.js 的 Acc 對同一組快照要算出同一組數字（前端即時與盤後日 K 用同一套規則）。"""
    js = ("const B=require(process.argv[1]);const v=require(process.argv[2]);const a=new B.Acc(v.thr);"
          "v.snaps.forEach(s=>a.step(s));console.log(JSON.stringify({row:a.row('2026-11-09','9999'),series:a.series}));")
    out = subprocess.run(["node", "-e", js, str(ROOT / "site" / "bigsmall.js"), str(ROOT / "tests" / "fixtures" / "bigsmall_vectors.json")],
                         capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    j = json.loads(out.stdout)
    for k in KEYS:
        assert j["row"][k] == pytest.approx(VEC["expect"][k], abs=0.051), k
    assert j["series"] == VEC["expect"]["series"]


def test_threshold_floor_and_scale():
    assert bs.threshold(None) == bs.BIG_FLOOR
    assert bs.threshold(50_000) == bs.BIG_FLOOR                  # 小型股：平均每筆很小 → 用下限 100 萬
    assert bs.threshold(2_000_000) == 8_000_000                  # 大型股：4 倍平均每筆
    px = pd.DataFrame({"date": ["2026-11-05", "2026-11-06"], "code": ["2330", "2330"],
                       "turnover": [1e10, 3e10], "transactions": [2000.0, 6000.0]})
    assert bs.avg_trade_amount(px)["2330"] == pytest.approx(5e6)


def test_auction_and_no_trade():
    a = bs.Acc(thr=1e6)
    a.step({"t": "08:59:50", "v": "0", "z": "-", "a": "10.5_", "b": "10_"})
    a.step({"t": "09:00:00", "v": "500", "z": "10.0", "tv": "500", "a": "10.5_", "b": "10_"})   # 開盤集合競價
    a.step({"t": "09:00:05", "v": "500", "z": "-", "tv": "-"})                                   # 沒成交
    r = a.row("2026-11-09", "1")
    assert r["auction"] == 500 and r["neutral"] == 500 and r["big_buy"] == 0 and r["small_sell"] == 0


def test_table_registered_and_payload_shape(tmp_path):
    assert config.TABLES["bigsmall_daily"] == ["date", "code"]
    a = _run_py()
    lake = pd.DataFrame([a.row("2026-11-09", "9999")], columns=bs.COLUMNS)
    px = pd.DataFrame({"date": ["2026-11-06"], "code": ["9999"], "turnover": [1e8], "transactions": [100.0]})
    s = bs.export(tmp_path, px, lake)
    assert s["codes"] == 1
    j = json.loads((tmp_path / "bigsmall" / "9999.json").read_text(encoding="utf-8"))
    assert j["cols"][:3] == ["date", "big_net", "small_net"] and len(j["days"]) == 1
    assert j["days"][0][1] == pytest.approx(20 - 13.3, abs=0.1) and j["thr"] == 4_000_000
    t = json.loads((tmp_path / "bigsmall" / "_thr.json").read_text(encoding="utf-8"))
    assert t["thr"]["9999"] == 4_000_000


def test_collector_skips_when_lake_has_today(monkeypatch):
    from pipeline.sources import bigsmall_collect as bc
    monkeypatch.setattr(bc, "universe", lambda: [("2330", "tse")])
    monkeypatch.setattr(bc, "thresholds", lambda codes: {"2330": 1e6})
    monkeypatch.setattr(bc, "_fetch", lambda b: [{"c": "2330", "d": "20261109", "t": "10:00:00", "v": "10", "z": "100"}])
    monkeypatch.setattr(bc, "already_have", lambda d: True)
    monkeypatch.setattr(bc.time, "sleep", lambda s: None)
    from datetime import datetime
    monkeypatch.setattr(bc, "_now", lambda: datetime(2026, 11, 9, 10, 0, tzinfo=bc.TPE))
    wrote = []
    monkeypatch.setattr(bc.store, "append", lambda t, df: wrote.append(t) or 0)
    assert bc.run() == 0 and wrote == []
