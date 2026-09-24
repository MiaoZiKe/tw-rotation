# 功能模組清單與積木化規格（`docs/feature_modules.md`）

> 撰寫：CEO 分派｜日期：2026-09-24（台北時間）｜對象：Andy
>
> Andy 的原話：「**CEO請將功能模組化，這樣方便變成像是積木一樣堆疊在介面上，模組後給我清單**」。
>
> **這份文件只產出清單與規格，沒有動任何一行 `site/**`、`pipeline/**`、`scripts/**`、`tests/**` 的程式碼，
> 沒有 commit、沒有 push。** 唯一新增的檔案就是這一份。
>
> 為什麼這一棒只寫清單不重構：① `site/app.js`／`industry.js`／`index.html` 現在有另一批手機版回歸在修，
> 同時大改會互相覆蓋；② 「積木化」要先有正確的切法才有意義，切錯了重構等於白做。

---

# ★ 模組總表（先看這一張，細節在 §3）

| # | id | 中文名 | 回答哪一問 | 建議層級 |
|---|---|---|---|---|
| 1 | `flow.clock` | 輪動時鐘 | ① 錢往哪跑 | 免費 |
| 2 | `flow.rank` | 資金流向排行 | ① 錢往哪跑 | 免費 |
| 3 | `flow.sankey` | 資金去向分流圖 | ① 錢往哪跑 | 免費 |
| 4 | `flow.heat` | 資金熱力圖 | ① 錢往哪跑 | 免費 |
| 5 | `flow.inst` | 族群 × 法人 | ① 錢往哪跑 | 免費 |
| 6 | `flow.conc` | 資金集中度 | ① 錢往哪跑 | 免費 |
| 7 | `market.treemap` | 全市場熱力圖 | ① 錢往哪跑 | 免費 |
| 8 | `theme.heat` | 題材熱度 | ① 錢往哪跑 | 免費 |
| 9 | `index.board` | 大盤三張圖 | ② 貴不貴 | 免費 |
| 10 | `market.kpi` | 大盤 KPI 六格 | ② 貴不貴 | 免費 |
| 11 | `market.breadth` | 市場寬度 | ② 貴不貴 | 免費 |
| 12 | `market.streak` | 法人連續買超 | ② 貴不貴 | 免費 |
| 13 | `market.detail` | 市場明細名單 | ② 貴不貴 | 免費 |
| 14 | `season.month` | 季節性（族群 × 月份） | ② 貴不貴 | 免費 |
| 15 | `stock.fund` | 個股基本面與財報 | ② 貴不貴 | 免費 |
| 16 | `cand.board` | 今日候選 | ③ 何時進場 | **只准免費**🔴 |
| 17 | `stock.kchart` | 個股 K 線（含即時分 K） | ③ 何時進場 | 免費 |
| 18 | `stock.mtf` | 多週期 SMC 判讀 | ③ 何時進場 | **只准免費**🔴 |
| 19 | `stock.signal` | 技術面訊號卡 | ③ 何時進場 | **只准免費**🔴 |
| 20 | `events.feed` | 今日事件 | ④ 別進的理由 | 免費 |
| 21 | `stock.news` | 個股新聞與公告 | ④ 別進的理由 | 免費 |
| 22 | `broker.views` | 券商觀點 | ④ 別進的理由 | **只准免費**🔴🔴 |
| 23 | `chain.map` | 產業地圖（八條鏈） | 知識／導覽 | 免費 |
| 24 | `chain.overview` | 族群總覽（長條＋圓餅） | ① 錢往哪跑 | 免費 |
| 25 | `chain.diagram` | 產業鏈剖析圖（2D＋3D） | 知識 | 免費看／**399 匯出**／**799 商用** |
| 26 | `chain.segments` | 環節詳情與分層關聯圖 | 知識 | 免費看／**399 反查** |
| 27 | `theme.diagram` | 題材剖析圖（18 張） | 知識 | 免費看／**399 匯出**／**799 商用** |

> 另有 **11 塊底層共用元件**（搜尋、盤中即時層、主題、拉 Bar、放大視窗、資料狀態、手機動線…），
> 它們不回答四問、也不單獨賣，列在 **§3.6**。
> 🔴 ＝ 依 `docs/compliance_and_tiers.md` 的四維度判準屬「推介建議」類，**不准放進付費層**。

---

# §0 這份文件的邊界（先講清楚什麼是量的、什麼是我判斷的）

- **〔事實〕** 標記的東西，都是我在這個容器裡用 `grep` / `wc` / 讀檔實際量到的，行號與檔名寫在旁邊。
- **〔判斷〕** 標記的東西，是我的切法主張。**切法沒有唯一解**，Andy 可以推翻，理由寫在 §6。
- 高度數字分兩種：**帶 `*` 的是實測**（來源 `docs/mobile_ia.md` 的 390×844 稽核表，那是 2026-09-24 改版**前**量的），
  **不帶 `*` 的是從 `site/index.html` 的 CSS `min-height` 推算**，不是實測值。
- 我**沒有**打開過線上網站（這個容器的出口被擋，`WebFetch`／`curl` 回 `EGRESS_BLOCKED`），
  所以這份文件全部是讀原始碼讀出來的，不是看畫面看出來的。
- 層級（免費／399／799）**一律引用 `docs/compliance_and_tiers.md` §2-2 的既有分層**，我沒有另訂一套。
  那份文件沒有講到的模組，我依同一套原則推，並在 §3 逐項標「這一條是我推的」。

---

# §1 現況盤點：現在到底有哪些功能，各自長在哪

## 1.1 程式碼規模（〔事實〕，`wc -l`，2026-09-24）

| 檔案 | 行數 | 角色 |
|---|---:|---|
| `site/three3d.js` | 8,104 | 剖析圖的真 3D 場景（Three.js），20 個 `SCENES` |
| `site/app.js` | 7,644 | **全站主程式**：路由、總覽、資金流向、題材、季節性、市場明細、事件、搜尋、手機動線 |
| `site/industry.js` | 4,203 | 產業地圖 → 產業鏈 → 個股頁（含 K 線設定、七個分頁） |
| `site/index.html` | 3,207 | 版面骨架 ＋ **2,736 行 inline CSS**（全站唯一一份樣式表） |
| `site/market3.js` | 1,854 | 大盤三張圖（加權／櫃買／台指期，含夜盤與 SSE 串流） |
| `site/diagrams.js` | 1,647 | 剖析圖的共用工具箱 `window.DG` ＋ 檔位登錄表 |
| `site/themes3d.js` | 1,531 | 題材剖析圖（18 張，`window.ThemeDiagrams`） |
| `site/chart.js` | 1,159 | K 線繪製與指標 `KInd`（`window.Chart`） |
| `site/live.js` | 636 | 盤中即時層（只更新 `[data-live]` 標記過的格子） |
| `site/livek.js` | 349 | 個股當日即時分 K（5 秒 K） |
| `site/tasks.js` | 103 | 任務板（頂層分頁入口已移除，路由留著） |
| `site/dg/*.js` | 27 個檔 | 一張剖析圖一個檔 |

**合計前端約 30,437 行。**

## 1.2 路由與 `.view` 區塊（〔事實〕）

`site/app.js:797` 的 `VIEWS` 與 `site/index.html` 的 `<section class="view">` 一對一：

| hash | `.view` id | 頂層分頁 | 主要 render 函式 |
|---|---|---|---|
| `#overview` | `v-overview`（`index.html:2868`） | 總覽 | `app.js:2059 renderOverview` |
| `#flow` | `v-flow`（`:2938`） | 資金流向 | `app.js:4280 renderFlow` |
| `#industry`／`#industry/<chain>`／`#stock/<code>` | `v-industry`（`:3072`） | 產業地圖 | `industry.js:33 route` |
| `#heatmap` | `v-heatmap`（`:3067`） | 熱力圖 | `industry.js:4169 routeHeat` |
| `#themes[/id]` | `v-themes`（`:3080`） | 題材 | `app.js:6931 renderThemes` |
| `#market[/sub]` | `v-market`（`:2927`） | 市場明細 | `app.js:1580 renderMarket` |
| `#season` | `v-season`（`:3101`） | 季節性 | `app.js:7144 renderSeason` |
| `#delivery` | `v-delivery`（`:3098`） | 交付清單 | `app.js:7088 renderDelivery` |
| `#tasks` | `v-tasks`（`:3093`） | **入口已移除**（`index.html:2799` 註解），網址仍可直接開 | `app.js:7036 renderTasks` |

**〔事實〕** `#industry`、`#industry/<chain>`、`#stock/<code>` **共用同一個 `.view`**（`v-industry`），
由 `industry.js:89 show(map, chain, stock)` 三選一顯示 `#indMap`／`#indChain`／`#stockPage`。
這是後面 §4 講「版面寫死在 HTML」時最明顯的一個案例。

## 1.3 `pipeline/compute/` → JSON → 畫面 的完整對照（〔事實〕）

`pipeline/build_payload.py` 的 `_write()`（`:92`）共寫出 **31 份 JSON**（`site/data/`，不進版控）。

