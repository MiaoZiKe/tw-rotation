/* tape.js — 「今日時間軸」：盤中從 09:00 到最新，可拖拉看任一時點、按播放重播當天（Andy 2026-10-29）
 *
 * Andy 原話：「即時功能 幫我新增一個時間軸，開盤到最新時間，他會多一個時間拉Bar 可以播放當日狀況，資金流水也是」「熱力圖也是」。
 * 三張圖（資金輪盤、資金分流樹、熱力圖產業／題材）的「即時」模式都吃「一包報價 {代號: {price, volume, chgPct, time}}」再用既有公式算出畫面，
 * 所以這支只做一件事：**提供「某個時點的那一包報價」**，圖要怎麼算還是它們自己的公式（口徑只有一份，不會分岔）。
 *
 * 資料從哪來（DECISIONS #372）
 *   ① 伺服器快照（主要）：Cloudflare Worker（workers/quote-proxy）盤中每 5 分鐘把約 455 檔成分股的成交價／累積量存進 KV，
 *      GET {proxy}/tape 一次拿到「今天 09:00 到現在」全部格子（NDJSON，第一行標頭、之後一格一行）。頁面沒開著也一樣有。
 *   ② 頁面自己累積（備援）：Worker 還沒部署、被擋、或最新一格還沒寫進 KV 時，live.js 每 5 秒收到的報價按 5 分鐘一格存在記憶體。
 *      只能從「開啟頁面那一刻」起算，所以不能只靠它——這是備援，不是主力。
 *   兩者合併：同一格以伺服器為準；本機格只補在伺服器最後一格之後。
 *
 * 游標（cur）是全站共用的一個：拖到哪，所有開著「即時」的圖都顯示那個時點；最右邊＝最新（回到即時、繼續跟新資料）。
 * 圖要不要反應由它們自己訂閱（Tape.on('cur'|'data', fn)），這支不碰任何圖。
 *
 * 只有站主或管理員（Live.proxy() 非空）會抓 /tape；訪客沒有即時，這支整個不動作。 */
