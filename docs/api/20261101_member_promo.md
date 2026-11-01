# 會員活動 API 契約：到期前問卷（送 7 天）／好友邀請（送 14 天 Pro）／許願／公告（2026-11-01）

程式：`workers/account-api/worker.js` 檔尾「到期前問卷＋好友邀請＋活動公告 區塊」；測試：`workers/account-api/tests/promo.test.mjs`。

## 呼叫方式（跟本站其他 API 一樣）
- 一律 **POST**、`content-type: text/plain`、JSON 本文；登入權杖放本文 `t`。前端用 `TwAccount.call(path, body)`（自動帶 `t`、回傳多一個 `_s` 狀態碼）。
  契約表上寫 GET 的路徑，實際也是 POST（Worker 只認 POST，GET 回 404）。
- 日期欄位（`until` 等）一律台北日期 `YYYY-MM-DD`，表示「含當天」仍可用。另附毫秒欄位（`end`、`pro_end`）給需要精算的人。
- 錯誤：`{ error: '代碼' }` ＋狀態碼。後端尚未部署時，預覽版呼叫回 404（`_s=404`）→ 前端當作「沒有這個功能」什麼都不顯示。

## 會員端
| 路徑 | 送 | 回 |
|---|---|---|
| `/v1/me/trial` | `{}` | `{ active, until, base_until, survey_done, survey_eligible, pro_until, end, now }`。`active`＝新會員體驗還沒到期；`base_until`＝問卷延長前的截止日；`survey_eligible`＝體驗剩 ≤3 天且沒填過；`pro_until`＝邀請得到的 Pro 到期日（沒有或已過期為 `null`）|
| `/v1/survey/submit` | `{ sat:1-5, useful:[{p,subs:[]}], improve:[{p,subs:[]}], improve_text, want:[字串], want_text }` | `{ ok:true, until, end, bonusDays:7 }` |
| `/v1/invite/me` | `{}` | `{ code, link, redeemed_count, can_redeem, redeemed:{at,pro_until}｜null, pro_days:14 }`（第一次呼叫自動產生 8 碼） |
| `/v1/invite/redeem` | `{ code }` | `{ ok:true, pro_until, pro_end, days:14 }` |
| `/v1/wish` | `{ text(6~500字), feature(≤60字) }` | `{ ok:true, replaced }`（Pro 體驗期內、一人一個、再送＝覆寫） |
| `/v1/wish/mine` | `{}` | `{ ok:是否在 Pro 期內, wish:{at,feature,text,status}｜null }`（額外） |
| `/v1/ann/state` | `{ aid? }` | `{ seen, trial:{同 /v1/me/trial} }`（額外，給首頁公告） |
| `/v1/ann/dismiss` | `{ aid:'launch-1101' }` | `{ ok:true }`（「不再顯示」記在後端，跨裝置） |

### 問卷後端驗證
體驗期內（welcome 種類的體驗還沒到期）且**剩 ≤3 天**、每人一份、`sat` 1~5 整數、`useful` 至少 1 個母分頁、`useful`／`improve` 各 ≤5 個母分頁（子分頁不限，單一母分頁最多 30 個擋濫用）、key 只能英數與 `_-`（≤40 字）、文字去掉控制字元與 `<>`。成功後把有效的 welcome 到期日 +7 天。
錯誤碼：`done`(409)｜`no_trial`(403)｜`too_early`(403)｜`bad_sat`｜`bad_pick`｜`need_useful`｜`bad_want`(400)。

### 邀請後端驗證
`bad_code`(400)｜`self`(400 自己的碼)｜`used`(409 已用過)｜`not_new`(403 註冊超過 7 天)｜`already_paid`(403 已是付費)｜`same_ip`(403 與邀請人同 IP，或該 IP 30 天內已領過；只比 HMAC，不存原始 IP)｜`too_many`(429 每人每天猜 8 次)｜`no_pro_plan`(503 沒有 pro 方案範本)。
獎勵＝直接寫 perm（plan=pro、expires=現在+14 天），不經 adminPermPut，所以不記 first_paid、不會出現退款。**邀請人本人沒有獎勵**（Andy 沒說，待確認）。

### 許願錯誤碼
`no_pro`(403)｜`bad_feature`｜`bad_text`(400)。

## 管理區（站主限定，其他人 403）
| 路徑 | 回 |
|---|---|
| `/v1/admin/survey` | `{ n, avg, sat:{1..5:數量}, useful:{key:數量}, improve:{key:數量}, useful_tree, improve_tree, want:{選項:數量}, texts:[{at,sat,email,improve_text,want,want_text}], invite:{codes,uses} }`。`useful`／`improve` 是扁平表，母分頁 key 與子分頁 key 都在裡面；`*_tree` 是 `{母key:{n,subs:{子key:數量}}}` |
| `/v1/admin/wishes` | `{ items:[{id,at,email,name,text,feature,status}] }`（status：new／doing／done）|
| `/v1/admin/wish/status` | 送 `{id,status}` 回 `{ok:true}`（額外）|

## 資料與隱私
- 問卷只存 `uid` 與答案，不存 email（管理區顯示時才用 uid 去 users 查）；邀請 IP 只存 HMAC；刪帳號時問卷、邀請碼、使用紀錄、許願、公告紀錄一起刪。
- 新表：`survey`、`invites`、`invite_uses`、`invite_ip`、`invite_try`、`wishes`、`ann_seen`（皆進備份匯出）。
