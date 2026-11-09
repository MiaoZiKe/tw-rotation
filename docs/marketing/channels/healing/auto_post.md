# 頻道④「談晴說礙」自動發文（IG 輪播＋Threads 輪播）

> 2026-11-08 Andy：「開通自動發文，這部分幫我想辦法自動化」。這句是頻道④開自動發文的授權（之前寫的「Andy 決定前不開自動發文」到此為止）。
> 跟頻道①（盤前／盤中／盤後）完全分開：不同的 Secrets、不同的開關、不同的佇列與紀錄。頻道①的 `docs/marketing/social_unit/post_quota.json` 沒有動。

## 1. 什麼時候發、發什麼

| 項目 | 內容 |
|---|---|
| 工作流 | `.github/workflows/healing_post.yml`（Actions 頁：<https://github.com/MiaoZiKe/tw-rotation/actions/workflows/healing_post.yml>） |
| 時段 | 每天台北 **20:27**（主時段）；**21:57** 保底補跑（主時段沒跑到或失敗時補上；當天已發過就不會再發）。GitHub 排程常晚幾分鐘到幾十分鐘 |
| 每次發幾則 | 最多 1 則；每天最多 `per_day` 則（目前 1，新帳號前幾週維持一天 1 則） |
| 發哪一則 | 佇列裡**資料夾名排最前面**、`status` 是 `approved`、`publish_at` 已到（或留空）、還有平台沒發的那一則 |
| 平台 | IG 輪播（用 `n.jpg`，caption 用 `caption.txt` 全文）＋ Threads 輪播（用 `n.png`，超過 500 字截斷加「…」） |
| 圖片網址 | `https://raw.githubusercontent.com/MiaoZiKe/tw-rotation/main/<路徑>`（repo 公開；實測 PNG 回 `image/png`、JPG 回 `image/jpeg`）。真的發之前會先確認 Meta 抓得到 |

## 2. 放新貼文進佇列

1. 開一個資料夾：`docs/marketing/channels/healing/queue/<YYYYMMDD>_<英文短名>/`（例如 `20261112_rent`）。**資料夾名用英數**，圖片網址比較不會出錯；排序就照這個名字。
2. 放進：
   - `1.png`、`2.png`…（從 1 連號，IG 最多 10 張）。IG 只收 JPEG：同名 `1.jpg`… 可以自己放，沒放的話工作流會自動從 PNG 轉（`python scripts/healing_post.py --prepare`）並先推上 main。
   - `caption.txt`：貼文內文（≤2200 字、#標籤 ≤30 個）。
   - `meta.json`：
     ```json
     {"title": "給人看的名字", "platforms": ["ig", "threads"], "status": "approved", "publish_at": null}
     ```
     `status`：`approved` 才會發；`draft` 不碰；發完自動改成 `posted` 並寫入 `urls`。
     `publish_at`：`null`＝下一個時段就發；要指定最早時間就寫台北時間，例如 `"2026-11-12T20:27+08:00"`（時間沒到會先發下一則，不會卡住佇列）。
3. 推上 main。圖若是 AI 生成的，資料夾要有 `ai_review.md`（art-director 審過）才准放 `approved`；不准放比比。
4. 推之前可以本機看一次會發什麼：`python scripts/healing_post.py --dry-run`。

首篇已放好：`queue/20261108_intro/`（首篇自介短版 3 張晝版，來源 `templates_tqsa_v3/首篇_短版3張/晝版/`，內文照該資料夾 README「貼文內文」）。

## 3. 開關

`docs/marketing/channels/healing/post_quota.json`：

| 欄位 | 值 | 意思 |
|---|---|---|
| `live` | `true` | `false`＝整個停發（以成功結束、不連 Meta） |
| `per_day` | `1` | 台北每天最多開始發幾則新貼文（發到一半的那則補完不算） |

## 4. 出錯怎麼看

