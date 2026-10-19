# 生成主題候選（topics.json）—— Claude 排程照做（2026-10-17）

Andy 10-17（看著管理區「精選文章 → 主題候選清單」）：「幫我每天都下午收盤後三個類別都會更新 3 個主題，並且這邊也需要日期區分。並多新增一個新增主題 Btn，當我點擊，你會在最上新增最新主題，可以單選和多選分類，也可以我提供關鍵字你幫我生成主題」。

兩種情況會做這件事，做法相同，只差「幾類、幾個、有沒有關鍵字」：

| 觸發 | 從哪裡知道 | 類別 | 每類幾個 | 關鍵字 |
|---|---|---|---|---|
| **新增主題鈕**（佇列裡 `kind: "topics"` 的請求） | `data/_state/article_jobs.json` | `note` 的 `cats=` | `note` 的 `n=` | `note` 的 `kw=`（沒有就自選） |
| **每日自動**：台北週一～五 **14:00 之後的第一輪**排程 | `site/articles/topics.json` 裡**沒有** `added` 等於今天的主題 | 三類全做 | 3 | 無 |

每日自動的判斷：`python3 -c "import json,datetime as d;t=(d.datetime.utcnow()+d.timedelta(hours=8)).date().isoformat();print(any(x.get('added')==t for x in json.load(open('site/articles/topics.json'))['topics']))"` 印 `False` 才做；週六日、14:00 前不做。同一天已經有人按「新增主題」生成過（added＝今天）也算做過，不重複。

## 類別定義與內容要求（2026-10-19 Andy；排程每輪必讀）

Andy 原話：「比比知識都是需要介紹像是 IC 代工、HBM、SSD、CPO 等等題材；比比快訊需要挑大家更想知道的話題，像是為什麼費半跌這麼誇張、馬斯克電動車、11 月後的財報行情等等很多；裡面的內容如果是消息和知識，需要有對應影片介紹（盡量），產業鏈需要有供應鏈圖等等，知識需要有該產品架構圖 2.5D 3D 等等，可以從我網站內素材拿；知識優先把我素材擁有 3D 圖的先完成」。

| 類別 | 定義 | 選題規則 | 文章必備 |
|---|---|---|---|
| 比比知識 know | 介紹**一個產品／技術**（IC 代工、HBM、SSD、CPO、CoWoS、矽光子、液冷、BBU…） | **優先選 `docs/articles/diagram_inventory.md` 有 3D 圖的**；其次 2.5D；`format_hint` 寫「文章＋3D 圖」並在 `why` 寫用哪張圖。**不寫投資理財觀念題**（除權息、法人買賣超、本益比這類）：不出新題（舊題不動） | 該產品的**架構圖（2.5D／3D）**：從網站素材取 —— 放對應頁連結（圖 id 與路由查 inventory）＋該頁截圖，或用 `illus`（style:2）重繪；**盡量附一支講解影片**（`video` 區塊） |
| 比比快訊 news | **大家最想知道的熱門話題**（例：費半為什麼跌這麼兇、馬斯克電動車、11 月後財報行情） | 用 WebSearch 找**近一週討論度最高**的；不是單純的行事曆公告；同一事件已上架就換角度 | 數據圖 ≥ 3；**盡量附對應新聞／發表會影片** |
| 比比產業鏈 intro | 講一條產業鏈的環節分工 | 挑站內已有鏈／族群頁的 | **一定要有供應鏈圖**（`flow`／`stack` 區塊，或網站產業鏈頁截圖）；講環節，**不排誰受惠** |

法遵沿用 成長計畫 growth_plan_1018 第九節（檔案若不在 repo，以此處為準）：標題以**題材為主詞**，不寫「受惠股」「概念股」，不點名值得關注的個股。

## 解析 note（新增主題鈕）

格式固定：`cats=<類別,…>;n=<1～5>[;kw=<關鍵字>]`，例如 `cats=news,know;n=3;kw=CoWoS 產能`。
類別：`news` 比比快訊、`intro` 比比產業鏈、`know` 比比知識。Worker 已擋過格式，解析不了就標 `failed`（result 寫「note 格式不對」），不要猜。
`topic_id` 是 `gen-<時間戳>`，**不是**某一個主題；不要把它寫進 topics.json 或 index.json。

