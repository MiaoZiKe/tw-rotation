"""P-1107-06 事件前後歷史走勢（pipeline/compute/eventstudy.py）。

法遵審查 docs/feature_proposals/p1107_06_legal_review.md 第四節 R1～R15：這支驗 Python 端的 R3、R4、R5、R7、R8、R9、R13、R2（JSON 不含禁用字）。
報酬用手算的小例子對：交易日 10 天、個股與指數各自一條價格。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.compute import eventstudy as es  # noqa: E402

CAL = [f"2024-01-{d:02d}" for d in (2, 3, 4, 5, 8, 9, 10, 11, 12, 15, 16, 17, 18, 19, 22, 23, 24, 25, 26, 29, 30, 31)]
# 個股：從 100 起每天 +1；指數：從 1000 起每天 +5
PX = {d: 100.0 + i for i, d in enumerate(CAL)}
IX = {d: 1000.0 + 5 * i for i, d in enumerate(CAL)}
W = ((2, 2),)


def test_交易日窗與超額報酬_手算():
    # 事件日 01-09（第 5 個交易日，索引 5）→ 第 −2 天＝索引 3（01-05，103）、第 +2 天＝索引 7（01-11，107）
    r = es.event_returns(["2024-01-09"], CAL, PX, IX, windows=W)
    ev = r["events"][0]
    raw, ex = ev["r"]["2"]
    assert ev["d0"] == "2024-01-09"
    assert raw == pytest.approx(107 / 103 - 1, abs=1e-5)
    # 指數：索引 3＝1015、索引 7＝1035
    assert ex == pytest.approx((107 / 103 - 1) - (1035 / 1015 - 1), abs=1e-5)


def test_事件日不是交易日_順延到下一個交易日():
    # 01-06（星期六）→ 第 0 天＝01-08（索引 4）；−2＝索引 2（102）、+2＝索引 6（106）
    r = es.event_returns(["2024-01-06"], CAL, PX, IX, windows=W)
    ev = r["events"][0]
    assert ev["d"] == "2024-01-06" and ev["d0"] == "2024-01-08"
    assert ev["r"]["2"][0] == pytest.approx(106 / 102 - 1, abs=1e-5)


def test_視窗沒走完不納入_而且不輸出未來日期():
    # 最後一個交易日 01-31（索引 21）：01-30 事件 +2 天超出 → 不納入，記 pending
    r = es.event_returns(["2024-01-30", "2024-02-05"], CAL, PX, IX, windows=W)
    assert r["events"] == [] and r["pending"] == 2


def test_兩端沒有收盤的事件不納入():
    px = dict(PX); px.pop("2024-01-05")
    r = es.event_returns(["2024-01-09"], CAL, px, IX, windows=W)
    assert r["events"] == []


def test_樣本少於5不給中位數與上漲比例():
    s = es.stats([0.01, 0.02, 0.03])
    assert s == {"n": 3, "few": True, "up": None, "med": None, "best": None, "worst": None}
    s = es.stats([0.03, -0.01, 0.02, 0.05, -0.04])
    assert s["n"] == 5 and not s["few"] and s["up"] == 3 and s["med"] == pytest.approx(0.02)
    assert s["best"] == pytest.approx(0.05) and s["worst"] == pytest.approx(-0.04)


def test_財報只用實際公告日_缺的季計入排除():
    rep = [{"k": "report", "code": "1234", "d": "2024-01-09", "q": "2023Q3"},
           {"k": "report", "code": "1234", "d": "2024-01-10", "q": "2023Q3"},   # 同一季第二次公告：取最早
           {"k": "board", "code": "1234", "d": "2024-01-05", "q": "2023Q4"},    # 董事會「預計召開」不是公告財報
           {"k": "report", "code": "1234", "d": "2024-01-11", "q": None}]       # 主旨沒寫季 → 公告日前最近一季（2023Q4）
    eq = es.earnings_dates(rep)
    assert eq == {"1234": {"2023Q3": "2024-01-09", "2023Q4": "2024-01-11"}}
    pl = es.stock_payload("1234", "2024-01-31", CAL, PX, IX, [], eq["1234"], ["2023Q1", "2023Q2", "2023Q3", "2023Q4"])
    assert len(pl["earn"]["events"]) == 2 and {e["q"] for e in pl["earn"]["events"]} == {"2023Q3", "2023Q4"}
    assert pl["earn"]["excl"] == 2 and pl["earn"]["excl_from"] == "2023Q1" and pl["earn"]["excl_to"] == "2023Q2"


def test_代號過濾_期貨選擇權權證不納入():
    assert es.eligible("2330") and es.eligible("0050") and es.eligible("00878") and es.eligible("00679B")
    for c in ("00631L", "00632R", "00635U", "030012", "2881A", "912000", "TXF"):
        assert not es.eligible(c), c
    dr = pd.DataFrame({"date": ["2024-01-09", "2024-01-09", "2024-01-10", "2024-01-11"],
                       "code": ["2330", "030012", "2330", "00631L"], "kind": ["息", "息", "權", "除息"]})
    assert es.dividend_dates(dr) == {"2330": ["2024-01-09"]}


def test_export_單檔JSON與索引_不含禁用字(tmp_path):
    price = pd.DataFrame([{"code": "2330", "date": d, "close": v} for d, v in PX.items()]
                         + [{"code": "1101", "date": d, "close": v} for d, v in PX.items()])
    idx = pd.DataFrame([{"symbol": "TSE", "date": d, "close": v} for d, v in IX.items()]
                       + [{"symbol": "OTC", "date": d, "close": 1.0} for d in CAL])
    dr = pd.DataFrame({"date": ["2024-01-09", "2024-01-23"], "code": ["2330", "2330"], "kind": ["息", "除息"]})
    res = es.export(tmp_path, price, idx, dr, [], None, "2024-01-31")
    files = sorted(p.name for p in (tmp_path / "eventstudy").glob("*.json"))
    assert files == ["2330.json", "_index.json"] and res["codes"] == 1      # 沒有事件的 1101 不寫檔
    assert json.loads((tmp_path / "eventstudy" / "_index.json").read_text(encoding="utf-8"))["codes"] == ["2330"]
    j = json.loads((tmp_path / "eventstudy" / "2330.json").read_text(encoding="utf-8"))
    assert j["code"] == "2330" and len(j["div"]["events"]) == 2 and j["div"]["sum"]["5"]["ex"]["few"]
    assert all(e["d"] <= j["asof"] for e in j["div"]["events"])
    txt = json.dumps(j, ensure_ascii=False)
    for w in ("勝率", "搶息", "穩賺", "必漲", "卡位", "上車", "下車", "埋伏", "買點", "賣點", "進場", "出場", "布局"):
        assert w not in txt, w
    assert "含息" in j["basis"]["stock"] and "不含息" in j["basis"]["bench"]


ROOT = Path(__file__).resolve().parent.parent
_ALLOWED = {"eventstudy.js", "industry.js", "mobile3.js", "features.js", "plan_presets.js", "index.html"}


def test_R9_R10_不進分享圖卡社群貼文與其他頁():
    """這份統計只准個股頁讀：其他前端檔、社群產圖／發文腳本都不准引用 eventstudy（R9、R10）。"""
    hits = [p.name for p in (ROOT / "site").glob("*.js") if p.name not in _ALLOWED and "eventstudy" in p.read_text(encoding="utf-8", errors="ignore")]
    hits += [str(p.relative_to(ROOT)) for p in (ROOT / "scripts").glob("social*.py") if "eventstudy" in p.read_text(encoding="utf-8", errors="ignore")]
    assert not hits, hits


def test_R15_功能公告不寫數字與禁用字():
    items = json.loads((ROOT / "site" / "notices" / "features.json").read_text(encoding="utf-8"))
    it = next(x for x in items if x["id"] == "f-20261109-event-study")
    txt = it["title"] + it["body"]
    assert not any(ch.isdigit() for ch in txt), txt
    for w in ("勝率", "搶息", "抓住", "行情", "穩賺", "必漲", "買點", "賣點", "進場", "出場"):
        assert w not in txt, w
