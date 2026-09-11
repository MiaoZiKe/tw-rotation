/* 台股資金輪動儀表板 v2 — 前端邏輯
 * 前端只畫圖不運算：所有數字來自 data/*.json（build_payload.py 產出）。
 * 路由用 hash：#overview / #flow / #stock / #stock/2330 / #chain / #season
 */
'use strict';

// ------------------------------------------------------------------ 工具
const CSS = k => getComputedStyle(document.documentElement).getPropertyValue(k).trim();
const C = () => ({rise: CSS('--rise'), fall: CSS('--fall'), accent: CSS('--accent'), info: CSS('--info'),
  ink: CSS('--ink'), ink2: CSS('--ink-2'), ink3: CSS('--ink-3'), line: CSS('--line'), surface: CSS('--surface'), s2: CSS('--surface-2')});
const isNum = v => v !== null && v !== undefined && !Number.isNaN(v);
const fmt = (v, d = 2) => isNum(v) ? Number(v).toLocaleString('zh-TW', {minimumFractionDigits: d, maximumFractionDigits: d}) : '—';
const fmtInt = v => isNum(v) ? Math.round(v).toLocaleString('zh-TW') : '—';
const toYi = v => isNum(v) ? (v / 1e8).toFixed(1) + ' 億' : '—';
const toLots = v => isNum(v) ? Math.round(v / 1000).toLocaleString('zh-TW') : '—';
const sign = (v, d = 2) => isNum(v) ? (v > 0 ? '+' : '') + fmt(v, d) : '—';
const cls = v => v > 0 ? 'up' : (v < 0 ? 'down' : '');
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
const $ = id => document.getElementById(id);

const charts = {};
function mk(id, opt, {clear = false} = {}) {
  const el = $(id); if (!el) return null;
  let c = charts[id];
  if (!c) { c = echarts.init(el, null, {renderer: 'canvas'}); charts[id] = c; }
  const k = C();
  const base = {
    textStyle: {fontFamily: '"Noto Sans TC", sans-serif', color: k.ink2},
    grid: {left: 8, right: 16, top: 24, bottom: 8, containLabel: true},
    tooltip: {backgroundColor: k.surface, borderColor: k.line, textStyle: {color: k.ink, fontSize: 12}, confine: true},
    animationDuration: 300,
  };
  c.setOption(Object.assign({}, base, opt), {notMerge: clear || true});
  return c;
}
addEventListener('resize', () => Object.values(charts).forEach(c => c.resize()));
const load = n => fetch(`data/${n}.json?v=${Date.now()}`).then(r => r.ok ? r.json() : null).catch(() => null);

// 紅漲綠跌，強度隨漲跌幅遞增
function heatColor(chg, max = 3) {
  if (!isNum(chg)) return '#8a8f99';
  const t = Math.min(Math.abs(chg) / max, 1);
  const grey = [138, 143, 153], mix = (a, b) => a.map((v, i) => Math.round(v + (b[i] - v) * t));
  return `rgb(${(chg >= 0 ? mix(grey, [196, 53, 60]) : mix(grey, [14, 143, 91])).join(',')})`;
}

// ------------------------------------------------------------------ 狀態與路由
const D = {};          // 所有載入的資料
let route = {view: 'overview', code: null};

function go(view, code) {
  location.hash = code ? `${view}/${code}` : view;
}
function parseHash() {
  const h = location.hash.replace('#', '') || 'overview';
  const [view, code] = h.split('/');
  return {view: ['overview', 'flow', 'stock', 'chain', 'season'].includes(view) ? view : 'overview', code: code || null};
}
function render() {
  route = parseHash();
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('on', t.dataset.v === route.view));
  document.querySelectorAll('.view').forEach(v => v.classList.toggle('on', v.id === 'v-' + route.view));
  if (route.view === 'stock') {
    if (route.code) openStock(route.code); else showStockList();
  }
  // 圖表在隱藏的分頁裡 init 會是 0 寬，切換後補 resize
  setTimeout(() => Object.values(charts).forEach(c => c.resize()), 30);
  window.scrollTo({top: 0});
}
addEventListener('hashchange', render);
document.querySelectorAll('.tab').forEach(t => t.onclick = () => go(t.dataset.v));

// ------------------------------------------------------------------ 主流程
(async function main() {
  if (typeof echarts === 'undefined') {
    const b = $('banner'); b.className = 'banner on';
    b.innerHTML = '<b>圖表函式庫沒有載入（vendor/echarts.min.js）。</b>數字仍會顯示，但所有圖表會是空的。請確認 repo 裡有 site/vendor/echarts.min.js，或重新整理。';
    window.echarts = {init: () => ({setOption(){}, resize(){}, on(){}, off(){}, dispose(){}})};
  }
  const names = ['meta', 'market_heat', 'groups_today', 'rotation', 'relative_strength', 'concentration',
    'seasonality', 'candidates', 'news', 'trust_streak', 'groups_detail', 'group_valuation',
    'fundamental', 'broker_views', 'supply_chain'];
  const res = await Promise.all(names.map(load));
  names.forEach((n, i) => D[n] = res[i]);

  renderMeta(D.meta);
  if (!D.meta && location.protocol === 'file:') {
    $('banner').className = 'banner on';
    $('banner').innerHTML = '<b>這個頁面不能用滑鼠雙擊開啟。</b>請用 <code>python -m http.server -d site 8000</code> 開 localhost:8000，或用 GitHub Pages 網址。';
    return;
  }
  if (!D.meta || D.meta.status !== 'ok') {
    document.querySelectorAll('.view').forEach(v => v.innerHTML = '<div class="empty">資料湖還是空的。先跑一次每日管線，或執行歷史回補。</div>');
    return;
  }
  D.candIdx = Object.fromEntries((D.candidates || []).map(c => [c.code, c]));
  D.fundIdx = Object.fromEntries((D.fundamental || []).map(f => [f.code, f]));

  renderHeat(D.market_heat);
  renderTreemap(D.groups_today);
  renderQuadrant(D.rotation, D.relative_strength, D.groups_today);
  renderCandidates(D.candidates);
  renderInst(D.groups_today);
  renderRS(D.relative_strength);
  renderConcentration(D.concentration);
  renderTrust(D.trust_streak);
  renderGroupValuation(D.group_valuation);
  renderStockTable(D.candidates);
  renderChain(D.supply_chain);
  renderSeason(D.seasonality);
  renderEvents(D.news, D.broker_views);
  setupSearch();
  render();
})();

// ------------------------------------------------------------------ 頂部
function renderMeta(m) {
  if (!m) return;
  $('stampTop').textContent = (m.data_date || '—') + '　盤後 T-1';
  $('evStamp').textContent = m.data_date || '';
  const warn = [];
  if (m.demo) warn.push('<b>這是示範資料，不是真實行情。</b>跑過一次每日管線後就會被真實資料覆蓋。');
  if (m.data_date) {
    const age = Math.floor((Date.now() - new Date(m.data_date).getTime()) / 864e5);
    if (age > 4) warn.push(`資料已經 ${age} 天沒更新，排程可能失效 —— 到 Actions 檢查每日管線。`);
  }
  if (m.groups_health && m.groups_health.is_stale) warn.push(`族群對照表上次檢視是 ${m.groups_health.reviewed}，該複查成分股了。`);
  if (m.last_run_errors && m.last_run_errors.length) warn.push(`上一輪有 ${m.last_run_errors.length} 個抓取錯誤：${esc(m.last_run_errors.slice(0, 2).join('；'))}`);
  if (warn.length) { $('banner').className = 'banner on'; $('banner').innerHTML = warn.join('<br>'); }
}

