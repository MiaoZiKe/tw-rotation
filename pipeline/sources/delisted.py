"""已下市股票名單與歷史日價量回補（2026-10-26，修個股回測的存活者偏誤）。

背景：資料湖 2000 檔 4 碼股票裡只有 7 檔在 2026 年前停止交易，幾乎沒有下市股，回測報酬被高估。

來源（都在白名單內）：
  · 名單：FinMind `TaiwanStockDelisting`（下市上櫃股票，欄位依文件為 date／stock_id／stock_name；
          容器連不到 FinMind 所以**尚未實測**，認不得欄位就回空並記 log 前 200 字，不猜）。
          官方對照：證交所「終止上市公司」（欄位：終止上市日期、公司名稱、上市編號，政府資料開放平台 data.gov.tw 資料集 11543）。
          ⚠ 證交所官網清單在 www.twse.com.tw，屬禁爬主機，**不使用**；openapi.twse.com.tw 是否有對應路徑沒查到，
          所以不依賴它，FinMind 回空時只記 log、下一輪重試。
  · 價量：FinMind `TaiwanStockPrice`，一檔一次請求（下市後的歷史日 K FinMind 仍保留）。
只收 2010 年以後下市、4 位數字普通股（roc.is_common_stock），價量從 2008-01-01 起，一律 store.append()。
"""
from __future__ import annotations

import logging

import pandas as pd

from ..util import http
from ..util.roc import is_common_stock

log = logging.getLogger(__name__)

SINCE = "2010-01-01"        # 只收這天之後下市的
PRICE_START = "2008-01-01"  # 價量起點：涵蓋因子研究的訓練窗


def parse_delisting(rows: list[dict] | None, since: str = SINCE) -> pd.DataFrame:
    """FinMind TaiwanStockDelisting -> (code, delist_date, name)，只留 since 之後下市的普通股。"""
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    if not {"date", "stock_id"} <= set(df.columns):
        log.warning("下市名單欄位認不得：%s", str(rows[:1])[:200])
        return pd.DataFrame()
    out = pd.DataFrame({"code": df["stock_id"].astype(str).str.strip(),
                        "delist_date": df["date"].astype(str).str[:10],
                        "name": df["stock_name"].astype(str) if "stock_name" in df.columns else ""})
    out = out[out["code"].map(is_common_stock) & (out["delist_date"] >= since)]
    return out.drop_duplicates("code", keep="last").sort_values("delist_date", ascending=False).reset_index(drop=True)


def delisted_list(*, wait: bool = False) -> pd.DataFrame:
    try:
        rows = http.finmind_get("TaiwanStockDelisting", start_date=SINCE, wait_when_exhausted=wait)
    except Exception as exc:  # noqa: BLE001
        log.warning("下市名單抓取失敗：%s", exc)
        return pd.DataFrame()
    return parse_delisting(rows)
