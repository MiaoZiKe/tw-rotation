# AI 辦公室「真的」端到端驗證報告（2026-11-15）

> 擁有者原話：「這是這系統最重要的設定，所以可以的話幫我找使用者使用，並且實際操作驗證，確保串接成功後，都可以在對話框上面進行，下達提示詞後，會做出對應行為，生產對應 AI Office 辦公室工作區 Agent，且真的有在執行，並且每個 Agent 都可以進行下達指令。」
>
> 這份報告驗的是**整條真的鏈路**：網站（真的瀏覽器、真滑鼠、真鍵盤）⇄ 收件服務（真的 worker.js，wrangler 本機版）⇄ 外掛（真的掛鉤）⇄ **真的 Claude Code 工作階段**（`claude -p`，有真的子 Agent、真的改檔）。
> 跟 `scripts/uitest_sections/*office*` 的差別：那些用假的收件服務；這裡沒有任何一段是假的，唯一替代的是「Google 登入」（見第二節）。

## 一、結論（先看這段）

| # | 鏈路的一步 | 結果 |
|---|---|---|
| 1 | 接入：頂列「連接我的 Claude」→ 接入引導 →「複製接入碼」自動產生一組碼、只顯示遮罩 | ✅ |
| 2 | 用這組碼設定外掛（`install_hooks.py`＋`~/.ai-office/config.json`）→ 開 Claude → 網站「已接上 ✓」 | ✅ |
| 3 | 辦公室出現這個專案（名稱＝專案資料夾）與 CEO，頂列「即時」 | ✅ |
| 4 | 對 CEO 下指令（README 加今天日期）→ Claude 取走、真的改檔、回報 → 網站狀態 排隊中→已取走→執行中→完成、看得到回覆 | ✅ |
| 5 | 對 CEO 下「派 tester 跑測試、派 frontend 改 h1」→ Claude 真的派兩位子 Agent（收件服務收到 SubagentStart／SubagentStop）、真的改檔 | ✅ |
| 6 | 辦公室為新的子 Agent 類型（tester、frontend）**生產角色、坐進座位** | ✅（修了一個斷點，見三之 2） |
| 7 | 真滑鼠點 3D 裡的 tester → 資訊卡「對他說」→ 下指令 → Claude 派的就是 tester → 完成、回覆出現在他的對話串 | ✅（修了兩個斷點，見三之 2、三之 3） |
| 8 | 同上，對 frontend 下指令 → Claude 派 frontend → index.html 的 title 真的改了 | ✅ |
| 9 | 至少 3 位不同 Agent 各下一次指令都真的完成（CEO、tester、frontend） | ✅ |
| 10 | 撤回一則排隊中的指令 → Claude 從頭到尾沒看到它（完整對話紀錄裡沒有那段字、檔案沒被改） | ✅ |
| 11 | 網站沒有 JavaScript 例外 | ✅ |

最後一輪的逐項結果、時間、截圖見第四節。整條流程可重跑：`bash scripts/e2e/ai_office_e2e.sh`（第六節）。

## 二、怎麼搭的（全部在本機，不連線上服務、不用任何金鑰）