function renderHeat(h) {
  if (!h) return;
  const b = h.breadth || {};
  const volNote = (h.turnover && h.turnover_ma20) ? `20 日均量的 ${(h.turnover / h.turnover_ma20 * 100).toFixed(0)}%` : '';
  const adv = h.advancers || 0, dec = h.decliners || 0, tot = adv + dec + (h.unchanged || 0);
  const advPct = tot ? adv / tot * 100 : 0;
  const items = [
    ['加權指數', fmt(h.taiex, 0), sign(h.change), cls(h.change), 'taiex'],
    ['成交值', toYi(h.turnover), volNote, '', null],
    ['漲跌家數', `<span class="up">${fmtInt(adv)}</span> <span class="muted">/</span> <span class="down">${fmtInt(dec)}</span>`,
      `<div class="gauge"><i style="width:${advPct.toFixed(0)}%"></i></div>`, '', null],
    ['站上月線', isNum(b.pct_above_ma20) ? b.pct_above_ma20.toFixed(0) + '%' : '—',
      isNum(b.pct_above_ma60) ? `站上季線 ${b.pct_above_ma60.toFixed(0)}%` : '', isNum(b.pct_above_ma20) ? (b.pct_above_ma20 >= 50 ? 'up' : 'down') : '', null],
    ['前 5 族群佔比', isNum(h.top5_share) ? h.top5_share.toFixed(1) + '%' : '—', '越高＝資金越集中', '', null],
    ['進場等級', `<span class="up">A ${b.grade_a ?? 0}</span> <span class="muted">/</span> <span style="color:var(--info)">B ${b.grade_b ?? 0}</span>`,
      `共掃描 ${b.n ?? 0} 檔`, '', 'cands'],
  ];
  $('heat').innerHTML = items.map(([k, v, s, c, act]) =>
    `<div class="${act ? 'link' : ''}" data-act="${act || ''}"><dt>${k}</dt><dd class="${c}">${v}</dd><div class="sub">${s}</div></div>`).join('');
  $('heat').querySelectorAll('[data-act]').forEach(el => el.onclick = () => {
    if (el.dataset.act === 'taiex') openTaiex();
    if (el.dataset.act === 'cands') document.getElementById('cand').scrollIntoView({behavior: 'smooth'});
  });
}

// ------------------------------------------------------------------ 熱力圖 + 下鑽
function renderTreemap(g) {
  if (!g || !g.length) return;
  const c = mk('treemap', {
    tooltip: {formatter: p => { const d = p.data; return `<b>${d.name}</b><br>成交值 ${toYi(d.value)}　佔比 ${fmt(d.share)}%<br>漲跌 ${sign(d.chg)}%　成分 ${d.n} 檔（漲 ${d.adv} / 跌 ${d.dec}）<br><span style="color:${C().accent}">點擊看成分股</span>`; }},
    series: [{type: 'treemap', roam: false, nodeClick: false, breadcrumb: {show: false}, left: 0, top: 0, right: 0, bottom: 0,
      label: {show: true, formatter: p => `${p.data.name}\n${sign(p.data.chg, 1)}%`, fontSize: 12, color: '#fff', textShadowColor: 'rgba(0,0,0,.5)', textShadowBlur: 3},
      itemStyle: {borderColor: C().surface, borderWidth: 2, gapWidth: 2},
      data: g.map(r => ({name: r.group_name, value: Math.max(r.turnover || 0, 1), chg: r.chg_pct, share: r.turnover_share,
        n: r.constituents, adv: r.advancers, dec: r.decliners, gid: r.group_id, itemStyle: {color: heatColor(r.chg_pct)}}))}]
  });
  c.off('click'); c.on('click', p => p.data && p.data.gid && openDrill(p.data.gid, p.data.name, 'drill'));
}

let drillState = {gid: null, market: 'all', sort: 'turnover'};
function openDrill(gid, name, target = 'drill', sortKey = 'turnover') {
  const box = $(target);
  const gd = D.groups_detail && D.groups_detail[gid];
  if (!gd) return;
  if (drillState.gid === gid && box.classList.contains('on') && target === 'drill') { box.classList.remove('on'); drillState.gid = null; return; }
  drillState = {gid, market: 'all', sort: sortKey};
  const draw = () => {
    let rows = gd.members.slice();
    if (drillState.market !== 'all') rows = rows.filter(m => (D.candIdx[m.code] || {}).market === drillState.market);
    const k = drillState.sort;
    rows.sort((a, b) => ((b[k] ?? -Infinity) - (a[k] ?? -Infinity)));
    const n = rows.length;
    box.innerHTML = `<div class="drill-h"><h3>${esc(name || gd.group_name)}</h3><span class="muted">${n} 檔</span>
      <span class="seg" data-f="market"><button data-v="all" class="${drillState.market === 'all' ? 'on' : ''}">全部</button><button data-v="TWSE" class="${drillState.market === 'TWSE' ? 'on' : ''}">上市</button><button data-v="TPEX" class="${drillState.market === 'TPEX' ? 'on' : ''}">上櫃</button></span>
      <span class="seg" data-f="sort"><button data-v="turnover" class="${k === 'turnover' ? 'on' : ''}">成交值</button><button data-v="chg_pct" class="${k === 'chg_pct' ? 'on' : ''}">漲幅</button><button data-v="trust" class="${k === 'trust' ? 'on' : ''}">投信</button><button data-v="foreign" class="${k === 'foreign' ? 'on' : ''}">外資</button><button data-v="tech_score" class="${k === 'tech_score' ? 'on' : ''}">技術分</button></span>
      <button class="x" aria-label="關閉">×</button></div>
      <div class="tw" style="max-height:340px"><table><thead><tr><th>代號</th><th>簡稱</th><th class="num">收盤</th><th class="num">漲跌</th><th class="num">成交值</th><th class="num">外資</th><th class="num">投信</th><th>判定</th><th class="num">同業分位</th></tr></thead><tbody>
      ${rows.map(m => `<tr data-code="${m.code}" class="${m.has_page ? '' : 'nopage'}"><td class="code">${m.code}<span class="mkt">${(D.candIdx[m.code] || {}).market === 'TPEX' ? '櫃' : ''}</span></td><td>${esc(m.name)}</td><td class="num mono">${fmt(m.close)}</td><td class="num mono ${cls(m.chg_pct)}">${sign(m.chg_pct)}%</td><td class="num mono">${toYi(m.turnover)}</td><td class="num mono ${cls(m.foreign)}">${toLots(m.foreign)}</td><td class="num mono ${cls(m.trust)}">${toLots(m.trust)}</td><td>${verdictPill(m)}</td><td class="num mono">${pctCell(m.pe_percentile)}</td></tr>`).join('') || '<tr><td colspan="9" class="empty">沒有符合的標的</td></tr>'}
      </tbody></table></div>`;
    box.classList.add('on');
    box.querySelectorAll('.seg button').forEach(b => b.onclick = () => { drillState[b.parentElement.dataset.f] = b.dataset.v; draw(); });
    box.querySelector('.x').onclick = () => { box.classList.remove('on'); drillState.gid = null; };
    box.querySelectorAll('tbody tr[data-code]').forEach(tr => tr.onclick = () => go('stock', tr.dataset.code));
  };
  draw();
  box.scrollIntoView({behavior: 'smooth', block: 'nearest'});
}
const verdictPill = r => {
  if (!r || !r.verdict) return '<span class="pill no">—</span>';
  if (r.grade === 'A') return '<span class="pill a">A 進場</span>';
  if (r.grade === 'B') return '<span class="pill b">B 突破</span>';
  if (r.verdict.startsWith('不要')) return '<span class="pill no">不要碰</span>';
  return '<span class="pill w">觀望</span>';
};
const pctCell = v => isNum(v) ? `<span class="${v > 70 ? 'up' : (v < 30 ? 'down' : '')}">${v.toFixed(0)}%</span>` : '—';