| 情況 | 會怎樣 | 去哪裡看 |
|---|---|---|
| 權杖還沒設 | **空跑**：印出會發的圖網址與內文，不呼叫 Meta，綠燈，摘要寫「等待 Andy 設定權杖」 | Actions 那一輪的摘要 |
| 只設了一個平台的權杖 | 只發有權杖的平台，另一個等設好後下一輪補 | 摘要的 ⚠️ |
| 發文失敗 | 每個平台自動重試 3 次；仍失敗 → `state/last_run.json` 記原因、工作流紅燈（GitHub 寄信）；21:57 保底會再補一次，已發成功的平台**不會重發** | `state/last_run.json`、Actions log |
| 佇列空了 | 不發，摘要寫「佇列已空」 | 摘要 |
| 今天額度用完 | 不發，下一則留到明天 | 摘要 |

**完成證據**：`docs/marketing/channels/healing/state/posted.json`（以資料夾名為鍵，記 IG／Threads 的貼文 id 與網址），以及該則 `meta.json` 的 `urls`。只說「已排程」不算發出。
**發現沒發** → 讀 log → 修程式 → 推 main → 到 Actions 頁按 **Run workflow**（執行）、`dry_run` **取消勾選** → 補發。修完寫進 HANDOFF 與本檔最下面的修改紀錄。

## 5. 權杖（Andy 要做的一次性設定）

逐格步驟由 CEO 另外提供（照 CLAUDE.md 10-16 規則：每格填什麼、每步附連結）；本檔只列名稱。Secrets 頁：<https://github.com/MiaoZiKe/tw-rotation/settings/secrets/actions>

| Secret 名稱 | 必填？ | 說明 |
|---|---|---|
| `HEALING_IG_ACCESS_TOKEN` | **必填** | 談晴說礙 IG 帳號的長效權杖（Instagram 登入版） |
| `HEALING_THREADS_ACCESS_TOKEN` | **必填** | 談晴說礙 Threads 帳號的權杖（要 60 天長效，見下） |
| `HEALING_IG_USER_ID`、`HEALING_THREADS_USER_ID` | 選填 | 沒填就用權杖呼叫 `/me` 自動查 |
| `THREADS_APP_SECRET` | 選填 | Meta app「liguligu-social」的 Threads App secret。有它的話，Threads 權杖若是 1 小時短效，工作流會自動換成 60 天長效並寫回 |
| `HEALING_*_ACCESS_TOKEN_AUTO` | **不用建** | 續期／換長效時程式自己寫回 |

- **絕不能用頻道①的帳號發**：程式只讀 `HEALING_*`，就算環境裡有 `IG_ACCESS_TOKEN`／`THREADS_ACCESS_TOKEN` 也不會用（有測試鎖住）。
- **Threads 短效權杖**：Meta 開發者後台產生的 Threads 權杖是 1 小時短效。工作流每次真的發之前會先試續期；續期失敗而且有 `THREADS_APP_SECRET` → 自動換長效（`th_exchange_token`），用 `META_SECRETS_PAT` 寫回 `HEALING_THREADS_ACCESS_TOKEN_AUTO`；沒有 app secret → 摘要提示「Threads 權杖可能是 1 小時短效，請換成 60 天長效」（手動換法見 `docs/marketing/social_unit/meta_api_setup.md` 第 7 步）。剛換好的長效權杖未滿 24 小時也會續期失敗，所以這個提示寫「可能」。
- **續期**：`meta_token_refresh.yml` 每週日台北 10:23 一起續期 `HEALING_THREADS_ACCESS_TOKEN`、`HEALING_IG_ACCESS_TOKEN`，新字串用 `META_SECRETS_PAT` 寫回 `*_AUTO`；到期前 10 天仍未續期成功會開 issue（跟頻道①同一套，見 `docs/security/20261101_meta_token_refresh.md`）。沒設 `HEALING_*` 時狀態是 missing，不告警。
- 權杖只在環境變數，log 一律 `::add-mask::` ＋遮蔽，`posted.json`／`last_run.json` 不含權杖。

## 5-1. 權杖要勾的權限（Andy 產生權杖時）

