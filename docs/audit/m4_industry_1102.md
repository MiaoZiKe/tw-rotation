# 手機產業地圖普查 2026-11-02（`docs/audit/m4_industry_1102.md`）

> 起因（Andy 逐字）：「CEO 我執行手機版本後發現很多問題，特別是在產業地圖上……確保每個功能每個按鈕都被使用過……編號不能點擊 無法看圖片等等」。

## 方法

- Playwright Chromium，`is_mobile=True`、`has_touch=True`、DPR 3，寬 390／360／430、深色／淺色（390 兩色、360 與 430 深色），全部用 `touchscreen.tap` 真的點；每次點之前後比對 `location.hash`、`body.innerHTML` 長度與雜湊、可見的彈窗／抽屜，兩次一樣＝「畫面沒變」＝✗。
- 範圍：#industry 首頁（圖例、「?」、收展、熱力圖連結、每一個產業鏈分頁）、每條產業鏈（半導體、AI 伺服器、矽光子／CPO、一般電子、軟體與資訊服務、金融、傳產與內需、基礎建設與能源）的預設頁、族群總覽頁、前 1～2 張剖析圖頁（「快速模式」）：麵包屑、產業鏈分頁列、環節 chip、每顆「?」、2D／3D、編號開關、圖說、每個剖析圖編號與零件卡內每顆鈕、延伸閱讀抽屜、「篩選 環節」下拉與每一格、關聯圖環節標題與公司節點。
- 圖片：每頁量 `naturalWidth>0`。**整個產業地圖沒有任何 `<img>` 是內容圖（每頁只有頁首 logo 1 張）；所謂「圖片」是 SVG／3D canvas 的剖析圖**，所以沒有破圖可抓——Andy 說的「無法看圖片」對應下面第 3 點（剖析圖本體太小又不能放大），屬剖析圖負責人。
- 截圖：scratchpad `indaudit_<路由>_<寬><d|l>.png`（每頁一張）、`indaudit_3d_*`（3D 畫面）。
- ⚠ 這支普查腳本自己有假陽性（例如開著抽屜就去點下一顆、把 #howPop 刪掉），逐項人工複驗後標在「結果」欄，不隱瞞。

## 統計

| 輪次 | 共點／量了 | ✓ | ✗ 合計 | 其中已修 | 其中部分已修／編號交剖析圖 | 假陽性（腳本） |
|---|---|---|---|---|---|---|
| 390 深色 | 824 | 710 | 114 | 12 | 51 | 51 |
| 390 淺色 | 824 | 668 | 156 | 54 | 51 | 51 |
| 360 深色 | 824 | 668 | 156 | 54 | 51 | 51 |
| 430 深色 | 824 | 668 | 156 | 54 | 51 | 51 |

> 390 深色那輪是在加了第一版修正 CSS 之後才跑完的，所以「?」那一類已經不再計入 ✗；其他三輪是改前（多出 42 筆「?」可點區 < 32 的 ✗），可直接當改前改後對照：**「?」可點範圍 30×24～30 → 42×42**。

## 重點結論（✗ 屬實的只有觸控範圍這一類）

| # | 問題 | 量到的數字 | 處理 |
|---|---|---|---|
| 1 | 「?」說明鈕畫面 18×18、實際可點只有 30×24～30（所有產業鏈／族群／剖析圖頁 3 顆，首頁 1 顆） | 改前 30×24～30 → 改後 42×42 | **已修**（site/m4/20261102-ind-audit.css） |
| 2 | 頁首麵包屑「產業地圖」連結 56×22 | 改前 22 高 → 改後可點 42 高 | **已修** |
| 3 | 關聯圖環節標題藥丸 19 高、手指點不準 | 改前 19 → 改後 32 | **已修** |
| 4 | 剖析圖編號圓鈕 20×20（2D）／28×28（3D）；手指點不準，Chromium 實測每一顆都點得開零件卡，但 iPhone 上 20px 圓鈕緊鄰排列很可能就是「編號不能點擊」 | 20×20，鄰居間距約 30px | **交給剖析圖負責人**（m4-dglayout1102），本段不碰 |
| 5 | 剖析圖（2D 約 308×227、字 7～8px）太小又 `user-scalable=no` 無法雙指放大，圖上字看不清；2D 沒有「放大」鈕（3D 有 ⤢） | 圖寬 308px | **交給剖析圖負責人**（即「2D／3D 剖析圖本身的版面放大」） |
| 6 | 矽光子／CPO 族群總覽「成員與階段」表：個股、族群連結 18 高（42 檔一整排小連結） | 改前 18 高 → 改後可點 36 高 | **已修**（同一支 CSS） |
| 7 | 關聯圖左右被切（欄位超出 390 寬，要左右拖；有邊緣淡出，但沒有文字提示） | 欄寬 > 容器 | 刻意留到下一版（見回報） |

## 假陽性逐項（人工複驗結果）

- 延伸閱讀 #2～#4「沒展開」：實際是前一個抽屜還開著，再點的是抽屜背景；逐顆關閉後重點，4 顆都開（半導體頁人工複驗）。
- 篩選環節下拉「0 格／沒展開」：選擇器抓錯（清單是 `#segDD .ddpanel .segchip`）；下拉真的會展開、點第 2 格下拉鈕文字真的變。
- 零件卡鈕「›」：真的點會換到下一個零件（01→02），複驗通過。
- 完整版圖連結「→ #stock/2303」：點下去前版面剛好位移；穩定後重點，落到 `#heatmap/industry`（正確）。
- 環節 chip「族群總覽／晶圓代工」hash 沒變：那顆本來就是目前這頁，不應換頁。
- console error「Cannot set properties of null (setting 'innerHTML')」：是普查腳本自己把 `#howPop` 從 DOM 刪掉造成（app.js:10410），不是網站問題。
- 腳本例外（矽光子／軟體）：腳本取不到元素；人工逐顆點這幾頁的編號 10／7／10 顆，全部開得了零件卡。

## 全部記錄

欄位：頁面／元素／動作／結果／問題描述／截圖。390 深色全列；其餘三輪只列 ✗（✓ 筆數見上表）。

### 390 深色

