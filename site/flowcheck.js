/* flowcheck.js —「流向驗證」獨立分頁（#flowcheck），規格 docs/design/20261030_flow_verify_page.md
 *
 * Andy 10-30 晚：「為何沒有對應的個股走勢圖在旁邊可以看」「需要我方便去比對才能知道目前輪動、流向是否與族群走勢吻合」
 *   「獨立一個分頁將輪盤、資金樹都個別拉出來與走勢圖比較」「有辦法撈取過去歷史紀錄某天的流向狀況進行回測驗證」。
 *
 * 核心：全頁只有一個焦點狀態 S＝{gid 族群, date 日期, t 時間, view 輪盤種類}，寫進網址 #flowcheck?g=&d=&t=&v=。
 *   點輪盤的點／樹節點／熱力方塊／焦點籤／成分股表列＝改 gid；拖時間軸、按播放＝改 t；日期選擇器＝改 date。
 *   每次改狀態都走 paint()：輪盤、熱力圖、走勢大圖、成分股小圖、表、訊號、新聞、法人一起換（同步），不各畫各的。
 * 資料：data/flowcheck/{index, day/<日期>, m5/<日期>, series/<族群>, backtest}.json（規格第七節）；
 *   欄位名集中在 norm*() 一處，真資料欄位若與規格有出入只改那裡。
 * 吻合／背離公式只有 judge() 一份（規格第三節），結論列、輪盤外環、熱力框、走勢籤都吃它。
 * 繪圖一律走 App.chart()（ResizeObserver、0×0 自修）；紅漲綠跌讀 App.CH（切主題會就地換色）。
 */
