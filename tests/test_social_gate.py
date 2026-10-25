"""社群貼文「資料是不是當天」把關（scripts/social_gate.py、social_snap.decide，2026-10-26）。不連網。"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import social_gate as g  # noqa: E402
import social_snap as ss  # noqa: E402

H = g.load_holidays()
# 靜態表「事前」的樣子：10/23 颱風停市是臨時的，事前不在表上 → 用這份測「只靠資料也判斷得出來」
H0 = {k: v for k, v in H.items() if k != "2026-10-23"}
CLOSE = ["inst-today", "streak-foreign", "streak-trust", "fut-oi", "retail-ratio"]
CREDIT = ["credit-ratio", "credit-rank", "credit-short"]


def T(s):
    return datetime.fromisoformat(s).replace(tzinfo=g.TPE)


# ---------- 交易日 ----------
def test_休市日表讀得到光復節補假與事後補登的颱風停市():
    assert "2026-10-26" in H and "光復" in H["2026-10-26"]
    assert "2026-10-10" in H and "颱風" in H["2026-10-23"] and "2026-10-22" not in H


def test_交易日看資料不看星期幾():
    assert g.trading_day("2026-10-22", ["2026-10-22"], H)[0] is True
    ok, why = g.trading_day("2026-10-26", ["2026-10-26"], H)       # 週一，但是休市日：資料怎麼說都不算
    assert ok is False and "休市" in why
    assert g.trading_day("2026-10-27", ["2026-10-23"], H)[0] is False   # 平日但資料沒有今天 → 不當交易日


def test_下一個交易日開盤跳過週末與補假():
    assert g.next_open("2026-10-22", H) == T("2026-10-27T09:00")     # 10/23 颱風、週末、10/26 補假 → 週二
    assert g.next_open("2026-10-22", H0) == T("2026-10-23T09:00")    # 事前的表不知道颱風
    assert g.next_open("2026-10-08", H) == T("2026-10-12T09:00")     # 10/09 補假、10/10 國慶、週末


# ---------- 盤後法人 ----------
def test_盤後法人_每張都是今天才發():
    d = {k: "2026-10-22" for k in CLOSE}
    assert g.close_gate("2026-10-22", d, H) == (True, "")


def test_盤後法人_有一張是昨天就不發並寫出哪張():
    # 10/22 23:02 那篇：文案寫 10/22，數字是 10/21
    d = {k: "2026-10-22" for k in CLOSE}
    d["streak-trust"] = d["streak-foreign"] = "2026-10-21"
    ok, why = g.close_gate("2026-10-22", d, H)
    assert ok is False and "streak-trust＝2026-10-21" in why and "streak-foreign＝2026-10-21" in why


def test_盤後法人_缺日期也不發_休市日不發():
    d = {k: "2026-10-22" for k in CLOSE}
    d["fut-oi"] = ""
    assert g.close_gate("2026-10-22", d, H)[0] is False
    assert g.close_gate("2026-10-26", {k: "2026-10-23" for k in CLOSE}, H)[0] is False


def test_decide_close_資料日取卡片自己的():
    cd = {k: "2026-10-22" for k in CLOSE}
    ok, d, why = ss.decide("close", T("2026-10-22T18:40"), {"inst_date": "2026-10-22"}, {}, cd, CLOSE, H)
    assert ok and d == "2026-10-22"
    ok, d, why = ss.decide("close", T("2026-10-23T00:10"), {"inst_date": "2026-10-22"}, {}, cd, CLOSE, H)
    assert not ok and "2026-10-23" in why       # 過了午夜，22 號的資料不是「今天」→ 不發


# ---------- 盤後融資 ----------
def _mf(d, short_d=None, meta_d=None):
    return ({"data_date": meta_d or d},
            {"margin": {"rows": [{"d": "2026-10-21", "ratio": 170.0}, {"d": d, "ratio": 168.0}],
                        "rank": {"d": d, "rows": []}, "short_rank": {"d": short_d or d, "rows": []}}})


def test_融資_資料日之後到下一個交易日開盤前才發():
    meta, mf = _mf("2026-10-21")
    cd = {k: "2026-10-21" for k in CREDIT}
    ev = {"last_trade": "2026-10-21", "live": True}
    assert ss.decide("credit", T("2026-10-22T05:10"), meta, mf, cd, CREDIT, H, ev)[0] is True
    ok, d, why = ss.decide("credit", T("2026-10-22T09:00"), meta, mf, cd, CREDIT, H, {"last_trade": "2026-10-22", "live": True})
    assert ok is False and d == "2026-10-21"         # 10/22 開盤、即時成交日已是 10/22 → 舊的不發
    ok, d, why = ss.decide("credit", T("2026-10-22T10:00"), meta, mf, cd, CREDIT, H, {})
    assert ok is False and "開盤" in why


def test_融資_颱風臨時休市_表上沒有也照資料順延():
    # 2026-10-23（五）颱風全日休市（事前不在表上），10/26 光復節補假，10/27 復市：
    # 10/22 的融資在 10/26 凌晨仍是「最近一個已收盤的交易日」→ 可以發，不是舊資料
    ev = {"last_trade": "2026-10-22", "live": True}
    ok, why = g.credit_gate(T("2026-10-26T00:30"), "2026-10-22", H0, **ev)
    assert ok is True and "2026-10-23" in why and "臨時休市" in why and "10/27 09:00" in why
    assert g.credit_gate(T("2026-10-27T09:00"), "2026-10-22", H0, **ev)[0] is False   # 10/27 復市開盤 → 不再發
    # 10/23 09:00～09:30 分不出「還沒成交」跟「休市」→ 先不發
    ok, why = g.credit_gate(T("2026-10-23T09:10"), "2026-10-22", H0, **ev)
    assert ok is False and "分不出" in why
    # 查不到即時成交日：只能靠事前的表 → 保守不發（寧可少發）
    ok, why = g.credit_gate(T("2026-10-26T00:30"), "2026-10-22", H0)
    assert ok is False and "無法確認" in why
    # 即時成交日比資料日新 → 有更新的交易日，不發
    assert g.credit_gate(T("2026-10-23T20:00"), "2026-10-22", H0, "2026-10-23", True)[0] is False


def test_盤後法人_颱風臨時休市不發_也不誤判成資料缺漏():
    cd = {k: "2026-10-22" for k in CLOSE}
    ok, why = g.close_gate("2026-10-23", cd, H0, "2026-10-22", True, T("2026-10-23T18:40"))
    assert ok is False and "臨時休市" in why and "不是資料缺漏" in why
    # 對照：今天真的有開盤（即時成交日＝今天）但卡片還是昨天 → 寫「資料還沒更新／缺漏」
    ok, why = g.close_gate("2026-10-22", {k: "2026-10-21" for k in CLOSE}, H0, "2026-10-22", True, T("2026-10-22T18:40"))
    assert ok is False and "缺漏" in why and "臨時休市" not in why


def test_盤中_颱風臨時休市報價停在前一天():
    ok, why = g.intraday_gate(T("2026-10-23T09:35"), {"20261022"}, H0)
    assert ok is False and "臨時休市" in why


def test_融資_融券排行不同一天就不發():
    meta, mf = _mf("2026-10-23", short_d="2026-10-22")
    ok, d, why = ss.decide("credit", T("2026-10-24T05:10"), meta, mf, {}, CREDIT, H)
    assert ok is False and "融券" in why


def test_融資_還沒收盤不發():
    assert g.credit_gate(T("2026-10-23T11:00"), "2026-10-23", H)[0] is False


# ---------- 盤中 ----------
def test_盤中_交易日盤中且報價是今天才發():
    assert g.intraday_gate(T("2026-10-22T09:35"), {"20261022"}, H) == (True, "")
    assert g.intraday_gate(T("2026-10-22T13:31"), {"20261022"}, H)[0] is False        # 收盤後
    assert g.intraday_gate(T("2026-10-22T08:59"), {"20261022"}, H)[0] is False
    assert g.intraday_gate(T("2026-10-22T10:00"), {"20261021"}, H)[0] is False        # 報價是昨天的
    assert g.intraday_gate(T("2026-10-22T10:00"), set(), H)[0] is False               # 沒讀到報價也不發
    ok, why = g.intraday_gate(T("2026-10-26T10:00"), {"20261026"}, H)
    assert ok is False and "休市" in why
    assert g.intraday_gate(T("2026-10-26T10:00"), [], H, check_quotes=False)[0] is False


def test_data_dates_回完整日期且含融券():
    import json
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "data"
        p.mkdir()
        (p / "market_fut.json").write_text(json.dumps({"margin": {"rows": [{"d": "2026-10-23", "ratio": 1}],
                                                                  "rank": {"d": "2026-10-23"}, "short_rank": {"d": "2026-10-23"}}}), "utf-8")
        (p / "inst_today.json").write_text(json.dumps({"date": "2026-10-22"}), "utf-8")
        d = ss.data_dates(Path(td))
    assert d["credit-short"] == "2026-10-23" and d["credit-rank"] == "2026-10-23"
    assert d["streak-trust"] == "2026-10-22" and ss.mmdd(d["streak-trust"]) == "10/22"
