"""ETF 成分股（各投信每日 PCF／持股明細，2026-10-07）。

樣本全部是 .github/workflows/probe-etf-pcf.yml 在 Actions 上實測回應的節錄（紀錄在 docs/etf_holdings_source.md），
不打真 API —— 開發容器出口被擋，而且測試不該依賴投信網站今天有沒有開。
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.compute import etf_holdings as etf_hold  # noqa: E402
from pipeline.sources import etf_pcf  # noqa: E402

CAPITAL_PCF = {"code": 200, "data": {"pcf": {"fundName": "群益台灣精選強棒主動式ETF基金", "date1": "2026-10-07", "date2": "2026-10-06"},
                                     "stocks": [{"date1": "2026/10/7 上午 12:00:00", "stocNo": "2330", "stocName": "台積電", "weight": 7.5387,
                                                 "share": 1544000.0}, {"stocNo": "2454", "stocName": "聯發科", "weight": 6.8396, "share": 736000.0}]}}
NOMURA_ASSETS = {"TotalPages": -1, "Entries": {"FundID": "00935", "Data": {
    "FundAsset": {"Aum": "55422777333", "Nav": "63.38", "NavDate": "2026/10/06"},
    "Table": [{"TableTitle": "股票", "Columns": [{"Name": "股票代號"}, {"Name": "股票名稱"}, {"Name": "股數"}, {"Name": "權重(%)"}],
               "Rows": [["2330", "台灣積體電路製造", "5059000", "23.6"], ["2454", "聯發科技", "1897000", "16.84"]]}]}}}
FH_ASSETS = {"result": [{"fundID": "ETF23", "etf002": "00991A", "dDate": "2026/10/06", "detail": [
    {"ftype": "股票", "stockid": "2330", "stockname": "台灣積體", "qshare": "4,200,000", "prate_addaccint": "13.473%"},
    {"ftype": "其他資產", "stockid": "", "stockname": "現金", "qshare": "", "prate_addaccint": "0.8%"}]}]}
CATHAY_STOCKS = {"result": [{"stockCode": "2330", "stockName": "台積電", "volumn": "1,034,000", "weights": "8.63"},
                            {"stockCode": "6187", "stockName": "萬  潤", "volumn": "596,000", "weights": "2.95"}],
                 "returnCode": "2000", "success": True}
UNI_PCF = {"pcf": [{"FundCode": "49YTW", "TranDate": "2026-10-06T00:00:00"}],
           "asset": [{"AssetCode": "GD", "AssetName": "期貨(名目本金)", "Details": [{"DetailCode": "TX", "DetailName": "台指期貨", "Share": 679}]},
                     {"AssetCode": "ST", "AssetName": "股票", "Details": [
                         {"DetailCode": "2330", "DetailName": "台積電", "NavRate": 9.15, "Share": 1000, "TranDate": "/Date(1791216000000)/"}]}]}
YUANTA_INKIND = ('<script>window.__NUXT__=(function(a,b,c,d){return {};fx.PCF={fundid:a,trandate:b,osunit:1000000,baseunit:500000};'
                 'gB.PCF=[{ParentCode:"InKind.FundComposition"}];fx.InKind={FundComposition:[{stkcd:c,name:d,qty:100},'
                 '{stkcd:"2317",name:"\\u9d3b\\u6d77",qty:50}]}}("1066","20261006","2330","台積電"));</script>')
YUANTA_WEIGHTS = ('<script>window.__NUXT__=(function(a,b,c){return {};hk.PCF={fundid:a,trandate:b,baseunit:500000};'
                  'hk.InKind={FundComposition:a};hk.FundWeights={Summary:{code:a},StockWeights:[{code:"3045",ym:a,name:c,weights:9.57,qty:84107000}]}}'
                  '(void 0,"20261006","台灣大"));</script>')


def test_parsers_each_issuer():
    r = etf_pcf.parse_capital("00982A", CAPITAL_PCF)
    assert (r[0]["date"], r[0]["code"], r[0]["weight"], r[0]["shares"], r[0]["issuer"]) == ("2026-10-06", "2330", 7.5387, 1544000.0, "群益")
    r = etf_pcf.parse_nomura("00935", NOMURA_ASSETS)
    assert [x["code"] for x in r] == ["2330", "2454"] and r[0]["weight"] == 23.6 and r[0]["date"] == "2026-10-06"
    r = etf_pcf.parse_fuhhwa(FH_ASSETS)
    assert len(r) == 1 and r[0]["etf"] == "00991A" and r[0]["weight"] == 13.473 and r[0]["shares"] == 4200000.0
    r = etf_pcf.parse_cathay("00400A", "2026-10-06", CATHAY_STOCKS)
    assert r[1]["name"] == "萬潤" and r[1]["weight"] == 2.95 and r[1]["shares"] == 596000.0
    r = etf_pcf.parse_uni("00981A", UNI_PCF)
    assert len(r) == 1 and r[0]["code"] == "2330" and r[0]["date"] == "2026-10-06"   # 期貨那一類不算成分股
    r = etf_pcf.parse_kgi("009816", '<p>資料日期 2026/10/06</p><tr name="content" style=""><td>2330</td>'
                                    '<td>&#x53F0;&#x7A4D;&#x96FB;</td><td>830,000</td><td>8.98</td></tr>')
    assert r[0]["name"] == "台積電" and r[0]["weight"] == 8.98 and r[0]["date"] == "2026-10-06"


def test_kgi_fund_ids_map_by_short_name():
    pg = ('<input id="AllFundName" name="AllFundName" type="hidden" value="[{&quot;label&quot;:&quot;'
          '&#x51F1;&#x57FA;&#x53F0;&#x7063;TOP50&quot;,&quot;fundID&quot;:&quot;J023&quot;}]" />')
    assert etf_pcf.kgi_fund_ids(pg, {"009816": "凱基台灣TOP50"}) == {"009816": "J023"}


def test_yuanta_nuxt_two_layouts():
    """元大：實物申贖型只有每基數股數（權重留空、股數換算成整檔）；現金申贖型有 FundWeights（權重＋總股數）。"""
    r = etf_pcf.parse_yuanta("0050", YUANTA_INKIND)
    assert [x["code"] for x in r] == ["2330", "2317"] and r[1]["name"] == "鴻海"
    assert r[0]["weight"] is None and r[0]["shares"] == 200.0 and r[0]["date"] == "2026-10-06"
    r = etf_pcf.parse_yuanta("00713", YUANTA_WEIGHTS)
    assert len(r) == 1 and (r[0]["code"], r[0]["name"], r[0]["weight"], r[0]["shares"]) == ("3045", "台灣大", 9.57, 84107000.0)


def test_bad_payload_is_empty_and_logs_first_200_chars(caplog, monkeypatch):
    """上游改版：回空 DataFrame、不拋例外，log 要有實際回應的前 200 字。"""
    assert etf_pcf.parse_capital("X", {"code": 400, "data": None}) == []
    assert etf_pcf.parse_nomura("X", {"weird": 1}) == []
    assert etf_pcf.parse_uni("X", "not a dict") == []
    monkeypatch.setattr(etf_pcf, "_req", lambda *a, **k: {"unexpected": "x" * 500})
    with caplog.at_level(logging.WARNING):
        df = etf_pcf.capital()
    assert df.empty and list(df.columns) == etf_pcf.COLS
    assert any("前 200 字" in m and "unexpected" in m for m in caplog.messages)


def test_fetch_all_one_issuer_crash_does_not_kill_others(monkeypatch):
    monkeypatch.setattr(etf_pcf, "capital", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    ok = pd.DataFrame([{"date": "2026-10-06", "etf": "00935", "code": "2330", "name": "台積電", "weight": 23.6, "shares": 1.0,
                        "issuer": "野村", "src": "u"}])
    for fn in ("fuhhwa", "uni", "cathay", "yuanta", "ctbc", "fsitc", "ab", "hn"):
        monkeypatch.setattr(etf_pcf, fn, lambda *a, **k: pd.DataFrame(columns=etf_pcf.COLS))
    monkeypatch.setattr(etf_pcf, "kgi", lambda *a, **k: pd.DataFrame(columns=etf_pcf.COLS))
    monkeypatch.setattr(etf_pcf, "nomura", lambda codes: ok)
    out = etf_pcf.fetch_all({"00935": "野村臺灣新科技50"})
    assert list(out["etf"]) == ["00935"]


def test_skip_non_equity_and_dates():
    assert etf_pcf._skip_code("00679B") and etf_pcf._skip_code("00631L") and not etf_pcf._skip_code("00981A")
    assert etf_pcf._iso("115/10/06") == "2026-10-06" and etf_pcf._iso("20261006") == "2026-10-06"
    assert etf_pcf._iso("/Date(1791216000000)/") == "2026-10-06"
    assert etf_pcf.issuer_of("主動統一台股增長") == "統一" and etf_pcf.issuer_of("中信綠能及電動車") == "中國信託"


def test_build_latest_estimate_and_manual():
    hold = pd.DataFrame([
        {"date": "2026-10-05", "etf": "00919", "code": "2881", "name": "富邦金", "weight": 15.0, "shares": 1.0, "issuer": "群益", "src": "u"},
        {"date": "2026-10-06", "etf": "00919", "code": "2881", "name": "富邦金", "weight": 15.3, "shares": 1.0, "issuer": "群益", "src": "u"},
        {"date": "2026-10-06", "etf": "0050", "code": "2330", "name": "台積電", "weight": None, "shares": 300.0, "issuer": "元大", "src": "y"},
        {"date": "2026-10-06", "etf": "0050", "code": "2317", "name": "鴻海", "weight": None, "shares": 100.0, "issuer": "元大", "src": "y"},
    ])
    price = pd.DataFrame([{"date": "2026-10-06", "code": "2330", "close": 1000.0}, {"date": "2026-10-03", "code": "2317", "close": 1000.0}])
    manual = {"00896": {"asof": "2026-08-24", "src": "https://example/ctbc", "issuer": "中國信託",
                        "items": [{"code": "2330", "name": "台積電", "w": 11.79}, {"code": "2317", "name": "鴻海", "w": 7.61}]}}
    out = etf_hold.build(hold, price, {"00896": "中信綠能及電動車", "00878": "國泰永續高股息"}, {"00878", "00896"}, manual=manual)
    e = out["etfs"]
    assert e["00919"]["asof"] == "2026-10-06" and e["00919"]["items"][0]["w"] == 15.3      # 只取最新一天
    assert e["0050"]["est"] is True and e["0050"]["items"][0] == {"code": "2330", "name": "台積電", "w": 75.0, "shares": 300}
    assert e["00896"]["manual"] is True and e["00896"]["asof"] == "2026-08-24"
    assert "00878" not in e and out["issuers"]["00878"] == "國泰"                           # 沒接上：前端要寫投信名


CTBC_HOLD = {"ResultCode": 0, "Data": {"Fund": [{"ETF_ID": "00896", "FID": "E0019"}],
             "FundAssets": [{"FID": "E0019", "基金淨資產": "14,377,839,179", "資料日期": "2026/10/06", "NAV_DT": "2026-10-06T00:00:00"}],
             "FundAssetsDetail": [{"Code": "STOCK", "Name": "股票", "Sum": 98.46, "Data": [
                 {"invtp_": "STOCK", "code_": "2330", "name_": "台灣積體電路製造", "qty_": "638,000.00", "weights_": "11.46"},
                 {"invtp_": "STOCK", "code_": "1303", "name_": "南亞塑膠工業", "qty_": "3,780,000.00", "weights_": "7.70"}]},
                 {"Code": "CASH", "Name": "現金", "Data": [{"code_": "", "name_": "現金", "weights_": "1.54"}]}]}}


def test_ctbc_00896_holding_weight():
    """00896（Andy 點名的那檔）：中信官網 etf/ETFHoldingWeight 的實測回應節錄（2026-10-07）。"""
    r = etf_pcf.parse_ctbc("00896", CTBC_HOLD)
    assert [x["code"] for x in r] == ["2330", "1303"]
    assert (r[0]["date"], r[0]["weight"], r[0]["shares"], r[0]["issuer"]) == ("2026-10-06", 11.46, 638000.0, "中國信託")


# ── 2026-10-07 第二批：第一金、聯博、華南永昌（樣本＝probe-etf-pcf.yml 真瀏覽器記下的 XHR 回應節錄）
FSITC_HD = {"d": '[{"fundid":"D90","sdate":"2026-10-07","group":"1","A":"2330","B":"台積電","C":"25.43","D":"274,230","E":""},'
                 '{"fundid":"D90","sdate":"2026-10-07","group":"1","A":"2303","B":"聯電","C":"15.06","D":"2,827,000","E":""},'
                 '{"fundid":"D90","sdate":"2026-10-07","group":"4","A":"現金/存款","B":"TWD 15,545,039","C":"2.10","D":"","E":""}]'}
AB_EQ = {"domesticHoldings": [
    {"asOfDate": "10/07/2026", "holdingCategory": "holdings-section-equity", "holdings": [
        {"holding": "矽創電子", "holdingPerc": "1.167495", "holdingCode": "8016", "holdingShares": 170000.0}]},
    {"asOfDate": "10/07/2026", "holdingCategory": "holdings-section-futures", "holdings": [
        {"holding": "台指期", "holdingPerc": "3.0", "holdingCode": "TXF", "holdingShares": 10.0}]}]}
AB_BOND = {"domesticHoldings": [{"asOfDate": "10/06/2026", "holdingCategory": "holdings-section-bond", "holdings": [
    {"holding": "APA CORP 6.750000 % 15-FEB-2055", "holdingPerc": "0.36041414", "holdingCode": "US03743QAT58", "holdingShares": 224000.0}]}]}
HN_BUYBACK = {"Data": {"DataDate": "2026-10-08T00:00:00+08:00", "FundID": "E101", "ETFID": "009808",
                       "Pcf": {"FundSize": 1292682619.0, "Punit": 33.14},
                       "StockList": [{"StockNo": "2330", "StockName": "台積電", "Share": 201000.0, "Weight": 0.401942},
                                     {"StockNo": "2308", "StockName": "台達電子", "Share": 26000.0, "Weight": 0.040025}]},
              "Message": "", "ResultCode": "00"}


def test_fsitc_only_stock_group():
    r = etf_pcf.parse_fsitc("00728", FSITC_HD)
    assert [x["code"] for x in r] == ["2330", "2303"]
    assert (r[0]["date"], r[0]["weight"], r[1]["shares"], r[0]["issuer"]) == ("2026-10-07", 25.43, 2827000.0, "第一金")
    assert etf_pcf.parse_fsitc("X", {"d": "not json"}) == [] and etf_pcf.parse_fsitc("X", None) == []


def test_ab_equity_bond_and_isin():
    assert etf_pcf.tw_isin("00404A") == "TW00000404A5" and etf_pcf.tw_isin("00980D") == "TW00000980D8"
    assert etf_pcf.tw_isin("0050") == "TW0000050004"
    assert etf_pcf._tw_code_from_isin("TW0002330008") == "2330"
    r = etf_pcf.parse_ab("00404A", AB_EQ)                      # 期貨類別不算成分
    assert [(x["code"], x["date"], x["weight"]) for x in r] == [("8016", "2026-10-07", 1.167495)]
    b = etf_pcf.parse_ab("00980D", AB_BOND)                    # 債券型照收：代號是債券 ISIN，前端顯示名稱＋權重
    assert b[0]["code"] == "US03743QAT58" and b[0]["name"].startswith("APA CORP") and b[0]["date"] == "2026-10-06"
    assert etf_pcf.parse_ab("X", {"weird": 1}) == [] and etf_pcf.parse_ab("X", "str") == []


def test_hn_009808_weight_fraction_to_percent():
    """009808（Andy 點名的那檔）：華南永昌 ETF/BuyBack 的權重是小數，要 ×100 才是 %。"""
    r = etf_pcf.parse_hn("009808", HN_BUYBACK)
    assert [x["code"] for x in r] == ["2330", "2308"]
    assert (r[0]["date"], r[0]["weight"], r[0]["shares"], r[0]["issuer"]) == ("2026-10-08", 40.1942, 201000.0, "華南永昌")
    assert etf_pcf.parse_hn("X", {"Data": None}) == [] and etf_pcf.parse_hn("X", []) == []


def test_hn_login_failure_returns_empty(monkeypatch, caplog):
    class R:
        status_code = 503
        text = "<html>maintenance" + "x" * 400

        def json(self):
            raise ValueError

    class S:
        def post(self, *a, **k):
            return R()

    monkeypatch.setattr(etf_pcf.http, "session", lambda: S())
    with caplog.at_level(logging.WARNING):
        df = etf_pcf.hn(["009808"])
    assert df.empty and list(df.columns) == etf_pcf.COLS
    assert any("maintenance" in m for m in caplog.messages)