(function () {
  'use strict';
  var A = function () { return window.App; };
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var esc = function (s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };
  var DB = 'data/flowcheck/';
  var TH = { r: 0.3, top: 0.3, fEps: 0.05, crash: -1.5 };      // 背離門檻（規格第三節：先定的預設值，回測後再調）
  var CATS = [['all', '全部族群'], ['semi', '半導體'], ['ai', 'AI 伺服器'], ['other', '其他']];
  var C = { idx: null, day: {}, m5: {}, ser: {}, bt: null, fail: {} };
  var S = { gid: null, date: null, t: 'close', view: 'money', cat: 'all', cmp: 'rel', span: 'auto' };
  var built = false, seq = 0, playT = null, playSpd = 1;
  var open = {};                  // 手機收展（使用者手動展開才記住）
  try { open = JSON.parse(localStorage.getItem('fc.open') || '{}') || {}; } catch (e) { open = {}; }
  var isM = function () { return window.matchMedia && window.matchMedia('(max-width:640px)').matches; };

  /* ---------------------------------------------------------------- 資料 */
  function jget(path) {
    if (C.fail[path]) return Promise.resolve(null);
    return fetch(DB + path + '?v=' + ((C.idx && C.idx.updated_at) || ''), { cache: 'no-cache' })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .catch(function () { C.fail[path] = 1; return null; });
  }
  function getDay(d) { if (C.day[d] !== undefined) return Promise.resolve(C.day[d]); return jget('day/' + d + '.json').then(function (j) { C.day[d] = j; return j; }); }
  function getM5(d) { if (C.m5[d] !== undefined) return Promise.resolve(C.m5[d]); return jget('m5/' + d + '.json').then(function (j) { C.m5[d] = j; return j; }); }
  function getSer(g) { if (C.ser[g] !== undefined) return Promise.resolve(C.ser[g]); return jget('series/' + encodeURIComponent(g) + '.json').then(function (j) { C.ser[g] = j; return j; }); }
  function layersOf(d) { return (C.idx && C.idx.layers && C.idx.layers[d]) || ['daily']; }
  var chainCat = function (ch) { return ch === 'semiconductor' ? 'semi' : ch === 'ai_server' ? 'ai' : 'other'; };
  var gInfo = function (gid) { return (C.idx.groups || []).filter(function (g) { return g.gid === gid; })[0] || { gid: gid, name: gid, members: [] }; };
  var f2 = function (v, n) { return v == null || !isFinite(v) ? '—' : (+v).toFixed(n == null ? 2 : n); };
  var sg = function (v, n, u) { return v == null || !isFinite(v) ? '—' : (v >= 0 ? '+' : '') + (+v).toFixed(n == null ? 2 : n) + (u || ''); };
  var col = function (v) { var c = A().CH; return v > 0 ? c.up : v < 0 ? c.down : c.ink3; };
  var weekday = function (d) { return '日一二三四五六'[new Date(d + 'T00:00:00+08:00').getDay()]; };

  /* ---------------------------------------------------------------- 網址 */
  function readUrl() {
    var h = decodeURIComponent(location.hash.replace(/^#/, '')), q = h.indexOf('?') >= 0 ? h.slice(h.indexOf('?') + 1) : '', o = {};
    q.split('&').forEach(function (p) { var k = p.split('=')[0], v = p.slice(k.length + 1); if (k) o[k] = v; });
    return o;
  }
  function writeUrl(push) {
    var q = [];
    if (S.gid) q.push('g=' + encodeURIComponent(S.gid));
    if (S.date) q.push('d=' + S.date);
    if (S.t && S.t !== 'close') q.push('t=' + S.t.replace(':', ''));
    if (S.view !== 'money') q.push('v=' + S.view);
    var u = '#flowcheck' + (q.length ? '?' + q.join('&') : '');
    if (u === location.hash) return;
    try { (push ? history.pushState : history.replaceState).call(history, null, '', u); } catch (e) { /* 預覽環境 */ }
  }

  /* ---------------------------------------------------------------- 某日某時的「每族群一列」 */
  function slotList(d) {                   // 這一天有哪些盤中時點：{kind:'m5'|'m60', times:[…]}
    var L = layersOf(d), m5 = C.m5[d], dy = C.day[d];
    if (L.indexOf('m5') >= 0 && m5 && m5.slots) return { kind: 'm5', times: m5.slots };
    if (L.indexOf('m60') >= 0 && dy && dy.m60 && dy.m60.times) return { kind: 'm60', times: dy.m60.times };
    return { kind: 'none', times: [] };
  }
  function tIndex(d) { var sl = slotList(d); if (S.t === 'close' || !sl.times.length) return -1; var i = sl.times.indexOf(S.t); return i; }
  function rowsAt() {
    var dy = C.day[S.date]; if (!dy) return [];
    var sl = slotList(S.date), ti = tIndex(S.date), m5 = C.m5[S.date], out = [];
    (C.idx.groups || []).forEach(function (g) {
      if (g.is_bucket) return;
      var d = dy.groups[g.gid]; if (!d) return;
      var x = { gid: g.gid, name: g.name, chain: g.chain, chainName: g.chain_name || g.chain, cat: chainCat(g.chain), members: g.members, tv: d.tv, share: d.share, rot: d.rot, rsx: d.rs_x, rsy: d.rs_y,
        trail: d.m_trail || [], inst: d.inst, f: d.dshare, r: d.rel, chg: d.chg, adv: d.adv, dec: d.dec, intra: false };
      if (ti >= 0) {
        var s = null;
        if (sl.kind === 'm5' && m5 && m5.groups[g.gid]) { var q = m5.groups[g.gid]; s = { f: q.share[ti], r: q.idx_rel[ti], chg: q.chg[ti], adv: q.adv[ti], dec: q.dec[ti] }; }
        if (sl.kind === 'm60' && dy.m60 && dy.m60.groups[g.gid]) { var q6 = dy.m60.groups[g.gid]; s = { f: q6.share[ti], r: q6.idx_rel[ti] }; }
        if (s) { x.f = s.f; x.r = s.r; if (s.chg != null) { x.chg = s.chg; x.adv = s.adv; x.dec = s.dec; } x.intra = true; }
      }
      x.mx = x.rot; x.my = x.f;
      out.push(x);
    });
    return out;
  }
  function catRows(rows) { return S.cat === 'all' ? rows : rows.filter(function (x) { return x.cat === S.cat; }); }

  /* ---------------------------------------------------------------- 吻合／背離（規格第三節，唯一一份公式） */
  function judge(rows) {
    var n = rows.length; if (!n) return { score: null, ic: null, nSig: 0, fit: 0 };
    var fs = rows.map(function (x) { return x.f; }).sort(function (a, b) { return b - a; });
    var k = Math.max(1, Math.round(n * TH.top)), hi = fs[k - 1], lo = fs[n - k];
    var fit = 0, sig = 0;
    rows.forEach(function (x) {
      var s = Math.abs(x.f) >= TH.fEps || Math.abs(x.r) >= TH.r;
      x.div = (x.f >= hi && x.r < -TH.r) ? 'A' : (x.r > TH.r && x.f <= lo) ? 'B' : null;
      var same = (x.f > 0 && x.r > 0) || (x.f < 0 && x.r < 0);
      x.fit = x.div ? 'div' : (s && same) ? 'fit' : 'mid';
      if (s) { sig++; if (same && !x.div) fit++; }
    });
    return { score: sig ? fit / sig : null, ic: spearman(rows.map(function (x) { return x.f; }), rows.map(function (x) { return x.r; })), nSig: sig, fit: fit };
  }
  function rank(a) { var o = a.map(function (v, i) { return [v, i]; }).sort(function (x, y) { return x[0] - y[0]; }), r = []; o.forEach(function (p, i) { r[p[1]] = i; }); return r; }
  function spearman(a, b) {
    var n = a.length; if (n < 5) return null;
    var ra = rank(a), rb = rank(b), ma = (n - 1) / 2, num = 0, da = 0, db = 0;
    for (var i = 0; i < n; i++) { num += (ra[i] - ma) * (rb[i] - ma); da += Math.pow(ra[i] - ma, 2); db += Math.pow(rb[i] - ma, 2); }
    return da && db ? num / Math.sqrt(da * db) : null;
  }
  function tagOf(x) {
    if (x.div === 'A') return { k: 'div', txt: '背離：資金進、相對大盤 ' + sg(x.r, 1, '%') };
    if (x.div === 'B') return { k: 'div', txt: '背離：走勢強、資金退（相對大盤 ' + sg(x.r, 1, '%') + '）' };
    if (x.fit === 'fit') return { k: 'fit', txt: '吻合：資金' + (x.f >= 0 ? '進' : '退') + '、相對大盤 ' + sg(x.r, 1, '%') };
    return { k: 'mid', txt: '中性：資金 ' + sg(x.f, 2, 'pp') + '、相對大盤 ' + sg(x.r, 1, '%') };
  }

  /* ---------------------------------------------------------------- 骨架 */
  var HOWS = {
    page: ['這一頁在做什麼',
      ['<b>用途</b>：把「錢往哪跑」（輪盤、資金樹）跟「那個族群真的有沒有漲」（走勢、成分股）放在同一個畫面，一點就全部同步，不用自己來回比對。',
        '<b>點</b>輪盤的點、樹的節點、熱力方塊、焦點籤、背離榜或成分股列＝換焦點族群，右邊走勢、成分股、新聞、法人、訊號一起換。',
        '<b>拖</b>底下的時間軸或按播放＝看當天（或歷史每一天）的演變，輪盤點、熱力色、走勢游標同步移動。',
        '<b>日期</b>：「歷史回放」可選過去的交易日；資料只有日線的日子，沒有盤中時點，畫面會寫原因，不會假裝有。']],
    verdict: ['吻合與背離怎麼算',
      ['<b>資金方向 f</b>：日線＝族群成交值占比今日減前一交易日（pp）；盤中＝該時點占比減同族群同時段過去 20 日平均。',
        '<b>走勢方向 r</b>：族群相對大盤漲跌（成交值加權，與資金流向頁同口徑）。',
        '<b>吻合</b>＝f 與 r 同號，且至少一方夠大（f 的絕對值 ≥ 0.05pp 或 r ≥ 0.3%）。',
        '<b>背離</b>：資金進但走勢弱＝f 在全族群前 30% 且 r &lt; −0.3%；走勢強但資金退＝r &gt; +0.3% 且 f 在後 30%。門檻是預設值，還沒用資料校準。',
        '<b>吻合度</b>＝有訊號的族群裡 f 與 r 同向的比率；旁邊印近 3 年常態當基準，才看得出今天算高還是低。大盤跌幅超過 1.5% 的日子，占比是被動變動，一致率常態偏低。']],
    wheel: ['三種輪盤怎麼看',
      ['<b>資金輪盤</b>（預設）：橫軸＝占比 5 日均減 20 日均（趨勢），縱軸＝今日（或該時點）占比變化。右上＝資金湧入，左下＝資金轉出。成交值占比是零和的：有人進就有人出。',
        '<b>強弱輪盤</b>：用價格算的相對強弱與動能（原本網站上叫「資金輪盤」的那張，其實是價格強弱）。它和走勢吻合是意料中事，所以拿來驗證沒有資訊量。',
        '<b>資金分流樹</b>：錢從全市場分到各產業鏈、各族群，點節點＝選族群。',
        '琥珀色外環＝背離族群；白色粗框＝焦點族群（連著 5 日軌跡）。']],
    heat: ['熱力圖怎麼看', ['方塊大小＝成交值，顏色＝相對大盤漲跌（紅漲綠跌），琥珀框＝背離族群。點方塊＝換焦點。位置固定，不能拖。']],
    trend: ['走勢圖怎麼看',
      ['上圖＝族群指數（預設為相對大盤，開盤＝0；可切絕對漲跌），下圖＝資金占比變化（柱）；虛線＝時間軸游標；琥珀三角＝訊號觸發點。',
        '「日內」只有有盤中資料的日子才有；歷史上 09:00–10:00 沒有成交量資料，會以灰底標示。「60 日」看這一天前後的日線走勢。']],
    mem: ['成分股走勢', ['前 6 大（依占族群成交值）各一張，游標跟著時間軸；下表是全部成分股。盤中時間點只有前 6 大有走勢值，其餘欄位為當日收盤值。點股名進個股頁。']],
    day: ['日級別訊號／潛在個股',
      ['<b>這一區在做什麼</b>：用日線資料把「資金占比連續上升但股價還沒表態」「法人連買」「量增價穩」等條件篩出候選族群與候選個股，不限當天，是找未來可能的觀察名單。',
        '<b>每一列</b>：觸發日、規則、理由數字、觸發後 5／10／20 日相對大盤的實際表現（只有已經過去的日子才有），以及該規則 3 年回測的樣本數、命中率、扣成本後超額。',
        '<b>這是實驗</b>：回測未證實有效的規則一律標「實驗」，候選名單不是買進建議；樣本不足 30 的規則灰字不下結論。點個股進個股頁、點族群同步焦點。']],
    sig: ['提前判斷（實驗）',
      ['三種訊號：<b>資金先行</b>（占比放大但價格尚未動）、<b>擴散</b>（上漲家數比率上升）、<b>開低回升</b>。每條每族群每天只記第一次觸發，開盤 30 分鐘後才判斷。',
        '<b>這是實驗</b>：近 3 年回測沒有任何一種通過多重比較檢定，不要把它當買進訊號。樣本不足 30 的整列灰字不下結論；信賴區間含 50% 的標「無法區分於隨機」。']],
    news: ['新聞與事件', ['只列焦點族群成分股當天的新聞與重大訊息；游標之前為實色、之後為灰。']],
    inst: ['法人買賣超', ['焦點族群外資、投信、自營近 20 個交易日（億元，買超為正）。']]
  };
  function howBox(k) { var h = HOWS[k]; return '<button class="howbtn pop" type="button" data-how="fc_' + k + '" data-ttl="' + esc(h[0]) + '" aria-label="' + esc(h[0]) + '">?</button>'; }
  function howDiv(k) { var h = HOWS[k]; return '<div class="howtxt" id="how-fc_' + k + '" hidden><div class="howbody">' + A().howHTML(h[0], h[1]) + '</div></div>'; }
  function seg(id, arr, cur, label) {
    return '<div class="seg" id="' + id + '" role="group" aria-label="' + esc(label) + '">' + arr.map(function (p) { return '<button type="button" data-v="' + p[0] + '" class="' + (p[0] === cur ? 'on' : '') + '" aria-pressed="' + (p[0] === cur) + '">' + esc(p[1]) + '</button>'; }).join('') + '</div>';
  }
  function fold(id, title, extra, body) {
    var op = !isM() || open[id];
    return '<section class="card fc-card fc-fold' + (op ? ' open' : '') + '" id="' + id + '"><div class="fc-hd"><h3>' + title + '</h3>' + (extra || '') + '<button type="button" class="fc-tog" data-fold="' + id + '" aria-expanded="' + !!op + '">' + (op ? '收起' : '展開') + '</button></div><div class="fc-bd">' + body + '</div></section>';
  }
  function build() {
    var v = $('#v-flowcheck'); if (!v) return false;
    v.innerHTML =
      '<div class="fc" id="fc">'
      + '<div class="card fc-bar" id="fcBar">' + howDiv('page')
      + '<div id="fcModeBox"></div><div class="fc-date" id="fcDate"></div><span class="fc-range" id="fcRange"></span>'
      + '<div class="fc-sp"></div>' + seg('fcCat', CATS, S.cat, '族群篩選') + howBox('page') + '</div>'
      + '<div class="card fc-verdict" id="fcVerdict" aria-live="polite"></div>'
      + '<div class="fc-grid">'
      + '<div class="fc-col fc-left">'
      + '<section class="card fc-card" id="fcWheelCard"><div class="fc-hd"><h3>錢往哪跑 ' + howBox('wheel') + '</h3>'
      + seg('fcView', [['strength', '強弱輪盤'], ['money', '資金輪盤'], ['tree', '資金分流樹']], S.view, '輪盤種類') + '</div>' + howDiv('wheel')
      + '<div id="fcWheel" class="chart fc-wheel"></div>'
      + '<div class="fc-tri" id="fcTri">' + [['strength', '強弱輪盤'], ['money', '資金輪盤'], ['tree', '資金分流樹']].map(function (k) { return '<div class="fc-tp"><h4>' + k[1] + '</h4><div class="chart fc-wheel" id="fcW_' + k[0] + '"></div></div>'; }).join('') + '</div>'
      + '<div class="fc-chips" id="fcRank"></div></section>'
      + fold('fcHeatCard', '全族群熱力圖 ' + howBox('heat'), '<small class="muted fc-sub">面積＝成交值　顏色＝相對大盤</small>', howDiv('heat') + '<div id="fcHeat" class="chart fc-heat"></div>')
      + '</div>'
      + '<div class="fc-col fc-right">'
      + '<section class="card fc-card" id="fcTrendCard"><div class="fc-hd"><h3><span id="fcTrendName">—</span>：真的有在漲嗎？ ' + howBox('trend') + '</h3><span class="fc-badge" id="fcBadge"></span><div class="fc-sp"></div>'
      + '<span id="fcSpanBox"></span>' + seg('fcCmp', [['rel', '相對大盤'], ['abs', '絕對']], S.cmp, '走勢口徑') + '</div>' + howDiv('trend')
      + '<div id="fcTrend" class="chart fc-trend"></div><div class="fc-note" id="fcTrendNote"></div></section>'
      + fold('fcMemCard', '成分股走勢（前 6 大） ' + howBox('mem'), '', howDiv('mem') + '<div class="fc-minis" id="fcMinis"></div><div class="fc-tbl" id="fcMemTbl"></div>')
      + '</div></div>'
      + fold('fcDayCard', '日級別訊號／潛在個股 <span class="fc-exp">實驗，非買進建議</span> ' + howBox('day'), '', howDiv('day') + '<div id="fcDay"></div>')
      + fold('fcSigCard', '提前判斷：這類訊號事後有用嗎？ <span class="fc-exp">實驗，回測未達顯著</span> ' + howBox('sig'), '', howDiv('sig') + '<div class="fc-sigwrap"><div class="fc-sigl" id="fcSigL"></div><div class="fc-sigr" id="fcSigR"></div></div>')
      + '<div class="fc-row2">'
      + fold('fcNewsCard', '當日相關新聞／事件 ' + howBox('news'), '', howDiv('news') + '<div class="fc-news" id="fcNews"></div>')
      + fold('fcInstCard', '法人買賣超（近 20 日） ' + howBox('inst'), '', howDiv('inst') + '<div id="fcInst" class="chart fc-inst"></div><div class="fc-note" id="fcInstNote"></div>')
      + '</div>'
      + '<div class="card fc-tl" id="fcTl"><button type="button" class="btn fc-play" id="fcPlay" aria-label="播放">▶</button>'
      + '<div class="seg tiny" id="fcSpd" role="group" aria-label="播放速度">' + [1, 2, 5].map(function (n) { return '<button type="button" data-v="' + n + '" class="' + (n === playSpd ? 'on' : '') + '">×' + n + '</button>'; }).join('') + '</div>'
      + '<div class="fc-axis"><input type="range" class="tlr" id="fcRange2" min="0" max="0" step="1" value="0" aria-label="時間軸"><div class="fc-marks" id="fcMarks"></div></div>'
      + '<span class="fc-tlab" id="fcTlab">—</span><div class="seg tiny" id="fcDayT" role="group" aria-label="日內時點"></div></div>'
      + '</div>';
    wire(v);
    built = true;
    try { window.matchMedia('(min-width:1440px)').addEventListener('change', function () { if (C.idx) setTimeout(paint, 80); }); } catch (e) { /* 舊瀏覽器 */ }
    return true;
  }
  function wire(v) {
    v.addEventListener('click', function (e) {
      var b = e.target.closest('button'); if (!b) return;
      if (b.dataset.fold) { var id = b.dataset.fold, card = $('#' + id), on = !card.classList.contains('open'); card.classList.toggle('open', on); b.textContent = on ? '收起' : '展開'; b.setAttribute('aria-expanded', on);
        open[id] = on; try { localStorage.setItem('fc.open', JSON.stringify(open)); } catch (x) { /* 私密視窗 */ } setTimeout(function () { paint(); window.dispatchEvent(new Event('resize')); }, 30); return; }
      var p = b.parentElement && b.parentElement.id;
      if (p === 'fcCat') { S.cat = b.dataset.v; ensureFocus(); paint(); return; }
      if (p === 'fcView') { S.view = b.dataset.v; writeUrl(true); paint(); return; }
      if (p === 'fcRule') { S.rule = b.dataset.v; paint(); return; }
      if (p === 'fcCmp') { S.cmp = b.dataset.v; paint(); return; }
      if (p === 'fcSpan') { S.span = b.dataset.v; paint(); return; }
      if (p === 'fcSpd') { playSpd = +b.dataset.v; $$('#fcSpd button').forEach(function (x) { x.classList.toggle('on', x === b); }); return; }
      if (p === 'fcDayT') { setT(b.dataset.v); return; }
      if (p === 'fcMode') { setMode(b.dataset.v); return; }
      if (b.id === 'fcPlay') { togglePlay(); return; }
      if (b.id === 'fcPrev') { stepDate(-1); return; }
      if (b.id === 'fcNext') { stepDate(1); return; }
      if (b.dataset.g) { pick(b.dataset.g); return; }
      if (b.dataset.go) { location.hash = '#stock/' + b.dataset.go; }
    });
    $('#fcRange2').addEventListener('input', function (e) { onSlider(+e.target.value); });
    v.addEventListener('change', function (e) {
      if (e.target.id !== 'fcDatePick') return;
      var d = e.target.value, ds = dates();
      if (ds.indexOf(d) >= 0) { setDate(d); return; }
      toast(d < ds[0] ? '早於資料起點（資料起點 ' + ds[0] + '）' : '這一天不是交易日或還沒有資料');
      e.target.value = S.date;
    });
  }

  /* ---------------------------------------------------------------- 狀態變更 */
  function pick(gid) { if (!gid || gid === S.gid) return; S.gid = gid; writeUrl(true); paint(); }
  function ensureFocus() {
    var rows = catRows(rowsAt()); if (!rows.length) return;
    if (!S.gid || !rows.some(function (x) { return x.gid === S.gid; })) { var top = rows.slice().sort(function (a, b) { return b.f - a.f; })[0]; S.gid = top.gid; }
  }
  function dates() { return (C.idx && C.idx.dates) || []; }
  function setMode(m) {
    stopPlay();
    var ds = dates();
    if (m === 'today') setDate(C.idx.latest);
    else if (S.date === C.idx.latest && ds.length > 1) setDate(ds[ds.length - 2]);
  }
  function setDate(d, keepT) {
    if (!d || dates().indexOf(d) < 0) return Promise.resolve();
    var my = ++seq, was = S.date;
    return Promise.all([getDay(d), layersOf(d).indexOf('m5') >= 0 ? getM5(d) : null]).then(function () {
      if (my !== seq) return;
      S.date = d;
      var sl = slotList(d);
      if (!keepT || sl.times.indexOf(S.t) < 0) S.t = (d === C.idx.latest && sl.times.length && isIntraNow()) ? sl.times[sl.times.length - 1] : 'close';
      if (was && was !== d && S.gid && C.day[d] && !C.day[d].groups[S.gid]) { S.gid = null; toast('這一天沒有「' + gInfo(S.gid || '').name + '」，已改選資金流入第 1 名'); }
      ensureFocus(); writeUrl(true); paint();
    });
  }
  function isIntraNow() {                  // 今天且盤中（台北 09:00–13:30）才停在「最新一格」，盤後停收盤
    try { var p = new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Taipei', hour12: false, hour: '2-digit', minute: '2-digit' }).formatToParts(new Date()), h = +p[0].value, m = +p[2].value; return h * 60 + m >= 540 && h * 60 + m < 810; } catch (e) { return false; }
  }
  function toast(msg) { var n = $('#fcToast'); if (!n) { n = document.createElement('div'); n.id = 'fcToast'; n.className = 'fc-toast'; n.setAttribute('role', 'status'); document.body.appendChild(n); } n.textContent = msg; n.classList.add('on'); clearTimeout(n._t); n._t = setTimeout(function () { n.classList.remove('on'); }, 3500); }
  function stepDate(k) { var ds = dates(), i = ds.indexOf(S.date) + k; if (i >= 0 && i < ds.length) setDate(ds[i]); }
  function setT(t) { S.t = t; writeUrl(false); paint(); }
  function modeIsToday() { return S.date === C.idx.latest; }
  function onSlider(i) {
    if (modeIsToday()) { var sl = slotList(S.date); if (sl.times.length) setT(sl.times[Math.min(i, sl.times.length - 1)]); }
    else { var d = dates()[i]; if (d && d !== S.date) setDate(d, true); }
  }
  function togglePlay() { if (playT) { stopPlay(); return; } startPlay(); }
  function stopPlay() { if (playT) { clearInterval(playT); playT = null; } var b = $('#fcPlay'); if (b) { b.textContent = '▶'; b.setAttribute('aria-label', '播放'); } }
  function startPlay() {
    var b = $('#fcPlay'); b.textContent = '⏸'; b.setAttribute('aria-label', '暫停');
    var busy = false;
    playT = setInterval(function () {
      if (busy) return; var r = $('#fcRange2'), i = +r.value;
      if (i >= +r.max) { if (modeIsToday() || +r.max === 0) { stopPlay(); return; } stopPlay(); return; }
      busy = true; Promise.resolve(modeIsToday() ? setT(slotList(S.date).times[i + 1]) : setDate(dates()[i + 1], true)).then(function () { busy = false; }, function () { busy = false; });
    }, 700 / playSpd);
  }

  /* ---------------------------------------------------------------- 繪製 */
  var painting = 0;
  function paint() {
    if (!built || !C.idx || !C.day[S.date]) return;
    var my = ++painting;
    var rows = rowsAt(), all = judge(rows), vis = catRows(rows);
    if (S.cat !== 'all') judge(vis);
    ensureFocus();
    drawBar(); drawVerdict(vis, all, rows); drawTimebar();
    drawWheel(vis); drawRank(vis); drawHeat(vis);
    var cur = rows.filter(function (x) { return x.gid === S.gid; })[0];
    $('#fcTrendName').textContent = (cur && cur.name) || '—';
    var bd = $('#fcBadge'); if (cur) { var tg = tagOf(cur); bd.className = 'fc-badge ' + tg.k; bd.textContent = tg.txt; } else { bd.className = 'fc-badge'; bd.textContent = ''; }
    getSer(S.gid).then(function (ser) { if (my !== painting) return; drawTrend(cur, ser); drawMinis(cur, ser); drawInst(ser); });
    drawMemTbl(cur); drawSig(rows); drawNews(); drawDaily(rows);
  }
  function drawBar() {
    var ds = dates(), i = ds.indexOf(S.date), today = modeIsToday(), L = layersOf(S.date);
    $('#fcModeBox').innerHTML = seg('fcMode', [['today', '今天 5 分鐘'], ['hist', '歷史回放']], today ? 'today' : 'hist', '模式');
    $('#fcDate').innerHTML = '<span class="fc-dl">日期</span><div class="fc-dgrp"><button type="button" class="btn fc-dn" id="fcPrev" aria-label="前一交易日"' + (i <= 0 ? ' disabled' : '') + '>◀</button>'
      + '<label class="fc-dv"><span id="fcDtxt">' + S.date + ' (' + weekday(S.date) + ')</span><input type="date" id="fcDatePick" value="' + S.date + '" min="' + ds[0] + '" max="' + ds[ds.length - 1] + '" aria-label="選擇日期"></label>'
      + '<button type="button" class="btn fc-dn" id="fcNext" aria-label="後一交易日"' + (i >= ds.length - 1 ? ' disabled' : '') + '>▶</button></div>'
      + (today ? '' : '<span class="fc-stale">歷史回放</span>');
    $('#fcRange').textContent = '可選 ' + ds[0] + ' ～ ' + ds[ds.length - 1] + (C.idx.m5_start ? '；5 分鐘僅 ' + C.idx.m5_start.slice(5) + ' 起' : '') + (L.indexOf('daily') >= 0 && L.length === 1 ? '；這一天只有日線' : '');
    $$('#fcCat button').forEach(function (b) { b.classList.toggle('on', b.dataset.v === S.cat); b.setAttribute('aria-pressed', b.dataset.v === S.cat); });
    $$('#fcView button').forEach(function (b) { b.classList.toggle('on', b.dataset.v === S.view); b.setAttribute('aria-pressed', b.dataset.v === S.view); });
    $$('#fcCmp button').forEach(function (b) { b.classList.toggle('on', b.dataset.v === S.cmp); });
  }
  function drawVerdict(vis, all, rows) {
    var el = $('#fcVerdict'), top = vis.slice().sort(function (a, b) { return b.f - a.f; }).slice(0, 5);
    var fitN = top.filter(function (x) { return x.fit === 'fit'; }).length, dv = top.filter(function (x) { return x.div; });
    var allDiv = vis.filter(function (x) { return x.div; });
    var base = C.idx.baseline || {}, bs = base.same_rate != null ? Math.round(base.same_rate * 100) : null;
    var mk = (C.day[S.date].market || {}).chg, crash = mk != null && mk < TH.crash;
    var sc = all.score != null ? Math.round(all.score * 100) : null;
    var when = S.t === 'close' ? '' : '（' + S.t + '）';
    var s = '資金流入前 5 名是 ' + top.map(function (x) { return '<b>' + esc(x.name) + '</b>'; }).join('、') + '；其中 <b class="fc-ok">' + fitN + ' 個走勢吻合</b>'
      + (dv.length ? '，<b class="fc-warn">' + dv.length + ' 個背離</b>（資金進、相對大盤落後）：' + dv.map(function (x) { return esc(x.name); }).join('、') : '，沒有背離') + '。'
      + (sc != null ? '全族群吻合度 <b>' + sc + '%</b>' + (bs != null ? '（近 3 年常態 ' + bs + '%）' : '') : '')
      + (all.ic != null ? '，橫斷面 IC ' + sg(all.ic, 2) + (base.ic != null ? '（常態 ' + sg(base.ic, 2) + '）' : '') : '')
      + (crash ? '<span class="fc-crash">　大盤急跌日（' + sg(mk, 1, '%') + '），占比被動變動，一致率常態偏低（' + Math.round((base.crash_same_rate || 0.55) * 100) + '%）</span>' : '');
    var divBtn = allDiv.length ? '<button type="button" class="fc-chip warn" data-g="' + allDiv[0].gid + '" title="背離榜：點第一個">背離榜 ' + allDiv.length + '</button>' : '';
    var chips = (top[0] ? '<span class="fc-fl">焦點</span>' : '') + (S.gid ? '<button type="button" class="fc-chip on" data-g="' + esc(S.gid) + '">' + esc(gInfo(S.gid).name) + '</button>' : '')
      + top.filter(function (x) { return x.gid !== S.gid; }).slice(0, 3).map(function (x) { return '<button type="button" class="fc-chip" data-g="' + esc(x.gid) + '">' + esc(x.name) + '</button>'; }).join('') + divBtn;
    el.innerHTML = '<div class="fc-vt">' + when + s + '</div><div class="fc-vc">' + chips + '</div>';
  }
  function drawRank(vis) {
    var s = vis.slice().sort(function (a, b) { return b.f - a.f; }), inn = s.slice(0, 5), out = s.slice(-5).reverse(), mx = Math.max.apply(null, s.map(function (x) { return Math.abs(x.f); }).concat([0.01]));
    var chip = function (x) { return '<button type="button" class="fc-chip' + (x.gid === S.gid ? ' on' : '') + (x.div ? ' div' : '') + '" data-g="' + esc(x.gid) + '"><span>' + esc(x.name) + '</span><b style="color:' + col(x.f) + '">' + sg(x.f, 2) + '</b><i style="width:' + Math.max(3, Math.abs(x.f) / mx * 28).toFixed(0) + 'px;background:' + col(x.f) + '"></i></button>'; };
    $('#fcRank').innerHTML = '<div class="fc-rr"><span class="fc-fl">流入前 5</span>' + inn.map(chip).join('') + '</div><div class="fc-rr"><span class="fc-fl">流出前 5</span>' + out.map(chip).join('') + '</div>';
  }
  var DOWN = function (c, o) { return A().chart(c, o, { notMerge: true }); };
  function baseOpt() {
    var a = A(), ch = a.CH;
    return { animationDurationUpdate: 250, textStyle: { color: ch.ink2 }, tooltip: Object.assign({}, a.tip, { trigger: 'item' }) };
  }
  var wide = function () { return !!(window.matchMedia && window.matchMedia('(min-width:1440px)').matches); };
  function drawWheel(vis) {          // ≥1440 三張並排（共用焦點與時間）；以下退成三選一
    if (wide()) ['strength', 'money', 'tree'].forEach(function (k) { drawWheelOne(vis, $('#fcW_' + k), k); });
    else drawWheelOne(vis, $('#fcWheel'), S.view);
  }
  function drawWheelOne(vis, el, view) {
    if (!el) return;
    if (view === 'tree') return drawTree(vis, el);
    var a = A(), ch = a.CH, money = view === 'money';
    if (!vis.length) { a.empty && a.empty(el, '沒有資料'); return; }
    var X = function (x) { return money ? x.mx : x.rsx; }, Y = function (x) { return money ? x.my : x.rsy; }, c0 = money ? 0 : 100;
    var mxv = Math.max.apply(null, vis.map(function (x) { return x.tv; }));
    var size = function (x) { return 9 + Math.sqrt(x.tv / mxv) * 22; };
    var data = vis.map(function (x) { return { name: x.name, gid: x.gid, value: [X(x), Y(x)], symbolSize: size(x), r: x.r, f: x.f, share: x.share, div: x.div, itemStyle: { color: a.chgColor(x.r, 2), borderColor: ch.line, borderWidth: 1 }, label: { show: x.gid === S.gid || (x.div && vis.length < 30) } }; });
    var cur = vis.filter(function (x) { return x.gid === S.gid; })[0];
    var xs = vis.map(X), ys = vis.map(Y), pad = function (lo, hi) { var m = Math.max(Math.abs(lo - c0), Math.abs(hi - c0), money ? 0.5 : 4) * 1.15; return [c0 - m, c0 + m]; };
    var xr = pad(Math.min.apply(null, xs), Math.max.apply(null, xs)), yr = pad(Math.min.apply(null, ys), Math.max.apply(null, ys));
    var qn = money ? ['資金回流', '資金湧入', '資金轉出', '資金續進'] : ['轉強', '領先', '落後', '轉弱'];
    var qa = function (nm, x0, x1, y0, y1) { return [{ name: nm, xAxis: x0, yAxis: y0, label: { color: ch.ink3, fontSize: 12, position: 'inside' }, itemStyle: { color: 'transparent' } }, { xAxis: x1, yAxis: y1 }]; };
    var series = [
      { type: 'scatter', data: data, z: 3, label: { formatter: '{b}', position: 'right', color: ch.ink, fontSize: 12 }, emphasis: { scale: 1.15 },
        markArea: { silent: true, data: [qa(qn[0], xr[0], c0, c0, yr[1]), qa(qn[1], c0, xr[1], c0, yr[1]), qa(qn[2], xr[0], c0, yr[0], c0), qa(qn[3], c0, xr[1], yr[0], c0)] },
        markLine: { silent: true, symbol: 'none', lineStyle: { color: ch.ink3, type: 'dashed', opacity: .6 }, label: { show: false }, data: [{ xAxis: c0 }, { yAxis: c0 }] } },
      { type: 'scatter', z: 2, silent: true, data: vis.filter(function (x) { return x.div; }).map(function (x) { return { value: [X(x), Y(x)], symbolSize: size(x) + 10 }; }), itemStyle: { color: 'transparent', borderColor: ch.amber, borderWidth: 2.5 } }
    ];
    if (cur) {
      series.push({ type: 'scatter', z: 4, silent: true, data: [{ value: [X(cur), Y(cur)], symbolSize: size(cur) + 6 }], itemStyle: { color: 'transparent', borderColor: ch.ink, borderWidth: 3 } });
      if (money && cur.trail && cur.trail.length > 1) series.push({ type: 'line', z: 1, silent: true, data: cur.trail, symbolSize: 4, lineStyle: { color: ch.ink2, width: 1.5, type: 'dashed' }, itemStyle: { color: ch.ink2 } });
    }
    DOWN(el, Object.assign(baseOpt(), {
      grid: { left: 48, right: 16, top: 24, bottom: 36 },
      tooltip: Object.assign({}, a.tip, { trigger: 'item', formatter: function (p) { if (!p.data || !p.data.gid) return ''; var d = p.data; return '<b>' + esc(d.name) + '</b><br>資金 f ' + sg(d.f, 2, 'pp') + '<br>相對大盤 ' + sg(d.r, 2, '%') + '<br>占比 ' + f2(d.share, 2) + '%' + (d.div ? '<br><span style="color:' + ch.amber + '">背離</span>' : ''); } }),
      xAxis: Object.assign({ type: 'value', min: xr[0], max: xr[1], name: money ? '趨勢：占比 5 日均 − 20 日均（pp）' : '相對強度（RS-Ratio）', nameLocation: 'middle', nameGap: 24, nameTextStyle: { color: ch.ink3, fontSize: 12 }, axisLabel: { color: ch.ink3, fontSize: 12, formatter: function (v) { return (+v).toFixed(1); } } }, { axisLine: a.axisStyle.axisLine, splitLine: a.axisStyle.splitLine }),
      yAxis: Object.assign({ type: 'value', min: yr[0], max: yr[1], name: money ? (S.t === 'close' ? '今日占比變化（pp）' : '該時點占比 − 同時段 20 日均') : '動能', nameTextStyle: { color: ch.ink3, fontSize: 12 }, axisLabel: { color: ch.ink3, fontSize: 12, formatter: function (v) { return (+v).toFixed(1); } } }, { axisLine: a.axisStyle.axisLine, splitLine: a.axisStyle.splitLine }),
      series: series
    }));
    var inst = echarts.getInstanceByDom(el);
    if (inst && !el._fcBound) { el._fcBound = 1; inst.on('click', function (p) { if (p.data && p.data.gid) pick(p.data.gid); }); }
  }
  function drawTree(vis, el) {
    var a = A(), ch = a.CH, dy = C.day[S.date], leaves = ((dy.sankey || {}).leaves || []).filter(function (l) { return vis.some(function (x) { return x.gid === l.gid; }); });
    if (!leaves.length) { a.empty && a.empty(el, '這一天沒有資金分流資料'); return; }
    var byG = {}; vis.forEach(function (x) { byG[x.gid] = x; });
    var chains = {}, nodes = [{ name: '全市場', itemStyle: { color: ch.ink3 } }], links = [];
    leaves.forEach(function (l) { var cn = l.chain_name || l.chain || '其他'; chains[cn] = (chains[cn] || 0) + l.tv; });
    Object.keys(chains).forEach(function (cn) { nodes.push({ name: cn, itemStyle: { color: ch.violet }, chainNode: true }); links.push({ source: '全市場', target: cn, value: chains[cn] }); });
    leaves.sort(function (x, y) { return y.tv - x.tv; }).slice(0, 24).forEach(function (l) {
      var x = byG[l.gid]; nodes.push({ name: l.name, gid: l.gid, itemStyle: { color: a.chgColor(x ? x.r : 0, 2), borderColor: l.gid === S.gid ? ch.ink : 'transparent', borderWidth: l.gid === S.gid ? 3 : 0 } });
      links.push({ source: l.chain_name || l.chain || '其他', target: l.name, value: l.tv });
    });
    DOWN(el, Object.assign(baseOpt(), {
      tooltip: Object.assign({}, a.tip, { trigger: 'item', formatter: function (p) { return p.data && p.data.gid ? '<b>' + esc(p.name) + '</b><br>成交值 ' + (p.value / 1e8).toFixed(0) + ' 億' : (p.data && p.data.source ? esc(p.data.source) + ' → ' + esc(p.data.target) + '<br>' + (p.value / 1e8).toFixed(0) + ' 億' : esc(p.name)); } }),
      series: [{ type: 'sankey', left: 8, right: 90, top: 8, bottom: 8, nodeWidth: 14, nodeGap: 5, draggable: false, emphasis: { focus: 'adjacency' }, data: nodes, links: links,
        label: { color: ch.ink, fontSize: 12 }, lineStyle: { color: 'gradient', opacity: .3, curveness: .5 } }]
    }));
    var inst = echarts.getInstanceByDom(el);
    if (inst && !el._fcBound2) { el._fcBound2 = 1; inst.on('click', function (p) { if (p.data && p.data.gid) pick(p.data.gid); }); }
  }
  function drawHeat(vis) {
    var el = $('#fcHeat'); if (!el) return; var a = A(), ch = a.CH;
    if (!vis.length) { a.empty && a.empty(el, '沒有資料'); return; }
    var data = vis.map(function (x) { return { name: x.name, gid: x.gid, value: x.tv, r: x.r, f: x.f, itemStyle: { color: a.chgColor(x.r, 2), borderColor: x.div ? ch.amber : (x.gid === S.gid ? ch.ink : ch.panel), borderWidth: x.div || x.gid === S.gid ? 3 : 1 },
      label: { formatter: function () { return x.name + '\n' + sg(x.r, 1, '%'); } } }; });
    DOWN(el, Object.assign(baseOpt(), {
      tooltip: Object.assign({}, a.tip, { trigger: 'item', formatter: function (p) { var d = p.data || {}; return '<b>' + esc(p.name) + '</b><br>相對大盤 ' + sg(d.r, 2, '%') + '<br>資金 ' + sg(d.f, 2, 'pp') + '<br>成交值 ' + ((d.value || 0) / 1e8).toFixed(0) + ' 億'; } }),
      series: [{ type: 'treemap', roam: false, nodeClick: false, breadcrumb: { show: false }, left: 0, right: 0, top: 0, bottom: 0, squareRatio: 1.2, data: data, label: { show: true, color: ch.ink, fontSize: 12, overflow: 'truncate' }, itemStyle: { gapWidth: 1 } }]
    }));
    var inst = echarts.getInstanceByDom(el);
    if (inst && !el._fcBound) { el._fcBound = 1; inst.on('click', function (p) { if (p.data && p.data.gid) pick(p.data.gid); }); }
  }

  /* 走勢大圖：日內（有盤中資料）或 60 日日線 */
  function trendMode() {
    var sl = slotList(S.date);
    if (S.span === 'daily') return 'daily';
    if (S.span === 'intra' && sl.times.length) return 'intra';
    return sl.times.length ? 'intra' : 'daily';
  }
  function drawTrend(cur, ser) {
    var el = $('#fcTrend'), a = A(), ch = a.CH, tm = trendMode(), sl = slotList(S.date), dy = C.day[S.date];
    var hasI = sl.times.length > 0;
    $('#fcSpanBox').innerHTML = hasI ? seg('fcSpan', [['intra', '日內'], ['daily', '60 日']], tm === 'intra' ? 'intra' : 'daily', '圖的範圍') : '';
    var xs, line, bars, cursor = null, note = '', sigs = [], gap = null;
    if (tm === 'intra') {
      var d5 = sl.kind === 'm5' ? C.m5[S.date].groups[S.gid] : dy.m60 && dy.m60.groups[S.gid];
      if (!d5) { a.empty && a.empty(el, '這一天沒有這個族群的盤中資料'); $('#fcTrendNote').textContent = ''; return; }
      xs = sl.times; line = S.cmp === 'rel' ? d5.idx_rel : (d5.chg || d5.idx_rel); bars = d5.share; cursor = S.t === 'close' ? xs[xs.length - 1] : S.t;
      if (sl.kind === 'm60' && dy.m60.gap_0900) { gap = xs[0]; note = '灰底：09:00–10:00 這一段沒有成交量資料（資料湖的 60 分 K 在開盤第一小時沒有量），占比柱不可信。'; }
      (dy.signals || []).filter(function (s) { return s.gid === S.gid; }).forEach(function (s) { var i = nearest(xs, s.t); if (i >= 0) sigs.push({ value: [xs[i], line[i]], name: s.type }); });
    } else {
      if (!ser) { a.empty && a.empty(el, '沒有這個族群的日線序列'); return; }
      var i1 = ser.dates.indexOf(S.date); if (i1 < 0) i1 = ser.dates.length - 1; var i0 = Math.max(0, i1 - 59), n1 = Math.min(ser.dates.length, i0 + 60);
      xs = ser.dates.slice(i0, n1); var base = (S.cmp === 'rel' ? ser.rel_idx : ser.idx).slice(i0, n1); line = base.map(function (v) { return (v / base[0] - 1) * 100; }); bars = ser.dshare.slice(i0, n1); cursor = S.date;
      note = '日線：以 ' + xs[0] + ' 為 0；柱＝每日占比變化。';
    }
    var up = function (v) { return col(v); };
    var cursorLine = cursor ? { silent: true, symbol: 'none', lineStyle: { color: ch.ink, type: 'dashed' }, label: { show: false }, data: [{ xAxis: cursor }] } : undefined;
    var markA = gap ? { silent: true, itemStyle: { color: 'rgba(128,128,128,.18)' }, label: { color: ch.ink3, fontSize: 12 }, data: [[{ xAxis: gap, name: '無成交量資料' }, { xAxis: gap }]] } : undefined;
    DOWN(el, Object.assign(baseOpt(), {
      tooltip: Object.assign({}, a.tip, { trigger: 'axis', axisPointer: { type: 'line' }, formatter: function (ps) { var h = '<b>' + esc(ps[0].axisValue) + '</b>'; ps.forEach(function (p) { if (p.seriesType === 'scatter') return; h += '<br>' + p.marker + esc(p.seriesName) + ' ' + sg(p.value, 2, p.seriesName === '資金占比變化' ? 'pp' : '%'); }); return h; } }),
      grid: [{ left: 48, right: 16, top: 14, height: '58%' }, { left: 48, right: 16, top: '76%', height: '14%' }],
      xAxis: [Object.assign({ type: 'category', data: xs, gridIndex: 0, boundaryGap: false, axisLabel: { show: false } }, { axisLine: a.axisStyle.axisLine }), Object.assign({ type: 'category', data: xs, gridIndex: 1, boundaryGap: true }, a.axisStyle, { splitLine: { show: false }, axisLabel: Object.assign({}, a.axisStyle.axisLabel, { interval: tm === 'intra' ? Math.max(0, Math.round(xs.length / 8) - 1) : Math.round(xs.length / 6), formatter: function (v) { return v.length > 5 ? v.slice(5) : v; } }) })],
      yAxis: [Object.assign({ type: 'value', gridIndex: 0, scale: true, axisLabel: Object.assign({}, a.axisStyle.axisLabel, { formatter: '{value}%' }) }, { splitLine: a.axisStyle.splitLine }), Object.assign({ type: 'value', gridIndex: 1, splitNumber: 2, axisLabel: Object.assign({}, a.axisStyle.axisLabel, { formatter: '{value}' }) }, { splitLine: { show: false } })],
      series: [
        { name: S.cmp === 'rel' ? '相對大盤' : '族群漲跌', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: line, showSymbol: false, smooth: false, lineStyle: { color: ch.cyan, width: 2 }, itemStyle: { color: ch.cyan },
          markLine: cursorLine ? Object.assign({}, cursorLine, { data: [{ xAxis: cursor }, { yAxis: 0, lineStyle: { color: ch.ink3, type: 'dotted' } }] }) : { silent: true, symbol: 'none', data: [{ yAxis: 0 }], lineStyle: { color: ch.ink3, type: 'dotted' }, label: { show: false } }, markArea: markA },
        { name: '資金占比變化', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: bars.map(function (v) { return { value: v, itemStyle: { color: up(v) } }; }), barMaxWidth: 10,
          markArea: markA ? Object.assign({}, markA, { data: markA.data }) : undefined },
        { name: '訊號', type: 'scatter', xAxisIndex: 0, yAxisIndex: 0, data: sigs, symbol: 'triangle', symbolSize: 12, itemStyle: { color: ch.amber }, z: 5, tooltip: { show: false } }
      ]
    }));
    $('#fcTrendNote').textContent = note;
  }
  function nearest(xs, t) { var best = -1, bd = 1e9; xs.forEach(function (x, i) { var d = Math.abs(toM(x) - toM(t)); if (d < bd) { bd = d; best = i; } }); return best; }
  function toM(t) { var p = String(t).split(':'); return (+p[0]) * 60 + (+p[1] || 0); }

  /* 成分股：前 6 大各一張折線（≥200×110）＋全表 */
  function memList(cur) {
    var dy = C.day[S.date], gi = gInfo(S.gid), rows = [];
    (gi.members || []).forEach(function (c) { var m = dy.members && dy.members[c]; if (m) rows.push(Object.assign({ code: c }, m)); });
    rows.sort(function (a, b) { return b.tv - a.tv; });
    return rows;
  }
  function drawMinis(cur, ser) {
    var box = $('#fcMinis'); if (!box) return; var a = A(), ch = a.CH, rows = memList(cur).slice(0, 6), tm = trendMode(), sl = slotList(S.date), m5 = C.m5[S.date];
    if (box._g !== S.gid + '|' + rows.length) { box._g = S.gid + '|' + rows.length; $$('.fc-mini .chart', box).forEach(function (c) { var i = echarts.getInstanceByDom(c); if (i) i.dispose(); }); box.innerHTML = rows.map(function (m, i) { return '<div class="fc-mini"><button type="button" class="fc-mn" data-go="' + esc(m.code) + '" title="進個股頁"><b>' + esc(m.name) + '</b> <span>' + esc(m.code) + '</span><em id="fcMc' + i + '"></em></button><div class="chart" id="fcM' + i + '"></div></div>'; }).join(''); }
    rows.forEach(function (m, i) {
      var el = $('#fcM' + i), xs, ys, cursor, last;
      if (tm === 'intra' && sl.kind === 'm5' && m5 && m5.members[m.code]) { xs = sl.times; ys = m5.members[m.code].chg; cursor = S.t === 'close' ? xs[xs.length - 1] : S.t; }
      else if (ser && ser.members && ser.members[m.code]) { var i1 = ser.dates.indexOf(S.date); if (i1 < 0) i1 = ser.dates.length - 1; var i0 = Math.max(0, i1 - 59), cl = ser.members[m.code].close.slice(i0, i1 + 1); xs = ser.dates.slice(i0, i1 + 1); ys = cl.map(function (v) { return (v / cl[0] - 1) * 100; }); cursor = S.date; }
      else { a.empty && a.empty(el, '無走勢資料'); return; }
      var k = cursor ? xs.indexOf(cursor) : xs.length - 1; last = ys[k >= 0 ? k : ys.length - 1];
      var lab = $('#fcMc' + i); if (lab) { lab.textContent = sg(last, 1, '%'); lab.style.color = col(last); }
      DOWN(el, Object.assign(baseOpt(), { grid: { left: 36, right: 6, top: 8, bottom: 18 }, tooltip: Object.assign({}, a.tip, { trigger: 'axis', formatter: function (ps) { return esc(ps[0].axisValue) + '<br>' + sg(ps[0].value, 2, '%'); } }),
        xAxis: Object.assign({ type: 'category', data: xs, boundaryGap: false }, a.axisStyle, { splitLine: { show: false }, axisLabel: Object.assign({}, a.axisStyle.axisLabel, { interval: Math.max(0, Math.round(xs.length / 3) - 1), formatter: function (v) { return v.length > 5 ? v.slice(5) : v; } }) }),
        yAxis: Object.assign({ type: 'value', scale: true, splitNumber: 2, axisLabel: Object.assign({}, a.axisStyle.axisLabel, { formatter: '{value}%' }) }, { splitLine: a.axisStyle.splitLine }),
        series: [{ type: 'line', data: ys, showSymbol: false, lineStyle: { color: col(last), width: 1.6 }, itemStyle: { color: col(last) }, markLine: { silent: true, symbol: 'none', lineStyle: { color: ch.ink, type: 'dashed', opacity: .8 }, label: { show: false }, data: [{ xAxis: cursor }] } }] }));
    });
    if (!rows.length) box.innerHTML = '<p class="muted">這個族群沒有成分股資料</p>';
  }
  function drawMemTbl(cur) {
    var rows = memList(cur), m5 = C.m5[S.date], sl = slotList(S.date), ti = tIndex(S.date), mx = Math.max.apply(null, rows.map(function (r) { return Math.abs(r.contrib || 0); }).concat([0.001]));
    var intra = ti >= 0 && sl.kind === 'm5' && m5;
    $('#fcMemTbl').innerHTML = '<div class="fc-tw"><table><thead><tr><th>成分股（全部）</th><th>漲跌</th><th class="hm">相對大盤</th><th class="hm">占族群成交</th><th class="hm">法人(億)</th><th>貢獻</th></tr></thead><tbody>'
      + rows.map(function (m) {
        var chg = m.chg; if (intra && m5.members[m.code]) chg = m5.members[m.code].chg[ti];
        var ins = m.inst ? (m.inst.f || 0) + (m.inst.t || 0) + (m.inst.d || 0) : null;
        return '<tr><td><button type="button" class="fc-lk" data-go="' + esc(m.code) + '">' + esc(m.name) + ' ' + esc(m.code) + '</button></td><td class="n" style="color:' + col(chg) + '">' + sg(chg, 1, '%') + '</td><td class="n hm" style="color:' + col(m.rel) + '">' + sg(m.rel, 1) + '</td><td class="n hm">' + f2(m.share_in_group, 0) + '%</td><td class="n hm" style="color:' + col(ins) + '">' + sg(ins, 1) + '</td>'
          + '<td><i class="fc-cb" style="width:' + Math.max(2, Math.abs(m.contrib || 0) / mx * 40).toFixed(0) + 'px;background:' + col(m.contrib) + '"></i></td></tr>';
      }).join('') + '</tbody></table></div>' + (intra ? '<div class="fc-note">盤中時點：前 6 大漲跌為該時點值，其餘欄位為當日收盤值。</div>' : '');
  }
  function drawSig(rows) {
    var dy = C.day[S.date], a = A(), ch = a.CH, sl = slotList(S.date), tm = (sl.times.length ? sl.times : ['09:05', '13:30']);
    var sigs = (dy.signals || []).slice(), t0 = toM(tm[0]), t1 = toM(tm[tm.length - 1]), tn = { flow_lead: '資金先行', breadth: '擴散', open_low_recover: '開低回升' };
    var byG = {}; rows.forEach(function (x) { byG[x.gid] = x; });
    var marks = sigs.map(function (s) { var p = (toM(s.t) - t0) / Math.max(1, t1 - t0) * 100; return '<button type="button" class="fc-sm" style="left:' + Math.max(0, Math.min(99, p)).toFixed(1) + '%" data-g="' + esc(s.gid) + '" title="' + esc(tn[s.type] + '　' + ((byG[s.gid] || {}).name || s.gid) + '　' + s.t) + '"></button>'; }).join('');
    var cursor = S.t === 'close' ? '' : '<i class="fc-sc" style="left:' + Math.max(0, Math.min(100, (toM(S.t) - t0) / Math.max(1, t1 - t0) * 100)).toFixed(1) + '%"></i>';
    var trs = sigs.map(function (s) {
      var x = byG[s.gid] || {}, now = x.r != null ? x.r - s.rel_at_trigger : null, nowTxt = S.t === 'close' ? s.rel_to_close : now;
      return '<tr class="' + (s.gid === S.gid ? 'on' : '') + '"><td>' + tn[s.type] + '</td><td><button type="button" class="fc-lk" data-g="' + esc(s.gid) + '">' + esc(x.name || s.gid) + '</button></td><td class="n">' + esc(s.t) + '</td><td class="n" style="color:' + col(nowTxt) + '">' + sg(nowTxt, 2, '%') + '</td><td class="n hm" style="color:' + col(s.rel_to_close) + '">' + sg(s.rel_to_close, 2, '%') + '</td><td class="n hm" style="color:' + col(s.rel_next_day) + '">' + (s.rel_next_day == null ? '—' : sg(s.rel_next_day, 2, '%')) + '</td></tr>';
    }).join('');
    $('#fcSigL').innerHTML = '<div class="fc-sub2">這一天的訊號時間軸（琥珀＝觸發，白線＝目前時點）</div><div class="fc-strip">' + marks + cursor + '</div>'
      + '<div class="fc-tw"><table><thead><tr><th>訊號</th><th>族群</th><th>觸發時間</th><th>觸發後至目前（相對大盤）</th><th class="hm">收盤前</th><th class="hm">隔日</th></tr></thead><tbody>' + (trs || '<tr><td colspan="6" class="muted">這一天沒有訊號</td></tr>') + '</tbody></table></div>';
    getBt().then(function (bt) {
      if (!bt) { $('#fcSigR').innerHTML = '<div class="fc-sub2">歷史回測</div><p class="muted">回測資料尚未上線</p>'; return; }
      $('#fcSigR').innerHTML = '<div class="fc-sub2">歷史回測（' + esc(bt.period || '近 3 年') + '，全族群；截至 ' + esc(bt.as_of || '') + '）</div><div class="fc-tw"><table><thead><tr><th>訊號</th><th>樣本</th><th>命中率（95% CI）</th><th class="hm">平均超額</th><th>扣成本後</th></tr></thead><tbody>'
        + (bt.rows || []).map(function (r) {
          var small = r.n < 30, rnd = r.ci && r.ci[0] <= 0.5 && r.ci[1] >= 0.5;
          return '<tr class="' + (small ? 'fc-gray' : '') + '"><td>' + esc(r.label || r.type) + '</td><td class="n">' + r.n + '</td><td class="n">' + (small ? '樣本不足，不下結論' : (r.hit_rate * 100).toFixed(1) + '%（' + (r.ci[0] * 100).toFixed(0) + '–' + (r.ci[1] * 100).toFixed(0) + '%）' + (rnd ? '<br><small>無法區分於隨機</small>' : '')) + '</td><td class="n hm">' + (small ? '—' : sg(r.avg_excess, 2, '%')) + '</td><td class="n" style="color:' + col(r.avg_excess_net) + '">' + (small ? '—' : sg(r.avg_excess_net, 2, '%')) + '</td></tr>';
        }).join('') + '</tbody></table></div><div class="fc-note">樣本 &lt; 30 不下結論；信賴區間含 50% 者無法區分於隨機。研究用 16 組訊號沒有任何一組通過多重比較，所以這整張卡都是「實驗」。</div>';
    });
  }
  /* 日級別訊號：daily_signals.json（strategy-backtest 產出；欄位以 docs/research/20261030_daily_signals.md 為準，這裡先照假設結構，變動只改 normDaily） */
  function normDaily(j) { return j && { rules: j.rules || [], items: j.items || [], as_of: j.as_of }; }
  function getDaily() { if (C.dsig !== undefined) return Promise.resolve(C.dsig); return jget('daily_signals.json').then(function (j) { C.dsig = normDaily(j) || false; return C.dsig; }); }
  function drawDaily(rows) {
    var el = $('#fcDay'); if (!el) return; var my = painting;
    getDaily().then(function (D) {
      if (my !== painting) return;
      if (!D) { el.innerHTML = '<p class="muted">日級別訊號資料尚未上線（data/flowcheck/daily_signals.json）。</p>'; return; }
      var rid = S.rule || 'all', byG = {}; rows.forEach(function (x) { byG[x.gid] = x; });
      var rl = {}; D.rules.forEach(function (r) { rl[r.id] = r; });
      var items = D.items.filter(function (it) { return it.date <= S.date && (rid === 'all' || it.rule === rid); }).sort(function (a, b) { return a.date < b.date ? 1 : a.date > b.date ? -1 : 0; }).slice(0, 60);
      var cur = items.filter(function (it) { return it.date === S.date; }).length;
      var pc = function (v) { return v == null ? '<span class="muted">—</span>' : '<span style="color:' + col(v) + '">' + sg(v, 1, '%') + '</span>'; };
      var stat = function (r) { if (!r || r.n == null) return '—'; if (r.n < 30) return '<span class="muted">n=' + r.n + '，樣本不足</span>'; var rnd = r.ci && r.ci[0] <= 0.5 && r.ci[1] >= 0.5; return 'n=' + r.n + '　命中 ' + (r.hit_rate * 100).toFixed(0) + '%　扣成本 <span style="color:' + col(r.avg_excess_net) + '">' + sg(r.avg_excess_net, 2, '%') + '</span>' + (rnd ? '<br><small class="muted">無法區分於隨機</small>' : ''); };
      el.innerHTML = '<div class="fc-dsw">' + seg('fcRule', [['all', '全部規則']].concat(D.rules.map(function (r) { return [r.id, r.label]; })), rid, '規則篩選') + '<span class="fc-note">' + S.date + ' 當天觸發 ' + cur + ' 筆；列出 ' + S.date + ' 以前的觸發（最多 60 筆），候選不是買進建議</span></div>'
        + '<div class="fc-tw"><table><thead><tr><th>觸發日</th><th>規則</th><th>族群</th><th>個股</th><th>理由</th><th>後 5 日</th><th>後 10 日</th><th>後 20 日</th><th class="hm">規則回測（3 年）</th></tr></thead><tbody>'
        + (items.length ? items.map(function (it) {
          var r = rl[it.rule] || {}, g = byG[it.gid] || gInfo(it.gid), f = it.fwd || {};
          return '<tr class="' + (it.gid === S.gid ? 'on' : '') + '"><td class="n">' + esc(it.date) + '</td><td>' + esc(r.label || it.rule) + (r.passed === true ? '' : '<span class="fc-tag">實驗</span>') + '</td><td><button type="button" class="fc-lk" data-g="' + esc(it.gid) + '">' + esc(g.name || it.gid) + '</button></td>'
            + '<td>' + (it.code ? '<button type="button" class="fc-lk" data-go="' + esc(it.code) + '">' + esc(it.name || '') + ' ' + esc(it.code) + '</button>' : '<span class="muted">（族群層）</span>') + '</td><td class="fc-reason">' + esc(it.reason || '') + '</td>'
            + '<td class="n">' + pc(f.d5) + '</td><td class="n">' + pc(f.d10) + '</td><td class="n">' + pc(f.d20) + '</td><td class="hm">' + stat(r) + '</td></tr>';
        }).join('') : '<tr><td colspan="9" class="muted">這個日期以前沒有符合的觸發</td></tr>')
        + '</tbody></table></div><div class="fc-note">後 N 日＝觸發後相對大盤的超額報酬；「—」表示還沒到那一天。研究顯示多數規則未通過多重比較檢定，只是觀察名單。</div>';
    });
  }
  function getBt() { if (C.bt !== null) return Promise.resolve(C.bt || null); return jget('backtest.json').then(function (j) { C.bt = j || false; return j; }); }
  function drawNews() {
    var dy = C.day[S.date], gi = gInfo(S.gid), set = {}; (gi.members || []).forEach(function (c) { set[c] = 1; });
    var items = (dy.news || []).filter(function (n) { return (n.codes || []).some(function (c) { return set[c]; }); }).sort(function (a, b) { return (a.t || '') < (b.t || '') ? -1 : 1; }).slice(0, 8);
    var cur = S.t === 'close' ? '99:99' : S.t;
    $('#fcNews').innerHTML = items.length ? items.map(function (n) { var past = (n.t || '') <= cur; return '<a class="fc-nw' + (past ? '' : ' fut') + '" href="' + esc(n.url) + '" target="_blank" rel="noopener noreferrer"><time>' + esc(n.t || '') + '</time><span>' + esc(n.title) + '</span><small>' + esc(n.source || '') + '</small></a>'; }).join('')
      : '<p class="muted">這一天「' + esc(gi.name) + '」成分股沒有新聞或重大訊息</p>';
  }
  function drawInst(ser) {
    var el = $('#fcInst'), a = A(), ch = a.CH;
    if (!ser || !ser.inst_f) { a.empty && a.empty(el, '法人長序列尚未提供'); $('#fcInstNote').textContent = ''; return; }
    var i1 = ser.dates.indexOf(S.date); if (i1 < 0) i1 = ser.dates.length - 1; var i0 = Math.max(0, i1 - 19), xs = ser.dates.slice(i0, i1 + 1);
    var s = function (k) { return ser[k].slice(i0, i1 + 1); };
    DOWN(el, Object.assign(baseOpt(), { grid: { left: 44, right: 12, top: 26, bottom: 24 }, legend: { top: 0, textStyle: { color: ch.ink2, fontSize: 12 } },
      tooltip: Object.assign({}, a.tip, { trigger: 'axis' }),
      xAxis: Object.assign({ type: 'category', data: xs }, a.axisStyle, { splitLine: { show: false }, axisLabel: Object.assign({}, a.axisStyle.axisLabel, { formatter: function (v) { return v.slice(5); } }) }),
      yAxis: Object.assign({ type: 'value' }, a.axisStyle),
      series: [['外資', 'inst_f', ch.cyan], ['投信', 'inst_t', ch.violet], ['自營', 'inst_d', ch.amber]].map(function (z) { return { name: z[0], type: 'bar', stack: 'i', data: s(z[1]), itemStyle: { color: z[2] }, barMaxWidth: 14,
        markLine: z[0] === '外資' ? { silent: true, symbol: 'none', label: { show: false }, lineStyle: { color: ch.ink, type: 'dashed' }, data: [{ xAxis: S.date }] } : undefined }; }) }));
    var k = ser.dates.indexOf(S.date);
    $('#fcInstNote').textContent = k >= 0 ? S.date + ' 外資 ' + sg(ser.inst_f[k], 1) + '、投信 ' + sg(ser.inst_t[k], 1) + '、自營 ' + sg(ser.inst_d[k], 1) + ' 億' : '';
  }
  function drawTimebar() {
    var r = $('#fcRange2'), today = modeIsToday(), sl = slotList(S.date), ds = dates(), lab = $('#fcTlab'), dt = $('#fcDayT');
    var mk = '';
    if (today) {
      var n = sl.times.length; r.max = Math.max(0, n - 1); r.disabled = n < 2;
      var ti = S.t === 'close' ? n - 1 : sl.times.indexOf(S.t); r.value = Math.max(0, ti);
      lab.textContent = n ? (S.t === 'close' ? '收盤 13:30' : S.t) + ' / 13:30' : '此日無盤中資料（只有日線）';
      dt.innerHTML = ''; dt.hidden = true;
      (C.day[S.date].signals || []).forEach(function (s) { var i = sl.times.indexOf(s.t); if (i < 0) i = nearest(sl.times, s.t); if (n > 1 && i >= 0) mk += '<i style="left:' + (i / (n - 1) * 100).toFixed(1) + '%"></i>'; });
    } else {
      r.max = Math.max(0, ds.length - 1); r.disabled = ds.length < 2; r.value = Math.max(0, ds.indexOf(S.date));
      lab.textContent = S.date + ' (' + weekday(S.date) + ')' + (S.t === 'close' ? '　收盤' : '　' + S.t) + '　歷史交易日軸';
      if (sl.times.length) { dt.hidden = false; dt.innerHTML = [['close', '收盤']].concat(sl.times.filter(function (x, i, a) { return sl.kind === 'm60' || /:00$/.test(x) || i === a.length - 1; }).map(function (x) { return [x, x]; })).map(function (p) { return '<button type="button" data-v="' + p[0] + '" class="' + (S.t === p[0] ? 'on' : '') + '">' + p[1] + '</button>'; }).join(''); }
      else { dt.hidden = false; dt.innerHTML = '<span class="fc-gtxt">此日只有日線，沒有盤中時點</span>'; }
    }
    $('#fcMarks').innerHTML = mk;
  }

  /* ---------------------------------------------------------------- 進入點 */
  function show() {
    if (!built && !build()) return Promise.resolve();
    var u = readUrl();
    return (C.idx ? Promise.resolve(C.idx) : jget('index.json')).then(function (idx) {
      if (!idx) { $('#fc').innerHTML = '<div class="card"><p class="muted">流向驗證資料尚未上線（data/flowcheck/index.json 還沒產出）。</p></div>'; built = false; return; }
      C.idx = idx;
      if (u.v && ['strength', 'money', 'tree'].indexOf(u.v) >= 0) S.view = u.v;
      var d = u.d && idx.dates.indexOf(u.d) >= 0 ? u.d : (S.date || idx.latest);
      if (u.g) S.gid = u.g;
      var tt = u.t ? (/^\d{4}$/.test(u.t) ? u.t.slice(0, 2) + ':' + u.t.slice(2) : u.t) : null;
      return Promise.all([getDay(d), layersOf(d).indexOf('m5') >= 0 ? getM5(d) : null]).then(function () {
        S.date = d; var sl = slotList(d);
        S.t = tt && sl.times.indexOf(tt) >= 0 ? tt : (d === idx.latest && sl.times.length && isIntraNow() ? sl.times[sl.times.length - 1] : 'close');
        ensureFocus(); paint(); writeUrl(false);
      });
    });
  }
  function leave() { stopPlay(); }
  window.TwFlowcheck = { show: show, leave: leave, state: function () { return JSON.parse(JSON.stringify(S)); }, judge: judge, TH: TH };
})();
