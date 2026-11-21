# 留言「消息」自動私訊方案（研究與規格，未實作）

台北時間 2026-10-25｜負責：社群營運主管｜性質：只研究，不改程式

## 一、結論

| 平台 | 可行？ | 做法 |
|---|---|---|
| IG | 可行（官方支援） | 留言 webhook → Worker → Private Replies 私訊一包消息 |
| Threads | 私訊不可行（查無私訊 API） | 改成公開回覆留言，附「今日消息頁」連結；或引導到 IG 領取 |

## 二、IG（Instagram API with Instagram Login）

| 項目 | 查證結果 | 信心度 |
|---|---|---|
| 權限 | instagram_business_basic ＋ instagram_business_manage_comments（私回留言用）。舊頁面曾寫 instagram_business_manage_messages，新版文件未列；建議兩個都申請，以免被擋 | 中高（官方新舊頁不一致） |
| webhook 欄位 | 訂閱 comments（直播另有 live_comments） | 高 |
| 時限 | 留言建立後 7 天內可私回（直播僅限直播期間） | 高 |
| 次數 | 每則留言只能私回 1 則；之後要對方回覆，且在其回覆後 24 小時內才能追加 | 高 |
| 存取等級 | 帳號是自己擁有／管理並加進 App，Standard Access 即可，理論上不需 App Review；服務他人帳號才要 Advanced Access＋企業驗證＋審核 | 中（實際以後台為準；有些權限在開發模式下只對 App 角色成員的帳號有效） |
| 帳號 | 必須是專業帳號（商業或創作者） | 高 |
| 呼叫方式 | POST graph.instagram.com/{版本}/{IG用戶ID}/messages，recipient 填 comment_id，message 填文字（一則最多約 1000 字元，需再核對） | 中 |
| 訂閱 | POST /{IG用戶ID}/subscribed_apps，subscribed_fields=comments | 中 |

限制：私訊內含連結可以，但「5 則標題＋連結」要控制在單則字數內，過長就拆成「一則私訊＋網站連結」。

來源：
- https://developers.facebook.com/docs/instagram-platform/private-replies/
- https://developers.facebook.com/documentation/business-messaging/instagram-messaging/features/private-replies
- https://developers.secure.facebook.com/docs/instagram/platform/instagram-api/comment-moderation

## 三、Threads

| 項目 | 查證結果 | 信心度 |
|---|---|---|
| 私訊 API | 查無（多個來源一致說 Threads API 不支援訊息、追蹤、按讚），唯一官方文件未直接確認「沒有」，屬缺席推論 | 中 |
| 回覆留言 | threads_manage_replies（POST 回覆）、threads_read_replies（GET 回覆） | 高 |
| webhook | 訂閱 replies、mentions；需 threads_basic＋threads_read_replies；App 沒有 Advanced Access 就收不到 webhook；私人帳號貼文不通知 | 高（官方） |
| 速率 | 每個帳號 24 小時滾動內最多 1000 則 API 發佈的回覆 | 高 |
| 公開 | 回覆是公開的，所有人看得到；無法「私下」給 | 高 |

重點風險：Threads webhook 需要 Advanced Access（要 App Review＋企業驗證）；若不想審核，可改成「輪詢」：定時用 threads_read_replies 讀自己貼文的回覆（GitHub Actions 每 10~15 分鐘，或 Worker Cron），比對關鍵字後回覆。延遲幾分鐘，但免審核（自己帳號 Standard Access）。

回覆文案範例（公開，注意法遵）：「今日盤前消息整理在這裡：<utm 連結>（資訊整理，非投資建議）」。

來源：
- https://developers.facebook.com/docs/threads/webhooks
- https://developers.facebook.com/docs/threads/retrieve-and-manage-replies
- https://developers.facebook.com/documentation/threads/changelog

## 四、建議架構

```
IG 留言 ──webhook──► Cloudflare Worker（/ig-webhook）
                      1. GET：回 hub.challenge（驗證 verify_token）
                      2. POST：驗 X-Hub-Signature-256（HMAC-SHA256，App Secret）
                      3. 取 comment text、comment_id、from.id、media_id
                      4. 關鍵字：正規化（去空白、全半形）後包含「消息」
                      5. KV 查重（key = comment_id；另 key = from.id+日期）
                      6. 讀 https://miaozike.github.io/tw-rotation/data/<盤前消息JSON>（site 另開一支精簡 JSON，5 則標題＋連結）
                      7. POST Private Reply
                      8. KV 記錄（TTL 8 天）
Threads 貼文回覆 ──(webhook 或輪詢)──► 同一 Worker／Actions ──► POST 公開回覆（reply_to_id）
```

