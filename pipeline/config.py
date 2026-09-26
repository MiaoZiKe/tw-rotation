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
    # v4：大盤／櫃買／台指期的日 K（給總覽那三張圖的歷史週期用）。
    # Yahoo 的櫃買代號 ^TWOII 已經壞掉、台指期沒有免費代號，所以改走 FinMind：
    #   TaiwanStockPrice(TAIEX / TPEx) 與 TaiwanFuturesDaily(TX)
    "index_ohlc":         ["date", "symbol"],
    # v5：60 分 K（Andy 2026-09-18 拍板保留 730 天）。
    # 以前分 K 完全不存，每次部署都從零重抓 400 檔，害部署 14 分鐘裡有 13 分 43 秒在這一步
    # —— 見 DECISIONS #155（通則：會重複用到的就要存）與 #156（分 K 的分層策略）。
    # 1/5/15 分只要當天，不進湖；240 分、週、月都由這一層推出來。
    "intraday_60m":       ["ts", "code"],
    # v7（2026-09-25）：大盤三張圖 1H／4H 用的指數與台指期分 K。
    # symbol：TSE（^TWII）/ OTC（^TWOII）/ FUT（台指期日盤）/ FUT_N（夜盤）；
    # interval：60m（Yahoo 保留 730 天，當長歷史）/ 15m（Yahoo 60 天，補最近的細節）。
    # 跟個股的 intraday_60m 分開：那張表的增量起點是「全表最後一根」，混進指數會互相干擾。
    # v8（2026-09-26）：interval 多一個 1m ＝ 證交所 mis 當日分時檔（TSE／OTC／FUT 同一個來源），
    #   每個交易日盤後自己存、自己累積（見 sources/mis.index_minute_bars）。多一欄 src="mis" 標來源；
    #   舊列沒有這欄（讀出來是 NaN），不影響 key。同一天有 1m 時 build 以 1m 為準（真實量、同口徑）。
    # v10（2026-09-26）：台指期多一個 1m 來源 src="taifex"＝期交所每筆成交合成（日盤 FUT＋夜盤 FUT_N，
    #   近月、真實盤中高低與口數；見 sources/taifex.py）。同一盤兩個來源都有時 taifex ＞ mis：
    #   寫入時 run_daily 不讓 mis 蓋掉已有 taifex 的那幾天，build 也照 src 排優先。
    "index_intraday":     ["ts", "symbol", "interval"],
    # v6：重大訊息（公開資訊觀測站 t187ap04）。與 news 分開存 ——
    # 新聞是媒體寫的，重大訊息是公司自己公告的，M4 事件面要否決進場靠的是後者。
    "material_news":      ["news_id"],
    # v9（2026-09-26）：上櫃／興櫃公司的官網網址（給 Logo 抓取用）。
    # 為什麼不寫進 company_info：store.append() 同 key 會**整列**以後到的為準，
    # 只帶 code＋website 的列會把 company_info 的名稱、產業、市場別全部蓋成空值。
    # 上市的網址 company_info 本來就有（t187ap03_L 的「網址」），這張表只補上櫃／興櫃。
    "company_website":    ["code"],
}

# 按「月」分割的表（其餘一律按年）。
# 為什麼要這個：`store.append()` 每次會**重寫整個分割檔**，而 data/ 每天都會 commit 進 repo。
# 60 分 K 一年約 100 萬列，照年分割的話每天的資料 commit 都要重寫 26 MB，
# 一年下來 git 歷史會多好幾 GB。按月分割之後每天只重寫當月那一個檔（約 1 MB）。
PARTITION_MONTHLY: set[str] = {"intraday_60m", "index_intraday"}

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
    # 重大訊息（公司自己公告的，不是媒體寫的）。2026-09-14 的 probe fixture 兩支都回 200。
    "material_news_twse": "/opendata/t187ap04_L",
    "material_news_tpex": "/opendata/t187ap04_O",
}

