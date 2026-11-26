# 排程清單（名稱、時間、目的、綁定對話）

> 歸檔：2026-11-26（SYSTEM_PLAYBOOK 缺口 #6）。資料來源：當天用 `list_triggers` 讀到的排程系統現況（只取名稱、時間、目的與出處，**未抄 prompt 全文**；prompt 內含的規則出處都已列在「目的」欄），再對照 `handoff/ceo_20261124.md`、`ch1_20261124.md`、`ch4_20261123.md`、`ch2_20261125.md`、`ch3_20261124.md`。
> 排程本身存在排程系統，不在 git；**現役狀態以 `list_triggers` 為準**，本檔是備援與說明。時間一律台北。
> 規則：一律叫它「排程」；停用的舊排程不列。換新對話時要把綁定改到新對話（見 `README.md` 對話管理）。
> 這份是 11-26 的快照，之後有增減要在這裡更新。

## 主控（CEO）綁定（session_018gakVURjPpCLn9AKajmD1E）
| 名稱 | 時間 | 目的（Andy 原話出處） |
|---|---|---|
| 社群發文監工：盤後 18:20 | 週一～五 18:20 | 交易日查 social-snaps `state/posted.json` 有沒有 `close-<今天>`；沒發就讀 log、修、重派 social-live 到發出為止；資料晚到每 30 分鐘自查（10-28「以後不要再發生，知道沒辦法發文需要立即安排人員處理直到完成」） |
| 資料維修監工：每日盤後 | 週一～五 21:47 | 讀 `data/_state/source_health.json`、`last_run.json`；有連續失敗／官方比對不一致／缺口就派 data-scraper 或 data-steward 修到恢復（11-06「找不到的要再安排維修人員去修復」） |
| 網站週報與新功能提案 | 每週六 10:23 | 健康週報、自主優化 1～3 件、提 3～5 個新功能寫入 `docs/feature_proposals.md` 等 Andy 勾選（11-06 網站由 CEO 全權維護） |
| Token 管理單位：每日用量檢查 | 每日 15:17 | 讀各頻道現役對話用量、更新 `token_ledger.json`、抓浪費、超過 30 萬的換新對話、額度警戒（11-20 新增專責 Token 單位；規則 `token_budget.md`） |
| 規範備份同步到 Google 雲端硬碟（每日） | 每日 23:23 | 依 `docs/drive_backup_manifest.json` 重建彙整檔、有變就更新 Drive（11-26 Andy「單一在 Github 不行，需要新增到 Google Drive」） |
| ②換新對話（額度重置後）（一次性提醒） | 11-27 07:10 | 週額度重置後把 context 約 57 萬的② 換新對話（封存舊的、4 個排程改綁） |
| 封存舊主控兩個對話（一次性，已停用） | 11-25 | 11-24 換主控後滿 24 小時封存舊主控 |

## ① 哩股哩股（session_018gakVTRUVZuXnGDLoyMk1p）
| 名稱 | 時間 | 目的 |
|---|---|---|
| 頻道①自動回覆寫稿 | 每日 11:47、15:47、19:47、21:47 | 照 `docs/marketing/social_unit/auto_reply.md` 第四節五步寫留言回覆稿；待寫清單空的就結束不回報（11-09 Andy「需要你像人一樣做回覆」） |
| 頻道①每週流量檢討會 | 每週一 10:13 | 拉 Threads／IG／網站數據，開六人會議，定下週 3～5 件改動並寫 `docs/marketing/weekly_review/`；11-23 起精簡版，11-30 恢復完整版（11-09「沒流量什麼都不用談」） |