## 步驟（一次做完，token 上限 8 萬）

1. 新增主題鈕的請求：先標 `working`、`stage=research`（`article-jobs.yml` 的 `workflow_dispatch`，見 `production_guide.md`「標狀態」）。每日自動沒有請求，不用標。
2. **找題材**（只印要用的數字，不印整張表）：
   - 本站資料湖：`git pull` 後照 `visual_playbook.md` 第 3 節的 Python 算**近 1～5 個交易日**族群漲跌與外資／投信買賣超，挑前後各 3 名；題材成分用 `pipeline.compute.themes.membership()`（`pipeline/groups/themes.yaml`），漲跌同一套算法。
   - 財經新聞：WebSearch **最多 6 次**（例如「台股 今日 盤後 族群」「<關鍵字> 產能 2026」「法說會 本週」「經濟數據 行事曆 本週」）。只看得到摘要，數字要對得上本站資料或第二個來源才寫進 `why`。
   - 近期行事曆：一週內的法說會、FOMC、CPI、非農、台灣出口與外銷訂單公布日 —— 快訊類優先。
   - 有關鍵字時：全部主題都要跟關鍵字有關（例如 CoWoS 產能 → 快訊寫最新產能消息、產業鏈寫 CoWoS 上下游、知識寫 CoWoS 是什麼）。
3. **不准重複**：跟 `topics.json` 現有每一題、`site/articles/index.json` 已上架文章的 `title`／`topic`／`from_topic`、佇列裡的請求比對；同一件事換句話說也算重複（例如「CoWoS 是什麼」與「三分鐘看懂 CoWoS」）。
4. **寫主題**：每類照數量各寫一題，欄位（沿用 topics.json 既有的欄名，前端讀的就是這幾個）：

| 欄位 | 必填 | 內容 |
|---|---|---|
| `id` | ✓ | `<n／i／k>_<英數簡稱>`（news＝n、intro＝i、know＝k），全檔不重複，只用 `A-Za-z0-9._-`，≤ 40 字 |
| `cat` | ✓ | `news`／`intro`／`know` |
| `title` | ✓ | 照 `visual_playbook.md` 第 4 節標題公式，≤ 26 字；不寫「崩盤」「必漲」、不點名「值得關注」的個股 |
| `why` | ✓ | 理由一句：為什麼現在寫、讀者會問什麼；有數字就寫數字與日期 |
| `score` | ✓ | 1～5 的整數：5＝今天就該寫（時效＋本站有資料），3＝常青題，1＝備用 |
| `format_hint` | ✓ | `貼文`／`文章`／`兩者` |
| `added` | ✓ | 今天（台北）`YYYY-MM-DD` —— 管理區靠它把新主題排在最上面那一段 |
| `site_links` |  | 本站相關頁 hash，例如 `#industry/group/ai_adv_packaging`（要是真的有的頁） |
| `keywords` |  | 有關鍵字時寫進來（陣列），之後查得到這批是怎麼來的 |

5. **寫回**：新主題**加在 `topics` 陣列最前面**，`updated` 改今天；用 `json.dump(..., ensure_ascii=False, indent=1)` 寫，舊主題一題都不刪不改。
6. **推上線**：`git add site/articles/topics.json`（**只加這一支**）→ commit（繁中，引用請求編號或「每日自動」）→ 推 main → `python scripts/deploy_wait.py --branch main` 印出 ✅。
7. 新增主題鈕的請求：標 `done`，`result` 寫 `topics+<新增題數>`（例如 `topics+6`）。做不出來（例如關鍵字查不到任何可靠來源）標 `failed`，`result` 寫一句原因 —— **不要硬湊**。

## 自檢（推之前，10 秒）

- 新增題數＝類別數 × n（每日自動＝9）；每題 `added`＝今天、`id` 不重複、`cat` 在三類裡、`score` 是 1～5 整數。
- `python3 -c "import json;json.load(open('site/articles/topics.json'))"` 不報錯。
- 標題沒有法遵禁用字（`visual_playbook.md` 第 4 節「不准」那一段）。
