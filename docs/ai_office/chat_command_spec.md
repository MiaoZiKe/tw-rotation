# AI Office 網站對話框指令：規格（第一版）

> 2026-11-15 建立。擁有者要的：在辦公室頁（`site/office/world.html`）有一個對話框，他打的指令可以指定給辦公室裡任何一位 Agent（或交給 CEO 分派），
> 而且由**他自己串接的 Claude（雲端 Claude Code 工作階段）**執行；**網站本身絕不呼叫 Claude、不花站長的額度**。
>
> 這一版已完成：收件服務的收件匣 API（`workers/ai-office-bridge/worker.js`）＋測試、外掛的取指令掛鉤與待命腳本（`tools/ai_office_bridge/plugin/ai-office-bridge/scripts/inbox.py`）＋測試。
> **還沒做**：網站對話框（另派前端，介面見第六節）。這一版只在開發分支，沒推 main、沒推預覽。
>
> 標示：【官方】＝讀過官方文件原文（出處見第十節）；【實測】＝`bridge_test_report.md` 或本版測試親眼看過；【未查證】＝只有搜尋摘要或推論。

---

## 一、一句話與原則

**網站只是一個「留言板」：擁有者把指令貼上去，他自己的 Claude 工作階段來把指令拿走、做完、把回覆貼回來。**

1. 網站與收件服務（Cloudflare Worker）**完全不呼叫任何模型**。花的模型額度只有「擁有者自己的 Claude 方案」——跟他直接在 Claude 裡打字一樣。站長這邊只用到 Cloudflare 免費方案的請求數與儲存。
2. 指令永遠是「Claude 去拿」，不是「網站推進去」：網站沒有任何能碰到 Claude 工作階段的權杖。
3. 預設關閉：外掛裝了也不會取指令，要擁有者在自己的環境設 `AIO_INBOX=1` 才開。

---

## 二、資料流

```
擁有者（網站登入：Google 管理者帳號）
   │ ① 對話框送出 {to: "ceo" 或 Agent 名稱, text}
   ▼   POST /v1/office/main/inbox      ← 只認網站登入（X-AIO-Session）＋白名單 Origin；接入碼不能寫
收件服務 tw-ai-office-bridge（Durable Object：inbox 資料表）
   │   狀態：排隊中（queued）
   │
   │ ② Claude 端取走（任一條路先到先拿，同一則只會給一次）
   │     · Stop 掛鉤：回合結束時取 → decision "block"＋reason，Claude 接著做
   │     · UserPromptSubmit 掛鉤：擁有者在 Claude 打字時順便取 → additionalContext
   │     · 待命模式：Claude 開的背景長輪詢指令取到 → 指令結束、喚醒工作階段
   ▼   POST /v1/inbox/pull             ← 只認接入碼，而且「帶 Origin 一律拒絕」（瀏覽器拿到碼也取不走）
擁有者自己的 Claude 雲端工作階段
   │   狀態：已取走（claimed）
   │ ③ Claude 開始做：inbox.py ack <編號> running      → 執行中（running）
   │ ④ 做完：inbox.py ack <編號> done --reply "重點"    → 完成（done）／失敗（failed）
   ▼   POST /v1/inbox/ack
收件服務：存回覆、狀態變化另寫一筆 InboxUpdate 事件（只有編號與狀態，不含內文）
   │
   │ ⑤ 網站每 5～15 秒讀 GET /v1/office/main/inbox?since=<rev>（只認網站登入）
   ▼
對話框顯示狀態與回覆
```

---

## 三、收件匣 API（已實作，`workers/ai-office-bridge/worker.js`）

### 3.1 網站端（擁有者網站登入）

身分：標頭 `X-AIO-Session: <網站登入權杖>`，**而且必須帶白名單 Origin**（`ALLOWED_ORIGINS`：正式網域、www、GitHub Pages）。
收件服務透過服務綁定問會員 Worker（`tw-account`）的 `/v1/me`，`user.admin` 為真才算「綁定這間辦公室的人」（第一版只有擁有者一間 `main`；結果快取 10 分鐘）。**接入碼在這三條路由一律無效**。

