// 績效總表（rewards_design.md 第七節）：CEO 置頂一列＋各部門一列，部門可展開看成員；14 欄、任一欄可排序、可切週次、
// 「只看需要加強」；桌機依欄寬自動收次要欄位（不橫向捲動藏欄），手機（< 720 寬）改卡片列，預設全部收起。
// 資料全讀 rewards.js（前端不重算等第），這裡只負責排序、篩選、畫出來、點了飛到 3D 裡的那個人或部門。
const $ = id => document.getElementById(id);
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

// 欄位：min＝這一欄至少要幾 px；tpl＝grid 欄寬；pr＝優先級（1 一定留，2 次要，3 最先收）；drop＝空間不夠時的收欄順序（小的先收）
const COLS = [
  { k: 'name', label: '單位', min: 170, tpl: 'minmax(170px,1.6fr)', pr: 1, cls: 'l' },
  { k: 'grade', label: '等第', min: 44, tpl: '44px', pr: 1 },
  { k: 'score', label: '分數', min: 52, tpl: '52px', pr: 1 },
  { k: 'delta', label: '升降', min: 68, tpl: '68px', pr: 1, title: '本週對上週' },
  { k: 'tasks', label: '任務數', min: 84, tpl: '84px', pr: 1, title: '未完成／進行中／已完成' },
  { k: 'done_rate', label: '完成率', min: 56, tpl: '56px', pr: 1 },
  { k: 'ontime', label: '準時率', min: 56, tpl: '56px', pr: 2, drop: 3 },
  { k: 'reject_rate', label: '退件率', min: 56, tpl: '56px', pr: 1 },
  { k: 'token_ratio', label: 'Token', min: 64, tpl: '64px', pr: 2, drop: 4, title: 'Token 效率：實際用量 ÷ 預算，1 倍以下較好' },
  { k: 'time_ratio', label: '工時', min: 60, tpl: '60px', pr: 2, drop: 5, title: '時間效率：實際工時 ÷ 預估工時，1 倍以下較好' },
  { k: 'false_reports', label: '不實', min: 52, tpl: '52px', pr: 2, drop: 6, title: '回報不實次數' },
  { k: 'top_loss', label: '主要扣分', min: 112, tpl: 'minmax(112px,1fr)', pr: 1, title: '主要扣分原因' },
  { k: 'advice', label: '建議補強', min: 150, tpl: 'minmax(150px,1.4fr)', pr: 2, drop: 2, title: '建議補強動作' },
  { k: 'acc', label: '配件／設備', min: 120, tpl: 'minmax(120px,.9fr)', pr: 3, drop: 1, title: '目前配件（Agent）與設備等級（部門）' },
];
const GAP = 6, PADX = 24;
const MOBILE_SORTS = [['score', '分數'], ['delta', '升降'], ['grade', '等第'], ['reject_rate', '退件率'], ['done_rate', '完成率'], ['name', '名稱']];

