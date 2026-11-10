/* ============================================================================
   側欄排序（site/navdrag.js，2026-11-10）
   ----------------------------------------------------------------------------
   Andy：「這邊改動就固定不變」「側邊也是具備拖曳功能，都只有我可以更改」。
   做法比照 navhide.js 的小眼睛：
     · 順序存在伺服器（會員 Worker /v1/nav/order 公開讀、/v1/nav/order/put 管理者寫，kv 鍵 nav_order），對所有人生效。
       localStorage（tw.nav.ord）只拿來「第一眼就是排好的順序」；只在伺服器回 200 後才當成已同步。
     · 形狀 {g:[組], v:{組:[大項]}, s:{大項:[子項]}, adm:[管理區子項]}；沒存過＝null＝預設順序（layout4.js 的 GROUPS／SUBS 原樣）。
     · 只有管理者能拖（滑鼠，電腦版側欄）；一般人與會員看到站主排好的順序、拖不動。手機抽屜讀同一份（mobile4.js 聽 tw:navorder 重畫），手機不能拖。
     · 拖曳範圍：組與組互換、組內大項互換、大項底下的子項互換、管理區子項互換。「不准拖到別的組底下」：
       大項屬於哪一組是路由結構（隱藏、收展、手機抽屜都靠它），跨組搬會讓這些全部對不上，所以只開同層互換。
     · 視覺順序靠 inline style.order（layout4.css 的 order 是寫死的，DOM 順序不是畫面順序），所以拖曳用「青色落點線＋放開才移動」，不即時換位。
     · 預覽版（TW_PREVIEW）只改這個瀏覽器（tw.nav.ord.pv），不動正式站。
     · 舊 Worker（沒有這個端點，回 404）：讀不到就維持預設順序；管理者拖了寫不上去，順序只留在他這個瀏覽器（標記「尚未同步」），
       等 Worker 更新後第一次載入自動補送，不跳錯、不登出。
   ============================================================================ */
