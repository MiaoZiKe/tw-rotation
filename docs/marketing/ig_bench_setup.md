# IG 對標採集：Andy 要做的設定（約 10 分鐘，一次做完 60 天有效）

## 為什麼要另外設

- Meta 的「商業帳號探索」（business_discovery）只開放給 **Facebook 登入**那一套（主機 graph.facebook.com）。
- 我們發文用的是 **Instagram 登入**權杖（graph.instagram.com）。2026-11-09 實際在 Actions 用它叫過一次，Meta 回：
  `code 100 IGApiException：Tried accessing nonexisting field (business_discovery)`（存在 social-snaps 分支 `research/ig_bench/2026-11-09.json`）。
- 官方文件：<https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/business_discovery>
  權杖要有 `instagram_basic`、`instagram_manage_insights`、`pages_read_engagement` 或 `pages_show_list`；粉專角色若是經由企業管理平台給的，再加 `business_management`。
- **這件事不擋其他工作**，可以晚點做；不做就只是對標資料抓不到。現有發文權杖完全不用動。

## 步驟

### 第 1 步：確認 IG @liguligu0818 有連到一個 Facebook 粉專

| 動作 | 連結 | 填什麼／點什麼 |
|---|---|---|
| 打開 Meta 商務套件的 Instagram 帳號設定 | <https://business.facebook.com/latest/settings/instagram_account> | 列表裡看到 **liguligu0818** → 已連好，跳到第 2 步 |
| 沒看到 → 先有一個粉專 | <https://www.facebook.com/pages/create> | 粉專名稱：隨意（例如「哩咕哩咕」）；類別：「媒體／新聞公司」；其他欄位不用動 → **建立粉絲專頁** |
| 把 IG 連到粉專 | 回到 <https://business.facebook.com/latest/settings/instagram_account> | 點 **新增**（Add）→ 登入 IG liguligu0818 → 允許 |

### 第 2 步：建一個新的 Meta 應用程式（舊的是 Instagram 登入型，加不了 Facebook 權限）

| 欄位 | 連結 | 值 |
|---|---|---|
| 開新應用程式 | <https://developers.facebook.com/apps/creation/> | — |
| 應用程式名稱 | 同一頁 | `liguligu-bench` |
| 聯絡電子郵件 | 同一頁 | 不用動（預設你的信箱） |
| 使用案例（Use cases） | 下一步 | 選 **其他**（Other） |
| 應用程式類型 | 下一步 | 選 **商家**（Business） |
| 企業管理組合 | 下一步 | 不用動（可留「未選取」） |
| 最後 | — | 按 **建立應用程式**（Create app），輸入 FB 密碼 |

不用送審、不用切成「上線」模式：你是這個應用程式的管理員，開發模式就能用。

### 第 3 步：在圖形 API 測試工具產生權杖

| 欄位 | 連結 | 值 |
|---|---|---|
| 打開 | <https://developers.facebook.com/tools/explorer/> | — |
| 右側「Meta 應用程式」（Meta App） | 同一頁 | 選 `liguligu-bench` |
| 「使用者或粉絲專頁」（User or Page） | 同一頁 | 選 **使用者存取權杖**（User Token） |
| 「權限」（Permissions）→ 新增 | 同一頁 | 逐一加入這 5 個：`instagram_basic`、`instagram_manage_insights`、`pages_show_list`、`pages_read_engagement`、`business_management` |
| 其他欄位（上方網址列 `me?fields=id,name`） | 同一頁 | 不用動 |
| 按鈕 | 同一頁 | **產生存取權杖**（Generate Access Token）→ 跳出 FB 視窗：粉專勾第 1 步那個、IG 勾 liguligu0818 → 一路 **繼續**／**儲存** |
| 結果 | 同一頁 | 「存取權杖」（Access Token）欄出現一長串 `EAA…` → 先不用複製，做第 4 步 |

### 第 4 步：延長成 60 天

| 欄位 | 連結 | 值 |
|---|---|---|
| 打開存取權杖偵錯工具 | <https://developers.facebook.com/tools/debug/accesstoken/> | — |
| 輸入框 | 同一頁 | 貼上第 3 步的 `EAA…` → 按 **偵錯**（Debug） |
| 頁面最下面 | 同一頁 | 按 **延長存取權杖**（Extend Access Token）→ 再輸入一次 FB 密碼 |
| 結果 | 同一頁 | 下方出現新的一串 `EAA…`（標示 60 天）→ **複製這一串**（不是第 3 步那串） |

### 第 5 步：存進 GitHub Secrets

| 欄位 | 連結 | 值 |
|---|---|---|
| 打開新增 secret 頁 | <https://github.com/MiaoZiKe/tw-rotation/settings/secrets/actions/new> | — |
| Name（名稱） | 同一頁 | `IG_BENCH_FB_TOKEN`（一字不差、全大寫） |
| Secret（值） | 同一頁 | 貼第 4 步複製的那串，前後不要有空白 |
| 按鈕 | 同一頁 | **Add secret**（新增密鑰） |
| `IG_BENCH_IG_USER_ID` | — | **不用設**，程式會自己從粉專找 |

**不要把權杖貼到聊天室。**

### 做完回我什麼

回一句「IG_BENCH_FB_TOKEN 設好了」就好。我會重跑 `ig_bench_collect`，結果寫到 social-snaps 分支 `research/ig_bench/<日期>.json`／`.md`。
若第 3 步跳出的視窗裡看不到 liguligu0818，截圖給我。