| 方法與路徑 | 本文 | 回應 | 錯誤 |
|---|---|---|---|
| `POST /v1/office/main/inbox` | `{ "to": "ceo" 或 Agent 名稱, "text": "…" }` | `{ ok, message: {id, to, text, status:"queued", created, …} }` | 401 不是擁有者／403 Origin 不對或不是自己的辦公室／400 `bad_to`、`empty`／413 `too_long`／429 `rate`、`rate_day`、`queue_full` |
| `GET /v1/office/main/inbox?since=<rev>` | — | `{ rev, messages:[…], open:[…進行中…], limits:{max_text, max_pending}, session_last_seen }` | 401／403／429 |
| `POST /v1/office/main/inbox/<id>/cancel` | `{}` | `{ ok }` | 404／409 `not_queued`（已被取走就不能撤回） |

- `since=0`：回最近 50 則；`since=<rev>`：只回 rev 之後有變化的。`open` 永遠附上所有進行中的（「沒有回音」是依時間推算的，增量讀不會因時間經過而回傳）。
- `session_last_seen`：最近一支沒結束的工作階段最後一次送事件的時間，給對話框判斷「你的 Claude 現在在不在」。
- `GET /v1/office/main/state` 多了 `inbox: { queued, active, rev }`，網站平常輪詢 state 時就知道要不要去讀收件匣。

### 3.2 Claude 端（接入碼）

身分：`Authorization: Bearer <接入碼>`（雲端由環境「網路金鑰」在代理端注入，腳本不持有）。**帶 `Origin` 標頭一律 403 `browser_not_allowed`**。

| 方法與路徑 | 本文 | 回應 |
|---|---|---|
| `POST /v1/inbox/pull` | `{ session_id, wait: 0～20 秒, max: 1～5 }` | `{ ok, source:"website", messages:[{id, to, text, created}] }`；沒有就 `messages: []` |
| `POST /v1/inbox/ack` | `{ id, status: "running"｜"done"｜"failed", reply?, session_id }` | `{ ok, status }`；409 `not_active`（已完成／撤回／過期的不能再改） |

- 取走是同步「查＋標記」，中間沒有 await：兩支工作階段同時取，同一則只會給其中一支（測試「取走後同一則不會再給第二支工作階段」）。
- 長輪詢：`wait>0` 且沒有指令時，請求掛著；網站一送就立刻叫醒回傳（測試實測 < 2 秒）；時間到回空陣列。
- 回覆：去控制字元（保留換行）、遮疑似金鑰（`aio_`、`ghp_`、`github_pat_`、`sk-`、`xox?-`、`AKIA`、`Bearer …`、48 字以上的長串），截到 4000 字。**網址與路徑保留**（回覆只給擁有者看，預覽網址要能點）。

### 3.3 狀態

| 狀態值 | 對話框顯示 | 怎麼來的 |
|---|---|---|
| `queued` | 排隊中 | 網站送出 |
| `claimed` | 已取走 | Claude 端 pull 取到 |
| `running` | 執行中 | Claude `ack running` |
| `done` | 完成 | Claude `ack done` |
| `failed` | 失敗 | Claude `ack failed` |
| `canceled` | 已撤回 | 擁有者在排隊中撤回 |
| `expired` | 過期（沒有 Claude 來拿） | 排隊超過 24 小時 |
| `stale` | 沒有回音 | 推算值：取走 30 分鐘沒回報執行中、或執行中 6 小時沒更新。**不會自動重新排隊**（避免同一件事做兩次），擁有者可以重送 |

### 3.4 上限

| 項目 | 值 |
|---|---|
| 一則指令 | 2,000 字（超過 413） |
| 一則回覆 | 4,000 字（超過截短） |
| 排隊中同時最多 | 20 則 |
| 擁有者送出 | 每分鐘 10 則、每天 100 則 |
| Claude 端 pull／ack | 各每分鐘 120 次 |
| 長輪詢單次 | 最多 20 秒；一次最多取 5 則 |
| 保留 | 每間辦公室最近 500 則；「進階 → 刪除所有紀錄」連收件匣一起清 |
| 驗證錯誤 | 同一來源 10 分鐘錯 20 次就先擋（沿用既有） |

---

## 四、Claude 端怎麼收（已實作，`scripts/inbox.py`）

外掛 `hooks/hooks.json` 在 `UserPromptSubmit` 與 `Stop` 各多一支**同步**掛鉤 `inbox.py hook <事件>`（`timeout: 10`；腳本自己的連線逾時 3 秒，任何錯誤安靜 exit 0、不輸出）。`install_hooks.py` 認得新腳本，重跑不重複、`--remove` 一起拿掉。

### 4.1（a）掛鉤取收件匣

