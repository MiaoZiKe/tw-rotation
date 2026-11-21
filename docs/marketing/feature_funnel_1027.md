# 功能引流規劃：從每日貼文導向網站各功能（2026-10-27）

> Andy 2026-10-27 原話：「目前仍需要每日自動發文，Default 是盤中盤前盤後，但是我網站內有很多功能需要推廣：1. 2D/3D 圖關於介紹科技產業鏈以及產品剖析介紹 2. ETF 配息 3. 財報 & ETF 行事曆 4. 抓取最受關注的話題消息，例如大公司財報、FED 消息、石油問題等等。幫我規劃如何連結到網頁，這才是真的引流」。
> 分工：本單位只做規劃、找方法、量測；文案與圖由 Andy 的 GPT 幫手製作（`growth_command_1026.md` 末節「分工更正」）。本檔不含貼文成品、不改程式。
> 讀過的依據：`site/app.js` route()、`site/industry.js` route()、`site/diagrams.js`、`site/features.js`、`site/plan_presets.js`、`site/account.js`（`srcFromUrl`／`landTrack`／`pv`）、`scripts/social_snap.py`（`link_url`）、`pipeline/sources/news.py`、`pipeline/calendar/macro_events.yaml`、`auto_post.md`、`today_events_feed.md`、`traffic_methods_1027.md`、`launch_standard.md` 第二節第 10 條。
> 信心度：高＝直接讀到程式碼；中＝讀到程式碼但行為可能被後台改過，或來自單一搜尋摘要；低＝推論。

---

## 一、事實（讀程式碼得到的，與我的判斷分開）

1. 網址形式：站內是 hash 路由，貼文網址要寫成 `https://liguligu-puipui.com/?u=<來源>#<路由>`。**`?u=` 必須放在 `#` 前面**，放在後面讀不到（`account.js` 的 `srcFromUrl` 讀 `location.search`）。信心：高。
2. `?u=` 解析：`<平台>-<時段>-<日期>`，平台 `th/ig/fb/yt/x/tt/ln` 會被翻成名稱，其他字串原樣收；時段 `pm/id/cl/mg/wk` 會被翻成名稱，其他原樣收；全部清掉非英數字元、截 40 字（`srcClean`）。所以 `th-f3d-20261028` 讀得進來，但**報表裡時段會顯示 `f3d_20261028` 而不是中文名**，除非把新時段碼加進 `SRC_SLOT`（見第四節規格）。Andy 例子 `threads-feat3d-20261028` 也讀得進來，但平台會變成原樣 `threads`，與現有 `th` 分成兩個來源，**建議統一用 `th`**。信心：高。
3. 漏斗事件已在站內：`land`（進站，30 分鐘內同一台只算一次）、`pricing_view`（進入 `#pricing` 時送出）；`signup`、`trial_start`、`paid` 由 Worker 計算（`account.js` 註解）。信心：高（`land`、`pricing_view` 讀到程式碼）；中（`signup`、`trial_start` 只讀到註解說明，沒讀到 Worker 原始碼）。
4. 「第一次來源」會存在瀏覽器 `tw.src`，註冊時送 Worker（`sendSrc`），所以**註冊歸因給第一次帶他進站的貼文**，不是最後一次。信心：高。
5. 現行貼文程式只帶首頁網址：`social_snap.py` 的 `link_url(kind, ymd, platform)` 輸出 `https://liguligu-puipui.com/?u=th-id-20261027`，沒有 `#路由`；`auto_post.md` 第三節 4 點寫「盤中 → `#flow/rotation`；盤後 → `#market/inst`」，但程式實際輸出沒有帶 hash。信心：高（讀到 `link_url` 原始碼；`auto_post.md` 與程式不一致，列入第九節第 12 點）。
6. 站內有的功能與路由、權限，見第二節表。權限數字來自 `plan_presets.js` 的訪客範本，**後台「權限矩陣」可即時改，所以以線上為準**。信心：中。
7. 站內沒有任何「付費才看得到」的內容隔離之外的金流：`pricing.js` 有方案頁，但收款前六道關卡（`launch_standard.md` 第二節 10）未過，**不得收款，只開預約**。信心：高。
8. 新聞資料：`pipeline/sources/news.py` 抓鉅亨（台股／科技／總經三類）、TechNews、經濟日報 RSS，進資料湖 `data/news`；`today_events_feed.md` 實測 4,881 則、重大訊息 1,170 則。再散布授權**未確認**（`launch_gap_legal_1009.md` F2）。信心：高（程式與實測）。

---

