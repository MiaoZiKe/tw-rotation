# 多頻道自動發文（IG 輪播／Reels＋Threads 輪播／影片）總說明

> ★ 2026-11-20 Andy：**Instagram Reels 一律帶 `share_to_feed=false`，只進 Reels 分頁，不進主格狀版面。**（只對 `media_type=REELS` 容器；輪播、圖片、限動、輪播子項目、Threads 都不帶。共用函式：`scripts/healing_post.py` `ig_video_container`；①`scripts/ig_post.py`、②`scripts/tc_post.py` 各自帶。）

> 2026-11-09 Andy 原話：「talk_01010909 已經好了 幫忙協助其他頻道 一起建立 Tech_01010909 Shrimp_01010909 caffaine.ai 以上三個都只差在 Github」。
> 頻道④「談晴說礙」的管線（`docs/marketing/channels/healing/auto_post.md`）擴充成多頻道共用：同一份發文程式，每個頻道自己的佇列、紀錄、開關、權杖。
> 2026-11-09 Andy 補一句：「Shrimp_01010909 不用 其他都幫我確認」→ **水下蝦米不接這套，繼續用 Buffer**；本管線只有 healing、tech、caffaine 三個頻道。
> 帳號與密碼名稱對照：`docs/marketing/channels/accounts.md`（名稱已定案，照用）。頻道①（股市，盤前／盤中／盤後）完全不在這裡，不受影響。

## 1. 頻道一覽

| 代碼 | 頻道 | 帳號 | 權杖前綴 | 資料夾 | 主時段（台北） | 保底補跑 | 工作流 | 開關現況 |
|---|---|---|---|---|---|---|---|---|
| `healing` | ④ 談晴說礙 | talk_01010909 | `HEALING_` | `docs/marketing/channels/healing/` | **20:27** | 21:57 | `healing_post.yml` | live（首篇 `20261108_intro` 在佇列） |
| `tech` | ② 科技透明圈 | Tech_01010909 | `TECH_` | `docs/marketing/channels/tech/` | **12:17** | 13:47 | `channel_post.yml` | live，佇列空 |
| `caffaine` | ③ AI 介紹頻道 | caffaine.ai | `CAFFAINE_` | `docs/marketing/channels/caffaine/` | **12:15**、**21:00**（兩個時段） | 13:43、22:27 | `channel_post.yml` | live，每天最多 2 則（每時段 1 則），佇列空 |

- 設定檔：`docs/marketing/channels/channels.json`（代碼、前綴、佇列、state、開關檔、時段、UTC 排程、每日上限 1、時段理由）。
- 水下蝦米（Shrimp_01010909）不在清單：繼續用 Buffer，這裡不排程、不續期、不建資料夾。
- 每天上限：`channels.json` 的 `per_day` 跟各自 `post_quota.json` 的 `per_day` 取較小者（tech 1；healing 2；caffaine 2，2026-11-15 Andy：「我決定每天兩隻 Reels」）。
- caffaine 一天兩個時段，**每個時段最多開始發 1 則**（見第 10 節），所以兩支不會在同一個時段一起發出去。

### 時段為什麼這樣排
| 頻道 | 理由 |
|---|---|
| 談晴說礙 20:27 | 晚餐後放鬆滑手機；療癒向內容晚上互動最好（沿用 11-08 已上線的時段，不動） |
| 科技透明圈 12:17 | 上班族午休（12:00～13:00）滑手機高峰，科技／產業類在午休最常被點開 |
| AI 介紹 12:15、21:00 | 2026-11-15 Andy 定：「我決定每天兩隻 Reels」，時段 12:15（午休）、21:00（睡前）。舊時段 19:13／20:43 停用 |

