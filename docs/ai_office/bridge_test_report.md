# AI Office 接入可行性實測報告

> 日期：2026-11-13｜性質：實測報告。沒有 commit、沒有 push、沒有改 `.claude/`、`CLAUDE.md` 或使用者層級設定。
> 實測環境：Claude Code **2.1.323**，跑在**一個 Claude Code 網頁版的雲端容器裡**（`CLAUDE_CODE_REMOTE=true`），用無頭模式 `claude -p` 與假終端機裡的互動模式各開獨立的測試工作階段，模型指定 haiku。
> 工具與可重跑腳本：`tools/ai_office_bridge/`（見該資料夾 README）。原始紀錄：暫存區 `bridge_test/logs/`（不進 repo）。去識別後的真實 JSON：`tools/ai_office_bridge/samples/hook_payloads.sanitized.json`。
>
> **標示**：【實測】＝我在這個容器親手跑出來的；【程式內文字】＝從 2.1.323 執行檔裡讀到的設定說明文字（比網路摘要可靠，但不是行為證明）；【文件摘要】＝WebSearch 摘要（沒讀到全文）；【未測】＝這個環境做不到。
> ⚠ 最重要的限制：我測的是「雲端容器裡另外開的 CLI」，**不是網頁版那個主工作階段本身**。主工作階段讀不讀使用者層級設定、讀不讀設定腳本寫的東西，我沒辦法在不動使用者設定的前提下驗證，全部列在第十節請擁有者配合。

---

## 〇、先看結論

1. **事件上報（方案 a）成立。** 掛鉤拿得到工作階段代號、工作目錄、對話紀錄檔路徑、子 Agent 類型與代號、派工說明；外掛裝在使用者層級後，兩個**沒有任何設定**的專案都自動觸發，含 SubagentStart／SubagentStop（前景、背景子 Agent 都有）。評估文件擔心的「外掛層級子 Agent 掛鉤不觸發」在 2.1.323 沒有重現。
2. **掛鉤資料裡沒有時間、也沒有 Token。** 時間由腳本自己補；Token 要從對話紀錄檔加總（實測可行，但子 Agent 的要等回合結束再算）。
3. **掛鉤可以直接用 HTTP 送**（不必 curl），失敗與逾時都不會中斷工作，但**同步掛鉤會讓使用者等到逾時為止**，而且 SessionStart 不支援 HTTP 掛鉤。建議用「一支腳本、逾時 2 秒」。
4. **用量額度拿得到一部分**：狀態列腳本收到的資料裡有 `rate_limits`（已用百分比與恢復時間）；無頭串流輸出有 `rate_limit_event`。**掛鉤事件本身沒有**。
5. **網站 → 工作階段（對話）有合規做法，而且實測通了三條**：Stop 掛鉤回 `decision: block`（回合結束時領訊息）、`asyncRewake` 背景等待（**閒置時也能叫醒**，推送後約 3～8 秒看到回覆）、無頭 `claude -p --resume`。全部都不需要把使用者的登入權杖交給網站。
6. **雲端版「裝一次全專案生效」還沒被證實**，而且文件摘要說「只在使用者設定啟用的外掛不會帶到雲端工作階段」。目前可行的候選是「預設環境的設定腳本＋網路允許清單＋網路金鑰」，需要擁有者在他的雲端環境做一次驗證（第九、十節）。
7. 這個容器的代理實測：不在允許清單的主機直接被擋；網路金鑰可以限定到「主機＋路徑」，由代理注入標頭。所以雲端版**不需要把接入碼放進容器**。

---

## 一、七題（加一題）結論總表

| # | 題目 | 結論 | 依據 | 把握 |
|---|---|---|---|---|
| 1 | 掛鉤事件與欄位 | 33 種事件；工作階段代號、工作目錄、紀錄檔路徑都有；**沒有時間、沒有 Token** | 【實測】10 種事件的原始 JSON；【程式內文字】完整事件名單 | 高 |
| 2 | 外掛帶掛鉤、裝一次全專案生效 | **本機成立**；子 Agent 掛鉤有觸發 | 【實測】獨立設定資料夾裡 `--scope user` 安裝，兩個專案都觸發 | 高（本機目錄型市集）；GitHub 型市集【未測】 |
| 3 | HTTP 直送、逾時與失敗 | 可以直送；失敗／逾時不中斷，但同步等待最長＝逾時秒數；SessionStart 不支援 HTTP | 【實測】正常、很慢、連不上、回 500、腳本逾時、腳本不存在 | 高 |
| 4 | 雲端版環境 | 容器內程序能照代理規則連外、金鑰由代理注入、可限定路徑；**設定腳本能否讓主工作階段載入外掛或使用者層級掛鉤：未證實** | 【實測】代理行為、環境現況；【文件摘要】其餘 | 網路與金鑰：高；設定腳本：低 |
| 5 | 用量額度 | 狀態列資料與串流輸出拿得到；掛鉤事件沒有 | 【實測】兩處的真實資料 | 中高（五小時窗這次沒出現） |
| 6 | 網站 → 工作階段 | a、b、c、無頭續接、閒置喚醒都實測通；官方遠端控制與 Channels 只有文件 | 見第七節逐項 | a／e：高（本機）；雲端網頁版主工作階段【未測】 |
| 7 | 隱私 | 預設只送白名單欄位；`bridge.py` 已照做 | 【實測】收件端實際收到的內容 | 高 |
| 新 | 只做一次帳號層級安裝 | 本機：成立。雲端：靠預設環境做到「每個環境一次」，待擁有者驗證 | 第九節 | 本機高／雲端低 |

