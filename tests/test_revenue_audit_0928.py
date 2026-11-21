"""月營收普查與防回歸（2026-09-28，金融專家；Andy：「營收走勢確保數值正常，檢查後續會不會還發生」）。

普查結果與逐檔原因在 docs/revenue_audit_0928.md。這支釘住三類事情：
1. 口徑（合成資料）：成長率分母 ≤ 0 不給、缺月補空列不補 0、同口徑基期（證交所附的去年同月）優先、
   累計要 1 月起連續；M2 的 revenue_momentum 同一套規則。
2. 偵測器本身會響（合成資料）：千元／元混用、年月錯位一個月、年月格式錯，revenue_audit 都要抓得到。
3. 資料湖現況（真資料）：年月格式、重複鍵、跨來源單位、年月錯位都必須是 0；
   「單月 1,000 倍跳動」只允許零星（建設交屋月、生技授權金是真的會這樣），
   **同一個月超過 3 檔就是系統性的單位錯**（例如 twse.py 的 thousand_scale 被拿掉，整個月一起放大）→ 紅。
"""
from __future__ import annotations

import glob
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import config  # noqa: E402
from pipeline.compute import fundamental as F  # noqa: E402
from pipeline.compute import stockpage  # noqa: E402
from pipeline.sources import twse  # noqa: E402


def _yms(y0, m0, n):
    out, y, m = [], y0, m0
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return out


def _rev(code, yms, vals, **extra):
    d = pd.DataFrame({"code": code, "ym": yms, "revenue": [float(v) for v in vals]})
    for k, v in extra.items():
        d[k] = v
    return d


# ------------------------------------------------------------------ 1. 口徑

def test_空資料與找不到代號回空結構():
    for rev in (None, pd.DataFrame(), _rev("A", ["2026-01"], [1.0])):
        out = stockpage.revenue_series(rev, "ZZZ")
        assert out["monthly"] == [] and out["yearly"] == [] and out["missing"] == []
        assert out["columns"][1] == "revenue"


def test_分母為負或零時成長率不給_不是正負號顛倒():
    # 證券商：去年同月 −3 億、上月 0、今年 +1 億 → 舊算法 YoY 給 −133%（看起來大衰退）
    rev = _rev("S", ["2025-06", "2026-05", "2026-06"], [-3e8, 0.0, 1e8])
    m = {r[0]: r for r in stockpage.revenue_series(rev, "S")["monthly"]}
    assert m["2026-06"][2] is None, "去年同月是負的 → YoY 沒有意義"
    assert m["2026-06"][3] is None, "上月是 0 → MoM 除以零，不給"
    assert m["2026-06"][6] == -3e8, "去年同期柱照實給（負的就是負的）"
    assert stockpage._pct(1, 0) is None and stockpage._pct(1, -2) is None and stockpage._pct(None, 3) is None
    assert stockpage._pct(3, 2) == pytest.approx(50.0)


def test_缺月補空列_營收是None不是0_月份連續():
    yms = ["2022-01", "2022-02", "2022-03", "2022-05", "2022-06"]
    out = stockpage.revenue_series(_rev("G", yms, [10, 11, 12, 14, 15]), "G")
    got = [r[0] for r in out["monthly"]]
    assert got == _yms(2022, 1, 6), "2022-04 要出現在序列裡，類別軸才不會把 3 月跟 5 月畫成相鄰"
    apr = out["monthly"][3]
    assert apr[1] is None and apr[2] is None and apr[3] is None and apr[4] is None, "缺月＝不知道，不是 0"
    assert out["monthly"][4][3] is None, "5 月的上個月缺 → MoM 不拿 3 月比"
    assert out["monthly"][4][4] is None, "4 月缺 → 5 月的累計不給"
    assert out["missing"] == ["2022-04"]
    assert out["yearly"][0]["months"] == 5 and 4 not in out["yearly"][0]["by_month"]