**Stop 掛鉤**（回合結束時）
- 官方欄位【官方】：Stop 的輸入多了 `stop_hook_active`、`last_assistant_message`、`background_tasks`、`session_crons`。`stop_hook_active` 為 true 表示「這次本來就是被 Stop 掛鉤接續的」。
- 官方行為【官方】：輸出 `{"decision":"block","reason":"…"}`，「`decision: "block"` prevents Claude from stopping」「`reason` … Required when `decision` is `"block"`. Tells Claude why it should continue」；exit 2 也一樣，stderr 當成 reason。
- 迴圈保護【官方】：「after stop hooks have continued the turn eight times in a row, Claude Code overrides the next block and ends the turn. The count of consecutive continuations resets each time Claude calls a tool」（上限可用 `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP` 調）。我們每次 block 都是「真的取到新指令」，取走就不會再給，所以不會無限接續；就算擁有者連送 9 則，最多也是第 9 次被系統強制停下，下一回合再接。
- 我們的做法：有新指令才輸出 `decision: block`，`reason` 是包裝好的指令文字（4.3）；沒有就什麼都不輸出，Claude 照常停下。
- 預設用 `block`（2026-11-13 已實測可行，畫面會出現一行掛鉤錯誤字樣、其實不是錯誤）。官方另有 `hookSpecificOutput.additionalContext`：「the transcript labels it `Stop hook feedback` and no hook error notification is shown」，同樣受 8 次上限保護。設 `AIO_STOP_MODE=context` 可改用這種，**畫面較乾淨但我們還沒在真的工作階段實測過**。

**UserPromptSubmit 掛鉤**（擁有者在 Claude 裡打字時）
- 官方【官方】：輸入有 `prompt`；輸出 `hookSpecificOutput.additionalContext`「String added to Claude's context alongside the submitted prompt」，以系統提醒注入、不顯示在對話紀錄。這個事件的掛鉤預設逾時是 30 秒，而且「a stuck hook stalls the session」——所以我們把連線逾時壓到 3 秒。
- 我們的做法：有新指令就以 additionalContext 附上；不擋擁有者這次打的字（不用 `decision: block`，那會把他的輸入丟掉）。

### 4.2（b）待命模式（閒置時也能收）

掛鉤只在「Claude 有動靜」時觸發；Claude 閒著時要靠待命：

1. 擁有者在 Claude 裡說一次「進入 AI Office 待命」，Claude 用**背景指令**執行：
   `python3 "<外掛路徑>/scripts/inbox.py" wait`（Bash 工具 `run_in_background: true`、`timeout: 1800000`）。
2. 腳本每次對收件服務長輪詢 20 秒，一直等到有指令或滿 25 分鐘。
3. 有指令：印出包裝好的指令（4.3，多一條「處理完再開一次待命」）並結束 → **背景指令結束會通知並喚醒工作階段**，Claude 讀到輸出就照做。
4. 25 分鐘沒指令：印「待命結束：沒有新指令，要繼續等就再執行一次」並結束，Claude 再開一次。
5. 接入碼被拒（401／403）：印原因並結束，不空轉。限速、連不上：退避（2→30 秒）重試，不提早結束。

依據與限制：
- 背景指令時限【官方】：雲端工作階段屬於「runs unattended」，背景指令「gets 30 minutes, or the `timeout` Claude passes with `run_in_background`, up to a maximum of 2 hours」，到時會被停掉並告知 Claude。所以待命預設 25 分鐘自己先結束，Claude 再開下一輪。
- 背景指令結束會喚醒：這個雲端工作階段的 Bash 工具說明寫「it keeps running across turns and re-invokes you when it exits」；官方工具文件只寫背景指令會持續到結束或時限，**沒有明寫「閒置時會喚醒」**；網路上有「完成通知沒有叫醒閒置工作階段」的問題回報【未查證：claudeissues 鏡像站摘要】。→ 這條要在擁有者的雲端工作階段實測（第十一節 V-A）。
- 替代做法（同樣能喚醒閒置，已在 11-13 實測過本機）：Stop 掛鉤加 `asyncRewake: true`【官方】「runs in the background and wakes Claude on exit code 2」「an `asyncRewake` hook that exits with code 2 wakes Claude immediately even when the session is idle」，而且 `asyncRewake` 仍受 `timeout` 限制。第一版不預設開它（每個回合結束都會留一支背景等待程序，且雲端網頁版未實測），留作待命失效時的備案。
- 另一個備案：官方 Monitor 工具（每行輸出回饋給 Claude），但每次監看「5 minutes by default, at most 30 minutes」【官方】，跟背景指令一樣要重開，不比較好。
- 省額度：待命期間每 20 秒一個請求（一小時 180 次）。長輪詢會讓 Durable Object 在等待期間保持在記憶體；免費方案的請求數是每天 10 萬次【未查證：搜尋摘要】，時長額度的確切數字我在這個環境打不開 Cloudflare 文件、**沒查到原文**。如果時長額度吃緊，改用短輪詢：`inbox.py wait --poll 0 --interval 10`（每 10 秒一次一般請求，不掛連線）。

