# TradingView 功能解析與重建規格書（交易練習室用）

> 撰寫：2026-10-28（台北）｜用途：給前端重建「交易練習室」，排版一律照 `docs/style_guide.md`、`docs/andy_ui_rules.md`。

## 〇、資料來源與限制（請先讀）

1. **這個容器無法登入或操作 TradingView**，所以沒有「實際操作」；本文件不是實機操作紀錄。
2. **WebFetch 實測失敗**：`https://www.tradingview.com/pine-script-docs/concepts/strategies/` 回 `getaddrinfo ENOTFOUND`（網域不在本 session 允許清單）。要讀原文，需在雲端環境的網路設定把 `www.tradingview.com` 加進允許清單。
3. 因此資料只有三種：
   - **〔摘〕** WebSearch 的搜尋摘要（只讀到摘要，沒讀到原文）。
   - **〔知〕** 撰寫者對 Pine Script v5/v6 官方手冊與參考文件的既有知識（2026-06 之前的版本），**這次沒有重新讀原文核對**，函式簽名與預設值上線前要再對一次。
   - **〔圖〕** Andy 提供的三張截圖。
4. 每一節的標記說明這段資料是從哪裡來的；沒有標記的段落是**我們自己的重建設計**，不是 TradingView 的描述。

主要出處（都是只讀到搜尋摘要）：
- 策略測試器報表欄位：<https://in.tradingview.com/support/folders/43000587044/>、Performance Summary：<https://il.tradingview.com/support/solutions/43000681683-performance-summary-tab>、Overview：<https://fr.tradingview.com/support/solutions/43000681733/>、入門：<https://ru.tradingview.com/support/solutions/43000764138>
- 內建策略資料夾：<https://www.tradingview.com/support/folders/43000587406-built-in-strategies/>、Consecutive Up/Down：<https://in.tradingview.com/support/solutions/43000599836-consecutive-up-down-strategy/>、BarUpDn 解說（OANDA）：<https://www.oanda.jp/lab-education/tradingviewstrategy/strategy/tradingview_barupdn_strategy>
- Bar Replay：<https://www.tradingview.com/support/solutions/43000712747-bar-replay-how-and-why-to-test-a-strategy-in-the-past/>、Bar Magnifier：<https://ru.tradingview.com/support/solutions/43000669285/>、Bar Replay 教學：<https://chartwisehub.com/tradingview-bar-replay/>
- Pine Script 手冊（未能開啟）：<https://www.tradingview.com/pine-script-docs/>、參考：<https://www.tradingview.com/pine-script-reference/v6/>

## 我們資料湖現況（判斷「需要的資料」用）

| 需要 | 資料湖 | 說明 |
|---|---|---|
| 日 K（開高低收量） | ✅ `price_daily`、`index_daily` | 主力資料 |
| 60 分 K | ✅ `intraday_60m` | 可做多週期、Bar Magnifier 簡化版 |
| 1/5 分 K、逐筆 tick | ❌ | 盤中只有即時報價（不進湖），重播與 Bar Magnifier 只能做到 60 分 |
| 除權息 | ✅ `dividend`、`dividend_events` | 還原權值、買進持有報酬要用 |
| 法人、融資、集保 | ✅ `inst_daily`、`margin_daily`、`shareholding_weekly` | 可當策略條件（我們獨有，TradingView 沒有） |
| 現有前端零件 | `site/chart.js`（KInd 指標、lightweight-charts）、`site/drawtools.js`（繪圖） | 可直接延用 |

---

## 一、策略測試器（Strategy Tester）

### 1.1 是什麼
把策略腳本在歷史 K 線上跑一次「券商模擬器」（broker emulator），產出交易清單與績效報表。圖上同時畫出進出場箭頭與標籤。〔摘〕〔知〕

### 1.2 畫面元素（〔圖一〕）
- 頂列：日期區間（可選整段或自訂，Deep Backtesting）、帳戶幣別與初始資金（1M USD）、明細程度（Default detalization）、腳本執行狀態（Script execution）、設定齒輪、匯出。
- **Key stats 卡片列**：Total PnL（金額＋%）、Max drawdown（金額＋%）、Profitable trades（%＋勝/總筆數，例 38.02% 395/1039）、Profit factor（例 0.813）。
- **Performance 區**：累積損益曲線，可切換疊加「Buy and hold」「Trades excursions」「Run-ups and drawdowns」。
- 三個分頁：Overview／Performance Summary／List of Trades（新版另有 Risk/performance ratios 分頁，Sharpe、Sortino、Profit factor、Margin calls 放在那裡〔摘〕）。

