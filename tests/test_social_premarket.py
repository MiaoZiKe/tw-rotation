"""盤前貼文（scripts/social_premarket.py）的資料整理：全部用假資料，不連網、不開瀏覽器。"""
import sys
import types
from datetime import date, datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import social_premarket as sp

from pipeline import config
from pipeline.sources import macro


def _intl(with_adr=True, with_dji=False, ohlc=True):
    days = pd.bdate_range("2026-08-03", "2026-10-23").strftime("%Y-%m-%d")
    rows = []
    for i, d in enumerate(days):
        syms = [("^IXIC", 26000 + i), ("^SOX", 11000 - i), ("^GSPC", 7600 + i), ("^VIX", 18.0), ("TWD=X", 32.5)]
        if with_adr:
            syms.append(("TSM", 400 + i))
        if with_dji:
            syms.append(("^DJI", 46000 + i))
        for sym, c in syms:
            r = {"date": d, "symbol": sym, "close": float(c), "volume": 1000.0 + i}
            if ohlc:
                r.update(open=c - 1, high=c + 2, low=c - 3)
            rows.append(r)
    rows.append({"date": "2026-10-25", "symbol": "TWD=X", "close": 99.0})   # 週末匯率列不可被拿來算（晚於美股收盤日）
    return pd.DataFrame(rows)


def test_intl_symbols_has_dji_and_tsm():
    assert "^DJI" in config.INTL_SYMBOLS and "TSM" in config.INTL_SYMBOLS


def test_macro_intl_keeps_ohlc(monkeypatch):
    idx = pd.to_datetime(["2026-10-22", "2026-10-23"])
    hist = pd.DataFrame({"Open": [1.0, 2.0], "High": [3.0, 4.0], "Low": [0.5, 1.5], "Close": [2.0, 3.0], "Volume": [10, 20]}, index=idx)
    hist.index.name = "Date"
    fake = types.SimpleNamespace(Ticker=lambda s: types.SimpleNamespace(history=lambda **k: hist))
    monkeypatch.setitem(sys.modules, "yfinance", fake)
    df = macro.intl_daily()
    assert {"open", "high", "low", "close", "volume"} <= set(df.columns)
    row = df[(df.symbol == "TSM") & (df.date == "2026-10-23")].iloc[0]
    assert (row.open, row.high, row.low, row.close) == (2.0, 4.0, 1.5, 3.0)


def test_us_close_rows_candles_and_missing_dji():
    us = sp.us_close(_intl(), date(2026, 10, 27))
    assert us["date"] == "2026-10-23"
    by = {r["sym"]: r for r in us["rows"]}
    assert by["^DJI"]["missing"] is True and "close" not in by["^DJI"]     # 沒資料就不給數字（圖上整列不畫）
    k = by["^IXIC"]["k"]
    assert by["^IXIC"]["chg"] == 1 and len(k["bars"]) == min(sp.K_LONG, 60) and k["has_ohlc"] is True
    assert sp.us_close(_intl(ohlc=False), date(2026, 10, 27))["rows"][0]["k"]["has_ohlc"] is False   # 舊資料沒開高低 → 折線


def test_k_series_indicators_use_full_history():
    ks = sp.k_series(_intl()[lambda d: d.symbol == "^IXIC"])
    b = ks["bars"]
    assert all(x["ma20"] is not None for x in b)          # 指標先用全歷史算，最後 25 根的 MA20 不會斷
    assert abs(b[-1]["ma5"] - sum(x["c"] for x in b[-5:]) / 5) < 1e-9
    assert b[-1]["rsi"] == 100.0                           # 一路上漲，Wilder RSI＝100


def test_k_series_long_has_six_mas():
    days = pd.bdate_range("2025-01-01", "2026-10-23").strftime("%Y-%m-%d")
    df = pd.DataFrame({"date": days, "open": 99.0, "high": 102.0, "low": 98.0, "close": [100.0 + i for i in range(len(days))], "volume": 1.0})
    ks = sp.k_series(df, sp.K_LONG)
    b = ks["bars"]
    assert len(b) == sp.K_LONG and 20 <= sp.K_LONG <= 23 and sp.DRAW_MAS == (5, 10, 20, 60) and [n for _, n in sp.MAS] == ["5日", "10日", "月線20", "季線60", "半年線120", "年線240"]
    assert all(x["ma240"] is not None for x in b)                  # 歷史夠長，半年 K 棒的年線全程都有
    assert abs(b[-1]["ma240"] - (sum(range(len(days) - 240, len(days))) / 240 + 100)) < 1e-6


