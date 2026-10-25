# 盤中／盤後即時貼文（Threads＋IG 限動）：截圖、排版、排程

Andy 2026-10-20 原話：「我需要在盤中發布當下即時狀況在 Threads 上和 IG 限動：1. 需資金輪盤、分流樹即時截圖，包含旁邊的長條圖；2. 需要串接自動發布系統；3. 排版只需要提供當前狀況，大家需要看」「熱力圖都需要具備即時功能，他也是需要截圖發布的內容」「也需要在盤後提供當天即時的法人買賣超狀況」。

## 檔案
| 檔案 | 做什麼 |
|---|---|
| `scripts/social_snap.py` | 開網站、切即時、截圖、排版（限動／Threads）、檢查重疊、產 `manifest.json` |
| `.github/workflows/social-live.yml` | 排程；跑 social_snap → 推圖到 `social-snaps` 分支 → 呼叫 `scripts/social_publish.py` |
| `scripts/social_publish.py` | 發布組寫的：讀 manifest、發 Threads 與 IG 限動（沒金鑰自動 dry-run） |

## 產出（每輪一個資料夾 `snaps/<kind>-<yyyymmdd-HHMM>/`）
- `story_<片段名>.png`：IG 限動 1080×1920，**手機版面截圖**（viewport 390、輸出 1080 寬）。一張截圖一張限動。
- `threads_<片段名>.png`：1080 寬，桌機寬（1440）截圖。同一批的圖按順序進同一則 Threads 輪播（上限 20 張）。
- `manifest.json`：`{"kind","taken_at","data_date","threads":{"text","images"},"story"}`，圖片路徑相對於資料夾。
- `layout_report.json`（每張的框、重疊檢查、截圖佔比、最小字）、`shots.json`（每個目標有沒有截成、為什麼略過）、`raw/`（原始截圖，不上傳）。

### 版型（Andy 10-20：「風格專業點、搭配截圖色調」「標題就是這功能」「版面填滿」）
財經終端／券商 App 風：頂端品牌列（比比小 logo＋哩股哩股）→ 圓角細框卡片（粗體標題＝功能名稱＋小字副標、文字塊、截圖、備註塊）→ 右下網址。沒有日期時間膠囊、沒有來源免責列：發布時間與免責改放 Threads 貼文文字。邊距約 24px，空間全給內容。配色取自 `site/index.html` 的 CSS 變數：淺色（預設）與深色，`--frame light|dark`。
- 資金輪盤：上方 2×2 四塊（改善／領先／落後／轉弱，排法照輪盤四個角；每塊標題＋前 5 個族群、一行一個）；截圖前取消「顯示軌跡／腳印／水波／掃描」，只留點與標籤。
- 資金分流樹：只截樹，根節點只寫「台股成交值」；下方兩塊「流入前五／流出前五」，只寫族群名。
- 熱力圖：桌機網頁版 1440，上＝產業「整個台股一次看」、下＝題材資金熱力，合成一張，Threads 與限動共用。
- 畫面與貼文文字不出現「即時」字樣；程式掃 DOM 文字，有就結束碼 4、不發（畫布內的字掃不到：輪盤底下那行用裁的，分流樹用 route 改截圖用瀏覽器載到的 flowtopo.js 把畫布文字改掉，網站本身不動）。

### 盤中（kind=intraday），順序＝Threads 輪播順序
| # | 片段 | 頁面 | 說明 |
|---|---|---|---|
| 1 | rotation-wheel（資金輪盤） | `#flow/rotation` | 只截輪盤圓盤＋四角象限標籤；上方四行「領先／轉弱／改善／落後：前 5 個族群 等 N 個」，名稱讀自輪盤的象限卡（點開各象限讀清單） |
| 2 | rotation-rank（族群資金排行） | 同上 | 只截長條圖 |
| 3 | sankey-tree（資金分流樹） | `#flow/sankey` | 只截樹狀圖；下方備註「流入前五／流出前五」，數字讀自右側排名卡兩個分頁原文 |
| 4 | heat（資金熱力圖：產業＋題材合成一張） | `#heatmap/industry`、`#heatmap/theme` | 要等 frontend 做好即時；沒即時就不發 |
| 5 | market-index（大盤走勢） | `#overview` 的 `#m3Frame` | 按卡片上的 `.livetg` 即時開關；狀態字出現「連不到…」就判失敗不發 |
| 6 | market-breadth（漲跌家數） | `#market/updown` 的 `.mktdist` | 按 `#mktMode` 的「⚡ 即時」；`#mktLive` 沒出錯才發 |

