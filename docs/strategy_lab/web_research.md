# 網路研調：宣稱長期贏過 0050／加權指數的台股策略（2026-10-26）

查證規則：只有 WebSearch 可用，摘要是線索不是事實。「高信心」＝兩個以上獨立來源數字對得上；
同一平台（FinLab、TEJ、鉅亨）自家文章互相佐證不算獨立。結果：**沒有任何一條夠格標高信心**，
最多是「中」。原因：搜到的幾乎全是平台自家行銷回測、樣本內、多半沒寫成本。
範圍含 0050／00631L 正二／槓桿 ETF 搭配策略（Andy 追加地毯式搜索）。

## 一、先看反面證據（最重要）

| 發現 | 來源 | 說明 |
|---|---|---|
| FinLab 六個經典因子（低 PE、高 ROE 等）單獨回測，全部輸給含息 0050 | https://finlab.finance/tools/stock-selection | 2018-2026；0050 含息年化約 21~25% |
| 純低波動 18 年年化 4.9%，輸 0050 含息 14.8% | https://finlab.finance/blog/low-volatility-strategy | 與我方已試結果一致 |
| 純跟投信買超年化 9.7%（另一篇 7.4%），輸 0050 的 20.6% | https://finlab.finance/blog/institutional-strategy | 純籌碼單獨沒用 |
| 原版神奇公式台股 2014-2019 年化 9.61%、夏普 0.15 | https://medium.com/@zaoldyeck9970/量化價值投資台股實證-3b52dd4f1009 ；https://vocus.cc/article/636df64cfd897800010000c5 | 兩處都說原版在台股不好 |
| 政大論文：F-score 僅對市值前 100 大有效，半導體無效 | https://thesis.lib.nccu.edu.tw/ （H-SCORE 論文摘要） | 多空僅年資料勝大盤 |
| 「高券資比＝軋空」回測勝率低於大盤平均 | https://blog.wistock.ai/investment-strategies-stock-selection-techniques/short-ratio-30-warning-3yr-backtest-30-days-win-rate-40/ | 行銷文，無期間 |
| PEAD 在台灣近年減弱（2009-2021） | NCCU 論文摘要（thesis.lib.nccu.edu.tw 搜尋結果） | 短期弱化，長期仍在 |
| 0050 含息年化約 12.8%（2004 起）至 14.9%（2003 至 2026-09）；近 10 年約 21~25% | https://udn.com/news/story/123006/9355499 ；https://www.money101.com.tw/blog/0050-成分股-配息-年化報酬率 | 基準很高，期間要對齊 |
| 00631L 過去 10 年落在模擬分布第 98.5 百分位（極端順風），長期報酬中位數僅約 0050 的 1.4~1.5 倍，最差曾跌 83% | https://udn.com/news/story/123006/9696096 ；https://udn.com/news/story/123006/9696202 | 清流君十萬次模擬；兩篇同作者，算一源 |

結論：**單因子與單一籌碼都贏不了 0050；宣稱贏的，幾乎都是「多因子疊加」或「動能＋品質／營收確認」，
且是 10~25 檔、全樣本內。** 另一條路是「槓桿＋趨勢濾網」，宣稱報酬高但吃的是 2014 以來的台股單邊多頭。

## 二、個股策略清單

欄位：規則／宣稱／成本／樣本外／信心／資料湖能否回測／缺什麼。

### S1 FinLab 複合動能優化版（動能＋ROE＋營收確認）
- 網址：https://finlab.finance/strategies/composite-momentum
- 規則：12-1 價格動能排序；ROE>10、營收年增>0；季換股、前 10 檔（頁面平均 8.7 檔）。
- 宣稱：2013-09 至 2026-06 年化 36.4%、日夏普 1.18、MDD -40.1%；同期 0050 含息 20.9%、MDD -34.0%。
- 成本：FinLab 預設手續費＋證交稅（未見滑價）。樣本外：無。信心：**中低**。
- 資料湖：可（price_daily、financial_q、revenue_monthly）。缺：ROE 公告日對齊（避免前視）。

