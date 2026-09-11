"""Yahoo Finance 分 K（yfinance，免 key）。

用途是個股頁的 60 分 / 15 分 K 線。Yahoo 對台股的分 K 只保留有限天數
（60m 約兩年、15m 約 60 天），而且是「快照」性質 —— 這層資料**不進資料湖**，
build_payload 每天直接抓、直接用，所以不用在 config.TABLES 註冊。

Yahoo 沒有正式 API，yfinance 走的是網頁端點，隨時可能改版或限流：
所有失敗只記 log，回已經成功的那部分，絕不讓整個 build 死掉。
"""
from __future__ import annotations

import logging
import time

import pandas as pd

log = logging.getLogger(__name__)

TAIPEI_TZ = "Asia/Taipei"
BATCH_PAUSE = 1.0        # 批與批之間停一下，避免被 Yahoo 當成攻擊

# yfinance 欄位名 → 我們的欄位名
_FIELDS = {"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}


def symbol_of(code: str, markets: dict[str, str]) -> str:
    """台股代號轉 Yahoo 符號：上櫃 .TWO、其餘（上市 / 不知道）.TW。"""
    return f"{code}.TWO" if markets.get(code) == "TPEX" else f"{code}.TW"


def _to_taipei_iso(index: pd.Index) -> list[str]:
    """把 yfinance 的時間索引轉成台北時間的 ISO 字串（帶 +08:00）。

    yfinance 的分 K 索引通常已帶交易所時區；若拿到 naive 時間，視為台北時間。
    """
    idx = pd.DatetimeIndex(index)
    if idx.tz is None:
        idx = idx.tz_localize(TAIPEI_TZ)
    else:
        idx = idx.tz_convert(TAIPEI_TZ)
    return [t.isoformat() for t in idx]


def _frame_to_long(frame: pd.DataFrame, code: str) -> pd.DataFrame:
    """單一代號的單層欄位（Open/High/Low/Close/Volume）→ 長格式。"""
    if frame is None or frame.empty:
        return pd.DataFrame()
    cols = {}
    for src, dst in _FIELDS.items():
        if src in frame.columns:
            cols[dst] = pd.to_numeric(frame[src], errors="coerce").to_numpy()
        else:
            cols[dst] = float("nan")
    out = pd.DataFrame({"ts": _to_taipei_iso(frame.index), "code": code, **cols})
    return out.dropna(subset=["close"]).reset_index(drop=True)


def _split_by_ticker(raw: pd.DataFrame, symbols: dict[str, str]) -> list[pd.DataFrame]:
    """把 yfinance.download 的回傳拆成每檔一張單層表。

    多代號時是 MultiIndex（ticker, field）；單一代號時 yfinance 回單層欄位。
    有些版本會把 ticker 放在第二層，所以兩層都找。
    """
    frames: list[pd.DataFrame] = []
    if raw is None or raw.empty:
        return frames

    if isinstance(raw.columns, pd.MultiIndex):
        lvl0 = set(raw.columns.get_level_values(0))
        lvl1 = set(raw.columns.get_level_values(1))
        for sym, code in symbols.items():
            if sym in lvl0:
                sub = raw[sym]
            elif sym in lvl1:
                sub = raw.xs(sym, axis=1, level=1)
            else:
                continue
            frames.append(_frame_to_long(sub, code))
        return frames

    # 單層欄位：只可能是「這批只有一檔」的情況
    if len(symbols) == 1:
        (code,) = symbols.values()
        frames.append(_frame_to_long(raw, code))
    else:
        log.warning("yfinance 回單層欄位但這批有 %d 檔，無法對應代號，略過", len(symbols))
    return frames


def intraday(codes: list[str], markets: dict[str, str], interval: str, period: str,
             batch: int = 40) -> pd.DataFrame:
    """分 K 長格式：ts（台北時間 ISO 字串）, code, open, high, low, close, volume。

    interval 支援 "60m" / "15m"，period 對應 "730d" / "60d"（Yahoo 的保留上限）。
    分批下載（每批 batch 檔），批間 sleep；任何例外只 log，回已成功的部分。
    """
    codes = [str(c).strip() for c in codes if str(c).strip()]
    if not codes:
        return pd.DataFrame()
    try:
        import yfinance as yf
    except ImportError:
        log.warning("未安裝 yfinance，跳過分 K")
        return pd.DataFrame()

    seen: set[str] = set()
    ordered = [c for c in codes if not (c in seen or seen.add(c))]
    frames: list[pd.DataFrame] = []
    batches = [ordered[i:i + batch] for i in range(0, len(ordered), max(1, int(batch)))]

    for n, chunk in enumerate(batches, 1):
        symbols = {symbol_of(c, markets): c for c in chunk}
        try:
            raw = yf.download(list(symbols), interval=interval, period=period,
                              group_by="ticker", auto_adjust=False,
                              progress=False, threads=True)
            frames.extend(f for f in _split_by_ticker(raw, symbols) if not f.empty)
        except Exception as exc:  # noqa: BLE001 —— Yahoo 隨時會掛，這層不能拋
            log.warning("yfinance 分 K 第 %d/%d 批失敗（%s %s）：%s",
                        n, len(batches), interval, period, exc)
        if n < len(batches):
            time.sleep(BATCH_PAUSE)

    if not frames:
        log.warning("yfinance 分 K %s/%s 一筆都沒拿到（%d 檔）", interval, period, len(ordered))
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df = df[["ts", "code", "open", "high", "low", "close", "volume"]]
    log.info("yfinance 分 K %s/%s：%d 列 / %d 檔", interval, period, len(df), df["code"].nunique())
    return df.sort_values(["code", "ts"], kind="stable").reset_index(drop=True)
