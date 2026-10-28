# 主題文章每日自動：AI 圖審查紀錄與重疊檢查（2026-10-29）

## AI 圖審查（依 ai_image_review.md）
- 本批所有卡片**不含任何 AI 生成圖**：版型為 `D-知識卡`（幾何版型：灰框大字＋三列資訊）與 `D-無圖大數字`；實景版型只用 Wikimedia Commons 真實照片（非 AI）。meta 一律 `has_ai_image: false`。
- 因此十條 AI 圖審項目不適用；自動流程不會產生 AI 圖，也不會從非「已審」圖池取圖（`social_news.py` 不開 allow_unreviewed）。
- 日後若加 AI 圖版，必須走 ai_image_review.md 流程並在每篇資料夾留 `ai_review.md`，layout 標 `D-AI圖`。
- 審查人：社群營運主管（自查）。**尚未經 art-director 複審**（本 session 無法派工）；建議 CEO 開關前請 art-director 看一次 `scratchpad/topic_auto/evg_all/*.jpg` 11 張。

## 版面自查（post_design_system.md／news_post_rules.md）
| 項目 | 結果 |
|---|---|
| 重疊檢查（程式，`chk_all.py` 逐篇渲染常備文庫） | 程式 11 張 0 筆（修正前 2 筆：「4 步」「10 日」大字行高被中文單位撐高壓到類別標籤） |
| 樣本重疊（今天盤後、週六 wk1、wk2、10-28 重播新聞） | 程式 4 張 0 筆；人工 4 格全解析度／縮圖逐張看 0 筆 |
| 字級下限 28px、安全邊距 64、格線 8 倍數 | 通過（CHECK 無出界／字太小／格線） |
| 對齊／留白修正 | ①單張卡底列「1 / 1」無意義 → 改左側放資料來源、多張才放張數；②大字框右半邊留白 → 大字依字數放大到最多 280px；③中文值（如「勞工統計局」）56px 貼滿 80px 列 → 縮 44px；④大字與灰框說明字距太貼 → 加 8px；⑤右上角時段字知識卡不再冒充「盤後新聞」 |
| 前後對照圖 | `scratchpad/topic_auto/before_after/前後對照.png` |
| 渲染字型 | 本機無 Noto Sans CJK TC，樣本用文泉驛正黑；Actions 會下載 Noto，字寬略有差，版面用實測字寬縮放，重疊檢查在 Actions 上會再跑一次 |

## 法遵
- 常備文庫 11 篇逐篇過 `news_legal.check`（單元測試 `test_evergreen_library_all_pass_gates`）；「買進／賣出」等字眼已改寫成「買股／先賣／買方成交金額」。
- 內容為定義型知識，不含股價推論；數字只有制度性事實（每年 8 次 FOMC、月營收次月 10 日前公告）。**事實查證仍需 finance-content-editor 對 `sources` 欄位覆核一次**。
