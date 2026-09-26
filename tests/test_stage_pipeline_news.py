"""週末的 phase=news：只更新新聞與國際盤，不去碰價量。

Andy 2026-09-14：「週六日有新增也必須更新上去」。
價量週末不會變（打了只會拿到週五的，而且會被 empty 記成「沒回資料」），
會變的是新聞、國際盤（美股週五夜盤、歐股）與總經。
"""
from __future__ import annotations

import pandas as pd
import pytest

from pipeline import run_daily


@pytest.fixture(autouse=True)
def _clean():
    run_daily.RESULT.clear()
    run_daily.RESULT.update({"steps": {}, "errors": [], "empty": []})
    yield


def _run(monkeypatch, phase, tmp_path):
    """把所有來源換成記名字的假函式，跑一次 main()，回傳被呼叫過的來源名單。"""
    called: list[str] = []

    def rec(name, ret=None):
        def fn(*a, **k):
            called.append(name)
            return pd.DataFrame() if ret is None else ret
        return fn

    # 價量要回真的有日期的一列，否則 trade_date 是 None，融資券與法人會被 `if trade_date:` 擋掉
    px = pd.DataFrame([{"date": "2026-09-14", "code": "2330", "market": "TWSE", "close": 2380.0}])

    for mod, attrs in {
        "twse": ["valuation_daily", "index_daily", "market_daily",
                 "company_info", "margin_daily", "revenue_monthly", "financial_q",
                 "dividend", "dividend_events"],
        "tpex": ["price_daily"],
        "tdcc": ["shareholding_weekly"],
        "news": ["collect", "extract_broker_views"],
        "macro": ["intl_daily", "macro_all"],
        "mops": ["material_news"],
        "finmind": ["stock_info"],
        "mis": ["price_snapshot"],
    }.items():
        target = getattr(run_daily, mod)
        for a in attrs:
            monkeypatch.setattr(target, a, rec(f"{mod}.{a}"), raising=False)
    # latest_date 回的是字串不是 DataFrame，不能用同一個假函式
    monkeypatch.setattr(run_daily.mis, "latest_date", rec("mis.latest_date", "2026-09-14"))
    monkeypatch.setattr(run_daily.store, "latest_date", lambda t: "2026-09-14")
    monkeypatch.setattr(run_daily, "universe_pairs", lambda: [("2330", "TWSE")])
    monkeypatch.setattr(run_daily, "universe", lambda n: ["2330"])

    monkeypatch.setattr(run_daily.twse, "price_daily", rec("twse.price_daily", px))
    monkeypatch.setattr(run_daily, "save", lambda *a, **k: 0)
    monkeypatch.setattr(run_daily, "fetch_institutional", rec("finmind.institutional"))
    # ★ 2026-09-19：分 K 一定要 mock。full phase 會抓 400 檔 Yahoo 分 K，
    #   沒 mock 的話在沒有網路的環境會發出上千個連線、一路重試到逾時
    #   （實測一次 full 就有 1,234 個失敗連線）。這是原本就漏的，
    #   只是以前只有一個測試跑 full，還撐得過去。
    monkeypatch.setattr(run_daily, "collect_intraday_60m", rec("yahoo.intraday_60m"))
    monkeypatch.setattr(run_daily, "refresh_financials", rec("finmind.financial_refresh"))
    # ★ 2026-09-26：期交所逐筆也要 mock —— 沒 mock 的話會對窗內約 30 個日期各試下載一次（每次重試兩輪）。
    monkeypatch.setattr(run_daily, "collect_taifex_minute", rec("taifex.futures_minute"))
    monkeypatch.setattr(run_daily.config, "STATE", tmp_path)
    monkeypatch.setattr(run_daily.store, "table_summary", lambda: pd.DataFrame())
    monkeypatch.setattr(run_daily.loader, "health", lambda: {})
    import pipeline.build_payload as bp
    monkeypatch.setattr(bp, "build", lambda: None)
    monkeypatch.setattr("sys.argv", ["run_daily", "--phase", phase])
    # ★ 2026-09-19：一定要把 exit code 帶出來。
    #   以前這裡只寫 run_daily.main() 不看回傳值，於是「news phase 永遠回 1」這個 bug
    #   從測試裡整個穿過去 —— Actions 的每日管線連續兩輪 failure、deploy 被 skip、
    #   網站在週末與盤前完全不更新，而三道關卡全是綠的。
    rc = run_daily.main()
    return called, rc


