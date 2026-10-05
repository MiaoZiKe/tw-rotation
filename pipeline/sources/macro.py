"""國際連動與總經。

國際指數走 yfinance（免 key），總經走 FRED REST API（免費，需註冊 key）。
刻意不用 fredapi 套件 —— 它自 2024 起停止維護，直接打 REST 更可靠。
"""
from __future__ import annotations

import json
import logging
import re

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


# ---------------------------------------------------------------- FRED
#
# 為什麼要把錯誤原因帶出來（2026-10-06）：
#   macro.fred 從 2026-09 起每一輪都是 ok=False rows=0，last_run.json 卻只寫「沒回資料」——
#   是沒金鑰、金鑰失效、金鑰格式壞掉、還是參數錯，從儀表板上完全分不出來，
#   而 Actions 日誌又長到 API 只拿得到最後 5,000 行，抓取那段根本看不到。
#   所以失敗原因改成掛在回傳 DataFrame 的 attrs["error"] 上，由 run_daily.step() 寫進
#   last_run.json 的 steps.<名稱>.error。函式本身照舊「失敗回空、不拋例外」。
#   ★ last_run.json 會 commit 進 public repo：寫進去之前一律經過 _redact()，金鑰一個字都不能出現。

_KEY_PARAM = re.compile(r"(api_key=)[^&\s\"']+", re.I)


def _redact(text) -> str:
    """把金鑰從錯誤字串裡抹掉（FRED 目前不會回顯金鑰，但連線例外的訊息會帶完整網址）。"""
    s = str(text or "")
    if config.FRED_KEY:
        s = s.replace(config.FRED_KEY, "***")
    return _KEY_PARAM.sub(r"\1***", s)


def key_problem(key: str | None = None) -> str:
    """金鑰格式自檢：FRED 金鑰是 32 個小寫英數字。只回描述（長度、哪一類字元不對），不回金鑰本身。

    用途是讓 last_run.json 一眼分出「貼壞了（長度不對、含空白）」和「格式對但沒註冊／被停用」，
    這兩種的修法不同：前者重貼，後者要到 FRED 重新申請。"""
    k = config.FRED_KEY if key is None else key
    if not k:
        return "未設定"
    probs = []
    if len(k) != 32:
        probs.append(f"長度 {len(k)}（應為 32）")
    if any(c.isupper() for c in k):
        probs.append("含大寫字母")
    n_bad = sum(1 for c in k if not (c.isascii() and c.isalnum()))
    if n_bad:
        probs.append(f"含 {n_bad} 個非英數字元")
    return "、".join(probs)


def _with_error(df: pd.DataFrame, err: str) -> pd.DataFrame:
    if err:
        df.attrs["error"] = _redact(err)[:500]
    return df


def _fred_get(url: str, params: dict) -> tuple[dict | None, str]:
    """打一次 FRED，回 (payload, 錯誤原因)。成功時錯誤原因是空字串。

    error_body=True：不重試的 4xx 會拿到 FRED 自己的錯誤 JSON
    （{"error_code":400,"error_message":"Bad Request. The value for variable api_key is not registered..."}），
    不再只是一個 None。"""
    payload = http.get(url, params={**params, "api_key": config.FRED_KEY, "file_type": "json"},
                       error_body=True)
    if payload is None:
        return None, "連線失敗、或重試後仍是 429／5xx（細節見 Actions 日誌）"
    if not isinstance(payload, dict):
        return None, _redact(f"回應不是 JSON 物件（前 200 字）：{str(payload)[:200]}")
    if "error_code" in payload or "error_message" in payload or "status" in payload:
        code = payload.get("error_code") or payload.get("status") or "?"
        msg = payload.get("error_message") or payload.get("msg") or ""
        return None, _redact(f"HTTP {code}：{' '.join(str(msg).split())}")[:300]
    return payload, ""


def _summarize(fails: dict[str, list[str]], total: int, what: str) -> str:
    """把「哪幾個失敗、為什麼」縮成一行；同一個原因只寫一次（金鑰錯的時候 12 檔原因都一樣）。"""
    if not fails:
        return ""
    n = sum(len(v) for v in fails.values())
    parts = []
    for reason, names in fails.items():
        shown = "、".join(names[:4]) + ("…" if len(names) > 4 else "")
        parts.append(f"{reason}（{shown}）")
    msg = f"{what} {n}/{total} 個失敗：" + "；".join(parts)
    kp = key_problem()
    if kp and any("api_key" in r or "HTTP 400" in r or "HTTP 401" in r or "HTTP 403" in r for r in fails):
        msg += f"｜金鑰自檢：{kp}"
    return msg


