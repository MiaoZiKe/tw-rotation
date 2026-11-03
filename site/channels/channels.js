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
      + '<div class="chn-grid" data-sub="' + esc(sub) + '">' + (pg.blocks || []).map((b, i) => blockHTML(sub, b, i)).join('') + '</div>';
    bind();
  }

  window.TwChannels = { show, isAdm };
})();
