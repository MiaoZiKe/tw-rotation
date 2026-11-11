"""抓非主管薪資 -> 進資料湖（append-only）-> 輸出排序 csv。由 nonmgr_salary.yml 手動觸發。"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline.sources import nonmgr_salary as ns  # noqa: E402
from pipeline.util import store  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
OUT = ROOT / "docs/marketing/channels/tc/data/nonmgr_salary_2025.csv"
YEAR = 2025


def main() -> int:
    df = pd.concat([ns.nonmgr_salary_twse(), ns.nonmgr_salary_tpex()], ignore_index=True)
    probe = {"rows": int(len(df)), "by_market_year": df.groupby(["market", "year"]).size().reset_index(name="n").to_dict("records") if len(df) else []}
    (ROOT / "docs/fixtures/nonmgr_salary_probe.json").write_text(json.dumps(probe, ensure_ascii=False, indent=1), encoding="utf-8")
    if df.empty:
        print("沒有抓到任何資料，詳見 log")
        return 0
    n = store.append("nonmgr_salary", df)
    print(f"資料湖新增 {n} 列")
    d = df[df["year"] == YEAR].copy()
    if d.empty:
        print(f"沒有 {YEAR} 年度資料，現有年度：{sorted(df['year'].unique())}")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    d["平均"] = (d["avg_k"] / 10).round(1)      # 仟元 -> 萬元
    d["中位數"] = (d["median_k"] / 10).round(1)
    out = d.rename(columns={"market": "市場", "code": "代號", "name": "公司", "headcount": "人數",
                            "year": "資料年度", "source": "來源端點", "total_k": "薪資總額(仟元)"})
    out = out.sort_values(["市場", "平均"], ascending=[False, False])  # 上櫃、上市各自依平均降序
    cols = ["市場", "代號", "公司", "平均", "中位數", "人數", "薪資總額(仟元)", "資料年度", "來源端點"]
    out[cols].to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"csv {len(out)} 列 -> {OUT}（平均、中位數單位：萬元）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
