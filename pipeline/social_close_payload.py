"""盤後貼文要的那幾份 JSON（只算這幾份，不重算整站）。

2026-10-27 Andy：「馬上拆開，盤後貼文資料到就發」「為何要那麼久」。
事故：16:17 法人就進湖了，但盤後貼文要等 build_payload 整站重算（約 20 分鐘）＋ Pages 部署排隊，17 點後才發。
現在 daily.yml 的 inst 輪：抓完就 commit 資料湖 → 立刻派 social-live（kind=close），social-live 用這支從湖裡
直接算出下面幾份（幾十秒），蓋在從正式站下載的網站資料上，資料齊了就發；整站重算與部署在 daily.yml 裡接著跑，互不等待。
口徑與 build_payload.build() 的同名檔案完全相同（直接呼叫同一批函式），改那邊記得這裡不用改。

用法：python -m pipeline.social_close_payload <輸出資料夾>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .build_payload import _clean, last_complete_date
from .compute import flow, inst_market, inst_today
from .compute import mktfut as mktfut_c
from .groups import loader
from .util import store


def build(out: Path) -> list[str]:
    out.mkdir(parents=True, exist_ok=True)
    wrote: list[str] = []

    def w(name, payload):
        (out / f"{name}.json").write_text(json.dumps(_clean(payload), ensure_ascii=False), encoding="utf-8")
        wrote.append(name)

    price = store.read("price_daily")
    if price.empty:
        return wrote
    company = store.read("company_info")
    inst = store.read("inst_daily")
    margin = store.read("margin_daily")
    names = {}
    if not company.empty and "name" in company.columns:
        names = company.dropna(subset=["name"]).drop_duplicates("code", keep="last").set_index("code")["name"].to_dict()
    latest = last_complete_date(price)
    price = price[price["date"].astype(str) <= latest]
    inst, margin = (t[t["date"].astype(str) <= latest] if not t.empty and "date" in t else t for t in (inst, margin))

    streaks = {}
    for who in ("trust", "foreign", "total"):
        df_s = flow.trust_streak(inst, min_days=2, who=who)
        streaks[who] = [] if df_s.empty else _clean(df_s.head(60).to_dict("records"))
        df_x = flow.trust_streak(inst, min_days=2, who=who, side="sell")
        streaks[who + "_sell"] = [] if df_x.empty else _clean(df_x.head(60).to_dict("records"))
    w("trust_streak", streaks.get("trust", []))
    w("inst_streak", streaks)

    ohlc = store.read("index_ohlc")
    fi, oi = store.read("fut_inst"), store.read("fut_oi")
    w("market_fut", mktfut_c.build(store.read("margin_total"), margin, company, price, ohlc, loader.membership()))
    w("fut_oi", mktfut_c.fut_oi_json(fi, ohlc, "期交所三大法人區分各期貨契約（經 FinMind TaiwanFuturesInstitutionalInvestors），臺股期貨 TX，所有到期月份合計"))
    w("retail_ratio", mktfut_c.retail_ratio_json(fi, oi, ohlc, "期交所三大法人未平倉＋期貨每日行情未平倉（經 FinMind），大台 TX／小台 MTX／微台 TMF，所有到期月份合計"))

    it = inst_today.payload(inst, price, names)
    it["latest"] = latest
    w("inst_today", it)
    im = inst_market.series(store.read("inst_market_daily"), inst, price, ohlc,
                            first=inst_market.with_seed(store.read("inst_market_first")))
    im["latest"] = latest
    w("inst_market", im)
    return wrote


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("用法：python -m pipeline.social_close_payload <輸出資料夾>")
    print("寫出：", "、".join(build(Path(sys.argv[1]))))
