# 追蹤解鎖：留言 → 私訊 → 會員帳號看頻道全部文章（共用機制設計）

日期 2026-11-16　狀態：設計稿（未實作、未開任何私訊開關）　分支 `design/follow-unlock`

Andy 11/16 原話：「確保讀者留言之後，我們會私訊給他。若是他沒有追蹤，會請他先追蹤，我們才會傳訊息給他……他如果有追蹤，那他就可以看到那個頻道的所有文章，其他的則隱藏起來……追蹤了科技版跟 AI，那兩個都可以看到……如果沒有註冊，只能看到那一篇文章」＋「這個方式沿用到不同頻道上面」。

## 1. 現況盤點

| 項目 | 現況 | 路徑 |
|---|---|---|
| 留言→私訊（②科技） | 兩段式：留言關鍵字→Private Reply 請追蹤並回「好了」→查 `is_user_follow_business`→送整理；`follow_gate`、每篇專屬關鍵字、私訊接不通改公開回覆 | `scripts/tc_ig_dm.py`、`scripts/tc_dm_keys.py`、`social/tc/dm_config.json` |
| 留言→私訊（④談晴、③CaffAIne） | 輪詢讀留言→先查追蹤→true 才 Private Reply，否則公開回覆保底；`keyword_replies`、Threads 只公開回覆 | `scripts/healing_comments.py`（`--channel`）、工作流 `healing_comments.yml`／`channel_comments.yml` |
| 設定 | ④ `enabled:true`；③ `enabled:false`、`message` 空；② 的設定在 `social/tc/` 且已交接 `tc_post.yml`；① 哩股無 dm_config | `docs/marketing/channels/<頻道>/dm_config.json`、`channels.json` |
| 網站隱藏分頁 | `PRIV` 有 tech／ligu／caffaine／healing，永遠隱藏，只有站主看得到，文章用直接連結可開；清單在 `site/articles/<k>/index.json` | `site/articles.js` 第 85 行 |
| 會員 | Google 登入＋Cloudflare Worker（Durable Object 存帳號、自選）；權杖存 `tw.acct.tok` | `site/account.js`、`workers/account-api/`、`docs/login_setup.md` |
| 功能閘門 | `site/features.js` 功能鍵（現有 `art.list`／`art.read`／`art.cat.*`）、`site/plan_presets.js` 四方案 | 同左 |
| 現有試作 | `preview/tc-unlock`（未進 main），見第 6 節 | |

### 頻道一覽（共用機制＋每頻道一列設定）

| 頻道 | IG／Threads | 留言關鍵字來源 | 文章分頁 id | dm 目前狀態 | 備註 |
|---|---|---|---|---|---|
| ① 哩股哩股 | liguligu0818 | 無（尚未建 dm_config、無關鍵字機制） | `ligu` | 未接 | 需先補 dm_config＋關鍵字來源；第三批 |
| ② 科技透明圈 | Tech_01010909 | `social/tc/dm_config.json` 的 `keywords`＋`post_keywords`＋`ig_dm.contents` | `tech` | 兩段式已建，法遵閘與權杖（需專頁）未全通；試作解鎖在 preview 分支 | 已交接 `tc_post.yml` |
| ③ CaffAIne | caffaine.ai | 佇列 `meta.json` 的 `comment_keyword`＋`dm_config.keyword_replies` | `caffaine` | `enabled:false` | 待 Andy 定私訊內容 |
| ④ 談晴說礙 | talk_01010909 | 同 ③ | `healing` | `enabled:true`（追蹤才私訊，否則公開回覆） | 自傷關鍵字規則最優先，不動 |
| 水下蝦米 | Shrimp_01010909 | — | — | 不接（用 Buffer） | 不在本機制內 |

## 2. 查證（2026-11-16 WebSearch）

