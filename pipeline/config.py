"""全域設定。所有路徑、端點、參數集中在這裡，其他模組不硬編碼。"""
from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------- 路徑
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"          # Parquet 資料湖（append-only）
SITE = ROOT / "site"          # 靜態網站
SITE_DATA = SITE / "data"     # 前端讀的預算好的 JSON
GROUPS_DIR = ROOT / "pipeline" / "groups"
STATE = DATA / "_state"       # last_run.json 等執行狀態

for _p in (DATA, SITE_DATA, STATE):
    _p.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- 資料表
# 每一張表 = data/<table>/year=<YYYY>/part.parquet
# key 欄位用來做 append 時的去重（同一筆資料重跑不會變成兩列）
TABLES: dict[str, list[str]] = {
    "price_daily":        ["date", "code"],   # 個股日行情
    "valuation_daily":    ["date", "code"],   # 本益比 / 殖利率 / 股價淨值比
    "margin_daily":       ["date", "code"],   # 融資融券
    "index_daily":        ["date", "index"],  # 各類股指數
    "market_daily":       ["date"],           # 大盤成交統計
    "inst_daily":         ["date", "code"],   # 三大法人買賣超（個股別）
    "revenue_monthly":    ["ym", "code"],     # 月營收
    "financial_q":        ["year", "quarter", "code"],  # EPS / 損益（單季值）
    "balance_q":          ["year", "quarter", "code"],  # 股本 / 淨值 / 總資產
    "dividend":           ["code", "year"],   # 股利
    "shareholding_weekly": ["date", "code", "level"],   # 集保股權分散
    "company_info":       ["code"],           # 公司基本資料 + 產業別
    "news":               ["news_id"],        # 新聞（含分類）
    "broker_views":       ["news_id", "code"], # 新聞裡引述的券商目標價
    "intl_daily":         ["date", "symbol"], # 國際指數 / 匯率 / 債息
    "macro":              ["date", "series"], # FRED 總經
    # v3：FinMind 股利公告（一期展開成 cash / stock 兩列）與除權息結果（參考價、當日開盤）
    "dividend_events":    ["code", "period", "kind"],
    "dividend_results":   ["code", "date"],
}

# ---------------------------------------------------------------- 端點
TWSE_OPENAPI = "https://openapi.twse.com.tw/v1"
TWSE_ENDPOINTS = {
    # 已於 2026-09-10 逐一實測回應與欄位
    "price_daily":     "/exchangeReport/STOCK_DAY_ALL",
    "valuation_daily": "/exchangeReport/BWIBBU_ALL",
    "margin_daily":    "/exchangeReport/MI_MARGN",
    "index_daily":     "/exchangeReport/MI_INDEX",
    "market_daily":    "/exchangeReport/FMTQIK",
    "company_info":    "/opendata/t187ap03_L",
    "revenue_monthly": "/opendata/t187ap05_L",
    "financial_q":     "/opendata/t187ap14_L",
    "dividend":        "/opendata/t187ap45_L",
}

# 證交所「基本市況報導」即時報價。2026-09-14 加入白名單（DECISIONS #108）——
# 它是證交所官網前台自己在打的那支，跟使用條款禁爬的 www.twse.com.tw/rwd/... 是不同主機。
# 用途：openapi 的日收落後一個交易日時，用它把「今天」補起來（見 sources/mis.py 的口徑說明）。
MIS_QUOTE = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
# 大盤當日分時（就是「基本市況報導」那張加權走勢圖的來源）。
# 它的 infoArray[0] 直接附當天的開高低收、昨收與成交金額，
# 用來在 openapi 還沒給今天的時候補 market_daily（加權指數那格數字）。
MIS_CHART_TSE = "https://mis.twse.com.tw/stock/data/mis_ohlc_TSE.txt"

TPEX_OPENAPI = "https://www.tpex.org.tw/openapi/v1"
TPEX_ENDPOINTS = {
    "price_daily":  "/tpex_mainboard_daily_close_quotes",
    "company_info": "/mopsfin_t187ap03_O",
}

TDCC_URL = "https://opendata.tdcc.com.tw/getOD.ashx?id=1-5"

FINMIND_API = "https://api.finmindtrade.com/api/v4/data"
FINMIND_TOKEN = os.environ.get("FINMIND_TOKEN", "")
# 免費層：未帶 token 300 req/hr、帶 token 600 req/hr。留 15% 安全邊際。
FINMIND_HOURLY_LIMIT = 510 if FINMIND_TOKEN else 255

# 鉅亨網分類（爬蟲專家實測）：tech 科技、wd_macro 國際政經、tw_stock 台股
CNYES_NEWS_BASE = "https://api.cnyes.com/media/api/v1/newslist/category/"
CNYES_CATEGORIES = {"tw_stock": "台股", "tech": "科技", "wd_macro": "總經"}
CNYES_NEWS = CNYES_NEWS_BASE + "tw_stock"
TECHNEWS_RSS = "https://cdn.technews.tw/feed/"
UDN_MONEY_RSS = "https://money.udn.com/rssfeed/news/1001/5590?ch=money"

# 財報法定公告期限 —— 沒有實際公告日時用這個當「可用日」，寧可延後不可提前，
# 否則 walk-forward 檢驗會偷看未來（金融專家指出的致命問題）
FINANCIAL_DEADLINES = {1: ("05", "15"), 2: ("08", "14"), 3: ("11", "14"), 4: ("03", "31")}
REVENUE_DEADLINE_DAY = 10   # 月營收次月 10 日

FRED_API = "https://api.stlouisfed.org/fred/series/observations"
FRED_KEY = os.environ.get("FRED_API_KEY", "")
FRED_SERIES = {
    "FEDFUNDS": "聯邦基金利率",
    "CPIAUCSL": "美國 CPI",
    "PAYEMS": "非農就業",
    "DGS10": "美國十年期公債殖利率",
    "T10Y2Y": "十年減兩年利差",
    "UNRATE": "美國失業率",
}

# 國際連動盤（yfinance 代碼）
INTL_SYMBOLS = {
    "^SOX":   "費城半導體",
    "^IXIC":  "那斯達克",
    "^GSPC":  "標普500",
    "^TWII":  "台灣加權",
    "DX-Y.NYB": "美元指數",
    "^VIX":   "波動率指數",
    "TWD=X":  "美元兌台幣",
}

# ---------------------------------------------------------------- 參數
UNIVERSE_SIZE = int(os.environ.get("UNIVERSE_SIZE", "500"))  # 個股歷史回補檔數
BACKFILL_START = os.environ.get("BACKFILL_START", "2016-01-01")

HTTP_TIMEOUT = 30
HTTP_RETRIES = 3
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

# 綜合評分權重（階段 4 會用 walk-forward 檢驗後回頭調）
SCORE_WEIGHTS = {
    "flow": 0.40,          # M1 資金面
    "fundamental": 0.25,   # M2 基本面
    "technical": 0.30,     # M3 技術面
    "seasonality": 0.05,   # M4 季節性（樣本數少，權重刻意壓低）
}
