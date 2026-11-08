# 頻道②「科技透明圈」Meta App Review 送審包（2026-11-08）

> Andy 原話：「讀主留言我自動傳訊息功能，傳之前還會檢查是否有追蹤」。
> 目的：Andy 只要按送出、做身分驗證。送審用的英文說明照 Meta 要求用英文填（下面每段都附中文對照）；畫面按鈕名以 Meta 當下為準。

## 一、到底要不要送審（查證結論）

| 功能 | 需要的權限 | 自己的帳號、開發模式（Standard Access）夠不夠 | 依據與信心 |
|---|---|---|---|
| 發文、刪文（Threads）、IG 建容器 | threads_basic、threads_content_publish、threads_delete、instagram_business_basic、instagram_business_content_publish | **夠**，免審。只發自己的帳號 | Meta：只服務自己擁有／管理的帳號，Standard Access 即可（高） |
| Threads 讀留言＋公開回覆（輪詢） | threads_read_replies、threads_manage_replies | **夠**，免審。我們用輪詢，不用 Threads webhook（webhook 才要 Advanced Access） | Meta Threads webhook 文件（高） |
| IG 讀留言（輪詢） | instagram_business_manage_comments | 讀自己貼文的留言：**夠** | 中高 |
| IG 私訊給**一般網友**（Private Reply、回覆私訊、查追蹤） | instagram_business_manage_messages（＋manage_comments） | **大概不夠**：Meta 文件寫 Standard Access 的 App 只能跟「有 App 角色的人」互動，一般網友收不到 | Messenger／IG 訊息文件（中，官方新舊頁說法不一致；要實測） |
| IG 即時 webhook（comments、messages） | 同上＋App 上線（Live） | **不夠**：收 comments webhook 要 Advanced Access，而且 App 要切 Live | IG webhook 文件（高） |

**結論：要送審**，送 `instagram_business_manage_messages` 與 `instagram_business_manage_comments` 的 **Advanced Access**。
送審期間：發文、刪文、Threads 回覆照常自動跑；IG 私訊用「輪詢版」先跑（`ig_dm.mode: poll`），對有 App 角色的帳號可以先實測整條流程。
審過之後：一般網友也收得到；要即時的話再按一次 `deploy-tc-dm.yml`（勾 subscribe）並把 `mode` 改成 `webhook`。

送審前 Meta 會要求（Meta 強制、只能本人做）：
1. **企業驗證（Business Verification）**：Advanced Access 一定要。要上傳公司或個人事業的證明文件，只能本人在 Meta 商業管理平台上傳。
2. **App 基本資料**：隱私權政策網址、資料刪除說明網址、App 圖示、類別。隱私權政策要寫到「私訊內容只用來回覆、只存雜湊」（第四節有文字可直接用）。
3. **操作錄影**：Meta 審核員要看到「留言 → 收到私訊 → 回好了 → 查追蹤 → 收到整理」的實際畫面（第三節腳本）。

## 二、權限說明（貼到 App Review 每個權限的「How will your app use this permission」）

### instagram_business_manage_comments
English（貼這段）:
> Our app manages a single Instagram professional account that we own ("科技透明圈", a salary-transparency education account). We read comments on our own posts so that when a user comments a specific keyword (for example "透明"), we can send that user one private reply inviting them to receive the key-point summary by direct message. We only read comments on media owned by our account, we never post comments on other accounts, and we store only a one-way hash of the comment ID for de-duplication (no comment text, no usernames).

中文對照：我們只管理自己的一個 IG 專業帳號。讀自己貼文的留言，留言含關鍵字的人，私回一次邀請他收重點整理。只讀自己貼文的留言、不到別人帳號留言、只存留言編號的雜湊。

