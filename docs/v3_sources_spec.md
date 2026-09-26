# v3 資料層擴充規格（交給爬蟲/回補 Agent）

先讀 `CLAUDE.md`。所有規則（不碰官網、append-only、可失敗、繁中註解）照舊。
**只准改這些檔案**：`pipeline/sources/finmind.py`、新檔 `pipeline/sources/yahoo.py`、
`pipeline/config.py`（只能在 `TABLES` 新增鍵、以及新增常數，不可改既有值）、
`pipeline/run_backfill.py`、`.github/workflows/backfill.yml`、
`tests/test_backfill.py`、新檔 `tests/test_sources_v3.py`。
其他檔案（build_payload、compute、site、run_daily、daily.yml）由另一個人同時在改，**不要動**。

開發環境的 egress 擋掉 FinMind 與 Yahoo，所以你**無法真的打 API**；下面附上實測回應樣本，
照樣本寫轉換與測試。所有來源函式失敗一律回空 DataFrame、不拋例外。

## 1. FinMind 新來源（`pipeline/sources/finmind.py`）

所有函式簽名比照既有 `month_revenue(code, start, *, wait=True)`，內部用
`http.finmind_get(dataset, data_id=code, start_date=start, wait_when_exhausted=wait)`。

### 1.1 `dividend_events(code, start)` → 表 `dividend_events`，key `["code", "period", "kind"]`
dataset `TaiwanStockDividend`，實測一筆：
```
{"AnnouncementDate":"2026-09-01","CashDividendPaymentDate":"2026-10-08","CashEarningsDistribution":7.00000137,
 "CashExDividendTradingDate":"2026-09-16","CashStatutorySurplus":0,"StockEarningsDistribution":0,
 "StockStatutorySurplus":0,"StockExDividendTradingDate":"","date":"2026-09-22","stock_id":"2330","year":"115年第1季"}
```
輸出欄位：`code, period(原始 year 字串，如 "115年第1季" 或 "114年"), kind("cash"|"stock"),
amount(cash = CashEarningsDistribution + CashStatutorySurplus；stock = StockEarningsDistribution + StockStatutorySurplus，單位元/股),
announce_date(AnnouncementDate), ex_date(cash→CashExDividendTradingDate、stock→StockExDividendTradingDate；空字串→None),
payment_date(cash→CashDividendPaymentDate，stock→None), fiscal_year(從 period 解析：民國年+1911，整數)`。
amount 為 0 的 kind 不輸出（一筆原始資料最多展開成 2 列）。

### 1.2 `dividend_results(code, start)` → 表 `dividend_results`，key `["code", "date"]`
dataset `TaiwanStockDividendResult`，實測一筆：
```
{"after_price":2248.99,"before_price":2255,"date":"2026-06-11","max_price":2470,"min_price":2025,"open_price":2250,
 "reference_price":2248.99,"stock_and_cache_dividend":6.000035,"stock_id":"2330","stock_or_cache_dividend":"息"}
```
輸出：`code, date(除權息日), kind("息"|"權"|"權息" 原字串), dividend(stock_and_cache_dividend), before_price, reference_price, open_price`。
（填息天數不在這裡算，由 build_payload 用行情算。）

### 1.3 `margin_history(code, start)` → 既有表 `margin_daily`（key `["date","code"]`）
dataset `TaiwanStockMarginPurchaseShortSale`，實測一筆：
```
{"MarginPurchaseBuy":728,"MarginPurchaseCashRepayment":6,"MarginPurchaseLimit":6483092,"MarginPurchaseSell":227,
 "MarginPurchaseTodayBalance":28474,"MarginPurchaseYesterdayBalance":27979,"OffsetLoanAndShort":0,
 "ShortSaleBuy":30,"ShortSaleCashRepayment":4,"ShortSaleLimit":6483092,"ShortSaleSell":0,
 "ShortSaleTodayBalance":2,"ShortSaleYesterdayBalance":36,"date":"2026-09-10","stock_id":"2330"}
```
欄位對應（單位都是張，與證交所 MI_MARGN 相同）：
`margin_balance=MarginPurchaseTodayBalance, margin_change=Today−Yesterday, short_balance=ShortSaleTodayBalance,
short_change=Today−Yesterday, margin_buy=MarginPurchaseBuy, margin_sell=MarginPurchaseSell,
short_sell=ShortSaleSell, short_cover=ShortSaleBuy, offset=OffsetLoanAndShort`。
既有 `margin_daily` 的欄位就是這 9 個 + date/code，請對齊（看 `pipeline/sources/twse.py` 的 MI_MARGN 轉換）。

