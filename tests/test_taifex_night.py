"""台指期夜盤：探測腳本問對了沒、夜盤日 K 進不進得了資料湖。

為什麼要有這一支（2026-09-20）
------------------------------
Andy：「台指期夜盤怎麼可能沒數據，幫我更新走勢圖以及 K 線上去」。

前一輪的結論是「夜盤沒有現成的分時序列」，但那個結論是**在還沒正確問過一次**的情況下下的：
探測時送了 `{"SymbolID": ["TXFJ6-F"]}`（陣列），期交所回 400，訊息是
`Cannot deserialize instance of java.lang.String out of START_ARRAY token
 ... GetChartData1MReqDto["SymbolID"]` —— 它要的是**字串**。
改成字串之後夜盤回 200、822 筆（fixture：`docs/fixtures/taifex_night_probe.json`）。

所以這裡守三件事，每一件都對應一個真的踩過的坑：
  1. `getChartData1M` 的 `SymbolID` **一定是字串**（回到陣列就是回到那個 400）
  2. 近月合約代號是**從報價清單撈的**，不是寫死月份碼（月份每個月都在換）
  3. 時間欄位 `046000`（04:60:00，不是合法時間）要被算成 05:00，不是被丟掉也不是被當成 4 點 60 分

開發環境沒有對外網路，所以全部用實測 fixture 與假回應驗。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.sources import finmind
from scripts import probe_sources as ps

FIXTURE = Path(__file__).resolve().parents[1] / "docs" / "fixtures" / "taifex_night_probe.json"


# =============================================================== 探測腳本

def test_getChartData1M_的_SymbolID_一定要是字串():
    """送陣列就是 400。這條規則不能靠記憶，要靠測試守著。"""
    for p in ps.PROBES["taifex_night"]:
        if "getChartData1M" in p["url"]:
            assert isinstance(p["json"]["SymbolID"], str), f"{p['id']} 又送成陣列了"


def test_夜盤探測用_M_結尾的代號_日盤用_F():
    by = {p["id"]: p for p in ps.PROBES["taifex_night"]}
    assert by["taifex_chartdata_1m_night"]["symbol_from"]["suffix"] == "-M"
    assert by["taifex_chartdata_1m_day"]["symbol_from"]["suffix"] == "-F"


def test_近月代號是從報價清單撈出來的_不是寫死的():
    """拿 2026-09-19 的實測回應當輸入，挑出來的要跟實際值一致。

    挑法：跳過 `TXF-S`／`TXF-P`（臺指**現貨**參考列）之後，成交量最大的那一支。
    """
    fx = json.loads(FIXTURE.read_text(encoding="utf-8"))
    by = {r["id"]: r for r in fx["results"]}
    assert ps.pick_symbol(by["taifex_quotelist_day"], "-F") == "TXFJ6-F"
    assert ps.pick_symbol(by["taifex_quotelist_night"], "-M") == "TXFJ6-M"


def test_撈不到代號時要沿用預設值而且要記下來(monkeypatch):
    """不然事後看 fixture 會分不清「問錯合約」和「端點真的沒資料」。"""
    monkeypatch.setattr(ps.requests, "request",
                        lambda *a, **k: _Resp({"RtCode": "0", "RtData": {}}))
    rec = ps.one({"id": "c", "url": "https://mis.taifex.com.tw/futures/api/getChartData1M",
                  "json": {"SymbolID": "TXFJ6-M"}, "note": "n",
                  "symbol_from": {"probe": "沒有這一支", "suffix": "-M"}}, {})
    assert rec["symbol_used"] == "TXFJ6-M"
    assert "沒撈到" in rec["symbol_source"]


def test_實際送出去的_body_會被記進_fixture(monkeypatch):
    """『我到底問了什麼』要留下來，不然下一輪又得重猜一次。"""
    seen = {}

    def grab(method, url, headers=None, data=None, json=None, timeout=None):
        seen["json"] = json
        return _Resp({"RtCode": "0", "RtData": {"Ticks": []}})

    monkeypatch.setattr(ps.requests, "request", grab)
    prev = {"q": {"sample": {"RtData": {"QuoteList": [
        {"SymbolID": "TXF-P", "CTotalVolume": ""},
        {"SymbolID": "TXFK6-M", "CTotalVolume": "217"},
        {"SymbolID": "TXFJ6-M", "CTotalVolume": "21499"},
    ]}}}}
    rec = ps.one({"id": "c", "url": "https://mis.taifex.com.tw/futures/api/getChartData1M",
                  "json": {"SymbolID": "寫死的"}, "note": "n",
                  "symbol_from": {"probe": "q", "suffix": "-M"}}, prev)
    assert seen["json"] == {"SymbolID": "TXFJ6-M"}        # 真的送出去的是撈來的那一支
    assert rec["req"] == {"SymbolID": "TXFJ6-M"}


# =============================================================== 時間欄位那個坑

@pytest.mark.parametrize("t,start,want", [
    ("150100", 900, 901),          # 15:01
    ("235900", 900, 1439),         # 23:59
    ("000100", 900, 1441),         # 翌日 00:01 → 跨午夜 +1440
    ("050000", 900, 1740),         # 翌日 05:00 ＝ 夜盤收盤
    ("046000", 900, 1740),         # ★ 04:60:00 不是合法時間 → 進位成 05:00
    ("134500", 525, 825),          # 日盤 13:45，不可以被誤判成跨午夜
    ("084600", 525, 526),          # 日盤第一根
])
def test_分時的時間欄位換算(t, start, want):
    assert ps._mins(t, start) == want


def test_series_stats_會把怪時間與缺的分鐘數出來():
    """fixture 為了不肥會把中間截掉，所以「822 筆裡有幾個怪時間」要在截短**之前**算好。

    2026-09-20 就是這樣：拿回來的 fixture 只有頭 5 尾 2，看到 `046000`
    卻沒辦法確認它是偶發還是每個整點都有。這支就是為了不要再發生一次。
    """
    ticks = []
    for m in range(901, 1741):
        if m in (1000, 1001):                      # 故意挖兩個洞
            continue
        mm = m % 1440
        ticks.append(["%02d%02d00" % (mm // 60, mm % 60), "1", "2", "0", "1", "10"])
    ticks.insert(-1, ["046000", "1", "2", "0", "1", "36"])     # 跟 050000 同一分鐘
    j = {"RtData": {"Info": {"Sessions": [{"Start": "1500", "End": "0500"}]},
                    "Quote": {"CTotalVolume": str(838 * 10 + 36)}, "Ticks": ticks}}
    st = ps.series_stats(j, {"path": "RtData.Ticks", "session": "RtData.Info.Sessions",
                             "total": "RtData.Quote.CTotalVolume"})
    assert list(st["weird_times"]) == ["046000"]
    assert st["duplicate_minutes"] == [1740]       # 04:60 與 05:00 撞在一起
    assert st["missing_minutes"] == [1000, 1001]
    assert st["monotonic"] is True
    assert st["volume_matches_quote"] is True      # 每分鐘量加總＝Quote 的累計量


def test_長序列會被截短但要講出原本有幾筆():
    out = ps.shrink({"Ticks": [[str(i)] for i in range(822)]})
    assert len(out["Ticks"]) == 8                  # 頭 5 ＋ 省略註記 ＋ 尾 2
    assert "822" in out["Ticks"][5]                # 原本幾筆要留在截斷標記裡


# =============================================================== 夜盤日 K 進資料湖

def _fut_rows():
    """兩天 × 兩個交易時段 × （近月 ＋ 次月 ＋ 一組價差）。

    欄位與挑法都照 2026-09-15 對 FinMind `TaiwanFuturesDaily` 的實測：
    `contract_date` 帶 `/` 的是價差組合不是指數，每天取成交量最大的月份＝近月。
    """
    rows = []
    for d in ("2026-09-17", "2026-09-18"):
        for sess, base in (("position", 47000), ("after_market", 47400)):
            rows += [
                {"date": d, "trading_session": sess, "contract_date": "202610",
                 "open": base, "max": base + 80, "min": base - 60, "close": base + 30,
                 "spread": 30, "volume": 65760},
                {"date": d, "trading_session": sess, "contract_date": "202611",
                 "open": base + 150, "max": base + 200, "min": base + 100, "close": base + 180,
                 "spread": 10, "volume": 217},
                # 價差組合的量刻意灌到最大 —— 挑錯的話線會整條跑到 100 點附近
                {"date": d, "trading_session": sess, "contract_date": "202610/202611",
                 "open": 100, "max": 120, "min": 80, "close": 110, "spread": 1, "volume": 999999},
            ]
    return rows


def test_夜盤日K也要存進資料湖(monkeypatch):
    """Andy：「台指期夜盤怎麼可能沒數據」。

    以前 `futures_ohlc()` 刻意只取 `position`，等於把夜盤的歷史日 K 丟掉 ——
    而資料本來就在同一個回應裡，不多花一次 FinMind 額度（額度是這個專案最稀缺的東西）。
    """
    monkeypatch.setattr(finmind.http, "finmind_get", lambda *a, **k: _fut_rows())
    out = finmind.futures_ohlc("2026-09-17")
    assert set(out["symbol"]) == {"FUT", "FUT_N"}
    assert len(out) == 4                                   # 2 天 × 2 個時段
    day = out[out.symbol == "FUT"].sort_values("date")
    night = out[out.symbol == "FUT_N"].sort_values("date")
    # 兩個時段是兩條不同的線，不是同一份複製
    assert list(day["close"]) != list(night["close"])
    assert list(day["close"]) == [47030, 47030]
    assert list(night["close"]) == [47430, 47430]


def test_價差組合不可以被挑成近月(monkeypatch):
    monkeypatch.setattr(finmind.http, "finmind_get", lambda *a, **k: _fut_rows())
    out = finmind.futures_ohlc("2026-09-17")
    assert (out["close"] > 1000).all(), "價差組合（收盤 110）被挑進來了"


def test_只有日盤時不會因為夜盤空掉就整支回空(monkeypatch):
    rows = [r for r in _fut_rows() if r["trading_session"] == "position"]
    monkeypatch.setattr(finmind.http, "finmind_get", lambda *a, **k: rows)
    out = finmind.futures_ohlc("2026-09-17")
    assert set(out["symbol"]) == {"FUT"} and len(out) == 2


def test_完全沒資料時回空_DataFrame(monkeypatch):
    monkeypatch.setattr(finmind.http, "finmind_get", lambda *a, **k: [])
    assert finmind.futures_ohlc("2026-09-17").empty


def test_回補要求的代號集合仍然被滿足(monkeypatch):
    """`run_backfill.backfill_indices()` 用 `need - set(symbol)` 判斷齊不齊。

    多吐一個 `FUT_N` 不可以害它以為缺東西（那樣會永遠不標 done、每小時重補）。
    """
    monkeypatch.setattr(finmind.http, "finmind_get", lambda *a, **k: _fut_rows())
    out = finmind.futures_ohlc("2026-09-17")
    assert not ({"FUT"} - set(out["symbol"].astype(str)))


def test_欄位與加權櫃買那支一致(monkeypatch):
    """同一張表 `index_ohlc`，欄位對不上的話 `store.append()` 會寫出一張爛表。"""
    monkeypatch.setattr(finmind.http, "finmind_get", lambda *a, **k: _fut_rows())
    out = finmind.futures_ohlc("2026-09-17")
    assert list(out.columns) == ["date", "symbol", "open", "high", "low", "close",
                                 "change", "volume", "turnover"]
    # 日期一律是字串（store 的 key 是 date＋symbol，型別飄掉就會出現兩筆同一天）
    assert all(isinstance(v, str) for v in out["date"])


class _Resp:
    """假回應（跟 tests/test_probe_sources.py 同一個形狀）。"""

    def __init__(self, payload, status=200, ctype="application/json"):
        self._p = payload
        self.status_code = status
        self.headers = {"Content-Type": ctype}
        self.text = json.dumps(payload, ensure_ascii=False)
        self.content = self.text.encode("utf-8")

    def json(self):
        return self._p