| 頁面 | 元素 | 動作 | 結果 | 問題描述 | 截圖 |
|---|---|---|---|---|---|
| #industry 首頁 | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 0 張；破圖 [] | indaudit_home_390d.png |
| #industry 首頁 | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修｜? 18x18 |  |
| #industry 首頁 | 圓餅圖例列 #1「晶圓代工 1483 億 16.0」 | touchscreen.tap → 圖例列被點亮／讀數改變 | ✓ |  |  |
| #industry 首頁 | 圓餅圖例列 #2「聯電 260 億 17.5%」 | touchscreen.tap → 圖例列被點亮／讀數改變 | ✓ |  |  |
| #industry 首頁 | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry 首頁 | 收展鈕「族群漲跌幅」 | （頁上沒有） | ✓ | 略 |  |
| #industry 首頁 | 完整版圖連結 | tap → #heatmap | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#stock/2303 |  |
| #industry 首頁 | 圓餅圖扇形 | tap 扇形 → 中心讀數／清單改變 | ✓ |  |  |
| #industry 首頁 | 產業鏈分頁「_all」 | tap → 換頁 | ✓ | #industry |  |
| #industry 首頁 | 產業鏈分頁「semiconductor」 | tap → 換頁 | ✓ | #industry/semiconductor/overview |  |
| #industry 首頁 | 產業鏈分頁「ai_server」 | tap → 換頁 | ✓ | #industry/ai_server/overview |  |
| #industry 首頁 | 產業鏈分頁「siph_cpo」 | tap → 換頁 | ✓ | #industry/siph_cpo/overview |  |
| #industry 首頁 | 產業鏈分頁「electronics」 | tap → 換頁 | ✓ | #industry/electronics/overview |  |
| #industry 首頁 | 產業鏈分頁「software」 | tap → 換頁 | ✓ | #industry/software/overview |  |
| #industry 首頁 | 產業鏈分頁「financial」 | tap → 換頁 | ✓ | #industry/financial/overview |  |
| #industry 首頁 | 產業鏈分頁「traditional」 | tap → 換頁 | ✓ | #industry/traditional/overview |  |
| #industry 首頁 | 產業鏈分頁「infrastructure」 | tap → 換頁 | ✓ | #industry/infrastructure/overview |  |
| #industry 首頁 | 產業鏈分頁「industry」 | tap → 換頁 | ✓ | #industry/industry/overview |  |
| #industry 首頁 | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/semiconductor | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_semiconductor_390d.png |
| #industry/semiconductor | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/semiconductor | 麵包屑「產業地圖」 | tap → 回 #industry | ✓ | #industry |  |
| #industry/semiconductor | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/semiconductor | 「?」說明鈕 #2「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/semiconductor | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/semiconductor | 圖說鈕 | tap → 畫面改變 | ✓ |  |  |
| #industry/semiconductor | 編號開關 | tap → 畫面改變 | ✓ |  |  |
| #industry/semiconductor | 剖析圖編號 #01（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x22 |  |
| #industry/semiconductor | 零件卡公司連結「台積電 2330」 | 連到 #stock/2330 | ✓ |  |  |
| #industry/semiconductor | 零件卡公司連結「聯電 2303」 | 連到 #stock/2303 | ✓ |  |  |
| #industry/semiconductor | 零件卡公司連結「力積電 6770」 | 連到 #stock/6770 | ✓ |  |  |
| #industry/semiconductor | 零件卡鈕「‹」 | tap → 畫面改變 | ✓ |  |  |
| #industry/semiconductor | 零件卡鈕「›」 | tap → 畫面改變 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/semiconductor | 剖析圖編號 #02（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x22 |  |
| #industry/semiconductor | 剖析圖編號 #03（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x22 |  |
| #industry/semiconductor | 剖析圖編號 #04（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x22 |  |
| #industry/semiconductor | 剖析圖編號 #05（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/semiconductor | 剖析圖編號 #06（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/semiconductor | 剖析圖編號 #07（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/semiconductor | 剖析圖編號 #08（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/semiconductor | 剖析圖編號 #09（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x26 |  |
| #industry/semiconductor | 剖析圖編號 #10（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/semiconductor | 剖析圖編號 #11（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x26 |  |
| #industry/semiconductor | 剖析圖編號 #12（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/semiconductor | 剖析圖編號 #13（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/semiconductor | 剖析圖編號 #14（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/semiconductor | 剖析圖編號 #15（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/semiconductor | 3D 切換鈕 | tap → 切到 3D | ✓ | 觸控 52x40 |  |
| #industry/semiconductor | 3D 畫面 | 3D canvas 出現且有大小 | ✓ | [332, 340] |  |
| #industry/semiconductor | 2D 切換鈕 | tap → 切到 2D | ✓ | 觸控 52x40 |  |
| #industry/semiconductor | 產業鏈分頁「全市場 464」 | tap → 換頁（或回頂） | ✓ | #industry |  |
| #industry/semiconductor | 產業鏈分頁「半導體 157」 | tap → 換頁（或回頂） | ✓ | #industry/semiconductor |  |
| #industry/semiconductor | 產業鏈分頁「AI 伺服器 100」 | tap → 換頁（或回頂） | ✓ | #industry/ai_server |  |
| #industry/semiconductor | 產業鏈分頁「矽光子／CPO 42」 | tap → 換頁（或回頂） | ✓ | #industry/siph_cpo |  |
| #industry/semiconductor | 產業鏈分頁「一般電子 101」 | tap → 換頁（或回頂） | ✓ | #industry/electronics |  |
| #industry/semiconductor | 產業鏈分頁「軟體與資訊服務 11」 | tap → 換頁（或回頂） | ✓ | #industry/software |  |
| #industry/semiconductor | 產業鏈分頁「金融 20」 | tap → 換頁（或回頂） | ✓ | #industry/financial |  |
| #industry/semiconductor | 產業鏈分頁「傳產與內需 51」 | tap → 換頁（或回頂） | ✓ | #industry/traditional |  |
| #industry/semiconductor | 產業鏈分頁「基礎建設與能源 24」 | tap → 換頁（或回頂） | ✓ | #industry/infrastructure |  |
| #industry/semiconductor | 產業鏈分頁「法定產業別 1878」 | tap → 換頁（或回頂） | ✓ | #industry/industry |  |
| #industry/semiconductor | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✓ | #industry/semiconductor/overview |  |
| #industry/semiconductor | 環節 chip「晶圓代工」 | tap → 換到那一頁 | ✓ | #industry/semiconductor/dg/foundry |  |
| #industry/semiconductor | 環節 chip「先進封裝」 | tap → 換到那一頁 | ✓ | #industry/semiconductor/dg/ai_adv_packaging |  |
| #industry/semiconductor | 環節 chip「HBM」 | tap → 換到那一頁 | ✓ | #industry/semiconductor/dg/hbm |  |
| #industry/semiconductor | 環節 chip「SSD」 | tap → 換到那一頁 | ✓ | #industry/semiconductor/dg/memory_module |  |
| #industry/semiconductor | 環節 chip「矽晶圓」 | tap → 換到那一頁 | ✓ | #industry/semiconductor/dg/silicon_wafer |  |
| #industry/semiconductor | 環節 chip「第三代半導體」 | tap → 換到那一頁 | ✓ | #industry/semiconductor/dg/wide_bandgap |  |
| #industry/semiconductor | 延伸閱讀 #1 | tap → 展開 | ✓ | ＋ 延伸 1｜尺度：晶圓 → 晶 |  |
| #industry/semiconductor | 延伸閱讀 #2 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 2｜製程迴圈：九站走完 |  |
| #industry/semiconductor | 延伸閱讀 #3 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 3｜節點演進：N5 → |  |
| #industry/semiconductor | 延伸閱讀 #4 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 4｜這張圖上每一段台股 |  |
| #industry/semiconductor | 篩選環節下拉 | tap → 展開清單 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/semiconductor | 篩選環節選項數 | 清單出現 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜0 格 |  |
| #industry/semiconductor | 關聯圖環節卡 #1「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 131x23（<32） |  |
| #industry/semiconductor | 關聯圖環節卡 #2「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 126x28（<32） |  |
| #industry/semiconductor | 關聯圖環節卡 #3「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 131x23（<32） |  |
| #industry/semiconductor | 公司名連結（頁上） | （頁上沒有） | ✓ | 略 |  |
| #industry/semiconductor | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/semiconductor/overview | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_semiconductor_overview_390d.png |
| #industry/semiconductor/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/semiconductor/overview | 麵包屑「產業地圖」 | tap → 回 #industry | ✓ | #industry |  |
| #industry/semiconductor/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/semiconductor/overview | 「?」說明鈕 #2「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/semiconductor/overview | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/semiconductor/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/semiconductor/overview |  |
| #industry/semiconductor/overview | 環節 chip「晶圓代工」 | tap → 換到那一頁 | ✓ | #industry/semiconductor/dg/foundry |  |
| #industry/semiconductor/overview | 環節 chip「先進封裝」 | tap → 換到那一頁 | ✓ | #industry/semiconductor/dg/ai_adv_packaging |  |
| #industry/semiconductor/overview | 環節 chip「HBM」 | tap → 換到那一頁 | ✓ | #industry/semiconductor/dg/hbm |  |
| #industry/semiconductor/overview | 環節 chip「SSD」 | tap → 換到那一頁 | ✓ | #industry/semiconductor/dg/memory_module |  |
| #industry/semiconductor/overview | 環節 chip「矽晶圓」 | tap → 換到那一頁 | ✓ | #industry/semiconductor/dg/silicon_wafer |  |
| #industry/semiconductor/overview | 環節 chip「第三代半導體」 | tap → 換到那一頁 | ✓ | #industry/semiconductor/dg/wide_bandgap |  |
| #industry/semiconductor/overview | 篩選環節下拉 | tap → 展開清單 | ✓ |  |  |
| #industry/semiconductor/overview | 篩選環節選項數 | 清單出現 | ✓ | 23 格 |  |
| #industry/semiconductor/overview | 公司名連結（頁上） | （頁上沒有） | ✓ | 略 |  |
| #industry/semiconductor/overview | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/semiconductor/dg/foundry | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_semiconductor_dg_foundry_390d.png |
| #industry/semiconductor/dg/foundry | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/semiconductor/dg/foundry | 麵包屑「產業地圖」 | tap → 回 #industry | ✓ | #industry |  |
| #industry/semiconductor/dg/foundry | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/semiconductor/dg/foundry | 「?」說明鈕 #2「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/semiconductor/dg/foundry | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/semiconductor/dg/foundry | 圖說鈕 | tap → 畫面改變 | ✓ |  |  |
| #industry/semiconductor/dg/foundry | 編號開關 | tap → 畫面改變 | ✓ |  |  |
| #industry/semiconductor/dg/foundry | 剖析圖編號 #01（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x22 |  |
| #industry/semiconductor/dg/foundry | 零件卡公司連結「台積電 2330」 | 連到 #stock/2330 | ✓ |  |  |
| #industry/semiconductor/dg/foundry | 零件卡公司連結「聯電 2303」 | 連到 #stock/2303 | ✓ |  |  |
| #industry/semiconductor/dg/foundry | 零件卡公司連結「力積電 6770」 | 連到 #stock/6770 | ✓ |  |  |
| #industry/semiconductor/dg/foundry | 零件卡鈕「‹」 | tap → 畫面改變 | ✓ |  |  |
| #industry/semiconductor/dg/foundry | 零件卡鈕「›」 | tap → 畫面改變 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/semiconductor/dg/foundry | 剖析圖編號 #02（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x22 |  |
| #industry/semiconductor/dg/foundry | 剖析圖編號 #03（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x22 |  |
| #industry/semiconductor/dg/foundry | 剖析圖編號 #04（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x22 |  |
| #industry/semiconductor/dg/foundry | 剖析圖編號 #05（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/semiconductor/dg/foundry | 剖析圖編號 #06（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/semiconductor/dg/foundry | 剖析圖編號 #07（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/semiconductor/dg/foundry | 剖析圖編號 #08（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/semiconductor/dg/foundry | 剖析圖編號 #09（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x26 |  |
| #industry/semiconductor/dg/foundry | 剖析圖編號 #10（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/semiconductor/dg/foundry | 剖析圖編號 #11（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x26 |  |
| #industry/semiconductor/dg/foundry | 剖析圖編號 #12（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/semiconductor/dg/foundry | 剖析圖編號 #13（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/semiconductor/dg/foundry | 剖析圖編號 #14（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/semiconductor/dg/foundry | 剖析圖編號 #15（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/semiconductor/dg/foundry | 3D 切換鈕 | tap → 切到 3D | ✓ | 觸控 52x40 |  |
| #industry/semiconductor/dg/foundry | 3D 畫面 | 3D canvas 出現且有大小 | ✓ | [332, 340] |  |
| #industry/semiconductor/dg/foundry | 2D 切換鈕 | tap → 切到 2D | ✓ | 觸控 52x40 |  |
| #industry/semiconductor/dg/foundry | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✓ | #industry/semiconductor/overview |  |
| #industry/semiconductor/dg/foundry | 環節 chip「晶圓代工」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/semiconductor/dg/foundry |  |
| #industry/semiconductor/dg/foundry | 環節 chip「先進封裝」 | tap → 換到那一頁 | ✓ | #industry/semiconductor/dg/ai_adv_packaging |  |
| #industry/semiconductor/dg/foundry | 環節 chip「HBM」 | tap → 換到那一頁 | ✓ | #industry/semiconductor/dg/hbm |  |
| #industry/semiconductor/dg/foundry | 環節 chip「SSD」 | tap → 換到那一頁 | ✓ | #industry/semiconductor/dg/memory_module |  |
| #industry/semiconductor/dg/foundry | 環節 chip「矽晶圓」 | tap → 換到那一頁 | ✓ | #industry/semiconductor/dg/silicon_wafer |  |
| #industry/semiconductor/dg/foundry | 環節 chip「第三代半導體」 | tap → 換到那一頁 | ✓ | #industry/semiconductor/dg/wide_bandgap |  |
| #industry/semiconductor/dg/foundry | 延伸閱讀 #1 | tap → 展開 | ✓ | ＋ 延伸 1｜尺度：晶圓 → 晶 |  |
| #industry/semiconductor/dg/foundry | 延伸閱讀 #2 | tap → 展開 | ✓ | ＋ 延伸 2｜製程迴圈：九站走完 |  |
| #industry/semiconductor/dg/foundry | 延伸閱讀 #3 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 3｜節點演進：N5 → |  |
| #industry/semiconductor/dg/foundry | 延伸閱讀 #4 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 4｜這張圖上每一段台股 |  |
| #industry/semiconductor/dg/foundry | 篩選環節下拉 | tap → 展開清單 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/semiconductor/dg/foundry | 篩選環節選項數 | 清單出現 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜0 格 |  |
| #industry/semiconductor/dg/foundry | 公司名連結（頁上） | （頁上沒有） | ✓ | 略 |  |
| #industry/semiconductor/dg/foundry | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/semiconductor/dg/ai_adv_packaging | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_semiconductor_dg_ai_adv_packaging_390d.png |
| #industry/semiconductor/dg/ai_adv_packaging | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/semiconductor/dg/ai_adv_packaging | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/semiconductor/dg/hbm | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_semiconductor_dg_hbm_390d.png |
| #industry/semiconductor/dg/hbm | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/semiconductor/dg/hbm | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/semiconductor/dg/memory_module | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_semiconductor_dg_memory_module_390d.png |
| #industry/semiconductor/dg/memory_module | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；? 18x18 |  |
| #industry/semiconductor/dg/memory_module | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/semiconductor/dg/silicon_wafer | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_semiconductor_dg_silicon_wafer_390d.png |
| #industry/semiconductor/dg/silicon_wafer | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；? 18x18；產業地圖 5 |  |
| #industry/semiconductor/dg/silicon_wafer | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/semiconductor/dg/wide_bandgap | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_semiconductor_dg_wide_bandgap_390d.png |
| #industry/semiconductor/dg/wide_bandgap | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/semiconductor/dg/wide_bandgap | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/ai_server | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_ai_server_390d.png |
| #industry/ai_server | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/ai_server | 麵包屑「產業地圖」 | tap → 回 #industry | ✓ | #industry |  |
| #industry/ai_server | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/ai_server | 「?」說明鈕 #2「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/ai_server | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/ai_server | 圖說鈕 | tap → 畫面改變 | ✓ |  |  |
| #industry/ai_server | 編號開關 | tap → 畫面改變 | ✓ |  |  |
| #industry/ai_server | 剖析圖編號 #01（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/ai_server | 零件卡公司連結「智邦 2345」 | 連到 #stock/2345 | ✓ |  |  |
| #industry/ai_server | 零件卡鈕「‹」 | tap → 畫面改變 | ✓ |  |  |
| #industry/ai_server | 零件卡鈕「›」 | tap → 畫面改變 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/ai_server | 剖析圖編號 #02（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/ai_server | 剖析圖編號 #03（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/ai_server | 剖析圖編號 #04（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/ai_server | 剖析圖編號 #05（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x26 |  |
| #industry/ai_server | 剖析圖編號 #06（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x30 |  |
| #industry/ai_server | 剖析圖編號 #07（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/ai_server | 剖析圖編號 #08（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/ai_server | 剖析圖編號 #09（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/ai_server | 剖析圖編號 #10（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/ai_server | 剖析圖編號 #11（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/ai_server | 剖析圖編號 #12（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/ai_server | 剖析圖編號 #13（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/ai_server | 3D 切換鈕 | tap → 切到 3D | ✓ | 觸控 52x40 |  |
| #industry/ai_server | 3D 畫面 | 3D canvas 出現且有大小 | ✓ | [332, 340] |  |
| #industry/ai_server | 2D 切換鈕 | tap → 切到 2D | ✓ | 觸控 52x40 |  |
| #industry/ai_server | 產業鏈分頁「全市場 464」 | tap → 換頁（或回頂） | ✓ | #industry |  |
| #industry/ai_server | 產業鏈分頁「半導體 157」 | tap → 換頁（或回頂） | ✓ | #industry/semiconductor |  |
| #industry/ai_server | 產業鏈分頁「AI 伺服器 100」 | tap → 換頁（或回頂） | ✓ | #industry/ai_server |  |
| #industry/ai_server | 產業鏈分頁「矽光子／CPO 42」 | tap → 換頁（或回頂） | ✓ | #industry/siph_cpo |  |
| #industry/ai_server | 產業鏈分頁「一般電子 101」 | tap → 換頁（或回頂） | ✓ | #industry/electronics |  |
| #industry/ai_server | 產業鏈分頁「軟體與資訊服務 11」 | tap → 換頁（或回頂） | ✓ | #industry/software |  |
| #industry/ai_server | 產業鏈分頁「金融 20」 | tap → 換頁（或回頂） | ✓ | #industry/financial |  |
| #industry/ai_server | 產業鏈分頁「傳產與內需 51」 | tap → 換頁（或回頂） | ✓ | #industry/traditional |  |
| #industry/ai_server | 產業鏈分頁「基礎建設與能源 24」 | tap → 換頁（或回頂） | ✓ | #industry/infrastructure |  |
| #industry/ai_server | 產業鏈分頁「法定產業別 1878」 | tap → 換頁（或回頂） | ✓ | #industry/industry |  |
| #industry/ai_server | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✓ | #industry/ai_server/overview |  |
| #industry/ai_server | 環節 chip「AI 伺服器」 | tap → 換到那一頁 | ✓ | #industry/ai_server/dg/ai_server |  |
| #industry/ai_server | 環節 chip「IC 載板」 | tap → 換到那一頁 | ✓ | #industry/ai_server/dg/ic_substrate |  |
| #industry/ai_server | 環節 chip「電源」 | tap → 換到那一頁 | ✓ | #industry/ai_server/dg/server_psu |  |
| #industry/ai_server | 環節 chip「PCB 硬板」 | tap → 換到那一頁 | ✓ | #industry/ai_server/dg/pcb_rigid |  |
| #industry/ai_server | 環節 chip「液冷」 | tap → 換到那一頁 | ✓ | #industry/ai_server/dg/liquid_cooling |  |
| #industry/ai_server | 環節 chip「氣冷」 | tap → 換到那一頁 | ✓ | #industry/ai_server/dg/air_cooling |  |
| #industry/ai_server | 環節 chip「網通」 | tap → 換到那一頁 | ✓ | #industry/ai_server/dg/switch_wireless |  |
| #industry/ai_server | 環節 chip「連接器」 | tap → 換到那一頁 | ✓ | #industry/ai_server/dg/ai_interconnect |  |
| #industry/ai_server | 篩選環節下拉 | tap → 展開清單 | ✓ |  |  |
| #industry/ai_server | 篩選環節選項數 | 清單出現 | ✓ | 20 格 |  |
| #industry/ai_server | 環節選項 #1「銅箔 / 玻纖布 / 樹脂 6」 | tap → 關聯圖改變／關閉清單 | ✓ |  |  |
| #industry/ai_server | 環節選項 #2「IC 設計 4」 | tap → 關聯圖改變／關閉清單 | ✓ |  |  |
| #industry/ai_server | 環節選項 #3「載板材料 ABF / BT 外商」 | tap → 關聯圖改變／關閉清單 | ✓ |  |  |
| #industry/ai_server | 環節選項 #4「晶圓代工 3」 | tap → 關聯圖改變／關閉清單 | ✓ |  |  |
| #industry/ai_server | 環節選項 #5「HBM 記憶體 外商 2」 | tap → 關聯圖改變／關閉清單 | ✓ |  |  |
| #industry/ai_server | 環節選項 #6「CCL 銅箔基板 4」 | tap → 關聯圖改變／關閉清單 | ✓ |  |  |
| #industry/ai_server | 環節選項 #7「先進封裝 CoWoS/SoIC 」 | tap → 關聯圖改變／關閉清單 | ✓ |  |  |
| #industry/ai_server | 環節選項 #8「封測 / 測試 7」 | tap → 關聯圖改變／關閉清單 | ✓ |  |  |
| #industry/ai_server | 環節選項 #9「IC 載板（ABF / BT） 」 | tap → 關聯圖改變／關閉清單 | ✓ |  |  |
| #industry/ai_server | 環節選項 #10「測試介面 探針卡 4」 | tap → 關聯圖改變／關閉清單 | ✓ |  |  |
| #industry/ai_server | 環節選項 #11「高階 PCB（HDI/高層板） 」 | tap → 關聯圖改變／關閉清單 | ✓ |  |  |
| #industry/ai_server | 環節選項 #12「光通訊磊晶 / 雷射晶粒 2」 | tap → 關聯圖改變／關閉清單 | ✓ |  |  |
| #industry/ai_server | 關聯圖環節卡 #1「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 131x23（<32） |  |
| #industry/ai_server | 關聯圖環節卡 #2「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 126x28（<32） |  |
| #industry/ai_server | 關聯圖環節卡 #3「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 131x23（<32） |  |
| #industry/ai_server | 公司名連結（頁上） | （頁上沒有） | ✓ | 略 |  |
| #industry/ai_server | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/ai_server/overview | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_ai_server_overview_390d.png |
| #industry/ai_server/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/ai_server/overview | 麵包屑「產業地圖」 | tap → 回 #industry | ✓ | #industry |  |
| #industry/ai_server/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/ai_server/overview | 「?」說明鈕 #2「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/ai_server/overview | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/ai_server/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/ai_server/overview |  |
| #industry/ai_server/overview | 環節 chip「AI 伺服器」 | tap → 換到那一頁 | ✓ | #industry/ai_server/dg/ai_server |  |
| #industry/ai_server/overview | 環節 chip「IC 載板」 | tap → 換到那一頁 | ✓ | #industry/ai_server/dg/ic_substrate |  |
| #industry/ai_server/overview | 環節 chip「電源」 | tap → 換到那一頁 | ✓ | #industry/ai_server/dg/server_psu |  |
| #industry/ai_server/overview | 環節 chip「PCB 硬板」 | tap → 換到那一頁 | ✓ | #industry/ai_server/dg/pcb_rigid |  |
| #industry/ai_server/overview | 環節 chip「液冷」 | tap → 換到那一頁 | ✓ | #industry/ai_server/dg/liquid_cooling |  |
| #industry/ai_server/overview | 環節 chip「氣冷」 | tap → 換到那一頁 | ✓ | #industry/ai_server/dg/air_cooling |  |
| #industry/ai_server/overview | 環節 chip「網通」 | tap → 換到那一頁 | ✓ | #industry/ai_server/dg/switch_wireless |  |
| #industry/ai_server/overview | 環節 chip「連接器」 | tap → 換到那一頁 | ✓ | #industry/ai_server/dg/ai_interconnect |  |
| #industry/ai_server/overview | 篩選環節下拉 | tap → 展開清單 | ✓ |  |  |
| #industry/ai_server/overview | 篩選環節選項數 | 清單出現 | ✓ | 20 格 |  |
| #industry/ai_server/overview | 公司名連結（頁上） | （頁上沒有） | ✓ | 略 |  |
| #industry/ai_server/overview | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/ai_server/dg/ai_server | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_ai_server_dg_ai_server_390d.png |
| #industry/ai_server/dg/ai_server | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/ai_server/dg/ai_server | 麵包屑「產業地圖」 | tap → 回 #industry | ✓ | #industry |  |
| #industry/ai_server/dg/ai_server | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/ai_server/dg/ai_server | 「?」說明鈕 #2「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/ai_server/dg/ai_server | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/ai_server/dg/ai_server | 圖說鈕 | tap → 畫面改變 | ✓ |  |  |
| #industry/ai_server/dg/ai_server | 編號開關 | tap → 畫面改變 | ✓ |  |  |
| #industry/ai_server/dg/ai_server | 剖析圖編號 #01（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/ai_server/dg/ai_server | 零件卡公司連結「智邦 2345」 | 連到 #stock/2345 | ✓ |  |  |
| #industry/ai_server/dg/ai_server | 零件卡鈕「‹」 | tap → 畫面改變 | ✓ |  |  |
| #industry/ai_server/dg/ai_server | 零件卡鈕「›」 | tap → 畫面改變 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/ai_server/dg/ai_server | 剖析圖編號 #02（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/ai_server/dg/ai_server | 剖析圖編號 #03（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/ai_server/dg/ai_server | 剖析圖編號 #04（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/ai_server/dg/ai_server | 剖析圖編號 #05（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x26 |  |
| #industry/ai_server/dg/ai_server | 剖析圖編號 #06（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x30 |  |
| #industry/ai_server/dg/ai_server | 剖析圖編號 #07（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/ai_server/dg/ai_server | 剖析圖編號 #08（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/ai_server/dg/ai_server | 剖析圖編號 #09（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/ai_server/dg/ai_server | 剖析圖編號 #10（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/ai_server/dg/ai_server | 剖析圖編號 #11（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/ai_server/dg/ai_server | 剖析圖編號 #12（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/ai_server/dg/ai_server | 剖析圖編號 #13（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/ai_server/dg/ai_server | 3D 切換鈕 | tap → 切到 3D | ✓ | 觸控 52x40 |  |
| #industry/ai_server/dg/ai_server | 3D 畫面 | 3D canvas 出現且有大小 | ✓ | [332, 340] |  |
| #industry/ai_server/dg/ai_server | 2D 切換鈕 | tap → 切到 2D | ✓ | 觸控 52x40 |  |
| #industry/ai_server/dg/ai_server | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✓ | #industry/ai_server/overview |  |
| #industry/ai_server/dg/ai_server | 環節 chip「AI 伺服器」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/ai_server/dg/ai_server |  |
| #industry/ai_server/dg/ai_server | 環節 chip「IC 載板」 | tap → 換到那一頁 | ✓ | #industry/ai_server/dg/ic_substrate |  |
| #industry/ai_server/dg/ai_server | 環節 chip「電源」 | tap → 換到那一頁 | ✓ | #industry/ai_server/dg/server_psu |  |
| #industry/ai_server/dg/ai_server | 環節 chip「PCB 硬板」 | tap → 換到那一頁 | ✓ | #industry/ai_server/dg/pcb_rigid |  |
| #industry/ai_server/dg/ai_server | 環節 chip「液冷」 | tap → 換到那一頁 | ✓ | #industry/ai_server/dg/liquid_cooling |  |
| #industry/ai_server/dg/ai_server | 環節 chip「氣冷」 | tap → 換到那一頁 | ✓ | #industry/ai_server/dg/air_cooling |  |
| #industry/ai_server/dg/ai_server | 環節 chip「網通」 | tap → 換到那一頁 | ✓ | #industry/ai_server/dg/switch_wireless |  |
| #industry/ai_server/dg/ai_server | 環節 chip「連接器」 | tap → 換到那一頁 | ✓ | #industry/ai_server/dg/ai_interconnect |  |
| #industry/ai_server/dg/ai_server | 篩選環節下拉 | tap → 展開清單 | ✓ |  |  |
| #industry/ai_server/dg/ai_server | 篩選環節選項數 | 清單出現 | ✓ | 20 格 |  |
| #industry/ai_server/dg/ai_server | 公司名連結（頁上） | （頁上沒有） | ✓ | 略 |  |
| #industry/ai_server/dg/ai_server | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/ai_server/dg/ic_substrate | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_ai_server_dg_ic_substrate_390d.png |
| #industry/ai_server/dg/ic_substrate | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；? 18x18；產業地圖 5 |  |
| #industry/ai_server/dg/ic_substrate | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/ai_server/dg/server_psu | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_ai_server_dg_server_psu_390d.png |
| #industry/ai_server/dg/server_psu | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；? 18x18；產業地圖 5 |  |
| #industry/ai_server/dg/server_psu | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/ai_server/dg/pcb_rigid | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_ai_server_dg_pcb_rigid_390d.png |
| #industry/ai_server/dg/pcb_rigid | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/ai_server/dg/pcb_rigid | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/ai_server/dg/liquid_cooling | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_ai_server_dg_liquid_cooling_390d.png |
| #industry/ai_server/dg/liquid_cooling | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；? 18x18 |  |
| #industry/ai_server/dg/liquid_cooling | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/ai_server/dg/air_cooling | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_ai_server_dg_air_cooling_390d.png |
| #industry/ai_server/dg/air_cooling | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/ai_server/dg/air_cooling | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/ai_server/dg/switch_wireless | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_ai_server_dg_switch_wireless_390d.png |
| #industry/ai_server/dg/switch_wireless | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；11 20x20；? 18x18；產業地圖 5 |  |
| #industry/ai_server/dg/switch_wireless | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/ai_server/dg/ai_interconnect | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_ai_server_dg_ai_interconnect_390d.png |
| #industry/ai_server/dg/ai_interconnect | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/ai_server/dg/ai_interconnect | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/siph_cpo | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_siph_cpo_390d.png |
| #industry/siph_cpo | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；? 18x18；產業地圖 5 |  |
| #industry/siph_cpo | 麵包屑「產業地圖」 | tap → 回 #industry | ✓ | #industry |  |
| #industry/siph_cpo | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/siph_cpo | 「?」說明鈕 #2「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/siph_cpo | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/siph_cpo | 圖說鈕 | tap → 畫面改變 | ✓ |  |  |
| #industry/siph_cpo | 編號開關 | tap → 畫面改變 | ✓ |  |  |
| #industry/siph_cpo | 剖析圖編號 #01（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x26 |  |
| #industry/siph_cpo | 零件卡鈕「‹」 | tap → 畫面改變 | ✓ |  |  |
| #industry/siph_cpo | 零件卡鈕「›」 | tap → 畫面改變 | ✓ |  |  |
| #industry/siph_cpo | 整頁 | 腳本例外 | ✗ | 假陽性（腳本；人工逐顆點 10／7／10 顆編號全開）｜'NoneType' object is not subscriptable |  |
| #industry/siph_cpo | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/siph_cpo/overview | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_siph_cpo_overview_390d.png |
| #industry/siph_cpo/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修（成員表個股／族群連結 18 高 → 可點 36）／編號交剖析圖｜2303 聯電 60x18；2313 華通 60x18；2330 台積電 73x18；2345 智邦 60x18；2360 致茂 60x18；2383 台光電 73x18；2454 聯發科 73x18；2455 全新 60x18；3008 大立光 73x18；3037 欣興 60x18；3081 聯亞 60x18；3 |  |
| #industry/siph_cpo/overview | 麵包屑「產業地圖」 | tap → 回 #industry | ✓ | #industry |  |
| #industry/siph_cpo/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/siph_cpo/overview | 「?」說明鈕 #2「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/siph_cpo/overview | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/siph_cpo/overview | 「?」說明鈕 #4「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/siph_cpo/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/siph_cpo/overview |  |
| #industry/siph_cpo/overview | 環節 chip「CPO 交換器封裝」 | tap → 換到那一頁 | ✓ | #industry/siph_cpo/dg/siph_pkg |  |
| #industry/siph_cpo/overview | 環節 chip「光訊號路徑與四種光互連架構」 | tap → 換到那一頁 | ✓ | #industry/siph_cpo/dg/siph_module |  |
| #industry/siph_cpo/overview | 篩選環節下拉 | tap → 展開清單 | ✓ |  |  |
| #industry/siph_cpo/overview | 篩選環節選項數 | 清單出現 | ✓ | 23 格 |  |
| #industry/siph_cpo/overview | 公司名連結（頁上） #1「3105 穩懋」 | touchscreen.tap → 換到個股頁 | ✓ |  |  |
| #industry/siph_cpo/overview | 公司名連結（頁上） #2「3081 聯亞」 | touchscreen.tap → 換到個股頁 | ✓ |  |  |
| #industry/siph_cpo/overview | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/siph_cpo/dg/siph_pkg | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_siph_cpo_dg_siph_pkg_390d.png |
| #industry/siph_cpo/dg/siph_pkg | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；? 18x18；產業地圖 5 |  |
| #industry/siph_cpo/dg/siph_pkg | 麵包屑「產業地圖」 | tap → 回 #industry | ✓ | #industry |  |
| #industry/siph_cpo/dg/siph_pkg | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/siph_cpo/dg/siph_pkg | 「?」說明鈕 #2「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/siph_cpo/dg/siph_pkg | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/siph_cpo/dg/siph_pkg | 圖說鈕 | tap → 畫面改變 | ✓ |  |  |
| #industry/siph_cpo/dg/siph_pkg | 編號開關 | tap → 畫面改變 | ✓ |  |  |
| #industry/siph_cpo/dg/siph_pkg | 剖析圖編號 #01（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x26 |  |
| #industry/siph_cpo/dg/siph_pkg | 零件卡鈕「‹」 | tap → 畫面改變 | ✓ |  |  |
| #industry/siph_cpo/dg/siph_pkg | 零件卡鈕「›」 | tap → 畫面改變 | ✓ |  |  |
| #industry/siph_cpo/dg/siph_pkg | 整頁 | 腳本例外 | ✗ | 假陽性（腳本；人工逐顆點 10／7／10 顆編號全開）｜'NoneType' object is not subscriptable |  |
| #industry/siph_cpo/dg/siph_pkg | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/siph_cpo/dg/siph_module | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_siph_cpo_dg_siph_module_390d.png |
| #industry/siph_cpo/dg/siph_module | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/siph_cpo/dg/siph_module | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/electronics | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_electronics_390d.png |
| #industry/electronics | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/electronics | 麵包屑「產業地圖」 | tap → 回 #industry | ✓ | #industry |  |
| #industry/electronics | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/electronics | 「?」說明鈕 #2「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/electronics | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/electronics | 圖說鈕 | tap → 畫面改變 | ✓ |  |  |
| #industry/electronics | 編號開關 | tap → 畫面改變 | ✓ |  |  |
| #industry/electronics | 剖析圖編號 #01（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/electronics | 零件卡公司連結「國巨* 2327」 | 連到 #stock/2327 | ✓ |  |  |
| #industry/electronics | 零件卡公司連結「華新科 2492」 | 連到 #stock/2492 | ✓ |  |  |
| #industry/electronics | 零件卡公司連結「凱美 2375」 | 連到 #stock/2375 | ✓ |  |  |
| #industry/electronics | 零件卡公司連結「禾伸堂 3026」 | 連到 #stock/3026 | ✓ |  |  |
| #industry/electronics | 零件卡公司連結「信昌電 6173」 | 連到 #stock/6173 | ✓ |  |  |
| #industry/electronics | 零件卡公司連結「光頡 3624」 | 連到 #stock/3624 | ✓ |  |  |
| #industry/electronics | 零件卡公司連結「大毅 2478」 | 連到 #stock/2478 | ✓ |  |  |
| #industry/electronics | 零件卡鈕「‹」 | tap → 畫面改變 | ✓ |  |  |
| #industry/electronics | 零件卡鈕「›」 | tap → 畫面改變 | ✓ |  |  |
| #industry/electronics | 剖析圖編號 #02（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/electronics | 剖析圖編號 #03（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/electronics | 剖析圖編號 #04（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/electronics | 剖析圖編號 #05（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/electronics | 剖析圖編號 #06（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/electronics | 3D 切換鈕 | tap → 切到 3D | ✓ | 觸控 52x40 |  |
| #industry/electronics | 3D 畫面 | 3D canvas 出現且有大小 | ✓ | [332, 340] |  |
| #industry/electronics | 2D 切換鈕 | tap → 切到 2D | ✓ | 觸控 52x40 |  |
| #industry/electronics | 產業鏈分頁「全市場 464」 | tap → 換頁（或回頂） | ✓ | #industry |  |
| #industry/electronics | 產業鏈分頁「半導體 157」 | tap → 換頁（或回頂） | ✓ | #industry/semiconductor |  |
| #industry/electronics | 產業鏈分頁「AI 伺服器 100」 | tap → 換頁（或回頂） | ✓ | #industry/ai_server |  |
| #industry/electronics | 產業鏈分頁「矽光子／CPO 42」 | tap → 換頁（或回頂） | ✓ | #industry/siph_cpo |  |
| #industry/electronics | 產業鏈分頁「一般電子 101」 | tap → 換頁（或回頂） | ✓ | #industry/electronics |  |
| #industry/electronics | 產業鏈分頁「軟體與資訊服務 11」 | tap → 換頁（或回頂） | ✓ | #industry/software |  |
| #industry/electronics | 產業鏈分頁「金融 20」 | tap → 換頁（或回頂） | ✓ | #industry/financial |  |
| #industry/electronics | 產業鏈分頁「傳產與內需 51」 | tap → 換頁（或回頂） | ✓ | #industry/traditional |  |
| #industry/electronics | 產業鏈分頁「基礎建設與能源 24」 | tap → 換頁（或回頂） | ✓ | #industry/infrastructure |  |
| #industry/electronics | 產業鏈分頁「法定產業別 1878」 | tap → 換頁（或回頂） | ✓ | #industry/industry |  |
| #industry/electronics | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✓ | #industry/electronics/overview |  |
| #industry/electronics | 環節 chip「被動元件」 | tap → 換到那一頁 | ✓ | #industry/electronics/dg/mlcc |  |
| #industry/electronics | 環節 chip「面板」 | tap → 換到那一頁 | ✓ | #industry/electronics/dg/panel |  |
| #industry/electronics | 環節 chip「工業自動化」 | tap → 換到那一頁 | ✓ | #industry/electronics/dg/factory_automation |  |
| #industry/electronics | 環節 chip「被動保護」 | tap → 換到那一頁 | ✓ | #industry/electronics/dg/resistor_protect |  |
| #industry/electronics | 環節 chip「電容器」 | tap → 換到那一頁 | ✓ | #industry/electronics/dg/capacitor |  |
| #industry/electronics | 環節 chip「被動元件」 | tap → 換到那一頁 | ✓ | #industry/electronics/dg/power_inductor |  |
| #industry/electronics | 環節 chip「CNC 工具機」 | tap → 換到那一頁 | ✓ | #industry/electronics/dg/machine_tool |  |
| #industry/electronics | 延伸閱讀 #1 | tap → 展開 | ✓ | ＋ 延伸 1｜端電極四層 ＋ 板 |  |
| #industry/electronics | 延伸閱讀 #2 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 2｜怎麼做出來的：十道 |  |
| #industry/electronics | 延伸閱讀 #3 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 3｜尺寸代號有兩套、這 |  |
| #industry/electronics | 篩選環節下拉 | tap → 展開清單 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/electronics | 篩選環節選項數 | 清單出現 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜0 格 |  |
| #industry/electronics | 關聯圖環節卡 #1「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 131x23（<32） |  |
| #industry/electronics | 關聯圖環節卡 #2「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 126x30（<32） |  |
| #industry/electronics | 關聯圖環節卡 #3「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 131x23（<32） |  |
| #industry/electronics | 公司名連結（頁上） | （頁上沒有） | ✓ | 略 |  |
| #industry/electronics | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/electronics/overview | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_electronics_overview_390d.png |
| #industry/electronics/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/electronics/overview | 麵包屑「產業地圖」 | tap → 回 #industry | ✓ | #industry |  |
| #industry/electronics/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/electronics/overview | 「?」說明鈕 #2「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/electronics/overview | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/electronics/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/electronics/overview |  |
| #industry/electronics/overview | 環節 chip「被動元件」 | tap → 換到那一頁 | ✓ | #industry/electronics/dg/mlcc |  |
| #industry/electronics/overview | 環節 chip「面板」 | tap → 換到那一頁 | ✓ | #industry/electronics/dg/panel |  |
| #industry/electronics/overview | 環節 chip「工業自動化」 | tap → 換到那一頁 | ✓ | #industry/electronics/dg/factory_automation |  |
| #industry/electronics/overview | 環節 chip「被動保護」 | tap → 換到那一頁 | ✓ | #industry/electronics/dg/resistor_protect |  |
| #industry/electronics/overview | 環節 chip「電容器」 | tap → 換到那一頁 | ✓ | #industry/electronics/dg/capacitor |  |
| #industry/electronics/overview | 環節 chip「被動元件」 | tap → 換到那一頁 | ✓ | #industry/electronics/dg/power_inductor |  |
| #industry/electronics/overview | 環節 chip「CNC 工具機」 | tap → 換到那一頁 | ✓ | #industry/electronics/dg/machine_tool |  |
| #industry/electronics/overview | 篩選環節下拉 | tap → 展開清單 | ✓ |  |  |
| #industry/electronics/overview | 篩選環節選項數 | 清單出現 | ✓ | 19 格 |  |
| #industry/electronics/overview | 公司名連結（頁上） | （頁上沒有） | ✓ | 略 |  |
| #industry/electronics/overview | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/electronics/dg/mlcc | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_electronics_dg_mlcc_390d.png |
| #industry/electronics/dg/mlcc | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/electronics/dg/mlcc | 麵包屑「產業地圖」 | tap → 回 #industry | ✓ | #industry |  |
| #industry/electronics/dg/mlcc | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/electronics/dg/mlcc | 「?」說明鈕 #2「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/electronics/dg/mlcc | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/electronics/dg/mlcc | 圖說鈕 | tap → 畫面改變 | ✓ |  |  |
| #industry/electronics/dg/mlcc | 編號開關 | tap → 畫面改變 | ✓ |  |  |
| #industry/electronics/dg/mlcc | 剖析圖編號 #01（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/electronics/dg/mlcc | 零件卡公司連結「國巨* 2327」 | 連到 #stock/2327 | ✓ |  |  |
| #industry/electronics/dg/mlcc | 零件卡公司連結「華新科 2492」 | 連到 #stock/2492 | ✓ |  |  |
| #industry/electronics/dg/mlcc | 零件卡公司連結「凱美 2375」 | 連到 #stock/2375 | ✓ |  |  |
| #industry/electronics/dg/mlcc | 零件卡公司連結「禾伸堂 3026」 | 連到 #stock/3026 | ✓ |  |  |
| #industry/electronics/dg/mlcc | 零件卡公司連結「信昌電 6173」 | 連到 #stock/6173 | ✓ |  |  |
| #industry/electronics/dg/mlcc | 零件卡公司連結「光頡 3624」 | 連到 #stock/3624 | ✓ |  |  |
| #industry/electronics/dg/mlcc | 零件卡公司連結「大毅 2478」 | 連到 #stock/2478 | ✓ |  |  |
| #industry/electronics/dg/mlcc | 零件卡鈕「‹」 | tap → 畫面改變 | ✓ |  |  |
| #industry/electronics/dg/mlcc | 零件卡鈕「›」 | tap → 畫面改變 | ✓ |  |  |
| #industry/electronics/dg/mlcc | 剖析圖編號 #02（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/electronics/dg/mlcc | 剖析圖編號 #03（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/electronics/dg/mlcc | 剖析圖編號 #04（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/electronics/dg/mlcc | 剖析圖編號 #05（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/electronics/dg/mlcc | 剖析圖編號 #06（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/electronics/dg/mlcc | 3D 切換鈕 | tap → 切到 3D | ✓ | 觸控 52x40 |  |
| #industry/electronics/dg/mlcc | 3D 畫面 | 3D canvas 出現且有大小 | ✓ | [332, 340] |  |
| #industry/electronics/dg/mlcc | 2D 切換鈕 | tap → 切到 2D | ✓ | 觸控 52x40 |  |
| #industry/electronics/dg/mlcc | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✓ | #industry/electronics/overview |  |
| #industry/electronics/dg/mlcc | 環節 chip「被動元件」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/electronics/dg/mlcc |  |
| #industry/electronics/dg/mlcc | 環節 chip「面板」 | tap → 換到那一頁 | ✓ | #industry/electronics/dg/panel |  |
| #industry/electronics/dg/mlcc | 環節 chip「工業自動化」 | tap → 換到那一頁 | ✓ | #industry/electronics/dg/factory_automation |  |
| #industry/electronics/dg/mlcc | 環節 chip「被動保護」 | tap → 換到那一頁 | ✓ | #industry/electronics/dg/resistor_protect |  |
| #industry/electronics/dg/mlcc | 環節 chip「電容器」 | tap → 換到那一頁 | ✓ | #industry/electronics/dg/capacitor |  |
| #industry/electronics/dg/mlcc | 環節 chip「被動元件」 | tap → 換到那一頁 | ✓ | #industry/electronics/dg/power_inductor |  |
| #industry/electronics/dg/mlcc | 環節 chip「CNC 工具機」 | tap → 換到那一頁 | ✓ | #industry/electronics/dg/machine_tool |  |
| #industry/electronics/dg/mlcc | 延伸閱讀 #1 | tap → 展開 | ✓ | ＋ 延伸 1｜端電極四層 ＋ 板 |  |
| #industry/electronics/dg/mlcc | 延伸閱讀 #2 | tap → 展開 | ✓ | ＋ 延伸 2｜怎麼做出來的：十道 |  |
| #industry/electronics/dg/mlcc | 延伸閱讀 #3 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 3｜尺寸代號有兩套、這 |  |
| #industry/electronics/dg/mlcc | 篩選環節下拉 | tap → 展開清單 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/electronics/dg/mlcc | 篩選環節選項數 | 清單出現 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜0 格 |  |
| #industry/electronics/dg/mlcc | 公司名連結（頁上） | （頁上沒有） | ✓ | 略 |  |
| #industry/electronics/dg/mlcc | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/electronics/dg/panel | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_electronics_dg_panel_390d.png |
| #industry/electronics/dg/panel | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/electronics/dg/panel | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/electronics/dg/factory_automation | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_electronics_dg_factory_automation_390d.png |
| #industry/electronics/dg/factory_automation | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/electronics/dg/factory_automation | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/electronics/dg/resistor_protect | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_electronics_dg_resistor_protect_390d.png |
| #industry/electronics/dg/resistor_protect | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/electronics/dg/resistor_protect | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/electronics/dg/capacitor | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_electronics_dg_capacitor_390d.png |
| #industry/electronics/dg/capacitor | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/electronics/dg/capacitor | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/electronics/dg/power_inductor | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_electronics_dg_power_inductor_390d.png |
| #industry/electronics/dg/power_inductor | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/electronics/dg/power_inductor | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/electronics/dg/machine_tool | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_electronics_dg_machine_tool_390d.png |
| #industry/electronics/dg/machine_tool | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/electronics/dg/machine_tool | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/software | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_software_390d.png |
| #industry/software | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/software | 麵包屑「產業地圖」 | tap → 回 #industry | ✓ | #industry |  |
| #industry/software | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/software | 「?」說明鈕 #2「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/software | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/software | 圖說鈕 | tap → 畫面改變 | ✓ |  |  |
| #industry/software | 編號開關 | tap → 畫面改變 | ✓ |  |  |
| #industry/software | 剖析圖編號 #01（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/software | 零件卡鈕「‹」 | tap → 畫面改變 | ✓ |  |  |
| #industry/software | 零件卡鈕「›」 | tap → 畫面改變 | ✓ |  |  |
| #industry/software | 整頁 | 腳本例外 | ✗ | 假陽性（腳本；人工逐顆點 10／7／10 顆編號全開）｜'NoneType' object is not subscriptable |  |
| #industry/software | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/software/overview | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_software_overview_390d.png |
| #industry/software/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/software/overview | 麵包屑「產業地圖」 | tap → 回 #industry | ✓ | #industry |  |
| #industry/software/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/software/overview | 「?」說明鈕 #2「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/software/overview | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/software/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/software/overview |  |
| #industry/software/overview | 環節 chip「雲端與 MSP」 | tap → 換到那一頁 | ✓ | #industry/software/dg/cloud_msp |  |
| #industry/software/overview | 環節 chip「企業 SaaS」 | tap → 換到那一頁 | ✓ | #industry/software/dg/saas |  |
| #industry/software/overview | 環節 chip「資安防護」 | tap → 換到那一頁 | ✓ | #industry/software/dg/cyber_security |  |
| #industry/software/overview | 環節 chip「電商零售」 | tap → 換到那一頁 | ✓ | #industry/software/dg/ecommerce |  |
| #industry/software/overview | 篩選環節下拉 | tap → 展開清單 | ✓ |  |  |
| #industry/software/overview | 篩選環節選項數 | 清單出現 | ✓ | 5 格 |  |
| #industry/software/overview | 公司名連結（頁上） | （頁上沒有） | ✓ | 略 |  |
| #industry/software/overview | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/software/dg/cloud_msp | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_software_dg_cloud_msp_390d.png |
| #industry/software/dg/cloud_msp | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/software/dg/cloud_msp | 麵包屑「產業地圖」 | tap → 回 #industry | ✓ | #industry |  |
| #industry/software/dg/cloud_msp | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/software/dg/cloud_msp | 「?」說明鈕 #2「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/software/dg/cloud_msp | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/software/dg/cloud_msp | 圖說鈕 | tap → 畫面改變 | ✓ |  |  |
| #industry/software/dg/cloud_msp | 編號開關 | tap → 畫面改變 | ✓ |  |  |
| #industry/software/dg/cloud_msp | 剖析圖編號 #01（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/software/dg/cloud_msp | 零件卡鈕「‹」 | tap → 畫面改變 | ✓ |  |  |
| #industry/software/dg/cloud_msp | 零件卡鈕「›」 | tap → 畫面改變 | ✓ |  |  |
| #industry/software/dg/cloud_msp | 整頁 | 腳本例外 | ✗ | 假陽性（腳本；人工逐顆點 10／7／10 顆編號全開）｜'NoneType' object is not subscriptable |  |
| #industry/software/dg/cloud_msp | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/software/dg/saas | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_software_dg_saas_390d.png |
| #industry/software/dg/saas | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/software/dg/saas | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/software/dg/cyber_security | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_software_dg_cyber_security_390d.png |
| #industry/software/dg/cyber_security | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/software/dg/cyber_security | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/software/dg/ecommerce | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_software_dg_ecommerce_390d.png |
| #industry/software/dg/ecommerce | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/software/dg/ecommerce | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/financial | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_financial_390d.png |
| #industry/financial | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/financial | 麵包屑「產業地圖」 | tap → 回 #industry | ✓ | #industry |  |
| #industry/financial | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/financial | 「?」說明鈕 #2「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/financial | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/financial | 圖說鈕 | tap → 畫面改變 | ✓ |  |  |
| #industry/financial | 編號開關 | tap → 畫面改變 | ✓ |  |  |
| #industry/financial | 剖析圖編號 #01（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/financial | 零件卡公司連結「中信金 2891」 | 連到 #stock/2891 | ✓ |  |  |
| #industry/financial | 零件卡公司連結「第一金 2892」 | 連到 #stock/2892 | ✓ |  |  |
| #industry/financial | 零件卡公司連結「華南金 2880」 | 連到 #stock/2880 | ✓ |  |  |
| #industry/financial | 零件卡公司連結「兆豐金 2886」 | 連到 #stock/2886 | ✓ |  |  |
| #industry/financial | 零件卡公司連結「合庫金 5880」 | 連到 #stock/5880 | ✓ |  |  |
| #industry/financial | 零件卡公司連結「玉山金 2884」 | 連到 #stock/2884 | ✓ |  |  |
| #industry/financial | 零件卡公司連結「永豐金 2890」 | 連到 #stock/2890 | ✓ |  |  |
| #industry/financial | 零件卡公司連結「台新新光金 2887」 | 連到 #stock/2887 | ✓ |  |  |
| #industry/financial | 零件卡鈕「‹」 | tap → 畫面改變 | ✓ |  |  |
| #industry/financial | 零件卡鈕「›」 | tap → 畫面改變 | ✓ |  |  |
| #industry/financial | 剖析圖編號 #02（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/financial | 剖析圖編號 #03（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/financial | 剖析圖編號 #04（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/financial | 剖析圖編號 #05（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/financial | 剖析圖編號 #06（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/financial | 剖析圖編號 #07（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/financial | 剖析圖編號 #08（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/financial | 剖析圖編號 #09（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/financial | 剖析圖編號 #10（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/financial | 剖析圖編號 #11（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/financial | 剖析圖編號 #12（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/financial | 剖析圖編號 #13（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/financial | 剖析圖編號 #14（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/financial | 剖析圖編號 #15（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/financial | 產業鏈分頁「全市場 464」 | tap → 換頁（或回頂） | ✓ | #industry |  |
| #industry/financial | 產業鏈分頁「半導體 157」 | tap → 換頁（或回頂） | ✓ | #industry/semiconductor |  |
| #industry/financial | 產業鏈分頁「AI 伺服器 100」 | tap → 換頁（或回頂） | ✓ | #industry/ai_server |  |
| #industry/financial | 產業鏈分頁「矽光子／CPO 42」 | tap → 換頁（或回頂） | ✓ | #industry/siph_cpo |  |
| #industry/financial | 產業鏈分頁「一般電子 101」 | tap → 換頁（或回頂） | ✓ | #industry/electronics |  |
| #industry/financial | 產業鏈分頁「軟體與資訊服務 11」 | tap → 換頁（或回頂） | ✓ | #industry/software |  |
| #industry/financial | 產業鏈分頁「金融 20」 | tap → 換頁（或回頂） | ✓ | #industry/financial |  |
| #industry/financial | 產業鏈分頁「傳產與內需 51」 | tap → 換頁（或回頂） | ✓ | #industry/traditional |  |
| #industry/financial | 產業鏈分頁「基礎建設與能源 24」 | tap → 換頁（或回頂） | ✓ | #industry/infrastructure |  |
| #industry/financial | 產業鏈分頁「法定產業別 1878」 | tap → 換頁（或回頂） | ✓ | #industry/industry |  |
| #industry/financial | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✓ | #industry/financial/overview |  |
| #industry/financial | 環節 chip「銀行金融」 | tap → 換到那一頁 | ✓ | #industry/financial/dg/bank |  |
| #industry/financial | 環節 chip「壽險金控」 | tap → 換到那一頁 | ✓ | #industry/financial/dg/life_fhc |  |
| #industry/financial | 環節 chip「證券金控」 | tap → 換到那一頁 | ✓ | #industry/financial/dg/securities_fhc |  |
| #industry/financial | 延伸閱讀 #1 | tap → 展開 | ✓ | ＋ 延伸 1｜升息之後，哪一段先 |  |
| #industry/financial | 延伸閱讀 #2 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 2｜為什麼用 PB-R |  |
| #industry/financial | 篩選環節下拉 | tap → 展開清單 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/financial | 篩選環節選項數 | 清單出現 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜0 格 |  |
| #industry/financial | 關聯圖環節卡 #1「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 199x23（<32） |  |
| #industry/financial | 關聯圖環節卡 #2「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 194x28（<32） |  |
| #industry/financial | 關聯圖環節卡 #3「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 199x23（<32） |  |
| #industry/financial | 公司名連結（頁上） | （頁上沒有） | ✓ | 略 |  |
| #industry/financial | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/financial/overview | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_financial_overview_390d.png |
| #industry/financial/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/financial/overview | 麵包屑「產業地圖」 | tap → 回 #industry | ✓ | #industry |  |
| #industry/financial/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/financial/overview | 「?」說明鈕 #2「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/financial/overview | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/financial/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/financial/overview |  |
| #industry/financial/overview | 環節 chip「銀行金融」 | tap → 換到那一頁 | ✓ | #industry/financial/dg/bank |  |
| #industry/financial/overview | 環節 chip「壽險金控」 | tap → 換到那一頁 | ✓ | #industry/financial/dg/life_fhc |  |
| #industry/financial/overview | 環節 chip「證券金控」 | tap → 換到那一頁 | ✓ | #industry/financial/dg/securities_fhc |  |
| #industry/financial/overview | 篩選環節下拉 | tap → 展開清單 | ✓ |  |  |
| #industry/financial/overview | 篩選環節選項數 | 清單出現 | ✓ | 3 格 |  |
| #industry/financial/overview | 公司名連結（頁上） | （頁上沒有） | ✓ | 略 |  |
| #industry/financial/overview | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/financial/dg/bank | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_financial_dg_bank_390d.png |
| #industry/financial/dg/bank | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/financial/dg/bank | 麵包屑「產業地圖」 | tap → 回 #industry | ✓ | #industry |  |
| #industry/financial/dg/bank | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/financial/dg/bank | 「?」說明鈕 #2「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/financial/dg/bank | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/financial/dg/bank | 圖說鈕 | tap → 畫面改變 | ✓ |  |  |
| #industry/financial/dg/bank | 編號開關 | tap → 畫面改變 | ✓ |  |  |
| #industry/financial/dg/bank | 剖析圖編號 #01（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/financial/dg/bank | 零件卡公司連結「中信金 2891」 | 連到 #stock/2891 | ✓ |  |  |
| #industry/financial/dg/bank | 零件卡公司連結「第一金 2892」 | 連到 #stock/2892 | ✓ |  |  |
| #industry/financial/dg/bank | 零件卡公司連結「華南金 2880」 | 連到 #stock/2880 | ✓ |  |  |
| #industry/financial/dg/bank | 零件卡公司連結「兆豐金 2886」 | 連到 #stock/2886 | ✓ |  |  |
| #industry/financial/dg/bank | 零件卡公司連結「合庫金 5880」 | 連到 #stock/5880 | ✓ |  |  |
| #industry/financial/dg/bank | 零件卡公司連結「玉山金 2884」 | 連到 #stock/2884 | ✓ |  |  |
| #industry/financial/dg/bank | 零件卡公司連結「永豐金 2890」 | 連到 #stock/2890 | ✓ |  |  |
| #industry/financial/dg/bank | 零件卡公司連結「台新新光金 2887」 | 連到 #stock/2887 | ✓ |  |  |
| #industry/financial/dg/bank | 零件卡鈕「‹」 | tap → 畫面改變 | ✓ |  |  |
| #industry/financial/dg/bank | 零件卡鈕「›」 | tap → 畫面改變 | ✓ |  |  |
| #industry/financial/dg/bank | 剖析圖編號 #02（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/financial/dg/bank | 剖析圖編號 #03（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/financial/dg/bank | 剖析圖編號 #04（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/financial/dg/bank | 剖析圖編號 #05（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/financial/dg/bank | 剖析圖編號 #06（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/financial/dg/bank | 剖析圖編號 #07（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/financial/dg/bank | 剖析圖編號 #08（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/financial/dg/bank | 剖析圖編號 #09（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/financial/dg/bank | 剖析圖編號 #10（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/financial/dg/bank | 剖析圖編號 #11（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/financial/dg/bank | 剖析圖編號 #12（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/financial/dg/bank | 剖析圖編號 #13（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/financial/dg/bank | 剖析圖編號 #14（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/financial/dg/bank | 剖析圖編號 #15（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/financial/dg/bank | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✓ | #industry/financial/overview |  |
| #industry/financial/dg/bank | 環節 chip「銀行金融」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/financial/dg/bank |  |
| #industry/financial/dg/bank | 環節 chip「壽險金控」 | tap → 換到那一頁 | ✓ | #industry/financial/dg/life_fhc |  |
| #industry/financial/dg/bank | 環節 chip「證券金控」 | tap → 換到那一頁 | ✓ | #industry/financial/dg/securities_fhc |  |
| #industry/financial/dg/bank | 延伸閱讀 #1 | tap → 展開 | ✓ | ＋ 延伸 1｜升息之後，哪一段先 |  |
| #industry/financial/dg/bank | 延伸閱讀 #2 | tap → 展開 | ✓ | ＋ 延伸 2｜為什麼用 PB-R |  |
| #industry/financial/dg/bank | 篩選環節下拉 | tap → 展開清單 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/financial/dg/bank | 篩選環節選項數 | 清單出現 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜0 格 |  |
| #industry/financial/dg/bank | 公司名連結（頁上） | （頁上沒有） | ✓ | 略 |  |
| #industry/financial/dg/bank | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/financial/dg/life_fhc | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_financial_dg_life_fhc_390d.png |
| #industry/financial/dg/life_fhc | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/financial/dg/life_fhc | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/financial/dg/securities_fhc | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_financial_dg_securities_fhc_390d.png |
| #industry/financial/dg/securities_fhc | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/financial/dg/securities_fhc | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/traditional | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_traditional_390d.png |
| #industry/traditional | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/traditional | 麵包屑「產業地圖」 | tap → 回 #industry | ✓ | #industry |  |
| #industry/traditional | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/traditional | 「?」說明鈕 #2「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/traditional | 圖說鈕 | tap → 畫面改變 | ✓ |  |  |
| #industry/traditional | 編號開關 | tap → 畫面改變 | ✓ |  |  |
| #industry/traditional | 剖析圖編號 #01（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x20 |  |
| #industry/traditional | 零件卡鈕「‹」 | tap → 畫面改變 | ✓ |  |  |
| #industry/traditional | 零件卡鈕「›」 | tap → 畫面改變 | ✓ |  |  |
| #industry/traditional | 剖析圖編號 #02（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x20 |  |
| #industry/traditional | 剖析圖編號 #03（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x20 |  |
| #industry/traditional | 剖析圖編號 #04（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x20 |  |
| #industry/traditional | 剖析圖編號 #05（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/traditional | 剖析圖編號 #06（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/traditional | 剖析圖編號 #07（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/traditional | 剖析圖編號 #08（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x20 |  |
| #industry/traditional | 剖析圖編號 #09（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x20 |  |
| #industry/traditional | 剖析圖編號 #10（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x20 |  |
| #industry/traditional | 剖析圖編號 #11（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/traditional | 剖析圖編號 #12（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/traditional | 剖析圖編號 #13（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x20 |  |
| #industry/traditional | 剖析圖編號 #14（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/traditional | 產業鏈分頁「全市場 464」 | tap → 換頁（或回頂） | ✓ | #industry |  |
| #industry/traditional | 產業鏈分頁「半導體 157」 | tap → 換頁（或回頂） | ✓ | #industry/semiconductor |  |
| #industry/traditional | 產業鏈分頁「AI 伺服器 100」 | tap → 換頁（或回頂） | ✓ | #industry/ai_server |  |
| #industry/traditional | 產業鏈分頁「矽光子／CPO 42」 | tap → 換頁（或回頂） | ✓ | #industry/siph_cpo |  |
| #industry/traditional | 產業鏈分頁「一般電子 101」 | tap → 換頁（或回頂） | ✓ | #industry/electronics |  |
| #industry/traditional | 產業鏈分頁「軟體與資訊服務 11」 | tap → 換頁（或回頂） | ✓ | #industry/software |  |
| #industry/traditional | 產業鏈分頁「金融 20」 | tap → 換頁（或回頂） | ✓ | #industry/financial |  |
| #industry/traditional | 產業鏈分頁「傳產與內需 51」 | tap → 換頁（或回頂） | ✓ | #industry/traditional |  |
| #industry/traditional | 產業鏈分頁「基礎建設與能源 24」 | tap → 換頁（或回頂） | ✓ | #industry/infrastructure |  |
| #industry/traditional | 產業鏈分頁「法定產業別 1878」 | tap → 換頁（或回頂） | ✓ | #industry/industry |  |
| #industry/traditional | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✓ | #industry/traditional/overview |  |
| #industry/traditional | 環節 chip「輕油裂解廠」 | tap → 換到那一頁 | ✓ | #industry/traditional/dg/petrochemical |  |
| #industry/traditional | 延伸閱讀 #1 | tap → 展開 | ✓ | ＋ 延伸 1｜四支基本原料與它們 |  |
| #industry/traditional | 延伸閱讀 #2 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 2｜製造流程（六格）： |  |
| #industry/traditional | 關聯圖環節卡 | （頁上沒有） | ✓ | 略 |  |
| #industry/traditional | 公司名連結（頁上） | （頁上沒有） | ✓ | 略 |  |
| #industry/traditional | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/traditional/overview | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_traditional_overview_390d.png |
| #industry/traditional/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/traditional/overview | 麵包屑「產業地圖」 | tap → 回 #industry | ✓ | #industry |  |
| #industry/traditional/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/traditional/overview | 「?」說明鈕 #2「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/traditional/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/traditional/overview |  |
| #industry/traditional/overview | 環節 chip「輕油裂解廠」 | tap → 換到那一頁 | ✓ | #industry/traditional/dg/petrochemical |  |
| #industry/traditional/overview | 公司名連結（頁上） | （頁上沒有） | ✓ | 略 |  |
| #industry/traditional/overview | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/traditional/dg/petrochemical | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_traditional_dg_petrochemical_390d.png |
| #industry/traditional/dg/petrochemical | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/traditional/dg/petrochemical | 麵包屑「產業地圖」 | tap → 回 #industry | ✓ | #industry |  |
| #industry/traditional/dg/petrochemical | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/traditional/dg/petrochemical | 「?」說明鈕 #2「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/traditional/dg/petrochemical | 圖說鈕 | tap → 畫面改變 | ✓ |  |  |
| #industry/traditional/dg/petrochemical | 編號開關 | tap → 畫面改變 | ✓ |  |  |
| #industry/traditional/dg/petrochemical | 剖析圖編號 #01（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x20 |  |
| #industry/traditional/dg/petrochemical | 零件卡鈕「‹」 | tap → 畫面改變 | ✓ |  |  |
| #industry/traditional/dg/petrochemical | 零件卡鈕「›」 | tap → 畫面改變 | ✓ |  |  |
| #industry/traditional/dg/petrochemical | 剖析圖編號 #02（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x20 |  |
| #industry/traditional/dg/petrochemical | 剖析圖編號 #03（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x20 |  |
| #industry/traditional/dg/petrochemical | 剖析圖編號 #04（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x20 |  |
| #industry/traditional/dg/petrochemical | 剖析圖編號 #05（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/traditional/dg/petrochemical | 剖析圖編號 #06（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/traditional/dg/petrochemical | 剖析圖編號 #07（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/traditional/dg/petrochemical | 剖析圖編號 #08（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x20 |  |
| #industry/traditional/dg/petrochemical | 剖析圖編號 #09（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x20 |  |
| #industry/traditional/dg/petrochemical | 剖析圖編號 #10（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x20 |  |
| #industry/traditional/dg/petrochemical | 剖析圖編號 #11（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/traditional/dg/petrochemical | 剖析圖編號 #12（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/traditional/dg/petrochemical | 剖析圖編號 #13（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x20 |  |
| #industry/traditional/dg/petrochemical | 剖析圖編號 #14（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/traditional/dg/petrochemical | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✓ | #industry/traditional/overview |  |
| #industry/traditional/dg/petrochemical | 環節 chip「輕油裂解廠」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/traditional/dg/petrochemical |  |
| #industry/traditional/dg/petrochemical | 延伸閱讀 #1 | tap → 展開 | ✓ | ＋ 延伸 1｜四支基本原料與它們 |  |
| #industry/traditional/dg/petrochemical | 延伸閱讀 #2 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 2｜製造流程（六格）： |  |
| #industry/traditional/dg/petrochemical | 公司名連結（頁上） | （頁上沒有） | ✓ | 略 |  |
| #industry/traditional/dg/petrochemical | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/infrastructure | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_infrastructure_390d.png |
| #industry/infrastructure | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/infrastructure | 麵包屑「產業地圖」 | tap → 回 #industry | ✓ | #industry |  |
| #industry/infrastructure | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/infrastructure | 「?」說明鈕 #2「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/infrastructure | 圖說鈕 | tap → 畫面改變 | ✓ |  |  |
| #industry/infrastructure | 編號開關 | tap → 畫面改變 | ✓ |  |  |
| #industry/infrastructure | 剖析圖編號 #01（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/infrastructure | 零件卡鈕「‹」 | tap → 畫面改變 | ✓ |  |  |
| #industry/infrastructure | 零件卡鈕「›」 | tap → 畫面改變 | ✓ |  |  |
| #industry/infrastructure | 剖析圖編號 #02（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x26 |  |
| #industry/infrastructure | 剖析圖編號 #03（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/infrastructure | 剖析圖編號 #04（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x26 |  |
| #industry/infrastructure | 剖析圖編號 #05（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x26 |  |
| #industry/infrastructure | 剖析圖編號 #06（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/infrastructure | 剖析圖編號 #07（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/infrastructure | 剖析圖編號 #08（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/infrastructure | 剖析圖編號 #09（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/infrastructure | 剖析圖編號 #10（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/infrastructure | 剖析圖編號 #11（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/infrastructure | 剖析圖編號 #12（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/infrastructure | 產業鏈分頁「全市場 464」 | tap → 換頁（或回頂） | ✓ | #industry |  |
| #industry/infrastructure | 產業鏈分頁「半導體 157」 | tap → 換頁（或回頂） | ✓ | #industry/semiconductor |  |
| #industry/infrastructure | 產業鏈分頁「AI 伺服器 100」 | tap → 換頁（或回頂） | ✓ | #industry/ai_server |  |
| #industry/infrastructure | 產業鏈分頁「矽光子／CPO 42」 | tap → 換頁（或回頂） | ✓ | #industry/siph_cpo |  |
| #industry/infrastructure | 產業鏈分頁「一般電子 101」 | tap → 換頁（或回頂） | ✓ | #industry/electronics |  |
| #industry/infrastructure | 產業鏈分頁「軟體與資訊服務 11」 | tap → 換頁（或回頂） | ✓ | #industry/software |  |
| #industry/infrastructure | 產業鏈分頁「金融 20」 | tap → 換頁（或回頂） | ✓ | #industry/financial |  |
| #industry/infrastructure | 產業鏈分頁「傳產與內需 51」 | tap → 換頁（或回頂） | ✓ | #industry/traditional |  |
| #industry/infrastructure | 產業鏈分頁「基礎建設與能源 24」 | tap → 換頁（或回頂） | ✓ | #industry/infrastructure |  |
| #industry/infrastructure | 產業鏈分頁「法定產業別 1878」 | tap → 換頁（或回頂） | ✓ | #industry/industry |  |
| #industry/infrastructure | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✓ | #industry/infrastructure/overview |  |
| #industry/infrastructure | 環節 chip「電力路徑」 | tap → 換到那一頁 | ✓ | #industry/infrastructure/dg/heavy_electric |  |
| #industry/infrastructure | 延伸閱讀 #1 | tap → 展開 | ✓ | ＋ 延伸 1｜資料中心這一側：配 |  |
| #industry/infrastructure | 延伸閱讀 #2 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 2｜工程統包與安裝：把 |  |
| #industry/infrastructure | 延伸閱讀 #3 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 3｜電力路徑（六格）： |  |
| #industry/infrastructure | 關聯圖環節卡 | （頁上沒有） | ✓ | 略 |  |
| #industry/infrastructure | 公司名連結（頁上） | （頁上沒有） | ✓ | 略 |  |
| #industry/infrastructure | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/infrastructure/overview | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_infrastructure_overview_390d.png |
| #industry/infrastructure/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/infrastructure/overview | 麵包屑「產業地圖」 | tap → 回 #industry | ✓ | #industry |  |
| #industry/infrastructure/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/infrastructure/overview | 「?」說明鈕 #2「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/infrastructure/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/infrastructure/overview |  |
| #industry/infrastructure/overview | 環節 chip「電力路徑」 | tap → 換到那一頁 | ✓ | #industry/infrastructure/dg/heavy_electric |  |
| #industry/infrastructure/overview | 公司名連結（頁上） | （頁上沒有） | ✓ | 略 |  |
| #industry/infrastructure/overview | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/infrastructure/dg/heavy_electric | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_infrastructure_dg_heavy_electric_390d.png |
| #industry/infrastructure/dg/heavy_electric | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/infrastructure/dg/heavy_electric | 麵包屑「產業地圖」 | tap → 回 #industry | ✓ | #industry |  |
| #industry/infrastructure/dg/heavy_electric | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/infrastructure/dg/heavy_electric | 「?」說明鈕 #2「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/infrastructure/dg/heavy_electric | 圖說鈕 | tap → 畫面改變 | ✓ |  |  |
| #industry/infrastructure/dg/heavy_electric | 編號開關 | tap → 畫面改變 | ✓ |  |  |
| #industry/infrastructure/dg/heavy_electric | 剖析圖編號 #01（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/infrastructure/dg/heavy_electric | 零件卡鈕「‹」 | tap → 畫面改變 | ✓ |  |  |
| #industry/infrastructure/dg/heavy_electric | 零件卡鈕「›」 | tap → 畫面改變 | ✓ |  |  |
| #industry/infrastructure/dg/heavy_electric | 剖析圖編號 #02（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x26 |  |
| #industry/infrastructure/dg/heavy_electric | 剖析圖編號 #03（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/infrastructure/dg/heavy_electric | 剖析圖編號 #04（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x26 |  |
| #industry/infrastructure/dg/heavy_electric | 剖析圖編號 #05（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x26 |  |
| #industry/infrastructure/dg/heavy_electric | 剖析圖編號 #06（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/infrastructure/dg/heavy_electric | 剖析圖編號 #07（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/infrastructure/dg/heavy_electric | 剖析圖編號 #08（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/infrastructure/dg/heavy_electric | 剖析圖編號 #09（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x24 |  |
| #industry/infrastructure/dg/heavy_electric | 剖析圖編號 #10（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/infrastructure/dg/heavy_electric | 剖析圖編號 #11（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/infrastructure/dg/heavy_electric | 剖析圖編號 #12（交給剖析圖負責人） | tap → 零件卡開啟 | ✓ | 零件卡開了；觸控區 32x32 |  |
| #industry/infrastructure/dg/heavy_electric | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✓ | #industry/infrastructure/overview |  |
| #industry/infrastructure/dg/heavy_electric | 環節 chip「電力路徑」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/infrastructure/dg/heavy_electric |  |
| #industry/infrastructure/dg/heavy_electric | 延伸閱讀 #1 | tap → 展開 | ✓ | ＋ 延伸 1｜資料中心這一側：配 |  |
| #industry/infrastructure/dg/heavy_electric | 延伸閱讀 #2 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 2｜工程統包與安裝：把 |  |
| #industry/infrastructure/dg/heavy_electric | 延伸閱讀 #3 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 3｜電力路徑（六格）： |  |
| #industry/infrastructure/dg/heavy_electric | 公司名連結（頁上） | （頁上沒有） | ✓ | 略 |  |
| #industry/infrastructure/dg/heavy_electric | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/industry | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_industry_390d.png |
| #industry/industry | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/industry | 麵包屑「產業地圖」 | tap → 回 #industry | ✓ | #industry |  |
| #industry/industry | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/industry | 產業鏈分頁「全市場 464」 | tap → 換頁（或回頂） | ✓ | #industry |  |
| #industry/industry | 產業鏈分頁「半導體 157」 | tap → 換頁（或回頂） | ✓ | #industry/semiconductor |  |
| #industry/industry | 產業鏈分頁「AI 伺服器 100」 | tap → 換頁（或回頂） | ✓ | #industry/ai_server |  |
| #industry/industry | 產業鏈分頁「矽光子／CPO 42」 | tap → 換頁（或回頂） | ✓ | #industry/siph_cpo |  |
| #industry/industry | 產業鏈分頁「一般電子 101」 | tap → 換頁（或回頂） | ✓ | #industry/electronics |  |
| #industry/industry | 產業鏈分頁「軟體與資訊服務 11」 | tap → 換頁（或回頂） | ✓ | #industry/software |  |
| #industry/industry | 產業鏈分頁「金融 20」 | tap → 換頁（或回頂） | ✓ | #industry/financial |  |
| #industry/industry | 產業鏈分頁「傳產與內需 51」 | tap → 換頁（或回頂） | ✓ | #industry/traditional |  |
| #industry/industry | 產業鏈分頁「基礎建設與能源 24」 | tap → 換頁（或回頂） | ✓ | #industry/infrastructure |  |
| #industry/industry | 產業鏈分頁「法定產業別 1878」 | tap → 換頁（或回頂） | ✓ | #industry/industry |  |
| #industry/industry | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✓ | #industry/industry/overview |  |
| #industry/industry | 關聯圖環節卡 | （頁上沒有） | ✓ | 略 |  |
| #industry/industry | 公司名連結（頁上） | （頁上沒有） | ✓ | 略 |  |
| #industry/industry | 整頁 | console error／網路 404 | ✓ |  |  |
| #industry/industry/overview | 整頁 | 橫向捲動／破圖 | ✓ | scrollWidth=390；圖 1 張；破圖 [] | indaudit_industry_industry_overview_390d.png |
| #industry/industry/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/industry/overview | 麵包屑「產業地圖」 | tap → 回 #industry | ✓ | #industry |  |
| #industry/industry/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✓ |  |  |
| #industry/industry/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/industry/overview |  |
| #industry/industry/overview | 公司名連結（頁上） | （頁上沒有） | ✓ | 略 |  |
| #industry/industry/overview | 整頁 | console error／網路 404 | ✓ |  |  |

