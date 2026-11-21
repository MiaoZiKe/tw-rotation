/* 管理區：問卷與願望（#admin/survey）—— 2026-11-01
   ----------------------------------------------------------------------------
   Andy 11-01：新會員體驗到期前填問卷（滿意度、最實用功能、需改善功能、希望新增功能；功能用「母分頁＋子分頁」選）送 7 天；
   好友邀請送 14 天 Pro、Pro 可許願。站主要看結果。
   三個分頁：
     ① 問卷結果：填寫人數、平均滿意度、滿意度分布（D 款橫條）、「最實用」「需改善」母分頁排行橫條（點母分頁原地展開子分頁排行）
     ② 文字意見：時間、email、改善、想要的功能；可搜尋、可匯出 CSV（含 BOM，Excel 直接開不亂碼）
     ③ 願望清單：時間、email、功能、願望文字（Pro 會員許願）；可搜尋、可匯出
   API（account-api，只認站主）：POST /v1/admin/survey、/v1/admin/wishes。這一頁只是排版；非站主後端回 403，畫面只寫「這個帳號不是管理者」。
   email 顯示配合錄影模式：window.TwRecMask 存在就用它遮罩（不存在原樣顯示）。CSV 匯出的是真實 email（那是站主自己的資料檔，不是畫面）。
   ============================================================================ */