### 1.4 `holding_history(code, start)` → 既有表 `shareholding_weekly`（key `["date","code","level"]`）
dataset `TaiwanStockHoldingSharesPer`（瀏覽器實測 CORS 失敗、無法取樣；依 FinMind 文件欄位為
`date, stock_id, HoldingSharesLevel, people, percent, unit`）。
`HoldingSharesLevel` 是字串級距，與 `tdcc.LEVEL_LABELS` 的標籤相同（"1-999"、"1,000-5,000"、…、
"1,000,001以上"；FinMind 可能寫成 "more than 1,000,001"、"total"、"差異數調整"）。
做一個寬鬆對照：去掉空白後比對 LEVEL_LABELS 的值；"more than 1,000,001" / "1,000,001以上" → 15；
"total"/"合計" → 17；"差異數調整" → 16；對不上的略過並 log 一次。
輸出欄位對齊 tdcc：`date, code, level, level_label, holders(people), shares(unit), pct(percent)`。
回應若是非 200（免費層可能不開放）→ 回空 DataFrame 即可。

### 1.5 `price_history` 起始日
既有函式已支援 start；實測 `TaiwanStockPrice` 從 1999 年就有資料（2330 於 1999-12-20 收 148.5）。
不用改，但回補要能用 `start="2000-01-01"`（見第 3 節）。

## 2. Yahoo 分 K（新檔 `pipeline/sources/yahoo.py`）

```python
def intraday(codes: list[str], markets: dict[str, str], interval: str, period: str,
             batch: int = 40) -> pd.DataFrame
```
- 代號轉 Yahoo 符號：`markets[code]=="TPEX"` → `f"{code}.TWO"`，其他 → `f"{code}.TW"`。
- 用 `yfinance.download(tickers, interval=interval, period=period, group_by="ticker",
  auto_adjust=False, progress=False, threads=True)` 分批（每批 `batch` 檔），批與批之間 `time.sleep(1.0)`。
- 回傳長格式 `ts(ISO 字串含時區偏移，台北時間 "+08:00"), code, open, high, low, close, volume`，
  丟掉 close 為 NaN 的列。單一代號時 yfinance 回的是單層欄位，多代號是 MultiIndex（ticker, field）——兩種都要處理。
- 任何例外只 log，回已成功的部分。**不進資料湖**（build_payload 直接用），所以不用註冊 TABLES。
- 支援 `interval` "60m" 與 "15m"；`period` "730d"、"60d"。

## 3. 回補計畫（`pipeline/run_backfill.py`）

### 3.1 新 jobs
在 `jobs` 清單加：
```
("dividend",  "dividend_events",  lambda c: finmind.dividend_events(c, start, wait=False)),
("divresult", "dividend_results", lambda c: finmind.dividend_results(c, start, wait=False)),
("margin",    "margin_daily",     lambda c: finmind.margin_history(c, start, wait=False)),
("holding",   "shareholding_weekly", lambda c: finmind.holding_history(c, start, wait=False)),
```
`FINANCIAL_KEYS`（ETF 跳過）加入 `dividend, divresult`（ETF 其實有配息，但先不抓）；`margin, holding` ETF 要抓。
`summary` 字典也要有這些鍵。

### 3.2 done_key 帶起始日
現在 `done_key = f"{key}:{code}"`。改成：`start == config.BACKFILL_START` 時維持原樣（相容既有進度檔），
否則 `f"{key}@{start}:{code}"`。`already_covered` 照舊（最早日期 ≤ start 就算補過）。

### 3.3 `--plan default`
新增 `--plan` 參數（與 `--datasets` 二擇一）。`plan="default"` 展開成依序執行的步驟：
```
PLAN_DEFAULT = [
  {"datasets": "revenue+financial+balance", "start": "2016-01-01", "scope": "universe"},
  {"datasets": "dividend+divresult",        "start": "2016-01-01", "scope": "universe"},
  {"datasets": "margin+holding",            "start": "2021-01-01", "scope": "universe"},
  {"datasets": "price",                     "start": "2000-01-01", "scope": "groups"},
]
```
- `scope=="groups"` → 只跑 `loader.membership()` 的成分股；`universe` → `target_codes(limit)`。
- 逐步驟呼叫既有 `run()`（把 `run` 改成可帶 `codes` 覆寫與 `datasets_key` 自訂）。
  某一步 `exhausted` 就停止整個計畫（後面的步驟下一小時再來）。
