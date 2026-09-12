# .claude/agents — 長期工作 Agent

Andy 提需求 → CEO（主 session）判斷屬於哪個領域 → 用 Task 工具派給下面對應的 Agent。
每個 Agent 的完整職責、負責檔案、檢查標準都寫在 repo 根目錄的 `AGENTS.md`，
這裡的檔案是「讓 Claude Code 真的叫得到它們」的定義檔。

**每個 Agent 開工前一律先讀**：`CLAUDE.md` → `AGENTS.md`（自己那一節）→ `HANDOFF.md` → `DECISIONS.md`。
這是硬規定：DECISIONS.md 裡已經拍板的事不重新討論、不「順手改回去」。
