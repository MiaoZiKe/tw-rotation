# 個股頁數據普查與補齊（2026-09-27，金融專家）

起因：Andy「如果網頁版有什麼缺漏資訊，也麻煩照給你的圖片補上，季的週期要對，我發現部分數據太少」，
附某券商 App 個股頁截圖（華邦電 2344：K 線、主力、法人、指標、資券、相關 ETF、營收、大戶、新聞、獲利、除權息）。
口徑決定寫在 DECISIONS #268；這份是**普查結果、payload 欄位規格（給手機版）與不做的項目的理由**。

## 1. 普查結果（六檔：2330、2454、3026、6669、2618、1101；資料日 2026-09-24）

| 卡片 | 問題 | 原因 | 處理 | 改前 → 改後 |
|---|---|---|---|---|
| 獲利（季） | 1,040 檔的 2026Q2 是「上半年累計」被當單季（2618：EPS 2.24、營收 1,283 億；單季其實 0.71、678 億） | 每日管線的證交所 t187ap14 給年度累計；`ttm()` 早就先還原，個股頁的 `profit_series`／`pe_daily` 卻吃原表 | 兩支都先過 `_decumulate`（`stockpage._single_quarter_frame`） | 錯 → 對（2344 核對：2026Q2 EPS 5.40、累計 7.65、2025Q4 累計 0.88、毛利率 66.25%、淨利率 40.44%，與 App 一致） |
| 獲利（季） | 缺季時 x 軸直接接過去（6669 2017Q1→Q2→Q4） | 只列有資料的季 | 缺季補空列、`gaps` 列出；年度累計遇缺季停 | 6669：3 個缺季看得見 |
| 獲利（季） | 點數 | payload 只給 24 季 | 給 40 季（資料湖 2016Q1 起約 42 季） | 24 → 40（6669 39） |
| 獲利（年） | 沒有年度 | — | `profit.yearly`：四季單季加總，今年標「前 n 季」 | 0 → 10 年 |
| 獲利（法定期限） | 沒有檢查 | — | `profit.timing`：expected／max_possible／status | 六檔皆 ok（2026Q2） |
| 本益比歷史 | 2026Q2 那段 TTM 灌水（同上累計列） | 同上 | 同上 | 20 季（沒變），最後一段修正 |
| AI 分析卡基本面 | 「近四季 EPS」可能跨缺季相加 | 濾掉空值後取最後四筆 | 從最新往回取連續季 | — |
| 月營收 | MoM 用上一列（缺月時跟兩個月前比）；累計缺月照加 | `pct_change`、`groupby.cumsum` | MoM 對日曆月；累計要 1 月起連續才給；加「去年同月」欄 | 72 個月（沒變） |
| 三大法人 | **1,980 檔普通股裡 1,626 檔 inst_daily 一列都沒有**，籌碼分頁整張不出現 | 回補計畫從來沒有 inst；每日管線只補成交值前 500 檔 | 計畫加「inst 2016 起」；落後的股票每天續補（`refresh_stale_inst`） | 0 → 約 2,600 天（補完後） |
| 法人自營商 | 只有合計 | payload 沒帶 | 列尾加自行買賣、避險 | — |
| 資券 | 沒有當沖、借券賣 | 資料湖沒有 | 新表 `daytrade_daily`、`sbl_daily`（FinMind），計畫 2025 起 | 0 → 約 430 天（補完後；帳號等級拿不到會自動封印並照實顯示） |
| 籌碼預設窗 | 4 週（20 天）太少 | — | 預設 3 個月（63 天），跟 App 的一季一致 | 20 → 63 |
| 集保大戶 | 4 週 | FinMind 集保歷史要 backer 等級（HTTP 400 register）；集保 opendata 只給當週 | 不變，照實寫；加每週表 | 4（每週 +1） |
| 除權息年度圖 | 2016 起、沒有殖利率線；2344 已除息的 2025H2 還掛「即將除權息」 | 回補起點 2016；證交所與 FinMind 同一期寫法不同（下半年／後半年度） | 計畫加 2009 起一步；每年現金殖利率；同一期去重；加「股利政策（所屬期間）」表 | 11 → 最多 18 年（補完後） |
| 新聞 | 「最新 8 則」不是最新；只有日期 | 拿 RFC 2822 字串排序＝照星期幾字母排 | 解析成台北時間排序，帶 `time` | — |
| 指標 | 沒有 | — | `tags`：8 條事實條件＋題材／族群（前端從 `meta.groups`、themes 帶） | 0 → 8 |
| 月營收明細表 | 沒有去年同期 | — | 表格多「去年同期」欄（圖本來就有並排柱） | — |
| 董監持股（2026-09-27 接手補） | 沒有 | 前一版判定「資料集未查證」 | 查到 `t187ap11_L`（政府資料開放平臺 資料集 22811，欄位見 §4）；新表 `insider_holding`、每日傍晚那輪抓、只存每家公司每月合計 | 0 → 每月 +1（第一筆要等 Actions 跑過，容器連不到 openapi） |
| 主力（2026-09-27 接手補） | 只有「?」裡一句「需付費資料」 | 分點不爬 | 新卡「主力（替代：三大法人）」：法人合計買賣超柱＋5／20 日集中度線＋每日表 | 0 → 約 260 天（跟法人同長） |
| 散戶口徑 | App 2344 散戶 27.62%，本站 17.36% | 級距不同：本站＝集保 1–3 級（≤10 張，DECISIONS #20）；App 用更寬的級距（沒公開定義） | 不改口徑，大戶卡寫明「散戶＝集保 1–3 級」 | — |

