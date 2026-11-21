"""總覽「漲跌家數」分佈依市場拆成 全部／上市／上櫃（Andy 2026-09-26）。

這裡守住的是四件事：

1. **級距邊界跟前端 UD_BINS 一模一樣**（漲跌停門檻 9.5、邊界值歸極端那一級、平＝捨入到 0.01 為 0）。
   以前分級只寫在 app.js，現在管線是唯一權威（stocks.json 每列帶 `ud`），前端直接讀；
   這裡把每一條邊界釘住，改了就紅。
2. **捨入跟 JavaScript Math.round 同一套（.5 往 +∞）**，不是 Python 的銀行家捨入 ——
   否則 0.005 這種剛好落在邊界的股票，長條算在 0~1、點開的清單卻說它是平盤。
3. **三組分佈每一級都滿足 全部 ＝ 上市 ＋ 上櫃（＋ 市場別不明）**；市場別不明的不准默默消失。
4. **邊界輸入**：空資料、None／NaN／字串漲跌幅、市場別缺值或興櫃。
"""
from __future__ import annotations

import math

import pytest

from pipeline.build_payload import LIMIT_PCT
from pipeline.compute import flow


# ---------------------------------------------------------------- 1. 級距邊界
@pytest.mark.parametrize("v,want", [
    (-10.0, 0), (-9.5, 0), (-9.49, 1),           # 跌停門檻：≤ -9.5
    (-5.0, 1), (-4.99, 2),                        # <-5 含 -5.00
    (-3.0, 2), (-2.99, 3),
    (-1.0, 3), (-0.99, 4),
    (-0.01, 4), (0.0, 5), (0.01, 6),              # 平＝剛好 0
    (0.99, 6), (1.0, 7),                          # 正邊界歸較極端那一級
    (2.99, 7), (3.0, 8),
    (4.99, 8), (5.0, 9),
    (9.49, 9), (9.5, 10), (10.0, 10),             # 漲停門檻：≥ 9.5
    (110.0, 10),                                  # 新上市無漲跌幅限制：歸漲停那一級（DECISIONS #258-8）
])
def test_bin_edges_match_frontend(v, want):
    assert flow.updown_bin(v, LIMIT_PCT) == want


def test_limit_threshold_is_build_payload_constant():
    """漲跌停判定不變：門檻就是 build_payload.LIMIT_PCT（9.5），不另立真值。"""
    assert LIMIT_PCT == 9.5
    assert flow.updown_bin(9.5) == 10 and flow.updown_bin(-9.5) == 0
    assert flow.updown_bin(9.49) == 9 and flow.updown_bin(-9.49) == 1
    # 換門檻時兩端一起跟著動（證明門檻是參數，不是寫死在級距裡）
    assert flow.updown_bin(7.0, limit_pct=7.0) == 10
    assert flow.updown_bin(6.99, limit_pct=7.0) == 9


# ---------------------------------------------------------------- 2. 捨入
def test_rounding_is_half_up_like_js_math_round():
    # 0.005 → JS Math.round(0.5)=1 → 0.01 → 0~1；Python round(0.005, 2) 會是 0.01 或 0.0（浮點＋銀行家），不能靠它
    assert flow.updown_bin(0.005) == 6
    # -0.005 → Math.round(-0.5) = -0（往 +∞）→ 平盤
    assert flow.updown_bin(-0.005) == 5
    assert flow.updown_bin(-0.0051) == 4
    assert flow.updown_bin(0.004) == 5 and flow.updown_bin(-0.004) == 5
    # ±9.495 × 100 在浮點是 ±949.4999…（不是 .5），兩邊都捨成 ±9.49 → 還不到漲跌停。
    # 這兩條不是在說「9.495 不算漲停」有什麼金融意義，是在釘「跟 JS 逐位一致」：
    # node 實測 Math.round(9.495*100)/100 = 9.49、Math.round(-0.005*100)/100 = -0。
    assert flow.updown_bin(-9.495) == 1
    assert flow.updown_bin(9.495) == 9
    assert flow.updown_bin(1.005) == 7            # 1.005×100 = 100.4999… → 1.0 → 1~3


@pytest.mark.parametrize("bad", [None, float("nan"), float("inf"), float("-inf"), "abc", "", True, [1]])
def test_bad_values_return_none(bad):
    assert flow.updown_bin(bad) is None


def test_numeric_string_is_accepted():
    assert flow.updown_bin("3.2") == 8


