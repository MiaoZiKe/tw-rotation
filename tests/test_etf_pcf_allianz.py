"""安聯 ETF 成分（2026-10-08 第四輪）：GetFundAssets 要帶 X-XSRF-TOKEN；樣本是 Actions 實測節錄（run 37685736089 E0002）。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.sources import etf_pcf  # noqa: E402

ALLIANZ = {"TotalPages": -1, "TotalItems": 0, "Entries": {"FundID": "E0002", "Data": {
    "FundAsset": {"Aum": "10474380388", "Units": "715591000", "Nav": "14.64", "NavDate": "2026/10/07", "PCFDate": "2026/10/08"},
    "Table": [{"TableTitle": "", "Columns": [{"Name": None}], "Rows": [[" ", " ", " ", " "]]},
              {"TableTitle": "股票 (96.12%)", "Columns": [{"Name": "序號"}, {"Name": "股票代號"}, {"Name": "股票名稱"}, {"Name": "股數"}, {"Name": "權重(%)"}],
               "Rows": [["1", "2330", "台積電", "341,000", "8.43%"]]},
              {"TableTitle": "期貨", "Columns": [{"Name": "序號"}], "Rows": [["1", "TX", "台指期貨", "19", "1.71%", "2026/10"]]}]}}}


def test_安聯_帶XSRF標頭_對照表(monkeypatch):
    seen = []

    class Cookies(dict):
        def get(self, k, default=None, domain=None):
            return dict.get(self, k, default)

    class R:
        def __init__(self, p):
            self.status_code, self._p, self.text = 200, p, "{}"

        def json(self):
            return self._p

    class S:
        cookies = Cookies({"X-XSRF-TOKEN": "tok123"})

        def get(self, url, **k):
            return R({})

        def post(self, url, json=None, headers=None, timeout=None):
            seen.append((json["FundID"], headers.get("X-XSRF-TOKEN")))
            return R(ALLIANZ if json["FundID"] == "E0002" else {"Entries": None})
    monkeypatch.setattr(etf_pcf.http, "session", lambda: S())
    monkeypatch.setattr(etf_pcf.time, "sleep", lambda *_: None)
    df = etf_pcf.allianz()
    assert list(df["etf"]) == ["00993A"] and df["code"].iloc[0] == "2330" and df["weight"].iloc[0] == 8.43   # 期貨不算
    assert df["issuer"].iloc[0] == "安聯" and df["date"].iloc[0] == "2026-10-07"
    assert seen and all(t == "tok123" for _, t in seen)


def test_安聯_拿不到token回空(monkeypatch):
    class S:
        cookies = {}

        def get(self, url, **k):
            raise ConnectionError("連不上")
    monkeypatch.setattr(etf_pcf.http, "session", lambda: S())
    df = etf_pcf.allianz()
    assert df.empty and list(df.columns) == etf_pcf.COLS
