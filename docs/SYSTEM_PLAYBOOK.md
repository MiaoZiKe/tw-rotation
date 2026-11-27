# 系統做法與規範總索引（SYSTEM_PLAYBOOK）

> Andy 2026-11-26：「最重要的資產是如何做出整套系統，包含我說過要改的規範、影片製作方法規範」。新對話先讀本檔，照索引讀對應文件即可重建做法。
> 本索引只涵蓋 repo `MiaoZiKe/tw-rotation` 分支 `main`。ai-mp4（私有）見第 I 區與文末缺口。日期＝該檔最後一次 commit（git log -1 --format=%cs）。


## A. 入口與總規則（新對話第一批要讀）（13 份）

| 路徑（tw-rotation／main） | 管什麼 | 最後更新 |
|---|---|---|
| `CLAUDE.md` | 入口檔：專案目的、Andy 全部「★」硬規矩（繁體中文、不重疊、先推上線、回報格式、做完才停、關卡驗收…） | 2026-11-25 |
| `AGENTS.md` | 九個專家 Agent 與 CEO 分工、產出格式、審核清單 | 2026-11-23 |
| `HANDOFF.md` | 目前進度、已知 bug、下一步 | 2026-11-25 |
| `DECISIONS.md` | 已拍板決策編號清單，不得重議 | 2026-11-23 |
| `docs/confirm_ledger.md` | 唯一待辦／待確認帳本 | 2026-11-23 |
| `docs/delivery_log.md` | 交付紀錄 | 2026-11-23 |
| `docs/token_policy.md` | Token 政策（網站側） | 2026-11-23 |
| `README.md` | 專案說明 | 2026-11-23 |
| `ROADMAP.md` | 路線圖 | 2026-11-23 |
| `SETUP.md` | 初次安裝 | 2026-11-23 |
| `docs/BACKUP_RUNBOOK.md` | Andy 說「備份」時照做的流程 | 2026-11-23 |
| `docs/preview.md` | preview/<名稱> 預覽分支做法與網址 | 2026-11-23 |
| `docs/launch_standard.md` | 上架標準與上架前清單（Andy 說「上架」要逐條提醒） | 2026-11-23 |

## B. 網站系統與資料管線（51 份）

| 路徑（tw-rotation／main） | 管什麼 | 最後更新 |
|---|---|---|
| `docs/v3_sources_spec.md` | 資料源規格（合法來源白名單） | 2026-11-23 |
| `docs/source_whitelist_taifex_tpex.md` | 期交所逐筆／櫃買指數盤中：能不能進白名單（2026-09-26 查證） | 2026-11-23 |
| `docs/supply_chain_sources.md` | 供應鏈關係的原文來源（supply_chain.yaml edges[].source_url） | 2026-11-23 |
| `docs/supply_chain_suggest.md` | supply_chain.yaml 校訂紀錄（2026-09-19 查證版，**已套用**） | 2026-11-23 |
| `docs/feature_modules.md` | 27 塊功能積木與對應驗收段落 | 2026-11-23 |
| `docs/feature_notices.md` | 新功能公告（site/notices/features.json）規範 | 2026-11-23 |
| `docs/feature_proposals.md` | 每週新功能提案紀錄（Andy 點頭才做） | 2026-11-23 |
| `docs/product_strategy.md` | 產品策略：框架、優劣勢、定價與命名 | 2026-11-23 |
| `docs/compliance_and_tiers.md` | 合規與會員方案分級 | 2026-11-23 |
| `docs/perm_matrix_1008.md` | 全站會員權限矩陣（2026-10-08 版） | 2026-11-23 |
| `docs/quota_plan.md` | 每日額度與 Plus／Pro 方案（2026-10-07） | 2026-11-23 |
| `docs/quota_coverage.md` | 每日次數覆蓋稽核（2026-10-07） | 2026-11-23 |
| `docs/etf_holdings_source.md` | ETF 成分股與權重：資料來源查證與實測（2026-10-07 改寫） | 2026-11-23 |
| `docs/etf_page_spec.md` | ETF 專區規格（2026-10-05） | 2026-11-23 |
| `docs/futpages_rules.md` | 信用交易／期貨籌碼頁規則 | 2026-11-23 |
| `docs/gh_cron_setup.md` | 準時派工（Cloudflare Worker `tw-gh-cron`）設定步驟 | 2026-11-23 |
| `docs/daily_audit.md` | 每日三關稽核（daily_audit） | 2026-11-23 |
| `docs/perf_1007.md` | 開頁速度量測與優化（2026-10-07） | 2026-11-23 |
| `docs/realtime_5s.md` | 盤中即時改成每 5 秒（2026-09-29，DECISIONS #277） | 2026-11-23 |
| `docs/datagw_plan.md` | 付費資料閘道 data-gw：分級盤點與三階段計畫（2026-10-06，security-privacy） | 2026-11-23 |
| `docs/hosting_cost_plan.md` | 上架主機成本與備援規劃（2026-10-06，resource-auditor） | 2026-11-23 |
| `docs/security_review_1006.md` | 資安檢查與付費內容保護方案（2026-10-06，security-privacy） | 2026-11-23 |
| `docs/security/20261101_meta_token_refresh.md` | Meta（Threads／IG）長效權杖自動續期 —— 設計、比較與風險（2026-11-01） | 2026-11-23 |
| `docs/security/anti_freeload_rollout_1016.md` | 防白嫖「最小有效版本」：部署順序、回滾、擋得住與擋不住（2026-10-16） | 2026-11-23 |
| `docs/payment_admin_tabs_1016.md` | 管理區「付款與訂單」分頁關係與處理措施（2026-10-16） | 2026-11-23 |
| `docs/payment_audit_1012.md` | 付款與訂閱稽核報告 — 2026-10-12 | 2026-11-23 |
| `docs/payment_checkout_1011.md` | 結帳與付款（綠界＋銀行轉帳）— 2026-10-11 | 2026-11-23 |
| `docs/payment_newebpay_plan.md` | 藍新金流（NewebPay）串接規格：訂閱制會員（免費試用暫不提供） | 2026-11-23 |
| `docs/checkout_plan.md` | 訂閱付款（綠界信用卡定期定額）接法規劃 | 2026-11-23 |
| `docs/legal_payment_faq_1006.md` | 法遵與金流 FAQ（2026-10-06，回答 Andy 21:00 的問題） | 2026-11-23 |
| `docs/legal_refund_1009.md` | 退款與取消訂閱政策、法律頁現況盤點（2026-10-09） | 2026-11-23 |
| `docs/legal/20261101_subscription_signals.md` | 付費訂閱「族群埋伏／進出場訊號」法遵評估（2026-11-01） | 2026-11-23 |
| `docs/legal/realtime_redistribution.md` | 即時行情「中央抓一次、推給所有讀者」合不合規 —— 風險盤點與待確認清單 | 2026-11-23 |
| `docs/launch_checklist_1009.md` | 下週上線總清單（2026-10-09 晚，CEO 彙整） | 2026-11-23 |
| `docs/launch_gap_legal_1009.md` | 上線前法遵缺口盤點＋限期限次體驗＋行銷文案守則（2026-10-09） | 2026-11-23 |
| `docs/launch_gap_payment_1009.md` | 上線前金流缺口盤點＋限期限次體驗規格（2026-10-09） | 2026-11-23 |
| `docs/launch_gap_security_1009.md` | 上線前資安與營運缺口清單（2026-10-09，security-privacy） | 2026-11-23 |
| `docs/launch_roadmap.md` | 上架五大項（Andy 10-06 19:15 列出） | 2026-11-23 |
| `docs/commercialization_plan.md` | 商業化上架規劃（App ＋ 電腦版 ＋ 付費方案） | 2026-11-23 |
| `docs/app_store_plan.md` | 哩股哩股 上架 Google Play 與 App Store 計畫（2026-10-22 版） | 2026-11-23 |
| `docs/mobile_release_plan.md` | 手機 App 上架計畫：三條路的比較、費用、送審會卡在哪，以及今天已經做掉的第一步 | 2026-11-23 |
| `docs/codex/AGENTS.md` | Codex 接手說明 | 2026-11-23 |
| `docs/codex/SETUP.md` | Codex 接手說明 | 2026-11-23 |
| `docs/ai_office/chat_command_spec.md` | AI 辦公室聊天指令規格 | 2026-11-23 |
| `docs/tc/crosscheck_dcard_goodjob.md` | 科技透明圈：Dcard 與 GoodJob 交叉比對（2025-01 起） | 2026-11-23 |
| `docs/tc/dcard_id_calibration.md` | Dcard 文章編號 → 發文日期 校準表 | 2026-11-23 |
| `docs/tc/desktop_dcard_runbook.md` | 用 Claude 桌面版＋Andy 的 Chrome 讀 Dcard（科技透明圈補樣本） | 2026-11-23 |
| `docs/tc/legal.md` | 科技透明圈：薪資資料來源法遵盤點 | 2026-11-23 |
| `docs/tc/nicknames.md` | Dcard／PTT 公司代稱對照（只收 Andy 確認過或有公開來源的） | 2026-11-23 |
| `docs/tc/schema.md` | 科技透明圈 資料格式（site/tc/json/<產業id>.json） | 2026-11-23 |
| `docs/weekly/2026-W45.md` | 網站週報 | 2026-11-23 |