- 每一步完成時仍寫 `prog["complete"][datasets_key]`；整個計畫每一步都 done → `prog["complete"]["plan:default"] = {"done": True, ...}`；
  任一步未完成 → `"plan:default"` 的 done=False。
- 每月更新：計畫最後再加一步 `{"datasets": "dividend+divresult", "start": <今年-01-01>, "scope": "groups", "tag": "m<YYYY-MM>"}`，
  done_key 用 `f"{key}@{tag}:{code}"`，這樣每個月會重新抓一次成分股的股利公告（一個月約 260 次請求）。
  `complete["plan:default"]` 的 done 要包含這一步（所以每月 1 日之後計畫會自動變成未完成、再跑一輪）。

### 3.4 `already_covered` 對 dividend/holding
`dividend_events` 沒有 date 欄位 → 會走「沒有時間維度的表，有資料就算補過」→ 對月更新步驟會誤判成已補過。
處理：`already_covered` 加參數 `respect_time: bool=True`；月更新步驟傳 False（只看 done_key）。

## 4. `.github/workflows/backfill.yml`
- 排程觸發時改跑 `python -m pipeline.run_backfill --plan default`；guard 改成看 `complete["plan:default"]["done"]`。
- 手動觸發保留 `datasets` 選單，選項加入 `dividend+divresult`、`margin+holding`、`plan`（=跑 default 計畫）；`start_date` 照舊。
- 其他（checkout ref、concurrency、回寫、摘要）維持現狀。摘要多印 `plan:default` 狀態。

## 5. 測試
- `tests/test_sources_v3.py`：用上面的樣本 dict monkeypatch `http.finmind_get`，驗證每個新函式的欄位、單位、
  kind 展開、空字串日期→None、非 200→空 DataFrame。Yahoo：monkeypatch `yfinance.download` 回一個
  MultiIndex DataFrame 與一個單層 DataFrame，驗證長格式與時區字串。
- `tests/test_backfill.py`：加 plan 測試（兩步驟，第一步 exhausted 時第二步不跑；全部完成時 plan:default done=True；
  done_key 帶 start 的行為）。
- 跑 `python -m pytest tests/ -q` 全綠才算完成。

## 6. 交付
完成後在 `docs/v3_sources_spec.md` 底下加一節「實作備註」：列出實際新增的函式、表、以及任何與規格不同之處。

## 實作備註（2026-09-11）

### 新增的函式
- `pipeline/sources/finmind.py`
  - `dividend_events(code, start, *, wait=True)` → 表 `dividend_events`
  - `dividend_results(code, start, *, wait=True)` → 表 `dividend_results`
  - `margin_history(code, start, *, wait=True)` → 既有表 `margin_daily`（欄位與 `twse.margin_daily` 逐一對齊，測試有比對）
  - `holding_history(code, start, *, wait=True)` → 既有表 `shareholding_weekly`
  - 輔助：`fiscal_year_of(period)`（民國年+1911，也接受西元四位數）、`holding_level(label)`（寬鬆級距對照）
- `pipeline/sources/yahoo.py`（新檔）
  - `intraday(codes, markets, interval, period, batch=40)`、輔助 `symbol_of(code, markets)`
- `pipeline/run_backfill.py`
  - `done_key_of(key, code, start, tag=None)`、`datasets_key_of(datasets, start, tag=None)`
  - `run(datasets, limit, start, *, codes=None, datasets_key=None, tag=None, respect_time=True)`（舊的三個位置參數不變）
  - `monthly_step(today=None)`、`plan_steps(name, today=None)`、`run_plan(name, limit, today=None)`、`plan_is_done(prog, name, today=None)`
  - 模組常數：`DATA_KEYS`、`FINANCIAL_KEYS`（移到模組層並加入 dividend / divresult）、`PLAN_DEFAULT`、`PLANS`
  - CLI：`--plan {default}` 與 `--datasets` 互斥；`--plan` 時忽略 `--start`（各步驟自帶起始日）