| 元件 | 這次用什麼 | 正式環境是什麼 |
|---|---|---|
| 網站 | `git archive HEAD site` → 刪 `site/data`、`site/preview` → `minify_site.py` 壓縮（跟部署同一支）→ `python -m http.server 8805`；網址帶 `?aio_url=http://127.0.0.1:8806`（live.js 既有參數，沒改產品預設值） | Cloudflare／GitHub Pages |
| 收件服務 | `workers/ai-office-bridge/worker.js`（HEAD 版）用 `wrangler dev --local`（4.162.0，miniflare，本機 SQLite），`--var ALLOWED_ORIGINS:http://127.0.0.1:8805` | Cloudflare Worker＋Durable Object |
| 站長登入 | **替代**：`scripts/e2e/fake_account.py`（本機假會員服務，只認一組每次隨機產生的「站長測試權杖」）；收件服務用 `--var ACCOUNT_API_URL` 指過去（worker.js 既有的替代路徑）；瀏覽器在 `localStorage['tw.acct.tok']` 放同一組權杖（＝主站 Google 登入後放權杖的同一個鍵） | Google 登入 → 會員 Worker（tw-account）`/v1/me`，服務綁定 `ACCOUNT` |
| 使用者的 Claude | `/opt/node22/bin/claude -p`（2.1.325，模型 sonnet），暫時 HOME；外掛用 `install_hooks.py` 裝進 `~/.claude/settings.json`；`~/.ai-office/config.json` 放收件服務網址＋接入碼＋`AIO_INBOX=1` | 擁有者的雲端工作階段（設定腳本裝外掛，接入碼由網路金鑰注入） |
| 使用者專案 | 暫存資料夾 `demo-calc`（git init）：README.md、calc.py、test_calc.py、index.html、`.claude/agents/tester.md`、`.claude/agents/frontend.md` | 擁有者的儲存庫 |
| 操作 | Playwright（`/opt/pw-browsers/chromium`）真滑鼠點、真鍵盤 Enter 送出；中文用 `keyboard.insert_text`（＝輸入法選字送出那一下） | 擁有者本人 |

**Claude 怎麼收指令**：整輪只開**一個** `claude -p` 工作階段，用待命模式——開場提示詞請它用背景指令跑 `inbox.py wait`；網站一送出，收件服務叫醒長輪詢 → `wait` 印出指令並結束 → 背景指令結束喚醒工作階段 → Claude 照規則 `ack running` → 做事（必要時用 Agent 工具派子 Agent）→ `ack done --reply …` → 再開一次 `wait`。（實測：無頭模式 `-p` 也會等背景指令結束再喚醒，不會提早結束。）

## 三、發現的斷點與修法

### 1. 頂列與接入引導把「站長自己送的指令」當成 Claude 已接上（已修，live.js）
- 現象：Claude 根本還沒開，只要站長在對話框送出／撤回過一則指令，頂列就變成綠燈「即時・最後更新」，接入引導一收到下一筆就誤報「已接上 ✓」。
- 原因：收件服務的 `total_events` 也算收件匣的 `InboxUpdate`（站長送出、撤回都會寫一筆）；live.js 拿它判斷「有沒有收到 Claude 的回報」。
- 修法：改用「各專案的事件數加總」（只有掛鉤事件會有專案）判斷已接上、即時、連上提示。commit `bfaafacc`。
- 驗證：最後一輪「Claude 還沒開工前，引導維持『等待你的 Claude 回報…』」✅、「Claude 開工後顯示已接上」✅。

### 2. 對新同事下指令，Claude 找不到這位 Agent（已修，live.js）
- 現象：辦公室為新的子 Agent 類型 `tester` 生出的角色代號是 `x-tester`；點他「對他說」送出後，收件匣的 `to` 是 `x-tester`，inbox.py 告訴 Claude「派給 subagent_type＝x-tester」——專案裡沒有這位。
- 修法：角色代號直接用子 Agent 類型名（合收件匣 `to` 格式、沒撞名時；撞名或格式不合才退回 `x-` 前綴）。驗收段落「辦公室即時模式」的代號同步改。commit `2b8d4d78`。
- 驗證：最後一輪「收件匣收到的 to＝tester」「Claude 真的派了 tester（SubagentStart 多一筆）」✅（frontend 同）。