---

## 二、第 1 題：掛鉤事件與欄位

**【程式內文字】2.1.323 的完整事件名單（33 種）**
PreToolUse、PostToolUse、PostToolUseFailure、PostToolBatch、Notification、UserPromptSubmit、UserPromptExpansion、SessionStart、SessionEnd、Stop、StopFailure、SubagentStart、SubagentStop、PreCompact、PostCompact、PreModelSwitch、PostModelSwitch、PermissionRequest、PermissionDenied、Setup、TeammateIdle、TaskCreated、TaskCompleted、Elicitation、ElicitationResult、ConfigChange、WorktreeCreate、WorktreeRemove、InstructionsLoaded、CwdChanged、FileChanged、DirectoryAdded、MessageDisplay。

**【實測】每個事件都有的共同欄位**：`session_id`、`transcript_path`、`cwd`、`scratchpad_dir`、`hook_event_name`；第一句話之後多一個 `prompt_id`（同一輪對話的代號）。

**【實測】各事件多出來的欄位**（一個「派子 Agent 列檔案」的任務實際收到的）

| 事件 | 多出來的欄位 | 備註 |
|---|---|---|
| SessionStart | `source`（實測值 `startup`） | 掛鉤環境變數另有 `CLAUDE_PROJECT_DIR`、`CLAUDE_ENV_FILE`、`CLAUDE_CODE_REMOTE` |
| UserPromptSubmit | `prompt`（**全文**）、`permission_mode` | ⚠ 背景子 Agent 跑完時，系統會送一則 `<task-notification>` 也觸發這個事件，不是真人輸入 |
| PreToolUse（工具 `Agent`） | `tool_name`、`tool_input`｛`description`、`prompt`（派工全文）、`subagent_type`｝、`tool_use_id`、`permission_mode`、`effort` | 這就是「派出子 Agent 之前」 |
| SubagentStart | `agent_id`、`agent_type` | 沒有說明文字；要靠前一筆 PreToolUse 對上 |
| PostToolUse（工具 `Agent`） | 再加 `tool_response`、`duration_ms` | **前景**：`status: completed`、`totalTokens`、`totalDurationMs`、`totalToolUseCount`、`usage`、`resolvedModel`。**背景**：`status: async_launched`、`agentId`，沒有 Token |
| 子 Agent 內部的工具事件 | 一樣的欄位再加 `agent_id`、`agent_type` | 可以知道子 Agent 正在用什麼工具 |
| SubagentStop | `agent_id`、`agent_type`、`agent_transcript_path`、`last_assistant_message`、`stop_hook_active`、`background_tasks`、`session_crons` | |
| Stop | `last_assistant_message`、`stop_hook_active`、`background_tasks`、`session_crons`、`permission_mode`、`effort` | 回覆全文直接在欄位裡，不必自己讀紀錄檔 |
| SessionEnd | `reason`（實測值 `other`） | |
| MessageDisplay | `turn_id`、`message_id`、`index`、`final`、`delta`（顯示的文字） | |
| PostToolBatch | `tool_calls`（一批工具呼叫與結果） | |

**問到的五樣東西**

| 要找的 | 有沒有 | 怎麼拿 |
|---|---|---|
| 工作階段代號 | 有 | `session_id` |
| 工作目錄／專案識別 | 有 | `cwd`（完整路徑）。git 分支不在掛鉤裡，但紀錄檔每一行有 `gitBranch` |
| 對話紀錄檔路徑 | 有 | `transcript_path`；子 Agent 的在 `agent_transcript_path`，實際位置是「主紀錄檔去掉 `.jsonl`／`subagents/agent-<代號>.jsonl`」，旁邊還有 `.meta.json`（含類型、說明） |
| Token 用量 | **掛鉤裡沒有**（只有前景子 Agent 的 PostToolUse 有 `totalTokens`） | 紀錄檔每一則助理訊息有 `message.usage`（input／output／cache）與 `timestamp`；加總即可。主紀錄檔結尾另有一筆 `cost-state`（總花費、總時間） |
| 時間 | **沒有** | 腳本自己補現在時間；紀錄檔每行有 `timestamp` |