(function () {
  'use strict';
  var root = document.documentElement;
  var $ = function (s, el) { return (el || document).querySelector(s); };
  var $$ = function (s, el) { return Array.prototype.slice.call((el || document).querySelectorAll(s)); };
  var PV = !!window.TW_PREVIEW, KEY = PV ? 'tw.nav.ord.pv' : 'tw.nav.ord';
  var KEY_RE = /^[a-z0-9][a-z0-9:_-]{1,29}$/;
  var N = function () { return window.TwL4Nav || null; };
  var order = null, uns = false, DEF = null, loadedAt = 0;

  function isAdm() {
    if (PV) return true;
    try { var u = window.TwAccount && window.TwAccount.user && window.TwAccount.user(); return !!(u && u.admin); } catch (e) { return false; }
  }
  function deskOn() { return root.classList.contains('l4') && !root.classList.contains('l4m'); }

  /* ---------- 快取（第一眼） ---------- */
  function clean(o) {
    if (!o || typeof o !== 'object' || Array.isArray(o)) return null;
    var arr = function (a) { return Array.isArray(a) ? a.filter(function (k) { return typeof k === 'string' && KEY_RE.test(k); }) : []; };
    var map = function (m) { var r = {}; if (m && typeof m === 'object') Object.keys(m).forEach(function (k) { if (KEY_RE.test(k)) r[k] = arr(m[k]); }); return r; };
    return { g: arr(o.g), v: map(o.v), s: map(o.s), adm: arr(o.adm) };
  }
  function cacheRead() {
    try { var j = JSON.parse(localStorage.getItem(KEY) || 'null'); if (j && j.o !== undefined) { order = clean(j.o); uns = !!j.u; } } catch (e) { /* 私密視窗 */ }
  }
  function cacheSave() { try { localStorage.setItem(KEY, JSON.stringify({ o: order, u: uns })); } catch (e) { /* 私密視窗：只留記憶體 */ } }

  /* ---------- 預設快照與排序 ---------- */
  function snap() {
    var n = N(); if (DEF || !n) return;
    DEF = { g: n.GROUPS.map(function (G) { return G.g; }), v: {}, s: {}, adm: n.admDefault ? n.admDefault() : [] };
    n.GROUPS.forEach(function (G) { DEF.v[G.g] = G.views.slice(); });
    Object.keys(n.SUBS_DESK).forEach(function (v) { DEF.s[v] = n.SUBS_DESK[v].map(function (i) { return i.k; }); });
  }
  function sortIn(arr, keyOf, ord, def) {
    var pos = function (k) { var i = (ord || []).indexOf(k); if (i >= 0) return i; var d = (def || []).indexOf(k); return 1000 + (d < 0 ? 999 : d); };
    arr.sort(function (a, b) { return pos(keyOf(a)) - pos(keyOf(b)); });
  }
  function admKeys() { var n = N(); return n && n.admSubs ? n.admSubs().map(function (x) { return x[0]; }) : []; }
  function curState() {
    var n = N(), o = { g: n.GROUPS.map(function (G) { return G.g; }), v: {}, s: {}, adm: admKeys() };
    n.GROUPS.forEach(function (G) { o.v[G.g] = G.views.slice(); });
    Object.keys(n.SUBS_DESK).forEach(function (v) { o.s[v] = n.SUBS_DESK[v].map(function (i) { return i.k; }); });
    return o;
  }
  function applyData() {
    var n = N(); if (!n) return; snap();
    var o = order || {};
    sortIn(n.GROUPS, function (G) { return G.g; }, o.g, DEF.g);
    n.GROUPS.forEach(function (G) { sortIn(G.views, function (v) { return v; }, (o.v || {})[G.g], DEF.v[G.g]); });
    Object.keys(n.SUBS_DESK).forEach(function (v) { sortIn(n.SUBS_DESK[v], function (i) { return i.k; }, (o.s || {})[v], DEF.s[v]); });
  }

  /* ---------- 套到畫面（inline order） ---------- */
  var managed = [];
  function viewEl(v) { var tabs = $('#tabs'); return v === 'admin' ? $('#l4Perm', tabs) : $('.tab[data-view="' + v + '"]', tabs); }
  function subEls(v) {
    var n = N(), tabs = $('#tabs');
    if (v === 'admin') { var ks = admKeys(); return $$('.l4subtab[data-parent="admin"]', tabs).sort(function (a, b) { return ks.indexOf(a.dataset.adm) - ks.indexOf(b.dataset.adm); }); }
    return (n.SUBS_DESK[v] || []).map(function (i) { return $('.l4subtab[data-l4sub="' + i.k + '"]', tabs); }).filter(Boolean);
  }
  function groupEls(G) {
    var out = [], b = $('.l4grp[data-g="' + G.g + '"]', $('#tabs'));
    if (b) out.push(b);
    G.views.forEach(function (v) { out = out.concat(viewBlock(v)); });
    return out;
  }
  function viewBlock(v) { var e = viewEl(v); return e ? [e].concat(subEls(v)) : []; }
  function paint() {
    var tabs = $('#tabs'), n = N(); if (!tabs || !n) return;
    var seq = [];
    if (deskOn()) n.GROUPS.forEach(function (G) { seq = seq.concat(groupEls(G)); });
    managed.forEach(function (e) { if (seq.indexOf(e) < 0) { e.style.order = ''; e.style.marginTop = ''; } });
    seq.forEach(function (e, i) { e.style.order = String(-1000 + i); e.style.marginTop = ''; });
    var firstG = seq.filter(function (e) { return e.classList.contains('l4grp'); })[0];
    if (firstG) firstG.style.marginTop = '0';   // 第一組不留上緣空白（預設只有「今日市場」是 0）
    managed = seq;
    root.classList.toggle('nd-adm', deskOn() && isAdm());
    bar();
  }
  function apply() { applyData(); paint(); window.dispatchEvent(new Event('tw:navorder')); }

  /* ---------- 管理者的「還原預設順序」列 ---------- */
  function bar() {
    var tabs = $('#tabs'), b = $('#ndBar');
    if (!tabs || !deskOn() || !isAdm()) { if (b) b.remove(); return; }
    if (!b) {
      b = document.createElement('div'); b.id = 'ndBar';
      b.innerHTML = '<span class="ndh">拖曳可調整順序</span><button type="button" class="ndr">還原預設順序</button>';
      b.querySelector('.ndr').addEventListener('click', function (ev) { ev.stopPropagation(); reset(); });
      tabs.appendChild(b);
    }
    b.querySelector('.ndr').hidden = !order;
    b.querySelector('.ndh').textContent = uns ? '拖曳可調整順序（尚未同步到伺服器）' : '拖曳可調整順序';
  }
  function reset() { if (!isAdm()) return; order = null; apply(); persist(); }

  /* ---------- 讀寫伺服器 ---------- */
  var call = function (path, body) { var A = window.TwAccount; return A && typeof A.call === 'function' ? A.call(path, body) : Promise.resolve(null); };
  function persist() {
    cacheSave();
    if (PV) return Promise.resolve();
    return call('/v1/nav/order/put', { order: order }).then(function (r) {
      if (r && r._s === 200) { uns = false; } else { uns = true; }
      cacheSave(); bar();
    }).catch(function () { uns = true; cacheSave(); bar(); });
  }
  function load(force) {
    if (PV) return Promise.resolve();
    if (!force && Date.now() - loadedAt < 60000) return Promise.resolve();
    return call('/v1/nav/order', {}).then(function (j) {
      if (!(j && j._s === 200 && 'order' in j)) return;   // 舊 Worker（404）：維持快取／預設，不吵
      loadedAt = Date.now();
      if (j.order == null && uns && isAdm()) { persist(); return; }   // 管理者在舊 Worker 時期排的，補送上去
      order = j.order == null ? null : clean(j.order); uns = false; cacheSave(); apply();
    }).catch(function () { /* 離線：維持快取 */ });
  }

  /* ---------- 拖曳 ---------- */
  var D = null, eat = false;
  function rectOf(els) {
    var t = 1e9, b = -1e9, l = 1e9, r = -1e9, any = false;
    els.forEach(function (e) { if (!e || !e.getClientRects().length) return; var q = e.getBoundingClientRect(); any = true; t = Math.min(t, q.top); b = Math.max(b, q.bottom); l = Math.min(l, q.left); r = Math.max(r, q.right); });
    return any ? { top: t, bottom: b, left: l, right: r } : null;
  }
  function sibs(d) {
    var n = N();
    if (d.kind === 'g') return n.GROUPS.map(function (G) { return { k: G.g, els: groupEls(G) }; });
    if (d.kind === 'v') { var G = n.GROUPS.filter(function (x) { return x.g === d.grp; })[0]; return G ? G.views.map(function (v) { return { k: v, els: viewBlock(v) }; }) : []; }
    if (d.kind === 'adm') return subEls('admin').map(function (e) { return { k: e.dataset.adm, els: [e] }; });
    return subEls(d.parent).map(function (e) { return { k: e.dataset.l4sub, els: [e] }; });
  }
  function down(ev) {
    if (ev.button !== 0 || ev.pointerType !== 'mouse' || !deskOn() || root.classList.contains('l4-mini') || !isAdm()) return;
    var t = ev.target; if (!t.closest || t.closest('.naveye, .l4car, #ndBar')) return;
    var tabs = $('#tabs'); if (!tabs || !tabs.contains(t)) return;
    var el = t.closest('.l4grp, .l4subtab, .tab'); if (!el || !tabs.contains(el)) return;
    var d = { el: el, x: ev.clientX, y: ev.clientY, on: false, to: null }, n = N();
    if (el.classList.contains('l4grp')) { d.kind = 'g'; d.key = el.dataset.g; }
    else if (el.classList.contains('l4subtab')) {
      if (el.dataset.parent === 'admin') { d.kind = 'adm'; d.key = el.dataset.adm; } else { d.kind = 's'; d.key = el.dataset.l4sub; d.parent = el.dataset.parent; }
    } else {
      var v = el.id === 'l4Perm' ? 'admin' : el.dataset.view; if (!v) return;
      var G = n.GROUPS.filter(function (x) { return x.views.indexOf(v) >= 0; })[0]; if (!G) return;
      d.kind = 'v'; d.key = v; d.grp = G.g;
    }
    d.label = (el.textContent || '').replace(/\s+/g, ' ').trim() || d.key;
    D = d;
  }
  function move(ev) {
    if (!D) return;
    if (!D.on) {
      if (Math.hypot(ev.clientX - D.x, ev.clientY - D.y) < 6) return;
      D.on = true; root.classList.add('nd-drag'); D.el.classList.add('nd-src');
      D.ghost = document.createElement('div'); D.ghost.className = 'nd-ghost'; D.ghost.textContent = '移動「' + D.label + '」'; document.body.appendChild(D.ghost);
      D.line = document.createElement('div'); D.line.className = 'nd-line'; document.body.appendChild(D.line);
    }
    ev.preventDefault();
    D.ghost.style.left = ev.clientX + 14 + 'px'; D.ghost.style.top = ev.clientY + 14 + 'px';
    var list = sibs(D).map(function (s) { return { k: s.k, r: rectOf(s.els) }; }).filter(function (s) { return s.r; });
    if (!list.length) return;
    var y = ev.clientY, hit = null;
    for (var i = 0; i < list.length; i++) if (y >= list[i].r.top && y <= list[i].r.bottom) { hit = { k: list[i].k, r: list[i].r, after: y > (list[i].r.top + list[i].r.bottom) / 2 }; break; }
    if (!hit) { var f = list[0], l = list[list.length - 1]; hit = y < f.r.top ? { k: f.k, r: f.r, after: false } : { k: l.k, r: l.r, after: true }; }
    D.to = hit;
    D.line.style.top = (hit.after ? hit.r.bottom : hit.r.top) - 1 + 'px'; D.line.style.left = hit.r.left + 'px'; D.line.style.width = Math.max(40, hit.r.right - hit.r.left) + 'px';
  }
  function up() {
    var d = D; D = null; if (!d || !d.on) return;
    d.el.classList.remove('nd-src'); root.classList.remove('nd-drag');
    if (d.ghost) d.ghost.remove(); if (d.line) d.line.remove();
    eat = true; setTimeout(function () { eat = false; }, 0);
    if (!d.to || d.to.k === d.key) return;
    var s = curState(), arr = d.kind === 'g' ? s.g : d.kind === 'v' ? s.v[d.grp] : d.kind === 'adm' ? s.adm : s.s[d.parent];
    var keys = arr.filter(function (k) { return k !== d.key; }), i = keys.indexOf(d.to.k);
    keys.splice(i + (d.to.after ? 1 : 0), 0, d.key);
    if (keys.join() === arr.join()) return;
    if (d.kind === 'g') s.g = keys; else if (d.kind === 'v') s.v[d.grp] = keys; else if (d.kind === 'adm') s.adm = keys; else s.s[d.parent] = keys;
    order = s; apply(); persist();
  }
  document.addEventListener('pointerdown', down);
  document.addEventListener('pointermove', move);
  document.addEventListener('pointerup', up);
  document.addEventListener('pointercancel', function () { if (D && D.on) { D.el.classList.remove('nd-src'); root.classList.remove('nd-drag'); if (D.ghost) D.ghost.remove(); if (D.line) D.line.remove(); } D = null; });
  window.addEventListener('click', function (e) { if (eat) { eat = false; e.stopPropagation(); e.preventDefault(); } }, true);   // 放開那一下不要當成點擊（會換頁／收展）

  /* ---------- 樣式與啟動 ---------- */
  function css() {
    if ($('#navdragCss')) return;
    var s = document.createElement('style'); s.id = 'navdragCss';
    s.textContent =
      ':root.nd-adm #tabs .l4grp,:root.nd-adm #tabs .tab,:root.nd-adm #tabs .l4subtab{cursor:grab}' +
      ':root.nd-drag,:root.nd-drag *{cursor:grabbing!important;user-select:none!important}' +
      '.nd-src{opacity:.4}' +
      '.nd-line{position:fixed;height:3px;border-radius:2px;background:var(--cyan,#4dc2b5);z-index:9999;pointer-events:none}' +
      '.nd-ghost{position:fixed;z-index:9999;pointer-events:none;padding:4px 10px;border-radius:6px;font-size:12px;background:var(--panel,#1c2230);color:var(--ink,#fff);border:1px solid var(--cyan,#4dc2b5);box-shadow:0 6px 20px rgba(0,0,0,.35)}' +
      '#ndBar{order:2000;display:flex;align-items:center;justify-content:space-between;gap:8px;margin:10px 4px 2px;padding:4px 8px;font-size:12px;color:var(--ink-3);border-top:1px dashed var(--line-2,rgba(128,128,128,.3))}' +
      '#ndBar .ndr{border:1px solid var(--line-2,rgba(128,128,128,.4));background:transparent;color:var(--ink-2);border-radius:6px;font-size:12px;padding:3px 8px;cursor:pointer}' +
      '#ndBar .ndr:hover{color:var(--ink);border-color:var(--cyan,#4dc2b5)}' +
      '#ndBar .ndr[hidden]{display:none}' +
      ':root.l4-mini #ndBar{display:none}' +
      '@media (max-width:640px){#ndBar{display:none}}';
    document.head.appendChild(s);
  }
  function boot() {
    css(); snap(); cacheRead(); apply();
    var tabs = $('#tabs');
    if (tabs && !tabs._ndObs) {
      tabs._ndObs = true; var t = 0;
      new MutationObserver(function () { clearTimeout(t); t = setTimeout(paint, 30); }).observe(tabs, { childList: true });   // layout4.js／管理區晚一步才建節點
    }
    var rt = 0; window.addEventListener('resize', function () { clearTimeout(rt); rt = setTimeout(paint, 120); });
    load();
  }
  ['tw:account', 'tw:account-config'].forEach(function (ev) { window.addEventListener(ev, function () { paint(); load(true); }); });
  window.TwNavOrder = { adm: function () { return order && order.adm && order.adm.length ? order.adm : null; }, get: function () { return order; }, apply: apply, reset: reset, unsynced: function () { return uns; } };
  snap(); cacheRead(); applyData();   // 在 layout4.js 第一次建側欄之前，陣列就先排好（管理區子項順序也先讀得到）
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