### 3. 點過的同事去交件卡在原地（已修，attention.js）
- 現象：使用者「真滑鼠點 tester → 資訊卡『對他說』→ 送出」，Claude 做完了、網站也顯示完成，但 3D 裡 tester 拿著文件站在原地，一直是「交件中」，資訊卡完成清單不增加。
- 原因：點角色會「選取」他；選取期間 attention.js 的「面向我」規則把**走路中**的人定在原地轉身看鏡頭，直到取消選取。「對他說」之後他還是被選著，所以走去交件的路一直走不動。
- 重現（不花 Claude 額度）：同一個網站，選取 tester 後送 SubagentStart／SubagentStop → 40 秒模擬時間位置不動；修正後 14 秒走到 CEO 桌、34 秒回到待命。
- 修法：只有「正在走去領任務（queued）或交件（delivering）」的人照走、只轉頭看；其他走路（例行散步等）照舊停下面向鏡頭（不影響「辦公室角色視角」那段既有驗收）。commit `e5212f55`。

### 4. 測試環境踩到、但正式環境要知道的
| 事項 | 說明 | 要做什麼 |
|---|---|---|
| 專案沒被「信任」時，無頭模式忽略專案的允許清單 | 第一輪 Claude 要跑 `python3 inbox.py wait` 被「需要核准」擋掉，待命沒啟動、工作階段直接結束 | 互動式使用（擁有者的雲端工作階段）第一次會跳核准，按「允許」即可；建議在設定腳本或使用者設定加允許規則 `Bash(python3 /opt/ai-office-bridge/scripts/inbox.py:*)`，免得每次問（要擁有者同意才加） |
| `AIO_INBOX` 預設關閉 | 這是既定的安全設計（`chat_command_spec.md` 待決 D-1）：沒設 `AIO_INBOX=1`，外掛不取任何網站指令 | 擁有者決定開通時，CEO 送核准卡片把 `AIO_INBOX=1` 加到雲端環境變數 |
| 「Claude 在線上」不等於「會收指令」 | 對話框的「你的 Claude 在線上」看的是最近有沒有掛鉤事件；`AIO_INBOX` 沒開時一樣顯示在線上，但指令會一直排隊 | 已記給 chat.js 負責人（見第七節），這次沒改 chat.js |
| 待命時「排隊中」只閃一下 | Claude 在待命時，收件服務一收到就叫醒它取走，網站常常直接看到「已取走」或「執行中」 | 正常。收件服務的狀態紀錄（InboxUpdate）四段都有，測試以它為準 |
| 新同事最多 3 位 | 後備座位只有 3 個；第 4 種子 Agent 類型會由現有同事兼任（畫面寫「座位已滿」） | 之後若專案 Agent 很多，要加座位或改成依專案生座位 |
| 專案的 Agent 要先被派過一次才會出現在辦公室 | 外掛沒有回報「這個專案有哪些 Agent」，辦公室只能在第一次 SubagentStart 時生角色；在那之前無法點他下指令（可以先對 CEO 說「派 tester 做…」） | 建議下一版：SessionStart 事件附上 `.claude/agents/*.md` 的名稱清單（只有名稱），辦公室一接上就生好座位。要動 bridge.py 與 worker.js（有同事正在改），這次沒做 |
| 即時模式仍顯示擁有者原本的 40 位示範同事 | 他們不是這個專案的 Agent；對他們下指令，inbox.py 會告訴 Claude「名稱對不上就由 CEO 判斷」 | 跟「一個專案一間辦公室」的規劃一起處理 |

## 四、最後一輪的結果（逐項、時間、截圖）

> 時間是台北時間。截圖都存在 scratchpad（不進 repo），路徑前綴：`/tmp/claude-0/-home-user-tw-rotation/93946fe2-a0f2-5914-8682-3d7a96898e8b/scratchpad/e2e/`。接入碼一律不記。

最後一輪：2026-11-15 20:25～20:40（台北），**33 項全部通過、0 項失敗**；整輪只開一個 `claude -p`（sonnet）工作階段，這個工作階段的費用約 0.26 美元。
截圖資料夾：`/tmp/claude-0/-home-user-tw-rotation/93946fe2-a0f2-5914-8682-3d7a96898e8b/scratchpad/e2e/final/shots/`（下表只寫檔名）。

