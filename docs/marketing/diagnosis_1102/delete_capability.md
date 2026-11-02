# IG／Threads 刪文能力盤點（2026-11-02 台北，社群發文營運主管）

> Andy 原話：「因為可能要重新開始，IG Thread 文章會需要砍掉，你需要幫我看看你是否有砍掉的功能」。
> 本次**只做工具、沒有刪任何一則**。真的刪要等 Andy 確認要刪哪些。

## 1. 結論（先看這段）

| 問題 | 答案 |
|---|---|
| 原本 repo 有沒有刪文功能 | **沒有。** `scripts/threads_post.py`、`ig_post.py`、`social_publish.py`、`meta_perm_check.py`、`threads_v2.py`、`meta_token_refresh.py` 與 `.github/workflows/` 社群相關 yml 全部搜過 `delete／DELETE／刪`，0 筆。 |
| Threads 能不能用 API 刪 | **能。** 官方 `DELETE /{threads-media-id}`，要 `threads_basic`＋`threads_delete` 權限，每帳號 24 小時滾動 100 則。 |
| IG 能不能用 API 刪 | **我們這套不能。** 官方刪除端點只開給「Instagram API with **Facebook** Login」（要 IG 綁 Facebook 粉專、`instagram_manage_contents` 權限）；我們用的是「Instagram API with **Instagram** Login」，不支援。IG 只能在 App 內手動刪（有批次刪除）。 |
| 現在的權杖有沒有刪文權限 | **大概沒有**（推論，還沒實測）：當初設定只加了 `threads_basic`、`threads_content_publish`，後來加了洞察；文件與程式從沒申請過 `threads_delete`。工具的「列清單」模式會實際測一次並寫出結果（見第 3 節）。 |
| 新做了什麼 | `scripts/social_delete.py`（列清單／真刪）、`.github/workflows/social_delete.yml`（只能手動觸發，預設只列清單）、`social/delete_keep.json`（保留清單：廣達、華碩兩篇薪資文）、`tests/test_social_delete.py`（11 項，全過）、`meta_perm_check.py` 多查刪文額度與回覆清單兩項。 |

## 2. 官方能力表

| 平台 | 內容 | 能否 API 刪 | 需要的權限 | 限制 | 信心度 | 來源 |
|---|---|---|---|---|---|---|
| Threads | 自己的貼文（文字／圖／輪播） | 能：`DELETE graph.threads.net/v1.0/{id}`，回 `success`＋`deleted_id` | `threads_basic`＋`threads_delete` | 只能刪自己帳號發的；每帳號 24 小時滾動 100 則；可查 `GET /me/threads_publishing_limit?fields=delete_quota_usage,delete_config` | 高（官方文件） | A、B |
| Threads | 自己的串文回覆（我們每篇 6 則串文的第 2 則起） | 應該能（回覆也是自己發的貼文物件，官方寫「authenticated user 建立的貼文」） | 同上；**要先列得出回覆 id** 還需 `threads_read_replies` | 刪主文時串文會不會一起消失，官方沒寫 → 先刪 1 篇實測 | 中（官方沒逐字寫到回覆；有一篇第三方說不能，但它也說 threads_delete 沒開放，與官方矛盾，判定過時） | A、D |
| Threads | 轉發（Repost） | 未查證：官方刪除頁沒提到轉發；第三方工具宣稱能刪 | — | 我們沒有轉發別人的貼文，影響小 | 低 | A、D |
| Threads | 別人在我們貼文底下的留言 | 不能刪，只能「隱藏」（`threads_manage_replies`） | — | 不在本次範圍 | 中 | D |
| IG | 動態（貼文／輪播）、Reels | **Instagram 登入版不能**；Facebook 登入版能（2025-12 新增 `DELETE /{ig-media-id}`） | Facebook 登入版：`instagram_basic`＋`instagram_manage_contents`，IG 要綁粉專 | 我們目前的權杖、帳號設定都不符合 | 中高（官方參考頁寫「只支援 Facebook Login」，官方部落格寫要綁粉專；第三方 2026-04 整理一致） | C、E、F |
| IG | 限時動態 | 同上（Facebook 登入版才有）；限動本來 24 小時後就自動下架、進封存 | 同上 | 我們的限動都已過期，不用刪 | 中 | E |
| IG | App 內手動刪 | 能，有批次：個人檔案 → ☰ →「你的活動」→「貼文」／「Reels」→「選取」→ 勾選 →「刪除」或「封存」 | 不用權限 | 刪掉先進「最近刪除」30 天可還原；限動只留 24 小時 | 中（媒體報導，非官方說明頁） | G、H |

