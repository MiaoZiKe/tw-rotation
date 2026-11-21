# 全站備份操作手冊（給 Claude 看的，2026-10-06）

> 讀者是**新 session 的 Claude**。讀完就照做，不要再問 Andy「要怎麼備份」。
> Andy 說「備份」→ 照這份做。Andy 的原話（2026-10-06 21:00）：「全站備份需要備份到我這筆電，並且 GitHub 需要有個 .md 檔案讓 Claude 之後看了可以照那份 .md 快速備份」。
> 給 Andy 看的逐步說明在 `tools/laptop/README.md`；這份是總表＋Claude 的檢查步驟。兩份衝突時，以 README 的實際步驟為準，並回頭修這份。

## 1. 備份什麼

| 項目 | 在哪裡 | 怎麼備份 | 備份檔位置（筆電） |
|---|---|---|---|
| 程式與文件 | GitHub repo `MiaoZiKe/tw-rotation` | `backup.ps1` 每天 `git fetch` 全部分支與標籤，另存當天快照 | `D:\tw-backup\repo.git` |
| 資料湖 `data/`（Parquet、`_state/`） | 同一個 repo（Actions 每天 commit） | 跟著 repo 一起，含完整歷史 | 同上 |
| 會員資料（帳號、方案、到期日、自選、權限、使用統計、意見回饋、公告） | Cloudflare Durable Object（`workers/account-api`） | `backup.ps1` 用 `BACKUP_TOKEN` 叫 `POST /v1/admin/export`，回應附 `sha256` 與 `sig` | `D:\tw-backup\members\members-YYYYMMDD.json` |
| GitHub Secrets | repo Settings → Secrets | **不備份值**。只記名稱（下表）；**值由 Andy 自己保管**（密碼管理器或紙本），Claude 永遠不碰、不寫進任何檔案 | — |

GitHub Secrets 名稱清單（從 `.github/workflows/*.yml` 的 `secrets.*` 取，2026-10-06）：

| 名稱 | 用途 | 掉了怎麼辦 |
|---|---|---|
| `FINMIND_TOKEN` | 每日管線抓 FinMind | 到 FinMind 會員頁重新產生 |
| `FRED_API_KEY` | 總經資料 | 到 FRED 帳號頁重新產生 |
| `ACCOUNT_API_URL` | 前端會員 Worker 網址（`https://tw-account.kcq01010909.workers.dev`） | 不是秘密，直接填回 |
| `ACCOUNT_ADMIN_EMAILS` | 管理者信箱 | Andy 填回 |
| `GOOGLE_CLIENT_ID`、`GOOGLE_CLIENT_SECRET` | Google 登入 | Google Cloud Console → 憑證，見 `docs/login_setup.md` |
| `CLOUDFLARE_ACCOUNT_ID`、`CLOUDFLARE_API_TOKEN` | 部署 Worker | Cloudflare 後台 → 我的設定檔 → API 權杖 |
| `DENO_DEPLOY_TOKEN` | 報價備援部署 | Deno Deploy 後台 |
| `BACKUP_TOKEN` | 筆電叫 `/v1/admin/export`；也是匯出檔的簽章金鑰 | **要跟舊備份檔同一個值**才驗得過簽章 —— 請 Andy 一定要另外保存 |

Worker 端另有用 `wrangler secret put` 設的（例如 `NEWEBPAY_HASH_KEY`），同樣只記名稱、值由 Andy 保管。
新增任何 Secret 時，把名稱補進上表。

## 2. 備份到哪

