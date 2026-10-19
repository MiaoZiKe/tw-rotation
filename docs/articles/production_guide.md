# 精選文章／短影片「產出佇列」作業手冊（2026-10-16）

Andy 10-16：「claude 指負責產出文章，內容……下方是我有功能可以點選清單內主題，點選後我可以再次點選產生精選文章，或是短影片」。

> ★ 2026-10-17 起：**排程與撰寫 agent 先照 `docs/articles/fast_path.md`（省 Token／省時間的快速流程）**；這份手冊只在卡上沒寫到時 grep 對應段落查。排程改成每小時開新對話、只在台北 08:05～23:05 跑（Andy：「改排程」）。
> ★ 2026-10-17 起：佇列裡 `kind: "topics"`（管理區「＋ 新增主題」）與每天收盤後的主題更新，照 `docs/articles/topic_gen.md`；管理區的「產出進度」已併進「主題候選清單」（一個主題一列，進度欄就是進度條）。

## 流程

1. Andy 在管理區 `#admin/articles` →「主題候選清單」點一列 → 按「產生精選文章」或「產生短影片」（可附補充）。
2. 請求排進會員 Worker 的 `article_jobs` 表（`workers/account-api/articles.js`），狀態 `queued`。
3. `.github/workflows/article-jobs.yml` 每小時 :41 把未完成的請求同步成 **`data/_state/article_jobs.json`**（只有編號、主題 id、種類、標題、補充、狀態、時間）。
4. Claude 排程（**台北每小時 :05**；2026-10-16 起由一天三輪改成每小時，因為頻率設定可以選任何整點）`git pull` 後讀這支檔（頻率設定到點的請求已經由工作流排進來，見下一節）：
   - 空的 → 什麼都不做，直接結束。
   - 有 `queued` → 一次處理一筆（先文章後影片、編號小的先），步驟見下。
5. 文章上架（見下面「發佈」兩種路徑）後，`article-jobs.yml`（`site/articles/index.json` 有變就跑）看到 index 裡有同一個 `topic` → 自動標 `done`。
   ⚠ **索引項目一定要帶 `topic`**（新文章由 `scripts/article_publish.py` 自動帶；它沒帶就拒絕）。

## 自動排隊：產貼文頻率設定（2026-10-16 第 2 版）

Andy 10-16 第一版：「先都不要填，它為可動開關……開啟後，會依據我設定的週期、時段進行生產對應類別文章」。
第 2 版（同日晚）：「應該是可以選擇 日期 後面是時段以小時為單位……然後接者是產的類型選擇，啟用應該是這邊都選完才會輪到」。

管理區 `#admin/articles` →「文章主題」最下面「產貼文頻率設定」：由上而下 ① 日期（每週重複／指定日期）② 整點時段 ③ 類別篇數 ④ 加入排程（變成一條規則）⑤ 啟用。
設定存在會員 Worker（`article_schedule` 表，只有管理者能存；每次增刪規則、切開關都即時存），`article-jobs.yml` 每小時 :41 同步成 **`data/_state/article_schedule.json`**：

```json
{ "ver": 2, "enabled": true,
  "rules": [
    { "days": [1, 3, 5], "hours": [10, 14], "cats": {"news": 1, "intro": 0, "know": 1} },
    { "dates": ["2026-10-20", "2026-10-23"], "hours": [21], "cats": {"news": 0, "intro": 2, "know": 0} }
  ],
  "updated": "2026-10-16 21:40" }
```

- `rules[]`：最多 20 條，每一條**自己**帶日期、時段、篇數（不再有全域篇數）。
  - `days`：每週重複，1＝週一…7＝週日；`dates`：指定日曆日 `YYYY-MM-DD`。**一條規則只會有其中一個**。
  - `hours`：整點，0～23，**台北時間**（10＝上午 10:00、14＝下午 2:00）。
  - `cats`：這條規則在每個對得上的整點，每個類別要產幾篇（0～3）；news＝比比快訊、intro＝比比產業鏈、know＝比比知識。
- 舊的第 1 版（`slots`／`cats`）已經由 Worker 與 `scripts/article_jobs.py` 自動轉成第 2 版寫進這支檔，**只需要認第 2 版**。
- **到點排隊由工作流做，不是 Claude**（Claude 的 session 拿不到 Worker 機器鑰匙）：`article-jobs.yml` 每小時 :41 跑 `scripts/article_jobs.py`，同步完設定後
  1. `ver` 不是 2、`enabled` 不是 `true` → **一律不排**（Andy 關著就是關著）。
  2. 取台北「這一個小時與前一個小時」（GitHub 排程常晚十幾分鐘、偶爾跳一輪，多看一小時補得回來；更早的不補，免得剛加的規則把今天早就過去的整點一次排進來）。
  3. 逐條規則比對：`dates` 含那天、或 `days` 含那天星期，**而且** `hours` 含那個小時 → 命中。
  4. 命中的規則裡每個大於 0 的類別，依篇數各排一筆 `kind=article`，`topic_id`＝**`sch-<YYYYMMDD>-<HH>-r<第幾條規則>-<類別>-<第幾篇>`**（例如 `sch-20261020-14-r1-news-1`）。
     Worker 對同一個 `sch-` id **不論狀態（連已完成、已取消）都不再排** —— 同一小時工作流跑幾次都只排一次；Andy 在「產出進度」取消的也不會被補回來。
  5. 標題＝從 `site/articles/topics.json` 挑該類別**還沒上架、也還沒在佇列**分數最高的主題；`note` 寫「排程自動排入（規則 N，台北 日期 HH:00）；建議主題 <主題 id>」。
     候選用完時標題寫「排程：<類別>（候選主題已用完，Claude 自選）」、`建議主題 無`。