| JSON | 產出處（`build_payload.py` 行） | 計算模組 | 前端讀者 | 落在哪一塊積木 |
|---|---|---|---|---|
| `groups_today` | `:187` | `compute/flow.py` | `app.js` | `market.kpi`／`market.detail` |
| `rotation` | `:188` | `flow.rotation_radar` | `app.js` | `flow.clock` |
| `flow_v3` | `:387` | `compute/rrg.py` | `app.js` | `flow.clock`／`flow.rank` |
| `rrg_members` | `:411` | `rrg.member_rrg` | `app.js` | `flow.clock`（展開成分股） |
| `sankey_daily` | `:405` | `rrg.sankey_daily` | `app.js` | `flow.sankey`／總覽「昨日資金去向」 |
| `concentration` | `:191` | `flow.concentration` | `app.js` | `flow.conc` |
| `concentration_members` | `:200` | `compute/flow.py` | `app.js` | `flow.conc`（逐日鑽取） |
| `market_heat` | `:362` | `build_payload.heat` | `app.js` | `flow.heat`／`market.kpi`／**`market.breadth`**（`heat.breadth`） |
| `ma_breadth` | `:194` | `flow.ma_breadth_history` | `app.js:1652 drawMaTrend`（**只有市場明細的 `ma` 子頁讀它**） | `market.detail` |
| `inst_streak`／`trust_streak` | `:213`／`:214` | `compute/flow.py` | `app.js` | `market.streak` |
| `index_ohlc` | `:380` | `build_payload` | **`market3.js`** | `index.board` |
| `candidates` | `:358` | `compute/technical.py` ＋ `scoring.py` | `app.js` | `cand.board` 🔴 |
| `groups_detail` | `:360` | `compute/flow.py` | `app.js`＋`industry.js` | `flow.inst`／`chain.overview` |
| `industry_map` | `:428` | `build_payload.industry_map` | `app.js`＋`industry.js` | `chain.map`／`market.treemap` |
| `supply_chain` | `:506` | `groups/loader.py`（**唯一人工維護**） | `app.js`＋`industry.js`＋`diagrams.js` | `chain.segments`／`chain.diagram` |
| `themes` | `:423` | `compute/themes.py` | `app.js`＋`industry.js` | `theme.heat`／`theme.diagram` |
| `stocks` | `:1076` | `build_payload` | `app.js`＋`industry.js`＋`live.js` | `core.search`／`core.live` |
| `stock/<code>.json` | `:939`／`:1053` | `compute/stockpage.py`＋`mtf.py` | `industry.js` | `stock.*` 全家 |
| `hist/<code>/p<N>.json` | `:956` | `build_payload` | `industry.js`（K 線分頁載入） | `stock.kchart` |
| `fundamental` | `:316` | `compute/fundamental.py` | **只有 `industry.js`** | `stock.fund` |
| `seasonality_v3` | `:262` | `compute/season.py` | `app.js` | `season.month` |
| `news` | `:491` | `sources/news.py` | `app.js`＋`industry.js` | `events.feed`／`stock.news` |
| `broker_views` | `:336` | `sources/news.py` | `app.js`＋`industry.js` | `broker.views` 🔴🔴 |
| `meta` | `:518` | `build_payload.meta_payload` | `app.js`＋`live.js` | `core.freshness` |
| `tasks` | `:514` | `obsidian/tasks.yaml` | `app.js`＋`tasks.js` | `meta.tasks` |
| `delivery` | `:517` | `pipeline/delivery_log.py`（來源 `docs/delivery_log.md`） | `app.js` | `meta.delivery` |

### ⚠ 孤兒 JSON：產出了，但**前端一個讀者都沒有**（〔事實〕，全站 `grep` 驗證）

| JSON | 產出處 | 為什麼沒人讀 |
|---|---|---|
| `group_valuation.json` | `:324` | 2026-09-23 Andy 指定「估值篩選拿掉」，`renderVal()`／`renderGval()` 一起移除 |
| `seasonality.json` | `:259` | 被 `seasonality_v3.json` 取代，舊鍵留著沒清 |
| `relative_strength.json` | `:205` | 找不到任何 `load('relative_strength')` |
| `intl.json` | `:500` | 找不到任何 `load('intl')`（`seasonality_v3` 內部用 `intl_all`，但那是 Python 端） |

> **〔判斷〕這四份就是「積木切不乾淨」的第一個證據**：拿掉一塊積木時，
> **只拿掉了畫面，沒有拿掉它的資料管線**。每天的 Actions 仍在算它們、寫它們。
> 積木化之後這件事應該是自動的：一塊積木被關掉，它宣告的輸入就不必再產。

## 1.4 `docs/delivery_log.md` 的 43 筆交付（〔事實〕）

43 筆逐字需求分佈在 6 個區段（第 103／104 次部署、2026-09-23 三次、以及「還沒結束的」）。
**我逐筆看過的結論**：43 筆裡有 **31 筆是「把某一塊挪位置／拿掉／換版面」**，
只有 12 筆是「做一個新東西」。

> **〔判斷〕這就是 Andy 要積木化的實證理由。**
> 現在「把一張卡從總覽搬到資金流向頁」是**改 HTML ＋ 改 render 函式 ＋ 改手機分段表 ＋ 改驗收段落名**四處；
> 積木化之後應該是**改一份版面設定**。43 筆需求裡 31 筆屬於這一類，
> 省下來的不是一點點。

---

# §2 切法的原則（先寫清楚，再套用）

## 2.1 三條硬原則（Andy 的建議判準，我全部採用，理由寫在後面）

### 原則一：**一塊積木 ＝ 一個問題的答案**，不是「一個圖表」

同一個問題如果要「圖 ＋ 數字」才答得完整，那它們是同一塊。

- **正例**：`flow.conc`（資金集中度）＝ 一張六條均線的折線圖 ＋ 逐日鑽取面板 ＋ 前 5／前 10 切換。
  三個 DOM 元素、一塊積木，因為它們回答的是同一句話：「錢是集中在少數族群還是散開了」。
- **反例（現在的樣子）**：總覽的 `#ovRotCard` **一張卡回答兩個問題** ——
  上半是輪動時鐘（誰在轉強），下半是昨日資金去向分流圖（昨天錢分給了誰）。
  `docs/mobile_ia.md` 量到它 1,059px，而且手機那一版**已經被迫把它拆成兩段**
  （`app.js` 的 `MIA_PAGER.overview` 裡 `#ovRotCard` 出現兩次，各帶不同的 `sel`）。
  **手機端已經先一步證明了正確的切法是兩塊。**

### 原則二：**積木之間只准透過資料溝通，不准直接呼叫對方的內部函式**

這是「能不能單獨關掉」的前提。具體成三條可檢查的規則：

1. 一塊積木只能讀**自己宣告的輸入**（JSON 檔 ＋ 欄位），不能讀別塊積木的區域變數。
2. 一塊積木要影響別塊（例如「點族群 → 排行也跟著篩」），只能**發事件／改共用狀態**，
   不能 `renderRankFlow()` 直接叫過去。
3. 共用的東西（篩選、拉 Bar、放大視窗、主題）是**獨立的底層元件**（§3.6），不屬於任何一塊積木。

### 原則三：**能不能單獨關閉是硬判準**

關掉之後其他東西還能用，才算切乾淨。驗收方式很具體：
**把那塊積木的 render 呼叫註解掉，整站要沒有 console error、其他積木畫面不變。**

## 2.2 我加的第四條原則（〔判斷〕，Andy 的清單裡沒有，但這一批必須有）

### 原則四：**一塊積木 ＝ 一個可以單獨計價、單獨標法遵的最小單位**

理由：Andy 要積木化的**目的**是 399／799 分層與 App 第一版取捨（見 `docs/compliance_and_tiers.md`、
`docs/mobile_release_plan.md`）。如果切出來的積木裡面**同時包含 🟢 產業知識與 🔴 個股推介**，
那這塊積木在分層表上就無法放置 —— 放進付費層違法，放進免費層又浪費。

**這一條實際改變了兩個切法**：

1. **個股頁沒有切成「一塊積木」，切成五塊**（`stock.fund` 🟡／`stock.kchart` 🟡／
   `stock.mtf` 🔴／`stock.signal` 🔴／`stock.news` 🟡），因為它們的法遵顏色不一樣。
2. **`broker.views` 從個股頁的「新聞分頁」裡拉出來獨立成一塊**，
   因為 `docs/compliance_and_tiers.md` 把它判定為 🔴🔴（士林地院 107 金訴 2），
   而它現在**混在 `tabNews` 裡面**（`industry.js:4140`）—— 混著就不可能單獨處理。

## 2.3 我**沒有**採用的切法（以及為什麼）

| 曾考慮的切法 | 不採用的理由 |
|---|---|
| 依**檔案**切（app.js 一塊、industry.js 一塊） | 檔案邊界是歷史造成的，不是功能邊界。`app.js` 一支就橫跨四問全部 |
| 依**路由**切（一頁一塊） | 太粗。總覽一頁就有 8 塊積木，而 Andy 要的是「搬得動」 |
| 依**圖表**切（一個 ECharts 實例一塊） | 太細，而且會把「圖 ＋ 它的數字」拆開 —— 那正是 `mobile_ia.md` 量到 1,087px 的那個病 |
| 依**資料表**切（一份 JSON 一塊） | `supply_chain.json` 一份餵四塊積木；`stock/<code>.json` 一份餵五塊。對不起來 |

---

# §3 模組規格：每一塊積木的定義

**欄位說明**
- **問題**：對到四問（① 錢往哪跑 ② 貴不貴 ③ 何時進場 ④ 別進的理由）或「知識」「工具」。
- **尺寸**：`1440 / 390` 兩個寬度各佔多高。`*` ＝ `docs/mobile_ia.md` 的實測值，其餘是 CSS `min-height` 推算。
- **相依**：需不需要別塊積木或底層元件先存在。
- **可否單獨關閉**：關掉它會不會讓別的東西壞掉。
- **法遵**：依 `docs/compliance_and_tiers.md` §1-4 的四維度判準（標的／時態／語氣／可執行性）。
  🟢 低／🟡 中低／🟠 中高／🔴 高。