## 二、功能 → 落點網址對照表（交付 1）

網址欄是**可直接點的完整網址**（`?u=` 欄位用佔位 `{u}`，使用時換成第三節規則產生的值）。「登入／付費」欄：**訪客**＝沒登入；**免費會員**＝註冊登入；**付費**＝Plus 以上，收款前不可對外說「購買」，只寫「可預約」。

| # | 功能 | 路由（hash） | 完整網址 | 登入／付費門檻（依訪客範本，信心中） | 適合的鉤子 | 最佳形式 |
|---|---|---|---|---|---|---|
| 1 | 產業鏈剖析圖 2D（半導體） | `#industry/semiconductor`（預設落在這條鏈第一張剖析圖） | https://liguligu-puipui.com/?u={u}#industry/semiconductor | 訪客可看（`ind.groups`、`ind.diagram` 訪客開）；免費會員每日 3 個產業分頁；超過跳「用完」卡 | 「一顆晶片從沙子到封裝，要過幾關？」 | IG 輪播（5 張拆步驟）、短影片 |
| 2 | 產業鏈剖析圖 2D（AI 伺服器） | `#industry/ai_server` | https://liguligu-puipui.com/?u={u}#industry/ai_server | 同上 | 「一台 AI 伺服器機櫃裡裝了什麼？」 | IG 輪播、短影片 |
| 3 | 單張產品剖析圖（例：MLCC） | `#industry/electronics/dg/mlcc`（格式 `#industry/<鏈>/dg/<圖id>`；**圖 id 必須掛在該鏈上，否則回選單**） | https://liguligu-puipui.com/?u={u}#industry/electronics/dg/mlcc | 同上 | 「手機裡幾百顆小方塊，是怎麼疊出來的？」 | 限動、Threads 單圖 |
| 4 | 3D 剖析圖 | 同上路由，頁內按「3D」鈕（沒有獨立網址） | 用 1～3 的網址 | **訪客關（`ind.3d: false`）；免費會員每日 1～3 次**；付費更多。所以 3D 貼文的 CTA 要寫「註冊後可轉 3D」 | 「轉得動的晶片剖面」 | 短影片（螢幕錄 3D 旋轉）、輪播末張 |
| 5 | 產業鏈關聯圖 | 同產業鏈頁內 | 用 1～2 的網址 | 訪客關（`ind.rel` 訪客 false）；Plus 以上 | 不建議當主鉤子 | 不單獨推 |
| 6 | 產業熱力圖（產業） | `#heatmap/industry` | https://liguligu-puipui.com/?u={u}#heatmap/industry | 訪客可看；點格跳頁（`heat.link`）訪客關 | 盤中、盤後固定文已用 | 沿用盤中模板 |
| 7 | 題材熱力圖／題材剖析 | `#heatmap/theme`、`#heatmap/theme/<題材id>`（舊 `#themes` 會導過來） | https://liguligu-puipui.com/?u={u}#heatmap/theme | 訪客可看；題材剖析有每日上限（`TwQuota.routeOk`） | 「這週市場在聊什麼題材」 | Threads 文字 |
| 8 | ETF 配息行事曆 | `#etf/cal` | https://liguligu-puipui.com/?u={u}#etf/cal | 訪客可看；點右側清單訪客 3 次／免費會員 5 次（`etf.cal.click`） | 「本月誰要除息？」「月配 ETF 月曆」 | IG 輪播（月曆圖）、Threads 文字 |
| 9 | ETF 總覽（含報酬比較） | `#etf/list` | https://liguligu-puipui.com/?u={u}#etf/list | 訪客可看；改期間、比較需 Plus（`etf.ret.period`、`etf.cmp`） | 「同類 ETF 配息率比一比」 | Threads 文字、輪播 |
| 10 | ETF 現金流試算 | `#etf/inc` | https://liguligu-puipui.com/?u={u}#etf/inc | **訪客不能看（`etf.cashflow` 訪客 false）；免費會員每日 3～5 次、只看預設參數；自訂參數 Plus 以上** | 「每月要領 1 萬，要存多少？」（工具型鉤子，最能帶註冊） | 短影片、限動、Threads 互動串 |
| 11 | 財經日曆（財報＋FED 等） | `#earnings` | https://liguligu-puipui.com/?u={u}#earnings | 訪客可看；點事件訪客 3 次／免費會員 5 次（`earn.click`） | 「本週財報週：誰要公布」「FOMC 本週」 | Threads 文字、IG 輪播 |
| 12 | 今日事件（新聞／法說／總經抽屜） | 無獨立路由，是側邊抽屜（`events`） | 落點用首頁：https://liguligu-puipui.com/?u={u} | 訪客**累計**最多開 5 次（`events.total`），用完跳免費註冊卡；點新聞連結訪客 3 次／免費會員 5 次（`news.open`） | 「今天市場在聊什麼」 | 搭配 11 一起推 |
| 13 | 精選文章（比比快訊、盤前消息等） | `#articles`（列表）、`#article/<id>`（單篇） | https://liguligu-puipui.com/?u={u}#articles | 單篇有類別權限（`art.cat.*`）；比比快訊類單篇可能要登入（信心低，未逐篇核對） | 「想看完整說明」 | 沿用既有精選文章推播 |
| 14 | 季節性 | `#season` | https://liguligu-puipui.com/?u={u}#season | 族群篩選免費會員每日 10 次，訪客關 | 「某月歷史上哪些族群常強」（只能講歷史統計） | Threads 文字 |
| 15 | 資金流向（盤中固定落點） | `#flow/rotation` | https://liguligu-puipui.com/?u={u}#flow/rotation | 訪客可看；時間列回放等需 Plus | 盤中模板既有 | 沿用 |
| 16 | 三大法人／融資融券（盤後固定落點） | `#market/inst` | https://liguligu-puipui.com/?u={u}#market/inst | 訪客可看，部分篩選有次數 | 盤後模板既有 | 沿用 |
| 17 | 方案頁（只在收款前當「預約」落點） | `#pricing` | https://liguligu-puipui.com/?u={u}#pricing | 免登入可看；`pricing_view` 事件在此送出 | **貼文不得直接導這頁**（六道關卡 ⑥：價格與結帳不放 github.io；正式網域上線與律師意見前，只當站內二次導流） | 不做貼文落點 |

