# 會員、自選清單、使用統計、線上人數 —— 規格與事件清單

Andy 2026-09-27：「使用者透過 google 登入設定，目的是能紀錄線上使用狀況，新增每頁使用功能狀況，
更能知道哪個功能更受歡迎，新增線上人數，知道目前有誰使用，新增自選清單並且可以新增五個分頁」。

- 架構與取捨：DECISIONS #270
- 設定步驟（給 Andy）：`docs/login_setup.md`
- 後端：`workers/account-api/worker.js`（Cloudflare Worker ＋ Durable Object SQLite）
- 前端：`site/account.js`（登入、統計、線上人數）、`site/watchlists.js`（自選五分頁）、`site/admin.js`（管理頁 `#admin`）
- 存取控制測試：`node --test workers/account-api/tests/account.test.mjs`（19 條，含本文件與程式白名單一致性）
- 前端驗收：`python scripts/_uitest.py --sections 會員與自選五分頁,會員雲端路徑 --workers 1`

## 1. 使用統計怎麼記

- **只記次數**：每一筆是「台北日期 × 鍵 × 次數」，沒有任何識別碼、不存 IP、不存單次點擊的原始紀錄。
- 前端先在記憶體累加，**每 60 秒隨心跳送一次**（離開分頁時用 sendBeacon 補送），一次最多 40 個鍵、每鍵最多 +50。
- Worker 只收下面白名單裡的鍵，其他一律整批拒絕（`worker.js` 的 `VIEWS`／`EVENTS`，與 `site/account.js` 同一份，測試會比對）。
- 瀏覽器開「請勿追蹤」（DNT）或「全球隱私控制」（GPC）→ 完全不送。
- 彙總資料保留 **13 個月**（Durable Object 每小時的 alarm 刪掉更舊的）。

## 2. 頁面瀏覽（鍵 `pv:<頁面>`）

換到另一頁算一次；個股頁換一檔股票算一次；同一頁內部切換（例如切族群）不重算。管理頁本身不計。

| 頁面 | 對應網址 |
|---|---|
| `overview` | `#overview`（也包含空網址） |
| `flow` | `#flow` |
| `industry` | `#industry`、`#industry/<鏈>` |
| `heatmap` | `#heatmap`（含舊網址 `#themes`） |
| `market` | `#market` |
| `season` | `#season`（畫面上叫「週期統計」） |
| `delivery` | `#delivery`（含舊網址 `#tasks`） |
| `stock` | `#stock/<代號>` |
| `legal` | `#terms`、`#privacy`、`#disclaimer`、`#leave` |
| `watch` | 保留給之後若自選清單變成獨立頁（目前是面板，不會出現） |
| `other` | 認不得的網址 |

## 3. 功能事件（鍵 `ev:<事件>`）

每一個事件都要能回答「這個功能有沒有人在用」。認法是**委派監聽**（`site/account.js` 的 `HOOKS`），
不改每個功能自己的程式 —— 那些檔案別的 agent 正在改；代價是按鈕的選擇器改名時這裡要跟著改。

| 事件 | 什麼時候算一次 | 回答的問題 |
|---|---|---|
| `session` | 一個瀏覽分頁第一次心跳 | 一天大約有多少次造訪 |
| `session_login` | 同上，而且是登入狀態 | 造訪裡有多少是會員 |
| `login` | 登入成功 | 登入流程有沒有人走完 |
| `logout` | 按登出 | — |
| `search` | 在頂欄搜尋框按 Enter，或點搜尋建議 | 搜尋是不是主要入口 |
| `watch_add` | 加進任一自選頁 | 自選清單有沒有人用 |
| `watch_remove` | 從自選頁移除 | — |
| `watch_tab_new` | 新增一個自選分頁 | 五個分頁夠不夠、有沒有人用到第二頁 |
| `watch_panel` | 打開自選清單面板 | 面板入口找不找得到 |
| `stock_tab` | 個股頁下方分頁（營收／獲利／籌碼…）或手機個股分頁切換 | 個股頁哪個部分有人看 |
| `k_period` | 切 K 線週期（`#tfSeg`） | 多週期有沒有人用 |
| `ai_tab` | 切 AI 分析的面向（技術／籌碼／基本／消息） | AI 分析有沒有人點開細看 |
| `open_3d` | 剖析圖切到 3D | 3D 值不值得繼續投資 |
| `zoom` | 圖表放大視窗打開 | 放大功能有沒有人用 |
| `how` | 打開任何一個「?」說明 | 哪些圖需要解釋（高＝圖本身不夠直覺） |
| `theme_toggle` | 切深色／明亮 | — |
| `events_drawer` | 打開「今日事件」 | 事件欄有沒有人看 |
| `mtf` | 個股「四週期同看」 | — |
| `indicators` | 打開指標設定下拉 | — |
| `draw` | 打開畫線工具 | — |
| `m_seg` | 手機分段導覽切換 | 手機的分段是不是被當成主要導覽 |

