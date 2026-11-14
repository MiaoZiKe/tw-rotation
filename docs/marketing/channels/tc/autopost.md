# 頻道②「科技透明圈」自動發文（2026-11-08）

> Andy 原話：「開通自動發文，這部分幫我想辦法自動化」。
> 範本：`docs/marketing/channels/ai_intro/ops.md` 第 1～2 節（多頻道隔離設計）。本頁是實作後的操作說明。

## 〇、2026-11-10 頻道④交接：改吃 TECH_* 權杖（先讀這節）

Andy 11-10：「Tech_01010909 丟給他們單位處理」。頻道②的帳號就是 IG／Threads 的 @tech_01010909，頻道④已經用 TECH_* 權杖驗證通過（run 42670385893）。CEO 決定只留一條管線：

- **保留 tc 管線**（tc_post.yml：佇列核准制、監工、自動測試、刪文、留言回覆）。權杖來源改成 `secrets.TECH_THREADS_ACCESS_TOKEN_AUTO || secrets.TECH_THREADS_ACCESS_TOKEN`、`secrets.TECH_IG_ACCESS_TOKEN_AUTO || secrets.TECH_IG_ACCESS_TOKEN`；帳號編號讀 `TECH_*_USER_ID`，沒填就用頻道④的 `healing_post.resolve_uid` 探查（`/me/assigned_instagram_accounts` 等）。
- **TC_* 收件流程保留但不需要**，Andy 不用再貼 TC_* 權杖；下面「四之三」第 4～6 步作廢。
- **channel_post.yml 不再排 tech**：`channels.json` 的 tech 標 `handed_over: tc_post.yml`，`channel_post.py --plan` 與留言私訊 plan 都跳過 tech。頻道③（caffaine）、頻道④（healing）不受影響。
- **成效**：`channel_insights.yml` 的 tech 照跑（寫 `docs/marketing/channels/tech/state/insights/`），週會直接讀它。
- **續期**：`meta_token_refresh` 已經續 TECH_*（Threads 每週；IG 延長需要 `META_APP_SECRET`）。

### IG 是 EAA 系統用戶權杖（graph.facebook.com）：能做／做不到

| 功能 | 狀態 | 原因 |
|---|---|---|
| IG 發輪播、建容器、回查 media_type | ✅ 可以 | `/{ig-user-id}/media`、`media_publish` 在 graph.facebook.com 用法相同；頻道④已驗證 |
| IG 讀自己貼文的留言 | ✅ 可以 | 權杖有 `instagram_manage_comments` |
| **IG 私訊（Private Reply、回覆私訊、查追蹤 is_user_follow_business）** | ❌ **目前做不到** | Facebook 這條路的 IG 私訊是 Messenger Platform：要「連結此 IG 帳號的粉絲專頁」＋專頁權杖，端點 `/{page-id}/messages`。頻道④診斷：權杖看得到 0 個粉絲專頁、缺 `pages_show_list`／`pages_read_engagement`。程式已寫好：一旦權杖看得到連結的粉絲專頁，會自動改用專頁權杖跑兩段式；現在安靜跳過、不紅燈 |
| IG 自動刪文 | ❌ 做不到（兩種權杖都一樣） | Instagram API 沒有刪貼文端點；到期照舊開 issue 請人工刪 |
| IG 完整成效 | ⚠️ 部分 | 缺 `instagram_manage_insights` |
| IG 私訊 Worker（workers/tc-dm） | ⏸ 先不部署 | Worker 走 graph.instagram.com（Instagram 登入版），跟 EAA 不相容 |
| Threads 發文、留言公開回覆、自動刪文、自我測試 | ✅ 可以 | Threads 權杖不受影響（刪文需 `threads_delete`；自我測試會先查刪除額度，沒權限就不發測試文） |

要讓 IG 私訊能做，有兩條路（都要本人在 Meta 後台操作）：① 建一個 Facebook 粉絲專頁並連結 @tech_01010909，系統用戶加指派粉絲專頁與 `pages_show_list`、`pages_read_engagement`、`pages_messaging`／`instagram_manage_messages`；② 改用 Instagram 登入版權杖（IGAA 開頭），走 graph.instagram.com（Worker 版即可用）。一般網友收得到仍要 Advanced Access（見 app_review/）。

