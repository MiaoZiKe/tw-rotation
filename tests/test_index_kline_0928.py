"""總覽大盤 K 線 2026-09-28（Andy：「櫃買 4H 1H…加權指數的成交量 15min 30min 1H…」）。

擋住四件事，全部用假資料、不打真 API：
1. 加權真實 1 分 K：FinMind 每 5 秒指數＋每 5 秒成交統計合成（09:00:00 那筆是昨收要丟、累計差分、單位千元）。
2. Yahoo 指數分 K 的缺口「每個指數各算各的」—— 以前整個 interval 取一個最後一根，櫃買永遠補不回歷史。
3. intraday_bars：同一盤 finmind 優先於 mis、指數量換成「元」、src 帶 vol_first／vol_unit、1H 保留 ≥ 3800 根。
4. 加權真實 1 分 K 的增量：湖裡有的那天不再抓；回補遇到「沒權限」記下來不再重試、每輪有上限。
"""
from __future__ import annotations

import pandas as pd

from pipeline.compute import intraday_bars as ib
from pipeline.sources import finmind, yahoo


# ------------------------------------------------------------ 1. 5 秒 → 1 分 K
def _px(day="2026-09-24"):
    # 09:00:00＝昨收 100（要丟）；09:00:05～09:01:00 屬 09:00 那根；09:01:05～09:02:00 屬 09:01；13:30:00 歸 13:29
    rows = [("09:00:00", 100.0), ("09:00:05", 101.0), ("09:00:30", 103.0), ("09:01:00", 102.0),
            ("09:01:05", 99.0), ("09:02:00", 98.0), ("09:02:05", 98.5), ("13:29:55", 97.0), ("13:30:00", 96.0)]
    return [{"date": f"{day} {t}", "TAIEX": v} for t, v in rows]


def _tr(day="2026-09-24"):
    # 累計成交金額（百萬元）；09:02:00 故意比 09:01:05 少一點（上游校正）→ 不准變負量
    rows = [("09:00:00", 0), ("09:00:05", 50), ("09:01:00", 120), ("09:01:05", 130), ("09:02:00", 125),
            ("09:02:05", 110),
            ("13:29:55", 700), ("13:30:00", 736)]
    return [{"date": day, "Time": t, "TotalDealMoney": v} for t, v in rows]


def test_tse_minute_from_5s_bars_and_money():
    out = finmind.tse_minute_from_5s(_px(), _tr(), "2026-09-24")
    assert list(out["src"].unique()) == ["finmind"] and list(out["symbol"].unique()) == ["TSE"]
    b = out.set_index("ts")
    k0 = "2026-09-24T09:00:00+08:00"
    assert b.loc[k0, "open"] == 101.0          # 09:00:00 的昨收沒有被當成開盤
    assert b.loc[k0, "high"] == 103.0 and b.loc[k0, "low"] == 101.0 and b.loc[k0, "close"] == 102.0
    assert b.loc[k0, "volume"] == 120 * 1000   # 百萬元 → 千元（湖的口徑）
    k1 = "2026-09-24T09:01:00+08:00"
    assert b.loc[k1, "volume"] == 5 * 1000     # 09:01 那根＝該分鐘最後一筆累計 125 − 上一分鐘 120
    k2 = "2026-09-24T09:02:00+08:00"
    assert b.loc[k2, "volume"] == 0            # 累計回頭到 110：取累積最大值，不變成負量
    k_last = "2026-09-24T13:29:00+08:00"
    assert b.loc[k_last, "close"] == 96.0      # 13:30:00 收盤那筆歸最後一根
    assert (out["volume"] >= 0).all()
    # 每分鐘成交金額加總＝收盤時的累計（真實值的差分，不是估）
    assert out["volume"].sum() == 736 * 1000