- **Claude 排程每小時醒來（台北每小時 :05）**，照下面「寫一篇精選文章」處理佇列。遇到 `sch-` 開頭的請求：
  - 類別取 id 裡那一段（news／intro／know）；`note` 有「建議主題 X」就寫 `topics.json` 裡 X 那一題；寫「建議主題 無」就**自己查證挑一個該類別的新主題**（快訊挑最近的新聞），不要硬湊。
  - `index.json` 那一筆帶 `"topic": "<這個 sch- id>"`（自動標完成靠它）**以及 `"from_topic": "<X>"`**（下次挑題才知道 X 用掉了；自選的就寫你挑的主題簡稱）。
- 關掉開關 → 下一次同步後 `enabled=false`，之後的整點不再排；**已經在佇列的項目照常處理**（要停請到「產出進度」按取消）。
- 指定日期的規則過了那些日期就不會再命中，留在清單上只是紀錄（管理區會標「已過期」）。
- 時間軸：整點到 → 當小時 :41 排進佇列（管理區「產出進度」看得到）→ 下一個 :05 Claude 開工。頁面上寫「到點後最多約 1 小時內，Claude 會自動把文章排進上面的產出進度」。
- 設定本身是存在 Worker 裡、排隊時直接讀 Worker 的最新一份，所以**整點前存好**就趕得上那個整點（不必等 `article_schedule.json` 同步進 repo；那支檔是給人與 Claude 看的紀錄）。

## 發佈：新文章全文只在會員後端（2026-10-16 防白嫖，Andy 批准「最小有效版本」）

Andy 10-16：已公開的 4 篇維持原狀（不改成免費試閱、不刪、不改寫歷史）；**從新文章起，全文不再放進 public repo**。原因：repo 是 public，
`site/articles/posts/<id>.json` 推上去的那一刻任何人都讀得到，畫面上的 Pro／Plus 分級擋不住直接開網址的人（評估：`docs/security/anti_freeload_1016.md`）。

| | 舊文章（目前 4 篇，維持原狀） | 新文章（從現在起） |
|---|---|---|
| 全文放哪 | `site/articles/posts/<id>.json`（public repo、靜態檔） | 會員 Worker 的資料庫（`article_body` 表；每天備份會一起帶走） |
| 索引 `site/articles/index.json` | 完整（標題、副標、摘要、標籤…） | **只有**標題、分類、日期、`topic`、族群、`reading_min`，加 `"src": "api"`。**不含摘要、副標、標籤** |
| 前端怎麼讀 | 直接抓靜態檔，次數存本機 | 登入後向 `/v1/articles/get` 取（訪客／註冊會員 403、Plus 累計 5 篇由伺服器計、Pro／管理者不限） |
| 怎麼辨認 | 索引項目沒有 `src` | 索引項目 `src: "api"` |

### Claude 寫完一篇新文章後怎麼上架（照順序，缺一不可）

1. 把全文 JSON（格式照下面「寫一篇精選文章」，**要帶 `id`、`cat`、`title`、`date`、`topic`、`reading_min`、`groups`、`blocks`…**）存到 **repo 以外**的地方（暫存區）。**絕對不要放進 `site/articles/posts/`、`docs/`、`data/` 或任何會 commit 的路徑**。
2. 執行 `python scripts/article_publish.py <全文.json>`：
   - 用機器鑰匙把全文傳到會員 Worker（`/v1/articles/jobs/bot` 的 `put_body`），再用 `list_bodies` **確認真的存進去了**；
   - 確認後**才**把「僅標題」的索引項目寫進 `site/articles/index.json`（所以不會出現「標題上架、全文沒上」）；
   - 全文檔在 repo 裡面、沒帶 `topic`、沒有機器鑰匙、上傳或確認失敗 → 一律不寫索引、離開代碼非 0。
3. `python scripts/article_publish.py --check`（公開檔洩漏檢查：新文章的索引項目不得帶 `summary`／`subtitle`／`tags`、`site/articles/posts/<id>.json` 不得存在；`pytest tests/test_article_public_guard.py` 也會跑）。
4. 只 `git add site/articles/index.json` → 推 main → `python scripts/deploy_wait.py --branch main` 印出 ✅ → 標 `done`（`article-jobs.yml` 看到索引有同一個 `topic` 也會自動標）。
5. **上傳被拒（`forbidden`／403）：不要退而求其次把全文推進 repo。** 把這個請求標 `failed`（原因：環境沒有上傳鑰匙），在回報裡寫明。

### 鑰匙怎麼來（2026-10-17 起已設好，不用再設）

- Andy 已在 **GitHub Secrets** 設 `ARTICLE_PUT_KEY`（部署 Worker 時寫進 Worker），並在 **Claude 雲端環境 → Edit cloud environment → Network secrets** 綁了 `tw-account.kcq01010909.workers.dev/v1/articles…` 這一筆。
- 所以 Claude 的容器**看不到也不需要**鑰匙：`article_publish.py` 不帶 `Authorization` 直接送，出口代理會自動補上；網址沒設 `ACCOUNT_API_URL` 就用程式裡的預設值。**不要再設環境變數、不要填假的佔位鑰匙**（10-17 填佔位字串被權限檢查擋下）。
- 快速自測：`python -c "from scripts import article_jobs as aj, article_publish as ap; print(aj.call(ap.DEFAULT_API, '', {'op':'list_bodies'}))"` 回 `bodies` 清單就是通的。
- 換鑰匙：GitHub 那筆改值 → 跑一次「部署 Worker（會員登入與使用統計）」→ Claude 環境 Network secrets 那筆按重新整理圖示貼同一串新值（兩邊要一樣）。

