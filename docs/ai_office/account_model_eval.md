# AI Office 帳號串接可行性、成本與方案額度評估

> 撰寫：marketing-strategist｜日期：2026-11-13｜查證日期一律 2026-11-13
> 性質：評估文件，只寫文件，沒有改任何產品程式碼、沒有 commit、沒有 push。
> 標示規則：**【事實】**有來源可追；**【判斷】**是我的推論；信心度分 高／中／低／未確認。
> ⚠ 查證限制：這個容器只有 WebSearch 能用，拿到的只是摘要，**我沒有讀過任何一篇官方全文**。
> 凡是「官方頁」的字句，都是摘要轉述；摘要會自己補出原文沒有的東西（本專案踩過兩次），所以關鍵結論我盡量用兩個以上獨立來源，湊不到的就標中或低。

---

## 〇、先看這 12 行

1. **「用 Claude 帳號登入」做不到，而且就算技術上有路，也違反 Anthropic 條款。** 查到的證據全部指向同一個方向：Anthropic 沒有對外開放「用 Claude 登入」給一般網站，並且明文禁止把 Free／Pro／Max 的 OAuth 權杖用在別的產品。（信心：中高）
2. **第三方網站讀不到使用者在 claude.ai 的專案清單，也收不到「新建立了一個專案」的通知。** 唯一查到的官方「列專案」介面是 Compliance API，它是企業組織層級、用合規金鑰，不是使用者授權給第三方的。（信心：中高）
3. **Claude Code 網頁版（雲端工作階段）也查不到公開的「列出工作階段」介面。**（信心：中）
4. 所以擁有者要的三種情況，**情況 1「有專案但沒內容 → 辦公室尚未成立」無法照字面做到**（我們看不到「從沒回報過的專案」）；情況 2、3 可以改成「**專案第一次有回報時才出現**」來近似。
5. **最接近的做法（我建議）**：網站用 Google 登入（同一個 Gmail）＋ 使用者做**一次性**的帳號層級接入（本機：裝一個外掛；雲端：在預設環境填一次網路白名單、金鑰與設定腳本），之後所有專案的事件自動上報、專案清單由「回報過的專案」累積。擁有者說的「自動建立辦公室」開關也做得到，觸發點是「新專案第一次回報」。
6. **這個做法有 4 個關鍵點必須實測才算數**（見第一部分 1.5）：外掛層級的子 Agent 掛鉤有沒有觸發、雲端環境的設定腳本寫的掛鉤有沒有生效、雲端網路白名單與金鑰能不能連到我們的網址、掛鉤收到的欄位夠不夠。**建議先花約 1～2 天實測再決定要不要往下投入。**
7. **多一間辦公室的成本確實不大，但原因要講對**：場景與角色模型是共用的靜態檔，不隨辦公室增加；真正會花錢的是「即時更新的請求數」，不是「辦公室數」。
8. **我的估算**：每位活躍使用者每月約 4,000～9,300 次請求（取決於輪詢間隔）；免費方案大約撐 150～550 位「每日活躍」使用者；1,000 人約 US$5.5～6.5／月，1 萬人約 US$20～45／月（輪詢 15 秒 vs 5 秒）。最耗錢的是**輪詢**。（以上是我的假設推算，信心：中低）
9. **不是擁有者付的錢**：使用者自己的 Claude 訂閱與 Token。掛鉤不消耗 Token。
10. **名稱與宣傳**：產品名不要有 Claude／Anthropic，不要宣稱官方整合或 Claude 登入，只能用純文字寫「相容 Claude Code」並加不隸屬聲明。（信心：中）
11. **額度建議**：免費 1 間辦公室 × 3 位 Agent（CEO 另計）＋新會員 14 天體驗 Plus 上限；Plus 3 間 × 5 位；擁有者信箱不限。「兼任」設計成**斜槓員工＋換帽子**，不是砍功能。
12. **價格建議**：Plus 每月 NT$99～199，先只做免費＋Plus 兩層；Pro 預留。依據與風險見第三部分。

---

## 第一部分：技術可行性

### 1.1 逐項回答

| # | 問題 | 結論 | 依據（事實） | 信心 |
|---|---|---|---|---|
| 1 | 第三方網站能不能提供「用 Claude 帳號登入」？ | **不可行**（沒有對外開放，且有禁令） | WebSearch 搜「Sign in with Claude」找不到任何官方計畫；多篇報導與 Anthropic 說明指出：第三方工具應用 API 金鑰；Anthropic 已撤銷第三方用 claude.ai 訂閱 OAuth 的能力，2026-02-19 文件更新明文釐清，執行據稱 2026-01-09 起。Claude Code 法遵頁（摘要引述）：「使用 Free、Pro、Max 帳號取得的 OAuth 權杖於任何其他產品、工具或服務，包括 Agent SDK，均不被允許。」另有一個專案自述「Anthropic 沒有提供註冊第三方 client ID 的方式」。Anthropic 的連接器 OAuth 是反方向（Claude 連到**你的**伺服器），不是給你的網站做使用者登入。 | 中高（官方頁只有摘要，沒讀全文；「沒有註冊管道」是單一專案自述） |
| 2a | 能讀到使用者的 claude.ai「Projects」清單嗎？ | **不可行** | 唯一查到的官方列專案介面是 Compliance API：`GET /v1/compliance/apps/projects`，需啟用 Compliance API、用合規金鑰，可依組織／使用者 ID 篩選。這是企業合規用，不是個人使用者授權第三方讀取。沒找到個人帳號可用一般 API 金鑰列專案的介面（這是「沒找到」的推論，非明文否定）。 | 中高 |
| 2b | 能列出 Claude Code 網頁版的工作階段／對應 GitHub 儲存庫嗎？ | **不可行（無公開介面）** | 搜尋沒找到官方公開的列出介面；官方文件只說可用 CLI 的 `/tasks` 監控。有一個 GitHub issue 顯示 VS Code 擴充套件內部有「列遠端工作階段」呼叫（會 404），代表**內部介面存在但未公開**；要用它就得拿使用者的訂閱 OAuth 權杖，正是第 1 項被禁的事。`/v1/sessions`（Managed Agents API）是另一個產品，與 Claude Code 網頁版無關。 | 中 |
| 2c | Claude Console／API 工作區？ | **不適用** | 屬於組織管理員用的管理介面（金鑰、用量），使用者不會把它授權給第三方網站；也不等於「專案」。我沒有查到面向第三方的授權流程。 | 中低（查得淺） |
| 2d | 有官方方式得知「新建立了一個專案」嗎？ | **不可行** | 以上三類都沒有查到事件通知（webhook）介面。 | 中 |
| 2e | 「Gmail 對應 Claude 帳戶」能驗證嗎？ | **不能** | Claude 不會告訴我們登入者是誰；Google 登入的 Gmail 與 Claude 帳號的 email 可能不同。只能是使用者自己宣稱，由「他的接入權杖有送來事件」當作關聯證據。 | 【判斷】高 |

