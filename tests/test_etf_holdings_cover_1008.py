"""ETF 成分股全覆蓋（2026-10-08 第五輪）：聯邦接上、資料湖取「每檔最近一次」、人工整理檔、公會月資料。

全部用假回應（節錄自 Actions 實測的真回應，probe-etf-pcf.yml run 37779130534），不打真 API。
"""
from __future__ import annotations

import pandas as pd

from pipeline.compute import etf_holdings
from pipeline.sources import etf_pcf

USITC_PAGE = """
<form action="/CustCenter/BuyBackList" id="form1" method="post" name="form1">
 <select name="FundNo" id="FundNo" class="form-control">
 <option value=009804>聯邦台灣精彩50ETF基金</option>
 <option value=009825>聯邦美國金融創新ETF基金</option>
 </select>
 <div class="infoTitle"><h2>聯邦台灣精彩50ETF基金 ( 009804 )</h2></div>
 <span style="float:right;color:gray"><b>資料日期： 2026-10-08</b></span>
 <table><tbody>
 <tr data-toggle="collapse" class="accordion-toggle">
 <td data-title="期貨代碼">TX</td><td data-title="期貨名稱">台指期貨</td><td data-title="口數">2</td>
 <td data-title="權重">0.5716</td><td data-title="契約年月">202610</td></tr>
 </tbody></table>
 <table><tbody><div class="card stepTitle">
 <tr data-toggle="collapse" class="accordion-toggle">
 <td data-title="股票代號">2330</td><td data-title="股票名稱">台積電</td><td data-title="股數">399,525</td><td data-title="權重">29.5002</td></tr>
 <tr data-toggle="collapse" class="accordion-toggle">
 <td data-title="股票代號">2454</td><td data-title="股票名稱">聯發科</td><td data-title="股數">73,826</td><td data-title="權重">10.0259</td></tr>
 <tr data-toggle="collapse" class="hiderow" style="display: none">
 <td data-title="股票代號">2327</td><td data-title="股票名稱">國巨*</td><td data-title="股數">79,783</td><td data-title="權重">1.4670</td></tr>
 </tbody></table>
"""


def test_聯邦_清單與股票表_期貨不收():
    assert etf_pcf.usitc_codes(USITC_PAGE) == ["009804", "009825"]
    rows = etf_pcf.parse_usitc("009804", USITC_PAGE)
    assert [r["code"] for r in rows] == ["2330", "2454", "2327"]            # 期貨 TX 不收；收起來的列（hiderow）照收
    assert rows[0]["date"] == "2026-10-08" and rows[0]["weight"] == 29.5002 and rows[0]["shares"] == 399525
    assert rows[2]["name"] == "國巨"                                          # 名稱尾端的 * 拿掉
    assert {r["issuer"] for r in rows} == {"聯邦"}


def test_聯邦_回錯檔就不收():
    # 官網對不認得的 FundNo 會回預設那一檔（009804）的頁面 —— 頁首代號對不上就略過，不能把 009804 的成分當成 009825 的
    assert etf_pcf.parse_usitc("009825", USITC_PAGE) == []


def test_聯邦_失敗回空並記前200字(monkeypatch, caplog):
    monkeypatch.setattr(etf_pcf, "_req", lambda *a, **k: "<html>維護中</html>")
    df = etf_pcf.usitc()
    assert df.empty and list(df.columns) == etf_pcf.COLS
    assert "維護中" in caplog.text


def test_聯邦已接上_不再寫逾時原因():
    assert "聯邦" in etf_pcf.CONNECTED and "聯邦" not in etf_pcf.NOT_CONNECTED_WHY


def _hold(rows):
    return pd.DataFrame(rows, columns=etf_pcf.COLS)


