"""盤前貼文（scripts/social_premarket.py）的資料整理：全部用假資料，不連網、不開瀏覽器。"""
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import social_premarket as sp

from pipeline import config


def _intl(with_adr=True, with_dji=False):
    days = pd.bdate_range("2026-09-21", "2026-10-23").strftime("%Y-%m-%d")
    rows = []
    for i, d in enumerate(days):
        rows += [{"date": d, "symbol": "^IXIC", "close": 26000 + i}, {"date": d, "symbol": "^SOX", "close": 11000 - i},
                 {"date": d, "symbol": "^GSPC", "close": 7600 + i}, {"date": d, "symbol": "^VIX", "close": 18.0},
                 {"date": d, "symbol": "TWD=X", "close": 32.5}]
        if with_adr:
            rows.append({"date": d, "symbol": "TSM", "close": 400 + i})
        if with_dji:
            rows.append({"date": d, "symbol": "^DJI", "close": 46000 + i})
    rows.append({"date": "2026-10-25", "symbol": "TWD=X", "close": 99.0})   # 週末匯率列不可被拿來算（晚於美股收盤日）
    return pd.DataFrame(rows)


def test_intl_symbols_has_dji_and_tsm():
    assert "^DJI" in config.INTL_SYMBOLS and "TSM" in config.INTL_SYMBOLS


def test_us_close_rows_and_missing_dji():
    us = sp.us_close(_intl(), date(2026, 10, 27))
    assert us["date"] == "2026-10-23"
    by = {r["sym"]: r for r in us["rows"]}
    assert by["^DJI"]["missing"] is True and "close" not in by["^DJI"]     # 沒資料就不給數字
    assert by["^IXIC"]["chg"] == 1 and len(by["^IXIC"]["spark"]) == sp.SPARK_N
    assert by["^SOX"]["pct"] < 0


def test_adr_conversion_and_premium():
    price = pd.DataFrame([{"date": "2026-10-21", "code": "2330", "close": 2420.0}, {"date": "2026-10-22", "code": "2330", "close": 2385.0},
                          {"date": "2026-10-27", "code": "2330", "close": 9999.0}])
    us = sp.us_close(_intl(), date(2026, 10, 27))
    a = sp.adr_info(_intl(), price, us["date"], date(2026, 10, 27))
    assert a["missing"] is False and a["fx"] == 32.5 and a["fx_date"] == "2026-10-23"
    assert a["tw_close"] == 2385.0 and a["tw_date"] == "2026-10-22"       # 目標日當天的價不能用
    assert abs(a["conv"] - a["close"] * 32.5 / 5) < 1e-9
    assert abs(a["prem"] - (a["conv"] / 2385 - 1) * 100) < 1e-9


def test_adr_missing_gives_no_numbers():
    a = sp.adr_info(_intl(with_adr=False), pd.DataFrame(), "2026-10-23", date(2026, 10, 27))
    assert a["missing"] is True and "conv" not in a and "prem" not in a


def _night():
    ts = []
    for d0, d1, base in (("2026-10-21", "2026-10-22", 47000), ("2026-10-22", "2026-10-23", 46200)):
        for k, t in enumerate(pd.date_range(f"{d0} 15:00", f"{d1} 04:59", freq="30min", tz="Asia/Taipei")):
            ts.append({"ts": t.isoformat(), "symbol": "FUT_N", "close": base - k})
    ts.append({"ts": "2026-10-22T13:44:00+08:00", "symbol": "FUT", "close": 46272})
    return pd.DataFrame(ts)


def test_night_session_picks_latest_finished_and_compares_day_close():
    intra = _night()
    last = float(intra[intra.symbol == "FUT_N"]["close"].iloc[-1])
    ohlc = pd.DataFrame([{"date": "2026-10-22", "symbol": "FUT", "close": 46272.0, "change": -741.0},
                         {"date": "2026-10-23", "symbol": "FUT_N", "close": last, "change": -580.0},
                         {"date": "2026-10-22", "symbol": "TSE", "close": 46041.0, "change": 0}])
    n = sp.night_session(intra, ohlc, date(2026, 10, 27))
    assert n["session"] == "2026-10-22" and n["close"] == last
    assert n["day_close"] == 46272.0 and n["diff"] == last - 46272.0
    assert n["official_chg"] == -580.0
    # 目標日 10/22：10/22 15:00 開始的夜盤還沒開始 → 取 10/21 那一盤
    n2 = sp.night_session(intra, ohlc, date(2026, 10, 22))
    assert n2["session"] == "2026-10-21"
    # 還沒收完的夜盤：時段寫實際最後一根的時間（不假裝到 05:00）
    part = intra[~((intra.symbol == "FUT_N") & (intra.ts >= "2026-10-23T03:00"))]
    n3 = sp.night_session(part, ohlc, date(2026, 10, 23))
    assert n3["session"] == "2026-10-22" and n3["end"].startswith("2026-10-23T02:30") and n3["partial"] is True
    assert n["partial"] is False