## 一、跟頻道一（股市帳號）怎麼隔離

| 項目 | 頻道一 | 頻道②（本頁） |
|---|---|---|
| 佇列 | `social/threads/queue/`、`social/ig/queue/` | `social/tc/queue/<日期>_<代號>/`（一篇一個資料夾） |
| 權杖 Secret | `THREADS_*`、`IG_*` | `TC_THREADS_*`、`TC_IG_*`（只傳給頻道② 的工作流） |
| 發文程式 | `threads_post.py`、`ig_post.py`、`social_publish.py` | `scripts/tc_post.py` |
| 發文紀錄 | social-snaps 分支 `state/posted.json` | main 的 `state/tc/posted.json` |
| 開關 | `post_quota.json` 的 `live`／`queue` | `post_quota.json` 的 `tc` 區塊 |

防呆：`tc_post.py` 發文前先用 TC 權杖打 `/me`，帳號 id 若等於頻道一的 `THREADS_USER_ID`／`IG_USER_ID`，**整篇不發**；收件時也做同一個比對，不會把頻道一的權杖收成頻道②。

## 二、檔案與工作流

| 檔案 | 作用 |
|---|---|
| `.github/workflows/tc_token_intake.yml`＋`scripts/tc_token_intake.py` | 權杖收件（只能手動按）：Threads 短效換長效 → `/me` 查 id 與 username → 寫回 `TC_THREADS_ACCESS_TOKEN_AUTO`、`TC_THREADS_USER_ID`、`TC_IG_ACCESS_TOKEN_AUTO`、`TC_IG_USER_ID` → `data/_state/tc_token.json`（只有日期、剩幾天、username） |
| `.github/workflows/meta_token_refresh.yml` | 每週日續期，TC 這組一起續（AUTO 優先；還沒收件就略過、不告警；收件後 24 小時內不續） |
| `.github/workflows/tc_post.yml`＋`scripts/tc_post.py` | 每 15 分鐘看佇列；只發 approved 且到點的稿；手動觸發預設 dry_run |
| `docs/marketing/social_unit/post_quota.json` 的 `tc` | `enabled`／`threads`／`ig` 開關、`per_day: 1`、`min_gap_hours: 20` |

### 開關為什麼可以開 true
頻道② 只發 **Andy 核准過**（`status: approved`）的稿。佇列裡沒有 approved 稿時，程式只讀檔、不連 Meta、不寫任何檔；所以開關開著也不會多發。真正的閘門是「Andy 核准」這一步。

### `META_APP_SECRET` 怎麼判斷已經有了
工作流把 `secrets.META_APP_SECRET` 帶進環境變數：設過就有值、直接用（log 印「已設定，直接使用」）；沒設過是空字串，log 印中文提示。另外收件一開始會用 `META_SECRETS_PAT` 列出 Secret **名稱**（GitHub 不給讀值），在 log 印出每個相關名稱「有／無」。所以設過一次之後 Andy 不用再填。

## 三、一篇稿的格式

```
social/tc/queue/20261105_quanta/
  post.md       檔頭：status、scheduled_at、weekday（中文星期，例如「四」；2026-11-12 起必填，程式用 scheduled_at 反算台北星期，對不上就擋下不發，缺欄位只警告）、platforms、images（同資料夾的 JPEG）
  ig.txt        IG 說明文字（整段原樣）
  threads.txt   【主文】……【第 1 則留言】……
  1_cover.jpg、2_fields.jpg
```

