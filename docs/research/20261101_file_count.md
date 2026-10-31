# 部署檔數瘦身（2026-11-01）

背景：正式網域（Cloudflare Pages）單次部署上限 20,000 檔，`pages.yml` 設 19,800 擋線。主站 18,902 檔，只剩約 900 檔空間，
`site/data/flowcheck/`（每個交易日 +1 檔）等還在長。目標 ≤ 14,000 檔，留 6,000 檔成長空間，不改任何功能。

## 一、盤點（site/data，本機產出實測；主站實際檔數含 flowcheck 等較新的檔）

| 資料夾 | 檔數 | 大小 | 內容 | 怎麼讀 |
|---|---|---|---|---|
| `data/hist/` | 7,843 | 約 415 MB | 個股更舊的日 K，每檔 3～6 段、每段 1,000 根 | `chart.js` 的 `histFetch`（使用者往左拖才讀） |
| `data/lab/` | 3,664 | 約 180 MB | 交易練習室的標的資料（c／s 兩層） | 練習室 |
| `data/stock/` | 2,529 | 約 382 MB | 每檔個股頁 JSON | `App.load('stock/<代號>')` |
| `data/logos/` | 1,720 | 約 10 MB | 64×64 公司 Logo PNG | `<img src>` |
| `data/m60/` | 1,655 | 約 140 MB | 每檔 60 分 K | `industry.js` |
| `data/` 頂層 | 49 | 小 | 各頁共用 JSON | `App.load` |
| `site/` 其他（brand、lab、m4、dg、tc…） | 約 340 | 約 15 MB | 前端程式、素材 | 頁面 |
| 部署時才產出（flowcheck 等） | 約 1,100 | — | 流向驗證 | 流向驗證頁 |

結論：**hist 一類就佔 41%**，而且它是「同一檔股票的多段」被拆成多個檔，是最划算的下刀處。

## 二、方案比較

| 方案 | 省多少檔 | 前端改動 | 風險 |
|---|---|---|---|
| A. 個股 JSON 依代號每 50 檔合一包（原任務假設） | 約 2,480（stock 2,529 → 約 50） | 每個讀 `stock/<代號>` 的地方 | 單包 約 8 MB，開一檔個股就要下載 8 MB，載入變慢 ＋ 付費分級（data-gw 逐檔計次）要重做，**不採用** |
| B. 每檔 hist 的各段合成一檔 `hist/<代號>.json` | 約 5,700 | **只有 `chart.js` 的 `histFetch` 一處** | 第一次往左拖多下載同一檔的其他段（gzip 後約數十 KB） |
| C. Logo 合併成圖集 | 約 1,700 | 全站所有 `<img>` | 改動面太大，之後再說 |
| D. lab 合併 | 約 3,000 | 練習室 | 還沒需要 |

選 **B**：一次只動一件事、前端只有一個集中函式、不動付費分級語意（單位仍是「代號」）、單檔大小仍小（3～6 段約 200～400 KB 未壓縮）。
單做 B 就從約 18,900 降到約 13,200，已達標；A、C、D 不做。

## 三、實作

- `pipeline/compute/stockpage.py`：新增 `pack_history` ／ `unpack_history`。格式 `{code, tf, chunk, pages:[p0,p1,…]}`，`pages` 每一項與原本 `p<N>.json` **逐欄相同**（page／prev／from／to／bars／code／tf）。
- `pipeline/build_payload.py`：寫 `hist/<代號>.json`（舊的 `hist/<代號>/` 目錄順手清掉）；`hist/index.json` 不變。
- `site/chart.js`：集中在 `histFetch(code, n)`；第一次整份讀進來放進快取，之後每一段從記憶體拿，使用者仍是往左拖一段接一段；`prev === null` 的收手邏輯不變。
- `workers/data-gw/tiers.js`、`pipeline/datagw_tiers.json`：分級規則改成同時接受 `hist/<代號>` 與舊的 `hist/<代號>/p<N>`（兩份字串一致，單位仍是代號，額度不變）。
- `.github/workflows/pages.yml`：保留 19,800 擋線；新增一行印出各大類檔數（hist／stock／m60／lab／logos／flowcheck…）。
- 預覽版（`preview/*`）：資料讀正式站，正式站部署前預覽會讀到舊格式的 hist（404、只影響「往左拖載入更早 K 棒」）；部署後即恢復。

## 四、驗證

- 對本機真資料（2,097 檔）逐檔「舊 p0..pN → pack → unpack」比對：不一致 0 檔。
- pytest：新增「合併後每一段與原本一致」測試。
- 真瀏覽器：個股 2330 日線反覆縮放拖曳，只打 1 次 `hist/2330.json`、依序載入到 2000-01-04（共 6 段）後提示「已經到最早一筆」，無 hist 的 404。

## 五、結果檔數

見 `pages.yml` 新增的「檔數分類」行（每次部署都印），部署後實測數字見回報。
