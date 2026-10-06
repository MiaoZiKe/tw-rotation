# 付費資料閘道 data-gw：分級盤點與三階段計畫（2026-10-06，security-privacy）

> 依據：`docs/security_review_1006.md` 2-2～2-4（方案）；Andy 10-06 19:10 拍板「付費內容保護要排」，上架收費前完成。
> 分支：`claude/data-gw`（**不上 main、不動正式站資料流**）。第一階段＝本文件＋`workers/data-gw/`＋手動部署的 workflow。

## 0. 一句話

現在 `site/data/*.json` 全部是公開網址，鎖頭只是畫面。data-gw 讓「付費候選」的檔改放 R2 私有 bucket，
只有驗過身分與方案的人拿得到，每次發放都留紀錄、加浮水印、限流，異常會標記。

## 1. 資料分級表（盤點結果）

判準：檔案餵哪個畫面 → 那個畫面在 `site/features.js` 的哪個功能開關 → 開關由 #admin/perm 對「訪客／免費會員／付費範本」設定。
**gateway 不另外維護一份「誰付費」名單**：檔案能不能拿，直接看這個人生效的功能開關（跟鎖頭同一份設定）。
所以下表的「付費候選」意思是「Andy 在 #admin/perm 把這個開關對免費範本關掉時，它就真的擋得住」。
機器版在 `workers/data-gw/tiers.js`（白名單；不在表上的一律 404）。

