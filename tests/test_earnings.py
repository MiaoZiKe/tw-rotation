"""財報日曆（pipeline/compute/earnings.py、sources/macro.release_calendar）與 earnings.json 結構。

這些測試釘住的是畫面上會寫出來的口徑：哪些是「公告」、哪些是「預估」、預估怎麼推、
FED 日程 FRED 優先 YAML 退回、台灣時間的夏令換算、分析句子的門檻。改口徑時兩邊（畫面文字、這裡）一起改。
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from pipeline import config
from pipeline.compute import earnings as E
from pipeline.sources import macro

ROOT = Path(__file__).resolve().parent.parent


# ------------------------------------------------------------------ 日期工具
def test_民國日期與季別解析():
    assert E.roc_date("公告本公司115年第三季法人說明會將於115年10月15日召開") == "2026-10-15"
    assert E.roc_date("沒有日期") is None
    assert E.roc_date("115年2月30日") is None            # 不存在的日子不硬湊
    assert E.subject_quarter("本公司將召開線上法說會說明115年第3季營運成果") == "2026Q3"
    assert E.subject_quarter("115年度第四季財務報告") == "2026Q4"


def test_法定期限與下一個要公布的季():
    assert E.deadline(2026, 3) == "2026-11-14"
    assert E.deadline(2026, 4) == "2027-03-31"
    assert E.quarter_for("2026-10-02") == (2026, 3)
    assert E.quarter_for("2026-11-14") == (2026, 3)
    assert E.quarter_for("2027-02-01") == (2026, 4)
    assert E.quarter_for("2026-04-10") == (2026, 1)


def test_台灣時間依美國夏令換算():
    assert E.tw_time("2026-10-14", "08:30") == "10/14 20:30"      # 夏令 +12
    assert E.tw_time("2026-11-10", "08:30") == "11/10 21:30"      # 11/1 起冬令 +13
    assert E.tw_time("2026-10-28", "14:00") == "10/29 02:00"      # FOMC 跨日
    assert E.tw_time("2026-12-09", "14:00") == "12/10 03:00"


# ------------------------------------------------------------------ 大公司名單
def test_市值前50只算四碼普通股():
    val = pd.DataFrame({"code": ["2330", "0050", "00878", "2454", "6488", "9999"],
                        "close": [1, 1, 1, 1, 1, 1], "market_cap": [9e12, 8e12, 7e12, 5e12, 4e12, None]})
    u = E.universe(val, {"2330": "台積電"}, n=2)
    assert [x["code"] for x in u] == ["2330", "2454"]
    assert u[0]["name"] == "台積電" and u[0]["rank"] == 1 and u[1]["name"] == "2454"


# ------------------------------------------------------------------ 重大訊息 → 公司事件
def _mops(rows):
    return pd.DataFrame(rows, columns=["date", "time", "code", "subject", "occurred"])


def test_重大訊息分出法說會_受邀_董事會_已公布_並排除更正():
    m = _mops([
        ["2026-09-29", "1", "2330", "公告本公司115年第三季法人說明會將於115年10月15日召開", "2026-10-15"],
        ["2026-09-21", "1", "3711", "公告本公司將受邀參加「CLSA Flagship Investors Forum」之法說訊息", "2026-09-22"],
        ["2026-09-29", "1", "2383", "公告本公司115年第三季財務報告董事會預計召開日期為\r\n115年10月28日", "2026-09-29"],
        ["2026-08-12", "1", "2454", "本公司董事會通過115年第二季合併財務報告", "2026-08-12"],
        ["2026-09-30", "1", "2317", "更正本公司115年第二季合併財務報告部分內容", "2026-09-30"],
        ["2026-09-30", "1", "9999", "公告本公司召開法人說明會", "2026-10-01"],        # 不在名單內
    ])
    ev = E.mops_events(m, {"2330", "3711", "2383", "2454", "2317"})
    got = {(e["code"], e["k"], e["d"]) for e in ev}
    assert got == {("2330", "conf", "2026-10-15"), ("3711", "invite", "2026-09-22"),
                   ("2383", "board", "2026-10-28"), ("2454", "report", "2026-08-12")}
    assert all(e["status"] == "公告" and "t187ap04" in e["src"] for e in ev)
    assert next(e for e in ev if e["code"] == "2383")["q"] == "2026Q3"


def test_預估日_沒紀錄標法定期限_有公告不重複_有紀錄往前推():
    univ = [{"code": "2330"}, {"code": "2454"}, {"code": "2317"}]
    ann = [{"d": "2026-10-15", "k": "conf", "code": "2330"},
           # 2454：過去兩季分別早於期限 14、10 天 → 中位數 12 天
           {"d": "2026-07-31", "k": "report", "code": "2454"},
           {"d": "2026-05-05", "k": "conf", "code": "2454"}]
    est = E.estimate_events(univ, ann, "2026-10-02", "2027-03-01")
    by = {e["code"]: e for e in est}
    assert "2330" not in by                                   # 已公告的不再放預估
    assert by["2317"]["d"] == "2026-11-14" and "法定期限" in by["2317"]["basis"]
    assert by["2454"]["d"] == "2026-11-02" and "中位數早於法定期限 12 天" in by["2454"]["basis"]
    assert all(e["status"] == "預估" and e["q"] == "2026Q3" for e in est)


def test_台股期限_月營收10日與季報期限():
    ev = E.market_events("2026-10-01", "2026-11-30")
    assert {(e["k"], e["d"]) for e in ev} == {("rev", "2026-10-10"), ("rev", "2026-11-10"), ("qdl", "2026-11-14")}
    assert next(e for e in ev if e["d"] == "2026-10-10")["title"] == "9 月營收公布期限"


# ------------------------------------------------------------------ FED 日程
CFG = {"verified": "測試", "fomc": {"source": "x", "meetings": [
    {"start": "2026-10-27", "end": "2026-10-28", "sep": False, "minutes": "2026-11-18"},
    {"start": "2026-12-08", "end": "2026-12-09", "sep": True, "minutes": "2026-12-30"}]},
    "releases": {"cpi": {"source": "bls", "dates": [{"date": "2026-10-14", "ref": "2026 年 9 月"}]},
                 "nfp": {"source": "bls", "dates": [{"date": "2026-11-06", "ref": "2026 年 10 月"}]}}}


def test_FED日程_YAML退回():
    ev = E.macro_events(CFG, None, "2026-10-01", "2026-12-31")
    ks = {(e["k"], e["d"]) for e in ev}
    assert ("fomc", "2026-10-28") in ks and ("minutes", "2026-11-18") in ks and ("cpi", "2026-10-14") in ks
    sep = next(e for e in ev if e["d"] == "2026-12-09")
    assert sep["sep"] and "點陣圖" in sep["title"] and sep["tw"] == "12/10 03:00"
    assert "退回值" in next(e for e in ev if e["k"] == "cpi")["src"]


def test_FED日程_FRED優先_只採用最近一次抓取():
    cal = pd.DataFrame([
        {"date": "2026-10-15", "release": "cpi", "release_id": 10, "fetched": "2026-09-01"},   # 舊抓取、後來改期 → 不採用
        {"date": "2026-10-14", "release": "cpi", "release_id": 10, "fetched": "2026-10-01"},
        {"date": "2026-11-10", "release": "cpi", "release_id": 10, "fetched": "2026-10-01"},
    ])
    ev = [e for e in E.macro_events(CFG, cal, "2026-10-01", "2026-12-31") if e["k"] == "cpi"]
    assert [e["d"] for e in ev] == ["2026-10-14", "2026-11-10"]
    assert all("FRED" in e["src"] for e in ev)
    # FRED 沒有的 nfp 照樣用 YAML
    assert any(e["k"] == "nfp" for e in E.macro_events(CFG, cal, "2026-10-01", "2026-12-31"))


def test_FRED公布日程_沒有金鑰回空_有回應時只留窗內(monkeypatch):
    monkeypatch.setattr(config, "FRED_KEY", "")
    assert macro.release_calendar().empty
    rows = macro.parse_release_dates({"release_dates": [{"release_id": 10, "date": "2026-10-14"},
                                                        {"release_id": 10, "date": "2030-01-01"}, {"date": "bad"}]},
                                     "cpi", 10, "2026-01-01", "2027-01-01")
    assert rows == [{"date": "2026-10-14", "release": "cpi", "release_id": 10}]


def test_FRED觀測值_年增率與非農變化():
    months = pd.date_range("2025-01-01", "2026-08-01", freq="MS").strftime("%Y-%m-%d")
    rows = [{"date": d, "series": "CPIAUCSL", "value": 100 + i} for i, d in enumerate(months)]
    rows += [{"date": d, "series": "PAYEMS", "value": 1000 + 10 * i} for i, d in enumerate(months)]
    rows += [{"date": "2026-09-18", "series": "DFEDTARL", "value": 4.0}, {"date": "2026-09-18", "series": "DFEDTARU", "value": 4.25}]
    snap = E.macro_snapshot(pd.DataFrame(rows))
    assert snap["cpi_yoy"]["date"] == "2026-08" and snap["cpi_yoy"]["value"] == f"{(119 / 107 - 1) * 100:.1f}%"
    assert snap["nfp_change"]["value"] == "+10 千人"
    assert snap["policy"]["value"] == "4.00%–4.25%"
    assert E.macro_snapshot(pd.DataFrame()) == {}


# ------------------------------------------------------------------ 分析句子
def _rev(yoys):
    cols = ["ym", "revenue", "yoy", "mom", "cum", "cum_yoy", "revenue_last_year"]
    rows = [[f"2026-{i + 1:02d}", 1e10, y, 1.0, None, 20.0, 1e10 / (1 + y / 100)] for i, y in enumerate(yoys)]
    return {"columns": cols, "monthly": rows}


def test_營收動能_加速放緩持平():
    r = E.section_revenue(E._cols(_rev([10, 10, 10, 30, 30, 30]), "monthly"))
    assert r["trend"] == "加速" and r["tone"] == 1 and "連續 6 個月年增為正" in "".join(r["lines"])
    assert E.section_revenue(E._cols(_rev([30, 30, 30, 10, 10, 10]), "monthly"))["trend"] == "放緩"
    assert E.section_revenue(E._cols(_rev([10, 10, 10, 12, 12, 12]), "monthly"))["trend"] == "持平"


def test_本次財報看點_季內月營收合計():
    rows = E._cols(_rev([10, 10, 10, 10, 10, 10, 50, 50]), "monthly")   # 7、8 月有資料
    s = E.section_focus(rows, [], "2026Q3")
    assert "已公布 7、8 月營收" in s["lines"][0] and "+50.0%" in s["lines"][0]
    assert "還沒有公布" in E.section_focus([], [], "2026Q3")["lines"][0]


def test_估值位置_百分位與少於8季不排():
    hist = [{"pe": v} for v in range(10, 30)]          # 20 季：10～29 倍
    s = E.section_valuation(28.5, hist, 100.0, "2026-10-02")
    assert s["pos"] == 95 and "偏高" in s["lines"][1]
    assert E.section_valuation(20, hist[:5], 100.0, "2026-10-02")["pos"] is None
    assert "不計算本益比" in E.section_valuation(None, hist, 100.0, "2026-10-02")["lines"][0]


def test_分析文字不含買賣建議用語():
    s = json.dumps([E.section_revenue(E._cols(_rev([1, 2, 3, 4, 5, 6]), "monthly")),
                    E.section_valuation(28.5, [{"pe": v} for v in range(10, 30)], 100.0, "x")], ensure_ascii=False)
    for w in ("建議", "買進", "賣出", "目標價"):
        assert w not in s


# ------------------------------------------------------------------ build() 與 earnings.json 結構
def test_build_小資料組出完整結構():
    names = {"2330": "台積電", "2454": "聯發科"}
    val = pd.DataFrame({"code": ["2330", "2454"], "close": [2500.0, 1500.0], "market_cap": [6e13, 2e12], "pe": [29.0, 20.0]})
    px = pd.DataFrame({"date": ["2026-10-01", "2026-10-02"] * 2, "code": ["2330", "2330", "2454", "2454"],
                       "close": [2490.0, 2500.0, 1490.0, 1500.0], "volume": [1e7] * 4})
    inst = pd.DataFrame({"date": ["2026-10-02"], "code": ["2330"], "foreign_total": [1e6], "trust": [0.0], "dealer": [0.0], "inst_total": [1e6]})
    mops = _mops([["2026-09-29", "1", "2330", "公告本公司115年第三季法人說明會將於115年10月15日召開", "2026-10-15"]])
    d = E.build(val=val, names=names, latest="2026-10-02", price=px, price_adj=px, revenue=pd.DataFrame(),
                financial=pd.DataFrame(), inst=inst, news=None, material_news=mops, macro=None, macro_cal=None, cfg=CFG)
    assert d["asof"] == "2026-10-02" and d["universe"]["n"] == 2
    ks = {(e["k"], e.get("code")) for e in d["events"]}
    assert ("conf", "2330") in ks and ("fomc", None) in ks
    assert not any(e["k"] in ("est", "rev", "qdl") or e.get("status") == "預估" for e in d["events"])   # Andy：不可以有推估數據
    assert d["companies"]["2330"]["next"]["d"] == "2026-10-15" and d["companies"]["2330"]["target"] == "2026Q3"
    assert any(s["key"] == "inst" for s in d["companies"]["2330"]["secs"])
    assert d["fed"]["snap"] == {} and "fomc" in d["fed"]["next"]
    assert [e["d"] for e in d["events"]] == sorted(e["d"] for e in d["events"])


SEED = ROOT / "site" / "earnings_seed.json"


@pytest.mark.skipif(not SEED.exists(), reason="沒有種子檔")
def test_種子檔結構():
    d = json.loads(SEED.read_text(encoding="utf-8"))
    for k in ("v", "asof", "window", "universe", "events", "companies", "fed"):
        assert k in d
    assert d["universe"]["n"] == len(d["universe"]["list"]) == len(d["companies"]) > 0
    kinds = {e["k"] for e in d["events"]}
    assert {"fomc", "cpi", "est"} <= kinds
    for e in d["events"]:
        assert len(e["d"]) == 10 and e["status"] in ("公告", "預估", "排程", "期限") and e.get("src")
        if e["k"] == "est":
            assert e["status"] == "預估" and e.get("basis")
        if e.get("code"):
            assert e["code"] in d["companies"]
    for c in d["companies"].values():
        for s in c["secs"]:
            assert s["src"] and s["lines"]


def test_YAML日程格式():
    cfg = E.load_macro_yaml()
    ms = cfg["fomc"]["meetings"]
    assert len(ms) == 8 and all(m["start"] < m["end"] < m["minutes"] for m in ms)
    for k, spec in cfg["releases"].items():
        assert k in E.FED_INFO and spec["source"].startswith("https://")


def test_conf_detail_and_conf_all():
    """法說會：內文欄位照抽（日期／時間／地點／擇要），且 conf_all 收名單外公司；名單外的財報董事會不收。"""
    import pandas as pd
    det = ("符合條款第四條第XX款：12\r\n事實發生日：115/09/30\r\n1.召開法人說明會之日期：115/09/30\r\n"
           "2.召開法人說明會之時間：14 時 00 分 \r\n3.召開法人說明會之地點：線上法說會\r\n4.法人說明會擇要訊息：115年第二季公司營運狀況\r\n")
    x = E.conf_detail(det)
    assert x == {"d": "2026-09-30", "time": "14:00", "place": "線上法說會", "brief": "115年第二季公司營運狀況"}
    assert E.conf_detail("") == {}
    m = pd.DataFrame([
        {"news_id": "a", "code": "1103", "name": "嘉泥", "date": "2026-09-23", "subject": "公告本公司召開法人說明會相關資訊", "occurred": "2026-09-30", "detail": det},
        {"news_id": "b", "code": "1104", "name": "環泥", "date": "2026-09-23", "subject": "公告本公司董事會通過第二季財務報告", "occurred": "2026-09-23", "detail": ""},
    ])
    ev = E.mops_events(m, {"2330"}, conf_all=True)
    assert [(e["code"], e["k"], e["d"], e.get("time"), e.get("place")) for e in ev] == [("1103", "conf", "2026-09-30", "14:00", "線上法說會")]
    assert E.mops_events(m, {"2330"}) == []