除了 Andy 指定的 21:00，全部避開整點與半點（GitHub 排程在整點最擠，常晚幾十分鐘；21:00 那輪晚到也還算同一個時段，22:27 保底補）。保底補跑在主時段後 90 分鐘：主時段沒跑到或失敗時補，當天已發過就不會再發。

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
| `per_day` | 台北每天最多開始發幾則新貼文（tech 1、caffaine 2） |

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
- **IG 權杖兩種都吃（2026-11-10）**：IGAA 開頭（Instagram 登入版）走 `graph.instagram.com`；EAA 開頭（Facebook 登入版）走 `graph.facebook.com`，IG 商業帳號編號用 `/me/accounts` 找（照 channels.json 的 `account` 對帳號名；看得到多個又對不上就不猜，要填 `<前綴>IG_USER_ID`）。verify 模式對 EAA 會在摘要列出：已授權權限、缺少的權限、粉絲專頁幾個、哪個連了哪個 IG、權杖類型與到期。EAA 需要的權限：`instagram_basic`、`instagram_content_publish`、`pages_show_list`（發文必要），`pages_read_engagement`、`instagram_manage_comments`、`instagram_manage_messages`（留言私訊）。留言私訊在 EAA 下改用粉絲專頁權杖走 `/{page-id}/messages`。續期：EAA 要 `META_APP_ID`＋`META_APP_SECRET` 才能用 `fb_exchange_token` 換長效，沒有就跳過續期、只讀到期日（到期前 10 天內告警）。
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
| `scripts/channel_media.py` | 影片放 GitHub Release：`stage`（作者推 media 分支）、`sync`／`testclip`／`clean`（工作流） |
| `tests/test_channel_reels.py` | 兩時段（每時段 1 則、整天 2 則）、影片走 Release、@reels-test 驗證、sync／clean／stage、其他頻道不變 |

## 10. 影片（Reels）與一天兩個時段（2026-11-15，頻道③ CaffAIne）

> Andy 2026-11-15：「我決定每天兩隻 Reels」，時段 12:15 與 21:00。

### 10-1 兩個時段怎麼運作
- `channels.json` 的 caffaine 用 `slots`：`[{"slot": "12:15", "backup": "13:43"}, {"slot": "21:00", "backup": "22:27"}]`，`cron`（UTC）依序 `15 4`、`43 5`、`0 13`、`27 14`，工作流排程一致（`tests/test_channel_post.py` 檢查）。
- 每一輪先算「現在屬於哪個時段」：最近一個已經到的主時段（13:43 保底、GitHub 晚到都還是 12:15 那個時段；12:15 之前算前一天 21:00 那個）。
- `posted.json` 每則記 `"slot": "2026-11-16 12:15"`。**同一個時段已經有一則開始發 → 這一輪不發新的**（摘要寫「這個時段（…）已發 …，每個時段最多 1 則」）；整天仍受 `per_day`=2 限制。
- 一則發一半（例如 IG 成功、Threads 失敗）→ 保底那輪只補沒發的平台，不算新的一則。
- 手動 **Run workflow** 也照同一套：12:15 前按＝前一天 21:00 時段；已發過就不發。
- **指定時段**：`meta.json` 的 `publish_at` 寫那個時段的時間，例如 `"2026-11-16T21:00+08:00"`＝最早晚上那個時段才發（中午那輪會跳過它，先發別則或不發）；`null`＝下一個時段就發。中午那則失敗沒補成，晚上時段會接著發（保底，不會整天 0 則）。

### 10-2 影片放哪裡（為什麼不放 main）
- 一支 Reels 10～30MB、每天 2 支。照頻道④的做法 commit 進 main（佇列一份＋`site/media` 一份）一個月就多 1～2GB，而且 git 歷史刪不掉，每次 clone、每個工作流 checkout 都要背著。
- 改用 **GitHub Release 資產**（tag `channel-media`，標成預發行、不是 latest）：資產不在 git 歷史裡，public repo 不算容量、沒有流量費，單檔上限 2GB；發完 3 天工作流自動刪掉資產與 media 分支（刪掉的分支 GitHub 會回收）。
- 影片本體怎麼到 Release：作者（Claude）把影片推到 **只有影片的分支** `media/caffaine/<資料夾>`（跟 main 沒有共同歷史，`scripts/channel_media.py stage` 一個指令做完），工作流 `sync` 從那個分支拿出來上傳。工作流用 `github.token`，不用另外設 Secret。
- Meta 抓得到嗎：Release 網址會 302 轉到 `release-assets.githubusercontent.com`，回 `application/octet-stream`。11-15 頻道④驗證（run 43704659369）已證明 raw.githubusercontent（一樣是 octet-stream）IG Reels 與 Threads 影片容器都 FINISHED；Release 這條 11-15 用 `@reels-test` 驗證通過（run 43705958501：IG REELS、Threads VIDEO 容器都 FINISHED，未發布）。
- 保底：影片若也放在佇列資料夾（相容舊做法），Release 失敗會退回 raw 網址；只放 media 分支時，`sync` 上傳失敗會在摘要寫原因、這輪發文失敗紅燈、保底那輪再試。
- 頻道④（healing）、② 不受影響：沒寫 `video_host` 的頻道照舊（正式站 `site/media` → raw）。

