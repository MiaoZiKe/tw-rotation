# Meta 權限檢查結果（2026-10-27 台北，工作流 meta_perm_check 第 1 次）

結論：W6 洞察所需權限齊全，Andy 不必動手（O-1 可劃掉）。

| 項目 | 結果 | 依據 |
|---|---|---|
| IG 基本資料 instagram_business_basic | 已有 | me 成功；帳號 liguligu0818，類型 BUSINESS |
| IG 洞察 instagram_business_manage_insights | 已有 | 帳號層 reach、views、follower_count 與單則 views、reach 都成功 |
| Threads 基本 threads_basic | 已有 | me、me/threads 成功 |
| Threads 洞察 threads_manage_insights | 已有 | threads_insights views、followers_count 與單則 views、likes、replies 成功 |
| 權杖到期日 | 查不到 | IG Login 權杖不支援 me/permissions 與 debug_token；需看開發者後台或最後一次產生日期 |
| IG_USER_ID、THREADS_USER_ID | Secrets 內為空 | 程式用 me 取得，洞察端點用 me 可行，W6 不依賴它 |

W6 規格重點：IG 帳號層用 metric=reach,views 加 metric_type=total_value；follower_count 用 period=day；Threads 用 me/threads_insights?metric=views,followers_count。

## 權杖到期日（Andy 2026-10-27：「我是昨天申請的」）
- 申請日：2026-10-25（台北）。長效權杖約 60 天 → **預估到期 2026-12-24**（推算值，Meta 未回傳到期欄位）。
- 2026-12-17 排了提醒，屆時給 Andy 逐格重新產生權杖的步驟；`social_insights.yml` 每日 `token_check` 失效會標紅。
