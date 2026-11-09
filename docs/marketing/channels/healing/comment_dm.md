# 談晴說礙：IG 留言自動私訊（讀主留言 → 查追蹤 → 私訊）

台北時間 2026-11-08 建立｜負責：社群營運主管
Andy 原話（2026-11-08）：「我希望可以自動化全部……以及讀主留言我自動傳訊息功能，傳之前還會檢查是否有追蹤」。
前置研究：`docs/marketing/social_unit/comment_dm_plan.md`（IG Private Replies 可行；Threads 沒有私訊 API；webhook 與輪詢比較）。

## 一、做了什麼

| 項目 | 檔案 |
|---|---|
| 程式 | `scripts/healing_comments.py` |
| 工作流 | `.github/workflows/healing_comments.yml`（每 15 分鐘，台北每小時 :07／:22／:37／:52） |
| 設定（Andy 可改） | `docs/marketing/channels/healing/dm_config.json` |
| 紀錄（自動寫回 main） | `docs/marketing/channels/healing/state/comments_dm.json` |
| 測試 | `tests/test_healing_comments.py` |

流程（輪詢，不用 webhook，免架伺服器）：

1. 找貼文：`state/posted.json` 裡近 7 天的 IG 貼文（頻道④自動發文寫的）＋ `GET /{IG帳號編號}/media` 近 7 天（含手動發的）。
2. 讀主留言：`GET /{貼文編號}/comments?fields=id,text,timestamp,username,from{id,username}`（只回主留言，不含回覆串）。
3. 每則新留言依序判斷：

| 情況 | 處理 | 紀錄的結果代碼 |
|---|---|---|
| 自己帳號留的 | 略過 | `own` |
| 留言超過 7 天（Meta 私回期限） | 不送 | `expired` |
| 有自傷關鍵字 | **不送一般私訊**，改送關懷資源訊息（不看追蹤）；摘要＋警告提醒 CEO | `care` |
| 有追蹤（`is_user_follow_business=true`） | 私訊預設文案 | `dm` |
| 沒追蹤 | 不私訊 | `skip_not_follower` |
| 查不到追蹤狀態 | 預設不私訊（`unknown_follow=skip`）；改成 `send` 就照樣私訊 | `skip_unknown_follow`／`dm_unknown_follow` |
| 私訊送出失敗 | 下一輪重試，最多 3 輪 | `send_failed` |

4. 私訊用 Private Replies：`POST /{IG帳號編號}/messages`，`recipient={"comment_id": 留言編號}`。Meta 規定每則留言只能私回 1 次、留言 7 天內。
5. 每輪最多送 `max_per_run`（預設 20）則；超過的留到下一輪（仍在 7 天內就會送）。
6. 同一則留言只處理一次（以留言編號的雜湊去重）。

## 二、設定檔 `dm_config.json`

| 欄位 | 預設 | 意思 |
|---|---|---|
| `enabled` | `true` | `false`＝整個停，不讀留言、不私訊 |
| `only_followers` | `true` | 只私訊有追蹤的人 |
| `unknown_follow` | `"skip"` | 查不到追蹤狀態時：`skip` 不私訊；`send` 照樣私訊 |
| `max_per_run` | `20` | 每輪最多送幾則 |
| `lookback_days` | `7` | 讀幾天內的貼文 |
| `message` | 見下 | 一般私訊文案 |
| `care_enabled` | `true` | 自傷關鍵字時要不要送關懷資源訊息 |
| `care_message` | 見下 | 關懷資源訊息 |
| `self_harm_keywords` | 死、不想活、自殺、輕生、結束生命…… | 命中任一個就走關懷訊息 |
| `self_harm_exclude` | 笑死、累死、熱死、死忠…… | 先把這些詞拿掉再比對，避免「笑死」被誤判 |

一般私訊預設文案（客觀、不用「我／我們」、不叫人做事、不放投資或醫療／諮商字眼）：

> 謝謝留下今天的晴 ☀️
> 這裡每天說一點礙，也談一點晴。
> 日子很硬的時候，記得光還在縫裡。

關懷資源訊息（依 `legal.md` 2-7；只給資源，不做諮商式回應）：

> 看到這則留言，先把幾個隨時接得通的電話放在這裡：
> 安心專線 1925（24 小時、免付費）
> 生命線 1995（24 小時）
> 如果現在有立即的危險，請撥 119 或 110。
> 不用一個人撐。

**自動訊息只是第一步，不取代人工。** 工作流摘要出現「⚠️ 自傷訊號 N 則」時，CEO 要照 `legal.md` 2-7：到 IG 收件匣／貼文看原留言、判斷級別、公開回範本 A、立即危險就檢舉「自殺或自傷」並視情況撥 110／119。紀錄檔只標 `self_harm: true`，不存原文（repo 是 public）。

## 三、Andy 要做的事：產生權杖時要勾的權限

這組權杖跟頻道④自動發文共用（`HEALING_IG_ACCESS_TOKEN`），**同一把要多勾兩個權限**：

| 權限 | 用途 | 發文需要？ | 私訊需要？ |
|---|---|---|---|
| `instagram_business_basic` | 讀帳號、貼文 | 要 | 要 |
| `instagram_business_content_publish` | 發文 | 要 | 不用 |
| `instagram_business_manage_comments` | 讀留言、拿到留言者 | 不用 | **要** |
| `instagram_business_manage_messages` | 私訊、查追蹤狀態 | 不用 | **要** |

步驟（畫面文字以當下 Meta 後台為準，不確定先貼截圖）：