**【實測】兩個會影響設計的現象**
1. **SubagentStop 當下，子 Agent 的最後一則訊息還沒寫進紀錄檔**：那一刻加總只算到 1 次請求（輸出 75），回合結束時重算是 2 次請求（輸出 169～214）。所以 Token 要在 Stop／SessionEnd 再整批算一次（`bridge.py` 已這樣做）。
2. **事件順序會因前景／背景而不同**：背景子 Agent 時，主工作階段的 Stop 可能比 SubagentStop 早到（實測 `background_tasks` 還有 1 個在跑）。網站不能假設「Stop＝大家都下班」。

沒觸發到、所以沒有實測欄位的事件：Notification、StopFailure、PreCompact、PermissionRequest 等 23 種（這個簡短任務不會發生）。

---

## 三、第 2 題：外掛帶掛鉤、裝一次全專案生效

**【實測】做法**：把 `tools/ai_office_bridge/plugin/` 當成本機市集，在**獨立的設定資料夾**（`CLAUDE_CONFIG_DIR` 指到暫存區，不碰 `~/.claude`）執行：

```
claude plugin marketplace add <市集資料夾>
claude plugin install ai-office-bridge@ai-office-local --scope user
```

結果：設定檔出現 `extraKnownMarketplaces` 與 `enabledPlugins`；外掛被複製到 `plugins/cache/`。接著在兩個**完全沒有 `.claude` 資料夾**的專案各跑一次派子 Agent 的任務：

| 專案 | 觸發的外掛掛鉤 |
|---|---|
| project2 | SessionStart、UserPromptSubmit、PreToolUse(Agent)、SubagentStart、PostToolUse(Agent)、Stop、SubagentStop、UserPromptSubmit（完成通知）、Stop、SessionEnd |
| project3 | 同上 10 筆 |

另外用 `--plugin-dir`（單次載入）跑前景子 Agent，SubagentStart／SubagentStop 也都有。兩種安裝方式都是非互動指令，可以寫進腳本。

**結論**：本機「裝一次，所有專案生效」成立；外掛層級的子 Agent 掛鉤在 2.1.323 會觸發。
**保留**：①我測的是**本機目錄型**市集，GitHub 型市集沒測（推不出去）。②網路上仍有人回報舊版（2.1.62、2.1.220）外掛的子 Agent 掛鉤不觸發【文件摘要，未確認修復版號】，所以接入頁要寫最低版本，並做「自我檢查」（裝完第一次回報就亮綠燈）。③VS Code 擴充套件、桌面版沒測。

---

## 四、第 3 題：HTTP 直送、逾時與失敗

**【實測】`type: "http"` 掛鉤可用**：Claude Code 直接 POST 掛鉤 JSON（`Content-Type: application/json`），`headers` 的值可以引用環境變數（要列在 `allowedEnvVars`），收件端確實收到 `X-AIO-Token`。

| 情況 | 實測結果 |
|---|---|
| 收件端正常 | 幾毫秒內完成 |
| 收件端 20 秒才回、掛鉤 `timeout: 2` | 工具呼叫**被拖住 2.0 秒**後照常繼續（記錄：`Slow PreToolUse hooks: 2009ms`） |
| 連不上（連線被拒） | 立刻失敗，照常繼續 |
| 回 500 | 照常繼續 |
| SessionStart 掛 HTTP | **被跳過**：`HTTP hooks are not supported for SessionStart`（程式內名單：SessionStart、Setup、CwdChanged、FileChanged） |
| 腳本掛鉤：睡 30 秒、`timeout: 3` | 3.0 秒後被砍，照常繼續 |
| 腳本掛鉤：exit 1、指令不存在（127） | 照常繼續，任務正常完成 |
| 腳本掛鉤 `async: true`（睡 6 秒） | 18 毫秒就放到背景，完全不拖慢 |

**結論與建議**：不會卡死，但**同步掛鉤最壞會讓每個事件多等「逾時秒數」**。建議：
- 用**一支腳本**（因為 SessionStart 不能用 HTTP、而且要做去識別與 Token 加總），腳本內連線逾時 2 秒、全部錯誤吞掉；
- 純上報的事件加 `async: true`（完全不拖慢）；只有要回傳決定的 Stop 保持同步；
- 收件端連續失敗就在本機記一個「暫停 5 分鐘」的旗標，避免網站掛掉時每個事件都等 2 秒。