## 2. 回補預估（FinMind 免費會員 600 次／時，程式留 15% 邊際＝510）

| 步驟 | 請求數 | 估計 |
|---|---|---|
| inst 2016 起（計畫第 5 步） | 約 1,630（已有 401 檔的 done 鍵） | 3～4 輪（小時） |
| daytrade＋sbl 2025 起 | 約 2,300 × 2 ＝ 4,600 | 9～10 輪 |
| dividend＋divresult 2009 起 | 約 2,300 × 2 ＝ 4,600 | 9～10 輪 |
| 每日續補（inst／daytrade／sbl 落後的） | 約 1,500～4,500／交易日 | 分散在每小時的回補 |

合計一次性約 1.1 萬次請求，**約 22～24 小時**（每小時一輪）。三步驟依序執行，額度用完下一輪接續。
⚠ 若 FinMind 對 `TaiwanStockDayTrading`／`TaiwanDailyShortSaleBalances` 回「Your level is register」，
回補會在連續 20 檔回空後停問、寫進 `unavailable` 封印（每 24 小時探 5 檔），頁面資券「當沖」「借券賣」段寫「資料源帳號等級拿不到」。
容器連不到 FinMind，無法事先實測這兩個資料集的等級（WebSearch 摘要只說「部分資料集需贊助會員」，沒點名這兩個）。

## 3. payload 新欄位（`site/data/stock/<code>.json`，給手機版）

- `profit.quarters[i]`：`[期別, 營收, 毛利率, 營益率, 淨利率, EPS, 年度累計EPS, EPS年增(元), 淨利]`；三率改 2 位小數；缺季整列除期別外為 null。
- `profit.gaps`：缺的期別清單。
- `profit.yearly[i]`：`{year, quarters, partial, eps, revenue, net_income, gm, om, nm}`。
- `profit.timing`：`{asof, expected, max_possible, latest, status: ok|missing|future}`。
- `revenue.monthly[i]` 第 7 欄 `revenue_last_year`（去年同月營收）。
- `inst_v3.daily[i]` 第 6、7 欄 `dealer_self`、`dealer_hedge`（股）；`inst_v3.columns`。
- `margin[i]` 第 6～9 欄：`daytrade_lots`（張）、`daytrade_ratio`（%）、`sbl_sell_lots`（張）、`sbl_balance_lots`（張）；`margin_columns`。
- `tags`：`{items: [{id, kind: "指標", label, hit: true|false|null, detail}], n_hit}`。
  「題材」「族群」兩種標籤不在這裡：桌機版從 `meta.groups`（族群名）與 themes.yaml（`App.L.themesOf(code)`）帶，手機版照同一個來源。
  顯示規則：符合的列上面（紅字＝條件成立）、不符合與資料不足收在下面照樣看得到、每條附 detail（判斷用的數字），不寫任何推介字眼。
