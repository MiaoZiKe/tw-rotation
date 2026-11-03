/* ============================================================================
   頻道規劃（#channels，2026-11-04）—— 管理者專用的社群頻道管理頁
   ----------------------------------------------------------------------------
   Andy 11-04：「幫我在我那網頁新增頻道規劃 母分頁 方便我管理 觀看，裡面要有主題方向 規劃 短中長期 目標
   如何經營 發文方式 IG Thread 如何分配 等等」。
   · 資料：site/channels/index.json 列出頻道 id；每個頻道一個 <id>.json（欄位見 ai_intro.json）。
     讀不到的頻道顯示「整理中」，不讓整頁壞掉（另兩個頻道的規劃是別人同步在寫）。
   · 路由：#channels（總覽）、#channels/<頻道 id>（單一頻道）。子分頁用全站共用的 .nbsw。
   · 閘門：同流向驗證（flowcheck.js）——html 掛 .ch-adm 才顯示側欄／手機抽屜入口，
     非管理者直接打網址導回 #overview；本機 127.0.0.1 用 window.TW_LAB_OVERRIDE 模擬。
     ⚠ 這只是「入口與路由」的閘；site/channels/*.json 是靜態檔，知道網址的人讀得到，
       所以 JSON 裡不准放金鑰、帳密、收入數字等機密，只放規劃本身。
   · 規矩對照（docs/andy_ui_rules.md）：頁首已有標題，卡內不重複；說明收進「?」；收展預設收起；
     表格外包 .ch-scroll 讓手機可用手指橫拖。
   ============================================================================ */