【判斷】擁有者說的「專案」可能指兩種東西：claude.ai 聊天的 Projects，或他日常在用的 Claude Code 工作目錄／GitHub 儲存庫。他的 CLAUDE.md 顯示他實際在用 Claude Code 雲端工作階段與儲存庫，所以我下面把「專案」定義成「**Claude Code 的工作目錄（git 儲存庫名稱）**」。這點列入決定事項 2。

### 1.2 替代做法評估

**共通前提（已查到的事實）**
- Claude Code 的掛鉤（hooks）有 SubagentStart、SubagentStop、SessionStart 事件，且支援 `type: "http"` 的處理器：直接 POST 到一個網址，可帶自訂標頭與環境變數。（官方 hooks 頁摘要＋多個第三方指南，信心：中高；「HTTP 掛鉤自 v2.1.63」是單一第三方，信心低）
- 外掛（plugin）可帶 `hooks/hooks.json`，使用者範圍（user scope）安裝後對該台機器上所有專案生效；外掛啟用旗標存在 `~/.claude/settings.json` 的 `enabledPlugins`，掛鉤本體在外掛內。（官方安裝頁摘要＋第三方，信心：中高）
- 有一個未證實的 issue：從 marketplace 安裝的外掛，SubagentStart 掛鉤可能不觸發。（單一使用者回報，信心：低，**必須實測**）
- 專案層級 `.claude/settings.json` 的 `extraKnownMarketplaces` 只在使用者信任該資料夾時生效。（官方頁摘要，信心：中）→ 這正是前一版「每個專案都要放設定」會麻煩的根源。
- 雲端工作階段：每個工作階段跑在一個「雲端環境」裡，環境保存網路存取等級、環境變數、設定腳本；設定腳本在 Claude Code 啟動前以 root 執行、結果會快取；環境也能存「網路金鑰」，由代理在請求送出時注入標頭，工作階段本身看不到值。（官方 cloud-environments／quickstart 摘要＋本 session 的環境文件，信心：中）。預設網路是受限白名單，要連我們的網址需加入。
- 使用者自訂連接器（custom connector）：Pro／Max／Team／Enterprise 可自行用遠端 MCP 伺服器網址新增，**免費帳號限 1 個**；連線是從 Anthropic 雲端發出，伺服器必須公開可達；OAuth 回呼為 `https://claude.ai/api/mcp/auth_callback`。（官方 support 頁摘要，信心：中高）

#### 方案 a：Google 登入 ＋ 一次性帳號層級接入（【判斷】建議）

| 項目 | 內容 |
|---|---|
| 使用者步驟 | **本機**：①網站按「用 Google 登入」→ ②網站顯示專屬接入碼與兩行指令（加入 marketplace、安裝外掛）→ ③在終端機貼上，外掛第一次啟動時用接入碼綁定（寫入使用者目錄，不進專案、不進 repo）。共約 3 步、約 2 分鐘。**雲端**：④在 Claude Code 網頁的預設環境填：網路白名單加 1 個網址、網路金鑰 1 筆、設定腳本貼 1 段（腳本負責裝外掛或寫使用者層級掛鉤）。約 3 個表單。**全部只做一次，新專案不用再設。** |
| 情況 1（有專案、沒內容 → 尚未成立） | **照字面做不到**：從沒回報過的專案我們看不到。替代呈現：網站空狀態寫「尚未收到任何專案的回報，完成接入後在 Claude 開一個工作階段就會出現」。 |
| 情況 2（有專案、有內容 → 點選創立） | **做得到（近似）**：專案第一次回報後出現在「發現的專案」清單，旁邊有「創立辦公室」鈕。 |
| 情況 3（登入後在 Claude 新建專案 → 自動建立） | **做得到（近似）**：新專案「第一次回報」時，若勾選「自動建立專案辦公室」，伺服器就自動建一間（受上限管控）。不是「建立專案的瞬間」，而是「第一次跑工作階段」。 |
| 限制／風險 | 不能看到從沒跑過的專案；雲端環境如果使用者有多個，要各設一次；金鑰若存成環境變數是明文儲存（官方環境機制），建議用「網路金鑰」；掛鉤必須逾時 2 秒放棄且不阻塞工作；隱私上只送專案名雜湊／顯示名、事件類型、時間、Token 數，不送提示詞與程式碼。 |
| 販售給一般使用者的難度 | **中**。本機 3 步可以做成一鍵複製；雲端 3 個表單對非技術使用者偏難，但目標客群（開 Claude Code 子 Agent 的開發者）能做。 |
| 沿用現有 | 主站已有 Google 登入與會員 Worker（`docs/login_setup.md`，只要 openid／email／profile，不需送審；方案範本與訂閱已有 `plan_presets`、`quota_plan`、`pay.js`＋綠界）。AI Office 是獨立專案與子網域，建議**複用同一個 Google 用戶端（加一個重新導向網址）與同一套寫法**，不要共用資料庫。 |