### 全文只存在 Worker：備份與復原

新文章的全文**不在 repo**，所以唯一的副本在 Worker 資料庫與每日筆電備份（`article_body` 已列入匯出清單）。復原用既有的還原流程（`tools/laptop/README.md`）。
Claude 寫稿時的全文檔（暫存區）容器回收就沒了——**上傳成功後不要指望它還在**。要改稿：從 Worker 取回（管理者登入後的 `/v1/articles/get`）、改完用同一個 `article_publish.py` 覆寫（同 id 覆蓋）。

### 兩種路徑如何並存（部署順序與回滾見 `docs/security/anti_freeload_rollout_1016.md`）

- 前端用 `src` 分流：沒有 `src`＝舊路徑（抓靜態檔、本機計數）；`src:"api"`＝新路徑。兩種可以同時出現在同一份索引。
- 舊前端（還沒更新的瀏覽器快取）遇到新文章：列表顯示標題；點進去會因為沒有靜態檔而顯示「暫時讀不到」——不會壞版、也不會洩漏內文。
- 舊 4 篇仍受前端分級（本機計數）；它們本來就是公開檔，擋的只是「一般人」。伺服器端的 Plus 5 篇額度**只計新文章**（舊 4 篇的本機計數不會同步給伺服器）。

## 標狀態

用 GitHub Actions 手動觸發 `article-jobs.yml`（`workflow_dispatch`）：

| 參數 | 值 |
|---|---|
| `mark_id` | 請求編號 |
| `mark_status` | `working`（開工）／`done`（完成）／`failed`（做不出來） |
| `result` | 完成時填文章 id 或影片路徑；失敗時填一句原因 |
| `stage` | （選填，2026-10-17 加）目前做到哪一格，見下表 |

開工前先標 `working`（Andy 也不能再取消）。

### ★ 每個階段開始時標一次（2026-10-17）

Andy 10-17（看著管理區「產出進度」）：「這邊一直顯示排隊中，但我不清楚他狀況如何，所以多一個進度條，並且備註目前的階段 安排？製作？發布？等等」。
管理區「進度」欄是一條進度條＋「階段・更新時間」，**畫的就是你標的 `stage`**。不標，Andy 只看得到「安排主題」停在 10% 不動。

**做法：每進入下一個階段，就用 `workflow_dispatch` 帶 `mark_id`、`mark_status=working`、`stage=<階段>` 標一次**（一篇文章大約 6 次，最後一次標 `done`）。

| 順序 | `stage` | 管理區顯示 | 進度條 | 什麼時候標 |
|---|---|---|---|---|
| 1 | `plan` | 安排主題 | 10% | 讀完請求、決定角度與大綱時（只標 `working` 不帶 stage 也會自動是這格） |
| 2 | `research` | 查資料 | 25% | 開始查證、找數據與來源時 |
| 3 | `write` | 撰寫 | 45% | 開始寫正文時 |
| 4 | `illus` | 插圖 | 65% | 開始畫圖表、剖析圖（`chart`／`illus` 區塊）時 |
| 5 | `review` | 驗收 | 80% | 跑驗收、截圖自己看時 |
| 6 | `publish` | 發布中 | 92% | 推上 main、等部署時 |
| — | （`mark_status=done`） | 已完成 | 100%（綠） | 部署成功；`result` 填文章 id。文章推上線後工作流也會自動標 |
| — | （`mark_status=failed`） | 失敗・卡在＜那一格＞ | 停在那一格（紅） | 做不出來；`result` 填一句原因。**失敗不用帶 stage**，會停在最後標的那一格，Andy 才看得出卡在哪 |

規則（Worker 端寫死，不用記也不會被亂填）：
- `stage` 只收上表 6 個字；打錯字（或填百分比）會被**忽略**、只標狀態，工作流記錄裡會印一行警告。
- 百分比是前端固定對照，**不能自己填數字**。
- 已經標過 `done` 或被取消的請求不能再改。
- 排隊中（還沒標 `working`）顯示「排隊中・下一輪 :05 開工」。

## 寫一篇精選文章

