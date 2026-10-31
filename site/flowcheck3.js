/* flowcheck3.js —「流向驗證」v3 首屏（河流／輪盤同一張圖）＋今天的訊號＋驗證與案例
 *
 * Andy 11-01：「這還是太亂了 資訊太雜看不懂…站在想使用介面但不想花太多時間的人進行安排」
 *            「資金輪盤 資金樹 都需要放在同一張圖 觀看走勢圖變化」
 *            「最後也需要有實際使用案例 不管是成功失敗都需要透過驗證來證明我們的數據工具成效」。
 * 規格 docs/design/20261101_flowcheck_v3.md（選定方案丁）；原型 docs/design/20261101_flowcheck_v3/proto_f.html。
 *
 * 分工：這支只管「首屏那一張主圖」與它的卡片、播放、訊號列、案例；舊頁面的熱力圖／走勢大圖／成分股／日級別訊號…
 * 留在 flowcheck.js，收進「進階」。兩邊靠 api（flowcheck.js 注入）溝通：選族群 pick、換日期 date、改網址 url。
 *
 * 資料：只讀 flowcheck/index.json 與 day/<日期>.json（近 30 個交易日並行載入）＋ next_wave.json（訊號研究，選用）。
 * 口徑（規格 5.4）：
 *   · 流入／流出前 N＝今日 dshare 排序，且占比 ≥ 1% 才參與（避免 0.3% 的小族群跳動就上榜）。
 *   · 「近期趨勢」＝資金輪盤象限 m_quadrant（近 5 日占比 ÷ 近 20 日），不叫「流入／流出」，兩個概念不同詞。
 *   · 累計漲跌由每日 chg 連乘，起點＝窗口第一天；各列刻度不同，以右邊數字為準。
 * 紅漲綠跌只用在漲跌（數字、折線）；色帶／輪盤點用產業鏈類別色（--cat-*）。
 */