| 議題 | 做法 |
|---|---|
| 驗簽 | 比對 X-Hub-Signature-256；不符回 403；Worker 要在 5 秒內回 200，內容處理用 ctx.waitUntil |
| 防重複 | KV 以 comment_id 去重（Meta 會重送 webhook）；每人每天 1 次；Meta 本身也限一則留言一次 |
| 速率 | 每分鐘最多 N 則（KV 計數）；超過排隊延後；留意 IG 私訊速率上限（官方數字待後台確認） |
| 內容來源 | 網站產出一支 `site/data/premarket_news.json`（日期、5 則標題、連結），Worker 讀取；若日期不是今天，回退成「今日消息尚未更新」＋首頁連結，不送舊聞 |
| 隱私 | 不存留言全文與使用者名稱，只存 comment_id 雜湊與時間；權杖、App Secret 放 Worker Secrets，不進 repo；隱私權政策頁需說明（Meta 上線必要） |
| 法遵 | 私訊文案模板固定，過 legal-compliance：整理新聞、非投資建議、無個股推薦、附免責 |
| 權杖 | IG 長期權杖 60 天到期，要排程續期（refresh_access_token） |

## 五、Andy 要在 Meta 後台做的事（逐格）

先確認他眼前畫面：請他貼 developers.facebook.com/apps 的截圖，下列欄位名以當下畫面為準。

| 步驟 | 網址 | 點哪裡 | 填什麼 |
|---|---|---|---|
| 1 | https://developers.facebook.com/apps | 點進現有 App → 左側「Instagram」→「API setup with Instagram login」 | 不用動既有設定 |
| 2 | 同上頁，「1. Generate access tokens」 | 確認已加入發文用的 IG 專業帳號 | 若帳號是個人帳號，要先在 IG App 改成專業帳號（設定→帳號類型） |
| 3 | 同上頁 Permissions／「App Review → Permissions and Features」 https://developers.facebook.com/apps（進 App 後左側） | 找 instagram_business_manage_comments、instagram_business_manage_messages | 兩個都加進 App；重新產生權杖並勾選這兩項 |
| 4 | 同上頁，「2. Configure webhooks」 | Callback URL 填 | Worker 網址，例如 https://<worker名>.<帳號>.workers.dev/ig-webhook（我會給確切值） |
| 5 | 同上 | Verify token 填 | 自訂一串亂碼，同步放進 Worker Secret（不要貼在對話，直接輸入 Cloudflare） |
| 6 | 同上 | 按「Verify and save」→ 在欄位清單勾 comments → Subscribe | 其他欄位不用動 |
| 7 | 同頁 | 「Add account」或 Subscribe app | 對發文帳號開啟訂閱 |
| 8 | https://developers.facebook.com/apps（App Settings → Basic） | 填「隱私權政策網址」「類別」 | 網址用網站的隱私頁 |
| 9 | App Review → Requests（視後台提示） | 若提示需要 Advanced Access 才送出 | 填使用說明＋錄一支操作影片（留言「消息」→收到私訊） |
| 10 | 做完回我 | | 回「已訂閱 comments」＋把 App ID（可公開）與 IG 用戶 ID 傳給我；App Secret 與權杖只放 GitHub／Cloudflare Secrets |

Cloudflare 端（Andy 或我協助）：Workers 新增 Secrets：APP_SECRET、VERIFY_TOKEN、IG_TOKEN、THREADS_TOKEN；建 KV 命名空間 `dm_dedupe`。連結：https://dash.cloudflare.com/ → Workers & Pages。

審核是否需要與時間：
- 帳號是自己的、只服務自己：理論上 Standard Access 免審核，測試帳號與 App 角色成員可立即測（信心中）。
- 若後台堅持要 Advanced Access：需企業驗證＋App Review，Meta 官方通常數個工作天到 2 週，企業驗證另需數天（信心中，視個案）。
- Threads webhook 一定要 Advanced Access；不想審核就用輪詢方案。

## 六、工時預估

| 項目 | 工時 |
|---|---|
| Worker（驗簽、關鍵字、KV 去重、私訊、記錄） | 0.5~1 天 |
| 網站產出 premarket_news.json＋回退邏輯 | 0.5 天 |
| Threads 輪詢回覆（Actions 或 Cron） | 0.5 天 |
| 測試（測試帳號留言）、權杖續期、法遵審文案 | 0.5 天 |
| 合計 | 約 2~3 個工作天，另加 Meta 審核等待（0~2 週） |

## 七、未解項目（需實測）

1. 新版文件是否仍要求 manage_messages（兩個都申請可避險）。
2. 開發模式下，非 App 角色的留言者是否收得到私訊（測試時用另一個帳號驗）。
3. IG 私訊字數與連結預覽限制。
4. 此容器無法開 Meta 頁面（WebFetch 被擋），以上均來自 WebSearch 摘要，已依規矩交叉比對；實作前請在後台核對一次。