來源：
- A 官方 Threads 刪文：<https://developers.facebook.com/docs/threads/posts/delete-posts>
- B 官方 Threads 總覽（刪除額度、`threads_publishing_limit`）：<https://developers.facebook.com/docs/threads/overview>
- C 官方 IG Media 參考（刪除段標明只支援 Facebook Login）：<https://developers.facebook.com/docs/instagram-platform/reference/instagram-media/>
- D 第三方（回覆／轉發，信心低）：<https://www.postpeer.dev/blog/how-to-manage-threads-comments-with-api>、<https://github.com/dstN/threadsDeleter>
- E 官方部落格 2025-12-03 IG API 更新（新增 IG Media Deleting API、帳號需連結粉專）：<https://developers.facebook.com/blog/post/2025/12/03/instragram-api-updates/>
- F 第三方 2026-04 IG 官方 API 整理（刪除列為 Facebook Login 限定）：<https://gist.github.com/jameschapman2c/65eff9f54a2d350b17a6ce5127b9fe42>
- G Engadget 批次刪除報導：<https://www.engadget.com/instagram-your-activity-bulk-delete-posts-comments-194138892.html>
- H 最近刪除 30 天：<https://9to5mac.com/2021/02/02/how-to-restore-deleted-instagram-posts/>

查過的關鍵字（7 組）：Threads API delete post threads_delete；Threads delete 100 per 24 hours；Threads delete reply repost；threads_publishing_limit delete_quota_usage；Instagram Login delete media；IG Media Deleting API Instagram Login；Instagram Your activity bulk delete／Recently deleted。
⚠ 我只能讀搜尋摘要、打不開原文；「IG 登入版不支援刪除」是兩個官方頁＋一個第三方的摘要互相印證，不是我讀過全文。

## 3. 工具用法

### 3.1 先列清單（不刪任何東西）——預設模式

GitHub 上跑：<https://github.com/MiaoZiKe/tw-rotation/actions/workflows/social_delete.yml> → **Run workflow**（執行工作流）→ `mode` 保持 **list** → 按綠色 **Run workflow**。跑完在該次執行頁最下面 **Artifacts**（產出檔）下載 `social-delete-list-…`，裡面有：

| 檔案 | 內容 |
|---|---|
| `list.json` | Threads（貼文＋自己的串文回覆）與 IG（動態／Reels／24 小時內限動）全部：id、台北時間、前 40 字、觀看數、連結、是否保留；另有一欄 `threads_delete_permission`＝**現在的權杖有沒有刪文權限**（實測結果） |
| `list_threads_ids.txt` | 要刪的 Threads id 草稿（已扣掉保留清單）；不想刪的那行刪掉或前面加 `#` |
| `list_ig_manual.md` | IG 手動刪除清單（每則附 permalink，保留的標「保留，不要刪」） |

本機（有權杖時）：`python scripts/social_delete.py --out out/social_delete/list.json`（`--no-views` 不抓觀看數、`--platform threads` 只列 Threads）。

### 3.2 真的刪（只有 Threads，等 Andy 確認後才跑）

同一個工作流：`mode` 選 **delete**、`confirm` 填 **我確定刪除**（一字不差）、`ids` 貼 id（逗號或空白分隔）或 `ids_file` 填 repo 裡的清單檔路徑、`max` 預設 90。
本機：`python scripts/social_delete.py --execute --ids-file ids.txt --confirm 我確定刪除`。

安全設計：
- 少了 `--execute`、`--ids-file`、`--confirm 我確定刪除` 任一個 → 一個請求都不送（測試驗過）。
- 保留清單 `social/delete_keep.json`：Threads `17877487434633706`（廣達）、`18017139806967577`（華碩）＋它們底下自己的串文回覆；IG `18099107264560696`（廣達）、`18207378916373397`（華碩）。ids 檔裡就算有也不刪。另可加 `--keep-id`。
- 只刪「這個帳號清單裡查得到」的 id，查不到的跳過。
- 先查刪除額度：權杖沒有 `threads_delete` → 一則都不刪、直接停（回傳碼 3）。
- 逐則刪、每則結果寫 `result.json`（成功／失敗原因）；遇到權杖失效（190）、權限不足（10、200～299）、頻率上限（4、17、32、613）立即停。
- 權杖只讀環境變數 `THREADS_DELETE_TOKEN`（優先）或 `THREADS_ACCESS_TOKEN`、`IG_ACCESS_TOKEN`；不印、不寫檔，錯誤訊息遮蔽。

建議順序：先刪 **1 篇**沒有人看的盤前文 → 再跑一次 list，看它的串文回覆有沒有跟著消失 → 再決定 ids 要不要包含回覆 → 分天刪（每天最多 100 則；46 篇主文＋串文回覆估計要 2～3 天）。

## 4. Andy 要做的設定（擋「真的刪 Threads」，不擋列清單、不擋發文；可以等決定要刪再做）

