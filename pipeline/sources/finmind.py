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
import re

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


# ------------------------------------------------------------------ v3：股利 / 融資券 / 股權分散歷史

def _blank_to_none(value) -> str | None:
    """FinMind 的日期欄位沒有值時是空字串，不是 null；統一轉成 None 才不會被當成日期。"""
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _num(value) -> float:
    """數值欄位轉 float，缺值或非數字一律當 0（股利金額相加時不能是 NaN）。"""
    v = pd.to_numeric(value, errors="coerce")
    return 0.0 if pd.isna(v) else float(v)


def fiscal_year_of(period: str | None) -> int | None:
    """從 FinMind 的 year 字串解析所屬年度：'115年第1季' / '114年' → 民國年 + 1911。

    偶爾會直接給西元四位數（'2024'），也一併接受；其他格式回 None。
    """
    if period is None:
        return None
    s = str(period).strip()
    m = re.match(r"^(\d{2,3})年", s)
    if m:
        return int(m.group(1)) + 1911
    if re.fullmatch(r"\d{4}", s):
        return int(s)
    return None


def dividend_events(code: str, start: str, *, wait: bool = True) -> pd.DataFrame:
    """單檔股利公告（TaiwanStockDividend）。

    一筆原始資料同時帶現金與股票股利，這裡展開成 kind = cash / stock 各一列，
    金額為 0 的那一種不輸出，所以一筆最多展開成 2 列。單位：元/股。
    """
    data = http.finmind_get("TaiwanStockDividend", data_id=code,
                            start_date=start, wait_when_exhausted=wait)
    if not data:
        return pd.DataFrame()

    rows = []
    for r in data:
        if not isinstance(r, dict):
            continue
        period = _blank_to_none(r.get("year"))
        if period is None:
            continue
        common = {
            "code": code,
            "period": period,
            "announce_date": _blank_to_none(r.get("AnnouncementDate")),
            "fiscal_year": fiscal_year_of(period),
        }
        cash = _num(r.get("CashEarningsDistribution")) + _num(r.get("CashStatutorySurplus"))
        if cash:
            rows.append({
                **common,
                "kind": "cash",
                "amount": cash,
                "ex_date": _blank_to_none(r.get("CashExDividendTradingDate")),
                "payment_date": _blank_to_none(r.get("CashDividendPaymentDate")),
            })
        stock = _num(r.get("StockEarningsDistribution")) + _num(r.get("StockStatutorySurplus"))
        if stock:
            rows.append({
                **common,
                "kind": "stock",
                "amount": stock,
                "ex_date": _blank_to_none(r.get("StockExDividendTradingDate")),
                "payment_date": None,      # 股票股利沒有發放日，配發即入帳
            })

    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["fiscal_year"] = df["fiscal_year"].astype("Int64")
    # 日期欄位保留 object dtype，讓「沒有日期」維持 None 而不是被字串型別轉成 NaN
    for c in ("announce_date", "ex_date", "payment_date"):
        df[c] = pd.Series([r[c] for r in rows], dtype=object)
    return df[["code", "period", "kind", "amount", "announce_date",
               "ex_date", "payment_date", "fiscal_year"]]


def dividend_results(code: str, start: str, *, wait: bool = True) -> pd.DataFrame:
    """單檔除權息結果（TaiwanStockDividendResult）：除權息日、參考價、當日開盤。

    填息天數不在這裡算 —— build_payload 有整段行情，用行情算才不會漏掉尚未填息的。
    """
    data = http.finmind_get("TaiwanStockDividendResult", data_id=code,
                            start_date=start, wait_when_exhausted=wait)
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    if df.empty or "date" not in df.columns:
        return pd.DataFrame()
    out = pd.DataFrame({
        "date": df["date"].astype(str),
        "code": code,
        "kind": df.get("stock_or_cache_dividend", pd.Series([None] * len(df))).map(_blank_to_none),
        "dividend": pd.to_numeric(df.get("stock_and_cache_dividend"), errors="coerce"),
        "before_price": pd.to_numeric(df.get("before_price"), errors="coerce"),
        "reference_price": pd.to_numeric(df.get("reference_price"), errors="coerce"),
        "open_price": pd.to_numeric(df.get("open_price"), errors="coerce"),
    })
    return out[out["date"].str.match(r"^\d{4}-\d{2}-\d{2}$", na=False)].reset_index(drop=True)


