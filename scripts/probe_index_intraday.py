"""大盤三張圖的歷史分 K／分鐘量候選來源探測（2026-09-28，Andy「櫃買 1H/4H 看不到之前的 K 棒、加權分 K 沒有量」）。

為什麼要探測：Claude 的容器連不到 FinMind／Yahoo，欄位名、會員等級擋不擋、一天幾筆，
只能在 Actions 上真的打一次才知道。規矩是「沒有 fixture 不寫 parser」。

候選（全部是既有白名單來源）：
  · FinMind TaiwanStockEvery5SecondsIndex   每 5 秒指數統計（上市＋上櫃，含櫃買指數）→ 櫃買歷史分 K
  · FinMind TaiwanVariousIndicators5Seconds  加權指數每 5 秒                               → 加權真實高低
  · FinMind TaiwanStockStatisticsOfOrderBookAndTrade 每 5 秒委託成交統計（累計成交量／金額） → 加權分鐘真實量
  · Yahoo IX0043.TWO（Yahoo 股市上櫃指數的代號）60m／15m／1d                            → 櫃買歷史分 K 備案

結果寫 docs/fixtures/index_intraday_probe.json：狀態、欄位、筆數、前後幾筆樣本、各名稱的出現次數。
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import config  # noqa: E402
from pipeline.util import http  # noqa: E402

OUT = ROOT / "docs" / "fixtures" / "index_intraday_probe.json"
DAY = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] != "sample" else "2026-09-24"
OLD_DAY = "2024-09-24"     # 兩年前那天拿不拿得到（決定能回補多長）


def fm(dataset: str, day: str, data_id: str | None = None) -> dict:
    rec: dict = {"dataset": dataset, "day": day, "data_id": data_id}
    try:
        data = http.finmind_get(dataset, data_id=data_id, start_date=day, end_date=day)
        err = http.finmind_last_error()
        rec["error"] = err
        if not data:
            rec["n"] = 0
            return rec
        rec["n"] = len(data)
        rec["columns"] = sorted({k for r in data[:50] for k in r})
        rec["head"] = data[:5]
        rec["tail"] = data[-5:]
        # 名稱類欄位的出現次數（看櫃買指數叫什麼、一天幾筆）
        for key in ("stock_id", "index_name", "name", "data_id", "type"):
            if key in data[0]:
                cnt: dict = {}
                for r in data:
                    cnt[str(r.get(key))] = cnt.get(str(r.get(key)), 0) + 1
                rec[f"count_by_{key}"] = dict(sorted(cnt.items(), key=lambda kv: -kv[1])[:80])
        # 找「櫃買」相關的樣本
        hits = [r for r in data if any("櫃" in str(v) or "TPEx" in str(v) or "OTC" in str(v).upper()
                                      for v in r.values())]
        rec["otc_hits_n"] = len(hits)
        rec["otc_hits_head"] = hits[:5]
        rec["otc_hits_tail"] = hits[-3:]
    except Exception as exc:  # noqa: BLE001
        rec["exception"] = f"{exc}\n{traceback.format_exc()[-800:]}"
    return rec


def yh(sym: str, interval: str, period: str) -> dict:
    rec: dict = {"symbol": sym, "interval": interval, "period": period}
    try:
        import yfinance as yf
        raw = yf.download(sym, interval=interval, period=period, auto_adjust=False,
                          progress=False, threads=False)
        rec["n"] = int(len(raw))
        if len(raw):
            if hasattr(raw.columns, "levels"):
                raw.columns = [c[0] if isinstance(c, tuple) else c for c in raw.columns]
            rec["first"] = str(raw.index[0])
            rec["last"] = str(raw.index[-1])
            rec["days"] = int(len({str(i)[:10] for i in raw.index}))
            if "Volume" in raw:
                rec["vol_pos_ratio"] = float((raw["Volume"] > 0).mean())
            rec["tail"] = json.loads(raw.tail(4).reset_index().to_json(orient="records", date_format="iso"))
    except Exception as exc:  # noqa: BLE001
        rec["exception"] = f"{exc}"
    return rec


def sample() -> None:
    """用**正式程式碼**（改好的 yahoo.index_intraday 與 finmind.tse_minute_bars）真的抓一輪，存成 fixture，
    讓容器裡能用真資料重算 payload、跑前端驗收（容器連不到 Yahoo／FinMind）。"""
    import pandas as pd
    from pipeline.sources import finmind, yahoo
    from pipeline.util import store
    parts = [yahoo.index_intraday("60m", "730d"), yahoo.index_intraday("15m", "60d")]
    ohlc = store.read("index_ohlc")
    tse = ohlc[ohlc["symbol"].astype(str) == "TSE"].sort_values("date")
    days = [str(d)[:10] for d in tse["date"].tail(12)]
    report = {"yahoo": {}, "finmind": {}}
    for p_ in parts:
        if not p_.empty:
            for (sym, iv), g in p_.groupby(["symbol", "interval"]):
                report["yahoo"][f"{sym}|{iv}"] = {"n": int(len(g)), "first": str(g["ts"].min()),
                                                  "last": str(g["ts"].max())}
    for d in days:
        f = finmind.tse_minute_bars(d)
        row = tse[tse["date"].astype(str).str[:10] == d]
        official = float(row["turnover"].iloc[0]) if len(row) else None
        report["finmind"][d] = {"n": int(len(f)), "money_yuan": float(f["volume"].sum() * 1000) if len(f) else 0.0,
                                "official_turnover": official}
        if not f.empty:
            parts.append(f)
    df = pd.concat([p_ for p_ in parts if not p_.empty], ignore_index=True)
    src = df["src"].astype(str) if "src" in df.columns else pd.Series("", index=df.index)
    df = df[(df["symbol"].astype(str) == "OTC") | (src == "finmind")]   # 加權 Yahoo 湖裡本來就有，不重存
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(ROOT / "docs" / "fixtures" / "index_intraday_sample.parquet", index=False)
    (ROOT / "docs" / "fixtures" / "index_intraday_sample_probe.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False)[:4000])


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "sample":
        sample()
        return
    out: dict = {"token_set": bool(config.FINMIND_TOKEN), "day": DAY, "finmind": [], "yahoo": []}
    for ds in ("TaiwanStockEvery5SecondsIndex", "TaiwanVariousIndicators5Seconds",
               "TaiwanStockStatisticsOfOrderBookAndTrade"):
        out["finmind"].append(fm(ds, DAY))
        out["finmind"].append(fm(ds, OLD_DAY))
    for sym in ("IX0043.TWO", "^TWOII", "^TWII"):
        for iv, pd_ in (("60m", "730d"), ("15m", "60d"), ("1d", "1mo")):
            out["yahoo"].append(yh(sym, iv, pd_))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, default=str)[:6000])


if __name__ == "__main__":
    main()