### 新增的表（`config.TABLES`）
- `dividend_events`：key `["code", "period", "kind"]`
- `dividend_results`：key `["code", "date"]`
- config 只加了這兩個鍵，沒有新增其他常數（`PLAN_DEFAULT` 依第 3.3 節放在 `run_backfill.py`）。

### 與規格不同或規格沒講清楚的地方
1. **`plan:default` 的 done 帶月份。** 規格要求「每月 1 日之後計畫會自動變成未完成」，但進度檔裡的 `done` 不會自己變，
   所以 `complete["plan:default"]` 多記 `month`（月更新步驟的年月，台北時間）、`steps`（各步驟 done）、`stopped_at`。
   `backfill.yml` 的排程 guard 只有在 `done == true` **且** `month == 當月` 才跳過；`run_backfill.plan_is_done()` 是同一條規則的 Python 版。
2. **計畫步驟的 `complete` 鍵也帶起始日 / tag**（與 done_key 同規則）：`revenue+financial+balance` 從 2016 起維持舊鍵
   `balance+financial+revenue`；`price` 從 2000 起寫成 `price@2000-01-01`；月更新寫成 `dividend+divresult@m2026-09`。
   否則族群成分股 2000 年起的價量會跟既有的 `price`（全市場 2016 起）旗標互相覆蓋。
3. **`scope == "groups"` 不套 `--limit`**：成分股約兩百多檔，本來就該全補；`universe` 才走 `target_codes(limit)`。
4. **`dividend_events`**：`year` 為空的原始列略過；`announce_date / ex_date / payment_date` 保持 object dtype，
   空字串→`None`（pandas 3 的字串型別會把 None 變 NaN，所以特別處理）；`fiscal_year` 為 `Int64`。
5. **`holding_history`**：級距對照去空白、不分大小寫（"MORE THAN 1,000,001" 也對得上）；對不上的級距一次 log 一筆 warning
   並列出標籤；`holders` 用 `Int64`。實測樣本取不到，欄位名照 FinMind 文件（`HoldingSharesLevel / people / percent / unit`）。
6. **`margin_history`**：`MarginPurchaseTodayBalance` 缺值的列丟掉；數值欄位維持 FinMind 的整數，append 進既有 float64 表時由 pandas 自動升型。
7. **Yahoo**：代號去重；ticker 在 MultiIndex 的第一層或第二層都找；naive 時間索引視為台北時間、其他時區一律轉台北；
   `yf.download` 抓不到某一批只 log 該批並繼續；`import yfinance` 放在函式內（測試 monkeypatch `yfinance.download` 即可）。
8. **`backfill.yml`**：`datasets` 選單預設值從 `revenue+financial+balance` 改成 `plan`（排程沒有 inputs，用同一個預設值就會跑計畫）；
   摘要多印 `plan:default` 的月份、停在哪一步、各步驟狀態。
9. 測試：`tests/test_sources_v3.py` 33 個、`tests/test_backfill.py` 新增 6 個；全套 145 個通過（原本 106）。

---

## 7. 額度保護：資料集封印與 FinMind 健檢（2026-09-20 補）

### 7.1 為什麼加這一層

2026-09-19 連續三輪「歷史回補」空轉（run `35468233078` 等）：
`revenue` / `financial` / `balance` 每一檔都回 HTTP 400，
`run()` 判定「整組回空 ＝ 資料集不開放」的結論**只存在那一輪的記憶體裡**，
沒有寫進 `data/_state/backfill_progress.json`。於是：

1. 每一輪都重問全部 **506 檔**，把 FinMind 額度（有 token 510/hr）一次燒光；
2. 額度用盡 → `exhausted=True` → 計畫永遠停在第 1 步，
   後面的股利、融資券／集保、族群成分股價量四個步驟**永遠輪不到**；
3. `finished_all` 當時寫成「只要有 `unavailable` 就永遠不算完成」，
   等於一個確定不開放的資料集可以把整個計畫**永久鎖死**。

同一輪的**第一個** FinMind 請求是 `TaiwanStockPrice` + `data_id=TAIEX`（補指數歷史），
它也回 400 —— 這就是 `index_ohlc` 一直只有 32 個交易日的原因。

### 7.2 進度檔新增的兩個區塊