要加新事件：`worker.js` 的 `EVENTS`、`site/account.js` 的 `EVENTS`（與 `HOOKS` 或呼叫 `TwTrack('名稱')`）、
本表三處一起改；`site/admin.js` 的 `EV_NAME` 補中文名。測試會抓三邊不一致。

## 4. 線上人數與「目前誰在用」

- 每次載入頁面一組隨機代碼（只在記憶體，重新整理或關掉就換一組，**不跨造訪追蹤**）。不放 `sessionStorage`：重新整理時舊頁面的「離開」會比新頁面的第一次心跳晚到，同一組代碼會把新頁面剛登記的在線紀錄刪掉（驗收實測抓到）。
- 分頁看得到時每 60 秒一次心跳；切到背景或關閉時送「離開」，Worker 立刻刪掉那一列。
- 150 秒內有心跳才算在線；超過 180 秒的紀錄每小時與每次心跳順手刪掉（「離線即刪」）。
- 一般訪客：頂欄看到「● N 人在線」（管理者可在 `#admin` 關掉，關掉後只有管理者看得到數字）。
- 管理者（`ADMIN_EMAILS`）：`#admin` 看得到登入者的名稱、email、在看哪一頁、最後動作時間；訪客只有人數。

## 5. 自選清單

- 最多 5 頁；每頁名字最多 12 字、最多 50 檔；**只存代號與清單名，不存張數、成本、損益**。
- 未登入：`localStorage` 的 `tw.watchlists`。舊的單一清單 `tw.watch` 第一次載入時搬進第 1 頁，搬完刪掉舊鍵。
- 登入後：雲端為準，本機快取 `tw.watchlists.u`。第一次登入把本機清單**合併**上雲（同名頁取聯集、不同名接在後面、
  滿五頁併進同位置那頁），成功後清空本機那份；登出時刪掉雲端快取、換回本機清單（共用電腦不會留下別人的清單）。
- 兩台裝置同時改：以版本號判斷，後到的那一邊收到 409 與雲端現況，畫面換成雲端版本並提示。

## 6. 存取控制（等同 Firebase 安全規則；逐條測試在 `workers/account-api/tests/account.test.mjs`）

| 規則 | 允許 | 拒絕 |
|---|---|---|
| R1 自選清單 | 帶自己權杖讀寫**自己那份** | 沒權杖、假權杖、改過 uid 或簽章的權杖；超過 5 頁／50 檔／代號格式錯；版本號不一致（409，不覆蓋） |
| R2 使用統計 | 任何人（含訪客）遞增白名單內的鍵，每鍵 1～50 | 非白名單鍵、0、負數、小數、超過 50、超過 40 鍵；**沒有任何給一般人的讀取端點** |
| R3 報表／線上名單／會員名單 | email 在 `ADMIN_EMAILS` 的已驗證帳號 | 訪客、一般會員；`ADMIN_EMAILS` 沒設時沒有任何人 |
| R4 線上總人數 | 預設公開（只有數字）；關掉後只給管理者 | 關掉後的訪客與一般會員 |
| R5 權杖 | HMAC 簽章有效、未過期（60 天，剩一半自動續）、使用者還在、版本號相符 | 刪除帳號後的舊權杖、過期權杖 |
| R6 登入 | 授權碼＋PKCE（S256）＋ state ＋ nonce ＋ 同瀏覽器 cookie；return 網址在白名單 | 白名單外網址、cookie 不符（別人的回呼網址）、aud／iss／nonce 不符、email 未驗證、過期 |
| 來源 | 白名單網站發出的 POST | 其他網站、沒有 Origin 的 POST（403） |


