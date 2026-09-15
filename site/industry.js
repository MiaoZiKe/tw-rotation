/* 產業與個股（合併頁）：產業地圖 → 單一產業鏈（產品剖析圖 + 分層關聯圖 + 成分股）→ 個股頁。
   個股頁上方永遠帶著它所屬的產業鏈，點任何股票上方同步更新。 */
(function () {
  'use strict';
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
  let A;                                   // window.App（app.js 提供）
  const state = { level: 0, chain: null, group: null, code: null, tf: '1d', mtfMode: false, cfg: null, tab: 'overview' };
  const CHAIN_NAME = { semiconductor: '半導體', ai_server: 'AI 伺服器', electronics: '一般電子', traditional: '傳產', infrastructure: '基礎建設', _other: '其他族群', industry: '產業別' };
  const SEG_COLORS = ['#3ee0ff', '#8b7bff', '#ffb454', '#c3ff5b', '#ff8fab', '#5ec8ff', '#f9f871', '#7ee8c7', '#ff9f68', '#b39dff', '#6ee7b7', '#fca5a5', '#93c5fd', '#fde68a'];
  let kchart = null, miniCharts = [];
  // 即時分 K 的訂閱（換頁要退掉，不然背景還在每 5 秒重畫一張看不到的圖）
  let liveOff = null;

  function setLiveNote(txt) {
    const el = document.getElementById('liveNote');
    if (!el) return;
    el.hidden = !txt;
    el.textContent = txt || '';
  }
  function stopLive() {
    if (liveOff) { liveOff(); liveOff = null; }
    if (window.LiveK) window.LiveK.detach();
  }

  // ================================================================ 路由
  async function route(head, rest) {
    A = window.App;
    dispose3D();   // 換頁一定要收掉 WebGL context（瀏覽器最多只給十幾個，不收會整個掛掉）
    if (head !== 'stock') stopLive();   // 離開個股頁就不要再每 5 秒抓報價了
    const [im, sc, gd] = await Promise.all([A.load('industry_map'), A.load('supply_chain'), A.load('groups_detail')]);
    if (head === 'stock') { state.level = 2; state.code = rest[0]; await renderStock(rest[0], im, sc, gd); return; }
    if (rest[0] === 'group' && rest[1]) { state.group = rest[1]; state.chain = chainOfGroup(im, rest[1]); state.level = 1; renderChain(im, sc, gd); return; }
    if (rest[0]) { state.chain = rest[0]; state.group = null; state.level = 1; renderChain(im, sc, gd, { seg: rest[1] || null }); return; }
    state.level = 0; state.chain = null; state.group = null; renderMap(im);
  }
  function chainOfGroup(im, gid) {
    if (!im) return null;
    if (gid.startsWith('ind_')) return 'industry';
    for (const c of im.chains) if (c.groups.some(g => g.id === gid)) return c.id;
    return null;
  }
  function crumbs(items) { $('#indCrumbs').innerHTML = items.map((it, i) => it.href ? `<a onclick="location.hash='${it.href}'">${it.label}</a>${i < items.length - 1 ? '›' : ''}` : `<span class="cur">${it.label}</span>`).join(' '); }
  function show(map, chain, stock) { $('#indMap').style.display = map ? '' : 'none'; $('#indChain').style.display = chain ? '' : 'none'; $('#stockPage').style.display = stock ? '' : 'none'; }

  // ================================================================ Level 0：產業地圖
  function renderMap(im) {
    show(true, false, false); crumbs([{ label: '產業地圖' }]);
    if (!im || !im.chains) { $('#indMap').innerHTML = '<div class="empty">尚無產業資料</div>'; return; }
    const el = $('#indMap');
    el.innerHTML = `<div class="card"><h3>整個台股一次看 <small>方塊＝族群成交值，顏色＝今日漲跌（紅漲綠跌）；點產業鏈進入單一鏈，點族群直接看成分股</small></h3><div class="zwrap" id="indTreeWrap"><div id="indTree" class="chart" style="min-height:520px"></div></div></div>
      <div class="grid g2" style="margin-top:16px"><div class="card"><h3>產業鏈總覽 <small>本益比為族群中位數（同族群才比）</small></h3><div class="tiles" id="chainTiles"></div></div>
      <div class="card"><h3>法定產業別 <small>沒被歸入題材族群的公司依證交所產業別歸戶</small></h3><div class="tiles" id="indTiles"></div></div></div>`;
    const data = im.chains.map(c => ({ name: c.name, cid: c.id, children: c.groups.map(g => ({ name: g.name, value: g.turnover || 1, gid: g.id, chg: g.chg_pct, share: g.turnover_share, pe: g.valuation && g.valuation.median, n: g.n, itemStyle: { color: A.chgColor(g.chg_pct, 3) } })) }));
    const c = A.chart('indTree', { tooltip: { ...A.tip, formatter: p => p.data.gid ? `<b>${p.name}</b><br>成交值 ${A.fmt.yi(p.value)}（${A.fmt.n(p.data.share, 1)}%）· ${p.data.n} 檔<br>漲跌 <span style="color:${A.upDown(p.data.chg)}">${A.fmt.pct(p.data.chg)}</span> · 本益比中位 ${p.data.pe != null ? A.fmt.n(p.data.pe, 1) : '—'}` : `<b>${p.name}</b>（點進入產業鏈）` },
      series: [{ type: 'treemap', roam: false, nodeClick: false, breadcrumb: { show: false }, top: 0, left: 0, width: '100%', height: '100%', leafDepth: 2, visibleMin: 900,
        label: { formatter: p => `${p.name}\n${A.fmt.pct(p.data.chg)}`, fontSize: 13, color: '#fff', textShadowColor: '#000', textShadowBlur: 4 },
        upperLabel: { show: true, height: 26, color: '#e8eeff', fontSize: 13, fontWeight: 700, backgroundColor: 'rgba(0,0,0,.3)' },
        itemStyle: { borderColor: '#0b1224', borderWidth: 2, gapWidth: 2 }, levels: [{ itemStyle: { borderWidth: 4, gapWidth: 4 }, upperLabel: { show: true } }, { itemStyle: { gapWidth: 1 } }], data }] });
    A.wheelZoom($('#indTreeWrap'), { onZoom: () => { const i = window.echarts && echarts.getInstanceByDom($('#indTree')); if (i) i.resize(); } });
    if (c) c.off('click').on('click', p => { if (p.data.gid) location.hash = '#industry/group/' + p.data.gid; else if (p.data.cid) location.hash = '#industry/' + p.data.cid; else if (p.treePathInfo && p.treePathInfo[1]) { const cid = (im.chains.find(x => x.name === p.treePathInfo[1].name) || {}).id; if (cid) location.hash = '#industry/' + cid; } });
    $('#chainTiles').innerHTML = im.chains.map(ch => { const pes = ch.groups.map(g => g.valuation && g.valuation.median).filter(Boolean); const chg = wavg(ch.groups); return `<div class="tile" onclick="location.hash='#industry/${ch.id}'"><div class="t">${ch.name}</div><div class="m">${ch.groups.length} 個族群 · ${ch.groups.reduce((s, g) => s + (g.n || 0), 0)} 檔</div><div class="v"><span class="${A.fmt.cls(chg)}">${A.fmt.pct(chg)}</span> <small style="font-size:12px;color:var(--ink-3)">PE 中位 ${pes.length ? A.fmt.n(median(pes), 1) : '—'}</small></div></div>`; }).join('');
    $('#indTiles').innerHTML = im.industries.slice(0, 18).map(g => `<div class="tile" onclick="location.hash='#industry/group/${g.id}'"><div class="t">${g.name}</div><div class="m">${g.n} 檔 · 佔比 ${A.fmt.n(g.turnover_share, 1)}%</div><div class="v ${A.fmt.cls(g.chg_pct)}">${A.fmt.pct(g.chg_pct)}</div></div>`).join('');
  }
  const median = (a) => { const s = a.slice().sort((x, y) => x - y); return s.length ? (s.length % 2 ? s[(s.length - 1) / 2] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2) : null; };
  const wavg = (gs) => { let w = 0, s = 0; gs.forEach(g => { if (g.chg_pct != null && g.turnover) { w += g.turnover; s += g.chg_pct * g.turnover; } }); return w ? s / w : null; };

  // ================================================================ Level 1：單一產業鏈
  function chainData(im, cid) {
    if (!im) return null;
    if (cid === 'industry') return { id: 'industry', name: '產業別', groups: im.industries };
    return im.chains.find(c => c.id === cid) || null;
  }
  const HAS_DIAGRAM = (cid) => ['semiconductor', 'ai_server'].includes(cid);
  // 哪些環節屬於這條鏈（半導體鏈把載板／封測也畫進來；AI 伺服器鏈把代工／封裝／HBM 畫進來）
  function chainSegments(sc, cid) {
    if (!sc) return [];
    return sc.segments.filter(s => s.chain === cid || (cid === 'ai_server' && ['foundry', 'adv_pkg', 'hbm'].includes(s.id)) || (cid === 'semiconductor' && ['abf_pcb', 'osat_test'].includes(s.id)));
  }
  const segName = (sc, id) => ((sc && sc.segments.find(s => s.id === id)) || {}).name || id;
  const segColor = (id) => (A.L.scolor[id] || '#8ea0c4');
  const twOf = (sc, seg) => (sc ? sc.companies.filter(c => c.segment === seg && c.tw_code) : []);
  const foreignOf = (sc, seg) => (sc ? sc.companies.filter(c => c.segment === seg && !c.tw_code) : []);

  function renderChain(im, sc, gd, opts) {
    opts = opts || {};
    const ch = chainData(im, state.chain);
    if (!ch) { show(true, false, false); renderMap(im); return; }
    show(false, true, false); crumbs([{ label: '產業地圖', href: '#industry' }, { label: ch.name }]);
    const el = $('#indChain');
    const hasDiagram = HAS_DIAGRAM(ch.id);
    const groups = state.group && ch.id === 'industry' ? ch.groups.filter(g => g.id === state.group) : ch.groups;
    const chg = wavg(groups); const pes = groups.map(g => g.valuation && g.valuation.median).filter(Boolean);
    const segs = chainSegments(sc, ch.id);
    const otherChains = (im.chains || []).filter(c => c.id !== ch.id);
    el.innerHTML = `
      <div class="card">
        <div class="row spread"><div><h2>${A.fmt.esc(ch.name)}${state.group && ch.id === 'industry' ? ' · ' + A.fmt.esc((groups[0] || {}).name) : ''}</h2>
          <div class="sub">${hasDiagram ? '剖析圖的零件、環節色標、關聯圖的公司、族群卡片都是同一套顏色：點任一個，其餘同色的一起亮，下方成分股同步篩選；點公司名進入個股頁。' : '點族群卡片篩選成分股；點股票進入個股頁。'}</div></div>
          <div class="row"><span class="pill">${groups.reduce((s, g) => s + (g.n || 0), 0)} 檔</span><span class="pill ${A.fmt.cls(chg)}">今日 ${A.fmt.pct(chg)}</span><span class="pill violet">本益比中位 ${pes.length ? A.fmt.n(median(pes), 1) : '—'}</span>${A.L.back()}</div></div>
        ${hasDiagram ? `<div style="margin-top:14px"><div class="row spread"><h4>產品剖析圖 <small class="muted">原創示意圖，非實物比例；每個零件對應一個供應鏈環節，點零件看供應商</small></h4><div class="row" style="gap:6px"><span class="pill" id="dg3d" style="cursor:pointer" hidden>3D 立體</span><span class="pill" id="dgReset" style="cursor:pointer" hidden>重設視角</span><span class="pill" id="dgAnim" style="cursor:pointer">動畫：開</span></div></div><div id="prodDiagram" class="dgwrap">${window.Diagrams[ch.id]()}</div><div id="prod3d" class="dg3d" hidden></div><div class="note" id="dg3dNote" hidden></div></div>` : ''}
        ${segs.length ? `<div class="segchips" id="segChips">${segs.map(s => { const tw = twOf(sc, s.id), fo = foreignOf(sc, s.id); return `<span class="segchip ${tw.length ? '' : 'nomem'}" data-seg="${s.id}" style="--c:${segColor(s.id)}" title="${tw.length ? tw.length + ' 檔台股' : '台股沒有直接對應，看外商'}"><i></i>${A.fmt.esc(s.name)}<span class="n">${tw.length ? tw.length : (fo.length ? '外商 ' + fo.length : '—')}</span></span>`; }).join('')}</div><div id="segBox"></div>` : ''}
        ${hasDiagram ? `<div style="margin-top:14px"><h4>供應鏈關聯圖 <small class="muted">上游 → 下游；線越粗依存度越高；虛線框＝外商；點公司進入個股頁</small></h4><div class="chainmap" id="chainMap"></div></div>` : ''}
        <div style="margin-top:14px"><h4>族群 <small class="muted">卡片顏色＝剖析圖零件與環節色；點卡片篩選成分股，點「族群頁」看該族群全部</small></h4><div class="row" id="groupCards" style="margin-top:8px;align-items:stretch"></div></div>
        ${otherChains.length ? `<div class="linkrow"><span class="muted">其他產業鏈</span>${otherChains.map(c => A.L.chain(c.id, c.name)).join('')}${A.L.chain('industry', '法定產業別')}</div>` : ''}
      </div>
      <div class="card" style="margin-top:16px"><div class="row spread"><h3 id="memberTitle">成分股</h3><div class="seg" id="mktSeg"><button data-v="ALL" class="on">全部</button><button data-v="TWSE">上市</button><button data-v="TPEX">上櫃</button></div></div>
        <div class="tw" style="margin-top:10px"><table id="memberTable"><thead></thead><tbody></tbody></table></div></div>`;
    // 族群卡片（顏色跟環節一致）
    const cardHtml = (g) => `<div class="tile colored ${state.group === g.id ? 'sel' : ''}" data-gid="${g.id}" style="min-width:180px;flex:1 1 200px;max-width:360px;--c:${A.L.gcolor[g.id] || '#8ea0c4'}"><div class="t">${A.fmt.esc(g.name)}</div><div class="m">${g.n} 檔 · 佔比 ${A.fmt.n(g.turnover_share, 1)}%${g.valuation && g.valuation.median ? ' · PE ' + A.fmt.n(g.valuation.median, 1) : ''}</div><div class="row spread" style="margin-top:4px"><div class="v ${A.fmt.cls(g.chg_pct)}" style="margin:0">${A.fmt.pct(g.chg_pct)}</div>${A.L.group(g.id, '族群頁 →', { dot: false, cls: 'sm' })}</div></div>`;
    $('#groupCards', el).innerHTML = groups.map(cardHtml).join('');
    let segFilter = opts.seg || null, mkt = 'ALL';
    const members = () => {
      let rows = []; groups.forEach(g => (g.members || []).forEach(m => rows.push({ ...m, group_name: g.name, gid: g.id })));
      if (state.group) rows = rows.filter(r => r.gid === state.group);
      if (segFilter && sc) { const codes = new Set(twOf(sc, segFilter).map(c => c.tw_code)); rows = rows.filter(r => codes.has(r.code)); }
      if (mkt !== 'ALL') rows = rows.filter(r => marketOf(r) === mkt);
      const seen = new Set(); return rows.filter(r => seen.has(r.code) ? false : (seen.add(r.code), true));
    };
    const COLS = [['code', '代號', r => `<span class="mono">${r.code}</span>`, 'l'], ['name', '簡稱', r => A.L.stock(r.code, r.name), 'l'], ['group_name', '族群', r => A.L.group(r.gid, r.group_name), 'l'], ['close', '收盤', r => `<span class="num" data-live="close" data-lc="${r.code}">${A.fmt.n(r.close)}</span>`], ['chg_pct', '漲跌', r => `<span class="num ${A.fmt.cls(r.chg_pct)}" data-live="chg" data-lc="${r.code}">${A.fmt.pct(r.chg_pct, 2)}</span>`], ['turnover', '成交值', r => `<span class="num">${A.fmt.yi(r.turnover)}</span>`], ['pe', '本益比', r => `<span class="num">${r.pe ? A.fmt.n(r.pe, 1) : '—'}</span>`], ['pe_percentile', '同業分位', r => `<span class="num">${r.pe_percentile != null ? A.fmt.n(r.pe_percentile, 0) + '%' : '—'}</span>`], ['momentum', '營運動能', r => `<span class="num">${r.momentum != null ? A.fmt.n(r.momentum, 0) : '—'}</span>`], ['foreign', '外資', r => `<span class="num ${A.fmt.cls(r.foreign)}">${r.foreign != null ? A.fmt.lot(r.foreign / 1000) : '—'}</span>`], ['trust', '投信', r => `<span class="num ${A.fmt.cls(r.trust)}">${r.trust != null ? A.fmt.lot(r.trust / 1000) : '—'}</span>`], ['grade', '技術判定', r => r.verdict ? `<span class="grade ${r.grade || 'W'}">${r.grade ? r.grade + ' ' : ''}${r.verdict}</span>` : '<span class="muted">—</span>', 'l']];
    /* 成分股預設照漲幅排（Andy 2026-09-15：「族群 Default 排序適用漲幅」）。
       以前預設是成交值，結果打開族群頁看到的永遠是那幾檔權值股，
       今天真的在動的中小型股要自己按一次表頭才看得到。
       按過表頭就記住，下次打開沿用他自己選的那一欄。 */
    const SORT_KEY = 'tw.memberSort';
    let sort = { key: 'chg_pct', dir: -1 };
    try {
      const s = JSON.parse(localStorage.getItem(SORT_KEY) || 'null');
      if (s && s.key) sort = { key: s.key, dir: s.dir === 1 ? 1 : -1 };
    } catch (e) { /* 忽略 */ }
    const renderMembers = () => {
      let rows = members(); rows.sort((a, b) => { const x = a[sort.key], y = b[sort.key]; if (x == null) return 1; if (y == null) return -1; return (x > y ? 1 : x < y ? -1 : 0) * sort.dir; });
      const segTw = segFilter ? twOf(sc, segFilter) : [];
      $('#memberTitle', el).innerHTML = `成分股 <small>${rows.length} 檔${segFilter ? ' · 環節：<span style="color:' + segColor(segFilter) + '">' + A.fmt.esc(segName(sc, segFilter)) + '</span>' : ''}${state.group ? ' · ' + A.fmt.esc((groups.find(g => g.id === state.group) || {}).name || '') : ''}</small>`;
      $('#memberTable thead', el).innerHTML = '<tr>' + COLS.map(c => `<th class="${c[3] || ''}" data-k="${c[0]}">${c[1]}${sort.key === c[0] ? (sort.dir > 0 ? ' ▲' : ' ▼') : ''}</th>`).join('') + '</tr>';
      $('#memberTable tbody', el).innerHTML = rows.slice(0, 200).map(r => `<tr data-code="${r.code}">` + COLS.map(c => `<td class="${c[3] || ''}">${c[2](r)}</td>`).join('') + '</tr>').join('')
        || `<tr><td colspan="12" class="l muted">${segFilter ? (segTw.length ? '這個環節的台股不在本鏈成分股裡：' + segTw.map(c => A.L.stock(c.tw_code, c.name)).join('　') : '這個環節目前沒有台股直接對應（' + foreignOf(sc, segFilter).map(c => c.name).join('、') + '），可看上方環節說明裡的相關族群') : '沒有符合的股票'}</td></tr>`;
      $$('#memberTable th', el).forEach(th => th.onclick = () => {
        sort = { key: th.dataset.k, dir: sort.key === th.dataset.k ? -sort.dir : -1 };
        try { localStorage.setItem(SORT_KEY, JSON.stringify(sort)); } catch (e) { /* 忽略 */ }
        renderMembers();
      });
      $$('#memberTable tbody tr', el).forEach(tr => tr.onclick = () => { if (tr.dataset.code) A.goStock(tr.dataset.code); });
    };
    /* 點剖析圖上的零件只做「亮起來 + 在原地說明這個環節」，
       不捲動、也不動下面的成分股表 —— Andy：「當我點擊圖片時，不用馬上切換到下方股票」。
       要真的篩成分股，用下面的環節晶片、族群卡片，或說明框裡那顆按鈕。 */
    let segHi = null;
    const syncHighlight = (opt) => {
      const o = opt || {};
      const shown = segFilter || segHi;
      const segsOn = shown ? [shown] : (state.group ? (A.L.gsegs[state.group] || []) : []);
      const color = shown ? segColor(shown) : (state.group ? A.L.gcolor[state.group] : null);
      highlightSegments(el, segsOn, color);
      if (segFilter && !o.quiet) scrollChainTo(el, segFilter);
      $$('#groupCards .tile', el).forEach(t => t.classList.toggle('sel', !!state.group && t.dataset.gid === state.group || (!!segFilter && (A.L.sgroups[segFilter] || []).includes(t.dataset.gid))));
      $$('#segChips .segchip', el).forEach(c => c.classList.toggle('sel', segsOn.includes(c.dataset.seg)));
      renderSegBox($('#segBox', el), sc, shown, ch, { filtered: !!segFilter, onFilter: () => {
        segFilter = shown; segHi = null; state.group = null; syncHighlight();
      } });
      if (!o.quiet) renderMembers();
    };
    $$('#groupCards .tile', el).forEach(t => t.onclick = (e) => { if (e.target.closest('a.lk')) return; state.group = state.group === t.dataset.gid ? null : t.dataset.gid; segFilter = null; segHi = null; syncHighlight(); });
    $$('#segChips .segchip', el).forEach(c => c.onclick = () => { segFilter = segFilter === c.dataset.seg ? null : c.dataset.seg; segHi = null; state.group = null; syncHighlight(); });
    $$('#mktSeg button', el).forEach(b => b.onclick = () => { $$('#mktSeg button', el).forEach(x => x.classList.toggle('on', x === b)); mkt = b.dataset.v; renderMembers(); });
    if (hasDiagram && sc) {
      paintDiagram($('#prodDiagram', el));
      // 剖析圖不加縮放：Andy 明講「產業與個股 剖析圖不用新增縮放功能」（本來就可以左右滑）
      drawChainMap($('#chainMap', el), sc, ch.id, im, { onSelect: (co) => { if (co && co.tw_code) A.goStock(co.tw_code); }, onSegment: (seg) => { segHi = segHi === seg ? null : seg; segFilter = null; syncHighlight({ quiet: true }); } });
      wireDiagram(el, (seg) => { segHi = segHi === seg ? null : seg; segFilter = null; syncHighlight({ quiet: true }); });
      const animBtn = $('#dgAnim', el); if (animBtn) animBtn.onclick = () => { const on = $('#prodDiagram', el).classList.toggle('noanim'); animBtn.textContent = on ? '動畫：關' : '動畫：開'; try { localStorage.setItem('tw.dganim', on ? '0' : '1'); } catch (e) { /* 忽略 */ } };
      try { if (localStorage.getItem('tw.dganim') === '0') { $('#prodDiagram', el).classList.add('noanim'); animBtn.textContent = '動畫：關'; } } catch (e) { /* 忽略 */ }
      // wire3D 是模組層級的函式，看不到這裡的 segHi／segFilter／syncHighlight，
      // 所以把要用到的動作當參數傳進去（之前直接寫在函式裡會噴 syncHighlight is not defined）。
      wire3D(el, ch.id, {
        onSeg: (seg) => { segHi = segHi === seg ? null : seg; segFilter = null; syncHighlight({ quiet: true }); },
        sync: () => syncHighlight({ quiet: true }),
      });
    }
    syncHighlight();
  }
  // 環節說明盒：這個環節的台股（可點）、外商、相關族群（可點）
  // 市場別一律以全市場索引（stocks.json）為準：groups_detail 的 market 欄位常常是空的
  const marketOf = (r) => String(A.L.cmarket[r.code] || r.market || '').toUpperCase() || null;

  function renderSegBox(box, sc, seg, ch, opt) {
    if (!box) return;
    if (!seg || !sc) { box.innerHTML = ''; return; }
    const o = opt || {};
    const tw = twOf(sc, seg), fo = foreignOf(sc, seg), gids = A.L.sgroups[seg] || [];
    const s = sc.segments.find(x => x.id === seg) || {};
    box.innerHTML = `<div class="segbox" style="--c:${segColor(seg)}"><div class="row spread">
        <div><b class="t">${A.fmt.esc(s.name || seg)}</b> <span class="muted">${s.desc ? A.fmt.esc(s.desc) : ''}</span></div>
        <button class="btn small" id="segOnly">${o.filtered ? '已套用到下方成分股' : '只看這個環節的成分股 →'}</button></div>
      <div class="row"><span class="muted">台股</span>${tw.length ? tw.map(c => A.L.stock(c.tw_code, c.name)).join('') : '<span class="muted">沒有直接對應的台股</span>'}</div>
      ${fo.length ? `<div class="row"><span class="muted">外商</span>${fo.map(c => `<span class="pill" title="${A.fmt.esc((c.tech || []).join('、'))}">${A.fmt.esc(c.name)}</span>`).join('')}</div>` : ''}
      ${gids.length ? `<div class="row"><span class="muted">相關族群</span>${gids.map(g => A.L.group(g)).join('')}</div>` : ''}</div>`;
    const btn = $('#segOnly', box);
    if (btn) { btn.disabled = !!o.filtered; if (o.onFilter && !o.filtered) btn.onclick = o.onFilter; }
  }
  // 讓剖析圖每個零件帶上環節色（CSS 用 var(--c)）
  function paintDiagram(root) {
    if (!root) return;
    $$('[data-seg]', root).forEach(n => { n.style.setProperty('--c', segColor(n.dataset.seg)); n.style.cursor = 'pointer'; });
    $$('[data-chain]', root).forEach(n => { n.style.cursor = 'pointer'; n.onclick = () => { location.hash = '#industry/' + n.dataset.chain; }; });
  }
  // 點下方環節後，右側供應鏈關聯圖自動捲到那一欄（不然要自己拉很久才找得到）
  function scrollChainTo(root, seg) {
    const map = $('#chainMap', root); if (!map || !seg) return;
    const t = $(`.chainmap .segtitle[data-seg="${seg}"]`, root) || $(`.chainmap .co[data-segment="${seg}"]`, root);
    if (!t || !t.getBBox) return;
    const svg = map.querySelector('svg'); if (!svg) return;
    const vb = (svg.getAttribute('viewBox') || '').split(/\s+/).map(Number);
    const scale = vb.length === 4 && vb[2] ? (svg.clientWidth || map.clientWidth) / vb[2] : 1;
    const b = t.getBBox();
    map.scrollTo({ left: Math.max(0, b.x * scale - 40), top: Math.max(0, b.y * scale - 40), behavior: 'smooth' });
    // 關聯圖本身也要進到視野裡，不然捲對了位置使用者還是看不到
    if (map.scrollIntoView) map.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
  function highlightSegments(root, segs, color) {
    const on = new Set(segs || []);
    if (view3d) view3d.highlight(on, color);       // 3D 場景與 SVG 用同一套高亮規則
    $$('#prodDiagram [data-seg]', root).forEach(n => { n.classList.toggle('sel', on.has(n.dataset.seg)); n.classList.toggle('dim', on.size > 0 && !on.has(n.dataset.seg)); if (color && on.has(n.dataset.seg)) n.style.setProperty('--c', color); else n.style.setProperty('--c', segColor(n.dataset.seg)); });
    $$('.chainmap .co', root).forEach(n => n.classList.toggle('dim', on.size > 0 && !on.has(n.dataset.segment)));
    $$('.chainmap .segtitle', root).forEach(n => n.classList.toggle('sel', on.has(n.dataset.seg)));
  }
  /* ---------------------------------------------------------------- 3D 剖析圖（Three.js）
     Andy 拍板「先試試看 three.js」。四條硬性驗收都在這裡兌現：
       可以轉、點零件會亮並帶出台股、標籤是 DOM、WebGL 不能用就退回 SVG。
     three.js 是動態載入的，只有真的按下 3D 才付那 670KB。*/
  let view3d = null;                 // 目前掛著的 3D 場景（沒有就是 null）

  function dispose3D() { if (view3d) { try { view3d.dispose(); } catch (e) { /* 忽略 */ } view3d = null; } }

  function wire3D(el, chainId, hooks) {
    const hk = hooks || {};
    const onSeg = hk.onSeg || (() => { /* 沒接就不做事 */ });
    const sync = hk.sync || (() => { /* 沒接就不做事 */ });
    const btn = $('#dg3d', el), rst = $('#dgReset', el), note = $('#dg3dNote', el);
    const svg = $('#prodDiagram', el), host = $('#prod3d', el);
    if (!btn || !host) return;
    const R = window.Rack3D;
    if (!R || !R.hasScene(chainId)) return;         // 這條鏈還沒有 3D 場景 → 維持平面圖
    if (!R.supported()) {                            // WebGL 不能用 → 連鈕都不出現，安靜退回 SVG
      note.hidden = false;
      note.textContent = '這台裝置不支援 WebGL，改用平面剖析圖（內容一樣）。';
      return;
    }
    btn.hidden = false;
    const setMode = async (on) => {
      try { localStorage.setItem('tw.dg3d', on ? '1' : '0'); } catch (e) { /* 忽略 */ }
      btn.classList.toggle('cyan', on);
      btn.textContent = on ? '3D 立體 ✓' : '3D 立體';
      rst.hidden = !on;
      svg.hidden = on; host.hidden = !on;
      if (!on) { dispose3D(); note.hidden = true; sync(); return; }
      note.hidden = false;
      note.textContent = '載入 3D 中…';
      dispose3D();
      host.innerHTML = '';
      let v = null;
      try {
        v = await R.mount(host, chainId, {
          color: segColor,
          onSeg: (seg) => onSeg(seg),
        });
      } catch (err) {
        // 起不來就要講出來，不能停在「載入 3D 中…」讓人以為當掉了
        note.textContent = '3D 起不來（' + (err && err.message ? err.message : err) + '），已退回平面剖析圖。';
        svg.hidden = false; host.hidden = true; rst.hidden = true; return;
      }
      if (!v) { note.textContent = '3D 起不來，已退回平面剖析圖。'; svg.hidden = false; host.hidden = true; rst.hidden = true; return; }
      view3d = v;
      note.textContent = `${v.sub}　·　拖曳轉視角、滾輪拉近拉遠、點零件看供應商`;
      sync();
    };
    btn.onclick = () => setMode(host.hidden);
    rst.onclick = () => { if (view3d) view3d.reset(); };
    let want = false;
    try { want = localStorage.getItem('tw.dg3d') === '1'; } catch (e) { /* 忽略 */ }
    setMode(want);
  }

  function wireDiagram(root, onSeg) { $$('#prodDiagram [data-seg]', root).forEach(n => { n.onclick = (e) => { e.stopPropagation(); onSeg(n.dataset.seg); }; }); }

  // ---------------------------------------------------------------- 分層關聯圖（SVG）
  function drawChainMap(host, sc, chainId, im, handlers) {
    if (!host) return;
    const segs = chainSegments(sc, chainId);
    const layers = [...new Set(segs.map(s => s.layer))].sort((a, b) => a - b);
    const cos = sc.companies.filter(c => segs.some(s => s.id === c.segment));
    const priceOf = {}; (im ? im.chains.flatMap(c => c.groups).concat(im.industries || []) : []).forEach(g => (g.members || []).forEach(m => { priceOf[m.code] = m; }));
    const colW = 178, cardH = 36, gapY = 8, padX = 14, padY = 36, colGap = 30;
    const bySeg = {}; cos.forEach(c => (bySeg[c.segment] = bySeg[c.segment] || []).push(c));
    const cols = layers.map(Lr => segs.filter(s => s.layer === Lr));
    let maxH = 0; const pos = {};
    cols.forEach((col, ci) => { let y = padY; col.forEach(s => { const list = bySeg[s.id] || []; pos[s.id] = { x: padX + ci * (colW + colGap), y, list }; y += 24 + list.length * (cardH + gapY) + 18; }); maxH = Math.max(maxH, y); });
    const W = padX * 2 + cols.length * (colW + colGap) - colGap, H = Math.max(maxH, 300);
    const coPos = {};
    let nodes = '';
    segs.forEach(s => { const p = pos[s.id]; if (!p) return; const col = segColor(s.id);
      nodes += `<g class="segtitle" data-seg="${s.id}" style="--c:${col}"><rect x="${p.x}" y="${p.y - 20}" width="${colW}" height="20" rx="5" fill="${col}" fill-opacity=".14"/><circle cx="${p.x + 10}" cy="${p.y - 10}" r="3.5" fill="${col}"/><text class="seg-title" x="${p.x + 19}" y="${p.y - 6}" fill="${col}">${A.fmt.esc(s.name)}</text></g>`;
      if (!p.list.length) nodes += `<text class="sub" x="${p.x + 6}" y="${p.y + 16}" fill="#6f7ea3">（台股無直接對應）</text>`;
      p.list.forEach((c, i) => { const y = p.y + 4 + i * (cardH + gapY); coPos[c.id] = { x: p.x, y, w: colW, h: cardH }; const m = c.tw_code ? priceOf[c.tw_code] : null; const chg = m ? m.chg_pct : null;
        nodes += `<g class="co ${c.foreign || !c.tw_code ? 'foreign' : ''} ${state.code && c.tw_code === state.code ? 'sel' : ''}" data-id="${c.id}" data-segment="${c.segment}" data-code="${c.tw_code || ''}" style="--c:${col}"><rect x="${p.x}" y="${y}" width="${colW}" height="${cardH}" rx="7"/><rect x="${p.x}" y="${y}" width="4" height="${cardH}" rx="2" fill="${col}"/><text x="${p.x + 12}" y="${y + 15}">${A.fmt.esc(c.name.length > 13 ? c.name.slice(0, 12) + '…' : c.name)}${c.tw_code ? ` <tspan class="sub">${c.tw_code}</tspan>` : ' <tspan class="sub">外商</tspan>'}</text><text class="sub" x="${p.x + 12}" y="${y + 29}">${m ? `${A.fmt.n(m.close)} <tspan fill="${A.upDown(chg)}">${A.fmt.pct(chg)}</tspan>` : A.fmt.esc((c.tech || []).slice(0, 2).join(' · '))}</text></g>`; }); });
    let edges = '';
    sc.edges.forEach(e => { const a = coPos[e.from], b = coPos[e.to]; if (!a || !b) return; const x1 = a.x + a.w, y1 = a.y + a.h / 2, x2 = b.x, y2 = b.y + b.h / 2; const mx = (x1 + x2) / 2; edges += `<path class="edge" data-from="${e.from}" data-to="${e.to}" d="M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}" stroke-width="${0.8 + (e.strength || 1) * 0.5}"><title>${A.fmt.esc(e.item || e.rel || '')}</title></path>`; });
    host.innerHTML = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;min-width:${Math.min(W, 860)}px;max-width:${Math.round(W * 1.25)}px;display:block">${edges}${nodes}</svg>`;
    $$('.co', host).forEach(n => { n.onmouseenter = () => { $$('.edge', host).forEach(e => { const on = e.dataset.from === n.dataset.id || e.dataset.to === n.dataset.id; e.classList.toggle('hi', on); e.classList.toggle('dim', !on); }); }; n.onmouseleave = () => $$('.edge', host).forEach(e => e.classList.remove('hi', 'dim')); n.onclick = () => { const co = cos.find(c => c.id === n.dataset.id); showCompany(co, sc); if (handlers.onSelect && co.tw_code) handlers.onSelect(co); }; });
    $$('.segtitle', host).forEach(n => n.onclick = () => handlers.onSegment && handlers.onSegment(n.dataset.seg));
    if (state.code) { const sel = $(`.co[data-code="${state.code}"]`, host); if (sel && sel.scrollIntoView) setTimeout(() => sel.scrollIntoView({ block: 'nearest', inline: 'center', behavior: 'smooth' }), 50); }
  }
  function showCompany(co, sc) {
    if (!co) return; let box = $('#coBox'); if (!box) { box = document.createElement('div'); box.id = 'coBox'; box.className = 'card'; box.style.cssText = 'position:fixed;right:24px;bottom:24px;width:360px;max-width:calc(100vw - 32px);z-index:60'; document.body.appendChild(box); }
    const shares = (co.share || []).map(s => `<li>${A.fmt.esc(s.metric || s.product || '市占')}：<b class="mono">${s.value_pct != null ? s.value_pct + '%' : (s.value || '—')}</b> <small class="muted">${s.as_of || ''} · ${s.source || ''}${s.stale ? ' · 已過期' : ''}</small></li>`).join('');
    const peers = sc.companies.filter(c => c.segment === co.segment && c.id !== co.id);
    box.innerHTML = `<div class="row spread"><h3>${A.fmt.esc(co.name)} ${co.tw_code ? `<span class="mono cyan">${co.tw_code}</span>` : '<span class="pill">外商</span>'}</h3><button class="close" onclick="document.getElementById('coBox').remove()">×</button></div>
      <div class="sub"><span style="color:${segColor(co.segment)}">● ${A.fmt.esc(segName(sc, co.segment))}</span>${(co.groups || []).length ? ' · ' + co.groups.map(gn => A.L.groupByName(gn)).join(' ') : ''}</div>
      ${(co.tech || []).length ? `<div class="row" style="gap:6px;margin:6px 0">${co.tech.map(t => `<span class="pill">${A.fmt.esc(t)}</span>`).join('')}</div>` : ''}
      ${shares ? `<ul style="margin:6px 0;padding-left:18px;font-size:13.5px">${shares}</ul>` : '<div class="note">尚無市占資料（supply_chain.yaml 待補）</div>'}
      ${co.growth ? `<div class="note">成長：${A.fmt.esc(co.growth)}</div>` : ''}${(co.risks || []).length ? `<div class="note">風險：${co.risks.map(A.fmt.esc).join('；')}</div>` : ''}
      ${peers.length ? `<div class="row" style="gap:4px 8px;margin-top:8px;font-size:12.5px"><span class="muted">同環節</span>${peers.map(p => p.tw_code ? A.L.stock(p.tw_code, p.name, { cls: 'sm' }) : `<span class="muted">${A.fmt.esc(p.name)}</span>`).join('')}</div>` : ''}
      ${co.tw_code ? `<button class="btn primary" style="margin-top:8px" onclick="goStock('${co.tw_code}')">看個股頁 →</button>` : ''}`;
  }

  /* ============================================================ 簡版個股頁
     Andy：「不可以出現沒有資訊狀況」。
     完整個股頁（stock/<代號>.json）偶爾會缺 —— 新上市、歷史價量還不到 60 根日線，
     或像預覽版那樣只帶了一部分個股頁。以前這種情況給的是一句「還沒產生」＋一個返回鍵，
     那就是一個死路。現在改成：用手上「已經載入的」資料重新組一頁真的有東西的頁面 ——
     stocks.json 有今日價量、groups_detail 有法人與技術分、fundamental 有估值與營收、
     news 有相關新聞、族群有同業名單。看得到的資訊只會少，不會沒有。 */
  async function renderStockLite(code, im, sc, gd) {
    const [stocks, fund, news, th] = await Promise.all([
      A.load('stocks', { fallback: [] }), A.load('fundamental', { fallback: [] }),
      A.load('news', { fallback: [] }), A.load('themes', { fallback: null }),
    ]);
    const known = (stocks || []).find(x => x.code === code) || (A.L.all || []).find(x => x.code === code);
    if (!known) {
      $('#indChain').innerHTML = '';
      crumbs([{ label: '產業地圖', href: '#industry' }, { label: code }]);
      $('#stockPage').innerHTML = `<div class="card"><div class="empty">
        找不到代號 ${A.fmt.esc(code)}。個股頁只做上市櫃普通股，權證／期貨／指數不列入。<br><br>${A.L.back()}</div></div>`;
      return;
    }
    // 同族群成員表裡有法人、技術分、判定 —— 這些是完整頁才會算的，但族群頁已經算好了
    let mem = null, sibs = [];
    Object.entries(gd || {}).forEach(([gid, g]) => {
      (g.members || []).forEach(mm => {
        if (mm.code === code) { mem = { ...mm, group_id: gid, group_name: g.group_name }; }
      });
    });
    const gid = (mem && mem.group_id) || known.group_id;
    if (gid && gd && gd[gid]) {
      sibs = (gd[gid].members || []).filter(x => x.code !== code)
        .sort((a, b) => (b.turnover || 0) - (a.turnover || 0)).slice(0, 24);
    }
    const fu = (fund || []).find(x => x.code === code) || {};
    const ns = (news || []).filter(n => String(n.codes || '').split(',').includes(code)).slice(0, 8);

    state.chain = chainOfGroup(im, gid) || 'industry'; state.group = null;
    const chainName = CHAIN_NAME[state.chain] || state.chain;
    crumbs([{ label: '產業地圖', href: '#industry' },
            { label: chainName, href: '#industry/' + state.chain },
            { label: `${known.name || ''} ${code}` }]);
    renderChainStrip(im, sc, { code, name: known.name, group_id: gid, groups: known.group ? [known.group] : [] });

    const n = A.fmt.n, pct = A.fmt.pct;
    // 有值才放進去 —— 寧可少一格，也不要放一格「—」在那裡佔位
    const kv = (pairs) => {
      const out = pairs.filter(p => p[1] !== null && p[1] !== undefined && p[1] !== '');
      return out.length ? `<div class="kvs">${out.map(p => `<div class="k"><div class="l">${p[0]}</div><div class="v${p[2] || ''}">${p[1]}</div></div>`).join('')}</div>` : '';
    };
    // 法人是「股」，全站一律換算成張再顯示
    const lot = (v) => (v === null || v === undefined ? null : `<span class="${A.fmt.cls(v)}">${A.fmt.lot(v / 1000)}</span>`);
    const close = known.close != null ? known.close : (mem && mem.close);
    const chg = known.chg_pct != null ? known.chg_pct : (mem && mem.chg_pct);
    const today = kv([
      ['收盤', close != null ? `<span class="num">${n(close)}</span>` : null],
      ['漲跌', chg != null ? `<span class="${A.fmt.cls(chg)}">${pct(chg, 2)}</span>` : null],
      ['成交值', known.turnover != null ? A.fmt.yi(known.turnover) : null],
      ['外資', mem ? lot(mem.foreign) : null],
      ['投信', mem ? lot(mem.trust) : null],
      ['自營', mem ? lot(mem.dealer) : null],
      ['技術分', mem && mem.tech_score != null ? n(mem.tech_score, 0) : null],
      ['目前判定', mem && mem.verdict ? A.fmt.esc(mem.verdict) : null],
    ]);
    const val = kv([
      ['本益比', fu.pe != null ? n(fu.pe, 1) : null],
      ['同族群中位', fu.group_median != null ? n(fu.group_median, 1) : null],
      ['股價淨值比', fu.pb != null ? n(fu.pb, 2) : null],
      ['ROE', fu.roe != null ? n(fu.roe, 1) + '%' : null],
      ['毛利率', fu.gross_margin != null ? n(fu.gross_margin, 1) + '%' : null],
      ['市值', fu.market_cap != null ? A.fmt.yi(fu.market_cap) : null],
      ['TTM EPS', fu.ttm_eps != null ? n(fu.ttm_eps, 2) : null],
      ['營收 YoY', fu.rev_yoy != null ? `<span class="${A.fmt.cls(fu.rev_yoy)}">${pct(fu.rev_yoy, 1)}</span>` : null],
      ['營收 MoM', fu.rev_mom != null ? `<span class="${A.fmt.cls(fu.rev_mom)}">${pct(fu.rev_mom, 1)}</span>` : null],
      ['營運動能', fu.momentum_score != null ? n(fu.momentum_score, 0) : null],
    ]);
    const themeLinks = A.L.themesOf(code);
    const why = known.tier === 'thin'
      ? '這一檔的歷史價量還在回補（完整頁需要至少 60 根日線才算得出指標、SMC 與評分）。'
      : '這一版的資料包沒有帶到這一檔的完整個股頁。';
    const card = (title, sub, body) => body
      ? `<div class="card" style="margin-top:16px"><h3>${title}${sub ? ` <small>${sub}</small>` : ''}</h3>${body}</div>` : '';

    $('#stockPage').innerHTML = `
      <div class="card" style="margin-top:16px">
        <div class="row spread">
          <div><h2>${A.fmt.esc(known.name || '')} <span class="mono cyan">${code}</span>
            <small class="muted" style="font-size:13px">${known.market === 'TPEX' ? '上櫃' : known.market === 'TWSE' ? '上市' : (known.market || '')}</small></h2>
            <div class="row" style="gap:6px 12px;margin-top:4px;font-size:13.5px">
              <span class="muted">產業鏈</span>${A.L.chain(state.chain, chainName)}
              <span class="muted">族群</span>${gid ? A.L.group(gid, (mem && mem.group_name) || known.group) : '—'}
              ${themeLinks ? `<span class="muted">題材</span>${themeLinks}` : ''}</div>
            <div class="row" style="margin-top:6px">
              <span class="num" style="font-size:30px;font-weight:700">${close != null ? n(close) : '—'}</span>
              ${chg != null ? `<span class="num ${A.fmt.cls(chg)}" style="font-size:18px">${pct(chg, 2)}</span>` : ''}
              <span class="pill amber">簡版個股頁</span></div></div>
        </div>
        <div class="banner on" style="margin:12px 0 0">
          <b>這一頁是簡版。</b>${why}
          下面是這一檔<b>現在就查得到的完整資訊</b>：今日價量與法人、估值與營收、相關新聞、同族群比較。
          完整版（K 線、多週期 SMC、五年營收獲利、除權息、籌碼）會在<b>下一次盤後更新</b>出現。
        </div>
      </div>
      ${card('今日盤後', '價量與三大法人', today)}
      ${card('估值與營收', '同族群才比本益比', val)}
      ${card('相關新聞', `${ns.length} 則`, ns.length ? `<div class="cards">${ns.map(x => `<div class="scard">
          <a href="${A.fmt.esc(x.url || '#')}" target="_blank" rel="noopener">${A.fmt.esc(x.title || '')}</a>
          <div class="r"><span class="muted">${A.fmt.esc(x.date || '')}</span><span class="muted">${A.fmt.esc(x.source || '')}</span></div></div>`).join('')}</div>` : '')}
      ${card('同族群其他個股', '點進去看完整頁', sibs.length ? `<div class="sibs">${sibs.map(x =>
          `${A.L.stock(x.code, x.name)}<span class="chg ${A.fmt.cls(x.chg_pct)}">${pct(x.chg_pct, 1)}</span>`).join('')}</div>` : '')}
      <div class="card" style="margin-top:16px"><div class="note">資料更新到 <b>${A.fmt.esc((A.D.meta && A.D.meta.data_date) || '—')}</b>（每個交易日盤後自動更新）。${A.L.back()}</div></div>`;
  }

  // ================================================================ Level 2：個股頁
  async function renderStock(code, im, sc, gd) {
    show(false, true, true);
    const pg = await A.load('stock/' + code, { fallback: null });
    if (!pg) { await renderStockLite(code, im, sc, gd); return; }
    const m = pg.meta, s = pg.summary || {};
    // 上方產業鏈（同步高亮）
    state.chain = chainOfGroup(im, m.group_id) || 'industry'; state.group = null;
    const chainName = CHAIN_NAME[state.chain] || state.chain;
    crumbs([{ label: '產業地圖', href: '#industry' }, { label: chainName, href: '#industry/' + state.chain }, { label: `${m.name} ${m.code}` }]);
    renderChainStrip(im, sc, m);
    // 個股主體
    const el = $('#stockPage');
    const v = pg.verdict || {}; const gradeCls = v.grade || 'W';
    const groupLinks = (m.groups || []).map(gn => A.L.groupByName(gn)).join(' ');
    const themeLinks = A.L.themesOf(m.code);
    const TIER = { full: ['分 K 完整', 'cyan', '15 分／1 小時／4 小時分 K 每日盤後由 Yahoo 補入'],
                   daily: ['日線以上', '', '這檔不在分 K 名單（族群成分股＋成交值前段才抓），日線／週線／月線與多週期判讀都正常'],
                   thin: ['資料回補中', 'amber', '歷史價量還在回補，目前只有最近幾天的日線'] };
    const tier = TIER[(m.tier || 'daily')] || TIER.daily;
    el.innerHTML = `
      <div class="card" style="margin-top:16px">
        <div class="row spread">
          <div><h2>${A.fmt.esc(m.name)} <span class="mono cyan">${m.code}</span> <small class="muted" style="font-size:13px">${m.market || ''}</small></h2>
            <div class="row" style="gap:6px 12px;margin-top:4px;font-size:13.5px"><span class="muted">產業鏈</span>${A.L.chain(state.chain, chainName)}<span class="muted">族群</span>${groupLinks || '—'}${themeLinks ? `<span class="muted">題材</span>${themeLinks}` : ''}</div>
            <div class="row" style="margin-top:6px"><span class="num" style="font-size:30px;font-weight:700" id="pxNow" data-live="close" data-lc="${m.code}">${A.fmt.n(s.close)}</span><span class="num ${A.fmt.cls(s.chg_pct)}" style="font-size:18px" data-live="chg" data-lc="${m.code}">${A.fmt.pct(s.chg_pct, 2)}</span><span class="pill">技術分 ${A.fmt.n(s.tech_score, 0)}</span><span class="pill">本益比 ${s.pe ? A.fmt.n(s.pe, 1) : '—'}</span><span class="pill">同業分位 ${s.pe_percentile != null ? A.fmt.n(s.pe_percentile, 0) + '%' : '—'}</span><span class="pill">營收 YoY ${A.fmt.pct(s.rev_yoy)}</span><span class="pill ${tier[1]}" title="${A.fmt.esc(tier[2])}">${tier[0]}</span></div></div>
          <div class="verdict" style="min-width:280px;max-width:520px"><h3><span class="grade ${gradeCls}">${v.grade ? v.grade + ' ' : ''}${v.verdict || '—'}</span> <small>停損 ${A.fmt.n(v.stop)} · 目標 ${A.fmt.n(v.tp1)} · 風報 ${v.rr != null ? A.fmt.n(v.rr, 1) : '—'}</small></h3><ul>${(v.reasons || []).slice(0, 3).map(r => `<li>${A.fmt.esc(r)}</li>`).join('')}</ul>${v.risk_text ? `<div class="note" style="margin-top:6px">風險：${A.fmt.esc(v.risk_text)}</div>` : ''}</div>
        </div>
        <div class="toolbar" style="margin-top:14px">
          <div class="seg" id="tfSeg">${tfButtons()}</div>
          <button class="btn small" id="tfAdd" title="自訂時間週期">＋</button>
          <div id="indChips" class="row" style="gap:6px"></div>
          <div class="sp"></div>
          <button class="btn small" id="cfgBtn" title="圖表設定：線寬、均線、顏色">⚙ 設定</button>
          <button class="btn small" id="mtfBtn">${state.mtfMode ? '單一週期' : '四週期同看'}</button>
          <button class="btn small" id="wideBtn" title="收起右側事件欄，把整個視窗的寬度讓給 K 線圖">⤢ 寬版</button>
          <button class="iconbtn" id="fitBtn" title="重設縮放（雙擊價格軸也可以）" aria-label="重設縮放">
            <svg viewBox="0 0 18 18"><rect x="2.5" y="2.5" width="13" height="13" rx="2"/><path d="M6,9 H12 M9,6 V12"/></svg></button>
        </div>
        <div class="note livenote" id="liveNote" hidden></div>
        <div class="chartwrap">
          <div class="drawbar" id="drawBar"></div>
          <div id="chartHost"></div>
        </div>
        <div class="cfgpop" id="cfgPop" hidden></div>
        ${pg.note ? `<div class="banner on" style="margin:10px 0 0">${A.fmt.esc(pg.note)}</div>` : ''}
        <div class="note" style="margin-top:6px">滑鼠在圖內滾輪＝時間縮放；在右側價格軸上滾輪或拖曳＝調整上下寬度（K 棒跟著變）；雙擊價格軸還原。
          <b>成交量／KD／MACD／RSI 之間的分隔線可以上下拖，把哪一格拉大都行，拉完會記住；按右上角「重設縮放」還原。</b>分 K 來源 Yahoo Finance（1 小時可回溯 2 年、15 分 60 天），盤後更新。
          <b>週期鈕上被劃掉的＝這檔沒有那個週期的資料</b>，滑鼠移上去會說原因。</div>
        <div class="note" style="margin-top:4px">資料更新到 <b>${A.fmt.esc(pg.as_of || (A.D.meta && A.D.meta.data_date) || '—')}</b>（每個交易日盤後自動更新一次：價量、法人、籌碼、營收／財報、新聞）。</div>
      </div>
      <div class="card" style="margin-top:16px" id="mtfCard"></div>
      <div class="subtabs" id="stockTabs">${[['overview', '總覽'], ['revenue', '營收'], ['profit', '獲利'], ['dividend', '除權息'], ['chips', '籌碼'], ['basics', '基本資料'], ['news', '新聞 / 券商']].map(t => `<button data-t="${t[0]}" class="${state.tab === t[0] ? 'on' : ''}">${t[1]}</button>`).join('')}</div>
      <div id="stockTab"></div>`;
    setupChart(pg);
    renderMtf(pg);
    $$('#stockTabs button').forEach(b => b.onclick = () => { $$('#stockTabs button').forEach(x => x.classList.toggle('on', x === b)); state.tab = b.dataset.t; renderTab(pg, state.tab); });
    renderTab(pg, state.tab);
  }

  // 個股頁上方：產業鏈 › 族群 › 同族群公司（可直接切換）＋ 可收合的剖析圖與關聯圖
  function renderChainStrip(im, sc, m) {
    const el = $('#indChain'); const cid = state.chain;
    const ch = chainData(im, cid);
    const hasDiagram = HAS_DIAGRAM(cid);
    if (!ch) { el.innerHTML = ''; return; }
    const g = ch.groups.find(x => x.id === m.group_id) || (im.industries || []).find(x => x.id === m.group_id);
    const sibs = g ? (g.members || []).slice().sort((a, b) => (b.turnover || 0) - (a.turnover || 0)) : [];
    const co = sc ? sc.companies.find(c => c.tw_code === m.code) : null;
    const segs = chainSegments(sc, cid);
    let open = false; try { open = localStorage.getItem('tw.chainOpen') === '1'; } catch (e) { /* 忽略 */ }
    el.innerHTML = `<div class="card tight">
      <div class="row spread"><div class="row" style="gap:8px"><b>${A.L.chain(cid, ch.name)}</b><span class="muted">›</span>${g ? A.L.group(g.id, g.name) : A.fmt.esc(m.group || '')}${co ? `<span class="muted">›</span><span class="pill" style="border-color:${segColor(co.segment)};color:${segColor(co.segment)}">● ${A.fmt.esc(segName(sc, co.segment))}</span>` : ''}</div>
        <div class="row" style="gap:8px">${hasDiagram ? `<button class="btn small" id="chainToggle">${open ? '收合產業鏈圖 ▴' : '展開產業鏈圖 ▾'}</button>` : ''}${A.L.back()}</div></div>
      ${sibs.length ? `<div class="sibs" id="sibs"><span class="muted" style="flex:none;font-size:12px;align-self:center">同族群</span>${sibs.map(x => `<a class="lk ${x.code === m.code ? 'cur' : ''}" href="#stock/${x.code}">${A.fmt.esc(x.name)}<span class="code">${x.code}</span><span class="chg ${A.fmt.cls(x.chg_pct)}">${A.fmt.pct(x.chg_pct)}</span></a>`).join('')}</div>` : ''}
      ${!hasDiagram ? `<div class="row" style="margin-top:8px;gap:6px">${ch.groups.map(x => `<span class="pill ${x.id === m.group_id ? 'cyan' : ''}" style="cursor:pointer" onclick="location.hash='#industry/group/${x.id}'"><i class="gdot" style="--c:${A.L.gcolor[x.id] || '#8ea0c4'}"></i>${A.fmt.esc(x.name)} <span class="${A.fmt.cls(x.chg_pct)}">${A.fmt.pct(x.chg_pct)}</span></span>`).join('')}</div>` : ''}
      ${hasDiagram ? `<div id="chainBody" style="${open ? '' : 'display:none'};margin-top:10px">
        <div class="segchips">${segs.map(s => `<span class="segchip ${co && co.segment === s.id ? 'sel' : ''}" data-seg="${s.id}" style="--c:${segColor(s.id)}" title="看這個環節的供應商"><i></i>${A.fmt.esc(s.name)}</span>`).join('')}</div>
        <div id="prodDiagram" class="dgwrap" style="margin-top:10px;max-width:1080px">${window.Diagrams[cid]()}</div><div class="chainmap" id="chainMap" style="margin-top:10px;max-height:380px"></div></div>` : ''}
    </div>`;
    const cur = $('#sibs a.cur', el); if (cur && cur.scrollIntoView) setTimeout(() => cur.scrollIntoView({ block: 'nearest', inline: 'center' }), 30);
    if (hasDiagram && sc) {
      const tog = $('#chainToggle', el); tog.onclick = () => { const b = $('#chainBody', el); const isOpen = b.style.display !== 'none'; b.style.display = isOpen ? 'none' : ''; tog.textContent = isOpen ? '展開產業鏈圖 ▾' : '收合產業鏈圖 ▴'; try { localStorage.setItem('tw.chainOpen', isOpen ? '0' : '1'); } catch (e) { /* 忽略 */ } };
      paintDiagram($('#prodDiagram', el));
      // 剖析圖不加縮放：Andy 明講「產業與個股 剖析圖不用新增縮放功能」（本來就可以左右滑）
      drawChainMap($('#chainMap', el), sc, cid, im, { onSelect: (c2) => { if (c2.tw_code) A.goStock(c2.tw_code); }, onSegment: (seg) => { location.hash = `#industry/${cid}/${seg}`; } });
      highlightSegments(el, co ? [co.segment] : [], co ? segColor(co.segment) : null);
      wireDiagram(el, (seg) => { location.hash = `#industry/${cid}/${seg}`; });
      $$('.segchip', el).forEach(c => c.onclick = () => { location.hash = `#industry/${cid}/${c.dataset.seg}`; });
      try { if (localStorage.getItem('tw.dganim') === '0') $('#prodDiagram', el).classList.add('noanim'); } catch (e) { /* 忽略 */ }
    }
  }

  // ---------------------------------------------------------------- K 線面板
  const DEFAULT_CFG = { ma: [5, 20, 60, 120], maColor: [], maWidth: [], lineWidth: 1,
    boll: null, vol: true, volma: 20, kd: { n: 9, m1: 3, m2: 3 }, macd: { f: 12, s: 26, g: 9 },
    rsi: null, smc: true, marks: true, lines: true, tfs: null,
    // 每個指標的顏色／線寬／透明度；zone 是 SMC 供需區的填色濃度與框線
    st: {}, zone: null,
    // K 棒寬度（Lightweight Charts 的 barSpacing）；預設比函式庫的 7 寬，Andy 要「default 先長一點」
    bar: 11 };
  // 設定面板要列出來的指標樣式（key、標題、幾個顏色、顏色的名字）
  const STYLE_ROWS = [
    ['boll', 'BOLL 通道', ['c'], ['線']],
    ['vol', '成交量', ['c', 'c2'], ['漲', '跌']],
    ['kd', 'KD', ['c', 'c2'], ['K', 'D']],
    ['macd', 'MACD', ['c', 'c2'], ['DIF', 'MACD']],
    ['rsi', 'RSI', ['c'], ['線']],
  ];
  const STYLE_DEF = {
    boll: { c: '#b39dff' }, vol: { c: '#ff4d6d', c2: '#2ee59d', o: 55 },
    kd: { c: '#3ee0ff', c2: '#ffd166' }, macd: { c: '#3ee0ff', c2: '#ffd166' }, rsi: { c: '#c3ff5b' },
  };
  // 內建週期＋使用者自訂的（nD = N 日合成、nW = N 週合成；分 K 只能用抓得到的那幾檔）
  /* 5秒 / 1分 / 5分 是「當天即時」的，資料不在 payload 裡，而是 livek.js 現場合成的
     （證交所沒有個股的分時檔，所以是 Yahoo 補早盤 ＋ 即時報價每 5 秒補尾巴）。 */
  const TF_BUILTIN = ['5s', '1m', '5m', '15m', '60m', '240m', '1d', '1w', '1M'];
  const TF_NAME = { '5s': '5秒', '1m': '1分', '5m': '5分', '15m': '15分', '60m': '1時', '240m': '4時', '1d': '日', '1w': '週', '1M': '月' };
  const LIVE_TF = ['5s', '1m', '5m'];
  const isLiveTf = (tf) => LIVE_TF.indexOf(tf) >= 0;
  const tfLabel = (tf) => TF_NAME[tf] || (/^\d+D$/.test(tf) ? tf.replace('D', ' 日') : /^\d+W$/.test(tf) ? tf.replace('W', ' 週') : tf);
  function tfList() { const c = (state.cfg && state.cfg.tfs) || []; return TF_BUILTIN.concat(c); }
  function tfButtons() { return tfList().map(tf => `<button data-tf="${tf}" class="${tf === state.tf ? 'on' : ''}">${tfLabel(tf)}</button>`).join(''); }
  /* 哪些週期這檔真的有資料：沒有的直接在按鈕上劃掉並寫清楚原因。
     Andy 回報「K 線圖 1 日以下都不見」—— 其實按鈕在，是那檔沒有分 K，
     但按下去才看到一行字，等於要用猜的。現在光看按鈕就知道哪些看得到。 */
  function markTf(pg) {
    $$('#tfSeg button').forEach(b => {
      const tf = b.dataset.tf;
      if (isLiveTf(tf)) {
        // 即時週期永遠可以按：盤中會邊看邊長，盤後顯示今天收集到的
        b.classList.remove('off');
        b.classList.add('livetf');
        b.title = '當天即時（Yahoo 補早盤 ＋ 證交所報價每 5 秒補尾巴）';
        return;
      }
      const has = (barsFor(pg, tf) || []).length >= 5;
      b.classList.toggle('off', !has);
      b.title = has ? '' : (/m$/.test(tf)
        ? `${pg.meta.name} 沒有分 K：分 K 每天只跟 Yahoo 抓族群成分股與成交值前 400 名，這檔不在名單內。日線／週線／月線正常。`
        : '這個週期的資料還在回補');
    });
  }
  function loadCfg() { try { const s = localStorage.getItem('tw.kcfg'); if (s) return Object.assign({}, DEFAULT_CFG, JSON.parse(s)); } catch (e) { /* 忽略 */ } return Object.assign({}, DEFAULT_CFG); }
  function saveCfg(c) { try { localStorage.setItem('tw.kcfg', JSON.stringify(c)); } catch (e) { /* 忽略 */ } }
  // N 根合成一根（自訂 N 日 / N 週用）
  function groupBars(bars, n) {
    const out = [];
    for (let i = 0; i < bars.length; i += n) {
      const g = bars.slice(i, i + n); if (!g.length) continue;
      out.push([g[g.length - 1][0], g[0][1], Math.max(...g.map(b => b[2])), Math.min(...g.map(b => b[3])),
        g[g.length - 1][4], g.reduce((s, b) => s + (b[5] || 0), 0)]);
    }
    return out;
  }
  /* 資料湖的日線最後一根是「上一個交易日」—— 今天那一筆要等 15:30 那輪管線才寫進去。
     Andy 2026-09-15：「為何個股會是 9/14，而非 9/15呢?…我的目的就是要即時訊息」。
     報價本身就帶著今天的開高低收與累計量，所以盤中就把它接成「今天這根還沒收的日 K」。
     週線／月線是從日線合成的，所以接在日線上，週月線也會跟著長出今天。
     管線晚上把正式資料寫進來之後，日期一樣就直接覆蓋掉，不會變成兩根。 */
  function withToday(daily) {
    const t = window.LiveK && window.LiveK.todayBar ? window.LiveK.todayBar() : null;
    if (!t || !daily || !daily.length) return daily;
    const out = daily.slice();
    const lastDate = String(out[out.length - 1][0]);
    if (t[0] < lastDate) return daily;                 // 報價比資料湖還舊（假日），不動
    if (t[0] === lastDate) out[out.length - 1] = t;    // 同一天 → 用比較新的報價蓋掉
    else out.push(t);
    return out;
  }

  function barsFor(pg, tf) {
    // 即時週期不吃 payload，直接跟 livek.js 拿（它自己在收）
    if (isLiveTf(tf)) return (window.LiveK ? window.LiveK.bars(tf) : []) || [];
    const daily = withToday(pg.daily && pg.daily.length ? pg.daily : pg.ohlcv);
    if (tf === '1d') return daily;
    if (tf === '1w') return KUtil.resampleDaily(daily, 'W');
    if (tf === '1M') return KUtil.resampleDaily(daily, 'M');
    let m = /^(\d+)D$/.exec(tf); if (m) return groupBars(daily || [], +m[1]);
    m = /^(\d+)W$/.exec(tf); if (m) return groupBars(KUtil.resampleDaily(daily || [], 'W'), +m[1]);
    return (pg.intraday && pg.intraday[tf]) || [];
  }
  function zonesFor(pg, tf) { const t = pg.mtf && pg.mtf.tf && pg.mtf.tf[tf]; if (t) return [...t.demand, ...t.supply].map(z => ({ ...z, tf: t.label })); if (tf === '1d' && pg.verdict) return [...(pg.verdict.demand || []).map(z => ({ ...z, kind: 'demand' })), ...(pg.verdict.supply || []).map(z => ({ ...z, kind: 'supply' }))]; return []; }
  function marksFor(pg, tf) { const t = pg.mtf && pg.mtf.tf && pg.mtf.tf[tf]; if (t) return t.marks; if (tf === '1d') return pg.marks || {}; return {}; }

  function setupChart(pg) {
    state.cfg = state.cfg || loadCfg();
    /* 即時分 K：切到這一檔就開始收，每收到一筆就重畫（畫面位置由 setBars(..., keepView) 保住）。
       Andy 2026-09-15：「當我點擊一般股票時也能做到這樣的效果」 */
    stopLive();
    if (window.LiveK) {
      window.LiveK.attach(pg.meta.code, pg.meta.market);
      liveOff = window.LiveK.onUpdate(() => {
        if (!document.getElementById('lwc')) return;      // 四週期同看或已離開，不用畫
        // 即時週期固然要重畫；日／週／月因為最後一根是「今天還沒收的」，也要跟著跳
        if (isLiveTf(state.tf) || ['1d', '1w', '1M'].indexOf(state.tf) >= 0) apply();
      });
    }
    const host = $('#chartHost');
    const chips = $('#indChips');
    const cfg = state.cfg;
    const chipDefs = [
      { k: 'ma', label: 'MA', on: () => !!cfg.ma, params: () => cfg.ma ? [{ key: 'ma', val: cfg.ma.join(','), w: 90 }] : [], toggle: () => { cfg.ma = cfg.ma ? null : [5, 20, 60, 120]; }, set: (v) => { cfg.ma = v.split(/[,，\s]+/).map(Number).filter(n => n > 0).slice(0, 6); }, color: '#ffd166' },
      { k: 'boll', label: 'BOLL', on: () => !!cfg.boll, params: () => cfg.boll ? [{ key: 'n', val: cfg.boll.n, w: 34 }, { key: 'k', val: cfg.boll.k, w: 30 }] : [], toggle: () => { cfg.boll = cfg.boll ? null : { n: 20, k: 2 }; }, set: (v, key) => { cfg.boll[key] = +v; }, color: '#8b7bff' },
      { k: 'vol', label: '成交量', on: () => !!cfg.vol, params: () => [], toggle: () => { cfg.vol = !cfg.vol; }, color: '#8ea0c4' },
      { k: 'kd', label: 'KD', on: () => !!cfg.kd, params: () => cfg.kd ? [{ key: 'n', val: cfg.kd.n, w: 30 }, { key: 'm1', val: cfg.kd.m1, w: 26 }, { key: 'm2', val: cfg.kd.m2, w: 26 }] : [], toggle: () => { cfg.kd = cfg.kd ? null : { n: 9, m1: 3, m2: 3 }; }, set: (v, key) => { cfg.kd[key] = +v; }, color: '#ffd166' },
      { k: 'macd', label: 'MACD', on: () => !!cfg.macd, params: () => cfg.macd ? [{ key: 'f', val: cfg.macd.f, w: 30 }, { key: 's', val: cfg.macd.s, w: 30 }, { key: 'g', val: cfg.macd.g, w: 26 }] : [], toggle: () => { cfg.macd = cfg.macd ? null : { f: 12, s: 26, g: 9 }; }, set: (v, key) => { cfg.macd[key] = +v; }, color: '#3ee0ff' },
      { k: 'rsi', label: 'RSI', on: () => !!cfg.rsi, params: () => cfg.rsi ? [{ key: 'n', val: cfg.rsi.n, w: 30 }] : [], toggle: () => { cfg.rsi = cfg.rsi ? null : { n: 14 }; }, set: (v) => { cfg.rsi.n = +v; }, color: '#c3ff5b' },
      { k: 'smc', label: 'SMC 區間', on: () => !!cfg.smc, params: () => [], toggle: () => { cfg.smc = !cfg.smc; }, color: '#2ee59d' },
      { k: 'marks', label: 'BOS/CHoCH', on: () => !!cfg.marks, params: () => [], toggle: () => { cfg.marks = !cfg.marks; }, color: '#ff8fab' },
      // 背離要有 MACD 才算得出來（DIF 是比較基準）
      { k: 'macdDiv', label: 'MACD 背離', on: () => cfg.macdDiv !== false && !!cfg.macd, params: () => [], toggle: () => { const nowOn = cfg.macdDiv !== false && !!cfg.macd; if (nowOn) { cfg.macdDiv = false; } else { cfg.macdDiv = true; if (!cfg.macd) cfg.macd = { f: 12, s: 26, g: 9 }; } }, color: '#ffd166' },
      { k: 'lines', label: '停損/目標', on: () => !!cfg.lines, params: () => [], toggle: () => { cfg.lines = !cfg.lines; }, color: '#ffb454' },
      /* 本益比河流（Andy 2026-09-15：「上方也多一個選項新增河流圖」）：
         把下方那張河流圖的五條倍數線直接疊在 K 棒上，同一套倍數，兩邊對得起來。
         需要近四季 EPS，所以只有日／週／月線畫得出來（分 K 的日期對不到財報那條階梯）。*/
      { k: 'peRiver', label: '本益比河流', on: () => !!cfg.peRiver, params: () => [], toggle: () => { cfg.peRiver = !cfg.peRiver; }, color: '#b39dff' },
    ];
    const drawChips = () => {
      chips.innerHTML = chipDefs.map(c => `<span class="chip ${c.on() ? 'on' : ''}" data-k="${c.k}"><i style="background:${c.color}"></i>${c.label}${c.params().map(p => `<input data-k="${c.k}" data-p="${p.key}" value="${p.val}" style="width:${p.w}px" onclick="event.stopPropagation()">`).join('')}</span>`).join('');
      $$('.chip', chips).forEach(ch => ch.onclick = (e) => { if (e.target.tagName === 'INPUT') return; chipDefs.find(c => c.k === ch.dataset.k).toggle(); saveCfg(cfg); drawChips(); apply(); });
      $$('.chip input', chips).forEach(inp => inp.onchange = () => { chipDefs.find(c => c.k === inp.dataset.k).set(inp.value, inp.dataset.p); saveCfg(cfg); drawChips(); apply(); });
    };
    const build = () => {
      if (kchart) { kchart.destroy(); kchart = null; } miniCharts.forEach(c => c.destroy()); miniCharts = [];
      if (state.mtfMode) { host.innerHTML = `<div class="mtf-grid" id="mtfGrid"></div>`; buildMtfGrid(pg); return; }
      host.innerHTML = `<div id="lwc"><div class="legend-ov" id="legendOv"></div><div class="ohlcbox" id="ohlcBox" hidden></div></div>`;
      kchart = new KChart($('#lwc'), { tf: state.tf, onText: () => window.prompt('文字內容', '') });
      apply();
      enableDraw(pg);
    };
    const apply = () => {
      const box = $('#lwc'); if (!box) return;
      const bars = barsFor(pg, state.tf);
      const live = isLiveTf(state.tf);
      if (!bars || bars.length < (live ? 2 : 5)) {
        const why = live
          ? (window.LiveK ? window.LiveK.sourceNote(state.tf) : '即時層還沒載入')
          : pg.meta.tier === 'thin' ? (pg.note || '歷史價量還在回補')
          : /m$/.test(state.tf) ? '這檔沒有分 K（只有族群成分股與成交值前段會抓 Yahoo 分 K）；日線／週線／月線可以正常看'
          : '這個週期尚無資料';
        if (kchart) { kchart.destroy(); kchart = null; }
        box.innerHTML = `<div class="empty" style="height:100%">${A.fmt.esc(why)}</div>`;
        setLiveNote(live ? why : '');
        return;
      }
      setLiveNote(live && window.LiveK ? window.LiveK.sourceNote(state.tf) : '');
      // 上一個週期沒資料時圖被拆掉了，換回有資料的週期要重建（不重建的話會整張空白到重新整理為止）
      if (!kchart || !$('#legendOv')) {
        if (kchart) { kchart.destroy(); kchart = null; }
        box.innerHTML = '<div class="legend-ov" id="legendOv"></div><div class="ohlcbox" id="ohlcBox" hidden></div>';
        kchart = new KChart(box, { tf: state.tf, onText: () => window.prompt('文字內容', '') });
        enableDraw(pg);
      }
      // 即時更新（同一檔、同一個週期、圖還在）就保留目前的縮放與位置
      const keep = kchart._liveKey === pg.meta.code + '|' + state.tf;
      kchart._liveKey = pg.meta.code + '|' + state.tf;
      kchart.setBars(bars, state.tf, keep);
      /* 本益比倍數線：算好之後掛在 chart 上（不要塞進 cfg —— cfg 會被寫進 localStorage，
         幾千筆數字存進去毫無意義）。applyIndicators 會自己去讀 this.peBands。*/
      kchart.peBands = cfg.peRiver ? peBandsForBars(peRiver(pg), bars) : null;
      kchart.applyIndicators(cfg);
      if (kchart.setBarSpacing) kchart.setBarSpacing(cfg.bar || 11);
      kchart.setZones(cfg.smc && !live ? zonesFor(pg, state.tf) : [], cfg.zone || undefined);
      kchart.setMarkers(cfg.marks && !live ? marksFor(pg, state.tf) : {});
      const v = pg.verdict || {};
      kchart.setPriceLines(cfg.lines && state.tf === '1d' ? [{ price: v.stop, title: '停損', color: '#ffb454' }, { price: v.tp1, title: '目標 1', color: '#3ee0ff' }, { price: v.tp2, title: '目標 2', color: '#8b7bff' }] : []);
      const legend = $('#legendOv');
      const TFN = { '5s': '5 秒（即時）', '1m': '1 分（即時）', '5m': '5 分（即時）', '15m': '15 分', '60m': '1 小時', '240m': '4 小時', '1d': '日線', '1w': '週線', '1M': '月線' };
      kchart.setWatermark(`${pg.meta.name} ${pg.meta.code} · ${TFN[state.tf] || state.tf}`);
      const at = (arr, i) => (arr ? arr[i == null ? arr.length - 1 : i] : null);
      const show = (i, pt) => {
        const idx = i == null ? kchart.data.length - 1 : i; const d = kchart.data[idx]; if (!d) return; const prev = kchart.data[idx - 1]; const vals = kchart.values || {};
        showOhlcBox(d, prev, pt, state.tf);
        const chg = prev ? (d.close - prev.close) / prev.close * 100 : null; const amp = d.low ? (d.high - d.low) / d.low * 100 : null;
        const col = d.close >= d.open ? '#ff4d6d' : '#2ee59d';
        let s = `<b>${KUtil.fmtTime(d.time, state.tf)}</b>　開 ${A.fmt.n(d.open)}　高 ${A.fmt.n(d.high)}　低 ${A.fmt.n(d.low)}　收 <b style="color:${col}">${A.fmt.n(d.close)}</b>${chg != null ? ` <span style="color:${A.upDown(chg)}">${A.fmt.pct(chg, 2)}</span>` : ''}　振幅 ${amp != null ? A.fmt.n(amp, 1) + '%' : '—'}　量 ${A.fmt.lot(d.volume / 1000)}`;
        const parts = []; (cfg.ma || []).forEach((n, k) => { const m = at(vals['MA' + n], i); if (m != null) parts.push(`<span style="color:${KUtil.colors.ma[k % 6]}">MA${n} ${A.fmt.n(m)}</span>`); });
        if (vals.BOLL) { const u = at(vals.BOLL.up, i), lo = at(vals.BOLL.low, i); if (u != null) parts.push(`<span style="color:#b39dff">BOLL ${A.fmt.n(lo)} – ${A.fmt.n(u)}</span>`); }
        // 本益比倍數線：直接把「幾倍＝股價多少」寫在圖例上，不然圖上五條虛線看不出誰是誰
        if (vals.PE) {
          const bits = vals.PE.map(b => { const v = at(b.vals, i); return v == null ? null : `<span style="color:${b.color}">${b.mult}倍 ${A.fmt.n(v)}</span>`; }).filter(Boolean);
          if (bits.length) parts.push('本益比 ' + bits.join('　'));
        }
        legend.innerHTML = s + (parts.length ? '<br>' + parts.join('　') : '');
        const pl = {};
        if (cfg.vol) pl.vol = `成交量 <b>${A.fmt.lot(d.volume / 1000)}</b>${cfg.volma && at(vals.VOLMA, i) != null ? `　<span style="color:#ffd166">MA${cfg.volma} ${A.fmt.lot(at(vals.VOLMA, i) / 1000)}</span>` : ''}`;
        if (vals.KD) pl.kd = `KD(${cfg.kd.n},${cfg.kd.m1},${cfg.kd.m2})　<span style="color:${KUtil.colors.k}">K ${A.fmt.n(at(vals.KD.k, i), 1)}</span>　<span style="color:${KUtil.colors.d}">D ${A.fmt.n(at(vals.KD.d, i), 1)}</span>`;
        if (vals.MACD) pl.macd = `MACD(${cfg.macd.f},${cfg.macd.s},${cfg.macd.g})　<span style="color:${KUtil.colors.dif}">DIF ${A.fmt.n(at(vals.MACD.dif, i))}</span>　<span style="color:${KUtil.colors.dea}">MACD ${A.fmt.n(at(vals.MACD.dea, i))}</span>　OSC <span style="color:${A.upDown(at(vals.MACD.osc, i))}">${A.fmt.n(at(vals.MACD.osc, i))}</span>`;
        if (vals.RSI) pl.rsi = `RSI(${cfg.rsi.n})　<span style="color:${KUtil.colors.rsi}">${A.fmt.n(at(vals.RSI, i), 1)}</span>`;
        kchart.setPaneLabels(pl);
      };
      show(null, null); kchart.onCrosshair(show);
      /* 面板高度：拖完（滑鼠放開）就記下來，下次打開、換股票、換週期都沿用。
         Andy 2026-09-15：「下方MACD KD 成交量等範圍上下可以拉大」—— 拉得動只是第一步，
         拉完換一檔又縮回去等於白拉。 */
      if (!box._paneSave) {
        box._paneSave = true;
        box.addEventListener('pointerup', () => setTimeout(() => {
          if (!kchart || !kchart.paneHeights) return;
          const h = kchart.paneHeights();
          // 面板在還沒畫出來時 getHeight() 會回 0，那種讀數不能存（存了下次就把版面壓扁）
          if (!h || !h.main) return;
          if (Object.keys(h).some(k => k !== 'main' && !h[k])) return;
          const before = JSON.stringify(cfg.paneH || {});
          if (JSON.stringify(h) === before) return;
          cfg.paneH = h; saveCfg(cfg);
        }, 120));
      }
      // 手繪線是「每檔每週期一組」，換週期要換一組，不然會畫到上一個週期的檔案裡
      if (kchart.draw && kchart.draw.key !== `tw.draw.${pg.meta.code}.${state.tf}`) enableDraw(pg);
    };
    // ---- 時間週期（含自訂）
    const wireTf = () => $$('#tfSeg button').forEach(b => {
      b.onclick = () => { $$('#tfSeg button').forEach(x => x.classList.toggle('on', x === b)); state.tf = b.dataset.tf; if (state.mtfMode) build(); else apply(); };
      b.oncontextmenu = (e) => { // 自訂的週期按右鍵可以移除
        if (TF_BUILTIN.includes(b.dataset.tf)) return;
        e.preventDefault();
        cfg.tfs = (cfg.tfs || []).filter(t => t !== b.dataset.tf); saveCfg(cfg);
        if (state.tf === b.dataset.tf) state.tf = '1d';
        $('#tfSeg').innerHTML = tfButtons(); wireTf(); markTf(pg); build();
      };
    });
    wireTf(); markTf(pg);
    $('#tfAdd').onclick = () => {
      const pop = $('#cfgPop');
      pop.hidden = false;
      pop.innerHTML = `<div class="ttl">自訂時間週期</div>
        <div class="note">用日線合成，例如 3 日＝三根日線併一根；週線同理。輸入後按加入，按鈕上按右鍵可移除。</div>
        <div class="row" style="margin-top:8px"><input id="tfN" type="number" min="2" max="60" value="3" style="width:64px">
        <select id="tfU"><option value="D">日</option><option value="W">週</option></select>
        <button class="btn small primary" id="tfOk">加入</button><button class="btn small" id="tfNo">關閉</button></div>`;
      $('#tfOk').onclick = () => {
        const n = Math.max(2, Math.min(60, +$('#tfN').value || 3)), u = $('#tfU').value;
        const id = n + u;
        cfg.tfs = [...new Set([...(cfg.tfs || []), id])].slice(0, 6); saveCfg(cfg);
        state.tf = id; pop.hidden = true; $('#tfSeg').innerHTML = tfButtons(); wireTf(); markTf(pg); build();
      };
      $('#tfNo').onclick = () => { pop.hidden = true; };
    };

    // ---- 圖表設定：線寬、均線條數／週期／顏色／粗細
    $('#cfgBtn').onclick = () => {
      const pop = $('#cfgPop');
      if (!pop.hidden && pop.dataset.kind === 'style') { pop.hidden = true; return; }
      pop.hidden = false; pop.dataset.kind = 'style';
      const mas = cfg.ma || [];
      const zn = Object.assign({}, KUtil.ZONE_DEF, cfg.zone || {});
      pop.innerHTML = `<div class="ttl">圖表設定</div>
        <div class="frow"><label>整體線寬</label><input id="lw" type="range" min="1" max="4" step="1" value="${cfg.lineWidth || 1}"><span class="val" id="lwv">${cfg.lineWidth || 1}px</span></div>
        <div class="frow"><label>K 棒寬度</label><input id="bw" type="range" min="3" max="28" step="1" value="${cfg.bar || 11}"><span class="val" id="bwv">${cfg.bar || 11}px</span></div>
        <div class="ttl2">均線（最多 6 條）</div>
        <div id="maRows">${mas.map((n, i) => `<div class="frow marow" data-i="${i}">
          <input type="number" min="2" max="480" value="${n}" data-f="n" style="width:62px">
          <input type="color" value="${(cfg.maColor || [])[i] || KUtil.colors.ma[i % 6]}" data-f="c">
          <input type="range" min="1" max="4" step="1" value="${(cfg.maWidth || [])[i] || cfg.lineWidth || 1}" data-f="w" style="width:78px">
          <button class="btn small" data-f="del" title="移除這條">✕</button></div>`).join('')}</div>
        <div class="row" style="margin-top:6px"><button class="btn small" id="maAdd" ${mas.length >= 6 ? 'disabled' : ''}>＋ 新增均線</button></div>
        <div class="ttl2">指標樣式（顏色 · 線寬 · 透明度）</div>
        <div id="stRows">${STYLE_ROWS.map(([k, label, keys, names]) => {
          const v = Object.assign({ w: cfg.lineWidth || 1, o: 100 }, STYLE_DEF[k], (cfg.st || {})[k] || {});
          return `<div class="frow strow" data-k="${k}"><label>${label}</label>
            ${keys.map((ck, i) => `<span class="cwrap" title="${names[i]}"><input type="color" data-f="${ck}" value="${v[ck]}"><em>${names[i]}</em></span>`).join('')}
            <input type="range" min="1" max="4" step="1" data-f="w" value="${v.w}" title="線寬" style="width:64px">
            <input type="range" min="15" max="100" step="5" data-f="o" value="${v.o}" title="透明度" style="width:78px">
            <span class="val" data-f="ov">${v.o}%</span></div>`;
        }).join('')}</div>
        <div class="ttl2">SMC 供需區</div>
        <div class="frow" id="zoneRow">
          <span class="cwrap" title="需求區"><input type="color" data-f="demand" value="${zn.demand}"><em>需求</em></span>
          <span class="cwrap" title="供給區"><input type="color" data-f="supply" value="${zn.supply}"><em>供給</em></span>
          <label style="margin-left:4px">填色</label><input type="range" min="0" max="45" step="1" data-f="fill" value="${zn.fill}" style="width:74px">
          <label>框線</label><input type="range" min="20" max="100" step="5" data-f="line" value="${zn.line}" style="width:66px">
          <input type="range" min="1" max="3" step="1" data-f="width" value="${zn.width}" title="框線粗細" style="width:54px">
          <label class="chk"><input type="checkbox" data-f="label" ${zn.label ? 'checked' : ''}>標籤</label>
        </div>
        <div class="row" style="margin-top:8px">
          <button class="btn small" id="cfgReset">回復預設</button><div class="sp"></div><button class="btn small primary" id="cfgClose">完成</button></div>`;
      const sync = () => {
        cfg.ma = []; cfg.maColor = []; cfg.maWidth = [];
        $$('#maRows .marow').forEach(r => {
          cfg.ma.push(+$('[data-f=n]', r).value || 20);
          cfg.maColor.push($('[data-f=c]', r).value);
          cfg.maWidth.push(+$('[data-f=w]', r).value || 1);
        });
        cfg.lineWidth = +$('#lw').value || 1;
        cfg.bar = +$('#bw').value || 11;
        cfg.st = {};
        $$('#stRows .strow').forEach(r => {
          const o = {};
          $$('input', r).forEach(i => { o[i.dataset.f] = i.type === 'color' ? i.value : +i.value; });
          const ov = $('[data-f=ov]', r); if (ov) ov.textContent = o.o + '%';
          cfg.st[r.dataset.k] = o;
        });
        const zr = $('#zoneRow');
        if (zr) { const z = {}; $$('input', zr).forEach(i => {
          z[i.dataset.f] = i.type === 'color' ? i.value : i.type === 'checkbox' ? i.checked : +i.value; });
          cfg.zone = z; }
        const add = $('#maAdd'); if (add) add.disabled = cfg.ma.length >= 6;   // 刪到剩 5 條要能再加回來
        saveCfg(cfg); drawChips(); apply();
      };
      $('#lw').oninput = () => {
        $('#lwv').textContent = $('#lw').value + 'px';
        $$('#maRows [data-f=w]').forEach(i => { i.value = $('#lw').value; });   // 整體線寬帶動每條均線
        sync();
      };
      $('#bw').oninput = () => { $('#bwv').textContent = $('#bw').value + 'px'; sync(); };
      const wireRows = () => $$('#maRows .marow').forEach(r => {
        $$('input', r).forEach(i => { i.oninput = sync; i.onchange = sync; });
        $('[data-f=del]', r).onclick = () => { r.remove(); sync(); };
      });
      wireRows();
      $$('#stRows .strow input, #zoneRow input').forEach(i => { i.oninput = sync; i.onchange = sync; });
      $('#maAdd').onclick = () => {
        const i = $$('#maRows .marow').length; if (i >= 6) return;
        const d = document.createElement('div'); d.className = 'frow marow';
        d.innerHTML = `<input type="number" min="2" max="480" value="10" data-f="n" style="width:62px">
          <input type="color" value="${KUtil.colors.ma[i % 6]}" data-f="c">
          <input type="range" min="1" max="4" step="1" value="1" data-f="w" style="width:78px">
          <button class="btn small" data-f="del" title="移除這條">✕</button>`;
        $('#maRows').appendChild(d); wireRows(); sync();
      };
      $('#cfgReset').onclick = () => { Object.assign(cfg, JSON.parse(JSON.stringify(DEFAULT_CFG))); saveCfg(cfg); pop.hidden = true; drawChips(); apply(); };
      $('#cfgClose').onclick = () => { pop.hidden = true; };
    };

    $('#mtfBtn').onclick = () => { state.mtfMode = !state.mtfMode; $('#mtfBtn').textContent = state.mtfMode ? '單一週期' : '四週期同看'; build(); };
    $('#fitBtn').onclick = () => {
      // 連同拖過的面板高度一起還原 —— 拉壞了要有一鍵回去的地方
      const c = state.cfg || loadCfg();
      if (c.paneH) { delete c.paneH; saveCfg(c); state.cfg = c; if (kchart) kchart.applyIndicators(c); }
      if (kchart) kchart.resetView(160);
    };
    /* 寬版（Andy：「K 線圖太小，版面需要擴大」）：把右側事件欄收起來，整個視窗寬度都給圖。
       Lightweight Charts 是 autoSize，容器一變寬它自己重畫；ECharts 的小圖要自己踢一下 resize。
       狀態存 localStorage，下次進個股頁維持同一個版面。 */
    const wideBtn = $('#wideBtn');
    const paintWide = () => {
      const on = document.body.classList.contains('kwide');
      wideBtn.classList.toggle('on', on);
      wideBtn.textContent = on ? '⤢ 寬版 ✓' : '⤢ 寬版';
      wideBtn.title = on ? '關掉寬版，把右側事件欄叫回來' : '收起右側事件欄，把整個視窗的寬度讓給 K 線圖';
    };
    wideBtn.onclick = () => {
      const on = document.body.classList.toggle('kwide');
      try { localStorage.setItem('tw.kwide', on ? '1' : '0'); } catch (e) { /* 忽略 */ }
      paintWide();
      setTimeout(() => { window.dispatchEvent(new Event('resize')); }, 60);
    };
    paintWide();
    drawChips(); drawBar(); build();
  }

  // 每檔每週期各存一份手繪線，換股或換週期就換一組
  function enableDraw(pg) {
    if (!kchart) return;
    const d = kchart.enableDrawing(`tw.draw.${pg.meta.code}.${state.tf}`);
    d.setTool(drawTool); d.setColor(drawColor); d.setWidth(drawW); d.setFill(drawFill);
  }

  /* 跟著游標走的資訊框（Andy 2026-09-15：「當游標移動過去時 需要在旁邊顯示開高收低 日期 時間等基本資訊」，
     附了一張看盤軟體的截圖當範例）。
     原本只有左上角那一條 legend，游標移到右半邊要一直回頭看，而且會蓋到 K 棒。
     這個框跟著十字線跑，靠近右邊界就自動翻到游標左側，不會被切掉。 */
  function showOhlcBox(d, prev, pt, tf) {
    const el = $('#ohlcBox'); if (!el) return;
    if (!pt) { el.hidden = true; return; }
    const chg = prev ? d.close - prev.close : null;
    const pct = prev && prev.close ? chg / prev.close * 100 : null;
    const cls = chg == null ? '' : chg > 0 ? 'up' : chg < 0 ? 'down' : '';
    const row = (k, v, c) => `<tr><th>${k}</th><td class="${c || ''}">${v}</td></tr>`;
    const amt = d.volume && d.close ? d.volume * d.close : null;   // 概算：量(股) × 收盤
    el.innerHTML = `<div class="oh">${A.fmt.esc(KUtil.fmtTime(d.time, tf))}</div>
      <table>
        ${row('開盤', A.fmt.n(d.open), d.open >= (prev ? prev.close : d.open) ? 'up' : 'down')}
        ${row('最高', A.fmt.n(d.high), 'up')}
        ${row('最低', A.fmt.n(d.low), 'down')}
        ${row('收盤', A.fmt.n(d.close), cls)}
        ${row('漲跌額', chg == null ? '—' : (chg > 0 ? '+' : '') + A.fmt.n(chg), cls)}
        ${row('漲跌幅', pct == null ? '—' : A.fmt.pct(pct, 2), cls)}
        ${row('成交量', A.fmt.lot(d.volume / 1000))}
        ${row('成交額', amt ? A.fmt.yi(amt) : '—')}
      </table>`;
    el.hidden = false;
    // 游標在左半邊就放右邊，反之亦然；上下也夾在圖內
    const host = el.parentElement;
    const W = host.clientWidth, H = host.clientHeight;
    const bw = el.offsetWidth || 150, bh = el.offsetHeight || 190;
    let x = pt.x + 16;
    if (x + bw > W - 8) x = pt.x - bw - 16;
    if (x < 6) x = 6;
    let y = pt.y - bh / 2;
    y = Math.max(6, Math.min(y, H - bh - 6));
    el.style.left = Math.round(x) + 'px';
    el.style.top = Math.round(y) + 'px';
  }

  // ---------------------------------------------------------------- 繪圖工具列（TradingView 式）
  // Andy 2026-09-15：「劃線需要有5種不同粗細可選，框格可選擇填滿或透明」
  const DRAW_WIDTHS = [1, 1.5, 2.5, 4, 6];
  const DW_KEY = 'tw.draw.style';
  let drawTool = 'cursor', drawColor = KUtil.DRAW_COLORS[0], drawW = 1.5, drawFill = false;
  try {
    const st = JSON.parse(localStorage.getItem(DW_KEY) || '{}');
    if (DRAW_WIDTHS.indexOf(+st.w) >= 0) drawW = +st.w;
    if (KUtil.DRAW_COLORS.indexOf(st.c) >= 0) drawColor = st.c;
    drawFill = !!st.fill;
  } catch (e) { /* 忽略 */ }
  const saveDrawStyle = () => {
    try { localStorage.setItem(DW_KEY, JSON.stringify({ w: drawW, c: drawColor, fill: drawFill })); }
    catch (e) { /* 忽略 */ }
  };

  function drawBar() {
    const bar = $('#drawBar'); if (!bar) return;
    bar.innerHTML = KUtil.DRAW_TOOLS.map(t =>
      `<button class="dtool ${t.k === drawTool ? 'on' : ''}" data-t="${t.k}" title="${t.label}${t.pts === 2 ? '（拉的時候按住 Shift ＝ 鎖水平／垂直）' : ''}">
         <svg viewBox="0 0 18 18"><path d="${t.icon}"/></svg></button>`).join('')
      + `<div class="dsep"></div>`
      + KUtil.DRAW_COLORS.map(c => `<button class="dcol ${c === drawColor ? 'on' : ''}" data-c="${c}" style="background:${c}" title="顏色"></button>`).join('')
      + `<div class="dsep"></div>`
      // 五段粗細：用線條本身的厚度表示，一眼看得出差別
      + DRAW_WIDTHS.map(w => `<button class="dw ${w === drawW ? 'on' : ''}" data-w="${w}" title="線寬 ${w}px">
           <span style="height:${w}px"></span></button>`).join('')
      + `<div class="dsep"></div>
         <button class="dtool dfill ${drawFill ? 'on' : ''}" data-a="fill" title="方框：${drawFill ? '填滿（點一下改成透明）' : '透明（點一下改成填滿）'}">
           <svg viewBox="0 0 18 18"><rect x="3" y="4" width="12" height="10" ${drawFill ? 'fill="currentColor"' : ''}/></svg></button>
         <button class="dtool" data-a="undo" title="復原上一筆"><svg viewBox="0 0 18 18"><path d="M7,4 L3,8 L7,12 M3,8 H11 a4,4 0 0 1 0,8 H8"/></svg></button>
         <button class="dtool" data-a="clear" title="清空這檔這個週期的所有線"><svg viewBox="0 0 18 18"><path d="M3,3 L15,15 M15,3 L3,15"/></svg></button>`;
    $$('.dtool[data-t]', bar).forEach(b => b.onclick = () => {
      drawTool = b.dataset.t; drawBar(); if (kchart && kchart.draw) kchart.draw.setTool(drawTool);
    });
    $$('.dcol', bar).forEach(b => b.onclick = () => {
      drawColor = b.dataset.c; saveDrawStyle(); drawBar(); if (kchart && kchart.draw) kchart.draw.setColor(drawColor);
    });
    $$('.dw', bar).forEach(b => b.onclick = () => {
      drawW = +b.dataset.w; saveDrawStyle(); drawBar(); if (kchart && kchart.draw) kchart.draw.setWidth(drawW);
    });
    $$('.dtool[data-a]', bar).forEach(b => b.onclick = () => {
      if (b.dataset.a === 'fill') {
        drawFill = !drawFill; saveDrawStyle(); drawBar();
        if (kchart && kchart.draw) kchart.draw.setFill(drawFill);
        return;
      }
      if (!kchart || !kchart.draw) return;
      if (b.dataset.a === 'undo') kchart.draw.undo(); else kchart.draw.clear();
    });
  }
  /* 四週期同看。
     Andy 2026-09-15：「同事看4個週期那頁需要新增可以切換週期，不然我看不到我要的」——
     以前四格是程式挑的（有 15 分就 15m/60m/240m/1d，沒有就取最後四個），使用者換不掉。
     現在每一格上面都有一個下拉選單，選什麼記在 `tw.kcfg` 的 mtfTfs 裡，換股票也還在。 */
  const MTF_LABEL = (tf) => ({ '5s': '5 秒（即時）', '1m': '1 分（即時）', '5m': '5 分（即時）',
    '15m': '15 分', '60m': '1 小時', '240m': '4 小時', '1d': '日線', '1w': '週線', '1M': '月線' })[tf] || tfLabel(tf);

  function mtfPick(pg) {
    const cfg = state.cfg || loadCfg();
    const saved = Array.isArray(cfg.mtfTfs) ? cfg.mtfTfs.filter(t => tfList().indexOf(t) >= 0) : null;
    if (saved && saved.length === 4) return saved;
    const have = (tf) => barsFor(pg, tf).length >= 20;
    const pref = ['15m', '60m', '240m', '1d', '1w', '1M'].filter(have);
    const pick = pref.length >= 4 ? (have('15m') ? ['15m', '60m', '240m', '1d'] : pref.slice(-4)) : pref;
    while (pick.length < 4 && pick.length) pick.push(pick[pick.length - 1]);
    return pick;
  }

  function buildMtfGrid(pg) {
    const cfg = state.cfg || loadCfg();
    const pick = mtfPick(pg);
    const grid = $('#mtfGrid');
    const opts = (cur) => tfList().map(tf =>
      `<option value="${tf}"${tf === cur ? ' selected' : ''}>${MTF_LABEL(tf)}</option>`).join('');
    grid.innerHTML = pick.map((tf, i) => {
      const t = pg.mtf && pg.mtf.tf && pg.mtf.tf[tf];
      return `<div class="mtf-cell"><div class="cap">
        <select class="mtfsel" data-i="${i}" title="換這一格要看的週期">${opts(tf)}</select>
        ${t ? `<span style="color:${t.trend > 0 ? '#ff4d6d' : t.trend < 0 ? '#2ee59d' : '#a9b6d6'}">${t.trend > 0 ? '多頭結構' : t.trend < 0 ? '空頭結構' : '盤整'}</span> · 均線${t.ma_align > 0 ? '多排' : t.ma_align < 0 ? '空排' : '糾結'}${t.rsi != null ? ' · RSI ' + t.rsi.toFixed(0) : ''}` : ''}
        </div><div class="cv" id="mini-${i}"></div></div>`;
    }).join('');
    pick.forEach((tf, i) => {
      const el = $('#mini-' + i);
      const bars = barsFor(pg, tf);
      if (!bars || bars.length < 2) {
        el.innerHTML = `<div class="empty" style="height:100%">${A.fmt.esc(isLiveTf(tf) ? '即時資料還在收集' : '這個週期尚無資料')}</div>`;
        return;
      }
      const c = new KChart(el, { mini: true, tf });
      c.setBars(bars, tf);
      c.applyIndicators({ ma: [20, 60], vol: false });
      if (!isLiveTf(tf)) { c.setZones(zonesFor(pg, tf)); c.setMarkers(marksFor(pg, tf)); }
      miniCharts.push(c);
    });
    $$('.mtfsel', grid).forEach(sel => sel.onchange = () => {
      const next = mtfPick(pg).slice();
      next[+sel.dataset.i] = sel.value;
      cfg.mtfTfs = next; saveCfg(cfg); state.cfg = cfg;
      miniCharts.forEach(c => { try { c.destroy(); } catch (e) { /* 忽略 */ } });
      miniCharts = [];
      buildMtfGrid(pg);
    });
  }
  function renderMtf(pg) {
    const el = $('#mtfCard'); const sm = pg.mtf && pg.mtf.summary; if (!sm || !sm.headline) { el.innerHTML = '<h3>多週期判讀</h3><div class="empty">資料不足</div>'; return; }
    const lv = sm.key_levels || {};
    const row = (z, kind) => `<div class="k" style="border-left:3px solid ${kind === 'support' ? '#2ee59d' : '#ff4d6d'}"><div class="l">${A.fmt.esc(z.label)} ${kind === 'support' ? '需求區' : '供給區'}</div><div class="v" style="font-size:15px">${z.low} – ${z.high}</div><div class="l">距現價 ${A.fmt.pct(z.dist_pct)} · 分數 ${z.score}</div></div>`;
    el.innerHTML = `<h3>多週期判讀 <small>大週期定方向（週 › 日），小週期找進場（4H › 1H › 15 分）</small></h3>
      <div class="lights">${(sm.tf_used || []).map(tf => { const t = sm.per_tf[tf]; return `<span class="light ${t.trend > 0 ? 'pos' : t.trend < 0 ? 'neg' : ''}">${({ '15m': '15 分', '60m': '1 小時', '240m': '4 小時', '1d': '日線', '1w': '週線', '1M': '月線' })[tf]} ${t.trend > 0 ? '多' : t.trend < 0 ? '空' : '盤整'}</span>`; }).join('')}</div>
      <div class="verdict" style="margin:10px 0"><h3 style="font-size:16px">${A.fmt.esc(sm.headline)}</h3><ul>${(sm.script || []).map(x => `<li>${A.fmt.esc(x)}</li>`).join('')}</ul></div>
      <div class="grid g2"><div><h4>支撐（由近到遠）</h4><div class="kvs" style="margin-top:6px">${(lv.support || []).map(z => row(z, 'support')).join('') || '<div class="note">沒有通過門檻的需求區</div>'}</div></div><div><h4>壓力（由近到遠）</h4><div class="kvs" style="margin-top:6px">${(lv.resistance || []).map(z => row(z, 'resistance')).join('') || '<div class="note">上方沒有通過門檻的供給區</div>'}</div></div></div>
      ${pg.verdict && pg.verdict.weekly_note ? `<div class="note" style="margin-top:8px">${A.fmt.esc(pg.verdict.weekly_note)}</div>` : ''}`;
  }

  // ---------------------------------------------------------------- 個股分頁
  function renderTab(pg, tab) {
    const el = $('#stockTab');
    ({ overview: tabOverview, revenue: tabRevenue, profit: tabProfit, dividend: tabDividend, chips: tabChips, basics: tabBasics, news: tabNews })[tab](pg, el);
    setTimeout(() => Object.values(A.charts).forEach(c => c && c.resize && c.resize()), 20);
  }
  function tabOverview(pg, el) {
    const f = pg.fundamental || {}, s = pg.summary || {}, iv = pg.inst_v3 || {}, dv = pg.dividends || {};
    const holders = pg.holders && pg.holders.length ? pg.holders[pg.holders.length - 1] : null; const hPrev = pg.holders && pg.holders.length > 4 ? pg.holders[pg.holders.length - 5] : null;
    const k = (l, v, cls) => `<div class="k"><div class="l">${l}</div><div class="v ${cls || ''}">${v}</div></div>`;
    el.innerHTML = `<div class="grid g3">
      <div class="card"><h3>基本面 <small>財報到 ${f.latest_period || '—'}</small></h3><div class="kvs" style="margin-top:8px">${k('近四季 EPS', f.ttm_eps != null ? A.fmt.n(f.ttm_eps) : '—')}${k('本益比', f.pe ? A.fmt.n(f.pe, 1) : '—')}${k('同業分位', f.percentile != null ? A.fmt.n(f.percentile, 0) + '%' : '<small>樣本不足</small>')}${k('ROE', f.roe != null ? A.fmt.n(f.roe, 1) + '%' : '—')}${k('毛利率', f.gross_margin != null ? A.fmt.n(f.gross_margin, 1) + '%' : '—')}${k('月營收 YoY', A.fmt.pct(f.rev_yoy), A.fmt.cls(f.rev_yoy))}${k('營運動能', f.momentum_score != null ? A.fmt.n(f.momentum_score, 0) + ' / 100' : '—')}${k('殖利率（近四次）', dv.yield_ttm != null ? A.fmt.n(dv.yield_ttm) + '%' : '—')}</div><div class="note" style="margin-top:8px">${f.group_name ? `同族群（${f.group_name}，n=${f.group_n}）本益比中位 ${f.group_median != null ? A.fmt.n(f.group_median, 1) : '—'}${f.vs_median != null ? '，本檔 ' + (f.vs_median > 0 ? '高於' : '低於') + '中位 ' + A.fmt.n(Math.abs(f.vs_median), 0) + '%' : ''}` : '本益比只在同族群內比較'}</div></div>
      <div class="card"><h3>籌碼快照</h3><div class="kvs" style="margin-top:8px">${k('法人 20 日', iv.sum20 != null ? A.fmt.lot(iv.sum20 / 1000) : '—', A.fmt.cls(iv.sum20))}${k('外資 20 日', iv.foreign20 != null ? A.fmt.lot(iv.foreign20 / 1000) : '—', A.fmt.cls(iv.foreign20))}${k('投信 20 日', iv.trust20 != null ? A.fmt.lot(iv.trust20 / 1000) : '—', A.fmt.cls(iv.trust20))}${k('千張大戶', holders ? A.fmt.n(holders[1], 1) + '%' : '—')}${k('大戶 4 週變化', holders && hPrev && holders[1] != null && hPrev[1] != null ? A.fmt.pct(holders[1] - hPrev[1], 2).replace('%', ' pp') : '—', holders && hPrev ? A.fmt.cls(holders[1] - hPrev[1]) : '')}${k('散戶（≤10 張）', holders ? A.fmt.n(holders[3], 1) + '%' : '—')}${k('融資餘額', pg.margin && pg.margin.length ? A.fmt.lot(pg.margin[pg.margin.length - 1][1]) : '—')}${k('量比', s.vol_ratio != null ? A.fmt.n(s.vol_ratio, 2) : '—')}</div><div class="note" style="margin-top:8px">「主力家數差」需券商分點資料（免費開放資料沒有）；這裡以集保千張大戶增減＋法人動向作替代指標。</div></div>
      <div class="card"><h3>技術面訊號</h3><div class="lights" style="margin-top:8px">${[['均線', s.ma_align > 0 ? '多頭排列' : s.ma_align < 0 ? '空頭排列' : '糾結', s.ma_align], ['結構', s.trend > 0 ? '多頭（HH/HL）' : s.trend < 0 ? '空頭（LH/LL）' : '盤整', s.trend], ['RSI', s.rsi != null ? s.rsi.toFixed(0) : '—', s.rsi > 50 ? 1 : -1], ['KD', s.k != null ? `K ${s.k.toFixed(0)} D ${s.d.toFixed(0)}` : '—', s.k > s.d ? 1 : -1], ['MACD OSC', s.osc != null ? s.osc.toFixed(2) : '—', s.osc > 0 ? 1 : -1], ['乖離 20', s.bias20 != null ? A.fmt.pct(s.bias20) : '—', 0], ['BOS', s.bos ? '出現' : '—', s.bos ? 1 : 0], ['CHoCH', s.choch ? '出現' : '—', s.choch ? 1 : 0], ['假跌破', s.sweep_low ? '出現' : '—', s.sweep_low ? 1 : 0]].map(x => `<span class="light ${x[2] > 0 ? 'pos' : x[2] < 0 ? 'neg' : ''}">${x[0]} ${x[1]}</span>`).join('')}</div>${pg.verdict && pg.verdict.invalidation ? `<div class="note" style="margin-top:8px">失效條件：${A.fmt.esc(pg.verdict.invalidation)}</div>` : ''}<div class="note" style="margin-top:6px">本頁為決策輔助，技術評分與規則權重尚未經 walk-forward 檢驗；不構成投資建議。</div></div></div>`;
  }
  function tabRevenue(pg, el) {
    const rv = pg.revenue || {}; const mo = rv.monthly || [];
    if (!mo.length) { el.innerHTML = '<div class="card"><div class="empty">尚無月營收歷史（回補進行中，每小時自動接續）</div></div>'; return; }
    const last = mo[mo.length - 1];
    el.innerHTML = `<div class="kvs" style="margin-bottom:12px"><div class="k"><div class="l">最新月份</div><div class="v">${last[0]}</div></div><div class="k"><div class="l">單月營收</div><div class="v">${A.fmt.yi(last[1])}</div></div><div class="k"><div class="l">YoY</div><div class="v ${A.fmt.cls(last[2])}">${A.fmt.pct(last[2])}</div></div><div class="k"><div class="l">MoM</div><div class="v ${A.fmt.cls(last[3])}">${A.fmt.pct(last[3])}</div></div><div class="k"><div class="l">累計營收</div><div class="v">${A.fmt.yi(last[4])}</div></div><div class="k"><div class="l">累計 YoY</div><div class="v ${A.fmt.cls(last[5])}">${A.fmt.pct(last[5])}</div></div></div>
      <div class="grid g2"><div class="card"><h3>每月營收與 YoY <small>近 ${Math.min(mo.length, 60)} 個月</small></h3><div id="revBar" class="chart"></div></div>
      <div class="card"><div class="row spread"><h3>年度走勢 <small>同月對比，看淡旺季</small></h3><div class="seg" id="revMode"><button data-v="m" class="on">單月</button><button data-v="c">累計</button></div></div><div id="revYear" class="chart"></div></div></div>
      <div class="card" style="margin-top:16px"><h3>月營收明細</h3><div class="tw" style="max-height:360px"><table><thead><tr><th class="l">月份</th><th>營收</th><th>YoY</th><th>MoM</th><th>累計</th><th>累計 YoY</th></tr></thead><tbody>${mo.slice().reverse().slice(0, 36).map(r => `<tr><td class="l mono">${r[0]}</td><td class="num">${A.fmt.yi(r[1])}</td><td class="num ${A.fmt.cls(r[2])}">${A.fmt.pct(r[2])}</td><td class="num ${A.fmt.cls(r[3])}">${A.fmt.pct(r[3])}</td><td class="num">${A.fmt.yi(r[4])}</td><td class="num ${A.fmt.cls(r[5])}">${A.fmt.pct(r[5])}</td></tr>`).join('')}</tbody></table></div></div>`;
    const t = mo.slice(-60);
    A.chart('revBar', { tooltip: { ...A.tip, trigger: 'axis', formatter: ps => `<b>${ps[0].axisValue}</b><br>` + ps.map(p => `${p.marker}${p.seriesName} ${p.seriesName === '營收' ? A.fmt.yi(p.value) : A.fmt.pct(p.value)}`).join('<br>') }, legend: { textStyle: { color: A.CH.ink2 }, top: 0 }, grid: { left: 60, right: 50, top: 30, bottom: 30 },
      xAxis: { ...A.axisStyle, type: 'category', data: t.map(r => r[0]), axisLabel: { color: A.CH.ink3, formatter: v => v.slice(2) } }, yAxis: [{ ...A.axisStyle, axisLabel: { formatter: v => A.fmt.yi(v) } }, { ...A.axisStyle, axisLabel: { formatter: '{value}%' }, splitLine: { show: false } }],
      series: [{ name: '營收', type: 'bar', data: t.map(r => r[1]), itemStyle: { color: 'rgba(62,224,255,.55)', borderRadius: [3, 3, 0, 0] } }, { name: 'YoY', type: 'line', yAxisIndex: 1, data: t.map(r => r[2]), smooth: .3, showSymbol: false, lineStyle: { color: '#ffb454', width: 2 } }] });
    const yr = (rv.yearly || []).slice(-6); let mode = 'm';
    const drawYear = () => { A.chart('revYear', { tooltip: { ...A.tip, trigger: 'axis', formatter: ps => `<b>${ps[0].axisValue} 月</b><br>` + ps.map(p => `${p.marker}${p.seriesName} ${A.fmt.yi(p.value)}`).join('<br>') }, legend: { textStyle: { color: A.CH.ink2 }, top: 0 }, grid: { left: 60, right: 20, top: 30, bottom: 30 }, xAxis: { ...A.axisStyle, type: 'category', data: Array.from({ length: 12 }, (_, i) => i + 1), axisLabel: { color: A.CH.ink3 } }, yAxis: { ...A.axisStyle, axisLabel: { formatter: v => A.fmt.yi(v) } },
      series: yr.map((y, i) => { let acc = 0; const d = Array.from({ length: 12 }, (_, m) => { const v = y.by_month[m + 1]; if (v == null) return null; if (mode === 'c') { acc += v; return acc; } return v; }); return { name: String(y.year), type: 'line', data: d, smooth: .2, symbolSize: 5, lineStyle: { width: i === yr.length - 1 ? 3 : 1.5, color: A.PALETTE[i] }, itemStyle: { color: A.PALETTE[i] } }; }) }); };
    $$('#revMode button').forEach(b => b.onclick = () => { $$('#revMode button').forEach(x => x.classList.toggle('on', x === b)); mode = b.dataset.v; drawYear(); });
    drawYear();
  }
  /* ------------------------------------------------------------ 本益比河流圖
     Andy 2026-09-15：「本益比這邊需要新增像是財報狗那樣的河流圖…兩種模式可切換」。

     做法跟 Goodinfo／財報狗一樣：把「近四季 EPS」當成一條**階梯函數**（每次財報公布才跳一次），
     再乘上幾個本益比倍數，就得到幾條「這個倍數對應的股價」。股價線穿梭在這幾條之間，
     它現在在哪一條帶，就是市場現在給的評價。

     倍數刻意**不寫死** 13/15/17/19/21/23：那是 Goodinfo 對台積電的預設值。
     金融股合理本益比十倍出頭、AI 股三十倍，寫死對大多數股票沒有意義。
     改用這一檔自己的歷史本益比分位數（10/30/50/70/90%），等於「跟自己比貴不貴」。*/
  const PE_ZONES = [            // 由下到上；顏色跟著「貴＝紅、便宜＝綠」（Andy 給的參考圖就是這個方向）
    { name: '低估', c: '#1c7a5a' }, { name: '價值', c: '#2ee59d' }, { name: '合理', c: '#c3ff5b' },
    { name: '觀望', c: '#ffd166' }, { name: '高估', c: '#ff8fab' }, { name: '警示', c: '#ff4d6d' },
  ];

  function peRiver(pg) {
    const hist = (pg.pe_history || []).filter(r => r && r.ttm_eps > 0 && r.from);
    const daily = (pg.daily && pg.daily.length ? pg.daily : pg.ohlcv) || [];
    if (hist.length < 4 || daily.length < 60) return null;
    const steps = hist.slice().sort((a, b) => (String(a.from) < String(b.from) ? -1 : 1));
    const dates = [], close = [], eps = [], pes = [];
    let si = 0;
    for (const b of daily) {
      const d = String(b[0]).slice(0, 10);
      if (d < String(steps[0].from)) continue;          // 第一份能算 TTM 的財報之前，沒有本益比可言
      while (si + 1 < steps.length && String(steps[si + 1].from) <= d) si++;
      const e = steps[si].ttm_eps, c = b[4];
      if (!(e > 0) || !(c > 0)) continue;
      dates.push(d); close.push(c); eps.push(e); pes.push(c / e);
    }
    if (dates.length < 60) return null;
    const sorted = pes.slice().sort((a, b) => a - b);
    const q = (p) => { const i = (sorted.length - 1) * p, lo = Math.floor(i), hi = Math.ceil(i);
      return sorted[lo] + (sorted[hi] - sorted[lo]) * (i - lo); };
    const mult = [q(0.1), q(0.3), q(0.5), q(0.7), q(0.9)].map(v => Math.round(v * 10) / 10);
    /* EPS 幾乎沒變、股價也沒動的股票，五個分位數會全部擠在一起，河流就變成一條線。
       撞在一起就強制拉開，至少看得出層次。*/
    for (let i = 1; i < mult.length; i++) {
      if (mult[i] <= mult[i - 1]) mult[i] = +(mult[i - 1] + Math.max(0.5, mult[0] * 0.08)).toFixed(1);
    }
    const bands = mult.map(m => eps.map(e => +(m * e).toFixed(2)));
    const lastClose = close[close.length - 1], lastEps = eps[eps.length - 1];
    const curPe = +(lastClose / lastEps).toFixed(1);
    let zi = 0; while (zi < mult.length && curPe >= mult[zi]) zi++;   // 0＝低估 … 5＝警示
    return { dates, close, eps, mult, bands, curPe, lastEps, zone: PE_ZONES[zi], zoneIdx: zi };
  }

  /** 把河流的倍數線對齊到 K 線圖的每一根（日期不同、根數也不同，所以要各自對表）。 */
  function peBandsForBars(r, bars) {
    if (!r || !bars || !bars.length) return null;
    const idx = new Map(); r.dates.forEach((d, i) => idx.set(d, i));
    const COL = ['#2ee59d', '#c3ff5b', '#ffd166', '#ff8fab', '#ff4d6d'];
    return r.mult.map((m, k) => ({
      mult: m, color: COL[k],
      vals: bars.map(b => {
        // 週線／月線的一根對應到那個區間的最後一個交易日；分 K 的日期在前 10 碼
        const i = idx.get(String(b[0]).slice(0, 10));
        return i == null ? null : +(m * r.eps[i]).toFixed(2);
      }),
    }));
  }

  /** 畫下方那張大圖。mode：'band' 色帶分區（fugle 那種）／'mult' 倍數線（Goodinfo 那種）。 */
  function drawPeRiver(id, r, mode) {
    if (!r) { A.empty(id, '需要至少四季連續財報，才算得出近四季 EPS'); return; }
    const maxClose = Math.max(...r.close), minClose = Math.min(...r.close);
    const lab = (i) => `${r.mult[i]} 倍`;
    let series, yMin, yMax;

    if (mode === 'mult') {
      /* 倍數線：只有線，線尾直接標倍數（Goodinfo 那張圖的讀法）。
         上下界只看收盤與五條線本身 —— 不要留色帶模式那塊「警示區」的空間，
         不然五條線會全部擠在畫面下半部。*/
      yMin = Math.floor(Math.min(minClose, Math.min(...r.bands[0])) * 0.95);
      yMax = Math.ceil(Math.max(maxClose, Math.max(...r.bands[4])) * 1.04);
      series = r.bands.map((b, i) => ({
        name: lab(i), type: 'line', data: b, symbol: 'none', silent: true, z: 2,
        lineStyle: { color: PE_ZONES[i + 1].c, width: 1.2, type: 'dashed' },
        endLabel: { show: true, color: PE_ZONES[i + 1].c, fontSize: 11, formatter: () => lab(i) },
        labelLayout: { moveOverlap: 'shiftY' },
      }));
    } else {
      // 色帶：堆疊面積，一層一個評價區間（fugle 那張圖的讀法）
      const top = r.bands[4].map(v => Math.max(v * 1.18, maxClose * 1.03));
      yMin = Math.floor(Math.min(minClose, Math.min(...r.bands[0])) * 0.93);
      yMax = Math.ceil(Math.max(maxClose, Math.max(...r.bands[4]) * 1.05) * 1.02);
      const diff = (a, b) => a.map((v, i) => +(v - b[i]).toFixed(2));
      const layers = [r.bands[0], diff(r.bands[1], r.bands[0]), diff(r.bands[2], r.bands[1]),
        diff(r.bands[3], r.bands[2]), diff(r.bands[4], r.bands[3]), diff(top, r.bands[4])];
      series = layers.map((d, i) => ({
        name: PE_ZONES[i].name, type: 'line', data: d, stack: 'pe', symbol: 'none', silent: true,
        lineStyle: { width: 0 }, areaStyle: { color: PE_ZONES[i].c, opacity: 0.3 }, z: 1,
        // 區間名稱標在自己那條帶的上緣、往下掛，讀起來就是「這一塊叫什麼」
        endLabel: { show: true, color: PE_ZONES[i].c, fontSize: 11, verticalAlign: 'top',
          offset: [4, 3], formatter: () => PE_ZONES[i].name },
        labelLayout: { moveOverlap: 'shiftY' },
      }));
    }
    series.push({ name: '收盤', type: 'line', data: r.close, symbol: 'none', z: 6, silent: true,
      lineStyle: { color: '#ffffff', width: 1.8 } });

    A.chart(id, {
      grid: { left: 56, right: 62, top: 24, bottom: 34 },
      tooltip: { ...A.tip, trigger: 'axis', formatter: (ps) => {
        const i = ps[0].dataIndex, c = r.close[i], e = r.eps[i], pe = e > 0 ? c / e : null;
        let z = 0; while (z < r.mult.length && pe >= r.mult[z]) z++;
        return `<b>${r.dates[i]}</b><br>收盤 ${A.fmt.n(c)}　近四季 EPS ${A.fmt.n(e)}<br>`
          + `本益比 <b>${pe != null ? A.fmt.n(pe, 1) : '—'}</b> 倍　`
          + `<span style="color:${PE_ZONES[z].c}">${PE_ZONES[z].name}</span><br>`
          + r.mult.map((m, k) => `${m} 倍 ＝ ${A.fmt.n(m * e)}`).join('　');
      } },
      xAxis: { ...A.axisStyle, type: 'category', data: r.dates, boundaryGap: false,
        axisLabel: { color: A.CH.ink3, formatter: (v) => String(v).slice(0, 7) } },
      yAxis: { ...A.axisStyle, min: yMin, max: yMax, axisLabel: { color: A.CH.ink3 } },
      series,
      // 一定要 notMerge：兩種模式的 series 數量與型態都不一樣，
      // 用合併的話切到「倍數線」時，上一次的色帶還留在圖上（實測就是這樣糊成一片）
    }, { notMerge: true });
  }

  function tabProfit(pg, el) {
    const q = (pg.profit || {}).quarters || []; const pe = pg.pe_history || [];
    if (!q.length) { el.innerHTML = '<div class="card"><div class="empty">尚無季報歷史（回補進行中）</div></div>'; return; }
    const last = q[q.length - 1];
    el.innerHTML = `<div class="kvs" style="margin-bottom:12px"><div class="k"><div class="l">最新季度</div><div class="v">${last[0]}</div></div><div class="k"><div class="l">單季 EPS</div><div class="v">${A.fmt.n(last[5])}</div></div><div class="k"><div class="l">年度累計 EPS</div><div class="v">${A.fmt.n(last[6])}</div></div><div class="k"><div class="l">EPS 年增（元）</div><div class="v ${A.fmt.cls(last[7])}">${last[7] != null ? (last[7] > 0 ? '+' : '') + A.fmt.n(last[7]) : '—'}</div></div><div class="k"><div class="l">毛利率</div><div class="v">${A.fmt.n(last[2], 1)}%</div></div><div class="k"><div class="l">營益率</div><div class="v">${A.fmt.n(last[3], 1)}%</div></div><div class="k"><div class="l">淨利率</div><div class="v">${A.fmt.n(last[4], 1)}%</div></div></div>
      <div class="card"><div class="row spread"><h3>本益比河流圖 <small>近四季 EPS × 各倍數 ＝ 那個倍數對應的股價；白線是實際收盤，它落在哪一條帶就是市場現在給的評價。倍數用這一檔自己的歷史分位數，不是寫死的 15/20/25 倍</small></h3>
        <div class="seg" id="peMode"><button data-v="band">色帶分區</button><button data-v="mult">倍數線</button></div></div>
        <div id="peChart" class="chart" style="height:340px"></div><div class="note" id="peNote"></div></div>
      <div class="grid g2" style="margin-top:16px"><div class="card"><h3>EPS 與三率 <small>單季；財報法規為季報，沒有每月</small></h3><div id="profitChart" class="chart"></div></div><div class="card"><h3>本益比（每季）<small>每季財報可用日後的收盤 / 近四季 EPS；虧損不算</small></h3><div id="peQ" class="chart"></div></div></div>
      <div class="card" style="margin-top:16px"><h3>季報明細</h3><div class="tw" style="max-height:360px"><table><thead><tr><th class="l">季度</th><th>營收</th><th>毛利率</th><th>營益率</th><th>淨利率</th><th>淨利</th><th>EPS</th><th>累計 EPS</th><th>EPS 年增</th></tr></thead><tbody>${q.slice().reverse().map(r => `<tr><td class="l mono">${r[0]}</td><td class="num">${A.fmt.yi(r[1])}</td><td class="num">${A.fmt.n(r[2], 1)}%</td><td class="num">${A.fmt.n(r[3], 1)}%</td><td class="num">${A.fmt.n(r[4], 1)}%</td><td class="num">${A.fmt.yi(r[8])}</td><td class="num">${A.fmt.n(r[5])}</td><td class="num">${A.fmt.n(r[6])}</td><td class="num ${A.fmt.cls(r[7])}">${r[7] != null ? (r[7] > 0 ? '+' : '') + A.fmt.n(r[7]) : '—'}</td></tr>`).join('')}</tbody></table></div></div>`;
    A.chart('profitChart', { tooltip: { ...A.tip, trigger: 'axis' }, legend: { textStyle: { color: A.CH.ink2 }, top: 0 }, grid: { left: 50, right: 50, top: 30, bottom: 30 },
      xAxis: { ...A.axisStyle, type: 'category', data: q.map(r => r[0]), axisLabel: { color: A.CH.ink3 } }, yAxis: [{ ...A.axisStyle, name: 'EPS' }, { ...A.axisStyle, axisLabel: { formatter: '{value}%' }, splitLine: { show: false } }],
      series: [{ name: 'EPS', type: 'bar', data: q.map(r => ({ value: r[5], itemStyle: { color: r[5] >= 0 ? 'rgba(255,77,109,.7)' : 'rgba(46,229,157,.7)', borderRadius: [3, 3, 0, 0] } })) }, { name: '毛利率', type: 'line', yAxisIndex: 1, data: q.map(r => r[2]), smooth: .3, showSymbol: false, lineStyle: { color: '#ffd166' } }, { name: '營益率', type: 'line', yAxisIndex: 1, data: q.map(r => r[3]), smooth: .3, showSymbol: false, lineStyle: { color: '#3ee0ff' } }, { name: '淨利率', type: 'line', yAxisIndex: 1, data: q.map(r => r[4]), smooth: .3, showSymbol: false, lineStyle: { color: '#8b7bff' } }] });
    if (pe.length) A.chart('peQ', { tooltip: { ...A.tip, trigger: 'axis', formatter: ps => { const r = pe[ps[0].dataIndex]; return `<b>${r.period}</b><br>本益比 ${r.pe ?? '—'}（區間 ${r.pe_low ?? '—'}–${r.pe_high ?? '—'}）<br>近四季 EPS ${r.ttm_eps}`; } }, grid: { left: 50, right: 20, top: 20, bottom: 30 }, xAxis: { ...A.axisStyle, type: 'category', data: pe.map(r => r.period), axisLabel: { color: A.CH.ink3 } }, yAxis: { ...A.axisStyle, scale: true },
      series: [{ name: '區間', type: 'line', data: pe.map(r => r.pe_low), lineStyle: { opacity: 0 }, stack: 'pe', showSymbol: false }, { name: '高低', type: 'line', data: pe.map(r => r.pe_high != null && r.pe_low != null ? r.pe_high - r.pe_low : null), lineStyle: { opacity: 0 }, stack: 'pe', areaStyle: { color: 'rgba(139,123,255,.2)' }, showSymbol: false }, { name: '本益比', type: 'line', data: pe.map(r => r.pe), lineStyle: { color: '#8b7bff', width: 2 }, symbolSize: 5 }] });
    else A.empty('peQ', '需要四季連續財報');

    // ---- 河流圖：兩種模式，選過就記住（換股票、重新整理都沿用）
    const river = peRiver(pg);
    let mode = 'band';
    try { const s = localStorage.getItem('tw.periver'); if (s === 'mult' || s === 'band') mode = s; } catch (e) { /* 忽略 */ }
    const note = $('#peNote', el);
    const paint = () => {
      $$('#peMode button', el).forEach(b => b.classList.toggle('on', b.dataset.v === mode));
      drawPeRiver('peChart', river, mode);
      if (note) {
        note.innerHTML = river
          ? `目前本益比 <b>${A.fmt.n(river.curPe, 1)}</b> 倍（近四季 EPS ${A.fmt.n(river.lastEps)} 元）`
            + `　·　落在 <b style="color:${river.zone.c}">${river.zone.name}</b> 區`
            + `　·　這一檔的歷史倍數帶：${river.mult.join(' / ')}`
            + `　·　${mode === 'band' ? '色帶分區：顏色越紅代表市場給的評價越高' : '倍數線：線尾標的是本益比倍數'}`
          : '這一檔還沒有四季連續財報（或近四季 EPS 是負的），河流圖算不出來。';
      }
    };
    $$('#peMode button', el).forEach(b => b.onclick = () => {
      mode = b.dataset.v;
      try { localStorage.setItem('tw.periver', mode); } catch (e) { /* 忽略 */ }
      paint();
    });
    paint();
  }
  function tabDividend(pg, el) {
    const dv = pg.dividends || {}; const ev = dv.events || [], rs = dv.results || [];
    if (!ev.length && !rs.length) { el.innerHTML = '<div class="card"><div class="empty">尚無除權息資料（回補進行中；ETF 暫不抓）</div></div>'; return; }
    const byYear = {}; ev.filter(e => e.kind === 'cash').forEach(e => { const y = e.fiscal_year || (e.period || '').slice(0, 4); byYear[y] = (byYear[y] || 0) + (e.amount || 0); });
    const years = Object.keys(byYear).sort();
    el.innerHTML = `<div class="kvs" style="margin-bottom:12px"><div class="k"><div class="l">近四次現金股利</div><div class="v">${dv.cash_ttm != null ? A.fmt.n(dv.cash_ttm) + ' 元' : '—'}</div></div><div class="k"><div class="l">殖利率</div><div class="v">${dv.yield_ttm != null ? A.fmt.n(dv.yield_ttm) + '%' : '—'}</div></div><div class="k"><div class="l">最近除息</div><div class="v" style="font-size:15px">${rs[0] ? rs[0].date : '—'}</div></div><div class="k"><div class="l">最近填息</div><div class="v">${rs[0] ? (rs[0].fill_days === -1 ? '一年未填' : rs[0].fill_days != null ? rs[0].fill_days + ' 天' : '進行中') : '—'}</div></div></div>
      <div class="grid g2"><div class="card"><h3>各年度現金股利 <small>依股利所屬年度</small></h3><div id="divBar" class="chart"></div></div>
      <div class="card"><h3>除權息紀錄 <small>填息天數＝除息後首次收在除息前收盤之上</small></h3><div class="tw" style="max-height:300px"><table><thead><tr><th class="l">除權息日</th><th class="l">類別</th><th>股利</th><th>前收盤</th><th>參考價</th><th>填息</th></tr></thead><tbody>${rs.map(r => `<tr><td class="l mono">${r.date}</td><td class="l">${r.kind}</td><td class="num">${A.fmt.n(r.dividend)}</td><td class="num">${A.fmt.n(r.before_price)}</td><td class="num">${A.fmt.n(r.reference_price)}</td><td class="num">${r.fill_days === -1 ? '<span class="down">未填</span>' : r.fill_days != null ? r.fill_days + ' 天' : '—'}</td></tr>`).join('') || '<tr><td colspan="6" class="l muted">—</td></tr>'}</tbody></table></div></div></div>
      <div class="card" style="margin-top:16px"><h3>股利公告</h3><div class="tw" style="max-height:320px"><table><thead><tr><th class="l">所屬期間</th><th class="l">類別</th><th>金額（元/股）</th><th class="l">公告日</th><th class="l">除權息日</th><th class="l">發放日</th></tr></thead><tbody>${ev.map(e => `<tr><td class="l">${A.fmt.esc(e.period)}</td><td class="l">${e.kind === 'cash' ? '現金' : '股票'}</td><td class="num">${A.fmt.n(e.amount, 3)}</td><td class="l mono">${e.announce_date || '—'}</td><td class="l mono">${e.ex_date || '—'}</td><td class="l mono">${e.payment_date || '—'}</td></tr>`).join('')}</tbody></table></div></div>`;
    if (years.length) A.chart('divBar', { tooltip: { ...A.tip }, grid: { left: 50, right: 20, top: 16, bottom: 30 }, xAxis: { ...A.axisStyle, type: 'category', data: years, axisLabel: { color: A.CH.ink3 } }, yAxis: { ...A.axisStyle }, series: [{ type: 'bar', data: years.map(y => +byYear[y].toFixed(3)), itemStyle: { color: '#ffb454', borderRadius: [3, 3, 0, 0] }, label: { show: true, position: 'top', color: '#e8eeff', fontFamily: 'JetBrains Mono', fontSize: 11 }, barWidth: '55%' }] }); else A.empty('divBar');
  }
  /* 籌碼頁：資料不夠就不要畫一張空圖。
     Andy：「若是籌碼下方無法抓取到數據，就把他替換其他方式，或是直接刪除」。
     規則：≥3 個點才畫線圖；只有 1~2 個點就改成把「現在的數字」直接列出來；
     一個點都沒有的那張卡片整張不出現。 */
  const CHIP_MIN = 3;
  function tabChips(pg, el) {
    const iv = (pg.inst_v3 || {}).daily || [], mg = pg.margin || [], ho = pg.holders || [];
    const cards = [];
    const card = (id, title, sub) => { cards.push(`<div class="card"><h3>${title} <small>${sub}</small></h3><div id="${id}" class="chart"></div></div>`); };
    const numCard = (title, sub, kvs, why) => cards.push(`<div class="card"><h3>${title} <small>${sub}</small></h3>
      <div class="kvs" style="margin-top:10px">${kvs}</div><div class="note" style="margin-top:8px">${why}</div></div>`);
    const k = (l, v, cls) => `<div class="k"><div class="l">${l}</div><div class="v ${cls || ''}">${v}</div></div>`;

    if (iv.length >= CHIP_MIN) card('instChart', '三大法人', '每日買賣超（張）與累計');
    else if (iv.length) { const r = iv[iv.length - 1];
      numCard('三大法人', `最新一筆 ${r[0]}`,
        k('外資', A.fmt.lot(r[1] / 1000), A.fmt.cls(r[1])) + k('投信', A.fmt.lot(r[2] / 1000), A.fmt.cls(r[2]))
        + k('自營', A.fmt.lot(r[3] / 1000), A.fmt.cls(r[3])),
        `法人歷史只回補到 ${iv.length} 天，畫成走勢圖看不出東西，先直接列數字；回補滿 ${CHIP_MIN} 天以上就會變成走勢圖。`); }

    if (mg.length >= CHIP_MIN) card('marginChart', '融資融券', '餘額（張）');
    else if (mg.length) { const r = mg[mg.length - 1];
      numCard('融資融券', `最新一筆 ${r[0]}`,
        k('融資餘額', A.fmt.lot(r[1])) + k('融券餘額', A.fmt.lot(r[2])),
        `融資券歷史只回補到 ${mg.length} 天，兩個點連起來是一條假的斜線，先直接列數字。`); }

    if (ho.length >= CHIP_MIN) {
      card('holderChart', '大戶 / 散戶持股', '集保每週：千張大戶、400–1000 張、10 張以下');
      card('holderCount', '股東人數', '人數下降＋大戶比例上升＝籌碼集中');
    } else if (ho.length) { const r = ho[ho.length - 1];
      numCard('集保股權分散', `最新一週 ${r[0]}`,
        k('千張大戶', A.fmt.n(r[1], 1) + '%') + k('400–1000 張', A.fmt.n(r[2], 1) + '%')
        + k('散戶 ≤10 張', A.fmt.n(r[3], 1) + '%') + k('股東人數', A.fmt.yi(r[4])),
        `集保是每週一筆，目前只累積到 ${ho.length} 週；滿 ${CHIP_MIN} 週就會變成走勢圖，看得出籌碼是在集中還是分散。`); }

    if (!cards.length) {
      el.innerHTML = `<div class="card"><div class="empty">這一檔的籌碼資料（法人、融資券、集保）還在回補，下一次盤後更新就會出現。</div></div>`;
      return;
    }
    el.innerHTML = cards.map((c, i) => (i % 2 === 0 ? `<div class="grid g2"${i ? ' style="margin-top:16px"' : ''}>` : '') + c + (i % 2 === 1 || i === cards.length - 1 ? '</div>' : '')).join('')
      + `<div class="note" style="margin-top:10px">主力（券商分點家數差）需付費資料，尚未提供；以千張大戶週變化與法人連續買賣作替代。</div>`;

    if (iv.length >= CHIP_MIN) A.chart('instChart', { tooltip: { ...A.tip, trigger: 'axis', formatter: ps => `<b>${ps[0].axisValue}</b><br>` + ps.map(p => `${p.marker}${p.seriesName} ${A.fmt.lot(p.value / 1000)}`).join('<br>') }, legend: { textStyle: { color: A.CH.ink2 }, top: 0 }, grid: { left: 60, right: 60, top: 30, bottom: 30 }, xAxis: { ...A.axisStyle, type: 'category', data: iv.map(r => r[0]), axisLabel: { color: A.CH.ink3, formatter: v => v.slice(5) } }, yAxis: [{ ...A.axisStyle, axisLabel: { formatter: v => A.fmt.lot(v / 1000) } }, { ...A.axisStyle, axisLabel: { formatter: v => A.fmt.lot(v / 1000) }, splitLine: { show: false } }],
      series: [{ name: '外資', type: 'bar', stack: 'i', data: iv.map(r => r[1]), itemStyle: { color: '#3ee0ff' } }, { name: '投信', type: 'bar', stack: 'i', data: iv.map(r => r[2]), itemStyle: { color: '#ffb454' } }, { name: '自營', type: 'bar', stack: 'i', data: iv.map(r => r[3]), itemStyle: { color: '#8b7bff' } }, { name: '累計', type: 'line', yAxisIndex: 1, data: iv.map(r => r[4]), showSymbol: false, lineStyle: { color: '#ff8fab', width: 2 } }] });
    if (mg.length >= CHIP_MIN) A.chart('marginChart', { tooltip: { ...A.tip, trigger: 'axis' }, legend: { textStyle: { color: A.CH.ink2 }, top: 0 }, grid: { left: 60, right: 60, top: 30, bottom: 30 }, xAxis: { ...A.axisStyle, type: 'category', data: mg.map(r => r[0]), axisLabel: { color: A.CH.ink3, formatter: v => v.slice(5) } }, yAxis: [{ ...A.axisStyle, scale: true }, { ...A.axisStyle, scale: true, splitLine: { show: false } }],
      series: [{ name: '融資餘額', type: 'line', data: mg.map(r => r[1]), showSymbol: false, areaStyle: { color: 'rgba(255,77,109,.12)' }, lineStyle: { color: '#ff4d6d', width: 2 } }, { name: '融券餘額', type: 'line', yAxisIndex: 1, data: mg.map(r => r[2]), showSymbol: false, lineStyle: { color: '#2ee59d', width: 1.5 } }] });
    if (ho.length >= CHIP_MIN) {
      A.chart('holderChart', { tooltip: { ...A.tip, trigger: 'axis' }, legend: { textStyle: { color: A.CH.ink2 }, top: 0 }, grid: { left: 50, right: 20, top: 30, bottom: 30 }, xAxis: { ...A.axisStyle, type: 'category', data: ho.map(r => r[0]), axisLabel: { color: A.CH.ink3, formatter: v => v.slice(2, 7) } }, yAxis: { ...A.axisStyle, scale: true, axisLabel: { formatter: '{value}%' } },
        series: [{ name: '千張大戶', type: 'line', data: ho.map(r => r[1]), showSymbol: false, lineStyle: { color: '#ff4d6d', width: 2 } }, { name: '400–1000 張', type: 'line', data: ho.map(r => r[2]), showSymbol: false, lineStyle: { color: '#ffb454' } }, { name: '散戶 ≤10 張', type: 'line', data: ho.map(r => r[3]), showSymbol: false, lineStyle: { color: '#2ee59d' } }] });
      A.chart('holderCount', { tooltip: { ...A.tip, trigger: 'axis' }, grid: { left: 70, right: 20, top: 16, bottom: 30 }, xAxis: { ...A.axisStyle, type: 'category', data: ho.map(r => r[0]), axisLabel: { color: A.CH.ink3, formatter: v => v.slice(2, 7) } }, yAxis: { ...A.axisStyle, scale: true, axisLabel: { formatter: v => A.fmt.yi(v) } }, series: [{ name: '股東人數', type: 'line', data: ho.map(r => r[4]), showSymbol: false, areaStyle: { color: 'rgba(62,224,255,.12)' }, lineStyle: { color: '#3ee0ff', width: 2 } }] });
    }
  }
  function tabBasics(pg, el) {
    const b = pg.basics || {}; const f = pg.fundamental || {};
    const indLink = b.industry ? (A.L.gname['ind_' + b.industry] ? A.L.group('ind_' + b.industry, b.industry) : A.fmt.esc(b.industry)) : null;
    const rows = [['公司全名', b.full_name], ['市場', b.market], ['產業別', indLink, true], ['上市日', b.listed_date], ['股本', b.capital_billion != null ? b.capital_billion + ' 億' : null], ['董事長', b.chairman], ['網站', b.website ? `<a href="${A.fmt.esc(b.website)}" target="_blank" rel="noopener">${A.fmt.esc(b.website)}</a>` : null, true], ['市值', f.market_cap != null ? A.fmt.yi(f.market_cap) : null], ['股價淨值比', f.pb != null ? A.fmt.n(f.pb) : null], ['股價營收比', f.ps != null ? A.fmt.n(f.ps) : null], ['所屬族群', (pg.meta.groups || []).map(gn => A.L.groupByName(gn)).join(' ') || null, true], ['題材', A.L.themesOf(pg.meta.code) || null, true]];
    el.innerHTML = `<div class="card"><h3>基本資料 <small>產業別、族群、題材都可以點</small></h3><dl class="kv" style="margin-top:10px">${rows.map(r => `<dt>${r[0]}</dt><dd>${r[1] != null && r[1] !== '' ? (r[2] ? r[1] : A.fmt.esc(r[1])) : '—'}</dd>`).join('')}</dl></div>`;
  }
  function tabNews(pg, el) {
    const news = pg.news || [], bv = pg.broker_views || [];
    el.innerHTML = `<div class="grid g2"><div class="card"><h3>相關新聞 <small>鉅亨 / TechNews / 經濟日報</small></h3>${news.length ? news.map(n => `<div class="ev" style="padding-left:0;padding-right:0"><a href="${A.fmt.esc(n.url)}" target="_blank" rel="noopener">${A.fmt.esc(n.title)}</a><div class="m"><span class="mono">${n.date}</span><span class="cat">${A.fmt.esc(n.category || '')}</span><span>${A.fmt.esc(n.source || '')}</span></div></div>`).join('') : '<div class="empty">近期沒有提到這檔的新聞</div>'}</div>
      <div class="card"><h3>券商觀點（新聞引述） <small>不是本站預估</small></h3>${bv.length ? `<div class="tw"><table><thead><tr><th class="l">日期</th><th class="l">券商</th><th>目標價</th><th class="l">動作</th></tr></thead><tbody>${bv.map(b => `<tr onclick="window.open('${A.fmt.esc(b.url || '#')}','_blank')"><td class="l mono">${b.date}</td><td class="l">${A.fmt.esc(b.broker || '—')}</td><td class="num">${A.fmt.n(b.target_price)}</td><td class="l">${A.fmt.esc(b.action || b.rating || '—')}</td></tr>`).join('')}</tbody></table></div>` : '<div class="empty">近 60 天沒有引述到目標價的新聞</div>'}</div></div>`;
  }

  // _dbg 只給 scripts/_preview.py 驗證用（檢查圖表與繪圖狀態），正式頁面不會呼叫
  window.Industry = { route, _dbg: () => ({ tf: state.tf, mtf: state.mtfMode, tool: drawTool,
    drawKey: kchart && kchart.draw ? kchart.draw.key : null,
    shapes: kchart && kchart.draw ? kchart.draw.shapes.length : -1,
    hasChart: !!kchart, w: drawW, fill: drawFill,
    // 驗收用：圖上最後一根的日期與收盤、各面板目前高度
    lastBar: kchart && kchart.bars && kchart.bars.length ? String(kchart.bars[kchart.bars.length - 1][0]) : null,
    lastClose: kchart && kchart.bars && kchart.bars.length ? kchart.bars[kchart.bars.length - 1][4] : null,
    paneH: kchart && kchart.paneHeights ? kchart.paneHeights() : null,
    // 驗收用：目前算出幾組背離
    div: kchart && kchart.divergences ? { top: kchart.divergences.top.length, bottom: kchart.divergences.bottom.length } : null,
    /* 驗收用：K 棒實際多寬、畫面上看得到幾根。
       Andy 2026-09-15：「切換到不同時間週期，K棒會很窄」—— 這兩個數字就是那件事的證據，
       只驗「有畫出來」看不出棒子被壓成一條線。 */
    barPx: kchart && kchart.chart ? +kchart.chart.timeScale().options().barSpacing.toFixed(2) : null,
    barsTotal: kchart && kchart.data ? kchart.data.length : 0,
    // 價格軸的上下界：K 棒被壓扁是「軸沒跟著週期重算」，不是棒子變窄
    priceRange: kchart && kchart.priceRange ? kchart.priceRange() : null,
    visibleBars: (() => {
      if (!kchart || !kchart.chart) return null;
      const r = kchart.chart.timeScale().getVisibleLogicalRange();
      return r ? +(r.to - r.from).toFixed(1) : null;
    })() }) };
})();