def test_closure_note_typhoon_and_normal_monday():
    c = sp.closure_note("2026-10-22", date(2026, 10, 27))
    assert c["text"] == "台股 10/23–10/26 休市 4 天，10/27 復市" and c["days"] == 4
    assert sp.closure_note("2026-10-16", date(2026, 10, 19)) is None       # 一般週末不寫


def test_pick_news_window_skip_and_formats():
    news = pd.DataFrame([
        {"published_at": "2026-10-24T09:18:27+08:00", "source": "technews", "category": "總經", "title": "AI 投資疑慮未消、油價飆漲，美股三大指數全面收黑"},
        {"published_at": "Sat, 24 Oct 2026 02:00:00 +0000", "source": "udn", "category": "科技", "title": "台積電與輝達擴大 CoWoS 合作"},
        {"published_at": "2026-10-24T20:00:00+08:00", "source": "cnyes", "category": "台股", "title": "杜金龍：台積電這價位閉眼撿"},
        {"published_at": "2026-10-23T20:00:00+08:00", "source": "cnyes", "category": "科技", "title": "輝達半導體晶片大新聞（美股收盤前，不算）"},
        {"published_at": "2026-10-27T09:00:00+08:00", "source": "cnyes", "category": "科技", "title": "台積電開盤後新聞（不算）"},
    ])
    start = sp.us_close_tpe("2026-10-23")
    assert start.hour == 4      # 10 月仍是美國夏令時間：美東 16:00＝台北 04:00
    got = sp.pick_news(news, start, datetime(2026, 10, 27, 8, 45, tzinfo=sp.TPE))
    titles = [g["title"] for g in got]
    assert titles == ["AI 投資疑慮未消、油價飆漲，美股三大指數全面收黑", "台積電與輝達擴大 CoWoS 合作"]
    assert got[1]["source"] == "聯合新聞網" and got[1]["time"].startswith("2026-10-24T10:00")


def test_upcoming_events_fomc_taipei_time():
    ev = sp.upcoming_events(date(2026, 10, 27), pd.DataFrame([{"date": "2026-10-29", "release": "gdp"}, {"date": "2026-10-29", "release": "pce"}]))
    names = [e["name"] for e in ev]
    assert "FOMC 利率決議" in names and ev[0]["time"].startswith("2026-10-29T02:00")
    assert any(e["name"] == "美國 GDP、PCE" and e["time"].startswith("2026-10-29T20:30") for e in ev)


def test_next_trading_day_skips_holidays():
    hol = {"2026-10-26"}
    assert sp.next_trading_day(datetime(2026, 10, 24, 10, 0, tzinfo=sp.TPE), hol) == date(2026, 10, 27)
    assert sp.next_trading_day(datetime(2026, 10, 27, 7, 0, tzinfo=sp.TPE), hol) == date(2026, 10, 27)
    assert sp.next_trading_day(datetime(2026, 10, 27, 9, 0, tzinfo=sp.TPE), hol) == date(2026, 10, 28)


def test_caption_and_summary_facts_only():
    intra = _night()
    ohlc = pd.DataFrame([{"date": "2026-10-22", "symbol": "FUT", "close": 46272.0, "change": 0},
                         {"date": "2026-10-22", "symbol": "TSE", "close": 46041.0, "change": 0}])
    news = pd.DataFrame([{"published_at": "2026-10-24T09:18:27+08:00", "source": "technews", "category": "總經",
                          "title": "AI 投資疑慮未消、油價飆漲，美股三大指數全面收黑" * 3}])
    D = sp.collect(date(2026, 10, 27), _intl(with_adr=False), pd.DataFrame([{"date": "2026-10-22", "code": "2330", "close": 2385.0}]),
                   intra, ohlc, news, pd.DataFrame())
    txt = sp.caption(D, "20261027")
    assert txt.splitlines()[0] == "台股盤前｜10/27"
    assert len(txt) <= 480 and "utm_campaign=premarket_1027" in txt and sp.DISCLAIMER in txt
    assert "台積電 ADR：查證中" in txt and "道瓊 查證中" in txt
    assert "休市 4 天" in D["summary"]
    for bad in ("買進", "賣出", "建議買", "看多", "看空"):
        assert bad not in D["summary"]