### 10-3 放一支 Reels 進佇列（Andy 看過、同意的內容才放）
1. 開資料夾 `docs/marketing/channels/caffaine/queue/<YYYYMMDD>_<英文短名>/`，放：
   - `caption.txt`（同輪播規則）
   - `cover.jpg`（IG Reels 封面，1080×1920 JPEG，可省略；小檔，放 main 沒關係）
   - `meta.json`：`{"title": "…", "format": "video", "platforms": ["ig", "threads"], "status": "approved", "publish_at": "2026-11-16T12:15+08:00"}`
2. 影片（1080×1920、H.264＋AAC、≤95MB）推到 media 分支，不要 commit 進 main：
   `python scripts/channel_media.py stage --channel caffaine --folder <資料夾名> --video <片.mp4>`
   （會自動在 `meta.json` 寫 `"video_src": "media/caffaine/<資料夾名>"`；不動工作目錄、不 force push）
3. 把資料夾（meta.json、caption.txt、cover.jpg）commit＋push 到 main。
4. 時段到了工作流：`sync` 上傳 Release → IG `media_type=REELS`（`video_url`、`cover_url`、`share_to_feed=false`）、Threads `media_type=VIDEO`，各自每 10 秒查一次容器、`FINISHED` 才發布（最多等 15 分鐘）→ `posted.json` 記網址。
- 也可以把 `video.mp4` 直接放進佇列資料夾（會讓 repo 變肥，不建議）；工作流一樣會先傳 Release、失敗退回 raw。
- 輪播（`1.png…`、沒寫 `format`）照舊，行為沒變。

### 10-4 怎麼驗（不發布）
- **空跑**：Actions → `channel_post` → **Run workflow**（執行），`channel` 選 `caffaine`、`mode` 選 `post`、`dry_run` 勾著 → 摘要列出下一則、要發的影片網址候選與文字；不連 Meta、不上傳、不寫紀錄。
- **Reels 容器驗證**：`mode` 選 `verify`、`dry_run` **取消勾選**、`target` 填 `@reels-test` → 工作流用 ffmpeg 當場產一支 3 秒測試片（1080×1920、H.264＋AAC）傳到 Release，IG（REELS）與 Threads（VIDEO）各建一個容器等到 `FINISHED`，**不發布**；結果記 `caffaine/state/verify.json` 的 `video`（`url_via: "release"`）。測試片 1 天後自動刪。
- **驗佇列裡某一則**：`target` 填資料夾名（`draft` 也可以），只建容器不發布、不改 status。

## 修改紀錄

- 2026-11-09：建立（social-ops-lead）。新增 tech、shrimp、caffaine 三個頻道；頻道④沿用 `healing_post.yml` 不動。
- 2026-11-09：Andy：「Shrimp_01010909 不用 其他都幫我確認」→ 拿掉 shrimp（channels.json、工作流、續期、資料夾）；只缺一個平台時摘要列出缺的權杖；新頻道佇列空時驗證模式借頻道④的圖（只建容器不發布）。
- 2026-11-10：Andy 重產兩次，三個頻道 IG 密鑰仍是 EAA（Facebook 登入版），verify 全部「Cannot parse access token」→ 程式改成 EAA 走 graph.facebook.com（發文、驗證、刪文、留言私訊、續期都對應），verify 加權限／粉絲專頁診斷；不再叫 Andy 重產（social-ops-lead）。
- 2026-11-15：Andy：「我決定每天兩隻 Reels」→ caffaine 改兩個時段 12:15／21:00（保底 13:43／22:27），每時段最多 1 則、整天 2 則（`per_day` 1→2）；影片改放 GitHub Release（`scripts/channel_media.py`、media 分支），不進 main；verify 加 `@reels-test`（social-ops-lead）。
