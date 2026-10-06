# 會員資料匯出 API 規格：`/v1/admin/export`（待實作，2026-10-06）

> 狀態：**只有規格，Worker 還沒改**。筆電備份（`tools/laptop/backup.ps1`）目前備不到會員資料，就卡在這一支。

## 為什麼要有

會員帳號、方案、到期日、使用統計全部存在 Cloudflare Durable Object（`workers/account-api/worker.js` 的單一實例 `hub`）裡的 SQLite。
GitHub 上沒有任何副本。Durable Object 被誤刪、帳號被停用、Worker 改壞資料表時，**目前沒有任何辦法還原**。
已查過 `worker.js` 的路由表（2026-10-06）：管理者路由只有 stats／online／settings／perm／plans／feedback 這些，**沒有匯出**。

## 規格

- 路徑：`POST /v1/admin/export`，跟其他管理者路由一樣走 Origin 白名單＋權杖檢查，**只有 `ADMIN_EMAILS` 內的帳號**能叫。
  另外接受「備份專用權杖」：環境變數 `EXPORT_TOKEN`（Cloudflare Secret，不進 repo），請求帶 `Authorization: Bearer <EXPORT_TOKEN>`、不檢查 Origin（筆電的排程沒有瀏覽器 Origin）。
- **唯讀**：只做 `SELECT`，不刪不改。
- 範圍（逐表）：`users`、`lists`、`perm`、`plans`、`kv`（排除任何金鑰類的鍵）、`sub_requests`、`feedback`、`notices`、`notice_reads`、`usage`、`ev2`、`uev`、`visits`、`hstat`、`quota_hits`。
  **不匯出**：`logins`（一次性登入狀態）、`presence`（線上名單，幾分鐘就過期）、任何權杖或 Google 的 sub 原值（`users.subh` 已經是雜湊，可以匯出）。
- 回應：`{ v: 1, at: <ISO 時間>, tables: { <表名>: { cols: [...], rows: [[...], ...] } }, sha256: <內容雜湊>, sig: <HMAC-SHA256(EXPORT_SIGN_KEY, 內容)> }`
  - `sig` 用另一個 Secret `EXPORT_SIGN_KEY` 簽，還原前可以驗「這份檔案是 Worker 自己吐出來、沒被改過的」。
- 大小：目前規模（數百人）預估在 1 MB 內，一次回完。超過 20 MB 再改成分頁（`?table=&after=`）。
- 限流：同一權杖每小時最多 6 次。
- 稽核：每次匯出寫一筆到 `usage`（`k = admin_export`），管理頁可以看到誰在什麼時候匯出。

## 對應的還原（另一支，也待實作）

`POST /v1/admin/import`：只接受 `sig` 驗得過的檔案；**只能匯入到空的資料庫**（`users` 為 0 筆才准），避免覆蓋現有資料。

## 筆電端（等 API 上線後補）

`backup.ps1` 每天多一步：用憑證管理員裡的 `tw-ops-export`（`EXPORT_TOKEN`）叫這支，存成 `<備份根目錄>\members\members-YYYYMMDD.json`，保留 14 份。