```jsonc
"unavailable": {                       // 判定為不開放的資料集（封印）
  "revenue": {
    "since": "2026-09-20T…",           // 第一次判定的時間
    "last_probe": "2026-09-20T…",      // 最近一次探測
    "probes": 3,
    "last_reason": "HTTP 400：Your level is register…"   // 上游回應原文
  }
},
"finmind_health": {                    // 每一輪開場的健檢結果
  "ok": false,
  "at": "2026-09-20T…",
  "probe": "TaiwanStockPrice/2330 since 2026-09-10",
  "detail": "HTTP 400：…"
}
```

### 7.3 規則

| 情境 | 行為 | 常數 |
|---|---|---|
| 某資料集整輪回空（≥3 檔）且一次都沒成功 | 寫進 `unavailable`，**不寫 done** | — |
| 同一輪連續回空太多次 | 本輪停問這個資料集，額度留給其他步驟 | `EMPTY_STREAK_LIMIT=20` |
| 封印期內 | **完全不發請求** | `UNAVAILABLE_RETRY_HOURS=24` |
| 封印超過 24 小時 | 只拿少量樣本重探 | `PROBE_CODES=5` |
| 探測拿到資料 | 解除封印，**本輪剩下的檔立刻恢復全量** | — |

**計畫什麼時候算完成**（`run()` 的 `finished_all`）：沒被限流、沒有抓取例外、
且沒有「**這一輪第一次**」被判定不開放的資料集。
已經封印過的資料集**不算未完成** —— 它不會因為我們一直等就開放，
拿整個計畫去陪葬是 2026-09-19 那三輪空轉的直接原因。

### 7.4 健檢（`finmind_reachable`）

`run_plan()` 與 `main()` 的 `--datasets` 路徑一開始先花 **1 次額度**問
「台積電最近 10 天的日線」——免費層一定拿得到的東西。

- 拿得到 → 是個別資料集的問題，交給封印機制。
- 拿不到 → **整把 token／帳號的問題**，整輪立刻停、一次請求都不再發，
  把上游回應原文寫進 `finmind_health.detail`，並在日誌寫明
  「到 FinMind 重產 token、更新 GitHub Secrets 的 `FINMIND_TOKEN`」。
  這一輪**不動** `complete["plan:default"]`，所以下一輪不會被工作流的 guard 跳過。

### 7.5 `http` 層

- `get()` 對不重試的 4xx（含 401/403）一律把**回應前 200 字**寫進 log。
  只記狀態碼等於把唯一的診斷資訊丟掉。
- 新參數 `error_body=True`（只有 `finmind_get` 用）：4xx 回
  `{"status": …, "msg": …}`，其他來源行為不變（仍然拿到 `None`）。
- `finmind_last_error()`：最近一次非 200 的 dataset / status / msg，
  供 `run_backfill` 寫進進度檔。

### 7.6 指數歷史

`backfill_indices()` 現在要求 `index_ohlc` 同時回到 `TSE` **與** `OTC` 才標 done
（那支函式一次抓兩個指數，只回到加權時它仍然「非空」，照舊標 done 會讓櫃買永遠只有 40 天）。

## 8. 大盤三張圖的 1 分 K：mis 當日分時檔自己累積（2026-09-26）

Andy：「加權 櫃買 台指期，這三個到底有沒有統一的來源，不是一個有一個沒有」。
當天分時三張本來就同一個來源；多日分 K 以前只有加權有（Yahoo `^TWII`），
櫃買 `^TWOII` 回空、台指期沒有 Yahoo 代號、FinMind 分 K 要付費等級（register 回 400）。

- 來源：`config.MIS_CHART_FILES` —— `mis_ohlc_TSE.txt`（t00）、`mis_ohlc_OTC.txt`（o00）、
  `futures_chart.txt`（台指期日盤）。三個都是 DECISIONS #121 登記過的、跟 `getStockInfo.jsp` 同一台主機。
  期交所 `mis.taifex.com.tw` 的夜盤分時**沒有進管線白名單**，不抓（前端經 Worker 讀的那條不受影響）。
- 函式：`mis.parse_index_chart(symbol, payload)`（純解析，可測）、`mis.index_minute_bars()`（抓三個檔，各自可失敗）；
  `run_daily.collect_index_minute()` 包成 `step("mis.index_minute")`，**每一個 phase 都跑**
  （含週末與清晨 news：那時檔案是上一個交易日的殘留，照內容歸日、去重，多一次保險）。
