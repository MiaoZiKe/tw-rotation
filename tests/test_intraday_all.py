"""個股 60 分 K 擴到全市場（2026-09-30）：名單、每日增量、回補分批與「確認無資料」。

起因：Andy 回報「有部分股票打開在小時間級別的周期裡面 1 小時 4 小時都會是找不到數據的狀況」。
資料湖實測只有 567 檔（全市場普通股約 1,980 檔），而且其中約 1/4 只有 2～15 根 ——
名單是「成交值前 400」、增量起點是「全表最後一根」，掉出前 400 的就再也不長。
這一組守住：
  1. 名單＝全市場普通股（與 run_backfill.market_codes() 同一份）＋成交值前段的 ETF；
  2. 每日續補只要最近幾天、逐檔只留自己最後一根之後的，而且跳過確認無資料的冷門股；
  3. 回補每輪有上限、進度寫進 backfill_progress（complete 鍵含 remaining），下一輪接續；
  4. Yahoo 回空要「連兩輪、而且同一輪 2330 拿得到」才記 no_data；整批回空又探不到 2330 ＝ 限流，收手不記。
全部用假回應，不打 Yahoo。
"""
from __future__ import annotations

import json

import pandas as pd
import pytest

from pipeline import config, intraday60, run_backfill, run_daily
from pipeline.sources import yahoo
from pipeline.util import store


def _bars(code, days, hours=(9, 10, 11, 12, 13)):
    return pd.DataFrame([{"ts": f"{d}T{h:02d}:00:00+08:00", "code": code, "open": 1.0, "high": 1.0,
                          "low": 1.0, "close": 1.0, "volume": 1.0} for d in days for h in hours])


@pytest.fixture
def lake(tmp_path, monkeypatch):
    """假資料湖：4 檔普通股（2330 上市、6488 上櫃、1101、9999 冷門）＋ 1 檔 ETF 0050 ＋ 1 檔權證。"""
    monkeypatch.setattr(config, "DATA", tmp_path)
    monkeypatch.setattr(config, "STATE", tmp_path / "_state")
    (tmp_path / "_state").mkdir()
    rows = []
    for d in ("2026-09-28", "2026-09-29"):
        for code, mk, tv in (("2330", "TWSE", 9e10), ("0050", "TWSE", 5e10), ("6488", "TPEX", 3e9),
                             ("1101", "TWSE", 1e9), ("9999", "TWSE", 1e5), ("030123", "TPEX", 9e11)):
            rows.append({"date": d, "code": code, "market": mk, "turnover": tv, "close": 10.0})
    store.append("price_daily", pd.DataFrame(rows))
    store.append("company_info", pd.DataFrame([
        {"code": c, "market": m} for c, m in (("2330", "TWSE"), ("6488", "TPEX"), ("1101", "TWSE"),
                                              ("9999", "TWSE"), ("0050", "TWSE"))]))
    monkeypatch.setattr(yahoo, "BATCH_PAUSE", 0)
    monkeypatch.setattr(run_backfill, "PROGRESS", tmp_path / "_state" / "backfill_progress.json")
    return tmp_path


class FakeYahoo:
    """記下每一次請求；`have` 裡的代號回 `days` 那幾天的 60 分 K，其餘回空。"""

    def __init__(self, have, days=("2026-09-28", "2026-09-29"), down=False, need_start=()):
        self.have, self.days, self.down, self.calls = set(have), days, down, []
        self.need_start = set(need_start)   # 這些代號只有送明確起日才拿得到（近兩年上市、730d 被換算到範圍外）

    def __call__(self, codes, markets, interval, period, batch=40, start=None):
        self.calls.append({"codes": list(codes), "period": period, "markets": dict(markets), "start": start})
        if self.down:
            return pd.DataFrame()
        parts = [_bars(c, self.days) for c in codes
                 if c in self.have and (start or c not in self.need_start)]
        return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


# ------------------------------------------------------------------ 1. 名單

def test_名單是全市場普通股加成交值前段ETF_濾掉權證(lake):
    codes, markets = intraday60.universe()
    assert set(codes) == {"2330", "0050", "6488", "1101", "9999"}, codes
    assert "030123" not in codes, "權證不該進分 K 名單"
    assert codes[:2] == ["2330", "0050"], "成交值大的排前面（回補額度中途用完時先補到熱門股）"
    assert markets["6488"] == "TPEX" and markets["2330"] == "TWSE", "市場別決定 Yahoo 的 .TW／.TWO"
    # 普通股部分與回補的 market_codes() 是同一份
    assert set(run_backfill.market_codes()) <= set(codes)