def margin_history(code: str, start: str, *, wait: bool = True) -> pd.DataFrame:
    """單檔融資融券歷史（TaiwanStockMarginPurchaseShortSale），單位張。

    欄位對齊證交所 MI_MARGN 的轉換（twse.margin_daily），可直接 append 進 margin_daily。
    """
    data = http.finmind_get("TaiwanStockMarginPurchaseShortSale", data_id=code,
                            start_date=start, wait_when_exhausted=wait)
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    if df.empty or "date" not in df.columns:
        return pd.DataFrame()

    def col(name: str) -> pd.Series:
        return pd.to_numeric(df.get(name), errors="coerce")

    m_today, m_yday = col("MarginPurchaseTodayBalance"), col("MarginPurchaseYesterdayBalance")
    s_today, s_yday = col("ShortSaleTodayBalance"), col("ShortSaleYesterdayBalance")
    out = pd.DataFrame({
        "date": df["date"].astype(str),
        "code": code,
        "margin_balance": m_today,
        "margin_change": m_today - m_yday,
        "short_balance": s_today,
        "short_change": s_today - s_yday,
        "margin_buy": col("MarginPurchaseBuy"),
        "margin_sell": col("MarginPurchaseSell"),
        "short_sell": col("ShortSaleSell"),
        "short_cover": col("ShortSaleBuy"),
        "offset": col("OffsetLoanAndShort"),
    })
    return out.dropna(subset=["margin_balance"]).reset_index(drop=True)


def _level_lookup() -> dict[str, int]:
    """集保級距標籤（去空白、小寫）→ 級距代號。FinMind 的寫法與集保略有出入，
    另外收幾個已知別名。"""
    from .tdcc import LEVEL_LABELS
    table = {label.replace(" ", "").lower(): lvl for lvl, label in LEVEL_LABELS.items()}
    table.update({
        "morethan1,000,001": 15,
        "morethan1000001": 15,
        "1,000,001以上": 15,
        "1000001以上": 15,
        "total": 17,
        "合計": 17,
        "差異數調整": 16,
    })
    return table


def holding_level(label) -> int | None:
    """寬鬆對照：去掉空白、不分大小寫，對不上回 None。"""
    if label is None:
        return None
    key = re.sub(r"\s+", "", str(label)).lower()
    if not key:
        return None
    return _level_lookup().get(key)


def holding_history(code: str, start: str, *, wait: bool = True) -> pd.DataFrame:
    """單檔集保股權分散歷史（TaiwanStockHoldingSharesPer），欄位對齊 tdcc。

    免費層不一定開放這個資料集；非 200 由 http.finmind_get 回 None → 這裡回空。
    """
    data = http.finmind_get("TaiwanStockHoldingSharesPer", data_id=code,
                            start_date=start, wait_when_exhausted=wait)
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    if df.empty or "date" not in df.columns or "HoldingSharesLevel" not in df.columns:
        return pd.DataFrame()

    from .tdcc import LEVEL_LABELS
    level = df["HoldingSharesLevel"].map(holding_level)
    unknown = sorted(set(df.loc[level.isna(), "HoldingSharesLevel"].astype(str)))
    if unknown:
        log.warning("%s 股權分散有對不上的級距，已略過：%s", code, unknown)
    keep = level.notna()
    if not keep.any():
        return pd.DataFrame()
    lvl = level[keep].astype(int)
    out = pd.DataFrame({
        "date": df.loc[keep, "date"].astype(str),
        "code": code,
        "level": lvl.values,
        "level_label": [LEVEL_LABELS.get(v, str(v)) for v in lvl],
        "holders": pd.to_numeric(df.loc[keep].get("people"), errors="coerce").astype("Int64"),
        "shares": pd.to_numeric(df.loc[keep].get("unit"), errors="coerce"),
        "pct": pd.to_numeric(df.loc[keep].get("percent"), errors="coerce"),
    })
    return out.reset_index(drop=True)