def fred_series(series_id: str, start: str = "2015-01-01") -> pd.DataFrame:
    if not config.FRED_KEY:
        log.info("未設定 FRED_API_KEY，跳過 %s", series_id)
        return _with_error(pd.DataFrame(), "未設定 FRED_API_KEY")

    payload, err = _fred_get(config.FRED_API, {"series_id": series_id, "observation_start": start})
    if err:
        log.warning("FRED %s 失敗：%s", series_id, err)
        return _with_error(pd.DataFrame(), err)
    if not isinstance(payload.get("observations"), list):
        # 上游改格式時要把實際回應印出來，下一個人才有辦法修
        head = _redact(json.dumps(payload, ensure_ascii=False)[:200])
        log.warning("FRED %s 回應沒有 observations（前 200 字）：%s", series_id, head)
        return _with_error(pd.DataFrame(), f"回應沒有 observations（前 200 字）：{head}")
    rows = []
    for o in payload["observations"]:
        v = o.get("value")
        if v in (".", "", None):        # FRED 用 "." 表示該期無值
            continue
        try:
            rows.append({"date": o["date"], "series": series_id,
                         "label": config.FRED_SERIES.get(series_id, series_id),
                         "value": float(v)})
        except (KeyError, TypeError, ValueError):
            continue
    if not rows:
        return _with_error(pd.DataFrame(), "observations 是空的")
    return pd.DataFrame(rows)


def macro_all(start: str = "2015-01-01") -> pd.DataFrame:
    """config.FRED_SERIES 全部抓一輪；任何一檔失敗，原因寫在回傳值的 attrs["error"]。"""
    if not config.FRED_KEY:
        log.warning("未設定 FRED_API_KEY（GitHub Secrets 沒有這個值，或工作流沒有傳進 env），跳過 FRED 總經")
        return _with_error(pd.DataFrame(),
                           "未設定 FRED_API_KEY（GitHub Secrets 沒有這個值，或工作流沒有傳進 env）")
    frames, fails = [], {}
    for s in config.FRED_SERIES:
        f = fred_series(s, start)
        if f.empty:
            fails.setdefault(f.attrs.get("error") or "回 0 筆", []).append(s)
        else:
            frames.append(f)
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if frames:
        log.info("FRED 總經：%d 列 / %d 檔", len(df), len(frames))
    return _with_error(df, _summarize(fails, len(config.FRED_SERIES), "FRED 序列"))


def release_calendar(days_back: int = 120, days_ahead: int = 240,
                     today: str | None = None) -> pd.DataFrame:
    """FRED 各統計發布的公布日程（財報日曆的「FED 與美國重大數據」用）。

    端點：fred/release/dates?release_id=<id>&include_release_dates_with_no_data=true ——
    帶上 include_release_dates_with_no_data 才會列出**還沒公布**的未來日期（不帶只回已經有資料的過去日期）。
    release_id 見 config.FRED_RELEASES（CPI 10、非農 50、GDP 53、PCE 54）。

    回傳欄位：date（公布日，美東）, release（cpi/nfp/gdp/pce）, release_id, fetched（抓取日，UTC）。
    沒有金鑰、端點失敗一律回空 DataFrame（原因在 attrs["error"]）—— 財報日曆會退回 YAML 的日程
    （pipeline/calendar/macro_events.yaml），不讓管線掛掉。
    today 只給測試用；正式執行取 UTC 今天（這裡不是交易日，是「抓取當下」的時間戳，不違反 CLAUDE.md 第 3 條）。
    """
    if not config.FRED_KEY:
        log.info("未設定 FRED_API_KEY，跳過 FRED 公布日程")
        return _with_error(pd.DataFrame(),
                           "未設定 FRED_API_KEY（GitHub Secrets 沒有這個值，或工作流沒有傳進 env）")
    t0 = pd.Timestamp(today) if today else pd.Timestamp.now("UTC").tz_localize(None).normalize()
    start = (t0 - pd.Timedelta(days=days_back)).strftime("%Y-%m-%d")
    end = (t0 + pd.Timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    rows, fails = [], {}
    for rid, key in config.FRED_RELEASES.items():
        payload, err = _fred_get(config.FRED_RELEASE_DATES_API, {
            "release_id": rid,
            "realtime_start": start, "realtime_end": "9999-12-31",
            "include_release_dates_with_no_data": "true", "sort_order": "asc", "limit": 1000,
        })
        if err:
            log.warning("FRED 公布日程 %s（release_id=%s）失敗：%s", key, rid, err)
            fails.setdefault(err, []).append(key)
            continue
        if not isinstance(payload.get("release_dates"), list):
            head = _redact(json.dumps(payload, ensure_ascii=False)[:200])
            log.warning("FRED 公布日程 %s 回應沒有 release_dates（前 200 字）：%s", key, head)
            fails.setdefault(f"回應沒有 release_dates（前 200 字）：{head}", []).append(key)
            continue
        got = parse_release_dates(payload, key, rid, start, end)
        if not got:
            fails.setdefault(f"{start}～{end} 之間 0 筆", []).append(key)
        rows.extend(got)
    err = _summarize(fails, len(config.FRED_RELEASES), "FRED 公布日程")
    if not rows:
        return _with_error(pd.DataFrame(), err)
    df = pd.DataFrame(rows)
    df["fetched"] = t0.strftime("%Y-%m-%d")
    return _with_error(df, err)


def parse_release_dates(payload: dict, key: str, rid: int, start: str, end: str) -> list[dict]:
    """把 fred/release/dates 的回應攤成列，只留 [start, end] 之間、格式正確的日期。"""
    out = []
    for r in payload.get("release_dates") or []:
        d = str(r.get("date") or "")[:10]
        if len(d) == 10 and start <= d <= end:
            out.append({"date": d, "release": key, "release_id": int(rid)})
    return out