- `status`：`draft` → Andy 核准改 `approved` → 程式發完改 `posted`（失敗改 `error`）。
- 發完回寫：`urls`（全部連結）、`urls_ig`、`urls_threads`、`urls_threads_reply`、`verified_ig`／`verified_threads`（回頭查的 media_type，要是 `CAROUSEL_ALBUM` 或 `IMAGE`）、`done`（已發的平台）。
- IG 發輪播（2～10 張）；Threads 主文帶同一組圖，**圖失敗不退回純文字**，整篇標 error。
- 上限：一天 1 篇、兩篇間隔 20 小時；超過就順延，檔頭寫 `deferred_until`，不算「沒發」。
- 圖要先在 main 上（用 raw.githubusercontent.com 公開網址給 Meta 抓）。
- **影片稿（2026-11-14 起）**：檔頭加 `media: video` 和 `video: <檔名>.mp4`（同資料夾）；`images` 可留空，有填就拿第 1 張 JPEG 當 IG Reels 封面（`cover_url`）。weekday 照查。
  IG 發 Reels（`media_type=REELS`＋`video_url`＋`caption`），Threads 主文發 `media_type=VIDEO`＋`video_url`，發完照舊發第 1 則留言。
  兩邊都每 10 秒查一次容器狀態，`FINISHED` 才發布；`ERROR` 直接報錯（整篇標 error、開 issue）；5 分鐘沒好也報錯。
  回查 media_type：影片稿 IG 要 `VIDEO`／`REELS`、Threads 要 `VIDEO`；圖片稿照舊。影片一樣要先在 main 上。

## 四、沒發出怎麼辦（10-29 規矩）

1. 監工：`approved` 且（排定時間或順延時間）過 30 分鐘還沒發、或 `status: error` → 開 issue「⚠️ 頻道② 科技透明圈：已核准貼文沒發出」。
2. 讀那次 run 的 log → 修 → 推 main → 把 `post.md` 改回 `status: approved`。`done:` 已有的平台不會重發，只補沒發的。
3. 沒有 TC 權杖時：安靜跳過（run 綠燈、不寄失敗信），記 `state/tc/status.json` 的 `no_token_since`；有 approved 稿卡住的話監工照樣開 issue。

## 四之一、第二階段（同一批已上線的部分）

| 功能 | 程式 | 行為 |
|---|---|---|
| 自動測試發文 | `scripts/tc_selftest.py`、`tc_selftest.yml`（收件成功後自動跑，也可手動） | Threads：先確認有刪除權限才發一則測試文 → `/me/threads` 讀回 → DELETE → 回查已刪。IG：只建 media container 等 FINISHED，**不呼叫 media_publish**（IG 登入版 API 不能刪貼文）。結果 `data/_state/tc_selftest.json`，失敗開 issue |
| 自動刪文 | `tc_post.py`（post.md 檔頭可選 `delete_at`） | Threads：先刪第 1 則留言、再刪主文，回查確認，寫 `deleted_threads`。IG：做不到，開 issue「IG 貼文到期，請手動刪除」附 permalink 與步驟，寫 `ig_delete_notified` |
| Threads 留言關鍵字回覆 | `scripts/tc_threads_replies.py`（tc_post.yml 每 15 分鐘一起跑） | Threads 沒有私訊 API、也查不到追蹤，所以改公開回覆一句＋網站連結；輪詢 `threads_read_replies`（免 Advanced Access）；每人每篇 1 次；只存雜湊。文案設定 `social/tc/dm_config.json`，`legal_reviewed` 不是 true 前只記錄不送出 |

### 權杖一次要齊的權限（避免授權兩次）
- Threads：`threads_basic`、`threads_content_publish`、`threads_manage_replies`、`threads_read_replies`、`threads_delete`
- IG：`instagram_business_basic`、`instagram_business_content_publish`、`instagram_business_manage_comments`、`instagram_business_manage_messages`

## 四之二、IG 留言關鍵字 → 私訊 → 查追蹤 → 送整理

**為什麼是兩段式（Meta 規定）**：`is_user_follow_business`（User Profile API）要等對方**先傳訊息給我們、建立同意**之後才查得到；只留言的人去查會回「User consent is required」。所以第一則私訊前不能檢查追蹤，只能：

1. 留言含關鍵字（`social/tc/dm_config.json` 的 `keywords`，第一版「透明」）→ Private Reply 私訊一句「謝謝留言！追蹤 @帳號 後回覆『好了』，我把重點整理傳給你」。每則留言只能私回 1 次、留言後 7 天內。
2. 對方在私訊回「好了」→ 查 `is_user_follow_business`：true → 送整理（`contents` 依貼文代號，沒有就用 `default`）；false → 「還沒看到你追蹤喔，追蹤後再回一次『好了』」（每人每天最多 3 次）。

