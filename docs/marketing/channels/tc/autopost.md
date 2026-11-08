# 頻道②「科技透明圈」自動發文（2026-11-08）

> Andy 原話：「開通自動發文，這部分幫我想辦法自動化」。
> 範本：`docs/marketing/channels/ai_intro/ops.md` 第 1～2 節（多頻道隔離設計）。本頁是實作後的操作說明。

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
  post.md       檔頭：status、scheduled_at、platforms、images（同資料夾的 JPEG）
  ig.txt        IG 說明文字（整段原樣）
  threads.txt   【主文】……【第 1 則留言】……
  1_cover.jpg、2_fields.jpg
```

- `status`：`draft` → Andy 核准改 `approved` → 程式發完改 `posted`（失敗改 `error`）。
- 發完回寫：`urls`（全部連結）、`urls_ig`、`urls_threads`、`urls_threads_reply`、`verified_ig`／`verified_threads`（回頭查的 media_type，要是 `CAROUSEL_ALBUM` 或 `IMAGE`）、`done`（已發的平台）。
- IG 發輪播（2～10 張）；Threads 主文帶同一組圖，**圖失敗不退回純文字**，整篇標 error。
- 上限：一天 1 篇、兩篇間隔 20 小時；超過就順延，檔頭寫 `deferred_until`，不算「沒發」。
- 圖要先在 main 上（用 raw.githubusercontent.com 公開網址給 Meta 抓）。

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

## 五、修改紀錄
- 2026-11-08 建立（social-ops-lead）：收件、續期、佇列、發文、監工；廣達稿放進佇列（draft）。
- 2026-11-08 同批：自動測試發文、Threads 自動刪文／IG 到期開 issue、Threads 留言關鍵字公開回覆。