### 390 淺色

| 頁面 | 元素 | 動作 | 結果 | 問題描述 | 截圖 |
|---|---|---|---|---|---|
| #industry 首頁 | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修｜? 18x18 |  |
| #industry 首頁 | 完整版圖連結 | tap → #heatmap | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#stock/2303 |  |
| #industry/semiconductor | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/semiconductor | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/semiconductor | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/semiconductor | 零件卡鈕「›」 | tap → 畫面改變 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/semiconductor | 延伸閱讀 #2 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 2｜製程迴圈：九站走完 |  |
| #industry/semiconductor | 延伸閱讀 #3 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 3｜節點演進：N5 → |  |
| #industry/semiconductor | 延伸閱讀 #4 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 4｜這張圖上每一段台股 |  |
| #industry/semiconductor | 篩選環節下拉 | tap → 展開清單 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/semiconductor | 篩選環節選項數 | 清單出現 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜0 格 |  |
| #industry/semiconductor | 關聯圖環節卡 #1「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 131x23（<32） |  |
| #industry/semiconductor | 關聯圖環節卡 #2「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 126x28（<32） |  |
| #industry/semiconductor | 關聯圖環節卡 #3「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 131x23（<32） |  |
| #industry/semiconductor/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/semiconductor/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/semiconductor/overview | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/semiconductor/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/semiconductor/overview |  |
| #industry/semiconductor/dg/foundry | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/semiconductor/dg/foundry | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/semiconductor/dg/foundry | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/semiconductor/dg/foundry | 零件卡鈕「›」 | tap → 畫面改變 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/semiconductor/dg/foundry | 環節 chip「晶圓代工」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/semiconductor/dg/foundry |  |
| #industry/semiconductor/dg/foundry | 延伸閱讀 #3 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 3｜節點演進：N5 → |  |
| #industry/semiconductor/dg/foundry | 延伸閱讀 #4 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 4｜這張圖上每一段台股 |  |
| #industry/semiconductor/dg/foundry | 篩選環節下拉 | tap → 展開清單 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/semiconductor/dg/foundry | 篩選環節選項數 | 清單出現 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜0 格 |  |
| #industry/semiconductor/dg/ai_adv_packaging | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/semiconductor/dg/hbm | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/semiconductor/dg/memory_module | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；? 18x18 |  |
| #industry/semiconductor/dg/silicon_wafer | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；? 18x18；產業地圖 5 |  |
| #industry/semiconductor/dg/wide_bandgap | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/ai_server | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/ai_server | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/ai_server | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/ai_server | 零件卡鈕「›」 | tap → 畫面改變 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/ai_server | 關聯圖環節卡 #1「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 131x23（<32） |  |
| #industry/ai_server | 關聯圖環節卡 #2「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 126x28（<32） |  |
| #industry/ai_server | 關聯圖環節卡 #3「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 131x23（<32） |  |
| #industry/ai_server/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/ai_server/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/ai_server/overview | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/ai_server/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/ai_server/overview |  |
| #industry/ai_server/dg/ai_server | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/ai_server/dg/ai_server | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/ai_server/dg/ai_server | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/ai_server/dg/ai_server | 零件卡鈕「›」 | tap → 畫面改變 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/ai_server/dg/ai_server | 環節 chip「AI 伺服器」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/ai_server/dg/ai_server |  |
| #industry/ai_server/dg/ic_substrate | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；? 18x18；產業地圖 5 |  |
| #industry/ai_server/dg/server_psu | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；? 18x18；產業地圖 5 |  |
| #industry/ai_server/dg/pcb_rigid | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/ai_server/dg/liquid_cooling | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；? 18x18 |  |
| #industry/ai_server/dg/air_cooling | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/ai_server/dg/switch_wireless | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；11 20x20；? 18x18；產業地圖 5 |  |
| #industry/ai_server/dg/ai_interconnect | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/siph_cpo | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；? 18x18；產業地圖 5 |  |
| #industry/siph_cpo | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/siph_cpo | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/siph_cpo | 整頁 | 腳本例外 | ✗ | 假陽性（腳本；人工逐顆點 10／7／10 顆編號全開）｜'NoneType' object is not subscriptable |  |
| #industry/siph_cpo/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修（成員表個股／族群連結 18 高 → 可點 36）／編號交剖析圖｜2303 聯電 60x18；2313 華通 60x18；2330 台積電 73x18；2345 智邦 60x18；2360 致茂 60x18；2383 台光電 73x18；2454 聯發科 73x18；2455 全新 60x18；3008 大立光 73x18；3037 欣興 60x18；3081 聯亞 60x18；3 |  |
| #industry/siph_cpo/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/siph_cpo/overview | 「?」說明鈕 #4「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/siph_cpo/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/siph_cpo/overview |  |
| #industry/siph_cpo/dg/siph_pkg | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；? 18x18；產業地圖 5 |  |
| #industry/siph_cpo/dg/siph_pkg | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/siph_cpo/dg/siph_pkg | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/siph_cpo/dg/siph_pkg | 整頁 | 腳本例外 | ✗ | 假陽性（腳本；人工逐顆點 10／7／10 顆編號全開）｜'NoneType' object is not subscriptable |  |
| #industry/siph_cpo/dg/siph_module | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/electronics | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/electronics | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/electronics | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/electronics | 延伸閱讀 #2 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 2｜怎麼做出來的：十道 |  |
| #industry/electronics | 延伸閱讀 #3 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 3｜尺寸代號有兩套、這 |  |
| #industry/electronics | 篩選環節下拉 | tap → 展開清單 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/electronics | 篩選環節選項數 | 清單出現 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜0 格 |  |
| #industry/electronics | 關聯圖環節卡 #1「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 131x23（<32） |  |
| #industry/electronics | 關聯圖環節卡 #2「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 126x30（<32） |  |
| #industry/electronics | 關聯圖環節卡 #3「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 131x23（<32） |  |
| #industry/electronics/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/electronics/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/electronics/overview | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/electronics/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/electronics/overview |  |
| #industry/electronics/dg/mlcc | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/electronics/dg/mlcc | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/electronics/dg/mlcc | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/electronics/dg/mlcc | 環節 chip「被動元件」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/electronics/dg/mlcc |  |
| #industry/electronics/dg/mlcc | 延伸閱讀 #3 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 3｜尺寸代號有兩套、這 |  |
| #industry/electronics/dg/mlcc | 篩選環節下拉 | tap → 展開清單 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/electronics/dg/mlcc | 篩選環節選項數 | 清單出現 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜0 格 |  |
| #industry/electronics/dg/panel | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/electronics/dg/factory_automation | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/electronics/dg/resistor_protect | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/electronics/dg/capacitor | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/electronics/dg/power_inductor | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/electronics/dg/machine_tool | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/software | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/software | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/software | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/software | 整頁 | 腳本例外 | ✗ | 假陽性（腳本；人工逐顆點 10／7／10 顆編號全開）｜'NoneType' object is not subscriptable |  |
| #industry/software/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/software/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/software/overview | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/software/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/software/overview |  |
| #industry/software/dg/cloud_msp | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/software/dg/cloud_msp | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/software/dg/cloud_msp | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/software/dg/cloud_msp | 整頁 | 腳本例外 | ✗ | 假陽性（腳本；人工逐顆點 10／7／10 顆編號全開）｜'NoneType' object is not subscriptable |  |
| #industry/software/dg/saas | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/software/dg/cyber_security | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/software/dg/ecommerce | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/financial | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/financial | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/financial | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/financial | 延伸閱讀 #2 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 2｜為什麼用 PB-R |  |
| #industry/financial | 篩選環節下拉 | tap → 展開清單 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/financial | 篩選環節選項數 | 清單出現 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜0 格 |  |
| #industry/financial | 關聯圖環節卡 #1「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 199x23（<32） |  |
| #industry/financial | 關聯圖環節卡 #2「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 194x28（<32） |  |
| #industry/financial | 關聯圖環節卡 #3「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 199x23（<32） |  |
| #industry/financial/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/financial/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/financial/overview | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/financial/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/financial/overview |  |
| #industry/financial/dg/bank | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/financial/dg/bank | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/financial/dg/bank | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/financial/dg/bank | 環節 chip「銀行金融」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/financial/dg/bank |  |
| #industry/financial/dg/bank | 篩選環節下拉 | tap → 展開清單 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/financial/dg/bank | 篩選環節選項數 | 清單出現 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜0 格 |  |
| #industry/financial/dg/life_fhc | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/financial/dg/securities_fhc | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/traditional | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/traditional | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/traditional | 延伸閱讀 #2 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 2｜製造流程（六格）： |  |
| #industry/traditional/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/traditional/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/traditional/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/traditional/overview |  |
| #industry/traditional/dg/petrochemical | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/traditional/dg/petrochemical | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/traditional/dg/petrochemical | 環節 chip「輕油裂解廠」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/traditional/dg/petrochemical |  |
| #industry/traditional/dg/petrochemical | 延伸閱讀 #2 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 2｜製造流程（六格）： |  |
| #industry/infrastructure | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/infrastructure | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/infrastructure | 延伸閱讀 #2 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 2｜工程統包與安裝：把 |  |
| #industry/infrastructure | 延伸閱讀 #3 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 3｜電力路徑（六格）： |  |
| #industry/infrastructure/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/infrastructure/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/infrastructure/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/infrastructure/overview |  |
| #industry/infrastructure/dg/heavy_electric | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/infrastructure/dg/heavy_electric | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/infrastructure/dg/heavy_electric | 環節 chip「電力路徑」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/infrastructure/dg/heavy_electric |  |
| #industry/infrastructure/dg/heavy_electric | 延伸閱讀 #2 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 2｜工程統包與安裝：把 |  |
| #industry/infrastructure/dg/heavy_electric | 延伸閱讀 #3 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 3｜電力路徑（六格）： |  |
| #industry/industry | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/industry/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/industry/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/industry/overview |  |