### 1.3 Overview（概覽）〔摘〕〔知〕
- 權益曲線（Equity）：每筆交易平倉後的累積淨利，畫成折線／面積。
- 回撤（Drawdown）：權益距前高的落差，畫成倒掛柱。
- 買進持有（Buy & Hold）：同期第一根開盤買入、持有到最後的權益，當對照線。
- Trades excursions：每筆交易的最大有利（MFE／Run-up）與最大不利（MAE／Drawdown）幅度，以柱狀畫在每筆交易上。
- Run-ups and drawdowns：權益曲線上的連續上升段與回落段。

### 1.4 Performance Summary 欄位與口徑
每欄都分 **All／Long／Short** 三欄。口徑為〔知〕，上線前要對原文。

| 欄位 | 中文 | 口徑 |
|---|---|---|
| Net Profit | 淨利 | Gross Profit − Gross Loss（已扣手續費），另顯示佔初始資金 % |
| Gross Profit | 總獲利 | 所有獲利交易的損益加總 |
| Gross Loss | 總虧損 | 所有虧損交易的損益加總（取絕對值） |
| Max Run-up | 最大上漲 | 權益從波段低點到之後高點的最大增幅（金額與 %） |
| Max Drawdown | 最大回撤 | 權益從波段高點到之後低點的最大跌幅（含未平倉損益的盤中權益），金額與 % |
| Buy & Hold Return | 買進持有報酬 | (最後收盤 − 第一根開盤)/第一根開盤 × 用初始資金可買的數量 |
| Sharpe Ratio | 夏普值 | 以**月報酬**計：(月平均報酬 − 無風險利率)/月報酬標準差；無風險利率預設 2% 年化〔知，待核〕 |
| Sortino Ratio | 索提諾值 | 同上，分母改成只算下檔偏差 |
| Profit Factor | 獲利因子 | Gross Profit / Gross Loss |
| Max Contracts Held | 最大持有口數 | 同時持有的最大數量 |
| Open PL | 未平倉損益 | 最後一根 K 線收盤時持倉的浮動損益 |
| Commission Paid | 手續費合計 | 所有成交手續費加總 |
| Total Closed Trades | 已平倉交易數 | |
| Total Open Trades | 未平倉交易數 | |
| Number Winning / Losing Trades | 獲利／虧損筆數 | 損益 > 0 / < 0（= 0 算平手，另計 Even） |
| Percent Profitable | 勝率 | 獲利筆數 / 已平倉筆數 |
| Avg Trade | 平均每筆 | Net Profit / 已平倉筆數（金額與 %） |
| Avg Winning / Losing Trade | 平均獲利／虧損 | |
| Ratio Avg Win / Avg Loss | 盈虧比 | 平均獲利 / 平均虧損 |
| Largest Winning / Losing Trade | 最大單筆獲利／虧損 | 金額與 % |
| Avg # Bars in Trades | 平均持有 K 數 | 另分 Winning／Losing |
| Margin Calls | 追繳次數 | 有設保證金時 |

### 1.5 List of Trades（交易清單）〔知〕
每筆兩列（進場／出場）：交易編號、類型（Entry Long / Exit Long…）、訊號名稱（entry id / comment）、日期時間、價格、數量、損益（金額與 %）、Run-up、Drawdown、累積損益。可點列跳到圖上那根 K；可排序；可匯出 CSV。

### 1.6 Properties（屬性設定）〔知〕〔摘：Bar Magnifier〕
| 設定 | 選項 | 說明 |
|---|---|---|
| Initial capital | 數字 | 初始資金 |
| Base currency | 幣別 | |
| Order size | 固定數量（Contracts）／固定金額（Cash）／權益百分比（% of equity） | 每筆下單量 |
| Pyramiding | 0～N | 同方向最多加碼幾次；0 或 1 = 不加碼 |
| Commission | % / 每口固定 / 每筆固定 | 手續費 |
| Slippage | ticks | 市價與停損單的滑價 |
| Margin long / short | % | 保證金比例，觸發追繳 |
| Verify price for limit orders | ticks | 限價單要價格「穿過」幾個 tick 才算成交 |
| Recalculate | After order is filled／On every tick | 成交後當根再算一次；即時資料每個 tick 都算 |
| Fill orders | On bar close（收盤即成交）／Using standard OHLC（預設，用開高低收推演盤中路徑）／Using bar magnifier（用更小週期 K 推演，最多 20 萬根小週期 K〔摘〕） |
| 日期區間 | 全部／自訂（Deep Backtesting 可回測超出圖上載入的歷史） | |

