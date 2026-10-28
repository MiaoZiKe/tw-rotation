/* ============================================================================
   交易練習室（#lab → #lab/<子頁>）—— 2026-10-28 建（Andy 要的 TradingView 式回測、K 線重播、事件分析、自訂策略）
   這一頁回答的問題：「這套技術分析規則放到歷史上，賺還是賠？換週期、換參數、加上事件條件後差多少？」
   子頁：台指期（lab/fut）、歷史回測（bt）、K 線重播（replay）、事件分析（evt）、自訂策略（custom）。
   資料：data/lab/{index,s/<代號>.json,s/<代號>.60.json,events.json}（pipeline/compute/lab.py 產出；預覽分支改讀 lab/sample/）。
   回測在 Web Worker 裡跑（lab/worker.js ＋ lab/engine.js），頁面不卡；引擎沒有 DOM，Node 也能跑（tests/lab_engine_check.js）。
   ⚠ 所有文字用 textContent／esc 輸出，不收 HTML。只有管理者看得到（判定同 tc.js）。
   ============================================================================ */
(function () {
  'use strict';
  const E = window.LabEngine;
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const VER = (() => { try { const m = /[?&]v=([^&]+)/.exec(document.currentScript.src); return m ? m[1] : ''; } catch (e) { return ''; } })();
  const LS = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* 私密視窗 */ } } };

  /* ---------------------------------------------------------------- 管理者限定（同 tc.js：預覽版全開、本機可用 TW_LAB_OVERRIDE） */
  function isAdm() {
    try {
      if (window.TW_PREVIEW) return true;
      const h = location.hostname;
      if ((h === '127.0.0.1' || h === 'localhost') && (window.TW_LAB_OVERRIDE === true || window.TW_LAB_OVERRIDE === false)) return window.TW_LAB_OVERRIDE;
      const A = window.TwAccount; let u = null;
      if (A && typeof A.user === 'function') u = A.user();
      else if (localStorage.getItem('tw.acct.tok')) u = JSON.parse(localStorage.getItem('tw.acct.user') || 'null');
      return !!(u && (u.admin === true || u.owner === true));
    } catch (e) { return false; }
  }
  let known = false;
  function gate() {
    const on = isAdm();
    document.documentElement.classList.toggle('lab-adm', on);
    if (!on && known && /^#lab(\/|$)/.test(location.hash || '')) location.replace('#overview');
    return on;
  }
  gate();
  window.addEventListener('tw:account', () => { known = true; if (gate() && /^#lab(\/|$)/.test(location.hash || '')) window.dispatchEvent(new HashChangeEvent('hashchange')); });
  setTimeout(() => { if (!known) { known = true; gate(); } }, 6000);
  window.addEventListener('hashchange', gate);

  /* ---------------------------------------------------------------- 資料載入（按需、有快取） */
  const DATA = { idx: null, ser: {}, sample: false, events: null };
  async function getJSON(rel) {
    const tries = ['data/lab/' + rel, 'lab/sample/' + rel];
    for (let i = 0; i < tries.length; i++) {
      try { const r = await fetch(tries[i], { cache: 'no-cache' }); if (r.ok) { if (i === 1) DATA.sample = true; return await r.json(); } } catch (e) { /* 換下一個來源 */ }
    }
    return null;
  }
  async function loadIndex() { if (!DATA.idx) DATA.idx = (await getJSON('index.json')) || { items: [] }; return DATA.idx; }
  async function loadSeries(code, tf) {
    const k = code + '|' + tf; if (DATA.ser[k]) return DATA.ser[k];
    let B;
    if (tf === '60') { const j = await getJSON('s/' + code + '.60.json'); if (!j) return null; B = E.decode(j.d, '60'); }
    else {
      const j = await getJSON('s/' + code + '.json'); if (!j) return null;
      const D = E.decode(j.d, 'D'); B = E.resample(D, tf); B.name = j.n; B.kind = j.k; B.vu = j.vu;
    }
    DATA.ser[k] = B; return B;
  }
  async function loadEvents() { if (!DATA.events) DATA.events = (await getJSON('events.json')) || { types: {}, events: [] }; return DATA.events; }

  /* ---------------------------------------------------------------- Web Worker（沒有就退回主執行緒） */
  const W = { w: null, seq: 0, pend: {}, loaded: {}, fallback: false };
  function worker() {
    if (W.w || W.fallback) return W.w;
    try {
      W.w = new Worker('lab/worker.js' + (VER ? '?v=' + VER : ''));
      W.w.onmessage = (e) => { const m = e.data, p = W.pend[m.id]; if (!p) return; delete W.pend[m.id]; if (m.ok) p.res(m.res); else p.rej(new Error(m.err)); };
      W.w.onerror = () => { W.fallback = true; W.w = null; Object.keys(W.pend).forEach((k) => { W.pend[k].rej(new Error('worker 失敗')); delete W.pend[k]; }); };
    } catch (e) { W.fallback = true; W.w = null; }
    return W.w;
  }
  function wcall(msg) {
    const w = worker();
    if (!w) { try { return Promise.resolve(E.handle(msg)); } catch (e) { return Promise.reject(e); } }
    return new Promise((res, rej) => { const id = ++W.seq; W.pend[id] = { res, rej }; w.postMessage(Object.assign({ id }, msg)); });
  }
  async function ensureLoaded(key, B) {
    if (W.loaded[key]) return;
    const bars = { n: B.n, tf: B.tf, ts: B.ts, day: B.day, dayEnd: B.dayEnd, o: B.o, h: B.h, l: B.l, c: B.c, v: B.v };
    await wcall({ op: 'load', key, bars });
    W.loaded[key] = 1;
  }

  /* ---------------------------------------------------------------- 狀態 */
  const SUBS = [['fut', '台指期', 10], ['bt', '歷史回測', 20]];
  const MODS = {};        // 其他子頁（K 線重播、事件分析、自訂策略）由各自的 js 註冊進來：{ id, name, ord, mount(body, util), unmount(), reset() }
  const RANGES = ['1M', '3M', '6M', 'YTD', '1Y', '5Y', 'All'];
  const RANGE_DAYS = { '1M': 31, '3M': 92, '6M': 183, '1Y': 366, '5Y': 1830 };
  const TFS = [['60', '60分'], ['D', '日'], ['W', '週'], ['M', '月']];
  function newState(sub) {
    const fut = sub === 'fut';
    return {
      sub, sym: fut ? 'TX' : '2330', tf: 'D', strat: 'ma2', params: {}, mode: 'both', range: 'All', showBH: false, ind: LabK.defaultInd(), ctype: 'k', tt: 'ov', eqMode: 'eq', sortK: 'no', sortD: -1,
      cfg: { capital: 1000000, sizeMode: fut ? 'units' : 'pct', sizeVal: fut ? 1 : 100, pyramiding: 1, fillOn: 'open', sl: 0, tp: 0, trail: 0, maxLoss: 0 },
      costs: {}, advOpen: false, pickOpen: false, res: null, B: null, sel: -1, rowsAll: false, busy: 0,
    };
  }
  const ST = { fut: newState('fut'), bt: newState('bt') };
  let curSub = '';

  const kindOf = (code) => { const it = ((DATA.idx || {}).items || []).find((x) => x.c === code); return it ? it.k : (code === 'TX' ? 'fut' : 'stock'); };
  const instOf = (S) => {
    const k = kindOf(S.sym); S.costs[k] = S.costs[k] || E.instDefaults(k);
    return S.costs[k];
  };

  /* ---------------------------------------------------------------- 格式 */
  const fmt = (x, d) => (x == null || !Number.isFinite(x) ? '—' : x.toLocaleString('en-US', { minimumFractionDigits: d || 0, maximumFractionDigits: d || 0 }));
  const sgn = (x, d) => (x == null || !Number.isFinite(x) ? '—' : (x > 0 ? '+' : x < 0 ? '−' : '') + fmt(Math.abs(x), d));
  const cls = (x) => (x > 0 ? 'up' : x < 0 ? 'dn' : '');
  function compact(x) {
    const a = Math.abs(x), s = x > 0 ? '+' : x < 0 ? '−' : '';
    if (a >= 1e8) return s + (a / 1e8).toFixed(2) + '億';
    if (a >= 1e4) return s + (a / 1e4).toFixed(a >= 1e5 ? 0 : 1) + '萬';
    return s + fmt(a, 0);
  }
  function tstr(B, i, end) {
    if (B.tf === '60') { const d = new Date((B.ts[i] + 8 * 3600) * 1000); return pad2(d.getUTCMonth() + 1) + '-' + pad2(d.getUTCDate()) + ' ' + pad2(d.getUTCHours()) + ':' + pad2(d.getUTCMinutes()); }
    return E.dayToStr(end ? B.dayEnd[i] : B.day[i]);
  }
  const pad2 = (n) => (n < 10 ? '0' : '') + n;
  const ltime = (B, i) => (B.tf === '60' ? B.ts[i] + 8 * 3600 : E.dayToStr(B.day[i]));
  const cssv = (n, f) => { const v = getComputedStyle(document.documentElement).getPropertyValue(n).trim(); return v || f; };
  function pal() { return { rise: cssv('--rise', '#ff4d6d'), fall: cssv('--fall', '#2ee59d'), ink: cssv('--ink-2', '#9aa7c0'), grid: cssv('--line', '#223'), cyan: cssv('--cyan', '#4cc9f0'), amber: cssv('--amber', '#ffb703'), bg: cssv('--panel', '#10182b') }; }

  /* ---------------------------------------------------------------- 骨架 */
  function qpop(html) {
    return '<span class="lab-how"><button class="howbtn lab-q" type="button" aria-label="這一頁怎麼用" aria-expanded="false">?</button><div class="lab-pop" hidden>' + html + '</div></span>';
  }
  const HOW = '<b>怎麼用</b><br>選標的、週期與策略，K 線上的箭頭是這套規則在歷史上的進出場，箭頭旁的數字是那一筆的損益（紅賺綠賠）。下方策略測試器：概覽看損益曲線、回撤、每筆損益；績效摘要看全部、做多、做空三欄；交易清單逐筆列出，點一筆把 K 線移到那裡。右上期間鈕決定回測從哪一天開始。' +
    '<br><br><b>成交規則</b><br>· 訊號在收盤判定，下一根開盤成交（設定可改成訊號當根收盤）；掛停損單的策略（通道突破、Keltner、波動擴張…）在下一根碰到價位才成交，跳空越過就以開盤價成交，沒碰到就取消。' +
    '<br>· 同一根同時碰到停損與停利：開盤離最高較近算先高後低（停利先），否則先低後高（停損先）；跳空越過以開盤價成交。' +
    '<br>· 成本都已扣：手續費 0.1425%（可設折扣、最低 20 元）、證交稅（股票 0.3%、ETF 與指數 0.1%，賣出時收）、滑價。台指期每點 200 元、期交稅十萬分之二（每邊）、手續費每口每邊可調。' +
    '<br>· 加碼口數上限 1＝不加碼；大於 1 時，同方向訊號再出現就再加一口，出場時各口分開記一筆。' +
    '<br>· 週、月 K 由日 K 合成；60 分 K 只有 2023-09 之後、近期成交值前 500 名的個股；價格是除權息還原後的價格。' +
    '<br>· 台指期是近月連續合約，換月的價差沒有調整，長期績效會有偏差。' +
    '<br><br><b>我們採用的定義（TradingView 原文未核實處）</b><br>· 夏普值＝月報酬：（月均報酬 − 無風險 2%÷12）÷ 月報酬標準差 × √12；索提諾值分母只算低於無風險報酬的下檔偏差；不足 3 個月不計算。' +
    '<br>· 最大回撤、最大上漲用每根收盤的權益（含未平倉浮動損益），不含盤中高低。' +
    '<br>· 買進持有＝期初第一根開盤買入、持有到最後一根收盤。' +
    '<br>· 內建策略的預設參數與進場方式照 TradingView 內建策略整理，Greedy 為我們的近似版（原版未核實）；台股 KD 用 9,3,3。' +
    '<br>· 回測是過去的結果，不代表未來，也不是投資建議。';

  function shell(root) {
    const tabs = '<div class="nbsw lab-tabs" role="tablist" aria-label="交易練習室">' + SUBS.map(([id, n]) => '<a href="#lab/' + id + '" role="tab" data-sub="' + id + '" class="' + (id === curSub ? 'on' : '') + '">' + n + '</a>').join('') + qpop(HOW) + '</div>';
    root.innerHTML = '<div class="card lab-card">' + tabs + '<div class="lab-body" id="labBody"></div></div>';
  }

  function btHTML(S) {
    return '<div class="lab-bar">' +
      '<div class="lab-f lab-symw"><span>標的</span><input id="labSym" class="lab-in" type="text" autocomplete="off" spellcheck="false" aria-label="搜尋標的" placeholder="代號或名稱"><div class="lab-dd" id="labSymDD" hidden></div></div>' +
      '<div class="seg lab-tf" id="labTf" role="tablist" aria-label="時間週期">' + TFS.map(([k, n]) => '<button type="button" role="tab" data-tf="' + k + '">' + n + '</button>').join('') + '</div>' +
      '<div class="lab-f"><span>策略</span><button type="button" class="lab-pickbtn" id="labPickBtn" aria-haspopup="listbox"></button></div>' +
      '<div class="seg lab-mode" id="labMode" role="tablist" aria-label="多空"><button type="button" data-m="both">多空</button><button type="button" data-m="long">只做多</button><button type="button" data-m="short">只做空</button></div>' +
      '<div class="seg lab-rng" id="labRng" role="tablist" aria-label="回測期間">' + RANGES.map((k) => '<button type="button" role="tab" data-r="' + k + '">' + k + '</button>').join('') + '</div>' +
      '<button type="button" class="lab-gear" id="labAdvBtn" aria-expanded="false">設定</button>' +
      '</div>' +
      '<div class="lab-params" id="labParams"></div>' +
      '<div class="lab-adv" id="labAdv" hidden></div><div class="lab-pick" id="labPick" hidden></div>' +
      '<div class="lab-ktool"><button type="button" class="lab-pickbtn lab-indbtn" id="labIndBtn" aria-haspopup="listbox">指標 ▾</button><div class="lab-chips" id="labChips"></div>' +
      '<div class="seg lab-ct" id="labCt" role="tablist" aria-label="圖表類型">' + LabK.TYPES.map(([k, n]) => '<button type="button" role="tab" data-c="' + k + '">' + n + '</button>').join('') + '</div></div>' +
      '<div class="lab-kwrap"><div class="lab-draw" id="labDraw" aria-label="繪圖工具"></div><div class="lab-kc"><div class="lab-ch" id="labK"></div></div></div><div class="lab-indset" id="labIndSet" hidden></div>' +
      '<div class="lab-tester"><div class="lab-thead"><div class="lab-stats" id="labStats"></div>' +
      '<div class="seg lab-tt" id="labTT" role="tablist" aria-label="策略測試器">' + TT.map(([k, n]) => '<button type="button" role="tab" data-t="' + k + '">' + n + '</button>').join('') + '</div></div>' +
      '<div class="lab-tbody" id="labTBody"></div></div>';
  }

  /* ---------------------------------------------------------------- 設定欄位 */
  function advFields(S) {
    const inst = instOf(S), c = S.cfg, fut = inst.kind === 'fut';
    const F = (id, lab, v, step, title) => '<label class="lab-fld" title="' + esc(title || '') + '"><span>' + lab + '</span><input class="lab-in" type="number" data-k="' + id + '" value="' + v + '" step="' + (step || 'any') + '"></label>';
    const sizeSel = '<label class="lab-fld"><span>部位方式</span><select class="lab-in" data-k="sizeMode">' +
      [['pct', '資金百分比'], ['amount', '固定金額'], ['units', fut ? '固定口數' : '固定股數']].map(([k, n]) => '<option value="' + k + '"' + (c.sizeMode === k ? ' selected' : '') + '>' + n + '</option>').join('') + '</select></label>';
    const unit = c.sizeMode === 'pct' ? '％' : c.sizeMode === 'amount' ? '元' : (fut ? '口' : '股');
    return '<div class="lab-grid">' +
      F('capital', '初始資金（元）', c.capital, 10000) + sizeSel + F('pyramiding', '加碼口數上限（1＝不加碼）', c.pyramiding, 1, '同方向最多同時持有幾口') +
      '<label class="lab-fld"><span>成交時機</span><select class="lab-in" data-k="fillOn"><option value="open"' + (c.fillOn === 'open' ? ' selected' : '') + '>下一根開盤（預設）</option><option value="close"' + (c.fillOn === 'close' ? ' selected' : '') + '>訊號當根收盤</option></select></label>' + F('sizeVal', '單筆部位（' + unit + '）', c.sizeVal, 1) +
      (fut ? F('mult', '每點（元）', inst.mult, 1) + F('futFee', '手續費（元／口／邊）', inst.futFee, 1) + F('futTax', '期交稅（％，每邊）', inst.futTax, 0.0005) + F('slip', '滑價（點）', inst.slip, 0.5)
        : F('feeRate', '手續費率（％）', inst.feeRate, 0.0005) + F('feeDisc', '手續費折扣（折，10＝無）', Math.round(inst.feeDisc * 100) / 10, 0.1) + F('feeMin', '最低手續費（元）', inst.feeMin, 1) + F('taxRate', '證交稅（％，賣出）', inst.taxRate, 0.05) + F('slip', '滑價（％，每邊）', inst.slip, 0.01)) +
      F('sl', '停損（％）', c.sl, 0.5, '0＝不設') + F('tp', '停利（％）', c.tp, 0.5, '0＝不設') + F('trail', '移動停損（％）', c.trail, 0.5, '0＝不設') + F('maxLoss', '最大日內虧損出場（權益％）', c.maxLoss, 0.1, '單根 K 棒內虧損超過前一根收盤權益的這個比例就出場；0＝不設') +
      '<button type="button" class="lab-clear" id="labReset">還原預設成本</button></div>' + evtFields(S);
  }
  /* 事件當濾網：事件窗內不進場／只在窗內進場、進入窗就平倉（事件日期表見 pipeline/groups/events_history.yaml） */
  function evtFields(S) {
    const D = DATA.events || { types: {} }, e = S.evt || { on: false, types: ['fomc'], mode: 'avoid', before: 3, after: 1, flat: false };
    const tp = Object.keys(D.types || {}); if (!tp.length) return '';
    return '<div class="lab-evt"><label class="lab-chk"><input type="checkbox" data-e="on"' + (e.on ? ' checked' : '') + '> 事件濾網</label>' +
      '<select class="lab-in" data-e="type">' + tp.map((k) => '<option value="' + k + '"' + (e.types[0] === k ? ' selected' : '') + '>' + esc(D.types[k]) + '</option>').join('') + '</select>' +
      '<select class="lab-in" data-e="mode"><option value="avoid"' + (e.mode === 'avoid' ? ' selected' : '') + '>事件窗內不進場</option><option value="only"' + (e.mode === 'only' ? ' selected' : '') + '>只在事件窗內進場</option></select>' +
      '<label class="lab-fld"><span>事件前</span><input class="lab-in lab-n" type="number" min="0" max="30" data-e="before" value="' + e.before + '"><span>日</span></label>' +
      '<label class="lab-fld"><span>事件後</span><input class="lab-in lab-n" type="number" min="0" max="30" data-e="after" value="' + e.after + '"><span>日</span></label>' +
      '<label class="lab-chk"><input type="checkbox" data-e="flat"' + (e.flat ? ' checked' : '') + '> 進入事件窗就平倉</label></div>';
  }
  function paramsHTML(S) {
    const st = E.STRAT[S.strat];
    if (S.strat.indexOf('u:') === 0) return '';
    if (!st || !st.params.length) return '<span class="lab-pdesc">' + esc(st ? st.desc : '') + '</span>';
    const p = Object.assign(E.defaults(S.strat), S.params);
    return st.params.map((q) => '<label class="lab-fld lab-pp"><span>' + esc(q.label) + '</span><input class="lab-in" type="number" data-p="' + q.k + '" value="' + p[q.k] + '" min="' + q.min + '" max="' + q.max + '" step="' + q.step + '"></label>').join('') + '<span class="lab-pdesc">' + esc(st.desc) + '</span>';
  }

  /* ---------------------------------------------------------------- 策略挑選（仿 TradingView 的「指標、指標、策略」視窗：搜尋＋分類） */
  /* 指標、策略挑選視窗（仿 TradingView「指標、指標、策略」視窗）：上方搜尋，分頁＝指標／策略，分類＝我的最愛、我的策略、各類指標與內建策略；
     星號加入我的最愛（存在這台裝置）。指標點了就加到圖上、視窗不關（可以連加好幾個）；策略點了就選用並關閉。 */
  const FAV_KEY = 'tw.lab.favs';
  const favs = () => { try { const a = JSON.parse(localStorage.getItem(FAV_KEY) || '[]'); return Array.isArray(a) ? a : []; } catch (e) { return []; } };
  const setFavs = (a) => { try { localStorage.setItem(FAV_KEY, JSON.stringify(a)); } catch (e) { /* 私密視窗 */ } };
  function pickHTML(S, tab) {
    tab = tab || S.pickTab || 'strat'; S.pickTab = tab;
    const fv = new Set(favs()), mine = (window.TwLabCustom && window.TwLabCustom.list ? window.TwLabCustom.list() : []);
    const star = (id) => '<button type="button" class="lab-star' + (fv.has(id) ? ' on' : '') + '" data-fav="' + esc(id) + '" aria-label="加入我的最愛" title="加入我的最愛">' + (fv.has(id) ? '★' : '☆') + '</button>';
    const rowS = (id, name, desc, on) => '<div class="lab-pr"><button type="button" class="lab-pi' + (on ? ' on' : '') + '" data-s="' + esc(id) + '" data-n="' + esc(name) + '" title="' + esc(desc || '') + '">' + esc(name) + '</button>' + star('s:' + id) + '</div>';
    const rowI = (d) => '<div class="lab-pr"><button type="button" class="lab-pi" data-i="' + d.id + '" data-n="' + esc(d.name) + '">' + esc(d.name) + '<small>＋ 加到圖上</small></button>' + star('i:' + d.id) + '</div>';
    let list = '';
    if (tab === 'ind') {
      const fi = LabK.IND.filter((d) => fv.has('i:' + d.id));
      if (fi.length) list += '<div class="lab-pc">我的最愛</div>' + fi.map(rowI).join('');
      const cats = {}; LabK.IND.forEach((d) => { (cats[d.cat] = cats[d.cat] || []).push(d); });
      list += Object.keys(cats).map((c) => '<div class="lab-pc">' + esc(c) + '</div>' + cats[c].map(rowI).join('')).join('');
    } else {
      const all = {}; E.STRATS.forEach((x) => { all[x.id] = x; });
      const fs = Array.from(fv).filter((k) => k.indexOf('s:') === 0).map((k) => k.slice(2));
      if (fs.length) list += '<div class="lab-pc">我的最愛</div>' + fs.map((id) => (all[id] ? rowS(id, all[id].name, all[id].desc, S.strat === id) : '')).join('');
      if (mine.length) list += '<div class="lab-pc">我的策略</div>' + mine.map((m) => rowS('u:' + m.id, m.name, '', S.strat === 'u:' + m.id)).join('');
      const cats = {}; E.STRATS.forEach((x) => { (cats[x.cat] = cats[x.cat] || []).push(x); });
      list += Object.keys(cats).map((c) => '<div class="lab-pc">內建策略・' + esc(c) + '</div>' + cats[c].map((x) => rowS(x.id, x.name, x.desc, S.strat === x.id)).join('')).join('');
    }
    return '<div class="lab-ptabs seg" role="tablist"><button type="button" role="tab" data-pt="ind" class="' + (tab === 'ind' ? 'on' : '') + '">指標</button><button type="button" role="tab" data-pt="strat" class="' + (tab === 'strat' ? 'on' : '') + '">策略</button></div>' +
      '<input class="lab-in lab-pq" type="text" id="labPq" placeholder="搜尋' + (tab === 'ind' ? '指標' : '策略') + '" aria-label="搜尋" autocomplete="off">' +
      '<div class="lab-plist" id="labPl">' + list + '</div>';
  }
  /* 圖上已加的指標：每個一顆小標籤（名稱＋參數）、齒輪開設定（輸入／樣式）、× 移除 */
  function chipsHTML(S) {
    return S.ind.map((it, i) => { const d = LabK.BY[it.id]; const par = (d.p || []).map(([k]) => it[k]).join(','); return '<span class="lab-chip" data-i="' + i + '"><b>' + esc(d.name.split(' ')[0]) + (par ? ' ' + par : '') + '</b>' + (d.p.length ? '<button type="button" class="lab-cg" data-cg="' + i + '" aria-label="設定" title="設定">⚙</button>' : '') + '<button type="button" class="lab-cx" data-cx="' + i + '" aria-label="移除" title="移除">×</button></span>'; }).join('');
  }
  function indSetHTML(S, i) {
    const it = S.ind[i], d = it && LabK.BY[it.id]; if (!it) return '';
    return '<div class="lab-isi"><b>' + esc(d.name) + '</b><div class="seg" role="tablist"><button type="button" data-ist="in" class="' + (S.istab !== 'st' ? 'on' : '') + '">輸入</button><button type="button" data-ist="st" class="' + (S.istab === 'st' ? 'on' : '') + '">樣式</button></div></div>' +
      (S.istab === 'st'
        ? '<div class="lab-isr"><label class="lab-fld"><span>顏色</span><input type="color" class="lab-col" data-ii="' + i + '" data-f="color" value="' + (it.color || '#3ee0ff') + '"></label><label class="lab-fld"><span>粗細</span><select class="lab-in" data-ii="' + i + '" data-f="w">' + [1, 2, 3].map((w) => '<option value="' + w + '"' + ((+it.w || 1) === w ? ' selected' : '') + '>' + w + '</option>').join('') + '</select></label><button type="button" class="lab-clear" data-iclr="' + i + '">預設顏色</button></div>'
        : '<div class="lab-isr">' + (d.p.length ? d.p.map(([k, lab, def, mn, mx]) => '<label class="lab-fld"><span>' + lab + '</span><input class="lab-in cb-n" type="number" min="' + mn + '" max="' + mx + '" step="any" data-ii="' + i + '" data-f="' + k + '" value="' + (it[k] != null ? it[k] : def) + '"></label>').join('') : '<span class="lab-pdesc">這個指標沒有可調的參數</span>') + '<button type="button" class="lab-clear" data-idef="' + i + '">預設值</button></div>') +
      '<button type="button" class="lab-clear lab-iok" data-iclose>完成</button>';
  }
  const stratName = (id) => { const s = E.STRAT[id]; if (s) return s.name; if (id.indexOf('u:') === 0 && window.TwLabCustom) { const m = window.TwLabCustom.get(id.slice(2)); return m ? m.name : id; } return id; };

  /* ---------------------------------------------------------------- 執行 */
  function buildCfg(S) {
    const inst = Object.assign({}, instOf(S));
    return Object.assign({ mode: S.mode, inst, evt: S.evt || null }, S.cfg);
  }
  let runTok = 0;
  async function recompute(S, keepView) {
    const tok = ++runTok;
    const body = $('#labBody'); if (!body) return;
    const B = S.B; if (!B) return;
    const key = S.sym + '|' + S.tf;
    try {
      await ensureLoaded(key, B);
      let strat;
      if (S.strat.indexOf('u:') === 0 && window.TwLabCustom) {
        const sg = window.TwLabCustom.compile(S.strat.slice(2), B);
        if (!sg) { renderEmpty(S, '這個自訂策略無法執行，請到「自訂策略」檢查條件'); return; }
        strat = { sig: sg, risk: sg.risk };
      } else strat = { id: S.strat, params: Object.assign(E.defaults(S.strat), S.params) };
      const evts = S.evt && S.evt.on ? ((await loadEvents()).events || []) : null;
      const r = await wcall({ op: 'run', key, strat: strat.sig ? { sig: strat.sig, risk: strat.risk } : strat, cfg: buildCfg(S), range: S.range, events: evts });
      if (tok !== runTok) return;
      S.res = r; S.sel = -1; S.rowsAll = false;
      paintResult(S, keepView);
    } catch (e) {
      if (tok === runTok) renderEmpty(S, '回測失敗：' + (e && e.message ? e.message : e));
    }
  }
  function renderEmpty(S, msg) {
    const st = $('#labStats'); if (st) st.innerHTML = '<div class="lab-note">' + esc(msg) + '</div>';
  }

  /* ---------------------------------------------------------------- 繪圖（Lightweight Charts） */
  const CH = { k: null, eq: null, cs: null, mk: null, s1: null, s2: null, syncing: false, ro: [] };
  /* 銷毀圖表：先把容器清空（canvas 先離開 DOM，觸發的 mouseleave 還打在活著的圖上），再 remove()；
     反過來做會讓「已銷毀的圖」收到滑鼠離開事件而丟 Object is disposed。 */
  function baseOpts(el) {
    const c = pal();
    return { autoSize: true, layout: { background: { type: 'solid', color: 'transparent' }, textColor: c.ink, fontSize: 12, attributionLogo: false }, grid: { vertLines: { color: c.grid }, horzLines: { color: c.grid } }, rightPriceScale: { borderColor: c.grid }, timeScale: { borderColor: c.grid, rightOffset: 4, timeVisible: false }, crosshair: { mode: 0 }, handleScroll: true, handleScale: true, localization: { locale: 'zh-TW' } };
  }
  function killChart(name) {
    if (name === 'k') {
      const kv = CH.kv; CH.kv = null; CH.k = null; CH.cs = CH.mk = null;
      CH.subs = (CH.subs || []).filter((x) => { if (kv && (x.a === kv.chart || x.b === kv.chart)) { try { x.a.timeScale().unsubscribeVisibleLogicalRangeChange(x.fn); } catch (e) { /* 已銷毀 */ } return false; } return true; });
      if (kv) { try { const el = $('#labK'); if (el) el.replaceChildren(); } catch (e) { /* 忽略 */ } kv.destroy(); }
      return;
    }
    const c = CH[name]; if (!c) return; CH[name] = null;
    // 先拆掉連到這張圖的時間軸連動，removal 時內部觸發的範圍事件才不會打到已銷毀的另一張
    CH.subs = (CH.subs || []).filter((x) => { if (x.a === c || x.b === c) { try { x.a.timeScale().unsubscribeVisibleLogicalRangeChange(x.fn); } catch (e) { /* 已銷毀 */ } return false; } return true; });
    // 先把容器清空（canvas 先離開 DOM，觸發的 mouseleave 還打在活著的圖上），再 remove()；反過來做會讓「已銷毀的圖」收到滑鼠離開事件而丟 Object is disposed。
    try { const el = $('#labEq'); if (el) el.replaceChildren(); } catch (e) { /* 忽略 */ }
    try { c.remove(); } catch (e) { /* 已銷毀 */ }
  }
  function disposeCharts() { CH.syncing = true; ['k', 'eq'].forEach((n) => killChart(n)); CH.s1 = CH.s2 = null; CH.syncing = false; CH.key = ''; }

  /* 圖上：K 線（全站 KChart）＋指標＋繪圖工具＋進出場箭頭。畫「全部歷史」，取景停在回測區間；換參數時不重建圖（同標的同週期同起點就只換箭頭）。 */
  function paintResult(S, keepView) {
    const r = S.res, B = S.B; if (!r) return;
    const c = pal(), from = r.from, n = B.n - from;
    const kEl = $('#labK'); if (!kEl) return;
    const key = S.sym + '|' + S.tf + '|' + from + '|' + B.n;
    if (!CH.kv || CH.key !== key) {
      killChart('k');
      const kv = new LabK.KView(kEl, B, { items: S.ind, type: S.ctype, drawKey: 'tw.draw.lab.' + S.sym + '.' + S.tf });
      CH.kv = kv; CH.k = kv.chart; CH.cs = kv.candle; CH.key = key;
      kv.set(B.n - 1, false);
      kv.enableDraw($('#labDraw'));
      kv.chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, from - 2), to: B.n + 3 });
    }
    S.times = Array.from({ length: n }, (_, i) => LabK.ltime(B, from + i));
    // 進出場箭頭：多單進場＝朝上箭頭（K 棒下方）、空單進場＝朝下箭頭；出場箭頭顏色＝這一筆的損益（紅賺綠賠），字＝損益
    const all = r.trades.concat(r.opens || []), mks = [], many = all.length > 60;
    all.forEach((t) => {
      if (t.i0 < from) return;
      mks.push({ time: LabK.ltime(B, t.i0), position: t.dir === 1 ? 'belowBar' : 'aboveBar', shape: t.dir === 1 ? 'arrowUp' : 'arrowDown', color: t.dir === 1 ? c.rise : c.fall, text: many ? '' : (t.dir === 1 ? '多 ' : '空 ') + (t.entryWhy || '').replace('訊號', ''), size: 1 });
      if (!t.open) mks.push({ time: LabK.ltime(B, t.i1), position: t.dir === 1 ? 'aboveBar' : 'belowBar', shape: t.dir === 1 ? 'arrowDown' : 'arrowUp', color: t.pnl >= 0 ? c.rise : c.fall, text: many ? '' : compact(t.pnl), size: 1 });
    });
    mks.sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0));
    CH.kv.setMarkers(mks);
    const ch = $('#labChips'); if (ch) ch.innerHTML = chipsHTML(S);
    $$('#labCt button').forEach((b) => b.classList.toggle('on', b.dataset.c === S.ctype));
    paintKeys(S); paintTester(S);
  }

  /* Key stats 四張卡（對照 TradingView）：總損益、最大回撤、獲利交易、獲利因子 */
  function paintKeys(S) {
    const s = S.res.stats, el = $('#labStats'); if (!el) return;
    const T = (lab, val, sub, c2, tip) => '<div class="lab-st" title="' + esc(tip || '') + '"><span>' + lab + '</span><b class="' + (c2 || '') + '">' + val + '</b><small>' + (sub || '') + '</small></div>';
    const pf = s.all.pf == null ? '—' : s.all.pf === Infinity ? '∞' : s.all.pf.toFixed(2);
    el.innerHTML =
      T('總損益', sgn(s.net, 0), sgn(s.ret, 2) + '%', cls(s.net), '含未平倉損益，已扣手續費、證交稅、滑價') +
      T('最大回撤', fmt(-s.mdd, 0), '−' + s.mddP.toFixed(2) + '%', s.mdd > 0 ? 'dn' : '', '權益（含未平倉浮動損益）從高點往下的最大跌幅') +
      T('獲利交易', s.all.win == null ? '—' : s.all.win.toFixed(2) + '%', s.all.nWin + ' / ' + s.all.nClosed, '', '已平倉交易中賺錢的比例') +
      T('獲利因子', pf, '總獲利 ÷ 總虧損', '', '大於 1 代表賺的比賠的多');
  }

  const TT = [['ov', '概覽'], ['sum', '績效摘要'], ['tr', '交易清單']];
  const EQM = [['eq', '累積損益'], ['dd', '回撤'], ['exc', '每筆損益']];
  function paintTester(S) {
    const body = $('#labTBody'); if (!body) return;
    killChart('eq'); CH.s1 = CH.s2 = null;
    $$('#labTT button').forEach((b) => b.classList.toggle('on', b.dataset.t === S.tt));
    if (S.tt === 'ov') {
      body.innerHTML = '<div class="lab-eqh"><div class="seg lab-eqm" id="labEqM" role="tablist" aria-label="圖表內容">' + EQM.map(([k, n]) => '<button type="button" role="tab" data-e="' + k + '" class="' + (S.eqMode === k ? 'on' : '') + '">' + n + '</button>').join('') + '</div>' +
        '<label class="lab-chk" id="labBHw"><input type="checkbox" id="labBH"' + (S.showBH ? ' checked' : '') + '> 疊上買進持有</label></div><div class="lab-ch" id="labEq"></div>';
      paintEq(S);
    } else if (S.tt === 'sum') { body.innerHTML = summaryHTML(S); }
    else { body.innerHTML = tradesHTML(S); }
  }
  function paintEq(S) {
    const r = S.res, B = S.B, LW = window.LightweightCharts, c = pal(), from = r.from, n = B.n - from, cap = S.cfg.capital;
    const eEl = $('#labEq'); if (!eEl) return;
    const tfv = B.tf === '60', times = S.times;
    $('#labBHw').style.display = S.eqMode === 'eq' ? '' : 'none';
    CH.eq = LW.createChart(eEl, baseOpts(eEl));
    CH.eq.applyOptions({ timeScale: { timeVisible: tfv, secondsVisible: false } });
    const ser = {};
    if (S.eqMode === 'eq') {
      CH.s1 = CH.eq.addSeries(LW.BaselineSeries, { baseValue: { type: 'price', price: 0 }, topLineColor: c.rise, topFillColor1: c.rise + '55', topFillColor2: c.rise + '08', bottomLineColor: c.fall, bottomFillColor1: c.fall + '08', bottomFillColor2: c.fall + '55', lineWidth: 2, priceLineVisible: false, lastValueVisible: true });
      CH.s1.setData(times.map((t, i) => ({ time: t, value: Math.round((r.eq[i] - cap) * 100) / 100 })));
      if (S.showBH) {
        CH.eq.applyOptions({ leftPriceScale: { visible: true, borderColor: c.grid } });
        CH.s2 = CH.eq.addSeries(LW.LineSeries, { color: c.amber, lineWidth: 1, lineStyle: 2, priceLineVisible: false, lastValueVisible: false, priceScaleId: 'left' });
        CH.s2.setData(times.map((t, i) => ({ time: t, value: Math.round((r.bh[i] - cap) * 100) / 100 })));
      }
    } else if (S.eqMode === 'dd') {
      CH.s1 = CH.eq.addSeries(LW.AreaSeries, { lineColor: c.fall, topColor: c.fall + '08', bottomColor: c.fall + '66', lineWidth: 2, priceLineVisible: false, priceFormat: { type: 'custom', formatter: (v) => v.toFixed(1) + '%' } });
      CH.s1.setData(times.map((t, i) => ({ time: t, value: Math.round(r.stats.dd[i] * 100) / 100 })));
    } else {
      // 每筆損益（出場那根）＋該筆的最大有利（MFE）與最大不利（MAE）幅度，其餘 K 棒留空白佔位，讓時間軸和 K 線一一對應
      const idx = {}; r.trades.forEach((t) => { idx[t.i1 - from] = t; });
      const H = (color) => CH.eq.addSeries(LW.HistogramSeries, { color, priceLineVisible: false, lastValueVisible: false });
      const sMfe = H(c.rise + '55'), sMae = H(c.fall + '55'), sPnl = H(c.rise);
      const pnl = [], mfe = [], mae = [];
      times.forEach((t, i) => { const x = idx[i]; if (x) { pnl.push({ time: t, value: Math.round(x.pnl), color: x.pnl >= 0 ? c.rise : c.fall }); mfe.push({ time: t, value: Math.round(x.mfe) }); mae.push({ time: t, value: -Math.round(x.mae) }); } else { pnl.push({ time: t }); mfe.push({ time: t }); mae.push({ time: t }); } });
      sMfe.setData(mfe); sMae.setData(mae); sPnl.setData(pnl); CH.s1 = sPnl;
    }
    void ser; void n;
    CH.eq.timeScale().fitContent();
    const off = r.from;     // K 線的第 off 根 ＝ 累積損益的第 0 根
    const link = (a, b, d) => { const fn = (rg) => { if (CH.syncing || !rg) return; CH.syncing = true; try { b.timeScale().setVisibleLogicalRange({ from: rg.from + d, to: rg.to + d }); } catch (e) { /* 圖已銷毀 */ } CH.syncing = false; }; (CH.subs = CH.subs || []).push({ a, b, fn }); a.timeScale().subscribeVisibleLogicalRangeChange(fn); };
    link(CH.k, CH.eq, -off); link(CH.eq, CH.k, off);
    try { const vr = CH.k.timeScale().getVisibleLogicalRange(); if (vr) CH.eq.timeScale().setVisibleLogicalRange({ from: vr.from - off, to: vr.to - off }); } catch (e) { /* 忽略 */ }
  }

  /* 績效摘要：全部／多／空三欄（欄位與口徑對照 TradingView；Sharpe、Sortino 與最大上漲／回撤只有「全部」） */
  function summaryHTML(S) {
    const s = S.res.stats, A = s.all, Lg = s.long, Sh = s.short, cap = S.cfg.capital;
    const fut = kindOf(S.sym) === 'fut', u = fut ? '口' : '股';
    const m = (x, p) => (x == null ? '—' : '<span class="' + cls(x) + '">' + sgn(x, 0) + '</span>' + (p == null ? '' : ' <small class="' + cls(x) + '">' + sgn(p, 2) + '%</small>'));
    const pf = (x) => (x == null ? '—' : x === Infinity ? '∞' : x.toFixed(3));
    const bars = (x) => (x == null ? '—' : x.toFixed(1));
    const row = (lab, a, l, sh, tip) => '<tr><th scope="row" title="' + esc(tip || '') + '">' + lab + '</th><td>' + a + '</td><td>' + (l == null ? '' : l) + '</td><td>' + (sh == null ? '' : sh) + '</td></tr>';
    const R = [
      ['淨利', (g) => m(g.net, g.netP), '總獲利減總虧損，已扣手續費、證交稅、滑價'],
      ['總獲利', (g) => m(g.gp), ''], ['總虧損', (g) => m(-g.gl), ''],
    ];
    let h = '<div class="lab-twrap"><table class="lab-tbl lab-sum"><thead><tr><th></th><th>全部</th><th>做多</th><th>做空</th></tr></thead><tbody>';
    R.forEach(([lab, f, tip]) => { h += row(lab, f(A), f(Lg), f(Sh), tip); });
    h += row('買進持有報酬', m(s.bhNet, s.bhRet), '', '', '同期間第一根開盤買入、持有到最後一根收盤；價格已還原除權息');
    h += row('最大上漲', m(s.runup, s.runupP), '', '', '權益從低點到之後高點的最大增幅');
    h += row('最大回撤', m(-s.mdd, -s.mddP), '', '', '權益（含未平倉浮動損益）從高點到之後低點的最大跌幅');
    h += row('夏普值', s.sharpe == null ? '—' : s.sharpe.toFixed(3), '', '', '月報酬計：（月均報酬 − 無風險 2%÷12）÷ 月報酬標準差 × √12。期間不足 3 個月不計算');
    h += row('索提諾值', s.sortino == null ? '—' : s.sortino.toFixed(3), '', '', '同夏普，分母改成只算低於無風險報酬的下檔偏差');
    const R2 = [
      ['獲利因子', (g) => pf(g.pf), '總獲利 ÷ 總虧損'],
      ['未平倉損益', (g) => m(g.openPL), '最後一根收盤時持倉的浮動損益'],
      ['手續費合計', (g) => fmt(g.comm, 0), '含手續費、證交稅（期貨為期交稅）；滑價已反映在成交價'],
      ['已平倉交易', (g) => String(g.nClosed), ''], ['未平倉交易', (g) => String(g.nOpen), ''],
      ['獲利筆數', (g) => String(g.nWin), ''], ['虧損筆數', (g) => String(g.nLoss), ''], ['平手筆數', (g) => String(g.nEven), ''],
      ['勝率', (g) => (g.win == null ? '—' : g.win.toFixed(2) + '%'), ''],
      ['平均每筆', (g) => (g.avgTrade == null ? '—' : m(g.avgTrade, g.avgTradeP)), ''],
      ['平均獲利', (g) => (g.avgW == null ? '—' : m(g.avgW, g.avgWP)), ''], ['平均虧損', (g) => (g.avgL == null ? '—' : m(-g.avgL, g.avgLP)), ''],
      ['盈虧比', (g) => (g.rr == null ? '—' : g.rr === Infinity ? '∞' : g.rr.toFixed(3)), '平均獲利 ÷ 平均虧損'],
      ['最大單筆獲利', (g) => (g.bigW == null ? '—' : m(g.bigW, g.bigWP)), ''], ['最大單筆虧損', (g) => (g.bigL == null ? '—' : m(g.bigL, g.bigLP)), ''],
      ['平均持有 K 數', (g) => bars(g.barsAll), ''], ['獲利單平均 K 數', (g) => bars(g.barsW), ''], ['虧損單平均 K 數', (g) => bars(g.barsL), ''],
    ];
    R2.forEach(([lab, f, tip]) => { h += row(lab, f(A), f(Lg), f(Sh), tip); });
    h += row('最大持有' + u + '數', fmt(s.maxLots, 0), '', '', '同時持有的最大數量（加碼時才會大於單筆數量）');
    void cap;
    return h + '</tbody></table></div>';
  }

  /* 交易清單：點一列把 K 線移到那一筆、再點取消；欄位可排序、可匯出 CSV */
  function tradeRows(S) {
    const r = S.res;
    return r.trades.map((t, i) => Object.assign({ no: i + 1 }, t)).concat((r.opens || []).map((t, i) => Object.assign({ no: r.trades.length + i + 1 }, t)));
  }
  const TCOL = [['no', '#'], ['dir', '方向'], ['i0', '進場時間'], ['i1', '出場時間'], ['p0', '進場價'], ['p1', '出場價'], ['qty', '數量'], ['pnl', '損益'], ['pnlP', '損益%'], ['cum', '累積損益'], ['mfe', 'MFE'], ['mae', 'MAE']];
  function tradesHTML(S) {
    const B = S.B, all = tradeRows(S);
    if (!all.length) return '<div class="lab-note">這段期間沒有交易</div>';
    const mob = window.matchMedia && window.matchMedia('(max-width:640px)').matches;
    const k = S.sortK || 'no', d = S.sortD || -1;
    const rows = all.slice().sort((a, b) => (a[k] < b[k] ? -1 : a[k] > b[k] ? 1 : 0) * d);
    const lim = mob && !S.rowsAll ? 10 : rows.length;
    const hold = (t) => (B.tf === '60' ? t.bars + ' 根' : B.tf === 'D' ? (B.day[Math.min(t.i1, B.n - 1)] - B.day[t.i0]) + ' 日' : t.bars + ' 根');
    return '<div class="lab-trbar"><button type="button" class="lab-clear" id="labCsv">匯出 CSV</button></div><div class="lab-twrap"><table class="lab-tbl"><thead><tr>' + TCOL.map(([kk, n], i) => '<th data-k="' + kk + '" class="lab-sort' + (i >= 9 ? ' lab-hm' : '') + (kk === k ? ' on' : '') + '" role="columnheader" aria-sort="' + (kk === k ? (d > 0 ? 'ascending' : 'descending') : 'none') + '">' + n + (kk === k ? (d > 0 ? ' ▲' : ' ▼') : '') + '</th>').join('') + '</tr></thead><tbody>' +
      rows.slice(0, lim).map((t) => '<tr data-i="' + (t.no - 1) + '" class="' + (S.sel === t.no - 1 ? 'on' : '') + '" title="' + esc('進場：' + (t.entryWhy || '') + '｜出場：' + (t.why || '') + '｜持有 ' + hold(t)) + '"><td>' + t.no + '</td><td class="' + (t.dir === 1 ? 'up' : 'dn') + '">' + (t.dir === 1 ? '多' : '空') + '</td><td>' + tstr(B, t.i0) + '</td><td>' + (t.open ? '未平倉' : tstr(B, t.i1)) + '</td><td>' + fmt(t.p0, 2) + '</td><td>' + fmt(t.p1, 2) + '</td><td>' + fmt(t.qty, 0) + '</td><td class="' + cls(t.pnl) + '">' + sgn(t.pnl, 0) + '</td><td class="' + cls(t.pnl) + '">' + sgn(t.pnlP, 2) + '%</td><td class="lab-hm ' + cls(t.cum) + '">' + sgn(t.cum, 0) + '</td><td class="lab-hm">' + fmt(t.mfe, 0) + '</td><td class="lab-hm">' + fmt(t.mae, 0) + '</td></tr>').join('') +
      '</tbody></table></div>' + (lim < rows.length ? '<button type="button" class="lab-more" id="labMore">看全部 ' + rows.length + ' 筆</button>' : '');
  }
  function csvOf(S) {
    const B = S.B, q = (x) => '"' + String(x).replace(/"/g, '""') + '"';
    const head = ['編號', '方向', '進場時間', '出場時間', '進場價', '出場價', '數量', '損益', '損益%', '累積損益', 'MFE', 'MAE', '進場訊號', '出場原因'];
    const lines = [head.map(q).join(',')].concat(tradeRows(S).map((t) => [t.no, t.dir === 1 ? '多' : '空', tstr(B, t.i0), t.open ? '未平倉' : tstr(B, t.i1), t.p0.toFixed(2), t.p1.toFixed(2), t.qty, t.pnl.toFixed(0), t.pnlP.toFixed(2), t.cum.toFixed(0), t.mfe.toFixed(0), t.mae.toFixed(0), t.entryWhy || '', t.why || ''].map(q).join(',')));
    return '﻿' + lines.join('\r\n');
  }
  function downloadCsv(S) {
    const blob = new Blob([csvOf(S)], { type: 'text/csv;charset=utf-8' }), a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = 'lab_' + S.sym + '_' + S.strat + '.csv'; document.body.appendChild(a); a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  }
  /* 取景回到回測區間（不是整段歷史） */
  function resetView(S) { try { if (CH.k && S.res) CH.k.timeScale().setVisibleLogicalRange({ from: Math.max(0, S.res.from - 2), to: S.B.n + 3 }); } catch (e) { /* 圖已銷毀 */ } }
  function focusTrade(S, i) {
    const all = tradeRows(S), t = all[i]; if (!t || !CH.k) return;
    S.sel = i;
    const a = Math.max(0, t.i0 - 12), b = Math.min(S.B.n - 1, t.i1 + 12);
    try { CH.k.timeScale().setVisibleLogicalRange({ from: a, to: b }); } catch (e) { /* 圖已銷毀 */ }
    $$('#labTBody tbody tr').forEach((tr) => tr.classList.toggle('on', +tr.dataset.i === i));
  }

  /* ---------------------------------------------------------------- 控制列同步 */
  function syncBar(S) {
    const sym = $('#labSym'); if (sym && document.activeElement !== sym) { const it = ((DATA.idx || {}).items || []).find((x) => x.c === S.sym); sym.value = it ? it.c + ' ' + it.n : S.sym; }
    const it = ((DATA.idx || {}).items || []).find((x) => x.c === S.sym);
    $$('#labTf button').forEach((b) => {
      const k = b.dataset.tf; const no60 = k === '60' && !(it && it.h60);
      b.classList.toggle('on', k === S.tf); b.disabled = no60; b.title = no60 ? '此標的沒有 60 分 K（60 分資料只有 2023-09 之後的個股）' : '';
    });
    $$('#labMode button').forEach((b) => b.classList.toggle('on', b.dataset.m === S.mode));
    const B = S.B, span = B && B.n ? (B.dayEnd[B.n - 1] - B.day[0]) : 0;
    $$('#labRng button').forEach((b) => {
      const k = b.dataset.r, short = RANGE_DAYS[k] && span < RANGE_DAYS[k] * 0.9;
      b.classList.toggle('on', k === S.range); b.disabled = !!short; b.title = short ? '資料只有 ' + Math.round(span / 30) + ' 個月，不足這個期間' : '';
    });
    const pb = $('#labPickBtn'); if (pb) pb.textContent = stratName(S.strat) + ' ▾';
    const pp = $('#labParams'); if (pp) pp.innerHTML = paramsHTML(S);
    const bh = $('#labBH'); if (bh) bh.checked = !!S.showBH;
    const ab = $('#labAdvBtn'); if (ab) { ab.setAttribute('aria-expanded', String(!!S.advOpen)); ab.classList.toggle('on', !!S.advOpen); }
    const adv = $('#labAdv'); if (adv) { adv.hidden = !S.advOpen; if (S.advOpen) adv.innerHTML = advFields(S); }
  }

  async function setSymbol(S, code, keepTf) {
    const idx = await loadIndex(); const it = idx.items.find((x) => x.c === code); if (!it) return;
    S.sym = code;
    if (!keepTf && S.tf === '60' && !it.h60) S.tf = 'D';
    S.B = await loadSeries(code, S.tf === '60' && !it.h60 ? 'D' : S.tf);
    if (!S.B && S.tf !== 'D') { S.tf = 'D'; S.B = await loadSeries(code, 'D'); }
    // 換標的種類時，部位預設跟著換（期貨 1 口、股票滿倉）
    const fut = it.k === 'fut';
    if (fut && S.cfg.sizeMode !== 'units') { S.cfg.sizeMode = 'units'; S.cfg.sizeVal = 1; }
    if (!fut && S.cfg.sizeMode === 'units' && S.sub !== 'fut') { S.cfg.sizeMode = 'pct'; S.cfg.sizeVal = 100; }
    if (S.range !== 'All') { const span = S.B.dayEnd[S.B.n - 1] - S.B.day[0]; if (RANGE_DAYS[S.range] && span < RANGE_DAYS[S.range] * 0.9) S.range = 'All'; }
    syncBar(S);
    await recompute(S);
  }
  async function setTf(S, tf) {
    S.tf = tf; S.B = await loadSeries(S.sym, tf);
    if (!S.B) return;
    syncBar(S); await recompute(S);
  }

  /* ---------------------------------------------------------------- 搜尋標的 */
  function searchItems(q) {
    const items = (DATA.idx || {}).items || []; q = q.trim().toLowerCase(); if (!q) return items.filter((x) => x.k !== 'stock' && x.k !== 'etf').concat(items.filter((x) => x.k === 'stock').slice(0, 9));
    const hit = [];
    for (const x of items) { if (x.c.toLowerCase().indexOf(q) === 0) hit.push([0, x]); else if (x.n.toLowerCase().indexOf(q) >= 0) hit.push([1, x]); if (hit.length > 400) break; }
    hit.sort((a, b) => a[0] - b[0] || (a[1].c < b[1].c ? -1 : 1));
    return hit.slice(0, 12).map((h) => h[1]);
  }
  const KIND_N = { stock: '', etf: 'ETF', index: '指數', fut: '期貨' };
  function paintDD(S) {
    const dd = $('#labSymDD'), inp = $('#labSym'); if (!dd) return;
    let list = searchItems(inp.value.replace(/^\S+\s/, (m) => (/^\d{4,6}[A-Z]?\s$/.test(m) ? '' : m)));
    if (S.sub === 'fut') list = list.filter((x) => x.k === 'fut' || x.k === 'index');
    dd.innerHTML = list.map((x) => '<button type="button" class="lab-di" data-c="' + esc(x.c) + '"><b>' + esc(x.c) + '</b> ' + esc(x.n) + (KIND_N[x.k] ? ' <small>' + KIND_N[x.k] + '</small>' : '') + '</button>').join('') || '<div class="lab-note">找不到符合的標的</div>';
    dd.hidden = false;
  }

  /* ---------------------------------------------------------------- 事件綁定 */
  let deb = null;
  function bind(S) {
    const body = $('#labBody');
    body.onclick = async (e) => {
      const t = e.target;
      const tf = t.closest('#labTf button'); if (tf && !tf.disabled) { await setTf(S, tf.dataset.tf); return; }
      const md = t.closest('#labMode button'); if (md) { S.mode = md.dataset.m; syncBar(S); recompute(S); return; }
      const rg = t.closest('#labRng button'); if (rg && !rg.disabled) { S.range = rg.dataset.r; syncBar(S); recompute(S); return; }
      if (t.closest('#labAdvBtn')) { S.advOpen = !S.advOpen; syncBar(S); return; }
      const pbtn = t.closest('#labPickBtn, #labIndBtn');
      if (pbtn) {
        const pk = $('#labPick'), tab = pbtn.id === 'labIndBtn' ? 'ind' : 'strat';
        const same = !pk.hidden && S.pickTab === tab;
        pk.hidden = same; if (!same) { pk.innerHTML = pickHTML(S, tab); const bb = $('#labBody').getBoundingClientRect(), r = pbtn.getBoundingClientRect(); pk.style.left = Math.max(0, Math.min(r.left - bb.left, bb.width - 300)) + 'px'; pk.style.top = (r.bottom - bb.top + 4) + 'px'; const q = $('#labPq'); q && q.focus(); }
        return;
      }
      const pt = t.closest('.lab-ptabs button'); if (pt) { $('#labPick').innerHTML = pickHTML(S, pt.dataset.pt); const q = $('#labPq'); q && q.focus(); return; }
      const sr = t.closest('.lab-star'); if (sr) { const id = sr.dataset.fav, a = favs(), k = a.indexOf(id); if (k >= 0) a.splice(k, 1); else a.push(id); setFavs(a); const q0 = ($('#labPq') || {}).value || ''; $('#labPick').innerHTML = pickHTML(S, S.pickTab); const q = $('#labPq'); if (q) { q.value = q0; filterPick(q0); } return; }
      const pin = t.closest('.lab-pi[data-i]');
      if (pin) {
        const id = pin.dataset.i, d = LabK.BY[id];
        if (d.multi || !S.ind.some((x) => x.id === id)) { S.ind.push(LabK.newItem(id)); applyInd(S); }
        const sm = pin.querySelector('small'); if (sm) sm.textContent = '✓ 已加到圖上';
        return;
      }
      const pi = t.closest('.lab-pi[data-s]'); if (pi) { S.strat = pi.dataset.s; S.params = {}; const st0 = E.STRAT[S.strat]; if (st0 && st0.risk) Object.assign(S.cfg, st0.risk); $('#labPick').hidden = true; S.pickOpen = false; syncBar(S); recompute(S); return; }
      const cx = t.closest('.lab-cx'); if (cx) { S.ind.splice(+cx.dataset.cx, 1); S.setI = -1; $('#labIndSet').hidden = true; applyInd(S); return; }
      const cg = t.closest('.lab-cg'); if (cg) { const i = +cg.dataset.cg, box = $('#labIndSet'); if (!box.hidden && S.setI === i) { box.hidden = true; S.setI = -1; return; } S.setI = i; S.istab = 'in'; box.innerHTML = indSetHTML(S, i); box.hidden = false; const bb = $('#labBody').getBoundingClientRect(), r = cg.getBoundingClientRect(); box.style.left = Math.max(0, Math.min(r.left - bb.left, bb.width - 280)) + 'px'; box.style.top = (r.bottom - bb.top + 4) + 'px'; return; }
      const ist = t.closest('[data-ist]'); if (ist) { S.istab = ist.dataset.ist; $('#labIndSet').innerHTML = indSetHTML(S, S.setI); return; }
      if (t.closest('[data-iclose]')) { $('#labIndSet').hidden = true; S.setI = -1; return; }
      const idf = t.closest('[data-idef]'); if (idf) { const i = +idf.dataset.idef, d = LabK.BY[S.ind[i].id]; d.p.forEach(([k, , def]) => { S.ind[i][k] = def; }); applyInd(S); $('#labIndSet').innerHTML = indSetHTML(S, i); return; }
      const icl = t.closest('[data-iclr]'); if (icl) { const i = +icl.dataset.iclr; delete S.ind[i].color; delete S.ind[i].w; applyInd(S); $('#labIndSet').innerHTML = indSetHTML(S, i); return; }
      const ct = t.closest('#labCt button'); if (ct) { S.ctype = ct.dataset.c; if (CH.kv) CH.kv.setType(S.ctype); $$('#labCt button').forEach((b) => b.classList.toggle('on', b.dataset.c === S.ctype)); return; }
      const di = t.closest('.lab-di'); if (di) { $('#labSymDD').hidden = true; await setSymbol(S, di.dataset.c); return; }
      if (t.closest('#labReset')) { delete S.costs[kindOf(S.sym)]; syncBar(S); recompute(S); return; }
      const tt = t.closest('#labTT button'); if (tt) { S.tt = tt.dataset.t; paintTester(S); return; }
      const em = t.closest('#labEqM button'); if (em) { S.eqMode = em.dataset.e; paintTester(S); return; }
      if (t.closest('#labCsv')) { downloadCsv(S); return; }
      if (t.closest('#labMore')) { S.rowsAll = true; paintTester(S); return; }
      const th = t.closest('#labTBody th.lab-sort'); if (th) { const k = th.dataset.k; if (S.sortK === k) S.sortD = -S.sortD; else { S.sortK = k; S.sortD = -1; } paintTester(S); return; }
      const tr = t.closest('#labTBody tbody tr'); if (tr && S.tt === 'tr') { const i = +tr.dataset.i; if (S.sel === i) { S.sel = -1; resetView(S); $$('#labTBody tbody tr').forEach((x) => x.classList.remove('on')); } else focusTrade(S, i); return; }
    };
    body.oninput = (e) => {
      const t = e.target;
      if (t.id === 'labSym') { paintDD(S); return; }
      if (t.id === 'labPq') { filterPick(t.value); return; }
      if (t.dataset.ii != null && t.dataset.ii !== '') {
        const it = S.ind[+t.dataset.ii], f = t.dataset.f; if (!it) return;
        if (f === 'color') it.color = t.value; else it[f] = parseFloat(t.value);
        if (Number.isFinite(it[f]) || f === 'color') { clearTimeout(deb); deb = setTimeout(() => applyInd(S), 200); }
        return;
      }
      if (t.id === 'labBH') { S.showBH = t.checked; paintEq(S); return; }
      if (t.dataset.e) {
        const e = S.evt = S.evt || { on: false, types: ['fomc'], mode: 'avoid', before: 3, after: 1, flat: false }, k = t.dataset.e;
        if (k === 'on') e.on = t.checked; else if (k === 'flat') e.flat = t.checked; else if (k === 'type') e.types = [t.value]; else if (k === 'mode') e.mode = t.value;
        else e[k] = Math.max(0, parseInt(t.value || '0', 10));
        clearTimeout(deb); deb = setTimeout(() => recompute(S), 280); return;
      }
      const pk = t.dataset.p, ck = t.dataset.k;
      if (pk || ck) {
        if (pk) S.params[pk] = parseFloat(t.value);
        else if (ck === 'sizeMode') { S.cfg.sizeMode = t.value; if (t.value === 'pct') S.cfg.sizeVal = 100; else if (t.value === 'units') S.cfg.sizeVal = kindOf(S.sym) === 'fut' ? 1 : 1000; else S.cfg.sizeVal = 1000000; syncBar(S); }
        else {
          const v = parseFloat(t.value); if (!Number.isFinite(v)) return;
          if (ck in S.cfg) S.cfg[ck] = ck === 'pyramiding' ? Math.max(1, Math.floor(v)) : v;
          else { const inst = instOf(S); inst[ck] = ck === 'feeDisc' ? Math.max(0.1, Math.min(10, v)) / 10 : v; }
        }
        clearTimeout(deb); deb = setTimeout(() => recompute(S), 280);
      }
    };
    body.onchange = (e) => { if (e.target.dataset.k === 'fillOn') { S.cfg.fillOn = e.target.value; recompute(S); } else if (e.target.dataset.e && e.target.tagName === 'SELECT') bodyInputFix(S, e); };
    const bodyInputFix = (S2, e) => body.oninput(e);
    body.onfocusin = (e) => { if (e.target.id === 'labSym') { e.target.select(); paintDD(S); } };
    document.addEventListener('click', docClick);
  }
  /* 指標清單改了 → 套到圖上、更新標籤列 */
  function applyInd(S) {
    if (CH.kv) CH.kv.applyInd(S.ind);
    const ch = $('#labChips'); if (ch) ch.innerHTML = chipsHTML(S);
  }
  function filterPick(v) {
    const q = String(v || '').trim().toLowerCase();
    $$('#labPl .lab-pr').forEach((r) => { const n = (r.querySelector('.lab-pi') || {}).dataset; r.hidden = !!q && !(n && n.n.toLowerCase().indexOf(q) >= 0); });
    $$('#labPl .lab-pc').forEach((c) => { let n = c.nextElementSibling, any = false; while (n && !n.classList.contains('lab-pc')) { if (!n.hidden) any = true; n = n.nextElementSibling; } c.hidden = !any; });
  }
  function docClick(e) {
    if (!e.target.isConnected) return;     // 點的那個元素已被重畫掉（例如挑選視窗點星號）：不是「點到外面」，別把視窗關掉
    const dd = $('#labSymDD'), pk = $('#labPick');
    if (dd && !e.target.closest('.lab-symw')) dd.hidden = true;
    if (pk && !pk.hidden && !e.target.closest('.lab-pick') && !e.target.closest('#labPickBtn') && !e.target.closest('#labIndBtn')) pk.hidden = true;
    const is = $('#labIndSet'); if (is && !is.hidden && !e.target.closest('.lab-indset') && !e.target.closest('.lab-cg')) { is.hidden = true; }
    const q = e.target.closest('.lab-q');
    $$('.lab-pop').forEach((p) => { if (!q || p !== q.nextElementSibling) p.hidden = true; });
    if (q) { const p = q.nextElementSibling; p.hidden = !p.hidden; q.setAttribute('aria-expanded', String(!p.hidden)); }
  }

  /* ---------------------------------------------------------------- 進入點 */
  /* 規矩 C7：離開交易練習室再進來，一律回 Default（每個子頁的選項都重來）。同一頁內 route() 重跑（資料背景更新）不重畫。 */
  let inLab = false;
  window.addEventListener('hashchange', () => { if (inLab && !/^#lab(\/|$)/.test(location.hash || '')) leaveLab(); });
  let docBound = false;
  function leaveLab() {
    inLab = false; curSub = ''; ST.fut = newState('fut'); ST.bt = newState('bt'); disposeCharts();
    Object.keys(MODS).forEach((k) => { try { MODS[k].unmount && MODS[k].unmount(); MODS[k].reset && MODS[k].reset(); } catch (e) { /* 忽略 */ } });
    document.removeEventListener('click', docClick); docBound = false;
  }
  async function show(head, rest) {
    const root = $('#v-lab'); if (!root) return;
    if (!gate()) { if (!known) root.innerHTML = '<div class="empty">確認登入身分中…</div>'; return; }
    const sub = rest[0];
    if (!SUBS.some((x) => x[0] === sub)) { location.replace('#lab/' + SUBS[0][0]); return; }
    if (inLab && curSub === sub && $('#labBody')) return;
    if (curSub && MODS[curSub]) { try { MODS[curSub].unmount && MODS[curSub].unmount(); } catch (e) { /* 忽略 */ } }
    inLab = true; curSub = sub;
    disposeCharts();          // 先銷毀圖表再換 DOM：容器先被拿掉的話，autoSize 的觀察器還會對已銷毀的圖重畫而丟錯
    shell(root);
    if (!docBound) { document.addEventListener('click', docClick); docBound = true; }
    await loadIndex(); await loadEvents();
    if (MODS[sub]) { await MODS[sub].mount($('#labBody'), UTIL); return; }
    const S = ST[sub];
    $('#labBody').innerHTML = btHTML(S);
    bind(S);
    S.B = null;
    await setSymbol(S, S.sym, true);
  }
  function register(mod) {
    MODS[mod.id] = mod;
    if (!SUBS.some((x) => x[0] === mod.id)) { SUBS.push([mod.id, mod.name, mod.ord || 50]); SUBS.sort((x, y) => (x[2] || 0) - (y[2] || 0)); }
  }

  /* 給其他子頁共用的小工具（K 重播、事件分析、自訂策略） */
  const UTIL = { LabK, E, $, $$, esc, fmt, sgn, cls, compact, pal, ltime, tstr, qpop, getJSON, loadIndex, loadSeries, loadEvents, wcall, ensureLoaded, instOf, kindOf, killChart, CH, DATA, summaryHTML, searchItems, KIND_N, stratName, pickHTML, paramsHTML, ST, defaultsBar: () => ({}) };

  window.TwLab = { show, register, mods: MODS, util: UTIL, state: () => ST, data: DATA, wcall, loadSeries, loadIndex, loadEvents, E, charts: CH };
}());