def test_每檔取資料湖裡自己最近一次_某天官網沒回也不會變空():
    """00918 退步的防線：今天（10-08）只有 0050 抓到，00918 最近一次是 10-06 —— 00918 照樣要有表、標 10-06。"""
    hold = _hold([
        {"date": "2026-10-06", "etf": "00918", "code": "2887", "name": "台新新光金", "weight": 7.82, "shares": 1, "issuer": "大華銀", "src": "u"},
        {"date": "2026-10-06", "etf": "00918", "code": "2891", "name": "中信金", "weight": 6.1, "shares": 1, "issuer": "大華銀", "src": "u"},
        {"date": "2026-10-07", "etf": "0050", "code": "2330", "name": "台積電", "weight": 50.0, "shares": 1, "issuer": "元大", "src": "y"},
        {"date": "2026-10-08", "etf": "0050", "code": "2330", "name": "台積電", "weight": 51.0, "shares": 1, "issuer": "元大", "src": "y"},
    ])
    out = etf_holdings.build(hold, pd.DataFrame(), {"00918": "大華優利高填息30", "0050": "元大台灣50"}, manual={})
    assert out["etfs"]["00918"]["asof"] == "2026-10-06" and len(out["etfs"]["00918"]["items"]) == 2
    assert out["etfs"]["0050"]["asof"] == "2026-10-08" and out["etfs"]["0050"]["items"][0]["w"] == 51.0


def test_人工整理檔_帶來源名稱與網址_自動來源較新時讓位():
    manual = {
        "00690": {"asof": "2026-10-07", "issuer": "兆豐", "src": "https://www.wantgoo.com/stock/etf/00690/constituent",
                  "src_name": "玩股網（人工整理）", "items": [{"code": "2330", "name": "台積電", "w": 5.1}, {"code": "2317", "name": "鴻海", "w": None}]},
        "0050": {"asof": "2026-10-01", "items": [{"code": "2330", "name": "台積電", "w": 1.0}]},
    }
    hold = _hold([{"date": "2026-10-07", "etf": "0050", "code": "2330", "name": "台積電", "weight": 50.0, "shares": 1, "issuer": "元大", "src": "y"}])
    out = etf_holdings.build(hold, pd.DataFrame(), {"00690": "兆豐藍籌30"}, manual=manual)
    m = out["etfs"]["00690"]
    assert m["manual"] is True and m["src_name"] == "玩股網（人工整理）" and m["src"].startswith("https://www.wantgoo.com/")
    assert [x["code"] for x in m["items"]] == ["2330"]                       # 沒有權重的列不收（不估）
    assert "manual" not in out["etfs"]["0050"]                                # 自動來源比較新 → 用自動的


# ───────────────────────────── 投信投顧公會每月前十大（pipeline/sources/sitca.py）
from pipeline.sources import sitca  # noqa: E402

SITCA_FORM = """<form name="aspnetForm" method="post" action="./IN2629.aspx" id="aspnetForm">
<input type="hidden" name="__VIEWSTATE" id="__VIEWSTATE" value="abc" />
<input type="hidden" name="__EVENTVALIDATION" id="__EVENTVALIDATION" value="def" />
<select name="ctl00$ContentPlaceHolder1$ddlQ_YM" id="ctl00_ContentPlaceHolder1_ddlQ_YM">
<option value="202607">2026 年 07 月</option>
<option selected="selected" value="202608">2026 年 08 月</option>
</select>"""

# 節錄自 2026-10-08 Actions 實抓（rdo1=rbClass、ddlQ_Class=AH11、202608）：第一名那列帶基金名稱（10 格），其後 9 格，最後「合計」
SITCA_TABLE = """<table>
<tr><td>基金名稱</td><td>名次</td><td>標的種類</td><td>標的代號</td><td>標的名稱</td><td>金額</td><td>擔保機構**</td><td>次順位債券**</td><td>受益權單位數***</td><td>占基金淨資產價值之比例(%)</td></tr>
<tr><td rowspan="10">兆豐臺灣藍籌30ETF基金</td><td>1</td><td>國內上市</td><td>2330</td><td>台積電</td><td>1,669,769,855</td><td></td><td></td><td>0</td><td>25.56</td></tr>
<tr><td>2</td><td>國內上市</td><td>2454</td><td>聯發科</td><td>951,659,425</td><td></td><td></td><td>0</td><td>14.57</td></tr>
<tr><td>8</td><td>國內上市</td><td>2327</td><td>國巨*</td><td>205,633,405</td><td></td><td></td><td>0</td><td>3.15</td></tr>
<tr><td colspan="9">合計</td><td>74.69</td></tr>
<tr><td rowspan="10">兆豐美國企業優選投資級公司債ETF基金<br>(基金之配息來源可能為收益平準金)</td><td>1</td><td>公司債 無擔保</td><td>US30303MAE21</td><td>META 5 58 111555</td><td>39,619,235</td><td></td><td></td><td>0</td><td>1.62</td></tr>
<tr><td>2</td><td>公司債 無擔保</td><td>US747525BT99</td><td>QCOM 6 052053</td><td>37,048,561</td><td></td><td></td><td>0</td><td>1.52</td></tr>
</table>"""

