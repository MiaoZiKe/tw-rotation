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


def release_calendar(days_back: int = 120, days_ahead: int = 240,
                     today: str | None = None) -> pd.DataFrame:
    """FRED 各統計發布的公布日程（財報日曆的「FED 與美國重大數據」用）。

    端點：fred/release/dates?release_id=<id>&include_release_dates_with_no_data=true ——
    帶上 include_release_dates_with_no_data 才會列出**還沒公布**的未來日期（不帶只回已經有資料的過去日期）。
    release_id 見 config.FRED_RELEASES（CPI 10、非農 50、GDP 53、PCE 54）。

    回傳欄位：date（公布日，美東）, release（cpi/nfp/gdp/pce）, release_id, fetched（抓取日，UTC）。
    沒有金鑰、端點失敗一律回空 DataFrame —— 財報日曆會退回 YAML 的日程（pipeline/calendar/macro_events.yaml），不讓管線掛掉。
    today 只給測試用；正式執行取 UTC 今天（這裡不是交易日，是「抓取當下」的時間戳，不違反 CLAUDE.md 第 3 條）。
    """
    if not config.FRED_KEY:
        log.info("未設定 FRED_API_KEY，跳過 FRED 公布日程")
        return pd.DataFrame()
    t0 = pd.Timestamp(today) if today else pd.Timestamp.now("UTC").tz_localize(None).normalize()
    start = (t0 - pd.Timedelta(days=days_back)).strftime("%Y-%m-%d")
    end = (t0 + pd.Timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    rows = []
    for rid, key in config.FRED_RELEASES.items():
        payload = http.get(config.FRED_RELEASE_DATES_API, params={
            "release_id": rid, "api_key": config.FRED_KEY, "file_type": "json",
            "realtime_start": start, "realtime_end": "9999-12-31",
            "include_release_dates_with_no_data": "true", "sort_order": "asc", "limit": 1000,
        })
        if not isinstance(payload, dict):
            continue
        rows.extend(parse_release_dates(payload, key, rid, start, end))
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["fetched"] = t0.strftime("%Y-%m-%d")
    return df


def parse_release_dates(payload: dict, key: str, rid: int, start: str, end: str) -> list[dict]:
    """把 fred/release/dates 的回應攤成列，只留 [start, end] 之間、格式正確的日期。"""
    out = []
    for r in payload.get("release_dates") or []:
        d = str(r.get("date") or "")[:10]
        if len(d) == 10 and start <= d <= end:
            out.append({"date": d, "release": key, "release_id": int(rid)})
    return out
