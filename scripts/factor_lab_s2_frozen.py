"""S2 凍結規則在 2013-02～2016-12 新資料（營收／財報 2012 回補完成後）上只跑一次。

凍結的兩個版本（規則寫死，不得因結果修改）：
  S2   前 10 檔、近 3 月均營收/近 12 月均營收>1、站上 20/60/120 日線、營收法定公告日（10 日）收盤後選、隔日開盤成交
  S2-R 同上，加單一產業最多 2 檔（只用 2016-12～2018 設計）
每個版本每池只跑一次（holdout_log.csv：重跑只讀紀錄）。同時報出覆蓋率：池內有營收資料的比例，避免把「空手」當成結果。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from pipeline.compute import factor_lab as F  # noqa: E402

SPECS = {
    "S2": dict(comps=("rv312",), N=10, rebal="R", mf=None, gt={"rv312": 1.0}, ge={"ma3": 1}),
    "S2-R": dict(comps=("rv312",), N=10, rebal="R", mf=None, gt={"rv312": 1.0}, ge={"ma3": 1}, ind_cap=2),
}

if __name__ == "__main__":
    P = F.load_all()
    idx = P["idx"]
    a, b = idx.searchsorted(pd.Timestamp(F.NEW[0])), idx.searchsorted(pd.Timestamp(F.NEW[1]))
    rows = []
    for name, sp in SPECS.items():
        for pool in (100, 200, 600):
            cov = float(np.mean([(P["elig"][pool][t] & np.isfinite(P["ff"]["rv312"][t])).sum() / max(P["elig"][pool][t].sum(), 1) for t in range(a, b, 20)]))
            m = F.holdout(P, F.skey(sp), pool, "新資料2013-2016")
            rows.append(dict(版本=name, 池=pool, 池內營收覆蓋率=round(cov, 3), 年化=m["cagr"], 同窗0050=m["bh"], 超額=m["cagr"] - m["bh"], 回撤=m["mdd"], 回撤0050=m["bh_mdd"],
                             夏普=m["sharpe"], 平均持股比=m["expo"], 逐年贏=f"{int(m['ywin'])}/{int(m['ynum'])}"))
    out = pd.DataFrame(rows)
    out.to_csv(F.OUT / "s2_frozen_2013_2016.csv", index=False, encoding="utf-8-sig")
    pd.set_option("display.width", 250)
    print(out.to_string())