NAMES = {"00690": "兆豐藍籌30", "00957B": "兆豐US優選投等債", "00921": "兆豐龍頭等權重", "00905": "FT臺灣Smart",
         "00961": "FT臺灣永續高息", "00878": "國泰永續高股息", "00701": "國泰股利精選30", "0050": "元大台灣50"}


def test_公會_年月與表格解析():
    assert sitca.latest_ym(SITCA_FORM) == "202608"
    assert sitca.month_end("202608") == "2026-08-31" and sitca.month_end("202602") == "2026-02-28"
    rows = sitca.parse_top10(SITCA_TABLE, "202608")
    assert [(r["fund"], r["rank"], r["code"]) for r in rows] == [
        ("兆豐臺灣藍籌30ETF基金", 1, "2330"), ("兆豐臺灣藍籌30ETF基金", 2, "2454"), ("兆豐臺灣藍籌30ETF基金", 8, "2327"),
        ("兆豐美國企業優選投資級公司債ETF基金", 1, "US30303MAE21"), ("兆豐美國企業優選投資級公司債ETF基金", 2, "US747525BT99")]
    assert rows[0]["weight"] == 25.56 and rows[0]["date"] == "2026-08-31" and rows[2]["name"] == "國巨"


def test_公會_基金全名對回代號_不猜():
    m = sitca.match_all(["兆豐臺灣藍籌30ETF基金", "兆豐美國企業優選投資級公司債ETF基金", "兆豐台灣產業龍頭存股等權重ETF基金",
                         "富蘭克林華美臺灣Smart ETF基金", "富蘭克林華美臺灣ESG永續高息ETF基金",
                         "國泰台灣高股息傘型基金之台灣ESG永續高股息ETF基金", "國泰低波動ETF傘型基金之臺灣低波動股利精選30基金",
                         "元大台灣卓越50基金", "兆豐全球尖端科技多重資產基金"], NAMES)
    assert m["兆豐臺灣藍籌30ETF基金"] == "00690"
    assert m["兆豐美國企業優選投資級公司債ETF基金"] == "00957B"          # US→美國、投等→投資級
    assert m["兆豐台灣產業龍頭存股等權重ETF基金"] == "00921"
    assert m["富蘭克林華美臺灣Smart ETF基金"] == "00905"                  # 簡稱 FT＝富蘭克林華美
    assert m["富蘭克林華美臺灣ESG永續高息ETF基金"] == "00961"
    assert m["國泰台灣高股息傘型基金之台灣ESG永續高股息ETF基金"] == "00878"  # 子基金名沒寫投信 → 補傘型的投信
    assert m["國泰低波動ETF傘型基金之臺灣低波動股利精選30基金"] == "00701"
    assert m["元大台灣卓越50基金"] == "0050"
    assert m["兆豐全球尖端科技多重資產基金"] is None                        # 不是 ETF、對不上就空著


def test_公會_湖裡已有最新月份就不抓(monkeypatch):
    calls = []

    class S:
        def get(self, url, timeout=None):
            calls.append("GET")
            return type("R", (), {"text": SITCA_FORM, "apparent_encoding": "utf-8", "encoding": "utf-8"})()

        def post(self, *a, **k):
            calls.append("POST")
            raise AssertionError("不該 POST")

    monkeypatch.setattr(sitca.http, "session", lambda: S())
    df = sitca.top10(NAMES, have_yms={"202608"})
    assert df.empty and calls == ["GET"]


def test_公會_頁面認不得回空並記前200字(monkeypatch, caplog):
    class S:
        def get(self, url, timeout=None):
            return type("R", (), {"text": "<html>系統維護中</html>", "apparent_encoding": "utf-8", "encoding": "utf-8"})()

    monkeypatch.setattr(sitca.http, "session", lambda: S())
    df = sitca.top10(NAMES)
    assert df.empty and list(df.columns) == sitca.COLS and "系統維護中" in caplog.text