HTTP 掛鉤未設定 `timeout` 時的預設值：沒查到【未確認】，所以一律自己寫。程式內還有 `allowedHttpHookUrls` 這個管理設定（企業可限制 HTTP 掛鉤能送去哪），企業帳號的使用者可能被擋【程式內文字，未測】。

---

## 五、第 5 題：用量額度

| 來源 | 拿得到什麼 | 依據 |
|---|---|---|
| 掛鉤事件 | **沒有**任何額度欄位 | 【實測】收到的 10 種事件都沒有 |
| 狀態列腳本（`statusLine`）收到的 JSON | `rate_limits`：每個時間窗有 `used_percentage`、`resets_at`；另有 `cost`（總花費、總時間）、`context_window`（已用百分比）、`model` | 【實測】互動模式下收到 `rate_limits.seven_day`。**這次沒有 `five_hour`**；文件摘要說各時間窗可能各自缺席、訂閱帳號才有 |
| 無頭串流輸出（`--output-format stream-json`） | `rate_limit_event`：`status`（allowed／allowed_warning／rejected）、`resetsAt`、`rateLimitType`、各時間窗 `utilization` | 【實測】收到一筆 |
| 對話紀錄檔 | 每則訊息的 Token 與花費合計；**沒有**「剩多少額度」 | 【實測】 |
| StopFailure 事件 | 可能帶被限流的錯誤 | 【未測】沒觸發到 |

**結論**：要顯示「剩餘額度／何時恢復」，本機互動模式可以由外掛附一支狀態列腳本，把 `rate_limits` 存到本機檔，掛鉤上報時順便帶上。限制：①狀態列是使用者自己的設定欄位，他如果已經有自訂狀態列就要改成「包一層」，不能硬蓋；②無頭與雲端網頁版有沒有狀態列資料【未測】；③「已被限流」的即時通知，掛鉤這條路目前沒有實測到。

---

## 六、第 4 題：雲端版環境

**【實測】這個雲端容器的現況**
- 環境「Default」：網路是「受限」等級，有允許主機清單、允許套件庫與 MCP 主機；**沒有設定腳本**；有 4 筆網路金鑰（主機＋標頭名稱，值看不到）。
- 對外連線全部經過容器內的代理。不在清單的主機：`CONNECT tunnel failed, response 403`。有網路金鑰的主機：通道會開，但代理會**解開連線逐一檢查路徑**——我對擁有者自己的 Worker 打一個不存在的路徑，代理回 `request blocked … allows the host but not path`。也就是金鑰與放行可以精確到「主機＋路徑」。
- `curl` 與 Python 的 `urllib`（`bridge.py` 用的方式）都自動走代理並信任代理的憑證，不需要額外設定。
- 雲端工作階段本身就是靠一份設定檔裡的掛鉤在運作（SessionStart、Stop 各一筆腳本掛鉤）→ **雲端版會執行設定檔裡的掛鉤**是確定的。
- 容器裡沒有 `~/.claude/settings.json`；外掛資料夾存在但內容由平台同步。

**【文件／工具說明】**
- 設定腳本：以 root 執行、在複製完儲存庫之後、Claude 啟動之前；每次「全新建立容器」才跑，續接不跑；**讀不到環境變數與金鑰**；失敗會讓工作階段開不起來。
- 網路金鑰：存在環境上，由代理在送出時注入標頭；存了金鑰等於放行該主機；工作階段看不到值。
- 環境變數是明文儲存，不該放金鑰。
- 文件摘要：「只在使用者設定啟用的外掛，不會帶到雲端工作階段」；儲存庫自己的 `.claude/settings.json` 掛鉤會帶到。另有一則未證實的回報說「用設定腳本把掛鉤寫進 `~/.claude/settings.json` 會生效」。

**結論**

| 子題 | 結論 | 把握 |
|---|---|---|
| 掛鉤送得出去嗎 | 只要收件主機放行就送得出去（容器內任何程序都受同一套代理規則） | 高（規則實測；沒有實際打到我們的收件端） |
| 金鑰怎麼注入 | 用「網路金鑰」綁收件主機與路徑，代理注入 `Authorization`；腳本不必持有接入碼 | 高 |
| 設定腳本能不能安裝外掛 | 指令本身是非互動的、在這個容器跑得起來；**但主工作階段會不會載入它裝的東西，沒有證據** | 低 |
| 設定腳本寫使用者層級設定有沒有效 | 只有一則未證實回報 | 低 |

---

## 七、第 6 題：網站把訊息送進正在跑的工作階段

