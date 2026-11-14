# AI Office 實際串接：設定步驟（第一版，只接擁有者本人）

> 2026-11-14 建立。擁有者原話：「目前看起來還是 Demo 版本，我想實際串接我的專案」。
> 依據：`docs/ai_office/bridge_test_report.md`（實測報告）、`docs/ai_office/account_model_eval.md`（方案 a，這一版先只做擁有者本人，Google 登入給多使用者留到下一版）。
> **標示**：「待截圖確認」＝我沒有親眼看到那個畫面上的按鈕或欄位名稱，照之前的規矩，CEO 要先請 Andy 截圖、逐格比對之後才能給他確切的點法。辦公室頁上的按鈕是這一版自己做的，名稱是確定的。

---

## 一、整體長什麼樣子（先看這段）

```
Andy 的 Claude（雲端工作階段）
   │ 掛鉤（外掛 tools/ai_office_bridge/plugin/ai-office-bridge）：只送類別、代號、短摘要；背景送出、逾時 2 秒、錯誤全吞
   ▼  POST /v1/events（接入碼由雲端代理注入，腳本手上沒有金鑰）
AI Office 收件端（Cloudflare Worker：tw-ai-office-bridge，Durable Object 存事件）
   ▲  GET /v1/office/main/state（每 15 秒；分頁在背景時暫停）
辦公室頁 https://liguligu-puipui.com/office/world.html（即時模式）
```

| 元件 | 位置 | 誰部署 |
|---|---|---|
| 收件端 Worker | `workers/ai-office-bridge/` | 推上 main 時 `.github/workflows/deploy-ai-office-bridge.yml` 自動部署（用既有的 `CLOUDFLARE_API_TOKEN`、`CLOUDFLARE_ACCOUNT_ID`，**不需要新金鑰**） |
| 外掛（掛鉤腳本） | `tools/ai_office_bridge/plugin/ai-office-bridge/` | 雲端：由雲端環境的「設定腳本」裝；本機：外掛指令或 `install_hooks.py` |
| 辦公室即時模式 | `site/office/world/js/live.js` | 跟著網站一起部署（Pages） |

**接入碼怎麼給 Andy（選擇與理由）**
- 收件端**只存接入碼的雜湊**，原碼不進 repo、不進 Actions 紀錄、不經過任何人手。
- 取得方式：Andy 用**網站原本的 Google 登入（管理者帳號）**打開辦公室頁，按「產生接入碼」→ 收件端透過服務綁定問會員 Worker（`tw-account`）「這個人是不是管理者」→ 是才產生一組，**只顯示這一次**。
- 為什麼不選「部署流程隨機產生、寫進 Worker Secret、在 Actions 摘要提示」：摘要一遮罩 Andy 就看不到碼；不遮罩就等於把碼寫進公開 repo 的執行紀錄（這是 public repo，任何人都看得到 Actions 紀錄）。
- 為什麼不選 GitHub 帳號領取：要另外做一套 GitHub 登入；網站已經有 Google 登入與管理者名單（`ACCOUNT_ADMIN_EMAILS`），直接沿用最省事，也跟 `account_model_eval.md` 方案 a 的「Google 登入＋一次性接入」同一條路。
- 弄丟或外洩：再按「產生新的接入碼」，舊的立刻失效。

---

## 二、誰做什麼（總表）