- **層級**：`compliance_and_tiers.md` §2-2 有寫的直接引用；沒寫的我依同一套原則推，標「**〔推〕**」。

## 3.1 ① 錢往哪個族群跑（M1 資金面）

### 1. `flow.clock`　輪動時鐘

| 欄位 | 內容 |
|---|---|
| **問題** | ① 哪些族群相對大盤在轉強，它們跑到強弱循環的哪一段 |
| **程式** | `app.js:2927 renderRotClock`、`:2337 rotStageAll`、`:2367 rotQuadChips`、`:2430 renderStagePanel`、`:5613 highlightClock`、`:4747 openRotZoom` |
| **輸入** | `flow_v3.json`（`rrg.points[]`：`group`／`rs`／`mom`／`stage`／`trail`）、`rotation.json`（前 25 名）、`rrg_members.json`（展開成分股） |
| **輸出** | 四象限散點圖 ＋ 軌跡線 ＋ 四顆可點的象限標籤 ＋ 展開面板（該段有哪些族群、強弱占比） |
| **尺寸** | 1440：440px（`#rotClock min-height:440`）／390：360px（總覽 compact 版 `#rotClockMini`）。主圖位置實測 `#flow` 489–929`*` |
| **相依** | `core.filter`（族群篩選）、`core.rangebar`（雙把手區間桿）、`core.zoom`（放大視窗）、`core.live`（盤中即時 RRG `rlv*`，`app.js:2509 RLV`） |
| **可否單獨關閉** | ⚠ **不行（現況）**。它和 `flow.rank` 合併在同一張卡 `#flowRotCard`，共用 `#flowRotFilter`／`#rotBack`。關掉時鐘會讓排行失去篩選器 |
| **法遵** | 🟡 中低 —— 族群層級，不點名個股。⚠ 但展開面板會列成分股 |
| **層級** | 免費（`compliance_and_tiers.md` §2-2 免費層第 1 列） |

### 2. `flow.rank`　資金流向排行

| 欄位 | 內容 |
|---|---|
| **問題** | ① 這一段時間誰把錢吸走了（成交值／法人淨額的族群排名） |
| **程式** | `app.js:4606 renderRankFlow`、`:4597 textW`、`:5518 renderDrillPanel` |
| **輸入** | `groups_detail.json`、`flow_v3.json` |
| **輸出** | 橫向長條排行 ＋ 點一條展開該族群成分股面板（`#rankPanel`） |
| **尺寸** | 1440：420px（`.chart.tall`）／390：實測 1019–1439`*`（420px） |
| **相依** | 同 `flow.clock`（共用篩選與區間桿） |
| **可否單獨關閉** | ⚠ **不行（現況）**，同上 |
| **法遵** | 🟡 中低 |
| **層級** | 免費 |

### 3. `flow.sankey`　資金去向分流圖

| 欄位 | 內容 |
|---|---|
| **問題** | ① 錢從大盤分到哪幾條產業鏈、鏈裡又分給哪幾個族群 |
| **程式** | `app.js:6106 renderSankey`、`:5720 startSankeyFlow`（小圓點動畫）、`:5979 sklFetch`（即時）、`:5451 renderDrillChainPanel` |
| **輸入** | `sankey_daily.json`（`dates`／`groups`／`leaves`），即時模式另打 `mis.twse.com.tw` |
| **輸出** | 桑基圖（線粗＝流量）＋ 流動小圓點 ＋ 點族群展開個股成交值排序面板 |
| **尺寸** | 1440：420px（`.chart.tall`）／390：實測 1733–2429`*`（696px） |
| **相依** | `core.rangebar`（看哪一天／播放）、`core.live` |
| **可否單獨關閉** | ✅ 可以。它自己一張卡 `#flowSankeyCard`，沒有別人讀它的狀態 |
| **法遵** | 🟡 中低（族群層級） |
| **層級** | 免費 |
| **備註** | **同一份資料在總覽也畫一次**（`#ovFlow`／`app.js:3593 renderOvFlow`，簡化版無動畫）。積木化之後這應該是**同一塊積木的兩種尺寸**，不是兩份程式碼 |

### 4. `flow.heat`　資金熱力圖

| 欄位 | 內容 |
|---|---|
| **問題** | ① 哪些族群現在佔掉最多成交值，而且是在流入還是流出 |
| **程式** | `app.js:2223 renderHeat`、`:2183 heatOption`、`:2211 heatChips`、`:2166 heatPanel` |
| **輸入** | `market_heat.json`（方塊＝族群成交值佔比；顏色＝5 日 vs 20 日佔比差） |
| **輸出** | Treemap ＋ 產業鏈晶片列 ＋ 點方塊展開面板 |
| **尺寸** | 1440：卡片撐滿（`.card.fillchart`）／390：實測 1292–1712`*`（420px） |
| **相依** | `core.zoom`（`#heatZoom`）、`core.howto` |
| **可否單獨關閉** | ✅ 可以 |
| **法遵** | 🟡 中低 |
| **層級** | 免費 |

### 5. `flow.inst`　族群 × 法人

| 欄位 | 內容 |
|---|---|
| **問題** | ① 三大法人的錢進了哪些族群（淨買超張數） |
| **程式** | `app.js:6738 renderInstPeriod` |
| **輸入** | `groups_detail.json` |
| **輸出** | 分組長條圖（外資／投信／自營）＋ 天數拉 Bar ＋ 截止日拉 Bar |
| **尺寸** | 1440：420px／390：420px |
| **相依** | `core.rangebar` ×2 |
| **可否單獨關閉** | ✅ 可以 |
| **法遵** | 🟡 中低 |
| **層級** | 免費 |

### 6. `flow.conc`　資金集中度

| 欄位 | 內容 |
|---|---|
| **問題** | ① 錢是集中在少數幾個族群，還是散開了（前 5／前 10 大佔比與其均線） |
| **程式** | `app.js:6821 renderConc`、`:6802 concMaSet`、`:6889 concDay` |
| **輸入** | `concentration.json`（近 400 個交易日）、`concentration_members.json`（逐日鑽取） |
| **輸出** | 折線圖 ＋ 六條均線開關 ＋ 前 5／前 10 切換 ＋ 點某一天展開當天前幾大族群 |
| **尺寸** | 1440：420px／390：420px |
| **相依** | `core.howto` |
| **可否單獨關閉** | ✅ 可以。⚠ 但總覽 KPI 的「前五族群佔比」會 drill 到 `#flow>conc`（`app.js:1513 wireKpiDrill`）—— 關掉會產生死連結 |
| **法遵** | 🟡 中低 |
| **層級** | 免費 |

### 7. `market.treemap`　全市場熱力圖

| 欄位 | 內容 |
|---|---|
| **問題** | ① 整個台股一次看，錢在哪一塊 |
| **程式** | `industry.js:117 renderHeat`、`:4169 routeHeat` |
| **輸入** | `industry_map.json` |
| **輸出** | 全市場 treemap（`#indTree`） |
| **尺寸** | 1440：560px／390：實測整頁 1009`*`，圖 282–842（560px） |
| **相依** | 無（獨立頂層分頁 `#heatmap`） |
| **可否單獨關閉** | ✅ 可以 —— **它是全站最乾淨的一塊**（自己一個 view、自己一個 render、只吃一份 JSON） |
| **法遵** | 🟡 中低 |
| **層級** | 免費 |

### 8. `theme.heat`　題材熱度

| 欄位 | 內容 |
|---|---|
| **問題** | ① 哪些題材在吸金（熱度＝資金佔比變化 ＋ 法人 ＋ 新聞） |
| **程式** | `app.js:6931 renderThemes`、`:3694 renderThemeStrip`（總覽的簡版） |
| **輸入** | `themes.json`（`themes[]` ＋ `series`） |
| **輸出** | 題材 treemap ＋ 點一格展開成員面板；總覽上是一條橫向題材條 |
| **尺寸** | 1440：460px（`#themeMap min-height:460`）／390：實測 282–742`*` |
| **相依** | `core.zoom` |
| **可否單獨關閉** | ⚠ 可以，但 `theme.diagram` 要靠它選到的題材 id |
| **法遵** | 🟡 中低（題材層級，成員不拆分） |
| **層級** | 免費 |

### 24. `chain.overview`　族群總覽（長條＋圓餅）

| 欄位 | 內容 |
|---|---|
| **問題** | ① 這一條產業鏈裡，哪個族群在漲、哪個族群佔掉最多成交值 |
| **程式** | `industry.js:221 renderGroupPanel`（含 `liveTick`／`onPick`／`paintFocus`） |
| **輸入** | `industry_map.json`、`groups_detail.json`，盤中另打 `mis` 即時 |
| **輸出** | 族群漲跌幅長條（`#gpBar`）＋ 成交值占比甜甜圈（`#gpPie`）＋ 點長條鑽進該族群個股 |
| **尺寸** | 1440：兩張並排各 360px（`.gpgrid .chart min-height:360`）／390：各 320px，改成左右滑 |
| **相依** | `core.live` |
| **可否單獨關閉** | ⚠ **不行**。它是 `#industry/<chain>/overview` 的預設分頁（2026-09-23 Andy 指定），關掉整條鏈就沒有預設畫面 |
| **法遵** | 🟡 中低（鑽取後會列個股，但只有代號／名稱／漲跌幅） |
| **層級** | 免費 |

## 3.2 ② 那個族群現在貴不貴（M2 基本面）

