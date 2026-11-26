# ③ CaffAIne：AI 教學頻道製作手冊索引

> 完整原文：ai-mp4 repo，分支 `claude/caffaine-ai`，路徑 `docs/channels/ai-daily-playbook.md`（§一～§三十，339 行）。
> 該分支未併進 ai-mp4 main（11-26 盤點）。取法：`git -C /home/user/ai-mp4 fetch --depth 1 --filter=blob:limit=1m origin claude/caffaine-ai` 後 `git show FETCH_HEAD:docs/channels/ai-daily-playbook.md`。
> 同分支另有：`ai-tutorial.md`、`caffaine-topics*.md`、`caffaine-strategy-1116.md`、`caffaine-top5-1122.md`、`caffaine-verify4-1122.md`、`caffaine-scores.md`、`docs/prompts/caffaine-agent-loop-旁白.txt`、`docs/layout-rules.md`。
> 本檔只做索引與 11-26 盤點到的重點，**不取代原文**。歸檔：2026-11-26（SYSTEM_PLAYBOOK 缺口 #2）。

## 章節索引
| § | 主題 | 日期／來源 |
|---|---|---|
| 一 | 分工（選題→實測→腳本→Gemini TTS 旁白→渲染→檢查） | 11-15；旁白改 API 自動生成 |
| 二 | 內容規格：45～75 秒、一支教一招、真實實測不改字、第 0 幀大字、每支有留言關鍵字 | 11-15 |
| 三 | 畫面：等距 2.5D 粉彩桌面、cue 驅動、字卡 ≥28px | 11-15 |
| 四 | 四個頻道共用版面規則 | 11-15 |
| 五、六 | 交片前檢查、範本片已知問題 | 11-15 |
| 七 | 內容三段結構 | 11-15 |
| 八 | 全頻道共用製作細則（LOGO 音效、動畫優化） | 11-15 |
| 九 | 標準流程：找題材→規劃→生成→驗證→優化→配旁白→發布；每週檢討 | 11-15 |
| 十 | 照哩股哩股敘述做（10.1 主控補充） | 11-16 |
| 十一 | 影片放進網站文章並可下載 | 11-15 |
| 十二 | 文案與開頭（套 ig-threads-copy skill） | 11-15 |
| 十三 | 退件教訓：急促、聽不懂、沒邏輯（13.1 寫稿步驟） | 11-16 |
| 十四、十五 | 省 Token、量產指令（一週 40～50 支） | 11-16、11-17 |
| 十六 | 形式、畫面、題材輪替，不准同模子量產 | 11-17 |
| 十七 | 開頭邏輯、結尾引導、節奏頓挫 | 11-17 |
| 十八、十九 | 片中不放「還不知道／沒實測」；畫面不放英文；題材要帶得走的技巧 | 11-17 |
| 二十 | 畫面配合內容做比喻與動作，不只對話框 | 11-17 |
| 二十一 | 鉤子試問法、細緻度六面向、範例庫、每支復盤 | 11-20 |
| 二十二 | 子 agent 依工作搭 model＋effort（見 `model_effort.md`） | 11-20 |
| 二十三 | 片尾「留言 XX」固定字（Andy 尚未給內容） | 11-20 |
| 二十四 | 音訊不斷續 | 11-21 |
| 二十五 | 交件前四道驗證 | 11-22 |
| 二十六 | 聲音先定、畫面跟聲音 | 11-22 |
| 二十七 | 全頻道語速上限與 AI 頻道舊目標的衝突（以 AI 頻道專屬規定為準） | 11-22 |
| 二十八 | 重置前只做到重置前分量 | 11-22 |
| 二十九 | 省花費 | 11-22 |
| 三十 | 頻道完善順序（科技→AI→哩股）與文章規範 | 11-23 |

## 最常用的硬規則（摘自 §一與 §二十七）
- 語速：成片扣停頓 ≥5.4（理想 5.4～5.8）、含停頓 ≥4.9 音節／秒；模型不夠快用 `TAKE_ATEMPO`（上限 1.15）、幕間停頓 `ALIGN_GAP_MAX=0.35`；全頻道 ≤4.3 不適用於本頻道（主控 11-22 確認；見 `video_logic.md`「各頻道語速」）。
- 旁白一律 API 生成（Gemini 2.5 Flash Preview TTS、音色 Sulafat、profile `ai-report-v5`），整篇送 1 次、沒音訊最多再送 1 次；重配前要先講原因與次數、等 Andy 同意。
- 發文走 `channel_post.yml`（台北 12:15、21:00，11-15 起）；選題與週流程見 `.claude/skills/caffaine-github-weekly`、本資料夾 `plan_202611_內容規劃.md`。

## 相關本 repo 檔
`handoff/ch3_20261124.md`（現況與待 Andy 事項）、`meta_inbox_automation_1120.md`（留言私訊）、`article_standard.md`、`video_logic.md`、`token_budget.md`。