(function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var esc = function (s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };
  var API = null, built = false;
  var V = { dates: [], T: 0, G: [], by: {}, mk: [], mcum: [], mh: 1, fix: null, nw: undefined, ready: false };
  var S = { t: 0, sel: null, win: 30, view: 'river', play: null, sigOpen: false };
  var QL = { leading: '持續升溫', improving: '降溫放緩', weakening: '升溫放緩', lagging: '持續降溫' };
  var NROWS = 10;
  var RH = function () { return isMob() ? 40 : 32; }, CHH = function () { return isMob() ? 18 : 16; };
  var stageH = function () { return 6 + NROWS * RH() + V.mh * CHH() + 28; };
  var CATS = ['semiconductor', 'ai_server', 'siph_cpo', 'electronics', 'software', 'financial', 'traditional', 'infrastructure'];

  var f1 = function (v) { return v == null || !isFinite(v) ? '—' : (v > 0 ? '+' : '') + (+v).toFixed(1); };
  var f2 = function (v) { return v == null || !isFinite(v) ? '—' : (v > 0 ? '+' : '') + (+v).toFixed(2); };
  var p1 = function (v) { return v == null || !isFinite(v) ? '—' : (+v).toFixed(1); };
  var cls = function (v) { return v == null || !isFinite(v) || v === 0 ? '' : (v > 0 ? 'fc3-up' : 'fc3-dn'); };
  var vcol = function (v) { return 'var(' + (v >= 0 ? '--rise' : '--fall') + ')'; };
  var mdl = function (d) { return d.slice(5).replace('-', '/'); };
  var isMob = function () { return window.matchMedia && window.matchMedia('(max-width:640px)').matches; };
  var weekday = function (d) { return '日一二三四五六'[new Date(d + 'T00:00:00+08:00').getDay()]; };
  /* 產業鏈類別色：已知 8 類用具名 token，其餘依字串雜湊落在 4 個備用色（兩個主題的色值都在 flowcheck3.css） */
  function catVar(ch) {
    if (CATS.indexOf(ch) >= 0) return 'var(--cat-' + ch + ')';
    var h = 0; String(ch || '').split('').forEach(function (c) { h = (h * 31 + c.charCodeAt(0)) >>> 0; });
    return 'var(--cat-o' + (h % 4) + ')';
  }
  var chainName = function (ch) { var a = API && API.A(); var n = a && a.chainLabel ? a.chainLabel(ch) : null; return n || ch || '其他'; };

  /* ---------------------------------------------------------------- 資料 */
  function cum(a) { var c = 100; return a.map(function (x) { c *= 1 + (x || 0) / 100; return c; }); }
  function load(idx) {
    var ds = (idx.dates || []).slice(-30);
    V.dates = ds; V.T = ds.length;
    return Promise.all(ds.map(function (d) { return API.getDay(d); })).then(function (days) {
      var gs = (idx.groups || []).filter(function (g) { return !g.is_bucket; });
      V.G = gs.map(function (g) {
        var o = { gid: g.gid, name: g.name, chain: g.chain, share: [], dshare: [], chg: [], rel: [], mx: [], my: [], q: [] };
        days.forEach(function (dy) {
          var r = dy && dy.groups && dy.groups[g.gid];
          o.share.push(r ? r.share : null); o.dshare.push(r ? r.dshare : null); o.chg.push(r ? r.chg : null); o.rel.push(r ? r.rel : null);
          o.mx.push(r ? r.m_x : null); o.my.push(r ? r.m_y : null); o.q.push(r ? r.m_quadrant : null);
        });
        o.cum = cum(o.chg);
        return o;
      });
      V.by = {}; V.G.forEach(function (g) { V.by[g.gid] = g; });
      V.mk = days.map(function (dy) { return dy ? dy.mkt_chg : null; });
      V.mcum = cum(V.mk);
      /* 輪盤座標範圍：整段期間固定（97 百分位 ×1.05，至少 ±30），播放時圖不縮放（規格 5.1） */
      var xs = [], ys = [];
      V.G.forEach(function (g) { for (var k = 0; k < V.T; k++) if (g.share[k] >= 0.5 && g.mx[k] != null && g.my[k] != null) { xs.push(Math.abs(g.mx[k] - 100)); ys.push(Math.abs(g.my[k] - 100)); } });
      xs.sort(function (a, b) { return a - b; }); ys.sort(function (a, b) { return a - b; });
      var q97 = function (a) { return a.length ? a[Math.floor(a.length * 0.97)] : 0; };
      V.fix = { x: Math.max(30, q97(xs) * 1.05), y: Math.max(30, q97(ys) * 1.05) };
      /* 主圖高度固定：10 列＋「窗口內任一天最多幾個產業鏈標題（被選族群換掉一列、標題數不超過它）」＋軸 → 換日期／窗口／選取／河流輪盤切換都不晃（andy_ui_rules A9） */
      var mh = 1;
      for (var t = 0; t < V.T; t++) mh = Math.max(mh, rowsF(t, null).length);
      V.mh = mh;
      V.ready = true;
    });
  }

  /* ---------------------------------------------------------------- 口徑 */
  function topN(t, n) {
    var r = V.G.filter(function (g) { return g.share[t] >= 1 && g.dshare[t] != null; }).sort(function (a, b) { return b.dshare[t] - a.dshare[t]; });
    var inn = r.slice(0, n), out = r.slice(Math.max(inn.length, r.length - n)).reverse();
    return { inn: inn, out: out };
  }
  function rowsF(t, sel) {
    var tn = topN(t, 5), ids = [];
    var add = function (g) { if (g && ids.indexOf(g.gid) < 0) ids.push(g.gid); };
    tn.inn.forEach(add); tn.out.slice(0, 3).forEach(add);
    V.G.slice().sort(function (a, b) { return (b.share[t] || 0) - (a.share[t] || 0); }).forEach(function (g) { if (ids.length < NROWS) add(g); });
    ids = ids.slice(0, NROWS);
    if (sel && ids.indexOf(sel) < 0 && V.by[sel]) {          // 被選的不在榜內：換掉一列（列數不變），並盡量不讓產業鏈標題數超過主圖預留的高度
      var nch = function (a) { var m = {}; a.forEach(function (id) { m[V.by[id].chain] = 1; }); return Object.keys(m).length; };
      var at = NROWS - 1;
      if (V.ready) for (var i = NROWS - 1; i >= 0; i--) { var tmp = ids.slice(); tmp[i] = sel; if (nch(tmp) <= V.mh) { at = i; break; } }
      ids[at] = sel;
    }
    var by = {};
    ids.forEach(function (id) { var g = V.by[id]; (by[g.chain] = by[g.chain] || []).push(g); });
    var tot = function (c) { return V.G.filter(function (g) { return g.chain === c; }).reduce(function (a, g) { return a + (g.share[t] || 0); }, 0); };
    return Object.keys(by).map(function (c) { return { chain: c, tot: tot(c), gs: by[c].sort(function (a, b) { return (b.share[t] || 0) - (a.share[t] || 0); }) }; })
      .sort(function (a, b) { return b.tot - a.tot; });
  }
  var lo = function () { return V.T - S.win; };
  function rel0(arr, k, base) { return arr[k] / arr[base] * 100 - 100; }          // 相對窗口起點的累計漲跌 %
  function focusG() { return S.sel ? V.by[S.sel] : (topN(S.t, 1).inn[0] || null); }

  /* ---------------------------------------------------------------- 骨架 */
  function mount(root) {
    root.innerHTML =
      '<div class="fc3" id="fc3root">'
      + '<div class="fc3-hd"><span class="fc3-date" id="fc3Date"></span><span class="fc3-sp"></span>'
      + '<div class="seg" id="fc3View" role="group" aria-label="圖的種類"><button type="button" data-v="river" class="on" aria-pressed="true">河流</button><button type="button" data-v="wheel" aria-pressed="false">輪盤</button></div>'
      + '<div class="seg" id="fc3Win" role="group" aria-label="期間">' + [10, 20, 30].map(function (n) { return '<button type="button" data-w="' + n + '"' + (n === 30 ? ' class="on" aria-pressed="true"' : ' aria-pressed="false"') + '>' + n + ' 日</button>'; }).join('') + '</div>'
      + API.howBox('v3') + '</div>'
      + API.howDiv('v3')
      + '<div class="fc3-sent" id="fc3Sent" aria-live="polite"></div>'
      + '<div class="fc3-ans" id="fc3Ans"></div>'
      + '<div class="card fc3-stagecard" id="fc3Card"><div class="fc3-info" id="fc3Info"></div><div class="fc3-stage" id="fc3Stage"></div><div class="fc3-tip" id="fc3Tip" role="tooltip"></div>'
      + '<div class="fc3-ctl"><button type="button" class="fc3-play" id="fc3Play" aria-label="播放">▶</button>'
      + '<input type="range" id="fc3Range" min="0" max="0" step="1" value="0" aria-label="日期">'
      + '<span class="fc3-tl" id="fc3Tl"></span><button type="button" class="fc3-latest" id="fc3Latest">回最新</button><span class="fc3-gap" id="fc3Gap"></span></div></div>'
      + '<div class="card fc3-sigwrap" id="fc3SigWrap"><div id="fc3Sig"></div></div>'
      + '</div>';
    wire(root);
    try { new ResizeObserver(function () { if (V.ready) drawStage(); }).observe($('#fc3Stage')); } catch (e) { /* 舊瀏覽器 */ }
    built = true;
  }
  function wire(root) {
    $('#fc3View').addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b) return; setView(b.dataset.v); });
    $('#fc3Win').addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b || b.disabled) return; setWin(+b.dataset.w); });
    $('#fc3Ans').addEventListener('click', function (e) { var c = e.target.closest('.fc3-chip'); if (c) select(c.dataset.g); });
    $('#fc3Play').addEventListener('click', togglePlay);
    $('#fc3Latest').addEventListener('click', function () { stopPlay(); setT(V.T - 1); });
    $('#fc3Range').addEventListener('input', function (e) { stopPlay(); setT(+e.target.value); });
    $('#fc3Sig').addEventListener('click', function (e) {
      var b = e.target.closest('[data-sig]'); if (!b) return;
      if (b.dataset.sig === 'toggle') { S.sigOpen = !S.sigOpen; drawSignal(); }
      else if (b.dataset.sig === 'cases') API.openAdv('cases');
      else if (b.dataset.sig === 'pick') select(b.dataset.g, true);
    });
  }

  /* ---------------------------------------------------------------- 狀態 */
  function select(gid, force) {
    if (!gid) return;
    S.sel = (S.sel === gid && !force) ? null : gid;
    if (S.sel) API.pick(S.sel);
    API.url(false); all();
  }
  function setT(t) {
    S.t = Math.max(lo(), Math.min(V.T - 1, t));
    API.date(V.dates[S.t]); API.url(false); all();
  }
  function setWin(n) {
    if (n > V.T) return;
    S.win = n; S.t = Math.max(S.t, lo()); API.date(V.dates[S.t]); API.url(false); all();
  }
  function setView(v) {
    if (v !== 'river' && v !== 'wheel') return;
    S.view = v; API.url(false); all();
  }
  function stopPlay() { if (S.play) { clearInterval(S.play); S.play = null; } var b = $('#fc3Play'); if (b) { b.textContent = '▶'; b.setAttribute('aria-label', '播放'); } }
  function togglePlay() {
    if (S.play) { stopPlay(); return; }
    var b = $('#fc3Play'); b.textContent = '❚❚'; b.setAttribute('aria-label', '暫停');
    if (S.t >= V.T - 1) setT(lo());
    S.play = setInterval(function () { if (S.t >= V.T - 1) { stopPlay(); return; } setT(S.t + 1); }, 500);
  }

  /* ---------------------------------------------------------------- 繪製 */
  function all() {
    if (!V.ready || !built) return;
    tip(null);
    $('#fc3Range').min = lo(); $('#fc3Range').max = V.T - 1; $('#fc3Range').value = S.t;
    var d = V.dates[S.t];
    $('#fc3Date').textContent = d + '（' + weekday(d) + '）';
    $$('#fc3View button').forEach(function (b) { var on = b.dataset.v === S.view; b.classList.toggle('on', on); b.setAttribute('aria-pressed', on); });
    $$('#fc3Win button').forEach(function (b) {
      var n = +b.dataset.w, on = n === S.win, off = n > V.T;
      b.classList.toggle('on', on); b.setAttribute('aria-pressed', on); b.disabled = off;
      b.title = off ? '資料只有 ' + V.T + ' 個交易日，不足 ' + n + ' 日' : '';
    });
    $('#fc3Tl').textContent = mdl(d);
    $('#fc3Latest').style.visibility = S.t < V.T - 1 ? 'visible' : 'hidden';
    drawSentence(); drawChips(); drawStage(); drawInfo(); drawGapNote();
  }
  function drawSentence() {
    var t = S.t, g = topN(t, 1).inn[0], m = V.mk[t], el = $('#fc3Sent');
    if (!g || g.dshare[t] <= 0) { el.innerHTML = mdl(V.dates[t]) + ' 沒有占比 ≥ 1% 且比前一天明顯增加的族群。'; return; }
    var rel = g.rel[t], w = rel == null ? '' : Math.abs(rel) < 0.3 ? '和加權指數差不多' : (rel > 0 ? '比加權指數強' : '比加權指數弱');
    el.innerHTML = mdl(V.dates[t]) + ' 資金往 <b>' + esc(g.name) + '</b> 集中（占全市場成交額 ' + p1(g.share[t]) + '%，比前一天多 ' + p1(g.dshare[t]) + ' 個百分點）；它當天 <b class="' + cls(g.chg[t]) + '">' + f1(g.chg[t]) + '%</b>'
      + (w ? '，' + w : '') + '（加權指數 <span class="' + cls(m) + '">' + f1(m) + '%</span>）。';
  }
  function drawChips() {
    var t = S.t, tn = topN(t, 3);
    var mk = function (g, i, k) {
      return '<button type="button" class="fc3-chip' + (S.sel === g.gid ? ' on' : '') + '" data-g="' + esc(g.gid) + '" aria-pressed="' + (S.sel === g.gid) + '" title="' + esc(g.name) + '">'
        + '<span class="k">' + k + (i + 1) + '</span><span class="n">' + esc(g.name) + '</span>'
        + '<span class="v"><span class="a">占比 ' + f2(g.dshare[t]) + '・</span><span class="' + cls(g.chg[t]) + '">' + f1(g.chg[t]) + '%</span></span></button>';
    };
    var empty = '<div class="fc3-none">今天沒有占比 ≥ 1% 的族群</div>';
    $('#fc3Ans').innerHTML = '<div class="fc3-grp"><div class="fc3-gt">今日資金流入</div>' + (tn.inn.length ? tn.inn.map(function (g, i) { return mk(g, i, '流入第 '); }).join('') : empty) + '</div>'
      + '<div class="fc3-grp"><div class="fc3-gt">今日資金流出</div>' + (tn.out.length ? tn.out.map(function (g, i) { return mk(g, i, '流出第 '); }).join('') : empty) + '</div>';
  }
  function drawStage() {
    var el = $('#fc3Stage'); if (!el || !V.ready) return;
    el.style.height = stageH() + 'px';
    if (el.clientWidth < 40) return;
    if (S.view === 'river') drawRiver(el); else drawWheel(el);
  }
  /* 點一列／一個點的細節：手機沒有 hover，所以主圖上方留固定一行（桌機隱藏，改用滑過提示） */
  function infoText(g) {
    var t = S.t;
    if (!g) return '<span class="fc3-mut">點任一列（或一個點）看細節</span>';
    return '<b>' + esc(g.name) + '</b><span class="fc3-mut">　占比 ' + p1(g.share[t]) + '%（' + f2(g.dshare[t]) + '）</span>　今日 <b class="' + cls(g.chg[t]) + '">' + f1(g.chg[t]) + '%</b><span class="fc3-mut">　加權 ' + f1(V.mk[t]) + '%</span>';
  }
  function drawInfo() { $('#fc3Info').innerHTML = infoText(S.sel ? V.by[S.sel] : null); }
  function drawGapNote() {
    var ix = API.idx, a = V.dates[lo()], b = V.dates[V.T - 1];
    var inR = function (arr) { return (arr || []).filter(function (d) { return d >= a && d <= b; }).map(mdl); };
    var cl = inR(ix.closed_days), ms = inR(ix.missing_days), s = [];
    if (cl.length) s.push('休市：' + cl.join('、'));
    if (ms.length) s.push('資料缺：' + ms.join('、'));
    $('#fc3Gap').textContent = s.join('　');
  }

  /* 名稱依像素截斷（中日韓字 13px、其他約 7px），放不下才加省略號；完整名稱在 <title> 與卡片 */
  function fitName(nm, px) {
    var w = 0, out = '';
    for (var i = 0; i < nm.length; i++) {
      var cw = nm.charCodeAt(i) > 255 ? 13 : 7.2;
      if (w + cw > px) { while (out.length && (w + 13 > px)) { var last = out.charAt(out.length - 1); w -= last.charCodeAt(0) > 255 ? 13 : 7.2; out = out.slice(0, -1); } return out + '…'; }
      w += cw; out += nm.charAt(i);
    }
    return nm;
  }
  /* ---- 河流 ---- */
  function drawRiver(el) {
    var W = el.clientWidth, mob = W < 560, t = S.t, L = lo(), n = S.win, T = V.T;
    var LW = mob ? 116 : 176, RW = mob ? 58 : 360, px0 = LW, px1 = W - RW - 6, dx = (px1 - px0) / Math.max(1, n - 1), X = function (k) { return px0 + (k - L) * dx; };
    var ROWH = RH(), CH = CHH(), rows = rowsF(t, S.sel), y = 6, items = [];
    rows.forEach(function (r) { items.push({ h: 1, r: r, y: y }); y += CH; r.gs.forEach(function (g) { items.push({ g: g, y: y }); y += ROWH; }); });
    var H = stageH(), mx = 0;
    items.forEach(function (i) { if (i.g) for (var k = L; k < T; k++) mx = Math.max(mx, i.g.share[k] || 0); });
    var sc = (ROWH - 6) / (mx || 1), out = [];
    if (!mob) out.push('<text x="' + (LW - 6) + '" y="17" text-anchor="end">近期趨勢</text><text x="' + (px1 + 8) + '" y="17">占比</text><text x="' + (px1 + 64) + '" y="17">今日占比</text><text x="' + (px1 + 148) + '" y="17">今日漲跌</text><text x="' + (px1 + 212) + '" y="17">累計</text><text x="' + (px1 + 268) + '" y="17">期間占比</text>');
    else out.push('<text x="' + (px1 + 6) + '" y="17">累計</text>');
    items.forEach(function (i) {
      if (i.h) {
        out.push('<text x="0" y="' + (i.y + CH - 5) + '" class="fc3-ch" style="fill:' + catVar(i.r.chain) + '">' + esc(chainName(i.r.chain)) + '・' + i.r.tot.toFixed(1) + '%</text><line x1="0" x2="' + W + '" y1="' + (i.y + CH - 2) + '" y2="' + (i.y + CH - 2) + '" stroke="var(--line)"/>');
        return;
      }
      var g = i.g, cy = i.y + ROWH / 2, on = S.sel === g.gid, dim = S.sel && !on;
      var nm = fitName(g.name, mob ? LW - 14 : LW - 6 - 52 - 12);
      out.push('<g data-g="' + esc(g.gid) + '" class="fc3-row' + (on ? ' on' : '') + '" role="button" tabindex="0" aria-label="' + esc(g.name) + '"><rect x="0" y="' + i.y + '" width="' + W + '" height="' + ROWH + '" class="fc3-rowbg"/>');
      out.push('<text x="6" y="' + (mob ? cy - 2 : cy + 4) + '" class="big"><title>' + esc(g.name) + '</title>' + esc(nm) + '</text>');
      var s0 = g.share[L] || 0, s1 = g.share[t] || 0, arrow = s1 >= s0 ? '↑' : '↓';
      if (mob) out.push('<text x="6" y="' + (cy + 13) + '">占比 ' + s0.toFixed(1) + '→' + s1.toFixed(1) + ' ' + arrow + '</text>');
      else out.push('<text x="' + (LW - 6) + '" y="' + (cy + 4) + '" text-anchor="end">' + (QL[g.q[t]] || '') + '</text>');
      var cc = catVar(g.chain);
      for (var k = L; k < T - 1; k++) {
        var a = g.share[k] || 0, b = g.share[k + 1] || 0;
        out.push('<path d="M' + X(k) + ',' + (cy - a * sc / 2) + 'L' + X(k + 1) + ',' + (cy - b * sc / 2) + 'L' + X(k + 1) + ',' + (cy + b * sc / 2) + 'L' + X(k) + ',' + (cy + a * sc / 2) + 'Z" fill="' + cc + '" opacity="' + (dim ? 0.25 : 0.8) + '"/>');
      }
      var ab = [], mm = [];
      for (var q = L; q < T; q++) { ab.push(rel0(g.cum, q, L)); mm.push(rel0(V.mcum, q, L)); }
      var amp = Math.max.apply(null, [3].concat(ab.map(Math.abs), mm.map(Math.abs))), ct = ab[t - L], lc = vcol(ct);
      var Yv = function (v) { return cy - v / amp * (ROWH / 2 - 3); };
      out.push('<line x1="' + px0 + '" x2="' + px1 + '" y1="' + cy + '" y2="' + cy + '" stroke="var(--line)" stroke-dasharray="2 3"/>'
        + '<polyline fill="none" stroke="var(--ink-3)" stroke-width="1.2" stroke-dasharray="3 3" points="' + mm.map(function (v, j) { return X(L + j) + ',' + Yv(v); }).join(' ') + '"/>'
        + '<polyline fill="none" stroke="' + lc + '" stroke-width="2.2" stroke-linejoin="round" opacity="' + (dim ? 0.5 : 1) + '" points="' + ab.map(function (v, j) { return X(L + j) + ',' + Yv(v); }).join(' ') + '"/>');
      var d = g.dshare[t] || 0, bw = Math.min(32, Math.abs(d) / 2 * 32);
      if (mob) out.push('<text x="' + (px1 + 6) + '" y="' + (cy + 4) + '" class="big" style="fill:' + lc + '">' + f1(ct) + '%</text>');
      else out.push('<text x="' + (px1 + 8) + '" y="' + (cy + 4) + '" class="big">' + s1.toFixed(1) + '%</text>'
        + '<rect x="' + (px1 + 64) + '" y="' + (cy - 5) + '" width="' + Math.max(1, bw) + '" height="10" rx="3" style="fill:' + (d >= 0 ? 'var(--cyan)' : 'var(--amber)') + '"/>'
        + '<text x="' + (px1 + 64 + Math.max(1, bw) + 4) + '" y="' + (cy + 4) + '">' + f2(d) + '</text>'
        + '<text x="' + (px1 + 148) + '" y="' + (cy + 4) + '" class="big" style="fill:' + vcol(g.chg[t]) + '">' + f1(g.chg[t]) + '%</text>'
        + '<text x="' + (px1 + 212) + '" y="' + (cy + 4) + '" class="big" style="fill:' + lc + '">' + f1(ct) + '%</text>'
        + '<text x="' + (px1 + 268) + '" y="' + (cy + 4) + '" class="big">' + s0.toFixed(1) + '→' + s1.toFixed(1) + ' ' + arrow + '</text>');
      out.push('</g>');
    });
    var cx = X(t);
    out.push('<line x1="' + cx + '" x2="' + cx + '" y1="22" y2="' + (H - 18) + '" stroke="var(--amber)" stroke-width="1.5" stroke-dasharray="4 3" pointer-events="none"/>');
    var step = Math.ceil(n / (mob ? 3 : 5));
    for (var k2 = L; k2 < T; k2 += step) out.push('<text x="' + X(k2) + '" y="' + (H - 4) + '" text-anchor="middle">' + mdl(V.dates[k2]) + '</text>');
    el.innerHTML = '<svg width="' + W + '" height="' + H + '" class="fc3-svg" role="img" aria-label="資金河流圖">' + out.join('') + '</svg>';
    $$('g[data-g]', el).forEach(function (e) {
      e.addEventListener('click', function () { select(e.dataset.g); });
      e.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); select(e.dataset.g); } });
      if (!mob) {
        e.addEventListener('mousemove', function (ev) {
          var g = V.by[e.dataset.g], k = Math.max(L, Math.min(T - 1, Math.round(L + (ev.clientX - el.getBoundingClientRect().left - px0) / dx)));
          tip('<b>' + esc(g.name) + '</b>　' + mdl(V.dates[k]) + '<br>占比 ' + p1(g.share[k]) + '%（' + f2(g.dshare[k]) + '）<br>當天 <span class="' + cls(g.chg[k]) + '">' + f1(g.chg[k]) + '%</span>　加權 ' + f1(V.mk[k]) + '%', ev);
        });
        e.addEventListener('mouseleave', function () { tip(null); });
      }
    });
  }

  /* ---- 輪盤 ---- */
  function wheelSvg(W, H, labelN) {
    var t = S.t, tail = 5, lo5 = Math.max(0, t - tail), pad = { l: 44, r: 14, t: 26, b: 34 };
    var pts = V.G.filter(function (g) { return g.mx[t] != null && g.my[t] != null && g.share[t] >= 0.3; });
    var xr = V.fix.x, yr = V.fix.y;
    var X = function (v) { return pad.l + (Math.max(100 - xr, Math.min(100 + xr, v)) - (100 - xr)) / (2 * xr) * (W - pad.l - pad.r); };
    var Y = function (v) { return pad.t + (1 - (Math.max(100 - yr, Math.min(100 + yr, v)) - (100 - yr)) / (2 * yr)) * (H - pad.t - pad.b); };
    var R = function (g) { return Math.max(4, Math.min(22, Math.sqrt(g.share[t]) * 5.2)); };
    var boxes = [[W - pad.r - 70, pad.t, W - pad.r, pad.t + 18], [pad.l, H - pad.b - 20, pad.l + 70, H - pad.b], [pad.l, pad.t, pad.l + 56, pad.t + 18], [W - pad.r - 56, H - pad.b - 20, W - pad.r, H - pad.b]];
    var hit = function (b) { return boxes.some(function (a) { return a[0] < b[2] && b[0] < a[2] && a[1] < b[3] && b[1] < a[3]; }); };
    var lbl = function (g, x, y, r) {
      var nm = g.name.length > 7 ? g.name.slice(0, 7) + '…' : g.name, w = nm.length * 13 + 10;
      var c = [[x, y - r - 4], [x, y + r + 14], [x + r + 4 + w / 2, y + 4], [x - r - 4 - w / 2, y + 4]];
      for (var i = 0; i < c.length; i++) {
        var px = Math.max(pad.l + w / 2, Math.min(W - pad.r - w / 2, c[i][0])), py = Math.max(pad.t + 12, Math.min(H - pad.b - 4, c[i][1])), b = [px - w / 2, py - 12, px + w / 2, py + 3];
        if (!hit(b)) { boxes.push(b); return '<text x="' + px + '" y="' + py + '" text-anchor="middle" class="big fc3-halo">' + esc(nm) + '</text>'; }
      }
      return '';
    };
    var cx = X(100), cy = Y(100), o = [];
    o.push('<rect x="' + cx + '" y="' + pad.t + '" width="' + (W - pad.r - cx) + '" height="' + (cy - pad.t) + '" style="fill:var(--cyan)" opacity=".07"/><rect x="' + pad.l + '" y="' + cy + '" width="' + (cx - pad.l) + '" height="' + (H - pad.b - cy) + '" style="fill:var(--ink-3)" opacity=".07"/>');
    o.push('<line x1="' + pad.l + '" x2="' + (W - pad.r) + '" y1="' + cy + '" y2="' + cy + '" stroke="var(--line-2)"/><line x1="' + cx + '" x2="' + cx + '" y1="' + pad.t + '" y2="' + (H - pad.b) + '" stroke="var(--line-2)"/>');
    o.push('<text x="' + (W - pad.r - 4) + '" y="' + (pad.t + 14) + '" text-anchor="end" class="fc3-qn">持續升溫</text><text x="' + (pad.l + 4) + '" y="' + (H - pad.b - 6) + '" class="fc3-qn">持續降溫</text><text x="' + (pad.l + 4) + '" y="' + (pad.t + 14) + '">降溫放緩</text><text x="' + (W - pad.r - 4) + '" y="' + (H - pad.b - 6) + '" text-anchor="end">升溫放緩</text>');
    o.push('<text x="' + cx + '" y="' + (H - pad.b + 12) + '" text-anchor="middle">100</text>');
    o.push('<text x="' + ((pad.l + W - pad.r) / 2) + '" y="' + (H - 8) + '" text-anchor="middle">資金占比趨勢（近 5 日 ÷ 近 20 日）→</text><text transform="translate(12,' + ((pad.t + H - pad.b) / 2) + ') rotate(-90)" text-anchor="middle">變化速度 →</text>');
    var tn = topN(t, 3), sg = focusG(), lab = {};
    V.G.slice().sort(function (a, b) { return (b.share[t] || 0) - (a.share[t] || 0); }).slice(0, labelN).forEach(function (g) { lab[g.gid] = 1; });
    tn.inn.slice(0, 2).forEach(function (g) { lab[g.gid] = 1; }); if (sg) lab[sg.gid] = 1;
    var tl = {}; tn.inn.forEach(function (g) { tl[g.gid] = 1; }); if (sg) tl[sg.gid] = 1;
    Object.keys(tl).forEach(function (id) {
      var g = V.by[id], p = [];
      for (var k = lo5; k <= t; k++) if (g.mx[k] != null && g.my[k] != null) p.push([X(g.mx[k]), Y(g.my[k])]);
      if (p.length < 2) return;
      var c = catVar(g.chain);
      o.push('<polyline fill="none" stroke="' + c + '" stroke-width="2" opacity=".7" points="' + p.map(function (a) { return a.join(','); }).join(' ') + '"/>'
        + p.slice(0, -1).map(function (a, i) { return '<circle cx="' + a[0] + '" cy="' + a[1] + '" r="' + (1.5 + i / p.length * 2) + '" fill="' + c + '" opacity=".6"/>'; }).join(''));
    });
    var labs = [];
    pts.sort(function (a, b) { return b.share[t] - a.share[t]; }).forEach(function (g) {
      var on = sg && sg.gid === g.gid, dim = S.sel && !on && !lab[g.gid], c = catVar(g.chain), x = X(g.mx[t]), y = Y(g.my[t]), r = R(g);
      o.push('<g data-g="' + esc(g.gid) + '" class="fc3-pt" role="button" tabindex="0" aria-label="' + esc(g.name) + '"><circle cx="' + x + '" cy="' + y + '" r="' + r + '" fill="' + c + '" fill-opacity=".55" style="stroke:' + (on ? 'var(--ink)' : c) + '" stroke-width="' + (on ? 3 : 1.5) + '" opacity="' + (dim ? 0.4 : 1) + '"/>'
        + '</g>');
      if (lab[g.gid]) labs.push(lbl(g, x, y, r));
    });
    o.push('<g pointer-events="none">' + labs.join('') + '</g>');
    return '<svg width="' + W + '" height="' + H + '" class="fc3-svg" role="img" aria-label="資金輪盤">' + o.join('') + '</svg>';
  }
  function miniLine(W, H, g) {
    var L = lo(), t = S.t, T = V.T, pad = { l: 50, r: 52, t: 10, b: 20 }, a = [], m = [];
    for (var k = L; k < T; k++) { a.push(rel0(g.cum, k, L)); m.push(rel0(V.mcum, k, L)); }
    var all2 = a.concat(m), mn = Math.min.apply(null, [0].concat(all2)), mxv = Math.max.apply(null, [0].concat(all2));
    var X = function (k2) { return pad.l + (k2 - L) / Math.max(1, T - 1 - L) * (W - pad.l - pad.r); }, Y = function (v) { return pad.t + (1 - (v - mn) / (mxv - mn || 1)) * (H - pad.t - pad.b); };
    var pl = function (arr, c, w, d) { return '<polyline fill="none" stroke="' + c + '" stroke-width="' + w + '"' + (d ? ' stroke-dasharray="4 3"' : '') + ' points="' + arr.map(function (v, i) { return X(L + i) + ',' + Y(v); }).join(' ') + '"/>'; };
    var gc = vcol(a[a.length - 1]);
    return '<svg width="' + W + '" height="' + H + '" class="fc3-svg fc3-mini" role="img" aria-label="累計走勢對加權指數"><line x1="' + pad.l + '" x2="' + (W - pad.r) + '" y1="' + Y(0) + '" y2="' + Y(0) + '" stroke="var(--line-2)"/>'
      + '<text x="' + (pad.l - 6) + '" y="' + (Y(mxv) + 4) + '" text-anchor="end">' + f1(mxv) + '%</text><text x="' + (pad.l - 6) + '" y="' + (Y(mn) + 4) + '" text-anchor="end">' + f1(mn) + '%</text>'
      + pl(m, 'var(--ink-3)', 1.6, 1) + pl(a, gc, 2.4)
      + '<line x1="' + X(t) + '" x2="' + X(t) + '" y1="' + pad.t + '" y2="' + (H - pad.b) + '" stroke="var(--amber)" stroke-dasharray="4 3"/>'
      + '<text x="' + (W - pad.r + 4) + '" y="' + (Y(a[a.length - 1]) + 4) + '" class="big" style="fill:' + gc + '">' + esc(g.name.slice(0, 4)) + '</text><text x="' + (W - pad.r + 4) + '" y="' + (Y(m[m.length - 1]) + 16) + '">加權</text>'
      + '<text x="' + pad.l + '" y="' + (H - 4) + '">' + mdl(V.dates[L]) + '</text><text x="' + (W - pad.r) + '" y="' + (H - 4) + '" text-anchor="end">' + mdl(V.dates[T - 1]) + '</text></svg>';
  }
  function drawWheel(el) {
    var W = el.clientWidth, mob = W < 640, SW = mob ? 0 : 300, WW = mob ? W : W - SW - 12, H = stageH(), g = focusG(), t = S.t;
    var side = '';
    if (!mob && g) {
      side = '<div class="fc3-side"><div class="fc3-sname">' + esc(g.name) + ' <span class="fc3-mut">' + esc(chainName(g.chain)) + '</span></div>'
        + '<div class="fc3-sline">占比 <b>' + p1(g.share[t]) + '%</b>（' + f2(g.dshare[t]) + '）・今日 <b class="' + cls(g.chg[t]) + '">' + f1(g.chg[t]) + '%</b><br><span class="fc3-mut">加權 ' + f1(V.mk[t]) + '%・' + (QL[g.q[t]] || '') + '</span></div>'
        + miniLine(SW - 8, 170, g) + '<div class="fc3-mut fc3-snote">實線＝' + esc(g.name) + '累計漲跌，虛線＝加權指數；起點 ' + mdl(V.dates[lo()]) + '</div></div>';
    }
    el.innerHTML = '<div class="fc3-wheelwrap"><div style="width:' + WW + 'px">' + wheelSvg(WW, H, mob ? 2 : 3) + '</div>' + (mob ? '' : '<div style="width:' + SW + 'px">' + side + '</div>') + '</div>';
    $$('g[data-g]', el).forEach(function (e) {
      e.addEventListener('click', function () { select(e.dataset.g); });
      e.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); select(e.dataset.g); } });
      if (!mob) {
        e.addEventListener('mousemove', function (ev) {
          var q = V.by[e.dataset.g];
          tip('<b>' + esc(q.name) + '</b>（' + esc(chainName(q.chain)) + '）<br>占比 ' + p1(q.share[t]) + '%（' + f2(q.dshare[t]) + '）<br>當天 <span class="' + cls(q.chg[t]) + '">' + f1(q.chg[t]) + '%</span>・' + (QL[q.q[t]] || ''), ev);
        });
        e.addEventListener('mouseleave', function () { tip(null); });
      }
    });
  }
  function tip(html, ev) {
    var t = $('#fc3Tip'); if (!t) return;
    if (!html) { t.style.display = 'none'; return; }
    t.innerHTML = html; t.style.display = 'block';
    var c = $('#fc3Card').getBoundingClientRect(), x = ev.clientX - c.left + 14, y = ev.clientY - c.top + 18;
    if (x + t.offsetWidth > c.width - 8) x = ev.clientX - c.left - t.offsetWidth - 14;
    t.style.left = Math.max(4, x) + 'px'; t.style.top = y + 'px';
  }

  /* ---------------------------------------------------------------- 今天的訊號（接 next_wave.json） */
  function getNW() {
    if (V.nw !== undefined) return Promise.resolve(V.nw);
    return API.jget('next_wave.json').then(function (j) { V.nw = j && j.methods ? j : false; return V.nw; });
  }
  function instMethod(nw) { return (nw.methods || []).filter(function (m) { return m.id === 'INST10' && m.level === 'group'; })[0] || null; }
  function bearText(nw) {
    var r = (nw.robust || []).filter(function (x) { return x.method === 'group-INST10'; })[0], reg = r && r.regime, k = reg && Object.keys(reg).filter(function (z) { return z.indexOf('空頭') === 0; })[0];
    if (!k || reg[k].spread == null) return '空頭期未驗證';
    return reg[k].spread <= 0 ? '空頭無效' : '空頭效果較弱';
  }
  function drawSignal() {
    var el = $('#fc3Sig'); if (!el) return;
    getNW().then(function (nw) {
      var head = '<span class="fc3-sigk">今天的訊號</span>';
      if (!nw) { el.innerHTML = '<div class="fc3-sigrow">' + head + '<span class="fc3-mut">訊號資料尚未上線</span></div>'; return; }
      var m = instMethod(nw), st = m && m.stats && m.stats['10'] && m.stats['10'].test;
      var cands = ((nw.latest && nw.latest.candidates) || []).filter(function (c) { return c.method === 'group-INST10'; });
      var when = nw.latest && nw.latest.date && V.dates.length && nw.latest.date !== V.dates[V.T - 1] ? '（訊號日 ' + mdl(nw.latest.date) + '）' : '';
      var back = '實驗訊號・近兩年略有利、空頭與 2026 年轉弱';
      var names = cands.slice(0, 3).map(function (c) { return c.name; }).join('、');
      var line = cands.length ? '外資＋投信近 10 日持續買超的族群：' + esc(names) + (cands.length > 3 ? ' 等 ' + cands.length + ' 個' : '') + when : '今天沒有候選族群' + when;
      var s = '<button type="button" class="fc3-sigrow" data-sig="toggle" aria-expanded="' + S.sigOpen + '">' + head + '<span class="fc3-exp">實驗訊號</span>'
        + '<span class="fc3-sigtx">' + line + '<span class="fc3-mut">　近兩年略有利、空頭與 2026 年轉弱</span></span><span class="fc3-car">' + (S.sigOpen ? '收起 ▴' : '看證據 ▾') + '</span></button>';
      if (S.sigOpen) {
        var rowSt = function (h) {
          var z = m && m.stats && m.stats[h] && m.stats[h].test; if (!z) return '';
          return '<tr><td>' + h + ' 日</td><td class="n">' + z.n_eff + '</td><td class="n">' + f2(z.spread) + '%（' + f2(z.spread_ci[0]) + '～' + f2(z.spread_ci[1]) + '）</td><td class="n">' + Math.round(z.hit * 100) + '%（' + Math.round(z.hit_ci[0] * 100) + '～' + Math.round(z.hit_ci[1] * 100) + '%）</td><td class="n">' + f2(z.net) + '%</td></tr>';
        };
        var z5 = m && m.stats && m.stats['5'] && m.stats['5'].test, z10 = st;
        s += '<div class="fc3-evid"><p class="fc3-evh">怎麼選：每個族群近 10 個交易日「外資＋投信淨買超占成交量」排名，前 20% 入選；只看族群，不列個股（個股層檢驗不成立）。</p>'
          + '<ol class="fc3-four"><li>2024～2025 樣本外：10 日比隨機多 ' + (z10 ? f2(z10.spread) : '+0.98') + '%、5 日 ' + (z5 ? f2(z5.spread) : '+0.54') + '%（樣本數 ' + ((z5 || z10) ? (z5 || z10).n_dates : 136) + ' 期）。</li>'
          + '<li>2012～2019 保留樣本：效果只剩約三分之一，扣成本後為負。</li>'
          + '<li>2026 年至今：效果接近零。</li>'
          + '<li>空頭期（大盤 60 日為負）：無效。</li></ol>'
          + '<div class="fc3-tw"><table><thead><tr><th>持有</th><th>樣本期數</th><th>比隨機入選多賺（95% 區間）</th><th>命中率（95% 區間）</th><th>扣成本後</th></tr></thead><tbody>' + rowSt('5') + rowSt('10') + '</tbody></table></div>'
          + '<p class="fc3-evn">樣本外 ' + esc((nw.meta && nw.meta.test_start) || '2024-01-01') + ' 起。今日候選族群：'
          + cands.map(function (c) { return V.by[c.code] ? '<button type="button" class="fc3-lk" data-sig="pick" data-g="' + esc(c.code) + '">' + esc(c.name) + '</button>' : '<span>' + esc(c.name) + '</span>'; }).join('、') + '</p>'
          + '<p class="fc3-evn fc3-mut">' + esc((nw.meta && nw.meta.disclaimer) || '統計研究輔助，不是買賣建議；歷史表現不代表未來。') + ((nw.meta && nw.meta.limits || [])[2] ? '　限制：' + esc(nw.meta.limits[2]) : '') + '</p>'
          + '<button type="button" class="fc3-lk fc3-casesbtn" data-sig="cases">看驗證與案例（成功與失敗各 3 個）▸</button></div>';
      }
      el.innerHTML = s;
    });
  }

  /* ---------------------------------------------------------------- 驗證與案例（進階的一段） */
  /* 6 個案例來自 docs/research/20261101_next_wave_signals.md 第六節「6 個使用案例」：族群綜合分數 A 樣本外的
     最好 12 筆與最差 12 筆裡各挑 3 筆講解；5／20／60 日是相對大盤的超額報酬。nw.cases 讀得到同日同族群就以 json 為準。 */
  var CASES = [
    { ok: true, date: '2026-03-12', name: '前段製程設備', f: [7.5, 66.5, 31.2], why: '月營收年增約 32%、過去約 3 個月只漲 19%（沒有過熱）、法人 10 日淨買約占成交量 9.3%、成交值放大 1.4 倍。', lesson: '基本面與籌碼一起來、價格還沒透支，是最好的組合。' },
    { ok: true, date: '2026-05-12', name: '被動元件 MLCC', f: [22.9, 90.0, 31.6], why: '3 個月漲 23%、法人淨買約 7%、成交值放大 2.5 倍；營收分數不高，主要靠籌碼與量能。', lesson: '它發生在大盤 20 日 +22% 的強勢期，大盤本身也在漲，不能全算訊號的功勞。' },
    { ok: true, date: '2026-01-19', name: 'PCB 載板', f: [8.2, 51.8, 169.8], why: '法人買、成交量放大，但融資同時暴增 61%。', lesson: '融資暴增本來是警訊，這次反而續漲：熱門多頭裡融資增加只是跟風，所以這個假說沒有通過驗證。' },
    { ok: false, date: '2026-03-19', name: 'NOR Flash 利基記憶體', f: [-17.7, -43.9, -22.1], why: '營收年增 147%、3 個月漲 137%；四個月前（2025-12-18）同族群入選，之後 20 日 +46%。', lesson: '基本面數字更漂亮，但價格已經先漲完：同一族群可以前次成功、這次慘敗。' },
    { ok: false, date: '2026-03-12', name: '太陽能產業', f: [-7.4, -42.8, -78.0], why: '3 個月暴漲 197%、成交值放大 2.1 倍，基本面（營收年增 16%、加速 0）跟不上。', lesson: '與「前段製程設備」同一天入選：一檔 +66%、一檔 −43%。榜單只是機率篩選，不是個別預測。' },
    { ok: false, date: '2026-04-13', name: '玻纖布', f: [-0.4, -27.2, -50.9], why: '營收年增 52%、法人持續買，大盤同期 20 日 +12.6%（強勢），族群卻大幅落後。', lesson: '沒有任何單一資料能事先解釋：這就是「訊號失靈」，多數失敗案例找不到單一原因。' }
  ];
  function caseCard(c, nw) {
    var f = c.f.slice();
    ((nw && nw.cases) || []).some(function (z) { if (z.date === c.date && z.name === c.name && z.fwd && z.fwd['20'] != null) { f = [z.fwd['5'], z.fwd['20'], z.fwd['60']]; return true; } return false; });
    var cell = function (lab, v) { return '<span class="fc3-cn"><span class="fc3-mut">' + lab + '</span><b class="' + cls(v) + '">' + f1(v) + '%</b></span>'; };
    return '<article class="fc3-case ' + (c.ok ? 'ok' : 'bad') + '"><div class="fc3-case-h"><b>' + esc(c.name) + '</b><span class="fc3-mut">' + c.date + ' 入選</span></div>'
      + '<div class="fc3-case-n">' + cell('之後 5 日', f[0]) + cell('20 日', f[1]) + cell('60 日', f[2]) + '</div>'
      + '<p><span class="fc3-mut">當時：</span>' + esc(c.why) + '</p><p><span class="fc3-mut">教訓：</span>' + esc(c.lesson) + '</p></article>';
  }
  function renderCases(el) {
    el.innerHTML = '<p class="fc3-mut">載入中…</p>';
    getNW().then(function (nw) {
      var cs = nw && (nw.case_stats || []).filter(function (x) { return x.method === 'group-A' && x.period === '樣本外'; })[0];
      var n = cs ? cs.n : 414, m20 = cs ? cs.mean20 : 1.28, md20 = cs ? cs.median20 : -0.86, w20 = cs ? cs.win20 : 0.459, ci = cs && cs.win20_ci ? cs.win20_ci : [0.412, 0.507];
      var stat = function (k, v, c) { return '<div class="fc3-stat"><span class="fc3-mut">' + k + '</span><b class="' + (c || '') + '">' + v + '</b></div>'; };
      var unt = (nw && nw.meta && nw.meta.untestable) || [];
      el.innerHTML = '<div class="fc3-verdict"><b>工具成效：機率略有利、波動極大，不是穩賺。</b> 我們把「族群綜合分數 A」（基本面＋籌碼＋價量排名）每次新進入前 8 名當成一次訊號，樣本外歷次結果如下，成功失敗都列：</div>'
        + '<div class="fc3-stats">' + stat('樣本外訊號', n + ' 筆') + stat('20 日平均', f2(m20) + '%', cls(m20)) + stat('20 日中位數', f2(md20) + '%', cls(md20)) + stat('20 日勝率', (w20 * 100).toFixed(1) + '%（' + Math.round(ci[0] * 100) + '～' + Math.round(ci[1] * 100) + '%）') + '</div>'
        + '<p class="fc3-mut fc3-readme">白話：少數大贏家撐起平均，多數案例其實輸給大盤（勝率不到一半）；所以它是「篩選觀察名單」的工具，不是買賣依據。下面 6 個案例取自樣本外最好 12 筆與最差 12 筆，各挑 3 筆講解（不是隨機抽樣），數字是相對大盤的超額報酬。</p>'
        + '<div class="fc3-cases"><div class="fc3-col ok"><h4>成功 3 例</h4>' + CASES.filter(function (c) { return c.ok; }).map(function (c) { return caseCard(c, nw); }).join('') + '</div>'
        + '<div class="fc3-col bad"><h4>失敗 3 例</h4>' + CASES.filter(function (c) { return !c.ok; }).map(function (c) { return caseCard(c, nw); }).join('') + '</div></div>'
        + (unt.length ? '<details class="fc3-unt"><summary>還不能驗證的方法（' + unt.length + ' 項，資料累積中）</summary><ul>' + unt.map(function (u) { return '<li><b>' + esc(u.name) + '</b>：' + esc(u.why) + '</li>'; }).join('') + '</ul></details>' : '')
        + '<p class="fc3-mut fc3-readme">' + esc((nw && nw.meta && nw.meta.disclaimer) || '統計研究輔助，不是買賣建議；歷史表現不代表未來。') + ' 樣本約 6.8 年，樣本外 2024 年起以多頭為主，缺完整空頭樣本。</p>';
    });
  }

  /* ---------------------------------------------------------------- 對外 */
  function show(o) {
    var idx = API.idx;
    if (o.v === 'river' || o.v === 'wheel') S.view = o.v;
    if (o.w && [10, 20, 30].indexOf(+o.w) >= 0) S.win = +o.w;
    var go = function () {
      S.win = Math.min(S.win, V.T) || V.T;
      var di = o.d ? V.dates.indexOf(o.d) : -1;
      S.t = Math.max(V.T - S.win, di >= 0 ? di : V.T - 1);
      if (o.g && V.by[o.g]) S.sel = o.g;
      API.date(V.dates[S.t]);
      all(); drawSignal();
    };
    if (V.ready) { go(); return Promise.resolve(); }
    $('#fc3Sent').textContent = '載入近 30 個交易日資料…';
    return load(idx).then(go);
  }
  window.TwFlowV3 = {
    init: function (api, root) { API = api; if (!built) mount(root); },
    show: show,
    leave: function () { stopPlay(); tip(null); },
    renderCases: renderCases,
    setSel: function (gid) { if (V.ready && V.by[gid] && S.sel !== gid) { S.sel = gid; all(); } },
    query: function () { return { v: S.view, w: S.win, d: V.dates[S.t], g: S.sel }; },
    state: function () { return { t: S.t, date: V.dates[S.t], sel: S.sel, win: S.win, view: S.view, playing: !!S.play, T: V.T, stageH: stageH() }; },
    redraw: function () { all(); }
  };
})();