### 9. `index.board`　大盤三張圖

| 欄位 | 內容 |
|---|---|
| **問題** | ② 加權／櫃買／台指期今天怎麼走（含夜盤） |
| **程式** | `market3.js`（整支）：`:213 schedule`、`:410 openFutStream`、`:780 nightSeries` |
| **輸入** | `index_ohlc.json` ＋ `mis` 即時報價 ＋ 期交所夜盤（走 `workers/quote-proxy`） |
| **輸出** | 三張日內走勢圖 ＋ 每張卡內的數字列（`.m3-nums`） |
| **尺寸** | 1440：實測 297–557`*`（260px）／390：同上，改成左右滑一次一張 |
| **相依** | `core.live`、`workers/quote-proxy`（CORS 代理） |
| **可否單獨關閉** | ✅ 可以（`#m3` 一個容器、一支獨立檔案）。**它是全站第二乾淨的一塊** |
| **法遵** | 🟢 低（指數層級的公開行情） |
| **層級** | 免費。⚠ **不准拿即時性去分層**（`compliance_and_tiers.md` §2-1：`mis` 的商用授權未確認） |

### 10. `market.kpi`　大盤 KPI 六格

| 欄位 | 內容 |
|---|---|
| **問題** | ② 今天大盤的體質（〔事實〕六格依序是：加權指數／成交值／漲跌家數／站上 MA20／前五族群佔比／今日候選，`app.js:2073–2085`） |
| **程式** | `app.js:2059 renderOverview` 裡的 `#hero` 段 ＋ `:1513 wireKpiDrill` |
| **輸入** | **只有 `market_heat.json` 一份**（〔事實〕`app.js:2071`：`const b = heat.breadth`，站上 MA20 與候選 A／B 檔數都在 `heat.breadth` 裡，不是另外去讀 `ma_breadth.json`／`candidates.json`）；加權與漲跌幅帶 `data-live` 走即時層 |
| **輸出** | 六格數字卡。**六格裡有四格可點** → drill 到市場明細（`updown`／`ma`／`cand`）或資金流向的集中度（`#flow>conc`）|
| **尺寸** | 1440：實測 181–289`*`（108px）／390：同 |
| **相依** | `market.detail`（drill 目的地）、`flow.conc`（drill 目的地） |
| **可否單獨關閉** | ⚠ 可以，但關掉會少掉四條進入 `market.detail` 的入口 |
| **法遵** | 🟢 低 |
| **層級** | 免費 |

### 11. `market.breadth`　市場寬度

| 欄位 | 內容 |
|---|---|
| **問題** | ② 指數漲，是「大家都在漲」還是「只有權值股在漲」 |
| **程式** | `app.js:3899 renderBreadth` |
| **輸入** | **`market_heat.json` 的 `breadth` 區塊**（〔事實〕`renderBreadth(heat)` 收的是 `market_heat`，**不是** `ma_breadth.json`）。`ma_breadth.json` 的讀者只有 `market.detail` |
| **輸出** | 上半：站上 20 日均線比例的折線；下半：今日漲／平／跌家數 |
| **尺寸** | 1440／390：250px（`#breadth min-height:250`） |
| **相依** | 無 |
| **可否單獨關閉** | ✅ 可以 |
| **法遵** | 🟢 低 |
| **層級** | 免費 |

### 12. `market.streak`　法人連續買超

| 欄位 | 內容 |
|---|---|
| **問題** | ② 誰被法人連續買了幾天（投信／外資／合計，門檻可調） |
| **程式** | `app.js:3984 renderTrust`、`:4061 wireStreak` |
| **輸入** | `inst_streak.json`（舊鍵 `trust_streak.json` 仍寫出，換版緩衝）＋ `candidates.json`（只為了查中文名） |
| **⚠ 暗通款曲** | 〔事實〕`app.js:3985` 寫的是 `const all = D.inst_streak`：它**不是從參數拿資料，是直接去讀全域快取 `D`**。`renderOverview`（`:2066`）把 `inst_streak` 載進來卻用 `, ,` 丟掉回傳值，只是為了讓 `D` 被填滿。**這是原則二（只准透過資料溝通）最典型的反例** |
| **輸出** | 泡泡圖（可滾輪縮放／拖曳／雙擊還原）＋ 點泡泡進個股頁 |
| **尺寸** | 1440／390：300px（`#trust min-height:300`） |
| **相依** | `core.wheelzoom`、`stock.*`（點進去） |
| **可否單獨關閉** | ✅ 可以 |
| **法遵** | 🟠 **中高**（**這一條是我判斷的**）。它**點名個股**而且**依「連續買超天數」排序**，
`compliance_and_tiers.md` 對「`technical_score` 排序、評分」判 🟠，我判這一塊同級 |
| **層級** | 免費（**〔推〕**，依上一列的判定不准進付費層） |

### 13. `market.detail`　市場明細名單

| 欄位 | 內容 |
|---|---|
| **問題** | ② 總覽上那幾個數字，完整名單長什麼樣 |
| **程式** | `app.js:1580 renderMarket`、`:1700 drawChgDist`、`:1650 drawMaTrend`、`:1569 stockTable`、`:1836 mudFetch`（即時） |
| **輸入** | `groups_today.json`、`stocks.json`、`market_heat.json`、`candidates.json`、**`ma_breadth.json`（全站唯一讀者，`app.js:1652`）** ＋ `mis` 即時 |
| **輸出** | 三個子頁：漲跌家數分布圖／站上均線趨勢／今日候選完整表 |
| **尺寸** | 1440：實測整頁 1835`*`／390：1817（`mobile_ia.md` 列為「刻意留到下一版沒動」） |
| **相依** | `core.live`、`cand.board`（第三個子頁就是它的表格版） |
| **可否單獨關閉** | ⚠ 可以，但 `market.kpi` 的四格 drill 會斷 |
| **法遵** | 🟡 中低；**但第三個子頁 `cand` 是 🔴**（見 §6 分歧 3） |
| **層級** | 免費 |

### 14. `season.month`　季節性

| 欄位 | 內容 |
|---|---|
| **問題** | ② 這個族群在這個月份，歷史上通常表現如何（超額報酬／絕對報酬／勝率） |
| **程式** | `app.js:7144 renderSeason` |
| **輸入** | `seasonality_v3.json`（`compute/season.py`） |
| **輸出** | 族群 × 月份熱力圖／曲線圖切換 ＋ 逐年明細 drill ＋ 本月歷史最強族群清單 |
| **尺寸** | 1440：熱力 640px、曲線 560px／390：實測整頁 6131`*`（清單自己 4586，已限 6 筆） |
| **相依** | 無 |
| **可否單獨關閉** | ✅ 可以（自己一個 view） |
| **法遵** | 🟡 中低。⚠ `compliance_and_tiers.md` 註記「文案要盯」——寫成「幾月該買」就變建議 |
| **層級** | 免費 |

### 15. `stock.fund`　個股基本面與財報

| 欄位 | 內容 |
|---|---|
| **問題** | ② 這一檔貴不貴、賺不賺錢（本益比／同業分位／ROE／營收 YoY／除權息） |
| **程式** | `industry.js:3587 tabOverview`（基本面卡）、`:3596 tabRevenue`、`:3903 tabProfit`、`:3985 tabDividend`、`:3824 drawPeRiver`（本益比河流）、`:4069 drawMonthSeason` |
| **輸入** | `stock/<code>.json`（`fundamental`／`revenue`／`profit`／`dividends`）、`fundamental.json` |
| **輸出** | 四個分頁的數字卡與圖表 ＋ 本益比河流圖 ＋ 月營收季節性 |
| **尺寸** | 1440：各分頁 400～900px／390：`#stockTabs`＋`#stockTab` 是手機分段列的第 3 段 |
| **相依** | `core.pop`（本益比河流的浮層）、`stock.*` 共用 `#stockTabs` 分頁列 |
| **可否單獨關閉** | ⚠ **不行**。七個分頁由 `industry.js:3582 renderTab` 的一張物件表硬派，少一個 key 就丟 `undefined is not a function` |
| **法遵** | 🟡 中低（點名個股，但呈現的是公開財報事實） |
| **層級** | 免費（`compliance_and_tiers.md` §2-2 免費層第 3 列：「個股頁全部」） |

## 3.3 ③ 什麼時候進場（M3 技術面）

### 16. `cand.board`　今日候選　🔴

| 欄位 | 內容 |
|---|---|
| **問題** | ③ 今天有哪些標的符合「A 回檔承接／B 突破追進」的條件 |
| **程式** | `app.js:3826 renderCandidates`、`:3777 renderCandFilter`、`:3767 whyHtml` |
| **輸入** | `candidates.json`（`compute/technical.py` ＋ `scoring.py`；`build_payload.py:1144 shortlist`，每面向 300 檔取聯集） |
| **輸出** | 表格（桌機）／卡片（手機）＋ 族群篩選 ＋ facet 切換 ＋ 每筆帶 `verdict`／`grade`／`stop`／`tp1`／`rr` |
| **尺寸** | 1440：表格隨筆數／390：實測 30 張卡 4335px`*`（已限 6 筆） |
| **相依** | `core.filter`（族群晶片，`localStorage tw.candGroups`） |
| **可否單獨關閉** | ⚠ 可以，但 `market.kpi` 的「候選檔數」與 `market.detail` 的 `cand` 子頁會斷 |
| **法遵** | 🔴🔴 **四維度全紅**（標的：點名個股／時態：預測／語氣：祈使「可以分批進場」／可執行性：停損＋目標價＋風報比） |
| **層級** | **只准免費，絕對不進付費層**（`compliance_and_tiers.md` §2-1、§2-2 的核心結論） |