## C. 前端與 UI 規範（16 份）

| 路徑（tw-rotation／main） | 管什麼 | 最後更新 |
|---|---|---|
| `docs/andy_ui_rules.md` | Andy 全部介面修正條目（第〇節 17 條） | 2026-11-23 |
| `docs/style_guide.md` | 網站預設風格規範 | 2026-11-23 |
| `docs/chart_library.md` | 圖表庫 A～E 款（附 docs/chart_library/*.png） | 2026-11-23 |
| `docs/design_system_v2.md` | 設計系統 v2（Design System v2）：版面、字級、熱力圖、輪動時鐘、資金去向、同意條款與導覽 | 2026-11-23 |
| `docs/design_title_icons.md` | 卡片標題小圖示（設計系統的一節） | 2026-11-23 |
| `docs/mobile_ia.md` | 手機資訊架構：一屏可讀性稽核與改版（`docs/mobile_ia.md`） | 2026-11-23 |
| `docs/mobile_v2_plan.md` | 手機 v2 規劃（2026-10-08） | 2026-11-23 |
| `docs/mobile_v3_spec.md` | 手機版 v3：設計規格與可操作原型（`docs/mobile_v3_spec.md`） | 2026-11-23 |
| `docs/web_mobile_sync_1010.md` | 網頁版（>640）／手機版（≤640）同步稽核 —— 2026-10-10 | 2026-11-23 |
| `docs/ui_polish_spec.md` | 桌面版介面精修規格（UI Polish Spec） | 2026-11-23 |
| `docs/market_ia_1020.md` | 市場明細資訊架構重整（籌碼分類）— 2026-10-20 | 2026-11-23 |
| `docs/diagram_style_tech_v3.md` | 3D 科技模式 v3：色彩與細節規格（Andy 2026-09-22 提供的提示詞，整理成可實作的規格） | 2026-11-23 |
| `docs/diagram_3d_pbr_spec.md` | 3D 精緻化規格：從「灰、透明、扁平」到半寫實科技產品展示 | 2026-11-23 |
| `docs/diagram_purpose.md` | 產業鏈剖析圖是幹嘛的 —— 這一頁的目的（所有圖的最高指導原則） | 2026-11-23 |
| `docs/brand/theme_5c.md` | 全站色系改為 LOGO ⑤C（深藍＋銅紅＋暖白） | 2026-11-23 |
| `docs/logo_manual.md` | LOGO 手冊 | 2026-11-23 |

## D. 專家 Agent 與技能（.claude/）（51 份）

| 路徑（tw-rotation／main） | 管什麼 | 最後更新 |
|---|---|---|
| `.claude/agents/_README.md` | Agent 總覽 | 2026-11-23 |
| `.claude/agents/_RESEARCH_RULES.md` | 研究規矩：查證、來源、信心度 | 2026-11-23 |
| `.claude/agents/ai-server-analyst.md` | 你負責的環節 | 2026-11-23 |
| `.claude/agents/animation-director.md` | 動畫導演（動畫設計單位） | 2026-11-23 |
| `.claude/agents/art-director.md` | 你擁有 `--dg-*` | 2026-11-23 |
| `.claude/agents/bibi-animator.md` | 動畫師 | 2026-11-23 |
| `.claude/agents/bibi-efficiency.md` | bibi-efficiency.md | 2026-11-23 |
| `.claude/agents/bibi-illustrator.md` | 插圖設計師 | 2026-11-23 |
| `.claude/agents/bibi-interaction.md` | 互動工程師 | 2026-11-23 |
| `.claude/agents/bibi-planner.md` | 企劃師 | 2026-11-23 |
| `.claude/agents/bibi-review.md` | 獨立品管師 | 2026-11-23 |
| `.claude/agents/canvas-motion-engineer.md` | Canvas 數學動效前端工程師 | 2026-11-23 |
| `.claude/agents/content-planner.md` | 企劃師 | 2026-11-23 |
| `.claude/agents/data-scraper.md` | 開工前必讀 | 2026-11-23 |
| `.claude/agents/data-steward.md` | 這個專案真的發生過的事（你存在的理由） | 2026-11-23 |
| `.claude/agents/delivery-planner.md` | 一批需求進來，你固定做這四件事 | 2026-11-23 |
| `.claude/agents/deployer.md` | 你的職責邊界 | 2026-11-23 |
| `.claude/agents/efficiency-planner.md` | 你要回答的三個問題 | 2026-11-23 |
| `.claude/agents/finance-content-editor.md` | 財經內容編輯（社群媒體部） | 2026-11-23 |
| `.claude/agents/finance-quant.md` | 開工前必讀 | 2026-11-23 |
| `.claude/agents/frontend-ui.md` | 開工前必讀 | 2026-11-23 |
| `.claude/agents/healing-editor.md` | 談晴說礙總編輯（healing-editor） | 2026-11-25 |
| `.claude/agents/industry-analyst.md` | 開工前必讀 | 2026-11-23 |
| `.claude/agents/inspector.md` | 每次稽核的步驟 | 2026-11-23 |
| `.claude/agents/legal-compliance.md` | 法遵與風險 | 2026-11-23 |
| `.claude/agents/market-researcher.md` | 市場研調專家 | 2026-11-23 |
| `.claude/agents/marketing-strategist.md` | 行銷與商業策略 | 2026-11-23 |
| `.claude/agents/mechanical-engineer.md` | 規矩一：沒有規格書就不准開畫 | 2026-11-23 |
| `.claude/agents/mobile-release.md` | 手機 App 上架 | 2026-11-23 |
| `.claude/agents/mobile-ui.md` | 手機介面專家 | 2026-11-23 |
| `.claude/agents/motion-designer.md` | 動態設計師（動畫設計單位） | 2026-11-23 |
| `.claude/agents/payments-billing.md` | 金流與訂閱制 | 2026-11-23 |
| `.claude/agents/pcb-substrate-analyst.md` | 你負責的環節 | 2026-11-23 |
| `.claude/agents/product-design-lead.md` | 產品設計總監 | 2026-11-23 |
| `.claude/agents/resource-auditor.md` | 這個專案已知的浪費樣態（都是真的發生過的） | 2026-11-23 |
| `.claude/agents/reviewer.md` | 開工前必讀 | 2026-11-23 |
| `.claude/agents/security-privacy.md` | 資安與隱私 | 2026-11-23 |
| `.claude/agents/semi-chain-analyst.md` | 你負責的環節 | 2026-11-23 |
| `.claude/agents/smc-technical.md` | 開工前必讀 | 2026-11-23 |
| `.claude/agents/social-ops-lead.md` | 社群發文營運主管（social-ops-lead） | 2026-11-23 |
| `.claude/agents/storyboard-artist.md` | 分鏡師 | 2026-11-23 |
| `.claude/agents/strategy-backtest.md` | 紅線（違反就是重做，這幾條沒有商量餘地） | 2026-11-23 |
| `.claude/agents/tc-channel-lead.md` | 科技透明圈營運負責人（tc-channel-lead） | 2026-11-23 |
| `.claude/agents/tech-illustrator.md` | Andy 已經明講、現在還沒做到的（2026-09-15／16） | 2026-11-23 |
| `.claude/agents/video-editor.md` | 影片剪輯製作工程師 | 2026-11-23 |
| `.claude/agents/visual-designer.md` | 設計美編 | 2026-11-23 |
| `.claude/agents/visual-explainer.md` | 目前確定的缺口（ROADMAP 已列，接手直接做） | 2026-11-23 |
| `.claude/skills/caffaine-github-weekly/SKILL.md` | CaffAIne｜GitHub 每週熱門「資訊差」發文技能 | 2026-11-23 |
| `.claude/skills/design-to-motion/SKILL.md` | Design to Motion | 2026-11-23 |
| `.claude/skills/ig-threads-copy/SKILL.md` | IG／Threads 文案技能（開頭、去 AI 味、前 125 字、輪播、Reels） | 2026-11-23 |
| `.claude/skills/report-progress/SKILL.md` | 回報進度 | 2026-11-23 |

## E. 社群發文（跨頻道）（66 份）

| 路徑（tw-rotation／main） | 管什麼 | 最後更新 |
|---|---|---|
| `docs/marketing/channels/README.md` | 頻道總表、圖片規則、文案先讀 ig-threads-copy | 2026-11-23 |
| `docs/marketing/channels/accounts.md` | 各頻道社群帳號與 GitHub 密碼名稱對照（2026-11-09） | 2026-11-23 |
| `docs/marketing/channels/auto_post_all.md` | 全頻道自動發文總則 | 2026-11-23 |
| `docs/marketing/channels/article_standard.md` | 精選文章規範（所有頻道） | 2026-11-23 |
| `docs/marketing/channels/token_budget.md` | Token 預算與省用量規則 | 2026-11-25 |
| `docs/marketing/channels/model_effort.md` | 各頻道子 agent 的模型與 effort 搭配（2026-11-20 Andy：「好 照這樣做 並且每個頻道都是」） | 2026-11-23 |
| `docs/marketing/social_unit/ai_image_review.md` | AI 生圖審核清單與流程（美編把關，2026-10-28 第 1 版） | 2026-11-23 |
| `docs/marketing/social_unit/auto_post.md` | 自動發文格式（Auto Post）—— 以後一律照這份 | 2026-11-23 |
| `docs/marketing/social_unit/auto_reply.md` | 像真人一樣的自動回覆（頻道① @liguligu0818，Threads＋IG） | 2026-11-23 |
| `docs/marketing/social_unit/bio_1011.md` | IG／Threads 自我介紹（2026-10-11） | 2026-11-23 |
| `docs/marketing/social_unit/bio_1011_v2.md` | IG／Threads 自我介紹 v2（依市調改寫，取代 bio_1011.md 的推薦版） | 2026-11-23 |
| `docs/marketing/social_unit/bio_1011_v3.md` | IG／Threads 自我介紹 v3（Andy 10-11 定稿方向；取代 v1、v2 的推薦版） | 2026-11-23 |
| `docs/marketing/social_unit/bio_1011_v4.md` | IG／Threads 自我介紹 v4（✅ Andy 10-16 選定為定稿版） | 2026-11-23 |
| `docs/marketing/social_unit/caption_samples_1026.md` | 社群文案範例（盤前／盤中／盤後）2026-10-26 稿 | 2026-11-23 |
| `docs/marketing/social_unit/charter.md` | 社群媒體部章程（2026-10-11 成立） | 2026-11-23 |
| `docs/marketing/social_unit/comment_dm_plan.md` | 留言「消息」自動私訊方案（研究與規格，未實作） | 2026-11-23 |
| `docs/marketing/social_unit/commentary_guide.md` | 盤面解讀文案指南（盤中／盤後社群貼文） | 2026-11-23 |
| `docs/marketing/social_unit/content_calendar.md` | 內容日曆（社群媒體部） | 2026-11-23 |
| `docs/marketing/social_unit/cover_photo_review_20261029.md` | 封面實景照片審查紀錄（2026-10-29，Andy：「封面沒圖片需要添加」） | 2026-11-23 |
| `docs/marketing/social_unit/etf_title_formulas.md` | ETF 貼文標題公式（每週沿用） | 2026-11-23 |
| `docs/marketing/social_unit/event_caption_format.md` | 事件貼文文案格式（法說／總經／ETF）2026-10-28 第 1 版 | 2026-11-23 |
| `docs/marketing/social_unit/featured_articles_menu_1011.md` | 「精選文章」欄目與選單（產業鏈・供應鏈・產品） | 2026-11-23 |
| `docs/marketing/social_unit/free_ai_image_options.md` | 免費 AI 產圖方法比較（2026-10-28） | 2026-11-23 |
| `docs/marketing/social_unit/gpt_post_design_prompt.md` | 給 GPT 的社群貼文設計提示詞（2026-10-26，Andy：「GPT 對於貼文設計這塊有比較好的優勢，所以給我提示 | 2026-11-23 |
| `docs/marketing/social_unit/ig_growth_plan.md` | IG 熱度提升計畫（2026-11-01） | 2026-11-23 |
| `docs/marketing/social_unit/live_posts.md` | 盤中／盤後即時貼文（Threads＋IG 限動）：截圖、排版、排程 | 2026-11-23 |
| `docs/marketing/social_unit/live_posts_legal.md` | 盤中社群貼文（Threads／IG 限動）法遵盤點 | 2026-11-23 |
| `docs/marketing/social_unit/market_read_rules.md` | 盤中／盤後「盤面分析」判斷規則 | 2026-11-23 |
| `docs/marketing/social_unit/meta_api_setup.md` | Threads／IG 自動發布：Meta 串接設定（給 Andy，逐格照做） | 2026-11-23 |
| `docs/marketing/social_unit/meta_perm_check_1026.md` | Meta 權限檢查結果（2026-10-27 台北，工作流 meta_perm_check 第 1 次） | 2026-11-23 |
| `docs/marketing/social_unit/news_auto.md` | 新聞貼文自動排程（2026-10-28 第 1 版） | 2026-11-23 |
| `docs/marketing/social_unit/news_post_rules.md` | 新聞貼文標題與寫法規則（2026-10-28 第 1 版） | 2026-11-23 |
| `docs/marketing/social_unit/photo_lib_review.md` | 公司實景照片審核清單（art-director，2026-10-28 第 1 版） | 2026-11-23 |
| `docs/marketing/social_unit/post_design_system.md` | 哩股哩股社群貼文版型規範（盤前／盤中／盤後共用，2026-10-26 第 1 版） | 2026-11-23 |
| `docs/marketing/social_unit/post_layout_b_pro.md` | 頻道① 「B 專業版」貼文版型規格（v4，2026-11-04） | 2026-11-23 |
| `docs/marketing/social_unit/premarket_news_format.md` | 盤前消息資料格式（premarket_news） | 2026-11-23 |
| `docs/marketing/social_unit/premarket_read_rules.md` | 盤前貼文「盤面解讀」判斷規則 | 2026-11-23 |
| `docs/marketing/social_unit/research_bio_1011.md` | 簡介市調摘要（market-researcher，2026-10-11） | 2026-11-23 |
| `docs/marketing/social_unit/research_content_types_1011.md` | 高點閱財經／科技／產業內容類型研究（2026-10-11，台北時間） | 2026-11-23 |
| `docs/marketing/social_unit/style_reference_1012.md` | 文章風格參考帳號（Andy 10-12 指定） | 2026-11-23 |
| `docs/marketing/social_unit/threads_rules.md` | ★ 2026-11-09 Andy 定案：頻道①每日熱點文流程（沒回應也要發） | 2026-11-23 |
| `docs/marketing/social_unit/today_events_feed.md` | 「今日事件」資料串接可行性（2026-10-11 實測） | 2026-11-23 |
| `docs/marketing/social_unit/topic_auto_review_1029.md` | 主題文章每日自動：AI 圖審查紀錄與重疊檢查（2026-10-29） | 2026-11-23 |
| `docs/marketing/social_unit/topic_bank_1011.md` | 選題庫（第一批 4 週）2026-10-11 | 2026-11-23 |
| `docs/marketing/diagnosis_1109.md` | 11-09 流量診斷（Andy：「到底為何我完全沒流量？」） | 2026-11-23 |
| `docs/marketing/event_posts_1028.md` | 事件型貼文方案：法說解析、總經前後兩篇、ETF 週介紹（2026-10-28 第一版） | 2026-11-23 |
| `docs/marketing/feature_funnel_1027.md` | 功能引流規劃：從每日貼文導向網站各功能（2026-10-27） | 2026-11-23 |
| `docs/marketing/growth_command_1026.md` | 引流 → 註冊 → 付費：完整執行方案（2026-10-26，台北） | 2026-11-23 |
| `docs/marketing/growth_plan_1018.md` | 社群成長與發文規劃（2026-10-18） | 2026-11-23 |
| `docs/marketing/hot_posts_research_1028.md` | 熱門財經貼文研調（ETF 以外）— 2026-10-28 | 2026-11-23 |
| `docs/marketing/launch_posts_1009.md` | 上線第一週社群貼文（2026-10-09） | 2026-11-23 |
| `docs/marketing/research_growth_1026.md` | 成長研調補充：內容類型、轉換漏斗、業界基準、法規（2026-10-26，台北） | 2026-11-23 |
| `docs/marketing/salary_page_feasibility_1027.md` | 各公司／職位待遇統計頁 可行性評估（2026-10-27） | 2026-11-23 |
| `docs/marketing/social_setup_1009.md` | 社群上線清單（2026-10-09） | 2026-11-23 |
| `docs/marketing/style_research_1027.md` | 社群風格研調：哪種版型最受歡迎（2026-10-27） | 2026-11-23 |
| `docs/marketing/style_stats_1027.md` | 貼文格式統計（2026-10-27） | 2026-11-23 |
| `docs/marketing/tier_plan_1027.md` | 會員分級與註冊體驗重新規劃（2026-10-27） | 2026-11-23 |
| `docs/marketing/traffic_methods_1027.md` | 引流方法庫、爆文公式與每週選題簡報（2026-10-27，台北） | 2026-11-23 |
| `docs/marketing/traffic_plan_1109.md` | 頻道① 流量重整計畫（2026-11-09） | 2026-11-23 |
| `docs/marketing/trial_offer_1009.md` | 付費功能體驗方案提案（2026-10-09） | 2026-11-23 |
| `docs/marketing/tts_options_1027.md` | 免費、可客製化的旁白聲音選項（2026-10-27） | 2026-11-23 |
| `docs/social_handoff/README.md` | 社群交接（Claude 研究 → GitHub → GPT 製作） | 2026-11-23 |
| `docs/social_handoff/style/LIGULIGU_IG_Threads_Style_Guide.md` | 哩股哩股｜IG・Threads 編輯與視覺規範 | 2026-11-23 |
| `docs/social_handoff/style/README.md` | 視覺規範 | 2026-11-23 |
| `docs/marketing/channels/meta_app_golive_checklist.md` | Meta 應用程式「一次做完」清單（讓 IG 留言自動私訊對一般讀者也能用） | 2026-11-23 |
| `docs/marketing/channels/meta_inbox_automation_1120.md` | Meta Business Suite「留言自動私訊」設定表（2026-11-20） | 2026-11-23 |

## F-1. 頻道①哩股哩股（財經數據）（18 份）

| 路徑（tw-rotation／main） | 管什麼 | 最後更新 |
|---|---|---|
| `docs/marketing/channels/liguligu_scores.md` | 頻道① 哩股哩股「像不像 2008」8 頁輪播 審查（2026-11-16，獨立審查者） | 2026-11-23 |
| `docs/marketing/channels/stock/plan.md` | 頻道①「股票網站與投資數據」整合規劃（2026-11-03 台北，企劃師整理） | 2026-11-23 |
| `docs/marketing/weekly_review/2026-11-16.md` | 每週流量檢討 | 2026-11-23 |
| `docs/marketing/weekly_review/2026-11-23.md` | 每週流量檢討 | 2026-11-23 |
| `docs/marketing/news_weekly/2026-11-02.md` | 新聞貼文週報（2026-11-02） | 2026-11-23 |
| `docs/marketing/news_weekly/2026-11-09.md` | 新聞貼文週報（2026-11-09） | 2026-11-23 |
| `docs/marketing/news_weekly/2026-11-16.md` | 新聞貼文週報（2026-11-16） | 2026-11-23 |
| `docs/marketing/news_weekly/2026-11-23.md` | 新聞貼文週報（2026-11-23） | 2026-11-23 |
| `docs/articles/diagram_inventory.md` | 精選文章製作：fast_path、production_guide、visual_playbook、illus_style 等 | 2026-11-23 |
| `docs/articles/fast_path.md` | 精選文章製作：fast_path、production_guide、visual_playbook、illus_style 等 | 2026-11-23 |
| `docs/articles/illus_style.md` | 精選文章製作：fast_path、production_guide、visual_playbook、illus_style 等 | 2026-11-23 |
| `docs/articles/priority_3d.md` | 精選文章製作：fast_path、production_guide、visual_playbook、illus_style 等 | 2026-11-23 |
| `docs/articles/production_guide.md` | 精選文章製作：fast_path、production_guide、visual_playbook、illus_style 等 | 2026-11-23 |
| `docs/articles/quality_audit_1019.md` | 精選文章製作：fast_path、production_guide、visual_playbook、illus_style 等 | 2026-11-23 |
| `docs/articles/rework_queue.md` | 精選文章製作：fast_path、production_guide、visual_playbook、illus_style 等 | 2026-11-23 |
| `docs/articles/topic_gen.md` | 精選文章製作：fast_path、production_guide、visual_playbook、illus_style 等 | 2026-11-23 |
| `docs/articles/topic_research_1014.md` | 精選文章製作：fast_path、production_guide、visual_playbook、illus_style 等 | 2026-11-23 |
| `docs/articles/visual_playbook.md` | 精選文章製作：fast_path、production_guide、visual_playbook、illus_style 等 | 2026-11-23 |

## F-2. 頻道②科技透明圈（17 份）

| 路徑（tw-rotation／main） | 管什麼 | 最後更新 |
|---|---|---|
| `docs/marketing/channels/tc/andy_style.md` | ②規範：lessons(教訓)、andy_style、autopost、series_plan、schedule… | 2026-11-23 |
| `docs/marketing/channels/tc/autopost.md` | ②規範：lessons(教訓)、andy_style、autopost、series_plan、schedule… | 2026-11-23 |
| `docs/marketing/channels/tc/lessons.md` | ②規範：lessons(教訓)、andy_style、autopost、series_plan、schedule… | 2026-11-26 |
| `docs/marketing/channels/tc/meta_rules_1203_1211.md` | ②規範：lessons(教訓)、andy_style、autopost、series_plan、schedule… | 2026-11-26 |
| `docs/marketing/channels/tc/schedule_1203.md` | ②規範：lessons(教訓)、andy_style、autopost、series_plan、schedule… | 2026-11-26 |
| `docs/marketing/channels/tc/scores.md` | ②規範：lessons(教訓)、andy_style、autopost、series_plan、schedule… | 2026-11-23 |
| `docs/marketing/channels/tc/series2_gap_review.md` | ②規範：lessons(教訓)、andy_style、autopost、series_plan、schedule… | 2026-11-26 |
| `docs/marketing/channels/tc/series3_gap_review.md` | ②規範：lessons(教訓)、andy_style、autopost、series_plan、schedule… | 2026-11-26 |
| `docs/marketing/channels/tc/series4_upstream_plan.md` | ②規範：lessons(教訓)、andy_style、autopost、series_plan、schedule… | 2026-11-26 |
| `docs/marketing/channels/tc/series_plan.md` | ②規範：lessons(教訓)、andy_style、autopost、series_plan、schedule… | 2026-11-26 |
| `docs/marketing/channels/tc/token_log.md` | ②規範：lessons(教訓)、andy_style、autopost、series_plan、schedule… | 2026-11-25 |
| `docs/marketing/channels/tc/topic_tree.md` | ②規範：lessons(教訓)、andy_style、autopost、series_plan、schedule… | 2026-11-23 |
| `docs/marketing/channels/tc/weekly_plan.md` | ②規範：lessons(教訓)、andy_style、autopost、series_plan、schedule… | 2026-11-23 |
| `docs/marketing/channels/tech_transparency/plan.md` | 頻道②「科技透明圈」完整規劃（合併版） | 2026-11-23 |
| `docs/marketing/channels/video_logic.md` | 影片邏輯 | 2026-11-23 |
| `docs/marketing/channels/video_in_articles.md` | 文章內嵌影片規則 | 2026-11-23 |
| `docs/tech_articles.md` | 科技透明圈文章（隱藏分頁）怎麼新增一篇 | 2026-11-25 |
| `docs/marketing/channels/tc/video_rules.md` | ②影片規範摘要（tech-andy-fixes 第 1～20 條；原文在 ai-mp4 分支） | 2026-11-26 |
| `docs/marketing/channels/render_pipeline.md` | 渲染流程（render-chunks）、容器硬碟與成片存放、ai-mp4 分支地圖 | 2026-11-26 |

## F-3. 頻道③CaffAIne（11 份）

| 路徑（tw-rotation／main） | 管什麼 | 最後更新 |
|---|---|---|
| `docs/marketing/channels/ai_intro/content.md` | 頻道③「AI 介紹頻道」內容企劃（IG／Threads，台灣） | 2026-11-23 |
| `docs/marketing/channels/ai_intro/finance_rules.md` | AI 介紹頻道：財經內容守則 | 2026-11-23 |
| `docs/marketing/channels/ai_intro/legal.md` | AI 介紹頻道（IG／Threads）法遵規範 | 2026-11-23 |
| `docs/marketing/channels/ai_intro/ops.md` | 頻道③「AI 介紹頻道」發文營運規劃（草案，未啟用） | 2026-11-23 |
| `docs/marketing/channels/ai_intro/plan.md` | 頻道③「AI 介紹頻道」整合規劃（2026-11-04 台北，CEO 整合） | 2026-11-23 |
| `docs/marketing/channels/ai_intro/research.md` | 頻道③「AI 介紹頻道」市場研調（2026-11-03，台北時間） | 2026-11-23 |
| `docs/marketing/channels/ai_intro/strategy.md` | 頻道③「AI 介紹頻道」定位與變現策略（2026-11-03） | 2026-11-23 |
| `docs/marketing/channels/ai_intro/visual.md` | 頻道③「AI 介紹頻道」視覺版型規格（2026-11-03 第 1 版） | 2026-11-23 |
| `docs/marketing/channels/ai_intro/visual_review.md` | 頻道③「AI 介紹頻道」版型審查（視覺總監，2026-11-03） | 2026-11-23 |
| `docs/marketing/channels/caffaine/bio.md` | CaffAIne 自介（IG／Threads 共用） | 2026-11-23 |
| `docs/marketing/channels/caffaine/weekly/review_template.md` | AI 介紹頻道（caffaine.ai）週檢討（YYYY-MM-DD 當週，台北） | 2026-11-23 |
| `docs/marketing/channels/caffaine/ai_daily_playbook_index.md` | ③CaffAIne 製作手冊 §一～§三十索引（原文在 ai-mp4 分支 claude/caffaine-ai） | 2026-11-26 |

## F-4. 頻道④談晴說礙（healing）（34 份）

| 路徑（tw-rotation／main） | 管什麼 | 最後更新 |
|---|---|---|
| `docs/marketing/channels/healing/auto_post.md` | 頻道④「談晴說礙」自動發文（IG 輪播＋Threads 輪播；2026-11-15 起也能發影片：IG Reels＋Th | 2026-11-23 |
| `docs/marketing/channels/healing/comment_dm.md` | 談晴說礙：IG 留言自動私訊（讀主留言 → 查追蹤 → 私訊） | 2026-11-23 |
| `docs/marketing/channels/healing/content.md` | 頻道④「心靈雞湯／療癒」內容企劃（IG／Threads，台灣） | 2026-11-23 |
| `docs/marketing/channels/healing/content_gen2000.md` | 頻道④ 新方向「2000 後的我們」內容企劃（2026-11-04 台北，企劃師） | 2026-11-23 |
| `docs/marketing/channels/healing/eval_quote_accounts.md` | 評估：心情語錄帳號的爆紅做法，適不適合「日日小晴」（2026-11-06） | 2026-11-23 |
| `docs/marketing/channels/healing/examples.md` | 談晴說礙 影片範例庫（2026-11-20 起，Andy：「讓下次有範例參考以提升製作影片效率」） | 2026-11-23 |
| `docs/marketing/channels/healing/legal.md` | 心靈撫慰頻道（頻道④，IG／Threads）法遵規範 | 2026-11-23 |
| `docs/marketing/channels/healing/legal_gen2000.md` | 頻道④ 新版（2000 後無力感）法遵補充規範 | 2026-11-23 |
| `docs/marketing/channels/healing/naming_copywriter.md` | 頻道命名提案（文案總監版） | 2026-11-23 |
| `docs/marketing/channels/healing/naming_final.md` | 頻道④ 命名決選（2026-11-04 深夜，CEO 整合） | 2026-11-23 |
| `docs/marketing/channels/healing/naming_leisure.md` | 頻道④ 命名・悠閒版（2026-11-04，品牌命名顧問） | 2026-11-23 |
| `docs/marketing/channels/healing/naming_leisure_copy.md` | 生活頻道命名提案（悠閒版） | 2026-11-23 |
| `docs/marketing/channels/healing/naming_leisure_final.md` | 頻道④ 命名第五輪決選：悠閒版（2026-11-05 凌晨，CEO 整合） | 2026-11-23 |
| `docs/marketing/channels/healing/naming_pro.md` | 頻道④ 專業命名（第四輪，品牌命名顧問版，2026-11-04） | 2026-11-23 |
| `docs/marketing/channels/healing/naming_v2.md` | 頻道④ 名稱第二輪（2026-11-04 台北，行銷策略） | 2026-11-23 |
| `docs/marketing/channels/healing/naming_v3.md` | 頻道④ 名稱第三輪（2026-11-04 深夜，CEO） | 2026-11-23 |
| `docs/marketing/channels/healing/ops.md` | 頻道④「心靈雞湯／療癒」發文營運規劃（草案，未啟用） | 2026-11-23 |
| `docs/marketing/channels/healing/plan.md` | 頻道④「心靈雞湯」整合規劃書（2026-11-04 台北，CEO 整合） | 2026-11-23 |
| `docs/marketing/channels/healing/research_color.md` | 頻道④ 色調研調：6 種候選色調的證據（2026-11-04） | 2026-11-23 |
| `docs/marketing/channels/healing/research_gen2000.md` | 頻道④ 新方向：2000 後年輕人的「無力感」議題研調（買房、薪資、婚育、世代落差） | 2026-11-23 |
| `docs/marketing/channels/healing/research_ig.md` | 頻道④ 心靈療癒｜IG 市場研調 A（台灣與華語為主） | 2026-11-23 |
| `docs/marketing/channels/healing/research_threads_pain.md` | 頻道④ 心靈雞湯／療癒：Threads 現況與受眾痛點研調（B 組） | 2026-11-23 |
| `docs/marketing/channels/healing/research_web_money.md` | 頻道④ 心靈雞湯／療癒：網站、Podcast、YouTube、電子報、App 與變現方式研調（研調 C） | 2026-11-23 |
| `docs/marketing/channels/healing/scores.md` | 談晴說礙 每篇評分紀錄 | 2026-11-23 |
| `docs/marketing/channels/healing/strategy.md` | 頻道④「心靈雞湯／療癒」定位與變現策略（2026-11-04） | 2026-11-23 |
| `docs/marketing/channels/healing/strategy_gen2000.md` | 頻道④ 改版策略：2000 後的「無力感」頻道（2026-11-04） | 2026-11-23 |
| `docs/marketing/channels/healing/visual.md` | 頻道④「心靈雞湯／療癒」視覺規格（2026-11-04 第 1 版，美術總監） | 2026-11-23 |
| `docs/marketing/channels/healing/weekly/README.md` | 談晴說礙・每週優化（weekly/） | 2026-11-23 |
| `docs/marketing/channels/healing/weekly/template.md` | 談晴說礙・每週檢討 <yyyy>W<ww>（<起日>～<迄日>，台北時間） | 2026-11-23 |
| `docs/marketing/channels/healing/layouts/README.md` | 頻道④（療癒）版型樣張 | 2026-11-23 |
| `docs/marketing/channels/healing/layouts/art_review.md` | 版型樣張美術審查（2026-11-04，美術總監） | 2026-11-23 |
| `docs/marketing/channels/healing/templates_tqsa_v3/video/v9/ILLUSTRATIONS.md` | ④影片 v9 腳本格式與插畫規範 | 2026-11-23 |
| `docs/marketing/channels/healing/templates_tqsa_v3/video/v9/README.md` | ④影片 v9 腳本格式與插畫規範 | 2026-11-23 |
| `docs/marketing/channels/healing/templates_tqsa_v3/video/v9/SCRIPT_FORMAT.md` | ④影片 v9 腳本格式與插畫規範 | 2026-11-23 |
| `docs/marketing/channels/healing/video_rules.md` | ④影片規則 30～33 彙整＋影片工具與半成品現況 | 2026-11-26 |

## G. 影片製作（本 repo 內的規範）（17 份）

| 路徑（tw-rotation／main） | 管什麼 | 最後更新 |
|---|---|---|
| `docs/marketing/video_1010/bibi_host_spec.md` | 影片 v3/v4 腳本、版面規則(layout_rules 不重疊)、比比主持規格 | 2026-11-23 |
| `docs/marketing/video_1010/compliance_check.md` | 影片 v3/v4 腳本、版面規則(layout_rules 不重疊)、比比主持規格 | 2026-11-23 |
| `docs/marketing/video_1010/layout_rules.md` | 影片 v3/v4 腳本、版面規則(layout_rules 不重疊)、比比主持規格 | 2026-11-23 |
| `docs/marketing/video_1010/plan.md` | 影片 v3/v4 腳本、版面規則(layout_rules 不重疊)、比比主持規格 | 2026-11-23 |
| `docs/marketing/video_1010/posts.md` | 影片 v3/v4 腳本、版面規則(layout_rules 不重疊)、比比主持規格 | 2026-11-23 |
| `docs/marketing/video_1010/research.md` | 影片 v3/v4 腳本、版面規則(layout_rules 不重疊)、比比主持規格 | 2026-11-23 |
| `docs/marketing/video_1010/storyboard.md` | 影片 v3/v4 腳本、版面規則(layout_rules 不重疊)、比比主持規格 | 2026-11-23 |
| `docs/marketing/video_1010/storyboard_v3_mobile.md` | 影片 v3/v4 腳本、版面規則(layout_rules 不重疊)、比比主持規格 | 2026-11-23 |
| `docs/marketing/video_1010/storyboard_v3_web.md` | 影片 v3/v4 腳本、版面規則(layout_rules 不重疊)、比比主持規格 | 2026-11-23 |
| `docs/marketing/video_1010/storyboard_v4_mobile.md` | 影片 v3/v4 腳本、版面規則(layout_rules 不重疊)、比比主持規格 | 2026-11-23 |
| `docs/marketing/video_1010/storyboard_v4_web.md` | 影片 v3/v4 腳本、版面規則(layout_rules 不重疊)、比比主持規格 | 2026-11-23 |
| `docs/marketing/video_1010/v3_brief.md` | 影片 v3/v4 腳本、版面規則(layout_rules 不重疊)、比比主持規格 | 2026-11-23 |
| `docs/marketing/video_1010/v4_brief.md` | 影片 v3/v4 腳本、版面規則(layout_rules 不重疊)、比比主持規格 | 2026-11-23 |
| `docs/marketing/videos/video_rules_1018.md` | 影片規則 1018 | 2026-11-23 |
| `docs/marketing/video/script_1009.md` | 哩股哩股功能宣傳影片 腳本（2026-10-09） | 2026-11-23 |
| `docs/anim/README.md` | 動畫總說明 | 2026-11-23 |
| `docs/anim/bibi_library/index.md` | 比比素材庫總表 | 2026-11-23 |

## H. 組織與對話管理（12 份）

| 路徑（tw-rotation／main） | 管什麼 | 最後更新 |
|---|---|---|
| `docs/marketing/channels/handoff/ceo_20261122.md` | 主控與各頻道換對話交接檔（含最新規則） | 2026-11-23 |
| `docs/marketing/channels/handoff/ceo_20261124.md` | 主控與各頻道換對話交接檔（含最新規則） | 2026-11-24 |
| `docs/ops/token_saving.md` | 省 token 五條＋用量監工（Andy 11-27） | 2026-11-27 |
| `docs/marketing/channels/handoff/healing_20261127.md` | 頻道④換對話交接檔 | 2026-11-27 |
| `docs/marketing/channels/handoff/ch1_20261127.md` | 頻道①換對話交接檔 | 2026-11-27 |
| `docs/marketing/channels/handoff/ch1_20261122.md` | 主控與各頻道換對話交接檔（含最新規則） | 2026-11-23 |
| `docs/marketing/channels/handoff/ch1_20261124.md` | 主控與各頻道換對話交接檔（含最新規則） | 2026-11-24 |
| `docs/marketing/channels/handoff/ch2_20261123.md` | 主控與各頻道換對話交接檔（含最新規則） | 2026-11-23 |
| `docs/marketing/channels/handoff/ch2_20261124.md` | 主控與各頻道換對話交接檔（含最新規則） | 2026-11-24 |
| `docs/marketing/channels/handoff/ch2_20261125.md` | 主控與各頻道換對話交接檔（含最新規則） | 2026-11-25 |
| `docs/marketing/channels/handoff/ch3_20261124.md` | 主控與各頻道換對話交接檔（含最新規則） | 2026-11-24 |
| `docs/marketing/channels/handoff/ch4_20261123.md` | 主控與各頻道換對話交接檔（含最新規則） | 2026-11-23 |
| `docs/marketing/channels/schedules.md` | 全部排程清單（名稱、時間、目的、綁定對話） | 2026-11-26 |
## I. 影片製作全流程（腳本→配音→畫面→渲染→審片→存檔→發文）與 ai-mp4

影片的「做法」分散在三處，順序如下。本次盤點時 ai-mp4 無法連線（見文末說明），下列路徑取自 tw-rotation 交接檔與 CLAUDE.md，**尚未逐檔核對存在與日期**，標「待核」。

| 步驟 | 規範位置 | 狀態 |
|---|---|---|
| 腳本與開場（接上一集、3 秒問句、validate-three 開場銜接／鉤子） | ai-mp4 分支 `claude/nifty-goodall-syke8a-1548` 的 `docs/channels/tech-andy-fixes.md`（第 1～17 條）；本 repo `docs/marketing/channels/tc/lessons.md`（到 #86） | 待核 |
| 配音與節奏（atempo＝4.5÷原始語速、上限 1.12、每幕 ≥4.5 秒、捲舌處理、重配音先講原因） | 同上第 13～14 條；本 repo `docs/marketing/channels/video_logic.md` | 待核 |
| 畫面（物理、機台擬真、爆炸分解、專業度 ≥8＋雙審；畫面不可重疊） | tech-andy-fixes 第 15～17 條；本 repo `docs/marketing/video_1010/layout_rules.md` | 部分在本 repo |
| 渲染（一律 GitHub Actions 分段多台跑，不在容器跑） | ai-mp4 `main` 的 `.github/workflows/render-chunks.yml`、`scripts/three/make-tech.sh`、`scripts/three/push-render-assets.sh`；規矩本文在本 repo `CLAUDE.md`（2026-11-25 條） | 待核 |
| 審片（四道驗證：重疊、靜止、斷音爆音、聽感；美編 ≥7） | ai-mp4 `docs/reviews/*`；④ 規則 30～33 在 `.claude/agents/healing-editor.md` | 待核 |
| 存檔（成片不進 git；存 `renders/series2`、`renders/series2-1124` 分支） | ai-mp4 分支 `renders/*` | 待核 |
| 發文（佇列 draft → Andy 核准才 approved → channel_post.yml／tc_post.yml 發） | 本 repo `docs/marketing/channels/tc/autopost.md`、`healing/auto_post.md`、`social_unit/auto_post.md` | 已在本 repo |
| ③ CaffAIne 全部規則（§一～§三十） | ai-mp4 分支 `claude/caffaine-ai` 的 `docs/channels/ai-daily-playbook.md` | 待核，疑為只在功能分支 |
| ③ 前 5 新題 | ai-mp4 `docs/channels/caffaine-top5-1122.md` | 待核 |

## J. 組織與對話管理（重點摘要，原文在第 H 區）

- 主控（CEO）在最上層，四個頻道對話掛主控下；Andy 在主控下的指令＝所有頻道一起執行（先判斷哪些頻道適用，再 send_message 轉達）。
- 頻道順序（11-23）：②科技 → ③AI → ①哩股；④另依排程。
- 換新對話門檻 context 30 萬；新對話跑滿 24 小時才封存舊的（只封存不刪）。
- 排程：Token 每日 15:17、網站週報週六 10:23、資料維修監工平日 21:47、盤後發文監工平日 18:20（綁主控）；各頻道另有自己的排程。排程本身存在排程系統，不在 git。
- 省用量：子 agent 回報 ≤10 行、每支片最多再改 2 輪、只在完成或卡住時回報主控（`token_budget.md`）。

## 缺口（規範只在非 main 分支、只在交接檔、或只在排程／對話裡）

> 2026-11-26 歸檔：13 項中 11 項完整歸檔、第 13 項部分完成、第 8 項仍待處理。表中「原位置」保留，方便對照。

| # | 內容 | 原位置 | 狀態 |
|---|---|---|---|
| 1 | ② 影片規範第 1～17 條 | ai-mp4 分支 `claude/nifty-goodall-syke8a-1548` | **已歸檔→`docs/marketing/channels/tc/video_rules.md`**（摘要含第 1～20 條，原文路徑已註明；ai-mp4 分支本身未合併，依指示不合併） |
| 2 | ③ CaffAIne `ai-daily-playbook.md`（§一～§三十） | ai-mp4 分支 `claude/caffaine-ai` | **已歸檔→`docs/marketing/channels/caffaine/ai_daily_playbook_index.md`**（索引放 caffaine/，不是 ai_intro/，因 ai_intro 是另一個版型審查資料夾） |
| 3 | 渲染流程使用說明 | `ch2_20261125.md`、CLAUDE.md 一句話 | **已歸檔→`docs/marketing/channels/render_pipeline.md`** |
| 4 | 各頻道語速規定 | 交接檔 | **已歸檔→`docs/marketing/channels/video_logic.md`（新增「各頻道語速一覽」）** |
| 5 | 換新對話門檻 30 萬、跑滿 24 小時封存 | `ceo_20261124.md` | **已歸檔→`docs/marketing/channels/README.md`（新增「對話管理」）** |
| 6 | 主控與各頻道排程 | 排程系統、`ceo_20261124.md` | **已歸檔→`docs/marketing/channels/schedules.md`**（名稱、時間、目的；用 list_triggers 讀到，**未抄 prompt 全文**） |
| 7 | ④ 規則 30～33 | `healing-editor.md`、`ch4_20261123.md` | **已歸檔→`docs/marketing/channels/healing/video_rules.md`** |
| 8 | ④ 影片工具改動與 2 支半成品 | 分支 `wip/healing-1128-1129` | **仍待處理**（原因：要把工具檔另開分支併 main，屬程式碼改動，本次歸檔任務不改程式；現況與待辦已寫進 `healing/video_rules.md` 末節，11-27 07:30 的④排程會接續兩支片） |
| 9 | Meta 私訊自動化現況與 Andy 偏好 | `ch3_20261124.md` | **已歸檔→`docs/marketing/channels/meta_inbox_automation_1120.md`（新增「Andy 的偏好與現況」）** |
| 10 | 容器硬碟管理與成片不進 git 約定 | 交接檔 | **已歸檔→`docs/marketing/channels/render_pipeline.md` 第四節** |
| 11 | FB 追進度 | `ch2_20261125.md` | **已歸檔→`docs/marketing/channels/tc/autopost.md`（新增「FB 追進度」）** |
| 12 | 子 agent 回報格式、頻道訊息是資料 | `ch1_20261124.md`、`ch3_20261124.md` | **已歸檔→`AGENTS.md` 末節** |
| 13 | ai-mp4 的 CLAUDE.md、scripts 說明、各分支 docs | 未盤點 | **已部分歸檔→`render_pipeline.md` 第五節**（已連線核對 main、兩個 docs 分支與 renders/series2；其餘 10 個分支未逐一看內容，歸入下一次盤點） |

### 本次盤點的限制
- （2026-11-26 更新）ai-mp4 已可讀；本次已驗證 `claude/nifty-goodall-syke8a-1548`、`claude/caffaine-ai` 的檔案存在，與 main 的 `render-chunks.yml`。第 I 區各列的「待核」狀態尚未逐列改寫；其餘分支內容未核。
- 日期為 git 最後 commit 日；`docs/**/queue/`、`posts/`、`samples*/`、各 storyboard、logo 試作子資料夾、資料檔與程式碼不列入索引。
