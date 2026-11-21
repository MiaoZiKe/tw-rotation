"""產生示範資料，讓 dashboard 在第一次真實抓取之前就能打開來看。

資料是合成的，不是真實行情 —— meta.json 會標記 demo:true，
頁面上會出現明顯的警示條。第一次跑 run_daily 之後就會被真實資料覆蓋。

用法：python -m scripts.make_demo
"""
from __future__ import annotations

import json
import logging
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("demo")


def main() -> int:
    from pipeline import config
    from pipeline.groups import loader

    # 把資料湖導到暫存目錄，絕不碰到真實的 data/
    tmp = Path(tempfile.mkdtemp(prefix="twdemo-"))
    (tmp / "_state").mkdir(parents=True)
    config.DATA = tmp
    config.STATE = tmp / "_state"

    from pipeline.util import store
    store.config.DATA = tmp

    m = loader.membership()
    codes = m["code"].drop_duplicates().tolist()
    rng = np.random.default_rng(20260910)
    days = 420
    # 讓示範資料的最後一天落在今天，避免頁面誤判成「排程已失效」
    dates = (pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=days)
               .strftime("%Y-%m-%d").tolist())

    tier_drift = {"upstream": 0.0016, "midstream": 0.0012,
                  "downstream": 0.0008, "standalone": -0.0002}
    code_tier = dict(zip(m["code"], m["tier"]))

    price, inst, margin, val = [], [], [], []
    for idx, code in enumerate(codes):
        drift = tier_drift.get(code_tier.get(code, "standalone"), 0.0)
        drift += rng.normal(0, 0.0008)
        steps = rng.normal(drift, 0.016, days)
        close = float(rng.uniform(25, 900)) * np.exp(np.cumsum(steps))
        prev = np.concatenate([[close[0]], close[:-1]])
        high = close * (1 + np.abs(rng.normal(0, 0.009, days)))
        low = close * (1 - np.abs(rng.normal(0, 0.009, days)))
        scale = float(rng.uniform(0.2, 6.0))
        vol = (rng.integers(3_000_000, 60_000_000, days) * scale).astype(int)

        for j, d in enumerate(dates):
            price.append({
                "date": d, "code": code, "name": f"示範{code}", "market": "DEMO",
                "open": float(prev[j]), "high": float(max(high[j], close[j], prev[j])),
                "low": float(min(low[j], close[j], prev[j])), "close": float(close[j]),
                "change": float(close[j] - prev[j]), "volume": int(vol[j]),
                "turnover": float(vol[j] * close[j]),
                "transactions": int(vol[j] / 1200),
            })
            if j >= days - 30:      # 法人只造最近 30 天，省檔案大小
                trust = float(rng.normal(4e5 if drift > 0.001 else -3e5, 9e5))
                inst.append({
                    "date": d, "code": code,
                    "foreign": float(rng.normal(drift * 2e9, 4e6)),
                    "foreign_dealer": 0.0,
                    "foreign_total": float(rng.normal(drift * 2e9, 4e6)),
                    "trust": trust, "dealer_self": 0.0, "dealer_hedge": 0.0,
                    "dealer": float(rng.normal(0, 6e5)),
                    "inst_total": float(rng.normal(drift * 2e9, 5e6)),
                })
                margin.append({
                    "date": d, "code": code,
                    "margin_balance": int(rng.integers(2000, 60000)),
                    "margin_change": int(rng.integers(-3000, 3000)),
                    "short_balance": int(rng.integers(0, 6000)),
                    "short_change": int(rng.integers(-600, 600)),
                })

        val.append({"date": dates[-1], "code": code,
                    "pe": float(rng.uniform(7, 45)), "pb": float(rng.uniform(0.7, 7)),
                    "dividend_yield": float(rng.uniform(0.3, 7))})

    taiex = 22000 * np.exp(np.cumsum(rng.normal(0.0005, 0.011, days)))
    market = [{"date": d, "volume": int(rng.integers(4e9, 9e9)),
               "turnover": float(rng.uniform(3.0e11, 6.5e11)),
               "transactions": int(rng.integers(1e6, 3e6)),
               "taiex": float(taiex[j]),
               "change": float(taiex[j] - (taiex[j - 1] if j else taiex[0]))}
              for j, d in enumerate(dates)]

    company = [{"code": c, "name": f"示範{c}", "market": "DEMO",
                "industry": "示範產業", "industry_code": "00"} for c in codes]

    store.append("price_daily", pd.DataFrame(price))
    store.append("inst_daily", pd.DataFrame(inst))
    store.append("margin_daily", pd.DataFrame(margin))
    store.append("valuation_daily", pd.DataFrame(val))
    store.append("market_daily", pd.DataFrame(market))
    store.append("company_info", pd.DataFrame(company))
    store.append("news", pd.DataFrame([{
        "news_id": f"demo-{i}", "source": "demo", "date": dates[-1],
        "published_at": f"{dates[-1]}T1{i%9}:00:00+00:00",
        "title": t, "summary": "", "url": "#",
        "codes": c, "keywords": k,
    } for i, (t, c, k) in enumerate([
        ("（示範資料）先進封裝產能傳將再擴，供應鏈同步受惠", "2330,3374", "CoWoS,先進封裝"),
        ("（示範資料）AI 伺服器液冷滲透率上修，散熱族群動能延續", "3017,3324", "液冷,AI伺服器"),
        ("（示範資料）記憶體合約價續漲，模組廠庫存效益浮現", "2408,3006", "記憶體,DRAM"),
        ("（示範資料）美系外資調升晶圓代工目標價", "2330", "外資,晶圓代工"),
        ("（示範資料）航運運價指數連續第三週回落", "2603,2609", "航運,運價"),
    ])]))

    from pipeline import build_payload
    build_payload.build()

    # 標記為示範資料，讓前端顯示警示
    meta_path = config.SITE_DATA / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["demo"] = True
    meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    shutil.rmtree(tmp, ignore_errors=True)
    total = sum(f.stat().st_size for f in config.SITE_DATA.glob("*.json"))
    log.info("示範資料已產生於 %s（共 %.0f KB）", config.SITE_DATA, total / 1024)
    log.info("真實資料抓進來之後，跑 run_daily 就會全部覆蓋。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