| 做法 | 結果 | 依據 | 延遲 | 限制 |
|---|---|---|---|---|
| **a. Stop 掛鉤領訊息** | **通** | 【實測】腳本版與 HTTP 版都成功：Claude 回完「收到」後，掛鉤回 `{"decision":"block","reason":"…訊息…"}`，Claude 收到一則 `Stop hook feedback: …` 並回答 391；第二次 Stop 的 `stop_hook_active` 為 true | 回合結束當下，1 秒內 | 只在「回合結束那一刻」有效；畫面會出現一行「Stop hook error occurred」字樣（實際不是錯誤，是內建的顯示方式）；訊息是以「掛鉤回饋」身分進來，不是真正的使用者訊息 |
| **b. UserPromptSubmit／SessionStart 附加內容** | **通** | 【實測】輸出 `hookSpecificOutput.additionalContext`，Claude 兩個暗號都讀到並說得出來源 | 下一次使用者送出時 | 只能「搭便車」，不能主動發起；適合帶「網站上有 N 則留言」這種提示 |
| **c. 自建 MCP 收件匣工具** | **通** | 【實測】`get_pending_messages`＋`send_reply` 兩個工具，Claude 讀到訊息、算出 42、送回 | 模型呼叫時 | 要模型主動呼叫（得靠提示或掛鉤提醒）；每次呼叫吃使用者的回合與 Token（實測多 3 個回合） |
| **d-1. 無頭續接 `claude -p --resume <工作階段代號>`** | **通** | 【實測】同一個代號續接成功，記得前文，掛鉤照常觸發 | 啟動約 5～10 秒＋模型時間 | 需要使用者電腦上有一支常駐小程式來收網站訊息並執行指令；同一個工作階段若正開在互動畫面，兩邊同時寫入的後果【未測】，應只用在已關閉的工作階段 |
| **d-2. 串流輸入（`--input-format stream-json`）** | **通** | 【實測】程序開著，第二則訊息從標準輸入送進去，正常回覆 | 即時 | 等於由常駐小程式代管一個工作階段，使用者看不到互動畫面 |
| **d-3. 官方遠端控制（Remote Control）** | 只查到文件 | 【文件摘要】使用者可從 claude.ai 或手機 App 對本機工作階段說話 | — | 這是 Anthropic 自己的畫面；我們的網站要驅動它就得拿使用者的登入權杖 → **不可用**。可以做的是在辦公室裡放一個「到官方畫面繼續聊」的連結 |
| **d-4. 官方 Channels** | 只查到文件 | 【文件摘要】通道是一個本機 MCP 伺服器，可把外部訊息推進工作階段；研究預覽階段，自訂通道不在核可名單，只能用開發旗標本機測試；【程式內文字】2.1.323 內有相關字串 | — | 最正規的長期路線，但現在不能發給一般使用者；列為觀察項 |
| **d-5. 排程喚醒** | 只查到工具說明 | 雲端工作階段有排程工具，但那是「Claude 自己設鬧鐘」，不是外部網站能呼叫的 | 最短一小時級 | 不適合對話 |
| **e. 閒置時叫醒** | **通（`asyncRewake`）** | 【實測】Stop 掛鉤加 `asyncRewake: true`，腳本在背景每秒查收件匣；有訊息就把內容寫到標準錯誤並以 exit 2 結束 → 閒置中的模型被叫醒並回答。無頭串流模式：回合結束 15 秒後推訊息，約 7.5 秒後出現回覆。**互動式終端機：推送後約 2.7 秒出現回覆** | 輪詢 1 秒＋模型時間，實測 3～8 秒 | 欄位說明來自程式內文字；網路上有舊版回報它會擋住啟動【文件摘要，未確認】。等待時間受掛鉤 `timeout` 限制（我只測到 90 秒，更長的上限【未測】）；工作階段程序關掉就叫不醒；使用者同時打字時可能出現兩支等待腳本，正式版要加鎖；**雲端網頁版主工作階段【未測】** |

**回覆怎麼送回網站**：Stop 事件直接帶 `last_assistant_message`（回覆全文），掛鉤把它 POST 回去即可，不必讀紀錄檔（實測收件端兩則都收到，欄位來源標為 `last_assistant_message`）。延遲＝模型回完話的當下。中途的工具動作可用 PostToolUse／MessageDisplay 補。

**合規檢查**：以上全部是「使用者自己電腦／容器上的掛鉤或小程式主動去網站拿訊息」，網站只持有我們自己發的接入碼，**從頭到尾沒有碰使用者的 Claude 登入權杖**。d-1／d-2 是在使用者自己的機器上執行官方 CLI，但「由第三方小程式自動驅動訂閱帳號的 CLI」是否符合條款，我沒有讀到條款全文，建議上架前由 legal-compliance 確認；a、b、e 是官方掛鉤機制本身，風險最低。

**安全提醒（重要）**：網站訊息一旦被當成指令執行，接入碼外洩就等於別人能指揮使用者的 Claude。對話功能必須：預設關閉、每個工作階段要使用者在本機明確開啟、訊息長度上限、接入碼可隨時作廢、只接受擁有者本人登入後送出的訊息、並在訊息前綴清楚標示來源（`bridge.py` 已加前綴）。

