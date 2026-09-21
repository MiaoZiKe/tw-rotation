"""v3 新資料源：FinMind 股利 / 除權息 / 融資券 / 股權分散歷史，與 Yahoo 分 K。

開發環境沒有對外網路，全部用規格書裡的實測回應樣本 monkeypatch。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import config  # noqa: E402
from pipeline.sources import finmind, tdcc, yahoo  # noqa: E402
from pipeline.sources import twse  # noqa: E402
from pipeline.util import http  # noqa: E402

# ------------------------------------------------------------------ 樣本（規格書實測）

DIVIDEND_ROW = {
    "AnnouncementDate": "2026-09-01", "CashDividendPaymentDate": "2026-10-08",
    "CashEarningsDistribution": 7.00000137, "CashExDividendTradingDate": "2026-09-16",
    "CashStatutorySurplus": 0, "StockEarningsDistribution": 0, "StockStatutorySurplus": 0,
    "StockExDividendTradingDate": "", "date": "2026-09-22", "stock_id": "2330",
    "year": "115年第1季",
}
DIVIDEND_ROW_BOTH = {
    "AnnouncementDate": "2025-03-01", "CashDividendPaymentDate": "",
    "CashEarningsDistribution": 1.5, "CashExDividendTradingDate": "",
    "CashStatutorySurplus": 0.5, "StockEarningsDistribution": 0.2, "StockStatutorySurplus": 0.3,
    "StockExDividendTradingDate": "2025-08-01", "date": "2025-07-22", "stock_id": "2330",
    "year": "114年",
}
DIVRESULT_ROW = {
    "after_price": 2248.99, "before_price": 2255, "date": "2026-06-11", "max_price": 2470,
    "min_price": 2025, "open_price": 2250, "reference_price": 2248.99,
    "stock_and_cache_dividend": 6.000035, "stock_id": "2330", "stock_or_cache_dividend": "息",
}
MARGIN_ROW = {
    "MarginPurchaseBuy": 728, "MarginPurchaseCashRepayment": 6, "MarginPurchaseLimit": 6483092,
    "MarginPurchaseSell": 227, "MarginPurchaseTodayBalance": 28474,
    "MarginPurchaseYesterdayBalance": 27979, "OffsetLoanAndShort": 0,
    "ShortSaleBuy": 30, "ShortSaleCashRepayment": 4, "ShortSaleLimit": 6483092,
    "ShortSaleSell": 0, "ShortSaleTodayBalance": 2, "ShortSaleYesterdayBalance": 36,
    "date": "2026-09-10", "stock_id": "2330",
}


def _holding_row(level: str, people: int, unit: float, pct: float) -> dict:
    return {"date": "2026-09-05", "stock_id": "2330", "HoldingSharesLevel": level,
            "people": people, "unit": unit, "percent": pct}


HOLDING_ROWS = [
    _holding_row("1-999", 100, 1000, 1.5),
    _holding_row("1,000-5,000", 50, 2000, 2.5),
    _holding_row(" 1,000,001 以上", 3, 8000, 40.0),      # 帶空白也要對得上
    _holding_row("more than 1,000,001", 5, 9000, 60.0),
    _holding_row("total", 155, 12000, 100.0),
    _holding_row("差異數調整", 0, 0, 0.0),
    _holding_row("whatever", 9, 9, 9.0),                 # 對不上的略過
]


@pytest.fixture()
def fake_finmind(monkeypatch):
    """把 http.finmind_get 換成查表；記下每次呼叫的參數。"""
    calls: list[dict] = []
    payloads: dict[str, object] = {}

    def fake_get(dataset, **kw):
        calls.append({"dataset": dataset, **kw})
        return payloads.get(dataset)

    monkeypatch.setattr(http, "finmind_get", fake_get)
    return payloads, calls


# ------------------------------------------------------------------ 股利公告

def test_dividend_events_expands_cash_and_skips_zero_stock(fake_finmind):
    payloads, calls = fake_finmind
    payloads["TaiwanStockDividend"] = [DIVIDEND_ROW]
    df = finmind.dividend_events("2330", "2016-01-01", wait=False)

    assert calls == [{"dataset": "TaiwanStockDividend", "data_id": "2330",
                      "start_date": "2016-01-01", "wait_when_exhausted": False}]
    assert list(df.columns) == ["code", "period", "kind", "amount", "announce_date",
                                "ex_date", "payment_date", "fiscal_year"]
    assert len(df) == 1, "股票股利為 0 不輸出"
    r = df.iloc[0]
    assert r["code"] == "2330" and r["period"] == "115年第1季" and r["kind"] == "cash"
    assert r["amount"] == pytest.approx(7.00000137)
    assert r["announce_date"] == "2026-09-01"
    assert r["ex_date"] == "2026-09-16"
    assert r["payment_date"] == "2026-10-08"
    assert r["fiscal_year"] == 2026


def test_dividend_events_both_kinds_and_blank_dates(fake_finmind):
    payloads, _ = fake_finmind
    payloads["TaiwanStockDividend"] = [DIVIDEND_ROW, DIVIDEND_ROW_BOTH]
    df = finmind.dividend_events("2330", "2016-01-01")
    assert len(df) == 3
    both = df[df["period"] == "114年"].set_index("kind")
    assert set(both.index) == {"cash", "stock"}
    # 現金 = 盈餘 + 公積；股票同理
    assert both.loc["cash", "amount"] == pytest.approx(2.0)
    assert both.loc["stock", "amount"] == pytest.approx(0.5)
    # 空字串日期 → None
    assert both.loc["cash", "ex_date"] is None
    assert both.loc["cash", "payment_date"] is None
    assert both.loc["stock", "ex_date"] == "2025-08-01"
    assert both.loc["stock", "payment_date"] is None, "股票股利沒有發放日"
    assert (both["fiscal_year"] == 2025).all()
    # key 欄位齊全，可以進資料湖
    assert all(k in df.columns for k in config.TABLES["dividend_events"])


def test_dividend_events_non_200_returns_empty(fake_finmind):
    payloads, _ = fake_finmind
    payloads["TaiwanStockDividend"] = None       # finmind_get 遇到非 200 回 None
    assert finmind.dividend_events("2330", "2016-01-01").empty
    payloads["TaiwanStockDividend"] = []
    assert finmind.dividend_events("2330", "2016-01-01").empty


@pytest.mark.parametrize("period,expected", [
    ("115年第1季", 2026), ("114年", 2025), ("113年上半年", 2024), ("2024", 2024),
    ("", None), (None, None), ("N/A", None),
])
def test_fiscal_year_parse(period, expected):
    assert finmind.fiscal_year_of(period) == expected


# ------------------------------------------------------------------ 除權息結果

def test_dividend_results_fields(fake_finmind):
    payloads, calls = fake_finmind
    payloads["TaiwanStockDividendResult"] = [DIVRESULT_ROW]
    df = finmind.dividend_results("2330", "2016-01-01", wait=False)
    assert calls[0]["dataset"] == "TaiwanStockDividendResult"
    assert list(df.columns) == ["date", "code", "kind", "dividend", "before_price",
                                "reference_price", "open_price"]
    r = df.iloc[0]
    assert r["date"] == "2026-06-11" and r["code"] == "2330" and r["kind"] == "息"
    assert r["dividend"] == pytest.approx(6.000035)
    assert r["before_price"] == 2255
    assert r["reference_price"] == pytest.approx(2248.99)
    assert r["open_price"] == 2250
    assert all(k in df.columns for k in config.TABLES["dividend_results"])


def test_dividend_results_non_200_returns_empty(fake_finmind):
    payloads, _ = fake_finmind
    payloads["TaiwanStockDividendResult"] = None
    assert finmind.dividend_results("2330", "2016-01-01").empty


# ------------------------------------------------------------------ 融資融券

def test_margin_history_aligns_with_twse_margin_daily(fake_finmind, monkeypatch):
    payloads, calls = fake_finmind
    payloads["TaiwanStockMarginPurchaseShortSale"] = [MARGIN_ROW]
    df = finmind.margin_history("2330", "2021-01-01", wait=False)
    assert calls[0]["dataset"] == "TaiwanStockMarginPurchaseShortSale"
    assert calls[0]["start_date"] == "2021-01-01"

    r = df.iloc[0]
    assert r["date"] == "2026-09-10" and r["code"] == "2330"
    assert r["margin_balance"] == 28474
    assert r["margin_change"] == 28474 - 27979
    assert r["short_balance"] == 2
    assert r["short_change"] == 2 - 36
    assert r["margin_buy"] == 728 and r["margin_sell"] == 227
    assert r["short_sell"] == 0 and r["short_cover"] == 30
    assert r["offset"] == 0

    # 欄位要跟證交所 MI_MARGN 的轉換完全一致，才能 append 進同一張 margin_daily
    monkeypatch.setattr(twse, "_fetch", lambda key: [{
        "股票代號": "2330", "融資前日餘額": "27979", "融資今日餘額": "28474",
        "融券前日餘額": "36", "融券今日餘額": "2", "融資買進": "728", "融資賣出": "227",
        "融券賣出": "0", "融券買進": "30", "資券互抵": "0",
    }])
    ref = twse.margin_daily("2026-09-10")
    assert list(df.columns) == list(ref.columns)
    assert df.iloc[0].to_dict() == {k: (v if isinstance(v, str) else float(v))
                                    for k, v in ref.iloc[0].to_dict().items()}


def test_margin_history_non_200_returns_empty(fake_finmind):
    payloads, _ = fake_finmind
    payloads["TaiwanStockMarginPurchaseShortSale"] = None
    assert finmind.margin_history("2330", "2021-01-01").empty


# ------------------------------------------------------------------ 股權分散

def test_holding_history_maps_levels_loosely(fake_finmind, caplog):
    payloads, calls = fake_finmind
    payloads["TaiwanStockHoldingSharesPer"] = HOLDING_ROWS
    with caplog.at_level("WARNING"):
        df = finmind.holding_history("2330", "2021-01-01", wait=False)
    assert calls[0]["dataset"] == "TaiwanStockHoldingSharesPer"

    assert list(df.columns) == ["date", "code", "level", "level_label",
                                "holders", "shares", "pct"]
    assert df["level"].tolist() == [1, 2, 15, 15, 17, 16], "對不上的 whatever 要略過"
    assert df["level_label"].tolist() == [tdcc.LEVEL_LABELS[v] for v in df["level"]]
    assert df["holders"].tolist() == [100, 50, 3, 5, 155, 0]
    assert df["shares"].tolist() == [1000, 2000, 8000, 9000, 12000, 0]
    assert df["pct"].tolist() == [1.5, 2.5, 40.0, 60.0, 100.0, 0.0]
    assert (df["date"] == "2026-09-05").all() and (df["code"] == "2330").all()
    # 對不上的級距只 log 一次，且把標籤列出來
    warn = [r for r in caplog.records if "級距" in r.getMessage()]
    assert len(warn) == 1 and "whatever" in warn[0].getMessage()
    assert all(k in df.columns for k in config.TABLES["shareholding_weekly"])


def test_holding_history_non_200_or_all_unknown_returns_empty(fake_finmind):
    payloads, _ = fake_finmind
    payloads["TaiwanStockHoldingSharesPer"] = None      # 免費層不開放 → 非 200 → None
    assert finmind.holding_history("2330", "2021-01-01").empty
    payloads["TaiwanStockHoldingSharesPer"] = [_holding_row("??", 1, 1, 1.0)]
    assert finmind.holding_history("2330", "2021-01-01").empty


@pytest.mark.parametrize("label,expected", [
    ("1-999", 1), ("1,000-5,000", 2), ("1,000,001以上", 15), ("more than 1,000,001", 15),
    ("MORE THAN 1,000,001", 15), ("total", 17), ("合計", 17), ("差異數調整", 16),
    ("800,001 - 1,000,000", 14), ("", None), (None, None), ("nope", None),
])
def test_holding_level_lookup(label, expected):
    assert finmind.holding_level(label) == expected


# ------------------------------------------------------------------ Yahoo 分 K

def _multi_frame(symbols: list[str], n: int = 3, freq: str = "60min") -> pd.DataFrame:
    idx = pd.date_range("2026-09-10 09:00", periods=n, freq=freq, tz="Asia/Taipei")
    cols = pd.MultiIndex.from_product([symbols, ["Open", "High", "Low", "Close", "Adj Close", "Volume"]])
    data = np.arange(n * len(cols), dtype=float).reshape(n, len(cols))
    return pd.DataFrame(data, index=idx, columns=cols)


@pytest.fixture()
def fake_yf(monkeypatch):
    import yfinance
    calls: list[dict] = []
    state = {"frame": None, "error": None}

    def fake_download(tickers, **kw):
        calls.append({"tickers": list(tickers), **kw})
        if state["error"]:
            raise state["error"]
        f = state["frame"]
        return f(tickers) if callable(f) else f

    monkeypatch.setattr(yfinance, "download", fake_download)
    monkeypatch.setattr(yahoo.time, "sleep", lambda s: None)
    return state, calls


def test_intraday_multiindex_to_long(fake_yf):
    state, calls = fake_yf
    frame = _multi_frame(["2330.TW", "6488.TWO"])
    frame.loc[frame.index[1], ("6488.TWO", "Close")] = np.nan     # 缺 K 要丟掉
    state["frame"] = frame

    df = yahoo.intraday(["2330", "6488"], {"6488": "TPEX", "2330": "TWSE"}, "60m", "730d")

    assert calls[0]["tickers"] == ["2330.TW", "6488.TWO"], "上櫃 .TWO、上市 .TW"
    assert calls[0]["interval"] == "60m" and calls[0]["period"] == "730d"
    assert calls[0]["group_by"] == "ticker" and calls[0]["auto_adjust"] is False
    assert calls[0]["progress"] is False and calls[0]["threads"] is True

    assert list(df.columns) == ["ts", "code", "open", "high", "low", "close", "volume"]
    assert df["code"].tolist() == ["2330"] * 3 + ["6488"] * 2
    assert df["ts"].str.endswith("+08:00").all()
    assert df["ts"].iloc[0] == "2026-09-10T09:00:00+08:00"
    assert df["ts"].iloc[1] == "2026-09-10T10:00:00+08:00"
    # 2330 第一根：Open/High/Low/Close/Volume 對到 0/1/2/3/5（Adj Close 是 4，不要拿錯）
    first = df.iloc[0]
    assert (first["open"], first["high"], first["low"], first["close"], first["volume"]) == (0, 1, 2, 3, 5)


def test_intraday_single_level_frame(fake_yf):
    state, calls = fake_yf
    idx = pd.date_range("2026-09-10 09:00", periods=2, freq="15min", tz="Asia/Taipei")
    state["frame"] = pd.DataFrame({"Open": [1.0, 2.0], "High": [1.5, 2.5], "Low": [0.5, 1.5],
                                   "Close": [1.2, np.nan], "Adj Close": [1.2, 2.2],
                                   "Volume": [10, 20]}, index=idx)
    df = yahoo.intraday(["2330"], {}, "15m", "60d")
    assert calls[0]["tickers"] == ["2330.TW"], "不在 markets 裡的代號視為上市"
    assert len(df) == 1 and df.iloc[0]["code"] == "2330"
    assert df.iloc[0]["ts"] == "2026-09-10T09:00:00+08:00"
    assert df.iloc[0]["close"] == pytest.approx(1.2)


def test_intraday_converts_utc_and_naive_to_taipei(fake_yf):
    state, _ = fake_yf
    utc_idx = pd.date_range("2026-09-10 01:00", periods=1, freq="60min", tz="UTC")
    state["frame"] = pd.DataFrame({"Open": [1.0], "High": [1.0], "Low": [1.0],
                                   "Close": [1.0], "Volume": [1]}, index=utc_idx)
    df = yahoo.intraday(["2330"], {}, "60m", "730d")
    assert df.iloc[0]["ts"] == "2026-09-10T09:00:00+08:00"

    naive_idx = pd.date_range("2026-09-10 09:00", periods=1, freq="60min")
    state["frame"] = pd.DataFrame({"Open": [1.0], "High": [1.0], "Low": [1.0],
                                   "Close": [1.0], "Volume": [1]}, index=naive_idx)
    df = yahoo.intraday(["2330"], {}, "60m", "730d")
    assert df.iloc[0]["ts"] == "2026-09-10T09:00:00+08:00"


def test_intraday_batches_and_keeps_partial_on_error(fake_yf):
    state, calls = fake_yf
    codes = [f"{2300 + i}" for i in range(5)]

    def frame_for(tickers):
        if "2303.TW" in tickers:
            raise RuntimeError("Yahoo 掛了")
        return _multi_frame(list(tickers), n=1)

    state["frame"] = frame_for
    df = yahoo.intraday(codes, {}, "60m", "730d", batch=2)
    assert [c["tickers"] for c in calls] == [["2300.TW", "2301.TW"], ["2302.TW", "2303.TW"], ["2304.TW"]]
    assert sorted(df["code"].unique()) == ["2300", "2301", "2304"], "失敗那批略過，其餘保留"


def test_intraday_all_failed_or_empty_returns_empty(fake_yf):
    state, _ = fake_yf
    state["error"] = RuntimeError("boom")
    assert yahoo.intraday(["2330"], {}, "60m", "730d").empty
    state["error"] = None
    state["frame"] = pd.DataFrame()
    assert yahoo.intraday(["2330"], {}, "60m", "730d").empty
    assert yahoo.intraday([], {}, "60m", "730d").empty


# ------------------------------------------------------------------ 4xx 要把回應內容記下來
# 真實事故（2026-09-19）：FinMind 對每一個資料集都回 400，而 http.get 只寫
# 「回 400，不重試」—— 唯一能判斷原因（token 失效？帳號等級不足？參數改了？）的
# 回應內容整個被丟掉，連續三輪空轉都查不出根因。

class _Resp4xx:
    def __init__(self, status, text, payload=None):
        self.status_code = status
        self.text = text
        self._payload = payload
        self.headers = {"Content-Type": "application/json"}

    def json(self):
        if self._payload is None:
            raise ValueError("不是 JSON")
        return self._payload


def _fake_session(resp):
    class _S:
        def get(self, url, **kw):
            return resp
    return lambda: _S()


def test_四百的回應內容會進log(monkeypatch, caplog):
    body = '{"msg":"Your level is register. Please update your user level","status":400}'
    monkeypatch.setattr(http, "session", _fake_session(_Resp4xx(400, body)))
    with caplog.at_level("WARNING"):
        assert http.get("https://example.invalid/api") is None
    assert "Your level is register" in caplog.text, \
        "沒有回應內容的 4xx 日誌等於沒有線索，下一個人修不了"


def test_四百時finmind會記下失敗原因(monkeypatch, tmp_path):
    monkeypatch.setattr(http, "_QUOTA_FILE", tmp_path / "quota.json")
    monkeypatch.setattr(http, "_last_error", None)
    payload = {"msg": "Your level is register. Please update your user level", "status": 400}
    monkeypatch.setattr(http, "session",
                        _fake_session(_Resp4xx(400, str(payload), payload)))

    assert http.finmind_get("TaiwanStockMonthRevenue", data_id="2330") is None
    err = http.finmind_last_error()
    assert err["status"] == 400 and err["dataset"] == "TaiwanStockMonthRevenue"
    assert "register" in err["msg"]


def test_其他來源的4xx行為不變(monkeypatch, caplog):
    """error_body 只給 finmind_get 用；其他來源還是一律拿到 None，
    不然 twse/tdcc 那些「拿到東西就當成資料」的呼叫端會把錯誤訊息當資料解析。"""
    monkeypatch.setattr(http, "session", _fake_session(_Resp4xx(400, "Bad Request")))
    assert http.get("https://example.invalid/api") is None
    assert http.get("https://example.invalid/api", error_body=True) == {
        "status": 400, "msg": "Bad Request"}


# ================================================================== TechNews 分類篩選
#
# Andy 2026-09-21：「今日事件這邊的科技新聞請確實篩選跟科技有關的，
# 我發現很多無關的，例如醫療科技等等」。
# 下面每一組標籤都是從資料湖 data/news 的真實 technews 記錄抄下來的，不是想像的資料。

from pipeline.sources import news  # noqa: E402

# （標題, 標籤, 應該落在哪一格）—— 標籤原封不動取自資料湖
TECHNEWS_CASES = [
    # --- Andy 截圖點名的四則，全部不該留在科技
    ("腫瘤完全消失！美男童接受實驗性 CAR-T 療法，肝癌治癒且一年未復發",
     "生物科技,醫療科技,CAR-T 療法,兒童癌症,癌症,肝癌", None),
    ("每天一杯手搖飲代價有多大？哈佛最新研究：胃癌風險狂飆 2.5 倍",
     "生物科技,科技生活,醫療科技,代糖,健康,含糖飲料,幽門桿菌,慢性發炎", None),
    ("腸道細菌會影響情緒嗎？研究發現它們可能牽動大腦化學訊號",
     "生物科技,醫療科技,腦腸系統,腸腦軸", None),
    ("拒當盤子，購買二手電腦零件必看的六大避險心法與驗貨訣竅",
     "3C,3C周邊,科技生活,電腦,二手交易,二手電腦,交易平台,信用卡", None),
    # --- 生醫題目被順手標上「晶片」：強拒絕要壓得過硬訊號
    ("全球首創「多器官晶片」問世：重現腫瘤擴散、加速抗癌新藥開發",
     "半導體,晶片,生物科技,醫療科技,器官,多器官晶片,抗癌,毫米", None),
    # --- 天文／地科／基礎科學
    ("水星冷卻收縮之路尚未結束，新研究：縮水速度比過去預估快 30%",
     "天文,自然科學,太陽系,水星,皺脊,行星收縮", None),
    # --- 生活化的 AI 題目：有 AI 標籤也不該進科技
    ("自拍照丟給 ChatGPT 求變美？實測真相：建議多是舊招，照片還可能被留存",
     "AI 人工智慧,ChatGPT,國際觀察,社群,AI 生成,Glow-up,提示詞,隱私", None),
    # --- 半導體供應鏈：一定要留
    ("CPO 題材太熱估值過高！大摩降評大立光至中立、減碼玉晶光",
     "CPO,iPhone,半導體,鏡頭,FAU,大立光,玉晶光", "科技"),
    ("AI 需求旺  村田製作所：「大膽評估」擴增 MLCC 產能",
     "AI 人工智慧,國際貿易,零組件,AI 伺服器,MLCC,村田製作所", "科技"),
    ("CPO 鬼故事嚇崩 CCL 三雄！大摩霸氣喊台光電、台燿逢低就是買點",
     "AI 人工智慧,CPO,PCB,半導體,尖端科技,財經,零組件,CCL", "科技"),
    # --- 硬訊號要壓得過弱拒絕：半導體廠的人才／房市／能源新聞仍然是科技
    ("AI 擴產潮遇人力瓶頸，美半導體業 2030 年恐面臨逾 15 萬人才缺口",
     "AI 人工智慧,人力資源,半導體,國際觀察,晶圓,晶片,AI 晶片,SK 海力士", "科技"),
    ("2026 年全球資料中心用電需求估年增 31%，電網供應缺口自 2028 年擴大",
     "AI 人工智慧,伺服器,能源科技,電力儲存,AI,AI 伺服器,供電,散熱", "科技"),
    # --- 3C 是弱拒絕不是強拒絕：帶筆電硬訊號的機種新聞要留
    ("打破入門機框架！Googlebook 規格曝光，搭 15.3 吋 OLED 螢幕與 Core Ultra 5 處理器",
     "3C,Android,Google,筆記型電腦,Gemini,Googlebook,lenovo,聯想", "科技"),
    # --- 泛科技（AI／資安／軟體）：沒有硬訊號但也沒被拒絕，留
    ("最新 AI 代理模擬世界結果出爐，說謊、偷竊、串通繞過安全護欄樣樣來",
     "AI 人工智慧,資訊安全,AI 代理,AI 越獄,Emergence AI,Emergence World,密語,黑話", "科技"),
    # --- 改標總經：央行、升息、油價、關稅
    ("高盛：聯準會比預期偏鷹  預料 10 月將再升息", "國際金融,財經,Fed,升息,通膨", "總經"),
    ("AI 通膨來襲？央行：短期可控、長期生產力提升將降壓",
     "AI 人工智慧,財經,金融政策,AI,央行,經濟成長,通膨", "總經"),
    ("彭博：傳美國將產能過剩關稅延至下週川習會後宣布",
     "國際觀察,國際貿易,川普,川習會,習近平,關稅", "總經"),
    ("電價暫不調整，台電爭取 711 億元撥補、12 月再議", "能源科技,台電,漲價,電價", "總經"),
    # --- 改標台股：ETF／基金的行情題
    ("台股 ETF 超級除息週！總計 13 檔年化配息率飆破 10% 一次看",
     "AI 人工智慧,半導體,證券,財經,台股 ETF,年化配息率,超級除息週", "台股"),
    # --- 但「台股」兩個字本身不算行情題：台積電的新聞還是科技
    ("費半跳水衝擊台股力守 4 萬 7 關卡，台積電創高營收力抗空軍",
     "證券,財經,ASIC,CoWoS,先進封裝,台積電,台股,晶圓代工", "科技"),
]


@pytest.mark.parametrize("title,tags,want", TECHNEWS_CASES)
def test_technews分類(title, tags, want):
    assert news.classify_technews(title, tags) == want, f"分錯了：{title}"


def test_technews分類遇到空標籤不會炸():
    """RSS 偶爾不給 category，標籤是空字串。這時只能看標題，而且不可以丟例外。"""
    assert news.classify_technews("台積電 2 奈米量產", "") == "科技"
    assert news.classify_technews("", "") is None
    assert news.classify_technews(None, None) is None


def test_technews抓回來會重新分類而且不收的直接丟掉(monkeypatch):
    """整份 RSS 不是每一則都是台股科技族群的事 —— technews() 要自己重分類。

    用假的 RSS 回應（真實標籤），不打真 API。
    """
    pytest.importorskip("feedparser")
    rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <item>
    <title>CPO 題材太熱估值過高！大摩降評大立光至中立</title>
    <link>https://technews.tw/2026/09/20/cpo-1/</link>
    <pubDate>Sat, 20 Sep 2026 01:30:00 +0000</pubDate>
    <description>大摩報告</description>
    <category>半導體</category><category>CPO</category>
  </item>
  <item>
    <title>腸道細菌會影響情緒嗎？</title>
    <link>https://technews.tw/2026/09/20/gut/</link>
    <pubDate>Sat, 20 Sep 2026 02:00:00 +0000</pubDate>
    <description>研究</description>
    <category>生物科技</category><category>醫療科技</category>
  </item>
  <item>
    <title>高盛：聯準會比預期偏鷹  預料 10 月將再升息</title>
    <link>https://technews.tw/2026/09/20/fed/</link>
    <pubDate>Sat, 20 Sep 2026 03:00:00 +0000</pubDate>
    <description>高盛</description>
    <category>國際金融</category><category>升息</category>
  </item>
</channel></rss>"""
    monkeypatch.setattr(http, "get", lambda *a, **k: rss)
    df = news.technews()
    assert len(df) == 2, "醫療那則應該被丟掉"
    assert set(df["category"]) == {"科技", "總經"}
    assert df[df.category == "科技"].iloc[0]["title"].startswith("CPO")
    # 日期仍然要吃回應裡的 pubDate 轉台北，不是執行當下的日期
    assert set(df["date"]) == {"2026-09-20"}


def test_篩選器在真實評估集上的precision與recall沒有退步():
    """護欄：清單是放在 config.py 讓人調的，調壞了要當場被擋下來。

    評估集是 docs/fixtures/technews_labels.tsv（121 則人工標註，
    取自資料湖 data/news 裡 363 則真實 technews 的每 3 則第 1 則）。
    門檻 0.85 是 Andy 這一批的驗收標準；現況遠高於此，掉到 0.85 以下代表清單被改壞了。
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "eval_news", Path(__file__).resolve().parent.parent / "scripts" / "eval_news_tech_filter.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    res = mod.evaluate(mod.load_labels())
    assert res["precision"] >= 0.85, f"precision 掉到 {res['precision']:.3f}"
    assert res["recall"] >= 0.85, f"recall 掉到 {res['recall']:.3f}"
