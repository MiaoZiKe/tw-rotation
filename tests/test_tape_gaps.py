"""盤中快照缺口（2026-11-06 稽核）：缺口要明示、不進 errors、不亮紅燈；保存期內的失敗仍是待補。"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pipeline.build_payload as bp
from pipeline.sources import tape

TPE = timezone(timedelta(hours=8))
NOW = datetime(2026, 11, 6, 16, 0, tzinfo=TPE)


def test_過期未收齊的交易日算永久缺口():
    gaps = tape.gap_report(NOW, ["20261028", "20261029"], complete=set())
    assert [g["date"] for g in gaps] == ["2026-10-28", "2026-10-29"]
    assert all("永久缺口" in g["reason"] for g in gaps)


def test_保存期內的不算缺口_仍可補():
    # 11-02 距今 4 天，還在 KV 保存期內 → 不是缺口（那是 pending，會亮黃等下一輪補）
    assert tape.gap_report(NOW, ["20261102"], complete=set()) == []


def test_收齊的交易日不是缺口():
    assert tape.gap_report(NOW, ["20261028"], complete={"20261028"}) == []


def test_早於開始日的不算缺口():
    # 盤中快照功能 10-28 才開始累積，更早的日子不能當缺口
    assert tape.gap_report(NOW, ["20261020"], complete=set()) == []


def test_meta_payload_缺口不進errors(monkeypatch, tmp_path):
    (tmp_path / "last_run.json").write_text(json.dumps({
        "errors": [], "empty": [], "finished_at": "2026-11-06T08:00:00+00:00",
        "gaps": [{"date": "2026-10-28", "reason": "永久缺口"}]}))
    monkeypatch.setattr(bp.config, "STATE", tmp_path)
    monkeypatch.setattr(bp.freshness, "check", lambda *a, **k: {})
    m = bp.meta_payload("2026-11-05", 10)
    assert m["gaps"] == [{"date": "2026-10-28", "reason": "永久缺口"}]
    assert m["last_run_errors"] == []
    assert m["last_run_empty"] == []


def test_meta_payload沒有gaps欄位時給空清單(monkeypatch, tmp_path):
    (tmp_path / "last_run.json").write_text(json.dumps({"errors": [], "empty": []}))
    monkeypatch.setattr(bp.config, "STATE", tmp_path)
    monkeypatch.setattr(bp.freshness, "check", lambda *a, **k: {})
    assert bp.meta_payload("2026-11-05", 10)["gaps"] == []


def _run_tape(monkeypatch, miss, trade, complete):
    import pandas as pd
    import pipeline.run_daily as rd
    df = pd.DataFrame(columns=tape.COLUMNS)
    df.attrs["miss"] = miss
    df.attrs["todo"] = miss
    monkeypatch.setattr(rd.tape, "collect", lambda *a, **k: df)
    monkeypatch.setattr(rd.tape, "_tpe_now", lambda: NOW)
    monkeypatch.setattr(rd.tape, "lake_calendar", lambda now: (set(trade), set(complete)))
    monkeypatch.setattr(rd, "RESULT", {"steps": {}, "errors": [], "empty": [], "gaps": []})
    rd._tape_step()
    return rd.RESULT


def test_過期缺口不亮黃燈也不進errors(monkeypatch):
    r = _run_tape(monkeypatch, miss=["20261028", "20261029"],
                  trade=["20261028", "20261029"], complete=[])
    assert [g["date"] for g in r["gaps"]] == ["2026-10-28", "2026-10-29"]
    assert "tape.collect" not in r["empty"]
    assert r["errors"] == []


def test_保存期內開過市沒抓到要亮黃燈(monkeypatch):
    r = _run_tape(monkeypatch, miss=["20261104"], trade=["20261104"], complete=[])
    assert "tape.collect" in r["empty"]
    assert r["gaps"] == []


def test_休市日沒有快照不算待補也不算缺口(monkeypatch):
    r = _run_tape(monkeypatch, miss=["20261102"], trade=[], complete=[])
    assert "tape.collect" not in r["empty"]
    assert r["gaps"] == []
