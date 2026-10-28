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
      '<label class="lab-fld cu-tpl"><span>從範本開始</span><select class="lab-in" id="cuTpl"><option value="">選一個範本…</option>' + TEMPLATES.map((t, i) => '<option value="' + i + '">' + U.esc(t[0]) + '</option>').join('') + '</select></label></div>' +
      '<div class="cu-main"><div class="cu-ed" id="cuEd"></div>' +
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
    const cfg = { mode: r.dir, capital: 1000000, sizeMode: fut ? 'units' : 'pct', sizeVal: fut ? 1 : 100, pyramiding: 1, fillOn: 'open', sl: 0, tp: 0, trail: 0, maxLoss: 0, inst: E.instDefaults(kind) };
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
    body.onchange = (e) => { if (e.target.id === 'cuTpl') { const v = e.target.value; if (v !== '') { S.cur = fromTemplate(TEMPLATES[+v]); e.target.value = ''; setDirty(true); paintEd(); schedule(); } return; } if (e.target.id === 'cuImp') { const f = e.target.files[0]; if (!f) return; f.text().then((tx) => { try { const j = JSON.parse(tx), arr = Array.isArray(j) ? j : (j.rules || [j]); let n = 0; arr.forEach((x) => { const r = sanitize(x); if (r) { RULES.push(r); n++; } }); save(RULES); S.cur = n ? JSON.parse(JSON.stringify(RULES[RULES.length - 1])) : S.cur; setDirty(false); paintEd(); schedule(); if (!n) alert('檔案裡沒有可以匯入的策略'); } catch (er) { alert('匯入失敗：不是有效的策略檔'); } e.target.value = ''; }); return; } onEdit(e); };
    body.onfocusin = (e) => { if (e.target.id === 'labSym') { e.target.select(); e.target.dispatchEvent(new Event('input', { bubbles: true })); } };
    await setSym(S.sym);
  }
  L.register({ id: 'custom', name: '自訂策略', ord: 50, mount, unmount() { clearTimeout(tdeb); }, reset() { S = fresh(); }, state: () => S, api: { sanitize, compileRule, scriptOf, blank, RULES: () => RULES } });
}());