### 盤後（kind=close）：法人連續買賣超
法人資料要收盤後證交所公布才有，沒有即時版，所以另一篇發，不放進盤中那篇。投信、外資、合計各一張（手機版切「排行」畫法，買超、賣超各留前 7 列）。`inst-today`（當日三大法人買賣超卡，另派人做，`data-snap="inst-today"`）頁面上沒有就跳過。

### 盤後融資（kind=credit）：融資維持率、融資增減排行、融券增減排行（2026-10-21 從盤後法人拆出來，自己一篇；10-26 加第三張融券）
三張圖（Threads 輪播與 IG 限動各一）：`credit-ratio` 融資維持率、`credit-rank` 融資增減排行、`credit-short` 融券增減排行（網站「信用交易 → 個股排行」的「融券」分段，版面同融資排行：LOGO＋標題列、每列公司 LOGO、名稱、代號、數字）。文案多一行「融券增加 前三名；融券減少 前三名」。
**為什麼拆**：融資比三大法人晚很多才到齊 —— 整體市場融資（FinMind `TaiwanStockTotalMarginPurchaseShortSale`）約台北 21:30～22:00 才有當天；
上市個股融資（維持率的分子、增減排行）要到隔天清晨（回補工作流逐檔補進來）。綁在法人那篇時，法人一到那篇就發掉、當天標成已發，
融資卡一律顯示「資料未更新」被略過（2026-10-21 22:13 那輪只產出 5 張就是這樣：融資資料日 10/20、法人 10/21）。

**什麼時候發**：一樣接在每日管線每一輪之後（`workflow_run`，跟法人那篇同一個工作流、先後各跑一次），四個條件都成立才發（`social_snap.py` 的 `credit_ready`）：
1. `market_fut.json` 的融資最後一天＝網站最新交易日（`meta.json` 的 `data_date`）；
2. 那天的融資維持率算得出來（個股融資到了）；
3. 不是「部分估算」（個股融資只到一部分時數字還會變）；
4. 融資增減排行、融券增減排行也是同一天；
5. （2026-10-26）時間窗：只在該資料日收盤（13:30）後、**下一個交易日 09:00 開盤前**發（`social_gate.credit_gate`）；過了就不發舊的。

比的是「網站最新交易日」不是「今天」：個股融資常在隔天清晨才齊，那時最新交易日還是前一天，照樣發（實際多半是隔天 05:07／09:07／12:07 那幾輪 news 管線後發出）；
隔天 15:30 價量進來、最新交易日換天後，前一天的融資就不再發。防重複的鍵是 `credit-<融資資料日>`。
配套：`run_daily.py` 的 news 輪也補抓整體市場融資（以前只有 price／full 抓，晚上最後一輪錯過就要等隔天傍晚）。

## ★ 圖上不放任何備註與來源（2026-10-26，Andy：「所有的備註都不要顯示、不包含來源」）
適用所有社群貼文圖：盤前（`social_premarket.py`）、盤中、盤後法人、盤後融資融券（`social_snap.py`）。
- 圖上**不准**出現：資料來源、說明小字、註腳、免責小字、副標的資料日／計算方式、「部分估算」等說明句。
- **日期只留在標題列**；估算用標題括號簡短標示，例如「上市融資維持率（估） 10/22」。
- 免責與來源**只放文案最後一行**（`DISCLAIMER`）。
- 把關：`social_snap.py` 每片截圖前先藏 `NOTE_CSS`／`NOTE_TEXT`，截完再掃一次看得到的 DOM 文字（`NOTE_RE`：資料來源、僅供參考、不構成投資建議、計算方式、估算、資料日…），有一筆就**結束碼 5、不發**；`social_premarket.py` 的版型不畫副標、備註與免責。畫布（圖表 canvas）內的字掃不到，靠人工看圖。

## ★ 盤後融資融券當天晚上發（2026-10-26，Andy：「盤後也需要新增融資融券」）
融資篇（kind=credit，三張：上市融資維持率（估）、融資增減排行、融券增減排行；文案標題「台股盤後融資融券｜MM/DD」）只要融資融券資料日＝今天就發 ——
雲端 21:38 那輪 `daily.yml phase=full`（Cloudflare Worker 準時派）跑完含部署後，`social-live.yml` 的 `workflow_run` 會接上，matrix 依序跑 close、credit；
當晚沒到齊才在隔天開盤（09:00）前補發（沿用下面的把關，防重複鍵 `credit-<資料日>`）。