// ------------------------------------------------------------------ 輪動象限
function renderQuadrant(rot, rs, g) {
  if (!rot || !rot.length) return;
  const rsIdx = Object.fromEntries((rs || []).map(r => [r.group_id, r]));
  const data = rot.filter(r => isNum(r.rotation)).map(r => {
    const s = rsIdx[r.group_id] || {};
    return {name: r.group_name, gid: r.group_id, value: [r.rotation, isNum(s.rs) ? s.rs : 0, Math.max(r.turnover || 1, 1)], share: r.turnover_share, chg: r.chg_pct};
  });
  const maxT = Math.max(...data.map(d => d.value[2]));
  const k = C();
  const c = mk('quadrant', {
    grid: {left: 8, right: 16, top: 26, bottom: 8, containLabel: true},
    tooltip: {formatter: p => `<b>${p.data.name}</b><br>資金流入 ${sign(p.data.value[0])} pp<br>相對大盤 ${sign(p.data.value[1])}%<br>佔比 ${fmt(p.data.share)}%`},
    xAxis: {type: 'value', name: '資金流入 →', nameTextStyle: {color: k.ink3, fontSize: 10}, axisLabel: {color: k.ink3, fontSize: 10}, splitLine: {lineStyle: {color: k.line}}},
    yAxis: {type: 'value', name: '相對強弱 ↑', nameTextStyle: {color: k.ink3, fontSize: 10}, axisLabel: {color: k.ink3, fontSize: 10, formatter: '{value}%'}, splitLine: {lineStyle: {color: k.line}}},
    series: [{type: 'scatter', data, symbolSize: d => 10 + Math.sqrt(d[2] / maxT) * 34,
      itemStyle: {color: p => heatColor(p.data.chg), opacity: .85, borderColor: k.surface, borderWidth: 1},
      label: {show: true, position: 'right', fontSize: 10, color: k.ink2, formatter: p => p.data.name}, labelLayout: {hideOverlap: true},
      markLine: {silent: true, symbol: 'none', lineStyle: {color: k.ink3, type: 'dashed', width: 1}, data: [{xAxis: 0}, {yAxis: 0}], label: {show: false}},
      markArea: {silent: true, itemStyle: {color: k.accent, opacity: .06}, data: [[{xAxis: 0, yAxis: 0}, {xAxis: 'max', yAxis: 'max'}]]}}]
  });
  c.off('click'); c.on('click', p => p.data && openDrill(p.data.gid, p.data.name, 'drill'));
}

// ------------------------------------------------------------------ 候選股
let ALL = [], sortKey = 'grade', sortDir = 1, cardLimit = 20;
const ASC = new Set(['pe_percentile', 'pe', 'code', 'grade']);
const gradeRank = g => g === 'A' ? 0 : g === 'B' ? 1 : 2;
function renderCandidates(rows) {
  ALL = rows || [];
  document.querySelectorAll('#cand th').forEach(th => th.onclick = () => { const k = th.dataset.k; if (sortKey === k) sortDir *= -1; else { sortKey = k; sortDir = ASC.has(k) ? 1 : -1; } drawCands(); });
  const sel = $('sortSel'); sel.onchange = () => { sortKey = sel.value; sortDir = ASC.has(sortKey) ? 1 : -1; cardLimit = 20; drawCands(); };
  drawCands();
}
function drawCands() {
  const rows = ALL.slice().sort((a, b) => {
    if (sortKey === 'grade') { const d = gradeRank(a.grade) - gradeRank(b.grade); return d !== 0 ? d * sortDir : (b.tech_score - a.tech_score); }
    const x = a[sortKey], y = b[sortKey];
    if (!isNum(x) && typeof x !== 'string') return 1; if (!isNum(y) && typeof y !== 'string') return -1;
    return typeof x === 'string' ? sortDir * x.localeCompare(y) : sortDir * (x - y);
  });
  $('candBody').innerHTML = rows.slice(0, 200).map(r => `<tr data-code="${r.code}">
    <td>${verdictPill(r)}</td><td class="code">${r.code}<span class="mkt">${r.market === 'TPEX' ? '櫃' : ''}</span></td><td>${esc(r.name)}</td><td class="muted">${esc(r.group)}</td>
    <td class="num mono">${fmt(r.close)}</td><td class="num mono ${cls(r.chg_pct)}">${sign(r.chg_pct)}%</td>
    <td class="num"><span class="bar" style="width:${Math.max(2, r.tech_score * .4)}px"></span><span class="mono">${r.tech_score.toFixed(0)}</span></td>
    <td class="muted" style="max-width:220px;overflow:hidden;text-overflow:ellipsis">${esc(r.verdict)}</td>
    <td class="num mono">${pctCell(r.pe_percentile)}</td><td class="num mono ${cls(r.rev_yoy)}">${isNum(r.rev_yoy) ? sign(r.rev_yoy, 0) + '%' : '—'}</td>
    <td class="num mono ${cls(r.trust_net)}">${toLots(r.trust_net)}</td><td class="num mono">${isNum(r.rr) ? r.rr.toFixed(1) : '—'}</td></tr>`).join('');
  $('candBody').querySelectorAll('tr').forEach(tr => tr.onclick = () => go('stock', tr.dataset.code));
  renderCards('candCards', rows);
}
function renderCards(id, all) {
  const el = $(id); if (!el) return;
  const rows = all.slice(0, cardLimit), more = all.length - rows.length;
  el.innerHTML = rows.map(r => `<div class="card" data-code="${r.code}"><div class="card-top"><div><div class="card-id">${r.code}<small>${esc(r.name)}</small></div><div class="card-g">${esc(r.group)}${r.market === 'TPEX' ? '　上櫃' : ''}</div></div>
    <div class="card-score">${r.tech_score.toFixed(0)}<span>技術分</span></div></div>
    <div class="card-chips">${verdictPill(r)} <span class="chip">收盤 <b>${fmt(r.close)}</b> <b class="${cls(r.chg_pct)}">${sign(r.chg_pct, 1)}%</b></span>
    ${isNum(r.pe_percentile) ? `<span class="chip">同業分位 <b>${r.pe_percentile.toFixed(0)}%</b></span>` : ''}
    ${isNum(r.rev_yoy) ? `<span class="chip">營收YoY <b class="${cls(r.rev_yoy)}">${sign(r.rev_yoy, 0)}%</b></span>` : ''}
    ${r.trust_net ? `<span class="chip">投信 <b>${toLots(r.trust_net)} 張</b></span>` : ''}
    ${isNum(r.rr) ? `<span class="chip">風報比 <b>${r.rr.toFixed(1)}</b></span>` : ''}</div></div>`).join('') || '<div class="empty">沒有標的</div>';
  if (more > 0) { const b = document.createElement('button'); b.className = 'more'; b.textContent = `再顯示 20 檔（還有 ${more} 檔）`; b.onclick = () => { cardLimit += 20; drawCands(); }; el.appendChild(b); }
  el.querySelectorAll('.card').forEach(c => c.onclick = () => go('stock', c.dataset.code));
}

