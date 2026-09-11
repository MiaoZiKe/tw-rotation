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
    let c = echarts.getInstanceByDom(el); if (!c) c = echarts.init(el, null, { renderer: 'canvas' });
    c.setOption(Object.assign({ backgroundColor: 'transparent', textStyle: { fontFamily: 'Noto Sans TC, JetBrains Mono, sans-serif', color: CH.ink2 }, animationDuration: 500 }, option), opts && opts.notMerge !== false);
    charts[el.id || Math.random()] = c; return c;
  }
  const axisStyle = { axisLine: { lineStyle: { color: CH.line } }, axisLabel: { color: CH.ink3, fontFamily: 'JetBrains Mono' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,.05)' } } };
  const tip = { backgroundColor: '#141e36', borderColor: '#2a3860', textStyle: { color: '#e8eeff', fontSize: 12.5 }, confine: true };
  const empty = (id, msg) => { const el = document.getElementById(id); if (el) { const c = echarts.getInstanceByDom(el); if (c) c.dispose(); el.innerHTML = `<div class="empty">${msg || '尚無資料'}</div>`; } };
  window.addEventListener('resize', () => { Object.values(charts).forEach(c => c && c.resize && c.resize()); });
  const goStock = (code) => { location.hash = '#stock/' + code; };
  window.goStock = goStock;

  // ---------------------------------------------------------------- 路由
  const VIEWS = ['overview', 'flow', 'industry', 'themes', 'season'];
  const rendered = {};
  async function route() {
    const h = location.hash.replace('#', '') || 'overview';
    const [head, ...rest] = h.split('/');
    let view = VIEWS.includes(head) ? head : head === 'stock' ? 'industry' : 'overview';
    $$('.tab').forEach(t => t.classList.toggle('on', t.dataset.view === view));
    $$('.view').forEach(v => v.classList.toggle('on', v.id === 'v-' + view));
    window.scrollTo({ top: 0 });
    if (view === 'industry') { await window.Industry.route(head, rest); return; }
    if (!rendered[view]) { rendered[view] = true; await ({ overview: renderOverview, flow: renderFlow, themes: renderThemes, season: renderSeason })[view](); }
    setTimeout(() => Object.values(charts).forEach(c => c && c.resize && c.resize()), 30);
  }
  window.addEventListener('hashchange', route);
  $$('.tab').forEach(t => t.addEventListener('click', () => { location.hash = '#' + t.dataset.view; }));

  // ---------------------------------------------------------------- 總覽
  async function renderOverview() {
    const [heat, gt, rot, cands, f3, th, trust, gval] = await Promise.all([load('market_heat'), load('groups_today'), load('rotation'), load('candidates'), load('flow_v3'), load('themes'), load('trust_streak'), load('group_valuation')]);
    // hero
    const b = (heat && heat.breadth) || {};
    const kp = (l, v, d, cls) => `<div class="card tight kpi"><div class="l">${l}</div><div class="v ${cls || ''}">${v}</div><div class="d">${d || ''}</div></div>`;
    $('#hero').innerHTML = [
      kp('加權指數', fmt.n(heat && heat.taiex, 0), heat ? `<span class="${fmt.cls(heat.change)}">${fmt.pct(heat.change / (heat.taiex - heat.change) * 100)} (${fmt.n(heat.change, 0)})</span>` : '', heat && fmt.cls(heat.change)),
      kp('成交值', heat ? fmt.yi(heat.turnover) : '—', heat && heat.turnover_ma20 ? `20 日均 ${fmt.yi(heat.turnover_ma20)}` : ''),
      kp('漲 / 跌家數', heat ? `<span class="up">${heat.advancers}</span> <span class="muted">/</span> <span class="down">${heat.decliners}</span>` : '—', heat ? `平盤 ${heat.unchanged}` : ''),
      kp('站上 MA20', b.pct_above_ma20 != null ? b.pct_above_ma20 + '%' : '—', `MA60 ${b.pct_above_ma60 ?? '—'}%　樣本 ${b.n ?? '—'}`),
      kp('前五族群佔比', heat && heat.top5_share != null ? heat.top5_share.toFixed(1) + '%' : '—', '越高＝資金越集中'),
      kp('今日候選', `<span class="up">${b.grade_a ?? 0}</span> A <span class="muted">/</span> <span class="amber">${b.grade_b ?? 0}</span> B`, '回檔承接 / 突破追進'),
    ].join('');
    renderHeat(gt, rot);
    renderRRG('rrgMini', f3 && f3.rrg, 5, true);
    renderThemeStrip(th);
    renderCandidates(cands);
    renderBreadth(heat);
    renderTrust(trust, cands);
    renderGval(gval);
  }

  function renderHeat(gt, rot) {
    if (!gt || !gt.length) return empty('heat');
    const rotMap = {}; (rot || []).forEach(r => { rotMap[r.group_id] = r.rotation; });
    const chains = {}; gt.forEach(g => { const c = g.chain || 'industry'; (chains[c] = chains[c] || []).push(g); });
    const CN = { semiconductor: '半導體', ai_server: 'AI 伺服器', electronics: '一般電子', traditional: '傳產', infrastructure: '基礎建設', industry: '其他產業別' };
    const data = Object.entries(chains).map(([cid, gs]) => ({ name: CN[cid] || cid, children: gs.map(g => ({ name: g.group_name, value: g.turnover, gid: g.group_id, chg: g.chg_pct, rot: rotMap[g.group_id], share: g.turnover_share, itemStyle: { color: chgColor(rotMap[g.group_id] != null ? rotMap[g.group_id] * 3 : g.chg_pct, 3) } })) }));
    const c = chart('heat', {
      tooltip: { ...tip, formatter: p => p.data.gid ? `<b>${p.name}</b><br>成交值 ${fmt.yi(p.value)}（${fmt.n(p.data.share, 1)}%）<br>漲跌 <span style="color:${upDown(p.data.chg)}">${fmt.pct(p.data.chg)}</span><br>資金流向 <span style="color:${upDown(p.data.rot)}">${p.data.rot != null ? (p.data.rot > 0 ? '流入 +' : '流出 ') + p.data.rot.toFixed(2) + ' pp' : '—'}</span>` : p.name },
      series: [{ type: 'treemap', roam: false, nodeClick: false, breadcrumb: { show: false }, width: '100%', height: '100%', top: 0, left: 0,
        label: { show: true, formatter: p => `${p.name}\n${fmt.pct(p.data.chg)}`, fontSize: 13, color: '#fff', textShadowColor: '#000', textShadowBlur: 4 },
        upperLabel: { show: true, height: 22, color: '#a9b6d6', fontSize: 12, backgroundColor: 'rgba(0,0,0,.25)' },
        itemStyle: { borderColor: '#0b1224', borderWidth: 2, gapWidth: 2 }, levels: [{ itemStyle: { borderColor: '#0b1224', borderWidth: 3, gapWidth: 3 } }, { itemStyle: { gapWidth: 1 } }],
        data }],
    });
    if (c) c.off('click').on('click', p => { if (p.data && p.data.gid) location.hash = '#industry/group/' + p.data.gid; });
  }

  function renderRRG(id, rrg, trail, mini) {
    if (!rrg || !rrg.points || !rrg.points.length) return empty(id, 'RRG 需要至少 20 個交易日');
    const pts = rrg.points.slice(0, mini ? 18 : 40);
    const lines = pts.map((p, i) => ({ type: 'line', data: p.trail.slice(-trail).map(t => [t[1], t[2]]), showSymbol: false, lineStyle: { width: 1.2, color: PALETTE[i % PALETTE.length], opacity: .55 }, smooth: .3, silent: true, z: 1 }));
    const scatter = { type: 'scatter', data: pts.map((p, i) => ({ name: p.group_name, value: [p.x, p.y], gid: p.group_id, share: p.share, quadrant: p.quadrant, symbolSize: Math.max(10, Math.min(38, Math.sqrt(p.share || 1) * (mini ? 7 : 10))), itemStyle: { color: PALETTE[i % PALETTE.length], borderColor: '#0a1020', borderWidth: 1.5 } })), label: { show: !mini, formatter: '{b}', position: 'right', color: '#e8eeff', fontSize: 11.5, textShadowColor: '#000', textShadowBlur: 3 }, z: 3, emphasis: { scale: 1.2 } };
    const c = chart(id, {
      tooltip: { ...tip, formatter: p => p.data && p.data.gid ? `<b>${p.name}</b><br>相對強度 ${fmt.n(p.value[0])}　動能 ${fmt.n(p.value[1])}<br>象限：${({ leading: '領先（強且變強）', weakening: '轉弱（強但變弱）', lagging: '落後（弱且變弱）', improving: '改善（弱但變強）' })[p.data.quadrant]}<br>成交值佔比 ${fmt.n(p.data.share, 1)}%` : '' },
      grid: { left: 40, right: mini ? 20 : 60, top: 24, bottom: 34 },
      xAxis: { ...axisStyle, name: '相對強度 →', nameLocation: 'end', nameTextStyle: { color: CH.ink3, fontSize: 11 }, scale: true, splitLine: { show: false } },
      yAxis: { ...axisStyle, name: '動能 ↑', nameTextStyle: { color: CH.ink3, fontSize: 11 }, scale: true, splitLine: { show: false } },
      graphic: mini ? [] : [
        { type: 'text', left: '60%', top: 10, style: { text: '領先', fill: 'rgba(255,77,109,.8)', fontSize: 14, fontWeight: 700 } },
        { type: 'text', left: '8%', top: 10, style: { text: '改善', fill: 'rgba(62,224,255,.8)', fontSize: 14, fontWeight: 700 } },
        { type: 'text', left: '8%', bottom: 40, style: { text: '落後', fill: 'rgba(46,229,157,.8)', fontSize: 14, fontWeight: 700 } },
        { type: 'text', left: '60%', bottom: 40, style: { text: '轉弱', fill: 'rgba(255,180,84,.8)', fontSize: 14, fontWeight: 700 } },
      ],
      series: [...lines, scatter, { type: 'line', markLine: { silent: true, symbol: 'none', lineStyle: { color: 'rgba(255,255,255,.25)', type: 'dashed' }, data: [{ xAxis: 100 }, { yAxis: 100 }], label: { show: false } }, data: [] }],
    });
    if (c) c.off('click').on('click', p => { if (p.data && p.data.gid) location.hash = '#industry/group/' + p.data.gid; });
  }

  function renderThemeStrip(th) {
    const el = $('#themeStrip'); if (!th || !th.themes || !th.themes.length) { el.innerHTML = '<div class="empty">尚無題材資料</div>'; return; }
    el.innerHTML = `<div class="tiles">` + th.themes.slice(0, 8).map(t => `<div class="tile" onclick="location.hash='#themes/${t.id}'"><div class="t">${fmt.esc(t.name)}</div><div class="m">${t.n} 檔 · 佔比 ${fmt.n(t.share, 1)}% · 新聞 ${t.news7}</div><div class="v"><span style="color:${t.heat >= 70 ? CH.up : t.heat >= 45 ? CH.amber : CH.ink2}">熱度 ${t.heat}</span> <small class="${fmt.cls(t.chg_pct)}" style="font-size:12px">${fmt.pct(t.chg_pct)}</small></div></div>`).join('') + '</div>';
  }

  const CAND_COLS = [
    ['grade', '判定', r => `<span class="grade ${r.grade || 'W'}">${r.grade ? r.grade + ' ' + r.verdict : r.verdict}</span>`, 'l'],
    ['code', '代號', r => `<span class="mono">${r.code}</span>`, 'l'], ['name', '簡稱', r => `<b>${fmt.esc(r.name)}</b>`, 'l'], ['group', '族群', r => fmt.esc(r.group), 'l'],
    ['close', '收盤', r => `<span class="num">${fmt.n(r.close)}</span>`], ['chg_pct', '漲跌', r => `<span class="num ${fmt.cls(r.chg_pct)}">${fmt.pct(r.chg_pct, 2)}</span>`],
    ['tech_score', '技術分', r => `<span class="num">${fmt.n(r.tech_score, 0)}</span>`], ['pe', '本益比', r => `<span class="num">${r.pe ? fmt.n(r.pe, 1) : '—'}</span>`],
    ['pe_percentile', '同業分位', r => `<span class="num">${r.pe_percentile != null ? fmt.n(r.pe_percentile, 0) + '%' : '—'}</span>`],
    ['rev_yoy', '營收YoY', r => `<span class="num ${fmt.cls(r.rev_yoy)}">${fmt.pct(r.rev_yoy)}</span>`],
    ['momentum_score', '動能分', r => `<span class="num">${r.momentum_score != null ? fmt.n(r.momentum_score, 0) : '—'}</span>`],
    ['trust_net', '投信', r => `<span class="num ${fmt.cls(r.trust_net)}">${r.trust_net != null ? fmt.lot(r.trust_net / 1000) : '—'}</span>`],
    ['foreign_net', '外資', r => `<span class="num ${fmt.cls(r.foreign_net)}">${r.foreign_net != null ? fmt.lot(r.foreign_net / 1000) : '—'}</span>`],
    ['stop', '停損', r => `<span class="num">${fmt.n(r.stop)}</span>`], ['rr', '風報比', r => `<span class="num">${r.rr != null ? fmt.n(r.rr, 1) : '—'}</span>`],
  ];
  let candSort = { key: null, dir: 1 };
  function renderCandidates(cands) {
    if (!cands) return;
    let rows = cands.slice();
    if (candSort.key) rows.sort((a, b) => { const x = a[candSort.key], y = b[candSort.key]; if (x == null) return 1; if (y == null) return -1; return (x > y ? 1 : x < y ? -1 : 0) * candSort.dir; });
    $('#candTable thead').innerHTML = '<tr>' + CAND_COLS.map(c => `<th class="${c[3] || ''}" data-k="${c[0]}">${c[1]}${candSort.key === c[0] ? (candSort.dir > 0 ? ' ▲' : ' ▼') : ''}</th>`).join('') + '</tr>';
    $('#candBody').innerHTML = rows.slice(0, 60).map(r => `<tr data-code="${r.code}">` + CAND_COLS.map(c => `<td class="${c[3] || ''}">${c[2](r)}</td>`).join('') + '</tr>').join('');
    $$('#candTable th').forEach(th => th.onclick = () => { const k = th.dataset.k; candSort = { key: k, dir: candSort.key === k ? -candSort.dir : -1 }; renderCandidates(cands); });
    $$('#candBody tr').forEach(tr => tr.onclick = () => goStock(tr.dataset.code));
    $('#candCards').innerHTML = rows.slice(0, 30).map(r => `<div class="scard" onclick="goStock('${r.code}')"><div class="h"><b>${fmt.esc(r.name)} <span class="mono muted">${r.code}</span></b><span class="grade ${r.grade || 'W'}">${r.grade ? r.grade + ' ' + r.verdict : r.verdict}</span></div><div class="r"><span>${fmt.esc(r.group)}</span><span class="num">${fmt.n(r.close)}</span><span class="num ${fmt.cls(r.chg_pct)}">${fmt.pct(r.chg_pct, 2)}</span><span>技術 ${fmt.n(r.tech_score, 0)}</span><span>PE ${r.pe ? fmt.n(r.pe, 1) : '—'}</span></div></div>`).join('');
  }

  function renderBreadth(heat) {
    const b = heat && heat.breadth; if (!b) return empty('breadth');
    chart('breadth', { tooltip: { ...tip }, grid: { left: 90, right: 30, top: 10, bottom: 20 },
      xAxis: { ...axisStyle, max: 100, splitLine: { show: false } }, yAxis: { ...axisStyle, type: 'category', data: ['站上 MA20', '站上 MA60', '60 日新高', 'A / B 級'], axisLabel: { color: CH.ink2 } },
      series: [{ type: 'bar', barWidth: 16, data: [b.pct_above_ma20, b.pct_above_ma60, b.n ? b.new_high_60 / b.n * 100 : 0, b.n ? (b.grade_a + b.grade_b) / b.n * 100 : 0].map(v => ({ value: +(v || 0).toFixed(1), itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [{ offset: 0, color: '#8b7bff' }, { offset: 1, color: '#3ee0ff' }]), borderRadius: 4 } })), label: { show: true, position: 'right', color: '#e8eeff', formatter: '{c}%', fontFamily: 'JetBrains Mono' } }] });
  }
  function renderTrust(trust, cands) {
    if (!trust || !trust.length) return empty('trust');
    const names = {}; (cands || []).forEach(c => { names[c.code] = c.name; });
    const rows = trust.slice(0, 10);
    const c = chart('trust', { tooltip: { ...tip, formatter: p => `<b>${p.name}</b><br>連續 ${rows[p.dataIndex].streak_days} 天，累計 ${fmt.lot(rows[p.dataIndex].accumulated / 1000)}` }, grid: { left: 100, right: 40, top: 6, bottom: 20 },
      xAxis: { ...axisStyle, splitLine: { show: false }, axisLabel: { show: false } }, yAxis: { ...axisStyle, type: 'category', inverse: true, data: rows.map(r => `${names[r.code] || r.code} ${r.code}`), axisLabel: { color: CH.ink2, fontSize: 12 } },
      series: [{ type: 'bar', barWidth: 12, data: rows.map(r => ({ value: r.streak_days, code: r.code, itemStyle: { color: '#ffb454', borderRadius: 4 } })), label: { show: true, position: 'right', color: '#e8eeff', formatter: p => p.value + ' 天', fontFamily: 'JetBrains Mono', fontSize: 11 } }] });
    if (c) c.off('click').on('click', p => goStock(p.data.code));
  }
  function renderGval(gval) {
    if (!gval || !gval.length) return empty('gval');
    const rows = gval.filter(g => g.metric === 'pe' && g.group_median && !g.group_id.startsWith('ind_')).sort((a, b) => b.group_median - a.group_median).slice(0, 12);
    const c = chart('gval', { tooltip: { ...tip, formatter: p => `<b>${p.name}</b><br>本益比中位數 ${fmt.n(p.value, 1)}（n=${rows[p.dataIndex].group_n}）` }, grid: { left: 110, right: 40, top: 6, bottom: 20 },
      xAxis: { ...axisStyle, splitLine: { show: false } }, yAxis: { ...axisStyle, type: 'category', inverse: true, data: rows.map(r => r.group_name), axisLabel: { color: CH.ink2, fontSize: 12 } },
      series: [{ type: 'bar', barWidth: 12, data: rows.map(r => ({ value: r.group_median, gid: r.group_id, itemStyle: { color: '#8b7bff', borderRadius: 4 } })), label: { show: true, position: 'right', color: '#e8eeff', formatter: p => fmt.n(p.value, 1), fontFamily: 'JetBrains Mono', fontSize: 11 } }] });
    if (c) c.off('click').on('click', p => { location.hash = '#industry/group/' + p.data.gid; });
  }

  // ---------------------------------------------------------------- 資金流向
  async function renderFlow() {
    const [f3, gt, conc] = await Promise.all([load('flow_v3'), load('groups_today'), load('concentration')]);
    let trail = 10;
    renderRRG('rrg', f3 && f3.rrg, trail, false);
    $$('#rrgTrail button').forEach(b => b.onclick = () => { $$('#rrgTrail button').forEach(x => x.classList.toggle('on', x === b)); trail = +b.dataset.v; renderRRG('rrg', f3 && f3.rrg, trail, false); });
    renderSankey(f3 && f3.sankey);
    renderRiver(f3 && f3.share);
    renderInstGroups(gt);
    renderConc(conc);
  }
  function renderSankey(sk) {
    if (!sk || !sk.links || !sk.links.length) return empty('sankey');
    const c = chart('sankey', { tooltip: { ...tip, formatter: p => p.dataType === 'edge' ? `${p.data.source} → ${p.data.target}<br>${fmt.yi(p.data.value)}` : `<b>${p.name}</b>` },
      series: [{ type: 'sankey', left: 10, right: 130, top: 10, bottom: 10, nodeWidth: 14, nodeGap: 8, nodeAlign: 'left', layoutIterations: 32, emphasis: { focus: 'adjacency' },
        data: sk.nodes.map((n, i) => ({ name: n.name, code: n.code, gid: n.group_id, itemStyle: { color: n.depth === 0 ? '#3ee0ff' : n.depth === 1 ? '#8b7bff' : n.depth === 2 ? '#ffb454' : '#c3ff5b', borderColor: 'transparent' } })),
        links: sk.links.map(l => ({ ...l, lineStyle: { color: 'gradient', opacity: .35 } })),
        label: { color: '#e8eeff', fontSize: 12, textShadowColor: '#000', textShadowBlur: 3 }, lineStyle: { curveness: .5 } }] });
    if (c) c.off('click').on('click', p => { if (p.dataType === 'node') { if (p.data.code) goStock(p.data.code); else if (p.data.gid) location.hash = '#industry/group/' + p.data.gid; } });
  }
  function renderRiver(sh) {
    if (!sh || !sh.series || !sh.series.length) return empty('river');
    const data = []; sh.series.forEach(s => s.values.forEach((v, i) => data.push([sh.dates[i], v || 0, s.name])));
    chart('river', { tooltip: { ...tip, trigger: 'axis', axisPointer: { type: 'line' }, formatter: ps => `<b>${ps[0].value[0]}</b><br>` + ps.sort((a, b) => b.value[1] - a.value[1]).slice(0, 10).map(p => `${p.marker}${p.value[2]} ${fmt.n(p.value[1], 1)}%`).join('<br>') },
      legend: { show: false }, singleAxis: { type: 'time', ...axisStyle, top: 10, bottom: 30, axisLabel: { color: CH.ink3, formatter: v => new Date(v).toISOString().slice(5, 10) } },
      color: PALETTE, series: [{ type: 'themeRiver', emphasis: { itemStyle: { shadowBlur: 20, shadowColor: 'rgba(0,0,0,.6)' } }, label: { color: '#e8eeff', fontSize: 11, textShadowColor: '#000', textShadowBlur: 3 }, data }] });
  }
  function renderInstGroups(gt) {
    if (!gt || !gt.length) return empty('instGroups');
    const rows = gt.filter(g => !g.group_id.startsWith('ind_')).map(g => ({ ...g, total: (g.foreign_net || 0) + (g.trust_net || 0) + (g.dealer_net || 0) })).sort((a, b) => b.total - a.total);
    const top = rows.slice(0, 8).concat(rows.slice(-6));
    const c = chart('instGroups', { tooltip: { ...tip, trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: ps => `<b>${ps[0].name}</b><br>` + ps.map(p => `${p.marker}${p.seriesName} ${fmt.lot(p.value / 1000)}`).join('<br>') },
      legend: { textStyle: { color: CH.ink2 }, top: 0 }, grid: { left: 100, right: 20, top: 30, bottom: 20 },
      xAxis: { ...axisStyle, axisLabel: { formatter: v => fmt.lot(v / 1000), color: CH.ink3 } }, yAxis: { ...axisStyle, type: 'category', inverse: true, data: top.map(g => g.group_name), axisLabel: { color: CH.ink2 } },
      series: [['外資', 'foreign_net', '#3ee0ff'], ['投信', 'trust_net', '#ffb454'], ['自營', 'dealer_net', '#8b7bff']].map(([n, k, col]) => ({ name: n, type: 'bar', stack: 'a', barWidth: 14, data: top.map(g => ({ value: g[k] || 0, gid: g.group_id })), itemStyle: { color: col } })) });
    if (c) c.off('click').on('click', p => { location.hash = '#industry/group/' + p.data.gid; });
  }
  function renderConc(conc) {
    if (!conc || !conc.length) return empty('conc');
    chart('conc', { tooltip: { ...tip, trigger: 'axis' }, grid: { left: 50, right: 20, top: 30, bottom: 30 }, legend: { textStyle: { color: CH.ink2 }, top: 0 },
      xAxis: { ...axisStyle, type: 'category', data: conc.map(r => r.date), axisLabel: { color: CH.ink3, formatter: v => v.slice(5) } }, yAxis: { ...axisStyle, scale: true, axisLabel: { formatter: '{value}%' } },
      series: [{ name: '前五族群佔比', type: 'line', data: conc.map(r => r.top_share), smooth: .3, showSymbol: false, lineStyle: { color: '#3ee0ff', width: 2 }, areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(62,224,255,.35)' }, { offset: 1, color: 'rgba(62,224,255,0)' }]) } },
        { name: '20 日均', type: 'line', data: conc.map(r => r.top_share_ma20), smooth: .3, showSymbol: false, lineStyle: { color: '#ffb454', width: 1.5, type: 'dashed' } }] });
  }

  // ---------------------------------------------------------------- 題材
  async function renderThemes() {
    const th = await load('themes'); if (!th || !th.themes || !th.themes.length) { empty('themeMap'); return; }
    $('#themeNote').textContent = th.note || '';
    const data = th.themes.map(t => ({ name: t.name, value: t.turnover, id: t.id, heat: t.heat, chg: t.chg_pct, share: t.share, news7: t.news7, itemStyle: { color: t.heat >= 75 ? 'rgba(255,77,109,.85)' : t.heat >= 60 ? 'rgba(255,143,171,.75)' : t.heat >= 45 ? 'rgba(139,123,255,.7)' : t.heat >= 30 ? 'rgba(62,224,255,.55)' : 'rgba(110,126,163,.5)' } }));
    const c = chart('themeMap', { tooltip: { ...tip, formatter: p => `<b>${p.name}</b><br>熱度 ${p.data.heat} · 成交值 ${fmt.yi(p.value)}（${fmt.n(p.data.share, 1)}%）<br>平均漲跌 <span style="color:${upDown(p.data.chg)}">${fmt.pct(p.data.chg)}</span> · 近 7 天新聞 ${p.data.news7}` },
      series: [{ type: 'treemap', roam: false, nodeClick: false, breadcrumb: { show: false }, top: 0, left: 0, width: '100%', height: '100%', label: { formatter: p => `${p.name}\n熱度 ${p.data.heat} · ${fmt.pct(p.data.chg)}`, fontSize: 13, color: '#fff', textShadowColor: '#000', textShadowBlur: 4 }, itemStyle: { borderColor: '#0b1224', borderWidth: 3, gapWidth: 3 }, data }] });
    if (c) c.off('click').on('click', p => { if (p.data && p.data.id) location.hash = '#themes/' + p.data.id; });
    const sel = location.hash.split('/')[1];
    renderThemeDetail(th, sel || th.themes[0].id);
  }
  function renderThemeDetail(th, id) {
    const t = th.themes.find(x => x.id === id) || th.themes[0]; if (!t) return;
    const el = $('#themeDetail');
    el.innerHTML = `<div class="grid g12"><div class="card"><h3>${fmt.esc(t.name)} <small>${fmt.esc(t.desc || '')}</small></h3>
      <div class="kvs" style="margin:10px 0"><div class="k"><div class="l">熱度</div><div class="v" style="color:${t.heat >= 70 ? CH.up : CH.amber}">${t.heat}</div></div><div class="k"><div class="l">成交值佔比</div><div class="v">${fmt.n(t.share, 1)}%</div></div><div class="k"><div class="l">5 日 vs 60 日</div><div class="v ${fmt.cls(t.flow_z)}">${t.flow_z != null ? (t.flow_z > 0 ? '+' : '') + t.flow_z.toFixed(1) + 'σ' : '—'}</div></div><div class="k"><div class="l">法人 5 日</div><div class="v ${fmt.cls(t.inst5)}">${t.inst5 != null ? fmt.lot(t.inst5 / 1000) : '—'}</div></div><div class="k"><div class="l">新聞 7 天</div><div class="v">${t.news7}</div></div></div>
      <div id="themeSeries" class="chart short"></div></div>
      <div class="card"><h3>成員 <small>依成交值；一檔可屬多題材</small></h3><div class="tw"><table><thead><tr><th class="l">代號</th><th class="l">簡稱</th><th>漲跌</th><th>成交值</th><th>法人</th></tr></thead><tbody>${t.members.map(m => `<tr onclick="goStock('${m.code}')"><td class="l mono">${m.code}</td><td class="l"><b>${fmt.esc(m.name)}</b></td><td class="num ${fmt.cls(m.chg_pct)}">${fmt.pct(m.chg_pct, 2)}</td><td class="num">${fmt.yi(m.turnover)}</td><td class="num ${fmt.cls(m.inst_net)}">${m.inst_net != null ? fmt.lot(m.inst_net / 1000) : '—'}</td></tr>`).join('')}</tbody></table></div></div></div>`;
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
        visualMap: { min: lim[0], max: lim[1], calculable: false, orient: 'vertical', right: 0, top: 'center', textStyle: { color: CH.ink3 }, inRange: { color: isWin ? ['#0f172b', '#8b7bff', '#ff4d6d'] : ['#2ee59d', '#0f172b', '#ff4d6d'] } },
        series: [{ type: 'heatmap', data: data.map(d => [d[0], d[1], d[2] == null ? null : +d[2].toFixed(1), d[3]]), label: { show: true, color: '#e8eeff', fontSize: 11, fontFamily: 'JetBrains Mono', formatter: p => p.data[2] == null ? '' : (isWin ? p.data[2] : (p.data[2] > 0 ? '+' : '') + p.data[2]) }, itemStyle: { borderColor: '#0b1224', borderWidth: 2, borderRadius: 3 }, emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,.6)' } } }] });
      if (c) c.off('click').on('click', p => drill(p.data[3]));
      $('#seasonNote').textContent = s3.note + `　大盤月報酬樣本 ${s3.benchmark_months} 個月。`;
      topThisMonth(P);
    };
    const drill = (cell) => {
      const det = (s3.detail || {})[cell.group_id] || {}; const years = Object.keys(det).sort();
      const vals = years.map(y => det[y][cell.month] ?? det[y][String(cell.month)]);
      $('#seasonDrillTitle').innerHTML = `${fmt.esc(cell.group_name)} · ${cell.month} 月逐年超額報酬 <small>紅正綠負</small>`;
      chart('seasonDrill', { tooltip: { ...tip, formatter: p => `${p.name} 年：${p.value != null ? fmt.pct(p.value) : '—'}` }, grid: { left: 50, right: 16, top: 16, bottom: 30 }, xAxis: { ...axisStyle, type: 'category', data: years, axisLabel: { color: CH.ink3 } }, yAxis: { ...axisStyle, axisLabel: { formatter: '{value}%' } },
        series: [{ type: 'bar', data: vals.map(v => ({ value: v, itemStyle: { color: v > 0 ? CH.up : CH.down, borderRadius: 3 } })), barWidth: '55%' }] });
    };
    const topThisMonth = (P) => {
      const m = new Date().getMonth() + 1;
      const rows = P.cells.filter(c => c.month === m && (c.avg_excess != null || c.avg_return != null)).map(c => ({ ...c, score: (c.excess_win_rate ?? c.win_rate ?? 0) * 0.6 + Math.max(-20, Math.min(20, c.avg_excess ?? c.avg_return ?? 0)) })).sort((a, b) => b.score - a.score).slice(0, 8);
      $('#seasonTop').innerHTML = rows.length ? `<div class="tw"><table><thead><tr><th class="l">族群</th><th>超額報酬</th><th>勝率</th><th>絕對報酬</th><th>樣本</th></tr></thead><tbody>${rows.map(r => `<tr onclick="location.hash='#industry/group/${r.group_id}'"><td class="l"><b>${fmt.esc(r.group_name)}</b></td><td class="num ${fmt.cls(r.avg_excess)}">${r.avg_excess != null ? fmt.pct(r.avg_excess) : '—'}</td><td class="num">${r.excess_win_rate ?? r.win_rate ?? '—'}%</td><td class="num ${fmt.cls(r.avg_return)}">${r.avg_return != null ? fmt.pct(r.avg_return) : '—'}</td><td class="num">${r.samples}</td></tr>`).join('')}</tbody></table></div><div class="note" style="margin-top:8px">${m} 月，依「超額報酬勝率 × 0.6 ＋ 平均超額」排序；樣本少於 3 年不列。</div>` : '<div class="empty">本月尚無足夠樣本</div>';
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
    const draw = () => { $('#evList').innerHTML = items.filter(i => cat === 'all' || i.cat === cat).slice(0, 80).map(i => `<div class="ev"><a href="${fmt.esc(i.url || '#')}" target="_blank" rel="noopener">${fmt.esc(i.title)}</a><div class="m"><span class="mono">${fmt.esc(String(i.date || '').slice(0, 10))}</span><span class="cat">${fmt.esc(i.cat)}</span><span>${fmt.esc(i.source || '')}</span>${i.code ? `<a onclick="goStock('${i.code}')" style="color:var(--cyan);cursor:pointer;display:inline">${i.code}</a>` : ''}</div></div>`).join('') || '<div class="empty">沒有這類事件</div>'; };
    $$('#evFilters button').forEach(b => b.onclick = () => { $$('#evFilters button').forEach(x => x.classList.toggle('on', x === b)); cat = b.dataset.c; draw(); });
    draw();
    $('#evToggle').onclick = () => $('#side').classList.toggle('open');
    $('#evClose').onclick = () => $('#side').classList.remove('open');
  }

  // ---------------------------------------------------------------- 搜尋
  async function initSearch() {
    const cands = await load('candidates'); const gd = await load('groups_detail');
    const idx = {}; (cands || []).forEach(c => { idx[c.code] = c.name; });
    Object.values(gd || {}).forEach(g => (g.members || []).forEach(m => { if (!idx[m.code]) idx[m.code] = m.name; }));
    const list = Object.entries(idx);
    const q = $('#q'), sg = $('#sugg');
    q.addEventListener('input', () => { const v = q.value.trim().toLowerCase(); if (!v) { sg.style.display = 'none'; return; } const hits = list.filter(([c, n]) => c.startsWith(v) || (n || '').toLowerCase().includes(v)).slice(0, 12); sg.innerHTML = hits.map(([c, n]) => `<div data-c="${c}"><span class="code">${c}</span>${fmt.esc(n)}</div>`).join(''); sg.style.display = hits.length ? 'block' : 'none'; $$('div', sg).forEach(d => d.onclick = () => { sg.style.display = 'none'; q.value = ''; goStock(d.dataset.c); }); });
    q.addEventListener('keydown', e => { if (e.key === 'Enter') { const v = q.value.trim(); const hit = list.find(([c]) => c === v) || list.find(([c, n]) => (n || '') === v); if (hit) { sg.style.display = 'none'; q.value = ''; goStock(hit[0]); } } });
    document.addEventListener('click', e => { if (!e.target.closest('.search')) sg.style.display = 'none'; });
  }

  // ---------------------------------------------------------------- 啟動
  async function boot() {
    if (typeof echarts === 'undefined' || typeof LightweightCharts === 'undefined') { $('#banner').textContent = '圖表函式庫載入失敗（vendor/ 目錄缺檔），請重新整理。'; $('#banner').classList.add('on'); }
    const meta = await load('meta');
    if (meta) {
      $('#asof').textContent = `${meta.data_date || ''} 盤後 · T-1`;
      const gen = meta.generated_at ? new Date(meta.generated_at) : null;
      if (gen && (Date.now() - gen.getTime()) > 3 * 86400e3) { $('#banner').textContent = `資料已 ${Math.floor((Date.now() - gen.getTime()) / 86400e3)} 天沒更新，排程可能出了問題。`; $('#banner').classList.add('on'); }
      if (meta.demo) { $('#banner').textContent = '這是示範資料，不是真實行情。'; $('#banner').classList.add('on'); }
    }
    window.App = { load, chart, fmt, tip, axisStyle, CH, PALETTE, chgColor, upDown, empty, charts, goStock, D };
    await Promise.all([renderEvents(), initSearch()]);
    await route();
  }
  boot();
})();
