/* flowcheck4.js —「流向驗證」v4 第一屏：驗證三步驟＋吻合率＋新手導覽
 *
 * Andy 11-01 20:20：「數據有點太多了 看不懂怎麼用，幫我給個導覽吧」「我還是不知道怎麼使用」
 *   「我要的是他可以搭配看 驗證我的數據 因為我的數據之後需要讓人使用」「我們事先提供基礎數據」。
 * 這一頁的目的不是找訊號，是讓使用者自己驗證：我們給的資金數據（資金流入／流出前 3 族群）和族群實際股價走勢對不對得上。
 *   ① 選一天 → ② 我們的數據說（流入前 3／流出前 3）→ ③ 實際股價怎麼走（當天、之後 5 日）＋ ✓／✗ 判定。
 *   最上面一排是吻合率（最近 20／60 個交易日累計）。河流圖、輪盤收進「看細節」，訊號降為最下方的「訂閱功能預覽」。
 *
 * 資料：flowcheck/verify.json（pipeline/compute/flowcheck.py 的 verify()，口徑寫在那裡）。
 *   ⚠ 預覽版讀的是正式站資料，verify.json 在合併 main 之前不存在 → 讀不到就用 day/<日期>.json 在前端算出同一份
 *   （同口徑：占比 ≥ 1%、依今日占比變化排名、之後 5 日＝兩邊日報酬複利後相減、剛好 0 算不吻合）。兩條路徑 _uitest 都驗。
 * 判定只看「方向」：流入且跑贏加權指數、流出且跑輸加權指數＝吻合。吻合率不是 100%，頁面直接寫出來，不修飾。
 * 紅漲綠跌只用在漲跌數字；判定用青（吻合）／琥珀（不吻合），不拿紅綠當對錯。
 */
