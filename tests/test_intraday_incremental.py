"""60 分 K 的增量抓取：只抓「資料湖最後一根之後」的那一段。

為什麼有這一組（Andy 2026-09-18）：以前 `build_payload` 每次部署都
`yahoo.intraday(..., "730d")` 從零重抓 400 檔，實測**部署 14 分鐘裡有 13 分 43 秒**
卡在那兩行 —— 昨天抓過的今天再抓一次，改一行 CSS 也照抓。通則見 DECISIONS #155。

這裡守住的是：**第二次以後不准再跟 Yahoo 要兩年**。
"""
from __future__ import annotations

import pandas as pd
import pytest

from pipeline import config, run_daily
from pipeline.sources import yahoo
from pipeline.util import store

TPE = "Asia/Taipei"


def _bars(rows):
    return pd.DataFrame([{"ts": ts, "code": c, "open": 1.0, "high": 1.0, "low": 1.0,
                          "close": 1.0, "volume": 1} for ts, c in rows])


# ------------------------------------------------------------------ period_for

def test_只缺幾天就不要跟人家要兩年():
    """這就是病根：要補 1 天卻去要 730 天。"""
    assert yahoo.period_for(1, "60m") == "4d"
    assert yahoo.period_for(3, "60m") == "6d"


def test_缺很久就補到保留上限為止():
    assert yahoo.period_for(9999, "60m") == "730d"
    assert yahoo.period_for(9999, "15m") == "60d"
    assert yahoo.period_for(9999, "1m") == "7d"     # Yahoo 的 1 分只留 7 天


def test_保留上限跟Andy拍板的一致():
    """1/5/15 分當天就好、60 分 730 天 —— 上限表是這個決策的依據（DECISIONS #156）。"""
    assert yahoo.INTRADAY_MAX_PERIOD["60m"] == "730d"
    assert yahoo.INTRADAY_MAX_PERIOD["1m"] == "7d"


# ------------------------------------------------------------------ intraday_since

@pytest.fixture
def spy(monkeypatch):
    """把真的 Yahoo 換掉，記錄「每次跟它要多長的區間」。"""
    calls = []

    def fake(codes, markets, interval, period, batch=40):
        calls.append({"interval": interval, "period": period, "codes": list(codes)})
        return _bars([("2026-09-17T13:00:00+08:00", "2330"),
                      ("2026-09-18T09:00:00+08:00", "2330"),
                      ("2026-09-18T10:00:00+08:00", "2330")])

    monkeypatch.setattr(yahoo, "intraday", fake)
    return calls


def test_資料湖空的時候補滿保留上限(spy):
    got = yahoo.intraday_since(["2330"], {}, None, "60m")
    assert spy[0]["period"] == "730d"
    assert len(got) == 3, "首次回補不該過濾掉任何一列"


def test_有資料之後只要新的那一段(spy):
    got = yahoo.intraday_since(["2330"], {}, "2026-09-17T13:00:00+08:00", "60m")
    assert spy[0]["period"] != "730d", f"第二次還在要兩年：{spy[0]['period']}"
    assert len(got) == 2, "應該只留 since 之後的兩根"
    assert all(str(t) > "2026-09-17T13:00:00+08:00" for t in got["ts"])


def test_since壞掉的時候不准把整批濾光(spy):
    """拿一個壞字串去比大小會把整批濾掉，症狀是「看起來抓到了、其實一列都沒寫進去」。"""
    got = yahoo.intraday_since(["2330"], {}, "不是時間", "60m")
    assert len(got) == 3, "解不出 since 就該全部留著，不是全部丟掉"


def test_Yahoo一筆都沒回也不會炸(monkeypatch):
    monkeypatch.setattr(yahoo, "intraday", lambda *a, **k: pd.DataFrame())
    assert yahoo.intraday_since(["2330"], {}, "2026-09-17T13:00:00+08:00", "60m").empty


# ------------------------------------------------------------------ 跟資料湖串起來

@pytest.fixture
def lake(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path)
    monkeypatch.setattr(config, "STATE", tmp_path)       # 確認無資料清單讀 backfill_progress，不能讀到真的那份
    store.append("price_daily", pd.DataFrame([
        {"date": "2026-09-18", "code": "2330", "market": "TWSE", "turnover": 9e9, "close": 1000.0},
        {"date": "2026-09-18", "code": "1101", "market": "TWSE", "turnover": 1e9, "close": 50.0},
    ]))
    run_daily.RESULT["steps"].pop("intraday.since", None)
    return tmp_path


def test_每日管線不再一次要兩年_第二次只補增量(lake, spy, monkeypatch):
    """★ 2026-09-30 改：名單擴到全市場（約 2,000 檔）之後，每日管線**連第一次都不准要 730 天**
    —— 兩年的歷史交給回補分批補（intraday60.backfill，見 tests/test_intraday_all.py），
    不然湖是空的那一天會一次對 Yahoo 打 2,000 檔 × 兩年。"""
    first = run_daily.collect_intraday_60m()
    assert spy[0]["period"] != "730d", f"每日管線不該要兩年：{spy[0]['period']}"
    store.append("intraday_60m", first)

    second = run_daily.collect_intraday_60m()
    assert spy[1]["period"] != "730d", f"第二次不該再要兩年：{spy[1]['period']}"
    assert run_daily.RESULT["steps"]["intraday.since"]["since"] == "2026-09-18T10:00:00+08:00"
    # 第二次 Yahoo 回的是同一段，逐檔只留最後一根之後 → 沒有新列；重跑也不會讓湖長出重複列（key = ts + code）
    assert second.empty
    store.append("intraday_60m", second)
    assert len(store.read("intraday_60m")) == 3


def test_挑代號照成交值由大到小(lake):
    codes, markets = run_daily.intraday_universe(limit=1)
    assert codes == ["2330"], codes
    assert markets["2330"] == "TWSE"


def test_還沒有價量資料時安靜跳過(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path)
    assert run_daily.collect_intraday_60m().empty
