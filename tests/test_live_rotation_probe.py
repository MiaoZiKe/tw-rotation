"""盤中巡檢（scripts/live_rotation_probe.py）的判定邏輯。

巡檢本身要打線上網站，只能在 Actions 上跑；但「什麼算綠、什麼算紅」是純函式，
在這裡守住三態原則：非交易日／非盤中不可以變紅，盤中點沒動一定要紅。
"""
import importlib.util
import json
from pathlib import Path

_P = Path(__file__).resolve().parent.parent / "scripts" / "live_rotation_probe.py"
_spec = importlib.util.spec_from_file_location("live_rotation_probe", _P)
probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe)


def _snap(t, quote, pts, hit=265, err="", top="晶圓代工"):
    return {"t": t, "hasRlvState": True,
            "state": {"on": True, "at": 1, "quoteAt": quote, "hit": hit, "codes": 265, "reqs": 3,
                      "err": err, "cover": 41.2, "pts": {g: {"x": x, "y": y} for g, (x, y) in pts.items()}},
            "drawn": {g: {"x": x, "y": y, "live": True, "name": g} for g, (x, y) in pts.items()},
            "top": [{"name": top}], "rankTop": "矽光子"}


def _res(a, b):
    return {"url": "u", "started": "2026-09-24 10:00:00", "A": a, "B": b, "ticks": [{"t": "10:01", "quoteAt": "x", "err": ""}]}


def test_盤中點有動就是綠():
    r = probe.judge(_res(_snap("10:00", "10:00:05", {"a": (101, 99)}),
                         _snap("10:02", "10:02:05", {"a": (101.02, 99.01)})), strict=True)
    assert r["verdict"] == "pass"
    assert r["moved_top"][0]["gid"] == "a"


def test_盤中報價沒前進點也沒動一定紅():
    same = {"a": (101, 99), "b": (98, 102)}
    r = probe.judge(_res(_snap("10:00", "10:00:05", same), _snap("10:02", "10:00:05", same)), strict=True)
    assert r["verdict"] == "fail"
    assert {c["key"] for c in r["checks"] if c["gate"] and not c["pass"]} == {"quote", "move"}


def test_抓不到報價一定紅_盤後也一樣():
    s = {"a": (101, 99)}
    r = probe.judge(_res(_snap("14:00", "", s, hit=0, err="代理回 HTTP 520"),
                         _snap("14:02", "", s, hit=0, err="代理回 HTTP 520")), strict=False)
    assert r["verdict"] == "fail"


def test_盤後點沒動不算壞():
    s = {"a": (101, 99)}
    r = probe.judge(_res(_snap("14:00", "13:30:00", s), _snap("14:02", "13:30:00", s)), strict=False)
    assert r["verdict"] == "pass_off_hours"
    md = probe.summary_md(r)
    assert "不是盤中" in md and "❌" not in md


def test_自動桶不算進有動的點():
    a = _snap("10:00", "10:00:05", {"a": (101, 99)})
    b = _snap("10:02", "10:02:05", {"a": (101, 99)})
    a["drawn"]["ind_etf"] = {"x": 100, "y": 100, "live": False, "name": "ETF"}
    b["drawn"]["ind_etf"] = {"x": 100.5, "y": 100, "live": False, "name": "ETF"}   # 不該發生，但就算發生也不准灌水
    r = probe.judge(_res(a, b), strict=True)
    assert r["verdict"] == "fail"


def test_休市表判斷(monkeypatch):
    rows = [{"Name": "中秋節", "Date": "1151006", "Weekday": "二", "Description": "放假一日"},
            {"Name": "春節前最後交易日", "Date": "1160210", "Weekday": "三", "Description": "最後交易"}]

    class _R:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps(rows, ensure_ascii=False).encode("utf-8")

    monkeypatch.setattr(probe.urllib.request, "urlopen", lambda *a, **k: _R())
    import datetime as dt
    assert probe.fetch_holidays(dt.date(2026, 10, 6))[0]            # 休市
    assert probe.fetch_holidays(dt.date(2027, 2, 10))[0] is None    # 最後交易日是交易日
    assert probe.fetch_holidays(dt.date(2026, 9, 24))[0] is None    # 表上沒有


def test_休市表抓不到就交給報價日期(monkeypatch):
    def boom(*a, **k):
        raise OSError("no network")
    monkeypatch.setattr(probe.urllib.request, "urlopen", boom)
    import datetime as dt
    h, note = probe.fetch_holidays(dt.date(2026, 9, 24))
    assert h is None and "抓不到" in note
