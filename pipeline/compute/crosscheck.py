"""盤後官方交叉比對（2026-11-06 稽核 C）：資料湖跟官方公開來源對得上嗎？

為什麼要做：資料湖每一層都是「我們自己算完的」，只跟自己比（freshness）抓不到「全部都對但都落後」或「整批寫錯」。
這支另外直接去官方 OpenAPI 抓一次，比三件事：
  1. 最新交易日（上市 STOCK_DAY_ALL、上櫃 tpex_mainboard_daily_close_quotes）跟湖裡一不一樣；
  2. 那一天的檔數跟湖裡一不一樣；
  3. 抽樣 5 檔的收盤價跟湖裡一不一樣。
結果寫進 data/_state/source_health.json 的 `crosscheck` 欄位（跟 data/ 一起 commit）。

判定（verdict）：
  · ok          ：日期相同、檔數差 ≤5%、抽樣收盤價全部相同（±0.01）
  · lake_behind ：湖裡最新日比官方舊（湖落後）
  · lake_ahead  ：湖裡最新日比官方新（通常是 mis 補的暫定值，官方還沒出；只提示，不算錯）
  · mismatch    ：日期相同但檔數或收盤價對不上 —— 這才是要查的
  · unknown     ：官方端點這一輪抓不到（不是湖壞了，不能判定）
失敗（抓不到官方）只標 unknown，不進 errors、不擋其他步驟。
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from .. import config
from ..sources import tpex, twse
from ..util import source_health, store

log = logging.getLogger(__name__)
TAIPEI = timezone(timedelta(hours=8))
SAMPLE_N = 5
ROW_TOL = 0.05        # 檔數差超過 5% 才算對不上（官方端點偶爾少幾檔權證／停牌，不能一檔就亮）
PRICE_TOL = 0.01      # 收盤價容許 0.01 的浮點差


def _summ(df: pd.DataFrame, market: str) -> dict:
    """單一市場的摘要：最新日、那天的檔數、全部收盤價（closes）、抽樣代號（sample）。

    ★ 抽樣由「官方那一邊」決定（呼叫端用 sample 指定），湖這邊一律回全部收盤價再查。
      兩邊各自挑會挑到不同的 5 檔，然後把「沒有可比對的」誤判成不一致。
    """
    if df is None or df.empty or "date" not in df.columns:
        return {"date": None, "rows": 0, "closes": {}, "sample": []}
    d = df[df["market"] == market] if "market" in df.columns else df
    if d.empty:
        return {"date": None, "rows": 0, "closes": {}, "sample": []}
    latest = str(d["date"].astype(str).max())[:10]
    day = d[d["date"].astype(str).str[:10] == latest].dropna(subset=["close"])
    closes = {str(c): float(v) for c, v in zip(day["code"], day["close"])}
    codes = sorted(closes)
    pick = [codes[int(i * (len(codes) - 1) / max(SAMPLE_N - 1, 1))] for i in range(min(SAMPLE_N, len(codes)))] if codes else []
    return {"date": latest, "rows": int(len(day)), "closes": closes, "sample": pick}


def compare(official: dict | None, lake: dict) -> dict:
    """純函式：官方摘要 vs 湖裡摘要 → 判定。official 為 None 代表官方這一輪抓不到。"""
    if not official or not official.get("date"):
        return {"verdict": "unknown", "lake_date": lake.get("date"), "official_date": None,
                "note": "官方端點這一輪抓不到，無法判定（不是湖的問題）"}
    od, ld = official["date"], lake.get("date")
    base = {"official_date": od, "lake_date": ld, "official_rows": official["rows"], "lake_rows": lake.get("rows", 0)}
    if ld is None or ld < od:
        return {**base, "verdict": "lake_behind", "note": f"湖裡最新 {ld or '無'}，官方已到 {od}"}
    if ld > od:
        return {**base, "verdict": "lake_ahead", "note": f"湖裡 {ld} 比官方 {od} 新，通常是盤中暫定值，官方尚未公布"}
    rows_ok = official["rows"] == 0 or abs(lake.get("rows", 0) - official["rows"]) / official["rows"] <= ROW_TOL
    bad = []
    sample = official.get("sample", [])
    for code in sample:
        c = official.get("closes", {}).get(code)
        lc = lake.get("closes", {}).get(code)
        if c is None or lc is None or abs(lc - c) > PRICE_TOL:
            bad.append({"code": code, "official": c, "lake": lc})
    ok = rows_ok and not bad
    return {**base, "verdict": "ok" if ok else "mismatch", "sample_checked": len(sample),
            "sample_mismatch": bad, "rows_ok": rows_ok}


def _lake_by_market(now: datetime) -> pd.DataFrame:
    years = sorted({now.year - 1, now.year})
    return store.read("price_daily", years=years)


def run(now: datetime | None = None, path: Path | None = None) -> dict:
    """抓官方、比湖、寫進 source_health.json 的 crosscheck。任何例外都吞掉並記在結果裡（不擋其他步驟）。"""
    now = now or datetime.now(TAIPEI)
    result: dict = {"at": now.isoformat(timespec="seconds")}
    try:
        lake = _lake_by_market(now)
        out = {}
        for market, fetch in (("TWSE", twse.price_daily), ("TPEX", tpex.price_daily)):
            try:
                # 上櫃日行情常被櫃買端傳一半切斷，3 次不夠（2026-11-06 上櫃 unknown）；退避 1+2+4+8+16 秒
                off_df = fetch(retries=6) if market == "TPEX" else fetch()
                off = _summ(off_df, market) if off_df is not None and not off_df.empty else None
            except Exception as exc:  # noqa: BLE001
                log.warning("官方 %s 抓取失敗：%s", market, exc)
                off = None
            out[market] = compare(off, _summ(lake, market))
        result.update(out)
        result["verdict"] = "mismatch" if any(v["verdict"] == "mismatch" for v in out.values()) else \
            ("lake_behind" if any(v["verdict"] == "lake_behind" for v in out.values()) else
             ("unknown" if all(v["verdict"] == "unknown" for v in out.values()) else "ok"))
    except Exception as exc:  # noqa: BLE001
        log.exception("盤後交叉比對失敗（不擋其他步驟）")
        result["error"] = str(exc)[:300]
        result["verdict"] = "unknown"
    p = path or (config.STATE / "source_health.json")
    h = source_health.load(p)
    h["crosscheck"] = result
    source_health.save(p, h)
    log.info("盤後交叉比對：%s", result.get("verdict"))
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