### 360 深色

| 頁面 | 元素 | 動作 | 結果 | 問題描述 | 截圖 |
|---|---|---|---|---|---|
| #industry 首頁 | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修｜? 18x18 |  |
| #industry 首頁 | 完整版圖連結 | tap → #heatmap | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#stock/2303 |  |
| #industry/semiconductor | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/semiconductor | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/semiconductor | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/semiconductor | 零件卡鈕「›」 | tap → 畫面改變 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/semiconductor | 延伸閱讀 #2 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 2｜製程迴圈：九站走完 |  |
| #industry/semiconductor | 延伸閱讀 #3 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 3｜節點演進：N5 → |  |
| #industry/semiconductor | 延伸閱讀 #4 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 4｜這張圖上每一段台股 |  |
| #industry/semiconductor | 篩選環節下拉 | tap → 展開清單 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/semiconductor | 篩選環節選項數 | 清單出現 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜0 格 |  |
| #industry/semiconductor | 關聯圖環節卡 #1「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 131x23（<32） |  |
| #industry/semiconductor | 關聯圖環節卡 #2「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 126x28（<32） |  |
| #industry/semiconductor | 關聯圖環節卡 #3「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 131x23（<32） |  |
| #industry/semiconductor/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/semiconductor/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/semiconductor/overview | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/semiconductor/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/semiconductor/overview |  |
| #industry/semiconductor/dg/foundry | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/semiconductor/dg/foundry | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/semiconductor/dg/foundry | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/semiconductor/dg/foundry | 零件卡鈕「›」 | tap → 畫面改變 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/semiconductor/dg/foundry | 環節 chip「晶圓代工」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/semiconductor/dg/foundry |  |
| #industry/semiconductor/dg/foundry | 延伸閱讀 #3 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 3｜節點演進：N5 → |  |
| #industry/semiconductor/dg/foundry | 延伸閱讀 #4 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 4｜這張圖上每一段台股 |  |
| #industry/semiconductor/dg/foundry | 篩選環節下拉 | tap → 展開清單 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/semiconductor/dg/foundry | 篩選環節選項數 | 清單出現 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜0 格 |  |
| #industry/semiconductor/dg/ai_adv_packaging | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/semiconductor/dg/hbm | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/semiconductor/dg/memory_module | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；? 18x18 |  |
| #industry/semiconductor/dg/silicon_wafer | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；? 18x18；產業地圖 5 |  |
| #industry/semiconductor/dg/wide_bandgap | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/ai_server | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/ai_server | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/ai_server | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/ai_server | 零件卡鈕「›」 | tap → 畫面改變 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/ai_server | 關聯圖環節卡 #1「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 131x23（<32） |  |
| #industry/ai_server | 關聯圖環節卡 #2「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 126x28（<32） |  |
| #industry/ai_server | 關聯圖環節卡 #3「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 131x23（<32） |  |
| #industry/ai_server/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/ai_server/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/ai_server/overview | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/ai_server/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/ai_server/overview |  |
| #industry/ai_server/dg/ai_server | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/ai_server/dg/ai_server | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/ai_server/dg/ai_server | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/ai_server/dg/ai_server | 零件卡鈕「›」 | tap → 畫面改變 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/ai_server/dg/ai_server | 環節 chip「AI 伺服器」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/ai_server/dg/ai_server |  |
| #industry/ai_server/dg/ic_substrate | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；? 18x18；產業地圖 5 |  |
| #industry/ai_server/dg/server_psu | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；? 18x18；產業地圖 5 |  |
| #industry/ai_server/dg/pcb_rigid | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/ai_server/dg/liquid_cooling | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；? 18x18 |  |
| #industry/ai_server/dg/air_cooling | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/ai_server/dg/switch_wireless | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；11 20x20；? 18x18；產業地圖 5 |  |
| #industry/ai_server/dg/ai_interconnect | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/siph_cpo | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；? 18x18；產業地圖 5 |  |
| #industry/siph_cpo | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/siph_cpo | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/siph_cpo | 整頁 | 腳本例外 | ✗ | 假陽性（腳本；人工逐顆點 10／7／10 顆編號全開）｜'NoneType' object is not subscriptable |  |
| #industry/siph_cpo/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修（成員表個股／族群連結 18 高 → 可點 36）／編號交剖析圖｜2303 聯電 60x18；2313 華通 60x18；2330 台積電 73x18；2345 智邦 60x18；2360 致茂 60x18；2383 台光電 73x18；2454 聯發科 73x18；2455 全新 60x18；3008 大立光 73x18；3037 欣興 60x18；3081 聯亞 60x18；3 |  |
| #industry/siph_cpo/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/siph_cpo/overview | 「?」說明鈕 #4「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/siph_cpo/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/siph_cpo/overview |  |
| #industry/siph_cpo/dg/siph_pkg | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；? 18x18；產業地圖 5 |  |
| #industry/siph_cpo/dg/siph_pkg | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/siph_cpo/dg/siph_pkg | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/siph_cpo/dg/siph_pkg | 整頁 | 腳本例外 | ✗ | 假陽性（腳本；人工逐顆點 10／7／10 顆編號全開）｜'NoneType' object is not subscriptable |  |
| #industry/siph_cpo/dg/siph_module | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/electronics | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/electronics | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/electronics | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/electronics | 延伸閱讀 #2 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 2｜怎麼做出來的：十道 |  |
| #industry/electronics | 延伸閱讀 #3 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 3｜尺寸代號有兩套、這 |  |
| #industry/electronics | 篩選環節下拉 | tap → 展開清單 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/electronics | 篩選環節選項數 | 清單出現 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜0 格 |  |
| #industry/electronics | 關聯圖環節卡 #1「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 131x23（<32） |  |
| #industry/electronics | 關聯圖環節卡 #2「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 126x30（<32） |  |
| #industry/electronics | 關聯圖環節卡 #3「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 131x23（<32） |  |
| #industry/electronics/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/electronics/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/electronics/overview | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/electronics/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/electronics/overview |  |
| #industry/electronics/dg/mlcc | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/electronics/dg/mlcc | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/electronics/dg/mlcc | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/electronics/dg/mlcc | 環節 chip「被動元件」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/electronics/dg/mlcc |  |
| #industry/electronics/dg/mlcc | 延伸閱讀 #3 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 3｜尺寸代號有兩套、這 |  |
| #industry/electronics/dg/mlcc | 篩選環節下拉 | tap → 展開清單 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/electronics/dg/mlcc | 篩選環節選項數 | 清單出現 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜0 格 |  |
| #industry/electronics/dg/panel | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/electronics/dg/factory_automation | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/electronics/dg/resistor_protect | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/electronics/dg/capacitor | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/electronics/dg/power_inductor | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/electronics/dg/machine_tool | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/software | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/software | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/software | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/software | 整頁 | 腳本例外 | ✗ | 假陽性（腳本；人工逐顆點 10／7／10 顆編號全開）｜'NoneType' object is not subscriptable |  |
| #industry/software/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/software/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/software/overview | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/software/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/software/overview |  |
| #industry/software/dg/cloud_msp | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/software/dg/cloud_msp | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/software/dg/cloud_msp | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/software/dg/cloud_msp | 整頁 | 腳本例外 | ✗ | 假陽性（腳本；人工逐顆點 10／7／10 顆編號全開）｜'NoneType' object is not subscriptable |  |
| #industry/software/dg/saas | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/software/dg/cyber_security | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/software/dg/ecommerce | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/financial | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/financial | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/financial | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/financial | 延伸閱讀 #2 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 2｜為什麼用 PB-R |  |
| #industry/financial | 篩選環節下拉 | tap → 展開清單 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/financial | 篩選環節選項數 | 清單出現 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜0 格 |  |
| #industry/financial | 關聯圖環節卡 #1「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 199x23（<32） |  |
| #industry/financial | 關聯圖環節卡 #2「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 194x28（<32） |  |
| #industry/financial | 關聯圖環節卡 #3「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 199x23（<32） |  |
| #industry/financial/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/financial/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/financial/overview | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/financial/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/financial/overview |  |
| #industry/financial/dg/bank | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/financial/dg/bank | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/financial/dg/bank | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/financial/dg/bank | 環節 chip「銀行金融」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/financial/dg/bank |  |
| #industry/financial/dg/bank | 篩選環節下拉 | tap → 展開清單 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/financial/dg/bank | 篩選環節選項數 | 清單出現 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜0 格 |  |
| #industry/financial/dg/life_fhc | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/financial/dg/securities_fhc | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/traditional | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/traditional | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/traditional | 延伸閱讀 #2 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 2｜製造流程（六格）： |  |
| #industry/traditional/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/traditional/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/traditional/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/traditional/overview |  |
| #industry/traditional/dg/petrochemical | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/traditional/dg/petrochemical | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/traditional/dg/petrochemical | 環節 chip「輕油裂解廠」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/traditional/dg/petrochemical |  |
| #industry/traditional/dg/petrochemical | 延伸閱讀 #2 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 2｜製造流程（六格）： |  |
| #industry/infrastructure | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/infrastructure | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/infrastructure | 延伸閱讀 #2 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 2｜工程統包與安裝：把 |  |
| #industry/infrastructure | 延伸閱讀 #3 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 3｜電力路徑（六格）： |  |
| #industry/infrastructure/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/infrastructure/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/infrastructure/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/infrastructure/overview |  |
| #industry/infrastructure/dg/heavy_electric | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/infrastructure/dg/heavy_electric | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/infrastructure/dg/heavy_electric | 環節 chip「電力路徑」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/infrastructure/dg/heavy_electric |  |
| #industry/infrastructure/dg/heavy_electric | 延伸閱讀 #2 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 2｜工程統包與安裝：把 |  |
| #industry/infrastructure/dg/heavy_electric | 延伸閱讀 #3 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 3｜電力路徑（六格）： |  |
| #industry/industry | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/industry/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/industry/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/industry/overview |  |