# 證交所「基本市況報導」即時報價。2026-09-14 加入白名單（DECISIONS #108）——
# 它是證交所官網前台自己在打的那支，跟使用條款禁爬的 www.twse.com.tw/rwd/... 是不同主機。
# 用途：openapi 的日收落後一個交易日時，用它把「今天」補起來（見 sources/mis.py 的口徑說明）。
MIS_QUOTE = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
# 大盤當日分時（就是「基本市況報導」那張加權走勢圖的來源）。
# 它的 infoArray[0] 直接附當天的開高低收、昨收與成交金額，
# 用來在 openapi 還沒給今天的時候補 market_daily（加權指數那格數字）。
MIS_CHART_TSE = "https://mis.twse.com.tw/stock/data/mis_ohlc_TSE.txt"
# 大盤三張圖的「當日分時」三個檔（DECISIONS #121 登記的就是這三個，跟 getStockInfo.jsp 同一台主機）。
# 2026-09-26 起管線盤後把它們存成 1 分 K 進 index_intraday，櫃買與台指期的多日分 K 才有來源
# （Yahoo ^TWOII 回空、台指期沒有 Yahoo 代號、FinMind 分 K 要付費等級）。
# ⚠ 只放這三個檔名；期交所（mis.taifex.com.tw）的夜盤分時沒有進管線白名單，不在這裡。
MIS_CHART_FILES = {
    "TSE": MIS_CHART_TSE,                                              # 加權 t00
    "OTC": "https://mis.twse.com.tw/stock/data/mis_ohlc_OTC.txt",      # 櫃買 o00
    "FUT": "https://mis.twse.com.tw/stock/data/futures_chart.txt",     # 台指期（只有日盤）
}

# 臺灣期貨交易所「每日期貨每筆成交資料」（2026-09-26 查證，見 docs/source_whitelist_taifex_tpex.md）。
# 政府資料開放平臺 資料集 20668，授權＝政府資料開放授權條款－第 1 版（提供機關：金管會證期局）；
# 期交所下載頁只留前 30 個交易日。用途：台指期（TX）近月 1 分 K（日盤 FUT＋夜盤 FUT_N）進 index_intraday。
# ⚠ 只抓這個資料集的逐筆檔本身，不抓期交所其他網頁；mis.taifex.com.tw（盤中夜盤分時）仍然不在管線白名單。
# 頁面上要標出處：「臺灣期貨交易所（政府資料開放平臺 資料集 20668）」。
TAIFEX_TICKS_PAGE = "https://www.taifex.com.tw/cht/3/dlFutPrevious30DaysSalesData"
TAIFEX_TICKS_CSV = ("https://www.taifex.com.tw/file/taifex/Dailydownload/DailydownloadCSV/"
                    "Daily_{y}_{m}_{d}.zip")
TAIFEX_TICK_PRODUCT = "TX"            # 臺股期貨（大台）；小台 MTX 不收
TAIFEX_TICK_LOOKBACK_DAYS = 45        # 30 個交易日 ≈ 42 個日曆日，多留幾天給連假
TAIFEX_TICK_MAX_FILES = 35            # 一輪最多下載幾個檔（第一次跑會把窗內 30 個左右一次補完）
TAIFEX_TICK_MAX_BYTES = 300_000_000   # 單檔上限（全部期貨商品一天的逐筆，壓縮後約數十 MB）

TPEX_OPENAPI = "https://www.tpex.org.tw/openapi/v1"
TPEX_ENDPOINTS = {
    "price_daily":  "/tpex_mainboard_daily_close_quotes",
    "company_info": "/mopsfin_t187ap03_O",
}

# 上櫃／興櫃公司基本資料（只拿「網址」一欄給 Logo 用）。兩個候選依序試，第一個拿到就停：
#   1. 證交所 OpenAPI 的 opendata/t187ap03_O —— 同一台主機已經在用 t187ap04_O（上櫃重大訊息），
#      但 t187ap03_O 這支**沒有實測過**（容器連不到外網），拿不到就記 log 換下一個。
#   2. 櫃買 OpenAPI 的 mopsfin_t187ap03_O —— TPEX_ENDPOINTS 早就登記了，但櫃買對雲端 IP 常回 403。
# 興櫃（t187ap03_R）同理只試證交所 OpenAPI。不碰 mopsfin.twse.com.tw 的 CSV（不在白名單）。
COMPANY_WEBSITE_ENDPOINTS = [
    ("TPEX", TWSE_OPENAPI + "/opendata/t187ap03_O"),
    ("TPEX", TPEX_OPENAPI + TPEX_ENDPOINTS["company_info"]),
    ("EMERGING", TWSE_OPENAPI + "/opendata/t187ap03_R"),
]

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