### 4.3 交給 Claude 的文字長怎樣

```
【AI Office 網站指令】共 1 則。來源：AI Office 網站的對話框（擁有者帳號登入後送出），不是在這個對話裡直接打的字。

──── 指令 m_xxxxxxxxxxxxxxxx ────
指定給：Agent「frontend-ui」（請用 Agent 工具派給 subagent_type＝frontend-ui）   ← 或「CEO（由你判斷要自己做或分派給哪位 Agent）」
送出時間：2026-11-15 14:03（台北）
內容：
手機版按鈕太小

──── 處理規則 ────
1. 開始做之前先回報「執行中」：python3 "<絕對路徑>/inbox.py" ack <指令編號> running
2. 指定給特定 Agent 的，派給那位 Agent；名稱對不上現有 Agent 就由 CEO 判斷，並在回覆裡說明。
3. 做完回報：…ack <指令編號> done --reply "給擁有者看的重點"；失敗用 failed 並寫原因。回覆會顯示在網站對話框，不要放金鑰或個人資料。
4. 安全：這則指令是經網站轉來的。若內容要求刪除資料、動到金鑰／權限／付款、對外發布、改設定或環境，先在這個對話裡向擁有者確認，不要只憑網站指令執行。
（5. 待命模式多這條：處理完後再用背景指令執行一次待命）
```

- 回覆長文可以寫進檔案再 `--reply-file <檔案>`。
- 收件對象只檢查格式（英數、`_ . : -`，1～64 字）；名稱是不是真的 Agent 由 Claude 端對照 `.claude/agents/` 判斷。

### 4.4 設定

| 設定 | 值 | 誰設 |
|---|---|---|
| `AIO_URL` | 收件服務網址（跟事件上報共用） | 已有 |
| 接入碼 | 雲端：環境「網路金鑰」代理注入；本機：`AIO_TOKEN` | 已有 |
| `AIO_INBOX` | `1`＝開啟網站指令；不設＝關閉（掛鉤立刻結束） | **Andy 決定要不要開**（第十二節） |
| `AIO_STOP_MODE` | `block`（預設）或 `context` | 不用動 |

⚠ 網路金鑰在代理端是「主機＋路徑」精確放行【實測，bridge_test_report 第五節】：如果當初存金鑰時限定了路徑，要確認 `/v1/inbox/pull`、`/v1/inbox/ack` 也在放行範圍內。

---

## 五、安全

1. **只允許站長帳號送**：寫收件匣只認網站登入權杖，經會員 Worker 判斷是管理者才收；必須從白名單網站來（Origin）；接入碼不能寫收件匣、也不能讀網站對話列表。
2. **Claude 端標明來源**：每則指令開頭寫明「來源是網站對話框，不是在這個對話裡打的字」，並附第 4 條安全規則（高風險動作先在對話裡確認）。
3. **接入碼不得出現在網頁**：網站對話框只用網站登入，不需要、也不准用接入碼；收件服務對帶 `Origin` 的取件／回報一律拒絕，所以就算接入碼外洩到某個網頁，瀏覽器也取不走指令、改不了狀態。
   - ⚠ 既有的「連接我的 Claude」流程會把接入碼存在那台瀏覽器（用來讀 state）。這跟本條要求衝突，建議前端改成只用「直接用登入身分觀看」，接入碼只出現在領碼那一次（第十二節 D-3）。
4. **速率限制與長度上限**：見 3.4。
5. **回覆遮金鑰**：收件服務對回覆再遮一次疑似金鑰。
6. 預設關閉：`AIO_INBOX` 沒設為 1，外掛不取任何指令。
7. 事件串（`/state`）只記「指令編號＋狀態＋收件對象」，不含指令與回覆內文。

