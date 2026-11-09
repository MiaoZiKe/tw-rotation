"""補抓某一天的 ETF 申購買回清單（etf_holdings）。

為什麼：2026-11-06 的 full 輪被 pytest 擋下，etf_holdings 只存到 84/235 檔。
各投信的 PCF 端點大多有日期參數（不過富邦、永豐、元大、玉山、安聯、聯博沒有），帶日期補抓；
基準日以回應內容為準（etf_pcf.fetch_all 最後只留基準日＝目標日的列），寫入走 store.append（只增不改、鍵重複後到為準）。
用法：python -m pipeline.etf_pcf_fill 2026-11-06
"""
from __future__ import annotations

import logging
import sys

from .sources import etf_pcf
from .util import store

log = logging.getLogger("etf_pcf_fill")


def main(date: str) -> int:
    ci = store.read("company_info")
    e = ci[ci["industry"].astype(str).isin(["ETF", "上櫃ETF"])]
    names = dict(zip(e["code"].astype(str), e["name"].astype(str)))
    old = store.read("etf_holdings")
    had = set(old.loc[old["date"].astype(str) == date, "etf"]) if len(old) else set()
    df = etf_pcf.fetch_all(names, date)
    print(f"目標日 {date}：湖裡原有 {len(had)} 檔；這次抓到 {df['etf'].nunique() if len(df) else 0} 檔、{len(df)} 列")
    if len(df):
        new_etfs = sorted(set(df["etf"]) - had)
        n = store.append("etf_holdings", df)
        print(f"新增 {n} 列；新補的 ETF {len(new_etfs)} 檔")
        for iss, g in df.groupby("issuer"):
            print(f"  {iss}: {g['etf'].nunique()} 檔 {len(g)} 列（其中新補 {g[g['etf'].isin(new_etfs)]['etf'].nunique()} 檔）")
    after = store.read("etf_holdings")
    sub = after[after["date"].astype(str) == date]
    miss = sorted(set(names) - set(sub["etf"]) - {c for c in names if etf_pcf._skip_code(c)})
    print(f"補完後 {date} 共 {sub['etf'].nunique()} 檔；清單內仍沒有的 {len(miss)} 檔：{miss[:80]}")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    sys.exit(main(sys.argv[1]))
