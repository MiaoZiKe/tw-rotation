/* ============================================================================
   交易練習室 › 事件分析（#lab/evt）—— 2026-10-28 建
   這一頁回答的問題：「FOMC、選舉、法說會、結算日這些大事前後，這檔標的平均怎麼走？把事件當成進場濾網，策略的報酬與回撤差多少？」
   · 事件日期表：pipeline/groups/events_history.yaml（人工維護、每筆有出處與信心度）→ data/lab/events.json。
   · 統計與回測都在 Web Worker 裡算（lab/engine.js 的 eventStudy／runStrategy）。
   · 事件發生在美國時間時，台股隔天才反應：事件窗從「日期＋時差之後的第一個交易日」起算。
   ============================================================================ */
(function () {
  'use strict';
  const L = window.TwLab; if (!L) return;
  let U = null, E = null;
  const COL = ['#2563EB', '#F97316', '#A855F7', '#14B8A6', '#ff4d6d', '#ffb454', '#3ee0ff', '#8b7bff', '#c3ff5b'];
  const NS = [5, 10, 20];
  const CONF = { 高: '官方公布的固定日期', 中: '依公開日程整理，尚未逐筆對官網', 低: '規則推算（遇假日或調整未核對）', 資料: '由資料湖統計得出' };

  function fresh() {
    return { sym: 'TAIEX', B: null, N: 10, types: null, sel: '', events: [], tmap: {}, study: null, f: { strat: 'ma2', mode: 'avoid', before: 3, after: 1, flat: false, types: null, on: true, cmp: null }, busy: 0 };
  }
  let S = fresh();

  /* ---------------------------------------------------------------- 小元件：可勾選的多選下拉 */
  function msel(id, label, opts, on) {
    const n = opts.filter(([k]) => on.has(k)).length;
    return '<div class="lab-ms" id="' + id + '"><button type="button" class="lab-pickbtn lab-msb" aria-haspopup="listbox" aria-expanded="false">' + U.esc(label) + '：' + (n === opts.length ? '全部' : n ? n + ' 項' : '無') + ' ▾</button>' +
      '<div class="lab-mp" hidden><div class="lab-mpa"><button type="button" class="lab-clear" data-a="all">全選</button><button type="button" class="lab-clear" data-a="none">全不選</button></div>' +
      opts.map(([k, nm]) => '<label class="lab-mo"><input type="checkbox" data-k="' + k + '"' + (on.has(k) ? ' checked' : '') + '> <span>' + U.esc(nm) + '</span></label>').join('') + '</div></div>';
  }

  /* 勾選時只改按鈕上的字，不重建面板（重建會把下拉關掉，要連勾好幾個就很煩） */
  function msLabel(id, label, opts, on) {
    const b = U.$('#' + id + ' .lab-msb'); if (!b) return; const n = opts.filter(([k]) => on.has(k)).length;
    b.textContent = label + '：' + (n === opts.length ? '全部' : n ? n + ' 項' : '無') + ' ▾';
    U.$$('#' + id + ' input[data-k]').forEach((c) => { c.checked = on.has(c.dataset.k); });
  }
  const typeOpts = (D) => Object.keys(D.types || {}).map((k) => [k, D.types[k]]);

  function html() {
    return '<div class="lab-bar"><div class="lab-f lab-symw"><span>標的</span><input id="labSym" class="lab-in" type="text" autocomplete="off" spellcheck="false" aria-label="搜尋標的" placeholder="代號或名稱"><div class="lab-dd" id="labSymDD" hidden></div></div>' +
      '<div class="seg" id="evN" role="tablist" aria-label="事件前後天數">' + NS.map((n) => '<button type="button" role="tab" data-n="' + n + '">±' + n + ' 日</button>').join('') + '</div>' +
      '<span id="evTypeW"></span><span class="ev-hint" id="evHint"></span></div>' +
      '<div class="ev-grid"><div class="ev-card"><div class="ev-h">平均走勢（以事件前一日收盤為 0）</div><div class="ev-ch" id="evPath"></div></div>' +
      '<div class="ev-card"><div class="ev-h">各類事件的平均表現</div><div class="lab-twrap ev-tw" id="evStats"></div></div></div>' +
      '<div class="ev-card ev-det"><div class="ev-h" id="evDetH">事件明細</div><div class="lab-twrap ev-tw" id="evDet"></div></div>' +
      '<div class="ev-card ev-flt"><div class="ev-h">事件當濾網：加上事件條件前後比較</div><div class="ev-fbar" id="evFBar"></div><div class="ev-fres" id="evFRes"></div></div>';
  }

  /* ---------------------------------------------------------------- 統計 */
  const pc = (x, d) => (x == null || !Number.isFinite(x) ? '—' : (x > 0 ? '+' : x < 0 ? '−' : '') + Math.abs(x).toFixed(d == null ? 2 : d) + '%');
  async function run() {
    const my = ++S.busy; if (!S.B) return;
    const D = await U.loadEvents(); S.D = D;
    if (!S.types) S.types = new Set(Object.keys(D.types || {}));
    const first = S.B.dayEnd[0], last = S.B.dayEnd[S.B.n - 1];
    S.events = (D.events || []).filter((e) => { const d = E.strToDay(e.d); return d >= first && d <= last && S.types.has(e.t); });
    const key = S.sym + '|D';
    await U.ensureLoaded(key, S.B);
    const res = await U.wcall({ op: 'study', key, events: S.events, N: S.N });
    if (my !== S.busy) return;
    S.study = res;
    const keys = Object.keys(res); if (!keys.includes(S.sel)) S.sel = '';
    paint();
  }
  function paint() {
    const D = S.D || { types: {}, events: [] }, res = S.study || {};
    U.$$('#evN button').forEach((b) => b.classList.toggle('on', +b.dataset.n === S.N));
    const sym = U.$('#labSym'); if (sym && document.activeElement !== sym) { const it = ((U.DATA.idx || {}).items || []).find((x) => x.c === S.sym); sym.value = it ? it.c + ' ' + it.n : S.sym; }
    const w = U.$('#evTypeW');
    if (w && S.types) { if (!U.$('#evTypes')) w.innerHTML = msel('evTypes', '事件', typeOpts(D), S.types); else msLabel('evTypes', '事件', typeOpts(D), S.types); }
    const hint = U.$('#evHint'); if (hint) hint.textContent = '';
    const names = D.types || {}, keys = Object.keys(res).sort((a, b) => (res[b].postN.avg || 0) - (res[a].postN.avg || 0));
    // ---- 統計表（後 N 日平均加長條）
    const mx = Math.max(1, ...keys.map((k) => Math.abs(res[k].postN.avg || 0)));
    const st = U.$('#evStats');
    st.innerHTML = keys.length ? '<table class="lab-tbl"><thead><tr><th>事件</th><th>次數</th><th>前 ' + S.N + ' 日</th><th>反應日</th><th>後 1 日</th><th>後 ' + S.N + ' 日</th><th>勝率</th><th>波動比</th></tr></thead><tbody>' +
      keys.map((k, i) => { const r = res[k]; return '<tr data-t="' + k + '" class="' + (S.sel === k ? 'on' : '') + '"><td class="ev-nm"><i style="background:' + COL[Object.keys(names).indexOf(k) % COL.length] + '"></i>' + U.esc(names[k] || k) + '</td><td>' + r.n + '</td><td class="' + U.cls(r.pre.avg) + '">' + pc(r.pre.avg) + '</td><td class="' + U.cls(r.day0.avg) + '">' + pc(r.day0.avg) + '</td><td class="' + U.cls(r.post1.avg) + '">' + pc(r.post1.avg) + '</td><td class="ev-bar ' + U.cls(r.postN.avg) + '"><u style="width:' + Math.round(Math.abs(r.postN.avg || 0) / mx * 100) + '%"></u><b>' + pc(r.postN.avg) + '</b></td><td>' + (Number.isFinite(r.postN.win) ? r.postN.win.toFixed(0) + '%' : '—') + '</td><td title="事件窗內日報酬波動 ÷ 全期間日報酬波動">' + (Number.isFinite(r.volRatio) ? r.volRatio.toFixed(2) + '×' : '—') + '</td></tr>'; }).join('') + '</tbody></table>' : '<div class="lab-note">這個標的的資料範圍內沒有符合的事件</div>';
    // ---- 路徑圖
    const el = U.$('#evPath');
    if (keys.length && window.App) {
      const xs = []; for (let j = -S.N; j <= S.N; j++) xs.push(j);
      const A = window.App;
      const series = keys.map((k) => ({ name: names[k] || k, type: 'line', showSymbol: false, smooth: false, data: res[k].path.map((v) => (Number.isFinite(v) ? +v.toFixed(3) : null)), lineStyle: { width: S.sel === k ? 3.5 : 2, opacity: S.sel && S.sel !== k ? 0.25 : 1 }, itemStyle: { color: COL[Object.keys(names).indexOf(k) % COL.length] }, z: S.sel === k ? 5 : 2 }));
      series[0] && (series[0].markLine = { silent: true, symbol: 'none', lineStyle: { color: A.CH.ink3, type: 'dashed' }, label: { formatter: '事件', color: A.CH.ink2 }, data: [{ xAxis: String(0) }] });
      A.chart('evPath', { grid: { left: 52, right: 16, top: 36, bottom: 32 }, legend: { top: 0, type: 'scroll', textStyle: { color: A.CH.ink2, fontSize: 12 } }, tooltip: { trigger: 'axis', valueFormatter: (v) => (v == null ? '—' : v.toFixed(2) + '%') },
        xAxis: { type: 'category', data: xs.map(String), boundaryGap: false, axisLabel: { color: A.CH.ink2, fontSize: 12 }, name: '日', nameTextStyle: { color: A.CH.ink3 } }, yAxis: { type: 'value', axisLabel: { color: A.CH.ink2, fontSize: 12, formatter: (v) => v + '%' }, splitLine: { lineStyle: { color: A.CH.grid } } }, series });
      if (!el.dataset.bound) { el.dataset.bound = 1; }
    } else if (el) { try { const c = window.echarts && echarts.getInstanceByDom(el); c && c.dispose(); } catch (e) { /* 忽略 */ } el.innerHTML = ''; }
    // ---- 明細
    const dh = U.$('#evDetH'), dt = U.$('#evDet');
    const showT = S.sel || keys[0];
    if (showT && res[showT]) {
      dh.textContent = (names[showT] || showT) + '：逐次明細' + (S.sel ? '（再點一次同一列取消鎖定）' : '');
      dt.innerHTML = '<table class="lab-tbl"><thead><tr><th>事件日</th><th>名稱</th><th>前 ' + S.N + ' 日</th><th>反應日</th><th>後 1 日</th><th>後 ' + S.N + ' 日</th><th>信心</th></tr></thead><tbody>' +
        res[showT].list.slice().reverse().map((x) => { const ev = S.events.find((e) => e.d === x.d && e.t === showT) || {}; return '<tr title="' + U.esc(ev.src || '') + '"><td>' + x.d + '</td><td class="ev-l">' + U.esc(x.name) + '</td><td class="' + U.cls(x.pre) + '">' + pc(x.pre * 100) + '</td><td class="' + U.cls(x.day0) + '">' + pc(x.day0 * 100) + '</td><td class="' + U.cls(x.post1) + '">' + pc(x.post1 * 100) + '</td><td class="' + U.cls(x.postN) + '">' + pc(x.postN * 100) + '</td><td title="' + U.esc(CONF[ev.conf] || '') + '">' + U.esc(ev.conf || '') + '</td></tr>'; }).join('') + '</tbody></table>';
    } else { dh.textContent = '事件明細'; dt.innerHTML = '<div class="lab-note">—</div>'; }
    fbar();
  }

  /* ---------------------------------------------------------------- 事件當濾網 */
  function fbar() {
    const f = S.f, D = S.D || { types: {} }, bar = U.$('#evFBar'); if (!bar) return;
    if (!f.types) f.types = new Set(Object.keys(D.types || {}).filter((k) => k === 'fomc'));
    if (bar.dataset.built) { msLabel('evFTypes', '事件', typeOpts(D), f.types); U.$$('#evFMode button').forEach((x) => x.classList.toggle('on', x.dataset.m === f.mode)); compare(); return; }
    bar.dataset.built = 1;
    const cats = {}; E.STRATS.forEach((s) => { (cats[s.cat] = cats[s.cat] || []).push(s); });
    bar.innerHTML = '<label class="lab-f"><span>策略</span><select class="lab-in" id="evStrat">' + Object.keys(cats).map((c) => '<optgroup label="' + U.esc(c) + '">' + cats[c].map((s) => '<option value="' + s.id + '"' + (f.strat === s.id ? ' selected' : '') + '>' + U.esc(s.name) + '</option>').join('') + '</optgroup>').join('') + '</select></label>' +
      msel('evFTypes', '事件', typeOpts(D), f.types) +
      '<div class="seg" id="evFMode" role="tablist" aria-label="濾網方式"><button type="button" data-m="avoid" class="' + (f.mode === 'avoid' ? 'on' : '') + '">事件窗內不進場</button><button type="button" data-m="only" class="' + (f.mode === 'only' ? 'on' : '') + '">只在事件窗內進場</button></div>' +
      '<label class="lab-f"><span>事件前</span><input class="lab-in ev-n" id="evFB" type="number" min="0" max="30" value="' + f.before + '"><span>日</span></label><label class="lab-f"><span>事件後</span><input class="lab-in ev-n" id="evFA" type="number" min="0" max="30" value="' + f.after + '"><span>日</span></label>' +
      '<label class="lab-chk"><input type="checkbox" id="evFFlat"' + (f.flat ? ' checked' : '') + '> 進入事件窗就平倉</label>';
    compare();
  }
  async function compare() {
    const f = S.f, my = ++S.busy; if (!S.B || !f.types || !f.types.size) { U.$('#evFRes').innerHTML = '<div class="lab-note">請至少選一種事件</div>'; return; }
    const D = S.D || { events: [] }, key = S.sym + '|D';
    const kind = U.kindOf(S.sym), fut = kind === 'fut';
    const cfg = { mode: 'both', capital: 1000000, sizeMode: fut ? 'units' : 'pct', sizeVal: fut ? 1 : 100, pyramiding: 1, fillOn: 'open', sl: 0, tp: 0, trail: 0, maxLoss: 0, inst: E.instDefaults(kind), evt: { on: true, types: Array.from(f.types), mode: f.mode, before: f.before, after: f.after, flat: f.flat } };
    await U.ensureLoaded(key, S.B);
    const r = await U.wcall({ op: 'cmp', key, strat: { id: f.strat, params: E.defaults(f.strat) }, cfg, range: 'All', events: D.events });
    if (my < S.busy - 0 && false) return;
    f.cmp = r; paintCmp(cap(cfg));
  }
  const cap = (cfg) => cfg.capital;
  function paintCmp(capital) {
    const r = S.f.cmp, el = U.$('#evFRes'); if (!el || !r) return;
    const a = r.base.stats, b = r.evt.stats;
    const row = (lab, x, y, f, better) => { const dx = (y == null || x == null) ? null : y - x; const good = dx == null || !better ? '' : (better === 'hi' ? (dx > 0 ? 'up' : dx < 0 ? 'dn' : '') : (dx < 0 ? 'up' : dx > 0 ? 'dn' : '')); return '<tr><th scope="row">' + lab + '</th><td>' + f(x) + '</td><td>' + f(y) + '</td><td class="' + good + '">' + (dx == null ? '—' : (dx > 0 ? '+' : dx < 0 ? '−' : '') + f(Math.abs(dx)).replace(/^[+−-]/, '')) + '</td></tr>'; };
    const n0 = (x) => U.fmt(x, 0), p2 = (x) => (x == null ? '—' : x.toFixed(2) + '%'), x2 = (x) => (x == null ? '—' : x === Infinity ? '∞' : x.toFixed(2));
    el.innerHTML = '<div class="ev-cmp"><div class="lab-twrap ev-tw"><table class="lab-tbl lab-sum"><thead><tr><th></th><th>不加事件條件</th><th>加上事件條件</th><th>差異</th></tr></thead><tbody>' +
      row('交易次數', a.n, b.n, n0, null) + row('淨利', a.net, b.net, n0, 'hi') + row('報酬率', a.ret, b.ret, p2, 'hi') + row('最大回撤', a.mddP, b.mddP, p2, 'lo') + row('勝率', a.all.win, b.all.win, p2, 'hi') + row('獲利因子', a.all.pf, b.all.pf, x2, 'hi') + row('夏普值', a.sharpe, b.sharpe, x2, 'hi') +
      '</tbody></table></div><div class="ev-ch ev-eqc" id="evEq"></div></div>';
    if (window.App) {
      const A = window.App, B = S.B, from = 0, xs = [], v1 = [], v2 = [], step = Math.max(1, Math.floor(r.base.eq.length / 500));
      for (let i = 0; i < r.base.eq.length; i += step) { xs.push(E.dayToStr(B.dayEnd[from + i])); v1.push(Math.round(r.base.eq[i] - capital)); v2.push(Math.round(r.evt.eq[i] - capital)); }
      A.chart('evEq', { grid: { left: 64, right: 16, top: 32, bottom: 28 }, legend: { top: 0, textStyle: { color: A.CH.ink2, fontSize: 12 } }, tooltip: { trigger: 'axis' }, xAxis: { type: 'category', data: xs, axisLabel: { color: A.CH.ink2, fontSize: 12 } }, yAxis: { type: 'value', axisLabel: { color: A.CH.ink2, fontSize: 12, formatter: (v) => (Math.abs(v) >= 1e4 ? v / 1e4 + '萬' : v) }, splitLine: { lineStyle: { color: A.CH.grid } } },
        series: [{ name: '不加事件條件', type: 'line', showSymbol: false, data: v1, lineStyle: { width: 2, color: '#94a3b8' }, itemStyle: { color: '#94a3b8' } }, { name: '加上事件條件', type: 'line', showSymbol: false, data: v2, lineStyle: { width: 2.5, color: '#2563EB' }, itemStyle: { color: '#2563EB' } }] });
    }
  }

  /* ---------------------------------------------------------------- 載入與綁定 */
  async function setSym(code) {
    const it = ((U.DATA.idx || {}).items || []).find((x) => x.c === code); if (!it) return;
    S.sym = code; S.B = await U.loadSeries(code, 'D'); if (!S.B) return;
    await run();
  }
  function bindMs(body) {
    body.addEventListener('click', (e) => {
      const b = e.target.closest('.lab-msb');
      if (e.target.closest('.lab-mp')) return;                       // 在面板裡點（勾選、全選）不關
      U.$$('.lab-mp').forEach((p) => { if (!b || p !== b.nextElementSibling) p.hidden = true; });
      if (b) { const p = b.nextElementSibling; p.hidden = !p.hidden; b.setAttribute('aria-expanded', String(!p.hidden)); e.stopPropagation(); }
    });
  }
  async function mount(body, util) {
    U = util; E = U.E; S = fresh();
    body.innerHTML = html(); bindMs(body);
    body.onclick = async (e) => {
      const t = e.target;
      const n = t.closest('#evN button'); if (n) { S.N = +n.dataset.n; await run(); return; }
      const di = t.closest('.lab-di'); if (di) { U.$('#labSymDD').hidden = true; await setSym(di.dataset.c); return; }
      const tr = t.closest('#evStats tbody tr'); if (tr) { S.sel = S.sel === tr.dataset.t ? '' : tr.dataset.t; paint(); return; }
      const m = t.closest('#evFMode button'); if (m) { S.f.mode = m.dataset.m; fbar(); return; }
      const a = t.closest('.lab-mpa button');
      if (a) { const box = a.closest('.lab-ms'), id = box.id, set = id === 'evTypes' ? S.types : S.f.types, all = Object.keys((S.D || {}).types || {}); set.clear(); if (a.dataset.a === 'all') all.forEach((k) => set.add(k)); if (id === 'evTypes') await run(); else { fbar(); } return; }
    };
    body.onchange = async (e) => {
      const t = e.target;
      if (t.closest('#evTypes') && t.dataset.k) { t.checked ? S.types.add(t.dataset.k) : S.types.delete(t.dataset.k); await run(); return; }
      if (t.closest('#evFTypes') && t.dataset.k) { t.checked ? S.f.types.add(t.dataset.k) : S.f.types.delete(t.dataset.k); fbar(); return; }
      if (t.id === 'evStrat') { S.f.strat = t.value; compare(); return; }
      if (t.id === 'evFFlat') { S.f.flat = t.checked; compare(); return; }
    };
    body.oninput = (e) => {
      const t = e.target;
      if (t.id === 'evFB') { S.f.before = Math.max(0, parseInt(t.value || '0', 10)); clearTimeout(S.dt); S.dt = setTimeout(compare, 300); return; }
      if (t.id === 'evFA') { S.f.after = Math.max(0, parseInt(t.value || '0', 10)); clearTimeout(S.dt); S.dt = setTimeout(compare, 300); return; }
      if (t.id === 'labSym') { const dd = U.$('#labSymDD'), list = U.searchItems(t.value.replace(/^\S+\s/, '')); dd.innerHTML = list.map((x) => '<button type="button" class="lab-di" data-c="' + U.esc(x.c) + '"><b>' + U.esc(x.c) + '</b> ' + U.esc(x.n) + (U.KIND_N[x.k] ? ' <small>' + U.KIND_N[x.k] + '</small>' : '') + '</button>').join('') || '<div class="lab-note">找不到符合的標的</div>'; dd.hidden = false; }
    };
    body.onfocusin = (e) => { if (e.target.id === 'labSym') { e.target.select(); e.target.dispatchEvent(new Event('input', { bubbles: true })); } };
    await setSym(S.sym);
  }
  L.register({ id: 'evt', name: '事件分析', ord: 40, mount, unmount() { try { ['evPath', 'evEq'].forEach((id) => { const el = document.getElementById(id), c = el && window.echarts && echarts.getInstanceByDom(el); c && c.dispose(); }); } catch (e) { /* 忽略 */ } }, reset() { S = fresh(); }, state: () => S });
}());
