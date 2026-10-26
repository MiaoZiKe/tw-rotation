"""前向模擬盤紅線測試：參數凍結、訊號日判斷、帳務輸出、不持有 ETF、回放與前向分段。"""
import json
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from test_swing_lab5 import _P  # noqa: E402

from pipeline.compute import paper_lab5 as PL  # noqa: E402


def test_凍結參數與第五輪三組完全一致():
    near = pd.read_csv(PL.ROOT / "docs" / "strategy_lab" / "round5" / "near_champions_pool200_only.csv")
    want = sorted(json.dumps(json.loads(s), sort_keys=True) for s in near["spec"])
    got = sorted(json.dumps(v, sort_keys=True) for v in PL.FROZEN.values())
    assert want == got and PL.POOL == 200


def test_季末訊號日判斷():
    idx = pd.bdate_range("2026-09-24", "2026-10-06")
    t = idx.get_loc(pd.Timestamp("2026-09-30"))
    assert PL.is_signal_day(idx, t, True) and not PL.is_signal_day(idx, t - 1, True)
    short = idx[:t + 1]                                   # 資料只到 9/30（沒有 10/1），用營業日推算
    assert PL.is_signal_day(short, len(short) - 1, True)
    assert not PL.is_signal_day(short, len(short) - 2, True)


def test_帳務輸出與0050並列(tmp_path):
    P = _P()
    specs = {"T1": dict(fam="mom", L=252, N=2, rebal="Q", mf="br200")}
    df, sm, orders, hold = PL.run_paper(P=P, replay_start="2020-01-02", forward_from="2020-07-01", out=tmp_path, specs=specs)
    for f in ("equity.csv", "holdings_latest.csv", "orders_next.csv", "trades_ledger.csv", "summary.csv", "latest_summary.md"):
        assert (tmp_path / f).exists()
    assert "0050 含息(扣成本)" in df.columns and set(df["段"]) == {"回放(不算成績)", "前向(算成績)"}
    assert df["0050 含息(扣成本)"].iloc[0] < 1.01 and (df.loc[df["段"].str.startswith("前向")].index >= pd.Timestamp("2020-07-01")).all()
    assert not (set(hold["代號"].astype(str)) & {"0050"})          # 從不持有 ETF
    assert abs(hold[hold["代號"] != "現金"]["占權益"].sum() + float(hold[hold["代號"] == "現金"]["占權益"].iloc[0]) - 1) < 1e-3


def test_不清倉不扣窗尾成本():
    P = _P()
    spec = dict(fam="mom", L=252, N=2, rebal="Q", mf="br200")
    a = PL.S.run_periodic(P, spec, 200, "2020-01-02", "2020-08-31", liquidate=True)
    b = PL.S.run_periodic(P, spec, 200, "2020-01-02", "2020-08-31", liquidate=False)
    assert b["eq"].iloc[-1] >= a["eq"].iloc[-1] and np.allclose(a["eq"].iloc[:-1], b["eq"].iloc[:-1])
