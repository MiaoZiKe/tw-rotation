# 第 5 項：資料湖沒有的歷史資料，哪裡有合規來源（只查來源，這一輪沒有抓）

目的：現在大盤分數只有 2021-01 起的法人、期貨、資券，國際只有 2024-10 起。要含 2018 與 2020 崩盤、讓子項預測力檢驗有更多「空頭樣本」，需要往前補。
原則照 CLAUDE.md：不碰 `www.twse.com.tw/rwd/...`；只用公開資料集、FinMind、FRED 等已在白名單內或授權明確的來源。
搜尋摘要只能讀到片段，下表的「待確認」要在實際抓取前用小量請求驗證。

| 缺的資料 | 建議來源 | 依據（搜尋所得） | 起始日 | 授權／限制 | 狀態 |
|---|---|---|---|---|---|
| 三大法人現貨買賣超（全市場） | FinMind `TaiwanStockTotalInstitutionalInvestors`（專案已用同一組 API） | FinMind v4 API，bearer token，超額回 HTTP 402（finmindtrade.com/llms.txt、ithelp.ithome.com.tw/articles/10343838） | 待確認（資料湖現有表自 2021-01，已是一次 backfill 的結果；FinMind 一般可追到 2000 年代，需實測） | 免費額度；402 即停 | 待實測 |
| 融資融券（全市場） | FinMind `TaiwanStockTotalMarginPurchaseShortSale`（資料湖現有表即此來源） | 同上；搜尋未找到該資料集的起始日文件 | 待確認 | 同上 | 待實測 |
| 外資台指期未平倉 | ① 期交所「期貨市場三大法人－區分各期貨契約－依日期」開放資料（data.gov.tw/dataset/11596，政府資料開放授權條款第 1 版、免費、每日更新）② FinMind 期貨法人資料集 | 期交所網頁查詢只提供交易日前三年，更早要填「公開資料申購表」（taifex.com.tw/cht/9/tradersQATrading 與三大法人頁說明） | 約近 3 年（網頁）；更早需申購或 FinMind | 期交所頁面提醒引用時不要誤導市場；開放資料授權明確可用 | 可行；2018 之前需申購或改走 FinMind |
| VIX | FRED `VIXCLS`（專案已有 FRED_API_KEY，與 macro 表同一管道） | FRED 系列頁：CBOE 資料，自 1990-01 起每日，網站標示版權與建議引用格式（fred.stlouisfed.org/series/VIXCLS） | 1990-01 | 免費需 API key；引用需註明來源 CBOE／FRED | 最容易，只要把系列代號加進 macro 抓取清單 |
| SOX、美股指數長歷史 | Yahoo（專案已用 yfinance 抓 intl_daily，目前只回補到 2024-10） | 專案現況 | 可往前到 1990s | 以 yfinance 條款為準，僅研究用；與現有 intl_daily 同一條路徑 | 把回補起始日往前拉即可 |
| 重大事件日曆（FOMC、CPI、非農、財報季） | FRED release dates（專案已有 macro_calendar，只抓了未來日程）；FOMC 日程為聯準會公開網頁 | macro_calendar 現況 2026-06 起 | FRED release dates 可回溯 | 免費 | 可回補歷史發布日 |
| 重大訊息 | 公開資訊觀測站（MOPS）重大訊息 | 專案 material_news 僅 2026-09 起 | MOPS 可查歷史 | 需確認 MOPS 使用條款是否允許批次抓取；若不明，改人工整理事件日期 | 需先確認條款，這一輪不碰 |
| 族群成分的「當時版本」 | 本專案 groups.yaml 的 git 歷史 | 專案 git 第一個 commit 是 2026-09-10；GitHub API 可取各版本（本輪已取最早版放 `groups_history/`） | 2026-09-10 | 自有資料 | 歷史不夠深：2021～2025 沒有當時版本，只能用法定產業別（變動極小）當無事後偏誤的替代 |

建議的補資料順序：VIX（FRED，半小時）→ 事件日曆歷史發布日（FRED）→ SOX 回補（yfinance）→ 期貨法人（先用 FinMind 測起始日，不足再走期交所開放資料）→ 法人與融資券往前補。