**OHLC 推演規則**〔知〕：開盤離高點較近時，路徑假設為 開→高→低→收；離低點較近則 開→低→高→收。停損／停利在路徑上依序檢查。

### 1.7 圖上的交易標記〔圖一〕〔圖三〕
- 進場：藍色向上箭頭（多）／紅色向下箭頭（空），旁標訊號名（例 `BarUp`、`BarDn`）與數量（`+1`／`-1`）。
- 出場：標註出場名稱（例 `Close Position (Max intraday Loss)`）與該筆損益。
- 進出場之間可畫虛線連接。
- **我們網站要改成台股慣例：紅色＝多、綠色＝空**，或至少跟全站紅漲綠跌一致。

### 1.8 重建優先級
- **P0**：回測引擎（日 K、Standard OHLC 推演、市價／限價／停損）、Properties 中的初始資金／下單量三種／手續費（台股預設 0.1425% 買賣＋0.3% 證交稅，可折扣）／滑價／Pyramiding、Key stats 四張卡、權益曲線＋買進持有＋回撤、Performance Summary 全表（All/Long/Short）、List of Trades（點列跳 K）、圖上箭頭與標籤。
- **P1**：Sharpe／Sortino、Trades excursions、Run-ups and drawdowns、日期區間選擇、匯出 CSV、Bar Magnifier（用 60 分 K）、Verify price for limit。
- **P2**：保證金與追繳、Recalculate on every tick、Deep Backtesting、多幣別。
- **資料**：日 K ✅、60 分 K ✅、除權息 ✅（買進持有要用還原價）。

---

## 二、內建策略清單

出處：內建策略資料夾 <https://www.tradingview.com/support/folders/43000587406-built-in-strategies/>〔摘〕。邏輯與預設參數以〔知〕為主（來自官方內建原始碼的記憶），**只有 Consecutive Up/Down 與 BarUpDn 有讀到搜尋摘要對照**。上線前建議在 TradingView 的 Pine Editor「Open → Built-in」開原始碼逐支核對（Andy 端可做，或開放網域後我們讀）。