### instagram_business_manage_messages
English:
> After a user comments the keyword, we send exactly one Private Reply (within Meta's 7-day window) asking them to follow the account and reply "好了" if they want the full summary. When the user replies in the conversation (which creates consent), we call the User Profile API field is_user_follow_business once to check whether they follow the account. If true, we send the summary text with a link to our website; if false, we send one short reminder (maximum three per day). We only respond to messages the user sends us, within the 24-hour messaging window. We do not send promotional broadcasts, we do not message users who have not contacted us, and we store only hashed IDs and timestamps.

中文對照：留言後私回一次（7 天內）；對方在私訊回「好了」（同意成立）才查一次是否追蹤；有追蹤送整理＋網站連結，沒追蹤送一次提醒（每天最多 3 次）。只回覆對方先傳來的訊息、在 24 小時窗內；不群發、不主動找沒聯絡過的人；只存雜湊與時間。

### instagram_business_basic（通常隨附，若要求說明）
English:
> Used to read our own account's username and media list so we can map comments to the correct post and personalize the reply with our handle.

## 三、操作錄影腳本（約 2 分鐘，手機直式或電腦錄螢幕都可以）

Meta 要看到「真的在用」的畫面。需要兩個帳號：A＝科技透明圈（我們的帳號），B＝另一個測試用 IG 帳號（加成 App 的 Instagram 測試人員，開發模式下才收得到）。

| 秒 | 畫面 | 動作 | 旁白字幕（英文，可直接打在影片上） |
|---|---|---|---|
| 0～10 | Meta App Dashboard → App settings → Basic | 停 3 秒讓審核員看到 App 名稱 | "This app manages our own Instagram account 科技透明圈." |
| 10～30 | 用帳號 B 打開帳號 A 的一篇貼文 | 留言「想看透明整理」 | "A user comments the keyword 透明 on our post." |
| 30～50 | 帳號 B 的 IG 私訊匣 | 等到收到「謝謝留言！追蹤 @帳號 後回覆『好了』…」（輪詢版最多等 15 分鐘，剪掉等待段） | "Our app sends one private reply to the comment." |
| 50～70 | 帳號 B | 先不追蹤，直接回「好了」→ 收到「還沒看到你追蹤喔…」 | "The user replies. We check is_user_follow_business: not following yet." |
| 70～95 | 帳號 B | 按追蹤帳號 A → 再回「好了」→ 收到整理與網站連結 | "After following, the user replies again and receives the summary." |
| 95～120 | GitHub 上 `social/tc/dm_config.json` | 捲過 keywords、上限欄位 | "Messages are only sent in response to user actions, with per-user daily limits." |

錄完存成 MP4（Meta 上限以畫面為準，通常 ≤ 100MB），在送審頁每個權限各上傳一次（可以同一支）。

## 四、隱私權政策要補的一段（貼到網站隱私權頁）

> 科技透明圈 Instagram 帳號的自動回覆：當你在我們的貼文留言特定關鍵字，或在私訊回覆我們，我們會使用 Meta 提供的介面回覆你一則訊息，並查詢你是否追蹤本帳號以決定回覆內容。我們只保存留言與帳號編號的單向雜湊值與時間（用來避免重複回覆），保存 30 天後自動刪除；不保存留言內容、私訊內容或帳號名稱。要刪除資料請私訊「刪除我的資料」，我們會在 7 天內處理。
>
> 留言含關鍵字時，我們會透過 Instagram 私訊傳送整理；僅保存去識別化的編號與時間，30 天後刪除。

## 五、送審步驟（Andy 做，附連結）

| # | 連結 | 點哪裡 | 填什麼 |
|---|---|---|---|
| 1 | <https://business.facebook.com/settings/security> | 「企業驗證（Business verification）」→ 開始驗證 | 上傳事業證明（Meta 列的文件之一）；這步只能本人 |
| 2 | <https://developers.facebook.com/apps/> → 點 App → 左側「應用程式設定 → 基本資料（App settings → Basic）」 | 隱私權政策網址、使用者資料刪除網址、App 圖示、類別 | 隱私權政策網址 `https://liguligu-puipui.com/#privacy`（先補第四節文字）；資料刪除網址同一頁 |
| 3 | 同上 App → 左側「應用程式審查 → 權限與功能（App Review → Permissions and Features）」 | 找 `instagram_business_manage_messages`、`instagram_business_manage_comments` → 各按「申請進階存取（Request advanced access）」 | 說明貼第二節英文；影片上傳第三節錄影 |
| 4 | 同上 → 「應用程式審查 → 申請（Requests）」 | 送出（Submit） | 審核通常數個工作天到 2 週（以 Meta 通知為準） |
| 5 | 審過後 | 回 CEO 一句「IG 私訊審過了」 | 其餘（切 Live、部署 Worker、註冊 webhook、改 mode）由程式與 CEO 做 |
