"""恐慌指數（臺指選擇權隱含波動率・本站自算）：公式、邊界、增量與回補游標（不碰網路）。

核心驗證：用 Black-Scholes 在「固定波動率 σ」下產生整條 TXO 價格鏈，CBOE 公式算回來的指數要 ≈ 100σ。
這是公式本身對不對的檢查（跟官方值比對是另一件事，見 DECISIONS）。"""
import math
from datetime import date

import numpy as np
import pandas as pd
import pytest

from pipeline import config
from pipeline.compute import ivx
from pipeline.sources import optivx


def _ncdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _bs(S, K, T, r, s, cp):
    d1 = (math.log(S / K) + (r + s * s / 2) * T) / (s * math.sqrt(T)); d2 = d1 - s * math.sqrt(T)
    if cp == "call":
        return S * _ncdf(d1) - K * math.exp(-r * T) * _ncdf(d2)
    return K * math.exp(-r * T) * _ncdf(-d2) - S * _ncdf(-d1)


def _chain(d, sigma=0.20, S=22000.0, yms=("202611", "202612", "202701"), step=100, width=0.35, tick=0.1, extra=()):
    rows = []
    dd = date.fromisoformat(d)
    for ym in yms:
        exp = ivx.third_wednesday(ym)
        T = ivx.minutes_to_expiry(dd, exp) / ivx.MIN_YEAR
        if T <= 0:
            continue
        for K in np.arange(S * (1 - width) // step * step, S * (1 + width), step):
            for cp in ("call", "put"):
                p = _bs(S, float(K), T, config.IVX_RATE, sigma, cp)
                p = round(p / tick) * tick
                rows.append(dict(date=d, option_id="TXO", contract_date=ym, strike_price=float(K), call_put=cp,
                                 settlement_price=p, close=p if p > 5 else 0, trading_session="position"))
    rows.extend(extra)
    return rows


def test_third_wednesday():
    assert ivx.third_wednesday("202611") == date(2026, 11, 18)
    assert ivx.third_wednesday("202401") == date(2024, 1, 17)
    assert ivx.third_wednesday("202405") == date(2024, 5, 15)


@pytest.mark.parametrize("sigma", [0.15, 0.25, 0.40])
def test_constant_vol_recovers_sigma(sigma):
    df = ivx.compute(_chain("2026-11-02", sigma=sigma))
    assert len(df) == 1
    v = float(df.iloc[0].ivx)
    assert abs(v - 100 * sigma) < 0.6, v            # 離散履約價＋0.1 跳動單位的截斷誤差
    r = df.iloc[0]
    assert r.near_ym == "202611" and r.next_ym == "202612"   # 近月剩 16 天，用近月＋次近月


def test_roll_when_near_under_min_days():
    assert ivx.compute(_chain("2026-11-13")).iloc[0].near_ym == "202611"   # 剩 5 天：還不換月
    df = ivx.compute(_chain("2026-11-16"))           # 近月 11/18 只剩 2 天（最後兩個交易日）→ 改用 12 月＋1 月
    r = df.iloc[0]
    assert r.near_ym == "202612" and r.next_ym == "202701"
    assert abs(r.ivx - 20) < 1.0


def test_weekly_after_market_and_zero_prices_ignored():
    junk = [dict(date="2026-11-02", option_id="TXO", contract_date="202611W2", strike_price=22000.0, call_put="call",
                 settlement_price=9999, close=9999, trading_session="position"),
            dict(date="2026-11-02", option_id="TXO", contract_date="202611", strike_price=22000.0, call_put="call",
                 settlement_price=9999, close=9999, trading_session="after_market")]
    a = float(ivx.compute(_chain("2026-11-02"))["ivx"].iloc[0])
    b = float(ivx.compute(_chain("2026-11-02", extra=junk))["ivx"].iloc[0])
    assert abs(a - b) < 1e-9                          # 週選與盤後一筆都不准混進來


def test_settlement_zero_falls_back_to_close():
    rows = _chain("2026-11-02")
    for r in rows:
        if r["strike_price"] == 21000.0 and r["call_put"] == "put" and r["contract_date"] == "202611":
            r["close"] = r["settlement_price"]; r["settlement_price"] = 0
    n = ivx.normalize(rows)
    p = n[(n.K == 21000.0) & (n.cp == "P") & (n.ym == "202611")]["price"].iloc[0]
    assert p > 0


def test_empty_and_insufficient():
    assert ivx.compute(None).empty and ivx.compute([]).empty
    assert ivx.compute([dict(foo=1)]).empty                       # 認不得欄位
    only_calls = [r for r in _chain("2026-11-02") if r["call_put"] == "call"]
    assert ivx.compute(only_calls).empty                           # 沒有賣權：不硬湊
    narrow = _chain("2026-11-02", width=0.004)                     # 每邊只剩 0～1 個價外履約價
    assert ivx.compute(narrow).empty
    one_month = _chain("2026-11-02", yms=("202611",))              # 只有一個月份：無法插補
    assert ivx.compute(one_month).empty


def test_term_variance_guards():
    assert ivx.term_variance(pd.DataFrame(), 0.1, 0.01) is None
    assert ivx.term_variance(pd.DataFrame({"K": [1.0], "cp": ["C"], "price": [1.0]}), 0.0, 0.01) is None   # T=0（除以零）


def _ivx_frame(vals, start="2024-01-01"):
    d = pd.bdate_range(start, periods=len(vals)).strftime("%Y-%m-%d")
    return pd.DataFrame({"date": d, "ivx": vals, "near_exp": "2024-01-17", "near_days": 10.0, "next_exp": "2024-02-21", "next_days": 45.0})


def test_percentile_no_lookahead():
    s = pd.Series([10.0, 20.0, 30.0, 5.0])
    p, n = ivx.percentile_series(s)
    assert list(n) == [1, 2, 3, 4]
    assert abs(p.iloc[2] - (2 + 0.5) / 3) < 1e-9 and p.iloc[3] == 0.125   # 第 3 天只看前 3 天；第 4 天的 5 不影響第 3 天
    p2, _ = ivx.percentile_series(pd.Series([11.0] * 10))
    assert p2.iloc[-1] == 0.5                                      # 全部同值＝中位，不是最高分位


def test_build_json_states_and_sample_size():
    vals = list(np.linspace(10, 30, 200)) + [12.0]
    j = ivx.build_json(_ivx_frame(vals), None)
    t = j["tw"]
    assert t["n_hist"] == 201 and t["state"] == "calm" and t["value"] == 12.0 and t["chg"] == round(12.0 - 30.0, 2)
    assert len(t["spark"]) == 60 and len(t["series"]) == 201 and j["us"] is None
    j2 = ivx.build_json(_ivx_frame(list(np.linspace(10, 30, 200)) + [29.0]), None)
    assert j2["tw"]["state"] == "panic"
    j3 = ivx.build_json(_ivx_frame(list(np.linspace(10, 30, 200)) + [21.0]), None)
    assert j3["tw"]["state"] == "alert"
    short = ivx.build_json(_ivx_frame([15.0, 16.0, 17.0]), None)["tw"]
    assert short["state"] is None and short["n_hist"] == 3        # 樣本不足：只給數字、不給標籤
    assert ivx.build_json(pd.DataFrame(), pd.DataFrame())["tw"] is None


def test_build_json_us_vix():
    intl = pd.DataFrame({"date": ["2026-11-03", "2026-11-04", "2026-11-04"], "symbol": ["^VIX", "^VIX", "^TWII"], "close": [18.0, 19.5, 23000]})
    u = ivx.build_json(None, intl)["us"]
    assert u["value"] == 19.5 and u["date"] == "2026-11-04" and u["chg"] == 1.5 and "芝加哥" in u["name"]


def test_daily_update_incremental():
    got = {}

    def fetch(a, b):
        got["a"], got["b"] = a, b
        return _chain("2026-11-05")
    df = optivx.daily_update(today=date(2026, 11, 6), fetch=fetch, last="2026-11-04")
    assert got == {"a": "2026-11-05", "b": "2026-11-06"} and len(df) == 1
    assert optivx.daily_update(today=date(2026, 11, 6), fetch=fetch, last="2026-11-06").empty   # 已是最新：不打 API


def test_backfill_cursor(monkeypatch):
    saved = []
    monkeypatch.setattr("pipeline.util.store.append", lambda t, df: len(df))
    prog = {"complete": {"opt_ivx": {"next": "2026-09-01"}}}
    calls = []

    def fetch(a, b):
        calls.append(a)
        return _chain(a[:8] + "03") if a != "2026-10-01" else []
    n = optivx.backfill(prog, lambda p: saved.append(dict(p["complete"]["opt_ivx"])), today=date(2026, 11, 6), fetch=fetch)
    assert calls == ["2026-09-01", "2026-10-01", "2026-11-01"] and n == 2
    f = prog["complete"]["opt_ivx"]
    assert f["next"] == "2026-11-01" and f["done"] is True
    assert optivx.backfill(prog, lambda p: None, today=date(2026, 11, 7), fetch=fetch) == 0   # 完成後交給每日增量


def test_backfill_quota_exhausted_keeps_cursor():
    prog = {"complete": {"opt_ivx": {"next": "2025-01-01"}}}
    assert optivx.backfill(prog, lambda p: None, today=date(2026, 11, 6), fetch=lambda a, b: None) == 0
    assert prog["complete"]["opt_ivx"]["next"] == "2025-01-01"