| 策略 | 進場 | 出場／反向 | 預設參數 | 依據 |
|---|---|---|---|---|
| BarUpDn | 收 > 開 且 開 > 前收 → 多（`BarUp`） | 收 < 開 且 開 < 前收 → 空（`BarDn`）；另有「Max intraday loss %」風控，觸發即全平（〔圖三〕標籤） | Max intraday loss = 1% | 〔摘〕OANDA、〔圖三〕、〔知〕 |
| Bollinger Bands Strategy | 收盤由下往上穿越下軌 → 掛停損買單於下軌 | 收盤由上往下穿越上軌 → 掛停損賣單於上軌；多空互翻 | length 20、mult 2.0、來源 close | 〔知〕 |
| Bollinger Bands Strategy directed | 同上，但可限定只做多或只做空 | 同上 | 同上＋方向 | 〔知〕 |
| ChannelBreakOut | 掛停損買單於前 N 根最高 | 掛停損賣單於前 N 根最低；多空互翻 | length 5 | 〔知〕 |
| Consecutive Up/Down | 連續 N 根收盤 > 前收 → 多 | 連續 M 根收盤 < 前收 → 空 | 3 / 3 | 〔摘〕官方頁 |
| Greedy | 跳空開高／開低後順勢進場，並在有利方向持續加碼（金字塔） | 反向訊號或停利 | 〔知，細節不確定，需核對原始碼〕 | — |
| InSide Bar | 內包 K（高 < 前高 且 低 > 前低）出現時：收 > 開 → 多；收 < 開 → 空 | 反向訊號 | 無 | 〔知〕 |
| Keltner Channels | 收盤穿越上通道 → 掛停損買單於當根高 | 穿越下通道 → 掛停損賣單於當根低 | length 20、mult 1.0、用 EMA、帶寬 True Range | 〔知〕 |
| MACD | 柱狀體（DIF−MACD）由負轉正 → 多 | 由正轉負 → 空 | 12/26/9 | 〔知〕 |
| Momentum | 動量（close − close[N]）> 0 且其一階變化 > 0 → 掛停損買單於高＋1 tick | 兩者 < 0 → 掛停損賣單於低−1 tick | length 12 | 〔知〕 |
| MovingAvg2Line Cross | 快 SMA 上穿慢 SMA → 多 | 下穿 → 空 | 9 / 18 | 〔知〕 |
| MovingAvg Cross | 收盤上穿 SMA（且確認 N 根）→ 多 | 下穿 → 空 | length 9、confirmBars 1 | 〔知〕 |
| OutSide Bar | 外包 K（高 > 前高 且 低 < 前低）：收 > 開 → 多；收 < 開 → 空 | 反向訊號 | 無 | 〔知〕 |
| Parabolic SAR | SAR 翻到價格下方 → 停損買單於 SAR | 翻到上方 → 停損賣單 | start 0.02、inc 0.02、max 0.2 | 〔知〕 |
| Pivot Extension | 出現樞紐低點（左右各 N 根）→ 多 | 樞紐高點 → 空 | left 4、right 2 | 〔知〕 |
| Pivot Reversal | 樞紐高點確認後掛停損買單於該高點＋1 tick | 樞紐低點掛停損賣單 | left 4、right 2 | 〔知〕 |
| Price Channel | 掛停損買單於前 N 根最高 | 前 N 根最低；與 ChannelBreakOut 類似，用 ta.highest/lowest[1] | length 20 | 〔知〕 |
| RSI Strategy | RSI 由下往上穿越超賣線 → 多 | 由上往下穿越超買線 → 空 | length 14、30/70 | 〔知〕 |
| Stochastic Slow | %K 上穿 %D 且 %K < 超賣 → 多 | %K 下穿 %D 且 %K > 超買 → 空 | 14,3,3、20/80（台股 KD 改 9,3,3） | 〔知〕 |
| Supertrend | Supertrend 方向翻多 → 多 | 翻空 → 空 | ATR 10、factor 3 | 〔知〕 |
| Technical Ratings | 技術評等綜合分（均線＋震盪指標）轉「買進」→ 多 | 轉「賣出」→ 空 | 依評等門檻 | 〔知，口徑複雜〕 |
| Volty Expan Close | 掛停損買單於 收 ＋ ATR(N)×k | 掛停損賣單於 收 − ATR×k | length 5、mult 0.75 | 〔知〕 |

**重建優先級**
- **P0**（8 支，邏輯簡單、口徑清楚、新手最常用）：MovingAvg2Line Cross、MovingAvg Cross、RSI、MACD、Bollinger Bands、Stochastic Slow（KD 9,3,3）、Supertrend、ChannelBreakOut／Price Channel。
- **P1**：BarUpDn、Consecutive Up/Down、InSide／OutSide Bar、Keltner、Momentum、Parabolic SAR、Pivot Reversal／Extension、Volty Expan Close。
- **P2**：Greedy、Technical Ratings、BB directed。
- **加碼（我們獨有）**：法人連買、融資減少＋價漲、集保大戶增加等籌碼策略。
- **資料**：全部只需日 K ✅；籌碼策略用 `inst_daily`／`margin_daily`／`shareholding_weekly` ✅。

---

## 三、Pine Script 寫策略

全節為〔知〕（Pine v5/v6 手冊與參考），原文未能開啟：<https://www.tradingview.com/pine-script-docs/>、<https://www.tradingview.com/pine-script-reference/v6/>。

### 3.1 strategy() 宣告
```pine
//@version=6
strategy("我的策略", overlay=true, initial_capital=1000000,
     default_qty_type=strategy.percent_of_equity, default_qty_value=10,
     pyramiding=0, commission_type=strategy.commission.percent, commission_value=0.1425,
     slippage=1, calc_on_order_fills=false, calc_on_every_tick=false,
     process_orders_on_close=false, use_bar_magnifier=false,
     close_entries_rule="FIFO", margin_long=100, margin_short=100)
```
`default_qty_type`：`strategy.fixed`／`strategy.cash`／`strategy.percent_of_equity`。這些參數就是 Properties 面板的預設值，使用者在面板改的會蓋掉。