- **追蹤判斷可行，但有前提**：Instagram User Profile API 的 `is_user_follow_business`（布林）可判斷對方是否追蹤我們；Meta 規定要先取得使用者同意，同意來源只有「對方傳訊息給我們、點 icebreaker 或常駐選單」，**只留言不算**，直接查會回同意錯誤。需 `instagram_basic`、`instagram_manage_messages`、`pages_manage_metadata`、`pages_read_engagement`、`pages_show_list` 與有 MODERATE 權限的專頁權杖。同意錯誤應視為「未知」而非「沒追蹤」（第三方文件：403、code 230，待實測）。來源：[Meta：User profile API](https://developers.facebook.com/documentation/business-messaging/instagram-messaging/features/user-profile)、[Meta：IG Login 版 User Profile API](https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login/messaging-api/user-profile.md)、[Socioverse：追蹤閘為何在送出之後才查](https://www.socioverse.io/blog/instagram-follow-gate-how-it-works)。這也是 `tc_ig_dm.py` 採兩段式的原因；`healing_comments.py` 的「留言後直接查追蹤」遇到同意錯誤會落入 `unknown_follow`（現為 skip→公開回覆），**要實測確認**。
- **Private Reply 限制**：每則留言只能私回 1 則、留言後 7 天內，對方回覆前不能再傳；對方回覆後開 24 小時窗。來源：[DEV：Comment-to-DM 官方 API](https://dev.to/igmsg/comment-to-dm-on-instagrams-official-api-webhooks-private-replies-and-viral-queues-3mp9)、[Instagram private replies：規則與限制](https://replyrep.io/guides/instagram-private-replies)、[DEV：一則留言一次機會](https://dev.to/tushar_kapil/instagrams-dm-api-gives-you-one-shot-per-comment-9-things-i-learned-the-hard-way-22hg)。這些是第三方整理，Meta 原文待上線前核對。
- **Threads 沒有私訊 API**：官方只有發文、回覆、隱藏回覆、洞察；`threads_manage_replies` 不含私訊；第三方整理一致無私訊端點（有一篇聲稱 Threads 有原生私訊，無 API，視為未證實）。來源：[Meta：Threads API 發布](https://developers.facebook.com/blog/post/2024/06/18/the-threads-api-is-finally-here/)、[Meta：權限參考](https://developers.facebook.com/docs/permissions)、[threads-mcp README](https://github.com/baguskto/threads-mcp)。結論與先前相同：Threads 只能公開回覆。

## 3. 共用機制

### 3.1 流程（IG）

1. 留言含該頻道關鍵字（來源見頻道表）。
2. **第 1 則（Private Reply，留言 7 天內、僅此 1 則）**：不論有沒有追蹤，都送同一則：「想收到完整整理，請先追蹤本帳號，然後在這則私訊回『好了』」＋（已知會被查的話）不放解鎖連結。這一則同時建立同意與 24 小時窗。
3. 對方回「好了」→ 查 `is_user_follow_business`：
   - true → 送**解鎖連結**（第 3.2）＋當篇重點。
   - false → 回「還沒看到你追蹤喔，追蹤後再回一次『好了』」（沿用現有：每人每天最多 3 次）。
   - 同意錯誤／查不到 → 視為未知，不送連結，請對方再回一次。
4. 私訊接不通（EAA 權杖看不到專頁）→ 沿用 `public_fallback`：公開回覆**單篇連結（不帶解鎖碼）**，頻道全部文章不解鎖。
5. 沿用既有安全規則：自傷關鍵字最優先、state 只存雜湊、每人每天上限、法遵閘 `legal_reviewed`。

> 與 `healing_comments.py` 現行「留言後直接查追蹤」的差別：那條路在同意前查會失敗。統一成兩段式（`tc_ig_dm.py` 已實作），healing／caffaine 套用時要把兩段式抽成共用模組 `scripts/follow_dm.py`，各頻道只剩設定。

### 3.2 解鎖連結（帶簽章的一次性代碼，綁頻道）

- 代碼：`base64url(頻道id | 隨機 16 位元組 | 到期時間)` ＋ HMAC-SHA256 簽章，連結 `https://liguligu-puipui.com/#unlock/<代碼>`（放 hash，不進伺服器日誌與 Referer）。簽章金鑰＝GitHub Secret `UNLOCK_HMAC_KEY`＋會員 Worker 同一把 secret（Worker 驗章；repo 不存任何明文碼）。
- 一次性：Worker 以代碼雜湊記「已兌換」，只能兌換一次；到期預設 14 天。每則私訊現發一組，**不是每頻道固定一組**（試作版是固定碼，見第 6 節）。
- 兌換：讀者打開連結 → 站上要求登入／註冊 → 已登入就呼叫 Worker `POST /v1/unlock/redeem {code}` → Worker 驗章、記「帳號 → 頻道」並回傳目前所有頻道。多次兌換不同頻道的碼，帳號權限累積（追蹤科技＋AI 兩個都能看）。
- 沒註冊／沒登入：連結帶的那一篇單篇文章可以讀（單篇 id 放在代碼 payload 與 hash 裡：`#unlock/<代碼>/<文章id>`），其他頻道內容不顯示；登入後兌換才開全頻道。

### 3.3 網站端

- 資料：Worker 為每個帳號存 `channels: { tech: {ts, src}, caffaine: {...} }`（只存頻道 id 與兌換時間，不存 IG 帳號）。`/v1/me` 回傳 `unlocked: ['tech', ...]`。
- `site/articles.js`：`canPriv(k)＝站主 || me.unlocked.includes(k)`（試作版是「已登入＋本機有憑證」）。分頁列只顯示有權限的頻道分頁；「全部文章」清單**不混入**沒權限頻道的文章；沒權限的頻道單篇內頁（直接連結）：已兌換該篇的連結可讀，否則顯示「請從該頻道的私訊連結進入」＋追蹤說明。站主不受限（維持現有行為）。
- 功能鍵（CLAUDE.md 2026-11-02 規則）：`site/features.js` 每頻道一鍵 `art.ch.<頻道id>`（`art.ch.tech`、`art.ch.ligu`、`art.ch.caffaine`、`art.ch.healing`，kind=box、route `#articles/<id>`、有 qnote）；`site/plan_presets.js` 四方案都寫值（建議：訪客 false、註冊會員／Plus／Pro true＝「解鎖」本身才是門檻，不靠方案擋）；體驗額度由 Andy 在「編輯：新會員體驗」自己設，不預設；不在 GRANT_BAN 會自動出現在清單。
- 驗收：`scripts/uitest_sections/<日期>_頻道追蹤解鎖.py`，真的操作：未登入開連結只看單篇、登入兌換後出現頻道分頁並可讀全部、兌換第二個頻道後兩個都在、用到功能鍵上限被鎖／體驗可繼續看／站主不受限、同一碼第二次兌換失敗。
- 公告：同一個 commit 在 `site/notices/features.json` 加「功能更新」（白話：追蹤並註冊後可看哪些頻道全部文章、去哪看）。
- 不得新增 `site/mobile4.css` 尾巴樣式；手機樣式走 `site/m4/` 並限定 ≤640，推 main 前跑桌機守門。

### 3.4 `dm_config` 擴充（只准加選填欄位、預設＝現行行為）

不改任何既有欄位（各頻道每天會加關鍵字）。新增皆為選填，**沒寫＝完全照現行**：

| 欄位 | 預設 | 意義 |
|---|---|---|
| `unlock.enabled` | false | 私訊是否附解鎖連結（false＝送現行純文字／單篇連結） |
| `unlock.channel` | （頻道表 `PRIV` id） | 解鎖綁定的頻道 id |
| `unlock.ttl_days` | 14 | 代碼有效天數 |
| `unlock.ask_follow_text` | 內建文案 | 第 1 則請追蹤的文字 |
| `unlock.not_following_text` | 內建文案 | 沒追蹤時回覆 |
| `unlock.revoke_on_unfollow` | false | 見 3.6 |

`channels.json` 每頻道另加選填 `article_cat`（對應 PRIV id），讓程式知道私訊連結要綁哪個頻道。

### 3.5 防分享連結給沒追蹤的人

| 選項 | 說明 | 建議 |
|---|---|---|
| A 固定共用碼（試作版） | 連結即憑證，轉傳＝解鎖 | 否 |
| B 一次性碼＋綁帳號（本設計） | 兌換後作廢，轉傳的連結已失效；仍可「兌換者把帳號給別人」，不處理 | **採用** |
| C 兌換時再查 IG 追蹤 | 做不到：網站拿不到對方 IG 身分，除非讓讀者做 Instagram 登入（要 Meta 審查，成本高） | 不做 |
| D 同一 IG 使用者碼綁 IG scoped id，兌換時比對 | 需 IG OAuth，同 C | 不做 |

另加：單帳號每日兌換上限（例 5）、單碼錯誤嘗試上限、Worker 記兌換來源雜湊供站主稽核。

### 3.6 取消追蹤後要不要收回

- 選項 1 不收回：解鎖是「曾經追蹤並註冊」，簡單、無隱私負擔。
- 選項 2 定期複查：Worker 查不到讀者的 IG 身分（我們不存也不該存），只能在對方再次私訊時才查得到，不可行。
- 選項 3 到期制：解鎖有效 90 天，到期後再留言／回「好了」重新確認追蹤即可續期。
- **建議：第一版選 1（不收回），第二版選 3**（`unlock.revoke_on_unfollow` 預留，預設 false）。理由：技術上無法即時得知取消追蹤；到期制是唯一可做的折衷。

### 3.7 Threads 替代流程（無私訊）

1. Threads 留言關鍵字 → **公開回覆**（現有 `threads_reply`）：給當篇文章單篇連結（不帶解鎖碼）＋「想看本頻道全部文章：到 IG 同帳號留言同一個關鍵字，私訊會附解鎖連結」。
2. 不在公開留言貼解鎖碼（公開＝全世界可轉傳）。
3. 單篇連結任何人可讀（符合「沒註冊只能看那一篇」）。

## 4. 需要 Andy 本人做的事

| # | 事項 | 擋什麼 |
|---|---|---|
| 1 | Meta 應用程式「liguligu-social」取得 `instagram_manage_messages` 等**進階存取（App Review）**＋App 設 Live（現在只有開發模式，只能私訊測試帳號與應用程式角色成員）；送審資料見 `docs/marketing/channels/tc/app_review/` | 擋「對一般讀者實際送私訊」，不擋網站端與程式開發 |
| 2 | ②③ 帳號連結 Facebook 粉絲專頁，或提供 IG Login 版權杖（EAA 權杖目前看不到專頁＝私訊做不到，只能公開回覆） | 擋該頻道私訊；網站端不擋 |
| 3 | 各頻道私訊內容定稿（③ `message` 目前空白）、法遵確認（以追蹤為條件是否可行，目前信心低，`legal_reviewed`） | 擋該頻道開關 |
| 4 | 會員 Worker 新增解鎖端點與 secret（`UNLOCK_HMAC_KEY`）的**正式部署需 Andy 同意**；他需動手時逐格附連結 | 擋「帳號綁定」上線，網站端與測試環境可先做 |
| 5 | 同意「第一版不收回、第二版到期制」或另指示 | 不擋 |

我不會開任何私訊開關；需要 Andy 動手時，先對他眼前畫面再逐格寫步驟（CLAUDE.md 2026-11-10）。

## 5. 工時與分批

| 批 | 內容 | 估時 | 上線條件 |
|---|---|---|---|
| 0 | 實測：`healing_comments.py` 同意前查追蹤的實際回應、Private Reply 次數與窗口（測試帳號） | 0.5 天 | 無 |
| 1 | 網站端：Worker 解鎖端點＋帳號 `channels`、`articles.js` 權限、功能鍵×4、四方案、uitest 段落、公告；先用站主產生的測試碼驗收 | 3～4 天 | 先推 `preview/follow-unlock`，Andy 同意 Worker 部署後上 main |
| 2 | 私訊端：抽 `follow_dm.py`、`unlock` 欄位、一次性碼產生、②④③ 套用；全部 `unlock.enabled=false` 上線 | 2～3 天 | Meta 審查／專頁權杖（Andy 事項 1、2）通過後逐頻道開 |
| 3 | ① 哩股哩股補 dm_config＋關鍵字來源；Threads 公開回覆文案；第二版到期制 | 2 天 | 視 Andy 排序 |

## 6. 與 `preview/tc-unlock` 試作版的關係

沿用：`?tc=` 前的整體流程（私訊確認追蹤才發連結）、`site/articles.js` 的 `canPriv()` 骨架與分頁列顯示邏輯、`art.ch.tech` 功能鍵與四方案值（改成每頻道一鍵）、`scripts/uitest_sections/20261116_頻道解鎖.py`、`site/notices/features.json` 公告、私訊連結由程式自動改寫（`tc_dm_keys.with_unlock`）。

要改：① 固定碼＋sha256 放 `site/articles/unlock.json` → 改一次性簽章碼＋Worker 驗章兌換，repo 不再放任何碼雜湊；② 解鎖只記 `localStorage tw.chunl`（連結即憑證、換裝置失效、未綁帳號）→ 綁會員帳號（Worker 存，跨裝置）；③ 只有科技一個頻道 → 多頻道累積（`unlocked[]`）；④ `?tc=` 在 query（會進日誌與 Referer）→ 改 hash；⑤ 單篇讀取規則一致保留（沒註冊只看那一篇）。**共用版完成後試作版作廢**，其 Secret `TC_UNLOCK_CODE` 一併廢止。

---
## 摘要（給主控轉 Andy，≤10 行）

1. IG 可判斷是否追蹤（`is_user_follow_business`），但要對方先私訊我們建立同意；所以流程是「留言→私訊請追蹤並回『好了』→查追蹤→追蹤了才送解鎖連結」。
2. Threads 沒有私訊 API：只能公開回覆單篇連結，並引導到 IG 留言拿解鎖連結。
3. 解鎖連結＝簽章、一次性、綁頻道；登入後兌換，帳號累積多頻道；沒註冊只能讀連結那一篇。
4. 網站依帳號頻道權限顯示分頁，其他隱藏；每頻道一個功能鍵、四方案值、驗收段、公告；站主不受限。
5. 適用科技、AI、談晴、哩股四頻道，一套機制，每頻道一列設定；`dm_config` 只加選填欄位，預設照現行。
6. 取消追蹤技術上無法即時得知：建議第一版不收回，第二版改 90 天到期制。
7. 需 Andy：Meta 進階存取審查＋App Live、②③專頁權杖、各頻道私訊內容與法遵、會員 Worker 部署同意。
8. 工時約 8～10 天，分 4 批；先預覽分支，私訊開關全預設關。
9. 科技頻道 `preview/tc-unlock` 試作版（固定碼、只存本機）在共用版完成後作廢。

---
## 7. 第 2 批實作紀錄（網站端，推 `preview/follow-unlock`）與獨立閱讀站

### 7.1 解鎖碼與假兌換（Worker 未上線的過渡）
- 連結格式：`#unlock/<解鎖碼>/<單篇文章 id>`（`site/unlock.js` 在路由前把碼暫存、網址改成單篇；沒註冊的人只讀得到那一篇）。登入後呼叫 `POST /v1/unlock/redeem {code}`，Worker 回 `{unlocked:[...], channel}` 或 `/v1/me` 的 `user.unlocked`，前端自動採用。
- **本批不改、不部署 `workers/account-api`**。端點回 404／連不到時：**預覽網域（`window.TW_PREVIEW`）走假兌換**，只認 `pv-<頻道>`（例 `pv-tech`、`pv-healing-x1`），只存這台裝置、依帳號 uid 分開；**正式網域假兌換不生效**（回「解鎖功能尚未開通」，不會多出任何頻道）。Worker 上線後假兌換仍只在預覽。
- 每頻道功能鍵 `art.ch.tech／ligu／caffaine／healing`：`features.js` 註冊、`plan_presets.js` 四方案都有值（訪客 false，其餘 true）；體驗額度由 Andy 在「編輯：新會員體驗」自設。

### 7.2 CaffAIne、談晴說礙：獨立閱讀站（Andy 11/16）
- 原話：「把 AI 的頻道還有談晴說礙的頻道文章連結獨立出來……點選連結的時候，它會獨立成一個新的網站，專門儲存他們的內文。避免主題差異太大。哩股哩股跟科技本來就可以在原本的網站上面。」
- 網址：`/c/caffaine/#/<文章 id>`、`/c/healing/#/<文章 id>`（清單：`/c/<頻道>/`）。程式 `site/c/reader.js`＋`site/c/reader.css`＋各自 `index.html`，讀同一份 `site/articles/<頻道>/`，不複製文章；沒有哩股哩股導覽與股市功能。內文含 mp4（可播放、有下載鈕）。
- 主站 `#articles/caffaine`、`#articles/healing` 分頁照舊列卡片，卡片連結與舊的 `#article/<id>` 一律開到獨立站（同分頁）；`tech`、`ligu` 維持主站內頁。
- 解鎖規則同主站（同網域共用登入）：單篇連結任何人可讀；清單頁＝站主或帳號已解鎖該頻道。
- **之後私訊、排程、貼文裡的文章連結要改成獨立站網址（本批只列出，不改 `dm_config`）**：
  | 產生處 | 現在 | 要改成 |
  |---|---|---|
  | `scripts/healing_article.py` 第 153 行（印出／登錄的網址） | `https://liguligu-puipui.com/#article/<id>` | `https://liguligu-puipui.com/c/healing/#/<id>` |
  | `scripts/article_publish.py`（依頻道產連結；caffaine、healing 兩頻道） | `…/#article/<id>` | `…/c/<頻道>/#/<id>` |
  | `social/*/queue/*.md` 的 `first_comment`、各頻道 `dm_config` 的 `unlock`／單篇連結產生（`scripts/tc_dm_keys.py with_unlock` 同類） | 主站單篇 | 獨立站單篇；解鎖連結仍是 `#unlock/<碼>/<id>`，主站會自動轉進獨立站 |
  | 排程文案（`healing_comments.py`、`channel_comments.py` 的公開回覆連結） | 主站單篇 | 獨立站單篇 |
  舊的主站連結不會壞（會自動轉過去）。
