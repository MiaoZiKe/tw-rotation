/* ============================================================================
   漲跌家數卡的「族群字卡」檢視（site/advdec.js，2026-11-06）
   ----------------------------------------------------------------------------
   Andy 11-06：「這邊多一個切換，可以看到全部族群的字卡，整齊排列 字卡需要剛好矩陣填滿
   並且點擊該族群也會有對應股票字卡　字卡顏色 -10~+10% 深綠~深紅
   目的是更直觀看到 哪些市場跌停 狀況　以及可以依照級距篩選」

   這張圖回答：今天跌停（漲停）的股票集中在哪些族群、哪些族群整個在跌。
   · 資料＝app.js renderUpDown 已經分好級距的那份（stocks.json 逐檔），所以跟直方圖的家數一定對得起來；
     這支只負責畫字卡，不自己抓資料、不吃盤中即時（這張卡本來就只有盤後資料）。
   · 族群＝stocks.json 每檔的 `group`（人工校訂的主族群，一檔只在一個族群），所以各族群家數加總＝直方圖的「共 N 檔」。
   · 族群的「平均漲跌幅」＝成分股等權平均。熱力圖／族群頁用的是「前一日成交值加權」，那個算法需要前一日成交值，
     這份逐檔資料沒有；而且一旦套了級距篩選，加權會被一兩檔大型股吃掉，看不出「有幾檔在跌停」。
     所以這裡刻意用等權，口徑寫在「?」裡，不跟熱力圖假裝是同一個數。
   · 級距篩選（多選）：選了之後「只算符合級距的成分股」，沒有符合股票的族群不顯示。
     理由：Andy 要看的是「哪些族群有跌停」——族群留著但平均值還是整個族群的，畫面會互相矛盾；
     直接只算符合的，字卡的平均與家數、點進去的個股字卡三者永遠同一批股票。
   · 字卡剛好填滿：依容器寬度算欄數，在「最多欄」附近挑最後一列最滿的那個欄數；最後一列不夠滿時，
     那一列的字卡等寬拉開補滿（每一列都是整列，沒有缺角）。
   與 app.js 的接口（避免兩邊互相 import）：app.js 呼叫 AdvDec.render(ctx)、AdvDec.toggle(i)、AdvDec.has(i)；
   這支用 document 事件 `adt:view`（切檢視）、`adt:sel`（篩選變了）通知 app.js 去重畫直方圖的亮暗。
   ============================================================================ */
