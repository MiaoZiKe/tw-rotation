"""ETF 成分股覆蓋率普查：所有上市櫃 ETF（site/data/etf.json）× 資料湖 etf_holdings，依發行投信分組列出缺哪幾檔。

為什麼要這支：Andy 2026-10-07 問「為何有 ETF 沒有成分股，並檢查其他是否一樣問題」。
一次性肉眼對照會過期，所以寫成可重跑的腳本，輸出貼進 docs/etf_holdings_coverage.md。
用法：python scripts/etf_coverage.py [etf.json 路徑]
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from pipeline.sources.etf_pcf import CONNECTED, issuer_of  # noqa: E402

# 槓桿反向／期貨型：資產是期貨契約與現金，沒有「一籃子成分」可列，不算缺漏（前端另有說明）。
NOCOMP = {"槓桿反向"}


def main() -> None:
    p = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "site" / "data" / "etf.json"
    items = json.loads(p.read_text(encoding="utf-8"))["items"]
    try:
        have = set(pd.read_parquet(ROOT / "data" / "etf_holdings")["etf"].astype(str))
    except Exception:  # noqa: BLE001
        have = set()
    tot = collections.Counter()
    miss = collections.defaultdict(list)
    nocomp = 0
    for x in items:
        nm = x["name"]
        iss = issuer_of(nm) or "未辨識"
        if x.get("cat") in NOCOMP or "期" in nm[:6]:
            nocomp += 1
            continue
        tot[iss] += 1
        if x["code"] not in have:
            miss[iss].append(f"{x['code']} {nm}（{x.get('cat') or '—'}）")
    n = sum(tot.values())
    got = n - sum(len(v) for v in miss.values())
    print(f"有成分可列的 ETF：{n} 檔（另 {nocomp} 檔槓桿反向／期貨型不列）；已有成分：{got} 檔（{got / n:.1%}）\n")
    print("| 發行投信 | 已接上 | 檔數 | 缺 | 缺的代號 |\n|---|---|---|---|---|")
    for iss in sorted(tot, key=lambda k: (-len(miss[k]), k)):
        print(f"| {iss} | {'是' if iss in CONNECTED else '否'} | {tot[iss]} | {len(miss[iss])} | {'、'.join(miss[iss]) or '—'} |")


if __name__ == "__main__":
    main()