### 17. `stock.kchart`　個股 K 線（含即時分 K）

| 欄位 | 內容 |
|---|---|
| **問題** | ③ 這一檔的價格結構現在長什麼樣 |
| **程式** | `chart.js`（`window.Chart` ＋ 指標 `KInd`）、`industry.js:3102 setupChart`、`:3423 enableDraw`、`:3482 drawBar`、`livek.js`（即時 5 秒 K） |
| **輸入** | `stock/<code>.json`、`hist/<code>/p<N>.json`（分頁載入）＋ `mis` 即時 |
| **輸出** | K 線 ＋ 多指標面板 ＋ 11 顆工具列（週期／指標／設定）＋ 手繪工具 ＋ 縮放 |
| **尺寸** | 1440：`clamp(600px, 100vh-250px, 1280px)`；寬版 `clamp(640px, 100vh-185px, 1500px)`／390：`clamp(380px, 100vh-343px, 620px)` |
| **相依** | `core.live`、`core.pop`（設定浮層）、`localStorage tw.kcfg`／`tw.kwide`／`tw.drawbar` |
| **可否單獨關閉** | ⚠ 可以，但 `stock.mtf` 共用 `KInd` 的口徑；關掉 K 線不影響 mtf，關掉 `chart.js` 兩者一起死 |
| **法遵** | 🟡 中低（呈現價格事實）。⚠ 指標本身不是建議 |
| **層級** | 免費 |

### 18. `stock.mtf`　多週期 SMC 判讀　🔴

| 欄位 | 內容 |
|---|---|
| **問題** | ③ 日／週／月多個週期的結構（BOS／CHoCH／假跌破）指向同一個方向嗎 |
| **程式** | `industry.js:3570 renderMtf`、`:3535 buildMtfGrid`、`:3524 mtfPick`；Python 端 `pipeline/compute/mtf.py` |
| **輸入** | `stock/<code>.json` 的 `mtf` 區塊 |
| **輸出** | 多週期小圖矩陣 ＋ 每格的結構結論 |
| **尺寸** | 1440：`clamp(300px, (100vh-260px)/2, 620px)` 每格／390：手機分段列第 2 段「判讀」 |
| **相依** | `stock.kchart`（共用 `KInd`） |
| **法遵** | 🔴 高 —— `compliance_and_tiers.md`：「M3『決定時機』是最典型的推介建議」 |
| **層級** | **只准免費** |

### 19. `stock.signal`　技術面訊號卡　🔴

| 欄位 | 內容 |
|---|---|
| **問題** | ③ 均線／結構／RSI／KD／MACD／乖離／BOS／CHoCH／假跌破 現在各是什麼狀態 |
| **程式** | `industry.js:3587 tabOverview` 的第三張卡（含 `verdict.invalidation`「失效條件」） |
| **輸入** | `stock/<code>.json` 的 `summary` 與 `verdict` |
| **輸出** | 九顆燈號 ＋ 失效條件 ＋ 一行免責（`industry.js:3594`，**目前全站唯一一句免責**） |
| **尺寸** | 1440：約 220px／390：同 |
| **相依** | `stock.fund`（**現在就長在同一個 `tabOverview` 函式裡**，這是要拆的第一刀） |
| **可否單獨關閉** | ❌ **不行**。它和 `stock.fund`、籌碼快照寫在**同一個 template literal** 裡（`industry.js:3591`，單行 3 張卡） |
| **法遵** | 🔴 高（`verdict.invalidation` ＝ 失效條件 ＝ 進出場規則） |
| **層級** | **只准免費** |

## 3.4 ④ 有沒有理由不進場（M4 事件面）

### 20. `events.feed`　今日事件

| 欄位 | 內容 |
|---|---|
| **問題** | ④ 今天有什麼新聞／法說／總經事件會讓我不進場 |
| **程式** | `app.js:7312 renderEvents` |
| **輸入** | `news.json` ＋ `broker_views.json` |
| **輸出** | 右側抽屜（`<aside id="side">`）：日期下拉 ＋ 五顆分類鈕（全部／台股／科技／總經／券商）＋ 清單 |
| **尺寸** | 1440：右側固定欄／390：收進「⋯ 更多」，是總覽第④步 |
| **相依** | `core.side`（`window.twSetSide`，`localStorage tw.side`）、`broker.views`（券商那一類） |
| **可否單獨關閉** | ⚠ 可以，但「券商」那一顆分類鈕會空掉 |
| **法遵** | 🟡 中低（新聞標題）。⚠ **「券商」分類例外，見下一塊** |
| **層級** | 免費 |

### 21. `stock.news`　個股新聞與公告

| 欄位 | 內容 |
|---|---|
| **問題** | ④ 這一檔最近有什麼消息 |
| **程式** | `industry.js:4140 tabNews` |
| **輸入** | `news.json`（依代號過濾）＋ `stock/<code>.json` |
| **輸出** | 新聞清單（標題 ＋ 日期 ＋ 連結） |
| **尺寸** | 1440：隨筆數／390：分段列第 3 段內 |
| **相依** | `stock.fund`（共用 `#stockTabs`） |
| **法遵** | 🟢 低（只連結、不轉述） |
| **層級** | 免費 |

### 22. `broker.views`　券商觀點　🔴🔴

| 欄位 | 內容 |
|---|---|
| **問題** | ④ 券商對這一檔怎麼看（目標價／評等／調升調降） |
| **程式** | **現在沒有獨立函式** —— 混在 `industry.js:4140 tabNews` 與 `app.js:7312 renderEvents` 兩處 |
| **輸入** | `broker_views.json`（`broker`／`target_price`／`action`／`rating`） |
| **輸出** | 個股頁的「券商觀點（新聞引述）」表格 ＋ 事件抽屜的「券商」分類 |
| **尺寸** | 1440：約 200px／390：同 |
| **相依** | `stock.news`（同一個分頁）、`events.feed`（同一份資料） |
| **可否單獨關閉** | ❌ **不行（現況）**。沒有邊界可以關 —— 這正是必須把它切出來的理由 |
| **法遵** | 🔴🔴 **最高**。`compliance_and_tiers.md` 摘要 2：士林地院 107 年度金訴字第 2 號認定「把各家投顧分析師的分析與投資建議納入自己網站，即屬 §4 之行為，不因間接取得而異」 |
| **層級** | **只准免費**，而且 `compliance_and_tiers.md` §2-5 第 4 項建議「**連免費層都要拿掉 `rating` 欄位，只留標題＋連結＋日期**」 |
| **★ 積木化的第一個具體用途** | 把它切成獨立積木之後，「拿掉 rating 欄位」就變成**改一塊積木的輸出欄位**，而不是在兩支檔案裡找字串 |

## 3.5 知識類（產業鏈與題材 —— 法遵上最乾淨、也最適合收費的一批）

### 23. `chain.map`　產業地圖

| 欄位 | 內容 |
|---|---|
| **問題** | 知識／導覽：台股分成哪八條產業鏈，各自現在強弱如何 |
| **程式** | `industry.js:171 renderMap`、`:145 chainTabsHtml`、`:159 wireChainTabs` |
| **輸入** | `industry_map.json`（`chains[]`／`industries[]`） |
| **輸出** | 八張鏈卡 ＋ 進入單一鏈的分頁列 |
| **尺寸** | 1440：實測整頁 1932`*`／390：同（長條與圓餅改左右滑被既有驗收 W3-8 擋下，見 `mobile_ia.md` §「做了又撤回的兩件事」） |
| **相依** | 無 |
| **法遵** | 🟢 低 |
| **層級** | 免費 |

### 25. `chain.diagram`　產業鏈剖析圖（2D ＋ 3D）

| 欄位 | 內容 |
|---|---|
| **問題** | 知識：這個產品／製程裡面到底有什麼零件，台廠站在哪幾格 |
| **程式** | `diagrams.js`（`window.DG` 工具箱 ＋ 檔位登錄表）、`site/dg/*.js` **27 個檔**、`diagrams.js:1437` 另外登錄 2 個（`ai_server` 鏈層級、`mlcc` 族群層級）＝ **共 29 個檔位**；3D 在 `three3d.js` 的 `SCENES`（定義 20 個，`semiconductor` 檔位 2026-09-22 退場，**實際可達 19 個**） |
| **輸入** | `supply_chain.json`（零件的 `data-seg` → 環節 → 台股與外商） |
| **輸出** | SVG 等角剖析圖（可點零件）＋ 可切 3D 場景（可繞圈、點零件亮起）＋ 零件說明卡 |
| **尺寸** | 1440：`native` 660～1180px 寬，高度隨圖／390：實測 `#industry/<chain>` 整頁 2579`*`（剖析圖預設收合） |
| **相依** | `chain.segments`（環節色與台股對應）、`core.theme`（深淺模式會切配色）、`localStorage tw.dgOpen`／`tw.dg3d`／`tw.dg3d.pal` |
| **可否單獨關閉** | ✅ **可以，而且切得最乾淨的就是這一塊** —— 一張圖一個檔、統一走 `DG.register`，`DS.has(slot)` 沒有就自動不顯示 |
| **法遵** | 🟢 **低（全站最低）**。`compliance_and_tiers.md`：「這是產業知識，不是證券分析。**這也是為什麼它是最適合收費的東西**」 |
| **層級** | **螢幕觀看免費**／**399：高解析單張匯出**（§2-2 399 層第 4 項）／**799：批次匯出 ＋ 商用授權**（§2-2 799 層第 1、2 項） |
| **⚠ 實作注意** | `compliance_and_tiers.md` §2-4 明寫：**前端 canvas 匯出擋不住，必須伺服器端渲染才擋得住**。這件事要在做之前決定 |

