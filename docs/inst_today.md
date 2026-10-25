# 當日三大法人買賣超（#market/inst）口徑

Andy 2026-10-20：「也需要在盤後提供當天即時的法人買賣超狀況」。市場明細新分頁「當日法人」，資料 `site/data/inst_today.json`，
由 `pipeline/compute/inst_today.py` 在 `build_payload` 產出，前端 `renderInstToday`（app.js）。

- **來源**：資料湖 `inst_daily`（證交所 OpenAPI／櫃買，單位「股」）。外資＝`foreign_total`（含外資自營商）、投信＝`trust`、自營商＝`dealer`（自行買賣＋避險）、合計＝`inst_total`；實測合計＝三者相加，誤差 0。
- **金額（元）**＝股數 × 當日收盤價，**估算**（沒有逐筆成交均價），與證交所公告金額會有小差距；前端說明「?」有寫。沒有收盤價的代號不進金額與排行，張數仍計入彙總。
- **日期**：法人表比價量晚出、上市上櫃分開落地（2026-10-19 盤後湖裡只有 148 檔）。取「涵蓋檔數 ≥ 近 10 日最多那天 60%」裡最新的一天（與 `inst_list_date` 同規則），日期寫進 payload 並標在標題；價量已更新而法人表未齊時，前端註明。
- **排行**依金額（張數會被低價股灌水），買超／賣超各前 10；含 ETF（證交所日報也含）。
- **社群截圖**：容器 `data-snap="inst-today"`，`window.TwSnapReady('inst-today')` 回 true 代表畫完（`data-ready="1"`）。
- 沒有新增功能開關（features.js）：所有人可看；若日後要分級再加 `mkt.inst`。

## 2026-10-20 第二版：三大法人買賣超日報（#market/inst，「法人連買賣」併入，舊網址 #market/streak 導向）
- **全市場金額（億元）以官方值為主**：新表 `inst_market_daily`（config.TABLES，key=date；欄位 `{foreign,trust,dealer,total}_{buy,sell}`，單位元），
  來源 FinMind `TaiwanStockTotalInstitutionalInvestors`（上市），解析在 `pipeline/sources/finmind.py::parse_market_institutional`；
  每日管線（run_daily，40 天增量）＋回補 5 年（`run_backfill.backfill_inst_market`，1 次額度，回空／402 不標 done）。
- **★ 2026-10-25 首次公布版優先**（DECISIONS #363）：FinMind 同一天晚間會把官方值換成含盤後成交的修訂版，跟新聞（證交所 15:00 公布值）對不上。
  另存 `inst_market_first`（先到的贏、只收台北當天抓到的最新日、帶 fetched_at），有首次版就用它，晚間版不同時放 `rev:{f,t,dl,tot}`。
- 官方值還沒進湖的日子，`compute/inst_market.py` 用 inst_daily×收盤價補，**只加總上市個股**（官方只有上市），每列 `est=True`，畫面標「估」。
  資料湖價量歷史較短，估算目前只涵蓋最近 ~23 個交易日；雲端回補官方值後長期間才會有資料，資料不足的期間鈕反灰。
- payload：`inst_market.json`（rows: d, f, t, dl, tot, tw, est；近 1300 個交易日）、`inst_today.json`（個股合計 `all`，供排行與族群篩選）。
- 期間鈕、百分位（近 252 個交易日、`≤今天值` 的比例）、累積（逐日相加）都在前端算。