# ---------------------------------------------------------------- TechNews 分類再判定
#
# 為什麼要這一段（Andy 2026-09-21：「今日事件這邊的科技新聞請確實篩選跟科技有關的，
# 我發現很多無關的，例如醫療科技等等」）：
# 以前 `technews()` 是把 TechNews RSS 的**每一則**都標成「科技」。但 TechNews 科技新報
# 本來就涵蓋天文、醫療、健康、生活科學，於是「腫瘤完全消失！CAR-T 療法」
# 「腸道細菌會影響情緒嗎」「二手電腦零件避險心法」全都跑進科技格。
#
# 這個網站的「科技」要回答的是 **「跟台股科技族群的資金流有關的事」**，不是泛科技新聞。
# 判斷主力用 RSS **自己的分類標籤**（`keywords` 欄，來源自己標的，比猜標題可靠太多），
# 標題關鍵字只在標籤沒給訊號時當補強。
#
# 四份清單的分工（順序就是判定順序，寫在 `sources/news.py:classify_technews()`）：
#   1. HARD  硬訊號 —— 出現就是科技，壓得過 SOFT_DENY（半導體廠的人才／電價／房市新聞還是科技）
#   2. STRONG_DENY 強拒絕 —— 連 HARD 都壓不過（生醫研究會被順手標上「晶片」，
#      例如「全球首創多器官晶片」其實是抗癌新藥的題目）
#   3. SOFT_DENY 弱拒絕 —— 只在沒有 HARD 時生效（生活、3C 開箱、軍武、航太、能源、房產…）
#   4. SOFT  弱允許 —— 沒有 HARD 也沒被拒絕時，有這些才算科技（AI／資安／軟體這種泛科技題目）
#
# ★ 改清單之前先看一眼 `scripts/eval_news_tech_filter.py`，它會拿資料湖裡的真實新聞
#   重算 precision／recall，改完跑一次就知道有沒有改壞。

# 1) 硬訊號：台股科技族群的產業鏈本身。出現任一個就留在「科技」。
#    只放「講到它幾乎一定是在講電子業」的標籤 —— 例如「材料」不放（中資收購鎳礦也叫材料），
#    「材料、設備」才放（那是 TechNews 的半導體設備材料分類）。
NEWS_TECH_HARD_TAGS = {
    # 半導體上中下游
    "半導體", "晶片", "晶圓", "晶圓代工", "IC 設計", "記憶體", "封裝測試", "先進封裝",
    "處理器", "GPU", "cpu", "dram", "AI 晶片", "半導體材料", "半導體設備", "先進製程",
    "光罩", "SiC", "GaN", "功率半導體", "矽智財", "晶片股",
    # 零組件與材料設備
    "零組件", "材料、設備", "被動元件", "MLCC", "PCB", "載板", "CCL", "銅箔基板",
    "散熱", "電源", "電源 IC", "電池", "燃料電池",
    # 光電、通訊、面板
    "光通訊", "矽光子", "CPO", "光模組", "光電科技", "面板", "OLED",
    "網通設備", "5G", "光互連",
    # 系統、終端、車用
    "伺服器", "AI 伺服器", "筆記型電腦", "筆電", "手機", "Android 手機", "智慧手機",
    "摺疊手機", "xR/AR/VR/MR", "穿戴式裝置", "汽車科技", "電動車", "自動化",
    # 台股權值核心（提到它就是在講台股科技的資金流）。
    # 只放這兩家 —— 再往下放（輝達、聯發科…）會把「麥可貝瑞的 AI 空單」這種
    # 純市場題也拉進科技格，那該是總經。
    "台積電", "鴻海",
}

# 2) 強拒絕：即使同時被標了硬訊號也不算科技。
#    只放「一旦出現，整篇的主題幾乎一定不是電子業」的領域標籤。
#    醫療科技放在這裡是因為 Andy 直接點名，而且 TechNews 會把生醫題目順手標上「晶片」
#    （「全球首創多器官晶片」= 抗癌新藥平台，不是半導體）。
#    ★ 代價：真的出現「半導體廠打進醫材供應鏈」時會被誤砍。
#      目前資料湖 363 則裡只有 1 則同時有醫療科技與硬訊號，而那 1 則本來就該砍；
#      之後若誤砍變多，就把醫療科技降到 SOFT_DENY 再重跑評估腳本。
NEWS_TECH_STRONG_DENY_TAGS = {
    "醫療科技", "天文", "自然科學", "環境科學", "生態保育", "科技趣聞",
    "食品科技", "農業科技", "旅遊",
}