| 檔名 | 誰在讀（前端檔） | 對應功能開關 | 分級 | 進 R2？ |
|---|---|---|---|---|
| meta | app.js、live.js | — | 免費（版本鍵，全站都要） | 否 |
| stocks | app.js、industry.js、mobile3.js、watchlists.js、watchpage.js、etfpage.js | — | 免費（搜尋清單） | 否 |
| groups_today | app.js、perm.js、admin.js | — | 免費（鎖頭本身要用） | 否 |
| logos、logos/*.png | app.js | — | 免費 | 否 |
| sparks | app.js、watchpage.js | — | 免費 | 否 |
| index_ohlc／index_intraday／index_lastday | market3.js、mobile3.js | ov.index | 免費（大盤公開資訊） | 否 |
| intl | mobile3.js | — | 免費 | 否 |
| news_head、updown、rrg_lite | app.js | ov.summary／ov.breadth／ov.rot | 免費（首頁門面） | 否 |
| hist/index | chart.js | — | 免費（只是索引） | 否 |
| market_heat | app.js | ov.heat | 付費候選 | 是 |
| flow_v3、rrg_members、rotation | app.js、mobile3.js | flow.rot | 付費候選 | 是 |
| sankey_daily | app.js、mobile3.js | flow.sankey | 付費候選 | 是 |
| concentration、concentration_members | app.js | flow.conc | 付費候選 | 是 |
| industry_map | app.js、industry.js | ind.map | 付費候選 | 是 |
| groups_detail、group_valuation、relative_strength | app.js、industry.js、mobile3.js | ind.groups | 付費候選 | 是 |
| supply_chain | app.js、industry.js | ind.rel | 付費候選 | 是 |
| themes | app.js、industry.js | heat.theme | 付費候選 | 是 |
| inst_streak、trust_streak | app.js | mkt.streak | 付費候選 | 是 |
| ma_breadth | app.js | mkt.ma | 付費候選 | 是 |
| candidates | app.js | mkt.cand | 付費候選 | 是 |
| seasonality_v3、seasonality | app.js | season.month | 付費候選 | 是 |
| fundamental | industry.js | stock.profit | 付費候選 | 是 |
| news | app.js、industry.js | stock.news | 付費候選 | 是 |
| broker_views | app.js | stock.ai | 付費候選 | 是 |
| stock/<代號>（約 2,300 檔） | industry.js、mobile3.js | stock.overview（整支檔，見 ⚠1） | 付費候選 | 是 |
| m60/<代號> | industry.js | stock.k_hour | 付費候選 | 是 |
| hist/<代號>/p<N> | chart.js | stock.k_day | 付費候選 | 是 |
| explore | explore.js | explore.page | 付費候選 | 是 |
| etf、etf_series | etfpage.js | etf.list／etf.returns | 付費候選 | 是 |
| earnings | earnings.js | earn.page | 付費候選 | 是 |
| delivery | app.js（#delivery） | — | **不發佈**（含 Andy 原話；sec-minify 已停發） | 否，白名單不列 |
| tasks | tasks.js | — | 已停產（2026-09-25） | 否 |

⚠1 **粒度**：`stock/<代號>` 一支檔同時餵總覽、營收、獲利、法人、資券、大戶分頁。第一階段以整支檔為單位（`stock.overview` 關掉才擋）。
要做到「營收免費、法人付費」，第二階段 pipeline 要把它拆成 `stock/<代號>`（基本）＋`stock_x/<代號>`（籌碼、財務），各自對應開關。

⚠2 **預設全開**：`features.js` 每一項 `def:true`。Andy 沒在 #admin/perm 關掉的，就算檔案已經在 R2，gateway 也照樣放行 —— 跟畫面一致，不會「突然看不到」。真的要收費時，鎖頭和檔案是**同一個動作**一起生效。

## 2. 第一階段做了什麼（本分支）

| 檔案 | 內容 |
|---|---|
| `workers/data-gw/worker.js` | `POST /v1/session`（登入權杖 → 5 分鐘資料權杖，綁裝置）、`GET /v1/data/<檔名>`（白名單 → 權限 → 限流 → 紀錄 → 異常規則 → R2 → 浮水印）、`POST /v1/admin/alerts`（管理者看異常） |
| `workers/data-gw/tiers.js` | 上表的機器版（白名單＋功能開關對照） |
| `workers/data-gw/harness.mjs`、`devserver.mjs` | 本機跑真的 worker.js（SQLite→node:sqlite、R2→記憶體或本機資料夾、account-api→本機 devserver） |
| `workers/data-gw/tests/gw.test.mjs` | 12 條允許／拒絕驗收（`node --test workers/data-gw/tests/gw.test.mjs`） |
| `workers/data-gw/wrangler.toml` | Worker＋DO＋R2 綁定＋account-api service binding＋門檻變數 |
| `.github/workflows/deploy-data-gw.yml` | **只有 workflow_dispatch**；先跑測試，缺 Secret 就跳過並列出缺什麼 |

### 跟原方案不同的一處（刻意）
原方案寫「account-api 簽資料權杖、共用簽章金鑰」。實際看 `workers/account-api/worker.js`：簽章金鑰是 Durable Object 第一次啟動時**隨機產生、存在它自己的 kv 表**，從不離開。
共用它要嘛把金鑰搬成 Secret（動到正式會員登入），要嘛改非對稱簽章。第一階段改用：**data-gw 拿登入權杖去問 account-api 的 `/v1/me` 與 `/v1/perm/me`**（同帳號 service binding，不走公網），
account-api 自己驗簽章與 `tv`，data-gw 再用自己的 `GW_SECRET` 簽 5 分鐘權杖。好處：**account-api 一行都沒改**；`tv` 一遞增（停權），最晚 5 分鐘後換權杖就失敗。
代價：每 5 分鐘每人多一次 Worker 對 Worker 呼叫（service binding 不另計請求費）。

### 權限判斷
- 免費檔：任何人拿得到（訪客以 IP 網段限流）。
- 付費候選檔：
  - 沒帶權杖 → 用訪客範本的開關判斷；被關 → 401 `login`。
  - 帶權杖 → 驗簽章、到期、裝置雜湊（`X-Device`），都過才看這個人的開關；被關 → 403 `plan`。
- 回應一律 `cache-control: private, no-store`，CDN 不會快取付費內容。

### 紀錄與個資
- `log` 表：時間、uid、檔名、IP 網段（`203.0.113.x`／IPv6 `/48`）、UA。**不存完整 IP、不存 email**。30 天自動刪。
- `alerts`／`flags` 表：異常種類、次數、最後時間。
- 隱私權政策要加的段落草稿在 `docs/security_review_1006.md` 2-5（口徑一致：網段、30 天）。**第二階段上線前要貼上。**

### 浮水印
- 物件型 JSON 加 `_wm: { a: HMAC(uid) 前 12 碼, t: 秒 }`；陣列型加在第一個物件元素上；回應標頭 `x-wm` 也有一份。前端不讀 `_wm`，畫面不變。
- 反查：`wmOf(GW_SECRET, uid)` 逐一比對（第二階段做成 #admin 按鈕）。
- ⚠ 這是「整份檔被原封不動轉貼」才查得到；有人只抄數字就查不到。數值層的浮水印（例如末位小數）會改到畫面，第一階段不做。

### 異常規則（命中只記錄＋標記，**不自動停權**）
| 規則 | 預設門檻 | 變數 |
|---|---|---|
| 同帳號 60 秒內不同檔數 | > 30 | `BURST_FILES` |
| 同一資料權杖的 IP 網段數 | > 2 | `MAX_IPS` |
| UA 不是 `Mozilla/5.0 …` 或缺 `Sec-Fetch-Mode` | 命中即記 | — |
| 每帳號每分鐘請求數 | > 60 → 429，並記一筆 `rate` | `RATE_PER_MIN` |
| 訪客每 IP 網段每分鐘 | > 120 → 429 | `GUEST_PER_MIN` |
| 每 IP 網段每分鐘換權杖 | > 20 → 429 | `SESSION_PER_MIN` |
同一帳號同一種異常 10 分鐘只記一筆（避免一個爬蟲寫爆資料表）。

## 3. 測試結果（本機）
`node --test workers/data-gw/tests/gw.test.mjs` → **12 過 0 敗**：白名單／路徑穿越 404、免費檔放行、未登入擋付費檔、session 拒絕假權杖／壞裝置／外站、
免費會員 403／付費會員 200、竄改／換裝置／過期 401、浮水印存在且反查得到且不是明文 email、限流 429 且下一分鐘恢復、紀錄欄位正確且只存網段、
三種異常都記錄而且仍放行（不停權）、正常使用者不被標記、管理者端點只給管理者、沒設金鑰 503。
另外起過兩支 devserver（真的 account-api devserver ＋ data-gw devserver），`/health`、免費檔、付費檔都能跑通（本機 account-api 的訪客範本是預設全開，所以付費檔也放行 —— 符合 ⚠2）。

沒驗到：真的 Cloudflare 部署、真的 R2、service binding 的實際行為（容器連不到 Cloudflare）。

## 4. 第二、三階段

### 第二階段（約 2～3 天）：資料真的搬進 R2、前端改走 gateway
| 檔案 | 做法 | 估時 |
|---|---|---|
| `pipeline/build_payload.py` | `_write()` 依 `tiers.js` 同一張表（抽成 `pipeline/datagw_tiers.json` 讓兩邊共讀，免得兩份不同步）把付費候選寫到 `site_paid/`，不寫進 `site/data/` | 0.5 天 |
| `.github/workflows/pages.yml` | 建完之後 `wrangler r2 object put`（或 `rclone sync`）把 `site_paid/` 上傳 R2；**上傳成功才部署 Pages**（不然會出現「頁面新、資料舊」） | 0.5 天 |
| `site/app.js` 的 `load()`（約 460 行） | 檔名在付費表上 → 改打 `DATA_GW_URL/v1/data/<name>`，帶 `Authorization`＋`X-Device`；401 自動換權杖一次；403 顯示 perm 的鎖頭 | 0.5 天 |
| `site/chart.js`（hist，414／428 行）、`site/mobile3.js`（280 行，自己的 load） | 同上（這兩支沒走 App.load） | 0.3 天 |
| 新 `site/datagw.js` | 裝置 id（localStorage）、權杖快取與到期前換新、統一 fetch | 0.3 天 |
| `site/app.js` 的 `Snap`（IndexedDB 快取） | **付費檔不准存進 Snap**：不然登出或降級後還看得到，也會留在共用電腦上 | 0.2 天 |
| `scripts/stamp_assets.py`、`pages.yml` 的 Secret | 前端要知道 gateway 網址（`DATA_GW_URL`，跟 `ACCOUNT_API_URL` 同做法） | 0.1 天 |
| `scripts/_uitest.py` | 新段落「付費資料閘道」：訪客拿不到、免費 403、付費 200（起兩支 devserver） | 0.5 天 |
| 隱私權政策 | 貼上 security_review 2-5 的段落 | 0.1 天 |

### 第三階段（約 1～1.5 天）：發現與阻擋
| 項目 | 做法 | 估時 |
|---|---|---|
| 通知 Andy | `alert()` 寄信（MailChannels／Resend）或推播；每天彙總一封＋重大即時一封 | 0.3 天 |
| 自動停權 | `flags.n` 超過門檻 → 呼叫 account-api 新端點遞增 `tv`＋`perm.suspended`（account-api 要加 0.3 天）；#admin 一鍵解除 | 0.5 天 |
| #admin 異常頁 | 讀 `/v1/admin/alerts`；浮水印反查按鈕 | 0.4 天 |
| 裝置數上限 | 每帳號最多 2 台裝置（session 表依 uid 數不同 devh） | 0.2 天 |

**剩餘合計約 3～4.5 天**（加第一階段約 1 天 ＝ 原估 4～6 天內）。

## 5. Andy 要按的（部署前）

1. **Cloudflare → R2 → Create bucket**：名稱 `tw-rotation-paid`，**不要開 Public access、不要接自訂網域**。（R2 第一次用要先在 R2 頁面按「啟用」，要綁信用卡但免費額度內不收費。）
2. **Cloudflare → My Profile → API Tokens → 編輯既有那張部署用權杖**（repo Secret `CLOUDFLARE_API_TOKEN` 那張），權限加：
   - Account → **Workers R2 Storage → Edit**（部署時綁 bucket、第二階段 pipeline 上傳）
   - 既有的 Workers Scripts: Edit 保留（Durable Object 跟著它）
3. **GitHub → Settings → Secrets and variables → Actions → New repository secret**：`DATA_GW_SECRET`，值是一串隨機字（可在終端機 `openssl rand -base64 48`，或請 Claude 在暫存區產生後**你自己貼**，不經過 repo）。
4. 想先試部署：Actions → 「部署 Worker（付費資料閘道 data-gw）」→ Run workflow（**選分支 claude/data-gw**）。部署了也不影響正式站：前端還沒呼叫它，bucket 也是空的。
5. 第二階段上線前：把 gateway 網址存成 Secret `DATA_GW_URL`。

## 6. 要 Andy 決定的門檻

| # | 決定什麼 | 我的建議（依據） |
|---|---|---|
| T1 | 每帳號每分鐘上限 | **60**。正常操作翻個股頁一次要 3～5 支檔（stock、m60、hist 2～3 頁），一分鐘翻 10 檔股票約 50 支 |
| T2 | 「大量抓」門檻（60 秒內不同檔數） | **30**。真人一分鐘看不到 8 檔股票（≈30 支檔）；爬蟲是一秒好幾支 |
| T3 | 同權杖 IP 網段數 | **2**（手機 Wi-Fi 切行動網路會變 2 個，所以 >2 才記） |
| T4 | 幾次異常自動停權 | **24 小時內 burst 或 multi_ip 累計 3 次**才停；bot_ua 單獨不停（有些瀏覽器外掛會改 UA）。先觀察兩週紀錄再定 |
| T5 | 哪些功能真的收費 | 在 #admin/perm 關免費範本的開關即可；建議先從 `stock.*` 籌碼與財務分頁、`explore.*`、`mkt.cand` 開始 |
| T6 | 異常通知寄到哪 | 沿用 security_review D5 |