- 格式：照 `site/articles/posts/*.json` 既有幾篇（區塊型別：h、p、ul、callout、table、stocks、kpi、chart、flow、stack、steps、compare、illus、video、scene）。
- **★ `scene` 區塊：文章裡直接嵌站內 3D／2.5D 剖析圖**（2026-10-19 稽核 #11；Andy 10-19：「知識需要有該產品架構圖 2.5D 3D，可以從網站內素材拿」）：
  | 欄位 | 可用值 | 說明 |
  |---|---|---|
  | `kind` | `3d` `25d` | `3d`＝產業鏈頁的 3D 場景（`site/three3d.js` 的 `SCENES`，可旋轉、點零件）；`25d`＝題材等角剖析圖（`site/themes3d.js`，點環節亮起、點代號進個股頁）。其他值整塊不畫 |
  | `id` | 小寫英數底線（2～40 字） | 圖 id，**一律從 `docs/articles/diagram_inventory.md` 查**（第一節 3D、第二節 2.5D）；格式不對整塊不畫，站內沒有的 id 顯示「暫時載不出來」＋連到站內頁 |
  | `title` | 字串 | 圖的標題（寫結論，例「HBM 是 8～12 層 DRAM 疊在邏輯晶粒上」） |
  | `caption` | 字串（選填） | 圖下一句話（看哪裡、怎麼操作），右邊自動附「在站內完整頁面看 ↗」 |
  ```json
  {"t": "scene", "kind": "3d", "id": "hbm", "title": "HBM：8～12 層 DRAM 疊在一顆邏輯晶粒上", "caption": "拖曳旋轉，點一層看它是什麼。"}
  {"t": "scene", "kind": "25d", "id": "hbm_memory", "title": "從一顆 DRAM 到一條 HBM 模組", "caption": "點環節亮起，點代號看個股。"}
  ```
  - 行為：捲到才載入（沒捲到的讀者一行 3D 程式都不抓）；手機（≤ 640）先是靜態預覽＋「點開互動」，點了在原地展開；3D 依方案開關（`ind.3d`），沒開的身分看到一行說明＋連到產業頁。
  - 位置：放在三句話重點後的**鉤子圖位置**或「結構」那一節的第一張；每篇最多 2 塊（3D 一塊、2.5D 一塊），算進圖數（算「其他圖」，不算數據圖）。
  - 有 `scene` 就不必再用 `illus` 重畫同一個產品（`visual_playbook.md` 1-3 第 2 步改為選做），`site_links` 第一個仍放該圖的路由。
  - 驗收段落 `文章3D區塊1019`（1440／390：捲到才初始化、3D 畫布有像素、手機預覽與點開、2.5D 點環節、壞 id 不壞頁、390 第一屏看得到第一個視覺區塊）。
- **手機第一屏（2026-10-19 稽核 #10，前端已做）**：≤ 640 的文章頁，副標、相關族群、標籤、摘要收進一顆「導讀・相關族群」（預設收起，點了展開、記住），麵包屑收掉；桌機不變。撰寫端仍要照 `visual_playbook.md` 第 1 節第一屏預算（`ul` 後緊接鉤子圖）。
- **`chart` 區塊（ECharts）欄位**（2026-10-17 加 `signed`／`refs`／`bands`；Andy：「觀眾大多為視覺系生物，對圖片圖表敏感度高於文字」）：
  | 欄位 | 可用值 | 說明 |
  |---|---|---|
  | `kind` | `bar` `line` `barline` `hbar` `range` | 直條／折線／直條＋折線／橫條／區間條；其他值一律當 `bar` |
  | `title` `unit` `y2unit` `note` `source` | 字串 | `y2unit`＝右軸單位（`barline` 的折線放右軸時用） |
  | `x` | 字串陣列 | 類別（日期寫成 `2024-10` 或 `2024-10-01` 這種遞增格式，`bands` 才能用不精確日期對上） |
  | `series` | `[{"name", "data": [...], "type": "bar"/"line", "axis": 0/1}]` | 最多 4 組；`range` 的 data 每格是 `[低, 高]` |
  | `highlight` | 索引陣列 | 要強調的那幾根（換成黃色＋描邊；`signed` 圖保留紅綠、只加描邊） |
  | `marks` | `[{"x": 類別, "text": "一句話"}]` | 指定那一根上的標註 |
  | **`signed`** | `true`（別名 `sign`） | **長條依正負上色：正＝紅（`--rise`）、負＝綠（`--fall`）、0＝灰**，標籤與提示框數字帶 `+`／`-`。漲跌幅、買賣超、年增率一律加。只套長條，同一張圖的折線照原本的色；`hbar` 加了就不會改對數軸 |
  | **`refs`** | `[{"y": 數值, "label": "文字"}]`（`hbar`／`range` 用 `"x"`） | **參考線**（虛線＋「文字 數值單位」）：大盤漲幅、均值、損益兩平、歷史高點。最多 4 條；直的畫在左軸 |
  | **`bands`** | `[{"from": 類別, "to": 類別, "label": "文字"}]` | **區間陰影**（灰色底，從 from 那一根左緣蓋到 to 那一根右緣）：升息期間、金融海嘯、去庫存。最多 4 段；標籤放在繪圖區上方（`hbar` 放在陰影右上角），太長自動截成「…」 |
  ```json
  {"t": "chart", "kind": "bar", "signed": true, "title": "外資買賣超（億元）", "unit": "億",
   "x": ["2026-10-13", "2026-10-14", "2026-10-15", "2026-10-16"], "series": [{"name": "外資", "data": [120, -80, 45, -230]}],
   "refs": [{"y": 0, "label": "多空分界"}],
   "bands": [{"from": "2026-10-14", "to": "2026-10-15", "label": "財報週"}]}
  ```
  壞值的處理（白名單，寫錯不會壞圖，只是那一筆不畫）：
  - `refs` 的值必須是數字或數字字串；空字串、`null`、布林、非數字都丟掉；離資料範圍超過「一個範圍寬」的也丟掉（寫錯單位的 1e6 不會把整張圖壓扁）。參考線會被算進座標範圍，刻度自動取整。
  - `bands` 的 `from`／`to` 先找一模一樣的類別；找不到時，只有類別是遞增日期字串才會取「落在區間裡的第一根到最後一根」（例：`2023-06-15`～`2023-09-30` 對到 `2023-07`～`2023-09`）；其他找不到的整段不畫。from 比 to 晚會自動對調。
  - `label`（也收 `text`）只當純文字：控制字元刪掉、`{` `}` `|` 換成全形（不會被當成 ECharts 富文字樣板）、參考線最多 24 字、區間最多 14 字；不進 HTML。
  - 沒帶這三個欄位的舊圖，畫出來的 option 一個字都不變（驗收段落「精選文章圖表擴充1017」逐字比對）。
