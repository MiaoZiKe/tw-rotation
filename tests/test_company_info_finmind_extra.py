"""company_info：證交所那支失敗時，FinMind 不可以把上市公司的證交所產業別蓋掉。

2026-10-28 晚上那輪 t187ap03_L 回空，FinMind 3168 列全部被當補充寫入，
上市公司的產業別被 FinMind 大類「電子工業」蓋掉（志聖從電子零組件業變電子工業），
族群離群檢查一次冒出 14 筆假警報。這裡鎖住修正後的行為。
"""
import pandas as pd

from pipeline.run_daily import finmind_company_extra


def _info():
    return pd.DataFrame({
        "code": ["2467", "6223", "9999"],
        "name": ["志聖", "旺矽", "新上櫃"],
        "market": ["TWSE", "TPEX", "TPEX"],
        "industry_finmind": ["電子工業", "半導體業", "半導體業"],
    })


def _lake():
    return pd.DataFrame({
        "code": ["2467", "6223"],
        "industry": ["電子零組件業", "半導體業"],
        "industry_code": ["28", None],   # 只有證交所版本有 industry_code
    })


def test_證交所今天失敗_湖裡的證交所列不被蓋掉():
    out = finmind_company_extra(_info(), pd.DataFrame(), _lake())
    assert "2467" not in set(out["code"])
    # 上櫃（只有 FinMind 來源）照常刷新，新代號照常補
    assert set(out["code"]) == {"6223", "9999"}
    assert list(out.columns) == ["code", "name", "market", "industry"]
    assert out.set_index("code").loc["9999", "industry"] == "半導體業"


def test_證交所今天成功_排除今天抓到的代號():
    company = pd.DataFrame({"code": ["2467"]})
    out = finmind_company_extra(_info(), company, None)
    assert set(out["code"]) == {"6223", "9999"}


def test_湖是空的_也沒有今天的證交所資料_全部補():
    out = finmind_company_extra(_info(), pd.DataFrame(), pd.DataFrame())
    assert set(out["code"]) == {"2467", "6223", "9999"}


def test_FinMind_空資料():
    out = finmind_company_extra(pd.DataFrame(), pd.DataFrame(), _lake())
    assert out.empty
    assert list(out.columns) == ["code", "name", "market", "industry"]


def test_舊湖沒有_industry_code_欄位不會出錯():
    lake = pd.DataFrame({"code": ["2467"], "industry": ["電子零組件業"]})
    out = finmind_company_extra(_info(), pd.DataFrame(), lake)
    assert set(out["code"]) == {"2467", "6223", "9999"}