| # | 步驟 | 誰做 | Andy 要不要動手 | 擋不擋其他事 |
|---|---|---|---|---|
| 1 | 把這一版推上 main（收件端自動部署、辦公室頁更新） | CEO | 不用 | — |
| 2 | 確認部署成功、記下收件端網址 | CEO | 不用 | 擋 3～6 |
| 3 | 在辦公室頁按「產生接入碼」，複製那一組碼 | **Andy 本人** | 要（登入＋按兩個鈕） | 擋 4 |
| 4 | 把接入碼存成雲端環境的「網路金鑰」 | CEO 送出表單卡片，**Andy 本人**在卡片上貼碼 | 要（貼一次） | 擋 6 |
| 5 | 雲端環境的設定腳本（安裝掛鉤）＋收件端網址 | CEO 提出，**Andy 在核准卡片上按同意** | 要（按同意） | 擋 6 |
| 6 | 開一個**新的**雲端工作階段，隨便交代一件會派子 Agent 的小事 | **Andy 本人** | 要 | — |
| 7 | 看辦公室頁的標章變成「即時・最後更新 HH:MM」、同事動起來 | Andy 看；CEO 同時查收件端有沒有收到 | 看一眼 | — |

---

## 三、CEO 代做的部分

### 步驟 1：推上 main
- 這一版的檔案見回報清單。推上去後兩件事會自己發生：
  - `部署 Worker（AI Office 收件端）` 工作流：先跑收件端測試與外掛測試，紅了不部署；缺 Cloudflare 金鑰就跳過並在摘要寫待辦（不紅燈）。
  - 網站 Pages 部署：辦公室頁多了即時模式（沒有接入碼時照舊是示範，頂列多一顆「連接我的 Claude」）。
- 推完照規矩跑 `python scripts/deploy_wait.py --branch main`，兩行 ✅ 才算網站部署好。

### 步驟 2：確認收件端部署成功
- 打開工作流頁：<https://github.com/MiaoZiKe/tw-rotation/actions/workflows/deploy-ai-office-bridge.yml>，點最新一次，看「Summary」：
  - 「收件端網址」那一行就是外掛要用的 `AIO_URL`（預期長得像 `https://tw-ai-office-bridge.<子網域>.workers.dev`）。
  - 「健康檢查」應該是 `{"ok":true,...,"claimed":false}`。
  - 如果出現「⚠ 會員 Worker（tw-account）還沒部署」：步驟 3 的「產生接入碼」會失敗，要先處理會員 Worker。
- 辦公室頁會自己從會員 API 網址推出收件端網址（把 `tw-account.` 換成 `tw-ai-office-bridge.`）。如果會員 API 用的是自訂網域、推不出來，Andy 在步驟 3 會看到「還不知道收件端網址」，那時再請他在「進階」貼上步驟 2 的網址。

### 步驟 4：網路金鑰（CEO 送表單卡片）
- CEO 用 `request_credential` 送出表單卡片：
  - 主機：步驟 2 網址的主機名稱（例如 `tw-ai-office-bridge.xxxx.workers.dev`）
  - 標頭：`Authorization`，前綴 `Bearer`
  - 說明：「AI Office 收件端：讓雲端的掛鉤把事件送到你的辦公室」
- 存了金鑰等於同時放行這個主機，**不用另外加允許清單**。
- 金鑰的值**只能由 Andy 在卡片上貼**，不可以貼在聊天室。

### 步驟 5：設定腳本（CEO 提出、Andy 按同意）
- 設定腳本只在「全新建立的容器」執行，所以要到步驟 6 開新工作階段才會生效。
- 實測報告第九節：雲端主工作階段會不會讀使用者層級的掛鉤**還沒被證實**（V1）。所以下面先試候選乙（寫進使用者層級設定檔），沒效再試候選甲（外掛指令），都沒效就退到候選丙（儲存庫自己的 `.claude/settings.json`，要 Andy 另外同意改 repo 設定）。
- 候選乙的腳本內容（CEO 提出前要先在自己的容器裡逐行跑過、看到每一步成功；`<收件端網址>` 換成步驟 2 的網址）：