## 細項事件（2026-10-05 admin-v2）

跟上面的計數並存（舊計數不動），心跳多帶一個 `e2`：`[[頁面, 元件, 細項, 次數], …]`，每批最多 60 列、每列最多 +50。
Worker 存在 `ev2(day, page, comp, detail, n)`，只有「每天的次數」，**沒有任何識別碼**，保留 13 個月。

- 頁面：上面的頁面白名單（`viewOf`）。管理頁不記。
- 元件：`^[a-z][a-z0-9_.]{0,31}$` 的固定名字。
- 細項：族群名／股票代號／元件 id／象限名，**只取畫面上既有的選項**；不存使用者打的字（搜尋只記「有搜尋」）。
  Worker 再擋一次：≤ 24 字、不准 `@`、控制字元與 `< > " ' \``。

| 元件 | 細項 | 點位 |
|---|---|---|
| `view` | 股票代號 | 打開個股頁（換一檔算一次）|
| `tab.<分頁>`、`kp.<週期>`、`ai_tab`、`mtf`、`indicators`、`draw`、`zoom`… | 個股頁＝代號；其他頁空白 | 既有 HOOKS 擴充 |
| `how` | 卡片 id | 「?」說明 |
| `play` | 時間軸容器 id（`rotBack`＝資金輪動）| 播放鈕 |
| `quad` | 領先／改善／轉弱／落後 | 輪盤象限卡 |
| `filter_chain` | 產業鏈名 | 資金輪動產業鏈下拉 |
| `filter_group` | 族群名 | 族群下拉「勾上」 |
| `filter_group_open`、`filter_top10`、`filter_clear` | 空 | 篩選列 |
| `rank_bar` | 族群名 | 右側排行長條（app.js 新點位）|
| `clock_group` | 族群名 | 輪盤族群點（app.js 新點位）|
| `heat_tile` | 族群名 | 熱力圖方塊（app.js 新點位）|
| `search` | 空 | 搜尋 Enter |

新增點位只有 app.js 三處 canvas 點擊（`twT`），其餘都是 account.js 的委派監聽。
查詢：`/v1/admin/stats` 回 `e2`（期間內依 page/comp/detail 加總，可帶 `page` 只看一頁）。
會員造訪：登入狀態的 `ev:session_login` 另記 `visits(uid, day, n)`，`/v1/admin/perm/list` 回 `seen`、`visits`（近 30 天）、`expires`。

### 2026-10-05 流量觀測「分頁統計」新增的事件鍵（只記次數，不記身分；前端 `site/account.js`）
Worker 的頁面白名單（`VIEWS`）沒有 etf／explore／support／events，所以這幾頁一律記在頁面 `other` 底下、元件名帶前綴，管理區（`site/admin.js` 的 `PAGES`／`classify`）再歸回該頁。**Worker 不必改**；若之後要在 Worker 端直接分頁面，再把這四個加進 `VIEWS`。

| 元件鍵 | 頁面 | 細項 | 點位 |
|---|---|---|---|
| `sub.<子頁>` | flow／heatmap／industry／market | 空 | 換到子頁（rotation／sankey／inst、industry／theme、chains／chain／group、市場明細頁籤） |
| `etf.cat` | other | 類別名 | ETF 分類按鈕 `#etfCatSeg` |
| `explore.topic` | other | 題目 | （預留，選股策略題目點選；示範資料已涵蓋，前端點位待 explore.js 補）|
| `watch_tab_new` | watch | 空 | 自選「＋」新增分頁 |
| `watch.chart`、`watch.kline` | watch | 空 | 自選：點走勢圖、展開圖內切 K 線週期 |
| `support.fab`／`support.tab`／`support.faq`／`support.send`／`support.mail` | other | 分頁名／問題前 20 字 | 客服浮動鈕與面板 |
| `events.link` | other | 空 | 事件抽屜點事件連結（`events_drawer` 本來就有，管理區用它的「來源頁」當細項）|
| `ind` | stock | 指標名稱 | 技術指標面板勾上 |
| `draw.tool` | stock | 工具名稱 | 畫線工具列 |

