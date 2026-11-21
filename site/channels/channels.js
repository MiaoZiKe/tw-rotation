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

  /* ---------------- 貼文成績表（#channels/scores，2026-11-09）----------------
     這張表回答：「Andy 給過分的貼文，這週平均幾分、比上週進步還是退步、哪些可以當範本、哪些要找原因寫規則？」
     怎麼用：看上方三張卡知道週趨勢；表裡 80 分以上標「範本」（以後照這種寫），60 分以下標「待改」（要找原因並在「新規則」寫下來）。
     資料在 site/channels/scores.json（陣列），由 CEO 依 Andy 在聊天室給的分數更新，頁面不能輸入。 */
  let SCORES = null, scLoading = null, scFailed = false, scCh = '全部';
  function loadScores() {
    if (SCORES || scFailed) return Promise.resolve(SCORES);
    if (scLoading) return scLoading;
    scLoading = fetch('channels/scores.json', { cache: 'no-cache' })
      .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then((j) => { SCORES = Array.isArray(j) ? j : []; return SCORES; })
      .catch(() => { scFailed = true; return null; })
      .finally(() => { scLoading = null; });
    return scLoading;
  }
  /* 今天（台北）：本機驗收可用 TW_SC_TODAY 固定日期，正式站一律用真實時間 */
  function todayTpe() {
    const h = location.hostname;
    if ((h === '127.0.0.1' || h === 'localhost') && window.TW_SC_TODAY) return String(window.TW_SC_TODAY);
    return new Date(Date.now() + (new Date().getTimezoneOffset() + 480) * 60000).toISOString().slice(0, 10);
  }
  /* 週一為一週起點；用 UTC 運算避免時區位移 */
  function weekStart(ymd) {
    const d = new Date(ymd + 'T00:00:00Z'); if (isNaN(d)) return '';
    d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7));
    return d.toISOString().slice(0, 10);
  }
  const avg = (a) => (a.length ? a.reduce((s, x) => s + (+x.score || 0), 0) / a.length : null);
  const f1 = (v) => (v == null ? '—' : String(Math.round(v * 10) / 10));
  const chOf = (c) => String(c || '').trim();
  function scoreCards(list) {
    const ws = weekStart(todayTpe());
    const dl = new Date(ws + 'T00:00:00Z'); dl.setUTCDate(dl.getUTCDate() - 7);
    const lw = dl.toISOString().slice(0, 10);
    const cur = list.filter((x) => weekStart(x.date) === ws), prev = list.filter((x) => weekStart(x.date) === lw);
    const a = avg(cur), b = avg(prev), nT = list.filter((x) => x.template).length;
    let sub = prev.length + ' 篇', dcls = '';
    if (a != null && b != null) { const d = Math.round((a - b) * 10) / 10; sub = '本週比上週 ' + (d > 0 ? '▲ +' : d < 0 ? '▼ ' : '＝ ') + d; dcls = d > 0 ? 'up' : d < 0 ? 'dn' : ''; }
    return '<div class="chs-cards">'
      + '<div class="chs-card" data-k="wk"><span class="l">本週平均</span><b>' + f1(a) + '</b><em>' + cur.length + ' 篇</em></div>'
      + '<div class="chs-card" data-k="lw"><span class="l">上週平均</span><b>' + f1(b) + '</b><em class="' + dcls + '">' + sub + '</em></div>'
      + '<div class="chs-card" data-k="tp"><span class="l">範本數</span><b>' + nT + '</b><em>共評 ' + list.length + ' 篇</em></div></div>';
  }
  function scoreRows(list) {
    const rows = list.slice().sort((x, y) => String(y.date).localeCompare(String(x.date)));
    if (!rows.length) return '<div class="chx-none">這個頻道還沒有評分</div>';
    const lk = (u, t) => (/^https?:\/\//.test(u || '') ? '<a href="' + esc(u) + '" target="_blank" rel="noopener noreferrer">' + t + '</a>' : '');
    const body = rows.map((x) => {
      const s = +x.score || 0, tag = s >= 80 ? '<i class="chs-tag ok">範本</i>' : s < 60 ? '<i class="chs-tag bad">待改</i>' : '';
      const pf = x.platforms || {}, ln = x.links || {};
      const links = [pf.threads ? (lk(ln.threads, 'Threads') || '<span class="chs-dim">Threads 待補</span>') : '', pf.ig ? (lk(ln.ig, 'IG') || '<span class="chs-dim">IG 待補</span>') : ''].filter(Boolean).join(' ');
      const rule = x.rule_added ? '<div class="chs-rule">新規則：' + esc(x.rule_added) + '</div>' : (s < 60 ? '<div class="chs-rule todo">尚未寫規則</div>' : '');
      return '<tr class="chs-r" data-ch="' + esc(chOf(x.channel)) + '">'
        + '<td class="chn-c0" data-l="日期">' + esc(x.date) + '</td>'
        + '<td data-l="頻道">' + esc(chOf(x.channel)) + '</td>'
        + '<td class="chs-ti" data-l="標題" title="' + esc(x.title) + '">' + (x.cover ? '<img class="chs-cv" src="' + esc(x.cover) + '" alt="" loading="lazy">' : '') + esc(x.title) + '</td>'
        + '<td class="chs-sc" data-l="分數"><b>' + s + '</b><u class="chs-bar ' + (s >= 80 ? 'ok' : s < 60 ? 'bad' : '') + '"><s style="width:' + Math.max(0, Math.min(100, s)) + '%"></s></u>' + tag + '</td>'
        + '<td class="chs-cm" data-l="評語">' + esc(x.comment || '') + rule + '</td>'
        + '<td class="chs-lk" data-l="連結">' + (links || '<span class="chs-dim">—</span>') + '</td></tr>';
    }).join('');
    return '<div class="chn-tw"><table class="chn-t chs-t"><thead><tr><th>日期</th><th>頻道</th><th>標題</th><th>分數</th><th>評語</th><th>連結</th></tr></thead><tbody>' + body + '</tbody></table></div>';
  }
  function scoresHTML() {
    const list = SCORES || [];
    const chs = ['全部'].concat(Array.from(new Set(list.map((x) => chOf(x.channel)))).sort());
    if (chs.indexOf(scCh) < 0) scCh = '全部';
    const shown = scCh === '全部' ? list : list.filter((x) => chOf(x.channel) === scCh);
    const key = 'scores.0', open = opened[key];
    const seg = '<div class="seg chs-seg" role="group" aria-label="依頻道篩選">' + chs.map((c) => '<button type="button" data-ch="' + esc(c) + '" class="' + (c === scCh ? 'on' : '') + '">' + esc(c) + '</button>').join('') + '</div>';
    return '<div id="chsBody">' + scoreCards(list)
      + '<section class="chn-blk wide chs-blk' + (open ? ' open' : '') + '" data-k="' + key + '"><div class="chn-h" role="button" tabindex="0" aria-expanded="' + (open ? 'true' : 'false') + '"><h3>每篇成績</h3>'
      + '<span class="chn-how"><button type="button" class="chn-q" aria-label="每篇成績說明" aria-expanded="false">?</button><span class="chn-pop" role="tooltip" hidden>Andy 每篇給分加一句評語。80 分以上標「範本」，以後照這種方式發；60 分以下標「待改」，要找出原因並在「新規則」寫下來。週平均以週一為起點。</span></span>'
      + '<span class="chs-n">' + shown.length + ' 篇</span><i class="chn-car" aria-hidden="true"></i></div>'
      + '<div class="chn-b">' + seg + '<div id="chsTable">' + scoreRows(shown) + '</div></div></section></div>';
  }
  function bindScores(root) {
    $$('.chs-seg button', root).forEach((btn) => btn.addEventListener('click', () => {
      scCh = btn.dataset.ch;
      $$('.chs-seg button', root).forEach((x) => x.classList.toggle('on', x === btn));
      const list = SCORES || [], shown = scCh === '全部' ? list : list.filter((x) => chOf(x.channel) === scCh);
      $('#chsTable', root).innerHTML = scoreRows(shown);
      const n = $('.chs-n', root); if (n) n.textContent = shown.length + ' 篇';
    }));
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
    if (sub === 'scores') {
      scCh = '全部';   // 離開再進來回預設（Andy 規矩 C7）
      await loadScores();
      if (!inCh() || subOf((location.hash || '').split('/').slice(1)) !== 'scores') return;   // 載入期間使用者已切走，不要蓋掉別頁
      root.innerHTML = tabs + '<div class="chn-tag"><span>Andy 每篇給分加一句評語；80 分以上列範本、60 分以下要找原因寫規則。</span></div>'
        + (SCORES ? '<div class="chn-grid" data-sub="scores">' + scoresHTML() + '</div>' : '<div class="empty">成績表資料載入失敗，請重新整理</div>');
      bind(); if (SCORES) bindScores(root);
      return;
    }
    const tag = '<div class="chn-tag"><span>' + esc(pg.tag || '') + '</span><small>更新 ' + esc(PLAN.updated || '') + '</small></div>';
    root.innerHTML = tabs + (pg.tag ? tag : '<div class="chn-tag"><small>更新 ' + esc(PLAN.updated || '') + '</small></div>')
      + (sub === 'overview' && PLAN.cards ? overviewTop() : '')
      + '<div class="chn-grid" data-sub="' + esc(sub) + '">' + (pg.blocks || []).map((b, i) => blockHTML(sub, b, i)).join('') + '</div>'
      + (sub === 'overview' ? gapsHtml() : '');
    bind();
  }

  window.TwChannels = { show, isAdm };
})();
