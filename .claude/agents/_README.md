# .claude/agents — 長期工作 Agent（十八個）

Andy 提需求 → CEO（主 session）判斷屬於哪個領域 → 用 Task 工具派給下面對應的 Agent。
每個 Agent 的完整職責、負責檔案、檢查標準都寫在 repo 根目錄的 `AGENTS.md`，
這裡的檔案是「讓 Claude Code 真的叫得到它們」的定義檔。

**每個 Agent 開工前一律先讀**：`CLAUDE.md` → `AGENTS.md`（自己那一節）→ `HANDOFF.md` → `DECISIONS.md`。
這是硬規定：DECISIONS.md 裡已經拍板的事不重新討論、不「順手改回去」。

## 名單（2026-09-19 起十八個）

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
| `semi-chain-analyst` | 半導體鏈分析師 | 去外面查：誰幫誰代工、封測客戶是誰 |
| `pcb-substrate-analyst` | 載板分析師 | 去外面查：載板 vs PCB、材料來自誰 |
| `ai-server-analyst` | AI 伺服器分析師 | 去外面查：散熱／電源／光通訊／機櫃 |

規矩不變：**有人做完，一定要有另一個人去驗**。不要自己做自己驗就說完成。

繪圖這條線是**三個人**：`tech-illustrator` 畫、`mechanical-engineer` 驗結構、
`art-director` 驗視覺。**開畫之前 `docs/diagram_specs/<id>.md` 要先存在並由
`mechanical-engineer` 簽掉**（2026-09-19 起）。兩個審查者衝突時，結構優先。

三位**鏈別查證分析師**（2026-09-19 起）跟 `industry-analyst` 分工不同：
後者管「這個 repo 裡的族群／題材／環節怎麼定義」，前者管「**外面的世界到底怎麼運作**」。
它們**只查不改**，共同規矩在 `_RESEARCH_RULES.md`（硬性：兩個獨立來源才給高信心、
社群只當線索、**查不到就寫查不到**、附 URL 並寫出它講了什麼、標信心度）。

**後續有類似領域就開新的一位**（Andy 2026-09-19）。判準：只要某個領域一再需要
「去查外面的事實」而不是「讀這個 repo」，就替它開一位 —— 例如 MLCC／被動元件、
面板、重電、生技。新開的一定要寫出「這條鏈上最容易錯的三到四件事」，
不然它跟通用的 `industry-analyst` 沒有差別。
