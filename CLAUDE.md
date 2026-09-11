# 專案脈絡（給 Claude Code 讀的）

## 這是什麼

台股資金輪動儀表板。每天盤後自動抓資料、算指標、產出一頁式靜態網站，
回答四個問題：**錢往哪個族群跑、那個族群現在貴不貴、什麼時候進場、有沒有理由不進場。**

判斷順序是刻意的：**M1 資金面 + M2 基本面決定方向 → M3 技術面決定時機 → M4 事件面否決。**
在資金流出的族群裡找黃金交叉沒有意義，所以技術面永遠是最後一關。

擁有者是 Andy，前 ASUS EC 韌體工程師、前台積電微影製程工程師，現任科技業 Sales PM。
半導體供應鏈的東西不用從頭解釋；`groups.yaml` 的成分股他會自己校訂。

## 絕對不要做的事

1. **不要碰 `www.twse.com.tw/rwd/...` 官網端點。** 證交所使用條款明文禁止爬蟲抓取官網，
   只有 `openapi.twse.com.tw`（政府開放資料）才在許可範圍內。
   個股別三大法人只有官網有 → 一律走 FinMind，不要「順手」改回官網。
2. **不要覆寫 `data/` 底下的 Parquet。** 開放資料只有當天快照，歷史全靠每天累積，
   寫壞就永遠回不來。一律經過 `store.append()`（append + 依 key 去重）。
3. **不要用執行當下的日期當交易日。** 非交易日 API 會靜默回上一個交易日的資料且不標示，
   一律用回應裡的 `Date` 欄位。`MI_MARGN` 沒有日期欄位，必須由同批行情的日期補上。
4. **不要引入 TA-Lib。** 需要編譯 C 函式庫，在 GitHub Actions 上安裝很脆弱。
   指標全部自己算，寫在 `pipeline/indicators.py`。
5. **不要把持股部位、成本價、個人損益放進 repo。** repo 是 public 的。

## 基本面規則（金融專家定的，寫在 compute/fundamental.py 的 docstring）

- PE 一律自算 = 收盤 / 近四季 EPS 合計；四季不連續就不給 TTM，**不用單季 ×4**
- 虧損股 PE 記 NaN，不排序；族群統計用中位數；PE 在 [3, 200] 外視為離群
- 分位只在同族群內算；樣本 < 5 退回法定產業別、< 3 留白、永遠顯示 n
- `groups.yaml` 的 `valuation_metric`：金融 pb_roe、生技 ps、其餘 pe。**絕不跨族群比 PE**
- 財報「可用日」用法定期限（Q1 5/15、Q2 8/14、Q3 11/14、Q4 隔年 3/31、月營收次月 10 日），
  寧可延後不可提前 —— 否則 walk-forward 會偷看未來
- 券商目標價是**新聞引述**，不是我們的預估；頁面必須標券商名、日期、來源

## 台股慣例（跟國外套件預設不同，弄錯會跟看盤軟體對不起來）

- **紅漲綠跌**，與美股相反。前端配色已經照這個做，不要「修正」成綠漲紅跌。
- **KD 用 9,3,3**，K 與 D 都是 1/3 平滑，初始值 50。
- **RSI 用 Wilder 種子**：前 14 筆變動的簡單平均起頭，不是 `ewm(adjust=False)` 的第一筆。
  這跟 Pine Script 的 `ta.rma` 一致，所以會跟 TradingView 對得起來。
  `pipeline/indicators.py` 的 `wilder_rma()` 就是為此存在，別繞過它。
- **MACD 慣稱 DIF / MACD / OSC**，OSC 才是柱狀體。
- 日期是民國格式、金額多為千元、所有欄位都是字串 —— 統一由 `pipeline/util/roc.py` 處理。

## 架構

```
證交所 OpenAPI ─┐
FinMind ────────┤
集保 ───────────┼→ pipeline/sources/* → store.append() → data/*.parquet
櫃買（可失敗）──┤                                            │
新聞 / FRED ────┘                                            ↓
                                          pipeline/compute/* + indicators.py
                                                             ↓
                                                  build_payload.py
                                                             ↓
                                              site/data/*.json → site/index.html
```

- **每日增量**走證交所 OpenAPI（免 key、無限速、一支請求拿全市場）
- **歷史**走 FinMind（免費層 600 req/hr，逐檔查，`run_backfill.py` 可重複執行）
- 前端只畫圖不運算，所有計算在 `build_payload.py` 做完

## 檔案地圖