### 3.2 下單函式
| 函式 | 用途 |
|---|---|
| `strategy.entry(id, direction, qty, limit, stop, comment)` | 進場；反向進場會先平掉反向倉位再開新倉；受 pyramiding 限制 |
| `strategy.order(id, direction, qty, limit, stop)` | 純下單，不自動反向、不受 pyramiding 限制 |
| `strategy.exit(id, from_entry, qty, qty_percent, profit, loss, limit, stop, trail_points, trail_offset, trail_price, comment)` | 停利／停損／移動停損；`profit`/`loss`/`trail_*` 單位是 tick，`limit`/`stop` 是價格 |
| `strategy.close(id, comment, qty_percent)` | 以市價平掉指定 entry |
| `strategy.close_all(comment)` | 全部平倉 |
| `strategy.cancel(id)` / `strategy.cancel_all()` | 取消未成交掛單 |
| `strategy.risk.max_intraday_loss(value, type)` | 單日最大虧損風控（BarUpDn 那個標籤的來源） |

**移動停損**：`trail_points`＝獲利達幾 tick 後啟動；`trail_offset`＝啟動後停損距最高價幾 tick。
**狀態變數**：`strategy.position_size`、`strategy.position_avg_price`、`strategy.equity`、`strategy.netprofit`、`strategy.opentrades`、`strategy.closedtrades`。

### 3.3 input.* 參數介面
`input.int`、`input.float`、`input.bool`、`input.string(options=[…])`、`input.source`、`input.timeframe`、`input.symbol`、`input.color`、`input.time`、`input.session`。參數 `title`、`minval`、`maxval`、`step`、`group`、`inline`、`tooltip`。所有 input 自動變成設定面板的 Inputs 分頁。

### 3.4 ta.* 常用函式
`ta.sma(src,n)`、`ta.ema`、`ta.rma`（Wilder）、`ta.rsi(src,n)`、`ta.macd(src,f,s,sig)`→[macd,signal,hist]、`ta.crossover(a,b)`、`ta.crossunder(a,b)`、`ta.cross`、`ta.highest(src,n)`、`ta.lowest`、`ta.atr(n)`、`ta.tr`、`ta.stoch(close,high,low,n)`（只回 %K，要自己 sma 平滑）、`ta.supertrend(factor, atrLen)`→[線, 方向]、`ta.bb(src,n,mult)`→[中,上,下]、`ta.kc`、`ta.sar`、`ta.mom`、`ta.change`、`ta.pivothigh/pivotlow(left,right)`、`ta.barssince`、`ta.valuewhen`。

### 3.5 request.security 跨週期
`request.security(symbol, timeframe, expression, lookahead=barmerge.lookahead_off)`。重點：要避免「偷看未來」，高週期值要用前一根已收盤的值（`expr[1]` 搭配 `lookahead_on`）。

### 3.6 編輯器流程（Pine Editor）〔知〕〔圖三：底部有 Pine Editor 分頁〕
新增（Open → New strategy 範本）→ 編寫 → **Save**（命名、存進 My scripts）→ **Add to chart**（編譯、錯誤列在下方 console）→ 圖上或 Strategy Tester 齒輪改參數 → 每次儲存產生版本，可在 version history 回看／還原 → 可 Publish 公開或保持私有。

### 3.7 我們網站可重建的最小子集（建議）
**不做完整 Pine 編譯器**（成本高、版權疑慮）。分兩層：

1. **P0：積木式策略編輯器**（不寫程式）：「條件 A〔指標/價〕〔上穿/下穿/大於/小於〕條件 B」用 AND/OR 組合，分成「多單進場／多單出場／空單進場／空單出場」四格，加停損 %、停利 %、移動停損 %、最長持有 N 天。存成 JSON。
2. **P1：迷你腳本語法（類 Pine 子集，JS 直譯）**：
```
// 交易練習室腳本 v1
策略("均線交叉", 資金=1000000, 下單=權益%10, 手續費=0.1425)
快 = 參數.整數("快線", 5)
慢 = 參數.整數("慢線", 20)
若 上穿(均線(收盤,快), 均線(收盤,慢)) 則 進場("多", 做多)
若 下穿(均線(收盤,快), 均線(收盤,慢)) 則 平倉("多")
出場("停損", 來源="多", 停損%=5, 停利%=10)
```
   同時接受英文別名（`strategy`、`input.int`、`ta.sma`、`ta.crossover`、`strategy.entry/exit/close`），讓會 Pine 的人能貼簡單策略。只支援：數值序列、`[n]` 取前值、算術與比較、if、上述 ta 函式、`entry/exit/close/close_all/cancel`。**不支援** 迴圈、陣列、`request.security`（P2 再加，只開放「日→週/月」）。