### S2 FinLab 月營收動能（近 3 月均營收>近 12 月均營收＋站上 20/60/120 日線）
- 網址：https://finlab.finance/blog/monthly-revenue-momentum
- 規則：動能最強前 10 檔，月營收公布後再平衡；流動性濾網版 48.6%、20 檔版 43.1%。
- 宣稱：2015-2026 年化 50.0%、日夏普 1.46、MDD -35.6%；0050 含息 21.3%。
- 成本：未明寫。樣本外：無。信心：**中低**（同站「月營收公告自動換股」29.12%、MDD -47.2%，口徑不一）。
- 學術佐證：顧廣平《營收創新高動能策略》（證券市場發展季刊 2022）持有 1~12 個月顯著正報酬
  https://www.airitilibrary.com/Common/Click_DOI?DOI=10.6529%2FRSFM.202206_34%282%29.0004 ；
  《產業營收動能策略》https://lawdata.com.tw/tw/detail.aspx?no=309163 。方向一致，無年化數字。
- 資料湖：可。缺：營收實際公告日。我們已試營收動能沒贏，差別在均線濾網＋10 檔集中，須驗是否前視。

### S3 FinLab 投信買超＋營收動能（新：籌碼＋基本面）
- 網址：https://finlab.finance/blog/institutional-strategy ；https://finlab.finance/blog/institutional-investors-comparison
- 規則：外資大賣後隔天、投信買超個股，疊月營收成長篩選；持有天數文中未取得。
- 宣稱：2015-2026 投信＋營收動能 33.9%（另一篇 30.1%），純投信 9.7%（或 7.4%），0050 含息 20.6%。
- 成本／樣本外：未見。信心：**低**（同站兩篇數字不同）。資料湖：可（inst_daily、revenue_monthly）。缺：讀原文確認規則。

### S4 FinLab 低波動優化版
- 網址：https://finlab.finance/strategies/low-volatility-optimized
- 規則：季換股前 15 檔；風險調整報酬因子為核心，疊 ROE、營收、動能。
- 宣稱：2013-09 至 2026-06 年化 33.3%、夏普 1.13、MDD -38.2%；0050 含息 20.9%。無樣本外。信心：**低**。資料湖：可。缺：門檻參數。

### S5 FinLab 四因子複合（ROE＋價格動能＋低波＋月營收年增）
- 網址：https://finlab.finance/tools/stock-selection ；https://finlab.finance/blog/multi-factor-stock-selection-beat-0050
- 規則：平均 25 檔；月換股。宣稱 2018-2026 日夏普 1.46 vs 0050 1.22、MDD -24.8% vs -33.96%；教學版年化 29.45%。
- **FinLab 自承年化沒贏 0050，贏在風險調整與回撤**。信心：**中**。資料湖：可。可當「風險調整勝」基準。

### S6 鉅亨易策略 高現金殖利率低估股（新）
- 網址：https://hao.cnyes.com/post/6482
- 規則：近 3 年平均現金殖利率>5%、股價淨值比<1（60 分）；近 5 日三大法人每日買超>0（40 分）；<60 分不買；前 5 名等金額、每年換股。
- 宣稱：10 年年化 21.02% vs 大盤 12.06%。成本／樣本外：無。信心：**低**（單一平台、僅 5 檔）。
- 資料湖：可（dividend、valuation_daily、inst_daily）。建議放寬到 20~30 檔重驗。

### S7 TEJ「基石價值」（O'Shaughnessy 台股化）
- 網址：https://www.tejwin.com/insight/james-oshaughnessy-基石價值策略-從大型收益股中發掘優質/
- 規則：上市櫃普通股排除金融業，六道量化篩選（大型、現金流充裕、估值合理），殖利率最高前 30 檔等權，每年 7 月初調倉。
- 宣稱：TEJ 量化月報第 25 期（2026-06）年化 25.67% vs 大盤 17.79%，MDD 與波動較低。信心：**低**（六道條件未讀到原文）。
- 資料湖：大致可。缺：六道條件原文（https://www.tejwin.com/news-category/tqnews/ ）。

### S8 zaoldyeck 神奇公式＋F-score＋營收／營業利益／現金流
- 網址：https://medium.com/@zaoldyeck9970/量化價值投資台股實證-3b52dd4f1009 ；https://vocus.cc/article/636df64cfd897800010000c5
- 規則：神奇公式前 10 檔、每季財報後再平衡；F-score≥8；再加月營收年增、營業利益年增、現金流。
- 宣稱：2014-05~2019-04 原版 9.61%；+F-score 20.62%；全加 25.09%（夏普 0.34），基準 0050。vocus 另版 GPA＋市值營收比前 30 名季調倉，標題「年賺 18%」（數字未確認）。
- 成本／樣本外：無；僅 5 年。信心：**低**。資料湖：可。缺：F-score 九項自算。

