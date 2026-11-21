"""風險警示牌（P-1107-02）：注意股／處置股的解析與整理。

樣本取自 docs/fixtures/risk_flag_probe.json（2026-11-09 Actions 實測）。
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from pipeline import config
from pipeline.compute import risk as risk_c
from pipeline.sources import risk

FIX = Path(__file__).resolve().parents[1] / "docs" / "fixtures" / "risk_flag_probe.json"


def _fx(pid: str) -> list:
    d = json.loads(FIX.read_text(encoding="utf-8"))
    return next(r for r in d["results"] if r["id"] == pid)["sample"]


def test_端點與資料表都有登記():
    assert config.TWSE_ENDPOINTS["risk_notice"] == "/announcement/notice"
    assert config.TWSE_ENDPOINTS["risk_punish"] == "/announcement/punish"
    assert config.TPEX_ENDPOINTS["risk_notice"] == "/tpex_trading_warning_information"
    assert config.TPEX_ENDPOINTS["risk_punish"] == "/tpex_disposal_information"
    assert config.TABLES["risk_notice"] == ["date", "code", "market"]
    assert config.TABLES["risk_punish"] == ["date", "code", "market"]


def test_上市注意盤中空殼要丟掉():
    # 實測：盤中打 /announcement/notice 回一筆 Code=""、Date="" 的空殼
    df = risk.parse_notice(_fx("twse_notice"), "TWSE")
    assert df.empty and list(df.columns) == risk.NOTICE_COLS


def test_空回應與非清單():
    assert risk.parse_notice([], "TWSE").empty
    assert risk.parse_notice(None, "TPEX").empty
    assert risk.parse_punish([], "TWSE").empty
    assert risk.parse_punish([{"foo": 1}, "x"], "TWSE").empty


def test_上櫃注意解析_日期取回應內的值():
    df = risk.parse_notice(_fx("tpex_warning"), "TPEX")
    assert len(df) == 3
    r = df[df["code"] == "2221"].iloc[0]
    assert r["date"] == "2026-11-06"          # 回應的 Date＝1151106，不是執行當天
    assert r["name"] == "大甲" and r["market"] == "TPEX"
    assert "週轉率" in r["reason"]
    assert r["close"] == 143.5 and r["pe"] == 47.36
    assert pd.isna(df[df["code"] == "1569"].iloc[0]["pe"])     # N/A → 空


def test_上市注意有名單時的欄位():
    rows = [{"Number": "1", "Code": "3017", "Name": "奇鋐", "NumberOfAnnouncement": "2",
             "TradingInfoForAttention": "最近六個營業日累積收盤價漲幅達32.15%", "Date": "1151109",
             "ClosingPrice": "1,105.00", "PE": "45.10"}]
    df = risk.parse_notice(rows, "TWSE")
    r = df.iloc[0]
    assert (r["date"], r["code"], r["close"], r["ann_n"]) == ("2026-11-09", "3017", 1105.0, 2.0)


def test_上市處置解析_期間與撮合原文():
    df = risk.parse_punish(_fx("twse_punish"), "TWSE")
    r = df[df["code"] == "2360"].iloc[0]
    assert r["date"] == "2026-11-06"
    assert (r["start"], r["end"]) == ("2026-11-09", "2026-11-13")
    assert r["measure"] == "第一次處置" and r["reason"] == "連續三次"
    assert r["match"] == "約每二分鐘撮合一次"
    assert bool(r["prepay"]) is True
    assert df["code"].tolist()[:2] == ["064019", "088008"]   # 權證代號原樣保留（6 碼、零開頭）


def test_上櫃處置解析_期間寫法不同():
    df = risk.parse_punish(_fx("tpex_disposal"), "TPEX")
    r = df[df["code"] == "8291"].iloc[0]
    assert (r["date"], r["start"], r["end"]) == ("2026-11-02", "2026-11-03", "2026-11-09")
    assert r["match"] == "約每10分鐘撮合一次"
    assert r["reason"] == "連續3個營業日"
    assert bool(r["prepay"]) is True


def test_期間解析():
    assert risk.parse_period("115/11/09～115/11/13") == ("2026-11-09", "2026-11-13")
    assert risk.parse_period("1151105~1151111") == ("2026-11-05", "2026-11-11")
    assert risk.parse_period("") == (None, None)
    assert risk.parse_period("亂寫") == (None, None)


def test_抓取失敗回空並記原因(monkeypatch):
    monkeypatch.setattr(risk.http, "get", lambda *a, **k: None)
    df = risk.notice()
    assert df.empty and "回應空白" in df.attrs.get("error", "")


def test_端點有回但沒名單算略過(monkeypatch):
    monkeypatch.setattr(risk.http, "get", lambda *a, **k: _fx("twse_notice"))
    df = risk.notice()
    assert df.empty and df.attrs.get("skipped") and not df.attrs.get("error")


def _notice_lake():
    return pd.DataFrame([
        {"date": "2026-11-03", "code": "2221", "market": "TPEX", "name": "大甲", "reason": "舊原因"},
        {"date": "2026-11-05", "code": "2221", "market": "TPEX", "name": "大甲", "reason": "週轉率"},
        {"date": "2026-11-06", "code": "2221", "market": "TPEX", "name": "大甲", "reason": "最新原因"},
        {"date": "2026-10-01", "code": "1101", "market": "TWSE", "name": "台泥", "reason": "很久以前"},
    ])


def _punish_lake():
    return pd.DataFrame([
        {"date": "2026-11-06", "code": "2360", "market": "TWSE", "name": "致茂", "start": "2026-11-09", "end": "2026-11-13",
         "reason": "連續三次", "measure": "第一次處置", "match": "約每二分鐘撮合一次", "prepay": True},
        {"date": "2026-10-20", "code": "2330", "market": "TWSE", "name": "台積電", "start": "2026-10-21", "end": "2026-10-27",
         "reason": "連續三次", "measure": "第一次處置", "match": "約每五分鐘撮合一次", "prepay": False},
    ])


def test_整理成前端格式_近十日次數與族群():
    td = ["2026-10-26", "2026-10-27", "2026-10-28", "2026-10-29", "2026-10-30", "2026-11-02",
          "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06"]
    mem = pd.DataFrame([{"code": "2221", "group_id": "food"}, {"code": "2360", "group_id": "test_eq"},
                        {"code": "2330", "group_id": "foundry"}, {"code": "2454", "group_id": "test_eq"}])
    out = risk_c.build_json(_notice_lake(), _punish_lake(), td, mem)
    assert out["date"] == "2026-11-06" and out["notice_date"] == "2026-11-06"
    assert out["window"] == td and out["since"] == "2026-10-01"
    n = out["stocks"]["2221"]["notice"]
    assert n["n10"] == 3 and n["last"] == "2026-11-06" and n["reason"] == "最新原因"
    assert "1101" not in out["stocks"]           # 10 個交易日之外的注意不列
    p = out["stocks"]["2360"]["punish"]
    assert p[0]["start"] == "2026-11-09" and p[0]["match"] == "約每二分鐘撮合一次" and p[0]["prepay"] is True
    assert "2330" not in out["stocks"]           # 處置已結束（訖日早於參考日）
    assert out["groups"] == {"food": ["2221"], "test_eq": ["2360"]}


def test_整理_空資料湖():
    out = risk_c.build_json(pd.DataFrame(), pd.DataFrame(), [], pd.DataFrame())
    assert out["stocks"] == {} and out["groups"] == {} and out["date"] is None and out["window"] == []