### 26. `chain.segments`　環節詳情與分層關聯圖

| 欄位 | 內容 |
|---|---|
| **問題** | 知識：這一條鏈分成哪幾個環節，每個環節有哪幾檔台股、哪幾家外商，誰依賴誰 |
| **程式** | `industry.js:2290 drawSegList`、`:1309 renderSegBox`、`:1461 renderPartCard`、`:2440 drawChainMap`（關聯圖）、`:2683 relBlock`／`:2733 wireRelBlock`（個股產業關係面板）、`:2646 showCompany`（外商小卡）、`:2933 renderChainStrip`（個股頁上方的鏈條） |
| **輸入** | `supply_chain.json`（**唯一人工維護的 YAML**，`pipeline/groups/supply_chain.yaml`） |
| **輸出** | 環節色標晶片列 ＋ 環節詳情格 ＋ 分層關聯圖（SVG，含依存度粗細）＋ 點個股展開它的產業關係 |
| **尺寸** | 1440：關聯圖區自己 1717px`*`／390：`#chainList` 實測 1129px`*`（已限 4 格） |
| **相依** | `chain.diagram`（同一套環節色，`App.L.scolor` 注入 `--c`） |
| **可否單獨關閉** | ⚠ 可以，但剖析圖的零件會失去「誰做的」小卡 |
| **法遵** | 🟢 低 |
| **層級** | 免費看／**399：跨產業鏈搜尋與公司反查**（§2-2 399 層第 5 項）。⚠ 該項自己註明「資料在 public repo，擋不住，只賣介面便利性」 |

### 27. `theme.diagram`　題材剖析圖

| 欄位 | 內容 |
|---|---|
| **問題** | 知識：這個題材的上游→中游→下游是誰，台廠站在哪一段 |
| **程式** | `themes3d.js`（`window.ThemeDiagrams`，`T.<id>` **18 張**：`cowos`／`hbm_memory`／`pcb_ccl`／`glass_substrate`／`asic_ip`／`ai_server`／`power_bbu`／`thermal`／`silicon_photonics`／`semi_equipment`／`apple_chain`／`edge_ai_pc`／`robotics`／`drone`／`satellite`／`ev_auto`／`defense`／`heavy_electric`）、`app.js:6954 wireThemeDiagram`、`:7013 renderThemeDetail` |
| **輸入** | `themes.json` ＋ `supply_chain.json`（環節色） |
| **輸出** | 水平等角供應鏈圖（站點 ＋ 說明 ＋ 可點的台股代號） |
| **尺寸** | 1440：畫布寬 1180（AI 伺服器 980）／390：實測 900–1403`*`（503px），要左右捲 |
| **相依** | `theme.heat`（題材 id）、`diagrams.js` 的 `window.DG` 工具箱 |
| **可否單獨關閉** | ✅ 可以（`T[id]` 沒有就不畫） |
| **法遵** | 🟢 低 |
| **層級** | 同 `chain.diagram`：免費看／399 匯出／799 商用授權 |

## 3.6 底層共用元件（**不是積木，是積木之間的插座**）

這 11 塊不回答四問、不單獨賣、也不該出現在分層表上。
**它們存在的意義是：積木之間不准直接呼叫對方，所以共用的東西必須有自己的位置。**

| id | 中文名 | 程式 | 誰在用 | 現況問題 |
|---|---|---|---|---|
| `core.route` | 路由 | `app.js:1422 route` | 全部 | render 函式寫死在一張物件表（`{overview: renderOverview, ...}`），加一頁要改這裡 |
| `core.data` | 資料快取 | `app.js:127 load` ＋ `const D = {}`（`:8`） | 全部 | 全域單例，沒有「哪一塊積木要哪一份」的宣告 |
| `core.chart` | 圖表工廠 | `app.js:152 chart` ＋ `const charts = {}`（`:9`） | 全部 | **key 是 DOM id**，所以 DOM id 必須全域唯一 |
| `core.filter` | 族群／產業鏈篩選 | `app.js:5089 wireRotFilter`、`:4820 filterChips`、`:4859 filterDropdown` ＋ `const ROT`（`:5009`） | `flow.clock`／`flow.rank`／`core.zoom` | 一份全域狀態被三處讀寫 |
| `core.rangebar` | 時間拉 Bar／區間桿／播放 | `app.js:453 rangeBar`、`:641 spanBar`、`:524 playBar` | `flow.*`、`season` | 還算乾淨，是目前最接近「元件」的一支 |
| `core.zoom` | 放大視窗 | `app.js:2137 openZoom`、`:4747 openRotZoom` | `flow.heat`／`flow.clock`／`theme.heat` | `openRotZoom` 是 `openZoom` 的特化版，重複了一份篩選 UI |
| `core.live` | 盤中即時層 | `live.js`（整支）＋ 各頁自己的 `rlv*`／`skl*`／`mud*`／`gpStopLive` | `index.board`／`flow.clock`／`flow.sankey`／`chain.overview`／`market.detail`／`stock.kchart` | **同一件事有 6 套實作**（見 §4） |
| `core.theme` | 深／淺主題 | `app.js:217 applyTheme`、`:196 refreshPalette` | 全部 ＋ 剖析圖配色 | 切主題要重畫剖析圖（`delivery_log` 第 12 筆） |
| `core.freshness` | 資料狀態與版號徽章 | `app.js:7485 renderFreshness`、`:7470 renderBuild` | 全站頂欄 | 乾淨 |
| `core.mobileIA` | 手機分段／限筆／收合／決策動線 | `app.js:1382 applyMobileIA` ＋ `MIA_PAGER`（`:1010` 一帶） | 全部 | **用 CSS 選擇器字串綁死 DOM id**（見 §4 第 4 項） |
| `core.pwa` | Service Worker | `site/sw.js` ＋ `index.html:3193` | 全站 | 對 `data/**` 完全不介入（刻意） |

**另外兩塊「不是功能、是紀錄」的積木：**

| id | 中文名 | 程式 | 輸入 | 層級 |
|---|---|---|---|---|
| `meta.delivery` | 交付清單 | `app.js:7088 renderDelivery`、`:7064 dlvCard` | `delivery.json`（來源 `docs/delivery_log.md`） | 免費（信任工具） |
| `meta.tasks` | 任務板 | `tasks.js` ＋ `app.js:7036 renderTasks` | `tasks.json`（來源 `obsidian/tasks.yaml`） | 免費。**頂層分頁入口已移除**，網址仍可開 |

---

# §4 現況離「積木」有多遠：重構清單

**⚠ 這一節只寫清單，這一棒沒有動手改任何一行。**

**規模定義**：小＝一天以內、單檔；中＝2～4 天、跨 2～3 檔；大＝一週以上、會動到全站共用的東西。
**風險定義**：低＝改壞了驗收一定抓得到；中＝會動到既有驗收段落；高＝會動到 Andy 現在正在看的畫面。

