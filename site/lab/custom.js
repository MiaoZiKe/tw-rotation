/* ============================================================================
   交易練習室 › 自訂策略（#lab/custom）—— 2026-10-28 建（規格 docs/tradingview_spec.md 3.7：P0 積木編輯器、P1 迷你腳本）
   這一頁回答的問題：「我自己想的規則（例如均線上穿且 RSI < 70、FOMC 前不進場）放到歷史上，賺還是賠？」
   · 積木：多單進場／多單出場／空單進場／空單出場四格，各格用「全部成立（AND）」或「任一成立（OR）」組合條件；
     加上停損、停利、移動停損、最長持有。積木會先轉成腳本文字再編譯（lab/expr.js），所以積木與腳本是同一條路徑。
   · 腳本：類 Pine 的迷你語法（中英文別名皆可），錯誤會指出第幾行。
   · 儲存：只存在這台裝置的瀏覽器（localStorage，每台裝置各自保存），可匯出／匯入 JSON；不上傳、不進 repo。
   ============================================================================ */
(function () {
  'use strict';
  const L = window.TwLab, X = window.LabExpr; if (!L || !X) return;
  let U = null, E = null;
  const KEY = 'tw.lab.rules';
  const LS = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { localStorage.setItem(k, v); return true; } catch (e) { return false; } } };
  const uid = () => 'r' + Date.now().toString(36) + Math.random().toString(36).slice(2, 5);

  /* ---------------------------------------------------------------- 儲存 */
  function load() { try { const a = JSON.parse(LS.get(KEY) || '[]'); return Array.isArray(a) ? a.filter((x) => x && x.id && x.name) : []; } catch (e) { return []; } }
  function save(rules) { return LS.set(KEY, JSON.stringify(rules)); }
  let RULES = load();
  const blank = () => ({ id: uid(), name: '我的策略', mode: 'blocks', dir: 'both', blocks: { le: { join: 'and', rows: [] }, lx: { join: 'and', rows: [] }, se: { join: 'and', rows: [] }, sx: { join: 'and', rows: [] } }, risk: { sl: 0, tp: 0, trail: 0, maxbars: 0 }, script: '', pvals: {} });
  const TEMPLATES = [
    ['均線上穿且 RSI 不過熱', { le: [['cmp', 'up', { t: 'sma', n: 5 }, { t: 'sma', n: 20 }], ['cmp', 'lt', { t: 'rsi', n: 14 }, { t: 'num', v: 70 }]], lx: [['cmp', 'dn', { t: 'sma', n: 5 }, { t: 'sma', n: 20 }]] }, { sl: 6, tp: 0, trail: 0, maxbars: 0 }],
    ['突破 20 日高、跌破 10 日低出場', { le: [['cmp', 'gt', { t: 'close' }, { t: 'hh', n: 20 }]], lx: [['cmp', 'lt', { t: 'close' }, { t: 'll', n: 10 }]] }, { sl: 0, tp: 0, trail: 8, maxbars: 0 }],
    ['布林下軌反彈、碰中軌出場', { le: [['cmp', 'up', { t: 'close' }, { t: 'bbl', n: 20, k: 2 }]], lx: [['cmp', 'up', { t: 'close' }, { t: 'bbm', n: 20, k: 2 }]] }, { sl: 5, tp: 0, trail: 0, maxbars: 20 }],
    ['FOMC 前 3 天不進場的均線策略', { le: [['cmp', 'up', { t: 'sma', n: 9 }, { t: 'sma', n: 18 }], ['evt', 'fomc', 3, 1, true]], lx: [['cmp', 'dn', { t: 'sma', n: 9 }, { t: 'sma', n: 18 }]] }, { sl: 0, tp: 0, trail: 0, maxbars: 0 }],
  ];
  function fromTemplate(t) {
    const r = blank(); r.name = t[0];
    for (const k of ['le', 'lx', 'se', 'sx']) r.blocks[k].rows = ((t[1][k]) || []).map((x) => (x[0] === 'evt' ? { kind: 'event', type: x[1], before: x[2], after: x[3], not: !!x[4] } : { kind: 'cmp', op: x[1], a: Object.assign({}, x[2]), b: Object.assign({}, x[3]) }));
    r.risk = Object.assign({}, t[2]); return r;
  }

  /* ---------------------------------------------------------------- 標準策略（2026-10-29）
     定義在 lab/standard_defs.js、預設成績由 scripts/gen_standard_strategies.js 產生 lab/standard_results.json（不是手寫的數字）。
     點一組 → 把腳本與積木（有的話）放進編輯器，同時顯示這組的預設回測成績；規則、出處、失效條件與免責的長文全部收進「?」。 */
  const SD = window.LabStandard || { DEFS: [], toRule: () => null };
  let STDR = null;
  async function loadStd() {
    if (STDR) return STDR;
    try { const r = await fetch('lab/standard_results.json', { cache: 'no-cache' }); if (r.ok) STDR = await r.json(); } catch (e) { /* 沒有結果檔就只顯示規則 */ }
    return STDR || { strategies: {}, symbols: {} };
  }
  const f1 = (x, d) => (x == null ? '—' : (+x).toFixed(d == null ? 1 : d));
  const pct = (x) => (x == null ? '—' : U.sgn(x, 1) + '%');
  const TFN = { D: '日 K', W: '週 K', 60: '60 分 K' };
  function stdHelp(d, R) {
    const st = (R.strategies || {})[d.id], h = st && st.runs.find((r) => r.sym === d.headline.sym && r.tf === d.headline.tf);
    const E_ = (t, v) => '<br><b>' + t + '</b><br>' + U.esc(v);
    let w = '';
    if (h && h.worst && h.worst.length) w = '<br><b>最慘的五筆交易（' + U.esc(h.sym) + '）</b><br>' + h.worst.map((x) => '· ' + x.d0 + ' 買 ' + x.p0 + ' → ' + x.d1 + ' 賣 ' + x.p1 + '（' + U.sgn(x.pct, 1) + '%，持有 ' + x.bars + ' 根' + (x.why ? '，' + U.esc(x.why) : '') + '）').join('<br>');
    return '<b>' + U.esc(d.name) + '</b>（' + U.esc(d.group) + '）' + E_('進場', d.rules.entry) + E_('出場', d.rules.exit) + E_('停損', d.rules.stop) + E_('停利', d.rules.tp) + E_('部位', d.rules.size) + E_('參數', d.rules.params) +
      E_('適用標的', d.applies) + E_('設計理由', d.why) + E_('出處', d.source) + E_('我們的研究怎麼說', d.evidence) + E_('什麼時候會失效', d.fail) + w +
      '<br><br><b>怎麼讀這些數字</b><br>成交＝訊號收盤後產生、下一根開盤成交；成本含手續費 0.1425%（不打折）、證交稅、滑價；期間＝該標的資料全部，買進持有從同一天的開盤算起。指數無法直接買，以 ETF 稅率近似且不含股息；個股價格已還原股息。參數是教科書預設值，事前定好、沒有看結果調過。' +
      '<br><b>免責</b><br>歷史回測，不代表未來，不構成任何投資建議；所有成交與成本為假設。';
  }
  function stdCardHTML(d, R, tf) {
    const st = (R.strategies || {})[d.id];
    const head = '<div class="cu-stdh"><b>' + U.esc(d.name) + '</b><span class="cu-chip">' + U.esc(d.group) + '</span><span class="cu-stdsub">' + U.esc(d.tagline) + '</span>' + U.qpop(stdHelp(d, R)) + '</div>';
    if (!st) return head + '<div class="lab-note">這組的預設成績尚未產生</div>';
    const h = st.runs.find((r) => r.sym === d.headline.sym && r.tf === d.headline.tf) || st.runs[0], sm = st.summary;
    const nm = (c) => ((R.symbols || {})[c] || {}).name || c;
    const T = (l, v, sub, c) => '<div class="lab-st"><span>' + l + '</span><b class="' + (c || '') + '">' + v + '</b><small>' + (sub || '') + '</small></div>';
    const tfs = ['D', 'W', '60'].filter((k) => d.tfs.indexOf(k) >= 0);
    const rows = st.runs.filter((r) => r.tf === tf).map((r) => '<tr' + (r.sym === h.sym && r.tf === h.tf ? ' class="on"' : '') + '><td>' + U.esc(nm(r.sym)) + '</td><td class="num">' + r.n + (r.n < 30 ? ' <i title="交易次數不到 30 筆，統計意義有限">少</i>' : '') + '</td><td class="num ' + U.cls(r.ret) + '">' + pct(r.ret) + '</td><td class="num ' + U.cls(r.ann) + '">' + pct(r.ann) + '</td><td class="num ' + U.cls(r.bhAnn) + '">' + pct(r.bhAnn) + '</td><td class="num ' + U.cls(r.exAnn) + '">' + pct(r.exAnn) + '</td><td class="num">−' + f1(r.mdd) + '% <small>/ −' + f1(r.bhMdd) + '%</small></td><td class="num">' + f1(r.win, 0) + '%</td><td class="num">' + (r.pf == null ? (r.pfInf ? '∞' : '—') : f1(r.pf, 2)) + '</td><td class="num dim">' + r.from.slice(0, 4) + '～' + r.to.slice(0, 4) + '</td></tr>').join('');
    const yr = h.yr.map((y) => '<div class="cu-yr"><span>' + y[0] + '</span><b class="' + U.cls(y[1]) + '">' + U.sgn(y[1], 0) + '</b><small class="' + U.cls(y[2]) + '">' + U.sgn(y[2], 0) + '</small></div>').join('');
    return head +
      '<div class="cu-stdn">預設回測：' + U.esc(nm(h.sym)) + '・' + TFN[h.tf] + '・' + h.from + '～' + h.to + '（' + f1(h.years, 1) + ' 年）　資料更新至 ' + U.esc(R.dataThrough || '') + (R.source === 'sample' ? '（樣本資料）' : '') + '</div>' +
      '<div class="lab-stats cu-stdst">' + T('年化報酬', pct(h.ann), '買進持有 ' + pct(h.bhAnn), U.cls(h.ann)) + T('總報酬', pct(h.ret), '買進持有 ' + pct(h.bhRet), U.cls(h.ret)) +
      T('最大回撤', '−' + f1(h.mdd) + '%', '買進持有 −' + f1(h.bhMdd) + '%', 'dn') + T('勝率', f1(h.win, 0) + '%', h.nWin + ' / ' + h.n + ' 筆') + T('獲利因子', h.pf == null ? (h.pfInf ? '∞' : '—') : f1(h.pf, 2), '') + T('交易次數', String(h.n), h.n < 30 ? '樣本偏少' : '期間共 ' + f1(h.years, 0) + ' 年') + '</div>' +
      '<div class="cu-stdv">' + (sm.beatBH === 0 ? '<b class="dn">已知沒有贏過買進持有</b>：' : '') + '日 K 在 ' + sm.nSym + ' 檔標的中，年化報酬勝過買進持有的有 ' + sm.beatBH + ' 檔、為正的有 ' + sm.positive + ' 檔、最大回撤比買進持有小的有 ' + sm.ddBetter + ' 檔（年化超額中位數 ' + U.sgn(sm.medianExAnn, 1) + ' 個百分點）。</div>' +
      '<div class="cu-stdt"><div class="seg" id="cuStdTf" role="tablist" aria-label="週期">' + tfs.map((k) => '<button type="button" role="tab" data-k="' + k + '" class="' + (k === tf ? 'on' : '') + '">' + TFN[k] + '</button>').join('') + '</div></div>' +
      '<div class="cu-stdtb"><table class="lab-tbl"><thead><tr><th>標的</th><th>交易</th><th>總報酬</th><th>年化</th><th>買進持有年化</th><th>超額</th><th>回撤 <small>/ 買進持有</small></th><th>勝率</th><th>獲利因子</th><th>期間</th></tr></thead><tbody>' + rows + '</tbody></table></div>' +
      '<div class="cu-yrs"><span class="cu-yrl">分年度報酬（%）<small>上：策略　下：買進持有</small></span>' + yr + '</div>';
  }
  let stdTf = 'D';
  async function paintStd() {
    const el = U.$('#cuStd'); if (!el) return;
    const r = cur(), d = r && r.std ? SD.DEFS.find((x) => x.id === r.std) : null;
    if (!d) { el.innerHTML = ''; el.hidden = true; return; }
    el.hidden = false; el.innerHTML = stdCardHTML(d, await loadStd(), d.tfs.indexOf(stdTf) >= 0 ? stdTf : 'D');
  }

  /* ---------------------------------------------------------------- 給 lab.js 用的介面 */
  function scriptOf(rule) { return rule.mode === 'script' ? rule.script : X.toScript(rule); }
  function compileRule(rule, B, events) {
    const text = scriptOf(rule);
    const res = X.compile(text, B, { events: events || [], params: rule.pvals || {} });
    return Object.assign(res, { text });
  }
  window.TwLabCustom = {
    list: () => RULES.map((r) => ({ id: r.id, name: r.name })),
    get: (id) => RULES.find((r) => r.id === id) || null,
    compile(id, B) {
      const r = RULES.find((x) => x.id === id); if (!r) return null;
      const res = compileRule(r, B, (L.data.events || {}).events || []);
      if (!res.sig) return null;
      res.sig.risk = res.risk; res.sig.dir = r.dir; return res.sig;
    },
    reload() { RULES = load(); },
    /** 從歷史回測「另存為我的策略」：把規則（腳本模式）存進這台裝置，回傳新策略的 id */
    addRule(x) {
      const r = Object.assign(blank(), x); r.risk = Object.assign({ sl: 0, tp: 0, trail: 0, maxbars: 0 }, x.risk || {});
      RULES = load(); RULES.push(r); save(RULES); return r.id;
    },
  };

  /* ---------------------------------------------------------------- 編輯器狀態 */
  function fresh() { return { cur: null, sym: '2330', B: null, msg: '', dirty: false, res: null, busy: 0, tab: 'blocks' }; }
  let S = fresh();
  const cur = () => S.cur;

  /* ---------------------------------------------------------------- 畫面 */
  const OPTS = Object.keys(X.OPD);
  function opHTML(o, path) {
    const d = X.OPD[o.t] || X.OPD.close;
    return '<select class="lab-in cb-t" data-f="' + path + '.t" aria-label="運算元">' + OPTS.map((k) => '<option value="' + k + '"' + (o.t === k ? ' selected' : '') + '>' + U.esc(X.OPD[k].name) + '</option>').join('') + '</select>' +
      d.p.map(([k, lab, def]) => '<label class="cb-p"><span>' + lab + '</span><input class="lab-in cb-n" type="number" step="any" data-f="' + path + '.' + k + '" value="' + (o[k] != null ? o[k] : def) + '"></label>').join('');
  }
  function rowHTML(b, i, r) {
    const D = U.DATA.events || { types: {} };
    if (r.kind === 'event') {
      return '<div class="cb-row cb-ev" data-b="' + b + '" data-i="' + i + '"><select class="lab-in" data-f="not"><option value="0"' + (!r.not ? ' selected' : '') + '>在事件窗內</option><option value="1"' + (r.not ? ' selected' : '') + '>不在事件窗內</option></select>' +
        '<select class="lab-in" data-f="type">' + Object.keys(D.types || {}).map((k) => '<option value="' + k + '"' + (r.type === k ? ' selected' : '') + '>' + U.esc(D.types[k]) + '</option>').join('') + '</select>' +
        '<label class="cb-p"><span>前</span><input class="lab-in cb-n" type="number" min="0" data-f="before" value="' + r.before + '"></label><label class="cb-p"><span>後</span><input class="lab-in cb-n" type="number" min="0" data-f="after" value="' + r.after + '"></label><button type="button" class="cb-x" data-del aria-label="刪除這個條件">×</button></div>';
    }
    return '<div class="cb-row" data-b="' + b + '" data-i="' + i + '">' + opHTML(r.a, 'a') +
      '<select class="lab-in cb-c" data-f="op" aria-label="比較">' + Object.keys(X.CMP).map((k) => '<option value="' + k + '"' + (r.op === k ? ' selected' : '') + '>' + X.CMP[k][0] + '</option>').join('') + '</select>' + opHTML(r.b, 'b') +
      '<button type="button" class="cb-x" data-del aria-label="刪除這個條件">×</button></div>';
  }
  const BLK = [['le', '多單進場'], ['lx', '多單出場'], ['se', '空單進場'], ['sx', '空單出場']];
  function editorHTML() {
    const r = cur(); if (!r) return '<div class="lab-note">左邊選一個策略，或按「新增」開始</div>';
    const head = '<div class="cb-head"><label class="lab-fld"><span>名稱</span><input class="lab-in cb-name" id="cuName" type="text" maxlength="30" value="' + U.esc(r.name) + '"></label>' +
      '<div class="seg" id="cuTab" role="tablist" aria-label="編輯方式"><button type="button" role="tab" data-t="blocks" class="' + (r.mode === 'blocks' ? 'on' : '') + '">積木</button><button type="button" role="tab" data-t="script" class="' + (r.mode === 'script' ? 'on' : '') + '">腳本</button></div>' +
      '<label class="lab-fld"><span>方向</span><select class="lab-in" id="cuDir"><option value="both"' + (r.dir === 'both' ? ' selected' : '') + '>多空</option><option value="long"' + (r.dir === 'long' ? ' selected' : '') + '>只做多</option><option value="short"' + (r.dir === 'short' ? ' selected' : '') + '>只做空</option></select></label>' +
      '<button type="button" class="lab-gear" id="cuSave">儲存</button><button type="button" class="lab-clear" id="cuDup">複製</button><button type="button" class="lab-clear" id="cuDel">刪除</button></div>';
    let body;
    if (r.mode === 'blocks') {
      body = '<div class="cb-grid">' + BLK.map(([k, n]) => { const b = r.blocks[k]; return '<div class="cb-blk" data-b="' + k + '"><div class="cb-bh"><b>' + n + '</b><div class="seg cb-join" data-b="' + k + '" role="tablist"><button type="button" data-j="and" class="' + (b.join !== 'or' ? 'on' : '') + '">全部成立</button><button type="button" data-j="or" class="' + (b.join === 'or' ? 'on' : '') + '">任一成立</button></div></div>' +
        (b.rows.length ? b.rows.map((x, i) => rowHTML(k, i, x)).join('') : '<div class="cb-empty">還沒有條件</div>') +
        '<div class="cb-add"><button type="button" class="lab-clear" data-add="cmp" data-b="' + k + '">＋ 條件</button><button type="button" class="lab-clear" data-add="event" data-b="' + k + '">＋ 事件條件</button></div></div>'; }).join('') + '</div>' +
        '<div class="cb-risk"><span class="cb-rt">風控</span>' + [['sl', '停損 %'], ['tp', '停利 %'], ['trail', '移動停損 %'], ['maxbars', '最長持有（根）']].map(([k, n]) => '<label class="lab-fld"><span>' + n + '</span><input class="lab-in cb-n" type="number" min="0" step="any" data-r="' + k + '" value="' + (r.risk[k] || 0) + '"></label>').join('') + '</div>';
    } else {
      body = '<textarea class="cb-script" id="cuScript" spellcheck="false" aria-label="策略腳本" placeholder="' + U.esc('若 上穿(均線(收盤,5), 均線(收盤,20)) 則 進場("多")\n若 下穿(均線(收盤,5), 均線(收盤,20)) 則 平倉("多")') + '">' + U.esc(r.script) + '</textarea><div class="cb-errs" id="cuErrs"></div><div class="cb-ps" id="cuPs"></div>' +
        '<button type="button" class="lab-clear" id="cuFromBlocks">把積木轉成腳本放進來</button>';
    }
    return head + body;
  }
  function html() {
    return '<div class="cu-mxrow"><button type="button" class="lab-gear lab-mxbtn" id="labMx" aria-expanded="false">我的策略・範本</button></div><div class="cu-wrap"><div class="cu-side lab-mx"><div class="cu-sh">我的策略</div><div class="cu-list" id="cuList"></div>' +
      '<div class="cu-btns"><button type="button" class="lab-gear" id="cuNew">新增</button><label class="lab-clear cu-imp">匯入<input type="file" id="cuImp" accept="application/json,.json" hidden></label><button type="button" class="lab-clear" id="cuExp">匯出</button></div>' +
      '<label class="lab-fld cu-tpl"><span>從範本開始</span><select class="lab-in" id="cuTpl"><option value="">選一個範本…</option>' + TEMPLATES.map((t, i) => '<option value="' + i + '">' + U.esc(t[0]) + '</option>').join('') + '</select></label>' +
      '<label class="lab-fld cu-tpl"><span>標準策略（10 組，含歷史成績）</span><select class="lab-in" id="cuStdSel"><option value="">選一組標準策略…</option>' + SD.DEFS.map((d) => '<option value="' + d.id + '">' + d.no + '. ' + U.esc(d.group + '｜' + d.name) + '</option>').join('') + '</select></label></div>' +
      '<div class="cu-main"><div class="cu-std" id="cuStd"></div><div class="cu-ed" id="cuEd"></div>' +
      '<div class="cu-test"><div class="lab-bar"><div class="lab-f lab-symw"><span>試跑標的</span><input id="labSym" class="lab-in" type="text" autocomplete="off" spellcheck="false" aria-label="搜尋標的" placeholder="代號或名稱"><div class="lab-dd" id="labSymDD" hidden></div></div><button type="button" class="lab-gear" id="cuGo">在歷史回測看完整結果</button></div><div class="lab-stats cu-stats" id="cuStats"></div></div></div></div>';
  }
  function listHTML() {
    const el = U.$('#cuList'); if (!el) return;
    el.innerHTML = RULES.length ? RULES.map((r) => '<button type="button" class="cu-item' + (cur() && cur().id === r.id ? ' on' : '') + '" data-id="' + U.esc(r.id) + '" title="' + U.esc(r.name) + '">' + U.esc(r.name) + '</button>').join('') : '<div class="cu-none">還沒有儲存的策略</div>';
  }
  function paintEd() {
    U.$('#cuEd').innerHTML = editorHTML(); listHTML();
    if (cur() && cur().mode === 'script') checkScript();
    const sv = U.$('#cuSave'); if (sv) sv.classList.toggle('dirty', S.dirty);
    paintStd();
  }
  function setDirty(v) { S.dirty = v; const sv = U.$('#cuSave'); if (sv) sv.classList.toggle('dirty', v); }

  /* ---------------------------------------------------------------- 試跑 */
  let tdeb = null;
  function schedule() { clearTimeout(tdeb); tdeb = setTimeout(trial, 350); }
  function checkScript() {
    const r = cur(); if (!r || r.mode !== 'script' || !S.B) return null;
    const res = compileRule(r, S.B, (U.DATA.events || {}).events || []);
    const er = U.$('#cuErrs'); if (er) er.innerHTML = res.errors.length ? res.errors.map((e) => '<div>' + U.esc(e) + '</div>').join('') : '';
    const ps = U.$('#cuPs'); if (ps) ps.dataset.k = res.params.map((p) => p.k).join('|');
    if (ps) ps.innerHTML = res.params.map((p) => '<label class="lab-fld"><span>' + U.esc(p.label) + '</span><input class="lab-in cb-n" type="number" step="any" data-pv="' + U.esc(p.k) + '" value="' + (r.pvals && r.pvals[p.k] != null ? r.pvals[p.k] : p.def) + '"></label>').join('');
    return res;
  }
  async function trial() {
    const r = cur(), el = U.$('#cuStats'); if (!el) return;
    if (!r || !S.B) { el.innerHTML = ''; return; }
    const my = ++S.busy, res = compileRule(r, S.B, (U.DATA.events || {}).events || []);
    if (r.mode === 'script') {
      const er = U.$('#cuErrs'); if (er) er.innerHTML = res.errors.map((e) => '<div>' + U.esc(e) + '</div>').join('');
      const ps = U.$('#cuPs'), keys = res.params.map((p) => p.k).join('|');      // 參數列只在「變數組成」變了才重建，免得打字打到一半失去焦點
      if (ps && ps.dataset.k !== keys) { ps.dataset.k = keys; ps.innerHTML = res.params.map((p) => '<label class="lab-fld"><span>' + U.esc(p.label) + '</span><input class="lab-in cb-n" type="number" step="any" data-pv="' + U.esc(p.k) + '" value="' + (r.pvals && r.pvals[p.k] != null ? r.pvals[p.k] : p.def) + '"></label>').join(''); }
    }
    const noEntry = r.mode === 'blocks' && !['le', 'se'].some((k) => r.blocks[k].rows.length);
    if (noEntry || !res.sig) { el.innerHTML = '<div class="lab-note">' + (noEntry ? '請先在「多單進場」或「空單進場」加入至少一個條件' : U.esc(res.errors[0] || '')) + '</div>'; S.res = null; return; }
    const kind = U.kindOf(S.sym), fut = kind === 'fut', key = S.sym + '|D';
    await U.ensureLoaded(key, S.B);
    const cfg = { mode: r.dir, capital: fut ? 5000000 : 1000000, sizeMode: fut ? 'units' : 'pct', sizeVal: fut ? 1 : 100, pyramiding: 1, fillOn: 'open', sl: 0, tp: 0, trail: 0, maxLoss: 0, inst: E.instDefaults(kind) };
    const out = await U.wcall({ op: 'run', key, strat: { sig: res.sig, risk: res.risk }, cfg, range: 'All', events: null });
    if (my !== S.busy) return;
    S.res = out; const s = out.stats, T = (l, v, sub, c) => '<div class="lab-st"><span>' + l + '</span><b class="' + (c || '') + '">' + v + '</b><small>' + (sub || '') + '</small></div>';
    el.innerHTML = T('總損益', U.sgn(s.net, 0), U.sgn(s.ret, 2) + '%', U.cls(s.net)) + T('最大回撤', '−' + s.mddP.toFixed(2) + '%', '', s.mdd > 0 ? 'dn' : '') + T('獲利交易', s.all.win == null ? '—' : s.all.win.toFixed(1) + '%', s.all.nWin + ' / ' + s.all.nClosed) +
      T('獲利因子', s.all.pf == null ? '—' : s.all.pf === Infinity ? '∞' : s.all.pf.toFixed(2), '') + T('交易次數', String(s.n), s.hasOpen ? '另有 ' + s.all.nOpen + ' 筆未平倉' : '全部歷史');
  }
  async function setSym(code) {
    const it = ((U.DATA.idx || {}).items || []).find((x) => x.c === code); if (!it) return;
    S.sym = code; S.B = await U.loadSeries(code, 'D'); const sym = U.$('#labSym'); if (sym) sym.value = it.c + ' ' + it.n;
    if (cur() && cur().mode === 'script') checkScript();
    await trial();
  }

  /* ---------------------------------------------------------------- 事件處理 */
  function setPath(o, path, val) { const ks = path.split('.'); let t = o; for (let i = 0; i < ks.length - 1; i++) t = t[ks[i]]; t[ks[ks.length - 1]] = val; }
  function persist() {
    const r = cur(); if (!r) return;
    const i = RULES.findIndex((x) => x.id === r.id);
    const copy = JSON.parse(JSON.stringify(r));
    if (i >= 0) RULES[i] = copy; else RULES.push(copy);
    const ok = save(RULES); setDirty(false); listHTML();
    if (!ok) alert('這台裝置不允許儲存（可能是無痕視窗）。請用「匯出」把策略存成檔案。');
  }
  function download(name, text) { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([text], { type: 'application/json' })); a.download = name; document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500); }
  function sanitize(x) {
    if (!x || typeof x !== 'object' || !x.name) return null;
    const r = blank(); r.name = String(x.name).slice(0, 30); r.mode = x.mode === 'script' ? 'script' : 'blocks'; r.dir = ['both', 'long', 'short'].includes(x.dir) ? x.dir : 'both';
    r.script = typeof x.script === 'string' ? x.script.slice(0, 5000) : '';
    r.risk = { sl: +((x.risk || {}).sl) || 0, tp: +((x.risk || {}).tp) || 0, trail: +((x.risk || {}).trail) || 0, maxbars: +((x.risk || {}).maxbars) || 0 };
    if (x.pvals && typeof x.pvals === 'object') Object.keys(x.pvals).forEach((k) => { if (Number.isFinite(+x.pvals[k])) r.pvals[k] = +x.pvals[k]; });
    for (const k of ['le', 'lx', 'se', 'sx']) {
      const b = (x.blocks || {})[k]; if (!b) continue; r.blocks[k].join = b.join === 'or' ? 'or' : 'and';
      r.blocks[k].rows = (Array.isArray(b.rows) ? b.rows : []).slice(0, 12).map((q) => {
        if (q && q.kind === 'event') return { kind: 'event', type: String(q.type || 'fomc'), before: +q.before || 0, after: +q.after || 0, not: !!q.not };
        const fix = (o) => { const t = X.OPD[o && o.t] ? o.t : 'close', v = { t }; (X.OPD[t].p || []).forEach(([kk, , def]) => { v[kk] = Number.isFinite(+(o || {})[kk]) ? +o[kk] : def; }); return v; };
        return { kind: 'cmp', op: X.CMP[q && q.op] ? q.op : 'gt', a: fix(q && q.a), b: fix(q && q.b) };
      });
    }
    return r;
  }
  async function mount(body, util) {
    U = util; E = U.E; S = fresh(); RULES = load();
    body.innerHTML = html(); listHTML();
    S.cur = RULES[0] ? JSON.parse(JSON.stringify(RULES[0])) : null;
    paintEd();
    body.onclick = async (e) => {
      const t = e.target;
      const mxb = t.closest('#labMx'); if (mxb) { U.toggleMx(body, mxb); return; }
      const it = t.closest('.cu-item'); if (it) { body.classList.remove('mx-open'); S.cur = JSON.parse(JSON.stringify(RULES.find((x) => x.id === it.dataset.id))); setDirty(false); paintEd(); schedule(); return; }
      if (t.closest('#cuNew')) { body.classList.remove('mx-open'); S.cur = blank(); setDirty(true); paintEd(); schedule(); return; }
      if (t.closest('#cuSave')) { persist(); return; }
      if (t.closest('#cuDup') && cur()) { const c = JSON.parse(JSON.stringify(cur())); c.id = uid(); c.name = c.name + ' 複本'; S.cur = c; persist(); paintEd(); return; }
      if (t.closest('#cuDel') && cur()) { const id = cur().id; RULES = RULES.filter((x) => x.id !== id); save(RULES); S.cur = RULES[0] ? JSON.parse(JSON.stringify(RULES[0])) : null; setDirty(false); paintEd(); schedule(); return; }
      if (t.closest('#cuExp')) { download('lab_strategies.json', JSON.stringify({ v: 1, rules: RULES }, null, 1)); return; }
      const tb = t.closest('#cuTab button'); if (tb && cur()) { const to = tb.dataset.t; if (to === 'script' && cur().mode === 'blocks' && !cur().script.trim()) cur().script = X.toScript(cur()); cur().mode = to; setDirty(true); paintEd(); schedule(); return; }
      const jn = t.closest('.cb-join button'); if (jn) { cur().blocks[jn.closest('.cb-join').dataset.b].join = jn.dataset.j; setDirty(true); paintEd(); schedule(); return; }
      const ad = t.closest('[data-add]'); if (ad) { const b = cur().blocks[ad.dataset.b]; const D = U.DATA.events || { types: {} }; b.rows.push(ad.dataset.add === 'event' ? { kind: 'event', type: Object.keys(D.types || {})[0] || 'fomc', before: 3, after: 1, not: true } : { kind: 'cmp', op: 'up', a: { t: 'sma', n: 5 }, b: { t: 'sma', n: 20 } }); setDirty(true); paintEd(); schedule(); return; }
      const dl = t.closest('[data-del]'); if (dl) { const row = dl.closest('.cb-row'); cur().blocks[row.dataset.b].rows.splice(+row.dataset.i, 1); setDirty(true); paintEd(); schedule(); return; }
      if (t.closest('#cuFromBlocks')) { cur().script = X.toScript(Object.assign({}, cur(), { mode: 'blocks' })); setDirty(true); paintEd(); schedule(); return; }
      const sb = t.closest('#cuStdTf button'); if (sb) { stdTf = sb.dataset.k; paintStd(); return; }
      const di = t.closest('.lab-di'); if (di) { U.$('#labSymDD').hidden = true; await setSym(di.dataset.c); return; }
      if (t.closest('#cuGo')) { if (!cur()) return; if (S.dirty || !RULES.some((x) => x.id === cur().id)) persist(); L.state().bt.strat = 'u:' + cur().id; L.state().bt.sym = S.sym; L.state().bt.mode = cur().dir; location.hash = '#lab/bt'; return; }
    };
    const onEdit = (e) => {
      const t = e.target, r = cur();
      if (t.id === 'labSym') { const dd = U.$('#labSymDD'), list = U.searchItems(t.value.replace(/^\S+\s/, '')); dd.innerHTML = list.map((x) => '<button type="button" class="lab-di" data-c="' + U.esc(x.c) + '"><b>' + U.esc(x.c) + '</b> ' + U.esc(x.n) + (U.KIND_N[x.k] ? ' <small>' + U.KIND_N[x.k] + '</small>' : '') + '</button>').join('') || '<div class="lab-note">找不到符合的標的</div>'; dd.hidden = false; return; }
      if (!r) return;
      if (t.id === 'cuName') { r.name = t.value; setDirty(true); return; }
      if (t.id === 'cuDir') { r.dir = t.value; setDirty(true); schedule(); return; }
      if (t.id === 'cuScript') { r.script = t.value; setDirty(true); schedule(); return; }
      if (t.dataset.pv) { r.pvals = r.pvals || {}; r.pvals[t.dataset.pv] = parseFloat(t.value); setDirty(true); schedule(); return; }
      if (t.dataset.r) { r.risk[t.dataset.r] = Math.max(0, parseFloat(t.value) || 0); setDirty(true); schedule(); return; }
      const row = t.closest('.cb-row'); if (row && t.dataset.f) {
        const rr = r.blocks[row.dataset.b].rows[+row.dataset.i], f = t.dataset.f; let v = t.type === 'number' ? parseFloat(t.value) : t.value;
        if (rr.kind === 'event') { if (f === 'not') v = v === '1'; if (f === 'before' || f === 'after') v = Math.max(0, v || 0); rr[f] = v; }
        else {
          const m = /^([ab])\.t$/.exec(f);
          if (m) { const t2 = v, o = { t: t2 }; (X.OPD[t2].p || []).forEach(([k, , def]) => { o[k] = def; }); rr[m[1]] = o; setDirty(true); paintEd(); schedule(); return; }   // 換運算元種類：參數換成該種類的預設值，要重畫
          setPath(rr, f, Number.isFinite(v) ? v : t.value);
        }
        setDirty(true); schedule();
      }
    };
    body.oninput = onEdit;
    body.onchange = async (e) => {
      if (e.target.id === 'cuStdSel') {
        const d = SD.DEFS.find((x) => x.id === e.target.value); e.target.value = ''; if (!d) return;
        body.classList.remove('mx-open'); S.cur = SD.toRule(d, blank); stdTf = 'D'; setDirty(true); paintEd();
        const it = ((U.DATA.idx || {}).items || []).find((x) => x.c === d.headline.sym); if (it) await setSym(d.headline.sym); else schedule();
        return;
      }
      return onchange0(e);
    };
    const onchange0 = (e) => { if (e.target.id === 'cuTpl') { const v = e.target.value; if (v !== '') { S.cur = fromTemplate(TEMPLATES[+v]); e.target.value = ''; setDirty(true); paintEd(); schedule(); } return; } if (e.target.id === 'cuImp') { const f = e.target.files[0]; if (!f) return; f.text().then((tx) => { try { const j = JSON.parse(tx), arr = Array.isArray(j) ? j : (j.rules || [j]); let n = 0; arr.forEach((x) => { const r = sanitize(x); if (r) { RULES.push(r); n++; } }); save(RULES); S.cur = n ? JSON.parse(JSON.stringify(RULES[RULES.length - 1])) : S.cur; setDirty(false); paintEd(); schedule(); if (!n) alert('檔案裡沒有可以匯入的策略'); } catch (er) { alert('匯入失敗：不是有效的策略檔'); } e.target.value = ''; }); return; } onEdit(e); };
    body.onfocusin = (e) => { if (e.target.id === 'labSym') { e.target.select(); e.target.dispatchEvent(new Event('input', { bubbles: true })); } };
    await setSym(S.sym);
  }
  L.register({ id: 'custom', name: '自訂策略', ord: 50, mount, unmount() { clearTimeout(tdeb); }, reset() { S = fresh(); }, state: () => S, api: { sanitize, compileRule, scriptOf, blank, RULES: () => RULES } });
}());