def test_上櫃股用TWO後綴(lake):
    _, markets = intraday60.universe()
    assert yahoo.symbol_of("6488", markets) == "6488.TWO"
    assert yahoo.symbol_of("2330", markets) == "2330.TW"


# ------------------------------------------------------------------ 2. 每日增量

def test_每日續補全名單只要最近幾天_逐檔只留自己最後一根之後(lake, monkeypatch):
    # 湖裡：2330 到 09-28 收盤；6488 只到 09-18（以前掉出前 400 就停了）；其餘沒有
    store.append("intraday_60m", pd.concat([_bars("2330", ["2026-09-28"]), _bars("6488", ["2026-09-18"])]))
    fake = FakeYahoo({"2330", "6488", "1101", "0050"})
    monkeypatch.setattr(yahoo, "intraday", fake)
    out, info = intraday60.daily_increment(now=pd.Timestamp("2026-09-30T18:30:00+08:00"))
    assert len(fake.calls) == 1
    assert set(fake.calls[0]["codes"]) == {"2330", "0050", "6488", "1101", "9999"}, "每日續補要涵蓋全市場"
    assert fake.calls[0]["period"] != "730d", "每日續補不准跟 Yahoo 要兩年（那是回補的事）"
    got = out.groupby("code")["ts"].agg(["min", "count"])
    assert got.loc["2330", "min"] == "2026-09-29T09:00:00+08:00" and got.loc["2330", "count"] == 5, \
        "2330 只該留 09-28 之後的 09-29 五根"
    assert got.loc["6488", "count"] == 10, "6488 的最後一根在 09-18，兩天都是新的"
    assert got.loc["1101", "count"] == 10, "湖裡沒有的代號全部都留"
    assert info["codes"] == 5


def test_每日續補天數夾在上下限(lake, monkeypatch):
    store.append("intraday_60m", _bars("2330", ["2026-06-01"]))       # 湖裡最新一根在四個月前
    fake = FakeYahoo(set())
    monkeypatch.setattr(yahoo, "intraday", fake)
    intraday60.daily_increment(now=pd.Timestamp("2026-09-30T18:30:00+08:00"))
    assert fake.calls[0]["period"] == yahoo.period_for(intraday60.DAILY_MAX_DAYS, "60m"), \
        "缺很久也只要 DAILY_MAX_DAYS，剩下的交給回補"


def test_每日續補跳過確認無資料的冷門股(lake, monkeypatch):
    (lake / "_state" / "backfill_progress.json").write_text(json.dumps(
        {"done": {"intraday_60m:9999": "no_data", "intraday_60m:2330": True}}))
    fake = FakeYahoo({"2330"})
    monkeypatch.setattr(yahoo, "intraday", fake)
    _, info = intraday60.daily_increment(now=pd.Timestamp("2026-09-30T18:30:00+08:00"))
    assert "9999" not in fake.calls[0]["codes"]
    assert info["skipped_no_data"] == 1


def test_run_daily的收集步驟改走全市場(lake, monkeypatch):
    fake = FakeYahoo({"2330", "6488"})
    monkeypatch.setattr(yahoo, "intraday", fake)
    run_daily.RESULT["steps"].pop("intraday.since", None)
    df = run_daily.collect_intraday_60m()
    assert set(df["code"]) == {"2330", "6488"}
    assert run_daily.RESULT["steps"]["intraday.since"]["codes"] == 5
    store.append("intraday_60m", df)
    # 第二輪：同一段不再新增（逐檔只留最後一根之後）
    assert run_daily.collect_intraday_60m().empty


def test_每日續補Yahoo全掛回空不炸(lake, monkeypatch):
    monkeypatch.setattr(yahoo, "intraday", FakeYahoo(set(), down=True))
    out, info = intraday60.daily_increment(now=pd.Timestamp("2026-09-30T18:30:00+08:00"))
    assert out.empty and info["rows"] == 0


# ------------------------------------------------------------------ 3. 回補分批

