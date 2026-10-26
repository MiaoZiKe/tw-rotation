"""選擇權 P/C 回補：解析與游標（不碰網路）。"""
from datetime import date

import pandas as pd

from pipeline.sources import optpc


def _rows():
    r = []
    for d, c_vol, p_vol, c_oi, p_oi in (("2024-03-04", 1000, 1500, 5000, 6000), ("2024-03-05", 800, 400, 5200, 5000)):
        for cp, v, oi in (("call", c_vol, c_oi), ("put", p_vol, p_oi)):
            r.append(dict(date=d, option_id="TXO", call_put=cp, volume=v / 2, open_interest=oi / 2, trading_session="position", strike_price=20000))
            r.append(dict(date=d, option_id="TXO", call_put=cp, volume=v / 2, open_interest=oi / 2, trading_session="position", strike_price=20100))
        r.append(dict(date=d, option_id="TXO", call_put="call", volume=99999, open_interest=99999, trading_session="after_market", strike_price=20000))
    return r


def test_parse_pc_ratio_ignores_after_market():
    df = optpc.parse_option_daily(_rows())
    a = df[df.date == "2024-03-04"].iloc[0]
    assert abs(a.pc_vol - 1.5) < 1e-9 and abs(a.pc_oi - 1.2) < 1e-9          # 盤後的假資料不得混進去
    b = df[df.date == "2024-03-05"].iloc[0]
    assert abs(b.pc_vol - 0.5) < 1e-9


def test_parse_unknown_columns_returns_empty():
    assert optpc.parse_option_daily([dict(x=1)]).empty and optpc.parse_option_daily(None).empty


def test_month_range_and_cursor(tmp_path, monkeypatch):
    ms = list(optpc.month_range(date(2024, 11, 1), date(2025, 2, 15)))
    assert [m[0] for m in ms] == [date(2024, 11, 1), date(2024, 12, 1), date(2025, 1, 1), date(2025, 2, 1)]
    from pipeline.util import store
    got = []
    monkeypatch.setattr(store, "append", lambda t, df: got.append((t, len(df))) or len(df))
    prog = {}
    saved = []
    calls = []

    def fetch(a, b):
        calls.append((a, b)); return _rows()
    n = optpc.backfill_opt_pc(prog, lambda p: saved.append(dict(p)), today=date(2008, 6, 20), months=2, fetch=fetch)
    assert len(calls) == 2 and prog["complete"]["opt_pc"]["next"] == "2008-03-01" and got and got[0][0] == "opt_pc"


def test_two_empty_months_do_not_advance_cursor(monkeypatch):
    from pipeline.util import store
    monkeypatch.setattr(store, "append", lambda t, df: len(df))
    prog = {}
    optpc.backfill_opt_pc(prog, lambda p: None, today=date(2008, 12, 1), months=3, fetch=lambda a, b: [])
    assert prog["complete"]["opt_pc"]["next"] <= "2008-02-01"             # 不把游標推過去，下一輪再試