| 版本 | 程式 | 什麼時候用 |
|---|---|---|
| 輪詢版（預設 `ig_dm.mode: "poll"`） | `scripts/tc_ig_dm.py`，tc_post.yml 每 15 分鐘 | 現在就能跑；不用 webhook，所以不需要 App 上線與 comments webhook 的 Advanced Access。延遲最多約 15 分鐘 |
| 即時版（`ig_dm.mode: "webhook"`） | `workers/tc-dm/`（Cloudflare Worker：驗簽、KV 去重、每人每天上限、每分鐘速率上限、紀錄）＋ `deploy-tc-dm.yml` | App Review（Advanced Access）審過後才切。兩版同時只開一個，避免重複私訊 |

- 評估：Worker 新建 `workers/tc-dm`，不併進既有 Worker —— 既有的 account-api 管付款與會員、quote-proxy 管報價，權杖與 KV 分開，出事不互相拖累。
- 上限：每則留言 1 次、每人每天 1 次私回（`per_user_per_day`）、每分鐘 10 則（`max_per_minute`）。
- 隱私：只存雜湊（留言 id、使用者 id）與時間，30 天後清掉；不存留言內容、帳號名稱、私訊內容。
- **follow_gate**（`dm_config.json` 的 `ig_dm.follow_gate`，預設 `true`）：true＝上面的兩段式（Andy 指示私訊前要檢查追蹤；法遵查不到 Meta 明文禁止，信心低，屬未確認風險）。改成 `false`＝法遵給的替代做法：不查追蹤，留言後直接私回「謝謝留言！重點整理在下面，想看後續可以追蹤 @帳號」＋重點內容，追蹤只當鼓勵。因為 Meta 每則留言只准私回 1 則、對方回覆前不能再傳，開頭句與重點是**合在同一則**送出。
- 法遵：2026-11-09 審過，修改後可用（「完整整理」改「重點整理」、面試題型改「網友分享的面試方向」、隱私權政策補一句），`legal_reviewed` 已改 true。
- **法遵閘**：`legal_reviewed` 不是 `true` 時兩版都只記錄「會送什麼」、不送出。私訊與 Threads 回覆文案要先過 legal-compliance（不寫投資建議、內部、爆料；有「網友公開分享整理，非公司公告，未經查證，僅供參考」）。
- 會不會發給一般網友：開發模式（Standard Access）下，Meta 文件寫只對 App 有角色的帳號有效（信心：中）；一般網友要 Advanced Access → 送審包在 `docs/marketing/channels/tc/app_review/`。

### Worker 部署說明（給 CEO 安排）
1. 先決條件：TC 權杖收件成功；repo Secrets 有 `CLOUDFLARE_API_TOKEN`（含 Workers KV Storage → Edit）、`CLOUDFLARE_ACCOUNT_ID`、`TC_IG_APP_SECRET`（Instagram 應用程式密鑰）。
2. 跑 <https://github.com/MiaoZiKe/tw-rotation/actions/workflows/deploy-tc-dm.yml> → Run workflow（subscribe 不勾）：跑 node 測試 → 建 KV `tw-tc-dm` → 部署 `tw-tc-dm` → 寫入 IG_TOKEN、IG_APP_SECRET。每週日自動重寫 IG_TOKEN（續期後的權杖）。
3. App Review 審過、App 切 Live 之後：再跑一次並勾 subscribe（另需 Secret `TC_IG_APP_ID`）→ 自動產生 verify token、向 Meta 註冊 webhook（comments、messages）、帳號訂閱 → 把 `dm_config.json` 的 `ig_dm.mode` 改成 `"webhook"` 推 main。

## 四之三、Andy 必做清單（只有 Meta 規定一定要本人做的事）

