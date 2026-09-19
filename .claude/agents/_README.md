# .claude/agents — 長期工作 Agent（十五個）

Andy 提需求 → CEO（主 session）判斷屬於哪個領域 → 用 Task 工具派給下面對應的 Agent。
每個 Agent 的完整職責、負責檔案、檢查標準都寫在 repo 根目錄的 `AGENTS.md`，
這裡的檔案是「讓 Claude Code 真的叫得到它們」的定義檔。

**每個 Agent 開工前一律先讀**：`CLAUDE.md` → `AGENTS.md`（自己那一節）→ `HANDOFF.md` → `DECISIONS.md`。
這是硬規定：DECISIONS.md 裡已經拍板的事不重新討論、不「順手改回去」。

## 名單（2026-09-19 起十五個）

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
| `delivery-planner` | 交付排程 | 這批有幾件事、先做哪個、做完了沒 |
| `tech-illustrator` | 機構繪圖 | 剖析圖、封裝結構、3D 零件 |
| `efficiency-planner` | 效率規劃 | 這步能不能不做、哪個 CP 值最高 |
| `resource-auditor` | 資源稽核 | Token／額度／Actions 分鐘數 |
| `mechanical-engineer` | 結構審查 | 畫得**對不對**（開畫前先寫規格書） |
| `art-director` | 視覺總監 | 畫得**好不好看**（擁有 `--dg-*`） |

規矩不變：**有人做完，一定要有另一個人去驗**。不要自己做自己驗就說完成。

繪圖這條線是**三個人**：`tech-illustrator` 畫、`mechanical-engineer` 驗結構、
`art-director` 驗視覺。**開畫之前 `docs/diagram_specs/<id>.md` 要先存在並由
`mechanical-engineer` 簽掉**（2026-09-19 起）。兩個審查者衝突時，結構優先。