def test_ta_rows_table_cross_vs_position_and_no_advice():
    def bar(c, ma5, ma20, ma60, rsi, v=None, vma5=None):
        return {"c": c, "ma5": ma5, "ma10": None, "ma20": ma20, "ma60": ma60, "ma120": None, "ma240": None, "rsi": rsi, "v": v, "vma5": vma5}
    rows = sp.ta_rows({"bars": [bar(100, 101, 90, 80, 50), bar(103, 102, 91, 81, 72.3, 1500, 1000)]})
    assert rows[0] == ("收盤", "103.00", "站上 5日")
    assert rows[1] == ("RSI(14)", "72.3", "70 以上高檔區")
    assert rows[2] == ("量能", "+50.0%", "較前 5 日均量・價漲量增")
    flat = sp.ta_rows({"bars": [bar(98, 99, 110, 90, 45), bar(97, 99.5, 110, 90, 41.0)]})
    assert flat[0][2] == "月線之下、季線之上" and flat[1][2] == "30–70 區間・50 以下" and len(flat) == 2   # 沒穿過 → 寫跟月線、季線的位置
    both = sp.ta_rows({"bars": [bar(100, 99, 101, 80, 50), bar(100, 101, 99, 80, 50)]})
    assert both[0][2] == "站上 月線20、跌破 5日"
    for r in rows + flat + both:
        for bad in ("買", "賣", "建議", "看多", "看空", "偏多", "偏空"):
            assert bad not in "".join(r)


def test_adr_conversion_premium_and_tsmc_fallback():
    price = pd.DataFrame([{"date": "2026-10-21", "code": "2330", "open": 2425, "high": 2435, "low": 2400, "close": 2420.0, "volume": 1},
                          {"date": "2026-10-22", "code": "2330", "open": 2435, "high": 2435, "low": 2385, "close": 2385.0, "volume": 1},
                          {"date": "2026-10-27", "code": "2330", "close": 9999.0}])
    a = sp.adr_info(_intl(), price, "2026-10-23", date(2026, 10, 27))
    assert a["missing"] is False and a["fx"] == 32.5 and a["fx_date"] == "2026-10-23"
    assert a["tw_close"] == 2385.0 and a["tw_date"] == "2026-10-22"       # 目標日當天的價不能用
    assert abs(a["conv"] - a["close"] * 32.5 / 5) < 1e-9
    assert abs(a["prem"] - (a["conv"] / 2385 - 1) * 100) < 1e-9
    m = sp.adr_info(_intl(with_adr=False), price, "2026-10-23", date(2026, 10, 27))
    assert m["missing"] is True and "conv" not in m and "prem" not in m
    assert m["tw_k"]["bars"][-1]["c"] == 2385.0 and abs(m["tw_pct"] - (2385 / 2420 - 1) * 100) < 1e-9


def _night():
    ts = []
    for d0, d1, base in (("2026-10-21", "2026-10-22", 47000), ("2026-10-22", "2026-10-23", 46200)):
        for k, t in enumerate(pd.date_range(f"{d0} 15:00", f"{d1} 04:59", freq="30min", tz="Asia/Taipei")):
            ts.append({"ts": t.isoformat(), "symbol": "FUT_N", "close": base - k})
    ts.append({"ts": "2026-10-22T13:44:00+08:00", "symbol": "FUT", "close": 46272})
    return pd.DataFrame(ts)


def _ohlc(last_night):
    days = pd.bdate_range("2026-08-03", "2026-10-21").strftime("%Y-%m-%d")
    rows = [{"date": d, "symbol": "FUT", "open": 46000.0 + i, "high": 46100.0 + i, "low": 45900.0 + i, "close": 46050.0 + i,
             "volume": 1000 + i, "change": 0} for i, d in enumerate(days)]
    rows += [{"date": "2026-10-22", "symbol": "FUT", "open": 46500.0, "high": 46600.0, "low": 46200.0, "close": 46272.0, "volume": 900, "change": -741.0},
             {"date": "2026-10-23", "symbol": "FUT_N", "close": last_night, "change": -580.0},
             {"date": "2026-10-22", "symbol": "TSE", "close": 46041.0, "change": 0}]
    return pd.DataFrame(rows), 46050.0 + len(days) - 1


