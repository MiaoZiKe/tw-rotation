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


# ------------------------------------------------------------------ 大盤 / 櫃買 / 台指期日 K

#: 這三個就是總覽最上面那三張卡。symbol 是我們自己的代號，data_id 是 FinMind 的。
INDEX_IDS = {"TSE": "TAIEX", "OTC": "TPEx"}


def index_ohlc(start: str, end: str | None = None, *, wait: bool = True) -> pd.DataFrame:
    """加權指數與櫃買指數的日 K。

    為什麼需要這支（Andy 2026-09-15：「櫃買 台指期怎麼可能沒有日線數據」）
    ----------------------------------------------------------------------
    總覽那三張圖的歷史週期原本走 Yahoo，但：
      - 加權 `^TWII` 可以用
      - 櫃買 `^TWOII` **已經壞掉**（2026-09-15 實測：最後一筆停在 2026-07-17、現價給 269.45 而實際 395）
      - 台指期 Yahoo 根本沒有代號
    FinMind 三個都有，而且欄位口徑跟個股日線一致（open/max/min/close/Trading_Volume/Trading_money）。
    2026-09-15 實測 `TaiwanStockPrice` + `data_id=TPEx`：2026-08 起 31 筆、開高低收齊全。

    一個 symbol 一次請求，兩個就是兩次 —— 對 600 次/小時的額度可以忽略。
    """
    rows = []
    for symbol, data_id in INDEX_IDS.items():
        data = http.finmind_get("TaiwanStockPrice", data_id=data_id,
                                start_date=start, end_date=end,
                                wait_when_exhausted=wait)
        if not data:
            log.warning("FinMind 沒有回 %s（%s）的指數日 K", symbol, data_id)
            continue
        df = pd.DataFrame(data)
        if df.empty:
            continue
        rows.append(pd.DataFrame({
            "date": df["date"].astype(str),
            "symbol": symbol,
            "open": pd.to_numeric(df.get("open"), errors="coerce"),
            "high": pd.to_numeric(df.get("max"), errors="coerce"),
            "low": pd.to_numeric(df.get("min"), errors="coerce"),
            "close": pd.to_numeric(df.get("close"), errors="coerce"),
            "change": pd.to_numeric(df.get("spread"), errors="coerce"),
            "volume": pd.to_numeric(df.get("Trading_Volume"), errors="coerce"),
            "turnover": pd.to_numeric(df.get("Trading_money"), errors="coerce"),
        }))
        log.info("FinMind 指數 %s：%d 筆", symbol, len(df))
    if not rows:
        return pd.DataFrame()
    out = pd.concat(rows, ignore_index=True)
    return out.dropna(subset=["close"])


def _near_month(df: pd.DataFrame, session: str, symbol: str) -> pd.DataFrame:
    """從 `TaiwanFuturesDaily` 的原始列裡，挑出某個交易時段的「近月」日 K。

    `contract_date`：除了單一月份（`202609`），還有價差組合（`202609/202610`）
      → 帶 `/` 的全部丟掉，那是價差不是指數。
    剩下的月份裡取**成交量最大**的那一個 ＝ 近月
      （2026-09-14 實測：202609 量 94,885、202610 量 50,428）。
    """
    d = df[df.get("trading_session").astype(str) == session]
    d = d[~d.get("contract_date").astype(str).str.contains("/", na=False)]
    if d.empty:
        return pd.DataFrame()
    d = d.copy()
    for c in ("open", "max", "min", "close", "volume"):
        d[c] = pd.to_numeric(d.get(c), errors="coerce")
    d = d[(d["close"] > 0) & (d["volume"] > 0)]
    if d.empty:
        return pd.DataFrame()
    # 每天留成交量最大的那個月份（＝近月）
    d = d.sort_values(["date", "volume"]).groupby("date", as_index=False).last()
    return pd.DataFrame({
        "date": d["date"].astype(str),
        "symbol": symbol,
        "open": d["open"], "high": d["max"], "low": d["min"], "close": d["close"],
        "change": pd.to_numeric(d.get("spread"), errors="coerce"),
        "volume": d["volume"],
        "turnover": pd.NA,
    }).dropna(subset=["close"])


