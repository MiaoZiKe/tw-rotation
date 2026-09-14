"""mis（證交所基本市況報導）的 parser，對著 2026-09-14 真的打回來的回應驗。

這一組要守住的是兩件事：

1. **開高低收要一字不差**。這是我們敢拿 mis 補「今天」的唯一理由 ——
   同一天三個來源（mis／FinMind／後來的 openapi）比對過，OHLC 完全吻合。
2. **量與值是暫定值，而且要標記出來**。mis 的 `v` 是盤中累計、不含盤後定價交易，
   逐檔差幅 −0.5%～−15.3%（fixture 裡有實測數字）。沒有 `px_source` 標記的話，
   隔天沒有人知道哪些列是估的。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.sources import mis

FIX = Path(__file__).resolve().parents[1] / "docs" / "fixtures" / "mis_getstockinfo_20260914.json"


@pytest.fixture
def payload():
    return json.loads(FIX.read_text(encoding="utf-8"))


@pytest.fixture
def snapshot(payload, monkeypatch):
    monkeypatch.setattr(mis.http, "get", lambda *a, **k: payload["response"])
    return mis.price_snapshot([("2330", "TWSE"), ("6488", "TPEX"),
                               ("1101", "TWSE"), ("0050", "TWSE")])


# ------------------------------------------------------------------ 基本形狀

def test_解得出來而且欄位對得上price_daily(snapshot):
    assert not snapshot.empty
    for col in ("date", "code", "name", "market", "open", "high", "low",
                "close", "change", "volume", "turnover", "px_source"):
        assert col in snapshot.columns, f"少了 {col}"


def test_日期取自回應不是執行當下(snapshot):
    """非交易日打這支會回上一個交易日的資料而且不標示，用執行日期當主鍵一定錯。"""
    assert set(snapshot["date"]) == {"2026-09-14"}


def test_指數不進price_daily(snapshot):
    """t00 是加權指數，不是股票。混進來會讓「上漲家數」之類的統計爆掉。"""
    assert "t00" not in set(snapshot["code"])


def test_上市上櫃分得出來(snapshot):
    mk = dict(zip(snapshot["code"], snapshot["market"]))
    assert mk["2330"] == "TWSE"
    assert mk["6488"] == "TPEX"      # ex=otc


# ------------------------------------------------------------------ 開高低收

def test_開高低收與官方一字不差(snapshot):
    r = snapshot[snapshot["code"] == "2330"].iloc[0]
    assert (r["open"], r["high"], r["low"], r["close"]) == (2385.0, 2395.0, 2380.0, 2380.0)
    o = snapshot[snapshot["code"] == "6488"].iloc[0]
    assert (o["open"], o["high"], o["low"], o["close"]) == (880.0, 907.0, 872.0, 900.0)


def test_漲跌用昨收算(snapshot):
    r = snapshot[snapshot["code"] == "2330"].iloc[0]
    assert r["change"] == pytest.approx(2380.0 - 2410.0)


def test_沒成交時退到最佳買價(payload, monkeypatch):
    """z 是 '-' 的時候不能回 None —— 停牌或早盤沒成交的股票也要有價格可以顯示。"""
    row = dict(payload["_no_trade_example"])
    monkeypatch.setattr(mis.http, "get", lambda *a, **k: {"rtcode": "0000", "msgArray": [row]})
    df = mis.price_snapshot([("9999", "TWSE")])
    assert df.iloc[0]["close"] == pytest.approx(49.5)      # 最佳買價第一檔

    row2 = dict(row); row2["b"] = ""
    monkeypatch.setattr(mis.http, "get", lambda *a, **k: {"rtcode": "0000", "msgArray": [row2]})
    df2 = mis.price_snapshot([("9999", "TWSE")])
    assert df2.iloc[0]["close"] == pytest.approx(50.0)      # 再退到昨收


# ------------------------------------------------------------------ 量與值的口徑

def test_成交量換成股(snapshot):
    """mis 的 v 是張，price_daily 的 volume 是股。"""
    assert snapshot[snapshot["code"] == "2330"].iloc[0]["volume"] == 18172 * 1000


def test_成交值用典型價估(snapshot):
    """mis 沒有成交金額欄位，用「股數 × (高+低+收)/3」估。"""
    r = snapshot[snapshot["code"] == "1101"].iloc[0]
    expect = 35582 * 1000 * (24.4 + 23.9 + 23.9) / 3
    assert r["turnover"] == pytest.approx(expect)


def test_估出來的成交值誤差要在可接受範圍(snapshot, payload):
    """對著官方值檢查估算本身。1101 的量幾乎沒差，所以它反映的是『估價法』準不準。"""
    official = payload["_official_turnover"]["1101"]
    got = snapshot[snapshot["code"] == "1101"].iloc[0]["turnover"]
    assert abs(got - official) / official < 0.01      # 實測 −0.3%


def test_量的口徑差異要被記錄下來(payload):
    """這不是驗程式，是釘住『我們知道這件事』：mis 的量不含盤後定價交易，
    而且差幅逐檔不同（0.5%～15%），所以不能當成一致的縮放去校正。"""
    off = payload["_official_volume_lots"]
    mis_lots = {r["c"]: int(r["v"]) for r in payload["response"]["msgArray"] if r.get("v")}
    gaps = {c: (mis_lots[c] - off[c]) / off[c] for c in off}
    assert all(g < 0 for g in gaps.values()), "mis 應該一律少於官方（少了盤後定價那段）"
    assert min(gaps.values()) < -0.10, "2330 實測 −15.3%，差幅可以很大"
    assert max(gaps.values()) > -0.02, "1101 實測 −0.55%，差幅也可以很小 → 不是固定比例"


def test_全部標成暫定值(snapshot):
    """沒有這個標記，隔天就分不出哪些列是估的。
    store.append 是後到覆蓋，openapi 的官方值進來時會蓋掉它們。"""
    assert set(snapshot["px_source"]) == {"mis"}


# ------------------------------------------------------------------ 失敗行為

def test_rtcode不是0000就回空(monkeypatch):
    monkeypatch.setattr(mis.http, "get", lambda *a, **k: {"rtcode": "5001", "rtmessage": "限流"})
    assert mis.price_snapshot([("2330", "TWSE")]).empty


def test_抓不到就回空不丟例外(monkeypatch):
    monkeypatch.setattr(mis.http, "get", lambda *a, **k: None)
    assert mis.price_snapshot([("2330", "TWSE")]).empty
    assert mis.latest_date() is None


def test_分批送(monkeypatch):
    """全市場約三千檔，一次送不完；要分批而且每批都要帶對代號。"""
    seen = []

    def fake_get(url, params=None, **k):
        seen.append((params or {}).get("ex_ch", ""))
        return {"rtcode": "0000", "msgArray": []}

    monkeypatch.setattr(mis.http, "get", fake_get)
    mis.quotes([(f"{i:04d}", "TWSE") for i in range(250)])
    assert len(seen) == 3                       # 100 + 100 + 50
    assert seen[0].count("|") == mis.BATCH - 1
    assert seen[0].startswith("tse_0000.tw|")


def test_上櫃用otc前綴(monkeypatch):
    seen = []
    monkeypatch.setattr(mis.http, "get",
                        lambda url, params=None, **k: (seen.append(params["ex_ch"]),
                                                       {"rtcode": "0000", "msgArray": []})[1])
    mis.quotes([("6488", "TPEX"), ("2330", "TWSE"), ("9999", None)])
    assert seen[0] == "otc_6488.tw|tse_2330.tw|tse_9999.tw"   # 市場別不明就當上市
