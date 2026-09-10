"""FinMind 免費版 —— 歷史回補主力，以及三大法人籌碼的唯一免費合規來源。

為什麼籌碼走這裡而不是證交所：
證交所的個股別三大法人（T86）只存在於官網 API，而官網使用條款明文禁止
以自動化程式抓取。FinMind 的 TaiwanStockInstitutionalInvestorsBuySell 是
免費資料集，取得同樣的資訊而不觸碰那條界線。

額度紀律：免費層 600 req/hr 且不支援「一次查全市場」，逐檔查會很快撞牆。
所有呼叫都經過 util.http.finmind_get 的跨程序額度管理。
"""
from __future__ import annotations

import logging

import pandas as pd

from ..util import http
from ..util.roc import clean_code

log = logging.getLogger(__name__)

# FinMind 的法人名稱 -> 我們的欄位名
INVESTOR_MAP = {
    "Foreign_Investor": "foreign",
    "Foreign_Dealer_Self": "foreign_dealer",
    "Investment_Trust": "trust",
    "Dealer_self": "dealer_self",
    "Dealer_Hedging": "dealer_hedge",
    "Dealer": "dealer_self",
}


def stock_info() -> pd.DataFrame:
    """台股總覽，含 FinMind 自己的產業分類。用來建立回補用的股票清單。"""
    data = http.finmind_get("TaiwanStockInfo")
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    if df.empty:
        return df
    df = df.rename(columns={
        "stock_id": "code",
        "stock_name": "name",
        "industry_category": "industry_finmind",
        "type": "market",
    })
    df["code"] = df["code"].map(clean_code)
    keep = [c for c in ("code", "name", "industry_finmind", "market") if c in df.columns]
    return df[keep].dropna(subset=["code"]).drop_duplicates("code")


def price_history(code: str, start: str, end: str | None = None,
                  *, wait: bool = True) -> pd.DataFrame:
    """單檔日 K 歷史。回補用，一檔一次請求。"""
    data = http.finmind_get("TaiwanStockPrice", data_id=code,
                            start_date=start, end_date=end,
                            wait_when_exhausted=wait)
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    if df.empty:
        return df
    out = pd.DataFrame({
        "date": df["date"].astype(str),
        "code": code,
        "open": pd.to_numeric(df.get("open"), errors="coerce"),
        "high": pd.to_numeric(df.get("max"), errors="coerce"),
        "low": pd.to_numeric(df.get("min"), errors="coerce"),
        "close": pd.to_numeric(df.get("close"), errors="coerce"),
        "change": pd.to_numeric(df.get("spread"), errors="coerce"),
        "volume": pd.to_numeric(df.get("Trading_Volume"), errors="coerce"),
        "turnover": pd.to_numeric(df.get("Trading_money"), errors="coerce"),
        "transactions": pd.to_numeric(df.get("Trading_turnover"), errors="coerce"),
    })
    out["market"] = "FINMIND"
    return out.dropna(subset=["close"])


def institutional(code: str, start: str, end: str | None = None,
                  *, wait: bool = True) -> pd.DataFrame:
    """單檔三大法人買賣超。

    FinMind 是長格式（每個法人一列），這裡轉成寬格式：
    一列一天，外資 / 投信 / 自營各一欄，單位為股。
    """
    data = http.finmind_get("TaiwanStockInstitutionalInvestorsBuySell",
                            data_id=code, start_date=start, end_date=end,
                            wait_when_exhausted=wait)
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    if df.empty or "name" not in df.columns:
        return pd.DataFrame()

    df["net"] = pd.to_numeric(df.get("buy"), errors="coerce").fillna(0) - \
                pd.to_numeric(df.get("sell"), errors="coerce").fillna(0)
    df["field"] = df["name"].map(INVESTOR_MAP)
    df = df.dropna(subset=["field"])
    if df.empty:
        return pd.DataFrame()

    wide = (df.pivot_table(index="date", columns="field", values="net",
                           aggfunc="sum")
              .reset_index())
    wide.columns.name = None
    for col in ("foreign", "foreign_dealer", "trust", "dealer_self", "dealer_hedge"):
        if col not in wide.columns:
            wide[col] = 0.0

    wide["code"] = code
    wide["date"] = wide["date"].astype(str)
    wide["dealer"] = wide["dealer_self"] + wide["dealer_hedge"]
    wide["foreign_total"] = wide["foreign"] + wide["foreign_dealer"]
    wide["inst_total"] = wide["foreign_total"] + wide["trust"] + wide["dealer"]
    return wide[["date", "code", "foreign", "foreign_dealer", "foreign_total",
                 "trust", "dealer_self", "dealer_hedge", "dealer", "inst_total"]]


def per_history(code: str, start: str, end: str | None = None,
                *, wait: bool = True) -> pd.DataFrame:
    """單檔 PER / PBR / 殖利率歷史，補證交所快照沒有的歷史。"""
    data = http.finmind_get("TaiwanStockPER", data_id=code,
                            start_date=start, end_date=end,
                            wait_when_exhausted=wait)
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    if df.empty:
        return df
    return pd.DataFrame({
        "date": df["date"].astype(str),
        "code": code,
        "pe": pd.to_numeric(df.get("PER"), errors="coerce"),
        "pb": pd.to_numeric(df.get("PBR"), errors="coerce"),
        "dividend_yield": pd.to_numeric(df.get("dividend_yield"), errors="coerce"),
    })


def month_revenue(code: str, start: str, *, wait: bool = True) -> pd.DataFrame:
    """單檔月營收歷史。"""
    data = http.finmind_get("TaiwanStockMonthRevenue", data_id=code,
                            start_date=start, wait_when_exhausted=wait)
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    if df.empty:
        return df
    year = pd.to_numeric(df.get("revenue_year"), errors="coerce")
    month = pd.to_numeric(df.get("revenue_month"), errors="coerce")
    out = pd.DataFrame({
        "ym": year.astype("Int64").astype(str) + "-" +
              month.astype("Int64").astype(str).str.zfill(2),
        "code": code,
        "revenue": pd.to_numeric(df.get("revenue"), errors="coerce"),
    })
    return out[out["ym"].str.match(r"^\d{4}-\d{2}$", na=False)]


def news(code: str | None = None, start: str | None = None,
         *, wait: bool = False) -> pd.DataFrame:
    """個股相關新聞。沒有 code 時 FinMind 會拒絕，所以一定要帶。"""
    if not code:
        return pd.DataFrame()
    data = http.finmind_get("TaiwanStockNews", data_id=code,
                            start_date=start, wait_when_exhausted=wait)
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    if df.empty:
        return df
    df["code"] = code
    return df
