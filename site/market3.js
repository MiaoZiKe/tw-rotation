/* market3.js — 總覽最上方那三張大盤圖：加權指數 / 櫃買指數 / 台指期
 *
 * Andy 2026-09-14：「總攬最上方需新增 加權 櫃買 期貨 指數 K線圖以及走勢圖 上下對應」
 *                  「需出現 加權與櫃買 台指期 即時 走勢圖並且可以切換K線型態，
 *                    且指標 格式 可以參考原本個股做好的執行。」
 *
 * 資料源（走 Cloudflare Worker 的 /chart，原因跟 live.js 一樣：CORS）
 * ------------------------------------------------------------------
 *   加權  https://mis.twse.com.tw/stock/data/mis_ohlc_TSE.txt   ch=t00.tw
 *   櫃買  https://mis.twse.com.tw/stock/data/mis_ohlc_OTC.txt   ch=o00.tw
 *   台指期 https://mis.twse.com.tw/stock/data/futures_chart.txt  ex=taifex
 * 就是證交所「基本市況報導」那三張走勢圖自己在用的檔。2026-09-14 17:30 實測：
 *   TSE/OTC：ohlcArray 270 筆，09:01~13:33 每分鐘一筆 {t:epoch毫秒, ts:"090100", c:指數, s:該分鐘張數}
 *   FUT   ：ohlcArray 300 筆，08:46~13:45，沒有 ts 欄位，其餘一樣
 *   三個檔的 infoArray[0] 都直接附當天的 o/h/l/z（開高低收）與 y（昨收），
 *   所以卡片上方那排數字不用另外再打一次報價端點。
 *
 * 為什麼「走勢圖」和「K 線」是兩套繪圖
 * ------------------------------------
 * 走勢圖要的是「固定 09:00–13:30 的時間軸 + 分鐘量柱 + 昨收虛線」，
 * 未到的時間也要留白（才看得出現在走到哪），ECharts 的類目軸最自然。
 * K 線要的是縮放、指標面板、跟個股同一套設定，那是 KChart（Lightweight Charts）的強項。
 * 兩邊共用 localStorage 的 `tw.kcfg` —— 在個股頁調好的 MA/KD/MACD，這裡直接吃到。
 *
 * ★ 分 K 是合成的，這件事要講清楚
 * 來源只給「每分鐘的指數收盤價」，沒有分鐘的最高最低。所以：
 *   開 = 前一分鐘的收盤（連續盤，等於這一分鐘的起點）
 *   高/低 = 該區間內分鐘收盤的極值 —— **不是真正的盤中極值**
 * 卡片上的「高 / 低」那兩個數字才是當天真正的極值（來自 infoArray）。
 */