def test_官方同口徑去年同月優先_IFRS17重編():
    # 2025-07 資料湖（FinMind 舊口徑）36.9 億；2026-07 證交所附的去年當月（重編後）83.0 億
    rev = pd.concat([_rev("2882", ["2025-06", "2025-07"], [30e8, 36.9e8]),
                     _rev("2882", ["2026-06", "2026-07"], [24e8, 25.1e8],
                          revenue_last_year=[np.nan, 83.0e8], revenue_prev_month=[np.nan, 24.5e8])])
    m = {r[0]: r for r in stockpage.revenue_series(rev, "2882")["monthly"]}
    assert m["2026-07"][6] == 83.0e8, "去年同期用官方重編值"
    assert m["2026-07"][2] == pytest.approx(round(25.1 / 83.0 * 100 - 100, 1))
    assert m["2026-07"][3] == pytest.approx(round(25.1 / 24.5 * 100 - 100, 1)), "MoM 也用官方的上月"
    assert m["2026-06"][6] == 30e8, "沒有官方欄位的列照舊用資料湖"


def test_累計要從一月起連續_跨年歸零():
    yms = _yms(2025, 1, 15)
    vals = [100.0] * 12 + [110.0, 120.0, 130.0]
    m = {r[0]: r for r in stockpage.revenue_series(_rev("C", yms, vals), "C")["monthly"]}
    assert m["2026-03"][4] == 360.0
    assert m["2026-03"][5] == pytest.approx(20.0), "累計 YoY＝360 ÷ 300"
    assert m["2025-12"][4] == 1200.0


def test_M2營收動能_日曆月對齊_缺年不拿兩年前比():
    # 2025 整年缺：舊算法 groupby(month).shift(1) 會拿 2024 來當 2026 的「去年同月」
    yms = _yms(2024, 1, 12) + _yms(2026, 1, 12)
    vals = [100.0] * 12 + [150.0] * 12
    r = F.revenue_momentum(_rev("A", yms, vals)).iloc[0]
    assert np.isnan(r["yoy"]) and r["growth_streak"] == 0
    assert not np.isnan(r["mom"]) and r["mom"] == pytest.approx(0.0)
    assert np.isnan(r["ytd_yoy"]) and np.isnan(r["yoy_3m"])


def test_M2營收動能_負基期不算成長():
    yms = _yms(2025, 1, 24)
    vals = [-50.0] * 12 + [10.0] * 12
    r = F.revenue_momentum(_rev("S", yms, vals)).iloc[0]
    assert np.isnan(r["yoy"]), "去年同月是負的 → 不給 YoY"
    assert r["growth_streak"] == 0 and not r["flag_spike"]


def test_M2營收動能_缺一個月_連續年增在缺口停():
    yms = _yms(2025, 1, 24)
    vals = [100.0] * 12 + [120.0] * 12
    d = _rev("A", yms, vals)
    d = d[d["ym"] != "2026-06"]
    r = F.revenue_momentum(d).iloc[0]
    assert r["growth_streak"] == 6, "2026-07～12 共 6 個月；2026-06 缺，不跨過去接著數"


def test_指標標籤的連續年增也用正分母():
    yms = _yms(2025, 1, 20)
    vals = [-10.0] * 12 + [5.0] * 8
    t = {x["id"]: x for x in stockpage.stock_tags(_rev("S", yms, vals), None, "S")["items"]}
    assert t["rev_streak"]["hit"] is None, "去年同月全是負的 → 一個 YoY 都算不出來，不判斷"


# ------------------------------------------------------------------ 2. 偵測器會響

def test_普查抓得到單月忘了千元換元():
    yms = _yms(2024, 1, 12)
    vals = [5e8] * 12
    vals[6] = 5e8 / 1000                     # 2024-07 少乘 1000
    a = stockpage.revenue_audit(_rev("U", yms, vals))
    assert [x["ym"] for x in a["unit_jump"]] == ["2024-07"]


def test_普查抓得到跨來源單位不一致與年月錯位():
    base = _rev("X", _yms(2025, 1, 12), [float(1000 + 50 * i) * 1e6 for i in range(12)])
    # 證交所列的去年當月忘了換元（千元）→ 跟 FinMind 差 1000 倍
    tw = _rev("X", ["2026-01"], [1.5e9], revenue_last_year=[1000e6 / 1000], revenue_prev_month=[1500e6])
    a = stockpage.revenue_audit(pd.concat([base, tw]))
    assert [x["ym"] for x in a["cross_unit"]] == ["2026-01"]
    assert [x["ym"] for x in a["month_shift"]] == ["2026-01"], "官方上月＝資料湖的前兩個月 → 年月錯位一格"