**判斷（我的）**：

- 產業鏈剖析圖是整站最獨特的資產（競品多半只有資金面），訪客可看、不用登入，**最適合當「拉新」落點**；3D 與 ETF 現金流試算有登入門檻，**最適合當「拉註冊」落點**。兩類不要混在同一篇裡講。
- 訪客有「今日事件累計 5 次」與各種每日次數，**貼文導入後看到「用完」卡的比例要量**，卡太早出現會讓新訪客以為站壞了（見第六節指標）。

---

## 三、每週發文排程（交付 2）

### 3.1 規則

1. **保留每日盤前 08:20／盤中 12:00／盤後（法人＋融資融券一篇）為預設**，格式不動（`auto_post.md`）。
2. 另加「功能推廣欄位」：**每天最多 1 篇**，發在晚間 20:30（延續 `traffic_methods_1027` 的首發時段），不與盤後同一時段。第 1～2 週先 **每週 4 篇**（週二、週三、週四、週六），第 3 週起依第五節判準再決定加減。
3. `?u=` 規則：`th-<功能碼>-<yyyymmdd>`（Threads）、`ig-<功能碼>-<yyyymmdd>`（IG 輪播）、`igs-<功能碼>-<yyyymmdd>`（IG 限動；站內平台碼要加 `igs`，見第四節 4.4 的 B）。**功能碼固定 3～4 碼，對照下表**；同一天同一功能發兩個平台就各用各的平台碼。信心：高（規則本身）；站內報表要顯示中文名需補 `SRC_SLOT`（工時見第四節）。
4. 事件型貼文用事件碼加年月：`th-ev<事件>-<yyyymmdd>`，例如 `th-evfomc-20261029`。

| 功能碼 | 功能 | 落點（表二列號） |
|---|---|---|
| `f2d` | 產業鏈 2D 剖析圖 | 1／2／3 |
| `f3d` | 3D 剖析圖（CTA 寫「註冊後可轉 3D」） | 1／2／3 |
| `etfd` | ETF 配息行事曆 | 8 |
| `etfi` | ETF 現金流試算 | 10 |
| `etfl` | ETF 總覽 | 9 |
| `earn` | 財報／財經日曆 | 11 |
| `evfomc` `evoil` `evcpi` | 事件型（FED／油價／CPI） | 11 或 7 |
| `hot` | 熱門話題（第五節簡報挑出的） | 簡報指定 |

### 3.2 每週排程（以 2026-10-27 起這週為例）