| 平台 | 要勾的權限 | 用途 |
|---|---|---|
| IG（Instagram 登入版） | `instagram_business_basic`、`instagram_business_content_publish` | 發文（必要） |
| IG | `instagram_business_manage_media`（畫面上有這個就勾；沒有就略過） | 試著用 API 刪文 |
| Threads | `threads_basic`、`threads_content_publish` | 發文（必要） |
| Threads | `threads_delete` | 自動刪文、測試發文後自動刪 |
| Threads | `threads_read_replies`、`threads_manage_replies` | 之後讀／管理留言 |

## 5-2. 自動測試發文、自動刪文（2026-11-08 Andy：「我希望可以自動化全部 包含測試發文 還有自動刪文」）

| 模式（Run workflow 的 `mode`） | 做什麼 | 會不會公開發出 |
|---|---|---|
| `post`（排程固定用這個） | 正式發佇列下一則。**某平台權杖第一次出現**（`state/verify.json` 沒有該平台的 verified）→ 先自動跑驗證模式，通過才發；失敗就紅燈、摘要寫原因、那個平台不發 | 驗證通過後才發 |
| `verify` | IG 與 Threads 各建一次輪播容器（用佇列下一則的圖）、輪詢到 FINISHED、**不呼叫 publish**；通過記 `state/verify.json` | 不會 |
| `delete` | `target` 填佇列資料夾名（刪那一則已發的 IG＋Threads）或貼文 id；`platform` 可選只刪一個平台。Threads 刪掉在 `posted.json` 標 `deleted`；IG 先試 API 刪除，回不支援就摘要寫「IG 無法用 API 刪除，需手動」並列進 `state/manual_delete.json` | — |
| `test_delete`（只有 Threads） | Andy 要求「先真發一則測試再刪」時用：用佇列圖真發一則 Threads 測試輪播（文字「系統測試貼文，會在 60 秒內自動刪除」）→ 拿到 id 立刻刪 → 記 `state/tests.json`（不進 `posted.json`）。IG 不做真發測試，只用驗證模式 | 會，幾十秒後刪掉 |

- `delete`、`test_delete` 不是空跑時，`confirm` 要填「我確定刪除」一字不差，否則什麼都不做。
- 手動觸發的 `dry_run` 預設勾著（只印出會做什麼）；要真的做要取消勾選。
- IG（Instagram 登入版）能不能用 `DELETE /{media_id}` 刪文：**還沒實測**（要等權杖），程式先試，不行就列手動清單。

## 6. 程式

| 檔案 | 用途 |
|---|---|
| `scripts/healing_post.py` | 取下一則、檢查格式、空跑、驗證模式、發 IG／Threads、刪文、寫紀錄（`--dry-run`、`--prepare`、`--mode post/verify/delete/test_delete`、`--target`、`--platform`） |
| `scripts/social_publish.py` | 沿用：`publish_threads`（輪播、輪詢 FINISHED、重試）、`http`、`resolve_user_id`、`redact` |
| `scripts/meta_token_refresh.py` | 每週續期，`healing_threads`／`healing_ig` 兩個平台 |
| `tests/test_healing_post.py` | 空跑、取下一則、不重發、開關、缺權杖、短效換長效、權杖不外洩、驗證模式、刪文、測試發文再刪 |

IG 輪播流程同 `scripts/ig_post.py` 的 `publish()`（子項 → CAROUSEL → media_publish → permalink），改走 `social_publish.http` 以便遮蔽權杖與輪詢「Media Not Found」。

## 修改紀錄

- 2026-11-08：建立（social-ops-lead）。首篇 `20261108_intro` 入佇列，等權杖設好後下一個 20:27 時段發。
- 2026-11-08：USER_ID 改選填（/me 自動查）；Threads 短效自動換長效（THREADS_APP_SECRET）；加驗證模式、刪文、Threads 測試發文再刪（Andy：「我希望可以自動化全部 包含測試發文 還有自動刪文」）。
