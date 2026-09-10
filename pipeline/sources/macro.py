"""國際連動與總經。

國際指數走 yfinance（免 key），總經走 FRED REST API（免費，需註冊 key）。
刻意不用 fredapi 套件 —— 它自 2024 起停止維護，直接打 REST 更可靠。
"""
from __future__ import annotations

import logging

import pandas as pd

from .. import config
from ..util import http

log = logging.getLogger(__name__)


def intl_daily(period: str = "1y") -> pd.DataFrame:
    """費半、那斯達克、美元指數、VIX、台幣匯率等，M4 國際連動盤的原料。"""
    try:
        import yfinance as yf
    except ImportError:
        log.warning("未安裝 yfinance，跳過國際指數")
        return pd.DataFrame()

    frames = []
    for symbol, label in config.INTL_SYMBOLS.items():
        try:
            hist = yf.Ticker(symbol).history(period=period, auto_adjust=False)
        except Exception as exc:
            log.warning("yfinance %s 抓取失敗：%s", symbol, exc)
            continue
        if hist is None or hist.empty:
            log.warning("yfinance %s 回傳空白", symbol)
            continue
        hist = hist.reset_index()
        frames.append(pd.DataFrame({
            "date": pd.to_datetime(hist["Date"]).dt.date.astype(str),
            "symbol": symbol,
            "label": label,
            "close": pd.to_numeric(hist["Close"], errors="coerce"),
            "volume": pd.to_numeric(hist.get("Volume"), errors="coerce"),
        }).dropna(subset=["close"]))

    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    log.info("國際指數：%d 列 / %d 個標的", len(df), df["symbol"].nunique())
    return df


def fred_series(series_id: str, start: str = "2015-01-01") -> pd.DataFrame:
    if not config.FRED_KEY:
        log.info("未設定 FRED_API_KEY，跳過 %s", series_id)
        return pd.DataFrame()

    payload = http.get(config.FRED_API, params={
        "series_id": series_id,
        "api_key": config.FRED_KEY,
        "file_type": "json",
        "observation_start": start,
    })
    if not isinstance(payload, dict):
        return pd.DataFrame()
    obs = payload.get("observations") or []
    rows = [
        {"date": o["date"], "series": series_id,
         "label": config.FRED_SERIES.get(series_id, series_id),
         "value": float(o["value"])}
        for o in obs if o.get("value") not in (".", "", None)
    ]
    return pd.DataFrame(rows)


def macro_all(start: str = "2015-01-01") -> pd.DataFrame:
    frames = [f for f in (fred_series(s, start) for s in config.FRED_SERIES) if not f.empty]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)