| 星期 | 預設（不變） | 功能推廣欄位（20:30） | 觸發事件 | 落點與 `?u=` |
|---|---|---|---|---|
| 週一 | 盤前／盤中／盤後 | — | — | — |
| 週二 | 同上 | **半導體或 AI 伺服器剖析圖 2D**（輪流） | 固定欄位（無事件；若當天盤後提到該產業則順接） | `#industry/semiconductor`；`th-f2d-20261027` |
| 週三 | 同上 | **FED／財報／油價（事件欄，擇一）** | 10/28（美東）FOMC 決議，台灣時間 10/29 凌晨公布（`macro_events.yaml`，信心中）：10/29 晚發「昨夜 FOMC 看什麼」；無事件日改發 3D 剖析圖 | `#earnings`；`th-evfomc-20261029`；無事件日 `th-f3d-<日期>` |
| 週四 | 同上 | **ETF 配息行事曆或現金流試算（輪流）** | ETF 除息前 7 天（資料湖有除息日）；本月月底發「下月誰除息」 | `#etf/cal` 或 `#etf/inc`；`th-etfd-<日期>`、`th-etfi-<日期>` |
| 週五 | 同上 | — | — | — |
| 週六 | 盤前盤中盤後休市，不發 | **3D 剖析圖／產品剖析（影片）** | 固定欄位，休市日有時間發長內容 | `#industry/<鏈>/dg/<圖id>`；`ig-f3d-<日期>`、`th-f3d-<日期>` |
| 週日 | 不發 | 備援：熱門話題（第六節） | 簡報分數高於門檻才發 | 簡報指定；`th-hot-<日期>` |

### 3.3 事件觸發表（日期都是公開日程，**發文前須再查證當週實際日期**）

| 事件 | 觸發時機 | 發什麼功能 | 日期依據（信心） |
|---|---|---|---|
| 月營收公布 | 每月 10 日前（上市櫃公司法定期限）；發在 8～10 日 | 財經日曆＋產業鏈剖析（講「營收看哪幾段」，不點名個股） | 法定期限為常識，**未在本專案文件查到出處**，標中；`#earnings` 是否含月營收事件未核對 |
| 財報週 | 第三季財報法定公告期限約 11/14 前，11 月上旬至中旬 | 財經日曆 `#earnings` ＋ 對應產業剖析圖 | 期限未查證，標低；站內 `earnings.json` 有日程可直接用 |
| FOMC | 10/28（美東）、12/9（美東）決議日；前一天預告、當天晚間回顧 | `#earnings`（含 FED 事件） | `macro_events.yaml` 兩個來源摘要，未讀官方原文（中） |
| CPI | 11/10（2026 年 10 月數據） | 財經日曆 | 同上（中） |
| ETF 除息前 7 天 | 依資料湖除息日滾動；月配 ETF 每月都有 | `#etf/cal` | 資料來自網站既有資料（高） |
| 油價大漲 | 當天布蘭特單日漲幅達門檻（建議 ≥ 3%，**門檻是我的假設**） | 熱門話題簡報 → 產業鏈中的「能源／塑化」若站內有對應族群才推；沒有就不硬連 | 觸發偵測需資料源，見第六節；站內是否已有油價序列**未確認** |

**不同意可以否決的地方**見第八節。

---

## 四、盤前／盤中／盤後模板加「深層連結」：程式規格（交付 3）

### 4.1 目標

固定文的結尾網址，從「首頁」改成「當天內容對應的功能頁」。**一篇貼文只放一個網址**（`auto_post.md` 規則 4 不動），只換落點。

### 4.2 規格（輸入 → 輸出）

函式：`pick_landing(kind, snap) -> (route_hash, reason)`，放在 `scripts/social_snap.py`（盤前用 `scripts/social_premarket.py` 呼叫同一支，避免兩套）；`link_url()` 改成 `link_url(kind, ymd, platform, route_hash="")`，輸出 `SITE_URL/?u=...` + `#route_hash`。

| 輸入（當天資料欄位） | 判斷 | 輸出落點 | 備註 |
|---|---|---|---|
| `kind=intraday`，資金輪盤第一名族群 `gid` | 若該族群所屬產業鏈有剖析圖（半導體、AI 伺服器、一般電子等） | `#industry/<chain>`（或 `#industry/group/<gid>` 族群成分頁，擇一，**預設用鏈頁**） | 族群→鏈對照用 `groups.yaml` 的 `chains.order`；沒有對應鏈就退回 `#flow/rotation` |
| `kind=intraday`，無對應 | — | `#flow/rotation`（現行） | 保底 |
| `kind=close`，法人買超族群或熱力圖漲最多族群 | 同上 | `#industry/<chain>`；沒有就 `#market/inst`（現行） | 避免每天都導同一頁：同一落點**連續 3 天**就改選次高分 |
| `kind=premarket`，事件欄含 FOMC／CPI／財報 | 當天 `macro_events` 或 `earnings.json` 有事件 | `#earnings` | 優先權最高 |
| `kind=premarket`，美股收盤提到半導體／AI | 同盤中 | `#industry/semiconductor` | — |
| 當週為除息前 7 天內，且功能推廣欄位當天未發 | 資料湖除息日距今 ≤ 7 | `#etf/cal` | 僅在「功能欄位」那篇，不動固定三篇 |
| 任何情況 | 落點必須通過 `route_ok(hash)`：鏈 id 在 `groups.yaml`、剖析圖 id 在 `diagrams.js` 的 SLOTS | 否則退回首頁 | 避免導到「不存在的頁」（`traffic_methods_1027` 同條規則） |