3. 指標計算一律重用 `site/chart.js` 的 `KInd`，跟 Python `pipeline/indicators.py` 口徑一致（KD 9,3,3 初始 50、RSI Wilder）。
4. 策略存放：登入會員存雲端（自選清單同一路徑），未登入存 localStorage；不進 repo。

**優先級**：P0 積木編輯器＋8 支內建策略可「另存為我的策略」；P1 迷你腳本、版本紀錄；P2 跨週期、分享策略。**資料**：日 K ✅、週月由日 K 合成 ✅。

---

## 四、K 線重播（Bar Replay）

### 4.1 功能〔摘〕
把圖表倒回過去某一天，K 線一根一根長出來，模擬當時看盤；可在重播中下單練習。重播中的委託透過 Paper Trading 等以重播價格成交〔摘：官方頁寫「訂單以即時資料執行」，原文脈絡未讀到，需核對〕。Renko、Kagi、Point & Figure 不支援。可重播的盤中歷史長度依付費方案而定。

### 4.2 操作〔知〕〔摘：chartwisehub 教學〕
- 頂列「Replay」鈕 → 進入選點模式，游標變成一條垂直剪刀線，點哪根 K 就從那裡開始（右邊全部隱藏）；也可「Select date」「Random bar」。
- 控制列：**選起點**、**播放／暫停**、**下一根（Forward，快捷鍵 Shift+→）**、**速度**（例如每秒 10 根 … 每 3 秒 1 根）、**更新週期**（以較小週期逐步長出當根）、**跳到即時（Jump to real-time）**、**離開重播**。
- 重播中可切換週期；繪圖工具照常可用。
- 策略在重播中只看到「已播出」的 K，Strategy Tester 隨播放即時更新。

### 4.3 重建優先級
- **P0**：日 K 重播（選起點：點圖／選日期／隨機）、播放／暫停／下一根／上一根（練習用，TradingView 沒有上一根，可作我們加值）、速度 5 段、跳到最新、離開；重播中隱藏未來 K、指標同步只算到當根；模擬下單（見第七節）；重播結束後出成績單（套用第一節報表）。
- **P1**：60 分 K 重播（`intraday_60m`）、重播中 Strategy Tester 即時更新、隱藏股票名稱的「盲測模式」（防止記得走勢）。
- **P2**：當根逐步長出（需要分 K，資料湖沒有）。
- **資料**：日 K ✅、60 分 ✅、1/5 分 K ❌。

---

## 五、指標／策略／型態選擇視窗

### 5.1 畫面〔圖二〕
標題「Indicators, metrics, and strategies」。上方搜尋框；左側分類：Favorites（我的最愛）、My scripts（我的腳本）、Purchased（已購買）、Technicals（技術）、Fundamentals（基本面）、Editors' picks（編輯精選）、Top、Trending、Marketplace；上方分頁 Indicators／Strategies／Profiles（成交量分布）／Patterns（K 線型態）；下方為清單，每列可點星號加入最愛，點名稱直接加到圖上（可重複加，視窗不關）。

### 5.2 設定面板〔知〕
雙擊圖上的指標名或點齒輪：
- **Inputs**：input.* 產生的參數。
- **Properties**（只有策略）：第一節 1.6 的全部欄位。
- **Style**：每條線的顏色、粗細、樣式、顯示與否、精度、標籤顯示。
- **Visibility**：在哪些週期顯示（秒／分／時／日／週／月各自勾選與範圍）。
- 下方：Defaults（重設為預設／另存為預設）、Cancel、OK。

### 5.3 重建優先級
- **P0**：搜尋＋分頁（指標／策略）＋分類（我的最愛、我的策略、技術指標、內建策略、籌碼〔我們獨有〕）、點了加到圖、星號最愛（localStorage／會員雲端）；設定面板 Inputs＋Properties＋Style（顏色、粗細）。
- **P1**：Visibility、存為預設、型態（K 線型態辨識：吞噬、十字、鎚子）。
- **P2**：社群（Community）分享、Profiles。
- **資料**：不需要新資料 ✅。