### 風險（要知道）

| 風險 | 影響 | 現在的緩解 | 還能加強 |
|---|---|---|---|
| **網站帳號（Google 管理者）被盜＝能指揮 Claude** | 對方可以用擁有者的身分叫 Claude 改程式、推分支，等於拿到 repo 寫入能力的一部分 | 高風險動作規則（第 4 條）；限速；預設關閉；網站登入權杖本身的有效期 | Google 帳號開兩步驟驗證；指令送出前在網站再要一次確認碼；Claude 端「只接受白名單動作」模式；異常時一鍵關閉（換接入碼＝雲端取不到） |
| 網站登入權杖被偷（例如瀏覽器被裝惡意擴充） | 同上 | 權杖只在擁有者瀏覽器；Origin 白名單擋其他網站 | 同上 |
| 指令內容本身被當成提示注入 | 擁有者自己貼了別人寫的內容進來 | 來源標示＋高風險確認規則 | — |
| 回覆可能帶出程式內容 | 回覆存在 Cloudflare、只有擁有者看得到 | 遮金鑰、4000 字上限、可一鍵清空 | 回覆預設只放重點（處理規則第 3 條） |
| 同一則被做兩次 | — | 取件同步標記；「沒有回音」不自動重排 | — |
| 掛鉤欄位隨版本改變 | 掛鉤失效（不會壞工作階段，只是收不到） | 腳本對缺欄位容錯、錯誤一律安靜結束 | 網站顯示「排隊太久沒人拿」提醒 |

---

## 六、網站對話框介面（交給前端，這一版不做）

> **2026-11-15 晚改版：主對話框。** 下面這一節描述的是第一版（頂列「下指令」鈕＋右側面板＋收件對象下拉）。擁有者後來要求改成「畫面下方常駐的主對話框」，現行做法：
> 輸入列常駐在畫面底部（寬螢幕在正中間的帶狀區、窄螢幕貼左、手機貼底並讓出客服鈕）；沒選人＝對 CEO 說；點 3D 的 Agent 或資訊卡「對他說」＝對象切成他（頭像、名字、他的對話串）。
> 技術上沒變：一律 `POST /v1/office/main/inbox`，`to` 欄位＝指定的 Agent（沒指定＝`ceo`），CEO 的 Claude 取走後派給那位；對話串依 `to` 分組、不另存資料。
> 鍵盤改成聊天軟體習慣：Enter 送出、Shift＋Enter 換行、Esc 收合；注音選字中的 Enter 不算送出。頂列「下指令」鈕已移除（理由見 HANDOFF／回報）。程式在 `site/office/world/js/chat.js`、`chat.css`；驗收段落「辦公室主對話框」（`scripts/uitest_sections/20261115_office_mainchat.py`）。

位置：辦公室頁 `site/office/world.html`，頂列或右下角一顆「對話」鈕，點開側邊抽屜（手機全螢幕）。照 `docs/andy_ui_rules.md` 與手機五條準則（預設收起、客服鈕位置不衝突）。

| 區塊 | 內容與行為 |
|---|---|
| 收件對象下拉 | 第一項「**交給 CEO 分派**」（值 `ceo`，預設）；其後是辦公室裡所有 Agent（名稱用辦公室角色名，值用 Agent 代號，例如 `frontend-ui`）。清單來源：辦公室角色表（`site/office/world/js/` 內既有的角色資料）；即時模式下可再合併 `/state` 的 `types[].agent_type` |
| 輸入框 | 多行；右下顯示「已輸入 N／2000」；超過不能送。Enter 換行、Ctrl/⌘+Enter 送出 |
| 送出鈕 | 沒登入／不是擁有者：灰掉並寫「用管理者帳號登入後才能下指令」。送出中鎖住避免連按 |
| 你的 Claude 在不在 | 依 `session_last_seen`：5 分鐘內「你的 Claude 在線上」，否則「你的 Claude 目前沒開，指令會排隊，下次開工作階段時才會被取走（最多保留 24 小時）」 |
| 訊息列表 | 由舊到新；每則：收件對象、送出時間（台北）、內容、狀態標籤、回覆（有就顯示，保留換行、網址可點）。排隊中的有「撤回」 |
| 狀態標籤 | 排隊中（灰）／已取走（藍）／執行中（藍＋轉圈）／完成（綠）／失敗（紅）／已撤回、過期（淡灰）／沒有回音（黃，附「重送」） |
| 錯誤提示 | `too_long`「最多 2000 字」、`queue_full`「排隊已滿 20 則，等 Claude 取走一些再送」、`rate`「送太快了，一分鐘後再試」、`rate_day`「今天已送 100 則」、401「登入過期，請重新登入」 |
| 輪詢 | 抽屜開著：每 5 秒 `GET …/inbox?since=<rev>`；關著：跟著 `/state` 每 15 秒，`inbox.rev` 變了才讀；分頁在背景暫停 |
| 動畫（選配） | 指令被取走時，被指定的 Agent 在辦公室裡走到 CEO 桌前領任務（`InboxUpdate` 事件） |