| 路徑 | 職責 |
|---|---|
| `pipeline/config.py` | 所有路徑、端點、參數。改設定只改這裡 |
| `pipeline/util/roc.py` | 民國日期、千元單位、`--`/`(45)`/全形符號等空值處理 |
| `pipeline/util/http.py` | 重試退避 + FinMind 跨程序額度管理 |
| `pipeline/util/store.py` | Parquet append-only 資料湖 |
| `pipeline/sources/*.py` | 各資料源，全部回 DataFrame，失敗回空的不拋例外 |
| `pipeline/indicators.py` | MA/MACD/RSI/KD/SMC + `technical_score()` |
| `pipeline/compute/flow.py` | M1 資金面 |
| `pipeline/groups/groups.yaml` | ★ 族群對照表，唯一人工維護的檔案 |
| `pipeline/run_daily.py` | 每日盤後管線 |
| `pipeline/run_backfill.py` | 歷史回補 |
| `pipeline/build_payload.py` | 算成前端 JSON |
| `site/index.html` | 儀表板（ECharts，單檔） |

## 開發約定

- **每個抓取步驟都必須可以失敗。** 一個來源掛掉不能讓整天的資料都沒存到。
  `run_daily.py` 的 `step()` 會吃掉所有例外並記進 `last_run.json`。
- **新增資料表要先在 `config.TABLES` 註冊 key 欄位**，否則 `store.append()` 會拒絕。
- **改指標一定要跑 `pytest tests/ -q`。** 裡面有兩個關鍵測試：
  `test_no_lookahead_in_moving_averages`（截斷資料後歷史值不能變）
  和 `test_append_is_idempotent`（同一天重跑不能變兩列）。
- **一檔股票可以屬於多個族群**，量能依所屬族群數平均拆分（`flow._attach_groups` 的 `weight`）。
  不要改成每個族群各算一次完整金額，那會讓市場總量灌水。
- 註解與 commit 訊息用繁體中文。

## 目前進度

已完成：資料層、抓取層、指標庫、M1 資金面、**M2 基本面**（`compute/fundamental.py`：
TTM EPS、自算 PE、分族群估值分位含 pb_roe/ps 口徑、月營收動能含農曆年合併）、
新聞三分類（鉅亨 tech / wd_macro / tw_stock ＋ TechNews）、券商目標價引述抽取、
儀表板前端 v1、GitHub Actions 排程、92 個測試。

v2 稿圖已經 Andy 確認（2026-09-11），三個拍板：註冊富果做即時、預估漲幅改營運動能分數、
每處都要有股票簡稱、券商目標價以「新聞引述」形式呈現。

**v2 已完成（2026-09-11）**：
- 前端 v2：`site/index.html` + `site/app.js`（hash 路由五分頁、事件側欄、熱力圖/象限/法人下鑽、
  季節性排名點圖、市場寬度、產業鏈分層圖 + 手機折疊清單）
- 個股頁：`site/data/stock/<code>.json`（K 線 + 指標序列 + BOS/CHoCH/掃蕩標記 + 需求/供給區 +
  判定 + 基本面 + 籌碼 + 新聞 + 券商引述）
- 規則引擎：`compute/technical.py` —— 多源交集區間（score≥3、≥2 來源、寬 ≤2×ATR、依距離排序）、
  A/B/觀望/不要碰、突破停損放在被突破的前高下方、測量目標、週線衝突降級、三段式文字
- 指標庫補 ATR、量比、Volume Profile、漲跌停旗標；FVG 門檻 max(0.6, 0.3×ATR%)
- `groups/supply_chain.yaml` + `loader.supply_chain()`（市占帶 as_of/source/confidence，180 天標 stale）

**還沒做**：

3. **即時層**：Fugle WebSocket 前端直連（等 Andy 給 key），Cloudflare Workers 藏 key。
4. **M4 事件面計算層** —— 用鉅亨新聞的 `market`/`keyword` 欄位把新聞歸戶到個股與族群，
   偵測當日新聞量異常的族群；國際連動係數（族群 vs `benchmarks` 指定的指數）。
5. **綜合評分** —— 目前有技術分與營收動能分。要把 M1/M2/M3/M4 依 `config.SCORE_WEIGHTS` 合成。
6. **walk-forward 檢驗** —— 這是最重要的一步。現在 `technical_score()` 的權重
   純粹是起始假設，沒有任何統計依據。要拿歷史資料驗證評分高的標的後續表現
   是否真的比較好，**結果不好就要誠實寫在頁面上，不要調參數去湊出好看的結果**。
7. **產業鏈頁**：supply_chain.yaml（節點/邊/市占帶 as_of+source+confidence）＋ 分層 DAG。
8. `build_groups.py` —— 從產業價值鏈平台與 MoneyDJ 抓候選清單，
   跟 `groups.yaml` 比對後產出「建議新增/移除」報告。**只產報告，不要自動改 YAML。**

## 已知限制（不要假裝它們不存在）

- 開放資料無歷史，回補完成前季節性與 RS 都不準
- T-1 延遲，這是合規換來的，不要為了即時性去碰官網
- 櫃買有反爬，Actions 共用 IP 很可能被擋 → 設計成可失敗，備援走 FinMind
- 季節性十年只有每月 10 個樣本，樣本 < 3 一律留白，權重刻意壓到 0.05
- 生存者偏差：用今天的成分股回推歷史會高估績效，目前只做到「標示」而非消除
- **這是決策輔助，不是交易系統。** 不接下單、不自動執行。