## ★ 資料一定要是當天（2026-10-26，Andy：「確保數據都是當天訊息」；程式 `scripts/social_gate.py`，測試 `tests/test_social_gate.py`）
事故：`snaps/close-20261022-2302` 文案寫 10/22、數字是 10/21；融資篇 10/26 凌晨還在發 10/22。
| 篇 | 什麼時候才發 | 日期取哪裡 |
|---|---|---|
| 盤後法人 close | 每張卡（inst-today、streak-foreign、streak-trust、fut-oi、retail-ratio）的資料日都＝今天（台北），且今天是交易日；任何一張不是 → 結束碼 10，log 寫「哪張＝哪天」 | 每張卡自己的資料檔最後一天（`data_dates()`）；圖上日期、文案日期、manifest `data_date` 三者一致 |
| 盤後融資 credit | 上面五個條件 | 融資資料日（三張卡都要同一天） |
| 盤中 intraday | 交易日 09:00～13:30，且即時報價回應的成交日＝今天（沒讀到任何成交日也不發） | 今天 |
交易日判斷：**休市日表 `pipeline/calendar/tw_holidays.yaml`（在表上一定不開，例 2026-10-26 光復節補假）＋資料本身有沒有今天**，不用 weekday 硬猜；
只有「下一個交易日幾點開盤」要往未來推，才用「休市日表＋週六日不開」。
**臨時休市（颱風等）**：例 2026-10-23（五）颱風全日休市、10/26 光復節補假、10/27 復市 —— 這種事前不在表上，所以以 **mis 即時報價（加權指數 `tse_t00.tw`）的成交日** 為準（`fetch_last_trade()`）：
排定開盤日過了 09:30 即時成交日還停在更早的日子 → 判定臨時休市（盤後法人 log 寫「臨時休市…不是資料缺漏」、不發；融資篇的「下一個交易日」往後順延，10/22 的融資在 10/26 仍可發）；
09:00～09:30 分不出「還沒成交」與「休市」→ 先不發；查不到 mis → 只靠休市日表，保守不發。事後把那天補登進 `tw_holidays.yaml`（10/23 已補）。`--force` 略過全部把關（只供測試，不可發布）；`--now YYYY-MM-DDTHH:MM` 可模擬時間。

## ★ 總開關 LIVE_ENABLED（2026-10-26）
repo 檔 `docs/marketing/social_unit/LIVE_ENABLED` **存在才真的發**；不存在＝一律 dry-run（即使 Secrets 有金鑰），workflow 與 `social_publish.py` 都會讀，log 寫「總開關關閉 → dry-run」。
Andy 說「開始發」之前**不建立**這個檔（`tests/test_social_publish.py` 有一條測試確認它不存在；開始發時連那條測試一起刪）。
`THREADS_USER_ID`／`IG_USER_ID` 空白但有權杖時，自動用權杖查帳號編號（Threads `GET https://graph.threads.net/v1.0/me?fields=id`；IG `GET https://graph.instagram.com/v24.0/me?fields=user_id,username` 取 `user_id`），log 只印末 4 碼、權杖不印。

## 規矩
- 亮色主題；同意橫幅、導覽、客服比比等固定浮動元素截圖前一律藏起來，截圖保留頁面上原有的免責字樣。
- **即時沒套上就不發**：盤中那幾張要等狀態字不再是「抓取中／抓不到」才截；沒套上的略過，不拿盤後舊圖冒充。
- **非交易日看資料判斷**：見上面「資料一定要是當天」那節（2026-10-26 起盤中時段是 09:00～13:30；盤後改成逐張比對每張卡自己的資料日，不再只看 `meta.json` 的 `inst_date`）。不用執行當下的星期幾。
- 貼文文字 4 行：標題與時間、重點一句（從頁面讀「資金佔比增加最多／減少最多」那行，或連買前三名，原文照抄）、免責一句、網址。
- 版面元素（標題、截圖、免責、網址）兩兩不得相交，超出畫布也不行；程式用瀏覽器量實際框與文字範圍，有一筆就結束碼 3、不發。

## 排程（台北時間；GitHub cron 用 UTC）
| 時段 | 台北 | UTC cron |
|---|---|---|
| 盤中 | 09:35 | `35 1 * * 1-5` |
| 盤中 | 11:05 | `5 3 * * 1-5` |
| 盤中 | 13:05 | `5 5 * * 1-5` |
| 盤後法人 | 接在「每日盤後管線」每一輪結束之後 | `workflow_run` |
| 盤後融資 | 同上（同一個工作流的第二篇；資料到齊那輪才發） | `workflow_run` |

盤後為什麼接管線而不是固定時間：三大法人傍晚才落地（`daily.yml` 台北 18:30 那輪 `phase=full` 才有，15:30 那輪只抓價量）。GitHub 排程常延遲數十分鐘，固定時間可能抓到舊資料。接在管線結束（資料已部署到網站）之後，再用 `inst_date == 今天` 把關；一天三輪都會接到，但 `social-snaps` 分支上有 `state/close-<日期>` 標記就跳過，只發一次。

