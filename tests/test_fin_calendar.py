"""財經日曆涵蓋本月＋下個月（Andy 2026-11-01：「財經日曆也一樣每週更新」）。全部用假資料，不打真 API。"""
import pandas as pd

from pipeline.compute import earnings as E
from pipeline.util import freshness


def _conf(code, d):
    return {"d": d, "k": "conf", "code": code, "name": code, "status": "公告", "title": "法說"}


def test_estimate_conf_每季一場推到下個月():
    got = E.estimate_conf([_conf("2330", "2026-09-22"), _conf("1101", "2026-10-15")], "2026-10-30", "2027-03-29")
    by = {x["code"]: x for x in got}
    assert by["2330"]["d"] == "2026-12-22" and by["2330"]["status"] == "預估" and by["2330"]["k"] == "cest"
    assert by["1101"]["d"] == "2027-01-15"
    assert pd.Timestamp(by["2330"]["d"]).weekday() < 5


def test_estimate_conf_已公告就不重複推():
    ann = [_conf("2330", "2026-09-22"), {**_conf("2330", "2026-12-20"), "k": "invite"}]   # 前後 21 天內已有公告
    assert E.estimate_conf(ann, "2026-10-30", "2027-03-29") == []


def test_estimate_conf_週末順延到前一個營業日():
    d = E.estimate_conf([_conf("2330", "2026-09-12")], "2026-10-30", "2027-03-29")[0]["d"]   # 12/12 是週六
    assert d == "2026-12-11"


def test_coverage_分開算預估與已公告():
    ev = [{"d": "2026-11-05", "k": "conf", "status": "公告"}, {"d": "2026-12-03", "k": "cest", "status": "預估"},
          {"d": "2026-12-10", "k": "rev", "status": "期限"}, {"d": "2026-12-09", "k": "fomc", "status": "排程"}]
    c = E.coverage(ev, "2026-11-02")
    assert c["2026-12"]["conf"] == {"announced": 0, "est": 1}
    assert c["2026-12"]["rep"]["announced"] == 1 and c["2026-12"]["fed"]["announced"] == 1
    assert list(c) == ["2026-11", "2026-12"]


def test_日期範圍含下個月_且YAML涵蓋2027年一月():
    ev = E.macro_events(E.load_macro_yaml(), None, "2026-11-01", "2027-01-31")
    assert any(e["k"] == "fomc" and e["d"].startswith("2027-01") for e in ev)
    assert any(e["k"] == "fomc" and e["d"] == "2026-12-09" for e in ev)
    m = E.market_events("2026-11-01", "2027-01-31")
    assert {e["d"] for e in m if e["k"] == "rev"} == {"2026-11-10", "2026-12-10", "2027-01-10"}


def _cov(rep=1, conf=1, fed=1):
    mk = lambda n: {"announced": n, "est": 0}
    return {"2026-11": {"rep": mk(1), "conf": mk(1), "fed": mk(1)}, "2026-12": {"rep": mk(rep), "conf": mk(conf), "fed": mk(fed)}}


def test_guard_下個月FED空白亮燈():
    w = freshness.fin_cal_guard(_cov(fed=0), "2026-11-02", fred_fetched="2026-11-01", mops_last="2026-11-01")
    assert [x["label"] for x in w] == ["財經日曆・FED 消息"] and w[0]["reason"] == "empty_next_month"


def test_guard_法說空白_要去年同月有才亮():
    assert freshness.fin_cal_guard(_cov(conf=0), "2026-11-02", fred_fetched="2026-11-01", mops_last="2026-11-01") == []
    w = freshness.fin_cal_guard(_cov(conf=0), "2026-11-02", last_year={"conf": 12}, fred_fetched="2026-11-01", mops_last="2026-11-01")
    assert w and w[0]["last_year_rows"] == 12


def test_guard_預估算數_不亮燈():
    cov = _cov(conf=0)
    cov["2026-12"]["conf"]["est"] = 3
    assert freshness.fin_cal_guard(cov, "2026-11-02", last_year={"conf": 12}, fred_fetched="2026-11-01", mops_last="2026-11-01") == []


def test_guard_來源超過8天沒更新或從沒抓到_亮燈():
    w = freshness.fin_cal_guard(_cov(), "2026-11-20", fred_fetched="2026-11-01", mops_last=None)
    assert {x["label"] for x in w} == {"財經日曆・FRED 日程", "財經日曆・重大訊息"}
    assert all(x["reason"] == "source_stale" for x in w)