#### 方案 b：GitHub 登入，列儲存庫當專案清單

| 項目 | 內容 |
|---|---|
| 使用者步驟 | 1 步（登入並授權）。 |
| 情況 1／2／3 | 情況 1：能列出沒用過的儲存庫，但**不等於 Claude 專案**，會把所有儲存庫都列出來。情況 2：可做。情況 3：新儲存庫出現可偵測（需輪詢或 GitHub 應用程式 webhook），但**「新儲存庫」≠「新 Claude 專案」**。 |
| 限制 | 只解決「專案清單」，**事件上報（誰被派出、做多久、Token）仍需要掛鉤**，所以不能取代 a；私有儲存庫要較大權限（授權畫面較嚇人）；只用本機 Claude Code 沒有 GitHub 的人覆蓋不到。（GitHub 授權範圍與 API 屬一般已知能力，我沒有另外搜尋，信心：中） |
| 難度 | 低到中。 |
| 【判斷】 | 可當 a 的**選配加分**（讓專案清單先有名字、能一鍵建好辦公室），不建議當主路徑。 |

#### 方案 c：自建 MCP 連接器，讓 Claude 主動呼叫

| 項目 | 內容 |
|---|---|
| 使用者步驟 | 在 claude.ai 設定新增自訂連接器（填名稱與網址）→ 走我們的 OAuth（可用 Google 登入）授權。約 3～4 步。免費帳號最多 1 個連接器。 |
| 情況 1／2／3 | **都做不到「被動偵測」**：MCP 是模型決定要不要呼叫工具，不是平台推送事件；要它回報就得在提示詞或 CLAUDE.md 要求「每次派子 Agent 都呼叫 report 工具」。 |
| 限制 | ①不確定性高：模型可能漏報，無法保證；②**每次呼叫都消耗使用者的 Token**，違背「不花使用者額度」的賣點；③不確定雲端工作階段與本機 CLI 是否都載入 claude.ai 連接器（本 session 有一些連接器可見，但不能據此推論所有人都行，未確認）。 |
| 難度 | 中高。 |
| 【判斷】 | 不當事件來源。**但很適合做反方向**：把「網頁上對 CEO 下指令」做成 MCP 工具讓 CEO 領取（plan.md 第七節擁有者要求「只用免費方法」，這是候選之一，需另行評估）。 |

### 1.3 三方案對照

| | a 外掛＋雲端環境 | b GitHub 登入 | c MCP 連接器 |
|---|---|---|---|
| 使用者設定 | 一次（本機 3 步＋雲端 3 表單） | 1 步 | 3～4 步 |
| 事件自動上報 | 是（掛鉤，不吃 Token） | 否 | 否（吃 Token、會漏） |
| 專案清單 | 回報過的專案 | 所有儲存庫（含沒用 Claude 的） | 無 |
| 新專案自動建辦公室 | 第一次回報時 | 偵測新儲存庫 | 否 |
| 實測風險 | 中（見 1.5） | 低 | 高 |
| 條款風險 | 低（不碰 Claude 帳號權杖） | 低 | 低 |

### 1.4 建議方案

【判斷】**採 a 為主、b 為選配、c 暫不做（只留給「網頁下指令」另案評估）。**

理由：只有 a 同時滿足「登入一次、不必每個專案各自設定、事件自動來、不花使用者 Token、不違反條款」。代價是接受**專案清單來自回報**這個事實，並把情況 1／3 的畫面與文案如實改寫，**不要在行銷上寫「自動偵測你在 Claude 的所有專案」**。

建議的使用者流程：
1. 開網站 → Google 登入（同一個 Gmail）。
2. 「接入」頁：複製兩行指令（本機）／照三格填寫（雲端）。
3. 在 Claude 開工作階段 → 網站出現「發現新專案：xxx」→ 點「創立辦公室」，或已勾「自動建立專案辦公室」就直接建好。
4. 超過額度的專案進「待開通」區，不丟資料、不擋事件收取。

### 1.5 仍需實測才能確定的事（建議先做，約 1～2 天）

| # | 實測項目 | 為什麼不確定 |
|---|---|---|
| T1 | 外掛（使用者範圍）安裝後，SubagentStart／SubagentStop／SessionStart 掛鉤是否真的觸發 | 有 issue 回報 SubagentStart 在外掛範圍不觸發（低信心） |
| T2 | 雲端工作階段：設定腳本寫入使用者層級設定或安裝外掛，是否被採用、是否每個新工作階段都有 | 我只查到設定腳本會快取、先於啟動執行；沒查到它能否安裝外掛的官方說法 |
| T3 | 雲端網路白名單＋網路金鑰：掛鉤對我們網址的 POST 能否連通、標頭是否被注入 | 預設白名單受限；plan.md 已列此為「開工第一天先測」 |
| T4 | 掛鉤收到的欄位：專案識別（工作目錄／儲存庫）、子 Agent 類型、起訖時間、Token 數是否都拿得到 | 我沒讀過官方欄位定義；plan.md 也寫「目前沒有逐件起訖時間與 Token 紀錄」 |
| T5 | 使用者有多個雲端環境時的負擔 | 沒查到環境數量與預設環境的行為細節 |

