/* ============================================================================
   頻道規劃（#channels → #channels/ch1|ch2|ch3[/<分頁>]）—— 2026-11-04 建，只給管理者
   Andy 11-04：「幫我在我那網頁新增頻道規劃 母分頁 方便我管理 觀看，裡面要有主題方向 規劃 短中長期 目標
   如何經營 發文方式 IG Thread 如何分配 等等」。
   這一頁回答的問題：「三個社群頻道各自要發什麼、什麼時候發、這週我要花多少時間、哪裡還有缺口？」
   怎麼用：先看三張頻道卡挑要管的；週曆看哪天撞時段（紅框）；點週曆裡的小標或頻道卡進子頁，子頁分頁籤看細節。
   資料：site/channels/plan.json（唯讀，由頻道規劃同事產出；欄位缺了就顯示「待補」，不會壞版）。
   ⚠ 所有文字一律 esc() 輸出，不收 HTML。
   管理者閘門沿用 flowcheck.js 同一條（TwAccount.user() 的 admin／owner；預覽版全開；本機 TW_LAB_OVERRIDE）。
   ============================================================================ */
(function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var esc = function (s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); };
  var arr = function (x) { return Array.isArray(x) ? x : []; };
  var DAYS = ['週一', '週二', '週三', '週四', '週五', '週六', '週日'];
  var TABS = [['topics', '主題方向'], ['plan', '規劃與時程'], ['goals', '短中長期目標'], ['run', '如何經營'], ['post', '發文方式'], ['team', '團隊與法遵'], ['kpi', 'KPI'], ['docs', '文件']];
  var GH = 'https://github.com/MiaoZiKe/tw-rotation/blob/main/';
  var S = { data: null, fail: false, loading: null, ch: '', tab: 'topics', gapOpen: false };

  /* ---------------------------------------------------------------- 只給管理者（做法同 flowcheck.js） */
  var known = false;
  function isAdm() {
    try {
      if (window.TW_PREVIEW) return true;
      var h = location.hostname;
      if ((h === '127.0.0.1' || h === 'localhost') && (window.TW_LAB_OVERRIDE === true || window.TW_LAB_OVERRIDE === false)) return window.TW_LAB_OVERRIDE;
      var A = window.TwAccount, u = null;
      if (A && typeof A.user === 'function') u = A.user();
      else if (localStorage.getItem('tw.acct.tok')) u = JSON.parse(localStorage.getItem('tw.acct.user') || 'null');
      return !!(u && (u.admin === true || u.owner === true));
    } catch (e) { return false; }
  }
  var inCh = function () { return /^#channels(\/|$)/.test(location.hash || ''); };
  function gate() {
    var on = isAdm();
    document.documentElement.classList.toggle('ch-adm', on);
    if (!on && known && inCh()) location.replace('#overview');
    return on;
  }
  gate();
  window.addEventListener('tw:account', function () { known = true; if (gate() && inCh()) window.dispatchEvent(new HashChangeEvent('hashchange')); });
  setTimeout(function () { if (!known) { known = true; gate(); } }, 6000);
  window.addEventListener('hashchange', gate);

  /* ---------------------------------------------------------------- 資料 */
  function load() {
    if (S.data || S.fail) return Promise.resolve();
    if (S.loading) return S.loading;
    S.loading = fetch('channels/plan.json', { cache: 'no-cache' }).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (j) { S.data = j; }).catch(function () { S.fail = true; });
    return S.loading;
  }
  var chans = function () { return arr(S.data && S.data.channels); };
  var byId = function (id) { return chans().filter(function (c) { return c.id === id; })[0] || null; };
  var cls = function (c) { var n = parseInt(String((c && c.id) || '').replace(/\D/g, ''), 10) || 1; return 'c' + ((n - 1) % 3); };            // 三頻道三色（CSS 的 c0 c1 c2）
  var short = function (c) { return String(typeof c === 'string' ? c : c.name || '').replace(/[（(].*$/, '').slice(0, 7); };
  var weekly = function (c) { return arr(c.posting && c.posting.weekly); };
  var minsOf = function (c) { return weekly(c).reduce(function (s, w) { return s + (+w.andy_min || 0); }, 0); };

  /* ---------------------------------------------------------------- 小零件 */
  function howHtml() {
    return '<span class="chn-how"><button class="howbtn chn-q" type="button" aria-label="這一頁怎麼用" aria-expanded="false">?</button>' +
      '<div class="chn-pop" hidden><b>怎麼用</b><br>三張卡是三個社群頻道的現況；週曆把三個頻道每週要發的貼文放在同一張表，同一天同一時段有兩個頻道會標紅框（撞時段），要錯開就去改排程。' +
      '點週曆小標或頻道卡進子頁：分頁籤依序是主題比重、時程、短中長期目標、經營方式、發文方式（IG 與 Threads 怎麼分配）、團隊與法遵、KPI、文件連結。' +
      '「你要做的事」是目前等你決定或動手的項目；缺漏清單收在最下面，點開看。</div></span>';
  }
  function bindHow(root) {
    var b = $('.chn-q', root), p = $('.chn-pop', root); if (!b || !p) return;
    b.onclick = function (e) { e.stopPropagation(); p.hidden = !p.hidden; b.setAttribute('aria-expanded', String(!p.hidden)); };
    if (!bindHow.doc) {
      bindHow.doc = true;
      document.addEventListener('click', function (e) { var q = $('#v-channels .chn-pop'); if (q && !q.hidden && !q.contains(e.target)) { q.hidden = true; var bb = $('#v-channels .chn-q'); if (bb) bb.setAttribute('aria-expanded', 'false'); } });
    }
  }
  var badge = function (t) {
    var k = /未啟用|暫停/.test(t) ? 'wait' : /運作|上線|經營中/.test(t) ? 'ok' : 'plan';
    return '<span class="chn-st ' + k + '">' + esc(t || '待補') + '</span>';
  };
  var mode = function (m) { var k = m === '自動' ? 'auto' : m === '半自動' ? 'semi' : 'man'; return '<span class="chn-mode ' + k + '">' + esc(m || '—') + '</span>'; };
  var txt = function (x) { return Array.isArray(x) ? x.join('、') : String(x == null ? '' : x); };
  var dayOf = function (d) { var m = /^週[一二三四五六日]/.exec(String(d || '')); return m ? m[0] : ''; };
  var minOf = function (t) { var m = /^(\d{1,2}):(\d{2})/.exec(String(t || '')); return m ? +m[1] * 60 + +m[2] : null; };
  var list = function (a, empty) { a = arr(a); return a.length ? '<ul class="chn-ul">' + a.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul>' : '<div class="chn-none">' + esc(empty || '待補') + '</div>'; };
  var sect = function (t, body, extra) { return '<section class="chn-sec' + (extra ? ' ' + extra : '') + '"><h4>' + esc(t) + '</h4>' + body + '</section>'; };

  /* ---------------------------------------------------------------- 總覽 */
  function cardHtml(c) {
    var w = weekly(c).length, td = arr(c.andy_todo).length;
    return '<a class="chn-card ' + cls(c) + '" href="#channels/' + esc(c.id) + '" data-ch="' + esc(c.id) + '">' +
      '<div class="chn-ch"><b class="chn-no">' + esc(c.no) + '</b><span class="chn-nm">' + esc(c.name) + '</span>' + badge(c.status) + '</div>' +
      '<p class="chn-pos">' + esc(c.positioning || '待補') + '</p>' +
      '<div class="chn-kv"><span><em>' + w + '</em>本週發文</span><span class="' + (td ? 'warn' : '') + '"><em>' + td + '</em>待 Andy</span></div></a>';
  }
  /* 週曆：列＝出現過的時段、欄＝週一～週日；同格兩個以上頻道＝撞時段（.clash） */
  function calHtml() {
    var cells = {}, times = {}, flex = [], all = [];
    chans().forEach(function (c) {
      weekly(c).forEach(function (w) {
        var d = dayOf(w.day), tm = String(w.time || '');
        if (!d || minOf(tm) == null) { flex.push({ c: c, w: w }); return; }
        times[tm] = 1; var k = tm + '|' + DAYS.indexOf(d); (cells[k] = cells[k] || []).push({ c: c, w: w });
        all.push({ c: c, d: d, m: minOf(tm), k: k });
      });
    });
    /* 撞時段：同一天、不同頻道、相隔 60 分鐘內（回覆窗重疊）；同格＝完全同時。 */
    var bad = {};
    all.forEach(function (x) { all.forEach(function (y) { if (x.c.id !== y.c.id && x.d === y.d && Math.abs(x.m - y.m) <= 60) bad[x.k] = (bad[x.k] || '') + (x.m === y.m ? '同時段' : '相隔 ' + Math.abs(x.m - y.m) + ' 分') + '・' + y.c.name + '；'; }); });
    var ts = Object.keys(times).sort();
    if (!ts.length) return '<div class="chn-none">還沒有排程資料</div>';
    var h = '<div class="chn-cal" role="table" aria-label="三頻道每週發文週曆"><div class="chn-cr hd" role="row"><span class="tm"></span>' + DAYS.map(function (d) { return '<span role="columnheader">' + d.replace('週', '') + '</span>'; }).join('') + '</div>';
    ts.forEach(function (tm) {
      h += '<div class="chn-cr" role="row"><span class="tm">' + esc(tm) + '</span>';
      DAYS.forEach(function (d, di) {
        var k = tm + '|' + di, cs = cells[k] || [], clash = !!bad[k];
        h += '<span class="cell' + (clash ? ' clash' : '') + (cs.length ? ' has' : '') + '" role="cell" data-day="' + esc(d) + '" data-tm="' + esc(tm) + '"' + (clash ? ' title="撞時段（回覆窗重疊）：' + esc(bad[k]) + '"' : '') + '>' +
          cs.map(function (x) { return '<a class="chn-chip ' + cls(x.c) + '" href="#channels/' + esc(x.c.id) + '/post" title="' + esc(x.c.name + '・' + x.w.day + '・' + (x.w.platform || '') + '・' + (x.w.type || '')) + '"><b>' + esc(x.c.no) + '</b><span class="t">' + esc(short(x.w.type || '')) + '</span></a>'; }).join('') + '</span>';
      });
      h += '</div>';
    });
    h += '</div>';
    if (flex.length) h += '<div class="chn-flex"><em>機動（不限時段）</em>' + flex.map(function (x) { return '<a class="chn-chip ' + cls(x.c) + '" href="#channels/' + esc(x.c.id) + '/post" title="' + esc(x.c.name + '・' + x.w.day + '・' + (x.w.type || '')) + '"><b>' + esc(x.c.no) + '</b><span class="t">' + esc(x.w.platform || '') + '</span></a>'; }).join('') + '</div>';
    return h;
  }
  function hoursHtml() {
    var cs = chans(), tot = cs.reduce(function (s, c) { return s + minsOf(c); }, 0), mx = Math.max.apply(null, cs.map(minsOf).concat([1]));
    var est = S.data && S.data.cross && S.data.cross.andy_week_hours;
    return '<div class="chn-hours">' + cs.map(function (c) {
      var m = minsOf(c);
      return '<div class="chn-hr"><span class="n ' + cls(c) + '">' + esc(c.no) + ' ' + esc(short(c)) + '</span><i class="bar"><u class="' + cls(c) + '" style="width:' + Math.round(m / mx * 100) + '%"></u></i><b>' + m + ' 分</b></div>';
    }).join('') + '</div><div class="chn-note">排程加總每週 <b>' + tot + ' 分</b>（約 ' + (tot / 60).toFixed(1) + ' 小時）' + '。</div>' + (est ? '<details class="chn-fold"><summary>規劃對 Andy 時數的估算</summary><p>' + esc(est) + '</p></details>' : '');
  }
  function gapsHtml() {
    var g = arr(S.data && S.data.gaps);
    if (!g.length) return '';
    return '<details class="chn-gaps" id="chnGaps"' + (S.gapOpen ? ' open' : '') + '><summary>缺漏清單<small>（' + g.length + ' 項）</small></summary>' +
      '<div class="chn-gtab">' + g.map(function (x) {
        return '<div class="chn-gr"><b>' + esc(byId(x.channel) ? byId(x.channel).no + ' ' + short(byId(x.channel)) : x.channel) + '</b><span>' + esc(x.item) + '</span><em>原本：' + esc(x.was || '—') + '</em><em class="fx">處理：' + esc(x.fixed || '待補') + '</em></div>';
      }).join('') + '</div></details>';
  }
  function overviewHtml() {
    var cross = (S.data && S.data.cross) || {};
    return '<div class="chn-cards">' + chans().map(cardHtml).join('') + '</div>' +
      '<div class="chn-two"><section class="chn-sec"><h4>三頻道週曆<small>紅框＝同天兩頻道相隔 60 分內，回覆窗重疊</small></h4>' + calHtml() + '</section>' +
      '<section class="chn-sec"><h4>Andy 每週要花的時間</h4>' + hoursHtml() +
      (cross.relations ? '<details class="chn-fold"><summary>三頻道關係</summary><p>' + esc(cross.relations) + '</p></details>' : '') +
      (arr(cross.shared_rules).length ? '<details class="chn-fold"><summary>共同規則（' + arr(cross.shared_rules).length + ' 條）</summary>' + list(cross.shared_rules) + '</details>' : '') + '</section></div>' + gapsHtml();
  }

  /* ---------------------------------------------------------------- 子頁各分頁 */
  function topicsHtml(c) {
    var t = arr(c.topics), tot = t.reduce(function (s, x) { return s + (+x.share || 0); }, 0) || 1;
    if (!t.length) return '<div class="chn-none">主題方向待補</div>';
    return '<div class="chn-topics"><div class="chn-dn" id="chnDn"><div class="chn-dnc" role="img" aria-label="內容主題比重"></div></div><ul class="chn-tl">' + t.map(function (x, i) {
      return '<li data-k="' + esc(x.name) + '"><div class="h"><i class="sw" data-i="' + i + '"></i><b>' + esc(x.name) + '</b><span class="pc">' + Math.round((+x.share || 0) / tot * 100) + '%</span></div><p>' + esc(x.desc || '') + '</p>' +
        (arr(x.examples).length ? '<div class="ex">例：' + esc(arr(x.examples).join('、')) + '</div>' : '') + '</li>';
    }).join('') + '</ul></div>';
  }
  function mountDonut(c) {
    var A = window.App, D = A && A.donut, box = $('#chnDn'), el = box && $('.chn-dnc', box); if (!el || !D || !el.clientWidth) return;
    var t = arr(c.topics), tot = t.reduce(function (s, x) { return s + (+x.share || 0); }, 0) || 1;
    var parts = t.map(function (x) { return { name: x.name, value: +x.share || 0 }; });
    $$('.sw', $('.chn-tl')).forEach(function (s) { s.style.background = D.color(+s.dataset.i); });
    var SZ = Math.round(el.clientWidth) || 160;
    var item = function (p, i, hi) { return D.item({ name: p.name, value: p.value }, i, hi); };
    A.chart(el, { tooltip: Object.assign({}, A.tip, { confine: false, position: D.tipPos, trigger: 'item', formatter: function (q) { return '<b>' + esc(q.name) + '</b><br>' + (+q.percent).toFixed(0) + '%'; } }),
      title: D.center('內容比重', t.length + ' 柱', SZ), animationDurationUpdate: D.MS, series: D.series({ cursor: 'default', data: parts.map(function (p, i) { return item(p, i, false); }) }) }, { notMerge: true });
    var inst = window.echarts.getInstanceByDom(el); if (!inst) return;
    var cur = null;
    var hi = function (nm) {
      if (inst.isDisposed() || cur === nm) return; cur = nm;
      var h = nm ? parts.filter(function (p) { return p.name === nm; })[0] : null;
      try { inst.setOption({ title: D.center(h ? h.name : '內容比重', h ? Math.round(h.value / tot * 100) + '%' : t.length + ' 柱', SZ), series: [{ data: parts.map(function (p, i) { return item(p, i, !!h && p.name === nm); }) }] }); } catch (e) { /* 已 dispose */ }
      $$('.chn-tl li', box.parentNode).forEach(function (li) { li.classList.toggle('hl', !!h && li.dataset.k === nm); });
    };
    inst.off('mouseover'); inst.off('globalout');
    inst.on('mouseover', function (q) { if (q.seriesIndex === 0) hi(q.name); }); inst.on('globalout', function () { hi(null); });
    $$('.chn-tl li', box.parentNode).forEach(function (li) { li.onmouseenter = function () { hi(li.dataset.k); }; li.onmouseleave = function () { hi(null); }; });
  }
  function planHtml(c) {
    var acc = c.account || {}, tl = arr(c.timeline), tk = function (st) { return st === 'done' ? 'done' : /🛠|進行/.test(st) ? 'doing' : /Andy|待確認/.test(st) ? 'ask' : 'todo'; };
    return '<div class="chn-info"><span><em>定位</em>' + esc(c.positioning || '待補') + '</span><span><em>受眾</em>' + esc(c.audience || '待補') + '</span><span><em>IG</em>' + esc(acc.ig || '待補') + '</span><span><em>Threads</em>' + esc(acc.threads || '待補') + '</span></div>' +
      '<div class="chn-two">' + sect('時程', tl.length ? '<ol class="chn-tline">' + tl.map(function (x) {
        return '<li class="' + tk(String(x.state || '')) + '"><b class="w">' + esc(x.when) + '</b><span class="what">' + esc(x.what) + '</span><em>' + esc(x.who || '') + '</em><u>' + esc(x.state || '待補') + '</u></li>';
      }).join('') + '</ol>' : '<div class="chn-none">時程待補</div>') +
      sect('你要做的事（Andy）', list(c.andy_todo, '目前沒有等你的事'), 'todo') + '</div>';
  }
  function goalsHtml(c) {
    var g = c.goals || {};
    return '<div class="chn-three">' + [['short', '短期'], ['mid', '中期'], ['long', '長期']].map(function (p) {
      var x = g[p[0]] || {};
      return sect(p[1] + (x.period ? '・' + x.period : ''), list(x.items, '待補'), 'g-' + p[0]);
    }).join('') + '</div>';
  }
  function runHtml(c) {
    var lad = arr(c.trust_ladder);
    return sect('信任階梯：過了關才解鎖下一階', lad.length ? '<div class="chn-ladder">' + lad.map(function (s, i) {
      return '<div class="chn-step" style="--i:' + i + '"><div class="s">' + esc(s.stage) + '</div><div class="gt"><em>過關條件</em>' + esc(s.gate || '待補') + '</div>' +
        '<div class="cc"><span class="can"><em>可以</em>' + esc(txt(s.can) || '—') + '</span><span class="cannot"><em>不可以</em>' + esc(txt(s.cannot) || '—') + '</span></div></div>';
    }).join('') + '</div>' : '<div class="chn-none">信任階梯待補</div>') +
      sect('經營要點', list(c.operation, '待補')) +
      sect('視覺', '<div class="chn-vis">LOGO：' + esc((c.visual && c.visual.logo) || '待補') + '　版型：' + esc((c.visual && c.visual.layout) || '待補') + '</div>');
  }
  function postHtml(c) {
    var w = weekly(c), ps = c.platform_split || {}, rules = arr(c.posting && c.posting.rules);
    var mins = minsOf(c);
    var tb = w.length ? '<div class="chn-tbw"><table class="chn-tb" id="chnPostTb"><thead><tr><th>星期</th><th>時間</th><th>平台</th><th>類型</th><th>方式</th><th>你花</th></tr></thead><tbody>' + w.map(function (x) {
      return '<tr><td>' + esc(x.day) + '</td><td class="mono">' + esc(x.time) + '</td><td>' + esc(x.platform) + '</td><td>' + esc(x.type) + '</td><td>' + mode(x.mode) + '</td><td class="mono">' + (+x.andy_min || 0) + ' 分</td></tr>';
    }).join('') + '</tbody></table></div><div class="chn-note">每週共 <b>' + w.length + '</b> 則，需要你動手 <b>' + mins + ' 分</b>。</div>' : '<div class="chn-none">排程待補</div>';
    var sp = [['threads', 'Threads'], ['ig', 'IG 貼文'], ['ig_story', 'IG 限動'], ['reels', 'Reels']];
    return '<div class="chn-two">' + sect('每週排程', tb) +
      sect('IG 與 Threads 怎麼分配', '<div class="chn-split">' + sp.map(function (p) { return '<div><em>' + p[1] + '</em>' + esc(ps[p[0]] || '待補') + '</div>'; }).join('') + '</div>' +
        (ps.reason ? '<div class="chn-note"><b>為什麼這樣分：</b>' + esc(ps.reason) + '</div>' : '') + '<h5>發文規則</h5>' + list(rules, '待補')) + '</div>';
  }
  function teamHtml(c) {
    var t = arr(c.team);
    return '<div class="chn-two">' + sect('團隊（誰做什麼）', t.length ? '<div class="chn-tbw"><table class="chn-tb"><thead><tr><th>角色</th><th>負責</th><th>做什麼</th></tr></thead><tbody>' + t.map(function (x) {
      return '<tr><td>' + esc(x.role) + '</td><td class="mono">' + esc(x.agent) + '</td><td>' + esc(x.does) + '</td></tr>';
    }).join('') + '</tbody></table></div>' : '<div class="chn-none">待補</div>') + sect('法遵紅線', list(c.compliance, '待補')) + '</div>';
  }
  function kpiHtml(c) {
    var k = arr(c.kpi);
    return sect('KPI（起點 → 第 4 週 → 第 8 週）', k.length ? '<div class="chn-tbw"><table class="chn-tb" id="chnKpiTb"><thead><tr><th>指標</th><th>起點</th><th>第 4 週</th><th>第 8 週</th></tr></thead><tbody>' + k.map(function (x) {
      return '<tr><td>' + esc(x.name) + '</td><td class="mono">' + esc(x.base) + '</td><td class="mono">' + esc(x.w4) + '</td><td class="mono">' + esc(x.w8) + '</td></tr>';
    }).join('') + '</tbody></table></div>' : '<div class="chn-none">KPI 待補</div>');
  }
  function docsHtml(c) {
    var d = arr(c.docs);
    return sect('相關文件（開 GitHub）', d.length ? '<ul class="chn-docs">' + d.map(function (x) {
      return '<li><a href="' + esc(GH + String(x.path || '').replace(/^\/+/, '')) + '" target="_blank" rel="noopener">' + esc(x.title) + '</a><em>' + esc(x.path) + '</em></li>';
    }).join('') + '</ul>' : '<div class="chn-none">待補</div>');
  }
  var BODY = { topics: topicsHtml, plan: planHtml, goals: goalsHtml, run: runHtml, post: postHtml, team: teamHtml, kpi: kpiHtml, docs: docsHtml };

  function subHtml(c) {
    var tabs = '<div class="nbsw chn-tabs" role="tablist" aria-label="頻道分頁">' + TABS.map(function (t) {
      return '<a href="#channels/' + esc(c.id) + '/' + t[0] + '" role="tab" data-tab="' + t[0] + '" class="' + (S.tab === t[0] ? 'on' : '') + '">' + t[1] + '</a>';
    }).join('') + '</div>';
    return '<div class="chn-subhd ' + cls(c) + '"><a class="chn-back" href="#channels">← 總覽</a><b class="chn-no">' + esc(c.no) + '</b><span class="chn-nm">' + esc(c.name) + '</span>' + badge(c.status) +
      '<span class="chn-sw">' + chans().filter(function (x) { return x.id !== c.id; }).map(function (x) { return '<a class="' + cls(x) + '" href="#channels/' + esc(x.id) + '/' + S.tab + '" title="切到' + esc(x.name) + '">' + esc(x.no) + '</a>'; }).join('') + '</span></div>' +
      tabs + '<div class="chn-body" id="chnBody" data-tab="' + S.tab + '">' + BODY[S.tab](c) + '</div>';
  }

  /* ---------------------------------------------------------------- 路由 */
  function paint() {
    var root = $('#v-channels'); if (!root) return;
    var c = S.ch ? byId(S.ch) : null;
    var upd = S.data && S.data.updated ? '<span class="chn-upd">更新 ' + esc(S.data.updated) + '</span>' : '';
    var h = '<div class="card chn-card0"><div class="row spread chn-hd"><h3>' + howHtml() + '</h3>' + upd + '</div>';
    if (S.fail || !S.data) h += '<div class="empty isempty">頻道規劃資料還沒有（site/channels/plan.json）</div>';
    else if (S.ch && !c) h += '<div class="empty isempty">找不到這個頻道</div><a class="chn-back" href="#channels">← 回總覽</a>';
    else h += c ? subHtml(c) : overviewHtml();
    root.innerHTML = h + '</div>';
    bindHow(root);
    var gp = $('#chnGaps'); if (gp) gp.addEventListener('toggle', function () { S.gapOpen = gp.open; });
    if (c && S.tab === 'topics') requestAnimationFrame(function () { mountDonut(c); });
  }
  async function show(head, rest) {
    var root = $('#v-channels'); if (!root) return;
    if (!gate()) { if (!known) root.innerHTML = '<div class="empty">確認登入身分中…</div>'; return; }
    rest = rest || [];
    S.ch = /^ch\d+$/.test(rest[0] || '') ? rest[0] : '';
    var tid = TABS.map(function (t) { return t[0]; });
    S.tab = tid.indexOf(rest[1]) >= 0 ? rest[1] : 'topics';
    if (!S.data && !S.fail) root.innerHTML = '<div class="empty">載入中…</div>';
    await load();
    paint();
  }
  window.TwChannels = { show: show, state: function () { return S; } };
})();
