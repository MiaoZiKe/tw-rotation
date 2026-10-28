/* ============================================================================
   交易練習室：10 組「標準策略」定義（2026-10-29 建）
   同一份定義三處共用：
     ① 自訂策略頁的「標準策略範本」（lab/custom.js）：點一下載入腳本與積木，直接回測；
     ② 產生預設回測結果的腳本（scripts/gen_standard_strategies.js → lab/standard_results.json）；
     ③ 驗收（tests/lab_standard_check.js）。
   鐵則：參數是「教科書預設值」，事前定好、不看回測結果調參；結果不好就照實寫（Andy：結果不好不准調參數湊）。
   成交一律「訊號收盤後產生 → 下一根開盤成交」（引擎預設，不可改）。
   每組都有「積木」與「腳本」兩種寫法的就必須等價（tests/lab_standard_check.js 逐組比對訊號）；
   只有腳本才寫得出來的（Supertrend、週均線、連買連賣跨門檻）標 blocks:null。
   ============================================================================ */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.LabStandard = factory();
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  const N = (v) => ({ t: 'num', v });
  const S = (t, o) => Object.assign({ t }, o || {});

  const DEFS = [
    {
      id: 'std_ma', no: 1, group: '趨勢', name: '雙均線 20/60 黃金交叉',
      tagline: '20 日均線上穿 60 日均線進場、下穿出場，只做多。',
      applies: '加權指數、大型權值股、ETF（趨勢明顯、流動性好的標的）；不適合長期盤整的股票',
      script: [
        '策略("雙均線 20/60")',
        '快 = 參數("快線週期", 20)',
        '慢 = 參數("慢線週期", 60)',
        '停損值 = 參數("停損 %", 10)',
        '若 crossover(sma(close,快), sma(close,慢)) 則 進場("多")',
        '若 crossunder(sma(close,快), sma(close,慢)) 則 平倉("多")',
        '出場("風控", 停損%=停損值)'].join('\n'),
      blocks: { le: { join: 'and', rows: [['up', S('sma', { n: 20 }), S('sma', { n: 60 })]] }, lx: { join: 'and', rows: [['dn', S('sma', { n: 20 }), S('sma', { n: 60 })]] } },
      risk: { sl: 10, tp: 0, trail: 0, maxbars: 0 },
      rules: { entry: '收盤後，20 日均線由下往上穿過 60 日均線（今天 20MA > 60MA 且昨天 20MA ≤ 60MA）→ 下一個交易日開盤買進。',
        exit: '收盤後，20 日均線由上往下穿過 60 日均線 → 下一個交易日開盤賣出。', stop: '進場價下跌 10% 以盤中價觸及停損（跳空則以開盤價）。', tp: '不設停利（讓獲利跑到均線反向為止）。',
        size: '全部資金（100%）、單一標的、不加碼、最多 1 檔。', params: '快線 20 日、慢線 60 日、停損 10%' },
      why: '最古老的趨勢跟隨：價格走出長趨勢時，短均線會先轉向。20/60 對應約一個月與一季，是台股最常見的中期組合。優點是規則單純、一眼看得懂；缺點是每次轉向都慢半拍，盤整時反覆被洗。',
      source: 'Brock、Lakonishok、LeBaron（1992）《Simple Technical Trading Rules and the Stochastic Properties of Stock Returns》，Journal of Finance；均線交叉是技術分析的基本款。',
      evidence: '站內前期研究（docs/futures_lab）：台指期 MA 家族樣本外年化 5.4%，輸同期 0050 14 個百分點；均線系統的價值是少吃回撤，不是多賺。',
      fail: '長期橫盤（均線糾纏、每個月都假突破）、V 型急殺急彈（出場太慢、進場更慢）、單日跳空跌破（停損跳空成交價比設定更差）。',
      headline: { sym: 'TAIEX', tf: 'D' }, syms: ['TAIEX', 'TX', '2330', '2317', '3037', '2881', '2603'], tfs: ['D', 'W', '60'], needs: null,
    },
    {
      id: 'std_macd', no: 2, group: '趨勢', name: 'MACD 零軸上黃金交叉',
      tagline: 'DIF 在零軸上方上穿 MACD 線進場，下穿出場，只做多。',
      applies: '加權指數、大型股；趨勢型個股',
      script: [
        '策略("MACD 零軸上黃金交叉")',
        '快 = 參數("快線", 12)',
        '慢 = 參數("慢線", 26)',
        '訊 = 參數("訊號線", 9)',
        '停損值 = 參數("停損 %", 8)',
        'd = macd_dif(close,快,慢)',
        'e = macd_dea(close,快,慢,訊)',
        '若 crossover(d,e) 且 d > 0 則 進場("多")',
        '若 crossunder(d,e) 則 平倉("多")',
        '出場("風控", 停損%=停損值)'].join('\n'),
      blocks: { le: { join: 'and', rows: [['up', S('dif'), S('dea')], ['gt', S('dif'), N(0)]] }, lx: { join: 'and', rows: [['dn', S('dif'), S('dea')]] } },
      risk: { sl: 8, tp: 0, trail: 0, maxbars: 0 },
      rules: { entry: '收盤後，DIF（12 日 EMA − 26 日 EMA）由下往上穿過 MACD 線（9 日 EMA of DIF），而且 DIF 在零軸上方 → 下一個交易日開盤買進。',
        exit: '收盤後，DIF 由上往下穿過 MACD 線 → 下一個交易日開盤賣出。', stop: '進場價下跌 8%。', tp: '不設停利。', size: '全部資金、單一標的、不加碼。', params: '12／26／9、停損 8%' },
      why: 'MACD 把「兩條均線的距離」再平滑一次，零軸上方才進場是為了只做多頭中的再加速，濾掉空頭反彈的假交叉。',
      source: 'Gerald Appel（1979）發明 MACD；「零軸上方的黃金交叉」是常見的濾網寫法。',
      evidence: '站內前期研究沒有單獨測 MACD；趨勢類（MA、BRK）在台指期樣本外全數輸 0050。',
      fail: '盤整（DIF 在零軸附近來回穿越，連續小額停損）、急漲後急殺（DIF 反應慢，吐回大半獲利）。',
      headline: { sym: 'TAIEX', tf: 'D' }, syms: ['TAIEX', 'TX', '2330', '2317', '3037', '2881', '2603'], tfs: ['D', 'W', '60'], needs: null,
    },
    {
      id: 'std_st', no: 3, group: '趨勢', name: 'Supertrend (10,3) 翻多進場',
      tagline: '用 ATR 畫出的趨勢線翻多就買、翻空就賣，只做多。',
      applies: '波動大、趨勢延續性高的個股與指數；成交量足夠',
      script: [
        '策略("Supertrend 10,3")',
        '期 = 參數("ATR 週期", 10)',
        '倍 = 參數("ATR 倍數", 3)',
        't = supertrend_dir(期,倍)',
        '若 t > 0 且 t[1] < 0 則 進場("多")',
        '若 t < 0 且 t[1] > 0 則 平倉("多")'].join('\n'),
      blocks: null,
      risk: { sl: 0, tp: 0, trail: 0, maxbars: 0 },
      rules: { entry: '收盤後，Supertrend 方向由空翻多（今天 > 0、昨天 < 0）→ 下一個交易日開盤買進。',
        exit: '收盤後，Supertrend 方向由多翻空 → 下一個交易日開盤賣出。', stop: 'Supertrend 線本身就是移動停損（隨 ATR 自動跟漲、不會往下調），不另設固定停損。', tp: '不設停利。', size: '全部資金、單一標的、不加碼。', params: 'ATR 週期 10、倍數 3' },
      why: 'Supertrend 把 ATR（真實波幅）當成緩衝帶，跟著價格上移；價格收盤跌破才翻空。比均線交叉少一點延遲，且停損位置有明確定義。',
      source: 'Wilder（1978）提出 ATR；Supertrend 由 Olivier Seban 推廣，是 TradingView 內建指標，(10,3) 為預設值。',
      evidence: '站內前期研究沒有單獨測 Supertrend；同屬趨勢跟隨，台指期趨勢類樣本外全數輸 0050。',
      fail: '橫盤（連續翻多翻空）、假突破後立刻翻空；ATR 倍數小的標的容易被洗。',
      headline: { sym: 'TAIEX', tf: 'D' }, syms: ['TAIEX', 'TX', '2330', '2317', '3037', '2881', '2603'], tfs: ['D', 'W', '60'], needs: null,
    },
    {
      id: 'std_kdrsi', no: 4, group: '動能', name: 'KD + RSI 動能共振',
      tagline: 'KD 黃金交叉且 K、RSI 都在 50 以上才進場，只做多。',
      applies: '個股、指數；動能延續的標的（強勢股）',
      script: [
        '策略("KD+RSI 動能共振")',
        '強 = 參數("強弱分界", 50)',
        '弱 = 參數("RSI 出場線", 45)',
        '停損值 = 參數("停損 %", 8)',
        'kn = 參數("KD 週期", 9)',
        'rn = 參數("RSI 週期", 14)',
        'k = kd_k(kn)',
        'd = kd_d(kn)',
        'r = rsi(close,rn)',
        '若 crossover(k,d) 且 k > 強 且 r > 強 則 進場("多")',
        '若 crossunder(k,d) 或 r < 弱 則 平倉("多")',
        '出場("風控", 停損%=停損值)'].join('\n'),
      blocks: { le: { join: 'and', rows: [['up', S('kdk', { n: 9 }), S('kdd', { n: 9 })], ['gt', S('kdk', { n: 9 }), N(50)], ['gt', S('rsi', { n: 14 }), N(50)]] },
        lx: { join: 'or', rows: [['dn', S('kdk', { n: 9 }), S('kdd', { n: 9 })], ['lt', S('rsi', { n: 14 }), N(45)]] } },
      risk: { sl: 8, tp: 0, trail: 0, maxbars: 0 },
      rules: { entry: '收盤後同時成立：KD（9,3,3）的 K 值上穿 D 值、K 值 > 50、RSI（14，Wilder）> 50 → 下一個交易日開盤買進。',
        exit: '收盤後，K 值下穿 D 值，或 RSI 跌破 45（兩者任一）→ 下一個交易日開盤賣出。', stop: '進場價下跌 8%。', tp: '不設停利。', size: '全部資金、單一標的、不加碼。', params: 'KD 9、RSI 14、分界 50、RSI 出場 45、停損 8%' },
      why: '一般 KD 黃金交叉在低檔（< 20）做反彈；這裡反過來，要求 K、RSI 都站在 50 以上，只在「已經轉強」時追，目的是把 KD 當動能確認而不是抄底。兩個指標互相驗證，減少單一指標的假訊號。',
      source: 'George Lane 的隨機指標（KD，1950 年代）；Wilder（1978）的 RSI；「KD 與 RSI 共振」是台股散戶最常見的組合之一。',
      evidence: '站內前期研究的 PB（RSI 回檔）家族在台指期樣本外年化 4.4%，輸 0050 15 個百分點；本組為動能型，尚無站內獨立驗證。',
      fail: '高檔鈍化（K 值在 80 以上持續不回頭，出場太晚）、盤整（K 在 50 附近反覆交叉）、急殺（RSI 出場線來不及）。',
      headline: { sym: 'TAIEX', tf: 'D' }, syms: ['TAIEX', 'TX', '2330', '2317', '3037', '2881', '2603'], tfs: ['D', 'W', '60'], needs: null,
    },
    {
      id: 'std_brk', no: 5, group: '突破', name: '唐奇安 20 日突破＋量增',
      tagline: '收盤創 20 日新高且量大於 20 日均量進場，跌破 10 日低點出場。',
      applies: '個股（量價配合才有意義）、台指期；大型股與中型股',
      script: [
        '策略("唐奇安突破＋量增")',
        '進 = 參數("突破週期", 20)',
        '出 = 參數("出場週期", 10)',
        '量 = 參數("均量週期", 20)',
        '停損值 = 參數("停損 %", 8)',
        '若 close > highest(high,進)[1] 且 volume > sma(volume,量) 則 進場("多")',
        '若 close < lowest(low,出)[1] 則 平倉("多")',
        '出場("風控", 停損%=停損值)'].join('\n'),
      blocks: { le: { join: 'and', rows: [['gt', S('close'), S('hh', { n: 20 })], ['gt', S('volume'), S('vma', { n: 20 })]] }, lx: { join: 'and', rows: [['lt', S('close'), S('ll', { n: 10 })]] } },
      risk: { sl: 8, tp: 0, trail: 0, maxbars: 0 },
      rules: { entry: '收盤後同時成立：收盤價 > 前 20 日最高價（不含今天）、今天成交量 > 20 日均量 → 下一個交易日開盤買進。',
        exit: '收盤後，收盤價 < 前 10 日最低價（不含今天）→ 下一個交易日開盤賣出。', stop: '進場價下跌 8%。', tp: '不設停利。', size: '全部資金、單一標的、不加碼。', params: '突破 20 日、出場 10 日、均量 20 日、停損 8%' },
      why: '突破新高代表上方沒有套牢賣壓，量增代表有人真的買進。出場用較短的 10 日低點，是為了「進慢出快」——保住大部分獲利。規則是海龜交易法的簡化版。',
      source: 'Richard Donchian 的 4 週規則；Curtis Faith《Way of the Turtle》（2007）的 20 日突破系統；Gervais、Kaniel、Mingelgrin（2001）《The High-Volume Return Premium》，Journal of Finance（成交量異常放大後報酬偏高）。',
      evidence: '站內前期研究：台指期突破家族（BRK）樣本外年化 6.9%，輸同期 0050 12.6 個百分點，分段 0/5 勝；此為不含量能濾網的版本。',
      fail: '盤整區的假突破（突破後立刻回落）、急跌市場（進場點少、一進場就被停損）、成交量極小的標的（量增門檻失去意義）。',
      headline: { sym: 'TAIEX', tf: 'D' }, syms: ['TAIEX', 'TX', '2330', '2317', '3037', '2881', '2603'], tfs: ['D', 'W', '60'], needs: null,
    },
    {
      id: 'std_revert', no: 6, group: '回歸', name: '布林下軌反彈＋RSI 超賣',
      tagline: '跌破布林下軌後收盤站回、且 RSI 偏低時買進，回到中軌賣出。',
      applies: '區間震盪的大型股、金融股、傳產股；不適合單邊下跌的標的',
      script: [
        '策略("布林下軌反彈＋RSI 超賣")',
        '週 = 參數("布林週期", 20)',
        '倍 = 參數("標準差倍數", 2)',
        '低 = 參數("RSI 超賣線", 40)',
        '停損值 = 參數("停損 %", 5)',
        '持有 = 參數("最長持有（根）", 20)',
        'rn = 參數("RSI 週期", 14)',
        '若 crossover(close, bb_low(close,週,倍)) 且 rsi(close,rn) < 低 則 進場("多")',
        '若 crossover(close, bb_mid(close,週,倍)) 則 平倉("多")',
        '出場("風控", 停損%=停損值, 最長持有=持有)'].join('\n'),
      blocks: { le: { join: 'and', rows: [['up', S('close'), S('bbl', { n: 20, k: 2 })], ['lt', S('rsi', { n: 14 }), N(40)]] }, lx: { join: 'and', rows: [['up', S('close'), S('bbm', { n: 20, k: 2 })]] } },
      risk: { sl: 5, tp: 0, trail: 0, maxbars: 20 },
      rules: { entry: '收盤後同時成立：收盤價由下往上穿過布林下軌（20 日、2 倍標準差；昨天收盤 ≤ 下軌、今天 > 下軌）、RSI（14）< 40 → 下一個交易日開盤買進。',
        exit: '收盤價由下往上穿過布林中軌（20 日均線）→ 下一個交易日開盤賣出。', stop: '進場價下跌 5%；最長持有 20 根 K 棒，逾時下一根開盤出場。', tp: '以中軌為目標，不另設固定停利。', size: '全部資金、單一標的、不加碼。', params: '布林 20/2、RSI 14 < 40、停損 5%、最長 20 根' },
      why: '價格偏離均值太遠通常會拉回來；用「跌出下軌後站回」而不是「跌破下軌就買」，是等反彈確認、避免接落下的刀。RSI 偏低是第二道確認。短停損、短持有：這類策略賺小錢，不能讓一次下跌吃光。',
      source: 'John Bollinger《Bollinger on Bollinger Bands》（2001）；Wilder（1978）RSI；均值回歸在股價短期反轉的研究（Jegadeesh 1990）有學術基礎，但交易成本後是否仍有利要看標的。',
      evidence: '站內前期研究：台指期 PB（回檔）家族樣本外年化 4.4%、B 多空版 0.8%，都輸 0050；均值回歸在強趨勢市場（如 2020 之後的台股）常常被單邊行情甩開。',
      fail: '單邊下跌（連續跌破下軌，每次反彈都不夠）、黑天鵝（停損跳空）、強勢多頭（回檔太淺，根本不會碰到下軌，交易次數很少）。',
      headline: { sym: 'TAIEX', tf: 'D' }, syms: ['TAIEX', 'TX', '2330', '2317', '3037', '2881', '2603'], tfs: ['D', 'W', '60'], needs: null,
    },
    {
      id: 'std_mtf', no: 7, group: '多週期', name: '週 K 定方向、日 K 進場',
      tagline: '週 K 在 20 週均線之上且均線向上，才在日 K 站回 20 日均線時買進。',
      applies: '個股與指數，需要日 K 至少 2 年以上資料（要算 20 週均線）；趨勢型標的',
      script: [
        '策略("週K定方向、日K進場")',
        '週數 = 參數("週均線週數", 20)',
        '日數 = 參數("日均線週期", 20)',
        '停損值 = 參數("停損 %", 8)',
        'w = wk_sma(週數)',
        '多頭 = w > w[5] 且 close > w',
        '若 多頭 且 crossover(close, sma(close,日數)) 則 進場("多")',
        '若 crossunder(close, sma(close,日數)) 或 close < w 則 平倉("多")',
        '出場("風控", 停損%=停損值)'].join('\n'),
      blocks: null,
      risk: { sl: 8, tp: 0, trail: 0, maxbars: 0 },
      rules: { entry: '大方向（週 K）：「已收完的週」收盤價的 20 週均線，比 5 個交易日前高（均線向上），而且今天收盤價在這條 20 週均線之上。小時機（日 K）：同時今天收盤價由下往上穿過 20 日均線 → 下一個交易日開盤買進。',
        exit: '收盤價由上往下穿過 20 日均線，或收盤價跌破 20 週均線（週 K 大方向轉壞）→ 下一個交易日開盤賣出。', stop: '進場價下跌 8%。', tp: '不設停利。', size: '全部資金、單一標的、不加碼。',
        params: '週均線 20 週、日均線 20 日、停損 8%（本策略只在「日 K」週期可用，週、60 分週期不適用）' },
      why: '大週期定方向、小週期找時機：只在大趨勢向上時才買回檔後的轉強，避免逆勢抄底。週均線只用「已經收完的週」計算，本週還沒收完就不算，所以不會偷看到本週後半段的價格。',
      source: 'Alexander Elder《Trading for a Living》（1993）的三重濾網：先看大週期趨勢，再用小週期找進場。',
      evidence: '站內前期研究（docs/futures_lab）的整體架構就是「週 K 判大格局、日 K 找進出場」，但 21 組樣本外全部輸 0050；多週期降低了假訊號，沒有讓它贏過買進持有。',
      fail: '大趨勢轉折初期（週均線還沒翻、已經在跌）、橫盤（日 K 反覆穿越 20 日線但週 K 方向不明）、急漲急殺（週均線太慢）。',
      headline: { sym: 'TAIEX', tf: 'D' }, syms: ['TAIEX', 'TX', '2330', '2317', '3037', '2881', '2603'], tfs: ['D'], needs: null,
    },
    {
      id: 'std_trust', no: 8, group: '籌碼', name: '投信連買 3 日進場',
      tagline: '投信連續 3 個交易日買超進場，連續 3 日賣超出場，只做多。',
      applies: '投信會買的個股（中小型股、電子股）；指數、期貨、沒有籌碼資料的標的不適用',
      script: [
        '策略("投信連買")',
        '日 = 參數("連買日數", 3)',
        '停損值 = 參數("停損 %", 8)',
        's = streak(chip("投信"))',
        '若 crossover(s, 日 - 0.5) 則 進場("多")',
        '若 crossunder(s, 0.5 - 日) 則 平倉("多")',
        '出場("風控", 停損%=停損值)'].join('\n'),
      blocks: { le: { join: 'and', rows: [['up', S('str'), N(2.5)]] }, lx: { join: 'and', rows: [['dn', S('str'), N(-2.5)]] } },
      risk: { sl: 8, tp: 0, trail: 0, maxbars: 0 },
      rules: { entry: '收盤後，投信買賣超連續買超的天數剛好達到 3 天（今天 = 3 天，昨天 < 3 天）→ 下一個交易日開盤買進。籌碼資料當天盤後公布，所以是收盤後才看得到。',
        exit: '收盤後，投信連續賣超天數剛好達到 3 天 → 下一個交易日開盤賣出。', stop: '進場價下跌 8%。', tp: '不設停利。', size: '全部資金、單一標的、不加碼。', params: '連買日數 3、停損 8%' },
      why: '投信是持股期間較長的法人，連續買超可能代表基金在建倉。「連買 3 日」是最常被引用的門檻。這是跟隨法人的策略：你不知道他們為什麼買，只知道他們在買。',
      source: '台股市場慣用的法人籌碼觀察（投信連買、作帳行情），沒有單一學術出處；本站內建策略「投信連買」同口徑。',
      evidence: '站內前期研究（docs/strategy_lab/council/r2_chips.md）：在營收動能股裡控制 20 日漲幅後，「投信 20 日買超」比「非買超」的下期月報酬平均差 −0.32%（t = −0.71，2017～2026），沒有增量、方向偏負；2023 年起轉正但與 ETF 被動買盤暴增同時發生，分不開。結論：不當作有證據的策略。',
      fail: '投信買超的是權值股指數調整（被動買盤，不代表看好）、作帳行情結束後（季底後投信反手賣）、小型股投信一買就拉高（進場價已偏貴）。',
      headline: { sym: '2330', tf: 'D' }, syms: ['2330', '2317', '3037', '2881', '2603'], tfs: ['D', 'W'], needs: 'chip',
    },
    {
      id: 'std_rev', no: 9, group: '基本面＋價格', name: '營收動能＋52 週新高波段',
      tagline: '近 3 月營收均值比近 12 月均值高 10% 以上，且收盤創 52 週新高才買，跌破 60 日線出場。',
      applies: '有月營收資料的上市櫃個股（中型成長股效果最明顯）；指數、ETF、期貨不適用',
      script: [
        '策略("營收動能＋52週新高")',
        '門檻 = 參數("營收動能門檻 %", 110)',
        '高 = 參數("新高天數", 250)',
        '線 = 參數("出場均線", 60)',
        '停損值 = 參數("停損 %", 12)',
        '營收 = chip("營收動能")',
        '若 營收 >= 門檻 且 close > highest(high,高)[1] 則 進場("多")',
        '若 close < sma(close,線) 則 平倉("多")',
        '出場("風控", 停損%=停損值)'].join('\n'),
      blocks: { le: { join: 'and', rows: [['ge', S('crv'), N(110)], ['gt', S('close'), S('hh', { n: 250 })]] }, lx: { join: 'and', rows: [['lt', S('close'), S('sma', { n: 60 })]] } },
      risk: { sl: 12, tp: 0, trail: 0, maxbars: 0 },
      rules: { entry: '營收面：每月 10 日前公布的月營收，用「近 3 個月平均營收 ÷ 近 12 個月平均營收」≥ 110%（營收加速）。可用日一律從「次月 11 日」起算，不用公司實際早公布的日子，寧可晚用不偷看。價格面：收盤價 > 前 250 個交易日（約 52 週）最高價（不含今天）。兩個同時成立 → 下一個交易日開盤買進。',
        exit: '收盤後，收盤價跌破 60 日均線 → 下一個交易日開盤賣出。', stop: '進場價下跌 12%。', tp: '不設停利。', size: '全部資金、單一標的、不加碼（完整版是在 200 檔內排名挑前 10 檔等權，這裡簡化成單一標的的進出場）。', params: '營收動能 ≥ 110、新高 250 日、出場 60 日線、停損 12%' },
      why: '營收加速代表基本面在改善，52 週新高代表市場也同意；兩者同時出現才買，是把「價值面」與「價格面」疊起來。這是站內前期因子研究（S2 月營收動能）的單一標的簡化版，完整版的選股排名、等權換倉在這裡做不到。',
      source: 'George 與 Hwang（2004）《The 52-Week High and Momentum Investing》，Journal of Finance；月營收動能為台股常用基本面動能指標，站內研究見 docs/strategy_lab/factor_lab（S2）。',
      evidence: '站內前期研究：S2 月營收動能在前 600 大年化約 33%（同期 0050 約 20%），但訓練期短、依賴 2021 年航運行情，統計上不顯著（t 約 1.8～1.9），存活者偏誤未量化，委員會結論為「不採用」。這裡的簡化版沒有排名與分散，結果不能直接當作完整版的證據。',
      fail: '營收是一次性拉貨（出貨高峰＝股價高點）、景氣循環股（營收最高時股價已反映）、大盤急殺（新高股一起殺）、單一標的的交易次數太少而不具統計意義。',
      headline: { sym: '2330', tf: 'D' }, syms: ['2330', '2317', '3037', '2881', '2603'], tfs: ['D', 'W'], needs: 'chip',
    },
    {
      id: 'std_tx200', no: 10, group: '台指期', name: '台指期 200 日線多單',
      tagline: '台指期收盤站上 200 日線進場做多 1 口，跌破出場，空手時不做空。',
      applies: '台指期（近月連續）、加權指數；每口約 200 × 指數點，需要足額保證金',
      script: [
        '策略("台指期200日線")',
        '週 = 參數("均線週期", 200)',
        '若 crossover(close, sma(close,週)) 則 進場("多")',
        '若 crossunder(close, sma(close,週)) 則 平倉("多")'].join('\n'),
      blocks: { le: { join: 'and', rows: [['up', S('close'), S('sma', { n: 200 })]] }, lx: { join: 'and', rows: [['dn', S('close'), S('sma', { n: 200 })]] } },
      risk: { sl: 0, tp: 0, trail: 0, maxbars: 0 },
      rules: { entry: '收盤後，收盤價由下往上穿過 200 日均線 → 下一個交易日開盤買進 1 口台指期（近月連續）。',
        exit: '收盤後，收盤價由上往下穿過 200 日均線 → 下一個交易日開盤賣出。', stop: '以 200 日線反向為停損，不另設固定停損（台指期槓桿高，實際操作建議另設保護性停損）。', tp: '不設停利。', size: '固定 1 口，初始資金 500 萬（約當現在 1 倍名目曝險；早年指數低時槓桿遠低於 1 倍）。空手時只放現金，不計利息。', params: '均線 200 日；期貨手續費 40 元／口、期交稅 0.002%、滑價 1 點（站內預設）' },
      why: '長期均線是最簡單的「風險開關」：多頭持有、空頭離場。目的不是多賺，而是避開 2008、2022 那種大空頭的大部分跌幅。',
      source: 'Mebane Faber（2007）《A Quantitative Approach to Tactical Asset Allocation》（10 個月均線，約等於 200 日線）；站內前期研究 docs/strategy_lab/council/r3_final.md 的 F4、E2。',
      evidence: '站內前期研究（r3_final）：加權指數 200 日線 ±2% 擇時，全期年化 24.5%，比直接持有 25.8% 少 1.2 個百分點，但最大回撤從 −83% 降到 −47%——買到的是回撤保護，不是報酬。台指期 21 組系統樣本外沒有一套贏過同期 0050。',
      fail: '橫盤（價格反覆穿越 200 日線，連續被洗）、V 型反轉（2020 年 3 月、2025 年 4 月：跌破出場後急彈，站回 200 日線時已錯過一大段）、逆價差與換月成本（近月連續價格含換月跳點）。',
      headline: { sym: 'TX', tf: 'D' }, syms: ['TX', 'TAIEX'], tfs: ['D', 'W'], needs: null,
    },
  ];

  /** 標準策略 → 自訂策略頁的規則物件（custom.js 的 blank() 結構）。script 為準；blocks 有就一併填，讓使用者能切到積木 */
  function toRule(def, blank) {
    const r = blank(); r.id = def.id; r.name = def.name; r.mode = 'script'; r.dir = 'long'; r.script = def.script; r.risk = Object.assign({}, def.risk); r.std = def.id;
    if (def.blocks) {
      ['le', 'lx', 'se', 'sx'].forEach((k) => {
        const b = def.blocks[k]; if (!b) return;
        r.blocks[k].join = b.join;
        r.blocks[k].rows = b.rows.map((x) => ({ kind: 'cmp', op: x[0], a: Object.assign({}, x[1]), b: Object.assign({}, x[2]) }));
      });
    }
    return r;
  }

  /** 回測統一設定（結果表與網頁預設完全一致）：多單、全部資金、下一根開盤成交、不加碼、成本用站內預設（手續費不打折） */
  const CAPITAL = { stock: 1000000, fut: 5000000 };
  return { DEFS, toRule, CAPITAL };
}));