def test_回補每輪有上限_進度寫complete含remaining_下一輪接續(lake, monkeypatch):
    fake = FakeYahoo({"2330", "0050", "6488", "1101"})
    monkeypatch.setattr(yahoo, "intraday", fake)
    prog: dict = {}
    saves = []
    rec = intraday60.backfill(prog, save=lambda p: saves.append(1), per_run=2, batch=2)
    assert [c["period"] for c in fake.calls] == ["730d"], "回補才跟 Yahoo 要滿 730 天；每批都有資料就不必探 2330"
    assert rec["this_run"]["asked"] == 2 and rec["this_run"]["got"] == 2
    assert rec["remaining"] == {"intraday_60m": 3} and rec["done"] is False
    assert prog["complete"]["intraday_60m"] is rec, "要寫進 prog['complete']（backfill.yml 守門看它）"
    assert prog["done"]["intraday_60m:2330"] is True and prog["done"]["intraday_60m:0050"] is True
    assert saves, "每批寫完都要存進度（CI 中途被砍不會重抓）"
    assert set(store.read("intraday_60m")["code"]) == {"2330", "0050"}

    # 第二輪從第三檔接著補，前兩檔不再問
    fake.calls.clear()
    rec = intraday60.backfill(prog, per_run=2, batch=2)
    asked = [c for call in fake.calls for c in call["codes"] if call["period"] == "730d"]
    assert asked == ["6488", "1101"], asked
    assert rec["remaining"] == {"intraday_60m": 1}


def test_冷門股連兩輪回空才記確認無資料(lake, monkeypatch):
    fake = FakeYahoo({"2330", "0050", "6488", "1101"})     # 9999 永遠回空，但 2330 拿得到
    monkeypatch.setattr(yahoo, "intraday", fake)
    prog: dict = {"done": {f"intraday_60m:{c}": True for c in ("2330", "0050", "6488", "1101")}}
    rec = intraday60.backfill(prog, per_run=10)
    assert "intraday_60m:9999" not in prog["done"], "第一次回空不能就定案（可能只是那一批剛好出事）"
    assert prog[intraday60.TRIES_KEY]["9999"] == 1 and rec["remaining"] == {"intraday_60m": 1}
    rec = intraday60.backfill(prog, per_run=10)
    assert prog["done"]["intraday_60m:9999"] == "no_data"
    assert rec["done"] is True and rec["remaining"] == {"intraday_60m": 0} and rec["no_data"] == 1
    assert intraday60.no_data_codes(prog) == {"9999"}


def test_730d被拒的新上市股改用明確起日重抓(lake, monkeypatch):
    # 2026-09-30 實測：00937B、6933、7734 等 15 檔每輪都回「range must be within the last 730 days」
    fake = FakeYahoo({"2330", "0050", "6488", "1101"}, need_start={"6488"})
    monkeypatch.setattr(yahoo, "intraday", fake)
    prog: dict = {}
    rec = intraday60.backfill(prog, per_run=10)
    assert prog["done"]["intraday_60m:6488"] is True, "明確起日重抓拿到了，就算補完"
    retry = [c for c in fake.calls if c["start"]]
    assert retry and set(retry[0]["codes"]) == {"6488", "9999"}, "只重抓同一批裡拿不到的那幾檔"
    assert "intraday_60m:9999" not in prog["done"] and prog[intraday60.TRIES_KEY]["9999"] == 1, \
        "重抓也拿不到的照舊算回空一次"
    assert rec["this_run"]["got"] == 4


def test_整批回空又探不到2330是限流_收手不記no_data(lake, monkeypatch):
    fake = FakeYahoo(set(), down=True)
    monkeypatch.setattr(yahoo, "intraday", fake)
    prog: dict = {}
    rec = intraday60.backfill(prog, per_run=10, batch=2)
    assert rec["stopped"] and "限流" in rec["stopped"]
    assert not any(k.startswith("intraday_60m:") for k in prog.get("done", {}))
    assert not prog.get(intraday60.TRIES_KEY), "限流那一輪不能算冷門股回空一次"
    assert sum(1 for c in fake.calls if c["period"] == "730d") == 1, "探不到 2330 之後就不該再打下一批"