| 時間（台北） | 步驟 | 結果 | 截圖 |
|---|---|---|---|
| 20:26 | 開場：示範模式，頂列「連接我的 Claude」 | ✅ | `01_開場_示範模式.png` |
| 20:27 | Claude 沒開時對 CEO 送一則（撤回測試）→ 排隊中、提示「你的 Claude 目前沒開」 | ✅ | `02_撤回前_排隊中.png` |
| 20:27 | 按「撤回」→ 已撤回 | ✅ | `03_撤回後.png` |
| 20:28 | 點頂列 → 接入引導 | ✅ | `04_接入引導.png` |
| 20:29 | 「複製接入碼」→ 收件服務發碼、進剪貼簿、畫面只顯示 `aio_xxx…（已隱藏）` | ✅ | `05_接入碼已複製_遮罩.png` |
| 20:29 | 設定外掛、Claude 還沒開工：引導維持「等待你的 Claude 回報…」（修正 三之 1 的驗證） | ✅ | — |
| 20:29 | 開 Claude（待命）→ 16 秒後引導顯示「已接上 ✓」、2.5 秒後自動關閉 | ✅ | `06_已接上.png` |
| 20:29 | 關掉引導後接入碼從網頁記憶體清掉，改用登入身分觀看 | ✅ | — |
| 20:29 | 頂列「即時」、左上辦公室名「demo-calc」、一個開著的工作階段（CEO） | ✅ | `07_辦公室_專案與CEO.png` |
| 20:30 | 被撤回的那則一直是「已撤回」，沒被 Claude 取走 | ✅ | — |
| 20:30～20:31 | 對 CEO：「在 README.md 最後加一行今天的日期…」→ 收件服務狀態 排隊中→已取走→執行中→完成；畫面看到 已取走（20:31:07）→執行中（20:31:18）→完成（20:31:30）；README 真的多一行 `2026-11-15`；回覆「CEO 親自處理…」 | ✅ | `08`～`11_CEO_README_*.png` |
| 20:31～20:32 | 對 CEO：「請派 tester 跑 python3 -m unittest…同時派 frontend 把 h1 改成『小計算機 v2』」→ 收件服務收到 tester、frontend 各一組 SubagentStart／SubagentStop；h1 真的改了；回覆兩項都完成 | ✅ | `12`～`14_CEO_派兩位_*.png` |
| 20:32 | 辦公室為 tester、frontend 生出角色（代號就是 tester、frontend），坐進後備座位，先前那件已記在資訊卡完成清單 | ✅ | `15_新同事報到_tester_frontend.png` |
| 20:33 | 真滑鼠點 3D 的 tester → 資訊卡、對話框對象切成他 → 「對他說」 | ✅ | `16_tester_資訊卡.png` |
| 20:34 | 對 tester：「再跑一次測試，只回報通過幾個。」→ 收件匣 `to＝tester` | ✅ | `17_tester_已送出_他的對話串.png` |
| 20:35 | Claude 派的就是 tester（SubagentStart 1→2）；3D 裡 tester 拿文件走到 CEO 桌交件、回到待命，完成清單 1→2；回覆出現在 tester 的對話串 | ✅ | `18_tester_3D_delivering.png`、`20_tester_3D_交件後.png`、`21_tester_回覆_他的對話串.png` |
| 20:37～20:39 | 同上，對 frontend：「把 index.html 的 title 也改成『小計算機 v2』」→ `to＝frontend`、Claude 派 frontend、title 真的改了、3D 交件、完成清單 1→2 | ✅ | `22`～`27_frontend_*.png` |
| 20:40 | Claude 完整對話紀錄（`claude_stream.jsonl`）從頭到尾沒有出現被撤回那則的字（`SHOULD-NOT-RUN`） | ✅ | — |
| 20:40 | 收件服務收到的事件種類：SessionStart、UserPromptSubmit、PreToolUse、PostToolUse、SubagentStart、SubagentStop、Stop、PermissionRequest、InboxUpdate，共 75 筆 | ✅ | `28_全部完成.png` |
| 20:40 | 網站沒有 JavaScript 例外 | ✅ | — |

