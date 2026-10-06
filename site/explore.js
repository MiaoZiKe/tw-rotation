/* ============================================================================
   選股策略（#explore）—— site/explore.js（Andy 2026-10-05 第二版，規格：docs/explore_page_spec.md）
   ----------------------------------------------------------------------------
   第一版是「六個白話問題＋泡泡圖」。Andy 看過後改方向：「改成圖片那樣類似好了，策略但寫成英文，
   並且不同面向為何篩選那些公司需要標示原因說明清楚，最好附上資料出處」。

   所以這一版是「策略卡片牆」：
     · 每個策略一張卡（英文標題＋一行中文翻譯），卡內列前 3 檔（依成交值排序 —— 不是好壞名次）。
     · 每一列點開 → 條件逐條打勾＋實際數值（為什麼入選），不讓使用者自己去猜。
     · 每張卡的「i」→ 篩選條件＋出處 ⓘ（滑過才顯示機構名）。
     · 「>」→ #explore/<策略 id> 完整名單頁：全部符合的公司＋每檔原因欄＋計算方式＋出處 ⓘ。
   2026-10-06 廢話普查第二輪（docs/copy_audit_1006_r2.md 轉交）：出處只留機構名（不寫端點代碼、FinMind 資料集名、程式路徑），
     整行「資料出處：」改成標題旁 ⓘ；卡片標題列的資料日期膠囊（.sl-date）與 i 浮層的資料日期拿掉（DECISIONS #329 轉交）。
   泡泡圖與條件積木拿掉（理由見規格 §2：卡片牆已經把「為何入選」寫在每一列上，泡泡圖要使用者
   自己對座標，等於多一步推論；交集功能改由完整名單頁的「也符合哪些策略」欄回答）。

   口徑沿用第一版（pipeline/compute/explore.py 的 explore.json＋fundamental.json＋stocks.json），
   另外用到 candidates.json（技術面兩張卡）與 inst_streak.json（投信連買）。
   排除 ETF 與近 20 日平均成交值 < 1,000 萬元的冷門股（價格不可靠）。
   ============================================================================ */