def futures_ohlc(start: str, end: str | None = None, *, wait: bool = True) -> pd.DataFrame:
    """台指期（TX）近月的日 K。**一次請求同時吐日盤（FUT）與夜盤（FUT_N）兩個 symbol。**

    FinMind 的 `TaiwanFuturesDaily` 一天會回很多列，要挑對才不會畫出一條莫名其妙的線
    （2026-09-15 實測 2026-09-14 那天有 32 列）：
      - `trading_session`：`position`（一般交易）與 `after_market`（盤後／夜盤）
      - `contract_date`：帶 `/` 的是價差組合，不是指數，要丟掉
      - 剩下的月份裡取成交量最大的那一個 ＝ 近月

    ★ 2026-09-20 這裡從「只取 position」改成「兩個時段都取」
    ------------------------------------------------------
    Andy：「台指期夜盤怎麼可能沒數據，幫我更新走勢圖以及 K 線上去」。
    以前這支刻意只留 `position`，等於**把夜盤的歷史日 K 丟掉** ——
    而總覽那三張卡切到「夜盤 ＋ 日／週／月／季」時就只剩日盤那條線可以畫，
    畫面上還得寫一句「夜盤日 K 資料湖還沒存」。資料其實一直都在同一個回應裡。

    夜盤存成 `FUT_N`（跟日盤的 `FUT` 同一張表 `index_ohlc`，靠 symbol 分）。
    這樣**不多花一次 FinMind 額度** —— 同一次請求本來就兩個時段的列都回來了，
    我們只是不要再把一半丟掉（額度是這個專案最稀缺的東西，DECISIONS #155）。

    ⚠ 還沒實測、寫在這裡免得以後誤會：**FinMind 對 `after_market` 的 `date`
      記成哪一個交易日還沒對帳過**（期交所把盤後交易時段的交易日認定為次一營業日，
      FinMind 是照原樣還是照期交所認定，目前的 token 失效拿不到資料驗證）。
      先照它給的 `date` 原樣存，拿得到真實回應之後要回來對一次帳。
    """
    data = http.finmind_get("TaiwanFuturesDaily", data_id="TX",
                            start_date=start, end_date=end,
                            wait_when_exhausted=wait)
    if not data:
        log.warning("FinMind 沒有回台指期日 K")
        return pd.DataFrame()
    df = pd.DataFrame(data)
    if df.empty:
        return df
    parts = []
    for session, symbol, label in (("position", "FUT", "日盤"),
                                   ("after_market", "FUT_N", "夜盤")):
        out = _near_month(df, session, symbol)
        if out.empty:
            # 夜盤回空不是致命傷（例如那段期間沒有夜盤），但要留一行才查得到
            log.warning("FinMind 台指期%s（%s）沒有可用的列", label, session)
            continue
        log.info("FinMind 台指期%s近月（%s）：%d 天", label, symbol, len(out))
        parts.append(out)
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True)



def futures_ticks(day: str, data_id: str = "TX", *, wait: bool = False) -> pd.DataFrame:
    """台指期某一天的逐筆（TaiwanFuturesTick），給大盤三張圖的 1H／4H 聚合用。

    一天一次請求；失敗／沒權限／當天休市都回空並記 log。
    ⚠ 2026-09-25：容器連不到 FinMind，這個資料集在我們的會員等級能不能拿、
      回應欄位是不是 date/contract_date/price/volume，都還沒實測 —— 第一次在 Actions 跑時看 log。
    """
    data = http.finmind_get("TaiwanFuturesTick", data_id=data_id, start_date=day,
                            wait_when_exhausted=wait)
    if not data:
        err = http.finmind_last_error() or {}
        log.warning("FinMind 台指期逐筆 %s 回空（上游：%s）", day,
                    f"{err.get('status')} {err.get('msg')}" if err else "無錯誤訊息／當天無交易")
        return pd.DataFrame()
    df = pd.DataFrame(data)
    need = {"date", "price"}
    if not need.issubset(df.columns):
        log.warning("FinMind 台指期逐筆欄位對不上，缺 %s；回應前 200 字：%s",
                    sorted(need - set(df.columns)), str(data[:2])[:200])
        return pd.DataFrame()
    if "contract_date" not in df.columns:
        df["contract_date"] = df["futures_id"] if "futures_id" in df.columns else ""
    return df