# 3) 弱拒絕：沒有硬訊號時就不算科技。
#    這些領域**本身**不是台股科技族群（能源、軍武、航太、房產、生活、娛樂、社群、人資），
#    但只要同一則也帶了硬訊號（例如「資料中心用電」同時標了 AI 伺服器），硬訊號說了算。
NEWS_TECH_SOFT_DENY_TAGS = {
    "生物科技", "科技生活", "科技教育", "人力資源", "職場", "房地產",
    "3C", "3C周邊", "3C手機",
    "能源科技", "電力儲存", "太陽能", "核能", "氫能", "淨零減碳", "ESG",
    "軍事科技", "航太科技", "無人機", "交通運輸", "自駕車",
    "電子娛樂", "遊戲軟體", "數位內容", "數位廣告", "社群",
    "公司治理",  # 單獨出現通常是人事／組織題，帶硬訊號時不受影響
}

# 4) 弱允許：泛科技題目（AI、資安、軟體、雲端、新創）。
#    沒有硬訊號、也沒被拒絕時，有這些才留在科技。
#    AI 人工智慧 放這裡而不是 HARD —— 363 則裡有 133 則帶它，放 HARD 會把
#    「自拍照丟給 ChatGPT 求變美」「AI 拍照教練」整批放進來。
NEWS_TECH_SOFT_TAGS = {
    "AI 人工智慧", "AI", "AI 模型", "AI 代理", "AI 基礎建設", "AI 資料中心", "資料中心",
    "尖端科技", "量子電腦", "機器人", "資訊安全", "軟體、系統", "雲端", "網路",
    "IPO", "財報", "市場動態", "新創", "科技政策", "數位通訊",
}

# 補強用的標題關鍵字（★ 只在標籤給不出訊號時才看，標籤永遠優先）。
NEWS_TECH_TITLE_HINTS = (
    "半導體", "晶圓", "晶片", "台積電", "聯發科", "鴻海", "記憶體", "封裝", "面板",
    "伺服器", "光通訊", "矽光子", "CPO", "載板", "被動元件", "MLCC", "散熱", "網通",
    "先進製程", "EUV", "HBM", "代工", "AI", "機器人",
)

# ---------------------------------------------------------------- 被篩掉之後改標到哪
#
# 「不是科技」不代表「沒有價值」：講日股／美股行情、央行利率、關稅、油價的那些，
# 改標成「總經」比直接丟掉誠實（Andy 2026-09-21 的指示）。真的哪一格都不屬於的才不收。
#
# 只用**明確的財經／政策標籤**，不用「財經」——363 則裡有 91 則帶「財經」，
# 連「易飛網包機戰術」都有，拿它當總經會把一堆公司新聞倒進總經格。
NEWS_MACRO_TAGS = {
    "國際金融", "金融政策", "國際貿易", "證券", "理財", "Fintech", "數位貨幣",
    "加密貨幣", "升息", "通膨", "油價", "公債殖利率", "美國公債", "美股",
}
NEWS_MACRO_TITLE_HINTS = (
    "央行", "聯準會", "Fed", "升息", "降息", "利率", "通膨", "GDP", "匯率",
    "油價", "關稅", "公債", "殖利率", "美股", "日圓", "電價", "景氣",
)

# 台股行情／ETF 題目：帶「證券」標籤又在講 ETF 與配息的，那是台股不是總經，更不是科技。
# ★ 刻意不放「台股」兩個字 —— 「費半跳水衝擊台股，台積電創高營收」是科技題，
#   放進來會把台積電的新聞整批倒進台股格。只認基金產品的字眼。
NEWS_TW_MARKET_TITLE_HINTS = ("ETF", "基金", "受益人", "開募", "除息", "配息", "定期定額")

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