- 表：沿用 `index_intraday`（key `["ts","symbol","interval"]`），`interval="1m"`、多一欄 `src="mis"`。
  - `ts`：每一筆 epoch `t` 換成台北時間（`2026-09-25T09:01:00+08:00`）—— **交易日取自檔案內容**。
  - 開＝前一分鐘收盤（第一根用 `infoArray.o`，日期對得上才用）；高低＝開收兩者極值（檔案只有分鐘收盤）。
  - 量：TSE／OTC 的 `s` 是張 → 存股（×1000，跟 `index_ohlc` 同口徑）；FUT 是口，照存。
- 防呆（上游改格式時不把錯的時間寫進只增不改的湖）：
  TSE／OTC 的 `ts` 標籤跟 epoch 對不上、或點落在交易時段外，超過 5% 就整檔不收，log 附回應前 200 字；
  `s` 若變成累計量（單調、最後一筆≈`staticObj.tv`）改用差分。
- 合成（`compute/intraday_bars.build`）：同一盤挑一種顆粒，1m（mis）＞15m＞60m（Yahoo）。
  加權的 Yahoo 歷史保留，同一天以 mis 為準；1m 聚合成 M15（格子開始時間）、H1、H4。
  `src` 多給 `first／last／mis_first／mis_days`，前端寫「櫃買分 K 自 YYYY-MM-DD 起累積（N 天）」。
- 限制：過去的補不回來；櫃買、台指期從第一個抓到的交易日開始長。夜盤沒有多日分 K。
- 測試：`tests/test_sources_v3.py` 的 `test_mis_chart_*`、`test_build_*`（假回應，不打真 API）。

## 9. 公司 Logo（2026-09-26）

完整的來源選擇、條款查證、商標風險與**關閉方式**在 `docs/logo_sources.md`；這裡只記規格。

- 來源：主＝公司官網（`<link rel="apple-touch-icon">`／`<link rel="icon">` → `/apple-touch-icon.png` → `/favicon.ico`），
  備援＝`https://www.google.com/s2/favicons?domain=<網域>&sz=64`。官網 robots.txt 不允許就兩個都不用。
- 網址：上市用 `company_info.website`；上櫃／興櫃用新表 `company_website`（key `["code"]`，欄位 `code, website, market, src, asof`），
  端點候選在 `config.COMPANY_WEBSITE_ENDPOINTS`（證交所 OpenAPI `t187ap03_O`／`t187ap03_R` 與櫃買 OpenAPI `mopsfin_t187ap03_O`，
  **都還沒實測**），30 天重抓一次。`asof` 取回應的「出表日期」，沒給才用抓取日（不是交易日，欄名刻意不叫 date）。
- 存放：`data/logos/<code>.png`（64×64 PNG）、`data/logos/_index.json`、`data/_state/logo_progress.json`。
  PNG 不是 Parquet，重抓時圖變了才換檔；被判成預設圖的刪檔。
- 判「沒有」：原圖長邊 < 32px（`too_small`）、全透明或白底黑底都單色（`blank`）、同一張圖 ≥ 3 個不同網域（`generic`）、
  robots 禁止（`robots`）、兩個來源都沒有（`none`）、連線失敗（`error`）。
- 增量：沒抓過的先（族群成分股優先）→ 網域換了 → 到期（`ok` 90 天、其他 30 天）。每輪 ≤ 300 家、≤ 15 分鐘、6 條執行緒；同網域一輪抓一次。
- 排程：`run_backfill` 在 FinMind 健檢**之前**跑 `backfill_logos()`；`--datasets logos` 只跑這一步。
  `backfill.yml` 守門：計畫補齊但 `logo_progress.json` 沒補完或到期 → 改跑 `--datasets logos`。
- 輸出：`build_payload.export_logos()` → `site/data/logos.json`（`{"2330": "data/logos/2330.png"}`，只列有圖的，沒有就 `{}`）
  ＋`site/data/logos/<code>.png`。每次先清掉舊的 `site/data/logos/`。`config.LOGOS_ENABLED` 關掉時輸出 `{}`。
- 依賴：`requirements.txt` 加 `Pillow>=10.0`（官方 manylinux wheel 免編譯；只有 Logo 步驟用到，延後載入）。
- 測試：`tests/test_logos.py`（網路全部 mock）。
