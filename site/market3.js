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
    // yahoo：有歷史 OHLC 可以抓的才填。櫃買的 ^TWOII 在 Yahoo 已經壞掉
    //（2026-09-15 實測：最後一筆停在 2026-07-17、現價給 269.45 而實際 395），
    // 台指期則沒有免費來源 —— 這兩個只有「當天即時」，選到歷史週期時畫面會說清楚為什麼。
    { id: 'TSE', name: '加權指數', sub: '上市', turnover: true, yahoo: '^TWII' },
    { id: 'OTC', name: '櫃買指數', sub: '上櫃', turnover: true, yahoo: null },
    { id: 'FUT', name: '台指期', sub: '近月', turnover: false, yahoo: null },
  ];
  // 交易時段（台北）。留白到收盤，才看得出「現在走到哪」。
  const SESSION = {
    TSE: [9 * 60, 13 * 60 + 30], OTC: [9 * 60, 13 * 60 + 30], FUT: [8 * 60 + 45, 13 * 60 + 45],
  };
  /* 週期清單。Andy 2026-09-15：「時間週期需要新增1H 4H 日 周 月 季K 太多的話可以改清單式選項」
     —— 按鈕排一排會超出卡片寬度，所以改成下拉選單，分「當天即時」與「歷史」兩組。
     即時那組是 mis 的當日分時檔自己合成的；歷史那組是 Yahoo 的 ^TWII。
     4 小時與季 K 是拿 1 小時 / 月線再合成的（Yahoo 沒有這兩個原生週期）。 */
  const TFS = [1, 5, 15, 30];                        // 當天即時的分鐘週期（相容舊的 tw.m3.tf）
  /* 日／週／月／季都從 `site/data/index_ohlc.json` 來 —— 那是管線用 FinMind 存進資料湖的
     （TaiwanStockPrice 的 TAIEX / TPEx 與 TaiwanFuturesDaily 的 TX 近月）。
     Andy 2026-09-15：「櫃買 台指期怎麼可能沒有日線數據」—— 對，Yahoo 那條壞了不代表沒有別條。
     只有「1 小時 / 4 小時」還是走 Yahoo，因為那是日線合成不出來的週期，而且只有加權有。 */
  const HIST = [
    { id: 'H1', label: '1 小時', iv: '60m', range: '3mo', group: 1, yahooOnly: true },
    { id: 'H4', label: '4 小時', iv: '60m', range: '1y', group: 4, yahooOnly: true },
    { id: 'D', label: '日 K', lake: true },
    { id: 'W', label: '週 K', lake: true, roll: 'W' },
    { id: 'M', label: '月 K', lake: true, roll: 'M' },
    { id: 'Q', label: '季 K', lake: true, roll: 'M', group: 3 },
  ];
  const histDef = (id) => HIST.filter(h => h.id === id)[0] || null;
  /** 存進 localStorage 的值可能是舊版的數字，也可能是新的歷史週期代號。 */
  function normTf(v) {
    const sv = String(v == null ? '5' : v);
    if (histDef(sv)) return sv;
    return TFS.indexOf(+sv) >= 0 ? String(+sv) : '5';
  }

  /* 自動更新的節奏。
     Andy 2026-09-15：「當我只要開啟走勢圖跟K線圖 他會自動更新 而非我要按下更新才更新」——
     之前這三張圖是寄生在 live.js 的報價輪詢裡（每分鐘一次），而且掛在 fetchQuotes 後面：
     報價連續失敗三次時整個計時器會被關掉，連帶這三張圖也不動了，只能按「更新」。
     現在改成自己有一組計時器，跟報價完全脫鉤 —— 報價壞掉不影響圖，圖壞掉也不影響報價。
     盤中 10 秒一次：mis 的 infoArray（卡片上那排數字）本來就是每 5 秒更新，
     分時檔每分鐘多一筆，10 秒足以讓數字一直在跳、新的一分鐘一出現就補上去。 */
  const MS_LIVE = 10 * 1000;
  const MS_AFTER = 5 * 60 * 1000;

  const state = { data: {}, err: {}, mode: 'line', tf: 5, big: '', kcharts: {}, busy: false, at: 0,
    hist: {}, histErr: {}, histBusy: {}, timer: null, fails: 0 };   // hist[TSE+'|'+id] = [[t,o,h,l,c,v]]

  function taipeiNow() {
    return new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Taipei' }));
  }
  /** 盤中？台指期 08:45 開盤，所以比現貨早；收盤後多留 10 分鐘讓尾盤落地。 */
  function isIntraday() {
    const d = taipeiNow();
    const w = d.getDay();
    if (w === 0 || w === 6) return false;
    const m = d.getHours() * 60 + d.getMinutes();
    return m >= 8 * 60 + 40 && m <= 13 * 60 + 55;
  }
  function schedule() {
    if (state.timer) clearInterval(state.timer);
    state.timer = setInterval(() => refresh(), isIntraday() ? MS_LIVE : MS_AFTER);
  }

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

  async function refresh(manual) {
    if (state.busy) return;
    if (!document.getElementById('m3')) return;          // 不在總覽就不用抓
    // 分頁切走就不要一直打人家的端點；切回來 visibilitychange 會補跑一次
    if (!manual && document.hidden) return;
    state.busy = true;
    const jobs = IDX.map(async x => {
      try { state.data[x.id] = await fetchOne(x.id); state.err[x.id] = ''; }
      catch (e) { state.err[x.id] = String(e.message || e); }
    });
    await Promise.all(jobs);
    state.busy = false; state.at = Date.now();
    state.fails = IDX.every(x => state.err[x.id]) ? state.fails + 1 : 0;
    draw();
  }

  /** 歷史 K。日／週／月／季走資料湖（index_ohlc.json）；1 小時／4 小時走 Yahoo（只有加權有）。 */
  async function fetchHist(x, def) {
    const key = x.id + '|' + def.id;
    if (state.hist[key] || state.histBusy[key]) return;
    if (def.lake) {
      state.histBusy[key] = true;
      try {
        const A = window.App;
        const all = await A.load('index_ohlc', { fallback: {} });
        let bars = (all && all[x.id]) || [];
        if (!bars.length) throw new Error('NOLAKE');
        bars = bars.map(b => b.slice());
        if (def.roll) bars = rollLake(bars, def.roll);
        if (def.group > 1) bars = groupBars(bars, def.group);
        state.hist[key] = bars;
        state.histErr[key] = '';
      } catch (e) {
        state.histErr[key] = String(e.message || e);
      } finally {
        state.histBusy[key] = false;
        draw();
      }
      return;
    }
    if (!x.yahoo) { state.histErr[key] = 'NOSRC'; return; }
    const base = proxy();
    if (!base) { state.histErr[key] = '還沒設定即時來源'; return; }
    state.histBusy[key] = true;
    try {
      const r = await fetch(`${base}/y?symbol=${encodeURIComponent(x.yahoo)}&interval=${def.iv}&range=${def.range}`,
                            { cache: 'no-store' });
      if (r.status === 404 || r.status === 400) throw new Error('NOCHART');
      if (!r.ok) throw new Error('代理回 HTTP ' + r.status);
      const j = await r.json();
      const res = ((j.chart || {}).result || [])[0];
      if (!res || !res.timestamp) throw new Error('Yahoo 沒有資料');
      const q = ((res.indicators || {}).quote || [])[0] || {};
      let bars = [];
      res.timestamp.forEach((t, i) => {
        const c = num(q.close && q.close[i]); if (c === null) return;
        bars.push([t + 8 * 3600, num(q.open && q.open[i]) ?? c, num(q.high && q.high[i]) ?? c,
                   num(q.low && q.low[i]) ?? c, c, num(q.volume && q.volume[i]) || 0]);
      });
      if (def.roll === 'W') bars = rollWeek(bars);
      if (def.group > 1) bars = groupBars(bars, def.group);
      state.hist[key] = bars;
      state.histErr[key] = '';
    } catch (e) {
      state.histErr[key] = String(e.message || e);
    } finally {
      state.histBusy[key] = false;
      draw();
    }
  }

  /** N 根併一根（4 小時＝四根 1 小時；季＝三根月線）。 */
  function groupBars(bars, n) {
    const out = [];
    for (let i = 0; i < bars.length; i += n) {
      const g = bars.slice(i, i + n); if (!g.length) continue;
      out.push([g[0][0], g[0][1], Math.max.apply(null, g.map(b => b[2])),
                Math.min.apply(null, g.map(b => b[3])), g[g.length - 1][4],
                g.reduce((a, b) => a + (b[5] || 0), 0)]);
    }
    return out;
  }
  /** 資料湖的日線（日期是 'YYYY-MM-DD' 字串）→ 週／月。直接用個股頁那一套，口徑才會一致。 */
  function rollLake(bars, mode) {
    return (window.KUtil && window.KUtil.resampleDaily)
      ? window.KUtil.resampleDaily(bars, mode) : bars;
  }

  /** 日線 → 週線（以該週第一個交易日標示，與個股頁的 resampleDaily 同口徑）。 */
  function rollWeek(bars) {
    const out = []; let cur = null, key = null;
    for (const b of bars) {
      const d = new Date(b[0] * 1000);
      const day = (d.getUTCDay() + 6) % 7;
      const k = Math.floor((b[0] - day * 86400) / 86400);
      if (k !== key) { if (cur) out.push(cur); key = k; cur = b.slice(); }
      else {
        cur[2] = Math.max(cur[2], b[2]); cur[3] = Math.min(cur[3], b[3]);
        cur[4] = b[4]; cur[5] += (b[5] || 0);
      }
    }
    if (cur) out.push(cur);
    return out;
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
    state.tf = normTf(ls.get(KEY_TF, '5'));
    state.big = ls.get(KEY_BIG, '');
    if (!IDX.some(x => x.id === state.big)) state.big = '';
    host.innerHTML = `
      <div class="m3-bar">
        <div class="seg" id="m3Mode"><button data-m="line">走勢圖</button><button data-m="k">K 線</button></div>
        <label class="m3-tfsel">週期
          <select id="m3Tf">
            <optgroup label="當天即時（證交所分時）">${TFS.map(n => `<option value="${n}">${n} 分</option>`).join('')}</optgroup>
            <optgroup label="歷史（Yahoo ^TWII）">${HIST.map(h => `<option value="${h.id}">${h.label}</option>`).join('')}</optgroup>
          </select></label>
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
    $('#m3Tf').onchange = (e) => { state.tf = e.target.value; ls.set(KEY_TF, state.tf); draw(); };
    $$('#m3Grid .m3-big').forEach(b => b.onclick = () => {
      state.big = state.big === b.dataset.id ? '' : b.dataset.id;
      ls.set(KEY_BIG, state.big); draw();
    });
    draw();
    refresh(true);
    schedule();
  }

  function draw() {
    const grid = document.getElementById('m3Grid');
    if (!grid) return;
    $$('#m3Mode button').forEach(b => b.classList.toggle('on', b.dataset.m === state.mode));
    const sel = document.getElementById('m3Tf');
    if (sel) { sel.value = String(state.tf); sel.parentElement.style.display = state.mode === 'k' ? '' : 'none'; }
    const note = document.getElementById('m3Note');
    if (note) {
      note.textContent = state.mode !== 'k'
        ? '紅／綠對照昨收；下方是每分鐘成交量。時間軸固定到收盤，空白＝還沒走到。'
        : histDef(state.tf)
        ? '日／週／月／季來自資料湖（FinMind：加權 TAIEX、櫃買 TPEx、台指期 TX 近月），週月季是拿日線合成的；1 小時／4 小時走 Yahoo，只有加權有。'
        : '分 K 由每分鐘指數收盤價合成：開＝前一分收盤，高低是分鐘收盤的極值（卡片上的「高／低」才是當天真正極值）。指標與個股共用同一組設定。';
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
    // 歷史週期不需要今天的分時檔（Worker 沒更新也照樣看得到日線）
    if (state.mode === 'k' && histDef(state.tf)) { el.classList.remove('isempty'); drawK(x, d || {}, el); return; }
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
    const def = histDef(state.tf);
    let bars, tfName;
    if (def) {
      const key = x.id + '|' + def.id;
      bars = state.hist[key];
      if (!bars) {
        const err = state.histErr[key];
        killK(x.id); el.dataset.kind = '';
        if (!err) { fetchHist(x, def); el.innerHTML = '<div class="empty">載入中…</div>'; return; }
        el.innerHTML = `<div class="empty">${window.App ? window.App.fmt.esc(
          err === 'NOLAKE' ? `${x.name}的歷史日 K 還沒進資料湖 —— 下一輪每日管線跑完（台北 15:30 / 18:30 / 21:30）就會有。`
          : err === 'NOSRC' ? `${x.name}沒有 1 小時／4 小時這種週期的免費來源（那是日線合成不出來的）。日／週／月／季可以看。`
          : err === 'NOCHART' ? 'Worker 還是舊版（沒有 /y）。到 Cloudflare 重貼 workers/quote-proxy/worker.js 就會有 1 小時／4 小時。'
          : '抓不到歷史 K：' + err) : err}</div>`;
        return;
      }
      tfName = def.lake ? '1d' : def.id === 'H4' ? '240m' : '60m';
    } else {
      bars = toBars(d.points, +state.tf);
      tfName = state.tf + 'm';
    }
    if (!bars || bars.length < 2) {
      killK(x.id);
      el.innerHTML = `<div class="empty">${def ? '這個週期的資料不足' : '今天的分鐘資料還不夠畫一根 K'}</div>`;
      el.dataset.kind = ''; return;
    }
    const expanded = state.big === x.id;
    const key = x.id + '|' + String(state.tf) + '|' + (expanded ? 'big' : 'small');
    const live0 = state.kcharts[x.id];
    /* 同一張卡、同一個週期、同樣大小 → 就地換資料。
       盤中 10 秒重畫一次，如果每次都 destroy 再 new，使用者的縮放與位置會一直被彈回最右邊，
       等於不能往左看早盤（Andy 2026-09-15 要的是「自動更新」，不是「自動跳回去」）。 */
    if (live0 && live0._m3key === key && el.dataset.kind === 'k') {
      live0.setBars(bars, tfName, true);
      live0.applyIndicators(loadCfg(expanded));
      return;
    }
    killK(x.id);
    el.innerHTML = ''; el.dataset.kind = 'k';
    // mini：不要面板標題與浮水印（那兩個的 CSS 只掛在個股頁的 #lwc 底下，放這裡會掉到卡片外面）
    const k = new window.KChart(el, { tf: tfName, mini: true, compact: !expanded });
    k._m3key = key;
    state.kcharts[x.id] = k;
    k.setBars(bars, tfName);
    const cfg = loadCfg(expanded);
    k.applyIndicators(cfg);
    const f = F();
    const dp = x.id === 'FUT' ? 0 : 2;
    k.setBarSpacing(expanded ? (cfg.bar || 9) : 5);
    // 當天的圖把整個交易日塞滿；歷史的圖看最近一段就好，不然幾百根擠成一片
    k.fitLast(def ? (expanded ? 160 : 90) : bars.length + 2);
    if (!def && d.prev != null) k.setPriceLines([{ price: d.prev, title: '昨收 ' + (f ? f.n(d.prev, dp) : d.prev), color: '#8ea0c4' }]);
  }

  // ---------------------------------------------------------------- 對外
  // 分頁切回來就補抓一次，不用等下一個 10 秒
  document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
  // 跨越開盤／收盤時要換節奏（10 秒 ↔ 5 分鐘），每分鐘檢查一次就夠
  setInterval(() => { if (document.getElementById('m3')) schedule(); }, 60 * 1000);

  window.Market3 = {
    mount, refresh, draw, schedule,
    get state() { return state; },
    toBars,                                  // 驗收用
    get lastAt() { return state.at; },
    get ticking() { return !!state.timer; },  // 驗收用：自己的計時器有沒有在跑
    isIntraday,
  };
})();
