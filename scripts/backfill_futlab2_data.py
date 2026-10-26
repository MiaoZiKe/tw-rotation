"""回補台指期研究（第二輪）缺的歷史資料：美股／VIX／ADR 日線（2000 起）與期貨三大法人（盡量往前）。

⚠ 本檔在寫它的容器裡**無法執行也未驗證**：該容器對 Yahoo／FinMind／FRED 的出口被代理擋下（HTTP 403）。
請在有網路的環境（例如 GitHub Actions）執行：  python scripts/backfill_futlab2_data.py [--start 2000-01-01]
一律走 store.append()（只增不改、依 key 去重），不覆寫任何 parquet。
"""
from __future__ import annotations

import argparse
import logging

import pandas as pd

from pipeline import config
from pipeline.util import store

log = logging.getLogger("backfill_futlab2")


def us_history(start: str) -> pd.DataFrame:
    import yfinance as yf
    syms = dict(config.INTL_SYMBOLS)
    syms["^TNX"] = "美國10年期公債殖利率"        # 殖利率（Yahoo 的 ^TNX＝殖利率 x10 的百分比報價）
    frames = []
    for sym, label in syms.items():
        try:
            h = yf.Ticker(sym).history(start=start, auto_adjust=False)
        except Exception as exc:                  # noqa: BLE001
            log.warning("%s 抓取失敗：%s", sym, exc)
            continue
        if h is None or h.empty:
            log.warning("%s 回傳空白", sym)
            continue
        h = h.reset_index()
        frames.append(pd.DataFrame({
            "date": pd.to_datetime(h["Date"]).dt.date.astype(str), "symbol": sym, "label": label,
            "open": pd.to_numeric(h.get("Open"), errors="coerce"), "high": pd.to_numeric(h.get("High"), errors="coerce"),
            "low": pd.to_numeric(h.get("Low"), errors="coerce"), "close": pd.to_numeric(h["Close"], errors="coerce"),
            "volume": pd.to_numeric(h.get("Volume"), errors="coerce")}).dropna(subset=["close"]))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def fut_inst_history(start: str) -> dict:
    from pipeline.sources import mktfut
    return mktfut.collect(start, None, wait=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2000-01-01")
    ap.add_argument("--fut-start", default="2008-01-01")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO)
    n = store.append("intl_daily", us_history(a.start))
    log.info("intl_daily 新增 %d 列", n)
    for table, df in fut_inst_history(a.fut_start).items():
        if table in config.TABLES:
            log.info("%s 新增 %d 列", table, store.append(table, df))


if __name__ == "__main__":
    main()
