/* 台股資金輪動儀表板 v3 —— 前端只畫圖不運算（K 線指標除外，因為要能調參數）。
   路由：#overview / #flow / #industry / #industry/<chain> / #stock/<code> / #themes / #season
   台股慣例：紅漲綠跌。 */
(function () {
  'use strict';
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
  const D = {};                       // 已載入的 JSON
  const charts = {};                  // ECharts 實例
  const CH = { up: '#ff4d6d', down: '#2ee59d', cyan: '#3ee0ff', violet: '#8b7bff', amber: '#ffb454', lime: '#c3ff5b', ink2: '#a9b6d6', ink3: '#6f7ea3', line: '#1e2a48' };
  const PALETTE = ['#3ee0ff', '#8b7bff', '#ffb454', '#c3ff5b', '#ff8fab', '#5ec8ff', '#f9f871', '#7ee8c7', '#ff9f68', '#b39dff', '#6ee7b7', '#fca5a5', '#93c5fd', '#fde68a'];

  // ---------------------------------------------------------------- 工具
  const fmt = {
    n(v, d = 2) { if (v === null || v === undefined || Number.isNaN(v)) return '—'; return Number(v).toLocaleString('zh-TW', { minimumFractionDigits: d, maximumFractionDigits: d }); },
    i(v) { if (v === null || v === undefined) return '—'; return Math.round(v).toLocaleString('zh-TW'); },
    pct(v, d = 1) { if (v === null || v === undefined || Number.isNaN(v)) return '—'; const s = v > 0 ? '+' : ''; return s + Number(v).toFixed(d) + '%'; },
    yi(v) { if (v === null || v === undefined) return '—'; const a = Math.abs(v); if (a >= 1e8) return (v / 1e8).toFixed(a >= 1e10 ? 0 : 1) + ' 億'; if (a >= 1e4) return (v / 1e4).toFixed(0) + ' 萬'; return fmt.i(v); },
    lot(v) { if (v === null || v === undefined) return '—'; const a = Math.abs(v); if (a >= 1e4) return (v / 1e4).toFixed(1) + ' 萬張'; return fmt.i(v) + ' 張'; },
    cls(v) { return v > 0 ? 'up' : v < 0 ? 'down' : 'flat'; },
    esc(s) { return String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); },
  };
  const upDown = (v) => (v > 0 ? CH.up : v < 0 ? CH.down : CH.ink3);
  // #rrggbb + 透明度 → rgba()：色票只寫一份，要半透明時就地調
  const hexA = (hex, a) => {
    const h = String(hex || '').replace('#', '');
    const n = h.length === 3 ? h.split('').map(c => c + c).join('') : h;
    const v = parseInt(n || '888888', 16);
    return `rgba(${(v >> 16) & 255},${(v >> 8) & 255},${v & 255},${a})`;
  };
  const chgColor = (v, cap = 3) => { // 紅漲綠跌的連續色
    if (v === null || v === undefined) return '#334155';
    const t = Math.max(-1, Math.min(1, v / cap));
    return t >= 0 ? `rgba(255,77,109,${0.25 + 0.7 * t})` : `rgba(46,229,157,${0.25 + 0.7 * -t})`;
  };
  async function load(name, opt) {
    if (D[name] && !opt) return D[name];
    try { const r = await fetch(`data/${name}.json?v=${(D.meta && D.meta.generated_at) || ''}`, { cache: 'no-store' }); if (!r.ok) throw new Error(r.status); D[name] = await r.json(); }
    catch (e) { console.warn('載入失敗', name, e); D[name] = opt && opt.fallback !== undefined ? opt.fallback : null; }
    return D[name];
  }
  function chart(id, option, opts) {
    const el = typeof id === 'string' ? document.getElementById(id) : id; if (!el) return null;
    if (typeof echarts === 'undefined') { el.innerHTML = '<div class="empty">圖表函式庫載入失敗</div>'; return null; }
    el.classList.remove('isempty');
    let c = echarts.getInstanceByDom(el); if (!c) c = echarts.init(el, null, { renderer: 'canvas' });
    c.setOption(Object.assign({ backgroundColor: 'transparent', textStyle: { fontFamily: 'Noto Sans TC, JetBrains Mono, sans-serif', color: CH.ink2 }, animationDuration: 500 }, option), opts && opts.notMerge !== false);
    // 容器在 display:none 或還沒排版時 init 出來會是 0×0，畫完就是一片空白而且不會自己好。
    // 盯著容器尺寸，一變就 resize，這樣切分頁、展開說明、視窗縮放都不會留下空白圖。
    if (!el._ro && typeof ResizeObserver !== 'undefined') {
      el._ro = new ResizeObserver(() => {
        const i = echarts.getInstanceByDom(el);
        if (i && el.clientWidth > 0 && el.clientHeight > 0) i.resize();
      });
      el._ro.observe(el);
    }
    charts[el.id || Math.random()] = c; return c;
  }
  const axisStyle = { axisLine: { lineStyle: { color: CH.line } }, axisLabel: { color: CH.ink3, fontFamily: 'JetBrains Mono' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,.05)' } } };
  const tip = { backgroundColor: '#141e36', borderColor: '#2a3860', textStyle: { color: '#e8eeff', fontSize: 12.5 }, confine: true };
  // 沒東西可畫就把高度收掉，只留一行字 —— 不要留一個 420px 的黑方塊讓人以為壞了
  const empty = (id, msg) => {
    const el = typeof id === 'string' ? document.getElementById(id) : id; if (!el) return;
    const c = echarts.getInstanceByDom(el); if (c) c.dispose();
    el.classList.add('isempty');
    el.innerHTML = `<div class="empty">${msg || '尚無資料'}</div>`;
  };
  window.addEventListener('resize', () => { Object.values(charts).forEach(c => c && c.resize && c.resize()); });
  /* 瀏覽器縮放（Ctrl +/-）會改 devicePixelRatio，而 ECharts 是在 init 當下記住 DPR 的。
     只呼叫 resize() 的話畫布尺寸對了、內部座標還是舊 DPR，結果就是「圖縮到中間一小塊、周圍一片黑」
     （Andy 縮小視窗後熱力圖變一小塊就是這個）。DPR 一變就整個丟掉重建，沒有別的解法。 */
  let _dpr = window.devicePixelRatio || 1;
  (function watchDPR() {
    const onChange = () => {
      const d = window.devicePixelRatio || 1;
      if (d !== _dpr) {
        _dpr = d;
        Object.keys(charts).forEach(k => { try { charts[k].dispose(); } catch (e) { /* 已經沒了 */ } delete charts[k]; });
        Object.keys(rendered).forEach(k => delete rendered[k]);
        route();
      }
      try { matchMedia(`(resolution: ${d}dppx)`).addEventListener('change', onChange, { once: true }); }
      catch (e) { /* 舊瀏覽器沒有這個 media query，退回只靠 resize */ }
    };
    onChange();
  })();
  /* 滾輪放大：Andy 要「可以用滾輪放大，但縮小最多就是原始畫面」。
     三個關鍵：
     1. 不用 CSS transform 縮放 —— 那是把畫好的點陣圖拉大，字會糊。
        改成把內容的寬高乘上倍率，ECharts 用新尺寸重畫，放多大都清楚；SVG 本來就是向量。
     2. **外框高度在放大時鎖死**。不鎖的話卡片會被撐成 4 倍高，整頁版面都被推開
        （Andy：「放大部份會影響到整頁面」）。放大只在框內發生，框外的版面完全不動。
     3. 倍率下限是 1（原始畫面）；已經 1 倍還往下滾就不攔 wheel，讓頁面正常往下捲。 */
  function wheelZoom(box, opts) {
    if (!box || box._zoom) return box && box._zoom;
    const o = Object.assign({ max: 4, onZoom: null }, opts || {});
    // 捲動層自己包一層，徽章才不會跟著內容捲走
    let pane = box.querySelector(':scope > .zpane');
    if (!pane) {
      pane = document.createElement('div'); pane.className = 'zpane';
      while (box.firstChild) pane.appendChild(box.firstChild);
      box.appendChild(pane);
    }
    const inner = pane.firstElementChild; if (!inner) return null;
    let k = 1, baseH = 0, calm = 0;
    box.classList.add('zwrap');
    const badge = document.createElement('div');
    badge.className = 'zbadge'; badge.textContent = '滾輪放大';
    box.appendChild(badge);
    const setK = (nk) => {
      nk = Math.max(1, Math.min(o.max, nk));
      if (Math.abs(nk - k) < 0.001) return false;
      if (!baseH) baseH = inner.clientHeight || inner.offsetHeight || 320;
      k = nk;
      if (k <= 1.001) {
        inner.style.width = ''; inner.style.height = ''; pane.style.height = '';
        box.classList.remove('zoomed');
      } else {
        pane.style.height = baseH + 'px';           // ← 外框高度鎖住，卡片不會被撐高
        inner.style.width = (k * 100) + '%';
        inner.style.height = Math.round(baseH * k) + 'px';
        box.classList.add('zoomed');
      }
      badge.textContent = k <= 1.001 ? '滾輪放大　·　放大後可拖曳' : k.toFixed(1) + '×　拖曳移動　·　雙擊還原';
      if (o.onZoom) o.onZoom(k);
      return true;
    };
    pane.addEventListener('wheel', (e) => {
      const zin = e.deltaY < 0;
      /* 已經是原始大小又繼續往下滾 → 交還給頁面捲動。
         但「剛剛才還原成 1 倍」的那一瞬間不能馬上交還：使用者手還在滾，
         一放手整頁就被帶著往下衝（Andy：「還原成正常大小 他會導致整體頁面往下」）。
         所以還原後留 450ms 的緩衝，這段時間內的 wheel 一律吃掉，停手後才恢復正常捲動。 */
      if (!zin && k <= 1.001) {
        if (Date.now() < calm) { e.preventDefault(); e.stopPropagation(); calm = Date.now() + 450; }
        return;
      }
      e.preventDefault(); e.stopPropagation();
      const r = pane.getBoundingClientRect();
      const ox = e.clientX - r.left, oy = e.clientY - r.top;
      const px = (pane.scrollLeft + ox) / k, py = (pane.scrollTop + oy) / k;
      if (!setK(k * (zin ? 1.18 : 1 / 1.18))) return;
      if (k <= 1.001) { calm = Date.now() + 450; pane.scrollTo({ left: 0, top: 0 }); return; }
      pane.scrollLeft = px * k - ox; pane.scrollTop = py * k - oy;
    }, { passive: false });

    /* 放大後用游標直接抓著圖移動（Andy：「需要新增游標抓取可以移動功能」）。
       只在放大時生效，1 倍時不攔，才不會影響點方塊看成分股那些互動。 */
    let drag = null;
    pane.addEventListener('pointerdown', (e) => {
      if (k <= 1.001 || e.button !== 0) return;
      drag = { x: e.clientX, y: e.clientY, l: pane.scrollLeft, t: pane.scrollTop, moved: false, id: e.pointerId };
      box.classList.add('grabbing');
    });
    pane.addEventListener('pointermove', (e) => {
      if (!drag) return;
      const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
      if (!drag.moved && Math.abs(dx) + Math.abs(dy) < 4) return;   // 小抖動還算點擊
      if (!drag.moved) { drag.moved = true; try { pane.setPointerCapture(drag.id); } catch (err) { /* 忽略 */ } }
      e.preventDefault();
      pane.scrollLeft = drag.l - dx; pane.scrollTop = drag.t - dy;
    });
    const endDrag = (e) => {
      if (!drag) return;
      // 真的拖過就把接下來那一次 click 吃掉，不然放開手會順便點到圖上的方塊
      if (drag.moved) { pane.addEventListener('click', (c) => { c.stopPropagation(); c.preventDefault(); }, { capture: true, once: true }); }
      try { pane.releasePointerCapture(drag.id); } catch (err) { /* 忽略 */ }
      drag = null; box.classList.remove('grabbing');
    };
    pane.addEventListener('pointerup', endDrag);
    pane.addEventListener('pointercancel', endDrag);
    pane.addEventListener('pointerleave', endDrag);

    box.addEventListener('dblclick', () => { setK(1); pane.scrollTo({ left: 0, top: 0 }); calm = Date.now() + 450; });
    box._zoom = { reset: () => setK(1), get scale() { return k; } };
    return box._zoom;
  }

  const goStock = (code) => { location.hash = '#stock/' + code; };
  window.goStock = goStock;

  // ---------------------------------------------------------------- 全站互通：任何股票／族群／產業鏈／題材名稱都可點
  // 資料載入後建索引；各頁用 L.stock()/L.group()/L.theme() 產生連結，永遠連到同一個地方。
  const L = {
    gname: {}, gid: {}, gchain: {}, gcolor: {}, cname: {}, cgroup: {}, cmarket: {}, ctheme: {}, chains: {}, scolor: {}, gsegs: {}, sgroups: {}, all: [], ready: false,
    init(im, gt, cands, th, sc, all) {
      const gs = [];
      if (im) { (im.chains || []).forEach(c => { L.chains[c.id] = c.name; (c.groups || []).forEach(g => gs.push({ ...g, chain: c.id })); }); (im.industries || []).forEach(g => gs.push({ ...g, chain: 'industry' })); }
      (gt || []).forEach(g => gs.push({ id: g.group_id, name: g.group_name, chain: g.chain, members: [] }));
      gs.forEach((g, i) => { if (!L.gname[g.id]) { L.gname[g.id] = g.name; L.gid[g.name] = g.id; L.gchain[g.id] = g.chain; L.gcolor[g.id] = PALETTE[i % PALETTE.length]; } (g.members || []).forEach(m => { if (!L.cname[m.code]) { L.cname[m.code] = m.name; L.cgroup[m.code] = g.id; } if (m.market) L.cmarket[m.code] = m.market; }); });
      (cands || []).forEach(c => { L.cname[c.code] = c.name; if (c.group_id) L.cgroup[c.code] = c.group_id; if (c.market) L.cmarket[c.code] = c.market; });
      // 全市場索引：每一檔上市櫃股票都有個股頁，搜尋與連結都以這份為準
      L.all = all || [];
      L.all.forEach(c => { if (c.name) L.cname[c.code] = c.name; if (c.group_id) L.cgroup[c.code] = c.group_id; if (c.market) L.cmarket[c.code] = c.market; });
      ((th && th.themes) || []).forEach(t => (t.members || []).forEach(m => { (L.ctheme[m.code] = L.ctheme[m.code] || []).push({ id: t.id, name: t.name }); if (!L.cname[m.code]) L.cname[m.code] = m.name; }));
      // 供應鏈環節的顏色是全站唯一：剖析圖零件、環節色標、關聯圖、族群卡片、族群連結的圓點都用它
      ((sc && sc.segments) || []).forEach((sg, i) => { L.scolor[sg.id] = PALETTE[i % PALETTE.length]; });
      ((sc && sc.companies) || []).forEach(c => (c.groups || []).forEach(gn => { const gid = L.gid[gn]; if (!gid || !c.segment) return; const a = (L.gsegs[gid] = L.gsegs[gid] || []); if (!a.includes(c.segment)) a.push(c.segment); const b = (L.sgroups[c.segment] = L.sgroups[c.segment] || []); if (!b.includes(gid)) b.push(gid); }));
      // 沒有台股直接對應的環節（HBM、雲端業者）也要點得到東西：接到最相近的族群
      const FALLBACK = { hbm: ['memory'], hyperscaler: ['ai_server_odm'], switch: ['networking', 'ai_server_odm'], ic_design: ['ic_design'], foundry: ['foundry'], adv_pkg: ['advanced_packaging'], osat_test: ['osat'], abf_pcb: ['pcb_abf'], ccl: ['pcb_abf'], thermal: ['server_thermal'], power: ['server_power'], optical: ['optical_comm'], assembly: ['ai_server_odm'], ip_eda: ['silicon_ip'] };
      Object.entries(FALLBACK).forEach(([seg, gids]) => { if (!L.scolor[seg]) return; gids.filter(g => L.gname[g]).forEach(g => { const b = (L.sgroups[seg] = L.sgroups[seg] || []); if (!b.includes(g)) b.push(g); const a = (L.gsegs[g] = L.gsegs[g] || []); if (!a.includes(seg)) a.push(seg); }); });
      Object.keys(L.gsegs).forEach(gid => { L.gcolor[gid] = L.scolor[L.gsegs[gid][0]] || L.gcolor[gid]; });
      L.ready = true;
    },
    stock(code, name, o) { o = o || {}; const n = name || L.cname[code] || ''; return `<a class="lk lk-stock ${o.cls || ''}" href="#stock/${code}" title="看 ${fmt.esc(n)} 個股頁">${o.codeFirst ? `<span class="code">${code}</span>${fmt.esc(n)}` : `${fmt.esc(n)}<span class="code">${code}</span>`}</a>`; },
    group(gid, name, o) { o = o || {}; if (!gid) return fmt.esc(name || ''); const n = name || L.gname[gid] || gid; const col = L.gcolor[gid] || '#8ea0c4'; return `<a class="lk lk-group ${o.cls || ''}" href="#industry/group/${gid}" title="看「${fmt.esc(n)}」族群成分股" style="--c:${col}">${o.dot === false ? '' : '<i></i>'}${fmt.esc(n)}</a>`; },
    groupByName(name, o) { const gid = L.gid[name] || (L.gname['ind_' + name] ? 'ind_' + name : null); return gid ? L.group(gid, name, o) : fmt.esc(name || ''); },
    chain(cid, name, o) { o = o || {}; const n = name || L.chains[cid] || ({ industry: '法定產業別' })[cid] || cid; return `<a class="lk lk-chain ${o.cls || ''}" href="#industry/${cid}" title="看整條產業鏈">${fmt.esc(n)}</a>`; },
    theme(id, name, o) { o = o || {}; return `<a class="lk lk-theme ${o.cls || ''}" href="#themes/${id}" title="看題材">${fmt.esc(name)}</a>`; },
    themesOf(code) { return (L.ctheme[code] || []).map(t => L.theme(t.id, t.name)).join(''); },
    back() { return `<a class="lk lk-back" data-back="1" href="#" title="回上一頁">← 返回</a>`; },
  };
  window.Link = L;
  // 連結在表格列／卡片裡：點連結走連結，不要再觸發列的 onclick（Ctrl／中鍵仍可開新分頁）
  document.addEventListener('click', (e) => {
    const a = e.target.closest('a.lk'); if (!a) return;
    e.stopPropagation();
    if (e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey) return;
    if (a.dataset.back) { e.preventDefault(); if (history.length > 1) history.back(); else location.hash = '#industry'; return; }
    const h = a.getAttribute('href'); if (h && h.startsWith('#')) { e.preventDefault(); if (location.hash === h) route(); else location.hash = h; }
  }, true);

  // ---------------------------------------------------------------- 路由
  const VIEWS = ['overview', 'flow', 'market', 'industry', 'themes', 'season'];
  const rendered = {};
  async function route() {
    const h = location.hash.replace('#', '') || 'overview';
    const [head, ...rest] = h.split('/');
    let view = VIEWS.includes(head) ? head : head === 'stock' ? 'industry' : 'overview';
    $$('.tab').forEach(t => t.classList.toggle('on', t.dataset.view === view));
    $$('.view').forEach(v => v.classList.toggle('on', v.id === 'v-' + view));
    /* K 線「寬版」只在個股頁生效：離開個股頁要把右側事件欄還回來，
       不然使用者會覺得事件欄莫名其妙消失了（設定本身留著，回個股頁自動復原）。 */
    // 預設就是寬版（Andy：「K 線圖 default 就大一點」）；只有自己按過關掉才會是窄的
    let wide = true;
    try { const v = localStorage.getItem('tw.kwide'); if (v !== null) wide = v === '1'; } catch (e) { /* 忽略 */ }
    document.body.classList.toggle('kwide', head === 'stock' && wide);
    window.scrollTo({ top: 0 });
    if (view === 'industry') { await window.Industry.route(head, rest); return; }
    if (view === 'themes' && rendered.themes && D.themes && D.themes.themes) { renderThemeDetail(D.themes, rest[0] || D.themes.themes[0].id); return; }
    if (view === 'market' && rendered.market) { drawMarket(rest[0] || 'updown'); return; }
    if (!rendered[view]) { rendered[view] = true; await ({ overview: renderOverview, flow: renderFlow, market: renderMarket, themes: renderThemes, season: renderSeason })[view](); }
    setTimeout(() => Object.values(charts).forEach(c => c && c.resize && c.resize()), 30);
  }
  window.addEventListener('hashchange', route);
  $$('.tab').forEach(t => t.addEventListener('click', () => { location.hash = '#' + t.dataset.view; }));


  /* 總覽上方那排數字只是摘要，點下去到「市場明細」分頁看完整名單。
     Andy：「上面是簡說，點擊後會出現所有資訊」——
     所以不在總覽塞一個小面板，而是給它一個真的分頁，資訊可以鋪得開。 */
  const MKT = [
    ['updown', '漲跌家數'], ['ma', '站上均線'], ['top5', '資金集中'], ['cand', '今日候選'],
  ];
  function wireKpiDrill() {
    $$('#hero .kpi.clickable').forEach(k => k.onclick = () => { location.hash = '#market/' + k.dataset.drill; });
  }

  function stockTable(rows, cols) {
    if (!rows || !rows.length) return '<div class="empty">沒有符合的股票</div>';
    return `<div class="tw cap-lg"><table><thead><tr><th class="l">股票</th><th class="l">族群</th>`
      + cols.map(c => `<th>${c[0]}</th>`).join('') + `</tr></thead><tbody>`
      + rows.map(r => `<tr data-code="${r.code}"><td class="l">${L.stock(r.code, r.name)}</td>`
        + `<td class="l">${r.group_id ? L.group(r.group_id, r.group_name) : '<span class="muted">—</span>'}</td>`
        + cols.map(c => `<td class="num">${c[1](r)}</td>`).join('') + '</tr>').join('')
      + '</tbody></table></div>';
  }

  let mktKind = 'updown', mktTab = 0;
  async function renderMarket() {
    wireHowto($('#v-market'));
    await Promise.all([load('market_heat'), load('groups_today'), load('candidates'), load('groups_detail')]);
    $('#mktSeg2').innerHTML = MKT.map(([k, l]) => `<button data-k="${k}">${l}</button>`).join('');
    $$('#mktSeg2 button').forEach(b => b.onclick = () => { location.hash = '#market/' + b.dataset.k; });
    drawMarket((location.hash.split('/')[1]) || 'updown');
  }

  function drawMarket(kind) {
    if (!MKT.some(m => m[0] === kind)) kind = 'updown';
    if (kind !== mktKind) mktTab = 0;
    mktKind = kind;
    $$('#mktSeg2 button').forEach(b => b.classList.toggle('on', b.dataset.k === kind));
    const heat = D.market_heat || {}, b = heat.breadth || {}, mv = b.movers || {};
    const gt = D.groups_today || [], cands = D.candidates || [], gd = D.groups_detail || {};
    const body = $('#mktBody'); const title = $('#mktTitle');
    const PCT = ['漲跌', r => `<span class="${fmt.cls(r.chg_pct)}">${fmt.pct(r.chg_pct, 2)}</span>`];
    const CLOSE = ['收盤', r => fmt.n(r.close)];
    const TO = ['成交值', r => fmt.yi(r.turnover)];
    const bind = () => $$('#mktBody tr[data-code]').forEach(tr =>
      tr.onclick = (e) => { if (e.target.closest('a')) return; goStock(tr.dataset.code); });

    if (kind === 'updown') {
      title.innerHTML = `漲跌家數 <small>今天 ${heat.advancers || 0} 漲 / ${heat.decliners || 0} 跌，漲停 ${(mv.counts || {}).limit_up ?? '—'} 檔、跌停 ${(mv.counts || {}).limit_down ?? '—'} 檔</small>`;
      const sets = [
        ['漲停', mv.limit_up, '漲幅 ≥ 9.5%（成交價照檔位跳，實際常落在 9.7~10.0）'],
        ['跌停', mv.limit_down, '跌幅 ≤ -9.5%'],
        ['漲幅前段', mv.up, '今天漲最多的'],
        ['跌幅前段', mv.down, '今天跌最多的'],
        ['成交值前段', mv.turnover, '今天量最大的，這裡才是真正的戰場'],
      ].filter(t => t[1] && t[1].length);
      if (!sets.length) { body.innerHTML = '<div class="empty">今天沒有明細資料</div>'; return; }
      if (mktTab >= sets.length) mktTab = 0;
      const draw = () => {
        const t = sets[mktTab];
        $('#mktInner').innerHTML = `<div class="kpinote">${t[2]}</div>` + stockTable(t[1], [PCT, CLOSE, TO]);
        bind();
      };
      body.innerHTML = `<div class="seg" id="mktTabs">${sets.map((t, i) =>
        `<button data-i="${i}" class="${i === mktTab ? 'on' : ''}">${t[0]} <em>${t[1].length}</em></button>`).join('')}</div>`
        + `<div id="mktInner" style="margin-top:10px"></div>`;
      $$('#mktTabs button').forEach(btn => btn.onclick = () => {
        mktTab = +btn.dataset.i;
        $$('#mktTabs button').forEach(x => x.classList.toggle('on', x === btn)); draw();
      });
      draw();
      return;
    }

    if (kind === 'ma') {
      const gs = (b.by_group || []);
      title.innerHTML = `站上均線 <small>全市場 ${b.pct_above_ma20 ?? '—'}% 站上 MA20（樣本 ${b.n ?? '—'} 檔）</small>`;
      body.innerHTML = `<div class="kpinote">大盤的一個百分比看完不知道要幹嘛，拆到族群才知道是哪幾個在撐、哪幾個在拖。
        條越長＝這個族群越多成分股站在 20 日均線之上。點族群看成分股。</div>`
        + (gs.length ? `<div class="magrid">${gs.map(g => `<div class="ma" data-gid="${g.group_id}">
            <div class="n">${fmt.esc(g.group_name)}<em>${g.n} 檔</em></div>
            <div class="bar"><i style="width:${g.pct20}%;background:${g.pct20 >= 60 ? 'var(--rise)' : g.pct20 >= 40 ? 'var(--amber)' : 'var(--fall)'}"></i></div>
            <div class="v">MA20 ${g.pct20}%<span>MA60 ${g.pct60}%</span></div></div>`).join('')}</div>`
          : '<div class="empty">均線統計還在產生</div>');
      $$('#mktBody .ma[data-gid]').forEach(e => e.onclick = () => { location.hash = '#industry/group/' + e.dataset.gid; });
      return;
    }

    if (kind === 'top5') {
      const top = gt.slice().sort((a, c) => c.turnover - a.turnover).slice(0, 10);
      title.innerHTML = `資金集中 <small>前五大族群吃掉 ${heat.top5_share != null ? heat.top5_share.toFixed(1) + '%' : '—'} 的成交值</small>`;
      body.innerHTML = `<div class="kpinote">吃掉最多成交值的十個族群，以及每個族群裡量最大的成分股。
        越高＝行情越縮圈在主流，這時候買冷門股不容易動。</div>`
        + `<div class="top5grid">${top.map((g, i) => {
          const det = gd[g.group_id] || {};
          const ms = (det.members || []).slice().sort((a, c) => (c.turnover || 0) - (a.turnover || 0)).slice(0, 10);
          return `<div class="t5"><div class="h">${i + 1}. ${L.group(g.group_id, g.group_name)}<em>${fmt.n(g.turnover_share, 1)}%</em></div>
            <div class="m">${fmt.yi(g.turnover)}　<span class="${fmt.cls(g.chg_pct)}">${fmt.pct(g.chg_pct)}</span>　${g.constituents || 0} 檔</div>
            <div class="ls">${ms.map(m => L.stock(m.code, m.name)).join('') || '<span class="muted">成分股整理中</span>'}</div></div>`;
        }).join('')}</div>`;
      return;
    }

    // 今日候選
    const ab = cands.filter(c => c.grade === 'A' || c.grade === 'B');
    const use = ab.length ? ab : cands.slice().sort((a, c) => (c.score_all || 0) - (a.score_all || 0)).slice(0, 40);
    title.innerHTML = `今日候選 <small>${ab.length ? `A ${cands.filter(c => c.grade === 'A').length} 檔 / B ${cands.filter(c => c.grade === 'B').length} 檔` : '今天沒有 A / B'}</small>`;
    body.innerHTML = `<div class="kpinote">${ab.length
      ? 'A＝回檔承接、B＝突破追進。技術面永遠是最後一關，方向與估值要先過。'
      : '今天技術面沒有任何一檔達到 A / B（大盤走弱時很常見）。下面是綜合分最高的前 40 檔，當觀察名單就好，不是進場訊號。'}
      　完整的四面向理由在總覽的「今日候選」。</div>`
      + stockTable(use.map(c => ({ code: c.code, name: c.name, group_id: c.group_id, group_name: c.group,
          chg_pct: c.chg_pct, close: c.close, grade: c.grade, verdict: c.verdict, score: c.score_all })),
        [['判定', r => r.grade ? `<span class="grade ${r.grade}">${r.grade}</span>` : `<span class="muted">${fmt.esc(r.verdict || '—')}</span>`],
         ['綜合分', r => r.score != null ? fmt.n(r.score, 0) : '—'], PCT, CLOSE]);
    bind();
  }

  // ---------------------------------------------------------------- 總覽
  async function renderOverview() {
    wireHowto($('#v-overview'));
    const [heat, gt, rot, cands, f3, th, trust, gval] = await Promise.all([load('market_heat'), load('groups_today'), load('rotation'), load('candidates'), load('flow_v3'), load('themes'), load('trust_streak'), load('group_valuation'), load('groups_detail')]);
    // hero
    const b = (heat && heat.breadth) || {};
    const mv = b.movers || {};
    // KPI 點得開：只看到「567 / 1545」沒辦法做任何事，要能往下看是哪些股票（Andy）
    const kp = (l, v, d, cls, drill) => `<div class="card tight kpi${drill ? ' clickable' : ''}"${drill ? ` data-drill="${drill}"` : ''}>`
      + `<div class="l">${l}${drill ? '<span class="more">看明細 ›</span>' : ''}</div><div class="v ${cls || ''}">${v}</div><div class="d">${d || ''}</div></div>`;
    $('#hero').innerHTML = [
      // 加權指數是 mis 的 tse_t00.tw；盤中每分鐘跳一次（live.js）
      kp('加權指數', `<span data-live="idx" data-lc="t00">${fmt.n(heat && heat.taiex, 0)}</span>`,
         heat ? `<span class="${fmt.cls(heat.change)}" data-live="chg" data-lc="t00">${fmt.pct(heat.change / (heat.taiex - heat.change) * 100)}</span>` : '', heat && fmt.cls(heat.change)),
      kp('成交值', heat ? fmt.yi(heat.turnover) : '—', heat && heat.turnover_ma20 ? `20 日均 ${fmt.yi(heat.turnover_ma20)}` : ''),
      kp('漲 / 跌家數', heat ? `<span class="up">${heat.advancers}</span> <span class="muted">/</span> <span class="down">${heat.decliners}</span>` : '—',
         mv.counts ? `漲停 ${mv.counts.limit_up}　跌停 ${mv.counts.limit_down}　平盤 ${heat.unchanged}` : (heat ? `平盤 ${heat.unchanged}` : ''), '', mv.counts ? 'updown' : ''),
      kp('站上 MA20', b.pct_above_ma20 != null ? b.pct_above_ma20 + '%' : '—', `MA60 ${b.pct_above_ma60 ?? '—'}%　樣本 ${b.n ?? '—'}`,
         '', (b.by_group || []).length ? 'ma' : ''),
      kp('前五族群佔比', heat && heat.top5_share != null ? heat.top5_share.toFixed(1) + '%' : '—', '越高＝資金越集中', '', (gt || []).length ? 'top5' : ''),
      kp('今日候選', `<span class="up">${b.grade_a ?? 0}</span> A <span class="muted">/</span> <span class="amber">${b.grade_b ?? 0}</span> B`, '回檔承接 / 突破追進', '', 'cand'),
    ].join('');
    wireKpiDrill();
    renderHeat(gt, rot);
    renderRotation(f3 && f3.rrg, 5, { board: 'rotMini', clock: 'rotClockMini', compact: true });
    renderThemeStrip(th);
    renderCandidates(cands);
    renderBreadth(heat);
    renderTrust(trust, cands);
    renderGval(gval, rot, gt);
    /* Andy（09-13）：「將這邊的縮放功能取消」—— 滾輪縮放**只留熱力圖類**
       （總覽資金熱力、產業地圖板塊、題材資金熱力）。其餘的圖一律原尺寸顯示：
       徽章會壓在圖上、滾輪又會搶走頁面捲動，代價大於收益。 */
  }

  // 圖表下方的可點連結列：圖上點得到的東西，這裡也一定點得到（手機沒有 hover）
  function linkRow(afterId, html, label) {
    const el = document.getElementById(afterId); if (!el) return;
    // 圖被包進放大層時，連結列要掛在放大層外面，否則放大時會跟著被裁掉
    const at = el.closest('.zwrap') || el;
    let row = at.nextElementSibling; if (!row || !row.classList.contains('linkrow')) { row = document.createElement('div'); row.className = 'linkrow'; at.parentNode.insertBefore(row, at.nextSibling); }
    row.innerHTML = (label ? `<span class="muted">${label}</span>` : '') + html;
  }
  // 資金熱力圖：不用 treemap 的 roam 縮放 —— 它會把整張圖平移縮放，而且狀態留在 instance 裡，
  // 換分頁再回來就是一片空白（Andy 遇到的就是這個），而且「只能放大縮小整張圖」也解決不了小方塊看不到。
  // 改成產業鏈下鑽：上面一排晶片點半導體就只看半導體，點「全部」回到原來的圖。
  const CHAIN_NAME = { semiconductor: '半導體', ai_server: 'AI 伺服器', electronics: '一般電子',
    traditional: '傳產', infrastructure: '基礎建設', industry: '其他產業別' };
  let heatChain = null;

  /* 放大罩：熱力圖方塊太小看不清楚時，全螢幕看同一張圖。
     刻意不做「拖曳平移」—— treemap 一旦可以拖，整張圖就會被拖走而且回不來
     （Andy 遇到的空白畫面就是這樣來的）。要看細節就放大或下鑽，位置永遠固定。 */
  function openZoom(title, render) {
    const ov = $('#zoomOv'); if (!ov) return;
    $('#zoomTitle').textContent = title;
    ov.hidden = false;
    document.body.style.overflow = 'hidden';
    const close = () => {
      ov.hidden = true; document.body.style.overflow = '';
      const c = echarts.getInstanceByDom($('#zoomBody')); if (c) c.dispose();
      $('#zoomChips').innerHTML = '';
      document.removeEventListener('keydown', esc);
    };
    const esc = (e) => { if (e.key === 'Escape') close(); };
    document.addEventListener('keydown', esc);
    $('#zoomClose').onclick = close;
    ov.onclick = (e) => { if (e.target === ov) close(); };
    setTimeout(() => { render($('#zoomBody'), $('#zoomChips'), close); }, 30);
  }

  // 點方塊後在原地列出成分股（不跳頁），每一檔都點得進個股頁
  function heatPanel(panelId, gid, gname, extra) {
    const box = $('#' + panelId); if (!box) return;
    const det = (D.groups_detail || {})[gid] || {};
    const ms = (det.members || []).slice().sort((a, b) => (b.turnover || 0) - (a.turnover || 0)).slice(0, 40);
    box.hidden = false;
    box.innerHTML = `<div class="hh"><b>${fmt.esc(gname || det.group_name || gid)}</b>
        <span class="m">${extra || ''}</span><span class="sp"></span>
        <a class="pill cyan" href="#industry/group/${gid}">進族群頁 →</a>
        <button class="btn small" data-x="1">收起 ✕</button></div>
      ${ms.length ? `<div class="ms">${ms.map(m => `<a href="#stock/${m.code}"><span>${fmt.esc(m.name)}</span>
          <span class="c">${m.code}</span><span class="g ${fmt.cls(m.chg_pct)}">${fmt.pct(m.chg_pct)}</span></a>`).join('')}</div>`
        : '<div class="empty">這個族群的成分股整理中</div>'}`;
    const x = box.querySelector('[data-x]'); if (x) x.onclick = () => { box.hidden = true; };
    box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  // 熱力圖的 option 與資料（放大罩與原圖共用，才不會兩邊畫出不一樣的東西）
  function heatOption(gt, rot, chain, big) {
    const rotMap = {}; (rot || []).forEach(r => { rotMap[r.group_id] = r.rotation; });
    const chains = {}; gt.forEach(g => { const c = g.chain || 'industry'; (chains[c] = chains[c] || []).push(g); });
    const mk = (g) => ({ name: g.group_name, value: g.turnover, gid: g.group_id, chg: g.chg_pct,
      rot: rotMap[g.group_id], share: g.turnover_share,
      itemStyle: { color: chgColor(rotMap[g.group_id] != null ? rotMap[g.group_id] * 3 : g.chg_pct, 3) } });
    const inChain = chain && chains[chain] ? chains[chain] : null;
    const data = inChain ? inChain.map(mk)
      : Object.keys(chains).map(cid => ({ name: CHAIN_NAME[cid] || cid, cid, children: chains[cid].map(mk) }));
    return { chains, inChain, option: {
      tooltip: { ...tip, formatter: p => p.data.gid
        ? `<b>${p.name}</b><br>成交值 ${fmt.yi(p.value)}（${fmt.n(p.data.share, 1)}%）<br>漲跌 <span style="color:${upDown(p.data.chg)}">${fmt.pct(p.data.chg)}</span><br>資金流向 <span style="color:${upDown(p.data.rot)}">${p.data.rot != null ? (p.data.rot > 0 ? '流入 +' : '流出 ') + p.data.rot.toFixed(2) + ' pp' : '—'}</span><br><small>點一下看成分股</small>`
        : `<b>${p.name}</b><br><small>點一下只看這條產業鏈</small>` },
      series: [{ type: 'treemap', roam: false, nodeClick: false, breadcrumb: { show: false },
        width: '100%', height: '100%', top: 0, left: 0, visibleMin: inChain ? (big ? 5 : 20) : (big ? 40 : 120),
        /* 顏色＝資金流向（5日vs20日佔比），文字以前只寫漲跌 —— 於是出現「紅底寫 -0.7%」，
           使用者只會當成 bug。現在方塊上兩個數字都寫，而且標明哪個是哪個。 */
        label: { show: true, formatter: p => `${p.name}\n${fmt.pct(p.data.chg)}\n${p.data.rot != null ? '資金 ' + (p.data.rot > 0 ? '+' : '') + p.data.rot.toFixed(1) + 'pp' : '資金 —'}`,
          lineHeight: big ? 19 : 16,
          fontSize: big ? 15 : (inChain ? 14 : 13), color: '#fff', textShadowColor: '#000', textShadowBlur: 4, overflow: 'truncate' },
        upperLabel: { show: !inChain, height: big ? 26 : 22, color: '#a9b6d6', fontSize: big ? 13 : 12, backgroundColor: 'rgba(0,0,0,.25)' },
        itemStyle: { borderColor: '#0b1224', borderWidth: 2, gapWidth: 2 },
        levels: inChain ? [{ itemStyle: { gapWidth: 2 } }]
          : [{ itemStyle: { borderColor: '#0b1224', borderWidth: 3, gapWidth: 3 } }, { itemStyle: { gapWidth: 1 } }],
        data }] } };
  }

  function heatChips(chains, box, cur, onPick) {
    if (!box) return;
    const order = Object.keys(chains).sort((a, b) =>
      chains[b].reduce((s, g) => s + g.turnover, 0) - chains[a].reduce((s, g) => s + g.turnover, 0));
    box.innerHTML = `<button data-c="" class="${cur ? '' : 'on'}">全部</button>`
      + order.map(cid => {
        const sh = chains[cid].reduce((s, g) => s + (g.turnover_share || 0), 0);
        return `<button data-c="${cid}" class="${cur === cid ? 'on' : ''}">${CHAIN_NAME[cid] || cid}<em>${fmt.n(sh, 1)}%</em></button>`;
      }).join('');
    $$('button', box).forEach(b => b.onclick = () => onPick(b.dataset.c || null));
  }

  function renderHeat(gt, rot) {
    if (!gt || !gt.length) return empty('heat');
    const { chains, inChain, option } = heatOption(gt, rot, heatChain, false);
    if (heatChain && !chains[heatChain]) heatChain = null;
    heatChips(chains, $('#heatChips'), heatChain, (c) => { heatChain = c; renderHeat(gt, rot); });
    const list = inChain || gt.filter(g => !g.group_id.startsWith('ind_'));
    linkRow('heat', list.slice().sort((a, b) => b.turnover - a.turnover).slice(0, 14)
      .map(g => L.group(g.group_id, g.group_name)).join(''), '族群');
    const c = chart('heat', option);
    wheelZoom($('#heatWrap'), { onZoom: () => { const i = echarts.getInstanceByDom($('#heat')); if (i) i.resize(); } });
    if (c) c.off('click').on('click', p => {
      if (!p.data) return;
      if (p.data.gid) heatPanel('heatPanel', p.data.gid, p.name,
        `成交值 ${fmt.yi(p.value)}（${fmt.n(p.data.share, 1)}%）　${fmt.pct(p.data.chg)}`);
      else if (p.data.cid) { heatChain = p.data.cid; renderHeat(gt, rot); }
    });
    const zb = $('#heatZoom');
    if (zb) zb.onclick = () => openZoom('資金熱力圖', (body, chipBox) => {
      let ch = heatChain;
      const draw = () => {
        const r = heatOption(gt, rot, ch, true);
        heatChips(r.chains, chipBox, ch, (c2) => { ch = c2; draw(); });
        const bc = chart(body, r.option);
        if (bc) bc.off('click').on('click', p => {
          if (!p.data) return;
          if (p.data.gid) location.hash = '#industry/group/' + p.data.gid;
          else if (p.data.cid) { ch = p.data.cid; draw(); }
        });
      };
      draw();
    });
  }

  const STAGE = {
    improving: { name: '改善', color: '#3ee0ff', sub: '還是比大盤弱，但動能轉強了', act: '資金剛開始進場，最早可以布局的一段' },
    leading: { name: '領先', color: '#ff4d6d', sub: '比大盤強，而且還在變強', act: '現在的主流，回檔找買點、不要追高' },
    weakening: { name: '轉弱', color: '#ffb454', sub: '還是比大盤強，但動能在掉', act: '主流開始鬆動，手上有的先設好停利' },
    lagging: { name: '落後', color: '#2ee59d', sub: '比大盤弱，而且還在變弱', act: '資金還在跑，別急著抄底' },
  };
  const STAGE_ORDER = ['improving', 'leading', 'weakening', 'lagging'];
  const stageOf = (x, y) => (x >= 100 ? (y >= 100 ? 'leading' : 'weakening') : (y >= 100 ? 'improving' : 'lagging'));

  function rotRows(rrg, back) {
    return (rrg && rrg.points ? rrg.points : []).map(p => {
      const t = p.trail || [];
      const prev = t.length > back ? t[t.length - 1 - back] : null;
      const was = prev ? stageOf(prev[1], prev[2]) : null;
      return {
        gid: p.group_id, name: p.group_name, share: p.share || 0, trail: t,
        rs: p.x, mo: p.y, stage: p.quadrant || stageOf(p.x, p.y),
        was, moved: was && was !== (p.quadrant || stageOf(p.x, p.y)),
        dmo: prev ? p.y - prev[2] : null, drs: prev ? p.x - prev[1] : null,
      };
    }).sort((a, b) => b.share - a.share);
  }

  // 一列族群：名稱、相對大盤強弱、動能方向、成交值佔比
  function rotItem(r) {
    const arrow = r.dmo == null ? '' : r.dmo > 0.15 ? '<span class="ar up">↑</span>' : r.dmo < -0.15 ? '<span class="ar dn">↓</span>' : '<span class="ar fl">→</span>';
    return `<li data-gid="${r.gid}"><span class="g">${fmt.esc(r.name)}</span>${arrow}
      <span class="m">強弱 ${r.rs >= 100 ? '+' : ''}${fmt.n(r.rs - 100, 1)}　佔比 ${fmt.n(r.share, 1)}%</span></li>`;
  }

  /* 資金輪動時鐘：Andy 看不懂 RRG 的 XY 散布圖（「完全看不懂這張圖」），
     但「時鐘」人人都懂 —— 圓盤切成四段，資金照順時針一段一段跑：
       落後 → 改善 → 領先 → 轉弱 → 回到落後。
     每個族群是一顆點，點在哪一段就代表現在在哪個階段；
     尾巴是牠這幾天走過的路，看得出來是正在往前跑還是倒退。
     離圓心越遠＝和大盤的差距越大，圓心附近＝跟大盤差不多。 */
  const CLOCK_SECTOR = [   // 角度由 0° 起算、逆時針；和 stageOf 的四象限對齊
    { from: 0, to: 90, k: 'leading' },      // 右上：比大盤強且還在變強
    { from: 90, to: 180, k: 'improving' },  // 左上：還弱但動能轉強
    { from: 180, to: 270, k: 'lagging' },   // 左下：又弱又還在變弱
    { from: 270, to: 360, k: 'weakening' }, // 右下：還強但動能在掉
  ];
  const CLOCK_MAXR = 1.25;

  function renderRotClock(rows, back, id, compact) {
    const el = $('#' + id); if (!el) return;
    const cap = compact ? 10 : 16;
    const top0 = rows.slice(0, cap);                     // rotRows 已照成交值佔比排序
    if (!top0.length) return empty(id, '輪動時鐘需要至少 20 個交易日');
    /* 兩個軸的尺度差很多：相對強弱常常差好幾點，動能只差零點幾。
       直接拿原始值算角度，所有族群會擠在水平線上（＝兩段的交界），根本看不出在哪一段。
       所以各自除以自己的最大偏離量再算角度 —— 正負號沒動，四段的歸屬完全不變，
       但分佈攤得開，一眼就看得出誰在哪一段、離中心多遠。 */
    const sx = Math.max(1e-6, ...top0.map(r => Math.abs((r.rs || 100) - 100)));
    const sy = Math.max(1e-6, ...top0.map(r => Math.abs((r.mo || 100) - 100)));
    const pos = (x, y) => {                              // (相對強弱, 動能) → [半徑, 角度]
      const dx = ((x || 100) - 100) / sx, dy = ((y || 100) - 100) / sy;
      let a = Math.atan2(dy, dx) * 180 / Math.PI; if (a < 0) a += 360;
      return [Math.min(CLOCK_MAXR, Math.sqrt(dx * dx + dy * dy)), a];
    };
    const pts = top0.map(r => ({ ...r, p: pos(r.rs, r.mo) }));
    const top = pts;
    const maxR = CLOCK_MAXR;
    /* 尾巴只畫「N 天前 → 現在」一條直線：畫整段實際軌跡會變成一團毛線，
       反而看不出來在往哪走。小圈圈是 N 天前的位置，線另一頭的大點就是現在。 */
    const trail = (r) => {
      const t = r.trail || [];
      const prev = t.length > back ? t[t.length - 1 - back] : t[0];
      if (!prev) return [];
      return [pos(prev[1], prev[2]), pos(r.rs, r.mo)];
    };
    const sectorColor = {};
    CLOCK_SECTOR.forEach(s => { sectorColor[s.k] = STAGE[s.k].color; });
    const areaColors = CLOCK_SECTOR.flatMap(s => [hexA(STAGE[s.k].color, .13), hexA(STAGE[s.k].color, .13)]);
    const o = {
      tooltip: {
        ...tip, trigger: 'item', formatter: (q) => {
          const r = q.data && q.data.row; if (!r) return '';
          const s = STAGE[r.stage];
          return `<b>${fmt.esc(r.name)}</b>　<span style="color:${s.color}">${s.name}</span>`
            + `<br>相對大盤強弱 ${r.rs >= 100 ? '+' : ''}${fmt.n(r.rs - 100, 2)}`
            + `<br>動能 ${r.mo >= 100 ? '+' : ''}${fmt.n(r.mo - 100, 2)}`
            + (r.was ? `<br>${back} 天前在「${STAGE[r.was].name}」${r.moved ? '　<b>已經換段</b>' : ''}` : '')
            + `<br>成交值佔比 ${fmt.n(r.share, 1)}%<br><small>點一下看成分股</small>`;
        },
      },
      polar: { center: ['50%', compact ? '52%' : '52%'], radius: compact ? '60%' : '72%' },
      angleAxis: {
        type: 'value', min: 0, max: 360, startAngle: 0, clockwise: false, interval: 45,
        axisLine: { show: false }, axisTick: { show: false },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,.08)' } },
        splitArea: { show: true, areaStyle: { color: areaColors } },
        axisLabel: {
          margin: compact ? 6 : 10, fontSize: compact ? 12 : 14, fontWeight: 700,
          formatter: (v) => { const s = CLOCK_SECTOR.find(z => Math.abs((z.from + z.to) / 2 - v) < 1); return s ? STAGE[s.k].name : ''; },
          color: (v) => { const s = CLOCK_SECTOR.find(z => Math.abs((z.from + z.to) / 2 - v) < 1); return s ? STAGE[s.k].color : 'transparent'; },
        },
      },
      // 外圈留一點餘裕，被夾住的「N 天前」小圈圈才不會壓在盤緣上
      radiusAxis: { type: 'value', min: 0, max: maxR * 1.08, axisLine: { show: false }, axisTick: { show: false },
        axisLabel: { show: false }, splitLine: { lineStyle: { color: 'rgba(255,255,255,.06)' } } },
      series: [
        // 尾巴：這幾天走過的路
        ...top.map(r => ({
          // 只在「N 天前」那一端點一個小圈圈（line series 的 symbol 不吃陣列，要用 symbolSize 挑）
          type: 'line', coordinateSystem: 'polar', silent: true, symbol: 'circle',
          symbolSize: (v, q) => (q.dataIndex === 0 ? 6 : 0), data: trail(r), z: 2,
          itemStyle: { color: hexA(STAGE[r.stage].color, .55) },
          lineStyle: { color: hexA(STAGE[r.stage].color, .42), width: 1.6 },
        })),
        // 現在的位置
        {
          type: 'scatter', coordinateSystem: 'polar', z: 5,
          data: top.map(r => ({ value: [Math.min(r.p[0], maxR), r.p[1]], row: r,
            itemStyle: { color: STAGE[r.stage].color, borderColor: '#0b0f1a', borderWidth: 1.5,
              shadowBlur: r.moved ? 14 : 0, shadowColor: STAGE[r.stage].color },
            // 左半邊的點把名字放左邊、右半邊放右邊，字才不會全部擠在同一側疊住
            label: { position: r.p[1] > 95 && r.p[1] < 265 ? 'left' : 'right' } })),
          symbolSize: (v, q) => { const r = q.data.row; return Math.max(9, Math.min(26, 8 + Math.sqrt(r.share) * 5)); },
          label: { show: !compact, distance: 7, color: CH.ink2, fontSize: 11.5,
            textBorderColor: '#0b0f1a', textBorderWidth: 3,
            formatter: (q) => q.data.row.name },
          labelLayout: { hideOverlap: true },
        },
      ],
      graphic: compact ? [] : [{
        type: 'text', right: 12, bottom: 8, silent: true,
        style: { text: '↻ 資金照順時針轉：落後 → 改善 → 領先 → 轉弱\n圈圈越大＝成交值佔比越高　·　離圓心越遠＝和大盤差越多',
          fill: 'rgba(232,238,255,.34)', fontSize: 11.5, lineHeight: 16, textAlign: 'right' },
      }],
    };
    // 尾巴是一族群一條線，族群數一變 series 數就變；不用 notMerge 會留下上一次的殘線
    const c = chart(id, o, { notMerge: true });
    if (c) c.off('click').on('click', q => { const r = q.data && q.data.row; if (r) location.hash = '#industry/group/' + r.gid; });
    if (!compact) linkRow(id, top.map(r => L.group(r.gid, r.name)).join(''));
  }

  function renderRotation(rrg, back, ids) {
    const rows = rotRows(rrg, back);
    const board = $('#' + ids.board);
    if (!rows.length) {
      if (board) board.innerHTML = '<div class="empty">相對輪動需要至少 20 個交易日</div>';
      if (ids.clock) empty(ids.clock, '輪動時鐘需要至少 20 個交易日');
      return;
    }
    if (ids.clock) renderRotClock(rows, back, ids.clock, !!ids.compact);

    if (ids.cycle) {
      const cy = $('#' + ids.cycle);
      if (cy) cy.innerHTML = STAGE_ORDER.map((k, i) =>
        `<span class="st" style="background:${STAGE[k].color}1f;color:${STAGE[k].color};border:1px solid ${STAGE[k].color}55">${STAGE[k].name}</span>`
        + (i < 3 ? '<span class="ar">→</span>' : '<span class="ar">↩ 回到改善</span>')).join('');
    }
    if (ids.move) {
      const mv = $('#' + ids.move);
      const moved = rows.filter(r => r.moved);
      if (mv) mv.innerHTML = moved.length
        ? `<b>最近 ${back} 個交易日換階段的族群</b>` + moved.slice(0, 10).map(r =>
          `<span class="mv" data-gid="${r.gid}"><i style="background:${STAGE[r.was].color}"></i>${STAGE[r.was].name}
             <em>→</em><i style="background:${STAGE[r.stage].color}"></i>${STAGE[r.stage].name}
             <b>${fmt.esc(r.name)}</b></span>`).join('')
        : `<b>最近 ${back} 個交易日沒有族群換階段</b><span class="muted">代表輪動很慢，主流還是同一批</span>`;
      if (mv) $$('.mv', mv).forEach(e => e.onclick = () => { location.hash = '#industry/group/' + e.dataset.gid; });
    }

    const cap = ids.compact ? 4 : 12;
    board.innerHTML = STAGE_ORDER.map(k => {
      const list = rows.filter(r => r.stage === k);
      const s = STAGE[k];
      return `<div class="stage" style="--c:${s.color}">
        <div class="sh"><b style="color:${s.color}">${s.name}</b><span class="n">${list.length}</span></div>
        <div class="sd">${s.sub}<br><em>${s.act}</em></div>
        <ul>${list.slice(0, cap).map(rotItem).join('') || '<li class="none">這個階段目前沒有族群</li>'}
        ${list.length > cap ? `<li class="none">還有 ${list.length - cap} 個</li>` : ''}</ul></div>`;
    }).join('');
    $$('li[data-gid]', board).forEach(li => li.onclick = () => { location.hash = '#industry/group/' + li.dataset.gid; });
  }

  function renderThemeStrip(th) {
    const el = $('#themeStrip'); if (!th || !th.themes || !th.themes.length) { el.innerHTML = '<div class="empty">尚無題材資料</div>'; return; }
    el.innerHTML = `<div class="tiles">` + th.themes.slice(0, 8).map(t => `<div class="tile" onclick="location.hash='#themes/${t.id}'"><div class="t">${fmt.esc(t.name)}</div><div class="m">${t.n} 檔 · 佔比 ${fmt.n(t.share, 1)}% · 新聞 ${t.news7}</div><div class="v"><span style="color:${t.heat >= 70 ? CH.up : t.heat >= 45 ? CH.amber : CH.ink2}">熱度 ${t.heat}</span> <small class="${fmt.cls(t.chg_pct)}" style="font-size:12px">${fmt.pct(t.chg_pct)}</small></div><div class="lks">${(t.members || []).slice(0, 4).map(m => L.stock(m.code, m.name)).join('')}</div></div>`).join('') + '</div>';
  }

  // ---- 候選名單：綜合／籌碼／技術／基本面四種切法 ----------------------------
  const num = (v, d = 1) => `<span class="num">${v != null ? fmt.n(v, d) : '—'}</span>`;
  const C = {
    grade: ['grade', '判定', r => `<span class="grade ${r.grade || 'W'}">${r.grade ? r.grade + ' ' + r.verdict : r.verdict}</span>`, 'l'],
    code: ['code', '代號', r => `<span class="mono">${r.code}</span>`, 'l'],
    name: ['name', '簡稱', r => L.stock(r.code, r.name), 'l'],
    group: ['group', '族群', r => L.group(r.group_id, r.group), 'l'],
    // data-live / data-lc 是給 live.js 認的：盤中每分鐘把這兩格換成即時價。
    // 只標記，不改算法 —— 收盤後這兩格仍然是資料湖裡的收盤價。
    close: ['close', '收盤', r => `<span class="num" data-live="close" data-lc="${r.code}">${r.close != null ? fmt.n(r.close) : '—'}</span>`],
    chg: ['chg_pct', '漲跌', r => `<span class="num ${fmt.cls(r.chg_pct)}" data-live="chg" data-lc="${r.code}">${fmt.pct(r.chg_pct, 2)}</span>`],
    sAll: ['score_all', '綜合', r => num(r.score_all, 0)],
    sChip: ['score_chip', '籌碼', r => num(r.score_chip, 0)],
    sTech: ['score_tech', '技術', r => num(r.score_tech, 0)],
    sFund: ['score_fund', '基本', r => num(r.score_fund, 0)],
    tech: ['tech_score', '技術分', r => num(r.tech_score, 0)],
    rsi: ['rsi', 'RSI', r => num(r.rsi, 0)],
    bias: ['bias20', '乖離', r => `<span class="num">${fmt.pct(r.bias20)}</span>`],
    vol: ['vol_ratio', '量比', r => num(r.vol_ratio, 1)],
    stop: ['stop', '停損', r => num(r.stop)],
    rr: ['rr', '風報比', r => num(r.rr, 1)],
    pe: ['pe', '本益比', r => num(r.pe, 1)],
    pct: ['pe_percentile', '同業分位', r => `<span class="num">${r.pe_percentile != null ? fmt.n(r.pe_percentile, 0) + '%' : '—'}</span>`],
    yoy: ['rev_yoy', '營收YoY', r => `<span class="num ${fmt.cls(r.rev_yoy)}">${fmt.pct(r.rev_yoy)}</span>`],
    streak: ['rev_streak', '連增月', r => `<span class="num">${r.rev_streak != null ? r.rev_streak + ' 月' : '—'}</span>`],
    mom: ['momentum_score', '動能分', r => num(r.momentum_score, 0)],
    trust: ['trust_net', '投信', r => `<span class="num ${fmt.cls(r.trust_net)}">${r.trust_net != null ? fmt.lot(r.trust_net / 1000) : '—'}</span>`],
    foreign: ['foreign_net', '外資', r => `<span class="num ${fmt.cls(r.foreign_net)}">${r.foreign_net != null ? fmt.lot(r.foreign_net / 1000) : '—'}</span>`],
    turn: ['avg_turnover', '日均量', r => `<span class="num">${r.avg_turnover != null ? fmt.yi(r.avg_turnover) : '—'}</span>`],
  };
  const HEAD = [C.grade, C.code, C.name, C.group, C.close, C.chg];
  const FACETS = {
    all: { label: '綜合', sub: '四面向加權', key: 'score_all',
      hint: '綜合分 = 技術 40% + 籌碼 30% + 基本面 30%（某一面向沒資料時，權重按比例分給其他面向）。每一列下方寫出這一檔在這個面向被挑中的實際理由。',
      cols: [...HEAD, C.sAll, C.sChip, C.sTech, C.sFund, C.pe, C.rr] },
    chip: { label: '籌碼', sub: '法人與大戶', key: 'score_chip',
      hint: '籌碼分看的是「誰在買」：投信／外資連續買超天數、法人五日淨買佔同期成交值的比例、集保大戶（400 張以上）四週持股增減、券商調升目標價。買超金額要相對於這檔自己的量才有意義，所以用佔比而不是絕對張數。',
      cols: [...HEAD, C.sChip, C.trust, C.foreign, C.turn, C.sAll] },
    tech: { label: '技術', sub: '結構與時機', key: 'score_tech',
      hint: '技術分把指標分、SMC 結構判定（A 回檔承接 / B 突破追進）、均線位置、風報比、量能與乖離合成一個分數。被硬性條件排除的（流動性不足、漲停鎖死、乖離過大）會直接扣分，理由列會寫出被排除的原因。',
      cols: [...HEAD, C.sTech, C.tech, C.rsi, C.vol, C.bias, C.stop, C.rr] },
    fund: { label: '基本面', sub: '營收與估值', key: 'score_fund',
      hint: '基本面分來自月營收動能（YoY 經 1-2 月合併調整、連增月數、近三月合計 YoY）與同族群估值分位。分位低 = 相對同業便宜。營收 YoY 超過 100% 會標示可能是併購或一次性，不當成長看。',
      cols: [...HEAD, C.sFund, C.yoy, C.streak, C.mom, C.pe, C.pct] },
  };
  let candFacet = 'all';
  let candSort = { key: null, dir: 1 };
  let candOpen = null;
  /* 族群篩選（Andy：「可勾選特定族群，下拉清單那樣，可以參考 EXCEL」）：
     null ＝ 全部；是 Set 就只看勾起來的那幾個（全部取消勾選＝什麼都不顯示，跟 Excel 一樣）。
     選擇存 localStorage，重新整理、換面向都還在。 */
  let candGroups = (() => {
    try { const v = JSON.parse(localStorage.getItem('tw.candGroups') || 'null'); return Array.isArray(v) ? new Set(v) : null; }
    catch (e) { return null; }
  })();
  const saveCandGroups = () => {
    try {
      if (candGroups) localStorage.setItem('tw.candGroups', JSON.stringify([...candGroups]));
      else localStorage.removeItem('tw.candGroups');
    } catch (e) { /* 忽略 */ }
  };

  function whyHtml(r, facet) {
    const w = (r.why || {})[facet] || {};
    const bits = (w.pros || []).map(t => `<span class="pro">✓ ${fmt.esc(t)}</span>`)
      .concat((w.cons || []).map(t => `<span class="con">！ ${fmt.esc(t)}</span>`));
    return bits.length ? `<div class="why">${bits.join('')}</div>`
      : '<div class="why"><span>這一檔在這個面向沒有明顯的理由，只是相對排名靠前</span></div>';
  }

  /* Excel 欄位篩選那種下拉：搜尋框 ＋ 全選／全部清除 ＋ 勾選清單（每個族群後面是筆數）。
     點面板以外的地方就收起來；勾一個就立刻重畫表格。 */
  function renderCandFilter(cands) {
    const host = $('#candGroupFilter'); if (!host) return;
    const counts = new Map();
    cands.forEach(r => { const g = r.group || '（未分類）'; counts.set(g, (counts.get(g) || 0) + 1); });
    const all = [...counts.keys()].sort((a, b) => counts.get(b) - counts.get(a) || a.localeCompare(b, 'zh-Hant'));
    const labelOf = (g) => !g ? '全部族群'
      : g.size === 0 ? '沒有勾選任何族群'
      : g.size === 1 ? [...g][0]
      : `已選 ${g.size} 個族群`;
    const sel = candGroups;
    host.innerHTML = `<button class="btn small ${sel ? 'on' : ''}" id="cgBtn"
        title="只看勾起來的族群（像 Excel 的欄位篩選）">族群：${fmt.esc(labelOf(sel))} ▾</button>
      <div class="cgpop" id="cgPop" hidden>
        <input id="cgSearch" placeholder="搜尋族群…" autocomplete="off">
        <div class="cgact"><button class="btn small" id="cgAll">全選</button>
          <button class="btn small" id="cgNone">全部清除</button>
          <span class="muted" id="cgCount"></span></div>
        <div class="cglist" id="cgList">${all.map(g => `
          <label data-g="${fmt.esc(g)}"><input type="checkbox" value="${fmt.esc(g)}"
            ${!sel || sel.has(g) ? 'checked' : ''}><span>${fmt.esc(g)}</span><em>${counts.get(g)}</em></label>`).join('')}</div>
      </div>`;
    const pop = $('#cgPop', host), btn = $('#cgBtn', host);
    const boxes = () => $$('#cgList input[type=checkbox]', host);
    const paintCount = () => { const n = boxes().filter(b => b.checked).length;
      $('#cgCount', host).textContent = `${n} / ${all.length}`; };
    const apply = () => {
      const on = boxes().filter(b => b.checked).map(b => b.value);
      candGroups = on.length === all.length ? null : new Set(on);
      saveCandGroups(); paintCount();
      btn.textContent = `族群：${labelOf(candGroups)} ▾`;
      btn.classList.toggle('on', !!candGroups);
      renderCandidates(cands, { keepOpen: true });
    };
    btn.onclick = (e) => { e.stopPropagation(); pop.hidden = !pop.hidden; if (!pop.hidden) $('#cgSearch', host).focus(); };
    pop.onclick = (e) => e.stopPropagation();
    $('#cgSearch', host).oninput = (e) => {
      const q = e.target.value.trim().toLowerCase();
      $$('#cgList label', host).forEach(l => { l.hidden = !!q && !l.dataset.g.toLowerCase().includes(q); });
    };
    $('#cgAll', host).onclick = () => { boxes().forEach(b => { if (!b.closest('label').hidden) b.checked = true; }); apply(); };
    $('#cgNone', host).onclick = () => { boxes().forEach(b => { if (!b.closest('label').hidden) b.checked = false; }); apply(); };
    boxes().forEach(b => b.onchange = apply);
    paintCount();
    if (!renderCandFilter._wired) {          // 點面板外面收起來，只掛一次
      document.addEventListener('click', () => { const q = document.getElementById('cgPop'); if (q) q.hidden = true; });
      renderCandFilter._wired = true;
    }
  }

  function renderCandidates(cands, opt) {
    if (!cands) return;
    if (!(opt && opt.keepOpen)) renderCandFilter(cands);
    const F = FACETS[candFacet], cols = F.cols;
    $('#candFacets').innerHTML = Object.keys(FACETS).map(k =>
      `<button data-f="${k}" class="${k === candFacet ? 'on' : ''}"><b>${FACETS[k].label}</b><em>${FACETS[k].sub}</em></button>`).join('');
    $$('#candFacets button').forEach(b => b.onclick = () => {
      candFacet = b.dataset.f; candSort = { key: null, dir: 1 }; candOpen = null; renderCandidates(cands);
    });
    $('#candHint').textContent = F.hint;

    const sk = candSort.key || F.key;
    const dir = candSort.key ? candSort.dir : -1;
    // candGroups === null ＝ 全部；是 Set 就只看勾起來的
    const pool = candGroups ? cands.filter(r => candGroups.has(r.group || '（未分類）')) : cands;
    const rows = pool.slice().sort((a, b) => {
      const x = a[sk], y = b[sk];
      if (x == null && y == null) return 0;
      if (x == null) return 1;
      if (y == null) return -1;
      return (x > y ? 1 : x < y ? -1 : 0) * dir;
    });

    $('#candTable thead').innerHTML = '<tr>' + cols.map(c =>
      `<th class="${c[3] || ''}" data-k="${c[0]}">${c[1]}${sk === c[0] ? (dir > 0 ? ' ▲' : ' ▼') : ''}</th>`).join('') + '</tr>';
    $('#candBody').innerHTML = rows.slice(0, 60).map(r => {
      const tr = `<tr data-code="${r.code}">` + cols.map(c => `<td class="${c[3] || ''}">${c[2](r)}</td>`).join('') + '</tr>';
      return r.code === candOpen
        ? tr + `<tr class="whyrow"><td colspan="${cols.length}">${whyHtml(r, candFacet)}</td></tr>` : tr;
    }).join('') || `<tr><td colspan="${cols.length}" class="l muted">勾選的族群今天沒有候選股，換幾個族群或按「全選」</td></tr>`;
    const cn = $('#candNum');
    if (cn) cn.textContent = candGroups
      ? `${rows.length} 檔（已篩 ${candGroups.size} 個族群，全部 ${cands.length} 檔）`
      : `${rows.length} 檔`;
    $$('#candTable th').forEach(th => th.onclick = () => {
      const k = th.dataset.k;
      candSort = { key: k, dir: candSort.key === k ? -candSort.dir : -1 };
      renderCandidates(cands);
    });
    // 單擊展開「為何選它」，再點一次收起；要看個股頁用簡稱那個連結
    $$('#candBody tr[data-code]').forEach(tr => tr.onclick = (e) => {
      if (e.target.closest('a')) return;
      candOpen = candOpen === tr.dataset.code ? null : tr.dataset.code;
      renderCandidates(cands);
    });
    // 表格比容器寬時會橫向捲動，理由那一列如果跟著撐開就會被推到畫面外。
    // 把它釘在捲動容器的左邊、寬度綁住容器，理由才會在看得到的地方換行。
    const box = $('#candTable').closest('.tw');
    $$('#candBody .why').forEach(el => {
      el.style.position = 'sticky';
      el.style.left = '0';
      el.style.width = Math.max(280, box.clientWidth - 24) + 'px';
    });

    $('#candCards').innerHTML = rows.slice(0, 30).map(r => {
      const w = ((r.why || {})[candFacet] || {}).pros || [];
      return `<div class="scard" onclick="goStock('${r.code}')">
        <div class="h"><b>${fmt.esc(r.name)} <span class="mono muted">${r.code}</span></b><span class="grade ${r.grade || 'W'}">${r.grade ? r.grade + ' ' + r.verdict : r.verdict}</span></div>
        <div class="r"><span>${L.group(r.group_id, r.group)}</span><span class="num" data-live="close" data-lc="${r.code}">${fmt.n(r.close)}</span><span class="num ${fmt.cls(r.chg_pct)}" data-live="chg" data-lc="${r.code}">${fmt.pct(r.chg_pct, 2)}</span><span>${F.label} ${r[F.key] != null ? fmt.n(r[F.key], 0) : '—'}</span></div>
        ${w.length ? `<div class="why"><span class="pro">✓ ${fmt.esc(w[0])}</span></div>` : ''}
      </div>`;
    }).join('');
  }

  /* 市場寬度：四根長條（其中兩根還常常是 0%）看不出「現在市場健不健康」。
     改成一個儀表＋一個漲跌環：儀表是站上 20 日均線的比例（多數股票在均線之上＝多頭結構），
     環是今天的漲／平／跌家數。兩個加起來才回答得了「今天是真的漲還是指數漲而已」。 */
  function renderBreadth(heat) {
    const b = heat && heat.breadth; if (!b) return empty('breadth');
    const p20 = b.pct_above_ma20 || 0, p60 = b.pct_above_ma60 || 0;
    const up = heat.advancers || 0, dn = heat.decliners || 0, fl = heat.unchanged || 0;
    const zone = p20 >= 70 ? '多數股票在均線之上，結構偏多' : p20 >= 45 ? '多空拉鋸，選股比押方向重要'
      : p20 >= 25 ? '偏弱，多數股票在均線之下' : '普遍破線，別急著搶反彈';
    chart('breadth', {
      tooltip: { ...tip, trigger: 'item', formatter: q => q.seriesIndex === 1
        ? `${q.name} <b>${q.value}</b> 檔（${fmt.n(q.percent, 1)}%）` : `站上 20 日均線 <b>${fmt.n(q.value, 1)}%</b>` },
      series: [
        { type: 'gauge', startAngle: 200, endAngle: -20, min: 0, max: 100, radius: '92%', center: ['30%', '72%'],
          progress: { show: true, width: 13, roundCap: true,
            itemStyle: { color: p20 >= 60 ? '#ff4d6d' : p20 >= 40 ? '#ffb454' : '#2ee59d' } },
          axisLine: { lineStyle: { width: 13, color: [[1, 'rgba(255,255,255,.08)']] } },
          axisTick: { show: false }, splitLine: { show: false },
          axisLabel: { distance: -20, color: CH.ink3, fontSize: 10, formatter: v => (v % 50 === 0 ? v : '') },
          pointer: { show: false },
          anchor: { show: false },
          title: { show: true, offsetCenter: [0, '30%'], color: CH.ink3, fontSize: 11.5 },
          detail: { valueAnimation: true, offsetCenter: [0, '-2%'], fontSize: 26, fontFamily: 'JetBrains Mono',
            fontWeight: 700, color: '#e8eeff', formatter: v => v.toFixed(1) + '%' },
          data: [{ value: p20, name: '站上 20 日均線' }] },
        { type: 'pie', radius: ['32%', '52%'], center: ['78%', '52%'], avoidLabelOverlap: true,
          label: { color: CH.ink2, fontSize: 11, formatter: '{b}\n{c}' }, labelLine: { length: 6, length2: 6 },
          data: [
            { name: '上漲', value: up, itemStyle: { color: '#ff4d6d' } },
            { name: '平盤', value: fl, itemStyle: { color: '#6f7ea3' } },
            { name: '下跌', value: dn, itemStyle: { color: '#2ee59d' } },
          ] },
      ],
    });
    // 圖下面一行把「還有什麼可以看」補上，不用再畫兩根 0% 的長條
    linkRow('breadth', `<span class="pill ${p20 >= 50 ? 'up' : 'down'}">${zone}</span>`
      + `<span class="pill">MA60 ${fmt.n(p60, 1)}%</span>`
      + `<span class="pill">60 日新高 ${b.new_high_60 ?? 0} 檔</span>`
      + `<span class="pill">樣本 ${b.n ?? 0} 檔</span>`
      + `<a class="pill cyan" href="#market/ma">看各族群 →</a>`);
  }

  /* 投信連續買超：長條圖只講得出「買幾天」，講不出「買多少」。
     改成氣泡圖：橫軸＝連續天數、縱軸＝這段期間累計買超張數、泡泡大小＝累計張數。
     右上角那幾顆才是真的在收貨（買得久而且買得多），只買一天大單的不會跑到右邊。 */
  function renderTrust(trust, cands) {
    if (!trust || !trust.length) return empty('trust');
    const names = {}; (cands || []).forEach(c => { names[c.code] = c.name; });
    const nm = (code) => names[code] || L.cname[code] || code;
    const rows = trust.slice(0, 26).map(r => ({ ...r, lots: (r.accumulated || 0) / 1000 }));
    const maxLots = Math.max(...rows.map(r => Math.abs(r.lots)), 1);
    const c = chart('trust', {
      tooltip: { ...tip, formatter: q => `<b>${q.data.nm} ${q.data.code}</b><br>連續買超 <b>${q.value[0]}</b> 天<br>期間累計 <b>${fmt.lot(q.value[1])}</b><br>${q.data.g ? fmt.esc(q.data.g) + '<br>' : ''}<small>點一下進個股頁</small>` },
      grid: { left: 62, right: 22, top: 26, bottom: 40 },
      xAxis: { ...axisStyle, name: '連續買超天數 →', nameLocation: 'middle', nameGap: 24,
        nameTextStyle: { color: CH.ink3, fontSize: 11 }, min: 2, splitLine: { show: false } },
      yAxis: { ...axisStyle, name: '累計張數 ↑', nameTextStyle: { color: CH.ink3, fontSize: 11 },
        scale: true, axisLabel: { formatter: v => fmt.lot(v) } },
      series: [{ type: 'scatter',
        data: rows.map(r => { const gid = L.cgroup[r.code];
          return { value: [r.streak_days, +r.lots.toFixed(0)], code: r.code, nm: nm(r.code), g: L.gname[gid],
            symbolSize: Math.max(10, Math.min(40, Math.sqrt(Math.abs(r.lots) / maxLots) * 40)),
            itemStyle: { color: L.gcolor[gid] || '#ffb454', opacity: .85, borderColor: '#0a1020', borderWidth: 1 } }; }),
        label: { show: true, formatter: q => q.data.nm, position: 'top', color: CH.ink2, fontSize: 11 },
        labelLayout: { hideOverlap: true, moveOverlap: 'shiftY' } }],
    });
    if (c) c.off('click').on('click', q => { if (q.data && q.data.code) goStock(q.data.code); });
    linkRow('trust', rows.slice(0, 12).map(r => L.stock(r.code, nm(r.code))).join(''));
  }

  /* 族群估值：單看本益比高低沒有用（IC 設計本來就比航運貴）。
     要看的是「貴不貴」× 「錢有沒有在進來」——
     左上（便宜而且資金流入）才是這張儀表板真正想找的地方，右下（貴又在流出）是該閃的。 */
  function renderGval(gval, rot, gt) {
    if (!gval || !gval.length) return empty('gval');
    const rotMap = {}; (rot || []).forEach(r => { rotMap[r.group_id] = r.rotation; });
    const shareMap = {}; (gt || []).forEach(g => { shareMap[g.group_id] = g.turnover_share; });
    const rows = gval.filter(g => g.metric === 'pe' && g.group_median && !g.group_id.startsWith('ind_')
      && rotMap[g.group_id] != null).map(g => ({ ...g, rot: rotMap[g.group_id], share: shareMap[g.group_id] || 0 }));
    if (rows.length < 3) return empty('gval', '族群估值需要更多有本益比的族群，財報還在回補');
    const pes = rows.map(r => r.group_median);
    const mid = pes.slice().sort((a, b) => a - b)[Math.floor(pes.length / 2)];
    const maxShare = Math.max(...rows.map(r => r.share), 1);
    const xs = [Math.min(...pes) * .9, Math.max(...pes) * 1.06];
    const ys = rows.map(r => r.rot); const yr = Math.max(...ys.map(Math.abs), .5) * 1.25;
    const c = chart('gval', {
      tooltip: { ...tip, formatter: q => `<b>${q.data.nm}</b><br>本益比中位 <b>${fmt.n(q.value[0], 1)}</b>（n=${q.data.n}，全市場中位 ${fmt.n(mid, 1)}）<br>資金流向 <span style="color:${upDown(q.value[1])}">${q.value[1] > 0 ? '流入 +' : '流出 '}${fmt.n(q.value[1], 2)} pp</span><br>成交值佔比 ${fmt.n(q.data.share, 1)}%<br><small>點一下看成分股</small>` },
      grid: { left: 56, right: 24, top: 30, bottom: 42 },
      xAxis: { ...axisStyle, name: '← 便宜　　本益比中位　　貴 →', nameLocation: 'middle', nameGap: 26,
        nameTextStyle: { color: CH.ink3, fontSize: 11 }, min: +xs[0].toFixed(0), max: +xs[1].toFixed(0), splitLine: { show: false } },
      yAxis: { ...axisStyle, name: '資金流入 ↑', nameTextStyle: { color: CH.ink3, fontSize: 11 },
        min: -yr, max: yr, axisLabel: { formatter: v => v.toFixed(1) }, splitLine: { show: false } },
      graphic: [
        { type: 'text', left: '13%', top: 6, style: { text: '便宜 × 資金流入', fill: 'rgba(255,77,109,.75)', fontSize: 12, fontWeight: 700 } },
        { type: 'text', right: '6%', top: 6, style: { text: '貴 × 資金流入', fill: 'rgba(255,180,84,.7)', fontSize: 12, fontWeight: 700, align: 'right' } },
        { type: 'text', left: '13%', bottom: 40, style: { text: '便宜 × 沒人要', fill: 'rgba(110,126,163,.8)', fontSize: 12, fontWeight: 700 } },
        { type: 'text', right: '6%', bottom: 40, style: { text: '貴 × 資金流出', fill: 'rgba(46,229,157,.7)', fontSize: 12, fontWeight: 700, align: 'right' } },
      ],
      series: [{ type: 'scatter',
        data: rows.map(r => ({ value: [+r.group_median.toFixed(1), +r.rot.toFixed(2)], gid: r.group_id,
          nm: r.group_name, n: r.group_n, share: r.share,
          symbolSize: Math.max(11, Math.min(34, Math.sqrt(r.share / maxShare) * 34)),
          itemStyle: { color: L.gcolor[r.group_id] || PALETTE[0], opacity: .85, borderColor: '#0a1020', borderWidth: 1 } })),
        label: { show: true, formatter: q => q.data.nm, position: 'right', color: CH.ink2, fontSize: 11 },
        labelLayout: { hideOverlap: true, moveOverlap: 'shiftY' } },
      { type: 'line', data: [], markLine: { silent: true, symbol: 'none',
        lineStyle: { color: 'rgba(255,255,255,.22)', type: 'dashed' },
        data: [{ xAxis: +mid.toFixed(1) }, { yAxis: 0 }], label: { show: false } } }],
    });
    if (c) c.off('click').on('click', q => { if (q.data && q.data.gid) location.hash = '#industry/group/' + q.data.gid; });
    linkRow('gval', rows.slice().sort((a, b) => b.rot - a.rot).slice(0, 12)
      .map(r => L.group(r.group_id, r.group_name)).join(''));
  }

  // ---------------------------------------------------------------- 資金流向
  // ================================================================ 資金流向頁
  // Andy 的要求：「需要有趨勢 好比說上週 上上週 上個月等等 可以查到不同時期 資金走向為何」
  //             「右側本益比需要多可篩選功能 全部在一起」「也需要附上說明怎麼觀看」
  // 所以整頁由上方一個期間切換列統一控制「什麼時候」，每張圖都有一顆「怎麼看」。
  const HOW = {
    rank: `<b>這張圖回答：這段時間錢往哪裡跑。</b>
      <ul><li>長條長度＝這個族群的<em>成交值佔比變化</em>（和上一段同樣長度的期間比），單位是百分點 pp。</li>
      <li><em>紅色向右</em>＝資金流進來，<em>綠色向左</em>＝資金退出去。只看金額會被大盤量能帶著走，所以看佔比。</li>
      <li>名字後面的 <em>3 ↑</em> 是成交值排名進步了 3 名；括號是這段期間的族群報酬。</li>
      <li>用法：先看誰在最上面（主流在換人），再去「名次變化」確認是一天的事還是連續好幾週。</li></ul>`,
    bump: `<b>這張圖回答：主流是穩穩的還是一直換人。</b>
      <ul><li>每條線是一個族群，<em>位置越高＝成交值排名越前面</em>（1 名在最上面）。</li>
      <li>線一路往上＝資金連續好幾週往它集中，通常比單週衝上來的更值得跟。</li>
      <li>線上下亂跳＝那一段時間在輪動，沒有明確主流，追高容易兩面挨巴掌。</li>
      <li>滑鼠移上去看每一週的實際佔比；點線上的點可以進該族群。</li></ul>`,
    rot: `<b>這張圖回答：每個族群現在跑到「強弱循環」的哪一段，以及該怎麼辦。</b>
      <ul><li><b>先看那個圓盤（資金輪動時鐘）</b>：圓盤切成四塊，就是循環的四段。
        一顆點是一個族群，<em>點落在哪一塊＝現在在哪一段</em>；點越大＝成交值佔比越高。</li>
      <li>資金照<em>順時針</em>一塊一塊跑：落後（左下）→ 改善（左上）→ 領先（右上）→ 轉弱（右下）→ 回落後。
        點後面那條尾巴是牠這幾天走過的路，尾巴往前拉＝正在往下一段前進，往回縮＝走回頭路。</li>
      <li><em>離圓心越遠＝和大盤差距越大</em>；擠在圓心附近就是跟大盤差不多，沒特色。</li>
      <li>族群跟著大盤轉，順序幾乎都是 <em>改善 → 領先 → 轉弱 → 落後 → 再回改善</em>。</li>
      <li><em>改善</em>：還比大盤弱，但動能已經轉強 —— 資金剛進場，這是最早可以布局的一段。</li>
      <li><em>領先</em>：現在的主流。回檔找買點，別追高，因為下一站是轉弱。</li>
      <li><em>轉弱</em>：還是比大盤強，但動能在掉。手上有的先設好停利。</li>
      <li><em>落後</em>：資金還在跑，別急著抄底，等它走到改善再說。</li>
      <li>名字後面的 <em>↑↓</em> 是動能的方向、「強弱」是相對大盤多少（0 就是跟大盤一樣）。</li>
      <li>最上面那條「換階段的族群」才是重點 —— 已經在領先的你早就知道了，<em>剛從落後轉進改善的</em>才是新機會。
        上面的鈕可以改成和 10 天或 20 天前比。</li></ul>`,
    rotm: `<b>族群現在跑到強弱循環的哪一段。</b>
      <ul><li>順序是 <em>改善 → 領先 → 轉弱 → 落後</em>，然後再回改善。</li>
      <li><em>改善</em>＝資金剛進場，最早可以布局；<em>領先</em>＝現在的主流，回檔找買點；
        <em>轉弱</em>＝動能在掉，設好停利；<em>落後</em>＝別急著抄底。</li>
      <li>完整的版本（含「誰剛換階段」）在「資金流向」分頁。</li></ul>`,
    mkt: `<b>這一頁是總覽上方那排數字的完整名單。</b>
      <ul><li><em>漲跌家數</em>：漲停通常是題材發動的第一天；跌停要看是個股利空還是整個族群一起倒；
        成交值前段才是今天真正的戰場。</li>
      <li><em>站上均線</em>：大盤那個百分比拆到族群，才知道是哪幾個在撐、哪幾個在拖。</li>
      <li><em>資金集中</em>：前幾大族群吃掉多少量；越集中，冷門股越不容易動。</li>
      <li><em>今日候選</em>：A 回檔承接、B 突破追進；沒有 A/B 的日子列綜合分前段當觀察名單。</li>
      <li>每一列都點得進個股頁，族群名稱點得進族群頁。</li></ul>`,
    heat: `<b>這張圖回答：今天的錢集中在哪些族群。</b>
      <ul><li>方塊<em>大小</em>＝這個族群吃掉多少成交值，方塊<em>顏色</em>＝資金在流入（紅）還是流出（綠），
        看的是 5 日佔比減 20 日佔比，不是今天的漲跌。</li>
      <li>所以會出現「紅方塊但今天收綠」——那代表股價在回檔，但錢還在往裡面放。</li>
      <li>上面那排可以只看一條產業鏈，小方塊就會變大、看得清楚；點方塊直接看成分股。</li></ul>`,
    sankey: `<b>這張圖回答：今天這筆量最後流進了誰的口袋。</b>
      <ul><li>由左到右：大盤 → 產業鏈 → 族群 → 代表股，<em>帶子越粗＝成交值越大</em>。</li>
      <li>只畫成交值前 18 大的代表股，不然線會糊成一團。</li>
      <li>點族群看成分股、點個股直接進個股頁。</li></ul>`,
    river: `<b>這張圖回答：這 60 天的主流換過幾次。</b>
      <ul><li>每一條色帶是一個族群，<em>帶子越厚＝當天成交值佔比越高</em>。</li>
      <li>某條帶子連續變厚＝資金正在往它集中；整體帶子變得一樣厚＝行情擴散。</li></ul>`,
    inst: `<b>這張圖回答：這段時間法人把錢放在哪裡。</b>
      <ul><li>三段堆疊分別是外資、投信、自營，<em>向右＝買超、向左＝賣超</em>（單位張）。</li>
      <li><em>投信</em>的錢比較黏（有作帳壓力、不太會隔天就跑），連續買超的族群參考價值比外資單日大買高。</li>
      <li>跟著上方期間切換一起變；點任一列看成分股。</li></ul>`,
    conc: `<b>這張圖回答：現在是「少數股票撐盤」還是「雨露均霑」。</b>
      <ul><li>線＝前幾大族群吃掉多少成交值，虛線是它的 20 日平均。</li>
      <li><em>往上＝縮圈</em>，行情集中在少數主流，這時候買冷門股很容易不會動。</li>
      <li><em>往下＝擴散</em>，通常是輪動或補漲，這時候主流反而容易休息。</li>
      <li>前 5 大看「主流有多獨」，前 10 大看「主流圈子有多大」；兩條走勢分岔時是換主流。</li></ul>`,
    val: `<b>這張表回答：這些族群現在貴不貴。</b>
      <ul><li>本益比只有<em>同族群</em>比才有意義（IC 設計跟航運的合理倍數本來就差很多），所以有「只看低於族群中位」這個條件。</li>
      <li>左圖橫軸本益比、縱軸 ROE，<em>右下＝貴又賺得少、左上＝便宜又賺得多</em>；圈圈大小是市值。</li>
      <li>本益比用自算 TTM EPS（近四季），虧損的公司沒有本益比，預設已排除。</li>
      <li>條件可以疊加，改任何一個右上角的檔數就會跟著變；點任一列進個股頁。</li></ul>`,
  };
  function wireHowto(root) {
    $$('.howbtn', root || document).forEach(b => b.onclick = () => {
      const box = $('#how-' + b.dataset.how); if (!box) return;
      const open = box.hidden;
      if (open && !box.dataset.filled) { box.innerHTML = HOW[b.dataset.how] || ''; box.dataset.filled = '1'; }
      box.hidden = !open; b.classList.toggle('on', open);
      b.textContent = open ? '收起說明' : '怎麼看 ?';
      Object.values(charts).forEach(c => c && c.resize && c.resize());
    });
  }

  let flowState = { period: 'w0', back: 5, concTop: 5 };
  async function renderFlow() {
    const [f3, conc, fund] = await Promise.all([load('flow_v3'), load('concentration'), load('fundamental')]);
    const periods = (f3 && f3.periods) || [];
    wireHowto($('#v-flow'));

    // ---- 期間切換列：整頁的「什麼時候」
    const seg = $('#periodSeg');
    if (!periods.length) { seg.innerHTML = '<span class="muted" style="padding:6px 10px">期間資料還在回補</span>'; }
    else {
      if (!periods.some(p => p.key === flowState.period)) flowState.period = periods[0].key;
      seg.innerHTML = periods.map(p => `<button data-p="${p.key}" class="${p.key === flowState.period ? 'on' : ''}">${p.label}</button>`).join('');
      $$('#periodSeg button').forEach(b => b.onclick = () => {
        $$('#periodSeg button').forEach(x => x.classList.toggle('on', x === b));
        flowState.period = b.dataset.p; drawPeriod();
      });
    }
    const drawPeriod = () => {
      const p = periods.find(x => x.key === flowState.period);
      if (!p) { empty('rankFlow', '這個期間還沒有資料'); empty('instGroups', '這個期間還沒有資料'); return; }
      $('#periodNote').textContent = `${p.from} ～ ${p.to}（${p.days} 個交易日）`
        + (p.prev_from ? `　·　和 ${p.prev_from} ～ ${p.prev_to} 相比` : '　·　沒有可比的上一段');
      $('#rankSub').textContent = `${p.label}：誰把錢吸走了`;
      $('#instSub').textContent = `${p.label}三大法人淨買超（張）`;
      renderRankFlow(p);
      renderInstPeriod(p);
      drawBump(p);
    };
    // 名次變化跟著期間換刻度：看週的期間就用週名次，看月／季就用月名次。
    // （之前固定是近 8 週，不管切到哪一段都長一樣，Andy 看到的就是「排名不會變」。）
    const drawBump = (p) => {
      const bs = (f3 && f3.bumps) || {};
      const unit = /^m|^q/.test(p.key) ? 'month' : 'week';
      const b = bs[unit] || (f3 && f3.bump);
      const sub = $('#bumpSub');
      if (sub) sub.textContent = `${(b && b.label) || (unit === 'month' ? '近 8 個月' : '近 8 週')}資金佔比排名`;
      renderBump(b, unit);
    };
    drawPeriod();

    // ---- 輪動階段：和幾天前比，用來判斷誰剛換階段
    const drawRot = () => renderRotation(f3 && f3.rrg, flowState.back,
      { board: 'rotBoard', cycle: 'rotCycle', move: 'rotMove', clock: 'rotClock' });
    drawRot();
    $$('#rotBack button').forEach(b => b.onclick = () => {
      $$('#rotBack button').forEach(x => x.classList.toggle('on', x === b)); flowState.back = +b.dataset.v; drawRot();
    });

    renderSankey(f3 && f3.sankey);
    renderRiver(f3 && f3.share);
    const drawConc = () => renderConc(conc, flowState.concTop);
    drawConc();
    $$('#concSeg button').forEach(b => b.onclick = () => {
      $$('#concSeg button').forEach(x => x.classList.toggle('on', x === b)); flowState.concTop = +b.dataset.v; drawConc();
    });
    renderVal(fund);
    // 資金流向頁的六張圖不加滾輪縮放（Andy 09-13）；圖本身已經用足卡片寬度
  }

  // ---- 資金流向排行：這段期間誰的成交值佔比長大、誰縮小
  function renderRankFlow(p) {
    const gs = (p.groups || []).filter(g => g.share_chg != null);
    if (!gs.length) return empty('rankFlow', p.prev_from ? '這個期間沒有可比的族群' : '沒有上一段期間可以比，換一個期間看看');
    const up = gs.slice().sort((a, b) => b.share_chg - a.share_chg).slice(0, 9);
    const down = gs.slice().sort((a, b) => a.share_chg - b.share_chg).slice(0, 6).reverse();
    const rows = up.concat(down.filter(d => !up.some(u => u.group_id === d.group_id)));
    rows.sort((a, b) => a.share_chg - b.share_chg);      // 由下往上＝由小到大，最會吸金的在最上面
    const label = (g) => {
      const arrow = g.rank_chg > 0 ? ` ${g.rank_chg}↑` : g.rank_chg < 0 ? ` ${-g.rank_chg}↓` : '';
      return `${g.group_name}${arrow}`;
    };
    const c = chart('rankFlow', {
      tooltip: {
        ...tip, trigger: 'item', formatter: (q) => { const g = rows[q.dataIndex];
          return `<b>${g.group_name}</b><br>成交值佔比 ${fmt.n(g.share, 2)}%（上一段 ${g.share_prev != null ? fmt.n(g.share_prev, 2) + '%' : '—'}）`
            + `<br>變化 <span style="color:${upDown(g.share_chg)}">${g.share_chg > 0 ? '+' : ''}${fmt.n(g.share_chg, 2)} pp</span>`
            + `<br>名次 ${g.rank_prev != null ? g.rank_prev + ' → ' : ''}${g.rank}`
            + `<br>期間報酬 <span style="color:${upDown(g.ret)}">${fmt.pct(g.ret, 1)}</span>`
            + `<br>成交值 ${fmt.yi(g.turnover)}<br><small>點一下看成分股</small>`; },
      },
      grid: { left: 132, right: 96, top: 12, bottom: 30 },
      xAxis: { ...axisStyle, name: '佔比變化 (pp)', nameLocation: 'middle', nameGap: 24, nameTextStyle: { color: CH.ink3, fontSize: 11 }, axisLabel: { color: CH.ink3 } },
      yAxis: { ...axisStyle, type: 'category', data: rows.map(label), axisLabel: { color: CH.ink2, fontSize: 12.5 } },
      series: [{
        type: 'bar', barWidth: 15,
        data: rows.map(g => ({ value: +g.share_chg.toFixed(3), gid: g.group_id,
          itemStyle: { color: chgColor(g.share_chg, 1.5), borderRadius: g.share_chg >= 0 ? [0, 4, 4, 0] : [4, 0, 0, 4] } })),
        label: { show: true, position: 'right', color: CH.ink2, fontSize: 11.5, fontFamily: 'JetBrains Mono',
          formatter: (q) => { const g = rows[q.dataIndex]; return `${g.share_chg > 0 ? '+' : ''}${g.share_chg.toFixed(2)}　${fmt.pct(g.ret, 1)}`; } },
        markLine: { silent: true, symbol: 'none', lineStyle: { color: 'rgba(255,255,255,.3)' }, data: [{ xAxis: 0 }], label: { show: false } },
      }],
    });
    if (c) c.off('click').on('click', q => { if (q.data && q.data.gid) location.hash = '#industry/group/' + q.data.gid; });
    linkRow('rankFlow', rows.slice().reverse().map(g => L.group(g.group_id, g.group_name)).join(''));
  }

  // ---- 名次變化：佔比排名的 bump 圖；unit 是 week（近 8 週）或 month（近 8 個月）
  function renderBump(bump, unit) {
    const u = (bump && bump.unit) || unit || 'week';
    const un = u === 'month' ? '那個月' : '那週';
    if (!bump || !bump.series || !bump.series.length) return empty('bump', `名次變化需要至少兩${u === 'month' ? '個月' : '週'}的資料`);
    const maxRank = Math.max(...bump.series.flatMap(s => s.ranks.filter(r => r != null)));
    const c = chart('bump', {
      tooltip: { ...tip, trigger: 'item', formatter: (q) => {
        const s = bump.series[q.seriesIndex]; const i = q.dataIndex;
        return `<b>${s.group_name}</b><br>${bump.weeks[i]} ${un}<br>排名第 ${s.ranks[i]}　佔比 ${s.shares[i] != null ? fmt.n(s.shares[i], 2) + '%' : '—'}<br><small>點一下看成分股</small>`; } },
      grid: { left: 34, right: 116, top: 24, bottom: 30 },
      xAxis: { ...axisStyle, type: 'category', boundaryGap: false, data: bump.weeks, axisLabel: { color: CH.ink3, fontSize: 11.5 } },
      yAxis: { ...axisStyle, inverse: true, min: 1, max: maxRank, interval: Math.max(1, Math.round(maxRank / 6)),
        name: '名次', nameTextStyle: { color: CH.ink3, fontSize: 11 }, axisLabel: { color: CH.ink3 }, splitLine: { show: true, lineStyle: { color: 'rgba(255,255,255,.05)' } } },
      series: bump.series.map((s, i) => ({
        name: s.group_name, type: 'line', data: s.ranks, connectNulls: true, smooth: .25,
        symbolSize: 7, lineStyle: { width: 2.2, color: L.gcolor[s.group_id] || PALETTE[i % PALETTE.length] },
        itemStyle: { color: L.gcolor[s.group_id] || PALETTE[i % PALETTE.length] },
        endLabel: { show: true, color: CH.ink2, fontSize: 11.5, distance: 6, formatter: s.group_name },
        emphasis: { focus: 'series', lineStyle: { width: 3.6 }, endLabel: { color: '#e8eeff', fontWeight: 700 } },
        blur: { lineStyle: { opacity: .12 }, itemStyle: { opacity: .12 }, endLabel: { opacity: .3 } },
        gid: s.group_id,
      })),
    }, { notMerge: true });   // 週↔月切換時族群數會變，不清乾淨會留上一次的線
    if (c) c.off('click').on('click', q => { const s = bump.series[q.seriesIndex]; if (s) location.hash = '#industry/group/' + s.group_id; });
    linkRow('bump', bump.series.map(s => L.group(s.group_id, s.group_name)).join(''));
  }

  function renderSankey(sk) {
    if (!sk || !sk.links || !sk.links.length) return empty('sankey');
    const leafVal = {}; sk.links.forEach(l => { const t = sk.nodes.find(n => n.name === l.target); if (t && t.code) leafVal[l.target] = (leafVal[l.target] || 0) + l.value; });
    const keepLeaf = new Set(Object.entries(leafVal).sort((a, b) => b[1] - a[1]).slice(0, 18).map(x => x[0]));
    const nodes = sk.nodes.filter(n => !n.code || keepLeaf.has(n.name));
    const links = sk.links.filter(l => nodes.some(n => n.name === l.source) && nodes.some(n => n.name === l.target));
    const c = chart('sankey', { tooltip: { ...tip, formatter: p => p.dataType === 'edge' ? `${p.data.source} → ${p.data.target}<br>${fmt.yi(p.data.value)}` : `<b>${p.name}</b><br><small>${p.data.code ? '點進個股頁' : p.data.gid ? '點看成分股' : ''}</small>` },
      series: [{ type: 'sankey', left: 10, right: 120, top: 10, bottom: 10, nodeWidth: 14, nodeGap: 10, nodeAlign: 'left', layoutIterations: 48, emphasis: { focus: 'adjacency' },
        data: nodes.map((n, i) => ({ name: n.name, code: n.code, gid: n.group_id, itemStyle: { color: n.depth === 0 ? '#3ee0ff' : n.depth === 1 ? '#8b7bff' : n.depth === 2 ? (L.gcolor[n.group_id] || '#ffb454') : (L.gcolor[L.cgroup[n.code]] || '#c3ff5b'), borderColor: 'transparent' } })),
        links: links.map(l => ({ ...l, lineStyle: { color: 'gradient', opacity: .35 } })),
        label: { color: '#e8eeff', fontSize: 12, textShadowColor: '#000', textShadowBlur: 3 }, lineStyle: { curveness: .5 } }] });
    if (c) c.off('click').on('click', p => { if (p.dataType === 'node') { if (p.data.code) goStock(p.data.code); else if (p.data.gid) location.hash = '#industry/group/' + p.data.gid; } });
    linkRow('sankey', sk.nodes.filter(n => n.group_id).map(n => L.group(n.group_id, n.name)).join('') + sk.nodes.filter(n => n.code).map(n => L.stock(n.code, n.name)).join(''));
  }
  function renderRiver(sh) {
    if (!sh || !sh.series || !sh.series.length) return empty('river');
    const data = []; sh.series.forEach(s => s.values.forEach((v, i) => data.push([sh.dates[i], v || 0, s.name])));
    linkRow('river', sh.series.map((s, i) => L.group(s.group_id || L.gid[s.name], s.name, {})).join(''));
    const cr = chart('river', { tooltip: { ...tip, trigger: 'axis', axisPointer: { type: 'line' }, formatter: ps => `<b>${ps[0].value[0]}</b><br>` + ps.sort((a, b) => b.value[1] - a.value[1]).slice(0, 10).map(p => `${p.marker}${p.value[2]} ${fmt.n(p.value[1], 1)}%`).join('<br>') },
      legend: { show: false }, singleAxis: { type: 'time', ...axisStyle, top: 10, bottom: 30, axisLabel: { color: CH.ink3, hideOverlap: true, formatter: v => new Date(v).toISOString().slice(5, 10) } },
      color: sh.series.map((s, i) => L.gcolor[s.group_id || L.gid[s.name]] || PALETTE[i % PALETTE.length]), series: [{ type: 'themeRiver', emphasis: { itemStyle: { shadowBlur: 20, shadowColor: 'rgba(0,0,0,.6)' } }, label: { show: false }, data }] });
    if (cr) cr.off('click').on('click', p => { const name = p.data && p.data[2]; const s = sh.series.find(x => x.name === name); const gid = (s && s.group_id) || L.gid[name]; if (gid) location.hash = '#industry/group/' + gid; });
  }

  // ---- 族群 × 法人：跟著上方期間走（期間資料裡已經有這段的法人合計）
  function renderInstPeriod(p) {
    const gs = (p.groups || []).filter(g => g.foreign != null || g.trust != null || g.dealer != null)
      .map(g => ({ ...g, total: (g.foreign || 0) + (g.trust || 0) + (g.dealer || 0) }));
    if (!gs.length) return empty('instGroups', '這個期間沒有法人資料');
    gs.sort((a, b) => b.total - a.total);
    const top = gs.slice(0, 8).concat(gs.slice(-6).filter(x => !gs.slice(0, 8).some(y => y.group_id === x.group_id)));
    const c = chart('instGroups', {
      tooltip: { ...tip, trigger: 'axis', axisPointer: { type: 'shadow' },
        formatter: ps => `<b>${ps[0].name}</b><br>` + ps.map(q => `${q.marker}${q.seriesName} ${fmt.lot(q.value / 1000)}`).join('<br>') + '<br><small>點一下看成分股</small>' },
      legend: { textStyle: { color: CH.ink2 }, top: 0 }, grid: { left: 108, right: 24, top: 30, bottom: 22 },
      xAxis: { ...axisStyle, axisLabel: { formatter: v => fmt.lot(v / 1000), color: CH.ink3 } },
      yAxis: { ...axisStyle, type: 'category', inverse: true, data: top.map(g => g.group_name), axisLabel: { color: CH.ink2 } },
      series: [['外資', 'foreign', '#3ee0ff'], ['投信', 'trust', '#ffb454'], ['自營', 'dealer', '#8b7bff']].map(([n, k, col]) => ({
        name: n, type: 'bar', stack: 'a', barWidth: 14,
        data: top.map(g => ({ value: g[k] || 0, gid: g.group_id })), itemStyle: { color: col } })),
    });
    if (c) c.off('click').on('click', q => { if (q.data && q.data.gid) location.hash = '#industry/group/' + q.data.gid; });
    linkRow('instGroups', top.map(g => L.group(g.group_id, g.group_name)).join(''));
  }

  function renderConc(conc, topN) {
    if (!conc || !conc.length) return empty('conc');
    const key = topN === 10 ? 'top10_share' : 'top_share';
    const maKey = topN === 10 ? 'top10_share_ma20' : 'top_share_ma20';
    const has10 = conc.some(r => r.top10_share != null);
    if (topN === 10 && !has10) { $('#concState').textContent = '前 10 大的歷史還在回補'; return empty('conc', '前 10 大集中度還在回補，先看前 5 大'); }
    const last = conc[conc.length - 1] || {};
    const cur = last[key], ma = last[maKey];
    if (cur != null && ma != null) {
      const diff = cur - ma;
      $('#concState').textContent = `前 ${topN} 大目前 ${fmt.n(cur, 1)}%，`
        + (diff > 0.8 ? '高於 20 日均 → 行情縮圈在主流，冷門股不容易動'
          : diff < -0.8 ? '低於 20 日均 → 資金在擴散輪動，主流容易休息'
            : '貼著 20 日均 → 沒有明顯的縮圈或擴散');
    }
    chart('conc', {
      tooltip: { ...tip, trigger: 'axis' }, grid: { left: 50, right: 20, top: 30, bottom: 30 }, legend: { textStyle: { color: CH.ink2 }, top: 0 },
      xAxis: { ...axisStyle, type: 'category', data: conc.map(r => r.date), axisLabel: { color: CH.ink3, formatter: v => v.slice(5) } },
      yAxis: { ...axisStyle, scale: true, axisLabel: { formatter: '{value}%' } },
      series: [{ name: `前 ${topN} 族群佔比`, type: 'line', data: conc.map(r => r[key]), smooth: .3, showSymbol: false, lineStyle: { color: '#3ee0ff', width: 2 }, areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(62,224,255,.35)' }, { offset: 1, color: 'rgba(62,224,255,0)' }]) } },
        { name: '20 日均', type: 'line', data: conc.map(r => r[maKey]), smooth: .3, showSymbol: false, lineStyle: { color: '#ffb454', width: 1.5, type: 'dashed' } }],
    });
  }

  // ---- 估值篩選：本益比、股價淨值比、ROE、市值、族群，全部條件放在一起
  const VF = { pe: [null, null], pb: null, roe: null, cap: null, group: '', market: '', below: false, profit: true };
  function renderVal(fund) {
    const all = (fund || []).filter(r => r.pe != null || r.pb != null);
    if (!all.length) { $('#valCount') && ($('#valCount').textContent = ''); empty('valScatter', '估值資料還在回補'); $('#valBody').innerHTML = ''; return; }
    const gsel = $('#vGroup');
    if (gsel && gsel.options.length <= 1) {
      const names = [...new Set(all.map(r => r.group_name).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'zh-TW'));
      gsel.innerHTML = '<option value="">全部族群</option>' + names.map(n => `<option value="${fmt.esc(n)}">${fmt.esc(n)}</option>`).join('');
    }
    const num = (el) => { const v = parseFloat(($(el) || {}).value); return Number.isFinite(v) ? v : null; };
    const apply = () => {
      VF.pe = [num('#vPeLo'), num('#vPeHi')]; VF.pb = num('#vPb'); VF.roe = num('#vRoe'); VF.cap = num('#vCap');
      VF.group = ($('#vGroup') || {}).value || ''; VF.market = ($('#vMarket') || {}).value || '';
      VF.below = !!($('#vBelow') || {}).checked; VF.profit = !!($('#vProfit') || {}).checked;
      const rows = all.filter(r => {
        if (VF.profit && (r.is_loss || r.pe == null)) return false;
        if (VF.group && r.group_name !== VF.group) return false;
        if (VF.market && r.market !== VF.market) return false;
        if (VF.pe[0] != null && !(r.pe != null && r.pe >= VF.pe[0])) return false;
        if (VF.pe[1] != null && !(r.pe != null && r.pe <= VF.pe[1])) return false;
        if (VF.pb != null && !(r.pb != null && r.pb <= VF.pb)) return false;
        if (VF.roe != null && !(r.roe != null && r.roe >= VF.roe)) return false;
        if (VF.cap != null && !(r.market_cap != null && r.market_cap >= VF.cap * 1e8)) return false;
        if (VF.below && !(r.vs_median != null && r.vs_median < 0)) return false;
        return true;
      });
      $('#vCount').textContent = `符合 ${rows.length} 檔（全市場有估值的 ${all.length} 檔）`;
      drawScatter(rows); drawTable(rows);
    };
    const drawScatter = (rows) => {
      const pts = rows.filter(r => r.pe != null && r.roe != null);
      if (!pts.length) return empty('valScatter', '這組條件沒有同時有本益比與 ROE 的股票');
      const caps = pts.map(r => r.market_cap || 0); const maxCap = Math.max(...caps, 1);
      const c = chart('valScatter', {
        tooltip: { ...tip, formatter: q => `<b>${q.data.name} ${q.data.code}</b><br>${fmt.esc(q.data.g || '')}<br>本益比 ${fmt.n(q.value[0], 1)}　ROE ${fmt.n(q.value[1], 1)}%<br>股價淨值比 ${fmt.n(q.data.pb)}　市值 ${fmt.yi(q.data.cap)}<br><small>點一下進個股頁</small>` },
        grid: { left: 52, right: 20, top: 20, bottom: 40 },
        xAxis: { ...axisStyle, name: '本益比 →', nameLocation: 'middle', nameGap: 24, nameTextStyle: { color: CH.ink3, fontSize: 11 }, scale: true, max: Math.min(80, Math.max(...pts.map(r => r.pe))) },
        yAxis: { ...axisStyle, name: 'ROE ↑', nameTextStyle: { color: CH.ink3, fontSize: 11 }, scale: true, axisLabel: { formatter: '{value}%' } },
        series: [{ type: 'scatter', data: pts.map(r => ({ value: [r.pe, r.roe], code: r.code, name: r.name, g: r.group_name, pb: r.pb, cap: r.market_cap,
          symbolSize: Math.max(8, Math.min(34, Math.sqrt((r.market_cap || 0) / maxCap) * 34)),
          itemStyle: { color: L.gcolor[r.group_id] || PALETTE[0], opacity: .78, borderColor: '#0a1020', borderWidth: 1 } })),
          label: { show: pts.length <= 40, formatter: q => q.data.name, position: 'right', color: CH.ink2, fontSize: 11 }, labelLayout: { hideOverlap: true } }],
      });
      if (c) c.off('click').on('click', q => { if (q.data && q.data.code) goStock(q.data.code); });
    };
    const drawTable = (rows) => {
      const top = rows.slice().sort((a, b) => (a.pe ?? 1e9) - (b.pe ?? 1e9)).slice(0, 80);
      $('#valTable thead').innerHTML = '<tr><th class="l">股票</th><th class="l">族群</th><th>本益比</th><th>族群中位</th><th>淨值比</th><th>ROE</th><th>市值</th></tr>';
      $('#valBody').innerHTML = top.map(r => `<tr data-code="${r.code}">
        <td class="l">${L.stock(r.code, r.name)}</td>
        <td class="l">${r.group_id ? L.group(r.group_id, r.group_name) : fmt.esc(r.group_name || '—')}</td>
        <td class="num">${fmt.n(r.pe, 1)}</td>
        <td class="num" style="color:${r.vs_median != null ? upDown(-r.vs_median) : CH.ink3}">${r.group_median != null ? fmt.n(r.group_median, 1) : '—'}</td>
        <td class="num">${fmt.n(r.pb)}</td><td class="num">${r.roe != null ? fmt.n(r.roe, 1) + '%' : '—'}</td>
        <td class="num">${fmt.yi(r.market_cap)}</td></tr>`).join('')
        || '<tr><td colspan="7" class="l muted" style="padding:16px">沒有符合條件的股票，放寬一點試試</td></tr>';
      $$('#valBody tr[data-code]').forEach(tr => tr.onclick = (e) => { if (e.target.closest('a')) return; goStock(tr.dataset.code); });
    };
    ['#vPeLo', '#vPeHi', '#vPb', '#vRoe', '#vCap'].forEach(s => { const el = $(s); if (el) el.oninput = apply; });
    ['#vGroup', '#vMarket'].forEach(s => { const el = $(s); if (el) el.onchange = apply; });
    ['#vBelow', '#vProfit'].forEach(s => { const el = $(s); if (el) el.onchange = apply; });
    const rst = $('#vReset');
    if (rst) rst.onclick = () => {
      ['#vPeLo', '#vPeHi', '#vPb', '#vRoe', '#vCap'].forEach(s => { const el = $(s); if (el) el.value = ''; });
      $('#vGroup').value = ''; $('#vMarket').value = ''; $('#vBelow').checked = false; $('#vProfit').checked = true; apply();
    };
    apply();
  }

  // ---------------------------------------------------------------- 題材
  async function renderThemes() {
    const th = await load('themes'); if (!th || !th.themes || !th.themes.length) { empty('themeMap'); return; }
    $('#themeNote').textContent = th.note || '';
    const data = th.themes.map(t => ({ name: t.name, value: t.turnover, id: t.id, heat: t.heat, chg: t.chg_pct, share: t.share, news7: t.news7, itemStyle: { color: t.heat >= 75 ? 'rgba(255,77,109,.85)' : t.heat >= 60 ? 'rgba(255,143,171,.75)' : t.heat >= 45 ? 'rgba(139,123,255,.7)' : t.heat >= 30 ? 'rgba(62,224,255,.55)' : 'rgba(110,126,163,.5)' } }));
    const themeOpt = (big) => ({ tooltip: { ...tip, formatter: p => `<b>${p.name}</b><br>熱度 ${p.data.heat} · 成交值 ${fmt.yi(p.value)}（${fmt.n(p.data.share, 1)}%）<br>平均漲跌 <span style="color:${upDown(p.data.chg)}">${fmt.pct(p.data.chg)}</span> · 近 7 天新聞 ${p.data.news7}<br><small>點一下看這個題材</small>` },
      series: [{ type: 'treemap', roam: false, nodeClick: false, breadcrumb: { show: false }, top: 0, left: 0, width: '100%', height: '100%', visibleMin: big ? 20 : 60, label: { overflow: 'truncate', formatter: p => `${p.name}\n熱度 ${p.data.heat} · ${fmt.pct(p.data.chg)}`, fontSize: big ? 15 : 13, color: '#fff', textShadowColor: '#000', textShadowBlur: 4 }, itemStyle: { borderColor: '#0b1224', borderWidth: 3, gapWidth: 3 }, data }] });
    const c = chart('themeMap', themeOpt(false));
    wheelZoom($('#themeMapWrap'), { onZoom: () => { const i = echarts.getInstanceByDom($('#themeMap')); if (i) i.resize(); } });
    // 點方塊：換下方明細（hash 一樣時 route 不會觸發，所以直接重畫）並捲到明細
    if (c) c.off('click').on('click', p => {
      if (!p.data || !p.data.id) return;
      const h = '#themes/' + p.data.id;
      if (location.hash === h) renderThemeDetail(th, p.data.id); else location.hash = h;
      const d = $('#themeDetail'); if (d && d.scrollIntoView) setTimeout(() => d.scrollIntoView({ behavior: 'smooth', block: 'start' }), 60);
    });
    const tz = $('#themeZoom');
    if (tz) tz.onclick = () => openZoom('題材資金熱力', (body, chipBox, close) => {
      const bc = chart(body, themeOpt(true));
      if (bc) bc.off('click').on('click', p => {
        if (!p.data || !p.data.id) return;
        close(); location.hash = '#themes/' + p.data.id;
      });
    });
    const sel = location.hash.split('/')[1];
    renderThemeDetail(th, sel || th.themes[0].id);
  }
  // 題材產品圖：零件 ↔ 個股雙向互通。點零件→列出該零件的個股；滑過成員→圖上對應零件同色亮起。
  function wireThemeDiagram(host, t) {
    const root = $('#themeDiagram', host); if (!root) return;
    const box = $('#themeParts', host);
    const nodes = $$('[data-part]', root);
    const color = {}, codesOf = {}, used = new Set();
    let i = 0;
    // 顏色規則：能對到供應鏈環節就用環節色（跟產業鏈頁一致）；同一張圖裡顏色不重複，
    // 否則五個零件都掛在「電源」環節時整張圖會變成同一色，反而分不出來。
    const pick = (seg) => {
      const sc = seg && L.scolor[seg];
      if (sc && !used.has(sc)) { used.add(sc); return sc; }
      while (used.has(PALETTE[i % PALETTE.length]) && i < PALETTE.length * 2) i++;
      const c = PALETTE[i++ % PALETTE.length]; used.add(c); return c;
    };
    nodes.forEach(n => {
      const id = n.dataset.part; if (!id) return;
      if (!(id in color)) color[id] = pick(n.dataset.seg);
      if (n.dataset.codes) codesOf[id] = n.dataset.codes.split(',').filter(Boolean);
    });
    nodes.forEach(n => { if (n.dataset.part) n.style.setProperty('--c', color[n.dataset.part]); });
    $$('[data-chain]', root).forEach(n => { n.style.cursor = 'pointer'; n.onclick = () => { location.hash = '#industry/' + n.dataset.chain; }; });
    // 圖上的代號標籤直接進個股頁（不必先點環節）
    $$('.scode', root).forEach(n => { n.onclick = (e) => { e.stopPropagation(); goStock(n.dataset.code); }; });
    const paint = (id) => {
      nodes.forEach(n => { n.classList.toggle('sel', !!id && n.dataset.part === id); n.classList.toggle('dim', !!id && n.dataset.part !== id); });
      $$('#themeMembers tr', host).forEach(tr => tr.classList.toggle('sel', !!id && (codesOf[id] || []).includes(tr.dataset.code)));
      if (!box) return;
      if (!id || !(codesOf[id] || []).length) { box.innerHTML = ''; return; }
      const n = nodes.find(x => x.dataset.part === id && x.classList.contains('stn')) || nodes.find(x => x.dataset.part === id);
      const ttl = (n && $('.lbl', n) && $('.lbl', n).textContent) || '';
      const mem = new Set((t.members || []).map(m => m.code));
      // 依族群分組列出這個環節的台股，才看得出來誰跟誰是同一塊的競爭對手
      const byG = {};
      codesOf[id].forEach(c => { const g = L.cgroup[c] || '_'; (byG[g] = byG[g] || []).push(c); });
      box.innerHTML = `<div class="segbox" style="--c:${color[id]}"><b class="t">${fmt.esc(ttl)}</b>
        <span class="muted" style="font-size:12px">灰色＝目前不在這個題材成員名單裡，但同樣做這塊</span>
        ${Object.entries(byG).map(([g, cs]) => `<div class="row"><span class="muted" style="min-width:7em">${g === '_' ? '未分類' : L.group(g)}</span>${cs.map(c => L.stock(c, null, { cls: mem.has(c) ? '' : 'out' })).join('')}</div>`).join('')}</div>`;
    };
    let cur = null;
    nodes.forEach(n => { n.onclick = (e) => { e.stopPropagation(); cur = (cur === n.dataset.part) ? null : n.dataset.part; paint(cur); }; });
    $$('#themeMembers tr', host).forEach(tr => {
      tr.onmouseenter = () => { if (cur) return; const hit = Object.keys(codesOf).find(k => codesOf[k].includes(tr.dataset.code)); nodes.forEach(n => n.classList.toggle('sel', !!hit && n.dataset.part === hit)); };
      tr.onmouseleave = () => { if (!cur) nodes.forEach(n => n.classList.remove('sel')); };
    });
  }
  // 題材成員依族群分組：同族群的擺在一起，才看得出來誰跟誰在搶同一塊
  function themeMembersByGroup(t) {
    const by = new Map();
    (t.members || []).forEach(m => {
      const g = L.cgroup[m.code] || '_';
      if (!by.has(g)) by.set(g, { gid: g, name: g === '_' ? '未分類' : (L.gname[g] || g), rows: [], turnover: 0 });
      const e = by.get(g); e.rows.push(m); e.turnover += m.turnover || 0;
    });
    return [...by.values()].sort((a, b) => b.turnover - a.turnover);
  }
  function renderThemeDetail(th, id) {
    const t = th.themes.find(x => x.id === id) || th.themes[0]; if (!t) return;
    const el = $('#themeDetail');
    const dg = (window.ThemeDiagrams || {})[t.id];
    const groups = themeMembersByGroup(t);
    el.innerHTML = `<div class="grid g12"><div class="card"><div class="row spread"><h3>${fmt.esc(t.name)} <small>${fmt.esc(t.desc || '')}</small></h3>
      <button class="btn small" id="themeBack">← 回題材總覽</button></div>
      <div class="kvs" style="margin:10px 0"><div class="k"><div class="l">熱度</div><div class="v" style="color:${t.heat >= 70 ? CH.up : CH.amber}">${t.heat}</div></div><div class="k"><div class="l">成交值佔比</div><div class="v">${fmt.n(t.share, 1)}%</div></div><div class="k"><div class="l">5 日 vs 60 日</div><div class="v ${fmt.cls(t.flow_z)}">${t.flow_z != null ? (t.flow_z > 0 ? '+' : '') + t.flow_z.toFixed(1) + 'σ' : '—'}</div></div><div class="k"><div class="l">法人 5 日</div><div class="v ${fmt.cls(t.inst5)}">${t.inst5 != null ? fmt.lot(t.inst5 / 1000) : '—'}</div></div><div class="k"><div class="l">新聞 7 天</div><div class="v">${t.news7}</div></div></div>
      <div id="themeSeries" class="chart short"></div></div>
      <div class="card"><h3>成員 <small>依族群分組、組內依成交值；滑過任一列會亮出它在產品圖上的位置</small></h3><div class="tw cap-md"><table id="themeMembers"><thead><tr><th class="l">代號</th><th class="l">簡稱</th><th>漲跌</th><th>成交值</th><th>法人</th></tr></thead><tbody>${groups.map(g => `<tr class="ghead"><td class="l" colspan="5">${g.gid === '_' ? '<span class="muted">未分類</span>' : L.group(g.gid)} <span class="muted">${g.rows.length} 檔 · ${fmt.yi(g.turnover)}</span></td></tr>`
      + g.rows.sort((a, b) => (b.turnover || 0) - (a.turnover || 0)).map(m => `<tr data-code="${m.code}" onclick="goStock('${m.code}')"><td class="l mono">${m.code}</td><td class="l">${L.stock(m.code, m.name)}</td><td class="num ${fmt.cls(m.chg_pct)}">${fmt.pct(m.chg_pct, 2)}</td><td class="num">${fmt.yi(m.turnover)}</td><td class="num ${fmt.cls(m.inst_net)}">${m.inst_net != null ? fmt.lot(m.inst_net / 1000) : '—'}</td></tr>`).join('')).join('')}</tbody></table></div>
      <div class="linkrow" style="margin-top:8px"><span class="muted">其他題材</span>${th.themes.filter(x => x.id !== t.id).slice(0, 12).map(x => L.theme(x.id, x.name)).join('')}</div></div></div>
      ${dg ? `<div class="card" style="margin-top:16px"><div class="row spread"><h3>產品剖析圖 <small>上游 → 中游 → 下游；原創等角示意圖，非實物比例。點環節看該段台股、點代號直接進個股頁</small></h3></div>
        <div id="themeDiagram" class="dgwrap">${dg()}</div><div id="themeParts"></div></div>` : ''}`;
    if (dg) {
      // 爆炸圖的零件高矮差很多，字串階段量不到尺寸，進 DOM 之後再等比縮到各自那一列
      if (window.ThemeDiagrams.fit) window.ThemeDiagrams.fit($('#themeDiagram', el));
      // 剖析圖不加滾輪縮放（跟產業／個股剖析圖一致，DECISIONS #84；Andy 09-13 再確認）
      // 要看大圖按右上角「放大」，那是明確的按鈕，不會搶走頁面捲動
      wireThemeDiagram(el, t);
    }
    // 點進某個題材之後要回得去（不然只能按瀏覽器上一頁）
    const back = $('#themeBack', el);
    if (back) back.onclick = () => {
      location.hash = '#themes';
      const m = $('#themeMap'); if (m && m.scrollIntoView) m.scrollIntoView({ behavior: 'smooth', block: 'start' });
    };
    const s = th.series[t.id] || [];
    chart('themeSeries', { tooltip: { ...tip, trigger: 'axis' }, grid: { left: 44, right: 16, top: 16, bottom: 26 }, xAxis: { ...axisStyle, type: 'category', data: s.map(x => x[0]), axisLabel: { color: CH.ink3, formatter: v => v.slice(5) } }, yAxis: { ...axisStyle, scale: true, axisLabel: { formatter: '{value}%' } },
      series: [{ name: '成交值佔比', type: 'line', data: s.map(x => x[1]), smooth: .3, showSymbol: false, lineStyle: { color: '#ff8fab', width: 2 }, areaStyle: { color: 'rgba(255,143,171,.15)' } }] });
  }

  // ---------------------------------------------------------------- 季節性
  async function renderSeason() {
    const s3 = await load('seasonality_v3'); if (!s3 || !s3.periods || !Object.keys(s3.periods).length) { empty('seasonHeat', '季節性需要歷史回補完成'); return; }
    let period = s3.periods['all'] ? 'all' : Object.keys(s3.periods)[0], metric = 'avg_excess';
    const draw = () => {
      const P = s3.periods[period]; if (!P) return empty('seasonHeat');
      $('#seasonRange').textContent = `${P.from} ～ ${P.to}，${P.years} 年`;
      const hasExcess = P.cells.some(c => c.avg_excess != null);
      if (metric === 'avg_excess' && !hasExcess) { metric = 'avg_return'; $$('#seasonMetric button').forEach(b => b.classList.toggle('on', b.dataset.v === metric)); }
      const groups = s3.groups; const gi = {}; groups.forEach((g, i) => { gi[g.group_id] = i; });
      const data = P.cells.map(c => [c.month - 1, gi[c.group_id], c[metric], c]);
      const isWin = metric === 'win_rate'; const vals = data.map(d => d[2]).filter(v => v != null);
      const lim = isWin ? [0, 100] : [-(Math.max(...vals.map(Math.abs)) || 5), Math.max(...vals.map(Math.abs)) || 5];
      const c = chart('seasonHeat', { tooltip: { ...tip, formatter: p => { const cl = p.data[3]; return `<b>${cl.group_name}</b> ${cl.month} 月<br>平均超額 ${cl.avg_excess != null ? fmt.pct(cl.avg_excess) : '—'}（勝率 ${cl.excess_win_rate ?? '—'}%）<br>平均報酬 ${cl.avg_return != null ? fmt.pct(cl.avg_return) : '—'}（勝率 ${cl.win_rate ?? '—'}%）<br>樣本 ${cl.samples} 年`; } },
        grid: { left: 130, right: 70, top: 10, bottom: 30 }, xAxis: { type: 'category', data: Array.from({ length: 12 }, (_, i) => (i + 1) + ' 月'), ...axisStyle, splitArea: { show: false }, axisLabel: { color: CH.ink2 } },
        yAxis: { type: 'category', data: groups.map(g => g.group_name), ...axisStyle, axisLabel: { color: CH.ink2, fontSize: 12 } },
        visualMap: { min: lim[0], max: lim[1], calculable: false, orient: 'vertical', right: 0, top: 'center', textStyle: { color: CH.ink3 }, // 中點以前用 #0f172b —— 那就是面板底色，±5% 以內的格子全部隱形，等於整張圖沒有顏色。
        // 換成看得見的中性藍灰，兩端也拉亮。
        inRange: { color: isWin ? ['#16203a', '#8b7bff', '#ff6b84'] : ['#19c489', '#16203a', '#ff6b84'] } },
        series: [{ type: 'heatmap', data: data.map(d => [d[0], d[1], d[2] == null ? null : +d[2].toFixed(1), d[3]]), label: { show: true, color: '#e8eeff', fontSize: 11, fontFamily: 'JetBrains Mono', formatter: p => p.data[2] == null ? '' : (isWin ? p.data[2] : (p.data[2] > 0 ? '+' : '') + p.data[2]) }, itemStyle: { borderColor: '#0b1224', borderWidth: 2, borderRadius: 3 }, emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,.6)' } } }] });
      if (c) c.off('click').on('click', p => drill(p.data[3]));
      $('#seasonNote').textContent = s3.note + `　大盤月報酬樣本 ${s3.benchmark_months} 個月。`;
      topThisMonth(P);
    };
    const drill = (cell) => {
      const det = (s3.detail || {})[cell.group_id] || {}; const years = Object.keys(det).sort();
      const vals = years.map(y => det[y][cell.month] ?? det[y][String(cell.month)]);
      $('#seasonDrillTitle').innerHTML = `${L.group(cell.group_id, cell.group_name)} · ${cell.month} 月逐年超額報酬 <small>紅正綠負 · 點族群名看成分股</small>`;
      chart('seasonDrill', { tooltip: { ...tip, formatter: p => `${p.name} 年：${p.value != null ? fmt.pct(p.value) : '—'}` }, grid: { left: 50, right: 16, top: 16, bottom: 30 }, xAxis: { ...axisStyle, type: 'category', data: years, axisLabel: { color: CH.ink3 } }, yAxis: { ...axisStyle, axisLabel: { formatter: '{value}%' } },
        series: [{ type: 'bar', data: vals.map(v => ({ value: v, itemStyle: { color: v > 0 ? CH.up : CH.down, borderRadius: 3 } })), barWidth: '55%' }] });
    };
    const topThisMonth = (P) => {
      const m = new Date().getMonth() + 1;
      const rows = P.cells.filter(c => c.month === m && (c.avg_excess != null || c.avg_return != null)).map(c => ({ ...c, score: (c.excess_win_rate ?? c.win_rate ?? 0) * 0.6 + Math.max(-20, Math.min(20, c.avg_excess ?? c.avg_return ?? 0)) })).sort((a, b) => b.score - a.score).slice(0, 8);
      $('#seasonTop').innerHTML = rows.length ? `<div class="tw"><table><thead><tr><th class="l">族群</th><th>超額報酬</th><th>勝率</th><th>絕對報酬</th><th>樣本</th></tr></thead><tbody>${rows.map(r => `<tr onclick="location.hash='#industry/group/${r.group_id}'"><td class="l">${L.group(r.group_id, r.group_name)}</td><td class="num ${fmt.cls(r.avg_excess)}">${r.avg_excess != null ? fmt.pct(r.avg_excess) : '—'}</td><td class="num">${r.excess_win_rate ?? r.win_rate ?? '—'}%</td><td class="num ${fmt.cls(r.avg_return)}">${r.avg_return != null ? fmt.pct(r.avg_return) : '—'}</td><td class="num">${r.samples}</td></tr>`).join('')}</tbody></table></div><div class="note" style="margin-top:8px">${m} 月，依「超額報酬勝率 × 0.6 ＋ 平均超額」排序；樣本少於 3 年不列。</div>` : '<div class="empty">本月尚無足夠樣本</div>';
    };
    $$('#seasonPeriod button').forEach(b => b.onclick = () => { $$('#seasonPeriod button').forEach(x => x.classList.toggle('on', x === b)); period = b.dataset.v; draw(); });
    $$('#seasonMetric button').forEach(b => b.onclick = () => { $$('#seasonMetric button').forEach(x => x.classList.toggle('on', x === b)); metric = b.dataset.v; draw(); });
    $$('#seasonPeriod button').forEach(b => { b.style.display = s3.periods[b.dataset.v] ? '' : 'none'; });
    draw();
  }

  // ---------------------------------------------------------------- 事件側欄
  async function renderEvents() {
    const [news, bv] = await Promise.all([load('news'), load('broker_views')]);
    const items = (news || []).map(n => ({ ...n, cat: n.category || '台股' }));
    (bv || []).forEach(b => items.push({ date: b.date, title: `${b.broker || '券商'} 目標價 ${b.target_price}${b.name ? '（' + b.name + ' ' + b.code + '）' : ''}${b.action ? ' · ' + b.action : ''}`, url: b.url, source: '新聞引述', cat: '券商', code: b.code }));
    items.sort((a, b) => String(b.published_at || b.date).localeCompare(String(a.published_at || a.date)));
    $('#evCount').textContent = items.length; $('#evDate').textContent = D.meta ? D.meta.data_date : '';
    let cat = 'all';
    const draw = () => { $('#evList').innerHTML = items.filter(i => cat === 'all' || i.cat === cat).slice(0, 80).map(i => `<div class="ev"><a href="${fmt.esc(i.url || '#')}" target="_blank" rel="noopener">${fmt.esc(i.title)}</a><div class="m"><span class="mono">${fmt.esc(String(i.date || '').slice(0, 10))}</span><span class="cat">${fmt.esc(i.cat)}</span><span>${fmt.esc(i.source || '')}</span>${(i.code ? [i.code] : String(i.codes || '').split(/[,\s]+/).filter(Boolean)).slice(0, 4).map(c => L.stock(c, L.cname[c] || c, { cls: 'sm' })).join('')}</div></div>`).join('') || '<div class="empty">沒有這類事件</div>'; };
    $$('#evFilters button').forEach(b => b.onclick = () => { $$('#evFilters button').forEach(x => x.classList.toggle('on', x === b)); cat = b.dataset.c; draw(); });
    draw();
    /* 事件側欄要真的關得掉。手機用 .open 滑出來，桌機要靠 .layout.noside 把那一欄收掉 ——
       以前只 toggle .open，桌機按了完全沒反應，而且側欄佔掉 360px 讓候選表的六個欄位躲進捲軸。 */
    const SIDE_KEY = 'tw.side';
    const setSide = (open) => {
      $('#side').classList.toggle('open', open);
      $('#layout').classList.toggle('noside', !open);
      try { localStorage.setItem(SIDE_KEY, open ? '1' : '0'); } catch (e) { /* 忽略 */ }
      window.dispatchEvent(new Event('resize'));       // 欄寬變了，圖表要重畫
    };
    let sideOpen = true;
    try { sideOpen = localStorage.getItem(SIDE_KEY) !== '0'; } catch (e) { /* 忽略 */ }
    setSide(sideOpen);
    $('#evToggle').onclick = () => setSide($('#layout').classList.contains('noside'));
    $('#evClose').onclick = () => setSide(false);
  }

  // ---------------------------------------------------------------- 搜尋
  async function initSearch() {
    const idx = {};
    (L.all || []).forEach(c => { idx[c.code] = c.name || c.code; });
    if (!Object.keys(idx).length) {           // 索引還沒產出時的退路
      const cands = await load('candidates'); const gd = await load('groups_detail');
      (cands || []).forEach(c => { idx[c.code] = c.name; });
      Object.values(gd || {}).forEach(g => (g.members || []).forEach(m => { if (!idx[m.code]) idx[m.code] = m.name; }));
    }
    const list = Object.entries(idx);
    const q = $('#q'), sg = $('#sugg');
    q.addEventListener('input', () => { const v = q.value.trim().toLowerCase(); if (!v) { sg.style.display = 'none'; return; } const hits = list.filter(([c, n]) => c.startsWith(v) || (n || '').toLowerCase().includes(v)).slice(0, 12); sg.innerHTML = hits.map(([c, n]) => `<div data-c="${c}"><span class="code">${c}</span>${fmt.esc(n)}<span class="g">${fmt.esc(L.gname[L.cgroup[c]] || '')}</span></div>`).join(''); sg.style.display = hits.length ? 'block' : 'none'; $$('div', sg).forEach(d => d.onclick = () => { sg.style.display = 'none'; q.value = ''; goStock(d.dataset.c); }); });
    q.addEventListener('keydown', e => { if (e.key === 'Enter') { const v = q.value.trim(); const hit = list.find(([c]) => c === v) || list.find(([c, n]) => (n || '') === v); if (hit) { sg.style.display = 'none'; q.value = ''; goStock(hit[0]); } } });
    document.addEventListener('click', e => { if (!e.target.closest('.search')) sg.style.display = 'none'; });
  }

  /* 資料新鮮度（Andy：「我今天盤後才看到，等到隔天才買」「不知道到底更新了沒」）：
     把「更新到哪一天、落後多少、哪些來源沒回資料、上次跑是什麼時候」直接攤在頁面頂端。
     以前只有「3 天沒更新」才會跳提示，而且來源失敗完全看不出來（errors 一直是空陣列）。*/
  function renderFreshness(meta) {
    const pad = (n) => String(n).padStart(2, '0');
    const tpe = (iso) => { if (!iso) return null; const d = new Date(iso);
      const t = new Date(d.getTime() + 8 * 3600e3);    // 轉台北時間
      return `${t.getUTCFullYear()}-${pad(t.getUTCMonth() + 1)}-${pad(t.getUTCDate())} ${pad(t.getUTCHours())}:${pad(t.getUTCMinutes())}`; };
    const D_ = meta.data_date || '';
    $('#asof').textContent = D_ ? `${D_} 盤後` : '—';

    const bits = [];
    let level = '';                                     // '' 正常 / 'warn' / 'bad'
    // 1) 資料湖已經有更新的一天，但前端沒採用 → 那天的上市資料沒到齊
    if (meta.price_ahead_of_payload && meta.price_latest) {
      bits.push(`資料湖已經有 <b>${fmt.esc(String(meta.price_latest))}</b> 的價格，但那天的上市資料沒到齊，所以畫面仍顯示 <b>${fmt.esc(D_)}</b>`);
      level = 'warn';
    }
    // 2) 多久沒更新
    const gen = meta.generated_at ? new Date(meta.generated_at) : null;
    if (gen) {
      const hrs = (Date.now() - gen.getTime()) / 3600e3;
      if (hrs > 72) { bits.push(`已經 <b>${Math.floor(hrs / 24)} 天</b>沒有重新產出，排程可能掛了`); level = 'bad'; }
      else if (hrs > 30) { bits.push(`上次產出是 ${Math.floor(hrs)} 小時前`); level = level || 'warn'; }
    }
    // 3) 哪些來源沒回資料
    const empt = meta.last_run_empty || [], errs = meta.last_run_errors || [];
    if (errs.length) { bits.push(`來源出錯：<b>${errs.slice(0, 4).map(e => fmt.esc(String(e).split(':')[0])).join('、')}</b>`); level = 'bad'; }
    if (empt.length) { bits.push(`沒回資料的來源：<b>${empt.slice(0, 6).map(fmt.esc).join('、')}</b>`); level = level || 'warn'; }
    if (meta.demo) { bits.push('這是示範資料，不是真實行情'); level = 'bad'; }

    const tail = [];
    // 盤後第一輪（台北 15:30）只抓價量，法人／融資券要傍晚才出。
    // 講清楚是「還沒到」而不是「掛了」，否則每天下午都會被誤會。
    if (meta.last_run_phase === 'price') tail.push('這輪只更新價量（法人與融資券傍晚那輪才補）');
    if (meta.last_run_at) tail.push(`上次抓資料 ${tpe(meta.last_run_at)}`);
    if (gen) tail.push(`上次產出 ${tpe(meta.generated_at)}`);
    const b = $('#banner');
    if (!bits.length) {                                  // 一切正常也要講一句，讓人知道系統是活的
      b.innerHTML = `<b>資料更新到 ${fmt.esc(D_)} 盤後</b>，所有來源正常。${tail.length ? '<span class="muted">（' + tail.join('、') + '，台北時間）</span>' : ''}`;
      b.className = 'banner on ok';
    } else {
      b.innerHTML = `<b>資料更新到 ${fmt.esc(D_)} 盤後</b>　·　${bits.join('　·　')}${tail.length ? '<br><span class="muted">' + tail.join('、') + '（台北時間）</span>' : ''}`;
      b.className = 'banner on ' + (level === 'bad' ? 'bad' : 'warn');
    }
  }

  // ---------------------------------------------------------------- 啟動
  async function boot() {
    if (typeof echarts === 'undefined' || typeof LightweightCharts === 'undefined') { $('#banner').textContent = '圖表函式庫載入失敗（vendor/ 目錄缺檔），請重新整理。'; $('#banner').classList.add('on'); }
    const meta = await load('meta');
    if (meta) { renderFreshness(meta); }
    window.App = { load, chart, fmt, tip, axisStyle, CH, PALETTE, chgColor, upDown, empty, charts, goStock, D, L, wheelZoom };
    const [im, gt, cands, th, sc, all] = await Promise.all([load('industry_map'), load('groups_today'), load('candidates'), load('themes'), load('supply_chain'), load('stocks', { fallback: [] })]);
    L.init(im, gt, cands, th, sc, all);
    await Promise.all([renderEvents(), initSearch()]);
    await route();
    // 盤中即時層。放在 route() 之後：畫面上先有代號，Live 才知道要抓哪些。
    if (window.Live) window.Live.start();
  }
  boot();
})();
