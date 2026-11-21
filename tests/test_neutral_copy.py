"""評語中性化的護欄（DECISIONS #333，Andy 2026-10-06：「好言論改中性」）。

為什麼要有這支：這是公開網站，任何人都看得到。判定文字只要寫成「可以分批進場」「突破可追」
「接近供給區要減碼」「觀望」，讀起來就是對不特定人提供個股買賣建議（投信投顧法）。
所以 pipeline 產生、會印到畫面上的每一句評語，只准描述數據狀態與「什麼條件成立／沒成立」，
不准出現動作建議或「便宜／好機會」這類價值判斷。

做法：拿隨機漫步（上漲、下跌、盤整三種漂移、多個種子）把技術判定、多週期腳本、
個股 AI 分析整包、技術分與基本面分的理由列全部跑一遍，把輸出的字串全部攤平掃禁用字。
「停損」不在禁用字內：它是規則推算的價位參數名稱（法遵頁已註明「不是建議的停損價」），
屬於保留的灰色地帶，見 docs/neutral_copy_1006.md。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import indicators as ind  # noqa: E402
from pipeline.compute import analysis as AN  # noqa: E402
from pipeline.compute import mtf  # noqa: E402
from pipeline.compute import scoring  # noqa: E402
from pipeline.compute import technical as T  # noqa: E402

# 動作建議與價值判斷。和 scripts/_uitest.py 的「中性用語1006」段用同一張清單（前端那邊多掃畫面文字）。
BANNED = ("買點", "賣點", "進場", "出場", "可追", "該跑", "加碼", "減碼", "布局", "佈局", "抄底",
          "逢低", "便宜", "好機會", "找買", "追高", "追進", "觀望", "可留意", "不要碰", "不要接",
          "承接", "抬轎", "停利", "該賣", "別急", "獲利了結", "短打", "划算", "出不掉", "沒人氣")


def _walk(n=400, drift=0.001, vol=0.014, seed=3):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(drift, vol, n)))
    h = c * (1 + np.abs(rng.normal(0, 0.004, n)))
    lo = c * (1 - np.abs(rng.normal(0, 0.004, n)))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum.reduce([h, c, o]); lo = np.minimum.reduce([lo, c, o])
    return pd.DataFrame({"date": pd.bdate_range("2024-01-01", periods=n).strftime("%Y-%m-%d"),
                         "open": o, "high": h, "low": lo, "close": c,
                         "volume": rng.integers(2e6, 4e7, n).astype(float)})


def _hits(obj) -> list[str]:
    txt = json.dumps(obj, ensure_ascii=False, default=str)
    return [w for w in BANNED if w in txt]


CASES = [(d, s) for d in (0.004, 0.001, 0.0, -0.002, -0.004) for s in (1, 3, 7, 12, 21)]


def test_判定常數本身是中性描述():
    for v in (T.V_EXCLUDED, T.V_A, T.V_B, T.V_PENDING, T.V_COUNTER, AN.ST_OK, AN.ST_PENDING, AN.ST_BEAR):
        assert not _hits(v), v


@pytest.mark.parametrize("drift,seed", CASES)
def test_技術判定與多週期腳本沒有操作建議(drift, seed):
    raw = _walk(drift=drift, seed=seed)
    x = ind.compute_all(raw)
    v = T.evaluate(x, avg_turnover=5e8, with_checks=True)
    assert v["verdict"] in (T.V_EXCLUDED, T.V_A, T.V_B, T.V_PENDING, T.V_COUNTER)
    assert not _hits(v), (v["verdict"], _hits(v))
    m = mtf.build(raw, None, None, daily_ind=x)
    assert not _hits(m), _hits(m)
    a = AN.build(verdict=v, mtf_res=m, inst_v3={"daily": [["2025-07-01", 1e6, 0, 0, 0]]},
                 margin=[["2025-07-01", 100.0, 0, 0, 0]], holders=[["2025-07-01", 30.0, 0, 0, 0]],
                 fundamental={"pe": 15.0, "percentile": 10.0, "group_median": 20.0, "group_n": 8,
                              "metric": "pe"},
                 revenue={"monthly": [["2025-06", 1, 5.0]]}, profit={"quarters": []},
                 news=[], material_news=[], as_of="2025-07-01", code="9999", name="測試",
                 avg_vol20=float(raw["volume"].tail(20).mean()))
    assert not _hits(a), _hits(a)
    assert a["facets"]["tech"]["stance"] in (AN.ST_OK, AN.ST_PENDING, AN.ST_BEAR)
    s, pros, cons = scoring.tech_score(x.iloc[-1], x, v, base=ind.technical_score(x.iloc[-1]))
    assert not _hits(pros + cons), _hits(pros + cons)


def test_低流動性與過熱的排除理由也是中性():
    """排除條件是最容易寫成「出不掉」「幫別人抬轎」的地方：逐條觸發確認文字。"""
    raw = _walk(drift=0.006, seed=5)          # 一路漲 → 20 日乖離高
    x = ind.compute_all(raw)
    v = T.evaluate(x, avg_turnover=1e6, with_checks=True)   # 成交值低於門檻
    assert v["verdict"] == T.V_EXCLUDED
    assert any("流動性門檻" in r for r in v["exclusions"]), v["exclusions"]
    assert not _hits(v), _hits(v)


@pytest.mark.parametrize("pct", [0.0, 10.0, 30.0, 50.0, 80.0, 95.0])
def test_估值分位的理由不寫便宜或貴(pct):
    s, pros, cons = scoring.fund_score({"percentile": pct, "metric": "pe", "group_n": 6})
    joined = "".join(pros + cons)
    assert not _hits(pros + cons), joined
    assert "貴" not in joined
    if pct <= 30:
        assert any("低於多數同業" in t for t in pros), pros
    if pct >= 80:
        assert any("高於多數同業" in t for t in cons), cons


def test_空資料不會炸也不會冒出建議字():
    """邊界：fund_score 給 None／空 dict 時照舊回 None 與空理由。"""
    assert scoring.fund_score(None) == (None, [], [])
    assert scoring.fund_score({}) == (None, [], [])
