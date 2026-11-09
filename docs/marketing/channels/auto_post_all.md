# 多頻道自動發文（IG 輪播＋Threads 輪播）總說明

> 2026-11-09 Andy 原話：「talk_01010909 已經好了 幫忙協助其他頻道 一起建立 Tech_01010909 Shrimp_01010909 caffaine.ai 以上三個都只差在 Github」。
> 頻道④「談晴說礙」的管線（`docs/marketing/channels/healing/auto_post.md`）擴充成多頻道共用：同一份發文程式，每個頻道自己的佇列、紀錄、開關、權杖。
> 2026-11-09 Andy 補一句：「Shrimp_01010909 不用 其他都幫我確認」→ **水下蝦米不接這套，繼續用 Buffer**；本管線只有 healing、tech、caffaine 三個頻道。
> 帳號與密碼名稱對照：`docs/marketing/channels/accounts.md`（名稱已定案，照用）。頻道①（股市，盤前／盤中／盤後）完全不在這裡，不受影響。

## 1. 頻道一覽

| 代碼 | 頻道 | 帳號 | 權杖前綴 | 資料夾 | 主時段（台北） | 保底補跑 | 工作流 | 開關現況 |
|---|---|---|---|---|---|---|---|---|
| `healing` | ④ 談晴說礙 | talk_01010909 | `HEALING_` | `docs/marketing/channels/healing/` | **20:27** | 21:57 | `healing_post.yml` | live（首篇 `20261108_intro` 在佇列） |
| `tech` | ② 科技透明圈 | Tech_01010909 | `TECH_` | `docs/marketing/channels/tech/` | **12:17** | 13:47 | `channel_post.yml` | live，佇列空 |
| `caffaine` | ③ AI 介紹頻道 | caffaine.ai | `CAFFAINE_` | `docs/marketing/channels/caffaine/` | **19:13** | 20:43 | `channel_post.yml` | live，佇列空 |

- 設定檔：`docs/marketing/channels/channels.json`（代碼、前綴、佇列、state、開關檔、時段、UTC 排程、每日上限 1、時段理由）。
- 水下蝦米（Shrimp_01010909）不在清單：繼續用 Buffer，這裡不排程、不續期、不建資料夾。
- 每天每個頻道最多 1 則（`channels.json` 的 `per_day` 跟各自 `post_quota.json` 的 `per_day` 取較小者）。

### 時段為什麼這樣排
| 頻道 | 理由 |
|---|---|
| 談晴說礙 20:27 | 晚餐後放鬆滑手機；療癒向內容晚上互動最好（沿用 11-08 已上線的時段，不動） |
| 科技透明圈 12:17 | 上班族午休（12:00～13:00）滑手機高峰，科技／產業類在午休最常被點開 |
| AI 介紹 19:13 | 下班通勤到晚餐，工具／教學類收藏最多；跟談晴說礙錯開一小時以上 |

全部避開整點與半點（GitHub 排程在整點最擠，常晚幾十分鐘）。保底補跑在主時段後 90 分鐘：主時段沒跑到或失敗時補，當天已發過就不會再發。

### 為什麼頻道④留在 healing_post.yml、其他兩個走 channel_post.yml
- 另一邊 CEO 正在用 `healing_post.yml` 跑頻道④的驗證，改它的排程或觸發方式會打斷進行中的工作；頻道④已經在線上，**不動它最安全**。
- 程式是同一份（`scripts/healing_post.py`；`scripts/channel_post.py --channel <代碼>` 是入口），所以修一次四個頻道都修到。
- `channel_post.yml` 用 matrix：每個頻道一個 job，**只帶自己前綴的 Secrets**（其他頻道的格子是空字串），一個頻道失敗不影響別的。

## 2. 放貼文進佇列（每個頻道都一樣）

1. 開資料夾：`docs/marketing/channels/<代碼>/queue/<YYYYMMDD>_<英文短名>/`（資料夾名用英數；排序照名字）。
2. 放進：
   - `1.png`、`2.png`…（從 1 連號，IG 最多 10 張）。IG 只收 JPEG：同名 `n.jpg` 可自己放，沒放工作流會自動從 PNG 轉並先推上 main。
   - `caption.txt`：內文（≤2200 字、#標籤 ≤30 個；Threads 超過 500 字自動截斷加「…」）。
   - `meta.json`：`{"title": "給人看的名字", "platforms": ["ig", "threads"], "status": "approved", "publish_at": null}`
     - `status`：`approved` 才會發；`draft` 不碰；發完自動改成 `posted` 並寫入 `urls`。
     - `publish_at`：`null`＝下一個時段就發；要指定最早時間就寫台北時間，例如 `"2026-11-12T12:17+08:00"`。