呼叫方式（前端用 fetch）：

```js
fetch(BRIDGE + '/v1/office/main/inbox', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-AIO-Session': 網站登入權杖 }, body: JSON.stringify({ to, text }) })
fetch(BRIDGE + '/v1/office/main/inbox?since=' + rev, { headers: { 'X-AIO-Session': 網站登入權杖 } })
fetch(BRIDGE + '/v1/office/main/inbox/' + id + '/cancel', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-AIO-Session': 網站登入權杖 }, body: '{}' })
```

驗收（前端那一批要加 `scripts/uitest_sections/<日期>_辦公室對話框.py`）：選 Agent→送出→列表出現「排隊中」；本機 devserver 用 `inbox.py hook Stop` 取走→變「已取走」；`ack done --reply`→顯示回覆；超過 2000 字送出鈕灰掉；撤回；手機 390 寬全螢幕可用。⚠ 這是使用者看得到的新功能：上線那個 commit 要依規矩在 `site/features.js` 註冊功能鍵（只開給站主）並在 `site/notices/features.json` 判斷要不要發公告（只給管理者的功能不發給一般人）。

---

## 七、限制

1. **沒有開著的工作階段時，指令只會排隊**：要等擁有者下次開工作階段（或在現有工作階段打一句話、或回合結束）才會被取走；排隊 24 小時沒人拿就過期。
2. **雲端工作階段閒置會被回收**【官方】：「Cloud sessions stop after a period of inactivity and the session's VM is reclaimed」，重開時對話保留，但「background work that was still running … Shell commands」不會恢復——**待命指令會跟著消失**，要重開待命。官方沒寫閒置多久會回收【未查證】。
3. 待命本身會讓工作階段每 25 分鐘醒來一次（沒指令時只是重開待命），會用掉一點點擁有者的額度；待命中的工作階段是否因此不被判定閒置，【未查證】。
4. Stop 接續上限 8 次（官方），超過會被強制停下，下一回合再取。
5. 一則指令只交給一支工作階段（先到先拿）；目前不能指定「要哪一支工作階段做」。
6. 第一版只有擁有者一間辦公室（`main`）、只有管理者帳號能送。

---

## 八、改了哪些檔

| 檔案 | 內容 |
|---|---|
| `workers/ai-office-bridge/worker.js` | 收件匣資料表、五條路由、長輪詢、狀態流轉、`InboxUpdate` 事件、`/state` 附 `inbox` 摘要、刪除紀錄連收件匣一起清、`maskSecrets` |
| `workers/ai-office-bridge/test/inbox.test.mjs` | 新增 8 組測試 |
| `workers/ai-office-bridge/test/index.js` | 指資料夾跑測試時也載入新測試 |
| `tools/ai_office_bridge/plugin/ai-office-bridge/scripts/inbox.py` | 新增：hook／wait／ack |
| `tools/ai_office_bridge/plugin/ai-office-bridge/scripts/test_inbox.py` | 新增：起本機真收件端端到端測試 |
| `tools/ai_office_bridge/plugin/ai-office-bridge/hooks/hooks.json` | `UserPromptSubmit`、`Stop` 各加一支同步 `inbox.py hook` |
| `tools/ai_office_bridge/plugin/ai-office-bridge/scripts/install_hooks.py` | 認得 `inbox.py`、路徑替換改成整個 scripts 資料夾 |
| `tools/ai_office_bridge/plugin/ai-office-bridge/.claude-plugin/plugin.json` | 版本 0.2.0、說明 |
| `.github/workflows/deploy-ai-office-bridge.yml` | 部署前多跑收件匣測試與外掛收件匣測試 |

---

## 九、測試

