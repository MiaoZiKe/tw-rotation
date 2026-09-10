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
    "financial_q":        ["year", "quarter", "code"],  # EPS / 損益
    "dividend":           ["code", "year"],   # 股利
    "shareholding_weekly": ["date", "code", "level"],   # 集保股權分散
    "company_info":       ["code"],           # 公司基本資料 + 產業別
    "news":               ["news_id"],        # 新聞
    "intl_daily":         ["date", "symbol"], # 國際指數 / 匯率 / 債息
    "macro":              ["date", "series"], # FRED 總經
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

CNYES_NEWS = "https://api.cnyes.com/media/api/v1/newslist/category/tw_stock"
UDN_MONEY_RSS = "https://money.udn.com/rssfeed/news/1001/5590?ch=money"

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