| # | 卡住的地方（〔事實〕） | 影響哪幾塊積木 | 規模 | 風險 | 建議順序 |
|---|---|---|---|---|---|
| 1 | **版面寫死在 `index.html`**：9 個 `.view` 區塊、每張卡的 `<div class="card">`、每個圖表容器的 id，全部是靜態 HTML（`index.html:2868–3129`）。積木**不帶自己的版面**，所以「搬位置」＝ 改 HTML | 全部 27 塊 | **大** | 中 | **④**（最根本，但要先有 2、3、5 才做得動） |
| 2 | **`broker.views` 沒有邊界**：券商目標價與評等混在 `industry.js:4140 tabNews` 與 `app.js:7312 renderEvents` 兩處，沒有獨立函式 | `broker.views`／`stock.news`／`events.feed` | **小** | 低 | **①（最先做）** |
| 3 | **`stock.signal` 與 `stock.fund` 寫在同一個 template literal**：`industry.js:3591` 單行輸出三張卡（基本面／籌碼快照／技術面訊號），🟡 與 🔴 綁在一起 | `stock.fund`／`stock.signal` | **小** | 低 | **②** |
| 4 | **`MIA_PAGER` 用 CSS 選擇器字串綁死 DOM id**（`app.js:1010` 一帶）：新增／搬動一塊積木要同時改 ①HTML ②render 函式 ③`MIA_PAGER` ④`_uitest.py` 的段落名。而且 `#ovRotCard` 在表裡出現兩次，就是為了硬拆「一張卡兩件事」 | 全部（手機） | 中 | 中 | **③** |
| 4b | **全域快取 `D` 被當成隱性參數**：`renderTrust`（`app.js:3985`）直接讀 `D.inst_streak`，而 `renderOverview`（`:2066`）載了它卻用 `, ,` 丟掉回傳值 —— 兩塊程式碼靠「誰先把 `D` 填滿」溝通。搬動或延後任何一塊都會讓另一塊拿到空的 | 〔事實〕`app.js` 共 **33 處**直接讀 `D.<表名>`：`groups_detail`×12、`meta`×6、`themes`×4、`stocks`×4、`groups_today`×2、`flow_v3`×2、`market_heat`／`inst_streak`／`candidates` 各 1；`industry.js` 另有 `A.D.meta`。影響 `market.streak`／`flow.*`／`chain.*` | 小 | 低 | **②b**（跟 #3 同一批） |
| 5 | **`const charts = {}` 用 DOM id 當 key**（`app.js:9`）：所以全站 DOM id 必須唯一。`industry.js:177` 的註解已經記下踩過的坑：「產業鏈頁的內容留在 DOM 裡的話，`#chainSwitch`／`#gpBar` 會同時出現兩份」 | 全部 | 中 | 中 | **⑤** |
| 6 | **`industry.js` 整支吃 `window.App`**：`let A = window.App`，全檔 **228 處** `A.xxx`（`grep -c`）。這是「透過內部函式溝通」最大的一筆，直接違反原則二 | `chain.*`／`stock.*` 全部 | **大** | 中 | **⑥** |
| 7 | **`core.live` 有 6 套實作**：`live.js` 的通用層之外，`app.js` 另有 `RLV`（RRG 即時，`:2509`）、`SKL`（桑基即時，`:5956`）、`MUD`（市場明細即時，`:1798`），`industry.js` 有 `gpStopLive`／`liveTick`，`market3.js` 有自己的 SSE，`livek.js` 又一套。每一套各自管排程、節流、錯誤顯示 | `index.board`／`flow.clock`／`flow.sankey`／`chain.overview`／`market.detail`／`stock.kchart` | **大** | **高**（盤中壞掉 Andy 馬上看到） | **⑧（最後做）** |
| 8 | **`ROT` 一份全域篩選狀態被三處讀寫**（`app.js:5009`）：時鐘、排行、放大視窗。所以 `flow.clock` 與 `flow.rank` 現在**無法單獨關閉** | `flow.clock`／`flow.rank` | 中 | 低 | **⑦** |
| 9 | **`route()` 的 render 表寫死**（`app.js:1490` 一帶）：`{overview: renderOverview, flow: renderFlow, ...}`，加一頁要改路由本身；且 `const rendered = {}`（`:798`）是**一次性閘門** —— 積木無法「重畫自己」 | `core.route` | 小 | 低 | **⑨**（跟 1 一起做） |
| 10 | **孤兒資料管線**：`group_valuation`／`seasonality`／`relative_strength`／`intl` 四份 JSON 每天照算照寫，前端零讀者 | 無（純浪費） | **小** | **低** | **⑩**（順手，但要先問 Andy 是不是打算之後再用） |
| 11 | **`site/dg/*.js` 27 支逐一列在 `index.html:3140–3170`**：新增一張剖析圖要改 `index.html` —— 而那正是多人同時改最容易撞的檔 | `chain.diagram` | 小 | 低 | 併入 ④ |
| 12 | **`_uitest.py` 的段落名是人工對照表**（`CLAUDE.md` 那張表），不是從模組清單生成的。積木改名／搬家，驗收段落不會自動跟上 | 全部（驗收） | 中 | 低 | 併入 ③ |

## 4.1 建議的做事順序（〔判斷〕）

**第一梯次（投報最高、風險最低，各自一天內）**
1. **切出 `broker.views`**（#2）—— 它是 🔴🔴 最高風險項，而且切出來之後
   `compliance_and_tiers.md` §2-5 第 4 項「拿掉 rating 欄位」立刻變成一行改動。
2. **拆 `stock.signal` / `stock.fund`**（#3）—— 把 🔴 與 🟡 分開，分層表才放得下。
3. **`MIA_PAGER` 改成從模組清單生成**（#4 ＋ #12）—— 一次解決「搬一塊要改四處」。

**第二梯次（結構，各 2～4 天）**

4. **模組宣告檔 ＋ 版面設定**（#1 ＋ #9 ＋ #11）：
   每塊積木宣告 `{ id, name, question, inputs[], mount(el, ctx), teardown() }`，
   版面改成一份 `layout.json`（哪一頁、哪一格、桌機／手機各自的順序）。
   **這一步做完，Andy 的「像積木一樣堆疊」才算真的成立。**
5. **`charts` 改用實例而非 DOM id 當 key**（#5）。
6. **`industry.js` 對 `window.App` 的依賴收斂成明確的 context 物件**（#6）。
7. **`ROT` 拆成 `core.filter` 元件，`flow.clock` 與 `flow.rank` 各自訂閱**（#8）。

**第三梯次（高風險，最後做）**

8. **`core.live` 六套合一**（#7）。⚠ 這一項**一定要單獨一批推**，不要跟別的綁在一起。

**隨時可做**

9. **清孤兒資料管線**（#10）—— 但先問 Andy，`group_valuation` 是他自己叫停的，可能之後要回來。

---

# §5 兩張直接可用的對照表

## 表 A：模組 × 四問 —— 哪一問回答得最弱

| 問題 | 回答它的積木 | 塊數 | 強弱 |
|---|---|---:|---|
| **① 錢往哪個族群跑** | `flow.clock`／`flow.rank`／`flow.sankey`／`flow.heat`／`flow.inst`／`flow.conc`／`market.treemap`／`theme.heat`／`chain.overview` | **9** | 🟩 **最強**。族群層級、個股層級、題材層級、鏈層級都有，而且有即時 |
| **② 那個族群現在貴不貴** | `index.board`／`market.kpi`／`market.breadth`／`market.streak`／`market.detail`／`season.month`／`stock.fund` | 7 | 🟥 **最弱（見下）** |
| **③ 什麼時候進場** | `cand.board`／`stock.kchart`／`stock.mtf`／`stock.signal` | 4 | 🟨 中等，但**四塊有三塊是 🔴 法遵高風險** |
| **④ 有沒有理由不進場** | `events.feed`／`stock.news`／`broker.views` | 3 | 🟧 **偏弱**，而且**三塊裡最有內容的那塊（`broker.views`）是 🔴🔴，長期不該留** |

### ★ 為什麼「② 貴不貴」最弱（〔事實〕＋〔判斷〕）

**〔事實〕** 表面上 ② 有 7 塊，但**其中 6 塊回答的是「大盤／個股」，不是「族群」**：

| 積木 | 它其實在回答哪一個層級 |
|---|---|
| `index.board` 大盤三張圖 | 大盤 |
| `market.kpi` 六格 | 大盤 |
| `market.breadth` 市場寬度 | 大盤 |
| `market.streak` 法人連續買超 | 個股 |
| `market.detail` 市場明細 | 個股 |
| `stock.fund` 個股基本面 | 個股 |
| `season.month` 季節性 | **族群（唯一一塊，但它答的是「歷史上這個月怎樣」，不是「現在貴不貴」）** |

**〔事實〕** 唯一真正回答「**這個族群現在貴不貴**」的兩塊，**在 2026-09-23 被 Andy 指定拿掉了**：

- 資金流向頁的「估值篩選」卡（本益比／股價淨值比／ROE／市值 ＋ 散點圖 ＋ 右側表格）——
  `renderVal()`／`VF`／`HOW.val` ＋ `.vfilters` CSS 全部移除（`index.html:3057` 註解）。
- 總覽的「族群估值」卡（`#gval`／`renderGval()`）—— 追問後 Andy 回「OK」＝ 一起砍。

**結果**：`group_valuation.json` 現在**每天照算，前端零讀者**（§1.3 孤兒表第 1 列）。

> **〔判斷〕這個缺口是整個產品架構上最大的一個，理由不只是「少一張圖」：**
> `CLAUDE.md` 第一段寫的判斷順序是「**M1 資金面 ＋ M2 基本面決定方向** → M3 決定時機 → M4 否決」。
> 現在 M2 在**族群層級上是空的** —— 使用者看到「錢流進 ABF 載板」之後，
> 下一個問題「那它現在貴不貴」在站上找不到答案，只能自己一檔一檔點進個股頁看本益比。
>
> ⚠ **但我不建議直接把那兩張卡加回去** —— 那是 Andy 親自拍板拿掉的（`DECISIONS` 等級的決定），
> 而且「估值篩選」那張卡的問題是**它是一個篩選器，不是一個答案**（四個滑桿 ＋ 一張散點圖，
> 使用者要自己調參數才看得到結論）。
> **建議的替代積木**（新的一塊，不是把舊的搬回來）：
> `flow.valuation`「族群估值位階」—— 一塊積木回答一句話：
> 「這個族群的本益比／股價淨值比，站在它自己近 5 年分佈的第幾分位」。
> 一個數字 ＋ 一條分佈條，**沒有滑桿、沒有排序、不點名個股**（法遵 🟢～🟡）。
> 資料已經有了（`group_valuation.json` 照算），不必動資料管線。
> **這一條要 Andy 點頭，我沒有自作主張把它排進重構清單。**

## 表 B：模組 × 方案層級

**〔事實〕** 分層一律引用 `docs/compliance_and_tiers.md` §2-2，我沒有另訂一套。
標「**〔推〕**」的是那份文件沒有逐項寫到、我依同一套原則推的。

### 免費層（NT$0）—— 全部 27 塊積木都看得到

| 積木 | 法遵 | 為什麼留在免費 |
|---|---|---|
| `flow.clock`／`flow.rank`／`flow.sankey`／`flow.heat`／`flow.inst`／`flow.conc` | 🟡 | 習慣的鉤子，每天打開就是看這個 |
| `market.treemap`／`theme.heat`／`chain.map`／`chain.overview` | 🟡🟢 | 同上 |
| `index.board`／`market.kpi`／`market.breadth`／`market.detail`／`season.month` | 🟢🟡 | 公開資料的呈現 |
| `market.streak` | 🟠 | **〔推〕** 點名個股 ＋ 依天數排序，判同 `technical_score`，不准進付費層 |
| `stock.fund`／`stock.kchart`／`stock.news` | 🟡🟢 | 「個股頁全部」留免費（public repo 藏了也沒用） |
| **`cand.board`** | 🔴🔴 | ⚠ **刻意免費**。放進付費層 ＝ 自己把 §107 的第四個要件補上 |
| **`stock.mtf`／`stock.signal`** | 🔴 | 同上（M3「決定時機」是最典型的推介建議） |
| **`broker.views`** | 🔴🔴 | 同上。⚠ 而且 §2-5 建議**連免費層都要拿掉 `rating` 欄位** |
| `chain.diagram`／`chain.segments`／`theme.diagram`（螢幕觀看） | 🟢 | 這是識別，藏起來沒有人知道我們有 |
| `meta.delivery`／`core.freshness` | 🟢 | 信任工具，本來就該免費 |

