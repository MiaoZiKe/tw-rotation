"""漲跌停判定（2026-10-05）：價格＝漲停價／跌停價，不是 ±9.5% 門檻。

Andy 拿券商 App 對 10/02 名單：舊版把 00715L 期街口布蘭特正2（ETF，+11.33%）列進漲停、
把 3163 波若威（+9.52%，收 713、漲停價 716，沒鎖住）也算漲停；跌停多算 6236 中湛（收 16.9、跌停價 16.85）。
下面幾條把這三檔的真實數字釘住。"""
import pandas as pd
import pytest

from pipeline.build_payload import limit_flags, movers
from pipeline.util.roc import is_common_stock, limit_down_price, limit_up_price, tw_tick


@pytest.mark.parametrize("p,t", [(9.99, 0.01), (10, 0.05), (49.95, 0.05), (50, 0.1), (99.9, 0.1),
                                 (100, 0.5), (499.5, 0.5), (500, 1.0), (999, 1.0), (1000, 5.0)])
def test_升降單位(p, t):
    assert tw_tick(p) == t


@pytest.mark.parametrize("prev,up,down", [
    (651.0, 716.0, 586.0),      # 3163 波若威 10/02：651×1.1＝716.1 → 1 元 tick 向下 716
    (18.7, 20.55, 16.85),       # 6236 中湛：20.57 → 20.55；16.83 → 16.85（向上）
    (110.0, 121.0, 99.0),       # 剛好落在 tick 上，不可以被浮點 floor 掉一格
    (50.0, 55.0, 45.0),
    (9.1, 10.0, 8.19),          # 跨價位：10.01 屬 10~50（0.05）→ 10.00
    (950.0, 1045.0, 855.0),     # 1045 屬 ≥1000（5 元）
    (5.55, 6.1, 5.0),           # 6.105 → 6.10；4.995 → 5.00
])
def test_漲跌停價(prev, up, down):
    assert limit_up_price(prev) == pytest.approx(up)
    assert limit_down_price(prev) == pytest.approx(down)


def test_只認普通股():
    assert is_common_stock("2330")
    assert not is_common_stock("0050")      # ETF
    assert not is_common_stock("00715L")    # 槓桿 ETF
    assert not is_common_stock("030123")    # 權證
    assert not is_common_stock("2881A")     # 特別股


def _day():
    # 10/02 真實收盤與漲跌（price_daily）
    return pd.DataFrame({
        "code": ["4716", "3163", "00715L", "6236", "4154", "2330"],
        "close": [None, 713.0, 70.75, 16.9, 39.15, 1000.0],
        "change": [None, 62.0, 7.2, -1.8, -4.35, 10.0],
        "turnover": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
    }).assign(close=lambda d: d["close"].fillna(0.0), change=lambda d: d["change"].fillna(0.0))


def test_limit_flags_用漲停價判定():
    d = _day()
    # 4154 樂威科：昨收 43.5 → 跌停 39.15（鎖跌停）
    f = limit_flags(d)
    assert f.get("4154") == -1
    assert "3163" not in f          # +9.52% 但收 713 ≠ 716
    assert "6236" not in f          # -9.63% 但收 16.9 ≠ 16.85
    assert "00715L" not in f        # ETF 不列漲停
    assert "2330" not in f


def test_movers_漲停跌停與前段排除ETF():
    d = pd.DataFrame({
        "code": ["1459", "3163", "00715L", "4154", "6236"],
        "close": [11.0, 713.0, 70.75, 39.15, 16.9],
        "change": [1.0, 62.0, 7.2, -4.35, -1.8],       # 1459：10→11 鎖漲停
        "turnover": [1.0] * 5,
    })
    m = movers(d, {}, {}, [])
    assert [r["code"] for r in m["limit_up"]] == ["1459"]
    assert [r["code"] for r in m["limit_down"]] == ["4154"]
    assert m["counts"]["limit_up"] == 1 and m["counts"]["limit_down"] == 1
    assert "00715L" not in [r["code"] for r in m["up"]]          # >10% 而且不是普通股：不進漲幅前段
    assert m["counts"]["up"] == 3                                # 家數口徑不變（含 ETF）


def test_新股不算漲停():
    d = pd.DataFrame({"code": ["7856"], "close": [11.0], "change": [1.0], "turnover": [1.0]})
    assert limit_flags(d, {"7856"}) == {}


def test_總覽漲跌分佈兩端改用新漲停判定():
    from pipeline.compute import flow
    assert flow.updown_bin(9.52, 9.5, lim=0) == 9      # 3163 沒鎖住 → >5 那格
    assert flow.updown_bin(9.68, 9.5, lim=1) == 10     # 鎖漲停
    assert flow.updown_bin(11.33, 9.5, lim=0) == 9     # ETF 不算漲停
    assert flow.updown_bin(-9.63, 9.5, lim=0) == 1
    assert flow.updown_bin(-9.9, 9.5, lim=-1) == 0
    assert flow.updown_bin(9.6, 9.5) == 10             # 沒給 lim 照舊
    d = flow.updown_distribution([{"chg_pct": 9.6, "ud": 9, "market": "TWSE"}])
    assert d["all"]["counts"][9] == 1 and d["all"]["counts"][10] == 0