### 4.3 輸出檢查（寫進 `tests/test_social_caption.py`）

1. 網址只有一個、`?u=` 在 `#` 前。
2. hash 路由必須在白名單（第二節表）。
3. 同一落點連續出現天數 ≤ 2。
4. 落點理由 `reason` 寫入 `state/` 的發文紀錄，週報用。

### 4.4 要改哪支程式、工時、負責 agent

| 項目 | 檔案 | 工時（估，依程式量；實際待實作回報） | 負責 agent |
|---|---|---|---|
| A. `link_url` 加 `route_hash`、落點白名單與保底 | `scripts/social_snap.py` | 2～3 小時 | `social-engineer`（若無此角色：前端／腳本工程 agent） |
| B. 站內 `SRC_SLOT`／`SRC_PLAT` 補新碼（`f2d f3d etfd etfi etfl earn hot ev*`、`igs`），讓報表顯示中文 | `site/account.js` | 0.5～1 小時 | 前端 agent（**公開功能的後台報表，改完同 commit 不需公告，管理者功能**） |
| C. 族群→鏈、事件→功能的選擇邏輯 `pick_landing` | `scripts/social_snap.py`（盤中盤後）、`scripts/social_premarket.py`（盤前） | 3～4 小時 | 同 A |
| D. 資料來源（除息日、財報日、`macro_events`）讀取接口 | 新小模組，讀 `data/`、`site/data/earnings.json` | 2～3 小時 | 同 A |
| E. 測試與 `auto_post.md` 改版（記 Andy 原話、同步 `test_social_caption.py`） | `tests/test_social_caption.py`、`auto_post.md` | 1.5～2 小時 | 同 A＋本單位審文件 |
| 合計 | | **約 9～13 小時（A～E）** | |

**判斷**：A＋B＋C 最小可用版約 **5.5～8 小時**，足以讓盤中盤後先換成產業鏈落點；D 讓事件型落點自動化，可晚一週。**先做 A＋B，再做 C**：沒有 B 的話報表分不出功能，會讓第五節的量測失效。

---

## 五、熱門話題擷取（交付 4）

### 5.1 合法可用的資料源

