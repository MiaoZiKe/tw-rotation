/* ============================================================================
   頻道規劃（#channels、#channels/<子分頁>）—— 2026-11-04 建，只給站主／管理者看
   這一頁回答的問題：「我們現在有哪些社群頻道、各自要做什麼、發多少、怎麼分配、成績怎樣才算及格？」
   怎麼用：上面分頁切頻道；總覽的頻道清單點一列直接進該頻道；「?」看補充說明。
   內容全在 site/channels/plan.json（CEO 改內容只改那個檔，這支程式不動）。
   ⚠ repo 是 public：plan.json 不准放金鑰、帳密、個資。
   ⚠ 所有文字用 textContent／esc 輸出，不收 HTML。
   ============================================================================ */
(function () {
  'use strict';
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const isM = () => !!(window.matchMedia && window.matchMedia('(max-width:640px)').matches);

  /* 只給站主／管理者（Andy 11-03）：判定沿用科技透明圈（tc.js）與交易練習室的做法——
     TwAccount.user() 的 admin／owner 旗標；html 掛 .ch-adm 才顯示側欄與手機抽屜入口（CSS 在 m4/20261104-channels.css）。
     身分還沒回來（/v1/me 載入中）不能當場導走，等第一次 tw:account 或 6 秒逾時才判定。
     預覽版（TW_PREVIEW）全開；本機 127.0.0.1／localhost 用 TW_CH_OVERRIDE 驗收。 */
  function isAdm() {
    try {
      if (window.TW_PREVIEW) return true;
      const h = location.hostname;
      if ((h === '127.0.0.1' || h === 'localhost') && (window.TW_CH_OVERRIDE === true || window.TW_CH_OVERRIDE === false)) return window.TW_CH_OVERRIDE;
      const A = window.TwAccount; let u = null;
      if (A && typeof A.user === 'function') u = A.user();
      else if (localStorage.getItem('tw.acct.tok')) u = JSON.parse(localStorage.getItem('tw.acct.user') || 'null');
      return !!(u && (u.admin === true || u.owner === true));
    } catch (e) { return false; }
  }
  let known = false;
  const inCh = () => /^#channels(\/|$)/.test(location.hash || '');
  function gate() {
    const on = isAdm();
    document.documentElement.classList.toggle('ch-adm', on);
    if (!on && known && inCh()) location.replace('#overview');
    return on;
  }
  gate();
  window.addEventListener('tw:account', () => { known = true; if (gate() && inCh()) window.dispatchEvent(new HashChangeEvent('hashchange')); });
  setTimeout(() => { if (!known) { known = true; gate(); } }, 6000);
  window.addEventListener('hashchange', gate);

  /* ---------------- 資料 ---------------- */
  let PLAN = null, loading = null, failed = false;
  function load() {
    if (PLAN || failed) return Promise.resolve(PLAN);
    if (loading) return loading;
    loading = fetch('channels/plan.json', { cache: 'no-cache' })
      .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then((j) => { PLAN = j; return j; })
      .catch(() => { failed = true; return null; })
      .finally(() => { loading = null; });
    return loading;
  }

  /* 手機收展：預設全收起，使用者手動展開過的才記住 */
  let opened = {};
  try { opened = JSON.parse(localStorage.getItem('chn.open') || '{}') || {}; } catch (e) { opened = {}; }
  const saveOpen = () => { try { localStorage.setItem('chn.open', JSON.stringify(opened)); } catch (e) { /* 忽略 */ } };

  const TONE = (v) => (/運作中/.test(v) ? 'ok' : /規劃中/.test(v) ? 'plan' : /待/.test(v) ? 'wait' : '');

  function tableHTML(b) {
    const cols = b.cols || [];
    const head = '<thead><tr>' + cols.map((c) => '<th>' + esc(c) + '</th>').join('') + '</tr></thead>';
    const body = (b.rows || []).map((r, i) => {
      const go = b.go && b.go[i];
      return '<tr' + (go ? ' class="chn-go" tabindex="0" role="link" data-go="' + esc(go) + '"' : '') + '>' + r.map((c, j) => {
        const st = cols[j] === '狀態' ? ' chn-st ' + TONE(c) : '';
        return '<td class="' + (j === 0 ? 'chn-c0' : '') + st + '" data-l="' + esc(cols[j] || '') + '">' + esc(c) + '</td>';
      }).join('') + '</tr>';
    }).join('');
    return '<div class="chn-tw"><table class="chn-t">' + head + '<tbody>' + body + '</tbody></table></div>';
  }
  function blockHTML(tab, b, i) {
    const key = tab + '.' + i;
    let inner = '';
    if (b.kind === 'table') inner = tableHTML(b);
    else if (b.kind === 'chips') inner = '<div class="chn-chips">' + (b.items || []).map((x) => '<span class="chn-chip">' + esc(x) + '</span>').join('') + '</div>';
    else inner = '<ul class="chn-ul">' + (b.items || []).map((x) => '<li>' + esc(x) + '</li>').join('') + '</ul>';
    const q = b.how ? '<span class="chn-how"><button type="button" class="chn-q" aria-label="' + esc(b.h) + '說明" aria-expanded="false">?</button><span class="chn-pop" role="tooltip" hidden>' + esc(b.how) + '</span></span>' : '';
    return '<section class="chn-blk' + (b.wide ? ' wide' : '') + (b.tone ? ' ' + esc(b.tone) : '') + (opened[key] ? ' open' : '') + '" data-k="' + esc(key) + '">'
      + '<div class="chn-h" role="button" tabindex="0" aria-expanded="' + (opened[key] ? 'true' : 'false') + '"><h3>' + esc(b.h) + '</h3>' + q + '<i class="chn-car" aria-hidden="true"></i></div>'
      + '<div class="chn-b">' + inner + '</div></section>';
  }


  /* ---------------- 總覽加掛：頻道卡、週曆（撞時段標紅）、Andy 每週時數、缺漏清單（2026-11-04 併入） ----------------
     資料在 plan.json 的 cards／schedule／gaps。週曆列＝出現過的時段、欄＝週一～週日；
     撞時段＝同一天、不同頻道、相隔 60 分鐘內（回覆窗重疊；同格＝完全同時），兩格都標紅框。
     「機動」或星期不明的排程另列在週曆下方。 */
  const DAYS = ['週一', '週二', '週三', '週四', '週五', '週六', '週日'];
  const dayOf = (d) => { const m = /^週[一二三四五六日]/.exec(String(d || '')); return m ? m[0] : ''; };
  const minOf = (t) => { const m = /^(\d{1,2}):(\d{2})/.exec(String(t || '')); return m ? +m[1] * 60 + +m[2] : null; };
  const cidx = (id) => (parseInt(String(id).replace(/\D/g, ''), 10) || 1) - 1;
  const cardOf = (id) => (PLAN.cards || []).filter((c) => c.id === id)[0] || { id, no: id, name: id };
  const weekOf = (id) => (PLAN.schedule || []).filter((w) => w.ch === id).length;
  function cardsHtml() {
    return '<div class="chx-cards">' + (PLAN.cards || []).map((c) => '<a class="chx-card c' + cidx(c.id) + '" href="#channels/' + esc(c.id) + '" data-ch="' + esc(c.id) + '">'
      + '<div class="chx-h"><b class="chx-no">' + esc(c.no) + '</b><span class="chx-nm">' + esc(c.name) + '</span><span class="chx-st ' + TONE(c.status || '') + '">' + esc(c.status || '待補') + '</span></div>'
      + '<p>' + esc(c.pos || '') + '</p><div class="chx-kv"><span><em>' + weekOf(c.id) + '</em>每週發文</span><span class="' + (c.todo ? 'warn' : '') + '"><em>' + (c.todo || 0) + '</em>待 Andy</span></div></a>').join('') + '</div>';
  }
  function calHtml() {
    const cells = {}, times = {}, flex = [], all = [];
    (PLAN.schedule || []).forEach((w) => {
      const d = dayOf(w.day), tm = String(w.time || '');
      if (!d || minOf(tm) == null) { flex.push(w); return; }
      times[tm] = 1; const k = tm + '|' + DAYS.indexOf(d); (cells[k] = cells[k] || []).push(w);
      all.push({ ch: w.ch, d, m: minOf(tm), k });
    });
    const bad = {};
    all.forEach((x) => all.forEach((y) => { if (x.ch !== y.ch && x.d === y.d && Math.abs(x.m - y.m) <= 60) bad[x.k] = (bad[x.k] || '') + (x.m === y.m ? '同時段' : '相隔 ' + Math.abs(x.m - y.m) + ' 分') + '・' + cardOf(y.ch).name + '；'; }));
    const chip = (w, txt) => '<a class="chx-chip c' + cidx(w.ch) + '" href="#channels/' + esc(w.ch) + '" title="' + esc(cardOf(w.ch).name + '・' + w.day + '・' + (w.platform || '') + '・' + (w.type || '')) + '"><b>' + esc(cardOf(w.ch).no) + '</b><span class="t">' + esc(txt) + '</span></a>';
    const ts = Object.keys(times).sort();
    if (!ts.length) return '<div class="chx-none">還沒有排程資料</div>';
    let h = '<div class="chx-cal" role="table" aria-label="各頻道每週發文週曆"><div class="chx-cr hd" role="row"><span class="tm"></span>' + DAYS.map((d) => '<span role="columnheader">' + d.slice(1) + '</span>').join('') + '</div>';
    ts.forEach((tm) => {
      h += '<div class="chx-cr" role="row"><span class="tm">' + esc(tm) + '</span>';
      DAYS.forEach((d, di) => {
        const k = tm + '|' + di, cs = cells[k] || [], cl = !!bad[k];
        h += '<span class="cell' + (cl ? ' clash' : '') + '" role="cell" data-day="' + d + '" data-tm="' + esc(tm) + '"' + (cl ? ' title="撞時段（回覆窗重疊）：' + esc(bad[k]) + '"' : '') + '>' + cs.map((w) => chip(w, String(w.type || '').replace(/[（(].*$/, '').slice(0, 7))).join('') + '</span>';
      });
      h += '</div>';
    });
    h += '</div>';
    if (flex.length) h += '<div class="chx-flex"><em>機動（不限時段）</em>' + flex.map((w) => chip(w, w.platform || '')).join('') + '</div>';
    return h;
  }
  function hoursHtml() {
    const ids = (PLAN.cards || []).map((c) => c.id), mins = ids.map((id) => (PLAN.schedule || []).filter((w) => w.ch === id).reduce((n, w) => n + (+w.andy_min || 0), 0));
    const mx = Math.max.apply(null, mins.concat([1])), tot = mins.reduce((a, b) => a + b, 0);
    return '<div class="chx-hours">' + ids.map((id, i) => '<div class="chx-hr c' + cidx(id) + '"><span class="n">' + esc(cardOf(id).no) + ' ' + esc(cardOf(id).name) + '</span><i class="bar"><u style="width:' + Math.round(mins[i] / mx * 100) + '%"></u></i><b>' + mins[i] + ' 分</b></div>').join('')
      + '</div><div class="chx-note">排程加總每週 <b>' + tot + ' 分</b>（約 ' + (tot / 60).toFixed(1) + ' 小時），只算要 Andy 動手的部分。</div>';
  }
  function gapsHtml() {
    const g = PLAN.gaps || []; if (!g.length) return '';
    return '<details class="chx-gaps" id="chxGaps"><summary>缺漏清單<small>（' + g.length + ' 項）</small></summary><div class="chx-gtab">' + g.map((x) => {
      const c = (PLAN.cards || []).filter((k) => k.id === x.channel)[0];
      return '<div class="chx-gr"><b>' + esc(c ? c.no + ' ' + c.name : x.channel) + '</b><span>' + esc(x.item) + '</span><em>原本：' + esc(x.was || '—') + '</em><em class="fx">處理：' + esc(x.fixed || '待補') + '</em></div>';
    }).join('') + '</div></details>';
  }
  function overviewTop() {
    return cardsHtml() + '<div class="chx-two"><section class="chx-sec"><h3>每週發文週曆<small>紅框＝同天兩頻道相隔 60 分內，回覆窗重疊</small></h3>' + calHtml() + '</section>'
      + '<section class="chx-sec"><h3>Andy 每週要花的時間</h3>' + hoursHtml() + '</section></div>';
  }

  function subOf(rest) {
    const id = (rest && rest[0]) || 'overview';
    return PLAN.tabs.some((t) => t.id === id) ? id : 'overview';
  }

  let bound = false;
  function bind() {
    if (bound) return; bound = true;
    document.addEventListener('click', (e) => {
      const root = $('#v-channels'); if (!root || !root.contains(e.target)) { closePops(); return; }
      const q = e.target.closest('.chn-q');
      if (q) {
        e.stopPropagation();
        const pop = q.nextElementSibling, was = !pop.hidden;
        closePops();
        if (!was) { pop.hidden = false; q.setAttribute('aria-expanded', 'true'); }
        return;
      }
      closePops();
      const go = e.target.closest('tr.chn-go');
      if (go) { location.hash = '#channels/' + go.dataset.go; return; }
      const h = e.target.closest('.chn-h');
      if (h && isM()) toggle(h.parentElement);
    });
    document.addEventListener('keydown', (e) => {
      const root = $('#v-channels'); if (!root || !root.contains(e.target)) return;
      if (e.key === 'Escape') { closePops(); return; }
      if (e.key !== 'Enter' && e.key !== ' ') return;
      const go = e.target.closest && e.target.closest('tr.chn-go');
      if (go) { e.preventDefault(); location.hash = '#channels/' + go.dataset.go; return; }
      const h = e.target.closest && e.target.closest('.chn-h');
      if (h && isM() && e.target === h) { e.preventDefault(); toggle(h.parentElement); }
    });
  }
  function closePops() { $$('#v-channels .chn-pop').forEach((p) => { p.hidden = true; }); $$('#v-channels .chn-q').forEach((q) => q.setAttribute('aria-expanded', 'false')); }
  function toggle(sec) {
    const on = !sec.classList.contains('open');
    sec.classList.toggle('open', on);
    const h = $('.chn-h', sec); if (h) h.setAttribute('aria-expanded', on ? 'true' : 'false');
    if (on) opened[sec.dataset.k] = 1; else delete opened[sec.dataset.k];
    saveOpen();
  }

  async function show(head, rest) {
    const root = $('#v-channels'); if (!root) return;
    if (!gate()) { if (!known) root.innerHTML = '<div class="empty">確認登入身分中…</div>'; return; }
    await load();
    if (!PLAN) { root.innerHTML = '<div class="empty">頻道規劃資料載入失敗，請重新整理</div>'; return; }
    const sub = subOf(rest);
    const pg = PLAN.pages[sub] || { blocks: [] };
    const tabs = '<div class="nbsw chn-tabs" role="tablist" aria-label="頻道規劃">' + PLAN.tabs.map((t) =>
      '<a href="#channels/' + esc(t.id) + '" role="tab" data-sub="' + esc(t.id) + '" class="' + (t.id === sub ? 'on' : '') + '" aria-selected="' + (t.id === sub ? 'true' : 'false') + '">' + esc(t.t) + '</a>').join('') + '</div>';
    const tag = '<div class="chn-tag"><span>' + esc(pg.tag || '') + '</span><small>更新 ' + esc(PLAN.updated || '') + '</small></div>';
    root.innerHTML = tabs + (pg.tag ? tag : '<div class="chn-tag"><small>更新 ' + esc(PLAN.updated || '') + '</small></div>')
      + (sub === 'overview' && PLAN.cards ? overviewTop() : '')
      + '<div class="chn-grid" data-sub="' + esc(sub) + '">' + (pg.blocks || []).map((b, i) => blockHTML(sub, b, i)).join('') + '</div>'
      + (sub === 'overview' ? gapsHtml() : '');
    bind();
  }

  window.TwChannels = { show, isAdm };
})();