def test_night_session_and_tx_daily():
    intra = _night()
    last = float(intra[intra.symbol == "FUT_N"]["close"].iloc[-1])
    ohlc, prev = _ohlc(last)
    n = sp.night_session(intra, ohlc, date(2026, 10, 27))
    assert n["session"] == "2026-10-22" and n["close"] == last and n["partial"] is False
    assert n["day_close"] == 46272.0 and n["diff"] == last - 46272.0 and n["official_chg"] == -580.0
    assert sp.night_session(intra, ohlc, date(2026, 10, 22))["session"] == "2026-10-21"
    part = intra[~((intra.symbol == "FUT_N") & (intra.ts >= "2026-10-23T03:00"))]
    n3 = sp.night_session(part, ohlc, date(2026, 10, 23))
    assert n3["end"].startswith("2026-10-23T02:30") and n3["partial"] is True
    tx = sp.tx_daily(ohlc, date(2026, 10, 27))
    assert tx["date"] == "2026-10-22" and tx["close"] == 46272.0 and tx["k"]["has_ohlc"] is True
    assert tx["chg"] == 46272.0 - prev


def test_closure_note_typhoon_and_normal_monday():
    c = sp.closure_note("2026-10-22", date(2026, 10, 27))
    assert c["text"] == "台股 10/23–10/26 休市 4 天，10/27 復市" and c["days"] == 4
    assert sp.closure_note("2026-10-16", date(2026, 10, 19)) is None


def test_news_category_rules():
    assert sp.news_category("美特使稱最快週末攻擊伊朗 推高油價") == "事件"
    assert sp.news_category("美債殖利率急跌、企業信用風險飆升") == "總經"
    assert sp.news_category("長江存儲重大突破 挑戰三星、美光") == "科技"     # 「挑戰」不是戰爭
    assert sp.news_category("亞馬遜砸2200億美元投資AI") == "科技"           # 「美元」金額不是匯率
    assert sp.news_category("006208擬分割一拆八") == "新聞"


def test_pick_news_coverage_ranking_window_and_skip():
    rows = [
        # 「伊朗」主題：3 家媒體報導 → 最受關注
        ("2026-10-24T07:30:00+08:00", "cnyes", "科技", "美特使稱最快週末攻擊伊朗 以色列宣布封鎖西岸、中東多線升溫", "伊朗,美國"),
        ("Sat, 24 Oct 2026 02:00:00 +0000", "udn", "台股", "伊朗情勢升溫 油價跳漲", ""),
        ("2026-10-24T11:00:00+08:00", "technews", "總經", "伊朗衝突牽動航運", "伊朗,航運"),
        # 「記憶體」主題：2 家
        ("2026-10-24T13:10:00+08:00", "cnyes", "科技", "長江存儲重大突破！傳開發 LPDDR5X　挑戰三星、美光", "記憶體,長江存儲"),
        ("2026-10-25T10:00:00+08:00", "technews", "科技", "南亞科 Q3 獲利創紀錄股價卻重挫", "記憶體,dram"),
        # 單篇（沒有別家報導同主題）→ 只在主題不夠時補位
        ("2026-10-25T08:00:00+08:00", "cnyes", "台股", "006208擬分割一拆八！12/18開受益人會議", "006208,分割"),
        # 排除：喊盤
        ("2026-10-24T20:00:00+08:00", "cnyes", "台股", "杜金龍：記憶體這價位閉眼撿", "記憶體"),
        # 窗口外
        ("2026-10-23T20:00:00+08:00", "cnyes", "科技", "伊朗（美股收盤前，不算）", "伊朗"),
        ("2026-10-27T09:00:00+08:00", "cnyes", "科技", "伊朗（開盤後，不算）", "伊朗"),
    ]
    news = pd.DataFrame([{"published_at": a, "source": b, "category": c, "title": t, "keywords": k, "url": f"https://x/{i}"}
                         for i, (a, b, c, t, k) in enumerate(rows)])
    got = sp.pick_news(news, sp.us_close_tpe("2026-10-23"), datetime(2026, 10, 27, 8, 45, tzinfo=sp.TPE), n=3)
    # 先看跟台股／市場／科技的相關度，再看報導家數：伊朗（3 家，代表標題挑有「油價」的那篇）→ 記憶體（2 家）→ 006208（單篇補位）
    assert [g["topic"] for g in got] == ["伊朗", "記憶體", ""]
    assert got[0]["title"] == "伊朗情勢升溫 油價跳漲" and got[0]["coverage"] == {"sources": 3, "articles": 3}
    assert {g["category"] for g in got} == {"科技", "新聞", "事件"}       # 第一輪每類各挑一則
    assert "\u3000" not in got[1]["title"]               # 全形空白正規化成一般空白（不改寫字）
    assert all("杜金龍" not in g["title"] and "不算" not in g["title"] for g in got)
    assert got[0]["url"].startswith("https://x/")