目的：做一把**有刪文權限**的新 Threads 權杖，存成**新的** Secret `THREADS_DELETE_TOKEN`。發文用的舊權杖完全不動（因為發文流程優先讀程式自動續期的 `THREADS_ACCESS_TOKEN_AUTO`，改舊的那把也不會生效）。約 10 分鐘。

| # | 連結 | 點哪裡／填什麼 | 不用動的 |
|---|---|---|---|
| 1 | <https://developers.facebook.com/apps/> | 點 `liguligu-social` 這個應用程式 | 其他 app |
| 2 | 同一頁左側 | **Use cases**（使用案例）→ **Access the Threads API**（存取 Threads API）那列的 **Customize**（自訂） | IG 那個使用案例 |
| 3 | 上方 **Permissions**（權限）分頁 | 找 `threads_delete` → 按右邊 **Add**（新增），變成 **Ready for testing**（可測試）；再找 `threads_read_replies` 一樣按 **Add**（列出串文回覆要用） | 已有的 `threads_basic`、`threads_content_publish`、`threads_manage_insights` 不要移除 |
| 4 | 上方 **Settings**（設定）分頁 → 往下到 **User Token Generator**（使用者權杖產生器） | 你的 Threads 帳號那列 → **Generate Access Token**（產生存取權杖）→ 跳出 Threads 授權視窗，**確認清單裡有「刪除」相關權限**再按 **Continue**（繼續）→ 複製出現的權杖 | 不要貼到聊天室 |
| 5 | 瀏覽器網址列（1 小時內做） | 貼上 `https://graph.threads.net/access_token?grant_type=th_exchange_token&client_secret=<App secret>&access_token=<第 4 步的權杖>`；App secret 在 <https://developers.facebook.com/apps/> → 這個 app → **App settings → Basic**（應用程式設定 → 基本資料）→ **App secret** 旁 **Show**（顯示） | 網頁顯示的 `access_token` 那一長串（不含引號）就是長效權杖，複製 |
| 6 | <https://github.com/MiaoZiKe/tw-rotation/settings/secrets/actions/new> | **Name**（名稱）填 `THREADS_DELETE_TOKEN`；**Secret**（值）貼第 5 步那串（前後不能有空白）→ **Add secret**（新增） | `THREADS_ACCESS_TOKEN`、`THREADS_ACCESS_TOKEN_AUTO`、`IG_*` 全部不要改、不要刪 |
| 7 | <https://github.com/MiaoZiKe/tw-rotation/actions/workflows/social_delete.yml> | **Run workflow** → `mode` 保持 **list** → 綠色 **Run workflow** | 其他欄位不用填 |

**做完回我**：「THREADS_DELETE_TOKEN 加好了，list 跑完了」一句話即可，不要貼權杖。我會讀 artifact 裡的 `threads_delete_permission` 確認有權限，再把要刪的清單給你勾。
第 4 步授權視窗看起來跟我寫的不一樣、或第 3 步找不到 `threads_delete` → 截圖給我，不要硬做。

IG：不用設定任何東西。照 `list_ig_manual.md` 在 App 內刪（「你的活動」可一次勾多則）。若一定要自動刪 IG，得改走 Facebook 登入版（IG 綁粉專、重新建權杖、改程式），約半天工，現階段不建議。

## 5. 風險

| 風險 | 說明 | 處理 |
|---|---|---|
| 刪掉不能復原 | Threads 用 API 刪的，官方沒有還原端點；App 內刪的據第三方說有 30 天「最近刪除」，但 API 刪的是否也進去**未查證**，一律當作不能還原。IG 手動刪先進「最近刪除」30 天可還原，超過永久刪除。 | 刪前先跑 list 留存清單（artifact 留 30 天；建議另存一份）；保留清單先寫好；先刪 1 篇試 |
| 洞察數據跟著消失 | 貼文刪了，該則的觀看／互動在平台上就查不到 | repo 已有 `social/threads/insights/metrics.csv` 與 posts_catalog 的歷史紀錄，不受影響 |
| 帳號權重 | **官方沒有任何「刪文會降權」的說法**（查不到來源）；大量短時間刪除可能被系統當異常行為，屬推測 | 工具每則間隔 1 秒、每天封頂 90 則（官方上限 100），分天刪 |
| 舊連結失效 | `state/posted.json`、queue 檔 `urls:` 指向的連結會變 404；監工若回頭驗連結會誤判 | 刪完把這些紀錄標記為已刪（另開工），監工只驗當天新發的 |
| 自動發文還在跑 | 「重新開始」期間排程照樣每天發 6 篇以上，會一邊刪一邊多出新文 | 要不要暫停 social-live／social_news 排程，等 Andy 決定（工具本身不動排程） |
| 權杖外洩 | 新權杖權限比原本多一個「刪除」 | 只放 GitHub Secrets；刪完可以把 `THREADS_DELETE_TOKEN` 刪掉、到 Meta 後台移除 `threads_delete` |