### 430 深色

| 頁面 | 元素 | 動作 | 結果 | 問題描述 | 截圖 |
|---|---|---|---|---|---|
| #industry 首頁 | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修｜? 18x18 |  |
| #industry 首頁 | 完整版圖連結 | tap → #heatmap | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#stock/2303 |  |
| #industry/semiconductor | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/semiconductor | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/semiconductor | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/semiconductor | 零件卡鈕「›」 | tap → 畫面改變 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/semiconductor | 延伸閱讀 #2 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 2｜製程迴圈：九站走完 |  |
| #industry/semiconductor | 延伸閱讀 #3 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 3｜節點演進：N5 → |  |
| #industry/semiconductor | 延伸閱讀 #4 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 4｜這張圖上每一段台股 |  |
| #industry/semiconductor | 篩選環節下拉 | tap → 展開清單 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/semiconductor | 篩選環節選項數 | 清單出現 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜0 格 |  |
| #industry/semiconductor | 關聯圖環節卡 #1「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 131x23（<32） |  |
| #industry/semiconductor | 關聯圖環節卡 #2「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 126x28（<32） |  |
| #industry/semiconductor | 關聯圖環節卡 #3「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 131x23（<32） |  |
| #industry/semiconductor/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/semiconductor/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/semiconductor/overview | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/semiconductor/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/semiconductor/overview |  |
| #industry/semiconductor/dg/foundry | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/semiconductor/dg/foundry | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/semiconductor/dg/foundry | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/semiconductor/dg/foundry | 零件卡鈕「›」 | tap → 畫面改變 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/semiconductor/dg/foundry | 環節 chip「晶圓代工」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/semiconductor/dg/foundry |  |
| #industry/semiconductor/dg/foundry | 延伸閱讀 #3 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 3｜節點演進：N5 → |  |
| #industry/semiconductor/dg/foundry | 延伸閱讀 #4 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 4｜這張圖上每一段台股 |  |
| #industry/semiconductor/dg/foundry | 篩選環節下拉 | tap → 展開清單 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/semiconductor/dg/foundry | 篩選環節選項數 | 清單出現 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜0 格 |  |
| #industry/semiconductor/dg/ai_adv_packaging | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/semiconductor/dg/hbm | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/semiconductor/dg/memory_module | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；? 18x18 |  |
| #industry/semiconductor/dg/silicon_wafer | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；? 18x18；產業地圖 5 |  |
| #industry/semiconductor/dg/wide_bandgap | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/ai_server | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/ai_server | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/ai_server | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/ai_server | 零件卡鈕「›」 | tap → 畫面改變 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/ai_server | 關聯圖環節卡 #1「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 131x23（<32） |  |
| #industry/ai_server | 關聯圖環節卡 #2「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 126x28（<32） |  |
| #industry/ai_server | 關聯圖環節卡 #3「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 131x23（<32） |  |
| #industry/ai_server/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/ai_server/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/ai_server/overview | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/ai_server/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/ai_server/overview |  |
| #industry/ai_server/dg/ai_server | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/ai_server/dg/ai_server | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/ai_server/dg/ai_server | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/ai_server/dg/ai_server | 零件卡鈕「›」 | tap → 畫面改變 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/ai_server/dg/ai_server | 環節 chip「AI 伺服器」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/ai_server/dg/ai_server |  |
| #industry/ai_server/dg/ic_substrate | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；? 18x18；產業地圖 5 |  |
| #industry/ai_server/dg/server_psu | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；? 18x18；產業地圖 5 |  |
| #industry/ai_server/dg/pcb_rigid | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/ai_server/dg/liquid_cooling | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；? 18x18 |  |
| #industry/ai_server/dg/air_cooling | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/ai_server/dg/switch_wireless | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；11 20x20；? 18x18；產業地圖 5 |  |
| #industry/ai_server/dg/ai_interconnect | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/siph_cpo | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；? 18x18；產業地圖 5 |  |
| #industry/siph_cpo | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/siph_cpo | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/siph_cpo | 整頁 | 腳本例外 | ✗ | 假陽性（腳本；人工逐顆點 10／7／10 顆編號全開）｜'NoneType' object is not subscriptable |  |
| #industry/siph_cpo/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修（成員表個股／族群連結 18 高 → 可點 36）／編號交剖析圖｜2303 聯電 60x18；2313 華通 60x18；2330 台積電 73x18；2345 智邦 60x18；2360 致茂 60x18；2383 台光電 73x18；2454 聯發科 73x18；2455 全新 60x18；3008 大立光 73x18；3037 欣興 60x18；3081 聯亞 60x18；3 |  |
| #industry/siph_cpo/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/siph_cpo/overview | 「?」說明鈕 #4「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/siph_cpo/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/siph_cpo/overview |  |
| #industry/siph_cpo/dg/siph_pkg | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；? 18x18；產業地圖 5 |  |
| #industry/siph_cpo/dg/siph_pkg | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/siph_cpo/dg/siph_pkg | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/siph_cpo/dg/siph_pkg | 整頁 | 腳本例外 | ✗ | 假陽性（腳本；人工逐顆點 10／7／10 顆編號全開）｜'NoneType' object is not subscriptable |  |
| #industry/siph_cpo/dg/siph_module | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/electronics | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/electronics | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/electronics | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/electronics | 延伸閱讀 #2 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 2｜怎麼做出來的：十道 |  |
| #industry/electronics | 延伸閱讀 #3 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 3｜尺寸代號有兩套、這 |  |
| #industry/electronics | 篩選環節下拉 | tap → 展開清單 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/electronics | 篩選環節選項數 | 清單出現 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜0 格 |  |
| #industry/electronics | 關聯圖環節卡 #1「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 131x23（<32） |  |
| #industry/electronics | 關聯圖環節卡 #2「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 126x30（<32） |  |
| #industry/electronics | 關聯圖環節卡 #3「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 131x23（<32） |  |
| #industry/electronics/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/electronics/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/electronics/overview | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/electronics/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/electronics/overview |  |
| #industry/electronics/dg/mlcc | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/electronics/dg/mlcc | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/electronics/dg/mlcc | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/electronics/dg/mlcc | 環節 chip「被動元件」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/electronics/dg/mlcc |  |
| #industry/electronics/dg/mlcc | 延伸閱讀 #3 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 3｜尺寸代號有兩套、這 |  |
| #industry/electronics/dg/mlcc | 篩選環節下拉 | tap → 展開清單 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/electronics/dg/mlcc | 篩選環節選項數 | 清單出現 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜0 格 |  |
| #industry/electronics/dg/panel | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/electronics/dg/factory_automation | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/electronics/dg/resistor_protect | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/electronics/dg/capacitor | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/electronics/dg/power_inductor | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/electronics/dg/machine_tool | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/software | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/software | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/software | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/software | 整頁 | 腳本例外 | ✗ | 假陽性（腳本；人工逐顆點 10／7／10 顆編號全開）｜'NoneType' object is not subscriptable |  |
| #industry/software/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/software/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/software/overview | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/software/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/software/overview |  |
| #industry/software/dg/cloud_msp | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/software/dg/cloud_msp | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/software/dg/cloud_msp | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/software/dg/cloud_msp | 整頁 | 腳本例外 | ✗ | 假陽性（腳本；人工逐顆點 10／7／10 顆編號全開）｜'NoneType' object is not subscriptable |  |
| #industry/software/dg/saas | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/software/dg/cyber_security | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/software/dg/ecommerce | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/financial | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/financial | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/financial | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/financial | 延伸閱讀 #2 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 2｜為什麼用 PB-R |  |
| #industry/financial | 篩選環節下拉 | tap → 展開清單 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/financial | 篩選環節選項數 | 清單出現 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜0 格 |  |
| #industry/financial | 關聯圖環節卡 #1「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 199x23（<32） |  |
| #industry/financial | 關聯圖環節卡 #2「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 194x28（<32） |  |
| #industry/financial | 關聯圖環節卡 #3「」 | touchscreen.tap → 展開公司／反亮 | ✗ | 已修（環節標題 19→32；#1/#3 為只裝飾的外框 rect，無點擊功能）｜觸控區 199x23（<32） |  |
| #industry/financial/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/financial/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/financial/overview | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/financial/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/financial/overview |  |
| #industry/financial/dg/bank | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/financial/dg/bank | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/financial/dg/bank | 「?」說明鈕 #3「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x24（<32） |  |
| #industry/financial/dg/bank | 環節 chip「銀行金融」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/financial/dg/bank |  |
| #industry/financial/dg/bank | 篩選環節下拉 | tap → 展開清單 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜ |  |
| #industry/financial/dg/bank | 篩選環節選項數 | 清單出現 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜0 格 |  |
| #industry/financial/dg/life_fhc | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/financial/dg/securities_fhc | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人；「?」鈕外擴 → 已修；麵包屑 → 已修｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；? 18x18；產業地圖 56x22 |  |
| #industry/traditional | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/traditional | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/traditional | 延伸閱讀 #2 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 2｜製造流程（六格）： |  |
| #industry/traditional/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/traditional/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/traditional/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/traditional/overview |  |
| #industry/traditional/dg/petrochemical | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/traditional/dg/petrochemical | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/traditional/dg/petrochemical | 環節 chip「輕油裂解廠」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/traditional/dg/petrochemical |  |
| #industry/traditional/dg/petrochemical | 延伸閱讀 #2 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 2｜製造流程（六格）： |  |
| #industry/infrastructure | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/infrastructure | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/infrastructure | 延伸閱讀 #2 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 2｜工程統包與安裝：把 |  |
| #industry/infrastructure | 延伸閱讀 #3 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 3｜電力路徑（六格）： |  |
| #industry/infrastructure/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/infrastructure/overview | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/infrastructure/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/infrastructure/overview |  |
| #industry/infrastructure/dg/heavy_electric | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：剖析圖編號 20×20 → 交給剖析圖負責人｜01 20x20；02 20x20；03 20x20；04 20x20；05 20x20；06 20x20；07 20x20；08 20x20；09 20x20；10 20x20；11 20x20；12 20x20 |  |
| #industry/infrastructure/dg/heavy_electric | 「?」說明鈕 #1「?」 | touchscreen.tap → 彈出說明 | ✗ | 已修｜觸控區 40x28（<32） |  |
| #industry/infrastructure/dg/heavy_electric | 環節 chip「電力路徑」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/infrastructure/dg/heavy_electric |  |
| #industry/infrastructure/dg/heavy_electric | 延伸閱讀 #2 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 2｜工程統包與安裝：把 |  |
| #industry/infrastructure/dg/heavy_electric | 延伸閱讀 #3 | tap → 展開 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜＋ 延伸 3｜電力路徑（六格）： |  |
| #industry/industry | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/industry/overview | 整頁 | 可點元素 <32px | ✗ | 部分已修／編號交剖析圖：「?」鈕外擴 → 已修；麵包屑 → 已修｜? 18x18；產業地圖 56x22 |  |
| #industry/industry/overview | 環節 chip「族群總覽」 | tap → 換到那一頁 | ✗ | 假陽性（人工複驗該操作正常，且新驗收段通過）｜#industry/industry/overview |  |
