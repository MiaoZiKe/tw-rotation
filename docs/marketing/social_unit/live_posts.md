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

### 版型（Andy 10-20：「風格專業點、搭配截圖色調」「標題就是這功能」）
財經終端／券商 App 風：頂端品牌列（比比小 logo＋「哩股哩股」＋右側日期時間膠囊 `MM/DD HH:MM`，等寬數字）→ 圓角細框卡片（粗體標題＝功能名稱本身＋小字副標、說明文字、截圖、備註）→ 底部細資料來源列。配色直接取自 `site/index.html` 的 CSS 變數：淺色（預設，跟截圖一致）與深色兩套，`--frame light|dark`。畫面與貼文文字一律不出現「即時」字樣（網站截圖裡自帶的字樣除外；能藏的藏、畫布內的裁掉）。

### 盤中（kind=intraday），順序＝Threads 輪播順序
| # | 片段 | 頁面 | 說明 |
|---|---|---|---|
| 1 | rotation-wheel（資金輪盤） | `#flow/rotation` | 只截輪盤圓盤＋四角象限標籤；上方四行「領先／轉弱／改善／落後：前 5 個族群 等 N 個」，名稱讀自輪盤的象限卡（點開各象限讀清單） |
| 2 | rotation-rank（族群資金排行） | 同上 | 只截長條圖 |
| 3 | sankey-tree（資金分流樹） | `#flow/sankey` | 只截樹狀圖；下方備註「流入前五／流出前五」，數字讀自右側排名卡兩個分頁原文 |
| 4 | heat-industry、heat-theme（熱力圖） | `#heatmap/industry`、`#heatmap/theme` | 要等 frontend 做好即時；沒即時就不發 |
| 5 | market-index（大盤走勢） | `#overview` 的 `#m3Frame` | 按卡片上的 `.livetg` 即時開關；狀態字出現「連不到…」就判失敗不發 |
| 6 | market-breadth（漲跌家數） | `#market/updown` 的 `.mktdist` | 按 `#mktMode` 的「⚡ 即時」；`#mktLive` 沒出錯才發 |

### 盤後（kind=close）：法人連續買賣超
法人資料要收盤後證交所公布才有，沒有即時版，所以另一篇發，不放進盤中那篇。投信、外資、合計各一張（手機版切「排行」畫法，買超、賣超各留前 7 列）。`inst-today`（當日三大法人買賣超卡，另派人做，`data-snap="inst-today"`）頁面上沒有就跳過。

## 規矩
- 亮色主題；同意橫幅、導覽、客服比比等固定浮動元素截圖前一律藏起來，截圖保留頁面上原有的免責字樣。
- **即時沒套上就不發**：盤中那幾張要等狀態字不再是「抓取中／抓不到」才截；沒套上的略過，不拿盤後舊圖冒充。
- **非交易日看資料判斷**：盤中看即時報價回應裡的成交日 `d` 是否＝今天，並限定台北 09:00～13:35；盤後看網站 `meta.json` 的 `inst_date` 是否＝今天。不用執行當下的星期幾。
- 貼文文字 4 行：標題與時間、重點一句（從頁面讀「資金佔比增加最多／減少最多」那行，或連買前三名，原文照抄）、免責一句、網址。
- 版面元素（標題、截圖、免責、網址）兩兩不得相交，超出畫布也不行；程式用瀏覽器量實際框與文字範圍，有一筆就結束碼 3、不發。

## 排程（台北時間；GitHub cron 用 UTC）
| 時段 | 台北 | UTC cron |
|---|---|---|
| 盤中 | 09:35 | `35 1 * * 1-5` |
| 盤中 | 11:05 | `5 3 * * 1-5` |
| 盤中 | 13:05 | `5 5 * * 1-5` |
| 盤後法人 | 接在「每日盤後管線」每一輪結束之後 | `workflow_run` |

盤後為什麼接管線而不是固定時間：三大法人傍晚才落地（`daily.yml` 台北 18:30 那輪 `phase=full` 才有，15:30 那輪只抓價量）。GitHub 排程常延遲數十分鐘，固定時間可能抓到舊資料。接在管線結束（資料已部署到網站）之後，再用 `inst_date == 今天` 把關；一天三輪都會接到，但 `social-snaps` 分支上有 `state/close-<日期>` 標記就跳過，只發一次。

## 即時閘門（不用任何登入權杖）
即時是管理者功能（`site/livegate.js`）。Actions 裡的做法：checkout 的 `site/` 在 `127.0.0.1` 起靜態伺服器，注入 `window.TW_LIVE_OVERRIDE = true`（只有 localhost 認的後門，正式站不受影響）；網站要讀的 JSON 用 `--data-url https://liguligu-puipui.com/data` 從正式站下載到本機 `site/data/`；報價請求（Worker／Deno 代理）由 Playwright 攔截，補上 `Origin: https://liguligu-puipui.com` 再轉發，回應補 CORS 標頭。即時沒套上就不發。

## 需要的 Secrets（只放 GitHub Secrets，不進 repo）
`THREADS_USER_ID`、`THREADS_ACCESS_TOKEN`、`IG_USER_ID`、`IG_ACCESS_TOKEN`（沒填＝發布程式自動 dry-run）。

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
