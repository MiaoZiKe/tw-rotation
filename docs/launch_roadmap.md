# 上架五大項（Andy 10-06 19:15 列出）

| # | 大項 | 誰 | 狀態 | 卡在誰 |
|---|---|---|---|---|
| 1 | 金流：串接藍新金流（訂閱制＋1 個月試用） | payments-billing（規格）→ 實作 | 規格完成（約 9～13 工作天）`docs/payment_newebpay_plan.md` | Andy 申請藍新商店帳號 |
| 2 | 架設新伺服器（搬 Cloudflare Pages＋付費方案＋自有網域） | deployer | 雙部署進行中；費用見 `docs/hosting_cost_plan.md` | Andy：Cloudflare 付費方案、用量通知、網域、Google OAuth 網域 |
| 3 | 社群＋Logo | **Andy 自己處理** | — | — |
| 4 | 資安 | security-privacy | F12 註解移除已上線（19:15）；付費內容保護三階段完成（分支 claude/data-gw，等上架前切換）；清單 `docs/security_review_1006.md` | Andy：三帳號兩步驟驗證、repo 改 private（搬完後） |
| 5 | 全站備份（避免遺失） | efficiency-planner | 筆電監控＋每日備份腳本施工；會員資料匯出規格 | Andy：在筆電執行安裝、選雲端備份（Google Drive 或 R2） |

收費上線前必須全部完成：1、2、4（data-gw）、5（含會員資料備份）。
