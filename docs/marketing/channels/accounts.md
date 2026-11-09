# 各頻道社群帳號與 GitHub 密碼名稱對照（2026-11-09）

Andy 原話：「提供給我 IG Thread 名稱就好 讓你以後找的到」。
GitHub 密碼頁：https://github.com/MiaoZiKe/tw-rotation/settings/secrets/actions
所有頻道共用同一個 Meta 應用程式「liguligu-social」（App ID 993014640153379）；`THREADS_APP_SECRET` 共用一筆。

| 頻道 | IG／Threads 帳號 | IG 權杖密碼名稱 | Threads 權杖密碼名稱 | 狀態 |
|---|---|---|---|---|
| ① 股票網頁（哩股哩股） | liguligu0818 | `IG_ACCESS_TOKEN` | `THREADS_ACCESS_TOKEN` | 既有，運作中 |
| ④ 談晴說礙 | talk_01010909 | `HEALING_IG_ACCESS_TOKEN` | `HEALING_THREADS_ACCESS_TOKEN` | Andy 11-09 回報已設好 |
| ② 科技透明圈 | Tech_01010909 | `TECH_IG_ACCESS_TOKEN` | `TECH_THREADS_ACCESS_TOKEN` | 等 GitHub 密碼 |
| 水下蝦米（幣圈） | Shrimp_01010909 | `SHRIMP_IG_ACCESS_TOKEN` | `SHRIMP_THREADS_ACCESS_TOKEN` | 等 GitHub 密碼；目前另用 Buffer 發文 |
| ③ AI 介紹頻道 | caffaine.ai | `CAFFAINE_IG_ACCESS_TOKEN` | `CAFFAINE_THREADS_ACCESS_TOKEN` | 等 GitHub 密碼 |

共用：`THREADS_APP_SECRET`（Threads 應用程式密鑰，讓系統把 1 小時的 Threads 權杖自動換成 60 天）。
帳號 ID 不用另外放：程式用權杖自動查（/me）。權杖每週自動續期，續期後的新值寫回同名加 `_AUTO` 的密碼（例如 `TECH_IG_ACCESS_TOKEN_AUTO`），不用手動建。
⚠ 頻道對應（Tech＝②、caffaine.ai＝③、Shrimp＝水下蝦米）是 CEO 依帳號名推定，Andy 若不同請更正本表。
