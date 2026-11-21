"""大華銀投信 ETF 成分股（2026-10-08）：補中繼憑證後接上。

樣本是 Actions 實測回應（.github/workflows/probe-etf-pcf.yml mode=cert，run 37672230153）的節錄，不打真 API。
"""
from __future__ import annotations

import logging
import ssl
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.sources import etf_pcf  # noqa: E402

# 前兩筆原樣；第三筆期貨是自己加的，驗證會被濾掉
UOB_PCF = {"fundID": "88329556", "etf002": "00918", "twName": "大華優利高填息30(本基金並無保證收益及配息且配息來源可能為收益平準金)",
           "announce": "/Date(1791388800000+0800)/", "publish": "/Date(1791302400000+0800)/", "datadate": "/Date(1791302400000+0800)/",
           "nav": "NT$ 34.10", "result": [
               {"id": 1239417, "kind": "stock", "code": "2887", "fundID": "88329556", "cName": "台新新光金", "qty": "301,361,380",
                "dataDate": "/Date(1791302400000+0800)/", "bbg_code": "2887 TT Equity", "price": 42.15, "weight": 7.82},
               {"id": 1239403, "kind": "stock", "code": "2357", "fundID": "88329556", "cName": "華碩", "qty": "12,522,000",
                "dataDate": "/Date(1791302400000+0800)/", "bbg_code": "2357 TT Equity", "price": 989.0, "weight": 7.63},
               {"id": 1, "kind": "futures", "code": "TXF", "fundID": "88329556", "cName": "台指期", "qty": "10", "weight": 1.0}]}


def test_uob_parse_實測回應():
    r = etf_pcf.parse_uob(UOB_PCF)
    assert [x["code"] for x in r] == ["2887", "2357"]                  # 期貨不算成分
    assert r[0]["etf"] == "00918" and r[0]["date"] == "2026-10-07"     # 代號、日期都取自回應，不用執行當下
    assert r[0]["weight"] == 7.82 and r[0]["shares"] == 301361380.0 and r[0]["issuer"] == "大華銀"
    assert etf_pcf.parse_uob({"etf002": "", "result": UOB_PCF["result"]}) == []
    assert etf_pcf.parse_uob("<html>") == []


def test_uob_fund_ids_只收ETF():
    lst = {"resultP": [{"id": 1, "result": [{"fundID": "88329556", "ec001": 3}, {"fundID": "X1", "ec001": 1}]},
                       {"id": 2, "result": [{"fundID": "Y2", "ec001": "3"}, {"fundID": "88329556", "ec001": 3}]}]}
    assert etf_pcf.uob_fund_ids(lst) == ["88329556", "Y2"]


def test_uob_中繼憑證在repo而且驗證沒關(monkeypatch):
    pem = Path(etf_pcf.__file__).parent / "certs" / "uobam_intermediate.pem"
    ssl.create_default_context().load_verify_locations(cafile=str(pem))   # 是合法的 PEM
    bundle = etf_pcf._uob_bundle()
    txt = open(bundle, encoding="utf-8").read()
    assert "GlobalSign Root R46" in txt and txt.count("BEGIN CERTIFICATE") > 100   # certifi 根憑證＋中繼
    seen: dict = {}

    class R:
        status_code = 200
        text = "{}"

        def json(self):
            return UOB_PCF if "Pcf" in seen["url"] else {"resultP": [{"result": [{"fundID": "88329556", "ec001": 3}]}]}

    class S:
        def get(self, url, params=None, timeout=None, verify=None):
            seen["url"] = url
            seen.setdefault("verify", set()).add(verify)
            return R()
    monkeypatch.setattr(etf_pcf.http, "session", lambda: S())
    monkeypatch.setattr(etf_pcf.time, "sleep", lambda *_: None)
    df = etf_pcf.uob()
    assert len(df) == 2 and set(df["etf"]) == {"00918"}
    assert seen["verify"] == {bundle}                       # 每次都帶憑證清單，從來不是 False


def test_uob_失敗回空並記前200字(monkeypatch, caplog):
    class R:
        status_code = 500
        text = "伺服器錯誤" * 100

    class S:
        def get(self, *a, **k):
            return R()
    monkeypatch.setattr(etf_pcf.http, "session", lambda: S())
    monkeypatch.setattr(etf_pcf.time, "sleep", lambda *_: None)
    with caplog.at_level(logging.WARNING):
        df = etf_pcf.uob()
    assert df.empty and list(df.columns) == etf_pcf.COLS
    assert "HTTP 500" in caplog.text and "伺服器錯誤" in caplog.text


def test_大華銀已接上_不再顯示抓不到():
    assert "大華銀" in etf_pcf.CONNECTED and "大華銀" not in etf_pcf.NOT_CONNECTED_WHY
