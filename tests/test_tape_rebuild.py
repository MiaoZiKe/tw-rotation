"""tape_5m 缺口的替代來源重建（Yahoo 5 分 K ＋ 證交所日收）。全部用假資料，不打 Yahoo。

守住的事：
1. 格對齊：Yahoo 棒起點 + 5 分 ＝ tape 格；09:00 量 0；13:30、13:35 用證交所收盤價。
2. 量：形狀來自 Yahoo、總量錨在證交所日量（不直接用 Yahoo 量），累計只增不減。
3. src 標 rebuild:yahoo5m，欄位與原始 tape 一致，才能走同一張表。
4. 寧缺勿造：沒 Yahoo 資料／沒官方日量的代號不寫列。
5. 只增不改：湖裡該日已收齊（原始資料）就不重建。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from pipeline import config
from pipeline.sources import tape, tape_rebuild as rb
from pipeline.util import store

TPE = timezone(timedelta(hours=8))


def bars():
    ts = ["2026-10-28T09:00:00+08:00", "2026-10-28T09:05:00+08:00", "2026-10-28T13:20:00+08:00"]
    return pd.DataFrame({"ts": ts * 2, "code": ["2330"] * 3 + ["9999"] * 3,
                         "open": [100.0, 101, 103] * 2, "close": [101.0, 102, 103.5] * 2,
                         "volume": [1000.0, 1000, 2000] * 2})


def official():
    return pd.DataFrame({"code": ["2330"], "close": [104.0], "volume": [8_000_000.0]})   # 9999 沒有官方日量


def test_格對齊與量錨定():
    df = rb.build_day("2026-10-28", bars(), official(), {"2330": 99.0})
    assert set(df.code) == {"2330"}                                  # 9999 沒官方日量 → 略過
    assert list(df.ts.str[11:16]) == ["09:00", "09:05", "09:10", "13:25", "13:30", "13:35"]
    assert list(df.columns) == tape.COLUMNS
    assert (df.src == "rebuild:yahoo5m").all() and (df.val_src == "est").all()
    assert df.price.iloc[0] == 100.0                                 # 09:00 ＝ 第一根開盤
    assert df.cum_lots.iloc[0] == 0
    assert df.price.iloc[-1] == 104.0 and df.price.iloc[-2] == 104.0  # 13:30、13:35 ＝ 證交所收盤
    final = 8_000_000 / 1000 * rb.VOL_FINAL
    assert abs(df.cum_lots.iloc[-1] - final) < 0.01
    assert abs(df.cum_lots.iloc[3] - final * rb.VOL_AT_1325) < 0.5   # 13:25 ＝ 最終的 94.5%
    assert (df.prev_close == 99.0).all()


def test_累計量與成交值單調不減():
    df = rb.build_day("2026-10-28", bars(), official(), {})
    assert df.cum_lots.is_monotonic_increasing and df.cum_value.is_monotonic_increasing
    assert df.cum_value.iloc[-1] > 0


def test_Yahoo量全0或沒資料寧缺勿造():
    z = bars().assign(volume=0.0)
    assert rb.build_day("2026-10-28", z, official(), {}).empty
    assert rb.build_day("2026-10-28", pd.DataFrame(), official(), {}).empty
    assert rb.build_day("2026-10-28", bars(), pd.DataFrame(), {}).empty


def test_collect_Worker沒有且超過兩天就用重建補(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DATA", tmp_path)
    monkeypatch.setattr(store.config, "DATA", tmp_path, raising=False)
    now = datetime(2026, 10, 30, 14, 10, tzinfo=TPE)                # 10-28 距今 2 天
    monkeypatch.setattr(tape, "fetch_day", lambda d8: pd.DataFrame(columns=tape.COLUMNS))
    monkeypatch.setattr(tape, "lake_calendar", lambda n: ({"20261028", "20261029", "20261030"}, set()))
    monkeypatch.setattr(rb, "universe", lambda: ["2330"])
    called = []

    def fake_rebuild(d8, codes):
        called.append(d8)
        return rb.build_day("2026-10-28", bars(), official(), {}) if d8 == "20261028" else pd.DataFrame(columns=tape.COLUMNS)

    monkeypatch.setattr(rb, "rebuild_day", fake_rebuild)
    out = tape.collect(now)
    assert called == ["20261028"]                                    # 10-29 只差 1 天、10-30 是今天 → 還不重建
    assert set(out.ts.str[:10]) == {"2026-10-28"}
    assert "20261028" not in out.attrs["miss"] and "20261029" in out.attrs["miss"]


def test_main_湖裡已收齊的日子不重建(monkeypatch):
    have = pd.DataFrame({"ts": ["2026-10-28T13:30:00+08:00"], "code": ["2330"]})
    monkeypatch.setattr(store, "read", lambda *a, **k: have)
    monkeypatch.setattr(rb, "universe", lambda: ["2330"])
    monkeypatch.setattr(rb, "rebuild_day", lambda *a: (_ for _ in ()).throw(AssertionError("不該重建")))
    assert rb.main(["20261028"]) == 0
