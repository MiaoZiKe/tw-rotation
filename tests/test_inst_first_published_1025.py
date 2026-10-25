"""全市場三大法人金額：首次公布版優先（2026-10-25）。

回歸案例：2026-10-21。
  · 證交所 15:00 公布、新聞（時報資訊）引用：外資 +9.60 億、投信 +129.19 億、自營商 −133.11 億、合計 +5.68 億。
  · 資料湖 inst_market_daily 被晚間那輪覆蓋成：外資 +22.39、投信 +127.99、自營商 −135.72、合計 +14.66。
  · 首次版（台北 16:00 那輪 commit 0f1527bb）原始欄位就是下面 FIRST_1021；晚間版是 REV_1021。
"""
import pandas as pd

from pipeline import run_daily
from pipeline.compute import inst_market

FIRST_1021 = dict(date="2026-10-21", foreign_buy=335331066770.0, foreign_sell=334370837354.0,
                  trust_buy=29598279699.0, trust_sell=16679250711.0,
                  dealer_buy=40617899741.0, dealer_sell=53928808208.0,
                  total_buy=405547246210.0, total_sell=404978896273.0)
REV_1021 = dict(date="2026-10-21", foreign_buy=3.470694e11, foreign_sell=3.448304e11,
                trust_buy=3.039890e10, trust_sell=1.760037e10, dealer_buy=4.061823e10, dealer_sell=5.418993e10,
                total_buy=4.180865e11, total_sell=4.166207e11)
DAY_1020 = dict(date="2026-10-20", foreign_buy=2.486755e11, foreign_sell=3.282152e11,
                trust_buy=3.404439e10, trust_sell=1.528588e10, dealer_buy=3.407223e10, dealer_sell=6.965154e10,
                total_buy=3.167922e11, total_sell=4.131527e11)
OHLC = pd.DataFrame({"symbol": "TSE", "date": ["2026-10-20", "2026-10-21"], "close": [46292.93, 46887.77]})


def _series(first):
    return inst_market.series(pd.DataFrame([DAY_1020, REV_1021]), pd.DataFrame(), pd.DataFrame(), OHLC, first=first)


def test_1021_首次公布版與新聞一致_晚間版放rev():
    s = _series(pd.DataFrame([FIRST_1021]))
    r = s["rows"][-1]
    assert r["d"] == "2026-10-21"
    assert (r["f"], r["t"], r["dl"], r["tot"]) == (9.60, 129.19, -133.11, 5.68)   # 新聞數字
    assert r["first"] is True
    assert r["rev"] == {"f": 22.39, "t": 127.99, "dl": -135.72, "tot": 14.66}      # 晚間修訂版保留
    assert round(r["f"] + r["t"] + r["dl"], 2) == r["tot"]
    assert s["n_rev"] == 1


def test_沒有首次版的日子退回晚間版_不標first():
    s = _series(pd.DataFrame([FIRST_1021]))
    r = s["rows"][0]
    assert r["d"] == "2026-10-20" and "first" not in r and "rev" not in r
    assert r["f"] == -795.40


def test_沒給first_行為與舊版相同():
    s = _series(None)
    assert s["rows"][-1]["f"] == 22.39 and "first" not in s["rows"][-1]
    assert _series(pd.DataFrame())["rows"][-1]["f"] == 22.39


def test_首次版與晚間版相同_不附rev():
    s = inst_market.series(pd.DataFrame([FIRST_1021]), pd.DataFrame(), pd.DataFrame(), OHLC,
                           first=pd.DataFrame([FIRST_1021]))
    r = s["rows"][-1]
    assert r["first"] is True and "rev" not in r and s["n_rev"] == 0


def test_只有首次版沒有晚間版也能用():
    s = inst_market.series(pd.DataFrame([DAY_1020]), pd.DataFrame(), pd.DataFrame(), OHLC,
                           first=pd.DataFrame([FIRST_1021]))
    assert s["rows"][-1]["f"] == 9.60 and "rev" not in s["rows"][-1]


def test_空資料不炸():
    s = inst_market.series(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), first=pd.DataFrame())
    assert s["rows"] == [] and s["n_rev"] == 0


# ------------------------------------------------------------ 每日管線：先到的贏、只收台北當天的最新日
def test_只收台北當天的最新一天_舊日子與隔天才抓到的不收(tmp_path):
    seed = tmp_path / "seed.csv"
    seed.write_text("date,foreign_buy\n", encoding="utf-8")          # 空種子
    df = pd.DataFrame([DAY_1020, REV_1021])
    # 台北 10/21 16:00 抓 → 只收 10/21
    got = run_daily.first_published_rows(df, now="2026-10-21T08:00:57Z", seed_path=seed)
    assert got["date"].tolist() == ["2026-10-21"] and got["src"].iloc[0] == "finmind"
    # 台北 10/22 05:00 才抓到（10/21 已是修訂版）→ 一筆都不收
    assert run_daily.first_published_rows(df, now="2026-10-21T21:00:00Z", seed_path=seed).empty


def test_種子優先於這一輪_且正式種子檔有1021(tmp_path):
    got = run_daily.first_published_rows(pd.DataFrame([REV_1021]), now="2026-10-21T13:38:00Z")
    r = got[got["date"] == "2026-10-21"].iloc[0]
    assert r["foreign_buy"] == FIRST_1021["foreign_buy"] and r["src"].startswith("git:")


def test_種子檔讀不到不影響(tmp_path):
    got = run_daily.first_published_rows(pd.DataFrame([REV_1021]), now="2026-10-21T08:00:00Z",
                                         seed_path=tmp_path / "nope.csv")
    assert got["date"].tolist() == ["2026-10-21"]
    assert run_daily.first_published_rows(None, seed_path=tmp_path / "nope.csv").empty


def test_資料表已註冊():
    from pipeline import config
    assert config.TABLES["inst_market_first"] == ["date"]


def test_with_seed_種子補進來_湖裡有的那天以湖為準(tmp_path):
    got = inst_market.with_seed(pd.DataFrame())
    assert "2026-10-21" in set(got["date"])                      # 正式種子檔
    lake = pd.DataFrame([dict(FIRST_1021, foreign_buy=1.0)])
    got = inst_market.with_seed(lake)
    assert got[got["date"] == "2026-10-21"]["foreign_buy"].iloc[0] == 1.0
    assert inst_market.with_seed(None, seed_path=tmp_path / "nope.csv").empty