使用者專案最後的樣子：README.md 最後一行 `2026-11-15`；index.html 的 `<title>` 與 `<h1>` 都是「小計算機 v2」。

**之前幾輪抓到的東西**（同一支腳本反覆跑出來的）：
- 第 1 輪：Claude 要跑待命指令被「需要核准」擋下、工作階段直接結束（三之 4 第一列）；接入引導在 Claude 開工前就誤報（三之 1）。
- 第 2～3 輪：新同事代號 `x-tester`（三之 2，修完才跑第 3 輪就對了）；點角色的座標要用 main.js 的判定點。
- 第 4～6 輪：點過的同事交件卡住（三之 3）；用「不花 Claude 額度的事件重播」重現與驗證修正。
- 第 7 輪（上表）：全部通過。

**畫面上順便看到的（不是這次的範圍，記給負責人）**：Claude 碰到需要核准的指令時頂列會多一顆「CEO 等你核准」，1280 寬時這顆把「績效總表」擠到第二列、壓在操作提示列上（`09_CEO_README_running.png` 左上）。

## 五、還不能自動化的部分
1. **Google 登入**：本機用假會員服務代替；正式環境的「站長是誰」由會員 Worker 判斷，這段只能在線上手動驗。
2. **雲端環境的網路金鑰與設定腳本**：接入碼在正式環境是由雲端代理注入，不是寫在設定檔；這段要擁有者本人在 Claude 雲端環境設定（第八節）。
3. **擁有者真的在 claude.ai 上按「允許」**：無頭模式用「信任專案＋允許清單」代替互動核准。
4. **3D 演出速度**：這個容器是軟體繪圖、CPU 很忙（負載 20～40），一秒畫不到一格，模擬時間大約是真實的 1/15；測試把 `__world.speed` 調成 8（跟既有驗收段落一樣），只影響動畫節奏，不影響收件服務與 Claude。

## 六、怎麼重跑
```bash
bash scripts/e2e/ai_office_e2e.sh [輸出資料夾]
# 已經裝好 wrangler：WRANGLER=<路徑>/node_modules/.bin/wrangler bash scripts/e2e/ai_office_e2e.sh
# 埠被占用：E2E_PORTS=8835,8836,8837 bash scripts/e2e/ai_office_e2e.sh
```
- 檔案：`scripts/e2e/ai_office_e2e.sh`（入口）、`scripts/e2e/ai_office_e2e.py`（流程與驗收）、`scripts/e2e/fake_account.py`（假會員服務）。
- 輸出：`run.log`（逐步結果）、`results.json`、`timeline.json`（每則指令每個狀態第一次出現的時間、3D 同事的階段）、`shots/*.png`、`claude_stream.jsonl`（Claude 的完整對話紀錄，用來證明撤回的那則沒被看到）。
- 費用：一輪只開一個 `claude -p` 工作階段（4 則小指令＋3 次子 Agent），一輪 15～20 分鐘（大部分是這個容器的 3D 畫面很慢）。
- 測的是 **HEAD**（已 commit 的版本）：工作區裡別人改到一半的檔不會被打包進來。

## 七、給其他負責人的紀錄（這次沒改）
- **chat.js**（主對話框，同事改版中）：
  1. 「你的 Claude 在線上」只看最近的掛鉤事件，`AIO_INBOX` 沒開時也顯示在線上（見三之 4）。建議收件服務在 `/inbox` 回應加「最近一次有 Claude 來取指令的時間」，對話框用它判斷「會不會收」。
  2. 對話串展開時會蓋住畫面中間（1280 寬時 x 372～908、y 241～657），剛好蓋住後備座位與走去 CEO 桌的路；使用者看不到他指派的人在走。可考慮送出後自動收合，或展開時讓 3D 鏡頭往旁邊讓。
  3. 收合時對話框只靠背景輪詢（預設 15 秒）更新狀態，指令很快做完時畫面會從「已送出」直接跳到「完成」。