- **★ 文章只要提到任何設備或實體產品，都要畫它的「大致剖析圖」（`illus` 區塊），不可以用平面色塊長條（`stack`）代替。**
  範圍不限於清單：晶片、封裝、板子、機櫃、散熱模組、電源、光模組、交換器、半導體製程設備（曝光機、蝕刻機、沉積設備）、測試設備、電動車、無人機、衛星……
  「大致剖析圖」＝**看得出外觀，也看得出內部主要組成**（剖開、拉出、開窗都可以），每個部位標「名稱＋一句話」，引線對到那個部位。
  Andy 原話（10-16）：「像是這種有提到特定元件，需要繪圖出來，更具像化，我指的就是這種圖要穿差一點」「不只這些 是只要設備 都要繪製他的大致剖析圖」。
  `stack` 只留給沒有實體外觀、純概念的分層（例如商業模式的上中下游）。
  - **內建的兩種**（直接套）：
    | kind | 畫什麼 | parts.id |
    |---|---|---|
    | `cowos` | CoWoS-S 2.5D 剖面（GPU＋兩側 HBM 堆疊、微凸塊、矽中介層含 TSV／重佈線、C4、ABF 載板、錫球、主機板） | `gpu` `hbm` `ubump` `interposer` `c4` `abf` `bga` `board` |
    | `rack` | 液冷 AI 機櫃拆開看（電源架、運算托盤、拉出的托盤上的冷板與水管、交換器托盤、分歧管、BBU） | `frame` `psu` `compute` `coldplate` `switch` `manifold` `bbu` |
    ```json
    {"t": "illus", "kind": "cowos", "style": 2, "title": "CoWoS 剖面：由上而下", "note": "示意圖，比例不是實際尺寸。",
     "parts": [{"id": "gpu", "label": "GPU 運算晶片", "sub": "一句話"}, {"id": "hbm", "label": "HBM", "sub": "一句話"}]}
    ```
    `parts` 只換說明文字；省略＝全部用預設說明，只列幾個＝只標那幾個。
  - **其他任何設備用 `kind: "custom"`，只寫 JSON、不用改程式**：用積木描述部件，畫在 `view` 大小的座標裡（左上是 0,0，往下 y 變大），
    `depth` 是「往後」的方向（預設 `[40,-24]`＝往右上，看得到上面與右側面）。陣列順序＝畫的順序，**後面／下面的先寫，前面／上面的後寫**。
    ```json
    {"t": "illus", "kind": "custom", "style": 2, "title": "氣冷散熱模組拆開看", "note": "示意圖，比例不是實際尺寸。",
     "view": [560, 330], "depth": [44, -26],
     "shapes": [
       {"part": "board", "type": "box", "x": 20, "y": 270, "w": 420, "h": 26, "mat": "pcb", "detail": "lines", "n": 2},
       {"part": "chip",  "type": "box", "x": 170, "y": 252, "w": 110, "h": 18, "mat": "chip", "detail": "grid"},
       {"part": "base",  "type": "box", "x": 150, "y": 234, "w": 150, "h": 18, "mat": "cu"},
       {"part": "pipe",  "type": "pipe", "mat": "cu", "r": 5, "points": [[180, 238], [180, 120], [200, 100]]},
       {"part": "fins",  "type": "box", "x": 140, "y": 90, "w": 180, "h": 120, "mat": "steel", "detail": ["fins", "screws"], "n": 18},
       {"part": "fan",   "type": "box", "x": 330, "y": 96, "w": 100, "h": 110, "mat": "plastic", "detail": "fan", "d": 0.5}],
     "parts": [{"id": "fins", "label": "散熱鰭片", "sub": "一片片薄鋁片，加大散熱面積"},
               {"id": "fan", "label": "風扇", "sub": "扇框＋扇葉＋輪轂", "anchor": [380, 150], "out": 40}]}
    ```
    | 欄位 | 可用值 |
    |---|---|
    | `type` | `box`（有厚度的方塊：x,y＝前面左上，w,h，`d`＝深度倍數 0～3）／`cyl`（直立圓柱：w＝直徑、h＝高）／`balls`（一排球：x 到 `x2`、y、`n` 顆、半徑 `r`；焊球、凸塊、滾珠）／`pipe`（管線：`points` 折線、`r`＝粗細） |
    | `mat`（材質＝顏色，深淺主題各一組） | `chip` `mem` `si` `cu` `solder` `abf` `core` `pcb` `steel` `tray` `dark` `battery` `cold` `hot` `plate` `cap` `glass` `plastic` `fiber` `magnet` `rubber` |
    | `detail`（識別特徵，`n`＝數量） | `layers`（分層，例如 DRAM 疊層、電芯）`vents`（散熱孔）`ports`（連接埠）`fins`（鰭片）`grid`（晶片格線）`lines`（內層線路）`vias`（通孔／TSV）`fan`（扇框＋扇葉＋輪轂）`terminals`（電池極柱＋正負號） |
    | `parts[]` | `id`（對到 shapes 的 `part`；圖上沒有的不列）、`label`、`sub`（一句話）、選填 `anchor:[x,y]`（引線起點，預設自動取部件右側）、`out`（引線先垂直走到這個 y 再往右，用來繞開別的部件） |
    不在白名單的值一律被略過或改成預設（JSON 的字串不會進到圖裡）。說明的編號由上而下自動排，引線自動對到那個部件；手機自動改成「圖右側編號＋圖下清單」。
  - 畫之前先查證結構（照 CLAUDE.md「有疑問先上網查」），**結構查不到的部分不要編**，`note` 寫「示意」；不畫任何公司的產品外觀、logo、商標。
    重點是**識別特徵**：風扇要有扇葉與輪轂、電池要有極柱、連接器要有接點、封裝要有凸塊與層次 —— 不是方塊越多越好。
  - 同一種設備會在很多篇出現時，再把它做成內建 kind（`site/artillus.js` 的 `KINDS`，參考 `cowos()`／`rack()`）。
  - **★ 2026-10-17 起新文章的 illus 一律寫 `"style": 2`**（Andy 10-17：「自動產精選文章，之後的圖需要再更細緻，顏色不要太單一，這部分跟動畫不合作，CEO 擬請動畫單位協助網頁單位製作，這次先不改」）。
    規格（色票、光影、細節密度、構圖、驗收門檻）全在 **`docs/articles/illus_style.md`**，動畫單位撰寫；這裡只列寫 JSON 要知道的。
    沒帶 `style` 的舊圖（已上架的 CoWoS、AI 機櫃、HBM…）照舊畫，畫面一個像素都不變（Andy：「這次先不改」）；要換新畫法要 Andy 點頭才補 `"style": 2`。
    | 第 2 版多的欄位 | 可用值 |
    |---|---|
    | `mat` 多 6 種 | `logic`（底層邏輯晶粒、控制晶片）`mold`（封裝膠體）`underfill`（底部填充膠）`gold`（金手指、接點）`tim`（導熱膏／墊）`ceramic`（陶瓷） |
    | `tone` | −2～+2 的整數：同一種材料、讀者要分得出的兩個零件（例如組好的 HBM `mem tone:-1`、拆開的 DRAM `mem tone:1`），兩者 ΔE00 要 ≥ 8；不能拿來湊色相數 |
    | `back` | 1＝後方零件（亮度 −0.04、彩度 ×0.9，做出遠近） |
    | `detail` 可以給陣列 | 例如 `["grid", "label", "seal"]`；多 10 種：`bumps`（頂面凸塊陣列，`nu`×`nv`、`bmat`＝`solder`／`cu`／`gold`）`traces`（頂面細走線）`label`（晶片刻印，不寫字、不畫 logo）`pads`（銅墊）`seal`（填充膠斜邊）`screws`（四角螺絲）`pins`（針腳／金手指）`hatch`（剖面斜線）`wires`（打線）`mesh`（濾網） |
    | `balls` | 預設兩排（後排錯開半格、較暗較小），`rows: 1` 只畫一排；**390 手機上球半徑要 ≥ 2.5px**（約 r ≥ 5.2，不夠就減顆數、加大、`note` 寫「凸塊放大畫」） |
    | `pipe` | 兩端自動加接頭（`ends: 0` 不加）、內側一條高光 |
    | `type: "guide"` | 拆開圖的虛線導引＋箭頭（`points` 折線，不用掛 `part`） |
    | `type: "wheel"`（10-17 晚） | 側視車輪：`x`,`y`＝輪心、`r`＝半徑；畫深色厚輪胎＋胎紋、輪框（`mat`＝輪框材質，輪胎固定橡膠）、碟盤、5 輻、輪轂＋5 螺帽、接地陰影。輪子要「接地」就讓 `y + r`＝地面 |
    | `type: "hcyl"`（10-17 晚） | 橫躺圓柱（馬達、氣瓶、噴口）：`x`,`y`,`w`,`h`；筒身由上往下受光、看得到右端面。`detail`：`fins`（散熱環，`n` 圈）`layers`（色帶）`screws`（端面螺栓）`terminals`（頂上接頭）。**馬達、氣瓶不要再用直立的 `cyl`** |
    | `type: "shell"`（10-17 晚） | 外殼剖面（車殼、機殼）：`points`＝近側輪廓（閉合、≤ 48 點）；`d`＝往深處擠出幾格 depth（0～8，看得到頂面與遠側殼）；`z`＝整個殼往深處推幾格；`op`＝半透明度（0.15～0.9）；`cut`＝開窗（≤ 3 個多邊形，窗內看得到殼裡的零件）；`open`＝哪幾條邊（第 i 點→第 i+1 點）不畫頂面（例如座艙開口）；`taper`＝兩端收窄（0～0.8，俯看時車頭車尾是圓的）；`layer`＝1 只畫後半（遠側殼＋頂面）／2 只畫前半（近側殼＋開窗）。**零件寫在 `layer: 1` 與 `layer: 2` 兩筆之間，就是「畫在殼內」** —— 不要再用細折線當車身、把零件擺在殼外 |
    | 構圖 | `view` 會依內容自動裁切；引線要能往右直接出去（把會被擋住的零件放右邊或上方、用 `anchor`／`out` 繞開），手機上編號要塞得進圖的高度 —— 零件 8 個時圖的長寬比最好接近 1:1 |
    不在白名單的值一律被略過或改成預設，JSON 的字串不會進到圖或樣式裡。
  - **插圖分工（每篇都照這個順序，規格第 5 節）**：
    | 步 | 誰 | 交什麼 |
    |---|---|---|
    | 0 | 文章作者（產文那一輪） | `docs/articles/illus/<文章id>/brief.md`：要畫的設備、要標的零件（id／名稱／一句話）、結構查證來源、「查不到所以只畫示意」的部分 |
    | 1 | **動畫單位**（`animation-director` 主導，可派 `bibi-illustrator`／`storyboard-artist`） | `sketch.md`（零件表：part／type／mat／tone／detail／大約位置）＋`sketch.svg`／`.png`：視角、哪些拆開剖開、配色配額試算 |
    | 2 | **網頁單位 `tech-illustrator`** | 依草稿寫 illus JSON（帶 `"style": 2`）；需要新 detail／mat 才改 `site/artillus.js`；跑量測與驗收（下面兩行指令）；截規格 4.1 節的圖（深淺 × 1440／390、兩張放大 3 倍、草稿與成品並排）放 scratchpad 的 `illus_<文章id>/` |
    | 3 | **審**：`animation-director`（細緻度、光影、配色配額）＋`art-director`（深淺主題、對比、不螢光）；結構有疑問加 `mechanical-engineer` | `review.md`：規格第 4 節逐條過／不過、「重疊檢查：程式 N 處 0 筆；人工 M 張 0 筆」那行、並排圖檔名 |
    | 4 | CEO | 用 Read 親眼看草稿與成品並排圖、深淺兩張 1440 圖，確認後才上架（沒親眼看過不准說好了） |
    同一張退件 2 次仍不過 → 回報 CEO，該篇先不上架插圖（不准降標準放行）。
    量測：`python scripts/illus_audit.py --post <文章 JSON 的本機路徑> --out <scratchpad>/illus_<文章id>/illus_audit.json --shots <同一個資料夾>`（全文在後端，JSON 放 scratchpad、**不要放進 repo**）；
    `❌` 就照它列的欄位改到全過。驗收段落：`python scripts/_uitest.py --sections 精選文章插圖v2,精選文章插圖積木1017 --workers 1`（第 2 版畫法、量測門檻、舊圖不變、主題切換、安全；後者驗 wheel／hcyl／shell）。
  - 算進圖數（10-17 起圖數改照 `docs/articles/visual_playbook.md`：快訊至少 3 張數據圖，全篇 4～6 張）。驗收：`python scripts/_uitest.py --sections 精選文章插圖1016,精選文章插圖v2 --workers 1`（深淺 × 1440／390：零件都畫出來、層序、凸塊大小、引線對到、說明不重疊不壓圖、滑過／點了真的變、通用 custom 與白名單）。