- **第一份：Andy 的 Windows 筆電** `D:\tw-backup\`（沒有 D 槽就是 `%USERPROFILE%\tw-backup`）。腳本在 `tools/laptop/`，安裝後複製到 `%LOCALAPPDATA%\tw-ops\`。
  - 排程 `tw-ops 每日備份`：每天 22:00；快照保留 14 天（`refs/snapshots/<日期>/...`，共用物件，不會佔 14 倍空間）。
  - 排程 `tw-ops 監控`：每 5 分鐘；備份失敗也會發通知（桌面／Gmail／ntfy）。
- **第二份：雲端（Andy 二選一，README「第二份異地備份」）**
  - A：Google Drive 桌面版同步 `D:\tw-backup`（免費 15 GB）。
  - B：Cloudflare R2（免費每月 10 GB）＋ rclone，`backup.ps1` 偵測到 `%LOCALAPPDATA%\tw-ops\rclone.exe` 就自動 `rclone sync`。
  - **目前選了哪一個：尚未選。** Andy 選了之後把這一行改掉。

## 3. Claude 可以做的步驟

Claude **讀不到筆電**，也打不開 `miaozike.github.io`／`workers.dev`（出口代理擋）。能查的只有 GitHub。

### 3.1 檢查備份大概是好的
1. 資料湖有沒有在長：`git fetch origin main && git show origin/main:data/_state/last_run.json | python -c "import json,sys;d=json.load(sys.stdin);print(d['finished_at'],d['complete'],len(d['errors']))"`
   `finished_at` 在 26 小時內（週末 74 小時）、`errors` 為 0 → 筆電當晚拉到的就是好資料。
2. 每日管線與部署沒紅燈：`gh api repos/MiaoZiKe/tw-rotation/actions/runs?per_page=10 --jq '.workflow_runs[]|[.name,.conclusion,.created_at]|@tsv'`
3. 會員匯出那條路有沒有開：`gh api repos/MiaoZiKe/tw-rotation/actions/workflows/deploy-account-worker.yml/runs?per_page=1`，
   看最近一輪的摘要有沒有「沒設 BACKUP_TOKEN」的待辦字樣（有＝會員資料備不到，告訴 Andy 做 README 第 7 步）。
4. **筆電那邊到底成功沒有，只有 Andy 看得到**。請他照第 4.3 節看一眼，回報結果。不要自己宣稱「備份成功」。

### 3.2 改了 `tools/laptop/` 之後
1. ps1 一律存成 **UTF-8 帶 BOM＋CRLF**（PowerShell 5.1 讀中文才不會亂碼；`tools/laptop/.gitattributes` 已設 CRLF）。
2. 語法自檢：容器沒有 PowerShell，就下載 pwsh 到 scratchpad，用 `[System.Management.Automation.Language.Parser]::ParseFile` 逐支檢查。
3. 字串裡不准有沒跳脫的 `> < | &`（CLAUDE.md 規則）。
4. 推 main 後告訴 Andy **重新安裝**（設定會保留）：
   ```powershell
   cd $env:USERPROFILE\tw-tools; git pull
   powershell -ExecutionPolicy Bypass -File .\tools\laptop\install.ps1
   ```

### 3.3 新增資料表時要同步改的地方
- **資料湖新表**（`pipeline/config.py` 的 `TABLES`）：放在 `data/` 底下就自動跟著 repo 備份，**不用改備份腳本**。確認沒有被 `.gitignore` 排除。
- **會員 Worker 新表**（`worker.js` 的 `CREATE TABLE`）：要把表名加進 `/v1/admin/export` 的匯出清單**與** `/v1/admin/import` 的匯入清單，
  並在 `workers/account-api/tests/` 補一條「匯出再匯入後資料一樣」的測試。表裡有權杖或金鑰的欄位要排除。
  同時更新本檔第 1 節「會員資料」那一格的內容說明。
- **新 Secret**：補進第 1 節的表。

## 4. Andy 要做的步驟

### 4.1 首次安裝（約 15 分鐘）—— 詳細在 `tools/laptop/README.md` 第 1～7 步
```powershell
cd $env:USERPROFILE
git clone --depth 1 --filter=blob:none --sparse https://github.com/MiaoZiKe/tw-rotation.git tw-tools
cd tw-tools; git sparse-checkout set tools/laptop; cd tools\laptop
powershell -ExecutionPolicy Bypass -File .\install.ps1 -GmailTo 你的信箱@gmail.com
cmdkey /generic:tw-ops-gmail /user:你的信箱@gmail.com /pass
```
接著做 README 第 7 步（`BACKUP_TOKEN`：GitHub Secret 與筆電 `cmdkey /generic:tw-ops-backup` 存同一個值）。

### 4.2 手動備份一次
```powershell
powershell -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\tw-ops\backup.ps1"
```
第一次要抓整個資料湖，可能跑幾分鐘到幾十分鐘。最後一行是「備份完成：main=…，快照 N 天，佔 … MB」。

### 4.3 確認備份成功
1. 看紀錄檔最後幾行：`Get-Content "$env:LOCALAPPDATA\tw-ops\ops.log" -Tail 10`，要有「備份完成」，會員資料那行要寫已匯出（不是「略過」）。
2. 看快照：`git -C D:\tw-backup\repo.git for-each-ref refs/snapshots --format='%(refname)'`，應該有今天的日期。
3. 看會員檔：`dir D:\tw-backup\members`，有今天的 `members-YYYYMMDD.json`。
4. 工作排程器 → `tw-ops 每日備份` →「上次執行結果」是 0x0。

## 5. 還原（詳細指令在 README「萬一資料不見：還原步驟」）

**情境 A：GitHub 的 repo 不見或歷史被覆寫**
1. `git clone D:\tw-backup\repo.git $env:USERPROFILE\tw-restore`
2. 要某一天：`for-each-ref refs/snapshots` 找那天 `heads/main` 的 commit → `git checkout -b restore <commit>`
3. 推回 GitHub（新 repo 或原 repo）：`git push <網址> restore:main`。原 repo 還在時先找 Claude 確認，**不准 force push 蓋掉好的部分**。
4. Andy 依第 1 節清單把 Secrets 一個一個填回 → Settings → Pages 開啟 → 手動跑 `pages.yml`。
5. Claude 用第 3.1 節確認 `last_run.json` 與 Actions 都正常。

**情境 B：Cloudflare 會員資料不見**
1. 重新部署 Worker（`deploy-account-worker.yml`），`BACKUP_TOKEN` 必須跟備份檔產生時同一個值。
2. **在任何人登入之前**，用最近一份 `members-YYYYMMDD.json` 叫 `/v1/admin/import?confirm=RESTORE-INTO-EMPTY-DB`（只准匯入空資料庫）。
3. 所有人重新登入一次（登入權杖的簽章金鑰刻意不備份）。
4. 管理區抽查：會員數、方案、到期日跟備份檔一致。

**情境 C：筆電壞掉**
1. 沒有雲端第二份 → GitHub 與 Cloudflare 都還在就沒損失，換一台照 4.1 重裝即可，會員資料從當天起重新累積備份。
2. 有雲端第二份 → 新筆電先把 `tw-backup` 整個從 Google Drive／R2（`rclone copy r2:tw-backup D:\tw-backup`）抓回來，再照 4.1 安裝（`-BackupRoot` 指到同一個位置），14 天快照就接得上。

## 6. 每月演練清單（每月第一個週末，約 20 分鐘）

- [ ] Claude：跑第 3.1 節 1～3 步，結果寫進 `HANDOFF.md`。
- [ ] Andy：第 4.3 節四項都看過。
- [ ] Andy：`git clone D:\tw-backup\repo.git %TEMP%\drill`，打開確認 `data/_state/last_run.json` 是昨天或今天；看完刪掉（**不推**）。
- [ ] Andy：最近一份 `members-*.json` 打得開、`tables.users.rows` 筆數跟管理區的會員數對得上。
- [ ] Andy：雲端第二份的檔案日期是最近 1～2 天。
- [ ] Andy：`test-notify.ps1` 跑一次，通知收得到。
- [ ] 任何一項不過 → 記進 `docs/confirm_ledger.md`，下一則回報附上。
