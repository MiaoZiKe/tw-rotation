"""季節性的兩個口徑（Andy 2026-09-19 圖三／圖十八）。

- **N9**「近三年就會只有到當前月份」：期間改成「最近 12×N 個**完整月**」滾動視窗。
  以前用日曆年切，近三年＝2024/2025/2026，而今年 9–12 月還沒發生，
  那四個月只有 2 個樣本、被 `n>=3` 門檻擋掉 → 整排留白。
- **N8**「超額 & 絕對報酬沒變化」：資料湖沒有夠長的大盤指數歷史
  （`index_ohlc` 只有 32 天、代號是 TSE 不是 TAIEX），超額報酬 312 格 0 格算得出來。
  改成指數覆蓋不足就用**全市場等權月報酬**當基準 —— 族群報酬本來就是等權算的，
  同口徑比較才有意義。
"""
from __future__ import annotations

import pandas as pd

from pipeline.compute import season


def _fake_price(months: int, codes=("1111", "2222"), start="2023-09"):
    """造出 `months` 個完整月的日收盤（每月兩天就夠算月報酬）。"""
    rows = []
    ym = pd.Period(start, freq="M")
    px = {c: 100.0 for c in codes}
    for i in range(months):
        for c in codes:
            d0 = ym.to_timestamp()
            d1 = ym.to_timestamp(how="end").normalize()
            rows.append({"date": d0.strftime("%Y-%m-%d"), "code": c, "close": px[c]})
            px[c] *= 1.0 + ((i % 5) - 2) / 100.0 + (0.003 if c == codes[0] else -0.003)
            rows.append({"date": d1.strftime("%Y-%m-%d"), "code": c, "close": px[c]})
        ym += 1
    return pd.DataFrame(rows)


def test_期間是最近12xN個完整月而不是日曆年(monkeypatch):
    """近三年要剛好 36 個完整月，不是「今年 1 月到現在」。"""
    codes = ("1111", "2222")
    monkeypatch.setattr(season.loader, "membership", lambda *a, **k: pd.DataFrame(
        [{"code": c, "group_id": "g1", "group_name": "測試族群"} for c in codes]))
    # 造 5 年的資料，最後一個完整月固定在 2026-08
    price = _fake_price(60, codes, start="2021-09")
    monkeypatch.setattr(pd.Timestamp, "today", staticmethod(lambda: pd.Timestamp("2026-09-19")))
    out = season.build(price, None)
    p3 = out["periods"]["3y"]
    assert p3["to"] == "2026-08"
    assert p3["from"] == "2023-09", f"近三年應該是滾動 36 個月，實際 {p3['from']}"
    # 12 個月每一格都要有樣本 —— 以前 9-12 月會留白
    months = {c["month"] for c in p3["cells"] if c["avg_return"] is not None}
    assert months == set(range(1, 13)), f"應該 12 個月都有值，缺 {sorted(set(range(1,13)) - months)}"


def test_沒有大盤指數時改用全市場等權當基準(monkeypatch):
    """這是 Andy 圖三「超額報酬沒變化」的根因：基準算不出來，超額就全空。"""
    codes = ("1111", "2222")
    monkeypatch.setattr(season.loader, "membership", lambda *a, **k: pd.DataFrame(
        [{"code": c, "group_id": "g1", "group_name": "測試族群"} for c in codes]))
    price = _fake_price(48, codes, start="2022-09")
    monkeypatch.setattr(pd.Timestamp, "today", staticmethod(lambda: pd.Timestamp("2026-09-19")))
    out = season.build(price, None)
    assert "全市場等權" in out["benchmark_source"], out["benchmark_source"]
    assert out["benchmark_months"] > 12, "基準要覆蓋整段歷史，不是只有十幾個月"
    # 超額報酬要真的算得出來（以前是 0 格）
    cells = out["periods"]["3y"]["cells"]
    got = [c for c in cells if c["avg_excess"] is not None]
    assert len(got) == len(cells), f"超額只有 {len(got)}/{len(cells)} 格算得出來"


def test_有夠長的大盤指數時就用指數(monkeypatch):
    """不要一律改用等權 —— 指數夠長就該用指數，那才是一般人講的「大盤」。"""
    codes = ("1111", "2222")
    monkeypatch.setattr(season.loader, "membership", lambda *a, **k: pd.DataFrame(
        [{"code": c, "group_id": "g1", "group_name": "測試族群"} for c in codes]))
    price = _fake_price(48, codes, start="2022-09")
    bench = _fake_price(48, ("TAIEX",), start="2022-09")
    monkeypatch.setattr(pd.Timestamp, "today", staticmethod(lambda: pd.Timestamp("2026-09-19")))
    out = season.build(pd.concat([price, bench], ignore_index=True), None)
    assert "TAIEX" in out["benchmark_source"], out["benchmark_source"]


def test_基準來源有寫進輸出讓畫面講得出來(monkeypatch):
    codes = ("1111",)
    monkeypatch.setattr(season.loader, "membership", lambda *a, **k: pd.DataFrame(
        [{"code": "1111", "group_id": "g1", "group_name": "測試族群"}]))
    monkeypatch.setattr(pd.Timestamp, "today", staticmethod(lambda: pd.Timestamp("2026-09-19")))
    out = season.build(_fake_price(40, codes, start="2023-05"), None)
    assert out.get("benchmark_source"), "畫面要講得出基準是什麼，不能只給一個數字"
    assert out["benchmark_source"] in out["note"], "note 裡也要寫，使用者才看得到"
