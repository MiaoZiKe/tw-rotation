# 會員登入（Google）設定步驟 —— 給 Andy

> 做完這份，網站右上角會出現「登入」，自選清單可以跨裝置同步，`#admin` 管理頁看得到使用統計與目前誰在線上。
> **不做也不會壞**：沒設定之前網站照常，只是沒有登入鈕，自選清單只存在各自的裝置。
>
> - 全部在網頁上點，不用裝任何東西、不用打指令。
> - 大約 **20～30 分鐘**，共 **6 步**。第 1 步你已經做過了（即時報價那時候）。
> - 為什麼用 Cloudflare 而不是 Firebase：DECISIONS #270（一句話：你公司網路連得到 workers.dev 是已知的；不用在網站放幾百 KB 的 SDK；保存期限可以真的自動刪）。

---

## 第 1 步：Cloudflare 金鑰（已完成，確認一下就好）

repo 的 **Settings → Secrets and variables → Actions** 裡應該已經有這兩個（即時報價的自動部署在用）：

- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`

有就跳到第 2 步。會員 Worker 會用同一組金鑰部署，不需要另外建資料庫（資料放在 Worker 自帶的 Durable Object 裡，跟著程式一起部署）。

---

## 第 2 步：在 Google 建一個「登入用戶端」（約 10～15 分鐘）

1. 開 <https://console.cloud.google.com/>，用你的 Google 帳號登入。第一次進來會問國家與條款，勾同意就好。
2. 最上面藍色列、Google Cloud 字樣右邊有一個**專案選擇器**（寫著「選取專案」或某個專案名）→ 點它 → 右上角 **新增專案**。
   - 專案名稱：`tw-rotation`（隨便取）→ **建立**。
   - 建好之後右上角會跳通知，點 **選取專案**（或再點一次專案選擇器選它）。**確認最上面顯示的是這個新專案**。
3. 左上角 ☰ 選單 → **API 和服務** → **OAuth 同意畫面**。
   - 新版畫面叫 **Google Auth Platform**，會看到「尚未設定 Google Auth Platform」→ 按 **開始使用**。
   - **應用程式資訊**：應用程式名稱填 `台股資金輪動`；使用者支援電子郵件選你的 email → **下一步**。
   - **目標對象**：選 **外部** → **下一步**。
   - **聯絡資訊**：填你的 email → **下一步**。
   - 勾「我同意 Google API 服務：使用者資料政策」→ **繼續** → **建立**。
4. 左邊選單點 **用戶端**（Clients）→ 上方 **＋ 建立用戶端**。
   - **應用程式類型**：選 **網頁應用程式**。
   - **名稱**：`tw-account`（隨便取）。
   - **已授權的 JavaScript 來源**：**不用填**。
   - **已授權的重新導向 URI** → **＋ 新增 URI** → 貼上（一個字都不能差）：
     ```
     https://tw-account.kcq01010909.workers.dev/auth/callback
     ```
   - 按 **建立**。
5. 跳出來的視窗會顯示 **用戶端 ID** 與 **用戶端密鑰**。
   - ⚠ **用戶端密鑰現在只會顯示這一次**，請先按旁邊的複製鈕貼到記事本（或按「下載 JSON」）。
   - 用戶端 ID 長得像 `123456789-xxxx.apps.googleusercontent.com`；密鑰像 `GOCSPX-xxxx`。
6. 左邊選單點 **目標對象**（Audience）→ 「發布狀態」寫著 **測試中** → 按 **發布應用程式** → **確認**。
   - 不發布的話只有你手動加的「測試使用者」能登入。
   - 我們只要求 `openid`、`email`、`profile` 三個最基本的權限，Google 規定這種**不需要送審**，發布後也不會出現「未經驗證的應用程式」警告。

---

## 第 3 步：把三個值存成 GitHub Secret（約 3 分鐘）

開 <https://github.com/MiaoZiKe/tw-rotation/settings/secrets/actions> → **New repository secret**，一個一個加（名稱大小寫要一模一樣，放在 **Repository secrets**）：

| Name | Secret（值） |
|---|---|
| `GOOGLE_CLIENT_ID` | 第 2 步的用戶端 ID |
| `GOOGLE_CLIENT_SECRET` | 第 2 步的用戶端密鑰 |
| `ACCOUNT_ADMIN_EMAILS` | 你的 Gmail（**管理者名單**；要多人就用逗號隔開，例如 `a@gmail.com,b@gmail.com`） |

> 管理者名單只存在 GitHub Secret 與 Cloudflare Worker 裡，**不在 repo、也不在網站原始碼裡**。
> 只有這些 email 登入後看得到 `#admin` 的使用統計、線上名單與會員名單。