### 管理區仍需 Worker 才能完整呈現的欄位（前端已先做好，預覽用示範資料；正式站目前顯示估算或「尚未提供」）
- **開站身分**（登入／訪客的甜甜圈拆「註冊會員＋各付費方案」）：Worker 的 `ev:session_login` 沒有分會員等級。目前前端用 `plans/get`＋`perm/list` 的名單人數比例估算（標「估算」）。要精準：心跳 `session_login` 改記 `session_tier:<plan id>`，或 `/v1/admin/stats` 回 `tiers: [{id, name, n, login}]`。
- **使用時段**（使用者分頁的每小時直條）：需要 `/v1/admin/stats` 回 `hourly: [24 個數字]`（期間內每天每小時的頁面瀏覽加總，台北時間）。沒有就顯示說明文字。
- **即時**（期間選單）：需要 `hours: [24 個數字]`（今天每小時瀏覽）；沒有時只畫 1 根（今天）。
- 範本刪除保護已在 `workers/account-api/worker.js` 檔尾（`plans/put` del → 409 `has_members`）；上正式站要先部署 Worker 再上前端。

### 圖表選型（流量觀測頁的「？ 圖表怎麼選」）
- 預設橫向排序長條：類別多、要比大小，長度最準。
- 圓餅／甜甜圈：只在 ≤ 5 類且加總 100%（登入／訪客開啟比例）。
- 散佈：只用在兩個數量的關係（個股被觀看次數 × 平均每次用幾次功能）。

## 族群權限鍵對照（features.js `grpKey`）
純小寫英數底線的 group_id 原樣 → `grp.<id>`；有大寫轉小寫；含中文的 `ind_*` 自動桶 → `grp.ind_x<FNV-1a 8 碼>`。上線後不要改算法。

| group_id | 鍵 |
|---|---|
| ind_ETF | `grp.ind_etf` |
| ind_半導體業 | `grp.ind_x4d6347d4` |
| ind_光電業 | `grp.ind_xaffe9bb6` |
| ind_電子零組件業 | `grp.ind_xb717244b` |
| ind_化學工業 | `grp.ind_x269acfc7` |
| ind_其他電子業 | `grp.ind_x88b93227` |
| ind_生技醫療業 | `grp.ind_x4ceef9e8` |
| ind_其他 | `grp.ind_xe82028fb` |
| ind_電腦及週邊設備業 | `grp.ind_x206d5a74` |
| ind_文化創意業 | `grp.ind_xdad9d3e5` |
| ind_通信網路業 | `grp.ind_xdca044c4` |
| ind_鋼鐵工業 | `grp.ind_x3737af8e` |
| ind_汽車工業 | `grp.ind_xdc531606` |
| ind_食品工業 | `grp.ind_x140977c9` |
| ind_電機機械 | `grp.ind_x1b8c31ca` |
| ind_綠能環保 | `grp.ind_xeff95aab` |
| ind_玻璃陶瓷 | `grp.ind_x84487036` |
| ind_建材營造 | `grp.ind_xacb9273e` |
| ind_資訊服務業 | `grp.ind_x9dadf523` |
| ind_紡織纖維 | `grp.ind_x060d3357` |
| ind_金融保險 | `grp.ind_x0686a15a` |
| ind_水泥工業 | `grp.ind_xd1d03aa6` |
| ind_貿易百貨 | `grp.ind_x5756834b` |
| ind_運動休閒 | `grp.ind_xd36b5780` |
| ind_橡膠工業 | `grp.ind_xde3e5aa8` |
| ind_居家生活 | `grp.ind_x2a747a56` |
| ind_塑膠工業 | `grp.ind_x94a13d58` |
| ind_電子通路業 | `grp.ind_x02e736c2` |
| ind_數位雲端 | `grp.ind_x3c577bd7` |
| ind_觀光餐旅 | `grp.ind_x786a931f` |
| ind_電器電纜 | `grp.ind_xfc41fa87` |
| ind_造紙工業 | `grp.ind_x3efb6a56` |
| ind_油電燃氣業 | `grp.ind_xb9888cd8` |
| ind_農業科技業 | `grp.ind_xa885935a` |

## 付費範本的價格與計費週期（2026-10-05 admin-v2b）