- **bridge.py／worker.js**：建議 SessionStart 附上專案的 Agent 名稱清單（見三之 4），辦公室才能「一接上就生好」專案的 Agent，而不是等第一次派工。

## 八、上線後在擁有者真實雲端環境怎麼驗（逐格）
> 前提：`docs/ai_office/bridge_setup.md` 的步驟 1～6 已完成（收件服務部署、接入碼存成網路金鑰、設定腳本裝好外掛）。網站上的按鈕名稱是這一版自己做的；Claude 雲端環境的畫面若跟下表不同，先截圖給 CEO 對過再按。

| 步驟 | 在哪裡 | 點哪裡／填什麼 | 做完回 CEO 什麼 |
|---|---|---|---|
| 1 | <https://liguligu-puipui.com/office/world.html>（用站長 Google 帳號登入過主站） | 看頂列標章 | 標章的字（應該是「即時・最後更新 HH:MM」或「連接我的 Claude」） |
| 2 | 同一頁 | 若是「連接我的 Claude」：點它 →「複製接入碼」→ 照 `bridge_setup.md` 步驟 4 貼進 Claude 的表單卡片（**不要貼在聊天室**） | 「貼好了」 |
| 3 | Claude 雲端環境 | 決定要不要開網站指令（`AIO_INBOX=1`，見三之 4）；同意就請 CEO 送核准卡片，在卡片上按「同意」 | 「同意了」或「先不開」 |
| 4 | <https://claude.ai/code> 開一個**新的**工作階段（選 tw-rotation 儲存庫） | 在對話框輸入：`進入 AI Office 待命`；Claude 要跑 `python3 /opt/ai-office-bridge/scripts/inbox.py wait` 時跳出核准 → 按「允許」 | Claude 回的第一句話 |
| 5 | 辦公室頁 | 下方對話框輸入：`在 docs 底下列出檔案數量，回報給我`，按 Enter | 對話框那則的狀態變化（排隊中／已取走／執行中／完成）與回覆截圖 |
| 6 | 辦公室頁 | 對話框輸入：`請派 reviewer 看一下 HANDOFF.md 最上面一段有沒有錯字，回報`，按 Enter；看 3D 裡 reviewer 是否走去 CEO 桌、回座位、做完拿文件回來 | 3D 截圖＋回覆截圖 |
| 7 | 辦公室頁 | 真滑鼠點 3D 裡的 reviewer → 資訊卡「對他說」→ 輸入：`再確認一次，只回一句`，Enter | 回覆是不是出現在 reviewer 的對話串 |
| 8 | 辦公室頁 | 送一則 `測試撤回`，在它還是「排隊中」時按「撤回」（Claude 待命中通常一秒內就取走；要測撤回請先在 Claude 那邊按停止或等待命結束） | 狀態是否變「已撤回」、Claude 有沒有做 |

## 九、改了哪些檔
| 檔案 | 改了什麼 |
|---|---|
| `site/office/world/js/live.js` | 三之 1（已接上判斷）、三之 2（新同事代號＝子 Agent 類型名） |
| `site/office/world/js/attention.js` | 三之 3（走去領任務／交件的人被選取時照走） |
| `scripts/uitest_sections/20261114_office_live.py` | 代號 `x-general-purpose` → `general-purpose` |
| `scripts/e2e/ai_office_e2e.sh`、`ai_office_e2e.py`、`fake_account.py` | 新增：可重跑的端到端驗證 |
| `docs/ai_office/e2e_report_1115.md` | 這份報告 |

收件服務（worker.js）與外掛（bridge.py、inbox.py、install_hooks.py）**這次沒有改**（它們的既有測試因此不必重跑；工作區裡另有同事改到一半的版本，本次測的是 HEAD）。