export function createLedger(W, R, X) {
  const { ui } = X, el = $('ledger'), L = { open: false }; R.ledger = L;
  const st = { wi: 0, key: 'score', dir: -1, need: false, exp: new Set(), mobile: false, cols: COLS.slice(), opener: null, helpOpen: false, flash: null };
  const ceoNo = () => R.index(st.wi).ceo;
  const W0 = () => R.index(st.wi).w;

  // ── 取值與排序 ──
  const num = v => (v == null ? null : +v);
  const taskSum = t => (t ? t.todo + t.doing + t.done : null);
  function val(u, k) {
    const r = u.row;
    switch (k) {
      case 'name': return u.kind === 'ceo' ? 'CEO' : u.kind === 'dept' ? R.deptName(u.id) : R.nickOf(u.id);
      case 'grade': return r.grade ? R.rules.length - R.rules.findIndex(x => x[1] === r.grade) : null;   // S 最大
      case 'score': return num(r.grade ? r.score : null);
      case 'delta': return r.grade ? num(r.delta) : null;
      case 'tasks': return taskSum(r.tasks);
      case 'top_loss': return r.grade ? R.reasonLabel(r.top_loss) || '' : null;
      case 'advice': return r.advice || '';
      case 'acc': return u.kind === 'dept' ? r.level : (r.acc || []).length;
      default: return r.grade ? num(r[k]) : null;
    }
  }
  const cmp = (a, b) => {
    const x = val(a, st.key), y = val(b, st.key);
    if (x == null && y == null) return 0; if (x == null) return 1; if (y == null) return -1;   // 沒資料的一律排最後，不管正序倒序
    const c = typeof x === 'string' ? x.localeCompare(y, 'zh-Hant') : x - y; return c * st.dir || (R.nickOf(a.id) < R.nickOf(b.id) ? -1 : 1);
  };
  // 展開單位清單（每個 unit：{kind,id,row,dept,subs[]}）
  function build() {
    const x = R.index(st.wi), ceo = { kind: 'ceo', id: 'ceo', row: x.ceo, dept: 'ceo', subs: [] };
    let depts = [...x.depts.values()].map(d => ({ kind: 'dept', id: d.id, row: d, dept: d.id, subs: Object.entries(d.members).map(([id, m]) => ({ kind: 'agent', id, row: m, dept: d.id })) }));
    if (st.need) {
      depts = depts.map(d => ({ ...d, subs: d.subs.filter(s => R.need(s.row)) })).filter(d => R.need(d.row) || d.subs.length);
    }
    depts.forEach(d => d.subs.sort(cmp)); depts.sort(cmp);
    return { ceo: st.need && !R.need(x.ceo) ? null : ceo, depts };
  }
  const isOpen = u => (u.kind === 'agent' ? st.exp.has(u.id) : st.need ? u.subs.length > 0 : st.exp.has(u.id));

  // ── 單元格 ──
  const pct = v => (v == null ? '—' : Math.round(v * 100) + '%');
  const rat = v => (v == null ? '—' : v.toFixed(2) + '×');
  const flagIcon = '<i class="fg" aria-hidden="true"></i>';
  function cell(u, c) {
    const r = u.row, ok = r.grade != null;
    switch (c.k) {
      case 'grade': return R.chip(r.grade);
      case 'score': return ok ? `<span class="mono">${r.score.toFixed(r.score % 1 ? 1 : 0)}</span>` : '—';
      case 'delta': return ok ? R.deltaHtml(r) : '<span class="dl na">—</span>';
      case 'tasks': return r.tasks ? `<span class="tk" title="未完成 ${r.tasks.todo}・進行中 ${r.tasks.doing}・已完成 ${r.tasks.done}"><i class="t1">${r.tasks.todo}</i><i class="t2">${r.tasks.doing}</i><i class="t3">${r.tasks.done}</i></span>` : '—';
      case 'done_rate': case 'ontime': case 'reject_rate': return `<span class="mono">${ok ? pct(r[c.k]) : '—'}</span>`;
      case 'token_ratio': case 'time_ratio': return `<span class="mono${ok && r[c.k] > 1.1 ? ' warn' : ''}">${ok ? rat(r[c.k]) : '—'}</span>`;
      case 'false_reports': return ok ? `<span class="mono${r.false_reports ? ' warn' : ''}">${r.false_reports || 0}</span>` : '—';
      case 'top_loss': { if (!ok) return '<span class="mut">樣本不足</span>'; const t = R.reasonLabel(r.top_loss); return t ? `<span class="loss" title="${esc(t)}">${r.flag ? flagIcon : ''}${esc(t)}</span>` : '<span class="mut">—</span>'; }
      case 'advice': return r.advice ? `<span class="adv" title="${esc(r.advice)}">${esc(r.advice)}</span>` : '<span class="mut">—</span>';
      case 'acc': return u.kind === 'dept' ? `<span class="lvb l${r.level}" title="設備等級 L${r.level}（${['', '簡配', '基本', '標準', '進階', '旗艦'][r.level]}）">L${r.level}</span>${r.levelPending ? `<span class="pend" title="${esc(r.levelPending.note || '')}">緩衝中</span>` : ''}` : u.kind === 'ceo' ? `${R.accChips(r.acc, 5)}<span class="lvb l${r.level}" title="辦公室設備等級 L${r.level}">L${r.level}</span>` : R.accChips(r.acc, 6);
      default: return '';
    }
  }
  const nameInner = u => {
    if (u.kind === 'ceo') return '<b>CEO</b><small>總經理</small>';
    if (u.kind === 'dept') { const n = Object.keys(u.row.members).length; return `<b>${esc(R.deptName(u.id))}</b><small>${n} 人</small>`; }
    const fired = W.hr && W.hr.isFired(u.id); return `<b>${esc(R.nickOf(u.id))}</b><small>${esc(R.zhOf(u.id))}${fired ? '・待業中' : ''}</small>`;
  };
  const dot = id => { const d = W.org.departments.find(q => q.id === id); return d ? `<i class="dd" style="background:${d.color}"></i>` : '<i class="dd ceo"></i>'; };

  function rowHtml(u, sub) {
    const open = isOpen(u), can = u.kind !== 'agent', lbl = u.kind === 'ceo' ? 'CEO' : R.deptName(u.id);
    const cells = st.cols.map(c => c.k === 'name'
      ? `<div class="c l nm" role="cell">${can ? `<button class="lg-caret" data-act="tog" aria-expanded="${open}" aria-label="${open ? '收合' : '展開'}${esc(lbl)}${u.kind === 'ceo' ? '的六個面向' : '成員'}" title="${open ? '收合' : '展開'}"><i></i></button>` : '<span class="lg-sp"></span>'}${dot(u.dept)}<button class="lg-go" data-act="go" title="到辦公室看${esc(lbl)}">${nameInner(u)}</button></div>`
      : `<div class="c" role="cell">${cell(u, c)}</div>`).join('');
    return `<div class="lg-row ${sub ? 'sub' : 'top'}${u.kind === 'ceo' ? ' ceo' : ''}${st.flash === u.id ? ' flash' : ''}" role="row" data-u="${u.kind}:${u.id}" data-lvl="${sub ? 'sub' : 'top'}" data-grade="${u.row.grade || ''}">${cells}</div>`;
  }
  function dimsHtml(u) {
    const dims = u.row.dims; if (!dims) return '';
    return `<div class="lg-dims" role="row" data-for="ceo">${Object.entries(dims).map(([k, v]) => `<div class="dim"><span>${esc(R.data.dimLabels[k] || k)}</span><div class="bar"><i style="width:${Math.max(2, v)}%"></i></div><b class="mono">${v}</b></div>`).join('')}${u.row.advice ? `<p class="dadv">${esc(u.row.advice)}</p>` : ''}</div>`;
  }

  // ── 桌機表格 ──
  function tableHtml(B) {
    const head = st.cols.map(c => `<div class="h${c.cls ? ' ' + c.cls : ''}" role="columnheader" aria-sort="${st.key === c.k ? (st.dir < 0 ? 'descending' : 'ascending') : 'none'}"><button data-sort="${c.k}" title="${esc(c.title || '依「' + c.label + '」排序')}">${esc(c.label)}<i class="ar">${st.key === c.k ? (st.dir < 0 ? '▼' : '▲') : ''}</i></button></div>`).join('');
    let body = ''; const rows = [];
    if (B.ceo) { rows.push(rowHtml(B.ceo, false)); if (isOpen(B.ceo)) rows.push(dimsHtml(B.ceo)); }
    for (const d of B.depts) { rows.push(rowHtml(d, false)); if (isOpen(d)) d.subs.forEach(s => rows.push(rowHtml(s, true))); }
    body = rows.join('') || '<div class="lg-empty">目前沒有符合的單位</div>';
    return `<div class="lg-head" role="row">${head}</div><div class="lg-body" role="rowgroup">${body}</div>`;
  }
  // ── 手機卡片 ──
  function cardHtml(u, sub) {
    const r = u.row, open = isOpen(u), ok = r.grade != null, nx = R.next(r);
    const lbl = u.kind === 'ceo' ? 'CEO' : u.kind === 'dept' ? R.deptName(u.id) : R.nickOf(u.id);
    const more = [['準時率', pct(ok ? r.ontime : null)], ['Token 效率', ok ? rat(r.token_ratio) : '—'], ['工時效率', ok ? rat(r.time_ratio) : '—'], ['回報不實', ok ? String(r.false_reports || 0) : '—'], ['主要扣分', ok ? (R.reasonLabel(r.top_loss) || '—') : '樣本不足'], ['建議補強', r.advice || '—'],
      [u.kind === 'dept' ? '設備' : u.kind === 'ceo' ? '辦公室' : '配件', u.kind === 'dept' ? R.levelText(r) : u.kind === 'ceo' ? R.levelText(r) : R.accChips(r.acc, 8)]];
    const sublist = u.kind === 'dept' && open ? `<div class="lg-subs">${u.subs.map(s => cardHtml(s, true)).join('')}</div>` : '';
    return `<div class="lg-card${sub ? ' sub' : ''}${u.kind === 'ceo' ? ' ceo' : ''}${st.flash === u.id ? ' flash' : ''}" data-u="${u.kind}:${u.id}" data-lvl="${sub ? 'sub' : 'top'}" data-grade="${r.grade || ''}">
      <div class="lg-c1" role="button" tabindex="0" data-act="card" aria-expanded="${open}" aria-label="${esc(lbl)}，${open ? '收合' : '展開'}">${dot(u.dept)}<span class="nm"><b>${esc(lbl)}</b>${u.kind === 'dept' ? `<small>${Object.keys(r.members).length} 人</small>` : u.kind === 'agent' ? `<small>${esc(R.zhOf(u.id))}</small>` : ''}</span>${R.chip(r.grade)}<span class="mono sc">${ok ? r.score.toFixed(r.score % 1 ? 1 : 0) : '—'}</span>${ok ? R.deltaHtml(r) : '<span class="dl na">—</span>'}<i class="chev"></i></div>
      <div class="lg-c2"><span>完成率 <b class="mono">${ok ? pct(r.done_rate) : '—'}</b></span><span>退件率 <b class="mono">${ok ? pct(r.reject_rate) : '—'}</b></span><span>任務 ${r.tasks ? `<span class="tk"><i class="t1">${r.tasks.todo}</i><i class="t2">${r.tasks.doing}</i><i class="t3">${r.tasks.done}</i></span>` : '—'}</span></div>
      ${open ? `<dl class="lg-c3">${more.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('')}</dl>${nx && !nx.top ? `<p class="lg-nx">距離下一級：再 +${nx.need} 分到 ${nx.to}</p>` : ''}${u.kind === 'ceo' && r.dims ? `<div class="lg-dims">${Object.entries(r.dims).map(([k, v]) => `<div class="dim"><span>${esc(R.data.dimLabels[k] || k)}</span><div class="bar"><i style="width:${Math.max(2, v)}%"></i></div><b class="mono">${v}</b></div>`).join('')}</div>` : ''}<button class="btn lg-gob" data-act="go">到辦公室看</button>` : ''}
      ${sublist}</div>`;
  }

  // ── 整體畫面 ──
  const weekCode = w => w.week.slice(5);
  function ctlHtml() {
    const ws = R.weeks, near = ws.slice(0, 4), older = ws.slice(4);
    const wsel = `<select id="lgWeek" class="lg-sel" aria-label="週次">${ws.map((w, i) => `<option value="${i}"${i === st.wi ? ' selected' : ''}>${weekCode(w)}${i === 0 ? '（本週）' : ''}</option>`).join('')}</select>`;
    if (st.mobile) return `${wsel}<select id="lgSort" class="lg-sel" aria-label="排序">${MOBILE_SORTS.map(([k, n]) => `<option value="${k}"${st.key === k ? ' selected' : ''}>${n}</option>`).join('')}</select><button class="btn lg-sw${st.need ? ' on' : ''}" data-act="need" aria-pressed="${st.need}">只看需要加強</button>`;
    return `<div class="seg lg-wk" role="group" aria-label="週次">${near.map((w, i) => `<button data-wk="${i}" class="${st.wi === i ? 'on' : ''}" aria-pressed="${st.wi === i}" title="${w.range[0]} 至 ${w.range[1]}">${weekCode(w)}</button>`).join('')}</div>${older.length ? `<select id="lgOld" class="lg-sel" aria-label="更早的週次"><option value="">更早 ▾</option>${older.map((w, i) => `<option value="${i + 4}"${st.wi === i + 4 ? ' selected' : ''}>${weekCode(w)}</option>`).join('')}</select>` : ''}<button class="btn lg-sw${st.need ? ' on' : ''}" data-act="need" aria-pressed="${st.need}" title="只留等第 D 以下、本週降級、有回報不實或有琥珀旗的單位">只看需要加強</button><button class="btn" data-act="all" ${st.need ? 'disabled' : ''}>${st.exp.size ? '全部收合' : '全部展開'}</button>`;
  }
  const sub = () => { const w = W0(); const m = w.range[0].slice(5).replace('-', '/') + '–' + w.range[1].slice(5).replace('-', '/'); return `${w.week}・${m}`; };
  function frame() {
    el.innerHTML = `<div class="lg-top"><h3>績效總表${R.data.demo ? '<span class="demo" title="目前是示範資料">示範</span>' : ''}<button class="q2" data-act="help" aria-expanded="false" aria-label="績效怎麼算">?</button></h3><span class="lg-sub" id="lgSub">${sub()}</span><button class="x" data-act="close" aria-label="關閉">×</button></div>
      <div class="lg-help" id="lgHelp" hidden><p>${R.HELP}</p><p>設備等級：S＝L5 旗艦、A＝L4 進階、B＝L3 標準、C 與 D＝L2 基本、E 與 F＝L1 簡配；連續 2 週達標或未達標才變動，緩衝中的單位會標「緩衝中」。「需要加強」＝等第 D 以下、本週降級、有回報不實，或部門有琥珀旗。人力吃緊的單位建議補人，不代表表現差。</p></div>
      <div class="lg-ctl" id="lgCtl">${ctlHtml()}</div><div class="lg-scroll" id="lgScroll" tabindex="-1"></div>`;
    paint();
  }
  function measure() {
    const w = el.clientWidth, mob = w > 0 && w < 720; st.mobile = mob;
    let cols = COLS.slice(); const sum = cs => cs.reduce((n, c) => n + c.min, 0) + GAP * (cs.length - 1) + PADX;
    if (!mob) { const avail = w - 24; const drops = COLS.filter(c => c.drop).sort((a, b) => a.drop - b.drop); for (const d of drops) { if (sum(cols) <= avail) break; cols = cols.filter(c => c !== d); } }
    st.cols = cols;
  }
  // 重畫會換掉按鈕：鍵盤操作時把焦點還給「同一顆」（用 id 或 data 屬性找回來），不然 Tab 順序會斷
  function focusSel() {
    const a = document.activeElement; if (!a || !el.contains(a) || a === el) return ''; const q = a.closest('[data-u]'), u = q ? `[data-u="${q.dataset.u}"] ` : '';
    if (a.id) return '#' + a.id; if (a.dataset.sort) return `[data-sort="${a.dataset.sort}"]`; if (a.dataset.wk) return `[data-wk="${a.dataset.wk}"]`; if (a.dataset.act) return u + `[data-act="${a.dataset.act}"]`; return '';
  }
  function paint() {
    const fs = focusSel(); paint0(); if (fs) { const n = el.querySelector(fs); if (n && !n.disabled) n.focus({ preventScroll: true }); }
  }
  function paint0() {
    const sc = $('lgScroll'); if (!sc) return; const keep = sc.scrollTop, B = build();
    if (st.mobile) sc.innerHTML = `<div class="lg-cards">${[B.ceo, ...B.depts].filter(Boolean).map(u => cardHtml(u, false)).join('') || '<div class="lg-empty">目前沒有符合的單位</div>'}</div>`;
    else { sc.innerHTML = tableHtml(B); sc.firstElementChild.style.gridTemplateColumns = st.cols.map(c => c.tpl).join(' '); sc.querySelectorAll('.lg-row').forEach(r => { r.style.gridTemplateColumns = st.cols.map(c => c.tpl).join(' '); }); }
    sc.scrollTop = keep; el.classList.toggle('mob', st.mobile);
    const ctl = $('lgCtl'); if (ctl) { ctl.dataset.mode = st.mobile ? 'm' : 'd'; ctl.innerHTML = ctlHtml(); }
    const s = $('lgSub'); if (s) s.textContent = sub();
    if (st.flash) { const t = st.flash; st.flash = null; const row = sc.querySelector(`[data-u$=":${t}"]`); if (row) { row.scrollIntoView({ block: 'nearest' }); setTimeout(() => row.classList.remove('flash'), 1800); } }
  }
  // 面板放在頂列、鏡頭操作提示、時間小標「下面」（桌機這三者在左上疊成兩三排），才不會蓋住它們
  const placeTop = () => { let b = $('bar').getBoundingClientRect().bottom; document.querySelectorAll('.cm-hint,.dt-chip,.pw-sign').forEach(n => { const r = n.getBoundingClientRect(); if (r.width && r.top < 220) b = Math.max(b, r.bottom); }); el.style.setProperty('--lg-top', Math.round(Math.max(56, b + 8)) + 'px'); };
  let ro = null;
  L.open = dept => {
    if (innerWidth <= 640 && document.body.classList.contains('m-more')) $('moreBtn').click();   // 手機：「更多」抽屜收起來，總表才有整屏可用
    ui.closePops(); ui.hideCard(); $('board').hidden = true; if (W.pilot && W.pilot.sel) W.pilot.deselect();
    if (dept && R.index(st.wi).depts.has(dept)) { st.exp.add(dept); st.flash = dept; }
    el.hidden = false; placeTop(); st.opener = document.activeElement && document.activeElement !== document.body ? document.activeElement : $('rwBtn');
    measure(); frame();
    document.body.classList.add('lg-on'); $('rwBtn').classList.add('on'); $('rwBtn').setAttribute('aria-expanded', 'true');
    if (!ro) { ro = new ResizeObserver(() => { if (el.hidden) return; const m = st.mobile, cols = st.cols.length; measure(); if (m !== st.mobile || cols !== st.cols.length) { paint(); } }); ro.observe(el); }
    el.focus({ preventScroll: true });
  };
  L.isOpen = () => !el.hidden;
  L.close = () => { if (el.hidden) return; el.hidden = true; document.body.classList.remove('lg-on'); $('rwBtn').classList.remove('on'); $('rwBtn').setAttribute('aria-expanded', 'false'); const o = st.opener; st.opener = null; if (o && o.focus && document.contains(o)) o.focus({ preventScroll: true }); };
  L.state = st;
  L.refresh = () => { if (!el.hidden) paint(); };
  el.tabIndex = -1;

  const parseU = node => { const p = node.closest('[data-u]'); if (!p) return null; const [kind, ...r] = p.dataset.u.split(':'); return { kind, id: r.join(':') }; };
  function go(u) {
    L.close();
    if (u.kind === 'dept') { X.fly(u); return; } X.fly(u);
  }
  el.addEventListener('click', e => {
    const t = e.target.closest('button,[role=button],[data-act],[data-sort],[data-wk]'); if (!t) return;
    if (e.detail) queueMicrotask(() => { if (t.matches('button')) t.blur(); });
    const act = t.dataset.act;
    if (t.dataset.sort) { const k = t.dataset.sort; if (st.key === k) st.dir *= -1; else { st.key = k; st.dir = k === 'name' || k === 'top_loss' || k === 'advice' ? 1 : -1; } paint(); return; }
    if (t.dataset.wk != null) { st.wi = +t.dataset.wk; paint(); return; }
    if (act === 'close') { L.close(); return; }
    if (act === 'help') { st.helpOpen = !st.helpOpen; $('lgHelp').hidden = !st.helpOpen; t.setAttribute('aria-expanded', st.helpOpen); return; }
    if (act === 'need') { st.need = !st.need; paint(); return; }
    if (act === 'all') { if (st.exp.size) st.exp.clear(); else R.index(st.wi).depts.forEach((d, id) => st.exp.add(id)); paint(); return; }
    const u = parseU(t); if (!u) return;
    if (act === 'tog' || act === 'card') { if (act === 'tog' && u.kind === 'agent') return; st.exp.has(u.id) ? st.exp.delete(u.id) : st.exp.add(u.id); paint(); return; }
    if (act === 'go') { go(u); return; }
  });
  // 點整列（名稱以外的格子）也能飛過去
  el.addEventListener('click', e => { if (e.target.closest('button,[role=button],select,a,.lg-dims')) return; const row = e.target.closest('.lg-row'); if (!row) return; const u = parseU(row); if (u) go(u); });
  el.addEventListener('change', e => {
    const t = e.target;
    if (t.id === 'lgWeek') { st.wi = +t.value; paint(); }
    else if (t.id === 'lgOld') { if (t.value !== '') { st.wi = +t.value; paint(); } }
    else if (t.id === 'lgSort') { st.key = t.value; st.dir = t.value === 'name' ? 1 : -1; paint(); }
  });
  el.addEventListener('keydown', e => {
    if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); L.close(); return; }
    const c = e.target.closest && e.target.closest('[data-act="card"]'); if (c && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); c.click(); }
  });
  addEventListener('resize', () => { if (!el.hidden) { placeTop(); } });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !el.hidden && !$('fireDlg')) { e.preventDefault(); L.close(); } });
  $('rwBtn').onclick = () => { if (el.hidden) L.open(); else L.close(); };
  return L;
}