```bash
node --test workers/ai-office-bridge/test/bridge.test.mjs workers/ai-office-bridge/test/inbox.test.mjs   # 收件服務：既有 13 ＋新 8
python3 tools/ai_office_bridge/plugin/ai-office-bridge/scripts/test_bridge.py                          # 外掛既有
python3 tools/ai_office_bridge/plugin/ai-office-bridge/scripts/test_inbox.py                           # 外掛收件匣（起本機真收件端）
```

測試裡的假權杖與假金鑰都在執行時拼接，repo 裡沒有任何真的碼。

---

## 十、查證出處（2026-11-15 讀取）

| 出處 | 用在哪 |
|---|---|
| 官方掛鉤文件 <https://code.claude.com/docs/en/hooks>：Stop 段（輸入欄位、decision control、8 次接續上限、`additionalContext`）、UserPromptSubmit 段（`prompt`、`additionalContext`、`decision: block` 會丟掉輸入、逾時預設 30 秒）、Run hooks in the background 段（`async`、`asyncRewake` exit 2 喚醒閒置、`asyncRewake` 仍受 timeout）、逾時預設值表 | 4.1、4.2 |
| 官方工具文件 <https://code.claude.com/docs/en/tools-reference>：Background commands（雲端屬 unattended，背景指令 30 分鐘預設、最多 2 小時；到時停掉並告知）、Monitor tool（5 分鐘預設、最多 30 分鐘） | 4.2 |
| 官方雲端工作階段文件 <https://code.claude.com/docs/en/claude-code-on-the-web>：Environment expired（閒置回收、背景指令不恢復）、網路金鑰在沙盒外由代理附加 | 七、五 |
| 本工作階段 Bash 工具說明：「re-invokes you when it exits」 | 4.2（待命喚醒） |
| WebSearch 摘要：claudeissues 鏡像站多則「背景指令完成通知沒叫醒閒置工作階段」問題回報（例如 issue 90555、21048） | 4.2 風險，【未查證】 |
| WebSearch 摘要：Cloudflare Durable Objects 免費方案每天 10 萬次請求、閒置在記憶體也計時長 | 4.2 省額度，【未查證】；developers.cloudflare.com 在這個環境被網路擋，打不開原文 |
| `docs/ai_office/bridge_test_report.md` 第七節：Stop `decision: block`、UserPromptSubmit `additionalContext`、`asyncRewake` 本機實測都通 | 4.1、4.2 |

---

## 十一、要在真的雲端工作階段實測的（我這邊測不到）

| # | 要驗什麼 | 怎麼驗 |
|---|---|---|
| V-A | 待命：背景指令結束會不會叫醒「閒置中」的雲端工作階段 | 擁有者開待命後什麼都不打，從網站送一則「回我一句 391」，看工作階段有沒有自己動起來（並截圖） |
| V-B | Stop 掛鉤 block 在雲端網頁版畫面長怎樣；`AIO_STOP_MODE=context` 是否較乾淨 | 回合進行中從網站送指令，等回合結束看畫面 |
| V-C | 雲端主工作階段有沒有吃到外掛掛鉤（沿用 bridge_setup V1） | 跟事件上報一起驗 |
| V-D | 網路金鑰的放行路徑是否涵蓋 `/v1/inbox/*` | 開 `AIO_INBOX=1` 後跑一次 `inbox.py wait --minutes 0.1`，看是不是「待命結束：沒有新指令」而不是被代理擋 |

---

## 十二、需要 Andy 決定或動手的

| # | 事項 | 擋不擋 | 說明 |
|---|---|---|---|
| D-1 | **要不要開網站指令**（風險：Google 管理者帳號被盜＝能指揮你的 Claude） | 擋開通 | 同意的話，CEO 送核准卡片把 `AIO_INBOX=1` 加到雲端環境變數（非機密）。建議同時確認 Google 帳號已開兩步驟驗證 |
| D-2 | 網站對話框前端 | 擋「網站上看得到」 | 這一版不做，另派前端；介面見第六節 |
| D-3 | 接入碼不要再存在瀏覽器 | 不擋 | 建議前端把「連接我的 Claude」改成只用登入身分觀看，接入碼只在領碼那一次出現 |
| D-4 | 收件服務新版部署 | 擋開通 | 推上 main 時部署流程自動部署，不需要新金鑰；這一版還在開發分支 |
| D-5 | 第十一節的實測 | 擋「確定可用」 | 要 Andy 在雲端工作階段畫面上看並截圖 |