```bash
# AI Office：把掛鉤裝到固定位置，所有儲存庫的工作階段共用
set -e
D=/opt/ai-office-bridge
if [ -d tw-rotation/tools/ai_office_bridge/plugin/ai-office-bridge ]; then
  rm -rf "$D" && cp -r tw-rotation/tools/ai_office_bridge/plugin/ai-office-bridge "$D"
fi
if [ -f "$D/scripts/install_hooks.py" ]; then
  python3 "$D/scripts/install_hooks.py" --settings "$HOME/.claude/settings.json"
  mkdir -p "$HOME/.ai-office"
  printf '{"AIO_URL": "%s"}\n' "<收件端網址>" > "$HOME/.ai-office/config.json"
fi
```

  - 沒有 tw-rotation 儲存庫的工作階段：這版腳本會略過（不會讓工作階段開不起來）。之後若要所有專案都接，再加「從公開儲存庫下載外掛」那一段（需要 `raw.githubusercontent.com` 在允許清單）。
  - 腳本**不含任何金鑰**：接入碼由步驟 4 的網路金鑰在代理端注入，腳本與外掛都不持有。
- 同一張核准卡片也可以順便設環境變數 `AIO_URL`（非機密，明文可）；有設定檔就不必，二擇一。

### 步驟 7：驗證
- CEO 在自己的工作階段讀收件端（用 Andy 給的碼不行——碼不進聊天室；改用辦公室頁看，或請 Andy 截圖辦公室頁）。
- 應該看到：標章「即時・最後更新 HH:MM」、說明框裡「專案：tw-rotation」、工作階段「CEO 工作中・雲端」、派出的子 Agent 走到 CEO 桌前領任務、回座位、做完拿文件回來。
- 沒收到（標章一直是「即時・尚未收到回報」）：照實驗報告第九節 9.3 步驟 7，把設定腳本換成候選甲，再請 Andy 開新工作階段。

---

## 四、Andy 本人做的部分（逐格）

### 步驟 3：產生接入碼（約 1 分鐘）
1. 打開網站首頁 <https://liguligu-puipui.com/>，確認右上角已經用 Google 登入（**要用管理者那個帳號**）。沒登入就按右上角的登入鈕登入。
2. 打開辦公室頁 <https://liguligu-puipui.com/office/world.html>。
3. 點頂列的「**連接我的 Claude**」（灰色小圓點那顆，在「電力」左邊）。
4. 在跳出來的框裡按「**產生接入碼**」。
5. 框的最上面會出現「你的接入碼（只顯示這一次）」和一串 `aio_` 開頭的字，按旁邊的「**複製**」。
   - 這台電腦的辦公室頁會自動記住這組碼、切成即時模式（標章變成「即時・尚未收到回報」是正常的，還沒開始送事件）。
   - 其他欄位（「已經有接入碼」、「進階」）都**不用動**。
6. 回聊天室跟 CEO 說「接入碼拿到了」（**不要把碼貼在聊天室**）。CEO 會送一張表單卡片給你（步驟 4）。

### 步驟 4：在表單卡片上貼接入碼
- 卡片長相：待截圖確認（CEO 送出後請你截圖給他比對）。
- 值那一格貼上剛剛複製的接入碼，其他格照卡片預填的不用動，按儲存。

### 步驟 5：核准設定腳本
- CEO 會送一張核准卡片，上面完整列出腳本內容。看過沒問題就按同意。卡片上的按鈕名稱：待截圖確認。

### 步驟 6：開新的雲端工作階段
- 設定腳本只在全新的容器執行，所以要**開一個新的工作階段**（不是在現在這個繼續）。開法與按鈕位置：待截圖確認。
- 開好之後隨便交代一件會派子 Agent 的小事，例如「派一位子 Agent 列出 docs 資料夾有哪些檔案，回報檔名數量」。
- 另開一個分頁打開辦公室頁，15 秒內應該看到同事動起來。

### 其他裝置怎麼看
- 手機或另一台電腦：先在網站首頁用同一個管理者帳號登入，再打開辦公室頁 → 點「連接我的 Claude」→ 按「**直接用登入身分觀看**」。不用再產生碼（再產生會讓舊碼失效、雲端那邊要重貼）。

