# 多圖連動普查（2026-10-19）

Andy 10-19：「圖表是有連動關係的，像這種同個資訊多張圖表，都需要有像是 ETF 月配那樣的連動效果」。規格：`docs/style_guide.md` 第十八節（照 `site/etfpage.js` comboLink）。

| # | 路由 | 區塊 | 程式 | 共用項目 | 難度 | 排程 |
|---|---|---|---|---|---|---|
| 1 | #stock（營收） | 營收走勢／逐年同月／月營收明細 | industry.js tabRevenue | 月份 | 低 | 第 3 批（等獲利一屏改完，同檔） |
| 2 | #stock（獲利） | 本益比每季／EPS 與三率／季報明細 | industry.js drawPeQ、profitChart | 季度 | 低 | 第 3 批 |
| 3 | #stock（法人／資券／大戶散戶） | 圖＋明細表 | industry.js instChart、marginChart、holderChart | 交易日／週 | 低 | 第 3 批 |
| 4 | #stock（除權息） | 各年度股利／除權息紀錄 | industry.js divBar | 年度 | 低 | 第 3 批 |
| 5 | #etf/inc（單檔） | 每月入帳長條＋清單＋膠囊 | etfpage.js drawSingleCurve、drawIncList | ETF | 低 | 第 2 批（等報酬比較改完，同檔） |
| 6 | #etf/inc（複利試算） | 回測走勢＋情境表 | etfpage.js drawCx | 情境 | 低 | 第 2 批 |
| 7 | #etf/list | 報酬比較 折線／長條／表 | etfpage.js drawRetCharts | ETF | — | 第 1 批（進行中） |
| 8 | #flow | 資金分流樹＋流向排名 | app.js renderSankey、sankeyRankDraw | 族群 | 中 | 第 1 批（進行中） |
| 9 | #flow | 足跡輪盤＋族群資金排行 | app.js renderRotClock、renderRankFlow | 族群 | 中 | 第 1 批（進行中） |
| 10 | #admin/traffic | 各頁次數＋占比 | admin.js allHtml、bindHover | 頁面 | 低 | 第 4 批 |
| 11 | #admin/traffic/頁 | 功能次數／對象（長條＋圓餅） | admin.js pageHtml | 功能 | 低 | 第 4 批 |
| 12 | #overview | 熱力圖＋迷你輪盤（相鄰兩張卡） | app.js renderHeat、renderRotClock | 族群 | 中高 | 跨卡，等 Andy 決定 |

已有連動不用做：ETF 月配組合、族群總覽漲跌長條＋甜甜圈、ETF 成分股甜甜圈＋持股表。

## 第二輪普查（同日）— 第一輪漏掉的

| # | 路由 | 區塊 | 程式 | 排程 |
|---|---|---|---|---|
| 13 | #market/ma | 站上均線走勢＋色票＋族群方格 | app.js | 第 5 批（市場頁） |
| 14 | #season（長條） | 長條＋色票＋族群下拉 | app.js | 第 5 批 |
| 15 | #market（漲跌分佈） | 分佈直條＋右側分頁表 | app.js | 第 5 批 |
| 16 | 手機 #stock 各分頁 | 柱狀圖＋每日表 | mobile3.js | 第 7 批（等個股桌機版） |
| 17 | #stock 各分頁 | HTML 圖例滑過亮線 | industry.js | 第 7 批 |
| 18 | #stock 四週期同看 | 四張小 K 線十字線同步 | industry.js | 第 7 批 |
| 19 | #industry/〈鏈〉 | 關聯圖＋右欄環節清單 | industry.js | 第 7 批 |
| 20 | #etf 行事曆 | 月曆格＋清單 | etfpage.js | 第 6 批（ETF＋財經日曆） |
| 21 | #etf 行事曆單檔 | 配息小圖＋明細表（補滑過） | etfpage.js、calgrid.js | 第 6 批 |
| 22 | #earnings | 月曆事件標籤＋本週重點 | earnings.js | 第 6 批 |
| 23 | 手機 #flow | 分流長條＋流向排名 | mobile3.js | 第 7 批 |
| 24 | #admin/traffic/stock | 三張卡跨卡互亮 | admin.js | 第 4 批（併入） |