- 後端 `plans` 表多兩欄：`price`（整數新台幣，0～999999）、`period`（`month`／`year`／`once`）。舊資料庫啟動時用 `PRAGMA table_info` 判斷、`ALTER TABLE ADD COLUMN` 補欄，舊範本補成 `price=0`、`period=month`。
- `/v1/admin/plans/put`：`price`、`period` 可省略（省略＝沿用原值，只改開關的呼叫不會把價格洗成 0）；帶了就嚴格驗證，錯誤回 `bad_price`／`bad_period`（400），不默默修正。`/v1/admin/plans/get` 每個範本都回 `price`、`period`。
- 管理區「會員權限 → 付費會員」：選一個範本後可改「名稱」「價格（整數 NT$）」「計費週期（月／年／一次）」，範本按鈕顯示「名稱・NT$價格/週期」。名稱不寫死價格（定價範本預設「免費方案 0／基本方案 399／進階方案 799」，每月）。
- ★ **金流以 plan id 對價、價格以後端為準。** plan id（例如 `p399`、`p799`、`p<亂數>`）建立後不變，是日後金流（訂單、Webhook）對應方案的鍵；名稱與價格可以隨時改，不影響已指定的會員。前端顯示的價格只是顯示，結帳金額一律由後端依 plan id 查 `plans.price`，不可相信前端送來的金額。

## 管理區 v3：瀏覽次數上限、會員名單使用數據（2026-10-05 admin-v3）

Andy 看了 admin-v2 預覽說「弄得好複雜，看了不清楚」，管理區改成三個大分頁（訪客｜註冊會員｜付費會員）＋「＋」新增付費範本，每頁兩個子分頁「觀看權限」「會員名單」。後端（`workers/account-api/worker.js` 檔尾 admin-v3 區塊，只新增、包 prototype，既有函式不動）：

- **瀏覽次數上限 `plans.lims`**（JSON：`{功能鍵: 0～9999}`）。留空（沒有這個鍵）＝不限、0＝不能看、N＝每日 N 次。跟開關 `feats` 分開存。`/v1/admin/plans/put` 可帶 `lims`（省略＝沿用原值；壞值整批 `bad_lims` 400）；`plans/get`、`/v1/plans/public`、`/v1/perm/me` 都回 `lims`（`perm/me` 回的是生效範本的，過期的人退回免費會員的）。
  前端：`perm.js` 把 0 當成「關掉」（同一個鎖頭＋「升級查看」鈕）；`quota.js` 對 N≥1 計數 —— 個股頁、題材、族群頁算「看了幾個不同的」，其他頁算「這個瀏覽器分頁開過一次」。原本 sub-v1 的三個 `quota.*` 開關拿掉，改成 `stock.page`（整個個股頁）、`stock.ai`、`heat.detail` 的上限。
- **在線時間 `visits.ms`**：登入者每次心跳加上距上次加時的間隔（單次最多 120 秒；超過 150 秒沒訊號＝斷線，不補中間那段）。用 `users.ob`（上次加時）而不是每個分頁各算，同一人開三個分頁不會加三倍。
- **個人使用明細 `uev`**（uid、台北日期、頁面、元件、細項、次數）：只記登入者（訪客仍然只有不具名的 `usage`／`ev2`）；頁面瀏覽記成 `comp='_pv'`。保留 90 天、刪除帳號一起刪、只有管理者讀得到（隱私權政策第二條已加「使用紀錄（登入後）」一列）。
- **`/v1/admin/members`**：一人一列（登入過的＋設定過的），帶 方案、付費與否、加入／到期、最後上線、累計在線、近 30 天造訪／活躍天數／頁面瀏覽、最常用的功能 Top3、最常看的股票 Top3、狀態。**`/v1/admin/member/detail`**：各分頁瀏覽、功能次數 Top 15、常看股票 Top 10、近 14 天每日（造訪、在線、瀏覽）。
- 相容遷移：`plans.lims`、`visits.ms`、`users.ob` 用 `PRAGMA table_info` 判斷再 `ALTER TABLE ADD COLUMN`，`uev` 是新表；舊資料原封不動、重啟不報錯（`tests/v3.test.mjs`）。
- `/v1/quota/hit` 的功能鍵放寬成任何功能鍵（原本只收 `quota.*`）。
