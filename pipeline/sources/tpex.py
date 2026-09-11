"""櫃買中心（上櫃）—— 全案最脆弱的一環，設計成可失敗、可替換。

實測狀況（2026-09-10）：所有 TPEx 端點對雲端 IP 一律回 403，判定為主動的
bot 防護。GitHub Actions 用共用 IP，被擋的機率比家用 IP 更高。

因此這個模組的契約是：抓得到就用，抓不到就回空 DataFrame，由 run_daily
改走 FinMind 補上櫃資料。整條管線不因為 TPEx 掛掉而中斷。

另一個已知陷阱：非交易日 TPEx 會靜默回傳上一個交易日的資料且不標示，
所以一定要用回傳的 Date 欄位去重，不能用執行日期當主鍵。
"""
from __future__ import annotations

import logging

import pandas as pd

from .. import config
from ..util import http
from ..util.roc import clean_code, is_tradable_security, roc_to_iso, to_float, to_int

log = logging.getLogger(__name__)

_BROWSER_HEADERS = {
    "Referer": "https://www.tpex.org.tw/",
    "Origin": "https://www.tpex.org.tw",
    "Accept": "application/json, text/plain, */*",
}


def available() -> bool:
    """先探一次，讓上層知道這輪要不要走備援。"""
    url = config.TPEX_OPENAPI + config.TPEX_ENDPOINTS["price_daily"]
    return http.get(url, headers=_BROWSER_HEADERS, retries=1) is not None


def price_daily() -> pd.DataFrame:
    """上櫃主板日行情。欄位是英文，與證交所的中文欄位不同，這裡統一。"""
    url = config.TPEX_OPENAPI + config.TPEX_ENDPOINTS["price_daily"]
    raw = http.get(url, headers=_BROWSER_HEADERS)
    if not isinstance(raw, list) or not raw:
        log.warning("TPEx 日行情不可用，上櫃資料本輪改走備援來源")
        return pd.DataFrame()

    rows = []
    for r in raw:
        code = clean_code(r.get("SecuritiesCompanyCode") or r.get("Code"))
        d = roc_to_iso(r.get("Date"))
        # 這支端點會把上萬檔權證一起回傳，一定要濾
        if not code or not d or not is_tradable_security(code):
            continue
        rows.append({
            "date": d,
            "code": code,
            "name": r.get("CompanyName") or r.get("Name"),
            "market": "TPEX",
            "open": to_float(r.get("Open")),
            "high": to_float(r.get("High")),
            "low": to_float(r.get("Low")),
            "close": to_float(r.get("Close")),
            "change": to_float(r.get("Change")),
            "volume": to_int(r.get("TradingShares")),
            "turnover": to_float(r.get("TransactionAmount") or r.get("TradingAmount")),
            "transactions": to_int(r.get("TransactionNumber")),
        })
    df = pd.DataFrame(rows)
    log.info("TPEx 日行情：%d 檔（已濾除權證等非股票標的）", len(df))
    return df