# ---------------------------------------------------------------- 3. 三組分佈與加總
def _rows():
    return [
        {"code": "2330", "market": "TWSE", "chg_pct": 1.2},
        {"code": "2317", "market": "TWSE", "chg_pct": -9.8},     # 跌停
        {"code": "2454", "market": "TWSE", "chg_pct": 0.0},      # 平
        {"code": "6669", "market": "TWSE", "chg_pct": 9.9},      # 漲停
        {"code": "8069", "market": "TPEX", "chg_pct": 9.6},      # 漲停
        {"code": "3105", "market": "TPEX", "chg_pct": -2.0},
        {"code": "5347", "market": "tpex", "chg_pct": 5.0},      # 市場別大小寫不影響
        {"code": "6488", "market": "TPEX", "chg_pct": None},     # 沒有漲跌幅：不計入任何一組
        {"code": "7777", "market": "EMERGING", "chg_pct": -0.5}, # 興櫃 → other
        {"code": "8888", "market": None, "chg_pct": 3.3},        # 市場別缺值 → other
    ]


def test_three_groups_distribution():
    d = flow.updown_distribution(_rows(), LIMIT_PCT)
    assert d["labels"] == list(flow.UD_LABELS) and len(d["labels"]) == 11
    assert d["limit_pct"] == 9.5
    assert d["twse"]["counts"] == [1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 1]
    assert d["tpex"]["counts"] == [0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 1]
    assert d["other"]["counts"] == [0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0]
    assert d["all"]["n"] == 9                        # 6488 沒漲跌幅不算
    assert d["twse"]["n"] == 4 and d["tpex"]["n"] == 3 and d["other"]["n"] == 2
    # 漲／跌／平家數
    assert (d["twse"]["up"], d["twse"]["down"], d["twse"]["flat"]) == (2, 1, 1)
    assert (d["tpex"]["up"], d["tpex"]["down"], d["tpex"]["flat"]) == (2, 1, 0)
    for k in ("all", "twse", "tpex", "other"):
        g = d[k]
        assert g["up"] + g["down"] + g["flat"] == g["n"] == sum(g["counts"])


def test_sum_invariant_every_bin():
    d = flow.updown_distribution(_rows(), LIMIT_PCT)
    for i in range(11):
        assert d["all"]["counts"][i] == d["twse"]["counts"][i] + d["tpex"]["counts"][i] + d["other"]["counts"][i]
    assert d["check"] == {"ok": True, "diff": [0] * 11}


def test_only_twse_and_tpex_then_listed_plus_otc_equals_all():
    rows = [r for r in _rows() if str(r["market"] or "").upper() in ("TWSE", "TPEX")]
    d = flow.updown_distribution(rows, LIMIT_PCT)
    assert d["other"]["n"] == 0
    assert [a + b for a, b in zip(d["twse"]["counts"], d["tpex"]["counts"])] == d["all"]["counts"]


def test_distribution_uses_same_bins_as_per_row_ud():
    """前端點一級列出的清單靠每列的 `ud`；長條高度＝分佈的 counts。兩者必須同一套分級。"""
    rows = _rows()
    d = flow.updown_distribution(rows, LIMIT_PCT)
    for k, want in (("TWSE", d["twse"]["counts"]), ("TPEX", d["tpex"]["counts"])):
        got = [0] * 11
        for r in rows:
            if str(r["market"] or "").upper() == k:
                i = flow.updown_bin(r["chg_pct"], LIMIT_PCT)
                if i is not None:
                    got[i] += 1
        assert got == want


# ---------------------------------------------------------------- 4. 邊界輸入
@pytest.mark.parametrize("rows", [[], None, [None, 1, "x"], [{"market": "TWSE"}]])
def test_empty_or_garbage_input(rows):
    d = flow.updown_distribution(rows, LIMIT_PCT)
    for k in ("all", "twse", "tpex", "other"):
        assert d[k]["n"] == 0 and d[k]["counts"] == [0] * 11
        assert d[k]["up"] == d[k]["down"] == d[k]["flat"] == 0
    assert d["check"]["ok"] is True


def test_nan_chg_is_skipped_not_counted_as_flat():
    d = flow.updown_distribution([{"market": "TWSE", "chg_pct": math.nan}], LIMIT_PCT)
    assert d["all"]["n"] == 0 and d["all"]["flat"] == 0