## ② 科技透明圈（session_018gakVRpyYeXzwbb6S5bBdm，11-26 後會換新對話）
| 名稱 | 時間 | 目的 |
|---|---|---|
| 科技透明圈到點補發 | 每日 18:07、20:07 | 讀 main `social/tc/queue/*/post.md`，找 status approved 且 `scheduled_at` 已到的稿，觸發 `tc_post.yml`（dry_run=false），確認 posted 並回報 IG／Threads 網址（11-12「麻煩安排人去監控」；GitHub 排程常延遲） |
| 科技透明圈發文監工 | 每日 18:47、20:47、22:47 | 確認已發出並回報連結；沒發就修到發出；檢查明天稿的 18:00／20:00 隔天交替週表（11-18） |
| 科技透明圈負責人每週檢討會 | 每週一 10:07 | tc-channel-lead 主持，派市調、內容、美編、社群四人，主題／內容／流量／排版四面向結論，週報寫 `tc/weekly/<週一日期>.md`，列 5 個候選題（Andy「負責人每週都要安排時間討論並優化」） |
| FB 追進度 | 非 Claude 排程，在 `social/tc/fb_backfill.json` 的 slots：08:00、12:00、18:00 | 回補 FB 粉專 Reels（見 `tc/autopost.md`） |
| gh-cron Worker | 08:01／08:16、12:01／12:18、18:01／18:18、20:01／20:18 | Cloudflare Worker 準時派 `tc_post.yml`（GitHub 原生排程約 8 小時才跑一次） |

## ③ CaffAIne
沒有綁 Claude 排程（11-24 查過）。發文走 GitHub Actions `channel_post.yml`，台北 12:15、21:00（11-15 起）。

## ④ 談晴說礙（session_018gakVR7b9oN9B5wv8q5xWf）
| 名稱 | 時間 | 目的 |
|---|---|---|
| 談晴說礙中午輪播保底 | 每日 12:41 | 確認 12:27 輪播已發到 IG 與 Threads，沒發就觸發 `healing_post.yml`（mode=post）修到發出（11-16「放寬」：每天最多 2 則，輪播 12:27＋影片 20:27） |
| 談晴說礙每晚發文保底 | 每日 20:41 | 同上，對 20:27 影片（11/11 當晚 8 個時段一個都沒準時跑） |
| 談晴說礙留言回覆準時補跑 | 每日 21:13、23:13 | 觸發 `healing_comments.yml`，用 `healing_comments.py --needs-human 24` 看自傷訊號則數（只報則數與貼文，不自動回覆；11-15 Andy 決定不回 1925） |
| 談晴說礙每週討論日 | 每週日 15:41 | healing-editor 主持，讀 7 天成效，寫 `weekly/<yyyymmdd>_檢討.md`，把下週 7 天內容排進佇列（11-10「一個禮拜有一天討論方向、改善」） |
| 談晴說礙檢討＋優化主題增加流量（一次性） | 11-27 07:30 | 11/16～11/26 成效檢討、查同類帳號高流量題型、提 12 月第一週主題清單、接續 11/28 平均月薪與 11/29 離職兩支（11-22「記得開檢討並優化發文主題增加流量」） |
| IG 重複發文檢查 | 非 Claude 排程，GitHub `ig_dup_check.yml` 每日 23:11 | 只讀檢查四帳號，報告 `IG重複發文檢查.md`（11-24） |

## 其他
| 名稱 | 時間 | 目的 |
|---|---|---|
| 精選文章產出佇列 | 每日 08:05～23:05 每小時（不綁對話，每次開新對話） | 同步 `article-jobs.yml`、生成每日 9 個主題、依 `priority_3d.md` 與重做佇列產文章；佇列空就回「佇列空的」（11-17、10-19 省 Token 規則） |
| Meta 權杖到期提醒（一次性） | 12-17 09:00 | 預估 12-24 到期，提醒 Andy 重產 IG／Threads 長效權杖並更新 GitHub Secrets（步驟要逐格附連結） |
| 社群自動發文（盤後主貼文） | GitHub Actions social-live，約 17:30～18:40 資料到齊就發（11-16 Andy） | 每天自動最多 2 則，現只開交易日盤後主貼文 1 則（`post_quota.json`） |

## 現役對話 ID（11-26 查）
主控 `session_018gakVURjPpCLn9AKajmD1E`｜① `session_018gakVTRUVZuXnGDLoyMk1p`｜② `session_018gakVRpyYeXzwbb6S5bBdm`（11-26 起，舊②`VSQo2n8d…` 已換）｜④ `session_018gakVR7b9oN9B5wv8q5xWf`。
註：`handoff/ceo_20261124.md` 寫的主控 4 個排程 ID 與 list_triggers 當前讀到的 ID 一致（trig_01QBQBB9、trig_012ZeWFP、trig_01PyLA4P、trig_011bT2M3），其餘 ID 請用 list_triggers 查，不要抄舊交接檔（舊檔的 trig_01CGDi…、trig_01D8eV… 等已停用）。
