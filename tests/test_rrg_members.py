"""個股層級的 RRG（`rrg.member_rrg`）—— Andy 2026-09-21 的兩階段下鑽用的那一份。

這裡守住的是四件「錯了不會當掉、但畫面會騙人」的事：

1. **族群與個股必須是同一套算法。** 兩邊只要差一個窗口長度，同一張盤上就會
   出現兩種尺度（個股全部貼在盤緣、族群全部縮在圓心），而那是我們算出來的，
   不是市場長那樣。測法：讓某個族群的走勢和某一檔個股**完全一樣**，
   兩邊算出來的 (x, y) 就必須一樣。
2. **樣本不足的個股不可以輸出。** 上市未滿 RS_BASE+MOM_ROC 天的股票寧可不畫，
   也不要給 0 或 NaN（DECISIONS：樣本不足要標示，不可以假裝有值）。
3. **控量**：每個族群只取成交值前 N 檔，而且真的是「前 N 大」。
4. **空資料不爆**：這一支在管線裡是 try 包起來的，但回傳形狀仍要是對的。
"""
from __future__ import annotations

import pandas as pd

from pipeline.compute import rrg


def _price(n_days: int = 80) -> pd.DataFrame:
    """三檔股票的日線：2330 天天漲一點、2317 天天跌一點、9999 只有 5 天（樣本不足）。"""
    dates = pd.bdate_range("2026-05-01", periods=n_days).strftime("%Y-%m-%d").tolist()
    rows = []
    for i, d in enumerate(dates):
        rows.append({"date": d, "code": "2330", "close": 100 * (1.004 ** i),
                     "change": 100 * (1.004 ** i) * 0.004 / 1.004, "turnover": 9e9})
        rows.append({"date": d, "code": "2317", "close": 50 * (0.998 ** i),
                     "change": -50 * (0.998 ** i) * 0.002 / 0.998, "turnover": 3e9})
        if i >= n_days - 5:                      # 新掛牌：只有最後 5 天有資料
            rows.append({"date": d, "code": "9999", "close": 20.0,
                         "change": 0.1, "turnover": 1e9})
    return pd.DataFrame(rows)


def _gdetail() -> dict:
    return {"g1": {"group_name": "測試族群", "members": [
        {"code": "2330", "name": "台積電", "turnover": 9e9, "has_page": True},
        {"code": "2317", "name": "鴻海", "turnover": 3e9, "has_page": True},
        {"code": "9999", "name": "新股", "turnover": 1e9, "has_page": False},
    ]}}


def _points() -> list:
    return [{"group_id": "g1", "group_name": "測試族群"}]


def test_同一條走勢在族群與個股算出來的座標一致():
    """族群 g1 的 chg_pct 就照 2330 的日報酬寫，兩邊的 (x, y) 必須一模一樣。

    這是「後端只能有一套 RRG 算法」的釘子 —— 有人以後想替個股單獨調參數，
    這條會先紅。
    """
    px = _price()
    ret = (px[px["code"] == "2330"].assign(
        prev=lambda d: d["close"] - d["change"]).eval("change / prev") * 100)
    gh = pd.DataFrame({
        "date": px[px["code"] == "2330"]["date"].tolist(),
        "group_id": "g1", "group_name": "測試族群", "chain": "other",
        "chg_pct": ret.tolist(), "turnover": 9e9, "turnover_share": 60.0,
    })
    group_pt = rrg.rrg(gh, px)["points"][0]
    member = rrg.member_rrg(px, _gdetail(), _points())["g1"]
    me = [m for m in member if m["code"] == "2330"][0]
    # 兩邊都是「相對同一個大盤指數」，而且族群指數就是 2330 的指數 → 座標必須相等
    assert abs(me["x"] - group_pt["x"]) < 0.02, (me["x"], group_pt["x"])
    assert abs(me["y"] - group_pt["y"]) < 0.02, (me["y"], group_pt["y"])
    assert me["quadrant"] == group_pt["quadrant"]


def test_樣本不足的個股直接不輸出():
    """只有 5 天資料的 9999 不可以出現 —— 不是給它一個 0，是根本不給。"""
    out = rrg.member_rrg(_price(), _gdetail(), _points())
    codes = [m["code"] for m in out["g1"]]
    assert "9999" not in codes, codes
    assert set(codes) == {"2330", "2317"}
    assert all(m["x"] is not None and m["y"] is not None for m in out["g1"])


def test_每個族群只取成交值前N檔且照成交值排序():
    out = rrg.member_rrg(_price(), _gdetail(), _points(), top_n=1)
    assert [m["code"] for m in out["g1"]] == ["2330"]        # 成交值最大的那一檔
    out2 = rrg.member_rrg(_price(), _gdetail(), _points())
    tv = [m["turnover"] for m in out2["g1"]]
    assert tv == sorted(tv, reverse=True), tv


def test_佔比的分母是所屬族群():
    """前端在時鐘與資金去向上都寫「佔族群 X%」，分母錯了整欄都會騙人。"""
    out = rrg.member_rrg(_price(), _gdetail(), _points())
    by = {m["code"]: m for m in out["g1"]}
    # 分母是**有進到前 N 檔的那幾檔**的成交值合計（9e9 + 3e9 + 1e9）
    assert abs(by["2330"]["share"] - 9e9 / 13e9 * 100) < 0.05, by["2330"]["share"]
    assert abs(by["2317"]["share"] - 3e9 / 13e9 * 100) < 0.05, by["2317"]["share"]


def test_軌跡長度與空資料():
    out = rrg.member_rrg(_price(), _gdetail(), _points(), trail=31)
    tr = out["g1"][0]["trail"]
    assert 1 <= len(tr) <= 31 and len(tr[0]) == 3
    assert all(isinstance(t[0], str) for t in tr)            # [日期, x, y]
    # 空輸入一律回空 dict，不可以回 None（前端拿到 undefined 會整張圖空白）
    assert rrg.member_rrg(pd.DataFrame(), _gdetail(), _points()) == {}
    assert rrg.member_rrg(_price(), {}, _points()) == {}
    assert rrg.member_rrg(_price(), _gdetail(), []) == {}
