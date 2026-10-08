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