// ------------------------------------------------------------------ 資金流向分頁
function renderInst(g) {
  if (!g || !g.length) return;
  const top = [...g].sort((a, b) => Math.abs((b.foreign_net || 0) + (b.trust_net || 0)) - Math.abs((a.foreign_net || 0) + (a.trust_net || 0))).slice(0, 12).reverse();
  const k = C();
  const s = (name, key, color) => ({name, type: 'bar', stack: 'i', itemStyle: {color}, data: top.map(d => d[key] ? Math.round(d[key] / 1000) : 0)});
  const c = mk('inst', {
    legend: {top: 0, textStyle: {color: k.ink2, fontSize: 11}, itemHeight: 8, itemWidth: 12},
    grid: {left: 8, right: 16, top: 30, bottom: 8, containLabel: true},
    tooltip: {trigger: 'axis', axisPointer: {type: 'shadow'}, valueFormatter: v => fmtInt(v) + ' 張'},
    xAxis: {type: 'value', axisLabel: {color: k.ink3, fontSize: 10}, splitLine: {lineStyle: {color: k.line}}},
    yAxis: {type: 'category', data: top.map(d => d.group_name), axisLabel: {color: k.ink2, fontSize: 11}, triggerEvent: true},
    series: [s('外資', 'foreign_net', '#c4353c'), s('投信', 'trust_net', '#d9a441'), s('自營', 'dealer_net', '#5b7fa8')]
  });
  c.off('click'); c.on('click', p => { const d = top[p.dataIndex] || top.find(x => x.group_name === p.value); if (d) openDrill(d.group_id, d.group_name, 'drillInst', 'trust'); });
}
function renderRS(rs) {
  if (!rs || !rs.length) return;
  const d = rs.filter(x => isNum(x.rs)).slice(0, 14).reverse(); const k = C();
  if (!d.length) { $('rs').innerHTML = '<div class="empty">大盤 20 日報酬還算不出來（需要 ^TWII 一年資料）</div>'; return; }
  mk('rs', {
    tooltip: {formatter: p => `<b>${p.name}</b><br>族群 ${fmt(d[p.dataIndex].ret)}%　大盤 ${fmt(d[p.dataIndex].market_ret)}%<br>超額 ${sign(p.value)}%`},
    xAxis: {type: 'value', axisLabel: {color: k.ink3, fontSize: 10}, splitLine: {lineStyle: {color: k.line}}},
    yAxis: {type: 'category', data: d.map(x => x.group_name), axisLabel: {color: k.ink2, fontSize: 11}},
    series: [{type: 'bar', data: d.map(x => ({value: x.rs, itemStyle: {color: x.rs >= 0 ? k.rise : k.fall}}))}]
  });
}
function renderConcentration(c) {
  if (!c || !c.length) return;
  const last = c[c.length - 1], k = C();
  const ma = last.top_share_ma20;
  const dir = isNum(ma) ? (last.top_share > ma + 2 ? '正在縮圈：資金集中到少數主流族群，強者恆強、但輪動風險升高' : last.top_share < ma - 2 ? '正在擴散：資金從主流流向其他族群，補漲或輪動進行中' : '持平：集中度沒有明顯變化') : '';
  $('concNote').innerHTML = `前 5 大族群吃掉的成交值佔比。目前 <b class="mono">${fmt(last.top_share, 1)}%</b>${isNum(ma) ? `（20 日均 ${fmt(ma, 1)}%）` : ''} —— ${dir}`;
  mk('concentration', {
    tooltip: {trigger: 'axis', valueFormatter: v => fmt(v) + '%'},
    xAxis: {type: 'category', data: c.map(d => d.date), axisLabel: {color: k.ink3, fontSize: 10}},
    yAxis: {type: 'value', scale: true, axisLabel: {color: k.ink3, fontSize: 10, formatter: '{value}%'}, splitLine: {lineStyle: {color: k.line}}},
    series: [{name: '前5族群佔比', type: 'line', showSymbol: false, smooth: true, lineStyle: {color: k.accent, width: 2}, areaStyle: {color: k.accent, opacity: .1}, data: c.map(d => d.top_share)},
      {name: '20日均', type: 'line', showSymbol: false, lineStyle: {color: k.ink3, width: 1, type: 'dashed'}, data: c.map(d => d.top_share_ma20)}]
  });
}
function renderTrust(t) {
  if (!t || !t.length) { $('trust').innerHTML = '<div class="empty">還沒有法人資料</div>'; return; }
  const d = t.slice(0, 10).reverse(), k = C();
  const c = mk('trust', {
    tooltip: {formatter: p => `<b>${p.name}</b><br>連買 ${p.value} 天　累計 ${toLots(d[p.dataIndex].accumulated)} 張`},
    xAxis: {type: 'value', axisLabel: {color: k.ink3, fontSize: 10}, splitLine: {lineStyle: {color: k.line}}},
    yAxis: {type: 'category', data: d.map(x => `${x.code} ${(D.candIdx[x.code] || {}).name || ''}`), axisLabel: {color: k.ink2, fontSize: 11}},
    series: [{type: 'bar', data: d.map(x => x.streak_days), itemStyle: {color: k.accent}}]
  });
  c.off('click'); c.on('click', p => go('stock', d[p.dataIndex].code));
}
function renderGroupValuation(gv) {
  if (!gv) return;
  const m = {pe: '本益比', pb_roe: 'PB + ROE', ps: '股價營收比'};
  $('gvalBody').innerHTML = gv.filter(g => g.group_id && !String(g.group_id).startsWith('ind_')).sort((a, b) => (b.group_n || 0) - (a.group_n || 0)).map(g => `<tr data-gid="${g.group_id}"><td>${esc(g.group_name)}</td><td><span class="ftag">${m[g.metric] || g.metric}</span></td><td class="num mono">${isNum(g.group_median) ? fmt(g.group_median, 1) : '<span class="muted">樣本不足</span>'}</td><td class="num mono">${g.group_n ?? '—'}</td><td class="num mono">${isNum(g.loss_ratio) ? g.loss_ratio.toFixed(0) + '%' : '—'}</td></tr>`).join('') || '<tr><td colspan="5" class="empty">財報回補完成後才有估值資料</td></tr>';
  $('gvalBody').querySelectorAll('tr[data-gid]').forEach(tr => tr.onclick = () => { go('overview'); setTimeout(() => openDrill(tr.dataset.gid, null, 'drill', 'tech_score'), 50); });
}

// ------------------------------------------------------------------ 個股清單與搜尋
function renderStockTable(rows) {
  const r = (rows || []).slice().sort((a, b) => (b.turnover || 0) - (a.turnover || 0));
  $('stockBody').innerHTML = r.map(x => `<tr data-code="${x.code}"><td class="code">${x.code}<span class="mkt">${x.market === 'TPEX' ? '櫃' : ''}</span></td><td>${esc(x.name)}</td><td class="muted">${esc(x.group)}</td><td class="num mono">${fmt(x.close)}</td><td class="num mono ${cls(x.chg_pct)}">${sign(x.chg_pct)}%</td><td>${verdictPill(x)}</td><td class="num mono">${x.tech_score.toFixed(0)}</td><td class="num mono">${isNum(x.momentum_score) ? x.momentum_score.toFixed(0) : '—'}</td></tr>`).join('');
  $('stockBody').querySelectorAll('tr').forEach(tr => tr.onclick = () => go('stock', tr.dataset.code));
  const el = $('stockCards'); el.innerHTML = r.slice(0, 40).map(x => `<div class="card" data-code="${x.code}"><div class="card-top"><div class="card-id">${x.code}<small>${esc(x.name)}</small></div><div>${verdictPill(x)}</div></div><div class="card-g">${esc(x.group)}　收盤 ${fmt(x.close)} <b class="${cls(x.chg_pct)}">${sign(x.chg_pct, 1)}%</b></div></div>`).join('');
  el.querySelectorAll('.card').forEach(c => c.onclick = () => go('stock', c.dataset.code));
}
function setupSearch() {
  const q = $('q'), box = $('sugg');
  const all = (D.candidates || []);
  q.oninput = () => {
    const v = q.value.trim().toLowerCase(); if (!v) { box.style.display = 'none'; return; }
    const hits = all.filter(c => c.code.startsWith(v) || (c.name || '').toLowerCase().includes(v)).slice(0, 10);
    box.innerHTML = hits.map(h => `<div data-code="${h.code}"><span class="code">${h.code}</span>${esc(h.name)}<span class="muted">${esc(h.group)}</span></div>`).join('') || '<div class="muted">找不到（只涵蓋有個股頁的標的）</div>';
    box.style.display = 'block';
    box.querySelectorAll('[data-code]').forEach(d => d.onclick = () => { box.style.display = 'none'; q.value = ''; go('stock', d.dataset.code); });
  };
  q.onkeydown = e => { if (e.key === 'Enter') { const v = q.value.trim(); if (D.candIdx[v]) { box.style.display = 'none'; q.value = ''; go('stock', v); } } if (e.key === 'Escape') box.style.display = 'none'; };
  document.addEventListener('click', e => { if (!e.target.closest('.search')) box.style.display = 'none'; });
}
function showStockList() { $('stockList').style.display = ''; $('stockPage').style.display = 'none'; }

