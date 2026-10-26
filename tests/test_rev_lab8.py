"""第八輪紅線測試：S2 規格不變、凍結檔完整、最終驗證在營收未補齊時不執行、保留日誌只讀不重算。"""
import json

import numpy as np
import pandas as pd

from pipeline.compute import rev_lab8 as R8


def test_S2規格與factor_lab一致():
    sp = R8.make_spec()
    assert sp["comps"] == ("rv312",) and sp["N"] == 10 and sp["rebal"] == "R" and sp["mf"] is None
    assert sp["gt"] == {"rv312": 1.0} and sp["ge"] == {"ma3": 1}                # 近 3 月均／近 12 月均 > 1、站上 20/60/120 日線、無大盤濾網


def test_變體只改指定軸():
    base = R8.make_spec()["axes"]
    for ax, lv in R8.AXES.items():
        for v in lv:
            a = R8.make_spec(**{ax: v})["axes"]
            assert sum(1 for k in a if a[k] != base[k]) == 1


def test_凍結檔完整且含S2():
    fc = json.loads((R8.OUT / "frozen_candidates.json").read_text(encoding="utf-8"))
    names = [c["name"] for c in fc["candidates"]]
    assert names[0].startswith("S2") and len(names) >= 5 and "frozen_at" in fc
    for c in fc["candidates"]:
        assert "axes" in c["spec"]


def test_營收未補齊不執行最終驗證(monkeypatch):
    monkeypatch.setattr(R8, "backfill_done", lambda fetch=True: (False, {"revenue": 273}))
    res = R8.run_final({}, [("S2", R8.make_spec(), "參照")])
    assert res["ran"] is False
    assert "不執行" in res["reason"]


def test_最終驗證每個凍結候選每池只跑一次(tmp_path, monkeypatch):
    monkeypatch.setattr(R8, "FINAL_LOG", tmp_path / "final_log.csv")
    monkeypatch.setattr(R8, "backfill_done", lambda fetch=True: (True, {}))
    monkeypatch.setattr(R8, "coverage_ok", lambda P, **k: True)
    calls = []
    monkeypatch.setattr(R8, "mrow", lambda P, sp, pool, lo, hi: calls.append(1) or dict(cagr=.2, mdd=-.2, sharpe=1, bh=.1, bh_mdd=-.3, excess=.1, ywin=2, ynum=3, yrets="{}", y0050="{}", expo=.8, turn=1, years=3))
    c = [("S2", R8.make_spec(), "參照")]
    R8.run_final({}, c); n = len(calls)
    R8.run_final({}, c)
    assert n == 2 and len(calls) == 2                          # 第二次只讀紀錄