(function () {
  'use strict';

  const KEY_MODE = 'tw.m3.mode';     // line | k
  const KEY_TF = 'tw.m3.tf';         // 1 | 5 | 15 | 30（分鐘）
  const KEY_BIG = 'tw.m3.big';       // 放大哪一張（空字串＝三張並排）

  const IDX = [
    { id: 'TSE', name: '加權指數', sub: '上市', turnover: true },
    { id: 'OTC', name: '櫃買指數', sub: '上櫃', turnover: true },
    { id: 'FUT', name: '台指期', sub: '近月', turnover: false },
  ];
  // 交易時段（台北）。留白到收盤，才看得出「現在走到哪」。
  const SESSION = {
    TSE: [9 * 60, 13 * 60 + 30], OTC: [9 * 60, 13 * 60 + 30], FUT: [8 * 60 + 45, 13 * 60 + 45],
  };
  const TFS = [1, 5, 15, 30];

  const state = { data: {}, err: {}, mode: 'line', tf: 5, big: '', kcharts: {}, busy: false, at: 0 };

  const ls = {
    get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : v; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* 私密視窗，忽略 */ } },
  };
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.prototype.slice.call((r || document).querySelectorAll(s));
  const num = (v) => { const n = parseFloat(v); return isFinite(n) ? n : null; };
  const F = () => (window.App && window.App.fmt) || null;

  // ---------------------------------------------------------------- 抓資料
  function proxy() {
    // 跟 live.js 用同一組設定（⚙ 面板改了這裡也跟著改）
    if (window.Live && window.Live.proxy) return window.Live.proxy();
    return '';
  }

  async function fetchOne(id) {
    const base = proxy();
    if (!base) throw new Error('還沒設定即時來源');
    const r = await fetch(base + '/chart?id=' + id + '&t=' + Date.now(), { cache: 'no-store' });
    if (r.status === 404 || r.status === 400) {
      // Worker 還是舊版（只有 /quote）。這是 Andy 要自己去 Cloudflare 重貼的那一步，直接寫在畫面上。
      throw new Error('NOCHART');
    }
    if (!r.ok) throw new Error('代理回 HTTP ' + r.status);
    const j = await r.json();
    if (j.rtcode && j.rtcode !== '0000') throw new Error('來源回 rtcode ' + j.rtcode);
    return parse(id, j);
  }

  /** 原始 JSON → {info, points:[{ms,min,c,s}], y, date} */
  function parse(id, j) {
    const info = (j.infoArray || [])[0] || {};
    const pts = [];
    (j.ohlcArray || []).forEach(o => {
      const ms = num(o.t); const c = num(o.c); if (ms === null || c === null) return;
      const d = new Date(ms + 8 * 3600 * 1000);          // 換算成台北牆鐘
      pts.push({ ms, min: d.getUTCHours() * 60 + d.getUTCMinutes(), c, s: num(o.s) || 0 });
    });
    pts.sort((a, b) => a.ms - b.ms);
    return {
      id,
      name: info.n || '',
      date: info.d || String(j.lastDatetime || '').slice(0, 8),
      time: info.t || '',
      prev: num(info.y),
      open: num(info.o), high: num(info.h), low: num(info.l), last: num(info.z),
      vol: num((j.staticObj || {}).tv),                  // 累計成交張數（台指期是口數）
      amt: num(info.v),                                  // 成交金額（百萬元）；台指期沒有
      points: pts,
    };
  }

  async function refresh() {
    if (state.busy) return;
    if (!document.getElementById('m3')) return;          // 不在總覽就不用抓
    state.busy = true;
    const jobs = IDX.map(async x => {
      try { state.data[x.id] = await fetchOne(x.id); state.err[x.id] = ''; }
      catch (e) { state.err[x.id] = String(e.message || e); }
    });
    await Promise.all(jobs);
    state.busy = false; state.at = Date.now();
    draw();
  }

  // ---------------------------------------------------------------- 合成分 K
  /** 分鐘收盤序列 → N 分鐘 K 棒 [[時間, 開, 高, 低, 收, 量]]。
   *  開＝前一根的收（連續盤）；高低是分鐘收盤的極值，不是真正盤中極值。 */
  function toBars(pts, n) {
    const out = []; let cur = null, key = null, prevClose = null;
    for (const p of pts) {
      const k = Math.floor(p.min / n);
      if (k !== key) {
        if (cur) { out.push(cur); prevClose = cur[4]; }
        key = k;
        const o = prevClose === null ? p.c : prevClose;
        cur = [Math.floor(p.ms / 1000) + 8 * 3600, o, Math.max(o, p.c), Math.min(o, p.c), p.c, p.s * 1000];
      } else {
        cur[2] = Math.max(cur[2], p.c); cur[3] = Math.min(cur[3], p.c);
        cur[4] = p.c; cur[5] += p.s * 1000;
      }
    }
    if (cur) out.push(cur);
    return out;
  }

  // ---------------------------------------------------------------- 版面
  const hhmm = (m) => String(Math.floor(m / 60)).padStart(2, '0') + ':' + String(m % 60).padStart(2, '0');

  function cardHead(x) {
    const d = state.data[x.id];
    const f = F();
    if (!d || !f) return `<div class="m3-nums"><span class="m3-px">—</span></div>`;
    const chg = (d.last != null && d.prev) ? d.last - d.prev : null;
    const pct = chg != null ? chg / d.prev * 100 : null;
    const dp = x.id === 'OTC' ? 2 : (x.id === 'FUT' ? 0 : 2);
    const extra = x.turnover
      ? `成交 ${d.amt != null ? f.n(d.amt / 100, 0) + ' 億' : '—'}`
      : `總量 ${d.vol != null ? f.i(d.vol) + ' 口' : '—'}`;
    return `<div class="m3-nums">
      <span class="m3-px ${f.cls(chg)}">${f.n(d.last, dp)}</span>
      <span class="m3-chg ${f.cls(chg)}">${chg == null ? '—' : (chg > 0 ? '+' : '') + f.n(chg, dp)} ${f.pct(pct, 2)}</span>
      <span class="m3-sub">開 ${f.n(d.open, dp)}　高 <b class="up">${f.n(d.high, dp)}</b>　低 <b class="down">${f.n(d.low, dp)}</b>　昨收 ${f.n(d.prev, dp)}</span>
      <span class="m3-sub">${extra}　<span class="mono">${f.esc(String(d.date).replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3'))} ${f.esc(d.time)}</span></span>
    </div>`;
  }

  function mount() {
    const host = document.getElementById('m3');
    if (!host) return;
    // 重掛（例如切主題）之前先收掉舊的 Lightweight Charts，不然 ResizeObserver 會留著
    Object.keys(state.kcharts).forEach(killK);
    state.mode = ls.get(KEY_MODE, 'line') === 'k' ? 'k' : 'line';
    state.tf = TFS.indexOf(+ls.get(KEY_TF, 5)) >= 0 ? +ls.get(KEY_TF, 5) : 5;
    state.big = ls.get(KEY_BIG, '');
    if (!IDX.some(x => x.id === state.big)) state.big = '';
    host.innerHTML = `
      <div class="m3-bar">
        <div class="seg" id="m3Mode"><button data-m="line">走勢圖</button><button data-m="k">K 線</button></div>
        <div class="seg" id="m3Tf">${TFS.map(n => `<button data-tf="${n}">${n} 分</button>`).join('')}</div>
        <span class="note" id="m3Note"></span>
      </div>
      <div class="m3-grid" id="m3Grid">${IDX.map(x => `
        <div class="card m3-card" data-id="${x.id}">
          <div class="m3-h">
            <h3>${x.name} <small>${x.sub}</small></h3>
            <button class="btn small m3-big" data-id="${x.id}">展開 ⤢</button>
          </div>
          ${cardHead(x)}
          <div class="m3-chart" id="m3c-${x.id}"></div>
        </div>`).join('')}</div>`;
    $$('#m3Mode button').forEach(b => b.onclick = () => { state.mode = b.dataset.m; ls.set(KEY_MODE, state.mode); draw(); });
    $$('#m3Tf button').forEach(b => b.onclick = () => { state.tf = +b.dataset.tf; ls.set(KEY_TF, state.tf); draw(); });
    $$('#m3Grid .m3-big').forEach(b => b.onclick = () => {
      state.big = state.big === b.dataset.id ? '' : b.dataset.id;
      ls.set(KEY_BIG, state.big); draw();
    });
    draw();
    refresh();
  }

  function draw() {
    const grid = document.getElementById('m3Grid');
    if (!grid) return;
    $$('#m3Mode button').forEach(b => b.classList.toggle('on', b.dataset.m === state.mode));
    $$('#m3Tf button').forEach(b => b.classList.toggle('on', +b.dataset.tf === state.tf));
    document.getElementById('m3Tf').style.display = state.mode === 'k' ? '' : 'none';
    const note = document.getElementById('m3Note');
    if (note) {
      note.textContent = state.mode === 'k'
        ? '分 K 由每分鐘指數收盤價合成：開＝前一分收盤，高低是分鐘收盤的極值（卡片上的「高／低」才是當天真正極值）。指標與個股共用同一組設定。'
        : '紅／綠對照昨收；下方是每分鐘成交量。時間軸固定到收盤，空白＝還沒走到。';
    }
    grid.classList.toggle('big', !!state.big);
    IDX.forEach(x => {
      const card = grid.querySelector(`.m3-card[data-id="${x.id}"]`);
      if (!card) return;
      card.classList.toggle('on', state.big === x.id);
      card.style.display = (state.big && state.big !== x.id) ? 'none' : '';
      const head = card.querySelector('.m3-nums');
      if (head) head.outerHTML = cardHead(x);
      const btn = card.querySelector('.m3-big');
      if (btn) btn.textContent = state.big === x.id ? '收合 ⤡' : '展開 ⤢';
      drawOne(x);
    });
    setTimeout(() => window.dispatchEvent(new Event('resize')), 30);
  }

  function killK(id) {
    if (state.kcharts[id]) { try { state.kcharts[id].destroy(); } catch (e) { /* 忽略 */ } delete state.kcharts[id]; }
  }

  function drawOne(x) {
    const el = document.getElementById('m3c-' + x.id);
    if (!el) return;
    const d = state.data[x.id];
    const err = state.err[x.id];
    if (!d || !d.points.length) {
      killK(x.id);
      if (typeof echarts !== 'undefined') { const i = echarts.getInstanceByDom(el); if (i) i.dispose(); }
      el.classList.add('isempty');
      el.dataset.kind = '';
      el.innerHTML = `<div class="empty">${err === 'NOCHART'
        ? 'Worker 還是舊版（只有 /quote）。到 Cloudflare → Workers → tw-quote → 編輯程式碼，把 repo 裡 <code>workers/quote-proxy/worker.js</code> 整份貼上去再按 Deploy，這三張圖就會出現。'
        : err ? '抓不到：' + (window.App ? window.App.fmt.esc(err) : err) : '載入中…'}</div>`;
      return;
    }
    el.classList.remove('isempty');
    if (state.mode === 'k') drawK(x, d, el); else drawLine(x, d, el);
  }

  // ---------------------------------------------------------------- 走勢圖（ECharts）
  function drawLine(x, d, el) {
    killK(x.id);
    // 從 K 線切回來時容器裡還留著 Lightweight Charts 的 DOM，不清掉 ECharts 會疊在上面
    if (el.dataset.kind !== 'line') { el.innerHTML = ''; el.dataset.kind = 'line'; }
    const f = F(); if (!f) return;
    const [s0, s1] = SESSION[x.id];
    const cats = []; for (let m = s0; m <= s1; m++) cats.push(hhmm(m));
    const price = new Array(cats.length).fill(null);
    const vol = new Array(cats.length).fill(null);
    d.points.forEach(p => { const i = p.min - s0; if (i >= 0 && i < cats.length) { price[i] = p.c; vol[i] = p.s; } });
    const up = d.last != null && d.prev ? d.last >= d.prev : true;
    const col = up ? '#ff4d6d' : '#2ee59d';
    const dp = x.id === 'FUT' ? 0 : 2;
    const A = window.App;
    // 價格軸以昨收為中心對稱，漲跌幅一眼看得出來（跟官方走勢圖同一個習慣）
    const vals = price.filter(v => v != null);
    const span = Math.max.apply(null, vals.map(v => Math.abs(v - (d.prev || v))).concat([(d.prev || 1) * 0.001]));
    const lo = (d.prev || vals[0]) - span * 1.08, hi = (d.prev || vals[0]) + span * 1.08;
    const vmax = Math.max.apply(null, vol.filter(v => v != null).concat([1]));
    A.chart(el, {
      grid: [{ left: 14, right: 58, top: 10, bottom: 74, containLabel: true },
        { left: 14, right: 58, height: 44, bottom: 24, containLabel: true }],
      tooltip: Object.assign({}, A.tip, {
        trigger: 'axis', axisPointer: { type: 'cross' },
        formatter: (ps) => {
          const i = ps[0].dataIndex;
          if (price[i] == null) return cats[i] + '<br>尚未成交';
          const c = price[i], ch = d.prev ? c - d.prev : null;
          return `<b>${cats[i]}</b><br>指數 <b class="mono">${f.n(c, dp)}</b>`
            + (ch != null ? ` <span style="color:${ch >= 0 ? '#ff4d6d' : '#2ee59d'}">${(ch > 0 ? '+' : '') + f.n(ch, dp)}（${f.pct(ch / d.prev * 100, 2)}）</span>` : '')
            + `<br>該分量 ${f.lot(vol[i] || 0)}`;
        },
      }),
      axisPointer: { link: [{ xAxisIndex: 'all' }] },
      xAxis: [
        Object.assign({}, A.axisStyle, { type: 'category', data: cats, gridIndex: 0, boundaryGap: false,
          axisLabel: { show: false }, axisTick: { show: false }, splitLine: { show: false } }),
        Object.assign({}, A.axisStyle, { type: 'category', data: cats, gridIndex: 1, boundaryGap: false,
          // 台指期的盤比較長（08:45–13:45），每半小時一個刻度會擠成一團
          axisLabel: { color: A.CH.ink3, fontSize: 10, hideOverlap: true, margin: 8,
            interval: (i) => (s0 + i) % (cats.length > 280 ? 60 : 30) === 0 },
          axisTick: { show: false }, splitLine: { show: false } }),
      ],
      yAxis: [
        // 小數位數看振幅決定：櫃買一天的區間不到 10 點，寫成整數會變成「396 396 395 395」
        Object.assign({}, A.axisStyle, { gridIndex: 0, min: lo, max: hi, position: 'right', splitNumber: 4,
          axisLabel: { color: A.CH.ink3, fontSize: 10, hideOverlap: true, showMinLabel: false,
            formatter: (v) => f.n(v, (hi - lo) < 10 ? 2 : (hi - lo) < 100 ? 1 : 0) },
          splitLine: { lineStyle: { color: A.CH.grid } } }),
        // 量軸只有 44px 高，放三個刻度一定疊在一起 —— interval 設成最大值等於只留「頂」那一格
        Object.assign({}, A.axisStyle, { gridIndex: 1, position: 'right', splitLine: { show: false },
          min: 0, max: vmax, interval: vmax || 1,
          axisLabel: { color: A.CH.ink3, fontSize: 9, showMinLabel: false,
            formatter: (v) => (v >= 1e4 ? (v / 1e4).toFixed(1) + ' 萬張' : f.i(v) + ' 張') } }),
      ],
      series: [
        { type: 'line', data: price, showSymbol: false, connectNulls: false, xAxisIndex: 0, yAxisIndex: 0,
          lineStyle: { color: col, width: 1.6 },
          areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: hexa(col, .30) }, { offset: 1, color: hexa(col, 0) }]) },
          markLine: { silent: true, symbol: 'none', label: { show: true, position: 'insideEndTop', color: A.CH.ink3, fontSize: 10, formatter: '昨收 ' + f.n(d.prev, dp) },
            lineStyle: { color: A.CH.ink3, type: 'dashed', width: 1 },
            data: [{ yAxis: d.prev }] } },
        { type: 'bar', data: vol, xAxisIndex: 1, yAxisIndex: 1, barWidth: '70%',
          itemStyle: { color: (p) => {
            const i = p.dataIndex; const prev = i > 0 ? price[i - 1] : d.prev;
            return (price[i] != null && prev != null && price[i] >= prev) ? hexa('#ff4d6d', .7) : hexa('#2ee59d', .7);
          } } },
      ],
    }, { notMerge: true });
  }

  const hexa = (hex, a) => {
    const h = String(hex).replace('#', '');
    const n = h.length === 3 ? h.split('').map(c => c + c).join('') : h;
    const v = parseInt(n, 16);
    return `rgba(${(v >> 16) & 255},${(v >> 8) & 255},${v & 255},${a})`;
  };

  // ---------------------------------------------------------------- K 線（KChart，與個股同一套）
  /** K 線的指標設定。跟個股頁共用 localStorage 的 `tw.kcfg`，但有兩個調整：
   *  1. 指數沒有供需區／BOS/CHoCH／停損目標，那三項在這裡沒有意義。
   *  2. 三張並排時每張只有 ~300px 高，塞四個面板等於什麼都看不到 ——
   *     並排時只留均線＋成交量，按「展開」變成整列大圖時才把使用者勾的指標全部放出來。 */
  function loadCfg(expanded) {
    const DEF = { ma: [5, 20, 60], maColor: [], maWidth: [], lineWidth: 1, st: {},
      vol: true, volma: 20, kd: { n: 9, m1: 3, m2: 3 }, macd: null, rsi: null, boll: null, bar: 9 };
    let c = DEF;
    try {
      const s = localStorage.getItem('tw.kcfg');
      if (s) c = Object.assign({}, DEF, JSON.parse(s));
    } catch (e) { /* 忽略 */ }
    c = Object.assign({}, c);
    delete c.smc; delete c.marks; delete c.lines; delete c.tfs;
    if (!expanded) { c.kd = null; c.macd = null; c.rsi = null; c.boll = null; }
    return c;
  }

  function drawK(x, d, el) {
    if (typeof window.KChart === 'undefined') { el.innerHTML = '<div class="empty">圖表函式庫載入失敗</div>'; return; }
    if (typeof echarts !== 'undefined') { const i = echarts.getInstanceByDom(el); if (i) i.dispose(); }
    const bars = toBars(d.points, state.tf);
    if (bars.length < 2) { killK(x.id); el.innerHTML = '<div class="empty">今天的分鐘資料還不夠畫一根 K</div>'; el.dataset.kind = ''; return; }
    killK(x.id);
    el.innerHTML = ''; el.dataset.kind = 'k';
    const expanded = state.big === x.id;
    // mini：不要面板標題與浮水印（那兩個的 CSS 只掛在個股頁的 #lwc 底下，放這裡會掉到卡片外面）
    const k = new window.KChart(el, { tf: state.tf + 'm', mini: true, compact: !expanded });
    state.kcharts[x.id] = k;
    k.setBars(bars, state.tf + 'm');
    const cfg = loadCfg(expanded);
    k.applyIndicators(cfg);
    const f = F();
    const dp = x.id === 'FUT' ? 0 : 2;
    k.setBarSpacing(expanded ? (cfg.bar || 9) : 5);
    k.fitLast(bars.length + 2);              // 小卡直接把整個交易日塞滿，不要只看得到尾盤
    if (d.prev != null) k.setPriceLines([{ price: d.prev, title: '昨收 ' + (f ? f.n(d.prev, dp) : d.prev), color: '#8ea0c4' }]);
  }

  // ---------------------------------------------------------------- 對外
  window.Market3 = {
    mount, refresh, draw,
    get state() { return state; },
    toBars,                                  // 驗收用
    get lastAt() { return state.at; },
  };
})();