// ------------------------------------------------------------------ 個股頁（K 線）
async function openStock(code) {
  $('stockList').style.display = 'none'; const pg = $('stockPage'); pg.style.display = ''; pg.innerHTML = '<div class="empty">載入中…</div>';
  const s = await load(`stock/${code}`);
  if (!s) { pg.innerHTML = `<button class="back" onclick="go('stock')">← 回清單</button><div class="empty">${code} 沒有個股頁 —— 目前只算成交值前 150 檔與族群成分股。</div>`; return; }
  const m = s.meta, sm = s.summary, v = s.verdict, f = s.fundamental || {}, k = C();
  const gcls = v.grade === 'A' ? 'a' : v.grade === 'B' ? 'b' : v.verdict.startsWith('不要') ? 'no' : '';
  const light = (t, l) => `<span class="light ${t === 1 ? 'g' : t === -1 ? 'r' : 'n'}">${l} ${t === 1 ? '多' : t === -1 ? '空' : '—'}</span>`;
  const metricName = {pe: '本益比', pb_roe: '股價淨值比', ps: '股價營收比'}[f.metric] || '本益比';
  pg.innerHTML = `
    <button class="back" onclick="go('stock')">← 回清單</button>
    <div class="stock-h" style="margin-top:10px"><h2>${m.code} ${esc(m.name)}</h2><span class="px ${cls(sm.chg_pct)}">${fmt(sm.close)} <small>${sign(sm.chg_pct)}%</small></span>
      <span class="chips">${(m.groups || []).map(g => `<span class="chip">${esc(g)}</span>`).join('')}<span class="chip">${m.market === 'TPEX' ? '上櫃' : '上市'}</span><span class="chip">資料 ${s.as_of}</span></span></div>
    <div class="verdict ${gcls}"><h3>${esc(v.verdict)}${v.grade ? `　<span class="pill ${v.grade === 'A' ? 'a' : 'b'}">${v.grade} 級</span>` : ''}</h3>
      <ol>${v.reasons.map(r => `<li>${esc(r)}</li>`).join('')}</ol>
      ${v.risk_text ? `<div class="risk"><b>風險：</b>${esc(v.risk_text)}${v.invalidation ? `　<b>失效條件：</b>${esc(v.invalidation)}` : ''}</div>` : ''}
      <div class="lights">${light(v.signals.trend, '日線結構')}${light(v.weekly.trend, '週線結構')}${light(v.signals.ma_align, '均線排列')}${v.weekly_note ? `<span class="muted" style="font-size:12px">${esc(v.weekly_note)}</span>` : ''}</div></div>
    <div class="panel"><div id="kline" class="chart" style="height:560px"></div>
      <div class="legend"><span><i style="background:${k.fall};opacity:.35"></i>需求區（支撐）</span><span><i style="background:${k.rise};opacity:.35"></i>供給區（壓力）</span><span><i style="background:${k.accent}"></i>停損 / 目標</span><span>▲ BOS　◆ CHoCH　↑ 假跌破</span></div></div>
    <div class="grid g-1-1" style="margin-top:14px">
      <div class="panel"><h3>基本面</h3><p class="note">${f.latest_period ? `財報到 ${f.latest_period}` : '財報回補完成後才有資料'}${f.rev_ym ? `　月營收到 ${f.rev_ym}` : ''}</p>
        <dl class="kv">
          <dt>近四季 EPS</dt><dd><b>${isNum(f.ttm_eps) ? fmt(f.ttm_eps) : '—'}</b>${f.ttm_complete === false ? ' <span class="muted">（四季不完整）</span>' : ''}</dd>
          <dt>${metricName}</dt><dd><b>${isNum(f.metric_value) ? fmt(f.metric_value, 1) : '—'}</b>${isNum(f.group_median) ? `　族群中位數 ${fmt(f.group_median, 1)}（n=${f.group_n}）` : ''}</dd>
          <dt>同業分位</dt><dd>${isNum(f.percentile) ? `<b class="${f.percentile > 70 ? 'up' : f.percentile < 30 ? 'down' : ''}">${f.percentile.toFixed(0)}%</b>　${f.percentile > 70 ? '比七成同業貴' : f.percentile < 30 ? '比七成同業便宜' : '在同業中段'}${f.thin_sample ? '　<span class="muted">樣本少</span>' : ''}` : '<span class="muted">樣本不足或無資料</span>'}</dd>
          ${isNum(f.roe) ? `<dt>ROE</dt><dd>${fmt(f.roe, 1)}%</dd>` : ''}${isNum(f.gross_margin) ? `<dt>毛利率</dt><dd>${fmt(f.gross_margin, 1)}%</dd>` : ''}
          <dt>月營收 YoY</dt><dd><b class="${cls(f.rev_yoy)}">${isNum(f.rev_yoy) ? sign(f.rev_yoy, 1) + '%' : '—'}</b>${f.rev_yoy_note ? ` <span class="muted">（${f.rev_yoy_note}）</span>` : ''}${f.rev_flag_spike ? ' <span class="pill w">YoY 異常，可能併購或一次性</span>' : ''}</dd>
          <dt>連續成長</dt><dd>${isNum(f.rev_streak) ? f.rev_streak + ' 個月' : '—'}${f.rev_record_high ? '　<span class="ftag">創新高</span>' : ''}</dd>
          <dt>近 3 月 YoY</dt><dd>${isNum(f.rev_yoy_3m) ? sign(f.rev_yoy_3m, 1) + '%' : '—'}　<span class="muted">年初至今</span> ${isNum(f.rev_ytd_yoy) ? sign(f.rev_ytd_yoy, 1) + '%' : '—'}</dd>
          <dt>營運動能分</dt><dd><b>${isNum(f.momentum_score) ? f.momentum_score.toFixed(0) : '—'}</b> <span class="muted">/ 100（營收 YoY、連續月數、創高、淡旺季修正）</span></dd>
        </dl></div>
      <div class="panel"><h3>籌碼</h3><p class="note">三大法人近 60 日（張）與千張大戶持股比例</p><div id="instChart" class="chart short"></div><div id="shChart" class="chart xs"></div></div>
    </div>
    <div class="grid g-1-1" style="margin-top:14px">
      <div class="panel"><h3>相關新聞</h3><p class="note">來自鉅亨 / TechNews / 經濟日報</p>
        ${(s.news || []).length ? s.news.map(n => `<div class="ev"><a href="${esc(n.url)}" target="_blank" rel="noopener">${esc(n.title)}</a><div class="m"><span>${n.date || ''}</span><span class="tag">${esc(n.category || '')}</span><span>${esc(n.source || '')}</span></div></div>`).join('') : '<div class="empty">近期沒有掛到這檔的新聞</div>'}</div>
      <div class="panel"><h3>券商觀點（新聞引述）</h3><p class="note">這是新聞裡引述的券商看法，不是本站的預估</p>
        ${(s.broker_views || []).length ? `<table><thead><tr><th>日期</th><th>券商</th><th>動作</th><th>評等</th><th class="num">目標價</th></tr></thead><tbody>${s.broker_views.map(b => `<tr onclick="window.open('${esc(b.url)}','_blank')"><td class="mono">${b.date || ''}</td><td>${esc(b.broker)}</td><td>${esc(b.action || '')}</td><td>${esc(b.rating || '')}</td><td class="num mono" style="color:var(--accent);font-weight:600">${fmt(b.target_price, 0)}</td></tr>`).join('')}</tbody></table>` : '<div class="empty">近 60 天沒有引述到目標價的新聞</div>'}
        <p class="disclaimer">本頁為決策輔助，技術評分與規則權重尚未經 walk-forward 檢驗；不構成投資建議。</p></div>
    </div>`;
  drawKline(s); drawInst(s); drawShareholding(s);
}

