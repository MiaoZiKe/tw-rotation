# AI Office 接入元件雛形與實測工具

> 2026-11-13 建立（可行性實測）；2026-11-14 外掛整理成第一版可安裝版本（`plugin/ai-office-bridge/`），收件端在 `workers/ai-office-bridge/`。
> 沒有任何金鑰或個人資料；測試只連 `127.0.0.1`。實測結論在 `docs/ai_office/bridge_test_report.md`；**設定步驟在 `docs/ai_office/bridge_setup.md`**。

## 內容

| 路徑 | 是什麼 |
|---|---|
| `plugin/` | 外掛市集（marketplace），裡面只有一個外掛 |
| `plugin/ai-office-bridge/` | 外掛第一版：`hooks/hooks.json` 把 12 種事件交給 `scripts/bridge.py`（全部 `async`、逾時 5 秒） |
| `plugin/ai-office-bridge/scripts/bridge.py` | 單一掛鉤腳本：去識別 → 背景送到收件端 `POST /v1/events`；工具只送類別、同類別 20 秒內不重送；收件端連不上就暫停 2 分鐘 |
| `plugin/ai-office-bridge/scripts/install_hooks.py` | 不用外掛系統時，把掛鉤寫進一份設定檔（雲端設定腳本用）；重跑不重複、`--remove` 只移除自己的 |
| `plugin/ai-office-bridge/scripts/test_bridge.py` | 外掛自我測試（去識別、類別、節流、背景送出、暫停、安裝）：`python3 test_bridge.py` |
| `test_rig/wait_inbox.py` | 實驗：閒置時被網站訊息叫醒（`asyncRewake`）。**第一版外掛不含網站對話**，只留在實驗工具裡 |
| `test_rig/receiver.py` | 假收件端（只聽 127.0.0.1:8765）：`/event`、`/slow`、`/err`、`/inbox`、`/inbox/push`、`/reply`、`/stopdecide` |
| `test_rig/log_event.py` | 把掛鉤收到的 JSON 原樣寫檔 |
| `test_rig/gen_settings.py` | 產生測試專案自己的 `.claude/settings.json`（模式：all／http／stopcmd／stophttp／ctx） |
| `test_rig/stop_bridge.py`、`ctx_hook.py`、`mcp_inbox.py`、`wait_inbox.py`、`pty_run.py` | 各項實測用的小腳本（檔頭有說明） |
| `test_rig/run_all.sh` | 一鍵重跑第 1～7 段實測 |
| `samples/hook_payloads.sanitized.json` | 2.1.323 實測收到的各事件原始 JSON（路徑已換佔位字、用量數字已遮蔽） |

## 重跑方式

需要：已登入、能跑的 Claude Code（`claude --version`）、`python3`、`curl`。會用到少量額度（每段一兩個很短的回合，模型指定 haiku）。

```bash
bash tools/ai_office_bridge/test_rig/run_all.sh /tmp/aio_bridge_test
```

- 專案掛鉤寫在工作資料夾自己的 `.claude/settings.json`；外掛安裝那一段用獨立的 `CLAUDE_CONFIG_DIR`，**不會動到 `~/.claude`**。
- 每一段會印出預期結果（例如「應看到 391」）。原始紀錄在 `<工作資料夾>/logs/`。
- ⚠ 2026-11-13 這支腳本整支重跑時跑到第 5 段後容器重啟而中斷；第 1～5 段的輸出與手動實測一致，**第 6、7 段只有手動實測過，腳本版本尚未完整跑過一次**。
- 互動式終端機的兩項（狀態列收到的資料、閒置喚醒）另外用 `test_rig/pty_run.py`，做法見報告第 5、6 題。

## 外掛的設定（都不進 repo）

環境變數優先，其次 `~/.ai-office/config.json`（可用 `AIO_CONFIG` 改路徑）：

| 名稱 | 用途 |
|---|---|
| `AIO_URL` | 收件端網址；沒有就什麼都不做 |
| `AIO_TOKEN` | 接入碼，放在 `Authorization: Bearer`。雲端版建議不設，改由環境的「網路金鑰」在代理端注入 |
| `AIO_SUMMARY` | `0`＝連派工短說明與回覆摘要都不送 |
| `AIO_DISABLE` | `1`＝完全停用 |
| `AIO_RAW_LOG` | 只給測試：把原始 JSON 寫到這個檔 |

## 設計原則（實測後確認要守的）

1. 掛鉤任何錯誤都 `exit 0`，送出交給背景子程序（父程序立刻結束），連線逾時 2 秒；掛鉤本身 `timeout` 5 秒、`async: true`。失敗、逾時都不會中斷工作階段（已實測）。
2. 預設不送提示詞、程式碼、工具輸入輸出、完整路徑；只送白名單欄位（見 `bridge.py` 的 `sanitize`）。
3. 掛鉤資料沒有時間與 Token 欄位：時間由腳本補，Token 從對話紀錄檔加總（子 Agent 的要在回合結束時再算，SubagentStop 當下會少算）。
4. `UserPromptSubmit` 也會被「背景子 Agent 完成通知」觸發，不能直接當成「使用者說了一句話」。
