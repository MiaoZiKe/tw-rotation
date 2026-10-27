"""自選日報事實表（pipeline/compute/digest.py）：口徑與法遵白名單。"""
import json
import re

import pandas as pd

from pipeline.compute import digest


def _frames():
    dates = ["2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22"]
    price = pd.DataFrame([{"date": d, "code": c, "close": cl, "volume": 5_000_000.0, "name": n}
                          for d in dates for c, n, cl in (("2330", "台積電", 100.0), ("1101", "台泥", 30.0))])
    price.loc[(price.code == "2330") & (price.date == "2026-10-21"), "close"] = 98.0
    # 2330 外資連 4 天買超；1101 外資前三天買、最後一天賣 → 連賣 1 天
    rows = []
    for d in dates:
        rows.append({"date": d, "code": "2330", "foreign_total": 3000.0, "trust": -1000.0, "dealer": 0.0, "inst_total": 2000.0})
        rows.append({"date": d, "code": "1101", "foreign_total": -500.0 if d == dates[-1] else 800.0, "trust": 0.0, "dealer": 0.0,
                     "inst_total": -500.0 if d == dates[-1] else 800.0})
    inst = pd.DataFrame(rows)
    rev = pd.DataFrame([
        {"ym": "2025-09", "code": "2330", "revenue": 4e11, "announce_date": "2025-10-10"},
        {"ym": "2026-08", "code": "2330", "revenue": 5e11, "announce_date": "2026-09-10"},
        {"ym": "2026-09", "code": "2330", "revenue": 6e11, "announce_date": "2026-10-10"}])
    de = pd.DataFrame([{"code": "1101", "kind": "cash", "amount": 1.5, "ex_date": "2026-11-05"},
                       {"code": "1101", "kind": "stock", "amount": 1.0, "ex_date": "2026-11-05"}])
    mops = [{"d": "2026-10-30", "k": "conf", "code": "2330", "title": "任何主旨"}, {"d": "2026-10-20", "k": "board", "code": "2330", "title": "x"}]
    return price, inst, rev, de, mops


def test_digest_facts():
    d = digest.build(*_frames(), latest="2026-10-22", names={})
    a, b = d["s"]["2330"], d["s"]["1101"]
    assert a["c"] == 100.0 and a["pc"] == 98.0 and a["v"] == 5000
    assert a["i"] == [3, -1, 0, 2]                    # 股 → 張
    assert a["k"] == [4, -4, 4]                       # 外資連買 4、投信連賣 4、合計連買 4
    assert b["k"] == [-1, 0, -1]                      # 最後一天翻賣
    assert a["r"] == {"ym": "2026-09", "rev": 6000.0, "ann": "2026-10-10", "yoy": 50.0, "mom": 20.0}
    assert b["x"] == {"d": "2026-11-05", "a": 1.5}   # 只收現金股利
    assert a["e"] == [["法說會", "2026-10-30"]]       # board 不是日報事件


def test_digest_whitelist_no_advice():
    """法遵 L-13：鍵名限白名單；整份輸出不得出現評分／排名／訊號／建議字樣。"""
    d = digest.build(*_frames(), latest="2026-10-22", names={})
    for s in d["s"].values():
        assert set(s) <= digest.ALLOWED_KEYS
        if "r" in s:
            assert set(s["r"]) <= digest.R_KEYS
    blob = json.dumps(d, ensure_ascii=False)
    assert not re.search(r"評分|排名|訊號|燈號|建議|買點|賣點|進場|出場|目標價|看多|看空|推薦|score|rank|signal", blob)
