"""債券型 ETF 成分（2026-10-08 第四輪）：已接上 8 家投信的債券表。

樣本全部是 Actions 實測回應的節錄（probe-etf-pcf.yml mode=bond，run 37679529998 與 37680170965），不打真 API。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.compute import etf_holdings as etf_hold  # noqa: E402
from pipeline.sources import etf_pcf  # noqa: E402

CAPITAL = {"code": 200, "data": {"pcf": {"fundName": "群益15年期以上電信業公司債ETF基金", "date1": "2026-10-08", "date2": "2026-10-06"},
                                 "stocks": [], "bonds": [
    {"date1": "2026/10/8 上午 12:00:00", "bondNo": "US00206RMN97", "bondName": "T 3.8 12/01/57", "weight": 4.1791, "weightRound": 4.18,
     "faceValue": 104345000.0, "faceValueFormat": "104,345,000", "marketValue": 63241855.34, "bondEname": "T 3.8 12/01/57"}]}}
NOMURA = {"TotalPages": -1, "Entries": {"FundID": "00987B", "Data": {
    "FundAsset": {"Aum": "1170833016", "Units": "77327000", "Nav": "15.1413", "NavDate": "2026/10/06"},
    "Table": [{"TableTitle": "債券", "Columns": [{"Name": "債券代碼"}, {"Name": "債券名稱"}, {"Name": "面值"}, {"Name": "市值"}, {"Name": "持債比例"}],
               "Rows": [["AU0000407256", "ACGB 4 1/4 10/21/36", "6750000", "6288801.64", "11.9", "AUD"]]}]}}}
FUHHWA = {"result": [{"fundID": "ETF05", "etf002": "00710B", "dDate": "2026/10/06", "detail": [
    {"ftype": "債券", "stockid": "USU4434TAH42", "stockname": "HBGCN 7 1/4 06/15/30", "qshare": "1,500,000", "qshareCur": "USD",
     "mvalue": "48,384,039", "price": "101.4628", "accint": "1,076,851", "prate_addaccint": "1.475%"},
    {"ftype": "其他資產", "stockid": "", "stockname": "現金", "qshare": "", "prate_addaccint": "0.8%"}]}]}
UNI = {"pcf": [{"FundCode": "37YTW", "TranDate": "/Date(1791216000000)/"}], "asset": [
    {"FundCode": "37YTW", "AssetCode": "GD", "AssetName": "期貨(名目本金)", "Details": None},
    {"FundCode": "37YTW", "AssetCode": "BD", "AssetName": "債券", "Details": [
        {"FundCode": "37YTW", "TranDate": "2026-10-06T00:00:00", "AssetCode": "BD", "MoneyType": "USD", "DetailCode": "US12189LAA98",
         "DetailName": "BNSF 5 3/4 05/01/40", "Share": 1780000.0, "Amount": 1726368.6, "NavRate": 1.19, "IssuserCname": "伯靈頓北方聖塔菲有限責任公司"}]}]}
KGI = ('<li><span>(2026/10/07)預估發行受益權單位數</span><span>4,130,309,000</span></li>'
       '<h4 class="redemption-rest__sub-title">債劵</h4><ul class="js-bond-list list-style-table Redemption01">'
       '<li><span class="x">債劵代碼</span><span class="x">債劵名稱</span><span class="x">面額</span><span class="x">市值</span><span class="x">持債比例</span></li>'
       '<li name="content" style=""><span class="p">EH9116177</span><span class="p">C 8 1/8 07/15/39</span><span class="p">32,000,000</span>'
       '<span class="p">37,134,080</span><span class="p">2.39</span></li></ul>'
       '<p class="textC-blue marginB-100r" id="Properties">持債特性 (2026/10/06)</p>')
CATHAY_BOND = {"result": [{"bondNo": "BBG01F3YX1P1", "bondName": "INTEL CORP 5.9-2063/02/10", "parValue": "94,070,000", "mkval": "81,312,094", "ntMkval": "2.11"}]}
CTBC = {"Data": {"FundAssets": [{"FID": "E0003", "資料日期": "2026/10/06", "NAV_DT": "2026-10-06T00:00:00"}], "FundAssetsDetail": [
    {"Code": "BOND", "Data": [{"invtp_": "BOND", "code_": "US03522AAJ97", "name_": "ABIBB 4.9 02/01/46 *", "cur_": "USD",
                               "qty_": "42,500,000.00", "weights_": "1.07", "amount_": "35,550,825.00", "price_": "83.65"}]},
    {"Code": "CASH", "Data": [{"invtp_": "CASH", "code_": "", "name_": "現金", "weights_": "1.06"}]}]}}
YUANTA = ('<script>window.__NUXT__=(function(a,b){return {};hk.PCF={fundid:a,markcd:"00679B",trandate:b,baseunit:500000};'
          'hk.FundWeights={Summary:{code:a,bndvalues:151488778209.74},StockWeights:[],FutureWeights:[],ETFWeights:[],'
          'BondWeights:[{code:"912810UK2",name:"US TREASURY N/B 4.75% 05/15/2055",ename:"US TREASURY N/B 4.75% 05/15/2055",'
          'weights:5.37,FACE_AMT:289300000,qty:256992538.97}]}}("1151","20261006"));</script>')


def test_債券型不再跳過_槓桿期貨照跳():
    assert not etf_pcf._skip_code("00679B") and not etf_pcf._skip_code("00981D")
    assert etf_pcf._skip_code("00631L") and etf_pcf._skip_code("00625K") and etf_pcf._skip_code("00642U")


def test_八家債券表():
    r = etf_pcf.parse_capital("00722B", CAPITAL)
    assert (r[0]["code"], r[0]["name"], r[0]["weight"], r[0]["shares"], r[0]["date"]) == ("US00206RMN97", "T 3.8 12/01/57", 4.1791, 104345000.0, "2026-10-06")
    r = etf_pcf.parse_nomura("00987B", NOMURA)
    assert (r[0]["code"], r[0]["weight"], r[0]["shares"], r[0]["date"]) == ("AU0000407256", 11.9, 6750000.0, "2026-10-06")
    r = etf_pcf.parse_fuhhwa(FUHHWA)
    assert len(r) == 1 and r[0]["etf"] == "00710B" and r[0]["weight"] == 1.475 and r[0]["shares"] == 1500000.0   # 現金不算
    r = etf_pcf.parse_uni("00853B", UNI)
    assert len(r) == 1 and r[0]["code"] == "US12189LAA98" and r[0]["weight"] == 1.19 and r[0]["date"] == "2026-10-06"
    r = etf_pcf.parse_kgi("00950B", KGI)
    assert len(r) == 1 and (r[0]["code"], r[0]["weight"], r[0]["shares"], r[0]["date"]) == ("EH9116177", 2.39, 32000000.0, "2026-10-06")
    r = etf_pcf.parse_cathay_bond("00725B", "2026-10-06", CATHAY_BOND)
    assert r[0]["name"] == "INTEL CORP 5.9-2063/02/10" and r[0]["weight"] == 2.11 and r[0]["shares"] == 94070000.0
    r = etf_pcf.parse_ctbc("00772B", CTBC)
    assert len(r) == 1 and r[0]["code"] == "US03522AAJ97" and r[0]["weight"] == 1.07   # CASH 不算
    r = etf_pcf.parse_yuanta("00679B", YUANTA)
    assert len(r) == 1 and r[0]["weight"] == 5.37 and r[0]["shares"] == 289300000.0 and r[0]["date"] == "2026-10-06"


def test_票面利率與到期日從名稱讀():
    b = etf_pcf.bond_terms
    assert b("T 3.8 12/01/57") == (3.8, "2057-12-01")
    assert b("ACGB 4 1/4 10/21/36") == (4.25, "2036-10-21")
    assert b("US TREASURY N/B 4.75% 05/15/2055") == (4.75, "2055-05-15")
    assert b("INTEL CORP 5.9-2063/02/10") == (5.9, "2063-02-10")
    assert b("EIX V8.125 06/15/53") == (8.125, "2053-06-15")
    assert b("ABIBB 4.9 02/01/46 *") == (4.9, "2046-02-01")
    assert b("台積電") == (None, None) and b("") == (None, None)


def test_payload債券帶票息到期_股票不帶():
    hold = pd.DataFrame([
        {"date": "2026-10-06", "etf": "00679B", "code": "912810UK2", "name": "US TREASURY N/B 4.75% 05/15/2055", "weight": 5.37, "shares": 1.0, "issuer": "元大", "src": ""},
        {"date": "2026-10-06", "etf": "0050", "code": "2330", "name": "台積電", "weight": 50.0, "shares": 1.0, "issuer": "元大", "src": ""}])
    out = etf_hold.build(hold, pd.DataFrame(), {}, manual={})
    b = out["etfs"]["00679B"]["items"][0]
    assert b["cpn"] == 4.75 and b["mat"] == "2055-05-15"
    assert "mat" not in out["etfs"]["0050"]["items"][0]