---

## 第 4 步：部署會員 Worker（約 2 分鐘）

1. 開 <https://github.com/MiaoZiKe/tw-rotation/actions>。
2. 左邊清單點 **部署 Worker（會員登入與使用統計）**。
3. 右邊 **Run workflow** → 分支選 `main` → 綠色 **Run workflow**。
4. 等它跑完（約 1 分鐘）變綠色勾勾，點進去看最下面的摘要，要寫「**會員 Worker 部署成功**」。
   - 如果寫「尚未部署，缺少：…」→ 回第 3 步補那個 Secret。
   - 如果「部署」那一步紅了，而且訊息提到 permission／Durable Objects：代表 Cloudflare 金鑰的權限不夠。
     到 <https://dash.cloudflare.com/profile/api-tokens> 編輯那把金鑰，確認有 **Account → Workers Scripts → Edit**，存檔後再跑一次。

**自己確認活著**：瀏覽器打開 <https://tw-account.kcq01010909.workers.dev/health>，要看到
`"ok":true` 而且 `"configured":true`、`"admins":true`。

---

## 第 5 步：告訴網站 Worker 的網址（約 2 分鐘）

1. 回到 <https://github.com/MiaoZiKe/tw-rotation/settings/secrets/actions> → **New repository secret**：
   - Name：`ACCOUNT_API_URL`
   - Secret：`https://tw-account.kcq01010909.workers.dev`（結尾不要加斜線）
2. 到 <https://github.com/MiaoZiKe/tw-rotation/actions> → 左邊 **部署網站** → **Run workflow** → `main` → **Run workflow**。
   跑完大約 2～6 分鐘。

---

## 第 6 步：確認（約 3 分鐘）

1. 打開 <https://miaozike.github.io/tw-rotation/> 重新整理。電腦版右上角「★ 自選」旁邊會出現 **登入**；
   手機版在右上「⋯」清單最下面。
2. 按 **登入** → 先跳出一段告知（蒐集什麼、保存多久、怎麼刪除）→ 按 **用 Google 帳號登入** → 小視窗選你的帳號。
3. 右上角變成你的頭像與名字 → 點它，選單裡要有 **管理頁：使用統計與線上名單**。
4. 點管理頁，會看到「現在誰在線上？」裡有你自己。使用統計要過幾分鐘、有人逛過網站才會開始累積。

---

## 之後想改什麼

| 想做的事 | 怎麼做 |
|---|---|
| 加／換管理者 | 改 Secret `ACCOUNT_ADMIN_EMAILS` → 重跑第 4 步 |
| 一般訪客不要看到「N 人在線」 | 管理頁「現在誰在線上？」卡片下面的勾選框取消勾選（立即生效） |
| 暫時關掉整個會員功能 | 刪掉 Secret `ACCOUNT_API_URL` → 重跑「部署網站」。登入鈕與統計都會消失，網站照常 |
| 換 Google 密鑰 | Google Cloud → 用戶端 → 那個用戶端 → 新增密鑰 → 更新 `GOOGLE_CLIENT_SECRET` → 重跑第 4 步 |

## 已知限制

- 登入流程需要瀏覽器連得到 `accounts.google.com`（Google 本身的登入頁）。公司網路如果連 Google 登入都擋，只能在別的網路登入；
  登入後的同步與統計只連 workers.dev。
- 小視窗被瀏覽器擋掉時會自動改成整頁跳轉，登入完成會回到原本那一頁。
- 這不是律師審過的隱私權政策；隱私權政策頁的蒐集者欄位要等 `site/legal_config.js` 的必填欄位填好才會完整（跟既有條款同一個狀態）。