(function () {
  'use strict';
  const T = () => window.TwSub;
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const nt = (n) => (Number(n) || 0).toLocaleString('en-US');
  /* 時間：後端給毫秒（也容錯秒、字串）；一律顯示臺北時間 */
  const ymdhm = (at) => {
    let t = typeof at === 'number' ? at : Date.parse(at);
    if (!isFinite(t)) return String(at || '');
    if (t < 1e12) t *= 1000;
    return new Date(t + 8 * 3600 * 1000).toISOString().slice(0, 16).replace('T', ' ');
  };
  const maskEmail = (e) => {
    try { if (typeof window.TwRecMask === 'function') { const r = window.TwRecMask(String(e || '')); if (typeof r === 'string') return r; } } catch (x) { /* 遮罩壞了就原樣 */ }
    return String(e || '');
  };
  /* 功能 key → 中文名。站上若有登錄就用 window.TwSurveyLabels（key→名稱），沒有就用下面這張；查不到顯示原 key */
  const LABELS = {
    overview: '總覽', flow: '資金流向', industry: '產業地圖', stock: '個股', themes: '題材熱度', season: '季節性', watch: '自選', market: '市場明細',
    etf: 'ETF', news: '新聞', articles: '精選文章', tc: '科技透明圈', calendar: '財經日曆', alerts: '提醒', pricing: '訂閱方案', notices: '公告',
    ma: '大盤與族群', chips: '籌碼', fin: '財報', k: 'K 線', kline: 'K 線', tech: '技術面', fund: '基本面', event: '事件面',
  };
  const label = (k) => { const m = window.TwSurveyLabels || {}; return m[k] || LABELS[k] || k; };
  const S = { d: null, w: null, tab: 'result', open: {}, q: '', wq: '', help: false, err: null };

  function css() {
    T().css('surveyAdmCss', `
#v-subadm .sv [hidden]{display:none!important}
#v-subadm .sv h3{margin:0;font-size:16px}
#v-subadm .sv .muted{color:var(--ink-2);font-size:13px;line-height:1.6;margin:4px 0 10px}
#v-subadm .sv .hd{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:8px}
#v-subadm .sv .hd .sp{flex:1}
#v-subadm .sv button{height:32px;padding:0 12px;border-radius:var(--r-sm,10px);border:1px solid var(--line-2);background:var(--panel-3);color:var(--ink);cursor:pointer;font-size:13px;white-space:nowrap}
#v-subadm .sv button.q{width:26px;height:26px;padding:0;border-radius:50%;font-weight:700;color:var(--cyan)}
#v-subadm .sv .seg{display:inline-flex;border:1px solid var(--line-2);border-radius:9px;overflow:hidden;max-width:100%}
#v-subadm .sv .seg button{border:0;border-radius:0;background:transparent;color:var(--ink-2);height:34px;padding:0 16px;font-size:13.5px}
#v-subadm .sv .seg button.on{background:var(--cyan);color:#04121a;font-weight:700}
:root[data-theme=light] #v-subadm .sv .seg button.on{color:#fff}
#v-subadm .sv .hint{border:1px solid var(--line);border-radius:10px;padding:8px 12px;margin:8px 0;font-size:13px;line-height:1.7;color:var(--ink-2)}
#v-subadm .sv .kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:12px 0}
#v-subadm .sv .kpi{border:1px solid var(--line);border-radius:12px;padding:10px 14px;min-width:0}
#v-subadm .sv .kpi small{display:block;color:var(--ink-2);font-size:12.5px}
#v-subadm .sv .kpi .v{display:flex;align-items:baseline;gap:4px;flex-wrap:nowrap}
#v-subadm .sv .kpi b{font-size:24px;font-family:var(--mono,ui-monospace,monospace);font-variant-numeric:tabular-nums}
#v-subadm .sv .kpi i{font-size:13px;font-style:normal;color:var(--ink-2);font-weight:400;white-space:nowrap}
#v-subadm .sv .grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;align-items:stretch}
#v-subadm .sv .card2{border:1px solid var(--line);border-radius:12px;padding:12px 14px;min-width:0}
#v-subadm .sv .card2 h4{margin:0 0 8px;font-size:14px;display:flex;align-items:center;gap:8px}
#v-subadm .sv .card2 h4 small{color:var(--ink-2);font-weight:400;font-size:12.5px}
#v-subadm .sv .br{display:grid;grid-template-columns:minmax(72px,auto) minmax(0,1fr) auto;align-items:center;gap:8px;min-height:30px;padding:2px 0;font-size:13.5px;width:100%;text-align:left;background:none;border:0;color:var(--ink);height:auto}
#v-subadm .sv .br .nm{white-space:nowrap}
#v-subadm .sv .br .trk{height:12px;background:var(--panel-3);border-radius:3px;position:relative;overflow:hidden}
#v-subadm .sv .br .fil{position:absolute;left:0;top:0;bottom:0;border-radius:0 3px 3px 0;background:linear-gradient(90deg,color-mix(in srgb,var(--c,var(--cyan)) 55%,transparent),var(--c,var(--cyan)))}
#v-subadm .sv .br .val{font-family:var(--mono,ui-monospace,monospace);font-variant-numeric:tabular-nums;font-size:13px;white-space:nowrap;text-align:right}
#v-subadm .sv .br .val i{font-style:normal;color:var(--ink-2);margin-left:4px}
#v-subadm .sv button.br:hover .fil{filter:brightness(1.2);outline:1px solid var(--c,var(--cyan))}
#v-subadm .sv .br .car{display:inline-block;width:12px;color:var(--ink-2);transition:transform .15s}
#v-subadm .sv .br[aria-expanded=true] .car{transform:rotate(90deg)}
#v-subadm .sv .subs{margin:2px 0 6px 18px;padding-left:10px;border-left:2px solid var(--line)}
#v-subadm .sv .subs .br{min-height:26px;font-size:13px;cursor:default}
#v-subadm .sv .subs .trk{height:9px}
#v-subadm .sv .empty{color:var(--ink-2);font-size:13px;padding:8px 0}
#v-subadm .sv .flt{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:10px 0}
#v-subadm .sv .flt input{height:32px;background:var(--panel);color:var(--ink);border:1px solid var(--line-2);border-radius:8px;padding:0 8px;font:inherit;font-size:13.5px;box-sizing:border-box;flex:1 1 220px;min-width:0}
#v-subadm .sv select.wst{height:30px;background:var(--panel);color:var(--ink);border:1px solid var(--line-2);border-radius:8px;padding:0 6px;font:inherit;font-size:13px;color-scheme:dark light}
#v-subadm .sv .flt .cn{color:var(--ink-2);font-size:13px}
#v-subadm .sv .tw{overflow-x:auto}
#v-subadm .sv table{width:100%;border-collapse:collapse;font-size:13px}
#v-subadm .sv th,#v-subadm .sv td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top;line-height:1.6}
#v-subadm .sv th{color:var(--ink-2);font-weight:600;font-size:12.5px;white-space:nowrap}
#v-subadm .sv td.t,#v-subadm .sv td.e{white-space:nowrap}
#v-subadm .sv td.x{min-width:220px;word-break:break-word}
#v-subadm .sv .st{min-height:1.2em;font-size:13px;color:var(--ink-2);margin-top:8px}
@media (max-width:900px){#v-subadm .sv .grid{grid-template-columns:minmax(0,1fr)}}
@media (max-width:640px){
  #v-subadm .sv .kpis{grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}
  #v-subadm .sv .kpi{padding:8px 8px}#v-subadm .sv .kpi .v{display:flex;align-items:baseline;gap:4px;flex-wrap:nowrap}
#v-subadm .sv .kpi b{font-size:19px}
  #v-subadm .sv .seg button{padding:0 10px;font-size:13px}
  #v-subadm .sv .br{grid-template-columns:minmax(64px,auto) minmax(0,1fr) auto;font-size:13px}
}`);
  }

  const call = (p) => T().call(p, {});
  async function load() {
    const [a, b] = await Promise.all([call('/v1/admin/survey'), call('/v1/admin/wishes')]);
    S.err = null;
    if (!a || a._s !== 200) S.err = a;
    else S.d = a;
    if (b && b._s === 200) S.w = b;
    return a;
  }

  /* 滿意度：{1..5:count}；平均＝加權平均（後端沒給 avg，前端自己算，口徑一樣） */
  function stats(d) {
    const sat = d.sat || {};
    let sum = 0, cnt = 0;
    for (let i = 1; i <= 5; i++) { const c = Number(sat[i]) || 0; sum += c * i; cnt += c; }
    const good = (Number(sat[4]) || 0) + (Number(sat[5]) || 0);
    return { avg: Number.isFinite(Number(d.avg)) && Number(d.avg) > 0 ? Number(d.avg) : cnt ? sum / cnt : 0, cnt, good, goodPct: cnt ? Math.round((good / cnt) * 100) : 0 };
  }
  /* 母分頁排行：key 是「母」或「母/子」；母的總數＝母本身 + 所有子；子分頁照次數排，單獨選母分頁（沒選子分頁）的另列「（整個分頁）」 */
  function groupBy(map, tree) {
    /* 後端的扁平表母／子 key 都在裡面，直接加總會重複算 → 有 *_tree（母→{n, subs}）就用它；沒有才退回扁平表自己分母子 */
    if (tree && typeof tree === 'object' && Object.keys(tree).length) {
      const arr = Object.entries(tree).map(([p, o]) => {
        const subs = Object.entries((o && o.subs) || {}).map(([k, n]) => ({ key: k, full: p + '/' + k, n: Number(n) || 0 })).filter((x) => x.n).sort((a, b) => b.n - a.n);
        return { key: p, total: Number(o && o.n) || subs.reduce((t, x) => t + x.n, 0), subs };
      }).filter((o) => o.total);
      return arr.sort((a, b) => b.total - a.total || String(a.key).localeCompare(String(b.key)));
    }
    const g = new Map();
    for (const [k, v] of Object.entries(map || {})) {
      const c = Number(v) || 0; if (!c) continue;
      const [p, ...r] = String(k).split('/'); const sub = r.join('/');
      if (!g.has(p)) g.set(p, { key: p, total: 0, subs: [] });
      const o = g.get(p); o.total += c; o.subs.push({ key: sub, full: k, n: c });
    }
    const arr = [...g.values()];
    arr.forEach((o) => o.subs.sort((a, b) => b.n - a.n));
    return arr.sort((a, b) => b.total - a.total || String(a.key).localeCompare(String(b.key)));
  }
  function barRow(nm, n, max, total, color, attrs, caret) {
    const w = max ? Math.max(2, Math.round((n / max) * 100)) : 0;
    const pct = total ? Math.round((n / total) * 100) : 0;
    const inner = `${caret ? '<span class="car" aria-hidden="true">▸</span>' : ''}<span class="nm">${esc(nm)}</span>`;
    return `<${attrs ? 'button type="button"' : 'div'} class="br" ${attrs || ''} style="--c:${color}"><span style="display:flex;align-items:center;gap:2px">${inner}</span><span class="trk"><span class="fil" style="width:${w}%"></span></span><span class="val">${nt(n)}<i>${pct}%</i></span></${attrs ? 'button' : 'div'}>`;
  }
  function rankCard(id, title, color, map, tree) {
    const gs = groupBy(map, tree);
    const total = gs.reduce((s, o) => s + o.total, 0);
    const max = gs.length ? gs[0].total : 0;
    const rows = gs.map((o) => {
      const open = !!S.open[id + ':' + o.key];
      const subMax = o.subs.length ? o.subs[0].n : 0;
      const hasSub = o.subs.some((s) => s.key);
      const head = hasSub ? barRow(label(o.key), o.total, max, total, color, `data-par="${esc(id + ':' + o.key)}" aria-expanded="${open}" title="點一下展開這個分頁底下的子分頁排行"`, true)
        : barRow(label(o.key), o.total, max, total, color, '', false);
      const subs = hasSub && open ? `<div class="subs" data-subs="${esc(id + ':' + o.key)}">${o.subs.map((s) => barRow(s.key ? label(s.key) : '（整個分頁）', s.n, subMax, o.total, color, '', false)).join('')}</div>` : '';
      return head + subs;
    }).join('');
    return `<div class="card2" id="${id}Card"><h4>${esc(title)}<small>共 ${nt(total)} 票・${nt(gs.length)} 個分頁</small></h4>${rows || '<div class="empty">還沒有人填。</div>'}</div>`;
  }

  function wantCard(d) {
    const arr = Object.entries(d.want || {}).map(([k, n]) => [k, Number(n) || 0]).filter((x) => x[1]).sort((a, b) => b[1] - a[1]);
    const total = arr.reduce((t, x) => t + x[1], 0), mx = arr.length ? arr[0][1] : 0;
    return `<div class="card2" id="svWant"><h4>想要新增的功能<small>共 ${nt(total)} 票</small></h4>${arr.map(([k, n]) => barRow(k.split('/').map(label).join(' › '), n, mx, total, '#a78bfa', '', false)).join('') || '<div class="empty">還沒有人選。</div>'}</div>`;
  }
  function resultView(v, box) {
    const d = S.d, st = stats(d);
    const sat = d.sat || {};
    const inv = d.invite || {};
    const COL = { 5: '#2fbf71', 4: '#7bd88f', 3: '#e0a93a', 2: '#f08a4b', 1: '#e5484d' };
    const NAME = { 5: '5 分 很滿意', 4: '4 分 滿意', 3: '3 分 普通', 2: '2 分 不太滿意', 1: '1 分 不滿意' };
    const mx = Math.max(1, ...[1, 2, 3, 4, 5].map((i) => Number(sat[i]) || 0));
    box.innerHTML = `
      <div class="kpis">
        <div class="kpi"><small>填寫人數</small><div class="v"><b id="svN">${nt(d.n)}</b><i>人</i></div></div>
        <div class="kpi"><small>平均滿意度</small><div class="v"><b id="svAvg">${st.cnt ? st.avg.toFixed(2) : '—'}</b><i>/ 5</i></div></div>
        <div class="kpi"><small>滿意以上（4～5 分）</small><div class="v"><b id="svGood">${st.cnt ? st.goodPct + '%' : '—'}</b><i>${nt(st.good)} 人</i></div></div>
        <div class="kpi"><small>好友邀請（邀請碼／被使用）</small><div class="v"><b id="svInv">${nt(inv.codes)}</b><i>碼</i><b id="svInvU" style="margin-left:10px">${nt(inv.uses)}</b><i>次</i></div></div>
      </div>
      <div class="grid">
        <div class="card2" id="svSat"><h4>滿意度分布<small>${nt(st.cnt)} 份</small></h4>
          ${[5, 4, 3, 2, 1].map((i) => barRow(NAME[i], Number(sat[i]) || 0, mx, st.cnt, COL[i], '', false)).join('')}</div>
        ${wantCard(d)}
        ${rankCard('svUse', '最實用的功能', '#22b8cf', d.useful, d.useful_tree)}
        ${rankCard('svImp', '最需要改善的功能', '#f08a4b', d.improve, d.improve_tree)}
      </div>`;
    box.querySelectorAll('[data-par]').forEach((b) => {
      b.onclick = () => { const k = b.dataset.par; S.open[k] = !S.open[k]; resultView(v, box); const nb = box.querySelector(`[data-par="${CSS.escape(k)}"]`); if (nb) nb.focus(); };
    });
  }

  /* 文字意見／願望清單共用的表格＋搜尋＋匯出 */
  const csvCell = (x) => `"${String(x == null ? '' : x).replace(/"/g, '""')}"`;
  function exportCsv(name, head, rows) {
    const txt = '﻿' + [head, ...rows].map((r) => r.map(csvCell).join(',')).join('\r\n');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([txt], { type: 'text/csv;charset=utf-8' }));
    a.download = `${name}_${new Date(Date.now() + 8 * 3600e3).toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500);
    window.__surveyCsv = txt;    // 驗收用：最後一次匯出的內容
  }
  function listView(v, box, cfg) {
    const all = cfg.items.slice().sort((a, b) => cfg.at(b) - cfg.at(a));
    const q = S[cfg.qkey].trim().toLowerCase();
    const rows = q ? all.filter((r) => cfg.hay(r).toLowerCase().includes(q)) : all;
    box.innerHTML = `
      <div class="flt"><input type="search" id="${cfg.id}Q" placeholder="${esc(cfg.ph)}" value="${esc(S[cfg.qkey])}" aria-label="搜尋">
        <span class="cn" id="${cfg.id}Cnt">${nt(rows.length)} / ${nt(all.length)} 筆</span>
        <button type="button" id="${cfg.id}Csv"${rows.length ? '' : ' disabled'}>匯出 CSV</button></div>
      <div class="tw"><table id="${cfg.id}Tbl"><thead><tr>${cfg.cols.map((c) => `<th>${c}</th>`).join('')}</tr></thead>
      <tbody>${rows.map(cfg.tr).join('') || `<tr><td colspan="${cfg.cols.length}" class="empty">${all.length ? '沒有符合的資料。' : cfg.none}</td></tr>`}</tbody></table></div>`;
    const inp = box.querySelector('#' + cfg.id + 'Q');
    inp.oninput = () => {
      S[cfg.qkey] = inp.value;
      const keep = inp.selectionStart;
      listView(v, box, cfg);
      const ni = box.querySelector('#' + cfg.id + 'Q'); ni.focus(); try { ni.setSelectionRange(keep, keep); } catch (e) { /* 略 */ }
    };
    if (cfg.after) cfg.after(v, box);
    box.querySelector('#' + cfg.id + 'Csv').onclick = () => exportCsv(cfg.file, cfg.csvHead, rows.map(cfg.csv));
  }
  const TXT = '<span class="muted" style="margin:0">—</span>';
  /* 想要的功能＝勾的選項（中文名）＋自己寫的字 */
  const wantTxt = (r) => [].concat(Array.isArray(r.want) ? r.want.map((k) => String(k).split('/').map(label).join(' › ')) : [], r.want_text ? [r.want_text] : []).join('；');
  function textsView(v, box) {
    listView(v, box, {
      id: 'svT', qkey: 'q', file: '問卷文字意見', ph: '搜尋 email、改善意見、想要的功能…', none: '還沒有人留文字意見。',
      items: (S.d.texts || []), at: (r) => Number(r.at) || 0,
      hay: (r) => [r.email, r.improve_text, r.want_text, wantTxt(r)].join(' '),
      cols: ['時間', 'email', '滿意度', '想改善的地方', '想要的新功能'],
      tr: (r) => `<tr><td class="t">${esc(ymdhm(r.at))}</td><td class="e" data-email="1">${esc(maskEmail(r.email))}</td><td class="t">${r.sat ? esc(r.sat) + ' 分' : TXT}</td><td class="x">${r.improve_text ? esc(r.improve_text) : TXT}</td><td class="x">${wantTxt(r) ? esc(wantTxt(r)) : TXT}</td></tr>`,
      csvHead: ['時間', 'email', '滿意度', '想改善的地方', '想要的新功能'],
      csv: (r) => [ymdhm(r.at), r.email, r.sat || '', r.improve_text || '', wantTxt(r)],
    });
  }
  const WST = { new: '新許願', doing: '處理中', done: '已完成' };
  function wishesView(v, box) {
    listView(v, box, {
      id: 'svW', qkey: 'wq', file: '願望清單', ph: '搜尋 email、功能、願望…', none: '還沒有人許願。',
      items: ((S.w && S.w.items) || []), at: (r) => Number(r.at) || 0,
      hay: (r) => [r.email, r.name, r.feature, label(r.feature), r.text, WST[r.status || 'new']].join(' '),
      cols: ['時間', 'email', '功能', '願望', '狀態'],
      tr: (r) => `<tr><td class="t">${esc(ymdhm(r.at))}</td><td class="e" data-email="1">${esc(maskEmail(r.email))}</td><td class="t">${r.feature ? esc(r.feature.split('/').map(label).join(' › ')) : TXT}</td><td class="x">${esc(r.text)}</td><td class="t"><select class="wst" data-wid="${esc(r.id)}" aria-label="處理狀態">${Object.entries(WST).map(([k, n]) => `<option value="${k}"${(r.status || 'new') === k ? ' selected' : ''}>${n}</option>`).join('')}</select></td></tr>`,
      csvHead: ['時間', 'email', '名稱', '功能', '願望', '狀態'],
      csv: (r) => [ymdhm(r.at), r.email, r.name || '', r.feature ? r.feature.split('/').map(label).join(' › ') : '', r.text || '', WST[r.status || 'new']],
      after: (v, box) => box.querySelectorAll('select.wst').forEach((sel) => { sel.onchange = async () => {
        const it = S.w.items.find((x) => String(x.id) === sel.dataset.wid), old = it.status || 'new', st = v.querySelector('#svSt');
        const j = await T().call('/v1/admin/wish/status', { id: it.id, status: sel.value });
        if (j && j._s === 200 && j.ok !== false) { it.status = sel.value; st.textContent = '已更新：' + WST[sel.value]; }
        else { sel.value = old; st.textContent = '更新失敗（' + (j ? j.error || j._s : '連不到') + '），已還原。'; }
      }; }),
    });
  }

  function paint(v) {
    const nT = (S.d.texts || []).length, nW = ((S.w && S.w.items) || []).length;
    const tabs = [['result', '問卷結果'], ['texts', `文字意見（${nT}）`], ['wishes', `願望清單（${nW}）`]];
    v.innerHTML = `<div class="card sv" id="svAdm">
      <div class="hd"><h3>問卷與願望</h3><button type="button" class="q" id="svHelp" aria-expanded="${S.help}" aria-label="說明" title="這一頁怎麼看">?</button>
        <span class="sp"></span><button type="button" id="svReload">重新整理</button></div>
      <div class="hint" id="svHint" ${S.help ? '' : 'hidden'}>
        新會員體驗期到期前會被請填問卷（填完送 7 天）。「問卷結果」看整體：滿意度越右邊越好、排行越長代表越多人點名；
        點一個分頁（例如「個股」）會展開它底下的子分頁，看大家具體指的是哪一塊。要決定先做什麼：「需改善」排前面的先修，「文字意見」裡的想要功能拿來排新功能。
        「願望清單」是 Pro 會員許的願（好友邀請送 14 天 Pro 後才有資格）。email 在錄影模式會自動遮罩。
      </div>
      <div class="seg" id="svTabs" role="tablist" aria-label="問卷與願望分頁">${tabs.map(([k, n]) => `<button type="button" role="tab" data-t="${k}" class="${S.tab === k ? 'on' : ''}" aria-selected="${S.tab === k}">${n}</button>`).join('')}</div>
      <div id="svView" style="margin-top:12px"></div><div class="st" id="svSt" role="status"></div></div>`;
    v.querySelector('#svReload').onclick = () => render(v);
    v.querySelector('#svHelp').onclick = (e) => { S.help = !S.help; e.currentTarget.setAttribute('aria-expanded', S.help); v.querySelector('#svHint').hidden = !S.help; };
    v.querySelectorAll('[data-t]').forEach((b) => { b.onclick = () => { S.tab = b.dataset.t; paint(v); }; });
    const box = v.querySelector('#svView');
    if (S.tab === 'texts') textsView(v, box); else if (S.tab === 'wishes') wishesView(v, box); else resultView(v, box);
  }

  async function render(v) {
    css();
    if (!S.d) v.innerHTML = '<div class="card sv"><p class="muted">載入中…</p></div>';
    const a = await load();
    if (!(location.hash || '').startsWith('#admin/survey')) return;
    if (!a || a._s !== 200) {
      v.innerHTML = `<div class="card sv"><h3>問卷與願望</h3><p class="muted" id="svDeny">${a && (a._s === 403 || a._s === 401) ? '這個帳號不是管理者。' : '讀不到問卷結果（' + esc(a ? a._s : '連不到會員伺服器') + '）。'}</p></div>`;
      return;
    }
    paint(v);
  }

  (window.TwSubRoutes = window.TwSubRoutes || []).push((head, rest) => {
    if (head !== 'admin' || rest[0] !== 'survey' || !T()) return null;
    const v = T().view('v-subadm'); if (!v) return null;
    /* 前端也先擋一次：確定不是站主就不打 API（後端本來就只認站主，這裡只是少一次無謂請求）*/
    const A = window.TwAccount, u = A && A.user && A.user();
    if (u && !u.admin) {
      css();
      v.innerHTML = '<div class="card sv"><h3>問卷與願望</h3><p class="muted" id="svDeny">這個帳號不是管理者。</p></div>';
      return 'v-subadm';
    }
    render(v);
    return 'v-subadm';
  });
  window.TwAdminSurvey = { render, state: () => S };
})();
