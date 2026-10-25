/* ============================================================================
   科技透明圈（#tc → #tc/<產業id> → #tc/<產業id>/<公司>）—— 2026-10-25 建
   這一頁回答的問題：「科技業各產業、各公司、各單位的職位，實際工時／底薪／分紅／年薪／加班長怎樣？」
   怎麼用：先挑產業，用上面五組篩選縮小（篩選對公司卡與職位表同時生效），點公司卡看單位→職位表。
   資料：site/tc/json/<產業id>.json（格式見 docs/tc/schema.md，由他人產出、前端只讀）。檔案還不存在的產業照樣有分頁，內容顯示「尚無資料」。
   數字全是區間，篩選一律拿區間中點比；工時、加班是單一值／分類。
   ⚠ 所有文字用 textContent／esc 輸出，不收 HTML。
   ============================================================================ */
(function () {
  'use strict';
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  const INDS = [['foundry', '晶圓代工'], ['memory', '記憶體'], ['osat', '封測'], ['material', '半導體材料'], ['equipment', '半導體設備'], ['icdesign', 'IC 設計'], ['odm', '電子代工 ODM'], ['foreign', '外商']];
  /* ★ 2026-10-25（Andy：「這內容就算上線了也只有我可以看，其他 Plus Pro 都先隱藏」）：只有管理者（站主＋站主加的人）看得到。
     判定沿用 livegate.js 同一條：/v1/me 的 admin／owner 旗標（TwAccount.user()，還沒載入退回登入快取）。
     非管理者：html 不掛 .tc-adm → m4/20261025-tc.css 把側欄與手機導覽的入口藏掉，直接打 #tc 導回總覽。
     本機驗收用 window.TW_TC_OVERRIDE（只在 localhost／127.0.0.1 生效）。 */
  function isAdm() {
    try {
      const h = location.hostname;
      if ((h === '127.0.0.1' || h === 'localhost') && (window.TW_TC_OVERRIDE === true || window.TW_TC_OVERRIDE === false)) return window.TW_TC_OVERRIDE;
      const A = window.TwAccount; let u = null;
      if (A && typeof A.user === 'function') u = A.user();
      else if (localStorage.getItem('tw.acct.tok')) u = JSON.parse(localStorage.getItem('tw.acct.user') || 'null');
      return !!(u && (u.admin === true || u.owner === true));
    } catch (e) { return false; }
  }
  function gate() {
    const on = isAdm();
    document.documentElement.classList.toggle('tc-adm', on);
    if (!on && /^#tc(\/|$)/.test(location.hash || '')) location.replace('#overview');
    return on;
  }
  gate();
  window.addEventListener('tw:account', gate);
  window.addEventListener('hashchange', gate);

  const FOOT = '資料整理自 GoodJob、Dcard、PTT 等公開分享，僅供參考';

  /* 篩選：k＝角色欄位、opts＝[顯示字, 判斷函式]；第一個永遠是「全部」 */
  const mid = (a) => (typeof a === 'number' ? a : Array.isArray(a) && a.length ? (a[0] + a[a.length - 1]) / 2 : null);
  /* 真資料的工時可能是區間或空、加班是自由文字（例「偶爾～經常（依部門）」）：缺值一律不通過數值篩選；加班依字面歸類，同時含兩類的兩邊都算 */
  const has = (v) => v != null;
  const otIs = (r, w) => { const t = String(r.overtime || ''); return w === '幾乎不' ? /幾乎不|很少|不加班/.test(t) : t.includes(w); };
  const FILTERS = [
    { k: 'hours', t: '工時', opts: [['全部'], ['≤45', (r) => has(mid(r.weekly_hours)) && mid(r.weekly_hours) <= 45], ['46–50', (r) => has(mid(r.weekly_hours)) && mid(r.weekly_hours) > 45 && mid(r.weekly_hours) <= 50], ['51–55', (r) => has(mid(r.weekly_hours)) && mid(r.weekly_hours) > 50 && mid(r.weekly_hours) <= 55], ['>55', (r) => has(mid(r.weekly_hours)) && mid(r.weekly_hours) > 55]], tip: '每週工時（小時）' },
    { k: 'base', t: '底薪', opts: [['全部'], ['≥50K', (r) => has(mid(r.base_month_k)) && mid(r.base_month_k) >= 50], ['≥60K', (r) => has(mid(r.base_month_k)) && mid(r.base_month_k) >= 60], ['≥70K', (r) => has(mid(r.base_month_k)) && mid(r.base_month_k) >= 70], ['≥80K', (r) => has(mid(r.base_month_k)) && mid(r.base_month_k) >= 80]], tip: '月底薪區間的中點' },
    { k: 'bonus', t: '分紅月數', opts: [['全部'], ['≥4', (r) => has(mid(r.bonus_months)) && mid(r.bonus_months) >= 4], ['≥8', (r) => has(mid(r.bonus_months)) && mid(r.bonus_months) >= 8], ['≥12', (r) => has(mid(r.bonus_months)) && mid(r.bonus_months) >= 12]], tip: '年終＋分紅合計月數區間的中點' },
    { k: 'annual', t: '年薪', opts: [['全部'], ['≥100萬', (r) => has(mid(r.annual_total_wan)) && mid(r.annual_total_wan) >= 100], ['≥150萬', (r) => has(mid(r.annual_total_wan)) && mid(r.annual_total_wan) >= 150], ['≥200萬', (r) => has(mid(r.annual_total_wan)) && mid(r.annual_total_wan) >= 200], ['≥300萬', (r) => has(mid(r.annual_total_wan)) && mid(r.annual_total_wan) >= 300]], tip: '年薪總額（萬）區間的中點' },
    { k: 'ot', t: '加班', opts: [['全部'], ['幾乎不', (r) => otIs(r, '幾乎不')], ['偶爾', (r) => otIs(r, '偶爾')], ['經常', (r) => otIs(r, '經常')]], tip: '加班狀況' },
  ];
  const S = { ind: '', co: '', f: {}, sort: { k: '', d: -1 }, fopen: false, data: {}, loaded: false };

  /* 分紅發放欄只放「幾月」：從公司層 bonus_timing 抓出所有「N 月」，抓不到顯示「—」（完整說明留在公司頁頂端） */
  const btMonths = (t) => { const m = String(t || '').match(/\d{1,2}\s*月/g); return m ? Array.from(new Set(m.map((x) => x.replace(/\s/g, '')))).join('、') : '—'; };
  const dash = (x) => (x === '–' ? '—' : x);
  const rng = (a, u) => (Array.isArray(a) && a.length ? (a[0] === a[a.length - 1] ? a[0] : a[0] + '–' + a[a.length - 1]) + (u || '') : '—');
  const roleOk = (r) => FILTERS.every((F) => { const i = S.f[F.k] || 0; return i === 0 || F.opts[i][1](r); });
  const nActive = () => FILTERS.filter((F) => (S.f[F.k] || 0) > 0).length;
  const sortVal = { base: (r) => mid(r.base_month_k), bonus: (r) => mid(r.bonus_months), annual: (r) => mid(r.annual_total_wan), hours: (r) => mid(r.weekly_hours), n: (r) => r.n };

  async function loadAll() {
    if (S.loaded) return;
    await Promise.all(INDS.map(async ([id]) => {
      try { const r = await fetch('tc/json/' + id + '.json', { cache: 'no-cache' }); S.data[id] = r.ok ? await r.json() : null; }
      catch (e) { S.data[id] = null; }
    }));
    S.loaded = true;
  }

  /* 「?」小說明：點開浮出、點背景關閉（Andy 規矩 B2：說明收進 ?） */
  function howHtml() {
    return '<span class="tc-how"><button class="howbtn tc-q" type="button" aria-label="這一頁怎麼用" aria-expanded="false">?</button>' +
      '<div class="tc-pop" hidden><b>怎麼用</b><br>上方挑產業，五組篩選（工時、底薪、分紅月數、年薪、加班）同時作用在公司卡與職位表；點公司卡看各單位的職位。' +
      '數字都是整理後的區間，篩選拿區間中點比；信心度低代表來源少或彼此對不起來。' + '<br><span class="muted">' + esc(FOOT) + '</span></div></span>';
  }
  function bindHow(root) {
    const b = $('.tc-q', root), p = $('.tc-pop', root); if (!b || !p) return;
    const close = () => { p.hidden = true; b.setAttribute('aria-expanded', 'false'); };
    b.onclick = (e) => { e.stopPropagation(); p.hidden = !p.hidden; b.setAttribute('aria-expanded', String(!p.hidden)); };
    document.addEventListener('click', (e) => { if (!p.hidden && !p.contains(e.target)) close(); });
  }

  function filterBar() {
    const n = nActive();
    return '<div class="tc-fbar"><button class="tc-ftog" type="button" aria-expanded="' + S.fopen + '">篩選' + (n ? '（' + n + '）' : '') + '</button>' +
      '<div class="tc-fgrp' + (S.fopen ? ' open' : '') + '">' + FILTERS.map((F) =>
        '<div class="tc-f" title="' + esc(F.tip) + '"><span class="tc-fl">' + F.t + '</span><div class="seg" data-fk="' + F.k + '">' +
        F.opts.map((o, i) => '<button type="button" data-i="' + i + '" class="' + ((S.f[F.k] || 0) === i ? 'on' : '') + '">' + esc(o[0]) + '</button>').join('') + '</div></div>').join('') +
      '<button class="tc-clear" type="button"' + (n ? '' : ' hidden') + '>清除篩選</button></div></div>';
  }

  function srcHtml(r) {
    return (r.sources || []).map((s) => {
      const t = esc(s.site) + (s.date ? ' ' + esc(s.date) : '');
      return /^https?:\/\//.test(s.url || '') ? '<a href="' + esc(s.url) + '" target="_blank" rel="noopener noreferrer">' + t + '</a>' : '<span>' + t + '</span>';
    }).join('、') || '–';
  }
  const confCls = (c) => (c === '高' ? 'hi' : c === '中' ? 'mid' : 'lo');

  function rolesTable(roles, bt) {
    const cols = [['role', '職位'], ['deg', '學歷'], ['base', '底薪(K/月)'], ['bonus', '分紅月數'], ['am', '年薪總月數'], ['bt', '分紅發放'], ['annual', '年薪(萬)'], ['hours', '週工時'], ['ot', '加班'], ['trv', '出差'], ['n', '樣本'], ['conf', '信心'], ['src', '來源・日期']];
    const sk = S.sort.k, sd = S.sort.d;
    const units = [];
    roles.forEach((r) => { let u = units.find((x) => x.u === r.unit); if (!u) { u = { u: r.unit, rows: [] }; units.push(u); } u.rows.push(r); });
    if (sk && sortVal[sk]) units.forEach((u) => u.rows.sort((a, b) => ((sortVal[sk](a) || 0) - (sortVal[sk](b) || 0)) * sd));
    const head = '<tr>' + cols.map(([k, n]) => '<th data-sk="' + (sortVal[k] ? k : '') + '" class="' + (sortVal[k] ? 'srt' : '') + (sk === k ? ' on' : '') + '">' + n + (sk === k ? (sd < 0 ? ' ▼' : ' ▲') : '') + '</th>').join('') + '</tr>';
    const body = units.map((u) => '<tr class="tc-unit"><td colspan="13"><i></i>' + esc(u.u) + '<small>' + u.rows.length + ' 個職位</small></td></tr>' + u.rows.map((r) =>
      '<tr class="tc-row"><td data-l="職位" class="tc-role"><b>' + esc(r.role) + '</b><small>' + esc(r.years ? r.years + ' 年經驗' : '') + '</small></td>' +
      '<td data-l="學歷" class="tc-deg">' + esc(r.degree || '—') + (r.degree_diff ? '<small>學士：' + esc(r.degree_diff) + '</small>' : '') + '</td>' +
      '<td data-l="底薪(K/月)">' + rng(r.base_month_k) + '</td><td data-l="分紅月數">' + rng(r.bonus_months) + '</td><td data-l="年薪總月數">' + dash(rng(r.annual_months)) + '</td><td data-l="分紅發放">' + esc(r.bonus_timing_month || btMonths(bt)) + '</td><td data-l="年薪(萬)" class="tc-big">' + rng(r.annual_total_wan) + '</td>' +
      '<td data-l="週工時">' + rng(r.weekly_hours) + '</td><td data-l="加班"><span class="tc-ot ot-' + esc(r.overtime) + '">' + esc(r.overtime || '—') + '</span></td><td data-l="出差">' + esc(r.travel || '—') + '</td>' +
      '<td data-l="樣本">' + (r.n != null ? r.n : '–') + '</td><td data-l="信心"><span class="tc-conf ' + confCls(r.confidence) + '" title="' + esc(r.note || '') + '">' + esc(r.confidence || '–') + '</span></td>' +
      '<td data-l="來源・日期" class="tc-src">' + srcHtml(r) + '</td></tr>').join('')).join('');
    return '<div class="tc-tw"><table class="tc-tbl"><thead>' + head + '</thead><tbody>' + body + '</tbody></table></div>';
  }

  /* 公司卡：把符合篩選的職位合併成「範圍」；全部缺值就顯示「—」。加班／出差取出現最多的字面值 */
  function span(arr, u) { const v = []; arr.forEach((a) => { if (Array.isArray(a) && a.length) v.push(a[0], a[a.length - 1]); else if (typeof a === 'number') v.push(a); }); return v.length ? (Math.min(...v) === Math.max(...v) ? Math.min(...v) : Math.min(...v) + '–' + Math.max(...v)) + (u || '') : '—'; }
  function top(arr) { const m = {}; arr.filter(Boolean).forEach((x) => { m[x] = (m[x] || 0) + 1; }); const k = Object.keys(m).sort((a, b) => m[b] - m[a])[0]; return k || '—'; }
  const clip = (t, n) => { t = String(t || ''); return t.length > n ? t.slice(0, n) + '…' : t; };
  function coCard(ind, c, matched) {
    const mids = matched.map((r) => mid(r.annual_total_wan)).filter((v) => v != null);
    const hrs = matched.map((r) => mid(r.weekly_hours)).filter((v) => v != null);
    const avg = (a) => (a.length ? Math.round(a.reduce((x, y) => x + y, 0) / a.length) : '–');
    const kv = (k, v) => '<div class="tc-kv"><span>' + k + '</span><b title="' + esc(v) + '">' + esc(v) + '</b></div>';
    const sum = [['福利', c.benefits], ['認股', c.stock_plan], ['風氣', c.culture]].map((x) => '<div class="tc-sm"><span>' + x[0] + '</span>' + esc(x[1] ? clip(x[1], 38) : '—') + '</div>').join('');
    return '<a class="tc-co" href="#tc/' + ind + '/' + encodeURIComponent(c.name) + '" data-co="' + esc(c.name) + '">' +
      '<div class="tc-coh"><b>' + esc(c.name) + '</b>' + (c.code ? '<small>' + esc(c.code) + '</small>' : '') + (c.heat ? '<span class="tc-heat">' + esc(c.heat) + '</span>' : '') + '</div>' +
      '<div class="tc-cok"><div><em>' + matched.length + '</em><span>符合職位</span></div><div><em>' + avg(mids) + '</em><span>年薪中點(萬)</span></div><div><em>' + avg(hrs) + '</em><span>平均週工時</span></div></div>' +
      '<div class="tc-kvs">' + kv('底薪(K/月)', span(matched.map((r) => r.base_month_k))) + kv('分紅月數', span(matched.map((r) => r.bonus_months))) +
      kv('年薪總月數', span(matched.map((r) => r.annual_months))) + kv('分紅發放', c.bonus_timing ? clip(c.bonus_timing, 14) : '—') +
      kv('加班', top(matched.map((r) => r.overtime))) + kv('出差', top(matched.map((r) => r.travel))) + '</div>' +
      '<div class="tc-sms">' + sum + '</div></a>';
  }

  function paint() {
    const root = $('#v-tc'); if (!root) return;
    const d = S.data[S.ind];
    const tabs = '<div class="nbsw tc-tabs" role="tablist" aria-label="產業">' + INDS.map(([id, n]) => '<a href="#tc/' + id + '" role="tab" data-ind="' + id + '" class="' + (id === S.ind ? 'on' : '') + '">' + n + (S.data[id] ? '<small>' + (S.data[id].companies || []).length + '</small>' : '') + '</a>').join('') + '</div>';
    let h = '<div class="card tc-card"><div class="row spread tc-hd"><h3>' + esc((INDS.find((x) => x[0] === S.ind) || [])[1] || '') + howHtml() + '</h3><span class="tc-upd">' +
      (d ? '資料 ' + esc(d.updated || '') + '・近一年' : '') + '</span></div>' + tabs + '<div class="tc-body">';
    if (!d || !(d.companies || []).length) {
      h += '<div class="empty isempty tc-empty">尚無資料</div>';
    } else {
      h += filterBar();
      const co = S.co ? d.companies.find((x) => x.name === S.co) : null;
      if (S.co && !co) { h += '<div class="empty isempty tc-empty">找不到這家公司</div>'; }
      else if (co) {
        const m = (co.roles || []).filter(roleOk);
        h += '<div class="tc-crumb"><a href="#tc/' + S.ind + '" id="tcBack">← 返回公司列表</a></div>' +
          '<div class="tc-cinfo"><h4>' + esc(co.name) + (co.code && /^\d{4,6}$/.test(co.code) ? ' <a class="tc-code" href="#stock/' + esc(co.code) + '">' + esc(co.code) + '</a>' : '') + '</h4><dl>' +
          [['福利', co.benefits], ['員工持股', co.stock_plan], ['分紅時間', co.bonus_timing], ['風氣', co.culture], ['面試', co.interview], ['討論熱度', co.heat], ['全體非主管員工年薪' + (co.mops ? '（' + co.mops.year + '）' : ''), co.mops && co.mops.avg_wan != null ? '平均 ' + co.mops.avg_wan + ' 萬・中位 ' + (co.mops.median_wan != null ? co.mops.median_wan : '–') + ' 萬（' + (co.mops.source || '') + '）' : '']].filter((x) => x[1]).map((x) => '<div><dt>' + x[0] + '</dt><dd>' + esc(x[1]) + '</dd></div>').join('') + '</dl></div>' +
          '<div class="tc-cnt" id="tcCnt">符合篩選 <b>' + m.length + '</b> / ' + (co.roles || []).length + ' 個職位</div>' +
          (m.length ? rolesTable(m, co.bonus_timing) : '<div class="empty isempty tc-empty">沒有符合篩選的職位</div>');
      } else {
        const list = d.companies.map((c) => [c, (c.roles || []).filter(roleOk)]).filter((x) => x[1].length);
        h += '<div class="tc-cnt" id="tcCnt">符合篩選 <b>' + list.length + '</b> / ' + d.companies.length + ' 家公司</div>' +
          (list.length ? '<div class="tc-grid">' + list.map((x) => coCard(S.ind, x[0], x[1])).join('') + '</div>' : '<div class="empty isempty tc-empty">沒有符合篩選的公司</div>');
      }
    }
    h += '</div></div><div class="tc-foot">' + esc(FOOT) + '</div>';
    root.innerHTML = h;
    bindHow(root);
    $$('.tc-fbar .seg', root).forEach((sg) => $$('button', sg).forEach((b) => b.onclick = () => { S.f[sg.dataset.fk] = +b.dataset.i; paint(); }));
    const cl = $('.tc-clear', root); if (cl) cl.onclick = () => { S.f = {}; paint(); };
    const tg = $('.tc-ftog', root); if (tg) tg.onclick = () => { S.fopen = !S.fopen; paint(); };
    $$('th.srt', root).forEach((th) => th.onclick = () => { const k = th.dataset.sk; S.sort = S.sort.k === k ? { k, d: -S.sort.d } : { k, d: -1 }; paint(); });
  }

  async function show(head, rest) {
    const root = $('#v-tc'); if (!root) return;
    if (!gate()) return;   // 非管理者：gate() 已導回總覽
    const ids = INDS.map((x) => x[0]);
    const ind = ids.includes(rest[0]) ? rest[0] : ids[0];
    const co = rest[1] ? decodeURIComponent(rest[1]) : '';
    if (ind !== S.ind) { S.f = {}; S.sort = { k: '', d: -1 }; S.fopen = false; }   // 換產業回 Default（Andy 規矩 C7）
    S.ind = ind; S.co = co;
    await loadAll();
    paint();
  }

  window.TwTc = { show, state: () => S, INDS };
})();