def test_pick_news_demotes_gossip_and_covers_four_categories():
    rows = [
        ("cnyes", "事件", "馬斯克再批澤倫斯基該下台", "澤倫斯基,馬斯克"), ("udn", "事件", "馬斯克嗆澤倫斯基 烏克蘭回擊", "澤倫斯基"),
        ("technews", "事件", "澤倫斯基回應馬斯克批評", "澤倫斯基,馬斯克"),
        ("cnyes", "科技", "輝達 GB300 出貨放量", "輝達"), ("cnyes", "總經", "美債殖利率急跌 Fed 降息預期升溫", "美債"),
        ("cnyes", "台股", "外資連三賣 台股成交量萎縮", "外資"), ("udn", "事件", "川普宣布對墨西哥加徵關稅", "關稅"),
    ]
    news = pd.DataFrame([{"published_at": f"2026-10-24T1{i}:00:00+08:00", "source": b, "category": c, "title": t, "keywords": k, "url": ""}
                         for i, (b, c, t, k) in enumerate(rows)])
    got = sp.pick_news(news, sp.us_close_tpe("2026-10-23"), datetime(2026, 10, 27, 8, 45, tzinfo=sp.TPE), n=4)
    assert {g["category"] for g in got} == {"新聞", "事件", "科技", "總經"}
    assert all("澤倫斯基" not in g["title"] for g in got)            # 3 家都報的口水新聞也排不進來（有更相關的就不用它）
    assert sp.relevance_tier("馬斯克再批澤倫斯基該下台", "事件") == 2 and sp.relevance_tier("川普宣布對墨西哥加徵關稅", "事件") == 0


def test_upcoming_events_fomc_taipei_time():
    ev = sp.upcoming_events(date(2026, 10, 27), pd.DataFrame([{"date": "2026-10-29", "release": "gdp"}, {"date": "2026-10-29", "release": "pce"}]))
    assert ev[0]["name"] == "FOMC 利率決議" and ev[0]["time"].startswith("2026-10-29T02:00")
    assert any(e["name"] == "美國 GDP、PCE" and e["time"].startswith("2026-10-29T20:30") for e in ev)


def test_next_trading_day_skips_holidays():
    hol = {"2026-10-26"}
    assert sp.next_trading_day(datetime(2026, 10, 24, 10, 0, tzinfo=sp.TPE), hol) == date(2026, 10, 27)
    assert sp.next_trading_day(datetime(2026, 10, 27, 7, 0, tzinfo=sp.TPE), hol) == date(2026, 10, 27)
    assert sp.next_trading_day(datetime(2026, 10, 27, 9, 0, tzinfo=sp.TPE), hol) == date(2026, 10, 28)


def _collect():
    intra = _night()
    news = pd.DataFrame([{"published_at": "2026-10-24T09:18:27+08:00", "source": "technews", "category": "總經",
                          "title": "AI 投資疑慮未消、油價飆漲，美股三大指數全面收黑" * 2, "keywords": "油價", "url": "https://x/1"}])
    price = pd.DataFrame([{"date": "2026-10-21", "code": "2330", "close": 2420.0}, {"date": "2026-10-22", "code": "2330", "close": 2385.0}])
    ohlc, _ = _ohlc(float(intra[intra.symbol == "FUT_N"]["close"].iloc[-1]))
    return sp.collect(date(2026, 10, 27), _intl(with_adr=False), price, intra, ohlc, news, pd.DataFrame())