---

## 第二部分：成本（擁有者要付的錢）

### 2.1 「多一間辦公室只是複製模板、消耗不大對吧？」

【判斷】**對，但成本的來源不是「模板」。**

| 面向 | 隨辦公室數增加嗎？ | 說明 |
|---|---|---|
| 靜態檔（場景、角色模型、貼圖、程式） | **不增加** | 全體使用者共用同一份，靠 CDN 快取。目前 `site/office/` 約 4.0 MB（本機 `du` 實測）。Cloudflare Pages 官方文件摘要未寫流量上限（見 `docs/hosting_cost_plan.md`）；GitHub Pages 禁商業用途、有 100 GB／月軟性上限，所以販售版要放 Cloudflare Pages（既有文件結論）。 |
| 每間辦公室的資料 | 線性增加但極小 | 設定（佈局、5 位角色、配件）約數 KB；事件每筆約 200 B（我的假設）。每人每月約 1,300 筆 ≈ 0.26 MB。 |
| 即時更新請求 | **這才是成本** | 每個正在看畫面的辦公室，每隔 N 秒打一次請求；與「辦公室總數」關係小，與「同時有多少人盯著看」「輪詢多快」關係大。沒人在看的辦公室成本接近 0。 |

### 2.2 用量假設與估算

**假設（全部是我的假設，沒有實測；上線後要用 Cloudflare 後台實際數字重算）**

| 項目 | 假設值 |
|---|---|
| 每位活躍使用者每月活躍天數 | 22 天 |
| 每天工作階段數 | 3 個 |
| 每個工作階段事件 | 約 20 筆（起訖＋子 Agent 起訖＋Token 回報） → 每天約 60 筆寫入 |
| 每天開辦公室頁 | 3 次，每次前景 10 分鐘 |
| 輪詢間隔 | 情境 A：5 秒；情境 B：15 秒（建議） |
| 每次輪詢讀取列數 | 約 50 列 |

**每人每月請求數**
- 寫入：60 × 22 = 1,320
- 輪詢 A（5 秒）：每次 10 分鐘 = 120 次 → 3 × 120 × 22 = 7,920；加寫入與頁面載入約 **9,300**
- 輪詢 B（15 秒）：2,640；加寫入與頁面載入約 **4,000**
- 儲存：約 0.26 MB／月；若保留 90 天約 0.8 MB／人

**現行公開價格（查詢日 2026-11-13，皆為 WebSearch 摘要；官方完整表格沒取得）**

