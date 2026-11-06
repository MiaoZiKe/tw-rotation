/* ============================================================================
   總覽摘要卡列最右邊的「恐慌指數」卡（site/fearcard.js）
   Andy 2026-11-06：「另外需要新增恐慌指數再右上」。
   ----------------------------------------------------------------------------
   資料：data/fear.json（pipeline/compute/ivx.py build_json；只重算這份＝python -m pipeline.compute.ivx）
     · 主數字＝本站自算「臺指選擇權隱含波動率」（CBOE 白皮書公式、TXO 月契約近月＋次近月、30 天期），**非期交所官方**；
       名稱刻意不用「VIX」（Cboe 商標）。
     · 副數字＝美股恐慌指數 VIX（芝加哥期權交易所，資料湖 intl_daily 的 ^VIX，yfinance）。
     · 狀態＝本站自算序列在「到那天為止」最近 750 個交易日的分位：< 50% 平靜、50～85% 警戒、≥ 85% 恐慌；
       歷史不到 120 天不給標籤（樣本不足），n 一律寫出來。
   為什麼放一支獨立檔：同事同時在改 app.js 的總覽（提示框、漲跌家數字卡），這張卡的邏輯全部放這裡，
   app.js 只留三個接點（renderOvSummary 加卡片、點卡片 → toggle、畫完 → mounted）。
   卡片長相沿用同一排的 .osc（標題列、比例條、數字、底線），比例條＝分位（0～100%）。
   點卡片 → 卡列下方展開完整圖（#ovFearFull，ECharts，拉Bar 可拖）；功能鍵 ov.fear 計的是這張完整圖（site/features.js）。
   ============================================================================ */
