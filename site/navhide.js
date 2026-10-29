/* ============================================================================
   側欄「隱藏分頁」小眼睛（site/navhide.js，2026-10-29）
   ----------------------------------------------------------------------------
   Andy：「交易練習室先隱藏，並且分頁都需要新增眼睛圖案方便我隱藏」「跟精選文章那個一樣，小小的圖示即可」。
   做法完全沿用精選文章分頁的眼睛（articles.js）：
     · 設定存在伺服器（會員 Worker /v1/nav/hidden 公開讀、/v1/nav/hidden/put 管理者寫，kv 鍵 nav_hidden），對所有人生效。
       ★ 伺服器從來沒存過時回預設 ['lab']（交易練習室預設隱藏）；上次讀到的結果另存 localStorage（tw.nav.hid）只拿來「第一眼就不出現」。
     · 鍵：大項＝路由名（lab、market…）、子項＝側欄子項鍵（mkt-updown、xp-fund…）、整組＝'g:'＋組代號（g:hist）。
       隱藏整組＝組標題與組內所有大項、子項一起藏。
     · 一般人與會員：被隱藏的項目整個不出現（電腦版側欄、手機抽屜都是），直接打該路由網址導回 #overview。
     · 管理者：項目照舊在（半透明＋劃掉），右側多一顆眼睛；斜線眼睛＝目前對外隱藏，再點一次恢復。
     · 預覽版（TW_PREVIEW）會員 API 寫入被擋，眼睛只改這個瀏覽器（tw.nav.hid.pv），不動正式站。
   ⚠ 交易練習室、科技透明圈本來就另有「只限管理者」的閘（lab.js／tc.js 掛 .lab-adm／.tc-adm）：
     眼睛管的是「一般人看不看得到入口」，不會把那兩頁的管理者閘拿掉 —— 取消隱藏後它們對一般人仍是不開放（要開放是另一個決定）。
   ============================================================================ */