(function () {
  'use strict';
  var S = { mode: 'dist', sel: new Set(), group: null, ctx: null };
  var GAP = 6;
  var $ = function (s) { return document.querySelector(s); };
  var esc = function (s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); };
  var pct = function (v) { return (v > 0 ? '+' : '') + (Math.round(v * 100) / 100).toFixed(2) + '%'; };
  var fire = function (n, d) { try { document.dispatchEvent(new CustomEvent(n, { detail: d || {} })); } catch (e) { /* 舊瀏覽器：直方圖不會即時亮暗，不影響字卡 */ } };

  /* 色階：-10% 深綠 → 0 中性 → +10% 深紅（超過封頂）。色票 --adt-up／--adt-dn／--adt-n 定義在 advdec.css（深淺主題各一組）。
     用 color-mix 混合，所以切主題不必重畫。≥7% 的深色底字用白，其餘用主文字色（兩個主題都量過對比 ≥ 4.5）。*/
  function tint(v) {
    v = +v;
    if (!isFinite(v) || Math.round(v * 100) === 0) return { bg: 'var(--adt-n)', fg: 'var(--ink)' };
    var p = Math.round(Math.min(1, Math.abs(v) / 10) * 100);
    return { bg: 'color-mix(in srgb, var(' + (v > 0 ? '--adt-up' : '--adt-dn') + ') ' + p + '%, var(--adt-n))', fg: p >= 70 ? '#fff' : 'var(--ink)' };
  }
  function ovOk() { return !window.TwQuota || !window.TwQuota.heatLinkOk || window.TwQuota.heatLinkOk(); }

  /* ---- 欄數：寬度 W、最小字卡寬 minW → 在 [0.6×最多欄, 最多欄] 之間挑最後一列最滿的（同分取欄數多的） ---- */
  function pickCols(n, W, minW) {
    var maxC = Math.max(2, Math.floor((W + GAP) / (minW + GAP)));
    if (n <= maxC) return Math.max(1, n);
    var best = maxC, bestR = -1, lo = Math.max(2, Math.floor(maxC * 0.6));
    for (var c = maxC; c >= lo; c--) {
      var r = (n % c || c) / c;
      if (r >= 0.6) return c;                  // 欄數愈多愈好：最後一列有 60% 以上就收
      if (r > bestR + 1e-9) { bestR = r; best = c; }
    }
    return best;
  }
  function layRows(html, W, minW) {
    var n = html.length; if (!n) return '';
    var c = pickCols(n, W, minW), out = '';
    for (var i = 0; i < n; i += c) out += '<div class="adt-row">' + html.slice(i, i + c).join('') + '</div>';
    return out;
  }

  function groupsOf() {
    var ctx = S.ctx, m = new Map(), total = new Map();
    ctx.bins.forEach(function (rows, bi) {
      rows.forEach(function (r) {
        var g = r.group || '（未分類）';
        total.set(g, (total.get(g) || 0) + 1);
        if (S.sel.size && !S.sel.has(bi)) return;
        var o = m.get(g); if (!o) { o = { name: g, gid: r.group_id || '', items: [], sum: 0 }; m.set(g, o); }
        o.items.push({ r: r, b: bi }); o.sum += +r.chg_pct || 0;
      });
    });
    var list = Array.from(m.values());
    list.forEach(function (o) { o.n = o.items.length; o.avg = o.sum / o.n; o.total = total.get(o.name) || o.n;
      o.lu = o.items.filter(function (x) { return x.b === 10; }).length; o.ld = o.items.filter(function (x) { return x.b === 0; }).length; });
    list.sort(function (a, b) { return b.avg - a.avg || (a.name < b.name ? -1 : 1); });
    return list;
  }

  function drawBins() {
    var box = $('#adtBins'); if (!box) return;
    var ctx = S.ctx, UD = ctx && ctx.UD;
    if (!UD) { box.innerHTML = ''; return; }
    box.innerHTML = UD.map(function (b, i) {
      var t = tint(b.m ? (b.m > 0 ? 1 : -1) * Math.max(6, Math.abs(b.m)) : 0), on = S.sel.has(i);   // 色點至少 60%，不然 -1~0／0~1 兩級看不出顏色
      return '<button type="button" data-b="' + i + '" class="adt-b' + (on ? ' on' : '') + '" aria-pressed="' + on + '" style="--tb:' + t.bg + ';--tf:' + t.fg + '" title="' + esc(i === 5 ? '平盤' : b.k + (i === 0 || i === 10 ? '（≥9.5%）' : '%')) + '">'
        + esc(b.k) + '<em>' + ctx.cnt[i] + '</em></button>';
    }).join('');
  }

  function subLine(left, right) { var s = $('#adtSub'); if (s) s.innerHTML = '<div class="adt-l">' + left + '</div><div class="adt-r">' + right + '</div>'; }
  var LEG = '<span class="adt-lg" aria-hidden="true"><i>-10%</i><u></u><i>+10%</i></span>';

  function draw() {
    var wrap = $('#adtWrap'), grid = $('#adtGrid'); if (!wrap || !grid) return;
    wrap.dataset.mode = S.mode; wrap.dataset.group = S.group || '';
    drawBins();
    var ctx = S.ctx;
    if (!ctx || !ctx.pool || !ctx.pool.length) { subLine('', ''); grid.innerHTML = '<div class="adt-empty">尚無逐檔漲跌資料</div>'; return; }
    var W = grid.clientWidth || 560;
    var date = ctx.date ? String(ctx.date).slice(5).replace('-', '/') + ' 盤後' : '盤後';
    var gs = groupsOf();
    var cur = S.group ? gs.filter(function (g) { return g.name === S.group; })[0] : null;
    if (S.group && !cur) { S.group = null; wrap.dataset.group = ''; }
    if (!cur) {
      var m = gs.reduce(function (a, g) { return a + g.n; }, 0);
      subLine('<span>' + gs.length + ' 個族群・' + (S.sel.size ? '符合 ' : '共 ') + m + ' 檔</span><span class="m">' + esc(date) + '</span>', LEG);
      if (!gs.length) { grid.innerHTML = '<div class="adt-empty">' + esc(ctx.mktName) + '沒有符合這些級距的股票</div>'; return; }
      var minW = innerWidth <= 640 ? 96 : 112;
      grid.innerHTML = layRows(gs.map(function (g) {
        var t = tint(g.avg);
        return '<button type="button" class="adt-g" data-g="' + esc(g.name) + '" data-n="' + g.n + '" data-avg="' + (Math.round(g.avg * 10000) / 10000) + '" data-lu="' + g.lu + '" data-ld="' + g.ld + '" style="--tb:' + t.bg + ';--tf:' + t.fg + '" title="' + esc(g.name + '：平均 ' + pct(g.avg) + '，' + g.n + ' 檔' + (S.sel.size ? '（符合級距；族群共 ' + g.total + ' 檔）' : '') + (g.lu ? '，漲停 ' + g.lu : '') + (g.ld ? '，跌停 ' + g.ld : '')) + '">'
          + '<span class="nm">' + esc(g.name) + '</span><span class="ln"><b class="pc">' + pct(g.avg) + '</b>'
          + (g.lu ? '<b class="lim">漲停' + g.lu + '</b>' : '') + (g.ld ? '<b class="lim">跌停' + g.ld + '</b>' : '') + '</span></button>';
      }), W, minW);
      return;
    }
    // ---- 個股字卡 ----
    var items = cur.items.slice().sort(function (a, b) { return (+b.r.chg_pct || 0) - (+a.r.chg_pct || 0) || (b.r.turnover || 0) - (a.r.turnover || 0); });
    subLine('<button type="button" class="adt-back" id="adtBack">← 返回族群</button><b class="gn">' + esc(cur.name) + '</b><span>平均 <b class="' + (cur.avg > 0 ? 'up' : cur.avg < 0 ? 'down' : '') + '">' + pct(cur.avg) + '</b>・' + cur.n + ' 檔</span>'
      + (cur.gid && ovOk() ? '<a class="adt-go" href="#industry/group/' + encodeURIComponent(cur.gid) + '">族群頁 →</a>' : ''), LEG);
    grid.innerHTML = layRows(items.map(function (x) {
      var r = x.r, t = tint(r.chg_pct), lim = x.b === 10 ? 'lu' : x.b === 0 ? 'ld' : '';
      return '<a class="adt-s ' + lim + '" data-pct="' + (+r.chg_pct || 0) + '" href="#stock/' + esc(r.code) + '" style="--tb:' + t.bg + ';--tf:' + t.fg + '" title="' + esc((r.name || '') + ' ' + r.code + ' ' + pct(+r.chg_pct || 0) + (lim ? (lim === 'lu' ? '（漲幅 ≥9.5%，視為漲停）' : '（跌幅 ≥9.5%，視為跌停）') : '')) + '">'
        + '<span class="nm">' + esc(r.name || r.code) + '</span><span class="cd">' + esc(r.code) + '</span><span class="ln"><b class="pc">' + pct(+r.chg_pct || 0) + '</b>'
        + (lim ? '<b class="lim">' + (lim === 'lu' ? '漲停' : '跌停') + '</b>' : '') + '</span></a>';
    }), W, innerWidth <= 640 ? 96 : 112);
  }

  function setMode(v) {
    if (v !== 'dist' && v !== 'tiles') return;
    S.mode = v;
    var bw = $('#breadthWrap'), aw = $('#adtWrap');
    if (bw) bw.hidden = v === 'tiles';
    if (aw) aw.hidden = v !== 'tiles';
    var pn = $('#udPanel'); if (pn && v === 'tiles') pn.hidden = true;
    document.querySelectorAll('#udView button').forEach(function (b) { var on = b.dataset.v === v; b.classList.toggle('on', on); b.setAttribute('aria-pressed', on ? 'true' : 'false'); });
    if (v === 'tiles') S.group = null;
    updClear();
    fire('adt:view', { v: v });
    if (v === 'tiles') draw();
  }
  function updClear() {
    var b = $('#adtClear'); if (!b) return;
    b.hidden = !S.sel.size; b.textContent = '清除篩選（' + S.sel.size + '）';
  }
  function toggle(i) {
    if (S.sel.has(i)) S.sel.delete(i); else S.sel.add(i);
    updClear(); fire('adt:sel'); if (S.mode === 'tiles') draw();
  }
  function clear() { S.sel.clear(); updClear(); fire('adt:sel'); if (S.mode === 'tiles') draw(); }
  function reset() {
    var dirty = S.mode !== 'dist' || S.sel.size || S.group;
    S.group = null; S.sel.clear(); S.mode = 'dist';
    if (dirty) { var bw = $('#breadthWrap'), aw = $('#adtWrap'); if (bw) bw.hidden = false; if (aw) aw.hidden = true;
      document.querySelectorAll('#udView button').forEach(function (b) { var on = b.dataset.v === 'dist'; b.classList.toggle('on', on); b.setAttribute('aria-pressed', on ? 'true' : 'false'); });
      updClear(); fire('adt:view', { v: 'dist' }); fire('adt:sel'); }
  }

  document.addEventListener('click', function (e) {
    var t = e.target; if (!t || !t.closest) return;
    var v = t.closest('#udView button'); if (v) { setMode(v.dataset.v); return; }
    if (t.closest('#adtClear')) { clear(); return; }
    var b = t.closest('#adtBins button');
    if (b) { toggle(+b.dataset.b); return; }
    var g = t.closest('#adtGrid .adt-g'); if (g) { S.group = g.dataset.g; draw(); var gr = $('#adtGrid'); if (gr) gr.scrollTop = 0; return; }
    if (t.closest('#adtBack')) { S.group = null; draw(); }
  });
  window.addEventListener('hashchange', function () { if (location.hash && !/^#overview/.test(location.hash)) reset(); });
  if (window.ResizeObserver) {
    var lastW = 0, ro = new ResizeObserver(function () { var g = $('#adtGrid'); if (!g) return; var w = g.clientWidth; if (w && Math.abs(w - lastW) >= 6 && S.mode === 'tiles') { lastW = w; draw(); } });
    var arm = function () { var g = $('#adtGrid'); if (g) ro.observe(g); };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', arm); else arm();
  }

  window.AdvDec = {
    render: function (ctx) { S.ctx = ctx; updClear(); if (S.mode === 'tiles') draw(); },
    toggle: toggle, has: function (i) { return S.sel.has(i); }, size: function () { return S.sel.size; },
    mode: function () { return S.mode; }, reset: reset, _state: S
  };
})();
