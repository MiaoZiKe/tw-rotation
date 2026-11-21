"""永豐、玉山 ETF 成分（2026-10-08 第四輪）。

樣本是 Actions 實測回應節錄（probe-etf-pcf.yml mode=bond --round3，run 37683032004），不打真 API。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.sources import etf_pcf  # noqa: E402

SINOPAC_STOCK = (
    '<select class="sel_typ" id="fundlist" name="fundId"><option value="00410A">主動永豐科技趨勢</option> '
    '<option selected="selected" value="00888">永豐台灣ESG</option> <option value="00836B">永豐10年A公司債</option> </select>'
    '<div class="fl_cell"><h4 style="text-align:left;">2026/10/07&nbsp;基金淨資產價值(元)</h4></div>'
    '<div class="cash_box"> <div class="cash_title-s">股票</div> <!--股票 PC版--> <table class="tab_sh tab_sh-w tab_fu-07"><tbody>'
    '<tr> <th style="width: auto">證券代碼</th> <th>證券名稱</th> <th>股數</th> <th>佔基金淨資產之權重(%)</th> </tr>'
    '<tr> <td>2330</td> <td>台積電</td> <td>2,625,736</td> <td>29.29</td> </tr>'
    '<tr> <td>2303</td> <td>聯電</td> <td>27,842,294</td> <td>17.83</td> </tr></tbody></table>'
    '<table class="tab_sh tab_sh-m"><tbody><tr><th>證券代碼</th><td>2330</td></tr></tbody></table></div>'
    '<div class="cash_title-s">期貨</div> <table><tbody><tr><th>期貨代碼</th></tr><tr> <td>TX</td> <td>台指期貨</td> <td>202610</td> <td>26</td> <td>1.12</td> </tr></tbody></table>')
SINOPAC_BOND = (
    '<option selected="selected" value="00836B">永豐10年A公司債</option>'
    '<h4 style="text-align:left;">2026/10/06&nbsp;基金淨資產價值(元)</h4>'
    '<div class="cash_title-s">債券</div> <!--債券 PC--> <table class="tab_sh tab_sh-w tab_fu-06"><tbody>'
    '<tr> <th>債券代碼</th> <th>債券名稱</th> <th>面額</th> <th>佔基金淨資產之權重(%)</th> </tr>'
    '<tr align="center"> <td>US747525BT99</td> <td>QCOM 6 05/20/53</td> <td>16,900,000</td> <td>2.87</td> </tr></tbody></table>'
    '<div class="cash_title-s">持債特性</div> <table><tbody><tr><th>項目</th></tr><tr align="center"> <td>成分債檔數</td> <td>135.00</td> <td>173.00</td> <td>-38.00</td> </tr></tbody></table>')
ESUN = {"TotalPages": -1, "TotalItems": 0, "Entries": {"CId": 850, "CFundId": "50", "CFundShortName": "玉山市值動能50",
        "CPcfdate": "2026-10-08T00:00:00", "CNavDt": "2026-10-07T00:00:00", "DynamicTableData": [
            {"TableTitle": "股票", "Columns": [{"Name": "股票代號"}, {"Name": "股票名稱"}, {"Name": "股數"}, {"Name": "權重(%)"}],
             "Rows": [["2330", "台積電", "1,037,000", "41.68"], ["2454", "聯發科", "90,000", "6.77"]]},
            {"TableTitle": "期貨", "Columns": [{"Name": "期貨代號"}, {"Name": "期貨名稱"}, {"Name": "口數"}, {"Name": "權重(%)"}, {"Name": "契約年月"}],
             "Rows": [["TX", "臺股期貨", "6", "0.93", "2026/10"]]}]}, "Message": "", "StatusCode": 0}
ESUN_BOND = {"Entries": {"CFundShortName": "玉山嚴選非投債", "CNavDt": "2026-10-06T00:00:00", "DynamicTableData": [
    {"TableTitle": "債券", "Columns": [{"Name": "債券代號"}, {"Name": "債券名稱"}, {"Name": "面額"}, {"Name": "權重(%)"}],
     "Rows": [["US451102CF29", "IEP 9 3/4 01/15/29", "2,494,000", "2.43"]]},
    {"TableTitle": "持債特性", "Columns": [{"Name": ""}], "Rows": [["成分債券檔數", "124", "221", "-97"]]}]}}


def test_永豐_清單與股票債券():
    assert etf_pcf.sinopac_codes(SINOPAC_STOCK) == ["00410A", "00888", "00836B"]
    r = etf_pcf.parse_sinopac("00888", SINOPAC_STOCK)
    assert [x["code"] for x in r] == ["2330", "2303"]                     # 期貨不算、行動版表不重複讀
    assert r[0]["date"] == "2026-10-07" and r[0]["weight"] == 29.29 and r[0]["shares"] == 2625736.0
    r = etf_pcf.parse_sinopac("00836B", SINOPAC_BOND)
    assert len(r) == 1 and r[0]["code"] == "US747525BT99" and r[0]["date"] == "2026-10-06" and r[0]["shares"] == 16900000.0
    assert etf_pcf.parse_sinopac("00410A", SINOPAC_STOCK) == []           # 官網回的是別檔的頁面就不收


def test_玉山_簡稱對代號與解析():
    names = {"009803": "玉山市值動能50", "009827": "玉山未來全球算力", "00988B": "玉山嚴選非投債", "0050": "元大台灣50"}
    mine = {c: n for c, n in names.items() if etf_pcf.issuer_of(n) == "玉山"}
    assert etf_pcf._name_match("玉山市值動能50", mine) == "009803"
    assert etf_pcf._name_match("玉山全球算力", mine) == "009827"            # 官網簡稱比證交所短
    assert etf_pcf._name_match("玉山", mine) is None                      # 對到多檔就不猜
    r = etf_pcf.parse_esun("009803", ESUN)
    assert [x["code"] for x in r] == ["2330", "2454"] and r[0]["date"] == "2026-10-07" and r[0]["weight"] == 41.68
    r = etf_pcf.parse_esun("00988B", ESUN_BOND)
    assert len(r) == 1 and r[0]["code"] == "US451102CF29" and r[0]["shares"] == 2494000.0   # 持債特性不是成分
    assert etf_pcf.parse_esun("x", {"Entries": []}) == [] and etf_pcf.parse_esun("x", None) == []
