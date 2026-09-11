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

  // ================================================================ 路由
  async function route(head, rest) {
    A = window.App;
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
    el.innerHTML = `<div class="card"><h3>整個台股一次看 <small>方塊＝族群成交值，顏色＝今日漲跌（紅漲綠跌）；點產業鏈進入單一鏈，點族群直接看成分股</small></h3><div id="indTree" class="chart" style="min-height:520px"></div></div>
      <div class="grid g2" style="margin-top:16px"><div class="card"><h3>產業鏈總覽 <small>本益比為族群中位數（同族群才比）</small></h3><div class="tiles" id="chainTiles"></div></div>
      <div class="card"><h3>法定產業別 <small>沒被歸入題材族群的公司依證交所產業別歸戶</small></h3><div class="tiles" id="indTiles"></div></div></div>`;
    const data = im.chains.map(c => ({ name: c.name, cid: c.id, children: c.groups.map(g => ({ name: g.name, value: g.turnover || 1, gid: g.id, chg: g.chg_pct, share: g.turnover_share, pe: g.valuation && g.valuation.median, n: g.n, itemStyle: { color: A.chgColor(g.chg_pct, 3) } })) }));
    const c = A.chart('indTree', { tooltip: { ...A.tip, formatter: p => p.data.gid ? `<b>${p.name}</b><br>成交值 ${A.fmt.yi(p.value)}（${A.fmt.n(p.data.share, 1)}%）· ${p.data.n} 檔<br>漲跌 <span style="color:${A.upDown(p.data.chg)}">${A.fmt.pct(p.data.chg)}</span> · 本益比中位 ${p.data.pe != null ? A.fmt.n(p.data.pe, 1) : '—'}` : `<b>${p.name}</b>（點進入產業鏈）` },
      series: [{ type: 'treemap', roam: false, nodeClick: false, breadcrumb: { show: false }, top: 0, left: 0, width: '100%', height: '100%', leafDepth: 2, visibleMin: 900,
        label: { formatter: p => `${p.name}\n${A.fmt.pct(p.data.chg)}`, fontSize: 13, color: '#fff', textShadowColor: '#000', textShadowBlur: 4 },
        upperLabel: { show: true, height: 26, color: '#e8eeff', fontSize: 13, fontWeight: 700, backgroundColor: 'rgba(0,0,0,.3)' },
        itemStyle: { borderColor: '#0b1224', borderWidth: 2, gapWidth: 2 }, levels: [{ itemStyle: { borderWidth: 4, gapWidth: 4 }, upperLabel: { show: true } }, { itemStyle: { gapWidth: 1 } }], data }] });
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
        ${hasDiagram ? `<div style="margin-top:14px"><div class="row spread"><h4>產品剖析圖 <small class="muted">原創示意圖，非實物比例；每個零件對應一個供應鏈環節，點零件看供應商</small></h4><div class="row" style="gap:6px"><span class="pill" id="dgAnim" style="cursor:pointer">動畫：開</span></div></div><div id="prodDiagram" class="dgwrap">${window.Diagrams[ch.id]()}</div></div>` : ''}
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
    const COLS = [['code', '代號', r => `<span class="mono">${r.code}</span>`, 'l'], ['name', '簡稱', r => A.L.stock(r.code, r.name), 'l'], ['group_name', '族群', r => A.L.group(r.gid, r.group_name), 'l'], ['close', '收盤', r => `<span class="num">${A.fmt.n(r.close)}</span>`], ['chg_pct', '漲跌', r => `<span class="num ${A.fmt.cls(r.chg_pct)}">${A.fmt.pct(r.chg_pct, 2)}</span>`], ['turnover', '成交值', r => `<span class="num">${A.fmt.yi(r.turnover)}</span>`], ['pe', '本益比', r => `<span class="num">${r.pe ? A.fmt.n(r.pe, 1) : '—'}</span>`], ['pe_percentile', '同業分位', r => `<span class="num">${r.pe_percentile != null ? A.fmt.n(r.pe_percentile, 0) + '%' : '—'}</span>`], ['momentum', '營運動能', r => `<span class="num">${r.momentum != null ? A.fmt.n(r.momentum, 0) : '—'}</span>`], ['foreign', '外資', r => `<span class="num ${A.fmt.cls(r.foreign)}">${r.foreign != null ? A.fmt.lot(r.foreign / 1000) : '—'}</span>`], ['trust', '投信', r => `<span class="num ${A.fmt.cls(r.trust)}">${r.trust != null ? A.fmt.lot(r.trust / 1000) : '—'}</span>`], ['grade', '技術判定', r => r.verdict ? `<span class="grade ${r.grade || 'W'}">${r.grade ? r.grade + ' ' : ''}${r.verdict}</span>` : '<span class="muted">—</span>', 'l']];
    let sort = { key: 'turnover', dir: -1 };
    const renderMembers = () => {
      let rows = members(); rows.sort((a, b) => { const x = a[sort.key], y = b[sort.key]; if (x == null) return 1; if (y == null) return -1; return (x > y ? 1 : x < y ? -1 : 0) * sort.dir; });
      const segTw = segFilter ? twOf(sc, segFilter) : [];
      $('#memberTitle', el).innerHTML = `成分股 <small>${rows.length} 檔${segFilter ? ' · 環節：<span style="color:' + segColor(segFilter) + '">' + A.fmt.esc(segName(sc, segFilter)) + '</span>' : ''}${state.group ? ' · ' + A.fmt.esc((groups.find(g => g.id === state.group) || {}).name || '') : ''}</small>`;
      $('#memberTable thead', el).innerHTML = '<tr>' + COLS.map(c => `<th class="${c[3] || ''}" data-k="${c[0]}">${c[1]}${sort.key === c[0] ? (sort.dir > 0 ? ' ▲' : ' ▼') : ''}</th>`).join('') + '</tr>';
      $('#memberTable tbody', el).innerHTML = rows.slice(0, 200).map(r => `<tr data-code="${r.code}">` + COLS.map(c => `<td class="${c[3] || ''}">${c[2](r)}</td>`).join('') + '</tr>').join('')
        || `<tr><td colspan="12" class="l muted">${segFilter ? (segTw.length ? '這個環節的台股不在本鏈成分股裡：' + segTw.map(c => A.L.stock(c.tw_code, c.name)).join('　') : '這個環節目前沒有台股直接對應（' + foreignOf(sc, segFilter).map(c => c.name).join('、') + '），可看上方環節說明裡的相關族群') : '沒有符合的股票'}</td></tr>`;
      $$('#memberTable th', el).forEach(th => th.onclick = () => { sort = { key: th.dataset.k, dir: sort.key === th.dataset.k ? -sort.dir : -1 }; renderMembers(); });
      $$('#memberTable tbody tr', el).forEach(tr => tr.onclick = () => { if (tr.dataset.code) A.goStock(tr.dataset.code); });
    };
    const syncHighlight = () => {
      const segsOn = segFilter ? [segFilter] : (state.group ? (A.L.gsegs[state.group] || []) : []);
      const color = segFilter ? segColor(segFilter) : (state.group ? A.L.gcolor[state.group] : null);
      highlightSegments(el, segsOn, color);
      if (segFilter) scrollChainTo(el, segFilter);
      $$('#groupCards .tile', el).forEach(t => t.classList.toggle('sel', !!state.group && t.dataset.gid === state.group || (!!segFilter && (A.L.sgroups[segFilter] || []).includes(t.dataset.gid))));
      $$('#segChips .segchip', el).forEach(c => c.classList.toggle('sel', segsOn.includes(c.dataset.seg)));
      renderSegBox($('#segBox', el), sc, segFilter, ch);
      renderMembers();
    };
    $$('#groupCards .tile', el).forEach(t => t.onclick = (e) => { if (e.target.closest('a.lk')) return; state.group = state.group === t.dataset.gid ? null : t.dataset.gid; segFilter = null; syncHighlight(); });
    $$('#segChips .segchip', el).forEach(c => c.onclick = () => { segFilter = segFilter === c.dataset.seg ? null : c.dataset.seg; state.group = null; syncHighlight(); });
    $$('#mktSeg button', el).forEach(b => b.onclick = () => { $$('#mktSeg button', el).forEach(x => x.classList.toggle('on', x === b)); mkt = b.dataset.v; renderMembers(); });
    if (hasDiagram && sc) {
      paintDiagram($('#prodDiagram', el));
      drawChainMap($('#chainMap', el), sc, ch.id, im, { onSelect: (co) => { if (co && co.tw_code) A.goStock(co.tw_code); }, onSegment: (seg) => { segFilter = segFilter === seg ? null : seg; state.group = null; syncHighlight(); } });
      wireDiagram(el, (seg) => { segFilter = segFilter === seg ? null : seg; state.group = null; syncHighlight(); });
      const animBtn = $('#dgAnim', el); if (animBtn) animBtn.onclick = () => { const on = $('#prodDiagram', el).classList.toggle('noanim'); animBtn.textContent = on ? '動畫：關' : '動畫：開'; try { localStorage.setItem('tw.dganim', on ? '0' : '1'); } catch (e) { /* 忽略 */ } };
      try { if (localStorage.getItem('tw.dganim') === '0') { $('#prodDiagram', el).classList.add('noanim'); animBtn.textContent = '動畫：關'; } } catch (e) { /* 忽略 */ }
    }
    syncHighlight();
  }
  // 環節說明盒：這個環節的台股（可點）、外商、相關族群（可點）
  // 市場別一律以全市場索引（stocks.json）為準：groups_detail 的 market 欄位常常是空的
  const marketOf = (r) => String(A.L.cmarket[r.code] || r.market || '').toUpperCase() || null;

  function renderSegBox(box, sc, seg, ch) {
    if (!box) return;
    if (!seg || !sc) { box.innerHTML = ''; return; }
    const tw = twOf(sc, seg), fo = foreignOf(sc, seg), gids = A.L.sgroups[seg] || [];
    const s = sc.segments.find(x => x.id === seg) || {};
    box.innerHTML = `<div class="segbox" style="--c:${segColor(seg)}"><b class="t">${A.fmt.esc(s.name || seg)}</b> <span class="muted">${s.desc ? A.fmt.esc(s.desc) : ''}</span>
      <div class="row"><span class="muted">台股</span>${tw.length ? tw.map(c => A.L.stock(c.tw_code, c.name)).join('') : '<span class="muted">沒有直接對應的台股</span>'}</div>
      ${fo.length ? `<div class="row"><span class="muted">外商</span>${fo.map(c => `<span class="pill" title="${A.fmt.esc((c.tech || []).join('、'))}">${A.fmt.esc(c.name)}</span>`).join('')}</div>` : ''}
      ${gids.length ? `<div class="row"><span class="muted">相關族群</span>${gids.map(g => A.L.group(g)).join('')}</div>` : ''}</div>`;
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
    $$('#prodDiagram [data-seg]', root).forEach(n => { n.classList.toggle('sel', on.has(n.dataset.seg)); n.classList.toggle('dim', on.size > 0 && !on.has(n.dataset.seg)); if (color && on.has(n.dataset.seg)) n.style.setProperty('--c', color); else n.style.setProperty('--c', segColor(n.dataset.seg)); });
    $$('.chainmap .co', root).forEach(n => n.classList.toggle('dim', on.size > 0 && !on.has(n.dataset.segment)));
    $$('.chainmap .segtitle', root).forEach(n => n.classList.toggle('sel', on.has(n.dataset.seg)));
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

  // ================================================================ Level 2：個股頁
  async function renderStock(code, im, sc, gd) {
    show(false, true, true);
    const pg = await A.load('stock/' + code, { fallback: null });
    if (!pg) {
      const known = (A.L.all || []).find(x => x.code === code);
      $('#stockPage').innerHTML = `<div class="card"><div class="empty">${known ? `${A.fmt.esc(known.name || '')} ${code} 的個股頁還沒產生，下一次盤後更新就會出現。` : `找不到代號 ${A.fmt.esc(code)}（上市櫃普通股才有個股頁，權證／期貨不列入）。`}<br><br>${A.L.back()}</div></div>`;
      $('#indChain').innerHTML = ''; crumbs([{ label: '產業地圖', href: '#industry' }, { label: code }]); return;
    }
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
            <div class="row" style="margin-top:6px"><span class="num" style="font-size:30px;font-weight:700" id="pxNow">${A.fmt.n(s.close)}</span><span class="num ${A.fmt.cls(s.chg_pct)}" style="font-size:18px">${A.fmt.pct(s.chg_pct, 2)}</span><span class="pill">技術分 ${A.fmt.n(s.tech_score, 0)}</span><span class="pill">本益比 ${s.pe ? A.fmt.n(s.pe, 1) : '—'}</span><span class="pill">同業分位 ${s.pe_percentile != null ? A.fmt.n(s.pe_percentile, 0) + '%' : '—'}</span><span class="pill">營收 YoY ${A.fmt.pct(s.rev_yoy)}</span><span class="pill ${tier[1]}" title="${A.fmt.esc(tier[2])}">${tier[0]}</span></div></div>
          <div class="verdict" style="min-width:280px;max-width:520px"><h3><span class="grade ${gradeCls}">${v.grade ? v.grade + ' ' : ''}${v.verdict || '—'}</span> <small>停損 ${A.fmt.n(v.stop)} · 目標 ${A.fmt.n(v.tp1)} · 風報 ${v.rr != null ? A.fmt.n(v.rr, 1) : '—'}</small></h3><ul>${(v.reasons || []).slice(0, 3).map(r => `<li>${A.fmt.esc(r)}</li>`).join('')}</ul>${v.risk_text ? `<div class="note" style="margin-top:6px">風險：${A.fmt.esc(v.risk_text)}</div>` : ''}</div>
        </div>
        <div class="toolbar" style="margin-top:14px">
          <div class="seg" id="tfSeg">${['15m', '60m', '240m', '1d', '1w', '1M'].map(tf => `<button data-tf="${tf}" class="${tf === state.tf ? 'on' : ''}">${({ '15m': '15分', '60m': '1時', '240m': '4時', '1d': '日', '1w': '週', '1M': '月' })[tf]}</button>`).join('')}</div>
          <div id="indChips" class="row" style="gap:6px"></div>
          <div class="sp"></div>
          <button class="btn small" id="mtfBtn">${state.mtfMode ? '單一週期' : '四週期同看'}</button>
          <button class="btn small" id="fitBtn" title="雙擊價格軸也可以">重設縮放</button>
        </div>
        <div id="chartHost"></div>
        ${pg.note ? `<div class="banner on" style="margin:10px 0 0">${A.fmt.esc(pg.note)}</div>` : ''}
        <div class="note" style="margin-top:6px">滑鼠在圖內滾輪＝時間縮放；在右側價格軸上滾輪或拖曳＝調整上下寬度（K 棒跟著變）；雙擊價格軸還原。分 K 來源 Yahoo Finance（1 小時可回溯 2 年、15 分 60 天），盤後更新。</div>
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
      drawChainMap($('#chainMap', el), sc, cid, im, { onSelect: (c2) => { if (c2.tw_code) A.goStock(c2.tw_code); }, onSegment: (seg) => { location.hash = `#industry/${cid}/${seg}`; } });
      highlightSegments(el, co ? [co.segment] : [], co ? segColor(co.segment) : null);
      wireDiagram(el, (seg) => { location.hash = `#industry/${cid}/${seg}`; });
      $$('.segchip', el).forEach(c => c.onclick = () => { location.hash = `#industry/${cid}/${c.dataset.seg}`; });
      try { if (localStorage.getItem('tw.dganim') === '0') $('#prodDiagram', el).classList.add('noanim'); } catch (e) { /* 忽略 */ }
    }
  }

  // ---------------------------------------------------------------- K 線面板
  const DEFAULT_CFG = { ma: [5, 20, 60, 120], boll: null, vol: true, volma: 20, kd: { n: 9, m1: 3, m2: 3 }, macd: { f: 12, s: 26, g: 9 }, rsi: null, smc: true, marks: true, lines: true };
  function loadCfg() { try { const s = localStorage.getItem('tw.kcfg'); if (s) return Object.assign({}, DEFAULT_CFG, JSON.parse(s)); } catch (e) { /* 忽略 */ } return Object.assign({}, DEFAULT_CFG); }
  function saveCfg(c) { try { localStorage.setItem('tw.kcfg', JSON.stringify(c)); } catch (e) { /* 忽略 */ } }
  function barsFor(pg, tf) {
    if (tf === '1d') return pg.daily && pg.daily.length ? pg.daily : pg.ohlcv;
    if (tf === '1w') return KUtil.resampleDaily(pg.daily || pg.ohlcv, 'W');
    if (tf === '1M') return KUtil.resampleDaily(pg.daily || pg.ohlcv, 'M');
    return (pg.intraday && pg.intraday[tf]) || [];
  }
  function zonesFor(pg, tf) { const t = pg.mtf && pg.mtf.tf && pg.mtf.tf[tf]; if (t) return [...t.demand, ...t.supply].map(z => ({ ...z, tf: t.label })); if (tf === '1d' && pg.verdict) return [...(pg.verdict.demand || []).map(z => ({ ...z, kind: 'demand' })), ...(pg.verdict.supply || []).map(z => ({ ...z, kind: 'supply' }))]; return []; }
  function marksFor(pg, tf) { const t = pg.mtf && pg.mtf.tf && pg.mtf.tf[tf]; if (t) return t.marks; if (tf === '1d') return pg.marks || {}; return {}; }

  function setupChart(pg) {
    state.cfg = state.cfg || loadCfg();
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
      { k: 'lines', label: '停損/目標', on: () => !!cfg.lines, params: () => [], toggle: () => { cfg.lines = !cfg.lines; }, color: '#ffb454' },
    ];
    const drawChips = () => {
      chips.innerHTML = chipDefs.map(c => `<span class="chip ${c.on() ? 'on' : ''}" data-k="${c.k}"><i style="background:${c.color}"></i>${c.label}${c.params().map(p => `<input data-k="${c.k}" data-p="${p.key}" value="${p.val}" style="width:${p.w}px" onclick="event.stopPropagation()">`).join('')}</span>`).join('');
      $$('.chip', chips).forEach(ch => ch.onclick = (e) => { if (e.target.tagName === 'INPUT') return; chipDefs.find(c => c.k === ch.dataset.k).toggle(); saveCfg(cfg); drawChips(); apply(); });
      $$('.chip input', chips).forEach(inp => inp.onchange = () => { chipDefs.find(c => c.k === inp.dataset.k).set(inp.value, inp.dataset.p); saveCfg(cfg); drawChips(); apply(); });
    };
    const build = () => {
      if (kchart) { kchart.destroy(); kchart = null; } miniCharts.forEach(c => c.destroy()); miniCharts = [];
      if (state.mtfMode) { host.innerHTML = `<div class="mtf-grid" id="mtfGrid"></div>`; buildMtfGrid(pg); return; }
      host.innerHTML = `<div id="lwc"><div class="legend-ov" id="legendOv"></div></div>`;
      kchart = new KChart($('#lwc'), { tf: state.tf });
      apply();
    };
    const apply = () => {
      if (!kchart) return;
      const bars = barsFor(pg, state.tf);
      if (!bars || bars.length < 5) {
        const why = pg.meta.tier === 'thin' ? (pg.note || '歷史價量還在回補')
          : /m$/.test(state.tf) ? '這檔沒有分 K（只有族群成分股與成交值前段會抓 Yahoo 分 K）；日線／週線／月線可以正常看'
          : '這個週期尚無資料';
        $('#lwc').innerHTML = `<div class="empty" style="height:100%">${A.fmt.esc(why)}</div>`; kchart = null; return;
      }
      if (!$('#legendOv')) { $('#lwc').innerHTML = '<div class="legend-ov" id="legendOv"></div>'; kchart = new KChart($('#lwc'), { tf: state.tf }); }
      kchart.setBars(bars, state.tf);
      kchart.applyIndicators(cfg);
      kchart.setZones(cfg.smc ? zonesFor(pg, state.tf) : []);
      kchart.setMarkers(cfg.marks ? marksFor(pg, state.tf) : {});
      const v = pg.verdict || {};
      kchart.setPriceLines(cfg.lines && state.tf === '1d' ? [{ price: v.stop, title: '停損', color: '#ffb454' }, { price: v.tp1, title: '目標 1', color: '#3ee0ff' }, { price: v.tp2, title: '目標 2', color: '#8b7bff' }] : []);
      const legend = $('#legendOv');
      const TFN = { '15m': '15 分', '60m': '1 小時', '240m': '4 小時', '1d': '日線', '1w': '週線', '1M': '月線' };
      kchart.setWatermark(`${pg.meta.name} ${pg.meta.code} · ${TFN[state.tf] || state.tf}`);
      const at = (arr, i) => (arr ? arr[i == null ? arr.length - 1 : i] : null);
      const show = (i) => {
        const idx = i == null ? kchart.data.length - 1 : i; const d = kchart.data[idx]; if (!d) return; const prev = kchart.data[idx - 1]; const vals = kchart.values || {};
        const chg = prev ? (d.close - prev.close) / prev.close * 100 : null; const amp = d.low ? (d.high - d.low) / d.low * 100 : null;
        const col = d.close >= d.open ? '#ff4d6d' : '#2ee59d';
        let s = `<b>${KUtil.fmtTime(d.time, state.tf)}</b>　開 ${A.fmt.n(d.open)}　高 ${A.fmt.n(d.high)}　低 ${A.fmt.n(d.low)}　收 <b style="color:${col}">${A.fmt.n(d.close)}</b>${chg != null ? ` <span style="color:${A.upDown(chg)}">${A.fmt.pct(chg, 2)}</span>` : ''}　振幅 ${amp != null ? A.fmt.n(amp, 1) + '%' : '—'}　量 ${A.fmt.lot(d.volume / 1000)}`;
        const parts = []; (cfg.ma || []).forEach((n, k) => { const m = at(vals['MA' + n], i); if (m != null) parts.push(`<span style="color:${KUtil.colors.ma[k % 6]}">MA${n} ${A.fmt.n(m)}</span>`); });
        if (vals.BOLL) { const u = at(vals.BOLL.up, i), lo = at(vals.BOLL.low, i); if (u != null) parts.push(`<span style="color:#b39dff">BOLL ${A.fmt.n(lo)} – ${A.fmt.n(u)}</span>`); }
        legend.innerHTML = s + (parts.length ? '<br>' + parts.join('　') : '');
        const pl = {};
        if (cfg.vol) pl.vol = `成交量 <b>${A.fmt.lot(d.volume / 1000)}</b>${cfg.volma && at(vals.VOLMA, i) != null ? `　<span style="color:#ffd166">MA${cfg.volma} ${A.fmt.lot(at(vals.VOLMA, i) / 1000)}</span>` : ''}`;
        if (vals.KD) pl.kd = `KD(${cfg.kd.n},${cfg.kd.m1},${cfg.kd.m2})　<span style="color:${KUtil.colors.k}">K ${A.fmt.n(at(vals.KD.k, i), 1)}</span>　<span style="color:${KUtil.colors.d}">D ${A.fmt.n(at(vals.KD.d, i), 1)}</span>`;
        if (vals.MACD) pl.macd = `MACD(${cfg.macd.f},${cfg.macd.s},${cfg.macd.g})　<span style="color:${KUtil.colors.dif}">DIF ${A.fmt.n(at(vals.MACD.dif, i))}</span>　<span style="color:${KUtil.colors.dea}">MACD ${A.fmt.n(at(vals.MACD.dea, i))}</span>　OSC <span style="color:${A.upDown(at(vals.MACD.osc, i))}">${A.fmt.n(at(vals.MACD.osc, i))}</span>`;
        if (vals.RSI) pl.rsi = `RSI(${cfg.rsi.n})　<span style="color:${KUtil.colors.rsi}">${A.fmt.n(at(vals.RSI, i), 1)}</span>`;
        kchart.setPaneLabels(pl);
      };
      show(null); kchart.onCrosshair(show);
    };
    $$('#tfSeg button').forEach(b => b.onclick = () => { $$('#tfSeg button').forEach(x => x.classList.toggle('on', x === b)); state.tf = b.dataset.tf; if (state.mtfMode) build(); else apply(); });
    $('#mtfBtn').onclick = () => { state.mtfMode = !state.mtfMode; $('#mtfBtn').textContent = state.mtfMode ? '單一週期' : '四週期同看'; build(); };
    $('#fitBtn').onclick = () => { if (kchart) { kchart.candle.priceScale().setAutoScale(true); kchart.fitLast(160); } };
    drawChips(); build();
  }
  function buildMtfGrid(pg) {
    const have = (tf) => barsFor(pg, tf).length >= 20;
    const pref = ['15m', '60m', '240m', '1d', '1w', '1M'].filter(have);
    const pick = pref.length >= 4 ? (have('15m') ? ['15m', '60m', '240m', '1d'] : pref.slice(-4)) : pref;
    const grid = $('#mtfGrid');
    grid.innerHTML = pick.map(tf => { const t = pg.mtf && pg.mtf.tf && pg.mtf.tf[tf]; return `<div class="mtf-cell"><div class="cap"><b>${({ '15m': '15 分', '60m': '1 小時', '240m': '4 小時', '1d': '日線', '1w': '週線', '1M': '月線' })[tf]}</b> ${t ? `<span style="color:${t.trend > 0 ? '#ff4d6d' : t.trend < 0 ? '#2ee59d' : '#a9b6d6'}">${t.trend > 0 ? '多頭結構' : t.trend < 0 ? '空頭結構' : '盤整'}</span> · 均線${t.ma_align > 0 ? '多排' : t.ma_align < 0 ? '空排' : '糾結'}${t.rsi != null ? ' · RSI ' + t.rsi.toFixed(0) : ''}` : ''}</div><div class="cv" id="mini-${tf}"></div></div>`; }).join('');
    pick.forEach(tf => { const el = $('#mini-' + tf); const c = new KChart(el, { mini: true, tf }); c.setBars(barsFor(pg, tf), tf); c.applyIndicators({ ma: [20, 60], vol: false }); c.setZones(zonesFor(pg, tf)); c.setMarkers(marksFor(pg, tf)); miniCharts.push(c); });
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
  function tabProfit(pg, el) {
    const q = (pg.profit || {}).quarters || []; const pe = pg.pe_history || [];
    if (!q.length) { el.innerHTML = '<div class="card"><div class="empty">尚無季報歷史（回補進行中）</div></div>'; return; }
    const last = q[q.length - 1];
    el.innerHTML = `<div class="kvs" style="margin-bottom:12px"><div class="k"><div class="l">最新季度</div><div class="v">${last[0]}</div></div><div class="k"><div class="l">單季 EPS</div><div class="v">${A.fmt.n(last[5])}</div></div><div class="k"><div class="l">年度累計 EPS</div><div class="v">${A.fmt.n(last[6])}</div></div><div class="k"><div class="l">EPS 年增（元）</div><div class="v ${A.fmt.cls(last[7])}">${last[7] != null ? (last[7] > 0 ? '+' : '') + A.fmt.n(last[7]) : '—'}</div></div><div class="k"><div class="l">毛利率</div><div class="v">${A.fmt.n(last[2], 1)}%</div></div><div class="k"><div class="l">營益率</div><div class="v">${A.fmt.n(last[3], 1)}%</div></div><div class="k"><div class="l">淨利率</div><div class="v">${A.fmt.n(last[4], 1)}%</div></div></div>
      <div class="grid g2"><div class="card"><h3>EPS 與三率 <small>單季；財報法規為季報，沒有每月</small></h3><div id="profitChart" class="chart"></div></div><div class="card"><h3>本益比河流 <small>每季財報可用日後的收盤 / 近四季 EPS；虧損不算</small></h3><div id="peChart" class="chart"></div></div></div>
      <div class="card" style="margin-top:16px"><h3>季報明細</h3><div class="tw" style="max-height:360px"><table><thead><tr><th class="l">季度</th><th>營收</th><th>毛利率</th><th>營益率</th><th>淨利率</th><th>淨利</th><th>EPS</th><th>累計 EPS</th><th>EPS 年增</th></tr></thead><tbody>${q.slice().reverse().map(r => `<tr><td class="l mono">${r[0]}</td><td class="num">${A.fmt.yi(r[1])}</td><td class="num">${A.fmt.n(r[2], 1)}%</td><td class="num">${A.fmt.n(r[3], 1)}%</td><td class="num">${A.fmt.n(r[4], 1)}%</td><td class="num">${A.fmt.yi(r[8])}</td><td class="num">${A.fmt.n(r[5])}</td><td class="num">${A.fmt.n(r[6])}</td><td class="num ${A.fmt.cls(r[7])}">${r[7] != null ? (r[7] > 0 ? '+' : '') + A.fmt.n(r[7]) : '—'}</td></tr>`).join('')}</tbody></table></div></div>`;
    A.chart('profitChart', { tooltip: { ...A.tip, trigger: 'axis' }, legend: { textStyle: { color: A.CH.ink2 }, top: 0 }, grid: { left: 50, right: 50, top: 30, bottom: 30 },
      xAxis: { ...A.axisStyle, type: 'category', data: q.map(r => r[0]), axisLabel: { color: A.CH.ink3 } }, yAxis: [{ ...A.axisStyle, name: 'EPS' }, { ...A.axisStyle, axisLabel: { formatter: '{value}%' }, splitLine: { show: false } }],
      series: [{ name: 'EPS', type: 'bar', data: q.map(r => ({ value: r[5], itemStyle: { color: r[5] >= 0 ? 'rgba(255,77,109,.7)' : 'rgba(46,229,157,.7)', borderRadius: [3, 3, 0, 0] } })) }, { name: '毛利率', type: 'line', yAxisIndex: 1, data: q.map(r => r[2]), smooth: .3, showSymbol: false, lineStyle: { color: '#ffd166' } }, { name: '營益率', type: 'line', yAxisIndex: 1, data: q.map(r => r[3]), smooth: .3, showSymbol: false, lineStyle: { color: '#3ee0ff' } }, { name: '淨利率', type: 'line', yAxisIndex: 1, data: q.map(r => r[4]), smooth: .3, showSymbol: false, lineStyle: { color: '#8b7bff' } }] });
    if (pe.length) A.chart('peChart', { tooltip: { ...A.tip, trigger: 'axis', formatter: ps => { const r = pe[ps[0].dataIndex]; return `<b>${r.period}</b><br>本益比 ${r.pe ?? '—'}（區間 ${r.pe_low ?? '—'}–${r.pe_high ?? '—'}）<br>近四季 EPS ${r.ttm_eps}`; } }, grid: { left: 50, right: 20, top: 20, bottom: 30 }, xAxis: { ...A.axisStyle, type: 'category', data: pe.map(r => r.period), axisLabel: { color: A.CH.ink3 } }, yAxis: { ...A.axisStyle, scale: true },
      series: [{ name: '區間', type: 'line', data: pe.map(r => r.pe_low), lineStyle: { opacity: 0 }, stack: 'pe', showSymbol: false }, { name: '高低', type: 'line', data: pe.map(r => r.pe_high != null && r.pe_low != null ? r.pe_high - r.pe_low : null), lineStyle: { opacity: 0 }, stack: 'pe', areaStyle: { color: 'rgba(139,123,255,.2)' }, showSymbol: false }, { name: '本益比', type: 'line', data: pe.map(r => r.pe), lineStyle: { color: '#8b7bff', width: 2 }, symbolSize: 5 }] });
    else A.empty('peChart', '需要四季連續財報');
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
  function tabChips(pg, el) {
    const iv = (pg.inst_v3 || {}).daily || [], mg = pg.margin || [], ho = pg.holders || [];
    el.innerHTML = `<div class="grid g2"><div class="card"><h3>三大法人 <small>每日買賣超（張）與累計</small></h3><div id="instChart" class="chart"></div></div><div class="card"><h3>融資融券 <small>餘額（張）</small></h3><div id="marginChart" class="chart"></div></div></div>
      <div class="grid g2" style="margin-top:16px"><div class="card"><h3>大戶 / 散戶持股 <small>集保每週：千張大戶、400–1000 張、10 張以下</small></h3><div id="holderChart" class="chart"></div></div><div class="card"><h3>股東人數 <small>人數下降＋大戶比例上升＝籌碼集中</small></h3><div id="holderCount" class="chart"></div></div></div>
      <div class="note" style="margin-top:10px">主力（券商分點家數差）需付費資料，尚未提供；以千張大戶週變化與法人連續買賣作替代。</div>`;
    if (iv.length) A.chart('instChart', { tooltip: { ...A.tip, trigger: 'axis', formatter: ps => `<b>${ps[0].axisValue}</b><br>` + ps.map(p => `${p.marker}${p.seriesName} ${A.fmt.lot(p.value / 1000)}`).join('<br>') }, legend: { textStyle: { color: A.CH.ink2 }, top: 0 }, grid: { left: 60, right: 60, top: 30, bottom: 30 }, xAxis: { ...A.axisStyle, type: 'category', data: iv.map(r => r[0]), axisLabel: { color: A.CH.ink3, formatter: v => v.slice(5) } }, yAxis: [{ ...A.axisStyle, axisLabel: { formatter: v => A.fmt.lot(v / 1000) } }, { ...A.axisStyle, axisLabel: { formatter: v => A.fmt.lot(v / 1000) }, splitLine: { show: false } }],
      series: [{ name: '外資', type: 'bar', stack: 'i', data: iv.map(r => r[1]), itemStyle: { color: '#3ee0ff' } }, { name: '投信', type: 'bar', stack: 'i', data: iv.map(r => r[2]), itemStyle: { color: '#ffb454' } }, { name: '自營', type: 'bar', stack: 'i', data: iv.map(r => r[3]), itemStyle: { color: '#8b7bff' } }, { name: '累計', type: 'line', yAxisIndex: 1, data: iv.map(r => r[4]), showSymbol: false, lineStyle: { color: '#ff8fab', width: 2 } }] }); else A.empty('instChart');
    if (mg.length) A.chart('marginChart', { tooltip: { ...A.tip, trigger: 'axis' }, legend: { textStyle: { color: A.CH.ink2 }, top: 0 }, grid: { left: 60, right: 60, top: 30, bottom: 30 }, xAxis: { ...A.axisStyle, type: 'category', data: mg.map(r => r[0]), axisLabel: { color: A.CH.ink3, formatter: v => v.slice(5) } }, yAxis: [{ ...A.axisStyle, scale: true }, { ...A.axisStyle, scale: true, splitLine: { show: false } }],
      series: [{ name: '融資餘額', type: 'line', data: mg.map(r => r[1]), showSymbol: false, areaStyle: { color: 'rgba(255,77,109,.12)' }, lineStyle: { color: '#ff4d6d', width: 2 } }, { name: '融券餘額', type: 'line', yAxisIndex: 1, data: mg.map(r => r[2]), showSymbol: false, lineStyle: { color: '#2ee59d', width: 1.5 } }] }); else A.empty('marginChart', '融資券歷史回補中');
    if (ho.length) { A.chart('holderChart', { tooltip: { ...A.tip, trigger: 'axis' }, legend: { textStyle: { color: A.CH.ink2 }, top: 0 }, grid: { left: 50, right: 20, top: 30, bottom: 30 }, xAxis: { ...A.axisStyle, type: 'category', data: ho.map(r => r[0]), axisLabel: { color: A.CH.ink3, formatter: v => v.slice(2, 7) } }, yAxis: { ...A.axisStyle, scale: true, axisLabel: { formatter: '{value}%' } },
      series: [{ name: '千張大戶', type: 'line', data: ho.map(r => r[1]), showSymbol: false, lineStyle: { color: '#ff4d6d', width: 2 } }, { name: '400–1000 張', type: 'line', data: ho.map(r => r[2]), showSymbol: false, lineStyle: { color: '#ffb454' } }, { name: '散戶 ≤10 張', type: 'line', data: ho.map(r => r[3]), showSymbol: false, lineStyle: { color: '#2ee59d' } }] });
      A.chart('holderCount', { tooltip: { ...A.tip, trigger: 'axis' }, grid: { left: 70, right: 20, top: 16, bottom: 30 }, xAxis: { ...A.axisStyle, type: 'category', data: ho.map(r => r[0]), axisLabel: { color: A.CH.ink3, formatter: v => v.slice(2, 7) } }, yAxis: { ...A.axisStyle, scale: true, axisLabel: { formatter: v => A.fmt.yi(v) } }, series: [{ name: '股東人數', type: 'line', data: ho.map(r => r[4]), showSymbol: false, areaStyle: { color: 'rgba(62,224,255,.12)' }, lineStyle: { color: '#3ee0ff', width: 2 } }] }); }
    else { A.empty('holderChart', '集保資料每週累積中'); A.empty('holderCount', '集保資料每週累積中'); }
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

  window.Industry = { route };
})();