---

## 六、圖表其他功能（依「交易練習室」重要性排序）

| 順序 | 功能 | 說明 | 依據 | 優先 | 資料 |
|---|---|---|---|---|---|
| 1 | 期間鈕 | 1D 5D 1M 3M 6M YTD 1Y 5Y All〔圖三〕；按了圖表縮放到該區間，**一定要真的生效**（andy_ui_rules 退件項） | 〔圖〕 | P0 | ✅ |
| 2 | 週期切換 | 日／週／月（60 分） | 〔知〕 | P0 | 日 ✅、60 分 ✅ |
| 3 | 圖表類型 | K 線、平均 K（Heikin Ashi：收=(O+H+L+C)/4、開=(前開+前收)/2）、線圖、面積 | 〔知〕 | P0（K、線）P1（平均 K） | ✅ |
| 4 | 繪圖工具 | 趨勢線、水平線、矩形、費波那契回撤（0/23.6/38.2/50/61.8/78.6/100%）；可選取、拖曳、刪除、鎖定 | 〔知〕 | P0（延用 `site/drawtools.js`） | ✅ |
| 5 | 警示 Alert | 價格穿越、指標條件、策略訊號；觸發一次／每次；通知方式 | 〔知〕 | P2（練習室用不到，重播中可做「到價提醒」P1） | 盤中報價 |
| 6 | 比較商品 | 疊加另一檔或加權指數，以 % 正規化 | 〔知〕 | P1 | ✅ `index_daily` |
| 7 | 多圖版面 | 1／2／4 格，同步商品、週期、十字線 | 〔知〕 | P2 | ✅ |

---

## 七、Paper Trading 模擬交易

### 7.1 功能〔知〕〔圖三：底部 Trading Panel〕
連線「Paper Trading」虛擬券商後，底部 Trading Panel 顯示帳戶與委託；圖上右側有買／賣快捷鈕，委託與持倉以水平線畫在圖上，可拖曳改價。

- **下單類型**：市價（Market）、限價（Limit）、停損（Stop）、停損限價（Stop Limit）；附帶停利／停損（Bracket：Take Profit／Stop Loss）。
- **委託單欄位**：商品、方向、數量、價格、有效期（當日／GTC）。
- **面板分頁**：Positions（持倉：商品、方向、數量、均價、現價、未實現損益）、Orders（委託：未成交可改可刪）、History（成交紀錄）、Account Summary（帳戶：初始資金、權益、可用資金、已實現／未實現損益）、Journal（操作日誌）。
- 可重設帳戶與初始資金。

### 7.2 重建（台股化）
- **P0**：重播中下單：市價（下一根開盤成交，避免偷看）、限價、停損；張／股切換；手續費＋證交稅；持倉、委託、成交紀錄、帳戶四塊；圖上畫委託線與持倉均價線；重設帳戶。
- **P1**：Bracket 停利停損一鍵掛、拖曳委託線改價、漲跌停限制（±10%）、操作日誌與每筆交易的「當時想法」筆記。
- **P2**：盤中即時模擬（用 `mis` 即時報價，不進湖）、融資融券、當沖。
- **資料**：日 K ✅、60 分 ✅；即時報價走既有 `live.js`。
- ⚠ 個人模擬損益只存使用者瀏覽器或會員雲端，**絕不進 repo**（CLAUDE.md 絕對不做第 5 條）。

---

## 八、查不到／未核實清單

1. 所有 TradingView 官方頁面與 Pine 手冊**原文都沒讀到**（網域被擋），只有搜尋摘要。
2. Sharpe／Sortino 的確切口徑（月報酬或日報酬、無風險利率預設值）未核實。
3. Max Run-up、Max Drawdown 是否含盤中浮動權益，未核實。
4. 內建策略中 **Greedy、Technical Ratings** 的完整邏輯沒有找到公開原始碼；其餘策略的預設參數來自記憶，需逐支開原始碼核對。
5. Bar Replay 中「訂單以即時資料執行」的確切意思（摘要原句）、重播速度的精確段數，未核實。
6. 2025～2026 年 Strategy Tester 改版後的分頁名稱（〔圖一〕已是新版卡片式介面，與舊版三分頁不同），以截圖為準。
7. 解法：在雲端環境網路設定允許 `www.tradingview.com`，即可補讀原文並把〔知〕改成有出處。