- `dividends.by_year[i].cash_yield`（%）、`items[j].cash_yield`；`dividends.results[i].cash_yield`；
  `dividends.by_period[i]`：`{period: "2025H2", fiscal_year, raw_period, cash, stock, cash_ex_date, stock_ex_date, payment_date, announce_date, cash_yield, status: paid|upcoming|pending}`。
- `news[i].time`（台北 HH:MM）。
- `insider`：`{monthly: [{ym, director_pct, insider_pct, director_shares, pledge_pct, n_directors, base_date, flag}], latest, source}`（2026-09-27 接手補）。
  director_pct ＝ 董監目前持股 ÷ 集保 level 17 股數（取離月底最近、≤45 天的那一週）；> 100% → None、flag＝"over100"；沒有集保那週 → 只給股數。
- `main_proxy`：`{daily: [[date, inst_net(股), volume(股), conc5(%), conc20(%)]], columns, proxy}`（只有完整頁有，精簡頁沒有）。
  concN ＝ Σ近 N 交易日法人合計 ÷ Σ近 N 交易日成交股數 × 100；窗內任何一天缺法人或缺量 → None；量 0 → None。
  **這是替代口徑**，手機版標題也要寫「替代」。

## 4. 不做的項目與理由（沒有合規來源就不做）

| 項目 | 結論 | 理由 |
|---|---|---|
| 主力（分點買賣超、家數差） | 分點不做；**替代卡已做** | CLAUDE.md 第 7 條禁止爬券商分點。替代口徑＝三大法人合計買賣超＋法人版 5／20 日集中度（`main_proxy`），標題寫「替代」；集保千張大戶週增減在「大戶」卡 |
| 內部人／董監持股 | **做了（待 Actions 首跑確認欄位）** | 證交所 OpenAPI `/opendata/t187ap11_L`「上市公司董監事持股餘額明細資料」＝政府資料開放平臺資料集 22811（開放授權，跟 t187ap03／04／05 同一類）；上櫃＝櫃買 OpenAPI `mopsfin_t187ap11_O`。WebSearch 兩個獨立摘要（data.gov.tw 資料集頁、一個 GitHub 專案）都列出欄位：資料年月、公司代號、職稱、姓名、選任時持股、目前持股、設質股數…；每月一次、次月 20 日前後公布、**只給最新一個月**（歷史只能逐月累積）。容器連不到 openapi，欄位名沒實測：parser 對鍵名寬鬆、解析不出就回空並把鍵名寫進 log。信心：中 |
| 相關 ETF（持有權重、股數、報價） | 不做 | ①證交所 OpenAPI：2026-09 的 swagger 共 143 個端點，分類是公司治理 56、證券交易 36、財報 30、券商 9、指數 5、權證 3、其他 4（twmarketdata 的端點總覽摘要），沒有 ETF 成分股／權重類。②FinMind：資料集清單（WebSearch 摘要）沒有 ETF 持股明細。③投信投顧公會（SITCA）與各投信官網的持股揭露：不是政府開放資料集、不在白名單、使用條款查不到原文。→ 沒有合規來源。報價本身有（本站已有 ETF 日收），但沒有「哪些 ETF 持有這檔」的對照就做不出「相關 ETF」 |
| 權證清單 | 不做（待查證） | 證交所 OpenAPI 有 3 個權證端點（同上 swagger 分類統計），但端點 ID 與欄位（有沒有「標的證券」）查不到原文、容器也連不到 swagger.json 實測；櫃買 OpenAPI 同樣未查證。查到端點 ID 與「標的證券」欄位再做（Actions 上跑一次 `curl https://openapi.twse.com.tw/v1/swagger.json` 就能確認） |
| 台灣 50／MSCI 成分股標籤 | 不做 | 名單由臺灣指數公司／MSCI 發布，不在白名單 |
| 集團標籤 | 不做 | 沒有公開、可機器讀取的集團歸屬資料源 |
| 紀念品、股息再投入 | 不做 | 沒有合規資料來源，且後者是試算工具 |