(function () {
  'use strict';
  var $ = function (s, el) { return (el || document).querySelector(s); };
  var $$ = function (s, el) { return Array.prototype.slice.call((el || document).querySelectorAll(s)); };
  var esc = function (s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); };
  var arr = function (x) { return Array.isArray(x) ? x : []; };
  var NUM = ['①', '②', '③', '④', '⑤', '⑥'];
  /* 頻道 JSON 還沒到齊時的暫用名稱（只用在「整理中」的佔位） */
  var FALLBACK = { stock: '台股資金輪動頻道', tech_transparency: '科技透明圈頻道', ai_intro: 'AI 介紹頻道' };
  var DEFAULT_IDS = ['stock', 'tech_transparency', 'ai_intro'];

  /* ---------------------------------------------------------------- 只給管理者 */
  var known = false;
  function isAdm() {
    try {
      if (window.TW_PREVIEW) return true;
      var h = location.hostname;
      if ((h === '127.0.0.1' || h === 'localhost') && (window.TW_LAB_OVERRIDE === true || window.TW_LAB_OVERRIDE === false)) return window.TW_LAB_OVERRIDE;
      var Ac = window.TwAccount, u = null;
      if (Ac && typeof Ac.user === 'function') u = Ac.user();
      else if (localStorage.getItem('tw.acct.tok')) u = JSON.parse(localStorage.getItem('tw.acct.user') || 'null');
      return !!(u && (u.admin === true || u.owner === true));
    } catch (e) { return false; }
  }
  function gate() {
    var on = isAdm();
    document.documentElement.classList.toggle('ch-adm', on);
    /* 身分還沒確認（/v1/me 沒回來）前不導走，避免管理者被誤踢；確認不是管理者才導回總覽 */
    if (!on && known && /^#channels(\/|$)/.test(location.hash || '')) location.replace('#overview');
    return on;
  }
  gate();
  window.addEventListener('tw:account', function () {
    known = true;
    if (gate() && /^#channels(\/|$)/.test(location.hash || '')) window.dispatchEvent(new HashChangeEvent('hashchange'));
  });
  setTimeout(function () { if (!known) { known = true; gate(); } }, 6000);
  window.addEventListener('hashchange', gate);

  /* ---------------------------------------------------------------- 資料 */
  var S = { ids: null, data: {}, sub: 'overview', phase: {}, bound: false };
  function jget(p) {
    return fetch(p, { cache: 'no-cache' }).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; });
  }
  function load() {
    return jget('channels/index.json').then(function (ix) {
      var ids = ix && arr(ix.channels).length ? ix.channels.filter(function (x) { return typeof x === 'string' && /^[a-z0-9_]+$/.test(x); }) : DEFAULT_IDS;
      S.ids = ids;
      return Promise.all(ids.map(function (id) {
        return jget('channels/' + id + '.json').then(function (d) { S.data[id] = d && typeof d === 'object' ? d : null; });
      }));
    });
  }

  /* ---------------------------------------------------------------- 小工具 */
  function kindOf(d) { var k = String(d && d.status_kind || '').toLowerCase(); return /^[a-z]+$/.test(k) ? k : 'plan'; }
  function badge(d) { return '<span class="ch-st ch-k-' + kindOf(d) + '">' + esc(d.status || '') + '</span>'; }
  function modeCls(m) { m = String(m || ''); return /半/.test(m) ? 'semi' : /^自動|自動（/.test(m) ? 'auto' : 'man'; }
  function modeChip(m) { return '<em class="ch-md ch-md-' + modeCls(m) + '">' + esc(m) + '</em>'; }
  function logoSrc(d) {
    var l = d && d.logo; if (!l || !l.src) return '';
    var s = String(l.src);
    if (!/^[\w./%-]+$/.test(s) && !/^(https?:|data:)/.test(s)) return '';
    if (/^(https?:|data:|\/)/.test(s)) return s;
    return s.indexOf('/') >= 0 ? s : 'channels/logos/' + s;
  }
  function logoHtml(d, cls) {
    var s = logoSrc(d); if (!s) return '';
    return '<img class="ch-logo ' + (cls || '') + '" src="' + esc(s) + '" alt="" loading="lazy" onerror="this.remove()">';
  }
  function pending(d) { return arr(d.decisions).filter(function (x) { return /待/.test(String(x.status || '')); }).length; }
  /* 每週量：各階段排程列數的範圍（沒排程列的階段不算） */
  function weekly(d) {
    var ns = arr(d.schedule).map(function (p) { return arr(p.rows).length; }).filter(function (n) { return n > 0; });
    if (!ns.length) return '—';
    var lo = Math.min.apply(null, ns), hi = Math.max.apply(null, ns);
    return (lo === hi ? lo : lo + '～' + hi) + ' 則';
  }
  function mins(p) { return arr(p.rows).reduce(function (a, r) { return a + (Number(r.minutes) || 0); }, 0); }
  function platOf(s) { s = String(s || ''); return /IG/i.test(s) ? 'ig' : /Threads/i.test(s) ? 'th' : 'ot'; }
  function titleOf(id, i) { var d = S.data[id]; return (d && d.name) || FALLBACK[id] || id; }
  function numOf(id, i) { var d = S.data[id]; return NUM[((d && d.no) || (i + 1)) - 1] || String(i + 1); }
  function help(txt) {
    return '<span class="ch-how"><button type="button" class="ch-q" aria-label="說明" aria-expanded="false">?</button><span class="ch-pop" hidden>' + txt + '</span></span>';
  }
  function list(a, cls) { return '<ul class="' + (cls || 'ch-ul') + '">' + arr(a).map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul>'; }
  function scroll(html) { return '<div class="ch-scroll">' + html + '</div>'; }

  /* ---------------------------------------------------------------- 子分頁列 */
  function tabsHtml() {
    var t = '<a href="#channels" role="tab" data-ch="overview" class="' + (S.sub === 'overview' ? 'on' : '') + '">總覽</a>';
    S.ids.forEach(function (id, i) {
      var d = S.data[id];
      t += '<a href="#channels/' + id + '" role="tab" data-ch="' + id + '" class="' + (S.sub === id ? 'on' : '') + '" title="' + esc(titleOf(id, i)) + '">' +
        (d ? logoHtml(d, 'ch-logo-s') : '') + '<span class="ch-tn">' + numOf(id, i) + ' ' + esc(titleOf(id, i)) + '</span>' +
        (d ? '<i class="ch-dot ch-k-' + kindOf(d) + '" aria-hidden="true"></i>' : '<i class="ch-dot ch-k-wait" aria-hidden="true"></i>') + '</a>';
    });
    return '<div class="nbsw ch-tabs" role="tablist" aria-label="頻道">' + t + '</div>';
  }

  /* ---------------------------------------------------------------- 總覽 */
  function overviewHtml() {
    var rows = S.ids.map(function (id, i) {
      var d = S.data[id];
      var link = '<a class="ch-nm" href="#channels/' + id + '">' + logoHtml(d, 'ch-logo-s') + '<b>' + numOf(id, i) + ' ' + esc(titleOf(id, i)) + '</b></a>';
      if (!d) return '<tr class="ch-wait"><td>' + link + '</td><td colspan="6" class="muted">整理中（頻道資料檔還沒到）</td></tr>';
      var g = d.goals || {};
      var first = function (k) { var it = arr((g[k] || {}).items)[0]; return it ? esc(it) : '—'; };
      return '<tr><td>' + link + '</td><td class="ch-c-tag">' + esc(d.tagline || '') + '</td><td>' + badge(d) + '</td>' +
        '<td>' + esc((d.platforms && d.platforms.decision) || '—') + '</td><td class="ch-n">' + esc(weekly(d)) + '</td>' +
        '<td><div class="ch-g3"><span><i>短</i>' + first('short') + '</span><span><i>中</i>' + first('mid') + '</span><span><i>長</i>' + first('long') + '</span></div></td>' +
        '<td class="ch-n"><b class="' + (pending(d) ? 'ch-pend' : '') + '">' + pending(d) + '</b> 項</td></tr>';
    }).join('');
    var how = help('三個頻道並排比較：定位、目前狀態、先做哪些平台、每週大約發幾則（取各階段排程列數）、短／中／長期目標各取第一條、還沒決定的事項數。點頻道名稱進入完整規劃；每週量與決定數由各頻道資料檔自動算出。');
    return '<div class="card ch-card"><div class="row spread ch-hd"><h3>三頻道並排' + how + '</h3><span class="ch-upd">共 ' + S.ids.length + ' 個頻道</span></div>' +
      scroll('<table class="ch-tbl ch-ov"><thead><tr><th>頻道</th><th>定位</th><th>狀態</th><th>平台</th><th>每週量</th><th>目標（短／中／長第一條）</th><th>待決定</th></tr></thead><tbody>' + rows + '</tbody></table>') + '</div>';
  }

  /* ---------------------------------------------------------------- 單一頻道 */
  function waitHtml(id, i) {
    return '<div class="card ch-card ch-waitcard"><div class="row spread ch-hd"><h3>' + numOf(id, i) + ' ' + esc(titleOf(id, i)) + '</h3><span class="ch-st ch-k-wait">整理中</span></div>' +
      '<div class="empty isempty">這個頻道的規劃資料整理中，完成後會自動出現在這裡。</div></div>';
  }

  function goalsHtml(d) {
    var g = d.goals || {};
    return '<div class="ch-goals">' + ['short', 'mid', 'long'].map(function (k) {
      var o = g[k] || {}; var items = arr(o.items);
      return '<div class="card ch-card ch-gc ch-gc-' + k + '"><h4>' + esc(o.label || { short: '短期', mid: '中期', long: '長期' }[k]) + '</h4>' +
        (items.length ? list(items, 'ch-ul ch-gl') : '<p class="muted">尚未設定</p>') + '</div>';
    }).join('') + '</div>';
  }

  function topHtml(d, i) {
    var a = d.audience || {};
    var plat = (d.platforms && d.platforms.decision) || '—';
    var more = '';
    if (d.why) more += '<h5>為什麼做</h5><p>' + esc(d.why) + '</p>';
    if (a.sub || a.note) more += '<h5>次要受眾與備註</h5><p>' + esc([a.sub, a.note].filter(Boolean).join('；')) + '</p>';
    if (arr(d.relation).length) more += '<h5>與其他頻道的關係</h5>' + list(d.relation);
    var meaning = d.logo && d.logo.meaning ? '<p class="ch-lmean"><b>LOGO 意涵</b>　' + esc(d.logo.meaning) + '</p>' : '';
    var how = help('這張卡回答「這個頻道是誰、給誰看」。下面依序是：目標（短中長期要到哪）、主題方向（發什麼）、發文排程（什麼時候發）、手動或自動、IG／Threads 分配、信任與變現、專業人員、待你決定的事、文件連結。展開的區塊預設收起，點標題列才打開。');
    return '<div class="card ch-card ch-top"><div class="row spread ch-hd"><h3>' + logoHtml(d, 'ch-logo-m') + numOf(d.id, i) + ' ' + esc(d.name || '') + how + '</h3>' +
      '<span class="ch-hd-r">' + badge(d) + (d.updated ? '<span class="ch-upd">更新 ' + esc(d.updated) + '</span>' : '') + '</span></div>' +
      '<p class="ch-tag">' + esc(d.tagline || '') + '</p>' +
      '<div class="ch-facts"><span><i>主要受眾</i>' + esc(a.main || '—') + '</span><span><i>平台</i>' + esc(plat) + '</span><span><i>每週量</i>' + esc(weekly(d)) + '</span><span><i>待決定</i><b class="' + (pending(d) ? 'ch-pend' : '') + '">' + pending(d) + '</b> 項</span></div>' +
      meaning +
      (more ? '<details class="ch-more"><summary>為什麼做・次要受眾・頻道關係</summary>' + more + '</details>' : '') + '</div>';
  }

  function pillarsHtml(d) {
    var ps = arr(d.pillars);
    var how = help('每張卡是一個內容支柱：佔比條＝這類內容該佔全部貼文的比例，下面寫適合的形式與主要平台。點「選題」可展開具體題目；★＝必須是你親手做過才能發。');
    var cards = ps.map(function (p, k) {
      var tp = arr(p.topics);
      return '<div class="ch-pil"><div class="ch-pil-h"><b>' + esc(p.name) + '</b><span class="ch-pct">' + esc(p.share == null ? '' : p.share + '%') + '</span></div>' +
        '<div class="ch-bar" role="img" aria-label="佔比 ' + esc(p.share) + '%"><i style="width:' + Math.max(0, Math.min(100, Number(p.share) || 0)) + '%"></i></div>' +
        (p.types ? '<p class="ch-pt">' + esc(p.types) + '</p>' : '') + (p.platform ? '<p class="ch-pp"><em>' + esc(p.platform) + '</em></p>' : '') +
        (tp.length ? '<details class="ch-tp"><summary>選題 ' + tp.length + ' 則</summary>' + list(tp, 'ch-ul ch-tl') + '</details>' : '') + '</div>';
    }).join('');
    return '<div class="card ch-card"><div class="row spread ch-hd"><h3>主題方向' + how + '</h3><span class="ch-upd">' + ps.length + ' 個支柱</span></div>' +
      '<div class="ch-pgrid">' + cards + '</div>' + (d.topic_note ? '<p class="ch-note">' + esc(d.topic_note) + '</p>' : '') + '</div>';
  }

  function schedBody(d, pi) {
    var p = arr(d.schedule)[pi]; if (!p) return '';
    var rows = arr(p.rows);
    return '<p class="ch-ps"><b>' + esc(p.weeks || '') + '</b>　' + esc(p.summary || '') + '</p>' +
      (rows.length ? scroll('<table class="ch-tbl"><thead><tr><th>星期</th><th>時間</th><th>平台</th><th>內容類型</th><th>方式</th><th>你的時間</th></tr></thead><tbody>' +
        rows.map(function (r) {
          return '<tr><td>' + esc(r.day) + '</td><td class="ch-n">' + esc(r.time) + '</td><td>' + esc(r.platform) + '</td><td>' + esc(r.type) + '</td><td>' + modeChip(r.mode) + '</td><td class="ch-n">' + esc(r.minutes == null ? '' : r.minutes + ' 分') + '</td></tr>';
        }).join('') + '</tbody></table>') : '<div class="empty isempty">這個階段沒有固定排程列，依前面階段的數字再決定。</div>');
  }
  function schedHtml(d) {
    var sc = arr(d.schedule);
    if (!sc.length) return '<div class="card ch-card"><div class="row spread ch-hd"><h3>發文排程</h3></div><div class="empty isempty">排程整理中</div></div>';
    var cur = Math.min(S.phase[d.id] || 0, sc.length - 1);
    var how = help('依時間分階段：先少量起步，數字好再加量。每個階段一張表，寫哪天幾點發什麼、手動還是半自動、你要花幾分鐘。切換上面的階段鈕看不同時期。');
    return '<div class="card ch-card ch-sched" data-id="' + esc(d.id) + '"><div class="row spread ch-hd"><h3>發文排程' + how + '</h3><span class="ch-upd">' + sc.length + ' 階段</span></div>' +
      '<div class="nbsw ch-ptabs" role="tablist" aria-label="排程階段">' + sc.map(function (p, k) {
        return '<button type="button" role="tab" data-ph="' + k + '" class="' + (k === cur ? 'on' : '') + '">' + esc(p.phase) + '<small>' + esc(p.weeks || '') + '</small></button>';
      }).join('') + '</div><div class="ch-sbody">' + schedBody(d, cur) + '</div></div>';
  }

  function sec(title, hint, body, open) {
    return '<details class="card ch-card ch-sec"' + (open ? ' open' : '') + '><summary><b>' + esc(title) + '</b><span class="ch-sh">' + esc(hint || '') + '</span></summary><div class="ch-sb">' + body + '</div></details>';
  }

  function autoBody(d) {
    var a = arr(d.automation);
    return scroll('<table class="ch-tbl"><thead><tr><th>工作</th><th>方式</th><th>原因</th></tr></thead><tbody>' + a.map(function (r) {
      return '<tr><td>' + esc(r.type) + '</td><td>' + modeChip(r.mode) + '</td><td>' + esc(r.reason) + '</td></tr>';
    }).join('') + '</tbody></table>');
  }
  function platBody(d) {
    var p = d.platforms || {};
    var LB = { decision: '決定', threads: 'Threads', ig: 'IG', account: '帳號' };
    var cards = Object.keys(p).filter(function (k) { return typeof p[k] === 'string'; }).map(function (k) {
      return '<div class="ch-pc"><h5>' + esc(LB[k] || k) + '</h5><p>' + esc(p[k]) + '</p></div>';
    }).join('');
    var rows = arr(d.schedule).filter(function (s) { return arr(s.rows).length; }).map(function (s) {
      var c = { th: 0, ig: 0, ot: 0 }; arr(s.rows).forEach(function (r) { c[platOf(r.platform)]++; });
      return '<tr><td>' + esc(s.phase) + '</td><td class="ch-n">' + c.th + '</td><td class="ch-n">' + c.ig + '</td><td class="ch-n">' + c.ot + '</td><td class="ch-n">' + arr(s.rows).length + '</td><td class="ch-n">' + mins(s) + ' 分</td></tr>';
    }).join('');
    return '<div class="ch-pcs">' + cards + '</div>' + (rows ? '<h5 class="ch-sub">每週分配（由排程列算出）</h5>' + scroll('<table class="ch-tbl"><thead><tr><th>階段</th><th>Threads</th><th>IG</th><th>其他</th><th>合計則數</th><th>你的時間</th></tr></thead><tbody>' + rows + '</tbody></table>') : '');
  }
  function trustBody(d) {
    var mo = arr(d.monetize);
    return '<div class="ch-two"><div><h5>信任守則</h5>' + list(d.trust) + '</div><div><h5>變現路徑</h5>' + (mo.length ? scroll('<table class="ch-tbl"><thead><tr><th>路徑</th><th>門檻</th><th>開始</th></tr></thead><tbody>' + mo.map(function (m) {
      return '<tr><td>' + esc(m.path) + '</td><td>' + esc(m.threshold) + '</td><td>' + esc(m.start) + '</td></tr>';
    }).join('') + '</tbody></table>') : '<p class="muted">尚未規劃</p>') + '</div></div>';
  }
  function teamBody(d) {
    return scroll('<table class="ch-tbl"><thead><tr><th>職責</th><th>負責人員</th><th>做什麼</th></tr></thead><tbody>' + arr(d.team).map(function (r) {
      return '<tr><td>' + esc(r.role) + '</td><td>' + esc(r.who) + '</td><td>' + esc(r.duty) + '</td></tr>';
    }).join('') + '</tbody></table>');
  }
  function decBody(d) {
    var dc = arr(d.decisions), nd = arr(d.needs);
    return '<h5>待你決定</h5>' + scroll('<table class="ch-tbl"><thead><tr><th>事項</th><th>選項</th><th>建議</th><th>狀態</th></tr></thead><tbody>' + dc.map(function (r) {
      return '<tr><td>' + esc(r.q) + '</td><td>' + esc(r.options) + '</td><td>' + esc(r.rec) + '</td><td>' + (/待/.test(String(r.status)) ? '<em class="ch-md ch-md-semi">' + esc(r.status) + '</em>' : '<em class="ch-md ch-md-auto">' + esc(r.status) + '</em>') + '</td></tr>';
    }).join('') + '</tbody></table>') +
      '<h5 class="ch-sub">要你提供的東西</h5>' + scroll('<table class="ch-tbl"><thead><tr><th>內容</th><th>用在哪</th><th>急迫度</th></tr></thead><tbody>' + nd.map(function (r) {
        return '<tr><td>' + esc(r.item) + '</td><td>' + esc(r.use) + '</td><td>' + (/最急|擋/.test(String(r.urgency)) ? '<em class="ch-md ch-md-semi">' + esc(r.urgency) + '</em>' : esc(r.urgency)) + '</td></tr>';
      }).join('') + '</tbody></table>');
  }
  function docsBody(d) {
    return '<ul class="ch-ul ch-docs">' + arr(d.docs).map(function (x) {
      var u = String(x.url || ''); var ok = /^https:\/\//.test(u);
      return '<li>' + (ok ? '<a href="' + esc(u) + '" target="_blank" rel="noopener">' + esc(x.label) + '</a>' : esc(x.label)) + '</li>';
    }).join('') + '</ul>';
  }

  function channelHtml(id, i) {
    var d = S.data[id];
    if (!d) return waitHtml(id, i);
    d.id = d.id || id;
    return topHtml(d, i) + goalsHtml(d) + pillarsHtml(d) + schedHtml(d) +
      sec('手動或自動', arr(d.automation).length + ' 項工作', autoBody(d)) +
      sec('IG／Threads 分配', (d.platforms && d.platforms.decision) || '', platBody(d)) +
      sec('信任與變現', arr(d.trust).length + ' 條守則・' + arr(d.monetize).length + ' 條路徑', trustBody(d)) +
      sec('專業人員', arr(d.team).length + ' 個職責', teamBody(d)) +
      sec('待 Andy 決定／要提供的東西', '待決定 ' + pending(d) + ' 項・要提供 ' + arr(d.needs).length + ' 項', decBody(d)) +
      sec('文件連結', arr(d.docs).length + ' 份', docsBody(d));
  }

  /* ---------------------------------------------------------------- 畫面 */
  function bind(root) {
    if (S.bound) return; S.bound = true;
    root.addEventListener('click', function (e) {
      var q = e.target.closest('.ch-q');
      if (q) {
        var pop = q.parentNode.querySelector('.ch-pop');
        var open = pop.hidden; $$('.ch-pop', root).forEach(function (p) { p.hidden = true; }); $$('.ch-q', root).forEach(function (b) { b.setAttribute('aria-expanded', 'false'); });
        pop.hidden = !open; q.setAttribute('aria-expanded', String(open));
        return;
      }
      var ph = e.target.closest('.ch-ptabs button');
      if (ph) {
        var card = ph.closest('.ch-sched'), id = card.dataset.id, k = Number(ph.dataset.ph);
        S.phase[id] = k;
        $$('.ch-ptabs button', card).forEach(function (b) { b.classList.toggle('on', b === ph); });
        $('.ch-sbody', card).innerHTML = schedBody(S.data[id], k);
        return;
      }
      if (!e.target.closest('.ch-how')) $$('.ch-pop', root).forEach(function (p) { p.hidden = true; });
    });
  }

  function paint() {
    var root = $('#v-channels'); if (!root) return;
    var i = S.ids.indexOf(S.sub);
    root.innerHTML = '<div class="ch">' + tabsHtml() + (S.sub === 'overview' ? overviewHtml() : channelHtml(S.sub, i)) + '</div>';
  }

  function show(head, rest) {
    var root = $('#v-channels'); if (!root) return Promise.resolve();
    if (!gate()) {
      if (!known) root.innerHTML = '<div class="empty">確認登入身分中…</div>';
      return Promise.resolve();
    }
    bind(root);
    var want = (rest && rest[0]) || 'overview';
    return (S.ids && S.ids.every(function (id) { return S.data[id]; }) ? Promise.resolve() : load()).then(function () {
      S.sub = want === 'overview' || S.ids.indexOf(want) >= 0 ? want : 'overview';
      paint();
    });
  }

  window.TwChannels = { show: show, state: function () { return S; } };
})();