### NT$399／月 —— 「省時間」層

| `compliance_and_tiers.md` §2-2 的項次 | 對到哪一塊積木 | 法遵 | 擋得住？ |
|---|---|---|---|
| 1. 每日盤後一封信（族群層級） | `flow.*` 的**輸出管道**（新增，不是現有積木） | 🟢 | ✅ 真的擋得住 |
| 2. 自選清單（雲端跨裝置） | `core.watchlist`（**尚不存在**，現在只有 `localStorage`） | 🟢 | ✅ |
| 3. 條件變化提醒（Email） | `flow.*`／`stock.fund` 的**訂閱層**（新增） | 🟡 | ✅ |
| 4. 剖析圖高解析匯出（單張） | **`chain.diagram`** ＋ `theme.diagram` | 🟢 | ⚠ 只有伺服器端渲染才擋得住 |
| 5. 跨產業鏈搜尋與公司反查 | **`chain.segments`** | 🟢 | ⚠ 資料在 public repo，只賣介面 |
| 6. 版面／主題／圖表設定跨裝置同步 | `core.theme` ＋ `core.mobileIA` ＋ 22 個 `localStorage` 鍵 | 🟢 | ✅ |
| 7. 歷史回放延長（30 天 → 2 年） | `core.rangebar` ＋ `flow.*` | 🟡 | ❌ 靜態檔擋不住 |

### NT$799／月 —— 「帶得走」層

| §2-2 的項次 | 對到哪一塊積木 | 法遵 | 擋得住？ |
|---|---|---|---|
| 1. 剖析圖與 3D 場景的**商用授權** | **`chain.diagram`（29 檔位）＋ `theme.diagram`（18 張）** | 🟢 | ✅✅ **100%**（法律，不是技術） |
| 2. 整套批次匯出（含向量檔） | 同上 | 🟢 | ⚠ 伺服器端渲染才擋得住 |
| 3. 自訂族群／自訂供應鏈 | `flow.*` 的計算層（跑在 Worker 上） | 🟡 | ✅ |
| 4. 資料出口（CSV／Parquet） | `flow.*`／`chain.segments` 的輸入 | 🟠 | ❌ ⚠ 卡在 FinMind／Yahoo 的資料授權 |
| 5. 需求排程權 | `meta.delivery` | 🟢 | ✅ |
| 6. 優先回覆 | 非積木（人的時間） | 🟠 | ✅ ⚠ **§2-2 判定這是整份分層風險最高的一項** |

### ★ 一句話結論

> **付費層裡只有三塊真正的積木：`chain.diagram`、`theme.diagram`、`chain.segments`。**
> 其餘的付費項目都是**輸出管道（信、匯出、同步、授權）**，不是新功能。
> 這是刻意的 —— `compliance_and_tiers.md` §2-1：
> 「把結論放進付費層，是我們自己把最後一塊拼圖補上。」
>
> **〔判斷〕這件事對積木化有一個很具體的影響**：
> 積木的介面除了 `mount(el)` 之外，**還要有 `export()`**（吐出這塊積木的資料與高解析圖），
> 因為「匯出」是付費層的主要賣點，而它必須是**每一塊積木自己的能力**，
> 不能做成一個到處挖資料的全域匯出器。

---

# §6 ⚠ Andy 可能不同意的地方（一次列完，讓他一次否決）

1. **我把「法人連續買超」（`market.streak`）標成 🟠 中高法遵風險。**
   `docs/compliance_and_tiers.md` 沒有逐項寫到它，這是我依它的四維度判準推的：
   **它點名個股、而且依「連續買超天數」排序** —— 跟該文件判 🟠 的「`technical_score` 排序」是同一種形態。
   **代價**：它因此不能進付費層。**如果 Andy 認為「連續買超天數」是純事實不是排序推介，這一格可以降成 🟡。**
   ⚠ 但我建議不要自己降，這一項該由專業人士確認。

2. **我建議新增一塊 `flow.valuation`「族群估值位階」來補第②問的缺口** ——
   而「族群估值」正是 Andy 自己在 2026-09-23 叫停的東西。
   **我沒有把它排進重構清單，只寫在表 A 的判斷裡。**
   我的理由是「舊的那張是篩選器不是答案」，但**這可能只是我在幫自己找理由把他否決的東西塞回來**。
   這一題要他點頭。

3. **我把「今日候選」在市場明細的第三個子頁（`#market/cand`）也算成 `cand.board` 的一部分。**
   所以「今日候選不准進付費層」這條約束**同時綁住市場明細**。
   Andy 可能覺得「市場明細只是一張表，不是候選卡」—— 但它讀的是同一份 `candidates.json`、
   同樣帶 `verdict`／`stop`／`tp1`，我判定它是同一塊積木的另一種呈現。

4. **我把 `flow.clock` 與 `flow.rank` 切成兩塊，但它們現在是同一張卡。**
   2026-09-21 是 Andy 親口要求合併的（「這兩張圖合併，共用同個篩選資訊」）。
   **我切成兩塊積木，不是要把畫面拆回去** —— 版面上仍然可以並排在同一張卡裡，
   切開的只是程式的邊界（讓它們各自能被關掉、各自能搬到別頁）。
   但如果 Andy 的意思是「這兩張圖在概念上就是一件事」，那應該合成一塊 `flow.rotation`。

5. **`stock.*` 我切成五塊，而不是一塊「個股頁」。**
   代價是個股頁的七個分頁（`renderTab` 那張表）要重寫。
   如果 Andy 覺得「個股頁就是一頁，不要拆」，那五塊會併成一塊 ——
   **但那樣的話這一塊就同時含 🟡 與 🔴，分層表上會放不下。** 我選了分層優先。

6. **排 `core.live`（六套即時實作合一）在最後做。**
   它其實是技術債最重的一項，但它壞掉 Andy 盤中馬上看得到。
   如果他覺得「反正我大部分時間看盤後，先修乾淨」，順序可以往前調。

7. **這份文件把「底層共用元件」排除在分層表之外。**
   也就是說「盤中即時」不會被賣。這是刻意的 —— `compliance_and_tiers.md` §2-1 明寫
   **不要用「即時不即時」分層**（`mis.twse.com.tw` 的商用授權未確認）。
   如果 Andy 想賣即時，得先把那個授權問題查清楚。

---

# §7 我沒查到的 / 沒有把握的

1. **每一塊積木在 1440 的實際高度，我只有 CSS `min-height`，沒有實測。**
   `docs/mobile_ia.md` 的稽核表是 **390×844** 量的，而且是 2026-09-24 改版**前**的數字。
   要精確的桌機高度，得跑 `python scripts/_show.py --view <x> --width 1440`，這一棒沒有跑（避免與另一批衝突）。

2. **`docs/compliance_and_tiers.md` 寫「27 張產業鏈剖析圖／19 個 3D 場景／18 張題材圖」，我量到的是
   29 個剖析圖檔位（27 個 `site/dg/*.js` ＋ `diagrams.js` 內建的 `ai_server`、`mlcc`）、
   20 個 `SCENES` 定義（`semiconductor` 檔位已退場 → 實際可達 19）、18 張題材圖。**
   題材圖與 3D 場景對得上，**剖析圖差 2 張**。差異很可能只是那份文件寫的是 `site/dg/` 的檔案數，
   但我沒有百分之百確認，所以兩個數字都列出來。

3. **`relative_strength.json` 與 `intl.json` 到底是「忘了清」還是「留著要用」，我不知道。**
   `git log` 沒有講。清掉之前要問 Andy 或查 `DECISIONS.md`。

4. **我沒有實際驗證「把某一塊 render 呼叫註解掉，整站不會壞」**（§2.1 原則三的驗收方式）。
   那要真的改程式碼跑一次，而這一棒不准動程式碼。
   所以**「可否單獨關閉」那一欄全部是讀原始碼推的，不是實測的**。
   §4 第 8 項（`ROT` 讓 `flow.clock`／`flow.rank` 關不掉）我有把握，
   因為 `wireRotFilter` 對每個 `.rotfilter` 各產一份 UI、吃同一個 `ROT` 狀態，這在程式碼上是明確的。

5. **`docs/mobile_release_plan.md` 我只看了標題與 `CLAUDE.md` 的引用，沒有逐字讀完。**
   所以「哪些積木進 App 第一版」這件事**這份文件沒有回答** ——
   它需要的前提（模組清單）現在有了，但取捨本身是另一批的工作。

6. **我沒有打開過線上網站確認任何一塊積木現在真的長什麼樣。**
   這個容器的出口被擋（`WebFetch`／`curl` 回 `EGRESS_BLOCKED`），
   全部內容都是讀 `/home/user/tw-rotation` 工作區的原始碼讀出來的。
   工作區已 `git pull --ff-only` 到 `origin/main` 的 `1f92bf0`（2026-09-24 00:41 的資料回補 commit）。