- **★ 3 分鐘看完（Andy 10-16：「不用太多，但需要重點 且直觀看得懂 3min 內可以看完」）**，每篇都照這幾條：
  1. **字數上限**：內文（h／p／ul／callout，不含圖表、表格、相關台股、來源、免責）**約 700～900 個中文字以內**；連圖表裡的字一起算，全篇控制在約 1,300 字。`reading_min` 寫實際值，**必須 ≤ 3**。
  2. **三句話重點**：第一個區塊固定是 `{"t":"h","text":"三句話重點"}` ＋ 三條的 `ul`；只看這三句就要懂這篇在講什麼（含最關鍵的數字）。
  3. **結論先行**：每個小節標題本身就是結論（例如「要看季、不看月：第三季創新高」），第一句話也是結論，理由放後面。不寫「前言」「先從名字拆起」這種鋪陳。
  4. **圖表數量（10-17 改，Andy：「以後內容都需要搭配圖表」「觀眾大多為視覺系生物」）**：照 `docs/articles/visual_playbook.md` 的視覺骨架，快訊至少 3 張數據圖、產業與知識類至少 2 張數據圖加 2 張其他圖，全篇 4～6 張，每張圖只回答一個問題；數字卡（kpi）最多 2 組、對照表（table）最多 1 張。同一件事不要用圖、表、段落各講一次。
  5. **圖說一句話**：`note` 只寫一句（口徑或「不代表個別訂單」這種必要警語）。
  6. 能用數字卡、圖、流程圖、對照表講的，就不要寫成長段落；段落一段 ≤ 120 字。
  7. 刪減時只能刪次要數字，**不能改值、不能新增沒有來源的數字**；`sources` 與免責聲明一律保留。