(function () {
  'use strict';
  const S = { data: null, loading: null, open: false, chart: null };
  const A = () => window.App || null;
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const md = (d) => { const s = String(d || ''); return /^\d{4}-\d{2}-\d{2}/.test(s) ? s.slice(5, 7) + '/' + s.slice(8, 10) : '—'; };
  const n2 = (v) => (v == null || !isFinite(v) ? '—' : Number(v).toFixed(2));
  // 漲跌：數值往上＝紅、往下＝綠（台股慣例，跟全站一致；恐慌指數往上＝市場更緊張）
  // 卡片上漲跌只留一位小數（五張一排時一欄約 93px，兩位小數會把「▲11.57」切掉）；完整圖下方的說明列是兩位
  const chg = (v) => (v == null || !isFinite(v) ? '<em>—</em>' : `<em class="${v > 0 ? 'fz-up' : v < 0 ? 'fz-dn' : ''}" title="較前一個交易日 ${v > 0 ? '+' : ''}${Number(v).toFixed(2)}">${v > 0 ? '▲' : v < 0 ? '▼' : ''}${Math.abs(v).toFixed(1)}</em>`);
  const ST = { calm: { n: '平靜', c: 'var(--cyan)' }, alert: { n: '警戒', c: 'var(--amber)' }, panic: { n: '恐慌', c: 'var(--rise)' } };
  const ICON = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    + '<path d="M4.5 16.5a8 8 0 1 1 15 0"/><path d="M12 16.5l4-5.5"/><circle cx="12" cy="16.5" r="1.3"/></svg>';

  function load() {
    if (S.data) return Promise.resolve(S.data);
    if (S.loading) return S.loading;
    const a = A();
    S.loading = (a && a.load ? a.load('fear') : fetch('data/fear.json').then((r) => (r.ok ? r.json() : null)))
      .catch(() => null).then((d) => { S.data = d || { tw: null, us: null }; S.loading = null; return S.data; });
    return S.loading;
  }

  /* 近 60 日小走勢線（純 SVG，不開 ECharts：卡片一排五張，各開一個圖表實例太重）。虛線＝85% 分位（恐慌門檻）。*/
  function spark(tw) {
    const pts = (tw && tw.spark) || [];
    if (pts.length < 2) return '<span class="fz-sp muted">—</span>';
    const vs = pts.map((p) => p[1]);
    const lo = Math.min(...vs, tw.q85 != null ? tw.q85 : Infinity), hi = Math.max(...vs, tw.q85 != null ? tw.q85 : -Infinity);
    const W = 100, H = 30, y = (v) => (hi === lo ? H / 2 : H - 2 - (v - lo) / (hi - lo) * (H - 4));
    const d = vs.map((v, i) => `${i ? 'L' : 'M'}${(i / (vs.length - 1) * W).toFixed(1)},${y(v).toFixed(1)}`).join('');
    const st = ST[tw.state] || { c: 'var(--ink-2)' };
    const ref = tw.q85 != null ? `<line x1="0" x2="${W}" y1="${y(tw.q85).toFixed(1)}" y2="${y(tw.q85).toFixed(1)}" stroke="var(--ink-3)" stroke-width="1" stroke-dasharray="3 3" vector-effect="non-scaling-stroke"/>` : '';
    return `<svg class="fz-sp" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="近 ${vs.length} 個交易日走勢">${ref}`
      + `<path d="${d}" fill="none" stroke="${st.c}" stroke-width="1.6" vector-effect="non-scaling-stroke"/></svg>`;
  }

  /* 卡片 HTML（跟 app.js ovsCard 同一套 class）。資料還沒到就先畫「載入中」，到了 refresh() 原地換。*/
  function inner(d) {
    const tw = d && d.tw, us = d && d.us;
    const st = tw && ST[tw.state];
    const pct = tw && tw.pct != null ? Math.round(tw.pct * 100) : null;
    const bar = pct != null ? `<i class="fz-pct" style="width:${Math.max(2, pct)}%;--c:${st ? st.c : 'var(--ink-3)'}" title="分位 ${pct}%（近 ${tw.n_hist} 個交易日）"></i>` : '<i class="osc-none"></i>';
    const badge = tw ? (st ? `<em class="fz-st" style="--c:${st.c}">${st.n}</em>` : '<em class="fz-st na" title="歷史不足 120 個交易日，不給狀態">樣本不足</em>') : '';
    const nums = !d ? '<span class="muted">載入中…</span>'
      : !tw && !us ? '<span class="muted">尚無資料</span>'
        : `<div class="osn fz-tw" data-v="tw"><small>台指自算 ${md(tw && tw.date)}</small><span class="osn-v"><b>${n2(tw && tw.value)}</b>${tw ? chg(tw.chg) : ''}</span></div>`
        + `<div class="osn fz-us" data-v="us"><small>美股VIX ${md(us && us.date)}</small><span class="osn-v"><b>${n2(us && us.value)}</b>${us ? chg(us.chg) : ''}</span></div>`;
    /* 最後一行：狀態膠囊＋近 60 日小走勢線＋分位（n）＋「非期交所官方」。五張卡一排時每張約 218px，數字列只放得下兩欄，走勢線放這一行 */
    const foot = tw ? `${badge}${spark(tw)}<span class="muted" title="今天的值在最近 ${tw.n_hist} 個交易日裡的分位">分位${pct != null ? pct + '%' : '—'}・n=${tw.n_hist}</span>`
      : '<span class="muted">台指自算值回補中</span>';
    return { bar, nums, foot, aria: `恐慌指數：台指選擇權隱含波動率（本站自算）${n2(tw && tw.value)}${st ? '，' + st.n : ''}；美股 VIX ${n2(us && us.value)}。點一下展開完整圖` };
  }
  function card() {
    const o = inner(S.data);
    return `<div class="osc fz" data-k="fear" role="button" tabindex="0" aria-expanded="${S.open}" aria-label="${esc(o.aria)}" title="點一下展開完整圖">`
      + `<div class="osc-h"><span class="osc-ic" data-icon="gauge" style="--ic:var(--rise)" aria-hidden="true">${ICON}</span><b class="osc-t">恐慌指數</b><span class="fz-tag" title="台指選擇權隱含波動率由本站依公開公式自算，不是期交所公布的臺指VIX">非期交所官方</span>`
      + `<button class="howbtn pop" data-how="ovs-fear" data-ttl="恐慌指數" type="button" aria-label="恐慌指數怎麼看">?</button></div>`
      + `<div class="osc-bar track">${o.bar}</div><div class="osc-n">${o.nums}</div><div class="osc-f">${o.foot}</div></div>`;
  }
  function howText(d) {
    const m = (d && d.method) || {};
    const lo = Math.round((m.calm || 0.5) * 100), hi = Math.round((m.panic || 0.85) * 100);
    return '<b class="howq">市場現在有多緊張：選擇權價格隱含的未來 30 天波動。</b><ul>'
      + '<li>主數字＝<b>台指選擇權隱含波動率（本站自算，非期交所官方）</b>：用期交所公布的臺指選擇權（TXO）近月、次近月月契約各履約價的結算價，照芝加哥期權交易所公開的 VIX 白皮書公式算，插補成 30 天期，單位是年化 %</li>'
      + `<li>無風險利率固定 ${((m.rate || 0.015) * 100).toFixed(1)}%；近月剩最後兩個交易日就改用次近月＋第三近月（同期交所換月規則）</li>`
      + '<li>官方臺指VIX用買賣報價中價，本站拿得到的是結算價，所以數字會有落差；看的是方向與相對高低</li>'
      + `<li>狀態＝今天的值在最近 ${m.window || 750} 個交易日（到今天為止，不含未來）裡的分位：低於 ${lo}% 平靜、${lo}～${hi}% 警戒、${hi}% 以上恐慌</li>`
      + `<li>門檻依據：${lo}%＝中位數（比一半的日子高才開始警戒）；${hi}%≈平均加一個標準差（常態分配下約 84%），不是對著歷史挑出來的數字</li>`
      + `<li>歷史不到 ${m.min_hist || 120} 個交易日只給數字、不給狀態；括號裡的 n＝分位用到的天數</li>`
      + '<li>副數字＝美股恐慌指數 VIX（芝加哥期權交易所），日期是美國交易日，跟台股差一天是正常的</li>'
      + '<li>小走勢線＝近 60 個交易日，虛線＝85% 分位；點卡片展開完整圖</li></ul>';
  }

  function refresh() {
    const c = document.querySelector('#hero .osc[data-k="fear"]'); if (!c) return;
    const o = inner(S.data);
    const set = (sel, h) => { const e = c.querySelector(sel); if (e && e.innerHTML !== h) e.innerHTML = h; };
    set('.osc-bar', o.bar); set('.osc-n', o.nums); set('.osc-f', o.foot);
    c.setAttribute('aria-label', o.aria); c.setAttribute('aria-expanded', String(S.open));
    const hb = document.getElementById('how-ovs-fear'); if (hb) hb.innerHTML = howText(S.data);
    const host = document.getElementById('hero');
    if (host && S.data) { host.dataset.fearTw = S.data.tw ? String(S.data.tw.value) : ''; host.dataset.fearUs = S.data.us ? String(S.data.us.value) : ''; host.dataset.fearState = (S.data.tw && S.data.tw.state) || ''; }
  }

  /* 卡列整排重畫（renderOvSummary）之後：補「?」說明、資料到了就原地換，開著的完整圖重新掛回去 */
  function mounted(host) {
    if (!host) return;
    if (!document.getElementById('how-ovs-fear')) { const b = document.createElement('div'); b.className = 'howtxt'; b.id = 'how-ovs-fear'; b.hidden = true; host.appendChild(b); }
    refresh();
    load().then(() => { refresh(); if (S.open) openFull(); });
  }

  function closeFull() {
    S.open = false;
    const p = document.getElementById('ovFearFull');
    if (S.chart) { try { S.chart.dispose(); } catch (e) { /* 已經沒了 */ } S.chart = null; }
    if (p) p.remove();
    refresh();
  }
  function openFull() {
    const host = document.getElementById('hero'); if (!host) return;
    S.open = true;
    let p = document.getElementById('ovFearFull');
    if (!p) {
      p = document.createElement('section'); p.id = 'ovFearFull'; p.className = 'fz-full'; p.setAttribute('aria-label', '恐慌指數完整圖');
      p.innerHTML = '<div class="fz-fh"><b>恐慌指數（台指選擇權隱含波動率・本站自算）</b><span class="fz-tag">非期交所官方</span>'
        + '<span class="fz-leg"><i style="--c:var(--rise)"></i>台指自算<i style="--c:var(--cyan)"></i>美股 VIX（芝加哥期權交易所）</span>'
        + '<button type="button" class="fz-x" aria-label="收起恐慌指數完整圖">×</button></div>'
        + '<div class="fz-cv" id="ovFearChart"></div><div class="fz-note" id="ovFearNote"></div>';
      host.appendChild(p);
      p.querySelector('.fz-x').onclick = (e) => { e.stopPropagation(); closeFull(); };
    }
    refresh();
    draw();
  }
  function draw() {
    const el = document.getElementById('ovFearChart'); const a = A(); const d = S.data || {};
    const tw = d.tw, us = d.us;
    const note = document.getElementById('ovFearNote');
    if (note) note.innerHTML = tw
      ? `台指自算 <b>${n2(tw.value)}</b>（${esc(tw.date)}，近月 ${esc((tw.near || {}).exp || '—')}／次近月 ${esc((tw.next || {}).exp || '—')}）・分位 ${tw.pct != null ? Math.round(tw.pct * 100) + '%' : '—'}（n=${tw.n_hist}）・50% 分位 ${n2(tw.q50)}／85% 分位 ${n2(tw.q85)}`
        + (us ? `　｜　美股 VIX <b>${n2(us.value)}</b>（${esc(us.date)}）` : '')
      : '台指自算值還在回補（FinMind 臺指選擇權每日行情）；先只顯示美股 VIX。';
    if (!el || !a || !a.chart) return;
    if (!tw && !us) { el.innerHTML = '<div class="empty">尚無資料</div>'; return; }
    const CH = a.CH || {};
    const ax = a.axisStyle || {};   // app.js 的共用軸樣式（物件，不是函式）
    const dates = [...new Set([...(tw ? tw.series.map((p) => p[0]) : []), ...(us ? us.series.map((p) => p[0]) : [])])].sort();
    const toMap = (s) => { const m = {}; (s || []).forEach((p) => { m[p[0]] = p[1]; }); return m; };
    const mt = toMap(tw && tw.series), mu = toMap(us && us.series);
    const start = Math.max(0, 100 - 250 / Math.max(1, dates.length) * 100);
    const mob = window.matchMedia && window.matchMedia('(max-width:640px)').matches;
    const ser = [];
    if (tw) ser.push({ name: '台指自算', type: 'line', data: dates.map((x) => (x in mt ? mt[x] : null)), connectNulls: true, showSymbol: false, lineStyle: { width: 1.8, color: CH.up }, itemStyle: { color: CH.up },
      markLine: tw.q85 != null ? { symbol: 'none', silent: true, lineStyle: { type: 'dashed', width: 1 }, label: { formatter: (p) => p.name, color: CH.ink3 || '#8a94a6', fontSize: 11 },
        data: [{ name: '50% 分位', yAxis: tw.q50, lineStyle: { color: CH.amber } }, { name: '85% 分位', yAxis: tw.q85, lineStyle: { color: CH.up } }] } : undefined });
    if (us) ser.push({ name: '美股 VIX', type: 'line', data: dates.map((x) => (x in mu ? mu[x] : null)), connectNulls: true, showSymbol: false, lineStyle: { width: 1.4, color: CH.cyan }, itemStyle: { color: CH.cyan } });
    S.chart = a.chart(el, {
      animation: false, grid: { left: 44, right: mob ? 12 : 64, top: 14, bottom: mob ? 64 : 58 },
      tooltip: { trigger: 'axis', valueFormatter: (v) => (v == null ? '—' : Number(v).toFixed(2)) },
      xAxis: Object.assign({ type: 'category', data: dates, boundaryGap: false }, ax, { splitLine: { show: false } }),
      yAxis: Object.assign({ type: 'value', scale: true, name: '年化 %', nameTextStyle: { fontSize: 11, color: CH.ink3 } }, ax),
      dataZoom: [{ type: 'inside', start, end: 100 }, { type: 'slider', start, end: 100, left: 44, right: mob ? 12 : 64, height: mob ? 30 : 22, bottom: 8, handleSize: mob ? '140%' : '100%', brushSelect: false }],
      series: ser,
    });
    if (window.App) window.App._fear = { n: dates.length, tw: tw ? tw.series.length : 0, us: us ? us.series.length : 0, open: true };
  }
  function toggle() { if (S.open) closeFull(); else load().then(openFull); }

  window.FearCard = { card, mounted, toggle, load, refresh, _s: S };
})();
