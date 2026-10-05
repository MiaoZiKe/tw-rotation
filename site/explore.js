/* ============================================================================
   選股策略（#explore）—— site/explore.js（Andy 2026-10-05 第二版，規格：docs/explore_page_spec.md）
   ----------------------------------------------------------------------------
   第一版是「六個白話問題＋泡泡圖」。Andy 看過後改方向：「改成圖片那樣類似好了，策略但寫成英文，
   並且不同面向為何篩選那些公司需要標示原因說明清楚，最好附上資料出處」。

   所以這一版是「策略卡片牆」：
     · 每個策略一張卡（英文標題＋一行中文翻譯），卡內列前 3 檔（依成交值排序 —— 不是好壞名次）。
     · 每一列點開 → 條件逐條打勾＋實際數值（為什麼入選），不讓使用者自己去猜。
     · 每張卡的「i」→ 白話條件、門檻、計算方式、資料日期、資料出處（照 pipeline/sources 實際來源寫）。
     · 「>」→ #explore/<策略 id> 完整名單頁：全部符合的公司＋每檔原因欄＋出處。
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
  const LS = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* 私密視窗 */ } },
  };
  const ok = (v) => v != null && isFinite(v);
  const n1 = (v, d) => (ok(v) ? Number(v).toFixed(d == null ? 1 : d) : '—');
  const MIN_TV = 10;          // 近 20 日平均成交值下限（百萬元）

  /* ---------------- 資料出處（照 pipeline/sources 與 docs/v3_sources_spec.md 實際走的路寫，不要編） ---------------- */
  const SRC = {
    price: ['股價（日 K）', '臺灣證券交易所 OpenAPI（STOCK_DAY_ALL，上市）、證券櫃檯買賣中心（上櫃；被擋時由 FinMind TaiwanStockPrice 補）'],
    fin: ['財報（EPS、毛利率、ROE）', '臺灣證券交易所 OpenAPI t187ap14_L（公開資訊觀測站彙整）；歷史由 FinMind TaiwanStockFinancialStatements／TaiwanStockBalanceSheet 回補'],
    rev: ['月營收', '臺灣證券交易所 OpenAPI t187ap05_L（公開資訊觀測站彙整）；歷史由 FinMind TaiwanStockMonthRevenue 回補'],
    per: ['本益比', '臺灣證券交易所 OpenAPI BWIBBU_ALL；歷史由 FinMind TaiwanStockPER 回補'],
    div: ['股利', '臺灣證券交易所 OpenAPI t187ap45_L；歷史由 FinMind TaiwanStockDividend 回補'],
    inst: ['三大法人買賣超', 'FinMind TaiwanStockInstitutionalInvestorsBuySell（個股別法人資料在證交所只放官網，官網條款禁止程式抓取，所以改走 FinMind）'],
    tech: ['技術指標', '本站以日 K 自行計算（pipeline/indicators.py：均線、MACD 用 DIF/MACD/OSC、RSI 用 Wilder）'],
    calc: ['衍生數值', '本站自行計算（pipeline/compute/explore.py、compute/fundamental.py）'],
  };

  /* ---------------- 分類（晶片） ---------------- */
  const CATS = [
    ['all', 'All', '全部'], ['fund', 'Fundamentals', '基本面'], ['val', 'Valuation', '估值面'], ['grow', 'Growth', '成長'],
    ['tech', 'Technicals', '技術面'], ['chip', 'Institutional', '籌碼面'], ['divd', 'Dividend', '股利'], ['mom', 'Momentum', '動能'],
  ];
  const ICON = {   // 簡單線條圖示（currentColor），一個分類一個
    fund: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
    val: '<circle cx="12" cy="12" r="8"/><path d="M12 7v10M9 9.5h4.5a2 2 0 010 4H10a2 2 0 000 4h5"/>',
    grow: '<path d="M3 17l6-6 4 4 8-8M15 7h6v6"/>',
    tech: '<path d="M3 12h4l3-7 4 14 3-7h4"/>',
    chip: '<path d="M4 20h16M6 16V9m4 7V6m4 10v-5m4 5V4"/>',
    divd: '<path d="M12 3v18M7 8c0-2 2-3 5-3s5 1 5 3-2 3-5 3-5 1-5 3 2 3 5 3 5-1 5-3"/>',
    mom: '<path d="M13 3L4 14h7l-1 7 9-11h-7z"/>',
  };
  const icon = (c) => `<svg class="sl-ic" viewBox="0 0 24 24" aria-hidden="true">${ICON[c] || ''}</svg>`;

  /* ---------------- 策略 ----------------
     conds：每一條 [標籤, 取值, 比較, 門檻, 格式]。符合＝全部條件成立；理由就是逐條把「實際值 vs 門檻」寫出來。
     key：卡片右側那一個關鍵指標。need：要哪一份資料（缺就顯示「資料準備中」，不要硬算）。 */
  const pct = (v) => `${n1(v)}%`;
  const days = (v) => `${ok(v) ? Math.round(v) : '—'} 天`;
  const S_ = [
    { id: 'quality', cat: 'fund', en: 'Quality Earners', zh: '高獲利品質：ROE 與毛利率都高', tags: ['ROE', 'Margin'],
      conds: [['ROE（近四季）', (r) => r.roe, '>=', 15, pct], ['毛利率（近四季）', (r) => r.gm, '>=', 20, pct, (r) => r.fin]],
      key: ['ROE', (r) => r.roe, pct], src: ['fin', 'calc'], date: 'fin',
      how: 'ROE＝近四季稅後淨利 ÷ 平均股東權益；毛利率＝近四季毛利 ÷ 營收。金融業沒有毛利率，只看 ROE。',
      care: '景氣循環股在高峰時 ROE 最漂亮；借很多錢的公司 ROE 也會被墊高。' },
    { id: 'margin', cat: 'fund', en: 'Margin Leaders', zh: '毛利率領先：產品有議價力', tags: ['Margin', 'Profit'],
      conds: [['毛利率（近四季）', (r) => r.gm, '>=', 40, pct], ['近四季有獲利', (r) => (r.loss ? 0 : (r.eps != null ? 1 : null)), '>=', 1, (v) => (v ? '是' : '否')]],
      key: ['毛利率', (r) => r.gm, pct], src: ['fin', 'calc'], date: 'fin',
      how: '毛利率＝近四季毛利 ÷ 近四季營收；獲利＝近四季 EPS 合計 > 0。',
      care: '不同產業的正常毛利率差很多（軟體、IC 設計天生高），最好跟同業比。' },
    { id: 'below', cat: 'val', en: 'Below Own History', zh: '比自己過去便宜：本益比在自身 5 年低檔', tags: ['P/E', 'History'], need: 'ex',
      conds: [['本益比歷史位置（0＝最便宜）', (r) => r.pepct, '<=', 30, (v) => `第 ${n1(v, 0)} 百分位`], ['本益比（有獲利）', (r) => r.pe, '>', 0, (v) => `${n1(v)} 倍`]],
      key: ['P/E 位置', (r) => r.pepct, (v) => `P${n1(v, 0)}`], src: ['per', 'fin', 'calc'], date: 'ex',
      how: '把目前本益比放進「這家公司自己近 5 年各季本益比」裡排位置（至少 8 季才算）。不跨族群比（不同產業本益比天生不同）。',
      care: '便宜可能有原因：市場預期它未來獲利會下滑。' },
    { id: 'value', cat: 'val', en: 'Low P/E, Real Profits', zh: '低本益比且真的有賺', tags: ['P/E', 'ROE'],
      conds: [['本益比', (r) => r.pe, '<=', 12, (v) => `${n1(v)} 倍`, null, 0], ['ROE（近四季）', (r) => r.roe, '>=', 10, pct]],
      key: ['P/E', (r) => r.pe, (v) => `${n1(v)}x`], src: ['per', 'fin', 'calc'], date: 'fin',
      how: '本益比＝收盤價 ÷ 近四季 EPS（虧損公司沒有本益比，不會入選）；再要求 ROE ≥ 10%，排除「便宜但不太賺」的。',
      care: '金融、航運、原物料等景氣股本益比常年偏低，低不一定代表被低估。' },
    { id: 'accel', cat: 'grow', en: 'Revenue Accelerators', zh: '營收加速：月營收連續年增', tags: ['Revenue', 'YoY'],
      conds: [['月營收連續年增', (r) => r.rs, '>=', 3, (v) => `${ok(v) ? v : '—'} 個月`], ['最新一月營收年增', (r) => r.ry, '>=', 10, pct]],
      key: ['營收 YoY', (r) => r.ry, (v) => `${v >= 0 ? '+' : ''}${n1(v)}%`], src: ['rev', 'calc'], date: 'rev',
      how: '年增率＝當月營收 ÷ 去年同月營收 − 1；連續月數＝年增率連續為正的月份數。跟去年同月比可以避開淡旺季。',
      care: '去年同期如果特別差（基期低），年增率會看起來很漂亮。' },
    { id: 'record', cat: 'grow', en: 'Record-High Sales', zh: '月營收創歷史新高', tags: ['Revenue', 'Record'],
      conds: [['最新月營收創歷史新高', (r) => (r.rec ? 1 : 0), '>=', 1, (v) => (v ? '是' : '否')], ['最新一月營收年增', (r) => r.ry, '>', 0, pct]],
      key: ['營收 YoY', (r) => r.ry, (v) => `${v >= 0 ? '+' : ''}${n1(v)}%`], src: ['rev', 'calc'], date: 'rev',
      how: '最新公布的月營收高於本站資料湖裡這家公司過去每一個月的營收，而且比去年同月成長。',
      care: '月營收創高不等於獲利創高：毛利可能在下滑。' },
    { id: 'accum', cat: 'chip', en: 'Institutional Accumulation', zh: '三大法人連續淨買超', tags: ['3 Institutions', 'Streak'], need: 'inst',
      conds: [['三大法人合計連續淨買超', (r) => r.bd, '>=', 5, days]],
      key: ['連買', (r) => r.bd, (v) => `${v} 天`], src: ['inst', 'calc'], date: 'inst',
      how: '外資＋投信＋自營商每日買賣超相加，從最近一個交易日往回數連續為正的天數；今天一轉賣就歸零。',
      care: '法人也會看錯；外資有時只是被動調整指數成分。' },
    { id: 'trust', cat: 'chip', en: 'Fund Manager Favorites', zh: '投信連續買超', tags: ['Investment Trust', 'Streak'], need: 'streak',
      conds: [['投信連續買超', (r) => r.td, '>=', 3, days]],
      key: ['投信連買', (r) => r.td, (v) => `${v} 天`], src: ['inst', 'calc'], date: 'inst',
      how: '只看投信（國內基金）每日買賣超，從最近一個交易日往回數連續為正的天數。本站只保留連買天數前 60 名。',
      care: '投信季底常有「作帳」買盤，季初可能反手。' },
    { id: 'steady', cat: 'tech', en: 'Steady Uptrend', zh: '穩健上升：低波動且站上均線', tags: ['Low Vol', 'MA'], need: 'ex',
      conds: [['60 日年化波動度', (r) => r.vol, '<=', 30, pct], ['收盤站上 20 日均線', (r) => r.a20, '>=', 1, (v) => (v ? '是' : '否')], ['收盤站上 60 日均線', (r) => r.a60, '>=', 1, (v) => (v ? '是' : '否')]],
      key: ['波動度', (r) => r.vol, pct], src: ['price', 'tech', 'calc'], date: 'ex',
      how: '波動度＝近 60 日日報酬標準差 × √252（年化）；均線用還原後日 K 收盤價。',
      care: '穩不代表會漲，可能只是盤整；財報或消息可能讓它突然大動。' },
    { id: 'macd', cat: 'tech', en: 'Bullish MA Alignment', zh: '均線多頭排列＋MACD 柱翻正', tags: ['MA', 'MACD'], need: 'cand',
      conds: [['均線多頭排列（5>20>60）', (r) => r.align, '>=', 1, (v) => (v === 1 ? '是' : '否')], ['MACD 柱（OSC）', (r) => r.osc, '>', 0, (v) => n1(v, 2)], ['RSI(14) 未過熱', (r) => r.rsi, '<=', 70, (v) => n1(v)]],
      key: ['OSC', (r) => r.osc, (v) => `${v >= 0 ? '+' : ''}${n1(v, 2)}`], src: ['price', 'tech'], date: 'ex',
      how: '只涵蓋本站技術面候選池（每天由管線依成交值與技術分數先篩出的數百檔），不是全市場。OSC＝DIF − MACD。',
      care: '技術訊號會反覆；多頭排列常出現在已經漲一段之後。' },
    { id: 'lead', cat: 'mom', en: '60-Day Leaders', zh: '近 60 日漲幅領先且仍站上均線', tags: ['Return', 'Trend'], need: 'ex',
      conds: [['近 60 日漲跌', (r) => r.ret, '>=', 20, pct], ['收盤站上 20 日均線', (r) => r.a20, '>=', 1, (v) => (v ? '是' : '否')]],
      key: ['60 日', (r) => r.ret, (v) => `${v >= 0 ? '+' : ''}${n1(v)}%`], src: ['price', 'calc'], date: 'ex',
      how: '近 60 日漲跌＝今天收盤 ÷ 60 個交易日前收盤 − 1（還原權息）。',
      care: '已經漲多的股票波動也大，回檔幅度常常很深。' },
    { id: 'volup', cat: 'mom', en: 'Volume Surge', zh: '帶量上漲：成交量放大且收紅', tags: ['Volume', 'Price'], need: 'cand',
      conds: [['量比（今日量 ÷ 5 日均量）', (r) => r.vr, '>=', 2, (v) => `${n1(v)} 倍`], ['今日漲跌', (r) => r.chg, '>', 0, pct]],
      key: ['量比', (r) => r.vr, (v) => `${n1(v)}x`], src: ['price', 'tech'], date: 'ex',
      how: '只涵蓋本站技術面候選池。量比＝今日成交量 ÷ 近 5 日平均量。',
      care: '爆量可能是主力出貨或消息面一次性反應，隔天常見反轉。' },
    { id: 'divcon', cat: 'divd', en: 'Dividend Consistency', zh: '穩定配息：殖利率不低且連年配現金', tags: ['Yield', 'Years'], need: 'ex',
      conds: [['近 12 個月現金殖利率', (r) => r.dy, '>=', 4, (v) => `${n1(v, 2)}%`], ['連續配現金股利', (r) => r.dv, '>=', 5, (v) => `${ok(v) ? v : '—'} 年`]],
      key: ['殖利率', (r) => r.dy, (v) => `${n1(v, 2)}%`], src: ['div', 'price', 'calc'], date: 'ex',
      how: '殖利率＝近 12 個月現金股利 ÷ 目前股價；連續年數從去年往回數（今年還沒過完不算）。',
      care: '股價大跌也會讓殖利率變高；配息後要填息才算真的賺到。' },
  ];
  const SBY = {}; S_.forEach((s) => { SBY[s.id] = s; });
  const OPS = { '>=': (a, b) => a >= b, '<=': (a, b) => a <= b, '>': (a, b) => a > b };

  /* ---------------- 狀態與資料 ---------------- */
  const ST = { cat: LS.get('tw.explore.cat') || 'all', tag: '', open: {}, info: {} };
  const HAVE = { ex: false, cand: false, streak: false, inst: false };
  let R = [], RBY = {}, built = false, DATES = {};

  async function loadAll() {
    const A = App();
    const get = (n) => (A.load ? A.load(n).catch(() => null) : Promise.resolve(null));
    const [fund, stocks, ex, cand, streak] = await Promise.all(['fundamental', 'stocks', 'explore', 'candidates', 'inst_streak'].map(get));
    HAVE.ex = !!(ex && Array.isArray(ex.rows) && ex.rows.length);
    HAVE.cand = Array.isArray(cand) && cand.length > 0;
    HAVE.streak = !!(streak && Array.isArray(streak.trust));
    HAVE.inst = HAVE.ex || !!(streak && Array.isArray(streak.total));
    const fx = {}; (fund || []).forEach((f) => { fx[f.code] = f; });
    const exRow = {};
    if (HAVE.ex) ex.rows.forEach((row) => { const o = {}; ex.cols.forEach((c, i) => { o[c] = row[i]; }); exRow[o.code] = o; });
    const cd = {}; (cand || []).forEach((c) => { cd[c.code] = c; });
    const td = {}; ((streak && streak.trust) || []).forEach((s) => { td[s.code] = s.streak_days; });
    const tot = {}; ((streak && streak.total) || []).forEach((s) => { tot[s.code] = s.streak_days; });
    const per = {}, ym = {}, instD = {};
    ((streak && streak.total) || []).forEach((s) => { if (s.date) instD[s.date] = 1; });
    const rows = [];
    (stocks || []).forEach((s) => {
      const f = fx[s.code] || {};
      if (!s.code || /^00/.test(s.code) || s.group_id === 'ind_ETF' || f.group_id === 'ind_ETF') return;
      const e = exRow[s.code] || {}, c = cd[s.code] || {};
      const tv = e.tv20 != null ? e.tv20 : (s.turnover != null ? s.turnover / 1e6 : null);
      if (tv == null || tv < MIN_TV) return;
      if (f.latest_period) per[f.latest_period] = (per[f.latest_period] || 0) + 1;
      if (f.rev_ym) ym[f.rev_ym] = (ym[f.rev_ym] || 0) + 1;
      rows.push({
        code: s.code, name: s.name || f.name || s.code, group: s.group || f.group_name || '—', close: s.close, chg: s.chg_pct, tv,
        roe: f.roe, gm: f.gross_margin, pe: f.pe, eps: f.ttm_eps, loss: !!f.is_loss, fin: /金融|銀行|保險|證券|金控/.test(s.group || f.group_name || '') && f.gross_margin == null,
        ry: f.rev_yoy, rs: f.rev_streak, rec: !!f.rev_record_high,
        pepct: e.pe_pct, vol: e.vol60, a20: e.above20, a60: e.above60, ret: e.ret60, dy: e.dy, dv: e.div_years,
        bd: HAVE.ex ? e.buy_days : (tot[s.code] || 0),
        td: td[s.code] || 0,
        align: c.ma_align, osc: c.osc, rsi: c.rsi, vr: c.vol_ratio, inCand: !!cd[s.code],
      });
    });
    const top = (o) => Object.keys(o).sort((a, b) => o[b] - o[a])[0] || '';
    const m = A.D && A.D.meta;
    const day = (ex && ex.asof) || (m && (m.data_date || m.price_latest)) || '';
    DATES = { fin: top(per) ? `財報 ${top(per)}` : '', rev: top(ym) ? `營收 ${top(ym)}` : '', ex: day ? `資料 ${day}` : '',
      inst: (Object.keys(instD).sort().pop() || (m && m.inst_date) || day) ? `法人 ${Object.keys(instD).sort().pop() || (m && m.inst_date) || day}` : '' };
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
  const srcHTML = (s) => `<dl class="sl-src">${s.src.map((k) => `<dt>${esc(SRC[k][0])}</dt><dd>${esc(SRC[k][1])}</dd>`).join('')}</dl>`;
  const condTxt = (s) => s.conds.map(([label, , op, th, fmt]) => `${label} ${op === '>=' ? '≥' : op === '<=' ? '≤' : '>'} ${fmt(th)}`).join('，且 ');
  function infoHTML(s) {
    return `<div class="sl-info" data-info="${s.id}">
      <p><b>篩選條件：</b>${esc(condTxt(s))}。</p>
      <p><b>計算方式：</b>${esc(s.how)}</p>
      <p><b>共同門檻：</b>排除 ETF，以及近 20 日平均成交值低於 1,000 萬元的冷門股（成交太少，價格不可靠）。</p>
      <p><b>資料日期：</b>${esc(DATES[s.date] || '—')}</p>
      <p><b>資料出處：</b></p>${srcHTML(s)}
      <p class="sl-care"><b>要小心：</b>${esc(s.care)}</p></div>`;
  }

  /* ---------------- 畫面：策略卡片牆 ---------------- */
  const LEGAL = '<div class="xp-legal" role="note" id="xpLegal">條件篩選結果僅供研究，不構成投資建議；本站非證券投資顧問。名單依成交值排序，不是好壞名次。</div>';
  function shellWall(root) {
    root.innerHTML = `${LEGAL}
      <div class="sl-head"><h2>Strategy Lab <small>選股策略：每張卡是一組公開條件，點一列看「為什麼入選」，點 i 看條件與資料出處</small></h2></div>
      <div class="sl-chips" id="slChips" role="tablist" aria-label="Filter"></div>
      <div class="sl-tags" id="slTags"></div>
      <div class="sl-grid" id="slGrid"></div>`;
    root.onclick = onClick;
  }
  function paintChips() {
    const cnt = (c) => S_.filter((s) => c === 'all' || s.cat === c).length;
    $('#slChips').innerHTML = CATS.map(([k, en, zh]) => `<button type="button" class="sl-chip${ST.cat === k ? ' on' : ''}" data-cat="${k}" role="tab" aria-selected="${ST.cat === k}" title="${esc(zh)}">${esc(en)} <em>${cnt(k)}</em></button>`).join('');
    const tags = [...new Set(S_.filter((s) => ST.cat === 'all' || s.cat === ST.cat).flatMap((s) => s.tags))];
    if (ST.tag && !tags.includes(ST.tag)) ST.tag = '';
    $('#slTags').innerHTML = `<span class="sl-tl">Tags</span>` + ['', ...tags].map((t) => `<button type="button" class="sl-tag${ST.tag === t ? ' on' : ''}" data-tag="${esc(t)}">${t ? esc(t) : 'Any'}</button>`).join('');
  }
  function rowHTML(s, r, i) {
    const k = s.key, kv = k[1](r), open = ST.open[s.id] === r.code;
    return `<div class="sl-row${open ? ' open' : ''}" data-sid="${s.id}" data-code="${esc(r.code)}">
      <button type="button" class="sl-rbtn" aria-expanded="${open}" title="${esc(check(s, r).map(reasonLine).join('\n'))}">
        <span class="sl-rank">${i + 1}</span>${logo(r, 26)}
        <span class="sl-nm"><b>${esc(r.name)}</b><small>${esc(r.code)}</small></span>
        <span class="sl-px"><b>${n1(r.close, r.close >= 100 ? 1 : 2)}</b><small class="${chgCls(r.chg)}">${chgTxt(r.chg)}</small></span>
        ${spark(r.code, 64, 24)}
        <span class="sl-key"><small>${esc(k[0])}</small><b>${ok(kv) ? esc(k[2](kv)) : '—'}</b></span>
      </button>
      ${open ? reasonBox(s, r) : ''}</div>`;
  }
  function reasonBox(s, r) {
    return `<div class="sl-why"><div class="sl-wt">為什麼入選</div><ul>${check(s, r).map((c) => `<li class="${c.pass ? 'y' : 'n'}"><span class="mk">${c.pass ? '✓' : '✗'}</span>${esc(c.label)}　<b>${esc(c.txt)}</b>${c.skip ? '' : ` <small>${esc(c.thTxt)}</small>`}</li>`).join('')}</ul>
      <a class="sl-go" href="#stock/${esc(r.code)}">看個股頁 →</a></div>`;
  }
  function cardHTML(s) {
    const can = usable(s), m = matches(s);
    return `<article class="sl-card" data-sid="${s.id}" data-cat="${s.cat}">
      <header class="sl-ch">
        <span class="sl-ici sl-c-${s.cat}">${icon(s.cat)}</span>
        <div class="sl-tt"><h3 class="sl-en">${esc(s.en)}</h3><div class="sl-zh">${esc(s.zh)}</div></div>
        <span class="sl-date">${esc(DATES[s.date] || '')}</span>
        <button type="button" class="sl-i${ST.info[s.id] ? ' on' : ''}" data-i="${s.id}" aria-expanded="${!!ST.info[s.id]}" aria-label="篩選條件與資料出處">i</button>
        <a class="sl-more" href="#explore/${s.id}" aria-label="看 ${esc(s.en)} 完整名單">›</a>
      </header>
      ${ST.info[s.id] ? infoHTML(s) : ''}
      <div class="sl-meta">${can ? `符合 <em class="sl-n">${m.length}</em> 家・依成交值排序，非推薦名次` : '資料準備中（這個策略要的歷史欄位還沒產出）'}</div>
      <div class="sl-rows">${can ? (m.length ? m.slice(0, 3).map((r, i) => rowHTML(s, r, i)).join('') : '<div class="sl-none">今天沒有公司同時符合全部條件。</div>') : ''}</div>
    </article>`;
  }
  function paintGrid() {
    const list = S_.filter((s) => (ST.cat === 'all' || s.cat === ST.cat) && (!ST.tag || s.tags.includes(ST.tag)));
    $('#slGrid').innerHTML = list.map(cardHTML).join('');
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

  /* ---------------- 畫面：完整名單頁（#explore/<id>） ---------------- */
  const FULL = { n: 100 };
  function paintFull(root, s) {
    const m = matches(s), can = usable(s);
    const others = (r) => S_.filter((o) => o.id !== s.id && usable(o) && matches(o).includes(r)).map((o) => o.en);
    const rows = m.slice(0, FULL.n).map((r, i) => {
      const cs = check(s, r), kv = s.key[1](r), ot = others(r);
      return `<tr data-code="${esc(r.code)}"><td class="num">${i + 1}</td>
        <td><a href="#stock/${esc(r.code)}" class="sl-tlink">${logo(r, 20)}<b>${esc(r.name)}</b> <small>${esc(r.code)}</small></a><div class="sl-grp">${esc(r.group)}</div></td>
        <td class="num">${n1(r.close, r.close >= 100 ? 1 : 2)}<div class="${chgCls(r.chg)}">${chgTxt(r.chg)}</div></td>
        <td>${spark(r.code, 72, 24)}</td>
        <td class="num"><b>${ok(kv) ? esc(s.key[2](kv)) : '—'}</b></td>
        <td class="sl-rsn">${cs.map((c) => `<span class="${c.pass ? 'y' : 'n'}">${esc(reasonLine(c))}</span>`).join('')}</td>
        <td class="sl-oth">${ot.length ? ot.map((x) => `<span>${esc(x)}</span>`).join('') : '—'}</td></tr>`;
    }).join('');
    root.innerHTML = `${LEGAL}
      <div class="sl-fhead"><a href="#explore" class="sl-back">‹ Strategy Lab</a>
        <h2><span class="sl-ici sl-c-${s.cat}">${icon(s.cat)}</span>${esc(s.en)} <small>${esc(s.zh)}</small></h2>
        <span class="sl-date">${esc(DATES[s.date] || '')}</span></div>
      <div class="card sl-finfo"><h3>篩選條件與資料出處</h3>${infoHTML(s)}</div>
      <div class="card sl-ftbl"><h3>${can ? `符合的公司 <em class="sl-n" id="slFullN">${m.length}</em> 家 <small>依近 20 日平均成交值排序（流動性），不是好壞名次</small>` : '資料準備中'}</h3>
        ${can && m.length ? `<div class="sl-tw"><table class="sl-table" id="slTbl"><thead><tr><th>#</th><th>公司</th><th>現價／漲跌</th><th>走勢</th><th>${esc(s.key[0])}</th><th>為什麼入選（實際值／門檻）</th><th>也符合</th></tr></thead><tbody>${rows}</tbody></table></div>
        ${m.length > FULL.n ? `<button type="button" class="sl-all" id="slAll">顯示全部 ${m.length} 家</button>` : ''}` : (can ? '<div class="sl-none">今天沒有公司同時符合全部條件。</div>' : '')}</div>`;
    root.onclick = onClick;
    upgrade(root);
  }

  /* ---------------- 互動 ---------------- */
  function onClick(e) {
    const ch = e.target.closest('.sl-chip'); if (ch) { ST.cat = ch.dataset.cat; ST.tag = ''; LS.set('tw.explore.cat', ST.cat); paintChips(); paintGrid(); return; }
    const tg = e.target.closest('.sl-tag'); if (tg) { ST.tag = tg.dataset.tag; paintChips(); paintGrid(); return; }
    const ib = e.target.closest('.sl-i'); if (ib) { ST.info[ib.dataset.i] = !ST.info[ib.dataset.i]; paintCard(ib.dataset.i); return; }
    const rb = e.target.closest('.sl-rbtn'); if (rb) {
      const row = rb.closest('.sl-row'), id = row.dataset.sid, code = row.dataset.code;
      ST.open[id] = ST.open[id] === code ? '' : code; paintCard(id); return;
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
    shellWall(root); paintChips(); paintGrid();
  }
  window.TwExplore = {
    render, show, S: S_, SRC,
    /* 給 _uitest.py 對帳用：每個策略的符合清單（依成交值排序）與可用與否 */
    debug: () => ({ n: R.length, have: Object.assign({}, HAVE), cat: ST.cat,
      hits: Object.fromEntries(S_.map((s) => [s.id, matches(s).map((r) => r.code)])),
      usable: Object.fromEntries(S_.map((s) => [s.id, usable(s)])) }),
  };
})();