| # | 做什麼 | 連結 | 為什麼程式不能代勞 |
|---|---|---|---|
| 1 | 用新 IG 帳號登入 Threads；IG 切成專業帳號（商業） | IG App：設定 → 帳號類型和工具 → 切換為專業帳號 | 建帳號、切帳號類型要本人登入，Meta 不提供 API |
| 2 | 在 Meta App 把新帳號加成 **Threads 測試人員**、**Instagram 測試人員**，再用新帳號接受邀請 | 加人：<https://developers.facebook.com/apps/> → 你的 App → App roles → Roles；接受（Threads）：Threads → 設定 → 帳號 → 網站權限 → 邀請；接受（IG）：<https://www.instagram.com/accounts/manage_access/> → 測試人員邀請 | 邀請必須由帳號本人接受（Meta 規定） |
| 3 | 在 App 的使用案例把權限加齊（只做一次）：Threads 加 `threads_manage_replies`、`threads_read_replies`、`threads_delete`；IG 加 `instagram_business_manage_comments`、`instagram_business_manage_messages` | <https://developers.facebook.com/apps/> → App → Use cases → 各自的 Customize → Permissions → Add | App 設定只能在後台改，沒有 API |
| 4 | 產生兩把權杖（授權畫面要本人按「繼續」） | Threads：同上 Use cases → Access the Threads API → Settings → User Token Generator → Generate；IG：Use cases → Instagram → API setup with Instagram login → Generate token | OAuth 授權必須帳號本人登入同意，Meta 禁止自動登入 |
| 5 | 把值貼進 GitHub Secrets（**Threads 短效權杖 1 小時內要用掉**）：`TC_THREADS_SHORT_TOKEN`、`TC_IG_ACCESS_TOKEN`；`META_APP_SECRET`（Threads 應用程式密鑰，設過就不用再貼） | <https://github.com/MiaoZiKe/tw-rotation/settings/secrets/actions/new> | 權杖與密鑰只在本人的後台看得到 |
| 6 | 按一次權杖收件（收件成功會自動接著跑自動測試） | <https://github.com/MiaoZiKe/tw-rotation/actions/workflows/tc_token_intake.yml> → Run workflow → Run | 也可以回 CEO「貼好了」由 CEO 觸發；但短效權杖 1 小時就過期，自己按最快 |
| 7 | 每篇稿核准：`post.md` 的 `status: draft` 改 `approved`（或回 CEO「第 X 篇核准」） | <https://github.com/MiaoZiKe/tw-rotation/tree/main/social/tc/queue> | 10-29 規矩：頻道② 只發 Andy 核准的稿 |
| 8 | IG 私訊給一般網友：企業驗證＋錄一支操作影片＋按送審 | 照 `docs/marketing/channels/tc/app_review/README.md` 第五節 | Advanced Access 要企業驗證與本人送審（Meta 規定） |
| 9 | IG 到期刪文：收到 issue 後在 IG App 手動刪 | issue 內附連結 | Instagram 登入版 API 沒有刪貼文功能 |

## 五、修改紀錄
- 2026-11-08 建立（social-ops-lead）：收件、續期、佇列、發文、監工；廣達稿放進佇列（draft）。
- 2026-11-08 同批：自動測試發文、Threads 自動刪文／IG 到期開 issue、Threads 留言關鍵字公開回覆。
- 2026-11-08 同批：IG 留言關鍵字私訊（輪詢版 tc_ig_dm.py＋Worker workers/tc-dm）、App Review 送審包、Andy 必做清單。
- 2026-11-09 法遵審後修改：文案改「重點整理」、面試方向不寫題目原文、加 follow_gate 開關、legal_reviewed=true；廣達 threads.txt 主文刪 4 個表情符號到 494 字。
- 2026-11-10 頻道④交接：改吃 TECH_*、IG 支援 EAA（graph.facebook.com）、channel_post 停排 tech；EAA 下 IG 私訊做不到（缺粉絲專頁）。
- 2026-11-14 加影片發文（social-ops-lead）：post.md `media: video`＋`video:`；IG Reels、Threads VIDEO，等容器 FINISHED 才發布；測試 tests/test_tc_autopost.py 補 9 條。
