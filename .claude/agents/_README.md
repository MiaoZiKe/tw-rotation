# .claude/agents — 長期工作 Agent（九個）

Andy 提需求 → CEO（主 session）判斷屬於哪個領域 → 用 Task 工具派給下面對應的 Agent。
每個 Agent 的完整職責、負責檔案、檢查標準都寫在 repo 根目錄的 `AGENTS.md`，
這裡的檔案是「讓 Claude Code 真的叫得到它們」的定義檔。

**每個 Agent 開工前一律先讀**：`CLAUDE.md` → `AGENTS.md`（自己那一節）→ `HANDOFF.md` → `DECISIONS.md`。
這是硬規定：DECISIONS.md 裡已經拍板的事不重新討論、不「順手改回去」。

## 名單（2026-09-14 起九個）

| 定義檔 | 角色 | 一句話 |
|---|---|---|
| `finance-quant` | 金融專家 | 這個數字該怎麼算、什麼時候可以用 |
| `frontend-ui` | UI 專家 | 版面、圖表、互動、手機寬 |
| `data-scraper` | 爬蟲專家 | 資料源接入、額度、可失敗設計 |
| `smc-technical` | 技術分析專家 | 指標、SMC、多週期判讀 |
| `industry-analyst` | 產業分析師 | 族群成分、題材、供應鏈、剖析圖 |
| `reviewer` | 審核專家 | 只驗收不改扣，跑完整清單不抽查 |
| `strategy-backtest` | 策略回測 | 照這套規則做，過去到底賺不賺 |
| `visual-explainer` | 圖解教學 | 看不懂的東西要有人翻成人話 |
| `data-steward` | 資料治理 | 資料新不新、壞了誰知道 |

規矩不變：**有人做完，一定要有另一個人去驗**。不要自己做自己驗就說完成。