def test_pages_have_no_notes_and_skip_missing():
    D = _collect()
    for mode in ("threads", "story"):
        pages = sp.build_pages(D, mode)
        assert [p["name"] for p in pages] == ["us-close", "tx", "news"]      # 2026-10-26 Andy：「就這三張」   # ADR 沒資料 → 下段不畫、不換成現貨
        assert pages[1]["title"] == "費半・台指期" and "台積電" not in pages[1]["inner"]      # 10-26 晚：費半移到第二張
        assert "季線60" in pages[1]["inner"] and "年線240" not in pages[1]["inner"] and "class=rdb" in pages[1]["inner"] and "class=tat" not in pages[1]["inner"] and "RSI" not in pages[1]["inner"]      # 10-26 拿掉技術面表格與 RSI
        html = "".join(p["inner"] + p["title"] for p in pages)
        for bad in ("查證中", "資料日", "休市", "時段", "本週", "資料：", "不構成投資建議", "道瓊"):
            assert bad not in html, bad
        assert pages[0]["title"] == "美股"


def test_tx_page_has_adr_section_when_available():
    intra = _night()
    ohlc, _ = _ohlc(float(intra[intra.symbol == "FUT_N"]["close"].iloc[-1]))
    price = pd.DataFrame([{"date": "2026-10-21", "code": "2330", "close": 2420.0}, {"date": "2026-10-22", "code": "2330", "close": 2385.0}])
    D = sp.collect(date(2026, 10, 27), _intl(), price, intra, ohlc, pd.DataFrame(), pd.DataFrame())
    pages = sp.build_pages(D, "threads")
    tx = pages[[p["name"] for p in pages].index("tx")]
    assert tx["title"] == "費半・台指期・ADR" and {"ktx", "kadr"} <= set(tx["charts"])
    assert tx["inner"].index("data-box=ktx-nm") < tx["inner"].index("data-box=kadr-nm") and "換算 " in tx["inner"] and "RSI" not in tx["inner"]
    assert "tsmc" not in [p["name"] for p in pages] and set(D["ta"]) == {"tx", "adr"}


def test_caption_and_premarket_news():
    D = _collect()
    txt = sp.caption(D, "20261027")
    lines = txt.splitlines()
    assert lines[0] == "🌅 盤前3分鐘 10/27" and lines[-1].split("#")[0] == "https://liguligu-puipui.com/?u=th-pm-20261027" and "留言" not in txt      # 2026-10-26 盤前文案改成盤中盤後同格式
    # 2026-10-27 Andy：「排版要整齊 一個一行 另外重點資訊至少5個且在多點描述」→ 主文「📌 今日焦點：」一則一行；盤面解讀＋融資改放回覆
    assert lines[1] == "📌 今日焦點：" and lines[2].startswith("・美股四大指數") and "費半持平" in lines[2] and "…" not in txt
    assert "・AI 投資疑慮未消、油價飆漲" in lines and "📰 昨日事件：" not in lines and "🧭 昨日盤面" not in txt and "資料：" not in txt
    assert len(txt) <= 480 and "👉 更多詳細資料可以點擊以下連結：\nhttps://liguligu-puipui.com/?u=th-pm-20261027" in txt and txt.endswith("#earnings")      # 10-27 深層連結：夾具有 FOMC 事件 → 落點 #earnings
    rp = sp.caption_reply(D)
    assert rp.startswith("🧭 昨日盤面（美股 10/23）：") and "https://" not in rp and "#台股" not in rp and len(rp) <= 480 and "查證中" not in txt
    pn = sp.premarket_news(D)
    assert pn["version"] == 1 and pn["target_date"] == "2026-10-27" and pn["categories"] == ["新聞", "事件", "科技", "總經"]
    it = pn["items"][0]
    assert set(it) == {"category", "title", "url", "source", "published_at", "coverage", "summary"}      # 10-27 加簡短敘述
    assert it["source"] == "科技新報" and it["url"] == "https://x/1" and it["published_at"].startswith("2026-10-24T09:18")
    for bad in ("買進", "賣出", "建議買", "看多", "看空"):
        assert bad not in D["summary"]


