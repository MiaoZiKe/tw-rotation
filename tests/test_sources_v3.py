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



# ------------------------------------------------------------ 櫃買／台指期分 K（2026-09-25，假回應）
def _kbar_rows(day="2026-09-24", minutes=("09:01:00", "09:59:00", "10:01:00", "13:30:00"), extra=None):
    rows = []
    for i, m in enumerate(minutes):
        r = {"date": day, "minute": m, "open": 100 + i, "high": 101 + i, "low": 99 + i,
             "close": 100.5 + i, "volume": 0}
        r.update(extra or {})
        rows.append(r)
    return rows


def test_index_kbar_to_60m(monkeypatch):
    from pipeline.compute.intraday_bars import kbar_to_60m
    from pipeline.util import http
    monkeypatch.setattr(http, "finmind_get", lambda *a, **k: _kbar_rows(extra={"stock_id": "TPEx"}))
    out = kbar_to_60m(finmind.index_kbar("2026-09-24", "TPEx"), symbol="OTC")
    assert list(out["symbol"].unique()) == ["OTC"]
    assert list(out["interval"].unique()) == ["60m"]
    assert len(out) == 3                       # 09、10、13 三根
    first = out.iloc[0]
    assert first["high"] == 102 and first["low"] == 99   # 09:01 與 09:59 兩根的真實極值


def test_index_kbar_bad_columns_logs_head(monkeypatch, caplog):
    from pipeline.util import http
    monkeypatch.setattr(http, "finmind_get", lambda *a, **k: [{"weird": 1}])
    with caplog.at_level("WARNING"):
        assert finmind.index_kbar("2026-09-24", "TPEx").empty
    assert "weird" in caplog.text               # 前 200 字真的進了 log


def test_index_kbar_denied_returns_empty(monkeypatch):
    from pipeline.util import http
    monkeypatch.setattr(http, "finmind_get", lambda *a, **k: None)
    assert finmind.index_kbar("2026-09-24", "TPEx").empty
    assert finmind.futures_kbar("2026-09-24").empty


def test_futures_kbar_near_month_and_night(monkeypatch):
    from pipeline.compute.intraday_bars import kbar_to_60m
    from pipeline.util import http
    rows = (_kbar_rows(minutes=("08:46:00", "09:30:00"), extra={"contract_date": "202610", "volume": 50})
            + _kbar_rows(minutes=("09:30:00",), extra={"contract_date": "202611", "volume": 1})
            + _kbar_rows(minutes=("09:30:00",), extra={"contract_date": "202610/202611", "volume": 999})
            + _kbar_rows(minutes=("15:30:00",), extra={"contract_date": "202610", "volume": 5}))
    monkeypatch.setattr(http, "finmind_get", lambda *a, **k: rows)
    out = kbar_to_60m(finmind.futures_kbar("2026-09-24"), futures=True)
    assert set(out["symbol"]) == {"FUT", "FUT_N"}
    day = out[out["symbol"] == "FUT"]
    assert len(day) == 1 and day.iloc[0]["volume"] == 100   # 價差單與遠月都沒混進來


def test_yahoo_index_tries_candidates(monkeypatch):
    import sys, types
    asked = []

    def dl(sym, **k):
        asked.append(sym)
        if sym in ("^TWII", "^TWOTCI"):
            idx = pd.DatetimeIndex(["2026-09-24 09:00"]).tz_localize("Asia/Taipei")
            return pd.DataFrame({"Open": [1.0], "High": [1.0], "Low": [1.0], "Close": [1.0],
                                 "Volume": [0]}, index=idx)
        return pd.DataFrame()
    monkeypatch.setitem(sys.modules, "yfinance", types.SimpleNamespace(download=dl))
    out = yahoo.index_intraday("60m", "5d")
    assert asked == ["^TWII", "^TWOII", "^TWOTCI"]
    assert set(out["symbol"]) == {"TSE", "OTC"}