function drawKline(s) {
  const k = C(), o = s.ohlcv, dates = o.map(r => r[0]);
  const v = s.verdict, se = s.series;
  const idx = Object.fromEntries(dates.map((d, i) => [d, i]));
  const areas = [];
  (v.demand || []).forEach(z => areas.push([{yAxis: z.low, itemStyle: {color: k.fall, opacity: .16}, name: `需求區 ${fmt(z.low, 1)}–${fmt(z.high, 1)}`}, {yAxis: z.high}]));
  (v.supply || []).forEach(z => areas.push([{yAxis: z.low, itemStyle: {color: k.rise, opacity: .16}, name: `供給區 ${fmt(z.low, 1)}–${fmt(z.high, 1)}`}, {yAxis: z.high}]));
  const lines = [];
  if (isNum(v.stop)) lines.push({yAxis: v.stop, lineStyle: {color: k.accent, type: 'dashed'}, label: {formatter: `停損 ${fmt(v.stop, 1)}`, position: 'insideEndTop', color: k.accent, fontSize: 10}});
  if (isNum(v.tp1)) lines.push({yAxis: v.tp1, lineStyle: {color: k.accent, type: 'dashed'}, label: {formatter: `目標 ${fmt(v.tp1, 1)}`, position: 'insideEndTop', color: k.accent, fontSize: 10}});
  const pts = [];
  (s.marks.bos || []).forEach(d => { if (idx[d] !== undefined) pts.push({coord: [idx[d], o[idx[d]][2] * 1.01], symbol: 'triangle', symbolSize: 9, itemStyle: {color: k.rise}, value: 'BOS'}); });
  (s.marks.choch || []).forEach(([d, t]) => { if (idx[d] !== undefined) pts.push({coord: [idx[d], t === 1 ? o[idx[d]][3] * .99 : o[idx[d]][2] * 1.01], symbol: 'diamond', symbolSize: 10, itemStyle: {color: t === 1 ? k.rise : k.fall}, value: 'CHoCH'}); });
  (s.marks.sweep_low || []).forEach(d => { if (idx[d] !== undefined) pts.push({coord: [idx[d], o[idx[d]][3] * .985], symbol: 'arrow', symbolSize: 10, itemStyle: {color: k.accent}, value: '假跌破'}); });
  const vol = o.map(r => ({value: r[5], itemStyle: {color: r[4] >= r[1] ? k.rise : k.fall, opacity: .6}}));
  const start = Math.max(0, 100 - Math.round(120 / dates.length * 100));
  mk('kline', {
    animation: false,
    tooltip: {trigger: 'axis', axisPointer: {type: 'cross'}, formatter: ps => {
      const p = ps.find(x => x.seriesType === 'candlestick'); if (!p) return '';
      const [_, op, hi, lo, cl] = o[p.dataIndex]; const i = p.dataIndex;
      return `<b>${dates[i]}</b><br>開 ${fmt(op)}　高 ${fmt(hi)}　低 ${fmt(lo)}　收 <b>${fmt(cl)}</b><br>MA20 ${fmt(se.ma20[i])}　MA60 ${fmt(se.ma60[i])}<br>K ${fmt(se.k[i], 0)}　D ${fmt(se.d[i], 0)}　RSI ${fmt(se.rsi14[i], 0)}　量比 ${isNum(se.vol_ma20[i]) && o[i][5] ? (o[i][5] / se.vol_ma20[i]).toFixed(1) : '—'}`; }},
    axisPointer: {link: [{xAxisIndex: 'all'}]},
    grid: [{left: 8, right: 60, top: 10, height: '52%', containLabel: true}, {left: 8, right: 60, top: '64%', height: '13%', containLabel: true}, {left: 8, right: 60, top: '80%', height: '15%', containLabel: true}],
    xAxis: [0, 1, 2].map(i => ({type: 'category', gridIndex: i, data: dates, boundaryGap: true, axisLine: {lineStyle: {color: k.line}}, axisLabel: {show: i === 2, color: k.ink3, fontSize: 10}, axisTick: {show: false}, splitLine: {show: false}, min: 'dataMin', max: 'dataMax'})),
    yAxis: [{scale: true, gridIndex: 0, position: 'right', axisLabel: {color: k.ink3, fontSize: 10}, splitLine: {lineStyle: {color: k.line}}},
      {scale: true, gridIndex: 1, position: 'right', axisLabel: {show: false}, splitLine: {show: false}, splitNumber: 2},
      {gridIndex: 2, position: 'right', min: 0, max: 100, interval: 50, axisLabel: {color: k.ink3, fontSize: 9}, splitLine: {lineStyle: {color: k.line}}}],
    dataZoom: [{type: 'inside', xAxisIndex: [0, 1, 2], start, end: 100}, {type: 'slider', xAxisIndex: [0, 1, 2], top: '96%', height: 14, start, end: 100, borderColor: k.line, backgroundColor: k.s2, fillerColor: 'rgba(138,90,17,.15)', textStyle: {color: k.ink3, fontSize: 9}}],
    series: [
      {type: 'candlestick', data: o.map(r => [r[1], r[4], r[3], r[2]]), itemStyle: {color: k.rise, color0: k.fall, borderColor: k.rise, borderColor0: k.fall},
        markArea: {silent: true, data: areas, label: {show: true, position: 'insideLeft', fontSize: 10, color: k.ink2}},
        markLine: {silent: true, symbol: 'none', data: lines},
        markPoint: {data: pts, label: {show: false}, tooltip: {formatter: p => p.data.value}}},
      // 看不見的點：讓 y 軸範圍涵蓋停損與目標（markLine 本身不會撐開座標軸）
      {type: 'scatter', data: [[dates.length - 1, isNum(v.tp1) ? v.tp1 : null], [dates.length - 1, isNum(v.stop) ? v.stop : null]], symbolSize: 0, silent: true, tooltip: {show: false}},
      {type: 'line', name: 'MA20', data: se.ma20, showSymbol: false, lineStyle: {width: 1.2, color: '#d9a441'}, smooth: false},
      {type: 'line', name: 'MA60', data: se.ma60, showSymbol: false, lineStyle: {width: 1.2, color: '#5b7fa8'}},
      {type: 'line', name: 'MA120', data: se.ma120, showSymbol: false, lineStyle: {width: 1, color: k.ink3, type: 'dashed', opacity: .6}},
      {type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: vol, barWidth: '60%'},
      {type: 'line', xAxisIndex: 1, yAxisIndex: 1, data: se.vol_ma20, showSymbol: false, lineStyle: {width: 1, color: k.ink3}},
      {type: 'line', xAxisIndex: 2, yAxisIndex: 2, name: 'K', data: se.k, showSymbol: false, lineStyle: {width: 1.2, color: '#d9a441'}},
      {type: 'line', xAxisIndex: 2, yAxisIndex: 2, name: 'D', data: se.d, showSymbol: false, lineStyle: {width: 1.2, color: '#5b7fa8'},
        markLine: {silent: true, symbol: 'none', lineStyle: {color: k.ink3, type: 'dotted', width: .8}, data: [{yAxis: 20}, {yAxis: 80}], label: {show: false}}},
    ]
  }, {clear: true});
}
function drawInst(s) {
  const k = C(), d = s.inst || [];
  if (!d.length) { $('instChart').innerHTML = '<div class="empty">沒有法人資料</div>'; return; }
  mk('instChart', {
    legend: {top: 0, textStyle: {color: k.ink2, fontSize: 10}, itemHeight: 7, itemWidth: 10},
    grid: {left: 8, right: 8, top: 26, bottom: 4, containLabel: true},
    tooltip: {trigger: 'axis', valueFormatter: v => fmtInt(v) + ' 張'},
    xAxis: {type: 'category', data: d.map(x => x.date), axisLabel: {color: k.ink3, fontSize: 9}},
    yAxis: {type: 'value', axisLabel: {color: k.ink3, fontSize: 9}, splitLine: {lineStyle: {color: k.line}}},
    series: [['外資', 'foreign_total', '#c4353c'], ['投信', 'trust', '#d9a441'], ['自營', 'dealer', '#5b7fa8']].map(([n, key, col]) => ({name: n, type: 'bar', stack: 'i', itemStyle: {color: col}, data: d.map(x => x[key] ? Math.round(x[key] / 1000) : 0)}))
  }, {clear: true});
}
function drawShareholding(s) {
  const k = C(), d = s.shareholding || [];
  if (!d.length) { $('shChart').innerHTML = '<div class="empty" style="padding:12px">沒有集保資料</div>'; return; }
  mk('shChart', {
    grid: {left: 8, right: 8, top: 18, bottom: 4, containLabel: true},
    title: {text: '600 張以上大戶持股比例（週）', left: 0, top: 0, textStyle: {fontSize: 10, color: k.ink3, fontWeight: 400}},
    tooltip: {trigger: 'axis', valueFormatter: v => fmt(v) + '%'},
    xAxis: {type: 'category', data: d.map(x => x.date), axisLabel: {show: false}},
    yAxis: {type: 'value', scale: true, axisLabel: {color: k.ink3, fontSize: 9, formatter: '{value}%'}, splitLine: {lineStyle: {color: k.line}}},
    series: [{type: 'line', data: d.map(x => x.pct), showSymbol: false, smooth: true, lineStyle: {color: k.accent, width: 1.5}, areaStyle: {color: k.accent, opacity: .1}}]
  }, {clear: true});
}
function openTaiex() {
  const h = D.market_heat; if (!h || !h.taiex_series) return;
  go('overview');
  const box = $('drill'), k = C(), s = h.taiex_series;
  box.innerHTML = `<div class="drill-h"><h3>加權指數</h3><span class="muted">${h.taiex_series_source || 'FMTQIK'}　近 ${s.length} 日</span><button class="x">×</button></div><div id="taiexChart" class="chart"></div>`;
  box.classList.add('on'); box.querySelector('.x').onclick = () => box.classList.remove('on');
  mk('taiexChart', {tooltip: {trigger: 'axis'}, xAxis: {type: 'category', data: s.map(x => x.date), axisLabel: {color: k.ink3, fontSize: 10}},
    yAxis: {type: 'value', scale: true, axisLabel: {color: k.ink3, fontSize: 10}, splitLine: {lineStyle: {color: k.line}}},
    series: [{type: 'line', data: s.map(x => x.taiex), showSymbol: false, lineStyle: {color: k.accent, width: 2}, areaStyle: {color: k.accent, opacity: .1}}]}, {clear: true});
  box.scrollIntoView({behavior: 'smooth'});
}