(function () {
  'use strict';
  var STEP_MIN = 5;             // 一格 5 分鐘（Worker 的 Cron 間隔）
  var FRAME_MS = 600;           // 播放：每格停多久（一天約 54 格 ≈ 32 秒播完）
  var POLL_MS = 60 * 1000;      // 有時間軸在畫面上時，每分鐘問一次伺服器有沒有新的一格

  var srv = null;               // { date:'YYYY-MM-DD', day8, codes:[], y:[], slots:[{t,p,v}] }
  var loc = {};                 // 本機累積：'HH:MM' → { day8, q:{code:{...}} }
  var maxLoc = 0;               // 本機格子裡最多的檔數（判斷新的一格算不算「夠完整」）
  var curT = null;              // 目前釘住的時間格（'10:30'）；null＝最新（跟著即時）
  var listeners = { cur: [], data: [] };
  var bars = [];                // 目前畫面上的時間軸 DOM
  var loadedAt = 0, loading = null, pollTimer = null;
  var playTimer = null, playRun = 0;

  // ------------------------------------------------------------ 時間（一律台北，使用者電腦不一定在台北）
  var FMT = null;
  try { FMT = new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Taipei', hour12: false, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }); } catch (e) { FMT = null; }
  function tpe() {
    var d = new Date();
    if (FMT) {
      var o = {}; FMT.formatToParts(d).forEach(function (p) { o[p.type] = p.value; });
      var h = o.hour === '24' ? '00' : o.hour;
      return { day8: o.year + o.month + o.day, mins: (+h) * 60 + (+o.minute) };
    }
    var u = new Date(d.getTime() + 8 * 3600 * 1000);
    var p2 = function (n) { return String(n).padStart(2, '0'); };
    return { day8: u.getUTCFullYear() + p2(u.getUTCMonth() + 1) + p2(u.getUTCDate()), mins: u.getUTCHours() * 60 + u.getUTCMinutes() };
  }
  function hm(mins) { return String(Math.floor(mins / 60)).padStart(2, '0') + ':' + String(mins % 60).padStart(2, '0'); }
  function live() { return window.Live || null; }
  function intraday() { var L = live(); return !!(L && L.isIntraday && L.isIntraday()); }
  function base() { var L = live(); return L && L.proxy ? L.proxy() : ''; }

  // ------------------------------------------------------------ 合併後的格子清單
  var cache = null;
  function slots() {
    if (cache) return cache;
    var out = [], now = tpe();
    var useSrv = srv && srv.slots.length && !(intraday() && srv.day8 !== now.day8);
    var lastSrv = '';
    if (useSrv) srv.slots.forEach(function (s) { out.push({ t: s.t, src: 's', s: s }); lastSrv = s.t; });
    var need = Math.max(20, Math.round((useSrv ? srv.codes.length : maxLoc) * 0.6));
    Object.keys(loc).sort().forEach(function (t) {
      var b = loc[t];
      if (b.day8 !== now.day8 || t <= lastSrv) return;
      if (Object.keys(b.q).length < need) return;
      out.push({ t: t, src: 'l', q: b.q });
    });
    cache = out;
    return out;
  }
  function dirty() { cache = null; }

  function qOfSlot(sl) {
    if (sl.q) return sl.q;
    var s = sl.s;
    if (s._q) return s._q;
    var q = {}, day = srv.day8;
    for (var i = 0; i < srv.codes.length; i++) {
      var p = s.p[i];
      if (p == null) continue;
      var y = srv.y[i];
      q[srv.codes[i]] = { code: srv.codes[i], price: p, volume: s.v[i], prevClose: y, chgPct: y ? (p - y) / y * 100 : null, time: s.t + ':00', date: day, at: 0 };
    }
    s._q = q;
    return q;
  }

  // ------------------------------------------------------------ 對外：游標
  function curIndex() {
    if (curT == null) return null;
    var a = slots();
    for (var i = 0; i < a.length; i++) if (a[i].t === curT) return i;
    return null;
  }
  var emitQ = 0;
  function emit(kind) {
    // 拖曳時 input 事件一秒幾十次，圖一次重畫要幾十毫秒：同一個 frame 只通知一次
    if (emitQ) { emitQ |= kind === 'cur' ? 1 : 2; return; }
    emitQ = kind === 'cur' ? 1 : 2;
    var run = function () {
      var k = emitQ; emitQ = 0;
      syncBars();
      if (k & 2) listeners.data.slice().forEach(function (f) { try { f('data'); } catch (e) { console.warn('Tape data', e); } });
      if (k & 1) listeners.cur.slice().forEach(function (f) { try { f('cur'); } catch (e) { console.warn('Tape cur', e); } });
    };
    if (window.requestAnimationFrame && !document.hidden) window.requestAnimationFrame(run); else setTimeout(run, 0);
  }
  function setCur(t) {
    if (t === curT) return;
    curT = t;
    emit('cur');
  }

  // ------------------------------------------------------------ 伺服器快照
  function parse(text) {
    var lines = String(text || '').split('\n').filter(Boolean);
    if (!lines.length) return null;
    var head = JSON.parse(lines[0]);
    if (!head || !head.codes) return null;
    var out = { date: head.date, day8: String(head.date || '').replace(/-/g, ''), codes: head.codes, y: head.y || [], slots: [] };
    for (var i = 1; i < lines.length; i++) {
      try { var s = JSON.parse(lines[i]); if (s && s.t && s.p) out.slots.push(s); } catch (e) { /* 壞行略過（寫到一半被讀走） */ }
    }
    return out;
  }
  function load(force) {
    var b = base();
    if (!b) return Promise.resolve(false);
    if (loading) return loading;
    if (!force && loadedAt && (!intraday() || Date.now() - loadedAt < 15000)) return Promise.resolve(!!srv);   // 盤後不重抓（格子不會再增加）
    loading = fetch(b + '/tape', { cache: 'no-store' }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.text();
    }).then(function (txt) {
      var n = srv ? srv.slots.length : 0;
      var nx = parse(txt);
      srv = nx; loadedAt = Date.now(); dirty();
      if (!nx || nx.slots.length !== n) emit('data');
      return !!nx;
    }).catch(function () { loadedAt = Date.now(); srv = srv || null; return false; })
      .then(function (v) { loading = null; return v; });
    return loading;
  }
  function poll() {
    if (pollTimer) return;
    pollTimer = setInterval(function () {
      if (!bars.length) { clearInterval(pollTimer); pollTimer = null; return; }
      if (!document.hidden && intraday()) load(true);
    }, POLL_MS);
  }

  // ------------------------------------------------------------ 本機累積（備援）
  function note() {
    var L = live();
    if (!L || !L.isIntraday || !L.isIntraday() || !L.quotes) return;
    var now = tpe();
    var t = hm(now.mins - (now.mins % STEP_MIN));
    var Q = L.quotes, b = loc[t];
    if (!b) { b = loc[t] = { day8: now.day8, q: {} }; }
    var before = Object.keys(b.q).length, n = 0;
    Object.keys(Q).forEach(function (c) {
      var x = Q[c];
      if (!x || x.price == null || x.volume == null) return;
      if (x.date && String(x.date).replace(/-/g, '') !== now.day8) return;
      b.q[c] = { code: c, price: x.price, volume: x.volume, prevClose: x.prevClose, chgPct: x.chgPct, time: x.time, date: x.date, at: x.at };
      n++;
    });
    var after = Object.keys(b.q).length;
    if (after > maxLoc) maxLoc = after;
    if (after !== before) { dirty(); if (bars.length) emit('data'); }
    // 一天的格子最多 55 個，舊的日子清掉
    Object.keys(loc).forEach(function (k) { if (loc[k].day8 !== now.day8) delete loc[k]; });
  }
  window.addEventListener('tw:live', note);

  // ------------------------------------------------------------ 時間軸 DOM
  var CSS = '' +
    '.tlbar{display:flex;align-items:center;gap:8px;flex-wrap:nowrap;font-size:12.5px;color:var(--ink-2);white-space:nowrap;min-width:0}' +
    '.tlbar .t{color:var(--ink-3)}' +
    '.tlbar input[type=range]{flex:1 1 180px;min-width:72px;max-width:420px;accent-color:var(--cyan);height:24px}' +
    '.tlbar .val{font-family:var(--mono);font-size:12px;color:var(--ink);min-width:52px;text-align:center;font-variant-numeric:tabular-nums}' +
    '.tlbar .pb.latest{width:auto;padding:0 var(--sp-2);font-size:12px}' +
    '.tlbar.playdim > input,.tlbar.playdim > .pb.step,.tlbar.playdim > .pb.latest{opacity:.32;filter:grayscale(1);pointer-events:none;cursor:not-allowed}' +
    '.tlbar.playing .pb.play{border-color:var(--cyan);color:var(--cyan);box-shadow:var(--glow)}' +
    '.tlbar.tlblock{width:100%;margin:var(--sp-1) 0 var(--sp-2)}' +
    '.rbar.tlon > :not(.livebtn){display:none!important}' +
    '@media (max-width:640px){' +
    '.tlbar{gap:6px;width:100%}' +
    '.tlbar .pb{width:32px;height:32px}' +
    '.tlbar .pb.latest{width:auto;padding:0 8px}' +
    '.tlbar input[type=range]{height:32px;min-height:32px;touch-action:none;flex:1 1 60px;min-width:48px}' +
    '.tlbar .tl0,.tlbar .tl1,.tlbar .tlt{display:none}' +
    '.tlbar .val{min-width:44px}' +
    '}';
  function injectCss() {
    if (document.getElementById('tapeCss')) return;
    var st = document.createElement('style'); st.id = 'tapeCss'; st.textContent = CSS; document.head.appendChild(st);
  }

  function mkBtn(cls, txt, title) {
    var b = document.createElement('button');
    b.type = 'button'; b.className = 'pb ' + cls; b.textContent = txt; b.title = title; b.setAttribute('aria-label', title);
    return b;
  }
  /** 建一條時間軸（還沒放進畫面）。id 給驗收與樣式用；block＝獨佔一整列（熱力圖卡片用）。 */
  function bar(id, block) {
    injectCss();
    var el = document.createElement('div');
    el.id = id; el.className = 'rbar tlbar' + (block ? ' tlblock' : ''); el.setAttribute('data-tl', '1');
    el.title = '今日時間軸：從開盤 09:00 到最新，拖拉看任一時點，▶ 重播當天';
    var tlt = document.createElement('span'); tlt.className = 't tlt'; tlt.textContent = '今日';
    var bPlay = mkBtn('play', '▶', '播放今天');
    var bMinus = mkBtn('step', '−', '前一格');
    var l0 = document.createElement('span'); l0.className = 't tl0';
    var inp = document.createElement('input'); inp.type = 'range'; inp.min = 0; inp.max = 0; inp.step = 1; inp.value = 0;
    inp.setAttribute('aria-label', '今日時間軸');
    var l1 = document.createElement('span'); l1.className = 't tl1'; l1.textContent = '最新';
    var bPlus = mkBtn('step', '＋', '後一格');
    var val = document.createElement('span'); val.className = 'val';
    var bLast = mkBtn('latest', '最新', '回到最新（繼續跟著即時更新）');
    [tlt, bPlay, bMinus, l0, inp, l1, bPlus, val, bLast].forEach(function (n) { el.appendChild(n); });
    el._tl = { inp: inp, l0: l0, val: val, bPlay: bPlay, bMinus: bMinus, bPlus: bPlus, bLast: bLast };

    var pos = function () { return +inp.value; };
    var N = function () { return slots().length; };
    var go = function (p) {   // p＝0..N-1 是某一格、N 是最新
      var a = slots();
      setCur(p >= a.length ? null : a[Math.max(0, p)].t);
    };
    inp.oninput = function () { stopPlay(); go(pos()); };
    inp.addEventListener('pointerdown', stopPlay);
    bMinus.onclick = function () { stopPlay(); go(Math.max(0, pos() - 1)); };
    bPlus.onclick = function () { stopPlay(); go(Math.min(N(), pos() + 1)); };
    bLast.onclick = function () { stopPlay(); setCur(null); };
    bPlay.onclick = function () { if (playTimer) stopPlay(); else startPlay(); };
    return el;
  }

  function syncBars() {
    bars = bars.filter(function (b) { return b.isConnected; });
    var a = slots(), n = a.length, ci = curIndex();
    bars.forEach(function (el) {
      var u = el._tl; if (!u) return;
      u.inp.max = n;
      u.inp.value = ci == null ? n : ci;
      u.l0.textContent = n ? a[0].t : '';
      u.val.textContent = ci == null ? '最新' : a[ci].t;
      u.bMinus.disabled = !!playTimer || (ci == null ? n === 0 : ci <= 0);
      u.bPlus.disabled = !!playTimer || ci == null;
      u.bLast.disabled = !!playTimer || ci == null;
      u.bPlay.disabled = n === 0;
      u.bPlay.textContent = playTimer ? '⏸' : '▶';
      u.bPlay.title = playTimer ? '暫停' : '播放今天';
      u.bPlay.setAttribute('aria-label', u.bPlay.title);
      el.classList.toggle('playing', !!playTimer);
      el.classList.toggle('playdim', !!playTimer);
      var src = srv && a.length && a[0].src === 's' ? '伺服器每 5 分鐘快照（從開盤起）' : '這個頁面開著之後累積的快照（伺服器快照尚未連線，不是從 09:00 起）';
      el.title = '今日時間軸：' + (n ? a[0].t + ' 到最新，每 5 分鐘一格，共 ' + n + ' 格。' : '') + '資料：' + src + '。拖拉看任一時點，▶ 重播當天。';
    });
  }

  function stopPlay() {
    if (playTimer) { clearTimeout(playTimer); playTimer = null; playRun++; syncBars(); }
  }
  function startPlay() {
    var a = slots(); if (!a.length || playTimer) return;
    var ci = curIndex();
    // 在最新（或最後一格）按播放＝從開盤重播；在中間＝從那一格接著播
    var p = (ci == null || ci >= a.length - 1) ? 0 : ci + 1;
    setCur(a[p].t);
    var id = ++playRun;
    var step = function () {
      playTimer = setTimeout(function () {
        if (id !== playRun) return;
        var b = slots(), c = curIndex();
        var nx = (c == null ? 0 : c + 1);
        if (nx >= b.length) { playTimer = null; setCur(null); syncBars(); return; }   // 播到最新：回到即時，繼續跟新資料
        setCur(b[nx].t);
        step();
      }, FRAME_MS);
    };
    step();
    syncBars();
  }

  /** 把時間軸放到 host 後面（host 之後的兄弟）；已經放過就不重複。 */
  function mountAfter(host, id, block) {
    if (!host) return null;
    var el = document.getElementById(id);
    if (el && el.isConnected) {
      if (el.previousElementSibling !== host) host.insertAdjacentElement('afterend', el);
      return el;
    }
    el = bar(id, block);
    host.insertAdjacentElement('afterend', el);
    bars.push(el);
    load(false); poll(); syncBars();
    return el;
  }
  function unmount(id) {
    var el = document.getElementById(id);
    if (el) el.remove();
    bars = bars.filter(function (b) { return b.id !== id && b.isConnected; });
    if (!bars.length) stopPlay();
  }

  window.Tape = {
    slots: slots,
    count: function () { return slots().length; },
    /** 某一格的報價包（{代號: {price, volume, chgPct, time, date}}）；不給＝目前游標（最新就是最後一格）。 */
    q: function (i) {
      var a = slots(); if (!a.length) return {};
      if (i == null) { var ci = curIndex(); i = ci == null ? a.length - 1 : ci; }
      return qOfSlot(a[Math.max(0, Math.min(a.length - 1, i))]);
    },
    get cur() { return curIndex(); },
    get curT() { return curT; },
    pinned: function () { return curIndex() != null; },
    setCur: function (t) { setCur(t); },
    /** 游標歸零（最新）。不通知也行：呼叫端通常是「所有即時都關了」的收尾。 */
    reset: function () { stopPlay(); if (curT != null) { curT = null; emit('cur'); } },
    on: function (kind, fn) { if (listeners[kind]) listeners[kind].push(fn); },
    load: load,
    note: note,
    mountAfter: mountAfter,
    unmount: unmount,
    play: startPlay,
    stop: stopPlay,
    get playing() { return !!playTimer; },
    get source() { var a = slots(); return !a.length ? 'none' : (a[0].src === 's' ? 'server' : 'local'); },
    get date() { return srv ? srv.date : ''; },
    stepMs: FRAME_MS,
    /** 驗收用：直接塞一份本機格子（不經 live.js）。 */
    _debugLoc: function () { return loc; },
  };
})();