def test_collect_otc_60m_skips_when_in_lake(monkeypatch):
    from pipeline import run_daily
    from pipeline.util import store
    called = []
    monkeypatch.setattr(store, "read", lambda t: pd.DataFrame(
        {"ts": ["2026-09-24T09:00:00+08:00"], "symbol": ["OTC"]}))
    monkeypatch.setattr(finmind, "index_kbar", lambda *a, **k: called.append(a) or pd.DataFrame())
    assert run_daily.collect_otc_60m("2026-09-24").empty
    assert not called                          # 湖裡已有那天就不花額度
    monkeypatch.setattr(store, "read", lambda t: pd.DataFrame())
    run_daily.collect_otc_60m("2026-09-24")
    assert [a[1] for a in called] == finmind.OTC_KBAR_IDS   # 依序試每個候選代號



def test_backfill_otc_marks_unavailable_after_empties(monkeypatch):
    from pipeline import run_backfill
    from pipeline.util import http, store
    days = pd.DataFrame({"date": ["2026-09-21", "2026-09-22", "2026-09-23", "2026-09-24"],
                         "symbol": ["OTC"] * 4})
    monkeypatch.setattr(store, "read", lambda t: days if t == "index_ohlc" else pd.DataFrame())
    monkeypatch.setattr(http, "finmind_budget_left", lambda: 500)
    monkeypatch.setattr(http, "finmind_last_error", lambda: None)
    calls = []
    monkeypatch.setattr(finmind, "index_kbar", lambda d, i, **k: calls.append((d, i)) or pd.DataFrame())
    flag = {}
    assert run_backfill._backfill_otc_kbar(flag, pd.DataFrame(), 60) is True
    assert "otc_unavailable" in flag
    assert len(calls) == 3 * len(finmind.OTC_KBAR_IDS)   # 3 天就停，不會把 60 天的額度燒完


# ------------------------------------------------------------------ mis 當日分時檔 → 1 分 K（2026-09-26）
# Andy：「加權 櫃買 台指期，這三個到底有沒有統一的來源」。三個檔同一台主機（DECISIONS #121），
# 盤後存成 1 分 K 自己累積。容器連不到 mis，格式照 docs/fixtures/mis_ohlc_tse_20260914.json（真的打回來的）
# 與 worker.js／market3.js 註解裡的實測描述：TSE／OTC {t, ts, c, s}；FUT {t, c, s}（沒有 ts）。
import json as _json  # noqa: E402

from pipeline.compute import intraday_bars as _ib  # noqa: E402
from pipeline.sources import mis as _mis  # noqa: E402

_MIS_FIX = Path(__file__).resolve().parents[1] / "docs" / "fixtures" / "mis_ohlc_tse_20260914.json"