| 步驟 | 連結 | 點哪裡 | 填／選什麼 |
|---|---|---|---|
| 1 | https://developers.facebook.com/apps | 點進頻道④用的 App → 左側「Instagram」→「API setup with Instagram login」（用 Instagram 登入設定 API） | 不用動既有設定 |
| 2 | 同一頁「Generate access tokens」（產生存取權杖） | 談晴說礙帳號那一列按「Generate token」（產生權杖） | 登入談晴說礙 IG；授權畫面**四個權限都要打勾**（上表） |
| 3 | https://github.com/MiaoZiKe/tw-rotation/settings/secrets/actions | 找到 `HEALING_IG_ACCESS_TOKEN` → 按鉛筆「Update」（更新） | 貼上新權杖 → 按「Update secret」（更新密鑰）。名稱不用動 |
| 4 | https://github.com/MiaoZiKe/tw-rotation/actions/workflows/healing_comments.yml | 右邊「Run workflow」（執行工作流）→ `dry_run` 保持打勾 → 按綠色「Run workflow」 | 這是空跑，只讀留言、不私訊 |
| 5 | 同上，點剛跑完那一輪 | 看「Summary」（摘要）表格 | 回我摘要截圖 |

做完回我：「權杖已更新、空跑摘要截圖」。這件事**不擋**頻道④自動發文（發文只要前兩個權限）。

⚠ App 在「開發模式」時，Meta 對私訊類權限可能只讓 App 角色成員（管理員、開發者、測試人員）收得到；一般粉絲收不收得到要實測（見第六節）。

## 四、怎麼關閉

| 想做的事 | 做法 |
|---|---|
| 全部停（不讀留言、不私訊） | `dm_config.json` 的 `enabled` 改成 `false`，推 main |
| 暫停排程 | https://github.com/MiaoZiKe/tw-rotation/actions/workflows/healing_comments.yml → 右上「…」→「Disable workflow」（停用工作流） |
| 查不到追蹤的也要私訊 | `unknown_follow` 改成 `"send"` |
| 改文案 | 改 `message` |

## 五、出錯怎麼看

| 看到什麼 | 意思 | 處理 |
|---|---|---|
| 摘要「等待權杖」、綠燈 | 還沒設 `HEALING_IG_ACCESS_TOKEN` | 照第三節設定 |
| 摘要「權杖無效或權限不足」、紅燈 | 權杖過期或沒勾 `instagram_business_basic` | 重新產生權杖 |
| 錯誤「讀留言失敗」 | 沒勾 `instagram_business_manage_comments` | 重新產生權杖並勾選 |
| 大量「追蹤無法確認，未私訊」 | 查追蹤被拒（多半是對方沒傳過訊息給帳號、不算授權） | 見第六節第 1 條；要不要改 `unknown_follow=send` 由 Andy 決定 |
| 錯誤「私訊失敗」 | 沒勾 `instagram_business_manage_messages`、開發模式限制、或超過 7 天 | 看錯誤代碼；3 輪後停止重試 |
| 「已達每輪上限」 | 一次湧入很多留言 | 正常，下一輪會接著送 |
| ⚠️ 自傷訊號 | 有留言命中自傷關鍵字，已送關懷訊息 | CEO 依 `legal.md` 2-7 人工處理 |

紀錄檔 `state/comments_dm.json`：`seen`（雜湊 → 時間、結果、follow、self_harm）、`weekly`（每週各結果則數，週報用，包含「無法確認追蹤」的數量）、`last_change`。只留 30 天。

## 六、要等權杖才能實測的事（未確認）

1. **查追蹤（`is_user_follow_business`）在「Instagram 登入版」權杖能不能用在留言者身上**：官方 User Profile API 寫明要 `instagram_business_basic`＋`instagram_business_manage_messages`，而且「需要使用者同意」—— Messenger 版文件寫「對方只留言、沒傳過訊息給商家，會回錯誤」。如果實測也是這樣，**大部分留言者會變成「無法確認」→ 預設不私訊**。到時把週報的數量給 Andy，請他決定要不要改成 `unknown_follow=send`（等於不檢查追蹤）。
2. **開發模式下非 App 角色的人收不收得到私訊**：用一個不是 App 角色的帳號留言測一次。收不到就要把 App 切成「上線（Live）」模式，必要時送 Advanced Access 審核。
3. 私訊單則字數上限、Private Reply 的確切錯誤代碼（程式把含「already」或 2534 的錯誤視為「已私回過」）。
4. `from{id,username}` 欄位在 Instagram 登入版的實際回應格式（程式也讀頂層 `username` 當備援）。

來源（WebSearch 摘要，容器打不開原文，實作前請在後台核對）：
- https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/messaging-api/user-profile
- https://developers.facebook.com/docs/messenger-platform/instagram/features/user-profile
- https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-comment
- https://developers.facebook.com/docs/instagram-platform/private-replies/

## 七、Threads

Threads API 沒有私訊功能（見 `comment_dm_plan.md` 第三節），本次不做。之後若要，可做「讀回覆 → 公開回覆一句」，但回覆是公開的。

## 八、已知風險

- 自傷關鍵字是字串比對，會漏（隱晦說法）也會誤判；排除詞清單可在設定檔增補。自動訊息不取代人工處理。
- 頻道④發文工作流寫回 state 時若整個資料夾覆蓋，可能把本檔的紀錄蓋回舊版；即使如此，Meta 規定每則留言只能私回 1 次，不會重複送到同一人（會被記成「已私回過」）。
- 權杖 60 天到期，續期由頻道④發文那邊的續期流程負責（`HEALING_IG_ACCESS_TOKEN_AUTO` 優先使用）。

## 修改紀錄

| 日期（台北） | 內容 |
|---|---|
| 2026-11-08 | 建立：輪詢讀主留言、查追蹤、Private Replies、自傷關懷訊息、空跑與上限 |