### S9 學術：價值（市值營收比）＋反向規模
- 網址：https://www.airitilibrary.com/Article/Detail/U0031-0207200917345163 ；https://fin.nkust.edu.tw/uploads/bulletin_file/file/5ee9dbaf1d41c865a300005e/ ；https://vocus.cc/article/63651ab4fd8978000199ebe8
- 發現：台股有價值溢酬與反向規模；價格比率中市值營收比最佳、PE 不好。無年化、無對 0050。信心：**中**（方向兩源一致）。
- 資料湖：可（valuation_daily、revenue_monthly）。

### S10 FinLab 法說會＋營收動能＋10% 停損
- 網址：https://finlab.finance/blog/investor-conference-revenue-momentum-strategy
- 績效在付費區未見；2018-2026 單樣本。反證：ATR 停損使動能策略年化 8% 變 -3.6%（https://finlab.finance/blog/atr-trailing-stop-tw-backtest）。信心：**低**。
- 資料湖：**不能**。缺：法說會日程（公開資訊觀測站）。

### S11 TEJ 鉅額交易策略
- 網址：https://www.tejwin.com/insight/tquant-lab-鉅額交易策略讓績效超越大盤/
- 規則：鉅額交易買進訊號＋關注度選股；含成本與流動性。宣稱優於加權指數，升息期回撤約 24% 歷時 1.5 年，年化未取得。信心：**低**。資料湖：**不能**（缺鉅額交易）。

### S12 TEJ 動能族（VAM 前 10、MAD、TW50 LTR）
- 網址：https://www.tejwin.com/insight/tquant-lab-動能策略/ 。年化未取得，與動能重疊。信心：**低**。資料湖：可。

### S13 0050／台灣 50 成分調整價格壓力（新：事件）
- 網址：政大碩論 104NCCU5305034 https://ndltd.ncl.edu.tw/cgi-bin/gs32/gsweb.cgi?o=dnclcdr&s=id%3D%22104NCCU5305034%22.&searchmode=basic ；編製說明 http://w3.uch.edu.tw/ylhsu/投資組合分析/講義/8.台灣50編製說明.pdf
- 發現：短期新增股顯著正、剔除股顯著負，之後反轉；投信於調整後加碼新增股。
- 規則可量化：3/6/9/12 月第二個週五審核，第三個週五後下一交易日生效；市值排名進前 40 納入、跌出 61 名剔除。
  交易：公告後買預期新增股、生效前賣；或剔除股反轉後買。無年化；樣本約 2015 以前。信心：**低**。
- 資料湖：部分可（etf_holdings、etf_holdings_monthly）。缺：歷史審核公告日、候補名單。MSCI 本輪無量化來源。

### S14 庫藏股宣告
- 網址：https://www.airitilibrary.com/Publication/Index/U0002-2505200601010600 ；https://ir.lib.nycu.edu.tw/handle/11536/140822 ；https://tdr.lib.ntu.edu.tw/handle/123456789/37766
- 發現：民國 89~95 年宣告日及隔日異常報酬顯著正，BHAR 長期顯著正；低 PB、非電子較強；台大研究買回後三年營運未改善。證據分歧。
- 規則：宣告次日買、持有 6~12 個月、偏低 PB。無年化。信心：**低**。資料湖：**不能**（缺庫藏股公告表）。

### S15 現金減資／增資
- 網址：https://ir.lib.ncu.edu.tw/bitstream/987654321/12376/1 ；https://irtest.lib.nccu.edu.tw/handle/140.119/30997
- 庫藏股減資、現金減資宣告日顯著正；彌補虧損減資顯著負；現增多為負。無年化。信心：**低**。資料湖：**不能**。

### S16 除權息／填息
- 網址：https://www.esunsec.com.tw/article/post/452 ；https://udn.com/news/story/7251/7575450
- **沒有找到宣稱贏 0050 的除權息策略**；高股息 ETF 長期輸市值型（2024-11~2025-11：0050 34.02% vs 00878 21.96%）。結論：可砍。資料湖：可（dividend_events）。負面結論信心：高。

### S17 投信季底作帳
- 網址：https://www.cmoney.tw/notes/note-detail.aspx?nid=95625 ；https://www.pocket.tw/school/articles/7586/
- 無正式回測，只有機制（偏中小型、季底前拉抬、結算後賣壓）。需自驗：季底前 10~20 日投信買超個股，持有至季底。資料湖：可。報酬無數字。

