# 社群交接（Claude 研究 → GitHub → GPT 製作）

> Andy 2026-10-16：Claude 研究、查核、寫重點；GPT 做社群文案改寫、IG 十頁設計、比比主持插圖、Threads 與視覺品管；GitHub 做交接、版本與素材來源管理。**這一版只做交接，不自動發布到任何社群帳號。**

## 分工
| 角色 | 負責 |
|---|---|
| Claude | 研究、文章重點、來源查核、數據與分析（寫 `brief.md`、`sources.md`、`manifest.json`） |
| GPT | 社群文案改寫、IG 十頁（1080×1350）設計、比比主持插圖、Threads 與視覺品管 |
| GitHub | 交接（PR）、版本（revision）、素材來源（`asset_references`） |
| Andy | 最後審稿與手動發布 |

## 一篇一個資料夾
`docs/social_handoff/YYYY-MM-DD_topic-slug/`：`brief.md`（交接單）、`sources.md`（來源表）、`manifest.json`（機器可讀狀態）、`assets/`（本篇必要參考素材；用既有素材可只記路徑）。
範本在 `_templates/`；用 `python scripts/social_handoff.py new <日期> <slug> "<主題>"` 建立骨架。

## 狀態與規則（給自動觸發辨識）
`draft → ready_for_gpt → processing → completed／needs_revision／failed`

| 狀態 | 誰改 | PR 狀態 |
|---|---|---|
| `draft` | Claude 建立時 | **draft PR** |
| `ready_for_gpt` | Claude，執行 `python scripts/social_handoff.py ready <資料夾>`（先通過檢查）後才可改 | 改成 **ready for review**（這一步才是給 GPT 的觸發訊號） |
| `processing` | GPT 開工時 | ready for review |
| `completed` / `needs_revision` / `failed` | GPT 或 Andy | 依結果 |

- **PR 標題固定格式：`[社群交接] YYYY-MM-DD｜主題`**；同一工作修訂時更新原 PR 與 `revision`，不要另開 PR。
- 分支名：`claude/social-handoff-YYYY-MM-DD-<slug>`；不直接提交 main。
- PR 說明列：job_id、revision、交接檔路徑、資料截止時間（Asia/Taipei）、待確認事項。
- 建立 PR **不代表** ChatGPT 已收到或開始製作；ChatGPT 端的 GitHub 事件任務由 Andy 在該對話設定。
- 不預設有能直接向 ChatGPT 對話送訊息的 API；不使用瀏覽器自動貼訊息；不使用付費 OpenAI API。

## 視覺規範
`docs/social_handoff/style/LIGULIGU_IG_Threads_Style_Guide.md`（v1.0，Andy 2026-10-16 提供）。manifest 的 `style_guide_status` 必須是 `present` 才能標 `ready_for_gpt`。不得自行重建成另一套規範。
比比主持規則（沿用既有）：`docs/marketing/video_1010/bibi_host_spec.md`、造型以 `docs/anim/bibi_library/reference/parts_sheet_1011.webp` 為準；每頁依內容換表情、視線、姿勢與道具，不能十頁同一張笑臉。

## 素材來源分類（`asset_references[].category`）
| category | 意義 |
|---|---|
| `gpt_original` | GPT 原繪 |
| `claude_original` | Claude 原作／程式繪製 |
| `claude_derived` | Claude 對既有素材的衍生加工／動畫（原畫作者仍須保留，不得改成 Claude） |
| `user_provided` | 使用者提供的參考 |
| `author_unverified` | 作者待核實（不依風格猜作者） |

每筆記：`path`、`category`、`original_author`、`processed_by`、`provenance_evidence`、`parent_path`、`note`。不確定的欄位寫 `"unknown"`，不要猜。不得搬動既有素材（網站引用路徑會失效）。

## 內容紅線（沿用專案規範）
不點名個股推薦、不買賣建議、不保證獲利；預估與財測不寫成事實；新聞用自己的話並附來源；非投顧免責維持。