def test_news模式不碰價量(monkeypatch, tmp_path):
    called, _ = _run(monkeypatch, "news", tmp_path)
    for name in ("twse.price_daily", "tpex.price_daily", "mis.price_snapshot",
                 "twse.valuation_daily", "twse.margin_daily"):
        assert name not in called, f"phase=news 不該呼叫 {name}"


def test_news模式有抓新聞與國際盤(monkeypatch, tmp_path):
    called, _ = _run(monkeypatch, "news", tmp_path)
    assert "news.collect" in called
    assert "macro.intl_daily" in called


def test_news模式不動FinMind額度(monkeypatch, tmp_path):
    """週末把額度花在補法人沒有意義，那些資料週末不會變。"""
    called, _ = _run(monkeypatch, "news", tmp_path)
    assert "finmind.institutional" not in called
    assert "finmind.financial_refresh" not in called


def test_price模式抓價量與新聞但不碰傍晚才落地的來源(monkeypatch, tmp_path):
    """15:30 那輪也要抓新聞（2026-09-15 起）：新聞整天都在更新，而且不吃 FinMind 額度。

    法人、融資券、財報那些傍晚才出的仍然不抓 —— 硬抓只會把「還沒出」記成「沒回資料」。
    """
    called, _ = _run(monkeypatch, "price", tmp_path)
    assert "twse.price_daily" in called
    assert "news.collect" in called
    assert "finmind.institutional" not in called
    assert "tdcc.shareholding_weekly" not in called


def test_full模式該抓的都抓(monkeypatch, tmp_path):
    called, _ = _run(monkeypatch, "full", tmp_path)
    for name in ("twse.price_daily", "twse.margin_daily", "tdcc.shareholding_weekly",
                 "news.collect", "macro.intl_daily"):
        assert name in called, f"phase=full 應該要呼叫 {name}"


# --------------------------------------------- 退出碼：news phase 不可以因為沒有交易日就失敗
# 真實事故（2026-09-19 才發現，但已經發生兩輪）：
#   run_daily 結尾寫 `return 0 if trade_date else 1`。這條是為 full／price 寫的，
#   但 phase=news 本來就不抓價量（週末、盤前、台北清晨），trade_date 必然是 None
#   → 每一輪 news 都回傳 1 → Actions 的 collect job 判失敗
#   → daily.yml 的 deploy job 是 `needs: collect`，於是被 skip
#   → **新聞與國際盤明明抓到了、前端資料也產好了，網站卻不會更新。**
#
# 日誌長這樣，自相矛盾得很明顯：
#   「=== 完成：4 個步驟成功，0 個錯誤，耗時 257s ===」
#   「##[error]Process completed with exit code 1.」
#
# 這個洞三道關卡都擋不住：pytest 以前只呼叫 main() 不看回傳值、
# _preview 與 _uitest 測的是前端。只有回頭看 Actions 才看得到。

def test_news模式沒有錯誤時退出碼是0(monkeypatch, tmp_path):
    called, rc = _run(monkeypatch, "news", tmp_path)
    assert "news.collect" in called, "前提：這一輪真的有抓到新聞"
    assert rc == 0, (
        "phase=news 不抓價量，trade_date 必然是 None —— "
        "不可以拿它判斷成敗，否則每一輪 news 都會讓 Actions 變紅、deploy 被 skip"
    )


def test_price與full模式仍然靠交易日判斷成敗(monkeypatch, tmp_path):
    """news 的例外不可以把 full／price 的保護一起拿掉 —— 那兩個沒抓到價量就是真的失敗。"""
    for phase in ("price", "full"):
        _, rc = _run(monkeypatch, phase, tmp_path)
        assert rc == 0, f"phase={phase} 有抓到價量，應該成功"


def test_期交所逐筆只在傍晚與週末那幾輪抓(monkeypatch, tmp_path):
    """15:30 那輪（phase price）當天的逐筆檔多半還沒出，打了只會多記一次 404；full 與 news 要抓。"""
    called, _ = _run(monkeypatch, "price", tmp_path)
    assert "taifex.futures_minute" not in called
    for ph in ("full", "news"):
        called, _ = _run(monkeypatch, ph, tmp_path)
        assert "taifex.futures_minute" in called, f"phase={ph} 應該要抓期交所逐筆"