---

## 八、第 7 題：隱私——送出前要去除或截短的欄位

| 欄位 | 內容 | 處理 |
|---|---|---|
| `prompt`（UserPromptSubmit） | 使用者輸入全文 | **不送**；只送字數與「是否為系統通知」 |
| `tool_input.prompt`（派工） | 派給子 Agent 的指示全文 | **不送** |
| `tool_input.description` | 派工短說明 | 截到 80 字（辦公室要顯示「在做什麼」）；提供「連說明也不送」的開關 |
| `tool_input`（其他工具） | 指令、檔案路徑、程式碼 | **不送**；最多只送工具名稱 |
| `tool_response`、`tool_calls` | 指令輸出、檔案內容 | **不送**；只取 `totalTokens`、`totalDurationMs`、`totalToolUseCount`、`status` |
| `last_assistant_message`、`delta` | Claude 的回覆全文 | 預設**不送**；只有使用者開啟網站對話時才送，截 8000 字 |
| `cwd`、`transcript_path`、`agent_transcript_path`、`scratchpad_dir` | 含使用者名稱與資料夾結構的完整路徑 | **不送**；`cwd` 改成「資料夾名＋路徑雜湊前 16 碼」 |
| `session_id`、`agent_id`、`prompt_id`、`tool_use_id` | 隨機代號 | 可送 |
| `agent_type`、`subagent_type`、`permission_mode`、`source`、`reason` | 類型字串 | 可送（自訂子 Agent 的名字可能透露專案內容，條款要寫明） |
| Token 數、時間 | 數字 | 可送 |
| 紀錄檔裡的 `gitBranch` | 分支名 | 預設不送 |
| 額度百分比與恢復時間 | 帳號用量 | 使用者同意才送 |

實測收件端實際收到的一筆（外掛去識別後）：`{"event":"SubagentStart","ts":…,"session_id":"…","project_name":"project2","project_hash":"2cfb42d1025642bb","cloud":true,"agent_id":"…","agent_type":"general-purpose"}`——沒有路徑、沒有提示詞。

---

## 九、新增題：只做一次帳號層級安裝，所有專案自動上報

### 9.1 本機（電腦上的 Claude Code）
**成立【實測】。** 兩行指令裝在使用者層級，之後任何資料夾開工作階段都會上報，新專案不用再設（第三節）。接入碼放使用者家目錄的 `~/.ai-office/config.json`，不進任何專案。

### 9.2 雲端版要怎麼做到等效
雲端沒有「使用者家目錄」這種跨工作階段的地方，等效物是**雲端環境**（一個環境套用到所有用它的工作階段，不分儲存庫）。做法是在**預設環境**設定三樣：

| 項目 | 填什麼 | 狀態 |
|---|---|---|
| 網路：允許主機 | AI Office 收件端的主機 | 機制【實測】；實際連我們的收件端【未測】 |
| 網路金鑰 | 主機＝收件端、標頭 `Authorization`、值＝接入碼（可限定路徑） | 機制【實測】 |
| 設定腳本 | 安裝外掛（或直接寫入使用者層級掛鉤） | **未證實**，有三個候選，要擁有者驗證哪一個有效 |

設定腳本的三個候選（依優先順序試）：
- **候選甲**：腳本執行 `claude plugin marketplace add …` 與 `claude plugin install … --scope user`。指令在這個容器實測可非互動執行；但文件摘要說使用者層級啟用的外掛不會帶到雲端工作階段，可能被平台覆蓋。
- **候選乙**：腳本直接把掛鉤寫進 `~/.claude/settings.json`（指向腳本下載到固定位置的 `bridge.py`）。只有一則未證實回報說有效。
- **候選丙（保底）**：每個儲存庫自己的 `.claude/settings.json` 放掛鉤。文件說這條確定會帶到雲端，但就不是「裝一次」了，而且會進版控。

所以雲端版的誠實說法是：**「每個雲端環境設定一次」有機會做到，但目前沒有證據**；多數使用者只有一個預設環境時，體感上等於帳號層級一次。若甲、乙都無效，雲端只能退到候選丙，或等官方開放。

### 9.3 擁有者本人在他的雲端環境要配合的步驟
⚠ 依專案規矩：**下面是流程大綱，不是逐格教學**。雲端環境設定頁的欄位名稱以他當下畫面為準，凡標「先截圖」的步驟，要先請他貼畫面、逐格比對後才給填寫內容。前置條件也還沒到位（見步驟 0）。

