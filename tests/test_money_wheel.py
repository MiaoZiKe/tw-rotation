"""資金輪盤（compute/money_wheel.py）：口徑、象限、盤中續算公式與批次算法一致。"""
import numpy as np
import pandas as pd

from pipeline.compute import money_wheel as mw


def _hist(n=60, seed=1):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2026-07-01", periods=n).strftime("%Y-%m-%d")
    rows = []
    for gid, base in (("a", 20.0), ("b", 10.0), ("c", 2.0), ("tiny", 0.1)):
        s = base * (1 + 0.05 * rng.standard_normal(n))
        if gid == "c":                       # c：最後 5 天占比暴增 → 資金集中
            s[-5:] *= 2.0
        for d, v in zip(dates, s):
            rows.append({"date": d, "group_id": gid, "group_name": gid.upper(), "chain": "t",
                         "turnover": v * 1e8, "turnover_share": v})
    return pd.DataFrame(rows)


def test_axes_definition():
    h = _hist()
    r = mw.money_rrg(h)
    p = {q["group_id"]: q for q in r["points"]}
    assert "tiny" not in p                                   # 占比 < 0.3% 不畫
    s = h[h.group_id == "c"].sort_values("date")["turnover_share"].to_numpy()
    assert abs(p["c"]["x"] - 100 * s[-5:].mean() / s[-20:].mean()) < 0.01
    assert p["c"]["x"] > 120 and p["c"]["quadrant"] in ("leading", "weakening")
    assert r["kind"] == "money" and r["date"] == h["date"].max()


def test_trail_length_and_cap():
    r = mw.money_rrg(_hist(), trail=31)
    for q in r["points"]:
        assert 1 <= len(q["trail"]) <= 31
        assert q["trail"][-1][1] == q["x"] and q["trail"][-1][2] == q["y"]


def test_insufficient_history_draws_nothing():
    assert mw.money_rrg(_hist(n=22))["points"] == []         # 20 日窗 + 5 日動能湊不滿


def test_live_step_matches_batch():
    """前端的續算公式（寫在 money_rrg 註解裡）拿「真實的下一天占比」算，要等於批次重算的結果。"""
    h = _hist(n=61)
    full = {q["group_id"]: q for q in mw.money_rrg(h)["points"]}
    cut = h[h.date != h.date.max()]
    part = {q["group_id"]: q for q in mw.money_rrg(cut)["points"]}
    last_day = h[h.date == h.date.max()].set_index("group_id")["turnover_share"]
    for gid, q in part.items():
        s_new = float(last_day[gid])
        tail = q["live_state"]["sh_tail"]
        ms = (tail[-(mw.SHORT - 1):] + [s_new])
        ml = (tail[-(mw.LONG - 1):] + [s_new])
        x = 100 * (sum(ms) / len(ms)) / (sum(ml) / len(ml))
        x5 = q["trail"][len(q["trail"]) - mw.MOM][1]
        y = 100 + 100 * (x / x5 - 1)
        assert abs(x - full[gid]["x"]) < 0.05, gid
        assert abs(y - full[gid]["y"]) < 0.1, gid