| 項目 | 免費方案 | 付費方案 | 來源／信心 |
|---|---|---|---|
| Workers | 每天 10 萬次請求 | 最低 US$5／月；內含請求量我只在第三方看到「1,000 萬／月」，超過每百萬 US$0.30（`docs/hosting_cost_plan.md` 已有同樣數字） | [Workers 定價](https://developers.cloudflare.com/workers/platform/pricing/)；「$5 最低」中高、「1,000 萬」低 |
| Durable Objects | 免費方案只能用 SQLite 型；請求／時數額度第三方互相矛盾（每天 10 萬 vs 每月 300 萬） | 內含 100 萬請求，超過每百萬 US$0.15；400,000 GB-s 之後每百萬 GB-s US$12.5；WebSocket 進站訊息 20:1 計費，出站與 ping 不計 | [DO 定價](https://developers.cloudflare.com/durable-objects/platform/pricing)；付費部分中，**免費額度未確認** |
| D1 | 每天讀 500 萬列、寫 10 萬列、儲存 5 GB | 內含每月讀 250 億列、寫 5,000 萬列、5 GB；超過寫入每百萬 US$1、儲存每 GB US$0.75 | 第三方彙整與官方文件摘要一致，中 |
| KV | 每天讀 10 萬、**寫 1,000** | 每月讀 1,000 萬、寫 100 萬 | 中。**事件不能放 KV**（免費寫入太少） |
| Pages 靜態 | 官方未寫流量上限 | — | 既有文件，中 |

**支撐人數與費用（【判斷】推算）**

| 規模（每月活躍） | 情境 B（15 秒）每月請求 | 情境 A（5 秒）每月請求 | 約每月費用（B） | 約每月費用（A） |
|---|---|---|---|---|
| 免費方案可撐 | 每日約 180 次／人 → 約 **550 位每日活躍** | 每日約 420 次／人 → 約 **240 位** | US$0 | US$0 |
| 1,000 人 | 約 400 萬 | 約 930 萬 | 約 US$5.5 | 約 US$6.5 |
| 1 萬人 | 約 4,000 萬 | 約 **9,300 萬** | 約 US$20 | 約 US$45 |

計算方式（供檢查）：1 萬人情境 B：Workers 4,000 萬 − 內含 1,000 萬 = 3,000 萬 × 0.30／百萬 ≈ US$9；若每次輪詢都經過 DO，DO 請求 4,000 萬 − 100 萬 = 3,900 萬 × 0.15／百萬 ≈ US$5.9；加基本 US$5 → 約 US$20。情境 A 同理約 US$45。D1 列數遠低於內含額度（寫入 1 萬人 × 1,320 × 約 3 列 ≈ 4,000 萬列 < 5,000 萬）；儲存 1 萬人 × 0.8 MB ≈ 8 GB，超過 5 GB 約多 US$2。

**最耗錢的一項：輪詢。** 降低方式（【判斷】由效果大到小）：
1. 分頁不在前景就停止輪詢（瀏覽器可見性事件）；估省 50% 以上。
2. 拉長間隔：預設 15 秒；一段時間沒有新事件退到 30～60 秒。
3. 輪詢只打 Worker 讀 D1，**不經過 Durable Object**（省掉 DO 請求費）；用 ETag／304，沒變化就回很小的回應。
4. 同一間辦公室多人同看時，Worker 邊緣快取 5 秒共用。
5. 日後要即時再改推送（WebSocket）：進站訊息 20:1 計費、出站免費，但「連線持續時間費」是最大未知（既有 launch_plan 也寫需實測）。
6. 事件批次送（掛鉤本機先收、每 10～30 秒送一批），減少寫入請求。

**單位成本**：情境 B 每位使用者每月約 4,000 次請求 ≈ US$0.001～0.003（超過內含後的邊際費率），遠低於一杯咖啡。【判斷】**免費使用者的成本不是額度設計的限制條件**，額度要依「產品價值與轉換」決定，不是依成本。

### 2.3 不是擁有者付的費用

| 項目 | 誰付 |
|---|---|
| Claude 訂閱（Pro／Max／Team） | 使用者 |
| 子 Agent 消耗的 Token、5 小時與每週額度 | 使用者（雲端工作階段與其他 Claude Code 用量共用額度，來源：Anthropic 部落格摘要，中） |
| 使用者的電腦／雲端環境 | 使用者 |
| 掛鉤本身 | 不消耗 Token（是 HTTP 呼叫，不是模型輸出）【判斷，高】 |

⚠ 擁有者要注意：**如果日後由伺服器呼叫 Claude API 產生「會議對白」或摘要，那就變成擁有者付 API 費**。目前 plan.md 的做法是由 CEO 順手產生（不另付）或規則自動排，請維持，不要在伺服器端偷加模型呼叫。

### 2.4 其他成本與風險

| 項目 | 事實 | 判斷／建議 | 信心 |
|---|---|---|---|
| Google 登入 | 只要 openid／email／profile，Google 視為登入用基本範圍；開發／測試階段不需驗證，想讓任何 Google 帳號用則要發布，名稱與標誌要顯示在同意畫面需品牌驗證（摘要引述 Google 官方頁）。主站已有同樣設定。 | 沿用主站的 Google 用戶端或新建一個；準備好隱私權政策與服務條款網址（品牌驗證需要）。 | 中 |
| 金流手續費 | 主站已有綠界（ECPay）串接與定期定額（`workers/account-api/pay.js`）。**綠界／藍新現行費率這次沒查到**（搜尋只回銀行卡友資料）。既有 launch_plan 引用「約 2.4～3%」為低信心。 | 未確認，不能當成已知；開價前向綠界確認費率與是否有固定手續費（會影響最低可行價）。 | 未確認 |
| 收款身分 | 既有文件：藍新個人開發者需統編（中低）；擁有者已申請綠界。 | 沿用主站已申請的綠界，但 AI Office 的銷售標的不同，需確認商店類別與發票處理（未查）。 | 低 |
| 客服 | 一人營運。 | 常見問題頁＋接入自檢頁（顯示「最後一次收到事件時間」「哪一步失敗」）可擋掉大部分「連不上」；雲端環境設定是最大客服來源。 | 【判斷】中 |
| 濫用／洗免費額度 | 免費額度是「每個 Google 帳號 1 間辦公室」，會有人開多個 Gmail。 | ①額度綁 Google `sub` 並正規化 Gmail 的點與加號；②辦公室要「收到第一筆事件」才算占用名額；③每把接入碼限速（例如每分鐘 120 筆）與單筆大小上限；④免費辦公室 30 天沒事件就封存；⑤註冊頁加 Cloudflare Turnstile（我印象它免費，未另查，信心低）。 | 【判斷】中 |
| 個資／內容 | 事件可能含專案名、任務標題。 | 預設只送專案顯示名、Agent 類型、時間、Token 數；**不送提示詞、不送程式碼**；提供刪除帳號與資料；服務條款寫清楚。 | 【判斷】高 |
| Anthropic 商標與條款 | ①Claude Code 法遵頁（摘要）：可用純文字陳述「產品執行／相容 Claude Code」；不得把 Claude Code 或 Anthropic 名稱／標誌放進產品、功能或公司名稱，或暗示 Anthropic 開發或背書。②商標指南存在且要求遵守最新版（我沒讀到全文）。③有案例：Clawdbot 因名稱聽起來像 Claude 被要求改名 Moltbot（商標事務所部落格，二手，低）。④Agent SDK 品牌用語「{你的產品名} Powered by Claude」是否適用，來源是 GitHub issue 轉述，低。 | **保守建議**：名稱與網域不含 Claude／Anthropic／Clawd 這類近音字；不使用 Claude 的橘色星芒標誌與官方吉祥物；頁尾寫「本產品為獨立第三方，與 Anthropic 無隸屬或背書關係」；文案只用「相容 Claude Code 的掛鉤」；**不寫「用 Claude 登入」「Claude 官方整合」**；上架前讓 legal-compliance 讀全文與商標指南。 | 中（全文未讀） |

---

## 第三部分：方案與額度

### 3.1 擁有者定的上限（3 間辦公室 × 5 位 Agent，超過就兼任）合理嗎？

【判斷】**合理，且從成本看很寬鬆。**
- 成本面：5 位 Agent 的資料量極小，不是限制條件（2.2）。
- 產品面：Claude Code 使用者常有 10 種以上的子 Agent 類型（本專案自己就有 45 位）。5 個座位偏緊，**如果呈現不好，會被讀成「閹割」**。所以關鍵不在數字，在「兼任」做成賣點。
- 與既有 launch_plan 的差異：launch_plan 寫免費總共 3 位 Agent、1 個專案；擁有者這次的「3 間 × 5 位」更大方，我把它當作**付費方案的上限**，免費版另外設定（見 3.3）。這點列入決定事項 3。

### 3.2 「兼任多個身份」怎麼呈現才不像被閹割

| 設計 | 做法 | 好處 |
|---|---|---|
| 斜槓員工 | 把 5 個座位稱為「正職員工」，其他子 Agent 類型稱為「帽子」（職稱）。名牌顯示主職稱＋「+2」小標。 | 不是「少一個人」，而是「這個人身兼多職」，符合辦公室隱喻 |
| 換帽子動畫 | 子 Agent 觸發時，角色戴上對應帽子／配件，頭上冒出職稱氣泡，結束再換回 | 每次兼任都是一個看得見的小演出，反而更有戲 |
| 分身提示 | 同時有兩個帽子在跑：角色身旁出現半透明小分身，名牌顯示「同時 ×2」 | 如實反映併行，不假裝一個人做一件事 |
| 自動分座 | 預設依「使用量最高的 5 種」分配正職，其餘按部門歸給對應正職；使用者可拖曳改 | 開箱即用，不用先設定 |
| 績效分開記 | 績效卡可切換「本人總表」與「各帽子明細」 | 兼任不會讓績效變糊，也是付費報表的賣點 |
| 升級誘因 | 超過座位時顯示「這個職稱目前由小明兼任（座位已滿，可讓現有同事兼任）」 | 把痛點變成可選擇的升級，不是封鎖 |

⚠ 如實性：兼任是**顯示層的歸併**，績效與稽核的原始事件仍依真實子 Agent 類型記錄，不可為了演出而改寫數字（與 plan.md 的「結論、數字、誰負責什麼一律照實」一致）。

### 3.3 方案層級與功能分層

分層原則（沿用本專案定價原則）：免費要足以養成習慣；付費對應「每天真的會用」的動作，用「省多少時間／承擔多少風險」分；不付費的人用較慢的方法也做得到。

| 功能 | 免費（Free） | Plus（建議主力） | Pro（預留，第一版不上） | 不付費的人怎麼辦 |
|---|---|---|---|---|
| 辦公室數 | 1 | 3 | 擁有者需另外同意（超過 3） | 第 2 個專案進「待開通」，事件照收，可輪流換上場（每 30 天一次） |
| 正職座位 | 3 位（CEO 另計） | 5 位 | 同 Plus 或更多（需同意） | 其餘用兼任顯示 |
| 新會員體驗 | 註冊後 14 天享有 Plus 上限（天數與額度由擁有者設，我只建議） | — | — | 體驗結束超出部分轉「休眠」唯讀 30 天，不刪資料 |
| 自動建立辦公室 | 手動點「創立辦公室」 | 勾選後自動 | 同 | 手動多點一下就好 |
| 績效 | 只看本週等第 | 完整總表（含各部門與 CEO）、各帽子明細 | 週報信、匯出 | 免費版每週一人工看當週等第 |
| 配件與設備升級 | 基本款獎勵（有成就感的迴圈要留給免費） | 全部款式、設備升級路線、更多裝飾格 | 搶先款 | 基本款也能體現「誰表現好」 |
| 寵物與十二生肖 | 1 隻預設寵物 | 全部寵物與生肖造型 | 同 | 預設寵物 |
| 歷史紀錄 | 7 天 | 90 天 | 1 年＋匯出 | 自己截圖／手動記錄 |
| 開除與重聘 | 可開除；重聘為新員工 | 重聘保留配件與紀錄 | 同 | 新員工重新累積 |
| 事件上報與基本功能（看誰在做什麼、Token） | **全部免費** | 同 | 同 | — |

【判斷】**不要把「看得到子 Agent 在做什麼」放進付費**。那是產品存在的理由，也是競品（免費開源的 2D 像素版）的主戰場；鎖了免費版會變殘廢試用品。付費賣的是：**更長的歷史、更完整的績效報表、更多外觀與自動化**。

### 3.4 價格區間與參照

**參照（均為 WebSearch 摘要，各站價格需到官方頁再確認）**

| 產品 | 類型 | 價格 | 來源 | 信心 |
|---|---|---|---|---|
| Gather | 虛擬辦公室 | 每人每月 US$15（月繳）／US$12（年繳），免費方案是否仍在說法不一 | [Gather 官方說明](https://support.gather.town/hc/en-us/articles/39590892978196) | 中高 |
| Langfuse | LLM 觀測 | Hobby 免費；Core US$29；Pro US$199（無按席位） | [彙整頁](https://costbench.com/compare/langfuse-vs-langsmith/) | 中低（第三方） |
| LangSmith | LLM 觀測 | Developer 免費（1 席）；Plus US$39／席 | 同上 | 中低 |
| Helicone | LLM 閘道／觀測 | 免費 1 萬請求／月；Pro 多數來源 US$79，另有 US$100、US$20／席說法 | [truefoundry](https://www.truefoundry.com/blog/helicone-pricing) 等 | 低（互相矛盾） |
| AgentOps | 代理人觀測 | 免費約 5,000 事件／月；Pro 約 US$40 | [aitoolsatlas](https://aitoolsatlas.ai/tools/agentops/pricing) | 低（單一彙整站，2026-03） |
| 開源 2D 像素版（Pixel Agent Desk、Claude Office Visualizer 等） | Claude Code 可視化 | 免費 | launch_plan 引用 | 中（僅摘要） |
| 本專案主站 Plus／Pro | 自家股票儀表板 | NT$249／499 每月 | `docs/quota_plan.md` | 高（自家文件） |

【判斷】觀測類工具起價 US$29～79 是工程團隊預算，個人開發者不會用同樣標準看「好玩的視覺化」；真正的錨點是**免費開源 2D**與**使用者本來就在付的 Claude 訂閱**。所以價格要明顯低於觀測工具。

**建議價格（新台幣／月）**

| 層級 | 建議區間 | 年繳 | 理由與風險 |
|---|---|---|---|
| Free | 0 | — | 成本 ≈ 0；是擴散管道（截圖分享） |
| Plus | **NT$99～199**（我建議先從 NT$149 試） | 約 8 折 | 比 launch_plan 原寫的 149～249 略低端。定太高（≥ NT$249）：會輸給免費開源版，且個人使用者視為「裝飾費」；定太低（< NT$99）：金流費率與可能的固定手續費吃掉利潤（綠界費率未確認），客服成本也撐不住 |
| Pro（預留） | NT$299～499 | 約 8 折 | 面向多專案／小團隊；**前提是擁有者同意突破 3×5**。第一版不上，先驗證有人付 Plus |
| 單次購買（裝飾包） | NT$30～90 | — | 與 launch_plan 一致，第二波再做 |

誠實聲明：【事實】沒有查到任何「3D 且收費的 Claude Code 可視化」同類產品價格；【判斷】轉換率與願付價格完全沒有實測資料。損益平衡見 launch_plan（固定成本約 US$5／月，若 Plus 每月約 US$4～5，幾位付費者即可打平），**但那只含雲端費用，不含擁有者的時間、發票與稅務**。

### 3.5 辦公室最多幾個比較合理？

- **付費上限 3 間**（擁有者已定）：合理。理由：個人開發者同時活躍的專案多為 2～4 個；3 間涵蓋大多數；成本不是瓶頸，所以不必再放寬，保留日後 Pro 突破的空間。
- **免費 1 間**（我的建議）：免費者要先養成習慣再談升級；1 間 × 3 位的成本幾乎為 0。
- 避免「不划算」感的三個配套：①新會員 14 天體驗 Plus 上限，讓他先愛上；②超額專案進「待開通」而不是消失，且事件照收；③體驗結束超出部分休眠 30 天不刪除，升級後原樣回來。
- 如果擁有者想更大方，我認為**免費 2 間 × 3 位**也不會有成本問題；代價是 Plus 的升級誘因變弱（只剩 1 間與 2 個座位），要靠績效報表、歷史、外觀撐。我建議先 1 間，上線後看數據再放寬——放寬容易、收緊會被罵。

---

## 需要擁有者決定的事（最多五條）

| # | 題目 | 我的建議 |
|---|---|---|
| 1 | 接受「做不到 Claude 登入與自動讀專案清單」，改用 Google 登入＋一次性接入（本機外掛＋雲端環境）？ | **接受。** 同時接受情況 1 改成「尚未收到回報」、情況 3 改成「新專案第一次回報時自動建立」 |
| 2 | 「專案」的定義：Claude Code 的工作目錄／儲存庫，還是 claude.ai 聊天的 Projects？ | **Claude Code 工作目錄**（claude.ai Projects 完全讀不到） |
| 3 | 3 間 × 5 位是付費上限嗎？免費給多少？ | 付費上限；**免費 1 間 × 3 位＋14 天體驗**（天數與體驗額度由你設，我只建議）；第一版只上免費＋Plus |
| 4 | Plus 價格區間 | **NT$99～199／月，先試 NT$149**；先確認綠界費率再定下限 |
| 5 | 要不要先花 1～2 天做第 1.5 節的實測，再決定是否投入 | **要。** 四個關鍵點沒過就會推翻方案 a，現在最便宜的是先驗證 |

---

## 沒查到／不確定的（單獨列出）

1. Anthropic 是否有**明文**說「不開放第三方使用 Claude 登入」：只有政策類二手報導與法遵頁摘要，沒讀到官方全文。我的結論是「無此計畫、且有訂閱 OAuth 禁令」，不是「官方明說不行」。
2. 2026-04-04 後第三方工具改走額外用量計費的說法：單一部落格，**未證實**，不影響本方案（我們不碰使用者權杖）。
3. 外掛層級子 Agent 掛鉤是否可靠（issue 單一回報）；雲端設定腳本能否安裝外掛；掛鉤欄位是否含專案識別與 Token 數。
4. Cloudflare Durable Objects 免費額度的確切數字（第三方互相矛盾）；Workers 付費方案內含請求量（只在第三方看到 1,000 萬）；WebSocket 持續時間費。
5. 綠界／藍新的現行手續費率、是否有固定手續費、AI Office 的發票與稅務處理。
6. Cloudflare Turnstile 是否免費（印象，未查）。
7. Anthropic 商標指南全文與「Powered by Claude」用語適用範圍。
8. 3D 且收費的同類產品價格：查過但沒找到，不代表不存在。
9. Teamflow／Branch 等虛擬辦公室價格：搜尋未取得。
10. 所有使用量數字（活躍天數、每天工作階段、事件筆數、前景時間）都是假設，沒有實測。
11. 雲端工作階段在多個環境、多個裝置下的實際接入負擔。
12. 免費使用者「Gmail 與 Claude 帳號是否同一人」無法驗證，只能靠接入碼關聯。

---

## 我查過的關鍵字與來源（WebSearch，2026-11-13，皆只取得摘要）

| 主題 | 關鍵字（節錄） | 來源類型與代表連結 |
|---|---|---|
| Claude 登入／OAuth | "Sign in with Claude" OAuth third-party apps Anthropic；Anthropic Claude Code legal and compliance OAuth tokens third-party tools not permitted Agent SDK consumer subscription | 官方：[連接器驗證文件](https://www.claude.com/docs/connectors/building/authentication)、[Claude Code 法遵頁](https://code.claude.com/docs/en/legal-and-compliance)；媒體：[The Register](https://www.theregister.com/2026/02/20/anthropic_clarifies_ban_third_party_claude_access)、[WinBuzzer](https://winbuzzer.com/2026/02/19/anthropic-bans-claude-subscription-oauth-in-third-party-apps-xcxwbn/)、[GIGAZINE](https://gigazine.net/gsc_news/en/20260220-anthropic-third-party-block)；開發者社群：[DEV](https://dev.to/aabyzov/anthropic-just-banned-oauth-token-usage-in-third-party-tools-what-this-means-for-claude-developers-564l) |
| 列專案／工作階段 | claude.ai Projects API list projects programmatically；Claude Code on the web list sessions API GitHub repository | 官方：[Compliance API 專案列表](https://platform.claude.com/docs/en/api/http/compliance/apps/projects/list)、[Claude Code 網頁版](https://code.claude.com/docs/en/claude-code-on-the-web)；社群：[issue 29264](https://claudeissues.com/issue/29264-bug-past-conversations-web-tab-shows-no-sessions-yet-list-remote-sessions-return) |
| 掛鉤／外掛 | Claude Code hooks SubagentStart SubagentStop SessionStart HTTP hook；plugin hooks.json user scope；extraKnownMarketplaces enabledPlugins | 官方：[Hooks](https://code.claude.com/docs/en/hooks)、[外掛安裝](https://code.claude.com/docs/en/plugins/install)、[外掛組織管理](https://code.claude.com/docs/en/plugins/org)；社群：[issue 16288](https://claudeissues.com/issue/16288-plugin-hooks-not-loaded-from-external-hooks-json-file)、[issue 32606](https://github.com/anthropics/claude-code/issues/32606) |
| 雲端環境 | Claude Code on the web environment setup script network access allowlist；web sessions plans limits | 官方：[雲端環境](https://code.claude.com/docs/en/cloud-environments)、[網頁快速入門](https://code.claude.com/docs/en/web-quickstart)；媒體：[Anthropic 部落格](https://claude.com/blog/claude-code-on-the-web) |
| 連接器 | Anthropic custom connectors remote MCP server | 官方：[support 說明](https://support.claude.com/en/articles/11175166)、[自訂連接器文件](https://claude.com/docs/connectors/custom/remote-mcp) |
| 商標 | Anthropic trademark guidelines "Claude" product name | 官方：[商標指南](https://www.anthropic.com/legal/trademark-guidelines)；二手：[Clawdbot 改名報導](https://secureyourtrademark.com/blog/anthropic-forces-clawdbot-to-rebrand-as-moltbot/) |
| Cloudflare 價格 | Durable Objects pricing free plan SQLite；D1 KV pricing free tier；Workers pricing paid $5 WebSocket 20:1 | 官方：[DO 定價](https://developers.cloudflare.com/durable-objects/platform/pricing)、[Workers 定價](https://developers.cloudflare.com/workers/platform/pricing/)、[SQLite 儲存計費公告](https://developers.cloudflare.com/changelog/2025-12-12-durable-objects-sqlite-storage-billing)；第三方：flarecalc、toolradar、agentdeals |
| Google 登入 | Google OAuth openid email profile no verification | 官方：[品牌驗證](https://developers.google.com/identity/protocols/oauth2/production-readiness/brand-verification)、[granular permissions](https://developers.google.cn/identity/protocols/oauth2/resources/granular-permissions)；社群：Auth0 討論串 |
| 競品價格 | LangSmith Langfuse pricing 2026；Helicone AgentOps pricing；Gather Town pricing 2026 | [Gather 官方說明](https://support.gather.town/hc/en-us/articles/39590892978196)；第三方：costbench、activepieces、truefoundry、aitoolsatlas |
| 台灣金流 | 綠界 ECPay 藍新 NewebPay 手續費 個人 定期定額 | 只找到[綠界定期定額 API 文件](https://developers.ecpay.com.tw/2900/)，**無費率** |

本地已讀文件：`docs/ai_office/plan.md`、`launch_plan.md`、`rewards_design.md`（前 80 行）、`docs/login_setup.md`、`docs/quota_plan.md`、`docs/hosting_cost_plan.md`、`docs/compliance_and_tiers.md`（摘要段）、`docs/payment_newebpay_plan.md`（摘要段）、`workers/README.md`、`workers/account-api/pay.js`（檔頭）。

---

## 第一步（一個人、沒有後端也做得到）

用一個不重要的專案，自己做第 1.5 節 T1～T4：裝一個只含 `hooks.json`（SubagentStart／SubagentStop／SessionStart 各一筆 HTTP 掛鉤，指向一個會把收到內容記下來的測試 Worker）的外掛，本機跑一個會派子 Agent 的工作階段；再到雲端預設環境加網路白名單與設定腳本，跑一次雲端工作階段。兩邊都收到、且欄位夠用，方案 a 才成立。