### 想換回示範畫面
- 點標章 →「**展示模式**」：畫面回到示範資料、停止讀取；再點標章 →「**回到即時模式**」。
- 「中斷連接」會把這台裝置記住的碼清掉。

---

## 五、本機（自己電腦上的 Claude Code）安裝方式（選配）

Andy 目前用雲端環境，這段給之後有本機 Claude Code 的情況。實測報告第三節：外掛裝在使用者層級，所有專案都會觸發。

1. 把 `tools/ai_office_bridge/plugin/` 整個資料夾放到電腦上（下載 repo 或複製這個資料夾）。
2. 在終端機執行（`<資料夾>` 換成實際路徑）：
   ```
   claude plugin marketplace add <資料夾>/plugin
   claude plugin install ai-office-bridge@ai-office-local --scope user
   ```
3. 建立 `~/.ai-office/config.json`（Windows 是 `%USERPROFILE%\.ai-office\config.json`）：
   ```json
   { "AIO_URL": "https://tw-ai-office-bridge.<子網域>.workers.dev", "AIO_TOKEN": "aio_…（步驟 3 的接入碼）" }
   ```
   這個檔只在自己電腦上，**不要放進任何專案資料夾**。
4. 不想用外掛系統也可以：`python3 <資料夾>/plugin/ai-office-bridge/scripts/install_hooks.py --settings ~/.claude/settings.json`（重跑不會重複；`--remove` 移除，只拿掉自己加的）。

| 設定 | 用途 | 預設 |
|---|---|---|
| `AIO_URL` | 收件端網址 | 沒有就什麼都不送 |
| `AIO_TOKEN` | 接入碼（本機才需要；雲端由代理注入，不要設） | — |
| `AIO_SUMMARY` | `0`＝連派工短說明與回覆摘要都不送，只送類別與代號 | `1` |
| `AIO_DISABLE` | `1`＝完全停用 | — |

---

## 六、送出去的到底有什麼（隱私）

| 會送 | 不會送 |
|---|---|
| 事件種類、時間、工作階段／子 Agent 的隨機代號 | 你打的指令全文、派工全文 |
| 專案資料夾名＋完整路徑的雜湊前 16 碼 | 完整路徑、檔名、指令內容、工具輸入輸出、程式碼 |
| 子 Agent 類型、工具「類別」（讀檔／寫檔／查資料／跑測試／部署／等部署／其他） | 網址、信箱、疑似金鑰的長字串（文字裡出現會被遮成〔網址〕〔信箱〕〔遮蔽〕） |
| 派工短說明（80 字內）、回覆第一行摘要（120 字內）——可用 `AIO_SUMMARY=0` 關掉 | 回覆全文 |
| Token 數字（從對話紀錄檔加總，只讀數字） | 對話紀錄檔內容 |

收件端再過濾一次（只收白名單欄位、文字再遮一次），保留最近 5,000 筆事件、工作階段與子 Agent 紀錄 14 天。擁有者在辦公室頁「進階 → 刪除所有紀錄」可以一鍵清空。

---

## 七、這一版做不到、要知道的

1. **雲端「裝一次全部生效」還沒被證實**（實測報告 V1）：要靠步驟 5～7 實際試。
2. **額度（電力）多半顯示「未提供」**：掛鉤事件沒有額度欄位；只有被限流時（StopFailure 帶限流類型）會演「大家去睡覺」，恢復時間未提供。
3. **網站對話（從辦公室傳訊息給 Claude）這一版沒有做**：實驗用的收件匣與閒置喚醒腳本已從外掛移除，降低被當成指令通道的風險。
4. **等第（S～F）在即時模式一律「未評等」**：計分規則（`rewards_design.md`）還沒接上真資料，不拿示範等第充數。
5. 子 Agent 超過 3 小時沒有任何消息，收件端會標成「狀態不明」，辦公室不再把他當成還在做。