| 步驟 | 誰做 | 做什麼 | 先截圖？ |
|---|---|---|---|
| 0 | CEO | 先備好：①一個公開的測試收件端（例如測試用 Worker，只記錄不存個資）②外掛放到公開位置（GitHub 型市集或可下載的壓縮檔）③一組測試用接入碼 | 否 |
| 1 | 擁有者 | 打開雲端環境設定（工作階段標題列的雲端環境選單 → Edit） | **是**：整頁截圖，確認有哪些區塊（網路、允許網域、網路金鑰、設定腳本）與實際名稱 |
| 2 | CEO 可代提、擁有者核准 | 把測試收件端主機加進允許清單。這一步可由 CEO 用環境工具提出，擁有者只要在核准卡片上按同意 | 否（核准卡片會顯示確切變更） |
| 3 | 擁有者（非他不可） | 新增一筆網路金鑰：主機、標頭名稱、值＝測試接入碼。金鑰值只能由本人在表單輸入，不能貼進聊天 | **是**：新增金鑰的表單截圖，確認每一格名稱 |
| 4 | CEO 可代提、擁有者核准 | 設定腳本（先試候選甲）。腳本內容會完整顯示在核准卡片上 | 否 |
| 5 | 擁有者 | **開一個全新的雲端工作階段**（設定腳本只在新容器執行），隨便交代一件會派子 Agent 的小事 | 否 |
| 6 | CEO | 看測試收件端有沒有收到 SessionStart／SubagentStart／SubagentStop／Stop，並比對標頭是否被注入 | 否 |
| 7 | CEO＋擁有者 | 沒收到就把設定腳本換成候選乙，重複步驟 4～6；仍沒有就記錄「雲端需用候選丙」 | 否 |
| 8 | 擁有者 | 測完決定保留或移除（移除也走核准卡片） | 否 |

為什麼這些非他不可：雲端環境屬於他的帳號，任何變更都要他本人核准；金鑰值只能本人輸入；設定腳本只在**新的**工作階段生效，要他開；而且我不能在這次任務裡動使用者層級設定。
擋不擋其他工作：不擋。這只影響「雲端版接入」這一項，本機版可以先做。

---

## 十、還需要在擁有者真實環境驗證的清單

| # | 要驗證什麼 | 要他做什麼 | 為什麼非他不可 |
|---|---|---|---|
| V1 | 雲端主工作階段會不會載入設定腳本裝的外掛／寫的使用者層級掛鉤 | 第 9.3 節步驟 1～7 | 要改他的雲端環境並開新工作階段 |
| V2 | 雲端容器的掛鉤 POST 能到我們的收件端、金鑰有被注入 | 同上（步驟 2、3、6） | 同上 |
| V3 | 雲端網頁版裡，Stop 領訊息與 `asyncRewake` 閒置喚醒是否有效、畫面長怎樣 | V1 通過後，在雲端工作階段回合結束後由 CEO 推一則測試訊息，他看畫面有沒有自己動起來並截圖 | 只有他看得到網頁版畫面 |
| V4 | 他自己電腦上（如果有裝 Claude Code）真實安裝外掛 | 貼兩行安裝指令、開一個專案跑一次；之後可移除 | 要動他電腦的使用者層級設定 |
| V5 | 訂閱帳號在互動模式下 `rate_limits` 是否含五小時窗 | V4 裝好後跑一次，由腳本把欄位名稱（不含數字也可）回報 | 取決於他的方案與登入方式 |
| V6 | GitHub 型市集安裝是否與本機目錄型一致 | 需要先把外掛推到公開儲存庫（這次不准 push） | 要他同意公開一個外掛儲存庫 |
| V7 | 條款：由常駐小程式驅動 `claude -p --resume` 是否允許 | 不需他動手；由 legal-compliance 讀條款全文 | — |

V4～V6 若他沒有本機 Claude Code，可以改由 CEO 在可用環境重跑 `tools/ai_office_bridge/test_rig/run_all.sh`。

---

## 十一、建議的最終架構

### 11.1 事件上報

```
使用者的 Claude Code（本機：使用者層級外掛／雲端：預設環境）
  │  掛鉤觸發（SessionStart、UserPromptSubmit、PreToolUse/PostToolUse〔只掛 Agent 工具〕、
  │            SubagentStart、SubagentStop、Stop、StopFailure、SessionEnd…）
  ▼
bridge.py（一支腳本，逾時 2 秒，錯誤全吞，純上報事件設 async）
  │  ① 去識別：只留白名單欄位，路徑改成「資料夾名＋雜湊」
  │  ② 補時間；Stop／SessionEnd 時從紀錄檔加總主工作階段與各子 Agent 的 Token
  │  ③ POST /event，帶接入碼（本機：家目錄設定檔；雲端：代理注入，腳本不持有）
  ▼
AI Office 收件端（Worker）→ 驗接入碼、限速、寫入資料庫
  ▼
網站辦公室畫面輪詢讀取：
  專案＝project_hash 第一次出現時建立「發現的專案」
  子 Agent 上工＝PreToolUse(Agent) 的說明＋SubagentStart 的代號配對
  子 Agent 下工＝SubagentStop（背景）或 PostToolUse(Agent)（前景，含 Token 與耗時）
  下班與否看 background_running，不能只看 Stop
```

