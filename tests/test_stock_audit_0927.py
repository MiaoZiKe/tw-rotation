"""個股頁數據普查（2026-09-27，金融專家）。

Andy：「季的週期要對，我發現部分數據數據太少」。這支釘住普查抓到、已經修掉的幾件事：
1. 個股頁季損益／本益比歷史直接吃 financial_q 原表 —— 證交所那條路的 2026Q2 是「上半年累計」，
   1,040 檔的單季 EPS 被寫成兩季合計（2618 長榮航 2.24 元，單季其實 0.71）。
2. 季標籤要連續：缺季補空列，不准把 2017Q1 直接接到 2017Q3；年度累計遇缺季就停。
3. 年 EPS＝四季單季相加；四季不齊的過去年份不給數字，今年給「前 n 季」並標 partial。
4. 法定期限判定「此時此刻至少應該有到哪一季」。
5. AI 分析卡的「近四季 EPS」必須是連續四季。
6. 三大法人：回補計畫裡要有歷史步驟，落後的股票每天續補。
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import config, run_backfill  # noqa: E402
from pipeline.compute import analysis, stockpage  # noqa: E402
from pipeline.compute.fundamental import quarter_timing  # noqa: E402
from pipeline.util import http  # noqa: E402


def _q(code, y, q, eps, rev=100.0, gp=30.0, oi=10.0, ni=8.0, ann="auto"):
    if ann == "auto":
        ann = {1: f"{y}-05-15", 2: f"{y}-08-14", 3: f"{y}-11-14", 4: f"{y + 1}-03-31"}[q]
    return {"code": code, "year": y, "quarter": q, "eps": eps, "revenue": rev, "gross_profit": gp,
            "operating_income": oi, "net_income": ni, "announce_date": ann,
            "period_end": None, "industry": None if ann else "航運業"}


# ------------------------------------------------------------------ 1. 累計列還原

def test_證交所累計的Q2在個股頁要還原成單季():
    fin = pd.DataFrame([
        _q("2618", 2026, 1, 1.53, rev=605.0, gp=100.0, oi=60.0, ni=88.6),
        # 證交所 t187ap14：Q2 列是上半年累計，沒有 announce_date
        _q("2618", 2026, 2, 2.24, rev=1283.0, gp=210.0, oi=120.0, ni=132.1, ann=None),
    ])
    p = stockpage.profit_series(fin, "2618")
    q2 = p["quarters"][-1]
    assert q2[0] == "2026Q2"
    assert q2[5] == pytest.approx(0.71), "單季 EPS＝上半年 2.24 − Q1 1.53"
    assert q2[1] == pytest.approx(678.0), "單季營收也要減掉 Q1"
    assert q2[6] == pytest.approx(2.24), "年度累計＝Q1＋Q2 單季＝原本的上半年累計"
    assert q2[2] == pytest.approx(110 / 678 * 100, abs=0.1), "毛利率用還原後的單季金額算"


def test_本益比歷史的TTM用還原後的單季():
    rows = [_q("X", y, q, 1.0) for y in (2025,) for q in (1, 2, 3, 4)]
    rows.append(_q("X", 2026, 1, 1.0))
    rows.append(_q("X", 2026, 2, 2.0, ann=None))          # 上半年累計 2.0 → 單季 1.0
    fin = pd.DataFrame(rows)
    px = pd.DataFrame({"code": "X", "date": ["2026-08-20", "2026-08-21"], "close": [40.0, 40.0]})
    d = stockpage.pe_daily(px, fin, "X")
    last = d[d["period"] == "2026Q2"].iloc[-1]
    assert last["ttm_eps"] == pytest.approx(4.0), "TTM＝2025Q3＋Q4＋2026Q1＋2026Q2（各 1 元）"
    assert last["pe"] == pytest.approx(10.0)
    assert last["from"] == "2026-08-20", "證交所列沒有公布日 → 用法定期限 8/14 之後的第一個收盤"


# ------------------------------------------------------------------ 2. 季標籤連續

def test_缺季補空列而且年度累計在缺季之後停止():
    fin = pd.DataFrame([_q("Y", 2017, 1, 1.0), _q("Y", 2017, 3, 2.0), _q("Y", 2017, 4, 3.0),
                        _q("Y", 2018, 1, 4.0)])
    p = stockpage.profit_series(fin, "Y")
    labels = [r[0] for r in p["quarters"]]
    assert labels == ["2017Q1", "2017Q2", "2017Q3", "2017Q4", "2018Q1"]
    assert p["gaps"] == ["2017Q2"]
    q2 = p["quarters"][1]
    assert all(v is None for v in q2[1:]), "缺的季除了期別全部是空值"
    assert [r[6] for r in p["quarters"]] == [1.0, None, None, None, 4.0], "缺 Q2 → 同年之後不給累計；隔年 Q1 重新起算"
    assert p["quarters"][4][7] == pytest.approx(3.0), "EPS 年增＝本季 − 去年同季"


# ------------------------------------------------------------------ 3. 年度

def test_年EPS等於四季相加_今年標partial_過去缺季不給():
    rows = [_q("Z", 2024, q, 1.0 * q) for q in (1, 2, 3)]                 # 2024 缺 Q4
    rows += [_q("Z", 2025, q, 1.0) for q in (1, 2, 3, 4)]
    rows += [_q("Z", 2026, q, 2.0) for q in (1, 2)]
    p = stockpage.profit_series(pd.DataFrame(rows), "Z", asof="2026-09-24")
    y = {r["year"]: r for r in p["yearly"]}
    assert y[2025]["eps"] == pytest.approx(4.0) and y[2025]["partial"] is False
    assert y[2025]["gm"] == pytest.approx(30.0), "三率＝Σ毛利 ÷ Σ營收"
    assert y[2024]["eps"] is None and y[2024]["quarters"] == 3, "過去年份缺季不給全年數字"
    assert y[2026]["eps"] == pytest.approx(4.0) and y[2026]["partial"] is True and y[2026]["quarters"] == 2


def test_Q4來自證交所全年累計時等於年報減前三季():
    rows = [_q("W", 2025, q, 1.0) for q in (1, 2, 3)]
    rows.append(_q("W", 2025, 4, 5.0, rev=500.0, gp=150.0, oi=50.0, ni=40.0, ann=None))   # 全年 5.0
    p = stockpage.profit_series(pd.DataFrame(rows), "W")
    assert p["quarters"][-1][5] == pytest.approx(2.0), "Q4 單季＝全年 5.0 − 前三季 3.0"
    assert p["yearly"][-1]["eps"] == pytest.approx(5.0)


def test_空資料與沒有這一檔():
    assert stockpage.profit_series(pd.DataFrame(), "2330")["quarters"] == []
    p = stockpage.profit_series(pd.DataFrame([_q("A", 2025, 1, 1.0)]), "B", asof="2026-09-24")
    assert p["quarters"] == [] and p["yearly"] == [] and p["timing"]["status"] == "missing"


def test_營收為零時三率給空值不除以零():
    p = stockpage.profit_series(pd.DataFrame([_q("V", 2025, 1, 0.1, rev=0.0)]), "V")
    assert p["quarters"][0][2:5] == [None, None, None]


# ------------------------------------------------------------------ 4. 法定期限

@pytest.mark.parametrize("asof,latest,expected,mx,status", [
    ("2026-09-24", "2026Q2", "2026Q2", "2026Q2", "ok"),
    ("2026-08-13", "2026Q1", "2026Q1", "2026Q2", "ok"),        # Q2 期限還沒到，只有 Q1 也對
    ("2026-08-14", "2026Q1", "2026Q2", "2026Q2", "missing"),   # 期限當天（含）就應該有
    ("2026-10-20", "2026Q3", "2026Q2", "2026Q3", "ok"),        # 提早公布（期限 11/14 前）是真的有
    ("2026-09-24", "2026Q3", "2026Q2", "2026Q2", "future"),    # 季底都還沒到 → 資料一定錯
    ("2026-03-31", "2025Q4", "2025Q4", "2025Q4", "ok"),        # 年報期限 3/31
    ("2026-03-30", "2025Q3", "2025Q3", "2025Q4", "ok"),
    ("2026-05-15", "2025Q4", "2026Q1", "2026Q1", "missing"),
])
def test_法定期限判定(asof, latest, expected, mx, status):
    t = quarter_timing(asof, latest)
    assert (t["expected"], t["max_possible"], t["status"]) == (expected, mx, status)


# ------------------------------------------------------------------ 5. AI 分析卡

def test_AI分析的近四季EPS必須連續():
    q = [["2025Q1", 1, 1, 1, 1, 1.0, None, None, 1], ["2025Q2", 1, 1, 1, 1, 1.0, None, None, 1],
         ["2025Q3", None, None, None, None, None, None, None, None],
         ["2025Q4", 1, 1, 1, 1, 2.0, None, None, 1], ["2026Q1", 1, 1, 1, 1, 2.0, None, None, 1]]
    f = analysis.fund_facet({}, None, {"quarters": q})
    assert any("只有 2 季" in s for s in f["points"]), f["points"]
    assert not any("近四季 EPS：" in s for s in f["points"]), "跨過 2025Q3 缺季的四季不能相加"


# ------------------------------------------------------------------ 6. 三大法人回補

@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path / "data")
    monkeypatch.setattr(config, "STATE", tmp_path / "state")
    (tmp_path / "data").mkdir(); (tmp_path / "state").mkdir()
    monkeypatch.setattr(http, "_QUOTA_FILE", tmp_path / "state" / "finmind_quota.json")
    monkeypatch.setattr(run_backfill, "PROGRESS", tmp_path / "state" / "backfill_progress.json")
    run_backfill._cov_cache.clear()
    return tmp_path


def test_回補計畫裡有三大法人歷史步驟():
    assert any(s["datasets"] == "inst" and s["start"] <= "2016-01-01" for s in run_backfill.PLAN_DEFAULT)


def test_落後判定只挑有歷史而且最新交易日有成交的股票():
    price = pd.DataFrame({"code": ["A", "B", "C", "D"], "date": ["2026-09-24"] * 3 + ["2026-09-01"]})
    inst = pd.DataFrame({"code": ["A", "B", "D"], "date": ["2026-09-24", "2026-09-10", "2026-08-01"]})
    latest, codes = run_backfill.stale_inst_codes(inst, price, ["A", "B", "C", "D"])
    assert latest == "2026-09-24"
    assert codes == ["B"], "A 已是最新、C 一列都沒有（交給歷史步驟）、D 最新交易日沒成交"
    assert run_backfill.stale_inst_codes(pd.DataFrame(), price, ["A"]) == (None, [])


def test_每日續補只抓落後的股票並清掉舊的done鍵(sandbox, monkeypatch):
    from pipeline.util import store
    store.append("price_daily", pd.DataFrame({"date": ["2026-09-24", "2026-09-24"], "code": ["2330", "1101"],
                                              "close": [1.0, 1.0], "turnover": [2.0, 1.0]}))
    store.append("inst_daily", pd.DataFrame({"date": ["2026-09-24", "2026-09-20"], "code": ["2330", "1101"],
                                             "foreign": [1.0, 1.0]}))
    run_backfill._save_progress({"done": {"inst@fresh2026-09-23:1101": True, "revenue:2330": True}})
    monkeypatch.setattr(run_backfill, "target_codes", lambda limit: ["2330", "1101"])
    asked = []

    def fake(code, start, end=None, wait=False):
        asked.append((code, start))
        return pd.DataFrame({"date": ["2026-09-24"], "code": [code], "foreign": [5.0], "foreign_dealer": [0.0],
                             "foreign_total": [5.0], "trust": [0.0], "dealer_self": [0.0], "dealer_hedge": [0.0],
                             "dealer": [0.0], "inst_total": [5.0]})
    monkeypatch.setattr(run_backfill.finmind, "institutional", fake)
    assert run_backfill.refresh_stale_inst(run_backfill._progress(), date(2026, 9, 25)) is True
    assert asked == [("1101", "2026-09-10")], "只補落後的 1101，往回 14 天"
    prog = json.loads(run_backfill.PROGRESS.read_text())
    assert prog["complete"]["inst_fresh"]["date"] == "2026-09-25" and prog["complete"]["inst_fresh"]["done"]
    assert "inst@fresh2026-09-23:1101" not in prog["done"], "前一天的續補鍵要清掉"
    assert prog["done"].get("revenue:2330") is True, "其他鍵不動"
    # 同一天再跑：旗標已完成，一次都不問
    asked.clear()
    assert run_backfill.refresh_stale_inst(run_backfill._progress(), date(2026, 9, 25)) is True
    assert asked == []


def test_回補計畫有當沖借券與2009股利步驟():
    ds = {(s["datasets"], s["start"]) for s in run_backfill.PLAN_DEFAULT}
    assert ("daytrade+sbl", "2025-01-01") in ds
    assert ("dividend+divresult", "2009-01-01") in ds
    assert {"daytrade", "sbl"} <= set(run_backfill.DATA_KEYS)
    assert {"daytrade_daily", "sbl_daily"} <= set(config.TABLES)


# ------------------------------------------------------------------ 7. 籌碼：自營商拆分、當沖、借券賣

def test_法人列尾多自營商自行買賣與避險_前五欄位置不變():
    inst = pd.DataFrame({"code": "2344", "date": ["2026-09-23", "2026-09-24"], "foreign_total": [10124e3, -17824e3],
                         "trust": [-3272e3, -162e3], "dealer": [94e3, -9e3], "dealer_self": [100e3, 1e3],
                         "dealer_hedge": [-6e3, -10e3]})
    iv = stockpage.inst_series(inst, "2344")
    assert iv["daily"][-1][:4] == ["2026-09-24", -17824000.0, -162000.0, -9000.0]
    assert iv["daily"][-1][5:] == [1000.0, -10000.0]
    assert iv["columns"][5:] == ["dealer_self", "dealer_hedge"]


def test_資券列有當沖與借券賣_單位換成張_當沖率用原始成交量():
    mg = pd.DataFrame({"code": "X", "date": ["2026-09-23", "2026-09-24"], "margin_balance": [100.0, 101.0],
                       "short_balance": [5.0, 4.0], "margin_change": [1.0, 1.0], "short_change": [0.0, -1.0]})
    dt = pd.DataFrame({"code": "X", "date": ["2026-09-24", "2026-09-25"], "daytrade_volume": [20943000.0, 1000.0]})
    sb = pd.DataFrame({"code": "X", "date": ["2026-09-24"], "sbl_sell": [5000.0], "sbl_balance": [108592000.0]})
    px = pd.DataFrame({"code": "X", "date": ["2026-09-24", "2026-09-25"], "volume": [83772000.0, 0.0]})
    rows = stockpage.margin_series(mg, "X", daytrade=dt, sbl=sb, price=px)
    assert [r[0] for r in rows] == ["2026-09-23", "2026-09-24", "2026-09-25"], "三個來源的日期取聯集"
    r = rows[1]
    assert r[:5] == ["2026-09-24", 101.0, 4.0, 1.0, -1.0]
    assert r[5] == 20943.0 and r[6] == pytest.approx(25.0, abs=0.01), "當沖 20,943 張、當沖率約 25%"
    assert r[7] == 5.0 and r[8] == 108592.0
    assert rows[0][5:] == [None, None, None, None], "那天沒有當沖／借券資料 → None，不補 0"
    assert rows[2][6] is None, "成交量 0 → 當沖率不除以零"
    assert rows[2][1] is None
    assert stockpage.margin_series(None, "X") == []
    assert len(stockpage.MARGIN_COLUMNS) == len(r)


# ------------------------------------------------------------------ 8. 營收：去年同月、MoM 對日曆月

def test_營收去年同月與MoM對到正確月份_缺月不亂比():
    rev = pd.DataFrame({"code": "R", "ym": ["2025-01", "2025-02", "2025-03", "2026-01", "2026-03"],
                        "revenue": [100.0, 110.0, 120.0, 130.0, 150.0]})
    out = stockpage.revenue_series(rev, "R")
    m = {r[0]: r for r in out["monthly"]}
    assert m["2026-03"][6] == 120.0 and m["2026-03"][2] == pytest.approx(25.0), "YoY 對 2025-03"
    assert m["2026-03"][3] is None, "2026-02 缺 → MoM 不拿 2026-01 來比"
    assert m["2026-01"][3] is None, "2025-12 不在 → 不跟 2025-03 比"
    assert m["2026-03"][4] is None and m["2026-03"][5] is None, "缺 2 月 → 累計與累計 YoY 不給"
    assert m["2025-03"][4] == 330.0
    assert out["columns"][6] == "revenue_last_year"


# ------------------------------------------------------------------ 9. 除權息：所屬期間、殖利率、重複公告

def _ev(rows):
    return pd.DataFrame(rows, columns=["code", "period", "kind", "amount", "announce_date", "ex_date",
                                       "payment_date", "fiscal_year"])


def _rs(rows):
    return pd.DataFrame(rows, columns=["date", "code", "kind", "dividend", "before_price", "reference_price",
                                       "open_price"])


@pytest.mark.parametrize("raw,fy,lab", [("114年", 2025, "2025"), ("114年後半年度", 2025, "2025H2"),
                                         ("114年下半年", 2025, "2025H2"), ("113年前半年度", 2024, "2024H1"),
                                         ("114年第3季", 2025, "2025Q3"), ("", 2025, "2025"), (None, None, None)])
def test_股利所屬期間標籤(raw, fy, lab):
    assert stockpage.period_label(raw, fy) == lab


def test_同一期兩家來源寫法不同不會掛在即將除權息_殖利率用除息前收盤():
    ev = _ev([["2344", "114年下半年", "cash", 0.5, "2026-02-10", None, None, 2025],        # 證交所：沒有除息日
              ["2344", "114年後半年度", "cash", 0.5, "2026-03-12", "2026-03-27", "2026-05-04", 2025]])
    rs = _rs([["2026-03-27", "2344", "息", 0.5, 50.0, 49.5, 49.5]])
    d = stockpage.dividends(ev, rs, None, "2344", 171.5, asof="2026-09-24")
    assert d["upcoming"] == [], "早就除息了，不能再掛在『已公告、尚未除權息』"
    per = d["by_period"]
    assert len(per) == 1 and per[0]["period"] == "2025H2" and per[0]["cash"] == pytest.approx(0.5), "兩筆收成一期、不重複加"
    assert per[0]["cash_ex_date"] == "2026-03-27" and per[0]["status"] == "paid"
    assert per[0]["cash_yield"] == pytest.approx(1.0), "0.5 ÷ 除息前收盤 50"
    y26 = next(b for b in d["by_year"] if b["year"] == 2026)
    assert y26["cash_yield"] == pytest.approx(1.0)
    assert d["results"][0]["cash_yield"] == pytest.approx(1.0)


def test_年度殖利率_季配加總_沒配是0_金額不明是None():
    ev = _ev([["2330", "114年第1季", "cash", 5.0, "2025-06-01", "2025-06-12", None, 2025],
              ["2330", "114年第2季", "cash", 5.0, "2025-08-01", "2025-09-16", None, 2025]])
    rs = _rs([["2025-06-12", "2330", "息", 5.0, 1000.0, 995.0, 995.0],
              ["2025-09-16", "2330", "息", 5.0, 500.0, 495.0, 495.0],
              ["2023-07-20", "2330", "權息", 9.8, 106.5, 96.66, 96.7]])       # 含權又對不到公告
    d = stockpage.dividends(ev, rs, None, "2330", 1000.0, asof="2026-09-24")
    y = {b["year"]: b for b in d["by_year"]}
    assert y[2025]["cash_yield"] == pytest.approx(0.5 + 1.0), "Σ 每次現金 ÷ 各自除息前收盤"
    assert y[2024]["cash_yield"] == 0.0 and y[2024]["n"] == 0
    assert y[2023]["cash_yield"] is None, "金額不知道 → 殖利率也不知道"
    assert [p["period"] for p in d["by_period"]] == ["2025Q2", "2025Q1"], "由新到舊"


# ------------------------------------------------------------------ 10. 指標標籤

def test_指標標籤只陳述事實_符合不符合都回傳():
    yms = [f"{y}-{m:02d}" for y in (2025, 2026) for m in range(1, 13) if (y, m) <= (2026, 8)]
    rev = pd.DataFrame({"code": "T", "ym": yms,
                        "revenue": [100.0] * 12 + [130.0, 125.0, 140.0, 150.0, 160.0, 170.0, 180.0, 200.0]})
    fin = pd.DataFrame([_q("T", 2025, q, 1.0, rev=300.0, gp=100.0, oi=40.0) for q in (1, 2, 3, 4)]
                       + [_q("T", 2026, q, 2.0, rev=r, gp=r * 0.4, oi=r * 0.2) for q, r in ((1, 395.0), (2, 480.0))])
    t = {x["id"]: x for x in stockpage.stock_tags(rev, fin, "T")["items"]}
    assert t["rev_yoy3_20"]["hit"] is True and "26-08 +100.0%" in t["rev_yoy3_20"]["detail"]
    assert t["rev_high_m"]["hit"] is True and "19 個月" in t["rev_high_m"]["detail"]
    assert t["rev_high_q"]["hit"] is True
    assert t["q_rev_yoy_3of4_20"]["hit"] is None, "2025Q3、Q4 沒有去年同季可比 → 不判斷（不是不符合）"
    assert t["q_gm_3of4_30"]["hit"] is True and t["q_om_3of4_10"]["hit"] is True
    # 2026-10-04：「連三月>20%」成立 ⇒「連續 N 個月年增」必成立 → 去重，N 併進前者的 detail
    assert "rev_streak" not in t and "連續 8 個月" in t["rev_yoy3_20"]["detail"]
    assert t["eps_pos4"]["hit"] is True
    assert all(x["kind"] == "指標" for x in t.values())
    empty = stockpage.stock_tags(None, None, "T")
    assert empty["n_hit"] == 0 and all(x["hit"] is None for x in empty["items"])


# ------------------------------------------------------------------ 11. 董監持股（t187ap11，每月）

def test_董監持股明細彙總_同名只算一次_民國年月_經理人不算董監():
    from pipeline.sources import mops
    rows = [
        {"資料年月": "11508", "公司代號": "2344", "職稱": "董事長", "姓名": "甲", "目前持股": "1,000,000", "設質股數": "100,000"},
        {"資料年月": "11508", "公司代號": "2344", "職稱": "大股東", "姓名": "甲", "目前持股": "1,000,000", "設質股數": "0"},
        {"資料年月": "11508", "公司代號": "2344", "職稱": "獨立董事", "姓名": "乙", "目前持股": "0"},
        {"資料年月": "11508", "公司代號": "2344", "職稱": "監察人", "姓名": "丙", "目前持股": "500,000"},
        {"資料年月": "11508", "公司代號": "2344", "職稱": "總經理", "姓名": "丁", "目前持股": "200,000"},
        {"資料年月": "11508", "公司代號": "2344 ", "職稱 ": "董事", "姓名": "", "目前持股": "-"},   # 持股解析不出 → 丟掉
        {"資料年月": "", "公司代號": "1101", "職稱": "董事", "姓名": "戊", "目前持股": "10"},          # 沒年月 → 丟掉
    ]
    d = mops.parse_insider(rows, "TWSE")
    assert len(d) == 1
    r = d.iloc[0]
    assert r["ym"] == "2026-08" and r["code"] == "2344"
    assert r["director_shares"] == 1_500_000, "甲兼大股東只算一次；總經理不是董監"
    assert r["insider_shares"] == 1_700_000 and r["n_directors"] == 3
    assert r["director_pledged"] == 100_000
    assert mops.parse_insider([{"奇怪的鍵": 1}], "TWSE").empty
    assert mops.parse_insider([], "TWSE").empty


def test_董監持股比例用最近月底的集保總股數_太遠不除_超過100不給():
    ih = pd.DataFrame([{"ym": "2026-08", "code": "T", "director_shares": 1.2e8, "insider_shares": 1.5e8,
                        "director_pledged": 1.2e7, "n_directors": 9},
                       {"ym": "2026-03", "code": "T", "director_shares": 1.0e8, "insider_shares": 1.0e8,
                        "director_pledged": 0.0, "n_directors": 9},
                       {"ym": "2026-09", "code": "T", "director_shares": 2.0e9, "insider_shares": 2.0e9,
                        "director_pledged": 0.0, "n_directors": 9}])
    sh = pd.DataFrame([{"date": "2026-09-04", "code": "T", "level": 17, "shares": 1.0e9},
                       {"date": "2026-09-04", "code": "T", "level": 15, "shares": 6.0e8}])
    x = stockpage.insider_series(ih, sh, "T")
    m = {r["ym"]: r for r in x["monthly"]}
    assert m["2026-08"]["director_pct"] == pytest.approx(12.0) and m["2026-08"]["insider_pct"] == pytest.approx(15.0)
    assert m["2026-08"]["pledge_pct"] == pytest.approx(10.0) and m["2026-08"]["base_date"] == "2026-09-04"
    assert m["2026-03"]["director_pct"] is None and m["2026-03"]["director_shares"] == 1.0e8, "分母離月底 > 45 天 → 只給股數"
    assert m["2026-09"]["director_pct"] is None and m["2026-09"]["flag"] == "over100"
    assert x["latest"]["ym"] == "2026-09"
    assert stockpage.insider_series(None, sh, "T")["monthly"] == []
    assert stockpage.insider_series(ih, None, "T")["monthly"][0]["director_pct"] is None, "沒有集保 → 沒有比例"


# ------------------------------------------------------------------ 12. 主力替代口徑（三大法人）

def test_主力替代集中度_N日法人買賣超除以N日成交量_缺一天就不給():
    days = [f"2026-09-{d:02d}" for d in (1, 2, 3, 4, 7, 8, 9)]
    price = pd.DataFrame({"code": "T", "date": days, "volume": [1000.0] * 7})
    inst = pd.DataFrame({"code": "T", "date": [d for d in days if d != "2026-09-08"],
                         "foreign_total": [100.0, -50.0, 30.0, 20.0, 10.0, 40.0],
                         "trust": [0.0, 0.0, None, 0.0, 0.0, 0.0], "dealer": [0.0] * 6})
    x = stockpage.main_proxy_series(inst, price, "T")
    rows = {r[0]: r for r in x["daily"]}
    assert rows["2026-09-07"][3] == pytest.approx((100 - 50 + 30 + 20 + 10) / 5000 * 100), "5 日集中＝Σ買賣超 ÷ Σ量"
    assert rows["2026-09-03"][1] == 30, "只缺投信一欄 → 當 0，合計照算"
    assert rows["2026-09-08"][1] is None and rows["2026-09-08"][3] is None, "那天沒有法人資料 → None"
    assert rows["2026-09-09"][3] is None, "5 日窗內有缺天 → 不拿 4 天湊"
    assert rows["2026-09-07"][4] is None, "不到 20 天 → 20 日集中度 None"
    z = stockpage.main_proxy_series(inst, price.assign(volume=0.0), "T")
    assert all(r[3] is None for r in z["daily"]), "量為 0 不除"
    assert stockpage.main_proxy_series(None, price, "T")["daily"] == []
    assert stockpage.main_proxy_series(inst, pd.DataFrame(), "T")["daily"] == []
