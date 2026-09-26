"""個股頁「AI 分析」卡（pipeline/compute/analysis.py）的規則測試。

Andy 2026-09-26：「觀望部分需要標示 AI 分析，並且需要說明原因；…分不同時間週期的說明（只到週級別）
→ 這是技術面，需要有籌碼面、基本面、消息面看法」。

這支擋的事：
- 技術面只有 1 小時／4 小時／日線／週線四行，**沒有月線**（月線的支撐壓力也不列）
- 觀望要列出**哪幾條**沒成立、帶數字；大小週期方向相反要講出來
- 籌碼／基本／消息三段：有資料就帶數字、缺資料就寫「資料缺」，不拿別的湊
- 消息面不做情緒打分；as_of 之後的新聞不准被算進來（無未來函數）
- 全部文字不准出現「買進／賣出／建議」這類指示用語（證券投顧法風險）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import indicators as ind  # noqa: E402
from pipeline.compute import analysis as AN  # noqa: E402
from pipeline.compute import mtf  # noqa: E402
from pipeline.compute import technical as T  # noqa: E402

FORBID = ("買進", "賣出", "建議", "不要接", "追進", "抬轎", "加碼", "減碼", "進場吧")


def _walk(n=400, drift=0.001, seed=3):
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(np.cumsum(rng.normal(drift, 0.014, n)))
    h = c * (1 + np.abs(rng.normal(0, 0.004, n)))
    lo = c * (1 - np.abs(rng.normal(0, 0.004, n)))
    o = np.r_[c[0], c[:-1]]
    h = np.maximum.reduce([h, c, o]); lo = np.minimum.reduce([lo, c, o])
    return pd.DataFrame({"date": pd.bdate_range("2024-01-01", periods=n).strftime("%Y-%m-%d"),
                         "open": o, "high": h, "low": lo, "close": c,
                         "volume": rng.integers(2e6, 4e7, n).astype(float)})


def _verdict_and_mtf(seed=3):
    raw = _walk(seed=seed)
    x = ind.compute_all(raw)
    v = T.evaluate(x, avg_turnover=5e8, with_checks=True)
    m = mtf.build(raw, None, None, daily_ind=x)
    return v, m, raw


def _all_text(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


# ------------------------------------------------------------------ 技術面

def test_tech_has_four_timeframes_and_no_monthly():
    v, m, _ = _verdict_and_mtf()
    t = AN.tech_facet(v, m)
    assert [r["tf"] for r in t["tfs"]] == ["60m", "240m", "1d", "1w"]
    assert [r["label"] for r in t["tfs"]] == ["1 小時", "4 小時", "日線", "週線"]
    assert "月線" not in _all_text(t["tfs"])
    for z in t["levels"]["support"] + t["levels"]["resistance"]:
        assert z["tf"] != "1M", "支撐壓力只列到週線"
    # 沒有分 K：1H／4H 要明講沒資料，不是空白、也不是拿日線冒充
    assert t["tfs"][0]["word"] == "無資料" and "60 分 K" in t["tfs"][0]["points"][0]
    assert t["label"] in ("偏多", "中性", "偏空")


def test_watch_lists_concrete_failed_conditions_with_numbers():
    """觀望時：列出 A／B 各幾條成立、未成立的是哪幾條（帶數字）。"""
    found = False
    for seed in range(3, 30):
        v, m, _ = _verdict_and_mtf(seed)
        if v["verdict"] != "觀望":
            continue
        found = True
        t = AN.tech_facet(v, m)
        assert t["stance"] == "觀望"
        joined = "；".join(t["reasons"])
        assert "回檔型態（A）6 條中" in joined and "突破型態（B）5 條中" in joined
        assert "未成立" in joined or not all(c["ok"] for c in v["checks"]["a"])
        assert any(ch.isdigit() for ch in joined)
        assert "多空條件都不完整" not in joined, "不能再只寫籠統的一句"
        assert t["ifs"] and all(s.startswith(("若", "日線下方", "價格已在", "已站上")) for s in t["ifs"])
        a = AN.build(verdict=v, mtf_res=m, inst_v3=None, margin=None, holders=None, fundamental=None,
                     revenue=None, profit=None, news=None, material_news=None, as_of="2025-07-01",
                     code="9999", name="測試", avg_vol20=None)
        assert a["headline"]["stance"] == "觀望" and "/6" in a["headline"]["brief"]
        break
    assert found, "隨機漫步 27 組裡應該至少有一組是觀望"


def test_timeframe_conflict_is_spelled_out():
    v, m, _ = _verdict_and_mtf()
    m = json.loads(json.dumps(m))
    m["tf"]["1w"]["trend"] = 1
    m["tf"]["60m"] = dict(m["tf"]["1d"], tf="60m", trend=-1)
    t = AN.tech_facet(v, m)
    assert any("週線多頭，但1 小時仍是空頭結構、尚未翻多" in r for r in t["reasons"]), t["reasons"]


def test_intraday_line_uses_bar_time():
    """1 小時的 BOS／CHoCH 標的是分 K 時間（帶時區的 ISO），要顯示成「月-日 時:分」，不是整串時間戳。"""
    v = {"trend": -1, "ma_align": -1, "rsi": 41.2, "demand": [], "supply": [],
         "marks": {"choch": [["2026-09-24T10:00:00+08:00", -1]], "bos": []}}
    ln = AN._tf_line("60m", "1 小時", v)
    assert ln["word"] == "空頭" and "最近 CHoCH 翻空（09-24 10:00）" in ln["points"]
    assert "均線空頭排列" in ln["points"] and "RSI 41" in ln["points"]


def test_grade_a_stance_is_can_watch():
    v = {"verdict": "可以分批進場（回檔承接）", "grade": "A", "reasons": [], "stop": 90, "tp1": 120, "rr": 2.5,
         "risk_pct": 4.0, "demand": [], "checks": {"a": [], "b": [], "risk": {}, "met_a": 6, "met_b": 0,
                                                    "n_a": 6, "n_b": 5, "exclusions": []}}
    m = {"tf": {"1d": {"trend": 1, "ma_align": 1, "rsi": 55, "demand": [], "supply": [], "marks": {}},
                "1w": {"trend": 1, "ma_align": 1, "rsi": 60, "demand": [], "supply": [], "marks": {}}},
         "summary": {}}
    t = AN.tech_facet(v, m)
    assert t["stance"] == "可留意" and t["label"] == "偏多"
    assert "A 級" in t["reasons"][0]


# ------------------------------------------------------------------ 籌碼面

def test_chip_facet_direction_and_units():
    # 20 天、每天三大法人合計買超 500 張（50 萬股），日均量 5,000 張 → 佔 10% → 偏多
    rows = [[f"2026-09-{d:02d}", 300000.0, 150000.0, 50000.0, 0.0] for d in range(1, 21)]
    margin = [[f"2026-08-{d:02d}", 10000.0 - d * 10, 0, 0, 0] for d in range(1, 26)]
    holders = [["2026-09-04", 40.0, 0, 0, 0], ["2026-09-11", 40.5, 0, 0, 0]]
    c = AN.chip_facet({"daily": rows}, margin, holders, avg_vol20=5_000_000)
    assert c["label"] == "偏多", c
    txt = _all_text(c)
    assert "近 5 日買超 2,500 張" in txt and "近 20 日買超 10,000 張" in txt   # 股 → 張
    assert "只有 2 週" in txt, "集保資料不滿 5 週要誠實講"


def test_chip_facet_missing_everything():
    c = AN.chip_facet(None, None, None, None)
    assert c["label"] == "資料缺" and all("資料缺" in p for p in c["points"])


def test_chip_facet_small_net_is_neutral():
    """法人淨額只佔成交量 0.2% → 不算方向（大型股賣超幾百張是雜訊）。"""
    rows = [[f"2026-09-{d:02d}", -10000.0, 0.0, 0.0, 0.0] for d in range(1, 21)]
    c = AN.chip_facet({"daily": rows}, None, None, avg_vol20=5_000_000)
    assert c["label"] == "中性"


# ------------------------------------------------------------------ 基本面

def test_fund_facet_growth_is_bullish_and_cites_numbers():
    fx = {"metric": "pe", "metric_value": 20.0, "pe": 20.0, "group_median": 25.0, "group_n": 8,
          "percentile": 30.0, "group_name": "測試族群", "rev_streak": 5}
    rev = {"monthly": [["2026-06", 1e9, 25.0], ["2026-07", 1e9, 30.0], ["2026-08", 1e9, 35.0]]}
    q = [[f"2024Q{i}", 0, 0, 0, 0, 1.0] for i in range(1, 5)] + [[f"2025Q{i}", 0, 0, 0, 0, 1.5] for i in range(1, 5)]
    f = AN.fund_facet(fx, rev, {"quarters": q})
    assert f["label"] == "偏多"
    txt = _all_text(f)
    assert "本益比 20.0 倍" in txt and "分位 30%" in txt and "+35.0%" in txt and "合計 6.00 元" in txt
    assert "逐月走高" in txt


def test_fund_facet_loss_and_missing():
    q = [[f"2025Q{i}", 0, 0, 0, 0, -0.5] for i in range(1, 5)]
    f = AN.fund_facet({"is_loss": True}, None, {"quarters": q})
    assert f["label"] == "偏空"
    assert "資料缺" in _all_text(f)
    assert AN.fund_facet(None, None, None)["label"] == "資料缺"


# ------------------------------------------------------------------ 消息面

def test_news_facet_counts_filters_and_no_future():
    news = [
        {"date": "2026-09-23", "title": "禾伸堂(3026)擴產", "url": "https://x/1", "source": "cnyes"},
        {"date": "2026-09-21", "title": "別家公司違約交割", "url": "https://x/2", "source": "cnyes"},   # 沒提到本檔
        {"date": "2026-09-30", "title": "禾伸堂 未來的新聞", "url": "https://x/3", "source": "cnyes"},  # as_of 之後
        {"date": "2026-08-01", "title": "禾伸堂 太舊的新聞", "url": "https://x/4", "source": "cnyes"},  # 超過 30 天
    ]
    mat = [{"date": "2026-09-23", "subject": "補充公告本公司取得不動產", "clause": "第20款"}]
    x = AN.news_facet(news, mat, "2026-09-24", "3026", "禾伸堂")
    assert x["counts"] == {"m7": 1, "m30": 1, "n7": 1, "n30": 1}
    assert x["label"] == "中性" and "未判讀情緒" in x["why"]
    titles = [i["title"] for i in x["items"]]
    assert "禾伸堂 未來的新聞" not in titles and "別家公司違約交割" not in titles
    assert x["items"][0]["kind"] in ("重大訊息", "新聞")


def test_news_facet_watch_words_and_empty():
    mat = [{"date": "2026-09-20", "subject": "本公司遭訴訟求償", "clause": "第12款"}]
    x = AN.news_facet([], mat, "2026-09-24", "1234", "某某")
    assert x["label"] == "留意" and "訴訟" in x["why"]
    y = AN.news_facet([], [], "2026-09-24", "1234", "某某")
    assert y["label"] == "中性" and "沒有" in y["why"]


# ------------------------------------------------------------------ 整包

def test_build_whole_card_has_no_advice_words():
    for seed in (3, 7, 12):
        v, m, raw = _verdict_and_mtf(seed)
        a = AN.build(verdict=v, mtf_res=m, inst_v3={"daily": [["2025-07-01", 1e6, 0, 0, 0]]},
                     margin=[["2025-07-01", 100.0, 0, 0, 0]], holders=[["2025-07-01", 30.0, 0, 0, 0]],
                     fundamental={"pe": 15.0}, revenue={"monthly": [["2025-06", 1, 5.0]]},
                     profit={"quarters": []}, news=[], material_news=[], as_of="2025-07-01",
                     code="9999", name="測試", avg_vol20=float(raw["volume"].tail(20).mean()))
        txt = _all_text(a)
        for w in FORBID:
            assert w not in txt, f"出現指示用語「{w}」"
        assert "nan" not in txt.lower()
        assert set(a["facets"]) == {"tech", "chip", "fund", "news"}
        for k, f in a["facets"].items():
            assert f["label"] in ("偏多", "中性", "偏空", "留意", "資料缺"), (k, f["label"])
            assert f["why"], k
        assert a["method"] == "規則式自動判讀"