| 來源 | 能拿到什麼 | 合法性／可用性 | 信心與出處 |
|---|---|---|---|
| 站內 pipeline 新聞（鉅亨、TechNews、經濟日報 RSS） | 每日數十到數百則標題、分類、`codes` | 已在抓；**再散布授權未確認**。但「內部打分數、只輸出自己的話題清單」不算再散布，貼文只寫自己的整理＋來源名稱＋連結 | 高（`today_events_feed.md`）；授權標未確認 |
| 站內事件日程（`macro_events.yaml`、FRED 發布日、`earnings.json`、重大訊息） | FOMC、CPI、非農、財報、法說會 | 公開日程，自己維護 | 高 |
| Google Trends「Trending Now」RSS（`trends.google.com/trending/rss?geo=TW`） | 台灣當日熱搜詞、約略搜尋量、相關新聞 | 一篇 2026-10 的第三方開發者文章稱此端點回 200（測試國家為 US、GB、DE，**台灣未測**）；**非官方文件、可能變動、服務條款對自動存取的規定我沒查到** | 低～中。來源：[DEV 文章](https://dev.to/egrarobo/pytrends-trendingsearches-returns-404-get-google-trends-trending-now-from-the-rss-feed-2026-59ma)、[Trends 台灣頁](https://trends.google.com/trending?geo=TW&hl=zh-TW) |
| Google Trends 非官方函式庫（pytrends） | 關鍵字熱度 | 套件已封存、常 429；官方 API 為邀請制 alpha | 中。來源：[DEV：pytrends is dead](https://dev.to/datafabrik/pytrends-is-dead-3-ways-to-get-google-trends-data-in-2026-with-code-1i5i) |
| Threads 官方 Keyword Search API | 以關鍵字搜公開貼文；官方文件寫每位用戶 24 小時最多 2,200 次查詢；需 `threads_keyword_search` 權限（未核准時只回自己的貼文） | **官方 API，合法**，但**沒有專用「熱門趨勢」端點**；我們目前權限是否含此項**未確認**（`meta_perm_check_1026.md` 只查發文權限） | 中。來源：[Meta 官方文件](https://developers.facebook.com/docs/threads/keyword-search/)（摘要，第三方報 500 次／週，未核對） |
| 第三方爬蟲（Apify 等）抓 Threads | 熱門貼文 | **不用**：違反平台條款風險，且 `CLAUDE.md` 對爬取的原則是保守 | 高（我們的政策判斷） |
| 人工：Andy／GPT 幫手每天看 Threads 首頁推薦與熱搜 | 補上述自動源看不到的 | 合法，成本是人的時間 | — |

### 5.2 打分規則

每個候選話題 `score = 關注度分 × 關聯度分`，兩項各 0～3 分：

| 項目 | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| **關注度**（多源取最高） | 只出現單一來源 | ≥ 2 個新聞來源同日報導 | 進 Google Trends 台灣前 20，或出現在日程大事件（FOMC、CPI） | 兩者皆有，或財報／法說會當週的大公司 |
| **與網站功能關聯度** | 站內沒有對應頁 | 可連到總覽／熱力圖 | 可連到某產業鏈或 ETF 或財經日曆 | 站內有**同主題剖析圖或當日日程**（例如談 AI 伺服器財報 → `#industry/ai_server` ＋ `#earnings`） |

- 發文門檻：`score ≥ 4`（滿分 9）。每日取前 3 名給 GPT 幫手，**最多發 1 篇功能欄位**。**門檻 4 是我的假設**，第 2 週依成效修（見第六節判準）。
- 否決規則（任一成立即剔除）：只與單一個股買賣有關；涉及政治選舉或醜聞；來源僅一篇且為社群傳言；站內沒有可連的頁（關聯度 0）。
- 去重：同一話題 7 天內不重複推。

### 5.3 每日「簡報欄位」（給 GPT 幫手，每天一份）

建議產出位置：`docs/marketing/social_unit/daily_topics/<日期>_feat.md`（沿用既有資料夾；機器產出，人不用寫）。欄位：

| 欄位 | 內容 |
|---|---|
| `id` | `<日期>-<序號>`，與 `?u=` 對帳用（對帳鍵見 `traffic_methods_1027` 第六節） |
| `topic` | 話題一句話（自己的話，不抄標題） |
| `sources` | 來源名稱＋連結（至少 2 個，標明新聞／日程／Trends） |
| `attention` / `fit` / `score` | 兩項分數與乘積 |
| `landing` | 完整落點網址（含 `?u=` 與 `#路由`） |
| `hook_options` | 3 個鉤子方向（不是成品文案；成品由 GPT 幫手寫） |
| `form` | 建議形式：Threads 文字／IG 輪播／短影片／限動 |
| `red_lines` | 本篇禁區（見第七節）；例如「不放個股、不談漲跌預測」 |
| `data_to_cite` | 可引用的站內資料（欄位名、抓取日） |
| `status` | `draft`（預設，不自動發） |

**自動化現況（如實）**：目前**沒有**這支腳本（`today_events_feed.md` 第 4 點已寫明）。建議新增 `scripts/social_topics.py`（專案已有此檔名，需先讀確認現況，**我沒有讀過它的內容，未確認是否已做類似事**）擴充，工時 **6～8 小時**（讀新聞表打分 2h、日程對應 2h、Trends RSS 接入與備援 2h、輸出簡報與測試 2h），負責 agent：資料 agent＋`finance-content-editor` 審口徑。第一步（不寫程式）：Andy 或 GPT 幫手**每天人工挑 3 題**，照上表欄位貼進去，先跑一週看哪些欄位用不到。

---

## 六、量測（交付 5）

### 6.1 前提

`?u=` 寫入與 `land`／`pricing_view` 已在站內；`signup`、`trial_start` 由 Worker 算，**我沒讀到 Worker 原始碼，是否真有 `trial_start` 事件需先確認**（列第九節）。沒有確認前，判準以 `land → signup → pricing_view` 三段為主。

### 6.2 每個功能落點的指標

| 指標 | 算法 | 用途 |
|---|---|---|
| 進站數 | `land` 事件，依 `?u=` 的功能碼分組 | 引流效果 |
| 註冊率 | 該功能碼 `signup` ÷ `land` | **主指標**：哪個功能最能帶註冊 |
| 看價格率 | `pricing_view` ÷ `land` | 付費意願的前導指標（收款前只代表「對方案有興趣」） |
| 試用／預約率 | `trial_start`（或預約表單）÷ `signup` | 深度轉換 |
| 用完卡出現率 | 看到額度用完卡 ÷ `land`（需補事件，工時未估） | 檢查訪客門檻是否擋太早 |
| 貼文層 | Threads／IG 觀看、讚、回覆（`social_insights.py`） | 內容吸引力，與站內分開看 |

### 6.3 週報欄位（每週一，CEO 排程產出，不由 GPT 自評）

`週次｜功能碼｜貼文數｜平台觀看合計｜land｜land/貼文｜signup｜註冊率｜pricing_view｜看價格率｜trial_start｜備註（用完卡、異常）`，一個功能碼一行；另附固定三篇（盤前／盤中／盤後）當對照組。

### 6.4 判準

| 時點 | 判準 | 通過 | 未通過怎麼做 |
|---|---|---|---|
| **第 2 週末** | 每個功能碼 ≥ 2 篇、`land` 累計 ≥ 100 才判（樣本不足不判，延到第 3 週） | 功能欄位的 `land/貼文` ≥ 固定三篇中位數的 1.0 倍 → 繼續；`signup` ≥ 1 的功能碼 → 標「有註冊力」 | `land/貼文` < 固定三篇 0.5 倍：該功能碼換鉤子重測 1 週，不直接砍 |
| **第 4 週末** | 單一功能碼累積 `land` ≥ 500 才做註冊率比較（沿用 `traffic_methods_1027` 的 V5 樣本門檻） | 註冊率最高的功能碼 ≥ 2%（基準 2～3% 來自 `research_growth_1026`，信心低）→ 列為主推功能，頻率加倍；註冊率 < 1% 且 `land` ≥ 500 → **先改落點頁（引導文案、額度卡），不改貼文** | 兩個以上功能碼都 < 1%：回頭檢查 `?u=` 是否寫進註冊（對帳），再談內容 |
| 任一週 | 觸及驟降 50% 或人工檢舉 | — | 立刻停功能欄位，回到預設三篇（沿用 `traffic_methods_1027` 的停損） |

**判斷（我的）**：預期「ETF 現金流試算」註冊率最高（互動、有登入門檻、切身），「產業鏈剖析圖」進站數最高但註冊率偏低（訪客直接可看，沒有登入理由）。這是假設，不是已知，第 4 週用數字驗證，**不得在數字出來前宣稱哪個功能有效**。

---

## 七、法遵紅線（交付 6）

依 `launch_standard.md` 第二節第 10 條（收款前六道關卡）、`social_unit/charter.md`、`today_events_feed.md`：

1. **功能推廣文不點名個股買賣、不放股價推論**：不寫「某某值得買／要漲」「目標價」「進場時機」。產業鏈文只講結構、製程、供需關係，公司名只出現在「某環節有哪些公司」的資料性敘述時，且**不排名、不暗示優劣**。信心：高（政策）。
2. **歷史統計**（季節性、配息率）必須寫「歷史資料，不代表未來」；ETF 配息只寫已公告事實與日期，不寫「適合存」「穩賺」。
3. **付費功能在收款前只寫「可預約」**：貼文與落點頁都不得出現價格、「立即購買」、結帳連結；`#pricing` 不當貼文落點（關卡 ⑥：價格與結帳不放 github.io；關卡 ① 律師意見前只開預約）。
4. **3D、現金流試算有登入門檻**：貼文 CTA 要誠實寫「註冊免費帳號後可使用」，不得寫「免費使用」讓訪客以為免登入（會造成落點挫折與客訴）。
5. **新聞不整段複製**：只用自己的話整理＋來源名稱＋連結；不截圖別人的新聞全文（再散布授權未確認）。
6. **FED、油價話題**：只講「發生了什麼、什麼時候、站內哪裡看日程」，不預測升降息或油價走勢，不連到個股。
7. **簡報的 `red_lines` 欄位每篇都要填**，由 `finance-content-editor` 發前核對一次；`status` 預設 `draft`，不自動發。
8. 資料源授權（即時報價、FinMind 商用）**未確認**（關卡 ③）：功能推廣文不得引用即時報價數字或 FinMind 衍生的個股財務數字。

---

## 八、Andy 可能不同意的地方（一次否決）

| # | 我的建議 | 你可能想的 | 若否決，影響 |
|---|---|---|---|
| 1 | 功能欄位每天最多 1 篇、晚間 20:30，第 1～2 週每週 4 篇 | 想每天多發 | 增加量不等於增加引流；`traffic_methods_1027` 的實驗設計也是先守住量再放大 |
| 2 | 3D 貼文 CTA 寫「註冊後可轉 3D」，不隱瞞登入門檻 | 想寫成「免費看 3D」 | 訪客點進去 3D 鈕灰掉，退出率高，且有誤導風險 |
| 3 | 固定三篇的落點從首頁換成當天內容的產業鏈頁 | 想維持首頁（簡單） | 首頁不是你要的「真的引流」；但首頁保底仍在 |
| 4 | `#pricing` 不當貼文落點 | 想直接導價格頁 | 違反關卡 ⑥，且收款前沒有東西可買 |
| 5 | 油價漲 ≥ 3% 當觸發門檻 | 想用別的門檻或不自動觸發 | 門檻純屬假設，要換就換 |
| 6 | 統一用平台碼 `th`，不用 `threads` | 想用你例子 `threads-feat3d-...` | 會與既有 `th-*` 分成兩個來源，報表要合併 |

## 九、我沒查到／不確定的

1. **剖析圖完整 id 清單**：只確認 `ai_server`、`mlcc` 在 `diagrams.js` 的 SLOTS 內；其餘半導體等圖的 id 是否同樣掛上、叫什麼，**我沒逐條核對**。程式規格要求用 SLOTS 清單產生白名單，不手寫。
2. **訪客權限是否為線上實際值**：我讀的是 `plan_presets.js` 預設範本；後台「權限矩陣」可即時改，線上可能不同。
3. **`trial_start`、`signup` 事件在 Worker 是否真有輸出**：只讀到 `account.js` 註解，未讀 Worker 原始碼。
4. **Threads 關鍵字搜尋權限**：我們的 App 是否已核准 `threads_keyword_search`，`meta_perm_check_1026.md` 沒涵蓋；官方限額（2,200 次／24 小時）與第三方說法（500 次／週）不一致，以 Meta 文件為準，未核對。
5. **Google Trends RSS 台灣端點**：只有第三方文章說美、英、德可用，台灣未測；Google 對自動存取的條款我沒查到。
6. **月營收 10 日期限、第三季財報期限（約 11/14）**：憑一般常識，專案文件裡沒有出處。
7. **站內是否有油價序列、對應「能源／塑化」族群**：未確認，影響「油價大漲」事件能導到哪裡。
8. **`#earnings` 是否含月營收事件**：未核對。
9. **`scripts/social_topics.py` 現況**：存在，但我沒讀內容。
10. **新聞再散布授權**：沿用 `launch_gap_legal_1009.md` F2 的「未確認」。
11. **用完卡出現率**需要新增事件，工時我沒估。
12. **`auto_post.md` 與程式不一致**：文件寫盤中導 `#flow/rotation`、盤後導 `#market/inst`，但 `link_url` 實際只輸出首頁。以程式為準，改版時一併修正。

## 十、第一步（Andy 一個人做得到的）

1. 本週先不等程式：**今晚（10/27）20:30 起**，由 GPT 幫手依第三節排程手動發 1 篇「產業鏈剖析圖 2D」，網址手寫 `https://liguligu-puipui.com/?u=th-f2d-20261027#industry/semiconductor`，其他照舊。
2. 同時開工 4.4 的 A＋B（約 3～4 小時），讓 `?u=` 功能碼在後台看得見。
3. 第 2 週末照第六節判準看第一份週報。

---

## 補充（2026-10-27，Andy「照建議，全部執行」）：深層連結三個已知限制已補

1. **漏斗依功能分組**：Worker 多寫 `fx.<事件>`（細項＝功能碼，沒有記 `none`），管理區漏斗卡右上角「依平台／依功能」切換；各欄加總＝全站合計、註冊率不超過 100%。見 `docs/account_analytics.md`。
2. **落點連續 2 天就換**：發文流程把落點存到 social-snaps 分支 `state/landing_recent.json`（真的發布才寫回），`social_snap.py`／`social_premarket.py` 以 `--landing-json` 讀入。
3. **盤前 ETF 除息導 #etf/cal**：盤前讀資料湖 `etf_dividend_events`（只讀），未來 7 天內有熱門 ETF（`social_premarket.py` 的 `POPULAR_ETFS`，人工清單可改）除息就導 `#etf/cal`；總經事件（FOMC／CPI／財報）優先。
