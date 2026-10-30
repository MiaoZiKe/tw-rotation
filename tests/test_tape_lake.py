"""盤中 5 分鐘快照（/tape）落地進資料湖 tape_5m。全部用假回應，不打真 Worker。

守住的事：
1. 格式解析與 site/tape.js 同一份（壞行略過、null 價格不寫列），解析失敗回空而不是拋例外。
2. 成交值是估算（逐格新增張數×1000×該格價），且標 val_src=est。
3. 只增不改：重抓同一天不會變兩列；按月分割（ts 是台北時間）。
4. 保底：湖裡沒收齊的日子會補抓、收齊的不再打 Worker、今天沒收盤不抓。
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from pipeline import config
from pipeline.sources import tape
from pipeline.util import http, store

TPE = timezone(timedelta(hours=8))


def ndjson(date="2026-10-30", slots=None):
    head = {"date": date, "codes": ["2330", "2317", "9999"], "y": [1000, 200, None]}
    slots = slots if slots is not None else [
        {"t": "09:00", "p": [1000, 200, None], "v": [100, 50, None]},
        {"t": "09:05", "p": [1010, 201, None], "v": [300, 50, None]},
        {"t": "13:30", "p": [1020, None, None], "v": [400, None, None]},
    ]
    return "\n".join([json.dumps(head)] + [json.dumps(s) for s in slots]) + "\n"


@pytest.fixture
def lake(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path)
    return tmp_path


def test_解析欄位與成交值估算():
    df = tape.parse(ndjson())
    assert list(df.columns) == tape.COLUMNS
    a = df[df.code == "2330"].reset_index(drop=True)
    assert a.ts.tolist() == ["2026-10-30T09:00:00+08:00", "2026-10-30T09:05:00+08:00", "2026-10-30T13:30:00+08:00"]
    # 逐格：100張×1000×1000 ＝ 1e8；再 200張×1000×1010 ＝ 2.02e8；再 100張×1000×1020 ＝ 1.02e8
    assert a.cum_value.tolist() == [1e8, 1e8 + 2.02e8, 1e8 + 2.02e8 + 1.02e8]
    assert a.cum_lots.tolist() == [100, 300, 400]
    assert set(a.src) == {"tape"} and set(a.val_src) == {"est"}
    assert a.prev_close.iloc[0] == 1000
    # 價格 null 的列不寫；9999 全程沒價 → 不出現
    assert "9999" not in set(df.code)
    assert len(df[df.code == "2317"]) == 2


def test_累計量倒退不倒扣():
    s = [{"t": "09:00", "p": [10, 1, 1], "v": [500, 1, 1]}, {"t": "09:05", "p": [10, 1, 1], "v": [400, 1, 1]},
         {"t": "09:10", "p": [10, 1, 1], "v": [600, 1, 1]}]
    a = tape.parse(ndjson(slots=s))
    a = a[a.code == "2330"]
    # 500 → (400 當 0 新增) → 600：只多算 100 張
    assert a.cum_value.iloc[-1] == (500 + 100) * 1000 * 10


@pytest.mark.parametrize("bad", ["", "not json", '{"codes": []}', '{"date":"x","codes":["1"]}', "<html>blocked</html>"])
def test_解析失敗回空不拋例外(bad, caplog):
    df = tape.parse(bad)
    assert df.empty and list(df.columns) == tape.COLUMNS
    if bad:
        assert any("前 200 字" in r.message for r in caplog.records)


def test_壞行略過():
    txt = ndjson() + '{"t":"13:35","p":[1,\n'
    assert len(tape.parse(txt)) == 5   # 2330×3 ＋ 2317×2，壞行不多出列


def test_抓取404回空並帶原因(monkeypatch):
    monkeypatch.setattr(http, "get", lambda *a, **k: None)
    df = tape.fetch_day("20261030")
    assert df.empty and "20261030" in df.attrs["error"]


def test_寫進湖按月分割且重抓不變兩列(lake):
    df = tape.parse(ndjson("2026-10-30"))
    assert store.append("tape_5m", df) == len(df)
    assert store.append("tape_5m", df) == 0
    store.append("tape_5m", tape.parse(ndjson("2026-11-02")))      # 跨月
    parts = sorted(p.parent.name for p in lake.glob("tape_5m/year=*/part.parquet"))
    assert parts == ["year=202610", "year=202611"]
    assert len(store.read("tape_5m")) == 2 * len(df)


def test_09點那格不會被分到前一個月(lake):
    store.append("tape_5m", tape.parse(ndjson("2026-11-02", [{"t": "09:00", "p": [1, 1, 1], "v": [1, 1, 1]}])))
    assert [p.parent.name for p in lake.glob("tape_5m/year=*/part.parquet")] == ["year=202611"]


def test_待補日期_略過週末收齊與未收盤的今天():
    now = datetime(2026, 10, 30, 14, 10, tzinfo=TPE)                # 週五
    got = tape.candidate_dates(now, {"20261029"})
    assert got[0] == "20261030" and "20261029" not in got
    assert all(datetime.strptime(d, "%Y%m%d").weekday() < 5 for d in got)
    assert len(got) <= tape.KV_DAYS
    early = datetime(2026, 10, 30, 12, 0, tzinfo=TPE)
    assert "20261030" not in tape.candidate_dates(early, set())


def test_collect_補抓沒收齊的日子_收齊的不再打Worker(lake, monkeypatch):
    now = datetime(2026, 10, 30, 14, 10, tzinfo=TPE)
    store.append("tape_5m", tape.parse(ndjson("2026-10-29")))       # 10-29 已收齊（有 13:30）
    called = []

    def fake_get(url, params=None, headers=None, **k):
        called.append(params["date"])
        assert headers["Origin"].startswith("https://")
        return ndjson("2026-10-30") if params["date"] == "20261030" else None

    monkeypatch.setattr(http, "get", fake_get)
    df = tape.collect(now)
    assert "20261029" not in called and called[0] == "20261030"
    assert set(df.ts.str[:10]) == {"2026-10-30"}
    assert "20261028" in df.attrs["miss"]                            # 404 的日子記在 miss
    # 寫進去之後再跑一次：10-30 也收齊了，不再重抓
    store.append("tape_5m", df)
    called.clear()
    tape.collect(now)
    assert "20261030" not in called


def test_collect_全部失敗回空不拋例外(lake, monkeypatch):
    monkeypatch.setattr(http, "get", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    df = tape.collect(datetime(2026, 10, 30, 14, 10, tzinfo=TPE))
    assert df.empty


def test_主程式寫狀態檔(lake, monkeypatch):
    monkeypatch.setattr(config, "STATE", lake / "_state")
    (lake / "_state").mkdir()
    monkeypatch.setattr(tape, "_tpe_now", lambda: datetime(2026, 10, 30, 14, 10, tzinfo=TPE))
    monkeypatch.setattr(http, "get", lambda url, params=None, **k: ndjson("2026-10-30") if params["date"] == "20261030" else None)
    assert tape.main() == 0
    st = json.loads((lake / "_state" / "tape_last.json").read_text(encoding="utf-8"))
    assert st["days"] == ["2026-10-30"] and st["added"] > 0
    assert len(store.read("tape_5m")) == st["added"]


def test_已註冊且按月分割():
    assert config.TABLES["tape_5m"] == ["ts", "code"] and "tape_5m" in config.PARTITION_MONTHLY