(function () {
  'use strict';
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
  const App = () => window.App || {};
  const ok = (v) => v != null && isFinite(v);
  const n1 = (v, d) => (ok(v) ? Number(v).toFixed(d == null ? 1 : d) : '—');
  const MIN_TV = 10;          // 近 20 日平均成交值下限（百萬元）

  /* ---------------- 資料出處 ----------------
     畫面只寫「機構名」：[項目, 機構]。實際走的端點與資料集（證交所 OpenAPI、櫃買中心、FinMind 回補、集保開放資料、
     鉅亨／TechNews／經濟日報 RSS）照 pipeline/sources 與 docs/v3_sources_spec.md —— 那是工程口徑，讀者用不到，不上畫面
     （Andy 10-06：「出處：…（證交所 OpenAPI t187ap04）…讀者看了沒意義」）。法人與融資的歷史是經 FinMind 取得，但原始公布機構是證交所／櫃買中心。 */
  const SRC = {
    price: ['股價', '臺灣證券交易所、證券櫃檯買賣中心'],
    fin: ['財報', '公開資訊觀測站'],
    rev: ['月營收', '公開資訊觀測站'],
    per: ['本益比', '臺灣證券交易所'],
    div: ['股利', '臺灣證券交易所'],
    inst: ['三大法人買賣超', '臺灣證券交易所、證券櫃檯買賣中心'],
    tech: ['技術指標', '本站計算'],
    calc: ['衍生數值', '本站計算'],
    tdcc: ['集保股權分散表', '臺灣集中保管結算所'],
    mgn: ['融資融券餘額', '臺灣證券交易所、證券櫃檯買賣中心'],
    news: ['新聞', '鉅亨網、TechNews 科技新報、經濟日報'],
    mops: ['重大訊息', '公開資訊觀測站'],
    theme: ['題材熱度', '本站計算'],
  };
  /* 出處 ⓘ：跟全站 App.srcInfo 同一個寫法（claude/copy-trim2 分支，還沒上 main）—— 有就直接用它；
     沒有就產出同樣的標記（class srcinfo＋title；樣式等 .srcinfo 進 index.html 才有，這之前借既有的 .muted 灰字）。
     App.srcInfo 上 main 之後，這裡的退回寫法可以刪掉。 */
  const srcI = (src) => (App().srcInfo ? App().srcInfo(src, '')
    : (src ? `<span class="srcinfo muted" tabindex="0" role="note" aria-label="出處" title="${esc('出處：' + src)}">ⓘ</span>` : ''));
  const srcOf = (s) => [...new Set(s.src)].map((k) => `${SRC[k][1]}（${SRC[k][0]}）`).join('；');

  /* ---------------- 分類（晶片） ---------------- */
  /* ★ 2026-10-05 第四版（Andy：「需要分成以下大族群：基本面、技術面、籌碼面、消息面」）：
     原本 7 類（基本／估值／成長／技術／籌碼／股利／動能）收成 4 大面向。估值與股利併入基本面、
     動能（60 日漲幅、帶量上漲）併入技術面；消息面是新的一類。第 4 欄是區段標題下那行「這一區在回答什麼」。 */
  /* ★ 2026-10-06（Andy：「全部分頁拿掉」）：只留四個面向，預設基本面；重新整理一律回基本面（不讀 localStorage）。 */
  const CATS = [
    ['fund', 'Fundamentals', '基本面', '公司本身賺不賺、成長快不快、價格貴不貴、配息穩不穩'],
    ['tech', 'Technicals', '技術面', '股價走勢與成交量：趨勢有沒有站穩、量有沒有跟上'],
    ['chip', 'Positioning', '籌碼面', '誰在買：法人、千張大戶、融資散戶的部位怎麼變'],
    ['news', 'News Flow', '消息面', '最近有沒有事：新聞變多、公司公告法說會、所屬題材升溫'],
  ];
  const CBY = {}; CATS.forEach((c) => { CBY[c[0]] = c; });
  const ICON = {   // 簡單線條圖示（currentColor），一個分類一個
    fund: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    val: '<circle cx="12" cy="12" r="8"/><path d="M12 7v10M9 9.5h4.5a2 2 0 010 4H10a2 2 0 000 4h5"/>',
    grow: '<path d="M3 17l6-6 4 4 8-8M15 7h6v6"/>',
    tech: '<path d="M3 12h4l3-7 4 14 3-7h4"/>',
    chip: '<path d="M4 20h16M6 16V9m4 7V6m4 10v-5m4 5V4"/>',
    divd: '<path d="M12 3v18M7 8c0-2 2-3 5-3s5 1 5 3-2 3-5 3-5 1-5 3 2 3 5 3 5-1 5-3"/>',
    mom: '<path d="M13 3L4 14h7l-1 7 9-11h-7z"/>',
    news: '<path d="M4 5h13v14H6a2 2 0 01-2-2zM17 9h3v8a2 2 0 01-2 2M7 9h7M7 13h7M7 16h4"/>',
  };
  const icon = (c) => `<svg class="sl-ic" viewBox="0 0 24 24" aria-hidden="true">${ICON[c] || ''}</svg>`;

  /* ---------------- 策略 ----------------
     conds：每一條 [標籤, 取值, 比較, 門檻, 格式]。符合＝全部條件成立；理由就是逐條把「實際值 vs 門檻」寫出來。
     key：卡片右側那一個關鍵指標。need：要哪一份資料（缺就顯示「尚無資料」，不要硬算）。 */
  const pct = (v) => `${n1(v)}%`;
  const days = (v) => `${ok(v) ? Math.round(v) : '—'} 天`;
  const S_ = [
    { id: 'quality', name: '高獲利品質', cat: 'fund', en: 'Quality Earners', zh: '高獲利品質：ROE 與毛利率都高', tags: ['ROE', '毛利率'],
      conds: [['ROE（近四季）', (r) => r.roe, '>=', 15, pct], ['毛利率（近四季）', (r) => r.gm, '>=', 20, pct, (r) => r.fin]],
      key: ['ROE', (r) => r.roe, pct], src: ['fin', 'calc'],
      how: 'ROE＝近四季稅後淨利 ÷ 平均股東權益；毛利率＝近四季毛利 ÷ 營收。金融業沒有毛利率，只看 ROE。',
      care: '景氣循環股在高峰時 ROE 最漂亮；借很多錢的公司 ROE 也會被墊高。' },
    { id: 'margin', name: '毛利率領先', cat: 'fund', en: 'Margin Leaders', zh: '毛利率領先：產品有議價力', tags: ['毛利率', '獲利'],
      conds: [['毛利率（近四季）', (r) => r.gm, '>=', 40, pct], ['近四季有獲利', (r) => (r.loss ? 0 : (r.eps != null ? 1 : null)), '>=', 1, (v) => (v ? '是' : '否')]],
      key: ['毛利率', (r) => r.gm, pct], src: ['fin', 'calc'],
      how: '毛利率＝近四季毛利 ÷ 近四季營收；獲利＝近四季 EPS 合計 > 0。',
      care: '不同產業的正常毛利率差很多（軟體、IC 設計天生高），最好跟同業比。' },
    { id: 'below', name: '本益比在自身歷史低檔', cat: 'fund', en: 'Below Own History', zh: '本益比在自身歷史低檔：落在自身 5 年第 30 百分位以下', tags: ['本益比', '歷史比較'], need: 'ex',
      conds: [['本益比歷史位置（0＝自身歷史最低）', (r) => r.pepct, '<=', 30, (v) => `第 ${n1(v, 0)} 百分位`], ['本益比（有獲利）', (r) => r.pe, '>', 0, (v) => `${n1(v)} 倍`]],
      key: ['本益比位置', (r) => r.pepct, (v) => `P${n1(v, 0)}`], src: ['per', 'fin', 'calc'],
      how: '把目前本益比放進「這家公司自己近 5 年各季本益比」裡排位置（至少 8 季才算）。不跨族群比（不同產業本益比天生不同）。',
      care: '本益比低於自己過去，可能反映市場預期未來獲利下滑。' },
    { id: 'value', name: '低本益比且真的有賺', cat: 'fund', en: 'Low P/E, Real Profits', zh: '低本益比且真的有賺', tags: ['本益比', 'ROE'],
      conds: [['本益比', (r) => r.pe, '<=', 12, (v) => `${n1(v)} 倍`, null, 0], ['ROE（近四季）', (r) => r.roe, '>=', 10, pct]],
      key: ['本益比', (r) => r.pe, (v) => `${n1(v)} 倍`], src: ['per', 'fin', 'calc'],
      how: '本益比＝收盤價 ÷ 近四季 EPS（虧損公司沒有本益比，不會入選）；再要求 ROE ≥ 10%，排除本益比低但 ROE 不到 10% 的。',
      care: '金融、航運、原物料等景氣股本益比常年偏低，低不一定代表被低估。' },
    { id: 'accel', name: '營收加速', cat: 'fund', en: 'Revenue Accelerators', zh: '營收加速：月營收連續年增', tags: ['營收', '年增'],
      conds: [['月營收連續年增', (r) => r.rs, '>=', 3, (v) => `${ok(v) ? v : '—'} 個月`], ['最新一月營收年增', (r) => r.ry, '>=', 10, pct]],
      key: ['營收年增', (r) => r.ry, (v) => `${v >= 0 ? '+' : ''}${n1(v)}%`], src: ['rev', 'calc'],
      how: '年增率＝當月營收 ÷ 去年同月營收 − 1；連續月數＝年增率連續為正的月份數。跟去年同月比可以避開淡旺季。',
      care: '去年同期如果特別差（基期低），年增率會看起來很漂亮。' },
    { id: 'record', name: '月營收創新高', cat: 'fund', en: 'Record-High Sales', zh: '月營收創歷史新高', tags: ['營收', '創新高'],
      conds: [['最新月營收創歷史新高', (r) => (r.rec ? 1 : 0), '>=', 1, (v) => (v ? '是' : '否')], ['最新一月營收年增', (r) => r.ry, '>', 0, pct]],
      key: ['營收年增', (r) => r.ry, (v) => `${v >= 0 ? '+' : ''}${n1(v)}%`], src: ['rev', 'calc'],
      how: '最新公布的月營收高於這家公司過去每一個月的營收，而且比去年同月成長。',
      care: '月營收創高不等於獲利創高：毛利可能在下滑。' },
    { id: 'accum', name: '法人連續買超', cat: 'chip', en: 'Institutional Accumulation', zh: '三大法人連續淨買超', tags: ['三大法人', '連續買超'], need: 'inst',
      conds: [['三大法人合計連續淨買超', (r) => r.bd, '>=', 5, days]],
      key: ['連買', (r) => r.bd, (v) => `${v} 天`], src: ['inst', 'calc'],
      how: '外資＋投信＋自營商每日買賣超相加，從最近一個交易日往回數連續為正的天數；今天一轉賣就歸零。',
      care: '法人也會看錯；外資有時只是被動調整指數成分。' },
    { id: 'trust', name: '投信連續買超', cat: 'chip', en: 'Fund Manager Favorites', zh: '投信連續買超', tags: ['投信', '連續買超'], need: 'streak',
      conds: [['投信連續買超', (r) => r.td, '>=', 3, days]],
      key: ['投信連買', (r) => r.td, (v) => `${v} 天`], src: ['inst', 'calc'],
      how: '只看投信（國內基金）每日買賣超，從最近一個交易日往回數連續為正的天數。只列連買天數前 60 名。',
      care: '投信季底常有「作帳」買盤，季初可能反手。' },
    { id: 'steady', name: '穩健上升', cat: 'tech', en: 'Steady Uptrend', zh: '穩健上升：低波動且站上均線', tags: ['低波動', '均線'], need: 'ex',
      conds: [['60 日年化波動度', (r) => r.vol, '<=', 30, pct], ['收盤站上 20 日均線', (r) => r.a20, '>=', 1, (v) => (v ? '是' : '否')], ['收盤站上 60 日均線', (r) => r.a60, '>=', 1, (v) => (v ? '是' : '否')]],
      key: ['波動度', (r) => r.vol, pct], src: ['price', 'tech', 'calc'],
      how: '波動度＝近 60 日日報酬標準差 × √252（年化）；均線用還原後日 K 收盤價。',
      care: '穩不代表會漲，可能只是盤整；財報或消息可能讓它突然大動。' },
    { id: 'macd', name: '均線多頭排列', cat: 'tech', en: 'Bullish MA Alignment', zh: '均線多頭排列＋MACD 柱翻正', tags: ['均線', 'MACD'], need: 'cand',
      conds: [['均線多頭排列（5>20>60）', (r) => r.align, '>=', 1, (v) => (v === 1 ? '是' : '否')], ['MACD 柱（OSC）', (r) => r.osc, '>', 0, (v) => n1(v, 2)], ['RSI(14) 未過熱', (r) => r.rsi, '<=', 70, (v) => n1(v)]],
      key: ['OSC', (r) => r.osc, (v) => `${v >= 0 ? '+' : ''}${n1(v, 2)}`], src: ['price', 'tech'],
      how: '只涵蓋技術面候選池（依成交值與技術分數篩出的數百檔），不是全市場。OSC＝DIF − MACD。',
      care: '技術訊號會反覆；多頭排列常出現在已經漲一段之後。' },
    { id: 'lead', name: '60 日漲幅領先', cat: 'tech', en: '60-Day Leaders', zh: '近 60 日漲幅領先且仍站上均線', tags: ['報酬', '趨勢'], need: 'ex',
      conds: [['近 60 日漲跌', (r) => r.ret, '>=', 20, pct], ['收盤站上 20 日均線', (r) => r.a20, '>=', 1, (v) => (v ? '是' : '否')]],
      key: ['60 日', (r) => r.ret, (v) => `${v >= 0 ? '+' : ''}${n1(v)}%`], src: ['price', 'calc'],
      how: '近 60 日漲跌＝今天收盤 ÷ 60 個交易日前收盤 − 1（還原權息）。',
      care: '已經漲多的股票波動也大，回檔幅度常常很深。' },
    { id: 'volup', name: '帶量上漲', cat: 'tech', en: 'Volume Surge', zh: '帶量上漲：成交量放大且收紅', tags: ['成交量', '價格'], need: 'cand',
      conds: [['量比（今日量 ÷ 5 日均量）', (r) => r.vr, '>=', 2, (v) => `${n1(v)} 倍`], ['今日漲跌', (r) => r.chg, '>', 0, pct]],
      key: ['量比', (r) => r.vr, (v) => `${n1(v)}x`], src: ['price', 'tech'],
      how: '只涵蓋技術面候選池（不是全市場）。量比＝今日成交量 ÷ 近 5 日平均量。',
      care: '爆量可能是主力出貨或消息面一次性反應，隔天常見反轉。' },
    { id: 'divcon', name: '穩定配息', cat: 'fund', en: 'Dividend Consistency', zh: '穩定配息：殖利率不低且連年配現金', tags: ['殖利率', '配息年數'], need: 'ex',
      conds: [['近 12 個月現金殖利率', (r) => r.dy, '>=', 4, (v) => `${n1(v, 2)}%`], ['連續配現金股利', (r) => r.dv, '>=', 5, (v) => `${ok(v) ? v : '—'} 年`]],
      key: ['殖利率', (r) => r.dy, (v) => `${n1(v, 2)}%`], src: ['div', 'price', 'calc'],
      how: '殖利率＝近 12 個月現金股利 ÷ 目前股價；連續年數從去年往回數（今年還沒過完不算）。',
      care: '股價大跌也會讓殖利率變高；配息後要填息才算真的賺到。' },

    /* ---------- 籌碼面（第四版新增） ---------- */
    { id: 'whale', name: '千張大戶週增', cat: 'chip', en: 'Whale Accumulation', zh: '千張大戶持股比例比上週增加', tags: ['集保', '大戶'], need: 'ex',
      conds: [['千張大戶持股比例週變化', (r) => r.bw, '>=', 0.5, (v) => `${v >= 0 ? '+' : ''}${n1(v, 2)} 個百分點`], ['千張大戶持股比例', (r) => r.big, '>=', 10, pct]],
      key: ['週增', (r) => r.bw, (v) => `+${n1(v, 2)}pp`], src: ['tdcc', 'calc'],
      how: '集保每週公布一次股權分散表；「千張大戶」＝持有 1,000 張以上的股東合計持股比例。週變化＝最新一週 − 上一週（百分點）。另外要求大戶比例 ≥ 10%，排除大戶本來就極少、一點變動就被放大的股票。',
      care: '集保只看「持有人」不看「是誰」：可能是公司派、也可能是 ETF 申購；每週一次，比股價慢一週。' },
    { id: 'settle', name: '籌碼沉澱', cat: 'chip', en: 'Margin Unwinding', zh: '融資減少＋股價上漲', tags: ['融資', '散戶'], need: 'ex',
      conds: [['融資餘額 5 日變化', (r) => r.mg5, '<=', -5, pct], ['股價 5 日漲跌', (r) => r.r5, '>', 0, pct]],
      key: ['融資 5 日', (r) => r.mg5, (v) => `${n1(v)}%`], src: ['mgn', 'price', 'calc'],
      how: '融資餘額 5 日變化＝今天融資餘額 ÷ 5 個交易日前 − 1（融資餘額不足 100 張的不算，分母太小會亂跳）；股價 5 日漲跌用還原收盤價。融資退場、股價卻往上，代表籌碼從散戶手上移到其他人手上。',
      care: '融資減少也可能是被斷頭（股價先大跌）；要搭配股價一起看，所以才要求 5 日是上漲。' },
    /* ---------- 消息面（第四版新增：只用站上已經合法取得的新聞列表、重大訊息與題材熱度） ---------- */
    { id: 'buzz', name: '新聞則數激增', cat: 'news', en: 'News Spike', zh: '近 7 日被新聞提到的次數暴增', tags: ['新聞', '關注度'], need: 'ex',
      conds: [['近 7 日新聞則數', (r) => r.n7, '>=', 3, (v) => `${ok(v) ? v : '—'} 則`], ['相對前 4 週平均（倍）', (r) => r.nr, '>=', 2, (v) => `${n1(v)} 倍`]],
      key: ['7 日新聞', (r) => r.n7, (v) => `${v} 則`], src: ['news', 'calc'],
      how: '數「標題或內文標到這個股票代號」的新聞則數。基準＝之前 28 天的平均每 7 日則數（基準低於 0.5 則以 0.5 計，避免從 0 變 1 就算無限倍）。只算鉅亨、TechNews、經濟日報這幾個來源，不是全網。',
      care: '新聞多不代表好消息：利空、處分、意外也會讓則數暴增。點進個股頁看新聞標題再判斷。' },
    { id: 'conf', name: '近期法說會', cat: 'news', en: 'Upcoming Investor Conference', zh: '已公告法說會、會議日在近期', tags: ['重大訊息', '法說會'], need: 'ex',
      conds: [['已公告法說會（會議日）', (r) => (r.conf ? 1 : 0), '>=', 1, (v, r) => (v ? '有' : '無')], ['距會議日（負數＝已開完）', (r) => r.confd, '<=', 30, (v) => `${ok(v) ? v : '—'} 天`]],
      key: ['法說日', (r) => (r.conf ? 1 : null), (v, r) => (r && r.conf ? r.conf.slice(5).replace('-', '/') : '—')], src: ['mops', 'calc'],
      how: '從公開資訊觀測站重大訊息裡找主旨含「法人說明會」或「法說會」的公告，取公告寫的會議日；會議日落在今天前 7 天到後 30 天內才列入（剛開完的一週也算，因為市場還在消化）。',
      care: '法說會是「資訊揭露的時間點」，不是好壞訊號；會前常有預期行情、會後可能反向。' },
    { id: 'themeup', name: '題材升溫', cat: 'news', en: 'Theme Heating Up', zh: '所屬題材熱度高且資金佔比上升', tags: ['題材', '熱度'], need: 'theme',
      conds: [['所屬題材熱度（0–100）', (r) => r.thh, '>=', 60, (v) => `${n1(v, 0)} 分`], ['題材資金佔比：今日 − 5 日平均', (r) => r.thu, '>', 0, (v) => `${v >= 0 ? '+' : ''}${n1(v, 2)} 個百分點`]],
      key: ['題材熱度', (r) => r.thh, (v) => `${n1(v, 0)} 分`], src: ['theme', 'news', 'price'],
      how: '只看本站題材熱度頁的題材成分股。熱度＝資金佔比變化、佔比排名、法人 5 日淨買、新聞提及量的加權百分位（0–100）；再要求題材今天的資金佔比高於 5 日平均（正在升溫，不是退燒中）。一檔屬於多個題材時取符合條件中熱度最高的那個。',
      care: '題材熱度是族群層級的訊號，不代表裡面每一檔都同步受惠；成分由人工維護，可能漏列。' },
  ];
  /* 依四大面向、再依 Andy 列的順序排（卡片牆依這個順序分區畫） */
  const ORDER = ['record', 'accel', 'quality', 'margin', 'value', 'below', 'divcon', 'lead', 'macd', 'steady', 'volup', 'trust', 'accum', 'whale', 'settle', 'buzz', 'conf', 'themeup'];
  S_.sort((a, b) => ORDER.indexOf(a.id) - ORDER.indexOf(b.id));
  const SBY = {}; S_.forEach((s) => { SBY[s.id] = s; });
  const OPS = { '>=': (a, b) => a >= b, '<=': (a, b) => a <= b, '>': (a, b) => a > b };

  /* ---------------- 狀態與資料 ---------------- */
  const ST = { cat: 'fund', tags: [], dd: false, open: {}, info: {} };
  const HAVE = { ex: false, cand: false, streak: false, inst: false, theme: false };
  let R = [], RBY = {}, built = false;

  async function loadAll() {
    const A = App();
    const get = (n) => (A.load ? A.load(n).catch(() => null) : Promise.resolve(null));
    const [fund, stocks, ex, cand, streak, th] = await Promise.all(['fundamental', 'stocks', 'explore', 'candidates', 'inst_streak', 'themes'].map(get));
    HAVE.ex = !!(ex && Array.isArray(ex.rows) && ex.rows.length);
    HAVE.theme = !!(th && Array.isArray(th.themes) && th.themes.length);
    /* 題材升溫：每檔取「熱度最高且資金佔比正在上升」的題材；都沒有在升溫就取熱度最高的那個（讓原因欄照實寫 ✗） */
    const thBy = {};
    ((th && th.themes) || []).forEach((t) => {
      const up = ok(t.share) && ok(t.share5) ? +(t.share - t.share5).toFixed(2) : null;
      (t.members || []).forEach((m) => {
        const cur = thBy[m.code], score = (up > 0 ? 1000 : 0) + (t.heat || 0);
        if (!cur || score > cur.score) thBy[m.code] = { score, heat: t.heat, up, name: t.name };
      });
    });
    const day0 = (ex && ex.asof) || '';
    const dd = (a, b) => (a && b ? Math.round((Date.parse(a) - Date.parse(b)) / 864e5) : null);
    HAVE.cand = Array.isArray(cand) && cand.length > 0;
    HAVE.streak = !!(streak && Array.isArray(streak.trust));
    HAVE.inst = HAVE.ex || !!(streak && Array.isArray(streak.total));
    const fx = {}; (fund || []).forEach((f) => { fx[f.code] = f; });
    const exRow = {};
    if (HAVE.ex) ex.rows.forEach((row) => { const o = {}; ex.cols.forEach((c, i) => { o[c] = row[i]; }); exRow[o.code] = o; });
    const cd = {}; (cand || []).forEach((c) => { cd[c.code] = c; });
    const td = {}; ((streak && streak.trust) || []).forEach((s) => { td[s.code] = s.streak_days; });
    const tot = {}; ((streak && streak.total) || []).forEach((s) => { tot[s.code] = s.streak_days; });
    const rows = [];
    (stocks || []).forEach((s) => {
      const f = fx[s.code] || {};
      if (!s.code || /^00/.test(s.code) || s.group_id === 'ind_ETF' || f.group_id === 'ind_ETF') return;
      const e = exRow[s.code] || {}, c = cd[s.code] || {};
      const tv = e.tv20 != null ? e.tv20 : (s.turnover != null ? s.turnover / 1e6 : null);
      if (tv == null || tv < MIN_TV) return;
      rows.push({
        code: s.code, name: s.name || f.name || s.code, group: s.group || f.group_name || '—', close: s.close, chg: s.chg_pct, tv,
        roe: f.roe, gm: f.gross_margin, pe: f.pe, eps: f.ttm_eps, loss: !!f.is_loss, fin: /金融|銀行|保險|證券|金控/.test(s.group || f.group_name || '') && f.gross_margin == null,
        ry: f.rev_yoy, rs: f.rev_streak, rec: !!f.rev_record_high,
        pepct: e.pe_pct, vol: e.vol60, a20: e.above20, a60: e.above60, ret: e.ret60, dy: e.dy, dv: e.div_years,
        bd: HAVE.ex ? e.buy_days : (tot[s.code] || 0),
        td: td[s.code] || 0,
        align: c.ma_align, osc: c.osc, rsi: c.rsi, vr: c.vol_ratio, inCand: !!cd[s.code],
        big: e.big_pct, bw: e.big_wchg, mg5: e.mg_chg5, r5: e.ret5,
        n7: e.news7, nr: ok(e.news7) ? e.news7 / Math.max(e.news_base || 0, 0.5) : null,
        conf: e.conf || null, confd: e.conf ? dd(e.conf, day0) : null,
        thh: thBy[s.code] ? thBy[s.code].heat : null, thu: thBy[s.code] ? thBy[s.code].up : null, thn: thBy[s.code] ? thBy[s.code].name : '',
      });
    });
    R = rows; RBY = {}; rows.forEach((r) => { RBY[r.code] = r; });
  }

  const usable = (s) => !s.need || HAVE[s.need];
  /* 逐條檢查：回傳 [{label, val, txt, th, pass}]；有任何一條取不到值就算不符合（不猜） */
  function check(s, r) {
    return s.conds.map(([label, get, op, th, fmt, skipIf]) => {
      if (skipIf && skipIf(r)) return { label, txt: '金融業無此項，略過', thTxt: '', pass: true, skip: true };
      let v = null; try { v = get(r); } catch (e) { v = null; }
      const pass = ok(v) && OPS[op](+v, th);
      const thTxt = `${op === '>=' ? '≥' : op === '<=' ? '≤' : '>'} ${fmt(th)}`;
      return { label, val: v, txt: ok(v) ? fmt(v) : '無資料', thTxt, pass };
    });
  }
  const passAll = (s, r) => check(s, r).every((c) => c.pass);
  const memo = {};
  function matches(s) {
    if (memo[s.id]) return memo[s.id];
    const out = usable(s) ? R.filter((r) => { try { return passAll(s, r); } catch (e) { return false; } }).sort((a, b) => b.tv - a.tv) : [];
    memo[s.id] = out; return out;
  }
  const reasonLine = (c) => `${c.label} ${c.txt}${c.skip ? '' : ` ${c.thTxt}`} ${c.pass ? '✓' : '✗'}`;
  const chgCls = (v) => (v > 0 ? 'up' : v < 0 ? 'dn' : '');
  const chgTxt = (v) => (ok(v) ? `${v > 0 ? '+' : ''}${n1(v, 2)}%` : '—');
  const spark = (code, w, h) => `<span class="spkw" data-spk="${esc(code)}" data-w="${w}" data-h="${h}">${App().sparkSVG ? App().sparkSVG(code, { w, h }) : ''}</span>`;
  const logo = (r, sz) => (App().logo ? App().logo(r.code, r.name, sz) : '');
  const condTxt = (s) => s.conds.map(([label, , op, th, fmt]) => `${label} ${op === '>=' ? '≥' : op === '<=' ? '≤' : '>'} ${fmt(th)}`).join('，且 ');
  /* 浮層用的精簡版（Andy 10-05：「"?"內標示篩選條件即可，不用說太多」）：只留條件；出處收在標題旁 ⓘ（openPop 那裡）。
     完整的計算方式／門檻留在「完整名單」頁（infoHTML）。 */
  function infoBrief(s) {
    return `<div class="sl-info sl-brief" data-info="${s.id}">
      <p><b>篩選條件：</b>${esc(condTxt(s))}。</p></div>`;
  }
  function infoHTML(s) {
    return `<div class="sl-info" data-info="${s.id}">
      <p><b>篩選條件：</b>${esc(condTxt(s))}。</p>
      <p><b>計算方式：</b>${esc(s.how)}</p>
      <p><b>共同門檻：</b>排除 ETF，以及近 20 日平均成交值低於 1,000 萬元的冷門股（成交太少，價格不可靠）。</p>
      <p class="sl-care"><b>要小心：</b>${esc(s.care)}</p></div>`;
  }

  /* ---------------- 畫面：策略卡片牆 ---------------- */
  // 2026-10-06 Andy：頂端黃色提示列會蓋住下方內容 → 法遵免責改放標題右側小字（同一行），不刪；原本的操作說明句移除（廢話）
  const LEGAL = '<small class="xp-legal" role="note" id="xpLegal">條件篩選結果僅供研究，不構成投資建議；本站非證券投資顧問。名單依成交值排序，不是好壞名次。</small>';
  function shellWall(root) {
    root.innerHTML = `
      <div class="sl-head"><h2>選股策略 ${LEGAL}</h2></div>
      <div class="nbsw sl-chips" id="slChips" role="tablist" aria-label="策略分類"></div>
      <div class="nbbody sl-nb"><div class="sl-tags" id="slTags"></div>
      <div class="sl-wall" id="slGrid"></div></div>`;
    root.onclick = onClick;
    if (!ST.ddDoc) { ST.ddDoc = true; document.addEventListener('pointerdown', (e) => { if (ST.dd && !e.target.closest('.sl-ddw')) { ST.dd = false; paintChips(); } }, true); }
  }
  function paintChips() {
    const cnt = (c) => S_.filter((s) => s.cat === c).length;
    $('#slChips').innerHTML = CATS.map(([k, en, zh]) => `<button type="button" class="sl-chip${ST.cat === k ? ' on' : ''}" data-cat="${k}" role="tab" aria-selected="${ST.cat === k}" title="${esc(en)}">${esc(zh)} <em>${cnt(k)}</em></button>`).join('');
    const tags = [...new Set(S_.filter((s) => s.cat === ST.cat).flatMap((s) => s.tags))];
    /* 分類＝資料夾分頁（沿用產業地圖的 .nbsw，Andy 10-05「上方的標籤改用分頁…統一」）；
       子標籤＝一顆下拉多選（Andy 10-05「子標籤用下拉式清單篩選」）：只列目前分頁的子標籤，勾選即篩、可清除，按鈕一行不換行。
       多選是「任一符合」—— 勾越多張卡越多，跟一般電商篩選一致。 */
    ST.tags = ST.tags.filter((t) => tags.includes(t));
    const lab = ST.tags.length ? (ST.tags.length <= 2 ? ST.tags.join('、') : `${ST.tags.slice(0, 2).join('、')} 等 ${ST.tags.length} 個`) : '不限';
    $('#slTags').innerHTML = `<span class="sl-tl">子標籤</span><span class="sl-ddw"><button type="button" class="sl-dd${ST.tags.length ? ' on' : ''}" id="slTagDd" aria-haspopup="listbox" aria-expanded="${ST.dd}" title="${esc(lab)}">${esc(lab)} ▾</button>`
      + (ST.dd ? `<div class="sl-ddm" id="slTagMenu" role="listbox" aria-multiselectable="true"><div class="sl-ddl">${tags.map((t) => `<label class="sl-tag${ST.tags.includes(t) ? ' on' : ''}"><input type="checkbox" data-tag="${esc(t)}" ${ST.tags.includes(t) ? 'checked' : ''}>${esc(t)}</label>`).join('')}</div>`
        + `<div class="sl-ddf"><button type="button" class="sl-ddclr" ${ST.tags.length ? '' : 'disabled'}>清除</button><button type="button" class="sl-ddok">完成</button></div></div>` : '') + '</span>';
  }
  function rowHTML(s, r, i) {
    const k = s.key, kv = k[1](r), open = ST.open[s.id] === r.code;
    return `<div class="sl-row${open ? ' open' : ''}" data-sid="${s.id}" data-code="${esc(r.code)}">
      <button type="button" class="sl-rbtn" aria-expanded="${open}" title="${esc(check(s, r).map(reasonLine).join('\n'))}">
        <span class="sl-rank">${i + 1}</span>${logo(r, 26)}
        <span class="sl-nm"><b>${esc(r.name)}</b><small>${esc(r.code)}</small></span>
        <span class="sl-px"><b>${n1(r.close, r.close >= 100 ? 1 : 2)}</b><small class="${chgCls(r.chg)}">${chgTxt(r.chg)}</small></span>
        ${spark(r.code, 64, 24)}
        <span class="sl-key"><small>${esc(k[0])}</small><b>${ok(kv) ? esc(k[2](kv, r)) : '—'}</b></span>
      </button>
</div>`;
  }
  function reasonBox(s, r) {
    return `<div class="sl-why"><div class="sl-wt">${esc(r.name)} ${esc(r.code)}・為什麼入選「${esc(s.name)}」</div><ul>${check(s, r).map((c) => `<li class="${c.pass ? 'y' : 'n'}"><span class="mk">${c.pass ? '✓' : '✗'}</span>${esc(c.label)}　<b>${esc(c.txt)}</b>${c.skip ? '' : ` <small>${esc(c.thTxt)}</small>`}</li>`).join('')}</ul>
      <a class="sl-go" href="#stock/${esc(r.code)}">看個股頁 →</a></div>`;
  }
  function cardHTML(s) {
    const can = usable(s), m = matches(s);
    return `<article class="sl-card" data-sid="${s.id}" data-cat="${s.cat}">
      <header class="sl-ch">
        <span class="sl-ici sl-c-${s.cat}">${icon(s.cat)}</span>
        <div class="sl-tt" title="${esc(s.zh)}"><h3 class="sl-zh">${esc(s.name)}</h3><div class="sl-en">${esc(s.en)}</div></div>
        <button type="button" class="sl-i${ST.info[s.id] ? ' on' : ''}" data-i="${s.id}" aria-expanded="${!!ST.info[s.id]}" aria-label="篩選條件">i</button>
        <a class="sl-more" href="#explore/${s.id}" aria-label="看 ${esc(s.name)} 完整名單">›</a>
      </header>
      <div class="sl-meta">${can ? `符合 <em class="sl-n">${m.length}</em> 家・依成交值排序，非推薦名次` : '尚無資料'}</div>
      <div class="sl-rows">${can && m.length ? m.slice(0, 3).map((r, i) => rowHTML(s, r, i)).join('') + '<div class="sl-row sl-blank" aria-hidden="true"></div>'.repeat(Math.max(0, 3 - m.length))
        : `<div class="sl-none">${can ? '目前沒有符合的公司' : ''}</div>`}</div>
    </article>`;
  }
  /* ★ 第四版：卡片牆依四大面向分區 —— 每區一個區段標題（名稱＋這區在回答什麼＋幾個策略）＋該區卡片（三欄、同寬同高）。
     點晶片只留那一區；「全部」就四區依序排。某區被子標籤篩到 0 張就整區不畫（不留空標題）。 */
  function paintGrid() {
    const cats = [CBY[ST.cat] || CATS[0]];
    $('#slGrid').innerHTML = cats.map(([k, en, zh, q]) => {
      const list = S_.filter((s) => s.cat === k && (!ST.tags.length || ST.tags.some((t) => s.tags.includes(t))));
      if (!list.length) return '';
      return `<section class="sl-sec" data-cat="${k}" aria-label="${esc(zh)}">
        <h3 class="sl-sech" title="${esc(q)}"><span class="sl-ici sl-c-${k}">${icon(k)}</span>${esc(zh)}
          <em class="sl-secn">${list.length} 個策略</em></h3>
        <div class="sl-grid">${list.map(cardHTML).join('')}</div></section>`;
    }).join('');
    upgrade($('#slGrid'));
  }
  function paintCard(id) {
    const el = $(`.sl-card[data-sid="${id}"]`); if (!el) return;
    const t = document.createElement('div'); t.innerHTML = cardHTML(SBY[id]);
    el.replaceWith(t.firstElementChild); upgrade($(`.sl-card[data-sid="${id}"]`));
  }
  function upgrade(root) {
    const A = App();
    if (A.sparkLoad) A.sparkLoad().then(() => { $$('.spkw[data-spk]:empty', root).forEach((el) => { el.innerHTML = A.sparkSVG(el.dataset.spk, { w: +el.dataset.w, h: +el.dataset.h }); }); });
    if (A.logoMapLoad) A.logoMapLoad().then(() => A.logoUpgrade && A.logoUpgrade(root));
  }

  /* ---------------- 浮層：「為什麼入選」與「i」 ----------------
     Andy：「版面都要固定大小，不是一大一小」。以前原因與出處在卡內原地展開，會把那張卡撐高、整列跟著變形；
     改成貼在按鈕旁的浮層（position:fixed，掛在 body 下），卡片高度永遠不動。點外面、Esc、換頁都會關；捲動時跟著按鈕重新定位。 */
  function closePop() {
    const p = $('#slPop'); if (p) p.remove();
    ST.open = {}; ST.info = {};
    $$('#v-explore .sl-row.open').forEach((el) => el.classList.remove('open'));
    $$('#v-explore .sl-rbtn[aria-expanded="true"],#v-explore .sl-i.on').forEach((el) => { el.setAttribute('aria-expanded', 'false'); el.classList.remove('on'); });
  }
  function openPop(anchor, html, kind) {
    closePop();
    const p = document.createElement('div');
    p.id = 'slPop'; p.className = `sl-pop sl-pop-${kind}`; p.setAttribute('role', 'dialog');
    p.innerHTML = `<button type="button" class="sl-pop-x" aria-label="關閉">×</button>${html}`;
    document.body.appendChild(p);
    POP.anchor = anchor; placePop();
  }
  const POP = { anchor: null };
  /* 浮層跟著按鈕走：捲動時重新定位，而不是關掉（Playwright／使用者點按鈕前的自動捲動也會發 scroll，
     一捲就關會讓剛打開的浮層立刻消失） */
  function placePop() {
    const p = $('#slPop'), an = POP.anchor; if (!p) return;
    if (!an || !an.isConnected) { closePop(); return; }
    const a = an.getBoundingClientRect(), w = p.offsetWidth, h = p.offsetHeight;
    const x = Math.min(Math.max(8, a.left), innerWidth - w - 8);
    let y = a.bottom + 6; if (y + h > innerHeight - 8) y = Math.max(8, a.top - h - 6);
    p.style.left = `${x}px`; p.style.top = `${y}px`;
  }
  document.addEventListener('click', (e) => {
    if (!$('#slPop')) return;
    if (e.target.closest('.sl-pop-x') || (!e.target.closest('#slPop') && !e.target.closest('.sl-rbtn,.sl-i'))) closePop();
  });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closePop(); });
  window.addEventListener('scroll', placePop, { passive: true });
  window.addEventListener('resize', placePop);
  window.addEventListener('hashchange', closePop);

  /* ---------------- 畫面：完整名單頁（#explore/<id>） ---------------- */
  const FULL = { n: 100 };
  function paintFull(root, s) {
    const m = matches(s), can = usable(s);
    const others = (r) => S_.filter((o) => o.id !== s.id && usable(o) && matches(o).includes(r)).map((o) => o.name);
    const rows = m.slice(0, FULL.n).map((r, i) => {
      const cs = check(s, r), kv = s.key[1](r), ot = others(r);
      return `<tr data-code="${esc(r.code)}"><td class="num">${i + 1}</td>
        <td><a href="#stock/${esc(r.code)}" class="sl-tlink">${logo(r, 20)}<b>${esc(r.name)}</b> <small>${esc(r.code)}</small></a><div class="sl-grp">${esc(r.group)}</div></td>
        <td class="num">${n1(r.close, r.close >= 100 ? 1 : 2)}<div class="${chgCls(r.chg)}">${chgTxt(r.chg)}</div></td>
        <td>${spark(r.code, 72, 24)}</td>
        <td class="num"><b>${ok(kv) ? esc(s.key[2](kv, r)) : '—'}</b></td>
        <td class="sl-rsn">${cs.map((c) => `<span class="${c.pass ? 'y' : 'n'}">${esc(reasonLine(c))}</span>`).join('')}</td>
        <td class="sl-oth">${ot.length ? ot.map((x) => `<span>${esc(x)}</span>`).join('') : '—'}</td></tr>`;
    }).join('');
    root.innerHTML = `${LEGAL}
      <div class="sl-fhead"><a href="#explore" class="sl-back">‹ 選股策略</a>
        <h2><span class="sl-ici sl-c-${s.cat}">${icon(s.cat)}</span>${esc(s.name)} <small>${esc(s.zh)}・${esc(s.en)}</small></h2></div>
      <div class="card sl-finfo"><h3>篩選條件 ${srcI(srcOf(s))}</h3>${infoHTML(s)}</div>
      <div class="card sl-ftbl"><h3>${can ? `符合的公司 <em class="sl-n" id="slFullN">${m.length}</em> 家 <small>依近 20 日平均成交值排序（流動性），不是好壞名次</small>` : '尚無資料'}</h3>
        ${can && m.length ? `<div class="sl-tw"><table class="sl-table" id="slTbl"><thead><tr><th>#</th><th>公司</th><th>現價／漲跌</th><th>走勢</th><th>${esc(s.key[0])}</th><th>為什麼入選（實際值／門檻）</th><th>也符合</th></tr></thead><tbody>${rows}</tbody></table></div>
        ${m.length > FULL.n ? `<button type="button" class="sl-all" id="slAll">顯示全部 ${m.length} 家</button>` : ''}` : (can ? '<div class="sl-none">今天沒有公司同時符合全部條件。</div>' : '')}</div>`;
    root.onclick = onClick;
    upgrade(root);
  }

  /* ---------------- 互動 ---------------- */
  function onClick(e) {
    const ch = e.target.closest('.sl-chip'); if (ch) { ST.cat = ch.dataset.cat; ST.tags = []; ST.dd = false; paintChips(); paintGrid(); return; }
    if (e.target.closest('#slTagDd')) { ST.dd = !ST.dd; paintChips(); return; }
    const tg = e.target.closest('input[data-tag]');
    if (tg) { const t = tg.dataset.tag; ST.tags = tg.checked ? [...ST.tags, t] : ST.tags.filter((x) => x !== t); paintChips(); paintGrid(); return; }
    if (e.target.closest('.sl-ddclr')) { ST.tags = []; paintChips(); paintGrid(); return; }
    if (e.target.closest('.sl-ddok')) { ST.dd = false; paintChips(); return; }
    if (e.target.closest('#slTagMenu')) return;
    if (ST.dd) { ST.dd = false; paintChips(); }
    const ib = e.target.closest('.sl-i'); if (ib) {
      const id = ib.dataset.i, was = ST.info[id]; closePop(); if (was) return;
      ST.info[id] = true; ib.classList.add('on'); ib.setAttribute('aria-expanded', 'true');
      openPop(ib, `<div class="sl-wt">${esc(SBY[id].name)}：篩選條件 ${srcI(srcOf(SBY[id]))}</div>${infoBrief(SBY[id])}`, 'info'); return;
    }
    const rb = e.target.closest('.sl-rbtn'); if (rb) {
      const row = rb.closest('.sl-row'), id = row.dataset.sid, code = row.dataset.code;
      const was = ST.open[id] === code; closePop(); if (was) return;
      ST.open[id] = code; row.classList.add('open'); rb.setAttribute('aria-expanded', 'true');
      openPop(rb, reasonBox(SBY[id], RBY[code]), 'why'); return;
    }
    const all = e.target.closest('#slAll'); if (all) { FULL.n = 1e9; const s = SBY[(location.hash.split('/')[1] || '')]; if (s) paintFull($('#v-explore'), s); }
  }

  async function render(sub) {
    const root = $('#v-explore'); if (!root) return;
    root.innerHTML = '<div class="card"><div class="empty">選股策略載入中…</div></div>';
    try { await loadAll(); } catch (e) { root.innerHTML = '<div class="card"><div class="empty">資料載入失敗，請重新整理</div></div>'; return; }
    built = true; show(sub);
  }
  function show(sub) {
    if (!built) return render(sub);
    const root = $('#v-explore'); if (!root) return;
    FULL.n = 100;
    if (SBY[sub]) { paintFull(root, SBY[sub]); window.scrollTo(0, 0); return; }
    closePop(); shellWall(root); paintChips(); paintGrid();
  }
  window.TwExplore = {
    render, show, S: S_, SRC,
    /* 給 _uitest.py 對帳用：每個策略的符合清單（依成交值排序）與可用與否 */
    debug: () => ({ n: R.length, have: Object.assign({}, HAVE), cat: ST.cat,
      hits: Object.fromEntries(S_.map((s) => [s.id, matches(s).map((r) => r.code)])),
      usable: Object.fromEntries(S_.map((s) => [s.id, usable(s)])) }),
  };
})();