3. AI 生成的圖要有 `ai_review.md`（art-director 審過）才准放 `approved`；不放比比。
4. 推上 main 前可以本機看一次會發什麼：`python scripts/channel_post.py --channel tech --dry-run`。

佇列是空的 → 不發，摘要寫「佇列已空」，綠燈。

## 3. 開關

`docs/marketing/channels/<代碼>/post_quota.json`：

| 欄位 | 意思 |
|---|---|
| `live` | `false`＝整個停發（綠燈、不連 Meta）；`true`＝照時段發 |
| `per_day` | 台北每天最多開始發幾則新貼文（目前全部 1） |

## 4. 權杖（各頻道只讀自己的）

Secrets 頁：<https://github.com/MiaoZiKe/tw-rotation/settings/secrets/actions>。名稱照 `accounts.md`：

| 頻道 | 要建的 Secret | 不用建（程式寫回） |
|---|---|---|
| tech | `TECH_IG_ACCESS_TOKEN`、`TECH_THREADS_ACCESS_TOKEN` | `TECH_*_ACCESS_TOKEN_AUTO` |
| caffaine | `CAFFAINE_IG_ACCESS_TOKEN`、`CAFFAINE_THREADS_ACCESS_TOKEN` | `CAFFAINE_*_ACCESS_TOKEN_AUTO` |
| 共用 | `THREADS_APP_SECRET`（已有）、`META_SECRETS_PAT`（已有） | — |

- 選填：`<前綴>IG_USER_ID`、`<前綴>THREADS_USER_ID`（沒填就用權杖呼叫 `/me` 自動查）。
- **隔離**：程式只讀 `<前綴>*`，就算環境裡有別頻道或頻道①的 `IG_ACCESS_TOKEN`／`THREADS_ACCESS_TOKEN` 也不會用；前綴空白或亂寫直接報錯（`tests/test_channel_post.py` 鎖住）。工作流也只把那個頻道的 Secrets 帶進那個 job。
- **沒設權杖** → 空跑、綠燈，摘要寫「等待 Andy 設定權杖：`<前綴>IG_ACCESS_TOKEN`、`<前綴>THREADS_ACCESS_TOKEN`」。只設一個平台 → 只發那個平台，另一個設好後補。
- **權杖第一次出現** → 先自動跑驗證模式（只建輪播容器、等 FINISHED、不發布），`state/verify.json` 記 verified 後才正式發。
- **Threads 短效（1 小時）**：發文前先試續期，失敗而且有 `THREADS_APP_SECRET` → 自動換 60 天長效，用 `META_SECRETS_PAT` 寫回 `<前綴>THREADS_ACCESS_TOKEN_AUTO`。
- **每週續期**：`meta_token_refresh.yml`（每週日台北 10:23）一起續 `HEALING／TECH／CAFFAINE` 的 IG 與 Threads，寫回 `*_AUTO`；沒設的狀態是 missing，不紅燈、不告警。這四組的 Threads 續期失敗時也會用共用 `THREADS_APP_SECRET` 試換長效。

## 5. 水下蝦米（不接）

Andy 11-09：「Shrimp_01010909 不用」。水下蝦米繼續由 Buffer（api.buffer.com）發文；本管線沒有 shrimp 頻道、沒有資料夾、不續期它的權杖，所以不會跟 Buffer 重複發。日後要改接，再照第 2～4 節加一個頻道（要先停 Buffer 的排程）。

## 6. 留言自動私訊（IG）

- 程式同頻道④：`scripts/healing_comments.py --channel <代碼>`；工作流：頻道④ `healing_comments.yml`，其他兩個 `channel_comments.yml`（每 30 分鐘，分鐘 11／41）。
- 新頻道（tech、caffaine）的 `docs/marketing/channels/<代碼>/dm_config.json` **預設 `enabled: false`**（Andy 還沒定私訊內容）。關著的頻道連 job 都不開、不讀權杖、不連 Meta。
- **怎麼開**：
  1. Andy 定好私訊文字。
  2. 把該頻道 `dm_config.json` 的 `message` 填上，`enabled` 改 `true`，推上 main。
  3. 到 <https://github.com/MiaoZiKe/tw-rotation/actions/workflows/channel_comments.yml> 按 **Run workflow**（執行），`channel` 選那個頻道、`dry_run` 勾著，看摘要會私訊哪些留言；沒問題就等排程自動跑。