(function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var esc = function (s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };
  var API = null, root = null, hooks = {};
  var VD = null, loading = null, seq = 0;
  var S = { d: null, win: 60, open: null };
  var SEEN = 'fc.tour4';
  var f1 = function (v) { return v == null || !isFinite(v) ? '—' : (v > 0 ? '+' : '') + (Math.round(+v * 10 + 1e-9 * Math.sign(v)) / 10).toFixed(1); };
  var f2 = function (v) { return v == null || !isFinite(v) ? '—' : (v > 0 ? '+' : '') + (Math.round(+v * 100 + 1e-9 * Math.sign(v)) / 100).toFixed(2); };
  var p1 = function (v) { return v == null || !isFinite(v) ? '—' : (+v).toFixed(1); };
  var cls = function (v) { return v == null || !isFinite(v) || v === 0 ? '' : (v > 0 ? 'fc3-up' : 'fc3-dn'); };
  var mdl = function (d) { return d.slice(5).replace('-', '/'); };
  var weekday = function (d) { return '日一二三四五六'[new Date(d + 'T00:00:00+08:00').getDay()]; };
  var gInfo = function (gid) { var gs = (API && API.idx && API.idx.groups) || []; for (var i = 0; i < gs.length; i++) if (gs[i].gid === gid) return gs[i]; return { gid: gid, name: gid }; };

  /* ---------------------------------------------------------------- 資料 */
  function compound(a) {                       // 日報酬（%）複利成總報酬（%）；任何一天缺值就 null（不補 0）
    var c = 1;
    for (var i = 0; i < a.length; i++) { if (a[i] == null || !isFinite(a[i])) return null; c *= 1 + a[i] / 100; }
    return a.length ? (c - 1) * 100 : null;
  }
  function hit(rows, key, pos) {
    var n = 0, k = 0;
    rows.forEach(function (r) { var v = r[key]; if (v == null) return; n++; if (pos ? v > 0 : v < 0) k++; });
    return { n: n, k: k };
  }
  function stats(vd) {
    var o = {};
    [20, 60].forEach(function (w) {
      var ds = vd.dates.slice(-w), inn = [], out = [];
      ds.forEach(function (d) { inn = inn.concat(vd.days[d].inn); out = out.concat(vd.days[d].out); });
      o[w] = { days: ds.length, from: ds[0], to: ds[ds.length - 1], inn_day: hit(inn, 'rel', true), out_day: hit(out, 'rel', false), inn_f5: hit(inn, 'rel5', true), out_f5: hit(out, 'rel5', false) };
    });
    return o;
  }
  /* verify.json 不存在（預覽版吃正式站資料）時：用 day 檔在前端算，口徑與 pipeline/compute/flowcheck.py verify() 一致 */
  function fromDays(idx) {
    var ds = (idx.dates || []).slice(), gs = (idx.groups || []).filter(function (g) { return !g.is_bucket; });
    return Promise.all(ds.map(function (d) { return API.getDay(d); })).then(function (days) {
      var days_ = {}, FWD = 5;
      ds.forEach(function (d, i) {
        var dy = days[i]; if (!dy || !dy.groups) return;
        var rows = gs.map(function (g) { var r = dy.groups[g.gid]; return r ? { g: g.gid, r: r } : null; })
          .filter(function (x) { return x && x.r.share >= 1 && x.r.dshare != null; }).sort(function (a, b) { return b.r.dshare - a.r.dshare; });
        var inn = rows.slice(0, 3), ids = {}; inn.forEach(function (x) { ids[x.g] = 1; });
        var out = rows.slice().reverse().filter(function (x) { return !ids[x.g]; }).slice(0, 3);
        var mk = function (x) {
          var g5 = null, m5 = null;
          if (i + FWD < ds.length) {
            var gl = [], ml = [];
            for (var k = i + 1; k <= i + FWD; k++) { var dk = days[k], rk = dk && dk.groups && dk.groups[x.g]; gl.push(rk ? rk.chg : null); ml.push(dk ? dk.mkt_chg : null); }
            g5 = compound(gl); m5 = compound(ml); if (g5 == null || m5 == null) { g5 = null; m5 = null; }
          }
          return { gid: x.g, share: x.r.share, dshare: x.r.dshare, chg: x.r.chg, rel: x.r.rel, f5: g5, m5: m5, rel5: g5 == null ? null : g5 - m5 };
        };
        days_[d] = { mkt: dy.mkt_chg, inn: inn.map(mk), out: out.map(mk) };
      });
      var have = ds.filter(function (d) { return days_[d]; });
      var vd = { schema: 1, src: 'day', dates: have, topn: 3, fwd: FWD, min_share: 1, min_n: 30, days: days_ };
      vd.stats = {}; var st = have.length ? stats(vd) : {}; vd.stats = st;
      return vd;
    });
  }
  function ensure() {
    if (VD) return Promise.resolve(VD);
    if (loading) return loading;
    loading = API.jget('verify.json').then(function (j) {
      if (j && j.dates && j.dates.length && j.days) { j.src = 'verify'; return j; }
      return fromDays(API.idx);
    }).then(function (vd) { VD = vd; loading = null; return vd; });
    return loading;
  }

  /* ---------------------------------------------------------------- 骨架 */
  function mount(el) {
    root = el;
    el.innerHTML =
      '<section class="card fc4" id="fc4Card" aria-label="驗證三步驟">'
      + API.howDiv('v4')
      + '<div class="fc4-hit" id="fc4Hit"></div>'
      + '<div class="fc4-s1" id="fc4S1">'
      +   '<span class="fc4-no">1</span><span class="fc4-sl">選一天</span>'
      +   '<button type="button" class="fc4-nav" id="fc4Prev" aria-label="前一個交易日">◀</button>'
      +   '<select id="fc4Date" aria-label="日期"></select>'
      +   '<button type="button" class="fc4-nav" id="fc4Next" aria-label="後一個交易日">▶</button>'
      +   '<button type="button" class="fc4-latest" id="fc4Latest">回最新</button>'
      +   '<span class="fc4-sp"></span>'
      +   '<button type="button" class="fc4-tourbtn" id="fc4Tour" aria-label="重看新手導覽">? 導覽</button>' + API.howBox('v4')
      + '</div>'
      + '<div class="fc4-cols" id="fc4Cols"></div>'
      + '</section>';
    el.addEventListener('click', onClick);
    el.addEventListener('keydown', function (e) {
      if ((e.key === 'Enter' || e.key === ' ') && e.target.classList && e.target.classList.contains('fc4-row')) { e.preventDefault(); toggle(e.target.dataset.gid); }
    });
    $('#fc4Date').addEventListener('change', function (e) { setDate(e.target.value); });
  }
  function onClick(e) {
    var b = e.target.closest('button,a,[data-gid]'); if (!b) return;
    if (b.id === 'fc4Prev') return step(-1);
    if (b.id === 'fc4Next') return step(1);
    if (b.id === 'fc4Latest') return setDate(VD.dates[VD.dates.length - 1]);
    if (b.id === 'fc4Tour') return startTour(true);
    if (b.dataset.win) { S.win = +b.dataset.win; drawHit(); return; }
    if (b.dataset.act === 'river') { if (hooks.river) hooks.river(b.dataset.g); return; }
    if (b.tagName === 'A') return;
    var row = e.target.closest('.fc4-row'); if (row) toggle(row.dataset.gid);
  }
  function step(k) { var i = VD.dates.indexOf(S.d) + k; if (i >= 0 && i < VD.dates.length) setDate(VD.dates[i]); }
  function setDate(d, quiet) {
    if (!VD || VD.dates.indexOf(d) < 0) return;
    S.d = d; S.open = null;
    drawDate(); drawCols();
    if (!quiet && hooks.date) hooks.date(d);
  }

  /* ---------------------------------------------------------------- 吻合率 */
  function tile(label, h, extra) {
    var low = h.n < (VD.min_n || 30), pct = h.n ? Math.round(h.k / h.n * 100) : null;
    return '<div class="fc4-tile' + (low ? ' low' : '') + '"><span class="fc4-tl">' + label + '</span>'
      + '<b class="fc4-tv">' + (pct == null ? '—' : pct + '%') + '</b>'
      + '<span class="fc4-ts">' + (h.n ? h.k + '／' + h.n + ' 筆' : '沒有樣本') + (low && h.n ? '・樣本不足' : '') + '</span></div>';
  }
  function drawHit() {
    var st = VD.stats && VD.stats[S.win] ? VD.stats[S.win] : null;
    if (!st) { $('#fc4Hit').innerHTML = ''; return; }
    var short = st.days < S.win;
    $('#fc4Hit').innerHTML =
      '<div class="fc4-hh"><b>吻合率</b><span class="fc4-mut">最近 ' + st.days + ' 個交易日（' + mdl(st.from) + '～' + mdl(st.to) + '）每天流入前 3、流出前 3 的累計' + (short ? '，資料只有這麼多' : '') + '</span>'
      + '<span class="fc4-sp"></span><div class="seg" id="fc4Win" role="group" aria-label="吻合率期間">'
      + [20, 60].map(function (n) { return '<button type="button" data-win="' + n + '" class="' + (n === S.win ? 'on' : '') + '" aria-pressed="' + (n === S.win) + '">' + n + ' 日</button>'; }).join('') + '</div></div>'
      + '<div class="fc4-tiles">'
      + tile('流入前 3・當天跑贏加權', st.inn_day) + tile('流入前 3・之後 5 日跑贏加權', st.inn_f5)
      + tile('流出前 3・當天跑輸加權', st.out_day) + tile('流出前 3・之後 5 日跑輸加權', st.out_f5)
      + '</div><div class="fc4-hn fc4-mut">隨機猜大約 50%；沒有哪一格會是 100%，數字高低請自己判斷。</div>';
  }

  /* ---------------------------------------------------------------- 日期列 */
  function drawDate() {
    var ds = VD.dates, i = ds.indexOf(S.d), sel = $('#fc4Date'), mob = !!(window.matchMedia && window.matchMedia('(max-width:640px)').matches);
    sel.innerHTML = ds.slice().reverse().map(function (d) { return '<option value="' + d + '"' + (d === S.d ? ' selected' : '') + '>' + (mob ? mdl(d) : d) + '（' + weekday(d) + '）</option>'; }).join('');
    $('#fc4Prev').disabled = i <= 0; $('#fc4Next').disabled = i >= ds.length - 1;
    $('#fc4Latest').style.visibility = i < ds.length - 1 ? 'visible' : 'hidden';
  }

  /* ---------------------------------------------------------------- 小卡（② 資金數據＋③ 實際股價＋判定） */
  function verdict(kind, rel) {              // kind: 'inn'｜'out'；rel 相對加權（百分點）。null＝無法判
    if (rel == null) return null;
    return kind === 'inn' ? rel > 0 : rel < 0;
  }
  function badge(lab, v) {
    return '<span class="fc4-v ' + (v == null ? 'na' : v ? 'ok' : 'bad') + '">' + lab + ' ' + (v == null ? '—' : v ? '✓' : '✗') + '</span>';
  }
  function sentence(kind, r) {
    var who = kind === 'inn' ? '資金流入' : '資金流出', dsh = r.dshare == null ? '' : '（占比比前一天' + (r.dshare >= 0 ? '多' : '少') + ' ' + Math.abs(r.dshare).toFixed(2) + ' 個百分點）';
    var cmp = function (rel, when) {
      if (rel == null) return when + '還沒有可比的資料';
      var strong = rel > 0, v = verdict(kind, rel);
      return when + '比加權指數' + (strong ? '強' : '弱') + ' ' + Math.abs(rel).toFixed(2) + ' 個百分點，' + (v ? '方向吻合' : '方向不吻合');
    };
    return who + dsh + '；' + cmp(r.rel, '當天') + '；' + (r.rel5 == null ? '之後 5 日還沒滿 5 個交易日，等資料到齊才判' : cmp(r.rel5, '之後 5 日'));
  }
  function rowHTML(kind, r, i) {
    var gi = gInfo(r.gid), on = S.open === r.gid, v1 = verdict(kind, r.rel), v5 = verdict(kind, r.rel5);
    return '<div class="fc4-item' + (on ? ' open' : '') + '" data-gid="' + esc(r.gid) + '">'
      + '<div class="fc4-row" role="button" tabindex="0" aria-expanded="' + on + '" data-gid="' + esc(r.gid) + '" title="點一下展開走勢">'
      +   '<span class="fc4-nm"><span class="fc4-rk">' + (kind === 'inn' ? '入' : '出') + (i + 1) + '</span><b>' + esc(gi.name) + '</b><span class="fc4-car">' + (on ? '▴' : '▾') + '</span></span>'
      +   '<span class="fc4-c fc4-c2"><span class="fc4-cl">占比</span>' + p1(r.share) + '%<span class="fc4-mut fc4-dsh">（' + f2(r.dshare) + '）</span></span>'
      +   '<span class="fc4-c fc4-c3"><span class="fc4-cl">當天</span><b class="' + cls(r.chg) + '">' + f1(r.chg) + '%</b></span>'
      +   '<span class="fc4-c fc4-c4"><span class="fc4-cl">之後 5 日</span>' + (r.f5 == null ? '<span class="fc4-mut"><span class="fc4-nfl">未滿 5 日</span><span class="fc4-nfs">未滿</span></span>' : '<b class="' + cls(r.f5) + '">' + f1(r.f5) + '%</b>') + '</span>'
      +   '<span class="fc4-c fc4-c5">' + badge('當天', v1) + badge('5 日', v5) + '</span>'
      +   '<span class="fc4-say">' + esc(sentence(kind, r)) + '</span>'
      + '</div>'
      + '<div class="fc4-panel" hidden></div></div>';
  }
  function drawCols() {
    var day = VD.days[S.d], el = $('#fc4Cols');
    if (!day) { el.innerHTML = '<div class="fc4-none">這一天沒有資料</div>'; return; }
    var sec = function (id, kind, title, rows) {
      return '<div class="fc4-sec" id="' + id + '"><div class="fc4-sh">' + title + '</div>'
        + (rows.length ? rows.map(function (r, i) { return rowHTML(kind, r, i); }).join('') : '<div class="fc4-none">這天沒有占比 ≥ 1% 的族群</div>') + '</div>';
    };
    el.innerHTML =
      '<div class="fc4-gh" aria-hidden="true"><span class="fc4-g2"><span class="fc4-no">2</span>我們的數據說</span><span class="fc4-g3"><span class="fc4-no">3</span>實際股價怎麼走（加權指數當天 <b class="' + cls(day.mkt) + '">' + f1(day.mkt) + '%</b>）</span>'
      + '<span class="fc4-gc c1">族群</span><span class="fc4-gc c2">占比（較前一天）</span><span class="fc4-gc c3">當天漲跌</span><span class="fc4-gc c4">之後 5 日漲跌</span><span class="fc4-gc c5">判定（✓＝方向吻合）</span></div>'
      + sec('fc4Inn', 'inn', '資金流入前 3<span class="fc4-sx">（今天占比比前一天增加最多）</span>', day.inn)
      + sec('fc4Out', 'out', '資金流出前 3<span class="fc4-sx">（今天占比比前一天減少最多）</span>', day.out);
    drawHit();
  }

  /* ---------------------------------------------------------------- 展開：走勢＋資金占比疊圖 */
  function toggle(gid) {
    if (!gid) return;
    var was = S.open === gid; S.open = was ? null : gid;
    $$('.fc4-item', root).forEach(function (it) {
      var on = it.dataset.gid === S.open, p = $('.fc4-panel', it), row = $('.fc4-row', it);
      it.classList.toggle('open', on); row.setAttribute('aria-expanded', on); $('.fc4-car', it).textContent = on ? '▴' : '▾';
      p.hidden = !on; if (!on) p.innerHTML = '';
    });
    if (S.open) {
      drawPanel(S.open);
    }
  }
  function drawPanel(gid) {
    var it = $('.fc4-item[data-gid="' + CSS.escape(gid) + '"]', root); if (!it) return;
    var day = VD.days[S.d], kind = day.inn.some(function (r) { return r.gid === gid; }) ? 'inn' : 'out';
    var r = (kind === 'inn' ? day.inn : day.out).filter(function (x) { return x.gid === gid; })[0], gi = gInfo(gid), p = $('.fc4-panel', it), my = ++seq;
    p.innerHTML = '<p class="fc4-ps">' + esc(sentence(kind, r)) + '。</p>'
      + '<div class="fc4-chart chart" aria-label="' + esc(gi.name) + ' 走勢與資金占比"></div>'
      + '<div class="fc4-pl"><span class="fc4-mut">線＝累計漲跌（以選的這天收盤為 0；青線族群、灰線加權），底下長條＝資金占比，虛線＝選的這天</span>'
      + '<a class="fc4-lk" href="#industry/group/' + encodeURIComponent(gid) + '">進「' + esc(gi.name) + '」族群頁 →</a>'
      + '<button type="button" class="fc4-lkb" data-act="river" data-g="' + esc(gid) + '">在資金河流圖看它</button></div>';
    API.jget('series/' + encodeURIComponent(gid) + '.json').then(function (ser) {
      if (my !== seq || S.open !== gid) return;
      var el = $('.fc4-chart', p); if (!el) return;
      var a = API.A();
      if (!ser || !ser.dates) { if (a.empty) a.empty(el, '沒有這個族群的日線序列'); return; }
      var iD = ser.dates.indexOf(S.d); if (iD < 0) { if (a.empty) a.empty(el, '這一天沒有走勢序列'); return; }
      var i0 = Math.max(0, iD - 20), i1 = Math.min(ser.dates.length - 1, iD + 10), xs = ser.dates.slice(i0, i1 + 1);
      var bi = ser.idx.map(function (v, k) { return ser.idx_rel[k] ? v / ser.idx_rel[k] * 100 : null; });
      var rb = function (arr) { var b = arr[iD]; return arr.slice(i0, i1 + 1).map(function (v) { return v == null || !b ? null : Math.round((v / b - 1) * 10000) / 100; }); };
      var gl = rb(ser.idx), ml = rb(bi), sh = ser.share.slice(i0, i1 + 1), ch = a.CH, lab = function (v) { return v.length > 5 ? v.slice(5) : v; };
      var cur = { silent: true, symbol: 'none', lineStyle: { color: ch.ink, type: 'dashed' }, label: { show: false }, data: [{ xAxis: S.d }] };
      var after = { silent: true, itemStyle: { color: 'rgba(128,128,128,.10)' }, data: [[{ xAxis: S.d }, { xAxis: xs[xs.length - 1] }]] };
      var opt = {
        animationDurationUpdate: 250, textStyle: { color: ch.ink2 },
        tooltip: Object.assign({}, a.tip, { trigger: 'axis', axisPointer: { type: 'line' }, formatter: function (ps) {
          var h = '<b>' + esc(ps[0].axisValue) + (ps[0].axisValue === S.d ? '（選的這天）' : '') + '</b>';
          ps.forEach(function (q) { h += '<br>' + q.marker + esc(q.seriesName) + ' ' + (q.seriesName === '資金占比' ? p1(q.value) + '%' : f2(q.value) + '%'); }); return h; } }),
        grid: [{ left: 48, right: 16, top: 12, height: '56%' }, { left: 48, right: 16, top: '74%', height: '14%' }],
        xAxis: [Object.assign({ type: 'category', data: xs, gridIndex: 0, boundaryGap: false, axisLabel: { show: false } }, { axisLine: a.axisStyle.axisLine }),
          Object.assign({ type: 'category', data: xs, gridIndex: 1, boundaryGap: true }, a.axisStyle, { splitLine: { show: false }, axisLabel: Object.assign({}, a.axisStyle.axisLabel, { interval: Math.max(0, Math.round(xs.length / 6) - 1), formatter: lab }) })],
        yAxis: [Object.assign({ type: 'value', gridIndex: 0, scale: true, axisLabel: Object.assign({}, a.axisStyle.axisLabel, { formatter: '{value}%' }) }, { splitLine: a.axisStyle.splitLine }),
          { type: 'value', gridIndex: 1, splitNumber: 1, scale: true, axisLabel: { show: false }, axisTick: { show: false }, axisLine: { show: false }, splitLine: { show: false } }],
        series: [
          { name: gi.name, type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: gl, showSymbol: false, lineStyle: { color: ch.cyan, width: 2 }, itemStyle: { color: ch.cyan }, markLine: cur, markArea: after },
          { name: '加權指數', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: ml, showSymbol: false, lineStyle: { color: ch.ink3, width: 1.5, type: 'dashed' }, itemStyle: { color: ch.ink3 } },
          { name: '資金占比', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: sh, barMaxWidth: 10, itemStyle: { color: ch.amber }, markLine: cur }
        ]
      };
      a.chart(el, opt, { notMerge: true });
    });
  }

  /* ---------------------------------------------------------------- 導覽 */
  function startTour(force) {
    if (!window.TwTour) return false;
    try { localStorage.setItem(SEEN, '1'); } catch (e) { /* 私密視窗 */ }
    if (hooks.beforeTour) hooks.beforeTour();
    window.TwTour.start('flowcheck');
    return true;
  }
  function maybeAutoTour() {
    var seen = false; try { seen = localStorage.getItem(SEEN) === '1'; } catch (e) { seen = false; }
    if (seen || !window.TwTour) return;
    setTimeout(function () {
      var tw = window.TwTour.state ? window.TwTour.state() : {};
      var banner = document.getElementById('lgBanner'), bannerOn = banner && banner.getBoundingClientRect().height > 0;
      if (tw.active || bannerOn || !$('#fc4Card') || !$('#fc4Card').offsetParent || location.hash.indexOf('#flowcheck') !== 0) return;   // 全站導覽或同意橫幅還在：這次先不跳，下次進來再說
      startTour(false);
    }, 1200);
  }

  /* ---------------------------------------------------------------- 對外 */
  /* 預設日期＝最近一個「已經有之後 5 日結果」的交易日：第一眼就看得到 ✓／✗（最新那天的 5 日還沒發生，全是「未滿 5 日」）。
     網址帶 d= 時以網址為準；最新日用 ▶ 或「回最新」切過去。 */
  function defaultDate(vd) {
    for (var i = vd.dates.length - 1; i >= 0; i--) {
      var day = vd.days[vd.dates[i]];
      if (day && day.inn.concat(day.out).some(function (r) { return r.rel5 != null; })) return vd.dates[i];
    }
    return vd.dates[vd.dates.length - 1];
  }
  function show(want) {
    return ensure().then(function (vd) {
      if (!vd.dates.length) { $('#fc4Cols').innerHTML = '<div class="fc4-none">驗證資料尚未上線</div>'; return; }
      var d = want && vd.dates.indexOf(want) >= 0 ? want : (S.d && vd.dates.indexOf(S.d) >= 0 ? S.d : defaultDate(vd));
      S.d = d; S.open = null; drawDate(); drawCols();
      if (hooks.date) hooks.date(d);
      maybeAutoTour();
    });
  }
  window.TwFlowV4 = {
    init: function (api, el, h) { API = api; hooks = h || {}; if (!root) mount(el); },
    show: show,
    date: function () { return S.d; },
    onDate: function (d) { if (VD && d !== S.d && VD.dates.indexOf(d) >= 0) setDate(d, true); },
    startTour: startTour,
    state: function () { return { d: S.d, win: S.win, open: S.open, src: VD && VD.src, n: VD ? VD.dates.length : 0 }; }
  };
})();