// ------------------------------------------------------------------ 產業鏈
function renderChain(sc) {
  if (!sc || !sc.segments) { $('chainGraph').innerHTML = '<div class="empty">沒有產業鏈資料</div>'; return; }
  const k = C();
  $('chainStamp').textContent = `資料 ${sc.meta.as_of || ''}　複核 ${sc.meta.reviewed || ''}`;
  const segs = sc.segments, layers = [...new Set(segs.map(s => s.layer))].sort((a, b) => a - b);
  const segIdx = Object.fromEntries(segs.map(s => [s.id, s]));
  const palette = ['#8a5a11', '#2f5f9e', '#0e8f5b', '#c4353c', '#6f4fa8', '#a86a00', '#3b8ea5'];
  const segColor = Object.fromEntries(segs.map((s, i) => [s.id, palette[i % palette.length]]));
  // 分層座標：x 依 layer，同層依序排 y
  const byLayer = {}; sc.companies.forEach(c => (byLayer[c.layer] = byLayer[c.layer] || []).push(c));
  const W = 1000, H = 520, nodes = [], nid = {};
  layers.forEach((L, li) => {
    const col = byLayer[L] || [], x = 60 + li * ((W - 120) / Math.max(1, layers.length - 1));
    col.forEach((c, i) => {
      const y = 40 + (i + 0.5) * ((H - 80) / col.length);
      const share = (c.share || [])[0];
      const size = 14 + (share && isNum(share.value_pct) ? Math.sqrt(share.value_pct) * 2.2 : (share && share.value_pct_range ? 12 : 0));
      nid[c.id] = nodes.length;
      nodes.push({name: c.name, id: c.id, x, y, symbolSize: size, tw: c.tw_code, foreign: c.foreign, seg: c.segment, share, tech: c.tech, note: c.note, groups: c.groups,
        itemStyle: {color: segColor[c.segment], opacity: c.foreign ? .45 : 1, borderColor: k.surface, borderWidth: 1},
        label: {show: true, position: 'right', fontSize: 10, color: c.foreign ? k.ink3 : k.ink, formatter: c.tw_code ? `${c.name} ${c.tw_code}` : c.name}});
    });
  });
  const links = sc.edges.filter(e => nid[e.from] !== undefined && nid[e.to] !== undefined && e.rel !== 'produced_by').map(e => ({
    source: nid[e.from], target: nid[e.to], rel: e.rel, item: e.item,
    lineStyle: {width: e.rel === 'competes' ? 1 : 1 + (e.strength || 2) * 0.6, color: e.rel === 'competes' ? k.ink3 : segColor[sc.companies.find(c => c.id === e.from).segment], opacity: e.rel === 'competes' ? .35 : .55, type: e.rel === 'competes' ? 'dashed' : 'solid', curveness: 0.15}}));
  const c = mk('chainGraph', {
    tooltip: {formatter: p => {
      if (p.dataType === 'edge') return `${nodes[p.data.source].name} → ${nodes[p.data.target].name}<br>${p.data.rel === 'competes' ? '競爭' : '供貨'}${p.data.item ? '：' + p.data.item : ''}`;
      const d = p.data, sh = d.share;
      return `<b>${d.name}${d.tw ? ' ' + d.tw : ''}</b>　<span style="color:${k.ink3}">${segIdx[d.seg].name}</span><br>${(d.tech || []).join('、')}${sh ? `<br>${sh.metric}：<b>${isNum(sh.value_pct) ? sh.value_pct + '%' : sh.value_pct_range.join('–') + '%'}</b> <span style="color:${k.ink3}">（${sh.source}，${sh.as_of}${sh.stale ? '，可能過時' : ''}）</span>` : ''}${d.tw ? `<br><span style="color:${k.accent}">點擊看 K 線</span>` : ''}`; }},
    series: [{type: 'graph', layout: 'none', data: nodes, links, roam: true, edgeSymbol: ['none', 'arrow'], edgeSymbolSize: 6, lineStyle: {curveness: .15},
      emphasis: {focus: 'adjacency', lineStyle: {width: 4}}}],
    graphic: layers.map((L, li) => ({type: 'text', left: (60 + li * ((W - 120) / Math.max(1, layers.length - 1))) / W * 100 + '%', top: 4, style: {text: segs.filter(s => s.layer === L).map(s => s.name).join(' / '), fontSize: 10, fill: k.ink3, fontFamily: '"IBM Plex Mono", monospace'}, z: 10}))
  }, {clear: true});
  c.off('click'); c.on('click', p => { if (p.dataType === 'node') { if (p.data.tw) go('stock', p.data.tw); else showCo(p.data); } });
  $('chainLegend').innerHTML = segs.map(s => `<span><i style="background:${segColor[s.id]}"></i>${s.name}</span>`).join('');
  // 手機：折疊清單
  $('chainList').innerHTML = segs.map(s => { const cos = sc.companies.filter(c => c.segment === s.id); return `<details class="seg-card"><summary>${s.name}<span class="n">${cos.length} 家</span></summary>${cos.map(co => { const sh = (co.share || [])[0]; return `<div class="co"><span class="nm" ${co.tw_code ? `onclick="go('stock','${co.tw_code}')"` : ''}>${esc(co.name)}${co.tw_code ? ` <span class="mono muted">${co.tw_code}</span>` : ''}</span>${sh ? `<span class="sh ${sh.stale ? 'stale' : ''}" title="${esc(sh.source)} ${sh.as_of}">${isNum(sh.value_pct) ? sh.value_pct + '%' : sh.value_pct_range.join('–') + '%'}</span>` : ''}<span class="tech">${(co.tech || []).slice(0, 3).join('・')}</span></div>`; }).join('')}</details>`; }).join('');
  // 瓶頸 / 滲透率
  $('chainProducts').innerHTML = (sc.products || []).map(p => {
    const rows = [];
    if (p.supply_demand) rows.push(`<dt>供需</dt><dd>${esc(p.supply_demand.status === 'shortage' ? '供不應求' : p.supply_demand.status)}　<span class="muted">${esc(p.supply_demand.note || '')}</span></dd>`);
    (p.demand_allocation || []).forEach(a => rows.push(`<dt>${esc(a.customer)}</dt><dd><span class="bar" style="width:${a.pct * 2}px"></span>${a.pct}%</dd>`));
    (p.penetration || []).forEach(pe => rows.push(`<dt>${esc(pe.metric)}</dt><dd><b class="${pe.stale ? 'muted' : ''}">${pe.value_pct}%</b> <span class="muted">${esc(pe.source)}，${pe.as_of}</span></dd>`));
    if (p.note) rows.push(`<dt>備註</dt><dd class="muted" style="font-family:inherit">${esc(p.note)}</dd>`);
    const src = p.allocation_source ? `<p class="note">來源：${esc(p.allocation_source.name)}（${p.allocation_source.as_of}，${p.allocation_source.confidence === 'reported' ? '媒體/法人轉述' : p.allocation_source.confidence}）</p>` : '';
    return `<div class="panel"><h3>${esc(p.name)}</h3>${src}<dl class="kv">${rows.join('')}</dl></div>`; }).join('');
}
function showCo(d) {
  const box = $('drillCo'), sh = d.share;
  box.innerHTML = `<div class="drill-h"><h3>${esc(d.name)}</h3><span class="muted">非台股，僅作為供應鏈節點</span><button class="x">×</button></div><div class="kv" style="display:grid"><dt>技術</dt><dd style="font-family:inherit">${(d.tech || []).join('、') || '—'}</dd>${sh ? `<dt>${esc(sh.metric)}</dt><dd>${isNum(sh.value_pct) ? sh.value_pct + '%' : sh.value_pct_range.join('–') + '%'} <span class="muted">${esc(sh.source)} ${sh.as_of}</span></dd>` : ''}</div>`;
  box.classList.add('on'); box.querySelector('.x').onclick = () => box.classList.remove('on');
}

