"""全市場融資餘額＋期貨三大法人未平倉＋微台全市場未平倉（FinMind，2026-10-20，Andy：「融資餘額以及期貨多空比和外資多空口數，新增在市場明細內」）。

三張表（都註冊在 config.TABLES，一律 store.append() 增量、日期用回應裡的 date）：
  · margin_total  ← FinMind `TaiwanStockTotalMarginPurchaseShortSale`（整體市場融資融券；上市）
                   一天三列 name＝MarginPurchase（張）／ShortSale（張）／MarginPurchaseMoney（元，實測 6.4e11），
                   欄位 TodayBalance／YesBalance。攤成一天一列。
  · fut_inst      ← FinMind `TaiwanFuturesInstitutionalInvestors`（期交所三大法人區分各期貨契約，所有月份合計）
                   data_id＝TX（大台）、TMF（微台）；institutional_investors＝自營商／投信／外資。
  · fut_oi        ← FinMind `TaiwanFuturesDaily` data_id＝TMF（一般交易時段 position），
                   各單一月份契約 open_interest 加總＝微台全市場未平倉（價差單 contract_date 帶 `/` 的丟掉）。
欄位名依 FinMind 文件與社群範例；容器連不到外網，第一次 Actions 才會實測，
所以解析一律「找不到欄位就回空並記 log（含回應前 200 字）」，不猜、不寫壞資料進只增不改的湖。
"""
from __future__ import annotations

import logging

import pandas as pd

from ..util import http

log = logging.getLogger(__name__)

WHO_MAP = (("外資", "foreign"), ("投信", "trust"), ("自營", "dealer"))
FUT_IDS = ("TX", "TMF")   # TX 大台（外資口數頁）、TMF 微台（2024-08 起；散戶多空比頁）


def _head(rows) -> str:
    return str(rows[:1])[:200]


def parse_margin_total(rows: list[dict] | None) -> pd.DataFrame:
    """整體市場融資融券 → 一天一列。融資金額單位仟元，張數單位張。"""
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    need = {"date", "name", "TodayBalance"}
    if not need <= set(df.columns):
        log.warning("margin_total 欄位認不得：%s", _head(rows))
        return pd.DataFrame()
    df["date"] = df["date"].astype(str).str[:10]
    for c in ("TodayBalance", "YesBalance"):
        df[c] = pd.to_numeric(df.get(c), errors="coerce")
    out = {}
    for name, key in (("MarginPurchase", "margin_lots"), ("ShortSale", "short_lots"),
                      ("MarginPurchaseMoney", "margin_money")):
        s = df[df["name"] == name].drop_duplicates("date", keep="last").set_index("date")
        out[key] = s["TodayBalance"]
        out[key + "_prev"] = s["YesBalance"]
    res = pd.DataFrame(out).reset_index().rename(columns={"index": "date"})
    if "margin_lots" not in res or res["margin_lots"].isna().all():
        log.warning("margin_total 沒有 MarginPurchase 列：%s", _head(rows))
        return pd.DataFrame()
    return res.sort_values("date").reset_index(drop=True)


def _who(v) -> str | None:
    s = str(v)
    for zh, en in WHO_MAP:
        if zh in s:
            return en
    return None


def parse_fut_inst(rows: list[dict] | None, futures_id: str) -> pd.DataFrame:
    """期貨三大法人 → (date, futures_id, who) 一列。口數＝口，金額＝仟元。"""
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    cols = {"long_open_interest_balance_volume": "long_oi", "short_open_interest_balance_volume": "short_oi",
            "long_open_interest_balance_amount": "long_oi_amt", "short_open_interest_balance_amount": "short_oi_amt",
            "long_deal_volume": "long_vol", "short_deal_volume": "short_vol"}
    if "date" not in df.columns or "institutional_investors" not in df.columns \
            or "long_open_interest_balance_volume" not in df.columns:
        log.warning("fut_inst(%s) 欄位認不得：%s", futures_id, _head(rows))
        return pd.DataFrame()
    df["who"] = df["institutional_investors"].map(_who)
    df = df.dropna(subset=["who"])
    out = pd.DataFrame({"date": df["date"].astype(str).str[:10], "futures_id": futures_id, "who": df["who"]})
    for src, dst in cols.items():
        out[dst] = pd.to_numeric(df.get(src), errors="coerce").values
    return out.drop_duplicates(["date", "futures_id", "who"], keep="last").reset_index(drop=True)


def parse_fut_oi(rows: list[dict] | None, futures_id: str) -> pd.DataFrame:
    """期貨日資料 → 一般交易時段各月份未平倉加總。"""
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    if not {"date", "contract_date", "open_interest"} <= set(df.columns):
        log.warning("fut_oi(%s) 欄位認不得：%s", futures_id, _head(rows))
        return pd.DataFrame()
    if "trading_session" in df.columns:
        df = df[df["trading_session"].astype(str) == "position"]
    df = df[~df["contract_date"].astype(str).str.contains("/", na=False)].copy()
    df["open_interest"] = pd.to_numeric(df["open_interest"], errors="coerce")
    df = df.dropna(subset=["open_interest"])
    if df.empty:
        return pd.DataFrame()
    g = df.groupby(df["date"].astype(str).str[:10], as_index=False)["open_interest"].sum()
    return pd.DataFrame({"date": g["date"], "futures_id": futures_id, "oi": g["open_interest"]})


def collect(start: str, end: str | None = None, *, wait: bool = False) -> dict[str, pd.DataFrame]:
    """一次抓五個請求（margin 1＋fut_inst 2＋fut_oi 1，共 4 次額度），回 {表名: DataFrame}；失敗的回空。"""
    out: dict[str, list[pd.DataFrame]] = {"margin_total": [], "fut_inst": [], "fut_oi": []}
    kw = dict(start_date=start, end_date=end, wait_when_exhausted=wait)
    out["margin_total"].append(parse_margin_total(
        http.finmind_get("TaiwanStockTotalMarginPurchaseShortSale", **kw)))
    for fid in FUT_IDS:
        out["fut_inst"].append(parse_fut_inst(
            http.finmind_get("TaiwanFuturesInstitutionalInvestors", data_id=fid, **kw), fid))
    out["fut_oi"].append(parse_fut_oi(http.finmind_get("TaiwanFuturesDaily", data_id="MTX", **kw), "MTX"))
    res = {}
    for k, v in out.items():
        v = [x for x in v if x is not None and not x.empty]
        res[k] = pd.concat(v, ignore_index=True) if v else pd.DataFrame()
        log.info("mktfut %s：%d 列", k, len(res[k]))
    return res