- **索引**：新文章**不要手寫**，由 `scripts/article_publish.py` 產生（只有標題、分類、日期、`topic`、`groups`、`reading_min`、`src:"api"`；**一定要帶 `topic`**，自動標完成就靠它）。
  ⚠ 下面幾條寫的是「全文 JSON 長什麼樣」；**全文本身不推 repo**，見上面「發佈」。舊文章（沒有 `src`）才是索引完整＋靜態檔那一套。
- **自訂主題（Andy 10-16：「也需要我填寫主題 產文章，例如 今天新聞 馬斯克飛天電動車介紹」，管理區有「自訂主題」欄）**：
  佇列裡 `topic_id` 開頭是 `c-<news|intro|know>-<時間碼>` 的，是 Andy 自己填的主題 ——
  類別取 id 中間那段（news／intro／know），標題與主題就是請求的 `title`（補充看 `note`）；
  `topics.json` 裡查不到這個 id 是正常的，不要當成錯誤跳過，要**從頭查證撰寫**。
  `index.json` 一樣要帶 `"topic": "<這個 topic_id>"`，才會自動標完成。同樣照上面「3 分鐘看完」的規則寫。
- id 格式：`<YYYY-MM-DD>-<news|intro|know>-<英文短名>`；類別依主題的 `cat`。
- 數字一律用資料湖（`data/`）或公司公告；查證規矩照 CLAUDE.md「有疑問先上網查」—— 只能用 WebSearch，摘要是線索不是事實，兩個獨立來源對得上才寫；來源日期寫原文日期，不寫查詢日。
- 不寫投資建議、不寫目標價；結尾保留免責。
- Andy 的補充（`note`）要照做；補充跟查證衝突時以證據為準，並在文末寫明。
- 驗收：`python scripts/_uitest.py --sections 精選文章1014 --workers 1`、`python scripts/_preview.py`；自己看 1440 與 390 截圖。新文章因為全文在後端，頁面驗收請用 `--sections 防白嫖後端1016`（起本機真的 Worker）的做法，不要為了驗收把全文放進 `site/`。
- 依上面「發佈」上傳全文 → 推**僅標題的索引** → `python scripts/deploy_wait.py --branch main` 印出 ✅ → 標 `done`（result＝文章 id）。