### S18 董監持股／千張大戶
- 網址：https://www.cmoney.tw/notes/note-detail.aspx?nid=14549
- 只有定性（董監改選行情：PB<0.9、董監持股<10%、小股本）。無回測。資料湖：insider_holding 可；shareholding_weekly 太短。

### S19 借券、融資券
- Wistock 稱高券資比勝率偏低；學術「券資比效應」https://www.airitilibrary.com/Publication/Index/U0002-2806202013545200 （僅題目）。借券本輪未找到量化策略。資料湖：margin_daily、sbl_daily 可驗。信心：低。

### S20 PEAD
- 網址：https://thesis.lib.nccu.edu.tw/detail/6342d21d6b6a22fffcd066d94cc8ff6d/ ；https://havingchien.substack.com/p/9d4
- 台灣存在但近年短期減弱，長期仍在；常見持有 1~3 月。無年化。資料湖：可（financial_q）。信心：低。

### S21 台指期：外資未平倉、選擇權、夜盤、當沖
- 網址：交大論文 https://ir.lib.nycu.edu.tw/handle/11536/71839 ；XQ 當沖回測 https://vocus.cc/article/659aa441fd89780001bfd36d ；夜盤制度 https://capfutures.com/taifex-day-vs-night/
- **沒有找到任何公開、可核對、贏過買進持有的台指期策略績效**。資料湖：fut_inst、fut_oi 可驗；選擇權 OI、夜盤、分 K 缺。建議自行拆「隔夜／日盤」報酬（TAIFEX 歷史資料）。

## 三、0050／00631L 正二／槓桿 ETF 搭配策略（追加）

資料注意：00631L 近期有股票分割（https://vocus.cc/article/6acc4d81fd89780001d866dd ），price_daily 要確認是否已還原；
有網站的 240 日均線值明顯錯誤（Win 投資頁），不可直接用第三方均線。00631L 2014 年才掛牌，樣本只有約 12 年。內扣費用約 1.04~1.17%（來源不同）。

### L1 Gayed「Leverage for the Long Run」：指數站上 200 日均線持有槓桿，跌破轉現金（或債）
- 網址：https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2741701 ；https://cmtassociation.org/wp-content/uploads/2025/08/2016-gayed-bilello.pdf ；https://paperswithbacktest.com/strategies/leverage-for-the-long-run-a-systematic-approach-to-managing-risk-and-magnifying-returns-in-stocks
- 規則：訊號指數收盤>200 日簡單均線→持有（2 倍）；否則現金。（美股，1928-2015 原論文）
- 宣稱：原論文 200 日擇時夏普 0.60 vs 買進持有 0.30；僅 49% 的 3 年滾動期絕對報酬勝，風險調整勝 69%。SSRN 擴充版 1988-2026：2 倍輪動 CAGR 14.00%、夏普 0.55、MDD -46.51%，基準 11.45%（含交易成本、收盤成交）。第三方 PapersWithBacktest 1990-2026：年化 12.24%、夏普 0.63、MDD -52.64%。
- 信心：**中**（學術原文＋第三方，數字略不同）。重點：贏在風險調整，絕對報酬優勢小。
- 資料湖：可（index_daily 加權指數、price_daily 的 0050／00631L；若 00631L 未還原則用日報酬 2 倍合成）。缺：還原價確認。**這就是我們「大盤濾網」的槓桿版，需明確區分測的是未槓桿還是槓桿。**

### L2 社群版：S&P 500 站上 200MA 持 00631L，跌破切回 0050
- 網址：https://www.threads.com/@meta.ai/post/DZrfx-JDUXu/ （轉述原文章，作者未明）
- 宣稱：年化 32.7%、MDD -37.8%（全程抱 00631L MDD -55.1%），收益保留約八成。
- 成本／樣本外：未見。信心：**低**（社群貼文，原文未取得）。資料湖：需 S&P 500 日線（intl_daily 可能有，待確認）。

### L3 加權指數 Range Filter(15,4) 決定持有 00631L 或空手
- 網址：https://github.com/EASON-237588/tw-trend-dashboard
- 宣稱：2000-2026 模擬正二年化約 23%（周邊參數平均約 19%）、最大回撤約 5 成，同期 0050 抱著約 10%。
- 樣本外：無，個人專案。信心：**低**。資料湖：可（需 2 倍合成）。屬趨勢濾網族，重疊。