def test_普查抓得到年月格式錯與重複鍵():
    d = _rev("Y", ["115-01", "2026-13", "2026-01", "2026-01"], [1, 2, 3, 4])
    a = stockpage.revenue_audit(d)
    assert {x["ym"] for x in a["bad_ym"]} == {"115-01", "2026-13"}
    assert a["dup_key"] == [{"code": "Y", "ym": "2026-01"}]
    assert stockpage.revenue_audit(None)["unit_jump"] == []


def test_證交所月營收解析一定把千元換成元(monkeypatch):
    raw = [{"資料年月": "11508", "公司代號": "2330", "公司名稱": "台積電", "產業別": "半導體業",
            "營業收入-當月營收": "335,772,262", "營業收入-上月營收": "323,166,000",
            "營業收入-去年當月營收": "250,866,000", "上月比較增減(%)": "3.9", "去年同月增減(%)": "33.8",
            "累計營業收入-當月累計": "2,400,000,000", "累計營業收入-去年累計": "1,800,000,000", "前期比較增減(%)": "33.3"}]
    monkeypatch.setattr(twse, "_fetch", lambda key: raw)
    d = twse.revenue_monthly()
    r = d.iloc[0]
    assert r["ym"] == "2026-08", "民國 115 年 8 月"
    assert r["revenue"] == pytest.approx(335_772_262_000.0), "千元 × 1000 ＝ 元（跟 FinMind 同單位）"
    assert r["revenue_last_year"] == pytest.approx(250_866_000_000.0)
    assert r["revenue_prev_month"] == pytest.approx(323_166_000_000.0)


# ------------------------------------------------------------------ 3. 資料湖現況

def _lake():
    files = sorted(glob.glob(str(config.DATA / "revenue_monthly" / "year=*" / "part.parquet")))
    if not files:
        pytest.skip("本機沒有 revenue_monthly 資料湖")
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)


def test_資料湖月營收_格式鍵值單位年月都乾淨():
    rev = _lake()
    a = stockpage.revenue_audit(rev)
    assert a["bad_ym"] == [], f"年月格式錯：{a['bad_ym'][:5]}"
    assert a["dup_key"] == [], f"同一檔同月兩列：{a['dup_key'][:5]}"
    assert a["cross_unit"] == [], f"證交所與 FinMind 單位差 1000 倍：{a['cross_unit'][:5]}"
    assert a["month_shift"] == [], f"年月錯位一個月：{a['month_shift'][:5]}"


def test_資料湖月營收_千倍跳動只准零星_同一個月超過三檔就是系統性單位錯():
    rev = _lake()
    a = stockpage.revenue_audit(rev)
    per_month = Counter(x["ym"] for x in a["unit_jump"])
    worst = per_month.most_common(1)
    assert not worst or worst[0][1] <= 3, f"{worst[0][0]} 有 {worst[0][1]} 檔同時跳 1000 倍 —— 那是單位錯，不是交屋"
    assert len(a["unit_jump"]) <= max(40, len(rev) * 0.0005), f"千倍跳動 {len(a['unit_jump'])} 列，比普查基準（28）暴增"


def test_資料湖每檔的個股頁營收序列_月份連續且缺月不是0():
    rev = _lake()
    rev = rev.assign(code=rev["code"].astype(str))
    bad = []
    for c, gg in rev.groupby("code"):
        out = stockpage.revenue_series(gg, c)
        mo = out["monthly"]
        mis = [int(r[0][:4]) * 12 + int(r[0][5:7]) for r in mo]
        if any(b - a != 1 for a, b in zip(mis, mis[1:])):
            bad.append((c, "月份不連續"))
        miss = set(out["missing"])
        if any(r[1] == 0 and r[0] in miss for r in mo):
            bad.append((c, "缺月被寫成 0"))
        if mo and mo[-1][1] is None:
            bad.append((c, "最後一列是空的"))
    assert bad == [], bad[:10]