# ------------------------------------------------------------ 分 K（2026-09-25，櫃買／台指期的 1H／4H）
# 為什麼走 FinMind 分 K：櫃買在 Yahoo 分 K 回「No data found」、台指期逐筆（TaiwanFuturesTick）
# 在 register 等級回 400。證交所 mis 的 mis_ohlc_*.txt、期交所 mis.taifex 的 getChartData1M
# 雖然前端經 Worker 在用，但**都不是** getStockInfo.jsp，不在管線的來源白名單（CLAUDE.md 絕對不要做的事 #1），
# 管線不抓。FinMind 是白名單來源。WebSearch 查證（2026-09-25，只拿得到摘要）：
#   · TaiwanStockKBar 可用 data_id="TAIEX" 取加權分 K，一天 271 筆、指數量固定 0
#     （https://finmind.github.io/WhatIsNew/）；摘要另說支援 3 碼指數代號、101＝櫃買加權（低信心，未見原文）。
#   · TaiwanFuturesKBar 是 2026-09 新增的期貨分 K（https://github.com/FinMind/FinMind/pull/458）。
#   兩者在我們的會員等級拿不拿得到**查不到**（摘要只講整日下載限 sponsorpro），只能在 Actions 看 log。
OTC_KBAR_IDS = ["TPEx", "101"]     # 依序試；第一個有資料的就用


def _kbar_frame(data: list[dict], dataset: str, day: str) -> pd.DataFrame:
    """分 K 回應 → 有 ts 欄（台北時間字串）與 open/high/low/close/volume 的表；欄位對不上回空並印前 200 字。"""
    df = pd.DataFrame(data)
    need = {"date", "open", "high", "low", "close"}
    if not need.issubset(df.columns):
        log.warning("FinMind %s %s 欄位對不上，缺 %s；回應前 200 字：%s",
                    dataset, day, sorted(need - set(df.columns)), str(data[:2])[:200])
        return pd.DataFrame()
    if "minute" in df.columns:
        df["ts"] = df["date"].astype(str).str.slice(0, 10) + " " + df["minute"].astype(str)
    else:
        df["ts"] = df["date"].astype(str)
    if "volume" not in df.columns:
        df["volume"] = 0
    return df


def _kbar_get(dataset: str, data_id: str, day: str, wait: bool, what: str) -> pd.DataFrame:
    data = http.finmind_get(dataset, data_id=data_id, start_date=day, end_date=day,
                            wait_when_exhausted=wait)
    if not data:
        err = http.finmind_last_error() or {}
        log.warning("FinMind %s %s %s 回空（上游：%s）", what, data_id, day,
                    f"{err.get('status')} {err.get('msg')}" if err else "無錯誤訊息／當天無交易")
        return pd.DataFrame()
    return _kbar_frame(data, dataset, day)


def index_kbar(day: str, data_id: str, *, wait: bool = False) -> pd.DataFrame:
    """台股指數某一天的 1 分 K（TaiwanStockKBar）。失敗／沒權限／休市回空並記 log。"""
    return _kbar_get("TaiwanStockKBar", data_id, day, wait, "指數分 K")


def futures_kbar(day: str, data_id: str = "TX", *, wait: bool = False) -> pd.DataFrame:
    """台指期某一天的 1 分 K（TaiwanFuturesKBar），含日盤夜盤、各月份；近月交給聚合那層挑。"""
    df = _kbar_get("TaiwanFuturesKBar", data_id, day, wait, "台指期分 K")
    if not df.empty and "contract_date" not in df.columns:
        df["contract_date"] = df["futures_id"] if "futures_id" in df.columns else ""
    return df
