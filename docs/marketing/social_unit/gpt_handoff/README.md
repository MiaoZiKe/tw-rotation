# 與 GPT 協作產出貼文與圖片（交接流程）

> Andy 10-16：精選貼文由社群媒體部負責整理文章；他每天從清單點選要做的題目；貼文與圖片交給 GPT 產出，完成後通知他。

## 先講限制（如實）
1. 本部（Claude，雲端容器）**不能直接呼叫 ChatGPT**：容器沒有連 OpenAI 的路徑，也沒有金鑰；金鑰也不能放進 public repo。
2. 所以「交給 GPT」＝**本部產出一份交接包**（Markdown），由 Andy 的 ChatGPT 取用；取用方式依下面三階段，由省事到全自動。
3. 圖片以 GPT 產出為主；網站真實截圖與比比既有素材（`docs/anim/bibi_library/`）由本部提供，不要求 GPT 重畫。

## 三階段方案
| 階段 | 怎麼做 | Andy 要做 | 通知 | 狀態 |
|---|---|---|---|---|
| 1 立刻可用 | 本部在對話裡回交接包，Andy 複製貼進 ChatGPT（建議建一個專案／自訂 GPT，貼上本目錄 `gpt_instructions.md` 當固定指令） | 勾選＋複製貼上 | 本部在對話回報；GPT 做完 Andy 自己看 | ✅ 文件已備 |
| 2 少動手 | 交接包存 repo 固定位置 `handoff/latest.md`（repo 是 public，GPT 若有瀏覽能力可讀 raw 網址）；Andy 對 GPT 說「照最新交接包做」 | 勾選＋一句話 | GitHub Issue 留言（手機 GitHub App 推播／信件） | 🛠️ 待 Andy 同意建立 Issue 流程 |
| 3 全自動 | GitHub Action 呼叫 OpenAI API 生文生圖並 commit，再發通知 | 提供 OpenAI API 金鑰（只存 GitHub Secrets）；接受按量計費 | Issue／Email | ⏸ 需 Andy 決定要不要付 API 費（ChatGPT 訂閱不含 API） |

## 勾選與通知怎麼接（階段 2 的設計）
1. 每天一份「每日選題清單」發成一則 GitHub Issue（內含勾選框，格式見 `../daily_menu/_template.md`）。Andy 用手機 GitHub App 勾選即可。
2. 本部定時（排程任務）讀取被勾的項目 → 產出交接包 → 在同一則 Issue 留言「交接包已備好」，Andy 會收到 GitHub 通知。
3. GPT 完成後，Andy 把成品貼回（或放進指定資料夾），本部做法遵與查證複核，回報可發佈。
⚠ 排程任務與 Issue 都是對外動作／會用額度，**未經 Andy 同意不建立**。
⚠ 目前 `social_topics.yml` 每日排程還沒合併 main；沒合併前清單由本部手動跑腳本產出。

## 交接包內容（每個被勾題目一份，範本見 `handoff_template.md`）
目標與受眾、比比口吻規格、結論先行大綱、已查證事實（附來源與日期）、不可說清單（法遵）、圖表與圖片清單（誰提供／GPT 要畫什麼）、輸出格式與字數、免責與 CTA、utm 連結、完成後回傳格式。

## 品質與責任分工
- 事實、數字、供應鏈說法：**本部查證後才進交接包**；GPT 只負責把已查證內容寫成貼文與畫圖，不得自行新增數據或點名個股。
- GPT 成品回來後，本部做：事實對照、法遵、重疊與排版檢查（圖文），通過才標「可發」。

## 補充（Andy 10-16）：用 Gmail 讓 GPT 取得內容可行嗎？
- 結論：**email 不能「觸發」ChatGPT**（它不會被信件喚醒）；只能由 ChatGPT 自己排程或由 Andy 對它說一句話時去讀。這點與 Drive 相同，是「拉」不是「推」。
- 可行做法：ChatGPT 若有 Gmail 連接與「排程任務」功能，可設定每天固定時間讀取特定寄件者／標籤的最新信件並照做。**這兩個功能在 Andy 的方案是否可用、是否能搭配使用，本部未驗證**；請 Andy 在 ChatGPT 試一次：建立排程任務「每天 08:30 讀 Gmail 中最新一封寄件者為 notifications@github.com 且標題含『交接包』的信」，看它能不能執行。
- 本部這邊不需要連接器就能產生信：排程任務在 Issue 留言交接包全文，GitHub 會寄通知信到 Andy 的 Gmail；ChatGPT 讀那封信即可。
- 注意：信件內容含交接包全文，不放金鑰；Issue 是公開的，交接包內容必須是可公開的（只含查證過的公開資訊與我們的文案）。
