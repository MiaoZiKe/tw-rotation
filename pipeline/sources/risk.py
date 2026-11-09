"""風險警示牌（P-1107-02，Andy 2026-11-09 點頭）：交易所公布的注意股、處置股。

四支端點都是官方 OpenAPI（白名單內），欄位 2026-11-09 在 Actions 上實測過，fixture 在
docs/fixtures/risk_flag_probe.json：

  上市注意  openapi.twse.com.tw/v1/announcement/notice
            Number, Code, Name, NumberOfAnnouncement, TradingInfoForAttention, Date, ClosingPrice, PE
            ⚠ 盤中打回來是一筆空殼（Code=""、Date=""）——「當日」名單要盤後才有，空殼一律丟掉。
  上市處置  openapi.twse.com.tw/v1/announcement/punish
            Number, Date, Code, Name, NumberOfAnnouncement, ReasonsOfDisposition,
            DispositionPeriod（115/11/09～115/11/13）, DispositionMeasures（第一次處置）, Detail, LinkInformation
  上櫃注意  www.tpex.org.tw/openapi/v1/tpex_trading_warning_information
            Date, SecuritiesCompanyCode, CompanyName, TradingInformation, ClosePrice, PriceEarningRatio
  上櫃處置  www.tpex.org.tw/openapi/v1/tpex_disposal_information
            Date, SecuritiesCompanyCode, CompanyName, DispositionPeriod（1151105~1151111）,
            DispositionReasons, DisposalCondition

規矩：
- 日期一律取回應裡的 Date（公布日），不用執行當天；處置起訖取 DispositionPeriod。
- 撮合方式只「原文摘句」（例如「約每二分鐘撮合一次」），不自己推算；預收款券只看原文有沒有
  「收取全部之買進價金」這句。處置門檻、累計次數會不會達標，一律不推算（提案法遵段）。
- 失敗回空 DataFrame，原因掛 attrs["error"]；任何一支掛了不影響另一支。
"""
from __future__ import annotations

import logging
import re

import pandas as pd

from .. import config
from ..util import http
from ..util.roc import clean_code, roc_to_iso, to_float

log = logging.getLogger(__name__)

NOTICE_COLS = ["date", "code", "market", "name", "reason", "close", "pe", "ann_n"]
PUNISH_COLS = ["date", "code", "market", "name", "start", "end", "reason", "measure", "match", "prepay", "detail", "ann_n"]

# 「約每二分鐘撮合一次」「約每2分鐘撮合一次」「約每10分鐘撮合一次」——原文怎麼寫就怎麼留
_MATCH_RE = re.compile(r"約每[0-9０-９一二三四五六七八九十]+分鐘撮合一次")
_PREPAY_KEYS = ("收取全部之買進價金", "收取全部買進價金")


def _pick(row: dict, *names: str):
    norm = {str(k).strip(): v for k, v in row.items()}
    for n in names:
        if n in norm and norm[n] not in (None, ""):
            return norm[n]
    return None


def _txt(v) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def parse_period(s) -> tuple[str | None, str | None]:
    """處置期間 → (起, 訖) ISO。上市「115/11/09～115/11/13」、上櫃「1151105~1151111」兩種寫法。"""
    if not s:
        return None, None
    parts = re.split(r"\s*[~～〜－-]\s*", str(s).strip(), maxsplit=1)
    if len(parts) != 2:
        return None, None
    return roc_to_iso(parts[0]), roc_to_iso(parts[1])


def match_phrase(detail) -> str | None:
    m = _MATCH_RE.search(str(detail or ""))
    return m.group(0) if m else None


def parse_notice(rows, market: str) -> pd.DataFrame:
    """注意股原始列 → risk_notice。沒有代號或沒有日期的列（盤中空殼）丟掉。"""
    out = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        code = clean_code(_pick(r, "Code", "SecuritiesCompanyCode"))
        d = roc_to_iso(_pick(r, "Date"))
        if not code or not d:
            continue
        out.append({
            "date": d, "code": code, "market": market,
            "name": _txt(_pick(r, "Name", "CompanyName")),
            "reason": _txt(_pick(r, "TradingInfoForAttention", "TradingInformation")),
            "close": to_float(_pick(r, "ClosingPrice", "ClosePrice")),
            "pe": to_float(_pick(r, "PE", "PriceEarningRatio")),
            "ann_n": to_float(_pick(r, "NumberOfAnnouncement")),
        })
    if not out:
        if rows:
            log.info("%s 注意股：%d 列都沒有代號或日期（盤中空殼或今天沒有名單）", market, len(rows))
        return pd.DataFrame(columns=NOTICE_COLS)
    return pd.DataFrame(out, columns=NOTICE_COLS).drop_duplicates(["date", "code", "market"], keep="last").reset_index(drop=True)


def parse_punish(rows, market: str) -> pd.DataFrame:
    """處置股原始列 → risk_punish。"""
    out = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        code = clean_code(_pick(r, "Code", "SecuritiesCompanyCode"))
        d = roc_to_iso(_pick(r, "Date"))
        if not code or not d:
            continue
        st, en = parse_period(_pick(r, "DispositionPeriod"))
        detail = _txt(_pick(r, "Detail", "DisposalCondition")) or ""
        out.append({
            "date": d, "code": code, "market": market,
            "name": _txt(_pick(r, "Name", "CompanyName")),
            "start": st, "end": en,
            "reason": _txt(_pick(r, "ReasonsOfDisposition", "DispositionReasons")),
            "measure": _txt(_pick(r, "DispositionMeasures")),
            "match": match_phrase(detail),
            "prepay": any(k in detail for k in _PREPAY_KEYS),
            "detail": detail[:2000] or None,
            "ann_n": to_float(_pick(r, "NumberOfAnnouncement")),
        })
    if not out:
        return pd.DataFrame(columns=PUNISH_COLS)
    return pd.DataFrame(out, columns=PUNISH_COLS).drop_duplicates(["date", "code", "market"], keep="last").reset_index(drop=True)


def _get(url: str, src: str, errs: list) -> list | None:
    data = http.get(url)
    if not isinstance(data, list):
        errs.append(f"{src} 回應空白或格式非預期")
        log.warning("%s 回應空白或格式非預期：%s", src, str(data)[:200])
        return None
    return data


def _collect(kind: str) -> pd.DataFrame:
    errs: list[str] = []
    frames, raw_ok = [], False
    parse = parse_notice if kind == "notice" else parse_punish
    for market, url in ((
        ("TWSE", config.TWSE_OPENAPI + config.TWSE_ENDPOINTS["risk_" + kind]),
        ("TPEX", config.TPEX_OPENAPI + config.TPEX_ENDPOINTS["risk_" + kind]),
    )):
        rows = _get(url, f"{market} {kind}", errs)
        if rows is None:
            continue
        raw_ok = True
        df = parse(rows, market)
        if not df.empty:
            frames.append(df)
    cols = NOTICE_COLS if kind == "notice" else PUNISH_COLS
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=cols)
    if errs:
        out.attrs["error"] = "；".join(errs)
    if out.empty and raw_ok and not errs:
        # 端點有回、只是今天沒有名單（或注意股盤中還沒公布）：不是失敗
        out.attrs["skipped"] = "交易所回應正常，目前沒有新的名單"
    return out


def notice() -> pd.DataFrame:
    """上市＋上櫃注意股（當日公布）。"""
    return _collect("notice")


def punish() -> pd.DataFrame:
    """上市＋上櫃處置股（目前公布中的處置）。"""
    return _collect("punish")