def _ems(day: str, hhmm: str) -> str:
    """台北時間 → mis 檔裡的 epoch 毫秒字串（檔案裡是字串）。"""
    return str(pd.Timestamp(f"{day} {hhmm}", tz="Asia/Taipei").value // 10**6)


def _chart(minutes, closes, vols, *, day="2026-09-25", with_ts=True, info=None, static=None):
    arr = []
    for m, c, s in zip(minutes, closes, vols):
        o = {"t": _ems(day, m), "c": str(c), "s": str(s)}
        if with_ts:
            o["ts"] = m.replace(":", "") + "00"
        arr.append(o)
    out = {"infoArray": [info] if info is not None else [], "ohlcArray": arr,
           "rtcode": "0000", "rtmessage": "OK"}
    if static is not None:
        out["staticObj"] = static
    return _json.dumps(out)


def _wall(s: str) -> int:
    return int((pd.Timestamp(s) - pd.Timestamp("1970-01-01")).total_seconds())


def test_mis_chart_real_tse_fixture():
    """真的打回來的加權分時檔：日期取自檔案（09-14），第一根開盤用 infoArray 的真開盤，量＝張×1000。"""
    df = _mis.parse_index_chart("TSE", _MIS_FIX.read_text(encoding="utf-8"))
    assert len(df) == 1
    r = df.iloc[0]
    assert r["ts"] == "2026-09-14T09:01:00+08:00"
    assert (r["symbol"], r["interval"], r["src"]) == ("TSE", "1m", "mis")
    assert r["open"] == 46010.74 and r["close"] == 45550.39
    assert r["high"] == 46010.74 and r["low"] == 45550.39
    assert r["volume"] == 33505 * 1000


def test_mis_chart_otc_chain_open_and_units():
    info = {"d": "20260925", "o": "390.00", "h": "395", "l": "389", "z": "392", "y": "388"}
    txt = _chart(["09:01", "09:02", "09:03"], [391.0, 390.5, 392.0], [120, 80, 95], info=info)
    df = _mis.parse_index_chart("OTC", "﻿" + txt)          # 帶 BOM 也要解得開
    assert list(df["open"]) == [390.0, 391.0, 390.5]            # 開＝前一分收；第一根＝infoArray 開盤
    assert list(df["high"]) == [391.0, 391.0, 392.0]
    assert list(df["low"]) == [390.0, 390.5, 390.5]
    assert list(df["volume"]) == [120_000, 80_000, 95_000]       # 張 → 股
    assert set(df["ts"].str[:10]) == {"2026-09-25"}


def test_mis_chart_futures_no_ts_no_date_uses_epoch():
    """futures_chart.txt 沒有 ts、infoArray 也不一定有 d：交易日一律取每一筆的 epoch，量是口數不乘。"""
    txt = _chart(["08:46", "08:47", "13:45"], [45100, 45110, 45200], [900, 300, 1500],
                 with_ts=False, info={"o": "45090"})
    df = _mis.parse_index_chart("FUT", txt)
    assert list(df["ts"]) == ["2026-09-25T08:46:00+08:00", "2026-09-25T08:47:00+08:00",
                              "2026-09-25T13:45:00+08:00"]
    assert list(df["volume"]) == [900.0, 300.0, 1500.0]
    assert df.iloc[0]["open"] == 45100                          # 沒有 d 就不拿 infoArray 開盤冒充


def test_mis_chart_residual_file_dated_by_content():
    """週六清晨抓到的是週五的殘留檔：歸在週五（檔案內容），跟執行當下是哪天無關。"""
    txt = _chart(["13:29", "13:30"], [100.0, 101.0], [1, 2], day="2026-09-25",
                 info={"d": "20260925", "o": "99"})
    df = _mis.parse_index_chart("TSE", txt)
    assert set(df["ts"].str[:10]) == {"2026-09-25"}


def test_mis_chart_label_mismatch_rejects_whole_file(caplog):
    """時間標籤跟 epoch 對不上＝時間戳語意變了：整檔不收（寫進只增不改的湖就洗不掉），log 附回應前 200 字。"""
    bad = _json.loads(_chart(["09:01", "09:02"], [1.0, 2.0], [1, 1]))
    for o in bad["ohlcArray"]:
        o["ts"] = "170100"
    with caplog.at_level("WARNING"):
        assert _mis.parse_index_chart("TSE", _json.dumps(bad)).empty
    assert "ohlcArray" in caplog.text                         # 前 200 字真的印出來了


def test_mis_chart_out_of_session_rejects():
    """epoch 被當成台北時間送（整體偏 8 小時）→ 全部落在時段外 → 不收。"""
    txt = _chart(["01:01", "01:02"], [1.0, 2.0], [1, 1], with_ts=False)
    assert _mis.parse_index_chart("FUT", txt).empty


def test_mis_chart_bad_payloads_return_empty(caplog):
    with caplog.at_level("WARNING"):
        assert _mis.parse_index_chart("TSE", "<html>系統維護中</html>").empty
    assert "系統維護中" in caplog.text
    assert _mis.parse_index_chart("TSE", _json.dumps({"rtcode": "5000", "ohlcArray": []})).empty
    assert _mis.parse_index_chart("TSE", _json.dumps({"rtcode": "0000"})).empty
    assert _mis.parse_index_chart("TSE", _json.dumps([1, 2])).empty


def test_mis_chart_cumulative_volume_guard():
    """萬一 s 變成累計量（單調、最後一筆＝總量、加總遠大於總量），改用差分，不把量放大幾十倍。"""
    mins = [f"09:{i:02d}" for i in range(1, 21)]
    cum = [10 * (i + 1) for i in range(20)]                     # 10, 20, … 200
    txt = _chart(mins, [100.0] * 20, cum, info={"d": "20260925", "o": "100"}, static={"tv": "200"})
    df = _mis.parse_index_chart("TSE", txt)
    assert df["volume"].sum() == 200 * 1000


def test_mis_index_minute_bars_one_source_failing(monkeypatch):
    """三個檔各自可失敗：一個 None、一個丟例外，剩下那個照收。"""
    good = _chart(["09:01"], [390.0], [5], info={"d": "20260925", "o": "390"})

    def fake_get(url, **k):
        if "OTC" in url:
            return good
        if "futures" in url:
            raise RuntimeError("連線被重置")
        return None
    monkeypatch.setattr(_mis.http, "get", fake_get)
    df = _mis.index_minute_bars()
    assert set(df["symbol"]) == {"OTC"}


def test_mis_minute_append_dedup(tmp_path, monkeypatch):
    """重複抓不重複寫；後一次比較完整時只多出新的分鐘，同一分鐘以後到的為準。"""
    from pipeline.util import store
    monkeypatch.setattr(config, "DATA", tmp_path)
    info = {"d": "20260925", "o": "100"}
    half = _mis.parse_index_chart("OTC", _chart(["09:01", "09:02"], [100.0, 101.0], [1, 2], info=info))
    full = _mis.parse_index_chart("OTC", _chart(["09:01", "09:02", "09:03"], [100.0, 101.5, 102.0],
                                                [1, 3, 4], info=info))
    assert store.append("index_intraday", half) == 2
    assert store.append("index_intraday", half) == 0
    assert store.append("index_intraday", full) == 1
    got = store.read("index_intraday").sort_values("ts")
    assert len(got) == 3 and got.iloc[1]["close"] == 101.5      # 09:02 那一分鐘被後到的蓋掉


def _mis_day(sym, day, base, unit_vol=10):
    """一整盤 09:01～13:30 的 1 分 K（走 parser，跟管線同一條路）。"""
    mins = [(pd.Timestamp(f"{day} 09:01") + pd.Timedelta(minutes=i)).strftime("%H:%M") for i in range(270)]
    closes = [base + i * 0.1 for i in range(270)]
    return _mis.parse_index_chart(sym, _chart(mins, closes, [unit_vol] * 270, day=day,
                                              info={"d": day.replace("-", ""), "o": str(base)}))


def test_build_minute_synth_15_60_240():
    """1 分 K → 15 分（格子開始時間）、1 小時（09～13）、4 小時（一盤一根），量加總＝真實量。"""
    out = _ib.build(_mis_day("OTC", "2026-09-25", 390.0))["OTC"]
    h1, h4, m15 = out["H1"], out["H4"], out["M15"]
    assert [b[0] for b in h1] == [_wall(f"2026-09-25 {h:02d}:00") for h in (9, 10, 11, 12, 13)]
    assert len(h4) == 1 and h4[0][0] == _wall("2026-09-25 09:00")
    assert h4[0][1] == 390.0 and h4[0][4] == pytest.approx(390.0 + 269 * 0.1)
    assert h4[0][5] == 270 * 10 * 1000
    assert m15[0][0] == _wall("2026-09-25 09:00") and all(b[0] % 900 == 0 for b in m15)
    assert m15[1][0] == _wall("2026-09-25 09:15")
    assert sum(b[5] for b in m15) == h4[0][5]
    assert out["src"]["mis_first"] == "2026-09-25" and out["src"]["mis_days"] == 1
    assert out["src"]["first"] == "2026-09-25" and out["src"]["days15"] == 1


def test_build_mis_wins_over_yahoo_same_day_and_keeps_history():
    """加權：Yahoo 歷史保留；同一天兩個來源都有時以 mis 為準（真實量、同口徑）。"""
    old = pd.DataFrame([{"ts": "2026-09-01T09:00:00+08:00", "symbol": "TSE", "interval": "60m",
                         "open": 1, "high": 2, "low": 1, "close": 2, "volume": 0}])
    dup = pd.DataFrame([{"ts": "2026-09-25T09:00:00+08:00", "symbol": "TSE", "interval": "15m",
                         "open": 999, "high": 999, "low": 999, "close": 999, "volume": 0}])
    out = _ib.build(pd.concat([old, dup, _mis_day("TSE", "2026-09-25", 45000.0)], ignore_index=True))["TSE"]
    assert out["H4"][0][4] == 2                                  # 09-01 的 Yahoo 還在
    assert out["H4"][-1][1] == 45000.0 and out["H4"][-1][5] > 0  # 09-25 用 mis（不是 999、量不是 0）
    assert out["src"]["first"] == "2026-09-01" and out["src"]["mis_first"] == "2026-09-25"
    assert out["src"]["days"] == 2


def test_build_three_symbols_same_logic_multi_day():
    """三個指數同一套邏輯：各自從第一個存到的交易日開始累積，天數讀資料。"""
    lake = pd.concat([_mis_day(s, d, b) for s, b in (("TSE", 45000.0), ("OTC", 390.0), ("FUT", 45100.0))
                      for d in ("2026-09-24", "2026-09-25")], ignore_index=True)
    out = _ib.build(lake)
    for s in ("TSE", "OTC", "FUT"):
        assert len(out[s]["H4"]) == 2 and len(out[s]["H1"]) == 10
        assert out[s]["src"]["mis_first"] == "2026-09-24" and out[s]["src"]["mis_days"] == 2


def test_collect_index_minute_records_days(monkeypatch):
    from pipeline import run_daily
    df = _mis_day("FUT", "2026-09-25", 45100.0).head(3)
    monkeypatch.setattr(_mis, "index_minute_bars", lambda: df)
    got = run_daily.collect_index_minute()
    assert len(got) == 3
    assert run_daily.RESULT["index_minute_days"] == {"FUT": ["2026-09-25"]}


# ================================================================== 期交所每筆成交 → 台指期 1 分 K（2026-09-26）
# ⚠ fixture 是**依期交所公告的欄位名稱與社群文件描述自製的**，不是實抓（容器連不到外網）：
#   tests/fixtures/taifex_Daily_2026_09_25.csv（cp950；成交日期寫「歸屬日」的版本）。
# 第一次 Actions 實際下載之後，若格式不同，log 會印出回應前 200 字，照那段改 parser 與這個 fixture。

import io as _io  # noqa: E402
import zipfile as _zipfile  # noqa: E402

from pipeline.sources import taifex  # noqa: E402

TAIFEX_FIX = Path(__file__).resolve().parent / "fixtures" / "taifex_Daily_2026_09_25.csv"


def _zip_of(text_bytes: bytes, name: str = "Daily_2026_09_25.csv") -> bytes:
    buf = _io.BytesIO()
    with _zipfile.ZipFile(buf, "w") as z:
        z.writestr(name, text_bytes)
    return buf.getvalue()


def _csv(rows, head=True) -> bytes:
    lines = ["成交日期,商品代號,到期月份(週別),成交時間,成交價格,成交數量(B+S),近月價格,遠月價格,開盤集合競價"] if head else []
    lines += [f"{d},{p:<7},{m:<11},{t},{px},{q},-,-," for d, p, m, t, px, q in rows]
    return ("\n".join(lines) + "\n").encode("cp950")


def test_taifex_parse_fixture_zip_only_tx():
    t = taifex.parse_ticks(_zip_of(TAIFEX_FIX.read_bytes()), file_id="2026-09-25")
    assert not t.empty
    assert set(t["month"]) == {"202610", "202611", "202610/202611", "202610W1"}   # MTX 已濾掉
    assert 45959 in set(t["time"])                                                # 前導 0 被吃掉也認得
    assert (t["file"] == "2026-09-25").all()
    assert t["qty"].sum() == 20 + 4 + 6 + 2 + 2 + 4 + 100 + 8 + 2 + 2 + 40 + 10 + 10 + 6 + 2


def test_taifex_parse_bad_header_logs_head(caplog):
    caplog.set_level("WARNING")
    bad = "<html><body>系統維護中</body></html>".encode("cp950")
    assert taifex.parse_ticks(bad, file_id="x").empty
    assert "系統維護中" in caplog.text                                             # 回應前 200 字進 log


def test_taifex_parse_bad_values_over_threshold_rejects(caplog):
    caplog.set_level("WARNING")
    rows = [("20260925", "TX", "202610", "08:45:00", "23000", "2")] * 10          # 時間格式變了
    assert taifex.parse_ticks(_csv(rows), file_id="y").empty
    assert "格式變了" in caplog.text


def test_taifex_night_attr_convention_wall_time():
    """成交日期寫歸屬日（晚上、凌晨同一天）→ 晚上那段是前一個交易日、凌晨是隔一個日曆日。"""
    t = taifex.parse_ticks(TAIFEX_FIX.read_bytes(), file_id="2026-09-25")
    w = taifex.attach_wall_time(t, known_days=["2026-09-24"])
    night = w[w["session"] == "night"]
    assert str(night["wall"].min()) == "2026-09-24 15:00:00"
    assert str(night[night["time"] == 45959]["wall"].iloc[0]) == "2026-09-25 04:59:59"
    assert set(night["open_day"]) == {"20260924"}
    assert not (w["time"] == 53000).any()                                          # 時段外丟掉
    day = w[w["session"] == "day"]
    assert str(day["wall"].min()) == "2026-09-25 08:45:00"


def test_taifex_night_attr_without_prev_day_is_dropped():
    """找不到前一個交易日就不收（寫錯的時間進只增不改的湖就洗不掉）。"""
    t = taifex.parse_ticks(TAIFEX_FIX.read_bytes(), file_id="2026-09-25")
    w = taifex.attach_wall_time(t, known_days=[])
    assert (w["session"] == "night").sum() == 0
    assert (w["session"] == "day").sum() > 0


def test_taifex_night_weekend_attr_goes_back_to_friday():
    """週一的檔：夜盤歸屬週一，晚上那段是週五、凌晨那段是週六。"""
    rows = [("20260928", "TX", "202610", "150000", "23000", "2"),
            ("20260928", "TX", "202610", "010000", "23010", "2"),
            ("20260928", "TX", "202610", "084500", "23020", "2")]
    t = taifex.parse_ticks(_csv(rows), file_id="2026-09-28")
    w = taifex.attach_wall_time(t, known_days=["20260925"])
    got = sorted(str(x) for x in w["wall"])
    assert got == ["2026-09-25 15:00:00", "2026-09-26 01:00:00", "2026-09-28 08:45:00"]


def test_taifex_night_calendar_convention_detected():
    """成交日期寫日曆日（凌晨比晚上晚一天）→ 直接用，不需要交易日曆。"""
    rows = [("20260924", "TX", "202610", "150000", "23000", "2"),
            ("20260925", "TX", "202610", "030000", "23010", "2"),
            ("20260925", "TX", "202610", "084500", "23020", "2")]
    t = taifex.parse_ticks(_csv(rows), file_id="2026-09-25")
    w = taifex.attach_wall_time(t, known_days=[])
    got = sorted(str(x) for x in w["wall"])
    assert got == ["2026-09-24 15:00:00", "2026-09-25 03:00:00", "2026-09-25 08:45:00"]
    assert set(w.loc[w["session"] == "night", "open_day"]) == {"20260924"}


def test_taifex_ticks_to_1m_near_month_and_ohlc():
    t = taifex.parse_ticks(TAIFEX_FIX.read_bytes(), file_id="2026-09-25")
    bars = taifex.ticks_to_1m(taifex.attach_wall_time(t, known_days=["20260924"]), divisor=2.0)
    assert set(bars["src"]) == {"taifex"} and set(bars["interval"]) == {"1m"}
    n = bars[bars["symbol"] == "FUT_N"].set_index("ts")
    b = n.loc["2026-09-24T15:00:00+08:00"]
    # 近月 202610：15:00:00 23000×20、15:00:12 23005×4、15:00:59 22995×6（週契約 15:00:01 不算）
    assert (b["open"], b["high"], b["low"], b["close"], b["volume"]) == (23000, 23005, 22995, 22995, 15.0)
    assert "2026-09-24T15:02:00+08:00" not in n.index                              # 次月那筆不混進來
    assert "2026-09-24T15:03:00+08:00" not in n.index                              # 價差單丟掉
    assert "2026-09-25T05:00:00+08:00" in n.index
    d = bars[bars["symbol"] == "FUT"].set_index("ts")
    b = d.loc["2026-09-25T08:45:00+08:00"]
    assert (b["open"], b["high"], b["low"], b["close"], b["volume"]) == (23200, 23210, 23190, 23190, 30.0)
    assert "2026-09-25T09:00:00+08:00" not in d.index                              # 次月


def test_taifex_rollover_picks_each_session_own_near_month():
    """換月：結算日前一盤 202609 量大、下一盤 202610 量大 → 各盤各自選，不混月份。"""
    rows = [("20260915", "TX", "202609", "090000", "22000", "100"),
            ("20260915", "TX", "202610", "090000", "22100", "10"),
            ("20260916", "TX", "202609", "090000", "22050", "10"),
            ("20260916", "TX", "202610", "090000", "22150", "100")]
    t = taifex.parse_ticks(_csv(rows), file_id="mix")
    bars = taifex.ticks_to_1m(taifex.attach_wall_time(t), divisor=2.0).set_index("ts")
    assert bars.loc["2026-09-15T09:00:00+08:00", "close"] == 22000
    assert bars.loc["2026-09-16T09:00:00+08:00", "close"] == 22150


def test_taifex_vol_divisor_checks_against_official():
    assert taifex.vol_divisor({}, {}) == 2.0
    assert taifex.vol_divisor({"20260925": 200.0}, {"20260925": 100.0}) == 2.0
    assert taifex.vol_divisor({"20260925": 101.0}, {"20260925": 100.0}) == 1.0
    assert taifex.vol_divisor({"20260925": 500.0}, {"20260925": 100.0}) == 2.0     # 都不像 → 預設


def test_taifex_minute_bars_incremental_and_idempotent(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    from pipeline.util import store
    monkeypatch.setattr(config, "DATA", tmp_path)
    monkeypatch.setattr(config, "STATE", tmp_path / "_state")
    calls = []

    def fake_fetch(day):
        calls.append(day)
        if day == "2026-09-25":
            return 200, _zip_of(TAIFEX_FIX.read_bytes())
        return 404, None

    monkeypatch.setattr(taifex, "fetch_day", fake_fetch)
    now = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)                       # 週六
    a = taifex.minute_bars(known_days=["20260924"], now=now, max_files=5)
    assert not a.empty and set(a["symbol"]) == {"FUT", "FUT_N"}
    st = taifex.load_state()
    assert "2026-09-25" in st["done"]
    assert "2026-09-21" in st["absent"] or "2026-09-22" in st["absent"]           # 舊的 404 記成假日
    assert "2026-09-25" not in st["absent"]
    n1 = store.append("index_intraday", a)
    assert n1 == len(a)
    calls.clear()
    taifex.minute_bars(known_days=["20260924"], now=now, max_files=5)
    assert "2026-09-25" not in calls                                              # 處理過的不再下載
    assert not any(d in calls for d in st["absent"])                              # 假日也不再試
    assert store.append("index_intraday", a) == 0                                 # 重跑不多一列


def test_taifex_fetch_non_zip_is_treated_as_missing(monkeypatch):
    monkeypatch.setattr(http, "get_bytes",
                        lambda *a, **k: (200, "<html>查無資料</html>".encode("cp950"), "text/html", "u"))
    assert taifex.fetch_day("2026-09-25") == (404, None)
    monkeypatch.setattr(http, "get_bytes", lambda *a, **k: None)
    assert taifex.fetch_day("2026-09-25") == (0, None)


def test_mis_fut_does_not_overwrite_taifex_days(tmp_path, monkeypatch):
    from pipeline import run_daily
    from pipeline.util import store
    monkeypatch.setattr(config, "DATA", tmp_path)
    store.append("index_intraday", pd.DataFrame([
        {"ts": "2026-09-25T08:45:00+08:00", "symbol": "FUT", "interval": "1m", "open": 1, "high": 1,
         "low": 1, "close": 1, "volume": 1, "src": "taifex"}]))
    mis_df = pd.DataFrame([
        {"ts": "2026-09-25T08:46:00+08:00", "symbol": "FUT", "interval": "1m", "close": 2, "src": "mis"},
        {"ts": "2026-09-25T09:01:00+08:00", "symbol": "OTC", "interval": "1m", "close": 3, "src": "mis"},
        {"ts": "2026-09-26T08:46:00+08:00", "symbol": "FUT", "interval": "1m", "close": 4, "src": "mis"}])
    out = run_daily.drop_days_with_taifex(mis_df)
    assert list(out["ts"]) == ["2026-09-25T09:01:00+08:00", "2026-09-26T08:46:00+08:00"]


def test_build_prefers_taifex_over_mis_same_day():
    from pipeline.compute import intraday_bars as ib
    rows = []
    for m, c in ((45, 100.0), (46, 101.0)):
        rows.append({"ts": f"2026-09-25T08:{m}:00+08:00", "symbol": "FUT", "interval": "1m",
                     "open": c, "high": c + 5, "low": c - 5, "close": c, "volume": 10.0, "src": "taifex"})
    rows.append({"ts": "2026-09-25T08:47:00+08:00", "symbol": "FUT", "interval": "1m",
                 "open": 999.0, "high": 999.0, "low": 999.0, "close": 999.0, "volume": 1.0, "src": "mis"})
    rows.append({"ts": "2026-09-24T09:00:00+08:00", "symbol": "FUT", "interval": "1m",
                 "open": 90.0, "high": 90.0, "low": 90.0, "close": 90.0, "volume": 1.0, "src": "mis"})
    out = ib.build(pd.DataFrame(rows))["FUT"]
    h4 = {ib._day_str(b[0] - 9 * 3600): b for b in out["H4"]}
    assert h4["2026-09-25"][4] == 101.0 and h4["2026-09-25"][2] == 106.0          # mis 的 999 沒混進來
    s = out["src"]
    assert s["m1_first"] == "2026-09-24" and s["m1_days"] == 2
    assert s["taifex_first"] == "2026-09-25" and s["taifex_days"] == 1
    assert s["mis_days"] == 1