### L4 00631L 與 0050 的 50:50 配置 + 再平衡（Chunkai）
- 網址：https://chunkai.blog/2024/05/13/leveraged-investing-backtest/
- 規則：以 00631L 取代一半 0050 曝險（等於 1.5 倍），股票漂移後（例 60:40）再平衡回 50:50；偏離門檻未取得。
- 宣稱 2014-10~2024-04：再平衡版年化 16.04%、波動 19.41%、MDD -29.19%；單買 0050 年化 10.1%、MDD -36.36%；未再平衡 50:50 年化 20.1%、MDD -45.28%、報酬 438.85%。
- 信心：**中低**（單一部落格，另一半是現金還是債未確認）。資料湖：可（price_daily）。缺：確認再平衡頻率。

### L5 00631L 長期持有／定期定額（基準，不是策略）
- 網址：https://vocus.cc/article/69c0ac42fd897800016ef25b ；https://leveragetw.com/0050-vs-00631l-investment-analysis-2026/ ；https://buffettonlineschool.com.tw/leveraged-etf/
- 宣稱：12 年年化 00631L 約 33.39%（BOS）至 38.6%，0050 約 18.5%；定期定額 2014-2026 最終 682 萬 vs 278 萬；近 5 年累積 303.6% vs 140%；MDD -55.1% vs -33.8%。
- 反證：清流君十萬次模擬，過去 10 年是第 98.5 百分位極端幸運。數字多源大致一致（高到中），但不能外推。
- 資料湖：可。**這條是 0050 要打敗的第二個基準。**

### L6 波動目標（目標波動率動態調整 0050／正二／現金比重）
- **本輪沒找到任何台股公開回測**（只有固定倍數）。元大說明書：00631L 每日重設 2 倍，並非波動目標。
- 規則（自擬、可回測）：目標年化波動 15~20%，槓桿＝目標/近 20~60 日實現波動，上限 2 倍、下限 0；週或月調整。學術依據為 Gayed 後續與 vol-managed portfolios 文獻（本輪未逐一核對）。信心：**無來源**。資料湖：可。

### L7 0050 加碼規則（季線乖離、跌 10% 加碼）
- 網址：https://www.cmoney.tw/forum/article/178845633 ；https://www.businesstoday.com.tw/article/category/183013/post/202610220035/ ；https://gist.github.com/shihyuho/646d078c9e973b9c3e9c82dfad9dc5f4
- 宣稱：季線乖離<-5% 加碼 2 倍、>10% 減碼：累積 282.7%→287.9%（幾乎沒差）；0050 拉回 10% 後單筆進場持有 1 年勝率 87%、平均 +20%（2003-2025，分析師引述）。
- 信心：**低到中**（兩源方向一致：效果小）。資料湖：可。

### L8 今周刊「0050、正2、現金這樣搭」
- 網址：https://www.businesstoday.com.tw/article/category/183013/post/202608270026/
- 摘要僅標題「比 0050 多賺 4 倍」，規則未取得。信心：**低**。需人工讀原文。

## 四、排序前 25 條（可回測 × 宣稱高 × 信心）