- **★ 影片區塊（10-17 Andy：「像是這種發佈會，他會有影片，最好是把影片也可以附上在文章中」「會有的區塊是可以直接播放」）**：
  `{"t":"video","provider":"youtube"|"x","id":"…","title":"…","source":"發布者","date":"YYYY-MM-DD"}`，文章裡直接嵌入播放器。
  - **來源（10-17 Andy 改：「不需要一定是官方，重點是影片內容，展示內容即可，即使是轉發，你判斷內容正確即可，不然之後的內容都需要這樣一個一個給你很浪費時間」）**：
    官方優先；沒有就用**內容是那場活動真實畫面**的上傳（媒體、創作者的轉載或剪輯都可以），Claude 自己找、自己判斷，**不必問 Andy**。
    排除：AI 生成／合成畫面、只有標題沒有現場畫面的評論片、標題與內容對不上的釣魚片、直播前的預告片（活動還沒發生）。
    判斷依據：標題與說明寫的是那場活動、兩次以上不同關鍵字的搜尋都撈得到同一支、片長合理（重點剪輯 5～25 分鐘）；`source` 寫上傳者，非官方就加註「轉載／剪輯，非官方」。
    只用平台自己的嵌入播放器（就是這個區塊），**不下載、不重新上傳**；之後若該影片被下架，前端只會顯示平台的「無法播放」，不影響文章。
  - Claude 的容器打不開 X／YouTube，只看得到搜尋結果的標題與網址：回報時要講明「依標題與多次搜尋判斷，沒有親眼看過內容」。
  - id 格式：YouTube 11 碼、X 貼文數字；格式不對前端整塊不畫。每篇最多 1 支，算進圖數（10-17 起圖數改照 `docs/articles/visual_playbook.md`：快訊至少 3 張數據圖，全篇 4～6 張）。驗收段落 `文章影片區塊1017`。

## 做一支短影片

- ★ **一定要是比比的角色動畫，不是投影片加小比比**（Andy 10-17 看完 CPO 那支：「為什麼不是動畫」）。派工給**比比動畫單位**（`animation-director` 統籌，`bibi-planner`／`bibi-animator`／`bibi-illustrator`／`bibi-review`），不要只派 `video-editor`；派工單要附 `docs/anim/動畫製作總提示詞_原文.md` 與 `docs/anim/bibi_library/index.md`、`docs/anim/GPT優化須知_比比互動.md`，比比是主持人：要有走位、指著圖解、和道具互動、表情隨台詞變，圖解本身也要動（不是整張卡片淡入）。`video-editor` 只負責最後合成、字幕、配樂與網站錄影。
- 規格與不重疊規矩：`docs/marketing/video_1010/layout_rules.md`（回報要有「重疊檢查：程式 N 幀 0 筆；人工 M 格 0 筆」）。
- 成品放 `docs/marketing/videos/<YYYY-MM-DD>-<主題 id>/`（直式 1080×1920 MP4＋封面），標 `done`（result＝資料夾路徑）。

## 傳給 GPT（IG 貼文／影片；純前端，不經佇列）

已上架文章每列有「傳給 GPT・IG 貼文」「傳給 GPT・影片」（手機＝下拉選類型＋一顆送出）。按下去＝**Andy 決定這篇要交接**：
前端（`site/gpthandoff.js`）讀該篇文章 JSON，組成 Markdown，開預填的 GitHub 新 Issue（label `social-handoff` 加 `gpt-ig-post` 或 `gpt-video`，
標題 `[社群交接] 日期｜IG 貼文｜文章標題`／`…｜影片｜…`），Andy 在 GitHub 按 Submit new issue 才算送出。不排隊、不碰 Worker、Claude 排程不處理這個。
內容只放文章已公開的部分；網址超過 8 KB 會自動省略站內連結／關鍵數據／來源，完整內容用頁面上的「複製完整交接內容」。

## 安全

- `data/_state/article_jobs.json` 在 public repo：管理區的補充欄已提示「請勿填個資」；寫入的欄位不含會員 uid／email。
- 機器鑰匙 `ARTICLE_BOT_KEY`＝`sha256("tw-article-jobs|" + CLOUDFLARE_API_TOKEN)` 前 48 字，兩支工作流各自算，不進 repo、不進 log（`::add-mask::`）。換 Cloudflare 權杖後要重跑「部署 Worker」。
- **全文絕不經過 public repo 的 Actions**：public repo 的執行紀錄與 `workflow_dispatch` 的輸入值任何人都看得到，所以 `article-jobs.yml` 只傳狀態（編號、狀態、文章 id），不傳全文；全文只走「Claude 容器 → 機器路由 `put_body`」。
- `put_body` 只認機器鑰匙（`ARTICLE_PUT_KEY` 最小權限，或 `ARTICLE_BOT_KEY`／`BACKUP_TOKEN`），不看 Origin、也不開放給任何網頁來源；鑰匙錯一律 403。`ARTICLE_PUT_KEY` 只能做全文的上傳／刪除／列出。
