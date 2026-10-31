"""除權除息預告表（證交所 openapi TWT48U_ALL＋櫃買 openapi），只取 ETF（代號 00 開頭）。

為什麼要有這支（Andy 2026-11-01：「ETF 行事曆每個禮拜都要更新 到下個月」）：
FinMind 的 TaiwanStockDividend 要等投信公告配息後才有列，ETF 的下個月除息常常還沒進來，
配息行事曆下個月整月空白。預告表是交易所每天更新的「已排定除息」清單，補在 FinMind 前面。

契約：失敗回空 DataFrame，原因掛在 attrs["error"]、attrs["raw_ok"]=是否至少一支端點回了資料；
解析失敗把實際回應前 200 字印進 log（上游改欄位是常態）。欄位名沒有實測過（容器連不到外網），
所以每個欄位都給候選名單＋模糊比對，抓到的欄位名也會記 log，下一個人才修得動。
輸出格式同 etf_dividend_events：code, period(民國年), kind=cash, amount, announce_date, ex_date, payment_date, fiscal_year。
"""
from __future__ import annotations

import logging

import pandas as pd

from .. import config
from ..util import http
from ..util.roc import clean_code, roc_to_iso, to_float

log = logging.getLogger(__name__)

COLS = ["code", "period", "kind", "amount", "announce_date", "ex_date", "payment_date", "fiscal_year"]
_DATE_KEYS = ("Date", "除權除息日期", "除權息日期", "除息日期", "ExDate", "除權息日")
_CODE_KEYS = ("Code", "SecuritiesCompanyCode", "股票代號", "證券代號", "代號")
_CASH_KEYS = ("CashDividend", "現金股利", "息值", "現金股利(元/股)", "CashDividendPerShare")


def _pick(row: dict, names: tuple[str, ...], fuzzy: tuple[str, ...] = ()):
    norm = {str(k).strip(): v for k, v in row.items()}
    for n in names:
        if n in norm:
            return norm[n]
    for k, v in norm.items():
        if fuzzy and any(f in k for f in fuzzy):
            return v
    return None


def is_etf(code: str | None) -> bool:
    return bool(code) and str(code).startswith("00") and len(str(code)) >= 5


def parse(rows: list, source: str) -> pd.DataFrame:
    """把預告表原始列轉成 etf_dividend_events 格式；只留 ETF、金額 > 0、日期可解析的列。"""
    out = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        code = clean_code(_pick(r, _CODE_KEYS))
        ex = roc_to_iso(_pick(r, _DATE_KEYS, ("日期", "Date")))
        amt = to_float(_pick(r, _CASH_KEYS, ("CashDiv", "現金", "息值")))
        if not code or not is_etf(code) or not ex or not amt or amt <= 0:
            continue
        year = int(ex[:4])
        out.append({"code": str(code), "period": str(year - 1911), "kind": "cash", "amount": float(amt),
                    "announce_date": None, "ex_date": ex, "payment_date": None, "fiscal_year": pd.NA})
    if not out:
        if rows:
            log.warning("%s 預告表有 %d 列但沒有可用的 ETF 列，第一列：%s", source, len(rows), str(rows[0])[:200])
        return pd.DataFrame(columns=COLS)
    df = pd.DataFrame(out, columns=COLS)
    df["fiscal_year"] = df["fiscal_year"].astype("Int64")
    return df.drop_duplicates(subset=["code", "ex_date"], keep="last").reset_index(drop=True)


def _fetch(url: str, source: str):
    data = http.get(url)
    if not isinstance(data, list) or not data:
        log.warning("%s 預告表回應空白或格式非預期：%s", source, str(data)[:200])
        return None
    return data


def fetch() -> pd.DataFrame:
    """證交所＋櫃買預告表合併（只 ETF）。任何一支掛了不影響另一支。"""
    frames, errs, raw_ok = [], [], False
    for src, url in (("TWSE", config.TWSE_OPENAPI + config.TWSE_ENDPOINTS["exright_notice"]),
                     ("TPEX", config.TPEX_OPENAPI + config.TPEX_ENDPOINTS["exright_notice"])):
        try:
            data = _fetch(url, src)
        except Exception as exc:  # noqa: BLE001
            data, _ = None, errs.append(f"{src}:{exc}"[:120])
        if data is None:
            errs.append(f"{src} 無回應")
            continue
        raw_ok = True
        log.info("%s 預告表 %d 列，欄位：%s", src, len(data), list(data[0].keys())[:10] if isinstance(data[0], dict) else "?")
        try:
            frames.append(parse(data, src))
        except Exception as exc:  # noqa: BLE001
            errs.append(f"{src} 解析失敗:{exc}"[:120])
    frames = [f for f in frames if not f.empty]
    df = (pd.concat(frames, ignore_index=True).drop_duplicates(subset=["code", "ex_date"], keep="first")
          if frames else pd.DataFrame(columns=COLS))
    df.attrs["raw_ok"] = raw_ok
    if errs:
        df.attrs["error"] = "；".join(errs)[:300]
    return df
