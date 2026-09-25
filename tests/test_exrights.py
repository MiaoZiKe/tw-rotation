"""除權息還原（DECISIONS #258，審查員 R5 2026-09-25）。

6669 緯穎 9/2 除權（每股配 1.98 股），股價 7800 → 2615；資料湖不還原的話：
K 線 -66% 斷崖、本益比 6.7（應約 20）、殖利率 10.33%（應約 3.4%）。
這裡釘住：還原後沒有假斷崖、除權前後本益比連續、殖利率用今天股數、
股利欄只放股利、0 價 K 棒濾掉、上市前 5 天的新股不算漲停。
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from pipeline.compute import fundamental as F
from pipeline.compute import stockpage as S


def _days(start: str, n: int) -> list[str]:
    return [d.date().isoformat() for d in pd.bdate_range(start, periods=n)]


def _px(code: str, dates: list[str], closes: list[float], change=None) -> pd.DataFrame:
    c = np.asarray(closes, dtype=float)
    return pd.DataFrame({"code": code, "date": dates, "open": c, "high": c * 1.01, "low": c * 0.99,
                         "close": c, "volume": 1000.0,
                         "change": change if change is not None else np.r_[0.0, np.diff(c)]})


# ---------------------------------------------------------------- 6669 形狀的假資料
EX = "2026-09-02"


def _wiwynn():
    """7800 → 除權參考價 2614.99（配股率 1.9828），之後在 2100～2600 之間走。"""
    pre = _days("2026-06-01", 66)                      # 到 2026-08-31
    pre = [d for d in pre if d < EX]
    post = [d for d in _days(EX, 17)]
    closes = list(np.linspace(5000, 7800, len(pre))) + list(np.linspace(2610, 2115, len(post)))
    px = _px("6669", pre + post, closes)
    results = pd.DataFrame([
        {"date": "2026-06-22", "code": "6669", "kind": "息", "dividend": 144.39,
         "before_price": 5130.0, "reference_price": 4985.6, "open_price": 4985.0},
        {"date": EX, "code": "6669", "kind": "權", "dividend": 5185.0,
         "before_price": 7800.0, "reference_price": 2614.99, "open_price": 2615.0},
    ])
    events = pd.DataFrame([
        {"code": "6669", "period": "114年", "kind": "cash", "amount": 144.391545,
         "announce_date": "2026-06-04", "ex_date": "2026-06-22", "payment_date": "2026-07-17", "fiscal_year": 2025},
        {"code": "6669", "period": "114年", "kind": "stock", "amount": 19.827946,
         "announce_date": "2026-08-19", "ex_date": EX, "payment_date": None, "fiscal_year": 2025},
    ])
    fin = pd.DataFrame({
        "code": "6669", "year": [2025, 2025, 2025, 2026, 2026], "quarter": [2, 3, 4, 1, 2],
        "period_end": ["2025-06-30", "2025-09-30", "2025-12-31", "2026-03-31", "2026-06-30"],
        "announce_date": ["2025-08-14", "2025-11-14", "2026-03-31", "2026-05-15", "2026-08-14"],
        "eps": [65.23, 82.92, 74.21, 75.95, 80.43],
        "net_income": [1.212e10, 1.541e10, 1.379e10, 1.411e10, 1.4969e10],
        "revenue": [1.0] * 5, "gross_profit": [0.1] * 5, "operating_income": [0.1] * 5,
    })
    bal = pd.DataFrame([{"code": "6669", "year": 2026, "quarter": 2, "period_end": "2026-06-30",
                         "announce_date": "2026-08-14", "shares": 186856800.0,
                         "equity_parent": 1.3726e11, "bps": 734.59, "total_assets": 5.5e11}])
    return px, results, events, fin, bal


def test_配股率從參考價反推而不是股票股利除以十():
    px, res, ev, *_ = _wiwynn()
    a = F.corporate_actions(px, res, ev)
    r = a[a["date"] == EX].iloc[0]
    assert r["source"] == "dividend_results"
    assert r["share_ratio"] == pytest.approx(7800 / 2614.99 - 1, rel=1e-9)     # 1.9828
    assert r["price_factor"] == pytest.approx(2614.99 / 7800, rel=1e-9)
    assert a[a["date"] == "2026-06-22"].iloc[0]["share_ratio"] == 0.0           # 純除息不動股數


def test_面額不是十元時配股率照參考價():
    # 5314 世紀* 面額 0.5 元：每股 1.58 元股票股利＝每千股 3,157 股；÷10 會錯 20 倍
    d = _days("2026-07-01", 40)
    i = d.index("2026-08-14")
    px = _px("5314", d, [61.3] * i + [16.2] * (len(d) - i))
    res = pd.DataFrame([{"date": "2026-08-14", "code": "5314", "kind": "除權", "dividend": 46.55,
                         "before_price": 61.3, "reference_price": 14.75, "open_price": 14.75}])
    a = F.corporate_actions(px, res, None)
    assert a.iloc[0]["share_ratio"] == pytest.approx(3.156, abs=0.01)


def test_還原後沒有單日超過35趴的斷崖且今天收盤不變():
    px, res, ev, *_ = _wiwynn()
    a = F.corporate_actions(px, res, ev)
    adj = F.adjust_prices(px, a, "total")
    r = adj["close"].pct_change().dropna()
    assert r.abs().max() < F.CLIFF_RET
    assert adj["close"].iloc[-1] == px["close"].iloc[-1]                     # 報價顯示用的是真實價
    raw = px.set_index("date")["close"]
    ad = adj.set_index("date")["close"]
    last_pre = max(d for d in px["date"] if d < EX)
    assert ad[last_pre] == pytest.approx(raw[last_pre] * 2614.99 / 7800, rel=1e-9)
    # 除息日之前還要再乘上除息因子
    first = px["date"].iloc[0]
    assert ad[first] == pytest.approx(raw[first] * (2614.99 / 7800) * (4985.6 / 5130), rel=1e-9)


def test_只還原股數模式不動現金股利():
    px, res, ev, *_ = _wiwynn()
    a = F.corporate_actions(px, res, ev)
    adj = F.adjust_prices(px, a, "share").set_index("date")["close"]
    raw = px.set_index("date")["close"]
    first = px["date"].iloc[0]
    assert adj[first] == pytest.approx(raw[first] / (7800 / 2614.99), rel=1e-9)


def test_沒有官方資料的分割用漲跌幅區間推估():
    # 6949：停牌後 1490 → 67.1（面額 10 → 0.5，÷20），FinMind 當天漲跌給 0
    d = _days("2026-07-01", 30)
    closes = [1490.0] * 20 + [67.1, 60.4, 54.9] + [55.0] * 7
    ch = [0.0] * 20 + [0.0, -6.7, -5.5] + [0.0] * 7
    px = _px("6949", d, closes, change=ch)
    a = F.corporate_actions(px, None, None)
    assert len(a) == 1
    r = a.iloc[0]
    assert r["source"] == "inferred_ratio" and r["share_ratio"] == pytest.approx(19.0)
    adj = F.adjust_prices(px, a, "total")
    assert adj["close"].pct_change().abs().max() < F.CLIFF_RET


def test_分割用官方漲跌反推參考價():
    # 0052：245.3 → 35.35，漲跌 +0.31 → 參考價 35.04 ＝ 245.3 ÷ 7
    d = _days("2025-11-01", 20)
    closes = [245.3] * 10 + [35.35] * 10
    ch = [0.0] * 10 + [0.31] + [0.0] * 9
    a = F.corporate_actions(_px("0052", d, closes, change=ch), None, None)
    assert a.iloc[0]["source"] == "inferred_change"
    assert a.iloc[0]["price_factor"] == pytest.approx(35.04 / 245.3, rel=1e-6)


def test_上市前五天的暴漲不當成股本事件():
    d = _days("2026-09-01", 8)
    closes = [100, 210, 420, 700, 900, 950, 980, 990]    # 前 5 天無漲跌幅限制
    a = F.corporate_actions(_px("7856", d, closes), None, None)
    assert a.empty


def test_空資料與參考價錯誤():
    assert F.corporate_actions(pd.DataFrame(), pd.DataFrame(), pd.DataFrame()).empty
    bad = pd.DataFrame([{"date": "2026-01-05", "code": "1", "kind": "息", "dividend": 1,
                         "before_price": 10.0, "reference_price": 0.0, "open_price": 0}])
    assert F.corporate_actions(None, bad, None).empty                      # 參考價 0：不猜、不除以零
    px = _px("1", _days("2026-01-01", 5), [10] * 5)
    assert F.adjust_prices(px, pd.DataFrame(), "total").equals(px)


# ---------------------------------------------------------------- 本益比
def test_6669形狀本益比落在15到25而且不用單季乘四():
    px, res, ev, fin, bal = _wiwynn()
    sh = F.share_table(F.corporate_actions(px, res, ev))
    asof = px["date"].iloc[-1]
    t = F.ttm(fin, sh, asof)
    day = px[px["date"] == asof][["code", "close"]]
    v = F.valuation(day, t, F.latest_balance(bal, sh, asof)).iloc[0]
    assert t.iloc[0]["ttm_eps_raw"] == pytest.approx(82.92 + 74.21 + 75.95 + 80.43)
    assert 15 <= v["pe"] <= 25
    # 市值 ÷ 近四季淨利 應該跟 收盤 ÷ 調整後 EPS 對得上（兩種口徑互相驗證）
    ni = 1.541e10 + 1.379e10 + 1.411e10 + 1.4969e10
    assert v["market_cap"] / ni == pytest.approx(v["pe"], rel=0.02)
    # 沒有股數表 → 舊的錯誤數字（證明測試真的有鑑別力）
    v0 = F.valuation(day, F.ttm(fin), F.latest_balance(bal)).iloc[0]
    assert v0["pe"] < 8


def test_除權日前後本益比不可跳超過一點五倍():
    px, res, ev, fin, _ = _wiwynn()
    sh = F.share_table(F.corporate_actions(px, res, ev))
    d = S.pe_daily(px, fin, "6669", sh).set_index("date")
    before = d.loc[:EX].iloc[-2]["pe"]
    after = d.loc[EX]["pe"]
    assert 1 / 1.5 < after / before < 1.5
    # 整段逐日也不准有 1.5 倍以上的跳動
    s = d["pe"].dropna()
    assert (s / s.shift(1)).dropna().between(1 / 1.5, 1.5).all()
    # 沒還原時會跳（鑑別力）
    raw = S.pe_daily(px, fin, "6669", None).set_index("date")
    assert raw.loc[EX]["pe"] / raw.loc[:EX].iloc[-2]["pe"] < 1 / 1.5


def test_本益比歷史的EPS換到還原價基準河流圖才對得上():
    px, res, ev, fin, _ = _wiwynn()
    a = F.corporate_actions(px, res, ev)
    sh = F.share_table(a)
    adj = F.adjust_prices(px, a, "total")
    rows = S.pe_history(px, fin, "6669", shares=sh, adj_price=adj)
    last = rows[-1]
    assert last["pe"] is not None
    # 河流圖：還原收盤 ÷ ttm_eps 在最新一天就是真的本益比
    true_pe = px["close"].iloc[-1] / (sum([82.92, 74.21, 75.95, 80.43]) / (7800 / 2614.99))
    assert adj["close"].iloc[-1] / last["ttm_eps"] == pytest.approx(true_pe, rel=0.01)


def test_財報公布前已除權的季度不重複調整():
    # 5386 形狀：7/20 除權（每股配 0.5 股），8/14 才公布 Q2，Q2 EPS 已按新股本（隱含股數 ×1.5）
    tbl = F.share_table(pd.DataFrame([{"code": "5386", "date": "2026-07-20", "price_factor": 0.66,
                                       "share_ratio": 0.5, "source": "dividend_results"}]))
    g = pd.DataFrame({"year": [2026, 2026], "quarter": [1, 2],
                      "announce_date": ["2026-05-15", "2026-08-14"],
                      "eps": [43.05, 14.22], "net_income": [1.5534e9, 7.698e8]})
    div = F.eps_divisors(g, tbl, "5386", "2026-09-24")
    assert div == pytest.approx([1.5, 1.0])
    # 同樣的日期，但隱含股數沒變 → 還是舊股本，要調
    g2 = g.assign(net_income=[1.5534e9, 14.22 * 36080900])
    assert F.eps_divisors(g2, tbl, "5386", "2026-09-24") == pytest.approx([1.5, 1.5])
    # 缺淨利 → 日期規則：公布日之前除權視為已反映
    assert F.eps_divisors(g.drop(columns="net_income"), tbl, "5386", "2026-09-24") == pytest.approx([1.5, 1.0])


def test_虧損給NaN不給負數且股數調整不改變正負():
    px, res, ev, fin, bal = _wiwynn()
    fin = fin.assign(eps=-fin["eps"])
    sh = F.share_table(F.corporate_actions(px, res, ev))
    asof = px["date"].iloc[-1]
    v = F.valuation(px[px["date"] == asof][["code", "close"]], F.ttm(fin, sh, asof),
                    F.latest_balance(bal, sh, asof)).iloc[0]
    assert np.isnan(v["pe"]) and bool(v["is_loss"])



def test_近四季EPS相加的浮點殘差不當成正數():
    """2026-09-26 小數點普查抓到：3504 2026Q2 的本益比是 5.3e+18。
    四季 EPS 0.1＋(-0.3)＋0.2＋0.0 在浮點數下是 2.8e-17（不是 0），以前被當成「正的 TTM」拿去除。"""
    px, _, _, fin, _ = _wiwynn()
    fin = fin.assign(eps=[0.5, 0.1, -0.3, 0.2, 0.0])
    assert sum([0.1, -0.3, 0.2, 0.0]) > 0            # 前提：殘差真的是正的（證明這個測試有鑑別力）
    d = S.pe_daily(px, fin, "6669", None)
    last = d[d["period"] == "2026Q2"]
    assert len(last) and last["pe"].isna().all()
    rows = S.pe_history(px, fin, "6669")
    assert rows[-1]["period"] == "2026Q2" and rows[-1]["pe"] is None and rows[-1]["ttm_eps"] == 0
    # 同一個殘差在 valuation（產業地圖、個股基本面那一格本益比）也要當虧損
    asof = px["date"].iloc[-1]
    v = F.valuation(px[px["date"] == asof][["code", "close"]], F.ttm(fin, None, asof), None).iloc[0]
    assert np.isnan(v["pe"]) and bool(v["is_loss"])

# ---------------------------------------------------------------- 殖利率與股利欄
def test_殖利率用今天股數而且股利欄只放股利():
    px, res, ev, *_ = _wiwynn()
    sh = F.share_table(F.corporate_actions(px, res, ev))
    asof = px["date"].iloc[-1]
    close = float(px["close"].iloc[-1])
    d = S.dividends(ev, res, px, "6669", close, shares=sh, asof=asof)
    assert d["cash_ttm"] == pytest.approx(144.391545 / (7800 / 2614.99), rel=1e-3)   # 每股 48.4 元
    assert d["yield_ttm"] == pytest.approx(48.405 / close * 100, abs=0.02)
    row = next(r for r in d["results"] if r["date"] == EX)
    assert row["dividend"] == pytest.approx(19.8279, abs=1e-3)               # 不是 5,185 的價差
    assert row["stock_dividend"] == pytest.approx(19.8279, abs=1e-3)
    assert row["price_gap"] == pytest.approx(7800 - 2614.99, abs=0.01)
    d0 = S.dividends(ev, res, px, "6669", close)                              # 沒換算：舊的 10% 級錯誤
    assert d0["yield_ttm"] > 6


def test_年配息股除息日提前幾天不會把兩年的股利加在一起():
    # 6669 真實情況：2025-06-24 配 74 元、2026-06-22 配 144.39 元；
    # 舊版用「最後一次除息往回 365 天」，兩天之差把去年那筆也算進來（殖利率多算一年）
    ev = pd.DataFrame([
        {"code": "X", "period": "113年", "kind": "cash", "amount": 74.0, "announce_date": "2025-06-05",
         "ex_date": "2025-06-24", "payment_date": None, "fiscal_year": 2024},
        {"code": "X", "period": "114年", "kind": "cash", "amount": 144.39, "announce_date": "2026-06-04",
         "ex_date": "2026-06-22", "payment_date": None, "fiscal_year": 2025},
    ])
    assert S.dividends(ev, None, None, "X", 1000.0)["cash_ttm"] == pytest.approx(144.39)
    # 季配息：四次都在一年內，全部算進來
    q = pd.DataFrame([{"code": "Q", "period": f"114年第{i}季", "kind": "cash", "amount": 5.0,
                       "announce_date": None, "ex_date": d, "payment_date": None, "fiscal_year": 2025}
                      for i, d in enumerate(["2025-12-11", "2026-03-17", "2026-06-11", "2026-09-16"], 1)])
    assert S.dividends(q, None, None, "Q", 1000.0)["cash_ttm"] == pytest.approx(20.0)


def test_含權但對不到公告時股利留空不猜():
    res = pd.DataFrame([{"date": "2026-08-14", "code": "5314", "kind": "除權", "dividend": 46.55,
                         "before_price": 61.3, "reference_price": 14.75, "open_price": 14.75}])
    d = S.dividends(pd.DataFrame(), res, None, "5314", 26.4)
    assert d["results"][0]["dividend"] is None


# ---------------------------------------------------------------- 0 價 K 棒
def test_收盤為零的K棒被濾掉_局部零用收盤補():
    df = pd.DataFrame({"code": "6949", "date": ["2026-09-01", "2026-09-02", "2026-09-03"],
                       "open": [0.0, 0.0, 10.0], "high": [0.0, 12.0, 11.0], "low": [0.0, 0.0, 9.0],
                       "close": [0.0, 11.0, 10.5]})
    c = F.clean_price(df)
    assert list(c["date"]) == ["2026-09-02", "2026-09-03"]
    assert (c[["open", "high", "low", "close"]] > 0).all().all()
    r = c.iloc[0]
    assert r["low"] <= min(r["open"], r["close"]) and r["high"] >= max(r["open"], r["close"])
    assert F.clean_price(pd.DataFrame()).empty


# ---------------------------------------------------------------- 漲停統計排除新股
def test_漲停清單排除上市未滿五個交易日():
    from pipeline.build_payload import _new_listings, movers
    days = _days("2026-09-01", 20)
    old = _px("2330", days, list(np.linspace(100, 110, 19)) + [121.0])        # 最後一天漲停
    new = _px("7856", days[-3:], [2250.0, 4730.0, 5200.0])                  # 上市第 3 天
    price = pd.concat([old, new], ignore_index=True)
    latest = days[-1]
    company = pd.DataFrame({"code": ["2330", "7856"], "listed_date": ["1994-09-05", None]})
    nl = _new_listings(price, latest, company)
    assert nl == {"7856"}
    day = price[price["date"] == latest].assign(turnover=1.0)
    m = movers(day, {}, {}, [], new_listing=nl)
    assert [r["code"] for r in m["limit_up"]] == ["2330"]
    assert m["counts"]["limit_up"] == 1
    assert m["counts"]["up"] == 2                                            # 漲跌家數照算
    # 有上市日：以全市場交易日數計
    company2 = pd.DataFrame({"code": ["7856"], "listed_date": [days[-6]]})
    assert "7856" not in _new_listings(price, latest, company2)             # 第 6 天起有漲跌幅限制


# ---------------------------------------------------------------- 真實資料湖（有才跑）
DATA = Path(__file__).resolve().parent.parent / "data"


def _lake(table: str, codes: list[str]) -> pd.DataFrame:
    files = sorted((DATA / table).glob("year=*/part.parquet"))
    if not files:
        return pd.DataFrame()
    fr = [pd.read_parquet(f, filters=[("code", "in", codes)]) for f in files]
    return pd.concat(fr, ignore_index=True)


@pytest.mark.skipif(not (DATA / "price_daily").exists() or not (DATA / "dividend_results").exists(),
                    reason="沒有資料湖")
def test_真實資料_6669本益比落在15到25_6949與5314沒有斷崖():
    codes = ["6669", "6949", "5314"]
    px = F.clean_price(_lake("price_daily", codes))
    px = px[px["date"].astype(str) >= "2024-01-01"]
    if px[px["code"] == "6669"]["date"].max() < EX:
        pytest.skip("資料湖還沒有 6669 除權之後的價格")
    a = F.corporate_actions(px, _lake("dividend_results", codes), _lake("dividend_events", codes))
    adj = F.adjust_prices(px, a, "total").sort_values(["code", "date"])
    assert (adj[["open", "high", "low", "close"]] > 0).all().all()           # 無 0 價 K 棒
    adj["n"] = adj.groupby("code").cumcount()
    r = adj.groupby("code")["close"].pct_change()
    assert r[adj["n"] >= F.NEW_LISTING_DAYS].abs().max() < F.CLIFF_RET
    sh = F.share_table(a)
    asof = str(px["date"].max())
    fin = _lake("financial_q", ["6669"])
    last = px[(px["code"] == "6669")].sort_values("date").iloc[[-1]][["code", "close"]]
    v = F.valuation(last, F.ttm(fin, sh, asof)).iloc[0]
    assert 15 <= v["pe"] <= 25