def test_tse_minute_bad_columns_or_empty(monkeypatch):
    assert finmind.tse_minute_from_5s([{"x": 1}], _tr(), "2026-09-24").empty
    from pipeline.util import http
    calls = []
    monkeypatch.setattr(http, "finmind_get", lambda ds, **k: calls.append(ds) or ([] if ds == finmind.TSE_5S_TRADE else _px()))
    monkeypatch.setattr(http, "finmind_last_error", lambda *a, **k: None)
    assert finmind.tse_minute_bars("2026-09-24").empty      # 成交統計拿不到 → 整天不給（不拿沒量的 K 棒充數）
    assert calls == [finmind.TSE_5S_PRICE, finmind.TSE_5S_TRADE]


# ------------------------------------------------------------ 2. Yahoo 缺口每個指數各算
def test_index_intraday_since_per_symbol_gap(monkeypatch):
    now = pd.Timestamp.now(tz="Asia/Taipei").normalize()
    recent = (now - pd.Timedelta(days=1) + pd.Timedelta(hours=9)).isoformat()
    have = pd.DataFrame({"ts": [recent], "symbol": ["TSE"], "interval": ["60m"]})
    asked = {}

    def fake(interval, period, symbols=None):
        asked["period"] = period
        old = (now - pd.Timedelta(days=400) + pd.Timedelta(hours=9)).isoformat()
        return pd.DataFrame({"ts": [old, recent, old], "symbol": ["TSE", "TSE", "OTC"], "interval": "60m",
                             "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 0.0})
    monkeypatch.setattr(yahoo, "index_intraday", fake)
    out = yahoo.index_intraday_since(have, "60m")
    # 櫃買湖裡一根都沒有 → 缺口＝保留上限（730 天），不是跟著加權只要一兩天
    assert asked["period"] == yahoo.period_for(int(str(yahoo.INTRADAY_MAX_PERIOD["60m"]).rstrip("d")), "60m")
    # 加權：湖裡已有的（≤ 最後一根）丟掉；櫃買：全部留下
    assert out.groupby("symbol").size().to_dict() == {"OTC": 1}


def test_otc_yahoo_symbol_is_ix0043():
    assert yahoo.INDEX_CANDIDATES["OTC"][0] == "IX0043.TWO"


# ------------------------------------------------------------ 3. intraday_bars 合成
def _rows(day, times, symbol, interval, src, vol):
    out = []
    for i, t in enumerate(times):
        ts = pd.Timestamp(f"{day} {t}").tz_localize("Asia/Taipei").isoformat()
        out.append({"ts": ts, "symbol": symbol, "interval": interval, "open": 100.0 + i, "high": 101.0 + i,
                    "low": 99.0 + i, "close": 100.5 + i, "volume": vol, "src": src})
    return out


def test_build_prefers_finmind_and_money_in_yuan():
    mins = [f"{h:02d}:{m:02d}" for h in range(9, 14) for m in range(0, 60) if (h, m) < (13, 30)]
    lake = pd.DataFrame(
        _rows("2026-09-23", ["09:00", "10:00", "11:00", "12:00", "13:00"], "TSE", "60m", None, 0.0)   # Yahoo：量 0
        + _rows("2026-09-24", ["09:00", "10:00", "11:00", "12:00", "13:00"], "TSE", "60m", None, 0.0)
        + _rows("2026-09-24", mins, "TSE", "1m", "finmind", 2000.0)                                     # 千元
        + _rows("2026-09-24", mins, "TSE", "1m", "mis", 999.0)
        + _rows("2026-09-24", ["09:00", "10:00"], "OTC", "60m", None, 0.0)
        + _rows("2026-09-24", ["09:00", "09:01"], "FUT", "1m", "taifex", 7.0))
    out = ib.build(lake)
    tse = out["TSE"]
    h1 = {b[0]: b for b in tse["H1"]}
    t924 = int((pd.Timestamp("2026-09-24 09:00") - pd.Timestamp("1970-01-01")).total_seconds())
    assert h1[t924][5] == 60 * 2000.0 * 1000       # 用 finmind（不是 mis 999），千元 → 元
    t923 = t924 - 86400
    assert h1[t923][5] == 0                         # Yahoo 那天照實 0，不估
    s = tse["src"]
    assert s["vol_unit"] == "yuan" and s["finmind_first"] == "2026-09-24" and s["finmind_days"] == 1
    assert s["vol_first"] == "2026-09-24" and s["vol_days"] == 1
    assert out["FUT"]["src"]["vol_unit"] == "lots"
    assert out["FUT"]["M15"][0][5] == 14.0          # 台指期口數不乘 1000
    assert len(out["OTC"]["H1"]) == 2               # 櫃買 Yahoo 60 分 K 有進來
    assert ib.H1_TAIL >= 3650                       # 兩年 60 分 K（≈725 盤 × 5 根）不會被切掉


# ------------------------------------------------------------ 4. 增量與回補
def test_tse_minute_todo_skips_days_in_lake():
    from pipeline import run_daily
    ohlc = pd.DataFrame({"date": ["2026-09-22", "2026-09-23", "2026-09-24", "2026-09-24"],
                         "symbol": ["TSE", "TSE", "TSE", "OTC"]})
    have = pd.DataFrame({"ts": ["2026-09-23T09:00:00+08:00", "2026-09-24T09:00:00+08:00"],
                         "symbol": ["TSE", "TSE"], "src": ["finmind", "mis"]})
    # 09-23 已有 finmind → 不抓；09-24 只有 mis → 還要抓（mis 沒有真實高低、也可能缺頭尾）；新的在前
    assert run_daily.tse_minute_todo(have, ohlc, 10) == ["2026-09-24", "2026-09-22"]
    assert run_daily.tse_minute_todo(have, ohlc, 1) == ["2026-09-24"]


def test_backfill_tse_minute_denied_and_cap(monkeypatch):
    from pipeline import run_backfill
    from pipeline.util import http, store
    today = pd.Timestamp.now(tz="Asia/Taipei").normalize()
    days = [(today - pd.Timedelta(days=i)).strftime("%Y-%m-%d") for i in range(1, 200)]
    ohlc = pd.DataFrame({"date": days, "symbol": ["TSE"] * len(days)})
    monkeypatch.setattr(store, "read", lambda t: ohlc if t == "index_ohlc" else pd.DataFrame())
    monkeypatch.setattr(http, "finmind_budget_left", lambda: 5000)
    appended = []
    monkeypatch.setattr(store, "append", lambda t, df: appended.append(len(df)))

    # 有資料：每輪最多 TSE_MINUTE_PER_RUN 天，剩下的下一輪接
    one = finmind.tse_minute_from_5s(_px(), _tr(), "2026-09-24")
    monkeypatch.setattr(finmind, "tse_minute_bars", lambda d, **k: one)
    flag = {}
    assert run_backfill._backfill_tse_minute(flag, pd.DataFrame()) is False
    assert len(appended) == run_backfill.TSE_MINUTE_PER_RUN
    assert flag["tse1m_left"] == len(days) - run_backfill.TSE_MINUTE_PER_RUN

    # 沒權限：記下來、算完成，之後不再打
    monkeypatch.setattr(finmind, "tse_minute_bars", lambda d, **k: pd.DataFrame())
    monkeypatch.setattr(http, "finmind_last_error",
                        lambda *a, **k: {"dataset": finmind.TSE_5S_PRICE, "status": 400, "msg": "Your level is register"})
    flag = {}
    assert run_backfill._backfill_tse_minute(flag, pd.DataFrame()) is True
    assert flag.get("tse1m_unavailable")
    called = []
    monkeypatch.setattr(finmind, "tse_minute_bars", lambda d, **k: called.append(d) or pd.DataFrame())
    assert run_backfill._backfill_tse_minute(flag, pd.DataFrame()) is True and not called


def test_minute_money_by_day_only_finmind():
    from pipeline import build_payload
    lake = pd.DataFrame({"ts": ["2026-09-24T09:00:00+08:00", "2026-09-24T09:01:00+08:00", "2026-09-24T09:00:00+08:00"],
                         "symbol": ["TSE", "TSE", "TSE"], "interval": ["1m", "1m", "1m"],
                         "volume": [1000.0, 2000.0, 999999.0], "src": ["finmind", "finmind", "mis"]})
    assert build_payload._minute_money_by_day(lake) == {("TSE", "2026-09-24"): 3_000_000.0}
    assert build_payload._minute_money_by_day(pd.DataFrame()) == {}