def test_來源優先順序_官網每日_公會月資料_人工整理():
    hold = _hold([{"date": "2026-10-07", "etf": "0050", "code": "2330", "name": "台積電", "weight": 50.0, "shares": 1, "issuer": "元大", "src": "y"}])
    monthly = pd.DataFrame([
        {"date": "2026-08-31", "ym": "202608", "fund": "兆豐臺灣藍籌30ETF基金", "rank": 1, "kind": "國內上市", "code": "2330", "name": "台積電",
         "amount": 1.0, "weight": 25.56, "etf": "00690", "issuer": "兆豐", "src": sitca.URL},
        {"date": "2026-07-31", "ym": "202607", "fund": "兆豐臺灣藍籌30ETF基金", "rank": 1, "kind": "國內上市", "code": "2330", "name": "台積電",
         "amount": 1.0, "weight": 20.0, "etf": "00690", "issuer": "兆豐", "src": sitca.URL},
        {"date": "2026-08-31", "ym": "202608", "fund": "元大台灣卓越50基金", "rank": 1, "kind": "國內上市", "code": "2330", "name": "台積電",
         "amount": 1.0, "weight": 1.0, "etf": "0050", "issuer": "元大", "src": sitca.URL},
    ])
    manual = {"00690": {"asof": "2026-10-07", "items": [{"code": "2330", "name": "台積電", "w": 9.9}]},
              "00911": {"asof": "2026-10-07", "src_name": "玩股網（人工整理）", "items": [{"code": "2330", "name": "台積電", "w": 30.0}]}}
    out = etf_holdings.build(hold, pd.DataFrame(), NAMES, manual=manual, monthly=monthly)["etfs"]
    assert out["0050"]["items"][0]["w"] == 50.0 and not out["0050"].get("monthly")     # ① 官網每日優先
    assert out["00690"]["monthly"] is True and out["00690"]["asof"] == "2026-08-31"      # ② 公會月資料（取最新月份）
    assert out["00690"]["items"][0]["w"] == 25.56 and "公會" in out["00690"]["src_name"]
    assert out["00911"]["manual"] is True                                                # ③ 前兩個都沒有才用人工檔


# ───────────────────────────── 資料日要是持股基準日，不是清單適用的下一個營業日（10-08 晚上公告的是 10-12）
def test_台新_資料日取實際申購總價金那天_不是PUB_DATE():
    page = """<input type="text" id="PUB_DATE" name="PUB_DATE" value="2026-10-12" />
    <h4>台新臺灣永續高息中小型ETF基金(00936)</h4>
    <tr><td>2026/10/8每基數實際申購總價金(元)</td><td>TWD 10,853,053</td></tr>
    <div class="card-header">股票</div><table><tr><th>股票代號</th><th>股票名稱</th><th>股數</th><th>權重(%)</th></tr>
    <tr><td>2330 TT</td><td>台積電</td><td>1,000</td><td>5.1</td></tr></table>"""
    rows = etf_pcf.parse_tsit("00936", page)
    assert rows and rows[0]["date"] == "2026-10-08" and rows[0]["code"] == "2330"


def test_凱基_資料日取淨值日():
    frag = """<div>凱基優選30(00938)</div><div>2026/10/12</div><div>現金申購買回清單公告</div>
    <div>(2026/10/08)每受益權單位淨資產價值(元)</div><div>TWD$26.87</div>
    <table><tr name="content"><td>2330</td><td>台積電</td><td>1,000</td><td>9.5</td></tr></table>"""
    rows = etf_pcf.parse_kgi("00938", frag)
    assert rows and rows[0]["date"] == "2026-10-08"


def test_華南永昌_資料日取BalDate():
    payload = {"Data": {"DataDate": "2026-10-12T00:00:00+08:00", "Pcf": {"BalDate": "2026-10-08T00:00:00+08:00"},
                        "Stocks": [{"StockNo": "2330", "StockName": "台積電", "Weight": 0.4019, "Share": 1000}]}}
    rows = etf_pcf.parse_hn("009808", payload)
    assert rows and rows[0]["date"] == "2026-10-08" and rows[0]["weight"] == 40.19