// ------------------------------------------------------------------ 季節性
function renderSeason(s) {
  if (!s || !s.length) { $('seasonDots').innerHTML = '<div class="empty">歷史回補完成後才有季節性統計</div>'; return; }
  const k = C(), month = new Date().getMonth() + 1;
  const valid = s.filter(r => isNum(r.avg_return));
  const groups = [...new Set(valid.map(r => r.group_name))];
  // 每月排名
  const rank = {}; for (let m = 1; m <= 12; m++) { const rows = valid.filter(r => r.month === m).sort((a, b) => b.avg_return - a.avg_return); rows.forEach((r, i) => rank[`${r.group_name}|${m}`] = i + 1); }
  const thisM = valid.filter(r => r.month === month).sort((a, b) => b.avg_return - a.avg_return).slice(0, 5);
  $('seasonTitle').textContent = `${month} 月歷史上最強的族群`;
  $('monthCards').innerHTML = thisM.map((r, i) => `<div class="mc"><div class="rank">#${i + 1}</div><div class="g">${esc(r.group_name)}</div><div class="v ${cls(r.avg_return)}">${sign(r.avg_return, 1)}%</div><div class="w">勝率 <b>${fmt(r.win_rate, 0)}%</b>　樣本 <b>${r.samples} 年</b>${r.samples < 5 ? '　<span class="up">樣本少</span>' : ''}</div></div>`).join('') || '<div class="empty">本月樣本不足</div>';
  const top = groups.slice(0, 18);
  const series = top.map((g, gi) => ({name: g, type: 'line', smooth: true, showSymbol: true, symbolSize: p => 4 + (p[2] || 50) / 12, lineStyle: {width: 1, opacity: .45}, emphasis: {focus: 'series', lineStyle: {width: 3, opacity: 1}},
    data: Array.from({length: 12}, (_, i) => { const r = valid.find(x => x.group_name === g && x.month === i + 1); return r ? [i, rank[`${g}|${i + 1}`], r.win_rate, r.avg_return, r.samples] : [i, null]; })}));
  mk('seasonDots', {
    color: ['#c4353c', '#d9a441', '#2f5f9e', '#0e8f5b', '#6f4fa8', '#a86a00', '#3b8ea5', '#e2585e', '#5b7fa8', '#2eb37c', '#8a5a11', '#9aa2b0', '#c96f2f', '#4f7d5f', '#b04a8c', '#6c8bd6', '#8f7a2e', '#4a9fb5'],
    legend: {type: 'scroll', bottom: 0, textStyle: {color: k.ink2, fontSize: 10}, itemHeight: 8, itemWidth: 12},
    grid: {left: 8, right: 16, top: 16, bottom: 40, containLabel: true},
    tooltip: {trigger: 'item', formatter: p => `<b>${p.seriesName}　${p.value[0] + 1} 月</b><br>排名 #${p.value[1]}　平均 ${sign(p.value[3], 1)}%<br>勝率 ${fmt(p.value[2], 0)}%　樣本 ${p.value[4]} 年`},
    xAxis: {type: 'category', data: Array.from({length: 12}, (_, i) => `${i + 1}月`), axisLabel: {color: k.ink2, fontSize: 11}, axisLine: {lineStyle: {color: k.line}},
      axisPointer: {show: true, type: 'shadow', shadowStyle: {color: k.accent, opacity: .06}}},
    yAxis: {type: 'value', inverse: true, min: 1, max: groups.length, interval: Math.ceil(groups.length / 6), axisLabel: {color: k.ink3, fontSize: 10, formatter: v => '#' + v}, splitLine: {lineStyle: {color: k.line}}, name: '排名', nameTextStyle: {color: k.ink3, fontSize: 10}},
    series
  }, {clear: true});
}

// ------------------------------------------------------------------ 事件側欄
let evCat = '全部';
function renderEvents(news, broker) {
  const side = $('side'), list = $('evList');
  const items = (news || []).map(n => ({...n, kind: 'news'}));
  const bv = (broker || []).map(b => ({kind: 'target', date: b.date, title: `${b.broker}${b.action ? ' ' + b.action : ''}${b.name || b.code} 目標價 ${fmt(b.target_price, 0)}${b.rating ? '（' + b.rating + '）' : ''}`, url: b.url, category: '券商', codes: b.code, source: b.source}));
  const all = [...bv, ...items].sort((a, b) => String(b.published_at || b.date).localeCompare(String(a.published_at || a.date)));
  const cats = ['全部', ...new Set(all.map(x => x.category).filter(Boolean))];
  $('evCount').textContent = all.length;
  $('evCats').innerHTML = cats.map(c => `<button class="${c === evCat ? 'on' : ''}" data-c="${c}">${c}</button>`).join('');
  $('evCats').querySelectorAll('button').forEach(b => b.onclick = () => { evCat = b.dataset.c; renderEvents(news, broker); });
  const rows = all.filter(x => evCat === '全部' || x.category === evCat).slice(0, 80);
  list.innerHTML = rows.map(x => `<div class="ev ${x.kind === 'target' ? 'target' : ''}"><a href="${esc(x.url)}" target="_blank" rel="noopener">${x.kind === 'target' ? '<span class="tp">目標價</span> ' : ''}${esc(x.title)}</a>
    <div class="m"><span>${x.date || ''}</span><span class="tag">${esc(x.category || '')}</span>${(String(x.codes || '').split(',').filter(c => D.candIdx[c]).slice(0, 4)).map(c => `<span class="c" onclick="go('stock','${c}')">${c} ${esc(D.candIdx[c].name)}</span>`).join('')}${(x.keywords || '').split(',').filter(Boolean).slice(0, 3).map(kw => `<span class="tag">${esc(kw)}</span>`).join('')}</div></div>`).join('') || '<div class="empty">沒有事件</div>';
  $('evToggle').onclick = () => side.classList.toggle('open');
  $('evClose').onclick = () => side.classList.remove('open');
}
