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


MARKET_MAP = {"twse": "TWSE", "tpex": "TPEX", "emerging": "EMERGING"}


def stock_info() -> pd.DataFrame:
    """台股總覽：簡稱、上市/上櫃/興櫃、FinMind 產業分類。

    這是「股票簡稱」與「上市櫃別」最省事的單一來源 —— 一支請求全市場搞定，
    不用串證交所與櫃買兩支端點。回補的歷史列沒有名稱，全靠這張表補。
    """
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
        "type": "market_raw",
    })
    df["code"] = df["code"].map(clean_code)
    df["market"] = df["market_raw"].map(MARKET_MAP).fillna(df["market_raw"])
    keep = [c for c in ("code", "name", "industry_finmind", "market") if c in df.columns]
    out = df[keep].dropna(subset=["code"])
    # 同一代號可能出現多列（不同日期的資訊更新），保留最後一筆
    return out.drop_duplicates("code", keep="last").reset_index(drop=True)


# FinMind 財報是長格式：一列一個科目。這裡挑出我們要的科目轉成寬格式。
_FS_FIELDS = {
    "Revenue": "revenue",
    "GrossProfit": "gross_profit",
    "OperatingIncome": "operating_income",
    "IncomeAfterTaxes": "net_income",
    "EPS": "eps",
}
_BS_FIELDS = {
    "OrdinaryShare": "ordinary_share",                      # 股本（元），面額 10 → 股數 = /10
    "EquityAttributableToOwnersOfParent": "equity_parent",  # 母公司權益，算 BPS / ROE
    "TotalAssets": "total_assets",
}


def _quarter_of(date_str: str) -> tuple[int, int] | None:
    try:
        y, m = int(date_str[:4]), int(date_str[5:7])
    except (TypeError, ValueError):
        return None
    q = {3: 1, 6: 2, 9: 3, 12: 4}.get(m)
    return (y, q) if q else None


def _pivot_statement(data: list[dict], fields: dict[str, str], code: str) -> pd.DataFrame:
    df = pd.DataFrame(data)
    if df.empty or "type" not in df.columns:
        return pd.DataFrame()
    df = df[df["type"].isin(fields)]
    if df.empty:
        return pd.DataFrame()
    wide = (df.pivot_table(index="date", columns="type", values="value", aggfunc="last")
              .rename(columns=fields).reset_index())
    wide.columns.name = None
    yq = wide["date"].astype(str).map(_quarter_of)
    wide = wide[yq.notna()].copy()
    wide["year"] = [t[0] for t in yq.dropna()]
    wide["quarter"] = [t[1] for t in yq.dropna()]
    wide["code"] = code
    wide["period_end"] = wide["date"].astype(str)
    return wide.drop(columns="date")


def financial_statements(code: str, start: str, *, wait: bool = True) -> pd.DataFrame:
    """單檔季損益（單季值，非累計）。用來算 TTM EPS。

    FinMind 官方註明 EPS 會因配股回溯調整，所以永遠用「近四季相加」而不是
    拿舊的累計數 —— 回溯調整後四季相加才是正確的 TTM。
    """
    data = http.finmind_get("TaiwanStockFinancialStatements", data_id=code,
                            start_date=start, wait_when_exhausted=wait)
    if not data:
        return pd.DataFrame()
    wide = _pivot_statement(data, _FS_FIELDS, code)
    if wide.empty:
        return wide
    for col in _FS_FIELDS.values():
        if col not in wide.columns:
            wide[col] = pd.NA
        wide[col] = pd.to_numeric(wide[col], errors="coerce")
    wide["announce_date"] = [
        announce_date(y, q) for y, q in zip(wide["year"], wide["quarter"])
    ]
    return wide[["year", "quarter", "code", "period_end", "announce_date",
                 "revenue", "gross_profit", "operating_income", "net_income", "eps"]]


def balance_sheet(code: str, start: str, *, wait: bool = True) -> pd.DataFrame:
    """單檔季資產負債表：股本、母公司權益、總資產。"""
    data = http.finmind_get("TaiwanStockBalanceSheet", data_id=code,
                            start_date=start, wait_when_exhausted=wait)
    if not data:
        return pd.DataFrame()
    wide = _pivot_statement(data, _BS_FIELDS, code)
    if wide.empty:
        return wide
    for col in _BS_FIELDS.values():
        if col not in wide.columns:
            wide[col] = pd.NA
        wide[col] = pd.to_numeric(wide[col], errors="coerce")
    # 台股面額 10 元，股數 = 股本 / 10（減資、私募會有誤差，但免費資料只能到這）
    wide["shares"] = wide["ordinary_share"] / 10.0
    wide["bps"] = wide["equity_parent"] / wide["shares"].replace(0, pd.NA)
    wide["announce_date"] = [
        announce_date(y, q) for y, q in zip(wide["year"], wide["quarter"])
    ]
    return wide[["year", "quarter", "code", "period_end", "announce_date",
                 "ordinary_share", "shares", "equity_parent", "total_assets", "bps"]]


def announce_date(year: int, quarter: int) -> str:
    """財報的法定公告期限，當作資料「可用日」。

    Q1 → 5/15、Q2 → 8/14、Q3 → 11/14、Q4 → 隔年 3/31。
    實際公告通常更早，但我們寧可延後：用早於真實公告日的日期做回測就是偷看未來。
    """
    from .. import config
    m, d = config.FINANCIAL_DEADLINES[int(quarter)]
    y = int(year) + (1 if int(quarter) == 4 else 0)
    return f"{y:04d}-{m}-{d}"


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
    out = out[out["ym"].str.match(r"^\d{4}-\d{2}$", na=False)].copy()
    # 可用日 = 次月 10 日（法定期限）
    out["announce_date"] = out["ym"].map(revenue_announce_date)
    return out


def revenue_announce_date(ym: str) -> str:
    from .. import config
    y, m = int(ym[:4]), int(ym[5:7])
    y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
    return f"{y2:04d}-{m2:02d}-{config.REVENUE_DEADLINE_DAY:02d}"


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
