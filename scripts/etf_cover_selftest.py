"""ETF 成分股全覆蓋自我測試（只在 Actions 手動跑：probe-etf-pcf.yml mode=cover；不寫資料湖、不 commit）。

為什麼要這支（2026-10-08 第五輪）：Andy 要的是「每一檔都有圖、有清單」，驗收要看**整套來源合起來**之後每一檔的狀態，
不是單看某一家投信抓到幾檔。這支在雲端照正式管線的順序跑一遍：
  ① 各投信官網每日公告（etf_pcf.fetch_all，現抓）＋資料湖裡既有的 etf_holdings（每檔取最近一次）
  ② 投信投顧公會每月前十大（sitca.top10，現抓）
  ③ 人工整理檔（pipeline/etf/holdings_manual.yaml）
→ compute.etf_holdings.build() → 逐檔分類：有表格／沒有表格／槓桿反向期貨型（不適用）。
同時算「修前」：只用資料湖既有 etf_holdings（＝正式站現在看到的），兩個數字一起印。
產出的 etf_holdings.json 寫到 /tmp/etf_holdings.json，工作流會一起推到 probe-log/<run id>，
本機拿去放進 site/data/ 跑 _uitest「ETF成分股全覆蓋1008」（容器連不到投信官網，只能這樣拿真資料）。
"""
from __future__ import annotations

import json
import logging
import re
import sys

import pandas as pd

sys.path.insert(0, ".")
from pipeline.compute import etf_holdings  # noqa: E402
from pipeline.sources import etf_pcf, sitca  # noqa: E402
from pipeline.util import store  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

ci = store.read("company_info")
m = ci["industry"].astype(str).isin(["ETF", "上櫃ETF"])
names = dict(zip(ci.loc[m, "code"].astype(str), ci.loc[m, "name"].astype(str)))
codes = set(names)


def lev(code: str, name: str) -> bool:
    """槓桿／反向／期貨型：前端 tabHoldings 的 noStock 同一條規則（代號尾碼 L R U K、名稱含期貨／正2／反1）。"""
    return bool(re.search(r"[LRUK]$", code)) or bool(re.search(r"期貨|正2|反1", name))


def classify(out: dict) -> tuple[list, list, list]:
    have, miss, na = [], [], []
    for c in sorted(codes):
        n = names[c]
        if lev(c, n):
            na.append(c)
            continue
        rec = (out.get("etfs") or {}).get(c)
        ok = bool(rec and [x for x in rec.get("items", []) if x.get("w")])
        (have if ok else miss).append(c)
    return have, miss, na


price = store.read("price_daily", years=[2026])
lake = store.read("etf_holdings")
before = etf_holdings.build(lake, price, names, codes, manual={}, monthly=None)
h0, m0, na0 = classify(before)
print(f"【修前】只讀資料湖既有 etf_holdings（正式站現況）：有表格 {len(h0)}／沒有 {len(m0)}／不適用（槓桿反向期貨）{len(na0)}／共 {len(codes)}")

fresh = etf_pcf.fetch_all(names)
print(f"官網每日公告現抓：{fresh['etf'].nunique() if len(fresh) else 0} 檔、{len(fresh)} 列")
monthly = sitca.top10(names)
print(f"公會每月前十大現抓：{monthly['fund'].nunique() if len(monthly) else 0} 檔基金、對上代號 {monthly['etf'].nunique() if len(monthly) else 0} 檔")
hold = pd.concat([x for x in (lake, fresh) if x is not None and len(x)], ignore_index=True) if len(fresh) else lake
if len(hold):
    hold = hold.drop_duplicates(subset=["date", "etf", "code"], keep="last")
after = etf_holdings.build(hold, price, names, codes, monthly=monthly)
h1, m1, na1 = classify(after)
kind = {}
for c in h1:
    r = after["etfs"][c]
    k = "人工整理" if r.get("manual") else ("公會月資料" if r.get("monthly") else "投信官網每日")
    kind[k] = kind.get(k, 0) + 1
print(f"【修後】官網每日＋公會月資料＋人工整理：有表格 {len(h1)}／沒有 {len(m1)}／不適用 {len(na1)}／共 {len(codes)}")
print("  有表格的來源分布：", kind)
newly = sorted(set(h1) - set(h0))
print(f"  修前沒有、修後有：{len(newly)} 檔")
for c in newly:
    r = after["etfs"][c]
    print(f"    {c}\t{names[c]}\t{'公會月資料' if r.get('monthly') else ('人工' if r.get('manual') else r.get('issuer', '') + '官網')}\t{r['asof']}\t{len(r['items'])} 檔\t前五：",
          [(x['code'], x['name'], x['w']) for x in r['items'][:5]])
print("  仍然沒有表格（要人工整理或再找來源）：")
for c in m1:
    print(f"    {c}\t{names[c]}\t{etf_pcf.issuer_of(names[c]) or ''}")
for c in ("00918", "009803", "00919", "0056", "00878", "00690", "00905", "009813", "00401A", "009804"):
    r = after["etfs"].get(c)
    if r:
        print(f"  抽查 {c} {names.get(c)}：資料日 {r['asof']}・{'公會月資料' if r.get('monthly') else r.get('issuer', '') + '官網'}・前五：",
              [(x['code'], x['name'], x['w']) for x in r['items'][:5]])
with open("/tmp/etf_holdings.json", "w", encoding="utf-8") as f:
    json.dump(after, f, ensure_ascii=False)
print("已寫 /tmp/etf_holdings.json")