def test_湖裡已經有完整歷史的直接記done不花請求(lake, monkeypatch):
    days = pd.bdate_range("2024-09-02", "2026-09-29").strftime("%Y-%m-%d").tolist()
    store.append("intraday_60m", pd.concat([_bars("2330", days), _bars("6488", days[-3:])]))
    fake = FakeYahoo({"0050", "6488", "1101"})
    monkeypatch.setattr(yahoo, "intraday", fake)
    prog: dict = {}
    rec = intraday60.backfill(prog, per_run=10)
    asked = [c for call in fake.calls for c in call["codes"] if call["period"] == "730d"]
    assert "2330" not in asked, "完整歷史已在湖裡，不必再跟 Yahoo 要兩年"
    assert "6488" in asked, "只有最近幾根的（以前掉出前 400）要補歷史"
    assert rec["this_run"]["marked_from_lake"] == 1


def test_個股頁狀態三種(lake):
    prog = {"done": {"intraday_60m:9999": "no_data"}}
    assert intraday60.state_of("2330", 100, prog) == "ok"
    assert intraday60.state_of("9999", 0, prog) == "none"
    assert intraday60.state_of("1101", 0, prog) == "pending"


# ------------------------------------------------------------------ 4. run_backfill 串接

def test_run_backfill的intraday資料集只跑分K_不碰FinMind(lake, monkeypatch):
    monkeypatch.setattr(yahoo, "intraday", FakeYahoo({"2330", "0050", "6488", "1101"}))
    monkeypatch.setattr(run_backfill, "finmind_reachable",
                        lambda *_: pytest.fail("intraday 只打 Yahoo，不該做 FinMind 健檢"))
    monkeypatch.setattr("sys.argv", ["run_backfill", "--datasets", "intraday"])
    assert run_backfill.main() == 0
    prog = json.loads((lake / "_state" / "backfill_progress.json").read_text())
    assert prog["complete"]["intraday_60m"]["remaining"] == {"intraday_60m": 1}
    assert len(set(store.read("intraday_60m")["code"])) == 4


def test_不在名單的代號算確認無資料_不講還在回補(lake):
    """成交值排不進前段的 ETF 不在名單裡，永遠不會補 —— 個股頁不能寫「還在回補」讓人一直等。"""
    names = set(intraday60.universe()[0])
    assert intraday60.state_of("00999", 0, {}, names) == "none"
    assert intraday60.state_of("1101", 0, {}, names) == "pending"


# ------------------------------------------------------------------ 5. 前端分 K 檔（build_payload）

def test_分K檔精簡格式_日期一次_HHMM_價格去尾巴():
    from pipeline import build_payload as bp
    bars = pd.DataFrame([
        {"ts": "2026-09-28T09:00:00+08:00", "open": 52.29999923706055, "high": 53.0, "low": 52.0, "close": 52.5, "volume": 1234.0},
        {"ts": "2026-09-28T13:00:00+08:00", "open": 52.5, "high": 52.6, "low": 52.1, "close": float("nan"), "volume": 99.0},
        {"ts": "2026-09-29T09:00:00+08:00", "open": 1010.0, "high": 1015.0, "low": 1005.0, "close": 1010.0, "volume": 5e6},
    ])
    j = bp._m60_payload("2330", bars, "2026-09-29")
    assert j["v"] == 1 and j["n"] == 3 and j["tz"] == "+08:00"
    assert [d[0] for d in j["days"]] == ["2026-09-28", "2026-09-29"], "同一天只寫一次日期"
    assert j["days"][0][1][0] == [900, 52.3, 53, 52, 52.5, 1234], "float32 尾巴要去掉、整數不帶 .0"
    assert j["days"][0][1][1][0] == 1300 and j["days"][0][1][1][4] is None, "NaN 要變 null（JSON 不吃 NaN）"
    assert j["days"][1][1][0] == [900, 1010, 1015, 1005, 1010, 5000000]
    json.dumps(j, allow_nan=False)


def test_分K只讀最近幾個月分割_每檔給最後幾根(lake, monkeypatch):
    from pipeline import build_payload as bp
    monkeypatch.setattr(bp, "M60_PAGE_BARS", 7)
    monkeypatch.setattr(bp, "M60_READ_MONTHS", 1)
    store.append("intraday_60m", pd.concat([_bars("2330", ["2026-08-31"]),
                                            _bars("2330", ["2026-09-28", "2026-09-29"])]))
    got = bp._m60_lake()
    assert set(got) == {"2330"}
    assert len(got["2330"]) == 7, "每檔只給最後 M60_PAGE_BARS 根"
    assert got["2330"]["ts"].min() >= "2026-09-01", "只讀最近 M60_READ_MONTHS 個月的分割"