(function () {
  'use strict';
  var root = document.documentElement;
  var $ = function (s, el) { return (el || document).querySelector(s); };
  var $$ = function (s, el) { return Array.prototype.slice.call((el || document).querySelectorAll(s)); };
  var DEF = ['lab'];                                   // 與 Worker 的 NAV_DEF 一致
  var KEY = window.TW_PREVIEW ? 'tw.nav.hid.pv' : 'tw.nav.hid';
  var KEY_RE = /^[a-z0-9][a-z0-9:_-]{1,29}$/;
  var ALIAS = { themes: 'heatmap', tasks: 'delivery' };
  var EYE_ON = '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>';
  var EYE_OFF = '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M9.9 4.2A10 10 0 0 1 12 4c6.5 0 10 8 10 8a17 17 0 0 1-3.2 4.4"/><path d="M6.6 6.6A17 17 0 0 0 2 12s3.5 8 10 8a9.7 9.7 0 0 0 5.4-1.6"/><path d="M14.1 14.1a3 3 0 1 1-4.2-4.2"/><path d="m2 2 20 20"/></svg>';

  var hid = null, loadedAt = 0, loadP = null;
  function cacheRead() {
    try { var raw = localStorage.getItem(KEY); if (raw == null) return DEF.slice(); var a = JSON.parse(raw); return Array.isArray(a) ? a.filter(function (k) { return typeof k === 'string' && KEY_RE.test(k); }) : DEF.slice(); }
    catch (e) { return DEF.slice(); }
  }
  function cacheSave() { try { localStorage.setItem(KEY, JSON.stringify(Array.from(hid))); } catch (e) { /* 私密視窗：只留記憶體 */ } }
  function H() { return hid || (hid = new Set(cacheRead())); }
  function isAdm() {
    if (window.TW_PREVIEW) return true;
    try { var u = window.TwAccount && window.TwAccount.user && window.TwAccount.user(); return !!(u && u.admin); } catch (e) { return false; }
  }
  var N = function () { return window.TwL4Nav || { GROUPS: [], SUBS_DESK: {}, PAGES: {} }; };
  function groupOf(v) { var g = N().GROUPS.filter(function (G) { return G.views.indexOf(v) >= 0; })[0]; return g ? g.g : ''; }
  function gOff(g) { return !!g && H().has('g:' + g); }
  function viewOff(v) { return H().has(v) || gOff(groupOf(v)); }
  function subOff(k, parent) { return H().has(k) || viewOff(parent); }
  function titleOf(kind, id) {
    var n = N();
    if (kind === 'g') { var G = n.GROUPS.filter(function (x) { return x.g === id; })[0]; return G ? G.t : id; }
    if (kind === 'v') return (n.PAGES[id] && n.PAGES[id].t) || id;
    var out = id; Object.keys(n.SUBS_DESK).forEach(function (v) { n.SUBS_DESK[v].forEach(function (it) { if (it.k === id) out = it.t; }); });
    return out;
  }
  /* 一般人看得到嗎？（給 mobile4 抽屜用：true＝這個人不該看到，抽屜整列不要畫） */
  function off(kind, id) {
    if (isAdm()) return false;
    if (kind === 'g') return gOff(id);
    return kind === 'v' ? viewOff(id) : H().has(id);
  }

  /* ---------------- 樣式（自帶，不動 layout4.css／m4 檔） ---------------- */
  function css() {
    if ($('#navhideCss')) return;
    var s = document.createElement('style'); s.id = 'navhideCss';
    s.textContent =
      '.nav-off{display:none!important}' +
      '.naveye{display:inline-flex;align-items:center;justify-content:center;flex:none;width:22px;height:22px;border-radius:999px;color:var(--ink-2);cursor:pointer;opacity:.6;line-height:0}' +
      '.naveye:hover,.naveye:focus-visible{opacity:1;background:color-mix(in srgb,var(--cyan) 22%,transparent);color:var(--ink)}' +
      '.naveye.off{opacity:.95;color:var(--ink-3)}' +
      '.naveye svg{width:15px;height:15px}' +
      '.naveye.err{outline:1px solid var(--down,#e5484d)}' +
      /* 電腦版側欄：大項（.tab 本身是 flex，眼睛排在文字後面；有子項的大項箭頭 .l4car 用 margin-left:auto，眼睛插在它前面） */
      ':root.l4 .tab>.naveye{margin:-4px 0 -4px auto}' +
      ':root.l4 .tab>.naveye+.l4car{margin-left:0}' +
      ':root.l4 .l4subtab>.naveye{margin:-4px -6px -4px auto}' +
      ':root.l4 .l4grp>.naveye{margin-left:auto;width:20px;height:20px}' +
      ':root.l4.l4-mini .naveye{display:none!important}' +
      /* 管理者看到的「對外隱藏」項目：半透明＋劃掉文字（眼睛本身不淡化，才點得到） */
      '.nav-hid{opacity:.55}' +
      '.nav-hid>.naveye{opacity:1}' +
      ':root.l4 .tab.nav-hid,:root.l4 .l4subtab.nav-hid,:root.l4 .l4grp.nav-hid{text-decoration:line-through}' +
      /* 手機抽屜（≤640）：眼睛排在列尾 */
      '@media (max-width:640px){.m4item>.naveye,.m4sub>.naveye{margin-left:auto;width:32px;height:32px}.m4gt{position:relative}.m4gt>.naveye{position:absolute;right:4px;top:50%;transform:translateY(-50%);width:32px;height:32px}.m4item.nav-hid>span:not(.naveye),.m4gt.nav-hid>span:not(.naveye){text-decoration:line-through}}';
    document.head.appendChild(s);
  }

  /* ---------------- 套到畫面 ---------------- */
  function eyeFor(el, kind, id) {
    var e = el.querySelector(':scope > .naveye');
    if (!e) {
      e = document.createElement('span'); e.className = 'naveye'; e.setAttribute('role', 'button'); e.tabIndex = 0;
      e.dataset.k = kind; e.dataset.id = id;
      var car = el.querySelector(':scope > .l4car');
      if (car) el.insertBefore(e, car); else el.appendChild(e);
    }
    return e;
  }
  function paintOne(el, kind, id, parent, adm) {
    var isOff = kind === 'g' ? gOff(id) : kind === 'v' ? viewOff(id) : subOff(id, parent);
    var own = H().has(kind === 'g' ? 'g:' + id : id);
    el.classList.toggle('nav-off', isOff && !adm);
    el.classList.toggle('nav-hid', isOff && adm);
    if (!adm) { var x = el.querySelector(':scope > .naveye'); if (x) x.remove(); return isOff; }
    var e = eyeFor(el, kind, id), nm = titleOf(kind, id);
    e.classList.toggle('off', own);
    e.innerHTML = own ? EYE_OFF : EYE_ON;
    e.setAttribute('aria-pressed', own ? 'true' : 'false');
    e.title = own ? '「' + nm + '」目前對外隱藏（一般訪客與會員看不到），點一下恢復顯示'
      : (isOff ? '「' + nm + '」因為上層被隱藏而對外不顯示；點一下連它自己也標成隱藏'
        : '「' + nm + '」目前對外顯示，點一下隱藏（一般訪客與會員將看不到）');
    e.setAttribute('aria-label', e.title);
    return isOff;
  }
  function apply() {
    var adm = isAdm();
    var tabs = $('#tabs');
    if (tabs) {
      $$('.tab[data-view]', tabs).forEach(function (t) {
        var v = t.dataset.view; if (v === 'delivery') return;
        paintOne(t, 'v', v, '', adm);
      });
      $$('.l4subtab[data-l4sub]', tabs).forEach(function (t) { paintOne(t, 's', t.dataset.l4sub, t.dataset.parent, adm); });
      $$('.l4grp[data-g]', tabs).forEach(function (t) { paintOne(t, 'g', t.dataset.g, '', adm); });
      /* 一般人：整組的大項都被隱藏 → 組標題也不要留一個空組 */
      if (!adm) N().GROUPS.forEach(function (G) {
        var gt = $('.l4grp[data-g="' + G.g + '"]', tabs); if (!gt) return;
        var vis = G.views.some(function (v) { var t = $('.tab[data-view="' + v + '"]', tabs); return t && !viewOff(v) && getComputedStyle(t).display !== 'none' || (v === 'admin' && $('#l4Perm')); });
        gt.classList.toggle('nav-off', !vis || gOff(G.g));
      });
    }
    decorateDrawer(adm);
    guard();
  }
  function decorateDrawer(adm) {
    if (adm === undefined) adm = isAdm();
    $$('.m4item[data-v]').forEach(function (b) {
      var v = b.dataset.v; if (v === 'admin' || v === 'delivery') return;
      paintOne(b, 'v', v, '', adm);
    });
    $$('.m4grp[data-g] > .m4gt').forEach(function (t) { paintOne(t, 'g', t.parentNode.dataset.g, '', adm); });
  }

  /* ---------------- 路由守門：一般人打到被隱藏的頁 → 導回總覽 ---------------- */
  function guard() {
    if (isAdm()) return false;
    var parts = location.hash.replace(/^#\/?/, '').split('/'); var v = ALIAS[parts[0]] || parts[0];
    if (!v || v === 'overview') return false;
    var go = null;
    if (viewOff(v)) go = '#overview';
    else if (parts[1]) {
      var subs = N().SUBS_DESK[v] || [];
      var it = subs.filter(function (x) { return x.h === '#' + parts[0] + '/' + parts[1]; })[0];
      if (it && H().has(it.k)) {
        var alt = subs.filter(function (x) { return !H().has(x.k); })[0];
        go = alt ? alt.h : '#overview';
      }
    }
    if (!go) return false;
    location.replace(go);
    return true;
  }

  /* ---------------- 讀寫伺服器 ---------------- */
  var call = function (path, body) { var A = window.TwAccount; return A && typeof A.call === 'function' ? A.call(path, body) : Promise.resolve(null); };
  function load(force) {
    if (window.TW_PREVIEW) { hid = new Set(cacheRead()); return Promise.resolve(hid); }
    if (loadP && !force) return loadP;
    if (!force && Date.now() - loadedAt < 60000) return Promise.resolve(H());
    loadP = call('/v1/nav/hidden', {}).then(function (j) {
      if (j && j._s === 200 && Array.isArray(j.hidden)) { hid = new Set(j.hidden.filter(function (k) { return KEY_RE.test(k); })); cacheSave(); loadedAt = Date.now(); }
      return H();
    }).catch(function () { return H(); }).then(function (r) { loadP = null; return r; });
    return loadP;
  }
  function toggle(kind, id) {
    if (!isAdm()) return;
    var key = kind === 'g' ? 'g:' + id : id;
    var was = new Set(H()), next = new Set(was);
    if (next.has(key)) next.delete(key); else next.add(key);
    hid = next; cacheSave(); apply(); window.dispatchEvent(new Event('tw:navhide'));   // 先改畫面（點了馬上有感），伺服器回失敗再還原
    if (window.TW_PREVIEW) return;
    call('/v1/nav/hidden/put', { hidden: Array.from(next) }).then(function (r) {
      if (r && r._s === 200 && Array.isArray(r.hidden)) { hid = new Set(r.hidden); cacheSave(); loadedAt = Date.now(); apply(); window.dispatchEvent(new Event('tw:navhide')); return; }
      hid = was; cacheSave(); apply(); window.dispatchEvent(new Event('tw:navhide'));
      var e = $('.naveye[data-id="' + id + '"][data-k="' + kind + '"]');
      if (e) { e.classList.add('err'); e.title = '儲存失敗，請稍後再試'; setTimeout(function () { e.classList.remove('err'); apply(); }, 2500); }
    });
  }

  /* capture 掛在 document：比 layout4.js 掛在 #tabs 的 capture、app.js 掛在每顆 .tab 的 onclick 都先跑，
     點眼睛只切隱藏，不會順便換頁、也不會觸發「再點已選中的大項＝收展子項」。 */
  function hit(ev) {
    var e = ev.target.closest && ev.target.closest('.naveye'); if (!e) return;
    ev.stopPropagation(); ev.preventDefault(); toggle(e.dataset.k, e.dataset.id);
  }
  document.addEventListener('click', hit, true);
  document.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' || ev.key === ' ') hit(ev); }, true);
  /* 拖曳排序、分頁長按等 pointer 系統不要把眼睛當成分頁的一部分 */
  document.addEventListener('pointerdown', function (ev) { if (ev.target.closest && ev.target.closest('.naveye')) ev.stopPropagation(); }, true);

  /* ---------------- 啟動 ---------------- */
  function boot() {
    css(); apply();
    var tabs = $('#tabs');
    if (tabs && !tabs._nhObs) {
      tabs._nhObs = true;
      var t = 0;
      new MutationObserver(function () { clearTimeout(t); t = setTimeout(apply, 30); }).observe(tabs, { childList: true });   // layout4.js 之後才建 .l4grp／.l4subtab／管理區
    }
    /* 帳號資料回來前先別把「其實是管理者」的人導走：有登入記號就等 tw:account（最多 3 秒）再守門 */
    var cfg = window.TW_ACCOUNT_OVERRIDE || window.TW_ACCOUNT;
    var A = window.TwAccount, waitAcct = !!(cfg && cfg.api) && !(A && A.user && A.user());
    load().then(function () { apply(); });
    if (waitAcct) setTimeout(apply, 3000);
  }
  window.addEventListener('hashchange', function () { guard(); load().then(function () { guard(); }); });
  ['tw:account', 'tw:account-config'].forEach(function (ev) { window.addEventListener(ev, function () { load(true).then(apply); }); });
  window.TwNavHide = { off: off, apply: apply, decorate: decorateDrawer, hidden: function () { return Array.from(H()); }, isAdmin: isAdm };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
