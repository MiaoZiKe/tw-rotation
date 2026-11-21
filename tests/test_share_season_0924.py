"""2026-09-24 審查員抓到的兩個口徑錯誤。

1. **資金去向「% 佔上一層」超過 100%**：「其他產業別 → 半導體・其他」底下
   華邦電 475.4%（6/30）、647.3%（7/23）。根因兩層：
   - `rrg.sankey_daily()` 判斷「沒有人工族群、該進收容桶」時只看**排進前 top_groups 名**
     的族群；掛在較小人工族群的股票被誤塞進 ind_*，但族群成交值（`flow._attach_groups`）
     用的是完整 membership —— 分子有、分母沒有。
   - 雙掛股：族群成交值只算了它的 1/n，葉子卻送整檔成交值。
   這裡用真的 `flow.group_daily()` 算族群值，再用 `rrg.sankey_daily()` 算葉子，
   守住「每一層子節點加總 ≤ 父節點」。

2. **週期統計的「近 N 年」顯示成 N+1 年**：舊寫法數橫跨幾個日曆年。
   改成月數 ÷ 12（.5 進位）。
"""
from __future__ import annotations

import pandas as pd
import pytest

from pipeline.compute import flow, rrg, season

TOL = 1.005          # 容差 0.5%（浮點加總誤差用，不是放寬口徑）


# ---------------------------------------------------------------- 1. 資金去向
def _mem(rows):
    return pd.DataFrame([{"code": c, "group_id": g, "group_name": g.upper(),
                          "tier": "standalone", "chain": ch} for c, g, ch in rows])


# 一檔一列：code → (成交值, 法定產業別)
_STOCKS = {
    "2330": (1000.0, "半導體業"),     # 只在 A
    "2317": (400.0, "其他電子業"),    # 同時在 A 與 C → 各算 1/2
    "6666": (10.0, "電子零組件業"),   # 只在 C
    "2344": (20.0, "半導體業"),       # 只在 memory（小族群、排不進前 3）→ 舊版被誤塞進 ind_半導體業
    "5555": (30.0, "半導體業"),       # 沒有任何人工族群 → ind_半導體業
}
_MEM = _mem([("2330", "a", "semi"), ("2317", "a", "semi"), ("2317", "c", "ai"),
             ("6666", "c", "ai"), ("2344", "memory", "semi")])


def _price(dates=("2026-06-30", "2026-07-01")):
    rows = []
    for i, d in enumerate(dates):
        for code, (tv, _ind) in _STOCKS.items():
            rows.append({"date": d, "code": code, "name": "N" + code,
                         "turnover": tv * (1 + 0.1 * i), "close": 100.0, "change": 1.0})
    return pd.DataFrame(rows)


def _company():
    return pd.DataFrame([{"code": c, "industry": ind} for c, (_tv, ind) in _STOCKS.items()])


def _run(monkeypatch, top_groups=3, top_members=10):
    monkeypatch.setattr(flow.loader, "membership", lambda *a, **k: _MEM)
    px, comp = _price(), _company()
    gh = flow.group_daily(px, comp)
    out = rrg.sankey_daily(gh, px, _MEM, 60, top_groups=top_groups,
                           top_members=top_members, company=comp)
    return gh, out


def _sum_leaves(out):
    """{date: {gid: 葉子 tv 加總}}"""
    res = {}
    for d, rows in out["leaves"].items():
        for r in rows:
            res.setdefault(d, {}).setdefault(r["gid"], 0.0)
            res[d][r["gid"]] += r["tv"]
    return res


def test_小族群的股票不可以被塞進收容桶(monkeypatch):
    """華邦電那一型：掛在沒排進前 N 名的人工族群，就不是「沒有人工族群」。"""
    _gh, out = _run(monkeypatch)
    gids = [g["gid"] for g in out["groups"]]
    assert "memory" not in gids, f"前提：memory 要排不進前 3，實際 {gids}"
    assert "ind_半導體業" in gids, gids
    for d, rows in out["leaves"].items():
        codes = {r["code"] for r in rows if r["gid"] == "ind_半導體業"}
        assert "2344" not in codes, f"{d}：2344 有人工族群 memory，不該出現在收容桶 {codes}"
        assert "5555" in codes


def test_每天每族群的個股加總不超過族群成交值(monkeypatch):
    gh, out = _run(monkeypatch)
    di = {d: i for i, d in enumerate(out["dates"])}
    sums = _sum_leaves(out)
    assert sums, "要有葉子才驗得到東西"
    for g in out["groups"]:
        for d, i in di.items():
            gtv = g["tv"][i] or 0
            got = sums.get(d, {}).get(g["gid"], 0.0)
            assert got <= gtv * TOL, (
                f"{d} {g['gid']}：個股加總 {got:.2f} > 族群 {gtv:.2f}（{got / gtv * 100:.1f}%）")


def test_雙掛股的葉子只計1_n並附整檔成交值(monkeypatch):
    _gh, out = _run(monkeypatch)
    d = out["dates"][0]
    rows = [r for r in out["leaves"][d] if r["code"] == "2317"]
    assert {r["gid"] for r in rows} == {"a", "c"}
    for r in rows:
        assert r["n"] == 2
        assert r["tv_full"] == pytest.approx(400.0)
        assert r["tv"] == pytest.approx(200.0), "族群成交值只算了 1/2，葉子也只能 1/2"
    only = [r for r in out["leaves"][d] if r["code"] == "2330"][0]
    assert "tv_full" not in only and "n" not in only, "單掛股不送多餘欄位"