| # | 策略 | 宣稱 | 信心 | 資料湖回測 |
|---|---|---|---|---|
| 1 | L1 Gayed 200MA 槓桿輪動（0050／正二／現金） | 學術 CAGR 14.0% vs 11.45%，夏普 0.55 | 中 | 可 |
| 2 | S2 月營收動能＋均線 10 檔 | 年化 50%（2015-26） | 中低 | 可 |
| 3 | S1 動能＋ROE＋營收 | 36.4%（2013-26） | 中低 | 可 |
| 4 | L5 00631L 長期持有（基準） | 12 年年化 33~38% | 中 | 可 |
| 5 | L4 0050/00631L 50:50 再平衡 | 16%、MDD -29% | 中低 | 可 |
| 6 | L2 S&P 200MA 切 00631L/0050 | 32.7%、MDD -37.8% | 低 | 需美股線 |
| 7 | S3 投信買超＋營收動能 | 33.9% | 低 | 可 |
| 8 | S4 低波動優化版 | 33.3% | 低 | 可 |
| 9 | L3 Range Filter 持 00631L | 23% vs 0050 10% | 低 | 可 |
| 10 | S7 TEJ 基石價值 | 25.67% vs 17.79% | 低 | 大致可 |
| 11 | S8 神奇公式＋F-score＋營收 | 25.09% | 低 | 可 |
| 12 | S6 高殖利率＋PB<1＋法人買 | 21.02% vs 12.06% | 低 | 可 |
| 13 | S5 四因子複合（風險調整勝） | 夏普 1.46 vs 1.22 | 中 | 可 |
| 14 | S9 市值營收比價值 | 方向明確無年化 | 中 | 可 |
| 15 | L6 波動目標槓桿（自擬） | 無來源 | 無 | 可 |
| 16 | L7 0050 跌幅／乖離加碼 | 效果小 | 低中 | 可 |
| 17 | S13 台灣 50 調整價格壓力 | 短漲長反轉 | 低 | 部分 |
| 18 | S20 PEAD | 近年減弱 | 低 | 可 |
| 19 | S17 投信季底作帳 | 無數字 | 低 | 可 |
| 20 | S12 TEJ 動能族 | 無年化 | 低 | 可 |
| 21 | S14 庫藏股宣告 | 無年化 | 低 | 不能 |
| 22 | S11 鉅額交易 | 贏加權 | 低 | 不能 |
| 23 | S10 法說會＋營收＋停損 | 付費區 | 低 | 不能 |
| 24 | L8 今周刊 0050/正2/現金配置 | 「多賺 4 倍」 | 低 | 待讀原文 |
| 25 | S15 增減資事件 | 無年化 | 低 | 不能 |
（可砍：S16 除權息、S19 券資比軋空、S21 台指期當沖／缺口、S18 董監。）

## 五、建議

1. 先驗 L1／L4／L5：成本低、資料齊（價量即可），且**必須同時報「0050 含息」與「00631L 買進持有」兩個基準**，並用 2014 起（正二掛牌）與 2000 起（合成 2 倍）兩段，避免單邊多頭幻覺。
2. 個股優先複驗 S3、S6、S7、S8、S9（較新的組合）；S1、S2 必驗但要查營收／財報公告日前視。
3. 所有 FinLab／TEJ／鉅亨數字視為「宣稱」：全樣本、多數沒寫滑價；0050 含息 2018-2026 年化約 21~25%，門檻很高。FinLab 自承多因子絕對報酬沒贏 0050。
4. 需補資料（先找一手來源）：庫藏股買回公告、現金增減資、法說會日程、鉅額交易、台灣 50 歷史審核公告與候補名單、台指選擇權 OI、夜盤／分 K、00631L 還原價確認、S&P 500 日線。
5. 限制：WebSearch 只有摘要、無法開原文；S3 持有天數、S7 六道條件、S10 績效、L2／L4 原文細節都需人工讀原文。

## 六、查過的關鍵字（共 39 組）

低股價淨值比動能、Piotroski F-score 台股、投信作帳、除權息填息、月營收異常報酬、FinLab 勝大盤、0050 成分調整、
外資選擇權 OI、價值殖利率本益比實證、神奇公式台股、庫藏股長期報酬、董監持股千張大戶、融資融券券資比、PEAD 台灣、
TQuant Lab 績效、台指期當沖缺口、基石價值、vocus 台股神奇公式、鉅亨易策略規模與 F-score、殖利率前 20 檔年度換股、
zaoldyeck 台股實證、高現金殖利率低估股、鉅額交易、FinLab 月營收創新高、四因子複合、低波動優化、月營收動能 50%、
法說會策略、現金增資減資、台灣 50 價格壓力、台指期夜盤隔夜、投信買超策略、顧廣平營收動能、複合動能優化版、
00631L 均線切換、Gayed Leverage for the Long Run、00631L 再平衡股債、正二波動目標、PTT 正二長期持有、Mobile01 正二季線年線、
Chunkai 再平衡、季線年線擇時＋槓桿 ETF、0050 加碼回測。
三類來源：學術／論文（政大、中央、台大、交大、華藝、SSRN、CMT）、券商與媒體（永豐金、玉山、工商時報、經濟日報、鉅亨、今周刊、聯合）、
實務作者與平台（FinLab、TEJ、vocus、Medium、Wistock、CMoney、Chunkai、BOS、GitHub、Threads）。
PTT、Mobile01 本輪搜尋未直接回傳原帖，只有轉述整理站（pttstock.tw 等），標為低信心。