# ---------------------------------------------------------------- 公司 Logo（2026-09-26）
# 來源選擇、條款查證、商標風險與關閉方式：docs/logo_sources.md。
# ★ 整批關掉：把 LOGOS_ENABLED 的預設改成 "0"（或在 workflow 設環境變數 LOGOS_ENABLED=0）。
#   關掉之後：回補不再抓；build_payload 輸出空的 logos.json 並刪掉 site/data/logos/，
#   前端全部退回字母頭像。已經進 repo 的 data/logos/*.png 要另外刪（見 docs 的「關閉方式」）。
LOGOS_ENABLED = os.environ.get("LOGOS_ENABLED", "1").strip() not in ("0", "false", "False", "")
LOGOS_SUBDIR = "logos"                 # data/logos/<code>.png ＋ data/logos/_index.json
LOGOS_INDEX_NAME = "_index.json"       # 代號 → 來源、網域、抓取日、雜湊、狀態
LOGOS_STATE_NAME = "logo_progress.json"  # data/_state/ 底下：每輪摘要、失敗清單、下一次到期日
LOGO_PX = 64                           # 統一輸出 64×64 PNG（等比縮放、置中、透明補邊，不裁不拉）
LOGO_MIN_PX = 32                       # 原圖長邊小於這個 ＝「過小」：Google s2 等第三方來源一律不收；官網的見下兩行
# 第三版（2026-09-26）：官網找不到 ≥48 的圖時，官網最大的那張只要 ≥16px 就收成「低解析」Logo（索引記 lowres）。
# 前端只顯示 20～32px，16px 官方 favicon 在那個尺寸幾乎是原生大小，比字母頭像好認；照原尺寸存、不放大重採樣。
LOGO_LOWRES_MIN_PX = 16                # 官網圖示原圖長邊的最低門檻（再小就是 1×1 追蹤點、間隔圖那種）
LOGO_LOWRES_BELOW = 48                 # 原圖長邊小於這個 ＝ 低解析：照原尺寸存（只補透明邊成正方形），不放大到 64
# Google s2 回的 16～31px 要不要也收成低解析。預設不收（任務要求「官方來源」；s2 找不到時回 16px 預設地球）。
# 2026-09-26 索引推算：too_small 裡有 23 家是「官網沒有任何圖、只有 s2 給 16px」，打開這個就會多救這 23 家
# （地球這類預設圖仍會被「≥3 個網域同一張」擋下）。要開就改 "1" 並把 LOGO_STRATEGY 加一。
LOGO_LOWRES_ALLOW_S2 = os.environ.get("LOGO_LOWRES_ALLOW_S2", "0").strip() in ("1", "true", "True")
LOGOS_PER_RUN = 300                    # 每輪最多處理幾家（避免被各家官網或 Google 當成濫用）
LOGO_REFRESH_DAYS = 90                 # 抓到的 Logo 多久重抓一次（Logo 很少換）
LOGO_RETRY_DAYS = 30                   # 沒抓到的多久再試一次（官網改版、暫時掛掉）
LOGO_TIME_BUDGET_SEC = 900             # 一輪最多花 15 分鐘，時間到就收手、下一輪接續
LOGO_WORKERS = 6                       # 同時抓幾家（每家都是不同網域；Google 備援一次最多 6 個並行）
LOGO_GENERIC_DOMAINS = 3               # 同一張圖出現在 ≥ 這麼多個不同網域 ＝ 預設圖（地球、架站商圖示），不當 Logo
# 備援：Google 的 favicon 服務（非官方、無文件、無 SLA；找不到時回 404＋16px 地球）。
# 2026-09-26 第二版改要 sz=128：它對有大圖的網站會回 128px，對只有小圖的網站仍回 16px ——
# 所以收不收仍看「實際回來的尺寸」（< LOGO_MIN_PX 一樣判太小），不看我們要了多大。
LOGO_GOOGLE_S2 = "https://www.google.com/s2/favicons?domain={domain}&sz=128"
# 取圖策略版本（2026-09-26 第二版：多候選取最大、manifest、og:image、頁首 logo 圖、SVG、跟轉址）。
# 索引裡每筆會記抓的時候用的是第幾版；狀態是「太小／找不到」而且版本比這個舊的，下一輪立刻重試，
# 不等 30 天 —— 策略變好了，舊結論就不算數。之後再改策略、想讓失敗的重來一次，把這個數字加一即可。
# 第三版（2026-09-26 深夜）：官網小圖當低解析後備；預設圖拒收後繼續往下找（不直接判失敗）；
# 「太小／找不到／預設圖」三種最先重試。好圖不重抓、不覆寫。
LOGO_STRATEGY = 3
LOGO_MAX_TRIES = 10                    # 每家最多下載幾個圖檔候選（找到 ≥64px 的正方形圖示就提早停）
LOGO_MAX_ASPECT = 5.0                  # 長寬比超過 5:1 的橫條字標，縮進 64×64 只剩 12px 高，判「太小」（不裁切）
LOGO_SVG_MAX_BYTES = 500_000           # SVG 超過這個大小不畫（防止病態檔案卡住整輪）