def test_每一層子節點加總不超過父節點(monkeypatch):
    """台股成交值 ≥ Σ 產業鏈 ＝ Σ 族群 ≥ Σ 個股。"""
    gh, out = _run(monkeypatch, top_groups=18)
    di = {d: i for i, d in enumerate(out["dates"])}
    root = gh.groupby("date")["turnover"].sum()
    sums = _sum_leaves(out)
    for d, i in di.items():
        chains: dict[str, float] = {}
        for g in out["groups"]:
            chains[g["chain_name"]] = chains.get(g["chain_name"], 0.0) + (g["tv"][i] or 0)
        assert sum(chains.values()) <= float(root[d]) * TOL, d
        # 族群加總等於全市場（這組資料每一檔都有歸屬，而且 18 名涵蓋了全部族群）
        assert sum(chains.values()) == pytest.approx(float(root[d]))
        for g in out["groups"]:
            assert sums.get(d, {}).get(g["gid"], 0.0) <= (g["tv"][i] or 0) * TOL


def test_族群成交值為零或缺值時不爆(monkeypatch):
    """邊界：當天某族群沒有量 —— 葉子也不能憑空長出正值。"""
    monkeypatch.setattr(flow.loader, "membership", lambda *a, **k: _MEM)
    px = _price(("2026-06-30",))
    px.loc[px["code"] == "6666", "turnover"] = 0.0
    px.loc[px["code"] == "2317", "turnover"] = float("nan")
    comp = _company()
    gh = flow.group_daily(px, comp)
    out = rrg.sankey_daily(gh, px, _MEM, 60, top_groups=18, top_members=10, company=comp)
    c = [g for g in out["groups"] if g["gid"] == "c"][0]
    assert (c["tv"][0] or 0) == 0
    assert all(r["tv"] == 0 for r in out["leaves"]["2026-06-30"] if r["gid"] == "c")


# ---------------------------------------------------------------- 2. 週期統計的年數
@pytest.mark.parametrize("first,last,months,years", [
    ("2023-09", "2026-08", 36, 3),      # 近 3 年：橫跨 4 個日曆年，但只有 3 年
    ("2021-09", "2026-08", 60, 5),
    ("2016-09", "2026-08", 120, 10),
    ("2015-04", "2026-08", 137, 11),    # 11.42 → 11
    ("2015-03", "2026-08", 138, 12),    # 11.5 → 12（.5 進位，不是銀行家捨入）
    ("2026-03", "2026-08", 6, 1),       # 半年進位
    ("2026-04", "2026-08", 5, 0),
    ("2026-08", "2026-08", 1, 0),
])
def test_年數是月數除以12四捨五入(first, last, months, years):
    assert season.span_months(first, last) == months
    assert season.span_years(first, last) == years


def test_年數_空值回0():
    assert season.span_months(None, "2026-08") == 0
    assert season.span_years(None, None) == 0
    assert season.span_years(pd.NaT, pd.NaT) == 0


def _fake_price(months, codes, start):
    rows, ym = [], pd.Period(start, freq="M")
    px = {c: 100.0 for c in codes}
    for i in range(months):
        for c in codes:
            rows.append({"date": ym.to_timestamp().strftime("%Y-%m-%d"), "code": c, "close": px[c]})
            px[c] *= 1.0 + ((i % 5) - 2) / 100.0
            rows.append({"date": ym.to_timestamp(how="end").normalize().strftime("%Y-%m-%d"),
                         "code": c, "close": px[c]})
        ym += 1
    return pd.DataFrame(rows)


def test_近N年顯示N年而且大盤對照用同一段(monkeypatch):
    codes = ("1111", "2222")
    monkeypatch.setattr(season.loader, "membership", lambda *a, **k: pd.DataFrame(
        [{"code": c, "group_id": "g1", "group_name": "測試族群"} for c in codes]))
    monkeypatch.setattr(pd.Timestamp, "today", staticmethod(lambda: pd.Timestamp("2026-09-19")))
    # 138 個月價格 → 137 個月報酬（2015-04～2026-08）
    price = pd.concat([_fake_price(138, codes, "2015-03"),
                       _fake_price(138, ("TAIEX",), "2015-03")], ignore_index=True)
    out = season.build(price, None)
    P = out["periods"]
    assert P["10y"]["years"] == 10 and P["10y"]["months"] == 120, P["10y"]["years"]
    assert P["5y"]["years"] == 5 and P["5y"]["months"] == 60
    assert P["3y"]["years"] == 3 and P["3y"]["months"] == 36, "舊版會算成 4（橫跨 2023～2026）"
    assert P["all"]["months"] == 137 and P["all"]["years"] == 11
    # 大盤對照：近 3 年每個月剛好 3 個樣本（以前日曆年切法，9–12 月只有 2 個）
    b3 = [r for r in out["benchmark"] if r["period"] == "3y"]
    assert len(b3) == 12 and all(r["samples"] == 3 for r in b3), b3