## 即時閘門（不用任何登入權杖）
即時是管理者功能（`site/livegate.js`）。Actions 裡的做法：checkout 的 `site/` 在 `127.0.0.1` 起靜態伺服器，注入 `window.TW_LIVE_OVERRIDE = true`（只有 localhost 認的後門，正式站不受影響）；網站要讀的 JSON 用 `--data-url https://liguligu-puipui.com/data` 從正式站下載到本機 `site/data/`；報價請求（Worker／Deno 代理）由 Playwright 攔截，補上 `Origin: https://liguligu-puipui.com` 再轉發，回應補 CORS 標頭。即時沒套上就不發。

## 需要的 Secrets（只放 GitHub Secrets，不進 repo）
`THREADS_ACCESS_TOKEN`、`IG_ACCESS_TOKEN`（必填）；`THREADS_USER_ID`、`IG_USER_ID`（可空白，空白時用權杖自動查）。沒權杖或總開關關閉＝自動 dry-run。

### 跟 `scripts/ig_post.py`／`scripts/threads_post.py`（排程發文）會不會重複發？
不會發到同一則：那兩支是讀 `social/ig/queue/`、`social/threads/queue/` 裡 **人工核准（status: approved）** 的貼文檔，發 IG 一般貼文（單張／輪播）與 Threads 貼文；
這支 `social_publish.py` 發的是 `social_snap.py` 自動截的盤中／盤後圖（Threads 輪播＋IG **限動**），兩邊來源不同、防重複紀錄也分開（queue 檔的 status vs. `social-snaps` 的 `state/posted.json`）。
只有人把 snaps 的圖再手動放進 queue 才會「同一張圖發兩次」。總開關只管這支，不管排程發文那兩支。

## 發布與防重複
workflow 先把圖推到 `social-snaps`，再呼叫 `python scripts/social_publish.py --manifest <資料夾>/manifest.json --base-url <該輪資料夾的 raw 網址>`；發布程式把防重複紀錄寫在 manifest 旁的 `posted.json`，workflow 事前從 `social-snaps` 的 `state/posted.json` 帶進來、事後寫回去。真發布失敗該步驟 exit 1；dry-run／缺金鑰 exit 0。

## 本機示範
```
python scripts/social_snap.py --kind intraday --serve site --mock-live --force --out /tmp/demo/intraday
python scripts/social_snap.py --kind close --serve site --force --out /tmp/demo/close
```
`--serve site` 起本機伺服器並自動開 `TW_LIVE_OVERRIDE`；`--mock-live` 用假報價（容器打不開正式站與報價代理）；`--skip-live [目標名,…]` 只測版面（不要求即時，不可用在發布）；`--frame dark` 深色版型。需要先有 `site/data/`（`python -m pipeline.build_payload`，或加 `--data-url` 下載）。

## 還缺什麼
1. 熱力圖即時鈕與 `data-snap`／`window.TwSnapReady`（frontend-ui）：上線後對齊 `docs/social_snap_targets.md` 的名稱（`TARGETS` 的 `name`）；`social_snap.py` 會自動優先用 `[data-snap="<名稱>"]`。
2. 當日三大法人買賣超卡（`data-snap="inst-today"`）。
3. 正式站上實際跑一輪 dry-run，確認報價代理接受補上的 Origin、Playwright／字型安裝步驟沒問題。

## 文案與 caption.txt（2026-10-20）
- `scripts/social_snap.py` 每次輸出 `manifest.json` 的 `threads.text`，同一份文字另存 `caption.txt`（與 manifest 同資料夾）。
- 格式：第 1 行標題＋時間；每張圖一行重點（資金輪盤領先／落後、資金分流樹流入／流出、熱力圖漲跌最多含 %、漲跌家數），行尾附站內深連結，網址帶 `?utm_source=threads&utm_medium=social&utm_campaign=intraday_MMDD`（盤後為 `close_MMDD`；hash 路由的 query 放在 # 前）；倒數第 2 行免責；最後一行 hashtag。
- Threads 單則上限 500 字：網址以實際字元數計；上限 480，超過就把每行列的名稱 3→2→1 個縮短。
- **IG 限動 API 不能附文字與連結貼紙**：限動只發圖，caption.txt 給 Andy 手動貼（連結貼紙要在 IG App 內手動加）。
- 法人頁路由常數 `ROUTE_INST`（目前 `market/streak`），日後改 `market/inst` 只改這一處。