### 11.2 網站對話

```
擁有者在網站對話窗送出訊息 → 收件端放進「該工作階段的收件匣」
                                   ▲ 掛鉤主動來拿（網站不主動連使用者機器）
  情況一：Claude 正在忙   → 這回合結束時 Stop 掛鉤查收件匣 → 回 decision:block＋訊息 → Claude 接著處理
  情況二：Claude 閒置中   → 上一次 Stop 留下的 asyncRewake 背景腳本輪詢到訊息 → exit 2 叫醒 → Claude 處理
  情況三：工作階段已關閉 → 網站顯示「這個工作階段已離線」；
                           進階選配：本機常駐小程式用 claude -p --resume 續接（待條款確認）
回覆：Stop 掛鉤把 last_assistant_message POST /reply → 網站對話窗輪詢顯示
延遲：忙碌中＝等這回合做完；閒置＝實測約 3～8 秒
```

第一版建議只做情況一＋二，並標示「實驗功能」；Channels 正式開放自訂通道後再評估換成官方通道。

---

## 十二、風險

| 風險 | 說明 | 緩解 |
|---|---|---|
| 雲端版「裝一次」不成立 | V1 沒過就只能每個儲存庫各放一份 | 先做 V1 再承諾；行銷文案先只寫本機 |
| 掛鉤行為隨版本變動 | 欄位名稱、`asyncRewake`（說明文字標為內部用途的相關欄位）都可能改；舊版有不觸發的回報 | 標明最低版本；接入頁做自我檢查；腳本對缺欄位一律容錯 |
| 拖慢使用者 | 同步掛鉤最壞多等逾時秒數 | async、2 秒逾時、失敗後暫停上報 |
| 被當成指令注入管道 | 接入碼外洩＝可指揮使用者的 Claude | 對話預設關、本機明確開啟、可作廢、長度上限、來源前綴 |
| 隱私 | 派工說明、自訂子 Agent 名稱可能含專案資訊 | 白名單、截短、可關閉、條款寫明、可刪除資料 |
| 條款 | 驅動訂閱帳號的 CLI、產品命名 | 不碰登入權杖；legal-compliance 讀全文後再上架 |
| 畫面觀感 | Stop 領訊息時終端機會顯示「Stop hook error occurred」字樣 | 說明文件先講清楚；觀察官方是否提供自訂顯示文字 |
| 企業帳號 | 管理員可限制掛鉤與 HTTP 掛鉤網址 | 列為不支援情境 |
| 額度資料不完整 | 五小時窗這次沒出現；雲端與無頭沒有狀態列 | 有就顯示、沒有就不顯示，不要承諾 |

---

## 十三、查過的資料與這次留下的痕跡

**WebSearch（2026-11-13，只有摘要）共 7 組關鍵字**：①hooks reference SubagentStart SubagentStop 欄位 ②asyncRewake／async hooks ③status line rate_limits ④cloud environment setup script plugin user settings ⑤Remote Control／channels ⑥channels reference 自訂通道 ⑦plugin hooks SubagentStart not firing。官方頁（只見摘要）：code.claude.com/docs/en/hooks、/statusline、/claude-code-on-the-web、/cloud-environments、/remote-control、/channels、/channels-reference。摘要裡「SubagentStart 的 `agent_type` 只在 `--agent` 啟動時才有」與實測不符（一般派工就有），未採用。
**環境文件工具**：讀了設定腳本、網路、金鑰、相依套件、遠端控制五頁，並讀取目前雲端環境的設定（只讀）。

**這次測試留下的東西（如實列出）**
- 巢狀測試工作階段的對話紀錄寫在 `~/.claude/projects/` 下以 `bridge-test` 結尾的幾個資料夾（Claude Code 自動產生，不是設定檔，可刪）。
- 第一次嘗試互動模式時沒有隔離設定資料夾，首次啟動畫面可能把「已完成新手引導」旗標寫進 `~/.claude.json`（這是程式狀態檔，不是 `settings.json`；之後的互動測試都改用獨立設定資料夾）。
- 對擁有者自己的 Worker 發過兩次不存在路徑的 GET（被代理擋下，沒有到達 Worker）。
- 消耗了少量額度（約 30 個很短的 haiku 回合）。
- `run_all.sh` 整支重跑到第 5 段時容器重啟；第 6、7 段只有手動實測。