def test_snap_note_regex_catches_notes():
    import re
    import social_snap as ss
    rx = re.compile(ss.NOTE_RE)
    for bad in ("資料來源：證交所", "僅供參考", "不構成投資建議", "部分估算", "上市融資維持率（估算）", "資料日：10/22", "計算方式"):
        assert rx.search(bad), bad
    for ok in ("融資增減排行", "增加 Top 8", "+2.71 千張", "外資", "130%", "較前日 -5.85 pp"):
        assert not rx.search(ok), ok


def test_盤面解讀_開低走高():
    import pandas as pd
    rows = [{"date": f"2026-10-{d:02d}", "open": o, "high": h, "low": l, "close": c, "volume": 1}
            for d, (o, h, l, c) in zip(range(10, 24), [(100, 101, 99, 100)] * 6 + [(100, 100, 98, 99), (99, 99, 97, 98), (98, 98, 96, 97),
                                                       (97, 98, 96, 97.5), (97.5, 97.5, 95, 96), (96, 96.5, 95, 96)] + [(96, 96, 95, 95.5), (95, 97, 94.8, 96.9)])]
    ks = sp.k_series(pd.DataFrame(rows), 25)
    r = sp.bar_read("費半", ks)
    assert r.startswith("費半 +1.47%，開低走高、翻紅作收") and "止跌" not in r      # 專家審查：用「連 N 黑後收紅」事實句，不用「止跌」


def test_盤面解讀_連黑與窄幅():
    import pandas as pd
    cl = [100, 101, 102, 103, 104, 105, 104, 103, 102, 101, 102.5]
    rows = [{"date": f"2026-10-{10 + i:02d}", "open": (cl[i - 1] if i else c) * 0.995, "high": c * 1.01, "low": c * 0.985, "close": c, "volume": 1} for i, c in enumerate(cl)]
    r = sp.bar_read("那斯達克", sp.k_series(pd.DataFrame(rows), 25))
    assert "連 4 黑後收紅" in r and "作收" not in r.split("；")[0] or "連 4 黑後收紅" in r
    r2 = sp.bar_read("那斯達克", sp.k_series(pd.DataFrame(rows), 25), partial=True)
    assert "作收" not in r2 and "收在" not in r2


def test_今日焦點描述不截半句():
    assert sp._desc("全球 AI 晶片搶購潮白熱化，特斯拉執行長馬斯克週日正式宣布，旗下 SpaceX 已完成募資", 40) == "全球 AI 晶片搶購潮白熱化"
    assert sp._desc("外資單日狂賣台股3025.55億元創紀錄，主因美國CPI高於預期。&#10;野村統計", 60) == "外資單日狂賣台股3025.55億元創紀錄，主因美國CPI高於預期"
    assert sp._clause("外資狂賣3025億元台股不妙？野村估明年EPS成長29%", 30) == "外資狂賣3025億元台股不妙？"
    assert sp._clause("川普任內汽油均價超越拜登時期 柴油價格創歷史新高 期中選舉壓力加劇", 30) == "川普任內汽油均價超越拜登時期"


def test_etf_exdiv_soon_熱門ETF七天內除息():
    df = pd.DataFrame([
        {"code": "00919", "ex_date": "2026-11-03"}, {"code": "00919", "ex_date": "2026-11-03"},    # 重複列只算一次
        {"code": "0056", "ex_date": "2026-11-10"},        # 超過 7 天
        {"code": "00999A", "ex_date": "2026-11-02"},      # 不在熱門清單
        {"code": "00878", "ex_date": "2026-10-27"},       # 已過
    ])
    out = sp.etf_exdiv_soon(date(2026, 10, 28), df)
    assert out == ["00919 群益台灣精選高息 11/03"]
    assert sp.etf_exdiv_soon(date(2026, 10, 28), pd.DataFrame(columns=["code", "ex_date"])) == []
    assert sp.etf_exdiv_soon(date(2026, 10, 28), pd.DataFrame([{"x": 1}])) == []       # 欄位不對 → 空，不炸貼文