- 防呆：`enabled: true` 但 `message` 空白 → 不私訊、紅燈提醒填內容。自傷關鍵字照樣改送關懷資源訊息（清單沿用頻道④；開之前看一下該頻道常見用語會不會誤判，要排除的詞加進 `self_harm_exclude`）。
- 需要 IG 權杖有 `instagram_business_manage_comments`、`instagram_business_manage_messages` 權限（同 `healing/comment_dm.md`）。

## 7. 出錯怎麼看

| 情況 | 會怎樣 | 去哪裡看 |
|---|---|---|
| 權杖還沒設 | 空跑、綠燈，摘要寫「等待 Andy 設定權杖：…」 | Actions 那一輪的摘要 |
| 佇列空 | 不發，摘要「佇列已空」 | 摘要 |
| 開關關 | 不發，摘要「開關關閉（live=false）」 | 摘要 |
| 今天額度用完 | 不發，下一則留到明天 | 摘要 |
| 發文失敗 | 每平台重試 3 次；仍失敗 → `<代碼>/state/last_run.json` 記原因、該頻道 job 紅燈（GitHub 寄信）；保底時段再補，已發成功的平台不會重發 | `state/last_run.json`、Actions log |

- Actions 頁：<https://github.com/MiaoZiKe/tw-rotation/actions/workflows/channel_post.yml>（頻道④：<https://github.com/MiaoZiKe/tw-rotation/actions/workflows/healing_post.yml>）。
- **完成證據**：`docs/marketing/channels/<代碼>/state/posted.json`（以資料夾名為鍵，記 IG／Threads 的貼文 id 與網址）與該則 `meta.json` 的 `urls`。只說「已排程」不算發出。
- **發現沒發** → 讀 log → 修程式 → 推 main → Actions 頁按 **Run workflow**（執行），`channel` 選頻道、`dry_run` 取消勾選 → 補發。修完寫進 HANDOFF 與本檔修改紀錄。
- 手動模式同頻道④：`verify`（只建容器不發布）、`delete`（刪 target）、`test_delete`（Threads 真發測試 60 秒內刪）；`delete`／`test_delete` 不是空跑時 `confirm` 要填「我確定刪除」。

## 8. ⚠ 已知風險：② 科技透明圈有兩條管線

`tc_post.yml`＋`scripts/tc_post.py`（11-08 建，用 `TC_*` 權杖、佇列 `social/tc/queue/`、開關在 `docs/marketing/social_unit/post_quota.json` 的 `tc`）跟本管線的 `tech`（`TECH_*`、`docs/marketing/channels/tech/queue/`）指的是同一個帳號 Tech_01010909（頻道對應是 CEO 依帳號名推定）。
現在 `tech` 佇列是空的，不會重複發；但**之後只能挑一條放貼文**。在 CEO 決定之前：新貼文只放其中一邊的佇列，不要兩邊都放。

## 9. 程式

| 檔案 | 用途 |
|---|---|
| `docs/marketing/channels/channels.json` | 頻道清單 |
| `scripts/channel_post.py` | 入口：`--channel <代碼>`（其餘參數同 healing_post.py）、`--plan`（工作流用：這輪跑哪些頻道） |
| `scripts/healing_post.py` | 發文邏輯（每個函式吃 `prefix`；不給就是頻道④，行為不變） |
| `scripts/healing_comments.py` | 留言私訊（`--channel`） |
| `scripts/meta_token_refresh.py` | 每週續期（含新三頻道、Threads 短效換長效） |
| `.github/workflows/channel_post.yml`、`channel_comments.yml` | tech／caffaine 的發文與私訊 |
| `tests/test_channel_post.py` | 設定讀取、前綴隔離、不重發、開關關閉略過、缺權杖空跑、排程一致、私訊、續期、沒有 shrimp |

## 修改紀錄

- 2026-11-09：建立（social-ops-lead）。新增 tech、shrimp、caffaine 三個頻道；頻道④沿用 `healing_post.yml` 不動。
- 2026-11-09：Andy：「Shrimp_01010909 不用 其他都幫我確認」→ 拿掉 shrimp（channels.json、工作流、續期、資料夾）；只缺一個平台時摘要列出缺的權杖；新頻道佇列空時驗證模式借頻道④的圖（只建容器不發布）。
